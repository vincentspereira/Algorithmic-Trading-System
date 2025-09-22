"""
Institutional-Grade Augmented Parabolic SAR Indicator

This module implements an enhanced Parabolic SAR indicator with institutional-grade features:
- Volume confirmation scoring
- Market regime adaptation
- Multi-timeframe convergence
- Smart money detection
- Automated risk management
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime
from collections import deque
import statistics

from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import (
    AugmentedIndicator,
    AugmentedIndicatorConfig,
    IndicatorSignal,
    SignalType,
)


@dataclass
class AugmentedParabolicSARConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Parabolic SAR"""
    acceleration_factor: float = 0.02
    max_acceleration: float = 0.2
    initial_trend_threshold: float = 0.01


class AugmentedParabolicSAR(AugmentedIndicator):
    """
    Institutional-grade Augmented Parabolic SAR indicator implementing 5-pillar architecture.

    Features:
    - Trend direction analysis with acceleration-based stop levels
    - Entry/exit signal generation for institutional trading
    - Market regime adaptation based on trend strength
    - Multi-timeframe convergence for trend confirmation
    - Smart money trend analysis for institutional flow detection
    - Automated risk management for trend-following strategies
    """

    def __init__(self, config: AugmentedParabolicSARConfig = None):
        if config is None:
            config = AugmentedParabolicSARConfig()

        super().__init__(config)
        self.sar_config = config

        # Parabolic SAR specific state
        self._highs = deque(maxlen=self.config.buffer_size)
        self._lows = deque(maxlen=self.config.buffer_size)
        self._sar_values = deque(maxlen=self.config.buffer_size)
        self._current_sar = None

        # Trend analysis
        self._trend_direction = 0  # -1, 0, 1 for down, neutral, up
        self._trend_strength = 0.0
        self._trend_duration = 0

        # Acceleration analysis
        self._acceleration_factor = self.sar_config.acceleration_factor
        self._extreme_point = None  # Highest high or lowest low
        self._acceleration_points = []

        # Signal analysis
        self._entry_signals = 0
        self._exit_signals = 0
        self._reversal_signals = 0
        self._signal_confidence = 0.0

        # Market structure
        self._support_levels = []
        self._resistance_levels = []
        self._breakout_probability = 0.0

        # Institutional analysis
        self._institutional_trend = 0.0
        self._smart_money_alignment = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Parabolic SAR is ready to provide signals"""
        return len(self._sar_values) > 0 and self._current_sar is not None

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update Parabolic SAR analysis

        Args:
            bar (Bar): New bar data
        """
        # Extract OHLC data
        if hasattr(bar, 'high') and hasattr(bar, 'low'):
            high = bar.high
            low = bar.low
        else:
            high = bar.get('high', bar.get('close', 0.0))
            low = bar.get('low', bar.get('close', 0.0))

        # Update Parabolic SAR calculation
        self._update_parabolic_sar(high, low)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_parabolic_sar(self, high: float, low: float):
        """Update the core Parabolic SAR calculation with institutional enhancements"""
        self._highs.append(high)
        self._lows.append(low)

        if len(self._highs) < 2:
            # Initialize with first bar
            self._current_sar = low
            self._sar_values.append(self._current_sar)
            self._extreme_point = high
            return

        # Determine trend direction
        if self._trend_direction == 0:
            # Initialize trend based on first significant move
            price_change = high - self._lows[-2]
            if price_change > self.sar_config.initial_trend_threshold:
                self._trend_direction = 1  # Uptrend
                self._extreme_point = high
            elif self._lows[-2] - low > self.sar_config.initial_trend_threshold:
                self._trend_direction = -1  # Downtrend
                self._extreme_point = low

        # Calculate new SAR value
        if self._trend_direction == 1:  # Uptrend
            new_sar = self._current_sar + self._acceleration_factor * (self._extreme_point - self._current_sar)

            # Check for trend reversal
            if low <= new_sar:
                # Reversal to downtrend
                self._trend_direction = -1
                self._reversal_signals += 1
                self._extreme_point = low
                new_sar = self._extreme_point
                self._acceleration_factor = self.sar_config.acceleration_factor  # Reset acceleration

            # Update extreme point
            if high > self._extreme_point:
                self._extreme_point = high
                # Increase acceleration
                self._acceleration_factor = min(self._acceleration_factor + self.sar_config.acceleration_factor,
                                              self.sar_config.max_acceleration)

        elif self._trend_direction == -1:  # Downtrend
            new_sar = self._current_sar + self._acceleration_factor * (self._extreme_point - self._current_sar)

            # Check for trend reversal
            if high >= new_sar:
                # Reversal to uptrend
                self._trend_direction = 1
                self._reversal_signals += 1
                self._extreme_point = high
                new_sar = self._extreme_point
                self._acceleration_factor = self.sar_config.acceleration_factor  # Reset acceleration

            # Update extreme point
            if low < self._extreme_point:
                self._extreme_point = low
                # Increase acceleration
                self._acceleration_factor = min(self._acceleration_factor + self.sar_config.acceleration_factor,
                                              self.sar_config.max_acceleration)

        self._current_sar = new_sar
        self._sar_values.append(self._current_sar)

        # Analyze Parabolic SAR characteristics
        self._analyze_sar_characteristics(high, low)

    def _analyze_sar_characteristics(self, high: float, low: float):
        """Analyze Parabolic SAR characteristics for institutional insights"""
        if not self.is_ready or len(self._sar_values) < 3:
            return

        # Calculate trend strength
        if len(self._sar_values) >= 5:
            recent_sar = list(self._sar_values)[-5:]
            sar_trend = (recent_sar[-1] - recent_sar[0]) / 5

            if self._trend_direction == 1:
                self._trend_strength = min(1.0, abs(sar_trend) / (high * 0.01))  # Normalize by price
            elif self._trend_direction == -1:
                self._trend_strength = min(1.0, abs(sar_trend) / (low * 0.01))   # Normalize by price
            else:
                self._trend_strength = 0.0

        # Track trend duration
        if len(self._sar_values) >= 2:
            if self._trend_direction == list(self._sar_values)[-2:][0] - list(self._sar_values)[-2:][1] > 0:
                self._trend_duration += 1
            else:
                self._trend_duration = 1

        # Track acceleration points
        self._acceleration_points.append(self._acceleration_factor)

        # Calculate signal confidence
        if self._trend_strength > 0.5 and self._trend_duration >= 3:
            self._signal_confidence = min(1.0, self._trend_strength * (self._trend_duration / 10.0))
        else:
            self._signal_confidence = 0.0

        # Track support/resistance levels
        if self._trend_direction == 1:
            self._support_levels.append(self._current_sar)
            if len(self._support_levels) > 10:
                self._support_levels.pop(0)
        elif self._trend_direction == -1:
            self._resistance_levels.append(self._current_sar)
            if len(self._resistance_levels) > 10:
                self._resistance_levels.pop(0)

        # Calculate breakout probability
        if self._trend_strength > 0.7 and self._acceleration_factor > self.sar_config.max_acceleration * 0.8:
            self._breakout_probability = min(1.0, self._trend_strength * (self._acceleration_factor / self.sar_config.max_acceleration))
        else:
            self._breakout_probability = 0.0

        # Track entry/exit signals
        if len(self._sar_values) >= 2:
            prev_sar = self._sar_values[-2]

            if self._trend_direction == 1 and prev_sar > high and self._current_sar <= high:
                self._entry_signals += 1  # SAR crosses below price (buy signal)
            elif self._trend_direction == -1 and prev_sar < low and self._current_sar >= low:
                self._exit_signals += 1   # SAR crosses above price (sell signal)

        # Calculate institutional trend analysis
        self._calculate_institutional_trend()

    def _calculate_institutional_trend(self):
        """Calculate institutional trend analysis based on Parabolic SAR"""
        if not self.is_ready:
            return

        # Institutional traders use Parabolic SAR for trend following
        base_trend = 0.0

        if self._trend_strength > 0.6 and self._trend_duration >= 5:
            base_trend = 0.8  # Strong, established trend
        elif self._trend_strength > 0.4 and self._trend_duration >= 3:
            base_trend = 0.6  # Moderate trend
        elif self._trend_strength > 0.2:
            base_trend = 0.4  # Weak trend

        self._institutional_trend = base_trend

        # Smart money alignment considers trend strength and duration
        smart_money_score = (
            self._trend_strength * 0.4 +
            (self._trend_duration / 20.0) * 0.3 +
            self._signal_confidence * 0.3
        )
        self._smart_money_alignment = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade Parabolic SAR analysis"""
        if not self.is_ready:
            return IndicatorSignal(
                value_raw=0.0,
                signal_type=SignalType.NEUTRAL,
                composite_confidence=0.0,
                confidence_components={},
                suggested_sl=0.0,
                suggested_tp=0.0,
                metadata={"status": "not_ready"}
            )

        sar_value = self._current_sar

        # Determine signal type based on Parabolic SAR analysis
        signal_type = self._determine_sar_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'trend_strength': self._trend_strength,
            'trend_duration': self._trend_duration,
            'signal_confidence': self._signal_confidence,
            'breakout_probability': self._breakout_probability,
            'acceleration_factor': self._acceleration_factor,
            'institutional_trend': self._institutional_trend,
            'smart_money_alignment': self._smart_money_alignment
        }

        # Use SAR value as primary raw value
        raw_value = sar_value

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._suggested_sl,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Parabolic_SAR",
                "acceleration_factor": self.sar_config.acceleration_factor,
                "max_acceleration": self.sar_config.max_acceleration,
                "initial_trend_threshold": self.sar_config.initial_trend_threshold,
                "trend_direction": self._trend_direction,
                "trend_strength": self._trend_strength,
                "trend_duration": self._trend_duration,
                "acceleration_factor_current": self._acceleration_factor,
                "extreme_point": self._extreme_point,
                "entry_signals": self._entry_signals,
                "exit_signals": self._exit_signals,
                "reversal_signals": self._reversal_signals,
                "signal_confidence": self._signal_confidence,
                "breakout_probability": self._breakout_probability,
                "support_levels_count": len(self._support_levels),
                "resistance_levels_count": len(self._resistance_levels),
                "institutional_trend": self._institutional_trend,
                "smart_money_alignment": self._smart_money_alignment,
                "is_ready": self.is_ready
            }
        )

    def _determine_sar_signal(self) -> SignalType:
        """Determine signal type based on Parabolic SAR analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong trend signals
        if self._trend_strength > 0.7 and self._trend_duration >= 5:
            if self._trend_direction == 1:
                return SignalType.STRONG_BULLISH
            elif self._trend_direction == -1:
                return SignalType.STRONG_BEARISH

        # Moderate trend signals
        elif self._trend_strength > 0.5 and self._trend_duration >= 3:
            if self._trend_direction == 1:
                return SignalType.BULLISH
            elif self._trend_direction == -1:
                return SignalType.BEARISH

        # Reversal signals
        elif self._reversal_signals > 0 and self._signal_confidence > 0.6:
            if self._trend_direction == 1:
                return SignalType.BULLISH  # Reversal to uptrend
            elif self._trend_direction == -1:
                return SignalType.BEARISH  # Reversal to downtrend

        # Breakout signals
        elif self._breakout_probability > 0.6:
            if self._trend_direction == 1:
                return SignalType.BULLISH
            elif self._trend_direction == -1:
                return SignalType.BEARISH

        return SignalType.NEUTRAL

    @property
    def parabolic_sar(self) -> float:
        """Get the current Parabolic SAR value"""
        return self._current_sar if self.is_ready else 0.0

    @property
    def trend_direction(self) -> int:
        """Get the current trend direction (-1, 0, 1)"""
        return self._trend_direction

    @property
    def trend_strength(self) -> float:
        """Get the current trend strength (0-1)"""
        return self._trend_strength

    @property
    def trend_duration(self) -> int:
        """Get the current trend duration"""
        return self._trend_duration

    @property
    def acceleration_factor(self) -> float:
        """Get the current acceleration factor"""
        return self._acceleration_factor

    @property
    def extreme_point(self) -> float:
        """Get the current extreme point"""
        return self._extreme_point

    @property
    def entry_signals(self) -> int:
        """Get the count of entry signals"""
        return self._entry_signals

    @property
    def exit_signals(self) -> int:
        """Get the count of exit signals"""
        return self._exit_signals

    @property
    def reversal_signals(self) -> int:
        """Get the count of reversal signals"""
        return self._reversal_signals

    @property
    def signal_confidence(self) -> float:
        """Get the signal confidence (0-1)"""
        return self._signal_confidence

    @property
    def breakout_probability(self) -> float:
        """Get the breakout probability (0-1)"""
        return self._breakout_probability

    @property
    def support_levels(self) -> list:
        """Get the list of support levels"""
        return self._support_levels.copy()

    @property
    def resistance_levels(self) -> list:
        """Get the list of resistance levels"""
        return self._resistance_levels.copy()

    @property
    def institutional_trend(self) -> float:
        """Get the institutional trend score (0-1)"""
        return self._institutional_trend

    @property
    def smart_money_alignment(self) -> float:
        """Get the smart money alignment score (0-1)"""
        return self._smart_money_alignment

    def is_uptrend(self) -> bool:
        """Check if in uptrend"""
        if not self.is_ready:
            return False
        return self._trend_direction == 1

    def is_downtrend(self) -> bool:
        """Check if in downtrend"""
        if not self.is_ready:
            return False
        return self._trend_direction == -1

    def is_strong_trend(self) -> bool:
        """Check if trend is strong"""
        return self._trend_strength > 0.6

    def is_long_trend(self) -> bool:
        """Check if trend is long-lasting"""
        return self._trend_duration >= 5

    def is_accelerating(self) -> bool:
        """Check if trend is accelerating"""
        return self._acceleration_factor > self.sar_config.acceleration_factor * 2

    def is_breakout_likely(self) -> bool:
        """Check if breakout is likely"""
        return self._breakout_probability > 0.6

    def is_reversal_recent(self) -> bool:
        """Check if reversal occurred recently"""
        return self._reversal_signals > 0 and len(self._sar_values) <= 5

    def is_institutional_trend(self) -> bool:
        """Check if trend is institutional-grade"""
        return self._institutional_trend > 0.7

    def get_parabolic_sar_info(self) -> Dict[str, Any]:
        """Get comprehensive Parabolic SAR information"""
        return {
            "sar_value": self.parabolic_sar,
            "trend_analysis": {
                "direction": self._trend_direction,
                "strength": self._trend_strength,
                "duration": self._trend_duration
            },
            "acceleration_analysis": {
                "factor": self._acceleration_factor,
                "extreme_point": self._extreme_point,
                "acceleration_points": len(self._acceleration_points)
            },
            "signal_analysis": {
                "entry_signals": self._entry_signals,
                "exit_signals": self._exit_signals,
                "reversal_signals": self._reversal_signals,
                "signal_confidence": self._signal_confidence,
                "breakout_probability": self._breakout_probability
            },
            "market_structure": {
                "support_levels": len(self._support_levels),
                "resistance_levels": len(self._resistance_levels)
            },
            "institutional_analysis": {
                "trend": self._institutional_trend,
                "smart_money_alignment": self._smart_money_alignment
            },
            "metadata": {
                "acceleration_factor": self.sar_config.acceleration_factor,
                "max_acceleration": self.sar_config.max_acceleration,
                "initial_trend_threshold": self.sar_config.initial_trend_threshold,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._highs.clear()
        self._lows.clear()
        self._sar_values.clear()
        self._current_sar = None
        self._trend_direction = 0
        self._trend_strength = 0.0
        self._trend_duration = 0
        self._acceleration_factor = self.sar_config.acceleration_factor
        self._extreme_point = None
        self._acceleration_points.clear()
        self._entry_signals = 0
        self._exit_signals = 0
        self._reversal_signals = 0
        self._signal_confidence = 0.0
        self._support_levels.clear()
        self._resistance_levels.clear()
        self._breakout_probability = 0.0
        self._institutional_trend = 0.0
        self._smart_money_alignment = 0.0