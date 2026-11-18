#!/usr/bin/env python3
"""Oman salon demos: take the ranked Oman leads (oman_leads.csv from oman_salons.py), fetch each salon's
details + 5 Google photos, write Oman-flavoured entries into leads.json and build them.

    PLACES_API_KEY=... python3 scripts/oman_demos.py path/to/oman_leads.csv --count 30

Skips barbers (walk-in businesses) and salons with fewer than 5 photos or no opening hours.
Writes out/oman-outreach.csv: salon, WhatsApp number, demo link, first message.
"""
import argparse, csv, json, os, re, sys, urllib.parse, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import places_to_leads as P

ROOT = P.ROOT
BASE = "https://salon-previews.vercel.app"
P.REGION = "OM"
P.MOBILE["OM"] = ("968", r"0[79]\d{7}")
P.COUNTRY["OM"] = ("Oman", "en-OM")

MEN = re.compile(r"\b(men|man|gents?|barber|groom|fellas|guys?)\b|رجال|حلاقة", re.I)

OMAN = {
    "ladies": dict(type="Ladies' salon", what="hair, makeup and bridal styling",
        services=[("Hair", ["Cut and blow-dry", "Hair colour", "Keratin and protein treatments", "Hair styling"]),
                  ("Beauty", ["Makeup", "Henna", "Threading and waxing", "Facials"]),
                  ("Nails", ["Manicure and pedicure", "Gel polish", "Nail extensions"])],
        band=["Bridal makeup", "Bridal hair", "Henna nights", "Bridesmaids and family"]),
    "nails": dict(type="Nail salon", what="gel, extensions and nail art",
        services=[("Nails", ["Gel polish", "Nail extensions", "Nail art", "Manicure"]),
                  ("Feet", ["Pedicure", "Gel toes"]), ("Beauty", ["Lash extensions", "Threading"])],
        band=["Bridal nails", "Henna-day nails", "Bridesmaids and family"]),
    "spa": dict(type="Spa", what="facials, Moroccan bath and body treatments",
        services=[("Spa", ["Moroccan bath", "Body scrub", "Facials", "Relaxing treatments"]),
                  ("Beauty", ["Manicure and pedicure", "Waxing", "Hair treatments"])],
        band=["Pre-wedding spa day", "Moroccan bath and scrub", "Bridal glow facial"]),
    "men": dict(type="Men's salon and spa", what="haircuts, beard styling and grooming",
        services=[("Hair and beard", ["Haircut", "Beard trim and shape", "Hair and beard colour", "Kids' cut"]),
                  ("Grooming", ["Facials", "Moroccan bath", "Manicure and pedicure"])],
        band=["Groom package", "Groom's party", "Pre-wedding grooming"]),
}


def persona(name, ptype):
    if MEN.search(name):
        return OMAN["men"]
    if ptype == "nail_salon":
        return OMAN["nails"]
    if ptype == "spa":
        return OMAN["spa"]
    return OMAN["ladies"]


def details(pid, key, budget):
    cf = P.CACHE / f"details-{pid}.json"
    if cf.exists():
        return json.loads(cf.read_text())
    fields = ",".join(f.replace("places.", "") for f in P.FIELDS.split(",") if f != "nextPageToken")
    req = urllib.request.Request(f"{P.API}/places/{pid}?languageCode=en",
                                 headers={"X-Goog-Api-Key": key, "X-Goog-FieldMask": fields})
    raw, _ = P.http(req, budget, f"details {pid}")
    P.CACHE.mkdir(parents=True, exist_ok=True)
    cf.write_text(raw.decode())
    return json.loads(raw)


def latin_name(name):
    parts = [w for w in re.split(r"\s+", name) if re.search(r"[A-Za-z]", w)]
    return " ".join(parts).strip(" -|()") or name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("leads_csv")
    ap.add_argument("--count", type=int, default=30)
    ap.add_argument("--max-requests", type=int, default=260)
    a = ap.parse_args()
    key = os.environ.get("PLACES_API_KEY", "")
    budget = P.Budget(a.max_requests)
    cfg = {"your_name": "Aryadev", "your_whatsapp": "+91 86378 59578"}

    leads = json.loads(P.LEADS.read_text())
    by_slug = {l["slug"]: i for i, l in enumerate(leads)}
    rows, built, skipped = [], [], []
    for r in csv.DictReader(open(a.leads_csv)):
        if len(built) >= a.count:
            break
        if r["ptype"] == "barber_shop":
            skipped.append((r["name"], "barber")); continue
        p = details(r["place_id"], key, budget)
        if len(p.get("photos") or []) < 5:
            skipped.append((r["name"], "fewer than 5 photos")); continue
        if not (p.get("regularOpeningHours") or {}).get("periods"):
            skipped.append((r["name"], "no opening hours")); continue
        nm = latin_name(p["displayName"]["text"])
        area, city, _ = P.address_parts(p)
        slug = P.slugify(f"{nm} {area or city} oman")[:60].strip("-")
        paths, credits = P.fetch_photos(p, slug, key, budget, 5, False)
        accent = P.accent_from(paths)
        per = persona(p["displayName"]["text"], p.get("primaryType", ""))
        P.PERSONA[p.get("primaryType") or "hair_salon"] = dict(type=per["type"], what=per["what"],
                                                                services=per["services"], party=per["band"])
        lead = P.make_lead(p, slug, cfg, accent, credits)
        lead["name"] = nm
        lead["country"], lead["lang"] = "Oman", "en-OM"
        lead["bridal"] = {"nav": "Weddings", "kicker": "Wedding season",
                          "title": "Book your wedding look early.",
                          "text": "Winter is wedding season. Bridal, henna-night and family appointments fill up weeks ahead, so send us your date and we'll hold it for you.",
                          "packages": [{"name": x} for x in per["band"]]}
        lead["subline"] = lead["subline"].replace(p["displayName"]["text"], nm)
        lead["highlights"][1] = f"Specialists in {per['what']}."
        lead["_market"] = "oman"
        if slug in by_slug:
            leads[by_slug[slug]] = lead
        else:
            by_slug[slug] = len(leads); leads.append(lead)
        built.append(slug)
        link = f"{BASE}/{slug}/"
        rows.append({"#": len(built), "salon": nm, "area": r["area"], "whatsapp": r["phone"],
                     "wa_link": r["whatsapp"], "rating": r["rating"], "reviews": r["reviews"],
                     "rank": r["rank"], "search": r["search"], "demo": link,
                     "weaker_competitors_above": r["weaker_competitors_above"]})
    P.LEADS.write_text(json.dumps(leads, indent=1, ensure_ascii=False) + "\n")
    json.dump({"built": built, "rows": rows, "skipped": skipped},
              open(ROOT / "out" / "oman-built.json", "w"), indent=1, ensure_ascii=False)
    print(f"{len(built)} leads written, {budget.used} Google requests; skipped: {skipped}")


if __name__ == "__main__":
    main()
