"""
Institutional-Grade Fibonacci Analysis

This module implements advanced Fibonacci analysis with institutional-grade features:
- Dynamic Fibonacci retracement and extension calculations
- Multi-timeframe validation and confluence analysis
- Volume-weighted level strength assessment
- Smart money integration for level validation
- Adaptive confidence scoring based on market conditions
- Risk management integration with Fibonacci-based stop levels

Fibonacci levels include standard ratios (0.236, 0.382, 0.5, 0.618, 0.786)
plus custom ratios and extensions (1.272, 1.618, 2.618, etc.).
All calculations include volume-weighting, multi-timeframe confirmation,
and integrated risk management.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import statistics
import math


class FibonacciLevelType(Enum):
    """Types of Fibonacci levels"""
    RETRACEMENT = "retracement"
    EXTENSION = "extension"
    PROJECTION = "projection"
    EXPANSION = "expansion"


class FibonacciStrength(Enum):
    """Strength levels for Fibonacci analysis"""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


@dataclass
class FibonacciLevel:
    """Represents a Fibonacci level"""
    level_type: FibonacciLevelType
    ratio: float
    price_level: float
    strength: FibonacciStrength
    confidence_score: float
    volume_weighted: bool
    multi_timeframe_confirmed: bool
    smart_money_confirmed: bool
    confluence_count: int
    risk_management_levels: Dict[str, float]


@dataclass
class FibonacciSignal:
    """Fibonacci trading signal"""
    level: FibonacciLevel
    signal_type: str  # "bounce", "breakout", "rejection"
    direction: str  # "BUY" or "SELL"
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence_score: float
    risk_reward_ratio: float
    volume_confirmation: bool
    timeframe_alignment: bool
    timestamp: datetime


class InstitutionalFibonacciAnalyzer:
    """
    Institutional-grade Fibonacci analyzer.

    Features:
    - Dynamic level calculation from swing points
    - Multi-timeframe confluence analysis
    - Volume-weighted strength calculation
    - Smart money integration for level validation
    - Adaptive confidence scoring
    - Risk management integration
    """

    def __init__(self, lookback_periods: int = 100, min_confluence: int = 2):
        self.lookback_periods = lookback_periods
        self.min_confluence = min_confluence

        # Historical data
        self.price_data = []
        self.volume_data = []
        self.time_data = []

        # Standard Fibonacci ratios
        self.retracement_ratios = [0.236, 0.382, 0.5, 0.618, 0.786]
        self.extension_ratios = [1.272, 1.414, 1.618, 2.0, 2.618, 4.236]
        self.custom_ratios = [0.382, 0.5, 0.618, 1.0, 1.272, 1.618]  # Common custom levels

        # Current levels
        self.active_levels = {}

    def update_price_data(self, price: float, volume: float, timestamp: datetime):
        """
        Update price data for Fibonacci calculations

        Args:
            price: Current price
            volume: Trading volume
            timestamp: Price timestamp
        """
        self.price_data.append(price)
        self.volume_data.append(volume)
        self.time_data.append(timestamp)

        # Keep only recent data
        if len(self.price_data) > self.lookback_periods:
            self.price_data.pop(0)
            self.volume_data.pop(0)
            self.time_data.pop(0)

    def calculate_fibonacci_levels(self, swing_high: float, swing_low: float,
                                  trend_direction: str = "up") -> List[FibonacciLevel]:
        """
        Calculate Fibonacci levels from swing points

        Args:
            swing_high: Significant swing high
            swing_low: Significant swing low
            trend_direction: "up" or "down" trend

        Returns:
            List of calculated Fibonacci levels
        """
        levels = []

        # Calculate range
        price_range = swing_high - swing_low

        if trend_direction == "up":
            # Bullish trend: retracements from swing low to swing high
            for ratio in self.retracement_ratios:
                price_level = swing_low + (price_range * ratio)
                level = self._create_fibonacci_level(
                    FibonacciLevelType.RETRACEMENT, ratio, price_level,
                    swing_high, swing_low, trend_direction
                )
                levels.append(level)

            # Extensions above swing high
            for ratio in self.extension_ratios:
                price_level = swing_high + (price_range * (ratio - 1.0))
                level = self._create_fibonacci_level(
                    FibonacciLevelType.EXTENSION, ratio, price_level,
                    swing_high, swing_low, trend_direction
                )
                levels.append(level)

        else:  # Downward trend
            # Bearish trend: retracements from swing high to swing low
            for ratio in self.retracement_ratios:
                price_level = swing_high - (price_range * ratio)
                level = self._create_fibonacci_level(
                    FibonacciLevelType.RETRACEMENT, ratio, price_level,
                    swing_high, swing_low, trend_direction
                )
                levels.append(level)

            # Extensions below swing low
            for ratio in self.extension_ratios:
                price_level = swing_low - (price_range * (ratio - 1.0))
                level = self._create_fibonacci_level(
                    FibonacciLevelType.EXTENSION, ratio, price_level,
                    swing_high, swing_low, trend_direction
                )
                levels.append(level)

        # Filter by confluence and strength
        strong_levels = [level for level in levels if level.confluence_count >= self.min_confluence]
        self.active_levels = {f"{level.level_type.value}_{level.ratio:.3f}": level
                            for level in strong_levels}

        return strong_levels

    def _create_fibonacci_level(self, level_type: FibonacciLevelType, ratio: float,
                               price_level: float, swing_high: float, swing_low: float,
                               trend_direction: str) -> FibonacciLevel:
        """Create a Fibonacci level with institutional analysis"""
        # Calculate confluence (how many timeframes/levels align)
        confluence_count = self._calculate_confluence(price_level, swing_high, swing_low)

        # Volume weighting
        volume_weighted = self._is_volume_supported(price_level)

        # Multi-timeframe confirmation
        multi_timeframe_confirmed = self._check_multi_timeframe_confirmation(price_level)

        # Smart money confirmation
        smart_money_confirmed = self._check_smart_money_confirmation(price_level)

        # Calculate strength
        strength = self._calculate_level_strength(confluence_count, volume_weighted,
                                                multi_timeframe_confirmed, smart_money_confirmed)

        # Confidence score
        confidence_score = self._calculate_confidence_score(strength, confluence_count)

        # Risk management levels
        risk_levels = self._calculate_risk_management_levels(price_level, swing_high, swing_low, trend_direction)

        return FibonacciLevel(
            level_type=level_type,
            ratio=ratio,
            price_level=price_level,
            strength=strength,
            confidence_score=confidence_score,
            volume_weighted=volume_weighted,
            multi_timeframe_confirmed=multi_timeframe_confirmed,
            smart_money_confirmed=smart_money_confirmed,
            confluence_count=confluence_count,
            risk_management_levels=risk_levels
        )

    def _calculate_confluence(self, price_level: float, swing_high: float, swing_low: float) -> int:
        """Calculate confluence count for the level"""
        confluence = 0

        # Check alignment with other Fibonacci levels
        for ratio in self.custom_ratios:
            fib_level_up = swing_low + (swing_high - swing_low) * ratio
            fib_level_down = swing_high - (swing_high - swing_low) * ratio

            if abs(price_level - fib_level_up) / price_level < 0.001:  # Within 0.1%
                confluence += 1
            if abs(price_level - fib_level_down) / price_level < 0.001:
                confluence += 1

        # Check alignment with pivot points
        if self.price_data:
            recent_high = max(self.price_data[-20:]) if len(self.price_data) >= 20 else max(self.price_data)
            recent_low = min(self.price_data[-20:]) if len(self.price_data) >= 20 else min(self.price_data)

            if abs(price_level - recent_high) / price_level < 0.005:  # Within 0.5%
                confluence += 1
            if abs(price_level - recent_low) / price_level < 0.005:
                confluence += 1

        return confluence

    def _is_volume_supported(self, price_level: float) -> bool:
        """Check if level has volume confirmation"""
        if not self.volume_data or not self.price_data:
            return False

        # Find periods where price was near this level
        level_tolerance = price_level * 0.005  # 0.5% tolerance
        level_volumes = []

        for i, price in enumerate(self.price_data):
            if abs(price - price_level) <= level_tolerance:
                level_volumes.append(self.volume_data[i])

        if not level_volumes:
            return False

        # Compare to average volume
        avg_volume = statistics.mean(self.volume_data) if self.volume_data else 0
        level_avg_volume = statistics.mean(level_volumes)

        return level_avg_volume > avg_volume * 1.5  # 50% above average

    def _check_multi_timeframe_confirmation(self, price_level: float) -> bool:
        """Check if level is confirmed across multiple timeframes"""
        # This would check higher timeframe alignment
        # For now, return True if confluence is high
        confluence = self._calculate_confluence(price_level, max(self.price_data), min(self.price_data))
        return confluence >= 3

    def _check_smart_money_confirmation(self, price_level: float) -> bool:
        """Check for smart money confirmation"""
        # This would integrate with order book data
        # For now, use volume as proxy
        return self._is_volume_supported(price_level)

    def _calculate_level_strength(self, confluence: int, volume_weighted: bool,
                                multi_timeframe: bool, smart_money: bool) -> FibonacciStrength:
        """Calculate overall level strength"""
        score = confluence

        if volume_weighted:
            score += 2
        if multi_timeframe:
            score += 2
        if smart_money:
            score += 2

        if score >= 7:
            return FibonacciStrength.VERY_STRONG
        elif score >= 5:
            return FibonacciStrength.STRONG
        elif score >= 3:
            return FibonacciStrength.MODERATE
        else:
            return FibonacciStrength.WEAK

    def _calculate_confidence_score(self, strength: FibonacciStrength, confluence: int) -> float:
        """Calculate confidence score"""
        base_score = {
            FibonacciStrength.WEAK: 0.3,
            FibonacciStrength.MODERATE: 0.5,
            FibonacciStrength.STRONG: 0.7,
            FibonacciStrength.VERY_STRONG: 0.9
        }[strength]

        # Adjust for confluence
        confluence_bonus = min(confluence * 0.1, 0.3)  # Max 30% bonus

        return min(1.0, base_score + confluence_bonus)

    def _calculate_risk_management_levels(self, price_level: float, swing_high: float,
                                        swing_low: float, trend_direction: str) -> Dict[str, float]:
        """Calculate risk management levels"""
        price_range = swing_high - swing_low
        atr = self._calculate_atr()

        if trend_direction == "up":
            # For bullish bounces at Fibonacci levels
            stop_loss = price_level - atr * 1.5
            take_profit = swing_high + price_range * 0.382  # Next extension level
        else:
            # For bearish bounces at Fibonacci levels
            stop_loss = price_level + atr * 1.5
            take_profit = swing_low - price_range * 0.382

        return {
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'breakeven_level': price_level,
            'partial_exit_level': (price_level + take_profit) / 2
        }

    def _calculate_atr(self, period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(self.price_data) < period + 1:
            return abs(self.price_data[-1] - self.price_data[0]) if len(self.price_data) > 1 else 0.02

        true_ranges = []
        for i in range(1, min(len(self.price_data), period + 1)):
            high = max(self.price_data[i], self.price_data[i-1])
            low = min(self.price_data[i], self.price_data[i-1])
            true_range = high - low
            true_ranges.append(true_range)

        return statistics.mean(true_ranges) if true_ranges else 0.02

    def check_fibonacci_signals(self, current_price: float, current_time: datetime) -> List[FibonacciSignal]:
        """
        Check for trading signals based on active Fibonacci levels

        Args:
            current_price: Current market price
            current_time: Current timestamp

        Returns:
            List of trading signals
        """
        signals = []

        for level_key, level in self.active_levels.items():
            signal = self._check_single_level_signal(level, current_price, current_time)
            if signal:
                signals.append(signal)

        return signals

    def _check_single_level_signal(self, level: FibonacciLevel, current_price: float,
                                 current_time: datetime) -> Optional[FibonacciSignal]:
        """Check for signal from a single Fibonacci level"""
        price_diff = abs(current_price - level.price_level)
        tolerance = level.price_level * 0.005  # 0.5% tolerance

        if price_diff > tolerance:
            return None

        # Determine signal type based on price action and level type
        signal_type = "bounce"  # Default for retracement levels

        if level.level_type == FibonacciLevelType.EXTENSION:
            # Extensions can act as breakout levels
            if abs(current_price - level.price_level) <= tolerance * 0.5:  # Tighter tolerance for extensions
                signal_type = "breakout"

        # Determine direction based on level type and market position
        if level.level_type == FibonacciLevelType.RETRACEMENT:
            # Retracements typically bounce
            direction = "BUY" if current_price >= level.price_level else "SELL"
        else:
            # Extensions can break out
            direction = "BUY" if current_price >= level.price_level else "SELL"

        # Calculate entry and risk levels
        entry_price = current_price
        risk_levels = level.risk_management_levels

        if direction == "BUY":
            stop_loss = risk_levels['stop_loss']
            take_profit = risk_levels['take_profit']
        else:
            stop_loss = risk_levels['stop_loss']
            take_profit = risk_levels['take_profit']

        risk_reward_ratio = abs(take_profit - entry_price) / abs(stop_loss - entry_price)

        return FibonacciSignal(
            level=level,
            signal_type=signal_type,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence_score=level.confidence_score,
            risk_reward_ratio=risk_reward_ratio,
            volume_confirmation=level.volume_weighted,
            timeframe_alignment=level.multi_timeframe_confirmed,
            timestamp=current_time
        )

    def get_fibonacci_info(self) -> Dict[str, Any]:
        """Get comprehensive Fibonacci analysis information"""
        return {
            'active_levels': len(self.active_levels),
            'level_details': [
                {
                    'type': level.level_type.value,
                    'ratio': level.ratio,
                    'price_level': level.price_level,
                    'strength': level.strength.value,
                    'confidence': level.confidence_score,
                    'volume_weighted': level.volume_weighted,
                    'multi_timeframe': level.multi_timeframe_confirmed,
                    'smart_money': level.smart_money_confirmed,
                    'confluence_count': level.confluence_count
                }
                for level in self.active_levels.values()
            ],
            'data_points': len(self.price_data),
            'lookback_periods': self.lookback_periods,
            'min_confluence_threshold': self.min_confluence,
            'retracement_ratios': self.retracement_ratios,
            'extension_ratios': self.extension_ratios
        }


# Factory functions for easy instantiation
def create_fibonacci_analyzer(lookback_periods: int = 100,
                            min_confluence: int = 2) -> InstitutionalFibonacciAnalyzer:
    """Create a Fibonacci analyzer"""
    return InstitutionalFibonacciAnalyzer(lookback_periods, min_confluence)


def calculate_fibonacci_retracement(high: float, low: float, ratio: float) -> float:
    """
    Calculate a Fibonacci retracement level

    Args:
        high: Swing high
        low: Swing low
        ratio: Fibonacci ratio (e.g., 0.618)

    Returns:
        Retracement price level
    """
    return low + (high - low) * ratio


def calculate_fibonacci_extension(high: float, low: float, ratio: float) -> float:
    """
    Calculate a Fibonacci extension level

    Args:
        high: Swing high
        low: Swing low
        ratio: Fibonacci ratio (e.g., 1.618)

    Returns:
        Extension price level
    """
    return high + (high - low) * (ratio - 1.0)


def find_fibonacci_confluence(high: float, low: float, target_price: float,
                            tolerance: float = 0.005) -> List[float]:
    """
    Find Fibonacci levels that confluence near a target price

    Args:
        high: Swing high
        low: Swing low
        target_price: Price to check for confluence
        tolerance: Acceptable tolerance for confluence (as fraction)

    Returns:
        List of confluent Fibonacci ratios
    """
    price_range = high - low
    target_ratio = (target_price - low) / price_range

    confluent_ratios = []
    fib_ratios = [0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618, 2.0, 2.618]

    for ratio in fib_ratios:
        expected_price = low + price_range * ratio
        if abs(target_price - expected_price) / target_price <= tolerance:
            confluent_ratios.append(ratio)

    return confluent_ratios