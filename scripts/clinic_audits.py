#!/usr/bin/env python3
"""Retainer pipeline: private dental and aesthetics clinics that HAVE a website but sit below the top 3.

    export GOOGLE_MAPS_API_KEY=...                       # Places API (New)
    python3 scripts/clinic_audits.py --dry-run           # search + rank only, nothing written
    python3 scripts/clinic_audits.py --check-sites       # leads + audits + out/clinics.csv
    python3 scripts/clinic_audits.py --sent              # after sending day 1's batch: mark it contacted
    python3 scripts/clinic_audits.py --mark some-slug:declined --mark other-slug:yes

The salon and trades scripts look for businesses with NO website and pitch a one-off site. This one is the
opposite: the buyer already has a site that isn't winning searches, and the pitch is a monthly retainer.

  1. Search "<service> in <town>" for every service and town in scripts/clinic-prospects.json.
     The order Google returns is the ranking we quote (it can vary a little by where the searcher is).
  2. Keep independent clinics at position 4+ with their own website, good rating and enough reviews.
  3. For each: the three businesses above them, how reviews compare, optional homepage checks.
  4. Write one audit page per clinic (demos/audit-<slug>/index.html), a value-first WhatsApp opener
     (no link, no price), the follow-up for after they say yes, and send-day batches of --per-day.

Only facts from Google and the clinic's own homepage go into messages and audits. No medical claims.
Leads and their status live in clinic_leads.json; declined clinics never get a message again.
"""
import argparse
import csv
import datetime
import html
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
API = "https://places.googleapis.com/v1"
FIELDS = ",".join("places." + f for f in [
    "id", "displayName", "formattedAddress", "addressComponents", "nationalPhoneNumber", "rating",
    "userRatingCount", "websiteUri", "googleMapsUri", "primaryType", "types", "businessStatus",
]) + ",nextPageToken"

NOT_A_WEBSITE = ["facebook.com", "fb.com", "instagram.com", "linktr.ee", "wa.me", "tiktok.com", "business.site",
                 "google.com", "g.page", "fresha.com", "treatwell.co.uk", "booksy.com", "phorest.com", "yell.com"]
CHAINS = ["mydentist", "my dentist", "bupa", "portman", "rodericks", "colosseum", "dentalcare group", "damira",
          "smilepod", "sk:n", "sknclinics", "therapie", "laser clinics", "transform hospital", "harley medical",
          "superdrug", "boots", "spire", "nuffield", "nhs", "together dental", "dental partners", "riverdale"]
CHAIN_HOSTS = ["mydentist.co.uk", "bupa.co.uk", "portmandentalcare.com", "rodericksdentalpartners.co.uk",
               "colosseumdental.co.uk", "sknclinics.co.uk", "therapieclinic.com", "laserclinics.co.uk",
               "togetherdental.co.uk", "dentalpartners.co.uk"]
STATUSES = ["", "contacted", "replied", "yes", "paid", "declined"]
BOOKING = ["book online", "book now", "book an appointment", "book a consultation", "online booking", "dentally",
           "softwareofexcellence", "pabau", "fresha.com", "phorest", "calendly", "cliniko", "timely", "ovatu"]
SCHEMA_TYPES = ["Dentist", "MedicalBusiness", "MedicalClinic", "LocalBusiness", "BeautySalon", "HealthAndBeautyBusiness",
                "Physician", "DaySpa"]


# ---------------------------------------------------------------- helpers
def slugify(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40].strip("-")


def host(url):
    h = urllib.parse.urlparse(url or "").netloc.lower()
    return h[4:] if h.startswith("www.") else h


def host_in(url, table):
    h = host(url)
    return bool(h) and any(h == d or h.endswith("." + d) for d in table)


def uk_mobile(phone):
    d = re.sub(r"\D", "", phone or "")
    if d.startswith("44"):
        d = "0" + d[2:]
    return "44" + d[1:] if re.fullmatch(r"07\d{9}", d) else ""


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def tidy_name(n):
    n = re.split(r"\s[-–—]\s?|\s?\|", re.sub(r"\s+", " ", n).strip())[0]
    n = re.sub(r"\s+(Ltd|Limited)\.?$", "", n, flags=re.I).strip()
    if n.isupper() and len(n) > 6:
        n = " ".join(w if len(w) <= 3 else w.capitalize() for w in n.split())
    return n


