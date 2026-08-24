# PRD.md — Product Requirements

*What we're building and why. Not how (that's DESIGN.md).*

## Problem

Freight forwarders live inside two jobs at once: watching for disruptions that threaten shipments in transit, and reacting fast when one hits (reroute, hold, notify the customer). Today that means a person scanning news and portals, then manually deciding and emailing. Disruptions that surface first in non-English sources — a German port strike, an Arabic-language Red Sea incident — are seen late. Existing risk tools (Everstream, Interos, Resilinc) alert big shippers but stop at the alert; they don't decide or act, and they're priced out of the mid-market.

## What we're building

A prototype where small AI agents:
1. **Detect** logistics-relevant disruptions from live, multilingual news.
2. **Decide** per shipment whether to reroute, hold, or do nothing — with recorded reasoning.
3. **Draft** the resulting carrier and customer emails for a human to approve.

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

If those five hold, the prototype is done. Nothing else is in scope.

## Explicitly NOT in this build (non-goals)

Naming these protects you from scope creep — the thing that kills beginner projects.

- **No real route optimisation.** Routes are pre-authored candidates; the agent *chooses among them and justifies the choice*. It does not compute routes.
- **No sending of anything.** Emails are drafted and displayed only.
- **No real shipment/TMS integration.** Shipments are synthetic (DATASET.md).
- **No scheduler / always-on.** Everything is triggered by a button.
- **No database.** In-memory + simple files are enough for a demo.
- **No Bloomberg / paid data.** Free sources only (news, GDELT, public gauges).
- **No user accounts, billing, multi-tenant, or the real 5U AI product.** The AI-Worker layer is cosmetic framing.

## The differentiation angle (what makes it more than "AI summarises news")

Two things, and only these two, are the story:

1. **Earlier signal from non-English sources.** English-only tools miss a German `Warnstreik` or an Arabic-language port notice until it hits the wires. Reading regional/multilingual sources *first* is a real informational edge.
2. **A closed risk → reroute → comms loop with recorded reasoning.** Risk incumbents stop at the alert; execution players (like 5U AI) don't touch risk. Welding them — and recording *why* each decision was made — is the whitespace, and the recorded reasoning is the defensible-feeling part.

## Honest caveat (carry this, don't bury it)

The prototype is scripted where it needs to be (the injected disruption) and real where it earns credibility (the news pull). It is a learning artifact and a compelling demo — not a live product. The gap between this and a business is exactly the integration/trust/liability wall, which is real work for later.
