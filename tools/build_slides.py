#!/usr/bin/env python3
"""Build the deck's slides as editable SVGs, sized for Figma.

Why a generator and not hand-written SVG: SVG text does not wrap. A line that
outgrows its column does not reflow, it silently runs into the next one - and
nobody sees it until the file is open in Figma. So every string here is measured
against the real Geist metrics in static/fonts/ and the build FAILS if one
overruns its box. That is the same discipline tools/build_pitch_pptx.js applies
to the PowerPoint, for the same reason: a layout fault that no validator catches.

The geometry is lifted from the reference deck (1920x1080, 48px margins, two
884px columns). The type is Geist, which the rest of the product already uses -
measured against the reference it sits within ~2% at weight 400.

    python3 tools/build_slides.py

Writes one editable SVG per slide into static/assets/, and static/pitch.html -
the same slides inlined into a browsable deck. The page is generated from these
objects rather than hand-written so the deck and the Figma files cannot drift:
change the copy here and both move together.
"""

import re
import sys
import xml.dom.minidom as minidom
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parent.parent
FONT = ROOT / "static" / "fonts" / "Geist-Variable.woff2"
ASSETS = ROOT / "static" / "assets"
LOOP_SRC = ASSETS / "sqrlane-loop.svg"
PAGE = ROOT / "static" / "pitch.html"

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


def wrap(text: str, width: float, size: float, weight: int) -> list[str]:
    """Greedy line break on real metrics, so copy edits cannot overrun a box."""
    lines: list[str] = []
    line = ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and measure(trial, size, weight) > width:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    return lines


# --------------------------------------------------------------------- palette
# Sampled out of the reference deck. The greys are very slightly warm (blue is a
# few steps down) - that is what the reference uses, so it is what we use.
INK = "#000000"
MUTED = "#797972"
HAIRLINE = "#DDDDD6"
PANEL = "#EFEFED"
PAPER = "#FFFFFF"

# One family, no CSS fallback stack. Figma imports a comma-separated stack as a
# single literal font name and reports it missing on every layer; a bare name
# resolves cleanly, and Geist is in Figma's Google Fonts library.
FAMILY = "Geist"

# ------------------------------------------------------------ shared geometry
W, H = 1920, 1080
ML, MR = 48.0, 1872.0
COL_L, COL_R = 48.0, 988.0          # column left edges
COL_W = 884.0                       # column width -> right edges 932 / 1872
IND_L, IND_R = 115.5, 1055.8        # text indent inside each column
ROW_STEP = 88.0                     # baseline-to-baseline between list rows

TITLE_SIZE, TITLE_LEAD, TITLE_BASE = 58.9, 63.4, 88.0
SUB_SIZE, SUB_BASE = 24.6, 264.0
RULE_Y = 301.0
HEAD_SIZE, HEAD_BASE, HEAD_RULE_Y = 24.6, 355.5, 373.0
ROW_TITLE_SIZE, ROW_TITLE_BASE = 21.0, 431.4
ROW_BODY_SIZE, ROW_BODY_BASE = 17.3, 460.9
SEP_BASE = 482.0                    # first row separator; +ROW_STEP thereafter
MICRO_SIZE = 12.4
FOOT_BASE, PAGE_SIZE = 1034.4, 13.1
BAND_BOTTOM = 1005.0          # content floor; the footer sits below it

MARK, MARK_GAP = 38.0, 14.0
BRAND_SIZE, BRAND_WEIGHT = 26.0, 600

MICRO_TRACK = tracking_for("PER YEAR", MICRO_SIZE, 400, 58.6)
PAGE_TRACK = tracking_for("01 / 08", PAGE_SIZE, 400, 42.7)


# ------------------------------------------------------------------ SVG output

