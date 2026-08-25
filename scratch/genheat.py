"""Emit the heatmap block as static HTML.

Every cell is banded by src/risk_monitor._gauge_state - the same rule the live
panel and the risk monitor use - so the heatmap cannot disagree with the rest
of the system about what a reading means. Delays are baked in here rather than
computed in the browser, so the block needs no script of its own: the page's
existing reveal observer is the only thing that starts it.
"""
import sys; sys.path.insert(0, "/home/user/Logistics-Freight-Forwarding")
from src import config, risk_monitor

DAYS = ["Aug 06","Aug 07","Aug 08","Aug 09","Aug 10","Aug 11","Aug 12","Aug 13",
        "Aug 14","Aug 15","Aug 16","Aug 17","Aug 18","Aug 19","Aug 20","Aug 21"]
CALL = 6                                    # Aug 12 - the day the call was made
SERIES = [
  ("KAUB",             [118,110,103, 96, 92, 85, 82, 80, 78, 71, 66, 61, 57, 52, 47, 44]),
  ("DUISBURG-RUHRORT", [286,272,258,244,232,221,212,206,199,190,182,174,171,167,163,160]),
  ("EMMERICH",         [ 96, 88, 80, 72, 66, 58, 52, 46, 41, 36, 31, 27, 23, 19, 16, 14]),
]
BAND = {"normal": ("b0", "Normal"), "watch": ("b1", "Watch"),
        "restricted": ("b2", "Restricted"), "critical": ("b3", "Critical")}

# bklit's heatmap reveal: cells fade in at pseudo-random delays spread over
# (enter duration - fade), not in a sweep. Seeded so the scatter is identical
# on every load - a demo should not reshuffle itself between runs.
def seeded(col, row):
    h = (col * 73_856_093) ^ (row * 19_349_663)
    h = (h * 2_654_435_761) & 0xFFFFFFFF
    return ((h >> 8) & 0xFFFF) / 0xFFFF

SPREAD_MS = 690                              # (1600 enter - 450 fade) * 0.6

by_station = {g["station"]: g for g in config.RHINE_GAUGES}
out = []
for row, (station, vals) in enumerate(SERIES):
    gauge = by_station[station]
    cells = []
    for col, v in enumerate(vals):
        _sev, state, _d, _n = risk_monitor._gauge_state(gauge, v)
        cls, label = BAND[state]
        extra = " call" if col == CALL else ""
        cells.append(
            f'<i class="hc {cls}{extra}" style="--d:{seeded(col,row)*SPREAD_MS:.0f}ms"'
            f' title="{gauge["name"]} · {DAYS[col]} · {v} cm · {label.lower()}"></i>')
    out.append(f'          <span class="hr-name">{gauge["name"]}</span>\n'
               + "\n".join("          " + c for c in cells))

print("\n".join(out))
print("\n--- band counts ---")
for station, vals in SERIES:
    g = by_station[station]
    b = [risk_monitor._gauge_state(g, v)[1] for v in vals]
    print(f"  {g['name']:<18}", {k: b.count(k) for k in ("normal","watch","restricted","critical") if b.count(k)})
