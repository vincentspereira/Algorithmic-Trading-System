"""
Institutional-Grade Heikin-Ashi Candlestick Indicator

This module implements an enhanced Heikin-Ashi candlestick indicator with institutional-grade features:
- Volume confirmation scoring
- Market regime adaptation
- Multi-timeframe convergence
- Smart money detection
- Automated risk management

Heikin-Ashi candles smooth price action to better identify trends and reduce noise.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime
from collections import deque

from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import (
    AugmentedIndicator,
    AugmentedIndicatorConfig,
    IndicatorSignal,
    SignalType,
)


@dataclass
class HeikinAshiConfig(AugmentedIndicatorConfig):
    """Configuration for Heikin-Ashi indicator"""
    smoothing_period: int = 1  # Usually 1 for traditional Heikin-Ashi


class HeikinAshiIndicator(AugmentedIndicator):
    """
    Institutional-grade Heikin-Ashi indicator implementing 5-pillar architecture.

    Heikin-Ashi candles are calculated as:
    - HA_Open = (Previous HA_Open + Previous HA_Close) / 2
    - HA_Close = (Open + High + Low + Close) / 4
    - HA_High = Max(High, HA_Open, HA_Close)
    - HA_Low = Min(Low, HA_Open, HA_Close)

    Features:
    - Trend identification with reduced noise
    - Support/resistance level identification
    - Momentum and trend strength assessment
    - Market regime adaptation based on candle color changes
    - Multi-timeframe convergence for institutional confirmation
    - Smart money trend analysis for institutional flow detection
    - Automated risk management for trend-following strategies
    """

    def __init__(self, config: HeikinAshiConfig = None):
        if config is None:
            config = HeikinAshiConfig()

        super().__init__(config)
        self.ha_config = config

        # Heikin-Ashi candle data storage
        self._ha_opens = deque(maxlen=self.config.buffer_size)
        self._ha_closes = deque(maxlen=self.config.buffer_size)
        self._ha_highs = deque(maxlen=self.config.buffer_size)
        self._ha_lows = deque(maxlen=self.config.buffer_size)

        # Current Heikin-Ashi values
        self._current_ha_open = None
        self._current_ha_close = None
        self._current_ha_high = None
        self._current_ha_low = None

        # Candle analysis
        self._candle_color = "neutral"  # "green", "red", "neutral"
        self._candle_size = 0.0
        self._candle_body_ratio = 0.0

        # Trend analysis
        self._trend_direction = 0  # -1, 0, 1 for down, neutral, up
        self._trend_strength = 0.0
        self._momentum_alignment = 0.0

        # Signal analysis
        self._color_change_signals = 0
        self._size_change_signals = 0
        self._doji_signals = 0
        self._signal_strength = 0.0

        # Market structure
        self._support_levels = []
        self._resistance_levels = []
        self._candle_touches = 0

        # Institutional analysis
        self._institutional_candle = 0.0
        self._smart_money_trend = 0.0

        # Previous candle data for calculations
        self._prev_ha_open = None
        self._prev_ha_close = None

    @property
    def is_ready(self) -> bool:
        """Return True if Heikin-Ashi indicator is ready to provide signals"""
        return (self._current_ha_open is not None and
                self._current_ha_close is not None and
                self._current_ha_high is not None and
                self._current_ha_low is not None)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update Heikin-Ashi analysis

        Args:
            bar (Bar): New bar data
        """
        # Extract OHLC data
        if hasattr(bar, 'high') and hasattr(bar, 'low') and hasattr(bar, 'close'):
            open_price = bar.open if hasattr(bar, 'open') else bar.close
            high = bar.high
            low = bar.low
            close = bar.close
        else:
            open_price = bar.get('open', bar.get('close', 0.0))
            high = bar.get('high', bar.get('close', 0.0))
            low = bar.get('low', bar.get('close', 0.0))
            close = bar.get('close', bar.get('price', 0.0))

        # Calculate Heikin-Ashi candle
        self._calculate_heikin_ashi_candle(open_price, high, low, close)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _calculate_heikin_ashi_candle(self, open_price: float, high: float, low: float, close: float):
        """Calculate Heikin-Ashi candle values"""
        # HA_Close = (Open + High + Low + Close) / 4
        ha_close = (open_price + high + low + close) / 4

        # HA_Open = (Previous HA_Open + Previous HA_Close) / 2
        if self._prev_ha_open is not None and self._prev_ha_close is not None:
            ha_open = (self._prev_ha_open + self._prev_ha_close) / 2
        else:
            # First candle, use regular open
            ha_open = open_price

        # HA_High = Max(High, HA_Open, HA_Close)
        ha_high = max(high, ha_open, ha_close)

        # HA_Low = Min(Low, HA_Open, HA_Close)
        ha_low = min(low, ha_open, ha_close)

        # Store current values
        self._current_ha_open = ha_open
        self._current_ha_close = ha_close
        self._current_ha_high = ha_high
        self._current_ha_low = ha_low

        # Store in deques
        self._ha_opens.append(ha_open)
        self._ha_closes.append(ha_close)
        self._ha_highs.append(ha_high)
        self._ha_lows.append(ha_low)

        # Update previous values for next calculation
        self._prev_ha_open = ha_open
        self._prev_ha_close = ha_close

        # Analyze candle characteristics
        self._analyze_candle_characteristics()

    def _analyze_candle_characteristics(self):
        """Analyze Heikin-Ashi candle characteristics"""
        if not self.is_ready:
            return

        # Determine candle color
        if self._current_ha_close > self._current_ha_open:
            self._candle_color = "green"  # Bullish
        elif self._current_ha_close < self._current_ha_open:
            self._candle_color = "red"    # Bearish
        else:
            self._candle_color = "neutral"

        # Calculate candle size (total range)
        candle_range = self._current_ha_high - self._current_ha_low
        if candle_range > 0:
            self._candle_size = candle_range
            # Calculate body ratio (body size / total range)
            body_size = abs(self._current_ha_close - self._current_ha_open)
            self._candle_body_ratio = body_size / candle_range
        else:
            self._candle_size = 0.0
            self._candle_body_ratio = 0.0

        # Calculate trend direction and strength
        if len(self._ha_closes) >= 2:
            prev_close = self._ha_closes[-2]
            current_close = self._current_ha_close

            if current_close > prev_close:
                self._trend_direction = 1  # Uptrend
            elif current_close < prev_close:
                self._trend_direction = -1  # Downtrend
            else:
                self._trend_direction = 0  # Neutral

            # Trend strength based on consecutive candles
            consecutive_count = self._calculate_consecutive_trend()
            self._trend_strength = min(1.0, consecutive_count / 5.0)  # Max at 5 consecutive

        # Calculate momentum alignment
        if len(self._ha_opens) >= 2 and len(self._ha_closes) >= 2:
            # Check if candle body direction aligns with trend
            body_direction = 1 if self._current_ha_close > self._current_ha_open else -1
            if self._trend_direction == body_direction:
                self._momentum_alignment = 0.8
            elif self._trend_direction == 0:
                self._momentum_alignment = 0.5
            else:
                self._momentum_alignment = 0.3

        # Track signals
        self._track_candle_signals()

        # Update market structure
        self._update_market_structure()

        # Calculate institutional candle analysis
        self._calculate_institutional_candle()

    def _calculate_consecutive_trend(self) -> int:
        """Calculate number of consecutive candles in same direction"""
        if len(self._ha_closes) < 2:
            return 0

        consecutive = 0
        current_direction = self._trend_direction

        # Check last 5 candles
        for i in range(min(5, len(self._ha_closes) - 1)):
            prev_idx = len(self._ha_closes) - 2 - i
            curr_idx = len(self._ha_closes) - 1 - i

            if prev_idx >= 0:
                prev_close = self._ha_closes[prev_idx]
                curr_close = self._ha_closes[curr_idx]

                candle_direction = 1 if curr_close > prev_close else -1

                if candle_direction == current_direction:
                    consecutive += 1
                else:
                    break

        return consecutive

    def _track_candle_signals(self):
        """Track Heikin-Ashi candle signals"""
        if not self.is_ready or len(self._ha_opens) < 2:
            return

        # Track color changes
        prev_color = self._get_candle_color(self._ha_opens[-2], self._ha_closes[-2])
        current_color = self._candle_color

        if prev_color != current_color and prev_color != "neutral" and current_color != "neutral":
            self._color_change_signals += 1

        # Track size changes (significant expansion/contraction)
        if len(self._ha_highs) >= 2 and len(self._ha_lows) >= 2:
            prev_range = self._ha_highs[-2] - self._ha_lows[-2]
            current_range = self._current_ha_high - self._current_ha_low

            if prev_range > 0:
                size_change_ratio = current_range / prev_range
                if size_change_ratio > 1.5 or size_change_ratio < 0.67:
                    self._size_change_signals += 1

        # Track doji patterns (very small body relative to range)
        if self._candle_body_ratio < 0.1:  # Body less than 10% of total range
            self._doji_signals += 1

        # Calculate overall signal strength
        signal_components = [
            self._color_change_signals > 0,
            self._size_change_signals > 0,
            self._doji_signals > 0,
            self._trend_strength > 0.6,
            self._momentum_alignment > 0.7
        ]
        self._signal_strength = sum(signal_components) / len(signal_components)

    def _get_candle_color(self, open_price: float, close_price: float) -> str:
        """Get candle color from open and close prices"""
        if close_price > open_price:
            return "green"
        elif close_price < open_price:
            return "red"
        else:
            return "neutral"

    def _update_market_structure(self):
        """Update market structure analysis"""
        if not self.is_ready:
            return

        # Track candle touches for support/resistance
        # Heikin-Ashi candles can show consolidation patterns
        if self._candle_body_ratio < 0.3:  # Small body indicates indecision
            self._candle_touches += 1

        # Update support/resistance levels based on candle extremes
        if self._candle_color == "green":
            self._support_levels.append(self._current_ha_low)
            if len(self._support_levels) > 10:
                self._support_levels.pop(0)
        elif self._candle_color == "red":
            self._resistance_levels.append(self._current_ha_high)
            if len(self._resistance_levels) > 10:
                self._resistance_levels.pop(0)

    def _calculate_institutional_candle(self):
        """Calculate institutional candle analysis"""
        if not self.is_ready:
            return

        # Institutional traders look for strong, consistent Heikin-Ashi signals
        base_candle = 0.0

        if self._trend_strength > 0.8 and self._momentum_alignment > 0.8:
            base_candle = 0.9  # Very strong trend with alignment
        elif self._trend_strength > 0.6 and self._momentum_alignment > 0.6:
            base_candle = 0.7  # Strong trend with good alignment
        elif self._trend_strength > 0.4:
            base_candle = 0.5  # Moderate trend
        elif self._candle_body_ratio < 0.2:
            base_candle = 0.3  # Consolidation/indecision

        self._institutional_candle = base_candle

        # Smart money trend considers all candle components
        smart_money_score = (
            self._trend_strength * 0.3 +
            self._momentum_alignment * 0.3 +
            self._signal_strength * 0.2 +
            self._institutional_candle * 0.2
        )
        self._smart_money_trend = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade Heikin-Ashi analysis"""
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

        # Use HA_Close as primary raw value
        raw_value = self._current_ha_close if self._current_ha_close is not None else 0.0

        # Determine signal type based on Heikin-Ashi analysis
        signal_type = self._determine_ha_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'trend_strength': self._trend_strength,
            'momentum_alignment': self._momentum_alignment,
            'signal_strength': self._signal_strength,
            'candle_size': self._candle_size,
            'candle_body_ratio': self._candle_body_ratio,
            'institutional_candle': self._institutional_candle,
            'smart_money_trend': self._smart_money_trend
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
                "indicator": "Heikin_Ashi",
                "ha_open": self._current_ha_open,
                "ha_close": self._current_ha_close,
                "ha_high": self._current_ha_high,
                "ha_low": self._current_ha_low,
                "candle_color": self._candle_color,
                "candle_size": self._candle_size,
                "candle_body_ratio": self._candle_body_ratio,
                "trend_direction": self._trend_direction,
                "trend_strength": self._trend_strength,
                "momentum_alignment": self._momentum_alignment,
                "color_change_signals": self._color_change_signals,
                "size_change_signals": self._size_change_signals,
                "doji_signals": self._doji_signals,
                "signal_strength": self._signal_strength,
                "candle_touches": self._candle_touches,
                "support_levels_count": len(self._support_levels),
                "resistance_levels_count": len(self._resistance_levels),
                "institutional_candle": self._institutional_candle,
                "smart_money_trend": self._smart_money_trend,
                "is_ready": self.is_ready
            }
        )

    def _determine_ha_signal(self) -> SignalType:
        """Determine signal type based on Heikin-Ashi analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong bullish signals
        if (self._trend_direction == 1 and
            self._candle_color == "green" and
            self._momentum_alignment > 0.8 and
            self._trend_strength > 0.7 and
            self._signal_strength > 0.6):
            return SignalType.STRONG_BULLISH

        # Strong bearish signals
        elif (self._trend_direction == -1 and
              self._candle_color == "red" and
              self._momentum_alignment > 0.8 and
              self._trend_strength > 0.7 and
              self._signal_strength > 0.6):
            return SignalType.STRONG_BEARISH

        # Moderate bullish signals
        elif (self._trend_direction == 1 and
              self._candle_color == "green"):
            return SignalType.BULLISH

        # Moderate bearish signals
        elif (self._trend_direction == -1 and
              self._candle_color == "red"):
            return SignalType.BEARISH

        # Doji signals (indecision)
        elif self._candle_body_ratio < 0.1:
            return SignalType.NEUTRAL  # Could be interpreted as reversal signal

        return SignalType.NEUTRAL

    @property
    def ha_open(self) -> float:
        """Get the current Heikin-Ashi open price"""
        return self._current_ha_open if self._current_ha_open is not None else 0.0

    @property
    def ha_close(self) -> float:
        """Get the current Heikin-Ashi close price"""
        return self._current_ha_close if self._current_ha_close is not None else 0.0

    @property
    def ha_high(self) -> float:
        """Get the current Heikin-Ashi high price"""
        return self._current_ha_high if self._current_ha_high is not None else 0.0

    @property
    def ha_low(self) -> float:
        """Get the current Heikin-Ashi low price"""
        return self._current_ha_low if self._current_ha_low is not None else 0.0

    @property
    def candle_color(self) -> str:
        """Get the current candle color"""
        return self._candle_color

    @property
    def candle_size(self) -> float:
        """Get the current candle size"""
        return self._candle_size

    @property
    def candle_body_ratio(self) -> float:
        """Get the current candle body ratio"""
        return self._candle_body_ratio

    @property
    def trend_direction(self) -> int:
        """Get the current trend direction (-1, 0, 1)"""
        return self._trend_direction

    @property
    def trend_strength(self) -> float:
        """Get the current trend strength (0-1)"""
        return self._trend_strength

    @property
    def momentum_alignment(self) -> float:
        """Get the momentum alignment score (0-1)"""
        return self._momentum_alignment

    @property
    def signal_strength(self) -> float:
        """Get the overall signal strength (0-1)"""
        return self._signal_strength

    @property
    def color_change_signals(self) -> int:
        """Get the count of color change signals"""
        return self._color_change_signals

    @property
    def size_change_signals(self) -> int:
        """Get the count of size change signals"""
        return self._size_change_signals

    @property
    def doji_signals(self) -> int:
        """Get the count of doji signals"""
        return self._doji_signals

    @property
    def candle_touches(self) -> int:
        """Get the count of candle touches"""
        return self._candle_touches

    @property
    def support_levels(self) -> list:
        """Get the list of support levels"""
        return self._support_levels.copy()

    @property
    def resistance_levels(self) -> list:
        """Get the list of resistance levels"""
        return self._resistance_levels.copy()

    @property
    def institutional_candle(self) -> float:
        """Get the institutional candle score (0-1)"""
        return self._institutional_candle

    @property
    def smart_money_trend(self) -> float:
        """Get the smart money trend score (0-1)"""
        return self._smart_money_trend

    def is_bullish_candle(self) -> bool:
        """Check if current candle is bullish"""
        return self._candle_color == "green"

    def is_bearish_candle(self) -> bool:
        """Check if current candle is bearish"""
        return self._candle_color == "red"

    def is_doji_candle(self) -> bool:
        """Check if current candle is a doji (indecision)"""
        return self._candle_body_ratio < 0.1

    def is_strong_trend(self) -> bool:
        """Check if trend is strong"""
        return self._trend_strength > 0.7

    def is_momentum_aligned(self) -> bool:
        """Check if momentum is aligned"""
        return self._momentum_alignment > 0.8

    def is_large_candle(self) -> bool:
        """Check if candle is large (high volatility)"""
        return self._candle_size > 0.02  # 2% threshold, adjustable

    def is_small_candle(self) -> bool:
        """Check if candle is small (low volatility)"""
        return self._candle_size < 0.005  # 0.5% threshold, adjustable

    def is_institutional_setup(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_candle > 0.8

    def get_heikin_ashi_info(self) -> Dict[str, Any]:
        """Get comprehensive Heikin-Ashi information"""
        return {
            "current_candle": {
                "ha_open": self.ha_open,
                "ha_close": self.ha_close,
                "ha_high": self.ha_high,
                "ha_low": self.ha_low,
                "color": self._candle_color,
                "size": self._candle_size,
                "body_ratio": self._candle_body_ratio
            },
            "trend_analysis": {
                "direction": self._trend_direction,
                "strength": self._trend_strength,
                "momentum_alignment": self._momentum_alignment
            },
            "signal_analysis": {
                "strength": self._signal_strength,
                "color_change_signals": self._color_change_signals,
                "size_change_signals": self._size_change_signals,
                "doji_signals": self._doji_signals
            },
            "market_structure": {
                "candle_touches": self._candle_touches,
                "support_levels": len(self._support_levels),
                "resistance_levels": len(self._resistance_levels)
            },
            "institutional_analysis": {
                "candle": self._institutional_candle,
                "smart_money_trend": self._smart_money_trend
            },
            "metadata": {
                "is_ready": self.is_ready,
                "smoothing_period": self.ha_config.smoothing_period
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._ha_opens.clear()
        self._ha_closes.clear()
        self._ha_highs.clear()
        self._ha_lows.clear()
        self._current_ha_open = None
        self._current_ha_close = None
        self._current_ha_high = None
        self._current_ha_low = None
        self._prev_ha_open = None
        self._prev_ha_close = None
        self._candle_color = "neutral"
        self._candle_size = 0.0
        self._candle_body_ratio = 0.0
        self._trend_direction = 0
        self._trend_strength = 0.0
        self._momentum_alignment = 0.0
        self._color_change_signals = 0
        self._size_change_signals = 0
        self._doji_signals = 0
        self._signal_strength = 0.0
        self._support_levels.clear()
        self._resistance_levels.clear()
        self._candle_touches = 0
        self._institutional_candle = 0.0
        self._smart_money_trend = 0.0