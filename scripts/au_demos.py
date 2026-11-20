#!/usr/bin/env python3
"""Australian bridal makeup artist demos.

Reads the ranked leads (au_bridal_leads.csv from au_bridal.py) and a list of artist names, fetches each listing's
details + 5 Google photos, writes bridal-makeup entries into leads.json and records what was built in
out/au-built.json. Street addresses are left off (many artists work from home); only the suburb is shown.

    PLACES_API_KEY=... python3 scripts/au_demos.py path/to/au_bridal_leads.csv "Name one" "Name two" ...
"""
import csv, json, os, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import places_to_leads as P
from oman_demos import details

ROOT = P.ROOT
BASE = "https://salon-previews.vercel.app"
P.REGION = "AU"

HAIR = re.compile(r"\bhair\b", re.I)


def persona(name):
    services = [
        ("Bridal", ["Bridal makeup", "Bridal trial", "Bridesmaids and mothers", "On-location wedding mornings"]),
        ("Occasions", ["Formal and event makeup", "Engagement and photoshoot makeup", "Soft glam"]),
    ]
    band = ["Bride", "Bridal party", "Mothers of the bride and groom", "Trial session"]
    what = "bridal and special-occasion makeup"
    if HAIR.search(name):
        services.insert(1, ("Hair", ["Bridal hair", "Updos and styling", "Bridal party hair"]))
        what = "bridal hair and makeup"
    services.append(("Extras", ["Lashes", "Touch-up kit for the day"]))
    return dict(type="Bridal makeup artist", what=what, services=services, party=band)


def main():
    csv_path, names = sys.argv[1], sys.argv[2:]
    key = os.environ.get("PLACES_API_KEY", "")
    budget = P.Budget(120)
    cfg = {"your_name": "Aryadev", "your_whatsapp": "+91 86378 59578"}
    rows = {r["name"]: r for r in csv.DictReader(open(csv_path))}
    leads = json.loads(P.LEADS.read_text())
    by_slug = {l["slug"]: i for i, l in enumerate(leads)}
    built, skipped = [], []
    for want in names:
        match = [n for n in rows if n.lower().startswith(want.lower())]
        if not match:
            skipped.append((want, "not in leads csv")); continue
        r = rows[match[0]]
        p = details(r["place_id"], key, budget)
        n_photos = min(5, len(p.get("photos") or []))
        if n_photos < 4:
            skipped.append((want, f"only {n_photos} photos")); continue
        if not (p.get("regularOpeningHours") or {}).get("periods"):
            p["regularOpeningHours"] = {"periods": [{"open": {"day": 0, "hour": 0, "minute": 0}}]}  # treat as by appointment
        nm = p["displayName"]["text"]
        if nm.isupper():
            nm = nm.title().replace(" And ", " and ")
        nm = re.sub(r"\s+I$", "", nm)
        area, city, _ = P.address_parts(p)
        slug = P.slugify(f"{nm} {area}")[:50].strip("-") + "-au"
        paths, credits = P.fetch_photos(p, slug, key, budget, n_photos, False)
        per = persona(nm)
        P.PERSONA[p.get("primaryType") or "makeup_artist"] = per
        lead = P.make_lead(p, slug, cfg, P.accent_from(paths), credits)
        comp = {c.get("types", [None])[0]: c.get("shortText") for c in p.get("addressComponents") or []}
        state = next((c.get("shortText") for c in p.get("addressComponents") or [] if "administrative_area_level_1" in c.get("types", [])), "")
        lead["name"] = nm
        lead["address"] = ", ".join(x for x in [area, state] if x)
        lead["country"], lead["lang"] = "Australia", "en-AU"
        lead["bridal"] = {"nav": "Weddings", "kicker": "Wedding season",
                          "title": "Lock in your wedding date early.",
                          "text": "Spring and summer weekends book out months ahead. Send us your date and we'll hold it while we plan your trial.",
                          "packages": [{"name": x} for x in per["party"]]}
        lead["subline"] = lead["subline"].replace(p["displayName"]["text"], nm)
        lead["_market"] = "au"
        if slug in by_slug:
            leads[by_slug[slug]] = lead
        else:
            by_slug[slug] = len(leads); leads.append(lead)
        built.append({"slug": slug, "name": nm, "csv_name": match[0], "link": f"{BASE}/{slug}/"})
    P.LEADS.write_text(json.dumps(leads, indent=1, ensure_ascii=False) + "\n")
    (ROOT / "out").mkdir(exist_ok=True)
    json.dump({"built": built, "skipped": skipped}, open(ROOT / "out" / "au-built.json", "w"), indent=1, ensure_ascii=False)
    print(f"{len(built)} built, {budget.used} Google requests; skipped: {skipped}")


if __name__ == "__main__":
    main()
