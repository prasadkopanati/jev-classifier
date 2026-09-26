import json

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.config import JEV_URL
from app.main import app

FAKE_KEY = "test-key-123"

GOOD = {
    "model": "jev-1.13",
    "answers": {
        "intent": {
            "type": "choice",
            "choice": "billing",
            "confidence": 0.9,
            "probabilities": {"billing": 0.95, "technical": 0.05},
        },
        "frustration": {
            "type": "score",
            "score": 1.0,
            "confidence": 1.0,
            "legend": {"0": "Calm", "1": "Frustrated"},
            "probabilities": {"0": 0.0, "1": 1.0},
        },
        "is_urgent": {"type": "noul", "noul": 1.0},
    },
    "usage": {"input_tokens": 414, "output_tokens": 73},
}


@pytest.fixture
def log_path(tmp_path, monkeypatch):
    path = tmp_path / "log.jsonl"
    monkeypatch.setattr("app.logger.LOG_PATH", path)
    monkeypatch.setenv("ZEN_API_KEY", FAKE_KEY)
    monkeypatch.setattr("app.config.load_dotenv", lambda *a, **k: None)
    return path


@pytest.fixture
def client(log_path):
    return TestClient(app)


def log_lines(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


@respx.mock
def test_classify_success(client, log_path):
    respx.post(JEV_URL).respond(200, json=GOOD)
    resp = client.post("/api/classify", json={"text": "I was billed twice"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "jev-1.13"
    assert data["answers"]["intent"]["choice"] == "billing"
    assert data["answers"]["is_urgent"]["noul"] == 1.0
    assert data["cost_usd"] == pytest.approx(414 / 1e6 * 0.042)
    assert data["cost_estimated"] is False
    assert data["latency_ms"] >= 0
    assert data["raw_response"] == GOOD

    (entry,) = log_lines(log_path)
    assert entry["status"] == "ok"
    assert entry["input_text"] == "I was billed twice"
    assert entry["request"]["state"] == "I was billed twice"
    assert len(entry["request"]["questions"]) == 7
    assert entry["response"] == GOOD
    assert entry["cost_usd"] == data["cost_usd"]
    assert entry["latency_ms"] == data["latency_ms"]
    assert FAKE_KEY not in log_path.read_text()


@respx.mock
def test_missing_usage_uses_flagged_estimate(client, log_path):
    no_usage = {k: v for k, v in GOOD.items() if k != "usage"}
    respx.post(JEV_URL).respond(200, json=no_usage)
    data = client.post("/api/classify", json={"text": "hi"}).json()
    assert data["cost_estimated"] is True
    assert data["cost_usd"] > 0
    assert log_lines(log_path)[0]["cost_estimated"] is True


@pytest.mark.parametrize(
    "payload",
    [{"text": ""}, {"text": "   \n\t "}, {"text": "x" * 5001}, {}, {"text": 5}],
)
@respx.mock
def test_invalid_input_is_422_and_never_calls_jev(client, log_path, payload):
    route = respx.post(JEV_URL).respond(200, json=GOOD)
    resp = client.post("/api/classify", json=payload)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid_input"
    assert not route.called
    assert log_lines(log_path) == []


@respx.mock
def test_max_length_text_is_accepted(client):
    respx.post(JEV_URL).respond(200, json=GOOD)
    assert client.post("/api/classify", json={"text": "x" * 5000}).status_code == 200


@pytest.mark.parametrize(
    "mock_kwargs,status,code",
    [
        ({"return_value": httpx.Response(401, text="bad key")}, 502, "auth_error"),
        ({"return_value": httpx.Response(402, text="pay")}, 402, "insufficient_credit"),
        ({"return_value": httpx.Response(429, text="slow")}, 429, "rate_limited"),
        ({"return_value": httpx.Response(500, text="boom")}, 502, "upstream_error"),
        ({"return_value": httpx.Response(200, text="not json")}, 502, "malformed_response"),
        ({"side_effect": httpx.ReadTimeout("slow")}, 504, "timeout"),
        ({"side_effect": httpx.ConnectError("down")}, 502, "upstream_error"),
    ],
)
@respx.mock
def test_jev_failures_return_error_contract_and_are_logged(
    client, log_path, mock_kwargs, status, code
):
    respx.post(JEV_URL).mock(**mock_kwargs)
    resp = client.post("/api/classify", json={"text": "hello"})
    assert resp.status_code == status
    error = resp.json()["error"]
    assert error["code"] == code
    assert error["message"]

    (entry,) = log_lines(log_path)
    assert entry["status"] == "error"
    assert entry["error"]["code"] == code
    assert entry["response"] is None
    assert entry["latency_ms"] >= 0
    assert entry["request"]["state"] == "hello"


@respx.mock
def test_upstream_detail_is_logged_but_not_returned_to_the_browser(client, log_path):
    respx.post(JEV_URL).respond(500, text=f"secret internals {FAKE_KEY}")
    resp = client.post("/api/classify", json={"text": "hello"})
    assert "secret internals" not in resp.text
    assert FAKE_KEY not in resp.text
    (entry,) = log_lines(log_path)
    assert "secret internals" in entry["error"]["detail"]
    assert FAKE_KEY not in log_path.read_text()


def test_missing_key_is_a_logged_500_without_network(client, log_path, monkeypatch):
    monkeypatch.delenv("ZEN_API_KEY")
    resp = client.post("/api/classify", json={"text": "hello"})
    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "missing_api_key"
    (entry,) = log_lines(log_path)
    assert entry["error"]["code"] == "missing_api_key"
    assert entry["latency_ms"] is None


@respx.mock
def test_log_write_failure_does_not_break_a_successful_call(client, monkeypatch, tmp_path):
    monkeypatch.setattr("app.logger.LOG_PATH", tmp_path / "missing_dir" / "log.jsonl")
    respx.post(JEV_URL).respond(200, json=GOOD)
    resp = client.post("/api/classify", json={"text": "hello"})
    assert resp.status_code == 200
