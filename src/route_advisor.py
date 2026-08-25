"""route_advisor.py - component 2: the decision layer.

Given one shipment and the current risk picture, decide: reroute, hold, or do
nothing - and say why in language an operations lead can act on.

The split of work matters:

    code decides the FACTS   - which chokepoints each candidate route touches,
                               what risk sits on them, how many days each option
                               adds, whether that fits the schedule slack.
    the LLM decides the CALL - weighing slack against added transit against
                               expected disruption delay, and explaining it.

Arithmetic and date maths stay in code because models are unreliable at both.
Judgement goes to the model because that is the part worth having.

Every decision carries a reasoning_trail: the ordered list of checks that were
run and what they found. That trail is the recorded reasoning the whole demo
rests on.

Run it on its own:

    python -m src.route_advisor --inject          # load the strike, advise all 5
    python -m src.route_advisor                   # use existing risk_state.json
    python -m src.route_advisor --shipment SHP-002
    python -m src.route_advisor --inject --no-llm # rules instead of the LLM
"""

import argparse
import json
import sys
from datetime import datetime, timezone

from src import config, llm, tms

DECISIONS = ["reroute", "hold", "no-action"]

# If an event carries no delay estimate (live classification may return null),
# fall back to a range implied by its severity.
SEVERITY_FALLBACK_DELAY = {"low": [0, 1], "medium": [1, 3], "high": [3, 5]}

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _days(n: int) -> str:
    """'1 day' / '2 days' - this text gets read aloud in the demo."""
    return f"{n} day" if n == 1 else f"{n} days"


def _load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_shipments() -> list[dict]:
    """The book, read out of the TMS.

    The advisor does not own the shipments and never reads the file itself: a
    forwarder's bookings live in their TMS, so they come in through the connector
    (src/tms.py) like everything else. That is one door, deliberately - the day
    the connector talks to a real TMS, every component on the board follows.
    """
    return tms.read_bookings()


def load_routes() -> dict[str, dict]:
    return {r["route_id"]: r for r in _load_json(config.ROUTES_FILE)["routes"]}


def load_risk_state() -> dict:
    """Read what the Risk Monitor last wrote. Missing file is not an error -
    it just means no risk is known yet."""
    try:
        return _load_json(config.RISK_STATE_FILE)
    except FileNotFoundError:
        return {"generated_at": None, "events": [], "sources": [], "stats": {}}


# ---------------------------------------------------------------------------
# Facts: cross-reference routes against active risk
# ---------------------------------------------------------------------------


def _delay_range(event) -> list[int]:
    delay = event.get("expected_delay_days")
    if isinstance(delay, (list, tuple)) and len(delay) == 2:
        return [int(delay[0]), int(delay[1])]
    return SEVERITY_FALLBACK_DELAY.get(event.get("severity", "low"), [0, 1])


def events_on_route(route: dict, events: list[dict]) -> list[dict]:
    """Which active events sit on any chokepoint this route passes through."""
    return [e for e in events if e.get("chokepoint") in route["chokepoints"]]


def _eur(n: int) -> str:
    return f"EUR {n:,.0f}"


def cost_of(candidate: dict, shipment: dict, primary: dict) -> dict:
    """What this option actually costs the customer, in money.

    The whole point of the exercise: a freight rate is not a cost. Three things
    are, and they are summed here rather than left for a person to hold in their
    head - the premium for taking the option at all, what every day past the
    required-by date costs, and the one-off cost of missing the date even once.

    Arithmetic only, as everywhere else in this file. Every input is an authored
    term on the booking; nothing here is estimated and no probability is applied.
    """
    terms = shipment.get("commercial") or {}
    freight = terms.get("freight_eur", 0)

    # The premium for taking this routing, from the relative index it is quoted in.
    freight_delta = round(freight * candidate["added_cost_index"] / 100)

    # Days past the deadline, not days of delay - slack is what absorbs the first
    # of them, and only what spills past it is billable to anyone.
    worst_delay = candidate["projected_delay_days"][1]
    days_late = max(0, worst_delay - shipment["deadline_slack_days"])

    delay_cost = days_late * terms.get("late_eur_per_day", 0)
    breach_cost = terms.get("breach_eur", 0) if days_late > 0 else 0

    # A changed discharge port means an extra handling. On a cold chain that is a
    # compliance event, so it is priced rather than described. Deterministic: it
    # applies when the port actually moves, and not otherwise.
    moves_port = candidate["discharge_port"] != primary["discharge_port"]
    transfer_cost = terms.get("transfer_risk_eur", 0) if (moves_port and shipment.get("cold_chain")) else 0

    return {
        "freight_delta_eur": freight_delta,
        "days_late": days_late,
        "delay_cost_eur": delay_cost,
        "breach_cost_eur": breach_cost,
        "transfer_cost_eur": transfer_cost,
        "exposure_eur": freight_delta + delay_cost + breach_cost + transfer_cost,
    }


