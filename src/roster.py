"""roster.py - the scripted half of the Worker roster.

Risk, Routing and Comms are real: they run live and their output is whatever the
model and the news actually produced. The four Workers here are **not**. They
replay authored data so the product surface looks complete, and every one of
them is tagged SCRIPTED on screen.

They are still reactive, which is the point: each panel is built from the
scenario that is active and the shipment that is selected, so switching either
visibly changes what they show. What is authored is the *content* - rate cards,
milestones, document fields, canned answers - not the shape of the response.

The honesty rule this file exists to keep: never present one of these as doing
live AI reasoning. `mode` is "scripted" on all four, and the dashboard renders
that tag from this data rather than hard-coding it.
"""

from datetime import date, timedelta

from src import route_advisor, tms

ROSTER = [
    {"id": "rate", "name": "Rate Worker", "mode": "scripted",
     "role": "Quote and rate lookups across the carriers on a lane"},
    {"id": "milestones", "name": "Milestones Worker", "mode": "scripted",
     "role": "Milestones and position for a booking"},
    {"id": "docs", "name": "Docs Worker", "mode": "scripted",
     "role": "Field extraction from bills of lading and invoices"},
    {"id": "inbox", "name": "Inbox Worker", "mode": "scripted",
     "role": "Triages inbound carrier and customer mail, and drafts the reply"},
    {"id": "rfq", "name": "RFQ Worker", "mode": "scripted",
     "role": "Reads an inbound rate request and drafts the quote back"},
    {"id": "booking", "name": "Booking Worker", "mode": "scripted",
     "role": "Holds the carrier booking, and the amendment a decision requires"},
    {"id": "invoice", "name": "Invoice Worker", "mode": "scripted",
     "role": "Reconciles the carrier invoice against the rate that was agreed"},
    {"id": "customs", "name": "Customs Worker", "mode": "scripted",
     "role": "Checks the entry for the discharge country, and escalates what needs a person"},
    {"id": "tms", "name": "TMS Link", "mode": "scripted",
     "role": "Booking sync, and the write-back a decision implies"},
    {"id": "assistant", "name": "Assistant", "mode": "scripted",
     "role": "Answers questions about what is on the board"},
]

# Authored per lane. Relative cost indices, in the same 100 = baseline units the
# routes use - not currency, and not a claim about real market rates.
_CARRIERS = {
    "R-HAM-STD":   [("Hapag-Lloyd", 100), ("Maersk", 104), ("ONE", 98)],
    "R-RTM-ALT":   [("Maersk", 108), ("MSC", 106), ("Hapag-Lloyd", 111)],
    "R-RTM-STD":   [("CMA CGM", 100), ("MSC", 97), ("Maersk", 103)],
    "R-ANR-STD":   [("MSC", 100), ("CMA CGM", 102), ("ONE", 99)],
    "R-RTM-RHINE": [("CMA CGM", 100), ("Contargo barge", 96), ("Rhenus", 101)],
    "R-RTM-RAIL":  [("CMA CGM + rail", 114), ("Hupac intermodal", 112), ("Road haulage", 121)],
    "R-FOS-STD":   [("MSC", 100), ("CMA CGM", 103), ("Marfret", 98)],
    "R-ANR-LYON":  [("MSC + road", 118), ("CMA CGM + road", 120)],
    "R-COGH-ALT":  [("Hapag-Lloyd", 130), ("Maersk", 133)],
    "R-COGH-RTM":  [("CMA CGM", 128), ("MSC", 131)],
    "R-COGH-ANR":  [("MSC", 128), ("CMA CGM", 130)],
    "R-COGH-BSL":  [("CMA CGM + rail", 134), ("Rhenus", 137)],
    "R-COGH-FOS":  [("MSC", 132), ("Marfret", 135)],
}

# What each disruption does to a quote. Authored, and labelled as such.
_SURCHARGE = {
    "hamburg": ("Port disruption surcharge", 6, "terminal congestion recovery at Hamburg"),
    "redsea":  ("Contingency / war-risk surcharge", 22, "Cape routing and war-risk premium"),
    "rhine":   ("Low-water surcharge", 14, "part-loaded barges on the Rhine"),
    "france":  ("Inland diversion surcharge", 9, "road detour around the closed corridor"),
}

