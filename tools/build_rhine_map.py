"""build_rhine_map.py - regenerate the Rhine corridor map on the landing page.

Not part of the app. Nothing imports it and it never runs at request time: the
map it produces is pasted into static/landing.html as inline SVG, which is why
the page fetches no tile, no key and no map service.

Run it when the frame, the gauges or the traced routes need to change:

    python3 tools/build_rhine_map.py            # needs network, once
    # then paste the printed <svg> over the one in static/landing.html

Geometry is Natural Earth via its public GitHub mirror:
  ne_50m_admin_0_countries       national outlines
  ne_10m_rivers_lake_centerlines river centrelines

Both are public domain. The files are cached beside this script on first run.

Three things in here are decisions rather than mechanics, and each is
commented where it happens:
  * Natural Earth names the Rhine in three pieces, one of them in French.
  * The corridor ends at Basel; the river does not.
  * The rail alternate is offset off the water so it can be seen, and tapered
    back to zero at the two ports it genuinely shares with the barge.
"""

import json, math, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".ne-cache")
BASE = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
        "master/geojson/")
LAYERS = {"ne_countries.geojson": "ne_50m_admin_0_countries.geojson",
          "ne_rivers_world.geojson": "ne_10m_rivers_lake_centerlines.geojson"}


def fetch():
    os.makedirs(CACHE, exist_ok=True)
    for local, remote in LAYERS.items():
        path = os.path.join(CACHE, local)
        if os.path.exists(path):
            continue
        print("fetching %s ..." % remote, file=sys.stderr)
        urllib.request.urlretrieve(BASE + remote, path)
    return CACHE


SP = fetch()
LON0, LON1, LAT0, LAT1 = 2.8, 10.6, 46.8, 53.2
W = 300.0
KX = math.cos(math.radians((LAT0 + LAT1) / 2))
H = round(W * (LAT1 - LAT0) / ((LON1 - LON0) * KX), 1)

def P(lon, lat):
    return ((lon - LON0) / (LON1 - LON0) * W, (LAT1 - lat) / (LAT1 - LAT0) * H)

def rdp(pts, eps):
    if len(pts) < 3: return pts
    a, b = pts[0], pts[-1]
    dx, dy = b[0]-a[0], b[1]-a[1]
    n = math.hypot(dx, dy)
    worst, wi = -1.0, 0
    for i in range(1, len(pts)-1):
        p = pts[i]
        d = (abs(dy*p[0]-dx*p[1]+b[0]*a[1]-b[1]*a[0])/n if n
             else math.hypot(p[0]-a[0], p[1]-a[1]))
        if d > worst: worst, wi = d, i
    if worst <= eps: return [a, b]
    return rdp(pts[:wi+1], eps)[:-1] + rdp(pts[wi:], eps)

def clip_rect(pts, x0, y0, x1, y1):
    def ix(p,q,x):
        t=(x-p[0])/(q[0]-p[0]); return (x, p[1]+t*(q[1]-p[1]))
    def iy(p,q,y):
        t=(y-p[1])/(q[1]-p[1]); return (p[0]+t*(q[0]-p[0]), y)
    def cl(pts, edge, keep):
        out=[]
        for i,cur in enumerate(pts):
            prv=pts[i-1]; ci,pi=keep(cur),keep(prv)
            if ci:
                if not pi: out.append(edge(prv,cur))
                out.append(cur)
            elif pi: out.append(edge(prv,cur))
        return out
    for edge,keep in ((lambda p,q: ix(p,q,x0), lambda p: p[0]>=x0),
                      (lambda p,q: ix(p,q,x1), lambda p: p[0]<=x1),
                      (lambda p,q: iy(p,q,y0), lambda p: p[1]>=y0),
                      (lambda p,q: iy(p,q,y1), lambda p: p[1]<=y1)):
        if not pts: return []
        pts = cl(pts, edge, keep)
    return pts

def d_of(rings, close=False):
    return "".join("M" + "L".join("%.1f,%.1f" % (p[0],p[1]) for p in r)
                   + ("Z" if close else "") for r in rings if len(r) > 1)

