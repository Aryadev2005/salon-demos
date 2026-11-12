# Handoff: UK website + Google visibility outreach (as of 12 Nov 2026, 15:30 IST)

Paste this into a new chat and attach both repos: `Aryadev2005/salon-demos` and `Aryadev2005/trades-demos`.

## Goal
- Short term: first paying client from UK local businesses (target was £300 in 24h).
- Medium term: ₹1 lakh/month recurring (≈ £900/month ≈ 20–30 clients on a monthly plan) within ~6 months.
- Owner: Aryadev (WhatsApp +91 86378 59578). Business name for outreach not decided (Codzo or Tenbits); messages use just "Aryadev".

## What exists
### salon-demos (hair, nail, beauty salons, barbers)
- `build.py` + `template.html`: one data-driven salon site per entry in `leads.json` → `demos/<slug>/index.html`.
  Supports: `colors` (brand palette override), `pitch` (top banner with WhatsApp to Aryadev), `bridal` band (used as
  "Christmas & New Year", `nav` renames the menu link), optional reviews/rating, `tel:` booking, og/link-preview tags.
- `scripts/places_to_leads.py` + `scripts/prospects.json` (Wigan area) / `scripts/prospects-affluent.json` (Harrogate + Cotswolds):
  Google Places (New) search → filter (no own website, rating/review thresholds, UK only, chains/tanning/`exclude_types` skipped)
  → photos, hours, reviews, accent colour → leads.json → build → `out/outreach.csv`. Cached in `cache/places/` (git-ignored).
  `--dry-run`, `--limit`, `--config`, `--max-requests`, `--rebuild-sheet`.
- `scripts/review_card.py`: printable A6 Google-review QR card PNG (free gift in outreach).
- `hosting/`: one Vercel site **salon-previews.vercel.app** serves `/<slug>/` by loading the page from GitHub `main`
  (`l.js`). `hosting/make_stubs.py` writes per-salon pages with link-preview tags (git-ignored, deployed by uploading files).
  Preview cards are live only for the Harrogate/Cotswolds batch; Wigan salons still show a bare "Preview" card.
- Hand-built demos (separate Vercel projects): phoenix-wigan.vercel.app, norman-philip-wigan-jade.vercel.app,
  suzannes-wigan.vercel.app, thebridalstylist-wigan.vercel.app (bridal enquiry flow + morning timeline + pipeline board).

### trades-demos (roofers, plumbers, electricians, builders)
- Existing template + `build.py`; Vercel project **trades-demos** is git-connected → every push deploys to trades-demos.vercel.app.
- `scripts/places_to_trades.py` + `scripts/prospects.json` / `prospects-affluent.json`: same pipeline for trades
  (min 4.6–4.7★, WhatsApp mobiles ranked first, quote form → WhatsApp, never claims insurance/accreditations).

## Vercel
- Team `team_R8dnIkhLDS0gEbWExrdjfKCI`. Projects: salon-previews, trades-demos, phoenix-wigan, norman-philip-wigan, suzannes-wigan, thebridalstylist-wigan.
- Vercel Authentication (Standard) is on but production domains are public (checked).
- Vercel's GitHub import for salon-demos was rate-limited, so salon-previews is deployed by uploading files, not git.

## Google API
- Places API (New) key was pasted in the old chat: **rotate it** and restrict to Places API; set a $10 budget alert.
- Workspace network allowlist must include `places.googleapis.com` and `*.googleusercontent.com`.
- ~420 requests used so far, within free tiers. Search $40/1k after 1k free; photos $7/1k after 1k free.

## Leads (61 total)
- Wigan area (sent 11 Nov night): 27 salons + 10 trades + 4 hand-built (Phoenix, Norman & Philip, Suzanne's, Bridal Stylist).
  Marked `contacted` in leads.json.
- Harrogate / Cotswolds (built 12 Nov, not yet confirmed sent): 15 salons + 5 trades.
- Declined: **Magic Scissor** (Wigan barber) and **Mr Cut** (Wigan barber, walk-ins only, "we don't do bookings").
  Marked `declined`; never message again. Mr Cut was offered a free review card as a goodwill gesture.
- Aryadev has sent the reframed follow-up up to and including Mr Cut (row 6 of all-leads-reframed.csv).

## Current pitch (value first)
1. First message, no link, no price: their Google ranking for "[service] in [town]", the 3 businesses above them (rating,
   reviews, website or not), note if lower-reviewed competitors with websites outrank them, marketplace commission if they
   use Treatwell (35% + VAT) / Fresha (20%) / Booksy (30%) on new marketplace clients. Offer a free review QR card.
2. After yes: send their QR card + message 2 (demo link, "only pay once it's live and you're happy").
- Files delivered in old chat: `pitches-after-mr-cut.csv` (rows 7–60) and `review-cards.zip` (53 cards). Regenerate with
  `scripts/review_card.py` if lost.
- Price in sheets: £300 one-off or £39/month. **Aryadev has been quoting £400**; confirm and update `price` in configs.

## Lessons so far
- Barbers are walk-in businesses: booking-led pitches don't land. Pitch reviews / walk-in visibility, or skip barbers.
- Bare link previews from an unknown +91 number look like spam; ask before sending a link.
- Affluent towns: salons are under-digitised; trades mostly already have websites (5 of ~450 qualified).
- Auto-picked Google photos need a 30-second look (selfies, kids, stock art, flyers, wrong business types slip in).

## Open next steps
1. Update message 2 for the 10 remaining barbers to be walk-in focused (hours, directions, "walk in now").
2. Decide £300 vs £400 and business name; update configs.
3. Send Harrogate openers; send Wigan follow-ups (rows 7–40) on 13 Nov, not same day.
4. Publish link-preview pages for Wigan salons (`hosting/make_stubs.py`, upload to salon-previews).
5. Track replies (contacted / replied / yes / paid). After ~500 contacts, measure close rate.
6. Next markets to test: Dubai (10 demos) once UK reply data is in. Paid offer to move toward: "Google growth"
   £79–149/month (site + Google profile + reviews + AI-visibility check), not one-off sites.
7. LinkedIn: build-in-public posts (don't name prospects without permission).
