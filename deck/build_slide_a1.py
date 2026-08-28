#!/usr/bin/env python3
"""
Slide A1 - LAB NOTES (appendix).  Emits deck/slide-a1-lab-notes.svg.

Explains LAB-NOTES-2026-08-28.md step by step, in plain language, for a mixed
technical / non-technical room. Three parts under a five-step spine -

  the practice world: why you cannot grade a decision without an answer key,
  and the synthetic book that provides one
  the scoreboard: every decider on the same test, with the practice-world
  caveat printed ON the chart, not near it
  the real-world test: the first live read of everything, and what running
  it for real caught that no stub could

House rules hold: amber only where it hurts, green only for live/fixed,
every figure counted from our own runs, and the practice-world scores carry
their disclaimer on the slide itself.
"""
from deckkit import *

GREEN, GREEN_BG = "#0f7b3f", "#e7f5ec"

s = Slide()
s.header("A1 — LAB NOTES · 2026-08-28",
         "One day in the lab, step by step.",
         "We tested an off-the-shelf AI on our decisions, made our own rules measurably "
         "smarter, and ran every live source against the real world for the first time.")

# =========================================================================
# THE FIVE STEPS - the spine
# =========================================================================
SY = 232
STEPS = [
    ("Ask", ["Can a ready-made AI model", "make our reroute calls?"]),
    ("Build a practice world", ["6,000 invented shipments where", "we know every true outcome."]),
    ("Score everyone on it", ["Our rules, classic ML and the", "new model - same exam for all."]),
    ("Meet the real world", ["Run all 60 live sources for the", "first time. Fix what breaks."]),
    ("Keep the receipts", ["Every number labelled, recorded,", "and guarded by a test."]),
]
SCW = (CW - 4 * 16) / 5
for i, (title, desc) in enumerate(STEPS):
    x = M + i * (SCW + 16)
    s.raw(f'<circle cx="{x+15}" cy="{SY+14}" r="14" fill="{FG}"/>')
    s.text(x + 15, SY + 19, str(i + 1), 13, 700, CARD, anchor="middle", cls="num")
    s.text(x + 38, SY + 19, title, 14.5, 600, FG, ls=-0.2)
    for j, line in enumerate(desc):
        s.text(x + 38, SY + 42 + j * 17, line, 11.5, 400, FAINT)
    if i < 4:
        s.line(x + SCW - 2, SY + 14, x + SCW + 12, SY + 14, GRAY400, 1.4, "ahN")

# =========================================================================
# CARD A - THE PRACTICE WORLD (steps 1-2)
# =========================================================================
AX, AY, AW, AH = M, 330, 500, 552
s.card(AX, AY, AW, AH, fill=CARD, stroke=BORDER_STRONG)
s.band_label(AX + 24, AY + 38, "01-02 · WHY A PRACTICE WORLD")

WHY = ["You cannot grade an answer without an answer key,",
       "and real freight never hands one out. Scoring a model",
       "against our own rules would just teach it to copy them."]
for j, line in enumerate(WHY):
    s.text(AX + 24, AY + 68 + j * 19, line, 12.5, 400, MUTED)

BOXES = [
    ("6,000 invented shipments", "18 months of disruptions over the product's real routes"),
    ("The desk sees only noisy estimates", "how bad each disruption truly is stays hidden - like real life"),
    ("The answer key", "what every choice would truly have cost: reroute, hold, or wait"),
]
BW_, BH_ = AW - 48, 56
for j, (t, d) in enumerate(BOXES):
    by = AY + 140 + j * (BH_ + 26)
    s.card(AX + 24, by, BW_, BH_, fill=SURFACE if j < 2 else GREEN_BG,
           stroke="none" if j < 2 else GREEN, rx=R)
    s.text(AX + 40, by + 24, t, 13, 600, FG if j < 2 else GREEN)
    s.text(AX + 40, by + 42, d, 11, 400, MUTED)
    if j < 2:
        s.line(AX + AW / 2, by + BH_ + 4, AX + AW / 2, by + BH_ + 22, FAINT, 1.4, "ahN")

s.text(AX + 24, AY + 392, "Noise is deliberate: a perfect score would mean cheating,", 11.5, 400, FAINT)
s.text(AX + 24, AY + 409, "so a test fails the build if any model ever hits 100%.", 11.5, 400, FAINT)

