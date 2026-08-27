"""llm.py - the ONLY place this project talks to an AI provider.

Every agent (risk_monitor, route_advisor, comms_agent) calls the functions here.
Nothing else imports a provider SDK or builds an inference request. That is the
whole point: to switch from Groq to Hugging Face to Gemini to a local Ollama
model you change LLM_PROVIDER in .env and touch no other file.

All four providers are spoken to over plain HTTP with `requests`, so there is
no extra SDK to install and no fourth way for things to break.

Groq and Hugging Face are both OpenAI-compatible - same chat body, same /models
listing, same bearer header - so they share one implementation here and differ
only in a base URL, a token and a preference list. Hugging Face is a sibling to
Groq rather than a replacement: its router fronts several upstream backends, so a
rate limit on one becomes a routing choice instead of a wall.

Public API
----------
    is_configured()  -> bool          # can we actually make a call right now?
    describe()       -> str           # human-readable "groq / llama-3.3-70b"
    complete(...)    -> str           # free text back
    complete_json(...) -> dict|list   # parsed JSON back, with one repair retry
"""

import json
import re
import time

import requests

from src import config


class LLMError(RuntimeError):
    """Any failure to get a usable answer out of the provider."""


class LLMNotConfigured(LLMError):
    """No key / no reachable provider. Callers can catch this and degrade."""


class ModelNotAvailable(LLMError):
    """The named model does not exist on this key.

    Distinct from a bad key on purpose: a retired model is recoverable by asking
    the provider what it does offer, whereas a bad key is not.
    """


# --- Is the provider usable? ----------------------------------------------


def is_configured() -> bool:
    """True if the selected provider has what it needs to make a call."""
    provider = config.LLM_PROVIDER
    if provider == "groq":
        return bool(config.GROQ_API_KEY)
    if provider == "hf":
        return bool(config.HF_API_TOKEN)
    if provider == "gemini":
        return bool(config.GEMINI_API_KEY)
    if provider == "ollama":
        return bool(config.OLLAMA_HOST)  # no key; reachability is checked on call
    return False


# The providers that speak the OpenAI chat API. They share everything below.
OPENAI_COMPATIBLE = ("groq", "hf")

PROVIDER_NAMES = {"groq": "Groq", "hf": "Hugging Face",
                  "gemini": "Gemini", "ollama": "Ollama"}

# Where a human goes to check the key, per provider. Used in error messages,
# which is the only moment anyone needs it.
_CONSOLES = {"groq": "https://console.groq.com",
             "hf": "https://huggingface.co/settings/tokens"}

# Resolved once per process, per provider. Serverless gives each cold start its
# own process, so this is at most one extra request per container, not per run.
_resolved: dict[str, str] = {}
_resolution_note: str = ""


def _endpoint(provider: str) -> tuple[str, str]:
    """(base url, bearer token) for an OpenAI-compatible provider."""
    if provider == "groq":
        return "https://api.groq.com/openai/v1", config.GROQ_API_KEY
    if provider == "hf":
        return config.HF_BASE_URL, config.HF_API_TOKEN
    raise LLMNotConfigured(f"{provider!r} does not speak the OpenAI-compatible API")


# Named one by one rather than "groq or else HF", so that adding a fifth
# provider fails here loudly instead of silently inheriting HF's lists.
def _preferences(provider: str) -> list[str]:
    if provider == "groq":
        return config.GROQ_MODEL_PREFERENCES
    if provider == "hf":
        return config.HF_MODEL_PREFERENCES
    raise LLMNotConfigured(f"{provider!r} has no model preference list")


def _exclusions(provider: str) -> tuple:
    if provider == "groq":
        return config.GROQ_MODEL_EXCLUDE
    if provider == "hf":
        return config.HF_MODEL_EXCLUDE
    raise LLMNotConfigured(f"{provider!r} has no model exclusion list")


# Task names that mean "this model answers with text". The Hugging Face router
# lists image, video and audio models in the same call as chat ones, and a name
# check alone does not catch them all.
_TEXT_TASKS = {"conversational", "text-generation", "text2text-generation", "chat"}


