"""The Rhine gauges are the one genuinely live number on /how-it-works.

Two things have to hold, and neither is obvious from reading the code:

  1. A reading is classified into the same bands the risk monitor uses. If the
     page said "normal" while the monitor was raising a medium-severity
     event off the same number, one of them would be lying.
  2. The page survives the gauge being down. PEGELONLINE is a third-party
     service with no key and no SLA, and it is being read on a public page - so
     slow, broken and absent all have to end in something readable rather than
     a stack trace or a hung request.

There is no network here. A local server stands in for PEGELONLINE, which is
enough to exercise parsing, the thresholds, concurrency, the cache and every
failure path. What it cannot prove is that the real host answers in this shape;
that needs one look at /api/gauges on a machine with outbound access.

    python -m unittest discover -s tests
"""

import http.server
import json
import socketserver
import threading
import time
import unittest
import urllib.parse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, risk_monitor  # noqa: E402


# --------------------------------------------------------------------------
# A stand-in for PEGELONLINE that can be told how to misbehave
# --------------------------------------------------------------------------

# station -> what to answer with. A float is a normal reading; anything else is
# a way of being broken.
RESPONSES: dict = {}


class _FakeGauge(http.server.BaseHTTPRequestHandler):
    def do_GET(self):                                    # noqa: N802
        # requests percent-encodes a non-ASCII station name (KÖLN) in the URL
        # path, so decode it back before looking the station up.
        station = urllib.parse.unquote(self.path.strip("/").split("/")[0])
        answer = RESPONSES.get(station, "missing")

        if answer == "missing":
            self.send_error(404)
            return
        if answer == "broken":
            self.send_error(503)
            return
        if answer == "garbage":
            body = b"<html>not json at all</html>"
        elif answer == "no-value":
            body = json.dumps({"timestamp": "2026-08-24T17:30:00+02:00"}).encode()
        else:
            body = json.dumps({"timestamp": "2026-08-24T17:30:00+02:00",
                               "value": answer, "trend": 0}).encode()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass                                             # keep the test output clean


class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class GaugeTestCase(unittest.TestCase):
    """Points the gauge reader at a local server instead of the real one."""

    @classmethod
    def setUpClass(cls):
        cls.server = _Server(("127.0.0.1", 0), _FakeGauge)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls._real_endpoint = config.PEGELONLINE_ENDPOINT
        config.PEGELONLINE_ENDPOINT = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        config.PEGELONLINE_ENDPOINT = cls._real_endpoint
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        RESPONSES.clear()


# --------------------------------------------------------------------------
# 1. The bands
# --------------------------------------------------------------------------


class TheBandsMatchTheMonitor(unittest.TestCase):
    """One table decides the bands, so the readout and the events agree."""

    KAUB = {"station": "KAUB", "name": "Kaub",
            "warn_cm": 100, "high_cm": 78, "critical_cm": 40}

    def test_each_band_including_its_exact_boundary(self):
        # A reading exactly ON a threshold is inside that band, not above it.
        cases = [
            (240, None,     "normal"),
            (101, None,     "normal"),
            (100, "low",    "watch"),        # exactly the warn level
            (79,  "low",    "watch"),
            (78,  "medium", "restricted"),   # exactly the loading threshold
            (41,  "medium", "restricted"),
            (40,  "high",   "critical"),     # exactly the critical level
            (12,  "high",   "critical"),
        ]
        for level, severity, state in cases:
            with self.subTest(level=level):
                got_sev, got_state, _delay, note = risk_monitor._gauge_state(
                    self.KAUB, level)
                self.assertEqual(got_sev, severity)
                self.assertEqual(got_state, state)
                self.assertTrue(note, "every band explains itself")

    def test_the_event_path_and_the_readout_agree(self):
        """The same number must not be 'normal' on the page and an event in the
        monitor. This is the drift the shared band table exists to prevent."""
        for level in (240, 100, 78, 40, 5):
            with self.subTest(level=level):
                severity, state, _delay, _note = risk_monitor._gauge_state(
                    self.KAUB, level)
                event = risk_monitor._rhine_event(self.KAUB, level, "2026-08-24T00:00:00Z")
                if severity is None:
                    self.assertIsNone(event, f"{level} cm reads normal, so no event")
                    self.assertEqual(state, "normal")
                else:
                    self.assertIsNotNone(event, f"{level} cm is {state}, so an event")
                    self.assertEqual(event["severity"], severity)


# --------------------------------------------------------------------------
# 2. Reading them
# --------------------------------------------------------------------------


