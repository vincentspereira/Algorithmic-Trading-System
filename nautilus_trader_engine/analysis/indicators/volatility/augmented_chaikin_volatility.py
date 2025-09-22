"""
Institutional-Grade Augmented Chaikin Volatility Indicator

This module implements an enhanced Chaikin Volatility indicator with institutional-grade features:
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
class AugmentedChaikinVolatilityConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Chaikin Volatility"""
    chaikin_period: int = 10
    roc_period: int = 12
    overbought_level: float = 0.15  # 15% increase in volatility
    oversold_level: float = -0.15   # 15% decrease in volatility


class AugmentedChaikinVolatility(AugmentedIndicator):
    """
    Institutional-grade Augmented Chaikin Volatility indicator implementing 5-pillar architecture.

    Features:
    - Rate of change of trading range analysis
    - Volatility expansion/contraction detection
    - Market regime classification
    - Breakout and breakdown probability analysis
    - Institutional volatility timing
    - Automated risk management
    """

    def __init__(self, config: AugmentedChaikinVolatilityConfig = None):
        if config is None:
            config = AugmentedChaikinVolatilityConfig()

        super().__init__(config)
        self.chaikin_config = config

        # Chaikin Volatility specific state
        self._highs = deque(maxlen=self.config.buffer_size)
        self._lows = deque(maxlen=self.config.buffer_size)
        self._ranges = deque(maxlen=self.config.buffer_size)
        self._ema_ranges = deque(maxlen=self.config.buffer_size)
        self._chaikin_values = deque(maxlen=self.config.buffer_size)
        self._current_chaikin = None

        # Volatility analysis
        self._volatility_direction = 0  # -1, 0, 1 for decreasing, neutral, increasing
        self._volatility_magnitude = 0.0
        self._volatility_acceleration = 0.0

        # Market structure
        self._expansion_signals = 0
        self._contraction_signals = 0
        self._breakout_probability = 0.0
        self._breakdown_probability = 0.0

        # Trend analysis
        self._volatility_trend = "neutral"  # "expanding", "contracting", "stable"
        self._volatility_regime = "normal"  # "low", "normal", "high", "extreme"

        # Institutional analysis
        self._institutional_timing = 0.0
        self._smart_money_volatility = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Chaikin Volatility is ready to provide signals"""
        return len(self._chaikin_values) > 0 and self._current_chaikin is not None

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update Chaikin Volatility analysis

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

        # Update Chaikin Volatility calculation
        self._update_chaikin_volatility(high, low)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_chaikin_volatility(self, high: float, low: float):
        """Update the core Chaikin Volatility calculation with institutional enhancements"""
        # Calculate trading range
        trading_range = high - low
        self._highs.append(high)
        self._lows.append(low)
        self._ranges.append(trading_range)

        if len(self._ranges) >= self.chaikin_config.chaikin_period:
            # Calculate EMA of trading ranges
            ranges_list = list(self._ranges)[-self.chaikin_config.chaikin_period:]
            ema_range = self._calculate_ema(ranges_list, self.chaikin_config.chaikin_period)
            self._ema_ranges.append(ema_range)

            if len(self._ema_ranges) >= self.chaikin_config.roc_period + 1:
                # Calculate ROC of EMA ranges
                past_ema = self._ema_ranges[-self.chaikin_config.roc_period - 1]
                current_ema = self._ema_ranges[-1]

                if past_ema > 0:
                    self._current_chaikin = ((current_ema - past_ema) / past_ema) * 100
                    self._chaikin_values.append(self._current_chaikin)

                    # Analyze Chaikin characteristics
                    self._analyze_chaikin_characteristics()

    def _calculate_ema(self, values: list, period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(values) < period:
            return sum(values) / len(values) if values else 0.0

        alpha = 2.0 / (period + 1)
        ema = values[0]

        for value in values[1:]:
            ema = alpha * value + (1 - alpha) * ema

        return ema

    def _analyze_chaikin_characteristics(self):
        """Analyze Chaikin Volatility characteristics for institutional insights"""
        if not self.is_ready or len(self._chaikin_values) < 3:
            return

        chaikin_value = self._current_chaikin

        # Calculate volatility direction and magnitude
        if chaikin_value > 5.0:
            self._volatility_direction = 1  # Increasing volatility
            self._volatility_magnitude = min(1.0, chaikin_value / 20.0)
        elif chaikin_value < -5.0:
            self._volatility_direction = -1  # Decreasing volatility
            self._volatility_magnitude = min(1.0, abs(chaikin_value) / 20.0)
        else:
            self._volatility_direction = 0  # Neutral volatility
            self._volatility_magnitude = 0.0

        # Calculate volatility acceleration
        if len(self._chaikin_values) >= 3:
            recent_chaikin = list(self._chaikin_values)[-3:]
            self._volatility_acceleration = (recent_chaikin[-1] - recent_chaikin[-2]) - (recent_chaikin[-2] - recent_chaikin[-1])

        # Determine volatility trend
        if chaikin_value > 10.0:
            self._volatility_trend = "expanding"
        elif chaikin_value < -10.0:
            self._volatility_trend = "contracting"
        else:
            self._volatility_trend = "stable"

        # Classify volatility regime
        abs_value = abs(chaikin_value)
        if abs_value < 5.0:
            self._volatility_regime = "low"
        elif abs_value < 15.0:
            self._volatility_regime = "normal"
        elif abs_value < 25.0:
            self._volatility_regime = "high"
        else:
            self._volatility_regime = "extreme"

        # Track expansion/contraction signals
        if chaikin_value >= self.chaikin_config.overbought_level * 100:
            self._expansion_signals += 1
        elif chaikin_value <= self.chaikin_config.oversold_level * 100:
            self._contraction_signals += 1

        # Calculate breakout/breakdown probabilities
        if chaikin_value > 15.0:
            self._breakout_probability = min(1.0, chaikin_value / 30.0)
            self._breakdown_probability = 0.0
        elif chaikin_value < -15.0:
            self._breakdown_probability = min(1.0, abs(chaikin_value) / 30.0)
            self._breakout_probability = 0.0
        else:
            self._breakout_probability = 0.0
            self._breakdown_probability = 0.0

        # Calculate institutional timing
        self._calculate_institutional_timing()

    def _calculate_institutional_timing(self):
        """Calculate institutional timing based on Chaikin Volatility analysis"""
        if not self.is_ready:
            return

        # Institutional traders use volatility expansion for entry timing
        base_timing = 0.0

        if self._volatility_trend == "expanding" and self._volatility_magnitude > 0.5:
            base_timing = 0.8  # High volatility expansion often precedes breakouts
        elif self._volatility_trend == "contracting" and self._volatility_magnitude > 0.3:
            base_timing = 0.6  # Volatility contraction often precedes breakouts
        elif self._volatility_regime == "extreme":
            base_timing = 0.9  # Extreme volatility often signals major moves

        self._institutional_timing = base_timing

        # Smart money volatility considers both magnitude and direction
        smart_money_score = (
            self._volatility_magnitude * 0.4 +
            self._breakout_probability * 0.3 +
            self._institutional_timing * 0.3
        )
        self._smart_money_volatility = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade Chaikin Volatility analysis"""
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

        chaikin_value = self._current_chaikin

        # Determine signal type based on Chaikin Volatility analysis
        signal_type = self._determine_chaikin_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'volatility_magnitude': self._volatility_magnitude,
            'volatility_acceleration': self._volatility_acceleration,
            'breakout_probability': self._breakout_probability,
            'breakdown_probability': self._breakdown_probability,
            'institutional_timing': self._institutional_timing,
            'smart_money_volatility': self._smart_money_volatility
        }

        # Use Chaikin value as primary raw value
        raw_value = chaikin_value

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._suggested_sl,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Chaikin_Volatility",
                "chaikin_period": self.chaikin_config.chaikin_period,
                "roc_period": self.chaikin_config.roc_period,
                "overbought_level": self.chaikin_config.overbought_level,
                "oversold_level": self.chaikin_config.oversold_level,
                "volatility_direction": self._volatility_direction,
                "volatility_magnitude": self._volatility_magnitude,
                "volatility_acceleration": self._volatility_acceleration,
                "volatility_trend": self._volatility_trend,
                "volatility_regime": self._volatility_regime,
                "expansion_signals": self._expansion_signals,
                "contraction_signals": self._contraction_signals,
                "breakout_probability": self._breakout_probability,
                "breakdown_probability": self._breakdown_probability,
                "institutional_timing": self._institutional_timing,
                "smart_money_volatility": self._smart_money_volatility,
                "is_ready": self.is_ready
            }
        )

    def _determine_chaikin_signal(self) -> SignalType:
        """Determine signal type based on Chaikin Volatility analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        chaikin_value = self._current_chaikin

        # Strong volatility expansion signals
        if chaikin_value > 20.0 and self._breakout_probability > 0.7:
            return SignalType.STRONG_BULLISH

        # Strong volatility contraction signals
        elif chaikin_value < -20.0 and self._breakdown_probability > 0.7:
            return SignalType.STRONG_BEARISH

        # Moderate volatility expansion signals
        elif chaikin_value >= self.chaikin_config.overbought_level * 100:
            return SignalType.BULLISH

        # Moderate volatility contraction signals
        elif chaikin_value <= self.chaikin_config.oversold_level * 100:
            return SignalType.BEARISH

        # High magnitude signals
        elif abs(chaikin_value) > 15.0:
            if chaikin_value > 0:
                return SignalType.BULLISH
            else:
                return SignalType.BEARISH

        return SignalType.NEUTRAL

    @property
    def chaikin_volatility(self) -> float:
        """Get the current Chaikin Volatility value"""
        return self._current_chaikin if self.is_ready else 0.0

    @property
    def volatility_direction(self) -> int:
        """Get the current volatility direction (-1, 0, 1)"""
        return self._volatility_direction

    @property
    def volatility_magnitude(self) -> float:
        """Get the current volatility magnitude (0-1)"""
        return self._volatility_magnitude

    @property
    def volatility_acceleration(self) -> float:
        """Get the current volatility acceleration"""
        return self._volatility_acceleration

    @property
    def volatility_trend(self) -> str:
        """Get the current volatility trend"""
        return self._volatility_trend

    @property
    def volatility_regime(self) -> str:
        """Get the current volatility regime"""
        return self._volatility_regime

    @property
    def expansion_signals(self) -> int:
        """Get the count of expansion signals"""
        return self._expansion_signals

    @property
    def contraction_signals(self) -> int:
        """Get the count of contraction signals"""
        return self._contraction_signals

    @property
    def breakout_probability(self) -> float:
        """Get the breakout probability (0-1)"""
        return self._breakout_probability

    @property
    def breakdown_probability(self) -> float:
        """Get the breakdown probability (0-1)"""
        return self._breakdown_probability

    @property
    def institutional_timing(self) -> float:
        """Get the institutional timing score (0-1)"""
        return self._institutional_timing

    @property
    def smart_money_volatility(self) -> float:
        """Get the smart money volatility score (0-1)"""
        return self._smart_money_volatility

    def is_volatility_expanding(self) -> bool:
        """Check if volatility is expanding"""
        if not self.is_ready:
            return False
        return self._volatility_direction == 1

    def is_volatility_contracting(self) -> bool:
        """Check if volatility is contracting"""
        if not self.is_ready:
            return False
        return self._volatility_direction == -1

    def is_high_volatility_regime(self) -> bool:
        """Check if in high volatility regime"""
        return self._volatility_regime in ["high", "extreme"]

    def is_breakout_likely(self) -> bool:
        """Check if breakout is likely"""
        return self._breakout_probability > 0.6

    def is_breakdown_likely(self) -> bool:
        """Check if breakdown is likely"""
        return self._breakdown_probability > 0.6

    def is_institutional_entry(self) -> bool:
        """Check if conditions are good for institutional entry"""
        return self._institutional_timing > 0.7

    def get_chaikin_volatility_info(self) -> Dict[str, Any]:
        """Get comprehensive Chaikin Volatility information"""
        return {
            "chaikin_value": self.chaikin_volatility,
            "volatility_analysis": {
                "direction": self._volatility_direction,
                "magnitude": self._volatility_magnitude,
                "acceleration": self._volatility_acceleration,
                "trend": self._volatility_trend,
                "regime": self._volatility_regime
            },
            "signal_analysis": {
                "expansion_signals": self._expansion_signals,
                "contraction_signals": self._contraction_signals,
                "breakout_probability": self._breakout_probability,
                "breakdown_probability": self._breakdown_probability
            },
            "institutional_analysis": {
                "timing": self._institutional_timing,
                "smart_money_volatility": self._smart_money_volatility
            },
            "metadata": {
                "chaikin_period": self.chaikin_config.chaikin_period,
                "roc_period": self.chaikin_config.roc_period,
                "overbought_level": self.chaikin_config.overbought_level,
                "oversold_level": self.chaikin_config.oversold_level,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._highs.clear()
        self._lows.clear()
        self._ranges.clear()
        self._ema_ranges.clear()
        self._chaikin_values.clear()
        self._current_chaikin = None
        self._volatility_direction = 0
        self._volatility_magnitude = 0.0
        self._volatility_acceleration = 0.0
        self._expansion_signals = 0
        self._contraction_signals = 0
        self._breakout_probability = 0.0
        self._breakdown_probability = 0.0
        self._volatility_trend = "neutral"
        self._volatility_regime = "normal"
        self._institutional_timing = 0.0
        self._smart_money_volatility = 0.0