def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Slide:
    """One 1920x1080 artboard. Collects markup and the strings to fit-check."""

    def __init__(self, name: str, note: str):
        self.name, self.note = name, note
        self.parts: list[str] = []
        self.checks: list[tuple] = []

    # -- primitives ---------------------------------------------------------
    def text(self, el_id, s, x, y, size, weight, fill, tracking=0.0, anchor=None):
        attrs = [f'id="{el_id}"', f'x="{x:g}"', f'y="{y:g}"',
                 f'font-family="{FAMILY}"', f'font-size="{size:g}"',
                 f'font-weight="{weight}"', f'fill="{fill}"']
        if tracking:
            attrs.append(f'letter-spacing="{tracking:.3f}"')
        if anchor:
            attrs.append(f'text-anchor="{anchor}"')
        self.parts.append(f'  <text {" ".join(attrs)}>{esc(s)}</text>')

    def rect(self, el_id, x, y, w, h, fill, rx=None):
        r = f' rx="{rx:g}"' if rx else ""
        self.parts.append(f'  <rect id="{el_id}" x="{x:g}" y="{y:g}" width="{w:g}" '
                          f'height="{h:g}"{r} fill="{fill}"/>')

    def raw(self, markup: str):
        self.parts.append(markup)

    def group(self, el_id):
        return _Group(self, el_id)

    def check(self, label, s, size, weight, x, right, tracking=0.0):
        self.checks.append((label, s, size, weight, x, right, tracking))

    # -- shared furniture ---------------------------------------------------
    def brand(self):
        """The product mark, top right, where the reference puts its logo."""
        track = -0.02 * BRAND_SIZE
        wm_w = measure("SQRlane", BRAND_SIZE, BRAND_WEIGHT, track)
        x, y = MR - (MARK + MARK_GAP + wm_w), 36.0
        with self.group("brand"):
            self.rect("brand-mark", x, y, MARK, MARK, INK, rx=8)
            # Three bars - the lane glyph the product already uses. The nav mark
            # sets a 20-unit glyph inside 16px, centred in a 28px tile; keep that
            # inset, or the bars grow to fill the tile and close into a block.
            glyph = MARK * (16.0 / 28.0)
            s = glyph / 20.0
            ox, oy = x + (MARK - glyph) / 2.0, y + (MARK - glyph) / 2.0
            bars = [(3.2, 14, 13.6), (3.2, 10, 8.6), (3.2, 6, 4.6)]
            d = " ".join(f"M{ox + bx * s:.2f} {oy + by * s:.2f}h{bw * s:.2f}"
                         for bx, by, bw in bars)
            self.raw(f'  <path id="brand-lanes" d="{d}" stroke="{PAPER}" '
                     f'stroke-width="{2.1 * s:.2f}" stroke-linecap="round"/>')
            self.text("brand-wordmark", "SQRlane", x + MARK + MARK_GAP, y + 28.0,
                      BRAND_SIZE, BRAND_WEIGHT, INK, track)
        return x

    def masthead(self, title_lines, subtitle) -> float:
        """Title, subtitle and the divider. Returns the divider's y.

        A short title pulls everything under it up by whole title lines - that
        is what the reference does (its two-line slides sit exactly 63.4px
        higher), and it is why the divider's y is returned rather than fixed.
        """
        shift = (3 - len(title_lines)) * TITLE_LEAD
        brand_x = self.brand()
        with self.group("title"):
            for i, line in enumerate(title_lines):
                self.text(f"title-line-{i + 1}", line, ML, TITLE_BASE + i * TITLE_LEAD,
                          TITLE_SIZE, 400, INK)
                self.check(f"title line {i + 1}", line, TITLE_SIZE, 400, ML, brand_x - 40)
        self.text("subtitle", subtitle, ML, SUB_BASE - shift, SUB_SIZE, 400, MUTED)
        self.check("subtitle", subtitle, SUB_SIZE, 400, ML, MR)
        rule_y = RULE_Y - shift
        self.rect("divider", ML, rule_y, MR - ML, 1, INK)
        return rule_y

    def column(self, side, col_x, ind_x, head, rows):
        """A headed column of numbered rows - the reference's core structure."""
        right = col_x + COL_W
        with self.group(f"column-{side}"):
            self.text(f"{side}-heading", head, col_x, HEAD_BASE, HEAD_SIZE, 600, INK)
            self.check(f"{side} heading", head, HEAD_SIZE, 600, col_x, right)
            self.rect(f"{side}-heading-rule", col_x, HEAD_RULE_Y, COL_W, 2, INK)
            for i in range(len(rows) - 1):
                self.rect(f"{side}-row-rule-{i + 1}", col_x,
                          SEP_BASE + i * ROW_STEP, COL_W, 1, HAIRLINE)
            for i, (marker, row_title, body) in enumerate(rows):
                ty, by = ROW_TITLE_BASE + i * ROW_STEP, ROW_BODY_BASE + i * ROW_STEP
                with self.group(f"{side}-row-{i + 1}"):
                    self.text(f"{side}-row-{i + 1}-marker", marker, col_x, ty,
                              ROW_TITLE_SIZE, 600, INK)
                    self.text(f"{side}-row-{i + 1}-title", row_title, ind_x, ty,
                              ROW_TITLE_SIZE, 400, INK)
                    self.text(f"{side}-row-{i + 1}-body", body, ind_x, by,
                              ROW_BODY_SIZE, 400, MUTED)
                    self.check(f"{side} row {i + 1} title", row_title,
                               ROW_TITLE_SIZE, 400, ind_x, right)
                    self.check(f"{side} row {i + 1} body", body,
                               ROW_BODY_SIZE, 400, ind_x, right)

    def footer(self, kicker, index: int, total: int):
        """The kicker and the page number.

        The number is derived from the deck, never typed: a hard-coded "01 / 08"
        on a two-slide deck is wrong the moment a slide is added or dropped, and
        it is the kind of wrong nobody notices until it is on a projector.
        """
        page = f"{index:02d} / {total:02d}"
        with self.group("footer"):
            self.text("footer-kicker", kicker, ML, FOOT_BASE, MICRO_SIZE, 400, MUTED,
                      tracking_for(kicker, MICRO_SIZE, 400,
                                   measure(kicker, MICRO_SIZE, 400) * 1.055))
            self.text("footer-page", page, MR, FOOT_BASE, PAGE_SIZE, 400, MUTED,
                      PAGE_TRACK, anchor="end")

    # -- emit ---------------------------------------------------------------
    def validate(self) -> None:
        """Fail the build if any string runs past the box it was placed in."""
        failures = []
        for label, s, size, weight, x, right, tracking in self.checks:
            end = x + measure(s, size, weight, tracking)
            if end > right:
                failures.append(
                    f"  [{self.name}] {label}: ends at {end:.1f}, box ends at "
                    f"{right:.1f} (over by {end - right:.1f}px)\n      {s!r}")
        if failures:
            print("Text does not fit its box:\n" + "\n".join(failures), file=sys.stderr)
            raise SystemExit(1)

    def body(self) -> str:
        """Everything inside the <svg>, background first."""
        return (f'  <rect id="background" x="0" y="0" width="{W}" height="{H}" '
                f'fill="{PAPER}"/>\n' + "\n".join(self.parts))

    def write(self, path: Path) -> None:
        self.validate()
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
                f'viewBox="0 0 {W} {H}" fill="none">\n  <!-- {self.note} -->')
        path.write_text(head + "\n" + self.body() + "\n</svg>\n", encoding="utf-8")
        print(f"  {path.relative_to(ROOT)}  ({path.stat().st_size:,} bytes, "
              f"{len(self.checks)} strings measured, all inside their boxes)")