def assess_route(route: dict, primary: dict, events: list[dict]) -> dict:
    """Everything measurable about one candidate route, versus the primary."""
    exposure = events_on_route(route, events)
    worst_case = max((_delay_range(e)[1] for e in exposure), default=0)
    best_case = max((_delay_range(e)[0] for e in exposure), default=0)
    added_transit = route["transit_days"] - primary["transit_days"]

    return {
        "route_id": route["route_id"],
        "description": route["description"],
        "discharge_port": route["discharge_port"],
        "inland_leg": route["inland_leg"],
        "transit_days": route["transit_days"],
        "chokepoints": route["chokepoints"],
        "added_transit_days": added_transit,
        "added_cost_index": route["cost_index"] - primary["cost_index"],
        "exposed_to": [
            {"event_id": e["event_id"], "chokepoint": e["chokepoint"], "type": e["type"],
             "severity": e["severity"], "delay_days": _delay_range(e), "title": e["title"]}
            for e in exposure
        ],
        "risk_delay_days": [best_case, worst_case],
        # What the customer actually feels: the detour plus whatever the risk costs.
        "projected_delay_days": [added_transit + best_case, added_transit + worst_case],
    }


def build_assessment(shipment: dict, routes: dict, events: list[dict]) -> dict:
    """Gather the facts and record the trail of checks that produced them."""
    primary = routes[shipment["primary_route"]]
    trail = []

    def note(check, finding):
        trail.append({"step": len(trail) + 1, "check": check, "finding": finding})

    note("Load shipment",
         f"{shipment['id']} {shipment['cargo']}, {shipment['origin']} -> "
         f"{shipment['final_destination']}, on {primary['route_id']} "
         f"({primary['transit_days']}d), ETA {shipment['eta']}, "
         f"{shipment['deadline_slack_days']}d slack.")

    note("Map current route to chokepoints",
         f"{primary['route_id']} passes {', '.join(primary['chokepoints'])}.")

    current = assess_route(primary, primary, events)
    current.update(cost_of(current, shipment, primary))
    if current["exposed_to"]:
        note("Cross-reference active risk",
             "Exposed: " + "; ".join(
                 f"{x['chokepoint']} {x['type']}/{x['severity']} "
                 f"({x['delay_days'][0]}-{x['delay_days'][1]}d)" for x in current["exposed_to"]))
    else:
        note("Cross-reference active risk",
             f"No active event touches {', '.join(primary['chokepoints'])}.")

    candidates = [current]
    for route_id in shipment.get("alternates", []):
        route = routes.get(route_id)
        if not route:
            note("Candidate route", f"{route_id} is not in routes.json - skipped.")
            continue
        assessment = assess_route(route, primary, events)
        assessment.update(cost_of(assessment, shipment, primary))
        candidates.append(assessment)
        exposure_note = (
            "also exposed to " + ", ".join(x["chokepoint"] for x in assessment["exposed_to"])
            if assessment["exposed_to"] else "no active risk on its chokepoints")
        note("Assess alternate",
             f"{route_id}: {assessment['added_transit_days']:+d}d transit, "
             f"{assessment['added_cost_index']:+d} cost index, "
             f"discharges {assessment['discharge_port']}, {exposure_note}.")
        note("Price the alternate",
             f"{route_id} exposure {_eur(assessment['exposure_eur'])} "
             f"= {_eur(assessment['freight_delta_eur'])} routing premium"
             + (f" + {assessment['days_late']}d late at "
                f"{_eur(assessment.get('delay_cost_eur', 0) // max(1, assessment['days_late']))}/day"
                if assessment["days_late"] else " + nothing late")
             + (f" + {_eur(assessment['breach_cost_eur'])} deadline breach"
                if assessment["breach_cost_eur"] else "")
             + (f" + {_eur(assessment['transfer_cost_eur'])} cold-chain transfer"
                if assessment["transfer_cost_eur"] else "") + ".")

    slack = shipment["deadline_slack_days"]
    worst = current["projected_delay_days"][1]
    note("Price staying put",
         f"Doing nothing exposes {_eur(current['exposure_eur'])}"
         + (f" - {current['days_late']}d past the required-by date."
            if current["days_late"] else " - the date still holds."))
    note("Compare against schedule slack",
         f"Staying put projects {current['projected_delay_days'][0]}-{worst}d of delay "
         f"against {slack}d of slack - "
         + ("deadline holds." if worst <= slack else "deadline breaks in the worst case."))

    # Routes the forwarder has not booked for this shipment. Not choosable, but
    # the advisor should be able to say why they are not the answer.
    other = [r for rid, r in routes.items()
             if rid != primary["route_id"] and rid not in shipment.get("alternates", [])]

    return {
        "shipment": shipment,
        "primary": primary,
        "current": current,
        "candidates": candidates,
        "other_network_routes": other,
        "slack_days": slack,
        "trail": trail,
    }


