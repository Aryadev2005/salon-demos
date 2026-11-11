#!/usr/bin/env python3
"""Find salons on Google, turn the best ones into demo sites, and write an outreach sheet.

    export GOOGLE_MAPS_API_KEY=...          # Places API (New) enabled, billing on
    python3 scripts/places_to_leads.py                       # uses scripts/prospects.json
    python3 scripts/places_to_leads.py --limit 27 --dry-run  # pick leads, no photos, no writes

Steps
  1. Text Search (New) for every query in scripts/prospects.json (up to 60 places each).
     Raw responses are cached in cache/places/, so re-runs cost nothing.
  2. Keep salons that are open, have no real website (none, or only Facebook/Instagram/
     Linktree/booking-marketplace links), meet the rating and review thresholds, and are
     not chains or salons already in leads.json / prospects.json "skip".
  3. Rank by rating and review count, take --limit.
  4. For each: download photos (hero, 4 gallery, Christmas band), pick an accent colour from them, build
     hours, services and up to 3 real Google reviews, append to leads.json.
  5. Run build.py for the new slugs and write out/outreach.csv: phone, WhatsApp
     click-to-send link (UK mobiles only), Instagram DM text, demo link.

Costs: one Text Search request returns up to 20 places; photos are one request each.
--max-requests caps the total per run. Standard library + Pillow only.
"""
import argparse
import csv
import json
import math
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "places"
OUT = ROOT / "out"
LEADS = ROOT / "leads.json"
CONFIG = ROOT / "scripts" / "prospects.json"
API = "https://places.googleapis.com/v1"
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

FIELDS = ",".join("places." + f for f in [
    "id", "displayName", "formattedAddress", "shortFormattedAddress", "addressComponents",
    "nationalPhoneNumber", "internationalPhoneNumber", "rating", "userRatingCount",
    "regularOpeningHours", "websiteUri", "googleMapsUri", "reviews", "photos",
    "primaryType", "primaryTypeDisplayName", "businessStatus",
]) + ",nextPageToken"

# A "website" on these hosts doesn't count as the salon having its own site.
NOT_A_WEBSITE = {
    "facebook.com": "Facebook", "fb.com": "Facebook", "instagram.com": "Instagram", "linktr.ee": "Linktree",
    "fresha.com": "Fresha", "treatwell.co.uk": "Treatwell", "booksy.com": "Booksy", "setmore.com": "Setmore",
    "phorest.com": "Phorest", "timely.co.nz": "Timely", "gettimely.com": "Timely", "vagaro.com": "Vagaro",
    "square.site": "Square", "squareup.com": "Square", "wa.me": "WhatsApp", "tiktok.com": "TikTok",
}
BOOKING_HOSTS = {"fresha.com": "Book on Fresha", "treatwell.co.uk": "Book on Treatwell", "booksy.com": "Book on Booksy",
                 "setmore.com": "Book online", "phorest.com": "Book online", "gettimely.com": "Book online",
                 "timely.co.nz": "Book online", "vagaro.com": "Book online", "square.site": "Book online"}
CHAINS = ["toni & guy", "toni&guy", "rush", "regis", "supercuts", "headmasters", "saks", "francesco group",
          "hair by ", "barberbar", "ruby's", "jaques", "blue sky", "the hair & beauty academy",
          "sun centre", "tanning", "sunbed"]