def name_of(p):
    return tidy_name((p.get("displayName") or {}).get("text", ""))


def town_of(p):
    comp = {}
    for c in p.get("addressComponents") or []:
        for t in c.get("types", []):
            comp.setdefault(t, c.get("longText"))
    return comp.get("postal_town") or comp.get("locality") or ""


def is_chain(p):
    n = (p.get("displayName") or {}).get("text", "").lower()
    return any(c in n for c in CHAINS) or host_in(p.get("websiteUri"), CHAIN_HOSTS)


class Budget:
    def __init__(self, n):
        self.n, self.used = n, 0

    def spend(self, what):
        if self.used >= self.n:
            raise SystemExit(f"Stopped at --max-requests {self.n} ({what}). Re-run to continue from cache.")
        self.used += 1


# ---------------------------------------------------------------- 1. search
def search(q, key, budget, cache):
    cf = cache / "places" / f"{slugify(q)}.json"
    if cf.exists():
        return json.loads(cf.read_text()).get("places", [])
    if not key:
        return []
    budget.spend(f'search "{q}"')
    body = {"textQuery": q, "pageSize": 20, "regionCode": "GB", "languageCode": "en"}
    req = urllib.request.Request(f"{API}/places:searchText", json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "X-Goog-Api-Key": key,
                                          "X-Goog-FieldMask": FIELDS})
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                data = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and i < 2:
                time.sleep(2 * (i + 1))
                continue
            raise SystemExit(f"Google API error {e.code} on \"{q}\": {e.read().decode('utf-8', 'replace')[:300]}")
        except urllib.error.URLError as e:
            if i == 2:
                raise SystemExit(f"Network error on \"{q}\": {e}")
            time.sleep(2)
    cf.parent.mkdir(parents=True, exist_ok=True)
    cf.write_text(json.dumps(data, indent=1))
    return data.get("places", [])


# ---------------------------------------------------------------- 2. filter
def in_town(p, town):
    where = " ".join([p.get("formattedAddress") or ""] + [c.get("longText") or "" for c in p.get("addressComponents") or []])
    return town.lower() in where.lower()


def why_not(p, pos, cfg, town):
    if pos < cfg["min_position"]:
        return "already top 3"
    if pos > cfg["max_position"]:
        return "too far down (may not offer it)"
    if p.get("businessStatus", "OPERATIONAL") != "OPERATIONAL":
        return "not operating"
    country = next((c.get("shortText") for c in p.get("addressComponents") or [] if "country" in c.get("types", [])), None)
    if country and country != "GB":
        return "other country"
    if is_chain(p):
        return "chain"
    if not in_town(p, town):
        return "based in another town"
    if re.search(r"hospital|@", (p.get("displayName") or {}).get("text", ""), re.I):
        return "inside a hospital"
    if (p.get("primaryType") or "") in cfg["exclude_types"]:
        return "excluded type"
    if not p.get("websiteUri") or host_in(p["websiteUri"], NOT_A_WEBSITE):
        return "no own website"
    if (p.get("rating") or 0) < cfg["min_rating"]:
        return "low rating"
    if (p.get("userRatingCount") or 0) < cfg["min_reviews"]:
        return "too few reviews"
    if not p.get("nationalPhoneNumber"):
        return "no phone"
    return None


def brief(p):
    return {"name": name_of(p), "rating": round(p.get("rating") or 0, 1), "reviews": p.get("userRatingCount") or 0,
            "website": bool(p.get("websiteUri")) and not host_in(p.get("websiteUri"), NOT_A_WEBSITE)}


def collect(cfg, key, budget, cache):
    """place id -> {place, niche, hits:[{query, service, town, position, above:[3 briefs]}]} plus skip counts."""
    found, rej = {}, {}
    for niche, spec in cfg["niches"].items():
        for town in cfg["towns"]:
            for service in spec["services"]:
                q = f"{service} in {town}"
                places = search(q, key, budget, cache)
                print(f"  {len(places):3d} · {q}")
                for i, p in enumerate(places):
                    w = why_not(p, i + 1, cfg, town)
                    if w:
                        rej[w] = rej.get(w, 0) + 1
                        continue
                    e = found.setdefault(p["id"], {"place": p, "niche": niche, "hits": []})
                    e["hits"].append({"query": q, "service": service, "town": town, "position": i + 1,
                                      "above": [brief(x) for x in places[:3]]})
    return found, rej


