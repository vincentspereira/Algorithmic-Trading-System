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
        pattern_type, signal = _classify_marubozu(current)

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

    # Kangaroo Tail
    if _is_kangaroo_tail(current):
        signal = (
            PatternSignal.BULLISH
            if self.current_trend == "bearish"
            else PatternSignal.BEARISH
        )
        pattern_type = PatternType.KANGAROO_TAIL

        patterns.append(
            PatternResult(
                pattern_type=pattern_type,
                signal=signal,
                confidence=_calculate_kangaroo_tail_confidence(current),
                strength=_calculate_pattern_strength(current),
                reliability=PatternReliability.MEDIUM,
                trend_context=self.current_trend,
            )
        )

    return patterns


def _calculate_hammer_confidence(candle: CandleData) -> float:
    """Calculate confidence score for hammer/hanging man pattern"""
    body_size = candle.body_size
    lower_shadow = candle.lower_shadow
    upper_shadow = candle.upper_shadow
    total_range = candle.total_range

    if total_range == 0:
        return 0.0

    # Confidence based on shadow ratios
    shadow_ratio = lower_shadow / body_size if body_size > 0 else 0
    upper_shadow_ratio = upper_shadow / body_size if body_size > 0 else 0

    # Perfect hammer has long lower shadow, minimal upper shadow
    confidence = min(1.0, shadow_ratio / 3.0)  # Max confidence at 3:1 ratio
    confidence *= (1.0 - min(1.0, upper_shadow_ratio))  # Penalize upper shadow

    return max(0.0, min(1.0, confidence))


def _calculate_shooting_star_confidence(candle: CandleData) -> float:
    """Calculate confidence score for shooting star/inverted hammer pattern"""
    body_size = candle.body_size
    upper_shadow = candle.upper_shadow
    lower_shadow = candle.lower_shadow
    total_range = candle.total_range

    if total_range == 0:
        return 0.0

    # Confidence based on shadow ratios
    shadow_ratio = upper_shadow / body_size if body_size > 0 else 0
    lower_shadow_ratio = lower_shadow / body_size if body_size > 0 else 0

    # Perfect shooting star has long upper shadow, minimal lower shadow
    confidence = min(1.0, shadow_ratio / 3.0)  # Max confidence at 3:1 ratio
    confidence *= (1.0 - min(1.0, lower_shadow_ratio))  # Penalize lower shadow

    return max(0.0, min(1.0, confidence))


def _calculate_doji_confidence(candle: CandleData) -> float:
    """Calculate confidence score for doji pattern"""
    body_size = candle.body_size
    total_range = candle.total_range

    if total_range == 0:
        return 0.0

    # Doji confidence based on how small the body is relative to total range
    body_ratio = body_size / total_range
    confidence = 1.0 - min(1.0, body_ratio * 10)  # Higher confidence for smaller bodies

    return max(0.0, min(1.0, confidence))


def _calculate_marubozu_confidence(candle: CandleData) -> float:
    """Calculate confidence score for marubozu pattern"""
    body_size = candle.body_size
    total_range = candle.total_range

    if total_range == 0:
        return 0.0

    # Marubozu confidence based on body size relative to total range
    body_ratio = body_size / total_range
    confidence = min(1.0, body_ratio)  # Higher confidence for larger bodies

    return max(0.0, min(1.0, confidence))


def _calculate_pattern_strength(candle: CandleData) -> float:
    """Calculate overall pattern strength"""
    total_range = candle.total_range

    if total_range == 0:
        return 0.0

    # Strength based on total range (volatility)
    # Higher volatility generally means stronger patterns
    strength = min(1.0, total_range / candle.close * 10)  # Normalize by price

    return max(0.0, min(1.0, strength))


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


def _classify_marubozu(candle: CandleData) -> tuple:
    """Classify marubozu type and signal"""
    upper_shadow = candle.upper_shadow
    lower_shadow = candle.lower_shadow
    total_range = candle.total_range

    # Opening Marubozu (opens at low/high, no opposite shadow)
    if candle.is_bullish:
        if lower_shadow < total_range * 0.02:  # No lower shadow
            if upper_shadow < total_range * 0.02:  # No upper shadow
                return PatternType.MARUBOZU_WHITE, PatternSignal.BULLISH
            else:
                return PatternType.MARUBOZU_OPENING_WHITE, PatternSignal.BULLISH
        else:
            return PatternType.MARUBOZU_CLOSING_WHITE, PatternSignal.BULLISH
    else:  # Bearish
        if upper_shadow < total_range * 0.02:  # No upper shadow
            if lower_shadow < total_range * 0.02:  # No lower shadow
                return PatternType.MARUBOZU_BLACK, PatternSignal.BEARISH
            else:
                return PatternType.MARUBOZU_CLOSING_BLACK, PatternSignal.BEARISH
        else:
            return PatternType.MARUBOZU_OPENING_BLACK, PatternSignal.BEARISH


def _is_kangaroo_tail(candle: CandleData) -> bool:
    """Check if candle is kangaroo tail pattern"""
    body_size = candle.body_size
    lower_shadow = candle.lower_shadow
    upper_shadow = candle.upper_shadow
    total_range = candle.total_range

    # Small body (< 30% of total range)
    if body_size > total_range * 0.3:
        return False

    # Very long lower shadow (> 3x body size)
    if lower_shadow < body_size * 3:
        return False

    # Minimal upper shadow (< 20% of body size)
    if upper_shadow > body_size * 0.2:
        return False

    return True


def _calculate_kangaroo_tail_confidence(candle: CandleData) -> float:
    """Calculate confidence score for kangaroo tail pattern"""
    body_size = candle.body_size
    lower_shadow = candle.lower_shadow
    upper_shadow = candle.upper_shadow
    total_range = candle.total_range

    if total_range == 0:
        return 0.0

    # Confidence based on shadow ratios
    shadow_ratio = lower_shadow / body_size if body_size > 0 else 0
    upper_shadow_ratio = upper_shadow / body_size if body_size > 0 else 0

    # Perfect kangaroo tail has very long lower shadow, minimal upper shadow
    confidence = min(1.0, shadow_ratio / 4.0)  # Max confidence at 4:1 ratio
    confidence *= (1.0 - min(1.0, upper_shadow_ratio * 5))  # Penalize upper shadow

    return max(0.0, min(1.0, confidence))