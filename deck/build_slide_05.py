#!/usr/bin/env python3
"""
Slide 05 - THE HOW.  Emits deck/slide-05-the-agents.svg.

Five parts, in the order the mechanism runs:

  SIGNALS      the families read, live today and in build
  CONFIDENCE   many variables watched at once; when the read crosses the
               trigger level the agents start
  PREDICTIONS  every alternative already priced, ranked on days and money
  SAME MOMENT  one decision to a person, every artefact already drafted
  and, down the left, what that shape buys: speed, coverage, reassurance

Two things here are NOT counted from a run and are tagged on the slide:
the confidence grid shows how detection works rather than a measured
accuracy, and the route table is an illustrative lane chosen so the options
are close - which is the case that actually needs deciding.
"""
from deckkit import *

GREEN, GREEN_BG = "#0f7b3f", "#e7f5ec"
HEAT = ["#f2f2f2", "#fdf3e3", "#f6dfb4", "#d9a441", "#96580a"]

s = Slide()
s.header("05 — THE HOW",
         "The answer is ready before the risk lands.",
         "Many signals, one confidence read. When it crosses the line, the whole chain is already written.")

TOP, BOT = 222, 852

# =========================================================================
# LEFT RAIL - what the shape buys, stacked
# =========================================================================
RX, RW, RH = M, 230, 200
for i, (head, lines) in enumerate((
        ("Speed", ["The option existed", "before the event did."]),
        ("Coverage", ["Every booking, not", "the one someone", "remembered."]),
        ("Reassurance", ["The reasoning is", "recorded. A person", "still approves."]))):
    y = TOP + i * (RH + 15)
    s.card(RX, y, RW, RH)
    s.text(RX + 24, y + 54, head, 22, 600, FG, ls=-0.5)
    for j, ln in enumerate(lines):
        s.text(RX + 24, y + 88 + j * 20, ln, 13, 400, MUTED)

# =========================================================================
# SIGNALS - families, vertical, live and in build
# =========================================================================
SX, SW, SH = 358, 300, 280
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
# CONFIDENCE - many variables, one read, one trigger
# =========================================================================
HX, HW = 678, W - M - 678
s.card(HX, TOP, HW, SH, stroke=BORDER_STRONG)
hx = HX + 24
s.text(hx, TOP + 36, "CONFIDENCE, BUILDING", 10, 700, AMBER, ls=1.4)
s.text(hx + 216, TOP + 36, "how detection works — not a measured accuracy", 11, 400, FAINT)

VARS = [("Union ballot",   [0, 0, 1, 1, 2, 3, 3, 4, 4, 4]),
        ("Berth waiting",  [0, 0, 0, 1, 1, 1, 2, 3, 4, 4]),
        ("Throughput",     [0, 1, 0, 1, 1, 2, 2, 3, 3, 4]),
        ("Rail slots",     [0, 0, 0, 0, 1, 1, 2, 2, 3, 4]),
        ("Prediction mkt", [0, 0, 1, 1, 2, 2, 3, 4, 4, 4]),
        ("Wire volume",    [0, 0, 0, 0, 0, 1, 1, 2, 3, 4])]
GX, CELL, GAP = hx + 116, 46, 5
for r, (name, row) in enumerate(VARS):
    y = TOP + 62 + r * 21
    s.text(hx, y + 11, name, 11.5, 400, MUTED)
    for c, v in enumerate(row):
        s.raw(f'<rect x="{GX + c*(CELL+GAP)}" y="{y}" width="{CELL}" height="16" rx="3" '
              f'fill="{HEAT[v]}"/>')
for c, lab in enumerate(["T-9", "", "T-7", "", "T-5", "", "T-3", "", "T-1", "T-0"]):
    if lab:
        s.text(GX + c * (CELL + GAP) + CELL / 2, TOP + 204, lab, 9.5, 400, FAINT,
               anchor="middle", cls="mono")

# the read itself, and the line it crosses
CONF = [5, 8, 14, 20, 31, 42, 55, 68, 81, 92]
BASE, HGT = TOP + 268, 48
s.text(hx, BASE - 16, "confidence", 11.5, 500, FG)
for c, v in enumerate(CONF):
    h = HGT * v / 100
    s.raw(f'<rect x="{GX + c*(CELL+GAP)}" y="{BASE - h:.0f}" width="{CELL}" height="{h:.0f}" '
          f'rx="2" fill="{AMBER if v >= 70 else GRAY400}"/>')
ty = BASE - HGT * 0.70
s.line(GX - 8, ty, GX + 10 * (CELL + GAP) - GAP + 8, ty, AMBER, 1.4, dash="4 4")
s.text(GX + 10 * (CELL + GAP) + 8, ty + 4, "trigger", 11, 600, AMBER)

