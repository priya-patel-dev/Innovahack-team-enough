"""
Stage 5: Budget Allocator.

Decides how many tokens the compressed prompt is allowed to use. In a
real system this would react to live cost/latency signals; for the
hackathon demo, expose it as a slider in the dashboard so judges can
see compression react live ("cost-aware adaptive compression").

Budget curve (no damping — pressure maps directly to token ceiling):
  pressure=0.0  → MAX_BUDGET (generous, minimal compression)
  pressure=0.50 → ~1750 tokens  (balanced: ~45% compression on large files)
  pressure=0.90 → ~570 tokens   (aggressive: ~65-70% compression)
  pressure=1.0  → MIN_BUDGET    (maximum: forces maximum node dropping)
"""

DEFAULT_BUDGET = 3000
MIN_BUDGET = 300
MAX_BUDGET = 3300


def allocate_budget(cost_pressure: float = 0.5, latency_pressure: float = 0.5) -> int:
    """
    cost_pressure / latency_pressure: 0.0 (no pressure, be generous)
    to 1.0 (high pressure, compress aggressively). In the demo these
    are wired to a UI slider; in a real deployment they'd come from
    live API cost tracking / p99 latency monitoring.
    """
    pressure = max(cost_pressure, latency_pressure)  # no damping — real pressure
    budget = MAX_BUDGET - pressure * (MAX_BUDGET - MIN_BUDGET)
    return int(max(MIN_BUDGET, min(MAX_BUDGET, budget)))
