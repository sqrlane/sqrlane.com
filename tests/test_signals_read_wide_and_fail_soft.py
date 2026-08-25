"""The structured public APIs: wide, honest, and unable to take the run down.

Three things are worth a test here, and they are the three that have actually
gone wrong in this project before:

  1. SCHEMA PARITY. Live news, the scripted scenarios and these instruments all
     produce events into one pipeline. Parity has broken three times, every time
     by adding a field to one producer and not the others. So a structured
     event is compared key-for-key against a scripted one.

  2. FAIL-SOFT. Forty-two sources is forty-two things that can be down, slow or
     reshaped in front of an audience. Every one of them must be able to fail
     without the cycle failing, and the failure has to be reported rather than
     swallowed.

  3. THE TIER LINE. A `context` source may never produce an event. That is the
     whole honesty of the second tier: the FX rate and the storm over a US port
     are real, they are on screen, and they decide nothing. If one of them ever
     starts emitting events, the board is claiming something it should not.

Run it with the rest:  python -m unittest discover -s tests
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, httpget, risk_monitor, signals  # noqa: E402


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


# What each host answers with, in the shape its documentation describes.
PAYLOADS = {
    "api.open-meteo.com": [
        {"current": {"time": "2026-08-25T03:00", "wind_speed_10m": 38.0,
                     "wind_gusts_10m": 52.0, "precipitation": 1.2}},
        {"current": {"time": "2026-08-25T03:00", "wind_speed_10m": 25.0,
                     "wind_gusts_10m": 36.0, "precipitation": 0.0}},
        {"current": {"time": "2026-08-25T03:00", "wind_speed_10m": 12.0,
                     "wind_gusts_10m": 18.0, "precipitation": 0.0}},
        {"current": {"time": "2026-08-25T03:00", "wind_speed_10m": 9.0,
                     "wind_gusts_10m": 14.0, "precipitation": 0.0}},
    ],
    "marine-api.open-meteo.com": [
        {"current": {"time": "2026-08-25T03:00", "wave_height": 1.1}},
        {"current": {"time": "2026-08-25T03:00", "wave_height": 4.4}},
        {"current": {"time": "2026-08-25T03:00", "wave_height": 7.2}},
    ],
    "earthquake.usgs.gov": {"features": [
        {"properties": {"mag": 6.8, "place": "120 km W of Suez",
                        "time": 1756000000000, "url": "https://example.invalid/q"},
         "geometry": {"coordinates": [32.0, 30.2, 10]}},
        # Real, large, and nowhere near anything this board routes through.
        {"properties": {"mag": 7.4, "place": "South Pacific",
                        "time": 1756000000000, "url": "https://example.invalid/p"},
         "geometry": {"coordinates": [-150.0, -20.0, 10]}},
    ]},
    "eonet.gsfc.nasa.gov": {"events": [
        {"title": "Wildfire - Rhone valley", "link": "https://example.invalid/e1",
         "categories": [{"id": "wildfires"}],
         "geometry": [{"type": "Point", "coordinates": [4.9, 45.9],
                       "date": "2026-08-24T00:00:00Z"}]},
        {"title": "Storm - far away", "link": "https://example.invalid/e2",
         "categories": [{"id": "severeStorms"}],
         "geometry": [{"type": "Polygon",
                       "coordinates": [[[100, 10], [101, 10], [101, 11], [100, 11]]],
                       "date": "2026-08-24T00:00:00Z"}]},
    ]},
    "www.federalregister.gov": {"results": [
        {"title": "Modification of Section 301 tariffs", "abstract": "USTR announces ...",
         "html_url": "https://example.invalid/fr", "publication_date": "2026-08-22",
         "type": "Notice"},
    ]},
    "api.frankfurter.app": {"base": "EUR", "date": "2026-08-22",
                            "rates": {"USD": 1.09, "CNY": 7.82, "GBP": 0.85}},
    "api.weather.gov": {"features": [
        {"properties": {"event": "Hurricane Warning", "areaDesc": "Coastal Georgia",
                        "severity": "Extreme"}}]},
    "data.weather.gov.hk": {"WTCSGNL": {"name": "Tropical Cyclone Warning Signal",
                                        "code": "TC8NE", "actionCode": "ISSUE",
                                        "issueTime": "2026-08-25T01:40:00"}},
}


class Budget:
    """The monitor's Budget, duck-typed. signals.py never imports the real one."""

    def spent(self):
        return False

    def remaining(self):
        return 25.0

    def timeout(self):
        return 8.0


