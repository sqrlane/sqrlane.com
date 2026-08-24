"""llm.py - the ONLY place this project talks to an AI provider.

Every agent (risk_monitor, route_advisor, comms_agent) calls the functions here.
Nothing else imports a provider SDK or builds an inference request. That is the
whole point: to switch from Groq to Gemini to a local Ollama model you change
LLM_PROVIDER in .env and touch no other file.

All three providers are spoken to over plain HTTP with `requests`, so there is
no extra SDK to install and no third way for things to break.

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
    if provider == "gemini":
        return bool(config.GEMINI_API_KEY)
    if provider == "ollama":
        return bool(config.OLLAMA_HOST)  # no key; reachability is checked on call
    return False


# Resolved once per process. Serverless gives each cold start its own process,
# so this is at most one extra request per container, not per run.
_resolved_groq_model: str | None = None
_resolution_note: str = ""


def list_groq_models() -> list[str]:
    """Ask Groq what this key can actually run. Read-only."""
    response = requests.get(
        "https://api.groq.com/openai/v1/models",
        headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
        timeout=config.LLM_TIMEOUT_SECONDS,
    )
    if response.status_code != 200:
        raise LLMError(f"could not list models: HTTP {response.status_code} "
                       f"{response.text[:200]}")
    return [m["id"] for m in response.json().get("data", []) if m.get("id")]


def _usable(model_id: str) -> bool:
    """Chat models only - not audio, safety classifiers or embeddings."""
    lowered = model_id.lower()
    return not any(bad in lowered for bad in config.GROQ_MODEL_EXCLUDE)


def _rank(model_id: str) -> tuple:
    """Sort key: preferred models first, then bigger/instruct-looking ones.

    The fallback half matters - it is what picks a sensible model from a lineup
    this code has never heard of.
    """
    lowered = model_id.lower()
    for position, preferred in enumerate(config.GROQ_MODEL_PREFERENCES):
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


def resolve_groq_model(*, force: bool = False, exclude: frozenset = frozenset()) -> str:
    """Decide which Groq model to call, asking Groq if we do not already know.

    An explicit LLM_MODEL in .env wins, but is not a hard pin: if it turns out
    to be retired, discovery still rescues the run rather than failing it.
    """
    global _resolved_groq_model, _resolution_note

    if not force and _resolved_groq_model and _resolved_groq_model not in exclude:
        return _resolved_groq_model

    if config.LLM_MODEL and config.LLM_MODEL not in exclude:
        _resolved_groq_model = config.LLM_MODEL
        _resolution_note = "pinned by LLM_MODEL in .env"
        return _resolved_groq_model

    try:
        available = [m for m in list_groq_models() if _usable(m) and m not in exclude]
    except (LLMError, requests.RequestException) as exc:
        # Could not ask. Fall back to the first preference and let the call fail
        # loudly if that is wrong, rather than guessing silently.
        _resolved_groq_model = next(
            (m for m in config.GROQ_MODEL_PREFERENCES if m not in exclude),
            config.GROQ_MODEL_PREFERENCES[0])
        _resolution_note = f"could not reach the model list ({exc}); using a default"
        return _resolved_groq_model

    if not available:
        raise ModelNotAvailable(
            "This Groq key exposes no usable chat model. Check the key at "
            "https://console.groq.com, or pin one with LLM_MODEL in .env.")

    available.sort(key=_rank)
    _resolved_groq_model = available[0]
    known = _resolved_groq_model.lower() in {p.lower() for p in config.GROQ_MODEL_PREFERENCES}
    _resolution_note = ("chosen from the models this key offers" if known else
                        f"chosen from the models this key offers "
                        f"(not in the preference list; {len(available)} available)")
    return _resolved_groq_model


def active_model() -> str:
    """The model that will be used, without forcing a lookup."""
    if config.LLM_PROVIDER == "groq":
        return _resolved_groq_model or config.LLM_MODEL or "(resolved on first call)"
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

    if provider == "groq":
        return _call_groq(prompt, system, temperature, max_tokens)
    if provider == "gemini":
        return _call_gemini(prompt, system, temperature, max_tokens)
    if provider == "ollama":
        return _call_ollama(prompt, system, temperature, max_tokens)
    raise LLMNotConfigured(f"Unknown LLM_PROVIDER {provider!r}. Use groq, gemini or ollama.")


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
    return ("model_not_found" in lowered
            or ("model" in lowered and ("does not exist" in lowered
                                        or "not found" in lowered
                                        or "decommission" in lowered
                                        or "no longer supported" in lowered)))


def _post_with_retries(url: str, *, headers=None, json_body=None, params=None) -> dict:
    """POST with backoff on rate limits and transient server errors.

    Free tiers rate-limit aggressively, and a demo that dies on one 429 is
    not a demo.
    """
    last_error = None
    for attempt in range(config.LLM_MAX_RETRIES):
        try:
            response = requests.post(url, headers=headers, json=json_body,
                                     params=params, timeout=config.LLM_TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            last_error = f"network error: {exc}"
        else:
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
            time.sleep(2 ** attempt)
    raise LLMError(f"provider unreachable after {config.LLM_MAX_RETRIES} attempts - {last_error}")


def _groq_chat(model, prompt, system, temperature, max_tokens) -> str:
    messages = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
    data = _post_with_retries(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {config.GROQ_API_KEY}",
                 "Content-Type": "application/json"},
        json_body={"model": model, "messages": messages,
                   "temperature": temperature, "max_tokens": max_tokens},
    )
    try:
        choice = data["choices"][0]
        content = choice["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise LLMError(f"unexpected Groq response shape: {str(data)[:300]}") from exc

    # A reply cut off at the token limit is not malformed JSON, it is an
    # incomplete one - and reasoning models spend part of this budget thinking
    # before they answer. Saying which it is turns a silent fallback into a
    # fixable number.
    if choice.get("finish_reason") == "length":
        raise LLMError(f"reply truncated at the {max_tokens}-token limit - "
                       f"raise max_tokens for this call")
    return content


def _call_groq(prompt, system, temperature, max_tokens) -> str:
    model = resolve_groq_model()
    try:
        return _groq_chat(model, prompt, system, temperature, max_tokens)
    except ModelNotAvailable:
        # The model was retired, renamed, or is not on this key. Ask Groq what it
        # does offer and try once more, rather than dropping the whole run to the
        # deterministic fallback over a stale name.
        replacement = resolve_groq_model(force=True, exclude=frozenset({model}))
        if replacement == model:
            raise
        return _groq_chat(replacement, prompt, system, temperature, max_tokens)


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
        if config.LLM_PROVIDER != "groq":
            print(f"--models only applies to Groq. Provider is {config.LLM_PROVIDER}.")
            raise SystemExit(1)
        try:
            models = list_groq_models()
        except (LLMError, requests.RequestException) as exc:
            print(f"Could not list models: {exc}")
            raise SystemExit(1)
        usable = sorted((m for m in models if _usable(m)), key=_rank)
        print(f"{len(models)} models on this key, {len(usable)} usable for this project:\n")
        for index, model in enumerate(usable):
            print(f"  {'-> ' if index == 0 else '   '}{model}")
        print(f"\nWould use: {usable[0] if usable else '(none)'}")
        raise SystemExit(0)

    print(f"Provider: {describe()}")
    print("Reply:", complete("Reply with exactly: OK", max_tokens=10).strip())
    print(f"Resolved model: {active_model()}  ({resolution_note()})")
