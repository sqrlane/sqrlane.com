"""ml/models.py - the model registry: one common surface, four kinds of brain.

Every backend, from a majority vote to TabPFN, wears the same two methods:

    model.fit(records, labels)     records: booking dicts, outcome stripped
    model.predict(records)         -> one prediction per record

The surface takes RECORDS rather than matrices because the most important
baseline in the registry is not a learner at all: "rules" is the SHIPPED
decision engine (src.route_advisor.decide_with_rules), and it reads a
booking's facts, not a feature vector. Everything statistical converts to
vectors internally through ml/features.py - the one authoritative feature
list - so no model ever sees a column that file does not bless.

Three tasks share the registry:

    action  - classify reroute / hold / no-action (labels are strings)
    delay   - regress days of delay on the do-nothing path
    breach  - probability the deadline breaks (predict returns p in [0, 1])

scikit-learn and TabPFN are imported lazily, inside the factories, so this
module imports clean on a machine that has neither - the stdlib baselines and
the rules engine must run with zero installs. A factory whose dependency is
missing raises DependencyMissing with a readable reason, and ml/evaluate.py
turns that into a skipped row rather than a crash.
"""

from collections import Counter

from ml import features

ACTION_LABELS = ["no-action", "hold", "reroute"]


class DependencyMissing(RuntimeError):
    """This backend cannot run here, and the message says why and what to
    install. Raised at construction time so the harness can skip the backend
    before wasting a fit."""


# ---------------------------------------------------------------------------
# Stdlib baselines - the floor every learner has to clear
# ---------------------------------------------------------------------------


class MajorityClass:
    """Predicts whatever the training labels said most often. Not a straw man:
    on a book that is mostly fine, "do nothing" is a strong policy, and any
    model that cannot beat this one has learned nothing worth shipping."""

    def fit(self, records, labels):
        self.answer = Counter(labels).most_common(1)[0][0]
        return self

    def predict(self, records):
        return [self.answer] * len(records)


class MeanValue:
    """The regression twin: predicts the training mean, always."""

    def fit(self, records, labels):
        self.answer = sum(labels) / len(labels) if labels else 0.0
        return self

    def predict(self, records):
        return [self.answer] * len(records)


class BaseRate:
    """The probability twin: predicts the training prevalence, always. Its
    Brier score is the number a calibrated model has to beat."""

    def fit(self, records, labels):
        self.answer = sum(labels) / len(labels) if labels else 0.0
        return self

    def predict(self, records):
        return [self.answer] * len(records)


class DeskEstimate:
    """What a desk would write down without a model: the worst published
    delay estimate among episodes on the primary route. For the delay task it
    predicts that number; for the breach task it says 1.0 when that number
    beats the slack and 0.0 otherwise. It is the policy the delay and breach
    models are actually competing with, the way "rules" is for the action
    task - beating the mean is easy, beating the desk is the real bar."""

    def __init__(self, task):
        self.task = task

    def fit(self, records, labels):
        return self

    def _worst_estimate(self, record):
        episodes = (record.get("facts", {}) or {}).get("active_episodes", [])
        return max((e.get("expected_delay_days", [0, 0])[1]
                    for e in episodes if e.get("on_primary_route")), default=0)

    def predict(self, records):
        if self.task == "delay":
            return [float(self._worst_estimate(r)) for r in records]
        return [1.0 if self._worst_estimate(r) > r.get("deadline_slack_days", 0) else 0.0
                for r in records]


# ---------------------------------------------------------------------------
# The shipped rules engine, scored like any other model
# ---------------------------------------------------------------------------


class ShippedRules:
    """src.route_advisor.decide_with_rules, run against the synthetic world.

    This is the policy the product actually ships when no LLM answers, so it
    is the baseline that matters: a learner that cannot beat it adds nothing,
    and one that beats it says exactly how much a trained model would be
    worth. The assessment it needs is built by the SHIPPED build_assessment -
    imported, never copied - fed with events reconstructed from the booking's
    decision-time facts, so the engine sees exactly what it would see in
    production: the estimates, never the ground truth.

    Note its structural handicap, because it is real and not a rigged fight:
    the engine was built for a board reviewed as a disruption lands, so it
    takes every visible episode's published estimate at face value - it
    never asks whether the episode will still be alive when the vessel
    actually reaches that chokepoint. The learners get each episode's age,
    type and days-to-passage and can learn that a five-day strike three
    weeks ahead of the passage is usually nobody's problem; the engine
    cannot. That gap is a finding about the shipped policy, not an accident
    of the harness. (The world already keeps episodes at chokepoints the
    vessel has passed off every booking's picture, for engine and learners
    alike - the fight is over timing, not position.)
    """

    def __init__(self):
        # Imported lazily so `import ml.models` stays dependency-light; the
        # src package is part of this repo, so this only fails if the repo
        # itself is broken - and then loudly.
        import json as _json

        from src import config as _config
        from src.route_advisor import build_assessment, decide_with_rules

        self._build_assessment = build_assessment
        self._decide = decide_with_rules
        with open(_config.ROUTES_FILE, encoding="utf-8") as handle:
            self._routes = {r["route_id"]: r for r in _json.load(handle)["routes"]}

    def fit(self, records, labels):
        return self  # a rules engine does not train - that is the point

    @staticmethod
    def _events_from_facts(record):
        """The booking's observed episodes, reshaped into the event dicts the
        advisor's assessment expects. Only observed fields cross over."""
        episodes = (record.get("facts", {}) or {}).get("active_episodes", [])
        return [{
            "event_id": e["episode_id"],
            "chokepoint": e["chokepoint"],
            "type": e["type"],
            "severity": e["severity"],
            "expected_delay_days": e.get("expected_delay_days"),
            # The two facts that let the advisor ask its timing question -
            # how old the episode is, and how far off this booking's passage
            # is. Both are decision-time observations, not outcomes.
            "days_into_episode": e.get("days_into_episode"),
            "days_to_passage": e.get("days_to_passage"),
            "title": f"{e['type']} at {e['chokepoint']} (synthetic episode)",
        } for e in episodes]

    def predict(self, records):
        decisions = []
        for record in records:
            assessment = self._build_assessment(
                record, self._routes, self._events_from_facts(record))
            verdict = self._decide(assessment)
            decision = verdict.get("decision")
            decisions.append(decision if decision in ACTION_LABELS else "no-action")
        return decisions


