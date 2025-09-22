"""
Institutional-Grade Augmented Force Index Indicator

This module implements an enhanced Force Index indicator with institutional-grade features:
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
class AugmentedForceIndexConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Force Index"""
    force_period: int = 13
    ema_period: int = 9
    overbought_level: float = 0.15
    oversold_level: float = -0.15


class AugmentedForceIndex(AugmentedIndicator):
    """
    Institutional-grade Augmented Force Index indicator implementing 5-pillar architecture.

    Features:
    - Price-volume force analysis for momentum measurement
    - Buying/selling pressure strength assessment
    - Market regime adaptation based on force patterns
    - Multi-timeframe convergence for institutional confirmation
    - Smart money force analysis for trend strength validation
    - Automated risk management for momentum-based strategies
    """

    def __init__(self, config: AugmentedForceIndexConfig = None):
        if config is None:
            config = AugmentedForceIndexConfig()

        super().__init__(config)
        self.force_config = config

        # Force Index specific state
        self._closes = deque(maxlen=self.config.buffer_size)
        self._volumes = deque(maxlen=self.config.buffer_size)
        self._raw_force_values = deque(maxlen=self.config.buffer_size)
        self._force_values = deque(maxlen=self.config.buffer_size)
        self._ema_force_values = deque(maxlen=self.config.buffer_size)
        self._current_force = None
        self._current_ema_force = None

        # Force analysis
        self._force_direction = 0  # -1, 0, 1 for down, neutral, up
        self._force_strength = 0.0
        self._force_acceleration = 0.0

        # Momentum analysis
        self._momentum_signals = 0
        self._breakout_signals = 0
        self._breakout_probability = 0.0
        self._momentum_divergence = 0.0

        # Volume analysis
        self._volume_force = 0.0
        self._volume_participation = 0.0
        self._institutional_force = 0.0

        # Institutional analysis
        self._smart_money_force = 0.0
        self._institutional_confidence = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Force Index is ready to provide signals"""
        return (len(self._force_values) > 0 and
                len(self._ema_force_values) > 0 and
                self._current_force is not None and
                self._current_ema_force is not None)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update Force Index analysis

        Args:
            bar (Bar): New bar data
        """
        # Extract price and volume data
        if hasattr(bar, 'close') and hasattr(bar, 'volume'):
            close = bar.close
            volume = bar.volume
        else:
            close = bar.get('close', bar.get('price', 0.0))
            volume = bar.get('volume', 1.0)

        # Update Force Index calculation
        self._update_force_index(close, volume)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_force_index(self, close: float, volume: float):
        """Update the core Force Index calculation with institutional enhancements"""
        self._closes.append(close)
        self._volumes.append(volume)

        if len(self._closes) >= 2:
            # Calculate Raw Force Index: (Current Close - Previous Close) * Current Volume
            price_change = close - self._closes[-2]
            raw_force = price_change * volume
            self._raw_force_values.append(raw_force)

            # Calculate Force Index (EMA of raw force)
            if len(self._raw_force_values) >= self.force_config.force_period:
                force_value = self._calculate_ema(list(self._raw_force_values)[-self.force_config.force_period:],
                                                 self.force_config.force_period)
                self._current_force = force_value
                self._force_values.append(force_value)

                # Calculate EMA of Force Index
                if len(self._force_values) >= self.force_config.ema_period:
                    ema_force = self._calculate_ema(list(self._force_values)[-self.force_config.ema_period:],
                                                   self.force_config.ema_period)
                    self._current_ema_force = ema_force
                    self._ema_force_values.append(ema_force)

                    # Analyze Force Index characteristics
                    self._analyze_force_characteristics()

    def _calculate_ema(self, values: list, period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(values) < period:
            return sum(values) / len(values) if values else 0.0

        alpha = 2.0 / (period + 1)
        ema = values[0]

        for value in values[1:]:
            ema = alpha * value + (1 - alpha) * ema

        return ema

    def _analyze_force_characteristics(self):
        """Analyze Force Index characteristics for institutional insights"""
        if not self.is_ready or len(self._force_values) < 3:
            return

        force_value = self._current_force
        ema_force_value = self._current_ema_force

        # Normalize force values for analysis
        if len(self._force_values) >= 10:
            force_std = statistics.stdev(list(self._force_values)[-10:]) if len(self._force_values) >= 10 else 0
            if force_std > 0:
                normalized_force = force_value / force_std
            else:
                normalized_force = 0.0
        else:
            normalized_force = force_value / 1000.0  # Rough normalization

        # Calculate force direction and strength
        if normalized_force > 0.5:
            self._force_direction = 1  # Up force
            self._force_strength = min(1.0, normalized_force / 2.0)
        elif normalized_force < -0.5:
            self._force_direction = -1  # Down force
            self._force_strength = min(1.0, abs(normalized_force) / 2.0)
        else:
            self._force_direction = 0  # Neutral force
            self._force_strength = 0.0

        # Calculate force acceleration
        if len(self._force_values) >= 3:
            recent_force = list(self._force_values)[-3:]
            self._force_acceleration = (recent_force[-1] - recent_force[-2]) - (recent_force[-2] - recent_force[-1])

        # Track momentum signals
        if abs(normalized_force) > 1.0:
            self._momentum_signals += 1

        # Calculate breakout probability
        if abs(normalized_force) > 1.5:
            self._breakout_probability = min(1.0, abs(normalized_force) / 3.0)
            if normalized_force > 0:
                self._breakout_signals += 1
        else:
            self._breakout_probability = 0.0

        # Calculate momentum divergence
        if len(self._closes) >= 5 and len(self._force_values) >= 5:
            recent_prices = list(self._closes)[-5:]
            recent_force = list(self._force_values)[-5:]

            price_trend = recent_prices[-1] - recent_prices[0]
            force_trend = recent_force[-1] - recent_force[0]

            if price_trend * force_trend < 0:  # Opposite directions
                self._momentum_divergence = min(1.0, abs(price_trend - force_trend) / (abs(price_trend) + abs(force_trend)))
            else:
                self._momentum_divergence = 0.0

        # Calculate volume force
        if len(self._volumes) >= 5:
            avg_volume = sum(list(self._volumes)[-5:]) / 5
            current_volume = self._volumes[-1]

            if avg_volume > 0:
                self._volume_force = min(1.0, current_volume / (avg_volume * 2.0))

        # Calculate volume participation
        if len(self._volumes) >= 10:
            avg_volume = sum(list(self._volumes)[-10:]) / 10
            current_volume = self._volumes[-1]

            if avg_volume > 0:
                self._volume_participation = min(1.0, current_volume / (avg_volume * 1.5))

        # Calculate institutional force
        if self._volume_participation > 0.7 and self._force_strength > 0.6:
            self._institutional_force = 0.8  # High volume with strong force
        elif self._volume_participation > 0.5 and self._force_strength > 0.4:
            self._institutional_force = 0.6  # Moderate volume with force
        else:
            self._institutional_force = 0.4  # Normal activity

        # Calculate institutional confidence
        self._calculate_institutional_confidence()

    def _calculate_institutional_confidence(self):
        """Calculate institutional confidence based on Force Index analysis"""
        if not self.is_ready:
            return

        # Institutional traders use Force Index for momentum confirmation
        base_confidence = (
            self._force_strength * 0.4 +
            self._volume_participation * 0.3 +
            self._institutional_force * 0.3
        )

        # Boost confidence for extreme readings
        if abs(self._current_force) > 1000:  # Large force values
            base_confidence *= 1.2

        self._institutional_confidence = min(1.0, base_confidence)

        # Smart money force considers both momentum and volume
        smart_money_score = (
            self._force_strength * 0.4 +
            self._volume_force * 0.3 +
            self._institutional_force * 0.3
        )
        self._smart_money_force = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade Force Index analysis"""
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

        force_value = self._current_force

        # Determine signal type based on Force Index analysis
        signal_type = self._determine_force_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'force_strength': self._force_strength,
            'force_acceleration': self._force_acceleration,
            'breakout_probability': self._breakout_probability,
            'momentum_divergence': self._momentum_divergence,
            'volume_force': self._volume_force,
            'volume_participation': self._volume_participation,
            'institutional_force': self._institutional_force,
            'institutional_confidence': self._institutional_confidence,
            'smart_money_force': self._smart_money_force
        }

        # Use Force Index value as primary raw value
        raw_value = force_value

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._suggested_sl,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Force_Index",
                "force_period": self.force_config.force_period,
                "ema_period": self.force_config.ema_period,
                "overbought_level": self.force_config.overbought_level,
                "oversold_level": self.force_config.oversold_level,
                "force_direction": self._force_direction,
                "force_strength": self._force_strength,
                "force_acceleration": self._force_acceleration,
                "momentum_signals": self._momentum_signals,
                "breakout_signals": self._breakout_signals,
                "breakout_probability": self._breakout_probability,
                "momentum_divergence": self._momentum_divergence,
                "volume_force": self._volume_force,
                "volume_participation": self._volume_participation,
                "institutional_force": self._institutional_force,
                "institutional_confidence": self._institutional_confidence,
                "smart_money_force": self._smart_money_force,
                "current_ema_force": self._current_ema_force,
                "is_ready": self.is_ready
            }
        )

    def _determine_force_signal(self) -> SignalType:
        """Determine signal type based on Force Index analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        force_value = self._current_force

        # Strong momentum signals
        if self._force_strength > 0.8 and self._breakout_probability > 0.7:
            if self._force_direction == 1:
                return SignalType.STRONG_BULLISH
            elif self._force_direction == -1:
                return SignalType.STRONG_BEARISH

        # Moderate momentum signals
        elif self._force_strength > 0.6 and self._volume_participation > 0.6:
            if self._force_direction == 1:
                return SignalType.BULLISH
            elif self._force_direction == -1:
                return SignalType.BEARISH

        # Breakout signals
        elif self._breakout_probability > 0.6:
            if force_value > 0:
                return SignalType.BULLISH
            else:
                return SignalType.BEARISH

        # Divergence signals
        elif self._momentum_divergence > 0.6:
            return SignalType.BEARISH  # Divergence often signals reversal

        return SignalType.NEUTRAL

    @property
    def force_index(self) -> float:
        """Get the current Force Index value"""
        return self._current_force if self.is_ready else 0.0

    @property
    def ema_force(self) -> float:
        """Get the current EMA of Force Index value"""
        return self._current_ema_force if self.is_ready else 0.0

    @property
    def force_direction(self) -> int:
        """Get the current force direction (-1, 0, 1)"""
        return self._force_direction

    @property
    def force_strength(self) -> float:
        """Get the current force strength (0-1)"""
        return self._force_strength

    @property
    def force_acceleration(self) -> float:
        """Get the current force acceleration"""
        return self._force_acceleration

    @property
    def momentum_signals(self) -> int:
        """Get the count of momentum signals"""
        return self._momentum_signals

    @property
    def breakout_signals(self) -> int:
        """Get the count of breakout signals"""
        return self._breakout_signals

    @property
    def breakout_probability(self) -> float:
        """Get the breakout probability (0-1)"""
        return self._breakout_probability

    @property
    def momentum_divergence(self) -> float:
        """Get the momentum divergence (0-1)"""
        return self._momentum_divergence

    @property
    def volume_force(self) -> float:
        """Get the volume force score (0-1)"""
        return self._volume_force

    @property
    def volume_participation(self) -> float:
        """Get the volume participation score (0-1)"""
        return self._volume_participation

    @property
    def institutional_force(self) -> float:
        """Get the institutional force score (0-1)"""
        return self._institutional_force

    @property
    def institutional_confidence(self) -> float:
        """Get the institutional confidence score (0-1)"""
        return self._institutional_confidence

    @property
    def smart_money_force(self) -> float:
        """Get the smart money force score (0-1)"""
        return self._smart_money_force

    def is_positive_force(self) -> bool:
        """Check if force is positive"""
        if not self.is_ready:
            return False
        return self._force_direction == 1

    def is_negative_force(self) -> bool:
        """Check if force is negative"""
        if not self.is_ready:
            return False
        return self._force_direction == -1

    def is_strong_force(self) -> bool:
        """Check if force is strong"""
        return self._force_strength > 0.6

    def is_accelerating_force(self) -> bool:
        """Check if force is accelerating"""
        return self._force_acceleration > 0.1

    def is_breakout_likely(self) -> bool:
        """Check if breakout is likely"""
        return self._breakout_probability > 0.6

    def is_divergence_present(self) -> bool:
        """Check if momentum divergence is present"""
        return self._momentum_divergence > 0.6

    def is_high_volume_participation(self) -> bool:
        """Check if volume participation is high"""
        return self._volume_participation > 0.7

    def is_institutional_force(self) -> bool:
        """Check if force is institutional"""
        return self._institutional_force > 0.7

    def get_force_index_info(self) -> Dict[str, Any]:
        """Get comprehensive Force Index information"""
        return {
            "force_value": self.force_index,
            "ema_force_value": self.ema_force,
            "force_analysis": {
                "direction": self._force_direction,
                "strength": self._force_strength,
                "acceleration": self._force_acceleration
            },
            "momentum_analysis": {
                "momentum_signals": self._momentum_signals,
                "breakout_signals": self._breakout_signals,
                "breakout_probability": self._breakout_probability,
                "momentum_divergence": self._momentum_divergence
            },
            "volume_analysis": {
                "volume_force": self._volume_force,
                "volume_participation": self._volume_participation,
                "institutional_force": self._institutional_force
            },
            "institutional_analysis": {
                "confidence": self._institutional_confidence,
                "smart_money_force": self._smart_money_force
            },
            "metadata": {
                "force_period": self.force_config.force_period,
                "ema_period": self.force_config.ema_period,
                "overbought_level": self.force_config.overbought_level,
                "oversold_level": self.force_config.oversold_level,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._closes.clear()
        self._volumes.clear()
        self._raw_force_values.clear()
        self._force_values.clear()
        self._ema_force_values.clear()
        self._current_force = None
        self._current_ema_force = None
        self._force_direction = 0
        self._force_strength = 0.0
        self._force_acceleration = 0.0
        self._momentum_signals = 0
        self._breakout_signals = 0
        self._breakout_probability = 0.0
        self._momentum_divergence = 0.0
        self._volume_force = 0.0
        self._volume_participation = 0.0
        self._institutional_force = 0.0
        self._smart_money_force = 0.0
        self._institutional_confidence = 0.0