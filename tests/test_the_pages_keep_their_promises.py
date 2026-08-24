"""The three pages make four promises about themselves. This file holds them.

Each of these was a hand-run script during the build, which is the same as not
having it: a guard nobody runs is a guard that has already stopped working. They
are tests now, so `python -m unittest discover -s tests` covers all four.

  * **The edge is source proximity, never a language.** A disruption is known
    locally before it is news globally, and that holds wherever in the world it
    happens. Naming a language makes a general capability look like one rehearsed
    trick, so the landing page and the dashboard say "regional" and
    "international wires" instead. Real outlet names are fine - they identify a
    source, they do not claim an edge.
  * **No invented metric.** The reference admin this shell is modelled on puts a
    "+12% vs. previous 30 days" delta on every stat card. Lanewatch has no
    history to compare a run against, so that number would be fabricated - and a
    fabricated number is the one thing this project refuses to produce.
  * **The Worker names are ours.** Never the names the reference product ships.
  * **Nothing loads from off-origin.** No CDN, no web font, no map tile. Flaky
    wifi in front of an audience must not be able to strip the typography or
    blank a page.

What "user-visible" means here matters, because the dashboard writes most of its
text from JavaScript: comments are stripped, code is not. A word that appears
only in a `/* ... */` explaining why it is avoided has not been said to anyone.

The whitepaper is deliberately outside the language rule. It is a technical
document that has to discuss where a model came from - "Teuken-7B came out of a
German research consortium", "Mistral is French" - and that is provenance, not a
claim about the detection edge. It is inside every other rule here.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"

LANDING = STATIC / "landing.html"
DASHBOARD = STATIC / "index.html"
WHITEPAPER = STATIC / "whitepaper.html"
ALL_PAGES = (LANDING, DASHBOARD, WHITEPAPER)

# Named languages. "English" is on the list for the same reason as the rest: the
# benchmark is "the international wires", not a language, and the data keys that
# still say english_wire are code, not copy.
LANGUAGES = ["German", "Arabic", "French", "Dutch", "Spanish", "English",
             "Deutsch", "multilingual", "Multilingual", "non-English"]

# The reference product's Worker names. Ours are ours.
BORROWED_NAMES = ["Rate Manager", "DocuMind", "Track & Trace", "Track and Trace", "Copilot"]

# The invented delta the reference stat card carries and this one must not.
INVENTED_METRIC = ["vs. previous", "vs previous", "% vs.", "since last month"]


def visible(page: Path) -> str:
    """Page text with comments removed - what a reader could actually be told.

    Block comments and HTML comments go; the code itself stays, because the
    dashboard builds nearly all of its copy from template literals inside
    <script>. Line comments are only stripped when they own their line, so a
    URL's // is never mistaken for one.
    """
    text = page.read_text(encoding="utf-8")
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"^[ \t]*//.*$", " ", text, flags=re.M)
    return text


class TheEdgeIsProximityNotALanguage(unittest.TestCase):
    """The pitch never names a language, because the edge is not one."""

    def test_the_landing_page_and_dashboard_name_no_language(self):
        offences = []
        for page in (LANDING, DASHBOARD):
            text = visible(page)
            for word in LANGUAGES:
                for match in re.finditer(rf"\b{re.escape(word)}\b", text):
                    line = text.count("\n", 0, match.start()) + 1
                    context = text[max(0, match.start() - 60):match.start() + 60]
                    offences.append(f"{page.name}:{line} says {word!r} — …{context.strip()}…")

        self.assertEqual(offences, [], "\n".join([
            "",
            "A language is named in copy a reader will see:",
            *(f"    {o}" for o in offences),
            "",
            "The edge is that the sources are close to the event, which holds wherever in",
            "the world it happens. Say 'regional' and 'international wires'. An outlet's",
            "own name is fine — that identifies a source rather than claiming an edge.",
        ]))

    def test_the_whitepaper_is_the_stated_exception(self):
        # A guard on the guard: if the whitepaper ever stops discussing model
        # provenance, the carve-out above is dead wording and should be removed
        # rather than left as a hole someone could widen.
        self.assertRegex(visible(WHITEPAPER), r"\b(German|French)\b",
                         "The whitepaper is exempted because it names where models come "
                         "from. If it no longer does, drop the exemption.")


class NoInventedMetric(unittest.TestCase):
    """Every number on screen is counted from the run that just happened."""

    def test_no_page_carries_a_period_over_period_delta(self):
        offences = []
        for page in ALL_PAGES:
            text = visible(page)
            for phrase in INVENTED_METRIC:
                if phrase in text:
                    line = text.count("\n", 0, text.index(phrase)) + 1
                    offences.append(f"{page.name}:{line} carries {phrase!r}")

        self.assertEqual(offences, [], "\n".join([
            "",
            "A period-over-period delta appears on a page:",
            *(f"    {o}" for o in offences),
            "",
            "There is no history to compare a run against, so any such number is invented.",
            "The stat card keeps the reference's anatomy and puts a fact from the run in",
            "the pill instead.",
        ]))

    def test_the_dashboard_has_no_ad_hoc_hint_blocks(self):
        # Empty states name the next action. A bare .hint was the thing they
        # replaced, and one creeping back is how a view goes quiet again.
        self.assertNotIn('class="hint"', DASHBOARD.read_text(encoding="utf-8"),
                         "An ad-hoc .hint block is back. Empty states should use "
                         "emptyState(), which names the next action.")


class TheWorkerNamesAreOurs(unittest.TestCase):
    """Never the reference product's names - not even in a comment."""

    def test_no_borrowed_name_appears_anywhere_it_is_served(self):
        from src import orchestrator, roster

        payload = orchestrator.run_cycle(live=False, inject=True, use_llm=False)
        haystacks = {
            "static/index.html": DASHBOARD.read_text(encoding="utf-8"),
            "static/landing.html": LANDING.read_text(encoding="utf-8"),
            "static/whitepaper.html": WHITEPAPER.read_text(encoding="utf-8"),
            "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
            "src/roster.py": (ROOT / "src" / "roster.py").read_text(encoding="utf-8"),
            "the served Worker names": " ".join(w["name"] for w in payload["workers"]),
            "the run payload": repr(payload),
        }
        offences = [f"{where} contains {name!r}"
                    for where, hay in haystacks.items()
                    for name in BORROWED_NAMES if name in hay]

        self.assertEqual(offences, [], "\n".join([
            "",
            "A reference product's Worker name has appeared:",
            *(f"    {o}" for o in offences),
            "",
            "The product name and the roster are ours. This check reads comments and the",
            "run payload as well as the copy, because it once caught one in a comment.",
        ]))
        # Guard on the guard: an empty roster would pass every assertion above.
        self.assertGreater(len(roster.ROSTER), 5, "The roster is empty - this tests nothing.")


