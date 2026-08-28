#!/usr/bin/env python3
"""Render a deck SVG to PNG. Chromium's headless viewport is 87px shorter than
--window-size, so we over-size the window and crop back to the exact slide box."""
import subprocess, sys, pathlib, tempfile
from PIL import Image

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
W, H, CHROME_GUTTER = 1920, 1080, 87

def render(svg: pathlib.Path, out: pathlib.Path, scale: int = 2):
    with tempfile.TemporaryDirectory() as td:
        page = pathlib.Path(td) / "p.html"
        page.write_text(
            '<!doctype html><meta charset="utf-8">'
            '<style>html,body{margin:0;padding:0;background:#fff;overflow:hidden}'
            f'img{{display:block;width:{W}px;height:{H}px}}</style>'
            f'<img src="{svg.resolve().as_uri()}">')
        subprocess.run([CHROME, "--headless", "--no-sandbox", "--disable-gpu",
                        "--hide-scrollbars", f"--force-device-scale-factor={scale}",
                        f"--window-size={W},{H + CHROME_GUTTER}",
                        f"--screenshot={out}", str(page)],
                       capture_output=True, check=True)
    im = Image.open(out).crop((0, 0, W * scale, H * scale))
    im.save(out)
    return im.size

if __name__ == "__main__":
    for a in sys.argv[1:] or ["slide-01-the-what.svg"]:
        s = pathlib.Path(a)
        o = s.with_name(s.stem + "-preview.png")
        print(f"{s.name} -> {o.name} {render(s, o)}")
