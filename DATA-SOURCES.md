# DATA-SOURCES.md — everything the desk reads

`public-apis/public-apis` catalogues thousands of free APIs. It is a directory, not a
shortlist: it will not tell you which of them a freight desk would actually look at. This
file is that shortlist, and it says for each source **which catalogue entry it is**, **what
it tells a forwarder**, and **how it is classified** once it arrives.

**The shape of it.** A trade lane is not moved by news alone. It is moved by a strike, a
gale, a river, an earthquake, a tariff notice and — when the invoice lands — an exchange
rate. Those arrive in different formats from different institutions, and a desk that only
watches headlines is reading a summary of some of them, late. So Lanewatch reads **42
sources across six families**, all of them free and keyless, and puts the whole picture on
one screen before deciding anything.

**The rule that replaced "wire CORE only".** Breadth is now the point, so the old rule —
three sources, nothing else — no longer holds. What holds instead is the reason behind it:
**no source may be load-bearing.** Every one is read in its own small function, inside a
shared time budget, and a source that is down, slow or reshaped is reported as failed and
skipped. Forty-two sources are safe to run in front of an audience precisely because none
of them can take the run down. `tests/test_signals_read_wide_and_fail_soft.py` holds that.

**How to read the tables**
- **Family** = which of the six signal families it belongs to.
- **Tier** = `lane` if a reading can put an exception on a booking, `context` if it is real
  and moves nothing on this board. See [The two tiers](#the-two-tiers).
- **Key?** = needs a free signup or an API key, or not. Everything wired here is *no*.
- Free tiers and limits **change** — check the current numbers when you wire one.

---

## The two tiers

Not every real signal is a risk, and pretending otherwise is the easiest lie a dashboard
can tell.

- **`lane`** — the reading maps onto a chokepoint that some route on the board passes
  through, so it can become an event, reach the Route Advisor, and move a booking.
- **`context`** — the reading is real, read live, and touches nothing on this board today:
  the ECB rate a reroute is billed at, a hurricane warning over a US port this board does
  not call at, a typhoon signal over a load port that is not modelled as a chokepoint. It
  is rendered in its own panel, labelled *"read live on this run; none of it moves a
  booking on this board"*, and it decides nothing.

A test asserts a `context` source never emits an event. That line is the difference between
a terminal that shows you the world and a dashboard that inflates its own alarm count.

---

## 1. News — the wires and the press closer to the event  ·  31 sources

A disruption is known locally long before it is news globally: the union announces it, the
regional broadcaster carries it, and only then does an international wire pick it up. A
monitor watching the wires is structurally late because it is reading *downstream*. So the
news family reads **outward from the corridors**, not from the newsroom.

| Source | Catalogue entry | What it gives you | Key? |
|---|---|---|---|
| **GDELT DOC 2.0** — 11 queries | *News → GDELT* | Global news backbone, ~15 min refresh, filterable by keyword, language and country. One query pinned per corridor: North Range, Low Countries, Western Med and the Rhone, Red Sea and the Gulf, Asian gateway ports, the Turkish straits, Panama and the Americas, plus customs/tariffs/sanctions. | No |
| **RSS** via `feedparser` — 20 feeds | *(direct publisher feeds)* | Regional broadcasters and papers on the corridors' doorsteps — NDR Hamburg, tagesschau, DW, NOS, VRT, RTVE, El País, France Info, Le Monde, ANSA, NHK, Al Jazeera (Arabic and English), DW and France 24 in Arabic, The Straits Times, Times of India — plus the narrow trade press where nearly every item is on topic: gCaptain, Splash 247, The Maritime Executive. | No |

Both are prose, so both go through the cheap keyword prefilter and then to the model, which
makes the actual relevance / chokepoint / severity call.

> **Reuters is deliberately not wired.** It is named in the research, but it retired its
> public RSS feeds — and a dead feed is a live failure.

---

## 2. River gauges — the inland leg  ·  3 sources

| Source | Catalogue entry | What it gives you | Family | Tier |
|---|---|---|---|---|
| **PEGELONLINE** (German WSV) | *(German federal waterways API)* | Rhine water levels at Kaub, Duisburg-Ruhrort and Emmerich, mapped to the `RHINE` chokepoint. Kaub is the gauge the barge market actually watches. | water | lane |

Readings are numbers, so they are classified by threshold (`GAUGE_BANDS`), not by the
model. Confirmed working against the live host in production.

---

## 3. Weather & sea state  ·  3 sources

| Source | Catalogue entry | What it gives you | Tier |
|---|---|---|---|
| **Open-Meteo** — port weather | *Weather → Open-Meteo* (Auth: No, HTTPS: Yes, CORS: Yes) | Wind and gusts over Hamburg, Rotterdam, Antwerp and Fos-sur-Mer, in one request. A container terminal loses crane hours around gale force 8 and stops near force 10 — `WIND_BANDS`. | lane |
| **Open-Meteo Marine** — sea state | *Weather → Open-Meteo* (marine endpoint) | Significant wave height at the Suez approaches, Bab-el-Mandeb and the Cape of Good Hope: the three points a box on this board actually rounds — `WAVE_BANDS`. | lane |
| **Hong Kong Observatory** | *Weather → Hong Kong Obervatory* (Auth: No) | The warnings in force over the Pearl River Delta. Two of the bookings load there and a T8 signal shuts Yantian and Hong Kong for a day — but load ports are not modelled as chokepoints, so this informs and decides nothing. | context |

Coordinates are **not** kept here: `data/geo.json` already carries a real lat/lon for every
chokepoint, so the watch lists in `config.py` are chokepoint ids and the coordinates are
read from the map. One source of truth.

---

## 4. Natural hazards  ·  2 sources

| Source | Catalogue entry | What it gives you | Tier |
|---|---|---|---|
| **USGS Earthquake Hazards Program** | *Science & Math → USGS Earthquake Hazards Program* (Auth: No) | Real-time seismic activity. A quake is mapped to the nearest watched chokepoint and **dropped if none is within 300 km** — a magnitude 7 in the South Pacific is real and is not this board's problem. | lane |
| **NASA EONET** | *Science & Math → NASA* (Auth: No) | NASA's natural-event tracker: wildfires, severe storms, floods and volcanoes, each with a coordinate, mapped onto a corridor the same way. This is the live source the authored `france` scenario — a wildfire on a land leg — is a rehearsal of. | lane |

---

## 5. Government & regulatory  ·  2 sources

| Source | Catalogue entry | What it gives you | Tier |
|---|---|---|---|
| **Federal Register** | *Government → Federal Register* (Auth: No) | The daily journal of the US government, searched for tariff, sanctions, customs and port-security filings. A rule lands here days before a trade paper writes it up. It is **prose**, so unlike the rest of this half it goes to the classifier rather than to a threshold. | lane |
| **US National Weather Service** | *Weather → US Weather* (Auth: No, CORS: Yes) | Active severe and extreme alerts over the US port states. No booking on this board discharges there, so it is context — wired because it is the same read as everything else, and already connected the day a transatlantic lane is on the board. | context |

> The Federal Register is a US journal and this is a European board, which is rather the
> point: what Washington publishes moves an Asia–Europe lane whether or not the box ever
> touches a US port.

---

## 6. Markets  ·  1 source

| Source | Catalogue entry | What it gives you | Tier |
|---|---|---|---|
| **Frankfurter** | *Currency Exchange → Frankfurter* (Auth: No, CORS: Yes) | The ECB's own daily reference rates, EUR against USD, CNY and GBP. A reroute is decided on a relative cost index; the rate is what turns that index into what the customer is actually invoiced, which is why an ops lead wants it on the same screen — and why it is not a risk event. | context |

---

## Considered and deliberately not wired

| Source | Why not |
|---|---|
| **Reuters RSS** | Retired its public feeds. A dead feed is a live failure. |
| **MarineTraffic, VesselFinder, Datalastic, Kpler** | All paid or credit-metered since the AIS market consolidated. |
| **AISstream.io** | Genuinely free, but a WebSocket stream rather than a request — a different failure model, and the board does not need live vessel positions to make a decision. |
| **OpenSanctions** | Listed as keyless, but the hosted API now gates behind a key. Wiring it would break the "no key" claim. |
| **Strait of Hormuz Ship Monitor** | On-theme and keyless, but single-vendor with an undocumented response shape. Not worth a live dependency the schema of which could move. |
| **USGS Water Services** | The same idea as PEGELONLINE for US rivers. Real, and redundant here — a second river authority adds a parse to maintain and no new kind of signal. |
| **NewsAPI.org, World News API** | Need keys, and the free tiers are developer-only. |
| **OpenStreetMap Nominatim** | Not needed: the map is inlined SVG drawn from `data/geo.json`, with no tile server and no geocoding call. |

---

## The AI brains — runtime inference (pick ONE)

These are the calls the agents make when they *run*, separate from what pays for building.

| Provider | Notes | Key? |
|---|---|---|
| **Groq** | Free tier, very fast, generous. **Recommended default.** | Yes (free) |
| **Google Gemini** (AI Studio) | Free tier, solid. | Yes (free) |
| **Ollama** (local) | Fully free, no key — needs decent hardware. Zero limits, full privacy. | No |

Pick one and put its key in `.env` (SETUP.md step 4–5). **Never hard-code a model name**:
providers retire models, and a retired name 404s in a way that looks exactly like a broken
key. `llm.py` resolves the model at runtime against the provider's own list.

---

## Honest notes

- **Free tiers change.** Verify current limits when you wire one; don't design around a
  number that may have moved.
- **None of this has been witnessed from this sandbox.** Its egress policy blocks every
  third-party host with a 403 at the proxy, so the new sources are built to their published
  shapes and tested against stubs. PEGELONLINE was in exactly this position until it was
  confirmed in production. Check `python -m src.signals` on a real connection.
- **Breadth is safe only because nothing is load-bearing.** If you add a source, add it as
  its own function, inside the budget, reporting its own failure. If a new source can make
  the cycle fail, it is wired wrong.

---

### Prompt for Claude Code (adding a source)

> "Read DATA-SOURCES.md. Add `<source>` to `src/signals.py` as its own small function
> returning events, items or context, register it in `SIGNAL_SOURCES` with a family and a
> tier, and put its endpoint and thresholds in `config.py`. It must be keyless, it must
> fail soft, and if it is a `context` source it must never emit an event."
