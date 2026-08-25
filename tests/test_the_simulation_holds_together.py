"""The authored week has to make sense as a week, not just day by day.

One rule lives in the simulation rather than the advisor, and it is the reason
this file exists. Without it SHP-001 went HAM -> RTM -> HAM -> COGH across four
days. Every single day's arithmetic was defensible - under the Red Sea closure,
Hamburg-under-strike genuinely beats Rotterdam-under-Red-Sea on "least late" -
but a box ping-ponging between two ports across a week is nonsense. The advisor
was right; it should never have been asked. So a booking is never offered the
route it just left.

That is the kind of bug no unit test finds and no single day reveals, which is
exactly why it needs a check over the whole run.

The other three claims here are what makes this a simulation rather than eight
independent runs: state carries between days, a hold costs a day for every day
it waits, and every decision is still made by the real advisor.

Deterministic - no model, no network - so it is safe to run anywhere.
"""

import unittest


class TheWeekHoldsTogether(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from src import simulation
        cls.result = simulation.run(use_llm=False, verbose=False)
        cls.days = cls.result["days"]

    def test_the_week_actually_ran(self):
        # A guard on the guard: an empty week passes every assertion below.
        self.assertGreater(len(self.days), 1, "No week to check.")
        self.assertTrue(any(d["actioned"] for d in self.days),
                        "Nothing was ever actioned - this tests nothing.")

    def test_no_booking_is_ever_offered_the_route_it_just_left(self):
        """The ping-pong bug, held down.

        Tracked per booking as the ordered list of routes it has been on: a
        route appearing again after it was left is the failure, whether that is
        one day later or four.
        """
        history, offences = {}, []
        for day in self.days:
            for card in day["shipments"]:
                been = history.setdefault(card["id"], [])
                if been and card["route"] == been[-1]:
                    continue                       # still where it was - not a move
                if card["route"] in been:
                    offences.append(f"day {day['day']}: {card['id']} returned to "
                                    f"{card['route']} after {' -> '.join(been)}")
                been.append(card["route"])

        self.assertEqual(offences, [], "\n".join([
            "",
            "A booking went back to a route it had already left:",
            *(f"    {o}" for o in offences),
            "",
            "Each day may be arithmetically right and the sequence still nonsense. The",
            "simulation must not offer a booking the route it just came off.",
        ]))

    def test_a_rerouted_booking_stays_on_its_new_route(self):
        """State carries. Otherwise this is eight unrelated runs in a row.

        A booking that moves again today is not a counter-example - a second
        disruption may genuinely move it a second time, which is what happens to
        SHP-006 when the Red Sea closes on top of the Rhine. What must never
        happen is yesterday's move quietly not being there this morning.
        """
        checked = 0
        for earlier, later in zip(self.days, self.days[1:]):
            before = {c["id"]: c for c in earlier["shipments"]}
            for card in later["shipments"]:
                was = before.get(card["id"])
                if not was or not was["changed"].get("moved"):
                    continue
                if card["changed"].get("moved"):
                    continue                       # moved again today, by a new event
                checked += 1
                with self.subTest(booking=card["id"], day=later["day"]):
                    self.assertEqual(card["route"], was["route"],
                                     "A booking moved yesterday, was not moved again "
                                     "today, and is not on the route it was moved to.")
        self.assertGreater(checked, 0, "No booking held its new route into the next day - "
                                       "this tests nothing.")

    def test_holding_costs_a_day_for_every_day_it_waits(self):
        """Holding is not free, and the week is what makes that legible."""
        checked = 0
        for earlier, later in zip(self.days, self.days[1:]):
            before = {c["id"]: c for c in earlier["shipments"]}
            for card in later["shipments"]:
                was = before.get(card["id"])
                if not was or card["state"] != "held" or was["state"] != "held":
                    continue
                checked += 1
                with self.subTest(booking=card["id"], day=later["day"]):
                    self.assertEqual(card["held_days"], was["held_days"] + 1,
                                     "A booking held two days running should have paid a "
                                     "day for the second one.")
                    self.assertGreater(card["eta"], was["eta"],
                                       "A day of waiting has to move the ETA.")
        self.assertGreater(checked, 0, "Nothing was held for two days running.")

    def test_every_decision_came_from_the_real_advisor(self):
        """Only the timeline is authored. The calls inside it are not."""
        for day in self.days:
            for card in day["shipments"]:
                with self.subTest(day=day["day"], booking=card["id"]):
                    self.assertTrue(card["decided_by"],
                                    "A decision with no recorded author is a decision "
                                    "nobody can check.")

    def test_the_week_says_it_is_authored(self):
        self.assertEqual(self.result["origin"], "scripted")
        self.assertIn("authored", self.result["honesty"].lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
