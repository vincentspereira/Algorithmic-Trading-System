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

    # Three Inside Up
    if _is_three_inside_up(first, middle, current):
        patterns.append(
            PatternResult(
                pattern_type=PatternType.THREE_INSIDE_UP,
                signal=PatternSignal.BULLISH,
                confidence=_calculate_three_inside_confidence(first, middle, current),
                strength=_calculate_three_candle_strength(first, middle, current),
                reliability=PatternReliability.HIGH,
                trend_context=self.current_trend,
                candles_analyzed=3,
            )
        )

    # Three Inside Down
    if _is_three_inside_down(first, middle, current):
        patterns.append(
            PatternResult(
                pattern_type=PatternType.THREE_INSIDE_DOWN,
                signal=PatternSignal.BEARISH,
                confidence=_calculate_three_inside_confidence(first, middle, current),
                strength=_calculate_three_candle_strength(first, middle, current),
                reliability=PatternReliability.HIGH,
                trend_context=self.current_trend,
                candles_analyzed=3,
            )
        )

    # Bullish Abandoned Baby
    if _is_bullish_abandoned_baby(first, middle, current):
        patterns.append(
            PatternResult(
                pattern_type=PatternType.BULLISH_ABANDONED_BABY,
                signal=PatternSignal.BULLISH,
                confidence=_calculate_abandoned_baby_confidence(first, middle, current),
                strength=_calculate_three_candle_strength(first, middle, current),
                reliability=PatternReliability.VERY_HIGH,
                trend_context=self.current_trend,
                candles_analyzed=3,
            )
        )

    # Bearish Abandoned Baby
    if _is_bearish_abandoned_baby(first, middle, current):
        patterns.append(
            PatternResult(
                pattern_type=PatternType.BEARISH_ABANDONED_BABY,
                signal=PatternSignal.BEARISH,
                confidence=_calculate_abandoned_baby_confidence(first, middle, current),
                strength=_calculate_three_candle_strength(first, middle, current),
                reliability=PatternReliability.VERY_HIGH,
                trend_context=self.current_trend,
                candles_analyzed=3,
            )
        )

    # Stick Sandwich
    if _is_stick_sandwich(first, middle, current):
        signal = PatternSignal.BULLISH if current.close > first.close else PatternSignal.BEARISH
        pattern_type = PatternType.STICK_SANDWICH
        patterns.append(
            PatternResult(
                pattern_type=pattern_type,
                signal=signal,
                confidence=_calculate_stick_sandwich_confidence(first, middle, current),
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


def _is_three_inside_up(
    first: CandleData, middle: CandleData, last: CandleData
) -> bool:
    """Check for three inside up pattern"""
    # First candle is bearish
    if not first.is_bearish:
        return False

    # Second candle is bullish and contained within first
    if not (middle.is_bullish and middle.open > first.close and middle.close < first.open):
        return False

    # Third candle is bullish and closes above first candle's open
    return last.is_bullish and last.close > first.open


def _is_three_inside_down(
    first: CandleData, middle: CandleData, last: CandleData
) -> bool:
    """Check for three inside down pattern"""
    # First candle is bullish
    if not first.is_bullish:
        return False

    # Second candle is bearish and contained within first
    if not (middle.is_bearish and middle.open < first.close and middle.close > first.open):
        return False

    # Third candle is bearish and closes below first candle's open
    return last.is_bearish and last.close < first.open


def _is_bullish_abandoned_baby(
    first: CandleData, middle: CandleData, last: CandleData
) -> bool:
    """Check for bullish abandoned baby pattern"""
    # First candle is bearish
    if not first.is_bearish:
        return False

    # Middle candle is doji with gap down
    if not (middle.is_doji and middle.high < first.low):
        return False

    # Third candle is bullish with gap up
    return last.is_bullish and last.low > middle.high


def _is_bearish_abandoned_baby(
    first: CandleData, middle: CandleData, last: CandleData
) -> bool:
    """Check for bearish abandoned baby pattern"""
    # First candle is bullish
    if not first.is_bullish:
        return False

    # Middle candle is doji with gap up
    if not (middle.is_doji and middle.low > first.high):
        return False

    # Third candle is bearish with gap down
    return last.is_bearish and last.high < middle.low


def _calculate_star_confidence(
    first: CandleData, middle: CandleData, last: CandleData
) -> float:
    """Calculate confidence for morning/evening star patterns"""
    # Based on gap size and body sizes
    gap_size = abs(middle.close - first.close) / first.close if first.close != 0 else 0
    body_ratio = last.body_size / first.body_size if first.body_size > 0 else 0
    return min(1.0, (gap_size + body_ratio) / 2)


def _calculate_soldiers_confidence(
    first: CandleData, middle: CandleData, last: CandleData
) -> float:
    """Calculate confidence for three white soldiers pattern"""
    # All bullish with increasing closes
    if not all(c.is_bullish for c in [first, middle, last]):
        return 0.0

    closes = [first.close, middle.close, last.close]
    if not all(closes[i] < closes[i+1] for i in range(len(closes)-1)):
        return 0.0

    # Average body size relative to range
    avg_body = sum(c.body_size for c in [first, middle, last]) / 3
    avg_range = sum(c.total_range for c in [first, middle, last]) / 3
    return min(1.0, avg_body / avg_range) if avg_range > 0 else 0.0


def _calculate_crows_confidence(
    first: CandleData, middle: CandleData, last: CandleData
) -> float:
    """Calculate confidence for three black crows pattern"""
    # All bearish with decreasing closes
    if not all(c.is_bearish for c in [first, middle, last]):
        return 0.0

    closes = [first.close, middle.close, last.close]
    if not all(closes[i] > closes[i+1] for i in range(len(closes)-1)):
        return 0.0

    # Average body size relative to range
    avg_body = sum(c.body_size for c in [first, middle, last]) / 3
    avg_range = sum(c.total_range for c in [first, middle, last]) / 3
    return min(1.0, avg_body / avg_range) if avg_range > 0 else 0.0


def _calculate_three_inside_confidence(
    first: CandleData, middle: CandleData, last: CandleData
) -> float:
    """Calculate confidence for three inside patterns"""
    # Middle candle contained within first
    containment = 1.0 - (middle.body_size / first.body_size) if first.body_size > 0 else 0
    # Third candle breaks out
    breakout = abs(last.close - first.open) / first.body_size if first.body_size > 0 else 0
    return min(1.0, (containment + breakout) / 2)


def _calculate_abandoned_baby_confidence(
    first: CandleData, middle: CandleData, last: CandleData
) -> float:
    """Calculate confidence for abandoned baby patterns"""
    # Gap sizes
    gap1 = abs(middle.close - first.close) / first.close if first.close != 0 else 0
    gap2 = abs(last.close - middle.close) / middle.close if middle.close != 0 else 0
    return min(1.0, (gap1 + gap2) / 2)


def _calculate_three_candle_strength(
    first: CandleData, middle: CandleData, last: CandleData
) -> float:
    """Calculate strength of three-candle pattern"""
    avg_body = sum(c.body_size for c in [first, middle, last]) / 3
    avg_range = sum(c.total_range for c in [first, middle, last]) / 3
    return min(1.0, avg_body / avg_range) if avg_range > 0 else 0.0


def _is_stick_sandwich(
    first: CandleData, middle: CandleData, last: CandleData
) -> bool:
    """Check for stick sandwich pattern"""
    # First and third candles have similar closes
    close_similarity = abs(first.close - last.close) / first.close if first.close != 0 else 0
    if close_similarity > 0.002:  # Within 0.2%
        return False

    # Middle candle is opposite color and has higher/lower close
    if first.is_bullish:
        return middle.is_bearish and middle.close < first.close
    else:
        return middle.is_bullish and middle.close > first.close


def _calculate_stick_sandwich_confidence(
    first: CandleData, middle: CandleData, last: CandleData
) -> float:
    """Calculate confidence for stick sandwich pattern"""
    # Based on close similarity and middle candle conviction
    close_similarity = 1.0 - (abs(first.close - last.close) / first.close) if first.close != 0 else 0
    middle_conviction = middle.body_size / middle.total_range if middle.total_range > 0 else 0
    return min(1.0, (close_similarity + middle_conviction) / 2)