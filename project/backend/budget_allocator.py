"""
Stage 5: Budget Allocator.
Decides how many tokens we can afford based on UI sliders.
"""

def allocate_budget(cost_pressure: float = 0.5, latency_pressure: float = 0.5) -> int:
    """
    Returns total token budget based on UI pressure sliders.
    Matches realistic deployment tiers for context window targeting,
    while hard-clamping to a baseline minimum so a 100% pressure slider 
    doesn't break the UI on stage with an empty prompt.
    """
    # Integrate both sliders so nothing is dead on the UI
    combined_pressure = (cost_pressure + latency_pressure) / 2.0
    
    scaled_budget = int((1.0 - combined_pressure) * 2000)
    
    # Hard floor of 150 ensures the system always degrades gracefully during extreme tests
    return max(150, scaled_budget)
