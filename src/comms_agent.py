"""comms_agent.py - component 3: the drafts a human would have had to write.

Given a shipment with an actioned decision, draft two emails:

    carrier   - a booking change or a hold instruction. Terse and operational.
    customer  - status and a revised ETA. Calm, human, honest about slippage.

The two voices are deliberately different, so each gets its own system prompt
and its own call. A carrier email is a transaction between operators. A customer
email is a relationship.

    THIS MODULE SENDS NOTHING.

There is no SMTP, no email library, no transport of any kind here, and there
will not be one. The agent drafts; a person reads, edits and sends. That is not
a limitation of the prototype - it is the responsible design, and it is worth
saying out loud during the demo.

Run it on its own:

    python -m src.comms_agent --inject            # full chain, draft everything
    python -m src.comms_agent --shipment SHP-002  # just the hold
    python -m src.comms_agent --inject --no-llm   # templates instead of the LLM
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone

from src import config, llm, route_advisor

AUDIENCES = ["carrier", "customer"]

# --- The two voices --------------------------------------------------------

CARRIER_SYSTEM = (
    "You write operational emails to ocean carrier booking desks on behalf of a "
    "freight forwarder. Booking desks process hundreds of these a day, so you are "
    "brief and unambiguous: what shipment, what you need, by when. You lead with the "
    "booking reference. You state the instruction as an instruction, not a question, "
    "while staying professional. You do not explain the geopolitics - the carrier is "
    "living the same disruption. No filler, no marketing language, no more than one "
    "line of courtesy."
)

CUSTOMER_SYSTEM = (
    "You write to a freight forwarder's customers on behalf of its operations team. "
    "Your reader is a logistics or supply-chain manager who needs to make their own "
    "decisions from what you tell them, so you lead with the date and what changed. "
    "You are calm and direct. You explain what happened and what you did about it in "
    "plain language, briefly. You never over-promise, you never hide slippage, and if "
    "a deadline is genuinely at risk you say so in the first two sentences and propose "
    "a next step. You write like a competent person who has already handled it, not "
    "like a form letter or an apology."
)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


def _shared_facts(decision: dict, shipment: dict) -> str:
    """The facts both emails are built from. Computed upstream, never invented here."""
    route_change = (
        f"{decision['route_before']} -> {decision['recommended_route']}"
        if decision["decision"] == "reroute" else
        f"stays on {decision['route_before']}"
    )
    deadline = (
        f"MISSES the customer's required-by date of {decision['required_by']}"
        if decision.get("deadline_breached") else
        f"still meets the customer's required-by date of {decision['required_by']}"
    )
    return f"""  Shipment:      {shipment['id']} - {shipment['cargo']}
  Detail:        {shipment.get('cargo_detail', 'n/a')}
  Booking ref:   {shipment.get('booking_ref', 'n/a')}
  Containers:    {shipment.get('container', 'n/a')}
  Carrier:       {shipment.get('carrier', 'n/a')}
  Lane:          {shipment['origin']} -> {shipment['final_destination']}
  Routing:       {route_change}
  Decision:      {decision['decision'].upper()}
  Why:           {decision['reasoning']}
  Original ETA:  {decision['original_eta']}
  Revised ETA:   {decision['revised_eta']} ({decision['delay_days']} days later)
  Deadline:      {deadline}
  Cold chain:    {'YES - ' + str(shipment.get('special_requirements')) if shipment.get('cold_chain') else 'no'}
  Special:       {shipment.get('special_requirements') or 'none'}"""


def _carrier_prompt(decision: dict, shipment: dict, routes: dict) -> str:
    if decision["decision"] == "reroute":
        old, new = routes[decision["route_before"]], routes[decision["recommended_route"]]
        ask = f"""WHAT YOU NEED FROM THEM
  Change the booking: discharge {new['discharge_port']} instead of
  {old['discharge_port']}, moving from {old['description']} to {new['description']}.
  Onward leg becomes {new['inland_leg']}.
  Ask them to confirm the amended booking and the revised discharge schedule."""
    else:
        ask = f"""WHAT YOU NEED FROM THEM
  Hold the cargo rather than discharging into the disruption. Ask them to confirm
  where the boxes will sit, that the reefer plugs stay powered if this is
  temperature-controlled cargo, and what the revised discharge window looks like.
  Ask them to flag any demurrage or storage exposure now rather than later."""

    return f"""Draft one email to the carrier's booking desk.

