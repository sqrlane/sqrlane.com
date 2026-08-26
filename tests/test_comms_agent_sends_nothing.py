"""The Comms Agent drafts emails. It never sends them.

That claim is made in the README, on the landing page, in the dashboard and out
loud during the demo, so it needs something better than everyone's good
intentions holding it up. This file is that something.

Two kinds of check:

  * Structural - no way to send exists. Every .py under src/ is parsed and every
    import it makes is inspected. If a transport library ever appears, this fails
    and names the file and line.
  * Behavioural - a full offline cycle is run and every draft it produces is
    checked for the "not sent" marker and the approval gate.

An important distinction, because it is easy to get wrong later: this is NOT a
"no networking" rule. The app makes real HTTP calls on purpose - GDELT,
PEGELONLINE, the news feeds, the public data APIs and the LLM provider all go
out over `requests`, and
the live news pull is the demo's credibility anchor. What must not exist is a
way to send a *message* to a carrier or a customer. So `requests` is fine and
`smtplib` is not.

Run it:

    python -m unittest discover -s tests

No test framework to install - this is the standard library. pytest will also
pick it up if you happen to have it.
"""

import ast
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"

# Root module names that can put a message in front of a human somewhere else.
# Matched on the root, so `from email.mime.text import MIMEText` is caught by
# "email". Add to this list rather than relaxing it.
TRANSPORT = {
    # --- stdlib mail and file transports ---
    "smtplib",      # the obvious one
    "email",        # message construction - no reason to build one we can't send
    "imaplib", "poplib",
    "ftplib", "telnetlib", "nntplib",
    # --- third-party mail services ---
    "aiosmtplib", "sendgrid", "mailgun", "mailjet", "postmarker", "resend",
    "sparkpost", "yagmail", "mailchimp", "flask_mail", "emails",
    # --- chat and SMS ---
    "twilio", "slack", "slack_sdk", "discord", "telegram", "telebot",
    # --- cloud SDKs whose whole point includes SES / SNS ---
    "boto3", "botocore",
}

# Dynamic escapes from the check above: __import__("smtplib") and
# importlib.import_module("smtplib") never appear as an ast.Import node.
DYNAMIC_IMPORTERS = {"__import__", "import_module"}


def python_files():
    """Every source file in src/, excluding __pycache__."""
    return sorted(p for p in SRC.rglob("*.py") if "__pycache__" not in p.parts)