class _Group:
    def __init__(self, slide: Slide, el_id: str):
        self.slide, self.id = slide, el_id

    def __enter__(self):
        self.slide.parts.append(f' <g id="{self.id}">')
        return self.slide

    def __exit__(self, *exc):
        self.slide.parts.append(" </g>")
        return False


# --------------------------------------------------------------- the loop art

_loop_cache: tuple | None = None


def _loop() -> tuple[minidom.Document, tuple[float, float, float, float]]:
    """The loop asset, parsed once, with the ink box it actually occupies.

    Read from static/assets/sqrlane-loop.svg rather than copied into this file,
    so the diagram has one source of truth - edit the asset and this slide moves
    with it. Two things are rewritten on the way in:

    · the font, to Geist. The standalone asset is set in Inter because Figma
      ships Inter and the asset travels on its own; a slide carrying two
      typefaces reads as a mistake.
    · nothing else. The diagram's own palette and geometry are left alone.

    The ink box is measured, not hard-coded, because the viewBox is not the
    drawing: the loop sits inside a 1200x360 frame with slack on every side, so
    centring on the frame leaves the diagram visibly off-centre on the slide.
    """
    global _loop_cache
    if _loop_cache is not None:
        return _loop_cache

    doc = minidom.parse(str(LOOP_SRC))
    xs: list[float] = []
    ys: list[float] = []
    for el in doc.getElementsByTagName("*"):
        if el.getAttribute("font-family"):
            el.setAttribute("font-family", FAMILY)
        tag = el.tagName
        if tag == "rect":
            x, y = float(el.getAttribute("x")), float(el.getAttribute("y"))
            xs += [x, x + float(el.getAttribute("width"))]
            ys += [y, y + float(el.getAttribute("height"))]
        elif tag == "path":
            # The asset draws with absolute M/L/Q/Z only, so the numbers in `d`
            # are x,y pairs. A relative command would break this - if the
            # diagram is ever redrawn with one, extend this.
            nums = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", el.getAttribute("d"))]
            xs += nums[0::2]
            ys += nums[1::2]
        elif tag == "text":
            size = float(el.getAttribute("font-size"))
            weight = int(el.getAttribute("font-weight") or 400)
            spacing = el.getAttribute("letter-spacing") or "0"
            track = (float(spacing[:-2]) * size if spacing.endswith("em")
                     else float(spacing.rstrip("px") or 0))
            body = "".join(n.data for n in el.childNodes if n.nodeType == n.TEXT_NODE)
            w = measure(body, size, weight, track)
            x, y = float(el.getAttribute("x")), float(el.getAttribute("y"))
            anchor = el.getAttribute("text-anchor")
            left = x - w / 2 if anchor == "middle" else (x - w if anchor == "end" else x)
            xs += [left, left + w]
            ys += [y - size * 0.78, y + size * 0.22]

    _loop_cache = (doc, (min(xs), min(ys), max(xs), max(ys)))
    return _loop_cache


