"""
Institutional-Grade Augmented Ease of Movement Indicator

This module implements an enhanced Ease of Movement indicator with institutional-grade features:
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
class AugmentedEaseOfMovementConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Ease of Movement"""
    emv_period: int = 14
    volume_divisor: float = 10000.0
    overbought_level: float = 0.05
    oversold_level: float = -0.05


class AugmentedEaseOfMovement(AugmentedIndicator):
    """
    Institutional-grade Augmented Ease of Movement indicator implementing 5-pillar architecture.

    Features:
    - Price-volume relationship analysis for trend strength assessment
    - Movement efficiency measurement for institutional flow detection
    - Market regime adaptation based on ease patterns
    - Multi-timeframe convergence for trend confirmation
    - Smart money ease analysis for accumulation/distribution detection
    - Automated risk management for volume-supported strategies
    """

    def __init__(self, config: AugmentedEaseOfMovementConfig = None):
        if config is None:
            config = AugmentedEaseOfMovementConfig()

        super().__init__(config)
        self.emv_config = config

        # Ease of Movement specific state
        self._highs = deque(maxlen=self.config.buffer_size)
        self._lows = deque(maxlen=self.config.buffer_size)
        self._volumes = deque(maxlen=self.config.buffer_size)
        self._midpoint_moves = deque(maxlen=self.config.buffer_size)
        self._box_ratios = deque(maxlen=self.config.buffer_size)
        self._emv_values = deque(maxlen=self.config.buffer_size)
        self._current_emv = None

        # Movement analysis
        self._movement_efficiency = 0.0
        self._movement_direction = 0  # -1, 0, 1 for down, neutral, up
        self._movement_strength = 0.0

        # Volume analysis
        self._volume_support = 0.0
        self._volume_efficiency = 0.0
        self._institutional_flow = 0.0

        # Trend analysis
        self._trend_signals = 0
        self._breakout_signals = 0
        self._breakout_probability = 0.0
        self._trend_reversal_probability = 0.0

        # Institutional analysis
        self._smart_money_ease = 0.0
        self._institutional_confidence = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Ease of Movement is ready to provide signals"""
        return len(self._emv_values) > 0 and self._current_emv is not None

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update Ease of Movement analysis

        Args:
            bar (Bar): New bar data
        """
        # Extract OHLCV data
        if hasattr(bar, 'high') and hasattr(bar, 'low') and hasattr(bar, 'volume'):
            high = bar.high
            low = bar.low
            volume = bar.volume
        else:
            high = bar.get('high', bar.get('close', 0.0))
            low = bar.get('low', bar.get('close', 0.0))
            volume = bar.get('volume', 1.0)

        # Update Ease of Movement calculation
        self._update_ease_of_movement(high, low, volume)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_ease_of_movement(self, high: float, low: float, volume: float):
        """Update the core Ease of Movement calculation with institutional enhancements"""
        self._highs.append(high)
        self._lows.append(low)
        self._volumes.append(volume)

        if len(self._highs) >= 2:
            # Calculate Midpoint Move: (Current High + Current Low) / 2 - (Previous High + Previous Low) / 2
            current_midpoint = (high + low) / 2
            previous_midpoint = (self._highs[-2] + self._lows[-2]) / 2
            midpoint_move = current_midpoint - previous_midpoint
            self._midpoint_moves.append(midpoint_move)

            # Calculate Box Ratio: (Current High - Current Low) / Volume
            if volume > 0:
                box_ratio = (high - low) / (volume / self.emv_config.volume_divisor)
            else:
                box_ratio = 0.0
            self._box_ratios.append(box_ratio)

            # Calculate Ease of Movement: Midpoint Move / Box Ratio
            if box_ratio != 0:
                emv_value = midpoint_move / box_ratio
            else:
                emv_value = 0.0

            self._current_emv = emv_value
            self._emv_values.append(emv_value)

            # Analyze Ease of Movement characteristics
            self._analyze_emv_characteristics()

    def _analyze_emv_characteristics(self):
        """Analyze Ease of Movement characteristics for institutional insights"""
        if not self.is_ready or len(self._emv_values) < 3:
            return

        emv_value = self._current_emv

        # Calculate movement efficiency
        if len(self._emv_values) >= 5:
            emv_std = statistics.stdev(list(self._emv_values)[-5:]) if len(self._emv_values) >= 5 else 0
            if emv_std > 0:
                self._movement_efficiency = 1.0 - (emv_std / abs(sum(self._emv_values[-5:]) / 5))
                self._movement_efficiency = max(0.0, min(1.0, self._movement_efficiency))
            else:
                self._movement_efficiency = 0.5

        # Calculate movement direction and strength
        if emv_value > 0.02:
            self._movement_direction = 1  # Up movement
            self._movement_strength = min(1.0, emv_value / 0.1)
        elif emv_value < -0.02:
            self._movement_direction = -1  # Down movement
            self._movement_strength = min(1.0, abs(emv_value) / 0.1)
        else:
            self._movement_direction = 0  # Neutral movement
            self._movement_strength = 0.0

        # Calculate volume support
        if len(self._volumes) >= 5:
            avg_volume = sum(list(self._volumes)[-5:]) / 5
            current_volume = self._volumes[-1]

            if avg_volume > 0:
                self._volume_support = min(1.0, current_volume / (avg_volume * 1.5))

        # Calculate volume efficiency
        if len(self._box_ratios) >= 3:
            recent_box_ratios = list(self._box_ratios)[-3:]
            avg_box_ratio = sum(recent_box_ratios) / len(recent_box_ratios)

            if avg_box_ratio > 0:
                self._volume_efficiency = 1.0 / (1.0 + avg_box_ratio)  # Lower box ratio = higher efficiency
            else:
                self._volume_efficiency = 0.5

        # Track trend signals
        if abs(emv_value) > 0.05:
            self._trend_signals += 1

        # Calculate breakout probability
        if abs(emv_value) > 0.08:
            self._breakout_probability = min(1.0, abs(emv_value) / 0.15)
            if emv_value > 0:
                self._breakout_signals += 1
        else:
            self._breakout_probability = 0.0

        # Calculate trend reversal probability
        if len(self._emv_values) >= 5:
            recent_emv = list(self._emv_values)[-5:]
            emv_trend = recent_emv[-1] - recent_emv[0]

            # Look for trend exhaustion
            if abs(emv_trend) < 0.01 and abs(recent_emv[-1]) < 0.02:
                self._trend_reversal_probability = 0.7  # Low movement suggests potential reversal
            elif abs(emv_value) > 0.1 and self._movement_efficiency < 0.3:
                self._trend_reversal_probability = 0.6  # Strong but inefficient movement
            else:
                self._trend_reversal_probability = 0.0

        # Calculate institutional flow
        if self._volume_support > 0.7 and self._movement_efficiency > 0.6:
            self._institutional_flow = 0.8  # High volume support with efficient movement
        elif self._volume_support > 0.5 and self._movement_efficiency > 0.4:
            self._institutional_flow = 0.6  # Moderate volume support with movement
        else:
            self._institutional_flow = 0.4  # Normal activity

        # Calculate institutional confidence
        self._calculate_institutional_confidence()

    def _calculate_institutional_confidence(self):
        """Calculate institutional confidence based on Ease of Movement analysis"""
        if not self.is_ready:
            return

        # Institutional traders use EMV for trend strength and volume confirmation
        base_confidence = (
            self._movement_efficiency * 0.3 +
            self._volume_support * 0.3 +
            self._institutional_flow * 0.4
        )

        # Boost confidence for strong, efficient movements
        if self._movement_strength > 0.7 and self._movement_efficiency > 0.7:
            base_confidence *= 1.2

        self._institutional_confidence = min(1.0, base_confidence)

        # Smart money ease considers movement efficiency and volume support
        smart_money_score = (
            self._movement_efficiency * 0.4 +
            self._volume_efficiency * 0.3 +
            self._institutional_flow * 0.3
        )
        self._smart_money_ease = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade Ease of Movement analysis"""
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

        emv_value = self._current_emv

        # Determine signal type based on Ease of Movement analysis
        signal_type = self._determine_emv_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'movement_efficiency': self._movement_efficiency,
            'movement_strength': self._movement_strength,
            'volume_support': self._volume_support,
            'volume_efficiency': self._volume_efficiency,
            'breakout_probability': self._breakout_probability,
            'trend_reversal_probability': self._trend_reversal_probability,
            'institutional_flow': self._institutional_flow,
            'institutional_confidence': self._institutional_confidence,
            'smart_money_ease': self._smart_money_ease
        }

        # Use EMV value as primary raw value
        raw_value = emv_value

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._suggested_sl,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Ease_of_Movement",
                "emv_period": self.emv_config.emv_period,
                "volume_divisor": self.emv_config.volume_divisor,
                "overbought_level": self.emv_config.overbought_level,
                "oversold_level": self.emv_config.oversold_level,
                "movement_direction": self._movement_direction,
                "movement_efficiency": self._movement_efficiency,
                "movement_strength": self._movement_strength,
                "volume_support": self._volume_support,
                "volume_efficiency": self._volume_efficiency,
                "trend_signals": self._trend_signals,
                "breakout_signals": self._breakout_signals,
                "breakout_probability": self._breakout_probability,
                "trend_reversal_probability": self._trend_reversal_probability,
                "institutional_flow": self._institutional_flow,
                "institutional_confidence": self._institutional_confidence,
                "smart_money_ease": self._smart_money_ease,
                "is_ready": self.is_ready
            }
        )

    def _determine_emv_signal(self) -> SignalType:
        """Determine signal type based on Ease of Movement analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        emv_value = self._current_emv

        # Strong trend signals
        if (self._movement_strength > 0.7 and
            self._movement_efficiency > 0.7 and
            self._volume_support > 0.6):
            if self._movement_direction == 1:
                return SignalType.STRONG_BULLISH
            elif self._movement_direction == -1:
                return SignalType.STRONG_BEARISH

        # Moderate trend signals
        elif self._movement_strength > 0.5 and self._volume_support > 0.5:
            if self._movement_direction == 1:
                return SignalType.BULLISH
            elif self._movement_direction == -1:
                return SignalType.BEARISH

        # Breakout signals
        elif self._breakout_probability > 0.6:
            if emv_value > 0:
                return SignalType.BULLISH
            else:
                return SignalType.BEARISH

        # Reversal signals
        elif self._trend_reversal_probability > 0.6:
            return SignalType.BEARISH  # Reversal often signals caution

        # Efficiency-based signals
        elif self._movement_efficiency > 0.8 and abs(emv_value) > 0.03:
            if emv_value > 0:
                return SignalType.BULLISH
            else:
                return SignalType.BEARISH

        return SignalType.NEUTRAL

    @property
    def ease_of_movement(self) -> float:
        """Get the current Ease of Movement value"""
        return self._current_emv if self.is_ready else 0.0

    @property
    def movement_direction(self) -> int:
        """Get the current movement direction (-1, 0, 1)"""
        return self._movement_direction

    @property
    def movement_efficiency(self) -> float:
        """Get the movement efficiency score (0-1)"""
        return self._movement_efficiency

    @property
    def movement_strength(self) -> float:
        """Get the movement strength (0-1)"""
        return self._movement_strength

    @property
    def volume_support(self) -> float:
        """Get the volume support score (0-1)"""
        return self._volume_support

    @property
    def volume_efficiency(self) -> float:
        """Get the volume efficiency score (0-1)"""
        return self._volume_efficiency

    @property
    def trend_signals(self) -> int:
        """Get the count of trend signals"""
        return self._trend_signals

    @property
    def breakout_signals(self) -> int:
        """Get the count of breakout signals"""
        return self._breakout_signals

    @property
    def breakout_probability(self) -> float:
        """Get the breakout probability (0-1)"""
        return self._breakout_probability

    @property
    def trend_reversal_probability(self) -> float:
        """Get the trend reversal probability (0-1)"""
        return self._trend_reversal_probability

    @property
    def institutional_flow(self) -> float:
        """Get the institutional flow score (0-1)"""
        return self._institutional_flow

    @property
    def institutional_confidence(self) -> float:
        """Get the institutional confidence score (0-1)"""
        return self._institutional_confidence

    @property
    def smart_money_ease(self) -> float:
        """Get the smart money ease score (0-1)"""
        return self._smart_money_ease

    def is_positive_movement(self) -> bool:
        """Check if movement is positive"""
        if not self.is_ready:
            return False
        return self._movement_direction == 1

    def is_negative_movement(self) -> bool:
        """Check if movement is negative"""
        if not self.is_ready:
            return False
        return self._movement_direction == -1

    def is_efficient_movement(self) -> bool:
        """Check if movement is efficient"""
        return self._movement_efficiency > 0.7

    def is_strong_movement(self) -> bool:
        """Check if movement is strong"""
        return self._movement_strength > 0.6

    def is_volume_supported(self) -> bool:
        """Check if movement has volume support"""
        return self._volume_support > 0.6

    def is_breakout_likely(self) -> bool:
        """Check if breakout is likely"""
        return self._breakout_probability > 0.6

    def is_reversal_likely(self) -> bool:
        """Check if trend reversal is likely"""
        return self._trend_reversal_probability > 0.6

    def is_institutional_flow(self) -> bool:
        """Check if flow is institutional"""
        return self._institutional_flow > 0.7

    def get_ease_of_movement_info(self) -> Dict[str, Any]:
        """Get comprehensive Ease of Movement information"""
        return {
            "emv_value": self.ease_of_movement,
            "movement_analysis": {
                "direction": self._movement_direction,
                "efficiency": self._movement_efficiency,
                "strength": self._movement_strength
            },
            "volume_analysis": {
                "volume_support": self._volume_support,
                "volume_efficiency": self._volume_efficiency,
                "institutional_flow": self._institutional_flow
            },
            "trend_analysis": {
                "trend_signals": self._trend_signals,
                "breakout_signals": self._breakout_signals,
                "breakout_probability": self._breakout_probability,
                "trend_reversal_probability": self._trend_reversal_probability
            },
            "institutional_analysis": {
                "confidence": self._institutional_confidence,
                "smart_money_ease": self._smart_money_ease
            },
            "metadata": {
                "period": self.emv_config.emv_period,
                "volume_divisor": self.emv_config.volume_divisor,
                "overbought_level": self.emv_config.overbought_level,
                "oversold_level": self.emv_config.oversold_level,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._highs.clear()
        self._lows.clear()
        self._volumes.clear()
        self._midpoint_moves.clear()
        self._box_ratios.clear()
        self._emv_values.clear()
        self._current_emv = None
        self._movement_efficiency = 0.0
        self._movement_direction = 0
        self._movement_strength = 0.0
        self._volume_support = 0.0
        self._volume_efficiency = 0.0
        self._trend_signals = 0
        self._breakout_signals = 0
        self._breakout_probability = 0.0
        self._trend_reversal_probability = 0.0
        self._institutional_flow = 0.0
        self._smart_money_ease = 0.0
        self._institutional_confidence = 0.0