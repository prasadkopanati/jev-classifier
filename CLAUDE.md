# CLAUDE.md

Read `PRD.md` first. It defines what to build and what is out of scope.

## Stack
- Backend: Python 3.x, FastAPI, managed with `uv` (`uv add`, `uv run`; no pip or requirements.txt). It lives in `backend/`.
- Frontend: React with Vite. It lives in `frontend/` and proxies `/api` to the backend in dev.
- Tests: `pytest` in `backend/tests/`. The Jev API is always mocked in tests.

## Layout
- `backend/` FastAPI app, question definitions, cost and logging code
- `frontend/` React app
- `log.jsonl` request log at the project root (git-ignored)
- `.env` holds `ZEN_API_KEY` (git-ignored, created by the user)

## Rules
- Do not write code until the user has approved the implementation plan.
- Never read, print, log or commit `.env`, the API key or any sensitive information. The key stays in the backend and is never sent to the browser.
- The question definitions live in one backend module. Do not scatter them across files.
- Cost and latency are computed in the backend, not the browser. Definitions are in `PRD.md`.
- Every call to Jev, including failures, is appended to `log.jsonl`.
- Tests must not make real network calls. Real calls go only through the manual smoke script.
- Keep to the scope in `PRD.md`. If something is out of scope, ask before adding it.
- Verify the Zen `/systemone` request and response shape with a real call before relying on the assumptions in `PRD.md`.

## Dependencies (supply chain rules)
- Only add packages through `uv add` (backend) and `npm install --save-exact` (frontend). Never edit lockfiles by hand.
- Age rule: never install a version published less than 7 days ago. Python is enforced by `exclude-newer = "7 days"` in `backend/pyproject.toml`. npm is enforced by the fixed `before=` date in `frontend/.npmrc` (npm 11.8.0 ignores `min-release-age`, so do not rely on it). When upgrading, move `before` to today minus 7 days, and verify publish dates with `npm view <pkg> time`.
- Python: `no-build = true` (wheels only, no source builds). Keep `uv.lock` committed.
- npm: `.npmrc` has `save-exact=true` and `ignore-scripts=true`. Keep `package-lock.json` committed. No `^` or `~` ranges in `package.json`.
- Install from the lockfiles: `uv sync --locked` and `npm ci`. If a lockfile is out of date, stop and ask.
- Upgrades are deliberate. Do not run `uv lock --upgrade` or `npm update` without asking. Show the lockfile diff and run the tests afterwards.
- After adding an npm package, check whether it declares install scripts (`preinstall`, `install`, `postinstall`) and tell the user. An unexpected script is a red flag.
- Keep the dependency list minimal. Ask before adding any package not named in `PLAN.md`.
- Exception for an urgent security patch: only with the user's explicit approval, per package (`exclude-newer-package` for Python), with the reason noted in the README.

## Commands
- Backend: `cd backend && uv run --locked uvicorn app.main:app --reload --port 8000`
- Frontend: `cd frontend && npm run dev` (http://localhost:5173, proxies `/api` to port 8000)
- Backend tests: `cd backend && uv run --locked pytest`
- Frontend typecheck and build: `cd frontend && npm run build`
- Install from lockfiles: `cd backend && uv sync --locked` and `cd frontend && npm ci`
- Smoke check (real call): `cd backend && uv run python scripts/smoke.py`
- Latency probe (10 real calls): `cd backend && uv run python scripts/latency_probe.py`

## Running servers safely
- Any server that reaches the real Jev API spends the user's credit. Only start one when the task needs it, and use no real requests other than the ones the task calls for. The user runs the smoke and latency scripts.
- Stop servers by port, not by wrapper PID: `lsof -ti tcp:8000 -sTCP:LISTEN | xargs kill` (same for 5173). Check with `lsof -nP -iTCP:8000 -iTCP:5173 -sTCP:LISTEN` that the ports are free before starting a server, and again after a test. A stale server on the port silently answers instead of the new one.
- To test error paths without spending credit, use a fake key in the environment (`ZEN_API_KEY=fake ...`) only after confirming the port was free.
