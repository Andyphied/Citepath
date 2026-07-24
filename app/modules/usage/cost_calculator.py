"""Static pricing table for estimated AI usage cost.

Estimates are approximate portfolio/demo figures — not invoice-grade billing.
Rates are USD per 1K tokens (single blended rate per model; input/output not
split). Unknown provider/model pairs return ``None`` so callers leave
``estimated_cost_usd`` unset rather than inventing a price.
"""

from decimal import ROUND_HALF_UP, Decimal

# USD per 1K tokens — updated manually when provider rates change (ADR-007).
PRICING_USD_PER_1K_TOKENS: dict[str, dict[str, Decimal]] = {
    "openai": {
        "text-embedding-3-small": Decimal("0.00002"),
        "text-embedding-3-large": Decimal("0.00013"),
        "gpt-4o-mini": Decimal("0.00015"),
        "gpt-4o": Decimal("0.005"),
    },
    "anthropic": {
        "claude-3-5-sonnet-20241022": Decimal("0.003"),
    },
}

_COST_QUANTUM = Decimal("0.000001")


def estimate_cost_usd(
    *,
    provider: str,
    model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    embedding_tokens: int = 0,
) -> Decimal | None:
    """Estimate call cost from the static price table (6 decimal places)."""
    provider_prices = PRICING_USD_PER_1K_TOKENS.get(provider)
    if provider_prices is None:
        return None

    price_per_1k = provider_prices.get(model)
    if price_per_1k is None:
        return None

    total_tokens = prompt_tokens + completion_tokens + embedding_tokens
    if total_tokens <= 0:
        return Decimal("0.000000")

    raw = (Decimal(total_tokens) / Decimal(1000)) * price_per_1k
    return raw.quantize(_COST_QUANTUM, rounding=ROUND_HALF_UP)