PERSONA = {  # wording + starter services by Google's primary type
    "hair_salon": dict(type="Hair salon", what="cuts, colour and blow-dries",
        services=[("Hair", ["Ladies' cut and blow-dry", "Wash and blow-dry", "Men's cut", "Children's cut"]),
                  ("Colour", ["Full head colour", "Highlights", "Balayage", "Toner and gloss"])],
        party=["Party blow-dry", "Hair up", "Gift vouchers"]),
    "barber_shop": dict(type="Barber", what="skin fades, beard trims and classic cuts",
        services=[("Cuts", ["Haircut", "Skin fade", "Clipper cut", "Kids' cut"]),
                  ("Beard", ["Beard trim", "Hot towel shave", "Cut and beard"])],
        party=["Christmas fade", "Cut and beard", "Gift vouchers"]),
    "nail_salon": dict(type="Nail salon", what="BIAB, gel and nail extensions",
        services=[("Nails", ["BIAB", "Gel polish", "Nail extensions", "Nail art"]),
                  ("Feet", ["Gel toes", "Pedicure"])],
        party=["Festive nail art", "Gel polish", "Gift vouchers"]),
    "beauty_salon": dict(type="Beauty salon", what="lashes, brows, nails and facials",
        services=[("Lashes & brows", ["Lash extensions", "Lash lift", "Brow lamination", "Brow wax and tint"]),
                  ("Beauty", ["Gel nails", "Facials", "Waxing"])],
        party=["Party lashes", "Gel nails", "Gift vouchers"]),
}
PERSONA["hair_care"] = PERSONA["hair_salon"]
PERSONA["beautician"] = PERSONA["beauty_salon"]
PERSONA["spa"] = PERSONA["beauty_salon"]


# ---------------------------------------------------------------- helpers
def slugify(text):
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    t = t.replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40].strip("-")


def host_of(url):
    try:
        h = urllib.parse.urlparse(url).netloc.lower()
    except ValueError:
        return ""
    return h[4:] if h.startswith("www.") else h


def match_host(url, table):
    h = host_of(url)
    for k, v in table.items():
        if h == k or h.endswith("." + k):
            return v
    return None


def uk_mobile(phone):
    """Return +447... if the number is a UK mobile (likely on WhatsApp), else ''."""
    d = re.sub(r"\D", "", phone or "")
    if d.startswith("44"):
        d = "0" + d[2:]
    return "+44" + d[1:] if re.fullmatch(r"07\d{9}", d) else ""


class Budget:
    def __init__(self, limit):
        self.limit, self.used = limit, 0

    def spend(self, what):
        if self.used >= self.limit:
            raise SystemExit(f"Stopped: --max-requests {self.limit} reached (at {what}). Re-run to continue from cache.")
        self.used += 1


def http(req, budget, what):
    budget.spend(what)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read(), r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:400]
            if e.code in (429, 500, 503) and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            raise SystemExit(f"Google API error {e.code} on {what}: {body}")
        except urllib.error.URLError as e:
            if attempt < 2:
                time.sleep(2)
                continue
            raise SystemExit(f"Network error on {what}: {e}")


# ---------------------------------------------------------------- 1. search
def search(query, key, budget, region, pages):
    places, token = [], None
    for page in range(pages):
        cf = CACHE / f"{slugify(query)}-p{page + 1}.json"
        if cf.exists():
            data = json.loads(cf.read_text())
        else:
            if not key:
                break
            body = {"textQuery": query, "pageSize": 20, "regionCode": region, "languageCode": "en"}
            if token:
                body["pageToken"] = token
                time.sleep(2)  # next-page tokens need a moment to become valid
            req = urllib.request.Request(f"{API}/places:searchText", data=json.dumps(body).encode(), method="POST",
                                         headers={"Content-Type": "application/json", "X-Goog-Api-Key": key,
                                                  "X-Goog-FieldMask": FIELDS})
            raw, _ = http(req, budget, f'search "{query}" p{page + 1}')
            data = json.loads(raw)
            CACHE.mkdir(parents=True, exist_ok=True)
            cf.write_text(json.dumps(data, indent=1))
        places += data.get("places", [])
        token = data.get("nextPageToken")
        if not token:
            break
    return places