def loop_ink_height(ink_width: float) -> float:
    """How tall the drawing will be once its ink is `ink_width` wide."""
    _, (x0, y0, x1, y1) = _loop()
    return (y1 - y0) * (ink_width / (x1 - x0))


def loop_markup(ink_x: float, ink_y: float, ink_width: float) -> str:
    """Place the loop so its *ink* starts at (ink_x, ink_y) and spans ink_width."""
    doc, (x0, y0, x1, y1) = _loop()
    scale = ink_width / (x1 - x0)
    root = doc.documentElement
    inner = "".join(
        n.toxml() for n in root.childNodes
        if not (n.nodeType == n.ELEMENT_NODE and n.tagName in ("title", "desc"))
    )
    return (f' <g id="loop" transform="translate({ink_x - x0 * scale:.4g} '
            f'{ink_y - y0 * scale:.4g}) scale({scale:.6g})">{inner}</g>')


# ------------------------------------------------------------------ slide 01

def build_problem(index: int, total: int) -> Slide:
    s = Slide("slide-problem", (
        "SQRlane - the problem, 1920x1080. Editable SVG: every line is a live\n"
        "       text layer, every rule a rectangle, every layer named. Set in Geist,\n"
        "       which Figma carries in its Google Fonts library. Regenerate with:\n"
        "       python3 tools/build_slides.py"))

    s.masthead(
        ["European freight forwarding",
         "still runs on people doing",
         "the data work by hand"],
        "The category has no product problem. It has a labour problem that nobody has "
        "priced — on a lane that will not sit still.")

    # Left: the work itself. Right: what keeps re-triggering it. The pairing is
    # the argument - manual work is only expensive because the world keeps
    # moving the lane it sits on.
    s.column("left", COL_L, IND_L, "What the work actually is", [
        ("01", "Quoting",
         "Rates rebuilt by hand for every enquiry, across carriers that publish nothing "
         "in a common format."),
        ("02", "Track and trace",
         "Status chased by email and phone, then retyped into the TMS so the customer "
         "can be told."),
        ("03", "Documents and exceptions",
         "Every mismatch escalates to a person, because the system that spots it cannot "
         "resolve it."),
    ])

    s.column("right", COL_R, IND_R, "What keeps moving the lane", [
        ("01", "Fuel and cost",
         "Bunker and energy prices move what a reroute is worth, after the routing is "
         "already decided."),
        ("02", "Tariffs and trade policy",
         "Filed on a government register, not announced on a wire. It moves the country "
         "of entry."),
        ("03", "Geopolitics and labour",
         "A strike closes a port for days, a corridor for months. The booking is already "
         "at sea."),
        ("04", "Climate and weather",
         "A gale over the crane, a river too low to float a barge, a wildfire across a "
         "rail leg."),
    ])

    # Headline figure and its panel, sized to the reference's bottom band.
    panel_x, panel_y, panel_h, pad = 255.0, 875.0, 130.0, 26.9
    with s.group("figure"):
        s.text("figure-value", "€3.4bn", ML, 930.0, 56.5, 400, INK)
        s.check("figure", "€3.4bn", 56.5, 400, ML, panel_x - 16)
        # The reference labels its figure only PER YEAR. Ours names whose number
        # it is: this one is our own estimate, and in a deck where every figure
        # cites a source, an unattributed one reads as someone else's.
        for i, label in enumerate(["PER YEAR", "SQRLANE ANALYSIS"]):
            s.text(f"figure-label-{i + 1}", label, ML, 958.0 + i * 17.4,
                   MICRO_SIZE, 400, MUTED, MICRO_TRACK)
            s.check(f"figure label {i + 1}", label, MICRO_SIZE, 400, ML,
                    panel_x - 16, MICRO_TRACK)

    with s.group("panel"):
        s.rect("panel-fill", panel_x, panel_y, MR - panel_x, panel_h, PANEL)
        tx, right = panel_x + pad, MR - pad
        lead = ("That is the annual labour value of the work being done by hand across "
                "the European market.")
        s.text("panel-lead", lead, tx, 917.0, 21.0, 600, INK)
        s.check("panel lead", lead, 21.0, 600, tx, right)
        notes = [
            "We are not displacing a competing tool. We are displacing spreadsheets and "
            "hours — a harder sale to start, and a far larger one to finish.",
            # Ties the two columns together: the lane moving is what turns manual
            # work into a cost, and the cost is what caps the business.
            "The substitute is headcount, not software — so every disruption is paid for "
            "in hours, and the margin gets worse as the business gets better.",
        ]
        # A running cursor, not i*step: a note that wrapped to two lines would
        # otherwise stack both at one baseline and print on top of itself.
        y = 949.0
        for i, note in enumerate(notes):
            for j, line in enumerate(wrap(note, right - tx, 19.0, 400)):
                s.text(f"panel-note-{i + 1}-{j + 1}", line, tx, y, 19.0, 400, MUTED)
                s.check(f"panel note {i + 1}.{j + 1}", line, 19.0, 400, tx, right)
                y += 26.0

    s.footer("MANUAL WORK, ON A LANE THAT WILL NOT SIT STILL", index, total)
    return s


