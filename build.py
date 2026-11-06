#!/usr/bin/env python3
"""Build a salon demo site from leads.json.

    python3 build.py <slug>        build one demo -> demos/<slug>/index.html
    python3 build.py --all         build every lead
    python3 build.py --list        list slugs in leads.json

Standard library only. Fails with a clear message when a field or image is missing.
"""
import colorsys
import datetime
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
LEADS = ROOT / "leads.json"
TEMPLATE = ROOT / "template.html"
DEMOS = ROOT / "demos"

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
REQUIRED = {
    "slug": str, "name": str, "type": str, "area": str, "city": str, "country": str,
    "phone": str, "whatsapp": str, "rating": (int, float), "review_count": int,
    "maps_link": str, "hours": list, "headline": str, "subline": str,
    "highlights": list, "services": list, "reviews": list,
    "accent": str, "mood": str, "photos": int,
}
MIN_PHOTOS = 4  # g1 = services photo, g2..gN = gallery (at least 3)


class LeadError(Exception):
    pass


# ---------------------------------------------------------------- helpers
def e(s):
    return html.escape(str(s), quote=True)


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def rgb2hex(c):
    return "#" + "".join(f"{round(max(0, min(1, v)) * 255):02X}" for v in c)


def mix(a, b, t):
    """t=0 -> a, t=1 -> b"""
    a, b = hex2rgb(a), hex2rgb(b)
    return rgb2hex(tuple(x + (y - x) * t for x, y in zip(a, b)))


def lum(h):
    def ch(v):
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in hex2rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def push_contrast(col, bg, target, toward):
    """Move col toward black/white until it reaches target contrast on bg."""
    t = 0.0
    out = col
    while contrast(out, bg) < target and t < 1:
        t += 0.04
        out = mix(col, toward, t)
    return out


def palette(accent, mood):
    accent = accent.upper()
    h, l, s = colorsys.rgb_to_hls(*hex2rgb(accent))
    soft = rgb2hex(colorsys.hls_to_rgb(h, min(0.72, l + 0.18), s * 0.7))
    if mood == "light":
        p = {
            "paper": mix(accent, "#FFFCF8", 0.93),
            "paper2": mix(accent, "#FFFFFF", 0.965),
            "mist": mix(accent, "#FFFFFF", 0.84),
            "line": mix(accent, "#FFFFFF", 0.76),
            "ink": mix(accent, "#16120F", 0.88),
            "board": mix(accent, "#120E0C", 0.80),
        }
        p["board2"] = mix(p["board"], "#FFFFFF", 0.06)
        p["muted"] = push_contrast(mix(accent, "#5A524C", 0.75), p["paper"], 5.2, "#000000")
        p["accent"] = push_contrast(accent, p["paper"], 4.6, "#000000")
        p["chalk"] = mix(accent, "#FFFFFF", 0.93)
        p["chalk_dim"] = mix(accent, "#FFFFFF", 0.70)
        p["gold"] = push_contrast(soft, p["board"], 4.6, "#FFFFFF")
        p["photo_a"], p["photo_b"] = mix(accent, "#FFFFFF", 0.7), mix(accent, "#FFFFFF", 0.4)
    else:
        p = {
            "paper": mix(accent, "#0C0B0A", 0.86),
            "paper2": mix(accent, "#161412", 0.80),
            "mist": mix(accent, "#1C1A17", 0.66),
            "line": mix(accent, "#34302B", 0.62),
            "ink": mix(accent, "#F4EFE8", 0.92),
            "board": mix(accent, "#120D0C", 0.48),
        }
        p["board2"] = mix(p["board"], "#FFFFFF", 0.06)
        p["muted"] = push_contrast(mix(p["ink"], p["paper"], 0.38), p["paper"], 5.2, "#FFFFFF")
        p["accent"] = push_contrast(soft, p["paper"], 4.8, "#FFFFFF")
        p["chalk"] = mix(accent, "#FFFFFF", 0.93)
        p["chalk_dim"] = mix(accent, "#FFFFFF", 0.70)
        p["gold"] = push_contrast(mix(soft, "#E8C89A", 0.5), p["board"], 4.8, "#FFFFFF")
        p["photo_a"], p["photo_b"] = mix(accent, "#000000", 0.4), mix(accent, "#000000", 0.7)
    # text on accent buttons
    p["on_accent"] = "#FFFFFF" if contrast("#FFFFFF", p["accent"]) >= contrast("#111111", p["accent"]) else "#111111"
    p["scheme"] = mood
    return p


