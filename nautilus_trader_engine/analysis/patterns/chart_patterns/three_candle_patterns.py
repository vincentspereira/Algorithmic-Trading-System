"""
Three-Candle Chart Pattern Detection.

This module provides functions to detect three-candle patterns in financial data.
These patterns are formed by the interaction of three consecutive candles and often
provide strong confirmation of market reversals or continuations.

Each function in this module is designed to analyze three consecutive candles and
return a `PatternAnalysis` object if a specific pattern is detected.

Available Patterns:
- Morning Star
- Evening Star
- Three White Soldiers
- Three Black Crows
- Abandoned Baby (Bullish and Bearish)
- Three Inside Up/Down
- Three Outside Up/Down
- Upside Tasuki Gap

"""

from datetime import datetime
from typing import Optional

from .base import CandleProperties, PatternAnalysis, PatternType, PatternStrength, VolumeProfile


def detect_morning_star(candle1: CandleProperties, candle2: CandleProperties, candle3: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Morning Star pattern"""
    is_morning_star = (
        candle1.is_bearish and
        candle2.body_size < candle1.body_size and
        candle3.is_bullish and
        candle3.close > candle1.midpoint
    )
    if not is_morning_star:
        return None
    
    confidence = 0.85
    return PatternAnalysis(
        pattern_name="Morning_Star",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.VERY_STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_evening_star(candle1: CandleProperties, candle2: CandleProperties, candle3: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Evening Star pattern"""
    is_evening_star = (
        candle1.is_bullish and
        candle2.body_size < candle1.body_size and
        candle3.is_bearish and
        candle3.close < candle1.midpoint
    )
    if not is_evening_star:
        return None
    
    confidence = 0.85
    return PatternAnalysis(
        pattern_name="Evening_Star",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.VERY_STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_three_white_soldiers(candle1: CandleProperties, candle2: CandleProperties, candle3: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Three White Soldiers pattern"""
    is_three_white_soldiers = (
        candle1.is_bullish and candle2.is_bullish and candle3.is_bullish and
        candle2.open > candle1.open and candle2.close > candle1.close and
        candle3.open > candle2.open and candle3.close > candle2.close and
        candle1.upper_shadow < candle1.body_size and
        candle2.upper_shadow < candle2.body_size and
        candle3.upper_shadow < candle3.body_size
    )
    if not is_three_white_soldiers:
        return None
    
    confidence = 0.90
    return PatternAnalysis(
        pattern_name="Three_White_Soldiers",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.VERY_STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_three_black_crows(candle1: CandleProperties, candle2: CandleProperties, candle3: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Three Black Crows pattern"""
    is_three_black_crows = (
        candle1.is_bearish and candle2.is_bearish and candle3.is_bearish and
        candle2.open < candle1.open and candle2.close < candle1.close and
        candle3.open < candle2.open and candle3.close < candle2.close and
        candle1.lower_shadow < candle1.body_size and
        candle2.lower_shadow < candle2.body_size and
        candle3.lower_shadow < candle3.body_size
    )
    if not is_three_black_crows:
        return None
    
    confidence = 0.90
    return PatternAnalysis(
        pattern_name="Three_Black_Crows",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.VERY_STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_abandoned_baby_bullish(candle1: CandleProperties, candle2: CandleProperties, candle3: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Bullish Abandoned Baby pattern"""
    is_abandoned_baby = (
        candle1.is_bearish and
        candle2.high < candle1.low and
        candle3.is_bullish and
        candle3.low > candle2.high
    )
    if not is_abandoned_baby:
        return None
    
    confidence = 0.95
    return PatternAnalysis(
        pattern_name="Abandoned_Baby_Bullish",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.VERY_STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_abandoned_baby_bearish(candle1: CandleProperties, candle2: CandleProperties, candle3: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Bearish Abandoned Baby pattern"""
    is_abandoned_baby = (
        candle1.is_bullish and
        candle2.low > candle1.high and
        candle3.is_bearish and
        candle3.high < candle2.low
    )
    if not is_abandoned_baby:
        return None
    
    confidence = 0.95
    return PatternAnalysis(
        pattern_name="Abandoned_Baby_Bearish",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.VERY_STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_three_inside_up(candle1: CandleProperties, candle2: CandleProperties, candle3: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Three Inside Up pattern"""
    is_three_inside_up = (
        candle1.is_bearish and
        candle2.is_bullish and
        candle2.open > candle1.close and candle2.close < candle1.open and
        candle3.is_bullish and candle3.close > candle1.high
    )
    if not is_three_inside_up:
        return None
    
    confidence = 0.80
    return PatternAnalysis(
        pattern_name="Three_Inside_Up",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_three_inside_down(candle1: CandleProperties, candle2: CandleProperties, candle3: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Three Inside Down pattern"""
    is_three_inside_down = (
        candle1.is_bullish and
        candle2.is_bearish and
        candle2.open < candle1.close and candle2.close > candle1.open and
        candle3.is_bearish and candle3.close < candle1.low
    )
    if not is_three_inside_down:
        return None
    
    confidence = 0.80
    return PatternAnalysis(
        pattern_name="Three_Inside_Down",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_three_outside_up(candle1: CandleProperties, candle2: CandleProperties, candle3: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Three Outside Up pattern"""
    is_three_outside_up = (
        candle1.is_bearish and
        candle2.is_bullish and
        candle2.close > candle1.open and candle2.open < candle1.close and
        candle3.is_bullish and candle3.close > candle2.close
    )
    if not is_three_outside_up:
        return None
    
    confidence = 0.82
    return PatternAnalysis(
        pattern_name="Three_Outside_Up",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_three_outside_down(candle1: CandleProperties, candle2: CandleProperties, candle3: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Three Outside Down pattern"""
    is_three_outside_down = (
        candle1.is_bullish and
        candle2.is_bearish and
        candle2.close < candle1.open and candle2.open > candle1.close and
        candle3.is_bearish and candle3.close < candle2.close
    )
    if not is_three_outside_down:
        return None
    
    confidence = 0.82
    return PatternAnalysis(
        pattern_name="Three_Outside_Down",
        pattern_type=PatternType.REVERSAL,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )

def detect_upside_tasuki_gap(candle1: CandleProperties, candle2: CandleProperties, candle3: CandleProperties, timestamp: datetime) -> Optional[PatternAnalysis]:
    """Detect Upside Tasuki Gap pattern"""
    is_upside_tasuki_gap = (
        candle1.is_bullish and
        candle2.is_bullish and candle2.open > candle1.close and
        candle3.is_bearish and
        candle3.open < candle2.close and candle3.open > candle2.open and
        candle3.close < candle1.close and candle3.close > candle1.open
    )
    if not is_upside_tasuki_gap:
        return None
    
    confidence = 0.70
    return PatternAnalysis(
        pattern_name="Upside_Tasuki_Gap",
        pattern_type=PatternType.CONTINUATION,
        detected=True,
        confidence=confidence,
        strength=PatternStrength.STRONG,
        volume_profile=VolumeProfile.NEUTRAL,
        timestamp=timestamp
    )