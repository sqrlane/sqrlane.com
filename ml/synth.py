"""ml/synth.py - a synthetic TMS world with ground truth.

The one thing the real repo cannot provide is a label. The demo book holds
seven authored bookings and the decisions on them come from the shipped rules
engine or the LLM - so a model trained on that board would only ever relearn
the policy that labelled it, and any accuracy figure it produced would be the
invented metric this project refuses to print.

This generator is the fix. It builds a WORLD, not a dataset of decisions:

  * about eighteen months of weekly departures over the real route catalogue
    (data/routes.json, read through src.config - the routes are the one piece
    of the demo that is reused verbatim);
  * disruption EPISODES arriving per chokepoint through a Poisson-ish process,
    each with a LATENT true severity and true duration the learners never see,
    plus the noisy proxies a desk actually gets: a banded severity that is
    sometimes misread, a delay-range estimate like the live classifier
    publishes, a headline count, and an instrument reading where the family
    fits (a gauge for the Rhine, gusts for a port, wave height at sea);
  * for every booking, the REALIZED outcome of each of the three actions the
    Route Advisor can take - stay, hold, reroute to the best alternate -
    computed from the latent episode state, a latent per-carrier reliability
    factor, and lognormal noise, then priced with the shipped cost arithmetic
    (src.route_advisor.cost_of - imported, never copied).

Labels therefore come from realized outcomes, not from any policy. The rules
engine can be scored against this world like any other model, which is the
whole point.

Honesty boundary, made mechanical: everything a model may look at lives on the
record OUTSIDE the "outcome" key; everything latent inside "outcome" is
prefixed with an underscore. ml/features.py refuses to read either, and
tests/test_the_models_stay_honest.py checks that refusal.

Dependencies: the standard library, plus the repo's own src/ modules (which the
demo already requires). No numpy, no scikit-learn, no install beyond what the
repo runs on - the world must be generatable anywhere the demo runs.

Run it:

    python -m ml.synth --bookings 6000 --seed 7
    python -m ml.synth --bookings 200 --seed 3 --out ml/data/

Writes tms_synthetic_bookings.json (the full book, gitignored - it is large
and exactly reproducible from its seed) and tms_synthetic_bookings.sample.json
(the first 50 records, committed so the schema is reviewable without running
anything). Same seed, byte-identical output - a test holds that, so nothing in
here may read a clock or the global RNG.
"""

import argparse
import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

from src import config
from src.route_advisor import cost_of

# ---------------------------------------------------------------------------
# The world's constants
# ---------------------------------------------------------------------------

# The timeline starts on a fixed Monday. Fixed, not "today", because the same
# seed must produce byte-identical output whenever it is run - determinism is
# what makes a generated dataset reviewable at all.
WORLD_START = date(2025, 1, 6)
DEFAULT_WEEKS = 78  # about eighteen months of weekly departures

# Where along a route each chokepoint is passed, as a fraction of transit.
# Stylised on purpose: the sea legs sit mid-voyage, the discharge port at the
# end, the inland leg after it. This is what makes episode TIMING learnable -
# a three-day strike at the discharge port, observed on departure day, is
# almost always over by the time the vessel arrives thirty days later, and a
# model that never learns that will hold cargo for ghosts.
PASSAGE_FRACTION = {
    "SUEZ": 0.45, "REDSEA": 0.40, "COGH": 0.50,
    "HAM": 0.95, "RTM": 0.95, "ANR": 0.95, "FOS": 0.95,
    "RHINE": 0.98, "FRINL": 0.98,
}

# How often each chokepoint is disrupted (episodes per year) and by what.
# The mixes lean the way the demo's scenarios lean: strikes at the labour
# ports, low water on the Rhine, geopolitics on the Red Sea leg. "other" from
# config.EVENT_TYPES is deliberately unused - it is the live classifier's
# catch-all, and a generator that produced "other" would be hiding structure.
EPISODES_PER_YEAR = {
    "HAM": 10, "RTM": 10, "ANR": 9, "FOS": 9,
    "SUEZ": 7, "REDSEA": 8, "COGH": 8, "RHINE": 9, "FRINL": 6,
}
TYPE_MIX = {
    "HAM": [("strike", 0.30), ("weather", 0.35), ("congestion", 0.25), ("customs", 0.10)],
    "RTM": [("strike", 0.20), ("weather", 0.35), ("congestion", 0.30), ("customs", 0.15)],
    "ANR": [("strike", 0.25), ("weather", 0.30), ("congestion", 0.30), ("customs", 0.15)],
    "FOS": [("strike", 0.45), ("weather", 0.25), ("congestion", 0.20), ("customs", 0.10)],
    "SUEZ": [("geopolitical", 0.45), ("congestion", 0.35), ("customs", 0.20)],
    "REDSEA": [("geopolitical", 0.60), ("weather", 0.40)],
    "COGH": [("weather", 0.85), ("congestion", 0.15)],
    "RHINE": [("weather", 0.75), ("congestion", 0.25)],
    "FRINL": [("strike", 0.40), ("weather", 0.40), ("congestion", 0.20)],
}

