"""Vercel entrypoint.

Vercel serves Python from files under `api/`, so this is the door the platform
knocks on. It adds nothing of its own - it puts the repository root on the
import path and re-exports the same FastAPI app that `uvicorn src.app:app`
serves locally, so there is exactly one application, not two.

`vercel.json` rewrites every path here, which is why the dashboard at `/` and
the `POST /run` endpoint both arrive at this one function.
"""

import sys
from pathlib import Path

# Vercel puts this file's own directory on sys.path, not the project root, so
# `import src...` would fail without this line.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.app import app  # noqa: E402  (must follow the sys.path line above)

# Vercel's Python runtime looks for a module-level ASGI application called
# `app`. Re-exported explicitly so nothing prunes it as an unused import.
__all__ = ["app"]
