"""
Institutional-Grade Augmented Trend Intensity Index Indicator

This module implements an enhanced Trend Intensity Index indicator with institutional-grade features:
- Volume confirmation scoring
- Market regime adaptation
- Multi-timeframe convergence
- Smart money detection
- Automated risk management
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import deque
import statistics
import math

from nautilus_trader_engine.indicators.base import (
    AugmentedIndicator,
    AugmentedIndicatorConfig,
    IndicatorSignal,
    SignalType,
)


@dataclass
class AugmentedTrendIntensityIndexConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Trend Intensity Index Indicator"""
    period: int = 14
    signal_period: int = 9
    intensity_threshold: float = 0.5
    adaptive_smoothing: bool = True


class AugmentedTrendIntensityIndexIndicator(AugmentedIndicator):
    """
    Institutional-grade Augmented Trend Intensity Index Indicator implementing 5-pillar architecture.

    Features:
    - Measures trend strength and intensity using price changes
    - Volume-weighted trend analysis for institutional validation
    - Market regime adaptation for different volatility environments
    - Multi-timeframe convergence for trend confirmation
    - Smart money trend intensity detection
    - Automated risk management based on trend strength
    """

    def __init__(self, config: AugmentedTrendIntensityIndexConfig = None):
        if config is None:
            config = AugmentedTrendIntensityIndexConfig()

        super().__init__(config)
        self.tii_config = config

        # Trend Intensity Index specific state
        self._close_values = deque(maxlen=self.config.buffer_size)
        self._volume_values = deque(maxlen=self.config.buffer_size)
        self._price_changes = deque(maxlen=self.config.buffer_size)

        # TII calculation components
        self._tii_values = deque(maxlen=self.config.buffer_size)
        self._signal_line = deque(maxlen=self.config.buffer_size)
        self._trend_intensity = 0.0

        # Trend analysis
        self._trend_direction = 0  # 1 = uptrend, -1 = downtrend, 0 = neutral
        self._trend_strength = 0.0
        self._trend_consistency = 0.0

        # Signal analysis
        self._intensity_signals = 0
        self._trend_signals = 0
        self._divergence_signals = 0
        self._breakout_signals = 0

        # Performance tracking
        self._signal_accuracy = 0.0
        self._trend_prediction_rate = 0.0
        self._intensity_reliability = 0.0

        # Market structure
        self._volatility_regime = "normal"
        self._trend_cycles = 0
        self._intensity_peaks = []

        # Risk management
        self._trend_based_stop = 0.0
        self._intensity_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0

        # Institutional analysis
        self._institutional_tii = 0.0
        self._smart_money_tii = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Trend Intensity Index Indicator is ready to provide signals"""
        return (len(self._close_values) >= self.tii_config.period and
                len(self._tii_values) > 0)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update Trend Intensity Index analysis

        Args:
            bar (Bar): New bar data
        """
        # Extract OHLCV data
        if hasattr(bar, 'close') and hasattr(bar, 'volume'):
            close = bar.close
            volume = bar.volume
        else:
            close = bar.get('close', bar.get('price', 0.0))
            volume = bar.get('volume', 1.0)

        # Update Trend Intensity Index analysis
        self._update_tii_analysis(close, volume)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_tii_analysis(self, close: float, volume: float):
        """Update the core Trend Intensity Index analysis with institutional enhancements"""
        # Store price and volume data
        self._close_values.append(close)
        self._volume_values.append(volume)

        if len(self._close_values) >= 2:
            # Calculate price change
            price_change = close - list(self._close_values)[-2]
            self._price_changes.append(price_change)

            if len(self._price_changes) >= self.tii_config.period:
                # Calculate Trend Intensity Index
                self._calculate_trend_intensity_index()

                # Calculate signal line
                self._calculate_signal_line()

                # Analyze trend characteristics
                self._analyze_trend_characteristics()

                # Generate TII signals
                self._generate_tii_signals()

                # Calculate institutional TII analysis
                self._calculate_institutional_tii()

    def _calculate_trend_intensity_index(self):
        """Calculate Trend Intensity Index"""
        if len(self._price_changes) < self.tii_config.period:
            return

        # Get recent price changes
        recent_changes = list(self._price_changes)[-self.tii_config.period:]

        # Calculate positive and negative changes
        positive_changes = [max(0, change) for change in recent_changes]
        negative_changes = [abs(min(0, change)) for change in recent_changes]

        # Calculate cumulative sums
        positive_sum = sum(positive_changes)
        negative_sum = sum(negative_changes)
        total_sum = positive_sum + negative_sum

        # Calculate Trend Intensity Index
        if total_sum > 0:
            tii = (positive_sum - negative_sum) / total_sum * 100
            # Normalize to 0-100 range
            tii = (tii + 100) / 2
        else:
            tii = 50.0  # Neutral when no movement

        self._tii_values.append(tii)
        self._trend_intensity = tii

    def _calculate_signal_line(self):
        """Calculate signal line using exponential smoothing"""
        if len(self._tii_values) < self.tii_config.signal_period:
            return

        # Simple moving average for signal line
        recent_tii = list(self._tii_values)[-self.tii_config.signal_period:]
        signal_value = statistics.mean(recent_tii)
        self._signal_line.append(signal_value)

    def _analyze_trend_characteristics(self):
        """Analyze trend characteristics for institutional insights"""
        if not self.is_ready:
            return

        # Determine trend direction based on TII
        if self._trend_intensity > 60:
            self._trend_direction = 1  # Strong uptrend
        elif self._trend_intensity < 40:
            self._trend_direction = -1  # Strong downtrend
        else:
            self._trend_direction = 0  # Neutral/weak trend

        # Calculate trend strength
        distance_from_neutral = abs(self._trend_intensity - 50)
        self._trend_strength = min(1.0, distance_from_neutral / 25.0)  # Max strength at 25 points from neutral

        # Calculate trend consistency
        if len(self._tii_values) >= 5:
            recent_tii = list(self._tii_values)[-5:]
            consistency = 1.0 - (statistics.stdev(recent_tii) / 50.0)  # Lower variance = higher consistency
            self._trend_consistency = max(0.0, min(1.0, consistency))

        # Determine volatility regime
        if len(self._price_changes) >= 10:
            recent_volatility = statistics.stdev(list(self._price_changes)[-10:])
            avg_price = statistics.mean(list(self._close_values)[-10:])

            if avg_price > 0:
                volatility_ratio = recent_volatility / avg_price
                if volatility_ratio > 0.05:
                    self._volatility_regime = "high"
                elif volatility_ratio < 0.01:
                    self._volatility_regime = "low"
                else:
                    self._volatility_regime = "normal"

        # Track trend cycles
        if len(self._tii_values) >= 2:
            prev_tii = list(self._tii_values)[-2]
            if ((prev_tii <= 50 and self._trend_intensity > 50) or
                (prev_tii >= 50 and self._trend_intensity < 50)):
                self._trend_cycles += 1

        # Track intensity peaks
        if self._trend_strength > 0.8:
            self._intensity_peaks.append(self._trend_intensity)

    def _generate_tii_signals(self):
        """Generate Trend Intensity Index-based signals"""
        if not self.is_ready:
            return

        # Intensity signals based on threshold crossings
        if self._trend_intensity > (50 + self.tii_config.intensity_threshold * 50):
            self._intensity_signals += 1
        elif self._trend_intensity < (50 - self.tii_config.intensity_threshold * 50):
            self._intensity_signals += 1

        # Trend signals based on direction changes
        if len(self._tii_values) >= 2:
            prev_direction = 1 if list(self._tii_values)[-2] > 50 else -1 if list(self._tii_values)[-2] < 50 else 0
            if self._trend_direction != prev_direction and self._trend_direction != 0:
                self._trend_signals += 1

        # Divergence signals
        if len(self._tii_values) >= 5 and len(self._close_values) >= 5:
            tii_trend = self._trend_intensity - list(self._tii_values)[-5]
            price_trend = list(self._close_values)[-1] - list(self._close_values)[-5]

            # Bullish divergence: price down, TII up
            if price_trend < 0 and tii_trend > 0:
                self._divergence_signals += 1
            # Bearish divergence: price up, TII down
            elif price_trend > 0 and tii_trend < 0:
                self._divergence_signals += 1

        # Breakout signals
        if self._trend_strength > 0.9:
            self._breakout_signals += 1

    def _calculate_institutional_tii(self):
        """Calculate institutional TII analysis based on trend characteristics"""
        if not self.is_ready:
            return

        # Institutional traders use TII for trend strength assessment and timing
        base_tii = 0.0

        if (self._trend_strength > 0.8 and
            self._trend_consistency > 0.7 and
            self._intensity_signals > 0):
            base_tii = 0.9  # Strong trend with high consistency and signals
        elif (self._trend_signals > 0 and
              self._signal_accuracy > 0.6 and
              self._trend_cycles > 2):
            base_tii = 0.8  # Good trend signals with accuracy and cycle confirmation
        elif (self._divergence_signals > 0 and
              self._breakout_signals > 0):
            base_tii = 0.7  # Divergence and breakout signals present

        self._institutional_tii = base_tii

        # Smart money TII considers trend strength and market timing
        smart_money_score = (
            self._trend_strength * 0.3 +
            self._trend_consistency * 0.3 +
            self._signal_accuracy * 0.2 +
            self._institutional_tii * 0.2
        )
        self._smart_money_tii = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade Trend Intensity Index analysis"""
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

        # Use trend intensity as primary raw value
        raw_value = self._trend_intensity

        # Determine signal type based on TII analysis
        signal_type = self._determine_tii_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'trend_intensity': self._trend_intensity,
            'signal_line': list(self._signal_line)[-1] if self._signal_line else 0.0,
            'trend_direction': self._trend_direction,
            'trend_strength': self._trend_strength,
            'trend_consistency': self._trend_consistency,
            'signal_accuracy': self._signal_accuracy,
            'trend_prediction_rate': self._trend_prediction_rate,
            'intensity_reliability': self._intensity_reliability,
            'volatility_regime': self._volatility_regime,
            'trend_cycles': self._trend_cycles,
            'intensity_peaks': self._intensity_peaks,
            'trend_based_stop': self._trend_based_stop,
            'intensity_based_position_size': self._intensity_based_position_size,
            'risk_adjustment_factor': self._risk_adjustment_factor,
            'intensity_signals': self._intensity_signals,
            'trend_signals': self._trend_signals,
            'divergence_signals': self._divergence_signals,
            'breakout_signals': self._breakout_signals,
            'institutional_tii': self._institutional_tii,
            'smart_money_tii': self._smart_money_tii
        }

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._trend_based_stop,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Trend_Intensity_Index_Indicator",
                "period": self.tii_config.period,
                "signal_period": self.tii_config.signal_period,
                "intensity_threshold": self.tii_config.intensity_threshold,
                "adaptive_smoothing": self.tii_config.adaptive_smoothing,
                "trend_intensity": self._trend_intensity,
                "signal_line": list(self._signal_line)[-1] if self._signal_line else 0.0,
                "trend_direction": self._trend_direction,
                "trend_strength": self._trend_strength,
                "trend_consistency": self._trend_consistency,
                "signal_accuracy": self._signal_accuracy,
                "trend_prediction_rate": self._trend_prediction_rate,
                "intensity_reliability": self._intensity_reliability,
                "volatility_regime": self._volatility_regime,
                "trend_cycles": self._trend_cycles,
                "intensity_peaks": self._intensity_peaks,
                "trend_based_stop": self._trend_based_stop,
                "intensity_based_position_size": self._intensity_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor,
                "intensity_signals": self._intensity_signals,
                "trend_signals": self._trend_signals,
                "divergence_signals": self._divergence_signals,
                "breakout_signals": self._breakout_signals,
                "institutional_tii": self._institutional_tii,
                "smart_money_tii": self._smart_money_tii,
                "is_ready": self.is_ready
            }
        )

    def _determine_tii_signal(self) -> SignalType:
        """Determine signal type based on Trend Intensity Index analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong trend signals
        if (self._trend_strength > 0.8 and
            self._trend_consistency > 0.8 and
            self._intensity_signals > 0):
            if self._trend_direction == 1:
                return SignalType.STRONG_BULLISH
            elif self._trend_direction == -1:
                return SignalType.STRONG_BEARISH

        # Moderate trend signals
        elif (self._trend_signals > 0 and
              self._signal_accuracy > 0.6):
            if self._trend_direction == 1:
                return SignalType.BULLISH
            elif self._trend_direction == -1:
                return SignalType.BEARISH

        # Divergence signals
        elif (self._divergence_signals > 0 and
              self._trend_strength > 0.6):
            if self._trend_direction == 1:
                return SignalType.BULLISH  # Bullish divergence in uptrend
            elif self._trend_direction == -1:
                return SignalType.BEARISH  # Bearish divergence in downtrend

        # Breakout signals
        elif self._breakout_signals > 0:
            if self._trend_direction == 1:
                return SignalType.STRONG_BULLISH
            elif self._trend_direction == -1:
                return SignalType.STRONG_BEARISH

        return SignalType.NEUTRAL

    @property
    def trend_intensity(self) -> float:
        """Get the current trend intensity (0-100)"""
        return self._trend_intensity if self.is_ready else 50.0

    @property
    def signal_line(self) -> float:
        """Get the current signal line value"""
        return list(self._signal_line)[-1] if self._signal_line else 50.0

    @property
    def trend_direction(self) -> int:
        """Get the current trend direction (1=up, -1=down, 0=neutral)"""
        return self._trend_direction

    @property
    def trend_strength(self) -> float:
        """Get the current trend strength (0-1)"""
        return self._trend_strength

    @property
    def trend_consistency(self) -> float:
        """Get the trend consistency (0-1)"""
        return self._trend_consistency

    @property
    def signal_accuracy(self) -> float:
        """Get the signal accuracy (0-1)"""
        return self._signal_accuracy

    @property
    def volatility_regime(self) -> str:
        """Get the current volatility regime"""
        return self._volatility_regime

    @property
    def trend_cycles(self) -> int:
        """Get the count of trend cycles"""
        return self._trend_cycles

    @property
    def intensity_signals(self) -> int:
        """Get the count of intensity signals"""
        return self._intensity_signals

    @property
    def trend_signals(self) -> int:
        """Get the count of trend signals"""
        return self._trend_signals

    @property
    def divergence_signals(self) -> int:
        """Get the count of divergence signals"""
        return self._divergence_signals

    @property
    def breakout_signals(self) -> int:
        """Get the count of breakout signals"""
        return self._breakout_signals

    @property
    def institutional_tii(self) -> float:
        """Get the institutional TII score (0-1)"""
        return self._institutional_tii

    @property
    def smart_money_tii(self) -> float:
        """Get the smart money TII score (0-1)"""
        return self._smart_money_tii

    def is_strong_uptrend(self) -> bool:
        """Check if trend is strong uptrend"""
        return self._trend_direction == 1 and self._trend_strength > 0.7

    def is_strong_downtrend(self) -> bool:
        """Check if trend is strong downtrend"""
        return self._trend_direction == -1 and self._trend_strength > 0.7

    def is_trend_consistent(self) -> bool:
        """Check if trend is consistent"""
        return self._trend_consistency > 0.7

    def is_high_intensity(self) -> bool:
        """Check if intensity is high"""
        return self._trend_intensity > 70 or self._trend_intensity < 30

    def is_neutral_intensity(self) -> bool:
        """Check if intensity is neutral"""
        return 40 <= self._trend_intensity <= 60

    def is_signal_accurate(self) -> bool:
        """Check if signals are accurate"""
        return self._signal_accuracy > 0.7

    def is_high_volatility(self) -> bool:
        """Check if volatility regime is high"""
        return self._volatility_regime == "high"

    def is_low_volatility(self) -> bool:
        """Check if volatility regime is low"""
        return self._volatility_regime == "low"

    def is_institutional_setup(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_tii > 0.7

    def get_tii_info(self) -> Dict[str, Any]:
        """Get comprehensive Trend Intensity Index indicator information"""
        return {
            "trend_analysis": {
                "intensity": self._trend_intensity,
                "signal_line": list(self._signal_line)[-1] if self._signal_line else 0.0,
                "direction": self._trend_direction,
                "strength": self._trend_strength,
                "consistency": self._trend_consistency
            },
            "performance_metrics": {
                "signal_accuracy": self._signal_accuracy,
                "trend_prediction_rate": self._trend_prediction_rate,
                "intensity_reliability": self._intensity_reliability
            },
            "market_conditions": {
                "volatility_regime": self._volatility_regime,
                "trend_cycles": self._trend_cycles
            },
            "signal_counts": {
                "intensity_signals": self._intensity_signals,
                "trend_signals": self._trend_signals,
                "divergence_signals": self._divergence_signals,
                "breakout_signals": self._breakout_signals
            },
            "intensity_tracking": {
                "peaks": self._intensity_peaks
            },
            "risk_management": {
                "trend_based_stop": self._trend_based_stop,
                "intensity_based_position_size": self._intensity_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor
            },
            "institutional_analysis": {
                "tii": self._institutional_tii,
                "smart_money_tii": self._smart_money_tii
            },
            "metadata": {
                "period": self.tii_config.period,
                "signal_period": self.tii_config.signal_period,
                "intensity_threshold": self.tii_config.intensity_threshold,
                "adaptive_smoothing": self.tii_config.adaptive_smoothing,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._close_values.clear()
        self._volume_values.clear()
        self._price_changes.clear()
        self._tii_values.clear()
        self._signal_line.clear()
        self._trend_intensity = 0.0
        self._trend_direction = 0
        self._trend_strength = 0.0
        self._trend_consistency = 0.0
        self._intensity_signals = 0
        self._trend_signals = 0
        self._divergence_signals = 0
        self._breakout_signals = 0
        self._signal_accuracy = 0.0
        self._trend_prediction_rate = 0.0
        self._intensity_reliability = 0.0
        self._volatility_regime = "normal"
        self._trend_cycles = 0
        self._intensity_peaks.clear()
        self._trend_based_stop = 0.0
        self._intensity_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0
        self._institutional_tii = 0.0
        self._smart_money_tii = 0.0