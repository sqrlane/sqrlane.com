"""tms.py - the TMS link. The system of record every agent works through.

Lanewatch is not a system of record and is not trying to become one. A
forwarder's bookings live in their TMS, and that is where the work has to land:
the agents read the book out of it, decide against those records, and put every
action they take back into it as a change a person approves.

So this module is both ends of the loop rather than a panel bolted to the side:

    read_bookings()    the book, read out of the TMS. Every other component
                       resolves back to this call - route_advisor, the
                       orchestrator, the roster and the simulation all get their
                       shipments from here, so there is exactly one door in.
    writebacks_for()   what one booking's cycle puts back: the routing change a
                       reroute implies, the status a hold implies, the risk
                       exception that explains either, and each drafted email
                       filed against the booking's communication log.
    connection()       the link itself - what synced, what is queued, which
                       agent wrote it, and the field mapping in both directions.

Every write-back names the **agent** that produced it, because that is the whole
claim: the Workers do not do their work beside the TMS, they do it *in* it. A
booking left on plan produces no write-back at all, which is a real answer
rather than an omission.

In this prototype the connector is a **demo** one and says so everywhere it is
surfaced. The read direction is genuinely the only door to the book - change
this file and the whole board changes - but the records behind it are the
synthetic pool. The write direction stops at a described change: there is no
client, no credential and no endpoint anywhere in this file, and a write-back is
a dict that stays a dict.

That is the same discipline the Comms Agent keeps for email, for the same
reason. Everything this system produces that leaves the building - an email, a
booking amendment, a quote, a TMS write - waits for a person.
"""

import json
from datetime import date, datetime, timedelta, timezone

from src import config

CONNECTOR_NAME = "TMS (demo connector)"
CONNECTOR_STATUS = "connected (demo)"

# Where this sits, in one line. The dashboard, the run payload and the roster all
# render this rather than each writing their own version of it.
POSITIONING = ("Lanewatch runs on top of the TMS the desk already uses. Bookings are read "
               "out of it, every decision the agents make is written back into it, and a "
               "person approves the write.")

HONESTY = ("Demo connector. No TMS is contacted and nothing is written - a write-back is a "
           "described change, held at the approval gate.")

# The agents, and the TMS record each one writes to. This is the mapping that
# makes "the Workers carry out the work through the TMS" concrete rather than a
# claim: every operation below is produced by one of these.
AGENT_RECORDS = [
    {"agent": "Risk Worker", "record": "exception",
     "writes": "The disruption that put the booking at risk, flagged on the booking"},
    {"agent": "Routing Worker", "record": "booking",
     "writes": "Discharge port, routing code, ETA - or the hold, when nothing better exists"},
    {"agent": "Comms Worker", "record": "communication_log",
     "writes": "Each drafted carrier and customer email, filed against the booking"},
]

# What a forwarder's TMS holds for a booking, where each field lands in this app,
# and - for the fields that move outward - which agent writes it. Authored to
# look like a real mapping table because that is the thing an ops lead
# recognises. Nothing is mapped at runtime; the read below is a JSON load.
FIELD_MAP = [
    {"tms_field": "booking_ref",        "lanewatch_field": "id",
     "direction": "in",   "written_by": None},
    {"tms_field": "commodity",          "lanewatch_field": "cargo",
     "direction": "in",   "written_by": None},
    {"tms_field": "port_of_loading",    "lanewatch_field": "origin",
     "direction": "in",   "written_by": None},
    {"tms_field": "port_of_discharge",  "lanewatch_field": "discharge_port",
     "direction": "both", "written_by": "Routing Worker"},
    {"tms_field": "routing_code",       "lanewatch_field": "primary_route",
     "direction": "both", "written_by": "Routing Worker"},
    {"tms_field": "eta",                "lanewatch_field": "eta",
     "direction": "both", "written_by": "Routing Worker"},
    {"tms_field": "booking_status",     "lanewatch_field": "state",
     "direction": "both", "written_by": "Routing Worker"},
    {"tms_field": "required_by",        "lanewatch_field": "required_by",
     "direction": "in",   "written_by": None},
    {"tms_field": "temperature_regime", "lanewatch_field": "cold_chain",
     "direction": "in",   "written_by": None},
    {"tms_field": "exception_flag",     "lanewatch_field": "triggering_events",
     "direction": "out",  "written_by": "Risk Worker"},
    {"tms_field": "communication_log",  "lanewatch_field": "drafts",
     "direction": "out",  "written_by": "Comms Worker"},
]


