"""ml/ - the machine-learning layer that would power SQRlane's agents.

PREPARED, NOT WIRED. Nothing in src/ imports this package, the demo does not
depend on it, and the Vercel bundle does not ship it -
tests/test_the_models_stay_honest.py fails the build if any of that changes.

Why it exists at all: the shipped Route Advisor decides with a rules engine (or
an LLM). The obvious next step - "train a model" - had a blocker: the repo had
no ground truth. Training on the rules engine's own output would just relearn
an if-statement, and an accuracy number from that would be exactly the invented
metric this project refuses to produce. So this package first builds a
synthetic WORLD (ml/synth.py) whose outcomes come from a structural model the
learners never see, and only then trains and scores models against it. Every
number this package produces describes that simulated world, never real
freight, and must never appear on the product pages.

The pieces:

    ml/synth.py           the synthetic TMS world - bookings, disruption
                          episodes, and realized outcomes (the ground truth)
    ml/features.py        the one authoritative feature list, with a
                          mechanical guard against outcome leakage
    ml/models.py          the model registry: stdlib baselines, the SHIPPED
                          rules engine as a policy baseline, scikit-learn,
                          and TabPFN via the adapter
    ml/tabpfn_adapter.py  TabPFN behind a door that fails readably when the
                          package (or its weights) is not available
    ml/evaluate.py        the harness: time-based split, three tasks, every
                          available backend, reports in ml/reports/
"""
