"""orchestrator.py - component 4: the loop that ties the other three together.

    trigger -> refresh risk -> advise every shipment -> draft for the actioned
            -> one result object the dashboard can render

No agent framework. This is plain functions calling functions over shared JSON
state, because that is genuinely all it needs to be, and because hiding this
loop inside a framework would hide the exact thing worth understanding.

Two entry points:

    initial_state()  - the board before anything happens: 5 shipments, all green.
    run_cycle()      - the whole loop. What the button calls.

Run it on its own:

    python -m src.orchestrator            # live pull + injected strike
    python -m src.orchestrator --no-live  # injected only, no network
    python -m src.orchestrator --no-llm   # deterministic fallbacks throughout
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone

from src import comms_agent, config, llm, risk_monitor, route_advisor

# What the dashboard colours a card by.
STATE_FOR_DECISION = {"reroute": "rerouted", "hold": "hold", "no-action": "green"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _shipment_card(shipment: dict, routes: dict) -> dict:
    """The parts of a shipment the dashboard shows, decision or no decision."""
    primary = routes.get(shipment["primary_route"], {})
    return {
        "id": shipment["id"],
        "cargo": shipment["cargo"],
        "cargo_detail": shipment.get("cargo_detail"),
        "origin": shipment["origin"],
        "final_destination": shipment["final_destination"],
        "customer": shipment.get("customer"),
        "carrier": shipment.get("carrier"),
        "booking_ref": shipment.get("booking_ref"),
        "cold_chain": bool(shipment.get("cold_chain")),
        "route_id": shipment["primary_route"],
        "route_description": primary.get("description"),
        "discharge_port": primary.get("discharge_port"),
        "transit_days": primary.get("transit_days"),
        "eta": shipment["eta"],
        "required_by": shipment.get("required_by"),
        "slack_days": shipment["deadline_slack_days"],
    }


def initial_state() -> dict:
    """The 'before' board. Everything green, nothing decided yet.

    This is deliberately a separate, cheap call: the page must render instantly
    on load so the audience sees five calm green cards before anything happens.
    """
    routes = route_advisor.load_routes()
    shipments = route_advisor.load_shipments()
    return {
        "ran_at": None,
        "state": "idle",
        "risk": {"events": [], "sources": [], "stats": {}},
        "shipments": [
            dict(_shipment_card(s, routes), state="green", decision=None, drafts=[])
            for s in shipments
        ],
        "summary": {"reroute": 0, "hold": 0, "no-action": len(shipments), "drafts": 0},
        "notes": [],
    }


def run_cycle(*, live=True, inject=True, use_llm=True, verbose=False) -> dict:
    """The whole loop. Returns one object with everything the dashboard needs."""
    started = time.monotonic()
    notes = []
    routes = route_advisor.load_routes()

    # --- 1. Refresh risk -------------------------------------------------
    # Live sources are best-effort on purpose: a slow feed must never be the
    # reason a demo stalls in front of people.
    risk = risk_monitor.run(live=live, inject=inject, use_llm=use_llm, verbose=verbose)

    failed = [s for s in risk["sources"] if s["status"] == "failed"]
    attempted = [s for s in risk["sources"] if s["status"] != "skipped"]
    if failed and len(failed) == len(attempted) and attempted:
        notes.append(f"All {len(failed)} live sources were unreachable - "
                     "running on the injected scenario only.")
    elif failed:
        notes.append(f"{len(failed)} of {len(attempted)} live sources were unreachable; "
                     "the rest were read normally.")

    if use_llm and not llm.is_configured():
        notes.append("No AI provider configured - decisions and drafts came from the "
                     "deterministic fallbacks, not the model.")

    # --- 2. Decide, every shipment ---------------------------------------
    decisions = route_advisor.advise_all(use_llm=use_llm)

    # --- 3. Draft, only where something is being done --------------------
    drafts = comms_agent.draft_all(decisions, use_llm=use_llm)
    drafts_by_shipment: dict[str, list] = {}
    for draft in drafts:
        drafts_by_shipment.setdefault(draft["shipment_id"], []).append(draft)

    # --- 4. Assemble one object ------------------------------------------
    shipments = {s["id"]: s for s in route_advisor.load_shipments()}
    cards = []
    for decision in decisions:
        shipment = shipments[decision["shipment_id"]]
        card = _shipment_card(shipment, routes)
        recommended = routes.get(decision["recommended_route"], {})
        card.update({
            "state": STATE_FOR_DECISION.get(decision["decision"], "green"),
            "decision": dict(decision,
                             recommended_route_description=recommended.get("description"),
                             recommended_discharge_port=recommended.get("discharge_port"),
                             recommended_inland_leg=recommended.get("inland_leg")),
            "drafts": drafts_by_shipment.get(decision["shipment_id"], []),
        })
        cards.append(card)

    tally = {d: sum(1 for c in cards if c["decision"]["decision"] == d)
             for d in route_advisor.DECISIONS}

    return {
        "ran_at": _now_iso(),
        "state": "complete",
        "duration_seconds": round(time.monotonic() - started, 1),
        "risk": risk,
        "shipments": cards,
        "summary": dict(tally, drafts=len(drafts)),
        "notes": notes,
    }


def main():
    parser = argparse.ArgumentParser(description="Orchestrator (component 4).")
    parser.add_argument("--no-live", action="store_true", help="skip the live news pull")
    parser.add_argument("--no-inject", action="store_true", help="skip the scripted strike")
    parser.add_argument("--no-llm", action="store_true", help="use deterministic fallbacks")
    parser.add_argument("--json", action="store_true", help="print the whole result object")
    args = parser.parse_args()

    result = run_cycle(live=not args.no_live, inject=not args.no_inject,
                       use_llm=not args.no_llm, verbose=not args.json)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    print(f"\nCycle complete in {result['duration_seconds']}s")
    for note in result["notes"]:
        print(f"  note: {note}")
    print(f"\n  risk events: {len(result['risk']['events'])}")
    for event in result["risk"]["events"]:
        print(f"    [{event['origin']}] {event['chokepoint']} {event['type']}/"
              f"{event['severity']} [{event['source_language']}] {event['title'][:60]}")
    print()
    for card in result["shipments"]:
        print(f"  {card['state']:<9} {card['id']}  {card['cargo']:<28} "
              f"{card['decision']['headline'][:44]}")
    summary = result["summary"]
    print(f"\n  {summary['reroute']} reroute   {summary['hold']} hold   "
          f"{summary['no-action']} no-action   {summary['drafts']} drafts (none sent)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
