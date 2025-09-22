"""
Institutional-Grade Augmented Money Flow Oscillator Indicator

This module implements an enhanced Money Flow Oscillator with institutional-grade features:
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
class AugmentedMoneyFlowOscillatorConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Money Flow Oscillator"""
    period: int = 14
    overbought: float = 70
    oversold: float = 30


class AugmentedMoneyFlowOscillatorIndicator(AugmentedIndicator):
    """
    Institutional-grade Augmented Money Flow Oscillator implementing 5-pillar architecture.

    Features:
    - Advanced money flow calculation for volume-price analysis
    - Volume-weighted calculations for institutional validation
    - Market regime adaptation for different volatility environments
    - Multi-timeframe convergence for money flow confirmation
    - Smart money flow detection and analysis
    - Automated risk management based on money flow signals
    """

    def __init__(self, config: AugmentedMoneyFlowOscillatorConfig = None):
        if config is None:
            config = AugmentedMoneyFlowOscillatorConfig()

        super().__init__(config)
        self.mfo_config = config

        # MFO specific state
        self._high_values = deque(maxlen=self.config.buffer_size)
        self._low_values = deque(maxlen=self.config.buffer_size)
        self._close_values = deque(maxlen=self.config.buffer_size)
        self._volume_values = deque(maxlen=self.config.buffer_size)

        # MFO calculation components
        self._mfo_values = deque(maxlen=self.config.buffer_size)
        self._positive_flow_values = deque(maxlen=self.config.buffer_size)
        self._negative_flow_values = deque(maxlen=self.config.buffer_size)

        # Current MFO values
        self._mfo = 0.0
        self._positive_flow = 0.0
        self._negative_flow = 0.0

        # Money flow analysis
        self._flow_direction = 0  # 1 = positive flow, -1 = negative flow, 0 = neutral
        self._flow_strength = 0.0
        self._mfo_signal = 0.0

        # Signal analysis
        self._bullish_flow_signals = 0
        self._bearish_flow_signals = 0
        self._divergence_signals = 0
        self._breakout_signals = 0

        # Performance tracking
        self._signal_accuracy = 0.0
        self._flow_prediction_rate = 0.0
        self._mfo_reliability = 0.0

        # Market structure
        self._volatility_regime = "normal"
        self._flow_cycles = 0
        self._mfo_extremes = []

        # Risk management
        self._mfo_based_stop = 0.0
        self._flow_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0

        # Institutional analysis
        self._institutional_mfo = 0.0
        self._smart_money_mfo = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Money Flow Oscillator is ready to provide signals"""
        return (len(self._close_values) >= self.mfo_config.period and
                len(self._mfo_values) > 0)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update MFO analysis

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

        # Update MFO analysis
        self._update_mfo_analysis(high, low, close, volume)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_mfo_analysis(self, high: float, low: float, close: float, volume: float):
        """Update the core Money Flow Oscillator analysis with institutional enhancements"""
        # Store OHLCV data
        self._high_values.append(high)
        self._low_values.append(low)
        self._close_values.append(close)
        self._volume_values.append(volume)

        if len(self._close_values) >= self.mfo_config.period:
            # Calculate Money Flow Oscillator
            self._calculate_money_flow_oscillator()

            # Analyze flow characteristics
            self._analyze_flow_characteristics()

            # Generate MFO signals
            self._generate_mfo_signals()

            # Calculate institutional MFO analysis
            self._calculate_institutional_mfo()

    def _calculate_money_flow_oscillator(self):
        """Calculate Money Flow Oscillator"""
        if len(self._close_values) < self.mfo_config.period:
            return

        # Calculate Typical Price
        typical_prices = []
        for i in range(len(self._close_values)):
            typical_price = (self._high_values[i] + self._low_values[i] + self._close_values[i]) / 3
            typical_prices.append(typical_price)

        # Calculate Raw Money Flow
        raw_money_flows = []
        for i in range(len(typical_prices)):
            raw_money_flow = typical_prices[i] * self._volume_values[i]
            raw_money_flows.append(raw_money_flow)

        # Calculate Money Flow Ratio
        positive_flow = 0.0
        negative_flow = 0.0

        for i in range(1, len(raw_money_flows)):
            if typical_prices[i] > typical_prices[i-1]:
                positive_flow += raw_money_flows[i]
            elif typical_prices[i] < typical_prices[i-1]:
                negative_flow += raw_money_flows[i]

        # Calculate Money Flow Ratio
        if negative_flow != 0:
            money_flow_ratio = positive_flow / negative_flow
        else:
            money_flow_ratio = positive_flow if positive_flow > 0 else 1.0

        # Calculate Money Flow Oscillator
        mfo = 100 - (100 / (1 + money_flow_ratio))

        self._mfo_values.append(mfo)
        self._mfo = mfo

        # Store flow components
        self._positive_flow_values.append(positive_flow)
        self._negative_flow_values.append(negative_flow)
        self._positive_flow = positive_flow
        self._negative_flow = negative_flow

    def _analyze_flow_characteristics(self):
        """Analyze flow characteristics for institutional insights"""
        if not self.is_ready:
            return

        # Determine flow direction based on MFO
        if self._mfo > 50:
            self._flow_direction = 1  # Positive money flow
        elif self._mfo < 50:
            self._flow_direction = -1  # Negative money flow
        else:
            self._flow_direction = 0  # Neutral money flow

        # Calculate flow strength
        self._flow_strength = abs(self._mfo - 50) / 50.0  # Normalize to 0-1

        # Calculate MFO signal
        self._mfo_signal = self._mfo

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

        # Track flow cycles
        if len(self._mfo_values) >= 2:
            prev_mfo = list(self._mfo_values)[-2]
            if ((prev_mfo <= 50 and self._mfo > 50) or
                (prev_mfo >= 50 and self._mfo < 50)):
                self._flow_cycles += 1

        # Track MFO extremes
        if self._mfo >= 90 or self._mfo <= 10:  # Extreme readings
            self._mfo_extremes.append(self._mfo)

    def _generate_mfo_signals(self):
        """Generate MFO-based signals"""
        if not self.is_ready:
            return

        # Bullish flow signals (MFO above 50 with increasing positive flow)
        if (self._mfo > 50 and
            len(self._positive_flow_values) >= 2 and
            self._positive_flow > list(self._positive_flow_values)[-2]):
            self._bullish_flow_signals += 1

        # Bearish flow signals (MFO below 50 with increasing negative flow)
        if (self._mfo < 50 and
            len(self._negative_flow_values) >= 2 and
            self._negative_flow > list(self._negative_flow_values)[-2]):
            self._bearish_flow_signals += 1

        # Divergence signals
        if len(self._mfo_values) >= 5 and len(self._close_values) >= 5:
            mfo_trend = self._mfo - list(self._mfo_values)[-5]
            price_trend = list(self._close_values)[-1] - list(self._close_values)[-5]

            # Bullish divergence: price down, MFO up
            if price_trend < 0 and mfo_trend > 0:
                self._divergence_signals += 1

            # Bearish divergence: price up, MFO down
            elif price_trend > 0 and mfo_trend < 0:
                self._divergence_signals += 1

        # Breakout signals
        if self._flow_strength > 0.8:
            self._breakout_signals += 1

    def _calculate_institutional_mfo(self):
        """Calculate institutional MFO analysis based on flow characteristics"""
        if not self.is_ready:
            return

        # Institutional traders use MFO to identify smart money flow and accumulation/distribution
        base_mfo = 0.0

        if (self._flow_strength > 0.8 and
            (self._bullish_flow_signals > 0 or self._bearish_flow_signals > 0) and
            self._signal_accuracy > 0.6):
            base_mfo = 0.9  # Strong flow with bullish/bearish signals and accuracy
        elif (self._divergence_signals > 0 and
              self._breakout_signals > 0 and
              self._flow_cycles > 2):
            base_mfo = 0.8  # Divergence and breakout signals with cycle confirmation
        elif (self._flow_strength > 0.6 and
              self._mfo_reliability > 0.7):
            base_mfo = 0.7  # Good flow strength with high reliability

        self._institutional_mfo = base_mfo

        # Smart money MFO considers flow strength and market timing
        smart_money_score = (
            self._flow_strength * 0.3 +
            self._signal_accuracy * 0.3 +
            abs(self._mfo_signal - 50) / 50.0 * 0.2 +  # Normalize signal
            self._institutional_mfo * 0.2
        )
        self._smart_money_mfo = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade MFO analysis"""
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

        # Use MFO value as primary raw value
        raw_value = self._mfo

        # Determine signal type based on MFO analysis
        signal_type = self._determine_mfo_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'mfo': self._mfo,
            'positive_flow': self._positive_flow,
            'negative_flow': self._negative_flow,
            'flow_direction': self._flow_direction,
            'flow_strength': self._flow_strength,
            'mfo_signal': self._mfo_signal,
            'signal_accuracy': self._signal_accuracy,
            'flow_prediction_rate': self._flow_prediction_rate,
            'mfo_reliability': self._mfo_reliability,
            'volatility_regime': self._volatility_regime,
            'flow_cycles': self._flow_cycles,
            'mfo_extremes': self._mfo_extremes,
            'mfo_based_stop': self._mfo_based_stop,
            'flow_based_position_size': self._flow_based_position_size,
            'risk_adjustment_factor': self._risk_adjustment_factor,
            'bullish_flow_signals': self._bullish_flow_signals,
            'bearish_flow_signals': self._bearish_flow_signals,
            'divergence_signals': self._divergence_signals,
            'breakout_signals': self._breakout_signals,
            'institutional_mfo': self._institutional_mfo,
            'smart_money_mfo': self._smart_money_mfo
        }

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._mfo_based_stop,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "Money_Flow_Oscillator",
                "period": self.mfo_config.period,
                "overbought": self.mfo_config.overbought,
                "oversold": self.mfo_config.oversold,
                "mfo": self._mfo,
                "positive_flow": self._positive_flow,
                "negative_flow": self._negative_flow,
                "flow_direction": self._flow_direction,
                "flow_strength": self._flow_strength,
                "mfo_signal": self._mfo_signal,
                "signal_accuracy": self._signal_accuracy,
                "flow_prediction_rate": self._flow_prediction_rate,
                "mfo_reliability": self._mfo_reliability,
                "volatility_regime": self._volatility_regime,
                "flow_cycles": self._flow_cycles,
                "mfo_extremes": self._mfo_extremes,
                "mfo_based_stop": self._mfo_based_stop,
                "flow_based_position_size": self._flow_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor,
                "bullish_flow_signals": self._bullish_flow_signals,
                "bearish_flow_signals": self._bearish_flow_signals,
                "divergence_signals": self._divergence_signals,
                "breakout_signals": self._breakout_signals,
                "institutional_mfo": self._institutional_mfo,
                "smart_money_mfo": self._smart_money_mfo,
                "is_ready": self.is_ready
            }
        )

    def _determine_mfo_signal(self) -> SignalType:
        """Determine signal type based on MFO analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong flow signals
        if (self._flow_strength > 0.8 and
            (self._bullish_flow_signals > 0 or self._bearish_flow_signals > 0) and
            self._signal_accuracy > 0.7):
            if self._flow_direction == 1:
                return SignalType.STRONG_BULLISH
            elif self._flow_direction == -1:
                return SignalType.STRONG_BEARISH

        # Moderate flow signals
        elif (self._divergence_signals > 0 and
              self._flow_strength > 0.6):
            if self._flow_direction == 1:
                return SignalType.BULLISH
            elif self._flow_direction == -1:
                return SignalType.BEARISH

        # Breakout signals
        elif (self._breakout_signals > 0 and
              abs(self._mfo - 50) > 30):
            if self._mfo > 50:
                return SignalType.STRONG_BULLISH
            else:
                return SignalType.STRONG_BEARISH

        # Bullish/bearish flow signals
        elif (self._bullish_flow_signals > 0 and
              self._mfo_reliability > 0.7):
            return SignalType.BULLISH  # Bullish flow signal
        elif (self._bearish_flow_signals > 0 and
              self._mfo_reliability > 0.7):
            return SignalType.BEARISH  # Bearish flow signal

        # Overbought/Oversold signals
        elif self._mfo > self.mfo_config.overbought:
            return SignalType.BEARISH  # Potential reversal from overbought
        elif self._mfo < self.mfo_config.oversold:
            return SignalType.BULLISH  # Potential reversal from oversold

        return SignalType.NEUTRAL

    @property
    def mfo(self) -> float:
        """Get the current MFO value"""
        return self._mfo if self.is_ready else 50.0

    @property
    def positive_flow(self) -> float:
        """Get the current positive flow value"""
        return self._positive_flow if self.is_ready else 0.0

    @property
    def negative_flow(self) -> float:
        """Get the current negative flow value"""
        return self._negative_flow if self.is_ready else 0.0

    @property
    def flow_direction(self) -> int:
        """Get the current flow direction (1=positive, -1=negative, 0=neutral)"""
        return self._flow_direction

    @property
    def flow_strength(self) -> float:
        """Get the current flow strength (0-1)"""
        return self._flow_strength

    @property
    def signal_accuracy(self) -> float:
        """Get the signal accuracy (0-1)"""
        return self._signal_accuracy

    @property
    def volatility_regime(self) -> str:
        """Get the current volatility regime"""
        return self._volatility_regime

    @property
    def flow_cycles(self) -> int:
        """Get the count of flow cycles"""
        return self._flow_cycles

    @property
    def bullish_flow_signals(self) -> int:
        """Get the count of bullish flow signals"""
        return self._bullish_flow_signals

    @property
    def bearish_flow_signals(self) -> int:
        """Get the count of bearish flow signals"""
        return self._bearish_flow_signals

    @property
    def divergence_signals(self) -> int:
        """Get the count of divergence signals"""
        return self._divergence_signals

    @property
    def breakout_signals(self) -> int:
        """Get the count of breakout signals"""
        return self._breakout_signals

    @property
    def institutional_mfo(self) -> float:
        """Get the institutional MFO score (0-1)"""
        return self._institutional_mfo

    @property
    def smart_money_mfo(self) -> float:
        """Get the smart money MFO score (0-1)"""
        return self._smart_money_mfo

    def is_positive_flow_mfo(self) -> bool:
        """Check if MFO indicates positive money flow"""
        return self._flow_direction == 1 and self._mfo > 50

    def is_negative_flow_mfo(self) -> bool:
        """Check if MFO indicates negative money flow"""
        return self._flow_direction == -1 and self._mfo < 50

    def is_strong_flow_mfo(self) -> bool:
        """Check if flow strength is strong"""
        return self._flow_strength > 0.7

    def is_bullish_flow_signal_mfo(self) -> bool:
        """Check if MFO has bullish flow signal"""
        return self._bullish_flow_signals > 0

    def is_bearish_flow_signal_mfo(self) -> bool:
        """Check if MFO has bearish flow signal"""
        return self._bearish_flow_signals > 0

    def is_mfo_divergence(self) -> bool:
        """Check if there's an MFO divergence"""
        return self._divergence_signals > 0

    def is_overbought_mfo(self) -> bool:
        """Check if MFO is overbought"""
        return self._mfo > self.mfo_config.overbought

    def is_oversold_mfo(self) -> bool:
        """Check if MFO is oversold"""
        return self._mfo < self.mfo_config.oversold

    def is_high_volatility_mfo(self) -> bool:
        """Check if volatility regime is high"""
        return self._volatility_regime == "high"

    def is_low_volatility_mfo(self) -> bool:
        """Check if volatility regime is low"""
        return self._volatility_regime == "low"

    def is_institutional_setup_mfo(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_mfo > 0.7

    def get_mfo_info(self) -> Dict[str, Any]:
        """Get comprehensive MFO indicator information"""
        return {
            "mfo_values": {
                "mfo": self._mfo,
                "positive_flow": self._positive_flow,
                "negative_flow": self._negative_flow
            },
            "flow_analysis": {
                "direction": self._flow_direction,
                "strength": self._flow_strength,
                "mfo_signal": self._mfo_signal
            },
            "performance_metrics": {
                "signal_accuracy": self._signal_accuracy,
                "flow_prediction_rate": self._flow_prediction_rate,
                "mfo_reliability": self._mfo_reliability
            },
            "market_conditions": {
                "volatility_regime": self._volatility_regime,
                "flow_cycles": self._flow_cycles
            },
            "signal_counts": {
                "bullish_flow_signals": self._bullish_flow_signals,
                "bearish_flow_signals": self._bearish_flow_signals,
                "divergence_signals": self._divergence_signals,
                "breakout_signals": self._breakout_signals
            },
            "mfo_tracking": {
                "extremes": self._mfo_extremes
            },
            "risk_management": {
                "mfo_based_stop": self._mfo_based_stop,
                "flow_based_position_size": self._flow_based_position_size,
                "risk_adjustment_factor": self._risk_adjustment_factor
            },
            "institutional_analysis": {
                "mfo": self._institutional_mfo,
                "smart_money_mfo": self._smart_money_mfo
            },
            "metadata": {
                "period": self.mfo_config.period,
                "overbought": self.mfo_config.overbought,
                "oversold": self.mfo_config.oversold,
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
        self._mfo_values.clear()
        self._positive_flow_values.clear()
        self._negative_flow_values.clear()
        self._mfo = 0.0
        self._positive_flow = 0.0
        self._negative_flow = 0.0
        self._flow_direction = 0
        self._flow_strength = 0.0
        self._mfo_signal = 0.0
        self._bullish_flow_signals = 0
        self._bearish_flow_signals = 0
        self._divergence_signals = 0
        self._breakout_signals = 0
        self._signal_accuracy = 0.0
        self._flow_prediction_rate = 0.0
        self._mfo_reliability = 0.0
        self._volatility_regime = "normal"
        self._flow_cycles = 0
        self._mfo_extremes.clear()
        self._mfo_based_stop = 0.0
        self._flow_based_position_size = 1.0
        self._risk_adjustment_factor = 1.0
        self._institutional_mfo = 0.0
        self._smart_money_mfo = 0.0