def _serves_text(entry: dict) -> bool:
    """True unless the listing positively says this model does something else.

    A STATED task that is not a text task is dropped. An ABSENT one is kept, so a
    provider that does not report tasks at all - Groq does not - loses nothing.
    """
    for key in ("task", "pipeline_tag"):
        stated = entry.get(key)
        if isinstance(stated, str) and stated.strip():
            return stated.strip().lower() in _TEXT_TASKS
    return True


def _list_model_entries(provider: str) -> list[dict]:
    """Ask the provider what this key can actually run. Read-only."""
    base, token = _endpoint(provider)
    response = requests.get(
        f"{base}/models",
        headers={"Authorization": f"Bearer {token}"},
        timeout=config.LLM_TIMEOUT_SECONDS,
    )
    if response.status_code != 200:
        raise LLMError(f"could not list models: HTTP {response.status_code} "
                       f"{response.text[:200]}")
    return [m for m in response.json().get("data", [])
            if isinstance(m, dict) and m.get("id")]


def list_models(provider: str | None = None) -> list[str]:
    """Every model id this key is offered, unfiltered."""
    return [m["id"] for m in _list_model_entries(provider or config.LLM_PROVIDER)]


def list_groq_models() -> list[str]:
    """Kept under its own name because the README and .env.example use it."""
    return list_models("groq")


def _usable(model_id: str, provider: str | None = None) -> bool:
    """Chat models only - not audio, safety classifiers, embeddings or images."""
    lowered = model_id.lower()
    return not any(bad in lowered
                   for bad in _exclusions(provider or config.LLM_PROVIDER))


def _rank(model_id: str, preferences: list[str] | None = None) -> tuple:
    """Sort key: preferred models first, then bigger/instruct-looking ones.

    The fallback half matters - it is what picks a sensible model from a lineup
    this code has never heard of.
    """
    lowered = model_id.lower()
    if preferences is None:
        preferences = _preferences(config.LLM_PROVIDER)
    for position, preferred in enumerate(preferences):
        if lowered == preferred.lower():
            return (0, position, 0)
    # Unknown model: prefer something that looks like a general instruct model,
    # and prefer larger parameter counts where the name states one.
    size = 0
    for token in re.findall(r"(\d+)\s*b\b", lowered):
        size = max(size, int(token))
    looks_general = any(word in lowered for word in
                        ("instruct", "versatile", "chat", "-it", "instant"))
    return (1, -size, 0 if looks_general else 1)


def resolve_model(provider: str | None = None, *, force: bool = False,
                  exclude: frozenset = frozenset()) -> str:
    """Decide which model to call, asking the provider if we do not already know.

    An explicit LLM_MODEL in .env wins, but is not a hard pin: if it turns out
    to be retired, discovery still rescues the run rather than failing it.

    On Hugging Face the id may carry an upstream backend - "...-Instruct:groq" -
    which is passed through untouched, because pinning the backend is the whole
    reason someone would set it.
    """
    global _resolution_note
    provider = provider or config.LLM_PROVIDER
    preferences = _preferences(provider)

    already = _resolved.get(provider)
    if not force and already and already not in exclude:
        return already

    if config.LLM_MODEL and config.LLM_MODEL not in exclude:
        _resolved[provider] = config.LLM_MODEL
        _resolution_note = "pinned by LLM_MODEL in .env"
        return config.LLM_MODEL

    try:
        entries = _list_model_entries(provider)
    except (LLMError, requests.RequestException) as exc:
        # Could not ask. Fall back to the first preference and let the call fail
        # loudly if that is wrong, rather than guessing silently.
        chosen = next((m for m in preferences if m not in exclude), preferences[0])
        _resolved[provider] = chosen
        _resolution_note = f"could not reach the model list ({exc}); using a default"
        return chosen

    available = [m["id"] for m in entries
                 if _serves_text(m) and _usable(m["id"], provider)
                 and m["id"] not in exclude]

    if not available:
        raise ModelNotAvailable(
            f"This {PROVIDER_NAMES.get(provider, provider)} key exposes no usable "
            f"chat model. Check the key at {_CONSOLES.get(provider, 'the provider')}, "
            f"or pin one with LLM_MODEL in .env.")

    available.sort(key=lambda model_id: _rank(model_id, preferences))
    chosen = available[0]
    _resolved[provider] = chosen
    known = chosen.lower() in {p.lower() for p in preferences}
    _resolution_note = ("chosen from the models this key offers" if known else
                        f"chosen from the models this key offers "
                        f"(not in the preference list; {len(available)} available)")
    return chosen


