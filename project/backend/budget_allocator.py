"""
Stage 5: Budget Allocator.

Decides how many tokens the compressed prompt is allowed to use. In a
real system this would react to live cost/latency signals; for the
hackathon demo, expose it as a slider in the dashboard so judges can
see compression react live ("cost-aware adaptive compression").
"""
DEFAULT_BUDGET = 2000
MIN_BUDGET = 300
MAX_BUDGET = 8000


def allocate_budget(cost_pressure: float = 0.5, latency_pressure: float = 0.5) -> int:
    """
    cost_pressure / latency_pressure: 0.0 (no pressure, be generous)
    to 1.0 (high pressure, compress aggressively). In the demo these
    are wired to a UI slider; in a real deployment they'd come from
    live API cost tracking / p99 latency monitoring.
    """
    pressure = max(cost_pressure, latency_pressure)
    budget = MAX_BUDGET - pressure * (MAX_BUDGET - MIN_BUDGET)
    return int(max(MIN_BUDGET, min(MAX_BUDGET, budget)))
