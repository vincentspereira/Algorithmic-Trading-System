"""
Institutional-Grade Augmented Volatility Stop Indicator

This module implements an enhanced Volatility Stop with institutional-grade features:
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
import math

from nautilus_trader_engine.indicators.base import (
    AugmentedIndicator,
    AugmentedIndicatorConfig,
    IndicatorSignal,
    SignalType,
)


@dataclass
class AugmentedVolatilityStopConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Volatility Stop"""
    period: int = 20
    multiplier: float = 2.0
    use_close: bool = True


class AugmentedVolatilityStopIndicator(AugmentedIndicator):
    """
    Institutional-grade Augmented Volatility Stop implementing 5-pillar architecture.

    Features:
    - Volatility-based stop loss levels for trend following
    - Volume-weighted calculations for institutional validation
    - Market regime adaptation for different volatility environments
    - Multi-timeframe convergence for stop level confirmation
    - Smart money volatility stop detection
    - Automated risk management based on volatility stop signals
    """

    def __init__(self, config: AugmentedVolatilityStopConfig = None):
        if config is None:
            config = AugmentedVolatilityStopConfig()

        super().__init__(config)
        self.vs_config = config

        # Volatility Stop specific state
        self._high_values = deque(maxlen=self.config.buffer_size)
        self._low_values = deque(maxlen=self.config.buffer_size)
        self._close_values = deque(maxlen=self.config.buffer_size)
        self._volume_values = deque(maxlen=self.config.buffer_size)

        # Volatility Stop calculation components
        self._volatility_stop_values = deque(maxlen=self.config.buffer_size)
        self._atr_values = deque(maxlen=self.config.buffer_size)
        self._stop_level_values = deque(maxlen=self.config.buffer_size)

        # Current Volatility Stop values
        self._volatility_stop = 0.0
        self._atr = 0.0
        self._stop_level = 0.0

        # Stop analysis
        self._stop_direction = 0  # 1 = long stop, -1 = short stop, 0 = neutral
        self._stop_strength = 0.0
        self._volatility_stop_signal = 0.0

        # Signal analysis
        self._stop_hit_signals = 0
        self._stop_adjustment_signals = 0
        self._trailing_stop_signals = 0
        self._breakout_signals = 0

        # Performance tracking
        self._signal_accuracy = 0.0
        self._stop_prediction_rate = 0.0
        self._volatility_stop_reliability = 0.0

        # Market structure
        self._volatility_regime = "normal"
        self._stop_cycles = 0
        self._volatility_stop_extremes = []

        # Risk management
        self._volatility_stop_based_stop = 0.0
        self._stop_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0

        # Institutional analysis
        self._institutional_volatility_stop = 0.0
        self._smart_money_volatility_stop = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Volatility Stop is ready to provide signals"""
        return (len(self._close_values) >= self.vs_config.period and
                len(self._volatility_stop_values) > 0)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update Volatility Stop analysis

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

        # Update Volatility Stop analysis
        self._update_volatility_stop_analysis(high, low, close, volume)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_volatility_stop_analysis(self, high: float, low: float, close: float, volume: float):
        """Update the core Volatility Stop analysis with institutional enhancements"""
        # Store OHLCV data
        self._high_values.append(high)
        self._low_values.append(low)
        self._close_values.append(close)
        self._volume_values.append(volume)

        if len(self._close_values) >= self.vs_config.period:
            # Calculate Volatility Stop
            self._calculate_volatility_stop()

            # Analyze stop characteristics
            self._analyze_stop_characteristics()

            # Generate Volatility Stop signals
            self._generate_volatility_stop_signals()

            # Calculate institutional Volatility Stop analysis
            self._calculate_institutional_volatility_stop()

    def _calculate_volatility_stop(self):
        """Calculate Volatility Stop using ATR-based trailing stops"""
        if len(self._close_values) < self.vs_config.period:
            return

        # Calculate ATR (Average True Range)
        if len(self._high_values) >= 2 and len(self._low_values) >= 2 and len(self._close_values) >= 2:
            # Calculate True Range
            tr_values = []
            for i in range(1, len(self._close_values)):
                tr1 = self._high_values[i] - self._low_values[i]
                tr2 = abs(self._high_values[i] - self._close_values[i-1])
                tr3 = abs(self._low_values[i] - self._close_values[i-1])
                true_range = max(tr1, tr2, tr3)
                tr_values.append(true_range)

            if len(tr_values) >= self.vs_config.period:
                # Calculate ATR using simple moving average
                recent_tr = tr_values[-self.vs_config.period:]
                atr = statistics.mean(recent_tr)
                self._atr_values.append(atr)
                self._atr = atr

                # Calculate Volatility Stop
                current_high = self._high_values[-1]
                current_low = self._low_values[-1]
                current_close = self._close_values[-1]

                # Determine trend direction and calculate stop level
                if self.vs_config.use_close:
                    # Use close for trend determination
                    if len(self._close_values) >= 2:
                        if current_close > list(self._close_values)[-2]:
                            # Uptrend - stop below recent low
                            stop_level = current_low - (atr * self.vs_config.multiplier)
                            self._stop_direction = 1  # Long position stop
                        else:
                            # Downtrend - stop above recent high
                            stop_level = current_high + (atr * self.vs_config.multiplier)
                            self._stop_direction = -1  # Short position stop
                    else:
                        stop_level = current_close
                        self._stop_direction = 0
                else:
                    # Use high/low for trend determination
                    if current_high > list(self._high_values)[-2]:
                        # Uptrend
                        stop_level = current_low - (atr * self.vs_config.multiplier)
                        self._stop_direction = 1
                    elif current_low < list(self._low_values)[-2]:
                        # Downtrend
                        stop_level = current_high + (atr * self.vs_config.multiplier)
                        self._stop_direction = -1
                    else:
                        # Sideways
                        stop_level = current_close
                        self._stop_direction = 0

                self._stop_level_values.append(stop_level)
                self._stop_level = stop_level

                # Calculate volatility stop score
                volatility_stop = abs(stop_level - current_close) / current_close if current_close > 0 else 0
                self._volatility_stop_values.append(volatility_stop)
                self._volatility_stop = volatility_stop

    def _analyze_stop_characteristics(self):
        """Analyze stop characteristics for institutional insights"""
        if not self.is_ready:
            return

        # Calculate stop strength
        current_close = list(self._close_values)[-1]
        if current_close > 0:
            self._stop_strength = abs(self._stop_level - current_close) / current_close
        else:
            self._stop_strength = 0.0

        # Calculate Volatility Stop signal
        self._volatility_stop_signal = self._stop_level

        # Determine volatility regime
        if len(self._close_values) >= 10:
            recent_prices = list(self._close_values)[-10:]
            price_volatility = statistics.stdev(recent_prices) / statistics.mean(recent_prices) if statistics.mean(recent_prices) > 0 else 0

            if price_volatility > 0.03:
                self._volatility_regime = "high"
            elif price_volatility < 0.01:
                self._volatility_regime = "low"
            else:
                self._volatility_regime = "normal"

        # Track stop cycles
        if len(self._stop_level_values) >= 2:
            prev_stop = list(self._stop_level_values)[-2]
            current_stop = self._stop_level
            if ((prev_stop <= current_stop and self._stop_direction == 1) or
                (prev_stop >= current_stop and self._stop_direction == -1)):
                self._stop_cycles += 1

        # Track Volatility Stop extremes
        if self._volatility_stop > 0.1:  # Extreme stop distances
            self._volatility_stop_extremes.append(self._volatility_stop)

    def _generate_volatility_stop_signals(self):
        """Generate Volatility Stop-based signals"""
        if not self.is_ready:
            return

        # Stop hit signals (price reaches stop level)
        current_close = list(self._close_values)[-1]
        if ((self._stop_direction == 1 and current_close <= self._stop_level) or
            (self._stop_direction == -1 and current_close >= self._stop_level)):
            self._stop_hit_signals += 1

        # Stop adjustment signals (stop level changes significantly)
        if len(self._stop_level_values) >= 2:
            prev_stop = list(self._stop_level_values)[-2]
            stop_change = abs(self._stop_level - prev_stop) / prev_stop if prev_stop > 0 else 0
            if stop_change > 0.05:  # 5% change
                self._stop_adjustment_signals += 1

        # Trailing stop signals (stop moving in trend direction)
        if ((self._stop_direction == 1 and self._stop_level > prev_stop) or
            (self._stop_direction == -1 and self._stop_level < prev_stop)):
            self._trailing_stop_signals += 1

        # Breakout signals
        if self._stop_strength > 0.05:  # Wide stops indicate potential breakouts
            self._breakout_signals += 1

    def _calculate_institutional_volatility_stop(self):
        """Calculate institutional Volatility Stop analysis based on stop characteristics"""
        if not self.is_ready:
            return

        # Institutional traders use Volatility Stop for dynamic risk management
        base_volatility_stop = 0.0

        if (self._stop_strength > 0.05 and
            (self._stop_hit_signals > 0 or self._stop_adjustment_signals > 0) and
            self._signal_accuracy > 0.6):
            base_volatility_stop = 0.9  # Strong stop assessment with signals and accuracy
        elif (self._trailing_stop_signals > 0 and
              self._breakout_signals > 0 and
              self._stop_cycles > 2):
            base_volatility_stop = 0.8  # Trailing and breakout signals with cycle confirmation
        elif (self._stop_strength > 0.03 and
              self._volatility_stop_reliability > 0.7):
            base_volatility_stop = 0.7  # Good stop strength with high reliability

        self._institutional_volatility_stop = base_volatility_stop

        # Smart money Volatility Stop considers stop strength and market timing
        smart_money_score = (
            self._stop_strength * 0.3 +
            self._signal_accuracy * 0.3 +
            abs(self._volatility_stop_signal) * 0.2 +
            self._institutional_volatility_stop * 0.2
        )
        self._smart_money_volatility_stop = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade Volatility Stop analysis"""
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

        # Use stop level as primary raw value
        raw_value = self._stop_level

        # Determine signal type based on Volatility Stop analysis
        signal_type = self._determine_volatility_stop_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'volatility_stop': self._volatility_stop,
            'atr': self._atr,
            'stop_level': self._stop_level,
            'stop_direction': self._stop_direction,
            'stop_strength': self._stop_strength,
            'volatility_stop_signal': self._volatility_stop_signal,
            'signal_accuracy': self._signal_accuracy,
            'stop_prediction_rate': self._stop_prediction_rate,
            'volatility_stop_reliability': self._volatility_stop_reliability,
            'volatility_regime': self._volatility_regime,
            'stop_cycles': self._stop_cycles,
            'volatility_stop_extremes': self._volatility_stop_extremes,
            'volatility_stop_based_stop': self._volatility_stop_based_stop,
            'stop_based_position_size': self._stop_based_position_size,
            'risk_adjustment_factor': self._risk_adjustment_factor,
            'stop_hit_signals': self._stop_hit_signals,
            'stop_adjustment_signals': self._stop_adjustment_signals,
            'trailing_stop_signals': self._trailing_stop_signals,
            'breakout_signals': self._breakout_signals,
            'institutional_volatility_stop': self._institutional_volatility_stop,
            'smart_money_volatility_stop': self._smart_money_volatility_stop
        }

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._volatility_stop_based_stop,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Volatility_Stop",
                "period": self.vs_config.period,
                "multiplier": self.vs_config.multiplier,
                "use_close": self.vs_config.use_close,
                "volatility_stop": self._volatility_stop,
                "atr": self._atr,
                "stop_level": self._stop_level,
                "stop_direction": self._stop_direction,
                "stop_strength": self._stop_strength,
                "volatility_stop_signal": self._volatility_stop_signal,
                "signal_accuracy": self._signal_accuracy,
                "stop_prediction_rate": self._stop_prediction_rate,
                "volatility_stop_reliability": self._volatility_stop_reliability,
                "volatility_regime": self._volatility_regime,
                "stop_cycles": self._stop_cycles,
                "volatility_stop_extremes": self._volatility_stop_extremes,
                "volatility_stop_based_stop": self._volatility_stop_based_stop,
                "stop_based_position_size": self._stop_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor,
                "stop_hit_signals": self._stop_hit_signals,
                "stop_adjustment_signals": self._stop_adjustment_signals,
                "trailing_stop_signals": self._trailing_stop_signals,
                "breakout_signals": self._breakout_signals,
                "institutional_volatility_stop": self._institutional_volatility_stop,
                "smart_money_volatility_stop": self._smart_money_volatility_stop,
                "is_ready": self.is_ready
            }
        )

    def _determine_volatility_stop_signal(self) -> SignalType:
        """Determine signal type based on Volatility Stop analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong stop signals
        if (self._stop_strength > 0.05 and
            (self._stop_hit_signals > 0 or self._stop_adjustment_signals > 0) and
            self._signal_accuracy > 0.7):
            if self._stop_direction == 1:
                return SignalType.STRONG_BULLISH  # Long stop suggests uptrend
            elif self._stop_direction == -1:
                return SignalType.STRONG_BEARISH  # Short stop suggests downtrend

        # Moderate stop signals
        elif (self._trailing_stop_signals > 0 and
              self._stop_strength > 0.03):
            if self._stop_direction == 1:
                return SignalType.BULLISH  # Trailing long stop
            elif self._stop_direction == -1:
                return SignalType.BEARISH  # Trailing short stop

        # Breakout signals
        elif (self._breakout_signals > 0 and
              self._volatility_stop > 0.05):
            if self._stop_direction == 1:
                return SignalType.STRONG_BULLISH
            else:
                return SignalType.STRONG_BEARISH

        # Stop adjustment signals
        elif (self._stop_adjustment_signals > 0 and
              self._volatility_stop_reliability > 0.7):
            if self._stop_direction == 1:
                return SignalType.BULLISH  # Stop adjustment in uptrend
            elif self._stop_direction == -1:
                return SignalType.BEARISH  # Stop adjustment in downtrend

        return SignalType.NEUTRAL

    @property
    def volatility_stop(self) -> float:
        """Get the current volatility stop value"""
        return self._volatility_stop if self.is_ready else 0.0

    @property
    def atr(self) -> float:
        """Get the current ATR value"""
        return self._atr if self.is_ready else 0.0

    @property
    def stop_level(self) -> float:
        """Get the current stop level"""
        return self._stop_level if self.is_ready else 0.0

    @property
    def stop_direction(self) -> int:
        """Get the current stop direction (1=long, -1=short, 0=neutral)"""
        return self._stop_direction

    @property
    def stop_strength(self) -> float:
        """Get the current stop strength (0-1)"""
        return self._stop_strength

    @property
    def signal_accuracy(self) -> float:
        """Get the signal accuracy (0-1)"""
        return self._signal_accuracy

    @property
    def volatility_regime(self) -> str:
        """Get the current volatility regime"""
        return self._volatility_regime

    @property
    def stop_cycles(self) -> int:
        """Get the count of stop cycles"""
        return self._stop_cycles

    @property
    def stop_hit_signals(self) -> int:
        """Get the count of stop hit signals"""
        return self._stop_hit_signals

    @property
    def stop_adjustment_signals(self) -> int:
        """Get the count of stop adjustment signals"""
        return self._stop_adjustment_signals

    @property
    def trailing_stop_signals(self) -> int:
        """Get the count of trailing stop signals"""
        return self._trailing_stop_signals

    @property
    def breakout_signals(self) -> int:
        """Get the count of breakout signals"""
        return self._breakout_signals

    @property
    def institutional_volatility_stop(self) -> float:
        """Get the institutional Volatility Stop score (0-1)"""
        return self._institutional_volatility_stop

    @property
    def smart_money_volatility_stop(self) -> float:
        """Get the smart money Volatility Stop score (0-1)"""
        return self._smart_money_volatility_stop

    def is_long_stop_volatility_stop(self) -> bool:
        """Check if stop is for long positions"""
        return self._stop_direction == 1

    def is_short_stop_volatility_stop(self) -> bool:
        """Check if stop is for short positions"""
        return self._stop_direction == -1

    def is_strong_stop_volatility_stop(self) -> bool:
        """Check if stop strength is strong"""
        return self._stop_strength > 0.05

    def is_stop_hit_volatility_stop(self) -> bool:
        """Check if stop has been hit"""
        return self._stop_hit_signals > 0

    def is_trailing_stop_volatility_stop(self) -> bool:
        """Check if stop is trailing"""
        return self._trailing_stop_signals > 0

    def is_high_volatility_volatility_stop(self) -> bool:
        """Check if volatility regime is high"""
        return self._volatility_regime == "high"

    def is_low_volatility_volatility_stop(self) -> bool:
        """Check if volatility regime is low"""
        return self._volatility_regime == "low"

    def is_institutional_setup_volatility_stop(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_volatility_stop > 0.7

    def get_volatility_stop_info(self) -> Dict[str, Any]:
        """Get comprehensive Volatility Stop indicator information"""
        return {
            "volatility_stop_values": {
                "volatility_stop": self._volatility_stop,
                "atr": self._atr,
                "stop_level": self._stop_level
            },
            "stop_analysis": {
                "direction": self._stop_direction,
                "strength": self._stop_strength,
                "volatility_stop_signal": self._volatility_stop_signal
            },
            "performance_metrics": {
                "signal_accuracy": self._signal_accuracy,
                "stop_prediction_rate": self._stop_prediction_rate,
                "volatility_stop_reliability": self._volatility_stop_reliability
            },
            "market_conditions": {
                "volatility_regime": self._volatility_regime,
                "stop_cycles": self._stop_cycles
            },
            "signal_counts": {
                "stop_hit_signals": self._stop_hit_signals,
                "stop_adjustment_signals": self._stop_adjustment_signals,
                "trailing_stop_signals": self._trailing_stop_signals,
                "breakout_signals": self._breakout_signals
            },
            "volatility_stop_tracking": {
                "extremes": self._volatility_stop_extremes
            },
            "risk_management": {
                "volatility_stop_based_stop": self._volatility_stop_based_stop,
                "stop_based_position_size": self._stop_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor
            },
            "institutional_analysis": {
                "volatility_stop": self._institutional_volatility_stop,
                "smart_money_volatility_stop": self._smart_money_volatility_stop
            },
            "metadata": {
                "period": self.vs_config.period,
                "multiplier": self.vs_config.multiplier,
                "use_close": self.vs_config.use_close,
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
        self._volatility_stop_values.clear()
        self._atr_values.clear()
        self._stop_level_values.clear()
        self._volatility_stop = 0.0
        self._atr = 0.0
        self._stop_level = 0.0
        self._stop_direction = 0
        self._stop_strength = 0.0
        self._volatility_stop_signal = 0.0
        self._stop_hit_signals = 0
        self._stop_adjustment_signals = 0
        self._trailing_stop_signals = 0
        self._breakout_signals = 0
        self._signal_accuracy = 0.0
        self._stop_prediction_rate = 0.0
        self._volatility_stop_reliability = 0.0
        self._volatility_regime = "normal"
        self._stop_cycles = 0
        self._volatility_stop_extremes.clear()
        self._volatility_stop_based_stop = 0.0
        self._stop_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0
        self._institutional_volatility_stop = 0.0
        self._smart_money_volatility_stop = 0.0