def outdone(hit, reviews):
    """How many of the three above have fewer Google reviews than the clinic."""
    return sum(1 for a in hit["above"] if a["reviews"] < reviews)


def best_hit(e):
    r = e["place"].get("userRatingCount") or 0
    return max(e["hits"], key=lambda h: (outdone(h, r), -h["position"]))


def score(e):
    p = e["place"]
    r = p.get("userRatingCount") or 0
    return ((2 if uk_mobile(p.get("nationalPhoneNumber")) else 0) * 10 + outdone(best_hit(e), r) * 3
            + (p.get("rating") or 0) * math.log10(1 + r))


# ---------------------------------------------------------------- 3. homepage checks
def check_site(url, town, services, cache, enabled):
    cf = cache / "sites" / f"{slugify(host(url))}.json"
    if cf.exists():
        return json.loads(cf.read_text())
    if not enabled:
        return None
    out = {"url": url, "ok": False}
    try:
        t0 = time.time()
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                                                                 "AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1"})
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read(2_000_000)
            final = r.geturl()
        secs = time.time() - t0
        page = raw.decode("utf-8", "replace")
        low = page.lower()
        title = re.sub(r"\s+", " ", (re.search(r"<title[^>]*>(.*?)</title>", page, re.I | re.S) or [None, ""])[1]).strip()
        h1 = re.sub(r"<[^>]+>", " ", (re.search(r"<h1[^>]*>(.*?)</h1>", page, re.I | re.S) or [None, ""])[1])
        head = (title + " " + h1).lower()
        ld = " ".join(re.findall(r"<script[^>]+application/ld\+json[^>]*>(.*?)</script>", page, re.I | re.S))
        out.update(ok=True, seconds=round(secs, 1), kb=round(len(raw) / 1024), title=html.unescape(title)[:120],
                   https=final.startswith("https://"), mobile="name=\"viewport\"" in low or "name='viewport'" in low,
                   town_in_title=town.lower() in head,
                   service_in_title=any(s.lower() in head for s in services),
                   schema=any(f'"{t}"' in ld for t in SCHEMA_TYPES),
                   booking=any(b in low for b in BOOKING), tap_to_call="href=\"tel:" in low or "href='tel:" in low)
    except Exception as e:  # a site that won't load is itself a finding; record and move on
        out["error"] = str(e)[:120]
    cf.parent.mkdir(parents=True, exist_ok=True)
    cf.write_text(json.dumps(out, indent=1))
    return out


def findings(lead):
    """(ok, label, plain-words detail) rows for the audit, and the fixes that follow from the failures."""
    s, rows, fixes = lead.get("site"), [], []
    hit = lead["hits"][0]
    most = max(hit["above"], key=lambda a: a["reviews"])
    if most["reviews"] > lead["reviews"]:
        fixes.append(f"Close the review gap: {most['name']} has {most['reviews']:,} Google reviews to your "
                     f"{lead['reviews']:,}. A text or QR card after each appointment does most of this.")
    if s and s.get("ok"):
        def row(ok, label, good, bad, fix=None):
            rows.append((ok, label, good if ok else bad))
            if not ok and fix:
                fixes.append(fix)
        row(s["town_in_title"] and s["service_in_title"], "Page title and heading",
            "Names both the treatment and the town.",
            f"The homepage title is \"{s['title'] or 'empty'}\". It doesn't clearly say what you do and where.",
            f"Put the treatment and the town (\"{hit['service'].title()} in {lead['town']}\") in the page title and "
            f"main heading, and give each main treatment its own page.")
        row(s["schema"], "Clinic details Google and AI assistants can read",
            "Structured clinic data found.", "No structured clinic data found on the homepage.",
            "Add structured data (services, hours, address, reviews) so Google and AI assistants can read the clinic "
            "properly instead of guessing.")
        row(s["booking"], "Booking or enquiry on the homepage", "A way to book is on the homepage.",
            "No clear way to book or enquire online on the homepage.",
            "Put a booking or enquiry button at the top of the homepage, so a search turns into an appointment.")
        row(s["tap_to_call"], "Tap to call on a phone", "The phone number can be tapped.",
            "The phone number can't be tapped to call.", "Make the phone number tap-to-call.")
        row(s["mobile"], "Built for phones", "The page is set up for phones.", "The page isn't set up for phones.",
            "Make the site work properly on phones, where most local searches happen.")
        row(s["seconds"] <= 3, "Speed", f"The homepage loaded in {s['seconds']}s in our test.",
            f"The homepage took {s['seconds']}s to load in our test.",
            f"Speed up the homepage ({s['seconds']}s in our test); slow pages lose visitors before they see anything.")
        row(s["https"], "Secure connection", "Uses https.", "Not on https; browsers show a warning.", "Move the site to https.")
    elif s and s.get("error"):
        rows.append((False, "Homepage", "The homepage didn't load when we tested it."))
        fixes.append("Fix the homepage: it didn't load when we tested it.")
    if not s:
        fixes.append(f"Give each main treatment its own page that names {lead['town']}, so Google has a clear page to rank.")
    fixes.append("Keep the Google profile active: treatments listed, new photos and a reply to every review.")
    return rows, fixes[:4]


