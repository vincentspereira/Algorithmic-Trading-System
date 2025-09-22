"""
Institutional-Grade Augmented Simple Moving Average (SMA) Indicator

This module implements an enhanced SMA indicator with institutional-grade features:
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
class AugmentedSMAConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented SMA"""
    sma_period: int = 20
    slope_threshold: float = 0.001  # Minimum slope for trend detection


class AugmentedSMA(AugmentedIndicator):
    """
    Institutional-grade Augmented SMA indicator implementing 5-pillar architecture.

    Features:
    - Trend direction and strength analysis
    - Support/resistance level identification
    - Slope analysis for momentum detection
    - Market regime adaptation
    - Multi-timeframe convergence
    - Smart money flow analysis
    - Automated risk management
    """

    def __init__(self, config: AugmentedSMAConfig = None):
        if config is None:
            config = AugmentedSMAConfig()

        super().__init__(config)
        self.sma_config = config

        # SMA specific state
        self._prices = deque(maxlen=self.sma_config.sma_period)
        self._sma_values = deque(maxlen=self.config.buffer_size)

        # Trend analysis
        self._trend_direction = 0  # -1, 0, 1 for down, sideways, up
        self._trend_strength = 0.0
        self._slope = 0.0

        # Support/resistance analysis
        self._support_level = 0.0
        self._resistance_level = 0.0
        self._level_confidence = 0.0

        # Momentum analysis
        self._momentum_score = 0.0
        self._acceleration = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if SMA is ready to provide signals"""
        return len(self._sma_values) > 0

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update SMA analysis

        Args:
            bar (Bar): New bar data
        """
        # Extract price (using close price as default)
        if hasattr(bar, 'close'):
            price = bar.close
        else:
            price = bar.get('close', bar.get('price', 0.0))

        # Update SMA calculation
        self._update_sma(price)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_sma(self, price: float):
        """Update the core SMA calculation with institutional enhancements"""
        self._prices.append(price)

        if len(self._prices) >= self.sma_config.sma_period:
            # Calculate SMA
            sma = sum(self._prices) / len(self._prices)
            self._sma_values.append(sma)

            # Analyze trend characteristics
            self._analyze_trend()

            # Update support/resistance levels
            self._update_support_resistance(price, sma)

    def _analyze_trend(self):
        """Analyze trend direction, strength, and slope"""
        if not self.is_ready or len(self._sma_values) < 3:
            return

        recent_smas = list(self._sma_values)[-3:]

        # Calculate slope (trend direction and strength)
        self._slope = (recent_smas[-1] - recent_smas[0]) / 3

        # Determine trend direction
        if self._slope > self.sma_config.slope_threshold:
            self._trend_direction = 1  # Uptrend
            self._trend_strength = min(1.0, self._slope / (recent_smas[0] * 0.01))  # Normalize
        elif self._slope < -self.sma_config.slope_threshold:
            self._trend_direction = -1  # Downtrend
            self._trend_strength = min(1.0, abs(self._slope) / (recent_smas[0] * 0.01))  # Normalize
        else:
            self._trend_direction = 0  # Sideways
            self._trend_strength = 0.0

        # Calculate momentum and acceleration
        if len(self._sma_values) >= 5:
            older_smas = list(self._sma_values)[-5:]
            self._momentum_score = (older_smas[-1] - older_smas[0]) / 5

            # Calculate acceleration (change in slope)
            if len(self._sma_values) >= 7:
                slopes = []
                for i in range(2, len(self._sma_values) - 2):
                    slope = (self._sma_values[i+1] - self._sma_values[i-1]) / 3
                    slopes.append(slope)

                if len(slopes) >= 2:
                    self._acceleration = slopes[-1] - slopes[-2]

    def _update_support_resistance(self, current_price: float, sma: float):
        """Update support and resistance levels based on SMA analysis"""
        if not self.is_ready:
            return

        # SMA often acts as dynamic support/resistance
        price_distance = abs(current_price - sma) / sma

        if price_distance < 0.005:  # Price within 0.5% of SMA
            # High confidence that SMA is acting as support/resistance
            self._level_confidence = 0.8

            if current_price > sma:
                self._support_level = sma
                self._resistance_level = sma * 1.01  # Potential resistance above
            else:
                self._resistance_level = sma
                self._support_level = sma * 0.99  # Potential support below
        else:
            self._level_confidence = max(0.0, 0.5 - price_distance * 10)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade SMA analysis"""
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

        sma_value = self._sma_values[-1]

        # Determine signal type based on SMA analysis
        signal_type = self._determine_sma_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'trend_strength': self._trend_strength,
            'momentum_score': min(1.0, abs(self._momentum_score) / (sma_value * 0.005)),
            'level_confidence': self._level_confidence
        }

        # Use SMA value as primary raw value
        raw_value = sma_value

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._suggested_sl,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "SMA",
                "sma_period": self.sma_config.sma_period,
                "trend_direction": self._trend_direction,
                "trend_strength": self._trend_strength,
                "slope": self._slope,
                "momentum_score": self._momentum_score,
                "acceleration": self._acceleration,
                "support_level": self._support_level,
                "resistance_level": self._resistance_level,
                "level_confidence": self._level_confidence,
                "is_ready": self.is_ready
            }
        )

    def _determine_sma_signal(self) -> SignalType:
        """Determine signal type based on SMA analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong trend signals
        if self._trend_strength > 0.7:
            if self._trend_direction == 1:
                return SignalType.BULLISH
            elif self._trend_direction == -1:
                return SignalType.BEARISH

        # Moderate trend signals
        elif self._trend_strength > 0.3:
            if self._trend_direction == 1:
                return SignalType.BULLISH
            elif self._trend_direction == -1:
                return SignalType.BEARISH

        # High momentum signals
        elif abs(self._momentum_score) > sma_value * 0.003:  # 0.3% momentum
            if self._momentum_score > 0:
                return SignalType.BULLISH
            else:
                return SignalType.BEARISH

        return SignalType.NEUTRAL

    @property
    def sma(self) -> float:
        """Get the current SMA value"""
        return self._sma_values[-1] if self.is_ready else 0.0

    @property
    def trend_direction(self) -> int:
        """Get the current trend direction (-1, 0, 1)"""
        return self._trend_direction

    @property
    def trend_strength(self) -> float:
        """Get the current trend strength (0-1)"""
        return self._trend_strength

    @property
    def slope(self) -> float:
        """Get the current SMA slope"""
        return self._slope

    @property
    def momentum_score(self) -> float:
        """Get the current momentum score"""
        return self._momentum_score

    @property
    def acceleration(self) -> float:
        """Get the current acceleration (change in slope)"""
        return self._acceleration

    @property
    def support_level(self) -> float:
        """Get the identified support level"""
        return self._support_level

    @property
    def resistance_level(self) -> float:
        """Get the identified resistance level"""
        return self._resistance_level

    @property
    def level_confidence(self) -> float:
        """Get the confidence in support/resistance levels"""
        return self._level_confidence

    def is_above_sma(self, current_price: float) -> bool:
        """Check if price is above SMA"""
        if not self.is_ready:
            return False
        return current_price > self.sma

    def is_below_sma(self, current_price: float) -> bool:
        """Check if price is below SMA"""
        if not self.is_ready:
            return False
        return current_price < self.sma

    def is_uptrend(self) -> bool:
        """Check if SMA indicates an uptrend"""
        return self._trend_direction == 1

    def is_downtrend(self) -> bool:
        """Check if SMA indicates a downtrend"""
        return self._trend_direction == -1

    def is_sideways(self) -> bool:
        """Check if SMA indicates sideways movement"""
        return self._trend_direction == 0

    def get_sma_info(self) -> Dict[str, Any]:
        """Get comprehensive SMA information"""
        return {
            "sma_value": self.sma,
            "trend_analysis": {
                "direction": self._trend_direction,
                "strength": self._trend_strength,
                "slope": self._slope
            },
            "momentum_analysis": {
                "momentum_score": self._momentum_score,
                "acceleration": self._acceleration
            },
            "level_analysis": {
                "support_level": self._support_level,
                "resistance_level": self._resistance_level,
                "level_confidence": self._level_confidence
            },
            "metadata": {
                "period": self.sma_config.sma_period,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._prices.clear()
        self._sma_values.clear()
        self._trend_direction = 0
        self._trend_strength = 0.0
        self._slope = 0.0
        self._support_level = 0.0
        self._resistance_level = 0.0
        self._level_confidence = 0.0
        self._momentum_score = 0.0
        self._acceleration = 0.0