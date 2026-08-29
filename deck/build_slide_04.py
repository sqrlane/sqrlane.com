#!/usr/bin/env python3
"""
Slide 04 - THE LANE.  Emits deck/slide-04-the-lane.svg.

The bridge from why into how. Three things:

  the file, end to end, drawn to scale so the sea leg visibly dominates
  the coordination web: who the forwarder talks to at each stage, as a matrix,
    because the density is the job
  what one bad day costs, and which side of the invoice it lands on

Plain language throughout: no demurrage, no detention. A day the box sits at
the port is what it is.

EUR 127 is Kuehne+Nagel Sea Logistics FY25 - CHF 585m recurring EBIT over 4.3M
TEU - the best-run operator in the industry, so the comparison is conservative.
Port storage is the 2025 global average. Both conversions are on the slide.
"""
from deckkit import *

GREEN = "#0f7b3f"

s = Slide()
s.header("04 — THE LANE",
         "Forty-five days, seven parties, and a margin one bad day wide.",
         "The forwarder owns no ship and no truck. They own the coordination, and every message in it.")

# =========================================================================
# THE FILE - the clock, then the coordination
# =========================================================================
FY, FH = 224, 414
s.card(M, FY, CW, FH)
s.text(M + 26, FY + 34, "THE FILE, END TO END", 10, 700, FAINT, ls=1.4)
s.text(M + 244, FY + 34, "one shipment, Shanghai to Munich", 11.5, 400, FAINT)
s.text(W - M - 26, FY + 34, "45 days", 13, 600, FG, anchor="end", cls="mono")

STAGES = [("Enquiry", 2), ("Quote", 3), ("Book", 2), ("Docs", 2),
          ("In transit", 32), ("Customs", 2), ("Delivery", 1), ("Invoice", 1)]
TX0, TXW = M + 190, CW - 214
UNIT = TXW / 45
x = TX0
for name, days in STAGES:
    w = days * UNIT
    hot = days > 10
    s.card(x + 1.5, FY + 62, w - 3, 22, fill=SURFACE_2 if hot else SURFACE, stroke="none", rx=4)
    if w > 70:
        s.text(x + w / 2, FY + 77, f"{days}d", 10.5, 600 if hot else 500,
               MUTED if hot else FAINT, anchor="middle", cls="mono")
    x += w
s.text(M + 26, FY + 78, "the clock", 11.5, 500, FG)
STRIKE = TX0 + 18 * UNIT
s.line(STRIKE, FY + 56, STRIKE, FY + 92, AMBER, 2)
s.raw(f'<circle cx="{STRIKE}" cy="{FY+56}" r="5" fill="{AMBER}"/>')
s.text(STRIKE + 12, FY + 106, "day 18 · the lane breaks", 12, 600, AMBER)
s.text(TX0, FY + 106, "opens", 11, 400, FAINT)
s.text(TX0 + TXW, FY + 106, "closes", 11, 400, FAINT, anchor="end")
s.line(M + 26, FY + 126, W - M - 26, FY + 126, BORDER)

# -- the coordination web -------------------------------------------------
s.text(M + 26, FY + 156, "WHO THE FORWARDER TALKS TO", 10, 700, AMBER, ls=1.4)
s.text(M + 290, FY + 156, "every dot is a mail, a portal login or a call", 11, 400, FAINT)

COLS = ["Enquiry", "Quote", "Book", "Docs", "In transit", "Customs", "Delivery", "Invoice"]
PARTIES = [
    ("Customer", [1, 1, 1, 1, 1, 0, 1, 1]),
    ("Shipping line", [0, 1, 1, 1, 1, 0, 0, 1]),
    ("Origin agent", [0, 0, 1, 1, 0, 0, 0, 0]),
    ("Port terminal", [0, 0, 0, 1, 1, 1, 0, 0]),
    ("Haulier", [0, 1, 0, 0, 0, 0, 1, 1]),
    ("Customs broker", [0, 0, 0, 1, 0, 1, 1, 0]),
    ("Consignee", [0, 0, 0, 0, 1, 0, 1, 1]),
]
TOUCHES = sum(sum(r) for _, r in PARTIES)
MX0, MW_ = M + 190, CW - 214
CWD = MW_ / len(COLS)
for c, lab in enumerate(COLS):
    s.text(MX0 + c * CWD + CWD / 2, FY + 186, lab, 10.5, 600, MUTED, anchor="middle")