# ---------------------------------------------------------------- 4. audit page
PAGE = """<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow"><title>Google visibility check: {name}</title>
<meta property="og:title" content="Google visibility check: {name}"><meta property="og:description" content="{og}">
<style>
:root{{--ink:#16202b;--soft:#5b6875;--line:#e3e7ec;--paper:#f7f5f1;--card:#fff;--you:#0f6d5c;--you-bg:#e6f3f0;--bad:#b4442c;--ok:#0f6d5c}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 Georgia,"Times New Roman",serif}}
main{{max-width:720px;margin:0 auto;padding:28px 16px 56px}}
.k{{font:600 12px/1.2 -apple-system,"Segoe UI",Roboto,sans-serif;letter-spacing:.09em;text-transform:uppercase;color:var(--soft)}}
h1{{font-size:30px;line-height:1.15;margin:8px 0 6px}}h2{{font-size:20px;margin:0 0 4px}}
p{{margin:0 0 12px}}.lede{{font-size:18px;color:var(--soft)}}
section{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:20px;margin-top:16px}}
.sans,table,li,.btn,.foot{{font-family:-apple-system,"Segoe UI",Roboto,sans-serif}}
table{{width:100%;border-collapse:collapse;font-size:15px;margin-top:10px}}
th{{text-align:left;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--soft);padding:6px 8px;border-bottom:1px solid var(--line)}}
td{{padding:9px 8px;border-bottom:1px solid var(--line);vertical-align:top}}td.n,th.n{{text-align:right;white-space:nowrap}}
tr.you td{{background:var(--you-bg);font-weight:600}}tr.you td:first-child{{color:var(--you)}}
.q{{font-style:italic}}ul{{list-style:none;margin:10px 0 0;padding:0}}li{{padding:9px 0 9px 30px;border-bottom:1px solid var(--line);position:relative;font-size:15px}}
li:last-child{{border-bottom:0}}li b{{display:block}}li::before{{position:absolute;left:0;top:9px;width:20px;height:20px;border-radius:50%;text-align:center;font:700 13px/20px sans-serif;color:#fff}}
li.ok::before{{content:"\\2713";background:var(--ok)}}li.no::before{{content:"!";background:var(--bad)}}
ol{{margin:10px 0 0;padding-left:22px}}ol li{{padding:6px 0;border:0;list-style:decimal}}
.btn{{display:inline-block;margin-top:6px;background:var(--you);color:#fff;text-decoration:none;font-weight:600;padding:12px 18px;border-radius:8px}}
.foot{{font-size:13px;color:var(--soft);margin-top:18px}}
</style></head><body><main>
<div class="k">Google visibility check · {date}</div>
<h1>{name}</h1>
<p class="lede">{lede}</p>
<section><h2>Where you come up</h2>
<p class="sans">Searches on Google Maps, and who is in the first three places.</p>
{searches}</section>
<section><h2>Reviews: you and the three above you</h2>
<p class="sans">For <span class="q">{query}</span>.</p>
<table><tr><th>Place</th><th>Clinic</th><th class="n">Rating</th><th class="n">Reviews</th></tr>{compare}</table>
{verdict}</section>
{site}{ai}
<section><h2>What I'd fix first</h2><ol>{fixes}</ol></section>
<section><h2>Want this done for you?</h2>
<p class="sans">I'm {me}. I do this work for clinics month to month: the site, the Google profile, reviews and how the clinic shows up in AI answers. No contract. Message me and I'll walk you through this page in ten minutes.</p>
<a class="btn" href="https://wa.me/{wa}?text={wa_text}">Message {me} on WhatsApp</a></section>
<p class="foot">Positions are from Google Maps searches run on {date} and can vary with the searcher's location. Ratings and review counts are from Google on the same date.{site_note}</p>
</main></body></html>
"""