# ---------------------------------------------------------------- 2. filter + rank
def qualifies(p, cfg, taken_ids, taken_names):
    name = (p.get("displayName") or {}).get("text", "")
    why = None
    if p.get("businessStatus", "OPERATIONAL") != "OPERATIONAL":
        why = "not operating"
    elif p.get("id") in taken_ids or slugify(name) in taken_names:
        why = "already a lead"
    elif any(c in name.lower() for c in CHAINS):
        why = "chain"
    elif (p.get("rating") or 0) < cfg["min_rating"]:
        why = "low rating"
    elif (p.get("userRatingCount") or 0) < cfg["min_reviews"]:
        why = "too few reviews"
    elif p.get("websiteUri") and not match_host(p["websiteUri"], NOT_A_WEBSITE):
        why = "has a website"
    elif not p.get("nationalPhoneNumber"):
        why = "no phone"
    elif not (p.get("regularOpeningHours") or {}).get("periods"):
        why = "no opening hours"
    elif len(p.get("photos") or []) < 5:
        why = "too few photos"
    return why


def score(p):
    return (p.get("rating") or 0) * math.log10(1 + (p.get("userRatingCount") or 0))


# ---------------------------------------------------------------- 4. lead fields
def hours(p):
    """Google periods (day 0 = Sunday) -> template hours, earliest open to latest close per day."""
    per = {}
    for pr in p["regularOpeningHours"]["periods"]:
        o, c = pr.get("open"), pr.get("close")
        if not o:
            continue
        if not c:  # open 24 hours
            for d in range(7):
                per[d] = (0, 24 * 60 - 1)
            break
        d = o["day"]
        start = o.get("hour", 0) * 60 + o.get("minute", 0)
        end = c.get("hour", 0) * 60 + c.get("minute", 0)
        if c["day"] != d or end <= start:
            end = 24 * 60 - 1
        lo, hi = per.get(d, (start, end))
        per[d] = (min(lo, start), max(hi, end))
    out = []
    for i, day in enumerate(DAYS):
        g = (i + 1) % 7
        if g in per:
            s, e = per[g]
            out.append({"day": day, "time": f"{s // 60:02d}:{s % 60:02d}-{e // 60:02d}:{e % 60:02d}"})
        else:
            out.append({"day": day, "time": "Closed"})
    return out


def first_name(display):
    n = (display or "").strip().split()
    if not n:
        return ""
    f = n[0].strip(".,")
    return f[:1].upper() + f[1:] if f.isalpha() and len(f) > 1 else ""


def trim_review(text, limit=230):
    t = re.sub(r"\s+", " ", text or "").strip()
    if len(t) <= limit:
        return t
    cut = t[:limit]
    m = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return cut[:m + 1] if m > 60 else ""


def reviews(p):
    out, seen = [], set()
    for r in sorted(p.get("reviews") or [], key=lambda r: -(r.get("rating") or 0)):
        if (r.get("rating") or 0) < 5:
            continue
        txt = trim_review(((r.get("originalText") or r.get("text") or {}).get("text")))
        name = first_name((r.get("authorAttribution") or {}).get("displayName"))
        if len(txt) < 35 or not name or name in seen:
            continue
        seen.add(name)
        out.append({"text": txt, "name": name})
        if len(out) == 3:
            break
    return out


def address_parts(p):
    comp = {}
    for c in p.get("addressComponents") or []:
        for t in c.get("types", []):
            comp.setdefault(t, c.get("longText") or c.get("shortText"))
    city = comp.get("postal_town") or comp.get("locality") or comp.get("administrative_area_level_2") or ""
    area = comp.get("sublocality") or comp.get("neighborhood") or city
    street = " ".join(x for x in [comp.get("street_number"), comp.get("route")] if x)
    pc = comp.get("postal_code", "")
    address = ", ".join(x for x in [street, f"{city} {pc}".strip()] if x) or p.get("shortFormattedAddress") or ""
    return area, city, address


