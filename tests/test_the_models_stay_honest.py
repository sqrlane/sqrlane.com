"""The ML layer is prepared, not wired - and its numbers cannot be invented.

ml/ exists to answer "what would a trained model be worth here?" without ever
producing the one thing this project refuses to produce: a metric that is not
real. Two ways that could quietly happen, and this file blocks both.

The first is WIRING: the demo starts depending on the ML layer, or the ML
layer starts reading the demo's book around the TMS connector, or the Vercel
bundle starts shipping models nobody promised. Structural checks hold each of
those doors shut.

The second is CIRCULARITY, which is subtler: a model trained on the rules
engine's own output relearns an if-statement and scores beautifully; a
feature that peeks at the outcome block scores even better. Either way the
number is fiction. So the generator is checked for determinism (the exact
dataset behind any report can be reproduced by anyone), the features are
checked to be blind to ground truth, the time split is checked not to leak an
episode across the boundary - and a small end-to-end run asserts both that
learning genuinely happens (the learner beats the majority baseline) and
that it stays imperfect (nothing hits 100%; in a world with honest noise, a
perfect score means the answer key leaked).

Run it:

    python -m unittest tests.test_the_models_stay_honest -v

Standard library throughout; the one end-to-end learning test skips itself
politely where scikit-learn is not installed.
"""

import ast
import copy
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
ML = ROOT / "ml"

try:
    import sklearn  # noqa: F401
    HAVE_SKLEARN = True
except ImportError:
    HAVE_SKLEARN = False

try:
    import tabpfn  # noqa: F401
    HAVE_TABPFN = True
except ImportError:
    HAVE_TABPFN = False


def python_files(folder):
    return sorted(p for p in folder.rglob("*.py") if "__pycache__" not in p.parts)