# ---------------------------------------------------------------------------
# The call: LLM
# ---------------------------------------------------------------------------

ADVISOR_SYSTEM = (
    "You are a senior freight-forwarding operations advisor at a mid-size European "
    "forwarder. You decide what to do with shipments when a disruption hits. You are "
    "measured and you do not cry wolf: if a shipment's schedule absorbs the delay, "
    "the right answer is to do nothing and keep watching. When there is no good "
    "option you say so plainly and recommend the least-bad one. You write for an "
    "operations lead who will act on your words, not for a report."
)


def _decision_prompt(assessment: dict) -> str:
    shipment = assessment["shipment"]
    current = assessment["current"]

    def render(candidate, label):
        lines = [
            f"  [{label}] {candidate['route_id']} - {candidate['description']}",
            f"      discharge {candidate['discharge_port']}, then {candidate['inland_leg']}",
            f"      {candidate['transit_days']}d transit "
            f"({candidate['added_transit_days']:+d}d vs current), "
            f"cost index {candidate['added_cost_index']:+d}",
        ]
        if candidate["exposed_to"]:
            for exposure in candidate["exposed_to"]:
                lines.append(f"      EXPOSED: {exposure['chokepoint']} {exposure['type']} "
                             f"severity {exposure['severity']}, "
                             f"{exposure['delay_days'][0]}-{exposure['delay_days'][1]}d delay "
                             f"- {exposure['title']}")
        else:
            lines.append("      no active risk on its chokepoints")
        low, high = candidate["projected_delay_days"]
        lines.append(f"      projected total delay: {low}-{high} days")
        bits = [f"{_eur(candidate['freight_delta_eur'])} routing premium"]
        if candidate["days_late"]:
            bits.append(f"{candidate['days_late']}d past the required-by date "
                        f"= {_eur(candidate['delay_cost_eur'])}")
        if candidate["breach_cost_eur"]:
            bits.append(f"{_eur(candidate['breach_cost_eur'])} deadline breach")
        if candidate["transfer_cost_eur"]:
            bits.append(f"{_eur(candidate['transfer_cost_eur'])} cold-chain transfer risk")
        lines.append(f"      COST OF THIS OPTION: {_eur(candidate['exposure_eur'])}  "
                     f"({'; '.join(bits)})")
        return "\n".join(lines)

    options = [render(current, "CURRENT ROUTE")]
    for candidate in assessment["candidates"][1:]:
        options.append(render(candidate, "ALTERNATE ON FILE"))

    others = "\n".join(
        f"  {r['route_id']} - {r['description']}, discharges {r['discharge_port']}, "
        f"{r['transit_days']}d" for r in assessment["other_network_routes"]) or "  (none)"

    cold_chain = ("YES - every transhipment or extra handling is a cold-chain break "
                  "risk and a compliance event" if shipment.get("cold_chain") else "no")

    selectable = [c["route_id"] for c in assessment["candidates"]]
    if len(selectable) == 1:
        choice_rule = (
            f"This shipment has NO alternate routing on file. The only route_id you "
            f"may return is {selectable[0]}, and your decision is therefore between "
            f"'hold' and 'no-action' - 'reroute' is not available to you. If holding "
            f"is wrong, say so in the reasoning, but do not name another route as the "
            f"recommendation.")
    else:
        choice_rule = (
            f"\"recommended_route\" MUST be exactly one of: {', '.join(selectable)}. "
            f"Any other route id will be refused and the recommendation discarded.")

    return f"""Decide what to do with this shipment.

SHIPMENT
  {shipment['id']}: {shipment['cargo']} ({shipment.get('cargo_detail', '')})
  {shipment['origin']} -> final destination {shipment['final_destination']}
  Customer: {shipment.get('customer', 'n/a')}
  Booked ETA {shipment['eta']}, customer needs it by {shipment.get('required_by', 'n/a')}
  Schedule slack: {_days(assessment['slack_days'])}
  Cold chain: {cold_chain}
  Special requirements: {shipment.get('special_requirements') or 'none'}

ROUTING OPTIONS - you may only recommend one of these
{chr(10).join(options)}

OTHER ROUTES IN THE NETWORK - context only; you may not recommend one.
These exist in the network but are not on this shipment's booking. If one is the
obvious question a manager would ask about, answer it on OPERATIONS, never on
paperwork: "it is not booked" is not a reason, because a booking can be changed.
What the detour would cost the cargo is the reason.
{others}

HOW TO DECIDE
  no-action - nothing touches this route, OR the projected delay fits inside the
              slack. Staying the course is a real answer; do not manufacture work.
  reroute   - an alternate on file gets the cargo in materially better than
              staying put, and its projected delay fits the slack. Name it.
  hold      - staying put breaks the deadline but no alternate is better. This is
              the "no good option" call: recommend holding and notifying, and be
              explicit about why each alternative would be worse.

Weigh four things against each other: the schedule slack, the transit days an
alternate adds, the delay the disruption is expected to cause, and COST OF THIS
OPTION. For a shipment whose final destination IS the disrupted port, remember
that rerouting elsewhere adds road transit and extra handling on top of the
detour.

The cost line is the one that settles most of these, and it is already computed
for you - do not recalculate it, quote it. It is not the freight rate: it is the
routing premium plus what being late actually costs this customer. A cheaper
routing that lands late is usually the expensive option, and a premium worth
paying is one smaller than the delay it avoids. Say which is which in euros.
If the cheapest option is also the latest, name the trade explicitly rather than
letting the number decide silently.

HARD CONSTRAINT
{choice_rule}

Return one JSON object:
  "decision": one of {DECISIONS}
  "recommended_route": route_id if rerouting, otherwise the current route id
  "notify_customer": true if the customer should be told now
  "confidence": 0.0 to 1.0
  "headline": one short line, at most 12 words, that an ops lead could scan
  "reasoning": 2 to 4 sentences of plain English. Cite the actual numbers -
      the days of slack, the days added, the expected disruption delay. This is
      read aloud to explain the call, so make it read like a person wrote it.
  "rejected_options": array of {{"route_id": "...", "why_not": "one sentence"}}
      for every option you seriously considered and did not pick. Give the
      OPERATIONAL consequence: days added, a chokepoint the route still hits,
      extra handling, a cold-chain transfer, a road leg because the discharge
      port is not the destination. Never reject a route for not being booked -
      that reads as an excuse rather than judgement. Include the current route
      only if you are rerouting away from it."""


