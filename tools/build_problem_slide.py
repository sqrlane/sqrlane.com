#!/usr/bin/env python3
"""Build the What/problem slide as an editable SVG, sized for Figma.

Why a generator and not a hand-written SVG: SVG text does not wrap. A line that
outgrows its column does not reflow, it silently runs into the next one - and
nobody sees it until the file is open in Figma. So every string here is measured
against the real Geist metrics in static/fonts/ and the build FAILS if one
overruns its box. That is the same discipline tools/build_pitch_pptx.js applies
to the PowerPoint, for the same reason: a layout fault that no validator catches.

The geometry is lifted from the reference deck (1920x1080, 48px margins, two
884px columns). The type is Geist, which the rest of the product already uses -
measured against the reference it sits within ~2% at weight 400.

    python3 tools/build_problem_slide.py

Writes static/assets/slide-problem.svg.
"""

import re
import sys
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parent.parent
FONT = ROOT / "static" / "fonts" / "Geist-Variable.woff2"
OUT = ROOT / "static" / "assets" / "slide-problem.svg"

# ---------------------------------------------------------------- type metrics

_cache: dict[int, TTFont] = {}


def _face(weight: int) -> TTFont:
    if weight not in _cache:
        _cache[weight] = instantiateVariableFont(
            TTFont(FONT), {"wght": weight}, inplace=False
        )
    return _cache[weight]


def measure(text: str, size: float, weight: int, tracking: float = 0.0) -> float:
    """Advance width in px, including letter-spacing. Raises on a missing glyph."""
    face = _face(weight)
    cmap, hmtx, upem = face.getBestCmap(), face["hmtx"], face["head"].unitsPerEm
    total = 0
    for ch in text:
        glyph = cmap.get(ord(ch))
        if glyph is None:
            raise SystemExit(f"Geist has no glyph for {ch!r} (U+{ord(ch):04X}) in: {text!r}")
        total += hmtx[glyph][0]
    return total / upem * size + tracking * len(text)


def tracking_for(text: str, size: float, weight: int, target: float) -> float:
    """The per-character letter-spacing that makes `text` span `target` px."""
    return (target - measure(text, size, weight)) / max(len(text), 1)


# --------------------------------------------------------------------- palette
# Sampled out of the reference deck. The greys are very slightly warm (blue is a
# few steps down) - that is what the reference uses, so it is what we use.
INK = "#000000"
MUTED = "#797972"
HAIRLINE = "#DDDDD6"
PANEL = "#EFEFED"
PAPER = "#FFFFFF"

# One family, no CSS fallback stack. Figma imports a comma-separated stack as a
# single literal font name and reports it missing on all 32 layers; a bare name
# resolves cleanly, and Geist is in Figma's Google Fonts library.
FAMILY = "Geist"

# ---------------------------------------------------------------------- layout
W, H = 1920, 1080
ML, MR = 48.0, 1872.0
COL_L, COL_R = 48.0, 988.0          # column left edges
COL_W = 884.0                       # column width -> right edges 932 / 1872
IND_L, IND_R = 115.5, 1055.8        # text indent inside each column
ROW_STEP = 88.0                     # baseline-to-baseline between list rows

TITLE_SIZE, TITLE_LEAD = 58.9, 63.4
TITLE_BASE = 88.0
SUB_SIZE, SUB_BASE = 24.6, 264.0
RULE_Y = 301.0
HEAD_SIZE, HEAD_BASE = 24.6, 355.5
HEAD_RULE_Y = 373.0
ROW_TITLE_SIZE, ROW_TITLE_BASE = 21.0, 431.4
ROW_BODY_SIZE, ROW_BODY_BASE = 17.3, 460.9
ROW_SEPS = (482.0, 570.0)
FIG_SIZE, FIG_BASE = 56.5, 956.0
MICRO_SIZE = 12.4
PANEL_X, PANEL_Y, PANEL_H = 255.0, 893.0, 112.0
PANEL_PAD = 26.9
LEAD_SIZE, LEAD_BASE = 21.0, 936.4
NOTE_SIZE, NOTE_BASE = 19.0, 972.3
FOOT_BASE = 1034.4
PAGE_SIZE = 13.1

# --------------------------------------------------------------------- content
TITLE = [
    "European freight forwarding",
    "still runs on people doing",
    "the data work by hand",
]
SUBTITLE = "The category has no product problem. It has a labour problem that nobody has priced."

LEFT_HEAD = "What the work actually is"
LEFT_ROWS = [
    ("01", "Quoting",
     "Rates rebuilt by hand for every enquiry, across carriers that publish nothing in a common format."),
    ("02", "Track and trace",
     "Status chased by email and phone, then retyped into the TMS so the customer can be told."),
    ("03", "Documents and exceptions",
     "Every mismatch escalates to a person, because the system that spots it cannot resolve it."),
]