class ReadingTheGauges(GaugeTestCase):

    def test_a_normal_river_reads_normal(self):
        RESPONSES.update({"KAUB": 214.0, "DUISBURG-RUHRORT": 385.0, "EMMERICH": 240.0})
        payload = risk_monitor.read_rhine_gauges()

        self.assertTrue(payload["ok"])
        # The default read is the panel's own selection - the three
        # reference gauges - not the monitor's wider RHINE_GAUGES list.
        self.assertEqual(len(payload["gauges"]), len(config.LANDING_GAUGES))
        kaub = payload["gauges"][0]
        self.assertEqual(kaub["station"], "KAUB")
        self.assertEqual(kaub["level_cm"], 214)
        self.assertEqual(kaub["state"], "normal")
        self.assertIsNone(kaub["severity"])
        # The thresholds travel with the reading, so the page can draw the line
        # it is being measured against without knowing config.py.
        self.assertEqual(kaub["high_cm"], 78)
        self.assertTrue(kaub["measured_at"])

    def test_a_low_river_reads_low(self):
        RESPONSES.update({"KAUB": 44.0, "DUISBURG-RUHRORT": 196.0, "EMMERICH": 51.0})
        gauges = {g["station"]: g for g in risk_monitor.read_rhine_gauges()["gauges"]}

        self.assertEqual(gauges["KAUB"]["state"], "restricted")
        self.assertEqual(gauges["DUISBURG-RUHRORT"]["state"], "restricted")
        self.assertEqual(gauges["EMMERICH"]["state"], "restricted")

    def test_readings_come_back_in_configured_order(self):
        RESPONSES.update({"KAUB": 200.0, "DUISBURG-RUHRORT": 400.0, "EMMERICH": 200.0})
        payload = risk_monitor.read_rhine_gauges()
        self.assertEqual([g["station"] for g in payload["gauges"]],
                         config.LANDING_GAUGES)

    def test_the_panel_default_and_the_wider_monitor_read_are_one_list(self):
        """The panel was designed around three readings and keeps
        showing exactly the reference gauges; the monitor reads every gauge in
        RHINE_GAUGES. The split is a parameter over one configured list, so
        the two callers cannot carry different thresholds for a station."""
        RESPONSES.update({"KAUB": 214.0, "DUISBURG-RUHRORT": 385.0, "EMMERICH": 240.0,
                          "KÖLN": 300.0, "MAINZ": 250.0, "MAXAU": 500.0})
        default = risk_monitor.read_rhine_gauges()
        self.assertEqual([g["station"] for g in default["gauges"]],
                         config.LANDING_GAUGES)

        everything = risk_monitor.read_rhine_gauges(
            stations=[g["station"] for g in config.RHINE_GAUGES])
        self.assertEqual(len(everything["gauges"]), len(config.RHINE_GAUGES))
        koeln = {g["station"]: g for g in everything["gauges"]}["KÖLN"]
        self.assertTrue(koeln["ok"])
        self.assertEqual(koeln["state"], "normal")


# --------------------------------------------------------------------------
# 3. Failing softly
# --------------------------------------------------------------------------


class WhenTheGaugeIsDown(GaugeTestCase):

    def test_one_bad_gauge_does_not_take_the_others_with_it(self):
        RESPONSES.update({"KAUB": 214.0, "DUISBURG-RUHRORT": "broken", "EMMERICH": 240.0})
        payload = risk_monitor.read_rhine_gauges()

        self.assertTrue(payload["ok"], "two good readings are still a reading")
        gauges = {g["station"]: g for g in payload["gauges"]}
        self.assertTrue(gauges["KAUB"]["ok"])
        self.assertFalse(gauges["DUISBURG-RUHRORT"]["ok"])
        self.assertTrue(gauges["DUISBURG-RUHRORT"]["error"], "and it says why")
        # The broken one still names itself, so the page can render three cells.
        self.assertEqual(gauges["DUISBURG-RUHRORT"]["name"], "Duisburg-Ruhrort")

    def test_every_shape_of_bad_answer_is_survivable(self):
        for bad in ("broken", "garbage", "no-value", "missing"):
            with self.subTest(answer=bad):
                RESPONSES.clear()
                RESPONSES.update({"KAUB": bad, "DUISBURG-RUHRORT": bad, "EMMERICH": bad})
                payload = risk_monitor.read_rhine_gauges()
                self.assertFalse(payload["ok"])
                self.assertEqual(len(payload["gauges"]), 3)
                self.assertTrue(all(g["error"] for g in payload["gauges"]))

    def test_the_whole_source_being_gone_is_not_an_exception(self):
        """Nothing listening at all - the case where the host is unreachable."""
        real = config.PEGELONLINE_ENDPOINT
        config.PEGELONLINE_ENDPOINT = "http://127.0.0.1:1"     # nothing is there
        try:
            payload = risk_monitor.read_rhine_gauges()
        finally:
            config.PEGELONLINE_ENDPOINT = real
        self.assertFalse(payload["ok"])
        self.assertEqual(len(payload["gauges"]), 3)


