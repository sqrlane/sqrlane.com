#!/usr/bin/env python3
"""
Slide 04 - THE JOB (1/2).  Emits deck/slide-04-the-job.svg.

The status quo, on a file where nothing goes wrong.

  the clock       45 days, drawn to scale, the sea leg owning 32 of them
  the web         seven parties, eight stages, a dot per handoff - the
                  repetition IS the job, so the density carries it
  the TMS         what it holds and what it does not do
  the margin      the P&L on one container, ending at EUR 127

All K+N Sea Logistics FY25: CHF 8.8bn net turnover and CHF 585m recurring EBIT
over 4.3M TEU, gross profit backed out of the published 29% conversion rate.
Best-run operator in the industry, so every figure here is generous.
"""
from deckkit import *

GREEN = "#0f7b3f"

s = Slide()
s.header("04 — THE JOB (1/2)",
         "Forty-five days, seven parties, €127.",
         "This is a file where nothing goes wrong. The TMS holds the booking; it does not do the work.")

# =========================================================================
# THE CLOCK, AND THE COORDINATION WEB
# =========================================================================
FY, FH = 218, 396
s.card(M, FY, CW, FH)
s.text(M + 26, FY + 34, "ONE FILE, END TO END", 10, 700, FAINT, ls=1.4)
s.text(M + 240, FY + 34, "Shanghai to Munich", 11.5, 400, FAINT)
s.text(W - M - 26, FY + 34, "45 days", 13, 600, FG, anchor="end", cls="mono")

STAGES = [("Enquiry", 2), ("Quote", 3), ("Book", 2), ("Docs", 2),
          ("In transit", 32), ("Customs", 2), ("Delivery", 1), ("Invoice", 1)]
TX0, TXW = M + 186, CW - 560
UNIT = TXW / 45
x = TX0
for name, days in STAGES:
    w = days * UNIT
    hot = days > 10
    s.card(x + 1.5, FY + 60, w - 3, 20, fill=SURFACE_2 if hot else SURFACE, stroke="none", rx=4)
    if w > 70:
        s.text(x + w / 2, FY + 74, f"{days}d", 10, 600 if hot else 500,
               MUTED if hot else FAINT, anchor="middle", cls="mono")
    x += w
s.text(M + 26, FY + 75, "the clock", 11.5, 500, FG)
s.text(TX0, FY + 100, "opens", 10.5, 400, FAINT)
s.text(TX0 + TXW, FY + 100, "closes", 10.5, 400, FAINT, anchor="end")
s.line(M + 26, FY + 116, W - M - 26, FY + 116, BORDER)

s.text(M + 26, FY + 146, "WHO THE FORWARDER TALKS TO", 10, 700, AMBER, ls=1.4)
s.text(M + 292, FY + 146, "every dot is a mail, a portal login or a call", 11, 400, FAINT)
COLS = [n for n, _ in STAGES]
PARTIES = [("Customer", [1, 1, 1, 1, 1, 0, 1, 1], "email · phone · WhatsApp"),
           ("Shipping line", [0, 1, 1, 1, 1, 0, 0, 1], "portal · EDI · email"),
           ("Origin agent", [0, 0, 1, 1, 0, 0, 0, 0], "email · WhatsApp"),
           ("Port terminal", [0, 0, 0, 1, 1, 1, 0, 0], "portal"),
           ("Haulier", [0, 1, 0, 0, 0, 0, 1, 1], "phone · WhatsApp"),
           ("Customs broker", [0, 0, 0, 1, 0, 1, 1, 0], "email · portal"),
           ("Consignee", [0, 0, 0, 0, 1, 0, 1, 1], "email · phone")]
TOUCHES = sum(sum(r) for _, r, _ in PARTIES)
CHX = TX0 + TXW + 40
CWD = TXW / len(COLS)
for c, lab in enumerate(COLS):
    s.text(TX0 + c * CWD + CWD / 2, FY + 176, lab, 10, 600, MUTED, anchor="middle")
s.text(CHX, FY + 176, "REACHED ON", 9, 700, AMBER, ls=1.2)
s.text(W - M - 26, FY + 176, "and not an exhaustive list", 9, 400, FAINT, anchor="end")
s.line(TX0, FY + 186, W - M - 26, FY + 186, BORDER_STRONG)
for r, (party, row, chans) in enumerate(PARTIES):
    y = FY + 208 + r * 22
    s.text(M + 26, y + 4, party, 12, 500, FG)
    for c, on in enumerate(row):
        cx = TX0 + c * CWD + CWD / 2
        s.raw(f'<circle cx="{cx}" cy="{y}" r="{6 if on else 2}" fill="{AMBER if on else GRAY400}"/>')
    cx_ = CHX
    for ch in chans.split(" · "):
        wpx = len(ch) * 5.6 + 26
        s.card(cx_, y - 9, wpx, 19, fill=AMBER_BG, stroke="none", rx=4)
        s.raw(f'<circle cx="{cx_+10}" cy="{y-0.5}" r="3" fill="{AMBER}"/>')
        s.text(cx_ + 18, y + 3.5, ch, 10, 600, AMBER)
        cx_ += wpx + 5