RIGHT_HEAD = "Who has it, and why it persists"
RIGHT_ROWS = [
    ("·", "Freight forwarders across DACH and Benelux",
     "213 companies in the beachhead, 1,479 in the full ICP. A named, finite list."),
    ("·", "The substitute is headcount, not software",
     "They add people when volume grows, because there is nothing on the market that does the work."),
    ("·", "So cost scales with volume",
     "The margin problem gets worse exactly when the business gets better."),
]

FIGURE = "€3.4bn"
FIG_LABELS = ["PER YEAR", "SQRLANE ANALYSIS"]   # the second one names whose number it is
PANEL_LEAD = "That is the annual labour value of the work being done by hand across the European market."
PANEL_NOTE = ("We are not displacing a competing tool. We are displacing spreadsheets and hours "
              "— a harder sale to start, and a far larger one to finish.")
FOOT_KICKER = "THE STATUS QUO IS MANUAL, AND IT IS EXPENSIVE"
PAGE_NUM = "01 / 08"
WORDMARK = "SQRlane"

# Tracking on the caps micro-labels, matched to the reference.
MICRO_TRACK = tracking_for("PER YEAR", MICRO_SIZE, 400, 58.6)
PAGE_TRACK = tracking_for(PAGE_NUM, PAGE_SIZE, 400, 42.7)

# ------------------------------------------------------------------- fit rules
# (label, text, size, weight, x, right edge). The build fails if any overruns.
checks: list[tuple[str, str, float, int, float, float]] = []


def check(label, text, size, weight, x, right, tracking=0.0):
    checks.append((label, text, size, weight, x, right, tracking))


# ----------------------------------------------------------------- SVG helpers
parts: list[str] = []


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(el_id, s, x, y, size, weight, fill, tracking=0.0, anchor=None):
    attrs = [
        f'id="{el_id}"', f'x="{x:g}"', f'y="{y:g}"',
        f'font-family="{FAMILY}"', f'font-size="{size:g}"',
        f'font-weight="{weight}"', f'fill="{fill}"',
    ]
    if tracking:
        attrs.append(f'letter-spacing="{tracking:.3f}"')
    if anchor:
        attrs.append(f'text-anchor="{anchor}"')
    parts.append(f'  <text {" ".join(attrs)}>{esc(s)}</text>')


def rect(el_id, x, y, w, h, fill, rx=None):
    r = f' rx="{rx:g}"' if rx else ""
    parts.append(f'  <rect id="{el_id}" x="{x:g}" y="{y:g}" width="{w:g}" '
                 f'height="{h:g}"{r} fill="{fill}"/>')


def open_g(el_id):
    parts.append(f' <g id="{el_id}">')


def close_g():
    parts.append(" </g>")


# ---------------------------------------------------------------------- build
parts.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
    f'viewBox="0 0 {W} {H}" fill="none">'
)
parts.append(
    "  <!-- SQRlane - the problem slide, 1920x1080. Editable SVG: every line is a\n"
    "       live text layer, every rule a rectangle, every layer named. Set in\n"
    "       Geist, which Figma carries in its Google Fonts library. Regenerate\n"
    "       with: python3 tools/build_problem_slide.py -->"
)
rect("background", 0, 0, W, H, PAPER)

# --- brand, top right ------------------------------------------------------
MARK = 38.0
GAP = 14.0
BRAND_SIZE, BRAND_WEIGHT = 26.0, 600
BRAND_TRACK = -0.02 * BRAND_SIZE
wm_w = measure(WORDMARK, BRAND_SIZE, BRAND_WEIGHT, BRAND_TRACK)
mark_x = MR - (MARK + GAP + wm_w)
mark_y = 36.0
open_g("brand")
rect("brand-mark", mark_x, mark_y, MARK, MARK, INK, rx=8)
# Three bars - the lane glyph the product already uses. The nav mark sets a
# 20-unit glyph inside 16px, centred in a 28px tile; keep that inset, or the
# bars grow to fill the tile and close up into a solid block.
glyph = MARK * (16.0 / 28.0)
s = glyph / 20.0
ox, oy = mark_x + (MARK - glyph) / 2.0, mark_y + (MARK - glyph) / 2.0
bars = [(3.2, 14, 13.6), (3.2, 10, 8.6), (3.2, 6, 4.6)]
d = " ".join(f"M{ox + bx * s:.2f} {oy + by * s:.2f}h{bw * s:.2f}" for bx, by, bw in bars)
parts.append(f'  <path id="brand-lanes" d="{d}" stroke="{PAPER}" '
             f'stroke-width="{2.1 * s:.2f}" stroke-linecap="round"/>')
text("brand-wordmark", WORDMARK, mark_x + MARK + GAP, mark_y + 28.0,
     BRAND_SIZE, BRAND_WEIGHT, INK, BRAND_TRACK)
close_g()

