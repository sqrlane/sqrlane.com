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
# been read is marked skipped and the cycle moves on. Thirteen sources at eight
# seconds each would otherwise be nearly two minutes on its own - the whole
# demo's budget - so this is what actually keeps the run on time.
#
# Deployed, the ceiling is the function's own timeout, and the LLM calls that
# follow the pull need most of it. Both are tunable by environment variable so
# a slow deploy can be trimmed without a code change.
LIVE_PULL_BUDGET_SECONDS = _env_int("LIVE_PULL_BUDGET_SECONDS", 10 if SERVERLESS else 25)

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
# Be polite - GDELT throttles rapid calls. But four queries at 1.5s is six
# seconds of pure waiting, which is most of a serverless budget, so it is
# shorter there.
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
]

# What each language code is called on screen, and which way its script runs.
# Arabic has to render right-to-left or the original headline is mangled.
LANGUAGES = {
    "de": {"name": "German",  "dir": "ltr"},
    "ar": {"name": "Arabic",  "dir": "rtl"},
    "fr": {"name": "French",  "dir": "ltr"},
    "nl": {"name": "Dutch",   "dir": "ltr"},
    "es": {"name": "Spanish", "dir": "ltr"},
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
    # Arabic - Red Sea, Suez and Gulf incidents surface here before the wires.
    {"name": "Al Jazeera Arabic", "language": "ar", "url": "https://www.aljazeera.net/xml/rss/all.xml"},
    # French - Fos-sur-Mer, Le Havre, and the Rhone corridor.
    {"name": "France Info", "language": "fr", "url": "https://www.francetvinfo.fr/titres.rss"},
    {"name": "Le Monde", "language": "fr", "url": "https://www.lemonde.fr/rss/une.xml"},
    # Dutch - Rotterdam and Antwerp are Dutch-language ports.
    {"name": "NOS Nieuws", "language": "nl", "url": "https://feeds.nos.nl/nosnieuwsalgemeen"},
    # Spanish - Algeciras, Valencia and the western Mediterranean.
    {"name": "RTVE", "language": "es", "url": "https://api2.rtve.es/rss/temas_noticias.xml"},
    # English - the wires, kept so the lag against them is measurable.
    {"name": "gCaptain (maritime)", "language": "en", "url": "https://gcaptain.com/feed/"},
    {"name": "Al Jazeera English", "language": "en", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
]

RSS_MAX_ITEMS_PER_FEED = 25

# A hard ceiling on any single source's response body. A feed that answers but
# never stops sending would otherwise be read forever - see _get_capped.
HTTP_MAX_BYTES = _env_int("HTTP_MAX_BYTES", 4_000_000)

# Feeds are independent requests, so they are read at once rather than in turn.
# Sequentially, ten feeds at the per-source timeout cannot fit in a serverless
# budget and all but the first would be skipped.
RSS_CONCURRENCY = _env_int("RSS_CONCURRENCY", 10)

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

# The landing page reads these gauges live, so they get their own allowance -
# tighter than the button's live pull, because a visitor will not wait 25
# seconds to see a water level, and longer-lived, because PEGELONLINE only
# refreshes about every fifteen minutes and the page is public.
GAUGE_TIMEOUT_SECONDS = _env_int("GAUGE_TIMEOUT_SECONDS", 5 if SERVERLESS else 6)
GAUGE_BUDGET_SECONDS = _env_int("GAUGE_BUDGET_SECONDS", 8 if SERVERLESS else 10)
GAUGE_CACHE_SECONDS = _env_int("GAUGE_CACHE_SECONDS", 300)

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