# ---- land ------------------------------------------------------------------
WANT = {"NLD","BEL","DEU","FRA","CHE","LUX"}
cs = json.load(open(SP+"/ne_countries.geojson"))
key = next(k for k in ("ISO_A3","ADM0_A3","SOV_A3") if k in cs["features"][0]["properties"])
land=[]
for f in cs["features"]:
    if f["properties"].get(key) not in WANT: continue
    g=f["geometry"]
    for poly in ([g["coordinates"]] if g["type"]=="Polygon" else g["coordinates"]):
        r=[P(x,y) for x,y in poly[0]]
        r=clip_rect(r,0,0,W,H)
        if len(r)<4: continue
        r=rdp(r,0.35)
        if len(r)>=4: land.append(r)

# ---- rivers ----------------------------------------------------------------
rv=json.load(open(SP+"/ne_rivers_world.geojson"))
def lines_named(names):
    out=[]
    for f in rv["features"]:
        if (f["properties"].get("name") or "") not in names: continue
        g=f["geometry"]
        for ln in ([g["coordinates"]] if g["type"]=="LineString" else g["coordinates"]):
            out.append([(x,y) for x,y in ln])
    return out

# The navigation itself, in lon/lat so the reach split is exact.
NAV = lines_named({"Waal","Rhine","Rhin"})
CONTEXT = lines_named({"Maas","Lek","Nederrijn","IJssel","Mosel","Main","Neckar","Aare"})

DUISBURG_LAT = 51.45          # Duisburg-Ruhrort: the last gauge reading clear
def split_reach(ln):
    """Above Duisburg the barge sails loaded; below it the draught binds."""
    ok, sus, cur, cur_ok = [], [], [], None
    for i,(x,y) in enumerate(ln):
        is_ok = y >= DUISBURG_LAT
        if cur_ok is None: cur_ok = is_ok
        if is_ok != cur_ok:
            px,py = ln[i-1]
            t = (DUISBURG_LAT-py)/(y-py) if y!=py else 0
            cross = (px+t*(x-px), DUISBURG_LAT)
            cur.append(cross)
            (ok if cur_ok else sus).append(cur)
            cur=[cross]; cur_ok=is_ok
        cur.append((x,y))
    if cur: (ok if cur_ok else sus).append(cur)
    return ok, sus

BASEL = (7.59, 47.56)
def cut_at_basel(ln):
    """The corridor ends at Basel. NE's 'Rhin' runs on east up the High Rhine,
    which is a different river reach and not a route anything here sails."""
    i = min(range(len(ln)),
            key=lambda k: (ln[k][0]-BASEL[0])**2 + (ln[k][1]-BASEL[1])**2)
    if (ln[i][0]-BASEL[0])**2 + (ln[i][1]-BASEL[1])**2 > 0.25:
        return ln                      # this piece does not reach Basel at all
    head, tail = ln[:i+1], ln[i:]
    return head if len(head) >= len(tail) else list(reversed(tail))

nav_ok, nav_sus = [], []
NAV = [cut_at_basel(ln) for ln in NAV]
for ln in NAV:
    a,b = split_reach(ln)
    nav_ok += a; nav_sus += b
def proj(runs, eps=0.5):
    out=[]
    for r in runs:
        pr=[P(x,y) for x,y in r]
        pr=[p for p in pr if -3<=p[0]<=W+3 and -3<=p[1]<=H+3]
        if len(pr)>1: out.append(rdp(pr,eps))
    return out

nav_ok, nav_sus = proj(nav_ok), proj(nav_sus)
ctx = proj(CONTEXT, 0.7)

# ---- the rail + road alternate ---------------------------------------------
# The Rhine-Alpine freight corridor, through the cities it actually serves.
# Drawn 6px west of the river - about 11 km at this scale, inside the valley
# the line really runs in - because a route drawn exactly on the water would
# be invisible under it.
# Through the gorge it follows the water, because the line really does - the
# Koblenz-Bingen stretch runs both banks. Cutting straight across that loop
# would draw a railway where there is only hillside.
RAIL = [(4.14,51.95),(6.25,51.83),(6.73,51.45),(6.96,50.94),(7.10,50.73),
        (7.60,50.36),(7.59,50.23),(7.77,50.09),(7.90,49.97),(8.27,50.00),
        (8.47,49.49),(8.43,49.32),(8.40,49.01),(8.20,48.50),(7.85,47.99),
        (7.59,47.56)]
