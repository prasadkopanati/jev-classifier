import httpx
import pytest
import respx

from app.config import JEV_URL
from app.jev_client import (
    AuthError,
    InsufficientCreditError,
    JevError,
    JevTimeoutError,
    MalformedResponseError,
    MissingApiKeyError,
    RateLimitError,
    call_jev,
)
from app.questions import build_request

FAKE_KEY = "test-key-123"

GOOD = {
    "model": "jev-1.13",
    "answers": {"is_urgent": {"type": "noul", "noul": 0.9}},
    "usage": {"input_tokens": 414, "output_tokens": 73},
}


@pytest.fixture(autouse=True)
def fake_key(monkeypatch):
    monkeypatch.setenv("ZEN_API_KEY", FAKE_KEY)
    monkeypatch.setattr("app.config.load_dotenv", lambda *a, **k: None)


BODY = build_request("hello")


@respx.mock
def test_success_returns_raw_parsed_and_latency():
    route = respx.post(JEV_URL).respond(200, json=GOOD)
    call = call_jev(BODY)
    assert route.called
    assert call.raw == GOOD
    assert call.parsed.answers["is_urgent"].noul == 0.9
    assert call.parsed.usage.input_tokens == 414
    assert call.latency_ms >= 0


@respx.mock
def test_sends_bearer_key_and_body():
    route = respx.post(JEV_URL).respond(200, json=GOOD)
    call_jev(BODY)
    request = route.calls.last.request
    assert request.headers["Authorization"] == f"Bearer {FAKE_KEY}"
    assert b'"jev-1.13"' in request.content


def test_missing_key_raises_without_network(monkeypatch):
    monkeypatch.delenv("ZEN_API_KEY")
    with pytest.raises(MissingApiKeyError):
        call_jev(BODY)


@pytest.mark.parametrize(
    "status,text,exc",
    [
        (401, "bad key", AuthError),
        (403, "forbidden", AuthError),
        (402, "payment required", InsufficientCreditError),
        (400, "Insufficient balance", InsufficientCreditError),
        (429, "slow down", RateLimitError),
        (429, "Out of credit", InsufficientCreditError),
        (500, "boom", JevError),
        (503, "unavailable", JevError),
    ],
)
@respx.mock
def test_http_errors_are_mapped_and_carry_latency(status, text, exc):
    respx.post(JEV_URL).respond(status, text=text)
    with pytest.raises(exc) as info:
        call_jev(BODY)
    assert type(info.value) is exc
    assert info.value.upstream_status == status
    assert info.value.latency_ms >= 0


@respx.mock
def test_timeout_is_mapped_and_carries_latency():
    respx.post(JEV_URL).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(JevTimeoutError) as info:
        call_jev(BODY)
    assert info.value.latency_ms >= 0


@respx.mock
def test_network_error_is_upstream_error():
    respx.post(JEV_URL).mock(side_effect=httpx.ConnectError("down"))
    with pytest.raises(JevError) as info:
        call_jev(BODY)
    assert type(info.value) is JevError
    assert info.value.latency_ms >= 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"text": "not json"},
        {"json": {"model": "jev-1.13"}},
        {"json": {"model": "jev-1.13", "answers": {"x": {"type": "mystery"}}}},
    ],
)
@respx.mock
def test_malformed_success_response(kwargs):
    respx.post(JEV_URL).respond(200, **kwargs)
    with pytest.raises(MalformedResponseError) as info:
        call_jev(BODY)
    assert info.value.latency_ms >= 0


@respx.mock
def test_key_is_redacted_from_error_detail():
    respx.post(JEV_URL).respond(401, text=f"invalid key {FAKE_KEY}")
    with pytest.raises(AuthError) as info:
        call_jev(BODY)
    assert FAKE_KEY not in info.value.detail
    assert "***" in info.value.detail
