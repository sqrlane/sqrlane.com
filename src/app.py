"""app.py - the web layer. Serves the dashboard and exposes the trigger.

Two endpoints and a static file. That is the whole backend:

    GET  /              the dashboard
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
INDEX = STATIC_DIR / "index.html"

app = FastAPI(title="Trade-Lane Risk & Reroute Agent",
              description="Demo prototype. Drafts emails; sends nothing.")


class RunRequest(BaseModel):
    """Options the button can send. The defaults are what the demo uses."""
    live: bool = True      # pull real news alongside the scripted event
    inject: bool = True    # load the scripted Hamburg strike
    use_llm: bool = True   # fall back to deterministic logic if this is false


@app.get("/")
def dashboard():
    if not INDEX.exists():
        # Only reachable if a deploy failed to bundle static/. Say which file is
        # missing rather than throwing a 500 at whoever opened the page.
        return HTMLResponse(status_code=500, content=(
            "<h1>Dashboard file missing</h1><p>Expected <code>"
            f"{INDEX}</code>. If this is a deployed build, check that "
            "<code>vercel.json</code> still lists <code>static/**</code> under "
            "<code>includeFiles</code>.</p>"))
    return FileResponse(INDEX)


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
        "data_files_present": {
            f.name: f.exists() for f in (
                config.CHOKEPOINTS_FILE, config.ROUTES_FILE,
                config.SHIPMENTS_FILE, config.INJECTED_EVENTS_FILE)
        },
        "risk_state_path": str(config.RISK_STATE_FILE),
        "risk_state_dir_writable": os.access(config.RISK_STATE_FILE.parent, os.W_OK),
        "ai_provider": llm.describe() if llm.is_configured() else None,
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
                                      use_llm=options.use_llm)
    except Exception as exc:  # noqa: BLE001 - never let the demo show a stack trace
        return JSONResponse(status_code=200, content={
            "state": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "notes": ["The run failed. The scripted scenario can still be shown with "
                      "the live pull turned off."],
            "shipments": [], "risk": {"events": [], "sources": []},
            "summary": {"reroute": 0, "hold": 0, "no-action": 0, "drafts": 0},
        })
