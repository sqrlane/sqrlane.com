"""risk_monitor.py - component 1: the real, live part.

Pulls the CORE sources from DATA-SOURCES.md, works out which of them matter to
our chokepoints, and writes structured events to risk_state.json.

    live news  ->  cheap keyword prefilter  ->  LLM classification  ->  events
    Rhine gauges  ->  threshold check  ->  events        (numbers need no LLM)
    injected file ->  already classified  ->  events     (the scripted strike)

Injected and live events share one schema on purpose: the scripted Hamburg
strike flows through the same pipeline as everything else, so the demo happens
on command while the plumbing stays honest.

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
import socket
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FuturesTimeout
from datetime import datetime, timedelta, timezone

import feedparser
import requests

from src import config, llm

# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _short_error(exc, host_hint: str = "") -> str:
    """Turn a wall of urllib3 traceback text into one readable line.

    A demo operator needs to know *which* source is down and roughly why, not
    the full connection-pool stack.
    """
    name = type(exc).__name__
    text = str(exc)
    if "Tunnel connection failed" in text or "ProxyError" in name or "ProxyError" in text:
        return f"blocked by network/proxy policy ({host_hint or 'host unreachable'})"
    if "NameResolution" in text or "getaddrinfo" in text:
        return f"DNS lookup failed ({host_hint})"
    if "timed out" in text.lower():
        return f"timed out after {config.HTTP_TIMEOUT_SECONDS}s ({host_hint})"
    return f"{name}: {text[:110]}"


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
    instead of the whole demo falling over."""

    def __init__(self):
        self.entries: list[dict] = []

    def ok(self, name, items, detail=""):
        self.entries.append({"name": name, "status": "ok", "items": items, "detail": detail})

    def failed(self, name, detail):
        self.entries.append({"name": name, "status": "failed", "items": 0, "detail": detail})

    def skipped(self, name, detail):
        self.entries.append({"name": name, "status": "skipped", "items": 0, "detail": detail})

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
            report.skipped(label, "live-pull time budget spent")
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
            report.failed(label, _short_error(exc, "api.gdeltproject.org"))
            continue
        except ValueError as exc:
            # GDELT answers 200 with HTML when it is overloaded or rate-limiting.
            report.failed(label, "non-JSON reply - GDELT is probably throttling; try again shortly")
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
        report.ok(label, len(found))
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


class SourceTooSlow(requests.RequestException):
    """A source that is answering, but too slowly to be worth waiting for."""


def _get_capped(url, *, timeout, params=None):
    """A GET that is guaranteed to end.

    requests' timeout is between-bytes, not total: a server that trickles one
    byte per second never trips an eight-second timeout, so the call - and the
    thread running it - lasts forever. Every source here is a third-party server
    we do not control, so each read is capped by a total deadline and a size
    limit as well. Without this a single slow feed hangs the whole demo, which
    is the failure mode that actually shows up in front of an audience.
    """
    response = requests.get(url, params=params, headers={"User-Agent": config.USER_AGENT},
                            timeout=timeout, stream=True)
    # Checking a deadline between chunks is not enough: a read blocks until its
    # chunk is full, so a trickling source never reaches the check. The socket
    # has to be closed from outside, which makes the blocked read raise.
    expired = []

    def _give_up():
        # Shutting the socket down is what actually unblocks a read that is
        # already waiting; closing the response object alone does not.
        expired.append(True)
        sock = getattr(getattr(response.raw, "_connection", None), "sock", None)
        for stop in (lambda: sock.shutdown(socket.SHUT_RDWR), lambda: sock.close(),
                     response.raw.close):
            try:
                stop()
            except Exception:                    # noqa: BLE001
                pass

    watchdog = threading.Timer(timeout, _give_up)
    watchdog.daemon = True
    watchdog.start()
    try:
        response.raise_for_status()
        chunks, total = [], 0
        for chunk in response.iter_content(8192):
            chunks.append(chunk)
            total += len(chunk)
            if total > config.HTTP_MAX_BYTES or expired:
                break
        if expired:
            raise SourceTooSlow(f"still sending after {timeout:.0f}s - gave up")
        response._content = b"".join(chunks)     # so .json() and .content still work
        return response
    except (OSError, requests.RequestException) as exc:
        if expired:
            raise SourceTooSlow(f"still sending after {timeout:.0f}s - gave up") from exc
        raise
    finally:
        watchdog.cancel()
        response.close()


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
                           "live-pull time budget spent")
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
            report.ok(label, len(found))
            items.extend(found)
        elif status == "failed":
            report.failed(label, detail)
        else:
            report.skipped(label, detail)
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


