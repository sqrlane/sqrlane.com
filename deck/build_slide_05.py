#!/usr/bin/env python3
"""
Slide 05 - THE HOW (the mechanism).  Emits deck/slide-05-the-agents.svg.

Four zones, left to right, because the product's shape is a sequence:

  ALWAYS ON    42 sources read continuously, every booking kept priced
  PREDICTIONS  alternatives mapped and ranked BEFORE anything happens,
               on the only two variables that decide: days added, money at risk
  THRESHOLD    a risk crosses the line
  SAME MOMENT  one decision to a person, every artefact already drafted

The prediction block is the essential one: the options exist before the event,
which is what makes the right-hand side simultaneous rather than sequential.

Route figures are SHP-001's real candidates from an offline run.
"""
from deckkit import *

GREEN, GREEN_BG = "#0f7b3f", "#e7f5ec"

s = Slide()
s.header("05 — THE HOW",
         "The answer is ready before the risk lands.",
         "One decision goes to a person. Everything else is already being written.")

BY, BH = 222, 456
AX, AW = M, 250
PX, PW = 366, 380
TX, TW = 766, 130
CX, CW2 = 916, W - M - 916

# =========================================================================
# ALWAYS ON
# =========================================================================
s.card(AX, BY, AW, BH)
ax = AX + 26
s.text(ax, BY + 38, "ALWAYS ON", 10, 700, FAINT, ls=1.4)
s.raw(f'<text x="{ax}" y="{BY+112}" font-size="46" font-weight="600" fill="{FG}" '
      f'letter-spacing="-1.4" class="num">42</text>')
s.text(ax, BY + 138, "sources, read", 13.5, 500, FG)
s.text(ax, BY + 158, "continuously", 13.5, 500, FG)
s.line(ax, BY + 196, AX + AW - 26, BY + 196, BORDER)
s.text(ax, BY + 238, "Every booking", 20, 600, FG, ls=-0.4)
s.text(ax, BY + 262, "kept priced, not just", 13, 400, MUTED)
s.text(ax, BY + 282, "flagged", 13, 400, MUTED)
s.line(ax, BY + 320, AX + AW - 26, BY + 320, BORDER)
s.text(ax, BY + 356, "None of this waits", 13, 500, FG)
s.text(ax, BY + 376, "for an event.", 13, 500, FG)

# =========================================================================
# PREDICTIONS - the options exist before the disruption does
# =========================================================================
s.card(PX, BY, PW, BH, fill=CARD, stroke=BORDER_STRONG)
px = PX + 26
s.text(px, BY + 38, "PREDICTIONS", 10, 700, AMBER, ls=1.4)
s.text(px, BY + 86, "Before it happens.", 22, 600, FG, ls=-0.5)
s.text(px, BY + 114, "Every alternative mapped and", 13, 400, MUTED)
s.text(px, BY + 134, "priced, ahead of the event.", 13, 400, MUTED)

for lab, cx_, anc in (("ROUTE", px, "start"), ("+DAYS", px + 190, "end"), ("EXPOSED", px + 328, "end")):
    s.text(cx_, BY + 180, lab, 9, 700, FAINT, ls=1.2, anchor=anc)
s.line(px, BY + 192, PX + PW - 26, BY + 192, BORDER)

ROUTES = [("R-HAM-STD", "+0d", "€31,500", False),
          ("R-RTM-ALT", "+2d", "€2,304", True),
          ("R-COGH-ALT", "+10d", "€135,140", False)]
for j, (rid, days, eur, best) in enumerate(ROUTES):
    y = BY + 222 + j * 38
    if best:
        s.card(px - 10, y - 20, PW - 32, 30, fill=AMBER_BG, stroke="none", rx=R)
    s.text(px, y, rid, 12, 500, AMBER if best else MUTED, cls="mono")
    s.text(px + 190, y, days, 12.5, 600 if best else 400, FG if best else MUTED, anchor="end", cls="mono")
    s.text(px + 328, y, eur, 12.5, 600 if best else 400, FG if best else MUTED, anchor="end", cls="mono")

s.line(px, BY + 356, PX + PW - 26, BY + 356, BORDER)
s.text(px, BY + 386, "Ranked on the two that decide:", 13, 500, FG)
s.text(px, BY + 408, "days added, and money at risk.", 13, 400, MUTED)

