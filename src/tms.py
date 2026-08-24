"""tms.py - the demo TMS connection.

A forwarder's shipments live in a TMS, not in this app. The demo needs to show
what integration would look like without pretending one exists, so this module
models the connection and nothing more:

  * it names a **demo** connector, never a real vendor's product;
  * it reads the same synthetic shipments the rest of the demo uses;
  * it turns each actioned decision into a **write-back** - the booking change a
    reroute or hold would require - and leaves every one of them queued.

Nothing is written anywhere. There is no client, no credential, no endpoint: a
write-back is a dict describing a change, and it stays a dict. That is the same
discipline the Comms Agent keeps for email, for the same reason - the honest
design is that a person approves the change, and the demo should show the gate
rather than skip it.

The status is "connected (demo)" everywhere it is surfaced. Never present this
as a live TMS link.
"""

from datetime import datetime, timedelta, timezone

CONNECTOR_NAME = "TMS (demo connector)"

# What a forwarder's TMS actually holds for a booking, and where each field ends
# up in this app. Authored to look like a real mapping table because that is the
# thing an ops lead recognises - not because a mapping is running.
FIELD_MAP = [
    {"tms_field": "booking_ref",        "lanewatch_field": "id",                "direction": "in"},
    {"tms_field": "commodity",          "lanewatch_field": "cargo",             "direction": "in"},
    {"tms_field": "port_of_loading",    "lanewatch_field": "origin",            "direction": "in"},
    {"tms_field": "port_of_discharge",  "lanewatch_field": "discharge_port",    "direction": "both"},
    {"tms_field": "routing_code",       "lanewatch_field": "primary_route",     "direction": "both"},
    {"tms_field": "eta",                "lanewatch_field": "eta",               "direction": "both"},
    {"tms_field": "required_by",        "lanewatch_field": "required_by",       "direction": "in"},
    {"tms_field": "temperature_regime", "lanewatch_field": "cold_chain",        "direction": "in"},
]


def _writeback_for(card: dict) -> dict | None:
    """The booking change one decision implies, or None if nothing changes.

    Derived from the decision the Route Advisor actually made, so this reacts to
    the run rather than replaying a script. A shipment left on plan produces no
    write-back at all - that is a real answer, not an omission.
    """
    decision = card.get("decision") or {}
    action = decision.get("decision")
    if action not in ("reroute", "hold"):
        return None

    changes = []
    if action == "reroute":
        if decision.get("recommended_discharge_port"):
            changes.append({"field": "port_of_discharge",
                            "to": decision["recommended_discharge_port"]})
        if decision.get("recommended_route"):
            changes.append({"field": "routing_code", "to": decision["recommended_route"]})
    else:
        changes.append({"field": "booking_status", "to": "HELD - awaiting berth"})
    if decision.get("revised_eta"):
        changes.append({"field": "eta", "to": decision["revised_eta"]})

    return {
        "booking_ref": card["id"],
        "action": action,
        "changes": changes,
        "reason": decision.get("headline", ""),
        # The gate. Identical in spirit to a drafted email: a person approves it,
        # and even then this app has nothing to send it through.
        "status": "QUEUED - not written",
        "approval_status": "awaiting_approval",
    }


def connection(board: list[dict]) -> dict:
    """The connection panel: what is synced, what is queued, what it would change."""
    synced = len(board)
    writebacks = [w for w in (_writeback_for(c) for c in board) if w]
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return {
        "connector": CONNECTOR_NAME,
        "status": "connected (demo)",
        # A demo connector has no real sync history, so this is stated relative to
        # the run rather than invented as a timestamp from nowhere.
        "last_sync": (now - timedelta(minutes=2)).isoformat(),
        "records_synced": synced,
        "direction_note": ("Bookings read in; routing, discharge port and ETA written back "
                           "once a person approves."),
        "field_map": FIELD_MAP,
        "writebacks": writebacks,
        "queued": len(writebacks),
        "honesty": ("Demo connector. No TMS is contacted and nothing is written - "
                    "a write-back is a described change, held at the approval gate."),
    }
