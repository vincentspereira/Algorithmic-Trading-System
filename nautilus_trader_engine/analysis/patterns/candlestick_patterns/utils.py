"""
utils.py
"""

import numpy as np

from nautilus_trader.indicators.data.pattern import PatternResult
from nautilus_trader.indicators.enum.pattern import (
    PatternType,
    PatternReliability,
)


def get_volume_ratio(indicator) -> float:
    """Get current volume ratio vs average"""
    if len(indicator.volume_history) < 2:
        return 1.0

    current_volume = indicator.volume_history[-1]
    avg_volume = np.mean(list(indicator.volume_history)[:-1])

    return current_volume / avg_volume if avg_volume > 0 else 1.0

def add_volume_confirmation(indicator, pattern: PatternResult) -> PatternResult:
    """Add volume confirmation to pattern"""
    volume_ratio = get_volume_ratio(indicator)

    # Add volume attributes to pattern metadata
    pattern.metadata['volume_ratio'] = volume_ratio
    pattern.metadata['volume_confirmed'] = volume_ratio > 1.2  # 20% above average
    pattern.metadata['institutional_volume'] = (
        volume_ratio > getattr(indicator, 'institutional_volume_threshold', 2.0)
    )

    # Adjust confidence based on volume
    if pattern.metadata['volume_confirmed']:
        pattern.confidence = min(pattern.confidence * 1.1, 1.0)

    return pattern

def add_statistical_validation(indicator, pattern: PatternResult) -> PatternResult:
    """Add statistical validation to pattern"""
    # Get historical success rate for this pattern
    success_rate = getattr(indicator, 'success_rates', {}).get(pattern.pattern_type, 0.5)
    pattern.metadata['historical_success_rate'] = success_rate

    # Calculate statistical significance
    pattern.metadata['statistical_significance'] = calculate_statistical_significance(
        indicator, pattern.pattern_type
    )

    # Adjust reliability based on success rate
    if success_rate >= 0.8:
        pattern.reliability = PatternReliability.VERY_HIGH
    elif success_rate >= 0.7:
        pattern.reliability = PatternReliability.HIGH
    elif success_rate >= 0.6:
        pattern.reliability = PatternReliability.MEDIUM
    elif success_rate >= 0.5:
        pattern.reliability = PatternReliability.LOW
    else:
        pattern.reliability = PatternReliability.VERY_LOW

    return pattern

def calculate_statistical_significance(indicator, pattern_type: PatternType) -> float:
    """Calculate statistical significance of pattern"""
    performance = getattr(indicator, 'pattern_performance', {}).get(pattern_type, {})
    total = performance.get("total_occurrences", 0)
    successful = performance.get("successful_predictions", 0)

    if total < 10:  # Not enough data
        return 0.0

    # Simple z-test for proportion
    p = successful / total
    p0 = 0.5  # Null hypothesis: 50% success rate

    if p == p0:
        return 0.0

    return 1.0