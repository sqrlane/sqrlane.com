# The SQRlane deck

Investment deck. **SVG only, one file per slide, 1920×1080.** No PPTX.

> **Starting a fresh session?** Point Claude Code at this file:
> *"Read `deck/README.md`, then build slide N — <what it argues>."*
> Everything needed to match the existing slides is here.

---

## Build and preview

```bash
cd deck
python3 build_slide_04.py          # writes slide-04-the-how-1.svg
python3 render.py slide-04-the-how-1.svg   # writes ...-preview.png at 2x
```

`render.py` shells out to a headless Chrome. It finds one itself — a bundled
Playwright build, else Chrome/Chromium/Edge on `PATH` or in the usual install
location — so it runs on a laptop as well as in the sandbox. `python3 render.py
--which` prints the browser it picked, and `DECK_CHROME=/path/to/chrome`
overrides the search. **Its one non-obvious job:** the
headless viewport is 87px shorter than `--window-size`, so it over-sizes the
window and crops back. Without that the bottom 87px of every slide is silently
missing from the preview — which hid a clipped footer for two rounds.

Always render and *look* at the result. Text overflowing a card does not raise.
The tool cannot tell you everything: it once reported ten successful renders
having written nothing at all, because Chrome exits 0 when it cannot write the
screenshot and the previous PNG was still sitting there. It now checks the file
was written *on this run*, but the habit is the real guard — the previews had
been stale for ten commits and every render said it had worked.

---

## The design system

`deckkit.py` holds it. Tokens are lifted verbatim from `static/index.html`, so
the deck and the product are one visual system — never invent a token, and if
the product's change, change them here too.

| | |
|---|---|
| Canvas | `W 1920 · H 1080 · M 96` margin, `CW 1728` content width |
| Surfaces | `BG #fafafa` · `CARD #fff` · `SURFACE #f2f2f2` · `SURFACE_2 #ebebeb` |
| Ink | `FG #171717` · `MUTED #4d4d4d` · `FAINT #8f8f8f` |
| Borders | `BORDER #00000014` · `BORDER_STRONG #00000024` |
| State | `AMBER #96580a` + `AMBER_BG #fdf3e3` · `RED #ea001d` · green `#0f7b3f`/`#e7f5ec` · blue `#006bff`/`#e8f1ff` |
| Radii | `R 6` controls · `RMD 12` cards |
| Type | Geist Sans + Geist Mono, embedded per slide so each SVG is self-contained |

**Colour is spent only on state.** `AMBER` means *this is where the pressure
lands* and nothing else. A second meaning for amber breaks every slide at once.

### Type scale, as used

| Role | Size / weight |
|---|---|
| Headline | 50–52 / 600, `ls -1.4` |
| Subline | 17 / 400 `MUTED` |
| Section head in a card | 19–24 / 600 |
| Big number | 34–48 / 600, `ls -1.2`, `cls="num"` |
| Body | 12.5–13.5 / 400 |
| Band label | 10 / 700, `ls 1.4`, `FAINT` — uppercase |
| Source line | 10.5 / 400 `FAINT`, `cls="mono"` |

### Layout conventions

- **One grid per slide.** Pick column widths once and reuse them on every row.
  Slide 04 is `830 / 24 / 870`; misaligned rows are the most common defect.
- **Cards that sit side by side need matching top structure.** If one has a
  window chrome band, give the other a header band of the same height.
- Header rule at `y=200`. Closing statement ~`y=900`. Footer rule `1008`,
  footer text `1036`.
- App mock windows: 34–38px chrome band, three grey dots or a breadcrumb.

---

## House rules

These are not style preferences. Breaking them is how the deck loses an
investor.

1. **Never invent a metric.** No traction, accuracy or performance claim about
   SQRlane anywhere. Every figure is either a cited third-party number or a
   count from a real run.
2. **Derived numbers show their arithmetic** in the source line, and say they
   are derived. `€34k avg salary × 40% · SalaryExpert` beats a bare €13,600.
3. **Assumptions are labelled on the slide**, in an `assumed` chip.
4. **`LIVE` / `SCRIPTED` / `DEMO` tags travel with every Worker.** Three agents
   are real; nine replay authored data; the TMS connector contacts nothing.
5. **No em dashes** in slide copy.
6. **Less text, more structure.** If a sentence restates what the layout
   already shows, cut the sentence.
7. **Read every caption cold.** If a number needs explaining to someone who
   wrote it, it fails. This caught `1880` and `a year, typed`.

---

## Adding a slide

```python
#!/usr/bin/env python3
"""Slide NN - SECTION.  Emits deck/slide-NN-name.svg.  What it argues, and why."""
from deckkit import *

s = Slide()
s.header("NN — SECTION", "The claim, in one line.", "The support, in one more.")

s.card(M, 226, CW, 400)
s.text(M + 26, 266, "BAND LABEL", 10, 700, FAINT, ls=1.4)
s.raw(f'<text x="{M+26}" y="330" font-size="44" font-weight="600" fill="{FG}" '
      f'letter-spacing="-1.2" class="num">42</text>')

s.text(M, 906, "The closing line.", 24, 600, FG, ls=-0.5)
s.footer("NN / SECTION")
s.write("slide-NN-name.svg")
```

`Slide` methods: `text · card · line · raw · band_label · header · footer ·
chip · write`. Geometry is always explicit so a layout can be read off the code.

---

## The files

| | |
|---|---|
| `deckkit.py` | tokens, embedded fonts, primitives. The template. |
| `render.py` | SVG → 2× PNG, with the Chromium viewport fix |
| `build_slide_01..05.py` | one per slide; all import `deckkit` |
| `build_slide_a1..a3.py` | the lab-notes appendix: the practice world, the TabPFN exam, the live read |
| `CONTENT.md` | slide index, the sourced number bank, what each slide argues |
| `SOURCES.md` | ~70 candidate signal sources by family, and the phase-two six |

### Slides, and what each argues

| Slide | Argues |
|---|---|
| 01 Introduction | A forwarder's product is a date; four things take it |
| 02 The What | Two problems: the work is manual, nothing watches the route |
| 03 The Why | €4bn of desk work, and a seam neither category crosses |
| 04 The How 1/2 | Answers problem one: the desk work does itself |
| 05 The How 2/2 | Answers problem two: know early, while options still exist |
| A1–A3 Lab notes | Appendix, one idea per slide: the grading problem and the practice world · TabPFN's win, status quo vs. after · the first full live read |

**Each How slide answers one of slide 02's two problems by name.** That pairing
is the spine of the deck. If a How slide stops answering its problem, it has
drifted — that exact drift happened once and needed a rebuild to fix.

### Reusing the product's own geometry

Slide 05's map is not drawn by hand. The coastline is read at build time from
the `COAST` constant in `static/index.html`, the lanes are the corridor chains
in `data/geo.json`, and the ports are their real coordinates. Prefer this
wherever the product already holds the data — two hand-drawn versions of the
same thing drift apart.
