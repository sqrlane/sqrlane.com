"""config.py - every knob in one place: paths, provider settings, source lists.

Nothing here does any work. If you want to add or remove a news source, change a
model, or retune a threshold, this is the only file you touch.
"""

import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")     # absent on a deployed host; env vars are used instead


def _env_int(name: str, default: int) -> int:
    """Read an int from the environment, falling back if unset or nonsense."""
    try:
        return int(os.getenv(name) or default)
    except ValueError:
        return default


# Serverless hosts (Vercel, Lambda) give you a read-only application directory
# and a short execution ceiling. Both change where state goes and how long the
# live pull may take, so detect it once here rather than scattering checks.
SERVERLESS = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))

# --- Paths -----------------------------------------------------------------

DATA_DIR = ROOT / "data"
CHOKEPOINTS_FILE = DATA_DIR / "chokepoints.json"
ROUTES_FILE = DATA_DIR / "routes.json"
SHIPMENTS_FILE = DATA_DIR / "shipments.json"
INJECTED_EVENTS_FILE = DATA_DIR / "injected_events.json"
SCENARIOS_FILE = DATA_DIR / "scenarios.json"

# risk_state.json is the one file written at runtime. On a serverless host the
# app directory is read-only and only the temp directory can be written, so the
# state file goes there. Same process reads it back within the request, which is
# all this needs - there is no database and no state kept between requests.
_state_dir = os.getenv("RISK_STATE_DIR")
if not _state_dir:
    _state_dir = tempfile.gettempdir() if (SERVERLESS or not os.access(ROOT, os.W_OK)) else str(ROOT)
RISK_STATE_FILE = Path(_state_dir) / "risk_state.json"

# --- AI provider -----------------------------------------------------------
# Read by llm.py and nowhere else. Swap providers by editing LLM_PROVIDER in .env.

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").strip().lower()

# Set LLM_MODEL in .env to pin a specific model. Left empty (the default), the
# model is discovered at runtime - see GROQ_MODEL_PREFERENCES below.
LLM_MODEL = os.getenv("LLM_MODEL", "").strip()

DEFAULT_MODELS = {
    "gemini": "gemini-2.0-flash",
    "ollama": "llama3.1",
}

# Groq retires and renames models regularly, and a hard-coded name that has been
# retired fails with a 404 that looks exactly like a broken key - the whole demo
# silently drops to the deterministic fallback. So the Groq model is RESOLVED AT
# RUNTIME against /openai/v1/models: whatever this key can actually run.
#
# This list is only a preference order among what is available. If none of these
# are offered, llm.py picks the most capable chat model the key does have, so a
# lineup this list has never heard of still works.
GROQ_MODEL_PREFERENCES = [
    "llama-3.3-70b-versatile",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "openai/gpt-oss-120b",
    "moonshotai/kimi-k2-instruct",
    "qwen/qwen3-32b",
    "openai/gpt-oss-20b",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]

# Never usable for this job: audio, safety classifiers, embeddings.
GROQ_MODEL_EXCLUDE = ("whisper", "tts", "guard", "embed", "moderation", "rerank")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").strip()

LLM_TIMEOUT_SECONDS = 60
LLM_MAX_RETRIES = _env_int("LLM_MAX_RETRIES", 4)

# A free tier rate-limits by the minute, so the old 1s + 2s backoff gave up long
# before the window reopened. Groq says how long to wait in a retry-after header;
# honour it, but never wait longer than this in total across one call, because a
# serverless function is killed at its own ceiling and a stalled retry would take
# the whole cycle down with it.
RETRY_WAIT_BUDGET_SECONDS = _env_int("RETRY_WAIT_BUDGET_SECONDS", 12 if SERVERLESS else 40)
LLM_TEMPERATURE = 0.0        # classification should be repeatable

# --- HTTP ------------------------------------------------------------------

