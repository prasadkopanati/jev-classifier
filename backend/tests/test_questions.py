import pytest
from pydantic import ValidationError

from app.questions import QUESTIONS, build_request
from app.schemas import JevResponse

EXPECTED_TYPES = {
    "intent": "choice",
    "department": "choice",
    "frustration": "score",
    "is_urgent": "noul",
    "refund_requested": "noul",
    "wants_human": "noul",
    "churn_risk": "noul",
}


def test_body_has_the_seven_questions_in_prd_order():
    body = build_request("hello")
    assert list(body["questions"]) == list(EXPECTED_TYPES)
    for qid, qtype in EXPECTED_TYPES.items():
        assert body["questions"][qid]["type"] == qtype
        assert body["questions"][qid]["instructions"]


def test_model_and_state():
    body = build_request("I was billed twice")
    assert body["model"] == "jev-1.13"
    assert body["state"] == "I was billed twice"


def test_choice_options():
    q = build_request("x")["questions"]
    assert set(q["intent"]["criteria"]) == {
        "billing", "technical", "sales", "general_inquiry", "complaint",
    }
    assert set(q["department"]["criteria"]) == {"billing", "technical", "sales"}
    assert all(q["intent"]["criteria"].values())


def test_score_has_three_levels_and_noul_has_no_criteria():
    q = build_request("x")["questions"]
    assert len(q["frustration"]["criteria"]) == 3
    for qid in ("is_urgent", "refund_requested", "wants_human", "churn_risk"):
        assert "criteria" not in q[qid]


def test_build_request_does_not_share_state_between_calls():
    body = build_request("a")
    body["questions"]["intent"]["criteria"].clear()
    assert QUESTIONS["intent"]["criteria"]
    assert build_request("b")["questions"]["intent"]["criteria"]


SAMPLE = {
    "model": "jev-1.13",
    "answers": {
        "department": {
            "type": "choice",
            "choice": "billing",
            "confidence": 0.9,
            "probabilities": {"billing": 0.95, "technical": 0.05},
        },
        "frustration": {
            "type": "score",
            "score": 1.0,
            "confidence": 1.0,
            "legend": {"0": "Calm", "1": "Frustrated"},
            "probabilities": {"0": 0.0, "1": 1.0},
        },
        "is_urgent": {"type": "noul", "noul": 1.0},
    },
    "usage": {"input_tokens": 414, "output_tokens": 73},
}


def test_response_parses_all_three_answer_types():
    resp = JevResponse.model_validate(SAMPLE)
    assert resp.answers["department"].choice == "billing"
    assert resp.answers["frustration"].score == 1.0
    assert resp.answers["is_urgent"].noul == 1.0
    assert resp.usage.input_tokens == 414


def test_response_usage_is_optional():
    resp = JevResponse.model_validate({k: v for k, v in SAMPLE.items() if k != "usage"})
    assert resp.usage is None


@pytest.mark.parametrize("missing", ["answers", "model"])
def test_response_missing_required_field_is_invalid(missing):
    bad = {k: v for k, v in SAMPLE.items() if k != missing}
    with pytest.raises(ValidationError):
        JevResponse.model_validate(bad)


def test_response_unknown_answer_type_is_invalid():
    bad = {**SAMPLE, "answers": {"x": {"type": "mystery", "value": 1}}}
    with pytest.raises(ValidationError):
        JevResponse.model_validate(bad)
