"""
Institutional-Grade Augmented Rate of Change (ROC) Indicator

This module implements an enhanced ROC indicator with institutional-grade features:
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
class AugmentedROCConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented ROC"""
    roc_period: int = 14
    overbought_level: float = 5.0  # ROC > 5% considered overbought
    oversold_level: float = -5.0   # ROC < -5% considered oversold


class AugmentedROC(AugmentedIndicator):
    """
    Institutional-grade Augmented ROC indicator implementing 5-pillar architecture.

    Features:
    - Momentum strength analysis and divergence detection
    - Trend continuation/breakout identification
    - Market regime adaptation based on momentum patterns
    - Multi-timeframe convergence
    - Smart money flow analysis
    - Automated risk management
    """

    def __init__(self, config: AugmentedROCConfig = None):
        if config is None:
            config = AugmentedROCConfig()

        super().__init__(config)
        self.roc_config = config

        # ROC specific state
        self._prices = deque(maxlen=self.roc_config.roc_period)
        self._roc_values = deque(maxlen=self.config.buffer_size)
        self._current_roc = None

        # Momentum analysis
        self._momentum_strength = 0.0
        self._momentum_direction = 0  # -1, 0, 1 for down, neutral, up
        self._momentum_acceleration = 0.0

        # Divergence detection
        self._bullish_divergence = False
        self._bearish_divergence = False
        self._divergence_confidence = 0.0

        # Trend analysis
        self._trend_alignment = 0.0
        self._breakout_probability = 0.0

        # Market structure
        self._overbought_signals = 0
        self._oversold_signals = 0
        self._mean_reversion_probability = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if ROC is ready to provide signals"""
        return len(self._roc_values) > 0 and self._current_roc is not None

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update ROC analysis

        Args:
            bar (Bar): New bar data
        """
        # Extract price
        if hasattr(bar, 'close'):
            price = bar.close
        else:
            price = bar.get('close', bar.get('price', 0.0))

        # Update ROC calculation
        self._update_roc(price)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_roc(self, price: float):
        """Update the core ROC calculation with institutional enhancements"""
        self._prices.append(price)

        if len(self._prices) >= self.roc_config.roc_period:
            # Calculate ROC: ((current - past) / past) * 100
            past_price = self._prices[0]  # Price from roc_period bars ago
            if past_price > 0:
                self._current_roc = ((price - past_price) / past_price) * 100
                self._roc_values.append(self._current_roc)

                # Analyze ROC characteristics
                self._analyze_roc_characteristics(price)

    def _analyze_roc_characteristics(self, current_price: float):
        """Analyze ROC characteristics for institutional insights"""
        if not self.is_ready or len(self._roc_values) < 3:
            return

        # Calculate momentum strength and direction
        roc_value = self._current_roc

        # Momentum strength (absolute ROC value normalized)
        self._momentum_strength = min(1.0, abs(roc_value) / 10.0)  # 10% ROC = max strength

        # Momentum direction
        if roc_value > 1.0:
            self._momentum_direction = 1  # Strong up momentum
        elif roc_value < -1.0:
            self._momentum_direction = -1  # Strong down momentum
        else:
            self._momentum_direction = 0  # Neutral momentum

        # Calculate momentum acceleration
        if len(self._roc_values) >= 3:
            recent_roc = list(self._roc_values)[-3:]
            self._momentum_acceleration = (recent_roc[-1] - recent_roc[-2]) - (recent_roc[-2] - recent_roc[-3])

        # Detect overbought/oversold conditions
        if roc_value >= self.roc_config.overbought_level:
            self._overbought_signals += 1
        elif roc_value <= self.roc_config.oversold_level:
            self._oversold_signals += 1

        # Calculate mean reversion probability
        if roc_value > self.roc_config.overbought_level:
            self._mean_reversion_probability = min(1.0, (roc_value - self.roc_config.overbought_level) / 5.0)
        elif roc_value < self.roc_config.oversold_level:
            self._mean_reversion_probability = min(1.0, (abs(roc_value) - abs(self.roc_config.oversold_level)) / 5.0)
        else:
            self._mean_reversion_probability = 0.0

        # Calculate breakout probability
        if abs(roc_value) > 8.0:  # Strong momentum
            self._breakout_probability = min(1.0, abs(roc_value) / 15.0)
        else:
            self._breakout_probability = 0.0

        # Detect divergences (simplified version)
        self._detect_divergences()

        # Calculate trend alignment
        self._calculate_trend_alignment()

    def _detect_divergences(self):
        """Detect bullish/bearish divergences between ROC and price"""
        if not self.is_ready or len(self._prices) < 5 or len(self._roc_values) < 5:
            return

        # Simple divergence detection
        recent_prices = list(self._prices)[-5:]
        recent_roc = list(self._roc_values)[-5:]

        # Check for bullish divergence (price makes lower low, ROC makes higher low)
        price_trend = recent_prices[-1] - recent_prices[-3]
        roc_trend = recent_roc[-1] - recent_roc[-3]

        if price_trend < 0 and roc_trend > 0 and recent_roc[-1] > -2.0:
            self._bullish_divergence = True
            self._bearish_divergence = False
            self._divergence_confidence = min(1.0, abs(roc_trend) / 3.0)

        # Check for bearish divergence (price makes higher high, ROC makes lower high)
        elif price_trend > 0 and roc_trend < 0 and recent_roc[-1] < 2.0:
            self._bullish_divergence = False
            self._bearish_divergence = True
            self._divergence_confidence = min(1.0, abs(roc_trend) / 3.0)

        else:
            self._bullish_divergence = False
            self._bearish_divergence = False
            self._divergence_confidence = 0.0

    def _calculate_trend_alignment(self):
        """Calculate alignment between ROC momentum and price trend"""
        if not self.is_ready or len(self._prices) < 3:
            return

        # Price trend over last 3 periods
        recent_prices = list(self._prices)[-3:]
        price_trend = recent_prices[-1] - recent_prices[0]

        # ROC trend over last 3 periods
        recent_roc = list(self._roc_values)[-3:]
        roc_trend = recent_roc[-1] - recent_roc[0]

        # Calculate alignment
        if (price_trend > 0 and roc_trend > 0) or (price_trend < 0 and roc_trend < 0):
            self._trend_alignment = 0.8  # Strong alignment
        elif (price_trend > 0 and roc_trend < 0) or (price_trend < 0 and roc_trend > 0):
            self._trend_alignment = 0.2  # Poor alignment
        else:
            self._trend_alignment = 0.5  # Neutral alignment

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade ROC analysis"""
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

        roc_value = self._current_roc

        # Determine signal type based on ROC analysis
        signal_type = self._determine_roc_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'momentum_strength': self._momentum_strength,
            'trend_alignment': self._trend_alignment,
            'breakout_probability': self._breakout_probability,
            'mean_reversion_probability': self._mean_reversion_probability,
            'divergence_confidence': self._divergence_confidence
        }

        # Use ROC value as primary raw value
        raw_value = roc_value

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._suggested_sl,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "ROC",
                "roc_period": self.roc_config.roc_period,
                "overbought_level": self.roc_config.overbought_level,
                "oversold_level": self.roc_config.oversold_level,
                "momentum_direction": self._momentum_direction,
                "momentum_strength": self._momentum_strength,
                "momentum_acceleration": self._momentum_acceleration,
                "bullish_divergence": self._bullish_divergence,
                "bearish_divergence": self._bearish_divergence,
                "divergence_confidence": self._divergence_confidence,
                "trend_alignment": self._trend_alignment,
                "breakout_probability": self._breakout_probability,
                "mean_reversion_probability": self._mean_reversion_probability,
                "overbought_signals": self._overbought_signals,
                "oversold_signals": self._oversold_signals,
                "is_ready": self.is_ready
            }
        )

    def _determine_roc_signal(self) -> SignalType:
        """Determine signal type based on ROC analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        roc_value = self._current_roc

        # Strong momentum signals
        if roc_value > 8.0 and self._momentum_strength > 0.7:
            return SignalType.STRONG_BULLISH
        elif roc_value < -8.0 and self._momentum_strength > 0.7:
            return SignalType.STRONG_BEARISH

        # Overbought/oversold signals
        elif roc_value >= self.roc_config.overbought_level:
            return SignalType.BEARISH
        elif roc_value <= self.roc_config.oversold_level:
            return SignalType.BULLISH

        # Divergence signals
        elif self._bullish_divergence and self._divergence_confidence > 0.6:
            return SignalType.BULLISH
        elif self._bearish_divergence and self._divergence_confidence > 0.6:
            return SignalType.BEARISH

        # Moderate momentum signals
        elif roc_value > 3.0:
            return SignalType.BULLISH
        elif roc_value < -3.0:
            return SignalType.BEARISH

        return SignalType.NEUTRAL

    @property
    def roc(self) -> float:
        """Get the current ROC value"""
        return self._current_roc if self.is_ready else 0.0

    @property
    def momentum_strength(self) -> float:
        """Get the current momentum strength (0-1)"""
        return self._momentum_strength

    @property
    def momentum_direction(self) -> int:
        """Get the current momentum direction (-1, 0, 1)"""
        return self._momentum_direction

    @property
    def momentum_acceleration(self) -> float:
        """Get the current momentum acceleration"""
        return self._momentum_acceleration

    @property
    def bullish_divergence(self) -> bool:
        """Return True if bullish divergence is detected"""
        return self._bullish_divergence

    @property
    def bearish_divergence(self) -> bool:
        """Return True if bearish divergence is detected"""
        return self._bearish_divergence

    @property
    def divergence_confidence(self) -> float:
        """Get the confidence in divergence detection"""
        return self._divergence_confidence

    @property
    def trend_alignment(self) -> float:
        """Get the trend alignment score (0-1)"""
        return self._trend_alignment

    @property
    def breakout_probability(self) -> float:
        """Get the breakout probability (0-1)"""
        return self._breakout_probability

    @property
    def mean_reversion_probability(self) -> float:
        """Get the mean reversion probability (0-1)"""
        return self._mean_reversion_probability

    @property
    def overbought_signals(self) -> int:
        """Get the count of overbought signals"""
        return self._overbought_signals

    @property
    def oversold_signals(self) -> int:
        """Get the count of oversold signals"""
        return self._oversold_signals

    def is_overbought(self) -> bool:
        """Check if ROC indicates overbought conditions"""
        if not self.is_ready:
            return False
        return self._current_roc >= self.roc_config.overbought_level

    def is_oversold(self) -> bool:
        """Check if ROC indicates oversold conditions"""
        if not self.is_ready:
            return False
        return self._current_roc <= self.roc_config.oversold_level

    def is_strong_momentum(self) -> bool:
        """Check if ROC shows strong momentum"""
        return self._momentum_strength > 0.7

    def is_divergence_present(self) -> bool:
        """Check if any divergence is present"""
        return self._bullish_divergence or self._bearish_divergence

    def get_roc_info(self) -> Dict[str, Any]:
        """Get comprehensive ROC information"""
        return {
            "roc_value": self.roc,
            "momentum_analysis": {
                "direction": self._momentum_direction,
                "strength": self._momentum_strength,
                "acceleration": self._momentum_acceleration
            },
            "divergence_analysis": {
                "bullish": self._bullish_divergence,
                "bearish": self._bearish_divergence,
                "confidence": self._divergence_confidence
            },
            "market_analysis": {
                "trend_alignment": self._trend_alignment,
                "breakout_probability": self._breakout_probability,
                "mean_reversion_probability": self._mean_reversion_probability
            },
            "signal_counts": {
                "overbought": self._overbought_signals,
                "oversold": self._oversold_signals
            },
            "metadata": {
                "period": self.roc_config.roc_period,
                "overbought_level": self.roc_config.overbought_level,
                "oversold_level": self.roc_config.oversold_level,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._prices.clear()
        self._roc_values.clear()
        self._current_roc = None
        self._momentum_strength = 0.0
        self._momentum_direction = 0
        self._momentum_acceleration = 0.0
        self._bullish_divergence = False
        self._bearish_divergence = False
        self._divergence_confidence = 0.0
        self._trend_alignment = 0.0
        self._breakout_probability = 0.0
        self._mean_reversion_probability = 0.0
        self._overbought_signals = 0
        self._oversold_signals = 0