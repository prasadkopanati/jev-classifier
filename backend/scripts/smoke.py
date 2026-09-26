"""Make one real call to Zen /systemone and print the response SHAPE only.

Never prints the API key or request headers.
Run from backend/:  uv run python scripts/smoke.py
"""

import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

URL = "https://opencode.ai/zen/v1/systemone"
MODEL = "jev-1.13"
TEXT = (
    "I have been billed twice for the subscription and I want to review the "
    "charge and reverse it asap"
)

BODY = {
    "model": MODEL,
    "state": TEXT,
    "questions": {
        "department": {
            "type": "choice",
            "instructions": "Which team should handle this",
            "criteria": {
                "billing": "Payment or subscription issues",
                "technical": "Bugs or integration problems",
                "sales": "Pricing or account questions",
            },
        },
        "frustration": {
            "type": "score",
            "instructions": "How frustrated the customer appears",
            "criteria": [
                "Calm, just stating facts",
                "Frustrated but civil",
                "Very angry, strong language",
            ],
        },
        "is_urgent": {
            "type": "noul",
            "instructions": "The message conveys urgency or time-sensitivity",
        },
    },
}


def main() -> int:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    key = os.environ.get("ZEN_API_KEY", "")
    if not key:
        print("ZEN_API_KEY is not set (expected in the project-root .env)")
        return 1

    start = time.perf_counter()
    try:
        resp = httpx.post(
            URL,
            json=BODY,
            headers={"Authorization": f"Bearer {key}"},
            timeout=30,
        )
    except httpx.HTTPError as exc:
        print(f"Request failed: {type(exc).__name__}")
        return 1
    elapsed_ms = (time.perf_counter() - start) * 1000

    print(f"HTTP status: {resp.status_code}")
    print(f"Elapsed: {elapsed_ms:.0f} ms")

    if resp.status_code != 200:
        print("Error body (truncated):", resp.text.replace(key, "***")[:300])
        return 1

    data = resp.json()
    print("Top-level keys:", sorted(data))
    print("model:", data.get("model"))
    answers = data.get("answers", {})
    for qid, ans in answers.items():
        print(f"  answer {qid}: type={ans.get('type')} keys={sorted(ans)}")
    usage = data.get("usage")
    print("usage present:", usage is not None, usage or "")
    if usage and "input_tokens" in usage:
        print(f"cost estimate: ${usage['input_tokens'] / 1e6 * 0.042:.8f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