def resolve_groq_model(*, force: bool = False, exclude: frozenset = frozenset()) -> str:
    """Kept under its own name because the README and .env.example use it."""
    return resolve_model("groq", force=force, exclude=exclude)


def active_model() -> str:
    """The model that will be used, without forcing a lookup."""
    if config.LLM_PROVIDER in OPENAI_COMPATIBLE:
        return (_resolved.get(config.LLM_PROVIDER) or config.LLM_MODEL
                or "(resolved on first call)")
    return config.LLM_MODEL or config.DEFAULT_MODELS.get(config.LLM_PROVIDER, "")


def resolution_note() -> str:
    return _resolution_note


def describe() -> str:
    return f"{config.LLM_PROVIDER} / {active_model()}"


def configuration_hint() -> str:
    """The message to show a human when is_configured() is False."""
    return (
        f"No usable AI provider. LLM_PROVIDER={config.LLM_PROVIDER!r}.\n"
        "  - Copy .env.example to .env and paste a key in.\n"
        "  - Groq (free):   https://console.groq.com     -> GROQ_API_KEY\n"
        "  - Hugging Face:  https://huggingface.co/settings/tokens -> HF_TOKEN\n"
        "                   (one token, several upstream backends; LLM_PROVIDER=hf)\n"
        "  - Gemini (free): https://aistudio.google.com/apikey -> GEMINI_API_KEY\n"
        "  - Ollama (local, no key): run `ollama serve` and set LLM_PROVIDER=ollama"
    )


# --- The one public text call ----------------------------------------------


def complete(prompt: str, *, system: str | None = None,
             temperature: float | None = None, max_tokens: int = 1200) -> str:
    """Send a prompt, get text back. Raises LLMError if it cannot."""
    if not is_configured():
        raise LLMNotConfigured(configuration_hint())

    temperature = config.LLM_TEMPERATURE if temperature is None else temperature
    provider = config.LLM_PROVIDER

    if provider in OPENAI_COMPATIBLE:
        return _call_openai_compatible(provider, prompt, system, temperature, max_tokens)
    if provider == "gemini":
        return _call_gemini(prompt, system, temperature, max_tokens)
    if provider == "ollama":
        return _call_ollama(prompt, system, temperature, max_tokens)
    raise LLMNotConfigured(f"Unknown LLM_PROVIDER {provider!r}. "
                           f"Use groq, hf, gemini or ollama.")


def complete_json(prompt: str, *, system: str | None = None,
                  temperature: float | None = None, max_tokens: int = 1200):
    """Same as complete(), but insists on JSON and parses it.

    Models sometimes wrap JSON in prose or ```json fences, so we strip those.
    If it still will not parse we ask once more, showing the model its own bad
    output - that repair round fixes almost every case in practice.
    """
    json_system = (system or "") + (
        "\n\nReply with valid JSON only. No prose, no markdown fences, no explanation "
        "outside the JSON."
    )
    raw = complete(prompt, system=json_system.strip(), temperature=temperature,
                   max_tokens=max_tokens)
    try:
        return _parse_json(raw)
    except ValueError:
        repair = (
            "Your previous reply was not valid JSON. Return the SAME content as "
            "valid JSON only - no fences, no commentary.\n\n"
            f"Your previous reply:\n{raw[:3000]}"
        )
        retry = complete(repair, system=json_system.strip(), temperature=0.0,
                         max_tokens=max_tokens)
        try:
            return _parse_json(retry)
        except ValueError as exc:
            raise LLMError(f"Provider did not return usable JSON: {exc}") from exc