def initials(name):
    words = [w for w in re.split(r"[\s&]+", name) if w and w[0].isalnum()]
    return "".join(w[0] for w in words[:2]).upper() or name[:2].upper()


def wa_number(raw):
    return re.sub(r"\D", "", raw)


def tel(raw):
    return "+" + re.sub(r"\D", "", raw)


# ---------------------------------------------------------------- validation
def validate(lead, folder):
    slug = lead.get("slug", "<missing slug>")
    problems = []
    for key, typ in REQUIRED.items():
        if key not in lead or lead[key] in ("", None, []):
            problems.append(f"missing required field '{key}'")
        elif not isinstance(lead[key], typ) or isinstance(lead[key], bool):
            problems.append(f"field '{key}' has the wrong type ({type(lead[key]).__name__})")
    if problems:
        raise LeadError(f"[{slug}] " + "; ".join(problems))

    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", lead["slug"]):
        problems.append("slug must be lowercase letters, digits and hyphens")
    if lead["mood"] not in ("light", "dark"):
        problems.append("mood must be \"light\" or \"dark\"")
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", lead["accent"]):
        problems.append("accent must be a hex colour like #8A4A3B")
    if len(lead["highlights"]) != 3:
        problems.append("highlights must have exactly 3 points")
    if len(lead["reviews"]) != 3 or not all(isinstance(r, dict) and r.get("text") and r.get("name") for r in lead["reviews"]):
        problems.append("reviews must be exactly 3 objects with 'text' and 'name'")
    if not 0 <= float(lead["rating"]) <= 5:
        problems.append("rating must be between 0 and 5")
    days = [h.get("day") for h in lead["hours"] if isinstance(h, dict)]
    if days != DAYS or not all(h.get("time") for h in lead["hours"]):
        problems.append("hours must list Monday..Sunday in order as {day, time} (time may be \"Closed\")")
    for h in lead["hours"]:
        t = h.get("time", "")
        if t and t.lower() != "closed" and not re.fullmatch(r"\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2}", t):
            problems.append(f"hours for {h.get('day')} must be like \"10:00-20:00\" or \"Closed\" (got \"{t}\")")
    for c in lead["services"]:
        if not isinstance(c, dict) or not c.get("category") or not c.get("items"):
            problems.append("each service needs 'category' and a non-empty 'items' list")
            continue
        for it in c["items"]:
            if not isinstance(it, dict) or not it.get("name"):
                problems.append(f"every item in '{c['category']}' needs a 'name'")
    if lead["photos"] < MIN_PHOTOS:
        problems.append(f"photos must be at least {MIN_PHOTOS} (g1 is the services photo, g2..gN the gallery)")
    for i, ba in enumerate(lead.get("before_after") or [], 1):
        if not isinstance(ba, dict) or not ba.get("title"):
            problems.append(f"before_after #{i} needs a 'title'")
    if lead.get("bridal"):
        b = lead["bridal"]
        if not b.get("title") or not b.get("text"):
            problems.append("bridal needs 'title' and 'text'")
    for t in lead.get("team") or []:
        if not t.get("name") or not t.get("role"):
            problems.append("each team member needs 'name' and 'role'")

    # images
    need = ["hero.jpg"] + [f"g{i}.jpg" for i in range(1, lead["photos"] + 1)]
    for i, _ in enumerate(lead.get("before_after") or [], 1):
        need += [f"ba{i}-before.jpg", f"ba{i}-after.jpg"]
    if lead.get("bridal"):
        need.append("bridal.jpg")
    missing = [n for n in need if not (folder / "img" / n).is_file()]
    if missing:
        problems.append(f"missing images in demos/{slug}/img/: " + ", ".join(missing))

    if problems:
        raise LeadError(f"[{slug}]\n  - " + "\n  - ".join(problems))


# ---------------------------------------------------------------- hours
def parse_hours(hours):
    out = []
    for h in hours:
        t = h["time"].strip()
        if t.lower() == "closed":
            out.append({"day": h["day"], "open": None, "close": None})
        else:
            a, b = re.split(r"\s*[-–]\s*", t)
            out.append({"day": h["day"], "open": a, "close": b})
    return out


def fmt_time(hhmm):
    h, m = map(int, hhmm.split(":"))
    suffix = "am" if h < 12 else "pm"
    h12 = h % 12 or 12
    return f"{h12}{'' if m == 0 else f':{m:02d}'}{suffix}"


