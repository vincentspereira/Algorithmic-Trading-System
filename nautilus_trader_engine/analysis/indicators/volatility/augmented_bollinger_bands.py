"""
Institutional-Grade Augmented Bollinger Bands Indicator

This module implements an enhanced Bollinger Bands indicator with institutional-grade features:
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

# from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import (
    AugmentedIndicator,
    AugmentedIndicatorConfig,
    IndicatorSignal,
    SignalType,
)


@dataclass
class AugmentedBollingerBandsConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Bollinger Bands"""
    period: int = 20
    std_dev_multiplier: float = 2.0
    squeeze_threshold: float = 0.8
    expansion_threshold: float = 1.2


class AugmentedBollingerBands(AugmentedIndicator):
    """
    Institutional-grade Augmented Bollinger Bands indicator implementing 5-pillar architecture.

    Features:
    - Band width analysis for volatility assessment
    - Squeeze and expansion detection for breakout signals
    - Mean reversion and breakout probability analysis
    - Market regime adaptation based on band behavior
    - Multi-timeframe convergence for institutional confirmation
    - Smart money band analysis for accumulation/distribution detection
    - Automated risk management for volatility-based strategies
    """

    def __init__(self, config: AugmentedBollingerBandsConfig = None):
        if config is None:
            config = AugmentedBollingerBandsConfig()

        super().__init__(config)
        self.bb_config = config

        # Bollinger Bands specific state
        self._prices = deque(maxlen=self.config.buffer_size)
        self._sma_values = deque(maxlen=self.config.buffer_size)
        self._upper_band_values = deque(maxlen=self.config.buffer_size)
        self._lower_band_values = deque(maxlen=self.config.buffer_size)
        self._band_width_values = deque(maxlen=self.config.buffer_size)

        self._current_sma = None
        self._current_upper = None
        self._current_lower = None
        self._current_band_width = None

        # Band analysis
        self._band_position = 0.0  # Price position within bands (-1 to 1)
        self._band_width_percentile = 0.0
        self._squeeze_signals = 0
        self._expansion_signals = 0

        # Volatility analysis
        self._volatility_regime = "normal"  # "low", "normal", "high", "extreme"
        self._volatility_trend = "stable"  # "increasing", "decreasing", "stable"
        self._volatility_momentum = 0.0

        # Signal analysis
        self._breakout_probability = 0.0
        self._mean_reversion_probability = 0.0
        self._trend_continuation_probability = 0.0

        # Market structure
        self._support_touches = 0
        self._resistance_touches = 0
        self._band_touches = 0

        # Institutional analysis
        self._institutional_bands = 0.0
        self._smart_money_bands = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Bollinger Bands is ready to provide signals"""
        return (len(self._sma_values) > 0 and
                self._current_sma is not None and
                self._current_upper is not None and
                self._current_lower is not None)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update Bollinger Bands analysis

        Args:
            bar (Bar): New bar data
        """
        # Extract price data
        if hasattr(bar, 'close'):
            price = bar.close
        else:
            price = bar.get('close', bar.get('price', 0.0))

        # Update Bollinger Bands calculation
        self._update_bollinger_bands(price)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_bollinger_bands(self, price: float):
        """Update the core Bollinger Bands calculation with institutional enhancements"""
        self._prices.append(price)

        if len(self._prices) >= self.bb_config.period:
            # Calculate SMA
            prices_list = list(self._prices)[-self.bb_config.period:]
            self._current_sma = sum(prices_list) / len(prices_list)
            self._sma_values.append(self._current_sma)

            # Calculate standard deviation
            if len(prices_list) > 1:
                std_dev = statistics.stdev(prices_list)
            else:
                std_dev = 0.0

            # Calculate bands
            self._current_upper = self._current_sma + (std_dev * self.bb_config.std_dev_multiplier)
            self._current_lower = self._current_sma - (std_dev * self.bb_config.std_dev_multiplier)

            self._upper_band_values.append(self._current_upper)
            self._lower_band_values.append(self._current_lower)

            # Calculate band width
            if self._current_sma != 0:
                self._current_band_width = (self._current_upper - self._current_lower) / self._current_sma
            else:
                self._current_band_width = 0.0

            self._band_width_values.append(self._current_band_width)

            # Analyze band characteristics
            self._analyze_band_characteristics(price)

    def _analyze_band_characteristics(self, current_price: float):
        """Analyze Bollinger Bands characteristics for institutional insights"""
        if not self.is_ready:
            return

        # Calculate price position within bands
        if self._current_upper != self._current_lower:
            self._band_position = (current_price - self._current_lower) / (self._current_upper - self._current_lower) * 2 - 1
            self._band_position = max(-1.0, min(1.0, self._band_position))
        else:
            self._band_position = 0.0

        # Calculate band width percentile
        if len(self._band_width_values) >= 10:
            band_widths = list(self._band_width_values)[-10:]
            sorted_widths = sorted(band_widths)
            current_width = self._current_band_width

            # Find percentile
            for i, width in enumerate(sorted_widths):
                if current_width <= width:
                    self._band_width_percentile = i / len(sorted_widths)
                    break
            else:
                self._band_width_percentile = 1.0

        # Detect squeeze and expansion
        if self._current_band_width < self.bb_config.squeeze_threshold:
            self._squeeze_signals += 1
            self._volatility_regime = "low"
        elif self._current_band_width > self.bb_config.expansion_threshold:
            self._expansion_signals += 1
            self._volatility_regime = "high"
        else:
            self._volatility_regime = "normal"

        # Analyze volatility trend
        if len(self._band_width_values) >= 3:
            recent_widths = list(self._band_width_values)[-3:]
            width_trend = (recent_widths[-1] - recent_widths[0]) / 3

            if width_trend > 0.01:
                self._volatility_trend = "increasing"
                self._volatility_momentum = width_trend
            elif width_trend < -0.01:
                self._volatility_trend = "decreasing"
                self._volatility_momentum = width_trend
            else:
                self._volatility_trend = "stable"
                self._volatility_momentum = 0.0

        # Calculate breakout and mean reversion probabilities
        if abs(self._band_position) > 0.8:
            # Price near bands - potential breakout
            self._breakout_probability = min(1.0, abs(self._band_position))
            self._mean_reversion_probability = 0.0
        elif abs(self._band_position) < 0.2:
            # Price near middle - potential mean reversion
            self._mean_reversion_probability = 1.0 - abs(self._band_position) * 5
            self._breakout_probability = 0.0
        else:
            self._breakout_probability = 0.0
            self._mean_reversion_probability = 0.0

        # Trend continuation probability
        if self._volatility_trend == "increasing" and self._band_width_percentile > 0.7:
            self._trend_continuation_probability = 0.8
        elif self._volatility_trend == "decreasing" and self._band_width_percentile < 0.3:
            self._trend_continuation_probability = 0.6
        else:
            self._trend_continuation_probability = 0.4

        # Track band touches
        if abs(current_price - self._current_upper) / current_price < 0.001:
            self._resistance_touches += 1
            self._band_touches += 1
        elif abs(current_price - self._current_lower) / current_price < 0.001:
            self._support_touches += 1
            self._band_touches += 1

        # Calculate institutional band analysis
        self._calculate_institutional_bands()

    def _calculate_institutional_bands(self):
        """Calculate institutional band analysis based on Bollinger Bands characteristics"""
        if not self.is_ready:
            return

        # Institutional traders use Bollinger Bands for volatility and breakout analysis
        base_bands = 0.0

        if self._volatility_regime == "low" and self._band_width_percentile < 0.2:
            base_bands = 0.9  # Strong squeeze setup for breakout
        elif self._volatility_regime == "high" and self._band_width_percentile > 0.8:
            base_bands = 0.7  # High volatility expansion
        elif self._breakout_probability > 0.7:
            base_bands = 0.8  # Strong breakout signal
        elif self._mean_reversion_probability > 0.6:
            base_bands = 0.6  # Good mean reversion setup

        self._institutional_bands = base_bands

        # Smart money bands considers band position and volatility
        smart_money_score = (
            (1.0 - abs(self._band_position)) * 0.3 +  # Central positioning preferred
            self._band_width_percentile * 0.3 +       # Width percentile
            self._breakout_probability * 0.2 +        # Breakout potential
            self._institutional_bands * 0.2           # Institutional confidence
        )
        self._smart_money_bands = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade Bollinger Bands analysis"""
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

        # Use band width as primary raw value
        raw_value = self._current_band_width if self._current_band_width is not None else 0.0

        # Determine signal type based on Bollinger Bands analysis
        signal_type = self._determine_bollinger_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'band_position': self._band_position,
            'band_width_percentile': self._band_width_percentile,
            'breakout_probability': self._breakout_probability,
            'mean_reversion_probability': self._mean_reversion_probability,
            'trend_continuation_probability': self._trend_continuation_probability,
            'volatility_momentum': self._volatility_momentum,
            'institutional_bands': self._institutional_bands,
            'smart_money_bands': self._smart_money_bands
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
                "indicator": "Bollinger_Bands",
                "period": self.bb_config.period,
                "std_dev_multiplier": self.bb_config.std_dev_multiplier,
                "squeeze_threshold": self.bb_config.squeeze_threshold,
                "expansion_threshold": self.bb_config.expansion_threshold,
                "sma": self._current_sma,
                "upper_band": self._current_upper,
                "lower_band": self._current_lower,
                "band_width": self._current_band_width,
                "band_position": self._band_position,
                "band_width_percentile": self._band_width_percentile,
                "volatility_regime": self._volatility_regime,
                "volatility_trend": self._volatility_trend,
                "volatility_momentum": self._volatility_momentum,
                "squeeze_signals": self._squeeze_signals,
                "expansion_signals": self._expansion_signals,
                "breakout_probability": self._breakout_probability,
                "mean_reversion_probability": self._mean_reversion_probability,
                "trend_continuation_probability": self._trend_continuation_probability,
                "support_touches": self._support_touches,
                "resistance_touches": self._resistance_touches,
                "band_touches": self._band_touches,
                "institutional_bands": self._institutional_bands,
                "smart_money_bands": self._smart_money_bands,
                "is_ready": self.is_ready
            }
        )

    def _determine_bollinger_signal(self) -> SignalType:
        """Determine signal type based on Bollinger Bands analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong breakout signals
        if (self._breakout_probability > 0.8 and
            self._volatility_regime == "high" and
            self._band_width_percentile > 0.7):
            if self._band_position > 0:
                return SignalType.STRONG_BULLISH
            else:
                return SignalType.STRONG_BEARISH

        # Moderate breakout signals
        elif self._breakout_probability > 0.6:
            if self._band_position > 0:
                return SignalType.BULLISH
            else:
                return SignalType.BEARISH

        # Mean reversion signals
        elif (self._mean_reversion_probability > 0.7 and
              self._volatility_regime == "normal"):
            if self._band_position > 0:
                return SignalType.BEARISH  # Price near upper band
            else:
                return SignalType.BULLISH  # Price near lower band

        # Squeeze signals (potential breakout setup)
        elif (self._volatility_regime == "low" and
              self._band_width_percentile < 0.3 and
              self._squeeze_signals > 0):
            return SignalType.BULLISH  # Squeeze often precedes breakouts

        # Trend continuation signals
        elif (self._trend_continuation_probability > 0.7 and
              self._volatility_trend == "increasing"):
            if self._band_position > 0:
                return SignalType.BULLISH
            else:
                return SignalType.BEARISH

        return SignalType.NEUTRAL

    @property
    def sma(self) -> float:
        """Get the current SMA value"""
        return self._current_sma if self.is_ready else 0.0

    @property
    def upper_band(self) -> float:
        """Get the current upper band value"""
        return self._current_upper if self.is_ready else 0.0

    @property
    def lower_band(self) -> float:
        """Get the current lower band value"""
        return self._current_lower if self.is_ready else 0.0

    @property
    def band_width(self) -> float:
        """Get the current band width"""
        return self._current_band_width if self.is_ready else 0.0

    @property
    def band_position(self) -> float:
        """Get the current band position (-1 to 1)"""
        return self._band_position

    @property
    def band_width_percentile(self) -> float:
        """Get the current band width percentile (0-1)"""
        return self._band_width_percentile

    @property
    def volatility_regime(self) -> str:
        """Get the current volatility regime"""
        return self._volatility_regime

    @property
    def volatility_trend(self) -> str:
        """Get the current volatility trend"""
        return self._volatility_trend

    @property
    def volatility_momentum(self) -> float:
        """Get the current volatility momentum"""
        return self._volatility_momentum

    @property
    def squeeze_signals(self) -> int:
        """Get the count of squeeze signals"""
        return self._squeeze_signals

    @property
    def expansion_signals(self) -> int:
        """Get the count of expansion signals"""
        return self._expansion_signals

    @property
    def breakout_probability(self) -> float:
        """Get the breakout probability (0-1)"""
        return self._breakout_probability

    @property
    def mean_reversion_probability(self) -> float:
        """Get the mean reversion probability (0-1)"""
        return self._mean_reversion_probability

    @property
    def trend_continuation_probability(self) -> float:
        """Get the trend continuation probability (0-1)"""
        return self._trend_continuation_probability

    @property
    def support_touches(self) -> int:
        """Get the count of support touches"""
        return self._support_touches

    @property
    def resistance_touches(self) -> int:
        """Get the count of resistance touches"""
        return self._resistance_touches

    @property
    def band_touches(self) -> int:
        """Get the count of band touches"""
        return self._band_touches

    @property
    def institutional_bands(self) -> float:
        """Get the institutional bands score (0-1)"""
        return self._institutional_bands

    @property
    def smart_money_bands(self) -> float:
        """Get the smart money bands score (0-1)"""
        return self._smart_money_bands

    def is_price_near_upper_band(self) -> bool:
        """Check if price is near upper band"""
        return self._band_position > 0.8

    def is_price_near_lower_band(self) -> bool:
        """Check if price is near lower band"""
        return self._band_position < -0.8

    def is_price_in_middle(self) -> bool:
        """Check if price is in the middle of bands"""
        return abs(self._band_position) < 0.2

    def is_squeeze_active(self) -> bool:
        """Check if squeeze is active"""
        return self._volatility_regime == "low" and self._band_width_percentile < 0.3

    def is_expansion_active(self) -> bool:
        """Check if expansion is active"""
        return self._volatility_regime == "high" and self._band_width_percentile > 0.7

    def is_breakout_likely(self) -> bool:
        """Check if breakout is likely"""
        return self._breakout_probability > 0.6

    def is_mean_reversion_likely(self) -> bool:
        """Check if mean reversion is likely"""
        return self._mean_reversion_probability > 0.6

    def is_trend_continuation_likely(self) -> bool:
        """Check if trend continuation is likely"""
        return self._trend_continuation_probability > 0.6

    def is_institutional_setup(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_bands > 0.7

    def get_bollinger_bands_info(self) -> Dict[str, Any]:
        """Get comprehensive Bollinger Bands information"""
        return {
            "bands": {
                "sma": self.sma,
                "upper_band": self.upper_band,
                "lower_band": self.lower_band,
                "band_width": self.band_width
            },
            "analysis": {
                "band_position": self._band_position,
                "band_width_percentile": self._band_width_percentile,
                "volatility_regime": self._volatility_regime,
                "volatility_trend": self._volatility_trend,
                "volatility_momentum": self._volatility_momentum
            },
            "signals": {
                "squeeze_signals": self._squeeze_signals,
                "expansion_signals": self._expansion_signals,
                "breakout_probability": self._breakout_probability,
                "mean_reversion_probability": self._mean_reversion_probability,
                "trend_continuation_probability": self._trend_continuation_probability
            },
            "market_structure": {
                "support_touches": self._support_touches,
                "resistance_touches": self._resistance_touches,
                "band_touches": self._band_touches
            },
            "institutional_analysis": {
                "bands": self._institutional_bands,
                "smart_money_bands": self._smart_money_bands
            },
            "metadata": {
                "period": self.bb_config.period,
                "std_dev_multiplier": self.bb_config.std_dev_multiplier,
                "squeeze_threshold": self.bb_config.squeeze_threshold,
                "expansion_threshold": self.bb_config.expansion_threshold,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._prices.clear()
        self._sma_values.clear()
        self._upper_band_values.clear()
        self._lower_band_values.clear()
        self._band_width_values.clear()
        self._current_sma = None
        self._current_upper = None
        self._current_lower = None
        self._current_band_width = None
        self._band_position = 0.0
        self._band_width_percentile = 0.0
        self._squeeze_signals = 0
        self._expansion_signals = 0
        self._volatility_regime = "normal"
        self._volatility_trend = "stable"
        self._volatility_momentum = 0.0
        self._breakout_probability = 0.0
        self._mean_reversion_probability = 0.0
        self._trend_continuation_probability = 0.0
        self._support_touches = 0
        self._resistance_touches = 0
        self._band_touches = 0
        self._institutional_bands = 0.0
        self._smart_money_bands = 0.0