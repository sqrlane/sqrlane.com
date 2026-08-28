"""risk_monitor.py - component 1: the real, live part.

Reads the prose half of what the desk watches - news and trade press - works out
which of it matters to our chokepoints, and assembles risk_state.json from every
family at once. The structured half (weather, sea state, seismic, natural
hazards, government filings, rates) lives in signals.py and is merged in here.

    news + filings ->  cheap keyword prefilter  ->  LLM classification  ->  events
    Rhine gauges   ->  threshold check  ->  events       (numbers need no LLM)
    instruments    ->  signals.py, threshold + proximity ->  events
    injected file  ->  already classified  ->  events    (the scripted strike)

Four producers, one schema, on purpose: the scripted Hamburg strike flows
through the same pipeline as a wave height and a wire story, so the demo happens
on command while the plumbing stays honest. Parity between them has broken three
times in this project, every time by adding a field to one producer and not the
others - `tests/test_signals_read_wide_and_fail_soft.py` now compares them.

All four families are read CONCURRENTLY inside one shared time budget (see
pull_everything). Read in turn, the first family would spend the budget and the
rest would be skipped, which is how a board that claims to watch the world
quietly ends up watching one feed.

Run it on its own:

    python -m src.risk_monitor                # live pull, classify, write state
    python -m src.risk_monitor --inject       # live pull PLUS the Hamburg strike
    python -m src.risk_monitor --inject-only  # skip the network entirely
    python -m src.risk_monitor --no-llm       # keyword-only, no API key needed
"""

import argparse
import hashlib
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FuturesTimeout
from datetime import datetime, timedelta, timezone

import feedparser
import requests

from src import config, httpget, llm, signals

# The capped GET and the one-line error live in httpget.py, because the
# structured sources in signals.py need exactly the same guarantees and neither
# module should have to import the other. The names are kept here so the rest of
# this file - and anything that has ever reached for them - still reads the same.
_get_capped = httpget.get_capped
_short_error = httpget.short_error
SourceTooSlow = httpget.SourceTooSlow

# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _stable_id(text: str, length: int = 6) -> str:
    """Short, deterministic id for a news item."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:length].upper()


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_chokepoints() -> list[dict]:
    return _load_json(config.CHOKEPOINTS_FILE)["chokepoints"]


class Budget:
    """A wall-clock allowance for the whole live pull.

    Sources are read one at a time, so without a shared ceiling one slow feed
    delays every feed behind it. Each source checks the clock before it starts
    and borrows only what is left.
    """

    def __init__(self, seconds: float):
        self.total = seconds
        self._deadline = time.monotonic() + seconds

    def remaining(self) -> float:
        return max(0.0, self._deadline - time.monotonic())

    def spent(self) -> bool:
        return self.remaining() <= 0.5      # under half a second is not worth starting

    def timeout(self) -> float:
        """Never wait longer than the budget has left."""
        return max(1.0, min(config.HTTP_TIMEOUT_SECONDS, self.remaining()))


class SourceReport:
    """Records how each source did, so the dashboard can say 'GDELT was down'
    instead of the whole demo falling over.

    Each report belongs to one family - news, water, weather, and so on - which
    is what lets the board group sixty sources into something a person can
    read at a glance instead of one long list.
    """

    def __init__(self, family: str = "news", tier: str = "lane"):
        self.family = family
        self.tier = tier
        self.entries: list[dict] = []

    def _add(self, name, status, items, detail, language=None):
        self.entries.append({"name": name, "status": status, "items": items,
                             "detail": detail, "family": self.family,
                             "tier": self.tier, "language": language})

    def ok(self, name, items, detail="", language=None):
        self._add(name, "ok", items, detail, language)

    def failed(self, name, detail, language=None):
        self._add(name, "failed", 0, detail, language)

    def skipped(self, name, detail, language=None):
        self._add(name, "skipped", 0, detail, language)

    @property
    def failures(self):
        return [e for e in self.entries if e["status"] == "failed"]


# ---------------------------------------------------------------------------
# Source 1 - GDELT DOC 2.0 (no key, global news backbone)
# ---------------------------------------------------------------------------


def fetch_gdelt(report: SourceReport, budget: "Budget") -> list[dict]:
    """One narrow query at a time; a failing query never kills the others."""
    items = []
    for spec in config.GDELT_QUERIES:
        label = f"GDELT: {spec['label']}"
        if budget.spent():
            report.skipped(label, "live-pull time budget spent", language=spec["language"])
            continue
        try:
            response = _get_capped(
                config.GDELT_ENDPOINT,
                params={"query": spec["query"], "mode": "artlist", "format": "json",
                        "maxrecords": config.GDELT_MAX_RECORDS, "timespan": config.GDELT_TIMESPAN},
                timeout=budget.timeout(),
            )
            articles = response.json().get("articles", [])
        except requests.RequestException as exc:
            report.failed(label, _short_error(exc, "api.gdeltproject.org"),
                          language=spec["language"])
            continue
        except ValueError:
            # GDELT answers 200 with HTML when it is overloaded or rate-limiting.
            report.failed(label, "non-JSON reply - GDELT is probably throttling; try again shortly",
                          language=spec["language"])
            continue

        found = [
            {
                "title": article.get("title", "").strip(),
                "summary": "",
                "url": article.get("url", ""),
                "source": f"GDELT / {article.get('domain', 'unknown')}",
                "source_type": "gdelt",
                "language": (article.get("language") or spec["language"] or "en").lower()[:2],
                "published_at": _parse_gdelt_date(article.get("seendate", "")),
            }
            for article in articles
            if article.get("title")
        ]
        items.extend(found)
        report.ok(label, len(found), language=spec["language"])
        time.sleep(min(config.GDELT_PAUSE_SECONDS, budget.remaining()))
    return items


def _parse_gdelt_date(seendate: str) -> str:
    """GDELT stamps dates as 20260824T021500Z."""
    try:
        return datetime.strptime(seendate, "%Y%m%dT%H%M%SZ").replace(
            tzinfo=timezone.utc).isoformat()
    except (ValueError, TypeError):
        return _now_iso()


# ---------------------------------------------------------------------------
# Source 2 - RSS (where the multilingual earliness edge lives)
# ---------------------------------------------------------------------------


def _fetch_one_feed(feed_spec: dict, timeout: float) -> tuple:
    """One feed. Returns (label, status, items, detail) and never raises.

    Kept separate so the feeds can be read concurrently: they are independent
    requests, and reading ten of them one after another cannot fit inside a
    serverless budget - at six seconds each that is a minute for RSS alone,
    so all but the first would be skipped and the language count that the whole
    differentiation rests on would collapse to one.
    """
    label = f"RSS: {feed_spec['name']} [{feed_spec['language']}]"
    try:
        response = _get_capped(feed_spec["url"], timeout=timeout)
        parsed = feedparser.parse(response.content)
    except requests.RequestException as exc:
        return label, "failed", [], _short_error(exc, feed_spec["url"].split("/")[2])

    if parsed.bozo and not parsed.entries:
        return label, "failed", [], f"unparseable feed: {str(parsed.get('bozo_exception',''))[:80]}"

    found = [
        {
            "title": _strip_html(entry.get("title", "")),
            "summary": _strip_html(entry.get("summary", ""))[:400],
            "url": entry.get("link", ""),
            "source": feed_spec["name"],
            "source_type": "rss",
            "language": feed_spec["language"],
            "published_at": _parse_rss_date(entry),
        }
        for entry in parsed.entries[: config.RSS_MAX_ITEMS_PER_FEED]
        if entry.get("title")
    ]
    return label, "ok", found, ""


def fetch_rss(report: SourceReport, budget: "Budget") -> list[dict]:
    """All feeds at once. One slow feed no longer delays the nine behind it."""
    if budget.spent():
        for feed_spec in config.RSS_FEEDS:
            report.skipped(f"RSS: {feed_spec['name']} [{feed_spec['language']}]",
                           "live-pull time budget spent", language=feed_spec["language"])
        return []

    timeout = budget.timeout()
    items = []
    results = {}
    # Not a `with` block: its exit joins every worker, so one wedged feed would
    # block the run there instead. Whatever has not answered by the deadline is
    # abandoned and reported as skipped - the capped read above means those
    # threads still end on their own shortly after.
    pool = ThreadPoolExecutor(max_workers=config.RSS_CONCURRENCY)
    try:
        futures = {pool.submit(_fetch_one_feed, spec, timeout): spec
                   for spec in config.RSS_FEEDS}
        try:
            for future in as_completed(futures, timeout=max(timeout + 2, budget.remaining())):
                spec = futures[future]
                try:
                    results[spec["name"]] = future.result()
                except Exception as exc:                   # noqa: BLE001
                    results[spec["name"]] = (
                        f"RSS: {spec['name']} [{spec['language']}]", "failed", [],
                        _short_error(exc, spec["url"].split("/")[2]))
        except FuturesTimeout:
            pass          # the ordered report below marks the stragglers skipped
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    # Report in the configured order so the output is stable run to run.
    for spec in config.RSS_FEEDS:
        label, status, found, detail = results.get(
            spec["name"], (f"RSS: {spec['name']} [{spec['language']}]",
                           "skipped", [], "not reached inside the time budget"))
        if status == "ok":
            report.ok(label, len(found), language=spec["language"])
            items.extend(found)
        elif status == "failed":
            report.failed(label, detail, language=spec["language"])
        else:
            report.skipped(label, detail, language=spec["language"])
    return items


def _parse_rss_date(entry) -> str:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime(*parsed[:6], tzinfo=timezone.utc).isoformat()
    return _now_iso()


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").replace("&nbsp;", " ").strip()


# ---------------------------------------------------------------------------
# Source 3 - PEGELONLINE Rhine gauges
# ---------------------------------------------------------------------------
# These come back as numbers, not prose. A water level does not need an LLM to
# be understood, so these are classified by threshold and become events directly.
#
# Two callers want these gauges for different reasons: the risk monitor wants
# events off every gauge in RHINE_GAUGES, the landing page wants the readings
# themselves - and only for the three reference gauges its panel was designed
# around (LANDING_GAUGES). Both go through _read_one_gauge and _gauge_state,
# so neither the request nor the threshold bands can drift between them -
# which is how the injected and live event schemas came apart three times.

# The bands, in the order they are tested: a reading at or below the threshold
# named on the left is in that band. Above them all, the gauge is unremarkable.
GAUGE_BANDS = [
    # threshold key   severity  state         delay days  what it means
    ("critical_cm",   "high",   "critical",   [3, 6], "barge traffic largely halted"),
    ("high_cm",       "medium", "restricted", [2, 4], "barges loading well below capacity"),
    ("warn_cm",       "low",    "watch",      [1, 2], "loading restrictions beginning to bite"),
]


def _gauge_state(gauge: dict, level_cm: float) -> tuple:
    """(severity, state, expected delay days, note) for one reading.

    severity is None when the river is simply running, which is the common case
    and the reason most days produce no Rhine event at all.
    """
    for key, severity, state, delay, note in GAUGE_BANDS:
        if level_cm <= gauge[key]:
            return severity, state, delay, note
    return None, "normal", None, "running normally"


def _read_one_gauge(gauge: dict, timeout: float) -> dict:
    """One gauge, read and classified. Never raises - the error is the result."""
    label = gauge["name"]
    try:
        response = _get_capped(
            f"{config.PEGELONLINE_ENDPOINT}/{gauge['station']}/W/currentmeasurement.json",
            timeout=timeout,
        )
        measurement = response.json()
        level_cm = float(measurement.get("value"))
    except (requests.RequestException, ValueError, TypeError) as exc:
        return {"station": gauge["station"], "name": label, "ok": False,
                "error": _short_error(exc, "pegelonline.wsv.de")}

    severity, state, _delay, note = _gauge_state(gauge, level_cm)
    return {
        "station": gauge["station"],
        "name": label,
        "ok": True,
        "level_cm": round(level_cm),
        "measured_at": measurement.get("timestamp") or _now_iso(),
        "severity": severity,          # None when the river is running normally
        "state": state,                # normal | watch | restricted | critical
        "note": note,
        "warn_cm": gauge["warn_cm"],
        "high_cm": gauge["high_cm"],   # the loading threshold - the line that matters
        "critical_cm": gauge["critical_cm"],
    }


def read_rhine_gauges(stations: list[str] | None = None) -> dict:
    """The Rhine gauges as readings, for callers that want numbers not events.

    `stations` picks which gauges by station id; it defaults to LANDING_GAUGES
    because the caller that matters is the landing page's gauge panel, which
    was designed around the three reference gauges and keeps showing exactly
    those - the monitor's live pull reads the wider RHINE_GAUGES list through
    fetch_rhine_levels instead. Both resolve against the same configured list,
    so the two callers cannot carry different thresholds for the same station.

    Read concurrently and on a tight leash: this one is called from a page load
    rather than from the button, and three sequential timeouts against a source
    having a slow day is a page that hangs in front of whoever opened it.
    """
    wanted = stations if stations is not None else config.LANDING_GAUGES
    by_station = {g["station"]: g for g in config.RHINE_GAUGES}
    selected = [by_station[s] for s in wanted if s in by_station]

    timeout = min(config.GAUGE_TIMEOUT_SECONDS, config.GAUGE_BUDGET_SECONDS)
    results = {}
    # Not a `with` block, for the reason given in fetch_rss: its exit joins every
    # worker, so one wedged gauge would block here instead.
    pool = ThreadPoolExecutor(max_workers=max(1, len(selected)))
    try:
        futures = {pool.submit(_read_one_gauge, g, timeout): g
                   for g in selected}
        try:
            for future in as_completed(futures, timeout=config.GAUGE_BUDGET_SECONDS):
                gauge = futures[future]
                try:
                    results[gauge["station"]] = future.result()
                except Exception as exc:                     # noqa: BLE001
                    results[gauge["station"]] = {
                        "station": gauge["station"], "name": gauge["name"], "ok": False,
                        "error": _short_error(exc, "pegelonline.wsv.de")}
        except FuturesTimeout:
            pass          # whatever did not answer is marked below
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    # Reported in the configured order so the strip is stable read to read.
    gauges = [results.get(g["station"], {
        "station": g["station"], "name": g["name"], "ok": False,
        "error": "no answer inside the time budget"}) for g in selected]
    return {"source": "PEGELONLINE",
            "read_at": _now_iso(),
            "gauges": gauges,
            "ok": any(g["ok"] for g in gauges)}


def fetch_rhine_levels(report: SourceReport, budget: "Budget") -> list[dict]:
    events = []
    for gauge in config.RHINE_GAUGES:
        label = f"PEGELONLINE: {gauge['name']}"
        if budget.spent():
            report.skipped(label, "live-pull time budget spent", language="de")
            continue

        reading = _read_one_gauge(gauge, budget.timeout())
        if not reading["ok"]:
            report.failed(label, reading["error"], language="de")
            continue

        event = _rhine_event(gauge, reading["level_cm"], reading["measured_at"])
        if event:
            events.append(event)
            report.ok(label, 1, f"{reading['level_cm']} cm - {event['severity']}", language="de")
        else:
            report.ok(label, 0, f"{reading['level_cm']} cm - normal, no event", language="de")
    return events


def _crossed_threshold_cm(gauge: dict, level_cm: float):
    """The threshold the reading actually crossed - the first band it clears,
    same walk as _gauge_state. Witnessed going wrong before this existed: a
    warn-band reading (Maxau, 370 cm) was captioned "at or below the 320 cm
    restriction threshold", quoting the medium band it had NOT crossed. The
    band was right and the sentence was false, which is worse than being
    wrong - it reads as broken arithmetic on screen."""
    for key, *_ in GAUGE_BANDS:
        if level_cm <= gauge[key]:
            return gauge[key]
    return None


def _rhine_event(gauge, level_cm, timestamp):
    """Turn a gauge reading into an event, or None if the level is unremarkable."""
    severity, _state, delay, note = _gauge_state(gauge, level_cm)
    if severity is None:
        return None
    crossed_cm = _crossed_threshold_cm(gauge, level_cm)

    return {
        "event_id": f"EVT-RHINE-{gauge['station']}",
        "origin": "live",
        "chokepoint": "RHINE",
        "type": "weather",
        "severity": severity,
        "title": f"Rhine low water at {gauge['name']}: {level_cm:.0f} cm - {note}",
        "title_original": None,
        "summary": (f"Gauge {gauge['name']} reading {level_cm:.0f} cm "
                    f"(restriction threshold {crossed_cm} cm)."),
        "source": f"PEGELONLINE / {gauge['name']} gauge",
        "source_type": "gauge",
        "source_language": "de",
        "url": f"https://www.pegelonline.wsv.de/webservice/dokuRestapi",
        "published_at": timestamp,
        "detected_at": _now_iso(),
        "expected_duration_hours": None,
        "expected_delay_days": delay,
        "scenario": None,
        "languages": ["de"],
        "language_trail": [{"language": "de", "source": f"PEGELONLINE {gauge['name']} gauge",
                            "offset_minutes": 0, "first": True, "english_wire": False}],
        "detected_first_from": f"PEGELONLINE {gauge['name']} gauge (regional)",
        "english_wire_lag_hours": None,
        "confidence": 0.9,
        "reasoning": (f"Water level {level_cm:.0f} cm is at or below the "
                      f"{crossed_cm} cm restriction threshold for {gauge['name']}, "
                      f"so Rhine barge capacity out of the North Range is constrained."),
    }


# ---------------------------------------------------------------------------
# Reading everything at once
# ---------------------------------------------------------------------------

# The order the board reads in. News first because it is the biggest family and
# the one an audience checks, then the instruments, then the notices and the
# rates. Every source the desk watches appears here whatever happened to it, so
# the count on screen is of what was ATTEMPTED, not of what happened to answer.
FAMILY_LABELS = {
    "news": "News",
    "water": "Rivers",
    **signals.FAMILY_LABELS,
    # Read live like everything else, and unable to move a booking on this
    # board. Kept as its own family so the count of what decides things stays
    # honest - see the `tier` note in signals.py.
    **{f"{family}-context": f"{label} (context)"
       for family, label in signals.FAMILY_LABELS.items()},
}

# The scripted scenario reports itself as a source so the CLI can show where
# each event came from. It is not a live source and never counts as one.
DISPLAY_LABELS = {**FAMILY_LABELS, "scenario": "Scripted scenario",
                  "offline": "Live sources (not read)"}


def expected_sources() -> list[dict]:
    """Every source the desk watches, in reading order, before anything is read.

    Kept in one place because three separate screens quote the source count and
    they must not be able to disagree about it.
    """
    listed = [{"name": f"GDELT: {q['label']}", "family": "news", "tier": "lane"}
              for q in config.GDELT_QUERIES]
    listed += [{"name": f"RSS: {f['name']} [{f['language']}]", "family": "news",
                "tier": "lane"} for f in config.RSS_FEEDS]
    listed += [{"name": f"PEGELONLINE: {g['name']}", "family": "water", "tier": "lane"}
               for g in config.RHINE_GAUGES]
    listed += [{"name": f"{sig['name']} [{sig['family']}]", "family": sig["family"],
                "tier": sig["tier"]} for sig in signals.SIGNAL_SOURCES
               if sig["tier"] == "lane"]
    # Context sources last, and grouped together: a family that can move a
    # booking and a family that cannot should not be interleaved on screen.
    listed += [{"name": f"{sig['name']} [{sig['family']}]",
                "family": f"{sig['family']}-context", "tier": "context"}
               for sig in signals.SIGNAL_SOURCES if sig["tier"] == "context"]
    return listed


def source_count() -> int:
    return len(expected_sources())


def family_summary(entries: list[dict]) -> list[dict]:
    """One row per family: how many of its sources answered, and what it is for.

    Sixty sources in a flat list is a wall. Grouped, it is the shape of the
    claim - the desk reads news, instruments, notices and rates, not just news.
    """
    rows = []
    for family, label in FAMILY_LABELS.items():
        mine = [e for e in entries if e.get("family") == family
                and not e["name"].startswith("scenario:")]
        if not mine:
            continue
        rows.append({
            "id": family,
            "label": label,
            "total": len(mine),
            "read": sum(1 for e in mine if e["status"] == "ok"),
            "items": sum(e["items"] for e in mine),
            # A family is context-only when none of its sources can move a
            # booking on this board. Said out loud rather than implied.
            "tier": "lane" if any(e.get("tier", "lane") == "lane" for e in mine) else "context",
        })
    return rows


def pull_everything(budget: "Budget") -> dict:
    """Every family at once, inside one shared time budget.

    Read in turn, sixty sources cannot fit a serverless budget: the first family
    would spend it and the rest would be skipped, which is how a board that
    claims to watch the world quietly ends up watching one feed. The families
    are independent requests to different hosts, so they run together and the
    whole pull costs about what the slowest single family costs.

    Each family fills its own report, and the reports are merged in the fixed
    order above - so the output is stable run to run even though the reads are
    not. Anything that has not answered by the deadline is reported skipped
    against the source it belongs to, never silently dropped.
    """
    news_report = SourceReport("news")
    water_report = SourceReport("water")
    collected = {"items": [], "events": [], "context": {}, "signal_entries": []}

    def _rss():
        collected["items"] += fetch_rss(news_report, budget)

    def _gdelt():
        collected["items"] += fetch_gdelt(news_report, budget)

    def _gauges():
        collected["events"] += fetch_rhine_levels(water_report, budget)

    def _signals():
        read = signals.read_signals(budget)
        collected["events"] += read["events"]
        collected["items"] += read["items"]
        collected["context"].update(read["context"])
        collected["signal_entries"] += read["entries"]

    # Not a `with` block, for the same reason as the pools inside it: its exit
    # joins every worker, so one wedged family would block here instead.
    pool = ThreadPoolExecutor(max_workers=4)
    try:
        futures = [pool.submit(job) for job in (_rss, _gdelt, _gauges, _signals)]
        try:
            for future in as_completed(futures, timeout=budget.remaining() + 2):
                future.result()
        except FuturesTimeout:
            pass          # whatever is missing is marked skipped just below
        except Exception:                                       # noqa: BLE001
            pass          # a family that threw is reported through its own entries
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    recorded = {e["name"]: e for e in
                news_report.entries + water_report.entries + collected["signal_entries"]}
    # The expected list is the one authority on which family a source belongs
    # to, so its family and tier are laid over whatever came back. Otherwise a
    # source that answered would be grouped by its own idea of itself and a
    # source that did not by the board's, and the two would drift.
    entries = []
    for spec in expected_sources():
        entry = recorded.get(spec["name"])
        if entry is None:
            entry = {"name": spec["name"], "status": "skipped", "items": 0,
                     "detail": "not reached inside the time budget", "language": None}
        entries.append({**entry, "family": spec["family"], "tier": spec["tier"]})
    return {"entries": entries, "items": collected["items"],
            "events": collected["events"], "context": collected["context"]}


# ---------------------------------------------------------------------------
# The injected (scripted) event
# ---------------------------------------------------------------------------


def load_scenarios(include_disabled: bool = False) -> list[dict]:
    """The baked-in disruptions. Each swaps the active risk over one shared pool."""
    data = _load_json(config.SCENARIOS_FILE)
    return [s for s in data["scenarios"] if include_disabled or s.get("enabled", True)]


def default_scenario() -> str:
    return _load_json(config.SCENARIOS_FILE).get("default", "hamburg")


def find_scenario(scenario_id: str | None) -> dict | None:
    """Look one up by id. A disabled scenario is still findable by name, so the
    France one can be switched on without editing code."""
    wanted = (scenario_id or default_scenario()).strip().lower()
    for s in load_scenarios(include_disabled=True):
        if s["id"] == wanted:
            return s
    return None


def wire_lag_hours(language_trail: list[dict]) -> int | None:
    """How far ahead of the English wires the first source was, in whole hours.

    Derived from the trail rather than stored beside it, so the headline number
    and the timeline it is drawn from can never disagree. Returns None when the
    English wires led (the Suez knock-on) or never appear - there is no lead to
    claim, and a claimed lead that is not real is the one thing this demo cannot
    afford.
    """
    if not language_trail:
        return None
    first = next((t for t in language_trail if t.get("first")), language_trail[0])
    english = next((t for t in language_trail if t.get("english_wire")), None)
    if english is None:
        return None
    minutes = english.get("offset_minutes", 0) - first.get("offset_minutes", 0)
    return int(minutes // 60) if minutes > 0 else None


def load_injected_events(scenario_id: str | None = None) -> list[dict]:
    """One scenario's events, stamped fresh so the feed reads as live."""
    scenario = find_scenario(scenario_id)
    raw_events = scenario["events"] if scenario else []
    events = []
    for raw in raw_events:
        event = {k: v for k, v in raw.items() if not k.startswith("_")}
        event["scenario"] = scenario["id"] if scenario else None
        offset = event.pop("published_offset_minutes", 0)
        now = datetime.now(timezone.utc).replace(microsecond=0)
        event["published_at"] = (now + timedelta(minutes=offset)).isoformat()
        event["detected_at"] = now.isoformat()
        # Derived, never read from the file: see wire_lag_hours.
        event["english_wire_lag_hours"] = wire_lag_hours(event.get("language_trail", []))
        events.append(event)
    return events