# --- title + subtitle ------------------------------------------------------
open_g("title")
for i, line in enumerate(TITLE):
    y = TITLE_BASE + i * TITLE_LEAD
    text(f"title-line-{i + 1}", line, ML, y, TITLE_SIZE, 400, INK)
    check(f"title line {i + 1}", line, TITLE_SIZE, 400, ML, mark_x - 40)
close_g()

text("subtitle", SUBTITLE, ML, SUB_BASE, SUB_SIZE, 400, MUTED)
check("subtitle", SUBTITLE, SUB_SIZE, 400, ML, MR)

rect("divider", ML, RULE_Y, MR - ML, 1, INK)

# --- the two columns -------------------------------------------------------
for side, col_x, ind_x, head, rows in (
    ("left", COL_L, IND_L, LEFT_HEAD, LEFT_ROWS),
    ("right", COL_R, IND_R, RIGHT_HEAD, RIGHT_ROWS),
):
    right_edge = col_x + COL_W
    open_g(f"column-{side}")
    text(f"{side}-heading", head, col_x, HEAD_BASE, HEAD_SIZE, 600, INK)
    check(f"{side} heading", head, HEAD_SIZE, 600, col_x, right_edge)
    rect(f"{side}-heading-rule", col_x, HEAD_RULE_Y, COL_W, 2, INK)
    for y in ROW_SEPS:
        rect(f"{side}-row-rule-{y:.0f}", col_x, y, COL_W, 1, HAIRLINE)

    for i, (marker, row_title, body) in enumerate(rows):
        ty = ROW_TITLE_BASE + i * ROW_STEP
        by = ROW_BODY_BASE + i * ROW_STEP
        open_g(f"{side}-row-{i + 1}")
        text(f"{side}-row-{i + 1}-marker", marker, col_x, ty, ROW_TITLE_SIZE, 600, INK)
        text(f"{side}-row-{i + 1}-title", row_title, ind_x, ty, ROW_TITLE_SIZE, 400, INK)
        text(f"{side}-row-{i + 1}-body", body, ind_x, by, ROW_BODY_SIZE, 400, MUTED)
        check(f"{side} row {i + 1} title", row_title, ROW_TITLE_SIZE, 400, ind_x, right_edge)
        check(f"{side} row {i + 1} body", body, ROW_BODY_SIZE, 400, ind_x, right_edge)
        close_g()
    close_g()

# --- headline figure + panel ----------------------------------------------
open_g("figure")
text("figure-value", FIGURE, ML, FIG_BASE, FIG_SIZE, 400, INK)
check("figure", FIGURE, FIG_SIZE, 400, ML, PANEL_X - 16)
for i, label in enumerate(FIG_LABELS):
    y = 983.6 + i * 17.4
    text(f"figure-label-{i + 1}", label, ML, y, MICRO_SIZE, 400, MUTED, MICRO_TRACK)
    check(f"figure label {i + 1}", label, MICRO_SIZE, 400, ML, PANEL_X - 16, MICRO_TRACK)
close_g()

open_g("panel")
rect("panel-fill", PANEL_X, PANEL_Y, MR - PANEL_X, PANEL_H, PANEL)
panel_text_x = PANEL_X + PANEL_PAD
text("panel-lead", PANEL_LEAD, panel_text_x, LEAD_BASE, LEAD_SIZE, 600, INK)
text("panel-note", PANEL_NOTE, panel_text_x, NOTE_BASE, NOTE_SIZE, 400, MUTED)
check("panel lead", PANEL_LEAD, LEAD_SIZE, 600, panel_text_x, MR - PANEL_PAD)
check("panel note", PANEL_NOTE, NOTE_SIZE, 400, panel_text_x, MR - PANEL_PAD)
close_g()

# --- footer ----------------------------------------------------------------
open_g("footer")
text("footer-kicker", FOOT_KICKER, ML, FOOT_BASE, MICRO_SIZE, 400, MUTED,
     tracking_for(FOOT_KICKER, MICRO_SIZE, 400, 311.7))
text("footer-page", PAGE_NUM, MR, FOOT_BASE, PAGE_SIZE, 400, MUTED, PAGE_TRACK, anchor="end")
close_g()

parts.append("</svg>")

# ------------------------------------------------------------------ fit gate
failures = []
for label, s, size, weight, x, right, tracking in checks:
    end = x + measure(s, size, weight, tracking)
    if end > right:
        failures.append(f"  {label}: ends at {end:.1f}, box ends at {right:.1f} "
                        f"(over by {end - right:.1f}px)\n      {s!r}")

if failures:
    print("Text does not fit its box:\n" + "\n".join(failures), file=sys.stderr)
    raise SystemExit(1)

OUT.write_text("\n".join(parts) + "\n", encoding="utf-8")
widest = max((x + measure(s, size, w, t)) - x for _, s, size, w, x, _, t in checks)
print(f"Wrote {OUT.relative_to(ROOT)}  ({OUT.stat().st_size:,} bytes)")
print(f"{len(checks)} strings measured, all inside their boxes "
      f"(widest line {widest:.0f}px).")
