"""Calls Zen /systemone. The only module that reads the API key or builds auth headers."""

import time
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import ValidationError

from app.config import JEV_URL, TIMEOUT_SECONDS, get_api_key
from app.schemas import JevResponse

_CREDIT_WORDS = ("insufficient", "credit", "balance", "billing")


class JevError(Exception):
    """Base class for failures calling Jev. Carries what the API layer and log need."""

    code = "upstream_error"
    http_status = 502
    message = "The Jev service returned an unexpected error."

    def __init__(
        self,
        *,
        latency_ms: float | None = None,
        upstream_status: int | None = None,
        detail: str | None = None,
    ):
        super().__init__(self.message)
        self.latency_ms = latency_ms
        self.upstream_status = upstream_status
        self.detail = detail


class MissingApiKeyError(JevError):
    code = "missing_api_key"
    http_status = 500
    message = "The server has no ZEN_API_KEY configured."


class AuthError(JevError):
    code = "auth_error"
    http_status = 502
    message = "Zen rejected the API key. Check ZEN_API_KEY."


class InsufficientCreditError(JevError):
    code = "insufficient_credit"
    http_status = 402
    message = "The Zen account has no credit left. Add funds and try again."


class RateLimitError(JevError):
    code = "rate_limited"
    http_status = 429
    message = "Zen rate limit reached. Wait a moment and try again."


class JevTimeoutError(JevError):
    code = "timeout"
    http_status = 504
    message = "The Jev request timed out."


class MalformedResponseError(JevError):
    code = "malformed_response"
    http_status = 502
    message = "Jev returned a response in an unexpected format."


@dataclass
class JevCall:
    raw: dict[str, Any]
    parsed: JevResponse
    latency_ms: float


def _safe_detail(text: str, key: str) -> str:
    return text.replace(key, "***")[:300]


def _raise_for_status(resp: httpx.Response, key: str, latency_ms: float) -> None:
    status = resp.status_code
    detail = _safe_detail(resp.text, key)
    kwargs = {"latency_ms": latency_ms, "upstream_status": status, "detail": detail}
    lowered = resp.text.lower()
    if status == 401 or status == 403:
        raise AuthError(**kwargs)
    if status == 402 or (
        status in (400, 429) and any(w in lowered for w in _CREDIT_WORDS)
    ):
        raise InsufficientCreditError(**kwargs)
    if status == 429:
        raise RateLimitError(**kwargs)
    raise JevError(**kwargs)


def call_jev(body: dict[str, Any]) -> JevCall:
    """POST the body to /systemone. Latency covers the HTTP round trip only."""
    key = get_api_key()
    if not key:
        raise MissingApiKeyError()

    start = time.perf_counter()
    try:
        resp = httpx.post(
            JEV_URL,
            json=body,
            headers={"Authorization": f"Bearer {key}"},
            timeout=TIMEOUT_SECONDS,
        )
    except httpx.TimeoutException as exc:
        latency = (time.perf_counter() - start) * 1000
        raise JevTimeoutError(latency_ms=latency, detail=type(exc).__name__) from exc
    except httpx.HTTPError as exc:
        latency = (time.perf_counter() - start) * 1000
        raise JevError(
            latency_ms=latency, detail=f"network error: {type(exc).__name__}"
        ) from exc
    latency_ms = (time.perf_counter() - start) * 1000

    if resp.status_code >= 400:
        _raise_for_status(resp, key, latency_ms)

    try:
        raw = resp.json()
        parsed = JevResponse.model_validate(raw)
    except (ValueError, ValidationError) as exc:
        raise MalformedResponseError(
            latency_ms=latency_ms,
            upstream_status=resp.status_code,
            detail=_safe_detail(resp.text, key),
        ) from exc
    return JevCall(raw=raw, parsed=parsed, latency_ms=latency_ms)
