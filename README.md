# Jev Classifier

A small local app for evaluating Jev, TypeSafe's classification-only "System One" model, through opencode.ai Zen. Paste a customer message and Jev classifies it on seven fixed metrics. The page shows each answer with its confidence and probabilities, plus the cost and latency of the request. Every call is logged.

Requirements are in [PRD.md](PRD.md). The build plan is in [PLAN.md](PLAN.md). Working rules are in [CLAUDE.md](CLAUDE.md).

## Setup
Prerequisites: [uv](https://docs.astral.sh/uv/), Node.js and npm, and a funded opencode.ai Zen account.

1. Create `.env` in the project root (it is git-ignored, see `.env.example`):
   ```
   ZEN_API_KEY=your-key-here
   ```
2. Install from the lockfiles:
   ```
   cd backend && uv sync --locked
   cd ../frontend && npm ci
   ```

## Run
Two terminals:
```
cd backend && uv run --locked uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```
Open http://localhost:5173. The frontend proxies `/api` to the backend on port 8000.

## Test
```
cd backend && uv run --locked pytest        # mocked Jev API, no network, no key needed
cd backend && uv run python scripts/smoke.py           # one real call, prints the response shape only
cd backend && uv run python scripts/latency_probe.py   # 10 real calls (~$0.0003), see "Latency" below
cd frontend && npm run build                # typecheck and production build
```
The two scripts make real calls with your key and spend a little credit.

## The metrics
Defined in one place, `backend/app/questions.py`.

| id | type | options |
|---|---|---|
| `intent` | choice | billing, technical, sales, general_inquiry, complaint |
| `department` | choice | billing, technical, sales |
| `frustration` | score | 0 calm, 1 frustrated but civil, 2 very angry |
| `is_urgent` | noul | the message conveys urgency or time-sensitivity |
| `refund_requested` | noul | the customer asks for money back or a charge reversal |
| `wants_human` | noul | the customer asks for a human agent or escalation |
| `churn_risk` | noul | the customer threatens to cancel or leave |

## API
- `GET /api/health` returns `{"status": "ok"}`.
- `POST /api/classify` takes `{"text": "..."}` (1 to 5000 characters) and returns `answers`, `cost_usd`, `cost_estimated`, `latency_ms`, `model` and `raw_response`.
- Errors return `{"error": {"code", "message"}}`: `invalid_input` (422), `insufficient_credit` (402), `rate_limited` (429), `timeout` (504), `auth_error`, `upstream_error` and `malformed_response` (502), `missing_api_key` (500).

## Log
`log.jsonl` at the project root gets one JSON line per call to Jev, including failures: `timestamp`, `input_text`, `request`, `response`, `cost_usd`, `cost_estimated`, `latency_ms`, `status`, `error`. It is git-ignored because it contains the text you typed. The API key is redacted from every line.

## Cost
`usage.input_tokens / 1,000,000 x $0.042`. Output tokens are free. If a response has no `usage`, the cost is estimated from the request size and flagged `estimated`. A typical request costs about $0.000026, so the UI shows six decimals.

## Latency
`latency_ms` is measured in the backend with `time.perf_counter()` around the single HTTP call to Zen. It is the round trip as the backend sees it, and includes:
- creating the HTTP client and loading the CA bundle (the app currently makes a new client per call)
- DNS, TCP and TLS setup to opencode.ai
- Zen's gateway, then Jev, then the response coming back

It does not include our own request building, response parsing, cost calculation or logging.

It is **not** Jev's own compute time. Neither Zen's response body (`answers`, `model`, `usage`) nor TypeSafe's documentation contains a latency value. TypeSafe's own API sends `x-envoy-upstream-service-time`, but Zen's responses to invalid-key requests carry no such header. Whether Zen forwards it on successful calls is what `scripts/latency_probe.py` checks.

Measurements so far (from one machine, 2026-09-26):
- Successful calls in `log.jsonl` took 1.2 to 1.9 s (median about 1.5 s).
- A call rejected at Zen's auth step, so Jev never ran, took 1.4 s in the app.
- With curl, that same rejected call took about 0.9 to 1.1 s on a new connection: roughly 0.5 s of TLS setup plus 0.4 s for Zen to answer. On a reused connection it took about 0.4 s.
- Calling TypeSafe's API directly with an invalid key took about 0.4 to 0.5 s in total.

So most of the observed latency is connection setup and the Zen hop, not model inference. Treat `latency_ms` as end-to-end time through Zen, not as Jev's model speed.

## Dependencies and supply chain rules
Goal: avoid freshly published (possibly compromised) versions, and make every install reproducible.

- **7-day minimum age.**
  - Python: `backend/pyproject.toml` sets `exclude-newer = "7 days"`. It is re-evaluated when the lock is refreshed. The current lock resolved with a cutoff of 2026-09-19.
  - npm: `frontend/.npmrc` sets `before=2026-09-19`, a fixed date. (npm 11.8.0 does not support `min-release-age`. It only warns and enforces nothing, so it is not used.)
- **Locked and exact.** `uv.lock` and `package-lock.json` are committed. `.npmrc` sets `save-exact=true`, so `package.json` has no `^` or `~`. Install with `uv sync --locked` and `npm ci`.
- **No install-time code.** Python has `no-build = true` (prebuilt wheels only). npm has `ignore-scripts=true`. The only npm package that declares an install script is `fsevents` (a macOS-only optional file watcher), which is blocked harmlessly.
- **Audits (2026-09-26):** `pip-audit` found no known vulnerabilities, and `npm audit` found 0.

Direct dependencies:

| Package | Version | First published |
|---|---|---|
| fastapi | 0.141.1 | 2026-07-29 |
| uvicorn | 0.53.0 | 2026-09-14 |
| httpx | 0.28.1 | 2024-12-06 |
| pydantic | 2.13.5 | 2026-08-28 |
| python-dotenv | 1.2.3 | 2026-08-16 |
| pytest (dev) | 9.1.1 | 2026-06-19 |
| respx (dev) | 0.23.1 | 2026-04-08 |
| react, react-dom | 19.3.0 | 2026-09-09 |
| vite | 8.3.0 | 2026-09-10 |
| @vitejs/plugin-react | 6.1.1 | 2026-08-28 |
| typescript | 7.0.2 | 2026-07-08 |
| @types/react, @types/react-dom | 19.3.0 | 2026-09-09 |

### Upgrading (deliberate, never automatic)
1. Python: `cd backend && uv lock --upgrade`, then review `git diff uv.lock`.
2. npm: set `before` in `frontend/.npmrc` to today minus 7 days, install the new versions with `npm install --save-exact <pkg>@<version>`, then review `git diff frontend/package-lock.json`.
3. Check every changed npm package for install scripts, run `uv sync --locked`, `npm ci`, the tests and `npm run build`, then repeat the audits (`uv run --with pip-audit pip-audit`, `npm audit`).
4. **Urgent security patch:** a newer-than-7-days version needs your explicit approval per package. Python: add it under `[tool.uv] exclude-newer-package`. npm: install that exact version explicitly. Note the reason here.

## Layout
```
backend/   FastAPI app (app/), tests (tests/), scripts (scripts/), uv.lock
frontend/  Vite + React + TypeScript app (src/), package-lock.json
log.jsonl  request log (created at runtime, git-ignored)
.env       ZEN_API_KEY (git-ignored, you create it)
```
