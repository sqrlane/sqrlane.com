# The operator's manual — running the agents that do the TMS work

This is the instruction script for the workflow shown on deck slide 04
(*"The desk work does itself"*): starting the board, triggering a disruption,
watching each agent turn what arrives into a change on the booking, and
working the one human step that gates all of it — approval.

Written to be followed live, step by step, with **what to type**, **what you
should see**, and — where it matters — **what to say out loud**. Windows
commands first (`py`); the Mac/Linux form is the same with `python3`.

**The honest frame, before anything runs.** Thirteen Workers are on the
board. Three are **LIVE** (Risk, Routing, Comms — they genuinely read, decide
and draft on every run). Nine are **SCRIPTED** (they replay authored content,
reactive to the scenario and the selected shipment — the tag on each pill is
the honesty). The TMS Link is a **DEMO** connector: both directions are
modelled, its write-backs are derived from the real decisions of that run,
but no TMS is contacted — no vendor, no credential, no endpoint. **Nothing
is ever sent and nothing is ever written**; every outbound action stops at
`DRAFT - not sent` or `QUEUED - not written`, behind the approval gate. Tests
enforce all of this. Never present it otherwise.

---

## 1. One-time setup (about five minutes)

You need the project folder and Python. If you already have both (you do if
you followed LAB-NOTES-2026-08-28.md), skip to step 3.

1. Install Python, then close and reopen the terminal:

       winget install -e --id Python.Python.3.12

2. Get the project (a browser window will ask you to sign in to GitHub):

       git clone https://github.com/sqrlane/sqrlane.com.git

3. Go into the folder — **every command below runs from here**, with the
   prompt ending in `\sqrlane.com>`:

       cd sqrlane.com

4. Install what it needs:

       py -m pip install -r requirements.txt

5. **Optional but recommended — the AI key.** Create a file named `.env` in
   the folder containing one line:

       GROQ_API_KEY=paste_your_free_key_here

   The key is free at console.groq.com. **Without it the demo still runs**:
   decisions fall back to transparent rules and drafts to templates, and
   every affected card wears a `rule` or `template` badge saying so — the
   designed, honest degradation. With it, the model genuinely decides and
   writes, which is the demo's centrepiece.

If the folder already exists from before, refresh it first with `git pull`.

---

## 2. Start the board

    py -m uvicorn src.app:app --reload

You should see `Uvicorn running on http://127.0.0.1:8000`. Leave this window
running — it *is* the server. Then open in a browser:

- **http://127.0.0.1:8000/app** — the dashboard (this manual lives here)
- `/` is the landing page, `/whitepaper` the technical paper
- `/api/health` — the first thing to check if anything misbehaves: it says
  what the running instance can see and whether a provider is configured

On load the board shows **seven shipment cards, all green** — every one a
booking read out of the TMS connector (`src/tms.py`), the only door to the
book. Nothing has happened yet. That calm is the starting state.

---

## 3. The band above every view — your two main controls

Across the top of every view sits one band:

- **Scenario** — a row of buttons (Hamburg port strike, Red Sea closure,
  Rhine low water, France inland), each labelled `scripted`, with a one-line
  note on what decision type it forces. Click one to arm it. The same seven
  bookings react differently to each — that is the point: one board,
  different disruptions, different defensible answers.
- **Workers** — thirteen pills, each carrying its mode tag (`LIVE`, `SCR`,
  `DEMO`). **Click a pill to open that Worker's panel** below the strip;
  click another to switch, the same one to close. Every panel is built from
  the active scenario and the currently selected shipment, so changing
  either visibly changes the panel.

Select a shipment by clicking its row in the sidebar (the board in
miniature — one row per booking, a live state dot and its id) or its card.

---

## 4. The main run — the eight-step demo script

1. **"Here are 7 bookings out of your TMS, in transit."** You're on
   Overview; all cards green. Point at the sidebar: the dots are real state.
