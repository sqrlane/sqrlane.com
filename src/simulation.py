"""simulation.py - replay an authored week over the same shipment pool.

The button runs one cycle: one set of active events, one set of decisions. That
shows the system working, but not the system *operating* - a disruption starting,
a second landing on top of it, a hold costing a day for every day it waits, and
the board climbing back once things clear.

This module runs that loop. It reads `data/simulation.json`, which says only which
authored events are active on which day, and steps through them:

  * events come from `scenarios.json` - never copied here, because a second copy
    of an event is exactly how schema parity has broken before;
  * every decision is made by the real Route Advisor, so the reasoning is genuine
    even though the timeline is not;
  * **state carries forward.** A shipment rerouted on Tuesday is *on* the new
    route on Wednesday, and is therefore no longer exposed to the thing that moved
    it. A held shipment accrues a day of delay for each day it waits, and keeps
    that delay when it resumes.

That last point is what makes this a simulation rather than eight independent
runs. It is also what makes the hold legible: holding is not free, and the week
shows exactly what it cost.

Nothing here sends, writes or files anything - it produces the same decision
objects the dashboard already renders.

    python -m src.simulation                # the whole week, deterministic
    python -m src.simulation --day 4        # stop after Thursday
    python -m src.simulation --llm          # let the model decide each day
"""

import argparse
import copy
import json
import sys
from datetime import datetime, timedelta

from src import config, risk_monitor, route_advisor

HELD = "held"
MOVING = "moving"


def load_timeline() -> dict:
    with open(config.DATA_DIR / "simulation.json", encoding="utf-8") as fh:
        return json.load(fh)


def _events_by_id() -> dict:
    """Every authored event, disabled scenarios included, keyed by id."""
    out = {}
    for scenario in risk_monitor.load_scenarios(include_disabled=True):
        for event in risk_monitor.load_injected_events(scenario["id"]):
            out[event["event_id"]] = event
    return out


def _add_days(iso: str, days: int) -> str:
    if not iso or not days:
        return iso
    return (datetime.fromisoformat(iso).date() + timedelta(days=days)).isoformat()


def _apply(shipment: dict, decision: dict) -> dict:
    """Carry the decision into the shipment, so tomorrow starts from today.

    Returns a short record of what actually changed, which is the thing worth
    printing - "rerouted" on its own does not say what moved.
    """
    verdict = decision.get("decision")
    change = {"moved": False, "held": False, "detail": None}

    if verdict == "reroute" and decision.get("recommended_route"):
        was = shipment["primary_route"]
        now = decision["recommended_route"]
        if now != was:
            shipment["primary_route"] = now
            # The route it just left is NOT put back on the list. Once a booking
            # has been moved it has moved - offering the old route again lets a
            # box ping-pong between two ports across consecutive days, which is
            # arithmetically defensible on each single day and nonsense across a
            # week. This is a simulation rule, not an advisor one: the advisor is
            # right that Hamburg-under-strike can beat Rotterdam-under-Red-Sea;
            # it just should never have been asked.
            shipment["alternates"] = [r for r in shipment.get("alternates", []) if r != now]
            shipment["_route_history"] = shipment.get("_route_history", []) + [was]
            shipment["eta"] = decision.get("revised_eta") or shipment["eta"]
            shipment["_state"] = MOVING
            change.update(moved=True, detail=f"{was} -> {now}")

    elif verdict == "hold":
        # Holding is not free: every day spent waiting is a day added to the ETA.
        shipment["_state"] = HELD
        shipment["_held_days"] = shipment.get("_held_days", 0) + 1
        shipment["eta"] = _add_days(shipment["eta"], 1)
        change.update(held=True, detail=f"day {shipment['_held_days']} of the hold")

    else:
        if shipment.get("_state") == HELD:
            # Whatever was blocking it has cleared.
            change["detail"] = (f"released after {shipment.get('_held_days', 0)} day(s), "
                                f"ETA {shipment['eta']}")
        shipment["_state"] = MOVING

    return change


