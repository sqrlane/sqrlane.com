#!/usr/bin/env python3
"""
Slide 05 - THE HOW (2/2).  Emits deck/slide-05-the-how-2.svg.

Answers problem two from slide 02: nothing watches the route. Signals feed one
confidence read; when it crosses the trigger the chain starts.

Deliberately drops rerouting a box that is already on the water. A shipment in
transit has almost no options, so promising a mid-ocean diversion is both weak
and mostly untrue. The value is that knowing earlier moves the decision into a
window where options still exist - which is what the bottom band draws.

The confidence grid shows the mechanism, not a measured accuracy, and says so.
"""
from deckkit import *

GREEN, GREEN_BG = "#0f7b3f", "#e7f5ec"
HEAT = ["#f2f2f2", "#fdf3e3", "#f6dfb4", "#d9a441", "#96580a"]

s = Slide()
s.header("05 — THE HOW (2/2)",
         "Know early enough that you still have options.",
         "Many signals, one confidence read. The earlier it fires, the cheaper the answer.")

TOP = 226

# =========================================================================
# SIGNALS
# =========================================================================
SX, SW, SH = M, 270, 280
s.card(SX, TOP, SW, SH)
sx = SX + 24
s.text(sx, TOP + 36, "SIGNALS", 10, 700, FAINT, ls=1.4)
FAMS = [("News & wires", 1), ("Weather & sea state", 1), ("River gauges", 1),
        ("Seismic & hazards", 1), ("Government filings", 1), ("Reference rates", 1),
        ("Prediction markets", 0), ("AIS & port calls", 0), ("Bunker & freight indices", 0)]
for j, (fam, live) in enumerate(FAMS):
    y = TOP + 60 + j * 20
    s.raw(f'<circle cx="{sx+4}" cy="{y-4}" r="3.2" fill="{GREEN if live else "none"}" '
          f'stroke="{GRAY400}" stroke-width="{0 if live else 1.3}"/>')
    s.text(sx + 18, y, fam, 12.5, 500 if live else 400, FG if live else FAINT)
s.line(sx, TOP + 238, SX + SW - 24, TOP + 238, BORDER)
s.text(sx, TOP + 262, "42 live today. The rest are phase two.", 11.5, 400, FAINT)

# =========================================================================
# CONFIDENCE
# =========================================================================
HX, HW = 390, 700
s.card(HX, TOP, HW, SH, stroke=BORDER_STRONG)
hx = HX + 24
s.text(hx, TOP + 36, "CONFIDENCE, BUILDING", 10, 700, AMBER, ls=1.4)
s.text(hx + 208, TOP + 26, "mechanism, not", 9.5, 400, FAINT)
s.text(hx + 208, TOP + 40, "a measured accuracy", 9.5, 400, FAINT)

VARS = [("Union ballot", [0, 0, 1, 1, 2, 3, 3, 4, 4, 4]),
        ("Berth waiting", [0, 0, 0, 1, 1, 1, 2, 3, 4, 4]),
        ("Throughput", [0, 1, 0, 1, 1, 2, 2, 3, 3, 4]),
        ("Rail slots", [0, 0, 0, 0, 1, 1, 2, 2, 3, 4]),
        ("Prediction mkt", [0, 0, 1, 1, 2, 2, 3, 4, 4, 4]),
        ("Wire volume", [0, 0, 0, 0, 0, 1, 1, 2, 3, 4])]
GX, CELL, GAP = hx + 104, 42, 5
for r, (name, row) in enumerate(VARS):
    y = TOP + 62 + r * 21
    s.text(hx, y + 11, name, 10.5, 400, MUTED)
    for c, v in enumerate(row):
        s.raw(f'<rect x="{GX + c*(CELL+GAP)}" y="{y}" width="{CELL}" height="16" rx="3" '
              f'fill="{HEAT[v]}"/>')
for c, lab in enumerate(["T-9", "", "T-7", "", "T-5", "", "T-3", "", "T-1", "T-0"]):
    if lab:
        s.text(GX + c * (CELL + GAP) + CELL / 2, TOP + 204, lab, 9.5, 400, FAINT,
               anchor="middle", cls="mono")

CONF = [5, 8, 14, 20, 31, 42, 55, 68, 81, 92]
BASE, HGT = TOP + 268, 48
s.text(hx, BASE - 16, "confidence", 11.5, 500, FG)
for c, v in enumerate(CONF):
    h = HGT * v / 100
    s.raw(f'<rect x="{GX + c*(CELL+GAP)}" y="{BASE - h:.0f}" width="{CELL}" height="{h:.0f}" '
          f'rx="2" fill="{AMBER if v >= 70 else GRAY400}"/>')
ty = BASE - HGT * 0.70
s.line(GX - 8, ty, GX + 10 * (CELL + GAP) - GAP + 8, ty, AMBER, 1.4, dash="4 4")
s.text(GX + 10 * (CELL + GAP) + 10, ty + 4, "trigger", 11, 600, AMBER)