_DOCS = {
    "SHP-001": {"doc": "Bill of lading HLCU-2261188", "hs": "8708.30", "incoterm": "FCA Shanghai",
                "gross_kg": "18,400", "packages": "12 containers"},
    "SHP-002": {"doc": "Bill of lading MAEU-9930472", "hs": "3002.20", "incoterm": "CIP Hamburg",
                "gross_kg": "5,120", "packages": "2 reefer containers"},
    "SHP-003": {"doc": "Bill of lading CMDU-4410765", "hs": "9403.60", "incoterm": "FOB Shanghai",
                "gross_kg": "11,900", "packages": "8 containers"},
    "SHP-004": {"doc": "Bill of lading MEDU-1774390", "hs": "8528.72", "incoterm": "CIF Antwerp",
                "gross_kg": "7,650", "packages": "5 containers"},
    "SHP-005": {"doc": "Bill of lading HLCU-2264903", "hs": "8457.10", "incoterm": "DAP Hamburg",
                "gross_kg": "26,300", "packages": "3 flatracks"},
    "SHP-006": {"doc": "Bill of lading CMDU-5518824", "hs": "2909.19", "incoterm": "CIP Basel",
                "gross_kg": "22,800", "packages": "6 ISO tanks"},
    "SHP-007": {"doc": "Bill of lading MEDU-2209471", "hs": "6203.42", "incoterm": "FOB Shanghai",
                "gross_kg": "9,240", "packages": "9 containers"},
}


def _shift(iso, days):
    try:
        return (date.fromisoformat(iso) + timedelta(days=days)).isoformat()
    except (ValueError, TypeError):
        return iso


# --- Rate ------------------------------------------------------------------


def rate_panel(shipment, decision, scenario_id):
    routes = route_advisor.load_routes()
    chosen = (decision or {}).get("recommended_route") or shipment["primary_route"]
    considered = [shipment["primary_route"]] + list(shipment.get("alternates", []))
    label, pct, why = _SURCHARGE.get(scenario_id, (None, 0, ""))

    quotes = []
    for route_id in considered:
        route = routes.get(route_id)
        if not route:
            continue
        for carrier, base in _CARRIERS.get(route_id, [("Market rate", route["cost_index"])]):
            # A surcharge only lands on a route the disruption actually touches.
            exposed = bool(decision) and route_id == shipment["primary_route"] and pct
            quotes.append({
                "carrier": carrier, "route_id": route_id,
                "discharge_port": route["discharge_port"],
                "transit_days": route["transit_days"],
                "cost_index": base + (pct if exposed else 0),
                "surcharge": label if exposed else None,
                "chosen": route_id == chosen,
            })
    quotes.sort(key=lambda q: q["cost_index"])
    if quotes:
        quotes[0]["cheapest"] = True
    return {
        "headline": f"{len(quotes)} quotes on {shipment['origin']} → {shipment['final_destination']}",
        "surcharge_note": (f"{label} applied: +{pct} index points on the booked routing, {why}."
                           if label and decision else None),
        "quotes": quotes,
    }


# --- Milestones ------------------------------------------------------------


def milestones_panel(shipment, decision, scenario_id):
    routes = route_advisor.load_routes()
    milestones = [
        {"label": "Booking confirmed", "at": _shift(shipment["etd"], -9), "done": True},
        {"label": f"Gate-in {shipment['origin']}", "at": _shift(shipment["etd"], -2), "done": True},
        {"label": f"Sailed {shipment['origin']}", "at": shipment["etd"], "done": True},
        {"label": "In transit", "at": _shift(shipment["etd"], 6), "done": True},
    ]
    if decision and decision.get("decision") == "reroute":
        route = routes.get(decision["recommended_route"], {})
        milestones.append({
            "label": f"Rerouted — discharge moved to {route.get('discharge_port','')}",
            "at": _shift(shipment["etd"], 12), "done": False, "disruption": True})
        milestones.append({"label": f"Onward: {route.get('inland_leg','')}",
                           "at": _shift(decision["revised_eta"], -1), "done": False})
    elif decision and decision.get("decision") == "hold":
        milestones.append({"label": "Held — awaiting the disruption to clear",
                           "at": _shift(shipment["etd"], 12), "done": False, "disruption": True})
    eta = (decision or {}).get("revised_eta") or shipment["eta"]
    milestones.append({"label": "Discharge / revised ETA", "at": eta, "done": False})
    return {
        "headline": f"{shipment.get('booking_ref','')} · {shipment.get('carrier','')}",
        "milestones": milestones,
        "eta": eta,
        "required_by": shipment.get("required_by"),
    }


# --- Docs ------------------------------------------------------------------


