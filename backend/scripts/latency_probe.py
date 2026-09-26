"""Diagnose where /systemone latency goes. Makes 10 real calls (about $0.0003 in total).

Compares a fresh connection per call (what the app does today) with a reused connection,
and a 7-question request with a 1-question request. Also lists the response header names,
to see whether Zen forwards any server-side timing from Jev.

Never prints the API key or request headers.
Run from backend/:  uv run python scripts/latency_probe.py
"""

import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import JEV_URL, get_api_key  # noqa: E402
from app.questions import build_request  # noqa: E402

TEXT = "I have been billed twice for the subscription and I want to review the charge and reverse it asap"
SENSITIVE = {"set-cookie", "authorization"}


def timed_call(client: httpx.Client, body: dict, key: str) -> dict:
    events: dict[str, float] = {}

    def trace(name: str, info: dict) -> None:
        events[name] = time.perf_counter()

    start = time.perf_counter()
    resp = client.post(
        JEV_URL,
        json=body,
        headers={"Authorization": f"Bearer {key}"},
        timeout=30,
        extensions={"trace": trace},
    )
    total = (time.perf_counter() - start) * 1000

    def span(a: str, b: str) -> float:
        return (events[b] - events[a]) * 1000 if a in events and b in events else 0.0

    sent = "http11.send_request_body.complete"
    return {
        "status": resp.status_code,
        "total": total,
        "tcp": span("connection.connect_tcp.started", "connection.connect_tcp.complete"),
        "tls": span("connection.start_tls.started", "connection.start_tls.complete"),
        "wait": span(sent, "http11.receive_response_headers.complete"),
        "resp": resp,
    }


def show(label: str, rows: list[dict]) -> None:
    print(f"\n{label}")
    print(f"  {'total':>8} {'tcp':>6} {'tls':>6} {'wait(server+net)':>17}  status")
    for r in rows:
        print(f"  {r['total']:8.0f} {r['tcp']:6.0f} {r['tls']:6.0f} {r['wait']:17.0f}  {r['status']}")
    totals = sorted(r["total"] for r in rows)
    print(f"  median total: {totals[len(totals) // 2]:.0f} ms")


def main() -> int:
    key = get_api_key()
    if not key:
        print("ZEN_API_KEY is not set")
        return 1

    body7 = build_request(TEXT)
    body1 = {**body7, "questions": {"is_urgent": body7["questions"]["is_urgent"]}}

    t = time.perf_counter()
    httpx.Client().close()
    print(f"Creating an httpx client (loads the CA bundle): {(time.perf_counter() - t) * 1000:.0f} ms")

    fresh = []
    for _ in range(3):
        with httpx.Client() as c:
            fresh.append(timed_call(c, body7, key))
    show("A) 7 questions, NEW connection per call (like the app today)", fresh)

    with httpx.Client() as c:
        timed_call(c, body7, key)  # warm-up, not shown
        reused = [timed_call(c, body7, key) for _ in range(3)]
        show("B) 7 questions, REUSED connection (after one warm-up call)", reused)
        one = [timed_call(c, body1, key) for _ in range(3)]
        show("C) 1 question, REUSED connection", one)

    if any(r["status"] != 200 for r in fresh + reused + one):
        print("\nSome calls did not return 200; results above may not be meaningful.")

    print("\nResponse headers from the first call (values shown, cookies hidden):")
    for name, value in fresh[0]["resp"].headers.items():
        shown = "<hidden>" if name.lower() in SENSITIVE else value[:100]
        print(f"  {name}: {shown}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
