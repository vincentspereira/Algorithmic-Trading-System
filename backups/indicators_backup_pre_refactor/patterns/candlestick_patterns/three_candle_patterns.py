"""
three_candle_patterns.py
"""

from nautilus_trader.indicators.data.candle import CandleData
from nautilus_trader.indicators.data.pattern import PatternResult
from nautilus_trader.indicators.enum.pattern import (
    PatternType,
    PatternSignal,
    PatternReliability,
)


def detect_three_candle_patterns(self) -> list[PatternResult]:
    """Detect three candle patterns"""
    patterns = []
    current = self.candle_history[-1]
    middle = self.candle_history[-2]
    first = self.candle_history[-3]

    # Morning Star
    if _is_morning_star(first, middle, current):
        patterns.append(
            PatternResult(
                pattern_type=PatternType.MORNING_STAR,
                signal=PatternSignal.BULLISH,
                confidence=_calculate_star_confidence(first, middle, current),
                strength=_calculate_three_candle_strength(first, middle, current),
                reliability=PatternReliability.VERY_HIGH,
                trend_context=self.current_trend,
                candles_analyzed=3,
            )
        )

    # Evening Star
    if _is_evening_star(first, middle, current):
        patterns.append(
            PatternResult(
                pattern_type=PatternType.EVENING_STAR,
                signal=PatternSignal.BEARISH,
                confidence=_calculate_star_confidence(first, middle, current),
                strength=_calculate_three_candle_strength(first, middle, current),
                reliability=PatternReliability.VERY_HIGH,
                trend_context=self.current_trend,
                candles_analyzed=3,
            )
        )

    # Three White Soldiers
    if _is_three_white_soldiers(first, middle, current):
        patterns.append(
            PatternResult(
                pattern_type=PatternType.THREE_WHITE_SOLDIERS,
                signal=PatternSignal.BULLISH,
                confidence=_calculate_soldiers_confidence(first, middle, current),
                strength=_calculate_three_candle_strength(first, middle, current),
                reliability=PatternReliability.HIGH,
                trend_context=self.current_trend,
                candles_analyzed=3,
            )
        )

    # Three Black Crows
    if _is_three_black_crows(first, middle, current):
        patterns.append(
            PatternResult(
                pattern_type=PatternType.THREE_BLACK_CROWS,
                signal=PatternSignal.BEARISH,
                confidence=_calculate_crows_confidence(first, middle, current),
                strength=_calculate_three_candle_strength(first, middle, current),
                reliability=PatternReliability.HIGH,
                trend_context=self.current_trend,
                candles_analyzed=3,
            )
        )

    return patterns

def _is_morning_star(
    first: CandleData, middle: CandleData, last: CandleData
) -> bool:
    """Check for morning star pattern"""
    # First candle is bearish
    if not first.is_bearish:
        return False

    # Middle candle is small (doji or spinning top)
    if middle.body_size > first.body_size * 0.3:
        return False

    # Last candle is bullish and closes above midpoint of first
    if not last.is_bullish:
        return False

    midpoint = (first.open + first.close) / 2
    return last.close > midpoint

def _is_evening_star(
    first: CandleData, middle: CandleData, last: CandleData
) -> bool:
    """Check for evening star pattern"""
    # First candle is bullish
    if not first.is_bullish:
        return False

    # Middle candle is small (doji or spinning top)
    if middle.body_size > first.body_size * 0.3:
        return False

    # Last candle is bearish and closes below midpoint of first
    if not last.is_bearish:
        return False

    midpoint = (first.open + first.close) / 2
    return last.close < midpoint

def _is_three_white_soldiers(
    first: CandleData, middle: CandleData, last: CandleData
) -> bool:
    """Check for three white soldiers pattern"""
    # All three candles are bullish
    if not (first.is_bullish and middle.is_bullish and last.is_bullish):
        return False

    # Each candle opens within previous candle's body
    if not (first.close > middle.open > first.open):
        return False

    if not (middle.close > last.open > middle.open):
        return False

    # Each candle closes higher than previous
    return middle.close > first.close and last.close > middle.close

def _is_three_black_crows(
    first: CandleData, middle: CandleData, last: CandleData
) -> bool:
    """Check for three black crows pattern"""
    # All three candles are bearish
    if not (first.is_bearish and middle.is_bearish and last.is_bearish):
        return False

    # Each candle opens within previous candle's body
    if not (first.close < middle.open < first.open):
        return False

    if not (middle.close < last.open < middle.open):
        return False

    # Each candle closes lower than previous
    return middle.close < first.close and last.close < middle.close