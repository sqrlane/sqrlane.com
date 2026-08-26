#!/usr/bin/env python3
"""
Slide 01 - THE WHAT.  Emits deck/slide-01-the-what.svg at 1920x1080.

Design system is SQRlane's own (static/index.html): near-monochrome Geist surfaces,
hairline alpha borders, 6/12px radii. Colour is spent only on state - here amber
means exactly one thing, "this is where the pressure lands", and nothing else is
tinted. Geist Sans + Mono are embedded so the file is self-contained.
"""
import base64, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT  = ROOT / "deck" / "slide-01-the-what.svg"

def font(name):
    return base64.b64encode((ROOT / "static" / "fonts" / name).read_bytes()).decode()

# ---- tokens (verbatim from static/index.html) ----------------------------
BG, CARD      = "#fafafa", "#ffffff"
FG, MUTED     = "#171717", "#4d4d4d"
FAINT         = "#8f8f8f"
BORDER        = "#00000014"
BORDER_STRONG = "#00000024"
SURFACE       = "#f2f2f2"
GRAY400       = "#dbdbdb"
AMBER, AMBER_BG = "#96580a", "#fdf3e3"
RED           = "#ea001d"
R, RMD        = 6, 12

W, H, M = 1920, 1080, 96
CW = W - 2 * M                     # 1728 content width

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

p = []
add = p.append

# ---- head ---------------------------------------------------------------
add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Geist">')
add(f'''<defs>
<style>
@font-face{{font-family:"Geist";src:url(data:font/woff2;base64,{font("Geist-Variable.woff2")}) format("woff2");font-weight:100 900;font-style:normal}}
@font-face{{font-family:"Geist Mono";src:url(data:font/woff2;base64,{font("GeistMono-Variable.woff2")}) format("woff2");font-weight:100 900;font-style:normal}}
text{{font-family:"Geist",-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}}
.mono{{font-family:"Geist Mono",ui-monospace,Menlo,monospace}}
.num{{font-feature-settings:"tnum";font-variant-numeric:tabular-nums}}
</style>
<marker id="ahA" viewBox="0 0 8 8" refX="7.2" refY="4" markerWidth="5.4" markerHeight="5.4" orient="auto">
  <path d="M0,0.4 L8,4 L0,7.6 Z" fill="{AMBER}"/></marker>
<marker id="ahN" viewBox="0 0 8 8" refX="7.2" refY="4" markerWidth="5.4" markerHeight="5.4" orient="auto">
  <path d="M0,0.4 L8,4 L0,7.6 Z" fill="{FAINT}"/></marker>
</defs>''')
add(f'<rect width="{W}" height="{H}" fill="{BG}"/>')

def txt(x, y, s, size=13, weight=400, fill=FG, anchor="start", ls=0, cls=""):
    c = f' class="{cls}"' if cls else ""
    l = f' letter-spacing="{ls}"' if ls else ""
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}"{a}{l}{c}>{esc(s)}</text>')

def card(x, y, w, h, fill=CARD, stroke=BORDER, rx=RMD, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}"{d}/>')

def band_label(x, y, s):
    add(f'<rect x="{x}" y="{y-8}" width="8" height="8" rx="2" fill="{FG}"/>')
    txt(x + 18, y, s, 11, 600, FAINT, ls=1.5)

def chip(x, y, label, w=None, fs=11.5, fill=SURFACE, stroke="none", col=MUTED, h=24, weight=500):
    w = w or (len(label) * fs * 0.58 + 22)
    add(f'<rect x="{x}" y="{y}" width="{w:.1f}" height="{h}" rx="{R}" fill="{fill}" stroke="{stroke}"/>')
    txt(x + w / 2, y + h / 2 + fs * 0.36, label, fs, weight, col, anchor="middle")
    return w