# ---------------------------------------------------------------------------
# Prefilter - cost control, NOT the relevance decision
# ---------------------------------------------------------------------------


def prefilter(items: list[dict], chokepoints: list[dict]) -> list[dict]:
    """Drop items that mention no chokepoint at all.

    General feeds like tagesschau are mostly domestic politics and sport. This
    screen exists so we do not spend LLM calls on them. It only ever REDUCES the
    candidate set - the LLM still makes the actual relevance and severity call
    on everything that survives.
    """
    chokepoint_terms = [(cp["id"], [k.lower() for k in cp["keywords"]]) for cp in chokepoints]
    disruption_terms = [k.lower() for k in config.DISRUPTION_KEYWORDS]

    kept = []
    for item in items:
        haystack = f"{item['title']} {item.get('summary', '')}".lower()
        hits = [cp_id for cp_id, terms in chokepoint_terms if any(t in haystack for t in terms)]
        if not hits:
            continue
        item["_candidate_chokepoints"] = hits
        item["_has_disruption_word"] = any(t in haystack for t in disruption_terms)
        kept.append(item)

    # A chokepoint plus a disruption word is the strong signal; put those first
    # so the per-run ceiling spends itself on the most promising items.
    kept.sort(key=lambda i: (not i["_has_disruption_word"], i["published_at"]), reverse=False)
    return kept[: config.MAX_ITEMS_TO_CLASSIFY]


