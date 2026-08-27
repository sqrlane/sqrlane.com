#!/usr/bin/env python3
"""
Slide 04 - THE HOW.  Emits deck/slide-04-the-how.svg at 1920x1080.

The loop, drawn as a horseshoe so it visibly opens and closes in the same
place. The TMS spans the top and is entered twice - read on the left, written
on the right - because that double entry IS the product thesis.

Every number is counted from a real offline cycle:
  python3 -c "from src import orchestrator; orchestrator.run_cycle(live=False)"
  -> 7 bookings, 42 sources, 2 reroute / 1 hold / 4 on plan, 6 drafts,
     12 write-backs, all QUEUED - not written.
"""
from deckkit import *

s = Slide()
s.header("04 — THE HOW",
         "One loop. It opens and closes on the booking.",
         "Every step works on the same record. Nothing the agents do happens beside the TMS.")

# =========================================================================
# THE TMS - the top of the horseshoe, entered twice
# =========================================================================
TY, TH2 = 246, 92
s.card(M, TY, CW, TH2, fill=SURFACE, stroke=BORDER_STRONG)
s.text(M + 28, TY + 38, "THE TMS", 11, 600, FAINT, ls=1.4)
s.text(M + 28, TY + 64, "The system of record", 19, 600, FG)
s.text(M + 300, TY + 58,
       "booking_ref · port_of_discharge · routing_code · eta · exception_flag · communication_log",
       12.5, 400, FAINT, cls="mono")
s.chip(W - M - 190, TY + 34, 162, 26, "demo connector", fs=11, fill=CARD,
       stroke=BORDER_STRONG, col=MUTED, weight=600)

IN_X, OUT_X = 420, 1500
s.line(IN_X, TY + TH2 + 6, IN_X, 396, AMBER, 1.8, "ahA")
s.text(IN_X + 16, TY + TH2 + 40, "7 bookings in", 13, 600, AMBER)
s.line(OUT_X, 396, OUT_X, TY + TH2 + 6, AMBER, 1.8, "ahA")
s.text(OUT_X + 16, TY + TH2 + 40, "12 changes out", 13, 600, AMBER)

# =========================================================================
# THE FOUR STAGES
# =========================================================================
SY, SH, SW, SG = 404, 300, 390, 56


def stage(i, n, name, big, label, detail, mech):
    x = M + i * (SW + SG)
    s.card(x, SY, SW, SH)
    tx = x + 26
    s.card(tx, SY + 26, 30, 30, fill=FG, stroke="none", rx=8)
    s.text(tx + 15, SY + 46, n, 12.5, 600, CARD, anchor="middle", cls="mono")
    s.text(tx + 42, SY + 47, name, 16, 600, FG, ls=0.3)
    s.raw(f'<text x="{tx}" y="{SY+116}" font-size="40" font-weight="600" fill="{FG}" '
          f'letter-spacing="-1.2" class="num">{esc(big)}</text>')
    s.text(tx, SY + 142, label, 13.5, 500, FG)
    for j, d in enumerate(detail):
        s.text(tx, SY + 178 + j * 19, d, 12, 400, FAINT, cls="mono")
    s.line(tx, SY + 222, x + SW - 26, SY + 222, BORDER)
    s.text(tx, SY + 252, mech, 13, 400, MUTED)
    if i < 3:
        s.line(x + SW + 12, SY + SH / 2, x + SW + SG - 12, SY + SH / 2, FAINT, 1.5, "ahN")


stage(0, "01", "WATCH", "42", "sources, six families",
      ["news · rivers · weather", "hazards · filings · rates"],
      "Prose goes to the model. Numbers go to a threshold.")
stage(1, "02", "DECIDE", "2 · 1 · 4", "reroute · hold · on plan",
      ["slack vs added transit", "vs expected delay"],
      "The reasoning is recorded on the booking.")
stage(2, "03", "DRAFT", "6", "emails written",
      ["carrier", "customer"],
      "Two voices, written separately. Neither is sent.")
stage(3, "04", "QUEUE", "12", "changes, back on the record",
      ["exception · discharge · routing", "eta · comms log"],
      "The four bookings on plan queue nothing at all.")

# =========================================================================
# THE GATE
# =========================================================================
GY, GH = 760, 92
s.card(M, GY, CW, GH, fill=FG, stroke="none")
s.text(M + 28, GY + 38, "THE GATE", 11, 600, "#8f8f8f", ls=1.4)
s.text(M + 28, GY + 66, "Nothing is sent. Nothing is written. A person approves, or it does not happen.",
       21, 600, CARD)
for i, (v, k) in enumerate((("6", "drafted"), ("0", "sent"), ("12", "queued"), ("0", "written"))):
    gx = W - M - 620 + i * 155
    s.raw(f'<text x="{gx}" y="{GY+54}" font-size="28" font-weight="600" fill="{CARD}" '
          f'class="num">{esc(v)}</text>')
    s.text(gx, GY + 74, k, 11.5, 400, "#a1a1a1")

# =========================================================================
s.text(M, 918, "Risk platforms stop after 01. Execution AI starts at 03. Nobody else runs 02.",
       24, 600, FG, ls=-0.5)
s.text(W - M, 918, "Counted from one offline cycle, not illustrative.",
       11.5, 400, FAINT, anchor="end")
s.footer("04 / THE HOW")
s.write("slide-04-the-how.svg")