s.line(MX0, FY + 196, MX0 + MW_, FY + 196, BORDER_STRONG)
for r, (party, row) in enumerate(PARTIES):
    y = FY + 218 + r * 24
    s.text(M + 26, y + 4, party, 12, 500, FG)
    for c, on in enumerate(row):
        cx = MX0 + c * CWD + CWD / 2
        if on:
            s.raw(f'<circle cx="{cx}" cy="{y}" r="6" fill="{AMBER}"/>')
        else:
            s.raw(f'<circle cx="{cx}" cy="{y}" r="2" fill="{GRAY400}"/>')
s.text(M + 26, FY + FH - 22,
       f"{TOUCHES} handoffs on a file where nothing goes wrong. Every one ends with the same facts "
       "typed somewhere new.", 13, 500, FG)

# =========================================================================
# WHAT ONE BAD DAY COSTS
# =========================================================================
CY, CH2 = 662, 200
s.card(M, CY, 830, CH2)
s.text(M + 26, CY + 32, "WHERE EACH COST LANDS", 10, 700, FAINT, ls=1.4)
for lab, x0, col in (("PASSED TO THE CUSTOMER", M + 26, MUTED),
                     ("ABSORBED BY THE FORWARDER", M + 400, AMBER)):
    s.text(x0, CY + 62, lab, 9.5, 700, col, ls=1.2)
s.line(M + 380, CY + 46, M + 380, CY + CH2 - 54, BORDER)
for j, item in enumerate(["The carrier's surcharge", "The higher freight rate", "The later arrival date"]):
    y = CY + 92 + j * 26
    s.raw(f'<circle cx="{M+30}" cy="{y-4}" r="3" fill="none" stroke="{GRAY400}" stroke-width="1.3"/>')
    s.text(M + 44, y, item, 12.5, 400, MUTED)
for j, item in enumerate(["Storage while the box waits", "Re-booking and paperwork",
                          "Clearing it into a new country"]):
    y = CY + 92 + j * 26
    s.raw(f'<circle cx="{M+404}" cy="{y-4}" r="3" fill="{AMBER}"/>')
    s.text(M + 418, y, item, 12.5, 500, FG)
s.text(M + 26, CY + CH2 - 26,
       "Which side a line falls on is the contract. The forwarder argues it afterwards, on their own time.",
       12.5, 400, MUTED)

BX, BW = 950, W - M - 950
s.card(BX, CY, BW, CH2, stroke=BORDER_STRONG)
s.text(BX + 26, CY + 32, "ON ONE CONTAINER", 10, 700, AMBER, ls=1.4)
BARS = [("What the forwarder earns", 127, FG), ("One day the box sits at the port", 185, AMBER),
        ("Five days sitting", 926, AMBER)]
BAR_X, BAR_MAX = BX + 26, BW - 200
for j, (lab, val, col) in enumerate(BARS):
    y = CY + 68 + j * 34
    s.text(BAR_X, y, lab, 12.5, 500, FG)
    s.raw(f'<rect x="{BAR_X+300}" y="{y-11}" width="{BAR_MAX*val/926*0.62:.0f}" height="14" '
          f'rx="3" fill="{col}"/>')
    s.raw(f'<text x="{BX+BW-26}" y="{y}" font-size="17" font-weight="600" fill="{col}" '
          f'text-anchor="end" class="num">€{val:,}</text>')
s.line(BAR_X, CY + CH2 - 62, BX + BW - 26, CY + CH2 - 62, BORDER)
s.text(BAR_X, CY + CH2 - 36, "One bad day costs more than the box earns.", 16, 600, FG, ls=-0.3)
s.text(BAR_X, CY + CH2 - 16, "K+N Sea FY25, CHF 136 EBIT/TEU at 1.07 · port storage $200/day at 1.08",
       10, 400, FAINT, cls="mono")

s.text(M, 908, "This is the day the agents are built for.", 24, 600, FG, ls=-0.5)
s.footer("04 / THE LANE")
s.write("slide-04-the-lane.svg")