# ------------------------------------------------------------------ slide 02

def build_fix(index: int, total: int) -> Slide:
    s = Slide("slide-fix", (
        "SQRlane - the shape of the fix, 1920x1080. The loop is placed from\n"
        "       static/assets/sqrlane-loop.svg and re-set in Geist; edit the asset,\n"
        "       not this copy. Regenerate with: python3 tools/build_slides.py"))

    rule_y = s.masthead(
        ["Read the booking, watch the lane,",
         "decide — and write it back"],
        "One loop. It opens and closes on the same record, and every action on it waits "
        "for a person.")

    # The diagram's ink is aligned to the text margins, and the whole block -
    # diagram plus its caption - is centred in the band under the rule. Sized
    # this way its smallest labels land near 21px, comfortably above the
    # slide's own 12.4px floor; squeezing the band pushes them under it.
    ink_w = MR - ML
    ink_h = loop_ink_height(ink_w)
    tail = ("Risk, decision, communication and the record — closed in one place, with the "
            "reasoning kept and nothing sent or written until a person approves it.")
    tail_lines = wrap(tail, MR - ML, 19.0, 400)
    gap = 54.0
    block_h = ink_h + gap + (len(tail_lines) - 1) * 26.0
    top = rule_y + (BAND_BOTTOM - rule_y - block_h) / 2

    s.raw(loop_markup(ML, top, ink_w))
    for j, line in enumerate(tail_lines):
        y = top + ink_h + gap + j * 26.0
        s.text(f"tail-{j + 1}", line, ML, y, 19.0, 400, MUTED)
        s.check(f"tail {j + 1}", line, 19.0, 400, ML, MR)

    s.footer("THE LOOP OPENS AND CLOSES IN THE SAME PLACE", index, total)
    return s


