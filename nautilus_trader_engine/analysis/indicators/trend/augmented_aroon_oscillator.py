"""
Institutional-Grade Augmented Aroon Oscillator Indicator

This module implements an enhanced Aroon Oscillator indicator with institutional-grade features:
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
class AugmentedAroonConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Aroon Oscillator"""
    aroon_period: int = 14
    overbought_level: float = 70.0
    oversold_level: float = -70.0


class AugmentedAroonOscillator(AugmentedIndicator):
    """
    Institutional-grade Augmented Aroon Oscillator indicator implementing 5-pillar architecture.

    Features:
    - Trend strength and direction measurement
    - Uptrend and downtrend oscillator analysis
    - Market regime adaptation based on trend strength
    - Multi-timeframe convergence for institutional confirmation
    - Smart money trend analysis for institutional flow detection
    - Automated risk management for trend-following strategies
    """

    def __init__(self, config: AugmentedAroonConfig = None):
        if config is None:
            config = AugmentedAroonConfig()

        super().__init__(config)
        self.aroon_config = config

        # Aroon Oscillator specific state
        self._highs = deque(maxlen=self.config.buffer_size)
        self._lows = deque(maxlen=self.config.buffer_size)

        # Aroon Up and Down values
        self._aroon_up_values = deque(maxlen=self.config.buffer_size)
        self._aroon_down_values = deque(maxlen=self.config.buffer_size)
        self._aroon_oscillator_values = deque(maxlen=self.config.buffer_size)

        self._current_aroon_up = None
        self._current_aroon_down = None
        self._current_aroon_oscillator = None

        # Trend analysis
        self._trend_direction = 0  # -1, 0, 1 for down, neutral, up
        self._trend_strength = 0.0
        self._trend_consistency = 0.0

        # Oscillator analysis
        self._oscillator_momentum = 0.0
        self._oscillator_divergence = 0.0
        self._overbought_signals = 0
        self._oversold_signals = 0

        # Market structure
        self._high_since_period = 0
        self._low_since_period = 0
        self._trend_reversal_probability = 0.0
        self._breakout_probability = 0.0

        # Institutional analysis
        self._institutional_aroon = 0.0
        self._smart_money_oscillator = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Aroon Oscillator is ready to provide signals"""
        return (len(self._aroon_up_values) > 0 and
                len(self._aroon_down_values) > 0 and
                len(self._aroon_oscillator_values) > 0 and
                self._current_aroon_oscillator is not None)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update Aroon Oscillator analysis

        Args:
            bar (Bar): New bar data
        """
        # Extract OHLC data
        if hasattr(bar, 'high') and hasattr(bar, 'low'):
            high = bar.high
            low = bar.low
        else:
            high = bar.get('high', bar.get('close', 0.0))
            low = bar.get('low', bar.get('close', 0.0))

        # Update Aroon Oscillator calculation
        self._update_aroon_oscillator(high, low)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_aroon_oscillator(self, high: float, low: float):
        """Update the core Aroon Oscillator calculation with institutional enhancements"""
        self._highs.append(high)
        self._lows.append(low)

        if len(self._highs) >= self.aroon_config.aroon_period:
            # Calculate periods since highest high
            highs_list = list(self._highs)[-self.aroon_config.aroon_period:]
            max_high = max(highs_list)
            periods_since_high = self.aroon_config.aroon_period - 1 - highs_list.index(max_high)

            # Calculate periods since lowest low
            lows_list = list(self._lows)[-self.aroon_config.aroon_period:]
            min_low = min(lows_list)
            periods_since_low = self.aroon_config.aroon_period - 1 - lows_list.index(min_low)

            # Calculate Aroon Up: ((period - periods_since_high) / period) * 100
            self._current_aroon_up = ((self.aroon_config.aroon_period - periods_since_high) /
                                     self.aroon_config.aroon_period) * 100
            self._aroon_up_values.append(self._current_aroon_up)

            # Calculate Aroon Down: ((period - periods_since_low) / period) * 100
            self._current_aroon_down = ((self.aroon_config.aroon_period - periods_since_low) /
                                       self.aroon_config.aroon_period) * 100
            self._aroon_down_values.append(self._current_aroon_down)

            # Calculate Aroon Oscillator: Aroon Up - Aroon Down
            self._current_aroon_oscillator = self._current_aroon_up - self._current_aroon_down
            self._aroon_oscillator_values.append(self._current_aroon_oscillator)

            # Analyze Aroon Oscillator characteristics
            self._analyze_aroon_characteristics()

    def _analyze_aroon_characteristics(self):
        """Analyze Aroon Oscillator characteristics for institutional insights"""
        if not self.is_ready or len(self._aroon_oscillator_values) < 3:
            return

        oscillator_value = self._current_aroon_oscillator

        # Calculate trend direction and strength
        if oscillator_value > 50.0:
            self._trend_direction = 1  # Strong uptrend
            self._trend_strength = min(1.0, oscillator_value / 100.0)
        elif oscillator_value < -50.0:
            self._trend_direction = -1  # Strong downtrend
            self._trend_strength = min(1.0, abs(oscillator_value) / 100.0)
        else:
            self._trend_direction = 0  # Weak or no trend
            self._trend_strength = 0.0

        # Calculate trend consistency
        if len(self._aroon_oscillator_values) >= 5:
            recent_oscillator = list(self._aroon_oscillator_values)[-5:]
            consistency_score = 0

            for i in range(1, len(recent_oscillator)):
                if ((recent_oscillator[i] > 0 and recent_oscillator[i-1] > 0) or
                    (recent_oscillator[i] < 0 and recent_oscillator[i-1] < 0)):
                    consistency_score += 1

            self._trend_consistency = consistency_score / (len(recent_oscillator) - 1)

        # Calculate oscillator momentum
        if len(self._aroon_oscillator_values) >= 3:
            recent_values = list(self._aroon_oscillator_values)[-3:]
            self._oscillator_momentum = (recent_values[-1] - recent_values[-2]) - (recent_values[-2] - recent_values[-1])

        # Track overbought/oversold signals
        if oscillator_value >= self.aroon_config.overbought_level:
            self._overbought_signals += 1
        elif oscillator_value <= self.aroon_config.oversold_level:
            self._oversold_signals += 1

        # Calculate trend reversal probability
        if abs(oscillator_value) > 80.0 and self._trend_consistency < 0.3:
            self._trend_reversal_probability = 0.8  # Extreme reading with low consistency suggests reversal
        elif abs(oscillator_value) < 20.0 and self._trend_consistency > 0.7:
            self._trend_reversal_probability = 0.6  # Weak trend with high consistency suggests continuation
        else:
            self._trend_reversal_probability = 0.0

        # Calculate breakout probability
        if self._trend_strength > 0.7 and self._trend_consistency > 0.8:
            self._breakout_probability = min(1.0, self._trend_strength * self._trend_consistency)
        else:
            self._breakout_probability = 0.0

        # Calculate oscillator divergence
        if len(self._aroon_oscillator_values) >= 5 and len(self._highs) >= 5:
            recent_prices = list(self._highs)[-5:]  # Using highs as price proxy
            recent_oscillator = list(self._aroon_oscillator_values)[-5:]

            price_trend = recent_prices[-1] - recent_prices[0]
            oscillator_trend = recent_oscillator[-1] - recent_oscillator[0]

            if price_trend * oscillator_trend < 0:  # Opposite directions
                self._oscillator_divergence = min(1.0, abs(price_trend - oscillator_trend) / (abs(price_trend) + abs(oscillator_trend)))
            else:
                self._oscillator_divergence = 0.0

        # Calculate institutional Aroon analysis
        self._calculate_institutional_aroon()

    def _calculate_institutional_aroon(self):
        """Calculate institutional Aroon analysis based on oscillator characteristics"""
        if not self.is_ready:
            return

        # Institutional traders use Aroon for trend strength assessment
        base_aroon = 0.0

        if self._trend_strength > 0.7 and self._trend_consistency > 0.8:
            base_aroon = 0.9  # Strong, consistent trend
        elif self._trend_strength > 0.5 and self._trend_consistency > 0.6:
            base_aroon = 0.7  # Moderate trend with consistency
        elif self._trend_strength > 0.3:
            base_aroon = 0.5  # Weak trend

        self._institutional_aroon = base_aroon

        # Smart money oscillator considers trend strength and consistency
        smart_money_score = (
            self._trend_strength * 0.4 +
            self._trend_consistency * 0.3 +
            (1.0 - self._oscillator_divergence) * 0.3
        )
        self._smart_money_oscillator = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade Aroon Oscillator analysis"""
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

        oscillator_value = self._current_aroon_oscillator

        # Determine signal type based on Aroon Oscillator analysis
        signal_type = self._determine_aroon_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'trend_strength': self._trend_strength,
            'trend_consistency': self._trend_consistency,
            'oscillator_momentum': self._oscillator_momentum,
            'oscillator_divergence': self._oscillator_divergence,
            'breakout_probability': self._breakout_probability,
            'trend_reversal_probability': self._trend_reversal_probability,
            'institutional_aroon': self._institutional_aroon,
            'smart_money_oscillator': self._smart_money_oscillator
        }

        # Use Aroon Oscillator value as primary raw value
        raw_value = oscillator_value

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._suggested_sl,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Aroon_Oscillator",
                "aroon_period": self.aroon_config.aroon_period,
                "overbought_level": self.aroon_config.overbought_level,
                "oversold_level": self.aroon_config.oversold_level,
                "aroon_up": self._current_aroon_up,
                "aroon_down": self._current_aroon_down,
                "trend_direction": self._trend_direction,
                "trend_strength": self._trend_strength,
                "trend_consistency": self._trend_consistency,
                "oscillator_momentum": self._oscillator_momentum,
                "oscillator_divergence": self._oscillator_divergence,
                "overbought_signals": self._overbought_signals,
                "oversold_signals": self._oversold_signals,
                "breakout_probability": self._breakout_probability,
                "trend_reversal_probability": self._trend_reversal_probability,
                "institutional_aroon": self._institutional_aroon,
                "smart_money_oscillator": self._smart_money_oscillator,
                "is_ready": self.is_ready
            }
        )

    def _determine_aroon_signal(self) -> SignalType:
        """Determine signal type based on Aroon Oscillator analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        oscillator_value = self._current_aroon_oscillator

        # Strong bullish signals
        if (oscillator_value > 50.0 and
            self._trend_strength > 0.7 and
            self._trend_consistency > 0.8 and
            self._oscillator_divergence < 0.3):
            return SignalType.STRONG_BULLISH

        # Strong bearish signals
        elif (oscillator_value < -50.0 and
              self._trend_strength > 0.7 and
              self._trend_consistency > 0.8 and
              self._oscillator_divergence < 0.3):
            return SignalType.STRONG_BEARISH

        # Moderate bullish signals
        elif oscillator_value > 30.0 and self._trend_strength > 0.5:
            return SignalType.BULLISH

        # Moderate bearish signals
        elif oscillator_value < -30.0 and self._trend_strength > 0.5:
            return SignalType.BEARISH

        # Reversal signals
        elif self._trend_reversal_probability > 0.6:
            if oscillator_value > 0:
                return SignalType.BEARISH  # Potential reversal from uptrend
            else:
                return SignalType.BULLISH  # Potential reversal from downtrend

        # Breakout signals
        elif self._breakout_probability > 0.6:
            if oscillator_value > 0:
                return SignalType.BULLISH
            else:
                return SignalType.BEARISH

        return SignalType.NEUTRAL

    @property
    def aroon_oscillator(self) -> float:
        """Get the current Aroon Oscillator value"""
        return self._current_aroon_oscillator if self.is_ready else 0.0

    @property
    def aroon_up(self) -> float:
        """Get the current Aroon Up value"""
        return self._current_aroon_up if self._current_aroon_up is not None else 0.0

    @property
    def aroon_down(self) -> float:
        """Get the current Aroon Down value"""
        return self._current_aroon_down if self._current_aroon_down is not None else 0.0

    @property
    def trend_direction(self) -> int:
        """Get the current trend direction (-1, 0, 1)"""
        return self._trend_direction

    @property
    def trend_strength(self) -> float:
        """Get the current trend strength (0-1)"""
        return self._trend_strength

    @property
    def trend_consistency(self) -> float:
        """Get the current trend consistency (0-1)"""
        return self._trend_consistency

    @property
    def oscillator_momentum(self) -> float:
        """Get the current oscillator momentum"""
        return self._oscillator_momentum

    @property
    def oscillator_divergence(self) -> float:
        """Get the current oscillator divergence (0-1)"""
        return self._oscillator_divergence

    @property
    def overbought_signals(self) -> int:
        """Get the count of overbought signals"""
        return self._overbought_signals

    @property
    def oversold_signals(self) -> int:
        """Get the count of oversold signals"""
        return self._oversold_signals

    @property
    def breakout_probability(self) -> float:
        """Get the breakout probability (0-1)"""
        return self._breakout_probability

    @property
    def trend_reversal_probability(self) -> float:
        """Get the trend reversal probability (0-1)"""
        return self._trend_reversal_probability

    @property
    def institutional_aroon(self) -> float:
        """Get the institutional Aroon score (0-1)"""
        return self._institutional_aroon

    @property
    def smart_money_oscillator(self) -> float:
        """Get the smart money oscillator score (0-1)"""
        return self._smart_money_oscillator

    def is_strong_uptrend(self) -> bool:
        """Check if in strong uptrend"""
        if not self.is_ready:
            return False
        return self._trend_direction == 1 and self._trend_strength > 0.7

    def is_strong_downtrend(self) -> bool:
        """Check if in strong downtrend"""
        if not self.is_ready:
            return False
        return self._trend_direction == -1 and self._trend_strength > 0.7

    def is_trend_consistent(self) -> bool:
        """Check if trend is consistent"""
        return self._trend_consistency > 0.7

    def is_overbought(self) -> bool:
        """Check if oscillator is overbought"""
        if not self.is_ready:
            return False
        return self._current_aroon_oscillator >= self.aroon_config.overbought_level

    def is_oversold(self) -> bool:
        """Check if oscillator is oversold"""
        if not self.is_ready:
            return False
        return self._current_aroon_oscillator <= self.aroon_config.oversold_level

    def is_divergence_present(self) -> bool:
        """Check if oscillator divergence is present"""
        return self._oscillator_divergence > 0.6

    def is_breakout_likely(self) -> bool:
        """Check if breakout is likely"""
        return self._breakout_probability > 0.6

    def is_reversal_likely(self) -> bool:
        """Check if trend reversal is likely"""
        return self._trend_reversal_probability > 0.6

    def is_institutional_trend(self) -> bool:
        """Check if trend is institutional-grade"""
        return self._institutional_aroon > 0.7

    def get_aroon_oscillator_info(self) -> Dict[str, Any]:
        """Get comprehensive Aroon Oscillator information"""
        return {
            "oscillator_value": self.aroon_oscillator,
            "aroon_up": self.aroon_up,
            "aroon_down": self.aroon_down,
            "trend_analysis": {
                "direction": self._trend_direction,
                "strength": self._trend_strength,
                "consistency": self._trend_consistency
            },
            "oscillator_analysis": {
                "momentum": self._oscillator_momentum,
                "divergence": self._oscillator_divergence,
                "overbought_signals": self._overbought_signals,
                "oversold_signals": self._oversold_signals
            },
            "probability_analysis": {
                "breakout_probability": self._breakout_probability,
                "trend_reversal_probability": self._trend_reversal_probability
            },
            "institutional_analysis": {
                "aroon": self._institutional_aroon,
                "smart_money_oscillator": self._smart_money_oscillator
            },
            "metadata": {
                "period": self.aroon_config.aroon_period,
                "overbought_level": self.aroon_config.overbought_level,
                "oversold_level": self.aroon_config.oversold_level,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._highs.clear()
        self._lows.clear()
        self._aroon_up_values.clear()
        self._aroon_down_values.clear()
        self._aroon_oscillator_values.clear()
        self._current_aroon_up = None
        self._current_aroon_down = None
        self._current_aroon_oscillator = None
        self._trend_direction = 0
        self._trend_strength = 0.0
        self._trend_consistency = 0.0
        self._oscillator_momentum = 0.0
        self._oscillator_divergence = 0.0
        self._overbought_signals = 0
        self._oversold_signals = 0
        self._breakout_probability = 0.0
        self._trend_reversal_probability = 0.0
        self._institutional_aroon = 0.0
        self._smart_money_oscillator = 0.0