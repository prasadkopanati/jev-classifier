"""Append-only JSONL request log."""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import LOG_PATH, get_api_key

_lock = threading.Lock()


def build_entry(
    *,
    input_text: str,
    request: dict[str, Any] | None,
    response: dict[str, Any] | None,
    cost_usd: float | None,
    cost_estimated: bool | None,
    latency_ms: float | None,
    status: str,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_text": input_text,
        "request": request,
        "response": response,
        "cost_usd": cost_usd,
        "cost_estimated": cost_estimated,
        "latency_ms": latency_ms,
        "status": status,
        "error": error,
    }


def append_entry(entry: dict[str, Any], path: Path | None = None) -> None:
    """Write one JSON line. Any occurrence of the API key is redacted as a safety net."""
    line = json.dumps(entry, ensure_ascii=False, default=str)
    key = get_api_key()
    if key:
        line = line.replace(key, "***")
    target = path or LOG_PATH
    with _lock:
        with open(target, "a", encoding="utf-8") as f:
            f.write(line + "\n")