# Per-type structure: how long an episode runs (lognormal, median days), how
# many days of delay a full-severity episode costs a passage, and how long the
# backlog lingers after it formally ends. Geopolitical episodes run long and
# bite hard - that is the Red Sea closure; strikes are short and sharp.
TYPE_PARAMS = {
    "strike":       {"dur_median": 5,  "dur_sigma": 0.35, "delay_scale": 9.0,  "recovery": 4},
    "weather":      {"dur_median": 6,  "dur_sigma": 0.30, "delay_scale": 8.0,  "recovery": 3},
    "congestion":   {"dur_median": 12, "dur_sigma": 0.30, "delay_scale": 6.0,  "recovery": 8},
    "geopolitical": {"dur_median": 24, "dur_sigma": 0.30, "delay_scale": 16.0, "recovery": 6},
    "customs":      {"dur_median": 8,  "dur_sigma": 0.30, "delay_scale": 5.0,  "recovery": 3},
}

# The noise knobs, all in one place so calibration is one edit and the README
# can quote the final values. Tuned empirically (see ml/README.md) so the task
# is learnable but not saturated: if a model ever scores 100% here, the noise
# is wrong, not the model right - and a test asserts exactly that.
NOISE = {
    "band_misread_prob": 0.15,   # chance the observed severity band is off by one
    "outcome_sigma": 0.35,       # lognormal sigma on each episode's realized bite
    "estimate_sigma": 0.25,      # lognormal sigma on the published delay estimate
    "schedule_sigma": 1.0,       # ordinary schedule slip, disruption or not
    "carrier_mu_range": (0.0, 1.4),   # latent per-carrier mean extra days
    "gauge_sigma_cm": 8.0,
    "gust_sigma_kn": 3.0,
    "wave_sigma_m": 0.4,
}

SEVERITY_BANDS = ["low", "medium", "high"]

# Disruptions that land AFTER the decision still happen to the voyage, but
# they are damped in every arm alike: in the product a later disruption gets
# a later decision of its own, so this booking's label should mostly be about
# the one on the table. Without the discount the label flips on events no
# information available at decision time could have predicted, and no model -
# or desk - should be scored on clairvoyance.
FUTURE_EPISODE_DISCOUNT = 0.45

# When a booking chooses to hold there is a ceiling on how long anyone waits
# before the plan is rewritten some other way; and holding with nothing to
# wait out still costs a couple of days of dwell - holding is never free.
HOLD_WAIT_CAP_DAYS = 21
POINTLESS_HOLD_DWELL_DAYS = 2.0

# Two actions within this much of each other are the same action to a desk, so
# the label prefers the calmer one (no-action, then hold) inside the band -
# knife-edge labels would just teach the model the generator's rounding.
INDIFFERENCE_BAND_EUR = 500

# ---------------------------------------------------------------------------
# Fictional parties. Every name below is invented for this generator - the
# same restraint as config.FORWARDER's .example domain. No real carrier,
# company or person appears, and the demo book's real-world carrier names are
# deliberately NOT reused here.
# ---------------------------------------------------------------------------

CARRIERS = [
    {"name": "Nordkap Container Line", "code": "NKCL"},
    {"name": "Meridian Ocean Carriers", "code": "MOCU"},
    {"name": "Albatros Shipping Co.", "code": "ALBU"},
    {"name": "Cobalt Star Line", "code": "CSLU"},
    {"name": "Westerlicht Lijnen", "code": "WLLU"},
    {"name": "Aurora Container Services", "code": "AURU"},
    {"name": "Trident & Meer Line", "code": "TRMU"},
    {"name": "Pelikaan Express Line", "code": "PELU"},
]

CUSTOMER_STEMS = [
    "Aldervale", "Brandtholm", "Cedermark", "Drossel", "Eisenhut", "Falkenrode",
    "Greifswerk", "Hollandia", "Isarfeld", "Juniper", "Kranenburg", "Lindwurm",
    "Morgenrot", "Nebelhorn", "Ostwind", "Palissade", "Quellenhof", "Rheingold",
    "Silberbach", "Tannenberg", "Uferwerk", "Vlinderhof", "Waldkauz", "Zilvermeeuw",
]
CUSTOMER_TRADES = [
    "Components", "Drivetrain", "Pharma Logistics", "Interieur", "Electronics",
    "Maschinenbau", "Foods", "Apparel Group", "Chemie", "Solar Systems",
    "Packaging", "Robotics",
]
CUSTOMER_SUFFIXES = ["GmbH", "B.V.", "N.V.", "AG", "S.A.", "S.à r.l."]

CONTACT_FIRST = ["Anneke", "Bram", "Clara", "Diederik", "Elke", "Frederik",
                 "Greetje", "Henrik", "Ilse", "Joost", "Katrien", "Lennart",
                 "Marit", "Nikolaus", "Odile", "Pieter"]