# =========================================================================
# PREDICTIONS - a close call, which is the case that needs deciding
# =========================================================================
PY, PH = 526, BOT - 526
s.card(SX, PY, 440, PH, stroke=BORDER_STRONG)
px = SX + 24
s.text(px, PY + 34, "PREDICTIONS", 10, 700, AMBER, ls=1.4)
s.chip(SX + 440 - 24 - 90, PY + 18, 90, 22, "illustrative", fs=9.5, fill=SURFACE, col=MUTED, weight=600)
s.text(px, PY + 68, "Priced before it happens.", 19, 600, FG, ls=-0.4)

for lab, cx_, anc in (("ROUTE", px, "start"), ("+DAYS", px + 226, "end"), ("EXPOSED", px + 380, "end")):
    s.text(cx_, PY + 100, lab, 9, 700, FAINT, ls=1.2, anchor=anc)
s.line(px, PY + 112, SX + 440 - 24, PY + 112, BORDER)

ROUTES = [("R-GEN-STD", "+0d", "€18,400", False), ("R-FOS-ALT", "+2d", "€17,900", True),
          ("R-BCN-ALT", "+3d", "€18,100", False), ("R-TRS-ALT", "+4d", "€19,600", False),
          ("R-COGH-ALT", "+12d", "€96,300", False)]
for j, (rid, days, eur, best) in enumerate(ROUTES):
    y = PY + 136 + j * 28
    if best:
        s.card(px - 10, y - 17, 400, 26, fill=AMBER_BG, stroke="none", rx=R)
    s.text(px, y, rid, 11.5, 500, AMBER if best else MUTED, cls="mono")
    s.text(px + 226, y, days, 12, 600 if best else 400, FG if best else MUTED, anchor="end", cls="mono")
    s.text(px + 380, y, eur, 12, 600 if best else 400, FG if best else MUTED, anchor="end", cls="mono")

s.line(px, PY + 272, SX + 440 - 24, PY + 272, BORDER)
s.text(px, PY + 298, "Three options within €500 of each other.", 12.5, 500, FG)
s.text(px, PY + 320, "The tie breaks on the paperwork each one triggers.", 12.5, 400, MUTED)

# =========================================================================
# THE SAME MOMENT
# =========================================================================
CX, CW2 = 826, W - M - 826
s.card(CX, PY, CW2, 100, fill=FG, stroke="none")
s.text(CX + 24, PY + 30, "TO THE PERSON", 9.5, 700, "#8f8f8f", ls=1.4)
s.text(CX + 24, PY + 68, "Reroute", 25, 600, CARD, ls=-0.6)
s.text(CX + 128, PY + 68, "GEN → FOS", 17, 600, "#f5a623", cls="mono")
s.text(CX + 24, PY + 90, "One call to make. The reasoning is attached.", 12, 400, "#a1a1a1")
s.chip(CX + CW2 - 24 - 178, PY + 42, 86, 30, "Approve", fs=12, fill=CARD, col=FG, weight=600)
s.chip(CX + CW2 - 24 - 86, PY + 42, 86, 30, "Reject", fs=12, fill="#333", col=CARD, weight=600)

s.card(CX, PY + 116, CW2, PH - 116, stroke=BORDER_STRONG)
s.text(CX + 24, PY + 148, "DRAFTED IN PARALLEL", 10, 700, FAINT, ls=1.4)
s.text(CX + 216, PY + 148, "written while the person is still deciding", 11, 400, FAINT)
COL_A, COL_W, COL_H, COL_T = CX + 24, CX + 176, CX + 410, CX + 754
for lab, cx_ in (("AGENT", COL_A), ("WRITES", COL_W), ("HOW", COL_H)):
    s.text(cx_, PY + 176, lab, 9, 700, FAINT, ls=1.2)
s.line(CX + 24, PY + 188, CX + CW2 - 24, PY + 188, BORDER)

AGENTS = [("Risk Monitor", "The exception on the booking", "Prose to the model, numbers to a threshold.", "LIVE"),
          ("Route Advisor", "Discharge port, routing, ETA", "Prices every option. Refuses one not offered.", "LIVE"),
          ("Comms Agent", "Carrier and customer mail", "Two voices, two calls. Flags internal codes.", "LIVE"),
          ("Customs", "Entry for the new country", "Escalates rather than files.", "SCRIPTED"),
          ("TMS Link", "All of it, onto the record", "One gate. Nothing bypasses it.", "DEMO")]
for j, (name, writes, how, tag) in enumerate(AGENTS):
    y = PY + 208 + j * 27
    live = tag == "LIVE"
    s.raw(f'<circle cx="{COL_A+4}" cy="{y-4}" r="3.4" fill="{GREEN if live else GRAY400}"/>')
    s.text(COL_A + 18, y, name, 12.5, 600, FG)
    s.text(COL_W, y, writes, 11.5, 400, MUTED)
    s.text(COL_H, y, how, 11, 400, FAINT)
    s.chip(COL_T, y - 14, 72, 20, tag, fs=8.5,
           fill=GREEN_BG if live else SURFACE, col=GREEN if live else MUTED, weight=700)

s.text(M, 908, "One decision to make. Everything else is already done.", 24, 600, FG, ls=-0.5)
s.footer("05 / THE AGENTS")
s.write("slide-05-the-agents.svg")