class TheDemoNeverDependsOnTheMLLayer(unittest.TestCase):
    """src/ must run exactly as before whether or not ml/ exists."""

    def test_src_contains_python_files(self):
        # The guard on the guard, same as the transport suite: an import scan
        # over an empty glob would pass while checking nothing.
        self.assertGreater(len(python_files(SRC)), 3,
                           f"Expected the components under {SRC}. Did the path move?")

    def test_nothing_in_src_imports_ml(self):
        offences = []
        for path in python_files(SRC):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split(".")[0] == "ml":
                            offences.append(f"{path.name}:{node.lineno} imports {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.level == 0 and node.module \
                            and node.module.split(".")[0] == "ml":
                        offences.append(f"{path.name}:{node.lineno} imports from {node.module}")
        self.assertEqual(offences, [], "\n".join([
            "",
            "src/ now imports the ML layer:",
            *(f"    {o}" for o in offences),
            "",
            "The ML layer is PREPARED, NOT WIRED. If wiring it is genuinely wanted,",
            "that is a product decision - and it drags numpy/scikit-learn into the",
            "demo's dependency set and the Vercel bundle, so it cannot happen as a",
            "side effect of one import.",
        ]))

    def test_root_requirements_carry_no_ml_dependency(self):
        # Vercel installs the ROOT requirements.txt. The ML stack lives in
        # ml/requirements.txt and nowhere else.
        text = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
        for package in ("numpy", "scikit-learn", "sklearn", "torch", "tabpfn"):
            self.assertNotIn(package, text,
                             f"{package!r} appeared in the root requirements.txt - the "
                             f"deployed demo must not install the ML stack. It belongs in "
                             f"ml/requirements.txt only.")

    def test_vercel_bundle_does_not_include_ml(self):
        config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
        include = config["functions"]["api/index.py"]["includeFiles"]
        # 'ml' as its own path token, so a legitimate '*.html' glob someday
        # cannot false-positive on the substring.
        self.assertIsNone(re.search(r"(^|[^A-Za-z])ml([^A-Za-z]|$)", include),
                          f"vercel.json includeFiles ({include!r}) now bundles ml/ - "
                          f"13 MB of synthetic data and reports the demo never reads.")


class TheTMSStaysTheOnlyDoorToTheBook(unittest.TestCase):
    """ml/ generates its own book. The demo's book stays behind the connector."""

    def test_ml_never_touches_the_demo_shipments_file(self):
        # String-level on purpose, and strict: not even a comment in ml/ may
        # name the demo's shipments file or its config handle, so there is
        # nothing to relax later "because it was already mentioned anyway".
        offences = []
        for path in python_files(ML):
            text = path.read_text(encoding="utf-8")
            for needle in ("SHIPMENTS_FILE", "shipments.json"):
                if needle in text:
                    offences.append(f"{path.name} mentions {needle}")
        self.assertEqual(offences, [], "\n".join([
            "",
            "ml/ now reaches for the demo's book:",
            *(f"    {o}" for o in offences),
            "",
            "tms.read_bookings() is the only door to the demo's shipments, and the",
            "ML layer does not get a second one - it works on the synthetic world",
            "its own generator writes.",
        ]))


class TheWorldIsReproducible(unittest.TestCase):
    """Same seed, same bytes - anyone can regenerate the dataset behind a report."""

    def test_same_seed_is_byte_identical_and_different_seed_is_not(self):
        from ml import synth
        first = json.dumps(synth.generate(bookings=40, seed=3, weeks=30))
        second = json.dumps(synth.generate(bookings=40, seed=3, weeks=30))
        self.assertEqual(first, second,
                         "Two runs with the same seed differed. Something in the "
                         "generator reads a clock or the global RNG, and the dataset "
                         "behind a report can no longer be reproduced or reviewed.")
        other = json.dumps(synth.generate(bookings=40, seed=4, weeks=30))
        self.assertNotEqual(first, other,
                            "Two different seeds produced identical worlds - the seed "
                            "is not actually driving the generator.")


class TheSyntheticBookMatchesTheRealSchema(unittest.TestCase):
    """A synthetic booking must carry every field a demo booking carries, so
    the TMS connector could one day point at this book without reshaping it.
    Schema parity has broken three times elsewhere in this repo - always by
    one producer gaining a field the other did not - hence a mechanical check
    rather than good intentions."""

    def test_synthetic_keys_are_a_superset_of_the_demo_record_keys(self):
        # The test reads the demo book directly - tests are allowed to; ml/
        # code is not, and the test above holds that.
        with open(ROOT / "data" / "shipments.json", encoding="utf-8") as handle:
            real = json.load(handle)["shipments"][0]
        from ml import synth
        world = synth.generate(bookings=5, seed=3, weeks=20)
        synthetic = world["bookings"][0]
        missing = set(real) - set(synthetic)
        self.assertEqual(missing, set(),
                         f"Synthetic bookings lost demo-book fields: {sorted(missing)}. "
                         f"The connector could no longer point at this book unchanged.")
        # And the commercial block, field for field - cost_of() reads it.
        missing_terms = set(real["commercial"]) - set(synthetic["commercial"])
        self.assertEqual(missing_terms, set(),
                         f"Synthetic commercial terms lost fields: {sorted(missing_terms)}.")


class TheFeaturesAreBlindToTheAnswer(unittest.TestCase):
    """If a feature can see the outcome, every score is fiction."""

    def test_no_feature_column_names_ground_truth(self):
        from ml import features
        for name in features.FEATURE_COLUMNS:
            self.assertFalse(
                name.startswith("_") or "outcome" in name or "realized" in name
                or "optimal" in name or "breached" in name,
                f"FEATURE_COLUMNS contains {name!r}, which smells of ground truth.")

    def test_deleting_the_outcome_block_changes_nothing(self):
        from ml import features, synth
        world = synth.generate(bookings=30, seed=3, weeks=30)
        for record in world["bookings"]:
            blinded = copy.deepcopy(record)
            del blinded["outcome"]
            self.assertEqual(features.build_features(record),
                             features.build_features(blinded),
                             f"Features for {record['id']} changed when the outcome "
                             f"block was deleted - something is reading the answer key.")

    def test_reading_the_outcome_raises_rather_than_leaks(self):
        # The fence itself: the guarded accessor must be loud, because a
        # silent default here is how a leak would look like a feature.
        from ml import features
        with self.assertRaises(features.LeakageError):
            features._guarded({"outcome": {}}, "outcome")
        with self.assertRaises(features.LeakageError):
            features._guarded({"_latent": 1}, "_latent")

    def test_vector_length_matches_the_authoritative_list(self):
        from ml import features, synth
        world = synth.generate(bookings=3, seed=3, weeks=20)
        vector = features.build_features(world["bookings"][0])
        self.assertEqual(len(vector), len(features.FEATURE_COLUMNS))
        self.assertTrue(all(isinstance(v, float) for v in vector))


class TheSplitDoesNotLeak(unittest.TestCase):
    """A disruption episode touches many bookings; scoring booking four of a
    strike the model trained on via bookings one to three is memorisation
    dressed as prediction. No episode id may appear on both sides."""

    def test_no_episode_id_lands_in_both_train_and_test(self):
        from ml import evaluate, synth
        world = synth.generate(bookings=400, seed=3)
        train, test, info = evaluate.split_by_time(world)
        train_episodes = {e["episode_id"] for b in train
                          for e in b["facts"]["active_episodes"]}
        test_episodes = {e["episode_id"] for b in test
                         for e in b["facts"]["active_episodes"]}
        self.assertEqual(train_episodes & test_episodes, set(),
                         "The time split leaked an episode across the boundary.")
        # And both sides must be real - a split that puts everything in train
        # would pass the assertion above while testing nothing.
        self.assertGreater(len(train), 100)
        self.assertGreater(len(test), 30)


@unittest.skipUnless(HAVE_SKLEARN, "scikit-learn is not installed - the learners "
                                   "cannot run here (pip install -r ml/requirements.txt)")
class LearningHappensAndStaysImperfect(unittest.TestCase):
    """The two-sided sanity check on the whole pipeline: the learner must beat
    the majority baseline (or the world has no learnable structure and every
    report is noise), and it must NOT be perfect (in a world with honest
    latent noise, 100% means the answer key leaked into the features).

    1200 bookings rather than a smaller book: episodes scale with the
    timeline, not the booking count, so a tiny run's test window can land on
    a freakishly quiet - or freakishly wild - few months and the margin
    becomes seed noise. This size is the smallest that held the margin
    across seeds while staying fast."""

    def test_gbm_beats_majority_and_scores_below_100_percent(self):
        from ml import evaluate, models, synth
        world = synth.generate(bookings=1200, seed=7)
        train, test, _ = evaluate.split_by_time(world)
        y_train = [models.target_for("action", r) for r in train]
        y_test = [models.target_for("action", r) for r in test]
        train_visible = evaluate.strip_outcomes(train)
        test_visible = evaluate.strip_outcomes(test)

        majority = models.MODELS["action"]["majority"]().fit(train_visible, y_train)
        majority_accuracy = evaluate.accuracy(y_test, majority.predict(test_visible))

        gbm = models.MODELS["action"]["gbm"]().fit(train_visible, y_train)
        gbm_accuracy = evaluate.accuracy(y_test, gbm.predict(test_visible))

        self.assertGreater(gbm_accuracy, majority_accuracy,
                           f"GBM ({gbm_accuracy:.3f}) did not beat the majority baseline "
                           f"({majority_accuracy:.3f}) - the world has lost its learnable "
                           f"structure, and every number in ml/reports/ is noise.")
        self.assertLess(gbm_accuracy, 1.0,
                        "GBM scored a perfect 100%. In a world with honest latent noise "
                        "that is not brilliance, it is leakage - the label, or something "
                        "derived from it, is reaching the features. Fix the generator or "
                        "the features; do not accept the circular result.")


class TheBestModelClaimTracksTheTable(unittest.TestCase):
    """The plain-language section's "best model" sentences are computed, not
    asserted. This has bitten twice: prose written when GBM led kept calling
    GBM the best after TabPFN overtook it, in the same file whose tables
    showed the truth. A report that contradicts its own table is this repo's
    hard-coded "live" chip all over again, so the winner is recomputed from
    the results and NAMED beside the number."""

    @staticmethod
    def _report(action_winner):
        scores = {"majority": 0.84, "rules": 0.76,
                  "gbm": 0.88, "tabpfn": 0.88}
        scores[action_winner] = 0.90
        blank = {t: {p: 0 for p in ("no-action", "hold", "reroute")}
                 for t in ("no-action", "hold", "reroute")}
        action = {name: {"accuracy": acc, "macro_f1": 0.5, "confusion": blank}
                  for name, acc in scores.items()}
        return {
            "honesty": "test", "world": {"bookings": 1, "weeks": 1, "seed": 1},
            "split": {"cut_date": "2026-01-01", "train": 1, "test": 1,
                      "dropped_straddling_bookings": 0, "train_episodes": 1,
                      "test_episodes": 1},
            "environment": {"python": "x", "scikit_learn": None},
            "results": {
                "action": action,
                "delay": {"mean": {"mae_days": 7.0, "p90_abs_error_days": 8.0},
                          "gbm": {"mae_days": 2.4, "p90_abs_error_days": 5.0},
                          "tabpfn": {"mae_days": 2.3, "p90_abs_error_days": 5.3}},
                "breach": {"base-rate": {"roc_auc": 0.5, "brier": 0.27},
                           "gbm": {"roc_auc": 0.86, "brier": 0.13},
                           "tabpfn": {"roc_auc": 0.88, "brier": 0.128}},
            },
        }

    def test_the_named_winner_is_the_argmax_whoever_wins(self):
        from ml import evaluate
        for winner in ("tabpfn", "gbm"):
            rendered = evaluate.render_markdown(self._report(winner))
            self.assertIn(f"The best trained model ({winner}) gets 90%", rendered)
        # And the delay/breach winners are computed too, not inherited.
        rendered = evaluate.render_markdown(self._report("gbm"))
        self.assertIn("best model (tabpfn) is off by 2.3", rendered)
        self.assertIn("best model's (tabpfn) ROC-AUC", rendered)

    def test_a_baseline_can_never_be_called_the_best_trained_model(self):
        from ml import evaluate
        report = self._report("gbm")
        # Even if a baseline outscores every learner, the "best trained
        # model" sentence must not crown it.
        report["results"]["action"]["majority"]["accuracy"] = 0.99
        report["results"]["action"]["rules"]["accuracy"] = 0.99
        rendered = evaluate.render_markdown(report)
        self.assertIn("The best trained model (gbm)", rendered)


class TabPFNDegradesReadably(unittest.TestCase):
    """Where tabpfn is not installed (this sandbox, most machines), asking for
    it must produce instructions and the license story - not a stack trace."""

    @unittest.skipIf(HAVE_TABPFN, "tabpfn IS installed here - the degradation "
                                  "path does not apply")
    def test_the_failure_names_the_enable_steps_and_the_license(self):
        from ml import tabpfn_adapter
        with self.assertRaises(tabpfn_adapter.TabPFNUnavailable) as caught:
            tabpfn_adapter.make_classifier()
        message = str(caught.exception)
        for expected in ("pip install -r ml/requirements.txt", "pip install tabpfn",
                         "huggingface.co", "NON-COMMERCIAL", "tabpfn-client"):
            self.assertIn(expected, message,
                          f"The TabPFN unavailable message no longer mentions "
                          f"{expected!r} - it must carry the enable steps, the "
                          f"license note and the data-privacy warning in full.")

    @unittest.skipIf(HAVE_TABPFN, "tabpfn IS installed here")
    def test_the_harness_skips_it_rather_than_crashing(self):
        from ml import models
        with self.assertRaises(models.DependencyMissing):
            models.MODELS["action"]["tabpfn"]()


if __name__ == "__main__":
    unittest.main()
