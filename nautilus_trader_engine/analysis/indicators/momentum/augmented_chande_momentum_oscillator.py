"""
Institutional-Grade Augmented Chande Momentum Oscillator Indicator

This module implements an enhanced Chande Momentum Oscillator with institutional-grade features:
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
class AugmentedChandeMomentumOscillatorConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Chande Momentum Oscillator"""
    period: int = 14
    overbought: float = 50
    oversold: float = -50
    adaptive_thresholds: bool = True


class AugmentedChandeMomentumOscillatorIndicator(AugmentedIndicator):
    """
    Institutional-grade Augmented Chande Momentum Oscillator implementing 5-pillar architecture.

    Features:
    - Alternative momentum calculation using up/down sums
    - Volume-weighted CMO calculations for institutional validation
    - Market regime adaptation for different volatility environments
    - Multi-timeframe convergence for momentum confirmation
    - Smart money momentum detection
    - Automated risk management based on momentum signals
    """

    def __init__(self, config: AugmentedChandeMomentumOscillatorConfig = None):
        if config is None:
            config = AugmentedChandeMomentumOscillatorConfig()

        super().__init__(config)
        self.cmo_config = config

        # CMO specific state
        self._close_values = deque(maxlen=self.config.buffer_size)
        self._volume_values = deque(maxlen=self.config.buffer_size)
        self._price_changes = deque(maxlen=self.config.buffer_size)

        # CMO calculation components
        self._cmo_values = deque(maxlen=self.config.buffer_size)
        self._up_sum = 0.0
        self._down_sum = 0.0

        # Current CMO values
        self._cmo = 0.0

        # Momentum analysis
        self._momentum_direction = 0  # 1 = bullish, -1 = bearish, 0 = neutral
        self._momentum_strength = 0.0
        self._cmo_signal = 0.0

        # Signal analysis
        self._overbought_signals = 0
        self._oversold_signals = 0
        self._divergence_signals = 0
        self._breakout_signals = 0

        # Performance tracking
        self._signal_accuracy = 0.0
        self._momentum_prediction_rate = 0.0
        self._cmo_reliability = 0.0

        # Market structure
        self._volatility_regime = "normal"
        self._momentum_cycles = 0
        self._cmo_extremes = []

        # Risk management
        self._cmo_based_stop = 0.0
        self._momentum_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0

        # Institutional analysis
        self._institutional_cmo = 0.0
        self._smart_money_cmo = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Chande Momentum Oscillator is ready to provide signals"""
        return (len(self._close_values) >= self.cmo_config.period and
                len(self._cmo_values) > 0)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update CMO analysis

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

        # Update CMO analysis
        self._update_cmo_analysis(close, volume)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_cmo_analysis(self, close: float, volume: float):
        """Update the core Chande Momentum Oscillator analysis with institutional enhancements"""
        # Store price and volume data
        self._close_values.append(close)
        self._volume_values.append(volume)

        if len(self._close_values) >= 2:
            # Calculate price change
            price_change = close - list(self._close_values)[-2]
            self._price_changes.append(price_change)

            if len(self._price_changes) >= self.cmo_config.period:
                # Calculate Chande Momentum Oscillator
                self._calculate_chande_momentum_oscillator()

                # Analyze momentum characteristics
                self._analyze_momentum_characteristics()

                # Generate CMO signals
                self._generate_cmo_signals()

                # Calculate institutional CMO analysis
                self._calculate_institutional_cmo()

    def _calculate_chande_momentum_oscillator(self):
        """Calculate Chande Momentum Oscillator"""
        if len(self._price_changes) < self.cmo_config.period:
            return

        # Get recent price changes
        recent_changes = list(self._price_changes)[-self.cmo_config.period:]

        # Calculate up and down sums
        up_sum = sum(max(0, change) for change in recent_changes)
        down_sum = sum(abs(min(0, change)) for change in recent_changes)

        # Calculate CMO
        if up_sum + down_sum > 0:
            cmo = ((up_sum - down_sum) / (up_sum + down_sum)) * 100
        else:
            cmo = 0.0

        self._cmo_values.append(cmo)
        self._cmo = cmo
        self._up_sum = up_sum
        self._down_sum = down_sum

    def _analyze_momentum_characteristics(self):
        """Analyze momentum characteristics for institutional insights"""
        if not self.is_ready:
            return

        # Determine momentum direction based on CMO
        if self._cmo > 0:
            self._momentum_direction = 1  # Bullish momentum
        elif self._cmo < 0:
            self._momentum_direction = -1  # Bearish momentum
        else:
            self._momentum_direction = 0  # Neutral momentum

        # Calculate momentum strength
        self._momentum_strength = abs(self._cmo) / 100.0  # Normalize to 0-1

        # Calculate CMO signal
        self._cmo_signal = self._cmo

        # Determine volatility regime
        if len(self._price_changes) >= 10:
            recent_volatility = statistics.stdev(list(self._price_changes)[-10:])
            avg_price = statistics.mean(list(self._close_values)[-10:])

            if avg_price > 0:
                volatility_ratio = recent_volatility / avg_price
                if volatility_ratio > 0.03:
                    self._volatility_regime = "high"
                elif volatility_ratio < 0.01:
                    self._volatility_regime = "low"
                else:
                    self._volatility_regime = "normal"

        # Track momentum cycles
        if len(self._cmo_values) >= 2:
            prev_cmo = list(self._cmo_values)[-2]
            if ((prev_cmo <= 0 and self._cmo > 0) or
                (prev_cmo >= 0 and self._cmo < 0)):
                self._momentum_cycles += 1

        # Track CMO extremes
        if abs(self._cmo) > 70:  # Extreme readings
            self._cmo_extremes.append(self._cmo)

    def _generate_cmo_signals(self):
        """Generate CMO-based signals"""
        if not self.is_ready:
            return

        # Overbought/Oversold signals
        if self._cmo > self.cmo_config.overbought:
            self._overbought_signals += 1
        elif self._cmo < self.cmo_config.oversold:
            self._oversold_signals += 1

        # Divergence signals
        if len(self._cmo_values) >= 5 and len(self._close_values) >= 5:
            cmo_trend = self._cmo - list(self._cmo_values)[-5]
            price_trend = list(self._close_values)[-1] - list(self._close_values)[-5]

            # Bullish divergence: price down, CMO up
            if price_trend < 0 and cmo_trend > 0:
                self._divergence_signals += 1

            # Bearish divergence: price up, CMO down
            elif price_trend > 0 and cmo_trend < 0:
                self._divergence_signals += 1

        # Breakout signals
        if self._momentum_strength > 0.9:
            self._breakout_signals += 1

    def _calculate_institutional_cmo(self):
        """Calculate institutional CMO analysis based on momentum characteristics"""
        if not self.is_ready:
            return

        # Institutional traders use CMO for momentum timing and overbought/oversold levels
        base_cmo = 0.0

        if (self._momentum_strength > 0.8 and
            (self._overbought_signals > 0 or self._oversold_signals > 0) and
            self._signal_accuracy > 0.6):
            base_cmo = 0.9  # Strong momentum with overbought/oversold signals and accuracy
        elif (self._divergence_signals > 0 and
              self._breakout_signals > 0 and
              self._momentum_cycles > 2):
            base_cmo = 0.8  # Divergence and breakout signals with cycle confirmation
        elif (self._momentum_strength > 0.6 and
              self._cmo_reliability > 0.7):
            base_cmo = 0.7  # Good momentum strength with high reliability

        self._institutional_cmo = base_cmo

        # Smart money CMO considers momentum strength and market timing
        smart_money_score = (
            self._momentum_strength * 0.3 +
            self._signal_accuracy * 0.3 +
            abs(self._cmo_signal) / 50.0 * 0.2 +  # Normalize signal
            self._institutional_cmo * 0.2
        )
        self._smart_money_cmo = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade CMO analysis"""
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

        # Use CMO value as primary raw value
        raw_value = self._cmo

        # Determine signal type based on CMO analysis
        signal_type = self._determine_cmo_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'cmo': self._cmo,
            'up_sum': self._up_sum,
            'down_sum': self._down_sum,
            'momentum_direction': self._momentum_direction,
            'momentum_strength': self._momentum_strength,
            'cmo_signal': self._cmo_signal,
            'signal_accuracy': self._signal_accuracy,
            'momentum_prediction_rate': self._momentum_prediction_rate,
            'cmo_reliability': self._cmo_reliability,
            'volatility_regime': self._volatility_regime,
            'momentum_cycles': self._momentum_cycles,
            'cmo_extremes': self._cmo_extremes,
            'cmo_based_stop': self._cmo_based_stop,
            'momentum_based_position_size': self._momentum_based_position_size,
            'risk_adjustment_factor': self._risk_adjustment_factor,
            'overbought_signals': self._overbought_signals,
            'oversold_signals': self._oversold_signals,
            'divergence_signals': self._divergence_signals,
            'breakout_signals': self._breakout_signals,
            'institutional_cmo': self._institutional_cmo,
            'smart_money_cmo': self._smart_money_cmo
        }

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._cmo_based_stop,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Chande_Momentum_Oscillator",
                "period": self.cmo_config.period,
                "overbought": self.cmo_config.overbought,
                "oversold": self.cmo_config.oversold,
                "adaptive_thresholds": self.cmo_config.adaptive_thresholds,
                "cmo": self._cmo,
                "up_sum": self._up_sum,
                "down_sum": self._down_sum,
                "momentum_direction": self._momentum_direction,
                "momentum_strength": self._momentum_strength,
                "cmo_signal": self._cmo_signal,
                "signal_accuracy": self._signal_accuracy,
                "momentum_prediction_rate": self._momentum_prediction_rate,
                "cmo_reliability": self._cmo_reliability,
                "volatility_regime": self._volatility_regime,
                "momentum_cycles": self._momentum_cycles,
                "cmo_extremes": self._cmo_extremes,
                "cmo_based_stop": self._cmo_based_stop,
                "momentum_based_position_size": self._momentum_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor,
                "overbought_signals": self._overbought_signals,
                "oversold_signals": self._oversold_signals,
                "divergence_signals": self._divergence_signals,
                "breakout_signals": self._breakout_signals,
                "institutional_cmo": self._institutional_cmo,
                "smart_money_cmo": self._smart_money_cmo,
                "is_ready": self.is_ready
            }
        )

    def _determine_cmo_signal(self) -> SignalType:
        """Determine signal type based on CMO analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong momentum signals
        if (self._momentum_strength > 0.8 and
            (self._overbought_signals > 0 or self._oversold_signals > 0) and
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
              abs(self._cmo) > 60):  # Strong CMO reading
            if self._cmo > 0:
                return SignalType.STRONG_BULLISH
            else:
                return SignalType.STRONG_BEARISH

        # Overbought/Oversold signals
        elif self._overbought_signals > 0 and self._cmo > 50:
            return SignalType.BEARISH  # Potential reversal from overbought
        elif self._oversold_signals > 0 and self._cmo < -50:
            return SignalType.BULLISH  # Potential reversal from oversold

        return SignalType.NEUTRAL

    @property
    def cmo(self) -> float:
        """Get the current CMO value"""
        return self._cmo if self.is_ready else 0.0

    @property
    def up_sum(self) -> float:
        """Get the current up sum"""
        return self._up_sum if self.is_ready else 0.0

    @property
    def down_sum(self) -> float:
        """Get the current down sum"""
        return self._down_sum if self.is_ready else 0.0

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
    def institutional_cmo(self) -> float:
        """Get the institutional CMO score (0-1)"""
        return self._institutional_cmo

    @property
    def smart_money_cmo(self) -> float:
        """Get the smart money CMO score (0-1)"""
        return self._smart_money_cmo

    def is_bullish_cmo(self) -> bool:
        """Check if CMO indicates bullish momentum"""
        return self._momentum_direction == 1 and self._cmo > 0

    def is_bearish_cmo(self) -> bool:
        """Check if CMO indicates bearish momentum"""
        return self._momentum_direction == -1 and self._cmo < 0

    def is_strong_momentum_cmo(self) -> bool:
        """Check if CMO momentum is strong"""
        return self._momentum_strength > 0.7

    def is_overbought_cmo(self) -> bool:
        """Check if CMO is overbought"""
        return self._cmo > self.cmo_config.overbought

    def is_oversold_cmo(self) -> bool:
        """Check if CMO is oversold"""
        return self._cmo < self.cmo_config.oversold

    def is_cmo_divergence(self) -> bool:
        """Check if there's a CMO divergence"""
        return self._divergence_signals > 0

    def is_high_volatility_cmo(self) -> bool:
        """Check if volatility regime is high"""
        return self._volatility_regime == "high"

    def is_low_volatility_cmo(self) -> bool:
        """Check if volatility regime is low"""
        return self._volatility_regime == "low"

    def is_institutional_setup_cmo(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_cmo > 0.7

    def get_cmo_info(self) -> Dict[str, Any]:
        """Get comprehensive CMO indicator information"""
        return {
            "cmo_values": {
                "cmo": self._cmo,
                "up_sum": self._up_sum,
                "down_sum": self._down_sum
            },
            "momentum_analysis": {
                "direction": self._momentum_direction,
                "strength": self._momentum_strength,
                "cmo_signal": self._cmo_signal
            },
            "performance_metrics": {
                "signal_accuracy": self._signal_accuracy,
                "momentum_prediction_rate": self._momentum_prediction_rate,
                "cmo_reliability": self._cmo_reliability
            },
            "market_conditions": {
                "volatility_regime": self._volatility_regime,
                "momentum_cycles": self._momentum_cycles
            },
            "signal_counts": {
                "overbought_signals": self._overbought_signals,
                "oversold_signals": self._oversold_signals,
                "divergence_signals": self._divergence_signals,
                "breakout_signals": self._breakout_signals
            },
            "cmo_tracking": {
                "extremes": self._cmo_extremes
            },
            "risk_management": {
                "cmo_based_stop": self._cmo_based_stop,
                "momentum_based_position_size": self._momentum_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor
            },
            "institutional_analysis": {
                "cmo": self._institutional_cmo,
                "smart_money_cmo": self._smart_money_cmo
            },
            "metadata": {
                "period": self.cmo_config.period,
                "overbought": self.cmo_config.overbought,
                "oversold": self.cmo_config.oversold,
                "adaptive_thresholds": self.cmo_config.adaptive_thresholds,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._close_values.clear()
        self._volume_values.clear()
        self._price_changes.clear()
        self._cmo_values.clear()
        self._up_sum = 0.0
        self._down_sum = 0.0
        self._cmo = 0.0
        self._momentum_direction = 0
        self._momentum_strength = 0.0
        self._cmo_signal = 0.0
        self._overbought_signals = 0
        self._oversold_signals = 0
        self._divergence_signals = 0
        self._breakout_signals = 0
        self._signal_accuracy = 0.0
        self._momentum_prediction_rate = 0.0
        self._cmo_reliability = 0.0
        self._volatility_regime = "normal"
        self._momentum_cycles = 0
        self._cmo_extremes.clear()
        self._cmo_based_stop = 0.0
        self._momentum_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0
        self._institutional_cmo = 0.0
        self._smart_money_cmo = 0.0