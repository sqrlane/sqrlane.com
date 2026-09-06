# static/video — the background clips

Footage plays behind four blocks. The landing hero rotates three clips, one at
a time, crossfading; the landing page's closer holds a single one behind the
sign-up block; `/how-it-works` and `/product` each hold a single one behind
their page head. `src/app.py` serves this directory at `/video/<name>.mp4`, so neither
page fetches anything from another host — the same promise the self-hosted fonts
keep, and `tests/test_the_pages_keep_their_promises.py` fails the build if a
clip is ever pointed at a CDN.

All six clips are committed. Their absence is still a supported state -
`/video/...` answers 404, the band never reveals itself, and every page renders
exactly as they do without it - so removing one breaks nothing.

**These are watermarked comp files** - 01 to 04 and 06 are iStock comps carrying
a Getty mark, 05 is a Filmsupply comp carrying a FILMSUPPLY mark across the
centre of frame. They were
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
| `05-port-aerial.mp4` | an aerial view of a container port | the landing closer |
| `06-assembly-line.mp4` | robot arms working a car body down a line | `/product` |

Drop files with those names in and they play. Nothing else needs changing: every
block measures the clip's own first frame and works out the opacity that puts it
at a fixed weight behind the copy, so replacement footage of any brightness
composites correctly without a re-tune.

**The opacity re-tunes itself; the wash does not.** The landing closer's wash was
measured against `05-port-aerial.mp4` specifically - its lower half is held clean
because that clip, at the opacity the script gives it, dropped the block's
`.note` to 2.32:1 from 3.23:1, and the note is the line disclaiming that the form
is not wired to anything. Replace that clip with a brighter one and the wash is
heavier than it needs to be; replace it with a darker one and it may not be
enough. Re-measure, do not assume.

## Before putting footage here

- **It has to be licensed for web use.** What is here now is not: they are
  iStock comps, watermarked, licensed for layout evaluation only.
- **Keep them small.** These are decoration on a first screen that reads fine
  without them. Around 1–2 MB each, 720p or less, no audio track.
  `06-assembly-line.mp4` is 3.3 MB, over that guideline - it is fetched only
  after `load` and only when the connection is not metered, so it costs the
  first screen nothing, but it is the one to re-encode first if this directory
  ever needs to shrink.
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
the fallback) follows from how many there are. The landing closer has a single
`<video class="signup-reel-v">` in its `.signup`, and `/how-it-works` and
`/product` a single `<video class="reel-v">` in their `.phead`.

The closer's classes are prefixed (`.signup-reel*`) because `landing.html`
already owns `.reel`/`.reel-v`/`.reel-wash` for the hero, whose rule fixes a
440px height. Reusing the name gives the closer the hero's geometry.

**The four blocks wash the footage differently, and that is not drift.** The
landing hero's copy is centred, so a radial centred with it protects the type
and lets the footage out at every edge; the closer starts from the same radial
but stops the footage above its lightest line rather than trying to veil it.
`/how-it-works`'s and `/product`'s headers are left-aligned and
nearly fill the band, so their wash is decomposed into one gradient across (which
protects the column the words are in) and one down (which dissolves the band
into the page at top and bottom). All are commented with the contrast each
piece of type actually measures. Re-measure before moving a stop — the eyebrow
is the page's lightest type and has the least to give.

**Those two pages share a shape, not a set of stops, and the difference is
worth knowing before copying one into the other.** `/product`'s header is
taller and its lines run further right, so `/how-it-works`' stops carried over
verbatim put its body copy at **3.42:1** — under the 4.5 floor, with every
other piece of type on the page comfortably clear. Body copy is what pays
first on both. Measure the worst pixel behind each element's box, at the worst
frame of the loop, at 1280 **and** at 375; a ratio read off whichever frame
happened to be on screen is not a measurement.
