# CLAUDE.md

Guidance for Claude Code working in this repository.

---

## What this project is

**SQRlane** ("Trade-lane risk, decided") — a demo-grade AI-agent prototype for freight
forwarding. The product name and identity are our own: **never borrow 5U AI's name,
colours, taglines or Worker names**, and never invent a metric — no traction, accuracy or
percentage claims. Real reasoning on synthetic shipments is the honest pitch, and a
sharp audience catches invented numbers.

**SQRlane works through the forwarder's TMS. That is the product, not a feature of it.**
It is not another book to keep: the bookings are read out of the system of record, the
agents decide against those records, and every action they take is written back onto them.
Risk → decision → communication → the system of record, closed. Nothing the agents do
happens beside the TMS.

Small agents watch **everything that moves a trade lane**, not just the news: 42 free, keyless
sources across six families — news in multiple languages, river gauges, port weather and sea
state, seismic and natural-hazard feeds, government filings, and the reference rate a reroute is
billed at. When a disruption hits, the system checks which of those bookings are affected,
decides whether to **reroute** or **hold** each one — and *explains why* — drafts the carrier and
customer emails a human would need to send, and queues the booking change each decision implies
back into the TMS: the exception on the booking, the new discharge port, routing code and ETA,
the drafted mail on the communication log. Every message and every write waits for a person. A
light "5U AI-style AI Worker" wrapper sits on top purely as demo framing.

**In this build the TMS is a demo connector** (`src/tms.py`), and that word is on screen
everywhere it is surfaced. Both directions are modelled and the read is genuinely the only
door to the book — `tests/test_tms_is_the_system_of_record.py` fails if anything else in
`src/` opens it — but no TMS is contacted: no client, no credential, no endpoint. A
write-back is a dict describing a change, and it stays a dict. **Never present the
connector as a live TMS link, and never quietly drop the "runs through the TMS" framing
either — the first is a lie about this build, the second is a lie about the product.**

**The problem it models:** forwarders watch for disruptions *and* react to them by hand, and both
halves are worse than they look. The watching is **narrower than the problem** — a lane is moved
by a strike, a gale over the crane, a river that has dropped, a swell off the Cape, a wildfire
across a rail leg and a tariff filed in Washington, and those arrive from broadcasters, waterway
authorities, weather services, seismic networks, government registers and central banks in that
many different formats. Someone reading trade press between other calls sees a summary of a
fraction of it, late; anything that surfaces first in a non-English source is later still.
Incumbent risk tools (Everstream, Interos, Resilinc) stop at the alert — they don't decide or
act, they mostly read the same wires, and they're priced out of the mid-market. On the other
side, the TMS and the visibility stack hold the booking and move it once someone has already
decided it should move — they don't watch the world. The desk is the manual bridge between the
two, and **re-keying each decision into the TMS is the plank of that bridge that eats the day**.

**Modelled end user:** Head of Operations at a mid-size DACH/Benelux forwarder.
**Actual audience:** whoever is being shown the demo — a forwarder ops lead, investor, or interviewer.

### The two differentiators (the whole story — nothing else)

**The second one is the bigger one.** Say so.

