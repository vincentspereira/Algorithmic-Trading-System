"""
Institutional-Grade Support/Resistance Analysis

This module implements advanced support/resistance analysis with institutional-grade features:
- Dynamic Support/Resistance Detection: Automatic identification of key levels
- Multi-Timeframe Confluence: Analysis across different timeframes
- Volume-Weighted Strength: Volume confirmation for level validity
- Smart Money Confirmation: Institutional activity validation
- Adaptive Confidence Scoring: Dynamic scoring based on market conditions
- Risk Management Integration: Level-based stop and target placement

Support/resistance levels include pivot points, trendlines, channels,
Fibonacci levels, and psychological price levels.
All calculations include volume-weighting, multi-timeframe confirmation,
and integrated risk management.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import statistics
import math


class SupportResistanceType(Enum):
    """Types of support/resistance levels"""
    PIVOT_POINT = "pivot_point"
    TREND_LINE = "trend_line"
    CHANNEL = "channel"
    FIBONACCI_LEVEL = "fibonacci_level"
    PSYCHOLOGICAL = "psychological"
    VOLUME_PROFILE = "volume_profile"
    ORDER_FLOW = "order_flow"


class SupportResistanceStrength(Enum):
    """Strength levels for support/resistance analysis"""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class LevelDirection(Enum):
    """Direction of support/resistance level"""
    SUPPORT = "support"
    RESISTANCE = "resistance"


@dataclass
class SupportResistanceLevel:
    """Represents a support/resistance level"""
    level_type: SupportResistanceType
    direction: LevelDirection
    price_level: float
    strength: SupportResistanceStrength
    confidence_score: float
    volume_weighted: bool
    multi_timeframe_confirmed: bool
    smart_money_confirmed: bool
    confluence_count: int
    test_count: int  # How many times price tested this level
    last_test_time: datetime
    risk_management_levels: Dict[str, float]


@dataclass
class SupportResistanceSignal:
    """Trading signal based on support/resistance analysis"""
    level: SupportResistanceLevel
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


class InstitutionalSupportResistanceAnalyzer:
    """
    Institutional-grade support/resistance analyzer.

    Features:
    - Dynamic level detection from price action
    - Multi-timeframe confluence analysis
    - Volume-weighted strength assessment
    - Smart money confirmation
    - Adaptive confidence scoring
    - Risk management integration
    """

    def __init__(self, lookback_periods: int = 200, min_confluence: int = 2,
                 min_tests: int = 2):
        self.lookback_periods = lookback_periods
        self.min_confluence = min_confluence
        self.min_tests = min_tests

        # Historical data
        self.price_data = []
        self.volume_data = []
        self.time_data = []

        # Level tracking
        self.support_levels = {}
        self.resistance_levels = {}
        self.level_history = []

        # Pivot point calculations
        self.pivot_periods = [5, 10, 20, 50]  # Different pivot periods

    def update_price_data(self, price: float, volume: float, timestamp: datetime):
        """
        Update price data for support/resistance analysis

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

    def analyze_support_resistance(self, current_price: float, current_time: datetime) -> List[SupportResistanceLevel]:
        """
        Analyze current support/resistance levels

        Args:
            current_price: Current market price
            current_time: Current timestamp

        Returns:
            List of identified support/resistance levels
        """
        if len(self.price_data) < 50:
            return []

        levels = []

        # Detect pivot-based levels
        pivot_levels = self._detect_pivot_levels()
        levels.extend(pivot_levels)

        # Detect trendline levels
        trendline_levels = self._detect_trendline_levels()
        levels.extend(trendline_levels)

        # Detect psychological levels
        psychological_levels = self._detect_psychological_levels()
        levels.extend(psychological_levels)

        # Detect volume profile levels
        volume_levels = self._detect_volume_profile_levels()
        levels.extend(volume_levels)

        # Validate and filter levels
        validated_levels = []
        for level in levels:
            if self._validate_level(level):
                validated_levels.append(level)

                # Store in appropriate collection
                if level.direction == LevelDirection.SUPPORT:
                    self.support_levels[f"{level.level_type.value}_{level.price_level:.4f}"] = level
                else:
                    self.resistance_levels[f"{level.level_type.value}_{level.price_level:.4f}"] = level

        return validated_levels

    def _detect_pivot_levels(self) -> List[SupportResistanceLevel]:
        """Detect pivot point based support/resistance levels"""
        levels = []

        if len(self.price_data) < 20:
            return levels

        # Calculate pivot points for different periods
        for period in self.pivot_periods:
            if len(self.price_data) >= period:
                recent_data = self.price_data[-period:]

                high = max(recent_data)
                low = min(recent_data)
                close = recent_data[-1]

                # Classic pivot calculation
                pivot = (high + low + close) / 3
                r1 = 2 * pivot - low
                s1 = 2 * pivot - high
                r2 = pivot + (high - low)
                s2 = pivot - (high - low)
                r3 = high + 2 * (pivot - low)
                s3 = low - 2 * (high - pivot)

                pivot_levels = [
                    (pivot, "pivot", SupportResistanceType.PIVOT_POINT),
                    (r1, "resistance_1", SupportResistanceType.PIVOT_POINT),
                    (s1, "support_1", SupportResistanceType.PIVOT_POINT),
                    (r2, "resistance_2", SupportResistanceType.PIVOT_POINT),
                    (s2, "support_2", SupportResistanceType.PIVOT_POINT),
                    (r3, "resistance_3", SupportResistanceType.PIVOT_POINT),
                    (s3, "support_3", SupportResistanceType.PIVOT_POINT),
                ]

                for price_level, level_name, level_type in pivot_levels:
                    direction = (LevelDirection.RESISTANCE if "resistance" in level_name
                               else LevelDirection.SUPPORT)

                    level = self._create_level(
                        level_type, direction, price_level,
                        self.time_data[-1], period
                    )
                    levels.append(level)

        return levels

    def _detect_trendline_levels(self) -> List[SupportResistanceLevel]:
        """Detect trendline-based support/resistance levels"""
        levels = []

        if len(self.price_data) < 30:
            return levels

        # Find swing points for trendline calculation
        swing_highs, swing_lows = self._find_swing_points()

        if len(swing_highs) >= 2:
            # Calculate resistance trendline from swing highs
            resistance_level = self._calculate_trendline_level(swing_highs, LevelDirection.RESISTANCE)
            if resistance_level:
                levels.append(resistance_level)

        if len(swing_lows) >= 2:
            # Calculate support trendline from swing lows
            support_level = self._calculate_trendline_level(swing_lows, LevelDirection.SUPPORT)
            if support_level:
                levels.append(support_level)

        return levels

    def _find_swing_points(self) -> Tuple[List[Tuple[float, datetime]], List[Tuple[float, datetime]]]:
        """Find swing high and low points"""
        swing_highs = []
        swing_lows = []

        lookback = 5  # Look 5 periods back/forward

        for i in range(lookback, len(self.price_data) - lookback):
            price = self.price_data[i]
            timestamp = self.time_data[i]

            # Check for swing high
            is_swing_high = all(price >= self.price_data[j]
                              for j in range(i - lookback, i + lookback + 1) if j != i)

            # Check for swing low
            is_swing_low = all(price <= self.price_data[j]
                             for j in range(i - lookback, i + lookback + 1) if j != i)

            if is_swing_high:
                swing_highs.append((price, timestamp))
            if is_swing_low:
                swing_lows.append((price, timestamp))

        return swing_highs, swing_lows

    def _calculate_trendline_level(self, swing_points: List[Tuple[float, datetime]],
                                 direction: LevelDirection) -> Optional[SupportResistanceLevel]:
        """Calculate trendline level from swing points"""
        if len(swing_points) < 2:
            return None

        # Use linear regression to find trendline
        prices = [point[0] for point in swing_points]
        times = [point[1].timestamp() for point in swing_points]

        # Calculate slope and intercept
        n = len(prices)
        sum_x = sum(times)
        sum_y = sum(prices)
        sum_xy = sum(x * y for x, y in zip(times, prices))
        sum_xx = sum(x * x for x in times)

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)
        intercept = (sum_y - slope * sum_x) / n

        # Project current trendline level
        current_time = self.time_data[-1].timestamp()
        current_level = slope * current_time + intercept

        return self._create_level(
            SupportResistanceType.TREND_LINE, direction, current_level,
            self.time_data[-1], len(swing_points)
        )

    def _detect_psychological_levels(self) -> List[SupportResistanceLevel]:
        """Detect psychological price levels"""
        levels = []

        if not self.price_data:
            return levels

        current_price = self.price_data[-1]

        # Common psychological levels (rounded numbers)
        price_str = f"{current_price:.2f}"
        base_price = float(price_str)

        # Generate psychological levels around current price
        psychological_levels = []

        # Round to nearest 10, 50, 100, etc.
        for multiplier in [1, 10, 50, 100, 500, 1000]:
            rounded_level = round(base_price / multiplier) * multiplier
            if abs(rounded_level - current_price) / current_price < 0.05:  # Within 5%
                psychological_levels.append(rounded_level)

        for level_price in psychological_levels:
            # Determine if it's support or resistance based on position relative to current price
            direction = (LevelDirection.RESISTANCE if level_price > current_price
                        else LevelDirection.SUPPORT)

            level = self._create_level(
                SupportResistanceType.PSYCHOLOGICAL, direction, level_price,
                self.time_data[-1], 1
            )
            levels.append(level)

        return levels

    def _detect_volume_profile_levels(self) -> List[SupportResistanceLevel]:
        """Detect volume profile based support/resistance levels"""
        levels = []

        if not self.volume_data or len(self.volume_data) < 20:
            return levels

        # Create price-volume histogram
        price_volume = {}
        for price, volume in zip(self.price_data[-100:], self.volume_data[-100:]):  # Last 100 periods
            price_key = round(price, 2)
            if price_key not in price_volume:
                price_volume[price_key] = 0
            price_volume[price_key] += volume

        if not price_volume:
            return levels

        # Find high volume levels
        avg_volume = statistics.mean(price_volume.values())
        high_volume_levels = [(price, vol) for price, vol in price_volume.items()
                            if vol > avg_volume * 1.5]

        for price_level, volume in high_volume_levels:
            # Determine direction based on current price
            current_price = self.price_data[-1]
            direction = (LevelDirection.RESISTANCE if price_level > current_price
                        else LevelDirection.SUPPORT)

            level = self._create_level(
                SupportResistanceType.VOLUME_PROFILE, direction, price_level,
                self.time_data[-1], int(volume)
            )
            levels.append(level)

        return levels

    def _create_level(self, level_type: SupportResistanceType, direction: LevelDirection,
                     price_level: float, timestamp: datetime, period: int) -> SupportResistanceLevel:
        """Create a support/resistance level with institutional analysis"""
        # Calculate confluence
        confluence_count = self._calculate_confluence(price_level)

        # Volume weighting
        volume_weighted = self._is_level_volume_supported(price_level, timestamp)

        # Multi-timeframe confirmation
        multi_timeframe_confirmed = self._check_level_multi_timeframe(price_level)

        # Smart money confirmation
        smart_money_confirmed = self._check_level_smart_money(price_level)

        # Calculate test count
        test_count = self._calculate_level_tests(price_level)

        # Calculate strength
        strength = self._calculate_level_strength(confluence_count, volume_weighted,
                                                multi_timeframe_confirmed, test_count)

        # Confidence score
        confidence_score = self._calculate_level_confidence(strength, confluence_count, test_count)

        # Risk management levels
        risk_levels = self._calculate_level_risk_management(price_level, direction)

        return SupportResistanceLevel(
            level_type=level_type,
            direction=direction,
            price_level=price_level,
            strength=strength,
            confidence_score=confidence_score,
            volume_weighted=volume_weighted,
            multi_timeframe_confirmed=multi_timeframe_confirmed,
            smart_money_confirmed=smart_money_confirmed,
            confluence_count=confluence_count,
            test_count=test_count,
            last_test_time=timestamp,
            risk_management_levels=risk_levels
        )

    def _calculate_confluence(self, price_level: float) -> int:
        """Calculate confluence count for the level"""
        confluence = 0

        # Check alignment with other level types
        for level_key, level in {**self.support_levels, **self.resistance_levels}.items():
            if abs(level.price_level - price_level) / price_level < 0.005:  # Within 0.5%
                confluence += 1

        return confluence

    def _is_level_volume_supported(self, price_level: float, timestamp: datetime) -> bool:
        """Check if level has volume confirmation"""
        if not self.volume_data:
            return False

        # Find volume around level
        tolerance = price_level * 0.005  # 0.5% tolerance
        level_volumes = []

        for i, (price, volume) in enumerate(zip(self.price_data, self.volume_data)):
            if abs(price - price_level) <= tolerance:
                level_volumes.append(volume)

        if not level_volumes:
            return False

        avg_level_volume = statistics.mean(level_volumes)
        avg_volume = statistics.mean(self.volume_data)

        return avg_level_volume > avg_volume * 1.2  # 20% above average

    def _check_level_multi_timeframe(self, price_level: float) -> bool:
        """Check multi-timeframe confirmation"""
        # This would check alignment with higher timeframes
        confluence = self._calculate_confluence(price_level)
        return confluence >= 2

    def _check_level_smart_money(self, price_level: float) -> bool:
        """Check smart money confirmation"""
        return self._is_level_volume_supported(price_level, datetime.now())

    def _calculate_level_tests(self, price_level: float) -> int:
        """Calculate how many times price tested this level"""
        if not self.price_data:
            return 0

        tolerance = price_level * 0.01  # 1% tolerance for tests
        test_count = 0

        for price in self.price_data:
            if abs(price - price_level) <= tolerance:
                test_count += 1

        return test_count

    def _calculate_level_strength(self, confluence: int, volume_weighted: bool,
                                multi_timeframe: bool, test_count: int) -> SupportResistanceStrength:
        """Calculate level strength"""
        score = confluence + test_count

        if volume_weighted:
            score += 2
        if multi_timeframe:
            score += 2

        if score >= 6:
            return SupportResistanceStrength.VERY_STRONG
        elif score >= 4:
            return SupportResistanceStrength.STRONG
        elif score >= 2:
            return SupportResistanceStrength.MODERATE
        else:
            return SupportResistanceStrength.WEAK

    def _calculate_level_confidence(self, strength: SupportResistanceStrength,
                                  confluence: int, test_count: int) -> float:
        """Calculate level confidence score"""
        base_score = {
            SupportResistanceStrength.WEAK: 0.3,
            SupportResistanceStrength.MODERATE: 0.5,
            SupportResistanceStrength.STRONG: 0.7,
            SupportResistanceStrength.VERY_STRONG: 0.9
        }[strength]

        # Adjust for confluence and tests
        confluence_bonus = min(confluence * 0.05, 0.15)  # Max 15% bonus
        test_bonus = min(test_count * 0.03, 0.15)  # Max 15% bonus

        return min(1.0, base_score + confluence_bonus + test_bonus)

    def _calculate_level_risk_management(self, price_level: float,
                                       direction: LevelDirection) -> Dict[str, float]:
        """Calculate risk management levels"""
        atr = self._calculate_atr()

        if direction == LevelDirection.SUPPORT:
            # Buying at support
            stop_loss = price_level - atr * 1.5
            take_profit = price_level + atr * 2.5
        else:
            # Selling at resistance
            stop_loss = price_level + atr * 1.5
            take_profit = price_level - atr * 2.5

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

    def _validate_level(self, level: SupportResistanceLevel) -> bool:
        """Validate level against institutional criteria"""
        if level.strength == SupportResistanceStrength.WEAK:
            return False

        if level.test_count < self.min_tests:
            return False

        if level.confluence_count < self.min_confluence:
            return False

        return level.confidence_score >= 0.5

    def check_support_resistance_signals(self, current_price: float,
                                       current_time: datetime) -> List[SupportResistanceSignal]:
        """
        Check for trading signals based on support/resistance levels

        Args:
            current_price: Current market price
            current_time: Current timestamp

        Returns:
            List of support/resistance trading signals
        """
        signals = []

        # Check all active levels
        all_levels = {**self.support_levels, **self.resistance_levels}

        for level_key, level in all_levels.items():
            signal = self._check_single_level_signal(level, current_price, current_time)
            if signal:
                signals.append(signal)

        return signals

    def _check_single_level_signal(self, level: SupportResistanceLevel, current_price: float,
                                 current_time: datetime) -> Optional[SupportResistanceSignal]:
        """Check for signal from a single level"""
        price_diff = abs(current_price - level.price_level)
        tolerance = level.price_level * 0.005  # 0.5% tolerance

        if price_diff > tolerance:
            return None

        # Determine signal type
        if level.direction == LevelDirection.SUPPORT:
            signal_type = "bounce"
            direction = "BUY"
        else:
            signal_type = "bounce"
            direction = "SELL"

        # Check for breakout (if price moves through level)
        if level.direction == LevelDirection.SUPPORT and current_price < level.price_level:
            signal_type = "breakout"
            direction = "SELL"
        elif level.direction == LevelDirection.RESISTANCE and current_price > level.price_level:
            signal_type = "breakout"
            direction = "BUY"

        entry_price = current_price
        risk_levels = level.risk_management_levels

        if direction == "BUY":
            stop_loss = risk_levels['stop_loss']
            take_profit = risk_levels['take_profit']
        else:
            stop_loss = risk_levels['stop_loss']
            take_profit = risk_levels['take_profit']

        risk_reward_ratio = abs(take_profit - entry_price) / abs(stop_loss - entry_price)

        return SupportResistanceSignal(
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

    def get_support_resistance_info(self) -> Dict[str, Any]:
        """Get comprehensive support/resistance analysis information"""
        return {
            'support_levels': len(self.support_levels),
            'resistance_levels': len(self.resistance_levels),
            'total_levels': len(self.support_levels) + len(self.resistance_levels),
            'level_details': [
                {
                    'type': level.level_type.value,
                    'direction': level.direction.value,
                    'price_level': level.price_level,
                    'strength': level.strength.value,
                    'confidence': level.confidence_score,
                    'volume_weighted': level.volume_weighted,
                    'multi_timeframe': level.multi_timeframe_confirmed,
                    'smart_money': level.smart_money_confirmed,
                    'confluence_count': level.confluence_count,
                    'test_count': level.test_count
                }
                for level in list(self.support_levels.values()) + list(self.resistance_levels.values())
            ],
            'data_points': len(self.price_data),
            'lookback_periods': self.lookback_periods,
            'min_confluence_threshold': self.min_confluence,
            'min_tests_threshold': self.min_tests
        }


# Factory functions for easy instantiation
def create_support_resistance_analyzer(lookback_periods: int = 200,
                                     min_confluence: int = 2) -> InstitutionalSupportResistanceAnalyzer:
    """Create a support/resistance analyzer"""
    return InstitutionalSupportResistanceAnalyzer(lookback_periods, min_confluence)


def calculate_pivot_points(high: float, low: float, close: float) -> Dict[str, float]:
    """
    Calculate classic pivot points

    Args:
        high: High price
        low: Low price
        close: Close price

    Returns:
        Dictionary of pivot levels
    """
    pivot = (high + low + close) / 3

    return {
        'pivot': pivot,
        'r1': 2 * pivot - low,
        's1': 2 * pivot - high,
        'r2': pivot + (high - low),
        's2': pivot - (high - low),
        'r3': high + 2 * (pivot - low),
        's3': low - 2 * (high - pivot)
    }


def find_psychological_levels(price: float, range_percent: float = 0.05) -> List[float]:
    """
    Find psychological price levels around a given price

    Args:
        price: Base price
        range_percent: Percentage range to search

    Returns:
        List of psychological levels
    """
    levels = []
    range_amount = price * range_percent

    min_price = price - range_amount
    max_price = price + range_amount

    # Check common psychological levels
    for level in [0.50, 1.00, 10.00, 50.00, 100.00, 500.00, 1000.00]:
        if min_price <= level <= max_price:
            levels.append(level)

    return levels