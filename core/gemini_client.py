"""
Gemini API wrapper. All AI calls in this project go through this module.

Two public functions:
  generate(prompt)       -> str
  generate_json(prompt)  -> dict

Model and key are read from Streamlit secrets (local: .streamlit/secrets.toml,
cloud: Streamlit Cloud secrets UI). Falls back to env var GEMINI_API_KEY so
the smoke_test.py script can run outside a Streamlit context.
"""

import json
import os

from google import genai

# ── initialisation ────────────────────────────────────────────────────────────

def _load_api_key() -> str:
    try:
        import streamlit as st
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass

    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise EnvironmentError(
            "GEMINI_API_KEY not found. Set it in .streamlit/secrets.toml "
            "or as an environment variable."
        )
    return key


def _get_model_name() -> str:
    try:
        import streamlit as st
        return st.secrets.get("GEMINI_MODEL", "gemini-2.5-flash")
    except Exception:
        return os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


_client = genai.Client(api_key=_load_api_key())
_MODEL = _get_model_name()

# ── public API ────────────────────────────────────────────────────────────────

def generate(prompt: str) -> str:
    """Send a plain prompt, return the text response."""
    response = _client.models.generate_content(model=_MODEL, contents=prompt)
    return response.text


def generate_json(prompt: str) -> dict:
    """
    Send a prompt instructing Gemini to return JSON.
    Strips any markdown fences Gemini may wrap around the response.
    Returns a parsed dict. Raises ValueError if the response isn't valid JSON.
    """
    json_prompt = (
        prompt
        + "\n\nIMPORTANT: Respond with valid JSON only. "
        "Do not include any explanation, markdown, or code fences."
    )

    response = _client.models.generate_content(model=_MODEL, contents=json_prompt)
    raw = response.text.strip()

    # Strip markdown code fences if Gemini wraps the JSON anyway
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Gemini did not return valid JSON.\nError: {e}\nRaw response:\n{raw}"
        ) from e
