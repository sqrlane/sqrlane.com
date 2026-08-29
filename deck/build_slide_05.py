#!/usr/bin/env python3
"""
Slide 05 - THE JOB (2/2).  Emits deck/slide-05-when-it-breaks.svg.

The answer to "should a forwarder actually care about this".

The hinge is schedule reliability. At ~53% roughly half of all sailings are
late, so a broken lane is not a tail risk a desk can absorb - it is the median
week. Set that against EUR 127 of margin per box from 04 and the question
answers itself.

  map        where the lanes and the chokepoints are, from the product's own
             geo data, so the deck and the dashboard cannot drift apart
  eaters     four published figures that move a forwarder's margin
  incidence  who owns which cost, and the honest note that it is contractual
  verdict    the cost-benefit, in one subtraction

Coastline is read at build time from static/index.html; lanes and ports from
data/geo.json.
"""
from deckkit import *
import json, re

GREEN, RED_BG = "#0f7b3f", "#feecec"
_H = (ROOT / "static" / "index.html").read_text()
COAST = re.search(r'const COAST\s*=\s*"([^"]+)"', _H).group(1)
GEO = json.loads((ROOT / "data" / "geo.json").read_text())
FR = GEO["_frame"]


def proj(lat, lon):
    return ((lon - FR["lon0"]) / (FR["lon1"] - FR["lon0"]) * FR["width"],
            (FR["lat1"] - lat) / (FR["lat1"] - FR["lat0"]) * FR["height"])


s = Slide()
s.header("05 — THE JOB (2/2)",
         "Half of all sailings are late. This is the median, not the tail.",
         "So the question is not whether a lane breaks. It is who pays when it does, and how often.")

TOP = 224

# =========================================================================
# THE MAP
# =========================================================================
MX, MW, MH = M, 700, 300
LON0, LON1, LAT0, LAT1 = -22.0, 40.0, 26.0, 58.0
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
    s.raw(f'<path d="{d}" fill="none" stroke="{AMBER}" stroke-width="1.8" opacity="0.5"/>')
