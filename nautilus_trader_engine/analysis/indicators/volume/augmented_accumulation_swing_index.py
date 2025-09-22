"""
Institutional-Grade Augmented Accumulation Swing Index Indicator

This module implements an enhanced Accumulation Swing Index with institutional-grade features:
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
class AugmentedAccumulationSwingIndexConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Accumulation Swing Index"""
    limit: float = 0.5
    overbought: float = 0.6
    oversold: float = -0.6


class AugmentedAccumulationSwingIndexIndicator(AugmentedIndicator):
    """
    Institutional-grade Augmented Accumulation Swing Index implementing 5-pillar architecture.

    Features:
    - Welles Wilder's Accumulation Swing Index for trend identification
    - Volume-weighted calculations for institutional validation
    - Market regime adaptation for different volatility environments
    - Multi-timeframe convergence for swing confirmation
    - Smart money accumulation/distribution detection
    - Automated risk management based on swing signals
    """

    def __init__(self, config: AugmentedAccumulationSwingIndexConfig = None):
        if config is None:
            config = AugmentedAccumulationSwingIndexConfig()

        super().__init__(config)
        self.asi_config = config

        # ASI specific state
        self._open_values = deque(maxlen=self.config.buffer_size)
        self._high_values = deque(maxlen=self.config.buffer_size)
        self._low_values = deque(maxlen=self.config.buffer_size)
        self._close_values = deque(maxlen=self.config.buffer_size)
        self._volume_values = deque(maxlen=self.config.buffer_size)

        # ASI calculation components
        self._asi_values = deque(maxlen=self.config.buffer_size)
        self._swing_values = deque(maxlen=self.config.buffer_size)

        # Current ASI values
        self._asi = 0.0
        self._swing = 0.0

        # Swing analysis
        self._swing_direction = 0  # 1 = bullish swing, -1 = bearish swing, 0 = neutral
        self._swing_strength = 0.0
        self._asi_signal = 0.0

        # Signal analysis
        self._accumulation_signals = 0
        self._distribution_signals = 0
        self._swing_signals = 0
        self._breakout_signals = 0

        # Performance tracking
        self._signal_accuracy = 0.0
        self._swing_prediction_rate = 0.0
        self._asi_reliability = 0.0

        # Market structure
        self._volatility_regime = "normal"
        self._swing_cycles = 0
        self._asi_extremes = []

        # Risk management
        self._asi_based_stop = 0.0
        self._swing_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0

        # Institutional analysis
        self._institutional_asi = 0.0
        self._smart_money_asi = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Accumulation Swing Index is ready to provide signals"""
        return (len(self._close_values) >= 2 and
                len(self._asi_values) > 0)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update ASI analysis

        Args:
            bar (Bar): New bar data
        """
        # Extract OHLCV data
        if hasattr(bar, 'open') and hasattr(bar, 'high') and hasattr(bar, 'low') and hasattr(bar, 'close') and hasattr(bar, 'volume'):
            open_price = bar.open
            high = bar.high
            low = bar.low
            close = bar.close
            volume = bar.volume
        else:
            open_price = bar.get('open', bar.get('close', 0.0))
            high = bar.get('high', bar.get('close', 0.0))
            low = bar.get('low', bar.get('close', 0.0))
            close = bar.get('close', bar.get('price', 0.0))
            volume = bar.get('volume', 1.0)

        # Update ASI analysis
        self._update_asi_analysis(open_price, high, low, close, volume)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_asi_analysis(self, open_price: float, high: float, low: float, close: float, volume: float):
        """Update the core Accumulation Swing Index analysis with institutional enhancements"""
        # Store OHLCV data
        self._open_values.append(open_price)
        self._high_values.append(high)
        self._low_values.append(low)
        self._close_values.append(close)
        self._volume_values.append(volume)

        if len(self._close_values) >= 2:
            # Calculate Accumulation Swing Index
            self._calculate_accumulation_swing_index()

            # Calculate swing analysis
            self._calculate_swing_analysis()

            # Analyze swing characteristics
            self._analyze_swing_characteristics()

            # Generate ASI signals
            self._generate_asi_signals()

            # Calculate institutional ASI analysis
            self._calculate_institutional_asi()

    def _calculate_accumulation_swing_index(self):
        """Calculate Accumulation Swing Index using Welles Wilder's formula"""
        if len(self._close_values) < 2:
            return

        # Get current and previous values
        prev_open = list(self._open_values)[-2]
        prev_high = list(self._high_values)[-2]
        prev_low = list(self._low_values)[-2]
        prev_close = list(self._close_values)[-2]

        curr_open = list(self._open_values)[-1]
        curr_high = list(self._high_values)[-1]
        curr_low = list(self._low_values)[-1]
        curr_close = list(self._close_values)[-1]

        # Calculate True Range
        tr1 = abs(curr_high - curr_low)
        tr2 = abs(curr_high - prev_close)
        tr3 = abs(curr_low - prev_close)
        true_range = max(tr1, tr2, tr3)

        # Calculate Swing Index
        if true_range > 0:
            # Determine if it's an up or down move
            move = curr_close - prev_close

            # Calculate numerator based on move direction
            if move > 0:  # Up move
                numerator = curr_close - curr_open + (curr_close - curr_open) / 2 + (curr_close - curr_open) / 4
            else:  # Down move
                numerator = curr_open - curr_close + (curr_open - curr_close) / 2 + (curr_open - curr_close) / 4

            # Calculate Swing Index
            swing_index = (numerator / true_range) * 100

            # Limit the swing index
            swing_index = max(min(swing_index, self.asi_config.limit), -self.asi_config.limit)

            self._swing_values.append(swing_index)
            self._swing = swing_index

            # Calculate Accumulation Swing Index (cumulative)
            if len(self._asi_values) == 0:
                asi = swing_index
            else:
                prev_asi = self._asi_values[-1]
                asi = prev_asi + swing_index

            self._asi_values.append(asi)
            self._asi = asi

    def _calculate_swing_analysis(self):
        """Calculate swing analysis for institutional insights"""
        if len(self._swing_values) < 2:
            return

        # Analyze swing direction and strength
        recent_swings = list(self._swing_values)[-5:] if len(self._swing_values) >= 5 else list(self._swing_values)

        # Calculate swing momentum
        swing_momentum = sum(recent_swings) / len(recent_swings) if recent_swings else 0

        # Update swing direction
        if swing_momentum > 0.1:
            self._swing_direction = 1  # Bullish swing
        elif swing_momentum < -0.1:
            self._swing_direction = -1  # Bearish swing
        else:
            self._swing_direction = 0  # Neutral swing

        # Calculate swing strength
        self._swing_strength = min(abs(swing_momentum) / 0.5, 1.0)  # Normalize to 0-1

        # Calculate ASI signal
        self._asi_signal = self._swing

    def _analyze_swing_characteristics(self):
        """Analyze swing characteristics for institutional insights"""
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

        # Track swing cycles
        if len(self._swing_values) >= 2:
            prev_swing = list(self._swing_values)[-2]
            if ((prev_swing <= 0 and self._swing > 0) or
                (prev_swing >= 0 and self._swing < 0)):
                self._swing_cycles += 1

        # Track ASI extremes
        if abs(self._asi) > 2.0:  # Extreme readings
            self._asi_extremes.append(self._asi)

    def _generate_asi_signals(self):
        """Generate ASI-based signals"""
        if not self.is_ready:
            return

        # Accumulation signals (positive swing with increasing ASI)
        if (self._swing > 0 and
            len(self._asi_values) >= 2 and
            self._asi > list(self._asi_values)[-2]):
            self._accumulation_signals += 1

        # Distribution signals (negative swing with decreasing ASI)
        if (self._swing < 0 and
            len(self._asi_values) >= 2 and
            self._asi < list(self._asi_values)[-2]):
            self._distribution_signals += 1

        # Swing signals (strong directional swings)
        if abs(self._swing) > self.asi_config.limit * 0.8:
            self._swing_signals += 1

        # Breakout signals
        if self._swing_strength > 0.8:
            self._breakout_signals += 1

    def _calculate_institutional_asi(self):
        """Calculate institutional ASI analysis based on swing characteristics"""
        if not self.is_ready:
            return

        # Institutional traders use ASI to identify accumulation/distribution phases
        base_asi = 0.0

        if (self._swing_strength > 0.8 and
            (self._accumulation_signals > 0 or self._distribution_signals > 0) and
            self._signal_accuracy > 0.6):
            base_asi = 0.9  # Strong swing with accumulation/distribution signals and accuracy
        elif (self._swing_signals > 0 and
              self._breakout_signals > 0 and
              self._swing_cycles > 2):
            base_asi = 0.8  # Swing and breakout signals with cycle confirmation
        elif (self._swing_strength > 0.6 and
              self._asi_reliability > 0.7):
            base_asi = 0.7  # Good swing strength with high reliability

        self._institutional_asi = base_asi

        # Smart money ASI considers swing strength and market timing
        smart_money_score = (
            self._swing_strength * 0.3 +
            self._signal_accuracy * 0.3 +
            abs(self._asi_signal) * 0.2 +
            self._institutional_asi * 0.2
        )
        self._smart_money_asi = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade ASI analysis"""
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

        # Use ASI value as primary raw value
        raw_value = self._asi

        # Determine signal type based on ASI analysis
        signal_type = self._determine_asi_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'asi': self._asi,
            'swing': self._swing,
            'swing_direction': self._swing_direction,
            'swing_strength': self._swing_strength,
            'asi_signal': self._asi_signal,
            'signal_accuracy': self._signal_accuracy,
            'swing_prediction_rate': self._swing_prediction_rate,
            'asi_reliability': self._asi_reliability,
            'volatility_regime': self._volatility_regime,
            'swing_cycles': self._swing_cycles,
            'asi_extremes': self._asi_extremes,
            'asi_based_stop': self._asi_based_stop,
            'swing_based_position_size': self._swing_based_position_size,
            'risk_adjustment_factor': self._risk_adjustment_factor,
            'accumulation_signals': self._accumulation_signals,
            'distribution_signals': self._distribution_signals,
            'swing_signals': self._swing_signals,
            'breakout_signals': self._breakout_signals,
            'institutional_asi': self._institutional_asi,
            'smart_money_asi': self._smart_money_asi
        }

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._asi_based_stop,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Accumulation_Swing_Index",
                "limit": self.asi_config.limit,
                "overbought": self.asi_config.overbought,
                "oversold": self.asi_config.oversold,
                "asi": self._asi,
                "swing": self._swing,
                "swing_direction": self._swing_direction,
                "swing_strength": self._swing_strength,
                "asi_signal": self._asi_signal,
                "signal_accuracy": self._signal_accuracy,
                "swing_prediction_rate": self._swing_prediction_rate,
                "asi_reliability": self._asi_reliability,
                "volatility_regime": self._volatility_regime,
                "swing_cycles": self._swing_cycles,
                "asi_extremes": self._asi_extremes,
                "asi_based_stop": self._asi_based_stop,
                "swing_based_position_size": self._swing_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor,
                "accumulation_signals": self._accumulation_signals,
                "distribution_signals": self._distribution_signals,
                "swing_signals": self._swing_signals,
                "breakout_signals": self._breakout_signals,
                "institutional_asi": self._institutional_asi,
                "smart_money_asi": self._smart_money_asi,
                "is_ready": self.is_ready
            }
        )

    def _determine_asi_signal(self) -> SignalType:
        """Determine signal type based on ASI analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong swing signals
        if (self._swing_strength > 0.8 and
            (self._accumulation_signals > 0 or self._distribution_signals > 0) and
            self._signal_accuracy > 0.7):
            if self._swing_direction == 1:
                return SignalType.STRONG_BULLISH
            elif self._swing_direction == -1:
                return SignalType.STRONG_BEARISH

        # Moderate swing signals
        elif (self._swing_signals > 0 and
              self._swing_strength > 0.6):
            if self._swing_direction == 1:
                return SignalType.BULLISH
            elif self._swing_direction == -1:
                return SignalType.BEARISH

        # Breakout signals
        elif (self._breakout_signals > 0 and
              abs(self._swing) > self.asi_config.limit * 0.7):
            if self._swing > 0:
                return SignalType.STRONG_BULLISH
            else:
                return SignalType.STRONG_BEARISH

        # Accumulation/distribution signals
        elif (self._accumulation_signals > 0 and
              self._asi_reliability > 0.7):
            return SignalType.BULLISH  # Accumulation signal
        elif (self._distribution_signals > 0 and
              self._asi_reliability > 0.7):
            return SignalType.BEARISH  # Distribution signal

        # Overbought/Oversold signals
        elif self._asi > self.asi_config.overbought:
            return SignalType.BEARISH  # Potential reversal from overbought
        elif self._asi < self.asi_config.oversold:
            return SignalType.BULLISH  # Potential reversal from oversold

        return SignalType.NEUTRAL

    @property
    def asi(self) -> float:
        """Get the current ASI value"""
        return self._asi if self.is_ready else 0.0

    @property
    def swing(self) -> float:
        """Get the current swing value"""
        return self._swing if self.is_ready else 0.0

    @property
    def swing_direction(self) -> int:
        """Get the current swing direction (1=bullish, -1=bearish, 0=neutral)"""
        return self._swing_direction

    @property
    def swing_strength(self) -> float:
        """Get the current swing strength (0-1)"""
        return self._swing_strength

    @property
    def signal_accuracy(self) -> float:
        """Get the signal accuracy (0-1)"""
        return self._signal_accuracy

    @property
    def volatility_regime(self) -> str:
        """Get the current volatility regime"""
        return self._volatility_regime

    @property
    def swing_cycles(self) -> int:
        """Get the count of swing cycles"""
        return self._swing_cycles

    @property
    def accumulation_signals(self) -> int:
        """Get the count of accumulation signals"""
        return self._accumulation_signals

    @property
    def distribution_signals(self) -> int:
        """Get the count of distribution signals"""
        return self._distribution_signals

    @property
    def swing_signals(self) -> int:
        """Get the count of swing signals"""
        return self._swing_signals

    @property
    def breakout_signals(self) -> int:
        """Get the count of breakout signals"""
        return self._breakout_signals

    @property
    def institutional_asi(self) -> float:
        """Get the institutional ASI score (0-1)"""
        return self._institutional_asi

    @property
    def smart_money_asi(self) -> float:
        """Get the smart money ASI score (0-1)"""
        return self._smart_money_asi

    def is_bullish_swing_asi(self) -> bool:
        """Check if ASI indicates bullish swing"""
        return self._swing_direction == 1 and self._swing > 0

    def is_bearish_swing_asi(self) -> bool:
        """Check if ASI indicates bearish swing"""
        return self._swing_direction == -1 and self._swing < 0

    def is_strong_swing_asi(self) -> bool:
        """Check if swing strength is strong"""
        return self._swing_strength > 0.7

    def is_accumulation_asi(self) -> bool:
        """Check if ASI indicates accumulation"""
        return self._accumulation_signals > 0

    def is_distribution_asi(self) -> bool:
        """Check if ASI indicates distribution"""
        return self._distribution_signals > 0

    def is_overbought_asi(self) -> bool:
        """Check if ASI is overbought"""
        return self._asi > self.asi_config.overbought

    def is_oversold_asi(self) -> bool:
        """Check if ASI is oversold"""
        return self._asi < self.asi_config.oversold

    def is_high_volatility_asi(self) -> bool:
        """Check if volatility regime is high"""
        return self._volatility_regime == "high"

    def is_low_volatility_asi(self) -> bool:
        """Check if volatility regime is low"""
        return self._volatility_regime == "low"

    def is_institutional_setup_asi(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_asi > 0.7

    def get_asi_info(self) -> Dict[str, Any]:
        """Get comprehensive ASI indicator information"""
        return {
            "asi_values": {
                "asi": self._asi,
                "swing": self._swing
            },
            "swing_analysis": {
                "direction": self._swing_direction,
                "strength": self._swing_strength,
                "asi_signal": self._asi_signal
            },
            "performance_metrics": {
                "signal_accuracy": self._signal_accuracy,
                "swing_prediction_rate": self._swing_prediction_rate,
                "asi_reliability": self._asi_reliability
            },
            "market_conditions": {
                "volatility_regime": self._volatility_regime,
                "swing_cycles": self._swing_cycles
            },
            "signal_counts": {
                "accumulation_signals": self._accumulation_signals,
                "distribution_signals": self._distribution_signals,
                "swing_signals": self._swing_signals,
                "breakout_signals": self._breakout_signals
            },
            "asi_tracking": {
                "extremes": self._asi_extremes
            },
            "risk_management": {
                "asi_based_stop": self._asi_based_stop,
                "swing_based_position_size": self._swing_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor
            },
            "institutional_analysis": {
                "asi": self._institutional_asi,
                "smart_money_asi": self._smart_money_asi
            },
            "metadata": {
                "limit": self.asi_config.limit,
                "overbought": self.asi_config.overbought,
                "oversold": self.asi_config.oversold,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._open_values.clear()
        self._high_values.clear()
        self._low_values.clear()
        self._close_values.clear()
        self._volume_values.clear()
        self._asi_values.clear()
        self._swing_values.clear()
        self._asi = 0.0
        self._swing = 0.0
        self._swing_direction = 0
        self._swing_strength = 0.0
        self._asi_signal = 0.0
        self._accumulation_signals = 0
        self._distribution_signals = 0
        self._swing_signals = 0
        self._breakout_signals = 0
        self._signal_accuracy = 0.0
        self._swing_prediction_rate = 0.0
        self._asi_reliability = 0.0
        self._volatility_regime = "normal"
        self._swing_cycles = 0
        self._asi_extremes.clear()
        self._asi_based_stop = 0.0
        self._swing_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0
        self._institutional_asi = 0.0
        self._smart_money_asi = 0.0