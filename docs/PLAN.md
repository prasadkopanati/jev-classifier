# Implementation Plan

Source of truth for requirements: `PRD.md`. Rules: `CLAUDE.md`. No code is written until this plan is approved.

## Approach
Build the backend first and prove it against the real API, then add the UI on top of a stable contract. Each task is small, ends in something verifiable and is committed on its own.

```
Phase 0 Verify API shape  ->  Phase 1 Backend core  ->  Phase 2 API + logging  ->  Phase 3 Frontend  ->  Phase 4 Docs and polish
   (gate)                      (pure, tested)            (FastAPI, tested)          (React)
```

## Decisions I'm making (tell me if you disagree)
| Topic | Decision | Reason |
|---|---|---|
| HTTP client | `httpx` (sync call inside a FastAPI route, or async `httpx.AsyncClient`) | Clean timeouts and mocking with `respx` |
| Config | `python-dotenv`, loading `.env` from the project root | The key stays out of code and out of the browser |
| Models | Pydantic models for request, response and log entry | Validates the "malformed response" case |
| Timeout | 30 s, no retries | Matches the PRD, keeps latency numbers honest |
| Latency timer | `time.perf_counter()` around the `httpx` call only | PRD definition |
| Token estimate fallback | `ceil(len(json.dumps(request_body)) / 4)` | Rough, flagged `cost_estimated: true` |
| Cost precision | Keep full float in the log, format to 6 decimals in the UI | A typical request costs about $0.00002, so 2 decimals would show $0.00 |
| Error contract | Non-2xx from our API with `{"error": {"code", "message"}}` | The UI can show a clear message per case |
| Log writes | Append one line under a `threading.Lock` | Safe for concurrent requests |
| Frontend | Vite + React + TypeScript, plain CSS, no UI library | Small app, fewer dependencies |
| Dev ports | Backend 8000, frontend 5173 with a `/api` proxy | Standard defaults |
| Package age | Nothing published less than 7 days ago (`exclude-newer` for Python; publish-date check for npm) | Supply chain defense |
| Locking | `uv.lock` and `package-lock.json` committed; installs use `uv sync --locked` and `npm ci` | Reproducible, hash-verified installs |
| Source builds | `no-build = true` for Python; `ignore-scripts=true` for npm | Blocks install-time code execution |
| Version pins | `save-exact=true` for npm, no `^` or `~` | Ranges silently accept future malicious versions |

## Target layout
```
.
├── PRD.md  CLAUDE.md  PLAN.md
├── .gitignore                 # .env, log.jsonl, node_modules, .venv, __pycache__ (lockfiles are NOT ignored)
├── .env.example               # ZEN_API_KEY=   (placeholder only)
├── log.jsonl                  # created at runtime
├── backend/
│   ├── pyproject.toml         # [tool.uv] exclude-newer, no-build
│   ├── uv.lock                # committed
│   ├── app/
│   │   ├── main.py            # FastAPI app, POST /api/classify, GET /api/health
│   │   ├── config.py          # loads .env, constants (URL, model, price, timeout)
│   │   ├── questions.py       # the ONLY place the 7 metrics are defined
│   │   ├── jev_client.py      # builds body, calls Zen, times the call, maps errors
│   │   ├── cost.py            # cost from usage, token estimate fallback
│   │   ├── logger.py          # append-only JSONL writer
│   │   └── schemas.py         # Pydantic models
│   ├── scripts/smoke.py       # one real call, prints shape and cost, never the key
│   └── tests/
└── frontend/
    ├── .npmrc                 # save-exact, ignore-scripts
    ├── package-lock.json      # committed
    └── src/ (App, api.ts, types.ts, components/, styles.css)
```

## Phase 0: Verify the API shape (gate)
Nothing else is built on assumptions until this passes.

**Task 0.1: Prerequisites**
- You confirm a funded Zen account exists and create `.env` with `ZEN_API_KEY=...` at the project root.
- I only check that the file exists, never its contents.
- Done when: `.env` exists.

**Task 0.2: Scaffold `backend/` and the smoke script**
- Check `uv --version` and the uv docs for the `exclude-newer` syntax (relative `"7 days"` if supported, otherwise an absolute timestamp with a README note to bump it).
- `uv init`, then set `[tool.uv]` in `backend/pyproject.toml` (`exclude-newer`, `no-build = true`) **before adding any package**.
- Add `fastapi`, `uvicorn`, `httpx`, `python-dotenv`, `pydantic`. Dev: `pytest`, `respx`.
- Confirm `uv.lock` was created and that every resolved package is at least 7 days old. Spot-check the upload dates in the lock file. If the index gives no upload time, stop and tell you.
- Add `.gitignore` and `.env.example`. `uv.lock` is not ignored.
- `scripts/smoke.py` loads the key, sends the PRD example text with a minimal 3-question body, and prints: HTTP status, top-level response keys, whether `usage` exists and the elapsed ms. It never prints the key or headers.
- Done when: you run it (`! cd backend && uv run python scripts/smoke.py`) and the output confirms the shape.

