# salon-demos

Private demo websites for independent salons (hair studios, beauty parlours,
bridal studios, unisex salons) that have strong Google reviews but no website
of their own. Each demo is shown privately to the owner to sell them a website.

```
leads.json  ->  python3 build.py <slug>  ->  demos/<slug>/index.html  ->  Vercel at /<slug>/
```

Each demo is one self-contained HTML file (Google Fonts only, no frameworks)
with its photos in `demos/<slug>/img/`. Every page carries `noindex`, and
`vercel.json` adds an `X-Robots-Tag: noindex` header to the whole site, so demos
stay out of search results.

## What a demo contains

- **Home**: arched hero photo with a turning badge, Google rating and an
  "open now / closed now" pill worked out from the hours; three highlights
  (01 / 02 / 03); before/after sliders (optional); services and prices beside a
  photo; a dark bridal band with a chalkboard sign (optional); a photo gallery with
  a full-screen lightbox (swipe row on mobile); three Google reviews; the team
  (optional); visit section with hours (today highlighted), map and directions.
- **Booking**: if the lead has a `booking_link`, a card with the top prices and a
  button to the salon's booking page. Otherwise a WhatsApp form: service, date, time and name. Time slots come from that day's
  opening hours, closed days are refused, and submitting opens WhatsApp with
  *"Hi, I'd like to book <service> at <salon> on <day date> at <time>. My name is <name>."*
- **`#review`**: a page the salon sends to clients after a visit. 4–5 stars go to
  Google; 1–3 stars are invited to send a private WhatsApp note first.
  `#review?s=<stylist>` pre-selects the stylist.
- **`#review-kit`**: a page for the salon team: a review link per stylist, a ready
  message to send by WhatsApp or SMS, and a printable counter card with a QR code.
- **Mobile**: a slim sticky bar with Call (or Directions) and WhatsApp (or Book).
- **Footer**: phone, WhatsApp, today's hours, and a small "Demo site" note.

The whole palette comes from the lead's `accent` and `mood`: `light` is a warm
off-white page, `dark` a deep, moody one. Text contrast is pushed automatically
to stay readable.

Rules for every demo: no online payment, no fake urgency ("only 2 slots left"),
no invented reviews (copy real ones from Google), no third-party marketplace
logos.

## Lead format (`leads.json`)

`leads.json` is a list with one object per salon.

| Field | Required | Notes |
|---|---|---|
| `slug` | yes | lowercase, digits, hyphens; becomes the URL `/<slug>/` |
| `name` | yes | salon name as on Google |
| `type` | yes | e.g. "Hair studio", "Bridal & beauty parlour", "Unisex salon" |
| `area`, `city`, `country` | yes | area is the locality, e.g. "Koramangala 5th Block" |
| `phone` | no | any format; adds Call buttons |
| `whatsapp` | one of these two | any format; turns on the WhatsApp booking form and WhatsApp buttons |
| `booking_link` | one of these two | the salon's own booking page (Fresha, Booksy…). When set, the booking card links there instead of showing the WhatsApp form |
| `rating` | yes | Google rating, e.g. `4.8` |
| `review_count` | yes | integer |
| `maps_link` | yes | the Google Maps link; used for directions and, if no `google_review_link`, for reviews |
| `hours` | yes | exactly 7 objects, Monday to Sunday: `{"day": "Monday", "time": "10:00-20:00"}` or `"Closed"` |
| `headline`, `subline` | yes | hero heading and the sentence under it |
| `highlights` | yes | exactly 3 short points |
| `services` | yes | list of `{category, items: [{name, price?, note?}]}`; omit `price` to hide prices |
| `reviews` | yes | exactly 3 `{text, name}` copied from Google (first name only) |
| `accent` | yes | hex colour, e.g. `#B4654A` |
| `mood` | yes | `"light"` or `"dark"` |
| `photos` | yes | number of gallery images, at least 4 (`g1` sits beside the services, `g2`…`gN` fill the gallery; 3 to 7 gallery photos get a hand-made layout) |
| `google_review_link` | no | `https://search.google.com/local/writereview?placeid=<PLACE_ID>` |
| `booking_label` | no | button text for `booking_link`, e.g. "Book on Fresha" (default "Book online") |
| `review_source` | no | where `rating`/`review_count`/`reviews` come from, e.g. "Fresha" (default "Google") |
| `address` | no | street line for the Visit section (defaults to `area`) |
| `lang` | no | page language, e.g. `en-NZ` (default `en`) |
| `instagram` | no | profile URL |
| `services_note` | no | line under the Services heading |
| `before_after` | no | up to 3 `{title, note?}` |
| `team` | no | `{name, role, note?}`; names also become stylist chips on `#review` |
| `bridal` | no | `{kicker?, title, text, packages?: [{name, price?}]}` |
| `gallery_title`, `gallery_text` | no | defaults to "Recent looks" |
| `monogram` | no | 1–2 letters; defaults to the initials of `name` |
| `hero_alt` | no | description of the hero photo or video for screen readers |

