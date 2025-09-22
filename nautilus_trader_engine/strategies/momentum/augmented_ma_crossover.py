"""
Institutional-Grade Augmented Moving Average Crossover System

This module implements an enhanced moving average crossover system with institutional-grade features:
- Multiple timeframe moving average analysis
- Volume confirmation scoring
- Market regime adaptation
- Multi-timeframe convergence
- Smart money detection
- Automated risk management
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import (
    AugmentedIndicator,
    AugmentedIndicatorConfig,
    IndicatorSignal,
    SignalType,
)


class CrossoverType(Enum):
    """Types of moving average crossovers"""
    FAST_OVER_SLOW = "fast_over_slow"
    FAST_UNDER_SLOW = "fast_under_slow"
    PRICE_OVER_FAST = "price_over_fast"
    PRICE_UNDER_FAST = "price_under_fast"
    PRICE_OVER_SLOW = "price_over_slow"
    PRICE_UNDER_SLOW = "price_under_slow"


@dataclass
class AugmentedMACrossoverConfig(AugmentedIndicatorConfig):
    """Configuration for Augmented MA Crossover System"""
    fast_period: int = 20
    slow_period: int = 50
    trend_period: int = 200
    crossover_types: List[CrossoverType] = None

    def __post_init__(self):
        if self.crossover_types is None:
            self.crossover_types = [
                CrossoverType.FAST_OVER_SLOW,
                CrossoverType.PRICE_OVER_FAST,
                CrossoverType.PRICE_OVER_SLOW
            ]


class AugmentedMACrossover(AugmentedIndicator):
    """
    Institutional-grade Augmented Moving Average Crossover system implementing 5-pillar architecture.

    Features:
    - Multiple moving average combinations (SMA, EMA, WMA)
    - Volume-weighted crossover analysis
    - Market regime adaptation
    - Multi-timeframe convergence
    - Smart money flow analysis
    - Automated risk management
    """

    def __init__(self, config: AugmentedMACrossoverConfig = None):
        if config is None:
            config = AugmentedMACrossoverConfig()

        super().__init__(config)
        self.ma_config = config

        # Initialize moving averages
        from ..moving_averages.sma import SMA, SMAConfig
        from ..moving_averages.ema import EMA, EMAConfig

        self.fast_ma = SMA(SMAConfig(period=self.ma_config.fast_period))
        self.slow_ma = SMA(SMAConfig(period=self.ma_config.slow_period))
        self.trend_ma = EMA(EMAConfig(period=self.ma_config.trend_period))

        # Crossover tracking
        self._previous_fast_slow_relationship = 0  # -1: fast < slow, 0: equal, 1: fast > slow
        self._previous_price_fast_relationship = 0
        self._previous_price_slow_relationship = 0

        # Crossover signals
        self._crossover_signals = []

    @property
    def is_ready(self) -> bool:
        """Return True if all moving averages are ready"""
        return (self.fast_ma.is_ready and
                self.slow_ma.is_ready and
                self.trend_ma.is_ready)

    def handle_bar(self, bar: Bar):
        """
        Handle new bar data and update crossover analysis

        Args:
            bar (Bar): New bar data
        """
        # Update moving averages
        self.fast_ma.handle_bar(bar)
        self.slow_ma.handle_bar(bar)
        self.trend_ma.handle_bar(bar)

        if self.is_ready:
            self._update_pillars(bar)
            self._detect_crossovers(bar)

    def _detect_crossovers(self, bar: Bar):
        """Detect various types of moving average crossovers"""
        if not self.is_ready:
            return

        current_signals = []

        # Get current values
        fast_value = self.fast_ma.value
        slow_value = self.slow_ma.value
        trend_value = self.trend_ma.value
        price = bar.close

        # Fast MA vs Slow MA crossover
        current_fast_slow = 1 if fast_value > slow_value else (-1 if fast_value < slow_value else 0)

        if (self._previous_fast_slow_relationship != 0 and
            current_fast_slow != 0 and
            self._previous_fast_slow_relationship != current_fast_slow):

            if current_fast_slow == 1:
                current_signals.append(CrossoverType.FAST_OVER_SLOW)
            else:
                current_signals.append(CrossoverType.FAST_UNDER_SLOW)

        # Price vs Fast MA crossover
        current_price_fast = 1 if price > fast_value else (-1 if price < fast_value else 0)

        if (self._previous_price_fast_relationship != 0 and
            current_price_fast != 0 and
            self._previous_price_fast_relationship != current_price_fast):

            if current_price_fast == 1:
                current_signals.append(CrossoverType.PRICE_OVER_FAST)
            else:
                current_signals.append(CrossoverType.PRICE_UNDER_FAST)

        # Price vs Slow MA crossover
        current_price_slow = 1 if price > slow_value else (-1 if price < slow_value else 0)

        if (self._previous_price_slow_relationship != 0 and
            current_price_slow != 0 and
            self._previous_price_slow_relationship != current_price_slow):

            if current_price_slow == 1:
                current_signals.append(CrossoverType.PRICE_OVER_SLOW)
            else:
                current_signals.append(CrossoverType.PRICE_UNDER_SLOW)

        # Update previous relationships
        self._previous_fast_slow_relationship = current_fast_slow
        self._previous_price_fast_relationship = current_price_fast
        self._previous_price_slow_relationship = current_price_slow

        # Store signals
        if current_signals:
            self._crossover_signals.extend(current_signals)
            # Keep only recent signals
            if len(self._crossover_signals) > 10:
                self._crossover_signals = self._crossover_signals[-10:]

    @property
    def value_meta(self) -> IndicatorSignal:
        """Return rich signal object with institutional-grade MA crossover analysis"""
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

        # Determine primary signal based on recent crossovers
        signal_type = self._determine_primary_signal()

        # Get confidence components from pillars
        confidence_components = {
            'volume_score': self._volume_confirmation_score,
            'volatility_score': self._volatility_score,
            'trend_alignment_score': self._trend_alignment_score,
            'mtf_convergence_score': self._mtf_convergence_score,
            'smart_money_score': self._smart_money_score,
            'crossover_strength': self._calculate_crossover_strength()
        }

        # Use fast MA value as primary raw value
        raw_value = self.fast_ma.value

        return IndicatorSignal(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=self._composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=self._suggested_sl,
            suggested_tp=self._suggested_tp,
            timestamp=datetime.now(),
            metadata={
                "indicator": "MA_Crossover",
                "fast_period": self.ma_config.fast_period,
                "slow_period": self.ma_config.slow_period,
                "trend_period": self.ma_config.trend_period,
                "fast_ma_value": self.fast_ma.value,
                "slow_ma_value": self.slow_ma.value,
                "trend_ma_value": self.trend_ma.value,
                "recent_crossovers": [s.value for s in self._crossover_signals[-3:]],
                "is_ready": self.is_ready
            }
        )

    def _determine_primary_signal(self) -> SignalType:
        """Determine primary signal based on recent crossovers"""
        if not self._crossover_signals:
            return SignalType.NEUTRAL

        # Get most recent crossover
        recent_crossover = self._crossover_signals[-1]

        # Map crossover types to signals
        signal_mapping = {
            CrossoverType.FAST_OVER_SLOW: SignalType.BULLISH,
            CrossoverType.FAST_UNDER_SLOW: SignalType.BEARISH,
            CrossoverType.PRICE_OVER_FAST: SignalType.BULLISH,
            CrossoverType.PRICE_UNDER_FAST: SignalType.BEARISH,
            CrossoverType.PRICE_OVER_SLOW: SignalType.STRONG_BULLISH,
            CrossoverType.PRICE_UNDER_SLOW: SignalType.STRONG_BEARISH
        }

        return signal_mapping.get(recent_crossover, SignalType.NEUTRAL)

    def _calculate_crossover_strength(self) -> float:
        """Calculate crossover-specific strength score"""
        if not self.is_ready or not self._crossover_signals:
            return 0.5

        # Strength based on MA separation
        fast_value = self.fast_ma.value
        slow_value = self.slow_ma.value

        if slow_value > 0:
            separation_ratio = abs(fast_value - slow_value) / slow_value
            separation_strength = min(1.0, separation_ratio * 10)  # Max strength at 10% separation
        else:
            separation_strength = 0.5

        # Strength based on trend alignment
        trend_value = self.trend_ma.value
        price_alignment = 1.0 if (fast_value > trend_value and slow_value > trend_value) else 0.5

        # Strength based on recent crossover frequency
        recent_crossovers = len([s for s in self._crossover_signals[-5:] if s in [
            CrossoverType.FAST_OVER_SLOW, CrossoverType.FAST_UNDER_SLOW
        ]])
        frequency_strength = min(1.0, recent_crossovers / 3)  # Max strength with 3+ crossovers

        return (separation_strength * 0.4 + price_alignment * 0.3 + frequency_strength * 0.3)

    def reset(self):
        """Reset the indicator to initial state"""
        super().reset()
        self.fast_ma.reset()
        self.slow_ma.reset()
        self.trend_ma.reset()
        self._previous_fast_slow_relationship = 0
        self._previous_price_fast_relationship = 0
        self._previous_price_slow_relationship = 0
        self._crossover_signals.clear()