#!/usr/bin/env python3
"""
Slide 05 - THE HOW (the agents).  Emits deck/slide-05-the-agents.svg.

Rebuilt. The first version proved the advisor's arithmetic with a EUR 234,420
vs EUR 91,000 comparison, which proves nothing: at 2.6x apart no judgement is
required. The decisions that need a system are the near-ties, and what breaks a
near-tie is the work that follows - which is exactly what nobody prices.

So the payoff is no longer a cost bar. It is one reroute and the eight things
it moves, taken from a real run of SHP-001 under the Hamburg strike, customs
re-entry included.

Agent columns are stripped to one line per row. MODEL / CODE / GUARD RAIL is
the structure; the guard-rail row is the one a competitor cannot fill in.
"""
from deckkit import *

GREEN, GREEN_BG = "#0f7b3f", "#e7f5ec"

s = Slide()
s.header("05 — THE HOW",
         "Deciding takes a second. The paperwork takes the day.",
         "The model reads and judges. Everything else is computed, and every consequence is queued.")

# =========================================================================
# THE FOUR AGENTS - one line per row
# =========================================================================
AY, AH, AW, AG = 222, 310, 408, 32


def agent(i, name, tag, tag_col, tag_bg, does, model, code, guard):
    x = M + i * (AW + AG)
    s.card(x, AY, AW, AH)
    tx = x + 26
    s.text(tx, AY + 42, name, 18, 600, FG, ls=-0.2)
    s.chip(x + AW - 26 - 62, AY + 26, 62, 22, tag, fs=9.5, fill=tag_bg, col=tag_col, weight=700)
    s.text(tx, AY + 68, does, 14, 500, MUTED)
    s.line(tx, AY + 92, x + AW - 26, AY + 92, BORDER)
    for j, (label, val) in enumerate((("MODEL", model), ("CODE", code), ("GUARD RAIL", guard))):
        y = AY + 122 + j * 58
        hot = label == "GUARD RAIL"
        s.text(tx, y, label, 9.5, 700, AMBER if hot else FAINT, ls=1.3)
        s.text(tx, y + 22, val, 13, 500 if hot else 400, FG if hot else MUTED)


agent(0, "Risk Monitor", "LIVE", GREEN, GREEN_BG, "Reads 42 sources.",
      "Classifies prose.", "Thresholds every number.", "No source is load-bearing.")
agent(1, "Route Advisor", "LIVE", GREEN, GREEN_BG, "Decides each booking.",
      "Picks, and explains.", "Prices every option.", "Refuses a route it was not offered.")
agent(2, "Comms Agent", "LIVE", GREEN, GREEN_BG, "Writes the mail.",
      "Two voices, two calls.", "Builds the facts.", "Flags internal codes to a human.")
agent(3, "TMS Link", "DEMO", MUTED, SURFACE, "Puts it all back.",
      "Nothing. No model call.", "Field changes on the record.", "One gate. Nothing bypasses it.")

# =========================================================================
# ONE DECISION, AND EVERYTHING IT MOVES
# =========================================================================
BY, BH = 566, 290
s.card(M, BY, CW, BH, fill=CARD, stroke=BORDER_STRONG)
s.text(M + 28, BY + 34, "ONE DECISION, AND EVERYTHING IT MOVES", 10, 700, FAINT, ls=1.4)

s.text(M + 28, BY + 96, "Reroute", 36, 600, FG, ls=-1.1)
s.text(M + 28, BY + 126, "HAM → RTM", 16, 600, AMBER, cls="mono")
s.text(M + 28, BY + 154, "SHP-001 · automotive parts", 12.5, 400, FAINT)
s.line(M + 28, BY + 180, M + 380, BY + 180, BORDER)
s.text(M + 28, BY + 210, "8 consequences", 20, 600, FG)
s.text(M + 28, BY + 234, "none of them typed by a person", 12.5, 400, MUTED)

s.line(M + 410, BY + 145, M + 450, BY + 145, AMBER, 2, "ahA")

ROWS_A = [("exception_flag", "EVT-HAM-STRIKE"),
          ("port_of_discharge", "HAM → RTM"),
          ("routing_code", "R-HAM-STD → R-RTM-ALT"),
          ("eta", "+2 days")]
ROWS_B = [("booking_status", "rerouted"),
          ("communication_log", "carrier draft"),
          ("communication_log", "customer draft"),
          ("customs entry", "DE → NL · B/L reissue")]

for col, rows in ((M + 480, ROWS_A), (M + 1090, ROWS_B)):
    for j, (field, val) in enumerate(rows):
        y = BY + 90 + j * 44
        s.text(col, y, field, 12.5, 400, FAINT, cls="mono")
        s.text(col + 200, y, val, 13, 500, FG, cls="mono")
        s.line(col, y + 16, col + 540, y + 16, BORDER)

# =========================================================================
s.text(M, 904, "When two options are close, this is what actually decides it.",
       24, 600, FG, ls=-0.5)
s.text(W - M, 904, "One real run. Nine more Workers are tagged SCRIPTED on screen.",
       11.5, 400, FAINT, anchor="end")
s.footer("05 / THE AGENTS")
s.write("slide-05-the-agents.svg")
