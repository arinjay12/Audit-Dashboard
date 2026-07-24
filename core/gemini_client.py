"""
Thin wrapper around the google-genai SDK.

Two resilience features matter here:

1. Key rotation — we hold a pool of API keys (GEMINI_API_KEY, GEMINI_API_KEY_2, …).
   When one key hits its daily/rate quota (HTTP 429), we transparently fall over to
   the next key. This lets a free-tier demo pool the per-key quotas of two accounts.

2. Retry with backoff — transient server errors (HTTP 503 "model overloaded") are
   retried on the same key with exponential backoff, so a momentary blip never
   surfaces as a raw error mid-demo.

Public API: generate(prompt) and generate_json(prompt) — unchanged signatures.
"""

import json
import os
import time

from google import genai
from google.genai import types, errors

# Names we look for, in priority order. Add GEMINI_API_KEY_3 etc. to extend the pool.
_KEY_NAMES = ["GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"]

_MAX_ROUNDS = 2          # full passes over the key pool before giving up
_RETRIES_PER_KEY = 3     # 503 retries on a single key before rotating
_BASE_BACKOFF = 2.0      # seconds; grows exponentially per retry


# ── initialisation ────────────────────────────────────────────────────────────

def _load_api_keys() -> list[str]:
    """
    Collect every configured key into an ordered, de-duplicated list.
    Looks in Streamlit secrets first (for the deployed app), then environment
    variables (which is how the test scripts load secrets.toml).
    """
    keys: list[str] = []

    try:
        import streamlit as st
        for name in _KEY_NAMES:
            val = st.secrets.get(name)
            if val and val not in keys:
                keys.append(val)
    except Exception:
        pass

    for name in _KEY_NAMES:
        val = os.environ.get(name, "")
        if val and val not in keys:
            keys.append(val)

    if not keys:
        raise EnvironmentError(
            "No Gemini API key found. Set GEMINI_API_KEY (and optionally "
            "GEMINI_API_KEY_2) in .streamlit/secrets.toml or as environment variables."
        )
    return keys


def _get_model_name() -> str:
    try:
        import streamlit as st
        return st.secrets.get("GEMINI_MODEL", "gemini-2.5-flash")
    except Exception:
        return os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


_clients = [genai.Client(api_key=k) for k in _load_api_keys()]
_MODEL = _get_model_name()


# ── core request loop (rotation + backoff) ────────────────────────────────────

def _request(contents: str, config: types.GenerateContentConfig):
    """
    Run a generate_content call against the key pool.

    - 503 (server overloaded)  → wait with exponential backoff, retry SAME key.
    - 429 (quota / rate limit) → rotate to the NEXT key immediately.
    - other 4xx                → raise straight away (it's a real request bug).

    Cycles through every key up to _MAX_ROUNDS times before surfacing the error.
    """
    last_error = None

    for round_num in range(_MAX_ROUNDS):
        for client in _clients:
            for attempt in range(_RETRIES_PER_KEY):
                try:
                    return client.models.generate_content(
                        model=_MODEL, contents=contents, config=config
                    )
                except errors.ServerError as e:        # 5xx — transient, retry same key
                    last_error = e
                    time.sleep(_BASE_BACKOFF * (2 ** attempt))
                except errors.ClientError as e:        # 4xx
                    last_error = e
                    if e.code == 429:                  # quota/rate — try the next key
                        break
                    raise                              # 400 etc. — a genuine error
        # Finished a full pass over all keys; pause before the next round in case a
        # per-minute window needs to recover.
        time.sleep(_BASE_BACKOFF * (round_num + 1))

    raise last_error


# ── public API ────────────────────────────────────────────────────────────────

def generate(prompt: str, temperature: float = 0.3) -> str:
    """
    Send a plain prompt, return the text response.
    Low default temperature keeps answers grounded in the documents
    (less creative drift / hallucination) — good for Q&A over audit data.
    """
    response = _request(prompt, types.GenerateContentConfig(temperature=temperature))
    # response.text is None when the model returns no candidates (e.g. a safety
    # block) — surface a clean error instead of returning the literal None.
    if not response.text:
        raise RuntimeError("Gemini returned an empty response. Please try again.")
    return response.text


_JSON_RETRIES = 1  # extra full regenerations if the response body isn't valid JSON


def generate_json(prompt: str, temperature: float = 0.0) -> dict:
    """
    Send a prompt instructing Gemini to return JSON.

    Uses response_mime_type="application/json" so the model is constrained to
    emit valid JSON (no markdown fences, no prose) — far more reliable than
    asking in text. temperature=0 makes extraction deterministic and accurate.

    response_mime_type constrains the model to JSON *syntax on average*, but on
    long outputs (e.g. 30+ findings) it can still occasionally drop a closing
    brace mid-generation — a token-level slip, not a prompt problem. Since a
    fresh call is very unlikely to repeat the exact same slip, we regenerate
    the whole response (up to _JSON_RETRIES times) rather than fail outright.

    Returns a parsed dict. Raises ValueError if every attempt returns invalid JSON.
    """
    last_error = None
    last_raw = ""

    for attempt in range(_JSON_RETRIES + 1):
        response = _request(
            prompt,
            types.GenerateContentConfig(
                temperature=temperature,
                response_mime_type="application/json",
            ),
        )
        # None (no candidates) becomes "" — json.loads("") fails, and the
        # existing regeneration loop treats it like any other bad response.
        raw = (response.text or "").strip()

        # Safety net: strip markdown code fences if any slip through
        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            last_error, last_raw = e, raw

    raise ValueError(
        f"Gemini did not return valid JSON after {_JSON_RETRIES + 1} attempt(s).\n"
        f"Error: {last_error}\nRaw response:\n{last_raw}"
    ) from last_error
