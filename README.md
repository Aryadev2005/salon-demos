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

## Find salons and make demos in bulk

`scripts/places_to_leads.py` turns Google searches into finished demos and an outreach sheet.

```bash
export GOOGLE_MAPS_API_KEY=...                      # Places API (New), on a billed Google Cloud project
python3 scripts/places_to_leads.py --dry-run        # search + rank only: see who qualifies
python3 scripts/places_to_leads.py                  # make the demos (default 27, see prospects.json)
git add leads.json demos && git commit -m "New demos" && git push
```

- **Searches** come from `scripts/prospects.json` (`queries`, `limit`, `min_rating`, `min_reviews`, `skip`,
  your name/WhatsApp, `price`, `base_url`). Each query returns up to 60 places (3 pages of 20).
- **Kept**: operating, phone and opening hours listed, at least 5 photos, rating and review count above the
  thresholds, no own website (Facebook, Instagram, Linktree, Fresha, Treatwell, Booksy etc. don't count),
  not a chain, not already in `leads.json` or `skip`. Ranked by rating × log(review count).
- **Each demo gets**: real hours, address, rating, up to 3 five-star Google reviews (first names, cut at a
  sentence), 6 Google photos (hero, 4 gallery, Christmas band) credited in the gallery line, an accent colour
  picked from the photos, starter services for the salon type (no prices), the Christmas band and your pitch
  banner. Booking: their Fresha/Treatwell/Booksy link if they have one, else the WhatsApp form for UK mobiles
  (07…), else call-to-book.
- **`out/outreach.csv`** (git-ignored): salon, phone, channel, a WhatsApp click-to-send link with the message
  filled in (mobiles), an Instagram link or search (everyone else), demo link, and blank status/notes columns.
  Re-make it any time with `--rebuild-sheet`.
- **Cost control**: raw Google responses are cached in `cache/places/` (git-ignored), so re-runs are free;
  `--max-requests` (default 400) stops the run. A 27-salon run is roughly 15–40 searches + 162 photos.
- Look at every demo before sending: auto-picked photos can be a dark shopfront or a client's face, and the
  starter services are generic. Edit the lead in `leads.json`, then `python3 build.py <slug>`.
- Generated leads carry `"_auto": true` and `place_id`. Google photos are fine for a private preview;
  swap in the salon's own photos before a site goes live.

## Hosting: one site for every demo

`hosting/` is deployed once to Vercel as **salon-previews.vercel.app**. Any path `/<slug>/` loads
`demos/<slug>/index.html` straight from this repo's `main` branch on GitHub, so **a `git push` publishes new
demos with no deploy** (GitHub's raw cache can take a few minutes). Unknown slugs show "This preview isn't
available". Everything is `noindex`.

## UK prospecting (Google Maps)

Search `<niche> <town>` in Google Maps, e.g. `hair salon Wigan`, `barbers Doncaster`.
Niches: hair salon, barbers, nail salon, beauty salon, lash and brow, aesthetics clinic,
dog groomer. Mid-size towns are less pitched-to than London or Manchester: Wigan, Bolton,
Doncaster, Rotherham, Stoke-on-Trent, Wolverhampton, Walsall, Sunderland, Preston,
Blackpool, Swindon, Peterborough, Northampton, Luton, Derby, Hull.

Keep a listing if it has **4.5+ stars, 40+ reviews**, a phone number, and **no Website
button** (or one pointing to Facebook, Instagram, Linktree or a broken page). Skip chains.
Copy rating, review count, hours, prices and three real reviews straight into a new lead.

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
| `bridal` | no | `{kicker?, title, text, packages?: [{name, price?}], nav?}`; `nav` renames the menu link (default "Bridal"), e.g. "Christmas" |
| `gallery_title`, `gallery_text` | no | defaults to "Recent looks" |
| `monogram` | no | 1–2 letters; defaults to the initials of `name` |
| `colors` | no | overrides for any generated palette colour (`paper`, `paper2`, `mist`, `line`, `ink`, `muted`, `accent`, `on_accent`, `board`, `board2`, `chalk`, `chalk_dim`, `gold`, `photo_a`, `photo_b`), e.g. to match a salon's exact brand colours |
| `pitch` | no | `{name, whatsapp, text?}`: a strip at the top of the page saying it's a free preview, with a WhatsApp button to you. Remove it once the salon buys |
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
- `example-uk-salon`: UK starter (Sheffield, `en-GB`, £ prices, +44 WhatsApp booking,
  closed Sundays and Mondays). The bridal band is reused as a **Christmas & New Year
  party bookings** band; copy this lead for any UK salon in November and December.

Both use generated placeholder images and made-up details.

## Live demos

- `bridal-stylist-wigan`: The Bridal Stylist by Beth Starkie (@_thebridalstylist), bridal hair at Suzanne's, 50 Wigan Lane.
  Hand-built page (not from `build.py`) in her ivory and gold. A 4-step enquiry (date, venue and ready time; party
  counts and trial; tap looks from her real work; contact) builds a live wedding-morning timeline (planning estimates:
  bride 60 min, bridesmaid 40, guest 35, flower girl 20, plus 20 min buffer), then copies a formatted enquiry and opens
  her Instagram DMs (ig.me). `#pipeline` is Beth's board: New enquiry, Quoted, Trial booked, Deposit paid, Wedding done,
  with sample brides plus any enquiry sent in that browser (localStorage). Photos are crops of her Instagram grid.

- `bleach`: Bleach Hair, 385 Smithdown Road, Wavertree, Liverpool L15 3JJ (Karl Mathers). Bespoke light page in the
  salon's own colours (red and blue velvet, white plaster). The hero is a real-time three.js copy of the gold iridescent
  mosaic sign in the salon: about 6,000 instanced glass tiles (RoundedBoxGeometry, MeshPhysicalMaterial with
  iridescence, RoomEnvironment reflections) that flip in on load, catch a light that follows the pointer (and wanders
  on its own on phones) and ripple as you scroll. "Bleach" is laid in black tiles from the Lobster font at runtime.
  The booking section has a rose velvet styling chair (the same FurniMesh GLB as Luke James, recoloured to Karl's station chairs) that loads only when you get near it: it rises a notch at each booking step, turns to face you while your time is held, spins when the booking is made and turns away on a cancel; drag to turn it. The hero needs no model or HDR files, so it loads light; the sign photo shows if WebGL is unavailable. Fonts are self-hosted in
  `assets/fonts/`. Source in `src/mosaic.js`, bundled to `assets/site.js` with esbuild from three.js r187.
  Real prices, durations and hours from their Treatwell mini-site; reviews and the 4.7 / 95 rating from Treatwell.
  Salon photos are hotlinked from Treatwell's CDN (download them into `img/` if that listing goes away).
  In-page booking (no server): service, day and live free times, details with a free patch test booked 48 hours
  before colour, a 10-minute hold, a £10 deposit (demo checkout unless `CONFIG.stripeLink` is set), reference, .ics
  and cancel. Fully booked days take waiting-list sign-ups; cancellations (by a client, or in Karl's diary at
  `#salon-view`) are offered to the waiting list with the text message shown. Diary clients are sample data.

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

  Premium pass (from their shopfront): monochrome black/white/chrome palette, Bodoni Moda wordmark matching the
  sign, a hexagon LED ceiling above the 3D chair (also baked into the reflections), graded photos as WebP with
  srcset, the shopfront in the Visit section, merged salon + recent work, stylists moved into the booking flow.
- `luke-james/diary/`: "Full Diary" back-office demo for Luke James (single HTML, no server), in the same style.
  Tabs: today's diary with a cancellation-refill engine and website bookings (read from the demo site's
  localStorage in the same browser), pre-visit add-on offers from their price list (NPlex, toner, rollers),
  rebook at the till with per-stylist rebook rates, product recommendations and reorder reminders, regulars due
  and first-timer second visits, 48-hour skin-test tracking with a CSV log, Christmas vouchers and memberships,
  missed-call text-back and 10pm replies, reviews and referrals, a wedding/prom quote builder with timings, a
  stylist scorecard and a revenue calculator. Prices, hours and stylists are the salon's; clients are sample data.
- `bridal-hairstyles`: Bridal Hairstyles by Alice Paonessa, 2 Wilberforce Rd, Wilford, Nottingham NG11 7GU
  (07546 606107, bridalhairstyles.co.uk). She already has a website, so this is a proposal page addressed to her
  ("Ciao Alice!") in her own palette (white, blush, peach; Cormorant Garamond + Jost). It sells a booking engine
  that replaces her Check Availability form: her process today vs with the engine; a live bride flow using her
  real prices (bride on the day £75, guest £60, bride trial £75, guest trial £60, under 10 £35, £50 deposit) and
  her real form fields (access time, ceremony time, where getting ready, venue, where heard), a quote, a morning
  timeline that flags when a second stylist is needed (as her FAQ says), a weekday studio trial picker, terms
  checkbox, demo deposit, reference and .ics; a WhatsApp preview of what she receives; her diary at `#studio`
  (pipeline, next automatic message, waiting list offer on cancel, quiet weekdays, sent log); quiet-day ideas
  (Hollywood waves £100, guest trials, waiting lists); an e-book follow-up sequence; Google/AI search setup with
  an honest no-rankings-promise note; a calculator driven by her prices and her own slider inputs; straight
  answers; next steps. Photos are cropped from her own site screenshots into `img/`. Booked dates and diary
  brides are sample data.
- `bridal-hairstyles/academy/`: student booking kit for Alice's bridal hair course (her idea: a simple tool she gives
  students so they can work professionally from day one). Three linked views in one file: `#link`, the bride's
  enquiry link a student shares on social media ("Trained by Alice Paonessa" badge, instant estimate from the
  student's prices, booked dates shown); `#app`, the student's phone app, where each bride moves through Alice's
  8 steps (enquiry, quote, date secured, trial, trial done, paid, ready, done) with Alice's tip and a ready
  WhatsApp message per step, tick-off payments (no card payments, as Alice asked), trial notes, wedding-morning
  schedule from access/ceremony times, a kit list, money and settings; `#academy`, Alice's console with all students'
  enquiries, bookings and flags, an editor for her method (tips and messages update every student's app) and a
  broadcast to all students. Method wording, students and brides are sample data; data lives in localStorage.
- `preshita-bafna`: Preshita Bafna, luxe bridal makeup artist, Mumbai & worldwide (Instagram
  @preshita_bafna_themakeupartist, WhatsApp +91 82374 78901; team @meerasakhrani since 2019, 500+ brides,
  destination specialist, runs a 2026 masterclass). She books through Instagram DMs and WhatsApp, and her team replies
  with a manual form (name, phone, date, venue/city, number of looks). Dark espresso/gold page with a proposal strip
  (today vs with a booking link), and a bride flow: date calendar (free / 1 slot / booked), functions as looks
  (haldi, mehendi, sangeet, wedding, reception) with dates offset from the wedding, family looks by her team,
  draping, trial, city chips incl. destination abroad, Preshita or senior artist, details, then a WhatsApp message
  pre-filled in her team's exact form format. `#studio`: enquiries pipeline (enquiry, quote, advance, trial,
  confirmed, done) with one-tap WhatsApp per stage, season view, team allocation, masterclass seats. Prices in INR
  are samples (labelled); photos cropped from her Instagram grid into `img/`.
- `sheetal-tripathi`: Sheetal Tripathi, luxury bridal & glam makeup artist, Mumbai, available worldwide
  (@sheetaltripathi.mua, WhatsApp +91 84259 39665; "Bridal bookings now open 2026–2027"; bridal, engagement,
  editorial; brand work incl. Nykaa). Adapted from `preshita-bafna` in a deep red/ivory palette: engagement added
  to the functions, no team/senior-artist choice, Pune in the cities, a brands & editorial enquiry section instead
  of the masterclass, WhatsApp hand-off to her number. Sample INR prices labelled; photos cropped from her grid.
- `preeti-khandelwal`: Preeti Khandelwal, bridal makeup artist, luxury soft glam, Delhi · Noida · Ghaziabad and
  destination weddings, 10+ years (@preetikhandelwalmakeup; "Classes" highlight; a reel about no confusing extra
  charges). Bookings are all manual on WhatsApp. Adapted from `preshita-bafna` in a rose/espresso palette:
  engagement/roka added, Delhi NCR cities, no team choice, an "Included / no hidden extras" note in the quote, and a
  classes section with two batches (Pro Soft Glam Masterclass, Self-Makeup Class) and seat booking. `C.wa` is empty
  because no public WhatsApp number was found: put hers in before sending live; until then the WhatsApp button
  opens WhatsApp with the message ready. Sample INR prices labelled; photos cropped from her grid.
- `black-and-white-jlt`: Black and White Ladies Salon, JLT Dubai (since 2012, 10am–10pm daily, +971 56 966 6647).
  Their website's Book Online page shows "This form is temporarily unavailable". Black/white/coral page with the
  real packages A–F (AED 149–399, with was-prices and contents from their site), individual services (prices at
  the salon), 14-day picker with 30-min slots, salon or home service, WhatsApp confirmation, reminder and rebooking
  plan, spa-party enquiry. `#studio`: today's diary by chair with gaps, offer-gaps-to-regulars, due-back nudges,
  sent log. Team photo and gallery crops from their site; clients and times are samples.
- `glam-with-saman`: Saman (@glamwithsaman), makeup artist in Rochdale & Manchester, travel available; bridal and party
  glam (makeup only), soft glam & Asian bridal. Books by Instagram DM: she replies asking for service, date, time and
  postcode; her Bookings highlight lists date, time, location, occasion, number of people; T&Cs highlight (non-refundable
  deposit, late fee). Plum/peach page from the Preshita styles with its own flow in GBP: date calendar, bridal events
  (mehndi, nikah/barat, walima, trial) or party glam (people, occasion), time + postcode with sample travel rule
  (OL/M free), details + T&Cs checkbox, and the message in her own format. `#studio`: enquiries pipeline, months,
  deposits. Sample prices labelled; photos cropped from her grid.
- `noha-ezz-el-din`: Noha Ezz El Din, bridal & celebrity makeup artist, Cairo + destination, 93.8K followers, founder of
  @the.makeuplab (studio in Sheikh Zayed). Bookings by WhatsApp +20 127 111 1747; her team replies with a pricing card
  (evening makeup 9,000 EGP, lashes included, 45 min–1 h), a booking form and policy, and a 2-person minimum for home
  bookings (1 person → studio). Black/ivory/champagne page from the Saman flow: evening (per person, min 2 at home,
  home disabled for 1) or bridal (katb el ketab, henna, wedding, trial, destination; quote on request), studio vs her
  place, policy checkbox, WhatsApp hand-off to her bookings number. `#studio`: requests pipeline. Photos from her grid.
- `rupangi-makeovers`: Rupangi B. Sethi (@rupangiimakeovers, verified, 40.1K followers, 1,412 posts), freelance MUA,
  Delhi, works globally; bridal and party makeup (highlights Brides'26, Party'26). Bookings "ONLY DM and WhatsApp"
  +91 81789 04859. Her WhatsApp reply asks: number of party makeups, location, event date(s), ideal time to be ready,
  and, if the bride, her functions (Engagement, Wedding, Reception, Roka). Wine/gold/ivory page from the Noha flow:
  event date calendar, party makeup (count + occasion) or bride (her four functions, each with its own date, plus
  family party makeups), Delhi NCR area chips or outside Delhi NCR + venue and ready time, details + policy checkbox,
  then a WhatsApp to her number with her own list filled in (her "Idle time" typo written as "Ideal"). `#studio`:
  requests pipeline (request, quote sent, advance paid, confirmed, done) with one-tap next message, season, advances.
  Sample: party price ₹8,500 each, bridal "personal quote", the 30% advance and policy lines, booked dates and studio
  clients. Photos cropped from her grid and profile into `img/`.
- `mehak-oberoi`: Mehak Oberoi (@mehakoberoiofficial, verified, 10.8K followers, 405 posts), Delhi MUA, "Certified
  Luxury Makeup Artist from @meerasakhrani @bhumikabahlofficial & @makeupbypratiba". Bookings: Call/WhatsApp
  +91 87449 19289. Her DM reply: "For which makeup?" then "share your date, location and ready time along with category
  of makeup". Her "Important note" highlight (used word for word): the time you share is your ready time, not the start
  time, meaning completely ready with makeup, hair and draping done; bookings are taken as per the ready timings
  communicated. Blush/mauve page (from her note card) on the Rupangi base: category of makeup + people (or bridal +
  family makeups), date calendar, Delhi NCR area or outside + venue + ready time with her note, details + "I've read
  Mehak's note" checkbox, then a WhatsApp to her number answering her four questions in her order. `#studio`: requests
  pipeline with one-tap next message (the advance message restates her ready-time rule), season, advances. Sample: the
  category list and prices (engagement ₹18,000, party/festive ₹6,500, bridal personal quote), 30% advance, travel line,
  booked dates and studio clients. Photos cropped from her grid (family selfies with children left out).
- `monalisa-patel`: Face Stories by Monalisa Tejas Patel (@facestories_by_monalisa, verified, 9,024 followers, 436
  posts), luxury makeup artist, Sindhu Bhavan, Ahmedabad, works globally; "Bookings are open for 2026-27"; highlights
  2026 brides, curls, siders, shoot work, hair goals. Her Instagram DM reply: "pls share your details on 7859972820", with
  no form or list, so the page collects those details for her. Black/champagne/emerald page on the Mehak base: look
  (bridal, engagement/reception, siders/party, shoot) + people or family makeups + hair styling add-on, date calendar,
  Ahmedabad area or outside + venue + ready time, details + policy checkbox, then a WhatsApp to +91 78599 72820
  ("Sharing my details as you asked"). `#studio`: requests pipeline with one-tap next message, season, advances.
  Sample: all prices (engagement ₹15,000, siders ₹5,500, hair ₹2,000, bridal and shoot on quote), the policy, ready-time
  wording, booked dates and studio clients. Photos cropped from her grid (the "Brides by Monalisa" watermark cropped out).
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
