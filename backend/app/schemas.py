from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class Usage(BaseModel):
    input_tokens: int
    output_tokens: int = 0


class ChoiceAnswer(BaseModel):
    type: Literal["choice"]
    choice: str
    confidence: float
    probabilities: dict[str, float]


class ScoreAnswer(BaseModel):
    type: Literal["score"]
    score: float
    confidence: float
    legend: dict[str, str]
    probabilities: dict[str, float]


class NoulAnswer(BaseModel):
    type: Literal["noul"]
    noul: float


Answer = Annotated[
    ChoiceAnswer | ScoreAnswer | NoulAnswer, Field(discriminator="type")
]


class JevResponse(BaseModel):
    """A validated /systemone response. Extra fields are ignored."""

    model: str
    answers: dict[str, Answer]
    usage: Usage | None = None


class ClassifyRequest(BaseModel):
    text: str


class ClassifyResult(BaseModel):
    model: str
    answers: dict[str, Answer]
    cost_usd: float
    cost_estimated: bool
    latency_ms: float
    raw_response: dict[str, Any]
