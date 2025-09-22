"""
Institutional-Grade Augmented True Strength Index (TSI) Indicator

This module implements an enhanced TSI indicator with institutional-grade features:
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
class AugmentedTSIConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented TSI"""
    momentum_period: int = 25
    smoothing_period: int = 13
    signal_period: int = 8
    overbought_level: float = 25.0
    oversold_level: float = -25.0


class AugmentedTSI(AugmentedIndicator):
    """
    Institutional-grade Augmented True Strength Index indicator implementing 5-pillar architecture.

    Features:
    - Double-smoothed momentum analysis for trend identification
    - Signal line crossover analysis for timing
    - Market regime adaptation based on trend strength
    - Multi-timeframe convergence for institutional confirmation
    - Smart money flow analysis with momentum confirmation
    - Automated risk management for momentum-based strategies
    """

    def __init__(self, config: AugmentedTSIConfig = None):
        if config is None:
            config = AugmentedTSIConfig()

        super().__init__(config)
        self.tsi_config = config

        # TSI specific state
        self._prices = deque(maxlen=self.config.buffer_size)

        # Momentum calculations
        self._momentum_values = deque(maxlen=self.config.buffer_size)
        self._double_smoothed_momentum = deque(maxlen=self.config.buffer_size)
        self._tsi_values = deque(maxlen=self.config.buffer_size)
        self._signal_values = deque(maxlen=self.config.buffer_size)

        self._current_tsi = None
        self._current_signal = None

        # Trend analysis
        self._trend_direction = 0  # -1, 0, 1 for down, sideways, up
        self._trend_strength = 0.0
        self._momentum_phase = "neutral"  # "bullish", "bearish", "neutral"

        # Signal analysis
        self._signal_crossover = "none"  # "bullish", "bearish", "none"
        self._crossover_confidence = 0.0
        self._signal_divergence = 0.0

        # Market structure
        self._overbought_signals = 0
        self._oversold_signals = 0
        self._breakout_probability = 0.0

        # Institutional analysis
        self._institutional_momentum = 0.0
        self._smart_money_confirmation = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if TSI is ready to provide signals"""
        return (len(self._tsi_values) > 0 and
                len(self._signal_values) > 0 and
                self._current_tsi is not None and
                self._current_signal is not None)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update TSI analysis

        Args:
            bar (Bar): New bar data
        """
        # Extract price
        if hasattr(bar, 'close'):
            price = bar.close
        else:
            price = bar.get('close', bar.get('price', 0.0))

        # Update TSI calculation
        self._update_tsi(price)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_tsi(self, price: float):
        """Update the core TSI calculation with institutional enhancements"""
        self._prices.append(price)

        if len(self._prices) >= self.tsi_config.momentum_period + 1:
            # Calculate momentum (price change)
            momentum = price - self._prices[-self.tsi_config.momentum_period - 1]
            self._momentum_values.append(momentum)

            # Double smooth the momentum
            if len(self._momentum_values) >= self.tsi_config.smoothing_period:
                # First smoothing (EMA of momentum)
                momentum_ema1 = self._calculate_ema(list(self._momentum_values)[-self.tsi_config.smoothing_period:],
                                                   self.tsi_config.smoothing_period)

                if len(self._double_smoothed_momentum) >= self.tsi_config.smoothing_period:
                    # Second smoothing (EMA of first EMA)
                    momentum_ema2 = self._calculate_ema(list(self._double_smoothed_momentum)[-self.tsi_config.smoothing_period:],
                                                       self.tsi_config.smoothing_period)

                    self._double_smoothed_momentum.append(momentum_ema1)

                    # Calculate TSI
                    if momentum_ema2 != 0:
                        tsi = (momentum_ema1 / abs(momentum_ema2)) * 100
                        self._current_tsi = tsi
                        self._tsi_values.append(tsi)

                        # Calculate signal line
                        if len(self._tsi_values) >= self.tsi_config.signal_period:
                            signal = self._calculate_ema(list(self._tsi_values)[-self.tsi_config.signal_period:],
                                                        self.tsi_config.signal_period)
                            self._current_signal = signal
                            self._signal_values.append(signal)

                            # Analyze TSI characteristics
                            self._analyze_tsi_characteristics()

    def _calculate_ema(self, values: list, period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(values) < period:
            return sum(values) / len(values) if values else 0.0

        alpha = 2.0 / (period + 1)
        ema = values[0]

        for value in values[1:]:
            ema = alpha * value + (1 - alpha) * ema

        return ema

    def _analyze_tsi_characteristics(self):
        """Analyze TSI characteristics for institutional insights"""
        if not self.is_ready or len(self._tsi_values) < 3:
            return

        tsi_value = self._current_tsi
        signal_value = self._current_signal

        # Calculate trend direction and strength
        recent_tsi = list(self._tsi_values)[-3:]
        tsi_slope = (recent_tsi[-1] - recent_tsi[0]) / 3

        if tsi_slope > 0.5:
            self._trend_direction = 1  # Uptrend
            self._trend_strength = min(1.0, tsi_slope / 5.0)
        elif tsi_slope < -0.5:
            self._trend_direction = -1  # Downtrend
            self._trend_strength = min(1.0, abs(tsi_slope) / 5.0)
        else:
            self._trend_direction = 0  # Sideways
            self._trend_strength = 0.0

        # Determine momentum phase
        if tsi_value > 20.0:
            self._momentum_phase = "bullish"
        elif tsi_value < -20.0:
            self._momentum_phase = "bearish"
        else:
            self._momentum_phase = "neutral"

        # Detect signal line crossovers
        if len(self._tsi_values) >= 2 and len(self._signal_values) >= 2:
            prev_tsi = self._tsi_values[-2]
            prev_signal = self._signal_values[-2]

            # Bullish crossover
            if prev_tsi <= prev_signal and tsi_value > signal_value:
                self._signal_crossover = "bullish"
                self._crossover_confidence = min(1.0, abs(tsi_value - signal_value) / 10.0)

            # Bearish crossover
            elif prev_tsi >= prev_signal and tsi_value < signal_value:
                self._signal_crossover = "bearish"
                self._crossover_confidence = min(1.0, abs(tsi_value - signal_value) / 10.0)

            else:
                self._signal_crossover = "none"
                self._crossover_confidence = 0.0

        # Detect overbought/oversold conditions
        if tsi_value >= self.tsi_config.overbought_level:
            self._overbought_signals += 1
        elif tsi_value <= self.tsi_config.oversold_level:
            self._oversold_signals += 1

        # Calculate breakout probability
        if abs(tsi_value) > 30.0:
            self._breakout_probability = min(1.0, abs(tsi_value) / 40.0)
        else:
            self._breakout_probability = 0.0

        # Calculate signal divergence
        if len(self._tsi_values) >= 5 and len(self._prices) >= 5:
            recent_prices = list(self._prices)[-5:]
            recent_tsi = list(self._tsi_values)[-5:]

            price_trend = recent_prices[-1] - recent_prices[0]
            tsi_trend = recent_tsi[-1] - recent_tsi[0]

            if price_trend * tsi_trend < 0:  # Opposite directions
                self._signal_divergence = min(1.0, abs(price_trend - tsi_trend) / (abs(price_trend) + abs(tsi_trend)))
            else:
                self._signal_divergence = 0.0

        # Calculate institutional momentum
        self._calculate_institutional_momentum()

    def _calculate_institutional_momentum(self):
        """Calculate institutional momentum based on TSI analysis"""
        if not self.is_ready:
            return

        # Institutional momentum combines trend strength and signal consistency
        base_momentum = (
            self._trend_strength * 0.4 +
            self._crossover_confidence * 0.3 +
            (1.0 - self._signal_divergence) * 0.3
        )

        # Boost for strong momentum phases
        if abs(self._current_tsi) > 25.0:
            base_momentum *= 1.2

        self._institutional_momentum = min(1.0, base_momentum)

        # Smart money confirmation based on signal quality
        smart_money_score = (
            self._crossover_confidence * 0.4 +
            self._trend_strength * 0.3 +
            (1.0 - self._signal_divergence) * 0.3
        )
        self._smart_money_confirmation = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade TSI analysis"""
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

        tsi_value = self._current_tsi

        # Determine signal type based on TSI analysis
        signal_type = self._determine_tsi_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'trend_strength': self._trend_strength,
            'crossover_confidence': self._crossover_confidence,
            'breakout_probability': self._breakout_probability,
            'signal_divergence': self._signal_divergence,
            'institutional_momentum': self._institutional_momentum,
            'smart_money_confirmation': self._smart_money_confirmation
        }

        # Use TSI value as primary raw value
        raw_value = tsi_value

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._suggested_sl,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "TSI",
                "momentum_period": self.tsi_config.momentum_period,
                "smoothing_period": self.tsi_config.smoothing_period,
                "signal_period": self.tsi_config.signal_period,
                "overbought_level": self.tsi_config.overbought_level,
                "oversold_level": self.tsi_config.oversold_level,
                "trend_direction": self._trend_direction,
                "trend_strength": self._trend_strength,
                "momentum_phase": self._momentum_phase,
                "signal_crossover": self._signal_crossover,
                "crossover_confidence": self._crossover_confidence,
                "signal_divergence": self._signal_divergence,
                "breakout_probability": self._breakout_probability,
                "overbought_signals": self._overbought_signals,
                "oversold_signals": self._oversold_signals,
                "institutional_momentum": self._institutional_momentum,
                "smart_money_confirmation": self._smart_money_confirmation,
                "current_signal": self._current_signal,
                "is_ready": self.is_ready
            }
        )

    def _determine_tsi_signal(self) -> SignalType:
        """Determine signal type based on TSI analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        tsi_value = self._current_tsi

        # Strong buy signals (oversold with bullish crossover)
        if (tsi_value < -25.0 and
            self._signal_crossover == "bullish" and
            self._crossover_confidence > 0.6):
            return SignalType.STRONG_BULLISH

        # Strong sell signals (overbought with bearish crossover)
        elif (tsi_value > 25.0 and
              self._signal_crossover == "bearish" and
              self._crossover_confidence > 0.6):
            return SignalType.STRONG_BEARISH

        # Moderate buy signals (oversold or bullish crossover)
        elif (tsi_value <= self.tsi_config.oversold_level or
              (self._signal_crossover == "bullish" and self._crossover_confidence > 0.4)):
            return SignalType.BULLISH

        # Moderate sell signals (overbought or bearish crossover)
        elif (tsi_value >= self.tsi_config.overbought_level or
              (self._signal_crossover == "bearish" and self._crossover_confidence > 0.4)):
            return SignalType.BEARISH

        # Trend-based signals
        elif self._trend_strength > 0.6 and self._institutional_momentum > 0.7:
            if self._trend_direction == 1:
                return SignalType.BULLISH
            elif self._trend_direction == -1:
                return SignalType.BEARISH

        return SignalType.NEUTRAL

    @property
    def tsi(self) -> float:
        """Get the current TSI value"""
        return self._current_tsi if self.is_ready else 0.0

    @property
    def signal(self) -> float:
        """Get the current signal line value"""
        return self._current_signal if self.is_ready else 0.0

    @property
    def trend_direction(self) -> int:
        """Get the current trend direction (-1, 0, 1)"""
        return self._trend_direction

    @property
    def trend_strength(self) -> float:
        """Get the current trend strength (0-1)"""
        return self._trend_strength

    @property
    def momentum_phase(self) -> str:
        """Get the current momentum phase"""
        return self._momentum_phase

    @property
    def signal_crossover(self) -> str:
        """Get the current signal crossover type"""
        return self._signal_crossover

    @property
    def crossover_confidence(self) -> float:
        """Get the crossover confidence (0-1)"""
        return self._crossover_confidence

    @property
    def signal_divergence(self) -> float:
        """Get the signal divergence (0-1)"""
        return self._signal_divergence

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
    def institutional_momentum(self) -> float:
        """Get the institutional momentum score (0-1)"""
        return self._institutional_momentum

    @property
    def smart_money_confirmation(self) -> float:
        """Get the smart money confirmation score (0-1)"""
        return self._smart_money_confirmation

    def is_overbought(self) -> bool:
        """Check if TSI indicates overbought conditions"""
        if not self.is_ready:
            return False
        return self._current_tsi >= self.tsi_config.overbought_level

    def is_oversold(self) -> bool:
        """Check if TSI indicates oversold conditions"""
        if not self.is_ready:
            return False
        return self._current_tsi <= self.tsi_config.oversold_level

    def is_bullish_crossover(self) -> bool:
        """Check if bullish crossover is detected"""
        return self._signal_crossover == "bullish" and self._crossover_confidence > 0.4

    def is_bearish_crossover(self) -> bool:
        """Check if bearish crossover is detected"""
        return self._signal_crossover == "bearish" and self._crossover_confidence > 0.4

    def is_high_momentum(self) -> bool:
        """Check if TSI shows high momentum"""
        return self._trend_strength > 0.7 and self._institutional_momentum > 0.7

    def get_tsi_info(self) -> Dict[str, Any]:
        """Get comprehensive TSI information"""
        return {
            "tsi_value": self.tsi,
            "signal_value": self.signal,
            "trend_analysis": {
                "direction": self._trend_direction,
                "strength": self._trend_strength,
                "phase": self._momentum_phase
            },
            "signal_analysis": {
                "crossover": self._signal_crossover,
                "crossover_confidence": self._crossover_confidence,
                "divergence": self._signal_divergence
            },
            "market_analysis": {
                "breakout_probability": self._breakout_probability,
                "overbought_signals": self._overbought_signals,
                "oversold_signals": self._oversold_signals
            },
            "institutional_analysis": {
                "momentum": self._institutional_momentum,
                "smart_money_confirmation": self._smart_money_confirmation
            },
            "metadata": {
                "momentum_period": self.tsi_config.momentum_period,
                "smoothing_period": self.tsi_config.smoothing_period,
                "signal_period": self.tsi_config.signal_period,
                "overbought_level": self.tsi_config.overbought_level,
                "oversold_level": self.tsi_config.oversold_level,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._prices.clear()
        self._momentum_values.clear()
        self._double_smoothed_momentum.clear()
        self._tsi_values.clear()
        self._signal_values.clear()
        self._current_tsi = None
        self._current_signal = None
        self._trend_direction = 0
        self._trend_strength = 0.0
        self._momentum_phase = "neutral"
        self._signal_crossover = "none"
        self._crossover_confidence = 0.0
        self._signal_divergence = 0.0
        self._overbought_signals = 0
        self._oversold_signals = 0
        self._breakout_probability = 0.0
        self._institutional_momentum = 0.0
        self._smart_money_confirmation = 0.0