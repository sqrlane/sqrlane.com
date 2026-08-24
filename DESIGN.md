# DESIGN.md — Technical Design

*How it's built. Read alongside PRD.md (why) and DATASET.md (the data).*

## Architecture — four components

The same shape 5U AI uses (listener → worker → approval → communicator), which is a good sign the instincts are right.

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
  [ Dashboard ] <-- shows shipment states, reasoning, drafts; has the trigger button
```

### 1. Risk Monitor (the real, live part — build first)
- Pulls from **free** sources: GDELT (no key), RSS feeds (feedparser), and at least one German-language source so the "caught it first" story is true. The exact curated list — and which sources to skip — lives in **DATA-SOURCES.md**; use the ones marked CORE.
- For each item: use the LLM to classify — is this logistics-relevant? Which **chokepoint** (see DATASET.md) does it affect? What **type** (strike/weather/congestion/geopolitical/customs) and **severity** (low/med/high)?
- Writes structured events to `risk_state.json`.
- **Also accepts an injected event** (the scripted Hamburg strike) via the trigger, so the demo is on-command. Injected and live events use the same format — the audience can't tell the plumbing apart, and you tell them honestly which is which.

### 2. Route Advisor
- Input: one shipment (with its candidate routes) + current risk_state.
- Checks which chokepoints each candidate route touches, cross-references active risk.
- Uses the LLM to weigh **schedule slack vs. added transit vs. expected disruption delay** and pick: `reroute` (and to which route), `hold`, or `no-action`.
- Output: decision + **plain-English reasoning** + a recorded reasoning trail (this is the "decision layer").

### 3. Comms Agent
- Input: one shipment with an actioned decision.
- Uses the LLM to draft a **carrier email** (booking change / hold instruction) and a **customer email** (status + revised ETA).
- Returns drafts as text. **Sends nothing.** No email library, no SMTP.

### 4. Orchestrator + Dashboard
- Orchestrator is the loop: on trigger → refresh risk → for each shipment call Route Advisor → for each actioned shipment call Comms Agent → assemble a result object → return to the dashboard.
- Dashboard renders shipment cards (green / rerouted / hold), a risk feed, click-to-expand reasoning, and the drafted emails. One **trigger button** runs the loop.

## Stack (chosen for a beginner + a presentable result)

- **Backend:** Python + **FastAPI**. One endpoint the button calls (`POST /run`) that runs the orchestrator and returns JSON.
- **Frontend:** a **single HTML page** with vanilla CSS/JS (no framework to learn). It calls `/run` and renders the result. Keep it clean and legible — this is what people see. Claude Code should apply solid visual-design judgment (clear hierarchy, restrained palette, readable cards) since the look is part of the deliverable.
- **AI calls:** a single wrapper module (`llm.py`) so the provider (Groq / Gemini / local) can be swapped in **one file**. Never call the provider directly from anywhere else.
- **Data:** JSON files for shipments, routes, chokepoints (from DATASET.md), and `risk_state.json` for live/injected risk. No database.

> **Alternative if the web UI feels heavy:** the whole thing can be a **Streamlit** app (pure Python, no HTML/JS). Less custom-looking, far less to break. Fine fallback — but default to FastAPI + HTML for the visual drama of cards flipping state.

## File structure Claude Code should create

```
trade-risk-agent/
├── START-HERE.md  PRD.md  DESIGN.md  DATASET.md  BUILD-GUIDE.md  SETUP.md
├── .env                      # your key — never committed
├── .gitignore
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
│   └── app.py                # FastAPI: serves the page + /run endpoint
├── static/
│   └── index.html            # the dashboard (single file: HTML+CSS+JS)
└── risk_state.json           # written at runtime (gitignored)
```

## Design principles (hold these)

- **One file per job, one job per file.** If a file does two things, split it.
- **`llm.py` is the only door to the AI provider.** Everything else calls `llm.py`.
- **Each component runnable alone.** You must be able to run the Risk Monitor by itself and see output before the Route Advisor exists.
- **Human-in-the-loop is a feature, not a limitation.** The Comms Agent drafts; it never sends. Say this in the demo — it's the responsible design.
- **No framework for the agent loop.** The orchestrator is plain functions calling functions plus a shared JSON state. Only reach for CrewAI/LangGraph if that genuinely becomes painful — they hide the exact thing you're learning.
