"""The Planner sweeps the forward book before departure - and stays honest.

ROADMAP-PRE-DEPARTURE.md designed the Worker; this build is rung two of its
own proof ladder: an authored scenario, tagged SCRIPTED like Inbox and
Customs. The claims it makes on screen are the ones this file holds:

  * Every sweep ends in exactly one of three states per forward booking -
    act now, tripwire armed, or stand down - and a stand-down is a recorded
    answer with reasoning, never an omission.
  * Nothing leaves without a person. Every proposal is DRAFT - not sent or
    QUEUED - not written, awaiting approval; a stand-down queues nothing,
    which is the forward-book mirror of "an on-plan booking has no
    write-back".
  * A tripwire is a condition over a reading the sources already band. The
    Rhine one quotes the same Kaub threshold config.RHINE_GAUGES carries, so
    the Planner and the risk monitor cannot disagree about the number.
  * The scenarios disagree. The same three forward bookings sweep into a
    different three-state pattern under each disruption - the pool rule
    ("if two scenarios produce the same pattern, one is redundant"),
    applied to the sweep.
  * The Worker is honestly scripted: mode "scripted" in the roster, the
    panel says its content is authored, and the run still reports exactly
    three live Workers - the Planner is not a quiet fourth.

Everything runs offline and deterministic - no network, no model, no key.
"""

import re
import unittest
from datetime import date, timedelta

from src import config, orchestrator, roster

SCENARIOS = {
    "hamburg": {"id": "hamburg", "name": "Hamburg port strike"},
    "redsea": {"id": "redsea", "name": "Red Sea closure"},
    "rhine": {"id": "rhine", "name": "Rhine low water"},
    "france": {"id": "france", "name": "Southern France wildfire"},
}

STATES = ("act_now", "tripwire_armed", "stand_down")
GATED = ("DRAFT - not sent", "QUEUED - not written")


def panel(scenario_id):
    return roster.planner_panel(scenario_id, SCENARIOS.get(scenario_id))


class TheSweepEndsInExactlyThreeStates(unittest.TestCase):
    """One full offline cycle; the panel rides on every card, identically."""

    @classmethod
    def setUpClass(cls):
        cls.result = orchestrator.run_cycle(live=False, inject=True, use_llm=False)
        cls.panels = [s["roster"]["planner"] for s in cls.result["shipments"]]

    def test_the_panel_is_on_every_card_and_board_level(self):
        self.assertGreater(len(self.panels), 0)
        first = self.panels[0]
        for p in self.panels[1:]:
            self.assertEqual(p, first,
                             "The Planner reads the forward book, not the selected "
                             "shipment - the panel must not vary by card.")

    def test_every_item_lands_in_one_of_the_three_states(self):
        for item in self.panels[0]["items"]:
            with self.subTest(ref=item["ref"]):
                self.assertIn(item["state"], STATES)

    def test_stand_down_is_a_recorded_answer(self):
        # The state the demo is proudest of: not acting, with the reasoning
        # written down. An empty reasoning would make it an omission.
        for item in self.panels[0]["items"]:
            with self.subTest(ref=item["ref"], state=item["state"]):
                for field in ("exposure", "timing", "reasoning"):
                    self.assertTrue(str(item.get(field) or "").strip(),
                                    f"{field} must be recorded whatever the state.")

    def test_the_headline_counts_match_the_items(self):
        p = self.panels[0]
        for state, label in (("act_now", "act now"), ("tripwire_armed", "tripwire"),
                             ("stand_down", "standing down")):
            n = sum(1 for i in p["items"] if i["state"] == state)
            self.assertIn(str(n), p["headline"],
                          f"The headline must count {label} from the items.")


class NothingLeavesWithoutAPerson(unittest.TestCase):
    """The same gate as every other Worker, forward book included."""

    def test_every_proposal_is_gated_in_every_scenario(self):
        for sid in SCENARIOS:
            for item in panel(sid)["items"]:
                for proposal in item["proposals"]:
                    with self.subTest(scenario=sid, ref=item["ref"],
                                      kind=proposal["kind"]):
                        self.assertIn(proposal["status"], GATED)
                        self.assertEqual(proposal["approval_status"],
                                         "awaiting_approval")

    def test_action_produces_proposals_and_stand_down_produces_none(self):
        produced = 0
        for sid in SCENARIOS:
            for item in panel(sid)["items"]:
                with self.subTest(scenario=sid, ref=item["ref"]):
                    if item["state"] == "stand_down":
                        self.assertEqual(item["proposals"], [],
                                         "A stand-down queues nothing - the "
                                         "forward-book mirror of an on-plan "
                                         "booking having no write-back.")
                    else:
                        self.assertGreater(len(item["proposals"]), 0,
                                           "Acting or arming with nothing on the "
                                           "booking is a decision that lands "
                                           "nowhere.")
                        produced += 1
        self.assertGreater(produced, 0, "No scenario produced action items - "
                                        "this file would be testing nothing.")

    def test_a_tripwire_holds_its_prepared_move_as_a_draft(self):
        for sid in ("hamburg", "rhine"):
            armed = [i for i in panel(sid)["items"] if i["state"] == "tripwire_armed"]
            self.assertGreater(len(armed), 0, f"{sid} should arm a tripwire.")
            for item in armed:
                self.assertIsNotNone(item["tripwire"])
                kinds = {p["kind"]: p for p in item["proposals"]}
                held = [p for p in item["proposals"] if p["status"] == "DRAFT - not sent"]
                self.assertGreater(len(held), 0,
                                   "The prepared move must exist as a held draft - "
                                   "that is what makes the wait managed.")
                self.assertTrue(any(p["status"] == "QUEUED - not written"
                                    for p in kinds.values()),
                                "The tripwire condition itself is a write-back to "
                                "the booking, queued like any other.")