def deduplicate(items: list[dict]) -> list[dict]:
    """Same story from two feeds is one item."""
    seen, unique = set(), []
    for item in items:
        key = item.get("url") or ""
        title_key = re.sub(r"\W+", "", item["title"].lower())[:60]
        if key in seen or title_key in seen:
            continue
        seen.update({key, title_key})
        unique.append(item)
    return unique


# ---------------------------------------------------------------------------
# Classification - the LLM's job
# ---------------------------------------------------------------------------

CLASSIFY_SYSTEM = (
    "You are a freight-forwarding risk analyst. You read news items and decide "
    "whether each one threatens ocean or inland freight moving through specific "
    "chokepoints. You are strict: most news is not logistics-relevant, and "
    "saying so is the correct answer. Never invent a disruption that the text "
    "does not describe."
)


def _classify_prompt(batch, chokepoints) -> str:
    vocabulary = "\n".join(
        f"  {cp['id']} = {cp['name']} ({cp['type']})" for cp in chokepoints
    )
    listing = "\n\n".join(
        f"[{index}] language={item['language']} source={item['source']}\n"
        f"title: {item['title']}\n"
        f"summary: {item.get('summary', '')[:300]}"
        for index, item in enumerate(batch)
    )
    return f"""Classify each news item below.

The only chokepoints that matter:
{vocabulary}

For EACH item return one object:
  "index": the item number
  "relevant": true only if the item describes a real, current or imminent event
              that would disrupt freight through one of the chokepoints above.
              Commentary, statistics, historical pieces and general business
              news are NOT relevant.
  "chokepoint": one id from the list above, or null if not relevant
  "type": one of {config.EVENT_TYPES}
  "severity": one of {config.SEVERITIES}
      low    = minor friction, hours of delay
      medium = meaningful disruption, 1-3 days
      high   = the chokepoint is effectively blocked or unusable
  "expected_delay_days": [min, max] whole days of delay to a shipment routed
      through that chokepoint, or null if not relevant
  "title_en": the title in English. If the item is already English, repeat it.
  "confidence": 0.0 to 1.0
  "reasoning": ONE sentence, plain English, explaining the call. This is shown
      to a human operator, so write it for them.

Return a JSON array of exactly {len(batch)} objects, nothing else.

ITEMS:
{listing}"""


