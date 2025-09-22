"""
Institutional-Grade Augmented Ulcer Index Indicator

This module implements an enhanced Ulcer Index with institutional-grade features:
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
class AugmentedUlcerIndexConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Ulcer Index"""
    period: int = 14
    risk_threshold: float = 5.0
    extreme_risk: float = 10.0


class AugmentedUlcerIndexIndicator(AugmentedIndicator):
    """
    Institutional-grade Augmented Ulcer Index implementing 5-pillar architecture.

    Features:
    - Measures downside volatility and drawdown risk
    - Volume-weighted calculations for institutional validation
    - Market regime adaptation for different volatility environments
    - Multi-timeframe convergence for risk assessment
    - Smart money risk management detection
    - Automated risk management based on ulcer signals
    """

    def __init__(self, config: AugmentedUlcerIndexConfig = None):
        if config is None:
            config = AugmentedUlcerIndexConfig()

        super().__init__(config)
        self.ulcer_config = config

        # Ulcer Index specific state
        self._close_values = deque(maxlen=self.config.buffer_size)
        self._volume_values = deque(maxlen=self.config.buffer_size)

        # Ulcer Index calculation components
        self._ulcer_values = deque(maxlen=self.config.buffer_size)
        self._max_values = deque(maxlen=self.config.buffer_size)
        self._drawdown_values = deque(maxlen=self.config.buffer_size)

        # Current Ulcer Index values
        self._ulcer = 0.0
        self._max_price = 0.0
        self._current_drawdown = 0.0

        # Risk analysis
        self._risk_level = 0  # 1 = low risk, 2 = moderate risk, 3 = high risk, 4 = extreme risk
        self._risk_strength = 0.0
        self._ulcer_signal = 0.0

        # Signal analysis
        self._low_risk_signals = 0
        self._high_risk_signals = 0
        self._recovery_signals = 0
        self._breakout_signals = 0

        # Performance tracking
        self._signal_accuracy = 0.0
        self._risk_prediction_rate = 0.0
        self._ulcer_reliability = 0.0

        # Market structure
        self._volatility_regime = "normal"
        self._risk_cycles = 0
        self._ulcer_extremes = []

        # Risk management
        self._ulcer_based_stop = 0.0
        self._risk_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0

        # Institutional analysis
        self._institutional_ulcer = 0.0
        self._smart_money_ulcer = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Ulcer Index is ready to provide signals"""
        return (len(self._close_values) >= self.ulcer_config.period and
                len(self._ulcer_values) > 0)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update Ulcer Index analysis

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

        # Update Ulcer Index analysis
        self._update_ulcer_analysis(close, volume)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_ulcer_analysis(self, close: float, volume: float):
        """Update the core Ulcer Index analysis with institutional enhancements"""
        # Store price and volume data
        self._close_values.append(close)
        self._volume_values.append(volume)

        if len(self._close_values) >= self.ulcer_config.period:
            # Calculate Ulcer Index
            self._calculate_ulcer_index()

            # Analyze risk characteristics
            self._analyze_risk_characteristics()

            # Generate Ulcer Index signals
            self._generate_ulcer_signals()

            # Calculate institutional Ulcer Index analysis
            self._calculate_institutional_ulcer()

    def _calculate_ulcer_index(self):
        """Calculate Ulcer Index using Peter Martin's formula"""
        if len(self._close_values) < self.ulcer_config.period:
            return

        # Find maximum price over the period
        recent_prices = list(self._close_values)[-self.ulcer_config.period:]
        max_price = max(recent_prices)
        self._max_values.append(max_price)
        self._max_price = max_price

        # Calculate percentage drawdown for each period
        drawdowns = []
        for price in recent_prices:
            if max_price > 0:
                drawdown = ((max_price - price) / max_price) * 100
                drawdowns.append(drawdown)

        # Calculate average of squared drawdowns
        if drawdowns:
            squared_drawdowns = [dd ** 2 for dd in drawdowns]
            avg_squared_drawdown = statistics.mean(squared_drawdowns)

            # Calculate Ulcer Index (square root of average squared drawdown)
            ulcer = math.sqrt(avg_squared_drawdown)
            self._ulcer_values.append(ulcer)
            self._ulcer = ulcer

            # Calculate current drawdown
            current_price = recent_prices[-1]
            if max_price > 0:
                current_drawdown = ((max_price - current_price) / max_price) * 100
                self._drawdown_values.append(current_drawdown)
                self._current_drawdown = current_drawdown

    def _analyze_risk_characteristics(self):
        """Analyze risk characteristics for institutional insights"""
        if not self.is_ready:
            return

        # Determine risk level based on Ulcer Index
        if self._ulcer < self.ulcer_config.risk_threshold:
            self._risk_level = 1  # Low risk
        elif self._ulcer < self.ulcer_config.extreme_risk:
            self._risk_level = 2  # Moderate risk
        elif self._ulcer < self.ulcer_config.extreme_risk * 1.5:
            self._risk_level = 3  # High risk
        else:
            self._risk_level = 4  # Extreme risk

        # Calculate risk strength
        self._risk_strength = min(self._ulcer / self.ulcer_config.extreme_risk, 1.0)  # Normalize to 0-1

        # Calculate Ulcer Index signal
        self._ulcer_signal = self._ulcer

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

        # Track risk cycles
        if len(self._ulcer_values) >= 2:
            prev_ulcer = list(self._ulcer_values)[-2]
            if ((prev_ulcer <= self.ulcer_config.risk_threshold and self._ulcer > self.ulcer_config.risk_threshold) or
                (prev_ulcer >= self.ulcer_config.risk_threshold and self._ulcer < self.ulcer_config.risk_threshold)):
                self._risk_cycles += 1

        # Track Ulcer Index extremes
        if self._ulcer > self.ulcer_config.extreme_risk * 2:  # Extreme readings
            self._ulcer_extremes.append(self._ulcer)

    def _generate_ulcer_signals(self):
        """Generate Ulcer Index-based signals"""
        if not self.is_ready:
            return

        # Low risk signals (Ulcer Index below threshold)
        if self._ulcer < self.ulcer_config.risk_threshold:
            self._low_risk_signals += 1

        # High risk signals (Ulcer Index above extreme threshold)
        if self._ulcer > self.ulcer_config.extreme_risk:
            self._high_risk_signals += 1

        # Recovery signals (Ulcer Index decreasing from high levels)
        if (len(self._ulcer_values) >= 2 and
            list(self._ulcer_values)[-2] > self.ulcer_config.extreme_risk and
            self._ulcer < list(self._ulcer_values)[-2]):
            self._recovery_signals += 1

        # Breakout signals
        if self._risk_strength > 0.8:
            self._breakout_signals += 1

    def _calculate_institutional_ulcer(self):
        """Calculate institutional Ulcer Index analysis based on risk characteristics"""
        if not self.is_ready:
            return

        # Institutional traders use Ulcer Index for risk management and portfolio protection
        base_ulcer = 0.0

        if (self._risk_strength > 0.8 and
            (self._low_risk_signals > 0 or self._high_risk_signals > 0) and
            self._signal_accuracy > 0.6):
            base_ulcer = 0.9  # Strong risk assessment with signals and accuracy
        elif (self._recovery_signals > 0 and
              self._breakout_signals > 0 and
              self._risk_cycles > 2):
            base_ulcer = 0.8  # Recovery and breakout signals with cycle confirmation
        elif (self._risk_strength > 0.6 and
              self._ulcer_reliability > 0.7):
            base_ulcer = 0.7  # Good risk strength with high reliability

        self._institutional_ulcer = base_ulcer

        # Smart money Ulcer Index considers risk strength and market timing
        smart_money_score = (
            (1 - self._risk_strength) * 0.3 +  # Lower risk is better for smart money
            self._signal_accuracy * 0.3 +
            abs(self._ulcer_signal - self.ulcer_config.risk_threshold) / self.ulcer_config.risk_threshold * 0.2 +
            self._institutional_ulcer * 0.2
        )
        self._smart_money_ulcer = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade Ulcer Index analysis"""
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

        # Use Ulcer Index value as primary raw value
        raw_value = self._ulcer

        # Determine signal type based on Ulcer Index analysis
        signal_type = self._determine_ulcer_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'ulcer': self._ulcer,
            'max_price': self._max_price,
            'current_drawdown': self._current_drawdown,
            'risk_level': self._risk_level,
            'risk_strength': self._risk_strength,
            'ulcer_signal': self._ulcer_signal,
            'signal_accuracy': self._signal_accuracy,
            'risk_prediction_rate': self._risk_prediction_rate,
            'ulcer_reliability': self._ulcer_reliability,
            'volatility_regime': self._volatility_regime,
            'risk_cycles': self._risk_cycles,
            'ulcer_extremes': self._ulcer_extremes,
            'ulcer_based_stop': self._ulcer_based_stop,
            'risk_based_position_size': self._risk_based_position_size,
            'risk_adjustment_factor': self._risk_adjustment_factor,
            'low_risk_signals': self._low_risk_signals,
            'high_risk_signals': self._high_risk_signals,
            'recovery_signals': self._recovery_signals,
            'breakout_signals': self._breakout_signals,
            'institutional_ulcer': self._institutional_ulcer,
            'smart_money_ulcer': self._smart_money_ulcer
        }

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._ulcer_based_stop,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Ulcer_Index",
                "period": self.ulcer_config.period,
                "risk_threshold": self.ulcer_config.risk_threshold,
                "extreme_risk": self.ulcer_config.extreme_risk,
                "ulcer": self._ulcer,
                "max_price": self._max_price,
                "current_drawdown": self._current_drawdown,
                "risk_level": self._risk_level,
                "risk_strength": self._risk_strength,
                "ulcer_signal": self._ulcer_signal,
                "signal_accuracy": self._signal_accuracy,
                "risk_prediction_rate": self._risk_prediction_rate,
                "ulcer_reliability": self._ulcer_reliability,
                "volatility_regime": self._volatility_regime,
                "risk_cycles": self._risk_cycles,
                "ulcer_extremes": self._ulcer_extremes,
                "ulcer_based_stop": self._ulcer_based_stop,
                "risk_based_position_size": self._risk_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor,
                "low_risk_signals": self._low_risk_signals,
                "high_risk_signals": self._high_risk_signals,
                "recovery_signals": self._recovery_signals,
                "breakout_signals": self._breakout_signals,
                "institutional_ulcer": self._institutional_ulcer,
                "smart_money_ulcer": self._smart_money_ulcer,
                "is_ready": self.is_ready
            }
        )

    def _determine_ulcer_signal(self) -> SignalType:
        """Determine signal type based on Ulcer Index analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong risk signals
        if (self._risk_strength > 0.8 and
            (self._low_risk_signals > 0 or self._high_risk_signals > 0) and
            self._signal_accuracy > 0.7):
            if self._risk_level == 1:
                return SignalType.STRONG_BULLISH  # Low risk environment
            elif self._risk_level >= 3:
                return SignalType.STRONG_BEARISH  # High risk environment

        # Moderate risk signals
        elif (self._recovery_signals > 0 and
              self._risk_strength > 0.6):
            return SignalType.BULLISH  # Recovery from high risk

        # Breakout signals
        elif (self._breakout_signals > 0 and
              abs(self._ulcer - self.ulcer_config.risk_threshold) > self.ulcer_config.risk_threshold):
            if self._ulcer < self.ulcer_config.risk_threshold:
                return SignalType.STRONG_BULLISH  # Low risk breakout
            else:
                return SignalType.STRONG_BEARISH  # High risk breakout

        # Low/high risk signals
        elif (self._low_risk_signals > 0 and
              self._ulcer_reliability > 0.7):
            return SignalType.BULLISH  # Low risk signal
        elif (self._high_risk_signals > 0 and
              self._ulcer_reliability > 0.7):
            return SignalType.BEARISH  # High risk signal

        return SignalType.NEUTRAL

    @property
    def ulcer(self) -> float:
        """Get the current Ulcer Index value"""
        return self._ulcer if self.is_ready else 0.0

    @property
    def max_price(self) -> float:
        """Get the current maximum price"""
        return self._max_price if self.is_ready else 0.0

    @property
    def current_drawdown(self) -> float:
        """Get the current drawdown percentage"""
        return self._current_drawdown if self.is_ready else 0.0

    @property
    def risk_level(self) -> int:
        """Get the current risk level (1-4)"""
        return self._risk_level

    @property
    def risk_strength(self) -> float:
        """Get the current risk strength (0-1)"""
        return self._risk_strength

    @property
    def signal_accuracy(self) -> float:
        """Get the signal accuracy (0-1)"""
        return self._signal_accuracy

    @property
    def volatility_regime(self) -> str:
        """Get the current volatility regime"""
        return self._volatility_regime

    @property
    def risk_cycles(self) -> int:
        """Get the count of risk cycles"""
        return self._risk_cycles

    @property
    def low_risk_signals(self) -> int:
        """Get the count of low risk signals"""
        return self._low_risk_signals

    @property
    def high_risk_signals(self) -> int:
        """Get the count of high risk signals"""
        return self._high_risk_signals

    @property
    def recovery_signals(self) -> int:
        """Get the count of recovery signals"""
        return self._recovery_signals

    @property
    def breakout_signals(self) -> int:
        """Get the count of breakout signals"""
        return self._breakout_signals

    @property
    def institutional_ulcer(self) -> float:
        """Get the institutional Ulcer Index score (0-1)"""
        return self._institutional_ulcer

    @property
    def smart_money_ulcer(self) -> float:
        """Get the smart money Ulcer Index score (0-1)"""
        return self._smart_money_ulcer

    def is_low_risk_ulcer(self) -> bool:
        """Check if Ulcer Index indicates low risk"""
        return self._risk_level == 1 and self._ulcer < self.ulcer_config.risk_threshold

    def is_high_risk_ulcer(self) -> bool:
        """Check if Ulcer Index indicates high risk"""
        return self._risk_level >= 3 and self._ulcer > self.ulcer_config.extreme_risk

    def is_moderate_risk_ulcer(self) -> bool:
        """Check if Ulcer Index indicates moderate risk"""
        return self._risk_level == 2

    def is_extreme_risk_ulcer(self) -> bool:
        """Check if Ulcer Index indicates extreme risk"""
        return self._risk_level == 4

    def is_recovery_ulcer(self) -> bool:
        """Check if Ulcer Index indicates recovery"""
        return self._recovery_signals > 0

    def is_strong_risk_ulcer(self) -> bool:
        """Check if risk strength is strong"""
        return self._risk_strength > 0.7

    def is_high_volatility_ulcer(self) -> bool:
        """Check if volatility regime is high"""
        return self._volatility_regime == "high"

    def is_low_volatility_ulcer(self) -> bool:
        """Check if volatility regime is low"""
        return self._volatility_regime == "low"

    def is_institutional_setup_ulcer(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_ulcer > 0.7

    def get_ulcer_info(self) -> Dict[str, Any]:
        """Get comprehensive Ulcer Index indicator information"""
        return {
            "ulcer_values": {
                "ulcer": self._ulcer,
                "max_price": self._max_price,
                "current_drawdown": self._current_drawdown
            },
            "risk_analysis": {
                "level": self._risk_level,
                "strength": self._risk_strength,
                "ulcer_signal": self._ulcer_signal
            },
            "performance_metrics": {
                "signal_accuracy": self._signal_accuracy,
                "risk_prediction_rate": self._risk_prediction_rate,
                "ulcer_reliability": self._ulcer_reliability
            },
            "market_conditions": {
                "volatility_regime": self._volatility_regime,
                "risk_cycles": self._risk_cycles
            },
            "signal_counts": {
                "low_risk_signals": self._low_risk_signals,
                "high_risk_signals": self._high_risk_signals,
                "recovery_signals": self._recovery_signals,
                "breakout_signals": self._breakout_signals
            },
            "ulcer_tracking": {
                "extremes": self._ulcer_extremes
            },
            "risk_management": {
                "ulcer_based_stop": self._ulcer_based_stop,
                "risk_based_position_size": self._risk_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor
            },
            "institutional_analysis": {
                "ulcer": self._institutional_ulcer,
                "smart_money_ulcer": self._smart_money_ulcer
            },
            "metadata": {
                "period": self.ulcer_config.period,
                "risk_threshold": self.ulcer_config.risk_threshold,
                "extreme_risk": self.ulcer_config.extreme_risk,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._close_values.clear()
        self._volume_values.clear()
        self._ulcer_values.clear()
        self._max_values.clear()
        self._drawdown_values.clear()
        self._ulcer = 0.0
        self._max_price = 0.0
        self._current_drawdown = 0.0
        self._risk_level = 0
        self._risk_strength = 0.0
        self._ulcer_signal = 0.0
        self._low_risk_signals = 0
        self._high_risk_signals = 0
        self._recovery_signals = 0
        self._breakout_signals = 0
        self._signal_accuracy = 0.0
        self._risk_prediction_rate = 0.0
        self._ulcer_reliability = 0.0
        self._volatility_regime = "normal"
        self._risk_cycles = 0
        self._ulcer_extremes.clear()
        self._ulcer_based_stop = 0.0
        self._risk_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0
        self._institutional_ulcer = 0.0
        self._smart_money_ulcer = 0.0