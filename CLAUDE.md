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
- Age rule: never install a version published less than 7 days ago. Python is enforced by `exclude-newer` in `backend/pyproject.toml`. For npm, check publish dates with `npm view <pkg> time` before installing, unless a native minimum-release-age setting is confirmed and configured.
- Python: `no-build = true` (wheels only, no source builds). Keep `uv.lock` committed.
- npm: `.npmrc` has `save-exact=true` and `ignore-scripts=true`. Keep `package-lock.json` committed. No `^` or `~` ranges in `package.json`.
- Install from the lockfiles: `uv sync --locked` and `npm ci`. If a lockfile is out of date, stop and ask.
- Upgrades are deliberate. Do not run `uv lock --upgrade` or `npm update` without asking. Show the lockfile diff and run the tests afterwards.
- After adding an npm package, check whether it declares install scripts (`preinstall`, `install`, `postinstall`) and tell the user. An unexpected script is a red flag.
- Keep the dependency list minimal. Ask before adding any package not named in `PLAN.md`.
- Exception for an urgent security patch: only with the user's explicit approval, per package (`exclude-newer-package` for Python), with the reason noted in the README.

## Commands (fill in as the project is built)
- Backend: `cd backend && uv run fastapi dev`
- Frontend: `cd frontend && npm run dev`
- Tests: `cd backend && uv run pytest`
- Smoke check: `cd backend && uv run python scripts/smoke.py`
