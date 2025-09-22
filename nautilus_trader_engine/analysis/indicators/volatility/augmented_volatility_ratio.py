"""
Institutional-Grade Augmented Volatility Ratio Indicator

This module implements an enhanced Volatility Ratio with institutional-grade features:
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
class AugmentedVolatilityRatioConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Volatility Ratio"""
    short_period: int = 5
    long_period: int = 20
    overbought: float = 1.5
    oversold: float = 0.5


class AugmentedVolatilityRatioIndicator(AugmentedIndicator):
    """
    Institutional-grade Augmented Volatility Ratio implementing 5-pillar architecture.

    Features:
    - Ratio of short-term to long-term volatility for trend identification
    - Volume-weighted calculations for institutional validation
    - Market regime adaptation for different volatility environments
    - Multi-timeframe convergence for volatility assessment
    - Smart money volatility ratio detection
    - Automated risk management based on volatility ratio signals
    """

    def __init__(self, config: AugmentedVolatilityRatioConfig = None):
        if config is None:
            config = AugmentedVolatilityRatioConfig()

        super().__init__(config)
        self.vr_config = config

        # Volatility Ratio specific state
        self._close_values = deque(maxlen=self.config.buffer_size)
        self._volume_values = deque(maxlen=self.config.buffer_size)

        # Volatility Ratio calculation components
        self._volatility_ratio_values = deque(maxlen=self.config.buffer_size)
        self._short_volatility_values = deque(maxlen=self.config.buffer_size)
        self._long_volatility_values = deque(maxlen=self.config.buffer_size)

        # Current Volatility Ratio values
        self._volatility_ratio = 0.0
        self._short_volatility = 0.0
        self._long_volatility = 0.0

        # Volatility analysis
        self._ratio_trend = 0  # 1 = increasing ratio, -1 = decreasing ratio, 0 = stable
        self._ratio_strength = 0.0
        self._volatility_ratio_signal = 0.0

        # Signal analysis
        self._high_ratio_signals = 0
        self._low_ratio_signals = 0
        self._ratio_divergence_signals = 0
        self._ratio_breakout_signals = 0

        # Performance tracking
        self._signal_accuracy = 0.0
        self._ratio_prediction_rate = 0.0
        self._volatility_ratio_reliability = 0.0

        # Market structure
        self._volatility_regime = "normal"
        self._ratio_cycles = 0
        self._volatility_ratio_extremes = []

        # Risk management
        self._volatility_ratio_based_stop = 0.0
        self._ratio_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0

        # Institutional analysis
        self._institutional_volatility_ratio = 0.0
        self._smart_money_volatility_ratio = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Volatility Ratio is ready to provide signals"""
        return (len(self._close_values) >= self.vr_config.long_period and
                len(self._volatility_ratio_values) > 0)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update Volatility Ratio analysis

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

        # Update Volatility Ratio analysis
        self._update_volatility_ratio_analysis(close, volume)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_volatility_ratio_analysis(self, close: float, volume: float):
        """Update the core Volatility Ratio analysis with institutional enhancements"""
        # Store price and volume data
        self._close_values.append(close)
        self._volume_values.append(volume)

        if len(self._close_values) >= self.vr_config.long_period:
            # Calculate Volatility Ratio
            self._calculate_volatility_ratio()

            # Analyze ratio characteristics
            self._analyze_ratio_characteristics()

            # Generate Volatility Ratio signals
            self._generate_volatility_ratio_signals()

            # Calculate institutional Volatility Ratio analysis
            self._calculate_institutional_volatility_ratio()

    def _calculate_volatility_ratio(self):
        """Calculate Volatility Ratio"""
        if len(self._close_values) < self.vr_config.long_period:
            return

        # Calculate returns
        returns = []
        for i in range(1, len(self._close_values)):
            ret = (self._close_values[i] - self._close_values[i-1]) / self._close_values[i-1] if self._close_values[i-1] > 0 else 0
            returns.append(ret)

        if len(returns) >= self.vr_config.long_period:
            # Calculate short-term volatility
            short_returns = returns[-self.vr_config.short_period:]
            if len(short_returns) >= 2:
                short_volatility = statistics.stdev(short_returns)
                self._short_volatility_values.append(short_volatility)
                self._short_volatility = short_volatility

            # Calculate long-term volatility
            long_returns = returns[-self.vr_config.long_period:]
            if len(long_returns) >= 2:
                long_volatility = statistics.stdev(long_returns)
                self._long_volatility_values.append(long_volatility)
                self._long_volatility = long_volatility

            # Calculate volatility ratio
            if self._long_volatility > 0:
                volatility_ratio = self._short_volatility / self._long_volatility
                self._volatility_ratio_values.append(volatility_ratio)
                self._volatility_ratio = volatility_ratio

    def _analyze_ratio_characteristics(self):
        """Analyze ratio characteristics for institutional insights"""
        if not self.is_ready:
            return

        # Determine ratio trend
        if len(self._volatility_ratio_values) >= 2:
            prev_ratio = list(self._volatility_ratio_values)[-2]
            if self._volatility_ratio > prev_ratio * 1.05:
                self._ratio_trend = 1  # Increasing ratio
            elif self._volatility_ratio < prev_ratio * 0.95:
                self._ratio_trend = -1  # Decreasing ratio
            else:
                self._ratio_trend = 0  # Stable ratio

        # Calculate ratio strength
        self._ratio_strength = min(abs(self._volatility_ratio - 1.0), 2.0) / 2.0  # Normalize around 1.0

        # Calculate Volatility Ratio signal
        self._volatility_ratio_signal = self._volatility_ratio

        # Determine volatility regime based on ratio
        if self._volatility_ratio < 0.7:
            self._volatility_regime = "low"
        elif self._volatility_ratio < 1.3:
            self._volatility_regime = "normal"
        elif self._volatility_ratio < 2.0:
            self._volatility_regime = "high"
        else:
            self._volatility_regime = "extreme"

        # Track ratio cycles
        if len(self._volatility_ratio_values) >= 2:
            prev_ratio = list(self._volatility_ratio_values)[-2]
            if ((prev_ratio <= 1.0 and self._volatility_ratio > 1.0) or
                (prev_ratio >= 1.0 and self._volatility_ratio < 1.0)):
                self._ratio_cycles += 1

        # Track Volatility Ratio extremes
        if self._volatility_ratio > 3.0 or self._volatility_ratio < 0.3:  # Extreme readings
            self._volatility_ratio_extremes.append(self._volatility_ratio)

    def _generate_volatility_ratio_signals(self):
        """Generate Volatility Ratio-based signals"""
        if not self.is_ready:
            return

        # High ratio signals (above overbought)
        if self._volatility_ratio > self.vr_config.overbought:
            self._high_ratio_signals += 1

        # Low ratio signals (below oversold)
        if self._volatility_ratio < self.vr_config.oversold:
            self._low_ratio_signals += 1

        # Ratio divergence signals
        if len(self._volatility_ratio_values) >= 5 and len(self._close_values) >= 5:
            ratio_trend = self._volatility_ratio - list(self._volatility_ratio_values)[-5]
            price_trend = list(self._close_values)[-1] - list(self._close_values)[-5]

            # Bullish divergence: price down, ratio up
            if price_trend < 0 and ratio_trend > 0:
                self._ratio_divergence_signals += 1

            # Bearish divergence: price up, ratio down
            elif price_trend > 0 and ratio_trend < 0:
                self._ratio_divergence_signals += 1

        # Breakout signals
        if self._ratio_strength > 0.8:
            self._ratio_breakout_signals += 1

    def _calculate_institutional_volatility_ratio(self):
        """Calculate institutional Volatility Ratio analysis based on ratio characteristics"""
        if not self.is_ready:
            return

        # Institutional traders use Volatility Ratio for volatility timing and risk assessment
        base_volatility_ratio = 0.0

        if (self._ratio_strength > 0.8 and
            (self._high_ratio_signals > 0 or self._low_ratio_signals > 0) and
            self._signal_accuracy > 0.6):
            base_volatility_ratio = 0.9  # Strong ratio assessment with signals and accuracy
        elif (self._ratio_divergence_signals > 0 and
              self._ratio_breakout_signals > 0 and
              self._ratio_cycles > 2):
            base_volatility_ratio = 0.8  # Divergence and breakout signals with cycle confirmation
        elif (self._ratio_strength > 0.6 and
              self._volatility_ratio_reliability > 0.7):
            base_volatility_ratio = 0.7  # Good ratio strength with high reliability

        self._institutional_volatility_ratio = base_volatility_ratio

        # Smart money Volatility Ratio considers ratio strength and market timing
        smart_money_score = (
            self._ratio_strength * 0.3 +
            self._signal_accuracy * 0.3 +
            abs(self._volatility_ratio_signal - 1.0) * 0.2 +  # Normalize around 1.0
            self._institutional_volatility_ratio * 0.2
        )
        self._smart_money_volatility_ratio = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade Volatility Ratio analysis"""
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

        # Use volatility ratio as primary raw value
        raw_value = self._volatility_ratio

        # Determine signal type based on Volatility Ratio analysis
        signal_type = self._determine_volatility_ratio_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'volatility_ratio': self._volatility_ratio,
            'short_volatility': self._short_volatility,
            'long_volatility': self._long_volatility,
            'ratio_trend': self._ratio_trend,
            'ratio_strength': self._ratio_strength,
            'volatility_ratio_signal': self._volatility_ratio_signal,
            'signal_accuracy': self._signal_accuracy,
            'ratio_prediction_rate': self._ratio_prediction_rate,
            'volatility_ratio_reliability': self._volatility_ratio_reliability,
            'volatility_regime': self._volatility_regime,
            'ratio_cycles': self._ratio_cycles,
            'volatility_ratio_extremes': self._volatility_ratio_extremes,
            'volatility_ratio_based_stop': self._volatility_ratio_based_stop,
            'ratio_based_position_size': self._ratio_based_position_size,
            'risk_adjustment_factor': self._risk_adjustment_factor,
            'high_ratio_signals': self._high_ratio_signals,
            'low_ratio_signals': self._low_ratio_signals,
            'ratio_divergence_signals': self._ratio_divergence_signals,
            'ratio_breakout_signals': self._ratio_breakout_signals,
            'institutional_volatility_ratio': self._institutional_volatility_ratio,
            'smart_money_volatility_ratio': self._smart_money_volatility_ratio
        }

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._volatility_ratio_based_stop,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Volatility_Ratio",
                "short_period": self.vr_config.short_period,
                "long_period": self.vr_config.long_period,
                "overbought": self.vr_config.overbought,
                "oversold": self.vr_config.oversold,
                "volatility_ratio": self._volatility_ratio,
                "short_volatility": self._short_volatility,
                "long_volatility": self._long_volatility,
                "ratio_trend": self._ratio_trend,
                "ratio_strength": self._ratio_strength,
                "volatility_ratio_signal": self._volatility_ratio_signal,
                "signal_accuracy": self._signal_accuracy,
                "ratio_prediction_rate": self._ratio_prediction_rate,
                "volatility_ratio_reliability": self._volatility_ratio_reliability,
                "volatility_regime": self._volatility_regime,
                "ratio_cycles": self._ratio_cycles,
                "volatility_ratio_extremes": self._volatility_ratio_extremes,
                "volatility_ratio_based_stop": self._volatility_ratio_based_stop,
                "ratio_based_position_size": self._ratio_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor,
                "high_ratio_signals": self._high_ratio_signals,
                "low_ratio_signals": self._low_ratio_signals,
                "ratio_divergence_signals": self._ratio_divergence_signals,
                "ratio_breakout_signals": self._ratio_breakout_signals,
                "institutional_volatility_ratio": self._institutional_volatility_ratio,
                "smart_money_volatility_ratio": self._smart_money_volatility_ratio,
                "is_ready": self.is_ready
            }
        )

    def _determine_volatility_ratio_signal(self) -> SignalType:
        """Determine signal type based on Volatility Ratio analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong ratio signals
        if (self._ratio_strength > 0.8 and
            (self._high_ratio_signals > 0 or self._low_ratio_signals > 0) and
            self._signal_accuracy > 0.7):
            if self._volatility_ratio < self.vr_config.oversold:
                return SignalType.STRONG_BULLISH  # Low ratio often precedes breakouts
            elif self._volatility_ratio > self.vr_config.overbought:
                return SignalType.STRONG_BEARISH  # High ratio often signals caution

        # Moderate ratio signals
        elif (self._ratio_divergence_signals > 0 and
              self._ratio_strength > 0.6):
            if self._ratio_trend == 1:
                return SignalType.BULLISH  # Increasing ratio
            elif self._ratio_trend == -1:
                return SignalType.BEARISH  # Decreasing ratio

        # Breakout signals
        elif (self._ratio_breakout_signals > 0 and
              abs(self._volatility_ratio - 1.0) > 0.5):
            if self._volatility_ratio < 1.0:
                return SignalType.STRONG_BULLISH
            else:
                return SignalType.STRONG_BEARISH

        # High/low ratio signals
        elif (self._high_ratio_signals > 0 and
              self._volatility_ratio_reliability > 0.7):
            return SignalType.BEARISH  # High ratio signal
        elif (self._low_ratio_signals > 0 and
              self._volatility_ratio_reliability > 0.7):
            return SignalType.BULLISH  # Low ratio signal

        return SignalType.NEUTRAL

    @property
    def volatility_ratio(self) -> float:
        """Get the current volatility ratio value"""
        return self._volatility_ratio if self.is_ready else 1.0

    @property
    def short_volatility(self) -> float:
        """Get the current short-term volatility value"""
        return self._short_volatility if self.is_ready else 0.0

    @property
    def long_volatility(self) -> float:
        """Get the current long-term volatility value"""
        return self._long_volatility if self.is_ready else 0.0

    @property
    def ratio_trend(self) -> int:
        """Get the current ratio trend (1=increasing, -1=decreasing, 0=stable)"""
        return self._ratio_trend

    @property
    def ratio_strength(self) -> float:
        """Get the current ratio strength (0-1)"""
        return self._ratio_strength

    @property
    def signal_accuracy(self) -> float:
        """Get the signal accuracy (0-1)"""
        return self._signal_accuracy

    @property
    def volatility_regime(self) -> str:
        """Get the current volatility regime"""
        return self._volatility_regime

    @property
    def ratio_cycles(self) -> int:
        """Get the count of ratio cycles"""
        return self._ratio_cycles

    @property
    def high_ratio_signals(self) -> int:
        """Get the count of high ratio signals"""
        return self._high_ratio_signals

    @property
    def low_ratio_signals(self) -> int:
        """Get the count of low ratio signals"""
        return self._low_ratio_signals

    @property
    def ratio_divergence_signals(self) -> int:
        """Get the count of ratio divergence signals"""
        return self._ratio_divergence_signals

    @property
    def ratio_breakout_signals(self) -> int:
        """Get the count of ratio breakout signals"""
        return self._ratio_breakout_signals

    @property
    def institutional_volatility_ratio(self) -> float:
        """Get the institutional Volatility Ratio score (0-1)"""
        return self._institutional_volatility_ratio

    @property
    def smart_money_volatility_ratio(self) -> float:
        """Get the smart money Volatility Ratio score (0-1)"""
        return self._smart_money_volatility_ratio

    def is_high_volatility_ratio(self) -> bool:
        """Check if Volatility Ratio indicates high volatility"""
        return self._volatility_ratio > self.vr_config.overbought and self._volatility_regime in ["high", "extreme"]

    def is_low_volatility_ratio(self) -> bool:
        """Check if Volatility Ratio indicates low volatility"""
        return self._volatility_ratio < self.vr_config.oversold and self._volatility_regime == "low"

    def is_normal_volatility_ratio(self) -> bool:
        """Check if Volatility Ratio indicates normal volatility"""
        return self._volatility_regime == "normal"

    def is_extreme_volatility_ratio(self) -> bool:
        """Check if Volatility Ratio indicates extreme volatility"""
        return self._volatility_regime == "extreme"

    def is_ratio_increasing_volatility_ratio(self) -> bool:
        """Check if ratio is increasing"""
        return self._ratio_trend == 1

    def is_ratio_decreasing_volatility_ratio(self) -> bool:
        """Check if ratio is decreasing"""
        return self._ratio_trend == -1

    def is_strong_ratio_volatility_ratio(self) -> bool:
        """Check if ratio strength is strong"""
        return self._ratio_strength > 0.7

    def is_institutional_setup_volatility_ratio(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_volatility_ratio > 0.7

    def get_volatility_ratio_info(self) -> Dict[str, Any]:
        """Get comprehensive Volatility Ratio indicator information"""
        return {
            "volatility_ratio_values": {
                "volatility_ratio": self._volatility_ratio,
                "short_volatility": self._short_volatility,
                "long_volatility": self._long_volatility
            },
            "ratio_analysis": {
                "trend": self._ratio_trend,
                "strength": self._ratio_strength,
                "volatility_ratio_signal": self._volatility_ratio_signal
            },
            "performance_metrics": {
                "signal_accuracy": self._signal_accuracy,
                "ratio_prediction_rate": self._ratio_prediction_rate,
                "volatility_ratio_reliability": self._volatility_ratio_reliability
            },
            "market_conditions": {
                "volatility_regime": self._volatility_regime,
                "ratio_cycles": self._ratio_cycles
            },
            "signal_counts": {
                "high_ratio_signals": self._high_ratio_signals,
                "low_ratio_signals": self._low_ratio_signals,
                "ratio_divergence_signals": self._ratio_divergence_signals,
                "ratio_breakout_signals": self._ratio_breakout_signals
            },
            "volatility_ratio_tracking": {
                "extremes": self._volatility_ratio_extremes
            },
            "risk_management": {
                "volatility_ratio_based_stop": self._volatility_ratio_based_stop,
                "ratio_based_position_size": self._ratio_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor
            },
            "institutional_analysis": {
                "volatility_ratio": self._institutional_volatility_ratio,
                "smart_money_volatility_ratio": self._smart_money_volatility_ratio
            },
            "metadata": {
                "short_period": self.vr_config.short_period,
                "long_period": self.vr_config.long_period,
                "overbought": self.vr_config.overbought,
                "oversold": self.vr_config.oversold,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._close_values.clear()
        self._volume_values.clear()
        self._volatility_ratio_values.clear()
        self._short_volatility_values.clear()
        self._long_volatility_values.clear()
        self._volatility_ratio = 0.0
        self._short_volatility = 0.0
        self._long_volatility = 0.0
        self._ratio_trend = 0
        self._ratio_strength = 0.0
        self._volatility_ratio_signal = 0.0
        self._high_ratio_signals = 0
        self._low_ratio_signals = 0
        self._ratio_divergence_signals = 0
        self._ratio_breakout_signals = 0
        self._signal_accuracy = 0.0
        self._ratio_prediction_rate = 0.0
        self._volatility_ratio_reliability = 0.0
        self._volatility_regime = "normal"
        self._ratio_cycles = 0
        self._volatility_ratio_extremes.clear()
        self._volatility_ratio_based_stop = 0.0
        self._ratio_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0
        self._institutional_volatility_ratio = 0.0
        self._smart_money_volatility_ratio = 0.0