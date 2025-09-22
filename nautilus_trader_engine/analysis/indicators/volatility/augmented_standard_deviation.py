"""
Institutional-Grade Augmented Standard Deviation Indicator

This module implements an enhanced Standard Deviation indicator with institutional-grade features:
- Volume confirmation scoring
- Market regime adaptation
- Multi-timeframe convergence
- Smart money detection
- Automated risk management
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime
from collections import deque
import statistics

from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import (
    AugmentedIndicator,
    AugmentedIndicatorConfig,
    IndicatorSignal,
    SignalType,
)


@dataclass
class AugmentedStandardDeviationConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Standard Deviation"""
    std_period: int = 20
    volatility_threshold: float = 0.02  # 2% threshold for high volatility
    stability_threshold: float = 0.005  # 0.5% threshold for low volatility


class AugmentedStandardDeviation(AugmentedIndicator):
    """
    Institutional-grade Augmented Standard Deviation indicator implementing 5-pillar architecture.

    Features:
    - Volatility measurement and trend analysis
    - Market regime classification based on volatility levels
    - Risk assessment and position sizing
    - Breakout probability analysis
    - Institutional volatility adaptation
    - Automated risk management
    """

    def __init__(self, config: AugmentedStandardDeviationConfig = None):
        if config is None:
            config = AugmentedStandardDeviationConfig()

        super().__init__(config)
        self.std_config = config

        # Standard Deviation specific state
        self._prices = deque(maxlen=self.config.buffer_size)
        self._returns = deque(maxlen=self.config.buffer_size)
        self._std_values = deque(maxlen=self.config.buffer_size)
        self._current_std = None

        # Volatility analysis
        self._volatility_level = 0.0
        self._volatility_trend = "neutral"  # "increasing", "decreasing", "stable"
        self._volatility_regime = "normal"  # "low", "normal", "high", "extreme"

        # Risk analysis
        self._risk_level = 0.0
        self._breakout_probability = 0.0
        self._stability_score = 0.0

        # Market structure
        self._volatility_clusters = []
        self._regime_changes = 0
        self._volatility_mean = 0.0

        # Institutional analysis
        self._institutional_volatility = 0.0
        self._smart_money_volatility = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Standard Deviation is ready to provide signals"""
        return len(self._std_values) > 0 and self._current_std is not None

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update Standard Deviation analysis

        Args:
            bar (Bar): New bar data
        """
        # Extract price
        if hasattr(bar, 'close'):
            price = bar.close
        else:
            price = bar.get('close', bar.get('price', 0.0))

        # Update Standard Deviation calculation
        self._update_standard_deviation(price)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_standard_deviation(self, price: float):
        """Update the core Standard Deviation calculation with institutional enhancements"""
        self._prices.append(price)

        if len(self._prices) >= 2:
            # Calculate returns (percentage changes)
            current_return = (price - self._prices[-2]) / self._prices[-2] if self._prices[-2] != 0 else 0.0
            self._returns.append(current_return)

        if len(self._returns) >= self.std_config.std_period:
            # Calculate standard deviation of returns
            returns_list = list(self._returns)[-self.std_config.std_period:]
            if len(returns_list) >= 2:
                self._current_std = statistics.stdev(returns_list)
                self._std_values.append(self._current_std)

                # Analyze volatility characteristics
                self._analyze_volatility_characteristics(price)

    def _analyze_volatility_characteristics(self, current_price: float):
        """Analyze volatility characteristics for institutional insights"""
        if not self.is_ready or len(self._std_values) < 3:
            return

        std_value = self._current_std

        # Calculate volatility level and regime
        self._volatility_level = std_value

        # Classify volatility regime
        if std_value < self.std_config.stability_threshold:
            self._volatility_regime = "low"
        elif std_value < self.std_config.volatility_threshold:
            self._volatility_regime = "normal"
        elif std_value < self.std_config.volatility_threshold * 2:
            self._volatility_regime = "high"
        else:
            self._volatility_regime = "extreme"

        # Calculate volatility trend
        if len(self._std_values) >= 5:
            recent_std = list(self._std_values)[-5:]
            std_trend = (recent_std[-1] - recent_std[0]) / 5

            if std_trend > 0.0001:
                self._volatility_trend = "increasing"
            elif std_trend < -0.0001:
                self._volatility_trend = "decreasing"
            else:
                self._volatility_trend = "stable"

        # Calculate risk level
        self._risk_level = min(1.0, std_value / (self.std_config.volatility_threshold * 3))

        # Calculate breakout probability
        if std_value > self.std_config.volatility_threshold:
            self._breakout_probability = min(1.0, std_value / (self.std_config.volatility_threshold * 2))
        else:
            self._breakout_probability = 0.0

        # Calculate stability score
        if len(self._std_values) >= 10:
            std_history = list(self._std_values)[-10:]
            std_mean = sum(std_history) / len(std_history)
            std_std = statistics.stdev(std_history) if len(std_history) > 1 else 0

            if std_mean > 0:
                # Lower coefficient of variation = higher stability
                cv = std_std / std_mean
                self._stability_score = max(0.0, 1.0 - cv * 2)

        # Track volatility clusters
        self._update_volatility_clusters()

        # Calculate institutional volatility metrics
        self._calculate_institutional_volatility()

    def _update_volatility_clusters(self):
        """Track volatility clusters for institutional analysis"""
        if not self.is_ready:
            return

        # Track periods of high volatility
        if self._volatility_regime in ["high", "extreme"]:
            self._volatility_clusters.append(self._current_std)
            # Keep only recent clusters
            if len(self._volatility_clusters) > 20:
                self._volatility_clusters.pop(0)

        # Track regime changes
        if len(self._std_values) >= 2:
            prev_regime = self._classify_regime(self._std_values[-2])
            current_regime = self._volatility_regime

            if prev_regime != current_regime:
                self._regime_changes += 1

    def _classify_regime(self, std_value: float) -> str:
        """Classify volatility regime for a given standard deviation value"""
        if std_value < self.std_config.stability_threshold:
            return "low"
        elif std_value < self.std_config.volatility_threshold:
            return "normal"
        elif std_value < self.std_config.volatility_threshold * 2:
            return "high"
        else:
            return "extreme"

    def _calculate_institutional_volatility(self):
        """Calculate institutional volatility metrics"""
        if not self.is_ready:
            return

        # Institutional volatility considers both magnitude and consistency
        base_volatility = self._volatility_level

        # Adjust for regime stability
        if self._volatility_trend == "stable":
            base_volatility *= 1.2  # More predictable = higher institutional confidence
        elif self._volatility_trend == "increasing":
            base_volatility *= 0.8   # Increasing volatility = lower confidence

        self._institutional_volatility = min(1.0, base_volatility / self.std_config.volatility_threshold)

        # Smart money volatility considers breakout potential
        smart_money_score = (
            self._breakout_probability * 0.4 +
            self._stability_score * 0.3 +
            (1.0 - self._risk_level) * 0.3
        )
        self._smart_money_volatility = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade Standard Deviation analysis"""
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

        std_value = self._current_std

        # Determine signal type based on Standard Deviation analysis
        signal_type = self._determine_std_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'volatility_level': self._volatility_level,
            'risk_level': self._risk_level,
            'breakout_probability': self._breakout_probability,
            'stability_score': self._stability_score,
            'institutional_volatility': self._institutional_volatility,
            'smart_money_volatility': self._smart_money_volatility
        }

        # Use Standard Deviation value as primary raw value
        raw_value = std_value

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._suggested_sl,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Standard_Deviation",
                "std_period": self.std_config.std_period,
                "volatility_threshold": self.std_config.volatility_threshold,
                "stability_threshold": self.std_config.stability_threshold,
                "volatility_level": self._volatility_level,
                "volatility_trend": self._volatility_trend,
                "volatility_regime": self._volatility_regime,
                "risk_level": self._risk_level,
                "breakout_probability": self._breakout_probability,
                "stability_score": self._stability_score,
                "regime_changes": self._regime_changes,
                "volatility_clusters_count": len(self._volatility_clusters),
                "institutional_volatility": self._institutional_volatility,
                "smart_money_volatility": self._smart_money_volatility,
                "is_ready": self.is_ready
            }
        )

    def _determine_std_signal(self) -> SignalType:
        """Determine signal type based on Standard Deviation analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        std_value = self._current_std

        # High volatility signals (potential breakouts)
        if std_value >= self.std_config.volatility_threshold * 1.5:
            return SignalType.STRONG_BULLISH if self._breakout_probability > 0.7 else SignalType.BULLISH

        # Low volatility signals (potential range trading)
        elif std_value <= self.std_config.stability_threshold:
            return SignalType.NEUTRAL  # Low volatility often means consolidation

        # Normal volatility signals
        elif std_value >= self.std_config.volatility_threshold:
            return SignalType.BULLISH

        return SignalType.NEUTRAL

    @property
    def standard_deviation(self) -> float:
        """Get the current Standard Deviation value"""
        return self._current_std if self.is_ready else 0.0

    @property
    def volatility_level(self) -> float:
        """Get the current volatility level"""
        return self._volatility_level

    @property
    def volatility_trend(self) -> str:
        """Get the current volatility trend"""
        return self._volatility_trend

    @property
    def volatility_regime(self) -> str:
        """Get the current volatility regime"""
        return self._volatility_regime

    @property
    def risk_level(self) -> float:
        """Get the current risk level (0-1)"""
        return self._risk_level

    @property
    def breakout_probability(self) -> float:
        """Get the breakout probability (0-1)"""
        return self._breakout_probability

    @property
    def stability_score(self) -> float:
        """Get the stability score (0-1)"""
        return self._stability_score

    @property
    def regime_changes(self) -> int:
        """Get the number of regime changes"""
        return self._regime_changes

    @property
    def volatility_clusters(self) -> list:
        """Get the list of volatility clusters"""
        return self._volatility_clusters.copy()

    @property
    def institutional_volatility(self) -> float:
        """Get the institutional volatility score (0-1)"""
        return self._institutional_volatility

    @property
    def smart_money_volatility(self) -> float:
        """Get the smart money volatility score (0-1)"""
        return self._smart_money_volatility

    def is_high_volatility(self) -> bool:
        """Check if volatility is high"""
        if not self.is_ready:
            return False
        return self._volatility_regime in ["high", "extreme"]

    def is_low_volatility(self) -> bool:
        """Check if volatility is low"""
        if not self.is_ready:
            return False
        return self._volatility_regime == "low"

    def is_volatility_increasing(self) -> bool:
        """Check if volatility is increasing"""
        return self._volatility_trend == "increasing"

    def is_volatility_stable(self) -> bool:
        """Check if volatility is stable"""
        return self._volatility_trend == "stable"

    def is_breakout_likely(self) -> bool:
        """Check if breakout is likely"""
        return self._breakout_probability > 0.6

    def is_market_stable(self) -> bool:
        """Check if market is stable"""
        return self._stability_score > 0.7

    def get_standard_deviation_info(self) -> Dict[str, Any]:
        """Get comprehensive Standard Deviation information"""
        return {
            "std_value": self.standard_deviation,
            "volatility_analysis": {
                "level": self._volatility_level,
                "trend": self._volatility_trend,
                "regime": self._volatility_regime
            },
            "risk_analysis": {
                "risk_level": self._risk_level,
                "breakout_probability": self._breakout_probability,
                "stability_score": self._stability_score
            },
            "market_structure": {
                "regime_changes": self._regime_changes,
                "volatility_clusters_count": len(self._volatility_clusters)
            },
            "institutional_analysis": {
                "volatility": self._institutional_volatility,
                "smart_money_volatility": self._smart_money_volatility
            },
            "metadata": {
                "period": self.std_config.std_period,
                "volatility_threshold": self.std_config.volatility_threshold,
                "stability_threshold": self.std_config.stability_threshold,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._prices.clear()
        self._returns.clear()
        self._std_values.clear()
        self._current_std = None
        self._volatility_level = 0.0
        self._volatility_trend = "neutral"
        self._volatility_regime = "normal"
        self._risk_level = 0.0
        self._breakout_probability = 0.0
        self._stability_score = 0.0
        self._volatility_clusters.clear()
        self._regime_changes = 0
        self._volatility_mean = 0.0
        self._institutional_volatility = 0.0
        self._smart_money_volatility = 0.0