CONTACT_LAST = ["Vandermolen", "Steinbrecher", "Callewaert", "Duivenvoorde",
                "Eichenwald", "Fontenelle", "Grootveld", "Hasenkamp",
                "Ijzerman", "Jägerstett", "Kettelhut", "Lindeboom"]
CONTACT_ROLES = ["Inbound Logistics", "Supply Chain Lead", "Materials Planning",
                 "Logistics Coordinator", "Procurement", "Plant Logistics"]

# Cargo types, whether they run cold, and the commercial scale of each. The
# late/breach terms echo the demo book's logic: an assembly line waiting on
# parts is expensive by the day, a retail promo mostly has a single cliff.
CARGO_TYPES = [
    {"cargo": "Automotive parts", "detail": "assembled brake and suspension components",
     "cold": False, "freight": (22000, 36000), "late": (6000, 12000), "breach": (15000, 30000)},
    {"cargo": "Consumer electronics", "detail": "small appliances and accessories",
     "cold": False, "freight": (16000, 28000), "late": (2500, 6000), "breach": (10000, 22000)},
    {"cargo": "Reefer pharma", "detail": "temperature-controlled pharmaceutical intermediates",
     "cold": True, "freight": (30000, 46000), "late": (8000, 14000), "breach": (20000, 34000)},
    {"cargo": "Frozen foods", "detail": "reefer boxes of frozen produce",
     "cold": True, "freight": (18000, 30000), "late": (3000, 7000), "breach": (9000, 18000)},
    {"cargo": "Furniture", "detail": "flat-packed retail furniture",
     "cold": False, "freight": (12000, 22000), "late": (1500, 4000), "breach": (6000, 14000)},
    {"cargo": "Machinery", "detail": "packaged industrial machinery and spares",
     "cold": False, "freight": (20000, 34000), "late": (5000, 10000), "breach": (14000, 26000)},
    {"cargo": "Apparel", "detail": "seasonal retail apparel",
     "cold": False, "freight": (12000, 20000), "late": (2000, 5000), "breach": (8000, 16000)},
    {"cargo": "Solar modules", "detail": "framed PV modules on project schedule",
     "cold": False, "freight": (16000, 28000), "late": (4000, 9000), "breach": (12000, 24000)},
]

# Trade lanes over the REAL route catalogue: each lane names a primary route
# and the alternates a forwarder would plausibly hold on file for it. The ids
# must all exist in data/routes.json - generate() asserts so, because a lane
# naming a route that is not in the catalogue would silently break the reuse
# of the shipped cost arithmetic.
LANES = [
    {"weight": 22, "destinations": ["Munich", "Stuttgart", "Nuremberg"],
     "primary": "R-HAM-STD", "alternates": ["R-RTM-ALT", "R-COGH-ALT"]},
    {"weight": 8, "destinations": ["Hamburg"],
     "primary": "R-HAM-STD", "alternates": []},
    {"weight": 16, "destinations": ["Rotterdam", "Utrecht", "Duisburg"],
     "primary": "R-RTM-STD", "alternates": ["R-ANR-STD", "R-COGH-RTM"]},
    {"weight": 14, "destinations": ["Antwerp", "Brussels", "Liège"],
     "primary": "R-ANR-STD", "alternates": ["R-RTM-STD", "R-COGH-ANR"]},
    {"weight": 14, "destinations": ["Basel", "Zurich"],
     "primary": "R-RTM-RHINE", "alternates": ["R-RTM-RAIL", "R-COGH-BSL"]},
    {"weight": 14, "destinations": ["Lyon", "Grenoble"],
     "primary": "R-FOS-STD", "alternates": ["R-ANR-LYON", "R-COGH-FOS"]},
]

ORIGINS = ["Shanghai", "Ningbo", "Shenzhen", "Busan", "Singapore", "Qingdao"]

SLACK_CHOICES = [1, 2, 2, 3, 3, 3, 4, 4, 5, 6]  # weighted toward the middle

ACTIONS = ["no-action", "hold", "reroute"]


# ---------------------------------------------------------------------------
# Small helpers - every draw goes through the one seeded Random instance
# ---------------------------------------------------------------------------


def _iso(day_index: int) -> str:
    """A world day number as an ISO date. All dates derive from WORLD_START."""
    return (WORLD_START + timedelta(days=day_index)).isoformat()


def _weighted_choice(rng, pairs):
    """Pick from [(value, weight), ...]. random.choices exists, but spelling it
    out keeps the draw order obvious - determinism lives or dies on order."""
    total = sum(w for _, w in pairs)
    roll = rng.random() * total
    for value, weight in pairs:
        roll -= weight
        if roll <= 0:
            return value
    return pairs[-1][0]


