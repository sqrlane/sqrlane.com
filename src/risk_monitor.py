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
import sys
import time
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
            response = requests.get(
                config.GDELT_ENDPOINT,
                params={"query": spec["query"], "mode": "artlist", "format": "json",
                        "maxrecords": config.GDELT_MAX_RECORDS, "timespan": config.GDELT_TIMESPAN},
                headers={"User-Agent": config.USER_AGENT},
                timeout=budget.timeout(),
            )
            response.raise_for_status()
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


def fetch_rss(report: SourceReport, budget: "Budget") -> list[dict]:
    """One feed at a time; a dead feed is recorded and skipped, never fatal."""
    items = []
    for feed_spec in config.RSS_FEEDS:
        label = f"RSS: {feed_spec['name']} [{feed_spec['language']}]"
        if budget.spent():
            report.skipped(label, "live-pull time budget spent")
            continue
        try:
            response = requests.get(
                feed_spec["url"],
                headers={"User-Agent": config.USER_AGENT},
                timeout=budget.timeout(),
            )
            response.raise_for_status()
            parsed = feedparser.parse(response.content)
        except requests.RequestException as exc:
            report.failed(label, _short_error(exc, feed_spec["url"].split("/")[2]))
            continue

        if parsed.bozo and not parsed.entries:
            report.failed(label, f"unparseable feed: {str(parsed.get('bozo_exception', ''))[:80]}")
            continue

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
        items.extend(found)
        report.ok(label, len(found))
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
            response = requests.get(
                f"{config.PEGELONLINE_ENDPOINT}/{gauge['station']}/W/currentmeasurement.json",
                headers={"User-Agent": config.USER_AGENT},
                timeout=budget.timeout(),
            )
            response.raise_for_status()
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
        "detected_first_from": f"PEGELONLINE {gauge['name']} gauge (de)",
        "english_wire_lag_hours": None,
        "confidence": 0.9,
        "reasoning": (f"Water level {level_cm:.0f} cm is at or below the "
                      f"{gauge['high_cm']} cm restriction threshold for {gauge['name']}, "
                      f"so Rhine barge capacity out of the North Range is constrained."),
    }


# ---------------------------------------------------------------------------
# The injected (scripted) event
# ---------------------------------------------------------------------------


def load_injected_events() -> list[dict]:
    """The scripted Hamburg strike, stamped fresh so the feed reads as live."""
    events = []
    for raw in _load_json(config.INJECTED_EVENTS_FILE)["events"]:
        event = {k: v for k, v in raw.items() if not k.startswith("_")}
        offset = event.pop("published_offset_minutes", 0)
        now = datetime.now(timezone.utc).replace(microsecond=0)
        event["published_at"] = (now + timedelta(minutes=offset)).isoformat()
        event["detected_at"] = now.isoformat()
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
        "detected_first_from": f"{item['source']} ({item['language']})",
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


def run(*, live=True, inject=False, use_llm=True, verbose=True) -> dict:
    """The whole monitor. Returns the risk_state dict it also writes to disk."""
    chokepoints = load_chokepoints()
    report = SourceReport()
    raw_items, events = [], []
    stats = {"raw_items": 0, "after_prefilter": 0, "llm_used": False}

    if live:
        budget = Budget(config.LIVE_PULL_BUDGET_SECONDS)
        if verbose:
            print(f"Pulling live sources (up to {budget.total:.0f}s) ...")
        raw_items += fetch_gdelt(report, budget)
        raw_items += fetch_rss(report, budget)
        events += fetch_rhine_levels(report, budget)
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

    if inject:
        injected = load_injected_events()
        events += injected
        report.ok("injected events (scripted)", len(injected), "data/injected_events.json")

    state = {
        "generated_at": _now_iso(),
        "provider": llm.describe() if stats["llm_used"] else "none (no LLM call made)",
        "sources": report.entries,
        "stats": stats,
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
                        help="also load the scripted Hamburg strike")
    parser.add_argument("--inject-only", action="store_true",
                        help="skip the network; load only the scripted strike")
    parser.add_argument("--no-llm", action="store_true",
                        help="keyword matching instead of the LLM (no API key needed)")
    parser.add_argument("--quiet", action="store_true", help="less chatter while running")
    args = parser.parse_args()

    state = run(
        live=not args.inject_only,
        inject=args.inject or args.inject_only,
        use_llm=not args.no_llm,
        verbose=not args.quiet,
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