class NothingLoadsFromOffOrigin(unittest.TestCase):
    """No CDN, no web font, no tile server. The pages carry their own assets."""

    ASSET_PATTERNS = (
        r'<script[^>]+src=["\']([^"\']+)',
        r'<link[^>]+href=["\']([^"\']+)',
        r'<img[^>]+src=["\']([^"\']+)',
        r'<iframe[^>]+src=["\']([^"\']+)',
        r'url\(\s*["\']?([^)"\']+)',
        r'@import\s+["\']([^"\']+)',
    )

    def test_every_asset_is_same_origin(self):
        offences, found = [], 0
        for page in ALL_PAGES:
            text = page.read_text(encoding="utf-8")
            for pattern in self.ASSET_PATTERNS:
                for ref in re.findall(pattern, text, re.I):
                    found += 1
                    if re.match(r"https?://|//", ref):
                        offences.append(f"{page.name} loads {ref}")

        self.assertEqual(offences, [], "\n".join([
            "",
            "A page loads something from another host:",
            *(f"    {o}" for o in offences),
            "",
            "Fonts are served from static/fonts/ and everything else is inline, so wifi",
            "that fails in front of an audience cannot strip the page.",
        ]))
        self.assertGreater(found, 0, "No asset references found at all - did the parse break?")

    def test_every_fetch_is_same_origin(self):
        # An external API call is the same failure with a different shape: the
        # page's own /api routes are fine, another host's are not.
        offences = []
        for page in ALL_PAGES:
            for url in re.findall(r'fetch\(\s*["\'`]([^"\'`]+)', page.read_text(encoding="utf-8")):
                if re.match(r"https?://|//", url):
                    offences.append(f"{page.name} fetches {url}")
        self.assertEqual(offences, [], "\n".join([
            "", "A page fetches from another host:", *(f"    {o}" for o in offences)]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
