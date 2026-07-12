"""Static pricing table for estimated AI usage cost."""

from decimal import Decimal

# USD per 1K tokens — updated manually when provider rates change.
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


def estimate_cost_usd(
    *,
    provider: str,
    model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    embedding_tokens: int = 0,
) -> Decimal | None:
    """Estimate call cost from the static price table."""
    provider_prices = PRICING_USD_PER_1K_TOKENS.get(provider)
    if provider_prices is None:
        return None

    price_per_1k = provider_prices.get(model)
    if price_per_1k is None:
        return None

    total_tokens = prompt_tokens + completion_tokens + embedding_tokens
    if total_tokens <= 0:
        return Decimal("0")

    return (Decimal(total_tokens) / Decimal(1000)) * price_per_1k
