"""A slow source must not be able to stall a demo. This file proves it can't.

The failure mode that actually threatens a live demo is not a dead source -
that fails fast - but a slow one, and there are two kinds:

  1. **It hangs.** Accepts the connection and never replies. requests' own
     timeout catches this.
  2. **It trickles.** Replies forever, one byte at a time. This one is nastier,
     because requests' timeout is measured *between bytes*, not in total: a
     source sending a byte a second never trips an eight-second timeout, so the
     call never returns and the thread running it never ends. A single such feed
     hung the whole run indefinitely.

So every news fetch goes through `_get_capped()`, which adds a total deadline
and a size cap on top of the timeout. Two details there are load-bearing and
easy to undo by accident: a deadline checked *between* chunks never fires,
because the read blocks until its chunk is full; and `response.close()` alone
does not unblock a read already in flight - the socket has to be shut down.

The tests below run against real sockets on localhost, with the budget patched
down so the suite stays fast. The documented figures - a 25-second budget for
the whole pull, 8 seconds per request - are asserted separately, because the
mechanism working and the numbers being what the docs say are two claims.
"""

import socket
import threading
import time
import unittest
from unittest import mock

import requests

from src import config, risk_monitor


class _SlowServer:
    """A localhost server that is slow in one of the two ways that matter."""

    def __init__(self, mode):
        self.mode = mode                      # "trickle" or "hang"
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(8)
        self.port = self.sock.getsockname()[1]
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.port}/feed.xml"

    def _serve(self):
        self.sock.settimeout(0.25)
        while not self.stop.is_set():
            try:
                conn, _ = self.sock.accept()
            except (socket.timeout, OSError):
                continue
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn):
        try:
            conn.recv(4096)
            if self.mode == "hang":
                # Accepted, and then nothing. Ever.
                while not self.stop.is_set():
                    time.sleep(0.1)
                return
            # Trickle: a valid response that promises far more than it sends,
            # one byte at a time, for as long as anyone is listening.
            conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/xml\r\n"
                         b"Content-Length: 1000000\r\n\r\n")
            while not self.stop.is_set():
                conn.sendall(b"<")
                time.sleep(0.2)
        except OSError:
            pass                                # the client gave up, which is the point
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def close(self):
        self.stop.set()
        try:
            self.sock.close()
        except OSError:
            pass


class ACappedGetAlwaysEnds(unittest.TestCase):
    """The mechanism, against real sockets."""

    def test_a_trickling_source_is_cut_off(self):
        server = _SlowServer("trickle")
        self.addCleanup(server.close)
        started = time.monotonic()
        with self.assertRaises(requests.RequestException) as caught:
            risk_monitor._get_capped(server.url, timeout=1)
        elapsed = time.monotonic() - started

        self.assertIsInstance(caught.exception, risk_monitor.SourceTooSlow,
                              "A trickle is the case the total deadline exists for. "
                              "Anything else means the watchdog did not fire.")
        self.assertLess(elapsed, 6, f"Took {elapsed:.1f}s against a 1s deadline. The "
                                    "watchdog has to shut the socket down - closing the "
                                    "response does not unblock a read in flight.")

    def test_a_hanging_source_is_cut_off(self):
        server = _SlowServer("hang")
        self.addCleanup(server.close)
        started = time.monotonic()
        with self.assertRaises(requests.RequestException):
            risk_monitor._get_capped(server.url, timeout=1)
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 6, f"Took {elapsed:.1f}s against a 1s timeout.")


class TheScenarioSurvivesASlowWorld(unittest.TestCase):
    """The whole point: the demo still plays when every source is unreachable."""

    def test_a_run_ends_inside_its_budget_with_the_scenario_intact(self):
        server = _SlowServer("trickle")
        self.addCleanup(server.close)
        feeds = [{"name": f"slow-{i}", "url": server.url, "language": "de",
                  "region": "test"} for i in range(4)]

        started = time.monotonic()
        with mock.patch.object(config, "RSS_FEEDS", feeds), \
             mock.patch.object(config, "GDELT_QUERIES", []), \
             mock.patch.object(config, "RHINE_GAUGES", []), \
             mock.patch.object(config, "HTTP_TIMEOUT_SECONDS", 1), \
             mock.patch.object(config, "LIVE_PULL_BUDGET_SECONDS", 3):
            result = risk_monitor.run(live=True, inject=True, use_llm=False, verbose=False)
        elapsed = time.monotonic() - started

        self.assertLess(elapsed, 20, f"The run took {elapsed:.1f}s against a 3s budget. "
                                     "A slow source is stalling the cycle.")
        self.assertTrue(result["events"],
                        "Every live source was unreachable, so the scripted scenario is "
                        "all that is left - and it has to still be there. A demo that "
                        "goes blank because a feed is slow is the failure this prevents.")
        self.assertTrue(any(s["status"] != "ok" for s in result["sources"]),
                        "Nothing was recorded as failed or skipped, so the slow sources "
                        "were not actually exercised.")


class TheDocumentedBudgetIsTheRealOne(unittest.TestCase):
    """The numbers the README and the landing page quote, read from config."""

    def test_the_figures_on_the_page_match_the_code(self):
        # Serverless runs deliberately tighten both; these are the local defaults
        # the pages quote, so the check is skipped rather than wrong there.
        if config.SERVERLESS:
            self.skipTest("Serverless tightens both budgets by design.")
        self.assertEqual(config.LIVE_PULL_BUDGET_SECONDS, 25,
                         "The landing page and CLAUDE.md quote a 25s hard budget.")
        self.assertEqual(config.HTTP_TIMEOUT_SECONDS, 8,
                         "The landing page and CLAUDE.md quote an 8s per-request timeout.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
