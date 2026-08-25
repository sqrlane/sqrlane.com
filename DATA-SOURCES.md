# DATA-SOURCES.md — the free APIs worth using (curated)

Yes, the big list helps — but only as a *directory*. `public-apis/public-apis` catalogues thousands of APIs; it won't tell you which ones fit *this* build. This file is that shortlist, mapped to the components that consume it.

**The one rule:** wire the **CORE** sources only. Every extra source is one more thing that can break live in front of an audience. Three sources carry the whole story — GDELT + multilingual RSS + Rhine levels.

**How to read the tables**
- **CORE** = use now. **OPTIONAL** = only if you want extra polish.
- **Key?** = needs a free signup/API key, or not.
- Free tiers and limits **change** — check the current numbers when you sign up.

---

## 0. Directories to browse (don't drown in them)

| Repo | Use it for |
|---|---|
| `public-apis/public-apis` | The main list. Browse the **News**, **Weather**, **Transportation**, and **Geocoding** categories only. |

That's the one to bookmark. There are mirror lists (`public-api-lists`, etc.) — you don't need them; they're the same idea with more noise.

---

## 1. Risk Monitor — news + disruption signals (the real, core part)

This is where the credibility and the differentiation live. Spend your effort here.

| Source | What it gives you | Key? | Priority |
|---|---|---|---|
| **GDELT DOC 2.0 API** | Global news, updates ~every 15 min, filter by keyword / language / country. The backbone of the monitor. | No | **CORE** |
| **RSS feeds** via the `feedparser` Python library | Direct feeds from Reuters, DW, Al Jazeera (English **and** Arabic), gCaptain (maritime), plus German sources (tagesschau, NDR) and union press (ver.di). | No | **CORE** — this is where the multilingual-earliness edge lives |
| **PEGELONLINE** (German WSV public API) | Rhine water levels. Low Rhine = barge disruption on your RHINE chokepoint. A DACH-specific signal that instantly reads as domain depth. | No | **CORE-ish** — cheap, easy, and a real differentiator |
| **Open-Meteo** | Free weather/marine forecasts; storms hitting ports or lanes. | No | OPTIONAL |
| **NewsAPI.org** | Extra headline coverage. Note: free tier is **developer-only, ~100 requests/day** — fine for testing, not for a live product. | Yes | OPTIONAL (backup) |
| **World News API** | More multilingual news, freemium. | Yes | OPTIONAL |

> Start with the first three. They're all keyless and they tell the entire demo story.

---

## 2. Shipments & routes — mostly DUMMY, so live data is optional

Your shipments are **synthetic** (see DATASET.md). You do **not** need live vessel data to run the demo. Only reach here if you want a "real ship moving on a map" flourish.

| Source | What it gives you | Key? | Priority |
|---|---|---|---|
| **AISstream.io** | The one genuinely **free** real-time AIS vessel-position feed (via WebSocket). Good for a live-vessel flourish. Slightly more work — it's a stream, not a simple request. | Yes (free) | OPTIONAL |
| **OpenStreetMap Nominatim** | Geocoding (place → coordinates) if the dashboard shows a map. Respect its usage limits. | No | OPTIONAL |

> **Skip these:** MarineTraffic, VesselFinder, Datalastic, Kpler — all paid/credit now after the market consolidated. Not worth it for a demo.

---

## 3. Comms Agent — nothing needed

The agent **drafts** emails and displays them; it sends nothing. **No API required.** (If a much later version ever actually sent mail, you'd add a transactional email API then — not now.)

---

## 4. The AI brains — runtime inference (CORE, pick ONE)

These are the calls your agents make when they *run*. This is separate from Claude Code Max, which pays for *building*, not running.

| Provider | Notes | Key? | Priority |
|---|---|---|---|
| **Groq** | Free tier, very fast, generous. **Recommended default.** | Yes (free) | **CORE** |
| **Google Gemini** (AI Studio) | Free tier, solid. | Yes (free) | CORE alt |
| **Ollama** (local) | Fully free, no key, runs on your machine — needs decent hardware. Zero limits, full privacy. | No | CORE alt |

Pick one and put its key in `.env` (SETUP.md step 4–5).

---

## The starter set — if you only touch 5 things

1. **GDELT** — global news backbone (no key)
2. **`feedparser` + a handful of RSS feeds, including one German** — the earliness edge (no key)
3. **PEGELONLINE** — Rhine levels, the domain-depth flex (no key)
4. **One free LLM tier (Groq)** — the agents' brain
5. **`public-apis` repo bookmarked** — for when you want to browse for more later

Everything else in this file is optional. Resist adding it until the core demo works end to end.

---

## Honest notes

- **Free tiers change.** Verify current limits at signup; don't design around a number that may have moved.
- **Live maritime data is mostly paid now.** You don't need it — dummy shipments cover the demo.
- **Don't wire everything.** In a live demo, fewer live dependencies = fewer ways to fail. The three keyless sources (GDELT + multilingual RSS + Rhine) are the ones that matter.

---

### Prompt for Claude Code (Phase 1)

> "Read DATA-SOURCES.md. In the Risk Monitor, wire only the CORE sources: GDELT, a small set of RSS feeds including at least one German-language feed, and PEGELONLINE for Rhine levels. Skip everything marked OPTIONAL for now. Keep each source in its own small function so I can add or remove one without touching the others."
