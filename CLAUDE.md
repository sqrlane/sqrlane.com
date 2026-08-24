# CLAUDE.md

Guidance for Claude Code working in this repository.

---

## What this project is

**Lanewatch** ("Trade-lane risk, decided") — a demo-grade AI-agent prototype for freight
forwarding. The product name and identity are our own: **never borrow 5U AI's name,
colours, taglines or Worker names**, and never invent a metric — no traction, accuracy or
percentage claims. Real reasoning on synthetic shipments is the honest pitch, and a
sharp audience catches invented numbers.

Small agents watch global news (in multiple languages) for events that disrupt shipping. When a
disruption hits, the system checks which shipments are affected, decides whether to **reroute** or
**hold** each one — and *explains why* — then drafts the carrier and customer emails a human would
need to send. Risk → decision → communication as one closed loop, with the reasoning recorded. A
light "5U AI-style AI Worker" wrapper sits on top purely as demo framing.

**The problem it models:** forwarders watch for disruptions *and* react to them by hand. Signals
that surface first in non-English sources (a German port strike, an Arabic-language Red Sea
incident) are seen late. Incumbent risk tools (Everstream, Interos, Resilinc) stop at the alert —
they don't decide or act, and they're priced out of the mid-market.

**Modelled end user:** Head of Operations at a mid-size DACH/Benelux forwarder.
**Actual audience:** whoever is being shown the demo — a forwarder ops lead, investor, or interviewer.

### The two differentiators (the whole story — nothing else)

