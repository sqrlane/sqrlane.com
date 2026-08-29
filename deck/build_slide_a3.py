#!/usr/bin/env python3
"""
Slide A3 - LAB NOTES 3 of 3.  Emits deck/slide-a3-lab-notes.svg.

The real-world slide: the same day the watch layer widened from 42 to 60
live sources, the whole read ran outside the lab for the first time, from
an ordinary laptop. Left, what answered - 47 of 60 on first contact, one
square per source, plus the unscripted moment. Right, the five things only
reality could catch: four fixed the same day, one honestly open.

House rules hold: amber only where it hurts, green only for answered and
fixed, every figure counted from the run's own report.
"""
from deckkit import *

GREEN, GREEN_BG = "#0f7b3f", "#e7f5ec"

s = Slide()
s.header("A3 — LAB NOTES · 2026-08-28 · 3 OF 3",
         "Then we switched everything on, for real.",
         "The same day, the watch layer widened from 42 to 60 live sources, and the full read "
         "ran outside the lab for the first time, from an ordinary laptop.")

# =========================================================================
# LEFT - THE FIRST FULL LIVE READ
# =========================================================================
LX, LY, LW, LH = M, 232, 780, 648
s.card(LX, LY, LW, LH, fill=CARD, stroke=BORDER_STRONG)
s.band_label(LX + 24, LY + 38, "THE FIRST FULL LIVE READ")

s.raw(f'<text x="{LX+24}" y="{LY+108}" font-size="40" font-weight="600" fill="{FG}" '
      f'class="num" letter-spacing="-1.2">47 of 60</text>')
s.text(LX + 24, LY + 132, "sources answered on first contact", 12, 400, MUTED)

# 60 squares, one per source, counted from the run report.
GX0, GY0, SQ, GAP = LX + 24, LY + 158, 26, 8
for k in range(60):
    gx = GX0 + (k % 15) * (SQ + GAP)
    gy = GY0 + (k // 15) * (SQ + GAP)
    if k < 47:
        fill, stroke = GREEN_BG, GREEN
    elif k < 58:
        fill, stroke = SURFACE_2, BORDER_STRONG
    else:
        fill, stroke = AMBER_BG, AMBER
    s.raw(f'<rect x="{gx}" y="{gy}" width="{SQ}" height="{SQ}" rx="4" '
          f'fill="{fill}" stroke="{stroke}"/>')

LEG = [(GREEN_BG, GREEN, "47 answered, across all six source families"),
       (SURFACE_2, BORDER_STRONG, "11: one news service, blocked from that laptop alone (all its queries)"),
       (AMBER_BG, AMBER, "2 dead links, found and replaced the same day")]
for j, (fill, stroke, lab) in enumerate(LEG):
    ly = LY + 314 + j * 21
    s.raw(f'<rect x="{LX+24}" y="{ly-10}" width="12" height="12" rx="3" fill="{fill}" stroke="{stroke}"/>')
    s.text(LX + 44, ly, lab, 11, 400, MUTED)

s.line(LX + 24, LY + 396, LX + LW - 24, LY + 396, BORDER)
s.band_label(LX + 24, LY + 426, "BUILT THE SAME DAY")
s.text(LX + 24, LY + 452, "The watch widened from 42 to 60 sources, in six families.", 12.5, 500, FG)
FAMS = [("News", "41"), ("Rivers", "7"), ("Weather & sea", "4"),
        ("Hazards", "5"), ("Government", "2"), ("Rates", "1")]
FCW = (LW - 48 - 20) / 3
for j, (fam, n) in enumerate(FAMS):
    fx = LX + 24 + (j % 3) * (FCW + 10)
    fy = LY + 468 + (j // 3) * 27
    s.card(fx, fy, FCW, 22, fill=SURFACE, stroke="none", rx=4)
    s.text(fx + 10, fy + 15, fam, 10.5, 500, MUTED)
    s.text(fx + FCW - 10, fy + 15, n, 10.5, 600, FG, anchor="end", cls="num")

uy = LY + 542
s.card(LX + 24, uy, LW - 48, 82, fill=GREEN_BG, stroke=GREEN, rx=R)
s.text(LX + 40, uy + 26, "UNSCRIPTED, DURING THE TEST", 9.5, 700, GREEN, ls=1.4)
s.text(LX + 40, uy + 50, "Hamburg's own broadcaster carried a real transport closure in Hamburg.", 11.5, 500, GREEN)
s.text(LX + 40, uy + 68, "The product's own story, happening live, on the day we first listened properly.", 11, 400, GREEN)

# =========================================================================
# RIGHT - WHAT ONLY REALITY COULD CATCH
# =========================================================================
RX, RY, RW, RH = M + LW + 24, 232, 924, 648
s.card(RX, RY, RW, RH, fill=CARD, stroke=BORDER_STRONG)
s.band_label(RX + 24, RY + 38, "WHAT ONLY REALITY COULD CATCH")
s.text(RX + 24, RY + 66, "Every stub and test had passed for months. One afternoon against real servers found five things.",
       12.5, 400, MUTED)

FIND = [
    ("FIXED", "The river reader cried wolf",
     "A dry cell on the flood map came back as a river crisis that was not there.",
     "Fixed: zero flow now means no reading, never an alarm."),
    ("FIXED", "Three services turned us away",
     "Our requests bent their rules in small ways that only real servers reject.",
     "Fixed: every request rewritten to the letter of each service's spec."),
    ("FIXED", "A warning quoted the wrong line",
     "A river alert cited a danger threshold the water had never actually crossed.",
     "Fixed: every alert now quotes the exact threshold it crossed."),
    ("FIXED", "Two links had quietly died",
     "Two news feeds had rotted since they were first wired in.",
     "Fixed: both replaced the same day. Backup readers covered the gap meanwhile."),
    ("OPEN", "One service stayed out of reach",
     "One news service was unreachable from that laptop. Everything else read fine.",
     "The run degraded cleanly, as designed. The diagnosis is still open."),
]
for j, (tag, title, what, fix) in enumerate(FIND):
    fy = RY + 100 + j * 104
    open_ = tag == "OPEN"
    s.chip(RX + 24, fy + 2, 52, 19, tag, fs=8.5, fill=AMBER_BG if open_ else GREEN_BG,
           col=AMBER if open_ else GREEN, weight=700)
    s.text(RX + 92, fy + 16, title, 13.5, 600, FG)
    s.text(RX + 92, fy + 38, what, 12, 400, MUTED)
    s.text(RX + 92, fy + 58, fix, 11.5, 400, AMBER if open_ else FAINT)
    if j < 4:
        s.line(RX + 24, fy + 80, RX + RW - 24, fy + 80, BORDER)

# =========================================================================
s.text(M, 940, "Five faults no rehearsal could find. Four fixed the same day. One honestly open.",
       24, 600, FG, ls=-0.5)
s.text(W - M, 940, "All figures counted from our own runs · full record: LAB-NOTES-2026-08-28.md",
       12, 400, FAINT, anchor="end")
s.footer("A3 / LAB NOTES · 3 OF 3")
s.write("slide-a3-lab-notes.svg")
