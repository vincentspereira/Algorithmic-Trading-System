"""
utils.py
"""

import numpy as np

from nautilus_trader.indicators.data.pattern import PatternResult
from nautilus_trader.indicators.enum.pattern import (
    PatternType,
    PatternReliability,
)


def get_volume_ratio(self) -> float:
    """Get current volume ratio vs average"""
    if len(self.volume_history) < 2:
        return 1.0

    current_volume = self.volume_history[-1]
    avg_volume = np.mean(list(self.volume_history)[:-1])

    return current_volume / avg_volume if avg_volume > 0 else 1.0

def add_volume_confirmation(self, pattern: PatternResult) -> PatternResult:
    """Add volume confirmation to pattern"""
    volume_ratio = self._get_volume_ratio()

    pattern.volume_ratio = volume_ratio
    pattern.volume_confirmed = volume_ratio > 1.2  # 20% above average
    pattern.institutional_volume = (
        volume_ratio > self.institutional_volume_threshold
    )

    # Adjust confidence based on volume
    if pattern.volume_confirmed:
        pattern.confidence = min(pattern.confidence * 1.1, 1.0)

    return pattern

def add_statistical_validation(self, pattern: PatternResult) -> PatternResult:
    """Add statistical validation to pattern"""
    # Get historical success rate for this pattern
    success_rate = self.success_rates.get(pattern.pattern_type, 0.5)
    pattern.historical_success_rate = success_rate

    # Calculate statistical significance
    pattern.statistical_significance = self._calculate_statistical_significance(
        pattern.pattern_type
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

def calculate_statistical_significance(self, pattern_type: PatternType) -> float:
    """Calculate statistical significance of pattern"""
    performance = self.pattern_performance.get(pattern_type, {})
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