def decide_with_llm(assessment: dict) -> dict:
    verdict = llm.complete_json(_decision_prompt(assessment),
                                system=ADVISOR_SYSTEM,
                                max_tokens=config.DECISION_MAX_TOKENS)
    if isinstance(verdict, list) and verdict:
        verdict = verdict[0]
    return verdict


def decide_with_rules(assessment: dict) -> dict:
    """Transparent fallback when no LLM is available.

    Same shape of answer, visibly labelled, so the pipeline can be exercised
    without a key - and so a flaky provider never takes the demo down. It picks
    defensibly but it does not explain like the model does.
    """
    slack = assessment["slack_days"]
    current = assessment["current"]
    staying_worst = current["projected_delay_days"][1]

    rejected = []
    if not current["exposed_to"]:
        decision, route, notify = "no-action", current["route_id"], False
        headline = "No active risk on this route"
        reasoning = (f"No active disruption touches "
                     f"{', '.join(current['chokepoints'])}, so {assessment['shipment']['id']} "
                     f"stays on {current['route_id']} and keeps its "
                     f"{assessment['shipment']['eta']} ETA.")
    elif staying_worst <= slack:
        decision, route, notify = "no-action", current["route_id"], False
        headline = f"Delay of up to {staying_worst}d fits {slack}d of slack"
        reasoning = (f"The disruption projects up to {_days(staying_worst)} of delay and the "
                     f"shipment carries {_days(slack)} of slack, so the deadline still holds. "
                     f"Hold course and keep watching.")
    else:
        # Staying put breaks the deadline. Two things can justify a reroute: an
        # alternate that lands inside the slack, or one that lands materially
        # sooner than staying even though it misses too. The second case is the
        # one that matters under a closed chokepoint, where every option is late
        # and the job is to pick the least-late - arriving eleven days behind
        # beats arriving fourteen.
        MATERIAL_GAIN_DAYS = 2
        alternates = assessment["candidates"][1:]
        viable = [c for c in alternates
                  if c["projected_delay_days"][1] <= slack
                  or c["projected_delay_days"][1] <= staying_worst - MATERIAL_GAIN_DAYS]

        # A reroute has to be worth what it costs. Landing sooner is not the same
        # as being better off: a Cape routing that arrives nine days late at a
        # thirty-point premium can cost more than absorbing the delay where it
        # is. Anything that does not beat staying put in money is not an option,
        # it is a more expensive way to be late.
        stay_exposure = current["exposure_eur"]
        priced_out = [c for c in viable if c["exposure_eur"] >= stay_exposure]
        viable = [c for c in viable if c["exposure_eur"] < stay_exposure]

        # Money first, days to break ties - the inversion is the point. Ranking
        # by days and breaking ties on a relative index answers "which is
        # soonest", which is not the question anyone is actually asking.
        viable.sort(key=lambda c: (c["exposure_eur"], c["projected_delay_days"][1]))
        for candidate in assessment["candidates"][1:]:
            if candidate not in viable[:1]:
                if candidate["exposed_to"]:
                    hit = ", ".join(sorted({x["chokepoint"] for x in candidate["exposed_to"]}))
                    why = (f"adds {_days(candidate['added_transit_days'])} and still runs "
                           f"through {hit}, so it projects "
                           f"{candidate['projected_delay_days'][1]}d against "
                           f"{_days(slack)} of slack")
                elif candidate in priced_out:
                    why = (f"lands {candidate['projected_delay_days'][1]}d out and costs "
                           f"{_eur(candidate['exposure_eur'])} against "
                           f"{_eur(stay_exposure)} for staying put - a more expensive "
                           f"way to be late")
                else:
                    why = (f"projects {candidate['projected_delay_days'][1]}d of delay "
                           f"against {_days(slack)} of slack")
                rejected.append({"route_id": candidate["route_id"], "why_not": why})
        if viable:
            best = viable[0]
            decision, route, notify = "reroute", best["route_id"], True
            headline = (f"Reroute via {best['discharge_port']} - "
                        f"{best['added_transit_days']:+d}d, inside {slack}d slack"
                        if best["projected_delay_days"][1] <= slack else
                        f"Reroute via {best['discharge_port']} - least-late option "
                        f"({best['projected_delay_days'][1]}d vs {staying_worst}d)")
            fits = best["projected_delay_days"][1] <= slack
            if fits:
                reasoning = (f"Staying on {current['route_id']} projects up to "
                             f"{_days(staying_worst)} of delay against {_days(slack)} of slack, "
                             f"which breaks the deadline. {best['route_id']} adds "
                             f"{_days(best['added_transit_days'])} of transit and carries no "
                             f"active risk, so it lands inside the slack.")
            else:
                # Everything is late. Say so plainly rather than implying a save.
                reasoning = (f"Every option is late. Staying on {current['route_id']} projects up "
                             f"to {_days(staying_worst)} of delay; {best['route_id']} projects "
                             f"{_days(best['projected_delay_days'][1])} and avoids the disruption "
                             f"outright. It still misses the {slack}-day window, but it is the "
                             f"least-late option and the arrival is far more certain.")
            rejected.append({"route_id": current["route_id"],
                             "why_not": f"projects up to {staying_worst}d of delay "
                                        f"against {slack}d of slack"})
        else:
            decision, route, notify = "hold", current["route_id"], True
            headline = "No better option - hold and notify"
            if not assessment["candidates"][1:]:
                # Nothing booked as an alternate, but a manager will still ask
                # about the obvious other ports. Answer it before they ask.
                destination = assessment["shipment"]["final_destination"]
                elsewhere = sorted({r["discharge_port"] for r in assessment["other_network_routes"]
                                    if r["discharge_port"] != current["discharge_port"]})
                if elsewhere:
                    rejected.append({
                        "route_id": "no alternate booked",
                        "why_not": (f"discharging at {' or '.join(elsewhere)} instead would add "
                                    f"road transit to {destination} and extra handling"
                                    + (", and a cold-chain transfer"
                                       if assessment["shipment"].get("cold_chain") else "")
                                    + " on top of the detour"),
                    })
            reasoning = (f"Staying put projects up to {_days(staying_worst)} of delay against "
                         f"{_days(slack)} of slack, but no alternate on file lands any better. "
                         f"Hold and tell the customer now.")

    return {"decision": decision, "recommended_route": route, "notify_customer": notify,
            "confidence": 0.4, "headline": headline,
            "reasoning": reasoning,
            "rejected_options": rejected}