s.raw('</g>')
for pid, lab, dx, dy, anc in (("HAM", "Hamburg", 10, -8, "start"), ("RTM", "Rotterdam", -10, -9, "end"),
                              ("ANR", "Antwerp", -10, 15, "end"), ("RHINE", "Rhine", 11, 14, "start"),
                              ("FOS", "Fos", 10, 13, "start"), ("SUEZ", "Suez", -10, -8, "end")):
    p = GEO["places"][pid]
    x, y = mp(p["lat"], p["lon"])
    s.raw(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{AMBER}" stroke="{CARD}" stroke-width="1.4"/>')
    s.text(x + dx, y + dy, lab, 10.5, 600, FG, anchor=anc)
s.text(MX + 20, TOP + 34, "ONE LANE, SIX PLACES IT CAN BREAK", 10, 700, AMBER, ls=1.4)
s.card(MX + 16, TOP + MH - 50, 276, 34, fill=CARD, stroke=BORDER, rx=R)
s.text(MX + 32, TOP + MH - 28, "A strike, low water, a closure, a queue.", 11.5, 500, FG)
s.text(MX + MW - 16, TOP + 34, "geometry from data/geo.json", 9.5, 400, FAINT, anchor="end")

# =========================================================================
# WHAT EATS THE MARGIN
# =========================================================================
EX, EW = 852, W - M - 852
s.card(EX, TOP, EW, MH, stroke=BORDER_STRONG)
s.text(EX + 26, TOP + 34, "WHAT EATS THE MARGIN", 10, 700, FAINT, ls=1.4)
s.text(EX + EW - 26, TOP + 34, "all published, all 2025", 10.5, 400, FAINT, anchor="end")
EAT = [("53%", "of sailings arrive on time", "was 75–80% before 2020", "Sea-Intelligence, mid-2025"),
       ("6–9%", "of global capacity pulled", "blank sailings and reroutes", "carrier programmes, 2025"),
       ("7–10d", "added when a box is rolled", "to the next vessel with space", "industry reporting, 2025"),
       ("2.4×", "swing in the spot rate", "$1,913 → $4,526 per 40ft", "Drewry WCI, Sep 25 to Aug 26")]
for j, (big, line, sub, src) in enumerate(EAT):
    y = TOP + 76 + j * 54
    s.raw(f'<text x="{EX+26}" y="{y+6}" font-size="26" font-weight="600" fill="{AMBER}" '
          f'letter-spacing="-0.7" class="num">{esc(big)}</text>')
    s.text(EX + 130, y, line, 13.5, 500, FG)
    s.text(EX + 130, y + 18, sub, 11.5, 400, MUTED)
    s.text(EX + EW - 26, y, src, 10, 400, FAINT, anchor="end", cls="mono")
    if j < 3:
        s.line(EX + 26, y + 32, EX + EW - 26, y + 32, BORDER)

# =========================================================================
# WHO OWNS THE RISK
# =========================================================================
RY, RH = 552, 268
s.card(M, RY, 830, RH)
s.text(M + 26, RY + 34, "WHO OWNS WHICH COST", 10, 700, FAINT, ls=1.4)
for lab, x0, col in (("THE CUSTOMER", M + 26, MUTED), ("THE FORWARDER", M + 424, AMBER)):
    s.text(x0, RY + 66, lab, 9.5, 700, col, ls=1.2)
for j, it in enumerate(["The carrier's surcharge", "The higher freight rate", "The later arrival date"]):
    y = RY + 98 + j * 28
    s.raw(f'<circle cx="{M+30}" cy="{y-4}" r="3" fill="none" stroke="{GRAY400}" stroke-width="1.3"/>')
    s.text(M + 44, y, it, 12.5, 400, MUTED)
for j, it in enumerate(["Storage while the box waits", "Re-booking and paperwork",
                        "Clearing into a new country", "Every hour spent chasing it"]):
    y = RY + 98 + j * 28
    s.raw(f'<circle cx="{M+428}" cy="{y-4}" r="3" fill="{AMBER}"/>')
    s.text(M + 442, y, it, 12.5, 500, FG)
s.line(M + 404, RY + 50, M + 404, RY + RH - 74, BORDER)
s.line(M + 26, RY + RH - 62, M + 830 - 26, RY + RH - 62, BORDER)
s.text(M + 26, RY + RH - 36, "Which side a line falls on is the contract.", 13, 500, FG)
s.text(M + 26, RY + RH - 16, "The forwarder argues it afterwards, on their own time.", 13, 400, MUTED)

# =========================================================================
# SO SHOULD THEY CARE
# =========================================================================
s.card(EX, RY, EW, RH, fill=FG, stroke="none")
s.text(EX + 26, RY + 36, "SO SHOULD A FORWARDER CARE", 10, 700, "#8f8f8f", ls=1.4)
ROWS = [("Margin on a clean box", "+€127", "#a1a1a1"),
        ("One day the box sits at the port", "−€185", "#f5a623"),
        ("Five days sitting", "−€926", "#f5a623")]
for j, (lab, val, col) in enumerate(ROWS):
    y = RY + 76 + j * 34
    s.text(EX + 26, y, lab, 13.5, 500, CARD)
    s.raw(f'<text x="{EX+EW-26}" y="{y}" font-size="19" font-weight="600" fill="{col}" '
          f'text-anchor="end" class="num">{esc(val)}</text>')
s.line(EX + 26, RY + 194, EX + EW - 26, RY + 194, "#333")
s.text(EX + 26, RY + 226, "One bad day undoes seven clean ones.", 21, 600, CARD, ls=-0.4)
s.text(EX + 26, RY + 250, "And on current reliability, roughly every other sailing is one.",
       12.5, 400, "#a1a1a1")

s.text(M, 878, "It is not an edge case. It is the business.", 24, 600, FG, ls=-0.5)
s.footer("05 / THE JOB 2/2")
s.write("slide-05-when-it-breaks.svg")
