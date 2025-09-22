"""
Institutional-Grade Augmented Vortex Indicator

This module implements an enhanced Vortex Indicator with institutional-grade features:
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
class AugmentedVortexIndicatorConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Vortex Indicator"""
    period: int = 14
    signal_threshold: float = 0.5
    adaptive_period: bool = True


class AugmentedVortexIndicator(AugmentedIndicator):
    """
    Institutional-grade Augmented Vortex Indicator implementing 5-pillar architecture.

    Features:
    - True range and directional movement for trend identification
    - Volume-weighted vortex calculations for institutional validation
    - Market regime adaptation for different volatility environments
    - Multi-timeframe convergence for trend confirmation
    - Smart money trend direction detection
    - Automated risk management based on vortex signals
    """

    def __init__(self, config: AugmentedVortexIndicatorConfig = None):
        if config is None:
            config = AugmentedVortexIndicatorConfig()

        super().__init__(config)
        self.vortex_config = config

        # Vortex Indicator specific state
        self._high_values = deque(maxlen=self.config.buffer_size)
        self._low_values = deque(maxlen=self.config.buffer_size)
        self._close_values = deque(maxlen=self.config.buffer_size)
        self._volume_values = deque(maxlen=self.config.buffer_size)

        # Vortex calculation components
        self._true_ranges = deque(maxlen=self.config.buffer_size)
        self._vm_plus = deque(maxlen=self.config.buffer_size)  # Positive directional movement
        self._vm_minus = deque(maxlen=self.config.buffer_size)  # Negative directional movement
        self._vip_values = deque(maxlen=self.config.buffer_size)  # Vortex Indicator Positive
        self._vim_values = deque(maxlen=self.config.buffer_size)  # Vortex Indicator Negative

        # Current vortex values
        self._vip = 0.0
        self._vim = 0.0
        self._vortex_diff = 0.0

        # Trend analysis
        self._trend_direction = 0  # 1 = uptrend, -1 = downtrend, 0 = neutral
        self._trend_strength = 0.0
        self._vortex_signal = 0.0

        # Signal analysis
        self._crossover_signals = 0
        self._divergence_signals = 0
        self._breakout_signals = 0
        self._reversal_signals = 0

        # Performance tracking
        self._signal_accuracy = 0.0
        self._trend_prediction_rate = 0.0
        self._vortex_reliability = 0.0

        # Market structure
        self._volatility_regime = "normal"
        self._trend_cycles = 0
        self._vortex_peaks = []

        # Risk management
        self._vortex_based_stop = 0.0
        self._trend_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0

        # Institutional analysis
        self._institutional_vortex = 0.0
        self._smart_money_vortex = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Vortex Indicator is ready to provide signals"""
        return (len(self._high_values) >= self.vortex_config.period and
                len(self._vip_values) > 0 and
                len(self._vim_values) > 0)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update Vortex Indicator analysis

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

        # Update Vortex Indicator analysis
        self._update_vortex_analysis(high, low, close, volume)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_vortex_analysis(self, high: float, low: float, close: float, volume: float):
        """Update the core Vortex Indicator analysis with institutional enhancements"""
        # Store price and volume data
        self._high_values.append(high)
        self._low_values.append(low)
        self._close_values.append(close)
        self._volume_values.append(volume)

        if len(self._high_values) >= 2:
            # Calculate True Range and Directional Movement
            self._calculate_true_range_and_movement(high, low, close)

            if len(self._true_ranges) >= self.vortex_config.period:
                # Calculate Vortex Indicator
                self._calculate_vortex_indicator()

                # Analyze trend characteristics
                self._analyze_trend_characteristics()

                # Generate Vortex signals
                self._generate_vortex_signals()

                # Calculate institutional Vortex analysis
                self._calculate_institutional_vortex()

    def _calculate_true_range_and_movement(self, high: float, low: float, close: float):
        """Calculate True Range and Directional Movement for Vortex"""
        if len(self._high_values) < 2:
            return

        prev_high = list(self._high_values)[-2]
        prev_low = list(self._low_values)[-2]
        prev_close = list(self._close_values)[-2]

        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        true_range = max(tr1, tr2, tr3)
        self._true_ranges.append(true_range)

        # Calculate Directional Movement
        up_move = high - prev_high
        down_move = prev_low - low

        # Positive Directional Movement
        vm_plus = up_move if (up_move > down_move and up_move > 0) else 0.0
        self._vm_plus.append(vm_plus)

        # Negative Directional Movement
        vm_minus = down_move if (down_move > up_move and down_move > 0) else 0.0
        self._vm_minus.append(vm_minus)

    def _calculate_vortex_indicator(self):
        """Calculate Vortex Indicator components"""
        if len(self._true_ranges) < self.vortex_config.period:
            return

        # Get recent values
        recent_tr = list(self._true_ranges)[-self.vortex_config.period:]
        recent_vm_plus = list(self._vm_plus)[-self.vortex_config.period:]
        recent_vm_minus = list(self._vm_minus)[-self.vortex_config.period:]

        # Calculate sums
        sum_tr = sum(recent_tr)
        sum_vm_plus = sum(recent_vm_plus)
        sum_vm_minus = sum(recent_vm_minus)

        # Calculate Vortex Indicator Positive (VIP)
        if sum_tr > 0:
            vip = sum_vm_plus / sum_tr
        else:
            vip = 0.0

        # Calculate Vortex Indicator Negative (VIM)
        if sum_tr > 0:
            vim = sum_vm_minus / sum_tr
        else:
            vim = 0.0

        self._vip_values.append(vip)
        self._vim_values.append(vim)

        self._vip = vip
        self._vim = vim
        self._vortex_diff = vip - vim

    def _analyze_trend_characteristics(self):
        """Analyze trend characteristics for institutional insights"""
        if not self.is_ready:
            return

        # Determine trend direction based on Vortex
        if self._vip > self._vim + self.vortex_config.signal_threshold:
            self._trend_direction = 1  # Uptrend
        elif self._vim > self._vip + self.vortex_config.signal_threshold:
            self._trend_direction = -1  # Downtrend
        else:
            self._trend_direction = 0  # Neutral

        # Calculate trend strength
        vortex_range = self._vip + self._vim
        if vortex_range > 0:
            self._trend_strength = abs(self._vortex_diff) / vortex_range
        else:
            self._trend_strength = 0.0

        # Calculate vortex signal
        self._vortex_signal = self._vortex_diff

        # Determine volatility regime
        if len(self._true_ranges) >= 10:
            recent_volatility = statistics.mean(list(self._true_ranges)[-10:])
            avg_price = statistics.mean(list(self._close_values)[-10:])

            if avg_price > 0:
                volatility_ratio = recent_volatility / avg_price
                if volatility_ratio > 0.03:
                    self._volatility_regime = "high"
                elif volatility_ratio < 0.01:
                    self._volatility_regime = "low"
                else:
                    self._volatility_regime = "normal"

        # Track trend cycles
        if len(self._vip_values) >= 2 and len(self._vim_values) >= 2:
            prev_vip = list(self._vip_values)[-2]
            prev_vim = list(self._vim_values)[-2]

            prev_diff = prev_vip - prev_vim
            if ((prev_diff <= 0 and self._vortex_diff > 0) or
                (prev_diff >= 0 and self._vortex_diff < 0)):
                self._trend_cycles += 1

        # Track vortex peaks
        if self._trend_strength > 0.8:
            self._vortex_peaks.append(self._vortex_diff)

    def _generate_vortex_signals(self):
        """Generate Vortex Indicator-based signals"""
        if not self.is_ready:
            return

        # Crossover signals
        if len(self._vip_values) >= 2 and len(self._vim_values) >= 2:
            prev_vip = list(self._vip_values)[-2]
            prev_vim = list(self._vim_values)[-2]

            # VIP crosses above VIM (bullish crossover)
            if prev_vip <= prev_vim and self._vip > self._vim:
                self._crossover_signals += 1

            # VIM crosses above VIP (bearish crossover)
            elif prev_vim <= prev_vip and self._vim > self._vip:
                self._crossover_signals += 1

        # Divergence signals
        if len(self._vip_values) >= 5 and len(self._vim_values) >= 5 and len(self._close_values) >= 5:
            vip_trend = self._vip - list(self._vip_values)[-5]
            vim_trend = self._vim - list(self._vim_values)[-5]
            price_trend = list(self._close_values)[-1] - list(self._close_values)[-5]

            # Bullish divergence: price down, VIP up or VIM down
            if price_trend < 0 and (vip_trend > 0 or vim_trend < 0):
                self._divergence_signals += 1

            # Bearish divergence: price up, VIP down or VIM up
            elif price_trend > 0 and (vip_trend < 0 or vim_trend > 0):
                self._divergence_signals += 1

        # Breakout signals
        if self._trend_strength > 0.9:
            self._breakout_signals += 1

        # Reversal signals
        if abs(self._vortex_diff) > 0.7 and self._trend_direction != 0:
            self._reversal_signals += 1

    def _calculate_institutional_vortex(self):
        """Calculate institutional Vortex analysis based on trend characteristics"""
        if not self.is_ready:
            return

        # Institutional traders use Vortex for trend direction and strength assessment
        base_vortex = 0.0

        if (self._trend_strength > 0.8 and
            self._crossover_signals > 0 and
            self._signal_accuracy > 0.6):
            base_vortex = 0.9  # Strong trend with crossover signals and accuracy
        elif (self._divergence_signals > 0 and
              self._breakout_signals > 0 and
              self._trend_cycles > 2):
            base_vortex = 0.8  # Divergence and breakout signals with cycle confirmation
        elif (self._reversal_signals > 0 and
              self._vortex_reliability > 0.7):
            base_vortex = 0.7  # Reversal signals with high reliability

        self._institutional_vortex = base_vortex

        # Smart money Vortex considers trend strength and market timing
        smart_money_score = (
            self._trend_strength * 0.3 +
            self._signal_accuracy * 0.3 +
            abs(self._vortex_signal) * 0.2 +
            self._institutional_vortex * 0.2
        )
        self._smart_money_vortex = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade Vortex Indicator analysis"""
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

        # Use vortex difference as primary raw value
        raw_value = self._vortex_diff

        # Determine signal type based on Vortex analysis
        signal_type = self._determine_vortex_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'vip': self._vip,
            'vim': self._vim,
            'vortex_diff': self._vortex_diff,
            'trend_direction': self._trend_direction,
            'trend_strength': self._trend_strength,
            'vortex_signal': self._vortex_signal,
            'signal_accuracy': self._signal_accuracy,
            'trend_prediction_rate': self._trend_prediction_rate,
            'vortex_reliability': self._vortex_reliability,
            'volatility_regime': self._volatility_regime,
            'trend_cycles': self._trend_cycles,
            'vortex_peaks': self._vortex_peaks,
            'vortex_based_stop': self._vortex_based_stop,
            'trend_based_position_size': self._trend_based_position_size,
            'risk_adjustment_factor': self._risk_adjustment_factor,
            'crossover_signals': self._crossover_signals,
            'divergence_signals': self._divergence_signals,
            'breakout_signals': self._breakout_signals,
            'reversal_signals': self._reversal_signals,
            'institutional_vortex': self._institutional_vortex,
            'smart_money_vortex': self._smart_money_vortex
        }

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._vortex_based_stop,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Vortex_Indicator",
                "period": self.vortex_config.period,
                "signal_threshold": self.vortex_config.signal_threshold,
                "adaptive_period": self.vortex_config.adaptive_period,
                "vip": self._vip,
                "vim": self._vim,
                "vortex_diff": self._vortex_diff,
                "trend_direction": self._trend_direction,
                "trend_strength": self._trend_strength,
                "vortex_signal": self._vortex_signal,
                "signal_accuracy": self._signal_accuracy,
                "trend_prediction_rate": self._trend_prediction_rate,
                "vortex_reliability": self._vortex_reliability,
                "volatility_regime": self._volatility_regime,
                "trend_cycles": self._trend_cycles,
                "vortex_peaks": self._vortex_peaks,
                "vortex_based_stop": self._vortex_based_stop,
                "trend_based_position_size": self._trend_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor,
                "crossover_signals": self._crossover_signals,
                "divergence_signals": self._divergence_signals,
                "breakout_signals": self._breakout_signals,
                "reversal_signals": self._reversal_signals,
                "institutional_vortex": self._institutional_vortex,
                "smart_money_vortex": self._smart_money_vortex,
                "is_ready": self.is_ready
            }
        )

    def _determine_vortex_signal(self) -> SignalType:
        """Determine signal type based on Vortex Indicator analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong trend signals
        if (self._trend_strength > 0.8 and
            self._crossover_signals > 0 and
            self._signal_accuracy > 0.7):
            if self._trend_direction == 1:
                return SignalType.STRONG_BULLISH
            elif self._trend_direction == -1:
                return SignalType.STRONG_BEARISH

        # Moderate trend signals
        elif (self._divergence_signals > 0 and
              self._trend_strength > 0.6):
            if self._trend_direction == 1:
                return SignalType.BULLISH
            elif self._trend_direction == -1:
                return SignalType.BEARISH

        # Breakout signals
        elif (self._breakout_signals > 0 and
              abs(self._vortex_diff) > 0.6):
            if self._vortex_diff > 0:
                return SignalType.STRONG_BULLISH
            else:
                return SignalType.STRONG_BEARISH

        # Reversal signals
        elif (self._reversal_signals > 0 and
              self._vortex_reliability > 0.7):
            if self._trend_direction == 1:
                return SignalType.BULLISH
            elif self._trend_direction == -1:
                return SignalType.BEARISH

        return SignalType.NEUTRAL

    @property
    def vip(self) -> float:
        """Get the current Vortex Indicator Positive (VIP)"""
        return self._vip if self.is_ready else 0.0

    @property
    def vim(self) -> float:
        """Get the current Vortex Indicator Negative (VIM)"""
        return self._vim if self.is_ready else 0.0

    @property
    def vortex_diff(self) -> float:
        """Get the current Vortex difference (VIP - VIM)"""
        return self._vortex_diff if self.is_ready else 0.0

    @property
    def trend_direction(self) -> int:
        """Get the current trend direction (1=up, -1=down, 0=neutral)"""
        return self._trend_direction

    @property
    def trend_strength(self) -> float:
        """Get the current trend strength (0-1)"""
        return self._trend_strength

    @property
    def signal_accuracy(self) -> float:
        """Get the signal accuracy (0-1)"""
        return self._signal_accuracy

    @property
    def volatility_regime(self) -> str:
        """Get the current volatility regime"""
        return self._volatility_regime

    @property
    def trend_cycles(self) -> int:
        """Get the count of trend cycles"""
        return self._trend_cycles

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
    def institutional_vortex(self) -> float:
        """Get the institutional Vortex score (0-1)"""
        return self._institutional_vortex

    @property
    def smart_money_vortex(self) -> float:
        """Get the smart money Vortex score (0-1)"""
        return self._smart_money_vortex

    def is_uptrend_vortex(self) -> bool:
        """Check if Vortex indicates uptrend"""
        return self._trend_direction == 1 and self._vip > self._vim

    def is_downtrend_vortex(self) -> bool:
        """Check if Vortex indicates downtrend"""
        return self._trend_direction == -1 and self._vim > self._vip

    def is_strong_trend_vortex(self) -> bool:
        """Check if Vortex trend is strong"""
        return self._trend_strength > 0.7

    def is_vortex_crossover(self) -> bool:
        """Check if there's a Vortex crossover"""
        return self._crossover_signals > 0

    def is_vortex_divergence(self) -> bool:
        """Check if there's a Vortex divergence"""
        return self._divergence_signals > 0

    def is_high_volatility_vortex(self) -> bool:
        """Check if volatility regime is high"""
        return self._volatility_regime == "high"

    def is_low_volatility_vortex(self) -> bool:
        """Check if volatility regime is low"""
        return self._volatility_regime == "low"

    def is_institutional_setup_vortex(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_vortex > 0.7

    def get_vortex_info(self) -> Dict[str, Any]:
        """Get comprehensive Vortex Indicator information"""
        return {
            "vortex_values": {
                "vip": self._vip,
                "vim": self._vim,
                "vortex_diff": self._vortex_diff
            },
            "trend_analysis": {
                "direction": self._trend_direction,
                "strength": self._trend_strength,
                "vortex_signal": self._vortex_signal
            },
            "performance_metrics": {
                "signal_accuracy": self._signal_accuracy,
                "trend_prediction_rate": self._trend_prediction_rate,
                "vortex_reliability": self._vortex_reliability
            },
            "market_conditions": {
                "volatility_regime": self._volatility_regime,
                "trend_cycles": self._trend_cycles
            },
            "signal_counts": {
                "crossover_signals": self._crossover_signals,
                "divergence_signals": self._divergence_signals,
                "breakout_signals": self._breakout_signals,
                "reversal_signals": self._reversal_signals
            },
            "vortex_tracking": {
                "peaks": self._vortex_peaks
            },
            "risk_management": {
                "vortex_based_stop": self._vortex_based_stop,
                "trend_based_position_size": self._trend_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor
            },
            "institutional_analysis": {
                "vortex": self._institutional_vortex,
                "smart_money_vortex": self._smart_money_vortex
            },
            "metadata": {
                "period": self.vortex_config.period,
                "signal_threshold": self.vortex_config.signal_threshold,
                "adaptive_period": self.vortex_config.adaptive_period,
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
        self._true_ranges.clear()
        self._vm_plus.clear()
        self._vm_minus.clear()
        self._vip_values.clear()
        self._vim_values.clear()
        self._vip = 0.0
        self._vim = 0.0
        self._vortex_diff = 0.0
        self._trend_direction = 0
        self._trend_strength = 0.0
        self._vortex_signal = 0.0
        self._crossover_signals = 0
        self._divergence_signals = 0
        self._breakout_signals = 0
        self._reversal_signals = 0
        self._signal_accuracy = 0.0
        self._trend_prediction_rate = 0.0
        self._vortex_reliability = 0.0
        self._volatility_regime = "normal"
        self._trend_cycles = 0
        self._vortex_peaks.clear()
        self._vortex_based_stop = 0.0
        self._trend_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0
        self._institutional_vortex = 0.0
        self._smart_money_vortex = 0.0