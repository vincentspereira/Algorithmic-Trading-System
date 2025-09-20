"""
strength.py
"""

import numpy as np

from nautilus_trader.indicators.data.candle import CandleData


def calculate_pattern_strength(self, candle: CandleData) -> float:
    """Calculate pattern strength based on candle characteristics"""
    if candle.total_range == 0:
        return 0.0

    body_ratio = candle.body_size / candle.total_range
    volume_ratio = self._get_volume_ratio()

    strength = 0.5
    strength += body_ratio * 0.3
    strength += min(volume_ratio - 1, 0.2)

    return min(strength, 1.0)

def calculate_two_candle_strength(
    self, prev: CandleData, curr: CandleData
) -> float:
    """Calculate strength for two-candle patterns"""
    avg_body = (prev.body_size + curr.body_size) / 2
    avg_range = (prev.total_range + curr.total_range) / 2

    if avg_range == 0:
        return 0.0

    body_ratio = avg_body / avg_range
    volume_ratio = self._get_volume_ratio()

    strength = 0.5 + body_ratio * 0.3 + min(volume_ratio - 1, 0.2)
    return min(strength, 1.0)

def calculate_three_candle_strength(
    self, first: CandleData, middle: CandleData, last: CandleData
) -> float:
    """Calculate strength for three-candle patterns"""
    avg_body = (first.body_size + middle.body_size + last.body_size) / 3
    avg_range = (first.total_range + middle.total_range + last.total_range) / 3

    if avg_range == 0:
        return 0.0

    body_ratio = avg_body / avg_range
    volume_ratio = self._get_volume_ratio()

    strength = 0.6 + body_ratio * 0.25 + min(volume_ratio - 1, 0.15)
    return min(strength, 1.0)