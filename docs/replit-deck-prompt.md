# Replit prompt — the SQRlane pitch deck

Copy everything between the rules into Replit Agent as a single message. It is written to
produce the same deck as `static/deck.html`, without needing this repo.

Two things it deliberately does **not** leave to the model: the market statistics (they are
supplied with their sources, so nothing gets invented) and the team bios (they stay as
visible slots, because a plausible-sounding placeholder is how a fake founder ends up on
screen).

---

Build me a **single self-contained HTML file** called `index.html` — a pitch deck for a
company called **SQRlane** (pronounced "square lane"). No framework, no build step, no
dependencies, no external requests of any kind. All CSS and JS inline in the one file.

## What SQRlane is

Freight forwarders lose hours moving information between systems, and even then, risk goes
unaccounted for — a drop in Rhine water levels or a strike at the Port of Hamburg quietly
shrinks margins. SQRlane puts AI agents on top of the forwarder's existing TMS (transport
management system). The agents read the bookings out of the TMS, watch everything that moves
a trade lane, decide per booking whether to reroute or hold and record why, draft the carrier
and customer emails, and queue the resulting change back onto the same booking. A human
approves everything. Nothing sends itself, nothing is written without sign-off. They also
handle RFQs and quoting, inbound and outbound comms, documents, booking amendments, invoice
reconciliation and customs.

The one-line positioning: **risk → decision → communication → the system of record, closed.**

## Design — this matters as much as the content

- **Monochrome only.** Off-white page (`#fafafa`), white cards (`#ffffff`), near-black ink
  (`#171717`), and greys (`#4d4d4d`, `#8f8f8f`, `#ebebeb`, `#dbdbdb`). Hairline borders at
  `rgba(0,0,0,.08)`. **No accent colour anywhere.** One dark-filled card per slide at most,
  used to mark the single most important point.
- **Minimal, editorial, lots of white space.** Think Vercel/Geist or Linear: tight negative
  letter-spacing on headings, generous line-height on body, one idea per slide.
- **Type:** Geist if you can self-host it, otherwise a neutral system sans
  (`-apple-system, "Segoe UI", Helvetica, Arial, sans-serif`). A monospace face for eyebrows,
  labels, figures and source citations — that contrast does most of the design's work.
  **Do not load fonts from a CDN**: this gets presented on other people's wifi.
- Cards: 12px radius, 1px hairline border, `0 2px 2px rgba(0,0,0,.04)` shadow. Controls 6px.
- No icons, no illustrations, no stock imagery, no gradients, no animation beyond a smooth
  scroll.

## Behaviour

- One slide per screen: a scroll container with `scroll-snap-type: y mandatory`, each slide
  `min-height: 100svh` and `scroll-snap-align: start`.
- **Keyboard:** →/↓/Space/PageDown next, ←/↑/PageUp previous, Home/End to the ends. Any
  modifier key (Cmd/Ctrl/Alt) defers to the browser.
- A slide counter bottom-right (`03 / 14`) and a 2px progress bar along the top. Keep the
  counter honest when someone scrolls by hand — use an `IntersectionObserver` at 0.5
  threshold, not just the key handler.
- **Print to PDF must give exactly one page per slide.** `@page { size: A4 landscape; margin: 0 }`,
  `break-after: page` on each slide, chrome hidden.
- **Critical:** size vertical spacing and type against **both** viewport width and height —
  e.g. `clamp(24px, min(3.6vw, 5.2vh), 46px)`. A slide sized only against width overflows on
  a 1280×720 projector, and under mandatory snapping an overflowing slide is not merely tall,
  it is unreachable. Verify every slide fits at 1280×720, 1440×900 and 1920×1080.
- Below ~620px tall or ~820px wide, turn snapping off and let it be an ordinary scrolling
  document.

## Slides

**1 — Cover.** "SQRlane" with "square lane" beside it. Headline: *Trade-lane risk, decided.*
One paragraph of positioning. Four small cards previewing the four sections. Footer:
Confidential, date slot, contact slot.

**2 — What: the problem.** Headline: *Forwarders spend the day moving information between
systems — and the risk still goes unaccounted for.* Under it, a framing line: about **80% of
world trade by volume moves by sea**, much of it through roughly a dozen chokepoints — a
forwarder's entire book runs through a handful of places that can close. *Source: Boston
Consulting Group.* Then two cards: "Re-keying is the job" (the
booking is in the TMS, the rate is in a mail, the exception is in a carrier notice — every hop
is a person retyping what a system already knew) and "Nobody owns the lane" (a disruption
doesn't arrive as an alert on the booking it affects; it arrives as a short margin a quarter
later). Close: both halves have one root — the decision and the system of record are in
different places, and a person is the bridge.

**3 — What, proof one: the information costs more to move than the box.**
Three figures, each with its source printed under it:
- `~30` — people and organisations touched by a single refrigerated shipment from East Africa
  to Europe. *Source: Maersk shipment trace, 2014.*
- `200+` — separate interactions between them, for that one container. *Same source.*
- `1,000,000+` — staff across 19,000+ European forwarding, logistics and customs companies.
  *Source: CLECAT.*

Close: the bridge between systems isn't software, it's a million people typing — and it's the
industry's largest controllable cost base.

**4 — What, proof two: disruption is routine, and there is often no good answer.** Headline:
*A month-long disruption every 3.7 years — and, at some chokepoints, nowhere better to go.*
Three figures:
- `3.7 yrs` — average interval between supply-chain disruptions lasting a month or longer.
  *Source: McKinsey & Company, "Risk, resilience, and rebalancing in global value chains", 2020.*
- `45%` — of one year's profit: the average cost of those disruptions across a decade.
  *Same source.*
- `3 of 14` — of the world's main maritime chokepoints have **no viable alternative route**;
  at others, rerouting adds **more than 40%** to the distance. *Source: Boston Consulting
  Group, "Rerouting around maritime chokepoints can add significant time and cost".*

Close, and make this the argument of the slide: frequency is only half of it. When a
disruption lands on a chokepoint with no viable alternative — or one whose detour costs weeks
— **there is no obvious right answer**. Someone has to make the call, per booking, and be able
to defend it. **That is why an alert is not enough.**

Footnote: the 45% is the cost to the *shippers* whose cargo the forwarder moves, and
chokepoint exposure is likewise mapped for shippers — but the forwarder is who they call when
one closes, and the forwarder is who has to decide. Naming that bridge matters; without it a
reader asks why shipper-facing statistics are in a forwarder-facing deck.

**5 — What, proof three: one lane, one autumn, real money.** Headline: *The Rhine fell in 2018.
The gauge readings were public, free and daily the entire time.*
- `€250m` — additional costs BASF attributed to the supply disruption from low Rhine water
  levels. *Source: BASF reporting, 2018.*
- `−1.5%` — fall in German industrial production in November 2018 attributed to the low-water
  period. *Source: Kiel Institute for the World Economy.*
- `−0.4%` — the corresponding drag on German GDP. *Same source.*

Close, and make this the emphasised line of the whole deck: **the information was never
missing.** The Kaub gauge posts a water level every few minutes, free, to anyone. What was
missing was anything reading it *against a book of bookings* and deciding, per booking, what
to do.

**6 — Why: the gap.** Three columns. Left: supply-chain risk platforms (Everstream Analytics,
Interos, Resilinc, Prewave) — they stop at the alert, never touch a booking, mostly read the
same wires, and are enterprise-priced. Right: TMS and visibility platforms (CargoWise, Riege
Scope, Descartes, Transporeon, project44) — they hold and move the booking *after* someone has
decided, and don't watch the world. Middle, dark-filled: **the desk** — a person reading the
alert, working out which bookings it touches, deciding, writing two mails and re-keying the
consequence, one booking at a time. That is the gap, and that is SQRlane. Add a footnote that
these systems are named for positioning only and none is connected.

**7 — Why: market.** A four-row ladder, label / figure / description:
- TAM — `€208.1bn` — global freight-forwarding market, 2025, growing to €233.0bn by 2030.
  *Source: Transport Intelligence, Global Freight Forwarding Market Size & Forecasts 2025–2030.*
- SAM — `19,000+ firms` — European forwarding, logistics and customs companies, 1,000,000+
  staff. *Source: CLECAT.*
- Beachhead — `[n] accounts` — mid-size DACH & Benelux forwarders, 50–500 staff, already on a
  modern TMS. Big enough to feel the re-keying, too small to employ a risk analyst.
- SOM — `[€n] ARR` — `[n]` accounts × `[€n]` ACV. Priced per seat on the desk, not per shipment.

Footnote, and keep it: €208bn is the industry's *revenue*, not its software budget — the
number worth arguing is the share of operating cost this replaces.

**8 — Why now, and what holds.** Three cards: disruption stopped being episodic; per-token
inference made a judgement call per booking cost cents rather than a data-science team;
modern forwarding systems finally expose the booking over an API. Then three more: the
write-back is the moat (alerting is commoditised, being trusted to change a booking is earned
per account and doesn't transfer); the reasoning trail compounds; breadth is hard to copy
cheaply. Footnote: we don't claim to be first to alerting — the claim is first to carry the
decision all the way back onto the booking.

**9 — How: the loop.** An inline SVG, monochrome: five boxes left to right — **TMS** (read the
book) → **Watch** (42 sources, six families) → **Decide** (reroute · hold · on plan) →
**Draft** (carrier · customer) → **TMS** (queued, not written) — with a return line curving
from the last box back under to the first. **Both end boxes are filled solid black and both
say TMS**: the loop closes where it opened, and calling the last one anything else makes it
read as a second system. Draw the return line in ink at full weight, not grey — it is the
claim the diagram makes, not a connector. Label it `every action, back onto the same
booking`, and put that label in a *gap* in the line rather than on an opaque rectangle laid
over it, so it works on any background colour. Under it: `exception flag · discharge port ·
routing code · revised ETA · communication log`, then `QUEUED — not written. Waiting on a
person.`

**10 — How: what it watches.** Six cards with counts — News 31, River gauges 3, Weather & sea
state 3, Seismic & natural hazards 2, Government filings 2, Reference rates 1. Then two cards:
"Prose goes to the model, numbers never do" (a gust, a wave height, a magnitude and a water
level are classified by threshold — cheaper, repeatable, and it cannot hallucinate a severity)
and "Nothing is load-bearing" (every source is its own function inside a shared budget, read
concurrently; a source that is down or slow is reported failed and skipped).

**11 — How: scope.** Six cards — Risk · Routing · Comms (mark these "running today"),
RFQ · Quoting · Rate, Inbox · Documents, Booking · Milestones, Invoice · Customs, and a
dark-filled card: **nothing sends, nothing writes** — every mail is `DRAFT — not sent`, every
record change is `QUEUED — not written`, one approval queue grouped by booking.

**12 — How: where the build actually is.** A five-row ladder, plainly labelled: *Real* — risk
detection (all 42 sources read live on every run). *Real* — the reasoning (model-made, with a
recorded trail and a badged deterministic fallback). *Demo* — the TMS connector (both
directions modelled, but no TMS is contacted: no vendor, no credential, no endpoint).
*Synthetic* — the bookings (seven authored shipments, so a disruption can be shown on demand).
*Next* — the first live TMS integration.

**13 — Team.** Two founder cards and two supporting cards (why this team; advisors and design
partners). **Leave every name, role and bullet as a visible placeholder** — a dashed grey
chip, monospace, obviously empty. Do not invent founders, do not write plausible-sounding
filler bios.

**14 — Close.** The ask (amount, stage, runway — all placeholders), what it buys (placeholder
bullets), and contact. Footer: the full source list for every figure in the deck.

## Rules — do not break these

1. **Never invent a number.** Every statistic in this deck is supplied above with its source.
   Print the source under the figure. If you want to add a figure I have not given you, don't
   — leave a placeholder instead. Where I have marked a figure as unconfirmed, keep it as a
   visible placeholder; do not fill it with a plausible guess.
2. **No performance, accuracy or traction claims about SQRlane**, and no period-over-period
   deltas ("+12% vs. last quarter"). There is no history to compare against, so any such
   number would be fabricated.
3. **Every placeholder must look like a placeholder** — a dashed border and grey monospace
   text. A placeholder that reads like real copy gets presented by accident.
4. **Nothing loads from another host.** No CDN, no Google Fonts, no analytics, no images from
   a URL. The deck must render fully with the network switched off.
5. Keep the code readable and lean — one file, no cleverness. Add short comments only where a
   choice is non-obvious.

When you are done, tell me how to open it, how to present it (keys), and how to export a PDF.