# =========================================================================
# HEADER
# =========================================================================
txt(M, 78, "01 — THE WHAT", 12, 600, FAINT, ls=2.2)
txt(M, 138, "Everything moves the lane. Nothing moves the booking.", 50, 600, FG, ls=-1.2)
txt(M, 180, "Four forces converge on one booking. The software that sees them cannot act. "
            "The software that acts cannot see.", 17, 400, MUTED)
add(f'<line x1="{M}" y1="212" x2="{W-M}" y2="212" stroke="{BORDER_STRONG}"/>')

# =========================================================================
# BAND A - what moves the lane
# =========================================================================
band_label(M, 254, "WHAT MOVES THE LANE")

CY, CH, CWd, GAP = 270, 220, 408, 32

def force(i, cat, big, big_sub, unit, ctx1, ctx2, src, micro):
    x = M + i * (CWd + GAP)
    card(x, CY, CWd, CH)
    tx = x + 24
    txt(tx, CY + 34, cat, 11, 600, FAINT, ls=1.4)
    add(f'<text x="{tx}" y="{CY+92}" font-size="42" font-weight="600" fill="{FG}" '
        f'letter-spacing="-1.4" class="num">{esc(big)}'
        + (f'<tspan font-size="19" font-weight="500" fill="{FAINT}" letter-spacing="0"> {esc(big_sub)}</tspan>' if big_sub else "")
        + '</text>')
    txt(tx, CY + 118, unit, 13.5, 500, FG)
    txt(tx, CY + 140, ctx1, 12.5, 400, MUTED)
    txt(tx, CY + 158, ctx2, 12.5, 400, MUTED)
    micro(tx, CY + 184)
    txt(tx, CY + 210, src, 10.5, 400, FAINT, cls="mono")

# -- micro 1: 14 chokepoints, 3 with no viable alternative
def m_choke(x, y):
    for i in range(14):
        cx = x + 4 + i * 13.5
        if i < 3:
            add(f'<circle cx="{cx:.1f}" cy="{y}" r="4" fill="{RED}"/>')
        else:
            add(f'<circle cx="{cx:.1f}" cy="{y}" r="3.4" fill="none" stroke="{GRAY400}" stroke-width="1.3"/>')

# -- micro 2: water level, marker at record low
def m_water(x, y):
    add(f'<rect x="{x}" y="{y-4}" width="186" height="8" rx="4" fill="{SURFACE}"/>')
    add(f'<rect x="{x+108}" y="{y-4}" width="78" height="8" rx="4" fill="{GRAY400}"/>')
    add(f'<rect x="{x+8}" y="{y-8}" width="3" height="16" rx="1.5" fill="{RED}"/>')
    txt(x + 194, y + 4, "normal", 10, 400, FAINT)

# -- micro 3: two bars, +123 / +128
def m_bars(x, y):
    for i, (lab, v) in enumerate((("geo", 123), ("reg", 128))):
        by = y - 6 + i * 11
        add(f'<rect x="{x+26}" y="{by}" width="{v*0.92:.0f}" height="7" rx="3.5" fill="{AMBER if i else GRAY400}"/>')
        txt(x, by + 6.4, lab, 9.5, 500, FAINT, cls="mono")

# -- micro 4: sparkline, down then sharply up
def m_spark(x, y):
    pts = [(0, -2), (24, 4), (52, 9), (74, 6), (96, 8), (120, 0), (146, -6), (172, -12)]
    d = " ".join(f"{'M' if i==0 else 'L'}{x+px},{y+py}" for i, (px, py) in enumerate(pts))
    add(f'<path d="{d}" fill="none" stroke="{AMBER}" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/>')
    add(f'<circle cx="{x+172}" cy="{y-12}" r="3" fill="{AMBER}"/>')

force(0, "CHOKEPOINTS", "3", "of 14", "with no viable alternative route",
      "~80% of world trade moves by sea, most of it",
      "through about a dozen chokepoints.", "BCG · 2026", m_choke)
force(1, "CLIMATE", "1880", "", "Rhine at Kaub, lowest since records began",
      "Surcharges past €1,000 a container, and up to",
      "~0.35pp off German GDP this quarter if it holds.", "gCaptain · ING · Aug 2026", m_water)
