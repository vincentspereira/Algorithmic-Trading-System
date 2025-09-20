"""
single_candle_patterns.py
"""

from nautilus_trader.indicators.data.candle import CandleData
from nautilus_trader.indicators.data.pattern import PatternResult
from nautilus_trader.indicators.enum.pattern import (
    PatternType,
    PatternSignal,
    PatternReliability,
)


def detect_single_candle_patterns(self) -> list[PatternResult]:
    """Detect single candle patterns"""
    patterns = []
    current = self.candle_history[-1]

    # Hammer / Hanging Man
    if _is_hammer_hanging_man(current):
        signal = (
            PatternSignal.BULLISH
            if self.current_trend == "bearish"
            else PatternSignal.BEARISH
        )
        pattern_type = (
            PatternType.HAMMER if signal == PatternSignal.BULLISH else PatternType.HANGING_MAN
        )

        patterns.append(
            PatternResult(
                pattern_type=pattern_type,
                signal=signal,
                confidence=_calculate_hammer_confidence(current),
                strength=_calculate_pattern_strength(current),
                reliability=PatternReliability.HIGH,
                trend_context=self.current_trend,
            )
        )

    # Shooting Star / Inverted Hammer
    if _is_shooting_star_inverted_hammer(current):
        signal = (
            PatternSignal.BEARISH
            if self.current_trend == "bullish"
            else PatternSignal.BULLISH
        )
        pattern_type = (
            PatternType.SHOOTING_STAR
            if signal == PatternSignal.BEARISH
            else PatternType.INVERTED_HAMMER
        )

        patterns.append(
            PatternResult(
                pattern_type=pattern_type,
                signal=signal,
                confidence=_calculate_shooting_star_confidence(current),
                strength=_calculate_pattern_strength(current),
                reliability=PatternReliability.MEDIUM,
                trend_context=self.current_trend,
            )
        )

    # Doji patterns
    if current.is_doji:
        doji_type = _classify_doji(current)
        patterns.append(
            PatternResult(
                pattern_type=doji_type,
                signal=PatternSignal.NEUTRAL,
                confidence=_calculate_doji_confidence(current),
                strength=_calculate_pattern_strength(current),
                reliability=PatternReliability.MEDIUM,
                trend_context=self.current_trend,
            )
        )

    # Marubozu patterns
    if _is_marubozu(current):
        pattern_type = (
            PatternType.MARUBOZU_BULLISH
            if current.is_bullish
            else PatternType.MARUBOZU_BEARISH
        )
        signal = (
            PatternSignal.BULLISH if current.is_bullish else PatternSignal.BEARISH
        )

        patterns.append(
            PatternResult(
                pattern_type=pattern_type,
                signal=signal,
                confidence=_calculate_marubozu_confidence(current),
                strength=_calculate_pattern_strength(current),
                reliability=PatternReliability.HIGH,
                trend_context=self.current_trend,
            )
        )

    return patterns

def _is_hammer_hanging_man(candle: CandleData) -> bool:
    """Check if candle is hammer or hanging man"""
    body_size = candle.body_size
    lower_shadow = candle.lower_shadow
    upper_shadow = candle.upper_shadow
    total_range = candle.total_range

    # Small body (< 30% of total range)
    if body_size > total_range * 0.3:
        return False

    # Long lower shadow (> 2x body size)
    if lower_shadow < body_size * 2:
        return False

    # Short upper shadow (< 50% of body size)
    if upper_shadow > body_size * 0.5:
        return False

    return True

def _is_shooting_star_inverted_hammer(candle: CandleData) -> bool:
    """Check if candle is shooting star or inverted hammer"""
    body_size = candle.body_size
    lower_shadow = candle.lower_shadow
    upper_shadow = candle.upper_shadow
    total_range = candle.total_range

    # Small body (< 30% of total range)
    if body_size > total_range * 0.3:
        return False

    # Long upper shadow (> 2x body size)
    if upper_shadow < body_size * 2:
        return False

    # Short lower shadow (< 50% of body size)
    if lower_shadow > body_size * 0.5:
        return False

    return True

def _classify_doji(candle: CandleData) -> PatternType:
    """Classify type of doji"""
    upper_shadow = candle.upper_shadow
    lower_shadow = candle.lower_shadow
    total_range = candle.total_range

    # Dragonfly Doji (long lower shadow, no upper shadow)
    if lower_shadow > total_range * 0.6 and upper_shadow < total_range * 0.1:
        return PatternType.DRAGONFLY_DOJI

    # Gravestone Doji (long upper shadow, no lower shadow)
    if upper_shadow > total_range * 0.6 and lower_shadow < total_range * 0.1:
        return PatternType.GRAVESTONE_DOJI

    # Regular Doji
    return PatternType.DOJI

def _is_marubozu(candle: CandleData) -> bool:
    """Check if candle is marubozu (no shadows)"""
    body_size = candle.body_size
    total_range = candle.total_range

    # Body should be > 95% of total range
    return body_size > total_range * 0.95