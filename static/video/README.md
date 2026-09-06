# static/video — the background clips

Two pages play footage behind their header. The landing hero rotates three
clips, one at a time, crossfading; `/how-it-works` holds a single one behind its
page head. `src/app.py` serves this directory at `/video/<name>.mp4`, so neither
page fetches anything from another host — the same promise the self-hosted fonts
keep, and `tests/test_the_pages_keep_their_promises.py` fails the build if a
clip is ever pointed at a CDN.

All four clips are committed. Their absence is still a supported state -
`/video/...` answers 404, the band never reveals itself, and both pages render
exactly as they do without it - so removing one breaks nothing.

**These are iStock comp files and carry a Getty watermark.** They were
committed on the owner's instruction, over a flagged objection: comps are
licensed for layout evaluation, not publication, and the watermark is visible
in the frame. Replace them with licensed downloads under the same filenames.

## What the page expects

| File | Shows | Used by |
|---|---|---|
| `01-container-yard.mp4` | a container yard from above | the landing hero |
| `02-terminal-queue.mp4` | trucks queued at a terminal | the landing hero |
| `03-road-corridor.mp4` | a road corridor from the air | the landing hero |
| `04-control-room.mp4` | an operations desk at a data wall | `/how-it-works` |

Drop files with those names in and they play. Nothing else needs changing: both
pages measure the clip's own first frame and work out the opacity that puts it
at a fixed weight behind the copy, so replacement footage of any brightness
composites correctly without a re-tune.

## Before putting footage here

- **It has to be licensed for web use.** What is here now is not: they are
  iStock comps, watermarked, licensed for layout evaluation only.
- **Keep them small.** These are decoration on a first screen that reads fine
  without them. Around 1–2 MB each, 720p or less, no audio track.
- **Prefer footage that is not near-white.** The page background is `#fafafa`.
  `04-control-room.mp4` measures 176 mean luminance against that 250, so even
  at the landing hero's opacity ceiling it composites to within a few points of
  plain background — a dead beat between two darker clips, which is why it was
  cut from the rotation. Under about 160 is safe **for the landing hero**. It
  is fine on `/how-it-works`, where it is the only clip and has nothing to
  match: that page raises the ceiling to 1 and lets its wash carry the
  contrast instead. A clip that has to sit in the rotation still needs to be
  under 160.

## Changing which clips play

The `<video class="reel-v">` elements at the top of `static/landing.html`'s
hero, one per clip, in order — everything else there (timing, the crossfade,
the fallback) follows from how many there are. `/how-it-works` has a single
such element in its `.phead`.

**The two pages wash the footage differently, and that is not drift.** The
landing hero's copy is centred, so a radial centred with it protects the type
and lets the footage out at every edge. This page's header is left-aligned and
nearly fills the band, so its wash is decomposed into one gradient across (which
protects the column the words are in) and one down (which dissolves the band
into the page at top and bottom). Both are commented with the contrast each
piece of type actually measures. Re-measure before moving a stop — the eyebrow
is the page's lightest type and has the least to give.