def esc(s):
    return html.escape(str(s), quote=True)


def audit_html(lead, cfg, today):
    hit = lead["hits"][0]
    searches = "<table><tr><th>Search</th><th class=\"n\">You</th><th>First three</th></tr>" + "".join(
        f"<tr><td class=\"q\">{esc(h['query'])}</td><td class=\"n\">{ordinal(h['position'])}</td>"
        f"<td>{esc(', '.join(a['name'] for a in h['above']))}</td></tr>" for h in lead["hits"]) + "</table>"
    compare = "".join(f"<tr><td>{ordinal(i + 1)}</td><td>{esc(a['name'])}</td><td class=\"n\">{a['rating']:.1f}</td>"
                      f"<td class=\"n\">{a['reviews']:,}</td></tr>" for i, a in enumerate(hit["above"]))
    compare += (f"<tr class=\"you\"><td>{ordinal(hit['position'])}</td><td>{esc(lead['name'])} (you)</td>"
                f"<td class=\"n\">{lead['rating']:.1f}</td><td class=\"n\">{lead['reviews']:,}</td></tr>")
    n = outdone(hit, lead["reviews"])
    verdict = (f"<p class=\"sans\" style=\"margin-top:12px\">You have more reviews than {'all three of the' if n == 3 else 'two of the three' if n == 2 else 'one of the three'} clinics above you. "
               f"Your reputation isn't what's holding you back.</p>" if n else
               "<p class=\"sans\" style=\"margin-top:12px\">The clinics above you have more reviews. That gap is the first thing to close.</p>")
    rows, fixes = findings(lead)
    site = ""
    if rows:
        site = ("<section><h2>Your website</h2><p class=\"sans\">What a phone sees on your homepage.</p><ul>"
                + "".join(f"<li class=\"{'ok' if ok else 'no'}\"><b>{esc(label)}</b>{esc(detail)}</li>" for ok, label, detail in rows)
                + "</ul></section>")
    ai = ""
    if lead.get("ai_mentioned") in (True, False):
        said = "named you" if lead["ai_mentioned"] else "did not name you"
        ai = (f"<section><h2>AI answers</h2><p class=\"sans\">I asked ChatGPT for the best clinics for "
              f"{esc(hit['service'])} in {esc(lead['town'])}. It {said}.</p></section>")
    lede = (f"You came up {ordinal(hit['position'])} for “{hit['query']}”. "
            f"Most people searching pick from the first three.")
    return PAGE.format(
        name=esc(lead["name"]), date=today, lede=esc(lede), og=esc(lede), searches=searches, query=esc(hit["query"]),
        compare=compare, verdict=verdict, site=site, ai=ai, fixes="".join(f"<li>{esc(f)}</li>" for f in fixes),
        me=esc(cfg["your_name"]), wa=re.sub(r"\D", "", cfg["your_whatsapp"]),
        wa_text=urllib.parse.quote(f"Hi {cfg['your_name']}, I saw the Google check for {lead['name']}."),
        site_note=" Website checks are of the homepage only, loaded as a phone would." if rows else "")


# ---------------------------------------------------------------- 5. messages + sheet
def messages(lead, cfg):
    hit, me = lead["hits"][0], cfg["your_name"]
    above = ", ".join(f"{a['name']} ({a['rating']:.1f} from {a['reviews']:,} reviews)" for a in hit["above"])
    n = outdone(hit, lead["reviews"])
    mine = f"{lead['rating']:.1f} from {lead['reviews']:,}"
    if n >= 2:
        gap = f"You have more reviews than {'all three' if n == 3 else 'two of them'} ({mine}), so it isn't your reputation."
    elif n == 1:
        beaten = next(a for a in hit["above"] if a["reviews"] < lead["reviews"])
        gap = f"You have more reviews than {beaten['name']} ({mine}) and it still comes up above you."
    else:
        gap = f"You're rated {mine}, so the gap can be closed."
    opener = (f"Hi, is this {lead['name']}? I'm {me}. I searched Google Maps for \"{hit['query']}\" and you came up "
              f"{ordinal(hit['position'])}. The three above you: {above}. {gap} I've put together a short page on where "
              f"you come up and what I'd fix first. Shall I send it over? It's free, and just say no if you'd rather not.")
    after_yes = (f"Here it is: {lead['audit_url']}\n\nIt shows where you come up for {len(lead['hits'])} "
                 f"search{'es' if len(lead['hits']) != 1 else ''}, who is above you, and the things I'd fix first. "
                 f"If it's useful, I can walk you through it in ten minutes whenever suits.")
    setup = f", plus £{cfg['setup']} to set up" if cfg.get("setup") else ""
    price = (f"I do it month to month: £{cfg['monthly']} a month{setup}, no contract, cancel any time. That covers the "
             f"site, your Google profile, reviews and how you show up in AI answers, with a report each month of the "
             f"calls and enquiries it brought in.")
    return opener, after_yes, price


