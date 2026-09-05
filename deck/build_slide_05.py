#!/usr/bin/env python3
"""
Slide 05 - THE JOB (2/2).  Emits deck/slide-05-the-job-2.svg.

Pairs with slide 04. Where 04 argued the cost of an ordinary file, this one
argues that "ordinary" is already unreliable: on one real corridor, six
independent things can knock a sailing late at once, and on current schedule
reliability roughly every other one does. The margin arithmetic from 04
(€127 per clean box) is reused here to show what one bad day costs against it.

  top     the corridor itself, mid-2025 schedule reliability, what erodes it
  bottom  who eats which part of the cost, and the arithmetic once it lands
          on the forwarder's own book

Map geometry is the product's own (data/geo.json, static/index.html's COAST
constant) - the same reuse slide 07's map already relies on.
"""
from deckkit import *
import json, re

_H = (ROOT / "static" / "index.html").read_text()
COAST = re.search(r'const COAST\s*=\s*"([^"]+)"', _H).group(1)
GEO = json.loads((ROOT / "data" / "geo.json").read_text())
FR = GEO["_frame"]


def proj(lat, lon):
    x = (lon - FR["lon0"]) / (FR["lon1"] - FR["lon0"]) * FR["width"]
    y = (FR["lat1"] - lat) / (FR["lat1"] - FR["lat0"]) * FR["height"]
    return x, y

s = Slide()
s.header("05 — THE JOB (2/2)",
         "Forty-seven sailings in a hundred arrive late.",
         "So the question is not whether a lane breaks. It is who pays for it when it does, and how often.")

TY, TH = 216, 470

# =========================================================================
# ONE LANE, SIX PLACES IT CAN BREAK - the map
# =========================================================================
MX, MW = M, 800
LON0, LON1, LAT0, LAT1 = -25.0, 38.4, 26.0, 59.5
_x0, _y0 = proj(LAT1, LON0)
_x1, _y1 = proj(LAT0, LON1)
SC = MW / (_x1 - _x0)
# The frame's full lat range at this width needs ~400px of vertical room
# (checked against data/geo.json's _frame) - the clip below must be at
# least that tall or a southerly point (Suez) projects below it and its
# label floats, unclipped, over whatever the next card draws.
MCLIP_H = TH - 60

s.card(MX, TY, MW, TH, fill="#f7f9fb", stroke=BORDER_STRONG)
s.text(MX + 20, TY + 30, "ONE LANE, SIX PLACES IT CAN BREAK", 10, 700, AMBER, ls=1.3)
s.text(MX + MW - 16, TY + 30, "geometry from data/geo.json", 9.5, 400, FAINT, anchor="end")
s.raw(f'<clipPath id="mclip5"><rect x="{MX}" y="{TY+40}" width="{MW}" height="{MCLIP_H}" rx="8"/></clipPath>')
s.raw(f'<g clip-path="url(#mclip5)">'
      f'<g transform="translate({MX - _x0*SC:.1f},{TY+40 - _y0*SC:.1f}) scale({SC:.4f})">'
      f'<path d="{COAST}" fill="#e8ecef" stroke="#d3d9de" stroke-width="0.7"/></g></g>')


def mp(lat, lon):
    x, y = proj(lat, lon)
    return MX + (x - _x0) * SC, TY + 40 + (y - _y0) * SC


