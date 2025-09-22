"""
Institutional-Grade Augmented Donchian Channels Indicator

This module implements an enhanced Donchian Channels indicator with institutional-grade features:
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

from nautilus_trader_engine.indicators.base import (
    AugmentedIndicator,
    AugmentedIndicatorConfig,
    IndicatorSignal,
    SignalType,
)


@dataclass
class AugmentedDonchianConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Donchian Channels"""
    period: int = 20
    breakout_threshold: float = 0.8  # Percentage of channel for breakout
    midline_threshold: float = 0.1  # Percentage from midline for signals


class AugmentedDonchian(AugmentedIndicator):
    """
    Institutional-grade Augmented Donchian Channels indicator implementing 5-pillar architecture.

    Features:
    - Channel breakout analysis using highest high/lowest low
    - Breakout probability assessment and confirmation
    - Market regime adaptation based on channel behavior
    - Multi-timeframe convergence for institutional confirmation
    - Smart money breakout analysis for institutional flow detection
    - Automated risk management for breakout-based strategies
    """

    def __init__(self, config: AugmentedDonchianConfig = None):
        if config is None:
            config = AugmentedDonchianConfig()

        super().__init__(config)
        self.donchian_config = config

        # Donchian Channels specific state
        self._highs = deque(maxlen=self.config.buffer_size)
        self._lows = deque(maxlen=self.config.buffer_size)
        self._closes = deque(maxlen=self.config.buffer_size)

        # Channel values
        self._channel_high = None
        self._channel_low = None
        self._channel_midline = None
        self._channel_width = 0.0

        # Price position analysis
        self._price_position = 0.0  # Position within channel (-1 to 1)
        self._distance_from_midline = 0.0

        # Breakout analysis
        self._breakout_probability = 0.0
        self._breakout_direction = 0  # -1, 0, 1 for down, neutral, up
        self._breakout_strength = 0.0

        # Channel analysis
        self._channel_trend = "neutral"  # "expanding", "contracting", "stable"
        self._channel_volatility = 0.0
        self._channel_efficiency = 0.0

        # Signal analysis
        self._breakout_signals = 0
        self._rejection_signals = 0
        self._continuation_signals = 0
        self._reversal_signals = 0

        # Market structure
        self._channel_touches = 0
        self._channel_tests = 0
        self._channel_penetrations = 0

        # Institutional analysis
        self._institutional_donchian = 0.0
        self._smart_money_channels = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Donchian Channels is ready to provide signals"""
        return (self._channel_high is not None and
                self._channel_low is not None and
                len(self._highs) >= self.donchian_config.period)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update Donchian Channels analysis

        Args:
            bar (Bar): New bar data
        """
        # Extract OHLC data
        if hasattr(bar, 'high') and hasattr(bar, 'low') and hasattr(bar, 'close'):
            high = bar.high
            low = bar.low
            close = bar.close
        else:
            high = bar.get('high', bar.get('close', 0.0))
            low = bar.get('low', bar.get('close', 0.0))
            close = bar.get('close', bar.get('price', 0.0))

        # Update Donchian Channels calculation
        self._update_donchian_channels(high, low, close)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_donchian_channels(self, high: float, low: float, close: float):
        """Update the core Donchian Channels calculation with institutional enhancements"""
        self._highs.append(high)
        self._lows.append(low)
        self._closes.append(close)

        if len(self._highs) >= self.donchian_config.period:
            # Calculate channel boundaries
            highs_list = list(self._highs)[-self.donchian_config.period:]
            lows_list = list(self._lows)[-self.donchian_config.period:]

            self._channel_high = max(highs_list)
            self._channel_low = min(lows_list)
            self._channel_midline = (self._channel_high + self._channel_low) / 2

            # Calculate channel width
            if self._channel_midline > 0:
                self._channel_width = (self._channel_high - self._channel_low) / self._channel_midline
            else:
                self._channel_width = 0.0

            # Calculate price position within channel
            if self._channel_high != self._channel_low:
                self._price_position = (close - self._channel_low) / (self._channel_high - self._channel_low) * 2 - 1
                self._price_position = max(-1.0, min(1.0, self._price_position))
            else:
                self._price_position = 0.0

            # Calculate distance from midline
            if self._channel_midline > 0:
                self._distance_from_midline = abs(close - self._channel_midline) / self._channel_midline
            else:
                self._distance_from_midline = 0.0

            # Analyze channel characteristics
            self._analyze_channel_characteristics(close)

    def _analyze_channel_characteristics(self, current_price: float):
        """Analyze Donchian Channels characteristics for institutional insights"""
        if not self.is_ready:
            return

        # Calculate breakout probability
        breakout_threshold = self.donchian_config.breakout_threshold

        if abs(self._price_position) > breakout_threshold:
            self._breakout_probability = min(1.0, abs(self._price_position))
            self._breakout_direction = 1 if self._price_position > 0 else -1
            self._breakout_strength = abs(self._price_position)
        else:
            self._breakout_probability = 0.0
            self._breakout_direction = 0
            self._breakout_strength = 0.0

        # Analyze channel trend
        if len(self._highs) >= self.donchian_config.period * 2:
            # Compare current channel with previous channel
            prev_highs = list(self._highs)[-self.donchian_config.period*2:-self.donchian_config.period]
            prev_lows = list(self._lows)[-self.donchian_config.period*2:-self.donchian_config.period]

            if prev_highs and prev_lows:
                prev_channel_width = (max(prev_highs) - min(prev_lows)) / ((max(prev_highs) + min(prev_lows)) / 2) if (max(prev_highs) + min(prev_lows)) > 0 else 0.0

                if self._channel_width > prev_channel_width * 1.1:
                    self._channel_trend = "expanding"
                elif self._channel_width < prev_channel_width * 0.9:
                    self._channel_trend = "contracting"
                else:
                    self._channel_trend = "stable"

        # Calculate channel volatility
        if self._channel_width > 0:
            self._channel_volatility = min(1.0, self._channel_width * 10)  # Scale for 0-1 range

        # Calculate channel efficiency (how well price uses the channel)
        if len(self._closes) >= self.donchian_config.period:
            closes_list = list(self._closes)[-self.donchian_config.period:]
            channel_range = self._channel_high - self._channel_low

            if channel_range > 0:
                price_range = max(closes_list) - min(closes_list)
                self._channel_efficiency = price_range / channel_range
            else:
                self._channel_efficiency = 0.0

        # Track channel interactions
        if abs(current_price - self._channel_high) / current_price < 0.001:
            self._channel_touches += 1
        elif abs(current_price - self._channel_low) / current_price < 0.001:
            self._channel_touches += 1

        # Generate signals
        self._generate_donchian_signals(current_price)

        # Calculate institutional Donchian analysis
        self._calculate_institutional_donchian()

    def _generate_donchian_signals(self, current_price: float):
        """Generate Donchian Channels-based signals"""
        if not self.is_ready:
            return

        # Breakout signals
        if (self._breakout_probability > self.donchian_config.breakout_threshold and
            self._breakout_strength > 0.8):
            self._breakout_signals += 1

        # Rejection signals (price touches channel boundary but reverses)
        if (self._channel_touches > 0 and
            abs(self._price_position) < 0.9 and
            self._breakout_probability < 0.5):
            self._rejection_signals += 1

        # Continuation signals (price moves within channel midline)
        if (abs(self._price_position) < self.donchian_config.midline_threshold and
            self._channel_efficiency > 0.7):
            self._continuation_signals += 1

        # Reversal signals (price breaks channel and holds)
        if (self._breakout_signals > 0 and
            self._channel_efficiency > 0.8 and
            self._channel_trend == "expanding"):
            self._reversal_signals += 1

    def _calculate_institutional_donchian(self):
        """Calculate institutional Donchian analysis based on channel characteristics"""
        if not self.is_ready:
            return

        # Institutional traders use Donchian Channels for breakout and range trading
        base_donchian = 0.0

        if (self._breakout_signals > 0 and
            self._breakout_probability > 0.8 and
            self._channel_volatility > 0.6):
            base_donchian = 0.9  # Strong breakout with high volatility
        elif (self._rejection_signals > 0 and
              self._channel_touches > 2 and
              self._channel_trend == "contracting"):
            base_donchian = 0.7  # Rejection at channel boundaries in contracting channel
        elif (self._continuation_signals > 0 and
              self._channel_efficiency > 0.8):
            base_donchian = 0.6  # Efficient price movement within channel

        self._institutional_donchian = base_donchian

        # Smart money channels considers breakout strength and channel efficiency
        smart_money_score = (
            self._breakout_probability * 0.4 +
            self._channel_efficiency * 0.3 +
            self._channel_volatility * 0.2 +
            self._institutional_donchian * 0.1
        )
        self._smart_money_channels = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade Donchian Channels analysis"""
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

        # Use channel width as primary raw value
        raw_value = self._channel_width

        # Determine signal type based on Donchian Channels analysis
        signal_type = self._determine_donchian_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'price_position': self._price_position,
            'distance_from_midline': self._distance_from_midline,
            'breakout_probability': self._breakout_probability,
            'breakout_direction': self._breakout_direction,
            'breakout_strength': self._breakout_strength,
            'channel_trend': self._channel_trend,
            'channel_volatility': self._channel_volatility,
            'channel_efficiency': self._channel_efficiency,
            'breakout_signals': self._breakout_signals,
            'rejection_signals': self._rejection_signals,
            'continuation_signals': self._continuation_signals,
            'reversal_signals': self._reversal_signals,
            'channel_touches': self._channel_touches,
            'channel_tests': self._channel_tests,
            'channel_penetrations': self._channel_penetrations,
            'institutional_donchian': self._institutional_donchian,
            'smart_money_channels': self._smart_money_channels
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
                "indicator": "Donchian_Channels",
                "period": self.donchian_config.period,
                "breakout_threshold": self.donchian_config.breakout_threshold,
                "midline_threshold": self.donchian_config.midline_threshold,
                "channel_high": self._channel_high,
                "channel_low": self._channel_low,
                "channel_midline": self._channel_midline,
                "channel_width": self._channel_width,
                "price_position": self._price_position,
                "distance_from_midline": self._distance_from_midline,
                "breakout_probability": self._breakout_probability,
                "breakout_direction": self._breakout_direction,
                "breakout_strength": self._breakout_strength,
                "channel_trend": self._channel_trend,
                "channel_volatility": self._channel_volatility,
                "channel_efficiency": self._channel_efficiency,
                "breakout_signals": self._breakout_signals,
                "rejection_signals": self._rejection_signals,
                "continuation_signals": self._continuation_signals,
                "reversal_signals": self._reversal_signals,
                "channel_touches": self._channel_touches,
                "channel_tests": self._channel_tests,
                "channel_penetrations": self._channel_penetrations,
                "institutional_donchian": self._institutional_donchian,
                "smart_money_channels": self._smart_money_channels,
                "is_ready": self.is_ready
            }
        )

    def _determine_donchian_signal(self) -> SignalType:
        """Determine signal type based on Donchian Channels analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong breakout signals
        if (self._breakout_probability > 0.9 and
            self._breakout_strength > 0.9 and
            self._channel_volatility > 0.7):
            if self._breakout_direction > 0:
                return SignalType.STRONG_BULLISH
            else:
                return SignalType.STRONG_BEARISH

        # Moderate breakout signals
        elif (self._breakout_probability > self.donchian_config.breakout_threshold and
              self._breakout_signals > 0):
            if self._breakout_direction > 0:
                return SignalType.BULLISH
            else:
                return SignalType.BEARISH

        # Rejection signals
        elif (self._rejection_signals > 0 and
              self._channel_touches > 1):
            if self._price_position > 0:
                return SignalType.BEARISH  # Rejection at upper channel
            else:
                return SignalType.BULLISH  # Rejection at lower channel

        # Continuation signals
        elif (self._continuation_signals > 0 and
              abs(self._price_position) < self.donchian_config.midline_threshold):
            return SignalType.NEUTRAL  # Good for range trading

        # Reversal signals
        elif (self._reversal_signals > 0 and
              self._channel_efficiency > 0.8):
            if self._breakout_direction > 0:
                return SignalType.BULLISH
            else:
                return SignalType.BEARISH

        return SignalType.NEUTRAL

    @property
    def channel_high(self) -> float:
        """Get the current channel high"""
        return self._channel_high if self.is_ready else 0.0

    @property
    def channel_low(self) -> float:
        """Get the current channel low"""
        return self._channel_low if self.is_ready else 0.0

    @property
    def channel_midline(self) -> float:
        """Get the current channel midline"""
        return self._channel_midline if self.is_ready else 0.0

    @property
    def channel_width(self) -> float:
        """Get the current channel width"""
        return self._channel_width

    @property
    def price_position(self) -> float:
        """Get the current price position within channel (-1 to 1)"""
        return self._price_position

    @property
    def distance_from_midline(self) -> float:
        """Get the current distance from midline"""
        return self._distance_from_midline

    @property
    def breakout_probability(self) -> float:
        """Get the current breakout probability (0-1)"""
        return self._breakout_probability

    @property
    def breakout_direction(self) -> int:
        """Get the current breakout direction (-1, 0, 1)"""
        return self._breakout_direction

    @property
    def breakout_strength(self) -> float:
        """Get the current breakout strength (0-1)"""
        return self._breakout_strength

    @property
    def channel_trend(self) -> str:
        """Get the current channel trend"""
        return self._channel_trend

    @property
    def channel_volatility(self) -> float:
        """Get the current channel volatility (0-1)"""
        return self._channel_volatility

    @property
    def channel_efficiency(self) -> float:
        """Get the current channel efficiency (0-1)"""
        return self._channel_efficiency

    @property
    def breakout_signals(self) -> int:
        """Get the count of breakout signals"""
        return self._breakout_signals

    @property
    def rejection_signals(self) -> int:
        """Get the count of rejection signals"""
        return self._rejection_signals

    @property
    def continuation_signals(self) -> int:
        """Get the count of continuation signals"""
        return self._continuation_signals

    @property
    def reversal_signals(self) -> int:
        """Get the count of reversal signals"""
        return self._reversal_signals

    @property
    def channel_touches(self) -> int:
        """Get the count of channel touches"""
        return self._channel_touches

    @property
    def channel_tests(self) -> int:
        """Get the count of channel tests"""
        return self._channel_tests

    @property
    def channel_penetrations(self) -> int:
        """Get the count of channel penetrations"""
        return self._channel_penetrations

    @property
    def institutional_donchian(self) -> float:
        """Get the institutional Donchian score (0-1)"""
        return self._institutional_donchian

    @property
    def smart_money_channels(self) -> float:
        """Get the smart money channels score (0-1)"""
        return self._smart_money_channels

    def is_price_near_upper_channel(self) -> bool:
        """Check if price is near upper channel"""
        return self._price_position > 0.8

    def is_price_near_lower_channel(self) -> bool:
        """Check if price is near lower channel"""
        return self._price_position < -0.8

    def is_price_at_midline(self) -> bool:
        """Check if price is at channel midline"""
        return abs(self._price_position) < self.donchian_config.midline_threshold

    def is_channel_expanding(self) -> bool:
        """Check if channel is expanding"""
        return self._channel_trend == "expanding"

    def is_channel_contracting(self) -> bool:
        """Check if channel is contracting"""
        return self._channel_trend == "contracting"

    def is_channel_stable(self) -> bool:
        """Check if channel is stable"""
        return self._channel_trend == "stable"

    def is_high_volatility_channel(self) -> bool:
        """Check if channel has high volatility"""
        return self._channel_volatility > 0.7

    def is_efficient_channel(self) -> bool:
        """Check if channel is efficient"""
        return self._channel_efficiency > 0.8

    def is_breakout_confirmed(self) -> bool:
        """Check if breakout is confirmed"""
        return self._breakout_probability > self.donchian_config.breakout_threshold

    def is_rejection_present(self) -> bool:
        """Check if rejection is present"""
        return self._rejection_signals > 0

    def is_continuation_present(self) -> bool:
        """Check if continuation is present"""
        return self._continuation_signals > 0

    def is_reversal_present(self) -> bool:
        """Check if reversal is present"""
        return self._reversal_signals > 0

    def is_institutional_setup(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_donchian > 0.7

    def get_donchian_info(self) -> Dict[str, Any]:
        """Get comprehensive Donchian Channels information"""
        return {
            "channel_values": {
                "high": self.channel_high,
                "low": self.channel_low,
                "midline": self.channel_midline,
                "width": self.channel_width
            },
            "price_analysis": {
                "position": self._price_position,
                "distance_from_midline": self._distance_from_midline
            },
            "breakout_analysis": {
                "probability": self._breakout_probability,
                "direction": self._breakout_direction,
                "strength": self._breakout_strength
            },
            "channel_analysis": {
                "trend": self._channel_trend,
                "volatility": self._channel_volatility,
                "efficiency": self._channel_efficiency
            },
            "signal_analysis": {
                "breakout_signals": self._breakout_signals,
                "rejection_signals": self._rejection_signals,
                "continuation_signals": self._continuation_signals,
                "reversal_signals": self._reversal_signals
            },
            "market_structure": {
                "touches": self._channel_touches,
                "tests": self._channel_tests,
                "penetrations": self._channel_penetrations
            },
            "institutional_analysis": {
                "donchian": self._institutional_donchian,
                "smart_money_channels": self._smart_money_channels
            },
            "metadata": {
                "period": self.donchian_config.period,
                "breakout_threshold": self.donchian_config.breakout_threshold,
                "midline_threshold": self.donchian_config.midline_threshold,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._highs.clear()
        self._lows.clear()
        self._closes.clear()
        self._channel_high = None
        self._channel_low = None
        self._channel_midline = None
        self._channel_width = 0.0
        self._price_position = 0.0
        self._distance_from_midline = 0.0
        self._breakout_probability = 0.0
        self._breakout_direction = 0
        self._breakout_strength = 0.0
        self._channel_trend = "neutral"
        self._channel_volatility = 0.0
        self._channel_efficiency = 0.0
        self._breakout_signals = 0
        self._rejection_signals = 0
        self._continuation_signals = 0
        self._reversal_signals = 0
        self._channel_touches = 0
        self._channel_tests = 0
        self._channel_penetrations = 0
        self._institutional_donchian = 0.0
        self._smart_money_channels = 0.0