def fmt_range(d):
    return "Closed" if not d["open"] else f"{fmt_time(d['open'])} to {fmt_time(d['close'])}"


def days_open_phrase(parsed):
    n = sum(1 for d in parsed if d["open"])
    if n == 7:
        return "Open seven days"
    closed = [d["day"] for d in parsed if not d["open"]]
    return "Closed " + " & ".join(c + "s" for c in closed)


# ---------------------------------------------------------------- sections
def sec_highlights(lead):
    items = "".join(
        f'<li><span class="num">0{i}</span><p>{e(h)}</p></li>' for i, h in enumerate(lead["highlights"], 1)
    )
    return f'<section class="hl wrap" aria-label="Why {e(lead["name"])}"><ol>{items}</ol></section>'


def sec_before_after(lead):
    pairs = lead.get("before_after") or []
    if not pairs:
        return ""
    figs = []
    for i, ba in enumerate(pairs, 1):
        t = e(ba["title"])
        figs.append(f'''
    <figure class="ba">
      <div class="stage" style="--pos:50%">
        <img src="img/ba{i}-before.jpg" alt="Before: {t}" loading="lazy" decoding="async">
        <img class="after" src="img/ba{i}-after.jpg" alt="After: {t}" loading="lazy" decoding="async">
        <span class="pill b">Before</span><span class="pill a">After</span>
        <input type="range" min="0" max="100" value="50" aria-label="Compare before and after: {t}">
        <span class="handle"></span>
      </div>
      <figcaption><h3>{t}</h3>{f"<p>{e(ba['note'])}</p>" if ba.get("note") else ""}</figcaption>
    </figure>''')
    cols = len(pairs)
    return f'''
<section id="results" class="wrap block">
  <div class="head"><h2>Before and after</h2><p>Real clients, straight from the chair. Drag the handle to compare.</p></div>
  <div class="ba-grid cols-{cols}">{"".join(figs)}
  </div>
</section>'''


def sec_services(lead):
    cats = []
    for c in lead["services"]:
        rows = []
        for it in c["items"]:
            price = f'<b>{e(it["price"])}</b>' if it.get("price") else ""
            note = f'<small>{e(it["note"])}</small>' if it.get("note") else ""
            rows.append(f'<li><span>{e(it["name"])}{note}</span>{price}</li>')
        cats.append(f'<div class="cat"><h3>{e(c["category"])}</h3><ul>{"".join(rows)}</ul></div>')
    note = lead.get("services_note") or "Every visit starts with a quick consultation."
    return f'''
<section id="services" class="wrap block">
  <div class="treat">
    <div class="photo"><img src="img/g1.jpg" alt="Inside {e(lead["name"])}" loading="lazy" decoding="async"></div>
    <div>
      <div class="head"><h2>Services{" and prices" if any(it.get("price") for c in lead["services"] for it in c["items"]) else ""}</h2><p>{e(note)}</p></div>
      <div class="menu">{"".join(cats)}</div>
      <div class="after-row"><a class="btn solid" href="#book">Book an appointment</a></div>
    </div>
  </div>
</section>'''


def sec_bridal(lead):
    b = lead.get("bridal")
    if not b:
        return ""
    rows = []
    for pkg in b.get("packages") or []:
        price = "<span>" + e(pkg["price"]) + "</span>" if pkg.get("price") else ""
        rows.append("<li><b>" + e(pkg["name"]) + "</b>" + price + "</li>")
    pk = "".join(rows)
    pk = f'<ul class="pkgs">{pk}</ul>' if pk else ""
    sign = "".join(f"<li>{e(c['category'])}</li>" for c in lead["services"][:4])
    return f'''
<section id="bridal" class="band">
  <div class="wrap shop">
    <div>
      <span class="kicker">{e(b.get("kicker") or "For the big day")}</span>
      <h2>{e(b["title"])}</h2>
      <p>{e(b["text"])}</p>
      {pk}
      <a class="btn chalk js-wa" href="#book">Ask about your date</a>
    </div>
    <div class="shop-visual">
      <div class="vid"><img src="img/bridal.jpg" alt="{e(b["title"])}" loading="lazy" decoding="async"></div>
      <div class="aframe{" long" if len(lead["name"]) > 16 else ""}" role="img" aria-label="Chalkboard sign for {e(lead["name"])}">
        <p class="t1">{e(lead["name"])}</p>
        <ul>{sign}</ul>
        <p class="open">Open</p>
      </div>
    </div>
  </div>
</section>'''


