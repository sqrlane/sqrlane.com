# The pre-departure loop — the next live agent, and why it leads

*Direction set by the owner, 2026-08-28, out of the lab-notes discussion. This
note captures the thesis and the design reasoning while both are fresh. It is
a roadmap document: nothing in it exists yet, and nothing in it may be
presented as existing.*

---

## The thesis

Today's three live agents are **reactive**: a disruption is detected, and the
system decides what to do about cargo already on the water. That is the
hardest loop and the right one to have proven first — but it acts at the
most expensive moment in a shipment's life. Once a container is on a vessel,
"reroute" means diversion fees, a longer inland leg, a reissued bill of
lading, a moved customs entry.

**The next live agent works before departure, and it leads.** The whole point
of understanding risk is to act *way in advance*: choose a different carrier,
a different routing, a different sailing — or hedge — while all of those are
still cheap. Before commitment, changing everything costs almost nothing.
After commitment, changing anything costs real money. The earlier the
decision point, the cheaper the fix; the pre-departure agent owns the
earliest one.

Working name: **the Planner**. (Our own name, as ever.)

## What "leads" means here — and what it must not mean

The Planner leads in three concrete senses:

1. **It acts on its own initiative.** Every existing agent waits for
   something — an event, a mail, a click. The Planner *sweeps*: on a
   schedule, it walks every shipment in the forward book (quoted, booked,
   not yet departed), asks what the world will look like when each one
   moves, and decides which need attention. It is the only agent whose
   default state is looking ahead rather than listening.
2. **It initiates work for the other agents.** A Planner finding is not a
   report; it is a proposed plan written onto the shipment's record, which
   is exactly the trigger the others already respond to: RFQ prices the
   alternative routing, Booking drafts the rebooking or amendment, Comms
   drafts the customer advisory, the TMS link queues the changes. The
   Planner starts the cascade the way a disruption event starts today's.
3. **It owns the decision menu the others don't have.** In transit the menu
   is reroute / hold / do nothing. Pre-departure the menu is wider, and
   most of it is hedging: book a different carrier or sailing; leave
   earlier to buy slack; **split** the shipment across two routings;
   book flexible or refundable terms as an option; price the risk into the
   customer's quote; escalate to a human with the trade-offs priced. Hedges
   only exist before commitment — that is why this agent, not the in-transit
   advisor, carries them.

**What it must not mean:** a hub that routes messages between agents. This
repo's standing rule — *agents coordinate through the record, not through
each other* — is what keeps every decision auditable, testable and gated,
and it holds for the Planner too. The Planner leads the way a chief
dispatcher leads: it decides what needs doing and writes that onto the
booking; the record is still the only medium, the orchestrator is still
plain functions, and the human approval gate is still the only exit. A
central super-agent that privately negotiates with other agents would hide
exactly the reasoning this product exists to show.

## Almost everything it needs already exists

This is the striking part: the Planner is mostly a re-aiming of proven
machinery at an earlier point in time.

| The Planner needs | Already built | Where |
|---|---|---|
| The risk picture | 60-source live read, two-tier lane/context | `risk_monitor.py`, `signals.py` |
| "Will it still be there when this shipment moves?" | the timing question — with days-to-passage counted from ETD instead of mid-voyage | `timing_factor` in `route_advisor.py` |
| Options priced in euros, not days | the cost model: premium + late fees + breach + transfer | `cost_of` in `route_advisor.py` |
| Risk priced into a quote | the RFQ worker's scenario surcharge — the seed of risk-aware quoting | `roster.py` |
| "How likely does this booking break its deadline?" | the breach model, scored AUC 0.8814 in the practice world | `ml/` |
| A place for every output | the write-back queue and the approval gate | `tms.py` |
| A way to measure whether any Planner policy is good | the practice world and its answer key | `ml/synth.py`, `ml/evaluate.py` |

## What is genuinely new

1. **Forecast, not just detection.** In transit, the disruption already
   exists and timing suffices. Four days before departure, the question is
   sometimes *"what are the odds this brewing situation becomes a
   closure?"* — a forecast. That is exactly where the phase-two source
   family in `deck/SOURCES.md` earns its place: prediction markets (a
   traded probability is a forecast with money behind it), plus base rates
   by episode type. **Honesty rule carried forward: a forecast is labelled
   a forecast, with its source, and no probability is ever invented.** The
   cry-wolf discipline applies with extra force — rebooking around a strike
   that never happens costs real money too, which is precisely why the
   hedge options (cheap, reversible) sit between "rebook everything" and
   "do nothing".
2. **Alternatives as live data.** The in-transit advisor chooses among
   alternates already on the booking. The Planner's whole value is choosing
   among *market* alternatives — other carriers, other sailings, other
   routings — which needs schedule and rate data (carrier APIs, rate
   platforms). That is integration-wall work, same wall as the TMS.
3. **The forward book as records.** Today the connector models in-transit
   bookings. The Planner reads quotations and unshipped bookings — earlier
   lifecycle states of the same record, same single door.

## How it would be proven (the same ladder as everything else)

1. **Practice world first.** Extend `ml/synth.py` with pre-departure
   decision points and the wider menu (rebook / split / buy-slack / price-in
   / do-nothing), each arm priced by the same structural model. Score
   Planner policies against the answer key exactly as the in-transit
   policies were scored — same split hygiene, same anti-circularity guards,
   numbers stay in `ml/reports/`.
2. **Scripted Worker second.** A `Planner` pill on the board, `SCR`-tagged
   like its peers: an authored pre-departure scenario (the owner's example:
   *departure in four days, a wildfire on the land leg with a high chance
   of closure*) showing the sweep, the priced menu, the hedge, and the
   cascade it initiates — honest about being authored, exactly like Inbox
   and Customs today.
3. **Live third,** behind the integration wall, where the rate and schedule
   data lives.

## The one-line version

> Detection tells you what is happening. Timing tells you whether it reaches
> you. **Planning is choosing, while choosing is still cheap** — and the
> agent that does it goes first, because everything downstream of it gets
> easier the earlier it acts.