FACTS - use these exactly; do not invent vessel names, dates or reference numbers
{_shared_facts(decision, shipment)}

{ask}

RULES
  - Open with the booking reference so it can be matched instantly.
  - Six to twelve lines of body. Shorter is better.
  - Sign off as {config.FORWARDER['ops_contact']}, {config.FORWARDER['ops_title']},
    {config.FORWARDER['company']}. Use that name - never a placeholder in brackets.
  - Do not write [Your Name], [Date], or any other bracketed placeholder.

Return JSON: {{"subject": "...", "body": "..."}}
The body is plain text with real line breaks."""


def _customer_prompt(decision: dict, shipment: dict, routes: dict) -> str:
    if decision["decision"] == "reroute":
        situation = f"""WHAT TO TELL THEM
  Their cargo is being rerouted to avoid the disruption. Discharge moves to
  {routes[decision['recommended_route']]['discharge_port']} and comes onward by
  {routes[decision['recommended_route']]['inland_leg']}. This costs
  {decision['delay_days']} days against the original ETA - which is faster than
  waiting out the disruption. Give them the new date plainly."""
    else:
        situation = """WHAT TO TELL THEM
  Their cargo is being held rather than rerouted, because rerouting would land it
  later or in worse condition. Be explicit that this was a choice between two
  imperfect options and why holding is the better one. If the required-by date is
  now at risk, say so up front and offer a next step - a call, a partial release,
  or a revised plan."""

    return f"""Draft one email to the customer.

FACTS - use these exactly; do not invent dates, numbers or promises
{_shared_facts(decision, shipment)}
  Customer:      {shipment.get('customer')}
  Contact:       {shipment.get('customer_contact')}

{situation}

RULES
  - The revised ETA must appear in the first three lines.
  - Eight to fourteen lines of body.
  - No jargon the customer would not use themselves. "Chokepoint", "slack" and
    route codes like R-RTM-ALT are internal - say "Rotterdam" and "two days".
  - Do not apologise more than once, and never grovel.
  - Sign off as {config.FORWARDER['ops_contact']}, {config.FORWARDER['ops_title']},
    {config.FORWARDER['company']}, {config.FORWARDER['ops_email']}.
    Use that name - never a placeholder in brackets.
  - Do not write [Your Name], [Date], or any other bracketed placeholder.

