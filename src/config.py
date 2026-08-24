"""config.py - every knob in one place: paths, provider settings, source lists.

Nothing here does any work. If you want to add or remove a news source, change a
model, or retune a threshold, this is the only file you touch.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# --- Paths -----------------------------------------------------------------

DATA_DIR = ROOT / "data"
CHOKEPOINTS_FILE = DATA_DIR / "chokepoints.json"
ROUTES_FILE = DATA_DIR / "routes.json"
SHIPMENTS_FILE = DATA_DIR / "shipments.json"
INJECTED_EVENTS_FILE = DATA_DIR / "injected_events.json"
RISK_STATE_FILE = ROOT / "risk_state.json"

# --- AI provider -----------------------------------------------------------
# Read by llm.py and nowhere else. Swap providers by editing LLM_PROVIDER in .env.

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").strip().lower()

DEFAULT_MODELS = {
    "groq": "llama-3.3-70b-versatile",
    "gemini": "gemini-2.0-flash",
    "ollama": "llama3.1",
}
# .env can override the model for whichever provider is selected.
LLM_MODEL = os.getenv("LLM_MODEL", "").strip() or DEFAULT_MODELS.get(LLM_PROVIDER, "")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").strip()

LLM_TIMEOUT_SECONDS = 60
LLM_MAX_RETRIES = 3          # free tiers rate-limit; retry 429/5xx with backoff
LLM_TEMPERATURE = 0.0        # classification should be repeatable

# --- HTTP ------------------------------------------------------------------

HTTP_TIMEOUT_SECONDS = 20
USER_AGENT = "trade-risk-agent/0.1 (demo prototype; contact: local)"

# ===========================================================================
# Risk Monitor sources - CORE ONLY (see DATA-SOURCES.md)
#
# The rule: every extra source is one more thing that can break live in front
# of an audience. Three keyless sources carry the whole story.
# ===========================================================================

# --- 1. GDELT DOC 2.0 - global news backbone, no key, refreshes ~15 min -----
# Each query is deliberately narrow. `sourcelang:german` is what makes the
# "we saw it in German first" claim true - keep at least one non-English query.

GDELT_ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_TIMESPAN = "3d"
GDELT_MAX_RECORDS = 20
GDELT_PAUSE_SECONDS = 1.5    # be polite; GDELT throttles rapid calls

GDELT_QUERIES = [
    {
        "label": "port disruption (English)",
        "language": "en",
        "query": '("port strike" OR "port closure" OR "port congestion" OR "terminal closed")',
    },
    {
        "label": "Hafen / Streik (German)",
        "language": "de",
        "query": "(Hafenstreik OR Warnstreik OR Hafenarbeiter) sourcelang:german",
    },
    {
        "label": "Red Sea / Suez routing",
        "language": "en",
        "query": '("Red Sea" OR "Suez Canal") (attack OR closure OR diverted OR delay)',
    },
    {
        "label": "North Range ports",
        "language": "en",
        "query": "(Hamburg OR Rotterdam OR Antwerp) (strike OR congestion OR backlog)",
    },
]

# --- 2. RSS - where the multilingual earliness edge actually lives ----------
# At least one German feed is required: the demo's whole differentiation is
# catching "Warnstreik Hamburger Hafen" before the English wires carry it.
#
# Note: Reuters is named in DATA-SOURCES.md but retired its public RSS feeds,
# so it is deliberately not wired here - a dead feed is a live failure.

RSS_FEEDS = [
    {"name": "NDR Hamburg", "language": "de", "url": "https://www.ndr.de/nachrichten/hamburg/index-rss.xml"},
    {"name": "tagesschau", "language": "de", "url": "https://www.tagesschau.de/index~rss2.xml"},
    {"name": "DW (Deutsch)", "language": "de", "url": "https://rss.dw.com/rdf/rss-de-all"},
    {"name": "gCaptain (maritime)", "language": "en", "url": "https://gcaptain.com/feed/"},
    {"name": "Al Jazeera English", "language": "en", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"name": "Al Jazeera Arabic", "language": "ar", "url": "https://www.aljazeera.net/xml/rss/all.xml"},
]

RSS_MAX_ITEMS_PER_FEED = 25

# --- 3. PEGELONLINE - Rhine water levels, the DACH domain-depth signal ------
# Gauge readings are numbers, not prose, so they are classified by threshold
# rather than by the LLM. Kaub is the reference gauge the barge market watches.
# Thresholds are approximate and tuned for the demo, not for operations.

PEGELONLINE_ENDPOINT = "https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations"

RHINE_GAUGES = [
    {"station": "KAUB", "name": "Kaub", "warn_cm": 100, "high_cm": 78, "critical_cm": 40},
    {"station": "DUISBURG-RUHRORT", "name": "Duisburg-Ruhrort", "warn_cm": 250, "high_cm": 200, "critical_cm": 150},
    {"station": "EMMERICH", "name": "Emmerich", "warn_cm": 100, "high_cm": 70, "critical_cm": 30},
]

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

CLASSIFY_BATCH_SIZE = 8      # items per LLM call - keeps free-tier usage sane
MAX_ITEMS_TO_CLASSIFY = 40   # hard ceiling on a single run


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
