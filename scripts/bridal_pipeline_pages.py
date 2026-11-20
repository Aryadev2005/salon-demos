#!/usr/bin/env python3
"""Photo-free bridal booking-pipeline demos, built from the Glam by Zetta page.

For artists with no Google listing (so no Google photos): the hero shows a sample wedding-morning card
instead of photos, and the portfolio section is a marked placeholder for their Instagram work.

    python3 scripts/bridal_pipeline_pages.py
"""
import html, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = (ROOT / "demos/glam-by-zetta-darra-au/index.html").read_text()

ARTISTS = [
    dict(
        slug="gaetana-marjas-findon-au", name="Gaetana Marjas", mono="G", who="Gaetana",
        tagline="Hair &amp; makeup artistry · Adelaide", kicker="Bridal hair &amp; makeup · Findon, Adelaide",
        h1="Award-winning <em>bridal</em> hair and makeup, booked in two minutes.",
        lead="Elegant, timeless hair and makeup for brides, bridesmaids and mums, in Gaetana's Findon studio or at your venue anywhere in Adelaide. Tell her about your day and she'll come back with availability and a quote.",
        facts=[("ABIA Winner", "Best Bridal Make-Up, SA"), ("10 years", "in weddings"), ("Mobile", "or Findon studio")],
        svc_mode="both", ig="gaetanamarjas", region="Adelaide",
        hero_media=[("img", "sarah-lewis", "Bride and groom walking hand in hand"), ("video", "reel-fluff", "Bridal hair being styled"), ("img", "olive-grove", "Bride in an olive grove")],
        gallery=[("video", "reel-sarah", "Sarah's wedding at Stoney Creek Estate"), ("img", "sarah-lewis", "Sarah and Lewis at Stoney Creek Estate"),
                 ("img", "olive-twirl", "Bride twirling her gown"), ("img", "on-the-lawn", "Bride on the lawn with her bouquet"),
                 ("video", "reel-fluff", "Sleek, then fluff, then gorgeous")],
        award_img="award",
        title="Gaetana Marjas · Bridal hair &amp; makeup, Adelaide",
        desc="Award-winning bridal hair and makeup by Gaetana Marjas, Findon studio or mobile across Adelaide. Check your date and plan your wedding morning.",
        proof_kicker="Recognition", proof_h="Adelaide's award-winning bridal artist.",
        proof=[("ABIA Winner", "Best Bridal Make-Up Artist, South Australia"),
               ("10 years", "in the wedding industry, specialising in bridal hair and makeup"),
               ("Studio or mobile", "Home studio in Findon, or at your home, hotel or venue across Adelaide")],
        quotes=[("“Gaetana is AMAZING! She knew exactly what I wanted and delivered!”", "Oneflare review")],
        venue_ph="Venue, hotel or home, and suburb",
        samples=[("Sophie R.", 210, "Mount Lofty House", 6, "Hair & makeup", True, ["Soft glam"], 0),
                 ("Ella M.", 150, "Home, Glenelg", 4, "Hair & makeup", True, ["Up-do"], 1),
                 ("Chloe D.", 95, "Adelaide Oval", 3, "Makeup only", True, ["Natural & fresh"], 2),
                 ("Isabella T.", 50, "Studio, Findon", 5, "Hair & makeup", False, ["Soft waves"], 3),
                 ("Lucy H.", -12, "Penfolds Magill Estate", 4, "Hair & makeup", True, ["Half-up"], 4)],
    ),
    dict(
        slug="kxhairdesign-melbourne-au", name="Kxhairdesign", mono="K", who="Kelly",
        tagline="Bridal hair by Kelly · Melbourne", kicker="Bridal hair · Melbourne &amp; surrounds",
        h1="Bridal hair that <em>lasts all day</em>, booked in two minutes.",
        lead="Soft waves, up-dos and half-ups for brides and their bridal party, by Kelly. Mobile across Melbourne and up to two hours out. Tell Kelly about your day and she'll come back with availability and a quote.",
        facts=[("5.0 ★", "24 Easy Weddings reviews"), ("8+ years", "bridal hair"), ("Mobile", "Melbourne + 2 hrs")],
        svc_mode="hair", ig="kxhairdesign", region="Melbourne",
        hero_media=[("img", "ponytail", "Bride's sleek high ponytail with glossy waves"), ("video", "reel-ready", "Bride's half-up waves on the wedding morning"), ("img", "waves-trial", "Blonde Hollywood waves at a bridal trial")],
        gallery=[("video", "reel-wedding", "Wedding day in Melbourne"), ("img", "ponytail", "Sleek high ponytail, glass-hair waves"),
                 ("img", "waves-trial", "Hollywood waves, bridal trial"), ("img", "wedding-couple", "Cathedral veil, smooth and secure all day"),
                 ("video", "reel-ready", "Half-up waves on the morning")],
        title="Kxhairdesign · Bridal hair by Kelly, Melbourne",
        desc="Bridal hair by Kelly at Kxhairdesign, mobile across Melbourne and surrounds. Check your date and plan your wedding morning.",
        proof_kicker="Reviews", proof_h="What Kelly's brides say.",
        proof=[],
        quotes=[("“Our hair was literally perfect and lasted extremely well in Melbourne's 30 degree heat, and then with storms.”", "Katie W. · Easy Weddings"),
                ("“Kelly is one of Melbourne's most sought after wedding hair stylists and there's no doubt why. Her work is flawless.”", "Veronica P. · Easy Weddings"),
                ("“Kelly did such an amazing job on me and my bridesmaids.”", "Easy Weddings review")],
        venue_ph="Venue, hotel or home, and suburb",
        samples=[("Charlotte B.", 215, "Stones of the Yarra Valley", 6, "Hair only", True, ["Soft waves"], 0),
                 ("Zoe P.", 140, "Home, Hawthorn", 4, "Hair only", True, ["Up-do"], 1),
                 ("Amelia N.", 92, "Leonda by the Yarra", 3, "Hair only", True, ["Half-up"], 2),
                 ("Ruby S.", 46, "Encore St Kilda Beach", 7, "Hair only", False, ["Sleek & polished"], 3),
                 ("Ava C.", -9, "Potters Receptions, Warrandyte", 5, "Hair only", True, ["Soft waves"], 4)],
    ),
]

