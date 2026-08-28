#!/usr/bin/env python3
"""
Slide 04 - THE HOW (1/2).  Emits deck/slide-04-the-how-1.svg.

Answers problem one from slide 02: the work is manual. Three parts -

  a dashboard mock, drawn from docs/dashboard.png so it is the real product
  the desk-work table, one row per job that used to be typed
  a parallel lane diagram: the agents run at once, each waiting only for the
  fact it needs, and every open loop closed by another agent rather than a person

Roles are verbatim from src/roster.py; the tags are what they are today.
"""
from deckkit import *

GREEN, GREEN_BG = "#0f7b3f", "#e7f5ec"
BLUE, BLUE_BG = "#006bff", "#e8f1ff"

s = Slide()
s.header("04 — THE HOW (1/2)",
         "The desk work does itself.",
         "The same six systems. Nobody re-types anything between them any more.")

# =========================================================================
# THE PRODUCT, AS IT LOOKS
# =========================================================================
DX, DY, DW, DH = M, 216, 830, 354
s.card(DX, DY, DW, DH, fill=CARD, stroke=BORDER_STRONG)
s.raw(f'<rect x="{DX}" y="{DY}" width="{DW}" height="38" rx="{RMD}" fill="{SURFACE}"/>')
s.raw(f'<rect x="{DX}" y="{DY+26}" width="{DW}" height="12" fill="{SURFACE}"/>')
s.line(DX, DY + 38, DX + DW, DY + 38, BORDER)
s.text(DX + 16, DY + 25, "SQRlane / Overview", 11.5, 500, MUTED)
s.card(DX + DW - 150, DY + 8, 134, 22, fill=FG, stroke="none", rx=R)
s.text(DX + DW - 83, DY + 23, "Inject Hamburg strike", 9.5, 600, CARD, anchor="middle")

# sidebar
SBW = 116
s.line(DX + SBW, DY + 38, DX + SBW, DY + DH, BORDER)
s.raw(f'<rect x="{DX+14}" y="{DY+52}" width="14" height="14" rx="4" fill="{FG}"/>')
s.text(DX + 34, DY + 63, "SQRlane", 10, 600, FG)
for j, (nav, n) in enumerate((("Overview", ""), ("Shipments", "7"), ("Risk feed", "1"),
                              ("Approvals", "18"), ("Map", "7"), ("Simulation", ""),
                              ("TMS link", "12"))):
    y = DY + 88 + j * 22
    if j == 0:
        s.card(DX + 8, y - 11, SBW - 16, 19, fill=SURFACE, stroke="none", rx=4)
    s.text(DX + 14, y, nav, 9.5, 600 if j == 0 else 400, FG if j == 0 else MUTED)
    if n:
        s.text(DX + SBW - 14, y, n, 9, 500, FAINT, anchor="end", cls="mono")

CXX = DX + SBW + 18
s.text(CXX, DY + 62, "WORKERS", 8.5, 700, FAINT, ls=1.2)
PILLS = [("Risk", "LIVE"), ("Routing", "LIVE"), ("Comms", "LIVE"), ("Rate", "SCR"),
         ("Milestones", "SCR"), ("Docs", "SCR"), ("Inbox", "SCR"), ("RFQ", "SCR"),
         ("Booking", "SCR"), ("Invoice", "SCR"), ("Customs", "SCR"), ("TMS Link", "DEMO"),
         ("Assistant", "SCR")]
px_, py_ = CXX, DY + 72
for name, tag in PILLS:
    w = len(name) * 5.4 + 42
    if px_ + w > DX + DW - 18:
        px_, py_ = CXX, py_ + 26
    live = tag == "LIVE"
    s.card(px_, py_, w, 21, fill=CARD, stroke=BORDER_STRONG, rx=R)
    s.text(px_ + 8, py_ + 14, name, 9, 500, FG)
    s.text(px_ + w - 8, py_ + 14, tag, 7.5, 700, GREEN if live else FAINT, anchor="end")
    px_ += w + 6

STATS = [("Bookings", "7", "4 on plan · 12 queued back", "3 actioned", BLUE, BLUE_BG),
         ("Risk events", "1", "Hamburg strike, high", "live", GREEN, GREEN_BG),
         ("Deadlines at risk", "1", "customer date missed", "breach", "#ea001d", "#feecec"),
         ("Awaiting approval", "18", "6 drafts · 12 TMS changes", "held", AMBER, AMBER_BG)]
