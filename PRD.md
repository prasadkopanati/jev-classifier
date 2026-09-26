# Jev Evaluation App: PRD

## Purpose
Learn how Jev (TypeSafe's classification-only "System One" model) behaves on customer-support text: what it returns, what it costs and how fast it is.

Audience: the author, i.e. myself. This is a personal project that runs locally.

## Success criteria
- I will paste a support message into a web page and get structured classifications in one click.
- Every result shows its cost (USD) and latency (ms).
- Every request/response pair is appended to `log.jsonl` at the project root, with cost and latency.
- Failed calls are shown clearly on the page and logged too.
- One documented command starts the backend and one starts the frontend.
- `pytest` passes against a mocked Jev API.

## Jev in brief
- Jev is not a text generator. Users send one `state` plus named typed questions. It answers each question independently and in parallel against that state.
- Question types:

| Type | Question | Returns |
|---|---|---|
| Choice | Which of these options? | `choice`, `probabilities`, `confidence` |
| Score | Which level of this rubric? | `score`, `legend`, `probabilities`, `confidence` |
| Noul | Is this statement true? | `noul` (0 to 1) |

- Docs: https://docs.typesafe.ai/llms.txt (page index), https://docs.typesafe.ai/introduction/quickstart.md (raw HTTP example)

## Access
- Provider: opencode.ai Zen.
- Endpoint: `POST https://opencode.ai/zen/v1/systemone`.
- Auth: `Authorization: Bearer $ZEN_API_KEY`. The key lives in a git-ignored `.env` and is never logged or sent to the browser.
- Model: `jev-1.13`.
- Price: $0.042 per 1M input tokens, output free.
- Request body (from the TypeSafe quickstart, to be verified against Zen):
  ```json
  {
    "model": "jev-1.13",
    "state": "<the user's text>",
    "questions": {
      "<id>": {"type": "choice|score|noul", "instructions": "...", "criteria": {} }
    }
  }
  ```
- Response: `{"model", "answers": {"<id>": {...}}, "usage": {"input_tokens", "output_tokens"}}`.

## Metrics (fixed in code)
The user only types the query text. The questions are hardcoded in the backend.

| id | type | options / rubric |
|---|---|---|
| `intent` | choice | `billing`, `technical`, `sales`, `general_inquiry`, `complaint` |
| `department` | choice | `billing`, `technical`, `sales` |
| `frustration` | score | 0 calm, 1 frustrated but civil, 2 very angry |
| `is_urgent` | noul | The message conveys urgency or time-sensitivity |
| `refund_requested` | noul | The customer asks for money back or a charge reversal |
| `wants_human` | noul | The customer asks for a human agent or escalation |
| `churn_risk` | noul | The customer threatens to cancel or leave |

Each option gets a one-line definition in `criteria`. Instructions refer to the state by name where the state is an object.

Example input: "I have been billed twice for the subscription and I want to review the charge and reverse it asap"

## Functional requirements
1. A web page with a text box and a Submit button.
2. Submit sends the text to the backend. The backend builds the Jev request and calls `/systemone`.
3. The page shows one card per metric with the winning label or value, the confidence and a probability breakdown for Choice and Score.
4. The page shows a summary bar with cost and latency, and a collapsible raw JSON view.
5. The page shows only the latest result. History lives in the log.
6. Errors (bad key, no credit, timeout, malformed response) show a clear message. There are no automatic retries.

## Non-functional requirements
1. Log each request to `log.jsonl` at the project root, one JSON object per line: timestamp, input text, request body, response body, cost, latency, status and error if any. The API key is never written.
2. Cost is computed from the response: `usage.input_tokens / 10^6 * 0.042`. If `usage` is missing, estimate the tokens locally and mark the cost as estimated.
3. Latency is the backend round trip of the Jev call only, in milliseconds.
4. Backend unit tests use a mocked Jev API and cover request building, cost calculation and logging.
5. A manual smoke script makes one real call.

## Out of scope (this version)
- Authentication, user accounts, deployment and hosting.
- A model switcher or other models. Only `jev-1.13` is used.
- Editing metrics in the UI.
- History in the UI, retries and frontend tests.
- Accuracy benchmarking against labeled data.

## Risks and open items
- **Zen body compatibility.** Assumed to match TypeSafe's raw API. Verify with one curl call before building on it.
- **Funded account.** A Zen account with credit and an API key must exist before live testing. The user creates `.env` with `ZEN_API_KEY`.
- **Missing `usage`.** If Zen omits it, the token estimate is used and flagged in the UI and log.
