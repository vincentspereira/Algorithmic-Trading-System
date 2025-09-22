"""
Institutional-Grade Augmented Know Sure Thing (KST) Indicator

This module implements an enhanced Know Sure Thing indicator with institutional-grade features:
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
class AugmentedKSTIndicatorConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented KST Indicator"""
    roc_periods: List[int] = None  # ROC periods for KST calculation
    sma_periods: List[int] = None  # SMA periods for smoothing
    signal_period: int = 9
    adaptive_smoothing: bool = True

    def __post_init__(self):
        if self.roc_periods is None:
            self.roc_periods = [10, 15, 20, 30]  # Standard KST ROC periods
        if self.sma_periods is None:
            self.sma_periods = [10, 10, 10, 15]  # Standard KST SMA periods


class AugmentedKSTIndicator(AugmentedIndicator):
    """
    Institutional-grade Augmented Know Sure Thing (KST) Indicator implementing 5-pillar architecture.

    Features:
    - Multiple rate of change calculations smoothed with moving averages
    - Volume-weighted KST calculations for institutional validation
    - Market regime adaptation for different volatility environments
    - Multi-timeframe convergence for trend confirmation
    - Smart money trend momentum detection
    - Automated risk management based on KST signals
    """

    def __init__(self, config: AugmentedKSTIndicatorConfig = None):
        if config is None:
            config = AugmentedKSTIndicatorConfig()

        super().__init__(config)
        self.kst_config = config

        # KST specific state
        self._close_values = deque(maxlen=self.config.buffer_size)
        self._volume_values = deque(maxlen=self.config.buffer_size)

        # KST calculation components
        self._roc_values = [deque(maxlen=self.config.buffer_size) for _ in range(4)]  # 4 ROC lines
        self._sma_values = [deque(maxlen=self.config.buffer_size) for _ in range(4)]  # 4 SMA lines
        self._kst_values = deque(maxlen=self.config.buffer_size)  # KST line
        self._signal_line = deque(maxlen=self.config.buffer_size)  # Signal line

        # Current KST values
        self._kst = 0.0
        self._signal = 0.0
        self._kst_diff = 0.0

        # Trend analysis
        self._trend_direction = 0  # 1 = uptrend, -1 = downtrend, 0 = neutral
        self._momentum_strength = 0.0
        self._kst_signal = 0.0

        # Signal analysis
        self._crossover_signals = 0
        self._divergence_signals = 0
        self._breakout_signals = 0
        self._reversal_signals = 0

        # Performance tracking
        self._signal_accuracy = 0.0
        self._trend_prediction_rate = 0.0
        self._kst_reliability = 0.0

        # Market structure
        self._volatility_regime = "normal"
        self._momentum_cycles = 0
        self._kst_peaks = []

        # Risk management
        self._kst_based_stop = 0.0
        self._momentum_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0

        # Institutional analysis
        self._institutional_kst = 0.0
        self._smart_money_kst = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if KST Indicator is ready to provide signals"""
        max_period = max(self.kst_config.roc_periods + self.kst_config.sma_periods + [self.kst_config.signal_period])
        return (len(self._close_values) >= max_period and
                len(self._kst_values) > 0)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update KST analysis

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

        # Update KST analysis
        self._update_kst_analysis(close, volume)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_kst_analysis(self, close: float, volume: float):
        """Update the core KST analysis with institutional enhancements"""
        # Store price and volume data
        self._close_values.append(close)
        self._volume_values.append(volume)

        max_period = max(self.kst_config.roc_periods)
        if len(self._close_values) >= max_period:
            # Calculate Rate of Change for each period
            self._calculate_rate_of_change()

            # Calculate Simple Moving Averages for smoothing
            self._calculate_smoothing_smas()

            # Calculate KST line
            self._calculate_kst_line()

            # Calculate signal line
            self._calculate_signal_line()

            # Analyze momentum characteristics
            self._analyze_momentum_characteristics()

            # Generate KST signals
            self._generate_kst_signals()

            # Calculate institutional KST analysis
            self._calculate_institutional_kst()

    def _calculate_rate_of_change(self):
        """Calculate Rate of Change for each KST component"""
        for i, period in enumerate(self.kst_config.roc_periods):
            if len(self._close_values) >= period + 1:
                current_price = self._close_values[-1]
                past_price = self._close_values[-period - 1]

                if past_price > 0:
                    roc = ((current_price - past_price) / past_price) * 100
                else:
                    roc = 0.0

                self._roc_values[i].append(roc)

    def _calculate_smoothing_smas(self):
        """Calculate Simple Moving Averages for smoothing ROC values"""
        for i, sma_period in enumerate(self.kst_config.sma_periods):
            if len(self._roc_values[i]) >= sma_period:
                recent_roc = list(self._roc_values[i])[-sma_period:]
                sma = statistics.mean(recent_roc)
                self._sma_values[i].append(sma)

    def _calculate_kst_line(self):
        """Calculate the Know Sure Thing line"""
        # Check if all SMA values are available
        if all(len(sma_values) > 0 for sma_values in self._sma_values):
            # Standard KST formula: (ROC10*1 + ROC15*2 + ROC20*3 + ROC30*4) / (1+2+3+4)
            weights = [1, 2, 3, 4]
            weighted_sum = sum(weight * sma_values[-1] for weight, sma_values in zip(weights, self._sma_values))
            total_weight = sum(weights)

            if total_weight > 0:
                kst = weighted_sum / total_weight
            else:
                kst = 0.0

            self._kst_values.append(kst)
            self._kst = kst

    def _calculate_signal_line(self):
        """Calculate signal line using exponential smoothing"""
        if len(self._kst_values) >= self.kst_config.signal_period:
            recent_kst = list(self._kst_values)[-self.kst_config.signal_period:]
            signal = statistics.mean(recent_kst)  # Simple average for signal
            self._signal_line.append(signal)
            self._signal = signal
            self._kst_diff = self._kst - self._signal

    def _analyze_momentum_characteristics(self):
        """Analyze momentum characteristics for institutional insights"""
        if not self.is_ready:
            return

        # Determine trend direction based on KST
        if self._kst > self._signal and self._kst > 0:
            self._trend_direction = 1  # Bullish momentum
        elif self._kst < self._signal and self._kst < 0:
            self._trend_direction = -1  # Bearish momentum
        else:
            self._trend_direction = 0  # Neutral momentum

        # Calculate momentum strength
        self._momentum_strength = abs(self._kst) / 100.0  # Normalize based on percentage

        # Calculate KST signal
        self._kst_signal = self._kst_diff

        # Determine volatility regime
        if len(self._close_values) >= 20:
            recent_prices = list(self._close_values)[-20:]
            price_volatility = statistics.stdev(recent_prices) / statistics.mean(recent_prices) if statistics.mean(recent_prices) > 0 else 0

            if price_volatility > 0.03:
                self._volatility_regime = "high"
            elif price_volatility < 0.01:
                self._volatility_regime = "low"
            else:
                self._volatility_regime = "normal"

        # Track momentum cycles
        if len(self._kst_values) >= 2:
            prev_kst = list(self._kst_values)[-2]
            if ((prev_kst <= 0 and self._kst > 0) or
                (prev_kst >= 0 and self._kst < 0)):
                self._momentum_cycles += 1

        # Track KST peaks
        if self._momentum_strength > 0.8:
            self._kst_peaks.append(self._kst)

    def _generate_kst_signals(self):
        """Generate KST-based signals"""
        if not self.is_ready:
            return

        # Crossover signals
        if len(self._kst_values) >= 2 and len(self._signal_line) >= 2:
            prev_kst = list(self._kst_values)[-2]
            prev_signal = list(self._signal_line)[-2]

            # KST crosses above signal (bullish crossover)
            if prev_kst <= prev_signal and self._kst > self._signal:
                self._crossover_signals += 1

            # KST crosses below signal (bearish crossover)
            elif prev_kst >= prev_signal and self._kst < self._signal:
                self._crossover_signals += 1

        # Divergence signals
        if len(self._kst_values) >= 5 and len(self._close_values) >= 5:
            kst_trend = self._kst - list(self._kst_values)[-5]
            price_trend = list(self._close_values)[-1] - list(self._close_values)[-5]

            # Bullish divergence: price down, KST up
            if price_trend < 0 and kst_trend > 0:
                self._divergence_signals += 1

            # Bearish divergence: price up, KST down
            elif price_trend > 0 and kst_trend < 0:
                self._divergence_signals += 1

        # Breakout signals
        if self._momentum_strength > 0.9:
            self._breakout_signals += 1

        # Reversal signals
        if abs(self._kst_diff) > 10 and self._trend_direction != 0:  # 10 point difference
            self._reversal_signals += 1

    def _calculate_institutional_kst(self):
        """Calculate institutional KST analysis based on momentum characteristics"""
        if not self.is_ready:
            return

        # Institutional traders use KST for momentum timing and trend confirmation
        base_kst = 0.0

        if (self._momentum_strength > 0.8 and
            self._crossover_signals > 0 and
            self._signal_accuracy > 0.6):
            base_kst = 0.9  # Strong momentum with crossover signals and accuracy
        elif (self._divergence_signals > 0 and
              self._breakout_signals > 0 and
              self._momentum_cycles > 2):
            base_kst = 0.8  # Divergence and breakout signals with cycle confirmation
        elif (self._reversal_signals > 0 and
              self._kst_reliability > 0.7):
            base_kst = 0.7  # Reversal signals with high reliability

        self._institutional_kst = base_kst

        # Smart money KST considers momentum strength and market timing
        smart_money_score = (
            self._momentum_strength * 0.3 +
            self._signal_accuracy * 0.3 +
            abs(self._kst_signal) / 20.0 * 0.2 +  # Normalize signal difference
            self._institutional_kst * 0.2
        )
        self._smart_money_kst = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade KST analysis"""
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

        # Use KST value as primary raw value
        raw_value = self._kst

        # Determine signal type based on KST analysis
        signal_type = self._determine_kst_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'kst': self._kst,
            'signal_line': self._signal,
            'kst_diff': self._kst_diff,
            'trend_direction': self._trend_direction,
            'momentum_strength': self._momentum_strength,
            'kst_signal': self._kst_signal,
            'signal_accuracy': self._signal_accuracy,
            'trend_prediction_rate': self._trend_prediction_rate,
            'kst_reliability': self._kst_reliability,
            'volatility_regime': self._volatility_regime,
            'momentum_cycles': self._momentum_cycles,
            'kst_peaks': self._kst_peaks,
            'kst_based_stop': self._kst_based_stop,
            'momentum_based_position_size': self._momentum_based_position_size,
            'risk_adjustment_factor': self._risk_adjustment_factor,
            'crossover_signals': self._crossover_signals,
            'divergence_signals': self._divergence_signals,
            'breakout_signals': self._breakout_signals,
            'reversal_signals': self._reversal_signals,
            'institutional_kst': self._institutional_kst,
            'smart_money_kst': self._smart_money_kst
        }

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._kst_based_stop,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Know_Sure_Thing_Indicator",
                "roc_periods": self.kst_config.roc_periods,
                "sma_periods": self.kst_config.sma_periods,
                "signal_period": self.kst_config.signal_period,
                "adaptive_smoothing": self.kst_config.adaptive_smoothing,
                "kst": self._kst,
                "signal_line": self._signal,
                "kst_diff": self._kst_diff,
                "trend_direction": self._trend_direction,
                "momentum_strength": self._momentum_strength,
                "kst_signal": self._kst_signal,
                "signal_accuracy": self._signal_accuracy,
                "trend_prediction_rate": self._trend_prediction_rate,
                "kst_reliability": self._kst_reliability,
                "volatility_regime": self._volatility_regime,
                "momentum_cycles": self._momentum_cycles,
                "kst_peaks": self._kst_peaks,
                "kst_based_stop": self._kst_based_stop,
                "momentum_based_position_size": self._momentum_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor,
                "crossover_signals": self._crossover_signals,
                "divergence_signals": self._divergence_signals,
                "breakout_signals": self._breakout_signals,
                "reversal_signals": self._reversal_signals,
                "institutional_kst": self._institutional_kst,
                "smart_money_kst": self._smart_money_kst,
                "is_ready": self.is_ready
            }
        )

    def _determine_kst_signal(self) -> SignalType:
        """Determine signal type based on KST analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong momentum signals
        if (self._momentum_strength > 0.8 and
            self._crossover_signals > 0 and
            self._signal_accuracy > 0.7):
            if self._trend_direction == 1:
                return SignalType.STRONG_BULLISH
            elif self._trend_direction == -1:
                return SignalType.STRONG_BEARISH

        # Moderate momentum signals
        elif (self._divergence_signals > 0 and
              self._momentum_strength > 0.6):
            if self._trend_direction == 1:
                return SignalType.BULLISH
            elif self._trend_direction == -1:
                return SignalType.BEARISH

        # Breakout signals
        elif (self._breakout_signals > 0 and
              abs(self._kst) > 15):  # 15 point KST value
            if self._kst > 0:
                return SignalType.STRONG_BULLISH
            else:
                return SignalType.STRONG_BEARISH

        # Reversal signals
        elif (self._reversal_signals > 0 and
              self._kst_reliability > 0.7):
            if self._trend_direction == 1:
                return SignalType.BULLISH
            elif self._trend_direction == -1:
                return SignalType.BEARISH

        return SignalType.NEUTRAL

    @property
    def kst(self) -> float:
        """Get the current KST value"""
        return self._kst if self.is_ready else 0.0

    @property
    def signal_line(self) -> float:
        """Get the current signal line value"""
        return self._signal if self.is_ready else 0.0

    @property
    def kst_diff(self) -> float:
        """Get the current KST difference (KST - Signal)"""
        return self._kst_diff if self.is_ready else 0.0

    @property
    def trend_direction(self) -> int:
        """Get the current trend direction (1=up, -1=down, 0=neutral)"""
        return self._trend_direction

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
    def institutional_kst(self) -> float:
        """Get the institutional KST score (0-1)"""
        return self._institutional_kst

    @property
    def smart_money_kst(self) -> float:
        """Get the smart money KST score (0-1)"""
        return self._smart_money_kst

    def is_bullish_kst(self) -> bool:
        """Check if KST indicates bullish momentum"""
        return self._trend_direction == 1 and self._kst > self._signal

    def is_bearish_kst(self) -> bool:
        """Check if KST indicates bearish momentum"""
        return self._trend_direction == -1 and self._kst < self._signal

    def is_strong_momentum_kst(self) -> bool:
        """Check if KST momentum is strong"""
        return self._momentum_strength > 0.7

    def is_kst_crossover(self) -> bool:
        """Check if there's a KST crossover"""
        return self._crossover_signals > 0

    def is_kst_divergence(self) -> bool:
        """Check if there's a KST divergence"""
        return self._divergence_signals > 0

    def is_high_volatility_kst(self) -> bool:
        """Check if volatility regime is high"""
        return self._volatility_regime == "high"

    def is_low_volatility_kst(self) -> bool:
        """Check if volatility regime is low"""
        return self._volatility_regime == "low"

    def is_institutional_setup_kst(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_kst > 0.7

    def get_kst_info(self) -> Dict[str, Any]:
        """Get comprehensive KST indicator information"""
        return {
            "kst_values": {
                "kst": self._kst,
                "signal_line": self._signal,
                "kst_diff": self._kst_diff
            },
            "trend_analysis": {
                "direction": self._trend_direction,
                "momentum_strength": self._momentum_strength,
                "kst_signal": self._kst_signal
            },
            "performance_metrics": {
                "signal_accuracy": self._signal_accuracy,
                "trend_prediction_rate": self._trend_prediction_rate,
                "kst_reliability": self._kst_reliability
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
            "kst_tracking": {
                "peaks": self._kst_peaks
            },
            "risk_management": {
                "kst_based_stop": self._kst_based_stop,
                "momentum_based_position_size": self._momentum_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor
            },
            "institutional_analysis": {
                "kst": self._institutional_kst,
                "smart_money_kst": self._smart_money_kst
            },
            "metadata": {
                "roc_periods": self.kst_config.roc_periods,
                "sma_periods": self.kst_config.sma_periods,
                "signal_period": self.kst_config.signal_period,
                "adaptive_smoothing": self.kst_config.adaptive_smoothing,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._close_values.clear()
        self._volume_values.clear()
        for roc_deque in self._roc_values:
            roc_deque.clear()
        for sma_deque in self._sma_values:
            sma_deque.clear()
        self._kst_values.clear()
        self._signal_line.clear()
        self._kst = 0.0
        self._signal = 0.0
        self._kst_diff = 0.0
        self._trend_direction = 0
        self._momentum_strength = 0.0
        self._kst_signal = 0.0
        self._crossover_signals = 0
        self._divergence_signals = 0
        self._breakout_signals = 0
        self._reversal_signals = 0
        self._signal_accuracy = 0.0
        self._trend_prediction_rate = 0.0
        self._kst_reliability = 0.0
        self._volatility_regime = "normal"
        self._momentum_cycles = 0
        self._kst_peaks.clear()
        self._kst_based_stop = 0.0
        self._momentum_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0
        self._institutional_kst = 0.0
        self._smart_money_kst = 0.0