def accent_from(img_paths):
    """Most characterful mid-tone colour across the photos, nudged to a usable accent."""
    from PIL import Image
    import colorsys
    best, best_s = None, -1
    for ip in img_paths:
        im = Image.open(ip).convert("RGB")
        im.thumbnail((160, 160))
        pal = im.quantize(colors=8, method=Image.Quantize.MEDIANCUT)
        cols = pal.getpalette()[:24]
        counts = sorted(pal.getcolors(), reverse=True)
        for cnt, idx in counts:
            r, g, b = (cols[idx * 3 + k] / 255 for k in range(3))
            h, l, s = colorsys.rgb_to_hls(r, g, b)
            if not (.18 < l < .7) or s < .18:
                continue
            sc = s * math.sqrt(cnt)
            if sc > best_s:
                best_s, best = sc, (h, l, s)
    if not best:
        return "#8A5A44"
    h, l, s = best
    r, g, b = colorsys.hls_to_rgb(h, min(max(l, .32), .48), min(max(s, .35), .7))
    return "#%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))


def fetch_photos(p, slug, key, budget, n, dry):
    folder = ROOT / "demos" / slug / "img"
    folder.mkdir(parents=True, exist_ok=True)
    names = ["hero", "g1", "g2", "g3", "g4", "bridal"][:max(5, min(n, 6))]
    credits, paths = [], []
    photos = p.get("photos") or []
    # hero: prefer a portrait photo
    order = sorted(range(len(photos)), key=lambda i: -(photos[i].get("heightPx", 1) / max(photos[i].get("widthPx", 1), 1)))
    hero_i = order[0] if order else 0
    picks = [hero_i] + [i for i in range(len(photos)) if i != hero_i][:n - 1]
    for name, i in zip(names, picks):
        ph = photos[i]
        dest = folder / f"{name}.jpg"
        for a in ph.get("authorAttributions") or []:
            if a.get("displayName"):
                credits.append(a["displayName"])
        paths.append(dest)
        if dest.exists() or dry:
            continue
        url = f"{API}/{ph['name']}/media?" + urllib.parse.urlencode({"maxWidthPx": 1400, "maxHeightPx": 1400, "key": key})
        raw, ctype = http(urllib.request.Request(url), budget, f"photo {slug}/{name}")
        tmp = dest.with_suffix(".tmp")
        tmp.write_bytes(raw)
        from PIL import Image
        im = Image.open(tmp).convert("RGB")
        im.thumbnail((1400, 1400))
        im.save(dest, "JPEG", quality=80, optimize=True, progressive=True)
        tmp.unlink()
    if not dry and not (folder / "bridal.jpg").exists():
        import shutil
        shutil.copy(folder / "g1.jpg", folder / "bridal.jpg")
    return paths, sorted(set(credits))


