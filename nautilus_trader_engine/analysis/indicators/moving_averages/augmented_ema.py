"""
Institutional-Grade Augmented Exponential Moving Average (EMA) Indicator

This module implements an enhanced EMA indicator with institutional-grade features:
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
class AugmentedEMAConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented EMA"""
    ema_period: int = 20
    responsiveness_threshold: float = 0.002  # Minimum change for responsiveness detection


class AugmentedEMA(AugmentedIndicator):
    """
    Institutional-grade Augmented EMA indicator implementing 5-pillar architecture.

    Features:
    - Responsive trend direction and strength analysis
    - Dynamic support/resistance level identification
    - Responsiveness analysis for market momentum
    - Market regime adaptation
    - Multi-timeframe convergence
    - Smart money flow analysis
    - Automated risk management
    """

    def __init__(self, config: AugmentedEMAConfig = None):
        if config is None:
            config = AugmentedEMAConfig()

        super().__init__(config)
        self.ema_config = config

        # EMA specific state
        self._prices = deque(maxlen=self.config.buffer_size)
        self._ema_values = deque(maxlen=self.config.buffer_size)
        self._alpha = 2.0 / (self.ema_config.ema_period + 1)
        self._current_ema = None

        # Trend analysis
        self._trend_direction = 0  # -1, 0, 1 for down, sideways, up
        self._trend_strength = 0.0
        self._slope = 0.0

        # Responsiveness analysis
        self._responsiveness = 0.0
        self._momentum_alignment = 0.0

        # Support/resistance analysis
        self._dynamic_support = 0.0
        self._dynamic_resistance = 0.0
        self._level_strength = 0.0

        # Convergence analysis
        self._price_ema_distance = 0.0
        self._distance_trend = "neutral"  # "widening", "narrowing", "stable"

    @property
    def is_ready(self) -> bool:
        """Return True if EMA is ready to provide signals"""
        return len(self._ema_values) > 0 and self._current_ema is not None

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update EMA analysis

        Args:
            bar (Bar): New bar data
        """
        # Extract price (using close price as default)
        if hasattr(bar, 'close'):
            price = bar.close
        else:
            price = bar.get('close', bar.get('price', 0.0))

        # Update EMA calculation
        self._update_ema(price)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_ema(self, price: float):
        """Update the core EMA calculation with institutional enhancements"""
        self._prices.append(price)

        # Calculate EMA
        if self._current_ema is None:
            self._current_ema = price
        else:
            self._current_ema = self._alpha * price + (1 - self._alpha) * self._current_ema

        self._ema_values.append(self._current_ema)

        # Analyze EMA characteristics
        self._analyze_ema_characteristics(price)

    def _analyze_ema_characteristics(self, current_price: float):
        """Analyze EMA characteristics for institutional insights"""
        if not self.is_ready or len(self._ema_values) < 3:
            return

        # Calculate trend direction and strength
        recent_emas = list(self._ema_values)[-3:]
        self._slope = (recent_emas[-1] - recent_emas[0]) / 3

        # Determine trend direction
        if self._slope > self.ema_config.responsiveness_threshold:
            self._trend_direction = 1  # Uptrend
            self._trend_strength = min(1.0, self._slope / (recent_emas[0] * 0.01))
        elif self._slope < -self.ema_config.responsiveness_threshold:
            self._trend_direction = -1  # Downtrend
            self._trend_strength = min(1.0, abs(self._slope) / (recent_emas[0] * 0.01))
        else:
            self._trend_direction = 0  # Sideways
            self._trend_strength = 0.0

        # Calculate responsiveness (how quickly EMA reacts to price changes)
        if len(self._prices) >= 3:
            recent_prices = list(self._prices)[-3:]
            price_change = abs(recent_prices[-1] - recent_prices[0]) / recent_prices[0]
            ema_change = abs(recent_emas[-1] - recent_emas[0]) / recent_emas[0]
            self._responsiveness = min(1.0, ema_change / price_change) if price_change > 0 else 0.0

        # Calculate price-EMA distance and trend
        if self._current_ema > 0:
            current_distance = abs(current_price - self._current_ema) / self._current_ema
            self._price_ema_distance = current_distance

            # Analyze distance trend
            if len(self._ema_values) >= 5:
                older_distances = []
                for i in range(-5, 0):
                    if i + len(self._prices) >= 0:
                        older_price = self._prices[i]
                        older_ema = self._ema_values[i]
                        if older_ema > 0:
                            older_distances.append(abs(older_price - older_ema) / older_ema)

                if len(older_distances) >= 2:
                    distance_trend = current_distance - older_distances[0]
                    if distance_trend > 0.001:
                        self._distance_trend = "widening"
                    elif distance_trend < -0.001:
                        self._distance_trend = "narrowing"
                    else:
                        self._distance_trend = "stable"

        # Update dynamic support/resistance levels
        self._update_dynamic_levels(current_price)

        # Calculate momentum alignment
        self._calculate_momentum_alignment()

    def _update_dynamic_levels(self, current_price: float):
        """Update dynamic support and resistance levels based on EMA"""
        if not self.is_ready:
            return

        # EMA often acts as dynamic support/resistance
        price_position = (current_price - self._current_ema) / self._current_ema

        if abs(price_position) < 0.01:  # Price within 1% of EMA
            self._level_strength = 0.9  # High confidence

            if current_price > self._current_ema:
                self._dynamic_support = self._current_ema
                self._dynamic_resistance = self._current_ema * 1.02
            else:
                self._dynamic_resistance = self._current_ema
                self._dynamic_support = self._current_ema * 0.98
        else:
            self._level_strength = max(0.0, 0.7 - abs(price_position) * 5)

    def _calculate_momentum_alignment(self):
        """Calculate alignment between price momentum and EMA momentum"""
        if not self.is_ready or len(self._prices) < 5 or len(self._ema_values) < 5:
            return

        # Calculate price momentum (recent price change rate)
        recent_prices = list(self._prices)[-5:]
        price_momentum = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]

        # Calculate EMA momentum
        recent_emas = list(self._ema_values)[-5:]
        ema_momentum = (recent_emas[-1] - recent_emas[0]) / recent_emas[0]

        # Calculate alignment score
        if abs(price_momentum) > 0.001 and abs(ema_momentum) > 0.001:
            alignment = 1.0 - abs(price_momentum - ema_momentum) / max(abs(price_momentum), abs(ema_momentum))
            self._momentum_alignment = max(0.0, min(1.0, alignment))
        else:
            self._momentum_alignment = 0.5  # Neutral alignment

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade EMA analysis"""
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

        ema_value = self._current_ema

        # Determine signal type based on EMA analysis
        signal_type = self._determine_ema_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'trend_strength': self._trend_strength,
            'responsiveness': self._responsiveness,
            'momentum_alignment': self._momentum_alignment,
            'level_strength': self._level_strength
        }

        # Use EMA value as primary raw value
        raw_value = ema_value

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._suggested_sl,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "EMA",
                "ema_period": self.ema_config.ema_period,
                "alpha": self._alpha,
                "trend_direction": self._trend_direction,
                "trend_strength": self._trend_strength,
                "slope": self._slope,
                "responsiveness": self._responsiveness,
                "momentum_alignment": self._momentum_alignment,
                "price_ema_distance": self._price_ema_distance,
                "distance_trend": self._distance_trend,
                "dynamic_support": self._dynamic_support,
                "dynamic_resistance": self._dynamic_resistance,
                "level_strength": self._level_strength,
                "is_ready": self.is_ready
            }
        )

    def _determine_ema_signal(self) -> SignalType:
        """Determine signal type based on EMA analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong trend signals
        if self._trend_strength > 0.7:
            if self._trend_direction == 1:
                return SignalType.BULLISH
            elif self._trend_direction == -1:
                return SignalType.BEARISH

        # High responsiveness signals
        elif self._responsiveness > 0.8 and self._trend_strength > 0.4:
            if self._trend_direction == 1:
                return SignalType.BULLISH
            elif self._trend_direction == -1:
                return SignalType.BEARISH

        # Momentum alignment signals
        elif self._momentum_alignment > 0.8 and abs(self._slope) > self.ema_config.responsiveness_threshold:
            if self._slope > 0:
                return SignalType.BULLISH
            else:
                return SignalType.BEARISH

        return SignalType.NEUTRAL

    @property
    def ema(self) -> float:
        """Get the current EMA value"""
        return self._current_ema if self.is_ready else 0.0

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
        """Get the current EMA slope"""
        return self._slope

    @property
    def responsiveness(self) -> float:
        """Get the current EMA responsiveness (0-1)"""
        return self._responsiveness

    @property
    def momentum_alignment(self) -> float:
        """Get the current momentum alignment score (0-1)"""
        return self._momentum_alignment

    @property
    def price_ema_distance(self) -> float:
        """Get the current price-EMA distance (as percentage)"""
        return self._price_ema_distance

    @property
    def distance_trend(self) -> str:
        """Get the current distance trend"""
        return self._distance_trend

    @property
    def dynamic_support(self) -> float:
        """Get the dynamic support level"""
        return self._dynamic_support

    @property
    def dynamic_resistance(self) -> float:
        """Get the dynamic resistance level"""
        return self._dynamic_resistance

    @property
    def level_strength(self) -> float:
        """Get the strength of dynamic levels (0-1)"""
        return self._level_strength

    def is_above_ema(self, current_price: float) -> bool:
        """Check if price is above EMA"""
        if not self.is_ready:
            return False
        return current_price > self.ema

    def is_below_ema(self, current_price: float) -> bool:
        """Check if price is below EMA"""
        if not self.is_ready:
            return False
        return current_price < self.ema

    def is_responsive(self) -> bool:
        """Check if EMA is highly responsive to price changes"""
        return self._responsiveness > 0.7

    def is_momentum_aligned(self) -> bool:
        """Check if price and EMA momentum are well aligned"""
        return self._momentum_alignment > 0.7

    def get_ema_info(self) -> Dict[str, Any]:
        """Get comprehensive EMA information"""
        return {
            "ema_value": self.ema,
            "trend_analysis": {
                "direction": self._trend_direction,
                "strength": self._trend_strength,
                "slope": self._slope
            },
            "responsiveness_analysis": {
                "responsiveness": self._responsiveness,
                "momentum_alignment": self._momentum_alignment
            },
            "distance_analysis": {
                "price_ema_distance": self._price_ema_distance,
                "distance_trend": self._distance_trend
            },
            "level_analysis": {
                "dynamic_support": self._dynamic_support,
                "dynamic_resistance": self._dynamic_resistance,
                "level_strength": self._level_strength
            },
            "metadata": {
                "period": self.ema_config.ema_period,
                "alpha": self._alpha,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._prices.clear()
        self._ema_values.clear()
        self._current_ema = None
        self._trend_direction = 0
        self._trend_strength = 0.0
        self._slope = 0.0
        self._responsiveness = 0.0
        self._momentum_alignment = 0.0
        self._dynamic_support = 0.0
        self._dynamic_resistance = 0.0
        self._level_strength = 0.0
        self._price_ema_distance = 0.0
        self._distance_trend = "neutral"