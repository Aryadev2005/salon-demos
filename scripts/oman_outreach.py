#!/usr/bin/env python3
"""Write out/oman-top30.csv: demo link, WhatsApp number and the two pitch messages for each built Oman demo.

    python3 scripts/oman_outreach.py path/to/oman_leads.csv
"""
import csv, json, sys, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
b = json.load(open(ROOT / "out" / "oman-built.json"))
L = {l["slug"]: l for l in json.load(open(ROOT / "leads.json"))}
full = {r["place_id"]: r for r in csv.DictReader(open(sys.argv[1]))}
rows = []
for i, slug in enumerate(b["built"], 1):
    l = L[slug]; f = full[l["place_id"]]
    first = f["weaker_competitors_above"].split("; ")[0]
    cname = first.split(" (")[0]; crev = first.split("★, ")[1].split(" reviews")[0]
    q = f["search"].replace(" Oman", ""); n = int(f["weaker_competitors_outranking"])
    m1 = (f"Hi {l['name']} team! I searched \"{q}\" on Google Maps. You're #{f['rank']}, behind "
          f"{'a salon' if n == 1 else str(n) + ' salons'} with fewer reviews than your {f['reviews']}, like {cname} ({crev} reviews). "
          "They have a website and you don't, so Google shows them first and they get those bookings. "
          "I made you a free preview of what your site could look like. Can I send you the link?")
    link = f"https://salon-previews.vercel.app/{slug}/"
    m2 = (f"Here it is: {link}\nIt uses your own Google photos, hours and reviews, and clients can pick a service and book "
          "with you on WhatsApp. If you like it, I'll set it up on your own domain and link it to your Google listing so you "
          "show up higher. You only pay once it's live and you're happy.")
    wa = l.get("whatsapp", "")
    rows.append({"#": i, "Salon": l["name"], "Area": l["area"], "Rating": f["rating"], "Reviews": f["reviews"],
                 "WhatsApp number": ("'" + wa) if wa else ("Landline '" + f["phone"] if f["phone"] else "No number"),
                 "Contact via": "WhatsApp" if wa else ("Call (landline)" if f["phone"] else
                                ("Facebook" if "facebook" in f["current_link"] else "Fresha / Instagram")),
                 "Demo link": link, "Message 1 (no link)": m1, "Message 2 (after yes)": m2,
                 "Send message 1": f"https://wa.me/{wa.lstrip('+')}?text={urllib.parse.quote(m1)}" if wa else f["current_link"],
                 "Status": "Not contacted"})
with open(ROOT / "out" / "oman-top30.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(f"{len(rows)} rows -> out/oman-top30.csv")
