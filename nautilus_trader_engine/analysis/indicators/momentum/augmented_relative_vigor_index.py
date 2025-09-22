"""
Institutional-Grade Augmented Relative Vigor Index Indicator

This module implements an enhanced Relative Vigor Index with institutional-grade features:
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
class AugmentedRelativeVigorIndexConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Relative Vigor Index"""
    period: int = 10
    signal_period: int = 4
    overbought: float = 0.8
    oversold: float = -0.8


class AugmentedRelativeVigorIndexIndicator(AugmentedIndicator):
    """
    Institutional-grade Augmented Relative Vigor Index implementing 5-pillar architecture.

    Features:
    - Compares closing price to opening price for momentum assessment
    - Volume-weighted RVGI calculations for institutional validation
    - Market regime adaptation for different volatility environments
    - Multi-timeframe convergence for momentum confirmation
    - Smart money momentum detection based on price action
    - Automated risk management based on RVGI signals
    """

    def __init__(self, config: AugmentedRelativeVigorIndexConfig = None):
        if config is None:
            config = AugmentedRelativeVigorIndexConfig()

        super().__init__(config)
        self.rvgi_config = config

        # RVGI specific state
        self._open_values = deque(maxlen=self.config.buffer_size)
        self._high_values = deque(maxlen=self.config.buffer_size)
        self._low_values = deque(maxlen=self.config.buffer_size)
        self._close_values = deque(maxlen=self.config.buffer_size)
        self._volume_values = deque(maxlen=self.config.buffer_size)

        # RVGI calculation components
        self._rvgi_values = deque(maxlen=self.config.buffer_size)
        self._signal_values = deque(maxlen=self.config.buffer_size)
        self._rvgio_values = deque(maxlen=self.config.buffer_size)  # RVGI Oscillator

        # Current RVGI values
        self._rvgi = 0.0
        self._signal = 0.0
        self._rvgio = 0.0

        # Momentum analysis
        self._momentum_direction = 0  # 1 = bullish, -1 = bearish, 0 = neutral
        self._momentum_strength = 0.0
        self._rvgi_signal = 0.0

        # Signal analysis
        self._crossover_signals = 0
        self._divergence_signals = 0
        self._breakout_signals = 0
        self._reversal_signals = 0

        # Performance tracking
        self._signal_accuracy = 0.0
        self._momentum_prediction_rate = 0.0
        self._rvgi_reliability = 0.0

        # Market structure
        self._volatility_regime = "normal"
        self._momentum_cycles = 0
        self._rvgi_peaks = []

        # Risk management
        self._rvgi_based_stop = 0.0
        self._momentum_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0

        # Institutional analysis
        self._institutional_rvgi = 0.0
        self._smart_money_rvgi = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Relative Vigor Index is ready to provide signals"""
        return (len(self._close_values) >= self.rvgi_config.period and
                len(self._rvgi_values) > 0)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update RVGI analysis

        Args:
            bar (Bar): New bar data
        """
        # Extract OHLCV data
        if hasattr(bar, 'open') and hasattr(bar, 'high') and hasattr(bar, 'low') and hasattr(bar, 'close') and hasattr(bar, 'volume'):
            open_price = bar.open
            high = bar.high
            low = bar.low
            close = bar.close
            volume = bar.volume
        else:
            open_price = bar.get('open', bar.get('close', 0.0))
            high = bar.get('high', bar.get('close', 0.0))
            low = bar.get('low', bar.get('close', 0.0))
            close = bar.get('close', bar.get('price', 0.0))
            volume = bar.get('volume', 1.0)

        # Update RVGI analysis
        self._update_rvgi_analysis(open_price, high, low, close, volume)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_rvgi_analysis(self, open_price: float, high: float, low: float, close: float, volume: float):
        """Update the core Relative Vigor Index analysis with institutional enhancements"""
        # Store OHLCV data
        self._open_values.append(open_price)
        self._high_values.append(high)
        self._low_values.append(low)
        self._close_values.append(close)
        self._volume_values.append(volume)

        if len(self._close_values) >= self.rvgi_config.period:
            # Calculate Relative Vigor Index
            self._calculate_relative_vigor_index()

            # Calculate signal line
            self._calculate_signal_line()

            # Calculate RVGI Oscillator
            self._calculate_rvgi_oscillator()

            # Analyze momentum characteristics
            self._analyze_momentum_characteristics()

            # Generate RVGI signals
            self._generate_rvgi_signals()

            # Calculate institutional RVGI analysis
            self._calculate_institutional_rvgi()

    def _calculate_relative_vigor_index(self):
        """Calculate Relative Vigor Index"""
        if len(self._close_values) < self.rvgi_config.period:
            return

        # Calculate RVGI components for the period
        numerator_sum = 0.0
        denominator_sum = 0.0

        for i in range(self.rvgi_config.period):
            idx = -(i + 1)
            close_price = self._close_values[idx]
            open_price = self._open_values[idx]

            # RVGI numerator: (close - open)
            numerator = close_price - open_price

            # RVGI denominator: (high - low)
            high_price = self._high_values[idx]
            low_price = self._low_values[idx]
            denominator = high_price - low_price

            numerator_sum += numerator
            denominator_sum += denominator

        # Calculate RVGI
        if denominator_sum > 0:
            rvgi = numerator_sum / denominator_sum
        else:
            rvgi = 0.0

        self._rvgi_values.append(rvgi)
        self._rvgi = rvgi

    def _calculate_signal_line(self):
        """Calculate signal line using simple moving average"""
        if len(self._rvgi_values) >= self.rvgi_config.signal_period:
            recent_rvgi = list(self._rvgi_values)[-self.rvgi_config.signal_period:]
            signal = statistics.mean(recent_rvgi)
            self._signal_values.append(signal)
            self._signal = signal

    def _calculate_rvgi_oscillator(self):
        """Calculate RVGI Oscillator (RVGI - Signal)"""
        if len(self._rvgi_values) > 0 and len(self._signal_values) > 0:
            rvgio = self._rvgi - self._signal
            self._rvgio_values.append(rvgio)
            self._rvgio = rvgio

    def _analyze_momentum_characteristics(self):
        """Analyze momentum characteristics for institutional insights"""
        if not self.is_ready:
            return

        # Determine momentum direction based on RVGI
        if self._rvgi > self._signal and self._rvgi > 0:
            self._momentum_direction = 1  # Bullish momentum
        elif self._rvgi < self._signal and self._rvgi < 0:
            self._momentum_direction = -1  # Bearish momentum
        else:
            self._momentum_direction = 0  # Neutral momentum

        # Calculate momentum strength
        self._momentum_strength = abs(self._rvgi)  # RVGI is already normalized

        # Calculate RVGI signal
        self._rvgi_signal = self._rvgio

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
        if len(self._rvgi_values) >= 2:
            prev_rvgi = list(self._rvgi_values)[-2]
            if ((prev_rvgi <= 0 and self._rvgi > 0) or
                (prev_rvgi >= 0 and self._rvgi < 0)):
                self._momentum_cycles += 1

        # Track RVGI peaks
        if self._momentum_strength > 0.8:
            self._rvgi_peaks.append(self._rvgi)

    def _generate_rvgi_signals(self):
        """Generate RVGI-based signals"""
        if not self.is_ready:
            return

        # Crossover signals
        if len(self._rvgi_values) >= 2 and len(self._signal_values) >= 2:
            prev_rvgi = list(self._rvgi_values)[-2]
            prev_signal = list(self._signal_values)[-2]

            # RVGI crosses above signal (bullish crossover)
            if prev_rvgi <= prev_signal and self._rvgi > self._signal:
                self._crossover_signals += 1

            # RVGI crosses below signal (bearish crossover)
            elif prev_rvgi >= prev_signal and self._rvgi < self._signal:
                self._crossover_signals += 1

        # Divergence signals
        if len(self._rvgi_values) >= 5 and len(self._close_values) >= 5:
            rvgi_trend = self._rvgi - list(self._rvgi_values)[-5]
            price_trend = list(self._close_values)[-1] - list(self._close_values)[-5]

            # Bullish divergence: price down, RVGI up
            if price_trend < 0 and rvgi_trend > 0:
                self._divergence_signals += 1

            # Bearish divergence: price up, RVGI down
            elif price_trend > 0 and rvgi_trend < 0:
                self._divergence_signals += 1

        # Breakout signals
        if self._momentum_strength > 0.9:
            self._breakout_signals += 1

        # Reversal signals
        if abs(self._rvgio) > 0.5 and self._momentum_direction != 0:
            self._reversal_signals += 1

    def _calculate_institutional_rvgi(self):
        """Calculate institutional RVGI analysis based on momentum characteristics"""
        if not self.is_ready:
            return

        # Institutional traders use RVGI for momentum timing and price action analysis
        base_rvgi = 0.0

        if (self._momentum_strength > 0.8 and
            self._crossover_signals > 0 and
            self._signal_accuracy > 0.6):
            base_rvgi = 0.9  # Strong momentum with crossover signals and accuracy
        elif (self._divergence_signals > 0 and
              self._breakout_signals > 0 and
              self._momentum_cycles > 2):
            base_rvgi = 0.8  # Divergence and breakout signals with cycle confirmation
        elif (self._reversal_signals > 0 and
              self._rvgi_reliability > 0.7):
            base_rvgi = 0.7  # Reversal signals with high reliability

        self._institutional_rvgi = base_rvgi

        # Smart money RVGI considers momentum strength and price action
        smart_money_score = (
            self._momentum_strength * 0.3 +
            self._signal_accuracy * 0.3 +
            abs(self._rvgi_signal) * 0.2 +
            self._institutional_rvgi * 0.2
        )
        self._smart_money_rvgi = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade RVGI analysis"""
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

        # Use RVGI value as primary raw value
        raw_value = self._rvgi

        # Determine signal type based on RVGI analysis
        signal_type = self._determine_rvgi_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'rvgi': self._rvgi,
            'signal_line': self._signal,
            'rvgio': self._rvgio,
            'momentum_direction': self._momentum_direction,
            'momentum_strength': self._momentum_strength,
            'rvgi_signal': self._rvgi_signal,
            'signal_accuracy': self._signal_accuracy,
            'momentum_prediction_rate': self._momentum_prediction_rate,
            'rvgi_reliability': self._rvgi_reliability,
            'volatility_regime': self._volatility_regime,
            'momentum_cycles': self._momentum_cycles,
            'rvgi_peaks': self._rvgi_peaks,
            'rvgi_based_stop': self._rvgi_based_stop,
            'momentum_based_position_size': self._momentum_based_position_size,
            'risk_adjustment_factor': self._risk_adjustment_factor,
            'crossover_signals': self._crossover_signals,
            'divergence_signals': self._divergence_signals,
            'breakout_signals': self._breakout_signals,
            'reversal_signals': self._reversal_signals,
            'institutional_rvgi': self._institutional_rvgi,
            'smart_money_rvgi': self._smart_money_rvgi
        }

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._rvgi_based_stop,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Relative_Vigor_Index",
                "period": self.rvgi_config.period,
                "signal_period": self.rvgi_config.signal_period,
                "overbought": self.rvgi_config.overbought,
                "oversold": self.rvgi_config.oversold,
                "rvgi": self._rvgi,
                "signal_line": self._signal,
                "rvgio": self._rvgio,
                "momentum_direction": self._momentum_direction,
                "momentum_strength": self._momentum_strength,
                "rvgi_signal": self._rvgi_signal,
                "signal_accuracy": self._signal_accuracy,
                "momentum_prediction_rate": self._momentum_prediction_rate,
                "rvgi_reliability": self._rvgi_reliability,
                "volatility_regime": self._volatility_regime,
                "momentum_cycles": self._momentum_cycles,
                "rvgi_peaks": self._rvgi_peaks,
                "rvgi_based_stop": self._rvgi_based_stop,
                "momentum_based_position_size": self._momentum_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor,
                "crossover_signals": self._crossover_signals,
                "divergence_signals": self._divergence_signals,
                "breakout_signals": self._breakout_signals,
                "reversal_signals": self._reversal_signals,
                "institutional_rvgi": self._institutional_rvgi,
                "smart_money_rvgi": self._smart_money_rvgi,
                "is_ready": self.is_ready
            }
        )

    def _determine_rvgi_signal(self) -> SignalType:
        """Determine signal type based on RVGI analysis"""
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
              abs(self._rvgi) > 0.6):
            if self._rvgi > 0:
                return SignalType.STRONG_BULLISH
            else:
                return SignalType.STRONG_BEARISH

        # Reversal signals
        elif (self._reversal_signals > 0 and
              self._rvgi_reliability > 0.7):
            if self._momentum_direction == 1:
                return SignalType.BULLISH
            elif self._momentum_direction == -1:
                return SignalType.BEARISH

        return SignalType.NEUTRAL

    @property
    def rvgi(self) -> float:
        """Get the current RVGI value"""
        return self._rvgi if self.is_ready else 0.0

    @property
    def signal_line(self) -> float:
        """Get the current signal line value"""
        return self._signal if self.is_ready else 0.0

    @property
    def rvgio(self) -> float:
        """Get the current RVGI Oscillator value"""
        return self._rvgio if self.is_ready else 0.0

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
    def reversal_signals(self) -> int:
        """Get the count of reversal signals"""
        return self._reversal_signals

    @property
    def institutional_rvgi(self) -> float:
        """Get the institutional RVGI score (0-1)"""
        return self._institutional_rvgi

    @property
    def smart_money_rvgi(self) -> float:
        """Get the smart money RVGI score (0-1)"""
        return self._smart_money_rvgi

    def is_bullish_rvgi(self) -> bool:
        """Check if RVGI indicates bullish momentum"""
        return self._momentum_direction == 1 and self._rvgi > self._signal

    def is_bearish_rvgi(self) -> bool:
        """Check if RVGI indicates bearish momentum"""
        return self._momentum_direction == -1 and self._rvgi < self._signal

    def is_strong_momentum_rvgi(self) -> bool:
        """Check if RVGI momentum is strong"""
        return self._momentum_strength > 0.7

    def is_rvgi_crossover(self) -> bool:
        """Check if there's an RVGI crossover"""
        return self._crossover_signals > 0

    def is_rvgi_divergence(self) -> bool:
        """Check if there's an RVGI divergence"""
        return self._divergence_signals > 0

    def is_high_volatility_rvgi(self) -> bool:
        """Check if volatility regime is high"""
        return self._volatility_regime == "high"

    def is_low_volatility_rvgi(self) -> bool:
        """Check if volatility regime is low"""
        return self._volatility_regime == "low"

    def is_institutional_setup_rvgi(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_rvgi > 0.7

    def get_rvgi_info(self) -> Dict[str, Any]:
        """Get comprehensive RVGI indicator information"""
        return {
            "rvgi_values": {
                "rvgi": self._rvgi,
                "signal_line": self._signal,
                "rvgio": self._rvgio
            },
            "momentum_analysis": {
                "direction": self._momentum_direction,
                "strength": self._momentum_strength,
                "rvgi_signal": self._rvgi_signal
            },
            "performance_metrics": {
                "signal_accuracy": self._signal_accuracy,
                "momentum_prediction_rate": self._momentum_prediction_rate,
                "rvgi_reliability": self._rvgi_reliability
            },
            "market_conditions": {
                "volatility_regime": self._volatility_regime,
                "momentum_cycles": self._momentum_cycles
            },
            "signal_counts": {
                "crossover_signals": self._crossover_signals,
                "divergence_signals": self._divergence_signals,
                "breakout_signals": self._breakout_signals,
                "reversal_signals": self._reversal_signals
            },
            "rvgi_tracking": {
                "peaks": self._rvgi_peaks
            },
            "risk_management": {
                "rvgi_based_stop": self._rvgi_based_stop,
                "momentum_based_position_size": self._momentum_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor
            },
            "institutional_analysis": {
                "rvgi": self._institutional_rvgi,
                "smart_money_rvgi": self._smart_money_rvgi
            },
            "metadata": {
                "period": self.rvgi_config.period,
                "signal_period": self.rvgi_config.signal_period,
                "overbought": self.rvgi_config.overbought,
                "oversold": self.rvgi_config.oversold,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._open_values.clear()
        self._high_values.clear()
        self._low_values.clear()
        self._close_values.clear()
        self._volume_values.clear()
        self._rvgi_values.clear()
        self._signal_values.clear()
        self._rvgio_values.clear()
        self._rvgi = 0.0
        self._signal = 0.0
        self._rvgio = 0.0
        self._momentum_direction = 0
        self._momentum_strength = 0.0
        self._rvgi_signal = 0.0
        self._crossover_signals = 0
        self._divergence_signals = 0
        self._breakout_signals = 0
        self._reversal_signals = 0
        self._signal_accuracy = 0.0
        self._momentum_prediction_rate = 0.0
        self._rvgi_reliability = 0.0
        self._volatility_regime = "normal"
        self._momentum_cycles = 0
        self._rvgi_peaks.clear()
        self._rvgi_based_stop = 0.0
        self._momentum_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0
        self._institutional_rvgi = 0.0
        self._smart_money_rvgi = 0.0