SW_ = (DW - SBW - 36 - 3 * 10) / 4
for j, (lab, val, sub, chip, col, bg) in enumerate(STATS):
    x = CXX + j * (SW_ + 10)
    s.card(x, DY + 152, SW_, 92, fill=CARD, stroke=BORDER)
    s.text(x + 12, DY + 174, lab, 8.5, 500, MUTED)
    s.chip(x + SW_ - 12 - 54, DY + 163, 54, 15, chip, fs=7, fill=bg, col=col, weight=700)
    s.raw(f'<text x="{x+12}" y="{DY+212}" font-size="26" font-weight="600" fill="{FG}" '
          f'class="num">{val}</text>')
    s.text(x + 12, DY + 232, sub, 8, 400, FAINT)

s.card(CXX, DY + 254, DW - SBW - 36, 68, fill=CARD, stroke=BORDER)
s.text(CXX + 12, DY + 274, "Board outcome", 9.5, 600, FG)
for j, (lab, n, col) in enumerate((("Rerouted", 2, BLUE), ("Held", 1, AMBER), ("On plan", 4, GREEN))):
    x = CXX + 12 + j * 150
    s.raw(f'<circle cx="{x+5}" cy="{DY+298}" r="4" fill="{col}"/>')
    s.text(x + 16, DY + 302, lab, 9.5, 400, MUTED)
    s.text(x + 96, DY + 302, str(n), 9.5, 600, FG, cls="mono")
s.text(DX + DW - 18, DY + 302, "7 shipments · last run 12:00", 8.5, 400, FAINT, anchor="end")

# =========================================================================
# WHAT USED TO BE TYPED
# =========================================================================
TX2, TW2 = 950, W - M - 950
s.card(TX2, DY, TW2, DH)
s.raw(f'<rect x="{TX2}" y="{DY}" width="{TW2}" height="38" rx="{RMD}" fill="{SURFACE}"/>')
s.raw(f'<rect x="{TX2}" y="{DY+26}" width="{TW2}" height="12" fill="{SURFACE}"/>')
s.line(TX2, DY + 38, TX2 + TW2, DY + 38, BORDER)
tx = TX2 + 24
s.text(tx, DY + 24, "What used to be typed", 11.5, 500, MUTED)
s.text(TX2 + TW2 - 24, DY + 24, "scripted today · src/roster.py", 10, 400, FAINT,
       anchor="end", cls="mono")

s.text(tx, DY + 66, "WHAT ARRIVES", 9, 700, FAINT, ls=1.2)
s.text(tx + 250, DY + 66, "AGENT", 9, 700, FAINT, ls=1.2)
s.text(tx + 380, DY + 66, "WHAT LANDS ON THE BOOKING", 9, 700, FAINT, ls=1.2)
s.line(tx, DY + 78, TX2 + TW2 - 24, DY + 78, BORDER_STRONG)
ROWS = [("A rate request", "RFQ", "Quote on the file"),
        ("Carrier or customer mail", "Inbox", "Reply on the comms log"),
        ("A bill of lading, an invoice", "Docs", "Fields on the booking"),
        ("A change to the booking", "Booking", "Amendment, for approval"),
        ("The carrier's invoice", "Invoice", "Discrepancy, flagged"),
        ("A new country of entry", "Customs", "Escalation, not a filing"),
        ("Every one of the above", "TMS Link", "One queued change, gated")]
for j, (a, ag, l) in enumerate(ROWS):
    y = DY + 110 + j * 38
    last = j == len(ROWS) - 1
    if last:
        s.card(tx - 10, y - 21, TW2 - 28, 32, fill=SURFACE, stroke="none", rx=R)
    s.text(tx, y, a, 12.5, 500, FG)
    s.text(tx + 250, y, ag, 12.5, 600, FG)
    s.text(tx + 380, y, l, 12.5, 400, MUTED)

# =========================================================================
# THE WORKFLOW, AS THE APP SHOWS IT
# =========================================================================
LY, LH = 594, 286
s.card(DX, LY, DW, LH, stroke=BORDER_STRONG)
s.raw(f'<rect x="{DX}" y="{LY}" width="{DW}" height="34" rx="{RMD}" fill="{SURFACE}"/>')
s.raw(f'<rect x="{DX}" y="{LY+22}" width="{DW}" height="12" fill="{SURFACE}"/>')
s.line(DX, LY + 34, DX + DW, LY + 34, BORDER)
for k in range(3):
    s.raw(f'<circle cx="{DX+18+k*13}" cy="{LY+17}" r="3.5" fill="{GRAY400}"/>')
