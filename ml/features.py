"""ml/features.py - the one authoritative feature list, with a leakage fence.

Every model in ml/models.py sees a booking through this file and nothing else,
so there is exactly one place where "what may the model know?" is answered -
and one place where leaking the answer key would have to happen. The fence is
mechanical, not a convention: build_features() reads the record through a
guarded accessor that RAISES on the "outcome" key and on any underscored key,
so a feature that touches ground truth cannot be added quietly. A test holds
this from the outside too, by checking that a record with its outcome block
deleted featurises to exactly the same vector.

Everything here is decision-time knowledge: the booking's own terms, the route
economics of the best alternate on file, and the observed face of whatever
episodes were active when the desk looked - banded severities, published
delay-range estimates, headline counts, instrument readings. No realized
delay, no latent severity, no label.

Stdlib only. The vectors are plain lists of floats so the stdlib baselines,
scikit-learn and TabPFN can all eat them unchanged.
"""

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}

# Sentinels for "this booking has no such thing". Chosen far outside each
# field's real range so a tree can split them off cleanly; the linear models
# see them too, which is part of why trees win here (see the reports).
NO_ALTERNATE_TRANSIT = 60.0     # no alternate on file: worse than any real detour
NO_ALTERNATE_COST = 60.0
NO_GAUGE_CM = 300.0             # far above any real low-water reading

# The authoritative, ordered list. Models, reports and tests all reference
# this - if a feature is added or removed, this list is the single edit.
FEATURE_COLUMNS = [
    # The booking itself
    "slack_days",
    "primary_transit_days",
    "days_since_departure",
    "cold_chain",
    "month_of_year",
    # Commercial terms - what a day late and a breach actually cost
    "freight_eur",
    "late_eur_per_day",
    "breach_eur",
    "transfer_risk_eur",
    # The escape routes on file, and what the cheapest one costs
    "n_alternates",
    "best_alt_added_transit_days",
    "best_alt_added_cost_index",
    # The carrier, through its observed on-time proxy (never its latent factor)
    "carrier_on_time_rate",
    # The risk picture at decision time - on the primary route
    "n_episodes_primary",
    "n_strike_primary",
    "n_weather_primary",
    "n_congestion_primary",
    "n_geopolitical_primary",
    "n_customs_primary",
    "max_severity_rank_primary",
    "est_delay_lo_primary",
    "est_delay_hi_primary",
    "worst_episode_days_running",
    "min_days_to_passage_primary",
    "n_episodes_ahead_primary",
    "est_delay_hi_ahead_primary",
    "sum_est_mid_ahead_primary",
    "soonest_ep_days_into",
    "soonest_ep_est_hi",
    "soonest_ep_is_strike",
    "soonest_ep_is_weather",
    "soonest_ep_is_congestion",
    "soonest_ep_is_geopolitical",
    "soonest_ep_is_customs",
    "headline_count_total",
    # ... and on the alternates (an escape route can be on fire too)
    "n_episodes_alternates",
    "est_delay_hi_alternates",
    # The instruments, where a reading exists
    "min_gauge_cm",
    "max_gust_kn",
    "max_wave_m",
]


class LeakageError(RuntimeError):
    """A feature tried to read ground truth. This is a bug in the caller, and
    it must be loud: a silent fallback here would let an outcome column ride
    into training and produce exactly the too-good-to-be-true number this
    package exists to refuse."""


def _guarded(record: dict, key: str, default=None):
    """The only way this module reads a booking. The outcome block and every
    underscored (latent) key are off-limits by construction."""
    if key == "outcome" or key.startswith("_"):
        raise LeakageError(
            f"build_features tried to read {key!r} - that is ground truth, "
            f"and features are decision-time knowledge only.")
    return record.get(key, default)