HERO_CARD_CSS = """
.trio video{width:100%;aspect-ratio:3/4.1;object-fit:cover;border-radius:999px 999px 4px 4px;transform:translateY(-28px);box-shadow:0 24px 40px -28px rgba(47,40,38,.45);background:var(--blush)}
@media (max-width:900px){.trio video{transform:translateY(-16px)}}
.media{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.media figure{margin:0;position:relative;border-radius:6px;overflow:hidden;background:var(--blush)}
.media img,.media video{width:100%;height:100%;object-fit:cover;aspect-ratio:3/4;display:block}
.media figure:first-child{grid-row:span 2}.media figure:first-child video,.media figure:first-child img{aspect-ratio:auto;height:100%}
.media figcaption{position:absolute;left:0;right:0;bottom:0;padding:26px 12px 10px;background:linear-gradient(transparent,rgba(30,22,20,.7));color:#fff;font-size:13px}
@media (max-width:640px){.media{grid-template-columns:1fr 1fr}.media figure:first-child{grid-column:span 2;grid-row:auto}.media figure:first-child video{aspect-ratio:9/12}}
.award{display:grid;grid-template-columns:.8fr 1.2fr;gap:28px;align-items:center;margin-bottom:24px}
.award img{width:100%;border-radius:8px;aspect-ratio:1;object-fit:cover}
.award .proofs{grid-template-columns:1fr;margin:0}
@media (max-width:900px){.award{grid-template-columns:1fr}}
.mcard{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:30px 30px 24px;box-shadow:0 30px 60px -40px rgba(47,40,38,.45);max-width:440px;justify-self:end;width:100%;position:relative}
.mcard::before{content:"";position:absolute;inset:-14px 24px auto auto;width:120px;height:120px;border-radius:50%;background:radial-gradient(circle,var(--blush),transparent 70%);z-index:-1}
.mcard .k{font:500 11px/1 var(--sans);letter-spacing:.2em;text-transform:uppercase;color:var(--gold)}
.mcard h3{font-size:30px;margin:10px 0 4px}
.mcard .sub{color:var(--muted);font-size:14px;margin:0 0 18px}
.mcard .pill{display:inline-block;font-size:12px;padding:4px 10px;border-radius:999px;background:var(--blush);margin:0 6px 6px 0}
.mcard .foot{display:flex;justify-content:space-between;align-items:center;border-top:1px solid var(--line);margin-top:14px;padding-top:14px;font-size:13px;color:var(--muted)}
.mcard .foot b{color:var(--gold);font-weight:500}
@media (max-width:900px){.mcard{justify-self:stretch;max-width:none}}
.ph{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.ph div{aspect-ratio:3/4;border:1px dashed var(--gold-soft);border-radius:6px;display:grid;place-items:center;text-align:center;color:var(--muted);font-size:13px;padding:14px;background:repeating-linear-gradient(135deg,transparent 0 14px,rgba(168,112,95,.05) 14px 15px)}
.ph div:first-child{grid-row:span 2;aspect-ratio:auto;font:italic 400 22px/1.3 var(--serif);color:var(--ink)}
@media (max-width:640px){.ph{grid-template-columns:1fr 1fr}.ph div:first-child{grid-column:span 2;grid-row:auto;aspect-ratio:auto;padding:28px}}
.proofs{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:16px}
.proofs div{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:24px}
.proofs b{display:block;font:500 28px/1.1 var(--serif);color:var(--gold);margin-bottom:6px}
.proofs span{color:var(--muted);font-size:15px}
@media (max-width:900px){.proofs{grid-template-columns:1fr}}
"""


