"""
confidence.py
"""

import numpy as np

from nautilus_trader.indicators.data.candle import CandleData


def calculate_hammer_confidence(candle: CandleData) -> float:
    """Calculate confidence for hammer pattern"""
    body_ratio = candle.body_size / candle.total_range
    shadow_ratio = candle.lower_shadow / candle.body_size

    confidence = 0.5
    confidence += (1 - body_ratio) * 0.3  # Smaller body = higher confidence
    confidence += min(shadow_ratio / 3, 0.2)  # Longer shadow = higher confidence

    return min(confidence, 1.0)

def calculate_shooting_star_confidence(candle: CandleData) -> float:
    """Calculate confidence for shooting star pattern"""
    body_ratio = candle.body_size / candle.total_range
    shadow_ratio = candle.upper_shadow / candle.body_size

    confidence = 0.5
    confidence += (1 - body_ratio) * 0.3
    confidence += min(shadow_ratio / 3, 0.2)

    return min(confidence, 1.0)

def calculate_doji_confidence(candle: CandleData) -> float:
    """Calculate confidence for doji pattern"""
    body_ratio = candle.body_size / candle.total_range
    confidence = 0.7 + (1 - body_ratio) * 0.3
    return min(confidence, 1.0)

def calculate_marubozu_confidence(candle: CandleData) -> float:
    """Calculate confidence for marubozu pattern"""
    body_ratio = candle.body_size / candle.total_range
    return min(0.5 + body_ratio * 0.5, 1.0)

def calculate_engulfing_confidence(prev: CandleData, curr: CandleData) -> float:
    """Calculate confidence for engulfing pattern"""
    engulf_ratio = curr.body_size / prev.body_size
    confidence = 0.6 + min(engulf_ratio - 1, 0.3)
    return min(confidence, 1.0)

def calculate_tweezer_confidence(prev: CandleData, curr: CandleData) -> float:
    """Calculate confidence for tweezer pattern"""
    high_diff = abs(prev.high - curr.high) / prev.high
    low_diff = abs(prev.low - curr.low) / prev.low

    min_diff = min(high_diff, low_diff)
    confidence = 0.7 - min_diff * 100  # Lower difference = higher confidence
    return max(min(confidence, 1.0), 0.3)

def calculate_piercing_confidence(prev: CandleData, curr: CandleData) -> float:
    """Calculate confidence for piercing pattern"""
    midpoint = (prev.open + prev.close) / 2
    penetration = (curr.close - midpoint) / prev.body_size

    confidence = 0.6 + min(penetration, 0.3)
    return min(confidence, 1.0)

def calculate_dark_cloud_confidence(prev: CandleData, curr: CandleData) -> float:
    """Calculate confidence for dark cloud cover pattern"""
    midpoint = (prev.open + prev.close) / 2
    penetration = (midpoint - curr.close) / prev.body_size

    confidence = 0.6 + min(penetration, 0.3)
    return min(confidence, 1.0)

def calculate_star_confidence(
    first: CandleData, middle: CandleData, last: CandleData
) -> float:
    """Calculate confidence for star patterns"""
    middle_ratio = middle.body_size / first.body_size
    penetration = abs(last.close - (first.open + first.close) / 2) / first.body_size

    confidence = 0.7
    confidence += (1 - middle_ratio) * 0.2  # Smaller middle = higher confidence
    confidence += min(penetration, 0.1)  # More penetration = higher confidence

    return min(confidence, 1.0)

def calculate_soldiers_confidence(
    first: CandleData, middle: CandleData, last: CandleData
) -> float:
    """Calculate confidence for three white soldiers"""
    # Check body sizes are similar
    bodies = [first.body_size, middle.body_size, last.body_size]
    body_consistency = 1 - (max(bodies) - min(bodies)) / np.mean(bodies)

    confidence = 0.6 + body_consistency * 0.3
    return min(confidence, 1.0)

def calculate_crows_confidence(
    first: CandleData, middle: CandleData, last: CandleData
) -> float:
    """Calculate confidence for three black crows"""
    # Check body sizes are similar
    bodies = [first.body_size, middle.body_size, last.body_size]
    body_consistency = 1 - (max(bodies) - min(bodies)) / np.mean(bodies)

    confidence = 0.6 + body_consistency * 0.3
    return min(confidence, 1.0)