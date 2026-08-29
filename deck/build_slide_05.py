#!/usr/bin/env python3
"""
Slide 05 - THE JOB (2/2).  Emits deck/slide-05-when-it-breaks.svg.

Rebuilt. Answers "should a forwarder actually care", and the answer turns on
frequency, not severity.

  map          the lane, and what each place on it is exposed to
  47 in 100    schedule reliability drawn as a hundred sailings, so half the
               board being late is something you see rather than read
  eaters       four published figures that move the margin
  incidence    who owns which cost, and the honest note that it is contractual
  verdict      the subtraction, on a dark panel

Coastline is read at build time from static/index.html; lanes and ports from
data/geo.json, so the deck and the dashboard cannot drift apart.
"""
from deckkit import *
import json, re

GREEN = "#0f7b3f"
_H = (ROOT / "static" / "index.html").read_text()
COAST = re.search(r'const COAST\s*=\s*"([^"]+)"', _H).group(1)
GEO = json.loads((ROOT / "data" / "geo.json").read_text())
FR = GEO["_frame"]


def proj(lat, lon):
    return ((lon - FR["lon0"]) / (FR["lon1"] - FR["lon0"]) * FR["width"],
            (FR["lat1"] - lat) / (FR["lat1"] - FR["lat0"]) * FR["height"])


s = Slide()
s.header("05 — THE JOB (2/2)",
         "Forty-seven sailings in a hundred arrive late.",
         "So the question is not whether a lane breaks. It is who pays when it does, and how often.")

TOP = 222

# =========================================================================
# THE LANE, AND WHAT EACH PLACE IS EXPOSED TO
# =========================================================================
MX, MW, MH = M, 760, 336
LON0, LON1, LAT0, LAT1 = -22.0, 51.6, 26.0, 58.0
_x0, _y0 = proj(LAT1, LON0)
_x1, _y1 = proj(LAT0, LON1)
SC = MW / (_x1 - _x0)
s.card(MX, TOP, MW, MH, fill="#f7f9fb", stroke=BORDER_STRONG)
s.raw(f'<clipPath id="mclip"><rect x="{MX}" y="{TOP}" width="{MW}" height="{MH}" rx="{RMD}"/></clipPath>')
s.raw(f'<g clip-path="url(#mclip)"><g transform="translate({MX - _x0*SC:.1f},{TOP - _y0*SC:.1f}) '
      f'scale({SC:.4f})"><path d="{COAST}" fill="#e8ecef" stroke="#d3d9de" stroke-width="0.7"/></g></g>')


def mp(lat, lon):
    x, y = proj(lat, lon)
    return MX + (x - _x0) * SC, TOP + (y - _y0) * SC


