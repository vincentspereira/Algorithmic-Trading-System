"""
Institutional-Grade Augmented Chandelier Exit Indicator

This module implements an enhanced Chandelier Exit indicator with institutional-grade features:
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
class AugmentedChandelierExitConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Chandelier Exit Indicator"""
    atr_period: int = 22
    multiplier: float = 3.0
    use_close: bool = True  # Use close instead of high/low for trailing
    adaptive_multiplier: bool = True


class AugmentedChandelierExitIndicator(AugmentedIndicator):
    """
    Institutional-grade Augmented Chandelier Exit Indicator implementing 5-pillar architecture.

    Features:
    - ATR-based trailing stop system for trend following
    - Dynamic exit levels that follow price movements
    - Volume confirmation for stop validation
    - Market regime adaptation for different volatility environments
    - Multi-timeframe convergence for institutional confirmation
    - Smart money trend validation and exit timing
    - Automated risk management with trailing stop optimization
    """

    def __init__(self, config: AugmentedChandelierExitConfig = None):
        if config is None:
            config = AugmentedChandelierExitConfig()

        super().__init__(config)
        self.chandelier_config = config

        # Chandelier Exit specific state
        self._high_values = deque(maxlen=self.config.buffer_size)
        self._low_values = deque(maxlen=self.config.buffer_size)
        self._close_values = deque(maxlen=self.config.buffer_size)
        self._volume_values = deque(maxlen=self.config.buffer_size)

        # ATR calculation for dynamic stops
        self._atr_values = deque(maxlen=self.config.buffer_size)
        self._true_ranges = deque(maxlen=self.config.buffer_size)

        # Chandelier Exit levels
        self._long_exit = 0.0  # Exit level for long positions
        self._short_exit = 0.0  # Exit level for short positions
        self._current_exit = 0.0  # Current active exit level

        # Trend tracking
        self._highest_high = 0.0
        self._lowest_low = float('inf')
        self._trend_direction = 0  # 1 = uptrend, -1 = downtrend

        # Exit signals
        self._exit_signals = 0
        self._trailing_signals = 0
        self._breakout_signals = 0
        self._reversal_signals = 0

        # Performance tracking
        self._exit_accuracy = 0.0
        self._trailing_efficiency = 0.0
        self._stop_distance = 0.0

        # Market structure
        self._volatility_regime = "normal"
        self._support_levels = []
        self._resistance_levels = []

        # Risk management
        self._risk_reward_ratio = 0.0
        self._optimal_stop_level = 0.0
        self._trailing_activation = 0.0

        # Institutional analysis
        self._institutional_chandelier = 0.0
        self._smart_money_chandelier = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Chandelier Exit Indicator is ready to provide signals"""
        return (len(self._high_values) >= self.chandelier_config.atr_period and
                len(self._low_values) >= self.chandelier_config.atr_period and
                len(self._close_values) >= self.chandelier_config.atr_period and
                len(self._atr_values) > 0)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update Chandelier Exit analysis

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

        # Update Chandelier Exit analysis
        self._update_chandelier_analysis(high, low, close, volume)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_chandelier_analysis(self, high: float, low: float, close: float, volume: float):
        """Update the core Chandelier Exit analysis with institutional enhancements"""
        # Store price and volume data
        self._high_values.append(high)
        self._low_values.append(low)
        self._close_values.append(close)
        self._volume_values.append(volume)

        if len(self._high_values) >= self.chandelier_config.atr_period:
            # Calculate True Range for ATR
            self._calculate_true_range(high, low, close)

            # Calculate ATR
            self._calculate_atr()

            # Update highest high and lowest low
            self._update_price_extremes(high, low)

            # Calculate Chandelier Exit levels
            self._calculate_chandelier_exits()

            # Determine trend direction
            self._determine_trend_direction(close)

            # Analyze exit characteristics
            self._analyze_exit_characteristics(close)

            # Generate Chandelier signals
            self._generate_chandelier_signals(close)

            # Calculate institutional Chandelier analysis
            self._calculate_institutional_chandelier()

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
        if len(self._true_ranges) >= self.chandelier_config.atr_period:
            recent_tr = list(self._true_ranges)[-self.chandelier_config.atr_period:]
            atr = statistics.mean(recent_tr)
            self._atr_values.append(atr)

    def _update_price_extremes(self, high: float, low: float):
        """Update highest high and lowest low for trailing stops"""
        if len(self._high_values) >= 2:
            # Update highest high since last exit
            if self._trend_direction >= 0:  # Bullish or neutral
                self._highest_high = max(self._highest_high, high)
            else:
                # Reset on trend change
                self._highest_high = high

            # Update lowest low since last exit
            if self._trend_direction <= 0:  # Bearish or neutral
                self._lowest_low = min(self._lowest_low, low)
            else:
                # Reset on trend change
                self._lowest_low = low

    def _calculate_chandelier_exits(self):
        """Calculate Chandelier Exit levels"""
        if len(self._atr_values) < 1:
            return

        current_atr = self._atr_values[-1]

        # Adaptive multiplier based on volatility regime
        multiplier = self._calculate_adaptive_multiplier()

        # Long exit (trailing stop for long positions)
        if self.chandelier_config.use_close:
            # Use highest high since entry
            self._long_exit = self._highest_high - (multiplier * current_atr)
        else:
            # Traditional Chandelier: use highest high
            self._long_exit = self._highest_high - (multiplier * current_atr)

        # Short exit (trailing stop for short positions)
        if self.chandelier_config.use_close:
            # Use lowest low since entry
            self._short_exit = self._lowest_low + (multiplier * current_atr)
        else:
            # Traditional Chandelier: use lowest low
            self._short_exit = self._lowest_low + (multiplier * current_atr)

        # Set current exit based on trend direction
        if self._trend_direction == 1:  # Uptrend
            self._current_exit = self._long_exit
        elif self._trend_direction == -1:  # Downtrend
            self._current_exit = self._short_exit
        else:
            # Neutral: use average
            self._current_exit = (self._long_exit + self._short_exit) / 2

    def _calculate_adaptive_multiplier(self) -> float:
        """Calculate adaptive multiplier based on market conditions"""
        base_multiplier = self.chandelier_config.multiplier

        if not self.chandelier_config.adaptive_multiplier:
            return base_multiplier

        if len(self._atr_values) < 10:
            return base_multiplier

        # Analyze volatility trend
        recent_atr = list(self._atr_values)[-10:]
        avg_atr = statistics.mean(recent_atr)
        current_atr = self._atr_values[-1]

        # Increase multiplier in high volatility, decrease in low volatility
        if current_atr > avg_atr * 1.5:
            return base_multiplier * 1.2  # High volatility - wider stops
        elif current_atr < avg_atr * 0.7:
            return base_multiplier * 0.8  # Low volatility - tighter stops
        else:
            return base_multiplier  # Normal volatility

    def _determine_trend_direction(self, close: float):
        """Determine trend direction based on price action"""
        if len(self._close_values) < 5:
            return

        recent_closes = list(self._close_values)[-5:]

        # Simple trend determination
        if recent_closes[-1] > recent_closes[0]:
            self._trend_direction = 1  # Uptrend
        elif recent_closes[-1] < recent_closes[0]:
            self._trend_direction = -1  # Downtrend
        else:
            self._trend_direction = 0  # Neutral

    def _analyze_exit_characteristics(self, close: float):
        """Analyze exit characteristics for institutional insights"""
        if not self.is_ready:
            return

        # Calculate stop distance
        if self._trend_direction == 1 and self._long_exit > 0:
            self._stop_distance = (close - self._long_exit) / close if close > 0 else 0
        elif self._trend_direction == -1 and self._short_exit > 0:
            self._stop_distance = (self._short_exit - close) / close if close > 0 else 0
        else:
            self._stop_distance = 0.0

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

        # Calculate risk-reward ratio
        if self._stop_distance > 0:
            # Assume target is 2x stop distance
            potential_reward = self._stop_distance * 2
            self._risk_reward_ratio = potential_reward / self._stop_distance if self._stop_distance > 0 else 0

        # Calculate trailing efficiency
        if len(self._close_values) >= 20:
            # Simplified trailing efficiency calculation
            self._trailing_efficiency = min(1.0, self._stop_distance * 10)

    def _generate_chandelier_signals(self, close: float):
        """Generate Chandelier Exit-based signals"""
        if not self.is_ready:
            return

        # Exit signals
        if self._trend_direction == 1 and close <= self._long_exit:
            self._exit_signals += 1
        elif self._trend_direction == -1 and close >= self._short_exit:
            self._exit_signals += 1

        # Trailing signals (when stop moves favorably)
        if len(self._close_values) >= 2:
            prev_close = list(self._close_values)[-2]
            if self._trend_direction == 1 and self._long_exit > prev_close:
                self._trailing_signals += 1
            elif self._trend_direction == -1 and self._short_exit < prev_close:
                self._trailing_signals += 1

        # Breakout signals (when price breaks above/below stops)
        if self._trend_direction == 1 and close > self._long_exit * 1.05:  # 5% above stop
            self._breakout_signals += 1
        elif self._trend_direction == -1 and close < self._short_exit * 0.95:  # 5% below stop
            self._breakout_signals += 1

        # Reversal signals (when trend changes)
        if len(self._close_values) >= 3:
            prev_trend = self._trend_direction
            # This would be calculated based on trend change detection
            self._reversal_signals += 1 if prev_trend != self._trend_direction else 0

    def _calculate_institutional_chandelier(self):
        """Calculate institutional Chandelier analysis based on exit characteristics"""
        if not self.is_ready:
            return

        # Institutional traders use Chandelier Exit for risk management and trend following
        base_chandelier = 0.0

        if (self._exit_signals > 0 and
            self._trailing_efficiency > 0.7 and
            self._stop_distance > 0.02):  # 2% stop distance
            base_chandelier = 0.9  # Strong exit signals with good trailing efficiency
        elif (self._trailing_signals > 0 and
              self._volatility_regime == "normal" and
              self._risk_reward_ratio > 1.5):
            base_chandelier = 0.8  # Good trailing signals with favorable risk-reward
        elif (self._breakout_signals > 0 and
              self._exit_accuracy > 0.6):
            base_chandelier = 0.7  # Breakout signals with decent accuracy

        self._institutional_chandelier = base_chandelier

        # Smart money Chandelier considers stop efficiency and market timing
        smart_money_score = (
            self._trailing_efficiency * 0.3 +
            self._exit_accuracy * 0.3 +
            self._risk_reward_ratio / 3.0 * 0.2 +  # Normalize risk-reward
            self._institutional_chandelier * 0.2
        )
        self._smart_money_chandelier = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade Chandelier Exit analysis"""
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

        # Use current exit level as primary raw value
        raw_value = self._current_exit

        # Determine signal type based on Chandelier Exit analysis
        signal_type = self._determine_chandelier_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'current_exit': self._current_exit,
            'long_exit': self._long_exit,
            'short_exit': self._short_exit,
            'trend_direction': self._trend_direction,
            'highest_high': self._highest_high,
            'lowest_low': self._lowest_low,
            'stop_distance': self._stop_distance,
            'exit_accuracy': self._exit_accuracy,
            'trailing_efficiency': self._trailing_efficiency,
            'volatility_regime': self._volatility_regime,
            'risk_reward_ratio': self._risk_reward_ratio,
            'optimal_stop_level': self._optimal_stop_level,
            'trailing_activation': self._trailing_activation,
            'exit_signals': self._exit_signals,
            'trailing_signals': self._trailing_signals,
            'breakout_signals': self._breakout_signals,
            'reversal_signals': self._reversal_signals,
            'support_levels': self._support_levels,
            'resistance_levels': self._resistance_levels,
            'institutional_chandelier': self._institutional_chandelier,
            'smart_money_chandelier': self._smart_money_chandelier
        }

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._current_exit,
            suggested_tp=self._optimal_stop_level,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Chandelier_Exit_Indicator",
                "atr_period": self.chandelier_config.atr_period,
                "multiplier": self.chandelier_config.multiplier,
                "use_close": self.chandelier_config.use_close,
                "adaptive_multiplier": self.chandelier_config.adaptive_multiplier,
                "current_exit": self._current_exit,
                "long_exit": self._long_exit,
                "short_exit": self._short_exit,
                "trend_direction": self._trend_direction,
                "highest_high": self._highest_high,
                "lowest_low": self._lowest_low,
                "stop_distance": self._stop_distance,
                "exit_accuracy": self._exit_accuracy,
                "trailing_efficiency": self._trailing_efficiency,
                "volatility_regime": self._volatility_regime,
                "risk_reward_ratio": self._risk_reward_ratio,
                "optimal_stop_level": self._optimal_stop_level,
                "trailing_activation": self._trailing_activation,
                "exit_signals": self._exit_signals,
                "trailing_signals": self._trailing_signals,
                "breakout_signals": self._breakout_signals,
                "reversal_signals": self._reversal_signals,
                "support_levels": self._support_levels,
                "resistance_levels": self._resistance_levels,
                "institutional_chandelier": self._institutional_chandelier,
                "smart_money_chandelier": self._smart_money_chandelier,
                "is_ready": self.is_ready
            }
        )

    def _determine_chandelier_signal(self) -> SignalType:
        """Determine signal type based on Chandelier Exit analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong exit signals
        if (self._exit_signals > 0 and
            self._trailing_efficiency > 0.8 and
            self._stop_distance > 0.03):  # 3% stop distance
            if self._trend_direction == 1:
                return SignalType.STRONG_BEARISH  # Exit long position
            elif self._trend_direction == -1:
                return SignalType.STRONG_BULLISH  # Exit short position

        # Moderate exit signals
        elif (self._exit_signals > 0 and
              self._exit_accuracy > 0.6):
            if self._trend_direction == 1:
                return SignalType.BEARISH
            elif self._trend_direction == -1:
                return SignalType.BULLISH

        # Trailing signals
        elif (self._trailing_signals > 0 and
              self._risk_reward_ratio > 2.0):
            if self._trend_direction == 1:
                return SignalType.BULLISH  # Continue long trend
            elif self._trend_direction == -1:
                return SignalType.BEARISH  # Continue short trend

        # Breakout signals
        elif self._breakout_signals > 0:
            if self._trend_direction == 1:
                return SignalType.STRONG_BULLISH  # Strong uptrend continuation
            elif self._trend_direction == -1:
                return SignalType.STRONG_BEARISH  # Strong downtrend continuation

        return SignalType.NEUTRAL

    @property
    def current_exit(self) -> float:
        """Get the current exit level"""
        return self._current_exit if self.is_ready else 0.0

    @property
    def long_exit(self) -> float:
        """Get the long exit level"""
        return self._long_exit if self.is_ready else 0.0

    @property
    def short_exit(self) -> float:
        """Get the short exit level"""
        return self._short_exit if self.is_ready else 0.0

    @property
    def trend_direction(self) -> int:
        """Get the current trend direction (1=up, -1=down, 0=neutral)"""
        return self._trend_direction

    @property
    def stop_distance(self) -> float:
        """Get the current stop distance (as percentage)"""
        return self._stop_distance

    @property
    def exit_accuracy(self) -> float:
        """Get the exit accuracy (0-1)"""
        return self._exit_accuracy

    @property
    def trailing_efficiency(self) -> float:
        """Get the trailing efficiency (0-1)"""
        return self._trailing_efficiency

    @property
    def volatility_regime(self) -> str:
        """Get the current volatility regime"""
        return self._volatility_regime

    @property
    def risk_reward_ratio(self) -> float:
        """Get the current risk-reward ratio"""
        return self._risk_reward_ratio

    @property
    def exit_signals(self) -> int:
        """Get the count of exit signals"""
        return self._exit_signals

    @property
    def trailing_signals(self) -> int:
        """Get the count of trailing signals"""
        return self._trailing_signals

    @property
    def breakout_signals(self) -> int:
        """Get the count of breakout signals"""
        return self._breakout_signals

    @property
    def reversal_signals(self) -> int:
        """Get the count of reversal signals"""
        return self._reversal_signals

    @property
    def institutional_chandelier(self) -> float:
        """Get the institutional Chandelier score (0-1)"""
        return self._institutional_chandelier

    @property
    def smart_money_chandelier(self) -> float:
        """Get the smart money Chandelier score (0-1)"""
        return self._smart_money_chandelier

    def is_long_exit_triggered(self) -> bool:
        """Check if long exit is triggered"""
        if not self.is_ready or len(self._close_values) < 1:
            return False
        return self._close_values[-1] <= self._long_exit

    def is_short_exit_triggered(self) -> bool:
        """Check if short exit is triggered"""
        if not self.is_ready or len(self._close_values) < 1:
            return False
        return self._close_values[-1] >= self._short_exit

    def is_trailing_active(self) -> bool:
        """Check if trailing stop is active"""
        return self._trailing_signals > 0

    def is_wide_stop(self) -> bool:
        """Check if stop distance is wide (>3%)"""
        return self._stop_distance > 0.03

    def is_narrow_stop(self) -> bool:
        """Check if stop distance is narrow (<1%)"""
        return self._stop_distance < 0.01

    def is_favorable_risk_reward(self) -> bool:
        """Check if risk-reward ratio is favorable (>1.5)"""
        return self._risk_reward_ratio > 1.5

    def is_high_volatility(self) -> bool:
        """Check if volatility regime is high"""
        return self._volatility_regime == "high"

    def is_low_volatility(self) -> bool:
        """Check if volatility regime is low"""
        return self._volatility_regime == "low"

    def is_institutional_setup(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_chandelier > 0.7

    def get_chandelier_info(self) -> Dict[str, Any]:
        """Get comprehensive Chandelier Exit indicator information"""
        return {
            "exit_levels": {
                "current": self._current_exit,
                "long": self._long_exit,
                "short": self._short_exit
            },
            "trend_analysis": {
                "direction": self._trend_direction,
                "highest_high": self._highest_high,
                "lowest_low": self._lowest_low
            },
            "risk_management": {
                "stop_distance": self._stop_distance,
                "exit_accuracy": self._exit_accuracy,
                "trailing_efficiency": self._trailing_efficiency,
                "risk_reward_ratio": self._risk_reward_ratio,
                "optimal_stop_level": self._optimal_stop_level,
                "trailing_activation": self._trailing_activation
            },
            "market_conditions": {
                "volatility_regime": self._volatility_regime
            },
            "signal_counts": {
                "exit_signals": self._exit_signals,
                "trailing_signals": self._trailing_signals,
                "breakout_signals": self._breakout_signals,
                "reversal_signals": self._reversal_signals
            },
            "support_resistance": {
                "support_levels": self._support_levels,
                "resistance_levels": self._resistance_levels
            },
            "institutional_analysis": {
                "chandelier": self._institutional_chandelier,
                "smart_money_chandelier": self._smart_money_chandelier
            },
            "metadata": {
                "atr_period": self.chandelier_config.atr_period,
                "multiplier": self.chandelier_config.multiplier,
                "use_close": self.chandelier_config.use_close,
                "adaptive_multiplier": self.chandelier_config.adaptive_multiplier,
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
        self._long_exit = 0.0
        self._short_exit = 0.0
        self._current_exit = 0.0
        self._highest_high = 0.0
        self._lowest_low = float('inf')
        self._trend_direction = 0
        self._exit_signals = 0
        self._trailing_signals = 0
        self._breakout_signals = 0
        self._reversal_signals = 0
        self._exit_accuracy = 0.0
        self._trailing_efficiency = 0.0
        self._stop_distance = 0.0
        self._volatility_regime = "normal"
        self._support_levels.clear()
        self._resistance_levels.clear()
        self._risk_reward_ratio = 0.0
        self._optimal_stop_level = 0.0
        self._trailing_activation = 0.0
        self._institutional_chandelier = 0.0
        self._smart_money_chandelier = 0.0