1. **One terminal for everything that moves a lane.** Not a news monitor. **42 sources in six
   families**, read together on every run: news (11 GDELT queries + 20 feeds), river gauges,
   port weather and sea state, seismic and natural-hazard feeds, government filings, and
   reference rates. Prose goes to the model; a gust, a wave height, a magnitude and a water
   level go to a threshold, which costs nothing and cannot hallucinate. Two things follow:
   reading *close* to the event is why a disruption often lands here before the wires carry
   it, and reading *widely* is why it lands here at all when it never becomes a headline.

   **Breadth is only safe because nothing is load-bearing.** The old rule was "wire CORE
   only — every extra source is one more thing that can break". The reason behind it still
   holds and is now enforced structurally instead: every source is its own small function,
   inside a shared budget, reporting its own failure, and the families are read concurrently
   so 42 sources cost about what the slowest family costs. If a new source can make the
   cycle fail, it is wired wrong.

   **The website never names a language.** Multilingual reading is one *mechanism* among
   several, not the pitch — the edge is breadth and source proximity, and it holds wherever
   in the world the event happens. Naming a language makes a general capability look like
   one rehearsed trick, so the UI says "regional" and "international wires" throughout. Real
   outlet names (Al Jazeera Arabic, DW Deutsch) are fine: those identify a source, they do
   not claim an edge. `tests/test_the_pages_keep_their_promises.py` holds this on the landing
   page and the dashboard, reading past comments — a word that appears only in a `/* ... */`
   explaining why it is avoided has not been said to anyone. **The whitepaper is the
   stated exception**: it has to say where a model came from ("a German research
   consortium", "Mistral is French"), and that is provenance, not a claim about the
   detection edge. See [The detection trail](#the-detection-trail).
2. **The agent does the TMS work — a closed risk → reroute → comms → record loop, with
   recorded reasoning. This is the biggest value in the product.** Risk incumbents stop at
   the alert; execution players start after the decision and don't touch risk. Between them
   sits a person re-keying consequences into the booking system, one booking at a time,
   because that is the only place a decision counts. Welding them — reading the book out of
   the system of record, deciding, recording *why*, and putting the result back on the same
   record as a queued change a human approves — is the whitespace. The loop opening and
   closing in the same place is what makes it operational rather than advisory: a decision
   that never reaches the TMS is a decision nobody acts on.

### The build owner

The repo owner has **no coding experience** and is not writing code by hand — they paste the
phase prompts from `BUILD-GUIDE.md` into Claude Code. So: explain what you built and **how to run
it**, in plain language, at the end of every phase. Prefer obvious code over clever code.

---

## Current state

**All five phases are built.** The demo runs end to end: `uvicorn src.app:app --reload`, then open
http://127.0.0.1:8000 for the landing page and http://127.0.0.1:8000/app for the board with
the button. `README.md` is the front door for anyone new.

It is also **deployed on Vercel** and running against the live Groq key there.

**The source layer was widened from 20 to 42** — eight structured public APIs added on top of
the news feeds, so the board reads weather, sea state, seismic activity, natural hazards,
government filings and reference rates as well as headlines. All eight are keyless and all
eight are unwitnessed from the build sandbox, which blocks every third-party host at the
proxy; they are covered by stub tests and by graceful degradation, and
[What still needs a human](#what-still-needs-a-human) says what to check before presenting.

Three claims still need a human to judge them — see
[What still needs a human](#what-still-needs-a-human) below. Everything else is verified.

> **Path note:** `DESIGN.md` shows the tree rooted at `trade-risk-agent/`. The repo is
> `sqrlane.com` on GitHub and may be checked out under an older directory name. Build at the
> **repo root** — `src/`, `data/`, `static/` go directly here. Don't create a nested
> `trade-risk-agent/` folder.

---

## The demo narrative — this IS the spec

Everything serves this. **If a feature doesn't help this story land, it doesn't get built.**
Target: runs start to finish in **under ~2 minutes**, on command, without breaking.

1. **"Here are 7 bookings out of your TMS, in transit."** Dashboard shows 7 shipment cards,
   all green. Every one is a record read through the connector — the board is a view of the
   book, not a second copy of it.
2. **"Watch — a strike hits the Port of Hamburg."** Click a trigger button.
3. **"The system caught it from a German-language source before the English news wires."** The risk
   feed shows the event, flagged as detected from a German source first — and under it, the
   family strip showing the other 41 sources read on the same run, with the instrument
   readings and the board context below that. Breadth first, then the lead.
4. **"It triaged the whole board in seconds."** Cards change state — two reroute, one hold,
   four stay green (the system doesn't cry wolf).
5. **"Here's the reasoning for each decision."** Click a rerouted card → plain-English justification
   (slack vs. added transit vs. strike delay).
6. **"And here are the emails it drafted."** Two drafts appear — carrier and customer. *Nothing is sent.*
7. **"And here is what goes back into the TMS."** The changes each decision implies, queued
   against the booking they came from — exception, discharge port, routing code, ETA,
   communication log — each one `QUEUED - not written`, waiting on a person. The bookings
   left on plan queue nothing, which is a real answer.
8. **"All of that, from one news event, on command."**

### The honest line (keep it visible in the UI)

> "The risk detection is real — it runs against live news right now. The shipments are synthetic, so
> I can show you a disruption on demand instead of waiting for one."

This is why the Risk Monitor stays **genuinely live** even though everything downstream runs on
authored data. The injected strike uses the **same event format** as live events so it flows through
the real pipeline.

---

## Architecture — five components (the Risk Monitor is in two files)

The loop opens and closes in the same place. That is the shape of the product: the agents
work on the TMS's records, not on a book of their own.

```
  [ TMS link ] --read_bookings()--> the book: every shipment on the board
        |  (src/tms.py - the ONLY door in. Nothing else opens shipments.json)
        v
  [ Risk Monitor ] --writes--> risk_state.json
        |  (42 keyless sources, read concurrently, in six families:
        |   news GDELT/RSS, river gauges, weather + sea state, seismic
        |   + natural hazards, government filings, reference rates.
        |   The prose half is risk_monitor.py, the instruments are signals.py)
        v
  [ Orchestrator ] --reads shipments + risk--> decides which shipments are affected
        |
        v
  [ Route Advisor ] --per affected shipment--> reroute | hold | no-action + reasoning
        |
        v
  [ Comms Agent ] --per actioned shipment--> draft carrier email + customer email
        |
        v
  [ TMS link ] --writebacks_for()--> every agent action as a change to the booking:
        |   Risk    -> exception_flag on the booking
        |   Routing -> port_of_discharge / routing_code / eta / booking_status
        |   Comms   -> each draft filed on the communication_log
        |   all of it QUEUED - not written, behind the approval gate
        v
  [ Dashboard ] <-- shipment states, reasoning, drafts, the write-back queue;
                    has the trigger button
```

0. **TMS link** (`src/tms.py`) — both ends of the loop. `read_bookings()` is the only door to
   the book: every component that needs shipments resolves back to it, so the day the
   connector points at a real TMS the whole board follows. `writebacks_for()` turns each
   agent's output into the change it implies on that record, named by the Worker that made
   it and gated. Imports nothing but `json`, `datetime` and `config` — no client, no
   credential, no endpoint.
1. **Risk Monitor** (the real, live part) — reads all 42 free sources at once. Prose (GDELT,
   RSS, Federal Register filings) is LLM-classified for logistics relevance → chokepoint /
   type / severity; numbers (gauges, gusts, wave heights, magnitudes, hazard coordinates) are
   classified by threshold in `signals.py` and never reach the model. Writes `risk_state.json`.
   Also loads the injected Hamburg event in the same format.

   **Two tiers, and the line is not cosmetic.** A `lane` source produces readings that map
   onto a chokepoint some route passes through, so it can move a booking. A `context` source
   is real, read live, and moves nothing on this board — the ECB rate a reroute is billed at,
   a hurricane warning over a US port this board does not call at, a typhoon signal over a
   load port that is not modelled as a chokepoint. Context is rendered in its own panel
   saying exactly that. A test asserts a context source never emits an event; the day one
   does, the board is inflating its own alarm count.
2. **Route Advisor** — maps each candidate route's chokepoints against active risk; LLM weighs
   **schedule slack vs. added transit vs. expected disruption delay** → `reroute` / `hold` /
   `no-action` + plain-English reasoning + a recorded reasoning trail.
3. **Comms Agent** — LLM drafts a carrier email (booking change / hold instruction) and a customer
   email (status + revised ETA). Returns text. **Sends nothing** — no email library, no SMTP.
4. **Orchestrator + Dashboard** — on trigger: read the book from the TMS → refresh risk →
   Route Advisor over all bookings → Comms Agent for actioned ones → queue every action back
   into the TMS → one result object → rendered as cards, risk feed, expandable reasoning,
   drafts and the write-back queue.

### The product layer

**Thirteen Workers, three of them real.** Risk, Routing and Comms genuinely run and are
tagged `LIVE`. Rate, Milestones, Docs, Inbox, RFQ, Booking, Invoice, Customs and Assistant
replay authored data from `src/roster.py` and are tagged `SCRIPTED`. **The tag is the
honesty** — never present a scripted Worker as reasoning live. They are still *reactive*:
each panel is built from the active scenario and the selected shipment, so switching either
visibly changes it. What is authored is the content, not the shape.

**The TMS Link is the exception, and carries its own tag** — `mode: "demo"`, rendered
`DEMO`. Nothing in it is replayed: its write-backs are derived from the decisions the real
advisor made on that run, and its summary reports what the run actually read and queued.
What makes it a demo is the far end, not the content, so calling it `SCRIPTED` would be
untrue in one direction and calling it `LIVE` untrue in the other.

**Every Worker works on the same records.** A booking amendment, an invoice query, an
entry, a routing change — each one is a change to a booking that came out of the TMS.
That is what makes the roster a desk rather than a set of unrelated panels.

**Four scenarios over one shared shipment pool** (`data/scenarios.json`). The pool never
changes; the active risk event does. That is the point — the same board reacting
differently is what shows the system generalises rather than performing one trick. Each
scenario is chosen to force a *different* decision type:

| Scenario | Kind | Decision type | Outcome |
|---|---|---|---|
| `hamburg` | Port blocked | Discharge-port reroute vs hold | 2 reroute · 1 hold · 4 on plan |
| `redsea` | Chokepoint closed | Forced long-haul reroute under pressure | 6 reroute · 1 hold — whole board |
| `rhine` | Inland waterway | **Mode switch**, barge → rail/road | SHP-006 only |
| `france` | Regional inland | Land-leg reroute | SHP-007 only — **off by default** |

If two scenarios ever produce the same pattern, one is redundant.

The same three components are also surfaced as named **Workers** — Risk, Routing, Comms —
each reporting, on every run, what it actually handled: sources read, shipments triaged,
drafts written, and how many came from the model rather than the fallback. Every number
is counted from that run; nothing is illustrative.

A **decision-engine strip** names the model in use and the model-vs-rules split, so the
central claim is checkable at a glance rather than asserted.

### The element kit — ported, not imported

Two more references sit behind the UI: [`bklit/bklit-ui`](https://github.com/bklit/bklit-ui)
and [`kokonut-labs/kokonutui`](https://github.com/kokonut-labs/kokonutui). bklit-ui is
the **upstream of limns-admin** — the same chart component names — so the Geist direction
is one lineage, not three.

Both are React + Tailwind. This page is one self-contained vanilla file with no build
step, so what carries over is **anatomy, never code**:

- **Command palette** on Ctrl/Cmd-K, plus the sidebar search box. It searches the seven
  views and every booking by id, cargo, origin and destination; Enter selects the booking
  and opens its panel. It reaches something rather than decorating the sidebar.
- **One page header everywhere** — title, what the page is, actions, last-run stamp.
  Before it, some views opened with a card and some with a bare table.
- **Segmented control** on Approvals (awaiting / approved / all).
- **Empty states** that name the next action. `tests/test_the_pages_keep_their_promises.py` asserts
  zero ad-hoc `.hint` blocks survive.
- **Skeletons** shaped like the thing that is loading, so the layout does not jump.
- **Notch gauge**, after bklit's, on the shipment drawer: **slack consumed** — the delay
  against the slack the booking had. A real proportion, and the number every decision
  turns on. SHP-002 reads `100%+` in red.

Three things worth keeping:

- **Global chrome above per-view content has to stay short.** The scenario switcher
  and the Worker roster sit in one band above every view, so their height is
  subtracted from every view's first screen. As a grid of thirteen 200px cards the
  band ran ~400px, and `go()` scrolls back to the top — so on a 1280x720 laptop
  clicking *TMS link* scrolled to an unchanged band and left **two pixels** of the
  clicked view on screen. Nothing was broken; the nav simply had nothing visible to
  change, which reads exactly like a dead button. The roster is now a wrapped strip
  of pills (dot, name, mode tag; the ellipsised summary moved to the tooltip) and the
  band is ~230px. Measure `innerHeight - .view.on.getBoundingClientRect().top` after a
  nav click before adding anything to that band: if it approaches zero, the board looks
  broken however well it works.
- **The gauge figure is capped to its track.** SHP-002 is 5 days of delay against 1 of
  slack — literally 500%. A full arc labelled "500%" reads as a bug, so the headline caps
  at `100%+` and the exact days sit in the line beside it. Nothing is lost.
- **A `running` flag must be cleared before the render that consumes it.** It was being
  cleared in `finally`, which runs *after* the success path's `render()`, so every
  skeletoned view stayed on its skeleton with the real data already in hand. Two browser
  suites caught it; no unit test would have.

Not ported, deliberately: kokonutui's decorative pieces (glitch-text, liquid-glass,
background-paths) and anything needing teams or avatar stacks. The first fight a demo
that has to read clearly in a room; the second would be invented data.

### Made to be worked in, not just looked at

The board renders the run correctly; a later pass made it a thing a person can
actually operate. Four changes, each closing a hole that looked like polish and
was really a workflow:

- **Approvals is a queue, not a transcript.** Eighteen drafts rendered open ran
  **5,452px** — five and a half screens to work a queue whose entire purpose is a
  person working it, with no way to scan, select or act in bulk. It is now one row
  per item (what it is, what it changes, its gate) opening to the full body on
  demand: **1,382px**. Rows group **by booking, not by kind**, because a
  write-back's `booking_ref` *is* the shipment id — so everything waiting on
  SHP-001, both mails and all four queued changes, reads as one block. That is the
  product's own claim ("every decision lands on the booking it came from") made
  navigable instead of asserted. Bulk approve is **select-then-approve**, never a
  blind "approve everything": the count is on the button so a person sees exactly
  what they are signing off, and only unapproved rows are selectable so the count
  can never claim work already done. It is still a browser state change with no
  transport behind it, in bulk exactly as singly.
- **Every view has an address.** `#/approvals`, `#/shipments/SHP-002`. Refresh
  keeps you where you were, the back button walks the views, and a link to the
  queue is a link someone can send. Before this every reload dropped you on
  Overview and Back left the dashboard. The `hashchange` handler is idempotent by
  construction — if we wrote the hash ourselves the state already matches it and
  the handler returns — so no guard flag is needed to stop `go()` and the URL
  bouncing off each other.
- **The risk feed stopped being a dead end.** An event now names the bookings it
  moved, and each one is a button through to the board. The link was *already in
  the data* — `decision.triggering_events` carries the `event_id` — and the feed
  simply never used it, leaving a person to work out by hand which bookings a
  strike moved. That hand-work is the manual bridge this product exists to remove,
  so leaving it in the UI was the demo arguing against itself.
- **`g`-then-key navigation**, `/` to search, `?` for the sheet. Typing in a field
  is never a shortcut and any modifier defers to the browser.

Two traps worth remembering, both found in a browser and invisible to a unit test:

- **A shared class name silently reparents a dialog.** The shortcut sheet reused
  `.pal` for its geometry and took `keys` as its modifier — which collided with an
  existing `.keys{display:flex}` legend rule and laid the dialog's header and body
  out side by side. Grep the class before adding a modifier to a shared component.
- **One body flag cannot open two dialogs.** `body.pal-on` showed both the palette
  and the sheet at once; each needs its own flag, with the scrim listening for
  either.

### The simulation loop — a week, not a snapshot

The button runs **one** cycle: one set of active events, one set of decisions. That
shows the system working, not the system *operating*. `src/simulation.py` replays an
authored week over the same pool — `python -m src.simulation`, or the **Simulation**
view in the dashboard.

`data/simulation.json` holds only a timeline: which authored events activate or resolve
on which day. **The events themselves are never copied there** — they are pulled from
`scenarios.json` by id, because a second copy of an event is exactly how schema parity
has broken before.

The arc is eight days: a quiet Monday, the Hamburg walkout, the Rhine falling *while the
strike is still on*, the Red Sea closing on top of both, the strike settling, a wildfire
on a land leg, two disruptions clearing, and a board settled on its revised plan. Two
disruptions at once is the case a single-event demo never shows.

**State carries between days — that is what makes it a simulation rather than eight
independent runs:**

- A booking rerouted on Tuesday is *on* the new route on Wednesday, and is therefore no
  longer exposed to the thing that moved it.
- A held booking accrues **a day of delay for every day it waits**, and keeps that delay
  when it resumes. Holding is not free, and the week is what makes that legible.
- Every decision is still made by the real Route Advisor. Only the timeline is authored.

**One rule lives in the simulation, not the advisor:** a booking is never offered the
route it just left. Without that, SHP-001 went HAM → RTM → HAM → COGH across four days.
Each single day was arithmetically defensible — under the Red Sea closure,
Hamburg-under-strike genuinely beats Rotterdam-under-Red-Sea on "least late" — but a box
ping-ponging between two ports across a week is nonsense. The advisor was right; it just
should never have been asked. `tests/test_the_simulation_holds_together.py` asserts no
booking ever revisits a route — and, because state carrying between days is the whole
difference between a simulation and eight runs in a row, that yesterday's reroute is
still in place this morning and that a held booking pays a day for every day it waits.

It runs **deterministically by default**. Seven shipments over eight days is 56
decisions, which is far more model calls than a free tier will take; `--llm` opts in.

One booking ends the week still held, because under a persistent corridor closure no
better routing exists for it. Saying so is a real answer, not a gap, and the day's copy
says it rather than claiming the board is clear.

### The dashboard follows limns-admin

The shell is modelled on [`Franvy/limns-admin`](https://github.com/Franvy/limns-admin),
whose `design.md` is Vercel's **Geist** system. The colour, type, spacing, radius and
shadow tokens in `static/index.html` are that spec's values, so read `design.md` before
inventing a token — it almost certainly already exists.

What was taken from the reference's layout:

- **Sidebar**, 264px: grouped nav with uppercase group titles, an active item on a
  `--surface` fill, blue count pills, and — in the slot where limns lists projects — the
  **board itself**: one row per shipment, a state dot and a monospace id. The dots are real
  state, so the sidebar is the board in miniature and doubles as the shipment picker.
- **Collapse**, persisted to `localStorage` and bound to ⌘B/Ctrl-B. Restored before
  transitions are enabled, so a collapsed sidebar does not slide in on load.
- **Cards** at the 12px radius (`--r-md`) with `0 2px 2px rgba(0,0,0,.04)`. Controls stay
  at 6px (`--r`) — the spec's two radii, not one.
- **Stat cards**: label and pill on the top row, a large tabular value, a caption under it.
- **A distribution ring** with the total in the middle and a legend carrying count and
  share, in place of the reference's Plan Distribution.

**Two things were deliberately not copied, and should not be added back:**

- The reference's stat cards carry a **sparkline and a "+12% vs. previous 30 days" delta**.
  SQRlane has no history to compare a run against, so both would be invented — and an
  invented metric is the one thing this project refuses to produce. The card keeps the
  same anatomy and puts a fact from the run in the pill instead.
  `tests/test_the_pages_keep_their_promises.py` fails if "vs. previous" — or any other
  period-over-period delta — ever appears on a page.
- The bottom-of-sidebar **user card** is replaced by the decision-engine strip, which names
  the model actually in use. On a demo whose whole claim is "the model decided this", that
  slot is worth more than a fake profile.

The ring shows **board outcome** — reroute / hold / on plan — because that is a real
part-to-whole from the run. Every number in it is counted, and the shares are asserted to
add to 100. Beside it, in the slot where the reference puts its revenue chart, is
**schedule pressure**: each shipment's slack against the delay the disruption imposes.
That is the advisor's own arithmetic drawn — where the delay bar clears the slack bar
there is no clean answer, which is exactly SHP-002.

### Chart colour is computed, not chosen

Series colours live in their own tokens (`--s-slack`, `--s-delay`, `--s-reroute`,
`--s-hold`, `--s-plan`), **not** the UI's `--blue` / `--amber` / `--green`. Those are
tuned for text contrast, and reusing them put "Held" and "On plan" at **ΔE 5.6 under
deuteranopia** — a deuteranope could not tell the two slices apart. That shipped
undetected until the palette was actually run through a validator.

Every set is checked against its own surface for lightness band, chroma floor,
all-pairs CVD separation, normal-vision floor, and contrast. Two findings worth
keeping:

- **Dark steps are chosen, never flipped.** The light values all sit outside the dark
  lightness band (0.48–0.67), so dark mode has its own validated triple.
- **The obvious pairings are the broken ones.** Blue against purple is ΔE 1.3 under
  deuteranopia; amber against a dark green is ΔE 3.9. Greying the "on plan" bucket
  fails too — gray against amber is ΔE 13.4 to *normal* vision, below the floor that
  secondary encoding cannot excuse. The fix each time was a different step, not a
  different idea.

Gridlines are **solid hairlines**. The reference draws them dashed; dashing reads as a
threshold when it is only a grid, so that one detail is deliberately not copied.
Direct labels are selective — only the shipment whose delay exceeds its slack — because
a number on every bar goes unread.

### The workflow layer — inbound comms, RFQs and the TMS link

The Comms Agent covers *outbound*. Two scripted Workers and the TMS link cover the
rest of the desk a disruption actually lands on — the other three scripted Workers
(Booking, Invoice, Customs) are below:

- **Inbox Worker** — inbound carrier and customer mail, triaged: intent classified,
  linked to the booking, and a reply drafted. Which mail arrives is derived from the
  decision the Route Advisor made, so a reroute produces an omit-notice and a status
  chase, a hold produces berth options, and an on-plan booking produces a routine
  milestone with **no reply drafted at all**. Answering everything would be showing
  volume rather than judgement.
- **RFQ Worker** — an inbound rate request read into structured fields, priced against
  the lane with the active scenario's surcharge, and answered with a drafted quote.
- **TMS Link** (`src/tms.py`) — the **system of record**, on a demo connector. Both ends
  of the loop: `read_bookings()` is the only door to the book, and `writebacks_for()` turns
  each agent's output into the change it implies on that record — the Risk Worker's
  exception flag, the Routing Worker's discharge port / routing code / ETA / booking
  status, and each of the Comms Worker's drafts filed on the communication log. Every
  operation names the Worker that produced it, because that is the claim: the Workers do
  not work beside the TMS, they work in it. A booking left on plan produces no write-back
  at all, which is a real answer rather than an omission.

**None of it sends, and none of it writes.** A drafted reply, a drafted quote and a
queued write-back are all outbound actions, so all three sit behind the same approval
gate as an email — `DRAFT - not sent` and `QUEUED - not written`, both
`awaiting_approval`. `tests/test_comms_agent_sends_nothing.py` now checks all of them:
the original checks only ever looked at `card["drafts"]`, which none of these appear in.
The dashboard's **Approvals** view and the bell count both kinds together, because a
queue a person never sees is not a gate.

`src/tms.py` imports `json`, `datetime` and `config` — and nothing else. There is no
client, no credential and no endpoint: a write-back is a dict describing a change, and it
stays a dict. Never present the connector as a live TMS link; it says `connected (demo)`
everywhere it is surfaced, and a test asserts that.

**`tests/test_signals_read_wide_and_fail_soft.py` holds what breadth costs.** Forty-two
sources is forty-two things that can be down, slow or reshaped in front of an audience, so it
asserts the three things that have actually gone wrong here before: a structured event matches
the scripted event schema **key for key** (parity has broken three times, every time by adding
a field to one producer and not the others); a reading far from every corridor is **dropped**
rather than attached to a lane; and a `context` source **never emits an event**. Then it takes
one host down mid-read and one host's response shape sideways, and checks the rest still read.

**`tests/test_tms_is_the_system_of_record.py` holds the other half of the claim**, the one
that is easy to lose by accident. Structurally: nothing except the connector may open
`SHIPMENTS_FILE`, so there stays exactly one door to the book — a second door is how "the
board is the TMS's book" quietly stops being true. Behaviourally: all three live Workers
must have written something back on a run, every actioned booking must have a write-back,
every on-plan booking must have none, and every operation must be `QUEUED - not written`.
Note what it deliberately does *not* assert — that a TMS was contacted. It was not.

**The roster covers the desk, under our own names.** The function set a forwarding
desk actually runs — quoting, booking, shipment tracking, TMS data entry, invoice
reconciliation, and customs — is all present. The names are ours: **never** use the
names the reference product ships (`Rate Manager`, `DocuMind`, `Track & Trace`,
`Copilot`), and `tests/test_the_pages_keep_their_promises.py` fails on any of them appearing
in the dashboard, the landing page, the whitepaper, the README, the roster source, the
served Worker names, or the run payload. It caught one of those names in a source
*comment*, which is the level of paranoia this deserves.

Three of them earn their place by reacting to the decision rather than decorating:

- **Booking Worker** — the carrier booking, and the amendment the decision forces: a
  reroute is a change of discharge port, a hold is a hold at the load port, an on-plan
  booking needs no amendment at all. An amendment is an outbound action, so it is
  `DRAFT - not sent` / `awaiting_approval` like an email.
- **Invoice Worker** — reconciles the carrier invoice against the rate agreed. It only
  bites under a disruption: the carrier bills a surcharge that was never quoted, and the
  discrepancy is the finding. With no disruption every line matches and it says so.
- **Customs Worker** — the one that only exists because of the reroute. Moving the
  discharge port moves the **country of entry** (HAM → RTM is Germany → Netherlands), so a
  different EORI and clearance agent apply and the bill of lading has to be reissued. It
  **escalates rather than files**, which is the honest behaviour and matches how these
  systems are supposed to treat a novel exception.

**Both pages name the systems the connector is built to point at** — CargoWise, Riege
Scope, Descartes, Transporeon, TIMOCOM, AEB, DAKOSY, Portbase. On the landing page
they are a second band below the workflow section, styled like the sources strip; on
the dashboard they are a card in the **TMS link** view, under the connector summary.
The dashboard's is a **grid, not a marquee** — a sliding band is a marketing device,
and the dashboard is a working view. Same names, same tags, same disclaimer.

Two rules hold both:

- **It is not the sources strip.** That band is headed "Watching, keyless and in the
  open" and lists what the Risk Monitor actually reads. None of these is read, so
  putting one there would claim an integration that does not exist.
  `tests/test_the_pages_keep_their_promises.py` fails if a named system appears
  inside the sources band.
- **The disclaimer is load-bearing and lives with the names.** A row of familiar
  vendor names — in the source strip's styling, or inside a view called "TMS link" —
  reads as an integration list unless the page says otherwise, so each block carries
  "None of these is connected", "no vendor, no credential, no endpoint" and "nothing
  is ever written". The test asserts all three **scoped to the block that names
  them**, on both pages. An earlier version looked at the whole page and passed on the
  `TMS (demo connector)` further down, which meant the line could have been deleted
  with the guard still green; it was caught by deleting the line and watching the test
  not fail.

No logo is reproduced. The marks are plain pictograms of what each *kind* of system
is — a container, a gantry, a ship, a shield — the same convention the sources strip
already states in its own comment. The same eight symbols are defined in both files,
because each page is self-contained by design; on the dashboard they are `.sysmk`,
**not** `.mk`, which that page already uses for the map's lane rows. Reusing it drew
every icon as an empty bordered box.

**The connection point** is its own view in the sidebar — **TMS link**, under `System` —
not just a Worker chip: connector name, `connected (demo)`, the one-line positioning,
bookings read in, changes queued back, bookings affected, which Worker writes to which
record, the field mapping with its direction and its author, and every queued write-back
with the change it describes and its own approve button. All of it from `src/tms.py`.

**The topbar bell** carries the real pending-approval count and shows a dot only when
something is actually waiting — a permanent badge would be decoration. Clicking it opens
Approvals, and a test asserts the bell and the Approvals count agree.

Drafts sit behind a **human-approval gate**: `awaiting_approval` → *Approve* →
`approved`. Approval is a state change in the browser and nothing else — there is no
transport anywhere in `src/` for it to trigger, and a test asserts that.

---

## Stack

- **Backend:** Python + **FastAPI**. One endpoint the button calls: `POST /run`.
- **Frontend:** a **single HTML page**, vanilla CSS/JS, no framework. Calls `/run`, renders result.
  The look is part of the deliverable — clear hierarchy, restrained palette, readable in a room.
- **AI calls:** one wrapper module `src/llm.py` so the provider (Groq / Gemini / Ollama) swaps in
  **one file**. Never call a provider directly from anywhere else.
- **Data:** JSON files. **No database.**
- **Fallback:** if the web UI gets fiddly, the whole thing can be a **Streamlit** app. Default to
  FastAPI + HTML for the visual drama of cards flipping state.

### File structure (all at repo root)

The tree as it actually stands, not as it was first planned — if you add a file, add it
here too, because this is what the next session reads to find its way around.

```
├── *.md                      # the seven planning docs + this file
├── .env                      # runtime AI key — NEVER committed
├── .gitignore                # must list .env, __pycache__/, .venv/, risk_state.json
├── requirements.txt
├── vercel.json               # rewrites every path to the function; lists includeFiles
├── api/index.py              # re-exports the same FastAPI app for Vercel
├── data/
│   ├── shipments.json        # the book: seven bookings, aged forward at load time
│   ├── routes.json           # candidate routes + the chokepoints each passes
│   ├── chokepoints.json
│   ├── scenarios.json        # the four switchable disruptions
│   ├── injected_events.json  # the scripted Hamburg strike
│   ├── simulation.json       # the authored week - a timeline only, never events
│   └── geo.json              # coastlines and points for the map
├── src/
│   ├── llm.py                # provider wrapper — the ONLY place AI is called
│   ├── config.py             # keys, model names, every source list and threshold
│   ├── httpget.py            # a GET that is guaranteed to end — shared plumbing
│   ├── tms.py                # component 0: the system of record — the ONLY door to
│   │                         #   the book, and every agent action as a queued change
│   ├── risk_monitor.py       # component 1a — the prose half + the live pull
│   ├── signals.py            # component 1b — the structured half: weather, sea
│   │                         #   state, seismic, hazards, filings, FX
│   ├── route_advisor.py      # component 2
│   ├── comms_agent.py        # component 3
│   ├── orchestrator.py       # component 4 (the loop)
│   ├── roster.py             # the SCRIPTED Workers - authored, never live
│   ├── simulation.py         # the authored week, replayed over the same board
│   ├── geo.py                # the board on a map - derived from the run
│   └── app.py                # FastAPI: serves the three pages + the API
├── static/
│   ├── assets/
│   │   ├── sqrlane-loop.svg  # the loop, standalone and Figma-ready
│   │   ├── slide-problem.svg # slide 01 - the problem, editable, for Figma
│   │   └── slide-fix.svg     # slide 02 - the loop, editable, for Figma
│   ├── landing.html          # the front page (HTML+CSS+JS in one file)
│   ├── index.html            # the dashboard (HTML+CSS+JS in one file)
│   ├── whitepaper.html       # the technical paper
│   ├── deck.html             # the pitch deck - what / why / how / team
│   ├── what.html             # the What section on its own, 6 slides
│   ├── pitch.html            # GENERATED - the rebuilt deck, from build_slides.py
│   └── fonts/                # Geist Sans + Mono, self-hosted - never a CDN
├── tests/                    # eight suites, one per claim the demo makes out loud
├── tools/
│   ├── build_rhine_map.py    # regenerates the landing page's corridor map
│   ├── build_pitch_pptx.js   # the deck as a PowerPoint, with layout checks
│   └── build_slides.py       # the rebuilt deck: SVG slides + pitch.html
├── scratch/genheat.py        # one-off generator for the landing heatmap
├── docs/
│   ├── dashboard.png         # the README's screenshot
│   ├── slide-problem.png     # what slide-problem.svg renders to
│   ├── slide-fix.png         # what slide-fix.svg renders to
│   ├── problem-brief.md      # the problem, with every figure graded by source
│   └── replit-deck-prompt.md # the deck, as a prompt for a fresh Replit build
└── risk_state.json           # written at runtime (gitignored)
```

---

## The dataset (the screenplay)

Authored for **drama, not realism** — positioned so *one* injected disruption yields three
different, defensible decisions. Full tables in `DATASET.md`; turn them into the `data/` JSON files.

- **Chokepoints:** HAM, RTM, ANR, SUEZ, REDSEA, COGH, RHINE.
- **Routes:** each has discharge port, transit_days, `cost_index` (relative, 100 = baseline), and the
  chokepoints it passes. Key pair: `R-HAM-STD` (32d/100) vs. `R-RTM-ALT` (34d/108) — the +2-day
  Rotterdam alternate.

**The five the strike was authored around, and their expected outcomes — this is the
payoff.** SHP-006 and SHP-007 joined the pool later for the Rhine and France scenarios;
they touch none of Hamburg's chokepoints, so they stay green here and the board reads
2 reroute · 1 hold · 4 on plan:

| id | cargo | route | slack | expected decision |
|---|---|---|---|---|
| SHP-001 | Automotive parts, Shanghai → Munich | R-HAM-STD → R-RTM-ALT | 4d | **REROUTE** — strike blocks HAM ~3–5d; alt adds 2d; slack absorbs it |
| SHP-002 | Reefer pharma, Ningbo → Hamburg | R-HAM-STD (no good alt) | 1d | **HOLD + NOTIFY** — customer *is* in Hamburg; rerouting adds road transit + a cold-chain transfer |
| SHP-003 | Furniture, Shanghai → Rotterdam | R-RTM-STD | 3d | **NO ACTION** — doesn't touch Hamburg |
| SHP-004 | Electronics, Shenzhen → Antwerp | R-ANR-STD | 2d | **NO ACTION** — unaffected |
| SHP-005 | Machinery, Busan → Hamburg | R-HAM-STD → R-RTM-ALT | 3d | **REROUTE** — same logic; 3d slack ≥ 2d penalty |

> **SHP-002 is the centrepiece.** The "no good option, here's the least-bad one" call is what shows
> judgment. Make its reasoning explicit.

**The injected event** (`EVT-HAM-STRIKE`): chokepoint HAM, type `strike`, severity `high`,
48–72h expected duration, `source_language: de`, first detected from German-language RSS,
English-wire lag ~1 day. DE title: *"Warnstreik im Hamburger Hafen — ver.di ruft zu ganztägigem
Ausstand auf"*. The demo points at the **source language** — that *is* the differentiation, made visible.

---

## Data sources — wide, keyless, and none of them load-bearing

Full rationale, and which `public-apis` catalogue entry each one is, in `DATA-SOURCES.md`.
**42 sources in six families, every one free and keyless.** The old rule was "wire CORE only";
breadth is now the point, so what holds instead is the reason behind it — **no source may be
load-bearing**. Each is its own small function inside a shared budget, families are read
concurrently, and a source that is down, slow or reshaped is reported failed and skipped.

| Family | Sources | Count | Classified by |
|---|---|---|---|
| **News** | GDELT DOC 2.0 (one query per corridor, plus customs/tariffs/sanctions) and RSS via `feedparser` — regional broadcasters and papers on the corridors' doorsteps (NDR, tagesschau, DW, NOS, VRT, RTVE, El País, France Info, Le Monde, ANSA, NHK, Al Jazeera, France 24, Straits Times, Times of India) plus the narrow trade press (gCaptain, Splash 247, The Maritime Executive). The international feeds stay so the lead *against* them is measurable | 31 | the model |
| **River gauges** | PEGELONLINE — Kaub, Duisburg-Ruhrort, Emmerich → RHINE | 3 | threshold |
| **Weather & sea state** | Open-Meteo (gusts over HAM/RTM/ANR/FOS), Open-Meteo Marine (wave height at SUEZ/REDSEA/COGH), Hong Kong Observatory (warnings in force — *context*) | 3 | threshold |
| **Natural hazards** | USGS Earthquake Hazards Program, NASA EONET — each reading mapped to the nearest chokepoint, **dropped if none is within reach** | 2 | threshold + proximity |
| **Government & regulatory** | Federal Register (tariff / sanctions / customs / port-security filings — prose, so it goes to the model), US National Weather Service (*context*) | 2 | model / threshold |
| **Markets** | Frankfurter — the ECB's own reference rates (*context*) | 1 | not classified |

`data/geo.json` is the single source of truth for where a source looks: it already carries a
real lat/lon for every chokepoint, so the watch lists in `config.py` are chokepoint ids. Never
keep a second coordinate table.

**Runtime LLM (pick one, key in `.env`):** Groq (recommended default) / Google Gemini / Ollama local.
Note: Claude Code Max pays for *building*, not for the agents' *runtime* calls.

**Never hard-code a Groq model name.** Groq retires and renames models, and a retired
name fails with a 404 that looks exactly like a broken key — the whole demo drops
silently to the deterministic fallback. `llm.py` resolves the model at runtime against
`/openai/v1/models`: it asks the key what it can run and picks the best available,
preferring `GROQ_MODEL_PREFERENCES` in `config.py` but falling back to a sensible choice
from a lineup it has never seen. A model that 404s mid-run triggers one re-resolve and
retry. `python -m src.llm --models` shows what a key offers; `/api/health` names the
model actually in use.

**Skip:** everything marked OPTIONAL (Open-Meteo, NewsAPI, World News API, AISstream, Nominatim)
until the core demo works end to end. **Never** wire MarineTraffic / VesselFinder / Datalastic /
Kpler — all paid.

Keep **each source in its own small function** so one can be added or removed without touching the others.

---

## Build phases

Each phase is independently demoable. Do one, hit its checkpoint, commit, then move on — don't batch.
Full copy-paste prompts live in `BUILD-GUIDE.md`.

| Phase | What | Checkpoint | Status |
|---|---|---|---|
| **0** | Orient: read the docs, confirm understanding, write no code | Summary matches the narrative + the components | ✅ (this file) |
| **1** | `data/` JSON + `llm.py`, `config.py`, `risk_monitor.py`, `signals.py`, `httpget.py` | Run the Risk Monitor alone from the terminal; see real current news classified; confirm ≥1 non-English source is actually read and that all six families report; injected event loadable | ✅ (live pull unverified — see below) |
| **2** | `route_advisor.py` | Run against the board with the strike active; the three expected outcomes appear with reasoning that reads *well* | ✅ (LLM wording unverified — see below) |
| **3** | `comms_agent.py` | Drafts for SHP-001 (reroute) and SHP-002 (hold) read like something a person would actually send | ✅ (LLM wording unverified — see below) |
| **4** | `orchestrator.py`, `app.py`, `static/index.html` | Open the URL, click the button, the whole narrative plays on screen. **This is the demo.** | ✅ (driven in a real browser) |
| **5** | Polish: AI-Worker framing · graceful degradation if a source is down · live-vs-synthetic legend · README | Runs cold, survives flaky wifi, the honest framing is visible | ✅ |

**No scheduler, nothing always-running.** For a demo, a button beats a background job — the magic
has to happen on screen, on command.

**After every phase:** commit with a clear message describing what was built, and push.

### The detection trail

The earliness claim is only worth making if it is **checkable**, so every event carries a
`language_trail` — the ordered list of which source carried the story and how many minutes
apart. The dashboard renders it **by outlet**, marks which entry was first and which was the
international wire, and shows the original headline in its own script (Arabic renders
`dir="rtl"`, or the headline is mangled — a rendering fact, not a claim).

The headline number — "seen 23h before the international wires" — is **derived from that
trail** by `wire_lag_hours()`, never stored beside it, so the claim and the timeline it rests
on cannot drift apart.

> **Naming note.** The data keys still say `language_trail` / `english_wire` because that is
> factually what they mark — the benchmark really is the English-language wires. The UI never
> uses those words. If you touch either side, keep them in step: the code may name the
> mechanism, the screen may not. It returns `None` when the English wires actually led, which is the
case for the Suez knock-on: no lead is claimed where none exists. **A claimed lead that is not
real is the one thing this demo cannot afford** — it would turn the honest differentiator into
the invented metric the whole project refuses to produce.

Each scenario deliberately leads in a different language, so the edge reads as general rather
than as one rehearsed German trick:

| Scenario | Trail | Lead over the international wires |
|---|---|---|
| `hamburg` | DE\* → DE → NL → EN | 23h |
| `redsea` | AR\* → AR → EN → FR | 11h |
| `redsea` (Suez knock-on) | EN\* → AR | none — English led, and it says so |
| `rhine` | DE\* → DE → NL → EN | 36h |
| `france` | FR\* → FR → ES → EN | 18h |

Live events carry the same two fields with a single-entry trail, so live and scripted events
stay the same shape.

The dashboard's source line — "N of 42 sources read", with the family strip under it —
**excludes the scripted scenario**, which reports itself as a source so the CLI can show where
each event came from. Counting it would inflate both halves of the exact number an audience
uses to check the live claim. `risk_monitor.expected_sources()` is the one authority on that
denominator: it lists every source *before* anything is read, so the count is of what was
attempted, and three screens quoting it cannot disagree. **Schema parity between live and injected events has broken three times**
— each time by adding a field to injected events only. Add it to both.

**"Live" is earned per run, and the risk feed used not to check.** Its card header
hard-coded a green `live` chip and its source line printed `✓ ${ok} of ${total}` — so a
run that reached nothing rendered a green **live** and a **tick against a zero**. The stat
card had always got this right (`read ? "live" : "no live source"`); the feed contradicted
it two panels away. That is not cosmetic: on any network that blocks the sources — every
build sandbox so far, and a conference wifi — the board asserted the live read it had just
failed to make, which is precisely the invented metric this project refuses to produce.
Both claims are now computed from the run: the chip falls to an amber `no live source` and
the tick becomes `!`. `tests/test_the_pages_keep_their_promises.py` holds both, and the
guards were confirmed by reverting the fix and watching them fail. `instrumentCard` and
`contextCard` were already honest — they return `""` when they have no readings, so their
chips cannot outlive their data. **Any new panel wearing a `live` chip owes the same
check.**

### Surviving a live audience

The failure mode that actually threatens a demo is not a *dead* source — that fails fast —
but a *slow* one. The whole live pull has a hard **25-second budget**
(`LIVE_PULL_BUDGET_SECONDS`) and each request an 8-second timeout. Whatever is not read by
then is marked `skipped` and the cycle moves on.

**The families are read concurrently, and that is what makes 42 sources fit.** Read in turn,
the first family would spend the whole budget and the rest would be skipped — which is how a
board that claims to watch the world quietly ends up watching one feed. `pull_everything()`
runs RSS, GDELT, the gauges and the structured sources at once, each filling its own report,
and merges them in a fixed order so the output is stable run to run even though the reads are
not. Every source appears in that merged report whatever happened to it; a straggler is
reported `skipped` against its own name, never silently dropped.

There are **two** ways a source can be slow, and only the first is obvious:

1. **It hangs** — accepts the connection and never replies. The per-request timeout catches
   this. Tested against such a server: the run ends at 25s with the scenario intact; without
   the budget the same test took over four minutes.
2. **It trickles** — replies forever, one byte at a time. This one is nastier, because
   `requests`' timeout is measured *between bytes*, not in total: a source sending one byte a
   second never trips an eight-second timeout, so the call never returns and the thread
   running it never ends. A single such feed hung the whole run indefinitely.

So every fetch — news and instrument alike — goes through `get_capped()` in `httpget.py`,
which adds a total deadline and a size cap (`HTTP_MAX_BYTES`) on top of the timeout. It lives
in its own file because both halves need it and neither should import the other;
`risk_monitor._get_capped` is kept as an alias so the name still reads the same. Two details
are load-bearing and easy to undo by accident:

- Checking a deadline *between chunks* does not work — the read blocks until its chunk is
  full, so a trickle never reaches the check. A watchdog has to **shut the socket down** from
  outside, which is what makes the blocked read raise.
- `response.close()` alone does not unblock a read already in flight;
  `raw._connection.sock.shutdown()` does.

Both cases are held by `tests/test_a_slow_source_cannot_stall_the_demo.py`, against real
sockets on localhost: a trickling source is cut off by the watchdog rather than the
between-bytes timeout, a hanging one by the timeout, and a whole run whose every source
trickles still ends inside its budget with the scenario intact. It runs with the budget
patched down so the suite stays fast, and asserts the documented 25s / 8s separately —
the mechanism working and the numbers being what the pages quote are two claims.

RSS feeds are read **concurrently** (`RSS_CONCURRENCY`). Sequentially, twenty feeds at the
per-source timeout cannot fit a serverless budget — only the first would be read and the
language count the whole differentiation rests on would collapse to one. The pool is
deliberately not a `with` block: its exit joins every worker, so one wedged feed would simply
block there instead.

Alongside that: a failed run returns a readable sentence rather than a stack trace; a
missing provider falls back to deterministic logic and every affected card is badged
`rule`; and the page loads no external asset, so flaky wifi cannot blank it.

### What still needs a human

Everything was built in a sandbox with no outbound network and no AI key, so several
claims were written and tested but unwitnessed. Most are now confirmed.

**Confirmed in production** (Vercel, live Groq key, observed on screen):

- **The model really is deciding.** A run produced no `rule` badges on any card, which
  means all three actioned shipments went through `decide_with_llm` and the provider
  answered. The deterministic fallback was not used.
- **The pipeline fits the function timeout.** A full cycle makes about fourteen
  sequential model calls — roughly five to screen headlines, three decisions and
  six drafts — and a cold serverless function is capped at 60s. It completed.
  This was a real risk, not a theoretical one.
- **Runtime model discovery works against the real Groq API.** The hard-coded
  `llama-3.3-70b-versatile` 404'd on the live key and silently sent every decision
  to the rule fallback — a retired model's 404 is indistinguishable from a broken
  key's. `llm.py` now asks the key what it can run and picks from that. Confirmed
  in production: a run produced no `rule` badges, so discovery resolved a real
  model and the provider answered. This was previously stub-tested only.

  The lesson is worth keeping: **any hard-coded model name is a scheduled outage.**
  Don't reintroduce one.
- **PEGELONLINE is real, and it has now been witnessed.** The landing page's gauge
  panel reads the three Rhine gauges on load. Confirmed against the live host from
  the deployed instance: Kaub 73 cm, Duisburg-Ruhrort 167 cm, Emmerich 14 cm — two
  `restricted`, one `critical`, every one banded by the same `GAUGE_BANDS` table the
  risk monitor uses. A real third-party source was fetched, parsed and classified in
  production. It had only ever been tested against a local stand-in, because the
  build sandbox's egress policy blocks `pegelonline.wsv.de` with a 403 at the proxy.

  Worth knowing before a demo: **the Rhine really was low that day.** The authored
  `rhine` scenario puts Kaub at 44 cm; the live panel above the write-up was reading
  73, with Emmerich past its critical threshold. A scenario and the world can land in
  the same regime, and the page then reads as uncannily well-timed — which is exactly
  the situation the `Synthetic scenario` label exists for. Never quietly let a live
  reading stand in for the authored one, and never move that label.

**Still open — and it needs judgement, not a test:**

- **How the prose actually reads.** Routing, fallbacks and guard rails are verified
  against stubs; the model is demonstrably being called. But whether SHP-002's
  reasoning and its two drafted emails sound like a person wrote them is the demo's
  centrepiece and cannot be asserted in a test. Read them aloud. If they sound
  robotic, tune `ADVISOR_SYSTEM` in `route_advisor.py` and `CARRIER_SYSTEM` /
  `CUSTOMER_SYSTEM` in `comms_agent.py` — the prompts, not the plumbing.
- **Whether the live *news* sources return anything useful.** PEGELONLINE is
  confirmed (above), which settles the gauges. The other thirty-nine
  sources are not: nobody has confirmed a real GDELT or RSS item was fetched,
  prefiltered and classified. That is the credibility anchor — "the risk detection is
  real" is the demo's central honest claim, and the `LIVE` chip on the risk feed
  asserts it. The dashboard's source line ("N of 42 sources read") and the family
  strip under it settle it at a glance; `python -m src.risk_monitor` on a real
  connection answers it in detail, family by family, and `python -m src.signals`
  does the structured half on its own. **If the news family reads 0, the news half
  of the live claim is still decoration.**

  The eight structured sources added on top — Open-Meteo, Open-Meteo Marine, USGS,
  NASA EONET, the Federal Register, Frankfurter, the US NWS and the Hong Kong
  Observatory — are in exactly the position PEGELONLINE was in before it was
  confirmed in production: built to their published shapes, covered by stub tests,
  and never once witnessed answering, because this sandbox's egress policy blocks
  every third-party host with a 403 at the proxy. **Run `python -m src.signals` on a
  real connection before presenting.** A source whose response shape has moved shows
  as `failed` with a readable reason, which is the designed behaviour and not a
  reason to panic mid-demo — but it is worth knowing which ones answer.
- **The two reroute cards have never been read.** Every review so far has been
  SHP-002, the hold. SHP-001 and SHP-005 take the other branch in both the advisor
  and the comms prompts, so the reroute emails have never been seen by anyone.

### Free-tier rate limits are the binding constraint

A cycle makes **nine sequential model calls** — three decisions plus two drafts for
each of three actioned shipments — and the customer email is the last of them. On
Groq's free tier that one reliably hit a 429 and fell back to a template. The retry
loop now honours `retry-after` within a bounded wait budget, but the ceiling is
real. If drafts keep falling back, the options are a paid tier or collapsing the two
drafts into one call per shipment (9 → 6) — which would cost the separate carrier
and customer voices, so prefer the former.

Diagnose it from the card: a `template` badge now prints the reason underneath.
That instrumentation is what found this after three rounds of wrong guesses; a
fallback that does not say why is a dead end.

### The dataset ages itself

Shipments are authored to sit mid-voyage on `_authored_on` in `shipments.json`.
`load_shipments()` rolls every date forward by whole weeks so the board still reads
as in-transit whenever it runs — ETAs in the past are the first thing an audience
notices. Whole weeks keep the weekday; a single uniform shift keeps slack, transit
days and ordering exactly as the screenplay authored them.

### Running the demo

```bash
uvicorn src.app:app --reload      # then open http://127.0.0.1:8000
```

`/` is the landing page, `/whitepaper` is the technical whitepaper, `/app` is the
dashboard, `/deck` is the pitch deck, `/what` is the What section on its own and
`/pitch` is the deck being rebuilt from scratch; all six are single self-contained
files. `GET /api/initial` renders the calm five-green-cards board instantly; `POST /run`
is the button. `GET /api/gauges` reads the three Rhine gauges live from PEGELONLINE for
the landing page's gauge panel — cached for `GAUGE_CACHE_SECONDS` because the page is
public and the source refreshes about every fifteen minutes, and it answers 200 with
`ok: false` rather than failing, so a gauge being down can never blank the page. `GET /api/health` reports what a running instance can actually see — the
path it received, whether the dashboard and data files shipped, and whether a provider
is configured. It is the first thing to check when a deploy misbehaves. The page is a single self-contained file — no CDN, no external font, no
network call beyond its own API — so flaky wifi cannot blank it.

Each component still runs alone, which is how you debug one without the others:

```bash
python -m src.signals                     # the instruments alone: what answered, and what it said
python -m src.risk_monitor --list-scenarios
python -m src.risk_monitor --scenario redsea
python -m src.route_advisor --inject --shipment SHP-002
python -m src.comms_agent  --inject
python -m src.orchestrator --no-live      # the whole loop, no network
```

### The pitch deck

`/deck` is the investor deck, served from `static/deck.html` and **deliberately not linked
from the landing nav** - it is the thing you hand to a room, not a page for whoever wanders
onto the site. Four sections: what the problem is, why it is worth solving, how the loop
works, and who is building it.

Three rules it holds, all of them the project's own:

- **Every third-party figure carries its source on the slide,** and every one of them comes
  from `docs/problem-brief.md` rather than from a search: Maersk's 2014 shipment trace,
  CLECAT's membership scope, Asana's Anatomy of Work Index, Magaya's 2024 survey of 71
  forwarders, Viterra via Sedna, and Transport Intelligence's market sizing. No figure appears without
  one - and where a figure has not been confirmed against its publication it stays a
  visible slot rather than a plausible guess. **No figure about SQRlane appears at all** - there is no traction, accuracy or
  performance claim in it, because none has been measured.
- **Every placeholder looks like one.** Founder names, bios, the ACV and the ask are dashed
  grey monospace slots (`.slot`), never plausible filler. A placeholder that reads like real
  copy is how an invented founder ends up on screen.
- **It is inside the off-origin rule.** The deck is the one page guaranteed to be opened on
  somebody else's wifi, so it is in `ALL_PAGES` in
  `tests/test_the_pages_keep_their_promises.py`. It stays outside the language and
  named-systems rules: it cites research by name and names the incumbents it is positioned
  against, neither of which the product pages do.

**Spacing is sized against viewport height as well as width, and that is not cosmetic.**
Sized against width alone, three slides overran a 1280x720 projector - the standard
presenting resolution - while a 1920x1080 monitor had room to spare. Under
`scroll-snap-type: y mandatory` an overrunning slide is not merely tall, it is *unreachable*:
the snap pulls you off it before you reach the bottom. Every vertical measure now takes the
smaller of a width- and a height-derived size (`clamp(24px, min(3.6vw, 5.2vh), 46px)`), and
below 620px tall the deck stops snapping and becomes an ordinary document. Measure all three
resolutions in a browser after touching the deck's CSS; no unit test sees this.

Print gives exactly one page per slide (`@page { size: A4 landscape }`), so the deck exports
to a 14-page PDF from the browser with nothing else installed. `docs/replit-deck-prompt.md`
is the same deck written as a single prompt, for rebuilding it outside this repo.

**`/what` is the What section on its own**, six slides, built from
`docs/problem-brief.md` so every third-party figure on it is one that survived being
checked. It exists separately because the problem is the half that gets rebuilt most
often and the half that goes into Figma on its own, and it ends on the loop diagram as
the handover into the How. Its CSS, its keyboard navigation and its loop SVG are lifted
verbatim from `deck.html` rather than rewritten, so the two cannot drift apart on layout
or on the diagram. **Change one, change both** - the deck's own What slides are the same
five, transplanted.

**The What section was rebuilt once, and the reason is worth keeping.** It used to argue
from BASF's EUR 250m and McKinsey's "45% of a year's profit". Both are the *cargo owner's*
loss, and using a shipper's pain to argue a forwarder's pain is a joint that breaks under
one good question. The section now argues only from costs that land on the forwarder's own
accounts. Those four sources are gone from the deck entirely, including from its footer -
a sources line that credits research the deck no longer shows is its own kind of untruth.

### The deck's slides, as editable SVGs

`tools/build_slides.py` writes `static/assets/slide-problem.svg` (01, the problem) and
`static/assets/slide-fix.svg` (02, the loop) as 1920x1080 vectors, built to be opened in
Figma and edited by hand rather than regenerated. Every line is its own named text layer,
every rule and panel a named rectangle, and there is **no `<style>` block** - Figma's
importer is reliable with inline presentation attributes and is not with CSS classes.

Slide 01 argues from two columns, and the pairing is the argument: **what the work
actually is** (quoting, track and trace, documents) against **what keeps moving the lane**
(fuel and cost, tariffs and trade policy, geopolitics and labour, climate and weather).
Manual work is only expensive because the world keeps re-triggering it. The right-hand
column carries no numbers, because none of those four has a figure that survived
`docs/problem-brief.md`'s grading - the mechanism is the claim.

Four things about the pair are load-bearing:

- **The font is named `Geist` alone, with no fallback stack.** Figma reads a
  comma-separated `font-family` as one literal font name and then reports it missing on
  every layer; a bare name resolves, and Geist is in Figma's Google Fonts library. This is
  the opposite of the rule for the web pages, where the stack is the safety net.
- **The build measures every string and fails if one overruns its box.** SVG text does
  not wrap - a line that outgrows its column does not reflow, it runs silently into the
  next column, and nobody sees it until the file is open in Figma. So each string is
  measured against the real Geist metrics in `static/fonts/` and the build stops, naming
  the line and the overrun in pixels. Same discipline as `build_pitch_pptx.js`, for the
  same reason: a layout fault no validator catches. Confirmed by lengthening a line and
  watching it fail - it caught a 6.8px overrun.
- **The loop is read from `static/assets/sqrlane-loop.svg`, never copied into the
  builder.** One source of truth: edit the asset and slide 02 moves with it. Only the
  font is rewritten on the way in - the standalone asset stays Inter because it travels
  on its own and Figma ships Inter, but a slide carrying two typefaces reads as a mistake.
  It is placed on its **measured ink box, not its viewBox**: the diagram sits inside a
  1200x360 frame with slack on every side, so centring on the frame leaves it visibly
  off-centre. The ink box is computed from the asset's rects, paths and text so it
  re-centres itself if the diagram is redrawn.
- **The headline figure carries whose number it is.** The reference slide labels EUR 3.4bn
  only `PER YEAR`. Ours adds `SQRLANE ANALYSIS` under it, because that figure is our own
  estimate and not a third party's - the deck's rule is that every figure names its source,
  and an unattributed number in a sourced deck reads as though someone else produced it.

**The same slides are also a page.** `static/pitch.html`, served at `/pitch`, inlines
those SVGs verbatim into a snapping one-slide-per-screen deck with keyboard navigation
and one-slide-per-page print. It is **generated by the same builder** rather than
re-implemented in HTML, which is the whole point: there is one description of each slide,
and the page a room sees cannot drift from the file that goes into Figma. Three
consequences worth knowing:

- **Ids are namespaced on the way into the page, and only there.** Two slides in one
  document would otherwise collide on `background`, `title` and the rest, and the loop
  asset carries ids with spaces in them, which an SVG file tolerates and HTML does not.
  The standalone SVGs keep the short ids, because those become the Figma layer names.
  `_scope_ids` refuses to run if the markup ever references an id (`url(#…)`, `href="#…"`),
  because rewriting one half of such a pair renders the page blank.
- **The page number is derived from the deck, never typed.** A hard-coded `01 / 08` on a
  two-slide deck is wrong the moment a slide is added, and it is the kind of wrong nobody
  notices until it is on a projector.
- **There is no fixed counter or brand chrome.** Each artboard already carries the mark
  and its own page number, and at 16:9 the stage fills enough of the viewport that fixed
  corners land on top of them. Driven in a browser at 1280x720 and 1920x1080: both slides
  sit fully inside the viewport, so neither is unreachable under mandatory snapping.

**Why the loop is not on the problem slide.** It was asked for there, and it does not fit:
the diagram is 3.3:1, so in that slide's free band it can only be ~230px tall, which
scales its sub-labels ("42 sources, six families", "reroute · hold · on plan") to about
10px - under the slide's own 12.4px floor and unreadable projected. On its own slide it
runs the full 1824px measure and those labels land near 21px. **If a later slide tries to
inline the loop again, check the resulting label size before anything else.**

The geometry - 48px margins, two 884px columns, the baseline grid - is lifted from the
reference deck the slides were modelled on. A short title pulls everything under it up by
whole title lines, which is what the reference does (its two-line slides sit exactly 63.4px
higher), so `masthead()` returns the divider's y rather than fixing it.
`docs/slide-problem.png` and `docs/slide-fix.png` are what they render to.

**`tools/build_pitch_pptx.js` builds the same deck as a PowerPoint file** - 18 slides, four
dark section dividers between the light content, Arial and Courier New because the reader's
PowerPoint renders the fonts and those two ship everywhere. It carries its own layout
checks, and they are the point: it estimates every text box's wrapped height and fails the
build if the text cannot fit its shape, or if content is placed above a wrapped title's
bottom. **Both faults shipped in the first render and neither is visible to the OOXML
validator** - `validate.py` passed a deck whose title ran underneath the cards and whose
card bodies spilled past their borders. The estimator is deliberately conservative: it
over-counts a line rather than under-counts, so its errors cost a little white space
instead of clipping a sentence.

### The whitepaper page

`/whitepaper` is the technical paper, served from `static/whitepaper.html` and linked
from the landing nav. It carries the same tokens, the same self-hosted Geist and the
same nav as the other two pages — no CDN, no Google Fonts, nothing external, which
`tests/test_the_pages_keep_their_promises.py` asserts by failing on any off-origin
asset or fetch, on all three pages.

It is the one document that states the project's assumptions and failures in public, so
four claims in it are load-bearing and tested for by string:

- the prototype **calls a US inference provider** today, so "built in Europe" describes
  an architecture and not the current deployment;
- the per-cycle cost figure **is an assumption, not a measurement**;
- **any hard-coded model name is a scheduled outage**;
- there are **no accuracy figures** anywhere, because none have been measured.

Model guidance names **specific models from Lyceum's own catalogue with their per-token
prices**, taken from their inference deck rather than from secondary sources, and dated
July–August 2026 with their own subject-to-change caveat.

Two things the deck settled that the earlier draft had wrong:

- **It is per-token serverless, not GPU rental.** That fits this workload far better —
  the system is idle until a disruption lands, then makes about fourteen calls. Costing
  it needed no assumption about GPU seconds: the per-cycle token volume is measured from
  the real prompts (~12.8k in, ~3.7k out) and priced against the catalogue. The
  recommended per-task mix is **about ten times cheaper** than a frontier model
  everywhere, which is the number worth quoting.
- **EU residency is not the same as European model provenance.** The catalogue's strong
  models are Chinese and American in origin, openly licensed and hosted in `eu-north1`
  with zero retention. Teuken-7B, EuroLLM and Mistral are the answer if provenance must
  be European too, at a cost in capability. The page keeps those two axes apart in a
  table rather than blurring them.

### Deployed on Vercel

`api/index.py` re-exports the same FastAPI app; `vercel.json` rewrites every path to it
and lists `includeFiles` so `data/` and `static/` are bundled (the Python builder traces
imports, not data files). Two serverless facts are handled in `config.py`: the app
directory is read-only, so `risk_state.json` goes to the temp directory; and functions
have a hard timeout, so the live pull drops to 10s and the classifier cap to 16 items.

`GROQ_API_KEY` lives in Vercel's environment variables. **Adding it requires a redeploy** —
Vercel bakes env vars in at deploy time, so an existing deployment will not pick it up.

**The deployment moved with the rename.** The old instance lived on the previous
account at `logistics-freight-forwarding.vercel.app` and is not the product's home any
more — do not quote that URL. The new one is being set up under the SQRlane account
against the `sqrlane` repo; once it is git-linked, every push to `main` deploys itself.

Two things a fresh project needs, and both have caused a 404 already:

- **Vercel must be able to see the repo.** A fork of a private repo is itself private,
  and Vercel's GitHub App has to be granted access to it explicitly. Without that there
  is no git link, nothing builds, and every path 404s.
- **`GROQ_API_KEY` must be set, then redeployed.** Vercel bakes env vars in at deploy
  time, so an existing deployment will not pick one up.

Check `Root Directory` is empty and the framework preset is `Other`; either one pointed
elsewhere 404s every path. `/api/health` is the first thing to open once it answers.

Deploy for sharing a link; run `uvicorn` locally for a demo you are presenting.

### How the decision layer splits the work

Code computes the **facts** (which chokepoints a route touches, active risk on them,
added transit days, whether it fits the slack, the revised ETA). The LLM makes the
**call** and explains it. Arithmetic and date maths never go to the model.

Guard rails already in place: a model that names a route it wasn't offered has the
reroute refused and downgraded to hold; an invalid decision value falls back to
`no-action`; a provider failure falls back to transparent rules. Every one of those
is recorded in the shipment's `reasoning_trail`.

Shipments whose route carries **no active risk short-circuit without an LLM call** —
that is a real answer, not a shortcut, and it keeps 2 of the 5 outcomes deterministic.

### The Comms Agent sends nothing, structurally

No SMTP, no email library, no transport of any kind is imported anywhere in `src/`,
and `tests/test_comms_agent_sends_nothing.py` asserts it stays that way — it parses every
file in `src/` and fails naming the file and line if a transport library ever appears
(including via `__import__` or `importlib`). It also runs a full offline cycle and checks
every draft it produces. Run the whole suite with
`python -m unittest discover -s tests` — standard library, nothing to install, and it
covers the other seven claim-guards too: the TMS being the only door to the book; the
pages naming no language, loading nothing external, carrying one product name and
disclaiming the systems they name; the simulated week never sending a booking back to a
route it left; a trickling source being cut off rather than hanging the run; the
structured sources keeping schema parity with the scripted ones and failing alone; a
reroute having to be worth what it costs, including the board outcomes that pricing must
not quietly move; and the landing page's live gauges being banded exactly as the risk
monitor bands them, so the two cannot disagree about the same number. Note it is deliberately *not* a "no networking" rule: the
live news pull and the LLM calls are real HTTP and must stay that way. Every draft carries `status: "DRAFT - not sent"`
in the data, not just in the UI. Say this out loud in the demo — it is the responsible
design, not a missing feature.

Carrier and customer get **different voices and separate calls**: a carrier email is a
transaction between operators, a customer email is a relationship. Internal vocabulary
(route codes like `R-RTM-ALT`, chokepoint ids like `HAM`) is fine in a carrier email and
is flagged as a warning if it ever appears in a customer one.

---

## Non-goals — protect the scope

Scope creep is the failure mode here. None of these are in this build:

- **No real route optimisation.** Routes are pre-authored candidates; the agent *chooses among them
  and justifies the choice*. It does not compute routes.
- **No sending of anything.** Emails are drafted and displayed only.
- **No *live* TMS connection.** Working through the TMS is the design, not a non-goal —
  what is out of scope is the far end of it. The TMS Link is a *demo connector*: it models
  both directions, owns the only read path, and describes the write-back each decision
  implies, but there is no vendor, no credential and no endpoint, and nothing is ever
  written. The bookings behind it are synthetic. Wiring a real TMS is on the far side of
  the integration/trust wall, not in this build — and it is the single highest-value thing
  on the other side of it.
- **No scheduler / always-on.** Button-triggered.
- **No database.** In-memory + JSON files.
- **No paid data.** Free sources only.
- **No accounts, billing, multi-tenant, or the real 5U AI product.** The AI-Worker layer is cosmetic.

---

## Design principles

- **One file per job, one job per file.** If a file does two things, split it.
- **`llm.py` is the only door to the AI provider.** Everything else calls `llm.py`.
- **`httpget.py` is the only door to a third-party host.** Every source fetch goes through
  `get_capped()`, so nothing we do not control can hold the run open.
- **A new source is a function in `signals.py`, or a feed in `config.py`. Never more than
  that.** Register it with a family and a tier, put its endpoint and thresholds in `config.py`,
  and make sure it fails alone. If it is a `context` source it must never emit an event.
- **Numbers do not go to the model.** A gust, a wave height, a magnitude, a water level and a
  distance are classified by threshold. It is cheaper, it is repeatable, and it cannot
  hallucinate a severity.
- **`tms.py` is the only door to the book.** Every component that needs shipments calls
  `tms.read_bookings()` — never `shipments.json` directly. One door means the day the
  connector points at a real TMS, the whole board follows it; a second door is how that
  quietly stops being true, and a test fails the build if one appears.
- **An agent's output is a change to a record, not a message on a screen.** Anything a
  Worker decides should be expressible as a write-back to the booking it came from. If it
  cannot be, ask whether the desk would actually act on it.
- **Each component runnable alone.** The Risk Monitor must produce visible output before the Route
  Advisor exists.
- **Human-in-the-loop is a feature, not a limitation.** The Comms Agent drafts; it never sends. Say
  this in the demo — it's the responsible design.
- **No agent framework.** The orchestrator is plain functions calling functions plus shared JSON
  state. Reach for CrewAI/LangGraph only if that genuinely becomes painful — they hide the exact
  thing being learned here.
- **Fail soft in front of an audience.** If a live source is slow or down, run the injected scenario
  anyway and show a small note. Never crash the demo.
- **Never commit `.env`.** If it's about to be staged, stop.
- **Both pages are set in Geist**, served from `static/fonts/` — the same typographic
  scale the dashboard's colour tokens came from, so the two pages read as one product.
  Self-hosted, never a CDN: an external font request is one more thing that can fail in
  front of an audience, and a page that loses its type looks broken.

---

## Definition of done

Six criteria — five from `PRD.md`, plus the one the product rests on. If these hold, the
prototype is finished and nothing else is in scope:

1. The demo narrative runs start to finish in under ~2 minutes, on command, without breaking.
2. The Risk Monitor genuinely pulls live sources across all six families — the credibility
   anchor. News is the half an audience checks; the instruments are the half that makes it a
   terminal rather than a news reader.
3. The injected strike produces three distinct, defensible decisions across the board, each
   with plain-English reasoning.
4. Drafted emails read like something a human would actually send.
5. It looks good enough to present — cards, states, and drafts legible on a screen in a room.
6. Every decision lands on the booking it came from. The board is read out of the TMS
   through one door, each Worker's action is queued back against the record, and all of it
   waits for a person — visible on screen, not just true in the payload.

---

## Document map

| File | What it's for |
|---|---|
| `START-HERE.md` | Orientation, the pitch, the demo narrative, build order. Build-time; `CLAUDE.md` is current |
| `SETUP.md` | One-time human setup: Node/Claude Code/Python, GitHub CLI, free AI key, `.env` |
| `PRD.md` | *What* and *why* — problem, success criteria, non-goals, differentiation |
| `DESIGN.md` | *How* — architecture, stack, file structure, design principles |
| `DATASET.md` | The screenplay — chokepoints, routes, the five shipments it was first authored around, the injected strike. Build-time; the pool is seven now |
| `DATA-SOURCES.md` | Every source the desk reads: the six families, which `public-apis` entry each one is, and what was deliberately skipped |
| `BUILD-GUIDE.md` | The copy-paste phase prompts — the spine of the build |
| `README.md` | The front door — what it is, how to run it, the honest framing |
| `docs/problem-brief.md` | The problem the deck argues, with every figure graded A/B/C by how well it is sourced — and the rejected ones named so they do not creep back |
| `trade-risk-agent-docs.zip` | Duplicate archive of the seven docs above; not a source of truth |

---

## Honest framing (carry it, don't bury it)

This is scripted where it needs to be (the injected disruption), modelled where it must be
(the TMS connector - the read is the only door and the write-backs are derived from real
decisions, but no TMS is contacted), and real where it earns credibility (the news pull). It's a strong learning artifact and a compelling demo — **not a live product**. The
gap between this and a business is the integration/trust/liability wall, which is real work for
later. Build this first; it teaches every piece of how an agent actually works.
