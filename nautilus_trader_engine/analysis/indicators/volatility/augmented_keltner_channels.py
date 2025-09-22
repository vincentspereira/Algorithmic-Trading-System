"""
Institutional-Grade Augmented Keltner Channels Indicator

This module implements an enhanced Keltner Channels indicator with institutional-grade features:
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
class AugmentedKeltnerConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Keltner Channels"""
    period: int = 20
    atr_period: int = 14
    multiplier: float = 2.0
    breakout_threshold: float = 0.8


class AugmentedKeltner(AugmentedIndicator):
    """
    Institutional-grade Augmented Keltner Channels indicator implementing 5-pillar architecture.

    Features:
    - ATR-based volatility channels for dynamic range analysis
    - Squeeze and expansion detection using ATR bands
    - Market regime adaptation based on volatility patterns
    - Multi-timeframe convergence for institutional confirmation
    - Smart money channel analysis for institutional flow detection
    - Automated risk management for volatility-adjusted strategies
    """

    def __init__(self, config: AugmentedKeltnerConfig = None):
        if config is None:
            config = AugmentedKeltnerConfig()

        super().__init__(config)
        self.keltner_config = config

        # Keltner Channels specific state
        self._highs = deque(maxlen=self.config.buffer_size)
        self._lows = deque(maxlen=self.config.buffer_size)
        self._closes = deque(maxlen=self.config.buffer_size)

        # ATR calculation for channels
        self._true_ranges = deque(maxlen=self.config.buffer_size)
        self._atr_values = deque(maxlen=self.config.buffer_size)
        self._current_atr = None

        # Channel values
        self._channel_middle = None
        self._channel_upper = None
        self._channel_lower = None
        self._channel_width = 0.0

        # Price position analysis
        self._price_position = 0.0  # Position within channel (-1 to 1)
        self._squeeze_ratio = 0.0

        # Volatility analysis
        self._volatility_regime = "normal"  # "low", "normal", "high", "extreme"
        self._volatility_trend = "stable"  # "increasing", "decreasing", "stable"
        self._volatility_momentum = 0.0

        # Signal analysis
        self._squeeze_signals = 0
        self._expansion_signals = 0
        self._breakout_signals = 0
        self._rejection_signals = 0

        # Market structure
        self._channel_touches = 0
        self._channel_penetrations = 0
        self._squeeze_duration = 0

        # Institutional analysis
        self._institutional_keltner = 0.0
        self._smart_money_keltner = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Keltner Channels is ready to provide signals"""
        return (self._channel_middle is not None and
                self._channel_upper is not None and
                self._channel_lower is not None and
                len(self._atr_values) > 0)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update Keltner Channels analysis

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

        # Update Keltner Channels calculation
        self._update_keltner_channels(high, low, close)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_keltner_channels(self, high: float, low: float, close: float):
        """Update the core Keltner Channels calculation with institutional enhancements"""
        self._highs.append(high)
        self._lows.append(low)
        self._closes.append(close)

        if len(self._highs) >= 2:
            # Calculate True Range
            prev_close = self._closes[-2]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            self._true_ranges.append(tr)

            # Calculate ATR
            if len(self._true_ranges) >= self.keltner_config.atr_period:
                if len(self._atr_values) == 0:
                    # First ATR value is simple average
                    tr_sum = sum(list(self._true_ranges)[-self.keltner_config.atr_period:])
                    self._current_atr = tr_sum / self.keltner_config.atr_period
                else:
                    # Subsequent values use Wilder's smoothing
                    self._current_atr = ((self._current_atr * (self.keltner_config.atr_period - 1)) + tr) / self.keltner_config.atr_period

                self._atr_values.append(self._current_atr)

                # Calculate Keltner Channels
                if len(self._closes) >= self.keltner_config.period:
                    # Middle line (EMA of close)
                    closes_list = list(self._closes)[-self.keltner_config.period:]
                    self._channel_middle = sum(closes_list) / len(closes_list)  # Simplified EMA

                    # Upper and lower channels
                    self._channel_upper = self._channel_middle + (self._current_atr * self.keltner_config.multiplier)
                    self._channel_lower = self._channel_middle - (self._current_atr * self.keltner_config.multiplier)

                    # Calculate channel width
                    if self._channel_middle > 0:
                        self._channel_width = (self._channel_upper - self._channel_lower) / self._channel_middle
                    else:
                        self._channel_width = 0.0

                    # Calculate price position within channel
                    if self._channel_upper != self._channel_lower:
                        self._price_position = (close - self._channel_lower) / (self._channel_upper - self._channel_lower) * 2 - 1
                        self._price_position = max(-1.0, min(1.0, self._price_position))
                    else:
                        self._price_position = 0.0

                    # Analyze channel characteristics
                    self._analyze_channel_characteristics(close)

    def _analyze_channel_characteristics(self, current_price: float):
        """Analyze Keltner Channels characteristics for institutional insights"""
        if not self.is_ready:
            return

        # Calculate squeeze ratio (channel width relative to ATR)
        if self._current_atr > 0:
            self._squeeze_ratio = self._channel_width / (self._current_atr * 4)  # ATR multiplier factor
            self._squeeze_ratio = min(2.0, self._squeeze_ratio)  # Cap at 2.0

        # Determine volatility regime
        if self._squeeze_ratio < 0.5:
            self._volatility_regime = "low"
        elif self._squeeze_ratio > 1.5:
            self._volatility_regime = "high"
        else:
            self._volatility_regime = "normal"

        # Calculate volatility trend
        if len(self._atr_values) >= 5:
            recent_atr = list(self._atr_values)[-5:]
            atr_trend = (recent_atr[-1] - recent_atr[0]) / 5

            if atr_trend > 0.001:
                self._volatility_trend = "increasing"
                self._volatility_momentum = atr_trend
            elif atr_trend < -0.001:
                self._volatility_trend = "decreasing"
                self._volatility_momentum = atr_trend
            else:
                self._volatility_trend = "stable"
                self._volatility_momentum = 0.0

        # Track channel interactions
        if abs(current_price - self._channel_upper) / current_price < 0.001:
            self._channel_touches += 1
        elif abs(current_price - self._channel_lower) / current_price < 0.001:
            self._channel_touches += 1

        # Track squeeze duration
        if self._volatility_regime == "low":
            self._squeeze_duration += 1
        else:
            self._squeeze_duration = 0

        # Generate signals
        self._generate_keltner_signals(current_price)

        # Calculate institutional Keltner analysis
        self._calculate_institutional_keltner()

    def _generate_keltner_signals(self, current_price: float):
        """Generate Keltner Channels-based signals"""
        if not self.is_ready:
            return

        # Squeeze signals (low volatility setup)
        if (self._volatility_regime == "low" and
            self._squeeze_ratio < 0.6 and
            self._squeeze_duration > 3):
            self._squeeze_signals += 1

        # Expansion signals (high volatility breakout)
        if (self._volatility_regime == "high" and
            self._squeeze_ratio > 1.2 and
            self._volatility_trend == "increasing"):
            self._expansion_signals += 1

        # Breakout signals
        if (abs(self._price_position) > self.keltner_config.breakout_threshold and
            self._volatility_regime == "high"):
            self._breakout_signals += 1

        # Rejection signals
        if (self._channel_touches > 0 and
            abs(self._price_position) < 0.8 and
            self._volatility_regime == "normal"):
            self._rejection_signals += 1

    def _calculate_institutional_keltner(self):
        """Calculate institutional Keltner analysis based on channel characteristics"""
        if not self.is_ready:
            return

        # Institutional traders use Keltner Channels for volatility-based trading
        base_keltner = 0.0

        if (self._squeeze_signals > 0 and
            self._squeeze_duration > 5 and
            self._volatility_regime == "low"):
            base_keltner = 0.9  # Strong squeeze setup for breakout
        elif (self._breakout_signals > 0 and
              self._volatility_trend == "increasing" and
              abs(self._price_position) > 0.9):
            base_keltner = 0.8  # Confirmed breakout with expanding volatility
        elif (self._rejection_signals > 0 and
              self._channel_touches > 2):
            base_keltner = 0.7  # Rejection at channel boundaries

        self._institutional_keltner = base_keltner

        # Smart money Keltner considers squeeze ratio and volatility momentum
        smart_money_score = (
            (1.0 - self._squeeze_ratio) * 0.3 +  # Lower squeeze ratio = higher potential
            abs(self._volatility_momentum) * 0.3 +
            self._institutional_keltner * 0.4
        )
        self._smart_money_keltner = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade Keltner Channels analysis"""
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

        # Determine signal type based on Keltner Channels analysis
        signal_type = self._determine_keltner_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'price_position': self._price_position,
            'squeeze_ratio': self._squeeze_ratio,
            'volatility_regime': self._volatility_regime,
            'volatility_trend': self._volatility_trend,
            'volatility_momentum': self._volatility_momentum,
            'squeeze_signals': self._squeeze_signals,
            'expansion_signals': self._expansion_signals,
            'breakout_signals': self._breakout_signals,
            'rejection_signals': self._rejection_signals,
            'channel_touches': self._channel_touches,
            'channel_penetrations': self._channel_penetrations,
            'squeeze_duration': self._squeeze_duration,
            'institutional_keltner': self._institutional_keltner,
            'smart_money_keltner': self._smart_money_keltner
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
                "indicator": "Keltner_Channels",
                "period": self.keltner_config.period,
                "atr_period": self.keltner_config.atr_period,
                "multiplier": self.keltner_config.multiplier,
                "breakout_threshold": self.keltner_config.breakout_threshold,
                "channel_middle": self._channel_middle,
                "channel_upper": self._channel_upper,
                "channel_lower": self._channel_lower,
                "channel_width": self._channel_width,
                "price_position": self._price_position,
                "squeeze_ratio": self._squeeze_ratio,
                "current_atr": self._current_atr,
                "volatility_regime": self._volatility_regime,
                "volatility_trend": self._volatility_trend,
                "volatility_momentum": self._volatility_momentum,
                "squeeze_signals": self._squeeze_signals,
                "expansion_signals": self._expansion_signals,
                "breakout_signals": self._breakout_signals,
                "rejection_signals": self._rejection_signals,
                "channel_touches": self._channel_touches,
                "channel_penetrations": self._channel_penetrations,
                "squeeze_duration": self._squeeze_duration,
                "institutional_keltner": self._institutional_keltner,
                "smart_money_keltner": self._smart_money_keltner,
                "is_ready": self.is_ready
            }
        )

    def _determine_keltner_signal(self) -> SignalType:
        """Determine signal type based on Keltner Channels analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong squeeze signals (breakout setup)
        if (self._squeeze_signals > 0 and
            self._squeeze_duration > 5 and
            self._volatility_regime == "low"):
            return SignalType.STRONG_BULLISH  # Squeeze often precedes breakouts

        # Strong breakout signals
        elif (self._breakout_signals > 0 and
              abs(self._price_position) > 0.9 and
              self._volatility_trend == "increasing"):
            if self._price_position > 0:
                return SignalType.STRONG_BULLISH
            else:
                return SignalType.STRONG_BEARISH

        # Moderate breakout signals
        elif (self._breakout_signals > 0 and
              abs(self._price_position) > self.keltner_config.breakout_threshold):
            if self._price_position > 0:
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

        # Expansion signals
        elif (self._expansion_signals > 0 and
              self._volatility_regime == "high"):
            return SignalType.BULLISH  # High volatility often precedes moves

        return SignalType.NEUTRAL

    @property
    def channel_middle(self) -> float:
        """Get the current channel middle"""
        return self._channel_middle if self.is_ready else 0.0

    @property
    def channel_upper(self) -> float:
        """Get the current channel upper"""
        return self._channel_upper if self.is_ready else 0.0

    @property
    def channel_lower(self) -> float:
        """Get the current channel lower"""
        return self._channel_lower if self.is_ready else 0.0

    @property
    def channel_width(self) -> float:
        """Get the current channel width"""
        return self._channel_width

    @property
    def price_position(self) -> float:
        """Get the current price position within channel (-1 to 1)"""
        return self._price_position

    @property
    def squeeze_ratio(self) -> float:
        """Get the current squeeze ratio"""
        return self._squeeze_ratio

    @property
    def current_atr(self) -> float:
        """Get the current ATR value"""
        return self._current_atr if self._current_atr is not None else 0.0

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
    def breakout_signals(self) -> int:
        """Get the count of breakout signals"""
        return self._breakout_signals

    @property
    def rejection_signals(self) -> int:
        """Get the count of rejection signals"""
        return self._rejection_signals

    @property
    def channel_touches(self) -> int:
        """Get the count of channel touches"""
        return self._channel_touches

    @property
    def channel_penetrations(self) -> int:
        """Get the count of channel penetrations"""
        return self._channel_penetrations

    @property
    def squeeze_duration(self) -> int:
        """Get the current squeeze duration"""
        return self._squeeze_duration

    @property
    def institutional_keltner(self) -> float:
        """Get the institutional Keltner score (0-1)"""
        return self._institutional_keltner

    @property
    def smart_money_keltner(self) -> float:
        """Get the smart money Keltner score (0-1)"""
        return self._smart_money_keltner

    def is_price_near_upper_channel(self) -> bool:
        """Check if price is near upper channel"""
        return self._price_position > 0.8

    def is_price_near_lower_channel(self) -> bool:
        """Check if price is near lower channel"""
        return self._price_position < -0.8

    def is_price_at_middle(self) -> bool:
        """Check if price is at channel middle"""
        return abs(self._price_position) < 0.2

    def is_squeeze_active(self) -> bool:
        """Check if squeeze is active"""
        return self._volatility_regime == "low" and self._squeeze_ratio < 0.6

    def is_expansion_active(self) -> bool:
        """Check if expansion is active"""
        return self._volatility_regime == "high" and self._squeeze_ratio > 1.2

    def is_high_volatility(self) -> bool:
        """Check if volatility is high"""
        return self._volatility_regime == "high"

    def is_low_volatility(self) -> bool:
        """Check if volatility is low"""
        return self._volatility_regime == "low"

    def is_volatility_increasing(self) -> bool:
        """Check if volatility is increasing"""
        return self._volatility_trend == "increasing"

    def is_volatility_decreasing(self) -> bool:
        """Check if volatility is decreasing"""
        return self._volatility_trend == "decreasing"

    def is_long_squeeze(self) -> bool:
        """Check if squeeze has been active for a long time"""
        return self._squeeze_duration > 10

    def is_breakout_confirmed(self) -> bool:
        """Check if breakout is confirmed"""
        return self._breakout_signals > 0 and abs(self._price_position) > self.keltner_config.breakout_threshold

    def is_rejection_present(self) -> bool:
        """Check if rejection is present"""
        return self._rejection_signals > 0

    def is_institutional_setup(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_keltner > 0.7

    def get_keltner_info(self) -> Dict[str, Any]:
        """Get comprehensive Keltner Channels information"""
        return {
            "channel_values": {
                "middle": self.channel_middle,
                "upper": self.channel_upper,
                "lower": self.channel_lower,
                "width": self.channel_width
            },
            "price_analysis": {
                "position": self._price_position,
                "squeeze_ratio": self._squeeze_ratio
            },
            "volatility_analysis": {
                "regime": self._volatility_regime,
                "trend": self._volatility_trend,
                "momentum": self._volatility_momentum,
                "atr": self._current_atr
            },
            "signal_analysis": {
                "squeeze_signals": self._squeeze_signals,
                "expansion_signals": self._expansion_signals,
                "breakout_signals": self._breakout_signals,
                "rejection_signals": self._rejection_signals
            },
            "market_structure": {
                "touches": self._channel_touches,
                "penetrations": self._channel_penetrations,
                "squeeze_duration": self._squeeze_duration
            },
            "institutional_analysis": {
                "keltner": self._institutional_keltner,
                "smart_money_keltner": self._smart_money_keltner
            },
            "metadata": {
                "period": self.keltner_config.period,
                "atr_period": self.keltner_config.atr_period,
                "multiplier": self.keltner_config.multiplier,
                "breakout_threshold": self.keltner_config.breakout_threshold,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._highs.clear()
        self._lows.clear()
        self._closes.clear()
        self._true_ranges.clear()
        self._atr_values.clear()
        self._current_atr = None
        self._channel_middle = None
        self._channel_upper = None
        self._channel_lower = None
        self._channel_width = 0.0
        self._price_position = 0.0
        self._squeeze_ratio = 0.0
        self._volatility_regime = "normal"
        self._volatility_trend = "stable"
        self._volatility_momentum = 0.0
        self._squeeze_signals = 0
        self._expansion_signals = 0
        self._breakout_signals = 0
        self._rejection_signals = 0
        self._channel_touches = 0
        self._channel_penetrations = 0
        self._squeeze_duration = 0
        self._institutional_keltner = 0.0
        self._smart_money_keltner = 0.0