def docs_panel(shipment, decision, scenario_id):
    routes = route_advisor.load_routes()
    booked = routes.get(shipment["primary_route"], {}).get("discharge_port")
    actual = routes.get((decision or {}).get("recommended_route") or shipment["primary_route"], {}) \
        .get("discharge_port")
    base = _DOCS.get(shipment["id"], {})
    fields = [
        {"field": "Document", "value": base.get("doc", "—")},
        {"field": "Shipper", "value": f"{shipment['origin']} consolidator"},
        {"field": "Consignee", "value": shipment.get("customer", "—")},
        {"field": "Containers", "value": shipment.get("container", "—")},
        {"field": "Packages", "value": base.get("packages", "—")},
        {"field": "Gross weight", "value": f"{base.get('gross_kg','—')} kg"},
        {"field": "HS code", "value": base.get("hs", "—")},
        {"field": "Incoterm", "value": base.get("incoterm", "—")},
        {"field": "Port of discharge", "value": booked or "—"},
    ]
    mismatch = bool(actual and booked and actual != booked)
    return {
        "headline": base.get("doc", "No document on file"),
        "fields": fields,
        "flag": (f"Discharge port on the bill of lading reads {booked}, but the shipment is now "
                 f"routed to {actual}. The B/L needs an amendment before arrival."
                 if mismatch else None),
    }


# --- Assistant -------------------------------------------------------------


def assistant_panel(shipment, decision, scenario_id, board, scenario):
    """Canned questions, answers computed from the board that is actually on screen."""
    actioned = [c for c in board if c.get("state") != "green" and c.get("decision")]
    late = [c for c in actioned if c["decision"].get("deadline_breached")]
    rerouted = [c for c in actioned if c["decision"]["decision"] == "reroute"]
    held = [c for c in actioned if c["decision"]["decision"] == "hold"]

    def ids(rows):
        return ", ".join(r["id"] for r in rows) or "none"

    qa = [
        {"q": "Which shipments does this disruption hit?",
         "a": (f"{len(actioned)} of {len(board)}: {ids(actioned)}. "
               f"The rest are on routes the event does not touch.")},
        {"q": "What did we decide, and why the split?",
         "a": (f"{len(rerouted)} rerouted ({ids(rerouted)}) and {len(held)} held ({ids(held)}). "
               f"A reroute wins when an alternate lands materially sooner than waiting; "
               f"a hold wins when every alternate is worse than the disruption itself.")},
        {"q": "Which customers need telling today?",
         "a": (f"{len(late) or 'No'} shipment{'' if len(late) == 1 else 's'} now miss the "
               f"required-by date{': ' + ids(late) if late else '.'} "
               f"Every actioned shipment has a drafted customer email waiting for approval.")},
    ]
    if shipment:
        qa.append({"q": f"What is happening to {shipment['id']} specifically?",
                   "a": ((decision or {}).get("reasoning")
                         or f"{shipment['id']} is on {shipment['primary_route']} and nothing "
                            f"active touches that route.")})
    return {"headline": (scenario or {}).get("name", "No scenario active"), "qa": qa}


# --- Inbox: taking over inbound comms --------------------------------------
#
# A forwarder's day is mail. A disruption multiplies it: the carrier sends a
# notice, the customer asks where their box is, the terminal issues an advisory.
# The workflow being modelled is triage - read it, work out what it is about,
# link it to the booking, and put a reply in front of a person.
#
# The messages are authored, but which ones appear is derived from the decision
# the Route Advisor actually made, so this reacts to the run. Every reply is a
# draft and stays one; nothing here can send.


def _inbound_for(shipment, decision, scenario_id):
    """The mail one decision would generate, as (from, role, subject, intent, body)."""
    action = (decision or {}).get("decision")
    port = (decision or {}).get("recommended_discharge_port") or "the discharge port"
    cargo = shipment["cargo"].lower()

    if action == "reroute":
        return [
            ("Carrier operations", "carrier",
             f"Booking {shipment['id']} - vessel to omit original discharge port",
             "booking change",
             "Advising that the nominated vessel will omit the original discharge port on "
             "this rotation. Please confirm whether the box is to be discharged at the "
             "alternate port or held on board."),
            (shipment.get("customer", "Customer"), "customer",
             f"Any update on our {cargo}?",
             "status request",
             "We were expecting this in a few days and have seen the port news. Do we still "
             "have a date we can plan the line around?"),
        ]
    if action == "hold":
        return [
            ("Carrier operations", "carrier",
             f"Booking {shipment['id']} - berth window options",
             "berth options",
             "Terminal is releasing revised berth windows as the backlog clears. Confirm "
             "whether you want the current booking held for the next available window."),
            (shipment.get("customer", "Customer"), "customer",
             f"Is our {cargo} still on schedule?",
             "status request",
             "Checking whether we need to warn our own downstream on this one, and whether "
             "the cargo condition is affected while it waits."),
        ]
    return [
        ("Terminal operations", "terminal",
         f"Booking {shipment['id']} - gate-in confirmed",
         "milestone",
         "Routine milestone notice. No exception recorded against this booking."),
    ]