**Task 0.3: Record the result**
- Update the "Access" and "Risks" sections of `PRD.md` with what the real API returned.
- If the shape differs (body fields, `usage` missing, different model string), stop and adjust the plan with you before Phase 1.
- Done when: the PRD assumptions are confirmed or corrected.

## Phase 1: Backend core (pure logic, unit-tested)
**Task 1.1: `questions.py` and `schemas.py`**
- Define the 7 metrics exactly as in the PRD, with one-line criteria per option, and a `build_request(text)` function returning the body.
- Pydantic models: `JevRequest`, `JevResponse` (answers, usage optional), `ClassifyResult`.
- Tests: the body has exactly 7 question ids with the right types and options, `model` is `jev-1.13`, `state` equals the input.
- Done when: tests pass.

**Task 1.2: `cost.py`**
- `compute_cost(usage, request_body) -> (cost_usd, estimated)`.
- Tests: 392 input tokens gives `392 / 1e6 * 0.042`; missing usage gives an estimate with `estimated=True`; output tokens never change the cost; zero tokens gives 0.
- Done when: tests pass.

**Task 1.3: `jev_client.py`**
- `call_jev(body) -> (response, latency_ms)` using `httpx` with a 30 s timeout.
- Error mapping to typed exceptions: 401/403 (bad key), 402 or credit-related (no credit), 429 (rate limit), timeout, other non-2xx, invalid JSON or missing `answers` (malformed).
- The Authorization header is built inside this module only.
- Tests with `respx`: success, each error case, and that latency is measured on failures too.
- Done when: tests pass and no test touches the network.

**Task 1.4: `logger.py`**
- `append_entry(entry)` writes one JSON line to the project-root `log.jsonl` under a lock.
- Entry fields: `timestamp`, `input_text`, `request`, `response`, `cost_usd`, `cost_estimated`, `latency_ms`, `status` (`ok` or `error`), `error`.
- Tests: one line per call, valid JSON per line, error entries recorded, and a scan confirming the key value never appears in the file (use a fake key).
- Done when: tests pass.

## Phase 2: API layer
**Task 2.1: `POST /api/classify` and `GET /api/health`**
- Input: `{"text": str}`; empty or whitespace-only gives 422, and very long text (over 5000 chars) gives 422.
- Flow: build body, time the call, compute cost, log, return `{answers, cost_usd, cost_estimated, latency_ms, raw_response, model}`.
- On any Jev error: log the failed attempt with its latency, return the error contract with a suitable status.
- Tests with `TestClient` and a mocked Jev: happy path, each error path, and that a log line is written in every case.
- Done when: tests pass and `uv run uvicorn app.main:app` serves it.

**Task 2.2: Live check**
- With the real key, run the server and POST the PRD example with curl.
- Done when: the response has 7 answers, a plausible cost and a latency, and `log.jsonl` has the entry. You run this one, since it uses your key and credit.

## Phase 3: Frontend
**Task 3.1: Scaffold and proxy**
- Before installing anything, create `frontend/.npmrc` with `save-exact=true` and `ignore-scripts=true`. Check the npm docs for a native minimum-release-age setting and add it if it exists.
- Vite + React + TS in `frontend/`, dev proxy `/api` to `localhost:8000`, typed `api.ts` and `types.ts` matching the API contract.
- Only React, React DOM, Vite, TypeScript and their type and plugin packages. For each package, confirm the resolved version was published at least 7 days ago (`npm view <pkg> time`) and pin it exactly. If the latest is too new, pin the newest version that is old enough.
- Confirm `package-lock.json` exists and is committed, then re-install with `npm ci`.
- List any installed package that declares an install script and report it to you.
- Done when: `npm run dev` shows the page and a health call works through the proxy.

**Task 3.2: Input and submit flow**
- Textarea, a Submit button (disabled while empty or loading), a loading state and a sample-text button using the PRD example.
- Done when: submitting calls the API and the raw result can be seen.

**Task 3.3: Result cards**
- One card per metric.
  - Choice: winning label, confidence and probability bars sorted descending.
  - Score: value, the matching legend text, confidence and bars per level.
  - Noul: yes/no lean plus the probability as a bar.