s.line(AX + 24, AY + 430, AX + AW - 24, AY + 430, BORDER)
s.band_label(AX + 24, AY + 460, "BUILT THE SAME DAY")
s.text(AX + 24, AY + 486, "The watch layer widened from 42 to 60 live sources.", 12.5, 500, FG)
FAMS = [("News", "41"), ("Rivers", "7"), ("Weather & sea", "4"),
        ("Hazards", "5"), ("Government", "2"), ("Rates", "1")]
FCW = (BW_ - 2 * 10) / 3
for j, (fam, n) in enumerate(FAMS):
    fx = AX + 24 + (j % 3) * (FCW + 10)
    fy = AY + 500 + (j // 3) * 24
    s.card(fx, fy, FCW, 20, fill=SURFACE, stroke="none", rx=4)
    s.text(fx + 10, fy + 14, fam, 10, 500, MUTED)
    s.text(fx + FCW - 10, fy + 14, n, 10, 600, FG, anchor="end", cls="num")

# =========================================================================
# CARD B - THE SCOREBOARD (step 3)
# =========================================================================
BX, BY, BW2, BH2 = M + AW + 24, 330, 640, 552
s.card(BX, BY, BW2, BH2, fill=CARD, stroke=BORDER_STRONG)
s.band_label(BX + 24, BY + 38, "03 · THE SCOREBOARD")
s.text(BX + 24, BY + 66, "Who calls reroute / hold / do-nothing best - the same exam for every row.",
       12.5, 400, MUTED)

# The caveat lives ON the chart, dashed and unmissable.
s.card(BX + 24, BY + 80, BW2 - 48, 34, fill=CARD_MUTED, stroke=BORDER_STRONG, rx=R, dash="6 5")
s.text(BX + BW2 / 2, BY + 101, "Practice-world scores only. They say nothing about real shipments,"
       " and never appear in the product.", 11.5, 600, MUTED, anchor="middle")


def hbar(x, y, ln, h, fill):
    ln = max(ln, 6)
    s.raw(f'<path d="M{x},{y} h{ln-4} a4,4 0 0 1 4,4 v{h-8} a4,4 0 0 1 -4,4 h-{ln-4} z" fill="{fill}"/>')


PX, PW_ = BX + 24, BW2 - 48          # plot band
ROWS = [
    ("Always say “do nothing”", 84.1, GRAY400,
     "right mostly by luck - most shipments are fine anyway"),
    ("Our rules - before", 65.7, AMBER,
     "acted on 484 shipments the world left alone"),
    ("Our rules - after one question", 76.0, "#9a9a9a",
     "“will the disruption still be there when the ship arrives?”  +10 pts"),
    ("Classic machine learning (GBM)", 88.1, "#9a9a9a", ""),
    ("TabPFN - the model we tested", 89.5, FG,
     "wins all three tasks, with zero tuning"),
]
CY0, PITCH = BY + 140, 56
# recessive grid first, so bars sit on top; the tick row gets its own band
# below the last note so nothing ever collides with it.
for pct in (0, 25, 50, 75, 100):
    gx = PX + PW_ * pct / 100
    s.line(gx, CY0 - 6, gx, CY0 + 4 * PITCH + 58, BORDER)
    s.text(gx, CY0 + 4 * PITCH + 74, f"{pct}%", 9.5, 400, FAINT,
           anchor="middle" if 0 < pct < 100 else ("start" if pct == 0 else "end"), cls="num")
for j, (label, val, col, note) in enumerate(ROWS):
    ry = CY0 + j * PITCH
    s.text(PX, ry + 10, label, 12.5, 600 if col in (FG, AMBER) else 500, FG)
    s.text(PX + PW_, ry + 10, f"{val:.1f}%", 13, 700 if col == FG else 500,
           FG if col != AMBER else AMBER, anchor="end", cls="num")
    hbar(PX, ry + 18, PW_ * val / 100, 14, col)
    if note:
        s.text(PX, ry + 47, note, 10.5, 400, AMBER if col == AMBER else FAINT)

DY_ = CY0 + 4 * PITCH + 88
s.card(BX + 24, DY_, BW2 - 48, 78, fill=SURFACE, stroke="none", rx=R)
s.text(BX + 40, DY_ + 24, "THE ONE-QUESTION FIX, MEASURED", 9.5, 700, FAINT, ls=1.4)
s.raw(f'<text x="{BX+40}" y="{DY_+58}" font-size="26" font-weight="600" fill="{AMBER}" class="num mono">484</text>')
s.line(BX + 106, DY_ + 50, BX + 140, DY_ + 50, FAINT, 1.6, "ahN")
s.raw(f'<text x="{BX+148}" y="{DY_+58}" font-size="26" font-weight="600" fill="{FG}" class="num mono">308</text>')
s.text(BX + 216, DY_ + 44, "false alarms - 176 fewer, from one question.", 11.5, 500, FG)
s.text(BX + 216, DY_ + 62, "The honest cost: 11 real catches lost (218 of 266 still caught).", 11, 400, FAINT)

# =========================================================================
# CARD C - THE REAL-WORLD TEST (step 4)
# =========================================================================
CX, CYY, CW2, CH2 = BX + BW2 + 24, 330, 540, 552
s.card(CX, CYY, CW2, CH2, fill=CARD, stroke=BORDER_STRONG)
s.band_label(CX + 24, CYY + 38, "04 · MEET THE REAL WORLD")
s.text(CX + 24, CYY + 66, "The first-ever full live read, from an ordinary laptop.", 12.5, 400, MUTED)

s.raw(f'<text x="{CX+24}" y="{CYY+116}" font-size="34" font-weight="600" fill="{FG}" '
      f'class="num" letter-spacing="-1">47 of 60</text>')
s.text(CX + 24, CYY + 136, "sources answered on first contact", 11.5, 400, MUTED)

# 60 squares: one per source, counted from the run report.
GX0, GY0, SQ, GAP = CX + 220, CYY + 88, 15, 5
for k in range(60):
    gx = GX0 + (k % 15) * (SQ + GAP)
    gy = GY0 + (k // 15) * (SQ + GAP)
    if k < 47:
        fill, stroke = GREEN_BG, GREEN
    elif k < 58:
        fill, stroke = SURFACE_2, BORDER_STRONG
    else:
        fill, stroke = AMBER_BG, AMBER
    s.raw(f'<rect x="{gx}" y="{gy}" width="{SQ}" height="{SQ}" rx="3" '
          f'fill="{fill}" stroke="{stroke}"/>')
LEG = [(GREEN_BG, GREEN, "47 answered"),
       (SURFACE_2, BORDER_STRONG, "11 = one blocked news service, all its queries (laptop-side)"),
       (AMBER_BG, AMBER, "2 dead links - replaced the same day")]
for j, (fill, stroke, lab) in enumerate(LEG):
    ly = CYY + 176 + j * 18
    s.raw(f'<rect x="{CX+24}" y="{ly-10}" width="12" height="12" rx="3" fill="{fill}" stroke="{stroke}"/>')
    s.text(CX + 44, ly, lab, 10.5, 400, MUTED)

s.line(CX + 24, CYY + 242, CX + CW2 - 24, CYY + 242, BORDER)
s.text(CX + 24, CYY + 268, "What running it for real caught - no rehearsal could:", 12.5, 500, FG)

FIND = [
    ("Cried wolf", "a dry map cell read “river critically low”.", "Zero is now “no reading”, never an alarm.", "FIXED"),
    ("3 services said no", "request wording only real servers reject.", "Rewritten to the letter of their specs.", "FIXED"),
    ("False caption", "a gauge quoted a threshold it never crossed.", "Events now quote the line they crossed.", "FIXED"),
    ("2 dead feeds", "links had rotted since they were wired.", "Replaced; backup readers held meanwhile.", "FIXED"),
    ("1 blocked service", "unreachable from this laptop only.", "Run degraded cleanly; diagnosis pending.", "OPEN"),
]
for j, (t, what, fix, tag) in enumerate(FIND):
    fy = CYY + 288 + j * 38
    open_ = tag == "OPEN"
    s.chip(CX + 24, fy, 46, 17, tag, fs=8, fill=AMBER_BG if open_ else GREEN_BG,
           col=AMBER if open_ else GREEN, weight=700)
    s.text(CX + 80, fy + 12, f"{t} - {what}", 11.5, 500, FG)
    s.text(CX + 80, fy + 28, fix, 10.5, 400, FAINT)

uy = CYY + 486
s.card(CX + 24, uy, CW2 - 48, 44, fill=GREEN_BG, stroke=GREEN, rx=R)
s.text(CX + 40, uy + 18, "Unscripted, during the test:", 10.5, 700, GREEN)
s.text(CX + 40, uy + 34, "Hamburg's own broadcaster carried a real Hamburg closure - the pitch, live.",
       10.5, 400, GREEN)

# =========================================================================
s.text(M, 940, "Witnessed live, measurably smarter - and the best model already picked out.",
       24, 600, FG, ls=-0.5)
s.text(W - M, 940, "All figures counted from our own runs · full record: LAB-NOTES-2026-08-28.md",
       12, 400, FAINT, anchor="end")
s.footer("A1 / LAB NOTES")
s.write("slide-a1-lab-notes.svg")
