"""
Institutional-Grade Augmented Volume Confirmation Indicator

This module implements an enhanced Volume Confirmation indicator with institutional-grade features:
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
class AugmentedVolumeConfirmationConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Volume Confirmation"""
    volume_ma_period: int = 20
    confirmation_threshold: float = 1.2  # Volume must be 20% above average
    divergence_threshold: float = 0.7    # Divergence detection threshold


class AugmentedVolumeConfirmation(AugmentedIndicator):
    """
    Institutional-grade Augmented Volume Confirmation indicator implementing 5-pillar architecture.

    Features:
    - Volume confirmation analysis for price movements
    - Bullish/bearish confirmation detection
    - Volume divergence identification
    - Trend confirmation scoring
    - Market regime adaptation
    - Multi-timeframe convergence
    - Smart money flow analysis
    - Automated risk management
    """

    def __init__(self, config: AugmentedVolumeConfirmationConfig = None):
        if config is None:
            config = AugmentedVolumeConfirmationConfig()

        super().__init__(config)
        self.vc_config = config

        # Volume Confirmation specific state
        self._volume_values = deque(maxlen=self.config.buffer_size)
        self._price_changes = deque(maxlen=self.config.buffer_size)
        self._confirmation_scores = deque(maxlen=self.config.buffer_size)

        # Volume moving average
        self._volume_ma_values = deque(maxlen=self.config.buffer_size)
        self._volume_ma_sum = 0.0

        # Confirmation analysis
        self._bullish_confirmation = False
        self._bearish_confirmation = False
        self._confirmation_strength = 0.0

        # Divergence detection
        self._divergence_detected = False
        self._divergence_type = "none"  # "bullish", "bearish", "none"
        self._divergence_confidence = 0.0

        # Trend analysis
        self._volume_trend = "neutral"  # "increasing", "decreasing", "neutral"
        self._price_volume_alignment = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Volume Confirmation has sufficient data"""
        return len(self._volume_values) >= self.vc_config.volume_ma_period

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update Volume Confirmation analysis

        Args:
            bar (Bar): New bar data
        """
        # Update volume confirmation analysis
        self._update_volume_confirmation(bar)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_volume_confirmation(self, bar: Bar):
        """Update the core volume confirmation analysis"""
        # Calculate price change
        if hasattr(bar, 'close') and hasattr(bar, 'open'):
            price_change = bar.close - bar.open
        else:
            # Fallback for different bar formats
            price_change = bar.get('close', 0.0) - bar.get('open', 0.0)

        # Store volume and price change
        self._volume_values.append(bar.volume)
        self._price_changes.append(price_change)

        # Update volume moving average
        self._update_volume_moving_average(bar.volume)

        # Calculate confirmation score
        if self.is_ready:
            confirmation_score = self._calculate_confirmation_score(bar.volume, price_change)
            self._confirmation_scores.append(confirmation_score)

            # Analyze confirmation signals
            self._analyze_confirmation_signals(confirmation_score, price_change)

            # Detect volume divergences
            self._detect_volume_divergences()

            # Update volume trend
            self._update_volume_trend()

    def _update_volume_moving_average(self, current_volume: float):
        """Update volume moving average calculation"""
        if len(self._volume_values) <= self.vc_config.volume_ma_period:
            # Initialize sum for first values
            if len(self._volume_values) == 1:
                self._volume_ma_sum = current_volume
            else:
                self._volume_ma_sum += current_volume
        else:
            # Update moving average
            oldest_volume = self._volume_values[-self.vc_config.volume_ma_period - 1]
            self._volume_ma_sum = self._volume_ma_sum - oldest_volume + current_volume

        # Calculate current MA value
        ma_value = self._volume_ma_sum / min(len(self._volume_values), self.vc_config.volume_ma_period)
        self._volume_ma_values.append(ma_value)

    def _calculate_confirmation_score(self, volume: float, price_change: float) -> float:
        """Calculate volume confirmation score for the current bar"""
        if not self.is_ready or len(self._volume_ma_values) == 0:
            return 0.0

        volume_ma = self._volume_ma_values[-1]

        # Volume ratio (current volume vs moving average)
        volume_ratio = volume / volume_ma if volume_ma > 0 else 1.0

        # Price direction factor
        price_direction = 1.0 if price_change > 0 else -1.0 if price_change < 0 else 0.0

        # Confirmation score combines volume and price direction
        if price_direction > 0:  # Bullish price movement
            confirmation_score = volume_ratio if volume_ratio > 1.0 else volume_ratio * 0.5
        elif price_direction < 0:  # Bearish price movement
            confirmation_score = volume_ratio if volume_ratio > 1.0 else volume_ratio * 0.5
        else:  # No price movement
            confirmation_score = 0.0

        # Normalize to 0-1 scale
        return min(1.0, max(0.0, confirmation_score))

    def _analyze_confirmation_signals(self, confirmation_score: float, price_change: float):
        """Analyze bullish/bearish confirmation signals"""
        # Bullish confirmation: rising price with above-average volume
        if price_change > 0 and confirmation_score >= self.vc_config.confirmation_threshold:
            self._bullish_confirmation = True
            self._bearish_confirmation = False
            self._confirmation_strength = confirmation_score

        # Bearish confirmation: falling price with above-average volume
        elif price_change < 0 and confirmation_score >= self.vc_config.confirmation_threshold:
            self._bullish_confirmation = False
            self._bearish_confirmation = True
            self._confirmation_strength = confirmation_score

        else:
            self._bullish_confirmation = False
            self._bearish_confirmation = False
            self._confirmation_strength = confirmation_score

    def _detect_volume_divergences(self):
        """Detect volume divergences with price"""
        if not self.is_ready or len(self._confirmation_scores) < 5:
            return

        recent_confirmations = list(self._confirmation_scores)[-5:]
        recent_price_changes = list(self._price_changes)[-5:]

        # Simple divergence detection
        confirmation_trend = recent_confirmations[-1] - recent_confirmations[-3]
        price_trend = recent_price_changes[-1] - recent_price_changes[-3]

        # Bullish divergence: price falling but volume confirmation rising
        if price_trend < 0 and confirmation_trend > 0 and recent_confirmations[-1] > self.vc_config.divergence_threshold:
            self._divergence_detected = True
            self._divergence_type = "bullish"
            self._divergence_confidence = min(1.0, confirmation_trend * 2)

        # Bearish divergence: price rising but volume confirmation falling
        elif price_trend > 0 and confirmation_trend < 0 and recent_confirmations[-1] < (1 - self.vc_config.divergence_threshold):
            self._divergence_detected = True
            self._divergence_type = "bearish"
            self._divergence_confidence = min(1.0, abs(confirmation_trend) * 2)

        else:
            self._divergence_detected = False
            self._divergence_type = "none"
            self._divergence_confidence = 0.0

    def _update_volume_trend(self):
        """Update volume trend analysis"""
        if not self.is_ready or len(self._volume_ma_values) < 3:
            return

        recent_volumes = list(self._volume_ma_values)[-3:]
        volume_slope = (recent_volumes[-1] - recent_volumes[0]) / 3

        if volume_slope > 0:
            self._volume_trend = "increasing"
        elif volume_slope < 0:
            self._volume_trend = "decreasing"
        else:
            self._volume_trend = "neutral"

        # Calculate price-volume alignment
        if len(self._price_changes) >= 3:
            recent_prices = list(self._price_changes)[-3:]
            price_slope = (recent_prices[-1] - recent_prices[0]) / 3

            # Alignment score: how well volume and price move together
            if (volume_slope > 0 and price_slope > 0) or (volume_slope < 0 and price_slope < 0):
                self._price_volume_alignment = 0.8
            elif (volume_slope > 0 and price_slope < 0) or (volume_slope < 0 and price_slope > 0):
                self._price_volume_alignment = 0.2
            else:
                self._price_volume_alignment = 0.5

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade Volume Confirmation analysis"""
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

        # Use latest confirmation score as primary raw value
        raw_value = self._confirmation_scores[-1] if self._confirmation_scores else 0.0

        # Determine signal type based on volume confirmation analysis
        signal_type = self._determine_vc_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'confirmation_strength': self._confirmation_strength,
            'price_volume_alignment': self._price_volume_alignment,
            'divergence_confidence': self._divergence_confidence
        }

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._suggested_sl,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Volume_Confirmation",
                "volume_ma_period": self.vc_config.volume_ma_period,
                "confirmation_threshold": self.vc_config.confirmation_threshold,
                "bullish_confirmation": self._bullish_confirmation,
                "bearish_confirmation": self._bearish_confirmation,
                "confirmation_strength": self._confirmation_strength,
                "divergence_detected": self._divergence_detected,
                "divergence_type": self._divergence_type,
                "divergence_confidence": self._divergence_confidence,
                "volume_trend": self._volume_trend,
                "price_volume_alignment": self._price_volume_alignment,
                "current_volume_ma": self._volume_ma_values[-1] if self._volume_ma_values else 0.0,
                "is_ready": self.is_ready
            }
        )

    def _determine_vc_signal(self) -> SignalType:
        """Determine signal type based on Volume Confirmation analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong confirmation signals
        if self._confirmation_strength >= self.vc_config.confirmation_threshold:
            if self._bullish_confirmation:
                return SignalType.BULLISH
            elif self._bearish_confirmation:
                return SignalType.BEARISH

        # Divergence signals
        if self._divergence_detected and self._divergence_confidence > 0.6:
            if self._divergence_type == "bullish":
                return SignalType.BULLISH
            elif self._divergence_type == "bearish":
                return SignalType.BEARISH

        return SignalType.NEUTRAL

    @property
    def confirmation_score(self) -> float:
        """Get the current volume confirmation score"""
        return self._confirmation_scores[-1] if self._confirmation_scores else 0.0

    @property
    def volume_ma(self) -> float:
        """Get the current volume moving average"""
        return self._volume_ma_values[-1] if self._volume_ma_values else 0.0

    @property
    def bullish_confirmation(self) -> bool:
        """Return True if bullish confirmation is detected"""
        return self._bullish_confirmation

    @property
    def bearish_confirmation(self) -> bool:
        """Return True if bearish confirmation is detected"""
        return self._bearish_confirmation

    @property
    def confirmation_strength(self) -> float:
        """Get the current confirmation strength (0-1)"""
        return self._confirmation_strength

    @property
    def divergence_detected(self) -> bool:
        """Return True if volume divergence is detected"""
        return self._divergence_detected

    @property
    def divergence_type(self) -> str:
        """Get the type of divergence detected"""
        return self._divergence_type

    @property
    def divergence_confidence(self) -> float:
        """Get the confidence in divergence detection"""
        return self._divergence_confidence

    @property
    def volume_trend(self) -> str:
        """Get the current volume trend"""
        return self._volume_trend

    @property
    def price_volume_alignment(self) -> float:
        """Get the current price-volume alignment score"""
        return self._price_volume_alignment

    def is_volume_confirmed(self, price_change: float) -> bool:
        """Check if volume confirms the price movement"""
        if not self.is_ready:
            return False

        if price_change > 0:
            return self._bullish_confirmation
        elif price_change < 0:
            return self._bearish_confirmation
        else:
            return False

    def get_volume_confirmation_info(self) -> Dict[str, Any]:
        """Get comprehensive volume confirmation information"""
        return {
            "confirmation_analysis": {
                "bullish": self._bullish_confirmation,
                "bearish": self._bearish_confirmation,
                "strength": self._confirmation_strength,
                "threshold": self.vc_config.confirmation_threshold
            },
            "divergence_analysis": {
                "detected": self._divergence_detected,
                "type": self._divergence_type,
                "confidence": self._divergence_confidence
            },
            "trend_analysis": {
                "volume_trend": self._volume_trend,
                "price_volume_alignment": self._price_volume_alignment
            },
            "technical_data": {
                "current_volume_ma": self.volume_ma,
                "confirmation_score": self.confirmation_score,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._volume_values.clear()
        self._price_changes.clear()
        self._confirmation_scores.clear()
        self._volume_ma_values.clear()
        self._volume_ma_sum = 0.0
        self._bullish_confirmation = False
        self._bearish_confirmation = False
        self._confirmation_strength = 0.0
        self._divergence_detected = False
        self._divergence_type = "none"
        self._divergence_confidence = 0.0
        self._volume_trend = "neutral"
        self._price_volume_alignment = 0.0