Return JSON: {{"subject": "...", "body": "..."}}
The body is plain text with real line breaks."""


# ---------------------------------------------------------------------------
# Templated fallbacks - so a dead provider never blanks the screen
# ---------------------------------------------------------------------------


def _template_draft(audience: str, decision: dict, shipment: dict, routes: dict) -> dict:
    """Plain, honest, obviously-templated drafts. Clearly labelled as such."""
    signature = (f"\n\n{config.FORWARDER['ops_contact']}\n{config.FORWARDER['ops_title']}\n"
                 f"{config.FORWARDER['company']}\n{config.FORWARDER['ops_email']}")
    rerouting = decision["decision"] == "reroute"
    ports = port_names()
    new_code = routes[decision["recommended_route"]]["discharge_port"] if rerouting else None
    new_port = ports.get(new_code, new_code)
    old_port = ports.get(routes[decision["route_before"]]["discharge_port"])

    if audience == "carrier":
        subject = (f"{shipment.get('booking_ref')} - amend discharge to {new_code}"
                   if rerouting else
                   f"{shipment.get('booking_ref')} - hold instruction")
        if rerouting:
            action = (f"Please amend the booking to discharge at {new_code} instead of "
                      f"{routes[decision['route_before']]['discharge_port']}, and confirm "
                      f"the revised discharge schedule.")
        else:
            action = ("Please hold the containers rather than discharging into the current "
                      "disruption, and confirm where they will sit and the revised "
                      "discharge window.")
            if shipment.get("cold_chain"):
                action += ("\n\nThese are reefers: confirm the units stay powered "
                           "throughout and send us the temperature log for the hold "
                           "period. Flag any demurrage or storage exposure now.")
            else:
                action += "\n\nPlease flag any demurrage or storage exposure now."
        body = (f"Booking {shipment.get('booking_ref')} / {shipment.get('container')}\n"
                f"{shipment['origin']} - {shipment['final_destination']}, "
                f"{shipment.get('cargo_detail')}\n\n{action}\n\n"
                f"Revised ETA on our side is {decision['revised_eta']}.\n"
                f"Please confirm by return." + signature)
    else:
        # Note what is NOT here: decision['reasoning'] is written for an ops lead
        # and names route codes. The customer gets the same facts in their words.
        cargo_words = _plain_cargo(shipment["cargo"])
        subject = (f"{shipment.get('booking_ref')} {cargo_words} - "
                   f"revised ETA {decision['revised_eta']}")
        days = "day" if decision["delay_days"] == 1 else "days"
        if rerouting:
            action = (f"we are bringing it in through {new_port} instead of {old_port}, "
                      f"which puts arrival at {decision['revised_eta']} - "
                      f"{decision['delay_days']} {days} later than planned")
            because = (f"There is {_disruption_phrase(decision, ports)} that we expect to "
                       f"hold cargo there for several days. Routing through {new_port} costs "
                       f"less time than waiting for it to clear.")
        else:
            action = (f"we are holding it rather than rerouting, which puts arrival at "
                      f"{decision['revised_eta']}")
            because = (f"There is {_disruption_phrase(decision, ports)}, which we expect "
                       f"to clear in a few days. Bringing the cargo in through another port "
                       f"would mean extra road transit and additional handling, landing it "
                       f"later and in worse condition than waiting. Holding is the better "
                       f"of two imperfect options.")
            if shipment.get("cold_chain"):
                because += (" The units stay powered and in temperature range throughout, "
                            "and we have asked the carrier for the log covering the hold.")
        warning = ("\n\nThat is after your required-by date of "
                   f"{decision['required_by']}, so I would rather talk it through than "
                   "leave you to work around it - are you free tomorrow?"
                   if decision.get("deadline_breached") else
                   f"\n\nThat still sits inside your required-by date of "
                   f"{decision['required_by']}.")
        contact = (shipment.get("customer_contact") or "colleague").split(",")[0]
        body = (f"Dear {contact},\n\n"
                f"An update on your {cargo_words.lower()} shipment "
                f"{shipment.get('booking_ref')}: {action}.\n\n{because}{warning}\n\n"
                f"I will confirm as soon as the carrier comes back to us." + signature)

    return {"subject": subject, "body": body}


# ---------------------------------------------------------------------------
# Drafting
# ---------------------------------------------------------------------------

PLACEHOLDER = re.compile(r"\[[^\]\n]{2,40}\]")

# Internal vocabulary that must never reach a customer: route codes like
# R-RTM-ALT and chokepoint ids like HAM. Fine for the carrier, wrong for the
# customer - "Rotterdam" is what a person says.
ROUTE_CODE = re.compile(r"\bR-[A-Z]{3,5}-[A-Z]{3,4}\b")

# Models write typographic punctuation: a route code comes back as R\u2011HAM\u2011STD
# with non-breaking hyphens, not R-HAM-STD. Matching on ASCII alone let internal
# codes through a guard that reported nothing wrong, which is worse than having
# no guard at all. Normalise before matching.
_DASHES = str.maketrans({c: "-" for c in "\u2010\u2011\u2012\u2013\u2014\u2015\u2212\u00ad"})


def _normalise(text: str) -> str:
    return (text or "").translate(_DASHES)


def port_names() -> dict[str, str]:
    """Chokepoint id -> the word a customer would actually use."""
    with open(config.CHOKEPOINTS_FILE, encoding="utf-8") as handle:
        return {c["id"]: c.get("short_name", c["name"])
                for c in json.load(handle)["chokepoints"]}


def _find_internal_leaks(text: str, ports: dict) -> list[str]:
    """Catch internal codes in customer-facing text before a human sends it."""
    normalised = _normalise(text)
    leaks = set(ROUTE_CODE.findall(normalised))
    for code in ports:
        if re.search(rf"\b{code}\b", normalised):
            leaks.add(code)
    return sorted(leaks)


def _find_placeholders(text: str) -> list[str]:
    """Models like to leave [Your Name] behind. Catch it so a human is warned
    before that reaches a customer."""
    return sorted(set(PLACEHOLDER.findall(text or "")))


# What a customer would call each kind of disruption. The event type comes from
# the Risk Monitor, so a strike reads as a strike and low water reads as low water.
DISRUPTION_WORDS = {
    "strike": "industrial action",
    "congestion": "heavy congestion",
    "weather": "weather disruption",
    "geopolitical": "security disruption",
    "customs": "customs delays",
    "other": "disruption",
}


def _disruption_phrase(decision: dict, ports: dict) -> str:
    """'industrial action at Hamburg', built from the event that actually fired."""
    events = {e["event_id"]: e for e in route_advisor.load_risk_state().get("events", [])}
    triggering = [events[i] for i in decision.get("triggering_events", []) if i in events]
    if not triggering:
        return "disruption on the route"
    worst = max(triggering, key=lambda e: {"low": 1, "medium": 2, "high": 3}.get(e["severity"], 0))
    where = ports.get(worst.get("chokepoint"), worst.get("chokepoint", "the route"))
    return f"{DISRUPTION_WORDS.get(worst.get('type'), 'disruption')} at {where}"


def _plain_cargo(cargo: str) -> str:
    """'Refrigerated pharma (reefer)' -> 'refrigerated pharma'. The trade term in
    brackets is ours, not the customer's."""
    return re.sub(r"\s*\([^)]*\)", "", cargo or "").strip()