### Images (`demos/<slug>/img/`)

| File | When |
|---|---|
| `hero.jpg` | always (portrait works best; it sits in an arch) |
| `g1.jpg` … `gN.jpg` | always, N = `photos` |
| `ba1-before.jpg`, `ba1-after.jpg`, … | one pair per `before_after` entry |
| `bridal.jpg` | if `bridal` is set |
| `hero.mp4` | optional: a short muted loop (5–10 s, ~540px wide, H.264, under ~1 MB) that replaces the hero photo; `hero.jpg` becomes its poster |

Keep photos around 1200–1600px on the long side and under ~300 KB each (JPEG,
quality ~75). Everything except the hero is lazy-loaded.

`build.py` stops with a clear message listing every missing field or image.

## Add a lead

1. Add an object to `leads.json` (copy one of the examples).
2. Put the photos in `demos/<slug>/img/` with the names above.
   No photos yet? `python3 scripts/placeholders.py <slug>` writes gradient
   placeholders so you can check the layout (needs Pillow). Never send a demo
   with placeholders.
3. Build and check it (below), then commit `leads.json` and `demos/<slug>/`.

## Build

```bash
python3 build.py <slug>     # one demo
python3 build.py --all      # every lead
python3 build.py --list     # list slugs
```

`build.py` uses the Python standard library only.

## Check

```bash
pip install playwright && python3 -m playwright install chromium   # once
python3 scripts/check.py <slug>     # or --all
```

This saves full-page screenshots at 1400px and 390px (home, `#review`,
`#review-kit`) to `shots/<slug>/` (git-ignored) and reports JS errors, broken
images and sideways scrolling. Open the screenshots and look at them before
sending a demo.

## Preview locally

```bash
python3 -m http.server 8000 --directory demos
# http://localhost:8000/example-hair-studio/
# http://localhost:8000/example-bridal-parlour/
```

## Deploy

The repo deploys to Vercel as a static site with `demos/` as the output folder,
so `demos/<slug>/index.html` is served at `https://<project>.vercel.app/<slug>/`.
There's no build step on Vercel: build locally and commit the output.

First time: import the repo in Vercel (framework preset "Other"); `vercel.json`
already sets the output folder. After that, every push to `main` deploys.
The site root has no index on purpose, so nobody can browse the list of demos.

## Examples

- `example-hair-studio`: light mood, terracotta accent, before/after, team, prices.
- `example-bridal-parlour`: dark mood, maroon accent, bridal band, no prices,
  closed on Tuesdays.

Both use generated placeholder images and made-up details.

## Live demos