class TheTripwireIsAConditionTheSourcesAlreadyBand(unittest.TestCase):
    """Deciding when to decide, mechanically - over readings that already exist."""

    def test_the_rhine_tripwire_quotes_the_kaub_threshold_from_config(self):
        kaub = next(g for g in config.RHINE_GAUGES if g["station"] == "KAUB")
        armed = [i for i in panel("rhine")["items"] if i["state"] == "tripwire_armed"]
        self.assertEqual(len(armed), 1)
        condition = armed[0]["tripwire"]["condition"]
        self.assertIn(f"{kaub['high_cm']} cm", condition,
                      "The tripwire must quote the same threshold the risk monitor "
                      "bands, or the two halves of the product disagree about one "
                      "number.")
        # And no other number in the condition pretends to be a threshold.
        quoted = [int(n) for n in re.findall(r"(\d+) cm", condition)]
        self.assertEqual(quoted, [kaub["high_cm"]])

    def test_the_hamburg_tripwire_is_over_the_events_own_window(self):
        armed = [i for i in panel("hamburg")["items"] if i["state"] == "tripwire_armed"]
        self.assertEqual(len(armed), 1)
        self.assertIn("72 hours", armed[0]["tripwire"]["condition"],
                      "The strike tripwire watches the episode's expected duration, "
                      "which is already on the event record.")


class TheScenariosDisagree(unittest.TestCase):
    """One forward book, different disruptions, different three-state patterns."""

    def test_no_two_active_scenarios_sweep_to_the_same_pattern(self):
        patterns = {sid: tuple(i["state"] for i in panel(sid)["items"])
                    for sid in ("hamburg", "redsea", "rhine")}
        seen = {}
        for sid, pat in patterns.items():
            self.assertNotIn(pat, seen,
                             f"{sid} and {seen.get(pat)} sweep to the same pattern "
                             f"{pat} - one of them is redundant.")
            seen[pat] = sid

    def test_a_quiet_board_stands_everything_down_and_queues_nothing(self):
        for sid in (None, "france"):
            p = roster.planner_panel(sid, SCENARIOS.get(sid))
            with self.subTest(scenario=sid):
                self.assertTrue(all(i["state"] == "stand_down" for i in p["items"]))
                self.assertEqual(sum(len(i["proposals"]) for i in p["items"]), 0)


class TheWorkerIsHonestlyScripted(unittest.TestCase):
    """SCRIPTED is the tag, and the panel says so in its own words."""

    def test_the_roster_entry_is_scripted(self):
        entry = next(w for w in roster.ROSTER if w["id"] == "planner")
        self.assertEqual(entry["mode"], "scripted")

    def test_the_panel_admits_it_is_authored_and_sends_nothing(self):
        note = panel("hamburg")["note"].lower()
        for word in ("authored", "scripted"):
            self.assertIn(word, note)
        self.assertIn("waits for a person", note)

    def test_the_run_still_reports_exactly_three_live_workers(self):
        result = orchestrator.run_cycle(live=False, inject=True, use_llm=False)
        live = [w for w in result["workers"] if w.get("mode") == "live"]
        self.assertEqual([w["id"] for w in live], ["risk", "routing", "comms"],
                         "The Planner must never appear as a quiet fourth live "
                         "Worker.")
        planner = next(w for w in result["workers"] if w["id"] == "planner")
        self.assertEqual(planner["mode"], "scripted")
        self.assertTrue(planner["summary"].startswith("authored sweep"),
                        "The run summary carries the honesty before the counts.")


class TheForwardBookIsForward(unittest.TestCase):
    """Pre-departure by construction, and never confusable with the board."""

    def test_refs_never_collide_with_the_in_transit_board(self):
        for item in panel("hamburg")["items"]:
            self.assertFalse(item["ref"].startswith("SHP-"),
                             "A forward record wearing a board id would blur the "
                             "jurisdiction line the roadmap draws.")

    def test_every_etd_is_in_the_future_with_cutoff_three_days_before(self):
        today = date.today()
        for item in panel("hamburg")["items"]:
            etd = date.fromisoformat(item["etd"])
            cutoff = date.fromisoformat(item["cutoff"])
            with self.subTest(ref=item["ref"]):
                self.assertGreater(etd, today,
                                   "A departed booking belongs to the in-transit "
                                   "advisor, not the Planner.")
                self.assertEqual(cutoff, etd - timedelta(days=3),
                                 "Cut-off follows the Booking Worker's own "
                                 "convention.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
