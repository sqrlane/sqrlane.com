#!/usr/bin/env python3
"""
Slide A2 - LAB NOTES 2 of 3.  Emits deck/slide-a2-lab-notes.svg.

The money slide: what TabPFN changed, status quo vs. after. Left, the
scoreboard - every decider on the same exam, the practice-world caveat
printed ON the chart, the two smaller tasks below it with their honest
qualifiers. Right, three before/after rows: can we grade a call at all,
the needless alarms inside our rules, and which model is picked for the
day there is real history - closed by the honest line that TabPFN itself
is not in the product, its lesson is.

House rules hold: amber only where it hurts, every figure counted from our
own runs, the caveat travels with the numbers.
"""
from deckkit import *

GREEN, GREEN_BG = "#0f7b3f", "#e7f5ec"

s = Slide()
s.header("A2 — LAB NOTES · 2026-08-28 · 2 OF 3",
         "TabPFN won the exam. Our rules got the lesson.",
         "A ready-made table model, zero tuning, on a laptop: best on all three tasks. And the "
         "gap it exposed led to the one question that made the shipped product better.")

# =========================================================================
# LEFT - THE SCOREBOARD
# =========================================================================
BX, BY, BW2, BH2 = M, 232, 940, 648
s.card(BX, BY, BW2, BH2, fill=CARD, stroke=BORDER_STRONG)
s.band_label(BX + 24, BY + 38, "THE EXAM · WHO CALLS IT BEST")
s.text(BX + 24, BY + 66, "Main task shown: choose reroute, hold, or do nothing, per shipment. Same exam for every row.",
       12.5, 400, MUTED)

# The caveat lives ON the chart, dashed and unmissable.
s.card(BX + 24, BY + 82, BW2 - 48, 34, fill=CARD_MUTED, stroke=BORDER_STRONG, rx=R, dash="6 5")
s.text(BX + BW2 / 2, BY + 103, "Practice-world scores only. They say nothing about real shipments,"
       " and never appear in the product.", 11.5, 600, MUTED, anchor="middle")


def hbar(x, y, ln, h, fill):
    ln = max(ln, 6)
    s.raw(f'<path d="M{x},{y} h{ln-4} a4,4 0 0 1 4,4 v{h-8} a4,4 0 0 1 -4,4 h-{ln-4} z" fill="{fill}"/>')


PX, PW_ = BX + 24, BW2 - 48          # plot band
ROWS = [
    ("Always say “do nothing”", 84.1, GRAY400,
     "right mostly by luck: most shipments are fine anyway"),
    ("Our rules, before", 65.7, AMBER,
     "the status quo. 484 needless alarms hiding inside"),
    ("Our rules, after one question", 76.0, "#9a9a9a",
     "the lesson, shipped the same day: up 10 points"),
    ("Classic machine learning", 88.1, "#9a9a9a",
     "gradient-boosted trees, trained on the practice world"),
    ("TabPFN, zero tuning", 89.5, FG,
     "the winner. A ready-made model, run on a laptop CPU"),
]
CY0, PITCH = BY + 150, 68
# recessive grid first, so bars sit on top; the tick row gets its own band
# below the last note so nothing ever collides with it.
for pct in (0, 25, 50, 75, 100):
    gx = PX + PW_ * pct / 100
    s.line(gx, CY0 - 8, gx, CY0 + 4 * PITCH + 66, BORDER)
    s.text(gx, CY0 + 4 * PITCH + 82, f"{pct}%", 9.5, 400, FAINT,
           anchor="middle" if 0 < pct < 100 else ("start" if pct == 0 else "end"), cls="num")
for j, (label, val, col, note) in enumerate(ROWS):
    ry = CY0 + j * PITCH
    s.text(PX, ry + 11, label, 13.5, 600 if col in (FG, AMBER) else 500, FG)
    s.text(PX + PW_, ry + 12, f"{val:.1f}%", 15, 700 if col == FG else 500,
           FG if col != AMBER else AMBER, anchor="end", cls="num")
    hbar(PX, ry + 20, PW_ * val / 100, 18, col)
    if note:
        s.text(PX, ry + 53, note, 11, 400, AMBER if col == AMBER else FAINT)

