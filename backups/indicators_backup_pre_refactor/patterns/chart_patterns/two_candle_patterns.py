"""
Two-Candle Chart Pattern Detection.

This module provides functions to detect two-candle patterns in financial data.
These patterns are formed by the interaction of two consecutive candles and can
provide strong signals for reversals or continuations.

Each function in this module is designed to analyze two consecutive candles and
return a `PatternAnalysis` object if a specific pattern is detected.

Available Patterns:
- Bullish/Bearish Engulfing
- Bullish/Bearish Harami
- Piercing Line
- Dark Cloud Cover
- Tweezer Top/Bottom
- Kicking (Bullish and Bearish)

"""

from datetime import datetime
from typing import Optional

from .base import CandleProperties, PatternAnalysis, PatternType, PatternStrength, VolumeProfile


def detect_bullish_engulfing(prev_candle: CandleProperties, current_candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Bullish Engulfing pattern"""
    is_bullish_engulfing = (
        prev_candle.is_bearish and
        current_candle.is_bullish and
        current_candle.close > prev_candle.open and
        current_candle.open < prev_candle.close
    )
    if not is_bullish_engulfing:
        return None
    
    confidence = 0.80
    return PatternAnalysis(
        pattern_name="Bullish_Engulfing",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_bearish_engulfing(prev_candle: CandleProperties, current_candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Bearish Engulfing pattern"""
    is_bearish_engulfing = (
        prev_candle.is_bullish and
        current_candle.is_bearish and
        current_candle.close < prev_candle.open and
        current_candle.open > prev_candle.close
    )
    if not is_bearish_engulfing:
        return None
    
    confidence = 0.80
    return PatternAnalysis(
        pattern_name="Bearish_Engulfing",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_bullish_harami(prev_candle: CandleProperties, current_candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Bullish Harami pattern"""
    is_bullish_harami = (
        prev_candle.is_bearish and
        current_candle.is_bullish and
        current_candle.open > prev_candle.close and
        current_candle.close < prev_candle.open
    )
    if not is_bullish_harami:
        return None
    
    confidence = 0.65
    return PatternAnalysis(
        pattern_name="Bullish_Harami",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.MEDIUM,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_bearish_harami(prev_candle: CandleProperties, current_candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Bearish Harami pattern"""
    is_bearish_harami = (
        prev_candle.is_bullish and
        current_candle.is_bearish and
        current_candle.open < prev_candle.close and
        current_candle.close > prev_candle.open
    )
    if not is_bearish_harami:
        return None
    
    confidence = 0.65
    return PatternAnalysis(
        pattern_name="Bearish_Harami",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.MEDIUM,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_piercing_line(prev_candle: CandleProperties, current_candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Piercing Line pattern"""
    is_piercing_line = (
        prev_candle.is_bearish and
        current_candle.is_bullish and
        current_candle.open < prev_candle.low and
        current_candle.close > prev_candle.midpoint and
        current_candle.close < prev_candle.open
    )
    if not is_piercing_line:
        return None
    
    confidence = 0.75
    return PatternAnalysis(
        pattern_name="Piercing_Line",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_dark_cloud_cover(prev_candle: CandleProperties, current_candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Dark Cloud Cover pattern"""
    is_dark_cloud = (
        prev_candle.is_bullish and
        current_candle.is_bearish and
        current_candle.open > prev_candle.high and
        current_candle.close < prev_candle.midpoint and
        current_candle.close > prev_candle.open
    )
    if not is_dark_cloud:
        return None
    
    confidence = 0.75
    return PatternAnalysis(
        pattern_name="Dark_Cloud_Cover",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_tweezer_top(prev_candle: CandleProperties, current_candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Tweezer Top pattern"""
    is_tweezer_top = (
        prev_candle.is_bullish and
        current_candle.is_bearish and
        abs(prev_candle.high - current_candle.high) < (0.05 * prev_candle.high)
    )
    if not is_tweezer_top:
        return None
    
    confidence = 0.70
    return PatternAnalysis(
        pattern_name="Tweezer_Top",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_tweezer_bottom(prev_candle: CandleProperties, current_candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Tweezer Bottom pattern"""
    is_tweezer_bottom = (
        prev_candle.is_bearish and
        current_candle.is_bullish and
        abs(prev_candle.low - current_candle.low) < (0.05 * prev_candle.low)
    )
    if not is_tweezer_bottom:
        return None
    
    confidence = 0.70
    return PatternAnalysis(
        pattern_name="Tweezer_Bottom",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_kicking_bullish(prev_candle: CandleProperties, current_candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Bullish Kicking pattern"""
    is_kicking = (
        prev_candle.is_bearish and prev_candle.body_ratio > 0.9 and
        current_candle.is_bullish and current_candle.body_ratio > 0.9 and
        current_candle.open > prev_candle.open
    )
    if not is_kicking:
        return None
    
    confidence = 0.85
    return PatternAnalysis(
        pattern_name="Kicking_Bullish",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.VERY_STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_kicking_bearish(prev_candle: CandleProperties, current_candle: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Bearish Kicking pattern"""
    is_kicking = (
        prev_candle.is_bullish and prev_candle.body_ratio > 0.9 and
        current_candle.is_bearish and current_candle.body_ratio > 0.9 and
        current_candle.open < prev_candle.open
    )
    if not is_kicking:
        return None
    
    confidence = 0.85
    return PatternAnalysis(
        pattern_name="Kicking_Bearish",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.VERY_STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )