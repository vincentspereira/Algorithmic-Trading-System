"""
Institutional-Grade Augmented Ichimoku Cloud Indicator

This module implements an enhanced Ichimoku Cloud indicator with institutional-grade features:
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
class AugmentedIchimokuConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented Ichimoku Cloud"""
    tenkan_period: int = 9
    kijun_period: int = 26
    senkou_span_b_period: int = 52
    displacement: int = 26


class AugmentedIchimokuCloud(AugmentedIndicator):
    """
    Institutional-grade Augmented Ichimoku Cloud indicator implementing 5-pillar architecture.

    Features:
    - Comprehensive trend analysis with multiple timeframe components
    - Cloud-based support/resistance identification
    - Momentum and trend strength assessment
    - Market regime adaptation based on cloud positioning
    - Multi-timeframe convergence for institutional confirmation
    - Smart money trend analysis for institutional flow detection
    - Automated risk management for trend-following strategies
    """

    def __init__(self, config: AugmentedIchimokuConfig = None):
        if config is None:
            config = AugmentedIchimokuConfig()

        super().__init__(config)
        self.ichimoku_config = config

        # Ichimoku Cloud specific state
        self._highs = deque(maxlen=self.config.buffer_size)
        self._lows = deque(maxlen=self.config.buffer_size)
        self._closes = deque(maxlen=self.config.buffer_size)

        # Ichimoku lines
        self._tenkan_sen = deque(maxlen=self.config.buffer_size)  # Conversion Line
        self._kijun_sen = deque(maxlen=self.config.buffer_size)   # Base Line
        self._senkou_span_a = deque(maxlen=self.config.buffer_size)  # Leading Span A
        self._senkou_span_b = deque(maxlen=self.config.buffer_size)  # Leading Span B
        self._chikou_span = deque(maxlen=self.config.buffer_size)    # Lagging Span

        # Current values
        self._current_tenkan = None
        self._current_kijun = None
        self._current_senkou_a = None
        self._current_senkou_b = None
        self._current_chikou = None

        # Cloud analysis
        self._cloud_color = "neutral"  # "green", "red", "neutral"
        self._cloud_thickness = 0.0
        self._price_cloud_position = "neutral"  # "above", "below", "inside"

        # Trend analysis
        self._trend_direction = 0  # -1, 0, 1 for down, neutral, up
        self._trend_strength = 0.0
        self._momentum_alignment = 0.0

        # Signal analysis
        self._tk_cross_signals = 0  # Tenkan-Kijun cross signals
        self._cloud_breakout_signals = 0
        self._chikou_confirmation_signals = 0
        self._signal_strength = 0.0

        # Market structure
        self._support_levels = []
        self._resistance_levels = []
        self._cloud_touches = 0

        # Institutional analysis
        self._institutional_cloud = 0.0
        self._smart_money_trend = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if Ichimoku Cloud is ready to provide signals"""
        return (self._current_tenkan is not None and
                self._current_kijun is not None and
                self._current_senkou_a is not None and
                self._current_senkou_b is not None)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update Ichimoku Cloud analysis

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

        # Update Ichimoku Cloud calculation
        self._update_ichimoku_cloud(high, low, close)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_ichimoku_cloud(self, high: float, low: float, close: float):
        """Update the core Ichimoku Cloud calculation with institutional enhancements"""
        self._highs.append(high)
        self._lows.append(low)
        self._closes.append(close)

        # Calculate Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
        if len(self._highs) >= self.ichimoku_config.tenkan_period:
            tenkan_high = max(list(self._highs)[-self.ichimoku_config.tenkan_period:])
            tenkan_low = min(list(self._lows)[-self.ichimoku_config.tenkan_period:])
            self._current_tenkan = (tenkan_high + tenkan_low) / 2
            self._tenkan_sen.append(self._current_tenkan)

        # Calculate Kijun-sen (Base Line): (26-period high + 26-period low) / 2
        if len(self._highs) >= self.ichimoku_config.kijun_period:
            kijun_high = max(list(self._highs)[-self.ichimoku_config.kijun_period:])
            kijun_low = min(list(self._lows)[-self.ichimoku_config.kijun_period:])
            self._current_kijun = (kijun_high + kijun_low) / 2
            self._kijun_sen.append(self._current_kijun)

        # Calculate Senkou Span A (Leading Span A): (Tenkan-sen + Kijun-sen) / 2, plotted 26 periods ahead
        if self._current_tenkan is not None and self._current_kijun is not None:
            senkou_a = (self._current_tenkan + self._current_kijun) / 2
            self._senkou_span_a.append(senkou_a)
            # Current value is displaced back by displacement period
            if len(self._senkou_span_a) > self.ichimoku_config.displacement:
                self._current_senkou_a = self._senkou_span_a[-self.ichimoku_config.displacement - 1]

        # Calculate Senkou Span B (Leading Span B): (52-period high + 52-period low) / 2, plotted 26 periods ahead
        if len(self._highs) >= self.ichimoku_config.senkou_span_b_period:
            senkou_b_high = max(list(self._highs)[-self.ichimoku_config.senkou_span_b_period:])
            senkou_b_low = min(list(self._lows)[-self.ichimoku_config.senkou_span_b_period:])
            senkou_b = (senkou_b_high + senkou_b_low) / 2
            self._senkou_span_b.append(senkou_b)
            # Current value is displaced back by displacement period
            if len(self._senkou_span_b) > self.ichimoku_config.displacement:
                self._current_senkou_b = self._senkou_span_b[-self.ichimoku_config.displacement - 1]

        # Calculate Chikou Span (Lagging Span): Current close plotted 26 periods back
        self._chikou_span.append(close)
        if len(self._chikou_span) > self.ichimoku_config.displacement:
            self._current_chikou = self._chikou_span[-self.ichimoku_config.displacement - 1]

        # Analyze Ichimoku Cloud characteristics
        self._analyze_ichimoku_characteristics(close)

    def _analyze_ichimoku_characteristics(self, current_price: float):
        """Analyze Ichimoku Cloud characteristics for institutional insights"""
        if not self.is_ready:
            return

        # Analyze cloud color and thickness
        if self._current_senkou_a > self._current_senkou_b:
            self._cloud_color = "green"  # Bullish cloud
        elif self._current_senkou_a < self._current_senkou_b:
            self._cloud_color = "red"    # Bearish cloud
        else:
            self._cloud_color = "neutral"

        # Calculate cloud thickness
        cloud_thickness = abs(self._current_senkou_a - self._current_senkou_b)
        if self._current_senkou_a != 0 and self._current_senkou_b != 0:
            avg_price = (self._current_senkou_a + self._current_senkou_b) / 2
            self._cloud_thickness = cloud_thickness / avg_price  # Normalize by price
        else:
            self._cloud_thickness = 0.0

        # Determine price position relative to cloud
        if current_price > max(self._current_senkou_a, self._current_senkou_b):
            self._price_cloud_position = "above"
        elif current_price < min(self._current_senkou_a, self._current_senkou_b):
            self._price_cloud_position = "below"
        else:
            self._price_cloud_position = "inside"

        # Calculate trend direction and strength
        if self._current_tenkan is not None and self._current_kijun is not None:
            if self._current_tenkan > self._current_kijun:
                self._trend_direction = 1  # Uptrend
            elif self._current_tenkan < self._current_kijun:
                self._trend_direction = -1  # Downtrend
            else:
                self._trend_direction = 0  # Neutral

            # Trend strength based on separation
            separation = abs(self._current_tenkan - self._current_kijun)
            if self._current_kijun != 0:
                self._trend_strength = min(1.0, separation / abs(self._current_kijun) * 10)

        # Calculate momentum alignment
        if (self._current_tenkan is not None and self._current_kijun is not None and
            self._current_chikou is not None):
            # Check if Chikou Span confirms the trend
            if self._trend_direction == 1 and self._current_chikou > self._current_kijun:
                self._momentum_alignment = 0.8
            elif self._trend_direction == -1 and self._current_chikou < self._current_kijun:
                self._momentum_alignment = 0.8
            elif self._trend_direction == 0:
                self._momentum_alignment = 0.5
            else:
                self._momentum_alignment = 0.3

        # Track signals
        self._track_ichimoku_signals()

        # Update market structure
        self._update_market_structure(current_price)

        # Calculate institutional cloud analysis
        self._calculate_institutional_cloud()

    def _track_ichimoku_signals(self):
        """Track Ichimoku Cloud signals"""
        if not self.is_ready or len(self._tenkan_sen) < 2 or len(self._kijun_sen) < 2:
            return

        # Track Tenkan-Kijun crosses
        prev_tenkan = self._tenkan_sen[-2]
        prev_kijun = self._kijun_sen[-2]
        current_tenkan = self._current_tenkan
        current_kijun = self._current_kijun

        if ((prev_tenkan <= prev_kijun and current_tenkan > current_kijun) or
            (prev_tenkan >= prev_kijun and current_tenkan < current_kijun)):
            self._tk_cross_signals += 1

        # Track cloud breakouts
        if self._price_cloud_position != "inside":
            self._cloud_breakout_signals += 1

        # Track Chikou confirmations
        if self._current_chikou is not None and self._current_kijun is not None:
            if ((self._trend_direction == 1 and self._current_chikou > self._current_kijun) or
                (self._trend_direction == -1 and self._current_chikou < self._current_kijun)):
                self._chikou_confirmation_signals += 1

        # Calculate overall signal strength
        signal_components = [
            self._tk_cross_signals > 0,
            self._cloud_breakout_signals > 0,
            self._chikou_confirmation_signals > 0,
            self._trend_strength > 0.5,
            self._momentum_alignment > 0.6
        ]
        self._signal_strength = sum(signal_components) / len(signal_components)

    def _update_market_structure(self, current_price: float):
        """Update market structure analysis"""
        if not self.is_ready:
            return

        # Track cloud touches for support/resistance
        if (self._price_cloud_position == "inside" or
            abs(current_price - self._current_senkou_a) / current_price < 0.001 or
            abs(current_price - self._current_senkou_b) / current_price < 0.001):
            self._cloud_touches += 1

        # Update support/resistance levels
        if self._cloud_color == "green":
            self._support_levels.append(min(self._current_senkou_a, self._current_senkou_b))
            if len(self._support_levels) > 10:
                self._support_levels.pop(0)
        elif self._cloud_color == "red":
            self._resistance_levels.append(max(self._current_senkou_a, self._current_senkou_b))
            if len(self._resistance_levels) > 10:
                self._resistance_levels.pop(0)

    def _calculate_institutional_cloud(self):
        """Calculate institutional cloud analysis"""
        if not self.is_ready:
            return

        # Institutional traders use Ichimoku for comprehensive trend analysis
        base_cloud = 0.0

        if self._cloud_thickness > 0.02 and self._trend_strength > 0.6:
            base_cloud = 0.8  # Thick cloud with strong trend
        elif self._cloud_thickness > 0.01 and self._trend_strength > 0.4:
            base_cloud = 0.6  # Moderate cloud with trend
        elif self._cloud_thickness > 0.005:
            base_cloud = 0.4  # Thin cloud

        self._institutional_cloud = base_cloud

        # Smart money trend considers all Ichimoku components
        smart_money_score = (
            self._trend_strength * 0.25 +
            self._momentum_alignment * 0.25 +
            self._signal_strength * 0.25 +
            self._institutional_cloud * 0.25
        )
        self._smart_money_trend = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade Ichimoku Cloud analysis"""
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

        # Use Tenkan-sen as primary raw value
        raw_value = self._current_tenkan if self._current_tenkan is not None else 0.0

        # Determine signal type based on Ichimoku Cloud analysis
        signal_type = self._determine_ichimoku_signal()

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
            'cloud_thickness': self._cloud_thickness,
            'institutional_cloud': self._institutional_cloud,
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
                "indicator": "Ichimoku_Cloud",
                "tenkan_period": self.ichimoku_config.tenkan_period,
                "kijun_period": self.ichimoku_config.kijun_period,
                "senkou_span_b_period": self.ichimoku_config.senkou_span_b_period,
                "displacement": self.ichimoku_config.displacement,
                "tenkan_sen": self._current_tenkan,
                "kijun_sen": self._current_kijun,
                "senkou_span_a": self._current_senkou_a,
                "senkou_span_b": self._current_senkou_b,
                "chikou_span": self._current_chikou,
                "cloud_color": self._cloud_color,
                "cloud_thickness": self._cloud_thickness,
                "price_cloud_position": self._price_cloud_position,
                "trend_direction": self._trend_direction,
                "trend_strength": self._trend_strength,
                "momentum_alignment": self._momentum_alignment,
                "tk_cross_signals": self._tk_cross_signals,
                "cloud_breakout_signals": self._cloud_breakout_signals,
                "chikou_confirmation_signals": self._chikou_confirmation_signals,
                "signal_strength": self._signal_strength,
                "cloud_touches": self._cloud_touches,
                "support_levels_count": len(self._support_levels),
                "resistance_levels_count": len(self._resistance_levels),
                "institutional_cloud": self._institutional_cloud,
                "smart_money_trend": self._smart_money_trend,
                "is_ready": self.is_ready
            }
        )

    def _determine_ichimoku_signal(self) -> SignalType:
        """Determine signal type based on Ichimoku Cloud analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # Strong bullish signals
        if (self._trend_direction == 1 and
            self._cloud_color == "green" and
            self._price_cloud_position == "above" and
            self._momentum_alignment > 0.7 and
            self._signal_strength > 0.6):
            return SignalType.STRONG_BULLISH

        # Strong bearish signals
        elif (self._trend_direction == -1 and
              self._cloud_color == "red" and
              self._price_cloud_position == "below" and
              self._momentum_alignment > 0.7 and
              self._signal_strength > 0.6):
            return SignalType.STRONG_BEARISH

        # Moderate bullish signals
        elif (self._trend_direction == 1 and
              (self._cloud_color == "green" or self._price_cloud_position == "above")):
            return SignalType.BULLISH

        # Moderate bearish signals
        elif (self._trend_direction == -1 and
              (self._cloud_color == "red" or self._price_cloud_position == "below")):
            return SignalType.BEARISH

        # Cloud breakout signals
        elif self._price_cloud_position != "inside" and self._cloud_thickness > 0.01:
            if self._price_cloud_position == "above":
                return SignalType.BULLISH
            else:
                return SignalType.BEARISH

        return SignalType.NEUTRAL

    @property
    def tenkan_sen(self) -> float:
        """Get the current Tenkan-sen (Conversion Line) value"""
        return self._current_tenkan if self._current_tenkan is not None else 0.0

    @property
    def kijun_sen(self) -> float:
        """Get the current Kijun-sen (Base Line) value"""
        return self._current_kijun if self._current_kijun is not None else 0.0

    @property
    def senkou_span_a(self) -> float:
        """Get the current Senkou Span A value"""
        return self._current_senkou_a if self._current_senkou_a is not None else 0.0

    @property
    def senkou_span_b(self) -> float:
        """Get the current Senkou Span B value"""
        return self._current_senkou_b if self._current_senkou_b is not None else 0.0

    @property
    def chikou_span(self) -> float:
        """Get the current Chikou Span value"""
        return self._current_chikou if self._current_chikou is not None else 0.0

    @property
    def cloud_color(self) -> str:
        """Get the current cloud color"""
        return self._cloud_color

    @property
    def cloud_thickness(self) -> float:
        """Get the current cloud thickness"""
        return self._cloud_thickness

    @property
    def price_cloud_position(self) -> str:
        """Get the price position relative to cloud"""
        return self._price_cloud_position

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
    def tk_cross_signals(self) -> int:
        """Get the count of Tenkan-Kijun cross signals"""
        return self._tk_cross_signals

    @property
    def cloud_breakout_signals(self) -> int:
        """Get the count of cloud breakout signals"""
        return self._cloud_breakout_signals

    @property
    def chikou_confirmation_signals(self) -> int:
        """Get the count of Chikou confirmation signals"""
        return self._chikou_confirmation_signals

    @property
    def cloud_touches(self) -> int:
        """Get the count of cloud touches"""
        return self._cloud_touches

    @property
    def support_levels(self) -> list:
        """Get the list of support levels"""
        return self._support_levels.copy()

    @property
    def resistance_levels(self) -> list:
        """Get the list of resistance levels"""
        return self._resistance_levels.copy()

    @property
    def institutional_cloud(self) -> float:
        """Get the institutional cloud score (0-1)"""
        return self._institutional_cloud

    @property
    def smart_money_trend(self) -> float:
        """Get the smart money trend score (0-1)"""
        return self._smart_money_trend

    def is_bullish_cloud(self) -> bool:
        """Check if cloud is bullish"""
        return self._cloud_color == "green"

    def is_bearish_cloud(self) -> bool:
        """Check if cloud is bearish"""
        return self._cloud_color == "red"

    def is_price_above_cloud(self) -> bool:
        """Check if price is above cloud"""
        return self._price_cloud_position == "above"

    def is_price_below_cloud(self) -> bool:
        """Check if price is below cloud"""
        return self._price_cloud_position == "below"

    def is_price_in_cloud(self) -> bool:
        """Check if price is inside cloud"""
        return self._price_cloud_position == "inside"

    def is_strong_trend(self) -> bool:
        """Check if trend is strong"""
        return self._trend_strength > 0.6

    def is_momentum_aligned(self) -> bool:
        """Check if momentum is aligned"""
        return self._momentum_alignment > 0.7

    def is_cloud_thick(self) -> bool:
        """Check if cloud is thick"""
        return self._cloud_thickness > 0.02

    def is_institutional_setup(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_cloud > 0.7

    def get_ichimoku_cloud_info(self) -> Dict[str, Any]:
        """Get comprehensive Ichimoku Cloud information"""
        return {
            "lines": {
                "tenkan_sen": self.tenkan_sen,
                "kijun_sen": self.kijun_sen,
                "senkou_span_a": self.senkou_span_a,
                "senkou_span_b": self.senkou_span_b,
                "chikou_span": self.chikou_span
            },
            "cloud_analysis": {
                "color": self._cloud_color,
                "thickness": self._cloud_thickness,
                "price_position": self._price_cloud_position,
                "touches": self._cloud_touches
            },
            "trend_analysis": {
                "direction": self._trend_direction,
                "strength": self._trend_strength,
                "momentum_alignment": self._momentum_alignment
            },
            "signal_analysis": {
                "strength": self._signal_strength,
                "tk_cross_signals": self._tk_cross_signals,
                "cloud_breakout_signals": self._cloud_breakout_signals,
                "chikou_confirmation_signals": self._chikou_confirmation_signals
            },
            "market_structure": {
                "support_levels": len(self._support_levels),
                "resistance_levels": len(self._resistance_levels)
            },
            "institutional_analysis": {
                "cloud": self._institutional_cloud,
                "smart_money_trend": self._smart_money_trend
            },
            "metadata": {
                "tenkan_period": self.ichimoku_config.tenkan_period,
                "kijun_period": self.ichimoku_config.kijun_period,
                "senkou_span_b_period": self.ichimoku_config.senkou_span_b_period,
                "displacement": self.ichimoku_config.displacement,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._highs.clear()
        self._lows.clear()
        self._closes.clear()
        self._tenkan_sen.clear()
        self._kijun_sen.clear()
        self._senkou_span_a.clear()
        self._senkou_span_b.clear()
        self._chikou_span.clear()
        self._current_tenkan = None
        self._current_kijun = None
        self._current_senkou_a = None
        self._current_senkou_b = None
        self._current_chikou = None
        self._cloud_color = "neutral"
        self._cloud_thickness = 0.0
        self._price_cloud_position = "neutral"
        self._trend_direction = 0
        self._trend_strength = 0.0
        self._momentum_alignment = 0.0
        self._tk_cross_signals = 0
        self._cloud_breakout_signals = 0
        self._chikou_confirmation_signals = 0
        self._signal_strength = 0.0
        self._support_levels.clear()
        self._resistance_levels.clear()
        self._cloud_touches = 0
        self._institutional_cloud = 0.0
        self._smart_money_trend = 0.0