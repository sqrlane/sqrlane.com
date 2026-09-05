#!/usr/bin/env python3
"""
Shared drawing kit for the SQRlane deck.

Tokens are SQRlane's own, lifted verbatim from static/index.html, so the deck
and the product read as one thing. Geist Sans + Mono are embedded in every
slide so each SVG is self-contained.

House rules, enforced by convention rather than code:
  - Colour is spent only on state. AMBER means "this is where it hurts" and
    nothing else is tinted.
  - Detail belongs in the graphic, not in a third sentence.
  - Every figure on a slide is a cited third-party number, never one of ours.
"""
import base64, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

# ---- tokens (static/index.html) -----------------------------------------
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
AMBER_BG      = "#fdf3e3"
RED           = "#ea001d"
R, RMD        = 6, 12

W, H, M = 1920, 1080, 96
CW = W - 2 * M


def _font(name):
    return base64.b64encode((ROOT / "static" / "fonts" / name).read_bytes()).decode()


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Slide:
    """Collects SVG fragments and writes the file. Every helper returns None;
    geometry is passed in explicitly so a layout can be read off the code."""

    def __init__(self, extra_defs=""):
        self.p = []
        self.p.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
                      f'width="{W}" height="{H}" font-family="Geist">')
        self.p.append(f'''<defs>
<style>
@font-face{{font-family:"Geist";src:url(data:font/woff2;base64,{_font("Geist-Variable.woff2")}) format("woff2");font-weight:100 900;font-style:normal}}
@font-face{{font-family:"Geist Mono";src:url(data:font/woff2;base64,{_font("GeistMono-Variable.woff2")}) format("woff2");font-weight:100 900;font-style:normal}}
text{{font-family:"Geist",-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}}
.mono{{font-family:"Geist Mono",ui-monospace,Menlo,monospace}}
.num{{font-feature-settings:"tnum";font-variant-numeric:tabular-nums}}
</style>
<marker id="ahA" viewBox="0 0 8 8" refX="7.2" refY="4" markerWidth="5.4" markerHeight="5.4" orient="auto">
  <path d="M0,0.4 L8,4 L0,7.6 Z" fill="{AMBER}"/></marker>
<marker id="ahN" viewBox="0 0 8 8" refX="7.2" refY="4" markerWidth="5.4" markerHeight="5.4" orient="auto">
  <path d="M0,0.4 L8,4 L0,7.6 Z" fill="{FAINT}"/></marker>
{extra_defs}</defs>''')
        self.p.append(f'<rect width="{W}" height="{H}" fill="{BG}"/>')

    def raw(self, s):
        self.p.append(s)

    def text(self, x, y, s, size=13, weight=400, fill=FG, anchor="start", ls=0, cls=""):
        c = f' class="{cls}"' if cls else ""
        l = f' letter-spacing="{ls}"' if ls else ""
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        self.p.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
                      f'fill="{fill}"{a}{l}{c}>{esc(s)}</text>')

    def card(self, x, y, w, h, fill=CARD, stroke=BORDER, rx=RMD, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                      f'fill="{fill}" stroke="{stroke}"{d}/>')

    def line(self, x1, y1, x2, y2, stroke=BORDER, width=1, marker=None, dash=None):
        m = f' marker-end="url(#{marker})"' if marker else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" '
                      f'stroke-width="{width}"{m}{d}/>')

    def band_label(self, x, y, s):
        self.p.append(f'<rect x="{x}" y="{y-8}" width="8" height="8" rx="2" fill="{FG}"/>')
        self.text(x + 18, y, s, 11, 600, FAINT, ls=1.5)

    def header(self, eyebrow, headline, sub, rule_y=200):
        self.text(M, 74, eyebrow, 12, 600, FAINT, ls=2.2)
        self.text(M, 136, headline, 52, 600, FG, ls=-1.4)
        self.text(M, 176, sub, 17, 400, MUTED)
        self.line(M, rule_y, W - M, rule_y, BORDER_STRONG)

    def footer(self, right, rule_y=1008, base=1036):
        self.line(M, rule_y, W - M, rule_y, BORDER)
        self.p.append(f'<rect x="{M}" y="{base-14}" width="18" height="18" rx="5" fill="{FG}"/>')
        self.p.append(f'<path d="M{M+4.5} {base-1}h9 M{M+4.5} {base-5}h6 M{M+4.5} {base-9}h3.5" '
                      f'stroke="{CARD}" stroke-width="1.5" stroke-linecap="round"/>')
        self.text(M + 28, base, "SQRlane", 13, 600, FG)
        self.text(M + 92, base, "AI Agents for freight enterprises.", 12, 400, FAINT)
        self.text(W - M, base, right, 11.5, 500, FAINT, anchor="end", ls=1.2, cls="mono")

    def chip(self, x, y, w, h, label, fs=11.5, fill=SURFACE, stroke="none", col=MUTED, weight=500):
        self.card(x, y, w, h, fill=fill, stroke=stroke, rx=R)
        self.text(x + w / 2, y + h / 2 + fs * 0.36, label, fs, weight, col, anchor="middle")

    def write(self, path):
        self.p.append("</svg>")
        p = pathlib.Path(path)
        p.write_text("\n".join(self.p), encoding="utf-8")
        print(f"wrote {p}  ({p.stat().st_size/1024:.0f} KB)")
