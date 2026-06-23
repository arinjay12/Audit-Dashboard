"""
Smoke test — run this first to confirm your Gemini API key works.

Usage (activate your venv first), then run: python smoke_test.py
    python smoke_test.py
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

secrets_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
if os.path.exists(secrets_path):
    with open(secrets_path) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from core.gemini_client import generate, generate_json


def test_plain_text():
    print("Test 1: plain text generation...", end=" ")
    result = generate("Reply with exactly three words: 'audit pipeline works'.")
    assert len(result) > 0, "Empty response"
    print(f"OK — got: {result.strip()!r}")


def test_json_output():
    print("Test 2: JSON generation...", end=" ")
    prompt = """
    Here is a fake audit finding:
    "The petty cash fund of $500 was not reconciled for 3 months."

    Extract the following fields and return as JSON:
    - finding_text (string)
    - amount_mentioned (number or null)
    - severity (one of: High, Medium, Low)
    - category (one of: Financial, Compliance, Operational)
    """
    result = generate_json(prompt)
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert "severity" in result, f"Missing 'severity'. Got: {result}"
    print("OK")
    print(f"    Response: {json.dumps(result, indent=2)}")


if __name__ == "__main__":
    print("=" * 50)
    print("Gemini Smoke Test")
    print("=" * 50)
    try:
        test_plain_text()
        test_json_output()
        print("\nAll tests passed. Gemini is wired up correctly.")
    except Exception as e:
        print(f"\nFAILED: {e}")
        sys.exit(1)
