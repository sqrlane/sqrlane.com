# Trade-Lane Risk & Reroute Agent

Small AI agents watch global news — in several languages — for events that disrupt
shipping. When one hits, the system works out which shipments are affected, decides
whether to **reroute** or **hold** each one, explains *why*, and drafts the carrier and
customer emails a person would otherwise have to write.

Risk → decision → communication, as one closed loop, with the reasoning recorded.

![The dashboard after a run](docs/dashboard.png)

> **The honest line:** the risk detection is real — it runs against live news right now.
> The shipments are synthetic, so a disruption can be shown on demand instead of waiting
> for one. **Emails are drafted and never sent.**

That distinction is on screen, not buried in a footnote: the risk feed is marked *live*,
the shipment board is marked *synthetic*, and every event says whether it came from a
real source or the scripted scenario.

---

## Run it

Needs Python 3.11+.

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env        # then paste a free API key into .env
uvicorn src.app:app --reload
```

Open **http://127.0.0.1:8000** and press **Inject Hamburg strike**.

For the AI key, pick one free provider and put it in `.env`:

| Provider | Where | `.env` |
|---|---|---|
| **Groq** (recommended) | https://console.groq.com | `GROQ_API_KEY=…` (provider defaults to groq) |
| Google Gemini | https://aistudio.google.com/apikey | `LLM_PROVIDER=gemini`, `GEMINI_API_KEY=…` |
| Ollama (local, no key) | https://ollama.com | `LLM_PROVIDER=ollama` |

You do **not** set a model name. On Groq the app asks your key which models it can
actually run and picks the best available one, because Groq retires and renames
models and a hard-coded name that has been retired fails with a 404 that looks
exactly like a broken key. To see what your key offers:

```bash
python -m src.llm --models
```

Pin one with `LLM_MODEL` in `.env` only if you want a specific model — and even then,
if it turns out to be unavailable the app falls back to discovery rather than failing.

Without a key it still runs — decisions and emails come from deterministic fallbacks,
and every card that used one is badged `rule` so you can see it.

---

## What happens when you press the button

1. **Five shipments in transit**, all green.
2. **A strike hits the Port of Hamburg.** One click.
3. **It was caught from a German-language source first** — the feed shows the original
   headline (*"Warnstreik im Hamburger Hafen…"*) next to the English one, roughly a day
   before the English wires carried it.
4. **All five are triaged in seconds** — two reroute, one holds, two stay green. It
   doesn't cry wolf.
5. **Each decision opens up** into plain-English reasoning, the routes it rejected and
   why, and the full recorded trail of checks behind the call.
6. **The emails are drafted** — one to the carrier, one to the customer. Nothing is sent.

The whole thing runs in well under two minutes.

---

## The four components

| | | |
|---|---|---|
| **Risk Monitor** | `src/risk_monitor.py` | Pulls GDELT, multilingual RSS and Rhine gauges. An LLM classifies each item for logistics relevance → chokepoint, type, severity. |
| **Route Advisor** | `src/route_advisor.py` | Weighs schedule slack against added transit against expected disruption delay. Decides reroute / hold / no-action, and records the trail. |
| **Comms Agent** | `src/comms_agent.py` | Drafts a carrier email and a customer email, in two deliberately different voices. Sends nothing. |
| **Orchestrator** | `src/orchestrator.py` | The loop, plus `src/app.py` (FastAPI) and `static/index.html` (the dashboard). |

Each runs on its own, which is how you debug one without the others:

```bash
python -m src.risk_monitor  --inject          # add --no-llm to skip the AI call
python -m src.route_advisor --inject --shipment SHP-002
python -m src.comms_agent   --inject
python -m src.orchestrator  --no-live         # the whole loop, no network
```

---

## Deploying to Vercel

The repo is configured for it: `api/index.py` re-exports the same FastAPI app,
and `vercel.json` rewrites every path to it, so `/` and `POST /run` both land on
one function.

1. In Vercel, **Add New → Project** and import this GitHub repo.
2. Framework preset **Other**. Leave build and output settings empty — `vercel.json`
   handles it.
3. Add your AI key under **Settings → Environment Variables**
   (`LLM_PROVIDER` and `GROQ_API_KEY`), then redeploy so it takes effect.

**Check `/api/health` first.** It reports what the running app can actually see —
the path it received, whether the dashboard and data files shipped, and whether a
provider is configured. If something is wrong, it will say so there before you go
hunting.

Serverless changes two things, both handled automatically:

- **The filesystem is read-only.** `risk_state.json` is written to the temp
  directory instead. Nothing is kept between requests, which is fine — this app
  has no database and never did.
- **Functions have a hard timeout.** `maxDuration` is 60s, and on a deployed host
  the live pull is trimmed to 10s and the classifier to 16 items to leave room for
  the LLM calls. Tune with `LIVE_PULL_BUDGET_SECONDS` and `MAX_ITEMS_TO_CLASSIFY`
  if a run gets cut off.

> **A demo you are presenting should run locally.** A full cycle makes up to a
> dozen sequential model calls, and on a cold serverless function that can bump the
> 60-second ceiling. Locally there is no ceiling and no cold start. Deploy for
> sharing a link; run `uvicorn` for the room.

---

## Built to survive a live audience

- **A dead source is skipped, not fatal.** Each one is read in its own function and its
  failure is recorded and shown.
- **A slow source cannot stall the demo.** The whole live pull has a hard 25-second
  budget; whatever isn't read by then is skipped and the cycle moves on.
- **No provider, no problem.** Decisions and drafts fall back to deterministic logic,
  clearly badged.
- **The page is self-contained.** No CDN, no external font, no request beyond its own
  API — flaky wifi can't blank it.
- **A failed run shows a sentence, not a stack trace.**

---

## What this is not

No real route optimisation (routes are pre-authored candidates the agent *chooses among*
and justifies). No sending. No TMS integration. No scheduler. No database. No paid data.
The "AI Worker" framing on the header is cosmetic.

It is a learning artifact and a demo — not a live product. The gap between this and a
business is the integration, trust and liability wall, which is real work for later.

---

## Where things are

```
data/     the screenplay - chokepoints, routes, 5 shipments, the injected strike
src/      the four components + llm.py (the only door to the AI provider) + config.py
static/   index.html - the dashboard, one self-contained file
*.md      the planning docs; CLAUDE.md is the working summary
```

`.env` and `risk_state.json` are gitignored. **Never commit `.env`.**