def _lognormal_days(rng, median, sigma, cap=60):
    """A duration in whole days, at least 1. Lognormal because disruptions
    have a long right tail - most strikes settle fast, a few do not."""
    return max(1, min(cap, round(math.exp(math.log(median) + rng.gauss(0.0, sigma)))))


def load_route_catalogue() -> dict[str, dict]:
    """The real route table, through the same config path the advisor uses.
    Routes are shared REFERENCE data, not the book - the demo's bookings stay
    behind the TMS connector and this module never touches them."""
    with open(config.ROUTES_FILE, encoding="utf-8") as handle:
        return {r["route_id"]: r for r in json.load(handle)["routes"]}


def passage_offset(route: dict, chokepoint: str) -> int:
    """On which day of this route's transit the chokepoint is passed."""
    return round(route["transit_days"] * PASSAGE_FRACTION.get(chokepoint, 0.5))


# ---------------------------------------------------------------------------
# Episodes - the disruptions, with their latents and their observed faces
# ---------------------------------------------------------------------------


def _true_band(severity: float) -> str:
    if severity < 1 / 3:
        return "low"
    if severity < 2 / 3:
        return "medium"
    return "high"


def _observed_band(rng, severity: float) -> str:
    """What the desk's classifier says the band is. Usually right; sometimes
    off by one step, because a headline is not an instrument."""
    band = _true_band(severity)
    if rng.random() < NOISE["band_misread_prob"]:
        index = SEVERITY_BANDS.index(band)
        neighbours = [i for i in (index - 1, index + 1) if 0 <= i < len(SEVERITY_BANDS)]
        band = SEVERITY_BANDS[rng.choice(neighbours)]
    return band


def _estimated_range(rng, severity: float, event_type: str) -> list[int]:
    """The published expected-delay range: what the live classifier would put
    on the event. It reads the episode's real magnitude - through noise - the
    way a classifier reads magnitude out of prose, so a bad estimate is
    possible and a useless one is not. The range brackets the noisy read."""
    mid = severity * TYPE_PARAMS[event_type]["delay_scale"]
    observed = max(0.5, mid * math.exp(rng.gauss(0.0, NOISE["estimate_sigma"])))
    lo = max(0, math.floor(observed * 0.7))
    # Capped where a live classifier's ranges live: nobody publishes "26 days
    # of delay" off a headline, and an uncapped tail here made the shipped
    # rules engine look far more trigger-happy than it is on the real board.
    hi = min(15, max(lo + 1, math.ceil(observed * 1.3)))
    return [min(lo, hi - 1), hi]


def generate_episodes(rng, total_days: int) -> list[dict]:
    """Walk the calendar per chokepoint; each day has a small chance of
    starting an episode - a Poisson-ish arrival process. Chokepoints iterate
    in a fixed order so the draw sequence, and hence the output bytes, never
    depend on dict whim."""
    episodes = []
    for chokepoint in sorted(EPISODES_PER_YEAR):
        daily_rate = EPISODES_PER_YEAR[chokepoint] / 365.0
        count = 0
        for day in range(total_days):
            if rng.random() >= daily_rate:
                continue
            count += 1
            event_type = _weighted_choice(rng, TYPE_MIX[chokepoint])
            params = TYPE_PARAMS[event_type]
            # Geopolitical episodes skew severe; everything else skews mild.
            if event_type == "geopolitical":
                severity = rng.betavariate(2.4, 2.0)
            else:
                severity = rng.betavariate(2.0, 2.6)
            duration = _lognormal_days(rng, params["dur_median"], params["dur_sigma"])
            band = _observed_band(rng, severity)
            episodes.append({
                "episode_id": f"EP-{chokepoint}-{count:03d}",
                "chokepoint": chokepoint,
                "type": event_type,
                "started_on": _iso(day),
                # Observed face - what a desk would be told.
                "severity": band,
                "expected_delay_days": _estimated_range(rng, severity, event_type),
                # Latents - underscored, and never surfaced in a booking's
                # facts. The learners meet these only through their effects.
                "_true_severity": round(severity, 4),
                "_true_duration_days": duration,
                "_start_day": day,
            })
    return episodes


def _episode_bite(rng, episode: dict, passage_day: int, noise_cache: dict) -> float:
    """Days of delay this episode really costs a passage on that day.

    Active episode: full force, scaled by latent severity and type. Recently
    ended: a decaying backlog, because a port does not clear the queue the
    hour a strike settles. Not yet started, or long over: nothing. Lognormal
    noise on top - two vessels through the same storm do not lose the same
    hours, and this irreducible noise is what keeps a perfect score
    impossible by construction.

    The noise multiplier is drawn ONCE per booking-and-episode and shared by
    every counterfactual arm (stay, hold, each reroute): how hard this storm
    hits this vessel is a fact about the storm and the vessel, not about the
    plan. Independent draws per arm would flip labels on noise that no
    information could ever predict, and the label would stop meaning
    "the action that was genuinely better".
    """
    start = episode["_start_day"]
    end = start + episode["_true_duration_days"]
    if passage_day < start:
        return 0.0
    if passage_day < end:
        factor = 1.0
    else:
        recovery = TYPE_PARAMS[episode["type"]]["recovery"]
        days_past = passage_day - end
        if days_past >= recovery:
            return 0.0
        factor = 0.4 * (1.0 - days_past / recovery)
    scale = TYPE_PARAMS[episode["type"]]["delay_scale"]
    if episode["episode_id"] not in noise_cache:
        noise_cache[episode["episode_id"]] = math.exp(rng.gauss(0.0, NOISE["outcome_sigma"]))
    return episode["_true_severity"] * scale * factor * noise_cache[episode["episode_id"]]


