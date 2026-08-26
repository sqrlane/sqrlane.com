"""app.py - the web layer. Serves the dashboard and exposes the trigger.

A handful of routes and two static pages. That is the whole backend:

    GET  /              the landing page - what this is, before you press anything
    GET  /app           the dashboard (the demo itself)
    GET  /fonts/{file}  the self-hosted Geist faces the pages are set in
    GET  /api/initial   the calm 'before' board, so the page renders instantly
    GET  /api/gauges    live Rhine water levels for the landing page
    POST /run           the trigger button - runs the orchestrator, returns JSON

Start it:

    uvicorn src.app:app --reload
    then open http://127.0.0.1:8000
"""

import os
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel

from src import config, llm, orchestrator, simulation

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
INDEX = STATIC_DIR / "index.html"        # the dashboard, served at /app
LANDING = STATIC_DIR / "landing.html"    # the marketing page, served at /
PAPER = STATIC_DIR / "whitepaper.html"   # the technical whitepaper, served at /whitepaper
DECK = STATIC_DIR / "deck.html"          # the pitch deck, served at /deck
WHAT = STATIC_DIR / "what.html"          # the What section on its own, served at /what
FONTS_DIR = STATIC_DIR / "fonts"         # Geist, self-hosted: no CDN, ever

app = FastAPI(title="SQRlane",
              description="Demo prototype. Drafts emails; sends nothing.")


class RunRequest(BaseModel):
    """Options the button can send. The defaults are what the demo uses."""
    live: bool = True             # pull real news alongside the scripted event
    inject: bool = True           # load the selected scripted scenario
    use_llm: bool = True          # fall back to deterministic logic if this is false
    scenario: str | None = None   # hamburg, redsea, rhine, france. None = the default


def _page(path: Path, what: str):
    """Serve a static page, or say which file is missing and why.

    Only the missing branch is interesting: it is reachable when a deploy fails
    to bundle static/, and a named file beats a 500 at whoever opened the page.
    """
    if not path.exists():
        return HTMLResponse(status_code=500, content=(
            f"<h1>{what} file missing</h1><p>Expected <code>{path}</code>. If this "
            "is a deployed build, check that <code>vercel.json</code> still lists "
            "<code>static/**</code> under <code>includeFiles</code>.</p>"))
    return FileResponse(path)


@app.get("/")
def landing():
    """The front door: what SQRlane is, and what is real about it."""
    return _page(LANDING, "Landing page")


@app.get("/whitepaper")
def whitepaper():
    """The technical whitepaper: how the loop works, and where it breaks."""
    return _page(PAPER, "Whitepaper")


@app.get("/deck")
def deck():
    """The pitch deck: what, why, how, who.

    Deliberately not linked from the landing nav. It is the deck you hand to a
    room, not a page for whoever wanders onto the site.
    """
    return _page(DECK, "Pitch deck")


@app.get("/what")
def what():
    """The What section on its own: the problem, and what it costs.

    Split out from /deck because the problem is the half that gets rebuilt most
    often, and because it is the section that goes into Figma on its own.
    """
    return _page(WHAT, "What deck")


@app.get("/app")
def dashboard():
    """The demo itself. This is the page with the button."""
    return _page(INDEX, "Dashboard")


@app.get("/fonts/{filename}")
def font(filename: str):
    """Geist Sans and Geist Mono, served from static/fonts/.

    Self-hosted on purpose: the pages must load no external asset, so flaky wifi
    in front of an audience cannot strip the typography or blank the page.
    """
    # Resolve and confine to FONTS_DIR so a crafted name cannot walk upward.
    target = (FONTS_DIR / filename).resolve()
    if not target.is_file() or FONTS_DIR.resolve() not in target.parents:
        return JSONResponse(status_code=404, content={"error": "No such font."})
    return FileResponse(target, media_type="font/woff2", headers={
        "Cache-Control": "public, max-age=31536000, immutable"})


@app.get("/api/scenarios")
def scenarios():
    """The switchable disruptions. All scripted, and labelled so on screen."""
    from src import risk_monitor
    return {"default": risk_monitor.default_scenario(),
            "scenarios": [{k: s[k] for k in ("id", "name", "kind", "summary",
                                             "decision_type", "expected")}
                          for s in risk_monitor.load_scenarios()]}


@app.get("/api/health")
def health(request: Request):
    """What the app can actually see. First stop when a deploy misbehaves.

    Reports the path FastAPI received, so a routing problem shows up here as a
    path that is not /api/health.
    """
    return {
        "ok": True,
        "path_seen_by_app": request.url.path,
        "serverless": config.SERVERLESS,
        "dashboard_present": INDEX.exists(),
        "landing_present": LANDING.exists(),
        "whitepaper_present": PAPER.exists(),
        "deck_present": DECK.exists(),
        "what_present": WHAT.exists(),
        "fonts_present": sorted(f.name for f in FONTS_DIR.glob("*.woff2")),
        "data_files_present": {
            f.name: f.exists() for f in (
                config.CHOKEPOINTS_FILE, config.ROUTES_FILE,
                config.SHIPMENTS_FILE, config.INJECTED_EVENTS_FILE)
        },
        "risk_state_path": str(config.RISK_STATE_FILE),
        "risk_state_dir_writable": os.access(config.RISK_STATE_FILE.parent, os.W_OK),
        "ai_provider": llm.describe() if llm.is_configured() else None,
        # Groq's model is resolved at runtime, so name the one really in use.
        "ai_model": llm.active_model() if llm.is_configured() else None,
        "ai_model_source": llm.resolution_note() or "not resolved yet",
        "live_pull_budget_seconds": config.LIVE_PULL_BUDGET_SECONDS,
        "gauge_budget_seconds": config.GAUGE_BUDGET_SECONDS,
        "gauge_cache_seconds": config.GAUGE_CACHE_SECONDS,
    }