def _parse_json(text: str):
    """Parse JSON that may be wrapped in fences or padded with prose."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1] if "```" in cleaned[3:] else cleaned[3:]
        if cleaned.lstrip().lower().startswith("json"):
            cleaned = cleaned.lstrip()[4:]
        cleaned = cleaned.strip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Models that "think out loud" - gpt-oss and the reasoning families - put
    # prose before the answer, and that prose often contains braces. Taking the
    # outermost span therefore swallows the preamble and fails to parse. Collect
    # every balanced span instead and try them last-first, because the answer is
    # what comes last.
    for span in reversed(_balanced_spans(cleaned)):
        try:
            return json.loads(span)
        except json.JSONDecodeError:
            continue
    raise ValueError(f"no JSON found in reply: {text[:200]!r}")


def _balanced_spans(text: str) -> list[str]:
    """Every complete {...} or [...] in the text, in the order they close.

    Quotes and escapes are tracked so a brace inside a string does not throw the
    depth count off.
    """
    spans, stack = [], []
    in_string = escaped = False
    quote = ""
    for index, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                in_string = False
            continue
        if char in "\"'":
            in_string, quote = True, char
        elif char in "{[":
            stack.append(index)
        elif char in "}]" and stack:
            start = stack.pop()
            if not stack:
                spans.append(text[start:index + 1])
    return spans


# --- Provider implementations (private) ------------------------------------


def _looks_like_missing_model(body: str) -> bool:
    lowered = (body or "").lower()
    # The second half deliberately requires the word "model" as well, so a
    # generic "not supported" from somewhere else cannot be mistaken for a
    # retired model and send us round the re-resolve loop for nothing.
    return ("model_not_found" in lowered
            or ("model" in lowered and ("does not exist" in lowered
                                        or "not found" in lowered
                                        or "decommission" in lowered
                                        or "no longer supported" in lowered
                                        or "not supported" in lowered
                                        or "no inference provider" in lowered)))


def _post_with_retries(url: str, *, headers=None, json_body=None, params=None) -> dict:
    """POST with backoff on rate limits and transient server errors.

    Free tiers rate-limit aggressively, and a demo that dies on one 429 is
    not a demo.
    """
    last_error = None
    waited = 0.0                       # total seconds slept across this call
    for attempt in range(config.LLM_MAX_RETRIES):
        retry_after = None
        try:
            response = requests.post(url, headers=headers, json=json_body,
                                     params=params, timeout=config.LLM_TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            last_error = f"network error: {exc}"
        else:
            retry_after = _retry_after_seconds(response)
            if response.status_code == 200:
                return response.json()
            if response.status_code in (408, 409, 429, 500, 502, 503, 504):
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
            else:
                body = response.text[:300]
                # A retired or unavailable model IS recoverable - we can ask the
                # provider what it does offer. A bad key is not. Tell them apart.
                if response.status_code in (400, 404) and _looks_like_missing_model(body):
                    raise ModelNotAvailable(f"HTTP {response.status_code}: {body}")
                raise LLMError(f"HTTP {response.status_code}: {body}")
        if attempt < config.LLM_MAX_RETRIES - 1:
            # Prefer what the provider asked for over a guess, but never spend
            # more than the budget - a stalled retry loop would take the whole
            # cycle past the function timeout.
            wait = retry_after if retry_after is not None else float(2 ** attempt)
            wait = min(wait, config.RETRY_WAIT_BUDGET_SECONDS - waited)
            if wait <= 0:
                last_error = (f"{last_error} (gave up after waiting "
                              f"{waited:.0f}s of a {config.RETRY_WAIT_BUDGET_SECONDS}s budget)")
                break
            time.sleep(wait)
            waited += wait
    raise LLMError(f"provider unreachable after {config.LLM_MAX_RETRIES} attempts - {last_error}")


def _retry_after_seconds(response) -> float | None:
    """How long the provider asked us to wait, if it said.

    Groq answers a 429 with retry-after (and x-ratelimit-reset-* on some plans).
    Reading it is the difference between backing off for the real window and
    guessing three seconds at a limit that resets by the minute.
    """
    # Defensive: this runs while handling an error, and a crash here would hide
    # the failure it is meant to explain.
    headers = getattr(response, "headers", None) or {}
    for header in ("retry-after", "x-ratelimit-reset-tokens", "x-ratelimit-reset-requests"):
        raw = headers.get(header)
        if not raw:
            continue
        try:
            return max(0.0, float(str(raw).rstrip("s")))
        except ValueError:
            continue
    return None


def _openai_chat(provider, model, prompt, system, temperature, max_tokens) -> str:
    base, token = _endpoint(provider)
    messages = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
    data = _post_with_retries(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
        json_body={"model": model, "messages": messages,
                   "temperature": temperature, "max_tokens": max_tokens},
    )
    try:
        choice = data["choices"][0]
        content = choice["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise LLMError(f"unexpected {PROVIDER_NAMES.get(provider, provider)} response "
                       f"shape: {str(data)[:300]}") from exc

    # A reply cut off at the token limit is not malformed JSON, it is an
    # incomplete one - and reasoning models spend part of this budget thinking
    # before they answer. Saying which it is turns a silent fallback into a
    # fixable number.
    if choice.get("finish_reason") == "length":
        raise LLMError(f"reply truncated at the {max_tokens}-token limit - "
                       f"raise max_tokens for this call")
    return content


def _call_openai_compatible(provider, prompt, system, temperature, max_tokens) -> str:
    model = resolve_model(provider)
    try:
        return _openai_chat(provider, model, prompt, system, temperature, max_tokens)
    except ModelNotAvailable:
        # The model was retired, renamed, or is not on this key. Ask the provider
        # what it does offer and try once more, rather than dropping the whole run
        # to the deterministic fallback over a stale name.
        replacement = resolve_model(provider, force=True, exclude=frozenset({model}))
        if replacement == model:
            raise
        return _openai_chat(provider, replacement, prompt, system, temperature,
                            max_tokens)


def _call_gemini(prompt, system, temperature, max_tokens) -> str:
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    data = _post_with_retries(
        f"https://generativelanguage.googleapis.com/v1beta/models/{active_model()}:generateContent",
        headers={"Content-Type": "application/json"},
        params={"key": config.GEMINI_API_KEY},
        json_body=body,
    )
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise LLMError(f"unexpected Gemini response shape: {str(data)[:300]}") from exc


def _call_ollama(prompt, system, temperature, max_tokens) -> str:
    messages = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
    data = _post_with_retries(
        f"{config.OLLAMA_HOST.rstrip('/')}/api/chat",
        headers={"Content-Type": "application/json"},
        json_body={"model": active_model(), "messages": messages, "stream": False,
                   "options": {"temperature": temperature, "num_predict": max_tokens}},
    )
    try:
        return data["message"]["content"]
    except KeyError as exc:
        raise LLMError(f"unexpected Ollama response shape: {str(data)[:300]}") from exc


if __name__ == "__main__":
    # python -m src.llm            smoke-test the provider
    # python -m src.llm --models   list what this key can actually run
    import sys

    if not is_configured():
        print(configuration_hint())
        raise SystemExit(1)

    if "--models" in sys.argv:
        provider = config.LLM_PROVIDER
        if provider not in OPENAI_COMPATIBLE:
            print(f"--models applies to groq and hf, which publish a model list. "
                  f"Provider is {provider}.")
            raise SystemExit(1)
        try:
            entries = _list_model_entries(provider)
        except (LLMError, requests.RequestException) as exc:
            print(f"Could not list models: {exc}")
            raise SystemExit(1)
        preferences = _preferences(provider)
        usable = sorted((m["id"] for m in entries
                         if _serves_text(m) and _usable(m["id"], provider)),
                        key=lambda model_id: _rank(model_id, preferences))
        print(f"{len(entries)} models on this key, {len(usable)} usable for this project:\n")
        for index, model in enumerate(usable):
            print(f"  {'-> ' if index == 0 else '   '}{model}")
        print(f"\nWould use: {usable[0] if usable else '(none)'}")
        raise SystemExit(0)

    print(f"Provider: {describe()}")
    print("Reply:", complete("Reply with exactly: OK", max_tokens=10).strip())
    print(f"Resolved model: {active_model()}  ({resolution_note()})")