1. **Earlier signal, because the sources are closer to the event.** A disruption is known
   locally long before it is news globally: the union announces it, the regional broadcaster
   carries it, and only then does an international wire pick it up. A monitor watching the
   wires is structurally late because it is reading *downstream*. Lanewatch reads ~20 sources
   across every corridor on the board, so somewhere one of them is publishing whatever the
   hour is here.

   **The website never names a language.** Multilingual reading is the *mechanism*, not the
   pitch — the edge is source proximity, and it holds wherever in the world the event
   happens. Naming a language makes a general capability look like one rehearsed trick, so
   the UI says "regional" and "international wires" throughout. Real outlet names
   (Al Jazeera Arabic, DW Deutsch) are fine: those identify a source, they do not claim an
   edge. `verify_neutral.py` holds this. See [The detection trail](#the-detection-trail).
2. **A closed risk → reroute → comms loop with recorded reasoning.** Risk incumbents stop at the
   alert; execution players don't touch risk. Welding them — and recording *why* each decision was
   made — is the whitespace.

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

One claim still needs a human to judge it — see
[What still needs a human](#what-still-needs-a-human) below. Everything else is verified.

> **Path note:** `DESIGN.md` shows the tree rooted at `trade-risk-agent/`. This repo is checked out
> as `Logistics-Freight-Forwarding`. Build at the **repo root** — `src/`, `data/`, `static/` go
> directly here. Don't create a nested `trade-risk-agent/` folder.

---

## The demo narrative — this IS the spec

Everything serves this. **If a feature doesn't help this story land, it doesn't get built.**
Target: runs start to finish in **under ~2 minutes**, on command, without breaking.

1. **"Here are 5 shipments in transit."** Dashboard shows 5 shipment cards, all green.
2. **"Watch — a strike hits the Port of Hamburg."** Click a trigger button.
3. **"The system caught it from a German-language source before the English news wires."** The risk
   feed shows the event, flagged as detected from a German source first.
4. **"It triaged all 5 shipments in seconds."** Cards change state — two reroute, one hold, two stay
   green (the system doesn't cry wolf).
5. **"Here's the reasoning for each decision."** Click a rerouted card → plain-English justification
   (slack vs. added transit vs. strike delay).
6. **"And here are the emails it drafted."** Two drafts appear — carrier and customer. *Nothing is sent.*
7. **"All of that, from one news event, on command."**

### The honest line (keep it visible in the UI)

> "The risk detection is real — it runs against live news right now. The shipments are synthetic, so
> I can show you a disruption on demand instead of waiting for one."

This is why the Risk Monitor stays **genuinely live** even though everything downstream runs on
authored data. The injected strike uses the **same event format** as live events so it flows through
the real pipeline.

---

## Architecture — four components

```
  [ Risk Monitor ] --writes--> risk_state.json
        |  (live news, multilingual, GDELT/RSS/gauges)
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
  [ Dashboard ] <-- shipment states, reasoning, drafts; has the trigger button
```

1. **Risk Monitor** (the real, live part) — pulls CORE free sources, LLM-classifies each item for
   logistics relevance → chokepoint / type / severity, writes `risk_state.json`. Also loads the
   injected Hamburg event in the same format.
2. **Route Advisor** — maps each candidate route's chokepoints against active risk; LLM weighs
   **schedule slack vs. added transit vs. expected disruption delay** → `reroute` / `hold` /
   `no-action` + plain-English reasoning + a recorded reasoning trail.
3. **Comms Agent** — LLM drafts a carrier email (booking change / hold instruction) and a customer
   email (status + revised ETA). Returns text. **Sends nothing** — no email library, no SMTP.
4. **Orchestrator + Dashboard** — on trigger: refresh risk → Route Advisor over all shipments →
   Comms Agent for actioned ones → one result object → rendered as cards, risk feed, expandable
   reasoning, drafts.

### The product layer

**Thirteen Workers, three of them real.** Risk, Routing and Comms genuinely run and are
tagged `LIVE`. Rate, Milestones, Docs, Inbox, RFQ, Booking, Invoice, Customs, TMS Link
and Assistant replay
authored data from `src/roster.py` and are tagged `SCRIPTED`. **The tag is the honesty** — never present a
scripted Worker as reasoning live. They are still *reactive*: each panel is built from
the active scenario and the selected shipment, so switching either visibly changes it.
What is authored is the content, not the shape.

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
- **Empty states** that name the next action. `verify_shell.py` asserts zero ad-hoc
  `.hint` blocks survive.
- **Skeletons** shaped like the thing that is loading, so the layout does not jump.
- **Notch gauge**, after bklit's, on the shipment drawer: **slack consumed** — the delay
  against the slack the booking had. A real proportion, and the number every decision
  turns on. SHP-002 reads `100%+` in red.

Two things worth keeping:

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
should never have been asked. `verify_simulation.py` asserts no booking ever revisits a
route.

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
  Lanewatch has no history to compare a run against, so both would be invented — and an
  invented metric is the one thing this project refuses to produce. The card keeps the
  same anatomy and puts a fact from the run in the pill instead. `verify_shell.py` fails if
  "vs. previous" ever appears on the page.
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

The Comms Agent covers *outbound*. Three scripted Workers cover the rest of the
desk a disruption actually lands on:

- **Inbox Worker** — inbound carrier and customer mail, triaged: intent classified,
  linked to the booking, and a reply drafted. Which mail arrives is derived from the
  decision the Route Advisor made, so a reroute produces an omit-notice and a status
  chase, a hold produces berth options, and an on-plan booking produces a routine
  milestone with **no reply drafted at all**. Answering everything would be showing
  volume rather than judgement.
- **RFQ Worker** — an inbound rate request read into structured fields, priced against
  the lane with the active scenario's surcharge, and answered with a drafted quote.
- **TMS Link** (`src/tms.py`) — a **demo connector**. It models the field mapping and
  turns each actioned decision into the booking change it implies (discharge port,
  routing code, ETA, or a hold status). A shipment left on plan produces no write-back,
  which is a real answer rather than an omission.

**None of it sends, and none of it writes.** A drafted reply, a drafted quote and a
queued write-back are all outbound actions, so all three sit behind the same approval
gate as an email — `DRAFT - not sent` and `QUEUED - not written`, both
`awaiting_approval`. `tests/test_comms_agent_sends_nothing.py` now checks all of them:
the original checks only ever looked at `card["drafts"]`, which none of these appear in.

`src/tms.py` imports nothing but `datetime`. There is no client, no credential and no
endpoint — a write-back is a dict describing a change, and it stays a dict. Never
present the connector as a live TMS link; it says `connected (demo)` everywhere it is
surfaced, and a test asserts that.

**The roster covers the desk, under our own names.** The function set a forwarding
desk actually runs — quoting, booking, shipment tracking, TMS data entry, invoice
reconciliation, and customs — is all present. The names are ours: **never** use the
names the reference product ships (`Rate Manager`, `DocuMind`, `Track & Trace`,
`Copilot`), and `verify_product.py` fails on any of them appearing in the dashboard,
the README, the roster source, the served Worker names, or the run payload. It caught
one of those names in a source *comment*, which is the level of paranoia this deserves.

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

**The connection point** is its own view in the sidebar under `System`, not just a Worker
chip: connector name, `connected (demo)`, bookings synced, changes queued, the field
mapping table, and every queued write-back with the change it describes. All of it from
`src/tms.py`, which still imports nothing but `datetime`.

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

### Target file structure (build at repo root)

```
├── *.md                      # the seven planning docs + this file
├── .env                      # runtime AI key — NEVER committed
├── .gitignore                # must list .env, __pycache__/, .venv/, risk_state.json
├── requirements.txt
├── data/
│   ├── shipments.json        # from DATASET.md
│   ├── routes.json           # candidate routes + chokepoints
│   ├── chokepoints.json
│   └── injected_events.json  # the scripted Hamburg strike
├── src/
│   ├── llm.py                # provider wrapper — the ONLY place AI is called
│   ├── config.py             # keys, model names, source list
│   ├── risk_monitor.py       # component 1
│   ├── route_advisor.py      # component 2
│   ├── comms_agent.py        # component 3
│   ├── roster.py             # the seven SCRIPTED Workers - authored, never live
│   ├── tms.py                # the demo TMS connector - describes changes, writes none
│   ├── orchestrator.py       # component 4 (the loop)
│   └── app.py                # FastAPI: serves the page + /run
├── static/
│   ├── landing.html          # the front page (HTML+CSS+JS in one file)
│   ├── index.html            # the dashboard (HTML+CSS+JS in one file)
│   └── fonts/                # Geist Sans + Mono, self-hosted - never a CDN
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

**The 5 shipments and their expected outcomes on the injected strike — this is the payoff:**

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

## Data sources — wire CORE only

Full rationale in `DATA-SOURCES.md`. **Every extra source is one more thing that can break live in
front of an audience.** Three keyless sources carry the whole story:

| Source | Role | Key? |
|---|---|---|
| **GDELT DOC 2.0** | Global news backbone, ~15 min refresh, filter by keyword/language/country | No |
| **RSS via `feedparser`** | Ten feeds in six languages — German (NDR / tagesschau / DW), Arabic (Al Jazeera), French (France Info / Le Monde), Dutch (NOS), Spanish (RTVE), English (gCaptain / Al Jazeera). This is where the earliness edge lives; the English feeds are kept so the lag *against* them is measurable | No |
| **PEGELONLINE** | Rhine water levels → RHINE chokepoint. DACH-specific domain-depth signal | No |

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
| **0** | Orient: read the docs, confirm understanding, write no code | Summary matches the narrative + four components | ✅ (this file) |
| **1** | `data/` JSON + `llm.py`, `config.py`, `risk_monitor.py` | Run the Risk Monitor alone from the terminal; see real current news classified; confirm ≥1 non-English source is actually read; injected event loadable | ✅ (live pull unverified — see below) |
| **2** | `route_advisor.py` | Run against the 5 shipments with the strike active; the three expected outcomes appear with reasoning that reads *well* | ✅ (LLM wording unverified — see below) |
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

The dashboard's source line — "N of 20 sources read" — **excludes the scripted scenario**,
which reports itself as a source so the CLI can show where each event came from. Counting it
would inflate both halves of the exact number an audience uses to check the live-news claim. **Schema parity between live and injected events has broken three times**
— each time by adding a field to injected events only. Add it to both.

### Surviving a live audience

The failure mode that actually threatens a demo is not a *dead* source — that fails fast —
but a *slow* one. The whole live pull has a hard **25-second budget**
(`LIVE_PULL_BUDGET_SECONDS`) and each request an 8-second timeout. Whatever is not read by
then is marked `skipped` and the cycle moves on.

There are **two** ways a source can be slow, and only the first is obvious:

1. **It hangs** — accepts the connection and never replies. The per-request timeout catches
   this. Tested against such a server: the run ends at 25s with the scenario intact; without
   the budget the same test took over four minutes.
2. **It trickles** — replies forever, one byte at a time. This one is nastier, because
   `requests`' timeout is measured *between bytes*, not in total: a source sending one byte a
   second never trips an eight-second timeout, so the call never returns and the thread
   running it never ends. A single such feed hung the whole run indefinitely.

So every news fetch goes through `_get_capped()` in `risk_monitor.py`, which adds a total
deadline and a size cap (`HTTP_MAX_BYTES`) on top of the timeout. Two details are load-bearing
and easy to undo by accident:

- Checking a deadline *between chunks* does not work — the read blocks until its chunk is
  full, so a trickle never reaches the check. A watchdog has to **shut the socket down** from
  outside, which is what makes the blocked read raise.
- `response.close()` alone does not unblock a read already in flight;
  `raw._connection.sock.shutdown()` does.

Both cases are held by `verify_slowsources.py`: the hang ends at 25s, the trickle at 8s, and
the scenario survives both.

RSS feeds are read **concurrently** (`RSS_CONCURRENCY`). Sequentially, ten feeds at the
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
- **The pipeline fits the function timeout.** A full cycle makes up to a dozen
  sequential model calls, and a cold serverless function is capped at 60s. It
  completed. This was a real risk, not a theoretical one.
- **Runtime model discovery works against the real Groq API.** The hard-coded
  `llama-3.3-70b-versatile` 404'd on the live key and silently sent every decision
  to the rule fallback — a retired model's 404 is indistinguishable from a broken
  key's. `llm.py` now asks the key what it can run and picks from that. Confirmed
  in production: a run produced no `rule` badges, so discovery resolved a real
  model and the provider answered. This was previously stub-tested only.

  The lesson is worth keeping: **any hard-coded model name is a scheduled outage.**
  Don't reintroduce one.

**Still open — and it needs judgement, not a test:**

- **How the prose actually reads.** Routing, fallbacks and guard rails are verified
  against stubs; the model is demonstrably being called. But whether SHP-002's
  reasoning and its two drafted emails sound like a person wrote them is the demo's
  centrepiece and cannot be asserted in a test. Read them aloud. If they sound
  robotic, tune `ADVISOR_SYSTEM` in `route_advisor.py` and `CARRIER_SYSTEM` /
  `CUSTOMER_SYSTEM` in `comms_agent.py` — the prompts, not the plumbing.
- **Whether live news sources return anything useful.** The fail-closed path is well
  tested and the deployed run completes, but nobody has confirmed a real
  GDELT/RSS/PEGELONLINE response was parsed. This is the credibility anchor — "the
  risk detection is real" is the demo's central honest claim, and the `LIVE` chip on
  the risk feed asserts it. The dashboard's source line ("N of 14 sources read")
  settles it at a glance; `python -m src.risk_monitor` on a real connection answers
  it in detail. **If N is 0 or 1, the live claim is currently decoration.**

  The **landing page's gauge panel is now the cheapest way to settle half of this**:
  it reads PEGELONLINE on load and prints three numbers or says why it could not.
  Open `/` on a machine with outbound access — three readings means a real
  third-party source was fetched and parsed. It was built in a sandbox whose egress
  policy blocks `pegelonline.wsv.de` (403 at the proxy), so every path is tested
  against a local stand-in and none against the real host.
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

`/` is the landing page, `/whitepaper` is the technical whitepaper and `/app` is the
dashboard; all three are single self-contained files. `GET /api/initial` renders the calm five-green-cards board instantly; `POST /run`
is the button. `GET /api/health` reports what a running instance can actually see — the
`/` is the landing page and `/app` is the dashboard; both are single self-contained
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
python -m src.risk_monitor --list-scenarios
python -m src.risk_monitor --scenario redsea
python -m src.route_advisor --inject --shipment SHP-002
python -m src.comms_agent  --inject
python -m src.orchestrator --no-live      # the whole loop, no network
```

### The whitepaper page

`/whitepaper` is the technical paper, served from `static/whitepaper.html` and linked
from the landing nav. It carries the same tokens, the same self-hosted Geist and the
same nav as the other two pages — no CDN, no Google Fonts, nothing external, which
`verify_paper.py` asserts by failing on any off-origin request.

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
  table rather than blurring them, and `verify_paper.py` asserts both are named.

### Deployed on Vercel

`api/index.py` re-exports the same FastAPI app; `vercel.json` rewrites every path to it
and lists `includeFiles` so `data/` and `static/` are bundled (the Python builder traces
imports, not data files). Two serverless facts are handled in `config.py`: the app
directory is read-only, so `risk_state.json` goes to the temp directory; and functions
have a hard timeout, so the live pull drops to 10s and the classifier cap to 16 items.

`GROQ_API_KEY` lives in Vercel's environment variables. **Adding it requires a redeploy** —
Vercel bakes env vars in at deploy time, so an existing deployment will not pick it up.

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
every draft it produces. Run it with `python -m unittest discover -s tests` — standard
library, nothing to install. Note it is deliberately *not* a "no networking" rule: the
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
- **No real shipment/TMS integration.** Shipments are synthetic. The TMS Link is a *demo
  connector*: it models the field mapping and describes the write-back a decision implies,
  and contacts nothing. Wiring a real TMS is on the far side of the integration/trust wall,
  not in this build.
- **No scheduler / always-on.** Button-triggered.
- **No database.** In-memory + JSON files.
- **No paid data.** Free sources only.
- **No accounts, billing, multi-tenant, or the real 5U AI product.** The AI-Worker layer is cosmetic.

---

## Design principles

- **One file per job, one job per file.** If a file does two things, split it.
- **`llm.py` is the only door to the AI provider.** Everything else calls `llm.py`.
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

Five criteria, from `PRD.md`. If these hold, the prototype is finished and nothing else is in scope:

1. The demo narrative runs start to finish in under ~2 minutes, on command, without breaking.
2. The Risk Monitor genuinely pulls live news — the credibility anchor.
3. The injected strike produces three distinct, defensible decisions across the 5 shipments, each
   with plain-English reasoning.
4. Drafted emails read like something a human would actually send.
5. It looks good enough to present — cards, states, and drafts legible on a screen in a room.

---

## Document map

| File | What it's for |
|---|---|
| `START-HERE.md` | Orientation, the pitch, the demo narrative, build order |
| `SETUP.md` | One-time human setup: Node/Claude Code/Python, GitHub CLI, free AI key, `.env` |
| `PRD.md` | *What* and *why* — problem, success criteria, non-goals, differentiation |
| `DESIGN.md` | *How* — architecture, stack, file structure, design principles |
| `DATASET.md` | The screenplay — chokepoints, routes, 5 shipments, the injected strike |
| `DATA-SOURCES.md` | Curated free APIs: which to wire (CORE) and which to skip |
| `BUILD-GUIDE.md` | The copy-paste phase prompts — the spine of the build |
| `README.md` | The front door — what it is, how to run it, the honest framing |
| `trade-risk-agent-docs.zip` | Duplicate archive of the seven docs above; not a source of truth |

---

## Honest framing (carry it, don't bury it)

This is scripted where it needs to be (the injected disruption) and real where it earns credibility
(the news pull). It's a strong learning artifact and a compelling demo — **not a live product**. The
gap between this and a business is the integration/trust/liability wall, which is real work for
later. Build this first; it teaches every piece of how an agent actually works.
