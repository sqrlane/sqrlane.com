# SQRlane — investment deck, content architecture

Slide-by-slide source of truth. Copy here is **final deck copy**, not notes: every line
is written to be set as-is. Layout specs describe the infographic, not decoration.

**Format:** one `.svg` per slide, 1920×1080. No PPTX.
**Design:** pending the reference deck upload. Everything below is design-agnostic —
the layouts are described in structure (columns, bands, node graphs), so they survive
whatever palette and type the reference deck sets.

---

## Rules this deck inherits from the product

1. **Never invent a metric.** No traction, accuracy, or performance claim about SQRlane
   appears anywhere. Every number on a slide is either (a) a cited third-party market or
   industry figure, or (b) a count of what the working prototype actually does.
2. **Sourced numbers carry their source on the slide**, set small. An investor who
   can't see where a figure came from discounts the whole page.
3. **The honesty slide is not a weakness, it is the differentiator.** What is live,
   what is modelled, what is synthetic — stated in our own words before anyone asks.
4. **Never borrow 5U AI's name, colours, taglines or Worker names.**

---

## Number bank — everything quotable, with its source

| Figure | Value | Year | Source |
|---|---|---|---|
| Supply-chain disruption alerts | **26,225** | 2025 | Resilinc EventWatchAI, *Illumination: 2025 Annual Supply Chain Report* |
| Disruption alerts | 22,522 | 2024 | Resilinc EventWatchAI |
| YoY increase in alerts | **+38%** | 2024 vs 2023 | Resilinc |
| Geopolitical risk alerts | +123% | 2024 vs 2023 | Resilinc |
| Regulatory change alerts | +128% | 2024 vs 2023 | Resilinc |
| EBITDA lost to disruption | **~45% of one year's, per decade** | 2025 | McKinsey & Company |
| Direct procurement disruption cost | ~$16M / organisation / year | 2026 | Coupa |
| Red Sea emergency surcharge | $500–1,500 / container | 2024– | Maersk, carrier notices |
| Cape of Good Hope reroute | **+30% transit time**, ~9% effective capacity cut | 2024– | J.P. Morgan Research |
| Freight forwarding & customs businesses, Europe | **163,000** | 2025 | IBISWorld |
| Top-10 forwarder share of global revenue | 35–40% | 2025 | Mordor Intelligence |
| Top-25 global forwarders on CargoWise | **24 of 25** | 2025 | WiseTech Global FY25 |
| WiseTech customers / countries | 17,000 / 181 | 2025 | WiseTech Global FY25 |
| Supply-chain risk management software market | $4.5B – $8.9B | 2025 | Mordor Intelligence (low) / Market Research Future (high) |

> **Deliberately excluded.** The global freight-forwarding market is quoted between
> $166B and $572B (2025) depending on whose definition you take. A range that wide is
> not evidence, it is noise — and we do not capture freight revenue anyway. The deck
> sizes the **software** opportunity bottom-up from business counts instead.

### Prototype facts (counted, not claimed)
60 sources · 6 families · 14 Workers (3 live, 10 scripted, 1 demo connector) ·
7 bookings · 4 scenarios · 8-day simulation · 10 test suites · ~14 model calls per cycle ·
0 emails sent · 0 records written.

---

# SECTION 1 — THE WHAT

## S01 · Cover
**SQRlane**
Trade-lane risk, decided.
`Agents that watch the lane, decide the booking, and do the TMS work.`

*Layout* — Full bleed. Wordmark at optical centre-left. One rule beneath. Bottom band:
date, and a single monospace line `sqrlane.com`. Nothing else.
*Why* — A cover that argues is a cover nobody reads. It states the category and stops.

---

## S02 · The one line
> **Watching, deciding, and doing are three jobs.**
> **Today one person does all three, by hand.**

*Layout* — Type-only slide. The three verbs set as three cells across the width, each
with a small glyph, all three joined by a bracket beneath labelled `one person`.
*Why* — This is the whole deck in nine words. It earns a full slide because every later
slide is a consequence of it.