def fetch_rhine_levels(report: SourceReport, budget: "Budget") -> list[dict]:
    events = []
    for gauge in config.RHINE_GAUGES:
        label = f"PEGELONLINE: {gauge['name']}"
        if budget.spent():
            report.skipped(label, "live-pull time budget spent")
            continue
        try:
            response = _get_capped(
                f"{config.PEGELONLINE_ENDPOINT}/{gauge['station']}/W/currentmeasurement.json",
                timeout=budget.timeout(),
            )
            measurement = response.json()
            level_cm = float(measurement.get("value"))
        except (requests.RequestException, ValueError, TypeError) as exc:
            report.failed(label, _short_error(exc, "pegelonline.wsv.de"))
            continue

        event = _rhine_event(gauge, level_cm, measurement.get("timestamp") or _now_iso())
        if event:
            events.append(event)
            report.ok(label, 1, f"{level_cm:.0f} cm - {event['severity']}")
        else:
            report.ok(label, 0, f"{level_cm:.0f} cm - normal, no event")
    return events


def _rhine_event(gauge, level_cm, timestamp):
    """Turn a gauge reading into an event, or None if the level is unremarkable."""
    if level_cm <= gauge["critical_cm"]:
        severity, delay, note = "high", [3, 6], "barge traffic largely halted"
    elif level_cm <= gauge["high_cm"]:
        severity, delay, note = "medium", [2, 4], "barges loading well below capacity"
    elif level_cm <= gauge["warn_cm"]:
        severity, delay, note = "low", [1, 2], "loading restrictions beginning to bite"
    else:
        return None

    return {
        "event_id": f"EVT-RHINE-{gauge['station']}",
        "origin": "live",
        "chokepoint": "RHINE",
        "type": "weather",
        "severity": severity,
        "title": f"Rhine low water at {gauge['name']}: {level_cm:.0f} cm - {note}",
        "title_original": None,
        "summary": (f"Gauge {gauge['name']} reading {level_cm:.0f} cm "
                    f"(restriction threshold {gauge['high_cm']} cm)."),
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
                      f"{gauge['high_cm']} cm restriction threshold for {gauge['name']}, "
                      f"so Rhine barge capacity out of the North Range is constrained."),
    }


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
    raw_items, events = [], []
    stats = {"raw_items": 0, "after_prefilter": 0, "llm_used": False}

    if live:
        budget = Budget(config.LIVE_PULL_BUDGET_SECONDS)
        if verbose:
            print(f"Pulling live sources (up to {budget.total:.0f}s) ...")
        # Order matters, because whatever the budget does not reach is skipped.
        # RSS first: it is one request per feed with no pauses, and it carries
        # the German-language feeds the whole earliness claim rests on. Gauges
        # next, being three small requests. GDELT last: four queries with a
        # pause between each, so it is the slowest and the most expendable.
        raw_items += fetch_rss(report, budget)
        events += fetch_rhine_levels(report, budget)
        raw_items += fetch_gdelt(report, budget)
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
        report.skipped("live sources", "--inject-only: network skipped")

    scenario_meta = None
    if inject:
        scenario_meta = find_scenario(scenario)
        injected = load_injected_events(scenario)
        events += injected
        report.ok(f"scenario: {scenario_meta['name'] if scenario_meta else 'unknown'} (scripted)",
                  len(injected), scenario_meta["kind"] if scenario_meta else "")

    languages_read = sorted({s["name"].split("[")[-1].rstrip("]")
                             for s in report.entries
                             if s["status"] == "ok" and "[" in s["name"]})
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
    for entry in state["sources"]:
        mark = {"ok": "ok  ", "failed": "FAIL", "skipped": "skip"}[entry["status"]]
        detail = f"  {entry['detail']}" if entry["detail"] else ""
        print(f"  [{mark}] {entry['name']:<42} {entry['items']:>3} items{detail}")

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
              "  <- this is the earliness edge, made visible.")
    print(f"\nWritten to {config.RISK_STATE_FILE}\n")


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
