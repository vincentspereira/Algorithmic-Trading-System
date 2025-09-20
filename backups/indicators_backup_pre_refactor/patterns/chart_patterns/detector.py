"""
Consolidated Pattern Detector
"""

from collections import deque
from typing import Optional, Dict

from nautilus_trader.indicators.base.indicator import Indicator
from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.patterns.chart_patterns.base import (
    PatternType,
    PatternStrength,
    VolumeProfile,
    PatternAnalysis,
    CandleProperties,
)
from nautilus_trader_engine.indicators.patterns.chart_patterns.single_candle_patterns import (
    detect_hammer,
    detect_hanging_man,
    detect_inverted_hammer,
    detect_shooting_star,
    detect_doji,
    detect_marubozu,
)
from nautilus_trader_engine.indicators.patterns.chart_patterns.two_candle_patterns import (
    detect_bullish_engulfing,
    detect_bearish_engulfing,
    detect_bullish_harami,
    detect_bearish_harami,
    detect_piercing_line,
    detect_dark_cloud_cover,
    detect_tweezer_top,
    detect_tweezer_bottom,
    detect_kicking_bullish,
    detect_kicking_bearish,
)
from nautilus_trader_engine.indicators.patterns.chart_patterns.three_candle_patterns import (
    detect_morning_star,
    detect_evening_star,
    detect_three_white_soldiers,
    detect_three_black_crows,
    detect_three_inside_up,
    detect_three_inside_down,
    detect_three_outside_up,
    detect_three_outside_down,
    detect_bullish_abandoned_baby,
    detect_bearish_abandoned_baby,
)
from nautilus_trader_engine.indicators.patterns.chart_patterns.complex_patterns import (
    detect_hikkake,
    detect_mat_hold,
)


class ConsolidatedPatternDetector(Indicator):
    """
    A consolidated pattern recognition indicator that detects a variety of candlestick patterns.
    """

    def __init__(
        self,
        volume_lookback: int = 20,
        name: str = "PatternDetector",
    ):
        super().__init__(name=name)
        self.volume_lookback = volume_lookback
        self.candle_history = deque(maxlen=5)  # Store last 5 candles
        self.volume_history = deque(maxlen=volume_lookback)

    def calculate(self, bar: Bar):
        """
        Main pattern detection method.
        """
        current_candle = CandleProperties(
            bar.open, bar.high, bar.low, bar.close, bar.volume
        )
        self.candle_history.append(current_candle)
        self.volume_history.append(bar.volume)

        detected_patterns = []

        # Single candle patterns
        detected_patterns.extend(self._detect_single_candle_patterns(current_candle))

        # Two candle patterns
        if len(self.candle_history) >= 2:
            detected_patterns.extend(self._detect_two_candle_patterns())

        # Three candle patterns
        if len(self.candle_history) >= 3:
            detected_patterns.extend(self._detect_three_candle_patterns())

        # Complex patterns
        if len(self.candle_history) >= 4:
            detected_patterns.extend(self._detect_complex_patterns())

        # Filter and rank patterns by confidence
        significant_patterns = [
            p for p in detected_patterns if p.detected and p.confidence > 0.5
        ]

        if not significant_patterns:
            return None

        # Get the highest confidence pattern
        best_pattern = max(significant_patterns, key=lambda x: x.confidence)

        return best_pattern

    def _detect_single_candle_patterns(self, current_candle):
        patterns = []
        avg_volume = (
            sum(self.volume_history) / len(self.volume_history)
            if self.volume_history
            else 0
        )
        patterns.append(detect_hammer(current_candle, avg_volume))
        patterns.append(detect_hanging_man(current_candle, avg_volume))
        patterns.append(detect_inverted_hammer(current_candle, avg_volume))
        patterns.append(detect_shooting_star(current_candle, avg_volume))
        patterns.append(detect_doji(current_candle, avg_volume))
        patterns.append(detect_marubozu(current_candle, avg_volume))
        return patterns

    def _detect_two_candle_patterns(self):
        patterns = []
        c1, c2 = self.candle_history[-2], self.candle_history[-1]
        avg_volume = (
            sum(self.volume_history) / len(self.volume_history)
            if self.volume_history
            else 0
        )
        patterns.append(detect_bullish_engulfing(c1, c2, avg_volume))
        patterns.append(detect_bearish_engulfing(c1, c2, avg_volume))
        patterns.append(detect_bullish_harami(c1, c2, avg_volume))
        patterns.append(detect_bearish_harami(c1, c2, avg_volume))
        patterns.append(detect_piercing_line(c1, c2, avg_volume))
        patterns.append(detect_dark_cloud_cover(c1, c2, avg_volume))
        patterns.append(detect_tweezer_top(c1, c2, avg_volume))
        patterns.append(detect_tweezer_bottom(c1, c2, avg_volume))
        patterns.append(detect_kicking_bullish(c1, c2, avg_volume))
        patterns.append(detect_kicking_bearish(c1, c2, avg_volume))
        return patterns

    def _detect_three_candle_patterns(self):
        patterns = []
        c1, c2, c3 = (
            self.candle_history[-3],
            self.candle_history[-2],
            self.candle_history[-1],
        )
        avg_volume = (
            sum(self.volume_history) / len(self.volume_history)
            if self.volume_history
            else 0
        )
        patterns.append(detect_morning_star(c1, c2, c3, avg_volume))
        patterns.append(detect_evening_star(c1, c2, c3, avg_volume))
        patterns.append(detect_three_white_soldiers(c1, c2, c3, avg_volume))
        patterns.append(detect_three_black_crows(c1, c2, c3, avg_volume))
        patterns.append(detect_three_inside_up(c1, c2, c3, avg_volume))
        patterns.append(detect_three_inside_down(c1, c2, c3, avg_volume))
        patterns.append(detect_three_outside_up(c1, c2, c3, avg_volume))
        patterns.append(detect_three_outside_down(c1, c2, c3, avg_volume))
        patterns.append(detect_bullish_abandoned_baby(c1, c2, c3, avg_volume))
        patterns.append(detect_bearish_abandoned_baby(c1, c2, c3, avg_volume))
        return patterns

    def _detect_complex_patterns(self):
        patterns = []
        candles = list(self.candle_history)
        avg_volume = (
            sum(self.volume_history) / len(self.volume_history)
            if self.volume_history
            else 0
        )
        if len(candles) >= 4:
            patterns.append(detect_hikkake(candles, avg_volume))
        if len(candles) >= 5:
            patterns.append(detect_mat_hold(candles, avg_volume))
        return patterns