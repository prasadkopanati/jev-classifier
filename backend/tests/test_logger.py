import json
import threading

import pytest

from app.logger import append_entry, build_entry

FAKE_KEY = "test-key-123"


@pytest.fixture(autouse=True)
def fake_key(monkeypatch):
    monkeypatch.setenv("ZEN_API_KEY", FAKE_KEY)
    monkeypatch.setattr("app.config.load_dotenv", lambda *a, **k: None)


def ok_entry(text="hello"):
    return build_entry(
        input_text=text,
        request={"state": text},
        response={"answers": {}},
        cost_usd=0.00002,
        cost_estimated=False,
        latency_ms=1690.5,
        status="ok",
    )


def read_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_one_valid_json_line_per_call(tmp_path):
    log = tmp_path / "log.jsonl"
    append_entry(ok_entry("a"), log)
    append_entry(ok_entry("b"), log)
    lines = read_lines(log)
    assert [entry["input_text"] for entry in lines] == ["a", "b"]


def test_entry_has_all_fields(tmp_path):
    log = tmp_path / "log.jsonl"
    append_entry(ok_entry(), log)
    (entry,) = read_lines(log)
    assert set(entry) == {
        "timestamp", "input_text", "request", "response", "cost_usd",
        "cost_estimated", "latency_ms", "status", "error",
    }
    assert entry["status"] == "ok"
    assert entry["cost_usd"] == 0.00002
    assert entry["latency_ms"] == 1690.5


def test_error_entry_is_recorded(tmp_path):
    log = tmp_path / "log.jsonl"
    entry = build_entry(
        input_text="hi",
        request={"state": "hi"},
        response=None,
        cost_usd=None,
        cost_estimated=None,
        latency_ms=30000.0,
        status="error",
        error={"code": "timeout", "message": "The Jev request timed out."},
    )
    append_entry(entry, log)
    (saved,) = read_lines(log)
    assert saved["status"] == "error"
    assert saved["error"]["code"] == "timeout"
    assert saved["response"] is None
    assert saved["latency_ms"] == 30000.0


def test_api_key_never_reaches_the_file(tmp_path):
    log = tmp_path / "log.jsonl"
    entry = ok_entry(f"my key is {FAKE_KEY}")
    entry["error"] = {"detail": f"Bearer {FAKE_KEY}"}
    append_entry(entry, log)
    assert FAKE_KEY not in log.read_text()
    assert "***" in log.read_text()


def test_non_ascii_text_round_trips(tmp_path):
    log = tmp_path / "log.jsonl"
    append_entry(ok_entry("café 请退款"), log)
    (entry,) = read_lines(log)
    assert entry["input_text"] == "café 请退款"


def test_concurrent_appends_stay_one_json_object_per_line(tmp_path):
    log = tmp_path / "log.jsonl"
    threads = [
        threading.Thread(target=append_entry, args=(ok_entry(f"t{i}" * 200), log))
        for i in range(40)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(read_lines(log)) == 40