def offset(pts, d):
    out = []
    n_last = len(pts) - 1
    for i, (x, y) in enumerate(pts):
        # Ramp the offset in and out so both routes meet at the two ports they
        # genuinely share, instead of ending 8px short of them.
        t = min(i, n_last - i) / (n_last * 0.18)
        d_i = d * min(1.0, t)
        ax, ay = pts[max(i-1, 0)]
        bx, by = pts[min(i+1, len(pts)-1)]
        dx, dy = bx-ax, by-ay
        n = math.hypot(dx, dy) or 1.0
        out.append((x - dy/n*d_i, y + dx/n*d_i))  # right-hand normal, going south
    return out
rail = offset([P(x, y) for x, y in RAIL], 8.5)

# ---- places ----------------------------------------------------------------
PARTS = {"W": W, "H": H,
         "land": d_of(land, True), "ctx": d_of(ctx), "nav_ok": d_of(nav_ok),
         "nav_sus": d_of(nav_sus), "rail": d_of([rail]),
         "P": {nm: P(lo, la) for nm, lo, la in
               (("RTM", 4.14, 51.95), ("EMM", 6.25, 51.83), ("DUI", 6.73, 51.45),
                ("KAUB", 7.77, 50.09), ("BSL", 7.59, 47.56))}}
p = PARTS
W, H = p["W"], p["H"]; pt = p["P"]

ALT = ("The Rhine corridor from Rotterdam up to Basel, drawn on the map. The barge route "
       "follows the river and is navigable as far as Duisburg-Ruhrort; from there up to "
       "Basel it is payload-limited, binding at Kaub where the gauge reads 44 centimetres "
       "against a 78 centimetre loading threshold. A rail and road alternate runs the same "
       "corridor overland from Rotterdam to Basel for one extra day.")

def T(x, y, s, cls="", anchor=None):
    a = ' text-anchor="%s"' % anchor if anchor else ""
    c = ' class="%s"' % cls if cls else ""
    return '<text%s x="%.1f" y="%.1f"%s>%s</text>' % (c, x, y, a, s)

def stack(k, lines, dx, dy, anchor=None):
    x, y = pt[k]
    return "".join(T(x+dx, y+dy+13*i, s, cls, anchor) for i, (s, cls) in enumerate(lines))

labels = (
    stack("RTM",  [("ROTTERDAM", "on")], 8, -6)
    # Emmerich and Duisburg-Ruhrort are 23px apart and each wants two lines, so
    # the upper one hangs to the left rather than stacking into its neighbour.
    + stack("EMM",  [("EMMERICH", ""), ("51 cm", "")], -8, 10, "end")
    + stack("DUI",  [("DUISBURG-RUHRORT", ""), ("196 cm", "")], 8, 4)
    + stack("KAUB", [("KAUB", "rd"), ("44 cm", "rd"), ("threshold 78", "")], 12, -1)
    + stack("BSL",  [("BASEL", "on")], 8, 4)
    + T(168, 268, "RAIL + ROAD", "bl", "end") + T(168, 280, "+1 d", "bl", "end")
)

svg = f'''<svg class="corridor" viewBox="0 0 {W:.0f} {H}" role="img" aria-label="{ALT}">
          <path class="land" d="{p['land']}"/>
          <path class="water" d="{p['ctx']}"/>

          <!-- the alternate first, so the river draws over it -->
          <path class="leg-alt" d="{p['rail']}"/>

          <!-- the barge route is the river itself, drawn in its two reaches -->
          <path class="leg-ok"  d="{p['nav_ok']}"/>
          <path class="leg-sus" d="{p['nav_sus']}"/>

          <circle class="node"  cx="{pt['RTM'][0]:.1f}" cy="{pt['RTM'][1]:.1f}" r="4.5"/>
          <circle class="gauge" cx="{pt['EMM'][0]:.1f}" cy="{pt['EMM'][1]:.1f}" r="3.5"/>
          <circle class="gauge" cx="{pt['DUI'][0]:.1f}" cy="{pt['DUI'][1]:.1f}" r="3.5"/>
          <circle class="gauge bind" cx="{pt['KAUB'][0]:.1f}" cy="{pt['KAUB'][1]:.1f}" r="4"/>
          <circle class="node"  cx="{pt['BSL'][0]:.1f}" cy="{pt['BSL'][1]:.1f}" r="4.5"/>

          {labels}
        </svg>'''
print(svg)