# Deliberately short. A dead source fails fast; the danger in a live demo is a
# source that is merely SLOW, because it stalls the whole run.
HTTP_TIMEOUT_SECONDS = _env_int("HTTP_TIMEOUT_SECONDS", 6 if SERVERLESS else 8)

# Hard ceiling on the entire live pull. Once this is spent, whatever has not
# been read is marked skipped and the cycle moves on. Sixty sources at eight
# seconds each would otherwise be eight minutes - so this, plus reading every
# family concurrently, is what actually keeps the run on time.
#
# Deployed, the ceiling is the function's own timeout, and the LLM calls that
# follow the pull need most of it. Both are tunable by environment variable so
# a slow deploy can be trimmed without a code change.
LIVE_PULL_BUDGET_SECONDS = _env_int("LIVE_PULL_BUDGET_SECONDS", 10 if SERVERLESS else 25)

USER_AGENT = "trade-risk-agent/0.1 (demo prototype; contact: local)"

# ===========================================================================
# Risk Monitor sources 1-3 - the prose and the river (read by risk_monitor.py)
#
# The rule used to be "wire CORE only: every extra source is one more thing
# that can break live in front of an audience". Breadth is the point now, so
# what holds instead is the reason behind that rule - NO SOURCE MAY BE
# LOAD-BEARING. Each is its own small function, inside a shared budget,
# reporting its own failure; the families are read concurrently. See
# DATA-SOURCES.md, and src/signals.py for sources 4-16.
#
# (These numbers are the sources; the SIX FAMILIES they group into - news,
# river gauges, weather & sea state, natural hazards, government, markets -
# are what the board shows. FAMILY_LABELS in risk_monitor.py owns that.)
# ===========================================================================

# --- 1. GDELT DOC 2.0 - global news backbone, no key, refreshes ~15 min -----
# Each query is deliberately narrow. `sourcelang:german` is what makes the
# "we saw it in German first" claim true - keep at least one non-English query.

GDELT_ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_TIMESPAN = "3d"
GDELT_MAX_RECORDS = 20
# Be polite - GDELT throttles rapid calls. But eleven queries at 1.5s is more
# waiting than a serverless budget has in total, so it is much shorter there.
# GDELT runs alongside the other families rather than after them, so this
# waiting overlaps their reads instead of delaying them.
GDELT_PAUSE_SECONDS = _env_int("GDELT_PAUSE_MS", 400 if SERVERLESS else 1500) / 1000

GDELT_QUERIES = [
    {"label": "port disruption", "language": "en",
     "query": '("port strike" OR "port closure" OR "port congestion" OR "terminal closed")'},
    {"label": "North Range ports - regional", "language": "de",
     "query": "(Hafenstreik OR Warnstreik OR Hafenarbeiter OR Niedrigwasser) sourcelang:german"},
    {"label": "Red Sea / Gulf - regional", "language": "ar",
     "query": "(ميناء OR إضراب OR البحر الأحمر) sourcelang:arabic"},
    {"label": "Western Med / Rhone - regional", "language": "fr",
     "query": "(port OR grève OR blocage) sourcelang:french"},
    {"label": "Low Countries ports - regional", "language": "nl",
     "query": "(haven OR staking OR Rotterdam) sourcelang:dutch"},
    {"label": "Red Sea / Suez routing", "language": "en",
     "query": '("Red Sea" OR "Suez Canal") (attack OR closure OR diverted OR delay)'},
    {"label": "North Range ports - wires", "language": "en",
     "query": "(Hamburg OR Rotterdam OR Antwerp) (strike OR congestion OR backlog)"},
    {"label": "Asian gateway ports - regional", "language": "zh",
     "query": "(港口 OR 罢工 OR 台风 OR 拥堵) sourcelang:chinese"},
    {"label": "Turkish straits & East Med - regional", "language": "tr",
     "query": "(liman OR grev OR boğaz OR tersane) sourcelang:turkish"},
    {"label": "Panama & the Americas - regional", "language": "es",
     "query": "(canal de Panamá OR puerto OR huelga portuaria) sourcelang:spanish"},
    {"label": "Customs, tariffs & sanctions", "language": "en",
     "query": '("export controls" OR "new tariffs" OR "customs delays" OR sanctions) '
              '(shipping OR freight OR port)'},
]