def _future_discount(episode: dict, decision_day: int) -> float:
    """Episodes that had not started when the desk decided are damped - see
    FUTURE_EPISODE_DISCOUNT for why. Applied identically in every arm, so it
    never favours one action over another."""
    return FUTURE_EPISODE_DISCOUNT if episode["_start_day"] > decision_day else 1.0


def _instrument_reading(rng, episode: dict):
    """The instrument that fits the family, with observation noise - the same
    split the live board makes: a number where a number exists, prose where it
    does not. Only weather episodes have an instrument; a strike has headlines.
    Returns (field_name, value) or None."""
    if episode["type"] != "weather":
        return None
    severity = episode["_true_severity"]
    chokepoint = episode["chokepoint"]
    if chokepoint == "RHINE":
        # Low water: the worse the episode, the lower the gauge.
        reading = 145 - 120 * severity + rng.gauss(0.0, NOISE["gauge_sigma_cm"])
        return ("gauge_cm", round(max(20.0, min(220.0, reading))))
    if chokepoint in ("HAM", "RTM", "ANR", "FOS"):
        reading = 28 + 32 * severity + rng.gauss(0.0, NOISE["gust_sigma_kn"])
        return ("gust_kn", round(max(5.0, reading)))
    if chokepoint in ("SUEZ", "REDSEA", "COGH"):
        reading = 1.8 + 5.5 * severity + rng.gauss(0.0, NOISE["wave_sigma_m"])
        return ("wave_m", round(max(0.2, reading), 1))
    return None


# ---------------------------------------------------------------------------
# Bookings
# ---------------------------------------------------------------------------


def _make_commercial(rng, cargo: dict, containers: int) -> dict:
    freight = rng.randint(*cargo["freight"])
    late = rng.randint(*cargo["late"])
    breach = rng.randint(*cargo["breach"])
    transfer = rng.randint(6000, 15000) if cargo["cold"] else 0
    return {
        "freight_eur": freight,
        "late_eur_per_day": late,
        "breach_eur": breach,
        "transfer_risk_eur": transfer,
        "basis": f"{containers} x 40HC synthetic booking; terms drawn by ml.synth, "
                 f"same shape as the demo book's commercial block.",
    }


def _active_on(episodes, day, chokepoints):
    """Episodes running on this day at any of these chokepoints."""
    hits = []
    for episode in episodes:
        start = episode["_start_day"]
        if start <= day < start + episode["_true_duration_days"] \
                and episode["chokepoint"] in chokepoints:
            hits.append(episode)
    return hits


def _relevant_on(episodes, day, passage_days):
    """What the desk reviewing this booking today actually has on its
    picture: episodes running now, at a chokepoint the voyage has NOT yet
    passed. The schedule is on the same screen as the risk feed, so a strike
    at a port the vessel cleared last week is news about someone else's
    booking - the terminal links an event to a booking only through the
    passages still ahead. passage_days maps each watched chokepoint to the
    earliest day any of this booking's routes would pass it."""
    hits = []
    for episode in _active_on(episodes, day, set(passage_days)):
        if passage_days[episode["chokepoint"]] >= day:
            hits.append(episode)
    return hits


def _realized_route_delay(rng, route, episodes, etd_day, decision_day,
                          noise_cache, shift=0.0):
    """Disruption delay a voyage on this route really collects, counting only
    passages still ahead of the decision - what has been sailed is sunk. The
    shift models a hold: every remaining passage happens that much later.
    Every episode in the world is consulted, including ones that START after
    the decision - the future stays as unforecastable here as it is at a desk.
    """
    total = 0.0
    for chokepoint in route["chokepoints"]:
        passage_day = etd_day + passage_offset(route, chokepoint)
        if passage_day < decision_day:
            continue
        shifted = round(passage_day + shift)
        for episode in episodes:
            if episode["chokepoint"] == chokepoint:
                total += (_episode_bite(rng, episode, shifted, noise_cache)
                          * _future_discount(episode, decision_day))
    return total


