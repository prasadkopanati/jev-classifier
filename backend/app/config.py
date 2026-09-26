import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = PROJECT_ROOT / "log.jsonl"

JEV_URL = "https://opencode.ai/zen/v1/systemone"
JEV_MODEL = "jev-1.13"
TIMEOUT_SECONDS = 30.0
PRICE_PER_MILLION_INPUT_TOKENS_USD = 0.042
MAX_TEXT_CHARS = 5000


def get_api_key() -> str | None:
    """Return the Zen API key from the environment or the project-root .env."""
    load_dotenv(PROJECT_ROOT / ".env")
    return os.environ.get("ZEN_API_KEY") or None
