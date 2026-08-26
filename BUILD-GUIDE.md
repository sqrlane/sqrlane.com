# BUILD-GUIDE.md — build it, step by step

> **This is a build-time document, kept as the record of how the prototype was
> planned.** The build has moved on since: the pool grew to **seven bookings** and
> four scenarios, and the loop now opens and closes on the forwarder's TMS — the
> bookings are read out of the system of record through `src/tms.py` and every
> agent action is queued back onto them. `CLAUDE.md` and `README.md` describe what
> the system does today; read those first if the two disagree.

This is your spine. Work top to bottom. Each phase has: a **prompt to paste into Claude Code**, a **checkpoint** (how you know it worked), and a **commit** step (save to GitHub).

**Rules of the road:**
- Do `SETUP.md` completely before Phase 1.
- Paste one prompt, let it finish, check the checkpoint, *then* move on. Don't batch phases.
- If something breaks, paste the error back to Claude Code and say "this failed, here's the error: …". Fixing errors this way *is* the skill.
- After every phase, run the commit prompt.

> **The commit prompt (use after each phase):**
> "Commit everything with a clear message describing what we just built, and push to GitHub."

---

## Phase 0 — orient Claude Code

**Paste:**
> "Read START-HERE.md, PRD.md, DESIGN.md, DATASET.md, and DATA-SOURCES.md fully. Summarise back to me in a few sentences: what we're building, the demo narrative, and the components. Don't write any code yet — I just want to confirm you understand before we start."

**Checkpoint:** its summary matches the demo narrative and lists Risk Monitor, Route Advisor, Comms Agent, Orchestrator/Dashboard. If it's off, correct it now — this context carries through everything.

---

## Phase 1 — dataset + Risk Monitor (the real, live part)

**Paste:**
> "Phase 1. Do two things.
> First, create the `data/` JSON files exactly from DATASET.md: chokepoints, candidate routes, the 5 shipments, and the injected Hamburg strike event.
> Second, build `src/llm.py` (the single wrapper for our AI provider, reading the key from `.env` — set it up for the provider I chose in SETUP), `src/config.py`, and `src/risk_monitor.py`.
> The Risk Monitor must pull live data from the sources in DATA-SOURCES.md, across all six families — news (GDELT plus RSS feeds including at least one German-language feed), river gauges, weather and sea state, natural hazards, government filings and reference rates. Keep each source in its own small function so one can be added or pulled without touching the others, and make sure none of them can take the run down. Send prose to the LLM to classify as logistics-relevant or not, tagging relevant ones with chokepoint / type / severity; classify numbers by threshold instead. Write it all to `risk_state.json`. It must also be able to load the injected Hamburg event in the same format.
> Give me a way to run just the Risk Monitor from the terminal and see the events it found. Explain how to run it."

**Checkpoint:** you run the Risk Monitor alone and see real, current news items classified, plus the injected strike loadable. Confirm at least one non-English source is actually being read.

**Commit.**

---

## Phase 2 — Route Advisor

**Paste:**
> "Phase 2. Build `src/route_advisor.py`. Given one shipment (with its candidate routes) and the current `risk_state.json`, it should: find which chokepoints each candidate route touches, cross-reference active risk, and use the LLM to decide reroute / hold / no-action — weighing schedule slack vs. added transit vs. expected disruption delay. It must return the decision plus plain-English reasoning and a recorded reasoning trail.
> Let me run it against the 5 shipments with the injected Hamburg strike active, printed to the terminal. I want to see it produce the three expected outcomes from DATASET.md: SHP-001 and SHP-005 reroute, SHP-002 hold+notify, SHP-003 and SHP-004 no-action — each with reasoning."

**Checkpoint:** the three outcomes appear with sensible reasoning. If a decision is wrong, tell Claude Code which shipment and what the right call is (per DATASET.md) and have it adjust the prompt/logic. Getting the reasoning to read *well* matters — this is the demo's centrepiece.

**Commit.**

---

## Phase 3 — Comms Agent

**Paste:**
> "Phase 3. Build `src/comms_agent.py`. Given a shipment with an actioned decision (reroute or hold), use the LLM to draft two emails: one to the carrier (booking change or hold instruction) and one to the customer (status + revised ETA, appropriate tone). Return them as text. It must NOT send anything — no email libraries, no SMTP.
> Let me run it for SHP-001 (reroute) and SHP-002 (hold) and read the drafts in the terminal."

**Checkpoint:** the drafts read like something a person would actually send — specific to the cargo, the route change, the revised ETA. Refine tone with Claude Code until they're presentable.

**Commit.**

---

## Phase 4 — Orchestrator + dashboard (wire it together)

**Paste:**
> "Phase 4. Build `src/orchestrator.py` and the web app. The orchestrator loop: on trigger, refresh risk (including the injected Hamburg event), run the Route Advisor over all shipments, run the Comms Agent for every actioned shipment, and assemble one result object (each shipment: state, decision, reasoning, any drafts).
> Then build `src/app.py` (FastAPI) with a `POST /run` endpoint that runs the orchestrator and returns that JSON, and serves `static/index.html`.
> Build `static/index.html` as a single clean, presentable page: 5 shipment cards that start green and change to rerouted / hold / green after running; a risk feed showing the detected event and its source language; click a card to expand its reasoning; and show the drafted emails for actioned shipments. One trigger button labelled like 'Inject Hamburg strike' runs everything. Make it look good — clear hierarchy, restrained colours, readable in a room. Tell me how to start it and what URL to open."

**Checkpoint:** you open the URL, see 5 green cards, click the button, and the whole narrative plays on screen — cards change, reasoning expands, emails appear. **This is the demo.** Walk the START-HERE narrative against it end to end.

**Commit.**

---

## Phase 5 — polish for the presentation

Small passes, one prompt each, only what the demo needs:

- > "Add the light '5U AI-style AI Worker' framing on top — a header/branding treatment that presents this as an AI Worker product, cosmetic only. Keep it tasteful."
- > "The demo needs to survive a live audience. Add graceful handling so that if a live news source is slow or down, the app still runs the injected scenario without erroring. Show a small note if a source failed rather than crashing."
- > "Add a tiny on-screen legend/label making clear which data is live (the news pull) and which is synthetic (the shipments), so I can honestly answer 'is this real?' during the demo."
- > "Write a short README.md: what this is, how to run it, and the one-line honest framing about live vs. synthetic data."

**Checkpoint:** you can run the full demo cold, it doesn't break if wifi is flaky, and the live-vs-synthetic distinction is visible.

**Commit. You're done.**

---

## If you get stuck (you will, everyone does)

- Paste the exact error back to Claude Code: "This failed: [paste]. Fix it and explain what went wrong."
- If a phase's result is wrong rather than broken, point at the specific shipment/decision and cite DATASET.md.
- If the web UI feels too fiddly, tell Claude Code: "Rebuild the dashboard as a Streamlit app instead" — pure Python, much less to break (DESIGN.md notes this fallback).
- Keep each request to one thing. "Fix X" beats "fix X and also add Y and change Z."

## What you'll have learned

By Phase 4 you'll have built, by hand-directing, the entire agent loop: **perceive** (Risk Monitor) → **reason** (Route Advisor) → **act** (Comms Agent) → **orchestrate** (the loop) — on free tools, with a real, presentable result. That's the actual foundation. Everything fancier is a variation on this.
