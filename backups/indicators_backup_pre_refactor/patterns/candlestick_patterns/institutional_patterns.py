"""
institutional_patterns.py
"""

import numpy as np

from nautilus_trader.indicators.data.pattern import PatternResult
from nautilus_trader.indicators.enum.pattern import (
    PatternType,
    PatternSignal,
    PatternReliability,
)


def detect_institutional_patterns(self) -> list[PatternResult]:
    """Detect advanced institutional patterns"""
    patterns = []

    if len(self.candle_history) < 5:
        return patterns

    # Institutional Accumulation Pattern
    if _is_institutional_accumulation(self):
        patterns.append(
            PatternResult(
                pattern_type=PatternType.INSTITUTIONAL_ACCUMULATION,
                signal=PatternSignal.BULLISH,
                confidence=0.75,
                strength=0.8,
                reliability=PatternReliability.HIGH,
                trend_context=self.current_trend,
                candles_analyzed=5,
            )
        )

    # Institutional Distribution Pattern
    if _is_institutional_distribution(self):
        patterns.append(
            PatternResult(
                pattern_type=PatternType.INSTITUTIONAL_DISTRIBUTION,
                signal=PatternSignal.BEARISH,
                confidence=0.75,
                strength=0.8,
                reliability=PatternReliability.HIGH,
                trend_context=self.current_trend,
                candles_analyzed=5,
            )
        )

    # Volume Climax Pattern
    if _is_volume_climax(self):
        signal = (
            PatternSignal.BEARISH
            if self.current_trend == "bullish"
            else PatternSignal.BULLISH
        )
        patterns.append(
            PatternResult(
                pattern_type=PatternType.VOLUME_CLIMAX,
                signal=signal,
                confidence=0.70,
                strength=0.85,
                reliability=PatternReliability.HIGH,
                trend_context=self.current_trend,
                candles_analyzed=3,
            )
        )

    return patterns

def _is_institutional_accumulation(self) -> bool:
    """Detect institutional accumulation pattern"""
    if len(self.candle_history) < 5 or len(self.volume_history) < 5:
        return False

    recent_candles = list(self.candle_history)[-5:]
    recent_volumes = list(self.volume_history)[-5:]
    avg_volume = (
        np.mean(list(self.volume_history)[-20:])
        if len(self.volume_history) >= 20
        else np.mean(recent_volumes)
    )

    # Price consolidation with increasing volume
    price_range = max(c.high for c in recent_candles) - min(
        c.low for c in recent_candles
    )
    avg_price = np.mean([c.close for c in recent_candles])

    # Tight price range (< 3% of average price)
    if price_range > avg_price * 0.03:
        return False

    # Increasing volume trend
    volume_trend = np.polyfit(range(len(recent_volumes)), recent_volumes, 1)[0]
    if volume_trend <= 0:
        return False

    # Above average volume
    avg_recent_volume = np.mean(recent_volumes)
    return avg_recent_volume > avg_volume * 1.2

def _is_institutional_distribution(self) -> bool:
    """Detect institutional distribution pattern"""
    if len(self.candle_history) < 5 or len(self.volume_history) < 5:
        return False

    recent_candles = list(self.candle_history)[-5:]
    recent_volumes = list(self.volume_history)[-5:]
    avg_volume = (
        np.mean(list(self.volume_history)[-20:])
        if len(self.volume_history) >= 20
        else np.mean(recent_volumes)
    )

    # Price weakness with high volume
    bearish_candles = sum(1 for c in recent_candles if c.is_bearish)

    # Majority bearish candles
    if bearish_candles < 3:
        return False

    # High volume
    avg_recent_volume = np.mean(recent_volumes)
    if avg_recent_volume <= avg_volume * 1.5:
        return False

    # Declining closes
    closes = [c.close for c in recent_candles]
    return closes[-1] < closes[0]

def _is_volume_climax(self) -> bool:
    """Detect volume climax pattern"""
    if len(self.volume_history) < 10:
        return False

    current_volume = self.volume_history[-1]
    avg_volume = (
        np.mean(list(self.volume_history)[-20:])
        if len(self.volume_history) >= 20
        else np.mean(list(self.volume_history))
    )

    # Volume spike (> 3x average)
    return current_volume > avg_volume * 3.0