# The landing page's live gauge strip, cached in the process. The page is
# public and PEGELONLINE only refreshes about every fifteen minutes, so reading
# it again on every visit would be both rude to the source and slower than the
# page for no new information. On Vercel each warm instance keeps its own copy,
# which is fine - the point is not to hit the gauge once per visitor.
_gauge_cache = {"at": 0.0, "payload": None}


def _gauge_response(payload: dict, *, age: float, stale: bool):
    """Attach the age to the body and the caching rules to the headers."""
    body = dict(payload, stale=stale, age_seconds=round(age))
    # A good reading may be cached; a failure must not be, or one bad minute
    # would be served for the next five.
    cache = ("no-store" if stale or not payload.get("ok") else
             f"public, max-age=60, s-maxage={config.GAUGE_CACHE_SECONDS}")
    return JSONResponse(body, headers={"Cache-Control": cache})


@app.get("/api/gauges")
def gauges():
    """Rhine water levels, read live from PEGELONLINE.

    This never fails the caller. If the source is unreachable it serves the last
    good reading marked stale, or an empty payload marked not-ok. The landing
    page is allowed to say the gauges are unavailable; it is not allowed to
    break because a river gauge is down.
    """
    from src import risk_monitor

    now = time.monotonic()
    cached = _gauge_cache["payload"]
    age = now - _gauge_cache["at"]
    if cached and age < config.GAUGE_CACHE_SECONDS:
        return _gauge_response(cached, age=age, stale=False)

    try:
        fresh = risk_monitor.read_rhine_gauges()
    except Exception as exc:                      # noqa: BLE001
        fresh = {"source": "PEGELONLINE", "gauges": [], "ok": False,
                 "error": f"{type(exc).__name__}: {exc}"}

    if fresh.get("ok"):
        _gauge_cache.update(at=now, payload=fresh)
        return _gauge_response(fresh, age=0, stale=False)

    # Nothing fresh. A stale reading still tells the truth about the river as of
    # a stated time, which beats an empty panel.
    if cached:
        return _gauge_response(cached, age=age, stale=True)
    return _gauge_response(fresh, age=0, stale=False)


@app.get("/api/initial")
def initial():
    """The board before the button is pressed: five shipments, all green."""
    try:
        state = orchestrator.initial_state()
    except OSError as exc:
        return JSONResponse(status_code=200, content={
            "state": "error",
            "error": f"Could not read the shipment data: {exc}",
            "notes": ["The data/ files did not ship with this build. Check "
                      "includeFiles in vercel.json."],
            "shipments": [], "risk": {"events": [], "sources": []},
            "summary": {"reroute": 0, "hold": 0, "no-action": 0, "drafts": 0},
        })
    state["provider"] = llm.describe() if llm.is_configured() else None
    state["forwarder"] = config.FORWARDER["company"]
    state["ai"] = {
        "provider": config.LLM_PROVIDER if llm.is_configured() else None,
        "model": llm.active_model() if llm.is_configured() else None,
        "model_source": llm.resolution_note(),
    }
    return state


@app.get("/api/simulation")
def api_simulation(days: int | None = None, use_llm: bool = False):
    """Replay the authored week over the board.

    Deterministic by default: a full week is seven shipments times eight days of
    decisions, which is far more model calls than a free tier will take. The
    timeline is authored either way and the payload says so.
    """
    try:
        return simulation.run(use_llm=use_llm, until_day=days, verbose=False)
    except Exception as exc:  # noqa: BLE001 - same reason as /run
        return JSONResponse(status_code=200, content={
            "state": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "days": [], "totals": {},
        })


@app.post("/run")
def run(request: RunRequest | None = None):
    """One press of the button: refresh risk, decide, draft, return everything.

    Any failure is returned as a readable payload rather than a 500, because a
    stack trace on screen in front of an audience is its own kind of failure.
    """
    options = request or RunRequest()
    try:
        return orchestrator.run_cycle(live=options.live, inject=options.inject,
                                      use_llm=options.use_llm, scenario=options.scenario)
    except Exception as exc:  # noqa: BLE001 - never let the demo show a stack trace
        return JSONResponse(status_code=200, content={
            "state": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "notes": ["The run failed. The scripted scenario can still be shown with "
                      "the live pull turned off."],
            "shipments": [], "risk": {"events": [], "sources": []},
            "summary": {"reroute": 0, "hold": 0, "no-action": 0, "drafts": 0},
        })
