# static/video — the hero reel's clips

The landing page's hero plays a background reel: three clips, one at a time,
crossfading. `src/app.py` serves this directory at `/video/<name>.mp4`, so the
page fetches nothing from another host — the same promise the self-hosted fonts
keep, and `tests/test_the_pages_keep_their_promises.py` fails the build if a
clip is ever pointed at a CDN.

The three clips are committed. Their absence is still a supported state -
`/video/...` answers 404, the reel never reveals itself, and the hero renders
exactly as it does without it - so removing one breaks nothing.

**These are iStock comp files and carry a Getty watermark.** They were
committed on the owner's instruction, over a flagged objection: comps are
licensed for layout evaluation, not publication, and the watermark is visible
in the frame. Replace them with licensed downloads under the same filenames.

## What the page expects

| File | Shows |
|---|---|
| `01-container-yard.mp4` | a container yard from above |
| `02-terminal-queue.mp4` | trucks queued at a terminal |
| `03-road-corridor.mp4` | a road corridor from the air |

Drop files with those names in and they play. Nothing else needs changing: the
reel measures each clip's own first frame and works out the opacity that puts
it at the same weight behind the copy as the others, so replacement footage of
any brightness composites correctly without a re-tune.

## Before putting footage here

- **It has to be licensed for web use.** What is here now is not: they are
  iStock comps, watermarked, licensed for layout evaluation only.
- **Keep them small.** These are decoration on a first screen that reads fine
  without them. Around 1–2 MB each, 720p or less, no audio track.
- **Prefer footage that is not near-white.** The page background is `#fafafa`.
  A fourth clip — an operations desk at a data wall — measured 176 mean
  luminance against that 250 and composited to within a few points of plain
  background even at the opacity ceiling: a dead beat in the rotation. Under
  about 160 is safe.

## Changing which clips play

The `<video class="reel-v">` elements at the top of `static/landing.html`'s
hero. One element per clip, in order. Everything else — timing, ticks, the
crossfade, the fallback — follows from how many there are.
