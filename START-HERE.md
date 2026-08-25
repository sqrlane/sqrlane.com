# START HERE — Trade-Lane Risk & Reroute Agent (Prototype)

> **What this is:** a set of planning + build documents for an AI-agent prototype you build with Claude Code.
> **Your background:** no coding experience — that's fine. You will not write code by hand. You paste prompts into Claude Code and it builds.
> **The goal:** one polished, presentable prototype that tells a clear story in ~2 minutes. Not a real product, not scale, not real integrations. A demo.

---

## The one-paragraph pitch

Small agents watch **everything that moves a trade lane** — 42 free, keyless sources across six families: news in multiple languages, river gauges, port weather and sea state, seismic and natural-hazard feeds, government filings, and the reference rate a reroute is billed at. When a disruption hits, the system reads your bookings out of the TMS, works out which are affected, decides whether to reroute or hold each one — and *explains why* — drafts the carrier and customer emails a human would need to send, and **queues each change back onto the booking it came from**, which is the part a person otherwise re-types. Risk → decision → communication → the system of record, as one closed loop, with the reasoning recorded and every write held for approval. A light "5U AI-style AI Worker" wrapper sits on top purely as demo framing.

---

## The demo narrative (this IS the spec — everything serves this)

Read this out loud. If a feature doesn't help this story land, it doesn't get built.

1. **"Here are 5 bookings out of your TMS, in transit."** A dashboard shows 5 shipment cards, all green.
2. **"Watch — a strike hits the Port of Hamburg."** You click a trigger button.
3. **"The system caught it from a German-language source before the English news wires."** The risk feed shows the event, flagged as detected from a German source first — and beside it, the family strip showing the other 41 sources read on the same run: the gauges, the weather, the hazard feeds, the government filings, the rates. *(This part runs against real, live sources — see below.)*
4. **"It triaged all 5 shipments in seconds."** Cards change state:
   - Two Hamburg-bound shipments with schedule slack → **reroute** (via Rotterdam).
   - One tight cold-chain Hamburg shipment → **hold + notify** (rerouting would be worse).
   - Two shipments bound for other ports → **stay green** (the system doesn't cry wolf).
5. **"Here's the reasoning for each decision."** Click a rerouted card → plain-English justification (slack vs. added transit vs. strike delay).
6. **"And here are the emails it drafted."** Two drafts appear — one to the carrier, one to the customer. *Nothing is sent.*
7. **"And here is what goes back into the TMS."** The change each decision implies, queued against the booking it came from — exception, discharge port, routing code, ETA, communication log. *Nothing is written.* This is the biggest thing the agents do: the desk stops re-keying.
8. **"All of that, from one event, on command."**

**The honest line to have ready** when someone asks "is this real?":
> "The risk detection is real — it runs against live news right now. The shipments are synthetic, so I can show you a disruption on demand instead of waiting for one."

That's a strong, truthful position. It's why the Risk Monitor stays genuinely live even though everything downstream runs on authored data.

---

## The files in this repo

| File | What it's for | Who reads it |
|---|---|---|
| `START-HERE.md` | This file — orientation | You, first |
| `SETUP.md` | One-time setup: install tools, GitHub, free AI key | You |
| `PRD.md` | *What* you're building and *why* (product) | You + Claude Code |
| `DESIGN.md` | *How* it's built: architecture, stack, file structure | Claude Code |
| `DATASET.md` | The "screenplay" — dummy shipments, routes, the scripted strike | Claude Code |
| `DATA-SOURCES.md` | The curated free APIs to actually use (and which to skip) | You + Claude Code |
| `BUILD-GUIDE.md` | The copy-paste prompts, phase by phase | You — this is your spine |

**How to use them:** do `SETUP.md` once. Then open `BUILD-GUIDE.md` and work top to bottom, pasting each phase's prompt into Claude Code. The other files are reference material Claude Code reads on its own.

---

## The build order (why it's phased)

You never build everything at once. Each phase is independently demoable, so if you get stuck you still have something real to show.

1. **Phase 0** — Setup + empty repo on GitHub.
2. **Phase 1** — Dummy dataset + **Risk Monitor** (the real, live part — reads all six source families in DATA-SOURCES.md).
3. **Phase 2** — **Route Advisor** (reasons and recommends).
4. **Phase 3** — **Comms Agent** (drafts emails, sends nothing).
5. **Phase 4** — **Orchestrator + dashboard** (wire it together, the trigger button).
6. **Phase 5** — Polish for the presentation.

There is **no scheduler** and **no "always running."** For a demo, a button beats a background job every time — the magic has to happen on screen, on command.

---

## One thing to keep in mind

A working dummy prototype is exactly the right thing to build and a genuinely impressive learning artifact. It is *not yet a business* — the moment it touches a real shipment you hit integrations, trust, and liability, which is the hard part your own research (the "constraint is distribution, not product" finding) is really about. Keep asking "who would pay, and how would I reach them?" in parallel. But build this first — it teaches you every piece of how an agent actually works.
