# Signal sources — the exhaustive catalogue

Everything SQRlane could read, grouped by family. **Live today** is what the 42
actually are; everything else is a candidate. Nothing here goes on a slide until
it is wired and answering — the deck says "42 live today, the rest are phase
two" for exactly that reason.

Legend: **F** free/keyless · **K** free but needs a key · **€** paid

---

## 1 · Prediction markets  *(new family — the strongest phase-2 addition)*

| Source | Access | What it gives |
|---|---|---|
| **Kalshi** | K | CFTC-regulated binary contracts. REST + WebSocket + FIX. Weather, hurricanes, geopolitics, rates, elections. A traded probability is a forecast with money behind it. |
| **Polymarket** | K | Larger geopolitical/conflict coverage, on-chain. Thinner on weather. |
| **Metaculus** | K | Forecaster consensus, long-horizon. Slower, but good on structural risk. |
| **Good Judgment Open** | F | Public forecasting tournaments. Low volume, high quality. |

> Why this family matters: every other source tells you what **has** happened.
> A prediction market tells you what the crowd thinks **will**. That is the only
> family that is natively forward-looking, which is what the slide now claims.

## 2 · News, wires and OSINT

GDELT DOC 2.0 (F) · RSS from regional broadcasters and port-adjacent press (F) ·
trade press: gCaptain, Splash 247, Maritime Executive, Lloyd's List (F/€) ·
**ACLED** conflict events (K) · **GDELT GKG** for tone and volume spikes (F) ·
NewsAPI / World News API (K, €)

## 3 · Weather — local and international

**Global:** Open-Meteo (F) · NOAA/NWS (F) · ECMWF open data (F) ·
Copernicus CAMS/C3S (K) · NASA POWER (F)
**National:** DWD Germany (F) · KNMI Netherlands (F) · Météo-France (K) ·
UK Met Office DataHub (K) · AEMET Spain (K) · JMA Japan (F) ·
Hong Kong Observatory (F) · IMD India (F) · BoM Australia (F) ·
NCM UAE, CMA China (varies)
**Tropical:** NOAA NHC (F) · JTWC (F) · RSMC La Réunion (F)

## 4 · Sea state, ocean and maritime

Open-Meteo Marine (F) · **Copernicus Marine Service** (K, waves/currents/sea
level, 350+ providers) · **EMODnet** in-situ marine (F) · NOAA WaveWatch III (F) ·
NDBC buoys (F) · Baltic/North Sea national buoy networks (F)

## 5 · AIS, vessels and port calls  *(new family)*

| Source | Access | Note |
|---|---|---|
| **AISstream.io** | K | Free global AIS over WebSocket. Best free entry point. |
| **AISHub** | K | Free data-sharing co-op; you contribute a feed to receive one. |
| VesselAPI | K/€ | Free tier, 700k vessels, port events. |
| MarineTraffic / Kpler | € | Largest set: port-congestion analytics, predictive ETA, berth calls. |
| Datalastic · VesselFinder · Spire · SeaVantage | € | Self-serve tiers, container-focused options. |

> Note: `CLAUDE.md` currently forbids wiring MarineTraffic / VesselFinder /
> Datalastic / Kpler as paid. That rule was written when "no paid data" was the
> constraint. If phase two has a budget, this is the first rule worth revisiting
> — berth waiting time is the single best leading indicator of port disruption.

## 6 · Ports, canals and terminals

Port of Rotterdam API (K) · Portbase NL (K) · Hamburg Port Authority (F) ·
Port of Antwerp-Bruges (K) · **Panama Canal Authority** advisories and booking
slots (F) · **Suez Canal Authority** (F) · UN/LOCODE reference (F) ·
terminal operator windows: DP World, PSA, HHLA (varies)

## 7 · Inland waterways

**PEGELONLINE** Germany (F, already live) · **Rijkswaterstaat** Waterinfo NL (F) ·
CCNR Rhine commission (F) · Danube Commission (F) · VNF France (F) ·
US Army Corps river gauges (F)

## 8 · Natural hazards

USGS Earthquakes (F, live) · **EMSC** European seismic (F) · NASA EONET (F, live) ·
**GDACS** global disaster alerts (F) · Copernicus Emergency Management (F) ·
FIRMS wildfire (K) · Global Volcanism Program (F) · Pacific Disaster Center (K)

## 9 · Government, regulatory and sanctions

US Federal Register (F, live) · **EUR-Lex** (F) · **EU TARIC** tariff database (K) ·
**OFAC SDN** list (F) · EU consolidated sanctions list (F) · UK OFSI (F) ·
BIS Entity List (F) · WTO notifications (F) · national customs bulletins (varies) ·
**Joint War Committee** listed areas (F — insurance war-risk zones)

## 10 · Freight rates, indices and markets

ECB / Frankfurter FX (F, live) · **Drewry WCI** (€) · **Freightos FBX** (F/€) ·
**Xeneta XSI** (€) · Baltic Exchange dry and container (€) ·
**NY Fed GSCPI** supply-chain pressure index (F) · Ship & Bunker prices (F/€) ·
EIA energy (K) · **Bloomberg Terminal / B-PIPE** (€€) · LSEG Refinitiv (€€)

## 11 · Rail, road and air

EUROCONTROL network operations (K) · FAA NOTAMs (F) · RailNetEurope (varies) ·
DB Netz disruptions (F) · national road authority incident feeds (F) ·
TIMOCOM / Transporeon capacity signals (€)

## 12 · Labour and industrial action

ITF Global (F) · national union bulletins — ver.di, FNV, CGT (F) ·
strike-tracker aggregators (varies) · works-council notices via news

---

## Recommended phase two — six additions, ranked

1. **Kalshi** — the only genuinely forward-looking source. Directly supports the
   "predict before it happens" claim the slide now makes.
2. **AISstream.io** — free AIS. Berth waiting and port dwell are the best
   leading indicators of congestion, and they are numbers, so they go to a
   threshold rather than the model.
3. **GDACS + EMSC** — broadens hazards beyond USGS/EONET at zero cost.
4. **Rijkswaterstaat** — completes the Rhine corridor picture on the Dutch side.
5. **OFAC SDN + EU sanctions** — sanctions are a step change, not a gradient;
   cheap to poll and unambiguous when they fire.
6. **NY Fed GSCPI** — one monthly number that contextualises everything else.

Each is free or free-tier, each is its own function in `signals.py`, and none
is load-bearing. Bloomberg is the one worth deferring: expensive, and its
unique value over the free set is thin for this use case.
