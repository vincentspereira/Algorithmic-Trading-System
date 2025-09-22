"""
Institutional-Grade Augmented Kaufman Adaptive Moving Average (KAMA) Indicator

This module implements an enhanced KAMA indicator with institutional-grade features:
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
class AugmentedKAMAConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented KAMA"""
    kama_period: int = 30
    fast_ema_period: int = 2
    slow_ema_period: int = 30
    responsiveness_threshold: float = 0.001  # Minimum change for responsiveness detection


class AugmentedKAMA(AugmentedIndicator):
    """
    Institutional-grade Augmented KAMA indicator implementing 5-pillar architecture.

    Features:
    - Adaptive smoothing based on market volatility
    - Efficiency ratio analysis for market noise assessment
    - Trend direction and strength analysis
    - Market regime adaptation
    - Multi-timeframe convergence
    - Smart money flow analysis
    - Automated risk management
    """

    def __init__(self, config: AugmentedKAMAConfig = None):
        if config is None:
            config = AugmentedKAMAConfig()

        super().__init__(config)
        self.kama_config = config

        # KAMA specific state
        self._prices = deque(maxlen=self.config.buffer_size)
        self._kama_values = deque(maxlen=self.config.buffer_size)
        self._current_kama = None

        # Adaptive smoothing components
        self._efficiency_ratio = 0.0
        self._smoothing_constant = 0.0
        self._volatility_measure = 0.0

        # Market noise analysis
        self._market_noise = 0.0
        self._trend_noise_ratio = 0.0
        self._adaptation_effectiveness = 0.0

        # Trend analysis
        self._trend_direction = 0  # -1, 0, 1 for down, sideways, up
        self._trend_strength = 0.0
        self._slope = 0.0

        # Adaptive behavior
        self._adaptation_speed = 0.0
        self._market_regime = "neutral"  # "trending", "ranging", "neutral"

    @property
    def is_ready(self) -> bool:
        """Return True if KAMA is ready to provide signals"""
        return len(self._kama_values) > 0 and self._current_kama is not None

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update KAMA analysis

        Args:
            bar (Bar): New bar data
        """
        # Extract price
        if hasattr(bar, 'close'):
            price = bar.close
        else:
            price = bar.get('close', bar.get('price', 0.0))

        # Update KAMA calculation
        self._update_kama(price)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_kama(self, price: float):
        """Update the core KAMA calculation with institutional enhancements"""
        self._prices.append(price)

        period = self.kama_config.kama_period
        if len(self._prices) >= period + 1:
            # Calculate Efficiency Ratio (ER)
            self._calculate_efficiency_ratio()

            # Calculate smoothing constant based on ER
            self._calculate_smoothing_constant()

            # Calculate KAMA
            if not self._kama_values:
                self._current_kama = price
            else:
                self._current_kama = (self._smoothing_constant * price +
                                    (1 - self._smoothing_constant) * self._current_kama)

            self._kama_values.append(self._current_kama)

            # Analyze KAMA characteristics
            self._analyze_kama_characteristics(price)

    def _calculate_efficiency_ratio(self):
        """Calculate the Efficiency Ratio for market noise assessment"""
        if len(self._prices) < self.kama_config.kama_period + 1:
            return

        # Calculate directional movement
        directional_change = abs(self._prices[-1] - self._prices[-self.kama_config.kama_period - 1])

        # Calculate total volatility
        total_volatility = 0.0
        for i in range(1, self.kama_config.kama_period + 1):
            total_volatility += abs(self._prices[-i] - self._prices[-i - 1])

        # Efficiency Ratio = Directional Change / Total Volatility
        if total_volatility > 0:
            self._efficiency_ratio = directional_change / total_volatility
            self._efficiency_ratio = min(1.0, self._efficiency_ratio)
        else:
            self._efficiency_ratio = 0.0

        # Market noise is the inverse of efficiency
        self._market_noise = 1.0 - self._efficiency_ratio

    def _calculate_smoothing_constant(self):
        """Calculate the adaptive smoothing constant based on efficiency ratio"""
        # KAMA smoothing constant formula
        # SC = [ER * (2/(fast+1) - 2/(slow+1)) + 2/(slow+1)]^2

        fast_alpha = 2.0 / (self.kama_config.fast_ema_period + 1)
        slow_alpha = 2.0 / (self.kama_config.slow_ema_period + 1)

        sc = self._efficiency_ratio * (fast_alpha - slow_alpha) + slow_alpha
        self._smoothing_constant = sc * sc  # Square it as per KAMA formula

        # Calculate adaptation speed
        self._adaptation_speed = self._smoothing_constant

    def _analyze_kama_characteristics(self, current_price: float):
        """Analyze KAMA characteristics for institutional insights"""
        if not self.is_ready or len(self._kama_values) < 3:
            return

        # Calculate trend direction and strength
        recent_kamas = list(self._kama_values)[-3:]
        self._slope = (recent_kamas[-1] - recent_kamas[0]) / 3

        # Determine trend direction
        if self._slope > self.kama_config.responsiveness_threshold:
            self._trend_direction = 1  # Uptrend
            self._trend_strength = min(1.0, self._slope / (recent_kamas[0] * 0.01))
        elif self._slope < -self.kama_config.responsiveness_threshold:
            self._trend_direction = -1  # Downtrend
            self._trend_strength = min(1.0, abs(self._slope) / (recent_kamas[0] * 0.01))
        else:
            self._trend_direction = 0  # Sideways
            self._trend_strength = 0.0

        # Determine market regime based on efficiency ratio
        if self._efficiency_ratio > 0.6:
            self._market_regime = "trending"
        elif self._efficiency_ratio < 0.3:
            self._market_regime = "ranging"
        else:
            self._market_regime = "neutral"

        # Calculate trend-to-noise ratio
        if self._market_noise > 0:
            self._trend_noise_ratio = self._efficiency_ratio / self._market_noise
        else:
            self._trend_noise_ratio = 1.0

        # Calculate adaptation effectiveness
        self._adaptation_effectiveness = (
            self._efficiency_ratio * 0.4 +
            self._adaptation_speed * 0.3 +
            self._trend_strength * 0.3
        )

        # Calculate volatility measure
        if len(self._prices) >= 10:
            price_std = statistics.stdev(list(self._prices)[-10:]) if len(self._prices) >= 10 else 0
            self._volatility_measure = price_std / (sum(self._prices[-10:]) / 10) if self._prices else 0

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade KAMA analysis"""
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

        kama_value = self._current_kama

        # Determine signal type based on KAMA analysis
        signal_type = self._determine_kama_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'trend_strength': self._trend_strength,
            'efficiency_ratio': self._efficiency_ratio,
            'adaptation_effectiveness': self._adaptation_effectiveness,
            'trend_noise_ratio': self._trend_noise_ratio,
            'market_noise': self._market_noise
        }

        # Use KAMA value as primary raw value
        raw_value = kama_value

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._suggested_sl,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "KAMA",
                "kama_period": self.kama_config.kama_period,
                "fast_ema_period": self.kama_config.fast_ema_period,
                "slow_ema_period": self.kama_config.slow_ema_period,
                "trend_direction": self._trend_direction,
                "trend_strength": self._trend_strength,
                "slope": self._slope,
                "efficiency_ratio": self._efficiency_ratio,
                "market_noise": self._market_noise,
                "smoothing_constant": self._smoothing_constant,
                "adaptation_speed": self._adaptation_speed,
                "adaptation_effectiveness": self._adaptation_effectiveness,
                "trend_noise_ratio": self._trend_noise_ratio,
                "market_regime": self._market_regime,
                "volatility_measure": self._volatility_measure,
                "is_ready": self.is_ready
            }
        )

    def _determine_kama_signal(self) -> SignalType:
        """Determine signal type based on KAMA analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong trending signals with high efficiency
        if (self._trend_strength > 0.7 and
            self._efficiency_ratio > 0.7 and
            self._market_regime == "trending"):
            if self._trend_direction == 1:
                return SignalType.STRONG_BULLISH
            elif self._trend_direction == -1:
                return SignalType.STRONG_BEARISH

        # Moderate trend signals with good adaptation
        elif (self._trend_strength > 0.4 and
              self._adaptation_effectiveness > 0.6):
            if self._trend_direction == 1:
                return SignalType.BULLISH
            elif self._trend_direction == -1:
                return SignalType.BEARISH

        # High efficiency signals
        elif (self._efficiency_ratio > 0.8 and
              abs(self._slope) > self.kama_config.responsiveness_threshold):
            if self._slope > 0:
                return SignalType.BULLISH
            else:
                return SignalType.BEARISH

        return SignalType.NEUTRAL

    @property
    def kama(self) -> float:
        """Get the current KAMA value"""
        return self._current_kama if self.is_ready else 0.0

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
        """Get the current KAMA slope"""
        return self._slope

    @property
    def efficiency_ratio(self) -> float:
        """Get the current efficiency ratio (0-1)"""
        return self._efficiency_ratio

    @property
    def market_noise(self) -> float:
        """Get the current market noise level (0-1)"""
        return self._market_noise

    @property
    def smoothing_constant(self) -> float:
        """Get the current smoothing constant"""
        return self._smoothing_constant

    @property
    def adaptation_speed(self) -> float:
        """Get the current adaptation speed (0-1)"""
        return self._adaptation_speed

    @property
    def adaptation_effectiveness(self) -> float:
        """Get the adaptation effectiveness (0-1)"""
        return self._adaptation_effectiveness

    @property
    def trend_noise_ratio(self) -> float:
        """Get the trend-to-noise ratio"""
        return self._trend_noise_ratio

    @property
    def market_regime(self) -> str:
        """Get the current market regime"""
        return self._market_regime

    @property
    def volatility_measure(self) -> float:
        """Get the current volatility measure"""
        return self._volatility_measure

    def is_above_kama(self, current_price: float) -> bool:
        """Check if price is above KAMA"""
        if not self.is_ready:
            return False
        return current_price > self.kama

    def is_below_kama(self, current_price: float) -> bool:
        """Check if price is below KAMA"""
        if not self.is_ready:
            return False
        return current_price < self.kama

    def is_highly_efficient(self) -> bool:
        """Check if KAMA is highly efficient (low noise)"""
        return self._efficiency_ratio > 0.7

    def is_well_adapted(self) -> bool:
        """Check if KAMA adaptation is effective"""
        return self._adaptation_effectiveness > 0.7

    def is_trending_market(self) -> bool:
        """Check if market is in trending regime"""
        return self._market_regime == "trending"

    def get_kama_info(self) -> Dict[str, Any]:
        """Get comprehensive KAMA information"""
        return {
            "kama_value": self.kama,
            "trend_analysis": {
                "direction": self._trend_direction,
                "strength": self._trend_strength,
                "slope": self._slope
            },
            "efficiency_analysis": {
                "efficiency_ratio": self._efficiency_ratio,
                "market_noise": self._market_noise,
                "trend_noise_ratio": self._trend_noise_ratio
            },
            "adaptation_analysis": {
                "smoothing_constant": self._smoothing_constant,
                "adaptation_speed": self._adaptation_speed,
                "adaptation_effectiveness": self._adaptation_effectiveness,
                "market_regime": self._market_regime
            },
            "volatility_analysis": {
                "volatility_measure": self._volatility_measure
            },
            "metadata": {
                "period": self.kama_config.kama_period,
                "fast_period": self.kama_config.fast_ema_period,
                "slow_period": self.kama_config.slow_ema_period,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._prices.clear()
        self._kama_values.clear()
        self._current_kama = None
        self._efficiency_ratio = 0.0
        self._smoothing_constant = 0.0
        self._volatility_measure = 0.0
        self._market_noise = 0.0
        self._trend_noise_ratio = 0.0
        self._adaptation_effectiveness = 0.0
        self._trend_direction = 0
        self._trend_strength = 0.0
        self._slope = 0.0
        self._adaptation_speed = 0.0
        self._market_regime = "neutral"