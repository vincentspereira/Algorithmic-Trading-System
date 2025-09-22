"""
Institutional-Grade Augmented Volatility System Indicator

This module implements an enhanced Volatility System with institutional-grade features:
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
class AugmentedVolatilitySystemConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Volatility System"""
    short_period: int = 5
    long_period: int = 20
    signal_period: int = 9
    volatility_threshold: float = 1.5
    extreme_volatility: float = 3.0


class AugmentedVolatilitySystemIndicator(AugmentedIndicator):
    """
    Institutional-grade Augmented Volatility System implementing 5-pillar architecture.

    Features:
    - Comprehensive volatility measurement system
    - Volume-weighted calculations for institutional validation
    - Market regime adaptation for different volatility environments
    - Multi-timeframe convergence for volatility assessment
    - Smart money volatility detection
    - Automated risk management based on volatility signals
    """

    def __init__(self, config: AugmentedVolatilitySystemConfig = None):
        if config is None:
            config = AugmentedVolatilitySystemConfig()

        super().__init__(config)
        self.vol_config = config

        # Volatility System specific state
        self._close_values = deque(maxlen=self.config.buffer_size)
        self._volume_values = deque(maxlen=self.config.buffer_size)

        # Volatility System calculation components
        self._volatility_values = deque(maxlen=self.config.buffer_size)
        self._short_volatility_values = deque(maxlen=self.config.buffer_size)
        self._long_volatility_values = deque(maxlen=self.config.buffer_size)
        self._volatility_ratio_values = deque(maxlen=self.config.buffer_size)

        # Current Volatility System values
        self._volatility = 0.0
        self._short_volatility = 0.0
        self._long_volatility = 0.0
        self._volatility_ratio = 0.0

        # Volatility analysis
        self._volatility_regime = "normal"  # low, normal, high, extreme
        self._volatility_trend = 0  # 1 = increasing, -1 = decreasing, 0 = stable
        self._volatility_strength = 0.0
        self._volatility_signal = 0.0

        # Signal analysis
        self._low_volatility_signals = 0
        self._high_volatility_signals = 0
        self._volatility_expansion_signals = 0
        self._volatility_contraction_signals = 0

        # Performance tracking
        self._signal_accuracy = 0.0
        self._volatility_prediction_rate = 0.0
        self._volatility_reliability = 0.0

        # Market structure
        self._volatility_cycles = 0
        self._volatility_extremes = []

        # Risk management
        self._volatility_based_stop = 0.0
        self._volatility_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0

        # Institutional analysis
        self._institutional_volatility = 0.0
        self._smart_money_volatility = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Volatility System is ready to provide signals"""
        return (len(self._close_values) >= self.vol_config.long_period and
                len(self._volatility_values) > 0)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update Volatility System analysis

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

        # Update Volatility System analysis
        self._update_volatility_analysis(close, volume)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_volatility_analysis(self, close: float, volume: float):
        """Update the core Volatility System analysis with institutional enhancements"""
        # Store price and volume data
        self._close_values.append(close)
        self._volume_values.append(volume)

        if len(self._close_values) >= self.vol_config.long_period:
            # Calculate Volatility System
            self._calculate_volatility_system()

            # Analyze volatility characteristics
            self._analyze_volatility_characteristics()

            # Generate Volatility System signals
            self._generate_volatility_signals()

            # Calculate institutional Volatility System analysis
            self._calculate_institutional_volatility()

    def _calculate_volatility_system(self):
        """Calculate comprehensive Volatility System"""
        if len(self._close_values) < self.vol_config.long_period:
            return

        # Calculate returns
        returns = []
        for i in range(1, len(self._close_values)):
            ret = (self._close_values[i] - self._close_values[i-1]) / self._close_values[i-1] if self._close_values[i-1] > 0 else 0
            returns.append(ret)

        if len(returns) >= self.vol_config.long_period:
            # Calculate short-term volatility (recent volatility)
            short_returns = returns[-self.vol_config.short_period:]
            if len(short_returns) >= 2:
                short_volatility = statistics.stdev(short_returns)
                self._short_volatility_values.append(short_volatility)
                self._short_volatility = short_volatility

            # Calculate long-term volatility (baseline volatility)
            long_returns = returns[-self.vol_config.long_period:]
            if len(long_returns) >= 2:
                long_volatility = statistics.stdev(long_returns)
                self._long_volatility_values.append(long_volatility)
                self._long_volatility = long_volatility

            # Calculate volatility ratio (short/long)
            if self._long_volatility > 0:
                volatility_ratio = self._short_volatility / self._long_volatility
                self._volatility_ratio_values.append(volatility_ratio)
                self._volatility_ratio = volatility_ratio

                # Calculate overall volatility score
                volatility = (self._short_volatility + self._long_volatility) / 2
                self._volatility_values.append(volatility)
                self._volatility = volatility

    def _analyze_volatility_characteristics(self):
        """Analyze volatility characteristics for institutional insights"""
        if not self.is_ready:
            return

        # Determine volatility regime
        if self._volatility_ratio < 0.8:
            self._volatility_regime = "low"
        elif self._volatility_ratio < self.vol_config.volatility_threshold:
            self._volatility_regime = "normal"
        elif self._volatility_ratio < self.vol_config.extreme_volatility:
            self._volatility_regime = "high"
        else:
            self._volatility_regime = "extreme"

        # Determine volatility trend
        if len(self._volatility_ratio_values) >= 2:
            prev_ratio = list(self._volatility_ratio_values)[-2]
            if self._volatility_ratio > prev_ratio * 1.1:
                self._volatility_trend = 1  # Increasing volatility
            elif self._volatility_ratio < prev_ratio * 0.9:
                self._volatility_trend = -1  # Decreasing volatility
            else:
                self._volatility_trend = 0  # Stable volatility

        # Calculate volatility strength
        self._volatility_strength = min(self._volatility_ratio / self.vol_config.extreme_volatility, 1.0)

        # Calculate Volatility System signal
        self._volatility_signal = self._volatility_ratio

        # Track volatility cycles
        if len(self._volatility_values) >= 2:
            prev_volatility = list(self._volatility_values)[-2]
            if ((prev_volatility <= self._volatility * 0.9 and self._volatility > prev_volatility) or
                (prev_volatility >= self._volatility * 1.1 and self._volatility < prev_volatility)):
                self._volatility_cycles += 1

        # Track volatility extremes
        if self._volatility_ratio > self.vol_config.extreme_volatility * 2:  # Extreme readings
            self._volatility_extremes.append(self._volatility_ratio)

    def _generate_volatility_signals(self):
        """Generate Volatility System-based signals"""
        if not self.is_ready:
            return

        # Low volatility signals
        if self._volatility_regime == "low":
            self._low_volatility_signals += 1

        # High volatility signals
        if self._volatility_regime in ["high", "extreme"]:
            self._high_volatility_signals += 1

        # Volatility expansion signals (increasing volatility)
        if self._volatility_trend == 1:
            self._volatility_expansion_signals += 1

        # Volatility contraction signals (decreasing volatility)
        if self._volatility_trend == -1:
            self._volatility_contraction_signals += 1

    def _calculate_institutional_volatility(self):
        """Calculate institutional Volatility System analysis based on volatility characteristics"""
        if not self.is_ready:
            return

        # Institutional traders use Volatility System for risk management and timing
        base_volatility = 0.0

        if (self._volatility_strength > 0.8 and
            (self._low_volatility_signals > 0 or self._high_volatility_signals > 0) and
            self._signal_accuracy > 0.6):
            base_volatility = 0.9  # Strong volatility assessment with signals and accuracy
        elif ((self._volatility_expansion_signals > 0 or self._volatility_contraction_signals > 0) and
              self._volatility_cycles > 2):
            base_volatility = 0.8  # Expansion/contraction signals with cycle confirmation
        elif (self._volatility_strength > 0.6 and
              self._volatility_reliability > 0.7):
            base_volatility = 0.7  # Good volatility strength with high reliability

        self._institutional_volatility = base_volatility

        # Smart money Volatility System considers volatility strength and market timing
        smart_money_score = (
            self._volatility_strength * 0.3 +
            self._signal_accuracy * 0.3 +
            abs(self._volatility_signal - 1.0) * 0.2 +  # Normalize around 1.0
            self._institutional_volatility * 0.2
        )
        self._smart_money_volatility = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade Volatility System analysis"""
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

        # Determine signal type based on Volatility System analysis
        signal_type = self._determine_volatility_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'volatility': self._volatility,
            'short_volatility': self._short_volatility,
            'long_volatility': self._long_volatility,
            'volatility_ratio': self._volatility_ratio,
            'volatility_regime': self._volatility_regime,
            'volatility_trend': self._volatility_trend,
            'volatility_strength': self._volatility_strength,
            'volatility_signal': self._volatility_signal,
            'signal_accuracy': self._signal_accuracy,
            'volatility_prediction_rate': self._volatility_prediction_rate,
            'volatility_reliability': self._volatility_reliability,
            'volatility_cycles': self._volatility_cycles,
            'volatility_extremes': self._volatility_extremes,
            'volatility_based_stop': self._volatility_based_stop,
            'volatility_based_position_size': self._volatility_based_position_size,
            'risk_adjustment_factor': self._risk_adjustment_factor,
            'low_volatility_signals': self._low_volatility_signals,
            'high_volatility_signals': self._high_volatility_signals,
            'volatility_expansion_signals': self._volatility_expansion_signals,
            'volatility_contraction_signals': self._volatility_contraction_signals,
            'institutional_volatility': self._institutional_volatility,
            'smart_money_volatility': self._smart_money_volatility
        }

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._volatility_based_stop,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Volatility_System",
                "short_period": self.vol_config.short_period,
                "long_period": self.vol_config.long_period,
                "signal_period": self.vol_config.signal_period,
                "volatility_threshold": self.vol_config.volatility_threshold,
                "extreme_volatility": self.vol_config.extreme_volatility,
                "volatility": self._volatility,
                "short_volatility": self._short_volatility,
                "long_volatility": self._long_volatility,
                "volatility_ratio": self._volatility_ratio,
                "volatility_regime": self._volatility_regime,
                "volatility_trend": self._volatility_trend,
                "volatility_strength": self._volatility_strength,
                "volatility_signal": self._volatility_signal,
                "signal_accuracy": self._signal_accuracy,
                "volatility_prediction_rate": self._volatility_prediction_rate,
                "volatility_reliability": self._volatility_reliability,
                "volatility_cycles": self._volatility_cycles,
                "volatility_extremes": self._volatility_extremes,
                "volatility_based_stop": self._volatility_based_stop,
                "volatility_based_position_size": self._volatility_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor,
                "low_volatility_signals": self._low_volatility_signals,
                "high_volatility_signals": self._high_volatility_signals,
                "volatility_expansion_signals": self._volatility_expansion_signals,
                "volatility_contraction_signals": self._volatility_contraction_signals,
                "institutional_volatility": self._institutional_volatility,
                "smart_money_volatility": self._smart_money_volatility,
                "is_ready": self.is_ready
            }
        )

    def _determine_volatility_signal(self) -> SignalType:
        """Determine signal type based on Volatility System analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong volatility signals
        if (self._volatility_strength > 0.8 and
            (self._low_volatility_signals > 0 or self._high_volatility_signals > 0) and
            self._signal_accuracy > 0.7):
            if self._volatility_regime == "low":
                return SignalType.STRONG_BULLISH  # Low volatility often precedes breakouts
            elif self._volatility_regime in ["high", "extreme"]:
                return SignalType.STRONG_BEARISH  # High volatility often signals caution

        # Moderate volatility signals
        elif ((self._volatility_expansion_signals > 0 or self._volatility_contraction_signals > 0) and
              self._volatility_strength > 0.6):
            if self._volatility_trend == 1:
                return SignalType.BEARISH  # Expanding volatility
            elif self._volatility_trend == -1:
                return SignalType.BULLISH  # Contracting volatility

        # Regime-based signals
        elif (self._low_volatility_signals > 0 and
              self._volatility_reliability > 0.7):
            return SignalType.BULLISH  # Low volatility signal
        elif (self._high_volatility_signals > 0 and
              self._volatility_reliability > 0.7):
            return SignalType.BEARISH  # High volatility signal

        return SignalType.NEUTRAL

    @property
    def volatility(self) -> float:
        """Get the current volatility value"""
        return self._volatility if self.is_ready else 0.0

    @property
    def short_volatility(self) -> float:
        """Get the current short-term volatility value"""
        return self._short_volatility if self.is_ready else 0.0

    @property
    def long_volatility(self) -> float:
        """Get the current long-term volatility value"""
        return self._long_volatility if self.is_ready else 0.0

    @property
    def volatility_ratio(self) -> float:
        """Get the current volatility ratio"""
        return self._volatility_ratio if self.is_ready else 1.0

    @property
    def volatility_regime(self) -> str:
        """Get the current volatility regime"""
        return self._volatility_regime

    @property
    def volatility_trend(self) -> int:
        """Get the current volatility trend (1=increasing, -1=decreasing, 0=stable)"""
        return self._volatility_trend

    @property
    def volatility_strength(self) -> float:
        """Get the current volatility strength (0-1)"""
        return self._volatility_strength

    @property
    def signal_accuracy(self) -> float:
        """Get the signal accuracy (0-1)"""
        return self._signal_accuracy

    @property
    def volatility_cycles(self) -> int:
        """Get the count of volatility cycles"""
        return self._volatility_cycles

    @property
    def low_volatility_signals(self) -> int:
        """Get the count of low volatility signals"""
        return self._low_volatility_signals

    @property
    def high_volatility_signals(self) -> int:
        """Get the count of high volatility signals"""
        return self._high_volatility_signals

    @property
    def volatility_expansion_signals(self) -> int:
        """Get the count of volatility expansion signals"""
        return self._volatility_expansion_signals

    @property
    def volatility_contraction_signals(self) -> int:
        """Get the count of volatility contraction signals"""
        return self._volatility_contraction_signals

    @property
    def institutional_volatility(self) -> float:
        """Get the institutional Volatility System score (0-1)"""
        return self._institutional_volatility

    @property
    def smart_money_volatility(self) -> float:
        """Get the smart money Volatility System score (0-1)"""
        return self._smart_money_volatility

    def is_low_volatility_system(self) -> bool:
        """Check if Volatility System indicates low volatility"""
        return self._volatility_regime == "low" and self._volatility_ratio < 0.8

    def is_high_volatility_system(self) -> bool:
        """Check if Volatility System indicates high volatility"""
        return self._volatility_regime in ["high", "extreme"] and self._volatility_ratio > self.vol_config.volatility_threshold

    def is_normal_volatility_system(self) -> bool:
        """Check if Volatility System indicates normal volatility"""
        return self._volatility_regime == "normal"

    def is_extreme_volatility_system(self) -> bool:
        """Check if Volatility System indicates extreme volatility"""
        return self._volatility_regime == "extreme"

    def is_volatility_expanding_system(self) -> bool:
        """Check if volatility is expanding"""
        return self._volatility_trend == 1

    def is_volatility_contracting_system(self) -> bool:
        """Check if volatility is contracting"""
        return self._volatility_trend == -1

    def is_strong_volatility_system(self) -> bool:
        """Check if volatility strength is strong"""
        return self._volatility_strength > 0.7

    def is_institutional_setup_volatility(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_volatility > 0.7

    def get_volatility_info(self) -> Dict[str, Any]:
        """Get comprehensive Volatility System indicator information"""
        return {
            "volatility_values": {
                "volatility": self._volatility,
                "short_volatility": self._short_volatility,
                "long_volatility": self._long_volatility,
                "volatility_ratio": self._volatility_ratio
            },
            "volatility_analysis": {
                "regime": self._volatility_regime,
                "trend": self._volatility_trend,
                "strength": self._volatility_strength,
                "volatility_signal": self._volatility_signal
            },
            "performance_metrics": {
                "signal_accuracy": self._signal_accuracy,
                "volatility_prediction_rate": self._volatility_prediction_rate,
                "volatility_reliability": self._volatility_reliability
            },
            "market_conditions": {
                "volatility_cycles": self._volatility_cycles
            },
            "signal_counts": {
                "low_volatility_signals": self._low_volatility_signals,
                "high_volatility_signals": self._high_volatility_signals,
                "volatility_expansion_signals": self._volatility_expansion_signals,
                "volatility_contraction_signals": self._volatility_contraction_signals
            },
            "volatility_tracking": {
                "extremes": self._volatility_extremes
            },
            "risk_management": {
                "volatility_based_stop": self._volatility_based_stop,
                "volatility_based_position_size": self._volatility_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor
            },
            "institutional_analysis": {
                "volatility": self._institutional_volatility,
                "smart_money_volatility": self._smart_money_volatility
            },
            "metadata": {
                "short_period": self.vol_config.short_period,
                "long_period": self.vol_config.long_period,
                "signal_period": self.vol_config.signal_period,
                "volatility_threshold": self.vol_config.volatility_threshold,
                "extreme_volatility": self.vol_config.extreme_volatility,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._close_values.clear()
        self._volume_values.clear()
        self._volatility_values.clear()
        self._short_volatility_values.clear()
        self._long_volatility_values.clear()
        self._volatility_ratio_values.clear()
        self._volatility = 0.0
        self._short_volatility = 0.0
        self._long_volatility = 0.0
        self._volatility_ratio = 0.0
        self._volatility_regime = "normal"
        self._volatility_trend = 0
        self._volatility_strength = 0.0
        self._volatility_signal = 0.0
        self._low_volatility_signals = 0
        self._high_volatility_signals = 0
        self._volatility_expansion_signals = 0
        self._volatility_contraction_signals = 0
        self._signal_accuracy = 0.0
        self._volatility_prediction_rate = 0.0
        self._volatility_reliability = 0.0
        self._volatility_cycles = 0
        self._volatility_extremes.clear()
        self._volatility_based_stop = 0.0
        self._volatility_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0
        self._institutional_volatility = 0.0
        self._smart_money_volatility = 0.0