def write_sheet(leads, cfg, out, per_day):
    rows, day_count = [], {}
    queue = [l for l in leads if l["whatsapp"] and not l["status"]]
    for i, l in enumerate(queue):
        l["_day"] = i // per_day + 1
    for l in leads:
        hit = l["hits"][0]
        if l["status"] == "declined":
            opener = after_yes = price = ""
        else:
            opener, after_yes, price = messages(l, cfg)
        day = l.pop("_day", "")
        day_count[day] = day_count.get(day, 0) + 1
        rows.append({
            "send_day": day, "status": l["status"], "clinic": l["name"], "niche": l["niche"], "town": l["town"],
            "phone": l["phone"], "channel": "WhatsApp" if l["whatsapp"] else "Landline: call or email",
            "whatsapp_link": (f"https://wa.me/{l['whatsapp']}?text={urllib.parse.quote(opener)}"
                              if l["whatsapp"] and opener and not l["status"] else ""),
            "website": l["website"], "search": hit["query"], "position": hit["position"],
            "rating": l["rating"], "reviews": l["reviews"],
            "above": "; ".join(f"{a['name']} {a['rating']:.1f}/{a['reviews']}" for a in hit["above"]),
            "1_opener": opener, "2_after_they_say_yes": after_yes, "3_if_they_ask_price": price,
            "audit": l["audit_url"], "ai_check_prompt": f"Best clinics for {hit['service']} in {l['town']}? Name three.",
            "slug": l["slug"], "notes": l.get("notes", "")})
    rows.sort(key=lambda r: (r["send_day"] == "", r["send_day"] or 0))
    out.mkdir(exist_ok=True)
    path = out / "clinics.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["clinic"])
        w.writeheader()
        w.writerows(rows)
    wa = sum(v for k, v in day_count.items() if k != "")
    print(f"Wrote {path}: {len(rows)} clinics, {wa} to send on WhatsApp over {max([k for k in day_count if k != ''], default=0)} "
          f"day(s) at {per_day} a day, {sum(1 for l in leads if not l['whatsapp'])} landline-only.")


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(ROOT / "scripts" / "clinic-prospects.json"))
    ap.add_argument("--root", default=str(ROOT), help="where cache/, out/, demos/ and clinic_leads.json live")
    ap.add_argument("--limit", type=int, help="most new clinics to add this run")
    ap.add_argument("--per-day", type=int, help="WhatsApp openers per send day (default from config, 40)")
    ap.add_argument("--max-requests", type=int, default=200, help="cap on paid Google searches this run")
    ap.add_argument("--check-sites", action="store_true", help="load each clinic's homepage for the website checks")
    ap.add_argument("--dry-run", action="store_true", help="search and rank only; nothing written")
    ap.add_argument("--mark", action="append", default=[], metavar="SLUG:STATUS", help="|".join(s for s in STATUSES if s))
    ap.add_argument("--sent", type=int, nargs="?", const=-1, metavar="N",
                    help="mark the next N WhatsApp rows (default: one day's batch) as contacted; the rest move up a day")
    a = ap.parse_args()
    root = Path(a.root)
    cache, out, store = root / "cache" / "clinics", root / "out", root / "clinic_leads.json"
    cfg = json.loads(Path(a.config).read_text())
    for k, v in dict(min_position=4, max_position=12, min_rating=4.5, min_reviews=15, per_day=40, limit=200,
                     exclude_types=["hospital", "pharmacy", "drugstore"], skip=[]).items():
        cfg.setdefault(k, v)
    per_day = a.per_day or cfg["per_day"]
    leads = json.loads(store.read_text()) if store.exists() else []
    by_slug = {l["slug"]: l for l in leads}

    if a.mark or a.sent:
        for m in a.mark:
            slug, _, status = m.partition(":")
            if slug not in by_slug or status not in STATUSES:
                sys.exit(f"--mark {m}: unknown slug or status (statuses: {', '.join(s for s in STATUSES if s)})")
            by_slug[slug]["status"] = status
        if a.sent:
            batch = [l for l in leads if l["whatsapp"] and not l["status"]][:per_day if a.sent < 0 else a.sent]
            for l in batch:
                l["status"] = "contacted"
                l["contacted_on"] = datetime.date.today().isoformat()
            print(f"Marked {len(batch)} clinics as contacted.")
        store.write_text(json.dumps(leads, indent=2, ensure_ascii=False) + "\n")
        return write_sheet(leads, cfg, out, per_day)

    key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    if not key and not any((cache / "places").glob("*.json")):
        sys.exit("Set GOOGLE_MAPS_API_KEY first (Places API (New)).")
    budget = Budget(a.max_requests)
    found, rej = collect(cfg, key, budget, cache)
    taken = {l["place_id"] for l in leads} | set(by_slug)
    skip = {slugify(s) for s in cfg["skip"]}
    fresh = [e for pid, e in found.items() if pid not in taken and slugify(name_of(e["place"])) not in skip]
    fresh.sort(key=score, reverse=True)
    pick = fresh[:a.limit or cfg["limit"]]
    print(f"\n{len(found)} clinics qualify, {len(fresh)} new, adding {len(pick)}. {budget.used} Google searches used.")
    for niche in cfg["niches"]:
        grp = [e for e in fresh if e["niche"] == niche]
        wa = sum(1 for e in grp if uk_mobile(e["place"].get("nationalPhoneNumber")))
        print(f"  {niche}: {len(grp)} new, {wa} WhatsApp-able, {len(grp) - wa} landline-only")
    print("  skipped: " + ", ".join(f"{v} {k}" for k, v in sorted(rej.items(), key=lambda x: -x[1])))
    for e in pick[:25]:
        p, h = e["place"], best_hit(e)
        print(f"  {ordinal(h['position']):>4} for \"{h['query']}\"  ·  {name_of(p)}  ·  {p.get('rating')}★ "
              f"{p.get('userRatingCount')}  ·  beats {outdone(h, p.get('userRatingCount') or 0)}/3 on reviews"
              f"{'  · WhatsApp' if uk_mobile(p.get('nationalPhoneNumber')) else ''}")
    if a.dry_run:
        return print("\nDry run: nothing written.")

    today = datetime.date.today().strftime("%-d %B %Y")
    for e in pick:
        p = e["place"]
        hits = sorted(e["hits"], key=lambda h: h is not best_hit(e))  # best search first, rest in found order
        town = town_of(p) or hits[0]["town"]
        slug = base = slugify(f"{name_of(p)} {town}" if slugify(town) not in slugify(name_of(p)) else name_of(p))
        while slug in by_slug:
            slug = base + "-2" if slug == base else slug + "-2"
        lead = {"slug": slug, "place_id": p["id"], "name": name_of(p), "niche": e["niche"], "town": town,
                "phone": p["nationalPhoneNumber"], "whatsapp": uk_mobile(p["nationalPhoneNumber"]),
                "website": p["websiteUri"], "google_url": p.get("googleMapsUri", ""),
                "rating": round(p.get("rating") or 0, 1), "reviews": p.get("userRatingCount") or 0, "hits": hits,
                "audit_url": f"{cfg['base_url'].rstrip('/')}/audit-{slug}/", "status": "", "notes": ""}
        lead["site"] = check_site(p["websiteUri"], town, cfg["niches"][e["niche"]]["services"], cache, a.check_sites)
        by_slug[slug] = lead
        leads.append(lead)
    for l in leads:  # rebuild every audit so edits to clinic_leads.json (e.g. ai_mentioned) show up
        if l["status"] != "declined":
            d = root / "demos" / f"audit-{l['slug']}"
            d.mkdir(parents=True, exist_ok=True)
            (d / "index.html").write_text(audit_html(l, cfg, today), encoding="utf-8")
    store.write_text(json.dumps(leads, indent=2, ensure_ascii=False) + "\n")
    write_sheet(leads, cfg, out, per_day)


if __name__ == "__main__":
    main()
