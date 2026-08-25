# PRD.md — Product Requirements

*What we're building and why. Not how (that's DESIGN.md).*

## Problem

Freight forwarders live inside two jobs at once: watching for disruptions that threaten shipments in transit, and reacting fast when one hits (reroute, hold, notify the customer, and re-key all of it into the TMS). Today that means a person scanning news and portals, then manually deciding, emailing, and updating the booking. Disruptions that surface first in non-English sources — a German port strike, an Arabic-language Red Sea incident — are seen late. Existing risk tools (Everstream, Interos, Resilinc) alert big shippers but stop at the alert; they don't decide or act, and they're priced out of the mid-market. The TMS sits on the other side of the same gap: it holds the booking and moves it once someone has already decided, but it does not watch the world. The desk is the manual bridge between the two.

## What we're building

A prototype that **works through the forwarder's TMS**, where small AI agents:
0. **Read** the book of bookings out of the TMS — the system of record, not a second copy.
1. **Detect** logistics-relevant disruptions from live, multilingual news.
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
- On the injected strike, the system produces **three distinct, defensible decisions** across the board (reroute / hold / no-action), each with plain-English reasoning.
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
- **No Bloomberg / paid data.** Free sources only (news, GDELT, public gauges).
- **No user accounts, billing, multi-tenant, or the real 5U AI product.** The AI-Worker layer is cosmetic framing.

## The differentiation angle (what makes it more than "AI summarises news")

Two things, and only these two, are the story:

1. **Earlier signal from non-English sources.** English-only tools miss a German `Warnstreik` or an Arabic-language port notice until it hits the wires. Reading regional/multilingual sources *first* is a real informational edge.
2. **A closed risk → reroute → comms loop that runs on the TMS, with recorded reasoning.** Risk incumbents stop at the alert; execution players (like 5U AI) start after the decision and don't touch risk. Welding them — reading the book out of the system of record, deciding, recording *why*, and putting the result back on the same record — is the whitespace. The loop opening and closing in the same place is what makes it operational rather than advisory: a decision that never reaches the TMS is a decision nobody acts on.

## Honest caveat (carry this, don't bury it)

The prototype is scripted where it needs to be (the injected disruption), modelled where it must be (the TMS connector — the read is the only door and the write-backs are derived from real decisions, but no TMS is contacted), and real where it earns credibility (the news pull). It is a learning artifact and a compelling demo — not a live product. The gap between this and a business is exactly the integration/trust/liability wall, which is real work for later.