s.raw('<g clip-path="url(#mclip)">')
for name in ("redsea_to_suez", "suez_to_gibraltar", "suez_to_fos", "gibraltar_to_northsea"):
    pts = [mp(la, lo) for la, lo in GEO["corridors"][name]]
    d = " ".join(f"{'M' if i==0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(pts))
    s.raw(f'<path d="{d}" fill="none" stroke="{AMBER}" stroke-width="2" opacity="0.5"/>')
s.raw('</g>')
PINS = [("HAM", "Hamburg", "labour", 12, -9, "start"), ("RTM", "Rotterdam", "congestion", -12, -10, "end"),
        ("ANR", "Antwerp", "congestion", -12, 20, "end"), ("RHINE", "Rhine", "low water", 13, 16, "start"),
        ("FOS", "Fos", "labour", 12, 14, "start"), ("SUEZ", "Suez", "conflict routing", -12, -9, "end")]
for pid, lab, risk, dx, dy, anc in PINS:
    p = GEO["places"][pid]
    x, y = mp(p["lat"], p["lon"])
    s.raw(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{AMBER}" stroke="{CARD}" stroke-width="1.6"/>')
    s.text(x + dx, y + dy, lab, 11, 600, FG, anchor=anc)
    s.text(x + dx, y + dy + 14, risk, 10, 400, AMBER, anchor=anc)
s.text(MX + 22, TOP + 34, "ONE LANE, SIX PLACES IT CAN BREAK", 10, 700, AMBER, ls=1.4)
s.text(MX + MW - 18, TOP + 34, "geometry from data/geo.json", 9.5, 400, FAINT, anchor="end")
s.text(MX + 22, TOP + MH - 22, "None of these is unusual. All of them are on this one route.",
       12.5, 500, FG)

# =========================================================================
# 47 IN 100
# =========================================================================
DX2, DW2 = 880, 440
s.card(DX2, TOP, DW2, MH, stroke=BORDER_STRONG)
s.text(DX2 + 24, TOP + 34, "A HUNDRED SAILINGS", 10, 700, FAINT, ls=1.4)
CELL, GAPC = 16, 4
GX0, GY0 = DX2 + 24, TOP + 64
for i in range(100):
    r, c = divmod(i, 10)
    late = i < 47
    s.raw(f'<rect x="{GX0 + c*(CELL+GAPC)}" y="{GY0 + r*(CELL+GAPC)}" width="{CELL}" '
          f'height="{CELL}" rx="4" fill="{AMBER if late else SURFACE_2}"/>')
LGX = GX0 + 10 * (CELL + GAPC) + 26
s.raw(f'<rect x="{LGX}" y="{GY0+70}" width="13" height="13" rx="3" fill="{AMBER}"/>')
s.text(LGX + 22, GY0 + 81, "47 late", 13, 600, FG)
s.raw(f'<rect x="{LGX}" y="{GY0+104}" width="13" height="13" rx="3" fill="{SURFACE_2}"/>')
s.text(LGX + 22, GY0 + 115, "53 on time", 13, 400, MUTED)
s.text(GX0, GY0 + 232, "Schedule reliability, mid-2025.", 12.5, 500, FG)
s.text(GX0, GY0 + 250, "It was 75–80% before 2020.", 12.5, 400, MUTED)

# =========================================================================
# WHAT EATS THE MARGIN
# =========================================================================
EX, EW = 1344, W - M - 1344
s.card(EX, TOP, EW, MH)
s.text(EX + 24, TOP + 34, "WHAT EATS IT", 10, 700, FAINT, ls=1.4)
EAT = [("6–9%", "of global capacity pulled", "blank sailings and reroutes"),
       ("7–10d", "added when a box is rolled", "to the next vessel with space"),
       ("2.4×", "swing in the spot rate", "$1,913 → $4,526 per 40ft"),
       ("€185", "a day once it sits at the port", "against €127 of margin")]
for j, (big, line, sub) in enumerate(EAT):
    y = TOP + 80 + j * 60
    s.raw(f'<text x="{EX+24}" y="{y}" font-size="21" font-weight="600" fill="{AMBER}" '
          f'letter-spacing="-0.8" class="num">{esc(big)}</text>')
    s.text(EX + 24, y + 20, line, 12.5, 500, FG)
    s.text(EX + 24, y + 36, sub, 11, 400, FAINT)
    if j < 3:
        s.line(EX + 24, y + 46, EX + EW - 24, y + 46, BORDER)
s.text(EX + 24, TOP + MH - 18, "Every figure published, all 2025.", 11, 400, FAINT, cls="mono")

# =========================================================================
# WHO OWNS WHICH COST
# =========================================================================
RY, RH = 600, 286
s.card(M, RY, 830, RH)
s.text(M + 26, RY + 34, "WHO OWNS WHICH COST", 10, 700, FAINT, ls=1.4)
for lab, x0, col in (("THE CUSTOMER", M + 26, MUTED), ("THE FORWARDER", M + 424, AMBER)):
    s.text(x0, RY + 68, lab, 9.5, 700, col, ls=1.2)
for j, it in enumerate(["The carrier's surcharge", "The higher freight rate", "The later arrival date"]):
    y = RY + 102 + j * 28
    s.raw(f'<circle cx="{M+30}" cy="{y-4}" r="3" fill="none" stroke="{GRAY400}" stroke-width="1.3"/>')
    s.text(M + 44, y, it, 12.5, 400, MUTED)
for j, it in enumerate(["Storage while the box waits", "Re-booking and paperwork",
                        "Clearing into a new country", "Every hour spent chasing it"]):
    y = RY + 102 + j * 28
    s.raw(f'<circle cx="{M+428}" cy="{y-4}" r="3" fill="{AMBER}"/>')
    s.text(M + 442, y, it, 12.5, 500, FG)
s.line(M + 404, RY + 54, M + 404, RY + RH - 72, BORDER)
s.line(M + 26, RY + RH - 60, M + 830 - 26, RY + RH - 60, BORDER)
s.text(M + 26, RY + RH - 34, "Which side a line falls on is the contract.", 13, 500, FG)
s.text(M + 26, RY + RH - 14, "The forwarder argues it afterwards, on their own time.", 13, 400, MUTED)

# =========================================================================
# THE VERDICT
# =========================================================================
VX, VW = 950, W - M - 950
s.card(VX, RY, VW, RH, fill=FG, stroke="none")
s.text(VX + 28, RY + 36, "SO SHOULD A FORWARDER CARE", 10, 700, "#8f8f8f", ls=1.4)
for j, (lab, val, col) in enumerate((("Margin on a clean box", "+€127", "#a1a1a1"),
                                     ("One day the box sits at the port", "−€185", "#f5a623"),
                                     ("Five days sitting", "−€926", "#f5a623"))):
    y = RY + 84 + j * 34
    s.text(VX + 28, y, lab, 13.5, 500, CARD)
    s.raw(f'<text x="{VX+VW-28}" y="{y}" font-size="19" font-weight="600" fill="{col}" '
          f'text-anchor="end" class="num">{esc(val)}</text>')
s.line(VX + 28, RY + 206, VX + VW - 28, RY + 206, "#333")
s.text(VX + 28, RY + 240, "One bad day undoes seven clean ones.", 21, 600, CARD, ls=-0.4)
s.text(VX + 28, RY + 264, "And on current reliability, roughly every other sailing is one.",
       12.5, 400, "#a1a1a1")

s.text(M, 916, "It is not an edge case. It is the business.", 24, 600, FG, ls=-0.5)
s.footer("05 / THE JOB 2/2")
s.write("slide-05-when-it-breaks.svg")
