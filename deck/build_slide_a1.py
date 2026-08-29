#!/usr/bin/env python3
"""
Slide A1 - LAB NOTES 1 of 3.  Emits deck/slide-a1-lab-notes.svg.

The setup slide: the question that started the lab day (could a ready-made
AI make our calls?) and the thing it forced us to build first - a practice
world with an answer key, because you cannot grade a decision without one.

Status quo on the left (calls made, never graded, errors hiding), the fix on
the right (6,000 invented shipments where every true outcome is known), and
the unlock across the bottom: every decider now sits the same exam.

House rules hold: amber only where it hurts, green only for the answer key,
every figure counted from our own runs, short plain sentences.
"""
from deckkit import *

GREEN, GREEN_BG = "#0f7b3f", "#e7f5ec"

s = Slide()
s.header("A1 — LAB NOTES · 2026-08-28 · 1 OF 3",
         "Could a ready-made AI make our calls?",
         "The question that started the lab day. Answering it forced us to fix something "
         "bigger first: nobody could grade the calls we already make.")

# =========================================================================
# LEFT - STATUS QUO: calls were made, nobody could mark them
# =========================================================================
AX, AY, AW, AH = M, 232, 852, 456
s.card(AX, AY, AW, AH, fill=CARD, stroke=BORDER_STRONG)
s.band_label(AX + 24, AY + 38, "STATUS QUO · BEFORE THE LAB DAY")
s.text(AX + 24, AY + 78, "Calls were made. Nobody could mark them.", 20, 600, FG, ls=-0.4)

SQ_ROWS = [
    ("Every disruption ends in a call",
     "reroute, hold, or do nothing, for every shipment on the board", False),
    ("Real life never hands out the answer key",
     "you never learn what the choice you did not make would have cost", False),
    ("So errors hid in plain sight",
     "484 needless alarms sat inside our rules, invisible until this day", True),
]
RW_, RH_ = AW - 48, 76
for j, (t, d, pain) in enumerate(SQ_ROWS):
    by = AY + 104 + j * (RH_ + 14)
    s.card(AX + 24, by, RW_, RH_, fill=AMBER_BG if pain else SURFACE,
           stroke=AMBER if pain else "none", rx=R)
    s.text(AX + 40, by + 32, t, 13.5, 600, AMBER if pain else FG)
    s.text(AX + 40, by + 54, d, 11.5, 400, MUTED)

s.text(AX + 24, AY + 400, "Testing any new model was impossible too: scored against our own rules,",
       12, 400, FAINT)
s.text(AX + 24, AY + 419, "it would simply learn to copy our mistakes.", 12, 400, FAINT)

# =========================================================================
# RIGHT - THE FIX: a practice world with an answer key
# =========================================================================
FX, FY, FW, FH = M + AW + 24, 232, 852, 456
s.card(FX, FY, FW, FH, fill=CARD, stroke=BORDER_STRONG)
s.band_label(FX + 24, FY + 38, "THE FIX · A PRACTICE WORLD")
s.text(FX + 24, FY + 78, "So we built a world where every true outcome is known.", 20, 600, FG, ls=-0.4)

FIX_BOXES = [
    ("6,000 made-up shipments", "18 months of disruptions over the product's real routes"),
    ("The desk sees only rough estimates", "how bad each disruption truly is stays hidden, like real life"),
    ("The answer key", "what each call would truly have cost: reroute, hold, or do nothing"),
]
BW_, BH_ = FW - 48, 68
for j, (t, d) in enumerate(FIX_BOXES):
    by = FY + 104 + j * (BH_ + 24)
    last = j == 2
    s.card(FX + 24, by, BW_, BH_, fill=GREEN_BG if last else SURFACE,
           stroke=GREEN if last else "none", rx=R)
    s.text(FX + 40, by + 28, t, 13.5, 600, GREEN if last else FG)
    s.text(FX + 40, by + 49, d, 11.5, 400, MUTED)
    if not last:
        s.line(FX + FW / 2, by + BH_ + 4, FX + FW / 2, by + BH_ + 20, FAINT, 1.4, "ahN")

s.text(FX + 24, FY + 400, "Noise is deliberate: a perfect score would mean cheating. A test fails",
       12, 400, FAINT)
s.text(FX + 24, FY + 419, "the build if any model ever hits 100%.", 12, 400, FAINT)

# =========================================================================
# BOTTOM - WHAT THIS UNLOCKS: everyone sits the same exam
# =========================================================================
UX, UY, UW, UH = M, 712, CW, 168
s.card(UX, UY, UW, UH, fill=CARD, stroke=BORDER_STRONG)
s.band_label(UX + 24, UY + 34, "WHAT THIS UNLOCKS")
s.text(UX + 24, UY + 68, "Every decider sits the same exam.", 18, 600, FG, ls=-0.3)

CY = UY + 92          # top of the flow row
CH_ = 44
DECIDERS = [("Always say do nothing", 186), ("Our shipped rules", 156),
            ("Classic machine learning", 196), ("TabPFN, the ready-made model", 226)]
dx = UX + 24
for label, w in DECIDERS:
    s.chip(dx, CY, w, CH_, label, fs=11.5, fill=SURFACE, col=FG, weight=500)
    dx += w + 10
s.line(dx + 4, CY + CH_ / 2, dx + 40, CY + CH_ / 2, FAINT, 1.4, "ahN")
dx += 52
s.chip(dx, CY, 300, CH_, "ONE EXAM · ONE ANSWER KEY", fs=11.5, fill=SURFACE_2, col=FG, weight=600)
dx += 300
s.line(dx + 4, CY + CH_ / 2, dx + 40, CY + CH_ / 2, FAINT, 1.4, "ahN")
s.text(dx + 52, CY + CH_ / 2 + 5, "Scores: next slide.", 13.5, 600, FG)

# =========================================================================
s.text(M, 940, "You cannot improve what you cannot grade. As of this day, we can grade.",
       24, 600, FG, ls=-0.5)
s.text(W - M, 940, "All figures counted from our own runs · full record: LAB-NOTES-2026-08-28.md",
       12, 400, FAINT, anchor="end")
s.footer("A1 / LAB NOTES · 1 OF 3")
s.write("slide-a1-lab-notes.svg")
