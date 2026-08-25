"""signals.py - the structured half of what the desk reads.

`risk_monitor.py` reads prose: headlines that a model has to judge. This file
reads the rest of it - the numbers and the notices - because a trade lane is
moved by more than news.

    weather over the ports        Open-Meteo
    sea state on the open legs    Open-Meteo Marine
    seismic activity              USGS Earthquake Hazards Program
    natural events, worldwide     NASA EONET
    the rule before it is news    Federal Register
    the rate a reroute is billed  Frankfurter (ECB reference rates)
    government alerts, US ports   US National Weather Service
    warnings in force, Pearl Rvr  Hong Kong Observatory

Every one is keyless and listed in the public-apis catalogue; DATA-SOURCES.md
says which entry each came from. None of them needs a model: a wave height, a
magnitude and a warning code are classified by threshold, which costs nothing
and cannot hallucinate. The one exception is the Federal Register, which is
prose, so its documents go into the same classifier queue as the headlines.

Two tiers, and the difference is not cosmetic:

  lane      the reading maps onto a chokepoint some route on the board passes
            through, so it can become an event that moves a booking.
  context   the reading is real and worth showing but touches nothing on this
            board today - the FX rate a reroute is billed at, a storm over a US
            port, a typhoon signal at a load port that is not modelled as a
            chokepoint. It is rendered, and it decides nothing.

Saying which is which is the honest part. A source that reads clean is not
decoration - most days most of the world is fine, and a terminal that only ever
showed you alarms would be lying about the shape of the job.

Each source is its own small function so one can be added or pulled without
touching the others, and none of them may take the run down: a source that is
down, slow or reshaped is reported failed and skipped. They are read
concurrently, because eight independent hosts read in turn would spend the
whole budget waiting on the slowest.

Run it on its own:

    python -m src.signals            # read everything, print what came back
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FuturesTimeout
from datetime import datetime, timedelta, timezone

import requests

from src import config, geo, httpget

# ---------------------------------------------------------------------------
# Shared shape
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_event(*, event_id, chokepoint, type_, severity, title, summary, source,
                source_type, url, published_at=None, delay_days=None,
                confidence=0.9, reasoning="", source_language="en") -> dict:
    """The one place a structured source builds an event.

    Live news, the scripted scenarios and everything here must share one schema
    or the pipeline quietly treats them differently. That parity has broken
    three times in this project, every time by adding a field to one producer
    and not the others, so there is exactly one constructor per producer and
    this is the structured sources'.
    """
    return {
        "event_id": event_id,
        "origin": "live",
        "chokepoint": chokepoint,
        "type": type_ if type_ in config.EVENT_TYPES else "other",
        "severity": severity if severity in config.SEVERITIES else "low",
        "title": title,
        "title_original": None,
        "summary": summary[:400],
        "source": source,
        "source_type": source_type,
        "source_language": source_language,
        "url": url,
        "published_at": published_at or _now_iso(),
        "detected_at": _now_iso(),
        "expected_duration_hours": None,
        "expected_delay_days": delay_days,
        "scenario": None,
        "languages": [source_language],
        # A measurement has a single reader by definition, so the trail is one
        # entry. It is still carried, because live and scripted events have to
        # be the same shape all the way to the screen.
        "language_trail": [{"language": source_language, "source": source,
                            "offset_minutes": 0, "first": True,
                            "english_wire": source_language == "en"}],
        "detected_first_from": f"{source} (instrument)",
        # Nothing to compare a gauge against, and a lead that is not real is the
        # one thing this project will not print.
        "english_wire_lag_hours": None,
        "confidence": confidence,
        "reasoning": reasoning,
    }


def _band(bands, value):
    """First band the value clears, walking from the worst down. None if it
    clears nothing, which is the common case and the reason most reads produce
    no event at all."""
    for band in bands:
        if value >= band[0]:
            return band
    return None


def _coords(place_ids):
    """(ids, lats, lons) for the places the board actually knows about."""
    known = [(pid, geo.place(pid)) for pid in place_ids]
    known = [(pid, spot) for pid, spot in known if spot]
    return ([pid for pid, _ in known],
            [spot["lat"] for _, spot in known],
            [spot["lon"] for _, spot in known])


def _as_list(payload):
    """Open-Meteo answers with an object for one location and an array for
    several. Both shapes reach this code, so normalise once."""
    return payload if isinstance(payload, list) else [payload]


# ---------------------------------------------------------------------------
# 4 - Open-Meteo: weather over the discharge ports
# ---------------------------------------------------------------------------


def fetch_port_weather(timeout: float) -> dict:
    """Wind over every port a route on this board can discharge through.

    One request for all of them: the API takes comma-separated coordinates and
    answers with one block per location, in the order asked.
    """
    ids, lats, lons = _coords(config.WEATHER_PORTS)
    if not ids:
        return {"detail": "no watched port has coordinates on the board"}

    response = httpget.get_capped(
        config.OPEN_METEO_ENDPOINT,
        timeout=timeout,
        params={
            "latitude": ",".join(str(v) for v in lats),
            "longitude": ",".join(str(v) for v in lons),
            "current": "wind_speed_10m,wind_gusts_10m,precipitation",
            "wind_speed_unit": "kn",
            "timezone": "UTC",
        },
    )
    blocks = _as_list(response.json())

    events, readings = [], []
    for place_id, block in zip(ids, blocks):
        current = (block or {}).get("current") or {}
        gusts = current.get("wind_gusts_10m")
        if gusts is None:
            continue
        gusts = float(gusts)
        name = geo.place(place_id)["name"]
        band = _band(config.WIND_BANDS, gusts)
        readings.append({"place": place_id, "name": name, "gusts_kn": round(gusts),
                         "wind_kn": round(float(current.get("wind_speed_10m") or 0)),
                         "state": band[2] if band else "workable",
                         "severity": band[1] if band else None})
        if not band:
            continue
        _threshold, severity, state, delay, note = band
        events.append(build_event(
            event_id=f"EVT-WX-{place_id}",
            chokepoint=place_id,
            type_="weather",
            severity=severity,
            title=f"{state.capitalize()} over {name}: gusting {gusts:.0f} kn - {note}",
            summary=(f"Open-Meteo reports gusts of {gusts:.0f} kn at {name}, "
                     f"at or above the {_threshold} kn band where {note}."),
            source=f"Open-Meteo / {name}",
            source_type="weather",
            url="https://open-meteo.com/",
            published_at=current.get("time"),
            delay_days=delay,
            reasoning=(f"Gusts of {gusts:.0f} kn at {name} are in the {state} band, "
                       f"so {note} and any box discharging there is exposed."),
        ))
    quiet = len(readings) - len(events)
    return {"events": events, "context": {"ports": readings},
            "detail": f"{len(readings)} ports read, {quiet} workable"}


# ---------------------------------------------------------------------------
# 5 - Open-Meteo Marine: sea state on the open legs
# ---------------------------------------------------------------------------


def fetch_sea_state(timeout: float) -> dict:
    """Wave height at the three points a box on this board actually rounds."""
    ids, lats, lons = _coords(config.MARINE_WAYPOINTS)
    if not ids:
        return {"detail": "no watched waypoint has coordinates on the board"}

    response = httpget.get_capped(
        config.OPEN_METEO_MARINE_ENDPOINT,
        timeout=timeout,
        params={
            "latitude": ",".join(str(v) for v in lats),
            "longitude": ",".join(str(v) for v in lons),
            "current": "wave_height",
            "timezone": "UTC",
        },
    )
    blocks = _as_list(response.json())

    events, readings = [], []
    for place_id, block in zip(ids, blocks):
        current = (block or {}).get("current") or {}
        height = current.get("wave_height")
        if height is None:
            continue
        height = float(height)
        name = geo.place(place_id)["name"]
        band = _band(config.WAVE_BANDS, height)
        readings.append({"place": place_id, "name": name, "wave_m": round(height, 1),
                         "state": band[2] if band else "slight",
                         "severity": band[1] if band else None})
        if not band:
            continue
        _threshold, severity, state, delay, note = band
        events.append(build_event(
            event_id=f"EVT-SEA-{place_id}",
            chokepoint=place_id,
            type_="weather",
            severity=severity,
            title=f"{state.capitalize()} seas at {name}: {height:.1f} m - {note}",
            summary=(f"Open-Meteo Marine reports a significant wave height of "
                     f"{height:.1f} m at {name} ({state})."),
            source=f"Open-Meteo Marine / {name}",
            source_type="marine",
            url="https://open-meteo.com/en/docs/marine-weather-api",
            published_at=current.get("time"),
            delay_days=delay,
            reasoning=(f"A significant wave height of {height:.1f} m at {name} is in the "
                       f"{state} band, so {note} for anything routed over that leg."),
        ))
    quiet = len(readings) - len(events)
    return {"events": events, "context": {"seas": readings},
            "detail": f"{len(readings)} waypoints read, {quiet} slight"}


# ---------------------------------------------------------------------------
# 6 - USGS Earthquake Hazards Program
# ---------------------------------------------------------------------------

# Which places a quake or a natural event is allowed to attach to: the
# chokepoints, and nothing else. A magnitude 7 in the middle of an ocean is
# real and is not this board's problem.
_WATCHED = ["HAM", "RTM", "ANR", "FOS", "SUEZ", "REDSEA", "COGH", "RHINE", "FRINL"]


def fetch_earthquakes(timeout: float) -> dict:
    """Significant quakes, mapped onto a corridor or dropped."""
    since = (datetime.now(timezone.utc)
             - timedelta(days=config.QUAKE_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    response = httpget.get_capped(
        config.USGS_QUAKE_ENDPOINT,
        timeout=timeout,
        params={"format": "geojson", "starttime": since,
                "minmagnitude": config.QUAKE_MIN_MAGNITUDE, "orderby": "magnitude",
                "limit": 40},
    )
    features = response.json().get("features") or []

    events, seen = [], set()
    for feature in features:
        props = feature.get("properties") or {}
        coords = ((feature.get("geometry") or {}).get("coordinates") or [None, None])
        lon, lat = coords[0], coords[1]
        magnitude = props.get("mag")
        if lat is None or lon is None or magnitude is None:
            continue
        place_id, km = geo.nearest_place(float(lat), float(lon), _WATCHED,
                                         config.QUAKE_RADIUS_KM)
        if not place_id or place_id in seen:
            continue
        band = _band(config.QUAKE_BANDS, float(magnitude))
        if not band:
            continue
        seen.add(place_id)
        _threshold, severity, delay, note = band
        name = geo.place(place_id)["name"]
        stamp = props.get("time")
        events.append(build_event(
            event_id=f"EVT-QUAKE-{place_id}",
            chokepoint=place_id,
            type_="other",
            severity=severity,
            title=(f"M{float(magnitude):.1f} earthquake {km:.0f} km from {name}"
                   f" - {note}"),
            summary=f"USGS reports {props.get('place') or 'an earthquake'} "
                    f"at magnitude {float(magnitude):.1f}.",
            source="USGS Earthquake Hazards Program",
            source_type="seismic",
            url=props.get("url") or "https://earthquake.usgs.gov/",
            published_at=(datetime.fromtimestamp(stamp / 1000, timezone.utc).isoformat()
                          if isinstance(stamp, (int, float)) else None),
            delay_days=delay,
            reasoning=(f"A magnitude {float(magnitude):.1f} event {km:.0f} km from {name} "
                       f"is inside the {config.QUAKE_RADIUS_KM} km radius this board "
                       f"watches, so {note}."),
        ))
    return {"events": events,
            "detail": f"{len(features)} quakes read, {len(events)} near a corridor"}


# ---------------------------------------------------------------------------
# 7 - NASA EONET: open natural events, worldwide
# ---------------------------------------------------------------------------


def fetch_natural_events(timeout: float) -> dict:
    """Wildfires, storms, floods and volcanoes - the ones near a corridor.

    This is the live source the authored `france` scenario is a rehearsal of:
    a wildfire on a land leg, read off a coordinate rather than a headline.
    """
    response = httpget.get_capped(
        config.EONET_ENDPOINT,
        timeout=timeout,
        params={"status": "open", "category": config.EONET_CATEGORIES,
                "limit": config.EONET_MAX_EVENTS},
    )
    raw = response.json().get("events") or []

    events, seen = [], set()
    for item in raw:
        geometry = (item.get("geometry") or [])
        if not geometry:
            continue
        point = geometry[-1].get("coordinates") or []
        # EONET draws polygons for some events and a point for others.
        if geometry[-1].get("type") == "Polygon":
            ring = point[0] if point else []
            if not ring:
                continue
            lon = sum(p[0] for p in ring) / len(ring)
            lat = sum(p[1] for p in ring) / len(ring)
        elif len(point) >= 2:
            lon, lat = point[0], point[1]
        else:
            continue

        place_id, km = geo.nearest_place(float(lat), float(lon), _WATCHED,
                                         config.EONET_RADIUS_KM)
        if not place_id:
            continue
        categories = [c.get("id") for c in (item.get("categories") or [])]
        category = categories[0] if categories else "other"
        key = (place_id, category)
        if key in seen:
            continue
        seen.add(key)
        name = geo.place(place_id)["name"]
        severity = config.EONET_SEVERITY.get(category, "low")
        events.append(build_event(
            event_id=f"EVT-EONET-{place_id}-{category[:8].upper()}",
            chokepoint=place_id,
            type_="weather",
            severity=severity,
            title=f"{item.get('title') or category} - {km:.0f} km from {name}",
            summary=(item.get("description")
                     or f"NASA EONET is tracking an open {category} event near {name}."),
            source="NASA EONET",
            source_type="hazard",
            url=item.get("link") or "https://eonet.gsfc.nasa.gov/",
            published_at=geometry[-1].get("date"),
            delay_days=[1, 3],
            confidence=0.6,
            reasoning=(f"An open {category} event {km:.0f} km from {name} is inside the "
                       f"{config.EONET_RADIUS_KM} km radius this board watches, so the "
                       f"leg through {name} may be affected."),
        ))
    return {"events": events,
            "detail": f"{len(raw)} open events read, {len(events)} near a corridor"}


# ---------------------------------------------------------------------------
# 8 - Federal Register: the rule before it is the news
# ---------------------------------------------------------------------------


def fetch_federal_register(timeout: float) -> dict:
    """Trade rules as filings. Prose, so these join the classifier queue.

    Returned as raw items rather than events for exactly that reason: a tariff
    notice is a headline-shaped thing and the model has to read it, the same way
    it reads a wire story.
    """
    since = (datetime.now(timezone.utc)
             - timedelta(days=config.FEDERAL_REGISTER_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    response = httpget.get_capped(
        config.FEDERAL_REGISTER_ENDPOINT,
        timeout=timeout,
        params={
            "conditions[term]": config.FEDERAL_REGISTER_TERMS,
            "conditions[publication_date][gte]": since,
            "per_page": config.FEDERAL_REGISTER_MAX,
            "order": "newest",
            "fields[]": ["title", "abstract", "html_url", "publication_date", "type"],
        },
    )
    documents = response.json().get("results") or []

    items = [
        {
            "title": (doc.get("title") or "").strip(),
            "summary": (doc.get("abstract") or "")[:400],
            "url": doc.get("html_url") or "https://www.federalregister.gov/",
            "source": "Federal Register",
            "source_type": "government",
            "language": "en",
            "published_at": f"{doc.get('publication_date')}T00:00:00+00:00"
                            if doc.get("publication_date") else _now_iso(),
        }
        for doc in documents
        if doc.get("title")
    ]
    return {"items": items, "detail": f"{len(items)} filings in the last "
                                      f"{config.FEDERAL_REGISTER_LOOKBACK_DAYS} days"}


# ---------------------------------------------------------------------------
# 9 - Frankfurter: the rate a reroute is billed at
# ---------------------------------------------------------------------------


def fetch_fx(timeout: float) -> dict:
    """ECB reference rates. Board context - this decides nothing.

    A reroute is priced here as a relative cost index. The rate is what turns
    that index into what the customer is actually invoiced, which is why an ops
    lead wants it on the same screen and why it is not a risk event.
    """
    response = httpget.get_capped(
        config.FX_ENDPOINT,
        timeout=timeout,
        params={"from": config.FX_BASE, "to": ",".join(config.FX_SYMBOLS)},
    )
    payload = response.json()
    rates = payload.get("rates") or {}
    pairs = [{"pair": f"{config.FX_BASE}/{symbol}", "rate": rates[symbol]}
             for symbol in config.FX_SYMBOLS if symbol in rates]
    return {"context": {"fx": {"base": config.FX_BASE, "as_of": payload.get("date"),
                               "pairs": pairs}},
            "detail": f"{len(pairs)} pairs as of {payload.get('date')}"}


# ---------------------------------------------------------------------------
# 10 - US National Weather Service: active government alerts
# ---------------------------------------------------------------------------


def fetch_us_alerts(timeout: float) -> dict:
    """Severe alerts over the US port states. Board context.

    No booking on this synthetic board discharges in the US, so this moves
    nothing today. It is wired because it is the same read as every other
    source, and it says so on screen rather than implying otherwise.
    """
    response = httpget.get_capped(
        config.NWS_ENDPOINT,
        timeout=timeout,
        headers={"Accept": "application/geo+json"},
        params={"status": "actual", "severity": "Severe,Extreme",
                "area": ",".join(config.NWS_AREAS), "limit": config.NWS_MAX_ALERTS},
    )
    features = response.json().get("features") or []
    alerts = [
        {
            "event": (f.get("properties") or {}).get("event"),
            "area": ((f.get("properties") or {}).get("areaDesc") or "")[:70],
            "severity": ((f.get("properties") or {}).get("severity") or "").lower(),
        }
        for f in features
        if (f.get("properties") or {}).get("event")
    ]
    return {"context": {"us_alerts": alerts},
            "detail": f"{len(alerts)} severe alerts over the US port states"}


# ---------------------------------------------------------------------------
# 11 - Hong Kong Observatory: the warnings in force
# ---------------------------------------------------------------------------


def fetch_hk_warnings(timeout: float) -> dict:
    """Warnings in force over the Pearl River Delta. Board context.

    Two of the five bookings load in the Delta and a typhoon signal shuts
    Yantian and Hong Kong for a day, but the load ports are not modelled as
    chokepoints on this board - so this informs the desk and moves nothing,
    which is the honest behaviour rather than a gap.
    """
    response = httpget.get_capped(
        config.HKO_ENDPOINT,
        timeout=timeout,
        params={"dataType": "warnsum", "lang": "en"},
    )
    payload = response.json() or {}
    warnings = [
        {"name": entry.get("name"), "code": entry.get("code"),
         "action": entry.get("actionCode"), "issued": entry.get("issueTime")}
        for entry in payload.values()
        if isinstance(entry, dict) and entry.get("name")
    ]
    return {"context": {"hk_warnings": warnings},
            "detail": (f"{len(warnings)} warnings in force"
                       if warnings else "no warnings in force")}


# ---------------------------------------------------------------------------
# The roster, and reading it
# ---------------------------------------------------------------------------

# tier: "lane" can move a booking on this board; "context" cannot, and says so.
SIGNAL_SOURCES = [
    {"id": "open-meteo", "name": "Open-Meteo: port weather", "family": "weather",
     "tier": "lane", "host": "api.open-meteo.com", "fn": fetch_port_weather},
    {"id": "open-meteo-marine", "name": "Open-Meteo Marine: sea state",
     "family": "weather", "tier": "lane", "host": "marine-api.open-meteo.com",
     "fn": fetch_sea_state},
    {"id": "usgs-quake", "name": "USGS: seismic", "family": "hazard",
     "tier": "lane", "host": "earthquake.usgs.gov", "fn": fetch_earthquakes},
    {"id": "eonet", "name": "NASA EONET: natural events", "family": "hazard",
     "tier": "lane", "host": "eonet.gsfc.nasa.gov", "fn": fetch_natural_events},
    {"id": "federal-register", "name": "Federal Register: trade rules",
     "family": "government", "tier": "lane", "host": "www.federalregister.gov",
     "fn": fetch_federal_register},
    {"id": "frankfurter", "name": "Frankfurter: ECB reference rates",
     "family": "markets", "tier": "context", "host": "api.frankfurter.app",
     "fn": fetch_fx},
    {"id": "nws", "name": "US NWS: active alerts", "family": "government",
     "tier": "context", "host": "api.weather.gov", "fn": fetch_us_alerts},
    {"id": "hko", "name": "Hong Kong Observatory: warnings", "family": "weather",
     "tier": "context", "host": "data.weather.gov.hk", "fn": fetch_hk_warnings},
]

FAMILY_LABELS = {
    "weather": "Weather & sea state",
    "hazard": "Natural hazards",
    "government": "Government & regulatory",
    "markets": "Markets",
}


def _read_one(spec: dict, timeout: float) -> tuple:
    """One source. Returns (label, status, result, detail) and never raises."""
    label = f"{spec['name']} [{spec['family']}]"
    try:
        result = spec["fn"](timeout) or {}
    except requests.RequestException as exc:
        return label, "failed", {}, httpget.short_error(exc, spec["host"])
    except (ValueError, TypeError, KeyError, IndexError) as exc:
        # The source answered with something other than what it documents.
        # That is a failure of this source, not of the run.
        return label, "failed", {}, f"unexpected reply shape: {type(exc).__name__}"
    return label, "ok", result, result.get("detail", "")


def read_signals(budget) -> dict:
    """Every structured source at once.

    `budget` is whatever the caller uses to keep the live pull on time - it only
    has to answer `spent()` and `timeout()`, so this module never has to import
    the monitor that owns it.

    Returns events (already classified, no model involved), items (prose, for
    the classifier), context (real readings that move nothing) and one report
    entry per source.
    """
    entries, events, items, context = [], [], [], {}

    if budget.spent():
        return {"events": [], "items": [], "context": {},
                "entries": [{"name": f"{s['name']} [{s['family']}]", "status": "skipped",
                             "items": 0, "detail": "live-pull time budget spent"}
                            for s in SIGNAL_SOURCES]}

    timeout = budget.timeout()
    results = {}
    # Not a `with` block, for the same reason as the RSS pool: its exit joins
    # every worker, so one wedged source would block the run there instead of
    # being abandoned. The capped read means those threads still end shortly.
    pool = ThreadPoolExecutor(max_workers=config.SIGNAL_CONCURRENCY)
    try:
        futures = {pool.submit(_read_one, spec, timeout): spec for spec in SIGNAL_SOURCES}
        try:
            for future in as_completed(futures, timeout=max(timeout + 2, budget.remaining())):
                spec = futures[future]
                try:
                    results[spec["id"]] = future.result()
                except Exception as exc:                       # noqa: BLE001
                    results[spec["id"]] = (f"{spec['name']} [{spec['family']}]",
                                           "failed", {},
                                           httpget.short_error(exc, spec["host"]))
        except FuturesTimeout:
            pass          # the ordered report below marks the stragglers skipped
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    # Reported in roster order so the output is stable run to run.
    for spec in SIGNAL_SOURCES:
        label, status, result, detail = results.get(
            spec["id"], (f"{spec['name']} [{spec['family']}]", "skipped", {},
                         "not reached inside the time budget"))
        found = list(result.get("events") or [])
        raw = list(result.get("items") or [])
        events += found
        items += raw
        context.update(result.get("context") or {})
        entries.append({"name": label, "status": status,
                        "items": len(found) + len(raw), "detail": detail,
                        "family": spec["family"], "tier": spec["tier"]})
    return {"events": events, "items": items, "context": context, "entries": entries}


# ---------------------------------------------------------------------------
# Run it on its own
# ---------------------------------------------------------------------------


class _Unbudgeted:
    """Stand-in for the monitor's Budget when this file is run by itself."""

    def spent(self):
        return False

    def remaining(self):
        return float(config.LIVE_PULL_BUDGET_SECONDS)

    def timeout(self):
        return float(config.HTTP_TIMEOUT_SECONDS)


def main():
    state = read_signals(_Unbudgeted())
    print("\nSTRUCTURED SOURCES")
    for entry in state["entries"]:
        mark = {"ok": "ok  ", "failed": "FAIL", "skipped": "skip"}[entry["status"]]
        print(f"  [{mark}] {entry['name']:<44} {entry['items']:>3}  {entry['detail']}")

    print(f"\n{len(state['events'])} event(s) on a watched corridor:")
    for event in state["events"]:
        print(f"  {event['chokepoint']:<7} {event['severity']:<7} {event['title']}")

    if state["items"]:
        print(f"\n{len(state['items'])} filing(s) queued for the classifier:")
        for item in state["items"][:5]:
            print(f"  {item['title'][:96]}")

    if state["context"]:
        print("\nBoard context (real, and decides nothing):")
        print(json.dumps(state["context"], indent=2)[:1200])
    print()


if __name__ == "__main__":
    main()