force(2, "POLICY", "+128%", "", "regulatory-change alerts, year on year",
      "Geopolitical alerts over the same period: +123%.",
      "A tariff filing now reprices a lane on its own.", "Resilinc EventWatchAI", m_bars)
force(3, "PRICE", "2.4×", "", "spot-rate swing in eleven months",
      "Drewry WCI, per 40ft: $1,913 in Sep 2025 to",
      "$4,526 in Aug 2026.", "Drewry World Container Index", m_spark)

# -- convergence arrows ----------------------------------------------------
for i in range(4):
    cx = M + i * (CWd + GAP) + CWd / 2
    add(f'<line x1="{cx}" y1="498" x2="{cx}" y2="546" stroke="{AMBER}" stroke-width="1.6" marker-end="url(#ahA)"/>')

# =========================================================================
# THE BOOKING - everything lands here
# =========================================================================
LY, LH = 550, 86
card(M, LY, CW, LH, stroke=BORDER_STRONG)
txt(M + 26, LY + 40, "SHP-001", 14, 600, FG, cls="mono")
txt(M + 26, LY + 62, "Automotive parts · 32d transit", 11.5, 400, FAINT)

NODES = [("SHANGHAI", 470, False), ("SUEZ", 767, True), ("HAMBURG", 1064, True), ("MUNICH", 1361, False)]
add(f'<line x1="470" y1="{LY+46}" x2="1361" y2="{LY+46}" stroke="{GRAY400}" stroke-width="1.4"/>')
for name, nx, hot in NODES:
    if hot:
        add(f'<circle cx="{nx}" cy="{LY+46}" r="9" fill="none" stroke="{AMBER}" stroke-width="1.6"/>')
        add(f'<circle cx="{nx}" cy="{LY+46}" r="4" fill="{AMBER}"/>')
    else:
        add(f'<circle cx="{nx}" cy="{LY+46}" r="4.5" fill="{CARD}" stroke="{FAINT}" stroke-width="1.6"/>')
    txt(nx, LY + 28, name, 10.5, 500, AMBER if hot else FAINT, anchor="middle", ls=0.8, cls="mono")
add(f'<line x1="{W-M-232}" y1="{LY+16}" x2="{W-M-232}" y2="{LY+LH-16}" stroke="{BORDER_STRONG}"/>')
txt(W - M - 26, LY + 40, "ETA 14 Oct", 14, 600, FG, anchor="end", cls="mono")
txt(W - M - 26, LY + 62, "on plan · 4d slack", 11.5, 400, FAINT, anchor="end")

txt(M, 668, "One booking. Each of those four rewrites its route, its ETA, or its cost — "
            "and the rewrite has to reach the record before anyone acts on it.", 13.5, 400, MUTED)

# =========================================================================
# BAND B - what the desk has
# =========================================================================
band_label(M, 710, "WHAT THE DESK HAS")

BY, BH = 728, 248
C1X, C1W = M, 520
C2X, C2W = 660, 600
C3X, C3W = 1304, 520

def capability(x, y, states):
    """three segments: watch / decide / act - filled means the layer does it."""
    seg, gap = 88, 10
    for i, (lab, on) in enumerate(states):
        sx = x + i * (seg + gap)
        add(f'<rect x="{sx}" y="{y}" width="{seg}" height="6" rx="3" fill="{FG if on else GRAY400}"/>')
        txt(sx, y + 22, lab, 10, 500, FG if on else FAINT, ls=0.6, cls="mono")

def side(x, w, label, verb, desc, vendors, states, status):
    card(x, BY, w, BH)
    tx = x + 26
    txt(tx, BY + 34, label, 11, 600, FAINT, ls=1.4)
    txt(tx, BY + 78, verb, 30, 600, FG, ls=-0.8)
    txt(tx, BY + 104, desc, 13, 400, MUTED)
    capability(tx, BY + 132, states)
    cx = tx
    for v in vendors:
        cx += chip(cx, BY + 178, v) + 8
    add(f'<circle cx="{tx+4}" cy="{BY+224}" r="3.5" fill="{AMBER}"/>')
    txt(tx + 16, BY + 228, status, 12, 500, MUTED)

