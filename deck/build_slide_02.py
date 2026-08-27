#!/usr/bin/env python3
"""
Slide 02 - THE WHAT.  Emits deck/slide-02-the-what.svg at 1920x1080.

Two folds, deliberately symmetrical so the reader sees "two problems" before
reading a word:

  01  The work is manual        - the same booking, typed into every system
  02  Nothing watches the route - the environment is enormous, and no system
                                  reads it continuously or per booking

The two folds share a spine: badge, title, one line, a diagram, a caption, a
cited stat, a payoff. Symmetry is the argument.
"""
from deckkit import *

s = Slide()
s.header("02 — THE WHAT",
         "Two problems, and they make each other worse.",
         "Every hour spent moving data by hand is an hour nobody is watching the lane.")

FY, FH = 228, 672
FW = (CW - 32) // 2                       # two folds, 32px apart
F1, F2 = M, M + FW + 32
PAD = 36
IW = FW - 2 * PAD                         # inner width of a fold


def fold(x, n, title, line, caption, big, big_label, src, payoff):
    s.card(x, FY, FW, FH)
    tx = x + PAD
    s.card(tx, FY + 30, 34, 34, fill=FG, stroke="none", rx=8)
    s.text(tx + 17, FY + 52, n, 14, 600, CARD, anchor="middle", cls="mono")
    s.text(tx + 48, FY + 53, title, 30, 600, FG, ls=-0.8)
    s.text(tx, FY + 98, line, 15, 400, MUTED)
    s.text(tx, FY + 424, caption, 13, 400, MUTED)
    s.line(tx, FY + 456, x + FW - PAD, FY + 456, BORDER)
    s.raw(f'<text x="{tx}" y="{FY+512}" font-size="44" font-weight="600" fill="{FG}" '
          f'letter-spacing="-1.4" class="num">{esc(big)}</text>')
    s.text(tx, FY + 540, big_label, 13.5, 500, FG)
    s.text(tx, FY + 562, src, 10.5, 400, FAINT, cls="mono")
    s.raw(f'<circle cx="{tx+4}" cy="{FY+608}" r="3.5" fill="{AMBER}"/>')
    s.text(tx + 16, FY + 612, payoff, 14, 500, AMBER)


# =========================================================================
# FOLD 01 - the work is manual
# =========================================================================
fold(F1, "01", "The work is manual.",
     "The same shipment data, entered again in every system it touches.",
     "Every arrow is a person re-typing what the last system already knew.",
     "40%", "of the day on repetitive admin", "logistics industry surveys · upper estimate",
     "Hours a day, and none of it is judgement.")

BW, BH2, BG_ = 240, 70, 28
r1y, r2y = FY + 156, FY + 278
row1 = ["Inbox", "TMS", "Carrier portal"]
row2 = ["Customer", "Invoice", "Customs"]        # the snake runs back right-to-left
for i, lab in enumerate(row1):
    s.chip(F1 + PAD + i * (BW + BG_), r1y, BW, BH2, lab, fs=14,
           fill=CARD, stroke=BORDER_STRONG, col=FG, weight=500)
for i, lab in enumerate(row2):
    s.chip(F1 + PAD + i * (BW + BG_), r2y, BW, BH2, lab, fs=14,
           fill=CARD, stroke=BORDER_STRONG, col=FG, weight=500)

# the five hand-offs, every one of them a re-key
for i in range(2):                                # row 1, left to right
    ax = F1 + PAD + i * (BW + BG_) + BW
    s.line(ax + 5, r1y + BH2 / 2, ax + BG_ - 5, r1y + BH2 / 2, AMBER, 1.6, "ahA")
for i in range(2):                                # row 2, right to left
    ax = F1 + PAD + (2 - i) * (BW + BG_)
    s.line(ax - 5, r2y + BH2 / 2, ax - BG_ + 5, r2y + BH2 / 2, AMBER, 1.6, "ahA")
turn_x = F1 + PAD + 2 * (BW + BG_) + BW / 2       # down the right-hand side
s.line(turn_x, r1y + BH2 + 6, turn_x, r2y - 6, AMBER, 1.6, "ahA")

# =========================================================================
# FOLD 02 - nothing watches the route
# =========================================================================
fold(F2, "02", "Nothing watches the route.",
     "The environment is enormous, and no one is reading it on your bookings.",
     "So the desk finds out afterwards, with no backup route ready.",
     "26,225", "disruption alerts in 2025", "Resilinc EventWatchAI",
     "By the time anyone knows, the delay has already happened.")

RISKS = ["Tariffs", "Sanctions", "War", "Strikes", "Congestion",
         "Low water", "Storms", "Floods", "Earthquakes", "Closures"]
CW_, CH_, CG = 140, 46, 19
for i, lab in enumerate(RISKS):
    cx = F2 + PAD + (i % 5) * (CW_ + CG)
    cy = FY + 148 + (i // 5) * (CH_ + 14)
    s.chip(cx, cy, CW_, CH_, lab, fs=12.5, fill=SURFACE, col=MUTED)

# everything above funnels down to a slot that is empty
for i in range(5):
    fx = F2 + PAD + i * (CW_ + CG) + CW_ / 2
    s.line(fx, FY + 264, fx, FY + 294, GRAY400, 1.4, "ahN")
s.card(F2 + PAD, FY + 302, IW, 74, fill=AMBER_BG, stroke=AMBER, dash="6 5")
s.text(F2 + PAD + IW / 2, FY + 334, "NO SYSTEM HERE", 13, 600, AMBER, anchor="middle", ls=1.4)
s.text(F2 + PAD + IW / 2, FY + 358, "Nothing reads these continuously, or per booking.",
       12.5, 400, AMBER, anchor="middle")

# =========================================================================
s.text(M, 952, "Both jobs land on the same desk. Neither of them has a system.",
       24, 600, FG, ls=-0.5)
s.footer("02 / THE WHAT")
s.write("slide-02-the-what.svg")
