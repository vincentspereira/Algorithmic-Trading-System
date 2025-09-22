"""
Institutional-Grade Augmented Ultimate Oscillator Indicator

This module implements an enhanced Ultimate Oscillator indicator with institutional-grade features:
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
class AugmentedUltimateOscillatorConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Ultimate Oscillator"""
    short_period: int = 7
    medium_period: int = 14
    long_period: int = 28
    overbought_level: float = 70.0
    oversold_level: float = 30.0


class AugmentedUltimateOscillator(AugmentedIndicator):
    """
    Institutional-grade Augmented Ultimate Oscillator indicator implementing 5-pillar architecture.

    Features:
    - Multi-timeframe momentum analysis for reduced false signals
    - Buying pressure vs. true range analysis
    - Market regime adaptation based on timeframe alignment
    - Multi-timeframe convergence for institutional confirmation
    - Smart money flow analysis across timeframes
    - Automated risk management for momentum-based strategies
    """

    def __init__(self, config: AugmentedUltimateOscillatorConfig = None):
        if config is None:
            config = AugmentedUltimateOscillatorConfig()

        super().__init__(config)
        self.uo_config = config

        # Ultimate Oscillator specific state
        self._prices = deque(maxlen=self.config.buffer_size)
        self._highs = deque(maxlen=self.config.buffer_size)
        self._lows = deque(maxlen=self.config.buffer_size)

        # Timeframe-specific calculations
        self._short_bp_values = deque(maxlen=self.config.buffer_size)  # Buying Pressure
        self._short_tr_values = deque(maxlen=self.config.buffer_size)  # True Range
        self._medium_bp_values = deque(maxlen=self.config.buffer_size)
        self._medium_tr_values = deque(maxlen=self.config.buffer_size)
        self._long_bp_values = deque(maxlen=self.config.buffer_size)
        self._long_tr_values = deque(maxlen=self.config.buffer_size)

        # Ultimate Oscillator values
        self._uo_values = deque(maxlen=self.config.buffer_size)
        self._current_uo = None

        # Momentum analysis
        self._momentum_strength = 0.0
        self._momentum_direction = 0  # -1, 0, 1 for down, neutral, up
        self._timeframe_alignment = 0.0

        # Signal analysis
        self._divergence_detected = False
        self._divergence_type = "none"  # "bullish", "bearish", "none"
        self._divergence_confidence = 0.0

        # Market structure
        self._overbought_signals = 0
        self._oversold_signals = 0
        self._breakout_probability = 0.0

        # Institutional analysis
        self._institutional_confidence = 0.0
        self._smart_money_alignment = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Ultimate Oscillator is ready to provide signals"""
        return len(self._uo_values) > 0 and self._current_uo is not None

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update Ultimate Oscillator analysis

        Args:
            bar (Bar): New bar data
        """
        # Extract OHLC data
        if hasattr(bar, 'close') and hasattr(bar, 'high') and hasattr(bar, 'low'):
            close = bar.close
            high = bar.high
            low = bar.low
        else:
            close = bar.get('close', bar.get('price', 0.0))
            high = bar.get('high', close)
            low = bar.get('low', close)

        # Update Ultimate Oscillator calculation
        self._update_ultimate_oscillator(close, high, low)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_ultimate_oscillator(self, close: float, high: float, low: float):
        """Update the core Ultimate Oscillator calculation with institutional enhancements"""
        self._prices.append(close)
        self._highs.append(high)
        self._lows.append(low)

        if len(self._prices) >= self.uo_config.long_period + 1:
            # Calculate buying pressure and true range for each timeframe
            self._calculate_timeframe_components()

            # Calculate Ultimate Oscillator
            if (self._short_bp_values and self._short_tr_values and
                self._medium_bp_values and self._medium_tr_values and
                self._long_bp_values and self._long_tr_values):

                # Average True Range percentages
                short_avg = sum(list(self._short_tr_values)[-self.uo_config.short_period:]) / self.uo_config.short_period
                medium_avg = sum(list(self._medium_tr_values)[-self.uo_config.medium_period:]) / self.uo_config.medium_period
                long_avg = sum(list(self._long_tr_values)[-self.uo_config.long_period:]) / self.uo_config.long_period

                # Buying Pressure percentages
                short_bp = sum(list(self._short_bp_values)[-self.uo_config.short_period:]) / self.uo_config.short_period
                medium_bp = sum(list(self._medium_bp_values)[-self.uo_config.medium_period:]) / self.uo_config.medium_period
                long_bp = sum(list(self._long_bp_values)[-self.uo_config.long_period:]) / self.uo_config.long_period

                # Calculate Ultimate Oscillator
                if short_avg > 0 and medium_avg > 0 and long_avg > 0:
                    uo = (4 * short_bp / short_avg + 2 * medium_bp / medium_avg + long_bp / long_avg) / 7 * 100
                    self._current_uo = uo
                    self._uo_values.append(uo)

                    # Analyze Ultimate Oscillator characteristics
                    self._analyze_uo_characteristics()

    def _calculate_timeframe_components(self):
        """Calculate buying pressure and true range for each timeframe"""
        if len(self._prices) < 2:
            return

        # Current and previous values
        current_close = self._prices[-1]
        previous_close = self._prices[-2]
        current_high = self._highs[-1]
        current_low = self._lows[-1]

        # Calculate True Range
        tr1 = current_high - current_low
        tr2 = abs(current_high - previous_close)
        tr3 = abs(current_low - previous_close)
        true_range = max(tr1, tr2, tr3)

        # Calculate Buying Pressure
        if current_close > previous_close:
            buying_pressure = current_close - current_low
        else:
            buying_pressure = 0.0

        # Store in respective timeframe buffers
        self._short_bp_values.append(buying_pressure)
        self._short_tr_values.append(true_range)
        self._medium_bp_values.append(buying_pressure)
        self._medium_tr_values.append(true_range)
        self._long_bp_values.append(buying_pressure)
        self._long_tr_values.append(true_range)

    def _analyze_uo_characteristics(self):
        """Analyze Ultimate Oscillator characteristics for institutional insights"""
        if not self.is_ready or len(self._uo_values) < 3:
            return

        uo_value = self._current_uo

        # Calculate momentum strength and direction
        recent_uo = list(self._uo_values)[-3:]
        momentum_slope = (recent_uo[-1] - recent_uo[0]) / 3

        if momentum_slope > 0.5:
            self._momentum_direction = 1  # Up momentum
            self._momentum_strength = min(1.0, momentum_slope / 2.0)
        elif momentum_slope < -0.5:
            self._momentum_direction = -1  # Down momentum
            self._momentum_strength = min(1.0, abs(momentum_slope) / 2.0)
        else:
            self._momentum_direction = 0  # Neutral momentum
            self._momentum_strength = 0.0

        # Calculate timeframe alignment
        if len(self._uo_values) >= 5:
            # Check alignment across recent values
            recent_values = list(self._uo_values)[-5:]
            alignment_score = 1.0 - (statistics.stdev(recent_values) / 50.0)  # Normalize around 50
            self._timeframe_alignment = max(0.0, min(1.0, alignment_score))

        # Detect overbought/oversold conditions
        if uo_value >= self.uo_config.overbought_level:
            self._overbought_signals += 1
        elif uo_value <= self.uo_config.oversold_level:
            self._oversold_signals += 1

        # Calculate breakout probability
        if uo_value > 70.0 or uo_value < 30.0:
            self._breakout_probability = min(1.0, abs(uo_value - 50.0) / 30.0)
        else:
            self._breakout_probability = 0.0

        # Detect divergences
        self._detect_uo_divergences()

        # Calculate institutional confidence
        self._calculate_institutional_confidence()

    def _detect_uo_divergences(self):
        """Detect divergences between Ultimate Oscillator and price"""
        if not self.is_ready or len(self._prices) < 5 or len(self._uo_values) < 5:
            return

        # Simple divergence detection
        recent_prices = list(self._prices)[-5:]
        recent_uo = list(self._uo_values)[-5:]

        price_trend = recent_prices[-1] - recent_prices[-3]
        uo_trend = recent_uo[-1] - recent_uo[-3]

        # Bullish divergence: price falling, UO rising
        if price_trend < 0 and uo_trend > 0 and recent_uo[-1] < 40.0:
            self._divergence_detected = True
            self._divergence_type = "bullish"
            self._divergence_confidence = min(1.0, abs(uo_trend) / 10.0)

        # Bearish divergence: price rising, UO falling
        elif price_trend > 0 and uo_trend < 0 and recent_uo[-1] > 60.0:
            self._divergence_detected = True
            self._divergence_type = "bearish"
            self._divergence_confidence = min(1.0, abs(uo_trend) / 10.0)

        else:
            self._divergence_detected = False
            self._divergence_type = "none"
            self._divergence_confidence = 0.0

    def _calculate_institutional_confidence(self):
        """Calculate institutional confidence based on multi-timeframe alignment"""
        if not self.is_ready:
            return

        # Institutional traders value multi-timeframe confirmation
        base_confidence = self._timeframe_alignment * 0.6 + self._momentum_strength * 0.4

        # Boost confidence for extreme readings (potential turning points)
        if self._current_uo > 70.0 or self._current_uo < 30.0:
            base_confidence *= 1.2

        # Reduce confidence for middle readings (indecision)
        elif 40.0 <= self._current_uo <= 60.0:
            base_confidence *= 0.8

        self._institutional_confidence = min(1.0, base_confidence)

        # Smart money alignment based on divergence and momentum
        smart_money_score = (
            self._divergence_confidence * 0.4 +
            self._momentum_strength * 0.3 +
            self._timeframe_alignment * 0.3
        )
        self._smart_money_alignment = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade Ultimate Oscillator analysis"""
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

        uo_value = self._current_uo

        # Determine signal type based on Ultimate Oscillator analysis
        signal_type = self._determine_uo_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'momentum_strength': self._momentum_strength,
            'timeframe_alignment': self._timeframe_alignment,
            'breakout_probability': self._breakout_probability,
            'divergence_confidence': self._divergence_confidence,
            'institutional_confidence': self._institutional_confidence,
            'smart_money_alignment': self._smart_money_alignment
        }

        # Use UO value as primary raw value
        raw_value = uo_value

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._suggested_sl,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Ultimate_Oscillator",
                "short_period": self.uo_config.short_period,
                "medium_period": self.uo_config.medium_period,
                "long_period": self.uo_config.long_period,
                "overbought_level": self.uo_config.overbought_level,
                "oversold_level": self.uo_config.oversold_level,
                "momentum_direction": self._momentum_direction,
                "momentum_strength": self._momentum_strength,
                "timeframe_alignment": self._timeframe_alignment,
                "divergence_detected": self._divergence_detected,
                "divergence_type": self._divergence_type,
                "divergence_confidence": self._divergence_confidence,
                "breakout_probability": self._breakout_probability,
                "overbought_signals": self._overbought_signals,
                "oversold_signals": self._oversold_signals,
                "institutional_confidence": self._institutional_confidence,
                "smart_money_alignment": self._smart_money_alignment,
                "is_ready": self.is_ready
            }
        )

    def _determine_uo_signal(self) -> SignalType:
        """Determine signal type based on Ultimate Oscillator analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        uo_value = self._current_uo

        # Strong buy signals (oversold with divergence)
        if (uo_value < 30.0 and
            self._divergence_type == "bullish" and
            self._divergence_confidence > 0.6):
            return SignalType.STRONG_BULLISH

        # Strong sell signals (overbought with divergence)
        elif (uo_value > 70.0 and
              self._divergence_type == "bearish" and
              self._divergence_confidence > 0.6):
            return SignalType.STRONG_BEARISH

        # Moderate buy signals (oversold)
        elif uo_value <= self.uo_config.oversold_level:
            return SignalType.BULLISH

        # Moderate sell signals (overbought)
        elif uo_value >= self.uo_config.overbought_level:
            return SignalType.BEARISH

        # Momentum-based signals
        elif self._momentum_strength > 0.6 and self._timeframe_alignment > 0.7:
            if self._momentum_direction == 1:
                return SignalType.BULLISH
            elif self._momentum_direction == -1:
                return SignalType.BEARISH

        return SignalType.NEUTRAL

    @property
    def ultimate_oscillator(self) -> float:
        """Get the current Ultimate Oscillator value"""
        return self._current_uo if self.is_ready else 0.0

    @property
    def momentum_strength(self) -> float:
        """Get the current momentum strength (0-1)"""
        return self._momentum_strength

    @property
    def momentum_direction(self) -> int:
        """Get the current momentum direction (-1, 0, 1)"""
        return self._momentum_direction

    @property
    def timeframe_alignment(self) -> float:
        """Get the timeframe alignment score (0-1)"""
        return self._timeframe_alignment

    @property
    def divergence_detected(self) -> bool:
        """Return True if divergence is detected"""
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
    def breakout_probability(self) -> float:
        """Get the breakout probability (0-1)"""
        return self._breakout_probability

    @property
    def overbought_signals(self) -> int:
        """Get the count of overbought signals"""
        return self._overbought_signals

    @property
    def oversold_signals(self) -> int:
        """Get the count of oversold signals"""
        return self._oversold_signals

    @property
    def institutional_confidence(self) -> float:
        """Get the institutional confidence score (0-1)"""
        return self._institutional_confidence

    @property
    def smart_money_alignment(self) -> float:
        """Get the smart money alignment score (0-1)"""
        return self._smart_money_alignment

    def is_overbought(self) -> bool:
        """Check if Ultimate Oscillator indicates overbought conditions"""
        if not self.is_ready:
            return False
        return self._current_uo >= self.uo_config.overbought_level

    def is_oversold(self) -> bool:
        """Check if Ultimate Oscillator indicates oversold conditions"""
        if not self.is_ready:
            return False
        return self._current_uo <= self.uo_config.oversold_level

    def is_bullish_divergence(self) -> bool:
        """Check if bullish divergence is detected"""
        return self._divergence_type == "bullish" and self._divergence_detected

    def is_bearish_divergence(self) -> bool:
        """Check if bearish divergence is detected"""
        return self._divergence_type == "bearish" and self._divergence_detected

    def is_timeframe_aligned(self) -> bool:
        """Check if timeframes are well aligned"""
        return self._timeframe_alignment > 0.7

    def get_ultimate_oscillator_info(self) -> Dict[str, Any]:
        """Get comprehensive Ultimate Oscillator information"""
        return {
            "uo_value": self.ultimate_oscillator,
            "momentum_analysis": {
                "direction": self._momentum_direction,
                "strength": self._momentum_strength,
                "timeframe_alignment": self._timeframe_alignment
            },
            "divergence_analysis": {
                "detected": self._divergence_detected,
                "type": self._divergence_type,
                "confidence": self._divergence_confidence
            },
            "market_analysis": {
                "breakout_probability": self._breakout_probability,
                "overbought_signals": self._overbought_signals,
                "oversold_signals": self._oversold_signals
            },
            "institutional_analysis": {
                "confidence": self._institutional_confidence,
                "smart_money_alignment": self._smart_money_alignment
            },
            "metadata": {
                "short_period": self.uo_config.short_period,
                "medium_period": self.uo_config.medium_period,
                "long_period": self.uo_config.long_period,
                "overbought_level": self.uo_config.overbought_level,
                "oversold_level": self.uo_config.oversold_level,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._prices.clear()
        self._highs.clear()
        self._lows.clear()
        self._short_bp_values.clear()
        self._short_tr_values.clear()
        self._medium_bp_values.clear()
        self._medium_tr_values.clear()
        self._long_bp_values.clear()
        self._long_tr_values.clear()
        self._uo_values.clear()
        self._current_uo = None
        self._momentum_strength = 0.0
        self._momentum_direction = 0
        self._timeframe_alignment = 0.0
        self._divergence_detected = False
        self._divergence_type = "none"
        self._divergence_confidence = 0.0
        self._overbought_signals = 0
        self._oversold_signals = 0
        self._breakout_probability = 0.0
        self._institutional_confidence = 0.0
        self._smart_money_alignment = 0.0