side(C1X, C1W, "RISK PLATFORMS", "See it.", "Alert, score, map exposure.",
     ["Everstream", "Interos", "Resilinc"],
     [("WATCH", True), ("DECIDE", False), ("ACT", False)], "stops at the alert")

side(C3X, C3W, "TMS & EXECUTION", "Do it.", "Book, amend, update, file.",
     ["CargoWise", "Riege", "Descartes", "Transporeon"],
     [("WATCH", False), ("DECIDE", False), ("ACT", True)], "moves only after a person decides")

# -- the centre: the only part that is not software ------------------------
card(C2X, BY, C2W, BH, fill=AMBER_BG, stroke="#96580a3d")
tx = C2X + 26
txt(tx, BY + 34, "THE DESK", 11, 600, AMBER, ls=1.4)
txt(C2X + C2W - 26, BY + 34, "the only part that is not software", 11, 500, AMBER, anchor="end")
txt(tx, BY + 78, "Joins them. By hand.", 30, 600, FG, ls=-0.8)
txt(tx, BY + 104, "The same four steps, once per booking, every time.", 13, 400, MUTED)

STEPS, SW, SG = ["READ", "DECIDE", "WRITE", "RE-KEY"], 120, 22
for i, s in enumerate(STEPS):
    sx = tx + i * (SW + SG)
    last = i == len(STEPS) - 1
    add(f'<rect x="{sx}" y="{BY+130}" width="{SW}" height="34" rx="{R}" '
        f'fill="{AMBER if last else CARD}" stroke="{"none" if last else BORDER_STRONG}"/>')
    txt(sx + SW / 2, BY + 152, s, 12, 600, CARD if last else FG, anchor="middle", ls=0.8, cls="mono")
    if not last:
        add(f'<line x1="{sx+SW+5}" y1="{BY+147}" x2="{sx+SW+SG-5}" y2="{BY+147}" '
            f'stroke="{FAINT}" stroke-width="1.3" marker-end="url(#ahN)"/>')
txt(tx, BY + 194, "× every booking on the board", 12.5, 500, MUTED)
txt(tx + 4, BY + 228, "Re-key is the step that eats the day — and the only one that counts.",
    12, 500, AMBER)

# -- flow arrows between the three columns ---------------------------------
for x1, x2 in ((C1X + C1W + 8, C2X - 8), (C2X + C2W + 8, C3X - 8)):
    add(f'<line x1="{x1}" y1="{BY+BH/2}" x2="{x2}" y2="{BY+BH/2}" stroke="{FAINT}" '
        f'stroke-width="1.4" marker-end="url(#ahN)"/>')

# =========================================================================
# FOOTER
# =========================================================================
txt(M, 996, "Named systems are integration targets, not integrations. None of them is connected.",
    11, 400, FAINT)
add(f'<line x1="{M}" y1="1012" x2="{W-M}" y2="1012" stroke="{BORDER}"/>')
add(f'<rect x="{M}" y="1026" width="18" height="18" rx="5" fill="{FG}"/>')
add(f'<path d="M{M+4.5} 1039h9 M{M+4.5} 1035h6 M{M+4.5} 1031h3.5" stroke="{CARD}" '
    f'stroke-width="1.5" stroke-linecap="round"/>')
txt(M + 28, 1040, "SQRlane", 13, 600, FG)
txt(M + 92, 1040, "Trade-lane risk, decided.", 12, 400, FAINT)
txt(W - M, 1040, "01 / THE WHAT", 11.5, 500, FAINT, anchor="end", ls=1.2, cls="mono")

add("</svg>")
OUT.write_text("\n".join(p), encoding="utf-8")
print(f"wrote {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")
