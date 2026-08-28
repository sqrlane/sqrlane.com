"""ml/tabpfn_adapter.py - TabPFN behind a door that fails readably.

TabPFN (github.com/PriorLabs/TabPFN) is a tabular foundation model: a
transformer pre-trained on millions of synthetic tables, wearing the standard
sklearn fit/predict surface. No gradient descent happens at fit time - the
"training set" is handed to a single forward pass as context - and its
published strength is exactly this repo's regime: small-to-medium tables,
which is what a forwarder's booking history is. That is why it earns a slot
in the registry next to the gradient-boosting workhorse.

It is NOT installed in every environment this repo runs in, and it cannot be:
the package needs PyTorch, and its first run downloads model weights from
Hugging Face - the build sandbox blocks that host outright. So this adapter's
whole job is to degrade well: if tabpfn imports, hand back its estimators
unchanged; if not, raise ONE exception type whose message says exactly how to
enable it and what the license and data-privacy tradeoffs are. Nothing else
in ml/ imports tabpfn - this file is the only door, the same pattern as
src/llm.py being the only door to a provider.

LICENSE NOTE (read before shipping anything built on this):

  * The TabPFN code and the v2 weights are under the Prior Labs License -
    Apache 2.0 plus an attribution condition: distributing anything built on
    them requires visible "Built with PriorLabs-TabPFN" attribution.
  * The newer 2.5 / 3 generation weights are NON-COMMERCIAL. Benchmarking
    them internally, as this harness would, is fine; putting them behind a
    product is a license decision that has to be made deliberately, not
    inherited from a requirements file.
  * tabpfn-client also exists - a thin client for Prior Labs' hosted API, no
    torch and no local weights. It SENDS THE TABLE TO PRIOR LABS' SERVERS.
    Synthetic bookings are harmless to send; a real forwarder's booking
    history is customer data, and pointing the client at it without a
    data-processing agreement and explicit sign-off would be a privacy
    failure, not a convenience. This adapter deliberately does not wire it.

Status here: UNWITNESSED. This sandbox can neither install torch nor reach
huggingface.co, so TabPFN has never actually run against this repo's
synthetic world - the adapter is built to the package's published sklearn
surface, like the repo's other unwitnessed sources are built to their
published API shapes. ml/README.md says the same thing louder.
"""


class TabPFNUnavailable(RuntimeError):
    """TabPFN cannot run in this environment. The message carries the enable
    steps and the caveats, so the harness can print it verbatim and a reader
    knows what to do without opening this file."""


_ENABLE_MESSAGE = (
    "TabPFN is not installed, so the tabpfn backend is skipped. To enable it:\n"
    "  1. pip install -r ml/requirements.txt   (numpy + scikit-learn)\n"
    "  2. pip install tabpfn                   (pulls PyTorch - several GB)\n"
    "  3. run once with network access to huggingface.co - the first fit\n"
    "     downloads the model weights from Hugging Face, and a sandbox that\n"
    "     blocks that host (like the one this repo is built in) cannot ever\n"
    "     run it. That is expected there, not a bug.\n"
    "License: TabPFN code and v2 weights are Prior-Labs-License (Apache-2.0\n"
    "plus required 'Built with PriorLabs-TabPFN' attribution when you\n"
    "distribute); the 2.5/3 weights are NON-COMMERCIAL - internal\n"
    "benchmarking is fine, shipping is a license decision. tabpfn-client\n"
    "(their hosted API, no torch) exists but sends the data to Prior Labs'\n"
    "servers - never point it at real customer bookings without sign-off."
)


def _import_tabpfn():
    try:
        import tabpfn
    except ImportError as exc:
        raise TabPFNUnavailable(_ENABLE_MESSAGE) from exc
    return tabpfn


def make_classifier():
    """A TabPFNClassifier, or TabPFNUnavailable with the full story."""
    tabpfn = _import_tabpfn()
    return tabpfn.TabPFNClassifier()


def make_regressor():
    """A TabPFNRegressor, or TabPFNUnavailable with the full story."""
    tabpfn = _import_tabpfn()
    return tabpfn.TabPFNRegressor()
