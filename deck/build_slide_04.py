#!/usr/bin/env python3
"""
Slide 04 - THE JOB (1/2).  Emits deck/slide-04-the-job-1.svg.

Sits between slide 03 (The Why) and slide 06 (The How 1/2, formerly numbered
04 before this slide and its pair were added). Argues what the desk actually
does on an ordinary file, before any disruption: forty-five days end to end,
seven parties re-contacted at every stage, and six euros of margin left over
per hundred billed once the TMS has been re-typed into by hand.

  top     one file, Shanghai to Munich, and the handoffs it takes to close it
  bottom  what the TMS holds vs. what it does not, beside what a clean file
          actually earns once every hour on that bar has been paid for

Source: K+N (Kuehne+Nagel) Sea Logistics FY25 segment disclosure, the same
filing "The Why" already cites for the sector's economics.
"""
from deckkit import *

GREEN = "#0f7b3f"

s = Slide()
s.header("04 — THE JOB (1/2)",
         "Forty-five days, seven parties, €127.",
         "The TMS just stores the booking, it does not decide or move things for the forwarders. "
         "More than 40% of the day is spent coordinating between channels and systems.")

# =========================================================================
# ONE FILE, END TO END + WHO THE FORWARDER TALKS TO
# =========================================================================
TY, TH = 216, 424
s.card(M, TY, CW, TH, stroke=BORDER_STRONG)
tx = M + 32
s.text(tx, TY + 34, "ONE FILE, END TO END", 10, 700, FAINT, ls=1.4)
s.text(tx + 220, TY + 34, "Shanghai to Munich", 12, 400, MUTED)
s.raw(f'<text x="{W-M-32}" y="{TY+38}" font-size="20" font-weight="600" fill="{FG}" '
      f'text-anchor="end" class="num">45 days</text>')

# the clock: seven bands across 45 days, only the two that matter labelled
BX, BW_, BY = tx, CW - 64, TY + 76
s.text(tx, TY + 60, "the clock", 11, 500, MUTED)
DAYS = [2, 3, 2, 2, 32, 2, 2]   # sums to 45
assert sum(DAYS) == 45
cx = BX
for i, d in enumerate(DAYS):
    w = BW_ * d / 45
    big = d == 32
    fill = SURFACE_2 if big else SURFACE
    s.raw(f'<rect x="{cx:.1f}" y="{BY}" width="{w:.1f}" height="24" '
          f'fill="{fill}" stroke="{CARD}" stroke-width="2"/>')
    if d in (3, 32):
        s.text(cx + w / 2, BY + 16, f"{d}d", 11.5 if not big else 13, 600, FG, anchor="middle")
    cx += w
s.text(BX, BY + 42, "opens", 10.5, 400, FAINT)
s.text(BX + BW_, BY + 42, "closes", 10.5, 400, FAINT, anchor="end")

# the touchpoint grid
GY = BY + 84
s.text(tx, GY, "WHO THE FORWARDER TALKS TO", 10, 700, AMBER, ls=1.3)
s.text(tx + 300, GY, "every dot is a mail, a portal login or a call", 11, 400, FAINT)
s.text(W - M - 32, GY, "and not an exhaustive list", 10.5, 400, FAINT, anchor="end")

STAGES = ["Enquiry", "Quote", "Book", "Docs", "In transit", "Customs", "Delivery", "Invoice"]
PARTIES = [
    ("Customer",       [0, 1, 1, 1, 1, 0, 1, 1], ["email", "phone", "WhatsApp"]),
    ("Shipping line",  [0, 1, 1, 1, 1, 0, 0, 1], ["portal", "EDI", "email"]),
    ("Origin agent",   [0, 0, 1, 1, 0, 0, 0, 0], ["email", "WhatsApp"]),
    ("Port terminal",  [0, 0, 0, 1, 1, 1, 0, 0], ["portal"]),
    ("Haulier",        [0, 1, 0, 0, 0, 0, 1, 1], ["phone", "WhatsApp"]),
    ("Customs broker", [0, 0, 0, 1, 0, 1, 1, 0], ["email", "portal"]),
    ("Consignee",      [0, 0, 0, 0, 1, 1, 1, 1], ["email", "phone"]),
]
RLX = tx + 152
COLW = 118
RCHX = RLX + len(STAGES) * COLW + 20
s.line(tx, GY + 20, RCHX + 210, GY + 20, BORDER)
for c, lab in enumerate(STAGES):
    s.text(RLX + c * COLW + COLW / 2, GY + 16, lab, 9.5, 600, FAINT, anchor="middle")
s.text(RCHX, GY + 16, "REACHED ON", 9.5, 600, FAINT)
row_h = 26
for r, (party, dots, channels) in enumerate(PARTIES):
    ry = GY + 40 + r * row_h
    s.text(tx, ry + 4, party, 12, 500, FG)
    for c, big in enumerate(dots):
        cxp = RLX + c * COLW + COLW / 2
        s.raw(f'<circle cx="{cxp}" cy="{ry}" r="{5 if big else 2.2}" '
              f'fill="{AMBER if big else GRAY400}"/>')
    s.text(RCHX, ry + 4, " · ".join(channels), 10, 500, AMBER if channels else FAINT)