def sec_gallery(lead):
    count = lead["photos"] - 1

    def area(n):  # named grid areas exist for 3..7 photos; more falls back to a repeating pattern
        return f' style="grid-area:t{n}"' if 3 <= count <= 7 else ""

    tiles = []
    for i in range(2, lead["photos"] + 1):
        tiles.append(
            f'<button class="tile" type="button" data-i="{i - 2}" aria-label="Open photo {i - 1}"{area(i - 1)}>'
            f'<img src="img/g{i}.jpg" alt="{e(lead["name"])}, photo {i - 1}" loading="lazy" decoding="async"></button>'
        )
    return f'''
<section id="gallery" class="wrap block">
  <div class="head"><h2>{e(lead.get("gallery_title") or "Recent looks")}</h2><p>{e(lead.get("gallery_text") or "A few favourites from the salon. Tap any photo to see it larger.")}</p></div>
  <div class="gallery{f' n{len(tiles)}' if 3 <= len(tiles) <= 7 else ''}">{"".join(tiles)}</div>
  {f'<div class="after-row"><a class="btn ghost" href="{e(lead["instagram"])}" target="_blank" rel="noopener">See more on Instagram</a></div>' if lead.get("instagram") else ""}
</section>'''


def sec_reviews(lead):
    star = '<svg viewBox="0 0 24 24"><path d="M12 2l3 6.6 7.2.7-5.4 4.8 1.6 7L12 17.5 5.6 21.1l1.6-7L1.8 9.3 9 8.6z"/></svg>'
    q = "".join(
        f'<blockquote><p>“{e(r["text"])}”</p><footer>{e(r["name"])} · Google review</footer></blockquote>'
        for r in lead["reviews"]
    )
    rating = f'{float(lead["rating"]):.1f}'
    return f'''
<section id="reviews" class="wrap block">
  <div class="rating">
    <b>{rating}</b>
    <div><div class="stars" aria-hidden="true">{star * 5}</div><span>from {lead["review_count"]:,} Google reviews</span></div>
  </div>
  <div class="quotes">{q}</div>
  <div class="rv-cta"><a class="btn ghost" href="#review">Been in recently? Leave a review</a></div>
</section>'''


def sec_team(lead):
    team = lead.get("team") or []
    if not team:
        return ""
    ppl = ""
    for t in team:
        note = "<p>" + e(t["note"]) + "</p>" if t.get("note") else ""
        ppl += '<div class="person"><h3>' + e(t["name"]) + '</h3><p class="role">' + e(t["role"]) + "</p>" + note + "</div>"
    return f'''
<section id="team" class="wrap block">
  <div class="head"><h2>Who you'll meet</h2></div>
  <div class="team n{min(len(team), 4)}">{ppl}</div>
</section>'''


