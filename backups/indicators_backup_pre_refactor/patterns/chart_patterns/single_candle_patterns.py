"""
Single-Candle Chart Pattern Detection.

This module provides functions to detect single-candle patterns in financial data.
These patterns are fundamental building blocks for more complex technical analysis.

Each function in this module is designed to analyze a single candle and return a
`PatternAnalysis` object if a specific pattern is detected. The analysis includes
confidence scores, pattern strength, and other relevant metadata.

Available Patterns:
- Hammer
- Inverted Hammer
- Shooting Star
- Doji
- Marubozu
- Hanging Man
- Spinning Top
- Long-Legged Doji
- Dragonfly Doji
- Gravestone Doji
- Four-Price Doji
- Belt Hold (Bullish and Bearish)
- Rickshaw Man
- High Wave Candle

"""

from datetime import datetime
from typing import Optional

from .base import CandleProperties, PatternAnalysis, PatternType, PatternStrength, VolumeProfile


def detect_hammer(candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect hammer pattern with volume analysis"""
    is_hammer = (
        candle.lower_shadow >= 2 * candle.body_size and
        candle.upper_shadow <= 0.15 * candle.total_range and
        candle.body_ratio <= 0.35
    )
    if not is_hammer:
        return None
    
    base_confidence = 0.65
    return PatternAnalysis(
        pattern_name="Hammer",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=base_confidence,
        strength=PatternStrength.MEDIUM,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_inverted_hammer(candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect inverted hammer pattern"""
    is_inverted_hammer = (
        candle.upper_shadow >= 2 * candle.body_size and
        candle.lower_shadow <= 0.15 * candle.total_range and
        candle.body_ratio <= 0.35
    )
    if not is_inverted_hammer:
        return None
    
    confidence = 0.60
    return PatternAnalysis(
        pattern_name="Inverted_Hammer",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.MEDIUM,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_shooting_star(candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect shooting star pattern"""
    is_shooting_star = (
        candle.upper_shadow >= 2 * candle.body_size and
        candle.lower_shadow <= 0.1 * candle.total_range and
        candle.body_ratio <= 0.35
    )
    if not is_shooting_star:
        return None
    
    confidence = 0.70
    return PatternAnalysis(
        pattern_name="Shooting_Star",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_doji(candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Doji pattern"""
    is_doji = candle.body_ratio <= 0.05
    if not is_doji:
        return None
    
    confidence = 0.50
    return PatternAnalysis(
        pattern_name="Doji",
        pattern_type=PatternType.NEUTRAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.LOW,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_marubozu(candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Marubozu pattern"""
    is_marubozu = candle.body_ratio >= 0.95
    if not is_marubozu:
        return None
    
    confidence = 0.80
    return PatternAnalysis(
        pattern_name="Marubozu",
        pattern_type=PatternType.CONTINUATION,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_hanging_man(candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Hanging Man pattern"""
    is_hanging_man = (
        candle.lower_shadow >= 2 * candle.body_size and
        candle.upper_shadow <= 0.1 * candle.total_range and
        candle.body_ratio <= 0.35
    )
    if not is_hanging_man:
        return None
    
    confidence = 0.70
    return PatternAnalysis(
        pattern_name="Hanging_Man",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_spinning_top(candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Spinning Top pattern"""
    is_spinning_top = (
        candle.body_ratio < 0.3 and
        candle.upper_shadow > candle.body_size and
        candle.lower_shadow > candle.body_size
    )
    if not is_spinning_top:
        return None
    
    confidence = 0.55
    return PatternAnalysis(
        pattern_name="Spinning_Top",
        pattern_type=PatternType.NEUTRAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.LOW,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_long_legged_doji(candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Long-Legged Doji pattern"""
    is_long_legged = (
        candle.body_ratio < 0.1 and
        candle.upper_shadow > candle.body_size * 3 and
        candle.lower_shadow > candle.body_size * 3
    )
    if not is_long_legged:
        return None
    
    confidence = 0.60
    return PatternAnalysis(
        pattern_name="Long_Legged_Doji",
        pattern_type=PatternType.NEUTRAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.MEDIUM,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_dragonfly_doji(candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Dragonfly Doji pattern"""
    is_dragonfly = (
        candle.body_ratio < 0.1 and
        candle.upper_shadow < 0.1 * candle.total_range and
        candle.lower_shadow > candle.body_size * 3
    )
    if not is_dragonfly:
        return None
    
    confidence = 0.75
    return PatternAnalysis(
        pattern_name="Dragonfly_Doji",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_gravestone_doji(candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Gravestone Doji pattern"""
    is_gravestone = (
        candle.body_ratio < 0.1 and
        candle.lower_shadow < 0.1 * candle.total_range and
        candle.upper_shadow > candle.body_size * 3
    )
    if not is_gravestone:
        return None
    
    confidence = 0.75
    return PatternAnalysis(
        pattern_name="Gravestone_Doji",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_four_price_doji(candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Four-Price Doji pattern"""
    is_four_price = (
        candle.open == candle.high and
        candle.open == candle.low and
        candle.open == candle.close
    )
    if not is_four_price:
        return None
    
    confidence = 0.90
    return PatternAnalysis(
        pattern_name="Four_Price_Doji",
        pattern_type=PatternType.NEUTRAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.VERY_STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_belt_hold_bullish(candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Bullish Belt Hold pattern"""
    is_belt_hold = (
        candle.is_bullish and
        candle.open == candle.low and
        candle.body_size > 0.7 * candle.total_range
    )
    if not is_belt_hold:
        return None
    
    confidence = 0.70
    return PatternAnalysis(
        pattern_name="Belt_Hold_Bullish",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_belt_hold_bearish(candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Bearish Belt Hold pattern"""
    is_belt_hold = (
        candle.is_bearish and
        candle.open == candle.high and
        candle.body_size > 0.7 * candle.total_range
    )
    if not is_belt_hold:
        return None
    
    confidence = 0.70
    return PatternAnalysis(
        pattern_name="Belt_Hold_Bearish",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_rickshaw_man(candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Rickshaw Man pattern"""
    is_rickshaw = (
        candle.body_ratio < 0.1 and
        candle.upper_shadow > candle.body_size * 2 and
        candle.lower_shadow > candle.body_size * 2 and
        abs(candle.upper_shadow - candle.lower_shadow) < 0.2 * candle.total_range
    )
    if not is_rickshaw:
        return None
    
    confidence = 0.60
    return PatternAnalysis(
        pattern_name="Rickshaw_Man",
        pattern_type=PatternType.NEUTRAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.MEDIUM,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_high_wave_candle(candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect High Wave Candle pattern"""
    is_high_wave = (
        candle.body_ratio < 0.2 and
        candle.upper_shadow > candle.body_size * 2 and
        candle.lower_shadow > candle.body_size * 2
    )
    if not is_high_wave:
        return None
    
    confidence = 0.55
    return PatternAnalysis(
        pattern_name="High_Wave_Candle",
        pattern_type=PatternType.NEUTRAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.LOW,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )