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

**2 — What: the claim.** Headline: *European freight forwarding still runs on people doing
the data work by hand.* Three cards: `€3.4bn a year` — the annual labour value of the work
being done by hand across the European market (*source: SQRlane analysis*); "No product
problem" — the software exists, buying more of it does not remove the hours, because the
hours are going into moving information *towards* the software; "A labour problem nobody has
priced" — we are not displacing a competing tool, we are displacing spreadsheets and hours.

**3 — What: what the work actually is.** Three cards — **Quoting** (rates rebuilt by hand for
every enquiry, across carriers that publish nothing in a common format), **Track and trace**
(status chased by email and phone, then retyped into the system so the customer can be told),
**Documents and exceptions** (every mismatch escalates to a person, because the system that
spots it cannot resolve it). Below, two wider cards: `~30 parties · 200+ interactions` for one
refrigerated shipment East Africa to Europe (*Maersk shipment trace, 2014*), and "And that was
2014" — before chat and messaging apps became operational infrastructure in freight; the
interactions have not reduced, the channels carrying them have multiplied.

**4 — What: where the hours go.** Headline: *Sixty percent of the day is spent carrying
information, not deciding anything.* A dark card with `60%` — of the working day goes to
coordination: chasing status, searching for information, switching apps; only 40% goes to the
skilled work (*Asana, Anatomy of Work Index 2022*). Beside it, "The five things that eat it":
finding it, retyping it, deciding what is true, switching, one person holding it.

**Then the sentence that makes the figure safe, and do not drop it:** coordination that needs
*judgement* — negotiating a rate, deciding a reroute — is what the forwarder sells;
coordination that only *carries information* from one place to another is not; we take the
second. Without it, a reader says "coordination is literally the job" and the figure argues
against you.

**5 — What: why the record is never right.** Headline: *A booking's true state is assembled in
someone's head. The system holds an old, partial copy.* Three figures: `under 40%` of freight
forwarders use a forwarding management system at all, and only 23% have digitised three
quarters of their processes (*Magaya, State of Digitization in Freight Forwarding 2025 — survey
of 71 forwarders, November 2024*); `1,300+ a day` emails filed by hand by one chartering desk
(*Viterra, via Sedna*); `~10 apps` and about 25 switches between them per person per day
(*Asana, 2022*). Close: the booking is agreed over email, the rate amended in a chat, the
carrier's exception notice arrives somewhere else again — none of it reaches the record on its
own.

**5b — What: why it persists.** Headline: *Nobody has fixed it because hiring works.* Three
cards: the substitute is headcount, not software; there is often nothing to integrate with
(most forwarders have no system of record, and the channels are conversations not systems); and
the dark one — **so cost scales with volume**, winning a bigger customer means hiring against
it, and the margin problem gets worse exactly when the business gets better. Close on that:
it is not an efficiency story, it is a ceiling on the business.

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