# ---------------------------------------------------------------------------
# scikit-learn, behind the matrix adapter
# ---------------------------------------------------------------------------


class SklearnModel:
    """Any sklearn estimator, fed through ml/features.py. For the breach task
    predict() returns the positive-class probability, because a probability
    is what that task is for - a hard 0/1 answer would waste the model."""

    def __init__(self, estimator, task):
        self.estimator = estimator
        self.task = task

    def fit(self, records, labels):
        self.estimator.fit(features.build_matrix(records), labels)
        return self

    def predict(self, records):
        matrix = features.build_matrix(records)
        if self.task == "breach":
            classes = list(self.estimator.classes_)
            column = classes.index(1)
            return [float(row[column]) for row in self.estimator.predict_proba(matrix)]
        predictions = self.estimator.predict(matrix)
        if self.task == "delay":
            # Plain floats, not numpy scalars - the report is JSON and the
            # stdlib metrics should not depend on numpy being importable.
            return [float(p) for p in predictions]
        return [str(p) for p in predictions]


def _need_sklearn():
    try:
        import sklearn  # noqa: F401 - the import is the check
    except ImportError as exc:
        raise DependencyMissing(
            "scikit-learn is not installed. Install the ML layer's own "
            "requirements (pip install -r ml/requirements.txt) - the ROOT "
            "requirements.txt deliberately does not carry it, because the "
            "demo and the Vercel bundle must not depend on this package."
        ) from exc


def _sklearn_linear(task):
    _need_sklearn()
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    if task == "delay":
        estimator = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    else:
        estimator = make_pipeline(StandardScaler(),
                                  LogisticRegression(max_iter=2000))
    return SklearnModel(estimator, task)


def _sklearn_gbm(task):
    _need_sklearn()
    from sklearn.ensemble import (HistGradientBoostingClassifier,
                                  HistGradientBoostingRegressor)

    if task == "delay":
        estimator = HistGradientBoostingRegressor(random_state=0)
    else:
        estimator = HistGradientBoostingClassifier(random_state=0)
    return SklearnModel(estimator, task)


def _tabpfn(task):
    # The adapter owns the import, the readable failure and the license
    # notes; a missing tabpfn arrives here as DependencyMissing so the
    # harness can skip it exactly like a missing sklearn.
    from ml import tabpfn_adapter

    try:
        if task == "delay":
            estimator = tabpfn_adapter.make_regressor()
        else:
            estimator = tabpfn_adapter.make_classifier()
    except tabpfn_adapter.TabPFNUnavailable as exc:
        raise DependencyMissing(str(exc)) from exc
    return SklearnModel(estimator, task)


# ---------------------------------------------------------------------------
# The registry - what ml/evaluate.py iterates over
# ---------------------------------------------------------------------------

# {task: {backend name: zero-argument factory}}. Order matters only for how
# the report reads: baselines first, then the shipped policy, then learners.
MODELS = {
    "action": {
        "majority": MajorityClass,
        "rules": ShippedRules,
        "logistic": lambda: _sklearn_linear("action"),
        "gbm": lambda: _sklearn_gbm("action"),
        "tabpfn": lambda: _tabpfn("action"),
    },
    "delay": {
        "mean": MeanValue,
        "desk-estimate": lambda: DeskEstimate("delay"),
        "ridge": lambda: _sklearn_linear("delay"),
        "gbm": lambda: _sklearn_gbm("delay"),
        "tabpfn": lambda: _tabpfn("delay"),
    },
    "breach": {
        "base-rate": BaseRate,
        "desk-estimate": lambda: DeskEstimate("breach"),
        "logistic": lambda: _sklearn_linear("breach"),
        "gbm": lambda: _sklearn_gbm("breach"),
        "tabpfn": lambda: _tabpfn("breach"),
    },
}


def target_for(task: str, record: dict):
    """The ground-truth label for one task, read from the outcome block. Only
    the harness calls this - models never see the record's outcome, because
    the harness strips it before records reach fit() or predict()."""
    outcome = record["outcome"]
    if task == "action":
        return outcome["optimal_action"]
    if task == "delay":
        return float(outcome["realized_delay_days_stay"])
    if task == "breach":
        return int(bool(outcome["deadline_breached"]))
    raise ValueError(f"unknown task {task!r}")
