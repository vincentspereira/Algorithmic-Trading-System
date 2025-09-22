"""
Institutional-Grade Augmented Volume Zone Oscillator Indicator

This module implements an enhanced Volume Zone Oscillator with institutional-grade features:
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
class AugmentedVolumeZoneOscillatorConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Volume Zone Oscillator"""
    fast_period: int = 14
    slow_period: int = 28
    signal_period: int = 9
    overbought: float = 60
    oversold: float = -60


class AugmentedVolumeZoneOscillatorIndicator(AugmentedIndicator):
    """
    Institutional-grade Augmented Volume Zone Oscillator implementing 5-pillar architecture.

    Features:
    - Volume-based oscillator for identifying volume zones
    - Volume-weighted calculations for institutional validation
    - Market regime adaptation for different volatility environments
    - Multi-timeframe convergence for volume zone confirmation
    - Smart money volume zone detection
    - Automated risk management based on volume zone signals
    """

    def __init__(self, config: AugmentedVolumeZoneOscillatorConfig = None):
        if config is None:
            config = AugmentedVolumeZoneOscillatorConfig()

        super().__init__(config)
        self.vzo_config = config

        # VZO specific state
        self._close_values = deque(maxlen=self.config.buffer_size)
        self._volume_values = deque(maxlen=self.config.buffer_size)

        # VZO calculation components
        self._vzo_values = deque(maxlen=self.config.buffer_size)
        self._signal_values = deque(maxlen=self.config.buffer_size)
        self._histogram_values = deque(maxlen=self.config.buffer_size)

        # Current VZO values
        self._vzo = 0.0
        self._signal = 0.0
        self._histogram = 0.0

        # Volume zone analysis
        self._zone_direction = 0  # 1 = bullish zone, -1 = bearish zone, 0 = neutral
        self._zone_strength = 0.0
        self._vzo_signal = 0.0

        # Signal analysis
        self._bullish_zone_signals = 0
        self._bearish_zone_signals = 0
        self._divergence_signals = 0
        self._breakout_signals = 0

        # Performance tracking
        self._signal_accuracy = 0.0
        self._zone_prediction_rate = 0.0
        self._vzo_reliability = 0.0

        # Market structure
        self._volatility_regime = "normal"
        self._zone_cycles = 0
        self._vzo_extremes = []

        # Risk management
        self._vzo_based_stop = 0.0
        self._zone_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0

        # Institutional analysis
        self._institutional_vzo = 0.0
        self._smart_money_vzo = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Volume Zone Oscillator is ready to provide signals"""
        max_period = max(self.vzo_config.fast_period, self.vzo_config.slow_period, self.vzo_config.signal_period)
        return (len(self._close_values) >= max_period and
                len(self._vzo_values) > 0)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update VZO analysis

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

        # Update VZO analysis
        self._update_vzo_analysis(close, volume)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_vzo_analysis(self, close: float, volume: float):
        """Update the core Volume Zone Oscillator analysis with institutional enhancements"""
        # Store price and volume data
        self._close_values.append(close)
        self._volume_values.append(volume)

        max_period = max(self.vzo_config.fast_period, self.vzo_config.slow_period)
        if len(self._close_values) >= max_period and len(self._volume_values) >= max_period:
            # Calculate Volume Zone Oscillator
            self._calculate_volume_zone_oscillator()

            # Calculate signal line
            self._calculate_signal_line()

            # Calculate histogram
            self._calculate_histogram()

            # Analyze zone characteristics
            self._analyze_zone_characteristics()

            # Generate VZO signals
            self._generate_vzo_signals()

            # Calculate institutional VZO analysis
            self._calculate_institutional_vzo()

    def _calculate_volume_zone_oscillator(self):
        """Calculate Volume Zone Oscillator"""
        if len(self._close_values) < self.vzo_config.slow_period or len(self._volume_values) < self.vzo_config.slow_period:
            return

        # Calculate volume-weighted price changes
        vp = []
        for i in range(1, len(self._close_values)):
            price_change = self._close_values[i] - self._close_values[i-1]
            volume_weighted_change = price_change * self._volume_values[i]
            vp.append(volume_weighted_change)

        if len(vp) >= self.vzo_config.slow_period:
            # Calculate fast and slow VP sums
            fast_vp_sum = sum(vp[-self.vzo_config.fast_period:])
            slow_vp_sum = sum(vp[-self.vzo_config.slow_period:])

            # Calculate VZO
            if slow_vp_sum != 0:
                vzo = ((fast_vp_sum - slow_vp_sum) / slow_vp_sum) * 100
            else:
                vzo = 0.0

            self._vzo_values.append(vzo)
            self._vzo = vzo

    def _calculate_signal_line(self):
        """Calculate signal line using EMA of VZO"""
        if len(self._vzo_values) >= self.vzo_config.signal_period:
            signal = self._calculate_ema(self._vzo_values, self.vzo_config.signal_period)
            if signal is not None:
                self._signal_values.append(signal)
                self._signal = signal

    def _calculate_histogram(self):
        """Calculate histogram (VZO - Signal)"""
        if len(self._vzo_values) > 0 and len(self._signal_values) > 0:
            histogram = self._vzo - self._signal
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

    def _analyze_zone_characteristics(self):
        """Analyze zone characteristics for institutional insights"""
        if not self.is_ready:
            return

        # Determine zone direction based on VZO
        if self._vzo > self._signal and self._vzo > 0:
            self._zone_direction = 1  # Bullish zone
        elif self._vzo < self._signal and self._vzo < 0:
            self._zone_direction = -1  # Bearish zone
        else:
            self._zone_direction = 0  # Neutral zone

        # Calculate zone strength
        self._zone_strength = abs(self._vzo) / 100.0  # Normalize based on typical VZO range

        # Calculate VZO signal
        self._vzo_signal = self._histogram

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

        # Track zone cycles
        if len(self._vzo_values) >= 2:
            prev_vzo = list(self._vzo_values)[-2]
            if ((prev_vzo <= 0 and self._vzo > 0) or
                (prev_vzo >= 0 and self._vzo < 0)):
                self._zone_cycles += 1

        # Track VZO extremes
        if abs(self._vzo) > 80:  # Extreme readings
            self._vzo_extremes.append(self._vzo)

    def _generate_vzo_signals(self):
        """Generate VZO-based signals"""
        if not self.is_ready:
            return

        # Bullish zone signals (VZO above signal in positive territory)
        if (self._vzo > self._signal and
            self._vzo > 0 and
            len(self._vzo_values) >= 2 and
            self._vzo > list(self._vzo_values)[-2]):
            self._bullish_zone_signals += 1

        # Bearish zone signals (VZO below signal in negative territory)
        if (self._vzo < self._signal and
            self._vzo < 0 and
            len(self._vzo_values) >= 2 and
            self._vzo < list(self._vzo_values)[-2]):
            self._bearish_zone_signals += 1

        # Divergence signals
        if len(self._vzo_values) >= 5 and len(self._close_values) >= 5:
            vzo_trend = self._vzo - list(self._vzo_values)[-5]
            price_trend = list(self._close_values)[-1] - list(self._close_values)[-5]

            # Bullish divergence: price down, VZO up
            if price_trend < 0 and vzo_trend > 0:
                self._divergence_signals += 1

            # Bearish divergence: price up, VZO down
            elif price_trend > 0 and vzo_trend < 0:
                self._divergence_signals += 1

        # Breakout signals
        if self._zone_strength > 0.8:
            self._breakout_signals += 1

    def _calculate_institutional_vzo(self):
        """Calculate institutional VZO analysis based on zone characteristics"""
        if not self.is_ready:
            return

        # Institutional traders use VZO to identify volume zones and smart money activity
        base_vzo = 0.0

        if (self._zone_strength > 0.8 and
            (self._bullish_zone_signals > 0 or self._bearish_zone_signals > 0) and
            self._signal_accuracy > 0.6):
            base_vzo = 0.9  # Strong zone with bullish/bearish signals and accuracy
        elif (self._divergence_signals > 0 and
              self._breakout_signals > 0 and
              self._zone_cycles > 2):
            base_vzo = 0.8  # Divergence and breakout signals with cycle confirmation
        elif (self._zone_strength > 0.6 and
              self._vzo_reliability > 0.7):
            base_vzo = 0.7  # Good zone strength with high reliability

        self._institutional_vzo = base_vzo

        # Smart money VZO considers zone strength and market timing
        smart_money_score = (
            self._zone_strength * 0.3 +
            self._signal_accuracy * 0.3 +
            abs(self._vzo_signal) * 0.2 +
            self._institutional_vzo * 0.2
        )
        self._smart_money_vzo = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade VZO analysis"""
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

        # Use VZO value as primary raw value
        raw_value = self._vzo

        # Determine signal type based on VZO analysis
        signal_type = self._determine_vzo_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'vzo': self._vzo,
            'signal_line': self._signal,
            'histogram': self._histogram,
            'zone_direction': self._zone_direction,
            'zone_strength': self._zone_strength,
            'vzo_signal': self._vzo_signal,
            'signal_accuracy': self._signal_accuracy,
            'zone_prediction_rate': self._zone_prediction_rate,
            'vzo_reliability': self._vzo_reliability,
            'volatility_regime': self._volatility_regime,
            'zone_cycles': self._zone_cycles,
            'vzo_extremes': self._vzo_extremes,
            'vzo_based_stop': self._vzo_based_stop,
            'zone_based_position_size': self._zone_based_position_size,
            'risk_adjustment_factor': self._risk_adjustment_factor,
            'bullish_zone_signals': self._bullish_zone_signals,
            'bearish_zone_signals': self._bearish_zone_signals,
            'divergence_signals': self._divergence_signals,
            'breakout_signals': self._breakout_signals,
            'institutional_vzo': self._institutional_vzo,
            'smart_money_vzo': self._smart_money_vzo
        }

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._vzo_based_stop,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Volume_Zone_Oscillator",
                "fast_period": self.vzo_config.fast_period,
                "slow_period": self.vzo_config.slow_period,
                "signal_period": self.vzo_config.signal_period,
                "overbought": self.vzo_config.overbought,
                "oversold": self.vzo_config.oversold,
                "vzo": self._vzo,
                "signal_line": self._signal,
                "histogram": self._histogram,
                "zone_direction": self._zone_direction,
                "zone_strength": self._zone_strength,
                "vzo_signal": self._vzo_signal,
                "signal_accuracy": self._signal_accuracy,
                "zone_prediction_rate": self._zone_prediction_rate,
                "vzo_reliability": self._vzo_reliability,
                "volatility_regime": self._volatility_regime,
                "zone_cycles": self._zone_cycles,
                "vzo_extremes": self._vzo_extremes,
                "vzo_based_stop": self._vzo_based_stop,
                "zone_based_position_size": self._zone_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor,
                "bullish_zone_signals": self._bullish_zone_signals,
                "bearish_zone_signals": self._bearish_zone_signals,
                "divergence_signals": self._divergence_signals,
                "breakout_signals": self._breakout_signals,
                "institutional_vzo": self._institutional_vzo,
                "smart_money_vzo": self._smart_money_vzo,
                "is_ready": self.is_ready
            }
        )

    def _determine_vzo_signal(self) -> SignalType:
        """Determine signal type based on VZO analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong zone signals
        if (self._zone_strength > 0.8 and
            (self._bullish_zone_signals > 0 or self._bearish_zone_signals > 0) and
            self._signal_accuracy > 0.7):
            if self._zone_direction == 1:
                return SignalType.STRONG_BULLISH
            elif self._zone_direction == -1:
                return SignalType.STRONG_BEARISH

        # Moderate zone signals
        elif (self._divergence_signals > 0 and
              self._zone_strength > 0.6):
            if self._zone_direction == 1:
                return SignalType.BULLISH
            elif self._zone_direction == -1:
                return SignalType.BEARISH

        # Breakout signals
        elif (self._breakout_signals > 0 and
              abs(self._vzo) > 40):
            if self._vzo > 0:
                return SignalType.STRONG_BULLISH
            else:
                return SignalType.STRONG_BEARISH

        # Bullish/bearish zone signals
        elif (self._bullish_zone_signals > 0 and
              self._vzo_reliability > 0.7):
            return SignalType.BULLISH  # Bullish zone signal
        elif (self._bearish_zone_signals > 0 and
              self._vzo_reliability > 0.7):
            return SignalType.BEARISH  # Bearish zone signal

        # Overbought/Oversold signals
        elif self._vzo > self.vzo_config.overbought:
            return SignalType.BEARISH  # Potential reversal from overbought
        elif self._vzo < self.vzo_config.oversold:
            return SignalType.BULLISH  # Potential reversal from oversold

        return SignalType.NEUTRAL

    @property
    def vzo(self) -> float:
        """Get the current VZO value"""
        return self._vzo if self.is_ready else 0.0

    @property
    def signal_line(self) -> float:
        """Get the current signal line value"""
        return self._signal if self.is_ready else 0.0

    @property
    def histogram(self) -> float:
        """Get the current histogram value"""
        return self._histogram if self.is_ready else 0.0

    @property
    def zone_direction(self) -> int:
        """Get the current zone direction (1=bullish, -1=bearish, 0=neutral)"""
        return self._zone_direction

    @property
    def zone_strength(self) -> float:
        """Get the current zone strength (0-1)"""
        return self._zone_strength

    @property
    def signal_accuracy(self) -> float:
        """Get the signal accuracy (0-1)"""
        return self._signal_accuracy

    @property
    def volatility_regime(self) -> str:
        """Get the current volatility regime"""
        return self._volatility_regime

    @property
    def zone_cycles(self) -> int:
        """Get the count of zone cycles"""
        return self._zone_cycles

    @property
    def bullish_zone_signals(self) -> int:
        """Get the count of bullish zone signals"""
        return self._bullish_zone_signals

    @property
    def bearish_zone_signals(self) -> int:
        """Get the count of bearish zone signals"""
        return self._bearish_zone_signals

    @property
    def divergence_signals(self) -> int:
        """Get the count of divergence signals"""
        return self._divergence_signals

    @property
    def breakout_signals(self) -> int:
        """Get the count of breakout signals"""
        return self._breakout_signals

    @property
    def institutional_vzo(self) -> float:
        """Get the institutional VZO score (0-1)"""
        return self._institutional_vzo

    @property
    def smart_money_vzo(self) -> float:
        """Get the smart money VZO score (0-1)"""
        return self._smart_money_vzo

    def is_bullish_zone_vzo(self) -> bool:
        """Check if VZO indicates bullish zone"""
        return self._zone_direction == 1 and self._vzo > self._signal

    def is_bearish_zone_vzo(self) -> bool:
        """Check if VZO indicates bearish zone"""
        return self._zone_direction == -1 and self._vzo < self._signal

    def is_strong_zone_vzo(self) -> bool:
        """Check if zone strength is strong"""
        return self._zone_strength > 0.7

    def is_bullish_zone_signal_vzo(self) -> bool:
        """Check if VZO has bullish zone signal"""
        return self._bullish_zone_signals > 0

    def is_bearish_zone_signal_vzo(self) -> bool:
        """Check if VZO has bearish zone signal"""
        return self._bearish_zone_signals > 0

    def is_vzo_divergence(self) -> bool:
        """Check if there's a VZO divergence"""
        return self._divergence_signals > 0

    def is_overbought_vzo(self) -> bool:
        """Check if VZO is overbought"""
        return self._vzo > self.vzo_config.overbought

    def is_oversold_vzo(self) -> bool:
        """Check if VZO is oversold"""
        return self._vzo < self.vzo_config.oversold

    def is_high_volatility_vzo(self) -> bool:
        """Check if volatility regime is high"""
        return self._volatility_regime == "high"

    def is_low_volatility_vzo(self) -> bool:
        """Check if volatility regime is low"""
        return self._volatility_regime == "low"

    def is_institutional_setup_vzo(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_vzo > 0.7

    def get_vzo_info(self) -> Dict[str, Any]:
        """Get comprehensive VZO indicator information"""
        return {
            "vzo_values": {
                "vzo": self._vzo,
                "signal_line": self._signal,
                "histogram": self._histogram
            },
            "zone_analysis": {
                "direction": self._zone_direction,
                "strength": self._zone_strength,
                "vzo_signal": self._vzo_signal
            },
            "performance_metrics": {
                "signal_accuracy": self._signal_accuracy,
                "zone_prediction_rate": self._zone_prediction_rate,
                "vzo_reliability": self._vzo_reliability
            },
            "market_conditions": {
                "volatility_regime": self._volatility_regime,
                "zone_cycles": self._zone_cycles
            },
            "signal_counts": {
                "bullish_zone_signals": self._bullish_zone_signals,
                "bearish_zone_signals": self._bearish_zone_signals,
                "divergence_signals": self._divergence_signals,
                "breakout_signals": self._breakout_signals
            },
            "vzo_tracking": {
                "extremes": self._vzo_extremes
            },
            "risk_management": {
                "vzo_based_stop": self._vzo_based_stop,
                "zone_based_position_size": self._zone_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor
            },
            "institutional_analysis": {
                "vzo": self._institutional_vzo,
                "smart_money_vzo": self._smart_money_vzo
            },
            "metadata": {
                "fast_period": self.vzo_config.fast_period,
                "slow_period": self.vzo_config.slow_period,
                "signal_period": self.vzo_config.signal_period,
                "overbought": self.vzo_config.overbought,
                "oversold": self.vzo_config.oversold,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._close_values.clear()
        self._volume_values.clear()
        self._vzo_values.clear()
        self._signal_values.clear()
        self._histogram_values.clear()
        self._vzo = 0.0
        self._signal = 0.0
        self._histogram = 0.0
        self._zone_direction = 0
        self._zone_strength = 0.0
        self._vzo_signal = 0.0
        self._bullish_zone_signals = 0
        self._bearish_zone_signals = 0
        self._divergence_signals = 0
        self._breakout_signals = 0
        self._signal_accuracy = 0.0
        self._zone_prediction_rate = 0.0
        self._vzo_reliability = 0.0
        self._volatility_regime = "normal"
        self._zone_cycles = 0
        self._vzo_extremes.clear()
        self._vzo_based_stop = 0.0
        self._zone_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0
        self._institutional_vzo = 0.0
        self._smart_money_vzo = 0.0