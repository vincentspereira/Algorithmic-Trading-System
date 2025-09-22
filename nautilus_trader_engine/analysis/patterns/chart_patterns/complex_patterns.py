"""
Complex Chart Pattern Detection (4+ candles).

This module provides functions to detect complex chart patterns that form over
four or more candles. These patterns often signal significant market turning points
or continuations and are highly valued by technical analysts.

Each function in this module is designed to analyze a sequence of candles and
return a `PatternAnalysis` object if a specific pattern is detected.

Available Patterns:
- Bullish/Bearish Hikkake
- Mat Hold
- Rising Three Methods
- Falling Three Methods
- Upside Tasuki Gap
- Downside Tasuki Gap
- Rising Window
- Falling Window
- Bullish Flag
- Bearish Flag

"""

from datetime import datetime
from typing import Optional

from .base import CandleProperties, PatternAnalysis, PatternType, PatternStrength, VolumeProfile


def detect_bullish_hikkake(
    candle1: CandleProperties, 
    candle2: CandleProperties, 
    candle3: CandleProperties, 
    candle4: CandleProperties, 
    timestamp: datetime
) -> Optional[PatternAnalysis]:
    """Detect Bullish Hikkake pattern"""
    is_hikkake = (
        candle1.is_bullish and
        candle2.is_bearish and
        candle2.high < candle1.high and candle2.low > candle1.low and
        candle3.is_bullish and
        candle3.close > candle1.high
    )
    if not is_hikkake:
        return None
    
    confidence = 0.78
    return PatternAnalysis(
        pattern_name="Bullish_Hikkake",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_mat_hold(
    candle1: CandleProperties, 
    candle2: CandleProperties, 
    candle3: CandleProperties, 
    candle4: CandleProperties, 
    candle5: CandleProperties, 
    timestamp: datetime
) -> Optional[PatternAnalysis]:
    """Detect Mat Hold pattern"""
    is_mat_hold = (
        candle1.is_bullish and candle1.body_ratio > 0.8 and
        candle2.is_bearish and candle2.open > candle1.close and
        candle3.is_bearish and candle3.open > candle2.open and
        candle4.is_bearish and candle4.open > candle3.open and
        candle5.is_bullish and candle5.close > candle1.high
    )
    if not is_mat_hold:
        return None
    
    confidence = 0.88
    return PatternAnalysis(
        pattern_name="Mat_Hold",
        pattern_type=PatternType.CONTINUATION,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.VERY_STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )


def detect_rising_three_methods(
    candle1: CandleProperties,
    candle2: CandleProperties,
    candle3: CandleProperties,
    candle4: CandleProperties,
    candle5: CandleProperties,
    timestamp
) -> Optional[PatternAnalysis]:
    """Detect Rising Three Methods pattern"""
    is_rising_three = (
        candle1.is_bullish and candle1.body_ratio > 0.7 and
        candle2.is_bearish and candle2.open > candle1.close and
        candle3.is_bearish and candle3.open > candle2.open and
        candle4.is_bearish and candle4.open > candle3.open and
        candle5.is_bullish and candle5.close > candle1.high
    )
    if not is_rising_three:
        return None

    confidence = 0.82
    return PatternAnalysis(
        pattern_name="Rising_Three_Methods",
        pattern_type=PatternType.CONTINUATION,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )


def detect_falling_three_methods(
    candle1: CandleProperties,
    candle2: CandleProperties,
    candle3: CandleProperties,
    candle4: CandleProperties,
    candle5: CandleProperties,
    timestamp
) -> Optional[PatternAnalysis]:
    """Detect Falling Three Methods pattern"""
    is_falling_three = (
        candle1.is_bearish and candle1.body_ratio > 0.7 and
        candle2.is_bullish and candle2.open < candle1.close and
        candle3.is_bullish and candle3.open < candle2.open and
        candle4.is_bullish and candle4.open < candle3.open and
        candle5.is_bearish and candle5.close < candle1.low
    )
    if not is_falling_three:
        return None

    confidence = 0.82
    return PatternAnalysis(
        pattern_name="Falling_Three_Methods",
        pattern_type=PatternType.CONTINUATION,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )


def detect_upside_tasuki_gap(
    candle1: CandleProperties,
    candle2: CandleProperties,
    candle3: CandleProperties,
    timestamp
) -> Optional[PatternAnalysis]:
    """Detect Upside Tasuki Gap pattern"""
    is_tasuki = (
        candle1.is_bullish and
        candle2.is_bullish and candle2.open > candle1.high and  # Gap up
        candle3.is_bearish and candle3.open > candle2.close and
        candle3.close > candle2.open and candle3.close < candle2.close  # Doesn't fill gap
    )
    if not is_tasuki:
        return None

    confidence = 0.75
    return PatternAnalysis(
        pattern_name="Upside_Tasuki_Gap",
        pattern_type=PatternType.CONTINUATION,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.MODERATE,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )


def detect_downside_tasuki_gap(
    candle1: CandleProperties,
    candle2: CandleProperties,
    candle3: CandleProperties,
    timestamp
) -> Optional[PatternAnalysis]:
    """Detect Downside Tasuki Gap pattern"""
    is_tasuki = (
        candle1.is_bearish and
        candle2.is_bearish and candle2.open < candle1.low and  # Gap down
        candle3.is_bullish and candle3.open < candle2.close and
        candle3.close < candle2.open and candle3.close > candle2.close  # Doesn't fill gap
    )
    if not is_tasuki:
        return None

    confidence = 0.75
    return PatternAnalysis(
        pattern_name="Downside_Tasuki_Gap",
        pattern_type=PatternType.CONTINUATION,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.MODERATE,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )


def detect_rising_window(
    candle1: CandleProperties,
    candle2: CandleProperties,
    timestamp
) -> Optional[PatternAnalysis]:
    """Detect Rising Window pattern"""
    is_window = (
        candle1.is_bullish and
        candle2.is_bullish and
        candle2.low > candle1.high  # Gap between candles
    )
    if not is_window:
        return None

    confidence = 0.78
    return PatternAnalysis(
        pattern_name="Rising_Window",
        pattern_type=PatternType.CONTINUATION,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.STRONG,
        volume_profile=VolumeProfile.HIGH_VOLUME,
        timestamp=timestamp
    )


def detect_falling_window(
    candle1: CandleProperties,
    candle2: CandleProperties,
    timestamp
) -> Optional[PatternAnalysis]:
    """Detect Falling Window pattern"""
    is_window = (
        candle1.is_bearish and
        candle2.is_bearish and
        candle2.high < candle1.low  # Gap between candles
    )
    if not is_window:
        return None

    confidence = 0.78
    return PatternAnalysis(
        pattern_name="Falling_Window",
        pattern_type=PatternType.CONTINUATION,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.STRONG,
        volume_profile=VolumeProfile.HIGH_VOLUME,
        timestamp=timestamp
    )


def detect_bullish_flag(
    candle1: CandleProperties,
    candle2: CandleProperties,
    candle3: CandleProperties,
    candle4: CandleProperties,
    candle5: CandleProperties,
    timestamp
) -> Optional[PatternAnalysis]:
    """Detect Bullish Flag pattern"""
    # Simplified flag detection - sharp move up followed by consolidation
    is_flag = (
        candle1.is_bullish and candle1.body_ratio > 0.8 and
        candle2.is_bullish and candle2.close > candle1.close and
        abs(candle3.close - candle2.close) < candle2.body_size * 0.5 and  # Consolidation
        abs(candle4.close - candle3.close) < candle3.body_size * 0.5 and
        candle5.is_bullish and candle5.close > candle4.high
    )
    if not is_flag:
        return None

    confidence = 0.70
    return PatternAnalysis(
        pattern_name="Bullish_Flag",
        pattern_type=PatternType.CONTINUATION,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.MODERATE,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )


def detect_bearish_flag(
    candle1: CandleProperties,
    candle2: CandleProperties,
    candle3: CandleProperties,
    candle4: CandleProperties,
    candle5: CandleProperties,
    timestamp
) -> Optional[PatternAnalysis]:
    """Detect Bearish Flag pattern"""
    # Simplified flag detection - sharp move down followed by consolidation
    is_flag = (
        candle1.is_bearish and candle1.body_ratio > 0.8 and
        candle2.is_bearish and candle2.close < candle1.close and
        abs(candle3.close - candle2.close) < candle2.body_size * 0.5 and  # Consolidation
        abs(candle4.close - candle3.close) < candle3.body_size * 0.5 and
        candle5.is_bearish and candle5.close < candle4.low
    )
    if not is_flag:
        return None

    confidence = 0.70
    return PatternAnalysis(
        pattern_name="Bearish_Flag",
        pattern_type=PatternType.CONTINUATION,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.MODERATE,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )


def detect_bullish_hikkake(
    candle1: CandleProperties,
    candle2: CandleProperties,
    candle3: CandleProperties,
    candle4: CandleProperties,
    timestamp: datetime
) -> Optional[PatternAnalysis]:
    """Detect Bullish Hikkake pattern"""
    is_hikkake = (
        candle1.is_bullish and
        candle2.is_bearish and
        candle2.high < candle1.high and candle2.low > candle1.low and
        candle3.is_bullish and
        candle3.close > candle1.high
    )
    if not is_hikkake:
        return None

    confidence = 0.78
    return PatternAnalysis(
        pattern_name="Bullish_Hikkake",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )


def detect_bearish_hikkake(
    candle1: CandleProperties,
    candle2: CandleProperties,
    candle3: CandleProperties,
    candle4: CandleProperties,
    timestamp: datetime
) -> Optional[PatternAnalysis]:
    """Detect Bearish Hikkake pattern"""
    is_hikkake = (
        candle1.is_bearish and
        candle2.is_bullish and
        candle2.low > candle1.low and candle2.high < candle1.high and
        candle3.is_bearish and
        candle3.close < candle1.low
    )
    if not is_hikkake:
        return None

    confidence = 0.78
    return PatternAnalysis(
        pattern_name="Bearish_Hikkake",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )