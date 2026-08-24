"""geo.py - put the board on a map.

Turns a route's ordered chokepoint list into a polyline that follows water. The
alternative - drawing a straight line from Shanghai to Hamburg - cuts across
Asia and Africa and reads as broken, which undermines the one thing the map is
for.

Coordinates and sea lanes live in `data/geo.json`. They are approximate by
design: this positions a demo, it does not navigate a ship, and the file says so.

Nothing here contacts a map service. There is no tile server, no API key and no
CDN - the whole map is inlined SVG, for the same reason the page carries its own
fonts: an external asset is one more thing that can fail in front of an audience.
"""

import json

from src import config

_CACHE: dict = {}


def _geo() -> dict:
    if not _CACHE:
        with open(config.DATA_DIR / "geo.json", encoding="utf-8") as fh:
            _CACHE.update(json.load(fh))
    return _CACHE


def project(lat: float, lon: float) -> tuple[float, float]:
    """Equirectangular, into the same viewBox the coastline was drawn in."""
    f = _geo()["_frame"]
    x = (lon - f["lon0"]) / (f["lon1"] - f["lon0"]) * f["width"]
    y = (f["lat1"] - lat) / (f["lat1"] - f["lat0"]) * f["height"]
    return round(x, 1), round(y, 1)


def _pt(place_id: str) -> tuple[float, float]:
    p = _geo()["places"][place_id]
    return project(p["lat"], p["lon"])


def _corridor(name: str) -> list[tuple[float, float]]:
    return [project(lat, lon) for lat, lon in _geo()["corridors"][name]]


def route_polyline(origin: str, route: dict, destination: str) -> list[tuple[float, float]]:
    """Origin, out through whatever the route actually transits, then inland.

    Built from the route's own chokepoint list rather than a per-route drawing,
    so a route added to routes.json appears on the map without touching this.
    """
    chokes = route.get("chokepoints", [])
    discharge = route.get("discharge_port")
    pts: list[tuple[float, float]] = [_pt(origin)]
    pts += _corridor("asia_to_malacca")

    if "COGH" in chokes:
        pts += _corridor("malacca_to_cogh")
        pts.append(_pt("COGH"))
        pts += _corridor("cogh_to_fos" if discharge == "FOS" else "cogh_to_northsea")
    else:
        pts += _corridor("malacca_to_babelmandeb")
        pts.append(_pt("REDSEA"))
        pts += _corridor("redsea_to_suez")
        pts.append(_pt("SUEZ"))
        pts += _corridor("suez_to_fos" if discharge == "FOS" else "suez_to_gibraltar")
        if discharge != "FOS":
            pts += _corridor("gibraltar_to_northsea")

    if discharge:
        pts.append(_pt(discharge))
    # Inland legs are drawn only where the route actually has one.
    for inland in ("RHINE", "FRINL"):
        if inland in chokes:
            pts.append(_pt(inland))
    if destination in _geo()["places"]:
        pts.append(_pt(destination))
    return pts


def build(board: list[dict], events: list[dict], routes: dict) -> dict:
    """Everything the map draws, derived from the run - never authored per-run."""
    blocked = {}
    for event in events:
        cp = event.get("chokepoint")
        if not cp:
            continue
        # Worst severity wins where two events land on the same place.
        rank = {"low": 1, "medium": 2, "high": 3}
        if cp not in blocked or rank.get(event.get("severity"), 0) > rank.get(blocked[cp]["severity"], 0):
            blocked[cp] = {"severity": event.get("severity"), "type": event.get("type"),
                           "title": event.get("title"), "origin": event.get("origin")}

    # Hamburg is both a discharge port and a final destination, at the same
    # coordinates. Draw the port and drop the duplicate, or every North Range
    # port carries two overlapping markers.
    port_coords = {project(p["lat"], p["lon"]) for p in _geo()["places"].values()
                   if p["kind"] in ("port", "strait", "cape", "inland")}
    places = []
    for pid, place in _geo()["places"].items():
        x, y = project(place["lat"], place["lon"])
        if place["kind"] == "destination" and (x, y) in port_coords:
            continue
        places.append({"id": pid, "name": place["name"], "kind": place["kind"],
                       "x": x, "y": y, "blocked": blocked.get(pid),
                       "lx": x + place.get("label_dx", 0),
                       "ly": y + place.get("label_dy", -9)})

    lanes = []
    for card in board:
        decision = card.get("decision") or {}
        # Draw where the box is actually going: the recommended route once a
        # reroute has been decided, the booked one otherwise. Drawing the booked
        # route on a rerouted card would show the map disagreeing with the board.
        effective = (decision.get("recommended_route")
                     if decision.get("decision") == "reroute" else None)
        route = routes.get(effective or card.get("route_id") or card.get("primary_route") or "")
        if not route:
            continue
        pts = route_polyline(card["origin"], route, card["final_destination"])
        lanes.append({
            "id": card["id"],
            "state": card.get("state", "green"),
            "route_id": route["route_id"],
            "rerouted": bool(effective),
            "cargo": card.get("cargo"),
            "from": card["origin"],
            "to": card["final_destination"],
            "points": pts,
            # Which of this lane's chokepoints are carrying active risk right now.
            "hit": [c for c in route.get("chokepoints", []) if c in blocked],
        })

    return {
        "frame": _geo()["_frame"],
        "places": places,
        "lanes": lanes,
        "blocked": blocked,
        "note": ("Positions are approximate and the sea lanes are authored - the map "
                 "places the board, it does not navigate it."),
    }
