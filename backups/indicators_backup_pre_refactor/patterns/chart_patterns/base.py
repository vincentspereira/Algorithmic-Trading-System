"""
base.py
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from nautilus_trader.indicators.core.base import MarketRegime


class PatternType(Enum):
    """Pattern classification types"""
    REVERSAL = "reversal"
    CONTINUATION = "continuation"
    NEUTRAL = "neutral"
    INDECISION = "indecision"

class PatternStrength(Enum):
    """Pattern strength classification"""
    VERY_WEAK = "very_weak"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"

class VolumeProfile(Enum):
    """Volume profile classification"""
    LOW_VOLUME = "low_volume"
    NORMAL_VOLUME = "normal_volume"
    HIGH_VOLUME = "high_volume"
    INSTITUTIONAL_VOLUME = "institutional_volume"
    CLIMAX_VOLUME = "climax_volume"

@dataclass
class PatternAnalysis:
    """Comprehensive pattern analysis"""
    pattern_name: str
    pattern_type: PatternType
    detected: bool
    confidence: float
    strength: PatternStrength
    volume_profile: VolumeProfile
    volume_confirmation: float
    smart_money_involvement: float
    institutional_bias: str
    risk_reward_ratio: float
    target_price: Optional[float]
    stop_loss: Optional[float]
    pattern_reliability: float
    market_regime: MarketRegime
    timestamp: datetime

class CandleProperties:
    """Enhanced candle properties for pattern analysis"""
    def __init__(self, open_price: float, high: float, low: float, close: float, volume: float):
        self.open_price = open_price
        self.high = high
        self.low = low
        self.close_price = close
        self.volume = volume
        # Aliases for compatibility with detection logic
        self.open = open_price
        self.close = close
        
        # Calculate basic properties
        self.body_size = abs(close - open_price)
        self.upper_shadow = high - max(open_price, close)
        self.lower_shadow = min(open_price, close) - low
        self.total_range = high - low
        self.body_ratio = self.body_size / self.total_range if self.total_range > 0 else 0
        
        # Determine candle type
        self.is_bullish = close > open_price
        self.is_bearish = close < open_price
        self.is_doji = self.body_size <= (self.total_range * 0.1)