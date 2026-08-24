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
import time

import requests

from src import config


class LLMError(RuntimeError):
    """Any failure to get a usable answer out of the provider."""


class LLMNotConfigured(LLMError):
    """No key / no reachable provider. Callers can catch this and degrade."""


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


def describe() -> str:
    return f"{config.LLM_PROVIDER} / {config.LLM_MODEL or '(no model set)'}"


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
    # Last resort: grab the outermost {...} or [...] in the reply.
    for opener, closer in (("[", "]"), ("{", "}")):
        start, end = cleaned.find(opener), cleaned.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start:end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError(f"no JSON found in reply: {text[:200]!r}")


# --- Provider implementations (private) ------------------------------------


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
                # 401/403/404 will not fix themselves - fail immediately.
                raise LLMError(f"HTTP {response.status_code}: {response.text[:300]}")
        if attempt < config.LLM_MAX_RETRIES - 1:
            time.sleep(2 ** attempt)
    raise LLMError(f"provider unreachable after {config.LLM_MAX_RETRIES} attempts - {last_error}")


def _call_groq(prompt, system, temperature, max_tokens) -> str:
    messages = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
    data = _post_with_retries(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {config.GROQ_API_KEY}",
                 "Content-Type": "application/json"},
        json_body={"model": config.LLM_MODEL, "messages": messages,
                   "temperature": temperature, "max_tokens": max_tokens},
    )
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise LLMError(f"unexpected Groq response shape: {str(data)[:300]}") from exc


def _call_gemini(prompt, system, temperature, max_tokens) -> str:
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    data = _post_with_retries(
        f"https://generativelanguage.googleapis.com/v1beta/models/{config.LLM_MODEL}:generateContent",
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
        json_body={"model": config.LLM_MODEL, "messages": messages, "stream": False,
                   "options": {"temperature": temperature, "num_predict": max_tokens}},
    )
    try:
        return data["message"]["content"]
    except KeyError as exc:
        raise LLMError(f"unexpected Ollama response shape: {str(data)[:300]}") from exc


if __name__ == "__main__":
    # Quick smoke test:  python -m src.llm
    print(f"Provider: {describe()}")
    if not is_configured():
        print(configuration_hint())
        raise SystemExit(1)
    print("Reply:", complete("Reply with exactly: OK", max_tokens=10).strip())