# --------------------------------------------------------------------------
# 4. The endpoint the page actually calls
# --------------------------------------------------------------------------


class TheEndpoint(GaugeTestCase):
    """Called directly rather than over HTTP, so the suite stays dependency-free."""

    def setUp(self):
        super().setUp()
        from src import app as app_module
        self.app_module = app_module
        app_module._gauge_cache.update(at=0.0, payload=None)

    def _call(self):
        response = self.app_module.gauges()
        return response, json.loads(bytes(response.body))

    def test_it_serves_a_live_reading_and_allows_caching(self):
        RESPONSES.update({"KAUB": 214.0, "DUISBURG-RUHRORT": 385.0, "EMMERICH": 240.0})
        response, body = self._call()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(body["ok"])
        self.assertFalse(body["stale"])
        self.assertIn("s-maxage", response.headers["cache-control"])

    def test_a_second_call_is_served_from_the_cache(self):
        RESPONSES.update({"KAUB": 214.0, "DUISBURG-RUHRORT": 385.0, "EMMERICH": 240.0})
        self._call()
        # If this were re-read, the new value would show. It must not be.
        RESPONSES.update({"KAUB": 999.0})
        _response, body = self._call()
        self.assertEqual(body["gauges"][0]["level_cm"], 214)

    def test_a_dead_source_serves_the_last_good_reading_marked_stale(self):
        RESPONSES.update({"KAUB": 214.0, "DUISBURG-RUHRORT": 385.0, "EMMERICH": 240.0})
        self._call()
        # Age the reading past the cache window. Not `at = 0.0`: monotonic()
        # counts from an arbitrary epoch - system boot on Linux - so on a
        # machine up for less than GAUGE_CACHE_SECONDS, zero is INSIDE the
        # window and the endpoint rightly serves the cached reading as fresh.
        # That made this test pass or fail on the host's uptime.
        self.app_module._gauge_cache["at"] = (
            time.monotonic() - config.GAUGE_CACHE_SECONDS - 1)
        RESPONSES.update({"KAUB": "broken", "DUISBURG-RUHRORT": "broken",
                          "EMMERICH": "broken"})

        response, body = self._call()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(body["stale"], "the reading is old, and says so")
        self.assertEqual(body["gauges"][0]["level_cm"], 214)
        self.assertEqual(response.headers["cache-control"], "no-store",
                         "a stale answer must not be cached on top of the failure")

    def test_a_dead_source_with_no_history_still_answers_200(self):
        RESPONSES.update({"KAUB": "broken", "DUISBURG-RUHRORT": "broken",
                          "EMMERICH": "broken"})
        response, body = self._call()

        self.assertEqual(response.status_code, 200, "the page must never see a 500")
        self.assertFalse(body["ok"])
        self.assertEqual(response.headers["cache-control"], "no-store",
                         "a failure must not be cached for the next five minutes")

    def test_an_unexpected_exception_is_still_a_200(self):
        """The catch-all matters: whatever goes wrong inside, the page gets JSON."""
        def explode():
            raise RuntimeError("something nobody thought of")

        original = risk_monitor.read_rhine_gauges
        risk_monitor.read_rhine_gauges = explode
        try:
            response, body = self._call()
        finally:
            risk_monitor.read_rhine_gauges = original
        self.assertEqual(response.status_code, 200)
        self.assertFalse(body["ok"])


if __name__ == "__main__":
    unittest.main()


class TheEventQuotesTheThresholdItCrossed(unittest.TestCase):
    """Witnessed on the first real six-gauge read: Maxau at 370 cm (warn band,
    380) was captioned "at or below the 320 cm restriction threshold" - the
    medium band it had NOT crossed. The band was right, the sentence was
    false. The quoted number must be the threshold the walk actually stopped
    at, for every band."""

    def test_every_band_quotes_its_own_threshold(self):
        gauge = {"station": "TEST", "name": "Test",
                 "warn_cm": 380, "high_cm": 320, "critical_cm": 250}
        for level, crossed in ((370, 380), (300, 320), (200, 250)):
            event = risk_monitor._rhine_event(gauge, float(level), "2026-08-28T00:00:00Z")
            self.assertIn(f"at or below the {crossed} cm", event["reasoning"],
                          f"level {level} should quote the {crossed} cm band")
            self.assertIn(f"restriction threshold {crossed} cm", event["summary"])
            self.assertGreaterEqual(crossed, level,
                                    "a quoted threshold below the level is a false sentence")

    def test_a_normal_level_still_produces_no_event(self):
        gauge = {"station": "TEST", "name": "Test",
                 "warn_cm": 380, "high_cm": 320, "critical_cm": 250}
        self.assertIsNone(risk_monitor._rhine_event(gauge, 400.0, "2026-08-28T00:00:00Z"))