sep_y = GY + 40 + len(PARTIES) * row_h + 6
s.line(tx, sep_y, W - M - 32, sep_y, BORDER)
s.text(tx, sep_y + 26,
       "26 handoffs, seven parties, five channels, before Teams, SMS, a carrier's own portal "
       "or whatever this customer happens to prefer.", 13, 400, MUTED)

# =========================================================================
# WHERE THE TMS SITS  /  WHAT A CLEAN FILE EARNS
# =========================================================================
BY2, BH2 = TY + TH + 28, 260
BW2 = (CW - 32) / 2
BX1, BX2 = M, M + BW2 + 32

s.card(BX1, BY2, BW2, BH2)
b1x = BX1 + 28
s.text(b1x, BY2 + 34, "WHERE THE TMS SITS", 10, 700, FAINT, ls=1.4)
colw = (BW2 - 56) / 2
s.text(b1x, BY2 + 66, "IT HOLDS", 11, 700, MUTED, ls=1)
s.text(b1x + colw, BY2 + 66, "IT DOES NOT", 11, 700, AMBER, ls=1)
HOLDS = ["The booking and its dates", "The rate that was agreed", "The documents on file"]
NOTS = ["Watch anything", "Decide anything", "Type itself"]
for i, t in enumerate(HOLDS):
    y = BY2 + 96 + i * 28
    s.raw(f'<path d="M{b1x} {y-4} l4 4.5 l9 -10" stroke="{GREEN}" stroke-width="2" '
          f'fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
    s.text(b1x + 22, y, t, 12.5, 400, FG)
for i, t in enumerate(NOTS):
    y = BY2 + 96 + i * 28
    xx = b1x + colw
    s.raw(f'<path d="M{xx} {y-8} l9 9 M{xx+9} {y-8} l-9 9" stroke="{AMBER}" stroke-width="1.8" '
          f'stroke-linecap="round"/>')
    s.text(xx + 22, y, t, 12.5, 400, FG)
s.line(b1x, BY2 + BH2 - 56, BX1 + BW2 - 28, BY2 + BH2 - 56, BORDER)
s.text(b1x, BY2 + BH2 - 32, "It is the system of record, and the desk is the thing that", 12.5, 400, MUTED)
s.text(b1x, BY2 + BH2 - 14, "records into it.", 12.5, 400, MUTED)

s.card(BX2, BY2, BW2, BH2)
b2x = BX2 + 28
s.text(b2x, BY2 + 34, "WHAT A CLEAN FILE EARNS", 10, 700, AMBER, ls=1.4)
s.text(BX2 + BW2 - 28, BY2 + 34, "per container", 10, 400, FAINT, anchor="end")
ROWS = [("Billed to the customer", 1913, 1913, "100.0%", FG, 600),
        ("Paid to the carrier", -1475, 1475, "-77.1%", MUTED, 400),
        ("Gross profit", 438, 438, "22.9%", FG, 600),
        ("Running the desk", -311, 311, "-16.3%", MUTED, 400),
        ("Left over", 127, 127, "6.6%", AMBER, 700)]
barx, barw = b2x + 210, BW2 - 210 - 150
for i, (lab, signed, mag, pct, col, wt) in enumerate(ROWS):
    y = BY2 + 60 + i * 28
    s.text(b2x, y, lab, 12, 500 if lab == "Left over" else 400, col if lab == "Left over" else FG)
    s.raw(f'<rect x="{barx}" y="{y-11}" width="{barw}" height="13" rx="4" fill="{SURFACE}"/>')
    s.raw(f'<rect x="{barx}" y="{y-11}" width="{barw*mag/1913:.0f}" height="13" rx="4" '
          f'fill="{AMBER if lab=="Left over" else (GRAY400 if signed<0 else FG)}"/>')
    s.raw(f'<text x="{BX2+BW2-28-58}" y="{y}" font-size="13" font-weight="{wt}" fill="{col}" '
          f'text-anchor="end" class="num">{"-" if signed<0 else ""}€{abs(signed):,}</text>')
    s.text(BX2 + BW2 - 28, y, pct, 12, 600 if lab == "Left over" else 400, col, anchor="end")
s.line(b2x, BY2 + BH2 - 56, BX2 + BW2 - 28, BY2 + BH2 - 56, BORDER)
s.text(b2x, BY2 + BH2 - 32, "Six euros and change on every hundred billed.", 13, 600, FG)
s.text(b2x, BY2 + BH2 - 14, "K+N Sea Logistics FY25 · CHF at 1.07 · gross profit from the 29% conversion rate",
       10.5, 400, FAINT, cls="mono")

# =========================================================================
s.text(M, BY2 + BH2 + 40, "That is the good day.", 24, 600, FG, ls=-0.5)
s.footer("04 / THE JOB 1/2")
s.write("slide-04-the-job-1.svg")
