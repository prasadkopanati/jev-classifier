import pytest

from app.cost import compute_cost, estimate_input_tokens
from app.schemas import Usage

BODY = {"model": "jev-1.13", "state": "hello", "questions": {}}


def test_cost_from_input_tokens():
    cost, estimated = compute_cost(Usage(input_tokens=392, output_tokens=65), BODY)
    assert cost == pytest.approx(392 / 1e6 * 0.042)
    assert estimated is False


def test_output_tokens_do_not_change_cost():
    low, _ = compute_cost(Usage(input_tokens=100, output_tokens=0), BODY)
    high, _ = compute_cost(Usage(input_tokens=100, output_tokens=100_000), BODY)
    assert low == high


def test_zero_tokens_costs_nothing():
    cost, estimated = compute_cost(Usage(input_tokens=0, output_tokens=0), BODY)
    assert cost == 0
    assert estimated is False


def test_missing_usage_falls_back_to_flagged_estimate():
    cost, estimated = compute_cost(None, BODY)
    assert estimated is True
    assert cost == pytest.approx(estimate_input_tokens(BODY) / 1e6 * 0.042)
    assert cost > 0


def test_estimate_grows_with_request_size():
    small = estimate_input_tokens(BODY)
    big = estimate_input_tokens({**BODY, "state": "x" * 4000})
    assert big > small