def _draft_warnings(audience: str, subject: str, body: str) -> list[str]:
    """Everything a human should fix before this is sent."""
    text = f"{subject}\n{body}"
    warnings = [f"unfilled placeholder {p}" for p in _find_placeholders(text)]
    if audience == "customer":
        warnings += [f"internal code {code!r} in customer-facing text"
                     for code in _find_internal_leaks(text, port_names())]
    return warnings


def _recipient(audience: str, shipment: dict) -> str:
    if audience == "carrier":
        return f"Booking Desk, {shipment.get('carrier', 'carrier')}"
    return f"{shipment.get('customer_contact', 'Contact')}, {shipment.get('customer', 'customer')}"


def draft_one(audience: str, decision: dict, shipment: dict, routes: dict,
              *, use_llm=True) -> dict:
    """One email. Never sent - returned as text for a human to read."""
    build_prompt = _carrier_prompt if audience == "carrier" else _customer_prompt
    system = CARRIER_SYSTEM if audience == "carrier" else CUSTOMER_SYSTEM
    fallback_reason = ""

    if use_llm and llm.is_configured():
        try:
            result = llm.complete_json(build_prompt(decision, shipment, routes),
                                       system=system,
                                       max_tokens=config.DRAFT_MAX_TOKENS)
            if isinstance(result, list) and result:
                result = result[0]
            subject = (result.get("subject") or "").strip()
            body = (result.get("body") or "").strip()
            if not subject or not body:
                raise llm.LLMError("provider returned an empty subject or body")
            drafted_by = f"llm ({llm.describe()})"
        except llm.LLMError as exc:
            result = _template_draft(audience, decision, shipment, routes)
            subject, body = result["subject"], result["body"]
            drafted_by = f"template (LLM unavailable: {exc})"
            fallback_reason = str(exc)[:160]
    else:
        result = _template_draft(audience, decision, shipment, routes)
        subject, body = result["subject"], result["body"]
        drafted_by = "template (--no-llm)" if use_llm is False else "template (no provider)"
        fallback_reason = "no AI provider configured" if use_llm else "requested without the model"

    return {
        "shipment_id": shipment["id"],
        "audience": audience,
        "to": _recipient(audience, shipment),
        "subject": subject,
        "body": body,
        # Said in the data, not just in the UI: nothing here has been sent.
        "status": "DRAFT - not sent",
        "warnings": _draft_warnings(audience, subject, body),
        # True when the model was meant to write this and could not, so the
        # dashboard can say so rather than passing a template off as authored.
        "fallback": drafted_by.startswith("template"),
        # Why the model did not write this one. Without it, a fallback is a
        # dead end on screen instead of something you can act on.
        "fallback_reason": fallback_reason,
        "drafted_by": drafted_by,
        "drafted_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


def draft_for(decision: dict, shipment: dict, routes: dict, *, use_llm=True) -> list[dict]:
    """Both emails for one actioned shipment. Returns [] for no-action."""
    if decision["decision"] == "no-action":
        return []
    return [draft_one(a, decision, shipment, routes, use_llm=use_llm) for a in AUDIENCES]


def draft_all(decisions: list[dict], *, use_llm=True) -> list[dict]:
    """Drafts for every actioned shipment in a set of decisions."""
    routes = route_advisor.load_routes()
    shipments = {s["id"]: s for s in route_advisor.load_shipments()}
    drafts = []
    for decision in decisions:
        shipment = shipments.get(decision["shipment_id"])
        if shipment:
            drafts.extend(draft_for(decision, shipment, routes, use_llm=use_llm))
    return drafts


# ---------------------------------------------------------------------------
# Terminal output
# ---------------------------------------------------------------------------


def print_drafts(drafts, decisions_by_id=None):
    if not drafts:
        print("\nNo actioned shipments, so nothing to draft. "
              "That is the correct output when nothing is wrong.\n")
        return

    print("\n" + "=" * 78)
    print("COMMS AGENT - DRAFTS ONLY.  NOTHING HERE HAS BEEN SENT.")
    print("=" * 78)

    current = None
    for draft in drafts:
        if draft["shipment_id"] != current:
            current = draft["shipment_id"]
            decision = (decisions_by_id or {}).get(current)
            heading = f"  {current}"
            if decision:
                heading += (f"  -  {decision['decision'].upper()}"
                            f"  (ETA {decision['original_eta']} -> {decision['revised_eta']})")
            print("\n" + "=" * 78 + f"\n{heading}\n" + "=" * 78)

        print(f"\n  ---------------- to the {draft['audience'].upper()} "
              + "-" * (44 - len(draft['audience'])))
        print(f"  To:      {draft['to']}")
        print(f"  Subject: {draft['subject']}")
        print(f"  Status:  {draft['status']}")
        print()
        for line in draft["body"].splitlines():
            print(f"    {line}")
        for warning in draft["warnings"]:
            print(f"\n  ! fix before sending: {warning}")
        print(f"\n  drafted by: {draft['drafted_by']}")

    print("\n" + "=" * 78)
    shipment_count = len({d["shipment_id"] for d in drafts})
    print(f"  {len(drafts)} drafts across {shipment_count} "
          f"{'shipment' if shipment_count == 1 else 'shipments'}. None sent.\n")


def main():
    parser = argparse.ArgumentParser(description="Comms Agent (component 3). Drafts only.")
    parser.add_argument("--inject", action="store_true",
                        help="load the scripted strike and re-run the Route Advisor first")
    parser.add_argument("--shipment", action="append", help="only this shipment id (repeatable)")
    parser.add_argument("--no-llm", action="store_true", help="use templates instead of the LLM")
    parser.add_argument("--json", action="store_true", help="print raw JSON instead")
    args = parser.parse_args()

    chatter = sys.stderr if args.json else sys.stdout

    if args.inject:
        from src import risk_monitor
        print("Loading the scripted Hamburg strike ...", file=chatter)
        risk_monitor.run(live=False, inject=True, verbose=False)

    only = set(args.shipment) if args.shipment else None
    print("Running the Route Advisor ...", file=chatter)
    decisions = route_advisor.advise_all(use_llm=not args.no_llm, only=only)

    actioned = [d for d in decisions if d["decision"] != "no-action"]
    print(f"{len(actioned)} of {len(decisions)} shipments need comms.", file=chatter)

    drafts = draft_all(decisions, use_llm=not args.no_llm)

    if args.json:
        print(json.dumps(drafts, indent=2, ensure_ascii=False))
    else:
        print_drafts(drafts, {d["shipment_id"]: d for d in decisions})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
