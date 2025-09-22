"""
Pattern data structures for technical indicators
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
from nautilus_trader.indicators.enum.pattern import PatternType, PatternSignal, PatternReliability


@dataclass
class PatternResult:
    """Result of a pattern detection"""

    pattern_type: PatternType
    signal: PatternSignal
    confidence: float  # 0.0 to 1.0
    strength: float = 0.5  # 0.0 to 1.0
    reliability: PatternReliability = PatternReliability.MEDIUM
    trend_context: str = "unknown"
    candles_analyzed: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_bullish(self) -> bool:
        """True if pattern signal is bullish"""
        return self.signal == PatternSignal.BULLISH

    @property
    def is_bearish(self) -> bool:
        """True if pattern signal is bearish"""
        return self.signal == PatternSignal.BEARISH

    @property
    def is_neutral(self) -> bool:
        """True if pattern signal is neutral"""
        return self.signal == PatternSignal.NEUTRAL