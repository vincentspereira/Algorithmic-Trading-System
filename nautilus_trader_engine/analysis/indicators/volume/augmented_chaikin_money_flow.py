"""
Institutional-Grade Augmented Chaikin Money Flow Indicator

This module implements an enhanced Chaikin Money Flow indicator with institutional-grade features:
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
class AugmentedChaikinMoneyFlowConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Chaikin Money Flow"""
    cmf_period: int = 21
    overbought_level: float = 0.25
    oversold_level: float = -0.25


class AugmentedChaikinMoneyFlow(AugmentedIndicator):
    """
    Institutional-grade Augmented Chaikin Money Flow indicator implementing 5-pillar architecture.

    Features:
    - Accumulation/distribution analysis with volume weighting
    - Money flow direction and strength analysis
    - Market regime adaptation based on flow patterns
    - Multi-timeframe convergence for institutional confirmation
    - Smart money flow analysis for accumulation/distribution detection
    - Automated risk management for volume-based strategies
    """

    def __init__(self, config: AugmentedChaikinMoneyFlowConfig = None):
        if config is None:
            config = AugmentedChaikinMoneyFlowConfig()

        super().__init__(config)
        self.cmf_config = config

        # Chaikin Money Flow specific state
        self._highs = deque(maxlen=self.config.buffer_size)
        self._lows = deque(maxlen=self.config.buffer_size)
        self._closes = deque(maxlen=self.config.buffer_size)
        self._volumes = deque(maxlen=self.config.buffer_size)
        self._money_flow_multipliers = deque(maxlen=self.config.buffer_size)
        self._money_flow_volumes = deque(maxlen=self.config.buffer_size)
        self._cmf_values = deque(maxlen=self.config.buffer_size)
        self._current_cmf = None

        # Money flow analysis
        self._flow_direction = 0  # -1, 0, 1 for negative, neutral, positive
        self._flow_strength = 0.0
        self._flow_acceleration = 0.0

        # Accumulation/distribution
        self._accumulation_signals = 0
        self._distribution_signals = 0
        self._accumulation_probability = 0.0
        self._distribution_probability = 0.0

        # Volume analysis
        self._volume_trend = "neutral"  # "increasing", "decreasing", "stable"
        self._volume_participation = 0.0
        self._institutional_volume = 0.0

        # Institutional analysis
        self._smart_money_flow = 0.0
        self._institutional_confidence = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Chaikin Money Flow is ready to provide signals"""
        return len(self._cmf_values) > 0 and self._current_cmf is not None

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update Chaikin Money Flow analysis

        Args:
            bar (Bar): New bar data
        """
        # Extract OHLCV data
        if hasattr(bar, 'high') and hasattr(bar, 'low') and hasattr(bar, 'close') and hasattr(bar, 'volume'):
            high = bar.high
            low = bar.low
            close = bar.close
            volume = bar.volume
        else:
            high = bar.get('high', bar.get('close', 0.0))
            low = bar.get('low', bar.get('close', 0.0))
            close = bar.get('close', bar.get('price', 0.0))
            volume = bar.get('volume', 1.0)

        # Update Chaikin Money Flow calculation
        self._update_chaikin_money_flow(high, low, close, volume)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_chaikin_money_flow(self, high: float, low: float, close: float, volume: float):
        """Update the core Chaikin Money Flow calculation with institutional enhancements"""
        self._highs.append(high)
        self._lows.append(low)
        self._closes.append(close)
        self._volumes.append(volume)

        if len(self._closes) >= 2:
            # Calculate Money Flow Multiplier
            typical_price = (high + low + close) / 3
            past_typical_price = (self._highs[-2] + self._lows[-2] + self._closes[-2]) / 3

            if high - low > 0:
                money_flow_multiplier = ((close - low) - (high - close)) / (high - low)
            else:
                money_flow_multiplier = 0.0

            self._money_flow_multipliers.append(money_flow_multiplier)

            # Calculate Money Flow Volume
            money_flow_volume = money_flow_multiplier * volume
            self._money_flow_volumes.append(money_flow_volume)

            # Calculate Chaikin Money Flow
            if len(self._money_flow_volumes) >= self.cmf_config.cmf_period:
                mfvs_sum = sum(list(self._money_flow_volumes)[-self.cmf_config.cmf_period:])
                volumes_sum = sum(list(self._volumes)[-self.cmf_config.cmf_period:])

                if volumes_sum > 0:
                    self._current_cmf = mfvs_sum / volumes_sum
                    self._cmf_values.append(self._current_cmf)

                    # Analyze Chaikin Money Flow characteristics
                    self._analyze_cmf_characteristics()

    def _analyze_cmf_characteristics(self):
        """Analyze Chaikin Money Flow characteristics for institutional insights"""
        if not self.is_ready or len(self._cmf_values) < 3:
            return

        cmf_value = self._current_cmf

        # Calculate flow direction and strength
        if cmf_value > 0.1:
            self._flow_direction = 1  # Positive money flow
            self._flow_strength = min(1.0, cmf_value / 0.5)
        elif cmf_value < -0.1:
            self._flow_direction = -1  # Negative money flow
            self._flow_strength = min(1.0, abs(cmf_value) / 0.5)
        else:
            self._flow_direction = 0  # Neutral money flow
            self._flow_strength = 0.0

        # Calculate flow acceleration
        if len(self._cmf_values) >= 3:
            recent_cmf = list(self._cmf_values)[-3:]
            self._flow_acceleration = (recent_cmf[-1] - recent_cmf[-2]) - (recent_cmf[-2] - recent_cmf[-1])

        # Track accumulation/distribution signals
        if cmf_value >= self.cmf_config.overbought_level:
            self._accumulation_signals += 1
            self._accumulation_probability = min(1.0, cmf_value / 0.5)
            self._distribution_probability = 0.0
        elif cmf_value <= self.cmf_config.oversold_level:
            self._distribution_signals += 1
            self._distribution_probability = min(1.0, abs(cmf_value) / 0.5)
            self._accumulation_probability = 0.0
        else:
            self._accumulation_probability = 0.0
            self._distribution_probability = 0.0

        # Analyze volume trend
        if len(self._volumes) >= 5:
            recent_volumes = list(self._volumes)[-5:]
            volume_trend = (recent_volumes[-1] - recent_volumes[0]) / 5

            if volume_trend > 0.1:
                self._volume_trend = "increasing"
            elif volume_trend < -0.1:
                self._volume_trend = "decreasing"
            else:
                self._volume_trend = "stable"

        # Calculate volume participation
        if len(self._volumes) >= 10:
            avg_volume = sum(list(self._volumes)[-10:]) / 10
            current_volume = self._volumes[-1]

            if avg_volume > 0:
                self._volume_participation = min(1.0, current_volume / (avg_volume * 1.5))

        # Calculate institutional volume
        if self._volume_participation > 0.7 and abs(cmf_value) > 0.2:
            self._institutional_volume = 0.8  # High volume with strong money flow
        elif self._volume_participation > 0.5 and abs(cmf_value) > 0.1:
            self._institutional_volume = 0.6  # Moderate volume with money flow
        else:
            self._institutional_volume = 0.4  # Normal activity

        # Calculate institutional confidence
        self._calculate_institutional_confidence()

    def _calculate_institutional_confidence(self):
        """Calculate institutional confidence based on Chaikin Money Flow analysis"""
        if not self.is_ready:
            return

        # Institutional traders use CMF for accumulation/distribution analysis
        base_confidence = (
            self._flow_strength * 0.4 +
            self._volume_participation * 0.3 +
            self._institutional_volume * 0.3
        )

        # Boost confidence for extreme readings
        if abs(self._current_cmf) > 0.3:
            base_confidence *= 1.2

        self._institutional_confidence = min(1.0, base_confidence)

        # Smart money flow considers both direction and volume
        smart_money_score = (
            self._flow_strength * 0.4 +
            self._volume_participation * 0.3 +
            self._institutional_volume * 0.3
        )
        self._smart_money_flow = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade Chaikin Money Flow analysis"""
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

        cmf_value = self._current_cmf

        # Determine signal type based on Chaikin Money Flow analysis
        signal_type = self._determine_cmf_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'flow_strength': self._flow_strength,
            'flow_acceleration': self._flow_acceleration,
            'accumulation_probability': self._accumulation_probability,
            'distribution_probability': self._distribution_probability,
            'volume_participation': self._volume_participation,
            'institutional_volume': self._institutional_volume,
            'institutional_confidence': self._institutional_confidence,
            'smart_money_flow': self._smart_money_flow
        }

        # Use CMF value as primary raw value
        raw_value = cmf_value

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._suggested_sl,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Chaikin_Money_Flow",
                "cmf_period": self.cmf_config.cmf_period,
                "overbought_level": self.cmf_config.overbought_level,
                "oversold_level": self.cmf_config.oversold_level,
                "flow_direction": self._flow_direction,
                "flow_strength": self._flow_strength,
                "flow_acceleration": self._flow_acceleration,
                "volume_trend": self._volume_trend,
                "accumulation_signals": self._accumulation_signals,
                "distribution_signals": self._distribution_signals,
                "accumulation_probability": self._accumulation_probability,
                "distribution_probability": self._distribution_probability,
                "volume_participation": self._volume_participation,
                "institutional_volume": self._institutional_volume,
                "institutional_confidence": self._institutional_confidence,
                "smart_money_flow": self._smart_money_flow,
                "is_ready": self.is_ready
            }
        )

    def _determine_cmf_signal(self) -> SignalType:
        """Determine signal type based on Chaikin Money Flow analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        cmf_value = self._current_cmf

        # Strong accumulation signals
        if cmf_value >= self.cmf_config.overbought_level and self._accumulation_probability > 0.7:
            return SignalType.STRONG_BULLISH

        # Strong distribution signals
        elif cmf_value <= self.cmf_config.oversold_level and self._distribution_probability > 0.7:
            return SignalType.STRONG_BEARISH

        # Moderate accumulation signals
        elif cmf_value >= self.cmf_config.overbought_level:
            return SignalType.BULLISH

        # Moderate distribution signals
        elif cmf_value <= self.cmf_config.oversold_level:
            return SignalType.BEARISH

        # Flow strength signals
        elif self._flow_strength > 0.6 and self._volume_participation > 0.6:
            if self._flow_direction == 1:
                return SignalType.BULLISH
            elif self._flow_direction == -1:
                return SignalType.BEARISH

        return SignalType.NEUTRAL

    @property
    def chaikin_money_flow(self) -> float:
        """Get the current Chaikin Money Flow value"""
        return self._current_cmf if self.is_ready else 0.0

    @property
    def flow_direction(self) -> int:
        """Get the current money flow direction (-1, 0, 1)"""
        return self._flow_direction

    @property
    def flow_strength(self) -> float:
        """Get the current money flow strength (0-1)"""
        return self._flow_strength

    @property
    def flow_acceleration(self) -> float:
        """Get the current money flow acceleration"""
        return self._flow_acceleration

    @property
    def volume_trend(self) -> str:
        """Get the current volume trend"""
        return self._volume_trend

    @property
    def accumulation_signals(self) -> int:
        """Get the count of accumulation signals"""
        return self._accumulation_signals

    @property
    def distribution_signals(self) -> int:
        """Get the count of distribution signals"""
        return self._distribution_signals

    @property
    def accumulation_probability(self) -> float:
        """Get the accumulation probability (0-1)"""
        return self._accumulation_probability

    @property
    def distribution_probability(self) -> float:
        """Get the distribution probability (0-1)"""
        return self._distribution_probability

    @property
    def volume_participation(self) -> float:
        """Get the volume participation score (0-1)"""
        return self._volume_participation

    @property
    def institutional_volume(self) -> float:
        """Get the institutional volume score (0-1)"""
        return self._institutional_volume

    @property
    def institutional_confidence(self) -> float:
        """Get the institutional confidence score (0-1)"""
        return self._institutional_confidence

    @property
    def smart_money_flow(self) -> float:
        """Get the smart money flow score (0-1)"""
        return self._smart_money_flow

    def is_positive_flow(self) -> bool:
        """Check if money flow is positive"""
        if not self.is_ready:
            return False
        return self._flow_direction == 1

    def is_negative_flow(self) -> bool:
        """Check if money flow is negative"""
        if not self.is_ready:
            return False
        return self._flow_direction == -1

    def is_strong_flow(self) -> bool:
        """Check if money flow is strong"""
        return self._flow_strength > 0.6

    def is_accumulation_phase(self) -> bool:
        """Check if in accumulation phase"""
        return self._accumulation_probability > 0.6

    def is_distribution_phase(self) -> bool:
        """Check if in distribution phase"""
        return self._distribution_probability > 0.6

    def is_high_volume_participation(self) -> bool:
        """Check if volume participation is high"""
        return self._volume_participation > 0.7

    def is_institutional_volume(self) -> bool:
        """Check if volume is institutional"""
        return self._institutional_volume > 0.7

    def get_chaikin_money_flow_info(self) -> Dict[str, Any]:
        """Get comprehensive Chaikin Money Flow information"""
        return {
            "cmf_value": self.chaikin_money_flow,
            "flow_analysis": {
                "direction": self._flow_direction,
                "strength": self._flow_strength,
                "acceleration": self._flow_acceleration
            },
            "accumulation_distribution": {
                "accumulation_signals": self._accumulation_signals,
                "distribution_signals": self._distribution_signals,
                "accumulation_probability": self._accumulation_probability,
                "distribution_probability": self._distribution_probability
            },
            "volume_analysis": {
                "trend": self._volume_trend,
                "participation": self._volume_participation,
                "institutional_volume": self._institutional_volume
            },
            "institutional_analysis": {
                "confidence": self._institutional_confidence,
                "smart_money_flow": self._smart_money_flow
            },
            "metadata": {
                "period": self.cmf_config.cmf_period,
                "overbought_level": self.cmf_config.overbought_level,
                "oversold_level": self.cmf_config.oversold_level,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._highs.clear()
        self._lows.clear()
        self._closes.clear()
        self._volumes.clear()
        self._money_flow_multipliers.clear()
        self._money_flow_volumes.clear()
        self._cmf_values.clear()
        self._current_cmf = None
        self._flow_direction = 0
        self._flow_strength = 0.0
        self._flow_acceleration = 0.0
        self._accumulation_signals = 0
        self._distribution_signals = 0
        self._accumulation_probability = 0.0
        self._distribution_probability = 0.0
        self._volume_trend = "neutral"
        self._volume_participation = 0.0
        self._institutional_volume = 0.0
        self._smart_money_flow = 0.0
        self._institutional_confidence = 0.0