---

## S03 · The bridge is a human
**Both ends are already software. The middle is a person.**

*Layout* — Three-column structural diagram, the centre column visibly load-bearing.

```
┌── RISK PLATFORMS ────┐   ╔═══ THE DESK ═══╗   ┌── TMS & EXECUTION ───┐
│  Tell you something  │   ║  read          ║   │  Moves the booking   │
│  happened.           │──▶║  decide        ║──▶│  once you've decided.│
│                      │   ║  write         ║   │                      │
│  Everstream          │   ║  re-key        ║   │  CargoWise · Riege   │
│  Interos · Resilinc  │   ╚════════════════╝   │  Descartes · Transp. │
│  ── stops at the alert   ↑ the manual bridge      doesn't watch ──    │
└──────────────────────┘                        └──────────────────────┘
```

Centre column drawn as a plank under load — hairline stress marks, or simply the only
column with weight. Footer, small: *Named systems are the connector's targets. None is
connected.*
*Why* — The competitive frame and the problem statement are the same picture. Showing
them once, together, is worth two slides.

---

## S04 · Where the day goes
**One event. Then the same six steps, once per booking.**

*Layout* — Horizontal timeline, left third; repeating loop, right two-thirds.

- **Left — detection lag.** Three stops on a line: `strike called` → `local source
  carries it` → `international wires` → `someone on the desk reads it`. Gaps drawn to
  scale, unlabelled in hours (we do not claim a number here).
- **Right — the loop.** Six chips in a ring or a run: `open booking` · `check route` ·
  `weigh slack` · `mail carrier` · `mail customer` · `re-key TMS`. Wrapped in a bracket
  labelled **× every booking on the board**.
- One chip — `re-key TMS` — carries visible weight (fill, or a thicker rule).

Caption: *The last step is the one that eats the day. It is also the only one that counts —
a decision that never reaches the TMS is a decision nobody acted on.*
*Why* — Investors under-price re-keying because it sounds clerical. Drawing it as the
heavy step in a loop that repeats per booking is the argument.

---

# SECTION 2 — THE WHY

## S05 · The problem is structural
**Disruption stopped being an event. It became a rate.**

*Layout* — Left: three-bar column chart, alerts by year (2023 ≈ 16.3k derived · 2024
22,522 · 2025 26,225). Right: two delta blocks stacked.

| | |
|---|---|
| **+38%** | alerts, 2024 vs 2023 |
| **+123%** | geopolitical |
| **+128%** | regulatory |

Source line: *Resilinc EventWatchAI, 2024 and 2025 annual reports.*
*Why* — Establishes the market is growing without us claiming anything. The two category
deltas matter more than the total: geopolitical and regulatory are exactly the signals a
news-only monitor reads late and a TMS never reads at all.

---

## S06 · What it costs
**The decision is worth more than the software.**

*Layout* — Four stat blocks, 2×2, descending in scale so the eye lands on the first.

| **~45%** | of one year's EBITDA, lost to disruption over a decade — *McKinsey* |
|---|---|
| **+30%** | transit time on the Cape reroute; ~9% of global container capacity erased — *J.P. Morgan* |
| **$500–1,500** | emergency surcharge, per container — *carrier notices, 2024–* |
| **~$16M** | direct procurement disruption cost, per organisation per year — *Coupa, 2026* |

Footer: *Our worked example turns on a single booking with one day of slack. These are
the stakes on the other side of that call.*
*Why* — Connects the macro number to the micro decision the product actually makes.

---

## S07 · The market, counted from the bottom
**163,000 forwarding businesses in Europe. 25 of them are well served.**

*Layout* — A funnel, but built from counts rather than a percentage guess.