- Cards are ordered as in the PRD table.
- Done when: the live example renders all 7 cards correctly.

**Task 3.4: Summary bar, raw JSON and errors**
- The summary bar shows cost (6 decimals, with an "estimated" tag when flagged), latency in ms and the model.
- A collapsible raw JSON view.
- An error banner with the message from the error contract; the previous result clears on a new submit.
- Done when: each PRD error case shows a clear message. Check manually by temporarily using a bad key or stopping the backend.

## Phase 4: Docs and wrap-up
**Task 4.1: Commands and README**
- Fill in the Commands section of `CLAUDE.md` and add a short README: setup, `.env`, run backend, run frontend, run tests, smoke script.
- Done when: a fresh checkout can follow it start to finish.

**Task 4.2: Dependency audit**
- Backend: `uv sync --locked` succeeds, `uv.lock` is committed, and an audit tool (`pip-audit` run through `uv run --with`, or `uv audit` if available) reports no known vulnerabilities. Any tool I run this way is also subject to the 7-day rule.
- Frontend: `npm ci` succeeds, `package.json` has no `^` or `~`, `.npmrc` has `save-exact` and `ignore-scripts`, and `npm audit` reports nothing at high severity or above.
- List every direct dependency with its version and publish date in the README.
- Document the upgrade procedure in the README: `uv lock --upgrade` or `npm update`, review the lockfile diff, run the tests.
- Done when: both audits are clean, or each finding is explained to you.

**Task 4.3: Final review against the PRD**
- Walk the success criteria one by one and record the result.
- Run `uv run pytest` and confirm the log and `.gitignore` are correct.
- Done when: every success criterion is checked.

## Dependencies
- 0.1 unblocks 0.2 (live run) and 2.2.
- 0.3 blocks Phase 1.
- 1.1 blocks 1.3 (bodies) and 2.1.
- 1.2, 1.3 and 1.4 are independent of each other, and all block 2.1.
- 2.1 blocks 3.x (contract), and 3.1 can start once the contract is stable.

## Risks and mitigations
| Risk | Mitigation |
|---|---|
| Zen body or response differs from TypeSafe's | Phase 0 gate |
| No `usage` in the response | Token estimate, flagged in the log and UI |
| Free or low credit runs out mid-test | Error mapping for it and a clear UI message; the smoke script and manual tests use few calls |
| Key leaks into logs or the browser | The key is only read in `jev_client.py`, tests assert it is absent from the log, and `.gitignore` covers `.env` and `log.jsonl` |
| Cost looks like $0.00 | Show 6 decimals and keep the full float in the log |
| Log contains the user's input text | It is local and git-ignored; noted in the README |
| A compromised release enters through a dependency | 7-day age rule, exact locked versions with hashes, wheels only, no install scripts, minimal dependency list |
| A malicious package stays undetected for over 7 days | Not fully covered. Audits in Task 4.2 and a deliberate upgrade process reduce it. The residual risk is accepted. |
| The index gives no upload time, so the age rule silently does nothing | Task 0.2 spot-checks dates in the lockfile |
| `exclude-newer` blocks an urgent patch | Per-package exception with your approval and a README note |

## Answered questions
1. `httpx` plus `respx` for HTTP and mocking: approved.
2. Frontend language: TypeScript.
3. Git: the repo is initialised (`main`) and `.gitignore` exists. Commit after each task.

## Final review against the PRD (2026-09-26)
| Success criterion | Result | Evidence |
|---|---|---|
| Paste a message, get classifications in one click | Met, but not yet viewed in a real browser by me | Live API call succeeded, the cards render correctly from a real response, and the submit flow builds. You tested the page yourself. |
| Every result shows cost and latency | Met | Summary bar shows cost to 6 decimals (with an "estimated" tag when flagged), latency and model. |
| Every request/response appended to `log.jsonl` with cost and latency | Met | 9 entries at review time, all with `cost_usd` and `latency_ms`. |
| Failed calls shown clearly and logged | Met | A fake key showed "Zen rejected the API key" and was logged with upstream 401, latency and no cost. A stopped backend shows "Could not reach the backend". |
| One documented command per server | Met | README and `CLAUDE.md`. |
| `pytest` passes against a mocked Jev API | Met | 57 passed. |
| Dependency rules (7-day age, locked, exact, no install scripts) | Met | 68 npm packages and 92 Python file uploads checked against the cutoff. `pip-audit` and `npm audit` are clean. |

Open item: `latency_ms` is 1.2 to 1.9 s, above the low hundreds of ms expected from Jev's own metrics. It measures the full round trip through Zen, not model time. See the README "Latency" section and `backend/scripts/latency_probe.py`.
