# PRD.md — Product Requirements

*What we're building and why. Not how (that's DESIGN.md).*

## Problem

Freight forwarders live inside two jobs at once: watching for disruptions that threaten shipments in transit, and reacting fast when one hits (reroute, hold, notify the customer, and re-key all of it into the TMS). Today that means a person scanning news and portals, then manually deciding, emailing, and updating the booking.

Both halves are worse than they look. The *watching* is narrower than the problem: a lane is moved by a strike, a gale over the crane, a river that has dropped, a swell off the Cape, a wildfire across a rail leg and a tariff filed in Washington — signals that arrive from broadcasters, waterway authorities, weather services, seismic networks, government registers and central banks, in that many formats. Someone reading trade press between other calls is seeing a summary of a fraction of it, late; and anything that surfaces first in a non-English source is later still. The *reacting* is worse: existing risk tools (Everstream, Interos, Resilinc) alert big shippers but stop at the alert; they don't decide or act, and they're priced out of the mid-market. The TMS sits on the other side of the same gap: it holds the booking and moves it once someone has already decided, but it does not watch the world. The desk is the manual bridge between the two — and the last plank of that bridge, keying each decision back onto each booking, is the part that eats the day.

## What we're building

A prototype that **works through the forwarder's TMS**, where small AI agents:
0. **Read** the book of bookings out of the TMS — the system of record, not a second copy.
1. **Detect** logistics-relevant disruptions from live, free, keyless sources across six families — news (multilingual), river gauges, weather and sea state, natural hazards, government filings and reference rates.
2. **Decide** per booking whether to reroute, hold, or do nothing — with recorded reasoning.
3. **Draft** the resulting carrier and customer emails for a human to approve.
4. **Write back** each of those actions as a change to the booking it came from — the risk exception, the new discharge port, routing code and ETA, the drafted mail on the communication log — every one held for the same human approval.

In this build the TMS is a **demo connector**: both directions are modelled and the read is the only door to the book, but no TMS is contacted and nothing is written.

A light "AI Worker" wrapper presents this as a 5U-AI-style product for demo framing only.

## Who it's for

The person being shown the demo: a forwarder operations lead, an investor, or an interviewer. The *modelled* end user is a mid-size DACH/Benelux forwarder's Head of Operations.

## Success criteria

This is a prototype, so success is narrow and specific:

- The **demo narrative in START-HERE.md runs start to finish in under ~2 minutes**, on command, without breaking.
- The **Risk Monitor genuinely pulls live news** (real, verifiable) — the credibility anchor.
- On the injected strike, the system produces **three distinct, defensible decisions** across the 5 shipments (reroute / hold / no-action), each with plain-English reasoning.
- **Drafted emails read like something a human would actually send.**
- It **looks good enough to present** — cards, states, and drafts are legible on a screen in a room.
- **Every decision lands on the booking it came from** — read through one door, queued back against the record, and visibly waiting on a person.

If those six hold, the prototype is done. Nothing else is in scope.

## Explicitly NOT in this build (non-goals)

Naming these protects you from scope creep — the thing that kills beginner projects.

- **No real route optimisation.** Routes are pre-authored candidates; the agent *chooses among them and justifies the choice*. It does not compute routes.
- **No sending of anything.** Emails are drafted and displayed only.
- **No *live* TMS connection.** Working through the TMS is the design, not a non-goal — what is out of scope is the far end: no vendor, no credential, no endpoint, and nothing is ever written. The connector models both directions and owns the only read path; the bookings behind it are synthetic (DATASET.md).
- **No scheduler / always-on.** Everything is triggered by a button.
- **No database.** In-memory + simple files are enough for a demo.
- **No paid data.** Free, keyless sources only — news, GDELT, public gauges, public weather, seismic and hazard feeds, government registers and central-bank rates. Breadth is the point; the bill is not.
- **No user accounts, billing, multi-tenant, or the real 5U AI product.** The AI-Worker layer is cosmetic framing.

## The differentiation angle (what makes it more than "AI summarises news")

Two things, and only these two, are the story. The second is the bigger one.

1. **One terminal for everything that moves a lane.** Not a news monitor — 42 free, keyless sources across six families, read together on every run: the wires and the press next to the port, river gauges, port weather and sea state, seismic and natural-hazard feeds, government filings, and the reference rate a reroute is billed at. Prose goes to the model; numbers go to a threshold. Reading close to the event is why a disruption often lands here before the wires carry it, and reading *widely* is why it lands here at all when it never becomes a headline. Breadth is safe because nothing is load-bearing: any single source can be down without the run failing.
2. **The agent does the TMS work — the closed risk → reroute → comms → record loop, with recorded reasoning.** This is the biggest value in the product. Risk incumbents stop at the alert; execution players (like 5U AI) start after the decision and don't touch risk. Between them sits a person re-keying consequences into the booking system, one booking at a time, because that is the only place a decision counts. Welding the two — reading the book out of the system of record, deciding, recording *why*, and putting the result back on the same record as a queued change a human approves — is the whitespace. A decision that never reaches the TMS is a decision nobody acts on.

## Honest caveat (carry this, don't bury it)

The prototype is scripted where it needs to be (the injected disruption), modelled where it must be (the TMS connector — the read is the only door and the write-backs are derived from real decisions, but no TMS is contacted), and real where it earns credibility (the news pull). It is a learning artifact and a compelling demo — not a live product. The gap between this and a business is exactly the integration/trust/liability wall, which is real work for later.
