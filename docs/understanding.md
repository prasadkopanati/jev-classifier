# JEV Getting Started: My Understanding

Status: DRAFT. Open questions are listed at the bottom. No code will be written until all are answered.

## Goal
A small evaluation app for the Jev model. A user types a free-text customer query. The app asks Jev to classify it on several metrics, then shows the results, the cost and the latency on the same page. Every request/response pair is logged.

## What Jev is (from docs.typesafe.ai)
- TypeSafe's "System One" model. It is a classifier, not a text generator.
- You send one `state` (arbitrary JSON) plus a dict of typed questions. Each question is evaluated independently and in parallel against the same state.
- Three question primitives:

| Primitive | Meaning | Returns |
|---|---|---|
| Choice | Pick one of the labeled options | `choice`, `probabilities`, `confidence` |
| Score | Rate against an ordered rubric | `score` (float), `legend`, `probabilities`, `confidence` |
| Noul | Is this statement true? | `noul` (0-1) |

- Each question has an ID (our key), a `type`, `instructions` and `criteria` (required for Choice and Score, optional for Noul).
- Instructions refer to state fields with backticks, e.g. `` `ticket_message` ``.
- The docs recommend atomic questions, one per metric, combined in our code.
- Note: the brief lists "State", "Choices", "NOUL", "Score" as primitives. The docs treat State as the input and Choice, Score and Noul as the question types. I will follow the docs.

## How we access it (from opencode.ai/docs/zen)
- Base URL `https://opencode.ai/zen/v1/`, Bearer auth with a Zen API key.
- Jev has its own endpoint: `POST https://opencode.ai/zen/v1/systemone`.
- Models: `jev-1.13` (paid) and `jev-1.13-free`.
- Pricing: input $0.042 per 1M tokens, output free.
- The TypeSafe quickstart shows the raw HTTP shape for its own endpoint (`POST https://api.typesafe.ai/v1/systemone`). I assume the Zen endpoint takes the same body. This is unverified until a live call is made.
  - Request: `{"model": "...", "state": <string or object>, "questions": {"<id>": {"type": "choice|score|noul", "instructions": "...", "criteria": {...} | [...]}}}`
  - Response: `{"model": "jev-1.13.0", "answers": {"<id>": {"type": ..., ...}}, "usage": {"input_tokens": N, "output_tokens": M}}`
  - The `usage` field is what cost will be computed from: `input_tokens / 1e6 * 0.042`, with output free.

## Proposed shape (not final)
- Backend: Python 3.x, FastAPI, managed with `uv`. It has one endpoint that receives the text and builds the Jev request (state + questions). It calls `/systemone` with `jev-1.13`, times the call, computes cost, appends to the log and returns everything to the UI.
- Frontend: React (Vite). It has a text box, a Submit button and a results panel showing intent, urgency, handling department, cost and latency.
- Logging: a file at the project root with one entry per request holding the input, the raw response, cost and latency.

## Requirements as I read them
Functional
1. The user types a classification query in a web page.
2. The backend calls Jev with a JSON object built from that input.
3. The response is shown on the same page.
4. The page shows the cost and processing time of the request.

Non-functional
1. Log requests and responses to a file at the project root.
2. Record cost and latency for each request/response pair in that log.

## Decisions (all confirmed by the user)
| Area | Decision |
|---|---|
| Metrics | Fixed in code. The user only types the query text. |
| Primitives | Choice, Score and Noul are all used. |
| Intent (Choice) | Small generic set: `billing`, `technical`, `sales`, `general_inquiry`, `complaint`. |
| Department (Choice) | Minimal set: `billing`, `technical`, `sales`. |
| Urgency | Noul only: `is_urgent`. |
| Extra Noul checks | `refund_requested`, `wants_human`, `churn_risk`. |
| Extra Score | `frustration`, 3 levels: calm, frustrated but civil, very angry. |
| Model | `jev-1.13` only, no switcher. |
| API key | `ZEN_API_KEY` in a git-ignored `.env`. The user creates it. It is never entered in the UI or logged. |
| Cost | `usage.input_tokens / 1e6 * 0.042`, output free. If `usage` is missing, estimate the tokens locally and flag the cost as estimated. |
| Latency | Backend-measured round trip of the Jev call only. |
| Log | `log.jsonl` at the project root. One JSON line per request with timestamp, request, response, cost, latency and status. |
| History | Current result only on the page. History lives in the log. |
| Errors | Show a clear message on the page. Log the failed attempt with its latency. No retries. |
| Layout | `backend/` (uv, FastAPI) and `frontend/` (Vite + React, dev proxy to the API). Log at the root. |
| Results UI | Cards per metric with label, confidence and probability bars. A cost/latency summary bar. A collapsible raw JSON view. |
| Testing | pytest backend unit tests with a mocked Jev API (request building, cost, logging), plus a manual live smoke script. |

## Assumption to verify first
- The Zen `/systemone` endpoint accepts the same body as `api.typesafe.ai/v1/systemone` and returns `usage`. I cannot check this without a key. Once the key exists, my first step will be a single curl call to confirm the shape before I build on it. If it differs, I will adjust and tell you.

## Next
Once you approve this understanding, I will write an implementation plan and then build it.
