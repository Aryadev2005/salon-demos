#!/usr/bin/env python3
"""Write hosting/<slug>/index.html for every built demo.

Each stub carries that salon's <title>, description and og:/twitter: tags (so WhatsApp, iMessage and
Facebook show the salon's name, rating and photo), then loads the real page from GitHub like
hosting/index.html does. Run after building, then redeploy hosting/ (see README).
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = "https://raw.githubusercontent.com/Aryadev2005/salon-demos/main/demos/"
LOADER = (ROOT / "hosting" / "index.html").read_text()
script = '<script src="/l.js"></script>'
style = re.search(r"<style>.*?</style>", LOADER, re.S).group(0)

n = 0
contacted = {l["slug"] for l in json.loads((ROOT / "leads.json").read_text()) if l.get("_auto") or l.get("pitch")}
for page in sorted((ROOT / "demos").glob("*/index.html")):
    slug = page.parent.name
    if slug not in contacted:
        continue
    src = page.read_text()
    title = re.search(r"<title>(.*?)</title>", src, re.S)
    if not title:
        continue
    metas = re.findall(r'<meta (?:name="(?:description|theme-color|twitter:card)"|property="og:[^"]+")[^>]*>', src)
    # og:image must be fetchable by link-preview bots: point it at GitHub's copy of the photo
    metas = [re.sub(r'(property="og:image" content=")[^"]*/img/', r"\1" + RAW + slug + "/img/", m) for m in metas]
    has_img = any('og:image"' in m for m in metas)
    if not has_img and (page.parent / "img" / "hero.jpg").exists():
        metas.append(f'<meta property="og:image" content="{RAW}{slug}/img/hero.jpg">')
    out = ROOT / "hosting" / slug / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">'
        f"<title>{title.group(1)}</title>" + "".join(metas) + style +
        "</head><body><p id=\"m\">This preview isn't available.</p>" + script + "</body></html>\n")
    n += 1
print(f"wrote {n} stubs")
