"""
Institutional-Grade Augmented Trade Volume Index Indicator

This module implements an enhanced Trade Volume Index with institutional-grade features:
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
class AugmentedTradeVolumeIndexConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Trade Volume Index"""
    min_volume: float = 1000.0
    volume_threshold: float = 1.5
    overbought: float = 0.8
    oversold: float = -0.8


class AugmentedTradeVolumeIndexIndicator(AugmentedIndicator):
    """
    Institutional-grade Augmented Trade Volume Index implementing 5-pillar architecture.

    Features:
    - Intraday volume analysis for accumulation/distribution tracking
    - Volume-weighted calculations for institutional validation
    - Market regime adaptation for different volatility environments
    - Multi-timeframe convergence for volume confirmation
    - Smart money intraday flow detection
    - Automated risk management based on volume signals
    """

    def __init__(self, config: AugmentedTradeVolumeIndexConfig = None):
        if config is None:
            config = AugmentedTradeVolumeIndexConfig()

        super().__init__(config)
        self.tvi_config = config

        # TVI specific state
        self._close_values = deque(maxlen=self.config.buffer_size)
        self._volume_values = deque(maxlen=self.config.buffer_size)

        # TVI calculation components
        self._tvi_values = deque(maxlen=self.config.buffer_size)
        self._direction_values = deque(maxlen=self.config.buffer_size)

        # Current TVI values
        self._tvi = 0.0
        self._direction = 0.0

        # Volume analysis
        self._volume_direction = 0  # 1 = increasing, -1 = decreasing, 0 = neutral
        self._volume_strength = 0.0
        self._tvi_signal = 0.0

        # Signal analysis
        self._accumulation_signals = 0
        self._distribution_signals = 0
        self._volume_signals = 0
        self._breakout_signals = 0

        # Performance tracking
        self._signal_accuracy = 0.0
        self._volume_prediction_rate = 0.0
        self._tvi_reliability = 0.0

        # Market structure
        self._volatility_regime = "normal"
        self._volume_cycles = 0
        self._tvi_extremes = []

        # Risk management
        self._tvi_based_stop = 0.0
        self._volume_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0

        # Institutional analysis
        self._institutional_tvi = 0.0
        self._smart_money_tvi = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Trade Volume Index is ready to provide signals"""
        return (len(self._close_values) >= 2 and
                len(self._tvi_values) > 0)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update TVI analysis

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

        # Update TVI analysis
        self._update_tvi_analysis(close, volume)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_tvi_analysis(self, close: float, volume: float):
        """Update the core Trade Volume Index analysis with institutional enhancements"""
        # Store price and volume data
        self._close_values.append(close)
        self._volume_values.append(volume)

        if len(self._close_values) >= 2 and volume >= self.tvi_config.min_volume:
            # Calculate Trade Volume Index
            self._calculate_trade_volume_index()

            # Calculate volume direction
            self._calculate_volume_direction()

            # Analyze volume characteristics
            self._analyze_volume_characteristics()

            # Generate TVI signals
            self._generate_tvi_signals()

            # Calculate institutional TVI analysis
            self._calculate_institutional_tvi()

    def _calculate_trade_volume_index(self):
        """Calculate Trade Volume Index"""
        if len(self._close_values) < 2:
            return

        # Get current and previous values
        prev_close = list(self._close_values)[-2]
        curr_close = list(self._close_values)[-1]
        curr_volume = list(self._volume_values)[-1]

        # Calculate price direction
        price_change = curr_close - prev_close

        # Calculate volume direction factor
        if price_change > 0:
            direction_factor = 1.0  # Up move
        elif price_change < 0:
            direction_factor = -1.0  # Down move
        else:
            direction_factor = 0.0  # No change

        self._direction_values.append(direction_factor)
        self._direction = direction_factor

        # Calculate TVI increment
        if len(self._tvi_values) == 0:
            tvi_increment = direction_factor * curr_volume
        else:
            prev_tvi = self._tvi_values[-1]
            tvi_increment = prev_tvi + (direction_factor * curr_volume)

        self._tvi_values.append(tvi_increment)
        self._tvi = tvi_increment

    def _calculate_volume_direction(self):
        """Calculate volume direction for institutional insights"""
        if len(self._volume_values) < 5:
            return

        # Analyze recent volume trend
        recent_volumes = list(self._volume_values)[-5:]
        volume_trend = sum(recent_volumes[i] - recent_volumes[i-1] for i in range(1, len(recent_volumes)))

        if volume_trend > 0:
            self._volume_direction = 1  # Increasing volume
        elif volume_trend < 0:
            self._volume_direction = -1  # Decreasing volume
        else:
            self._volume_direction = 0  # Neutral volume

        # Calculate volume strength
        avg_volume = statistics.mean(recent_volumes)
        if avg_volume > 0:
            volume_ratio = recent_volumes[-1] / avg_volume
            self._volume_strength = min(volume_ratio, 3.0) / 3.0  # Normalize to 0-1

        # Calculate TVI signal
        self._tvi_signal = self._direction * self._volume_strength

    def _analyze_volume_characteristics(self):
        """Analyze volume characteristics for institutional insights"""
        if not self.is_ready:
            return

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
        if len(self._direction_values) >= 2:
            prev_direction = list(self._direction_values)[-2]
            if ((prev_direction <= 0 and self._direction > 0) or
                (prev_direction >= 0 and self._direction < 0)):
                self._volume_cycles += 1

        # Track TVI extremes
        if abs(self._tvi) > 10000:  # Extreme readings (adjust based on typical volume)
            self._tvi_extremes.append(self._tvi)

    def _generate_tvi_signals(self):
        """Generate TVI-based signals"""
        if not self.is_ready:
            return

        # Accumulation signals (positive direction with increasing TVI)
        if (self._direction > 0 and
            len(self._tvi_values) >= 2 and
            self._tvi > list(self._tvi_values)[-2]):
            self._accumulation_signals += 1

        # Distribution signals (negative direction with decreasing TVI)
        if (self._direction < 0 and
            len(self._tvi_values) >= 2 and
            self._tvi < list(self._tvi_values)[-2]):
            self._distribution_signals += 1

        # Volume signals (strong volume with directional bias)
        if (self._volume_strength > 0.7 and
            abs(self._direction) > 0):
            self._volume_signals += 1

        # Breakout signals
        if self._volume_strength > 0.8:
            self._breakout_signals += 1

    def _calculate_institutional_tvi(self):
        """Calculate institutional TVI analysis based on volume characteristics"""
        if not self.is_ready:
            return

        # Institutional traders use TVI to track intraday accumulation/distribution
        base_tvi = 0.0

        if (self._volume_strength > 0.8 and
            (self._accumulation_signals > 0 or self._distribution_signals > 0) and
            self._signal_accuracy > 0.6):
            base_tvi = 0.9  # Strong volume with accumulation/distribution signals and accuracy
        elif (self._volume_signals > 0 and
              self._breakout_signals > 0 and
              self._volume_cycles > 2):
            base_tvi = 0.8  # Volume and breakout signals with cycle confirmation
        elif (self._volume_strength > 0.6 and
              self._tvi_reliability > 0.7):
            base_tvi = 0.7  # Good volume strength with high reliability

        self._institutional_tvi = base_tvi

        # Smart money TVI considers volume strength and market timing
        smart_money_score = (
            self._volume_strength * 0.3 +
            self._signal_accuracy * 0.3 +
            abs(self._tvi_signal) * 0.2 +
            self._institutional_tvi * 0.2
        )
        self._smart_money_tvi = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade TVI analysis"""
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

        # Use TVI value as primary raw value
        raw_value = self._tvi

        # Determine signal type based on TVI analysis
        signal_type = self._determine_tvi_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'tvi': self._tvi,
            'direction': self._direction,
            'volume_direction': self._volume_direction,
            'volume_strength': self._volume_strength,
            'tvi_signal': self._tvi_signal,
            'signal_accuracy': self._signal_accuracy,
            'volume_prediction_rate': self._volume_prediction_rate,
            'tvi_reliability': self._tvi_reliability,
            'volatility_regime': self._volatility_regime,
            'volume_cycles': self._volume_cycles,
            'tvi_extremes': self._tvi_extremes,
            'tvi_based_stop': self._tvi_based_stop,
            'volume_based_position_size': self._volume_based_position_size,
            'risk_adjustment_factor': self._risk_adjustment_factor,
            'accumulation_signals': self._accumulation_signals,
            'distribution_signals': self._distribution_signals,
            'volume_signals': self._volume_signals,
            'breakout_signals': self._breakout_signals,
            'institutional_tvi': self._institutional_tvi,
            'smart_money_tvi': self._smart_money_tvi
        }

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._tvi_based_stop,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Trade_Volume_Index",
                "min_volume": self.tvi_config.min_volume,
                "volume_threshold": self.tvi_config.volume_threshold,
                "overbought": self.tvi_config.overbought,
                "oversold": self.tvi_config.oversold,
                "tvi": self._tvi,
                "direction": self._direction,
                "volume_direction": self._volume_direction,
                "volume_strength": self._volume_strength,
                "tvi_signal": self._tvi_signal,
                "signal_accuracy": self._signal_accuracy,
                "volume_prediction_rate": self._volume_prediction_rate,
                "tvi_reliability": self._tvi_reliability,
                "volatility_regime": self._volatility_regime,
                "volume_cycles": self._volume_cycles,
                "tvi_extremes": self._tvi_extremes,
                "tvi_based_stop": self._tvi_based_stop,
                "volume_based_position_size": self._volume_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor,
                "accumulation_signals": self._accumulation_signals,
                "distribution_signals": self._distribution_signals,
                "volume_signals": self._volume_signals,
                "breakout_signals": self._breakout_signals,
                "institutional_tvi": self._institutional_tvi,
                "smart_money_tvi": self._smart_money_tvi,
                "is_ready": self.is_ready
            }
        )

    def _determine_tvi_signal(self) -> SignalType:
        """Determine signal type based on TVI analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong volume signals
        if (self._volume_strength > 0.8 and
            (self._accumulation_signals > 0 or self._distribution_signals > 0) and
            self._signal_accuracy > 0.7):
            if self._volume_direction == 1:
                return SignalType.STRONG_BULLISH
            elif self._volume_direction == -1:
                return SignalType.STRONG_BEARISH

        # Moderate volume signals
        elif (self._volume_signals > 0 and
              self._volume_strength > 0.6):
            if self._direction > 0:
                return SignalType.BULLISH
            elif self._direction < 0:
                return SignalType.BEARISH

        # Breakout signals
        elif (self._breakout_signals > 0 and
              self._volume_strength > self.tvi_config.volume_threshold):
            if self._direction > 0:
                return SignalType.STRONG_BULLISH
            else:
                return SignalType.STRONG_BEARISH

        # Accumulation/distribution signals
        elif (self._accumulation_signals > 0 and
              self._tvi_reliability > 0.7):
            return SignalType.BULLISH  # Accumulation signal
        elif (self._distribution_signals > 0 and
              self._tvi_reliability > 0.7):
            return SignalType.BEARISH  # Distribution signal

        # Overbought/Oversold signals
        elif self._tvi > self.tvi_config.overbought:
            return SignalType.BEARISH  # Potential reversal from overbought
        elif self._tvi < self.tvi_config.oversold:
            return SignalType.BULLISH  # Potential reversal from oversold

        return SignalType.NEUTRAL

    @property
    def tvi(self) -> float:
        """Get the current TVI value"""
        return self._tvi if self.is_ready else 0.0

    @property
    def direction(self) -> float:
        """Get the current direction value"""
        return self._direction if self.is_ready else 0.0

    @property
    def volume_direction(self) -> int:
        """Get the current volume direction (1=increasing, -1=decreasing, 0=neutral)"""
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
    def accumulation_signals(self) -> int:
        """Get the count of accumulation signals"""
        return self._accumulation_signals

    @property
    def distribution_signals(self) -> int:
        """Get the count of distribution signals"""
        return self._distribution_signals

    @property
    def volume_signals(self) -> int:
        """Get the count of volume signals"""
        return self._volume_signals

    def is_bullish_volume_tvi(self) -> bool:
        """Check if TVI indicates bullish volume"""
        return self._volume_direction == 1 and self._direction > 0

    def is_bearish_volume_tvi(self) -> bool:
        """Check if TVI indicates bearish volume"""
        return self._volume_direction == -1 and self._direction < 0

    def is_strong_volume_tvi(self) -> bool:
        """Check if volume strength is strong"""
        return self._volume_strength > 0.7

    def is_accumulation_tvi(self) -> bool:
        """Check if TVI indicates accumulation"""
        return self._accumulation_signals > 0

    def is_distribution_tvi(self) -> bool:
        """Check if TVI indicates distribution"""
        return self._distribution_signals > 0

    def is_overbought_tvi(self) -> bool:
        """Check if TVI is overbought"""
        return self._tvi > self.tvi_config.overbought

    def is_oversold_tvi(self) -> bool:
        """Check if TVI is oversold"""
        return self._tvi < self.tvi_config.oversold

    def is_high_volatility_tvi(self) -> bool:
        """Check if volatility regime is high"""
        return self._volatility_regime == "high"

    def is_low_volatility_tvi(self) -> bool:
        """Check if volatility regime is low"""
        return self._volatility_regime == "low"

    def is_institutional_setup_tvi(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_tvi > 0.7

    def get_tvi_info(self) -> Dict[str, Any]:
        """Get comprehensive TVI indicator information"""
        return {
            "tvi_values": {
                "tvi": self._tvi,
                "direction": self._direction
            },
            "volume_analysis": {
                "direction": self._volume_direction,
                "strength": self._volume_strength,
                "tvi_signal": self._tvi_signal
            },
            "performance_metrics": {
                "signal_accuracy": self._signal_accuracy,
                "volume_prediction_rate": self._volume_prediction_rate,
                "tvi_reliability": self._tvi_reliability
            },
            "market_conditions": {
                "volatility_regime": self._volatility_regime,
                "volume_cycles": self._volume_cycles
            },
            "signal_counts": {
                "accumulation_signals": self._accumulation_signals,
                "distribution_signals": self._distribution_signals,
                "volume_signals": self._volume_signals,
                "breakout_signals": self._breakout_signals
            },
            "tvi_tracking": {
                "extremes": self._tvi_extremes
            },
            "risk_management": {
                "tvi_based_stop": self._tvi_based_stop,
                "volume_based_position_size": self._volume_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor
            },
            "institutional_analysis": {
                "tvi": self._institutional_tvi,
                "smart_money_tvi": self._smart_money_tvi
            },
            "metadata": {
                "min_volume": self.tvi_config.min_volume,
                "volume_threshold": self.tvi_config.volume_threshold,
                "overbought": self.tvi_config.overbought,
                "oversold": self.tvi_config.oversold,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._close_values.clear()
        self._volume_values.clear()
        self._tvi_values.clear()
        self._direction_values.clear()
        self._tvi = 0.0
        self._direction = 0.0
        self._volume_direction = 0
        self._volume_strength = 0.0
        self._tvi_signal = 0.0
        self._accumulation_signals = 0
        self._distribution_signals = 0
        self._volume_signals = 0
        self._breakout_signals = 0
        self._signal_accuracy = 0.0
        self._volume_prediction_rate = 0.0
        self._tvi_reliability = 0.0
        self._volatility_regime = "normal"
        self._volume_cycles = 0
        self._tvi_extremes.clear()
        self._tvi_based_stop = 0.0
        self._volume_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0
        self._institutional_tvi = 0.0
        self._smart_money_tvi = 0.0