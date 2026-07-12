"""Unit tests for embedding cost estimation."""

from decimal import Decimal

from app.modules.usage.cost_calculator import estimate_cost_usd


def test_estimate_cost_usd_for_embedding_tokens() -> None:
    cost = estimate_cost_usd(
        provider="openai",
        model="text-embedding-3-small",
        embedding_tokens=1000,
    )

    assert cost == Decimal("0.00002")


def test_estimate_cost_usd_returns_none_for_unknown_model() -> None:
    cost = estimate_cost_usd(
        provider="openai",
        model="unknown-model",
        embedding_tokens=1000,
    )

    assert cost is None


def test_estimate_cost_usd_zero_tokens_returns_zero() -> None:
    cost = estimate_cost_usd(
        provider="openai",
        model="text-embedding-3-small",
    )

    assert cost == Decimal("0")
