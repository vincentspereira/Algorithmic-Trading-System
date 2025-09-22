"""
Institutional-Grade Augmented ADX Indicator

This module implements an enhanced ADX indicator with institutional-grade features:
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
class AugmentedADXConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented ADX"""
    period: int = 14
    trend_threshold: float = 25.0  # ADX level for trend identification
    strong_trend_threshold: float = 40.0  # ADX level for strong trend


class AugmentedADX(AugmentedIndicator):
    """
    Institutional-grade Augmented ADX indicator implementing 5-pillar architecture.

    Features:
    - Trend strength measurement using directional movement
    - Market regime classification (trending vs ranging)
    - Directional bias analysis with +DI and -DI
    - Multi-timeframe convergence for institutional confirmation
    - Smart money trend analysis for institutional flow detection
    - Automated risk management for trend-following strategies
    """

    def __init__(self, config: AugmentedADXConfig = None):
        if config is None:
            config = AugmentedADXConfig()

        super().__init__(config)
        self.adx_config = config

        # ADX specific state
        self._highs = deque(maxlen=self.config.buffer_size)
        self._lows = deque(maxlen=self.config.buffer_size)
        self._closes = deque(maxlen=self.config.buffer_size)

        # Directional Movement components
        self._plus_dm_values = deque(maxlen=self.config.buffer_size)
        self._minus_dm_values = deque(maxlen=self.config.buffer_size)
        self._plus_di_values = deque(maxlen=self.config.buffer_size)
        self._minus_di_values = deque(maxlen=self.config.buffer_size)
        self._adx_values = deque(maxlen=self.config.buffer_size)

        self._current_plus_dm = None
        self._current_minus_dm = None
        self._current_plus_di = None
        self._current_minus_di = None
        self._current_adx = None

        # Trend analysis
        self._trend_direction = 0  # -1, 0, 1 for down, neutral, up
        self._trend_strength = 0.0
        self._trend_regime = "ranging"  # "ranging", "trending", "strong_trending"

        # Directional analysis
        self._directional_bias = 0.0
        self._directional_strength = 0.0
        self._directional_divergence = 0.0

        # Signal analysis
        self._trend_signals = 0
        self._reversal_signals = 0
        self._continuation_signals = 0
        self._ranging_signals = 0

        # Market structure
        self._regime_changes = 0
        self._trend_consistency = 0.0
        self._momentum_alignment = 0.0

        # Institutional analysis
        self._institutional_adx = 0.0
        self._smart_money_trend = 0.0

    @property
    def is_ready(self) -> bool:
        """Return True if ADX is ready to provide signals"""
        return (len(self._adx_values) > 0 and
                self._current_adx is not None and
                self._current_plus_di is not None and
                self._current_minus_di is not None)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update ADX analysis

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

        # Update ADX calculation
        self._update_adx(high, low, close)

        # Update all 5 pillars
        self._update_pillars(bar)

    def _update_adx(self, high: float, low: float, close: float):
        """Update the core ADX calculation with institutional enhancements"""
        self._highs.append(high)
        self._lows.append(low)
        self._closes.append(close)

        if len(self._highs) >= 2:
            # Calculate Directional Movement
            prev_high = self._highs[-2]
            prev_low = self._lows[-2]

            # Calculate +DM and -DM
            move_up = high - prev_high
            move_down = prev_low - low

            if move_up > move_down and move_up > 0:
                plus_dm = move_up
                minus_dm = 0.0
            elif move_down > move_up and move_down > 0:
                plus_dm = 0.0
                minus_dm = move_down
            else:
                plus_dm = 0.0
                minus_dm = 0.0

            self._plus_dm_values.append(plus_dm)
            self._minus_dm_values.append(minus_dm)

            # Calculate True Range (simplified)
            tr = max(high - low, abs(high - prev_high), abs(low - prev_low))

            # Calculate Directional Indicators
            if len(self._plus_dm_values) >= self.adx_config.period and tr > 0:
                # Smoothed +DM and -DM
                plus_dm_sum = sum(list(self._plus_dm_values)[-self.adx_config.period:])
                minus_dm_sum = sum(list(self._minus_dm_values)[-self.adx_config.period:])

                # Calculate +DI and -DI
                self._current_plus_di = (plus_dm_sum / tr) * 100
                self._current_minus_di = (minus_dm_sum / tr) * 100

                self._plus_di_values.append(self._current_plus_di)
                self._minus_di_values.append(self._current_minus_di)

                # Calculate DX (Directional Index)
                if self._current_plus_di + self._current_minus_di > 0:
                    dx = abs(self._current_plus_di - self._current_minus_di) / (self._current_plus_di + self._current_minus_di) * 100
                else:
                    dx = 0.0

                # Calculate ADX (smoothed DX)
                if len(self._adx_values) == 0:
                    self._current_adx = dx
                else:
                    self._current_adx = ((self._current_adx * (self.adx_config.period - 1)) + dx) / self.adx_config.period

                self._adx_values.append(self._current_adx)

                # Analyze ADX characteristics
                self._analyze_adx_characteristics()

    def _analyze_adx_characteristics(self):
        """Analyze ADX characteristics for institutional insights"""
        if not self.is_ready:
            return

        adx_value = self._current_adx
        plus_di = self._current_plus_di
        minus_di = self._current_minus_di

        # Determine trend regime
        if adx_value >= self.adx_config.strong_trend_threshold:
            self._trend_regime = "strong_trending"
            self._trend_strength = min(1.0, adx_value / 60.0)
        elif adx_value >= self.adx_config.trend_threshold:
            self._trend_regime = "trending"
            self._trend_strength = min(1.0, adx_value / 40.0)
        else:
            self._trend_regime = "ranging"
            self._trend_strength = max(0.0, (adx_value / self.adx_config.trend_threshold) - 0.5)

        # Determine trend direction
        if plus_di > minus_di:
            self._trend_direction = 1  # Uptrend
            self._directional_bias = (plus_di - minus_di) / (plus_di + minus_di)
        elif minus_di > plus_di:
            self._trend_direction = -1  # Downtrend
            self._directional_bias = (minus_di - plus_di) / (plus_di + minus_di)
        else:
            self._trend_direction = 0  # Neutral
            self._directional_bias = 0.0

        # Calculate directional strength
        self._directional_strength = abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0.0

        # Calculate directional divergence
        if len(self._plus_di_values) >= 3 and len(self._minus_di_values) >= 3:
            recent_plus_di = list(self._plus_di_values)[-3:]
            recent_minus_di = list(self._minus_di_values)[-3:]

            plus_di_trend = recent_plus_di[-1] - recent_plus_di[0]
            minus_di_trend = recent_minus_di[-1] - recent_minus_di[0]

            if plus_di_trend * minus_di_trend < 0:
                self._directional_divergence = min(1.0, abs(plus_di_trend - minus_di_trend) / max(abs(plus_di_trend), abs(minus_di_trend)))
            else:
                self._directional_divergence = 0.0

        # Calculate trend consistency
        if len(self._adx_values) >= 5:
            recent_adx = list(self._adx_values)[-5:]
            consistency_count = 0

            for i in range(1, len(recent_adx)):
                if ((recent_adx[i] >= self.adx_config.trend_threshold and recent_adx[i-1] >= self.adx_config.trend_threshold) or
                    (recent_adx[i] < self.adx_config.trend_threshold and recent_adx[i-1] < self.adx_config.trend_threshold)):
                    consistency_count += 1

            self._trend_consistency = consistency_count / (len(recent_adx) - 1)

        # Generate signals
        self._generate_adx_signals()

        # Calculate institutional ADX analysis
        self._calculate_institutional_adx()

    def _generate_adx_signals(self):
        """Generate ADX-based signals"""
        if not self.is_ready:
            return

        # Trend signals
        if (self._trend_regime in ["trending", "strong_trending"] and
            self._trend_strength > 0.6):
            self._trend_signals += 1

        # Reversal signals
        if (self._directional_divergence > 0.5 and
            self._trend_consistency < 0.4):
            self._reversal_signals += 1

        # Continuation signals
        if (self._trend_regime == "strong_trending" and
            self._directional_strength > 0.7 and
            self._trend_consistency > 0.8):
            self._continuation_signals += 1

        # Ranging signals
        if (self._trend_regime == "ranging" and
            self._trend_strength < 0.3):
            self._ranging_signals += 1

    def _calculate_institutional_adx(self):
        """Calculate institutional ADX analysis based on trend characteristics"""
        if not self.is_ready:
            return

        # Institutional traders use ADX for trend strength and market regime identification
        base_adx = 0.0

        if (self._trend_regime == "strong_trending" and
            self._trend_strength > 0.8 and
            self._trend_consistency > 0.8):
            base_adx = 0.9  # Strong, consistent trending market
        elif (self._trend_regime == "trending" and
              self._trend_strength > 0.6 and
              self._directional_strength > 0.6):
            base_adx = 0.8  # Moderate trending with directional strength
        elif (self._trend_regime == "ranging" and
              self._trend_strength < 0.3):
            base_adx = 0.6  # Clear ranging market for mean reversion strategies

        self._institutional_adx = base_adx

        # Smart money trend considers directional bias and strength
        smart_money_score = (
            self._trend_strength * 0.4 +
            self._directional_strength * 0.3 +
            self._trend_consistency * 0.2 +
            self._institutional_adx * 0.1
        )
        self._smart_money_trend = min(1.0, smart_money_score)

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade ADX analysis"""
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

        adx_value = self._current_adx

        # Determine signal type based on ADX analysis
        signal_type = self._determine_adx_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'trend_regime': self._trend_regime,
            'trend_direction': self._trend_direction,
            'trend_strength': self._trend_strength,
            'directional_bias': self._directional_bias,
            'directional_strength': self._directional_strength,
            'directional_divergence': self._directional_divergence,
            'trend_consistency': self._trend_consistency,
            'trend_signals': self._trend_signals,
            'reversal_signals': self._reversal_signals,
            'continuation_signals': self._continuation_signals,
            'ranging_signals': self._ranging_signals,
            'regime_changes': self._regime_changes,
            'institutional_adx': self._institutional_adx,
            'smart_money_trend': self._smart_money_trend
        }

        # Use ADX value as primary raw value
        raw_value = adx_value

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._suggested_sl,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "ADX",
                "period": self.adx_config.period,
                "trend_threshold": self.adx_config.trend_threshold,
                "strong_trend_threshold": self.adx_config.strong_trend_threshold,
                "adx_value": self._current_adx,
                "plus_di": self._current_plus_di,
                "minus_di": self._current_minus_di,
                "trend_regime": self._trend_regime,
                "trend_direction": self._trend_direction,
                "trend_strength": self._trend_strength,
                "directional_bias": self._directional_bias,
                "directional_strength": self._directional_strength,
                "directional_divergence": self._directional_divergence,
                "trend_consistency": self._trend_consistency,
                "trend_signals": self._trend_signals,
                "reversal_signals": self._reversal_signals,
                "continuation_signals": self._continuation_signals,
                "ranging_signals": self._ranging_signals,
                "regime_changes": self._regime_changes,
                "institutional_adx": self._institutional_adx,
                "smart_money_trend": self._smart_money_trend,
                "is_ready": self.is_ready
            }
        )

    def _determine_adx_signal(self) -> SignalType:
        """Determine signal type based on ADX analysis"""
        if not self.is_ready:
            return SignalType.NEUTRAL

        adx_value = self._current_adx
        plus_di = self._current_plus_di
        minus_di = self._current_minus_di

        # Strong trending signals
        if (self._trend_regime == "strong_trending" and
            self._trend_strength > 0.8 and
            self._directional_strength > 0.7):
            if plus_di > minus_di:
                return SignalType.STRONG_BULLISH
            else:
                return SignalType.STRONG_BEARISH

        # Moderate trending signals
        elif (self._trend_regime == "trending" and
              self._trend_strength > 0.6):
            if plus_di > minus_di:
                return SignalType.BULLISH
            else:
                return SignalType.BEARISH

        # Ranging market signals
        elif (self._trend_regime == "ranging" and
              self._ranging_signals > 0):
            return SignalType.NEUTRAL  # Good for mean reversion strategies

        # Reversal signals
        elif (self._reversal_signals > 0 and
              self._directional_divergence > 0.6):
            return SignalType.BEARISH  # Potential trend reversal

        # Continuation signals
        elif (self._continuation_signals > 0 and
              self._trend_consistency > 0.8):
            if plus_di > minus_di:
                return SignalType.BULLISH
            else:
                return SignalType.BEARISH

        return SignalType.NEUTRAL

    @property
    def adx(self) -> float:
        """Get the current ADX value"""
        return self._current_adx if self.is_ready else 0.0

    @property
    def plus_di(self) -> float:
        """Get the current +DI value"""
        return self._current_plus_di if self._current_plus_di is not None else 0.0

    @property
    def minus_di(self) -> float:
        """Get the current -DI value"""
        return self._current_minus_di if self._current_minus_di is not None else 0.0

    @property
    def trend_regime(self) -> str:
        """Get the current trend regime"""
        return self._trend_regime

    @property
    def trend_direction(self) -> int:
        """Get the current trend direction (-1, 0, 1)"""
        return self._trend_direction

    @property
    def trend_strength(self) -> float:
        """Get the current trend strength (0-1)"""
        return self._trend_strength

    @property
    def directional_bias(self) -> float:
        """Get the current directional bias (-1 to 1)"""
        return self._directional_bias

    @property
    def directional_strength(self) -> float:
        """Get the current directional strength (0-1)"""
        return self._directional_strength

    @property
    def directional_divergence(self) -> float:
        """Get the current directional divergence (0-1)"""
        return self._directional_divergence

    @property
    def trend_consistency(self) -> float:
        """Get the current trend consistency (0-1)"""
        return self._trend_consistency

    @property
    def trend_signals(self) -> int:
        """Get the count of trend signals"""
        return self._trend_signals

    @property
    def reversal_signals(self) -> int:
        """Get the count of reversal signals"""
        return self._reversal_signals

    @property
    def continuation_signals(self) -> int:
        """Get the count of continuation signals"""
        return self._continuation_signals

    @property
    def ranging_signals(self) -> int:
        """Get the count of ranging signals"""
        return self._ranging_signals

    @property
    def regime_changes(self) -> int:
        """Get the count of regime changes"""
        return self._regime_changes

    @property
    def institutional_adx(self) -> float:
        """Get the institutional ADX score (0-1)"""
        return self._institutional_adx

    @property
    def smart_money_trend(self) -> float:
        """Get the smart money trend score (0-1)"""
        return self._smart_money_trend

    def is_strong_trending_market(self) -> bool:
        """Check if market is in strong trending regime"""
        return self._trend_regime == "strong_trending"

    def is_trending_market(self) -> bool:
        """Check if market is in trending regime"""
        return self._trend_regime in ["trending", "strong_trending"]

    def is_ranging_market(self) -> bool:
        """Check if market is in ranging regime"""
        return self._trend_regime == "ranging"

    def is_uptrend(self) -> bool:
        """Check if trend is upward"""
        return self._trend_direction == 1

    def is_downtrend(self) -> bool:
        """Check if trend is downward"""
        return self._trend_direction == -1

    def is_trend_consistent(self) -> bool:
        """Check if trend is consistent"""
        return self._trend_consistency > 0.7

    def is_directionally_strong(self) -> bool:
        """Check if directional movement is strong"""
        return self._directional_strength > 0.7

    def is_divergence_present(self) -> bool:
        """Check if directional divergence is present"""
        return self._directional_divergence > 0.6

    def is_institutional_setup(self) -> bool:
        """Check if setup is institutional-grade"""
        return self._institutional_adx > 0.7

    def get_adx_info(self) -> Dict[str, Any]:
        """Get comprehensive ADX information"""
        return {
            "adx_values": {
                "adx": self.adx,
                "plus_di": self.plus_di,
                "minus_di": self.minus_di
            },
            "trend_analysis": {
                "regime": self._trend_regime,
                "direction": self._trend_direction,
                "strength": self._trend_strength,
                "consistency": self._trend_consistency
            },
            "directional_analysis": {
                "bias": self._directional_bias,
                "strength": self._directional_strength,
                "divergence": self._directional_divergence
            },
            "signal_analysis": {
                "trend_signals": self._trend_signals,
                "reversal_signals": self._reversal_signals,
                "continuation_signals": self._continuation_signals,
                "ranging_signals": self._ranging_signals,
                "regime_changes": self._regime_changes
            },
            "institutional_analysis": {
                "adx": self._institutional_adx,
                "smart_money_trend": self._smart_money_trend
            },
            "metadata": {
                "period": self.adx_config.period,
                "trend_threshold": self.adx_config.trend_threshold,
                "strong_trend_threshold": self.adx_config.strong_trend_threshold,
                "is_ready": self.is_ready
            }
        }

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self._highs.clear()
        self._lows.clear()
        self._closes.clear()
        self._plus_dm_values.clear()
        self._minus_dm_values.clear()
        self._plus_di_values.clear()
        self._minus_di_values.clear()
        self._adx_values.clear()
        self._current_plus_dm = None
        self._current_minus_dm = None
        self._current_plus_di = None
        self._current_minus_di = None
        self._current_adx = None
        self._trend_direction = 0
        self._trend_strength = 0.0
        self._trend_regime = "ranging"
        self._directional_bias = 0.0
        self._directional_strength = 0.0
        self._directional_divergence = 0.0
        self._trend_signals = 0
        self._reversal_signals = 0
        self._continuation_signals = 0
        self._ranging_signals = 0
        self._regime_changes = 0
        self._trend_consistency = 0.0
        self._momentum_alignment = 0.0
        self._institutional_adx = 0.0
        self._smart_money_trend = 0.0