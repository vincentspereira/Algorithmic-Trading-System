"""
Institutional-Grade Augmented Average True Range (ATR) Indicator

This module implements an enhanced ATR indicator with institutional-grade features:
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
class AugmentedATRConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented ATR"""
    period: int = 14
    volatility_threshold_high: float = 0.02  # 2% for high volatility
    volatility_threshold_low: float = 0.005  # 0.5% for low volatility


class AugmentedATR(AugmentedIndicator):
    """
    Institutional-grade Augmented ATR indicator implementing 5-pillar architecture.

    Features:
    - True range analysis for volatility measurement
    - Risk management and position sizing calculations
    - Market regime classification based on volatility levels
    - Multi-timeframe convergence for institutional confirmation
    - Smart money volatility analysis for trend strength validation
    - Automated risk management for volatility-adjusted strategies
    """

    def __init__(self, config: AugmentedATRConfig = None):
        if config is None:
            config = AugmentedATRConfig()

        super().__init__(config)
        self.atr_config = config

        # ATR specific state
        self._highs = deque(maxlen=self.config.buffer_size)
        self._lows = deque(maxlen=self.config.buffer_size)
        self._closes = deque(maxlen=self.config.buffer_size)
        self._true_ranges = deque(maxlen=self.config.buffer_size)
        self._atr_values = deque(maxlen=self.config.buffer_size)

        self._current_atr = None
        self._previous_close = None

        # Volatility analysis
        self._volatility_regime = "normal"  # "low", "normal", "high", "extreme"
        self._volatility_trend = "stable"  # "increasing", "decreasing", "stable"
        self._volatility_momentum = 0.0

        # Risk management
        self._position_size_multiplier = 1.0
        self._stop_loss_distance = 0.0
        self._take_profit_distance = 0.0
        self._risk_adjusted_position = 0.0

        # Market structure
        self._volatility_breakouts = 0
        self._volatility_contractions = 0
        self._range_expansions = 0
        self._range_contractions = 0

        # Institutional analysis
        self._institutional_atr = 0.0
        self._smart_money_volatility = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if ATR is ready to provide signals"""
        return len(self._atr_values) > 0 and self._current_atr is not None

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update ATR analysis

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

        # Update ATR calculation
        self._update_atr(high, low, close)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_atr(self, high: float, low: float, close: float):
        """Update the core ATR calculation with institutional enhancements"""
        self._highs.append(high)
        self._lows.append(low)
        self._closes.append(close)

        if self._previous_close is not None:
            # Calculate True Range
            tr1 = high - low
            tr2 = abs(high - self._previous_close)
            tr3 = abs(low - self._previous_close)
            true_range = max(tr1, tr2, tr3)

            self._true_ranges.append(true_range)

            # Calculate ATR using Wilder's smoothing
            if len(self._true_ranges) >= self.atr_config.period:
                if len(self._atr_values) == 0:
                    # First ATR value is simple average
                    tr_sum = sum(list(self._true_ranges)[-self.atr_config.period:])
                    self._current_atr = tr_sum / self.atr_config.period
                else:
                    # Subsequent values use Wilder's smoothing
                    self._current_atr = ((self._current_atr * (self.atr_config.period - 1)) + true_range) / self.atr_config.period

                self._atr_values.append(self._current_atr)

                # Analyze ATR characteristics
                self._analyze_atr_characteristics()

        self._previous_close = close

    def _analyze_atr_characteristics(self):
        """Analyze ATR characteristics for institutional insights"""
        if not self.is_ready or len(self._atr_values) < 3:
            return

        atr_value = self._current_atr
        current_price = self._closes[-1] if self._closes else 0.0

        # Calculate volatility regime
        if current_price > 0:
            volatility_ratio = atr_value / current_price

            if volatility_ratio > self.atr_config.volatility_threshold_high:
                self._volatility_regime = "high"
            elif volatility_ratio < self.atr_config.volatility_threshold_low:
                self._volatility_regime = "low"
            else:
                self._volatility_regime = "normal"

            # Extreme volatility detection
            if volatility_ratio > self.atr_config.volatility_threshold_high * 1.5:
                self._volatility_regime = "extreme"

        # Calculate volatility trend
        if len(self._atr_values) >= 5:
            recent_atr = list(self._atr_values)[-5:]
            atr_trend = (recent_atr[-1] - recent_atr[0]) / 5

            if atr_trend > 0.001:
                self._volatility_trend = "increasing"
                self._volatility_momentum = atr_trend
                self._volatility_breakouts += 1
            elif atr_trend < -0.001:
                self._volatility_trend = "decreasing"
                self._volatility_momentum = atr_trend
                self._volatility_contractions += 1
            else:
                self._volatility_trend = "stable"
                self._volatility_momentum = 0.0

        # Calculate range expansion/contraction
        if len(self._true_ranges) >= 5:
            recent_ranges = list(self._true_ranges)[-5:]
            range_trend = (recent_ranges[-1] - recent_ranges[0]) / 5

            if range_trend > 0.001:
                self._range_expansions += 1
            elif range_trend < -0.001:
                self._range_contractions += 1

        # Calculate risk management parameters
        if current_price > 0 and atr_value > 0:
            # Position size multiplier (inverse to volatility)
            volatility_ratio = atr_value / current_price
            self._position_size_multiplier = 1.0 / (1.0 + volatility_ratio * 10)  # Reduce position size in high volatility

            # Stop loss distance (2 * ATR for moderate risk)
            self._stop_loss_distance = atr_value * 2.0

            # Take profit distance (3 * ATR for 1.5:1 reward ratio)
            self._take_profit_distance = atr_value * 3.0

            # Risk-adjusted position size
            self._risk_adjusted_position = self._position_size_multiplier

        # Calculate institutional ATR analysis
        self._calculate_institutional_atr()

    def _calculate_institutional_atr(self):
        """Calculate institutional ATR analysis based on volatility characteristics"""
        if not self.is_ready:
            return

        # Institutional traders use ATR for risk management and volatility assessment
        base_atr = 0.0

        if self._volatility_regime == "high" and self._volatility_trend == "increasing":
            base_atr = 0.9  # High volatility trending higher - strong signal
        elif self._volatility_regime == "low" and self._volatility_trend == "stable":
            base_atr = 0.7  # Low stable volatility - good for precise entries
        elif self._volatility_regime == "extreme":
            base_atr = 0.8  # Extreme volatility - high risk/reward potential
        elif self._volatility_trend == "increasing":
            base_atr = 0.6  # Increasing volatility - potential breakout

        self._institutional_atr = base_atr

        # Smart money volatility considers trend and regime
        smart_money_score = (
            (1.0 if self._volatility_regime == "normal" else 0.5) * 0.3 +
            (1.0 if self._volatility_trend == "stable" else 0.7) * 0.3 +
            self._institutional_atr * 0.4
        )
        self._smart_money_volatility = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade ATR analysis"""
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

        atr_value = self._current_atr

        # Determine signal type based on ATR analysis
        signal_type = self._determine_atr_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'volatility_regime': self._volatility_regime,
            'volatility_trend': self._volatility_trend,
            'volatility_momentum': self._volatility_momentum,
            'position_size_multiplier': self._position_size_multiplier,
            'stop_loss_distance': self._stop_loss_distance,
            'take_profit_distance': self._take_profit_distance,
            'risk_adjusted_position': self._risk_adjusted_position,
            'volatility_breakouts': self._volatility_breakouts,
            'volatility_contractions': self._volatility_contractions,
            'range_expansions': self._range_expansions,
            'range_contractions': self._range_contractions,
            'institutional_atr': self._institutional_atr,
            'smart_money_volatility': self._smart_money_volatility
        }

        # Use ATR value as primary raw value
        raw_value = atr_value

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._suggested_sl,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "ATR",
                "period": self.atr_config.period,
                "volatility_threshold_high": self.atr_config.volatility_threshold_high,
                "volatility_threshold_low": self.atr_config.volatility_threshold_low,
                "volatility_regime": self._volatility_regime,
                "volatility_trend": self._volatility_trend,
                "volatility_momentum": self._volatility_momentum,
                "position_size_multiplier": self._position_size_multiplier,
                "stop_loss_distance": self._stop_loss_distance,
                "take_profit_distance": self._take_profit_distance,
                "risk_adjusted_position": self._risk_adjusted_position,
                "volatility_breakouts": self._volatility_breakouts,
                "volatility_contractions": self._volatility_contractions,
                "range_expansions": self._range_expansions,
                "range_contractions": self._range_contractions,
                "institutional_atr": self._institutional_atr,
                "smart_money_volatility": self._smart_money_volatility,
                "is_ready": self.is_ready
            }
        )

    def _determine_atr_signal(self) -> SignalType:
        """Determine signal type based on ATR analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        # High volatility signals
        if (self._volatility_regime == "high" and
            self._volatility_trend == "increasing" and
            self._volatility_breakouts > 0):
            return SignalType.STRONG_BULLISH  # High volatility often precedes breakouts

        # Low volatility signals
        elif (self._volatility_regime == "low" and
              self._volatility_trend == "stable" and
              self._volatility_contractions > 0):
            return SignalType.BULLISH  # Low volatility often precedes precise moves

        # Extreme volatility signals
        elif self._volatility_regime == "extreme":
            return SignalType.STRONG_BULLISH  # Extreme volatility indicates major moves

        # Volatility expansion signals
        elif (self._range_expansions > 0 and
              self._volatility_trend == "increasing"):
            return SignalType.BULLISH

        # Volatility contraction signals
        elif (self._range_contractions > 0 and
              self._volatility_trend == "decreasing"):
            return SignalType.BEARISH  # Contracting volatility may signal pause

        return SignalType.NEUTRAL

    @property
    def atr(self) -> float:
        """Get the current ATR value"""
        return self._current_atr if self.is_ready else 0.0

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
    def position_size_multiplier(self) -> float:
        """Get the position size multiplier"""
        return self._position_size_multiplier

    @property
    def stop_loss_distance(self) -> float:
        """Get the stop loss distance"""
        return self._stop_loss_distance

    @property
    def take_profit_distance(self) -> float:
        """Get the take profit distance"""
        return self._take_profit_distance

    @property
    def risk_adjusted_position(self) -> float:
        """Get the risk-adjusted position size"""
        return self._risk_adjusted_position

    @property
    def volatility_breakouts(self) -> int:
        """Get the count of volatility breakouts"""
        return self._volatility_breakouts

    @property
    def volatility_contractions(self) -> int:
        """Get the count of volatility contractions"""
        return self._volatility_contractions

    @property
    def range_expansions(self) -> int:
        """Get the count of range expansions"""
        return self._range_expansions

    @property
    def range_contractions(self) -> int:
        """Get the count of range contractions"""
        return self._range_contractions

    @property
    def institutional_atr(self) -> float:
        """Get the institutional ATR score (0-1)"""
        return self._institutional_atr

    @property
    def smart_money_volatility(self) -> float:
        """Get the smart money volatility score (0-1)"""
        return self._smart_money_volatility

    def is_high_volatility(self) -> bool:
        """Check if volatility is high"""
        return self._volatility_regime == "high"

    def is_low_volatility(self) -> bool:
        """Check if volatility is low"""
        return self._volatility_regime == "low"

    def is_extreme_volatility(self) -> bool:
        """Check if volatility is extreme"""
        return self._volatility_regime == "extreme"

    def is_volatility_increasing(self) -> bool:
        """Check if volatility is increasing"""
        return self._volatility_trend == "increasing"

    def is_volatility_decreasing(self) -> bool:
        """Check if volatility is decreasing"""
        return self._volatility_trend == "decreasing"

    def is_volatility_stable(self) -> bool:
        """Check if volatility is stable"""
        return self._volatility_trend == "stable"

    def is_risk_adjusted_positioning(self) -> bool:
        """Check if position sizing is risk-adjusted"""
        return self._position_size_multiplier < 0.8

    def is_conservative_positioning(self) -> bool:
        """Check if position sizing is conservative"""
        return self._position_size_multiplier < 0.6

    def is_aggressive_positioning(self) -> bool:
        """Check if position sizing is aggressive"""
        return self._position_size_multiplier > 1.2

    def is_institutional_volatility(self) -> bool:
        """Check if volatility setup is institutional-grade"""
        return self._institutional_atr > 0.7

    def get_atr_info(self) -> Dict[str, Any]:
        """Get comprehensive ATR information"""
        return {
            "atr_value": self.atr,
            "volatility_analysis": {
                "regime": self._volatility_regime,
                "trend": self._volatility_trend,
                "momentum": self._volatility_momentum
            },
            "risk_management": {
                "position_size_multiplier": self._position_size_multiplier,
                "stop_loss_distance": self._stop_loss_distance,
                "take_profit_distance": self._take_profit_distance,
                "risk_adjusted_position": self._risk_adjusted_position
            },
            "market_structure": {
                "volatility_breakouts": self._volatility_breakouts,
                "volatility_contractions": self._volatility_contractions,
                "range_expansions": self._range_expansions,
                "range_contractions": self._range_contractions
            },
            "institutional_analysis": {
                "atr": self._institutional_atr,
                "smart_money_volatility": self._smart_money_volatility
            },
            "metadata": {
                "period": self.atr_config.period,
                "volatility_threshold_high": self.atr_config.volatility_threshold_high,
                "volatility_threshold_low": self.atr_config.volatility_threshold_low,
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
        self._previous_close = None
        self._volatility_regime = "normal"
        self._volatility_trend = "stable"
        self._volatility_momentum = 0.0
        self._position_size_multiplier = 1.0
        self._stop_loss_distance = 0.0
        self._take_profit_distance = 0.0
        self._risk_adjusted_position = 0.0
        self._volatility_breakouts = 0
        self._volatility_contractions = 0
        self._range_expansions = 0
        self._range_contractions = 0
        self._institutional_atr = 0.0
        self._smart_money_volatility = 0.0
