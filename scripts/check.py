#!/usr/bin/env python3
"""Screenshot a built demo at desktop and mobile width with Playwright.

    python3 scripts/check.py <slug> [<slug> ...]     (or --all)

Saves full-page shots to shots/<slug>/ (1400px and 390px wide), plus the
#review and #review-kit views, and prints any console errors or broken images.
Setup once:  pip install playwright && python3 -m playwright install chromium
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
WIDTHS = [(1400, 900), (390, 844)]


def check(page, slug):
    url = (ROOT / "demos" / slug / "index.html").resolve().as_uri()
    out = ROOT / "shots" / slug
    out.mkdir(parents=True, exist_ok=True)
    problems = []
    def on_console(m):
        if m.type != "error":
            return
        if "net::ERR" in m.text:  # offline or blocked fonts/QR/map: worth knowing, not a page bug
            print(f"  (warning) {m.text}")
        else:
            problems.append(f"console: {m.text}")
    page.on("console", on_console)
    page.on("pageerror", lambda err: problems.append(f"js error: {err}"))
    for w, h in WIDTHS:
        page.set_viewport_size({"width": w, "height": h})
        page.goto(url, wait_until="load")
        page.wait_for_timeout(600)
        # scroll through so lazy images load before the full-page shot
        height = page.evaluate("document.body.scrollHeight")
        for y in range(0, height, h // 2):
            page.evaluate(f"scrollTo(0,{y})")
            page.wait_for_timeout(120)
        page.evaluate("scrollTo(0,0)")
        page.wait_for_timeout(400)
        broken = page.evaluate("[...document.images].filter(i=>i.closest('main:not([hidden])')&&i.complete&&!i.naturalWidth).map(i=>i.getAttribute('src'))")
        problems += [f"broken image at {w}px: {b}" for b in broken]
        wide = page.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
        if wide:
            problems.append(f"horizontal scroll at {w}px")
        page.screenshot(path=str(out / f"home-{w}.png"), full_page=True)
        for view in ("review", "review-kit"):
            page.goto(url + "#" + view)
            page.wait_for_timeout(300)
            page.screenshot(path=str(out / f"{view}-{w}.png"), full_page=True)
    return problems


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__.strip())
    if args == ["--all"]:
        args = [l["slug"] for l in json.loads((ROOT / "leads.json").read_text())]
    bad = False
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for slug in args:
            if not (ROOT / "demos" / slug / "index.html").is_file():
                print(f"{slug}: not built yet, run python3 build.py {slug}")
                bad = True
                continue
            page = browser.new_page()
            probs = check(page, slug)
            page.close()
            print(f"{slug}: shots in shots/{slug}/" + ("" if not probs else "\n  - " + "\n  - ".join(dict.fromkeys(probs))))
            bad = bad or bool(probs)
        browser.close()
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
