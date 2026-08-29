#!/usr/bin/env python3
"""
Slide 06 - THE HOW (2/2).  Emits deck/slide-06-the-how-2.svg.

Answers problem two from slide 02: nothing watches the route.

  left    what the warning is worth by when it arrives, stacked
  top     signals feeding one confidence read, and the line it crosses
  bottom  the app, mid-run: the agents working, and the recommendation

Deliberately no mid-ocean reroute. A box already on the water has almost no
options, so the value is that knowing earlier moves the decision into a window
where options still exist.

The confidence grid shows the mechanism, not a measured accuracy, and says so.
"""
from deckkit import *
import json, re

# The coastline the product itself draws, reused verbatim so the deck's map and
# the dashboard's map are the same geometry rather than two hand-drawn guesses.
_H = (ROOT / "static" / "index.html").read_text()
COAST = re.search(r'const COAST\s*=\s*"([^"]+)"', _H).group(1)
GEO = json.loads((ROOT / "data" / "geo.json").read_text())
FR = GEO["_frame"]


def proj(lat, lon):
    x = (lon - FR["lon0"]) / (FR["lon1"] - FR["lon0"]) * FR["width"]
    y = (FR["lat1"] - lat) / (FR["lat1"] - FR["lat0"]) * FR["height"]
    return x, y

GREEN, GREEN_BG = "#0f7b3f", "#e7f5ec"
BLUE, BLUE_BG = "#006bff", "#e8f1ff"
HEAT = ["#f2f2f2", "#fdf3e3", "#f6dfb4", "#d9a441", "#96580a"]

s = Slide()
s.header("06 — THE HOW (2/2)",
         "Know early enough that you still have options.",
         "Many signals, one confidence read. The earlier it fires, the cheaper the answer.")

# =========================================================================
# LEFT - what the warning is worth, by when it arrives
# =========================================================================
LX, LW = M, 320
s.text(LX, 216, "WORTH, BY WHEN IT ARRIVES", 10, 700, FAINT, ls=1.4)
WINDOWS = [("NOT YET BOOKED", "Route around it.", "many", 5, AMBER, AMBER_BG, AMBER),
           ("BOOKED, NOT SAILED", "Amend while it is cheap.", "some", 2, FG, SURFACE, BORDER_STRONG),
           ("ALREADY IN TRANSIT", "Prepare. Do not reroute.", "few", 1, MUTED, CARD, BORDER_STRONG)]
for i, (label, head, opts, n, col, bg, stroke) in enumerate(WINDOWS):
    y = 228 + i * 208
    s.card(LX, y, LW, 190, fill=bg, stroke=stroke)
    s.text(LX + 24, y + 34, label, 9.5, 700, col, ls=1.3)
    s.text(LX + 24, y + 76, head.split(" ", 1)[0], 21, 600, FG, ls=-0.4)
    s.text(LX + 24, y + 102, head.split(" ", 1)[1] if " " in head else "", 21, 600, FG, ls=-0.4)
    s.line(LX + 24, y + 128, LX + LW - 24, y + 128, BORDER)
    s.text(LX + 24, y + 160, opts, 20, 600, col)
    s.text(LX + 24, y + 176, "options", 10.5, 400, FAINT)
    for k in range(5):
        s.raw(f'<rect x="{LX + LW - 24 - (5-k)*22}" y="{y+148}" width="15" height="15" rx="3" '
              f'fill="{col if k < n else GRAY400}"/>')

# =========================================================================
# TOP RIGHT - signals and the confidence read
# =========================================================================
TOP = 228
SX, SW, SH = 444, 220, 250
s.card(SX, TOP, SW, SH)
sx = SX + 20
s.text(sx, TOP + 32, "SIGNALS", 10, 700, FAINT, ls=1.4)
FAMS = [("News & wires", 1), ("Weather & sea state", 1), ("River gauges", 1),
        ("Seismic & hazards", 1), ("Government filings", 1), ("Reference rates", 1),
        ("Prediction markets", 0), ("AIS & port calls", 0), ("Freight indices", 0)]
