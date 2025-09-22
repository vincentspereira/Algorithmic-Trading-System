"""
Institutional-Grade Augmented Coppock Curve Indicator

This module implements an enhanced Coppock Curve indicator with institutional-grade features:
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
class AugmentedCoppockConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Coppock Curve"""
    short_roc_period: int = 11
    long_roc_period: int = 14
    wma_period: int = 10
    signal_threshold: float = 0.0  # Coppock signal threshold


class AugmentedCoppockCurve(AugmentedIndicator):
    """
    Institutional-grade Augmented Coppock Curve indicator implementing 5-pillar architecture.

    Features:
    - Long-term momentum analysis for major market turns
    - ROC combination with WMA smoothing for trend identification
    - Market regime adaptation for different time horizons
    - Multi-timeframe convergence for confirmation
    - Smart money flow analysis for institutional activity
    - Automated risk management for long-term positions
    """

    def __init__(self, config: AugmentedCoppockConfig = None):
        if config is None:
            config = AugmentedCoppockConfig()

        super().__init__(config)
        self.coppock_config = config

        # Coppock Curve specific state
        self._prices = deque(maxlen=self.config.buffer_size)
        self._short_roc_values = deque(maxlen=self.config.buffer_size)
        self._long_roc_values = deque(maxlen=self.config.buffer_size)
        self._roc_sum_values = deque(maxlen=self.config.buffer_size)
        self._coppock_values = deque(maxlen=self.config.buffer_size)
        self._current_coppock = None

        # Trend analysis
        self._trend_direction = 0  # -1, 0, 1 for down, sideways, up
        self._trend_strength = 0.0
        self._momentum_phase = "neutral"  # "accumulation", "bullish", "distribution", "bearish"

        # Signal analysis
        self._signal_strength = 0.0
        self._confirmation_count = 0
        self._last_signal = "none"  # "buy", "sell", "none"

        # Market timing
        self._market_bottom_probability = 0.0
        self._market_top_probability = 0.0
        self._timing_confidence = 0.0

        # Institutional analysis
        self._institutional_alignment = 0.0
        self._smart_money_confirmation = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Coppock Curve is ready to provide signals"""
        return len(self._coppock_values) > 0 and self._current_coppock is not None

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update Coppock Curve analysis

        Args:
            bar (Bar): New bar data
        """
        # Extract price
        if hasattr(bar, 'close'):
            price = bar.close
        else:
            price = bar.get('close', bar.get('price', 0.0))

        # Update Coppock Curve calculation
        self._update_coppock_curve(price)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_coppock_curve(self, price: float):
        """Update the core Coppock Curve calculation with institutional enhancements"""
        self._prices.append(price)

        # Need sufficient data for both ROC periods
        max_period = max(self.coppock_config.short_roc_period, self.coppock_config.long_roc_period)
        if len(self._prices) >= max_period + 1:
            # Calculate short ROC
            short_past_price = self._prices[-self.coppock_config.short_roc_period - 1]
            if short_past_price > 0:
                short_roc = ((price - short_past_price) / short_past_price) * 100
                self._short_roc_values.append(short_roc)

            # Calculate long ROC
            long_past_price = self._prices[-self.coppock_config.long_roc_period - 1]
            if long_past_price > 0:
                long_roc = ((price - long_past_price) / long_past_price) * 100
                self._long_roc_values.append(long_roc)

            # Calculate ROC sum
            if self._short_roc_values and self._long_roc_values:
                roc_sum = self._short_roc_values[-1] + self._long_roc_values[-1]
                self._roc_sum_values.append(roc_sum)

                # Apply WMA smoothing
                if len(self._roc_sum_values) >= self.coppock_config.wma_period:
                    wma_sum = self._calculate_wma(self._roc_sum_values, self.coppock_config.wma_period)
                    self._current_coppock = wma_sum
                    self._coppock_values.append(self._current_coppock)

                    # Analyze Coppock characteristics
                    self._analyze_coppock_characteristics()

    def _calculate_wma(self, values: deque, period: int) -> float:
        """Calculate Weighted Moving Average"""
        if len(values) < period:
            return 0.0

        weights = list(range(1, period + 1))  # 1, 2, 3, ..., period
        recent_values = list(values)[-period:]

        weighted_sum = sum(value * weight for value, weight in zip(recent_values, weights))
        total_weight = sum(weights)

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _analyze_coppock_characteristics(self):
        """Analyze Coppock Curve characteristics for institutional insights"""
        if not self.is_ready or len(self._coppock_values) < 3:
            return

        coppock_value = self._current_coppock

        # Determine trend direction and strength
        recent_coppock = list(self._coppock_values)[-3:]
        slope = (recent_coppock[-1] - recent_coppock[0]) / 3

        if slope > 0.01:
            self._trend_direction = 1  # Uptrend
            self._trend_strength = min(1.0, slope / 0.05)  # Normalize
        elif slope < -0.01:
            self._trend_direction = -1  # Downtrend
            self._trend_strength = min(1.0, abs(slope) / 0.05)  # Normalize
        else:
            self._trend_direction = 0  # Sideways
            self._trend_strength = 0.0

        # Determine momentum phase
        if coppock_value > 5.0:
            self._momentum_phase = "bullish"
        elif coppock_value < -5.0:
            self._momentum_phase = "bearish"
        elif coppock_value > 0:
            self._momentum_phase = "accumulation"
        else:
            self._momentum_phase = "distribution"

        # Calculate signal strength
        self._signal_strength = min(1.0, abs(coppock_value) / 10.0)

        # Calculate market timing probabilities
        if coppock_value < -10.0:
            # Potential market bottom
            self._market_bottom_probability = min(1.0, abs(coppock_value) / 20.0)
            self._market_top_probability = 0.0
        elif coppock_value > 10.0:
            # Potential market top
            self._market_top_probability = min(1.0, coppock_value / 20.0)
            self._market_bottom_probability = 0.0
        else:
            self._market_bottom_probability = 0.0
            self._market_top_probability = 0.0

        # Calculate timing confidence
        if len(self._coppock_values) >= 5:
            recent_values = list(self._coppock_values)[-5:]
            consistency = 1.0 - (statistics.stdev(recent_values) / abs(sum(recent_values) / len(recent_values)))
            self._timing_confidence = max(0.0, min(1.0, consistency))

        # Track signal confirmation
        self._update_signal_confirmation()

        # Calculate institutional alignment
        self._calculate_institutional_alignment()

    def _update_signal_confirmation(self):
        """Update signal confirmation tracking"""
        if not self.is_ready:
            return

        coppock_value = self._current_coppock

        # Buy signal (Coppock crosses above threshold from below)
        if (coppock_value > self.coppock_config.signal_threshold and
            len(self._coppock_values) >= 2 and
            self._coppock_values[-2] <= self.coppock_config.signal_threshold):
            self._last_signal = "buy"
            self._confirmation_count += 1

        # Sell signal (Coppock crosses below threshold from above)
        elif (coppock_value < self.coppock_config.signal_threshold and
              len(self._coppock_values) >= 2 and
              self._coppock_values[-2] >= self.coppock_config.signal_threshold):
            self._last_signal = "sell"
            self._confirmation_count += 1

        else:
            self._last_signal = "none"

    def _calculate_institutional_alignment(self):
        """Calculate alignment with institutional market timing"""
        if not self.is_ready:
            return

        # Institutional investors often follow Coppock signals for long-term positioning
        # High confidence when Coppock shows strong directional movement
        if abs(self._current_coppock) > 5.0 and self._trend_strength > 0.6:
            self._institutional_alignment = 0.8
        elif abs(self._current_coppock) > 2.0:
            self._institutional_alignment = 0.6
        else:
            self._institutional_alignment = 0.4

        # Smart money confirmation based on signal consistency
        self._smart_money_confirmation = self._timing_confidence * self._institutional_alignment

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade Coppock Curve analysis"""
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

        coppock_value = self._current_coppock

        # Determine signal type based on Coppock analysis
        signal_type = self._determine_coppock_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'trend_strength': self._trend_strength,
            'signal_strength': self._signal_strength,
            'timing_confidence': self._timing_confidence,
            'institutional_alignment': self._institutional_alignment,
            'smart_money_confirmation': self._smart_money_confirmation
        }

        # Use Coppock value as primary raw value
        raw_value = coppock_value

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._suggested_sl,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Coppock_Curve",
                "short_roc_period": self.coppock_config.short_roc_period,
                "long_roc_period": self.coppock_config.long_roc_period,
                "wma_period": self.coppock_config.wma_period,
                "signal_threshold": self.coppock_config.signal_threshold,
                "trend_direction": self._trend_direction,
                "trend_strength": self._trend_strength,
                "momentum_phase": self._momentum_phase,
                "signal_strength": self._signal_strength,
                "last_signal": self._last_signal,
                "confirmation_count": self._confirmation_count,
                "market_bottom_probability": self._market_bottom_probability,
                "market_top_probability": self._market_top_probability,
                "timing_confidence": self._timing_confidence,
                "institutional_alignment": self._institutional_alignment,
                "smart_money_confirmation": self._smart_money_confirmation,
                "is_ready": self.is_ready
            }
        )

    def _determine_coppock_signal(self) -> SignalType:
        """Determine signal type based on Coppock Curve analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        coppock_value = self._current_coppock

        # Strong buy signals (market bottom)
        if (coppock_value < -10.0 and
            self._market_bottom_probability > 0.7 and
            self._timing_confidence > 0.6):
            return SignalType.STRONG_BULLISH

        # Strong sell signals (market top)
        elif (coppock_value > 10.0 and
              self._market_top_probability > 0.7 and
              self._timing_confidence > 0.6):
            return SignalType.STRONG_BEARISH

        # Moderate buy signals
        elif coppock_value < -5.0 and self._last_signal == "buy":
            return SignalType.BULLISH

        # Moderate sell signals
        elif coppock_value > 5.0 and self._last_signal == "sell":
            return SignalType.BEARISH

        # Bullish momentum phase
        elif self._momentum_phase == "bullish" and self._trend_strength > 0.5:
            return SignalType.BULLISH

        # Bearish momentum phase
        elif self._momentum_phase == "bearish" and self._trend_strength > 0.5:
            return SignalType.BEARISH

        return SignalType.NEUTRAL

    @property
    def coppock_curve(self) -> float:
        """Get the current Coppock Curve value"""
        return self._current_coppock if self.is_ready else 0.0

    @property
    def trend_direction(self) -> int:
        """Get the current trend direction (-1, 0, 1)"""
        return self._trend_direction

    @property
    def trend_strength(self) -> float:
        """Get the current trend strength (0-1)"""
        return self._trend_strength

    @property
    def momentum_phase(self) -> str:
        """Get the current momentum phase"""
        return self._momentum_phase

    @property
    def signal_strength(self) -> float:
        """Get the current signal strength (0-1)"""
        return self._signal_strength

    @property
    def last_signal(self) -> str:
        """Get the last signal generated"""
        return self._last_signal

    @property
    def confirmation_count(self) -> int:
        """Get the signal confirmation count"""
        return self._confirmation_count

    @property
    def market_bottom_probability(self) -> float:
        """Get the market bottom probability (0-1)"""
        return self._market_bottom_probability

    @property
    def market_top_probability(self) -> float:
        """Get the market top probability (0-1)"""
        return self._market_top_probability

    @property
    def timing_confidence(self) -> float:
        """Get the timing confidence (0-1)"""
        return self._timing_confidence

    @property
    def institutional_alignment(self) -> float:
        """Get the institutional alignment score (0-1)"""
        return self._institutional_alignment

    @property
    def smart_money_confirmation(self) -> float:
        """Get the smart money confirmation score (0-1)"""
        return self._smart_money_confirmation

    def is_market_bottom_signal(self) -> bool:
        """Check if Coppock indicates a potential market bottom"""
        return self._market_bottom_probability > 0.6

    def is_market_top_signal(self) -> bool:
        """Check if Coppock indicates a potential market top"""
        return self._market_top_probability > 0.6

    def is_bullish_phase(self) -> bool:
        """Check if in bullish momentum phase"""
        return self._momentum_phase == "bullish"

    def is_bearish_phase(self) -> bool:
        """Check if in bearish momentum phase"""
        return self._momentum_phase == "bearish"

    def get_coppock_info(self) -> Dict[str, Any]:
        """Get comprehensive Coppock Curve information"""
        return {
            "coppock_value": self.coppock_curve,
            "trend_analysis": {
                "direction": self._trend_direction,
                "strength": self._trend_strength,
                "phase": self._momentum_phase
            },
            "signal_analysis": {
                "strength": self._signal_strength,
                "last_signal": self._last_signal,
                "confirmation_count": self._confirmation_count
            },
            "market_timing": {
                "bottom_probability": self._market_bottom_probability,
                "top_probability": self._market_top_probability,
                "timing_confidence": self._timing_confidence
            },
            "institutional_analysis": {
                "alignment": self._institutional_alignment,
                "smart_money_confirmation": self._smart_money_confirmation
            },
            "metadata": {
                "short_roc_period": self.coppock_config.short_roc_period,
                "long_roc_period": self.coppock_config.long_roc_period,
                "wma_period": self.coppock_config.wma_period,
                "signal_threshold": self.coppock_config.signal_threshold,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._prices.clear()
        self._short_roc_values.clear()
        self._long_roc_values.clear()
        self._roc_sum_values.clear()
        self._coppock_values.clear()
        self._current_coppock = None
        self._trend_direction = 0
        self._trend_strength = 0.0
        self._momentum_phase = "neutral"
        self._signal_strength = 0.0
        self._confirmation_count = 0
        self._last_signal = "none"
        self._market_bottom_probability = 0.0
        self._market_top_probability = 0.0
        self._timing_confidence = 0.0
        self._institutional_alignment = 0.0
        self._smart_money_confirmation = 0.0