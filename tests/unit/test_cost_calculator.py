"""Unit tests for usage cost estimation."""

from decimal import Decimal

from app.modules.usage.cost_calculator import estimate_cost_usd


def test_estimate_cost_usd_for_embedding_tokens() -> None:
    cost = estimate_cost_usd(
        provider="openai",
        model="text-embedding-3-small",
        embedding_tokens=1000,
    )

    assert cost == Decimal("0.000020")


def test_estimate_cost_usd_for_llm_completion_tokens() -> None:
    cost = estimate_cost_usd(
        provider="openai",
        model="gpt-4o-mini",
        prompt_tokens=800,
        completion_tokens=200,
    )

    # 1000 tokens * $0.00015 / 1K = $0.00015
    assert cost == Decimal("0.000150")


def test_estimate_cost_usd_quantizes_to_six_decimal_places() -> None:
    cost = estimate_cost_usd(
        provider="openai",
        model="text-embedding-3-small",
        embedding_tokens=1,
    )

    assert cost == Decimal("0.000000")
    assert str(cost) == "0.000000"


def test_estimate_cost_usd_returns_none_for_unknown_model() -> None:
    cost = estimate_cost_usd(
        provider="openai",
        model="unknown-model",
        embedding_tokens=1000,
    )

    assert cost is None


def test_estimate_cost_usd_returns_none_for_unknown_provider() -> None:
    cost = estimate_cost_usd(
        provider="unknown",
        model="gpt-4o-mini",
        prompt_tokens=100,
    )

    assert cost is None


def test_estimate_cost_usd_zero_tokens_returns_zero() -> None:
    cost = estimate_cost_usd(
        provider="openai",
        model="text-embedding-3-small",
    )

    assert cost == Decimal("0.000000")