# ---------------------------------------------------------------------- main

# ---------------------------------------------------------------- the web deck

_ID = re.compile(r'id="([^"]*)"')


def _scope_ids(markup: str, prefix: str) -> str:
    """Namespace a slide's ids so several can share one HTML document.

    Duplicate ids across slides are invalid HTML and break getElementById; the
    loop asset also carries ids with spaces in them, which an SVG file tolerates
    and an HTML document does not. Only done on the way into the page - the
    standalone SVGs keep their short ids, because those become the Figma layer
    names and `slide-problem--title-line-1` is a worse name than `title-line-1`.
    """
    if "url(#" in markup or 'href="#' in markup:
        raise SystemExit(
            f"{prefix}: markup references an id (a gradient, mask or marker). "
            "Rewrite those references here too, or the page will render blank.")
    return _ID.sub(lambda m: f'id="{prefix}--{"-".join(m.group(1).split())}"', markup)


PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SQRlane \u2014 Pitch</title>
<meta name="description" content="The problem SQRlane solves, and the shape of the fix.">

<!-- GENERATED by tools/build_slides.py - edit that, not this file.

     The slides are the same SVGs that go to Figma, inlined verbatim. They are
     not re-implemented in HTML, so the deck and the design files cannot drift:
     there is one description of each slide and both outputs come from it.

     Geist is self-hosted from static/fonts/. Never a CDN - an external font
     request is one more thing that can fail in a room, and a deck that loses
     its type looks broken. Same rule the other pages hold. -->
<style>
@font-face{
  font-family:"Geist";
  src:url("/fonts/Geist-Variable.woff2") format("woff2-variations"),
      url("/fonts/Geist-Variable.woff2") format("woff2");
  font-weight:100 900; font-style:normal; font-display:swap;
}

:root{
  --paper:#e8e8e5;
  --ink:#000000;
  --muted:#797972;
  --gap:clamp(10px, 2.4vh, 30px);
}

*{box-sizing:border-box; margin:0; padding:0}

body{
  font-family:"Geist", -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  background:var(--paper); color:var(--ink);
  -webkit-font-smoothing:antialiased; text-rendering:optimizeLegibility;
}

/* One slide per screen, snapping. */
.deck{
  height:100svh; overflow-y:scroll; scroll-snap-type:y mandatory;
  scroll-behavior:smooth;
}
.slide{
  height:100svh; scroll-snap-align:start;
  display:flex; align-items:center; justify-content:center;
  padding:var(--gap);
}

/* The artboard is 16:9 and fixed, so it is sized against viewport HEIGHT as
   well as width. Sized against width alone it overruns a 1280x720 projector -
   and under mandatory snapping an overrunning slide is not merely tall, it is
   unreachable, because the snap pulls you off it before you reach the bottom. */
.stage{
  width:min(100%, calc((100svh - var(--gap) * 2) * 16 / 9));
  aspect-ratio:16 / 9;
  background:#fff;
  box-shadow:0 2px 2px rgba(0,0,0,.04), 0 0 0 1px rgba(0,0,0,.07);
}
.stage svg{display:block; width:100%; height:100%}

