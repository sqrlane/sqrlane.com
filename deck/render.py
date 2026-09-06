#!/usr/bin/env python3
"""Render a deck SVG to PNG. Chromium's headless viewport is 87px shorter than
--window-size, so we over-size the window and crop back to the exact slide box."""
import functools, glob, os, pathlib, re, shutil, subprocess, sys, tempfile, time
from PIL import Image

W, H, CHROME_GUTTER = 1920, 1080, 87

# --- finding a browser ------------------------------------------------------
# This used to be one hard-coded path to one Playwright build, which made the
# script unrunnable anywhere but the sandbox it was written in - and the path
# pinned chromium-1194 exactly, so a Playwright bump would have broken it even
# there. Same failure as a hard-coded model name: it works until the day the
# thing behind it is renamed, and then it is a scheduled outage.
#
# Order matters. The bundled Playwright build is tried first because it is the
# one the committed previews were drawn against, and a different browser can
# hint fonts differently; everything after it is so the script runs on a
# laptop at all. Set DECK_CHROME to override the search entirely.
CHROME_ENV = "DECK_CHROME"

_GLOBS = [
    "/opt/pw-browsers/chromium-*/chrome-linux/chrome",
    os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux/chrome"),
    os.path.expanduser(
        "~/AppData/Local/ms-playwright/chromium-*/chrome-win/chrome.exe"),
]

_NAMES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
          "chrome", "msedge", "microsoft-edge"]

_PATHS = {
    "win32": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ],
    "darwin": [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ],
    "linux": [
        "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
        "/snap/bin/chromium",
    ],
}


def _newest(pattern):
    """Highest-numbered match for a versioned glob. Plain sorting puts
    chromium-999 above chromium-1194, so compare the digits as numbers."""
    hits = [p for p in glob.glob(pattern) if os.path.exists(p)]
    return sorted(hits, key=lambda p: [int(n) for n in re.findall(r"\d+", p)] or [0])


@functools.lru_cache(maxsize=1)
def find_chrome():
    """First usable Chrome/Chromium/Edge, or a SystemExit naming what was tried.
    Cached: ten slides should not mean ten filesystem sweeps."""
    override = os.environ.get(CHROME_ENV)
    if override:
        if pathlib.Path(override).exists():
            return override
        raise SystemExit(f"{CHROME_ENV} is set to {override!r}, which does not exist")

    for pattern in _GLOBS:
        found = _newest(pattern)
        if found:
            return found[-1]
    for name in _NAMES:
        found = shutil.which(name)
        if found:
            return found
    for p in _PATHS.get(sys.platform, []):
        if os.path.exists(p):
            return p

    raise SystemExit(
        "no Chrome/Chromium found. Looked for a bundled Playwright build, then "
        + ", ".join(_NAMES) + " on PATH, then the usual install paths for "
        + sys.platform + f".\nSet {CHROME_ENV} to a browser binary to override.")


def render(svg: pathlib.Path, out: pathlib.Path, scale: int = 2):
    t0 = time.time()
    with tempfile.TemporaryDirectory() as td:
        page = pathlib.Path(td) / "p.html"
        page.write_text(
            '<!doctype html><meta charset="utf-8">'
            '<style>html,body{margin:0;padding:0;background:#fff;overflow:hidden}'
            f'img{{display:block;width:{W}px;height:{H}px}}</style>'
            f'<img src="{svg.resolve().as_uri()}">')
        r = subprocess.run([find_chrome(), "--headless", "--no-sandbox", "--disable-gpu",
                        "--hide-scrollbars", f"--force-device-scale-factor={scale}",
                        f"--window-size={W},{H + CHROME_GUTTER}",
                        f"--screenshot={out.resolve()}", str(page)],
                       capture_output=True)
        # Chrome must have written the file ON THIS RUN. It exits 0 having
        # written nothing if the screenshot path is not writable - and with a
        # preview already sitting there, PIL then re-crops and re-saves the OLD
        # image, so the run looks successful, the mtime updates, and git shows
        # a modified file. That is how these previews went ten commits stale
        # carrying a tagline the deck had already stopped using. An mtime test
        # is what catches it; os.path.exists cannot.
        if not out.exists() or out.stat().st_mtime < t0:
            raise SystemExit("chrome wrote no screenshot for %s\n%s"
                             % (svg.name, r.stderr.decode(errors="replace")[:500]))
    im = Image.open(out).crop((0, 0, W * scale, H * scale))
    im.save(out)
    return im.size


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--which":          # which browser would be used
        print(find_chrome())
        sys.exit(0)
    for a in args or ["slide-01-the-what.svg"]:
        s = pathlib.Path(a)
        o = s.with_name(s.stem + "-preview.png")
        print(f"{s.name} -> {o.name} {render(s, o)}")
