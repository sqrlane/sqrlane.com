#!/usr/bin/env python3
"""
Slide 01 - INTRODUCTION.  Emits deck/slide-01-introduction.svg at 1920x1080.

The story, in three beats: a forwarder sells a date -> four things can take it
-> the one person who could protect it is doing data entry. The competitive
frame (risk platforms vs TMS) deliberately does NOT live here; an introduction
needs a protagonist, not a positioning grid.

Design system is SQRlane's own (static/index.html): near-monochrome Geist
surfaces, hairline alpha borders, 6/12px radii. Colour is spent only on state -
amber means "this is where the pressure lands" and nothing else is tinted.
Geist Sans + Mono are embedded so the file is self-contained.
"""
import base64, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT  = ROOT / "deck" / "slide-01-introduction.svg"

def font(name):
    return base64.b64encode((ROOT / "static" / "fonts" / name).read_bytes()).decode()

# ---- tokens (verbatim from static/index.html) ----------------------------
BG, CARD      = "#fafafa", "#ffffff"
CARD_MUTED    = "#fafafa"
FG, MUTED     = "#171717", "#4d4d4d"
FAINT         = "#8f8f8f"
BORDER        = "#00000014"
BORDER_STRONG = "#00000024"
SURFACE       = "#f2f2f2"
SURFACE_2     = "#ebebeb"
GRAY400       = "#dbdbdb"
AMBER         = "#96580a"
RED           = "#ea001d"
R, RMD        = 6, 12

W, H, M = 1920, 1080, 96
CW = W - 2 * M                     # 1728 content width

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