/* Below a short viewport the deck stops snapping and becomes a document. */
@media (max-height:620px){
  .deck{scroll-snap-type:none; height:auto; overflow:visible}
  .slide{height:auto; min-height:0}
  .stage{width:100%}
}

.bar{
  position:fixed; top:0; left:0; height:2px; background:var(--ink);
  z-index:30; transition:width .25s ease;
}
/* No fixed counter or brand chrome. Each artboard already carries the product
   mark and its own page number, and at 16:9 the stage fills the viewport far
   enough that fixed corners land on top of them. The bar is the only chrome
   that has somewhere to live. */
@media (max-height:620px), (max-width:820px){ .bar{display:none} }

/* Print: one slide per page, chrome off. */
@page{size:A4 landscape; margin:0}
@media print{
  body{background:#fff}
  .deck{height:auto; overflow:visible; scroll-snap-type:none}
  .slide{
    height:100vh; min-height:0; padding:0;
    break-after:page; page-break-after:always;
  }
  .slide:last-child{break-after:auto; page-break-after:auto}
  .stage{width:100%; box-shadow:none}
  .bar{display:none !important}
}
</style>
</head>
<body>

<div class="bar" id="bar"></div>

<main class="deck" id="deck">
__SLIDES__
</main>

<script>
(function () {
  var slides = Array.prototype.slice.call(document.querySelectorAll(".slide"));
  var bar = document.getElementById("bar");
  var i = 0;

  function paint() {
    bar.style.width = ((i + 1) / slides.length * 100) + "%";
  }

  function goTo(n) {
    i = Math.max(0, Math.min(slides.length - 1, n));
    slides[i].scrollIntoView({ behavior: "smooth", block: "start" });
    paint();
  }

  /* Which slide is on screen, so scrolling by hand keeps the counter honest.
     Half the viewport is the threshold - a slide is "current" once most of it
     is showing, which is what a reader would say too. */
  if ("IntersectionObserver" in window) {
    var seen = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { i = slides.indexOf(e.target); paint(); }
      });
    }, { threshold: 0.5 });
    slides.forEach(function (s) { seen.observe(s); });
  }

  document.addEventListener("keydown", function (e) {
    /* Any modifier is the browser's, not ours. */
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    var k = e.key;
    if (k === "ArrowRight" || k === "ArrowDown" || k === "PageDown" || k === " ") {
      e.preventDefault(); goTo(i + 1);
    } else if (k === "ArrowLeft" || k === "ArrowUp" || k === "PageUp") {
      e.preventDefault(); goTo(i - 1);
    } else if (k === "Home") {
      e.preventDefault(); goTo(0);
    } else if (k === "End") {
      e.preventDefault(); goTo(slides.length - 1);
    }
  });

  paint();
})();
</script>
</body>
</html>
"""


def write_page(slides: list[Slide], path: Path) -> None:
    """The same slides, inlined into one browsable deck."""
    blocks = []
    for slide in slides:
        slide.validate()
        art = _scope_ids(slide.body(), slide.name)
        blocks.append(
            f'  <section class="slide" aria-label="{slide.name}">\n'
            f'    <div class="stage">\n'
            f'      <svg viewBox="0 0 {W} {H}" role="img" fill="none" '
            f'xmlns="http://www.w3.org/2000/svg">\n{art}\n      </svg>\n'
            f"    </div>\n  </section>")
    path.write_text(PAGE_TEMPLATE.replace("__SLIDES__", "\n".join(blocks)),
                    encoding="utf-8")
    print(f"  {path.relative_to(ROOT)}  ({path.stat().st_size:,} bytes, "
          f"{len(slides)} slides inlined)")


if __name__ == "__main__":
    print("Building deck slides:")
    builders = [build_problem, build_fix]
    slides = [b(i + 1, len(builders)) for i, b in enumerate(builders)]
    for slide in slides:
        slide.write(ASSETS / f"{slide.name}.svg")
    write_page(slides, PAGE)