s.line(M + 26, FY + 372, W - M - 26, FY + 372, BORDER)
s.text(M + 26, FY + FH - 12,
       f"{TOUCHES} handoffs, seven parties, five channels, before Teams, SMS, a carrier's own portal "
       "or whatever this customer happens to prefer.", 13.5, 500, FG)

# =========================================================================
# WHERE THE TMS SITS
# =========================================================================
TY2, TH3 = 636, 250
s.card(M, TY2, 830, TH3)
s.text(M + 26, TY2 + 34, "WHERE THE TMS SITS", 10, 700, FAINT, ls=1.4)
for lab, x0, col, items in (
        ("IT HOLDS", M + 26, FG, ["The booking and its dates", "The rate that was agreed",
                                  "The documents on file"]),
        ("IT DOES NOT", M + 424, AMBER, ["Watch anything", "Decide anything",
                                         "Type itself"])):
    s.text(x0, TY2 + 66, lab, 9.5, 700, col, ls=1.2)
    for j, it in enumerate(items):
        y = TY2 + 100 + j * 28
        if col is AMBER:
            s.raw(f'<path d="M{x0+2} {y-8} l9 9 M{x0+11} {y-8} l-9 9" stroke="{AMBER}" '
                  f'stroke-width="1.8" stroke-linecap="round"/>')
        else:
            s.raw(f'<path d="M{x0+1} {y-4} l4 4 l8 -9" stroke="{GREEN}" stroke-width="1.8" '
                  f'fill="none" stroke-linecap="round"/>')
        s.text(x0 + 22, y, it, 12.5, 500 if col is AMBER else 400,
               FG if col is AMBER else MUTED)
s.line(M + 404, TY2 + 52, M + 404, TY2 + TH3 - 72, BORDER)
s.text(M + 26, TY2 + TH3 - 30,
       "It is the system of record, and the desk is the thing that records into it.", 12.5, 400, MUTED)

# =========================================================================
# WHAT A CLEAN FILE EARNS
# =========================================================================
BX, BW = 950, W - M - 950
s.card(BX, TY2, BW, TH3, stroke=BORDER_STRONG)
s.text(BX + 26, TY2 + 34, "WHAT A CLEAN FILE EARNS", 10, 700, AMBER, ls=1.4)
s.text(BX + BW - 26, TY2 + 34, "per container", 11, 400, FAINT, anchor="end")

STEPS = [("Billed to the customer", 1913, 100.0), ("Paid to the carrier", -1475, -77.1),
         ("Gross profit", 438, 22.9), ("Running the desk", -311, -16.3),
         ("Left over", 127, 6.6)]
SX2, SWID = BX + 26, BW - 52
for j, (lab, val, pct) in enumerate(STEPS):
    y = TY2 + 66 + j * 28
    last = j == len(STEPS) - 1
    col = AMBER if last else (SURFACE_2 if val > 0 else GRAY400)
    s.text(SX2, y, lab, 12.5, 600 if last else 400, FG if last else MUTED)
    s.raw(f'<rect x="{SX2+210}" y="{y-11}" width="{abs(pct)/100*230:.0f}" height="14" rx="3" fill="{col}"/>')
    s.raw(f'<text x="{SX2+SWID-96}" y="{y}" font-size="{15 if last else 12.5}" font-weight="600" '
          f'fill="{AMBER if last else (FG if val>0 else FAINT)}" text-anchor="end" class="num">'
          f'{"−" if val<0 else ""}€{abs(val):,}</text>')
    s.raw(f'<text x="{SX2+SWID}" y="{y}" font-size="{16 if last else 13}" font-weight="600" '
          f'fill="{AMBER if last else (MUTED if val>0 else FAINT)}" text-anchor="end" class="num">'
          f'{"−" if pct<0 else ""}{abs(pct):.1f}%</text>')
s.line(SX2, TY2 + TH3 - 54, BX + BW - 26, TY2 + TH3 - 54, BORDER)
s.text(SX2, TY2 + TH3 - 30, "Six euros and change on every hundred billed.", 15, 600, FG)
s.text(SX2, TY2 + TH3 - 10, "K+N Sea Logistics FY25 · CHF at 1.07 · gross profit from the 29% conversion rate",
       10, 400, FAINT, cls="mono")

s.text(M, 916, "That is the good day.", 24, 600, FG, ls=-0.5)
s.footer("04 / THE JOB 1/2")
s.write("slide-04-the-job.svg")