p = []
add = p.append

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
</defs>''')
add(f'<rect width="{W}" height="{H}" fill="{BG}"/>')

def txt(x, y, s, size=13, weight=400, fill=FG, anchor="start", ls=0, cls=""):
    c = f' class="{cls}"' if cls else ""
    l = f' letter-spacing="{ls}"' if ls else ""
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}"{a}{l}{c}>{esc(s)}</text>')

def card(x, y, w, h, fill=CARD, stroke=BORDER, rx=RMD):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}"/>')

def band_label(x, y, s):
    add(f'<rect x="{x}" y="{y-8}" width="8" height="8" rx="2" fill="{FG}"/>')
    txt(x + 18, y, s, 11, 600, FAINT, ls=1.5)

# =========================================================================
# HEADER - the story opens here
# =========================================================================
txt(M, 74, "INTRODUCTION", 12, 600, FAINT, ls=2.2)
txt(M, 136, "A freight forwarder's product is a date.", 52, 600, FG, ls=-1.4)
txt(M, 176, "No ships, no trucks, no planes. Just one promise: this box, there, by then.", 17, 400, MUTED)
add(f'<line x1="{M}" y1="200" x2="{W-M}" y2="200" stroke="{BORDER_STRONG}"/>')

# =========================================================================
# BEAT 1 - what can take the date
# =========================================================================
band_label(M, 238, "FOUR THINGS CAN TAKE THAT DATE")

CY, CH, CWd, GAP = 254, 304, 408, 32

def force(i, cat, big, big_sub, line, summary, src, micro):
    """One card. The number and `line` read as a single phrase ("146 years since
    the Rhine was this low"); `summary` is the plain-language payoff - why this
    threatens the date - and the graphic carries the detail that used to be
    prose."""
    x = M + i * (CWd + GAP)
    card(x, CY, CWd, CH)
    tx = x + 26
    txt(tx, CY + 36, cat, 11, 600, FAINT, ls=1.4)
    add(f'<text x="{tx}" y="{CY+104}" font-size="48" font-weight="600" fill="{FG}" '
        f'letter-spacing="-1.8" class="num">{esc(big)}'
        + (f'<tspan font-size="21" font-weight="500" fill="{FAINT}" letter-spacing="0"> {esc(big_sub)}</tspan>' if big_sub else "")
        + '</text>')
    txt(tx, CY + 132, line, 14.5, 500, FG)
    micro(tx, CY + 152)
    add(f'<line x1="{tx}" y1="{CY+238}" x2="{x+CWd-26}" y2="{CY+238}" stroke="{BORDER}"/>')
    txt(tx, CY + 262, summary, 12.5, 400, MUTED)
    txt(tx, CY + 286, src, 10.5, 400, FAINT, cls="mono")

def m_choke(x, y):
    """14 chokepoints. The 3 with no alternative are split off by a gap, so the
    ratio reads on its own - the headline above already names it."""
    for i in range(3):
        add(f'<circle cx="{x+12+i*23}" cy="{y+40}" r="8" fill="{RED}"/>')
    for i in range(11):
        add(f'<circle cx="{x+97+i*23}" cy="{y+40}" r="6.5" fill="none" '
            f'stroke="{GRAY400}" stroke-width="1.7"/>')

def m_water(x, y):
    """A depth scale: where the Rhine sits now against where it normally sits."""
    add(f'<rect x="{x+2}" y="{y+30}" width="340" height="14" rx="7" fill="{SURFACE}"/>')
    add(f'<rect x="{x+192}" y="{y+30}" width="150" height="14" rx="7" fill="{GRAY400}"/>')
    add(f'<rect x="{x+12}" y="{y+22}" width="4" height="30" rx="2" fill="{RED}"/>')
    txt(x + 14, y + 16, "now", 11.5, 600, RED, anchor="middle")
    txt(x + 267, y + 16, "normal", 11.5, 400, FAINT, anchor="middle")
    txt(x + 2, y + 70, "record low", 11.5, 500, FG)

def m_bars(x, y):
    """Two alert categories, drawn to the same scale so they compare."""
    for i, (lab, v, hot) in enumerate((("rules", 128, True), ("politics", 123, False))):
        by = y + 24 + i * 34
        add(f'<rect x="{x+66}" y="{by}" width="{v*1.72:.0f}" height="18" rx="{R}" '
            f'fill="{AMBER if hot else GRAY400}"/>')
        txt(x, by + 13.5, lab, 11.5, 500, FAINT)
        txt(x + 66 + v * 1.72 + 10, by + 13.5, f"+{v}%", 12, 600, FG)

def m_spark(x, y):
    """The swing itself, with only the two endpoints labelled."""
    x0, w, y0, h = x + 12, 224, y + 16, 42
    pts = [(0, .45), (.12, .62), (.25, .95), (.4, .78), (.55, .84), (.7, .5), (.85, .24), (1, .04)]
    d = " ".join(f"{'M' if i==0 else 'L'}{x0+px*w:.0f},{y0+py*h:.0f}" for i, (px, py) in enumerate(pts))
    add(f'<path d="{d}" fill="none" stroke="{AMBER}" stroke-width="2.2" '
        f'stroke-linejoin="round" stroke-linecap="round"/>')
    lx, ly = x0 + .25 * w, y0 + .95 * h
    add(f'<circle cx="{lx:.0f}" cy="{ly:.0f}" r="3.6" fill="{GRAY400}"/>')
    txt(lx, ly + 20, "$1,913", 12, 500, FAINT, anchor="middle")
    add(f'<circle cx="{x0+w}" cy="{y0+.04*h:.0f}" r="4" fill="{AMBER}"/>')
    txt(x0 + w + 12, y0 + .04 * h + 4, "$4,526", 13, 600, FG)

force(0, "CHOKEPOINTS", "3", "of 14", "have no way around",
      "If one closes, there is no second route.", "BCG · 2026", m_choke)
force(1, "CLIMATE", "146", "years", "since the Rhine was this low",
      "Less cargo per barge, and surcharges on top.", "gCaptain · ING · Aug 2026", m_water)
force(2, "POLICY", "+128%", "", "more rule changes to track",
      "One tariff filing can reprice a lane overnight.", "Resilinc EventWatchAI", m_bars)
force(3, "PRICE", "2.4×", "", "swing in what a container costs",
      "The same box, twice the price, months apart.", "Drewry · $1,913 to $4,526 per 40ft", m_spark)

for i in range(4):
    cx = M + i * (CWd + GAP) + CWd / 2
    add(f'<line x1="{cx}" y1="566" x2="{cx}" y2="606" stroke="{AMBER}" stroke-width="1.6" marker-end="url(#ahA)"/>')

# =========================================================================
# BEAT 2 - the promise itself
# =========================================================================
LY, LH = 614, 88
card(M, LY, CW, LH, stroke=BORDER_STRONG)
txt(M + 26, LY + 38, "SHP-001", 14, 600, FG, cls="mono")
txt(M + 26, LY + 60, "Automotive parts · Shanghai → Munich", 11.5, 400, FAINT)

NODES = [("SHANGHAI", 470, False), ("SUEZ", 757, True), ("HAMBURG", 1044, True), ("MUNICH", 1331, False)]
add(f'<line x1="470" y1="{LY+48}" x2="1331" y2="{LY+48}" stroke="{GRAY400}" stroke-width="1.4"/>')
for name, nx, hot in NODES:
    if hot:
        add(f'<circle cx="{nx}" cy="{LY+48}" r="9" fill="none" stroke="{AMBER}" stroke-width="1.6"/>')
        add(f'<circle cx="{nx}" cy="{LY+48}" r="4" fill="{AMBER}"/>')
    else:
        add(f'<circle cx="{nx}" cy="{LY+48}" r="4.5" fill="{CARD}" stroke="{FAINT}" stroke-width="1.6"/>')
    txt(nx, LY + 30, name, 10.5, 500, AMBER if hot else FAINT, anchor="middle", ls=0.8, cls="mono")

# the date is the product, so it is set as the hero of this row
add(f'<line x1="{W-M-262}" y1="{LY+18}" x2="{W-M-262}" y2="{LY+LH-18}" stroke="{BORDER_STRONG}"/>')
txt(W - M - 26, LY + 30, "THE DATE", 10, 600, FAINT, anchor="end", ls=1.4)
txt(W - M - 26, LY + 60, "14 Oct", 30, 600, FG, anchor="end", ls=-0.8, cls="num")
txt(W - M - 26, LY + 78, "4 days of margin", 12, 500, MUTED, anchor="end")

txt(M, 732, "Four days of margin. Any one of the four above can eat all of it.", 14, 400, MUTED)

# =========================================================================
# BEAT 3 - and nobody is watching, because the desk is doing data entry
# =========================================================================
band_label(M, 774, "AND THE PERSON WHO OWNS IT")

DY, DH = 788, 156
card(M, DY, CW, DH)
bx, bw = M + 26, CW - 52
txt(bx, DY + 34, "A working day on the desk", 14.5, 600, FG)

BARY, BARH = DY + 54, 38
admin = bw * 0.40
add(f'<rect x="{bx}" y="{BARY}" width="{bw}" height="{BARH}" rx="{R}" fill="{CARD_MUTED}" stroke="{BORDER_STRONG}"/>')
add(f'<rect x="{bx}" y="{BARY}" width="{admin:.0f}" height="{BARH}" rx="{R}" fill="{SURFACE_2}" stroke="{BORDER_STRONG}"/>')
add(f'<line x1="{bx+admin:.0f}" y1="{BARY}" x2="{bx+admin:.0f}" y2="{BARY+BARH}" stroke="{BORDER_STRONG}"/>')
txt(bx + 16, BARY + 24, "40% repetitive admin", 13.5, 600, FG)
txt(bx + admin + 16, BARY + 24, "everything else", 13, 400, MUTED)

txt(bx, BARY + BARH + 24, "Quotes · data entry · documents · invoices · customs", 12.5, 400, FAINT)

add(f'<circle cx="{bx+4}" cy="{DY+DH-24}" r="3.5" fill="{AMBER}"/>')
txt(bx + 16, DY + DH - 20,
    "Watching the world that moves the cargo has no slot on this bar.", 13, 500, AMBER)

# =========================================================================
# THE TURN
# =========================================================================
txt(M, 980, "The one person who could protect the date is doing data entry.", 24, 600, FG, ls=-0.5)

add(f'<line x1="{M}" y1="1008" x2="{W-M}" y2="1008" stroke="{BORDER}"/>')
add(f'<rect x="{M}" y="1022" width="18" height="18" rx="5" fill="{FG}"/>')
add(f'<path d="M{M+4.5} 1035h9 M{M+4.5} 1031h6 M{M+4.5} 1027h3.5" stroke="{CARD}" '
    f'stroke-width="1.5" stroke-linecap="round"/>')
txt(M + 28, 1036, "SQRlane", 13, 600, FG)
txt(M + 92, 1036, "Trade-lane risk, decided.", 12, 400, FAINT)
txt(W - M, 1036, "01 / INTRODUCTION", 11.5, 500, FAINT, anchor="end", ls=1.2, cls="mono")

add("</svg>")
OUT.write_text("\n".join(p), encoding="utf-8")
print(f"wrote {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")