def sec_hours_rows(parsed):
    idx = {"Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4, "Friday": 5, "Saturday": 6, "Sunday": 0}
    rows = ""
    for d in parsed:
        cls = ' class="closed"' if not d["open"] else ""
        rows += '<tr data-d="%d"%s><td>%s</td><td>%s</td></tr>' % (idx[d["day"]], cls, d["day"], fmt_range(d))
    return rows


def service_options(lead):
    out = []
    for c in lead["services"]:
        opts = "".join(f"<option>{e(it['name'])}</option>" for it in c["items"])
        out.append(f'<optgroup label="{e(c["category"])}">{opts}</optgroup>')
    out.append("<option>Not sure yet, I'd like advice</option>")
    return "".join(out)


def chips(lead, pressed_first=False):
    names = [t["name"] for t in lead.get("team") or []]
    return names


# ---------------------------------------------------------------- render
def render(lead):
    slug = lead["slug"]
    folder = DEMOS / slug
    validate(lead, folder)
    p = palette(lead["accent"], lead["mood"])
    parsed = parse_hours(lead["hours"])
    name = lead["name"]
    place = f'{lead["area"]}, {lead["city"]}'
    wa = wa_number(lead["whatsapp"])
    names = chips(lead)

    review_chips = "".join(f'<button class="chip" type="button" aria-pressed="false">{e(n)}</button>' for n in names)
    kit_chips = '<button class="chip" type="button" aria-pressed="true" data-s="">Anyone</button>' + "".join(
        f'<button class="chip" type="button" aria-pressed="false" data-s="{e(n)}">{e(n)}</button>' for n in names
    )

    nav = [("#services", "Services")]
    if lead.get("before_after"):
        nav.append(("#results", "Results"))
    nav.append(("#gallery", "Gallery"))
    if lead.get("bridal"):
        nav.append(("#bridal", "Bridal"))
    nav += [("#reviews", "Reviews"), ("#visit", "Visit")]

    data = {
        "name": name,
        "whatsapp": wa,
        "google_review": lead.get("google_review_link") or lead["maps_link"],
        "hours": [{"open": d["open"], "close": d["close"]} for d in parsed],  # Monday-first
        "gallery": [f"img/g{i}.jpg" for i in range(2, lead["photos"] + 1)],
    }

    q = quote(f'{name}, {lead["area"]}, {lead["city"]}, {lead["country"]}')
    values = {
        "lang": lead.get("lang", "en"),
        "title": e(f'{name} · {lead["type"]} in {place}'),
        "description": e(f'{lead["headline"]} {lead["subline"]}'[:300]),
        "name": e(name),
        "type": e(lead["type"]),
        "area": e(lead["area"]),
        "city": e(lead["city"]),
        "place": e(place),
        "headline": e(lead["headline"]),
        "subline": e(lead["subline"]),
        "initials": e(lead.get("monogram") or initials(name)),
        "rating": f'{float(lead["rating"]):.1f}',
        "review_count": f'{lead["review_count"]:,}',
        "badge_text": e(f'{lead["area"]} · {lead["city"]} · {days_open_phrase(parsed).lower()} ·'),
        "days_open": e(days_open_phrase(parsed)),
        "phone": e(lead["phone"]),
        "tel": tel(lead["phone"]),
        "wa_link": f"https://wa.me/{wa}",
        "maps_link": e(lead["maps_link"]),
        "map_embed": f"https://www.google.com/maps?q={q}&output=embed",
        "book_link": e(lead.get("booking_link") or "#book"),
        "nav": "".join(f'<a href="{h}">{t}</a>' for h, t in nav),
        "highlights": sec_highlights(lead),
        "before_after": sec_before_after(lead),
        "services": sec_services(lead),
        "bridal": sec_bridal(lead),
        "gallery": sec_gallery(lead),
        "reviews": sec_reviews(lead),
        "team": sec_team(lead),
        "hours_rows": sec_hours_rows(parsed),
        "service_options": service_options(lead),
        "review_chips_block": f'<div class="rv-q">Who looked after you?</div><div class="chips" id="rvWho">{review_chips}</div>' if names else "",
        "kit_chips_block": f'<p>Who is sending it?</p><div class="chips left" id="kitWho">{kit_chips}</div>' if names else "",
        "instagram_link": f' · <a href="{e(lead["instagram"])}" target="_blank" rel="noopener">Instagram</a>' if lead.get("instagram") else "",
        "year": str(datetime.date.today().year),
        "data_json": json.dumps(data, ensure_ascii=False).replace("</", "<\\/"),
    }
    for k, v in p.items():
        values["c_" + k] = v

    tpl = TEMPLATE.read_text(encoding="utf-8")
    out = re.sub(r"\{\{\s*([a-z_0-9]+)\s*\}\}", lambda m: lookup(values, m.group(1), slug), tpl)
    (folder / "index.html").write_text(out, encoding="utf-8")
    return folder / "index.html"


def lookup(values, key, slug):
    if key not in values:
        raise LeadError(f"[{slug}] template uses unknown placeholder {{{{{key}}}}}")
    return str(values[key])


def load_leads():
    try:
        leads = json.loads(LEADS.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        sys.exit(f"leads.json is not valid JSON: {err}")
    if not isinstance(leads, list):
        sys.exit("leads.json must be a list of lead objects")
    return leads


def main(argv):
    if len(argv) != 2 or argv[1] in ("-h", "--help"):
        sys.exit(__doc__.strip())
    leads = load_leads()
    if argv[1] == "--list":
        for l in leads:
            print(l.get("slug"))
        return
    targets = leads if argv[1] == "--all" else [l for l in leads if l.get("slug") == argv[1]]
    if not targets:
        sys.exit(f"No lead with slug '{argv[1]}' in leads.json. Known: {', '.join(str(l.get('slug')) for l in leads) or 'none'}")
    failed = False
    for lead in targets:
        try:
            path = render(lead)
            print(f"built {path.relative_to(ROOT)}  ->  /{lead['slug']}/")
        except LeadError as err:
            failed = True
            print(f"ERROR {err}", file=sys.stderr)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv)
