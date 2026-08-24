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

from src import comms_agent, config, geo, llm, risk_monitor, roster, route_advisor, tms

# What the dashboard colours a card by.
STATE_FOR_DECISION = {"reroute": "rerouted", "hold": "hold", "no-action": "green"}

# The three agents, named. These are not new components - they are the three
# that have always existed, surfaced so the division of labour is visible.
# Every number a Worker reports is counted from the run that just happened;
# nothing here is illustrative.
WORKERS = [
    {"id": "risk", "name": "Risk Worker",
     "role": "Reads global news in several languages and tags what threatens a lane"},
    {"id": "routing", "name": "Routing Worker",
     "role": "Weighs schedule slack against added transit and expected delay, then decides"},
    {"id": "comms", "name": "Comms Worker",
     "role": "Drafts the carrier and customer emails. Sends nothing"},
]


def _idle_workers() -> list[dict]:
    live = [dict(w, mode="live", status="idle", summary="", detail=[], seconds=None)
            for w in WORKERS]
    # Scripted Workers are never "working" - they replay authored data - so they
    # sit at "ready" rather than borrowing the live Workers' status language.
    scripted = [dict(w, status="ready", summary="", detail=[], seconds=None) for w in roster.ROSTER]
    return live + scripted


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
    cards = [dict(_shipment_card(s, routes), state="green", decision=None, drafts=[])
             for s in shipments]
    return {
        "ran_at": None,
        "state": "idle",
        "workers": _idle_workers(),
        "scenario": None,
        "scenarios": [{k: sc[k] for k in ("id", "name", "kind", "summary",
                                          "decision_type", "expected")}
                      for sc in risk_monitor.load_scenarios()],
        "risk": {"events": [], "sources": [], "stats": {}},
        "shipments": cards,
        # The calm board on a map, with no risk on it yet - so the map is there
        # before the button is pressed rather than appearing with the disruption.
        "map": geo.build(cards, [], routes),
        "summary": {"reroute": 0, "hold": 0, "no-action": len(shipments), "drafts": 0},
        "notes": [],
    }