def _hold_wait(route, visible_episodes, etd_day, decision_day):
    """How long a hold actually waits: until every visible episode that would
    still be live at a remaining passage has ended, plus a day of margin -
    capped, because nobody waits three weeks on a berth option. Only VISIBLE
    episodes count: a desk cannot wait out a disruption it has not seen."""
    wait = 0.0
    for chokepoint in route["chokepoints"]:
        passage_day = etd_day + passage_offset(route, chokepoint)
        if passage_day < decision_day:
            continue
        for episode in visible_episodes:
            if episode["chokepoint"] != chokepoint:
                continue
            end = episode["_start_day"] + episode["_true_duration_days"]
            wait = max(wait, min(HOLD_WAIT_CAP_DAYS, max(0, end - passage_day + 1)))
    return wait


def _price(action_delay, added_cost_index, discharge_port, booking, primary):
    """The realized cost of one action, through the SHIPPED cost arithmetic.
    cost_of() is imported from src.route_advisor, never copied - the world is
    synthetic but the money is priced exactly the way the product prices it.
    The realized delay goes in as both ends of the range because it is not an
    estimate any more: it is what happened."""
    candidate = {
        "added_cost_index": added_cost_index,
        "projected_delay_days": [action_delay, action_delay],
        "discharge_port": discharge_port,
    }
    return round(cost_of(candidate, booking, primary)["exposure_eur"])


def _label(costs: dict) -> str:
    """Argmin of realized cost, with an indifference band: within EUR 500 of
    the best, prefer doing nothing, then holding. A desk does not rebook a
    container to save the price of a dinner, and a label that flips on such
    margins teaches a model nothing but the generator's own rounding."""
    best = min(costs.values())
    for action in ACTIONS:  # preference order: no-action, hold, reroute
        if action in costs and costs[action] <= best + INDIFFERENCE_BAND_EUR:
            return action
    return "no-action"  # unreachable, but explicit beats clever


