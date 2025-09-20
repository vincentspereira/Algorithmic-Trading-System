"""
two_candle_patterns.py
"""

from nautilus_trader.indicators.data.candle import CandleData
from nautilus_trader.indicators.data.pattern import PatternResult
from nautilus_trader.indicators.enum.pattern import (
    PatternType,
    PatternSignal,
    PatternReliability,
)


def detect_two_candle_patterns(self) -> list[PatternResult]:
    """Detect two candle patterns"""
    patterns = []
    current = self.candle_history[-1]
    previous = self.candle_history[-2]

    # Engulfing patterns
    if _is_bullish_engulfing(previous, current):
        patterns.append(
            PatternResult(
                pattern_type=PatternType.BULLISH_ENGULFING,
                signal=PatternSignal.BULLISH,
                confidence=_calculate_engulfing_confidence(previous, current),
                strength=_calculate_two_candle_strength(previous, current),
                reliability=PatternReliability.HIGH,
                trend_context=self.current_trend,
                candles_analyzed=2,
            )
        )

    if _is_bearish_engulfing(previous, current):
        patterns.append(
            PatternResult(
                pattern_type=PatternType.BEARISH_ENGULFING,
                signal=PatternSignal.BEARISH,
                confidence=_calculate_engulfing_confidence(previous, current),
                strength=_calculate_two_candle_strength(previous, current),
                reliability=PatternReliability.HIGH,
                trend_context=self.current_trend,
                candles_analyzed=2,
            )
        )

    # Tweezer patterns
    if _is_tweezer_top(previous, current):
        patterns.append(
            PatternResult(
                pattern_type=PatternType.TWEEZER_TOP,
                signal=PatternSignal.BEARISH,
                confidence=_calculate_tweezer_confidence(previous, current),
                strength=_calculate_two_candle_strength(previous, current),
                reliability=PatternReliability.MEDIUM,
                trend_context=self.current_trend,
                candles_analyzed=2,
            )
        )

    if _is_tweezer_bottom(previous, current):
        patterns.append(
            PatternResult(
                pattern_type=PatternType.TWEEZER_BOTTOM,
                signal=PatternSignal.BULLISH,
                confidence=_calculate_tweezer_confidence(previous, current),
                strength=_calculate_two_candle_strength(previous, current),
                reliability=PatternReliability.MEDIUM,
                trend_context=self.current_trend,
                candles_analyzed=2,
            )
        )

    # Piercing Pattern
    if _is_piercing_pattern(previous, current):
        patterns.append(
            PatternResult(
                pattern_type=PatternType.PIERCING_PATTERN,
                signal=PatternSignal.BULLISH,
                confidence=_calculate_piercing_confidence(previous, current),
                strength=_calculate_two_candle_strength(previous, current),
                reliability=PatternReliability.HIGH,
                trend_context=self.current_trend,
                candles_analyzed=2,
            )
        )

    # Dark Cloud Cover
    if _is_dark_cloud_cover(previous, current):
        patterns.append(
            PatternResult(
                pattern_type=PatternType.DARK_CLOUD_COVER,
                signal=PatternSignal.BEARISH,
                confidence=_calculate_dark_cloud_confidence(previous, current),
                strength=_calculate_two_candle_strength(previous, current),
                reliability=PatternReliability.HIGH,
                trend_context=self.current_trend,
                candles_analyzed=2,
            )
        )

    return patterns

def _is_bullish_engulfing(prev: CandleData, curr: CandleData) -> bool:
    """Check for bullish engulfing pattern"""
    return (
        prev.is_bearish
        and curr.is_bullish
        and curr.open < prev.close
        and curr.close > prev.open
    )

def _is_bearish_engulfing(prev: CandleData, curr: CandleData) -> bool:
    """Check for bearish engulfing pattern"""
    return (
        prev.is_bullish
        and curr.is_bearish
        and curr.open > prev.close
        and curr.close < prev.open
    )

def _is_tweezer_top(prev: CandleData, curr: CandleData) -> bool:
    """Check for tweezer top pattern"""
    high_diff = abs(prev.high - curr.high) / prev.high
    return prev.is_bullish and curr.is_bearish and high_diff < 0.002  # Highs within 0.2%

def _is_tweezer_bottom(prev: CandleData, curr: CandleData) -> bool:
    """Check for tweezer bottom pattern"""
    low_diff = abs(prev.low - curr.low) / prev.low
    return prev.is_bearish and curr.is_bullish and low_diff < 0.002  # Lows within 0.2%

def _is_piercing_pattern(prev: CandleData, curr: CandleData) -> bool:
    """Check for piercing pattern"""
    if not (prev.is_bearish and curr.is_bullish):
        return False

    # Current candle opens below previous low
    if curr.open >= prev.low:
        return False

    # Current candle closes above midpoint of previous candle
    midpoint = (prev.open + prev.close) / 2
    return curr.close > midpoint

def _is_dark_cloud_cover(prev: CandleData, curr: CandleData) -> bool:
    """Check for dark cloud cover pattern"""
    if not (prev.is_bullish and curr.is_bearish):
        return False

    # Current candle opens above previous high
    if curr.open <= prev.high:
        return False

    # Current candle closes below midpoint of previous candle
    midpoint = (prev.open + prev.close) / 2
    return curr.close < midpoint