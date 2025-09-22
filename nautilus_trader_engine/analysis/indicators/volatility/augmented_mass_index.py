"""
Institutional-Grade Augmented Mass Index Indicator

This module implements an enhanced Mass Index indicator with institutional-grade features:
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
class AugmentedMassIndexConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Mass Index"""
    mass_period: int = 25
    ema_period: int = 9
    setup_threshold: float = 26.5
    reversal_threshold: float = 27.0


class AugmentedMassIndex(AugmentedIndicator):
    """
    Institutional-grade Augmented Mass Index indicator implementing 5-pillar architecture.

    Features:
    - Range expansion/contraction analysis for reversal detection
    - Setup and reversal signal identification
    - Market regime classification based on volatility patterns
    - Institutional reversal timing
    - Smart money volatility analysis
    - Automated risk management
    """

    def __init__(self, config: AugmentedMassIndexConfig = None):
        if config is None:
            config = AugmentedMassIndexConfig()

        super().__init__(config)
        self.mass_config = config

        # Mass Index specific state
        self._highs = deque(maxlen=self.config.buffer_size)
        self._lows = deque(maxlen=self.config.buffer_size)
        self._ranges = deque(maxlen=self.config.buffer_size)
        self._ema_ranges = deque(maxlen=self.config.buffer_size)
        self._ema_ema_ranges = deque(maxlen=self.config.buffer_size)
        self._ratios = deque(maxlen=self.config.buffer_size)
        self._mass_values = deque(maxlen=self.config.buffer_size)
        self._current_mass = None

        # Reversal analysis
        self._setup_signals = 0
        self._reversal_signals = 0
        self._bullish_reversal_probability = 0.0
        self._bearish_reversal_probability = 0.0

        # Volatility analysis
        self._volatility_convergence = 0.0
        self._range_expansion = 0.0
        self._range_contraction = 0.0

        # Market structure
        self._reversal_setup = False
        self._reversal_triggered = False
        self._setup_duration = 0

        # Institutional analysis
        self._institutional_reversal = 0.0
        self._smart_money_setup = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Mass Index is ready to provide signals"""
        return len(self._mass_values) > 0 and self._current_mass is not None

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update Mass Index analysis

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

        # Update Mass Index calculation
        self._update_mass_index(high, low)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_mass_index(self, high: float, low: float):
        """Update the core Mass Index calculation with institutional enhancements"""
        # Calculate trading range
        trading_range = high - low
        self._highs.append(high)
        self._lows.append(low)
        self._ranges.append(trading_range)

        if len(self._ranges) >= self.mass_config.mass_period:
            # Calculate EMA of trading ranges
            ranges_list = list(self._ranges)[-self.mass_config.mass_period:]
            ema_range = self._calculate_ema(ranges_list, self.mass_config.ema_period)
            self._ema_ranges.append(ema_range)

            if len(self._ema_ranges) >= self.mass_config.ema_period:
                # Calculate EMA of EMA ranges
                ema_ranges_list = list(self._ema_ranges)[-self.mass_config.ema_period:]
                ema_ema_range = self._calculate_ema(ema_ranges_list, self.mass_config.ema_period)
                self._ema_ema_ranges.append(ema_ema_range)

                if ema_ema_range > 0:
                    # Calculate ratio
                    ratio = ema_range / ema_ema_range
                    self._ratios.append(ratio)

                    # Calculate Mass Index (sum of ratios over period)
                    if len(self._ratios) >= self.mass_config.mass_period:
                        ratios_sum = sum(list(self._ratios)[-self.mass_config.mass_period:])
                        self._current_mass = ratios_sum
                        self._mass_values.append(self._current_mass)

                        # Analyze Mass Index characteristics
                        self._analyze_mass_characteristics()

    def _calculate_ema(self, values: list, period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(values) < period:
            return sum(values) / len(values) if values else 0.0

        alpha = 2.0 / (period + 1)
        ema = values[0]

        for value in values[1:]:
            ema = alpha * value + (1 - alpha) * ema

        return ema

    def _analyze_mass_characteristics(self):
        """Analyze Mass Index characteristics for institutional insights"""
        if not self.is_ready or len(self._mass_values) < 3:
            return

        mass_value = self._current_mass

        # Detect setup signals (Mass Index > 26.5)
        if mass_value >= self.mass_config.setup_threshold:
            if not self._reversal_setup:
                self._reversal_setup = True
                self._setup_duration = 1
            else:
                self._setup_duration += 1

            self._setup_signals += 1
        else:
            if self._reversal_setup:
                self._reversal_setup = False
                self._setup_duration = 0

        # Detect reversal signals (Mass Index > 27.0)
        if mass_value >= self.mass_config.reversal_threshold:
            if not self._reversal_triggered:
                self._reversal_triggered = True
                self._reversal_signals += 1

                # Calculate reversal probabilities based on setup duration
                if self._setup_duration >= 3:
                    self._bullish_reversal_probability = min(1.0, self._setup_duration / 10.0)
                    self._bearish_reversal_probability = min(1.0, self._setup_duration / 10.0)
        else:
            self._reversal_triggered = False

        # Calculate volatility convergence
        if len(self._ranges) >= 5:
            recent_ranges = list(self._ranges)[-5:]
            range_std = statistics.stdev(recent_ranges) if len(recent_ranges) > 1 else 0
            range_mean = sum(recent_ranges) / len(recent_ranges)

            if range_mean > 0:
                self._volatility_convergence = 1.0 - (range_std / range_mean)
                self._volatility_convergence = max(0.0, min(1.0, self._volatility_convergence))

        # Calculate range expansion/contraction
        if len(self._ranges) >= 3:
            recent_ranges = list(self._ranges)[-3:]
            range_trend = (recent_ranges[-1] - recent_ranges[0]) / 3

            if range_trend > 0:
                self._range_expansion = min(1.0, range_trend / (recent_ranges[0] * 0.1))
                self._range_contraction = 0.0
            elif range_trend < 0:
                self._range_contraction = min(1.0, abs(range_trend) / (recent_ranges[0] * 0.1))
                self._range_expansion = 0.0
            else:
                self._range_expansion = 0.0
                self._range_contraction = 0.0

        # Calculate institutional reversal timing
        self._calculate_institutional_reversal()

    def _calculate_institutional_reversal(self):
        """Calculate institutional reversal timing based on Mass Index analysis"""
        if not self.is_ready:
            return

        # Institutional traders use Mass Index for timing major reversals
        base_reversal = 0.0

        if self._reversal_triggered and self._setup_duration >= 5:
            base_reversal = 0.9  # Strong reversal setup
        elif self._reversal_setup and self._setup_duration >= 3:
            base_reversal = 0.7  # Good reversal setup
        elif mass_value > 25.0:
            base_reversal = 0.5  # Potential reversal setup

        self._institutional_reversal = base_reversal

        # Smart money setup considers both setup quality and duration
        smart_money_score = (
            self._volatility_convergence * 0.3 +
            self._institutional_reversal * 0.4 +
            (self._setup_duration / 10.0) * 0.3
        )
        self._smart_money_setup = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade Mass Index analysis"""
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

        mass_value = self._current_mass

        # Determine signal type based on Mass Index analysis
        signal_type = self._determine_mass_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'volatility_convergence': self._volatility_convergence,
            'range_expansion': self._range_expansion,
            'range_contraction': self._range_contraction,
            'bullish_reversal_probability': self._bullish_reversal_probability,
            'bearish_reversal_probability': self._bearish_reversal_probability,
            'institutional_reversal': self._institutional_reversal,
            'smart_money_setup': self._smart_money_setup
        }

        # Use Mass Index value as primary raw value
        raw_value = mass_value

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._suggested_sl,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Mass_Index",
                "mass_period": self.mass_config.mass_period,
                "ema_period": self.mass_config.ema_period,
                "setup_threshold": self.mass_config.setup_threshold,
                "reversal_threshold": self.mass_config.reversal_threshold,
                "reversal_setup": self._reversal_setup,
                "reversal_triggered": self._reversal_triggered,
                "setup_duration": self._setup_duration,
                "setup_signals": self._setup_signals,
                "reversal_signals": self._reversal_signals,
                "volatility_convergence": self._volatility_convergence,
                "range_expansion": self._range_expansion,
                "range_contraction": self._range_contraction,
                "bullish_reversal_probability": self._bullish_reversal_probability,
                "bearish_reversal_probability": self._bearish_reversal_probability,
                "institutional_reversal": self._institutional_reversal,
                "smart_money_setup": self._smart_money_setup,
                "is_ready": self.is_ready
            }
        )

    def _determine_mass_signal(self) -> SignalType:
        """Determine signal type based on Mass Index analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        mass_value = self._current_mass

        # Strong reversal signals
        if (self._reversal_triggered and
            self._setup_duration >= 5 and
            (self._bullish_reversal_probability > 0.7 or self._bearish_reversal_probability > 0.7)):
            return SignalType.STRONG_BULLISH if self._bullish_reversal_probability > self._bearish_reversal_probability else SignalType.STRONG_BEARISH

        # Moderate reversal signals
        elif self._reversal_triggered and self._setup_duration >= 3:
            return SignalType.BULLISH if self._bullish_reversal_probability > self._bearish_reversal_probability else SignalType.BEARISH

        # Setup signals
        elif self._reversal_setup and mass_value >= self.mass_config.setup_threshold:
            return SignalType.BULLISH  # Setup often precedes bullish reversals

        # High Mass Index signals
        elif mass_value >= self.mass_config.reversal_threshold:
            return SignalType.BULLISH  # High values often signal reversals

        return SignalType.NEUTRAL

    @property
    def mass_index(self) -> float:
        """Get the current Mass Index value"""
        return self._current_mass if self.is_ready else 0.0

    @property
    def reversal_setup(self) -> bool:
        """Return True if reversal setup is active"""
        return self._reversal_setup

    @property
    def reversal_triggered(self) -> bool:
        """Return True if reversal is triggered"""
        return self._reversal_triggered

    @property
    def setup_duration(self) -> int:
        """Get the current setup duration"""
        return self._setup_duration

    @property
    def setup_signals(self) -> int:
        """Get the count of setup signals"""
        return self._setup_signals

    @property
    def reversal_signals(self) -> int:
        """Get the count of reversal signals"""
        return self._reversal_signals

    @property
    def volatility_convergence(self) -> float:
        """Get the volatility convergence score (0-1)"""
        return self._volatility_convergence

    @property
    def range_expansion(self) -> float:
        """Get the range expansion score (0-1)"""
        return self._range_expansion

    @property
    def range_contraction(self) -> float:
        """Get the range contraction score (0-1)"""
        return self._range_contraction

    @property
    def bullish_reversal_probability(self) -> float:
        """Get the bullish reversal probability (0-1)"""
        return self._bullish_reversal_probability

    @property
    def bearish_reversal_probability(self) -> float:
        """Get the bearish reversal probability (0-1)"""
        return self._bearish_reversal_probability

    @property
    def institutional_reversal(self) -> float:
        """Get the institutional reversal score (0-1)"""
        return self._institutional_reversal

    @property
    def smart_money_setup(self) -> float:
        """Get the smart money setup score (0-1)"""
        return self._smart_money_setup

    def is_reversal_setup(self) -> bool:
        """Check if reversal setup is active"""
        return self._reversal_setup

    def is_reversal_triggered(self) -> bool:
        """Check if reversal is triggered"""
        return self._reversal_triggered

    def is_strong_setup(self) -> bool:
        """Check if setup is strong (duration >= 5)"""
        return self._setup_duration >= 5

    def is_volatility_converging(self) -> bool:
        """Check if volatility is converging"""
        return self._volatility_convergence > 0.7

    def is_range_expanding(self) -> bool:
        """Check if range is expanding"""
        return self._range_expansion > 0.6

    def is_range_contracting(self) -> bool:
        """Check if range is contracting"""
        return self._range_contraction > 0.6

    def is_bullish_reversal_likely(self) -> bool:
        """Check if bullish reversal is likely"""
        return self._bullish_reversal_probability > 0.6

    def is_bearish_reversal_likely(self) -> bool:
        """Check if bearish reversal is likely"""
        return self._bearish_reversal_probability > 0.6

    def get_mass_index_info(self) -> Dict[str, Any]:
        """Get comprehensive Mass Index information"""
        return {
            "mass_value": self.mass_index,
            "reversal_analysis": {
                "setup": self._reversal_setup,
                "triggered": self._reversal_triggered,
                "setup_duration": self._setup_duration,
                "setup_signals": self._setup_signals,
                "reversal_signals": self._reversal_signals
            },
            "volatility_analysis": {
                "convergence": self._volatility_convergence,
                "range_expansion": self._range_expansion,
                "range_contraction": self._range_contraction
            },
            "reversal_probability": {
                "bullish": self._bullish_reversal_probability,
                "bearish": self._bearish_reversal_probability
            },
            "institutional_analysis": {
                "reversal": self._institutional_reversal,
                "smart_money_setup": self._smart_money_setup
            },
            "metadata": {
                "mass_period": self.mass_config.mass_period,
                "ema_period": self.mass_config.ema_period,
                "setup_threshold": self.mass_config.setup_threshold,
                "reversal_threshold": self.mass_config.reversal_threshold,
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
        self._ema_ema_ranges.clear()
        self._ratios.clear()
        self._mass_values.clear()
        self._current_mass = None
        self._setup_signals = 0
        self._reversal_signals = 0
        self._bullish_reversal_probability = 0.0
        self._bearish_reversal_probability = 0.0
        self._volatility_convergence = 0.0
        self._range_expansion = 0.0
        self._range_contraction = 0.0
        self._reversal_setup = False
        self._reversal_triggered = False
        self._setup_duration = 0
        self._institutional_reversal = 0.0
        self._smart_money_setup = 0.0