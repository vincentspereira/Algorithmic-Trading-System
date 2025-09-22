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

    # Harami patterns
    if _is_bullish_harami(previous, current):
        patterns.append(
            PatternResult(
                pattern_type=PatternType.BULLISH_HARAMI,
                signal=PatternSignal.BULLISH,
                confidence=_calculate_harami_confidence(previous, current),
                strength=_calculate_two_candle_strength(previous, current),
                reliability=PatternReliability.MEDIUM,
                trend_context=self.current_trend,
                candles_analyzed=2,
            )
        )

    if _is_bearish_harami(previous, current):
        patterns.append(
            PatternResult(
                pattern_type=PatternType.BEARISH_HARAMI,
                signal=PatternSignal.BEARISH,
                confidence=_calculate_harami_confidence(previous, current),
                strength=_calculate_two_candle_strength(previous, current),
                reliability=PatternReliability.MEDIUM,
                trend_context=self.current_trend,
                candles_analyzed=2,
            )
        )

    # Meeting Lines patterns
    if _is_bullish_meeting_lines(previous, current):
        patterns.append(
            PatternResult(
                pattern_type=PatternType.BULLISH_MEETING_LINES,
                signal=PatternSignal.BULLISH,
                confidence=_calculate_meeting_lines_confidence(previous, current),
                strength=_calculate_two_candle_strength(previous, current),
                reliability=PatternReliability.MEDIUM,
                trend_context=self.current_trend,
                candles_analyzed=2,
            )
        )

    if _is_bearish_meeting_lines(previous, current):
        patterns.append(
            PatternResult(
                pattern_type=PatternType.BEARISH_MEETING_LINES,
                signal=PatternSignal.BEARISH,
                confidence=_calculate_meeting_lines_confidence(previous, current),
                strength=_calculate_two_candle_strength(previous, current),
                reliability=PatternReliability.MEDIUM,
                trend_context=self.current_trend,
                candles_analyzed=2,
            )
        )

    # Stick Sandwich
    if _is_stick_sandwich(previous, current):
        signal = (
            PatternSignal.BULLISH
            if self.current_trend == "bearish"
            else PatternSignal.BEARISH
        )
        patterns.append(
            PatternResult(
                pattern_type=PatternType.STICK_SANDWICH,
                signal=signal,
                confidence=_calculate_stick_sandwich_confidence(previous, current),
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


def _is_bullish_harami(prev: CandleData, curr: CandleData) -> bool:
    """Check for bullish harami pattern"""
    if not (prev.is_bearish and curr.is_bullish):
        return False

    # Current candle is completely contained within previous candle
    return curr.open > prev.close and curr.close < prev.open


def _is_bearish_harami(prev: CandleData, curr: CandleData) -> bool:
    """Check for bearish harami pattern"""
    if not (prev.is_bullish and curr.is_bearish):
        return False

    # Current candle is completely contained within previous candle
    return curr.open < prev.close and curr.close > prev.open


def _calculate_engulfing_confidence(prev: CandleData, curr: CandleData) -> float:
    """Calculate confidence for engulfing patterns"""
    engulfing_ratio = curr.body_size / prev.body_size if prev.body_size > 0 else 0
    return min(1.0, engulfing_ratio / 2.0)  # Max confidence at 2:1 ratio


def _calculate_tweezer_confidence(prev: CandleData, curr: CandleData) -> float:
    """Calculate confidence for tweezer patterns"""
    # Based on how close the highs/lows are
    if prev.is_bullish and curr.is_bearish:  # Tweezer top
        diff = abs(prev.high - curr.high) / prev.high
        return max(0.0, 1.0 - diff * 100)  # Closer highs = higher confidence
    else:  # Tweezer bottom
        diff = abs(prev.low - curr.low) / prev.low
        return max(0.0, 1.0 - diff * 100)


def _calculate_piercing_confidence(prev: CandleData, curr: CandleData) -> float:
    """Calculate confidence for piercing pattern"""
    if not (prev.is_bearish and curr.is_bullish):
        return 0.0

    # How deep the penetration into previous candle
    penetration = (curr.close - prev.low) / prev.body_size if prev.body_size > 0 else 0
    return min(1.0, penetration)


def _calculate_dark_cloud_confidence(prev: CandleData, curr: CandleData) -> float:
    """Calculate confidence for dark cloud cover pattern"""
    if not (prev.is_bullish and curr.is_bearish):
        return 0.0

    # How deep the penetration into previous candle
    penetration = (prev.high - curr.close) / prev.body_size if prev.body_size > 0 else 0
    return min(1.0, penetration)


def _calculate_harami_confidence(prev: CandleData, curr: CandleData) -> float:
    """Calculate confidence for harami patterns"""
    # Based on how well the smaller candle is contained
    containment = 1.0 - (curr.body_size / prev.body_size) if prev.body_size > 0 else 0
    return min(1.0, containment)


def _calculate_two_candle_strength(prev: CandleData, curr: CandleData) -> float:
    """Calculate strength of two-candle pattern"""
    avg_body = (prev.body_size + curr.body_size) / 2
    avg_range = (prev.total_range + curr.total_range) / 2
    return min(1.0, avg_body / avg_range) if avg_range > 0 else 0.0


def _is_bullish_meeting_lines(prev: CandleData, curr: CandleData) -> bool:
    """Check for bullish meeting lines pattern"""
    if not (prev.is_bearish and curr.is_bullish):
        return False

    # Closes are nearly equal (within 0.1% of previous close)
    close_diff = abs(prev.close - curr.close) / prev.close
    return close_diff < 0.001


def _is_bearish_meeting_lines(prev: CandleData, curr: CandleData) -> bool:
    """Check for bearish meeting lines pattern"""
    if not (prev.is_bullish and curr.is_bearish):
        return False

    # Closes are nearly equal (within 0.1% of previous close)
    close_diff = abs(prev.close - curr.close) / prev.close
    return close_diff < 0.001


def _is_stick_sandwich(prev: CandleData, curr: CandleData) -> bool:
    """Check for stick sandwich pattern"""
    # Three candles needed, but we check for the sandwich part
    # This is a simplified version - ideally needs 3 candles
    if not prev.is_bearish:
        return False

    # Current candle should be bullish with close near previous close
    if not curr.is_bullish:
        return False

    close_diff = abs(prev.close - curr.close) / prev.close
    return close_diff < 0.005  # Within 0.5% of previous close


def _calculate_meeting_lines_confidence(prev: CandleData, curr: CandleData) -> float:
    """Calculate confidence for meeting lines patterns"""
    # Based on how close the closes are
    close_diff = abs(prev.close - curr.close) / prev.close
    return max(0.0, 1.0 - close_diff * 1000)  # Closer closes = higher confidence


def _calculate_stick_sandwich_confidence(prev: CandleData, curr: CandleData) -> float:
    """Calculate confidence for stick sandwich pattern"""
    # Based on close proximity and body sizes
    close_diff = abs(prev.close - curr.close) / prev.close
    body_ratio = curr.body_size / prev.body_size if prev.body_size > 0 else 0
    return min(1.0, (1.0 - close_diff * 200) * min(1.0, body_ratio))