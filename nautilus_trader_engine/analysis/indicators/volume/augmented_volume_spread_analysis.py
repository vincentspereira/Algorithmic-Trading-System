"""
Institutional-Grade Augmented Volume Spread Analysis Indicator

This module implements an enhanced Volume Spread Analysis with institutional-grade features:
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

from nautilus_trader_engine.indicators.base import (
    AugmentedIndicator,
    AugmentedIndicatorConfig,
    IndicatorSignal,
    SignalType,
)


@dataclass
class AugmentedVolumeSpreadAnalysisConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Volume Spread Analysis"""
    spread_period: int = 20
    volume_period: int = 20
    institutional_threshold: float = 2.0
    spread_threshold: float = 0.5


class AugmentedVolumeSpreadAnalysisIndicator(AugmentedIndicator):
    """
    Institutional-grade Augmented Volume Spread Analysis implementing 5-pillar architecture.

    Features:
    - Analyzes price spread vs volume relationship for institutional activity
    - Volume-weighted calculations for institutional validation
    - Market regime adaptation for different volatility environments
    - Multi-timeframe convergence for volume confirmation
    - Smart money flow detection through spread analysis
    - Automated risk management based on volume spread signals
    """

    def __init__(self, config: AugmentedVolumeSpreadAnalysisConfig = None):
        if config is None:
            config = AugmentedVolumeSpreadAnalysisConfig()

        super().__init__(config)
        self.vsa_config = config

        # VSA specific state
        self._high_values = deque(maxlen=self.config.buffer_size)
        self._low_values = deque(maxlen=self.config.buffer_size)
        self._close_values = deque(maxlen=self.config.buffer_size)
        self._volume_values = deque(maxlen=self.config.buffer_size)

        # VSA calculation components
        self._spread_values = deque(maxlen=self.config.buffer_size)
        self._volume_ratio_values = deque(maxlen=self.config.buffer_size)
        self._vsa_score_values = deque(maxlen=self.config.buffer_size)

        # Current VSA values
        self._spread = 0.0
        self._volume_ratio = 0.0
        self._vsa_score = 0.0

        # Volume analysis
        self._volume_direction = 0  # 1 = increasing, -1 = decreasing, 0 = neutral
        self._volume_strength = 0.0
        self._vsa_signal = 0.0

        # Signal analysis
        self._institutional_signals = 0
        self._accumulation_signals = 0
        self._distribution_signals = 0
        self._breakout_signals = 0

        # Performance tracking
        self._signal_accuracy = 0.0
        self._volume_prediction_rate = 0.0
        self._vsa_reliability = 0.0

        # Market structure
        self._volatility_regime = "normal"
        self._volume_cycles = 0
        self._vsa_extremes = []

        # Risk management
        self._vsa_based_stop = 0.0
        self._volume_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0

        # Institutional analysis
        self._institutional_vsa = 0.0
        self._smart_money_vsa = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Volume Spread Analysis is ready to provide signals"""
        return (len(self._close_values) >= self.vsa_config.spread_period and
                len(self._volume_values) >= self.vsa_config.volume_period and
                len(self._vsa_score_values) > 0)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update VSA analysis

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

        # Update VSA analysis
        self._update_vsa_analysis(high, low, close, volume)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_vsa_analysis(self, high: float, low: float, close: float, volume: float):
        """Update the core Volume Spread Analysis with institutional enhancements"""
        # Store OHLCV data
        self._high_values.append(high)
        self._low_values.append(low)
        self._close_values.append(close)
        self._volume_values.append(volume)

        if len(self._close_values) >= self.vsa_config.spread_period and len(self._volume_values) >= self.vsa_config.volume_period:
            # Calculate spread analysis
            self._calculate_spread_analysis()

            # Calculate volume analysis
            self._calculate_volume_analysis()

            # Calculate VSA score
            self._calculate_vsa_score()

            # Analyze volume characteristics
            self._analyze_volume_characteristics()

            # Generate VSA signals
            self._generate_vsa_signals()

            # Calculate institutional VSA analysis
            self._calculate_institutional_vsa()

    def _calculate_spread_analysis(self):
        """Calculate price spread analysis"""
        if len(self._high_values) < self.vsa_config.spread_period or len(self._low_values) < self.vsa_config.spread_period:
            return

        # Calculate average spread over the period
        recent_highs = list(self._high_values)[-self.vsa_config.spread_period:]
        recent_lows = list(self._low_values)[-self.vsa_config.spread_period:]

        spreads = [h - l for h, l in zip(recent_highs, recent_lows)]
        avg_spread = statistics.mean(spreads) if spreads else 0

        # Current spread
        current_spread = recent_highs[-1] - recent_lows[-1]

        # Normalize spread
        if avg_spread > 0:
            normalized_spread = current_spread / avg_spread
        else:
            normalized_spread = 1.0

        self._spread_values.append(normalized_spread)
        self._spread = normalized_spread

    def _calculate_volume_analysis(self):
        """Calculate volume analysis"""
        if len(self._volume_values) < self.vsa_config.volume_period:
            return

        # Calculate average volume over the period
        recent_volumes = list(self._volume_values)[-self.vsa_config.volume_period:]
        avg_volume = statistics.mean(recent_volumes) if recent_volumes else 1

        # Current volume
        current_volume = recent_volumes[-1]

        # Volume ratio
        if avg_volume > 0:
            volume_ratio = current_volume / avg_volume
        else:
            volume_ratio = 1.0

        self._volume_ratio_values.append(volume_ratio)
        self._volume_ratio = volume_ratio

    def _calculate_vsa_score(self):
        """Calculate Volume Spread Analysis score"""
        if len(self._spread_values) == 0 or len(self._volume_ratio_values) == 0:
            return

        # VSA score combines spread and volume analysis
        # High spread + high volume = potential institutional activity
        # Low spread + high volume = accumulation/distribution
        # High spread + low volume = weak move
        # Low spread + low volume = consolidation

        spread_factor = self._spread
        volume_factor = self._volume_ratio

        # Calculate VSA score based on spread-volume relationship
        if spread_factor > self.vsa_config.spread_threshold and volume_factor > self.vsa_config.institutional_threshold:
            # Wide spread + high volume = strong institutional move
            vsa_score = (spread_factor * volume_factor) / 2.0
        elif spread_factor < (1 - self.vsa_config.spread_threshold) and volume_factor > self.vsa_config.institutional_threshold:
            # Narrow spread + high volume = accumulation/distribution
            vsa_score = volume_factor * 0.8
        elif spread_factor > self.vsa_config.spread_threshold and volume_factor < 1.0:
            # Wide spread + low volume = weak move
            vsa_score = spread_factor * 0.3
        else:
            # Normal conditions
            vsa_score = (spread_factor + volume_factor) / 2.0

        self._vsa_score_values.append(vsa_score)
        self._vsa_score = vsa_score

    def _analyze_volume_characteristics(self):
        """Analyze volume characteristics for institutional insights"""
        if not self.is_ready:
            return

        # Determine volume direction
        if self._volume_ratio > 1.5:
            self._volume_direction = 1  # High volume
        elif self._volume_ratio < 0.7:
            self._volume_direction = -1  # Low volume
        else:
            self._volume_direction = 0  # Normal volume

        # Calculate volume strength
        self._volume_strength = min(self._volume_ratio, 3.0) / 3.0  # Normalize to 0-1

        # Calculate VSA signal
        self._vsa_signal = self._vsa_score

        # Determine volatility regime
        if len(self._close_values) >= 10:
            recent_prices = list(self._close_values)[-10:]
            price_volatility = statistics.stdev(recent_prices) / statistics.mean(recent_prices) if statistics.mean(recent_prices) > 0 else 0

            if price_volatility > 0.03:
                self._volatility_regime = "high"
            elif price_volatility < 0.01:
                self._volatility_regime = "low"
            else:
                self._volatility_regime = "normal"

        # Track volume cycles
        if len(self._volume_ratio_values) >= 2:
            prev_ratio = list(self._volume_ratio_values)[-2]
            if ((prev_ratio <= 1.0 and self._volume_ratio > 1.0) or
                (prev_ratio >= 1.0 and self._volume_ratio < 1.0)):
                self._volume_cycles += 1

        # Track VSA extremes
        if self._vsa_score > 2.0:  # Extreme readings
            self._vsa_extremes.append(self._vsa_score)

    def _generate_vsa_signals(self):
        """Generate VSA-based signals"""
        if not self.is_ready:
            return

        # Institutional signals (high volume + significant spread)
        if (self._volume_ratio > self.vsa_config.institutional_threshold and
            abs(self._spread - 1.0) > self.vsa_config.spread_threshold):
            self._institutional_signals += 1

        # Accumulation signals (narrow spread + high volume)
        if (self._spread < (1 - self.vsa_config.spread_threshold) and
            self._volume_ratio > self.vsa_config.institutional_threshold):
            self._accumulation_signals += 1

        # Distribution signals (wide spread + high volume)
        if (self._spread > (1 + self.vsa_config.spread_threshold) and
            self._volume_ratio > self.vsa_config.institutional_threshold):
            self._distribution_signals += 1

        # Breakout signals
        if self._volume_strength > 0.8:
            self._breakout_signals += 1

    def _calculate_institutional_vsa(self):
        """Calculate institutional VSA analysis based on volume characteristics"""
        if not self.is_ready:
            return

        # Institutional traders use VSA to identify smart money activity
        base_vsa = 0.0

        if (self._volume_strength > 0.8 and
            self._institutional_signals > 0 and
            self._signal_accuracy > 0.6):
            base_vsa = 0.9  # Strong volume with institutional signals and accuracy
        elif (self._accumulation_signals > 0 and
              self._distribution_signals > 0 and
              self._volume_cycles > 2):
            base_vsa = 0.8  # Accumulation/distribution signals with cycle confirmation
        elif (self._breakout_signals > 0 and
              self._vsa_reliability > 0.7):
            base_vsa = 0.7  # Breakout signals with high reliability

        self._institutional_vsa = base_vsa

        # Smart money VSA considers volume strength and market timing
        smart_money_score = (
            self._volume_strength * 0.3 +
            self._signal_accuracy * 0.3 +
            self._vsa_signal * 0.2 +
            self._institutional_vsa * 0.2
        )
        self._smart_money_vsa = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade VSA analysis"""
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

        # Use VSA score as primary raw value
        raw_value = self._vsa_score

        # Determine signal type based on VSA analysis
        signal_type = self._determine_vsa_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'spread': self._spread,
            'volume_ratio': self._volume_ratio,
            'vsa_score': self._vsa_score,
            'volume_direction': self._volume_direction,
            'volume_strength': self._volume_strength,
            'vsa_signal': self._vsa_signal,
            'signal_accuracy': self._signal_accuracy,
            'volume_prediction_rate': self._volume_prediction_rate,
            'vsa_reliability': self._vsa_reliability,
            'volatility_regime': self._volatility_regime,
            'volume_cycles': self._volume_cycles,
            'vsa_extremes': self._vsa_extremes,
            'vsa_based_stop': self._vsa_based_stop,
            'volume_based_position_size': self._volume_based_position_size,
            'risk_adjustment_factor': self._risk_adjustment_factor,
            'institutional_signals': self._institutional_signals,
            'accumulation_signals': self._accumulation_signals,
            'distribution_signals': self._distribution_signals,
            'breakout_signals': self._breakout_signals,
            'institutional_vsa': self._institutional_vsa,
            'smart_money_vsa': self._smart_money_vsa
        }

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._vsa_based_stop,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Volume_Spread_Analysis",
                "spread_period": self.vsa_config.spread_period,
                "volume_period": self.vsa_config.volume_period,
                "institutional_threshold": self.vsa_config.institutional_threshold,
                "spread_threshold": self.vsa_config.spread_threshold,
                "spread": self._spread,
                "volume_ratio": self._volume_ratio,
                "vsa_score": self._vsa_score,
                "volume_direction": self._volume_direction,
                "volume_strength": self._volume_strength,
                "vsa_signal": self._vsa_signal,
                "signal_accuracy": self._signal_accuracy,
                "volume_prediction_rate": self._volume_prediction_rate,
                "vsa_reliability": self._vsa_reliability,
                "volatility_regime": self._volatility_regime,
                "volume_cycles": self._volume_cycles,
                "vsa_extremes": self._vsa_extremes,
                "vsa_based_stop": self._vsa_based_stop,
                "volume_based_position_size": self._volume_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor,
                "institutional_signals": self._institutional_signals,
                "accumulation_signals": self._accumulation_signals,
                "distribution_signals": self._distribution_signals,
                "breakout_signals": self._breakout_signals,
                "institutional_vsa": self._institutional_vsa,
                "smart_money_vsa": self._smart_money_vsa,
                "is_ready": self.is_ready
            }
        )

    def _determine_vsa_signal(self) -> SignalType:
        """Determine signal type based on VSA analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong institutional signals
        if (self._volume_strength > 0.8 and
            self._institutional_signals > 0 and
            self._signal_accuracy > 0.7):
            if self._volume_direction == 1:
                return SignalType.STRONG_BULLISH
            elif self._volume_direction == -1:
                return SignalType.STRONG_BEARISH

        # Accumulation/distribution signals
        elif (self._accumulation_signals > 0 and
              self._volume_strength > 0.6):
            return SignalType.BULLISH  # Accumulation signal
        elif (self._distribution_signals > 0 and
              self._volume_strength > 0.6):
            return SignalType.BEARISH  # Distribution signal

        # Breakout signals
        elif (self._breakout_signals > 0 and
              self._vsa_score > 1.5):
            if self._spread > 1.0:
                return SignalType.STRONG_BULLISH
            else:
                return SignalType.STRONG_BEARISH

        # Volume confirmation signals
        elif (self._volume_ratio > self.vsa_config.institutional_threshold and
              self._vsa_reliability > 0.7):
            if self._volume_direction == 1:
                return SignalType.BULLISH
            else:
                return SignalType.BEARISH

        return SignalType.NEUTRAL

    @property
    def spread(self) -> float:
        """Get the current spread value"""
        return self._spread if self.is_ready else 1.0

    @property
    def volume_ratio(self) -> float:
        """Get the current volume ratio"""
        return self._volume_ratio if self.is_ready else 1.0

    @property
    def vsa_score(self) -> float:
        """Get the current VSA score"""
        return self._vsa_score if self.is_ready else 0.0

    @property
    def volume_direction(self) -> int:
        """Get the current volume direction (1=high, -1=low, 0=normal)"""
        return self._volume_direction

    @property
    def volume_strength(self) -> float:
        """Get the current volume strength (0-1)"""
        return self._volume_strength

    @property
    def signal_accuracy(self) -> float:
        """Get the signal accuracy (0-1)"""
        return self._signal_accuracy

    @property
    def volatility_regime(self) -> str:
        """Get the current volatility regime"""
        return self._volatility_regime

    @property
    def volume_cycles(self) -> int:
        """Get the count of volume cycles"""
        return self._volume_cycles

    @property
    def institutional_signals(self) -> int:
        """Get the count of institutional signals"""
        return self._institutional_signals

    @property
    def accumulation_signals(self) -> int:
        """Get the count of accumulation signals"""
        return self._accumulation_signals

    @property
    def distribution_signals(self) -> int:
        """Get the count of distribution signals"""
        return self._distribution_signals

    @property
    def breakout_signals(self) -> int:
        """Get the count of breakout signals"""
        return self._breakout_signals

    @property
    def institutional_vsa(self) -> float:
        """Get the institutional VSA score (0-1)"""
        return self._institutional_vsa

    @property
    def smart_money_vsa(self) -> float:
        """Get the smart money VSA score (0-1)"""
        return self._smart_money_vsa

    def is_high_volume_vsa(self) -> bool:
        """Check if volume is high"""
        return self._volume_direction == 1 and self._volume_ratio > self.vsa_config.institutional_threshold

    def is_low_volume_vsa(self) -> bool:
        """Check if volume is low"""
        return self._volume_direction == -1 and self._volume_ratio < 1.0

    def is_strong_volume_vsa(self) -> bool:
        """Check if volume strength is strong"""
        return self._volume_strength > 0.7

    def is_institutional_volume_vsa(self) -> bool:
        """Check if volume indicates institutional activity"""
        return self._institutional_signals > 0

    def is_accumulation_vsa(self) -> bool:
        """Check if VSA indicates accumulation"""
        return self._accumulation_signals > 0

    def is_distribution_vsa(self) -> bool:
        """Check if VSA indicates distribution"""
        return self._distribution_signals > 0

    def is_high_volatility_vsa(self) -> bool:
        """Check if volatility regime is high"""
        return self._volatility_regime == "high"

    def is_low_volatility_vsa(self) -> bool:
        """Check if volatility regime is low"""
        return self._volatility_regime == "low"

    def is_institutional_setup_vsa(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_vsa > 0.7

    def get_vsa_info(self) -> Dict[str, Any]:
        """Get comprehensive VSA indicator information"""
        return {
            "vsa_values": {
                "spread": self._spread,
                "volume_ratio": self._volume_ratio,
                "vsa_score": self._vsa_score
            },
            "volume_analysis": {
                "direction": self._volume_direction,
                "strength": self._volume_strength,
                "vsa_signal": self._vsa_signal
            },
            "performance_metrics": {
                "signal_accuracy": self._signal_accuracy,
                "volume_prediction_rate": self._volume_prediction_rate,
                "vsa_reliability": self._vsa_reliability
            },
            "market_conditions": {
                "volatility_regime": self._volatility_regime,
                "volume_cycles": self._volume_cycles
            },
            "signal_counts": {
                "institutional_signals": self._institutional_signals,
                "accumulation_signals": self._accumulation_signals,
                "distribution_signals": self._distribution_signals,
                "breakout_signals": self._breakout_signals
            },
            "vsa_tracking": {
                "extremes": self._vsa_extremes
            },
            "risk_management": {
                "vsa_based_stop": self._vsa_based_stop,
                "volume_based_position_size": self._volume_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor
            },
            "institutional_analysis": {
                "vsa": self._institutional_vsa,
                "smart_money_vsa": self._smart_money_vsa
            },
            "metadata": {
                "spread_period": self.vsa_config.spread_period,
                "volume_period": self.vsa_config.volume_period,
                "institutional_threshold": self.vsa_config.institutional_threshold,
                "spread_threshold": self.vsa_config.spread_threshold,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._high_values.clear()
        self._low_values.clear()
        self._close_values.clear()
        self._volume_values.clear()
        self._spread_values.clear()
        self._volume_ratio_values.clear()
        self._vsa_score_values.clear()
        self._spread = 0.0
        self._volume_ratio = 0.0
        self._vsa_score = 0.0
        self._volume_direction = 0
        self._volume_strength = 0.0
        self._vsa_signal = 0.0
        self._institutional_signals = 0
        self._accumulation_signals = 0
        self._distribution_signals = 0
        self._breakout_signals = 0
        self._signal_accuracy = 0.0
        self._volume_prediction_rate = 0.0
        self._vsa_reliability = 0.0
        self._volatility_regime = "normal"
        self._volume_cycles = 0
        self._vsa_extremes.clear()
        self._vsa_based_stop = 0.0
        self._volume_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0
        self._institutional_vsa = 0.0
        self._smart_money_vsa = 0.0