2. **"Watch — a strike hits the Port of Hamburg."** Make sure the *Hamburg
   port strike* scenario is armed, then press the trigger button (top
   right). This is the one button; it calls `POST /run` and runs the whole
   loop: read the book → refresh risk from all 60 live sources → decide
   every booking → draft the mails → queue every change back at the TMS.
3. **"It caught it from a regional source before the international wires."**
   The Risk feed shows the strike with its detection trail — which outlet
   carried it first, in its original language and script, and the measured
   lead over the wires. Under it, the source line: *N of 60 sources read*,
   with the family strip. Say the honest line: **"The risk detection is
   real — it runs against live news right now. The shipments are synthetic,
   so I can show you a disruption on demand instead of waiting for one."**
4. **"It triaged the whole board in seconds."** Back on Overview: **2
   rerouted, 1 held, 4 stay green.** The board ring shows the split. Four
   staying green is the system not crying wolf.
5. **"Here's the reasoning."** Click SHP-002 — the centrepiece: reefer
   pharma, one day of slack, the customer *in* Hamburg, no good alternative.
   Open its reasoning: the trail of checks, the slack-consumed gauge, and
   the least-bad call, in plain English.
6. **"And the emails it drafted."** On an actioned shipment: the carrier
   mail (operational, uses route codes) and the customer mail (plain
   language, revised ETA). Both say `DRAFT - not sent`. **Nothing sends.**
7. **"And here is what goes back into the TMS."** Sidebar → **TMS link**:
   the connector (`connected (demo)` — say the word *demo*), bookings read
   in, and every queued change — exception flag, new discharge port, routing
   code, ETA, drafts filed on the communication log — each `QUEUED - not
   written`, each named by the Worker that produced it. Bookings left on
   plan queued nothing, which is a real answer.
8. **"All of that, from one event, on command."** Total time should be
   well under two minutes.

---

## 5. The TMS-workflow tour — what arrives, which agent, what lands

This is slide 04's table, walked live. For each row: **select a shipment
that was actioned** (SHP-001 is the clean reroute), then **click the
Worker's pill** and read its panel. Every one of these ends as a change on
the booking record — that is what makes it a desk, not a set of panels.

| What arrives | Click this pill | What lands on the booking | Mode |
|---|---|---|---|
| A rate request | **RFQ** | the request read into fields, priced with the scenario's surcharge, a quote drafted on the file | SCR |
| Carrier or customer mail | **Inbox** | mail triaged: intent, linked booking, a reply drafted on the comms log — and for an on-plan booking, *no reply at all* (judgement, not volume) | SCR |
| A bill of lading, an invoice | **Docs** | the document's fields extracted onto the booking | SCR |
| A change to the booking | **Booking** | the carrier amendment the decision forces — reroute = new discharge port, hold = hold at load port — drafted for approval | SCR |
| The carrier's invoice | **Invoice** | reconciled against the agreed rate; under a disruption the unquoted surcharge is flagged as a discrepancy; with none, every line matches and it says so | SCR |
| A new country of entry | **Customs** | the reroute moved the entry country (HAM→RTM is Germany→Netherlands), so it **escalates rather than files** — the honest behaviour for a novel exception | SCR |
| Every one of the above | **TMS Link** | one queued change per action, gated, `QUEUED - not written` | DEMO |

Two things to say while touring:

- **The tags are the honesty.** These panels are scripted — authored
  content, reactive to scenario and shipment. What's authored is the words,
  not the shape: switch scenario or shipment and watch the panel change.
- **They run at once.** Each agent starts when the fact it needs exists
  (Booking waits for Docs' fields, Invoice for the agreed rate, Customs for
  the new port) and nothing waits for a person until the single approval at
  the end.

---

## 6. The approval gate — the one human step

Everything outbound converges here. Press the **bell** (it shows a dot only
when something actually waits) or go to **Approvals** (`#/approvals`).

- One row per waiting item, **grouped by booking** — everything waiting on
  SHP-001 reads as one block, because a write-back's reference *is* the
  shipment. Click a row to open the full draft or change.