# What each language code is called on screen, and which way its script runs.
# Arabic has to render right-to-left or the original headline is mangled.
LANGUAGES = {
    "de": {"name": "German",  "dir": "ltr"},
    "ar": {"name": "Arabic",  "dir": "rtl"},
    "fr": {"name": "French",  "dir": "ltr"},
    "nl": {"name": "Dutch",   "dir": "ltr"},
    "es": {"name": "Spanish", "dir": "ltr"},
    "it": {"name": "Italian", "dir": "ltr"},
    "tr": {"name": "Turkish", "dir": "ltr"},
    "zh": {"name": "Chinese", "dir": "ltr"},
    "ja": {"name": "Japanese", "dir": "ltr"},
    "pt": {"name": "Portuguese", "dir": "ltr"},
    "en": {"name": "English", "dir": "ltr"},
}

# --- 2. RSS - where the multilingual earliness edge actually lives ----------
# At least one German feed is required: the demo's whole differentiation is
# catching "Warnstreik Hamburger Hafen" before the English wires carry it.
#
# Note: Reuters is named in DATA-SOURCES.md but retired its public RSS feeds,
# so it is deliberately not wired here - a dead feed is a live failure.

RSS_FEEDS = [
    # German - the North Range ports and the Rhine are German-language stories
    # first. This is where the earliness edge is most often real.
    {"name": "NDR Hamburg", "language": "de", "url": "https://www.ndr.de/nachrichten/hamburg/index-rss.xml"},
    {"name": "tagesschau", "language": "de", "url": "https://www.tagesschau.de/index~rss2.xml"},
    {"name": "DW (Deutsch)", "language": "de", "url": "https://rss.dw.com/rdf/rss-de-all"},
    # Hamburg's own paper - a walkout in the port is its local story before it
    # is anyone's shipping story.
    {"name": "Hamburger Abendblatt", "language": "de", "url": "https://www.abendblatt.de/rss"},
    # Austria - the Alpine hinterland the rail legs out of the North Range serve.
    {"name": "ORF", "language": "de", "url": "https://rss.orf.at/news.xml"},
    # Arabic - Red Sea, Suez and Gulf incidents surface here before the wires.
    {"name": "Al Jazeera Arabic", "language": "ar", "url": "https://www.aljazeera.net/xml/rss/all.xml"},
    # French - Fos-sur-Mer, Le Havre, and the Rhone corridor.
    {"name": "France Info", "language": "fr", "url": "https://www.francetvinfo.fr/titres.rss"},
    {"name": "Le Monde", "language": "fr", "url": "https://www.lemonde.fr/rss/une.xml"},
    # Dutch - Rotterdam and Antwerp are Dutch-language ports.
    {"name": "NOS Nieuws", "language": "nl", "url": "https://feeds.nos.nl/nosnieuwsalgemeen"},
    # Rotterdam's own regional broadcaster, on the port's doorstep - the same
    # role NDR Hamburg plays for the other end of the North Range.
    {"name": "Rijnmond", "language": "nl", "url": "https://www.rijnmond.nl/rss/index.xml"},
    # Spanish - Algeciras, Valencia and the western Mediterranean.
    {"name": "RTVE", "language": "es", "url": "https://api2.rtve.es/rss/temas_noticias.xml"},
    # Flemish - Antwerp's own regional broadcaster, on the port's doorstep.
    {"name": "VRT NWS", "language": "nl", "url": "https://www.vrt.be/vrtnws/nl.rss.articles.xml"},
    # Arabic - more than one reader on the Red Sea and Gulf, because a single
    # feed having a bad day should not silence a whole corridor.
    {"name": "DW (العربية)", "language": "ar", "url": "https://rss.dw.com/rdf/rss-ar-all"},
    {"name": "France 24 (العربية)", "language": "ar", "url": "https://www.france24.com/ar/rss"},
    # The Suez corridor's doorstep, in English - close to the canal rather than
    # to a newsroom half the world away from it.
    {"name": "Egypt Independent", "language": "en", "url": "https://www.egyptindependent.com/feed/"},
    # The Cape of Good Hope corridor - the leg every Red Sea reroute on this
    # board actually sails. Two readers, for the same reason there are two
    # Arabic feeds: one source having a bad day must not silence a corridor.
    {"name": "News24", "language": "en",
     "url": "https://feeds.capi24.com/v1/Search/articles/news24/TopStories/rss"},
    {"name": "Daily Maverick", "language": "en", "url": "https://www.dailymaverick.co.za/dmrss/"},
    # Italian - Genoa, Trieste and the Adriatic feeder network.
    {"name": "ANSA", "language": "it", "url": "https://www.ansa.it/sito/ansait_rss.xml"},
    # Spanish - Algeciras and Valencia already have GDELT; this is the paper.
    {"name": "El País", "language": "es",
     "url": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada"},
    # Japanese - Tokyo, Yokohama and Kobe, and the typhoon season that closes them.
    {"name": "NHK", "language": "ja", "url": "https://www3.nhk.or.jp/rss/news/cat0.xml"},
    # English, but close to the lane rather than to the newsroom: the load ports
    # and the transshipment hub our boxes actually pass through.
    {"name": "The Straits Times", "language": "en",
     "url": "https://www.straitstimes.com/news/singapore/rss.xml"},
    {"name": "Times of India", "language": "en",
     "url": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms"},
    # English trade press - narrow, and almost every item is on topic.
    {"name": "Splash 247 (maritime)", "language": "en", "url": "https://splash247.com/feed/"},
    {"name": "The Maritime Executive", "language": "en",
     "url": "https://www.maritime-executive.com/articles.rss"},
    # More of the same trade press: The Loadstar is the forwarders' own paper,
    # Hellenic Shipping News and Container News cover the carriers and the box
    # trades, and SAFETY4SEA carries the casualty and port-state stories that
    # close a berth before anyone calls it a disruption.
    {"name": "The Loadstar", "language": "en", "url": "https://theloadstar.com/feed/"},
    {"name": "Hellenic Shipping News", "language": "en",
     "url": "https://www.hellenicshippingnews.com/feed/"},
    {"name": "Container News", "language": "en", "url": "https://container-news.com/feed/"},
    {"name": "SAFETY4SEA", "language": "en", "url": "https://safety4sea.com/feed/"},
    # English - the wires, kept so the lag against them is measurable.
    {"name": "gCaptain (maritime)", "language": "en", "url": "https://gcaptain.com/feed/"},
    {"name": "Al Jazeera English", "language": "en", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
]

RSS_MAX_ITEMS_PER_FEED = 25

# A hard ceiling on any single source's response body. A feed that answers but
# never stops sending would otherwise be read forever - see _get_capped.
HTTP_MAX_BYTES = _env_int("HTTP_MAX_BYTES", 4_000_000)

# Feeds are independent requests, so they are read at once rather than in turn.
# Sequentially, thirty feeds at the per-source timeout cannot fit in a
# serverless budget and all but the first would be skipped - taking the language
# spread, and most of the point, with them.
RSS_CONCURRENCY = _env_int("RSS_CONCURRENCY", 30)

# --- 3. PEGELONLINE - Rhine water levels, the DACH domain-depth signal ------
# Gauge readings are numbers, not prose, so they are classified by threshold
# rather than by the LLM. Kaub is the reference gauge the barge market watches.
# Thresholds are approximate and tuned for the demo, not for operations.

PEGELONLINE_ENDPOINT = "https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations"

# Everything the risk monitor reads. The first three are the reference gauges
# the barge market quotes; the next three widen the read along the river - Köln
# and Maxau bracket Kaub upstream and down, Mainz sits at the Main confluence -
# so a level falling in one reach shows up before it reaches the reference
# gauge. Bands for the newer three are demo-tuned like the rest.
RHINE_GAUGES = [
    {"station": "KAUB", "name": "Kaub", "warn_cm": 100, "high_cm": 78, "critical_cm": 40},
    {"station": "DUISBURG-RUHRORT", "name": "Duisburg-Ruhrort", "warn_cm": 250, "high_cm": 200, "critical_cm": 150},
    {"station": "EMMERICH", "name": "Emmerich", "warn_cm": 100, "high_cm": 70, "critical_cm": 30},
    {"station": "KÖLN", "name": "Köln", "warn_cm": 180, "high_cm": 140, "critical_cm": 90},
    {"station": "MAINZ", "name": "Mainz", "warn_cm": 160, "high_cm": 120, "critical_cm": 80},
    {"station": "MAXAU", "name": "Maxau", "warn_cm": 380, "high_cm": 320, "critical_cm": 250},
]

# The landing page's gauge panel was designed around three readings, and the
# three it shows are the reference gauges - so the panel keeps its shape while
# the monitor reads the wider set above. Station ids, resolved against
# RHINE_GAUGES, so the two lists cannot carry different thresholds for the
# same station.
LANDING_GAUGES = ["KAUB", "DUISBURG-RUHRORT", "EMMERICH"]

# The landing page reads these gauges live, so they get their own allowance -
# tighter than the button's live pull, because a visitor will not wait 25
# seconds to see a water level, and longer-lived, because PEGELONLINE only
# refreshes about every fifteen minutes and the page is public.
GAUGE_TIMEOUT_SECONDS = _env_int("GAUGE_TIMEOUT_SECONDS", 5 if SERVERLESS else 6)
GAUGE_BUDGET_SECONDS = _env_int("GAUGE_BUDGET_SECONDS", 8 if SERVERLESS else 10)
GAUGE_CACHE_SECONDS = _env_int("GAUGE_CACHE_SECONDS", 300)

# ===========================================================================
# Sources 4-16 - the structured public APIs (read by src/signals.py)
#
# Everything above this line is prose: a headline that a model has to read and
# judge. Everything below it arrives as a NUMBER or a government notice, which
# is a different kind of signal and a cheaper one - a wave height or a warning
# code is classified by threshold, so it costs nothing and cannot hallucinate.
#
# All keyless, all HTTPS, most of them listed in the public-apis catalogue
# (github.com/public-apis/public-apis); the rest are institutions publishing
# their own open feeds. DATA-SOURCES.md says which catalogue entry each one is
# where there is one, and why it earns its place on a freight desk.
#
# None of these are load-bearing for the demo. Each is read in its own small
# function, and a source that is down, slow or reshaped is reported as failed
# and skipped - never allowed to take the run with it.
# ===========================================================================

# Where each source looks is NOT repeated here: data/geo.json already carries a
# real lat/lon for every chokepoint on the board, so the watch lists below are
# chokepoint ids and the coordinates are read from there. One source of truth.

# --- 4. Open-Meteo - weather over the ports a route discharges through ------
# public-apis: Weather > Open-Meteo (Auth: No, HTTPS: Yes, CORS: Yes).
# One request covers every port: the API takes comma-separated coordinates and
# answers with one block per location.

OPEN_METEO_ENDPOINT = "https://api.open-meteo.com/v1/forecast"
WEATHER_PORTS = ["HAM", "RTM", "ANR", "FOS"]

# Gusts in knots. A container terminal starts losing crane hours around gale
# force 8 and stops near force 10. The first band a reading clears is the one
# it gets - same shape as GAUGE_BANDS, and approximate for the same reason:
# this positions a demo, it does not run a terminal.
WIND_BANDS = [
    # gusts kn  severity  state          delay days  what it means
    (47, "high",   "storm force",  [2, 4], "cranes down, berths likely closed"),
    (39, "medium", "strong gale",  [1, 3], "crane hours lost and vessels bunching"),
    (34, "low",    "gale force",   [1, 2], "handling slows, some moves suspended"),
]

# --- 5. Open-Meteo Marine - sea state on the open legs ----------------------
# public-apis: Weather > Open-Meteo (the same provider's marine endpoint).
# The three points a box on this board actually rounds.

OPEN_METEO_MARINE_ENDPOINT = "https://marine-api.open-meteo.com/v1/marine"
MARINE_WAYPOINTS = ["SUEZ", "REDSEA", "COGH"]

# Significant wave height in metres.
WAVE_BANDS = [
    (6.0, "high",   "very rough", [2, 4], "routing and speed both constrained"),
    (4.0, "medium", "rough",      [1, 3], "speed reduced over the leg"),
    (3.0, "low",    "moderate",   [1, 2], "minor speed loss over the leg"),
]

# --- 6. USGS Earthquake Hazards Program - real-time seismic -----------------
# public-apis: Science & Math > USGS Earthquake Hazards Program (Auth: No).
# A quake matters to this board only if it is near something on it, so a
# reading is mapped to the nearest watched chokepoint and dropped if there
# isn't one within reach.

USGS_QUAKE_ENDPOINT = "https://earthquake.usgs.gov/fdsnws/event/1/query"
QUAKE_MIN_MAGNITUDE = 5.5
QUAKE_RADIUS_KM = 300
QUAKE_LOOKBACK_DAYS = 3
QUAKE_BANDS = [
    (7.0, "high",   [3, 7], "port infrastructure and inland links likely damaged"),
    (6.3, "medium", [2, 4], "terminal inspections and handling suspensions likely"),
    (5.5, "low",    [1, 2], "precautionary checks at nearby terminals"),
]

# --- 7. NASA EONET - open natural events, worldwide -------------------------
# public-apis: Science & Math > NASA (Auth: No). EONET is NASA's natural-event
# tracker: wildfires, severe storms, floods and volcanoes, each with a
# coordinate, which is what lets it be mapped onto a corridor the same way a
# quake is. The `france` scenario is a wildfire on a land leg, so this is the
# live source that scenario is a rehearsal of.

EONET_ENDPOINT = "https://eonet.gsfc.nasa.gov/api/v3/events"
EONET_CATEGORIES = "wildfires,severeStorms,floods,volcanoes"
EONET_RADIUS_KM = 250
EONET_MAX_EVENTS = 40
EONET_SEVERITY = {"volcanoes": "high", "severeStorms": "medium",
                  "floods": "medium", "wildfires": "medium"}

# --- 8. Federal Register - the rule before it is the news -------------------
# public-apis: Government > Federal Register (Auth: No).
# A tariff, an export control or a port-security rule lands here as a filing
# days before a trade paper writes it up. It is prose, so unlike the rest of
# this section it goes to the classifier rather than to a threshold.
#
# It is a US journal and this is a European board, which is the point: what
# Washington publishes moves an Asia-Europe lane whether or not the box ever
# touches a US port.

FEDERAL_REGISTER_ENDPOINT = "https://www.federalregister.gov/api/v1/documents.json"
FEDERAL_REGISTER_TERMS = "tariff OR sanctions OR customs OR \"port security\""
FEDERAL_REGISTER_LOOKBACK_DAYS = 7
FEDERAL_REGISTER_MAX = 20

# --- 9. Frankfurter - the ECB's own reference rates -------------------------
# public-apis: Currency Exchange > Frankfurter (Auth: No, CORS: Yes).
# Board context, not a risk event. A reroute is priced as a cost index; the
# rate is what turns that index into what the customer is actually billed.

FX_ENDPOINT = "https://api.frankfurter.app/latest"
FX_BASE = "EUR"
FX_SYMBOLS = ["USD", "CNY", "GBP"]

# --- 10. US National Weather Service - active government alerts -------------
# public-apis: Weather > US Weather (Auth: No, CORS: Yes).
# Board context: these are the US port states, and no booking on this synthetic
# board discharges there. It is wired anyway because it is the same read as
# every other source, and the day a transatlantic lane is on the board it is
# already connected. api.weather.gov asks for a contact in the User-Agent.

NWS_ENDPOINT = "https://api.weather.gov/alerts/active"
NWS_AREAS = ["NY", "NJ", "GA", "SC", "VA", "TX", "LA", "CA", "WA", "FL"]
NWS_MAX_ALERTS = 12

# --- 11. Hong Kong Observatory - the warnings in force ----------------------
# public-apis: Weather > Hong Kong Obervatory (Auth: No).
# Board context, for the same reason: two of the five bookings load in the
# Pearl River Delta, and a T8 signal shuts Yantian and Hong Kong for a day.
# The load ports are not modelled as chokepoints, so this informs the desk
# without moving a booking - which is exactly what it should do.

HKO_ENDPOINT = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php"

# --- 12. Open-Meteo Flood - GloFAS river discharge on the Rhine -------------
# public-apis: Weather > Open-Meteo (the same provider's flood endpoint).
# Complements the PEGELONLINE gauges rather than repeating them: a gauge is a
# measured LEVEL at a point, GloFAS is modelled FLOW for the reach - two
# independent reads on the same river, so one being down or wrong does not
# blind the board to the Rhine.

OPEN_METEO_FLOOD_ENDPOINT = "https://flood-api.open-meteo.com/v1/flood"
DISCHARGE_RIVER = "RHINE"     # the chokepoint whose coordinate is asked about

# Discharge in m3/s, and LOW is the risk - the inverse of every other band
# table here, so it is walked with value <= threshold rather than >=. The
# figures are demo-tuned like the gauge thresholds: they position a demo, they
# do not run a barge operator.
DISCHARGE_BANDS = [
    # m3/s      severity  state             delay days  what it means
    (500,  "high",   "critically low", [3, 6], "barge loading largely uneconomic"),
    (800,  "medium", "low",            [2, 4], "barges loading well below capacity"),
    (1100, "low",    "falling",        [1, 2], "loading restrictions beginning to bite"),
]

# --- 13. Deutscher Wetterdienst - the official German warnings --------------
# Not in the public-apis catalogue: this is the German weather service's own
# open warnings feed, the one its warnapp reads. The body is JSONP rather than
# JSON, so signals.py unwraps it before parsing.

DWD_WARNINGS_ENDPOINT = "https://www.dwd.de/DWD/warnungen/warnapp/json/warnings.json"

# Which warning regions map onto a chokepoint on this board. DWD warns by
# administrative region, so the match is on the region NAME; only Hamburg is a
# chokepoint here today, and the day Bremerhaven is on the board it is one more
# row in this table.
DWD_REGION_WATCH = [
    {"match": "Hamburg", "chokepoint": "HAM"},
]

# DWD Warnstufen: 1 is weather, 5 is extreme weather. Below 4, a warning is
# real and moves nothing - it stays context, like most of what this file reads.
DWD_LEVEL_BANDS = {
    5: ("high",   [2, 4], "extreme weather warning - handling likely suspended"),
    4: ("medium", [1, 2], "severe weather warning - crane hours likely lost"),
}
DWD_CONTEXT_SAMPLE = 5        # how many of the other regions' warnings to show

# --- 14. EMSC - the European seismic reader ---------------------------------
# A standard FDSN event service, the same query shape as USGS. A second seismic
# reader for the same reason there are two Arabic feeds: one source having a
# bad day must not silence the signal. It reuses the USGS thresholds and
# proximity rule wholesale, so the two can never band the same quake apart.

EMSC_ENDPOINT = "https://www.seismicportal.eu/fdsnws/event/1/query"

# --- 15. GDACS - the UN/EC disaster alert system ----------------------------
# Public JSON from the Global Disaster Alert and Coordination System, run by
# the UN and the European Commission. It has already judged severity - Green /
# Orange / Red - so the banding here is a translation, not a threshold.

GDACS_ENDPOINT = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/MAP"
GDACS_RADIUS_KM = 300
GDACS_ALERT_BANDS = {
    "red":    ("high",   [2, 5]),
    "orange": ("medium", [1, 3]),
    # Green is deliberately absent: a Green alert is context, never an event.
}
# GDACS event types that are weather-shaped (tropical cyclone, flood, wildfire,
# drought); earthquakes and volcanoes are classified "other" like USGS quakes.
GDACS_WEATHER_TYPES = ("TC", "FL", "WF", "DR")
GDACS_CONTEXT_SAMPLE = 5

# --- 16. NOAA National Hurricane Center - active storms ---------------------
# Public JSON. Board context, same honesty as the US NWS source: these are
# Atlantic and East-Pacific storms and no booking on this board routes there,
# so it informs the desk and may never move a booking.

NHC_ENDPOINT = "https://www.nhc.noaa.gov/CurrentStorms.json"

# How many of the structured sources are read at once. They are independent
# requests to different hosts, so reading them in turn would spend the whole
# budget on the slowest one - and with thirteen of them, anything less than
# all-at-once queues the stragglers behind the slowest of the first wave.
SIGNAL_CONCURRENCY = _env_int("SIGNAL_CONCURRENCY", 13)

# --- Classification tuning -------------------------------------------------

# The prefilter only REDUCES COST - it decides what is worth spending an LLM
# call on. The LLM still makes the actual relevance / severity call.
DISRUPTION_KEYWORDS = [
    # English
    "strike", "walkout", "closure", "closed", "shut", "congestion", "backlog",
    "delay", "disruption", "blockade", "blocked", "suspended", "attack", "storm",
    "customs", "tariff", "embargo", "sanction", "queue", "diverted",
    # German
    "streik", "warnstreik", "ausstand", "sperrung", "gesperrt", "stau",
    "verspätung", "störung", "blockade", "niedrigwasser", "hochwasser", "zoll",
    # Arabic
    "إضراب", "إغلاق", "تعطل", "هجوم",
    # Dutch / French
    "staking", "grève", "blocage",
]

EVENT_TYPES = ["strike", "weather", "congestion", "geopolitical", "customs", "other"]
SEVERITIES = ["low", "medium", "high"]

# Reasoning models (gpt-oss, the r1 family) emit analysis tokens before the
# answer, and those count against the completion budget. The customer email is
# the longest single output this project asks for, so a tight cap truncates it
# mid-JSON and the draft silently falls back to a template.
DRAFT_MAX_TOKENS = _env_int("DRAFT_MAX_TOKENS", 1400)
DECISION_MAX_TOKENS = _env_int("DECISION_MAX_TOKENS", 1400)

CLASSIFY_BATCH_SIZE = 8      # items per LLM call - keeps free-tier usage sane
MAX_ITEMS_TO_CLASSIFY = _env_int("MAX_ITEMS_TO_CLASSIFY", 16 if SERVERLESS else 40)


# ===========================================================================
# Who the emails come FROM (Comms Agent, Phase 3)
#
# Not in DATASET.md - authored so drafts are signed by a consistent person
# instead of the model inventing one on every run. The modelled end user is a
# mid-size DACH/Benelux forwarder's Head of Operations.
#
# The domain uses .example, a TLD reserved by RFC 2606 so it can never belong
# to anyone. Nothing here is a real company, person or address.
# ===========================================================================

FORWARDER = {
    "company": "Hanseatic Freight Partners GmbH",
    "ops_contact": "Lena Brandt",
    "ops_title": "Head of Operations",
    "ops_email": "operations@hanseatic-freight.example",
    "ops_phone": "+49 40 5550 118",
}