def classify_with_llm(items, chokepoints, verbose=True) -> list[dict]:
    """Batch the survivors through the LLM and build events from the hits."""
    events = []
    for start in range(0, len(items), config.CLASSIFY_BATCH_SIZE):
        batch = items[start:start + config.CLASSIFY_BATCH_SIZE]
        if verbose:
            print(f"  classifying items {start + 1}-{start + len(batch)} "
                  f"of {len(items)} ...", flush=True)
        try:
            verdicts = llm.complete_json(_classify_prompt(batch, chokepoints),
                                         system=CLASSIFY_SYSTEM, max_tokens=2000)
        except llm.LLMError as exc:
            print(f"  ! classification batch failed, skipping it: {exc}", file=sys.stderr)
            continue
        if isinstance(verdicts, dict):
            verdicts = verdicts.get("items") or verdicts.get("results") or [verdicts]

        valid_ids = {cp["id"] for cp in chokepoints}
        for verdict in verdicts:
            if not isinstance(verdict, dict) or not verdict.get("relevant"):
                continue
            if verdict.get("chokepoint") not in valid_ids:
                continue
            try:
                item = batch[int(verdict["index"])]
            except (KeyError, ValueError, TypeError, IndexError):
                continue
            events.append(_event_from_verdict(item, verdict))
    return events


