import json
import math
from typing import Any

from app.config import PRICE_PER_MILLION_INPUT_TOKENS_USD
from app.schemas import Usage


def estimate_input_tokens(request_body: dict[str, Any]) -> int:
    """Rough token estimate (about 4 characters per token) used only when usage is missing."""
    return math.ceil(len(json.dumps(request_body)) / 4)


def compute_cost(
    usage: Usage | None, request_body: dict[str, Any]
) -> tuple[float, bool]:
    """Return (cost_usd, estimated). Only input tokens are billed; output is free."""
    if usage is not None:
        return usage.input_tokens / 1_000_000 * PRICE_PER_MILLION_INPUT_TOKENS_USD, False
    tokens = estimate_input_tokens(request_body)
    return tokens / 1_000_000 * PRICE_PER_MILLION_INPUT_TOKENS_USD, True
