"""
Stage 5: Budget Allocator.

Dynamically computes token budgets based on cost and latency signals.
Adapts dynamically to the input context size:
- Low pressure (0.0): Retains ~85-90% of tokens (maximum reasoning fidelity)
- Balanced (0.5): Retains ~50% of tokens
- High pressure (1.0): Compresses to ~25-30% of original tokens
"""
from typing import Optional

MIN_ABSOLUTE_BUDGET = 250
DEFAULT_MAX_BUDGET = 3500


def allocate_budget(
    cost_pressure: float = 0.5,
    latency_pressure: float = 0.5,
    context_tokens: Optional[int] = None
) -> int:
    """
    Computes token budget ceiling.
    Args:
        cost_pressure: Float in [0.0, 1.0] representing cost sensitivity.
        latency_pressure: Float in [0.0, 1.0] representing latency sensitivity.
        context_tokens: Total token count of original context.
    Returns:
        Integer token budget limit.
    """
    pressure = max(0.0, min(1.0, max(cost_pressure, latency_pressure)))

    if context_tokens and context_tokens > MIN_ABSOLUTE_BUDGET:
        # Retention ratio maps from 0.85 (pressure 0.0) down to 0.25 (pressure 1.0)
        retention_ratio = 0.85 - pressure * (0.85 - 0.25)
        budget = int(context_tokens * retention_ratio)
        return max(MIN_ABSOLUTE_BUDGET, budget)

    budget = DEFAULT_MAX_BUDGET - pressure * (DEFAULT_MAX_BUDGET - MIN_ABSOLUTE_BUDGET)
    return int(max(MIN_ABSOLUTE_BUDGET, budget))