def inbox_panel(shipment, decision, scenario_id):
    action = (decision or {}).get("decision")
    revised = (decision or {}).get("revised_eta")
    port = (decision or {}).get("recommended_discharge_port")
    items = []
    for i, (sender, role, subject, intent, body) in enumerate(
            _inbound_for(shipment, decision, scenario_id)):
        # A reply is only drafted where one is actually owed. A routine milestone
        # gets read, linked and closed - answering it would be noise, and a demo
        # that replies to everything is showing volume rather than judgement.
        needs_reply = intent != "milestone"
        if intent == "booking change":
            reply = (f"Confirming discharge at {port} for {shipment['id']}. "
                     f"Please re-nominate the booking to the alternate routing and confirm "
                     f"the revised ETA of {revised}.")
        elif intent == "berth options":
            reply = (f"Please hold {shipment['id']} for the next available window. "
                     f"We are planning against a revised ETA of {revised} and will not "
                     f"re-nominate the discharge port.")
        elif intent == "status request":
            reply = (f"Yes - we have re-planned this one. Revised ETA is {revised}. "
                     f"The reasoning behind the change is on the booking, and we will flag "
                     f"any further movement before it affects your line.")
        else:
            reply = None
        items.append({
            "from": sender, "role": role, "subject": subject,
            "received": f"{(i + 1) * 17}m ago",
            "intent": intent,
            "linked_booking": shipment["id"],
            "body": body,
            "suggested_reply": reply,
            "status": "DRAFT - not sent" if needs_reply else "No reply needed",
            "approval_status": "awaiting_approval" if needs_reply else "closed",
        })
    awaiting = sum(1 for i in items if i["approval_status"] == "awaiting_approval")
    return {
        "headline": (f"{len(items)} inbound on {shipment['id']} · "
                     f"{awaiting} repl{'y' if awaiting == 1 else 'ies'} drafted"),
        "note": ("Triaged and linked automatically. Replies are drafted and held - "
                 "this app has no way to send one."),
        "items": items,
    }


# --- RFQ: taking over the quote round --------------------------------------
#
# The other half of a forwarder's inbound. A rate request arrives as prose, has
# to be read into structured fields, priced against the lane, and answered. The
# disruption matters here too: a quote written during a closure that ignores the
# surcharge is a quote the forwarder loses money on.


def rfq_panel(shipment, decision, scenario_id):
    routes = route_advisor.load_routes()
    label, pct, why = _SURCHARGE.get(scenario_id, (None, 0, ""))
    considered = [shipment["primary_route"]] + list(shipment.get("alternates", []))

    options = []
    for route_id in considered:
        route = routes.get(route_id)
        if not route:
            continue
        carrier, base = _CARRIERS.get(route_id, [("Market rate", route["cost_index"])])[0]
        exposed = bool(decision) and route_id == shipment["primary_route"] and pct
        options.append({
            "carrier": carrier, "route_id": route_id,
            "discharge_port": route["discharge_port"],
            "transit_days": route["transit_days"],
            "cost_index": base + (pct if exposed else 0),
            "surcharge": label if exposed else None,
        })
    options.sort(key=lambda o: o["cost_index"])
    best = options[0] if options else None

    request = {
        "from": shipment.get("customer", "Customer"),
        "received": "24m ago",
        "raw": (f"Need pricing {shipment['origin']} to {shipment['final_destination']}, "
                f"2 x 40ft, similar spec to our {shipment['cargo'].lower()} moves, "
                f"ready in about three weeks. What can you do?"),
        "parsed": {
            "lane": f"{shipment['origin']} → {shipment['final_destination']}",
            "equipment": "2 x 40ft" + (" reefer" if shipment.get("cold_chain") else ""),
            "commodity": shipment["cargo"],
            "ready": "≈ 3 weeks",
            "incoterm": "FCA origin (assumed - not stated in the request)",
        },
    }
    draft = None
    if best:
        surcharge_line = (f" A {label.lower()} of {pct} index points currently applies on the "
                          f"direct routing, {why}; the quote above reflects it."
                          if label and decision else "")
        draft = (f"Thanks for the enquiry. On {request['parsed']['lane']} we would route via "
                 f"{best['discharge_port']} with {best['carrier']}, around "
                 f"{best['transit_days']} days port to port.{surcharge_line} "
                 f"Happy to firm this up against your ready date.")
    return {
        "headline": f"1 rate request on {shipment['origin']} → {shipment['final_destination']}",
        "note": ("Read into fields, priced against the lane, answer drafted. "
                 "Nothing is quoted to anyone until a person approves it."),
        "request": request,
        "options": options,
        "recommended": best,
        "draft_reply": draft,
        "status": "DRAFT - not sent",
        "approval_status": "awaiting_approval",
    }


# --- TMS link ---------------------------------------------------------------


# --- Booking ---------------------------------------------------------------
# A forwarder's booking is the thing a reroute actually changes. This models the
# amendment that follows from the decision - and holds it, because sending an
# amendment to a carrier is an outbound action like any other.

_VESSELS = {
    "SHP-001": ("MSC AMBER", "V.418W"), "SHP-002": ("MAERSK KOWLOON", "V.233E"),
    "SHP-003": ("CMA CGM LOIRE", "V.107W"), "SHP-004": ("EVER LEGACY", "V.912E"),
    "SHP-005": ("HMM GARNET", "V.055W"), "SHP-006": ("RHINE TRADER", "B.221"),
    "SHP-007": ("CMA CGM RHONE", "V.340W"),
}


def booking_panel(shipment, decision, scenario_id):
    routes = route_advisor.load_routes()
    vessel, voyage = _VESSELS.get(shipment["id"], ("TBN", "TBN"))
    booked = routes.get(shipment["primary_route"], {})
    action = (decision or {}).get("decision")

    amendment = None
    if action == "reroute":
        to = routes.get((decision or {}).get("recommended_route"), {})
        amendment = {
            "type": "Change of discharge port",
            "from": booked.get("discharge_port", "-"),
            "to": to.get("discharge_port", "-"),
            "also": f"routing {shipment['primary_route']} to {decision.get('recommended_route')}",
            "revised_eta": decision.get("revised_eta"),
        }
    elif action == "hold":
        amendment = {
            "type": "Hold at load port",
            "from": "Booked to sail",
            "to": "Hold pending berth confirmation",
            "also": "no equipment release until the hold lifts",
            "revised_eta": (decision or {}).get("revised_eta"),
        }

    return {
        "headline": f"Booking {shipment['id']} with {vessel} {voyage}",
        "booking": {
            "carrier_ref": f"BK-{shipment['id'].replace('SHP-', '')}-{voyage.replace('.', '')}",
            "vessel": vessel, "voyage": voyage,
            "load_port": shipment["origin"],
            "discharge_port": booked.get("discharge_port", "-"),
            "cutoff": _shift(shipment.get("etd") or shipment["eta"], -3),
        },
        "amendment": amendment,
        # An amendment is an outbound action, so it waits like a draft email does.
        "status": "DRAFT - not sent" if amendment else "No amendment needed",
        "approval_status": "awaiting_approval" if amendment else "not_applicable",
        "note": ("Nothing is sent to the carrier. The amendment is described and held "
                 "at the approval gate."),
    }


# --- Invoice ---------------------------------------------------------------
# The reconciliation only bites when a disruption is active: the carrier bills a
# surcharge that was never in the quote, and the discrepancy is the whole point.


def invoice_panel(shipment, decision, scenario_id):
    routes = route_advisor.load_routes()
    label, pct, why = _SURCHARGE.get(scenario_id, (None, 0, ""))
    booked = routes.get(shipment["primary_route"], {})
    agreed = booked.get("cost_index", 100)
    exposed = bool(decision) and pct

    lines = [
        {"description": "Ocean freight, base rate", "agreed": agreed, "invoiced": agreed},
        {"description": "Terminal handling, destination", "agreed": 8, "invoiced": 8},
        {"description": "Documentation", "agreed": 2, "invoiced": 2},
    ]
    if exposed:
        lines.append({"description": f"{label} (not in the agreed rate)",
                      "agreed": 0, "invoiced": pct})

    disputed = [ln for ln in lines if ln["invoiced"] != ln["agreed"]]
    gap = sum(ln["invoiced"] - ln["agreed"] for ln in lines)
    return {
        "headline": f"Carrier invoice for {shipment['id']}",
        "invoice_ref": f"INV-{shipment['id'].replace('SHP-', '')}-0{1 if not exposed else 2}",
        "lines": lines,
        "gap": gap,
        "finding": (f"{len(disputed)} line does not match the agreed rate — {label.lower()}, "
                    f"{why}. Query it before the invoice is passed for payment."
                    if disputed else
                    "Every line matches the agreed rate. Nothing to query."),
        "matched": not disputed,
        "note": "Index points, in the same 100 = baseline units the rates use. Not currency.",
    }


# --- Customs ---------------------------------------------------------------
# The one that only exists because of the reroute: moving the discharge port can
# move the country of entry, and that changes who files and under which number.

_ENTRY = {
    "HAM": {"country": "Germany", "office": "Zollamt Hamburg-Waltershof", "eori": "DE"},
    "RTM": {"country": "Netherlands", "office": "Douane Rotterdam Maasvlakte", "eori": "NL"},
    "ANR": {"country": "Belgium", "office": "Douane Antwerpen", "eori": "BE"},
    "FOS": {"country": "France", "office": "Douane Marseille-Fos", "eori": "FR"},
}


def customs_panel(shipment, decision, scenario_id):
    routes = route_advisor.load_routes()
    booked = routes.get(shipment["primary_route"], {})
    now_port = ((decision or {}).get("recommended_discharge_port")
                or booked.get("discharge_port"))
    was_port = booked.get("discharge_port")
    entry = _ENTRY.get(now_port) or _ENTRY.get(was_port) or {}
    moved = bool(now_port) and bool(was_port) and now_port != was_port

    checks = [
        {"item": "Commercial invoice", "state": "on file"},
        {"item": "Packing list", "state": "on file"},
        {"item": "Bill of lading", "state": "on file" if not moved else "reissue required"},
        {"item": "Commodity code", "state": "classified"},
    ]
    if shipment.get("cold_chain"):
        checks.append({"item": "Health certificate (temperature-controlled goods)",
                       "state": "on file"})

    escalate = None
    if moved:
        escalate = (f"Entry moves from {_ENTRY.get(was_port, {}).get('country', was_port)} to "
                    f"{entry.get('country', now_port)}. A different EORI and clearance agent "
                    f"apply, and the bill of lading has to name the new discharge port. "
                    f"A person files this — the Worker will not.")
    elif shipment.get("cold_chain") and (decision or {}).get("action") == "hold":
        escalate = ("Temperature-controlled goods sitting longer than booked. Confirm the "
                    "health certificate still covers the revised date before the entry is filed.")

    return {
        "headline": f"Entry for {shipment['id']} at {now_port or '-'}",
        "entry": {"country": entry.get("country", "-"), "office": entry.get("office", "-"),
                  "eori_prefix": entry.get("eori", "-"), "regime": "Import, release for free circulation"},
        "checks": checks,
        "escalate": escalate,
        # The workers this roster models escalate a novel exception rather than
        # deciding it. So does this one, and it says so on screen rather than
        # implying it filed anything.
        "status": "Escalated to a person" if escalate else "Ready to file",
        "note": "Nothing is filed. The Worker prepares and escalates; a person submits.",
    }


def tms_panel(shipment, decision, scenario_id):
    """One booking's view of the connection. The board-wide view lives in tms.py."""
    writeback = tms._writeback_for({"id": shipment["id"], "decision": decision})
    return {
        "headline": f"Booking {shipment['id']} synced from {tms.CONNECTOR_NAME}",
        "connector": tms.CONNECTOR_NAME,
        "status": "connected (demo)",
        "field_map": tms.FIELD_MAP,
        "writeback": writeback,
        "note": (tms.connection([])["honesty"]),
    }


PANELS = {"rate": rate_panel, "milestones": milestones_panel, "docs": docs_panel,
          "inbox": inbox_panel, "rfq": rfq_panel, "booking": booking_panel,
          "invoice": invoice_panel, "customs": customs_panel, "tms": tms_panel}


def build(shipment, decision, scenario_id, board, scenario) -> dict:
    """Every scripted panel for one selected shipment."""
    out = {}
    for worker in ROSTER:
        wid = worker["id"]
        if wid == "assistant":
            out[wid] = assistant_panel(shipment, decision, scenario_id, board, scenario)
        elif shipment:
            out[wid] = PANELS[wid](shipment, decision, scenario_id)
        else:
            out[wid] = None
    return out