def run(*, use_llm: bool = False, until_day: int | None = None, verbose: bool = True) -> dict:
    timeline = load_timeline()
    routes = route_advisor.load_routes()
    catalogue = _events_by_id()
    # A private copy: the simulation mutates shipments as the week runs, and must
    # not leave the loaded dataset changed for whatever runs next.
    shipments = copy.deepcopy(route_advisor.load_shipments())

    active: dict[str, dict] = {}
    days = []

    for step in timeline["days"]:
        if until_day and step["day"] > until_day:
            break

        for eid in step.get("activate", []):
            if eid in catalogue:
                active[eid] = catalogue[eid]
        for eid in step.get("resolve", []):
            active.pop(eid, None)

        events = list(active.values())
        cards, tally = [], {"reroute": 0, "hold": 0, "no-action": 0}

        for shipment in shipments:
            decision = route_advisor.advise(shipment, routes, events, use_llm=use_llm)
            change = _apply(shipment, decision)
            tally[decision.get("decision", "no-action")] += 1
            cards.append({
                "id": shipment["id"],
                "cargo": shipment["cargo"],
                "decision": decision.get("decision"),
                "headline": decision.get("headline"),
                "route": shipment["primary_route"],
                "eta": shipment["eta"],
                "state": shipment.get("_state", MOVING),
                "held_days": shipment.get("_held_days", 0),
                "changed": change,
                "decided_by": decision.get("decided_by"),
            })

        days.append({
            "day": step["day"],
            "label": step["label"],
            "headline": step["headline"],
            "note": step["note"],
            "active_events": [{"event_id": e["event_id"], "chokepoint": e["chokepoint"],
                               "type": e["type"], "severity": e["severity"],
                               "title": e["title"]} for e in events],
            "shipments": cards,
            "summary": tally,
            "actioned": tally["reroute"] + tally["hold"],
        })

        if verbose:
            _print_day(days[-1])

    result = {
        "name": timeline["name"],
        "summary": timeline["summary"],
        "origin": "scripted",
        "honesty": timeline["_honesty"],
        "days": days,
        "totals": _totals(days),
    }
    if verbose:
        _print_totals(result)
    return result


def _totals(days: list[dict]) -> dict:
    """Counted across the week, never estimated."""
    reroutes = sum(d["summary"]["reroute"] for d in days)
    holds = sum(d["summary"]["hold"] for d in days)
    moved = {c["id"] for d in days for c in d["shipments"] if c["changed"]["moved"]}
    held = {c["id"] for d in days for c in d["shipments"] if c["changed"]["held"]}
    hold_days = max((c["held_days"] for d in days for c in d["shipments"]), default=0)
    return {
        "days": len(days),
        "decisions": sum(sum(d["summary"].values()) for d in days),
        "reroute_decisions": reroutes,
        "hold_decisions": holds,
        "shipments_moved": len(moved),
        "shipments_held": len(held),
        "longest_hold_days": hold_days,
        "busiest_day": max(days, key=lambda d: d["actioned"])["label"] if days else None,
    }


def _print_day(day: dict) -> None:
    print(f"\n\033[1mDay {day['day']} · {day['label']} — {day['headline']}\033[0m")
    print(f"  {day['note']}")
    if day["active_events"]:
        for e in day["active_events"]:
            print(f"    active: {e['chokepoint']} {e['type']}/{e['severity']} — {e['title'][:58]}")
    else:
        print("    active: nothing")
    for c in day["shipments"]:
        if c["decision"] == "no-action" and not c["changed"]["detail"]:
            continue
        flag = "REROUTE" if c["changed"]["moved"] else "HOLD" if c["changed"]["held"] else "RESUME"
        print(f"    {flag:<8} {c['id']}  {c['changed']['detail'] or ''}  (ETA {c['eta']})")
    s = day["summary"]
    print(f"    → {s['reroute']} reroute · {s['hold']} hold · {s['no-action']} on plan")


def _print_totals(result: dict) -> None:
    t = result["totals"]
    print(f"\n\033[1mAcross {t['days']} days\033[0m")
    print(f"  {t['decisions']} decisions · {t['shipments_moved']} shipments moved · "
          f"{t['shipments_held']} held")
    print(f"  longest hold: {t['longest_hold_days']} day(s) · busiest day: {t['busiest_day']}")
    print(f"\n  {result['honesty']}\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Replay the authored week over the board.")
    ap.add_argument("--day", type=int, help="stop after this day")
    ap.add_argument("--llm", action="store_true", help="let the model decide (slow, many calls)")
    ap.add_argument("--json", action="store_true", help="print the result object instead")
    args = ap.parse_args()

    result = run(use_llm=args.llm, until_day=args.day, verbose=not args.json)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
