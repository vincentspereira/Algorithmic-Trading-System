"""
Institutional-Grade Augmented Double Exponential Moving Average (DEMA) Indicator

This module implements an enhanced DEMA indicator with institutional-grade features:
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
class AugmentedDEMAConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented DEMA"""
    dema_period: int = 20
    responsiveness_threshold: float = 0.001  # Minimum change for responsiveness detection


class AugmentedDEMA(AugmentedIndicator):
    """
    Institutional-grade Augmented DEMA indicator implementing 5-pillar architecture.

    Features:
    - Double exponential smoothing for reduced lag
    - Lag reduction analysis and effectiveness scoring
    - Trend direction and strength analysis
    - Market regime adaptation
    - Multi-timeframe convergence
    - Smart money flow analysis
    - Automated risk management
    """

    def __init__(self, config: AugmentedDEMAConfig = None):
        if config is None:
            config = AugmentedDEMAConfig()

        super().__init__(config)
        self.dema_config = config

        # DEMA specific state
        self._prices = deque(maxlen=self.config.buffer_size)
        self._ema1_values = deque(maxlen=self.config.buffer_size)  # First EMA
        self._ema2_values = deque(maxlen=self.config.buffer_size)  # Second EMA
        self._dema_values = deque(maxlen=self.config.buffer_size)
        self._current_dema = None

        # Lag reduction analysis
        self._lag_reduction = 0.0
        self._effectiveness_score = 0.0
        self._smoothing_quality = 0.0

        # Trend analysis
        self._trend_direction = 0  # -1, 0, 1 for down, sideways, up
        self._trend_strength = 0.0
        self._slope = 0.0

        # Responsiveness analysis
        self._responsiveness = 0.0
        self._noise_reduction = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if DEMA is ready to provide signals"""
        return len(self._dema_values) > 0 and self._current_dema is not None

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update DEMA analysis

        Args:
            bar (Bar): New bar data
        """
        # Extract price
        if hasattr(bar, 'close'):
            price = bar.close
        else:
            price = bar.get('close', bar.get('price', 0.0))

        # Update DEMA calculation
        self._update_dema(price)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_dema(self, price: float):
        """Update the core DEMA calculation with institutional enhancements"""
        self._prices.append(price)

        if len(self._prices) >= self.dema_config.dema_period:
            # Calculate first EMA
            alpha = 2.0 / (self.dema_config.dema_period + 1)

            if not self._ema1_values:
                ema1 = price
            else:
                ema1 = alpha * price + (1 - alpha) * self._ema1_values[-1]

            self._ema1_values.append(ema1)

            # Calculate second EMA of the first EMA
            if len(self._ema1_values) >= self.dema_config.dema_period:
                if not self._ema2_values:
                    ema2 = ema1
                else:
                    ema2 = alpha * ema1 + (1 - alpha) * self._ema2_values[-1]

                self._ema2_values.append(ema2)

                # Calculate DEMA: 2 * EMA1 - EMA2
                self._current_dema = 2 * ema1 - ema2
                self._dema_values.append(self._current_dema)

                # Analyze DEMA characteristics
                self._analyze_dema_characteristics(price)

    def _analyze_dema_characteristics(self, current_price: float):
        """Analyze DEMA characteristics for institutional insights"""
        if not self.is_ready or len(self._dema_values) < 3:
            return

        # Calculate trend direction and strength
        recent_demas = list(self._dema_values)[-3:]
        self._slope = (recent_demas[-1] - recent_demas[0]) / 3

        # Determine trend direction
        if self._slope > self.dema_config.responsiveness_threshold:
            self._trend_direction = 1  # Uptrend
            self._trend_strength = min(1.0, self._slope / (recent_demas[0] * 0.01))
        elif self._slope < -self.dema_config.responsiveness_threshold:
            self._trend_direction = -1  # Downtrend
            self._trend_strength = min(1.0, abs(self._slope) / (recent_demas[0] * 0.01))
        else:
            self._trend_direction = 0  # Sideways
            self._trend_strength = 0.0

        # Calculate lag reduction effectiveness
        if len(self._prices) >= self.dema_config.dema_period + 5:
            # Compare DEMA responsiveness to SMA
            recent_prices = list(self._prices)[-5:]
            sma_value = sum(recent_prices) / len(recent_prices)

            price_change = abs(recent_prices[-1] - recent_prices[0])
            sma_change = abs(sma_value - (sum(recent_prices[:-1]) / (len(recent_prices) - 1)))
            dema_change = abs(recent_demas[-1] - recent_demas[0])

            if sma_change > 0:
                self._lag_reduction = (sma_change - dema_change) / sma_change
                self._lag_reduction = max(0.0, min(1.0, self._lag_reduction))

        # Calculate responsiveness
        if len(self._prices) >= 3:
            recent_prices = list(self._prices)[-3:]
            price_volatility = abs(recent_prices[-1] - recent_prices[0]) / recent_prices[0]

            if price_volatility > 0:
                dema_volatility = abs(recent_demas[-1] - recent_demas[0]) / recent_demas[0]
                self._responsiveness = min(1.0, dema_volatility / price_volatility)

        # Calculate smoothing quality (noise reduction)
        if len(self._prices) >= 10:
            price_std = statistics.stdev(list(self._prices)[-10:]) if len(self._prices) >= 10 else 0
            dema_std = statistics.stdev(list(self._dema_values)[-10:]) if len(self._dema_values) >= 10 else 0

            if price_std > 0:
                self._noise_reduction = 1.0 - (dema_std / price_std)
                self._noise_reduction = max(0.0, min(1.0, self._noise_reduction))

        # Calculate overall effectiveness score
        self._effectiveness_score = (
            self._lag_reduction * 0.4 +
            self._responsiveness * 0.3 +
            self._noise_reduction * 0.3
        )

        # Calculate smoothing quality
        self._smoothing_quality = (
            self._noise_reduction * 0.6 +
            (1.0 - abs(self._slope) * 10) * 0.4  # Penalize excessive volatility
        )

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade DEMA analysis"""
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

        dema_value = self._current_dema

        # Determine signal type based on DEMA analysis
        signal_type = self._determine_dema_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'trend_strength': self._trend_strength,
            'lag_reduction': self._lag_reduction,
            'responsiveness': self._responsiveness,
            'effectiveness_score': self._effectiveness_score,
            'smoothing_quality': self._smoothing_quality
        }

        # Use DEMA value as primary raw value
        raw_value = dema_value

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._suggested_sl,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "DEMA",
                "dema_period": self.dema_config.dema_period,
                "trend_direction": self._trend_direction,
                "trend_strength": self._trend_strength,
                "slope": self._slope,
                "lag_reduction": self._lag_reduction,
                "responsiveness": self._responsiveness,
                "noise_reduction": self._noise_reduction,
                "effectiveness_score": self._effectiveness_score,
                "smoothing_quality": self._smoothing_quality,
                "ema1_value": self._ema1_values[-1] if self._ema1_values else 0.0,
                "ema2_value": self._ema2_values[-1] if self._ema2_values else 0.0,
                "is_ready": self.is_ready
            }
        )

    def _determine_dema_signal(self) -> SignalType:
        """Determine signal type based on DEMA analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong trend signals with high effectiveness
        if self._trend_strength > 0.7 and self._effectiveness_score > 0.7:
            if self._trend_direction == 1:
                return SignalType.BULLISH
            elif self._trend_direction == -1:
                return SignalType.BEARISH

        # Moderate trend signals with good responsiveness
        elif self._trend_strength > 0.4 and self._responsiveness > 0.6:
            if self._trend_direction == 1:
                return SignalType.BULLISH
            elif self._trend_direction == -1:
                return SignalType.BEARISH

        # High effectiveness signals
        elif self._effectiveness_score > 0.8 and abs(self._slope) > self.dema_config.responsiveness_threshold:
            if self._slope > 0:
                return SignalType.BULLISH
            else:
                return SignalType.BEARISH

        return SignalType.NEUTRAL

    @property
    def dema(self) -> float:
        """Get the current DEMA value"""
        return self._current_dema if self.is_ready else 0.0

    @property
    def ema1(self) -> float:
        """Get the first EMA value"""
        return self._ema1_values[-1] if self._ema1_values else 0.0

    @property
    def ema2(self) -> float:
        """Get the second EMA value"""
        return self._ema2_values[-1] if self._ema2_values else 0.0

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
        """Get the current DEMA slope"""
        return self._slope

    @property
    def lag_reduction(self) -> float:
        """Get the lag reduction effectiveness (0-1)"""
        return self._lag_reduction

    @property
    def responsiveness(self) -> float:
        """Get the current responsiveness (0-1)"""
        return self._responsiveness

    @property
    def noise_reduction(self) -> float:
        """Get the noise reduction effectiveness (0-1)"""
        return self._noise_reduction

    @property
    def effectiveness_score(self) -> float:
        """Get the overall effectiveness score (0-1)"""
        return self._effectiveness_score

    @property
    def smoothing_quality(self) -> float:
        """Get the smoothing quality score (0-1)"""
        return self._smoothing_quality

    def is_above_dema(self, current_price: float) -> bool:
        """Check if price is above DEMA"""
        if not self.is_ready:
            return False
        return current_price > self.dema

    def is_below_dema(self, current_price: float) -> bool:
        """Check if price is below DEMA"""
        if not self.is_ready:
            return False
        return current_price < self.dema

    def is_effective(self) -> bool:
        """Check if DEMA is highly effective"""
        return self._effectiveness_score > 0.7

    def is_responsive(self) -> bool:
        """Check if DEMA is highly responsive"""
        return self._responsiveness > 0.7

    def get_dema_info(self) -> Dict[str, Any]:
        """Get comprehensive DEMA information"""
        return {
            "dema_value": self.dema,
            "trend_analysis": {
                "direction": self._trend_direction,
                "strength": self._trend_strength,
                "slope": self._slope
            },
            "effectiveness_analysis": {
                "lag_reduction": self._lag_reduction,
                "responsiveness": self._responsiveness,
                "noise_reduction": self._noise_reduction,
                "effectiveness_score": self._effectiveness_score,
                "smoothing_quality": self._smoothing_quality
            },
            "component_analysis": {
                "ema1": self.ema1,
                "ema2": self.ema2
            },
            "metadata": {
                "period": self.dema_config.dema_period,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._prices.clear()
        self._ema1_values.clear()
        self._ema2_values.clear()
        self._dema_values.clear()
        self._current_dema = None
        self._lag_reduction = 0.0
        self._effectiveness_score = 0.0
        self._smoothing_quality = 0.0
        self._trend_direction = 0
        self._trend_strength = 0.0
        self._slope = 0.0
        self._responsiveness = 0.0
        self._noise_reduction = 0.0