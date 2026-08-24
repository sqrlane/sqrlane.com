"""Lanewatch works through the TMS. This file holds that claim up.

The product statement is that the agents do not run beside the forwarder's
system of record - they run on it: bookings are read out of the TMS, every
decision is written back into it, and a person approves the write. That is said
on the landing page, in the dashboard, in the whitepaper and out loud in the
demo, so it needs something better than good intentions behind it.

Two kinds of check, the same split the sending test uses:

  * Structural - there is exactly one door to the book. Every .py under src/ is
    parsed, and if anything except the connector reads the shipments file
    directly, this fails and names the file and line. A second door is how "the
    board is the TMS's book" quietly stops being true.
  * Behavioural - a full offline cycle is run, and every action the three live
    Workers took is checked for a matching TMS write-back, named by the Worker
    that produced it and queued behind a person.

What this deliberately does NOT assert: that a TMS was contacted. It was not.
The connector is a demo one and every check below expects it to say so.

Run it:

    python -m unittest discover -s tests
"""

import ast
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"

# The connector owns the read. config names the path; nothing else may touch it.
MAY_READ_THE_BOOK = {"tms.py", "config.py"}


def python_files():
    return sorted(p for p in SRC.rglob("*.py") if "__pycache__" not in p.parts)


class OneDoorToTheBook(unittest.TestCase):
    """Structural: the bookings can only come in one way."""

    def test_only_the_connector_reads_the_shipments_file(self):
        """Passing the path to a call is reading it. Naming it is not.

        app.py names the file in /api/health to report whether the deploy
        bundled data/ at all, which is a question about files rather than about
        bookings. Opening it anywhere outside the connector is the thing that
        matters, so that is what this looks for.
        """
        offences = []
        for path in python_files():
            if path.name in MAY_READ_THE_BOOK:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                passed = list(node.args) + [kw.value for kw in node.keywords]
                for arg in passed:
                    if isinstance(arg, ast.Attribute) and arg.attr == "SHIPMENTS_FILE":
                        offences.append(f"{path.name}:{node.lineno} opens SHIPMENTS_FILE")

        self.assertEqual(offences, [], "\n".join([
            "",
            "Something other than the connector is reading the book directly:",
            *(f"    {o}" for o in offences),
            "",
            "Bookings come out of the TMS through tms.read_bookings(), and that is the",
            "whole point - one door in means the day the connector talks to a real TMS,",
            "every component follows. A second door is how that quietly stops being true.",
        ]))

    def test_the_advisor_gets_its_shipments_from_the_connector(self):
        from src import route_advisor
        bookings = route_advisor.load_shipments()
        self.assertGreater(len(bookings), 0, "No bookings means this tests nothing.")
        for booking in bookings:
            with self.subTest(booking=booking["id"]):
                self.assertIn("demo", booking["source_system"].lower(),
                              "Every record must carry the system it came from - and in "
                              "this build that system is the demo connector.")
                self.assertEqual(booking["record_status"], "synced")


class EveryActionLandsOnTheRecord(unittest.TestCase):
    """Behavioural: what the Workers did, expressed as changes to TMS records."""

    @classmethod
    def setUpClass(cls):
        from src import orchestrator, tms
        cls.tms = tms
        cls.result = orchestrator.run_cycle(live=False, inject=True, use_llm=False)
        cls.link = cls.result["tms"]
        cls.operations = cls.link["writebacks"]

    def test_the_cycle_queued_something_to_check(self):
        self.assertGreater(len(self.operations), 0,
                           "The injected strike actions bookings, so write-backs should be "
                           "queued. None means this file is testing nothing.")

    def test_the_board_is_the_book(self):
        self.assertEqual(self.link["bookings_read"], len(self.result["shipments"]),
                         "Every card on the board is one booking read out of the TMS.")
        for card in self.result["shipments"]:
            with self.subTest(booking=card["id"]):
                self.assertEqual(card["source_system"], self.tms.CONNECTOR_NAME)

    def test_all_three_live_workers_write_to_the_tms(self):
        """The claim is that the agents work *in* the system of record.

        A run where only the Routing Worker wrote anything would still look fine
        on screen while the claim quietly narrowed to one agent.
        """
        wrote = {op["agent"] for op in self.operations}
        for agent in ("Risk Worker", "Routing Worker", "Comms Worker"):
            with self.subTest(agent=agent):
                self.assertIn(agent, wrote,
                              f"{agent} produced no TMS write-back on a run that actioned "
                              f"{self.link['bookings_affected']} bookings.")

    def test_every_actioned_booking_has_a_write_back(self):
        actioned = [c["id"] for c in self.result["shipments"]
                    if (c.get("decision") or {}).get("decision") in ("reroute", "hold")]
        self.assertGreater(len(actioned), 0, "Nothing was actioned - this tests nothing.")
        written = {op["booking_ref"] for op in self.operations}
        for booking in actioned:
            with self.subTest(booking=booking):
                self.assertIn(booking, written,
                              "A decision that never reaches the TMS is a decision nobody "
                              "acts on.")

    def test_a_booking_on_plan_writes_nothing(self):
        """Silence is a real answer. A write-back for an unchanged booking is noise."""
        on_plan = [c["id"] for c in self.result["shipments"]
                   if (c.get("decision") or {}).get("decision") == "no-action"]
        self.assertGreater(len(on_plan), 0,
                           "The strike leaves some bookings alone - that is the point of "
                           "the screenplay. None means this tests nothing.")
        written = {op["booking_ref"] for op in self.operations}
        for booking in on_plan:
            with self.subTest(booking=booking):
                self.assertNotIn(booking, written)

    def test_every_write_back_names_the_worker_that_made_it(self):
        known = {a["agent"] for a in self.tms.AGENT_RECORDS}
        records = {a["record"] for a in self.tms.AGENT_RECORDS}
        for op in self.operations:
            with self.subTest(booking=op["booking_ref"], operation=op["operation"]):
                self.assertIn(op["agent"], known)
                self.assertIn(op["record"], records)
                self.assertTrue(op["changes"], "A write-back that changes nothing is not one.")

    def test_nothing_is_ever_written(self):
        """The gate, on the write side. Same rule as a drafted email."""
        for op in self.operations:
            with self.subTest(booking=op["booking_ref"], operation=op["operation"]):
                self.assertEqual(op["status"], "QUEUED - not written")
                self.assertEqual(op["approval_status"], "awaiting_approval")

    def test_the_link_says_what_it_is_everywhere_it_is_surfaced(self):
        self.assertIn("demo", (self.link["connector"] + self.link["status"]).lower())
        self.assertIn("tms", self.link["positioning"].lower(),
                      "The one-line positioning is where the product claim is written "
                      "down. It has to name the system of record.")
        self.assertIn("nothing is written", self.link["honesty"].lower())

    def test_the_board_reports_the_link_before_the_button_is_pressed(self):
        """The connection is not something a run creates. It is where the board came from."""
        from src import orchestrator
        idle = orchestrator.initial_state()
        self.assertEqual(idle["tms"]["bookings_read"], len(idle["shipments"]))
        self.assertEqual(idle["tms"]["queued"], 0,
                         "Nothing has been decided yet, so nothing can be queued.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
