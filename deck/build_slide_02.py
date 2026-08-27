#!/usr/bin/env python3
"""
Slide 02 - THE WHAT.  Emits deck/slide-02-the-what.svg at 1920x1080.

Two folds, deliberately symmetrical so the reader sees "two problems" before
reading a word:

  01  The work is manual        - the same three fields, re-typed into six
                                  systems; the repetition is the graphic
  02  Nothing watches the route - ten of the things that move a lane, with a
                                  faded row above them because ten is a sample,
                                  not the list - funnelled into an empty slot

Each fold ends in two numbers: what it costs in time, and what that is in money.
The money figures are DERIVED, not measured, so each one shows its arithmetic
in the source line. Nothing here is a claim about SQRlane.
"""
from deckkit import *

FADE = f'''<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="{CARD}" stop-opacity="1"/>
  <stop offset="0.62" stop-color="{CARD}" stop-opacity="0.94"/>
  <stop offset="1" stop-color="{CARD}" stop-opacity="0.28"/>
</linearGradient>
'''

s = Slide(extra_defs=FADE)
s.header("02 — THE WHAT",
         "Two problems, and they make each other worse.",
         "Every hour spent moving data by hand is an hour nobody is watching the lane.")

FY, FH = 228, 672
FW = (CW - 32) // 2
F1, F2 = M, M + FW + 32
PAD = 36
IW = FW - 2 * PAD


def fold(x, n, title, line, caption, stats, payoff):
    s.card(x, FY, FW, FH)
    tx = x + PAD
    s.card(tx, FY + 30, 34, 34, fill=FG, stroke="none", rx=8)
    s.text(tx + 17, FY + 52, n, 14, 600, CARD, anchor="middle", cls="mono")
    s.text(tx + 48, FY + 53, title, 30, 600, FG, ls=-0.8)
    s.text(tx, FY + 98, line, 15, 400, MUTED)
    s.text(tx, FY + 424, caption, 13, 400, MUTED)
    s.line(tx, FY + 456, x + FW - PAD, FY + 456, BORDER)
    for i, (big, label, src) in enumerate(stats):
        sx = tx + i * (IW / 2)
        s.raw(f'<text x="{sx}" y="{FY+508}" font-size="40" font-weight="600" fill="{FG}" '
              f'letter-spacing="-1.2" class="num">{esc(big)}</text>')
        s.text(sx, FY + 534, label, 13, 500, FG)
        s.text(sx, FY + 555, src, 10.5, 400, FAINT, cls="mono")
    s.raw(f'<circle cx="{tx+4}" cy="{FY+608}" r="3.5" fill="{AMBER}"/>')
    s.text(tx + 16, FY + 612, payoff, 14, 500, AMBER)


# =========================================================================
# FOLD 01 - the work is manual
# =========================================================================
fold(F1, "01", "The work is manual.",
     "The same three fields, re-typed into every system the booking touches.",
     "Six systems. One set of facts. Nobody adds anything on the way through.",
     [("40%", "of the day on repetitive admin", "logistics surveys · upper estimate"),
      ("€13,600", "per desk, per year", "€34k avg salary × 40% · SalaryExpert")],
     "Hours a day, and none of it is judgement.")

BW, BH2, BG_ = 240, 92, 28
r1y, r2y = FY + 150, FY + 282
FIELDS = ["ref", "container", "ETA"]


def system_box(bx, by, name):
    """Name on top, then the identical three fields underneath. Drawing the
    same pills six times is the whole point - it is duplication, not work."""
    s.card(bx, by, BW, BH2, fill=CARD, stroke=BORDER_STRONG)
    s.text(bx + BW / 2, by + 32, name, 14, 500, FG, anchor="middle")
    pw, pg = 64, 8
    x0 = bx + (BW - (3 * pw + 2 * pg)) / 2
    for i, f in enumerate(FIELDS):
        px = x0 + i * (pw + pg)
        s.card(px, by + 48, pw, 22, fill=SURFACE, stroke="none", rx=4)
        s.text(px + pw / 2, by + 63, f, 9.5, 500, FAINT, anchor="middle", cls="mono")


for i, lab in enumerate(["Inbox", "TMS", "Carrier portal"]):
    system_box(F1 + PAD + i * (BW + BG_), r1y, lab)
for i, lab in enumerate(["Customer", "Invoice", "Customs"]):
    system_box(F1 + PAD + i * (BW + BG_), r2y, lab)

for i in range(2):                                    # row 1, left to right
    ax = F1 + PAD + i * (BW + BG_) + BW
    s.line(ax + 5, r1y + BH2 / 2, ax + BG_ - 5, r1y + BH2 / 2, AMBER, 1.6, "ahA")
for i in range(2):                                    # row 2, back right to left
    ax = F1 + PAD + (2 - i) * (BW + BG_)
    s.line(ax - 5, r2y + BH2 / 2, ax - BG_ + 5, r2y + BH2 / 2, AMBER, 1.6, "ahA")
turn_x = F1 + PAD + 2 * (BW + BG_) + BW / 2
s.line(turn_x, r1y + BH2 + 6, turn_x, r2y - 6, AMBER, 1.6, "ahA")

# =========================================================================
# FOLD 02 - nothing watches the route
# =========================================================================
fold(F2, "02", "Nothing watches the route.",
     "The environment is enormous, and no one is reading it on your bookings.",
     "So the desk finds out afterwards, with no backup route ready.",
     [("26,225", "disruption alerts in 2025", "Resilinc EventWatchAI"),
      ("€1,000+", "surcharge, per container", "Rhine low water · Aug 2026")],
     "By the time anyone knows, the delay has already happened.")

CW_, CH_, CG = 140, 46, 19
GHOST = ["Piracy", "Fuel", "Inspections", "Capacity", "Blank sailings"]
RISKS = ["Tariffs", "Sanctions", "War", "Strikes", "Congestion",
         "Low water", "Storms", "Floods", "Earthquakes", "Closures"]


def risk_row(y, labels, col=MUTED):
    for i, lab in enumerate(labels):
        s.chip(F2 + PAD + i * (CW_ + CG), y, CW_, CH_, lab, fs=12.5, fill=SURFACE, col=col)


# ten is a sample, not the list - so the grid runs off the top of the fold
risk_row(FY + 110, GHOST, col=FAINT)
s.raw(f'<rect x="{F2+PAD-4}" y="{FY+106}" width="{IW+8}" height="52" fill="url(#fade)"/>')
risk_row(FY + 174, RISKS[:5])
risk_row(FY + 232, RISKS[5:])

for i in range(5):
    fx = F2 + PAD + i * (CW_ + CG) + CW_ / 2
    s.line(fx, FY + 286, fx, FY + 310, GRAY400, 1.4, "ahN")
s.card(F2 + PAD, FY + 316, IW, 70, fill=AMBER_BG, stroke=AMBER, dash="6 5")
s.text(F2 + PAD + IW / 2, FY + 346, "NO SYSTEM HERE", 13, 600, AMBER, anchor="middle", ls=1.4)
s.text(F2 + PAD + IW / 2, FY + 369, "Nothing reads these continuously, or per booking.",
       12.5, 400, AMBER, anchor="middle")

# =========================================================================
s.text(M, 952, "Both jobs land on the same desk. Neither of them has a system.",
       24, 600, FG, ls=-0.5)
s.text(W - M, 952, "Money figures are derived, not measured. The arithmetic is shown above.",
       12, 400, FAINT, anchor="end")
s.footer("02 / THE WHAT")
s.write("slide-02-the-what.svg")