for j, (fam, live) in enumerate(FAMS):
    y = TOP + 56 + j * 18
    s.raw(f'<circle cx="{sx+4}" cy="{y-4}" r="3" fill="{GREEN if live else "none"}" '
          f'stroke="{GRAY400}" stroke-width="{0 if live else 1.2}"/>')
    s.text(sx + 16, y, fam, 11, 500 if live else 400, FG if live else FAINT)
s.text(sx, TOP + 232, "42 live. Rest is phase two.", 10, 400, FAINT)

HX, HW = 684, 620
s.card(HX, TOP, HW, SH, stroke=BORDER_STRONG)
hx = HX + 22
s.text(hx, TOP + 32, "CONFIDENCE, BUILDING", 10, 700, AMBER, ls=1.4)
s.text(HX + HW - 22, TOP + 32, "mechanism, not accuracy", 10, 400, FAINT, anchor="end")
VARS = [("Union ballot", [0, 0, 1, 1, 2, 3, 3, 4, 4, 4]),
        ("Berth waiting", [0, 0, 0, 1, 1, 1, 2, 3, 4, 4]),
        ("Throughput", [0, 1, 0, 1, 1, 2, 2, 3, 3, 4]),
        ("Rail slots", [0, 0, 0, 0, 1, 1, 2, 2, 3, 4]),
        ("Prediction mkt", [0, 0, 1, 1, 2, 2, 3, 4, 4, 4]),
        ("Wire volume", [0, 0, 0, 0, 0, 1, 1, 2, 3, 4])]
GX, CELL, GAP = hx + 96, 44, 4
for r, (name, row) in enumerate(VARS):
    y = TOP + 54 + r * 19
    s.text(hx, y + 10, name, 10.5, 400, MUTED)
    for c, v in enumerate(row):
        s.raw(f'<rect x="{GX + c*(CELL+GAP)}" y="{y}" width="{CELL}" height="14" rx="3" fill="{HEAT[v]}"/>')
for c, lab in enumerate(["T-9", "", "T-7", "", "T-5", "", "T-3", "", "T-1", "T-0"]):
    if lab:
        s.text(GX + c * (CELL + GAP) + CELL / 2, TOP + 182, lab, 9, 400, FAINT, anchor="middle", cls="mono")
CONF = [5, 8, 14, 20, 31, 42, 55, 68, 81, 92]
BASE, HGT = TOP + 232, 40
s.text(hx, BASE - 14, "confidence", 11, 500, FG)
for c, v in enumerate(CONF):
    h = HGT * v / 100
    s.raw(f'<rect x="{GX + c*(CELL+GAP)}" y="{BASE-h:.0f}" width="{CELL}" height="{h:.0f}" '
          f'rx="2" fill="{AMBER if v >= 70 else GRAY400}"/>')
ty = BASE - HGT * 0.70
s.line(GX - 8, ty, GX + 10 * (CELL + GAP) - GAP + 8, ty, AMBER, 1.4, dash="4 4")
s.text(GX - 12, ty + 4, "trigger", 10, 600, AMBER, anchor="end")

# =========================================================================
# THE LANES, ON A MAP - Europe and the approaches it is reached through
# =========================================================================
MX, MW, MH = 1324, W - M - 1324, SH
LON0, LON1, LAT0, LAT1 = -25.0, 38.4, 26.0, 59.5
_x0, _y0 = proj(LAT1, LON0)
_x1, _y1 = proj(LAT0, LON1)
SC = MW / (_x1 - _x0)

s.card(MX, TOP, MW, MH, fill="#f7f9fb", stroke=BORDER_STRONG)
s.raw(f'<clipPath id="mclip"><rect x="{MX}" y="{TOP}" width="{MW}" height="{MH}" rx="{RMD}"/></clipPath>')
s.raw(f'<g clip-path="url(#mclip)">'
      f'<g transform="translate({MX - _x0*SC:.1f},{TOP - _y0*SC:.1f}) scale({SC:.4f})">'
      f'<path d="{COAST}" fill="#e8ecef" stroke="#d3d9de" stroke-width="0.7"/></g></g>')