s.text(DX + 68, LY + 21, "SQRlane / Shipments / SHP-001", 11, 500, MUTED)
s.text(DX + DW - 16, LY + 21, "activity", 10, 400, FAINT, anchor="end", cls="mono")

FLOW = [("09:12", "Inbox", "carrier mail read, linked to SHP-001", GREEN),
        ("09:12", "Docs", "B/L fields extracted onto the booking", GREEN),
        ("09:13", "Booking", "amendment drafted for the carrier", GREEN),
        ("09:13", "Customs", "entry checked, B/L reissue flagged", AMBER),
        ("09:13", "Invoice", "surcharge reconciled against the rate", GREEN),
        ("09:14", "TMS Link", "4 changes queued, awaiting approval", FG)]
for j, (ts, who, what, col) in enumerate(FLOW):
    y = LY + 62 + j * 33
    s.text(DX + 20, y, ts, 10.5, 400, FAINT, cls="mono")
    s.raw(f'<circle cx="{DX+78}" cy="{y-4}" r="4" fill="{col}"/>')
    if j < len(FLOW) - 1:
        s.line(DX + 78, y + 2, DX + 78, y + 25, GRAY400, 1.2)
    s.text(DX + 94, y, who, 12.5, 600, FG)
    s.text(DX + 190, y, what, 12.5, 400, MUTED)
    s.chip(DX + DW - 20 - 62, y - 13, 62, 19, "done" if col is not FG else "queued",
           fs=9, fill=SURFACE, col=MUTED, weight=600)

# =========================================================================
# AND THEY RUN AT ONCE - the same claim, a sixth of the space
# =========================================================================
s.card(TX2, LY, TW2, LH)
s.text(TX2 + 24, LY + 34, "AND THEY RUN AT ONCE", 10, 700, AMBER, ls=1.4)
LANES = [("Inbox", 0, 5, "starts at once"), ("Docs", 0, 4, "starts at once"),
         ("RFQ", 0, 3, "starts at once"), ("Booking", 3, 7, "waits for the fields"),
         ("Invoice", 4, 8, "waits for the agreed rate"), ("Customs", 6, 10, "waits for the new port")]
L0, LWU = TX2 + 116, 380 / 10
for j, (name, a, b, why) in enumerate(LANES):
    y = LY + 62 + j * 24
    s.text(TX2 + 24, y + 9, name, 10.5, 400, MUTED)
    s.raw(f'<rect x="{L0}" y="{y+3}" width="{10*LWU}" height="11" rx="3" fill="{SURFACE}"/>')
    s.raw(f'<rect x="{L0 + a*LWU}" y="{y+3}" width="{(b-a)*LWU}" height="11" rx="3" fill="{AMBER}"/>')
    s.raw(f'<circle cx="{L0 + b*LWU + 14}" cy="{y+8}" r="5.5" fill="{GREEN_BG}"/>')
    s.raw(f'<path d="M{L0 + b*LWU + 11} {y+8} l2.2 2.2 l5 -5" stroke="{GREEN}" '
          f'stroke-width="1.6" fill="none" stroke-linecap="round"/>')
    s.text(L0 + 400 + 30, y + 12, why, 11, 400, FAINT)

s.line(TX2 + 24, LY + 212, TX2 + TW2 - 24, LY + 212, BORDER)
s.text(TX2 + 24, LY + 240, "A bar starts when the fact it needs exists, and ends", 13, 500, FG)
s.text(TX2 + 24, LY + 260, "when its output is on the booking. Nothing waits for", 13, 400, MUTED)
s.text(TX2 + 24, LY + 280, "a person until the single approval at the end.", 13, 400, MUTED)

s.text(M, 926, "Six systems, one record. The re-typing is gone.", 24, 600, FG, ls=-0.5)
s.raw(f'<text x="{W-M}" y="922" font-size="30" font-weight="600" fill="{FG}" '
      f'text-anchor="end" class="num">40%</text>')
s.text(W - M, 944, "of the day, back", 12, 400, FAINT, anchor="end")
s.footer("04 / THE HOW 1/2")
s.write("slide-04-the-how-1.svg")