def make_lead(p, slug, cfg, accent, credits):
    ptype = p.get("primaryType") or "hair_salon"
    per = PERSONA.get(ptype, PERSONA["hair_salon"])
    name = p["displayName"]["text"]
    area, city, address = address_parts(p)
    phone = p.get("nationalPhoneNumber", "")
    mobile = uk_mobile(phone)
    site = p.get("websiteUri", "")
    booking = match_host(site, BOOKING_HOSTS) if site else None
    rating, count = p.get("rating"), p.get("userRatingCount")
    open_days = [h["day"] for h in hours(p) if h["time"] != "Closed"]
    late = [h for h in hours(p) if h["time"] != "Closed" and int(h["time"][-5:-3]) >= 19]

    def pm(hhmm):
        hh, mm = int(hhmm[:2]), hhmm[3:]
        return f"{hh - 12 if hh > 12 else hh}{'' if mm == '00' else ':' + mm}pm"
    third = (f"Late appointments until {pm(late[0]['time'][-5:])} on {late[0]['day']}s." if late
             else f"Open {'seven days a week' if len(open_days) == 7 else open_days[0] + ' to ' + open_days[-1]}.")
    lead = {
        "slug": slug, "name": name, "type": per["type"],
        "area": area, "address": address, "city": city, "country": "United Kingdom", "lang": "en-GB",
        "phone": phone,
        "rating": rating, "review_count": count,
        "maps_link": p.get("googleMapsUri") or "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(f"{name} {address}"),
        "google_review_link": f"https://search.google.com/local/writereview?placeid={p['id']}",
        "hours": hours(p),
        "headline": f"{per['what'][0].upper() + per['what'][1:]} in {area}.",
        "subline": f"{name} is a {per['type'].lower()} in {city}, rated {rating} from {count:,} Google reviews. "
                   + ("Pick a service and a time below and we'll confirm on WhatsApp." if mobile and not booking
                      else "Book online or give us a ring."),
        "highlights": [f"Rated {rating} from {count:,} Google reviews.",
                       f"Specialists in {per['what']}.", third],
        "services_note": "Call or message the salon for prices.",
        "services": [{"category": c, "items": [{"name": i} for i in items]} for c, items in per["services"]],
        "bridal": {"nav": "Christmas", "kicker": "Christmas & New Year", "title": "Festive appointments go fast.",
                   "text": "Work dos, Christmas Day and New Year's Eve: book early, because December evenings and Saturdays fill up first.",
                   "packages": [{"name": x} for x in per["party"]]},
        "reviews": reviews(p),
        "gallery_title": "Inside the salon",
        "gallery_text": "Photos from the salon's Google listing" + (f" (by {', '.join(credits[:3])})" if credits else "") + ".",
        "accent": accent, "mood": "light", "photos": 4,
        "place_id": p["id"],
        "pitch": {"name": cfg["your_name"], "whatsapp": cfg["your_whatsapp"]},
        "hero_alt": f"Recent work at {name}",
        "_auto": True,
    }
    if mobile:
        lead["whatsapp"] = mobile
    if booking:
        lead["booking_link"], lead["booking_label"] = site, booking
    elif not mobile:
        lead["booking_link"], lead["booking_label"] = "tel:" + re.sub(r"[^\d+]", "", p.get("internationalPhoneNumber") or phone), f"Call {phone} to book"
    if match_host(site, {"instagram.com": 1}):
        lead["instagram"] = site
    if not lead["reviews"]:
        del lead["reviews"]
    return lead


