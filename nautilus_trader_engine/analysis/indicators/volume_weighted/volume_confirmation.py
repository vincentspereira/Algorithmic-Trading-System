"""Volume Confirmation and Analysis Module

This module provides comprehensive volume confirmation scoring and analysis
for all technical indicators in the trading system. It implements institutional-grade
volume analysis techniques including:

- Multi-timeframe volume confirmation scoring
- Institutional volume pattern detection
- Volume-price relationship analysis
- Smart money flow detection
- Volume quality assessment
- Volume trend analysis
- Order flow imbalance detection

Author: Vincent S. Pereira
Version: 1.0.0
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List

import numpy as np
from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import (
    MultiTimeframeIndicator,
    MultiTimeframeIndicatorConfig,
)


class VolumeRegime(Enum):
    """Volume regime classification"""

    VERY_LOW = "very_low"
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    VERY_HIGH = "very_high"
    INSTITUTIONAL = "institutional"


class VolumeQuality(Enum):
    """Volume quality assessment"""

    POOR = "poor"
    FAIR = "fair"
    GOOD = "good"
    EXCELLENT = "excellent"


class OrderFlowBias(Enum):
    """Order flow bias direction"""

    STRONG_BUYING = "strong_buying"
    MODERATE_BUYING = "moderate_buying"
    NEUTRAL = "neutral"
    MODERATE_SELLING = "moderate_selling"
    STRONG_SELLING = "strong_selling"


@dataclass
class VolumeConfirmationScore:
    """Comprehensive volume confirmation scoring"""

    overall_score: float  # 0-1 scale
    price_volume_sync: float
    volume_breakout: float
    volume_persistence: float
    institutional_presence: float
    volume_trend_alignment: float
    volume_quality: float
    confidence: float
    timestamp: datetime


@dataclass
class VolumeAnalysis:
    """Detailed volume analysis results"""

    volume_regime: VolumeRegime
    volume_quality: VolumeQuality
    order_flow_bias: OrderFlowBias
    institutional_activity: float  # 0-1 scale
    volume_momentum: float
    volume_acceleration: float
    relative_volume: float
    volume_z_score: float
    volume_percentile: float
    smart_money_flow: float
    retail_flow: float
    timestamp: datetime


@dataclass
class VolumeProfile:
    """Volume profile analysis"""

    poc_price: float  # Point of Control
    value_area_high: float
    value_area_low: float
    volume_weighted_price: float
    high_volume_nodes: List[float]
    low_volume_nodes: List[float]
    total_volume: float
    buying_volume: float
    selling_volume: float
    neutral_volume: float


class VolumeConfirmationConfig(MultiTimeframeIndicatorConfig):
    """
    Configuration for the VolumeConfirmation indicator.
    """

    lookback_period: int = 50
    institutional_threshold: float = 2.0


class VolumeConfirmation(MultiTimeframeIndicator):
    """
    Advanced volume confirmation and analysis indicator.
    """

    def __init__(self, config: VolumeConfirmationConfig):
        super().__init__(config)
        self.lookback_period = config.lookback_period
        self.institutional_threshold = config.institutional_threshold

        self.prices = deque(maxlen=self.lookback_period * 2)
        self.volumes = deque(maxlen=self.lookback_period * 2)

        self.confirmation_history = deque(maxlen=1000)

    @property
    def is_ready(self) -> bool:
        return len(self.volumes) >= 10

    def on_aggregated_bar(self, bar: Bar):
        self.prices.append(bar.close)
        self.volumes.append(bar.volume)

        if self.is_ready:
            score = self._calculate_comprehensive_confirmation(bar.close, bar.volume, bar.timestamp)
            self.confirmation_history.append(score)
            self.values.append(score.overall_score)

    def reset(self):
        super().reset()
        self.prices.clear()
        self.volumes.clear()
        self.confirmation_history.clear()

    def _calculate_comprehensive_confirmation(
        self, price: float, volume: float, timestamp: datetime
    ) -> VolumeConfirmationScore:
        volume_stats = self._get_volume_statistics()

        price_volume_sync = self._calculate_price_volume_sync(price, volume, volume_stats)
        volume_breakout = self._calculate_volume_breakout(volume, volume_stats)
        volume_persistence = self._calculate_volume_persistence(volume_stats)
        institutional_presence = self._detect_institutional_presence(volume, volume_stats)
        volume_trend_alignment = self._calculate_volume_trend_alignment(volume_stats)
        volume_quality = self._assess_volume_quality(volume, volume_stats)

        weights = {
            "price_volume_sync": 0.25,
            "volume_breakout": 0.20,
            "volume_persistence": 0.15,
            "institutional_presence": 0.20,
            "volume_trend_alignment": 0.10,
            "volume_quality": 0.10,
        }

        overall_score = (
            price_volume_sync * weights["price_volume_sync"]
            + volume_breakout * weights["volume_breakout"]
            + volume_persistence * weights["volume_persistence"]
            + institutional_presence * weights["institutional_presence"]
            + volume_trend_alignment * weights["volume_trend_alignment"]
            + volume_quality * weights["volume_quality"]
        )

        confidence = self._calculate_confidence(volume_stats)

        return VolumeConfirmationScore(
            overall_score=overall_score,
            price_volume_sync=price_volume_sync,
            volume_breakout=volume_breakout,
            volume_persistence=volume_persistence,
            institutional_presence=institutional_presence,
            volume_trend_alignment=volume_trend_alignment,
            volume_quality=volume_quality,
            confidence=confidence,
            timestamp=timestamp,
        )

    def _get_volume_statistics(self) -> dict:
        volumes = np.array(self.volumes)
        return {
            "mean": np.mean(volumes),
            "std": np.std(volumes),
            "median": np.median(volumes),
            "max": np.max(volumes),
            "min": np.min(volumes),
            "lookback": len(volumes),
        }

    def _calculate_price_volume_sync(self, price: float, volume: float, stats: dict) -> float:
        if len(self.prices) < 2:
            return 0.5
        price_change = price - self.prices[-2]
        volume_change = volume - self.volumes[-2]

        if price_change > 0 and volume_change > 0:
            return 0.8  # Convergent
        if price_change < 0 and volume_change > 0:
            return 0.2  # Divergent
        return 0.5

    def _calculate_volume_breakout(self, volume: float, stats: dict) -> float:
        if stats["std"] == 0:
            return 0.5
        z_score = (volume - stats["mean"]) / stats["std"]
        return min(1.0, max(0.0, (z_score / 3.0) + 0.5))

    def _calculate_volume_persistence(self, stats: dict) -> float:
        if len(self.volumes) < 5:
            return 0.5
        recent_volumes = list(self.volumes)[-5:]
        if all(v > stats["mean"] for v in recent_volumes):
            return 0.8
        if all(v < stats["mean"] for v in recent_volumes):
            return 0.2
        return 0.5

    def _detect_institutional_presence(self, volume: float, stats: dict) -> float:
        if stats["std"] == 0:
            return 0.0
        z_score = (volume - stats["mean"]) / stats["std"]
        if z_score > self.institutional_threshold:
            return min(1.0, (z_score - self.institutional_threshold) / 2.0)
        return 0.0

    def _calculate_volume_trend_alignment(self, stats: dict) -> float:
        if len(self.volumes) < 10:
            return 0.5
        volume_trend = np.polyfit(range(10), list(self.volumes)[-10:], 1)[0]
        price_trend = np.polyfit(range(10), list(self.prices)[-10:], 1)[0]

        if np.sign(volume_trend) == np.sign(price_trend):
            return 0.8
        return 0.2

    def _assess_volume_quality(self, volume: float, stats: dict) -> float:
        if volume < stats["mean"] - 2 * stats["std"]:
            return 0.1  # Very low volume
        if volume > stats["mean"] + 2 * stats["std"]:
            return 0.9  # Very high volume
        return 0.6

    def _calculate_confidence(self, stats: dict) -> float:
        return min(1.0, stats["lookback"] / self.lookback_period)