def generate(bookings: int = 6000, seed: int = 7, weeks: int = DEFAULT_WEEKS) -> dict:
    """Build the whole world and return it as one JSON-ready dict.

    One seeded Random instance drives every draw, in one fixed order, so the
    same call is byte-identical every time - which is what lets a reviewer
    regenerate the exact dataset a report was scored on.
    """
    rng = random.Random(seed)
    routes = load_route_catalogue()

    # A lane naming a route the catalogue does not carry would quietly break
    # the reuse of the shipped arithmetic, so fail loudly here instead.
    for lane in LANES:
        for route_id in [lane["primary"], *lane["alternates"]]:
            if route_id not in routes:
                raise ValueError(f"Lane names unknown route {route_id!r} - "
                                 f"data/routes.json does not carry it.")

    # Episodes need to outlive the last departure by a full long voyage, or
    # bookings near the end of the timeline would sail through a world that
    # has gone suspiciously quiet.
    total_days = weeks * 7 + 70
    episodes = generate_episodes(rng, total_days)

    # The latent carrier factor: some lines just run later than others. Drawn
    # once per carrier, observed only through a noisy on-time-rate proxy.
    carrier_mu = {c["name"]: rng.uniform(*NOISE["carrier_mu_range"]) for c in CARRIERS}

    lane_pairs = [(lane, lane["weight"]) for lane in LANES]
    records = []
    for index in range(bookings):
        lane = _weighted_choice(rng, lane_pairs)
        primary = routes[lane["primary"]]

        # Which alternates this forwarder actually holds on file. Some
        # bookings have none - those are the world's hold-only corners, the
        # SHP-002s, and without them "hold" would never be the right answer.
        roll = rng.random()
        if roll < 0.20:
            alternates = []
        elif roll < 0.45 and len(lane["alternates"]) > 1:
            alternates = [rng.choice(lane["alternates"])]
        else:
            alternates = list(lane["alternates"])

        cargo = rng.choice(CARGO_TYPES)
        carrier = rng.choice(CARRIERS)
        containers = rng.randint(1, 14)
        slack = rng.choice(SLACK_CHOICES)

        etd_day = rng.randrange(weeks) * 7 + rng.randrange(7)
        transit = primary["transit_days"]
        eta_day = etd_day + transit
        required_day = eta_day + slack

        # The desk reviews this booking once, somewhere mid-voyage - that is
        # when the demo's decisions happen too: the strike lands while the
        # box is already at sea, not on booking day. The review day leans
        # toward days when something is visibly active, because that is when
        # desks actually look: an alert fires and the board gets read. The
        # rest of the time the review lands on a quiet day, so "nothing to
        # see, do nothing" stays a well-represented, honest answer.
        # The earliest passage of every watched chokepoint, over the primary
        # and every alternate on file - the schedule knowledge that decides
        # which episodes are on this booking's picture at all.
        passage_days = {}
        for route in [primary] + [routes[rid] for rid in alternates]:
            for chokepoint in route["chokepoints"]:
                day = etd_day + passage_offset(route, chokepoint)
                if chokepoint not in passage_days or day < passage_days[chokepoint]:
                    passage_days[chokepoint] = day
        alert_days = [d for d in range(etd_day, etd_day + transit)
                      if _relevant_on(episodes, d, passage_days)]
        if alert_days and rng.random() < 0.65:
            decision_day = rng.choice(alert_days)
        else:
            decision_day = etd_day + rng.randrange(transit)
        visible = _relevant_on(episodes, decision_day, passage_days)

        # --- decision-time facts: everything the desk knows BEFORE acting ---
        fact_episodes = []
        for episode in visible:
            severity_num = episode["_true_severity"]
            headline_base = severity_num * 14 * (1.4 if episode["type"] in ("strike", "geopolitical") else 1.0)
            days_into = decision_day - episode["_start_day"]
            on_primary = episode["chokepoint"] in primary["chokepoints"]
            # How far ahead the disrupted chokepoint is on the schedule the
            # desk is already looking at. Negative means the vessel is past
            # it - a strike astern is news, not a problem. Pure schedule
            # knowledge, so it is observed, not latent.
            if on_primary:
                days_to_passage = (etd_day + passage_offset(primary, episode["chokepoint"])
                                   - decision_day)
            else:
                alt_offsets = [etd_day + passage_offset(routes[rid], episode["chokepoint"])
                               - decision_day
                               for rid in alternates
                               if episode["chokepoint"] in routes[rid]["chokepoints"]]
                days_to_passage = min(alt_offsets) if alt_offsets else 0
            entry = {
                "episode_id": episode["episode_id"],
                "chokepoint": episode["chokepoint"],
                "type": episode["type"],
                "severity": episode["severity"],
                "expected_delay_days": episode["expected_delay_days"],
                "started_on": episode["started_on"],
                "days_into_episode": days_into,
                "days_to_passage": days_to_passage,
                "headline_count": max(0, round(rng.gauss(headline_base + days_into / 3, 3.0))),
                "on_primary_route": on_primary,
            }
            reading = _instrument_reading(rng, episode)
            if reading is not None:
                entry[reading[0]] = reading[1]
            fact_episodes.append(entry)

        fact_candidates = [{
            "route_id": route_id,
            "added_transit_days": routes[route_id]["transit_days"] - transit,
            "added_cost_index": routes[route_id]["cost_index"] - primary["cost_index"],
            "discharge_port": routes[route_id]["discharge_port"],
        } for route_id in alternates]

        mu = carrier_mu[carrier["name"]]
        on_time_rate = max(0.50, min(0.99, 0.92 - mu * 0.18 + rng.gauss(0.0, 0.03)))

        booking = {
            "id": f"SYN-{index + 1:06d}",
            "cargo": cargo["cargo"],
            "cargo_detail": f"{containers} x 40HC, {cargo['detail']}",
            "origin": rng.choice(ORIGINS),
            "final_destination": rng.choice(lane["destinations"]),
            "primary_route": lane["primary"],
            "alternates": alternates,
            "deadline_slack_days": slack,
            "notes": "Synthetic booking generated by ml.synth - not a real shipment.",
            "customer": f"{rng.choice(CUSTOMER_STEMS)} {rng.choice(CUSTOMER_TRADES)} "
                        f"{rng.choice(CUSTOMER_SUFFIXES)}",
            "customer_contact": f"{rng.choice(CONTACT_FIRST)} {rng.choice(CONTACT_LAST)}, "
                                f"{rng.choice(CONTACT_ROLES)}",
            "carrier": carrier["name"],
            "booking_ref": f"{carrier['code']}-{rng.randint(1_000_000, 9_999_999)}",
            "container": f"{carrier['code'][:3]}U{rng.randint(1_000_000, 9_999_999)}"
                         + (f" + {containers - 1}" if containers > 1 else ""),
            "etd": _iso(etd_day),
            "eta": _iso(eta_day),
            "required_by": _iso(required_day),
            "cold_chain": cargo["cold"],
            "special_requirements": ("temperature-controlled, keep chain of custody"
                                     if cargo["cold"] else None),
            "commercial": _make_commercial(rng, cargo, containers),
            "facts": {
                "decided_on": _iso(decision_day),
                "days_since_departure": decision_day - etd_day,
                "primary_transit_days": transit,
                "active_episodes": fact_episodes,
                "candidates": fact_candidates,
                "carrier_on_time_rate": round(on_time_rate, 3),
            },
        }

        # --- ground truth: what each action would really have cost ----------
        # One base slip for the voyage - the carrier runs how the carrier
        # runs, whichever way the desk decides.
        base_slip = max(0.0, rng.gauss(mu, NOISE["schedule_sigma"]))
        noise_cache = {}

        stay_delay = base_slip + _realized_route_delay(
            rng, primary, episodes, etd_day, decision_day, noise_cache)

        wait = _hold_wait(primary, visible, etd_day, decision_day)
        if wait == 0.0:
            # Nothing visible to wait out: holding is pure dwell on top of
            # whatever staying would have collected anyway.
            hold_delay = stay_delay + POINTLESS_HOLD_DWELL_DAYS
        else:
            hold_delay = wait + base_slip + _realized_route_delay(
                rng, primary, episodes, etd_day, decision_day, noise_cache, shift=wait)

        costs = {
            "no-action": _price(stay_delay, 0, primary["discharge_port"], booking, primary),
            "hold": _price(hold_delay, 0, primary["discharge_port"], booking, primary),
        }

        reroute_route, reroute_delay = None, None
        for route_id in alternates:
            alternate = routes[route_id]
            delay = (alternate["transit_days"] - transit) + base_slip \
                + _realized_route_delay(rng, alternate, episodes, etd_day, decision_day,
                                        noise_cache)
            cost = _price(delay, alternate["cost_index"] - primary["cost_index"],
                          alternate["discharge_port"], booking, primary)
            if reroute_route is None or cost < costs["reroute"]:
                reroute_route, reroute_delay = route_id, delay
                costs["reroute"] = cost

        booking["outcome"] = {
            "realized_delay_days_stay": round(stay_delay, 1),
            "deadline_breached": stay_delay > slack,
            "realized_cost_eur": costs,
            "optimal_action": _label(costs),
            "reroute_route_id": reroute_route,
            "hold_wait_days": round(wait, 1),
            # Latents, underscored: the boundary ml/features.py enforces is
            # "nothing under outcome, nothing underscored" - so everything the
            # learners must never see is mechanically inside that fence.
            "_carrier_delay_mu_days": round(mu, 3),
            "_base_slip_days": round(base_slip, 2),
            "_reroute_delay_days": round(reroute_delay, 1) if reroute_delay is not None else None,
        }
        records.append(booking)

    return {
        "_comment": "SYNTHETIC TMS world generated by ml.synth. Every booking, "
                    "company, contact and outcome is invented; labels come from "
                    "the generator's structural model, not from any policy. "
                    "Numbers learned here describe this simulated world only "
                    "and must never appear on the product pages.",
        "world": {
            "generator": "ml.synth",
            "seed": seed,
            "bookings": bookings,
            "weeks": weeks,
            "start": WORLD_START.isoformat(),
            "noise": NOISE,
            "indifference_band_eur": INDIFFERENCE_BAND_EUR,
        },
        "episodes": episodes,
        "bookings": records,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _write(world: dict, out_dir: Path, sample_size: int = 50) -> tuple[Path, Path]:
    """The full book (gitignored - large, and exactly reproducible from its
    seed) and a committed sample so the schema is reviewable in the repo."""
    out_dir.mkdir(parents=True, exist_ok=True)
    full_path = out_dir / "tms_synthetic_bookings.json"
    with open(full_path, "w", encoding="utf-8") as handle:
        json.dump(world, handle, indent=1, ensure_ascii=False)
        handle.write("\n")

    sample_bookings = world["bookings"][:sample_size]
    referenced = {e["episode_id"]
                  for b in sample_bookings
                  for e in b["facts"]["active_episodes"]}
    sample = {
        "_comment": world["_comment"] + " This file is the committed 50-record "
                    "sample; the full book is regenerated with: python -m ml.synth "
                    "--bookings " + str(world["world"]["bookings"]) + " --seed "
                    + str(world["world"]["seed"]),
        "world": world["world"],
        "episodes": [e for e in world["episodes"] if e["episode_id"] in referenced],
        "bookings": sample_bookings,
    }
    sample_path = out_dir / "tms_synthetic_bookings.sample.json"
    with open(sample_path, "w", encoding="utf-8") as handle:
        json.dump(sample, handle, indent=1, ensure_ascii=False)
        handle.write("\n")
    return full_path, sample_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the synthetic TMS world (bookings + episodes + ground truth).")
    parser.add_argument("--bookings", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--weeks", type=int, default=DEFAULT_WEEKS)
    parser.add_argument("--out", default="ml/data",
                        help="output directory (default ml/data)")
    args = parser.parse_args()

    world = generate(bookings=args.bookings, seed=args.seed, weeks=args.weeks)
    full_path, sample_path = _write(world, Path(args.out))

    labels = [b["outcome"]["optimal_action"] for b in world["bookings"]]
    exposed = sum(1 for b in world["bookings"] if b["facts"]["active_episodes"])
    breached = sum(1 for b in world["bookings"] if b["outcome"]["deadline_breached"])
    print(f"Wrote {len(world['bookings'])} bookings and {len(world['episodes'])} "
          f"episodes (seed {args.seed}, {args.weeks} weeks)")
    print(f"  {full_path}  (full book - gitignored)")
    print(f"  {sample_path}  (committed sample)")
    for action in ACTIONS:
        share = labels.count(action) / len(labels)
        print(f"  optimal {action:9s} {labels.count(action):5d}  ({share:.1%})")
    print(f"  exposed to >=1 visible episode: {exposed} ({exposed / len(labels):.1%})")
    print(f"  deadline breached on the stay path: {breached} ({breached / len(labels):.1%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
