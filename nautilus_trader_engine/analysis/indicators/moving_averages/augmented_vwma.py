"""
Institutional-Grade Augmented Volume Weighted Moving Average (VWMA) Indicator

This module implements an enhanced VWMA indicator with institutional-grade features:
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
class AugmentedVWMAConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented VWMA"""
    vwma_period: int = 20
    volume_sensitivity: float = 1.5  # Volume sensitivity multiplier
    institutional_volume_threshold: float = 1.2  # Threshold for institutional volume


class AugmentedVWMA(AugmentedIndicator):
    """
    Institutional-grade Augmented VWMA indicator implementing 5-pillar architecture.

    Features:
    - Volume-weighted trend direction and strength analysis
    - Institutional volume participation analysis
    - Smart money flow detection in VWMA
    - Market regime adaptation based on volume patterns
    - Multi-timeframe convergence
    - Automated risk management
    """

    def __init__(self, config: AugmentedVWMAConfig = None):
        if config is None:
            config = AugmentedVWMAConfig()

        super().__init__(config)
        self.vwma_config = config

        # VWMA specific state
        self._prices = deque(maxlen=self.vwma_config.vwma_period)
        self._volumes = deque(maxlen=self.vwma_config.vwma_period)
        self._vwma_values = deque(maxlen=self.config.buffer_size)
        self._current_vwma = None

        # Volume analysis
        self._volume_participation = 0.0
        self._institutional_volume_score = 0.0
        self._volume_trend = "neutral"  # "increasing", "decreasing", "neutral"

        # Trend analysis
        self._trend_direction = 0  # -1, 0, 1 for down, sideways, up
        self._trend_strength = 0.0
        self._slope = 0.0

        # Smart money analysis
        self._smart_money_alignment = 0.0
        self._volume_price_alignment = 0.0

        # Institutional activity
        self._high_volume_periods = []
        self._institutional_participation = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if VWMA is ready to provide signals"""
        return len(self._vwma_values) > 0 and self._current_vwma is not None

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update VWMA analysis

        Args:
            bar (Bar): New bar data
        """
        # Extract price and volume
        if hasattr(bar, 'close'):
            price = bar.close
        else:
            price = bar.get('close', bar.get('price', 0.0))

        volume = bar.volume * self.vwma_config.volume_sensitivity

        # Update VWMA calculation
        self._update_vwma(price, volume)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_vwma(self, price: float, volume: float):
        """Update the core VWMA calculation with institutional enhancements"""
        self._prices.append(price)
        self._volumes.append(volume)

        if len(self._prices) >= self.vwma_config.vwma_period:
            # Calculate VWMA
            price_volume_sum = sum(p * v for p, v in zip(self._prices, self._volumes))
            total_volume = sum(self._volumes)

            if total_volume > 0:
                self._current_vwma = price_volume_sum / total_volume
                self._vwma_values.append(self._current_vwma)

                # Analyze institutional characteristics
                self._analyze_institutional_characteristics(price, volume)

    def _analyze_institutional_characteristics(self, current_price: float, current_volume: float):
        """Analyze institutional characteristics of VWMA"""
        if not self.is_ready:
            return

        # Calculate volume participation score
        avg_volume = sum(self._volumes) / len(self._volumes)
        if avg_volume > 0:
            self._volume_participation = current_volume / avg_volume

            # Institutional volume score (high volume periods)
            if self._volume_participation >= self.vwma_config.institutional_volume_threshold:
                self._institutional_volume_score = min(1.0, self._volume_participation / 2.0)
                self._high_volume_periods.append(current_price)
                # Keep only recent high volume periods
                if len(self._high_volume_periods) > 10:
                    self._high_volume_periods.pop(0)
            else:
                self._institutional_volume_score = 0.0

        # Analyze volume trend
        if len(self._volumes) >= 5:
            recent_volumes = list(self._volumes)[-5:]
            volume_slope = (recent_volumes[-1] - recent_volumes[0]) / 5

            if volume_slope > 0:
                self._volume_trend = "increasing"
            elif volume_slope < 0:
                self._volume_trend = "decreasing"
            else:
                self._volume_trend = "neutral"

        # Calculate trend direction and strength
        if len(self._vwma_values) >= 3:
            recent_vwmas = list(self._vwma_values)[-3:]
            self._slope = (recent_vwmas[-1] - recent_vwmas[0]) / 3

            # Determine trend direction
            if self._slope > 0.001:  # 0.1% slope threshold
                self._trend_direction = 1  # Uptrend
                self._trend_strength = min(1.0, self._slope / (recent_vwmas[0] * 0.01))
            elif self._slope < -0.001:
                self._trend_direction = -1  # Downtrend
                self._trend_strength = min(1.0, abs(self._slope) / (recent_vwmas[0] * 0.01))
            else:
                self._trend_direction = 0  # Sideways
                self._trend_strength = 0.0

        # Calculate smart money alignment
        self._calculate_smart_money_alignment(current_price, current_volume)

        # Calculate institutional participation
        self._calculate_institutional_participation()

    def _calculate_smart_money_alignment(self, current_price: float, current_volume: float):
        """Calculate alignment between price movement and volume (smart money indicator)"""
        if not self.is_ready or len(self._prices) < 2:
            return

        # Price direction
        price_change = current_price - self._prices[-2] if len(self._prices) >= 2 else 0
        price_direction = 1 if price_change > 0 else -1 if price_change < 0 else 0

        # Volume confirmation
        volume_direction = 1 if current_volume > sum(list(self._volumes)[-3:-1]) / 2 else -1

        # Alignment score
        if price_direction == volume_direction and price_direction != 0:
            self._smart_money_alignment = 0.8  # Strong alignment
        elif price_direction == volume_direction:
            self._smart_money_alignment = 0.5  # Neutral alignment
        else:
            self._smart_money_alignment = 0.2  # Poor alignment

        # Volume-price alignment
        if abs(price_change) > 0.001:  # Significant price change
            volume_intensity = current_volume / (sum(list(self._volumes)[-5:]) / 5) if len(self._volumes) >= 5 else 1.0
            self._volume_price_alignment = min(1.0, volume_intensity * abs(price_change) * 1000)

    def _calculate_institutional_participation(self):
        """Calculate level of institutional participation based on volume patterns"""
        if not self.is_ready:
            return

        # Analyze volume distribution
        volumes = list(self._volumes)
        if volumes:
            avg_volume = sum(volumes) / len(volumes)
            high_volume_count = sum(1 for v in volumes if v > avg_volume * 1.5)
            self._institutional_participation = high_volume_count / len(volumes)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade VWMA analysis"""
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

        vwma_value = self._current_vwma

        # Determine signal type based on VWMA analysis
        signal_type = self._determine_vwma_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'trend_strength': self._trend_strength,
            'volume_participation': min(1.0, self._volume_participation),
            'institutional_volume_score': self._institutional_volume_score,
            'smart_money_alignment': self._smart_money_alignment,
            'institutional_participation': self._institutional_participation
        }

        # Use VWMA value as primary raw value
        raw_value = vwma_value

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._suggested_sl,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "VWMA",
                "vwma_period": self.vwma_config.vwma_period,
                "volume_sensitivity": self.vwma_config.volume_sensitivity,
                "trend_direction": self._trend_direction,
                "trend_strength": self._trend_strength,
                "slope": self._slope,
                "volume_participation": self._volume_participation,
                "volume_trend": self._volume_trend,
                "institutional_volume_score": self._institutional_volume_score,
                "smart_money_alignment": self._smart_money_alignment,
                "volume_price_alignment": self._volume_price_alignment,
                "institutional_participation": self._institutional_participation,
                "high_volume_periods_count": len(self._high_volume_periods),
                "is_ready": self.is_ready
            }
        )

    def _determine_vwma_signal(self) -> SignalType:
        """Determine signal type based on VWMA analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong institutional signals
        if (self._trend_strength > 0.7 and
            self._institutional_volume_score > 0.6 and
            self._smart_money_alignment > 0.7):
            if self._trend_direction == 1:
                return SignalType.STRONG_BULLISH
            elif self._trend_direction == -1:
                return SignalType.STRONG_BEARISH

        # Moderate trend signals with volume confirmation
        elif (self._trend_strength > 0.4 and
              self._volume_participation > 1.2):
            if self._trend_direction == 1:
                return SignalType.BULLISH
            elif self._trend_direction == -1:
                return SignalType.BEARISH

        # High volume participation signals
        elif self._volume_participation > 1.5 and self._institutional_participation > 0.3:
            if self._trend_direction == 1:
                return SignalType.BULLISH
            elif self._trend_direction == -1:
                return SignalType.BEARISH

        return SignalType.NEUTRAL

    @property
    def vwma(self) -> float:
        """Get the current VWMA value"""
        return self._current_vwma if self.is_ready else 0.0

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
        """Get the current VWMA slope"""
        return self._slope

    @property
    def volume_participation(self) -> float:
        """Get the current volume participation ratio"""
        return self._volume_participation

    @property
    def volume_trend(self) -> str:
        """Get the current volume trend"""
        return self._volume_trend

    @property
    def institutional_volume_score(self) -> float:
        """Get the institutional volume score (0-1)"""
        return self._institutional_volume_score

    @property
    def smart_money_alignment(self) -> float:
        """Get the smart money alignment score (0-1)"""
        return self._smart_money_alignment

    @property
    def volume_price_alignment(self) -> float:
        """Get the volume-price alignment score (0-1)"""
        return self._volume_price_alignment

    @property
    def institutional_participation(self) -> float:
        """Get the institutional participation score (0-1)"""
        return self._institutional_participation

    @property
    def high_volume_periods(self) -> list:
        """Get the list of high volume periods"""
        return self._high_volume_periods.copy()

    def is_above_vwma(self, current_price: float) -> bool:
        """Check if price is above VWMA"""
        if not self.is_ready:
            return False
        return current_price > self.vwma

    def is_below_vwma(self, current_price: float) -> bool:
        """Check if price is below VWMA"""
        if not self.is_ready:
            return False
        return current_price < self.vwma

    def is_institutional_volume(self) -> bool:
        """Check if current volume represents institutional participation"""
        return self._institutional_volume_score > 0.5

    def is_smart_money_aligned(self) -> bool:
        """Check if smart money is aligned with price movement"""
        return self._smart_money_alignment > 0.7

    def get_vwma_info(self) -> Dict[str, Any]:
        """Get comprehensive VWMA information"""
        return {
            "vwma_value": self.vwma,
            "trend_analysis": {
                "direction": self._trend_direction,
                "strength": self._trend_strength,
                "slope": self._slope
            },
            "volume_analysis": {
                "participation": self._volume_participation,
                "trend": self._volume_trend,
                "institutional_score": self._institutional_volume_score
            },
            "smart_money_analysis": {
                "alignment": self._smart_money_alignment,
                "volume_price_alignment": self._volume_price_alignment,
                "institutional_participation": self._institutional_participation
            },
            "metadata": {
                "period": self.vwma_config.vwma_period,
                "volume_sensitivity": self.vwma_config.volume_sensitivity,
                "high_volume_periods_count": len(self._high_volume_periods),
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._prices.clear()
        self._volumes.clear()
        self._vwma_values.clear()
        self._current_vwma = None
        self._volume_participation = 0.0
        self._institutional_volume_score = 0.0
        self._volume_trend = "neutral"
        self._trend_direction = 0
        self._trend_strength = 0.0
        self._slope = 0.0
        self._smart_money_alignment = 0.0
        self._volume_price_alignment = 0.0
        self._high_volume_periods.clear()
        self._institutional_participation = 0.0