# ---------------------------------------------------------------- 5. outreach
def outreach_row(lead, base_url, cfg):
    demo = f"{base_url.rstrip('/')}/{lead['slug']}/"
    first = cfg["your_name"]
    hook = f"{lead['rating']} from {lead['review_count']:,} Google reviews"
    msg = (f"Hi! I'm {first}. I came across {lead['name']} on Google: {hook} is brilliant, "
           f"but there's no website on your listing, so people searching for a {lead['type'].lower()} in {lead['city']} "
           f"can't see your work, prices or hours in one place.\n\nSo I made you one to look at, free: {demo}\n\n"
           f"If you like it, it's £{cfg['price']} one-off and I'll put it live on your Google listing this week. "
           f"If not, no worries at all 😊")
    wa = lead.get("whatsapp", "")
    ig = lead.get("instagram") or "https://www.google.com/search?q=" + urllib.parse.quote(f"{lead['name']} {lead['city']} instagram")
    return {
        "salon": lead["name"], "type": lead["type"], "town": lead["city"], "rating": lead["rating"],
        "reviews": lead["review_count"], "phone": lead["phone"],
        "channel": "WhatsApp" if wa else "Instagram DM (or call)",
        "whatsapp_link": f"https://wa.me/{wa.lstrip('+')}?text={urllib.parse.quote(msg)}" if wa else "",
        "instagram": "" if wa else ig,
        "demo": demo, "message": msg, "status": "", "notes": "",
    }


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(CONFIG))
    ap.add_argument("--limit", type=int, help="how many new demos to make (default from config)")
    ap.add_argument("--max-requests", type=int, default=400, help="hard cap on Google requests this run")
    ap.add_argument("--dry-run", action="store_true", help="search and rank only; no photos, no writes")
    ap.add_argument("--rebuild-sheet", action="store_true", help="only rewrite out/outreach.csv from leads.json")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text())
    cfg.setdefault("min_rating", 4.5)
    cfg.setdefault("min_reviews", 40)
    cfg.setdefault("photos", 6)
    cfg.setdefault("region", "GB")
    cfg.setdefault("pages", 3)
    cfg.setdefault("price", 300)
    limit = args.limit or cfg.get("limit", 27)
    key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    leads = json.loads(LEADS.read_text())

    if args.rebuild_sheet:
        write_sheet([l for l in leads if l.get("_auto")], cfg)
        return

    if not key and not any(CACHE.glob("*.json")):
        sys.exit("Set GOOGLE_MAPS_API_KEY first (Places API (New) enabled on a billed project).")

    budget = Budget(args.max_requests)
    seen, pool = set(), []
    for q in cfg["queries"]:
        found = search(q, key, budget, cfg["region"], cfg["pages"])
        print(f"  {len(found):3d} places  · {q}")
        for p in found:
            if p["id"] not in seen:
                seen.add(p["id"])
                pool.append(p)

    taken_ids = {l.get("place_id") for l in leads if l.get("place_id")}
    taken_names = {slugify(l["name"]) for l in leads} | {slugify(s) for s in cfg.get("skip", [])}
    rejected, keep = {}, []
    for p in pool:
        why = qualifies(p, cfg, taken_ids, taken_names)
        if why:
            rejected[why] = rejected.get(why, 0) + 1
        else:
            keep.append(p)
    keep.sort(key=score, reverse=True)
    pick = keep[:limit]
    print(f"\n{len(pool)} unique places, {len(keep)} qualify, making {len(pick)}.")
    print("  skipped: " + ", ".join(f"{v} {k}" for k, v in sorted(rejected.items(), key=lambda kv: -kv[1])))
    for p in pick:
        print(f"  {p.get('rating')}★ {p.get('userRatingCount'):>5}  {p['displayName']['text']}  ·  {p.get('nationalPhoneNumber')}"
              f"{'  · WhatsApp' if uk_mobile(p.get('nationalPhoneNumber')) else ''}")
    if args.dry_run:
        print(f"\nDry run: {budget.used} Google requests used. Nothing written.")
        return

    used_slugs = {l["slug"] for l in leads}
    new = []
    for p in pick:
        base = slugify(p["displayName"]["text"])
        town = slugify(address_parts(p)[1])
        slug = base if base.endswith(town) or not town else f"{base}-{town}"
        n = 2
        while slug in used_slugs:
            slug, n = f"{base}-{town}-{n}", n + 1
        used_slugs.add(slug)
        paths, credits = fetch_photos(p, slug, key, budget, cfg["photos"], False)
        lead = make_lead(p, slug, cfg, accent_from(paths[:3]), credits)
        new.append(lead)
        print(f"  ✓ {slug}  ({lead['accent']})")

    leads += new
    LEADS.write_text(json.dumps(leads, indent=2, ensure_ascii=False) + "\n")
    import subprocess
    for l in new:
        r = subprocess.run([sys.executable, str(ROOT / "build.py"), l["slug"]], capture_output=True, text=True)
        print(("  built " if r.returncode == 0 else "  FAILED ") + l["slug"] + ("" if r.returncode == 0 else ": " + r.stderr.strip()))
    write_sheet([l for l in leads if l.get("_auto")], cfg)
    print(f"\n{budget.used} Google requests used this run.")


def write_sheet(auto, cfg):
    OUT.mkdir(exist_ok=True)
    rows = [outreach_row(l, cfg["base_url"], cfg) for l in auto]
    path = OUT / "outreach.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["salon"])
        w.writeheader()
        w.writerows(rows)
    wa = sum(1 for r in rows if r["whatsapp_link"])
    print(f"Wrote {path.relative_to(ROOT)}: {len(rows)} salons, {wa} by WhatsApp, {len(rows) - wa} by Instagram/phone.")


if __name__ == "__main__":
    main()