# =========================================================================
# THRESHOLD
# =========================================================================
s.text(TX + TW / 2, BY + 38, "THRESHOLD", 10, 700, AMBER, ls=1.4, anchor="middle")
s.line(TX + TW / 2, BY + 58, TX + TW / 2, BY + BH - 10, AMBER, 1.6, dash="5 5")
s.card(TX - 4, BY + 168, TW + 8, 88, fill=AMBER_BG, stroke=AMBER)
s.text(TX + TW / 2, BY + 200, "Hamburg", 14, 600, FG, anchor="middle")
s.text(TX + TW / 2, BY + 220, "strike", 14, 600, FG, anchor="middle")
s.text(TX + TW / 2, BY + 242, "high · 3–5d", 11, 400, AMBER, anchor="middle", cls="mono")
s.line(TX + TW + 8, BY + 212, TX + TW + 42, BY + 212, AMBER, 2, "ahA")

# =========================================================================
# THE SAME MOMENT
# =========================================================================
s.text(CX, BY + 38, "THE SAME MOMENT", 10, 700, FAINT, ls=1.4)

s.card(CX, BY + 54, CW2, 116, fill=FG, stroke="none")
s.text(CX + 26, BY + 84, "TO THE PERSON", 9.5, 700, "#8f8f8f", ls=1.4)
s.text(CX + 26, BY + 124, "Reroute", 27, 600, CARD, ls=-0.7)
s.text(CX + 136, BY + 124, "HAM → RTM", 18, 600, "#f5a623", cls="mono")
s.text(CX + 26, BY + 152, "One call to make. The reasoning is attached.", 12.5, 400, "#a1a1a1")
s.chip(CX + CW2 - 26 - 190, BY + 96, 92, 32, "Approve", fs=12.5, fill=CARD, col=FG, weight=600)
s.chip(CX + CW2 - 26 - 92, BY + 96, 92, 32, "Reject", fs=12.5, fill="#333", col=CARD, weight=600)

s.card(CX, BY + 190, CW2, BH - 190, stroke=BORDER_STRONG)
s.text(CX + 26, BY + 222, "DRAFTED IN PARALLEL", 10, 700, FAINT, ls=1.4)
s.text(CX + 216, BY + 222, "already written, waiting behind the same approval", 11.5, 400, FAINT)

COL_A, COL_W, COL_H, COL_T = CX + 26, CX + 186, CX + 426, CX + 782
for lab, cx_ in (("AGENT", COL_A), ("WRITES", COL_W), ("HOW", COL_H)):
    s.text(cx_, BY + 252, lab, 9, 700, FAINT, ls=1.2)
s.line(CX + 26, BY + 264, CX + CW2 - 26, BY + 264, BORDER)

AGENTS = [
    ("Risk Monitor",  "The exception on the booking", "Prose to the model, numbers to a threshold.", "LIVE"),
    ("Route Advisor", "Discharge port, routing, ETA", "Prices every option. Refuses one not offered.", "LIVE"),
    ("Comms Agent",   "Carrier and customer mail",    "Two voices, two calls. Flags internal codes.", "LIVE"),
    ("Customs",       "Entry for the new country",    "Escalates rather than files.",                "SCRIPTED"),
    ("TMS Link",      "All of it, onto the record",   "One gate. Nothing bypasses it.",              "DEMO"),
]
for j, (name, writes, how, tag) in enumerate(AGENTS):
    y = BY + 292 + j * 32
    live = tag == "LIVE"
    s.raw(f'<circle cx="{COL_A+4}" cy="{y-4}" r="3.5" fill="{GREEN if live else GRAY400}"/>')
    s.text(COL_A + 18, y, name, 13, 600, FG)
    s.text(COL_W, y, writes, 12, 400, MUTED)
    s.text(COL_H, y, how, 11.5, 400, FAINT)
    s.chip(COL_T, y - 14, 74, 20, tag, fs=8.5,
           fill=GREEN_BG if live else SURFACE, col=GREEN if live else MUTED, weight=700)

# =========================================================================
# WHAT THAT BUYS
# =========================================================================
OY, OH = 716, 136
for i, (head, line) in enumerate((
        ("Speed", "The option existed before the event did."),
        ("Coverage", "Every booking, not the one someone remembered."),
        ("Reassurance", "The reasoning is recorded. A person still approves."))):
    ox = M + i * (CW / 3)
    s.card(ox, OY, CW / 3 - 24, OH)
    s.text(ox + 26, OY + 56, head, 24, 600, FG, ls=-0.5)
    s.text(ox + 26, OY + 86, line, 13.5, 400, MUTED)

s.text(M, 906, "One decision to make. Everything else is already done.", 24, 600, FG, ls=-0.5)
s.footer("05 / THE AGENTS")
s.write("slide-05-the-agents.svg")
