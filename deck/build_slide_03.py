#!/usr/bin/env python3
"""
Slide 03 - THE WHY.  Emits deck/slide-03-the-why.svg at 1920x1080.

One argument: the desk work is worth ~EUR 4bn a year in Europe, two funded
categories sit either side of it, and the capability strip shows DECIDE empty
on both. That hole is the seam.

Left  - the TAM, derived in the open so every assumption is arguable.
Right - risk / seam / execution, with real companies and real rounds named.

The TAM is DERIVED, not measured. The "1 in 5 on an operating desk" step is an
assumption and is labelled as one on the slide.
"""
from deckkit import *

s = Slide()
s.header("03 — THE WHY",
         "€4bn a year of desk work. Nobody does all of it.",
         "Risk platforms watch and stop. Execution AI starts after the decision. Both are funded.")

TY, TH = 232, 580

# =========================================================================
# LEFT - where the EUR 4bn comes from, shown as arithmetic
# =========================================================================
LX, LW = M, 560
s.card(LX, TY, LW, TH)
lx = LX + 36
s.band_label(lx, TY + 40, "WHERE THE €4BN SITS")


def step(y, big, label):
    s.raw(f'<text x="{lx}" y="{TY+y}" font-size="36" font-weight="600" fill="{FG}" '
          f'letter-spacing="-1.1" class="num">{esc(big)}</text>')
    s.text(lx, TY + y + 26, label, 13, 400, MUTED)


def op(y, sign, note, assumed=False):
    s.text(lx + 4, TY + y, sign, 15, 600, AMBER, cls="mono")
    s.text(lx + 124, TY + y, note, 12.5, 400, FAINT)
    if assumed:
        s.chip(lx + 316, TY + y - 14, 84, 20, "assumed", fs=10,
               fill=AMBER_BG, col=AMBER, weight=600)


step(112, "1.6M", "people in European freight forwarding")
op(174, "÷ 5", "1 in 5 on an operating desk", assumed=True)
step(238, "320,000", "operating desks")
op(300, "× €13,600", "admin cost each, per year")
s.line(lx, TY + 340, LX + LW - 36, TY + 340, BORDER_STRONG)

s.raw(f'<text x="{lx}" y="{TY+424}" font-size="58" font-weight="600" fill="{FG}" '
      f'letter-spacing="-2" class="num">€4.36bn</text>')
s.text(lx, TY + 454, "a year in wages, spent on data entry", 16, 500, FG)
s.text(lx, TY + 512, "UK 66,187 staff / 6,737 firms, scaled to 163,000 EU firms", 10.5, 400, FAINT, cls="mono")
s.text(lx, TY + 530, "€34k salary × 40% admin · IBISWorld · SalaryExpert", 10.5, 400, FAINT, cls="mono")

# =========================================================================
# RIGHT - two funded categories, and the hole between them
# =========================================================================
C1, C2, C3 = 688, 1066, 1484
W1, W2 = 340, 380

VERBS = ["WATCH", "DECIDE", "ACT", "RECORD"]


def strip(x, w, states, on=FG):
    inner = w - 48
    seg = (inner - 3 * 12) / 4
    for i, (v, lit) in enumerate(zip(VERBS, states)):
        sx = x + 24 + i * (seg + 12)
        s.card(sx, TY + 150, seg, 10, fill=on if lit else GRAY400, stroke="none", rx=5)
        s.text(sx, TY + 178, v, 9.5, 600 if lit else 500, on if lit else FAINT, ls=0.4, cls="mono")


def side(x, label, verb, line, vendors, states, big, big_label, source_lines=()):
    s.card(x, TY, W1, TH)
    tx = x + 24
    s.text(tx, TY + 40, label, 11, 600, FAINT, ls=1.4)
    s.text(tx, TY + 84, verb, 22, 600, FG, ls=-0.5)
    s.text(tx, TY + 112, line, 13, 400, MUTED)
    strip(x, W1, states)
    for i, v in enumerate(vendors):
        s.chip(tx, TY + 218 + i * 42, W1 - 48, 34, v, fs=13, fill=SURFACE, col=FG)
    s.line(tx, TY + 400, x + W1 - 24, TY + 400, BORDER)
    s.raw(f'<text x="{tx}" y="{TY+452}" font-size="30" font-weight="600" fill="{FG}" '
          f'letter-spacing="-0.9" class="num">{esc(big)}</text>')
    s.text(tx, TY + 476, big_label, 12, 400, FAINT)
    for i, ln in enumerate(source_lines):
        s.text(tx, TY + 500 + i * 16, ln, 9.5, 400, FAINT, cls="mono")


side(C1, "RISK PLATFORMS", "Watch, then stop.", "Never touch the booking.",
     ["Everstream", "Interos", "Resilinc"], [1, 0, 0, 0],
     "$1bn", "Interos valuation, 2024")

# Derived: Augment $85M Series A (Sept 2025) + Nexcade $8.5M pre-seed/seed
# (Oct 2025 + Jul 2026) + 5U AI $3.2M pre-seed (Jul 2026) = $96.7M, all
# inside the trailing 12 months. Zauber's own round (Sept 2025) is real but
# its size is not reliably reported, so it is named as a vendor without
# being added to the sum - never invent the missing number.
side(C3, "EXECUTION AI", "Act, once you decide.", "Never touch risk.",
     ["5U AI", "Augment", "Nexcade", "Zauber"], [0, 0, 1, 1],
     "$96.7M", "raised in the last 12 months",
     source_lines=["Augment $85M · Nexcade $8.5M · 5U AI $3.2M",
                    "press releases · Zauber's round size undisclosed"])

# -- the seam itself -------------------------------------------------------
s.card(C2, TY, W2, TH, fill=AMBER_BG, stroke="#96580a3d")
tx = C2 + 24
s.text(tx, TY + 40, "THE SEAM", 11, 600, AMBER, ls=1.4)
s.raw(f'<text x="{tx}" y="{TY+100}" font-size="46" font-weight="600" fill="{FG}" '
      f'letter-spacing="-1.6">DECIDE</text>')
s.text(tx, TY + 126, "empty on both sides", 14, 500, AMBER)
strip(C2, W2, [1, 1, 1, 1], on=AMBER)
s.text(tx, TY + 244, "One loop, one record.", 17, 600, FG)
s.text(tx, TY + 272, "Watch and act are sold. The step between is not.", 13, 400, MUTED)
s.line(tx, TY + 400, C2 + W2 - 24, TY + 400, "#96580a3d")
s.raw(f'<rect x="{tx}" y="{TY+430}" width="22" height="22" rx="6" fill="{FG}"/>')
s.raw(f'<path d="M{tx+5.5} {TY+446}h11 M{tx+5.5} {TY+441}h7.5 M{tx+5.5} {TY+436}h4" '
      f'stroke="{CARD}" stroke-width="1.8" stroke-linecap="round"/>')
s.text(tx + 32, TY + 447, "SQRlane", 17, 600, FG)

# =========================================================================
s.text(M, 886, "Alerts are a commodity. The record of why a booking moved is not.",
       24, 600, FG, ls=-0.5)
s.text(M, 918, "163,000 forwarding businesses in Europe. 24 of the top 25 already run CargoWise.",
       13, 400, MUTED)
s.text(W - M, 918, "TAM derived from cited sources, not measured. Steps shown left.",
       11.5, 400, FAINT, anchor="end")
s.footer("03 / THE WHY")
s.write("slide-03-the-why.svg")