s.raw('<g clip-path="url(#mclip5)">')
for name in ("redsea_to_suez", "suez_to_gibraltar", "suez_to_fos", "gibraltar_to_northsea"):
    pts = [mp(la, lo) for la, lo in GEO["corridors"][name]]
    d = " ".join(f"{'M' if i==0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(pts))
    s.raw(f'<path d="{d}" fill="none" stroke="{AMBER}" stroke-width="1.6" '
          f'stroke-linecap="round" opacity="0.55"/>')
s.raw('</g>')

s.raw('<g clip-path="url(#mclip5)">')
BREAKS = [("RTM", "Rotterdam", "congestion", -10, -9, "end"),
          ("HAM", "Hamburg", "labour", 10, -8, "start"),
          ("ANR", "Antwerp", "congestion", -10, 15, "end"),
          ("RHINE", "Rhine", "low water", 11, 14, "start"),
          ("FOS", "Fos", "labour", 10, 13, "start"),
          ("SUEZ", "Suez", "conflict routing", -10, -8, "end")]
for pid, lab, why, dx, dy, anc in BREAKS:
    p = GEO["places"][pid]
    x, y = mp(p["lat"], p["lon"])
    s.raw(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{AMBER}"/>')
    s.text(x + dx, y + dy, lab, 10.5, 600, FG, anchor=anc)
    s.text(x + dx, y + dy + 14, why, 9.5, 400, AMBER, anchor=anc)
s.raw('</g>')
s.text(MX + 20, TY + TH - 16, "None of these is unusual. All of them are on this one route.", 12, 400, MUTED)

# =========================================================================
# A HUNDRED SAILINGS - the pictogram
# =========================================================================
PX_, PW_ = MX + MW + 32, 460
s.card(PX_, TY, PW_, TH)
s.text(PX_ + 24, TY + 30, "A HUNDRED SAILINGS", 10, 700, FAINT, ls=1.4)
GX0, GY0, CELL, GAP = PX_ + 24, TY + 52, 26, 4.5
for i in range(100):
    r, c = divmod(i, 10)
    late = i < 47
    s.raw(f'<rect x="{GX0+c*(CELL+GAP):.0f}" y="{GY0+r*(CELL+GAP):.0f}" width="{CELL}" height="{CELL}" '
          f'rx="4" fill="{AMBER if late else SURFACE}"/>')
LEGY = GY0 + 10 * (CELL + GAP) + 14
s.raw(f'<rect x="{GX0}" y="{LEGY-11}" width="12" height="12" rx="3" fill="{AMBER}"/>')
s.text(GX0 + 20, LEGY, "47 late", 12, 600, FG)
s.raw(f'<rect x="{GX0+120}" y="{LEGY-11}" width="12" height="12" rx="3" fill="{SURFACE}"/>')
s.text(GX0 + 140, LEGY, "53 on time", 12, 600, FG)
s.text(PX_ + 24, TY + TH - 34, "Schedule reliability, mid-2025.", 12, 400, MUTED)
s.text(PX_ + 24, TY + TH - 16, "It was 75-80% before 2020.", 12, 400, MUTED)

# =========================================================================
# WHAT EATS IT
# =========================================================================
EX = PX_ + PW_ + 32
EW = W - M - EX
s.card(EX, TY, EW, TH)
s.text(EX + 24, TY + 30, "WHAT EATS IT", 10, 700, FAINT, ls=1.4)
EATS = [("6–9%", "of global capacity pulled", "blank sailings and reroutes"),
        ("7–10d", "added when a box is rolled", "to the next vessel with space"),
        ("2.4×", "swing in the spot rate", "$1,913 → $4,526 per 40ft"),
        ("€185", "a day once it sits at the port", "against €127 of margin")]
for i, (big, line, sub) in enumerate(EATS):
    y = TY + 62 + i * 68
    s.raw(f'<text x="{EX+24}" y="{y}" font-size="24" font-weight="600" fill="{AMBER}" '
          f'letter-spacing="-0.6" class="num">{esc(big)}</text>')
    s.text(EX + 24, y + 20, line, 11.5, 500, FG)
    s.text(EX + 24, y + 37, sub, 10.5, 400, FAINT)
s.line(EX + 24, TY + TH - 30, EX + EW - 24, TY + TH - 30, BORDER)
s.text(EX + 24, TY + TH - 12, "Every figure published, all 2025.", 10.5, 400, FAINT)

# =========================================================================
# WHO OWNS WHICH COST  /  SO SHOULD A FORWARDER CARE
# =========================================================================
BY2, BH2 = TY + TH + 24, 240
BW2 = (CW - 32) / 2
BX1, BX2 = M, M + BW2 + 32

s.card(BX1, BY2, BW2, BH2)
b1x = BX1 + 28
s.text(b1x, BY2 + 34, "WHO OWNS WHICH COST", 10, 700, FAINT, ls=1.4)
colw = (BW2 - 56) / 2
s.text(b1x, BY2 + 64, "THE CUSTOMER", 11, 700, MUTED, ls=1)
s.text(b1x + colw, BY2 + 64, "THE FORWARDER", 11, 700, AMBER, ls=1)
CUST = ["The carrier's surcharge", "The higher freight rate", "The later arrival date"]
FWD = ["Storage while the box waits", "Re-booking and paperwork",
       "Clearing into a new country", "Every hour spent chasing it"]
for i, t in enumerate(CUST):
    y = BY2 + 92 + i * 26
    s.raw(f'<circle cx="{b1x+3}" cy="{y-4}" r="3" fill="{GRAY400}"/>')
    s.text(b1x + 16, y, t, 12, 400, MUTED)
for i, t in enumerate(FWD):
    y = BY2 + 92 + i * 26
    xx = b1x + colw
    s.raw(f'<circle cx="{xx+3}" cy="{y-4}" r="3" fill="{AMBER}"/>')
    s.text(xx + 16, y, t, 12, 400, FG)
s.line(b1x, BY2 + BH2 - 54, BX1 + BW2 - 28, BY2 + BH2 - 54, BORDER)
s.text(b1x, BY2 + BH2 - 32, "Which side a line falls on is the contract.", 12.5, 400, MUTED)
s.text(b1x, BY2 + BH2 - 14, "The forwarder argues it afterwards, on their own time.", 12.5, 400, MUTED)

s.card(BX2, BY2, BW2, BH2, fill=FG, stroke="none")
b2x = BX2 + 28
s.text(b2x, BY2 + 34, "SO SHOULD A FORWARDER CARE", 10, 700, "#c9c9c9", ls=1.4)
CARE = [("Margin on a clean box", "+€127", "#e5e5e5"),
        ("One day the box sits at the port", "-€185", "#f0b03a"),
        ("Five days sitting", "-€926", "#f0b03a")]
for i, (lab, val, col) in enumerate(CARE):
    y = BY2 + 70 + i * 30
    s.text(b2x, y, lab, 13, 400, "#c9c9c9")
    s.raw(f'<text x="{BX2+BW2-28}" y="{y}" font-size="17" font-weight="600" fill="{col}" '
          f'text-anchor="end" class="num">{val}</text>')
s.line(b2x, BY2 + 70 + 2 * 30 + 16, BX2 + BW2 - 28, BY2 + 70 + 2 * 30 + 16, "#3a3a3a")
s.text(b2x, BY2 + BH2 - 40, "One bad day undoes seven clean ones.", 15, 600, CARD)
s.text(b2x, BY2 + BH2 - 16, "And on current reliability, roughly every other sailing is one.",
       11.5, 400, "#9a9a9a")

# =========================================================================
s.text(M, BY2 + BH2 + 40, "It is not an edge case. It is the whole job.", 24, 600, FG, ls=-0.5)
s.footer("05 / THE JOB 2/2")
s.write("slide-05-the-job-2.svg")