def hero_card(a):
    sample = ("Bride + 3 bridesmaids + mum", ["7:10am · " + a["who"] + " arrives", "7:30am · Mum", "8:30am · Bridesmaids",
              "10:45am · Bride", "12:40pm · Veil &amp; touch-ups", "1pm · Ready for photos ✨"])
    tl = "".join(f'<li{" class=\"ready\"" if i == len(sample[1]) - 1 else ""}><time>{s.split(" · ")[0]}</time>{s.split(" · ", 1)[1]}</li>'
                 for i, s in enumerate(sample[1]))
    svc = "Hair & makeup" if a["svc_mode"] == "both" else "Bridal hair"
    return f'''<div class="mcard" aria-label="Example of a planned wedding morning">
    <span class="k">Sample wedding morning</span>
    <h3>Saturday, 1pm photos</h3>
    <p class="sub">{sample[0]}</p>
    <span class="pill">{html.escape(svc)}</span><span class="pill">Trial booked</span><span class="pill">Soft waves</span>
    <ol class="tl" style="margin-top:12px">{tl}</ol>
    <div class="foot"><span>Planned in 2 minutes by the bride</span><b>Sent to {a["who"]} ✓</b></div>
  </div>'''


def media_tag(kind, name, alt, cls=""):
    if kind == "video":
        return (f'<video src="img/{name}.mp4" poster="img/{name}.jpg" autoplay muted loop playsinline preload="metadata" '
                f'aria-label="{html.escape(alt)}"></video>')
    return f'<img src="img/{name}.jpg" alt="{html.escape(alt)}" loading="lazy">'


def hero_trio(a):
    return '<div class="trio">' + "".join(media_tag(k, n, al) for k, n, al in a["hero_media"]) + "</div>"


