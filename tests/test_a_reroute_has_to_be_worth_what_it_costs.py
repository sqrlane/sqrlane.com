"""What the cost weighting claims, held to it.

The advisor used to rank options by days and break ties on a relative cost
index. That answers "which lands soonest", which is not the question anyone is
asking: a cheaper routing that lands late is usually the expensive option. This
suite holds the four things that can quietly stop being true.

The fourth is here because it nearly got away. Pricing the options changed a
documented scenario outcome on a 3% margin - one authored input of mine against
a screenplay that was deliberately composed. The board's decisions are the spec;
a change to the cost model that moves them is a change to the product, and it
should fail here rather than be noticed in front of an audience.
"""
import json
import unittest
from collections import Counter

from src import route_advisor as ra, tms


def _events(scenario_id):
    with open("data/scenarios.json", encoding="utf-8") as fh:
        data = json.load(fh)
    return next(s for s in data["scenarios"] if s["id"] == scenario_id)["events"]


class TheArithmetic(unittest.TestCase):
    def setUp(self):
        self.routes = ra.load_routes()
        self.ships = {s["id"]: s for s in tms.read_bookings()}

    def test_slack_absorbs_the_first_days_before_anything_is_billable(self):
        """Days of delay are not days late. Only the spill past slack costs."""
        ship = dict(self.ships["SHP-001"], deadline_slack_days=4)
        candidate = {"added_cost_index": 0, "projected_delay_days": [0, 3],
                     "discharge_port": "HAM"}
        priced = ra.cost_of(candidate, ship, {"discharge_port": "HAM"})
        self.assertEqual(priced["days_late"], 0)
        self.assertEqual(priced["delay_cost_eur"], 0)
        self.assertEqual(priced["breach_cost_eur"], 0,
                         "the breach cliff must not fire while the date still holds")

    def test_the_breach_cliff_fires_once_not_per_day(self):
        ship = dict(self.ships["SHP-001"], deadline_slack_days=4)
        c = {"added_cost_index": 0, "projected_delay_days": [0, 9], "discharge_port": "HAM"}
        priced = ra.cost_of(c, ship, {"discharge_port": "HAM"})
        terms = ship["commercial"]
        self.assertEqual(priced["days_late"], 5)
        self.assertEqual(priced["delay_cost_eur"], 5 * terms["late_eur_per_day"])
        self.assertEqual(priced["breach_cost_eur"], terms["breach_eur"])
        self.assertEqual(priced["exposure_eur"],
                         priced["freight_delta_eur"] + priced["delay_cost_eur"]
                         + priced["breach_cost_eur"] + priced["transfer_cost_eur"])

    def test_the_cold_chain_transfer_is_priced_only_when_the_port_actually_moves(self):
        """It is a handling cost, so it applies to a handling, not to a cargo type."""
        pharma = self.ships["SHP-002"]
        self.assertTrue(pharma.get("cold_chain"))
        same = ra.cost_of({"added_cost_index": 0, "projected_delay_days": [0, 0],
                           "discharge_port": "HAM"}, pharma, {"discharge_port": "HAM"})
        moved = ra.cost_of({"added_cost_index": 0, "projected_delay_days": [0, 0],
                            "discharge_port": "RTM"}, pharma, {"discharge_port": "HAM"})
        self.assertEqual(same["transfer_cost_eur"], 0)
        self.assertEqual(moved["transfer_cost_eur"], pharma["commercial"]["transfer_risk_eur"])


class EveryCandidateIsPriced(unittest.TestCase):
    """Schema parity. Adding a field to one producer and not the others is the
    way this repo has broken before, three times."""

    MONEY = ("freight_delta_eur", "days_late", "delay_cost_eur",
             "breach_cost_eur", "transfer_cost_eur", "exposure_eur")

    def test_current_and_alternates_all_carry_the_money_fields(self):
        routes, events = ra.load_routes(), _events("hamburg")
        for ship in tms.read_bookings():
            a = ra.build_assessment(ship, routes, events)
            for candidate in a["candidates"]:
                for key in self.MONEY:
                    self.assertIn(key, candidate,
                                  f"{ship['id']} {candidate['route_id']} is missing {key}")
                    self.assertIsInstance(candidate[key], int)

    def test_every_booking_carries_commercial_terms(self):
        for ship in tms.read_bookings():
            terms = ship.get("commercial")
            self.assertTrue(terms, f"{ship['id']} has no commercial terms")
            for key in ("freight_eur", "late_eur_per_day", "breach_eur", "transfer_risk_eur"):
                self.assertIn(key, terms, f"{ship['id']} is missing {key}")


class ARerouteMustBeatStayingPut(unittest.TestCase):
    def test_an_alternate_that_costs_more_than_staying_is_not_chosen(self):
        """The guard rail. Landing sooner is not the same as being better off."""
        routes, events = ra.load_routes(), _events("redsea")
        ships = {s["id"]: s for s in tms.read_bookings()}
        a = ra.build_assessment(ships["SHP-007"], routes, events)
        stay = a["current"]["exposure_eur"]
        for alt in a["candidates"][1:]:
            self.assertGreaterEqual(
                alt["exposure_eur"], stay,
                "fixture drifted: SHP-007's alternates are supposed to be the case "
                "where every reroute is a more expensive way to be late")
        decision = ra.decide_with_rules(a)
        self.assertEqual(decision["decision"], "hold")


class TheBoardStillDecidesWhatTheScreenplaySays(unittest.TestCase):
    """The demo narrative is the spec. Pricing the options must explain those
    decisions, not overturn them."""

    EXPECTED = {"hamburg": (2, 1, 4), "redsea": (6, 1, 0),
                "rhine": (1, 0, 6), "france": (1, 0, 6)}

    def test_every_scenario_lands_on_its_documented_split(self):
        routes = ra.load_routes()
        for scenario_id, (reroute, hold, on_plan) in self.EXPECTED.items():
            with self.subTest(scenario=scenario_id):
                events = _events(scenario_id)
                counts = Counter(
                    ra.decide_with_rules(ra.build_assessment(s, routes, events))["decision"]
                    for s in tms.read_bookings())
                self.assertEqual(
                    (counts["reroute"], counts["hold"], counts["no-action"]),
                    (reroute, hold, on_plan),
                    f"{scenario_id} moved: {dict(counts)}")


if __name__ == "__main__":
    unittest.main()