- `luke-james`: Luke James Hairdressing, 148 Hunts Cross Ave, Woolton, Liverpool L25 8SQ.
  Bespoke light-theme page with real-time three.js: a grey salon chair (FurniMesh GLB, materials set in
  code to match their chairs) lit by a Poly Haven studio HDRI, with a shadow that follows the pointer, drag to
  turn and 3D-anchored labels, plus three tools in the price list that swap per service (scissors for cuts, dryer for blow dries and perms,
  brush for colour): "Barber's scissors" by DUCK_ (CC BY 4.0), "HAIR DRYER" by saud_artist (CC BY-SA 4.0,
  simplified from 6.3 MB to 0.4 MB, so the slimmed file stays CC BY-SA) and "hair bush" by pibini modeling
  (CC BY 4.0, simplified to 0.75 MB). All credited in the footer. Real prices from their price list (short/long toggle),
  their own salon and colour photos, named reviews, stylist mirrors in their frame style, a "Recent work" photo reel,
  and an in-page booking system (no server): service, stylist, live slots per stylist (Gill, Kerry, or first free),
  details with a skin-test check for colour, a 10-minute chair hold with countdown, a £10 deposit, then a fixed
  slot with a booking reference, .ics file and cancel. Bookings live in localStorage, so a taken slot is only
  taken in that browser; `#salon` opens the salon view of those bookings. Set `CONFIG.stripeLink` in the page to a
  Stripe Payment Link for a £10 product to take real deposits (the reference is passed as `client_reference_id`);
  left empty, the checkout is a clearly labelled demo. Shared slots across all visitors need a small backend. The 3D source lives outside this repo: rebuild
  `assets/site.js` with esbuild from three.js r187 (`three` + `GLTFLoader` + `HDRLoader`). `assets/studio.hdr` is the
  1K EXR downsampled to 512x256. `assets/chair-poster.webp` shows while WebGL loads.

- `house-of-henshaw`: House of Henshaw, 303 Aigburth Road, Liverpool L17. Bespoke page in their
  cream-and-gold brand with H monogram: lived-in colour hero film, Serenity headspa and testing,
  "Wife Day Care" reel, gift vouchers and shop, team, reviews, built-in 4-step booking (closed
  Sundays, real opening hours), HairSalon + FAQ JSON-LD. Photos and films are the salon's own.

- `luke-james/diary/`: "Full Diary" back-office demo for Luke James (single HTML, no server), in the same style.
  Tabs: today's diary with a cancellation-refill engine and website bookings (read from the demo site's
  localStorage in the same browser), pre-visit add-on offers from their price list (NPlex, toner, rollers),
  rebook at the till with per-stylist rebook rates, product recommendations and reorder reminders, regulars due
  and first-timer second visits, 48-hour skin-test tracking with a CSV log, Christmas vouchers and memberships,
  missed-call text-back and 10pm replies, reviews and referrals, a wedding/prom quote builder with timings, a
  stylist scorecard and a revenue calculator. Prices, hours and stylists are the salon's; clients are sample data.
- `beyond-salon`: Beyond Beauty Salon by Ahmed Batekha, Egypt (Sheikh Zayed at The Lane
  Mall Palm Hills, Zamalek, Sahel). Bespoke page with a built-in 5-step booking engine
  (branch, services, stylist, date/time, details), booking reference, .ics calendar file,
  My bookings with cancel, and a salon dashboard view (bookings stored in the browser
  for the demo). SEO/AEO: Organization + 3 BeautySalon locations with ReserveAction,
  OfferCatalog and FAQPage JSON-LD, answer-first FAQ, hreflang en/ar, and `llms.txt`.
  Opening hours in the booking engine (11am to 10pm, Sahel 12 to 11pm) are assumed.

- `her-salons`: HER Salons, Perth (423 Oxford St, Mount Hawthorn) and Melbourne
  (287 High St, Prahran). A bespoke, hand-built page (not from `template.html`)
  because it covers two salons and a product shop: split hero film, salons with
  hours, hair menu, spa rituals, a 12-product shop with a bag that sends the order
  to the salon by email, lookbook, press quotes and FAQ. Details from
  hersalons.com.au and their Phorest store; photos and films from @her_salons.

- `the-cut-co`: The Cut Co, 125 Karangahape Road, Auckland (Remi Chak, @remichak).
  Details, prices, hours and reviews come from their Fresha listing; photos and
  the hero video are their own Instagram work (two gallery tiles are still screenshot crops). Books through Fresha (no WhatsApp/phone found).