# ---------------------------------------------------------------------------
# Put it together
# ---------------------------------------------------------------------------


def _projected_delay(assessment, decision, route_id) -> int:
    """Worst-case days late, computed in code rather than asked of the model."""
    lookup = {c["route_id"]: c for c in assessment["candidates"]}
    if decision == "reroute" and route_id in lookup:
        return max(0, lookup[route_id]["projected_delay_days"][1])
    if decision == "hold":
        return max(0, assessment["current"]["projected_delay_days"][1])
    return 0


def _shift_date(iso_date: str, days: int) -> str:
    """One date, moved by whole days. Defined once, at the TMS edge."""
    return tms.shift_date(iso_date, days)


def advise(shipment: dict, routes: dict, events: list[dict], *, use_llm=True) -> dict:
    """One shipment in, one recorded decision out."""
    assessment = build_assessment(shipment, routes, events)
    trail = assessment["trail"]

    valid_routes = {c["route_id"] for c in assessment["candidates"]}

    # Short-circuit: if no active event touches any chokepoint on the current
    # route, there is genuinely nothing to weigh. Saying so is a real answer,
    # and it costs no LLM call.
    if not assessment["current"]["exposed_to"]:
        verdict = decide_with_rules(assessment)
        decided_by = "rule (no risk on this route - no LLM call needed)"
    elif use_llm and llm.is_configured():
        try:
            verdict = decide_with_llm(assessment)
            decided_by = f"llm ({llm.describe()})"
        except llm.LLMError as exc:
            trail.append({"step": len(trail) + 1, "check": "LLM decision",
                          "finding": f"Provider failed ({exc}) - fell back to rules."})
            verdict = decide_with_rules(assessment)
            decided_by = "rule (LLM unavailable)"
    else:
        verdict = decide_with_rules(assessment)
        decided_by = "rule (--no-llm)"

    decision = verdict.get("decision")
    if decision not in DECISIONS:
        decision = "no-action"
    route_id = verdict.get("recommended_route")
    if decision == "reroute" and route_id not in valid_routes:
        # The model named a route it was not offered: refuse the reroute rather
        # than book something that does not exist.
        trail.append({"step": len(trail) + 1, "check": "Validate recommendation",
                      "finding": f"Recommended route {route_id!r} is not a candidate "
                                 f"for this shipment - decision downgraded to hold."})
        decision, route_id = "hold", assessment["primary"]["route_id"]
        # The headline, reasoning and rejected options were all written to argue
        # for a reroute. Keeping them next to a hold puts a self-contradicting
        # card on screen and feeds the Comms Agent contradictory facts. Rebuild
        # the narrative to match the decision that actually stands.
        verdict = decide_with_rules(assessment)
        decision, route_id = "hold", assessment["primary"]["route_id"]
        decided_by = "rule (model named an unavailable route)"
    if route_id not in valid_routes:
        route_id = assessment["primary"]["route_id"]

    # On a hold the current route is the one being kept, so listing it under
    # "considered and rejected" contradicts the decision on screen.
    rejected = verdict.get("rejected_options") or []
    if decision != "reroute":
        rejected = [r for r in rejected
                    if isinstance(r, dict)
                    and r.get("route_id") != assessment["primary"]["route_id"]]

    delay_days = _projected_delay(assessment, decision, route_id)
    revised_eta = _shift_date(shipment["eta"], delay_days)

    trail.append({"step": len(trail) + 1, "check": "Decision",
                  "finding": f"{decision.upper()}"
                             + (f" to {route_id}" if decision == "reroute" else "")
                             + f" - decided by {decided_by}."})
    if delay_days:
        trail.append({"step": len(trail) + 1, "check": "Revised ETA",
                      "finding": f"{shipment['eta']} + {delay_days}d = {revised_eta} "
                                 f"(customer needs it by "
                                 f"{shipment.get('required_by', 'n/a')})."})

    return {
        "shipment_id": shipment["id"],
        "cargo": shipment["cargo"],
        "customer": shipment.get("customer"),
        "route_before": assessment["primary"]["route_id"],
        "decision": decision,
        "recommended_route": route_id,
        "notify_customer": bool(verdict.get("notify_customer", decision != "no-action")),
        "headline": verdict.get("headline", ""),
        "reasoning": verdict.get("reasoning", ""),
        "rejected_options": rejected,
        "confidence": verdict.get("confidence", 0.5),
        "original_eta": shipment["eta"],
        "revised_eta": revised_eta,
        "delay_days": delay_days,
        "required_by": shipment.get("required_by"),
        "deadline_breached": (revised_eta > shipment["required_by"]
                              if shipment.get("required_by") else False),
        "slack_days": assessment["slack_days"],
        "triggering_events": [e["event_id"] for e in assessment["current"]["exposed_to"]],
        "reasoning_trail": trail,
        "decided_by": decided_by,
        # True only when the model was supposed to decide and could not. The
        # no-risk short-circuit is a rule by design, so it is not a fallback.
        "fallback": decided_by.startswith("rule (") and "no risk on this route" not in decided_by,
        "decided_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


def advise_all(*, use_llm=True, only=None) -> list[dict]:
    routes = load_routes()
    events = load_risk_state().get("events", [])
    shipments = [s for s in load_shipments() if only is None or s["id"] in only]
    return [advise(s, routes, events, use_llm=use_llm) for s in shipments]


# ---------------------------------------------------------------------------
# Terminal output
# ---------------------------------------------------------------------------

BADGE = {"reroute": "REROUTE ", "hold": "HOLD    ", "no-action": "NO ACTION"}


def print_decisions(decisions, *, show_trail=True):
    print("\n" + "=" * 78)
    print("ROUTE ADVISOR")
    print("=" * 78)

    for decision in decisions:
        print("\n" + "-" * 78)
        route_note = (f"{decision['route_before']} -> {decision['recommended_route']}"
                      if decision["decision"] == "reroute" else decision["route_before"])
        print(f"  {BADGE[decision['decision']]}  {decision['shipment_id']}  "
              f"{decision['cargo']}  ({route_note})")
        print(f"  {decision['headline']}")
        print()
        for line in _wrap(decision["reasoning"], 74):
            print(f"    {line}")

        if decision["rejected_options"]:
            print("\n    Considered and rejected:")
            for option in decision["rejected_options"]:
                for index, line in enumerate(_wrap(
                        f"{option.get('route_id', '?')}: {option.get('why_not', '')}", 68)):
                    print(f"      {'- ' if index == 0 else '  '}{line}")

        if decision["delay_days"]:
            flag = "  BREACHES DEADLINE" if decision["deadline_breached"] else "  within deadline"
            print(f"\n    ETA {decision['original_eta']} -> {decision['revised_eta']} "
                  f"(+{decision['delay_days']}d, needs {decision['required_by']}){flag}")
        else:
            print(f"\n    ETA {decision['original_eta']} unchanged")

        if show_trail:
            print("\n    Reasoning trail:")
            for step in decision["reasoning_trail"]:
                for index, line in enumerate(_wrap(
                        f"{step['check']}: {step['finding']}", 66)):
                    print(f"      {str(step['step']) + '.' if index == 0 else '  '} {line}"
                          if index == 0 else f"         {line}")
        print(f"\n    decided by: {decision['decided_by']}  "
              f"confidence {decision['confidence']}")

    print("\n" + "-" * 78)
    tally = {d: sum(1 for x in decisions if x["decision"] == d) for d in DECISIONS}
    print(f"  {tally['reroute']} reroute   {tally['hold']} hold   "
          f"{tally['no-action']} no-action\n")


def _wrap(text, width):
    words, lines, line = (text or "").split(), [], ""
    for word in words:
        if len(line) + len(word) + 1 > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines or [""]


def main():
    parser = argparse.ArgumentParser(description="Route Advisor (component 2).")
    parser.add_argument("--inject", action="store_true",
                        help="load the scripted Hamburg strike into risk_state.json first")
    parser.add_argument("--shipment", action="append",
                        help="only advise this shipment id (repeatable)")
    parser.add_argument("--no-llm", action="store_true",
                        help="use the rule-based fallback instead of the LLM")
    parser.add_argument("--no-trail", action="store_true", help="hide the reasoning trail")
    parser.add_argument("--json", action="store_true", help="print raw JSON instead")
    args = parser.parse_args()

    # With --json, stdout must be nothing but JSON so the output can be piped.
    chatter = sys.stderr if args.json else sys.stdout

    if args.inject:
        from src import risk_monitor
        print("Loading the scripted Hamburg strike into risk_state.json ...", file=chatter)
        risk_monitor.run(live=False, inject=True, verbose=False)

    state = load_risk_state()
    events = state.get("events", [])
    if not events:
        print("\nNo active risk events in risk_state.json.", file=chatter)
        print("Run:  python -m src.route_advisor --inject\n", file=chatter)
    else:
        print("\nActive risk: " + ", ".join(
            f"{e['chokepoint']}/{e['type']}/{e['severity']}" for e in events), file=chatter)

    decisions = advise_all(use_llm=not args.no_llm, only=set(args.shipment) if args.shipment else None)

    if args.json:
        print(json.dumps(decisions, indent=2, ensure_ascii=False))
    else:
        print_decisions(decisions, show_trail=not args.no_trail)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