def mp(lat, lon):
    x, y = proj(lat, lon)
    return MX + (x - _x0) * SC, TOP + (y - _y0) * SC


s.raw('<g clip-path="url(#mclip)">')
for name in ("redsea_to_suez", "suez_to_gibraltar", "suez_to_fos", "gibraltar_to_northsea"):
    pts = [mp(la, lo) for la, lo in GEO["corridors"][name]]
    d = " ".join(f"{'M' if i==0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(pts))
    s.raw(f'<path d="{d}" fill="none" stroke="{AMBER}" stroke-width="1.6" '
          f'stroke-linecap="round" opacity="0.55"/>')
s.raw('</g>')

PORTS = [("HAM", "Hamburg", 1, 10, -8, "start"), ("RTM", "Rotterdam", 1, -10, -9, "end"),
         ("ANR", "Antwerp", 0, -10, 15, "end"), ("RHINE", "Rhine", 1, 11, 14, "start"),
         ("FOS", "Fos", 0, 10, 13, "start"), ("SUEZ", "Suez", 0, -10, -8, "end")]
for pid, lab, hot, dx, dy, anc in PORTS:
    p = GEO["places"][pid]
    x, y = mp(p["lat"], p["lon"])
    s.raw(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{5 if hot else 3.6}" '
          f'fill="{AMBER if hot else CARD}" stroke="{AMBER if hot else FAINT}" stroke-width="1.5"/>')
    s.text(x + dx, y + dy, lab, 10, 600 if hot else 500, FG if hot else MUTED, anchor=anc)

s.card(MX + 14, TOP + MH - 46, 210, 32, fill=CARD, stroke=BORDER, rx=R)
s.raw(f'<circle cx="{MX+30}" cy="{TOP+MH-30}" r="4.5" fill="{AMBER}"/>')
s.text(MX + 42, TOP + MH - 26, "watched chokepoint", 10.5, 500, FG)
s.text(MX + MW - 16, TOP + 30, "lanes from data/geo.json", 9.5, 400, FAINT, anchor="end")

# =========================================================================
# THE APP, MID-RUN
# =========================================================================
AX, AY, AW, AH = 444, 502, W - M - 444, 332
s.card(AX, AY, AW, AH, stroke=BORDER_STRONG)
s.raw(f'<rect x="{AX}" y="{AY}" width="{AW}" height="38" rx="{RMD}" fill="{SURFACE}"/>')
s.raw(f'<rect x="{AX}" y="{AY+26}" width="{AW}" height="12" fill="{SURFACE}"/>')
s.line(AX, AY + 38, AX + AW, AY + 38, BORDER)
for k in range(3):
    s.raw(f'<circle cx="{AX+20+k*14}" cy="{AY+19}" r="4" fill="{GRAY400}"/>')
s.text(AX + 74, AY + 24, "SQRlane / Run", 11.5, 500, MUTED)
s.card(AX + 190, AY + 10, 132, 20, fill=AMBER_BG, stroke=AMBER, rx=R)
s.text(AX + 256, AY + 24, "triggered · 92%", 9.5, 700, AMBER, anchor="middle")
s.text(AX + AW - 20, AY + 24, "12:00", 10.5, 400, FAINT, anchor="end", cls="mono")

PX, PW2 = AX + 22, 430
s.text(PX, AY + 70, "AGENTS WORKING", 9.5, 700, FAINT, ls=1.3)
WORK = [("Risk Monitor", 100, "3 exceptions"), ("Route Advisor", 100, "14 options"),
        ("Comms Agent", 100, "6 mails"), ("Customs", 72, "in progress"),
        ("TMS Link", 40, "in progress")]
for j, (who, pct, out) in enumerate(WORK):
    y = AY + 102 + j * 42
    done = pct == 100
    s.raw(f'<circle cx="{PX+9}" cy="{y+2}" r="8" fill="{GREEN_BG if done else AMBER_BG}"/>')
    if done:
        s.raw(f'<path d="M{PX+5} {y+2} l3 3 l6 -7" stroke="{GREEN}" stroke-width="1.8" '
              f'fill="none" stroke-linecap="round"/>')
    else:
        s.raw(f'<circle cx="{PX+9}" cy="{y+2}" r="3" fill="{AMBER}"/>')
    s.text(PX + 28, y, who, 12.5, 600, FG)
    s.text(PX + PW2 - 20, y, out, 10.5, 400, FAINT, anchor="end", cls="mono")
    s.raw(f'<rect x="{PX+28}" y="{y+10}" width="220" height="6" rx="3" fill="{SURFACE}"/>')
    s.raw(f'<rect x="{PX+28}" y="{y+10}" width="{220*pct/100:.0f}" height="6" rx="3" '
          f'fill="{GREEN if done else AMBER}"/>')

# the artefact itself, so "drafts written" is a thing rather than a count
DXp = AX + 22 + PW2 + 26
DWp = 470
s.line(DXp - 26, AY + 58, DXp - 26, AY + AH - 22, BORDER)
s.text(DXp, AY + 70, "WHAT COMMS JUST WROTE", 9.5, 700, FAINT, ls=1.3)
s.card(DXp, AY + 84, DWp, 168, fill=CARD_MUTED, stroke=BORDER_STRONG)
s.text(DXp + 16, AY + 108, "To", 9.5, 600, FAINT)
s.text(DXp + 52, AY + 108, "Booking Desk, Hapag-Lloyd", 11, 500, FG)
s.text(DXp + 16, AY + 128, "Subj", 9.5, 600, FAINT)
s.text(DXp + 52, AY + 128, "HLCU-2261188 — amend discharge to RTM", 11, 500, FG)
s.line(DXp + 16, AY + 142, DXp + DWp - 16, AY + 142, BORDER)
for j, ln in enumerate(["Please amend the booking to discharge at RTM",
                        "instead of HAM, and confirm the revised schedule.",
                        "Revised ETA on our side is 15 Sep."]):
    s.text(DXp + 16, AY + 164 + j * 18, ln, 11, 400, MUTED)
s.chip(DXp + 16, AY + 222, 122, 22, "DRAFT · not sent", fs=9, fill=AMBER_BG, col=AMBER, weight=700)
s.text(DXp + 148, AY + 237, "written by Comms, held for you", 10.5, 400, FAINT)
s.text(DXp, AY + 276, "Five more like it: one customer mail, a carrier", 11.5, 400, MUTED)
s.text(DXp, AY + 294, "amendment, and the customs entry for Rotterdam.", 11.5, 400, MUTED)

QX = AX + AW - 22 - 300
s.line(QX - 26, AY + 58, QX - 26, AY + AH - 22, BORDER)
s.text(QX, AY + 70, "THE CALL", 9.5, 700, FAINT, ls=1.3)
s.text(QX, AY + 108, "Route around 2", 18, 600, FG, ls=-0.4)
s.text(QX, AY + 132, "Amend 1 · Watch 4", 18, 600, FG, ls=-0.4)
for j, (sid, act, col) in enumerate((("SHP-001", "route around", AMBER),
                                     ("SHP-005", "route around", AMBER),
                                     ("SHP-002", "amend", FG))):
    y = AY + 174 + j * 24
    s.text(QX, y, sid, 11, 500, MUTED, cls="mono")
    s.text(QX + 86, y, act, 11, 500, col)
s.card(QX, AY + AH - 84, 150, 34, fill=FG, stroke="none", rx=R)
s.text(QX + 75, AY + AH - 62, "Approve all", 12.5, 600, CARD, anchor="middle")
s.text(QX, AY + AH - 32, "or one at a time", 10.5, 400, FAINT)

s.text(M, 890, "The prediction moves the decision left, into the window where options still exist.",
       23, 600, FG, ls=-0.5)
s.footer("06 / THE HOW 2/2")
s.write("slide-06-the-how-2.svg")
