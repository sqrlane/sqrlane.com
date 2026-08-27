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
txt(M, 78, "INTRODUCTION", 12, 600, FAINT, ls=2.2)
txt(M, 142, "A freight forwarder's product is a date.", 52, 600, FG, ls=-1.4)
txt(M, 184, "They own no ships, no trucks, no planes. They sell one promise: this box, there, by then.",
    17, 400, MUTED)
add(f'<line x1="{M}" y1="216" x2="{W-M}" y2="216" stroke="{BORDER_STRONG}"/>')

# =========================================================================
# BEAT 1 - what can take the date
# =========================================================================
band_label(M, 258, "FOUR THINGS CAN TAKE THAT DATE")

CY, CH, CWd, GAP = 276, 220, 408, 32

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

def m_choke(x, y):
    for i in range(14):
        cx = x + 4 + i * 13.5
        if i < 3:
            add(f'<circle cx="{cx:.1f}" cy="{y}" r="4" fill="{RED}"/>')
        else:
            add(f'<circle cx="{cx:.1f}" cy="{y}" r="3.4" fill="none" stroke="{GRAY400}" stroke-width="1.3"/>')

def m_water(x, y):
    add(f'<rect x="{x}" y="{y-4}" width="186" height="8" rx="4" fill="{SURFACE}"/>')
    add(f'<rect x="{x+108}" y="{y-4}" width="78" height="8" rx="4" fill="{GRAY400}"/>')
    add(f'<rect x="{x+8}" y="{y-8}" width="3" height="16" rx="1.5" fill="{RED}"/>')
    txt(x + 194, y + 4, "normal", 10, 400, FAINT)

def m_bars(x, y):
    for i, (lab, v) in enumerate((("geo", 123), ("reg", 128))):
        by = y - 6 + i * 11
        add(f'<rect x="{x+26}" y="{by}" width="{v*0.92:.0f}" height="7" rx="3.5" fill="{AMBER if i else GRAY400}"/>')
        txt(x, by + 6.4, lab, 9.5, 500, FAINT, cls="mono")

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

for i in range(4):
    cx = M + i * (CWd + GAP) + CWd / 2
    add(f'<line x1="{cx}" y1="504" x2="{cx}" y2="550" stroke="{AMBER}" stroke-width="1.6" marker-end="url(#ahA)"/>')

# =========================================================================
# BEAT 2 - the promise itself
# =========================================================================
LY, LH = 558, 96
card(M, LY, CW, LH, stroke=BORDER_STRONG)
txt(M + 26, LY + 42, "SHP-001", 14, 600, FG, cls="mono")
txt(M + 26, LY + 64, "Automotive parts · Shanghai → Munich", 11.5, 400, FAINT)

NODES = [("SHANGHAI", 470, False), ("SUEZ", 757, True), ("HAMBURG", 1044, True), ("MUNICH", 1331, False)]
add(f'<line x1="470" y1="{LY+52}" x2="1331" y2="{LY+52}" stroke="{GRAY400}" stroke-width="1.4"/>')
for name, nx, hot in NODES:
    if hot:
        add(f'<circle cx="{nx}" cy="{LY+52}" r="9" fill="none" stroke="{AMBER}" stroke-width="1.6"/>')
        add(f'<circle cx="{nx}" cy="{LY+52}" r="4" fill="{AMBER}"/>')
    else:
        add(f'<circle cx="{nx}" cy="{LY+52}" r="4.5" fill="{CARD}" stroke="{FAINT}" stroke-width="1.6"/>')
    txt(nx, LY + 34, name, 10.5, 500, AMBER if hot else FAINT, anchor="middle", ls=0.8, cls="mono")

# the date is the product, so it is set as the hero of this row
add(f'<line x1="{W-M-262}" y1="{LY+18}" x2="{W-M-262}" y2="{LY+LH-18}" stroke="{BORDER_STRONG}"/>')
txt(W - M - 26, LY + 32, "THE DATE", 10, 600, FAINT, anchor="end", ls=1.4)
txt(W - M - 26, LY + 64, "14 Oct", 30, 600, FG, anchor="end", ls=-0.8, cls="num")
txt(W - M - 26, LY + 84, "4 days of margin", 12, 500, MUTED, anchor="end")

txt(M, 690, "One booking, one date, four days of margin. Any one of the four above can eat all of it.",
    14, 400, MUTED)

# =========================================================================
# BEAT 3 - and nobody is watching, because the desk is doing data entry
# =========================================================================
band_label(M, 738, "AND THE PERSON WHO OWNS THAT DATE")

DY, DH = 756, 172
card(M, DY, CW, DH)
bx, bw = M + 26, CW - 52
txt(bx, DY + 36, "A working day on a forwarding desk", 14.5, 600, FG)

BARY, BARH = DY + 62, 38
admin = bw * 0.40
add(f'<rect x="{bx}" y="{BARY}" width="{bw}" height="{BARH}" rx="{R}" fill="{CARD_MUTED}" stroke="{BORDER_STRONG}"/>')
add(f'<rect x="{bx}" y="{BARY}" width="{admin:.0f}" height="{BARH}" rx="{R}" fill="{SURFACE_2}" stroke="{BORDER_STRONG}"/>')
add(f'<line x1="{bx+admin:.0f}" y1="{BARY}" x2="{bx+admin:.0f}" y2="{BARY+BARH}" stroke="{BORDER_STRONG}"/>')
txt(bx + 16, BARY + 24, "up to 40% of the day", 13.5, 600, FG)
txt(bx + admin + 16, BARY + 24, "customer work, exceptions, everything else", 13, 400, MUTED)

txt(bx, BARY + BARH + 26, "Quotes · rate requests · data entry · documents · tracking · invoice checks · customs entries",
    12.5, 400, FAINT)

add(f'<circle cx="{bx+4}" cy="{DY+DH-24}" r="3.5" fill="{AMBER}"/>')
txt(bx + 16, DY + DH - 20,
    "Watching the world that moves the cargo has no slot on this bar. It happens between other calls, or it does not happen.",
    13, 500, AMBER)

# =========================================================================
# THE TURN
# =========================================================================
txt(M, 972, "The one person who could protect the date is doing data entry.", 24, 600, FG, ls=-0.5)

add(f'<line x1="{M}" y1="1006" x2="{W-M}" y2="1006" stroke="{BORDER}"/>')
add(f'<rect x="{M}" y="1022" width="18" height="18" rx="5" fill="{FG}"/>')
add(f'<path d="M{M+4.5} 1035h9 M{M+4.5} 1031h6 M{M+4.5} 1027h3.5" stroke="{CARD}" '
    f'stroke-width="1.5" stroke-linecap="round"/>')
txt(M + 28, 1036, "SQRlane", 13, 600, FG)
txt(M + 92, 1036, "Trade-lane risk, decided.", 12, 400, FAINT)
txt(W - M, 1036, "01 / INTRODUCTION", 11.5, 500, FAINT, anchor="end", ls=1.2, cls="mono")

add("</svg>")
OUT.write_text("\n".join(p), encoding="utf-8")
print(f"wrote {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")
