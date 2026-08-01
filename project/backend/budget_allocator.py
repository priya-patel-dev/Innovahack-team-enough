"""
Stage 5: Budget Allocator.
Decides how many tokens we can afford based on UI sliders.
"""

def allocate_budget(cost_pressure: float = 0.5, latency_pressure: float = 0.5) -> int:
    """
    Returns total token budget based on UI pressure sliders.
    Lowered multiplier to 150 so small hackathon files exceed the budget 
    and actually trigger the Recovery Index logic.
    """
    return int((1.0 - cost_pressure) * 150)
