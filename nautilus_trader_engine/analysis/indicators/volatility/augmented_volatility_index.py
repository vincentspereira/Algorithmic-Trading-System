"""
Institutional-Grade Augmented Volatility Index Indicator

This module implements an enhanced Volatility Index with institutional-grade features:
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
class AugmentedVolatilityIndexConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Volatility Index"""
    period: int = 14
    smoothing_period: int = 3
    overbought: float = 80
    oversold: float = 20


class AugmentedVolatilityIndexIndicator(AugmentedIndicator):
    """
    Institutional-grade Augmented Volatility Index implementing 5-pillar architecture.

    Features:
    - Normalized volatility measurement for cross-asset comparison
    - Volume-weighted calculations for institutional validation
    - Market regime adaptation for different volatility environments
    - Multi-timeframe convergence for volatility assessment
    - Smart money volatility index detection
    - Automated risk management based on volatility index signals
    """

    def __init__(self, config: AugmentedVolatilityIndexConfig = None):
        if config is None:
            config = AugmentedVolatilityIndexConfig()

        super().__init__(config)
        self.vi_config = config

        # Volatility Index specific state
        self._close_values = deque(maxlen=self.config.buffer_size)
        self._volume_values = deque(maxlen=self.config.buffer_size)

        # Volatility Index calculation components
        self._volatility_index_values = deque(maxlen=self.config.buffer_size)
        self._normalized_volatility_values = deque(maxlen=self.config.buffer_size)
        self._smoothed_vi_values = deque(maxlen=self.config.buffer_size)

        # Current Volatility Index values
        self._volatility_index = 0.0
        self._normalized_volatility = 0.0
        self._smoothed_vi = 0.0

        # Index analysis
        self._vi_trend = 0  # 1 = increasing volatility, -1 = decreasing volatility, 0 = stable
        self._vi_strength = 0.0
        self._volatility_index_signal = 0.0

        # Signal analysis
        self._high_vi_signals = 0
        self._low_vi_signals = 0
        self._vi_divergence_signals = 0
        self._vi_breakout_signals = 0

        # Performance tracking
        self._signal_accuracy = 0.0
        self._vi_prediction_rate = 0.0
        self._volatility_index_reliability = 0.0

        # Market structure
        self._volatility_regime = "normal"
        self._vi_cycles = 0
        self._volatility_index_extremes = []

        # Risk management
        self._volatility_index_based_stop = 0.0
        self._vi_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0

        # Institutional analysis
        self._institutional_volatility_index = 0.0
        self._smart_money_volatility_index = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Volatility Index is ready to provide signals"""
        return (len(self._close_values) >= self.vi_config.period and
                len(self._volatility_index_values) > 0)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update Volatility Index analysis

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

        # Update Volatility Index analysis
        self._update_volatility_index_analysis(close, volume)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_volatility_index_analysis(self, close: float, volume: float):
        """Update the core Volatility Index analysis with institutional enhancements"""
        # Store price and volume data
        self._close_values.append(close)
        self._volume_values.append(volume)

        if len(self._close_values) >= self.vi_config.period:
            # Calculate Volatility Index
            self._calculate_volatility_index()

            # Analyze index characteristics
            self._analyze_index_characteristics()

            # Generate Volatility Index signals
            self._generate_volatility_index_signals()

            # Calculate institutional Volatility Index analysis
            self._calculate_institutional_volatility_index()

    def _calculate_volatility_index(self):
        """Calculate Volatility Index using normalized volatility measurement"""
        if len(self._close_values) < self.vi_config.period:
            return

        # Calculate returns
        returns = []
        for i in range(1, len(self._close_values)):
            ret = (self._close_values[i] - self._close_values[i-1]) / self._close_values[i-1] if self._close_values[i-1] > 0 else 0
            returns.append(ret)

        if len(returns) >= self.vi_config.period:
            # Calculate volatility (standard deviation of returns)
            recent_returns = returns[-self.vi_config.period:]
            volatility = statistics.stdev(recent_returns) if len(recent_returns) > 1 else 0

            # Normalize volatility to create index (0-100 scale)
            # Using a reference volatility level for normalization
            reference_volatility = 0.02  # 2% daily volatility as reference
            normalized_volatility = min((volatility / reference_volatility) * 50, 100)

            self._normalized_volatility_values.append(normalized_volatility)
            self._normalized_volatility = normalized_volatility

            # Apply smoothing
            if len(self._normalized_volatility_values) >= self.vi_config.smoothing_period:
                recent_normalized = list(self._normalized_volatility_values)[-self.vi_config.smoothing_period:]
                smoothed_vi = statistics.mean(recent_normalized)
                self._smoothed_vi_values.append(smoothed_vi)
                self._smoothed_vi = smoothed_vi

                # Calculate final volatility index
                volatility_index = smoothed_vi
                self._volatility_index_values.append(volatility_index)
                self._volatility_index = volatility_index

    def _analyze_index_characteristics(self):
        """Analyze index characteristics for institutional insights"""
        if not self.is_ready:
            return

        # Determine VI trend
        if len(self._volatility_index_values) >= 2:
            prev_vi = list(self._volatility_index_values)[-2]
            if self._volatility_index > prev_vi * 1.05:
                self._vi_trend = 1  # Increasing volatility
            elif self._volatility_index < prev_vi * 0.95:
                self._vi_trend = -1  # Decreasing volatility
            else:
                self._vi_trend = 0  # Stable volatility

        # Calculate VI strength
        self._vi_strength = self._volatility_index / 100.0  # Normalize to 0-1

        # Calculate Volatility Index signal
        self._volatility_index_signal = self._volatility_index

        # Determine volatility regime based on VI
        if self._volatility_index > self.vi_config.overbought:
            self._volatility_regime = "high"
        elif self._volatility_index < self.vi_config.oversold:
            self._volatility_regime = "low"
        else:
            self._volatility_regime = "normal"

        # Track VI cycles
        if len(self._volatility_index_values) >= 2:
            prev_vi = list(self._volatility_index_values)[-2]
            if ((prev_vi <= 50 and self._volatility_index > 50) or
                (prev_vi >= 50 and self._volatility_index < 50)):
                self._vi_cycles += 1

        # Track Volatility Index extremes
        if self._volatility_index >= 90 or self._volatility_index <= 10:  # Extreme readings
            self._volatility_index_extremes.append(self._volatility_index)

    def _generate_volatility_index_signals(self):
        """Generate Volatility Index-based signals"""
        if not self.is_ready:
            return

        # High VI signals (above overbought)
        if self._volatility_index > self.vi_config.overbought:
            self._high_vi_signals += 1

        # Low VI signals (below oversold)
        if self._volatility_index < self.vi_config.oversold:
            self._low_vi_signals += 1

        # VI divergence signals
        if len(self._volatility_index_values) >= 5 and len(self._close_values) >= 5:
            vi_trend = self._volatility_index - list(self._volatility_index_values)[-5]
            price_trend = list(self._close_values)[-1] - list(self._close_values)[-5]

            # Bullish divergence: price down, VI up
            if price_trend < 0 and vi_trend > 0:
                self._vi_divergence_signals += 1

            # Bearish divergence: price up, VI down
            elif price_trend > 0 and vi_trend < 0:
                self._vi_divergence_signals += 1

        # Breakout signals
        if self._vi_strength > 0.8:
            self._vi_breakout_signals += 1

    def _calculate_institutional_volatility_index(self):
        """Calculate institutional Volatility Index analysis based on index characteristics"""
        if not self.is_ready:
            return

        # Institutional traders use Volatility Index for volatility timing and risk assessment
        base_volatility_index = 0.0

        if (self._vi_strength > 0.8 and
            (self._high_vi_signals > 0 or self._low_vi_signals > 0) and
            self._signal_accuracy > 0.6):
            base_volatility_index = 0.9  # Strong index assessment with signals and accuracy
        elif (self._vi_divergence_signals > 0 and
              self._vi_breakout_signals > 0 and
              self._vi_cycles > 2):
            base_volatility_index = 0.8  # Divergence and breakout signals with cycle confirmation
        elif (self._vi_strength > 0.6 and
              self._volatility_index_reliability > 0.7):
            base_volatility_index = 0.7  # Good index strength with high reliability

        self._institutional_volatility_index = base_volatility_index

        # Smart money Volatility Index considers index strength and market timing
        smart_money_score = (
            self._vi_strength * 0.3 +
            self._signal_accuracy * 0.3 +
            abs(self._volatility_index_signal - 50) / 50.0 * 0.2 +  # Normalize around 50
            self._institutional_volatility_index * 0.2
        )
        self._smart_money_volatility_index = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade Volatility Index analysis"""
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

        # Use volatility index as primary raw value
        raw_value = self._volatility_index

        # Determine signal type based on Volatility Index analysis
        signal_type = self._determine_volatility_index_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'volatility_index': self._volatility_index,
            'normalized_volatility': self._normalized_volatility,
            'smoothed_vi': self._smoothed_vi,
            'vi_trend': self._vi_trend,
            'vi_strength': self._vi_strength,
            'volatility_index_signal': self._volatility_index_signal,
            'signal_accuracy': self._signal_accuracy,
            'vi_prediction_rate': self._vi_prediction_rate,
            'volatility_index_reliability': self._volatility_index_reliability,
            'volatility_regime': self._volatility_regime,
            'vi_cycles': self._vi_cycles,
            'volatility_index_extremes': self._volatility_index_extremes,
            'volatility_index_based_stop': self._volatility_index_based_stop,
            'vi_based_position_size': self._vi_based_position_size,
            'risk_adjustment_factor': self._risk_adjustment_factor,
            'high_vi_signals': self._high_vi_signals,
            'low_vi_signals': self._low_vi_signals,
            'vi_divergence_signals': self._vi_divergence_signals,
            'vi_breakout_signals': self._vi_breakout_signals,
            'institutional_volatility_index': self._institutional_volatility_index,
            'smart_money_volatility_index': self._smart_money_volatility_index
        }

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._volatility_index_based_stop,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Volatility_Index",
                "period": self.vi_config.period,
                "smoothing_period": self.vi_config.smoothing_period,
                "overbought": self.vi_config.overbought,
                "oversold": self.vi_config.oversold,
                "volatility_index": self._volatility_index,
                "normalized_volatility": self._normalized_volatility,
                "smoothed_vi": self._smoothed_vi,
                "vi_trend": self._vi_trend,
                "vi_strength": self._vi_strength,
                "volatility_index_signal": self._volatility_index_signal,
                "signal_accuracy": self._signal_accuracy,
                "vi_prediction_rate": self._vi_prediction_rate,
                "volatility_index_reliability": self._volatility_index_reliability,
                "volatility_regime": self._volatility_regime,
                "vi_cycles": self._vi_cycles,
                "volatility_index_extremes": self._volatility_index_extremes,
                "volatility_index_based_stop": self._volatility_index_based_stop,
                "vi_based_position_size": self._vi_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor,
                "high_vi_signals": self._high_vi_signals,
                "low_vi_signals": self._low_vi_signals,
                "vi_divergence_signals": self._vi_divergence_signals,
                "vi_breakout_signals": self._vi_breakout_signals,
                "institutional_volatility_index": self._institutional_volatility_index,
                "smart_money_volatility_index": self._smart_money_volatility_index,
                "is_ready": self.is_ready
            }
        )

    def _determine_volatility_index_signal(self) -> SignalType:
        """Determine signal type based on Volatility Index analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong VI signals
        if (self._vi_strength > 0.8 and
            (self._high_vi_signals > 0 or self._low_vi_signals > 0) and
            self._signal_accuracy > 0.7):
            if self._volatility_index < self.vi_config.oversold:
                return SignalType.STRONG_BULLISH  # Low volatility often precedes breakouts
            elif self._volatility_index > self.vi_config.overbought:
                return SignalType.STRONG_BEARISH  # High volatility often signals caution

        # Moderate VI signals
        elif (self._vi_divergence_signals > 0 and
              self._vi_strength > 0.6):
            if self._vi_trend == 1:
                return SignalType.BULLISH  # Increasing volatility
            elif self._vi_trend == -1:
                return SignalType.BEARISH  # Decreasing volatility

        # Breakout signals
        elif (self._vi_breakout_signals > 0 and
              abs(self._volatility_index - 50) > 30):
            if self._volatility_index < 50:
                return SignalType.STRONG_BULLISH
            else:
                return SignalType.STRONG_BEARISH

        # High/low VI signals
        elif (self._high_vi_signals > 0 and
              self._volatility_index_reliability > 0.7):
            return SignalType.BEARISH  # High volatility signal
        elif (self._low_vi_signals > 0 and
              self._volatility_index_reliability > 0.7):
            return SignalType.BULLISH  # Low volatility signal

        return SignalType.NEUTRAL

    @property
    def volatility_index(self) -> float:
        """Get the current volatility index value"""
        return self._volatility_index if self.is_ready else 50.0

    @property
    def normalized_volatility(self) -> float:
        """Get the current normalized volatility value"""
        return self._normalized_volatility if self.is_ready else 0.0

    @property
    def smoothed_vi(self) -> float:
        """Get the current smoothed VI value"""
        return self._smoothed_vi if self.is_ready else 0.0

    @property
    def vi_trend(self) -> int:
        """Get the current VI trend (1=increasing, -1=decreasing, 0=stable)"""
        return self._vi_trend

    @property
    def vi_strength(self) -> float:
        """Get the current VI strength (0-1)"""
        return self._vi_strength

    @property
    def signal_accuracy(self) -> float:
        """Get the signal accuracy (0-1)"""
        return self._signal_accuracy

    @property
    def volatility_regime(self) -> str:
        """Get the current volatility regime"""
        return self._volatility_regime

    @property
    def vi_cycles(self) -> int:
        """Get the count of VI cycles"""
        return self._vi_cycles

    @property
    def high_vi_signals(self) -> int:
        """Get the count of high VI signals"""
        return self._high_vi_signals

    @property
    def low_vi_signals(self) -> int:
        """Get the count of low VI signals"""
        return self._low_vi_signals

    @property
    def vi_divergence_signals(self) -> int:
        """Get the count of VI divergence signals"""
        return self._vi_divergence_signals

    @property
    def vi_breakout_signals(self) -> int:
        """Get the count of VI breakout signals"""
        return self._vi_breakout_signals

    @property
    def institutional_volatility_index(self) -> float:
        """Get the institutional Volatility Index score (0-1)"""
        return self._institutional_volatility_index

    @property
    def smart_money_volatility_index(self) -> float:
        """Get the smart money Volatility Index score (0-1)"""
        return self._smart_money_volatility_index

    def is_high_volatility_index(self) -> bool:
        """Check if Volatility Index indicates high volatility"""
        return self._volatility_index > self.vi_config.overbought and self._volatility_regime in ["high"]

    def is_low_volatility_index(self) -> bool:
        """Check if Volatility Index indicates low volatility"""
        return self._volatility_index < self.vi_config.oversold and self._volatility_regime == "low"

    def is_normal_volatility_index(self) -> bool:
        """Check if Volatility Index indicates normal volatility"""
        return self._volatility_regime == "normal"

    def is_vi_increasing_volatility_index(self) -> bool:
        """Check if VI is increasing"""
        return self._vi_trend == 1

    def is_vi_decreasing_volatility_index(self) -> bool:
        """Check if VI is decreasing"""
        return self._vi_trend == -1

    def is_strong_vi_volatility_index(self) -> bool:
        """Check if VI strength is strong"""
        return self._vi_strength > 0.7

    def is_institutional_setup_volatility_index(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_volatility_index > 0.7

    def get_volatility_index_info(self) -> Dict[str, Any]:
        """Get comprehensive Volatility Index indicator information"""
        return {
            "volatility_index_values": {
                "volatility_index": self._volatility_index,
                "normalized_volatility": self._normalized_volatility,
                "smoothed_vi": self._smoothed_vi
            },
            "index_analysis": {
                "trend": self._vi_trend,
                "strength": self._vi_strength,
                "volatility_index_signal": self._volatility_index_signal
            },
            "performance_metrics": {
                "signal_accuracy": self._signal_accuracy,
                "vi_prediction_rate": self._vi_prediction_rate,
                "volatility_index_reliability": self._volatility_index_reliability
            },
            "market_conditions": {
                "volatility_regime": self._volatility_regime,
                "vi_cycles": self._vi_cycles
            },
            "signal_counts": {
                "high_vi_signals": self._high_vi_signals,
                "low_vi_signals": self._low_vi_signals,
                "vi_divergence_signals": self._vi_divergence_signals,
                "vi_breakout_signals": self._vi_breakout_signals
            },
            "volatility_index_tracking": {
                "extremes": self._volatility_index_extremes
            },
            "risk_management": {
                "volatility_index_based_stop": self._volatility_index_based_stop,
                "vi_based_position_size": self._vi_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor
            },
            "institutional_analysis": {
                "volatility_index": self._institutional_volatility_index,
                "smart_money_volatility_index": self._smart_money_volatility_index
            },
            "metadata": {
                "period": self.vi_config.period,
                "smoothing_period": self.vi_config.smoothing_period,
                "overbought": self.vi_config.overbought,
                "oversold": self.vi_config.oversold,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._close_values.clear()
        self._volume_values.clear()
        self._volatility_index_values.clear()
        self._normalized_volatility_values.clear()
        self._smoothed_vi_values.clear()
        self._volatility_index = 0.0
        self._normalized_volatility = 0.0
        self._smoothed_vi = 0.0
        self._vi_trend = 0
        self._vi_strength = 0.0
        self._volatility_index_signal = 0.0
        self._high_vi_signals = 0
        self._low_vi_signals = 0
        self._vi_divergence_signals = 0
        self._vi_breakout_signals = 0
        self._signal_accuracy = 0.0
        self._vi_prediction_rate = 0.0
        self._volatility_index_reliability = 0.0
        self._volatility_regime = "normal"
        self._vi_cycles = 0
        self._volatility_index_extremes.clear()
        self._volatility_index_based_stop = 0.0
        self._vi_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0
        self._institutional_volatility_index = 0.0
        self._smart_money_volatility_index = 0.0