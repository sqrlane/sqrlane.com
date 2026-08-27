#!/usr/bin/env python3
"""
Slide 05 - THE HOW (the agents).  Emits deck/slide-05-the-agents.svg.

One argument: the model is used for exactly two things - reading prose and
making a call it then has to justify. Everything else is arithmetic. The
repeating three-row structure (MODEL / CODE / GUARD RAIL) is what carries it,
and the guard-rail row is the one a competitor cannot fill in.

Grounded in the source, not the docs:
  route_advisor.cost_of()  - four real cost terms, summed in code
  route_advisor.advise()   - refuses a route it did not offer
  comms_agent._find_internal_leaks() / _find_placeholders()
  tms._gated()             - the gate applied in exactly one place
The SHP-002 figures are printed by a real run, not authored here.
"""
from deckkit import *

GREEN, GREEN_BG = "#0f7b3f", "#e7f5ec"

s = Slide()
s.header("05 — THE HOW",
         "The model decides. The code does the maths.",
         "It reads prose and makes the call. Chokepoints, days, money and dates are computed, never asked.")

AY, AH, AW, AG = 222, 478, 408, 32


def agent(i, name, tag, tag_col, tag_bg, question, model, code, guard, produces):
    x = M + i * (AW + AG)
    s.card(x, AY, AW, AH)
    tx = x + 26
    s.text(tx, AY + 42, name, 18, 600, FG, ls=-0.2)
    s.chip(x + AW - 26 - 62, AY + 26, 62, 22, tag, fs=9.5, fill=tag_bg, col=tag_col, weight=700)
    s.text(tx, AY + 68, question, 13, 400, MUTED)
    s.line(tx, AY + 90, x + AW - 26, AY + 90, BORDER)

    for label, lines, y0 in (("MODEL", model, 118), ("CODE", code, 192), ("GUARD RAIL", guard, 284)):
        s.text(tx, AY + y0, label, 9.5, 700, AMBER if label == "GUARD RAIL" else FAINT, ls=1.3)
        for j, ln in enumerate(lines):
            s.text(tx, AY + y0 + 22 + j * 18, ln, 12.5, 400,
                   FG if label == "GUARD RAIL" else MUTED)

    s.line(tx, AY + 386, x + AW - 26, AY + 386, BORDER)
    s.text(tx, AY + 414, "PRODUCES", 9.5, 700, FAINT, ls=1.3)
    s.text(tx, AY + 440, produces, 12, 500, FG, cls="mono")


agent(0, "Risk Monitor", "LIVE", GREEN, GREEN_BG, "What just changed?",
      ["Reads prose from 31 news sources", "and classifies what moves a lane."],
      ["Thresholds every number. A gust, a wave,", "a magnitude, a water level become",
       "a severity and a delay range."],
      ["No source is load-bearing. A slow feed is", "skipped, never fatal. Context sources",
       "can never raise an event."],
      "events · chokepoint · severity")

agent(1, "Route Advisor", "LIVE", GREEN, GREEN_BG, "Does it matter to this booking?",
      ["Picks the option and explains", "the choice."],
      ["Maps chokepoints, adds transit days,", "prices every option in euros,",
       "shifts the ETA."],
      ["A route it was not offered is refused", "and downgraded to hold. No risk on",
       "the route means no model call at all."],
      "reroute / hold / on plan · 9-step trail")

agent(2, "Comms Agent", "LIVE", GREEN, GREEN_BG, "Who needs to know?",
      ["Writes two emails, in two calls,", "in two different voices."],
      ["Builds the facts both emails", "are made from."],
      ["Scans customer text for internal route", "codes and unfilled placeholders,",
       "and warns the human."],
      "2 drafts · DRAFT - not sent")

agent(3, "TMS Link", "DEMO", MUTED, SURFACE, "Where does it land?",
      ["Nothing. No model call is made here."],
      ["Turns each output into a field change", "on the record it came from."],
      ["The gate is applied in one place,", "so no operation can skip it."],
      "12 changes · QUEUED - not written")

# =========================================================================
# The decision, priced. Arithmetic beats adjectives.
# =========================================================================
BY, BH = 728, 176
s.card(M, BY, CW, BH, fill=CARD, stroke=BORDER_STRONG)
s.text(M + 28, BY + 34, "ONE DECISION, PRICED", 10, 700, FAINT, ls=1.4)
s.text(M + 236, BY + 34, "SHP-002 · refrigerated pharma · Ningbo → Hamburg · 1 day of slack",
       11.5, 400, FAINT)

BAR_X, BAR_MAX, TOP = M + 250, 700, 234420
for i, (label, val, parts) in enumerate((
        ("Reroute via Cape", 234420, "€3,420 premium  +  14d late × €14,000  +  €35,000 breach"),
        ("Hold", 91000, "4d late × €14,000  +  €35,000 breach"))):
    y = BY + 74 + i * 62
    s.text(M + 28, y + 4, label, 15, 600, FG)
    w = BAR_MAX * val / TOP
    s.card(BAR_X, y - 14, w, 24, fill=AMBER if i == 0 else SURFACE_2, stroke="none", rx=4)
    s.raw(f'<text x="{BAR_X+w+16}" y="{y+5}" font-size="20" font-weight="600" fill="{FG}" '
          f'class="num">€{val:,}</text>')
    s.text(BAR_X, y + 26, parts, 11.5, 400, FAINT, cls="mono")

s.line(W - M - 400, BY + 30, W - M - 400, BY + BH - 30, BORDER)
s.text(W - M - 360, BY + 78, "Hold is €143,420", 22, 600, FG, ls=-0.5)
s.text(W - M - 360, BY + 104, "cheaper.", 22, 600, FG, ls=-0.5)
s.text(W - M - 360, BY + 136, "Not a hedge. Arithmetic.", 12.5, 400, MUTED)

# =========================================================================
s.text(M, 942, "Nine more Workers replay authored data and are tagged SCRIPTED on screen: "
               "rate, milestones, docs, inbox, RFQ, booking, invoice, customs, assistant.",
       12.5, 400, FAINT)
s.footer("05 / THE AGENTS")
s.write("slide-05-the-agents.svg")