# The other two tasks, with their honest qualifiers.
TY = CY0 + 4 * PITCH + 108
TCW = (PW_ - 16) / 2
s.card(PX, TY, TCW, 76, fill=SURFACE, stroke="none", rx=R)
s.text(PX + 16, TY + 24, "TASK 2 · HOW LATE, IN DAYS", 9, 700, FAINT, ls=1.2)
s.text(PX + 16, TY + 46, "TabPFN off by 2.33 days on average, vs 2.38", 13, 600, FG)
s.text(PX + 16, TY + 64, "classic ML keeps the tighter worst-case tail", 10.5, 400, FAINT)
s.card(PX + TCW + 16, TY, TCW, 76, fill=SURFACE, stroke="none", rx=R)
s.text(PX + TCW + 32, TY + 24, "TASK 3 · WILL THE DEADLINE BREAK", 9, 700, FAINT, ls=1.2)
s.text(PX + TCW + 32, TY + 46, "TabPFN 0.8814 vs 0.880, a near dead heat", 13, 600, FG)
s.text(PX + TCW + 32, TY + 64, "ranking score, 1.0 = perfect", 10.5, 400, FAINT)

# =========================================================================
# RIGHT - STATUS QUO VS. AFTER
# =========================================================================
VX, VY, VW, VH = M + BW2 + 24, 232, 764, 648
s.card(VX, VY, VW, VH, fill=CARD, stroke=BORDER_STRONG)
s.band_label(VX + 24, VY + 38, "STATUS QUO VS. AFTER THE LAB DAY")

BOXW = (VW - 48 - 44) / 2
AR_X1 = VX + 24 + BOXW + 6
AR_X2 = VX + 24 + BOXW + 38


def vsrow(ry, title, before, after, pain=True, before_fs=12, after_fs=12):
    s.text(VX + 24, ry, title, 13.5, 600, FG)
    by = ry + 12
    s.card(VX + 24, by, BOXW, 56, fill=AMBER_BG if pain else SURFACE,
           stroke=AMBER if pain else "none", rx=R)
    s.text(VX + 40, by + 22, "BEFORE", 8, 700, AMBER if pain else FAINT, ls=1.2)
    s.text(VX + 40, by + 42, before, before_fs, 500, AMBER if pain else MUTED)
    s.line(AR_X1, by + 28, AR_X2, by + 28, FAINT, 1.4, "ahN")
    ax = VX + 24 + BOXW + 44
    s.card(ax, by, BOXW, 56, fill=GREEN_BG, stroke=GREEN, rx=R)
    s.text(ax + 16, by + 22, "AFTER", 8, 700, GREEN, ls=1.2)
    s.text(ax + 16, by + 42, after, after_fs, 500, GREEN)


R1 = VY + 84
vsrow(R1, "Can we grade a routing call at all?",
      "No. Real freight hides the key", "Yes. One exam, 6,000 shipments")

R2 = VY + 194
vsrow(R2, "Needless alarms inside our rules",
      "484 false alarms", "308, one question later", before_fs=13, after_fs=13)
s.text(VX + 24, R2 + 88, "The question: will the trouble still be there when the ship arrives?",
       11.5, 500, FG)
s.text(VX + 24, R2 + 106, "Shipped into the product the same day. The honest cost: 11 real",
       11, 400, FAINT)
s.text(VX + 24, R2 + 123, "catches lost, 218 of 266 still caught.", 11, 400, FAINT)

R3 = VY + 356
vsrow(R3, "Which model, the day real history exists?",
      "Unknown, a guess", "TabPFN, proven on the exam", pain=False)
s.text(VX + 24, R3 + 88, "Won all three tasks with zero tuning, no training run, no GPU.",
       11, 400, FAINT)

# The honest line - same dashed treatment as the chart caveat.
HY = VY + 486
s.card(VX + 24, HY, VW - 48, 116, fill=CARD_MUTED, stroke=BORDER_STRONG, rx=R, dash="6 5")
s.text(VX + 40, HY + 28, "THE HONEST LINE", 9.5, 700, FAINT, ls=1.4)
s.text(VX + 40, HY + 56, "TabPFN itself is not in the product. Its lesson is.", 14.5, 600, FG)
s.text(VX + 40, HY + 80, "The product still runs on rules plus a live language model. What", 11.5, 400, MUTED)
s.text(VX + 40, HY + 97, "shipped is the exam, and the one question the exam surfaced.", 11.5, 400, MUTED)

# =========================================================================
s.text(M, 940, "Same rules, one new question, ten points better. And the next model is already picked.",
       24, 600, FG, ls=-0.5)
s.text(W - M, 940, "All figures counted from our own runs · full record: LAB-NOTES-2026-08-28.md",
       12, 400, FAINT, anchor="end")
s.footer("A2 / LAB NOTES · 2 OF 3")
s.write("slide-a2-lab-notes.svg")