# ---------------------------------------------------------------------------
# The read side: the book comes out of the TMS
# ---------------------------------------------------------------------------


def _load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


# The bookings were authored to sit mid-voyage on a particular day. Left alone, a
# demo run months later shows cargo "in transit" with ETAs in the past, which is
# the first thing an audience notices. Rolling every date forward by the same
# whole number of weeks keeps the board plausible and leaves every relationship
# the screenplay depends on - slack, ordering, the gaps between bookings -
# exactly as authored. A real connector would not need this; a synthetic book
# does, and doing it here keeps it at the edge where the records come in.
DATE_FIELDS = ("etd", "eta", "required_by")


def shift_date(iso_date: str, days: int) -> str:
    """One date, moved by whole days. Bad input passes straight through."""
    try:
        return (date.fromisoformat(iso_date) + timedelta(days=days)).isoformat()
    except (ValueError, TypeError):
        return iso_date


def _weeks_since_authored(authored_on: str) -> int:
    """Whole weeks between the authoring date and today, never negative.

    Whole weeks rather than days so ETAs keep their weekday: cargo authored to
    arrive on a Tuesday still arrives on a Tuesday.
    """
    try:
        authored = date.fromisoformat(authored_on)
    except (ValueError, TypeError):
        return 0
    return max(0, (date.today() - authored).days // 7)


def read_bookings() -> list[dict]:
    """The book, read out of the TMS. The only door to it.

    Every component that needs shipments comes through here, so "the agents work
    on the TMS's records" is true of the code and not only of the pitch. Each
    record is stamped with where it came from, so a booking on screen can say
    which system it belongs to.
    """
    raw = _load_json(config.SHIPMENTS_FILE)
    bookings = raw["shipments"]
    shift = _weeks_since_authored(raw.get("_authored_on", "")) * 7
    synced_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    for booking in bookings:
        if shift:
            for field in DATE_FIELDS:
                if booking.get(field):
                    booking[field] = shift_date(booking[field], shift)
            booking["_dates_rolled_forward_days"] = shift
        # Provenance, on every record: this came from the system of record, and
        # the app is holding a copy of it rather than owning it.
        booking["source_system"] = CONNECTOR_NAME
        booking["record_status"] = "synced"
        booking["synced_at"] = synced_at
    return bookings


# ---------------------------------------------------------------------------
# The write side: every agent action, expressed as a change to a TMS record
# ---------------------------------------------------------------------------


def _gated(operation: dict) -> dict:
    """The gate, applied in one place so no operation can be added without it."""
    return dict(operation, status="QUEUED - not written",
                approval_status="awaiting_approval")


def _routing_writeback(card: dict) -> dict | None:
    """The booking change the Routing Worker's decision implies.

    Derived from the decision the Route Advisor actually made, so this reacts to
    the run rather than replaying a script. A booking left on plan produces no
    write-back at all.
    """
    decision = card.get("decision") or {}
    action = decision.get("decision")
    if action not in ("reroute", "hold"):
        return None

    changes = []
    if action == "reroute":
        if decision.get("recommended_discharge_port"):
            changes.append({"field": "port_of_discharge",
                            "from": card.get("discharge_port"),
                            "to": decision["recommended_discharge_port"]})
        if decision.get("recommended_route"):
            changes.append({"field": "routing_code",
                            "from": decision.get("route_before") or card.get("route_id"),
                            "to": decision["recommended_route"]})
        changes.append({"field": "booking_status",
                        "from": "ON PLAN", "to": "REROUTED - amendment pending"})
    else:
        changes.append({"field": "booking_status",
                        "from": "ON PLAN", "to": "HELD - awaiting berth"})
    if decision.get("revised_eta"):
        changes.append({"field": "eta",
                        "from": decision.get("original_eta") or card.get("eta"),
                        "to": decision["revised_eta"]})

    return _gated({
        "booking_ref": card["id"],
        "agent": "Routing Worker",
        "record": "booking",
        "operation": "update_booking" if action == "reroute" else "hold_booking",
        "action": action,
        "changes": changes,
        "reason": decision.get("headline", ""),
    })


def _exception_writeback(card: dict) -> dict | None:
    """The Risk Worker's finding, flagged on the booking it threatens.

    This is the write that makes the booking explain itself inside the TMS: the
    next person to open it sees which disruption moved it, without having to come
    back to this app for the reason.
    """
    decision = card.get("decision") or {}
    events = decision.get("triggering_events") or []
    if not events or decision.get("decision") not in ("reroute", "hold"):
        return None
    # Composed from the decision's own facts rather than sliced out of its
    # prose: a reason cut off at 180 characters reads as a bug on screen, and
    # this line has to stand on its own inside someone else's system.
    route = decision.get("route_before") or card.get("route_id") or "the booked route"
    reason = f"{route} is exposed to {', '.join(events)}."
    if decision.get("delay_days"):
        reason += (f" Revised ETA {decision.get('revised_eta')}, "
                   f"{decision['delay_days']} day"
                   f"{'' if decision['delay_days'] == 1 else 's'} later than booked.")
    return _gated({
        "booking_ref": card["id"],
        "agent": "Risk Worker",
        "record": "exception",
        "operation": "flag_exception",
        "action": "exception",
        "changes": [{"field": "exception_flag", "from": "none",
                     "to": ", ".join(events)}],
        "reason": reason,
    })


def _communication_writebacks(card: dict) -> list[dict]:
    """Each drafted email, filed against the booking's communication log.

    A forwarder's audit trail lives on the booking, not in a mailbox, so a draft
    that never reaches the TMS is a draft nobody will find later. It is still a
    draft: filing it and sending it are different things, and this system does
    neither until a person says so.
    """
    out = []
    for draft in card.get("drafts") or []:
        out.append(_gated({
            "booking_ref": card["id"],
            "agent": "Comms Worker",
            "record": "communication_log",
            "operation": "file_communication",
            "action": f"{draft.get('audience', 'draft')} email",
            # No "from": the communication log is appended to, not overwritten,
            # and a struck-through placeholder would imply something was replaced.
            "changes": [{"field": "communication_log",
                         "to": f"{draft.get('audience', 'draft')} draft to "
                               f"{draft.get('to', 'n/a')}"}],
            "reason": draft.get("subject", ""),
        }))
    return out


def writebacks_for(card: dict) -> list[dict]:
    """Every TMS operation one booking's cycle implies, in the order they happen.

    Risk flags the exception, Routing changes the booking, Comms files what was
    written about it. All three are the same kind of thing - a described change,
    queued behind a person - which is why they are built and gated in one place.
    """
    operations = [_exception_writeback(card), _routing_writeback(card)]
    return [op for op in operations if op] + _communication_writebacks(card)


def connection(board: list[dict]) -> dict:
    """The link: what synced in, what is queued to go back, and who wrote it."""
    operations = [op for card in board for op in writebacks_for(card)]
    by_agent: dict[str, int] = {}
    for op in operations:
        by_agent[op["agent"]] = by_agent.get(op["agent"], 0) + 1
    now = datetime.now(timezone.utc).replace(microsecond=0)

    return {
        "connector": CONNECTOR_NAME,
        "status": CONNECTOR_STATUS,
        "role": "System of record",
        "positioning": POSITIONING,
        # A demo connector has no real sync history, so this is stated relative to
        # the run rather than invented as a timestamp from nowhere.
        "last_sync": (now - timedelta(minutes=2)).isoformat(),
        "records_synced": len(board),
        "bookings_read": len(board),
        "bookings_affected": len({op["booking_ref"] for op in operations}),
        "direction_note": ("Bookings read in; routing, discharge port, ETA, booking status, "
                           "the risk exception and the communication log written back once "
                           "a person approves."),
        "field_map": FIELD_MAP,
        "agent_records": AGENT_RECORDS,
        # The dashboard and the tests both read "writebacks". Kept as the name.
        "writebacks": operations,
        "queued": len(operations),
        "queued_by_agent": by_agent,
        "honesty": HONESTY,
    }
