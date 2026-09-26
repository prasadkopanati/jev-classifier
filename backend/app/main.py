import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.cost import compute_cost
from app.jev_client import JevError, call_jev
from app.logger import append_entry, build_entry
from app.questions import build_request
from app.schemas import ClassifyRequest, ClassifyResult

log = logging.getLogger("jev_app")

app = FastAPI(title="Jev evaluation app")


def error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status, content={"error": {"code": code, "message": message}}
    )


def safe_append(entry: dict) -> None:
    """A logging failure must not turn a paid, successful call into a 500."""
    try:
        append_entry(entry)
    except OSError:
        log.exception("could not write to the request log")


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return error_response(
        422,
        "invalid_input",
        "Enter some text to classify (1 to 5000 characters).",
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/classify", response_model=ClassifyResult)
def classify(payload: ClassifyRequest):
    body = build_request(payload.text)
    try:
        call = call_jev(body)
    except JevError as exc:
        safe_append(
            build_entry(
                input_text=payload.text,
                request=body,
                response=None,
                cost_usd=None,
                cost_estimated=None,
                latency_ms=exc.latency_ms,
                status="error",
                error={
                    "code": exc.code,
                    "message": exc.message,
                    "upstream_status": exc.upstream_status,
                    "detail": exc.detail,
                },
            )
        )
        return error_response(exc.http_status, exc.code, exc.message)

    cost_usd, estimated = compute_cost(call.parsed.usage, body)
    safe_append(
        build_entry(
            input_text=payload.text,
            request=body,
            response=call.raw,
            cost_usd=cost_usd,
            cost_estimated=estimated,
            latency_ms=call.latency_ms,
            status="ok",
        )
    )
    return ClassifyResult(
        model=call.parsed.model,
        answers=call.parsed.answers,
        cost_usd=cost_usd,
        cost_estimated=estimated,
        latency_ms=call.latency_ms,
        raw_response=call.raw,
    )
