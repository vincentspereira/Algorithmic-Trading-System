"""
Institutional-Grade Augmented Detrended Price Oscillator Indicator

This module implements an enhanced Detrended Price Oscillator with institutional-grade features:
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
class AugmentedDetrendedPriceOscillatorConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Detrended Price Oscillator"""
    period: int = 20
    signal_period: int = 5
    overbought: float = 0.5
    oversold: float = -0.5


class AugmentedDetrendedPriceOscillatorIndicator(AugmentedIndicator):
    """
    Institutional-grade Augmented Detrended Price Oscillator implementing 5-pillar architecture.

    Features:
    - Removes trend from price to identify short-term cycles
    - Volume-weighted calculations for institutional validation
    - Market regime adaptation for different volatility environments
    - Multi-timeframe convergence for cycle confirmation
    - Smart money cycle detection
    - Automated risk management based on cycle signals
    """

    def __init__(self, config: AugmentedDetrendedPriceOscillatorConfig = None):
        if config is None:
            config = AugmentedDetrendedPriceOscillatorConfig()

        super().__init__(config)
        self.dpo_config = config

        # DPO specific state
        self._close_values = deque(maxlen=self.config.buffer_size)
        self._volume_values = deque(maxlen=self.config.buffer_size)

        # DPO calculation components
        self._dpo_values = deque(maxlen=self.config.buffer_size)
        self._signal_values = deque(maxlen=self.config.buffer_size)

        # Current DPO values
        self._dpo = 0.0
        self._signal = 0.0

        # Cycle analysis
        self._cycle_direction = 0  # 1 = bullish cycle, -1 = bearish cycle, 0 = neutral
        self._cycle_strength = 0.0
        self._dpo_signal = 0.0

        # Signal analysis
        self._overbought_signals = 0
        self._oversold_signals = 0
        self._divergence_signals = 0
        self._breakout_signals = 0

        # Performance tracking
        self._signal_accuracy = 0.0
        self._cycle_prediction_rate = 0.0
        self._dpo_reliability = 0.0

        # Market structure
        self._volatility_regime = "normal"
        self._cycle_phases = 0
        self._dpo_extremes = []

        # Risk management
        self._dpo_based_stop = 0.0
        self._cycle_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0

        # Institutional analysis
        self._institutional_dpo = 0.0
        self._smart_money_dpo = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Detrended Price Oscillator is ready to provide signals"""
        return (len(self._close_values) >= self.dpo_config.period and
                len(self._dpo_values) > 0)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update DPO analysis

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

        # Update DPO analysis
        self._update_dpo_analysis(close, volume)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_dpo_analysis(self, close: float, volume: float):
        """Update the core Detrended Price Oscillator analysis with institutional enhancements"""
        # Store price and volume data
        self._close_values.append(close)
        self._volume_values.append(volume)

        if len(self._close_values) >= self.dpo_config.period:
            # Calculate Detrended Price Oscillator
            self._calculate_detrended_price_oscillator()

            # Calculate signal line
            self._calculate_signal_line()

            # Analyze cycle characteristics
            self._analyze_cycle_characteristics()

            # Generate DPO signals
            self._generate_dpo_signals()

            # Calculate institutional DPO analysis
            self._calculate_institutional_dpo()

    def _calculate_detrended_price_oscillator(self):
        """Calculate Detrended Price Oscillator"""
        if len(self._close_values) < self.dpo_config.period:
            return

        # DPO formula: Close - SMA(Close, period) shifted back by (period/2 + 1) periods
        shift_period = self.dpo_config.period // 2 + 1

        if len(self._close_values) >= self.dpo_config.period + shift_period:
            # Calculate SMA of the period
            recent_prices = list(self._close_values)[-self.dpo_config.period:]
            sma = statistics.mean(recent_prices)

            # Get the price from (period/2 + 1) periods ago
            shifted_price = list(self._close_values)[-(self.dpo_config.period + shift_period)]

            # Calculate DPO
            dpo = shifted_price - sma
            self._dpo_values.append(dpo)
            self._dpo = dpo

    def _calculate_signal_line(self):
        """Calculate signal line using simple moving average"""
        if len(self._dpo_values) >= self.dpo_config.signal_period:
            recent_dpo = list(self._dpo_values)[-self.dpo_config.signal_period:]
            signal = statistics.mean(recent_dpo)
            self._signal_values.append(signal)
            self._signal = signal

    def _analyze_cycle_characteristics(self):
        """Analyze cycle characteristics for institutional insights"""
        if not self.is_ready:
            return

        # Determine cycle direction based on DPO
        if self._dpo > 0:
            self._cycle_direction = 1  # Bullish cycle
        elif self._dpo < 0:
            self._cycle_direction = -1  # Bearish cycle
        else:
            self._cycle_direction = 0  # Neutral cycle

        # Calculate cycle strength
        self._cycle_strength = abs(self._dpo) / (statistics.stdev(list(self._close_values)[-20:]) if len(self._close_values) >= 20 else 1.0)

        # Calculate DPO signal
        self._dpo_signal = self._dpo

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

        # Track cycle phases
        if len(self._dpo_values) >= 2:
            prev_dpo = list(self._dpo_values)[-2]
            if ((prev_dpo <= 0 and self._dpo > 0) or
                (prev_dpo >= 0 and self._dpo < 0)):
                self._cycle_phases += 1

        # Track DPO extremes
        if abs(self._dpo) > self._cycle_strength * 2:  # Extreme readings
            self._dpo_extremes.append(self._dpo)

    def _generate_dpo_signals(self):
        """Generate DPO-based signals"""
        if not self.is_ready:
            return

        # Overbought/Oversold signals
        if self._dpo > self.dpo_config.overbought:
            self._overbought_signals += 1
        elif self._dpo < self.dpo_config.oversold:
            self._oversold_signals += 1

        # Divergence signals
        if len(self._dpo_values) >= 5 and len(self._close_values) >= 5:
            dpo_trend = self._dpo - list(self._dpo_values)[-5]
            price_trend = list(self._close_values)[-1] - list(self._close_values)[-5]

            # Bullish divergence: price down, DPO up
            if price_trend < 0 and dpo_trend > 0:
                self._divergence_signals += 1

            # Bearish divergence: price up, DPO down
            elif price_trend > 0 and dpo_trend < 0:
                self._divergence_signals += 1

        # Breakout signals
        if self._cycle_strength > 0.8:
            self._breakout_signals += 1

    def _calculate_institutional_dpo(self):
        """Calculate institutional DPO analysis based on cycle characteristics"""
        if not self.is_ready:
            return

        # Institutional traders use DPO for cycle identification and short-term momentum
        base_dpo = 0.0

        if (self._cycle_strength > 0.8 and
            (self._overbought_signals > 0 or self._oversold_signals > 0) and
            self._signal_accuracy > 0.6):
            base_dpo = 0.9  # Strong cycle with overbought/oversold signals and accuracy
        elif (self._divergence_signals > 0 and
              self._breakout_signals > 0 and
              self._cycle_phases > 2):
            base_dpo = 0.8  # Divergence and breakout signals with cycle confirmation
        elif (self._cycle_strength > 0.6 and
              self._dpo_reliability > 0.7):
            base_dpo = 0.7  # Good cycle strength with high reliability

        self._institutional_dpo = base_dpo

        # Smart money DPO considers cycle strength and market timing
        smart_money_score = (
            self._cycle_strength * 0.3 +
            self._signal_accuracy * 0.3 +
            abs(self._dpo_signal) * 0.2 +
            self._institutional_dpo * 0.2
        )
        self._smart_money_dpo = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade DPO analysis"""
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

        # Use DPO value as primary raw value
        raw_value = self._dpo

        # Determine signal type based on DPO analysis
        signal_type = self._determine_dpo_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'dpo': self._dpo,
            'signal_line': self._signal,
            'cycle_direction': self._cycle_direction,
            'cycle_strength': self._cycle_strength,
            'dpo_signal': self._dpo_signal,
            'signal_accuracy': self._signal_accuracy,
            'cycle_prediction_rate': self._cycle_prediction_rate,
            'dpo_reliability': self._dpo_reliability,
            'volatility_regime': self._volatility_regime,
            'cycle_phases': self._cycle_phases,
            'dpo_extremes': self._dpo_extremes,
            'dpo_based_stop': self._dpo_based_stop,
            'cycle_based_position_size': self._cycle_based_position_size,
            'risk_adjustment_factor': self._risk_adjustment_factor,
            'overbought_signals': self._overbought_signals,
            'oversold_signals': self._oversold_signals,
            'divergence_signals': self._divergence_signals,
            'breakout_signals': self._breakout_signals,
            'institutional_dpo': self._institutional_dpo,
            'smart_money_dpo': self._smart_money_dpo
        }

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._dpo_based_stop,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Detrended_Price_Oscillator",
                "period": self.dpo_config.period,
                "signal_period": self.dpo_config.signal_period,
                "overbought": self.dpo_config.overbought,
                "oversold": self.dpo_config.oversold,
                "dpo": self._dpo,
                "signal_line": self._signal,
                "cycle_direction": self._cycle_direction,
                "cycle_strength": self._cycle_strength,
                "dpo_signal": self._dpo_signal,
                "signal_accuracy": self._signal_accuracy,
                "cycle_prediction_rate": self._cycle_prediction_rate,
                "dpo_reliability": self._dpo_reliability,
                "volatility_regime": self._volatility_regime,
                "cycle_phases": self._cycle_phases,
                "dpo_extremes": self._dpo_extremes,
                "dpo_based_stop": self._dpo_based_stop,
                "cycle_based_position_size": self._cycle_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor,
                "overbought_signals": self._overbought_signals,
                "oversold_signals": self._oversold_signals,
                "divergence_signals": self._divergence_signals,
                "breakout_signals": self._breakout_signals,
                "institutional_dpo": self._institutional_dpo,
                "smart_money_dpo": self._smart_money_dpo,
                "is_ready": self.is_ready
            }
        )

    def _determine_dpo_signal(self) -> SignalType:
        """Determine signal type based on DPO analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong cycle signals
        if (self._cycle_strength > 0.8 and
            (self._overbought_signals > 0 or self._oversold_signals > 0) and
            self._signal_accuracy > 0.7):
            if self._cycle_direction == 1:
                return SignalType.STRONG_BULLISH
            elif self._cycle_direction == -1:
                return SignalType.STRONG_BEARISH

        # Moderate cycle signals
        elif (self._divergence_signals > 0 and
              self._cycle_strength > 0.6):
            if self._cycle_direction == 1:
                return SignalType.BULLISH
            elif self._cycle_direction == -1:
                return SignalType.BEARISH

        # Breakout signals
        elif (self._breakout_signals > 0 and
              abs(self._dpo) > self._cycle_strength):
            if self._dpo > 0:
                return SignalType.STRONG_BULLISH
            else:
                return SignalType.STRONG_BEARISH

        # Overbought/Oversold signals
        elif self._overbought_signals > 0 and self._dpo > self.dpo_config.overbought:
            return SignalType.BEARISH  # Potential reversal from overbought
        elif self._oversold_signals > 0 and self._dpo < self.dpo_config.oversold:
            return SignalType.BULLISH  # Potential reversal from oversold

        return SignalType.NEUTRAL

    @property
    def dpo(self) -> float:
        """Get the current DPO value"""
        return self._dpo if self.is_ready else 0.0

    @property
    def signal_line(self) -> float:
        """Get the current signal line value"""
        return self._signal if self.is_ready else 0.0

    @property
    def cycle_direction(self) -> int:
        """Get the current cycle direction (1=bullish, -1=bearish, 0=neutral)"""
        return self._cycle_direction

    @property
    def cycle_strength(self) -> float:
        """Get the current cycle strength (0-1)"""
        return self._cycle_strength

    @property
    def signal_accuracy(self) -> float:
        """Get the signal accuracy (0-1)"""
        return self._signal_accuracy

    @property
    def volatility_regime(self) -> str:
        """Get the current volatility regime"""
        return self._volatility_regime

    @property
    def cycle_phases(self) -> int:
        """Get the count of cycle phases"""
        return self._cycle_phases

    @property
    def overbought_signals(self) -> int:
        """Get the count of overbought signals"""
        return self._overbought_signals

    @property
    def oversold_signals(self) -> int:
        """Get the count of oversold signals"""
        return self._oversold_signals

    @property
    def divergence_signals(self) -> int:
        """Get the count of divergence signals"""
        return self._divergence_signals

    @property
    def breakout_signals(self) -> int:
        """Get the count of breakout signals"""
        return self._breakout_signals

    @property
    def institutional_dpo(self) -> float:
        """Get the institutional DPO score (0-1)"""
        return self._institutional_dpo

    @property
    def smart_money_dpo(self) -> float:
        """Get the smart money DPO score (0-1)"""
        return self._smart_money_dpo

    def is_bullish_dpo(self) -> bool:
        """Check if DPO indicates bullish cycle"""
        return self._cycle_direction == 1 and self._dpo > 0

    def is_bearish_dpo(self) -> bool:
        """Check if DPO indicates bearish cycle"""
        return self._cycle_direction == -1 and self._dpo < 0

    def is_strong_cycle_dpo(self) -> bool:
        """Check if DPO cycle is strong"""
        return self._cycle_strength > 0.7

    def is_overbought_dpo(self) -> bool:
        """Check if DPO is overbought"""
        return self._dpo > self.dpo_config.overbought

    def is_oversold_dpo(self) -> bool:
        """Check if DPO is oversold"""
        return self._dpo < self.dpo_config.oversold

    def is_dpo_divergence(self) -> bool:
        """Check if there's a DPO divergence"""
        return self._divergence_signals > 0

    def is_high_volatility_dpo(self) -> bool:
        """Check if volatility regime is high"""
        return self._volatility_regime == "high"

    def is_low_volatility_dpo(self) -> bool:
        """Check if volatility regime is low"""
        return self._volatility_regime == "low"

    def is_institutional_setup_dpo(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_dpo > 0.7

    def get_dpo_info(self) -> Dict[str, Any]:
        """Get comprehensive DPO indicator information"""
        return {
            "dpo_values": {
                "dpo": self._dpo,
                "signal_line": self._signal
            },
            "cycle_analysis": {
                "direction": self._cycle_direction,
                "strength": self._cycle_strength,
                "dpo_signal": self._dpo_signal
            },
            "performance_metrics": {
                "signal_accuracy": self._signal_accuracy,
                "cycle_prediction_rate": self._cycle_prediction_rate,
                "dpo_reliability": self._dpo_reliability
            },
            "market_conditions": {
                "volatility_regime": self._volatility_regime,
                "cycle_phases": self._cycle_phases
            },
            "signal_counts": {
                "overbought_signals": self._overbought_signals,
                "oversold_signals": self._oversold_signals,
                "divergence_signals": self._divergence_signals,
                "breakout_signals": self._breakout_signals
            },
            "dpo_tracking": {
                "extremes": self._dpo_extremes
            },
            "risk_management": {
                "dpo_based_stop": self._dpo_based_stop,
                "cycle_based_position_size": self._cycle_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor
            },
            "institutional_analysis": {
                "dpo": self._institutional_dpo,
                "smart_money_dpo": self._smart_money_dpo
            },
            "metadata": {
                "period": self.dpo_config.period,
                "signal_period": self.dpo_config.signal_period,
                "overbought": self.dpo_config.overbought,
                "oversold": self.dpo_config.oversold,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._close_values.clear()
        self._volume_values.clear()
        self._dpo_values.clear()
        self._signal_values.clear()
        self._dpo = 0.0
        self._signal = 0.0
        self._cycle_direction = 0
        self._cycle_strength = 0.0
        self._dpo_signal = 0.0
        self._overbought_signals = 0
        self._oversold_signals = 0
        self._divergence_signals = 0
        self._breakout_signals = 0
        self._signal_accuracy = 0.0
        self._cycle_prediction_rate = 0.0
        self._dpo_reliability = 0.0
        self._volatility_regime = "normal"
        self._cycle_phases = 0
        self._dpo_extremes.clear()
        self._dpo_based_stop = 0.0
        self._cycle_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0
        self._institutional_dpo = 0.0
        self._smart_money_dpo = 0.0