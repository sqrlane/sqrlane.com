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

1. **Earlier signal from non-English sources.** English-only tools miss a German `Warnstreik` until
   it hits the wires. Reading regional/multilingual sources *first* is a real informational edge.
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

The same three components are surfaced as named **Workers** — Risk, Routing, Comms —
each reporting, on every run, what it actually handled: sources read, shipments triaged,
drafts written, and how many came from the model rather than the fallback. Every number
is counted from that run; nothing is illustrative.

A **decision-engine strip** names the model in use and the model-vs-rules split, so the
central claim is checkable at a glance rather than asserted.

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
| **RSS via `feedparser`** | Reuters, DW, Al Jazeera (EN + AR), gCaptain, **plus German: tagesschau / NDR / ver.di** — this is where the earliness edge lives | No |
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

### Surviving a live audience

The failure mode that actually threatens a demo is not a *dead* source — that fails fast —
but a *slow* one, because sources are read in sequence. So the whole live pull has a hard
**25-second budget** (`LIVE_PULL_BUDGET_SECONDS`) and each request an 8-second timeout.
Whatever is not read by then is marked `skipped` and the cycle moves on. Tested against a
server that accepts connections and never replies: the run ends at 25s with the scenario
intact. Without the budget the same test would take over four minutes.

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

`/` is the landing page and `/app` is the dashboard; both are single self-contained
files. `GET /api/initial` renders the calm five-green-cards board instantly; `POST /run`
is the button. `GET /api/health` reports what a running instance can actually see — the
path it received, whether the dashboard and data files shipped, and whether a provider
is configured. It is the first thing to check when a deploy misbehaves. The page is a single self-contained file — no CDN, no external font, no
network call beyond its own API — so flaky wifi cannot blank it.

Each component still runs alone, which is how you debug one without the others:

```bash
python -m src.risk_monitor --inject
python -m src.route_advisor --inject --shipment SHP-002
python -m src.comms_agent  --inject
python -m src.orchestrator --no-live      # the whole loop, no network
```

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
- **No real shipment/TMS integration.** Shipments are synthetic.
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