def build_features(record: dict) -> list[float]:
    """One booking record -> one vector, in FEATURE_COLUMNS order.

    Works identically whether or not the record still carries its outcome
    block, because it never looks - the test deletes the block and asserts
    the vectors match byte for byte.
    """
    facts = _guarded(record, "facts", {}) or {}
    commercial = _guarded(record, "commercial", {}) or {}
    episodes = facts.get("active_episodes", [])
    candidates = facts.get("candidates", [])

    on_primary = [e for e in episodes if e.get("on_primary_route")]
    elsewhere = [e for e in episodes if not e.get("on_primary_route")]
    ahead_primary = [e for e in on_primary if e.get("days_to_passage", 0) >= 0]
    soonest = min(ahead_primary, key=lambda e: e.get("days_to_passage", 0), default=None)

    def count_type(event_type):
        return float(sum(1 for e in on_primary if e.get("type") == event_type))

    # The cheapest escape on file, by the routing premium it charges. "Best"
    # here is a decision-time notion (cost index), never the realized winner.
    if candidates:
        cheapest = min(candidates, key=lambda c: c.get("added_cost_index", 0))
        best_alt_transit = float(cheapest.get("added_transit_days", 0))
        best_alt_cost = float(cheapest.get("added_cost_index", 0))
    else:
        best_alt_transit = NO_ALTERNATE_TRANSIT
        best_alt_cost = NO_ALTERNATE_COST

    # Month of year from the ETD string - seasonality is real information (a
    # winter gale season, a low-water summer) and costs nothing to expose.
    etd = _guarded(record, "etd", "") or ""
    month = float(int(etd[5:7])) if len(etd) >= 7 else 0.0

    gauges = [e["gauge_cm"] for e in episodes if "gauge_cm" in e]
    gusts = [e["gust_kn"] for e in episodes if "gust_kn" in e]
    waves = [e["wave_m"] for e in episodes if "wave_m" in e]

    values = {
        "slack_days": float(_guarded(record, "deadline_slack_days", 0)),
        "primary_transit_days": float(facts.get("primary_transit_days", 0)),
        "days_since_departure": float(facts.get("days_since_departure", 0)),
        "cold_chain": 1.0 if _guarded(record, "cold_chain") else 0.0,
        "month_of_year": month,
        "freight_eur": float(commercial.get("freight_eur", 0)),
        "late_eur_per_day": float(commercial.get("late_eur_per_day", 0)),
        "breach_eur": float(commercial.get("breach_eur", 0)),
        "transfer_risk_eur": float(commercial.get("transfer_risk_eur", 0)),
        "n_alternates": float(len(candidates)),
        "best_alt_added_transit_days": best_alt_transit,
        "best_alt_added_cost_index": best_alt_cost,
        "carrier_on_time_rate": float(facts.get("carrier_on_time_rate", 0.9)),
        "n_episodes_primary": float(len(on_primary)),
        "n_strike_primary": count_type("strike"),
        "n_weather_primary": count_type("weather"),
        "n_congestion_primary": count_type("congestion"),
        "n_geopolitical_primary": count_type("geopolitical"),
        "n_customs_primary": count_type("customs"),
        "max_severity_rank_primary": float(max(
            (SEVERITY_RANK.get(e.get("severity"), 0) for e in on_primary), default=0)),
        "est_delay_lo_primary": float(max(
            (e.get("expected_delay_days", [0, 0])[0] for e in on_primary), default=0)),
        "est_delay_hi_primary": float(max(
            (e.get("expected_delay_days", [0, 0])[1] for e in on_primary), default=0)),
        "worst_episode_days_running": float(max(
            (e.get("days_into_episode", 0) for e in on_primary), default=0)),
        # Schedule geometry: how soon is the disrupted chokepoint reached?
        # An episode three weeks ahead of the passage will usually have blown
        # over by the time the vessel arrives - this is the feature that
        # carries that, and it is pure decision-time schedule knowledge.
        "min_days_to_passage_primary": float(min(
            (e.get("days_to_passage", 0) for e in on_primary), default=99)),
        "n_episodes_ahead_primary": float(sum(
            1 for e in on_primary if e.get("days_to_passage", 0) >= 0)),
        # The estimates over episodes whose passage is still ahead. In the
        # synthetic world the generator already keeps astern episodes off the
        # booking's picture, so today these mirror the all-episode columns -
        # they stay separate because a real risk feed would carry astern
        # events too, and this is the pair of columns that would then split
        # "how loud is the board" from "how much of it is in my path".
        "est_delay_hi_ahead_primary": float(max(
            (e.get("expected_delay_days", [0, 0])[1] for e in ahead_primary), default=0)),
        "sum_est_mid_ahead_primary": float(sum(
            (e.get("expected_delay_days", [0, 0])[0]
             + e.get("expected_delay_days", [0, 0])[1]) / 2 for e in ahead_primary)),
        # The soonest-passage episode, described AS ONE THING. The aggregates
        # above decouple - the max estimate and the min days-to-passage can
        # come from different episodes - and the question "will the next
        # disruption on my path still be alive when I reach it" needs one
        # episode's age, size and distance kept together.
        "soonest_ep_days_into": float(soonest.get("days_into_episode", 0)) if soonest else 0.0,
        "soonest_ep_est_hi": float(soonest.get("expected_delay_days", [0, 0])[1]) if soonest else 0.0,
        "soonest_ep_is_strike": 1.0 if soonest and soonest.get("type") == "strike" else 0.0,
        "soonest_ep_is_weather": 1.0 if soonest and soonest.get("type") == "weather" else 0.0,
        "soonest_ep_is_congestion": 1.0 if soonest and soonest.get("type") == "congestion" else 0.0,
        "soonest_ep_is_geopolitical": 1.0 if soonest and soonest.get("type") == "geopolitical" else 0.0,
        "soonest_ep_is_customs": 1.0 if soonest and soonest.get("type") == "customs" else 0.0,
        "headline_count_total": float(sum(e.get("headline_count", 0) for e in episodes)),
        "n_episodes_alternates": float(len(elsewhere)),
        "est_delay_hi_alternates": float(max(
            (e.get("expected_delay_days", [0, 0])[1] for e in elsewhere), default=0)),
        "min_gauge_cm": float(min(gauges)) if gauges else NO_GAUGE_CM,
        "max_gust_kn": float(max(gusts)) if gusts else 0.0,
        "max_wave_m": float(max(waves)) if waves else 0.0,
    }

    # The dict-then-list construction exists so this assertion can exist: the
    # vector and FEATURE_COLUMNS cannot drift apart without failing here.
    assert set(values) == set(FEATURE_COLUMNS), "features drifted from FEATURE_COLUMNS"
    return [values[name] for name in FEATURE_COLUMNS]


def build_matrix(records: list[dict]) -> list[list[float]]:
    """Vectors for a whole book, in the book's order."""
    return [build_features(record) for record in records]