def _event_from_verdict(item, verdict) -> dict:
    """Assemble the shared event schema from one item + one LLM verdict."""
    is_english = item["language"] == "en"
    english_title = (verdict.get("title_en") or item["title"]).strip()
    return {
        # Stable across runs: Python's hash() is randomised per process, which
        # would give the same article a new id every time the monitor runs.
        "event_id": f"EVT-{verdict['chokepoint']}-{_stable_id(item['url'] or item['title'])}",
        "origin": "live",
        "chokepoint": verdict["chokepoint"],
        "type": verdict.get("type") if verdict.get("type") in config.EVENT_TYPES else "other",
        "severity": verdict.get("severity") if verdict.get("severity") in config.SEVERITIES else "low",
        "title": english_title,
        "title_original": None if is_english else item["title"],
        "summary": item.get("summary", "")[:400],
        "source": item["source"],
        "source_type": item["source_type"],
        "source_language": item["language"],
        "url": item["url"],
        "published_at": item["published_at"],
        "detected_at": _now_iso(),
        "expected_duration_hours": None,
        "expected_delay_days": verdict.get("expected_delay_days"),
        # Where we caught it. On a non-English source this is the earliness edge,
        # recorded as data rather than asserted in the demo script.
        "scenario": None,          # live news belongs to no scripted scenario
        "languages": [item["language"]],
        "language_trail": [{"language": item["language"], "source": item["source"],
                            "offset_minutes": 0, "first": True,
                            "english_wire": item["language"] == "en"}],
        # Where the source sits, not what language it publishes in. The edge is
        # proximity to the event; the language it happens to be in is incidental
        # and naming it makes the claim look narrower than it is.
        "detected_first_from": (f"{item['source']} "
                                f"({'international' if item['language'] == 'en' else 'regional'})"),
        # We cannot measure wire lag on a live pull, so we say so rather than guess.
        "english_wire_lag_hours": None,
        "confidence": verdict.get("confidence", 0.5),
        "reasoning": verdict.get("reasoning", ""),
    }