def run_cycle(*, live=True, inject=True, use_llm=True, verbose=False,
              scenario=None) -> dict:
    """The whole loop. Returns one object with everything the dashboard needs."""
    started = time.monotonic()
    notes = []
    routes = route_advisor.load_routes()
    workers = {w["id"]: dict(w, mode="live", status="idle", summary="", detail=[], seconds=None)
               for w in WORKERS}

    # --- 1. Refresh risk -------------------------------------------------
    # Live sources are best-effort on purpose: a slow feed must never be the
    # reason a demo stalls in front of people.
    stage_started = time.monotonic()
    risk = risk_monitor.run(live=live, inject=inject, use_llm=use_llm, verbose=verbose,
                            scenario=scenario)
    read = [s for s in risk["sources"] if s["status"] == "ok"]
    live_events = [e for e in risk["events"] if e.get("origin") == "live"]
    # How many events a regional source carried before the international wires.
    # That lead is the earliness claim, and it is counted from the run rather
    # than asserted in the script. It is reported as source proximity, never as
    # a language: the edge is reading close to the event, and that holds
    # wherever in the world the event happens.
    led_by_regional = 0
    for event in risk["events"]:
        first = next((t for t in event.get("language_trail", []) if t.get("first")), None)
        if first and first["language"] != "en":
            led_by_regional += 1

    total_events = len(risk["events"])
    workers["risk"].update(
        status="done", seconds=round(time.monotonic() - stage_started, 1),
        summary=(f"{risk['live_sources_read']} of {risk['live_sources_total']} "
                 f"sources read · "
                 f"{total_events} event{'' if total_events == 1 else 's'}"),
        detail=[d for d in [
            f"{len(live_events)} from live sources, "
            f"{total_events - len(live_events)} scripted",
            # Only worth saying when a live pull actually happened: offline runs
            # report a single placeholder source, and "drawn from 1 source
            # worldwide" would read as a claim rather than a debug mode.
            (f"drawn from {risk['live_sources_total']} sources worldwide"
             if risk["live_sources_total"] > 1 else None),
            f"a regional source was first on {led_by_regional} of "
            f"{total_events} event{'' if total_events == 1 else 's'}",
        ] if d])

    # Live sources only, for the same reason the counts above exclude the
    # scripted scenario: it always succeeds, so counting it here would make
    # "N of M were unreachable" disagree with the number on the board.
    live_entries = [s for s in risk["sources"] if not s["name"].startswith("scenario:")]
    failed = [s for s in live_entries if s["status"] == "failed"]
    attempted = [s for s in live_entries if s["status"] != "skipped"]
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
    stage_started = time.monotonic()
    decisions = route_advisor.advise_all(use_llm=use_llm)
    by_model = [d for d in decisions if d["decided_by"].startswith("llm")]
    tally_now = {d: sum(1 for x in decisions if x["decision"] == d)
                 for d in route_advisor.DECISIONS}
    workers["routing"].update(
        status="done", seconds=round(time.monotonic() - stage_started, 1),
        summary=(f"{len(decisions)} shipments triaged · {tally_now['reroute']} reroute, "
                 f"{tally_now['hold']} hold, {tally_now['no-action']} on plan"),
        detail=[f"{len(by_model)} decided by the model, "
                f"{len(decisions) - len(by_model)} by rules",
                f"{sum(1 for d in decisions if d.get('deadline_breached'))} "
                f"breaching a required-by date"])

    # --- 3. Draft, only where something is being done --------------------
    stage_started = time.monotonic()
    drafts = comms_agent.draft_all(decisions, use_llm=use_llm)
    templated = [d for d in drafts if d.get("fallback")]
    workers["comms"].update(
        status="done", seconds=round(time.monotonic() - stage_started, 1),
        summary=(f"{len(drafts)} drafts for "
                 f"{len({d['shipment_id'] for d in drafts})} shipments · none sent"),
        detail=[f"{len(drafts) - len(templated)} written by the model, "
                f"{len(templated)} from templates",
                "every draft awaiting human approval"])
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

    active_scenario = risk.get("scenario")
    for card in cards:
        shipment = shipments[card["id"]]
        card["roster"] = roster.build(shipment, card["decision"],
                                      (active_scenario or {}).get("id"), cards, active_scenario)

    tally = {d: sum(1 for c in cards if c["decision"]["decision"] == d)
             for d in route_advisor.DECISIONS}

    decided_by_model = sum(1 for c in cards if c["decision"]["decided_by"].startswith("llm"))
    drafted_by_model = sum(1 for c in cards for d in c["drafts"] if not d.get("fallback"))

    return {
        "ran_at": _now_iso(),
        "state": "complete",
        "duration_seconds": round(time.monotonic() - started, 1),
        "workers": [workers[w["id"]] for w in WORKERS] +
                   [dict(w, status="ready", summary="scripted — replays authored data",
                         detail=[], seconds=None) for w in roster.ROSTER],
        "scenario": active_scenario,
        "scenarios": [{k: sc[k] for k in ("id", "name", "kind", "summary",
                                          "decision_type", "expected")}
                      for sc in risk_monitor.load_scenarios()],
        # What actually ran this cycle, so the dashboard can show it rather than
        # asserting it. Counted from the run, never illustrative.
        "ai": {
            "provider": config.LLM_PROVIDER if llm.is_configured() else None,
            "model": llm.active_model() if llm.is_configured() else None,
            "model_source": llm.resolution_note(),
            "decisions_from_model": decided_by_model,
            "decisions_total": len(cards),
            "drafts_from_model": drafted_by_model,
            "drafts_total": sum(len(c["drafts"]) for c in cards),
        },
        "risk": risk,
        "shipments": cards,
        # The demo TMS connection, board-wide: what synced, and the booking
        # changes each decision implies. Every one stays queued - see tms.py.
        "tms": tms.connection(cards),
        # The board on a map: lanes drawn through what they actually transit,
        # and which chokepoints are carrying risk right now. Derived, not authored.
        "map": geo.build(cards, risk["events"], routes),
        "summary": dict(tally, drafts=len(drafts)),
        "notes": notes,
    }


def main():
    parser = argparse.ArgumentParser(description="Orchestrator (component 4).")
    parser.add_argument("--no-live", action="store_true", help="skip the live news pull")
    parser.add_argument("--no-inject", action="store_true", help="skip the scripted strike")
    parser.add_argument("--no-llm", action="store_true", help="use deterministic fallbacks")
    parser.add_argument("--scenario", help="hamburg, redsea, rhine or france")
    parser.add_argument("--json", action="store_true", help="print the whole result object")
    args = parser.parse_args()

    result = run_cycle(live=not args.no_live, inject=not args.no_inject,
                       use_llm=not args.no_llm, verbose=not args.json,
                       scenario=args.scenario)

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
