#!/usr/bin/env python3
"""Generate soft gradient placeholder images for a lead (for examples / layout testing).

    python3 scripts/placeholders.py <slug>

Writes every image build.py expects into demos/<slug>/img/. Needs Pillow.
Never use these for a real lead: drop the salon's real photos in instead.
"""
import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def shade(rgb, t, to=(255, 255, 255)):
    return tuple(int(c + (d - c) * t) for c, d in zip(rgb, to))


def make(path, size, base, seed, mood, dull=False):
    rnd = random.Random(seed)
    w, h = size
    light = mood == "light"
    top = shade(base, rnd.uniform(.45, .7)) if light else shade(base, rnd.uniform(.35, .55), (0, 0, 0))
    bot = shade(base, rnd.uniform(.05, .25)) if light else shade(base, rnd.uniform(.65, .8), (0, 0, 0))
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bot)))
    # soft light blobs
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    for _ in range(5):
        r = rnd.randint(int(min(w, h) * .18), int(min(w, h) * .5))
        x, y = rnd.randint(0, w), rnd.randint(0, h)
        col = shade(base, rnd.uniform(.5, .9)) if rnd.random() < .6 else shade(base, rnd.uniform(.3, .6), (0, 0, 0))
        ld.ellipse([x - r, y - r, x + r, y + r], fill=col + (rnd.randint(60, 120),))
    layer = layer.filter(ImageFilter.GaussianBlur(min(w, h) * .12))
    img = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
    if dull:
        g = img.convert("L").convert("RGB")
        img = Image.blend(img, g, .7)
    img.save(path, "JPEG", quality=78, optimize=True, progressive=True)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__.strip())
    slug = sys.argv[1]
    leads = json.loads((ROOT / "leads.json").read_text())
    lead = next((l for l in leads if l.get("slug") == slug), None)
    if not lead:
        sys.exit(f"No lead '{slug}' in leads.json")
    out = ROOT / "demos" / slug / "img"
    out.mkdir(parents=True, exist_ok=True)
    base, mood = hex2rgb(lead["accent"]), lead["mood"]
    jobs = [("hero.jpg", (1200, 1720))]
    sizes = [(1000, 1300), (1200, 900), (1000, 1250), (1400, 900), (1000, 1300), (1200, 1200)]
    for i in range(1, lead["photos"] + 1):
        jobs.append((f"g{i}.jpg", sizes[(i - 1) % len(sizes)]))
    for i, _ in enumerate(lead.get("before_after") or [], 1):
        jobs += [(f"ba{i}-before.jpg", (900, 1200)), (f"ba{i}-after.jpg", (900, 1200))]
    if lead.get("bridal"):
        jobs.append(("bridal.jpg", (1000, 1400)))
    for n, (name, size) in enumerate(jobs):
        seed = f"{slug}-{name.replace('-before', '').replace('-after', '')}"
        make(out / name, size, base, seed, mood, dull=name.endswith("-before.jpg"))
    print(f"wrote {len(jobs)} placeholder images to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