# =========================================================================
# AFTER THE TRIGGER - the run, as the app shows it
# =========================================================================
RX, RW = 1114, W - M - 1114
s.card(RX, TOP, RW, SH, fill=CARD, stroke=BORDER_STRONG)
s.raw(f'<rect x="{RX}" y="{TOP}" width="{RW}" height="34" rx="{RMD}" fill="{SURFACE}"/>')
s.raw(f'<rect x="{RX}" y="{TOP+22}" width="{RW}" height="12" fill="{SURFACE}"/>')
s.line(RX, TOP + 34, RX + RW, TOP + 34, BORDER)
s.text(RX + 16, TOP + 22, "SQRlane / Run", 11, 500, MUTED)
s.text(RX + RW - 16, TOP + 22, "12:00", 10.5, 400, FAINT, anchor="end", cls="mono")

s.card(RX + 14, TOP + 46, RW - 28, 34, fill=AMBER_BG, stroke=AMBER, rx=R)
s.text(RX + 28, TOP + 68, "TRIGGERED", 10, 700, AMBER, ls=1.3)
s.text(RX + 122, TOP + 68, "Hamburg strike", 12.5, 600, FG)
s.text(RX + RW - 28, TOP + 68, "confidence 92%", 11.5, 500, AMBER, anchor="end", cls="mono")

STEPS = [("Risk Monitor", "exception raised", "3 bookings"),
         ("Route Advisor", "alternatives priced", "14 options"),
         ("Comms Agent", "drafts written", "6 mails"),
         ("Customs", "entries checked", "2 countries")]
for j, (who, did, n) in enumerate(STEPS):
    y = TOP + 108 + j * 26
    s.raw(f'<circle cx="{RX+30}" cy="{y-4}" r="6" fill="{GREEN_BG}"/>')
    s.raw(f'<path d="M{RX+27} {y-4} l2.5 2.5 l5 -5.5" stroke="{GREEN}" stroke-width="1.6" '
          f'fill="none" stroke-linecap="round"/>')
    s.text(RX + 46, y, who, 11.5, 600, FG)
    s.text(RX + 158, y, did, 11.5, 400, MUTED)
    s.text(RX + RW - 28, y, n, 11, 400, FAINT, anchor="end", cls="mono")

s.line(RX + 16, TOP + 222, RX + RW - 16, TOP + 222, BORDER)
s.text(RX + 28, TOP + 244, "RECOMMENDED", 9.5, 700, FAINT, ls=1.3)
s.text(RX + 28, TOP + 266, "Route around 2 · Amend 1 · Watch 4", 13, 600, FG)
s.chip(RX + RW - 28 - 84, TOP + 240, 84, 28, "Approve", fs=11.5, fill=FG, col=CARD, weight=600)

# =========================================================================
# THE DECISION WINDOW - what earlier knowledge is actually worth
# =========================================================================
DY, DH = 546, 258
s.text(M, DY - 16, "WHAT THE WARNING IS WORTH, BY WHEN IT ARRIVES", 10, 700, FAINT, ls=1.4)
WW = (CW - 48) / 3
WINDOWS = [
    ("NOT YET BOOKED", "Route around it.",
     ["The disruption never touches", "this shipment at all."], "many", AMBER, AMBER_BG),
    ("BOOKED, NOT SAILED", "Amend while it is cheap.",
     ["Discharge port, routing and entry,", "before the vessel moves."], "some", FG, SURFACE),
    ("ALREADY IN TRANSIT", "No reroute. Prepare.",
     ["Warn the customer, re-plan the", "inland leg, ready the entry."], "few", MUTED, CARD_MUTED),
]
for i, (label, head, line, opts, col, bg) in enumerate(WINDOWS):
    x = M + i * (WW + 24)
    s.card(x, DY, WW, DH, fill=bg, stroke=AMBER if i == 0 else BORDER_STRONG)
    s.text(x + 26, DY + 38, label, 10, 700, col, ls=1.3)
    s.text(x + 26, DY + 84, head, 22, 600, FG, ls=-0.5)
    for k, ln in enumerate(line):
        s.text(x + 26, DY + 116 + k * 20, ln, 13, 400, MUTED)
    s.line(x + 26, DY + 168, x + WW - 26, DY + 168, BORDER)
    s.text(x + 26, DY + 200, "options", 11.5, 400, FAINT)
    s.raw(f'<text x="{x+26}" y="{DY+230}" font-size="26" font-weight="600" fill="{col}">{opts}</text>')
    n = {"many": 5, "some": 2, "few": 1}[opts]
    for k in range(5):
        s.raw(f'<rect x="{x + WW - 26 - (5-k)*20}" y="{DY+210}" width="14" height="14" rx="3" '
              f'fill="{col if k < n else GRAY400}"/>')
    if i < 2:
        s.line(x + WW + 4, DY + DH / 2, x + WW + 20, DY + DH / 2, FAINT, 1.4, "ahN")

s.text(M, 866, "The prediction moves the decision left, into the window where options still exist.",
       24, 600, FG, ls=-0.5)
s.footer("05 / THE HOW 2/2")
s.write("slide-05-the-how-2.svg")
