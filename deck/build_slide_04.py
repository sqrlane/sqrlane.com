#!/usr/bin/env python3
"""
Slide 04 - THE LANE.  Emits deck/slide-04-the-lane.svg.

The bridge between why and how. Two jobs:

  what a forwarder's work actually is - where the file opens, where it closes,
  and how much of the 45 days is spent waiting rather than working

  what a disruption in the middle of it costs, and which side of the invoice
  each cost lands on

The punch is the margin comparison. Kuehne+Nagel Sea Logistics - the best-run
operator in the industry - earns CHF 136 of EBIT per TEU. One day of demurrage
at the 2025 global average costs more than that. Every figure is published and
its conversion is on the slide.
"""
from deckkit import *

GREEN, GREEN_BG = "#0f7b3f", "#e7f5ec"
RED_BG = "#feecec"

s = Slide()
s.header("04 — THE LANE",
         "Forty-five days of work, and a margin one bad day wide.",
         "The file opens at the enquiry and closes at the invoice. Every handoff between them is the forwarder's.")

# =========================================================================
# THE FILE, END TO END
# =========================================================================
FY, FH = 226, 196
s.card(M, FY, CW, FH)
s.text(M + 26, FY + 36, "THE FILE, END TO END", 10, 700, FAINT, ls=1.4)
s.text(M + 250, FY + 36, "one shipment, Shanghai to Munich", 11.5, 400, FAINT)
s.text(W - M - 26, FY + 36, "45 days", 13, 600, FG, anchor="end", cls="mono")

STAGES = [("Enquiry", 2), ("Quote", 3), ("Book", 2), ("Docs", 2),
          ("In transit", 32), ("Customs", 2), ("Invoice", 2)]
TX0, TXW = M + 40, CW - 80
UNIT = TXW / sum(d for _, d in STAGES)
x = TX0
for name, days in STAGES:
    w = days * UNIT
    hot = name == "In transit"
    s.card(x + 2, FY + 96, w - 4, 38, fill=SURFACE_2 if hot else SURFACE, stroke="none", rx=R)
    s.text(x + w / 2, FY + 84, name, 11, 600 if hot else 500, FG if hot else MUTED, anchor="middle")
    s.text(x + w / 2, FY + 120, f"{days}d", 11, 500, MUTED if hot else FAINT,
           anchor="middle", cls="mono")
    x += w

STRIKE = TX0 + 18 * UNIT
s.line(STRIKE, FY + 78, STRIKE, FY + 148, AMBER, 2)
s.raw(f'<circle cx="{STRIKE}" cy="{FY+78}" r="6" fill="{AMBER}"/>')
s.text(STRIKE + 14, FY + 160, "day 18 · the lane breaks", 12.5, 600, AMBER)
s.text(TX0, FY + 160, "file opens", 11.5, 400, FAINT)
s.text(TX0 + TXW, FY + 160, "file closes", 11.5, 400, FAINT, anchor="end")

# =========================================================================
# WHAT IT COSTS, AND WHERE IT LANDS
# =========================================================================
CY, CH2 = 450, 400
s.card(M, CY, 830, CH2)
s.text(M + 26, CY + 36, "WHERE EACH COST LANDS", 10, 700, FAINT, ls=1.4)
for lab, x0, col in (("PASSED TO THE CUSTOMER", M + 26, MUTED),
                     ("ABSORBED BY THE FORWARDER", M + 440, AMBER)):
    s.text(x0, CY + 76, lab, 9.5, 700, col, ls=1.2)
s.line(M + 420, CY + 60, M + 420, CY + CH2 - 90, BORDER)

PASSED = ["Emergency surcharge", "Higher freight rate", "Revised transit time"]
EATEN = ["Demurrage and detention", "Re-booking and amendments", "Customs re-entry, new EORI",
         "The hours spent re-keying", "The credit for a missed date"]
for j, item in enumerate(PASSED):
    y = CY + 112 + j * 30
    s.raw(f'<circle cx="{M+30}" cy="{y-4}" r="3.2" fill="none" stroke="{GRAY400}" stroke-width="1.3"/>')
    s.text(M + 44, y, item, 12.5, 400, MUTED)
for j, item in enumerate(EATEN):
    y = CY + 112 + j * 30
    s.raw(f'<circle cx="{M+444}" cy="{y-4}" r="3.2" fill="{AMBER}"/>')
    s.text(M + 458, y, item, 12.5, 500, FG)

s.line(M + 26, CY + CH2 - 76, M + 830 - 26, CY + CH2 - 76, BORDER)
s.text(M + 26, CY + CH2 - 42, "Which side a line falls on is the contract.", 13, 500, FG)
s.text(M + 26, CY + CH2 - 20, "The forwarder argues it afterwards, on their own time.", 13, 400, MUTED)

# =========================================================================
# THE MARGIN, AGAINST THE DELAY
# =========================================================================
BX, BW = 950, W - M - 950
s.card(BX, CY, BW, CH2, stroke=BORDER_STRONG)
s.text(BX + 26, CY + 36, "ON ONE CONTAINER", 10, 700, AMBER, ls=1.4)

BARS = [("What the forwarder earns", 127, FG, "K+N Sea Logistics, FY25"),
        ("One day of demurrage", 185, AMBER, "$200/day, 2025 global average"),
        ("Five days of demurrage", 926, AMBER, "before any surcharge at all")]
BAR_X, BAR_MAX, TOPV = BX + 26, BW - 52, 926
for j, (lab, val, col, note) in enumerate(BARS):
    y = CY + 88 + j * 86
    s.text(BAR_X, y, lab, 13.5, 500, FG)
    s.raw(f'<text x="{BX+BW-26}" y="{y}" font-size="22" font-weight="600" fill="{col}" '
          f'text-anchor="end" class="num">€{val:,}</text>')
    s.raw(f'<rect x="{BAR_X}" y="{y+12}" width="{BAR_MAX*val/TOPV:.0f}" height="20" rx="4" fill="{col}"/>')
    s.text(BAR_X, y + 50, note, 11, 400, FAINT, cls="mono")

s.line(BAR_X, CY + CH2 - 70, BX + BW - 26, CY + CH2 - 70, BORDER)
s.text(BAR_X, CY + CH2 - 38, "One bad day costs more than the box earns.", 17, 600, FG, ls=-0.3)
s.text(BAR_X, CY + CH2 - 16, "CHF 136 EBIT/TEU at 1.07 · USD at 1.08 · published figures",
       10.5, 400, FAINT, cls="mono")

s.text(M, 886, "This is the day the agents are built for.", 24, 600, FG, ls=-0.5)
s.footer("04 / THE LANE")
s.write("slide-04-the-lane.svg")
