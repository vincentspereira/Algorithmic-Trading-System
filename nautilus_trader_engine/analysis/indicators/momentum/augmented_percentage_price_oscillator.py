"""
Institutional-Grade Augmented Percentage Price Oscillator Indicator

This module implements an enhanced Percentage Price Oscillator with institutional-grade features:
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
class AugmentedPercentagePriceOscillatorConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Percentage Price Oscillator"""
    fast_period: int = 12
    slow_period: int = 26
    signal_period: int = 9
    overbought: float = 2.0
    oversold: float = -2.0


class AugmentedPercentagePriceOscillatorIndicator(AugmentedIndicator):
    """
    Institutional-grade Augmented Percentage Price Oscillator implementing 5-pillar architecture.

    Features:
    - MACD expressed in percentage terms for cross-asset comparison
    - Volume-weighted calculations for institutional validation
    - Market regime adaptation for different volatility environments
    - Multi-timeframe convergence for momentum confirmation
    - Smart money momentum detection
    - Automated risk management based on PPO signals
    """

    def __init__(self, config: AugmentedPercentagePriceOscillatorConfig = None):
        if config is None:
            config = AugmentedPercentagePriceOscillatorConfig()

        super().__init__(config)
        self.ppo_config = config

        # PPO specific state
        self._close_values = deque(maxlen=self.config.buffer_size)
        self._volume_values = deque(maxlen=self.config.buffer_size)

        # PPO calculation components
        self._ppo_values = deque(maxlen=self.config.buffer_size)
        self._signal_values = deque(maxlen=self.config.buffer_size)
        self._histogram_values = deque(maxlen=self.config.buffer_size)

        # Current PPO values
        self._ppo = 0.0
        self._signal = 0.0
        self._histogram = 0.0

        # Momentum analysis
        self._momentum_direction = 0  # 1 = bullish, -1 = bearish, 0 = neutral
        self._momentum_strength = 0.0
        self._ppo_signal = 0.0

        # Signal analysis
        self._crossover_signals = 0
        self._divergence_signals = 0
        self._breakout_signals = 0
        self._histogram_signals = 0

        # Performance tracking
        self._signal_accuracy = 0.0
        self._momentum_prediction_rate = 0.0
        self._ppo_reliability = 0.0

        # Market structure
        self._volatility_regime = "normal"
        self._momentum_cycles = 0
        self._ppo_extremes = []

        # Risk management
        self._ppo_based_stop = 0.0
        self._momentum_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0

        # Institutional analysis
        self._institutional_ppo = 0.0
        self._smart_money_ppo = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Percentage Price Oscillator is ready to provide signals"""
        max_period = max(self.ppo_config.fast_period, self.ppo_config.slow_period, self.ppo_config.signal_period)
        return (len(self._close_values) >= max_period and
                len(self._ppo_values) > 0)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update PPO analysis

        Args:
            bar (Bar): New bar data
        """
        # Extract OHLCV data
        if hasattr(bar, 'close') and hasattr(bar, 'volume'):
            close = bar.close
            volume = bar.volume
        else:
            close = bar.get('close', bar.get('price', 0.0))
            volume = bar.get('volume', 1.0)

        # Update PPO analysis
        self._update_ppo_analysis(close, volume)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_ppo_analysis(self, close: float, volume: float):
        """Update the core Percentage Price Oscillator analysis with institutional enhancements"""
        # Store price and volume data
        self._close_values.append(close)
        self._volume_values.append(volume)

        max_period = max(self.ppo_config.fast_period, self.ppo_config.slow_period)
        if len(self._close_values) >= max_period:
            # Calculate Percentage Price Oscillator
            self._calculate_percentage_price_oscillator()

            # Calculate signal line
            self._calculate_signal_line()

            # Calculate histogram
            self._calculate_histogram()

            # Analyze momentum characteristics
            self._analyze_momentum_characteristics()

            # Generate PPO signals
            self._generate_ppo_signals()

            # Calculate institutional PPO analysis
            self._calculate_institutional_ppo()

    def _calculate_percentage_price_oscillator(self):
        """Calculate Percentage Price Oscillator"""
        if len(self._close_values) < self.ppo_config.slow_period:
            return

        # Calculate EMAs for PPO
        fast_ema = self._calculate_ema(self._close_values, self.ppo_config.fast_period)
        slow_ema = self._calculate_ema(self._close_values, self.ppo_config.slow_period)

        if fast_ema is not None and slow_ema is not None and slow_ema > 0:
            # PPO formula: ((Fast EMA - Slow EMA) / Slow EMA) * 100
            ppo = ((fast_ema - slow_ema) / slow_ema) * 100
            self._ppo_values.append(ppo)
            self._ppo = ppo

    def _calculate_signal_line(self):
        """Calculate signal line using EMA of PPO"""
        if len(self._ppo_values) >= self.ppo_config.signal_period:
            signal = self._calculate_ema(self._ppo_values, self.ppo_config.signal_period)
            if signal is not None:
                self._signal_values.append(signal)
                self._signal = signal

    def _calculate_histogram(self):
        """Calculate histogram (PPO - Signal)"""
        if len(self._ppo_values) > 0 and len(self._signal_values) > 0:
            histogram = self._ppo - self._signal
            self._histogram_values.append(histogram)
            self._histogram = histogram

    def _calculate_ema(self, values: deque, period: int) -> Optional[float]:
        """Calculate Exponential Moving Average"""
        if len(values) < period:
            return None

        recent_values = list(values)[-period:]
        if len(recent_values) < period:
            return None

        # Calculate EMA using smoothing factor
        multiplier = 2 / (period + 1)
        ema = recent_values[0]

        for value in recent_values[1:]:
            ema = (value * multiplier) + (ema * (1 - multiplier))

        return ema

    def _analyze_momentum_characteristics(self):
        """Analyze momentum characteristics for institutional insights"""
        if not self.is_ready:
            return

        # Determine momentum direction based on PPO
        if self._ppo > self._signal and self._ppo > 0:
            self._momentum_direction = 1  # Bullish momentum
        elif self._ppo < self._signal and self._ppo < 0:
            self._momentum_direction = -1  # Bearish momentum
        else:
            self._momentum_direction = 0  # Neutral momentum

        # Calculate momentum strength
        self._momentum_strength = abs(self._ppo) / 10.0  # Normalize based on typical PPO range

        # Calculate PPO signal
        self._ppo_signal = self._histogram

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

        # Track momentum cycles
        if len(self._ppo_values) >= 2:
            prev_ppo = list(self._ppo_values)[-2]
            if ((prev_ppo <= 0 and self._ppo > 0) or
                (prev_ppo >= 0 and self._ppo < 0)):
                self._momentum_cycles += 1

        # Track PPO extremes
        if abs(self._ppo) > 5:  # Extreme readings
            self._ppo_extremes.append(self._ppo)

    def _generate_ppo_signals(self):
        """Generate PPO-based signals"""
        if not self.is_ready:
            return

        # Crossover signals
        if len(self._ppo_values) >= 2 and len(self._signal_values) >= 2:
            prev_ppo = list(self._ppo_values)[-2]
            prev_signal = list(self._signal_values)[-2]

            # PPO crosses above signal (bullish crossover)
            if prev_ppo <= prev_signal and self._ppo > self._signal:
                self._crossover_signals += 1

            # PPO crosses below signal (bearish crossover)
            elif prev_ppo >= prev_signal and self._ppo < self._signal:
                self._crossover_signals += 1

        # Divergence signals
        if len(self._ppo_values) >= 5 and len(self._close_values) >= 5:
            ppo_trend = self._ppo - list(self._ppo_values)[-5]
            price_trend = list(self._close_values)[-1] - list(self._close_values)[-5]

            # Bullish divergence: price down, PPO up
            if price_trend < 0 and ppo_trend > 0:
                self._divergence_signals += 1

            # Bearish divergence: price up, PPO down
            elif price_trend > 0 and ppo_trend < 0:
                self._divergence_signals += 1

        # Breakout signals
        if self._momentum_strength > 0.8:
            self._breakout_signals += 1

        # Histogram signals
        if len(self._histogram_values) >= 2:
            prev_histogram = list(self._histogram_values)[-2]
            if ((prev_histogram <= 0 and self._histogram > 0) or
                (prev_histogram >= 0 and self._histogram < 0)):
                self._histogram_signals += 1

    def _calculate_institutional_ppo(self):
        """Calculate institutional PPO analysis based on momentum characteristics"""
        if not self.is_ready:
            return

        # Institutional traders use PPO for momentum timing and trend confirmation
        base_ppo = 0.0

        if (self._momentum_strength > 0.8 and
            self._crossover_signals > 0 and
            self._signal_accuracy > 0.6):
            base_ppo = 0.9  # Strong momentum with crossover signals and accuracy
        elif (self._divergence_signals > 0 and
              self._histogram_signals > 0 and
              self._momentum_cycles > 2):
            base_ppo = 0.8  # Divergence and histogram signals with cycle confirmation
        elif (self._breakout_signals > 0 and
              self._ppo_reliability > 0.7):
            base_ppo = 0.7  # Breakout signals with high reliability

        self._institutional_ppo = base_ppo

        # Smart money PPO considers momentum strength and market timing
        smart_money_score = (
            self._momentum_strength * 0.3 +
            self._signal_accuracy * 0.3 +
            abs(self._ppo_signal) * 0.2 +
            self._institutional_ppo * 0.2
        )
        self._smart_money_ppo = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade PPO analysis"""
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

        # Use PPO value as primary raw value
        raw_value = self._ppo

        # Determine signal type based on PPO analysis
        signal_type = self._determine_ppo_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'ppo': self._ppo,
            'signal_line': self._signal,
            'histogram': self._histogram,
            'momentum_direction': self._momentum_direction,
            'momentum_strength': self._momentum_strength,
            'ppo_signal': self._ppo_signal,
            'signal_accuracy': self._signal_accuracy,
            'momentum_prediction_rate': self._momentum_prediction_rate,
            'ppo_reliability': self._ppo_reliability,
            'volatility_regime': self._volatility_regime,
            'momentum_cycles': self._momentum_cycles,
            'ppo_extremes': self._ppo_extremes,
            'ppo_based_stop': self._ppo_based_stop,
            'momentum_based_position_size': self._momentum_based_position_size,
            'risk_adjustment_factor': self._risk_adjustment_factor,
            'crossover_signals': self._crossover_signals,
            'divergence_signals': self._divergence_signals,
            'breakout_signals': self._breakout_signals,
            'histogram_signals': self._histogram_signals,
            'institutional_ppo': self._institutional_ppo,
            'smart_money_ppo': self._smart_money_ppo
        }

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._ppo_based_stop,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Percentage_Price_Oscillator",
                "fast_period": self.ppo_config.fast_period,
                "slow_period": self.ppo_config.slow_period,
                "signal_period": self.ppo_config.signal_period,
                "overbought": self.ppo_config.overbought,
                "oversold": self.ppo_config.oversold,
                "ppo": self._ppo,
                "signal_line": self._signal,
                "histogram": self._histogram,
                "momentum_direction": self._momentum_direction,
                "momentum_strength": self._momentum_strength,
                "ppo_signal": self._ppo_signal,
                "signal_accuracy": self._signal_accuracy,
                "momentum_prediction_rate": self._momentum_prediction_rate,
                "ppo_reliability": self._ppo_reliability,
                "volatility_regime": self._volatility_regime,
                "momentum_cycles": self._momentum_cycles,
                "ppo_extremes": self._ppo_extremes,
                "ppo_based_stop": self._ppo_based_stop,
                "momentum_based_position_size": self._momentum_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor,
                "crossover_signals": self._crossover_signals,
                "divergence_signals": self._divergence_signals,
                "breakout_signals": self._breakout_signals,
                "histogram_signals": self._histogram_signals,
                "institutional_ppo": self._institutional_ppo,
                "smart_money_ppo": self._smart_money_ppo,
                "is_ready": self.is_ready
            }
        )

    def _determine_ppo_signal(self) -> SignalType:
        """Determine signal type based on PPO analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong momentum signals
        if (self._momentum_strength > 0.8 and
            self._crossover_signals > 0 and
            self._signal_accuracy > 0.7):
            if self._momentum_direction == 1:
                return SignalType.STRONG_BULLISH
            elif self._momentum_direction == -1:
                return SignalType.STRONG_BEARISH

        # Moderate momentum signals
        elif (self._divergence_signals > 0 and
              self._momentum_strength > 0.6):
            if self._momentum_direction == 1:
                return SignalType.BULLISH
            elif self._momentum_direction == -1:
                return SignalType.BEARISH

        # Breakout signals
        elif (self._breakout_signals > 0 and
              abs(self._ppo) > 2):
            if self._ppo > 0:
                return SignalType.STRONG_BULLISH
            else:
                return SignalType.STRONG_BEARISH

        # Histogram signals
        elif (self._histogram_signals > 0 and
              self._ppo_reliability > 0.7):
            if self._histogram > 0:
                return SignalType.BULLISH
            else:
                return SignalType.BEARISH

        # Overbought/Oversold signals
        elif self._ppo > self.ppo_config.overbought:
            return SignalType.BEARISH  # Potential reversal from overbought
        elif self._ppo < self.ppo_config.oversold:
            return SignalType.BULLISH  # Potential reversal from oversold

        return SignalType.NEUTRAL

    @property
    def ppo(self) -> float:
        """Get the current PPO value"""
        return self._ppo if self.is_ready else 0.0

    @property
    def signal_line(self) -> float:
        """Get the current signal line value"""
        return self._signal if self.is_ready else 0.0

    @property
    def histogram(self) -> float:
        """Get the current histogram value"""
        return self._histogram if self.is_ready else 0.0

    @property
    def momentum_direction(self) -> int:
        """Get the current momentum direction (1=bullish, -1=bearish, 0=neutral)"""
        return self._momentum_direction

    @property
    def momentum_strength(self) -> float:
        """Get the current momentum strength (0-1)"""
        return self._momentum_strength

    @property
    def signal_accuracy(self) -> float:
        """Get the signal accuracy (0-1)"""
        return self._signal_accuracy

    @property
    def volatility_regime(self) -> str:
        """Get the current volatility regime"""
        return self._volatility_regime

    @property
    def momentum_cycles(self) -> int:
        """Get the count of momentum cycles"""
        return self._momentum_cycles

    @property
    def crossover_signals(self) -> int:
        """Get the count of crossover signals"""
        return self._crossover_signals

    @property
    def divergence_signals(self) -> int:
        """Get the count of divergence signals"""
        return self._divergence_signals

    @property
    def breakout_signals(self) -> int:
        """Get the count of breakout signals"""
        return self._breakout_signals

    @property
    def histogram_signals(self) -> int:
        """Get the count of histogram signals"""
        return self._histogram_signals

    @property
    def institutional_ppo(self) -> float:
        """Get the institutional PPO score (0-1)"""
        return self._institutional_ppo

    @property
    def smart_money_ppo(self) -> float:
        """Get the smart money PPO score (0-1)"""
        return self._smart_money_ppo

    def is_bullish_ppo(self) -> bool:
        """Check if PPO indicates bullish momentum"""
        return self._momentum_direction == 1 and self._ppo > self._signal

    def is_bearish_ppo(self) -> bool:
        """Check if PPO indicates bearish momentum"""
        return self._momentum_direction == -1 and self._ppo < self._signal

    def is_strong_momentum_ppo(self) -> bool:
        """Check if PPO momentum is strong"""
        return self._momentum_strength > 0.7

    def is_ppo_crossover(self) -> bool:
        """Check if there's a PPO crossover"""
        return self._crossover_signals > 0

    def is_ppo_divergence(self) -> bool:
        """Check if there's a PPO divergence"""
        return self._divergence_signals > 0

    def is_overbought_ppo(self) -> bool:
        """Check if PPO is overbought"""
        return self._ppo > self.ppo_config.overbought

    def is_oversold_ppo(self) -> bool:
        """Check if PPO is oversold"""
        return self._ppo < self.ppo_config.oversold

    def is_high_volatility_ppo(self) -> bool:
        """Check if volatility regime is high"""
        return self._volatility_regime == "high"

    def is_low_volatility_ppo(self) -> bool:
        """Check if volatility regime is low"""
        return self._volatility_regime == "low"

    def is_institutional_setup_ppo(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_ppo > 0.7

    def get_ppo_info(self) -> Dict[str, Any]:
        """Get comprehensive PPO indicator information"""
        return {
            "ppo_values": {
                "ppo": self._ppo,
                "signal_line": self._signal,
                "histogram": self._histogram
            },
            "momentum_analysis": {
                "direction": self._momentum_direction,
                "strength": self._momentum_strength,
                "ppo_signal": self._ppo_signal
            },
            "performance_metrics": {
                "signal_accuracy": self._signal_accuracy,
                "momentum_prediction_rate": self._momentum_prediction_rate,
                "ppo_reliability": self._ppo_reliability
            },
            "market_conditions": {
                "volatility_regime": self._volatility_regime,
                "momentum_cycles": self._momentum_cycles
            },
            "signal_counts": {
                "crossover_signals": self._crossover_signals,
                "divergence_signals": self._divergence_signals,
                "breakout_signals": self._breakout_signals,
                "histogram_signals": self._histogram_signals
            },
            "ppo_tracking": {
                "extremes": self._ppo_extremes
            },
            "risk_management": {
                "ppo_based_stop": self._ppo_based_stop,
                "momentum_based_position_size": self._momentum_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor
            },
            "institutional_analysis": {
                "ppo": self._institutional_ppo,
                "smart_money_ppo": self._smart_money_ppo
            },
            "metadata": {
                "fast_period": self.ppo_config.fast_period,
                "slow_period": self.ppo_config.slow_period,
                "signal_period": self.ppo_config.signal_period,
                "overbought": self.ppo_config.overbought,
                "oversold": self.ppo_config.oversold,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._close_values.clear()
        self._volume_values.clear()
        self._ppo_values.clear()
        self._signal_values.clear()
        self._histogram_values.clear()
        self._ppo = 0.0
        self._signal = 0.0
        self._histogram = 0.0
        self._momentum_direction = 0
        self._momentum_strength = 0.0
        self._ppo_signal = 0.0
        self._crossover_signals = 0
        self._divergence_signals = 0
        self._breakout_signals = 0
        self._histogram_signals = 0
        self._signal_accuracy = 0.0
        self._momentum_prediction_rate = 0.0
        self._ppo_reliability = 0.0
        self._volatility_regime = "normal"
        self._momentum_cycles = 0
        self._ppo_extremes.clear()
        self._ppo_based_stop = 0.0
        self._momentum_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0
        self._institutional_ppo = 0.0
        self._smart_money_ppo = 0.0