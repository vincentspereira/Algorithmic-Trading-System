"""
Institutional-Grade Augmented Supertrend Indicator

This module implements an enhanced Supertrend indicator with institutional-grade features:
- Volume confirmation scoring
- Market regime adaptation
- Multi-timeframe convergence
- Smart money detection
- Automated risk management
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import deque
import statistics

from nautilus_trader_engine.indicators.base import (
    AugmentedIndicator,
    AugmentedIndicatorConfig,
    IndicatorSignal,
    SignalType,
)


@dataclass
class AugmentedSupertrendConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Supertrend Indicator"""
    period: int = 10
    multiplier: float = 3.0
    adaptive_multiplier: bool = True
    volume_weighted: bool = True


class AugmentedSupertrendIndicator(AugmentedIndicator):
    """
    Institutional-grade Augmented Supertrend Indicator implementing 5-pillar architecture.

    Features:
    - ATR-based trend following with dynamic stops
    - Volume confirmation for trend validation
    - Market regime adaptation for different volatility environments
    - Multi-timeframe convergence for institutional confirmation
    - Smart money trend detection and validation
    - Automated risk management with trailing stops
    """

    def __init__(self, config: AugmentedSupertrendConfig = None):
        if config is None:
            config = AugmentedSupertrendConfig()

        super().__init__(config)
        self.supertrend_config = config

        # Supertrend specific state
        self._high_values = deque(maxlen=self.config.buffer_size)
        self._low_values = deque(maxlen=self.config.buffer_size)
        self._close_values = deque(maxlen=self.config.buffer_size)
        self._volume_values = deque(maxlen=self.config.buffer_size)

        # ATR calculation for dynamic bands
        self._atr_values = deque(maxlen=self.config.buffer_size)
        self._true_ranges = deque(maxlen=self.config.buffer_size)

        # Supertrend bands
        self._upper_band = 0.0
        self._lower_band = 0.0
        self._supertrend_value = 0.0

        # Trend direction
        self._trend_direction = 0  # 1 = uptrend, -1 = downtrend, 0 = neutral
        self._previous_trend = 0

        # Signal analysis
        self._trend_signals = 0
        self._reversal_signals = 0
        self._continuation_signals = 0
        self._breakout_signals = 0

        # Performance tracking
        self._trend_accuracy = 0.0
        self._reversal_success_rate = 0.0
        self._signal_strength = 0.0

        # Market structure
        self._trend_duration = 0
        self._volatility_regime = "normal"
        self._support_resistance_levels = []

        # Institutional analysis
        self._institutional_supertrend = 0.0
        self._smart_money_supertrend = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Supertrend Indicator is ready to provide signals"""
        return (len(self._high_values) >= self.supertrend_config.period and
                len(self._low_values) >= self.supertrend_config.period and
                len(self._close_values) >= self.supertrend_config.period)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update Supertrend analysis

        Args:
            bar (Bar): New bar data
        """
        # Extract OHLCV data
        if hasattr(bar, 'high') and hasattr(bar, 'low') and hasattr(bar, 'close') and hasattr(bar, 'volume'):
            high = bar.high
            low = bar.low
            close = bar.close
            volume = bar.volume
        else:
            high = bar.get('high', bar.get('close', 0.0))
            low = bar.get('low', bar.get('close', 0.0))
            close = bar.get('close', bar.get('price', 0.0))
            volume = bar.get('volume', 1.0)

        # Update Supertrend analysis
        self._update_supertrend_analysis(high, low, close, volume)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_supertrend_analysis(self, high: float, low: float, close: float, volume: float):
        """Update the core Supertrend analysis with institutional enhancements"""
        # Store price and volume data
        self._high_values.append(high)
        self._low_values.append(low)
        self._close_values.append(close)
        self._volume_values.append(volume)

        if len(self._high_values) >= self.supertrend_config.period:
            # Calculate True Range for ATR
            self._calculate_true_range(high, low, close)

            # Calculate ATR
            self._calculate_atr()

            # Calculate Supertrend bands
            self._calculate_supertrend_bands()

            # Determine trend direction
            self._determine_trend_direction(close)

            # Analyze trend characteristics
            self._analyze_trend_characteristics()

            # Generate Supertrend signals
            self._generate_supertrend_signals()

            # Calculate institutional Supertrend analysis
            self._calculate_institutional_supertrend()

    def _calculate_true_range(self, high: float, low: float, close: float):
        """Calculate True Range for ATR calculation"""
        if len(self._close_values) < 2:
            true_range = high - low
        else:
            previous_close = list(self._close_values)[-2]
            tr1 = high - low
            tr2 = abs(high - previous_close)
            tr3 = abs(low - previous_close)
            true_range = max(tr1, tr2, tr3)

        self._true_ranges.append(true_range)

    def _calculate_atr(self):
        """Calculate Average True Range"""
        if len(self._true_ranges) >= self.supertrend_config.period:
            recent_tr = list(self._true_ranges)[-self.supertrend_config.period:]
            atr = statistics.mean(recent_tr)
            self._atr_values.append(atr)

    def _calculate_supertrend_bands(self):
        """Calculate Supertrend upper and lower bands"""
        if len(self._atr_values) < 1:
            return

        current_atr = self._atr_values[-1]
        current_high = self._high_values[-1]
        current_low = self._low_values[-1]

        # Calculate basic bands
        basic_upper = (current_high + current_low) / 2 + (self.supertrend_config.multiplier * current_atr)
        basic_lower = (current_high + current_low) / 2 - (self.supertrend_config.multiplier * current_atr)

        # Adaptive multiplier based on volatility regime
        if self.supertrend_config.adaptive_multiplier:
            volatility_multiplier = self._calculate_volatility_multiplier()
            basic_upper = (current_high + current_low) / 2 + (volatility_multiplier * current_atr)
            basic_lower = (current_high + current_low) / 2 - (volatility_multiplier * current_atr)

        # Volume-weighted adjustment
        if self.supertrend_config.volume_weighted and len(self._volume_values) > 1:
            volume_weight = self._calculate_volume_weight()
            basic_upper *= volume_weight
            basic_lower *= volume_weight

        self._upper_band = basic_upper
        self._lower_band = basic_lower

        # Determine Supertrend value based on trend direction
        if self._trend_direction == 1:  # Uptrend
            self._supertrend_value = self._lower_band
        elif self._trend_direction == -1:  # Downtrend
            self._supertrend_value = self._upper_band
        else:
            self._supertrend_value = (self._upper_band + self._lower_band) / 2

    def _calculate_volatility_multiplier(self) -> float:
        """Calculate adaptive multiplier based on volatility regime"""
        if len(self._atr_values) < 10:
            return self.supertrend_config.multiplier

        recent_atr = list(self._atr_values)[-10:]
        avg_atr = statistics.mean(recent_atr)
        current_atr = self._atr_values[-1]

        # Increase multiplier in high volatility, decrease in low volatility
        if current_atr > avg_atr * 1.5:
            return self.supertrend_config.multiplier * 1.2  # High volatility
        elif current_atr < avg_atr * 0.7:
            return self.supertrend_config.multiplier * 0.8  # Low volatility
        else:
            return self.supertrend_config.multiplier  # Normal volatility

    def _calculate_volume_weight(self) -> float:
        """Calculate volume weight for band adjustment"""
        if len(self._volume_values) < 5:
            return 1.0

        recent_volumes = list(self._volume_values)[-5:]
        avg_volume = statistics.mean(recent_volumes)
        current_volume = self._volume_values[-1]

        # Volume weight: higher volume = tighter bands
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0

        if volume_ratio > 2.0:
            return 0.95  # High volume tightens bands
        elif volume_ratio < 0.5:
            return 1.05  # Low volume widens bands
        else:
            return 1.0   # Normal volume

    def _determine_trend_direction(self, close: float):
        """Determine trend direction based on Supertrend bands"""
        self._previous_trend = self._trend_direction

        if close > self._upper_band:
            self._trend_direction = 1  # Uptrend
        elif close < self._lower_band:
            self._trend_direction = -1  # Downtrend
        else:
            self._trend_direction = self._previous_trend  # Maintain previous trend

        # Track trend duration
        if self._trend_direction == self._previous_trend:
            self._trend_duration += 1
        else:
            self._trend_duration = 1

    def _analyze_trend_characteristics(self):
        """Analyze trend characteristics for institutional insights"""
        if not self.is_ready:
            return

        # Calculate signal strength based on band distance
        band_distance = self._upper_band - self._lower_band
        if band_distance > 0:
            price_position = (list(self._close_values)[-1] - self._lower_band) / band_distance
            self._signal_strength = min(1.0, max(0.0, price_position))

        # Determine volatility regime
        if len(self._atr_values) >= 5:
            recent_atr = list(self._atr_values)[-5:]
            avg_atr = statistics.mean(recent_atr)
            current_atr = self._atr_values[-1]

            if current_atr > avg_atr * 1.3:
                self._volatility_regime = "high"
            elif current_atr < avg_atr * 0.7:
                self._volatility_regime = "low"
            else:
                self._volatility_regime = "normal"

        # Calculate trend accuracy (simplified)
        if len(self._close_values) >= 20:
            correct_predictions = 0
            total_predictions = 0

            for i in range(10, len(self._close_values)):
                if self._trend_direction != 0:
                    future_price = list(self._close_values)[i]
                    current_price = list(self._close_values)[i-1]

                    if self._trend_direction == 1 and future_price > current_price:
                        correct_predictions += 1
                    elif self._trend_direction == -1 and future_price < current_price:
                        correct_predictions += 1
                    total_predictions += 1

            if total_predictions > 0:
                self._trend_accuracy = correct_predictions / total_predictions

    def _generate_supertrend_signals(self):
        """Generate Supertrend-based signals"""
        if not self.is_ready:
            return

        # Trend change signals
        if self._trend_direction != self._previous_trend and self._trend_direction != 0:
            self._trend_signals += 1

            if self._trend_direction == 1:
                self._reversal_signals += 1  # Bullish reversal
            else:
                self._reversal_signals += 1  # Bearish reversal

        # Continuation signals
        elif self._trend_direction == self._previous_trend and self._trend_duration > 3:
            self._continuation_signals += 1

        # Breakout signals
        if abs(self._signal_strength - 0.5) > 0.3:
            self._breakout_signals += 1

    def _calculate_institutional_supertrend(self):
        """Calculate institutional Supertrend analysis based on trend characteristics"""
        if not self.is_ready:
            return

        # Institutional traders use Supertrend for trend following and risk management
        base_supertrend = 0.0

        if (self._trend_signals > 0 and
            self._trend_accuracy > 0.6 and
            self._signal_strength > 0.6):
            base_supertrend = 0.9  # Strong trend signals with high accuracy
        elif (self._continuation_signals > 0 and
              self._trend_duration > 5 and
              self._volatility_regime == "normal"):
            base_supertrend = 0.8  # Good continuation signals in stable conditions
        elif (self._reversal_signals > 0 and
              self._breakout_signals > 0):
            base_supertrend = 0.7  # Reversal signals with breakout confirmation

        self._institutional_supertrend = base_supertrend

        # Smart money Supertrend considers trend strength and duration
        smart_money_score = (
            self._signal_strength * 0.3 +
            self._trend_accuracy * 0.3 +
            min(1.0, self._trend_duration / 20.0) * 0.2 +  # Longer trends = better
            self._institutional_supertrend * 0.2
        )
        self._smart_money_supertrend = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade Supertrend analysis"""
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

        # Use Supertrend value as primary raw value
        raw_value = self._supertrend_value

        # Determine signal type based on Supertrend analysis
        signal_type = self._determine_supertrend_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'supertrend_value': self._supertrend_value,
            'upper_band': self._upper_band,
            'lower_band': self._lower_band,
            'trend_direction': self._trend_direction,
            'signal_strength': self._signal_strength,
            'trend_accuracy': self._trend_accuracy,
            'trend_duration': self._trend_duration,
            'volatility_regime': self._volatility_regime,
            'reversal_success_rate': self._reversal_success_rate,
            'trend_signals': self._trend_signals,
            'reversal_signals': self._reversal_signals,
            'continuation_signals': self._continuation_signals,
            'breakout_signals': self._breakout_signals,
            'support_resistance_levels': self._support_resistance_levels,
            'institutional_supertrend': self._institutional_supertrend,
            'smart_money_supertrend': self._smart_money_supertrend
        }

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._suggested_sl,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Supertrend_Indicator",
                "period": self.supertrend_config.period,
                "multiplier": self.supertrend_config.multiplier,
                "adaptive_multiplier": self.supertrend_config.adaptive_multiplier,
                "volume_weighted": self.supertrend_config.volume_weighted,
                "supertrend_value": self._supertrend_value,
                "upper_band": self._upper_band,
                "lower_band": self._lower_band,
                "trend_direction": self._trend_direction,
                "signal_strength": self._signal_strength,
                "trend_accuracy": self._trend_accuracy,
                "trend_duration": self._trend_duration,
                "volatility_regime": self._volatility_regime,
                "reversal_success_rate": self._reversal_success_rate,
                "trend_signals": self._trend_signals,
                "reversal_signals": self._reversal_signals,
                "continuation_signals": self._continuation_signals,
                "breakout_signals": self._breakout_signals,
                "support_resistance_levels": self._support_resistance_levels,
                "institutional_supertrend": self._institutional_supertrend,
                "smart_money_supertrend": self._smart_money_supertrend,
                "is_ready": self.is_ready
            }
        )

    def _determine_supertrend_signal(self) -> SignalType:
        """Determine signal type based on Supertrend analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong trend signals
        if (self._trend_signals > 0 and
            self._trend_accuracy > 0.7 and
            self._signal_strength > 0.7):
            if self._trend_direction == 1:
                return SignalType.STRONG_BULLISH
            elif self._trend_direction == -1:
                return SignalType.STRONG_BEARISH

        # Moderate trend signals
        elif (self._continuation_signals > 0 and
              self._trend_duration > 5):
            if self._trend_direction == 1:
                return SignalType.BULLISH
            elif self._trend_direction == -1:
                return SignalType.BEARISH

        # Reversal signals
        elif (self._reversal_signals > 0 and
              self._breakout_signals > 0):
            if self._trend_direction == 1:
                return SignalType.BULLISH
            elif self._trend_direction == -1:
                return SignalType.BEARISH

        # Breakout signals
        elif self._breakout_signals > 0 and abs(self._signal_strength - 0.5) > 0.4:
            if self._signal_strength > 0.5:
                return SignalType.BULLISH
            else:
                return SignalType.BEARISH

        return SignalType.NEUTRAL

    @property
    def supertrend_value(self) -> float:
        """Get the current Supertrend value"""
        return self._supertrend_value if self.is_ready else 0.0

    @property
    def upper_band(self) -> float:
        """Get the current upper band"""
        return self._upper_band if self.is_ready else 0.0

    @property
    def lower_band(self) -> float:
        """Get the current lower band"""
        return self._lower_band if self.is_ready else 0.0

    @property
    def trend_direction(self) -> int:
        """Get the current trend direction (1=up, -1=down, 0=neutral)"""
        return self._trend_direction

    @property
    def signal_strength(self) -> float:
        """Get the current signal strength (0-1)"""
        return self._signal_strength

    @property
    def trend_accuracy(self) -> float:
        """Get the trend accuracy (0-1)"""
        return self._trend_accuracy

    @property
    def trend_duration(self) -> int:
        """Get the current trend duration"""
        return self._trend_duration

    @property
    def volatility_regime(self) -> str:
        """Get the current volatility regime"""
        return self._volatility_regime

    @property
    def trend_signals(self) -> int:
        """Get the count of trend signals"""
        return self._trend_signals

    @property
    def reversal_signals(self) -> int:
        """Get the count of reversal signals"""
        return self._reversal_signals

    @property
    def continuation_signals(self) -> int:
        """Get the count of continuation signals"""
        return self._continuation_signals

    @property
    def breakout_signals(self) -> int:
        """Get the count of breakout signals"""
        return self._breakout_signals

    @property
    def institutional_supertrend(self) -> float:
        """Get the institutional Supertrend score (0-1)"""
        return self._institutional_supertrend

    @property
    def smart_money_supertrend(self) -> float:
        """Get the smart money Supertrend score (0-1)"""
        return self._smart_money_supertrend

    def is_uptrend(self) -> bool:
        """Check if current trend is uptrend"""
        return self._trend_direction == 1

    def is_downtrend(self) -> bool:
        """Check if current trend is downtrend"""
        return self._trend_direction == -1

    def is_trend_strong(self) -> bool:
        """Check if current trend is strong"""
        return self._signal_strength > 0.7

    def is_trend_accurate(self) -> bool:
        """Check if trend predictions are accurate"""
        return self._trend_accuracy > 0.7

    def is_long_trend(self) -> bool:
        """Check if current trend is long-duration"""
        return self._trend_duration > 10

    def is_high_volatility(self) -> bool:
        """Check if volatility regime is high"""
        return self._volatility_regime == "high"

    def is_low_volatility(self) -> bool:
        """Check if volatility regime is low"""
        return self._volatility_regime == "low"

    def is_institutional_setup(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_supertrend > 0.7

    def get_supertrend_info(self) -> Dict[str, Any]:
        """Get comprehensive Supertrend indicator information"""
        return {
            "bands": {
                "upper": self._upper_band,
                "lower": self._lower_band,
                "supertrend": self._supertrend_value
            },
            "trend_analysis": {
                "direction": self._trend_direction,
                "strength": self._signal_strength,
                "accuracy": self._trend_accuracy,
                "duration": self._trend_duration
            },
            "market_conditions": {
                "volatility_regime": self._volatility_regime,
                "reversal_success_rate": self._reversal_success_rate
            },
            "signal_counts": {
                "trend_signals": self._trend_signals,
                "reversal_signals": self._reversal_signals,
                "continuation_signals": self._continuation_signals,
                "breakout_signals": self._breakout_signals
            },
            "support_resistance": {
                "levels": self._support_resistance_levels
            },
            "institutional_analysis": {
                "supertrend": self._institutional_supertrend,
                "smart_money_supertrend": self._smart_money_supertrend
            },
            "metadata": {
                "period": self.supertrend_config.period,
                "multiplier": self.supertrend_config.multiplier,
                "adaptive_multiplier": self.supertrend_config.adaptive_multiplier,
                "volume_weighted": self.supertrend_config.volume_weighted,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._high_values.clear()
        self._low_values.clear()
        self._close_values.clear()
        self._volume_values.clear()
        self._atr_values.clear()
        self._true_ranges.clear()
        self._upper_band = 0.0
        self._lower_band = 0.0
        self._supertrend_value = 0.0
        self._trend_direction = 0
        self._previous_trend = 0
        self._trend_signals = 0
        self._reversal_signals = 0
        self._continuation_signals = 0
        self._breakout_signals = 0
        self._trend_accuracy = 0.0
        self._reversal_success_rate = 0.0
        self._signal_strength = 0.0
        self._trend_duration = 0
        self._volatility_regime = "normal"
        self._support_resistance_levels.clear()
        self._institutional_supertrend = 0.0
        self._smart_money_supertrend = 0.0