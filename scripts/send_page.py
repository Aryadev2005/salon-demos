#!/usr/bin/env python3
"""Turn a clinics sheet into a simple page: one card per clinic, with copy buttons.

    python3 scripts/send_page.py out/clinics_us.csv          # today's batch (send_day 1)
    python3 scripts/send_page.py out/clinics.csv --day 2     # a later batch, or the UK sheet

Writes out/send-<sheet>-day<N>.html and opens it. Each card has: the WhatsApp button (opens the chat with the
message typed), and To / Subject / Email each with a Copy button for pasting into Gmail or any mail app.
Tick "Sent" as you go; ticks are remembered in this browser. The page stays on your Mac (out/ isn't uploaded).
"""
import argparse
import csv
import html
import json
import subprocess
import sys
from pathlib import Path

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title>
<style>
:root{{--ink:#17202a;--soft:#5d6874;--line:#e2e6ea;--bg:#f6f5f2;--card:#fff;--go:#0f6d5c;--wa:#1f8f4e}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,"Segoe UI",Roboto,sans-serif}}
header{{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:14px 16px;z-index:2}}
header h1{{font-size:18px;margin:0}}header p{{margin:2px 0 0;color:var(--soft);font-size:13px}}
main{{max-width:760px;margin:0 auto;padding:16px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin-bottom:14px}}
.card.done{{opacity:.45}}
.top{{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}}
.name{{font-weight:650;font-size:16px}}.meta{{color:var(--soft);font-size:13px}}
.sent{{display:flex;gap:6px;align-items:center;font-size:14px;white-space:nowrap;cursor:pointer}}
.sent input{{width:18px;height:18px}}
.field{{margin-top:12px}}.label{{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--soft);
display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}}
.box{{background:#fafaf8;border:1px solid var(--line);border-radius:6px;padding:9px 11px;white-space:pre-wrap;word-break:break-word}}
.body{{max-height:220px;overflow:auto}}
button.copy{{font:600 12px sans-serif;border:1px solid var(--go);color:var(--go);background:#fff;border-radius:6px;padding:4px 10px;cursor:pointer}}
button.copy.ok{{background:var(--go);color:#fff}}
.actions{{margin-top:12px;display:flex;gap:8px;flex-wrap:wrap}}
a.btn{{text-decoration:none;font-weight:600;font-size:14px;padding:8px 14px;border-radius:7px;color:#fff;background:var(--wa)}}
a.btn.alt{{background:#fff;color:var(--go);border:1px solid var(--go)}}
.none{{color:var(--soft);font-size:13px;margin-top:10px}}
</style></head><body>
<header><h1>{title}</h1><p>{count} clinics. WhatsApp first; if the number isn't on WhatsApp, copy the email. <span id="left"></span></p></header>
<main>{cards}</main>
<script>
const KEY = {key};
let sent = {{}};
try {{ sent = JSON.parse(localStorage.getItem(KEY) || "{{}}"); }} catch (e) {{}}
function save() {{ try {{ localStorage.setItem(KEY, JSON.stringify(sent)); }} catch (e) {{}} }}
function refresh() {{
  let left = 0;
  document.querySelectorAll(".card").forEach(c => {{
    const on = !!sent[c.dataset.slug];
    c.classList.toggle("done", on); c.querySelector(".sent input").checked = on; if (!on) left++;
  }});
  document.getElementById("left").textContent = left + " left to send.";
}}
document.querySelectorAll(".sent input").forEach(i => i.addEventListener("change", e => {{
  sent[e.target.closest(".card").dataset.slug] = e.target.checked; save(); refresh();
}}));
document.querySelectorAll("button.copy").forEach(b => b.addEventListener("click", async () => {{
  const text = document.getElementById(b.dataset.for).textContent;
  try {{ await navigator.clipboard.writeText(text); }}
  catch (e) {{ const t = document.createElement("textarea"); t.value = text; document.body.appendChild(t); t.select();
              document.execCommand("copy"); t.remove(); }}
  b.textContent = "Copied"; b.classList.add("ok"); setTimeout(() => {{ b.textContent = "Copy"; b.classList.remove("ok"); }}, 1500);
}}));
refresh();
</script></body></html>
"""


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def field(label, fid, text, cls=""):
    return (f'<div class="field"><div class="label">{label}<button class="copy" data-for="{fid}">Copy</button></div>'
            f'<div class="box {cls}" id="{fid}">{html.escape(text)}</div></div>')


def card(i, r):
    e = html.escape
    meta = f"{r['town']} · {r['search']}: {ordinal(int(r['position']))} · {r['rating']}★ from {r['reviews']} reviews"
    out = [f'<div class="card" data-slug="{e(r["slug"])}"><div class="top"><div><div class="name">{i}. {e(r["clinic"])}</div>'
           f'<div class="meta">{e(meta)} · {e(r["phone"])}</div></div>'
           f'<label class="sent"><input type="checkbox"> Sent</label></div>']
    acts = []
    if r.get("whatsapp_link"):
        acts.append(f'<a class="btn" href="{e(r["whatsapp_link"])}" target="_blank" rel="noopener">Open WhatsApp</a>')
    if r.get("website"):
        acts.append(f'<a class="btn alt" href="{e(r["website"])}" target="_blank" rel="noopener">Their website</a>')
    if acts:
        out.append('<div class="actions">' + "".join(acts) + "</div>")
    if r.get("email"):
        out.append(field("To", f"to{i}", r["email"]))
        out.append(field("Subject", f"su{i}", r.get("1_email_subject", "")))
        out.append(field("Email", f"em{i}", r.get("1_email", ""), "body"))
    else:
        out.append('<div class="none">No email found. If WhatsApp doesn\'t work, call: ' + e(r["phone"]) + "</div>")
    out.append("</div>")
    return "".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sheet", nargs="?", default="out/clinics_us.csv")
    ap.add_argument("--day", type=int, default=1, help="which send_day to show (default 1)")
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()
    src = Path(a.sheet)
    if not src.exists():
        sys.exit(f"{src} not found. Run clinic_audits.py first.")
    rows = [r for r in csv.DictReader(src.open(encoding="utf-8-sig")) if r.get("send_day") == str(a.day)]
    if not rows:
        sys.exit(f"No rows with send_day {a.day} in {src}.")
    title = f"Send day {a.day}: {src.stem.replace('_', ' ')}"
    page = PAGE.format(title=html.escape(title), count=len(rows), key=json.dumps(f"sent-{src.stem}"),
                       cards="".join(card(i, r) for i, r in enumerate(rows, 1)))
    dest = src.parent / f"send-{src.stem}-day{a.day}.html"
    dest.write_text(page, encoding="utf-8")
    print(f"Wrote {dest}: {len(rows)} clinics.")
    if not a.no_open:
        subprocess.run(["open", str(dest)], check=False)


if __name__ == "__main__":
    main()