- The segmented control filters *awaiting / approved / all*.
- Bulk approve is **select-then-approve**: tick rows, the button carries the
  exact count you're signing off. Never a blind approve-everything.
- **What approving does:** flips the state to `approved` in the browser.
  **What it does not do:** send or write anything — there is no transport in
  the codebase for it to trigger, and a test keeps it that way. Say this out
  loud; human-in-the-loop is the responsible design, not a limitation.

---

## 7. The week, not the snapshot — the simulation

One button-press is one cycle. To show the system *operating*, open
**Simulation** in the sidebar, or run it in a terminal:

    py -m src.simulation

Eight authored days over the same seven bookings: a quiet Monday, the
Hamburg walkout, the Rhine falling *while the strike is still on*, the Red
Sea closing on top of both, a wildfire, two recoveries. State carries
between days — a booking rerouted Tuesday is *on* that route Wednesday; a
held booking pays a day for every day it waits. Every decision is still made
by the real Route Advisor; only the timeline is authored, and the dashboard
tags it SCRIPTED. One booking ends the week still held because no better
routing exists — a real answer, said out loud.

(Deterministic by default; `py -m src.simulation --llm` opts the 56
decisions into the model, which a free key may not enjoy.)

---

## 8. Each agent alone — the terminal commands

The same components, runnable one at a time. This is how you check a piece
without the whole board, and how the witnessing runs in the lab notes were
done:

    py -m src.signals                          # the 13 instruments: what answered, what it read
    py -m src.risk_monitor                     # all 60 sources + classification
    py -m src.risk_monitor --list-scenarios
    py -m src.risk_monitor --scenario redsea   # arm a scripted disruption
    py -m src.route_advisor --inject           # decide the whole board under the strike
    py -m src.route_advisor --inject --shipment SHP-002
    py -m src.route_advisor --inject --no-llm  # the transparent rules path
    py -m src.comms_agent --inject             # the four drafts, in full
    py -m src.orchestrator --no-live           # the entire loop, no network
    py -m unittest discover -s tests           # every claim-guard (should end "OK")

---

## 9. Driving it like an operator

- **Ctrl/Cmd-K** — command palette: jump to any view, or find any booking by
  id, cargo, origin or destination; Enter opens it.
- **`g` then a key** — go to a view; **`/`** — search; **`?`** — the
  shortcut sheet; **⌘B / Ctrl-B** — collapse the sidebar.
- **Every view has an address** (`#/approvals`, `#/shipments/SHP-002`) —
  refresh keeps your place, and a link to the queue is a link you can send.
- In the Risk feed, an event **names the bookings it moved** — each one a
  button straight to the board.

---

## 10. If something misbehaves

| Symptom | Meaning | Do |
|---|---|---|
| Cards wear `rule` / `template` badges | No AI key, or the provider failed — the designed fallback | Add `GROQ_API_KEY` to `.env`, restart the server. A `template` badge prints its reason underneath |
| Risk feed chip says `no live source` (amber) | The network blocks the sources; the scenario still runs | Honest by design — the board never claims a live read it didn't make |
| Some sources `FAIL` with a readable reason | A third-party feed is down, slow or reshaped | Also by design: no source is load-bearing. `py -m src.signals` before presenting tells you who's answering today |
| Nothing loads at all | Server not running, or port busy | Check the uvicorn window; `/api/health` in the browser is the first diagnostic |
| The page loads but looks stale | An old tab | Hard-refresh; the page is one self-contained file, no CDN to blame |

---

## 11. The lines never to cross

1. Never present a `SCR` panel as live reasoning, or the connector as a
   live TMS link — the tags and the word `demo` are on screen because they
   are true.
2. Never quote a number that wasn't counted on that run — and never quote
   the practice-world model scores (`ml/reports/`) as product accuracy.
3. Never skip the honest line in step 4.3 — it is the credibility of the
   whole demo, not a disclaimer.
4. Nothing sends, nothing writes. If someone asks whether it could — that
   is the roadmap conversation, on the far side of the integration wall.
