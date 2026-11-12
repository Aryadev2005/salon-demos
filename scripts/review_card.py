#!/usr/bin/env python3
"""Make a printable Google-review QR card (A6, 1240x1748 px) for a business.

    python3 scripts/review_card.py --name "Eden Hair" --place-id ChIJ... --out cards/eden-hair.png [--trade]

The QR opens Google's "write a review" box for that business. Use it as the free gift in outreach.
"""
import argparse
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont

F = "/usr/share/fonts/truetype/dejavu/"


def font(name, size):
    try:
        return ImageFont.truetype(F + name, size)
    except OSError:
        return ImageFont.load_default()


def fit(draw, text, fname, size, max_w):
    while size > 28:
        f = font(fname, size)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 4
    return font(fname, size)


def card(name, place_id, out, trade=False, accent=(36, 36, 36)):
    W, H = 1240, 1748
    im = Image.new("RGB", (W, H), (250, 248, 244))
    d = ImageDraw.Draw(im)
    d.rectangle([40, 40, W - 40, H - 40], outline=accent, width=4)
    f_name = fit(d, name, "DejaVuSerif-Bold.ttf", 92, W - 200)
    d.text((W / 2, 230), name, font=f_name, fill=accent, anchor="mm")
    lead = "Happy with the work?" if trade else "Loved your visit?"
    d.text((W / 2, 380), lead, font=font("DejaVuSans.ttf", 64), fill=(60, 60, 60), anchor="mm")
    d.text((W / 2, 460), "Scan to leave us a Google review", font=font("DejaVuSans.ttf", 48), fill=(90, 90, 90), anchor="mm")
    url = f"https://search.google.com/local/writereview?placeid={place_id}"
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=2, box_size=20)
    qr.add_data(url)
    qr.make(fit=True)
    q = qr.make_image(fill_color=accent, back_color=(250, 248, 244)).convert("RGB").resize((720, 720), Image.NEAREST)
    im.paste(q, ((W - 720) // 2, 560))
    stars = "★ ★ ★ ★ ★"
    d.text((W / 2, 1390), stars, font=font("DejaVuSans.ttf", 84), fill=(214, 160, 40), anchor="mm")
    d.text((W / 2, 1500), "It takes 30 seconds and really helps us. Thank you!", font=font("DejaVuSans.ttf", 40),
           fill=(90, 90, 90), anchor="mm")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    im.save(out, "PNG", optimize=True)
    return url


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True)
    ap.add_argument("--place-id", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--trade", action="store_true")
    a = ap.parse_args()
    print(card(a.name, a.place_id, a.out, a.trade))
