"""app.py - the web layer. Serves the dashboard and exposes the trigger.

A handful of routes and two static pages. That is the whole backend:

    GET  /              the landing page - what this is, before you press anything
    GET  /app           the dashboard (the demo itself)
    GET  /fonts/{file}  the self-hosted Geist faces the pages are set in
    GET  /api/initial   the calm 'before' board, so the page renders instantly
    POST /run           the trigger button - runs the orchestrator, returns JSON

Start it:

    uvicorn src.app:app --reload
    then open http://127.0.0.1:8000
"""

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel

from src import config, llm, orchestrator

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
INDEX = STATIC_DIR / "index.html"        # the dashboard, served at /app
LANDING = STATIC_DIR / "landing.html"    # the marketing page, served at /
FONTS_DIR = STATIC_DIR / "fonts"         # Geist, self-hosted: no CDN, ever

app = FastAPI(title="Trade-Lane Risk & Reroute Agent",
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
    """The front door: what Lanewatch is, and what is real about it."""
    return _page(LANDING, "Landing page")


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
    }


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
