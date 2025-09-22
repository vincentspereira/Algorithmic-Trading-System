"""
Institutional-Grade Augmented Hull Moving Average (HMA) Indicator

This module implements an enhanced HMA indicator with institutional-grade features:
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
class AugmentedHMAConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented HMA"""
    hma_period: int = 20
    responsiveness_threshold: float = 0.001  # Minimum change for responsiveness detection


class AugmentedHMA(AugmentedIndicator):
    """
    Institutional-grade Augmented HMA indicator implementing 5-pillar architecture.

    Features:
    - Weighted calculation for optimal smoothness and responsiveness
    - Hull transformation analysis for effectiveness scoring
    - Trend direction and strength analysis
    - Market regime adaptation
    - Multi-timeframe convergence
    - Smart money flow analysis
    - Automated risk management
    """

    def __init__(self, config: AugmentedHMAConfig = None):
        if config is None:
            config = AugmentedHMAConfig()

        super().__init__(config)
        self.hma_config = config

        # HMA specific state
        self._prices = deque(maxlen=self.config.buffer_size)
        self._hma_values = deque(maxlen=self.config.buffer_size)
        self._current_hma = None

        # HMA components
        self._fast_ma_values = deque(maxlen=self.config.buffer_size)
        self._slow_ma_values = deque(maxlen=self.config.buffer_size)
        self._diff_ma_values = deque(maxlen=self.config.buffer_size)

        # Hull transformation analysis
        self._hull_effectiveness = 0.0
        self._smoothing_score = 0.0
        self._responsiveness_score = 0.0

        # Trend analysis
        self._trend_direction = 0  # -1, 0, 1 for down, sideways, up
        self._trend_strength = 0.0
        self._slope = 0.0

        # Quality metrics
        self._signal_quality = 0.0
        self._noise_reduction = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if HMA is ready to provide signals"""
        return len(self._hma_values) > 0 and self._current_hma is not None

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update HMA analysis

        Args:
            bar (Bar): New bar data
        """
        # Extract price
        if hasattr(bar, 'close'):
            price = bar.close
        else:
            price = bar.get('close', bar.get('price', 0.0))

        # Update HMA calculation
        self._update_hma(price)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_hma(self, price: float):
        """Update the core HMA calculation with institutional enhancements"""
        self._prices.append(price)

        period = self.hma_config.hma_period
        if len(self._prices) >= period * 2:  # Need 2x period for HMA calculation
            # Calculate fast MA (period/2)
            fast_period = period // 2
            if len(self._prices) >= fast_period:
                fast_ma = sum(list(self._prices)[-fast_period:]) / fast_period
                self._fast_ma_values.append(fast_ma)

            # Calculate slow MA (period)
            if len(self._prices) >= period:
                slow_ma = sum(list(self._prices)[-period:]) / period
                self._slow_ma_values.append(slow_ma)

            # Calculate difference and its MA
            if self._fast_ma_values and self._slow_ma_values:
                diff = 2 * self._fast_ma_values[-1] - self._slow_ma_values[-1]
                self._diff_ma_values.append(diff)

                # Calculate MA of the difference
                diff_period = int(period ** 0.5)  # Square root of period
                if len(self._diff_ma_values) >= diff_period:
                    diff_ma = sum(list(self._diff_ma_values)[-diff_period:]) / diff_period

                    # Final HMA calculation
                    self._current_hma = diff_ma
                    self._hma_values.append(self._current_hma)

                    # Analyze HMA characteristics
                    self._analyze_hma_characteristics(price)

    def _analyze_hma_characteristics(self, current_price: float):
        """Analyze HMA characteristics for institutional insights"""
        if not self.is_ready or len(self._hma_values) < 3:
            return

        # Calculate trend direction and strength
        recent_hmas = list(self._hma_values)[-3:]
        self._slope = (recent_hmas[-1] - recent_hmas[0]) / 3

        # Determine trend direction
        if self._slope > self.hma_config.responsiveness_threshold:
            self._trend_direction = 1  # Uptrend
            self._trend_strength = min(1.0, self._slope / (recent_hmas[0] * 0.01))
        elif self._slope < -self.hma_config.responsiveness_threshold:
            self._trend_direction = -1  # Downtrend
            self._trend_strength = min(1.0, abs(self._slope) / (recent_hmas[0] * 0.01))
        else:
            self._trend_direction = 0  # Sideways
            self._trend_strength = 0.0

        # Calculate Hull transformation effectiveness
        if len(self._prices) >= 10:
            # Compare HMA smoothness vs raw price volatility
            price_std = statistics.stdev(list(self._prices)[-10:]) if len(self._prices) >= 10 else 0
            hma_std = statistics.stdev(list(self._hma_values)[-10:]) if len(self._hma_values) >= 10 else 0

            if price_std > 0:
                self._noise_reduction = 1.0 - (hma_std / price_std)
                self._noise_reduction = max(0.0, min(1.0, self._noise_reduction))

        # Calculate responsiveness (how well HMA tracks price changes)
        if len(self._prices) >= 5:
            recent_prices = list(self._prices)[-5:]
            recent_hmas = list(self._hma_values)[-5:]

            price_change = abs(recent_prices[-1] - recent_prices[0])
            hma_change = abs(recent_hmas[-1] - recent_hmas[0])

            if price_change > 0:
                self._responsiveness_score = min(1.0, hma_change / price_change)

        # Calculate overall Hull effectiveness
        self._hull_effectiveness = (
            self._noise_reduction * 0.5 +
            self._responsiveness_score * 0.3 +
            (1.0 - abs(self._slope) * 5) * 0.2  # Smoothness bonus
        )

        # Calculate smoothing quality
        self._smoothing_score = (
            self._noise_reduction * 0.7 +
            (1.0 - abs(self._slope) * 10) * 0.3
        )

        # Calculate signal quality
        self._signal_quality = (
            self._hull_effectiveness * 0.6 +
            self._trend_strength * 0.4
        )

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade HMA analysis"""
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

        hma_value = self._current_hma

        # Determine signal type based on HMA analysis
        signal_type = self._determine_hma_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'trend_strength': self._trend_strength,
            'hull_effectiveness': self._hull_effectiveness,
            'smoothing_score': self._smoothing_score,
            'responsiveness_score': self._responsiveness_score,
            'signal_quality': self._signal_quality
        }

        # Use HMA value as primary raw value
        raw_value = hma_value

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._suggested_sl,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "HMA",
                "hma_period": self.hma_config.hma_period,
                "trend_direction": self._trend_direction,
                "trend_strength": self._trend_strength,
                "slope": self._slope,
                "hull_effectiveness": self._hull_effectiveness,
                "smoothing_score": self._smoothing_score,
                "responsiveness_score": self._responsiveness_score,
                "noise_reduction": self._noise_reduction,
                "signal_quality": self._signal_quality,
                "fast_ma": self._fast_ma_values[-1] if self._fast_ma_values else 0.0,
                "slow_ma": self._slow_ma_values[-1] if self._slow_ma_values else 0.0,
                "diff_ma": self._diff_ma_values[-1] if self._diff_ma_values else 0.0,
                "is_ready": self.is_ready
            }
        )

    def _determine_hma_signal(self) -> SignalType:
        """Determine signal type based on HMA analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong trend signals with high Hull effectiveness
        if self._trend_strength > 0.7 and self._hull_effectiveness > 0.8:
            if self._trend_direction == 1:
                return SignalType.STRONG_BULLISH
            elif self._trend_direction == -1:
                return SignalType.STRONG_BEARISH

        # Moderate trend signals with good signal quality
        elif self._trend_strength > 0.4 and self._signal_quality > 0.7:
            if self._trend_direction == 1:
                return SignalType.BULLISH
            elif self._trend_direction == -1:
                return SignalType.BEARISH

        # High effectiveness signals
        elif self._hull_effectiveness > 0.85 and abs(self._slope) > self.hma_config.responsiveness_threshold:
            if self._slope > 0:
                return SignalType.BULLISH
            else:
                return SignalType.BEARISH

        return SignalType.NEUTRAL

    @property
    def hma(self) -> float:
        """Get the current HMA value"""
        return self._current_hma if self.is_ready else 0.0

    @property
    def fast_ma(self) -> float:
        """Get the fast MA component"""
        return self._fast_ma_values[-1] if self._fast_ma_values else 0.0

    @property
    def slow_ma(self) -> float:
        """Get the slow MA component"""
        return self._slow_ma_values[-1] if self._slow_ma_values else 0.0

    @property
    def diff_ma(self) -> float:
        """Get the difference MA component"""
        return self._diff_ma_values[-1] if self._diff_ma_values else 0.0

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
        """Get the current HMA slope"""
        return self._slope

    @property
    def hull_effectiveness(self) -> float:
        """Get the Hull transformation effectiveness (0-1)"""
        return self._hull_effectiveness

    @property
    def smoothing_score(self) -> float:
        """Get the smoothing quality score (0-1)"""
        return self._smoothing_score

    @property
    def responsiveness_score(self) -> float:
        """Get the responsiveness score (0-1)"""
        return self._responsiveness_score

    @property
    def signal_quality(self) -> float:
        """Get the overall signal quality (0-1)"""
        return self._signal_quality

    @property
    def noise_reduction(self) -> float:
        """Get the noise reduction effectiveness (0-1)"""
        return self._noise_reduction

    def is_above_hma(self, current_price: float) -> bool:
        """Check if price is above HMA"""
        if not self.is_ready:
            return False
        return current_price > self.hma

    def is_below_hma(self, current_price: float) -> bool:
        """Check if price is below HMA"""
        if not self.is_ready:
            return False
        return current_price < self.hma

    def is_hull_effective(self) -> bool:
        """Check if HMA Hull transformation is highly effective"""
        return self._hull_effectiveness > 0.8

    def is_high_quality_signal(self) -> bool:
        """Check if HMA signal quality is high"""
        return self._signal_quality > 0.8

    def get_hma_info(self) -> Dict[str, Any]:
        """Get comprehensive HMA information"""
        return {
            "hma_value": self.hma,
            "trend_analysis": {
                "direction": self._trend_direction,
                "strength": self._trend_strength,
                "slope": self._slope
            },
            "hull_analysis": {
                "effectiveness": self._hull_effectiveness,
                "smoothing_score": self._smoothing_score,
                "responsiveness_score": self._responsiveness_score,
                "noise_reduction": self._noise_reduction,
                "signal_quality": self._signal_quality
            },
            "component_analysis": {
                "fast_ma": self.fast_ma,
                "slow_ma": self.slow_ma,
                "diff_ma": self.diff_ma
            },
            "metadata": {
                "period": self.hma_config.hma_period,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._prices.clear()
        self._hma_values.clear()
        self._fast_ma_values.clear()
        self._slow_ma_values.clear()
        self._diff_ma_values.clear()
        self._current_hma = None
        self._hull_effectiveness = 0.0
        self._smoothing_score = 0.0
        self._responsiveness_score = 0.0
        self._trend_direction = 0
        self._trend_strength = 0.0
        self._slope = 0.0
        self._signal_quality = 0.0
        self._noise_reduction = 0.0