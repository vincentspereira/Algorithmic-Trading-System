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