```
  163,000   Freight forwarding & customs businesses, Europe        IBISWorld 2025
            ─────────────────────────────────────────────────
     ~25    Global top-tier — 24 of the top 25 already run CargoWise   WiseTech FY25
            ─────────────────────────────────────────────────
            The top 10 take 35–40% of global revenue.
            The other 60–65% is the long tail — and it is the tail
            that has no risk desk, no data team, and no budget for
            an enterprise SCRM seat.
            ─────────────────────────────────────────────────
  ENTRY     Mid-size DACH / Benelux forwarder, ops-led
```

Beside it, the value pool as a single band: **SCRM software, $4.5–8.9B (2025)** — two
figures, both cited, shown as a range because the definitions differ. Annotate: *We sit
where this market meets the TMS layer. Neither side currently sells into the tail.*
*Why* — A bottom-up count is unfalsifiable in the way a top-down TAM never is, and it
doubles as the go-to-market. The "24 of 25" figure does more work than any TAM: it proves
the top is closed and the tail is open.

---

## S08 · Competition
**Everyone stops one step short.**

*Layout* — 2×2. X: *Watches the world* (no → yes). Y: *Acts on the booking* (no → yes).

- **Bottom-left** — Trade press, portals, spreadsheets. `the default today`
- **Bottom-right** — Everstream · Interos · Resilinc. `alert, then stop` · *enterprise-priced*
- **Top-left** — CargoWise · Riege · Descartes · Transporeon · execution AI. `act after you decide` · *never watches*
- **Top-right** — **SQRlane.** `watch → decide → act → record`

Under the grid, a three-row comparison strip — the only place in the deck with a table:

| | Watches the lane | Decides the booking | Writes to the TMS | Priced for the tail |
|---|---|---|---|---|
| Risk platforms | ✓ | — | — | — |
| TMS / execution | — | — | ✓ | partly |
| **SQRlane** | **✓** | **✓** | **✓** | **✓** |

*Why* — The 2×2 makes the whitespace visual; the strip makes it checkable. One without
the other is either hand-waving or a wall of text.

---

## S09 · Why now
**Three things became true at once.**

*Layout* — Three equal boxes, each with a one-word head, one line, one proof chip.

1. **Public** — The signals went free and keyless. `42 sources · 0 API keys · 0 cost`
2. **Cheap** — Inference fell far enough to read all of them, every run. `~14 model calls per cycle`
3. **Accountable** — A decision can now carry its own reasoning and a human gate. `every action queued, nothing sent`

*Why* — "Why now" is the question that kills decks that skip it. Each of the three is a
fact about the prototype, not a forecast.

---

# SECTION 3 — THE HOW

## S10 · The closed loop  ← **the money slide**
**Risk → decision → communication → the system of record. Closed.**

*Layout* — The architecture, drawn as a ring so the loop reads as a loop. The TMS sits
at the top and is entered **twice** — once as the read, once as the write. That double
entry is the entire product thesis and must be visually unmistakable.

```
                    ┌─────────────────────────┐
             read   │   TMS · system of       │   write-back
        ┌──────────▶│   record                │◀───────────┐
        │           └─────────────────────────┘            │
        │                                                  │
   ┌────┴─────┐   ┌──────────┐   ┌──────────┐   ┌──────────┴┐
   │   RISK   │──▶│  ROUTE   │──▶│  COMMS   │──▶│  APPROVAL │
   │ MONITOR  │   │ ADVISOR  │   │  AGENT   │   │   GATE    │
   │  LIVE    │   │  LIVE    │   │  LIVE    │   │  human    │
   └──────────┘   └──────────┘   └──────────┘   └───────────┘
   42 sources     reroute/hold   carrier +      nothing sent
   6 families     + reasoning    customer       nothing written
```

Every arrow labelled with what travels along it. The gate drawn as an actual gate — the
only element that stops flow.
*Why* — Two claims live or die here: that the loop closes on the same record it opened,
and that a human sits in it. Both are geometry, so draw them.

---

## S11 · The signal layer
**A lane is not moved by news alone.**

*Layout* — Six family columns, source counts as small stacked ticks so 42 is countable
rather than asserted. Beneath, the classification split as a fork.

| Family | n | Reads |
|---|---|---|
| News | 31 | wires, regional broadcasters, trade press |
| River gauges | 3 | Rhine — Kaub, Duisburg, Emmerich |
| Weather & sea state | 3 | port gusts, wave height |
| Natural hazards | 2 | seismic, wildfire, storm |
| Government | 2 | tariff, sanctions, customs filings |
| Reference rates | 1 | what a reroute is billed at |

The fork, set large:
**Prose → the model.**  **Numbers → a threshold.**
`a gust, a wave, a magnitude, a water level — costs nothing, cannot hallucinate`

Footer: *Not one of the 42 is load-bearing. Any source can be down and the run still
completes.*
*Why* — "42 sources" is a claim; six families with counts and a classification rule is
an architecture. And the fork pre-empts the obvious objection — that this is an LLM
guessing at severity.

---

## S12 · What each agent does, and why it exists
**Three live agents. One connector. Each earns its place.**

*Layout* — Four rows. Each: name · tag · one-line job · the input it takes · the artefact
it produces. The artefact column is the important one — every row ends in a *record*, not
a message.

| | Tag | Job | Produces |
|---|---|---|---|
| **TMS link** | `DEMO` | The only door to the book | bookings in · changes out |
| **Risk Monitor** | `LIVE` | Reads 42 sources, classifies what moves a lane | an exception on the booking |
| **Route Advisor** | `LIVE` | Weighs slack vs added transit vs delay | discharge port · routing code · ETA |
| **Comms Agent** | `LIVE` | Writes what a person would have written | two drafts on the communication log |

Sidebar: *Nine further Workers — rate, milestones, docs, inbox, RFQ, booking, invoice,
customs, assistant — replay authored data and are tagged `SCRIPTED` on screen. The tag is
the honesty.*
*Why* — The "why it exists" test is the user's own brief. Each row answers it by naming
the record it changes; anything that couldn't name one would not be in the product.

---

## S13 · Worked example
**One strike. Seven bookings. Three different answers.**

*Layout* — Board strip of 7 cards across the top, colour-coded by outcome. Below, the
one hard call, opened up.

Top strip: `2 reroute` · `1 hold` · `4 on plan`
Caption on the four: *The system does not cry wolf.*

The hard call, drawn as a balance:

```
   SHP-002 · reefer pharma · Ningbo → Hamburg · 1 day slack

   REROUTE                        HOLD
   ├ avoids the strike            ├ 5 days late
   ├ + road transit               ├ against 1 day of slack
   ├ + a cold-chain transfer      └ customer is in Hamburg
   └ customer is still in Hamburg
                    ▼
              HOLD + NOTIFY
   "No good option. This is the least-bad one, and here is why."
```

Add the slack gauge: **100%+ consumed**, exact days beside it.
*Why* — Anyone can show a system taking the easy branch. The centrepiece is the booking
with no good answer — that is the only slide that demonstrates judgement rather than
routing.

---

## S14 · The last mile
**Every decision lands on the booking it came from.**

*Layout* — A single booking record, drawn as a card, with four write-backs docking into
named fields. Each carries its gate chip.

```
  BOOKING SHP-001
  ├── exception_flag ......... Risk Worker      QUEUED · not written
  ├── port_of_discharge ...... Routing Worker   QUEUED · not written
  ├── routing_code / eta ..... Routing Worker   QUEUED · not written
  └── communication_log ×2 ... Comms Worker     DRAFT · not sent
```

Beside it, in the same weight: **A booking left on plan queues nothing.**
*That is an answer, not an omission.*

Bottom band, set as the strongest line on the slide:
**Nothing is sent. Nothing is written. A person approves, or it does not happen.**
*Why* — This is the biggest value in the product *and* the answer to the liability
question every investor asks about agents. Same slide, both jobs.

---

## S15 · What is real, and what is not
**Said before you ask.**

*Layout* — Three columns, plainly labelled, no hedging.

| **REAL** | **MODELLED** | **SYNTHETIC** |
|---|---|---|
| 42 live sources, read on every run | The TMS connector — both directions, one door, derived write-backs | The seven bookings |
| The model makes every decision | | The injected disruption |
| The reasoning is recorded, per booking | *no vendor · no credential · no endpoint* | *so a disruption can be shown on demand* |

Footer: *The gap between this and a business is the integration and trust wall. That is
real work, and it is the next thing we do — not something this deck skips.*
*Why* — Volunteering the boundary is the cheapest credibility in the deck, and a prototype
that mislabels itself loses the room the moment someone probes. It also sets up the ask.

---

# SECTION 4 — THE TEAM

## S16 · Team  ⚠ PLACEHOLDER — awaiting names
**Who is building it.**

*Layout* — Two to four person blocks: name, role, one proof line each. Beneath, a
single band: *why this team, for this problem* — one sentence, not a list.

```
┌ ─ ─ ─ ─ ─ ─ ─ ─ ┐   ┌ ─ ─ ─ ─ ─ ─ ─ ─ ┐
   [ NAME ]              [ NAME ]
   [ ROLE ]              [ ROLE ]
   [ one proof line ]    [ one proof line ]
└ ─ ─ ─ ─ ─ ─ ─ ─ ┘   └ ─ ─ ─ ─ ─ ─ ─ ─ ┘
      dashed = placeholder, cannot be mistaken for real
```

Every placeholder renders in a **dashed** container with bracketed text, so the slide is
visibly unfinished until filled. Nothing invented.
*Why* — A team slide with plausible-looking fiction is worse than an empty one.

**Needed from you:** name · role · one line each of why-this-person-for-this-problem.
Optional: advisors, and one sentence on the founding insight.

---

## S17 · Appendix — the ask *(optional, flagged)*
Not in your four-section skeleton, so it is built but held separately. An investment deck
without an ask usually gets one asked out loud instead. If you want it: amount, runway in
months, and the three things the money buys — stated as milestones, not headcount.

Suggested three, drawn from S15's own gap:
1. **The first real TMS connection** — the write-back, live, on one design partner.
2. **The trust layer** — audit, permissions, and the approval gate as a product surface.
3. **Lane coverage beyond the demo corridors.**

---

## Slide index, as built

| File | Section | Argues |
|---|---|---|
| `slide-01-introduction.svg` | Introduction | A forwarder's product is a date; four things take it |
| `slide-02-the-what.svg` | The What | Two problems: the work is manual, nothing watches the route |
| `slide-03-the-why.svg` | The Why | EUR 4bn of desk work, and a seam neither category crosses |
| `slide-04-the-how-1.svg` | The How 1/2 | Answers problem one: the desk work does itself |
| `slide-05-the-how-2.svg` | The How 2/2 | Answers problem two: know early, while options exist |
| `slide-a1-lab-notes.svg` | Appendix · Lab notes 1/3 | Nobody could grade the calls; a practice world with an answer key fixes that |
| `slide-a2-lab-notes.svg` | Appendix · Lab notes 2/3 | TabPFN wins the exam, status quo vs. after; its lesson ships, not the model |
| `slide-a3-lab-notes.svg` | Appendix · Lab notes 3/3 | The first full live read: 47 of 60 answered, five faults found, four fixed |

Each How slide answers one of slide 02's two problems by name. That pairing is
the spine of the deck; if a How slide stops answering its problem, it has
drifted.

The three appendix slides retell `LAB-NOTES-2026-08-28.md` for a mixed room,
one idea per slide. Every figure on them is counted from our own runs, the
practice-world caveat is printed on the chart itself, and A2 carries the honest
line in a dashed box: TabPFN itself is not in the product, its lesson is.

## Build order once the reference deck lands

1. Extract palette, type scale, grid and any recurring motif from the upload.
2. Build `deck/_tokens.md` — the extracted system, written down before any slide.
3. Render S10, S03, S08 first. They carry the most structure; if the system survives
   those three it survives the rest.
4. Render the remainder, then S16 last, once names arrive.