def classify_without_llm(items, chokepoints) -> list[dict]:
    """Keyword-only fallback for --no-llm: lets you prove the source plumbing
    works before you have an API key. Deliberately crude, and labelled as such
    so its output can never be mistaken for the real classification."""
    events = []
    for item in items:
        if not item.get("_has_disruption_word"):
            continue
        chokepoint = item["_candidate_chokepoints"][0]
        events.append(_event_from_verdict(item, {
            "index": 0, "relevant": True, "chokepoint": chokepoint,
            "type": "other", "severity": "low",
            "expected_delay_days": None, "confidence": 0.2,
            "title_en": item["title"],
            "reasoning": "KEYWORD MATCH ONLY - no LLM was used. Not a real classification.",
        }))
    return events


# ---------------------------------------------------------------------------
# Assemble and write the state
# ---------------------------------------------------------------------------


def run(*, live=True, inject=False, use_llm=True, verbose=True, scenario=None) -> dict:
    """The whole monitor. Returns the risk_state dict it also writes to disk."""
    chokepoints = load_chokepoints()
    report = SourceReport()
    raw_items, events, context = [], [], {}
    stats = {"raw_items": 0, "after_prefilter": 0, "llm_used": False}

    if live:
        budget = Budget(config.LIVE_PULL_BUDGET_SECONDS)
        if verbose:
            print(f"Pulling {source_count()} live sources (up to {budget.total:.0f}s) ...")
        pulled = pull_everything(budget)
        report.entries = pulled["entries"]
        raw_items += pulled["items"]
        events += pulled["events"]
        context = pulled["context"]
        out_of_time = [e for e in report.entries if e["status"] == "skipped"]
        if out_of_time and verbose:
            print(f"  {len(out_of_time)} source(s) not reached inside the time budget")

        raw_items = deduplicate(raw_items)
        stats["raw_items"] = len(raw_items)
        candidates = prefilter(raw_items, chokepoints)
        stats["after_prefilter"] = len(candidates)
        if verbose:
            print(f"  {len(raw_items)} items pulled, {len(candidates)} mention a chokepoint")

        if candidates:
            if use_llm and llm.is_configured():
                stats["llm_used"] = True
                events += classify_with_llm(candidates, chokepoints, verbose=verbose)
            else:
                if verbose and use_llm:
                    print("  ! no AI provider configured - falling back to keyword matching")
                    print(f"  ! {llm.configuration_hint()}")
                events += classify_without_llm(candidates, chokepoints)
    else:
        # Its own family, so the family strip does not report "News 0/1" and
        # imply the board watches a single news source.
        offline = SourceReport("offline")
        offline.skipped("live sources", "--inject-only: network skipped")
        report.entries += offline.entries

    scenario_meta = None
    if inject:
        scenario_meta = find_scenario(scenario)
        injected = load_injected_events(scenario)
        events += injected
        scenario_report = SourceReport("scenario")
        scenario_report.ok(
            f"scenario: {scenario_meta['name'] if scenario_meta else 'unknown'} (scripted)",
            len(injected), scenario_meta["kind"] if scenario_meta else "")
        report.entries += scenario_report.entries

    # Taken from what each source recorded rather than scraped out of its label:
    # the structured sources carry a family in brackets, not a language, so
    # parsing the name would have counted "weather" as a language.
    languages_read = sorted({s["language"] for s in report.entries
                             if s["status"] == "ok" and s.get("language")})
    # The scripted scenario reports itself as a source so the CLI can show where
    # each event came from. It is not a live source, and "N of M sources read" is
    # the claim an audience uses to check that the news pull is real - so the
    # count is taken here, once, rather than filtered differently on each screen.
    live_sources = [e for e in report.entries if not e["name"].startswith("scenario:")]
    state = {
        "generated_at": _now_iso(),
        "languages_read": languages_read,
        "live_sources_total": len(live_sources),
        "live_sources_read": sum(1 for e in live_sources if e["status"] == "ok"),
        "provider": llm.describe() if stats["llm_used"] else "none (no LLM call made)",
        "sources": report.entries,
        # Readings that are real and decide nothing: the rate a reroute is
        # billed at, weather over ports this board does not call at. Kept apart
        # from `events` on purpose - a number on a screen is not a risk.
        "context": context,
        "families": family_summary(report.entries),
        "stats": stats,
        "scenario": ({k: scenario_meta[k] for k in
                      ("id", "name", "kind", "summary", "decision_type", "expected")}
                     if scenario_meta else None),
        "events": events,
    }
    with open(config.RISK_STATE_FILE, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, ensure_ascii=False)
    return state


