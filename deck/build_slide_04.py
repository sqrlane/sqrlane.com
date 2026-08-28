#!/usr/bin/env python3
"""
Slide 04 - THE HOW (1/2).  Emits deck/slide-04-the-how-1.svg.

Answers problem one from slide 02: the work is manual, the same facts re-typed
into six systems. Every row here is a job that used to be typed, the agent that
now does it, and the record it lands on. The gate closes the slide, because the
answer to "an agent did my paperwork" is "and a person still signs it".

Roles are taken verbatim from src/roster.py. All but the connector are tagged
SCRIPTED, because that is what they are today.
"""
from deckkit import *

GREEN, GREEN_BG = "#0f7b3f", "#e7f5ec"

s = Slide()
s.header("04 — THE HOW (1/2)",
         "The desk work does itself.",
         "The same six systems. Nobody re-types anything between them any more.")

TY, TH2 = 226, 512
s.card(M, TY, CW, TH2)
tx = M + 30
s.text(tx, TY + 40, "WHAT ARRIVES", 9.5, 700, FAINT, ls=1.3)
for lab, x in (("AGENT", M + 400), ("WHAT IT DOES", M + 610), ("WHAT LANDS ON THE BOOKING", M + 1090)):
    s.text(x, TY + 40, lab, 9.5, 700, FAINT, ls=1.3)
s.line(tx, TY + 56, W - M - 30, TY + 56, BORDER_STRONG)

ROWS = [
    ("A rate request", "RFQ", "Prices the lane, drafts the quote", "Quote on the file", "SCRIPTED"),
    ("Carrier or customer mail", "Inbox", "Classifies it, links the booking", "Reply on the comms log", "SCRIPTED"),
    ("A bill of lading, an invoice", "Docs", "Extracts the fields", "Fields on the booking", "SCRIPTED"),
    ("A change to the booking", "Booking", "Drafts the carrier amendment", "Amendment, awaiting approval", "SCRIPTED"),
    ("The carrier's invoice", "Invoice", "Reconciles against the agreed rate", "Discrepancy, flagged", "SCRIPTED"),
    ("A new country of entry", "Customs", "Checks entry, EORI, documents", "Escalation, not a filing", "SCRIPTED"),
    ("Every one of the above", "TMS Link", "Writes it where it came from", "One queued change, gated", "DEMO"),
]
for j, (arrives, agent, does, lands, tag) in enumerate(ROWS):
    y = TY + 96 + j * 60
    last = j == len(ROWS) - 1
    if last:
        s.card(tx - 12, y - 26, CW - 36, 48, fill=SURFACE, stroke="none", rx=R)
    s.text(tx, y, arrives, 14, 500, FG)
    s.text(M + 400, y, agent, 14, 600, FG)
    s.text(M + 610, y, does, 13.5, 400, MUTED)
    s.text(M + 1090, y, lands, 13.5, 400, MUTED)
    s.chip(W - M - 30 - 78, y - 15, 78, 21, tag, fs=8.5, fill=CARD if last else SURFACE,
           col=MUTED, weight=700)
    if not last:
        s.line(tx, y + 22, W - M - 30, y + 22, BORDER)

GY, GH = 766, 108
s.card(M, GY, CW, GH, fill=FG, stroke="none")
s.text(M + 30, GY + 40, "THE GATE", 10, 700, "#8f8f8f", ls=1.4)
s.text(M + 30, GY + 76, "Nothing is sent. Nothing is written. A person approves, or it does not happen.",
       22, 600, CARD)
s.raw(f'<text x="{W-M-30}" y="{GY+58}" font-size="34" font-weight="600" fill="{CARD}" '
      f'text-anchor="end" class="num">40%</text>')
s.text(W - M - 30, GY + 82, "of the day, back", 12.5, 400, "#a1a1a1", anchor="end")

s.text(M, 918, "Six systems, one record. The re-typing is gone.", 24, 600, FG, ls=-0.5)
s.text(W - M, 918, "Roles from src/roster.py. Scripted today, tagged on screen.",
       11.5, 400, FAINT, anchor="end")
s.footer("04 / THE HOW 1/2")
s.write("slide-04-the-how-1.svg")