def build(a):
    h = BASE
    h = h.replace('<html lang="en-AU">', '<html lang="en-AU">')
    h = re.sub(r"<title>.*?</title>", f"<title>{a['title']}</title>", h)
    h = re.sub(r'<meta name="description" content=".*?">', f'<meta name="description" content="{a["desc"]}">', h)
    h = h.replace("</style>", HERO_CARD_CSS + "</style>", 1)
    # pitch strip
    h = h.replace("This is a free preview made for Glam by Zetta. Want it live, linked from your Google listing and Instagram?",
                  f"This is a free preview made for {a['name']}. Want it live" + ("" if a.get("gallery") else ", with your own photos") + ", on Google and in your Instagram bio?")
    h = h.replace("made%20for%20Glam%20by%20Zetta", "made%20for%20" + a["name"].replace(" ", "%20"))
    # header
    h = h.replace('aria-label="Glam by Zetta, back to top"', f'aria-label="{a["name"]}, back to top"')
    h = h.replace('<span class="mono" aria-hidden="true">Z</span>', f'<span class="mono" aria-hidden="true">{a["mono"]}</span>')
    h = h.replace("<b>Glam by Zetta</b><small>Bridal hair &amp; makeup · Brisbane</small>", f"<b>{a['name']}</b><small>{a['tagline']}</small>")
    h = h.replace('<a href="#work">Brides</a><a href="#reviews">Reviews</a><a href="#pipeline">Zetta\'s view</a>',
                  f'<a href="#reviews">{"Recognition" if a["proof"] else "Reviews"}</a><a href="#pipeline">{a["who"]}\'s view</a>')
    # hero
    h = h.replace('<span class="kicker">Bridal hair &amp; makeup · Darra, Brisbane</span>', f'<span class="kicker">{a["kicker"]}</span>')
    h = re.sub(r"<h1>.*?</h1>", f"<h1>{a['h1']}</h1>", h, count=1, flags=re.S)
    h = re.sub(r'(<section class="wrap hero">\s*<div>.*?</h1>\s*)<p>.*?</p>', lambda m: m.group(1) + f"<p>{a['lead']}</p>", h, count=1, flags=re.S)
    h = h.replace('<a class="btn ghost" href="#work">See her brides</a>', f'<a class="btn ghost" href="#pipeline">See {a["who"]}\'s view</a>')
    facts = "".join(f"<div><b>{k}</b>{v}</div>" for k, v in a["facts"])
    right = hero_trio(a) if a.get("hero_media") else hero_card(a)
    h = re.sub(r'<div class="facts">.*?</div>\s*</div>\s*<div class="trio".*?</div>', f'<div class="facts">{facts}</div>\n  </div>\n  {right}', h, count=1, flags=re.S)
    # how it works + planner copy
    h = h.replace("Everything Zetta needs, in one go.", f"Everything {a['who']} needs, in one go.")
    h = h.replace("Your enquiry goes to Zetta on WhatsApp, and she replies", f"Your enquiry goes to {a['who']} on Instagram, and she replies")
    h = h.replace("Tell Zetta the vibe you love, from natural to full glam.",
                  "Tell " + a["who"] + (" the vibe you love, from natural to full glam." if a["svc_mode"] == "both" else " the style you love, from soft waves to a sleek up-do."))
    if a["svc_mode"] == "hair":
        h = h.replace("and choose hair, makeup or both.", "and choose a trial.")
        h = h.replace('<div class="seg" role="group" aria-label="Service">', '<div class="seg" role="group" aria-label="Service" style="display:none">')
        h = h.replace('<div class="chipset" id="mkset">', '<div class="chipset" id="mkset" style="display:none">')
        h = h.replace('svc="both"', 'svc="hair"')
        h = h.replace("Who's getting ready?", "Who needs their hair done?")
        h = h.replace("(veil, accessories, skin type, Pinterest board)", "(hair length, veil, accessories, Pinterest board)")
        h = h.replace("e.g. Long, thick hair. Wearing a cathedral veil. Sensitive skin.", "e.g. Long, thick hair. Wearing a cathedral veil.")
        h = h.replace('L.push("💄 Service: "+SVC[svc]);', "")
        h = h.replace('💐 Bridal enquiry:', '💐 Bridal hair enquiry:')
    h = h.replace('placeholder="Venue, hotel or home, and suburb"', f'placeholder="{a["venue_ph"]}"')
    h = h.replace("Where can Zetta reach you?", f"Where can {a['who']} reach you?")
    h = h.replace("Please add a mobile number Zetta can reach you on.", f"Please add a mobile number {a['who']} can reach you on.")
    # send step: Instagram (copy, then open DM)
    h = h.replace("Send it to Zetta on WhatsApp. It opens with your enquiry already written, so just press send.",
                  f"Send it to {a['who']} on Instagram. We've copied it for you, so just paste it into the chat.")
    h = h.replace('<a class="btn" id="sendWa" href="#" target="_blank" rel="noopener">Send to Zetta on WhatsApp</a>',
                  f'<a class="btn" id="sendWa" href="https://ig.me/m/{a["ig"]}" target="_blank" rel="noopener">Send to {a["who"]} on Instagram</a>')
    h = h.replace('<a class="btn ghost" href="https://ig.me/m/glambyzetta" target="_blank" rel="noopener">Instagram instead</a>', "")
    h = h.replace('$("sendWa").href="https://wa.me/"+WA+"?text="+encodeURIComponent(text);', 'copy(text);')
    h = h.replace('$("copy").addEventListener("click",function(){copy($("summary").textContent)});',
                  '$("copy").addEventListener("click",function(){copy($("summary").textContent)});\n  $("sendWa").addEventListener("click",function(){copy($("summary").textContent)});')
    h = h.replace('function ok(){toast("Copied!")}', f'function ok(){{toast("Copied! Paste it into your chat with {a["who"]}.")}}')
    h = h.replace("Estimated, with one artist. Zetta will confirm exact timings.", f"Estimated, with one artist. {a['who']} will confirm exact timings.")
    h = h.replace("'</time>Zetta arrives and sets up</li>'", f"'</time>{a['who']} arrives and sets up</li>'")
    h = h.replace("so Zetta may suggest a second artist", f"so {a['who']} may suggest a second artist")
    h = h.replace('"Hi Zetta! 💐', f'"Hi {a["who"]}! 💐')
    if a.get("gallery"):
        figs = "".join(f"<figure>{media_tag(k, n, al)}<figcaption>{html.escape(al)}</figcaption></figure>" for k, n, al in a["gallery"])
        h = re.sub(r'<section class="block alt" id="work">.*?</section>', f'''<section class="block alt" id="work">
  <div class="wrap">
    <div class="head"><span class="kicker">Brides</span><h2>Recent brides.</h2><p>More on <a href="https://www.instagram.com/{a["ig"]}/" target="_blank" rel="noopener">@{a["ig"]}</a>.</p></div>
    <div class="media">{figs}</div>
  </div>
</section>''', h, count=1, flags=re.S)
        h = h.replace('<a href="#reviews">', '<a href="#work">Brides</a><a href="#reviews">', 1)
    else:  # no photos: drop the gallery; the pitch strip says the live version uses their own photos
        h = re.sub(r'<section class="block alt" id="work">.*?</section>\s*', "", h, count=1, flags=re.S)
    # proof / reviews
    proofs = ('<div class="proofs">' + "".join(f"<div><b>{k}</b><span>{v}</span></div>" for k, v in a["proof"]) + "</div>") if a["proof"] else ""
    if a.get("award_img") and proofs:
        proofs = f'<div class="award"><img src="img/{a["award_img"]}.jpg" alt="{a["who"]} with her ABIA award">{proofs}</div>'
    qs = "".join(f'<figure class="rev"><div class="st">★★★★★</div><blockquote>{q}</blockquote><figcaption>{c}</figcaption></figure>' for q, c in a["quotes"])
    grid = f'<div class="revs"{" style=\"grid-template-columns:1fr\"" if len(a["quotes"]) == 1 else ""}>{qs}</div>'
    h = re.sub(r'<section class="block" id="reviews">.*?</section>', f'''<section class="block" id="reviews">
  <div class="wrap">
    <div class="head"><span class="kicker">{a["proof_kicker"]}</span><h2>{a["proof_h"]}</h2></div>
    {proofs}{grid}
  </div>
</section>''', h, count=1, flags=re.S)
    if not a.get("gallery"):
        h = h.replace('<section class="block" id="reviews">', '<section class="block alt" id="reviews">')
        h = h.replace('<section class="block alt" id="pipeline">', '<section class="block" id="pipeline">')
    # pipeline
    h = h.replace("<span class=\"kicker\">Zetta's view</span>", f"<span class=\"kicker\">{a['who']}'s view</span>")
    h = h.replace("notify Zetta by text or email", f"notify {a['who']} by text or email")
    samples = ",\n    ".join(
        f'{{id:{i+1},name:"{n}",date:iso({d}),venue:"{v}",heads:{hd},svc:"{s}",trial:{"true" if t else "false"},looks:["{lk[0]}"],stage:{st}}}'
        for i, (n, d, v, hd, s, t, lk, st) in enumerate(a["samples"]))
    h = re.sub(r"var SAMPLE=\[.*?\];", f"var SAMPLE=[\n    {samples}\n  ];", h, count=1, flags=re.S)
    h = h.replace('var KEY="gbz-pipeline-v1";', f'var KEY="{a["slug"]}-v1";')
    h = h.replace('var GALLERY=["z5","z1","z0","z2","z7","z4","z9","z6","z8","z3"];', "var GALLERY=[];")
    h = h.replace('var WA="61406528538";', "")
    h = h.replace("(Zetta sets her real timings", f"({a['who']} sets her real timings")
    h = h.replace('i.alt="Bride styled by Glam by Zetta"', f'i.alt="Bride styled by {a["name"]}"')
    # footer
    h = re.sub(r"<footer>.*?</footer>", f'''<footer>
  <div class="wrap">
    <div><b>{a["name"]}</b>{a["tagline"].split(" · ")[0]}.<br>{a["region"]}.</div>
    <div><h5>Enquiries</h5><a href="https://ig.me/m/{a["ig"]}" target="_blank" rel="noopener">Message on Instagram</a></div>
    <div><h5>Follow</h5><a href="https://www.instagram.com/{a["ig"]}/" target="_blank" rel="noopener">@{a["ig"]}</a></div>
    <div class="fine"><span>© <span id="yr"></span> {a["name"]}</span><span>Demo site, made to show {a["who"]} what her booking page could look like</span></div>
  </div>
</footer>''', h, count=1, flags=re.S)
    leftovers = [w for w in ("Zetta", "Darra", "Brisbane", "glambyzetta", "61406528538", "Prynissa", "Michelle", "achaiaauman", "233") if w in h]
    out = ROOT / "demos" / a["slug"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(h)
    print(a["slug"], "leftovers:", leftovers)


for a in ARTISTS:
    build(a)