class SignalsTest(unittest.TestCase):

    def setUp(self):
        self._real_get = httpget.get_capped

    def tearDown(self):
        httpget.get_capped = self._real_get

    def _serve(self, responder):
        httpget.get_capped = responder

    def _all_good(self, url, *, timeout, params=None, headers=None):
        return FakeResponse(PAYLOADS[httpget.host_of(url)])

    # -- 1. schema parity ---------------------------------------------------

    def test_a_structured_event_has_the_same_keys_as_a_scripted_one(self):
        """One pipeline, one schema. Adding a field to one producer and not the
        others is exactly how this has broken before."""
        self._serve(self._all_good)
        read = signals.read_signals(Budget())
        self.assertTrue(read["events"], "the stubbed sources should produce events")

        scripted = risk_monitor.load_injected_events("hamburg")[0]
        for event in read["events"]:
            self.assertEqual(
                sorted(event.keys()), sorted(scripted.keys()),
                f"{event['event_id']} does not match the scripted event schema")

    def test_every_structured_event_is_shaped_for_the_advisor(self):
        """The advisor matches on chokepoint and reads severity and delay off
        the event, so those three have to be real values, not None."""
        self._serve(self._all_good)
        for event in signals.read_signals(Budget())["events"]:
            self.assertIn(event["severity"], config.SEVERITIES)
            self.assertIn(event["type"], config.EVENT_TYPES)
            self.assertTrue(event["chokepoint"], "an event with no chokepoint moves nothing")
            self.assertEqual(event["origin"], "live")
            low, high = event["expected_delay_days"]
            self.assertLessEqual(low, high)

    # -- 2. what the thresholds actually decide -----------------------------

    def test_readings_are_classified_by_threshold_and_quiet_ones_produce_nothing(self):
        self._serve(self._all_good)
        events = {e["event_id"]: e for e in signals.read_signals(Budget())["events"]}
        # 52 kn over Hamburg is storm force; 18 kn over Antwerp is a normal day.
        self.assertEqual(events["EVT-WX-HAM"]["severity"], "high")
        self.assertEqual(events["EVT-WX-RTM"]["severity"], "low")
        self.assertNotIn("EVT-WX-ANR", events)
        self.assertNotIn("EVT-WX-FOS", events)
        # 7.2 m off the Cape is the worst band; 1.1 m at Suez is nothing.
        self.assertEqual(events["EVT-SEA-COGH"]["severity"], "high")
        self.assertNotIn("EVT-SEA-SUEZ", events)

    def test_an_event_far_from_every_corridor_is_dropped(self):
        """A magnitude 7.4 in the South Pacific is real and is not this board's
        problem. Attaching it to a lane would be inventing exposure."""
        self._serve(self._all_good)
        events = signals.read_signals(Budget())["events"]
        self.assertIn("EVT-QUAKE-SUEZ", [e["event_id"] for e in events])
        self.assertEqual([e for e in events if "South Pacific" in e["summary"]], [])
        self.assertEqual([e for e in events if "far away" in e["title"]], [])

    def test_prose_goes_to_the_classifier_rather_than_becoming_an_event(self):
        """A tariff filing is a headline-shaped thing. It must reach the model,
        not be waved through as a pre-classified event."""
        self._serve(self._all_good)
        read = signals.read_signals(Budget())
        titles = [item["title"] for item in read["items"]]
        self.assertIn("Modification of Section 301 tariffs", titles)
        self.assertNotIn("Modification of Section 301 tariffs",
                         [e["title"] for e in read["events"]])

    # -- 3. the tier line ---------------------------------------------------

    def test_a_context_source_never_produces_an_event(self):
        """The second tier is honest only while it stays inert. The FX rate and
        a storm over a US port are shown; they decide nothing."""
        self._serve(self._all_good)
        for spec in signals.SIGNAL_SOURCES:
            if spec["tier"] != "context":
                continue
            result = spec["fn"](8.0) or {}
            self.assertEqual(result.get("events") or [], [],
                             f"{spec['id']} is a context source and emitted an event")
            self.assertEqual(result.get("items") or [], [],
                             f"{spec['id']} is a context source and queued an item")
            self.assertTrue(result.get("context"),
                            f"{spec['id']} is a context source and showed nothing")

    def test_context_is_carried_separately_from_events(self):
        self._serve(self._all_good)
        context = signals.read_signals(Budget())["context"]
        self.assertEqual(context["fx"]["base"], "EUR")
        self.assertEqual(len(context["fx"]["pairs"]), 3)
        self.assertEqual(context["hk_warnings"][0]["code"], "TC8NE")
        self.assertEqual(context["us_alerts"][0]["event"], "Hurricane Warning")

    # -- 4. fail-soft -------------------------------------------------------

    def test_a_source_that_is_down_is_reported_and_the_rest_still_read(self):
        import requests

        def one_host_down(url, *, timeout, params=None, headers=None):
            host = httpget.host_of(url)
            if host == "earthquake.usgs.gov":
                raise requests.ConnectionError(
                    "HTTPSConnectionPool(host='earthquake.usgs.gov', port=443): Max retries "
                    "exceeded with url: /fdsnws/event/1/query (Caused by "
                    "NameResolutionError(\"Failed to resolve 'earthquake.usgs.gov'\"))")
            return FakeResponse(PAYLOADS[host])

        self._serve(one_host_down)
        read = signals.read_signals(Budget())
        by_name = {e["name"]: e for e in read["entries"]}
        down = by_name["USGS: seismic [hazard]"]
        self.assertEqual(down["status"], "failed")
        # One readable line naming the host, not a connection-pool stack trace:
        # a demo operator needs to know which source is down, at a glance.
        self.assertIn("DNS lookup failed", down["detail"])
        self.assertIn("earthquake.usgs.gov", down["detail"])
        self.assertLess(len(down["detail"]), 140)
        self.assertTrue(read["events"], "the sources that were up should still have read")

    def test_a_source_that_answers_with_the_wrong_shape_fails_alone(self):
        """The likeliest real failure is not a dead host, it is a live one that
        has quietly reshaped its response."""
        def reshaped(url, *, timeout, params=None, headers=None):
            host = httpget.host_of(url)
            if host == "api.frankfurter.app":
                return FakeResponse({"unexpected": True})
            if host == "api.open-meteo.com":
                return FakeResponse("this is not json at all")
            return FakeResponse(PAYLOADS[host])

        self._serve(reshaped)
        read = signals.read_signals(Budget())
        by_name = {e["name"]: e for e in read["entries"]}
        self.assertEqual(by_name["Open-Meteo: port weather [weather]"]["status"], "failed")
        # Frankfurter degrades to zero pairs rather than failing, which is the
        # right answer for a source whose reply parsed but said nothing.
        self.assertIn(by_name["Frankfurter: ECB reference rates [markets]"]["status"],
                      {"ok", "failed"})
        self.assertTrue(any(e["status"] == "ok" for e in read["entries"]))

    def test_every_source_is_accounted_for_even_when_the_budget_is_spent(self):
        class Spent(Budget):
            def spent(self):
                return True

        read = signals.read_signals(Spent())
        self.assertEqual(len(read["entries"]), len(signals.SIGNAL_SOURCES))
        self.assertTrue(all(e["status"] == "skipped" for e in read["entries"]))
        self.assertEqual(read["events"], [])