# ---------------------------------------------------------------------------
# Terminal output
# ---------------------------------------------------------------------------


def print_state(state):
    print("\n" + "=" * 74)
    print(f"RISK STATE   {state['generated_at']}   (AI: {state['provider']})")
    print("=" * 74)

    print("\nSOURCES")
    shown = None
    for entry in state["sources"]:
        family = entry.get("family", "news")
        if family != shown:
            shown = family
            note = "  - real, and moves nothing on this board" if entry.get("tier") == "context" else ""
            print(f"\n  -- {DISPLAY_LABELS.get(family, family)}{note}")
        mark = {"ok": "ok  ", "failed": "FAIL", "skipped": "skip"}[entry["status"]]
        detail = f"  {entry['detail']}" if entry["detail"] else ""
        print(f"  [{mark}] {entry['name']:<44} {entry['items']:>3} items{detail}")

    if state.get("families"):
        print("\n  " + "   ".join(f"{f['label']} {f['read']}/{f['total']}"
                                  for f in state["families"]))

    stats = state["stats"]
    print(f"\n  {stats['raw_items']} pulled -> {stats['after_prefilter']} mention a chokepoint "
          f"-> {len(state['events'])} events")

    if not state["events"]:
        print("\nNo events. That is a normal result - most days nothing is on fire.")
        print("Run with --inject to load the scripted Hamburg strike.\n")
        return

    print("\nEVENTS")
    for event in state["events"]:
        flag = "INJECTED" if event["origin"] == "injected" else "LIVE"
        print("\n" + "-" * 74)
        print(f"  [{flag}] {event['chokepoint']}  {event['type']}  severity={event['severity']}")
        print(f"  {event['title']}")
        if event.get("title_original"):
            print(f"  original ({event['source_language']}): {event['title_original']}")
        print(f"  source: {event['source']}  [{event['source_language']}]")
        if event.get("expected_delay_days"):
            low, high = event["expected_delay_days"]
            print(f"  expected delay: {low}-{high} days")
        print(f"  why: {event['reasoning']}")
    print("-" * 74)

    non_english = {e["source_language"] for e in state["events"] if e["source_language"] != "en"}
    if non_english:
        print(f"\n  Non-English sources produced events: {', '.join(sorted(non_english))}"
              "  <- read closer to the event than the wires are.")

    _print_context(state.get("context") or {})
    print(f"\nWritten to {config.RISK_STATE_FILE}\n")


def _print_context(context):
    """The readings that are real and decide nothing. Labelled as such."""
    if not context:
        return
    print("\nBOARD CONTEXT  (read live; affects no booking on this board)")
    for reading in context.get("ports", []):
        print(f"  wind   {reading['name']:<22} {reading['gusts_kn']:>3} kn gusts - {reading['state']}")
    for reading in context.get("seas", []):
        print(f"  sea    {reading['name']:<22} {reading['wave_m']:>4} m - {reading['state']}")
    fx = context.get("fx")
    if fx:
        rates = "  ".join(f"{p['pair']} {p['rate']}" for p in fx["pairs"])
        print(f"  fx     as of {fx['as_of']}: {rates}")
    for alert in context.get("us_alerts", [])[:4]:
        print(f"  us     {alert['event']} - {alert['area']}")
    for warning in context.get("hk_warnings", [])[:4]:
        print(f"  hk     {warning['name']} ({warning['code']})")


def main():
    parser = argparse.ArgumentParser(description="Trade-lane Risk Monitor (component 1).")
    parser.add_argument("--inject", action="store_true",
                        help="also load a scripted scenario (default: hamburg)")
    parser.add_argument("--scenario", help="which scenario: hamburg, redsea, rhine, france")
    parser.add_argument("--list-scenarios", action="store_true", help="show the scenarios and exit")
    parser.add_argument("--inject-only", action="store_true",
                        help="skip the network; load only the scripted strike")
    parser.add_argument("--no-llm", action="store_true",
                        help="keyword matching instead of the LLM (no API key needed)")
    parser.add_argument("--quiet", action="store_true", help="less chatter while running")
    args = parser.parse_args()

    if args.list_scenarios:
        for s in load_scenarios(include_disabled=True):
            print(f"  {s['id']:<9} {'on ' if s.get('enabled', True) else 'off'} "
                  f"{s['name']:<26} {s['decision_type']}")
        return 0

    state = run(
        live=not args.inject_only,
        inject=args.inject or args.inject_only or bool(args.scenario),
        use_llm=not args.no_llm,
        verbose=not args.quiet,
        scenario=args.scenario,
    )
    print_state(state)

    failures = [e for e in state["sources"] if e["status"] == "failed"]
    if failures and not state["events"]:
        print(f"All {len(failures)} live source(s) failed and nothing was injected.")
        print("Check your network, or run: python -m src.risk_monitor --inject-only\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