class NoWayToSend(unittest.TestCase):
    """Structural: the capability is absent, not merely unused."""

    def test_src_contains_python_files(self):
        # A guard on the guard. If the glob ever silently matches nothing, the
        # two tests below would pass while checking absolutely nothing.
        self.assertGreater(len(python_files()), 3,
                           f"Expected the components under {SRC}. Did the path move?")

    def test_no_transport_library_is_imported(self):
        offences = []
        for path in python_files():
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root = alias.name.split(".")[0]
                        if root in TRANSPORT:
                            offences.append(f"{path.name}:{node.lineno} imports {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    # level > 0 is a relative import - one of ours, by definition.
                    if node.level == 0 and node.module:
                        root = node.module.split(".")[0]
                        if root in TRANSPORT:
                            offences.append(f"{path.name}:{node.lineno} imports from {node.module}")

        self.assertEqual(offences, [], "\n".join([
            "",
            "A transport library is now imported in src/:",
            *(f"    {o}" for o in offences),
            "",
            "The Comms Agent drafts and stops. If sending is genuinely wanted, that is",
            "a product decision to make deliberately - and the README, the landing page",
            "and the dashboard all need to stop saying nothing is sent.",
        ]))

    def test_no_transport_library_is_imported_dynamically(self):
        offences = []
        for path in python_files():
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = getattr(func, "id", None) or getattr(func, "attr", None)
                if name not in DYNAMIC_IMPORTERS:
                    continue
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        if arg.value.split(".")[0] in TRANSPORT:
                            offences.append(
                                f"{path.name}:{node.lineno} dynamically imports {arg.value}")

        self.assertEqual(offences, [], "\n".join([
            "",
            "A transport library is imported dynamically in src/:",
            *(f"    {o}" for o in offences),
            "",
            "Going around the import statement does not change what the demo claims.",
        ]))


class EveryDraftSaysSo(unittest.TestCase):
    """Behavioural: the drafts themselves carry the marker, in the data.

    Run fully offline - no live sources, no model - so this is deterministic and
    works on a machine with no API key.
    """

    @classmethod
    def setUpClass(cls):
        from src import orchestrator
        cls.result = orchestrator.run_cycle(live=False, inject=True, use_llm=False)
        cls.drafts = [d for s in cls.result["shipments"] for d in s.get("drafts", [])]

    def test_the_cycle_produced_drafts_to_check(self):
        # Same guard-on-the-guard: an empty list passes every assertion below.
        self.assertGreater(len(self.drafts), 0,
                           "The injected Hamburg strike should action shipments and draft "
                           "emails for them. No drafts means this file is testing nothing.")

    def test_every_draft_is_marked_not_sent(self):
        for draft in self.drafts:
            with self.subTest(shipment=draft["shipment_id"], audience=draft["audience"]):
                self.assertEqual(draft["status"], "DRAFT - not sent")

    def test_every_draft_starts_behind_the_approval_gate(self):
        for draft in self.drafts:
            with self.subTest(shipment=draft["shipment_id"], audience=draft["audience"]):
                self.assertEqual(draft["approval_status"], "awaiting_approval",
                                 "A draft must start unapproved. Approval is a human step.")

    def test_no_draft_claims_to_have_been_sent(self):
        # Belt and braces: nothing anywhere in a draft should read as "sent".
        for draft in self.drafts:
            with self.subTest(shipment=draft["shipment_id"], audience=draft["audience"]):
                for field in ("status", "approval_status", "drafted_by"):
                    self.assertNotIn("sent", draft[field].lower().replace("not sent", ""),
                                     f"{field} suggests the draft left the process.")


class TheWorkflowLayerSendsNothingEither(unittest.TestCase):
    """The same rule, applied to the workflow Workers.

    The Inbox Worker drafts replies to inbound mail, the RFQ Worker drafts a
    quote, and the TMS link describes a booking change. Every one of those is an
    outbound action a person has to approve, so every one of them belongs under
    the same gate as an email - and the checks above only ever looked at
    `card["drafts"]`, which none of these appear in.
    """

    @classmethod
    def setUpClass(cls):
        from src import orchestrator
        cls.result = orchestrator.run_cycle(live=False, inject=True, use_llm=False)
        cls.rosters = [s.get("roster") or {} for s in cls.result["shipments"]]

    def test_the_cycle_produced_workflow_output_to_check(self):
        replies = [i for r in self.rosters for i in (r.get("inbox") or {}).get("items", [])
                   if i.get("suggested_reply")]
        quotes = [r["rfq"] for r in self.rosters if (r.get("rfq") or {}).get("draft_reply")]
        self.assertGreater(len(replies), 0, "No drafted replies means this tests nothing.")
        self.assertGreater(len(quotes), 0, "No drafted quotes means this tests nothing.")

    def test_every_drafted_reply_is_held(self):
        for roster in self.rosters:
            for item in (roster.get("inbox") or {}).get("items", []):
                if not item.get("suggested_reply"):
                    continue                      # nothing drafted, nothing to gate
                with self.subTest(booking=item["linked_booking"], intent=item["intent"]):
                    self.assertEqual(item["status"], "DRAFT - not sent")
                    self.assertEqual(item["approval_status"], "awaiting_approval")

    def test_every_drafted_quote_is_held(self):
        for roster in self.rosters:
            rfq = roster.get("rfq") or {}
            if not rfq.get("draft_reply"):
                continue
            with self.subTest(headline=rfq.get("headline")):
                self.assertEqual(rfq["status"], "DRAFT - not sent")
                self.assertEqual(rfq["approval_status"], "awaiting_approval")

    def test_every_booking_amendment_is_held(self):
        """An amendment to a carrier booking is an outbound action like an email.

        The original checks only ever looked at card["drafts"], which a booking
        amendment does not appear in - the same blind spot that let the inbox and
        RFQ replies through unchecked.
        """
        amended = 0
        for roster in self.rosters:
            booking = roster.get("booking") or {}
            if not booking.get("amendment"):
                continue
            amended += 1
            with self.subTest(headline=booking.get("headline")):
                self.assertEqual(booking["status"], "DRAFT - not sent")
                self.assertEqual(booking["approval_status"], "awaiting_approval")
        self.assertGreater(amended, 0,
                           "The injected strike reroutes and holds shipments, so some "
                           "booking should need amending. None means this tests nothing.")

    def test_customs_escalates_and_never_files(self):
        """The Customs Worker prepares an entry; a person submits it."""
        escalated = 0
        for roster in self.rosters:
            customs = roster.get("customs") or {}
            if not customs:
                continue
            self.assertIn(customs["status"], ("Escalated to a person", "Ready to file"))
            self.assertIn("Nothing is filed", customs["note"])
            escalated += bool(customs.get("escalate"))
        self.assertGreater(escalated, 0,
                           "A reroute moves the country of entry, so at least one entry "
                           "should escalate. None means this tests nothing.")

    def test_no_tms_writeback_is_ever_written(self):
        board = self.result["tms"]
        self.assertGreater(board["queued"], 0,
                           "The injected strike actions shipments, so write-backs should "
                           "be queued. None means this tests nothing.")
        for writeback in board["writebacks"]:
            with self.subTest(booking=writeback["booking_ref"]):
                self.assertEqual(writeback["status"], "QUEUED - not written")
                self.assertEqual(writeback["approval_status"], "awaiting_approval")

    def test_the_tms_connector_never_claims_to_be_real(self):
        board = self.result["tms"]
        self.assertIn("demo", board["connector"].lower() + board["status"].lower(),
                      "The TMS link is a demo connector and has to say so wherever it "
                      "is surfaced.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