class SourceRosterTest(unittest.TestCase):
    """The count on screen is the one an audience checks. It has to be of what
    was attempted, and it has to be the same number everywhere."""

    def test_every_configured_source_is_listed_exactly_once(self):
        listed = risk_monitor.expected_sources()
        names = [s["name"] for s in listed]
        self.assertEqual(len(names), len(set(names)), "a source is listed twice")
        self.assertEqual(
            len(names),
            len(config.GDELT_QUERIES) + len(config.RSS_FEEDS)
            + len(config.RHINE_GAUGES) + len(signals.SIGNAL_SOURCES))
        self.assertEqual(risk_monitor.source_count(), len(names))

    def test_the_families_add_up_to_the_source_count(self):
        entries = [dict(spec, status="ok", items=0, detail="", language=None)
                   for spec in risk_monitor.expected_sources()]
        rows = risk_monitor.family_summary(entries)
        self.assertEqual(sum(row["total"] for row in rows), risk_monitor.source_count())
        self.assertTrue(all(row["label"] for row in rows))

    def test_the_scripted_scenario_is_never_counted_as_a_live_source(self):
        """The whole point of the number is that it is checkable. A scripted
        event reporting itself as a source would inflate both halves of it."""
        entries = [dict(spec, status="ok", items=0, detail="", language=None)
                   for spec in risk_monitor.expected_sources()]
        entries.append({"name": "scenario: Hamburg port strike (scripted)", "status": "ok",
                        "items": 1, "detail": "", "family": "news", "tier": "lane",
                        "language": None})
        rows = risk_monitor.family_summary(entries)
        self.assertEqual(sum(row["total"] for row in rows), risk_monitor.source_count())

    def test_a_context_source_is_grouped_apart_from_the_lane_sources(self):
        by_name = {s["name"]: s for s in risk_monitor.expected_sources()}
        for spec in signals.SIGNAL_SOURCES:
            listed = by_name[f"{spec['name']} [{spec['family']}]"]
            self.assertEqual(listed["tier"], spec["tier"])
            if spec["tier"] == "context":
                self.assertTrue(listed["family"].endswith("-context"))


if __name__ == "__main__":
    unittest.main()
