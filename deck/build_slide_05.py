#!/usr/bin/env python3
"""
Slide 05 - THE HOW (the mechanism).  Emits deck/slide-05-the-agents.svg.

Third build. The first proved arithmetic nobody disputes; the second showed a
consequence list without saying when any of it happens. Both missed the actual
mechanism, which is a matter of timing:

  Alternatives are priced for every booking BEFORE anything happens.
  A risk crosses a threshold.
  In the same moment: one decision goes to a person, and every downstream
  artefact is already being drafted.

So the slide is a timeline with a threshold in the middle, and the payoff is
that the two right-hand rows happen simultaneously. Speed / Coverage /
Reassurance sit underneath as the three consequences of that shape.

Every artefact carries the tag of the Worker that produced it, so the three
live agents and the scripted one cannot be confused.
"""
from deckkit import *

GREEN, GREEN_BG = "#0f7b3f", "#e7f5ec"

s = Slide()
s.header("05 — THE HOW",
         "The answer is ready before the risk lands.",
         "One decision goes to a person. Everything else is already being written.")

BY, BH = 230, 470

# =========================================================================
# ALWAYS ON - the work that happens before anything happens
# =========================================================================
AX, AW = M, 430
s.card(AX, BY, AW, BH)
ax = AX + 28
s.text(ax, BY + 40, "ALWAYS ON", 10, 700, FAINT, ls=1.4)

s.raw(f'<text x="{ax}" y="{BY+112}" font-size="34" font-weight="600" fill="{FG}" '
      f'letter-spacing="-1" class="num">42 sources</text>')
s.text(ax, BY + 138, "watched continuously", 13.5, 400, MUTED)
s.line(ax, BY + 172, AX + AW - 28, BY + 172, BORDER)
s.raw(f'<text x="{ax}" y="{BY+232}" font-size="34" font-weight="600" fill="{FG}" '
      f'letter-spacing="-1">Every booking</text>')
s.text(ax, BY + 258, "alternatives already priced", 13.5, 400, MUTED)
s.line(ax, BY + 292, AX + AW - 28, BY + 292, BORDER)
s.text(ax, BY + 330, "None of this waits for an event.", 13, 500, FG)
s.text(ax, BY + 354, "When one lands, the options exist.", 13, 400, MUTED)

# =========================================================================
# THE THRESHOLD
# =========================================================================
TX, TW = 566, 210
s.text(TX + TW / 2, BY + 40, "THRESHOLD", 10, 700, AMBER, ls=1.4, anchor="middle")
s.line(TX + TW / 2, BY + 62, TX + TW / 2, BY + BH - 20, AMBER, 1.6, dash="5 5")
s.card(TX + 8, BY + 150, TW - 16, 96, fill=AMBER_BG, stroke=AMBER)
s.text(TX + TW / 2, BY + 184, "Hamburg strike", 15, 600, FG, anchor="middle")
s.text(TX + TW / 2, BY + 208, "high · 3–5 days", 12.5, 400, AMBER, anchor="middle", cls="mono")
s.text(TX + TW / 2, BY + 232, "crosses the line", 11.5, 400, MUTED, anchor="middle")
s.line(TX + TW - 4, BY + 198, TX + TW + 36, BY + 198, AMBER, 2, "ahA")

# =========================================================================
# THE SAME MOMENT - one decision out, everything else drafted at once
# =========================================================================
CX, CW2 = 816, W - M - 816
s.text(CX, BY + 40, "THE SAME MOMENT", 10, 700, FAINT, ls=1.4)

# -- to the person
s.card(CX, BY + 62, CW2, 148, fill=FG, stroke="none")
s.text(CX + 28, BY + 96, "TO THE PERSON", 10, 700, "#8f8f8f", ls=1.4)
s.text(CX + 28, BY + 138, "Reroute", 30, 600, CARD, ls=-0.8)
s.text(CX + 150, BY + 138, "HAM → RTM", 20, 600, "#f5a623", cls="mono")
s.text(CX + 28, BY + 172, "One call to make. The reasoning is attached.", 13, 400, "#a1a1a1")
s.chip(CX + CW2 - 28 - 210, BY + 118, 100, 34, "Approve", fs=13, fill=CARD, col=FG, weight=600)
s.chip(CX + CW2 - 28 - 100, BY + 118, 100, 34, "Reject", fs=13, fill="#333", col=CARD, weight=600)

# -- drafted in parallel
s.card(CX, BY + 234, CW2, BH - 234, stroke=BORDER_STRONG)
s.text(CX + 28, BY + 268, "DRAFTED IN PARALLEL", 10, 700, FAINT, ls=1.4)
s.text(CX + 240, BY + 268, "already written, waiting behind the same approval", 11.5, 400, FAINT)

ITEMS = [("Carrier mail", "Comms", True), ("Customer mail", "Comms", True),
         ("Exception flag", "Risk", True), ("Discharge · routing · ETA", "Routing", True),
         ("Customs entry, DE → NL", "Customs", False)]
for j, (what, who, live) in enumerate(ITEMS):
    y = BY + 296 + j * 34
    s.raw(f'<circle cx="{CX+34}" cy="{y+10}" r="3.5" fill="{GREEN if live else GRAY400}"/>')
    s.text(CX + 50, y + 14, what, 13.5, 500, FG)
    s.text(CX + 420, y + 14, who, 12, 400, FAINT, cls="mono")
    s.chip(CX + 540, y - 2, 74, 22, "LIVE" if live else "SCRIPTED",
           fs=9, fill=GREEN_BG if live else SURFACE, col=GREEN if live else MUTED, weight=700)

# =========================================================================
# WHAT THAT BUYS
# =========================================================================
OY, OH = 744, 128
for i, (head, line) in enumerate((
        ("Speed", "The option existed before the event did."),
        ("Coverage", "Every booking, not the one someone remembered."),
        ("Reassurance", "The reasoning is recorded. A person still approves."))):
    ox = M + i * (CW / 3)
    s.card(ox, OY, CW / 3 - 24, OH)
    s.text(ox + 26, OY + 52, head, 24, 600, FG, ls=-0.5)
    s.text(ox + 26, OY + 82, line, 13.5, 400, MUTED)

s.text(M, 938, "One decision to make. Everything else is already done.", 24, 600, FG, ls=-0.5)
s.footer("05 / THE AGENTS")
s.write("slide-05-the-agents.svg")
