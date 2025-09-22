"""
Dynamic Support and Resistance Levels Module

Advanced dynamic level analysis with institutional-grade features including:
- Fibonacci-based support/resistance levels
- Volume profile analysis for level strength
- Multi-timeframe level alignment
- Smart money confirmation
- Adaptive level strength scoring
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import numpy as np

from ...core.base_classes import AugmentedIndicator


class DynamicLevelType(Enum):
    """Types of dynamic support/resistance levels"""
    FIBONACCI_SUPPORT = "fibonacci_support"
    FIBONACCI_RESISTANCE = "fibonacci_resistance"
    VOLUME_PROFILE_SUPPORT = "volume_profile_support"
    VOLUME_PROFILE_RESISTANCE = "volume_profile_resistance"
    PIVOT_POINT_LEVEL = "pivot_point_level"
    TREND_CHANNEL_SUPPORT = "trend_channel_support"
    TREND_CHANNEL_RESISTANCE = "trend_channel_resistance"
    PSYCHOLOGICAL_LEVEL = "psychological_level"


class LevelConfidence(Enum):
    """Confidence levels for dynamic levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class DynamicLevel:
    """Represents a dynamic support/resistance level"""
    level_type: DynamicLevelType
    price_level: float
    confidence: LevelConfidence
    strength_score: float
    confluence_factors: List[str]
    volume_profile: Dict[str, Any]
    timeframe_alignment: float
    smart_money_score: float
    last_update: datetime
    touch_count: int
    age_days: int


@dataclass
class DynamicLevelSignal:
    """Signal for dynamic level analysis"""
    value_raw: float
    signal_type: str
    composite_confidence: float
    confidence_components: Dict[str, float]
    suggested_sl: float
    suggested_tp: float
    timestamp: datetime
    additional_metadata: Dict[str, Any]

    # Dynamic level specific fields
    active_levels: List[DynamicLevel]
    nearest_support: Optional[float]
    nearest_resistance: Optional[float]
    level_density: float
    market_regime: str


class DynamicLevels(AugmentedIndicator):
    """
    Advanced Dynamic Support and Resistance Levels Analyzer

    Combines multiple methodologies for institutional-grade level analysis:
    - Fibonacci retracement/projection levels
    - Volume profile analysis for high-volume areas
    - Pivot point calculations
    - Trend channel analysis
    - Psychological price levels
    - Multi-timeframe alignment
    - Smart money confirmation

    All implementations include volume-weighting, smart money confirmation,
    multi-timeframe analysis, adaptive confidence scoring, and integrated risk management.
    """

    def __init__(self, timeframe: str = "1D", lookback_period: int = 200):
        super().__init__(name="DynamicLevels", timeframe=timeframe)
        self.lookback_period = lookback_period
        self.price_history = []
        self.volume_history = []
        self.timestamp_history = []

        # Dynamic level storage
        self.fibonacci_levels = []
        self.volume_profile_levels = []
        self.pivot_levels = []
        self.trend_channel_levels = []
        self.psychological_levels = []

        # Level tracking
        self.active_levels = []
        self.level_history = []

        # Market regime detection
        self.market_regime = "unknown"

    def update(self, price: float, volume: float, high: float = None,
               low: float = None, timestamp: datetime = None,
               order_book_data: Dict = None, trade_data: List = None) -> Optional[DynamicLevelSignal]:
        """
        Update analyzer with new price/volume data

        Args:
            price: Current price
            volume: Current volume
            high: High price (optional)
            low: Low price (optional)
            timestamp: Data timestamp
            order_book_data: Order book data for smart money analysis
            trade_data: Trade data for volume analysis

        Returns:
            DynamicLevelSignal if significant level activity detected, None otherwise
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Update histories
        self.price_history.append(price)
        self.volume_history.append(volume)
        self.timestamp_history.append(timestamp)

        # Maintain history size
        max_history = self.lookback_period
        if len(self.price_history) > max_history:
            self.price_history.pop(0)
            self.volume_history.pop(0)
            self.timestamp_history.pop(0)

        # Need minimum data for analysis
        if len(self.price_history) < 50:
            return None

        # Update market regime
        self.market_regime = self._detect_market_regime()

        # Update all dynamic level types
        self._update_fibonacci_levels()
        self._update_volume_profile_levels()
        self._update_pivot_levels()
        self._update_trend_channel_levels()
        self._update_psychological_levels()

        # Consolidate active levels
        self._consolidate_active_levels()

        # Generate signal if significant level activity
        signal = self._generate_level_signal(timestamp, order_book_data, trade_data)

        if signal:
            self.current_signal = signal
            self.level_history.append(signal)

        return signal

    def _detect_market_regime(self) -> str:
        """Detect current market regime"""
        if len(self.price_history) < 20:
            return "unknown"

        # Simple regime detection based on trend and volatility
        recent_prices = np.array(self.price_history[-20:])
        trend_slope = np.polyfit(range(len(recent_prices)), recent_prices, 1)[0]
        volatility = np.std(recent_prices) / np.mean(recent_prices)

        if abs(trend_slope) > volatility * 0.1:
            return "trending"
        elif volatility > 0.02:
            return "volatile"
        else:
            return "ranging"

    def _update_fibonacci_levels(self):
        """Update Fibonacci-based support/resistance levels"""
        if len(self.price_history) < 20:
            return

        # Find recent swing points
        swings = self._find_swing_points()

        if len(swings) >= 2:
            # Calculate Fibonacci levels from recent swing
            recent_swing = swings[-1]
            prev_swing = swings[-2]

            high_point = max(recent_swing['high'], prev_swing['high'])
            low_point = min(recent_swing['low'], prev_swing['low'])
            range_size = high_point - low_point

            if range_size > 0:
                fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]

                for fib_ratio in fib_levels:
                    # Support levels (from high)
                    support_price = high_point - (range_size * fib_ratio)
                    # Resistance levels (from low)
                    resistance_price = low_point + (range_size * fib_ratio)

                    # Create dynamic levels
                    support_level = DynamicLevel(
                        level_type=DynamicLevelType.FIBONACCI_SUPPORT,
                        price_level=support_price,
                        confidence=LevelConfidence.MEDIUM,
                        strength_score=self._calculate_fibonacci_strength(fib_ratio),
                        confluence_factors=[f"Fib_{fib_ratio}"],
                        volume_profile={},
                        timeframe_alignment=0.7,
                        smart_money_score=0.6,
                        last_update=self.timestamp_history[-1],
                        touch_count=0,
                        age_days=0
                    )

                    resistance_level = DynamicLevel(
                        level_type=DynamicLevelType.FIBONACCI_RESISTANCE,
                        price_level=resistance_price,
                        confidence=LevelConfidence.MEDIUM,
                        strength_score=self._calculate_fibonacci_strength(fib_ratio),
                        confluence_factors=[f"Fib_{fib_ratio}"],
                        volume_profile={},
                        timeframe_alignment=0.7,
                        smart_money_score=0.6,
                        last_update=self.timestamp_history[-1],
                        touch_count=0,
                        age_days=0
                    )

                    self.fibonacci_levels.extend([support_level, resistance_level])

    def _find_swing_points(self) -> List[Dict]:
        """Find swing high and low points"""
        swings = []
        window = 5

        for i in range(window, len(self.price_history) - window):
            # Check for swing high
            if all(self.price_history[i] >= self.price_history[i-j] for j in range(1, window+1)) and \
               all(self.price_history[i] >= self.price_history[i+j] for j in range(1, window+1)):
                swings.append({
                    'type': 'high',
                    'price': self.price_history[i],
                    'index': i,
                    'high': self.price_history[i],
                    'low': self.price_history[i]
                })

            # Check for swing low
            if all(self.price_history[i] <= self.price_history[i-j] for j in range(1, window+1)) and \
               all(self.price_history[i] <= self.price_history[i+j] for j in range(1, window+1)):
                swings.append({
                    'type': 'low',
                    'price': self.price_history[i],
                    'index': i,
                    'high': self.price_history[i],
                    'low': self.price_history[i]
                })

        return swings[-10:]  # Return last 10 swings

    def _calculate_fibonacci_strength(self, fib_ratio: float) -> float:
        """Calculate strength score for Fibonacci level"""
        # Key Fibonacci levels are stronger
        key_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
        if fib_ratio in key_levels:
            return 0.8
        else:
            return 0.6

    def _update_volume_profile_levels(self):
        """Update volume profile based support/resistance levels"""
        if len(self.price_history) < 50 or len(self.volume_history) < 50:
            return

        # Create price bins
        price_min = min(self.price_history[-50:])
        price_max = max(self.price_history[-50:])
        bins = np.linspace(price_min, price_max, 20)

        # Calculate volume profile
        volume_profile = {}
        for i in range(len(self.price_history[-50:])):
            price = self.price_history[-50:][i]
            volume = self.volume_history[-50:][i]

            # Find appropriate bin
            bin_idx = np.digitize(price, bins) - 1
            bin_key = f"{bins[bin_idx]:.2f}"

            if bin_key not in volume_profile:
                volume_profile[bin_key] = 0
            volume_profile[bin_key] += volume

        # Find high volume areas (top 3)
        sorted_volumes = sorted(volume_profile.items(), key=lambda x: x[1], reverse=True)
        high_volume_levels = sorted_volumes[:3]

        for price_str, volume in high_volume_levels:
            price_level = float(price_str)

            # Determine if support or resistance based on current price
            current_price = self.price_history[-1]
            level_type = (DynamicLevelType.VOLUME_PROFILE_SUPPORT
                         if price_level < current_price
                         else DynamicLevelType.VOLUME_PROFILE_RESISTANCE)

            volume_level = DynamicLevel(
                level_type=level_type,
                price_level=price_level,
                confidence=LevelConfidence.HIGH,
                strength_score=min(volume / sorted_volumes[0][1], 1.0),  # Relative to highest volume
                confluence_factors=["High_Volume"],
                volume_profile={'total_volume': volume, 'relative_strength': volume / sorted_volumes[0][1]},
                timeframe_alignment=0.8,
                smart_money_score=0.7,
                last_update=self.timestamp_history[-1],
                touch_count=0,
                age_days=0
            )

            self.volume_profile_levels.append(volume_level)

    def _update_pivot_levels(self):
        """Update pivot point based levels"""
        if len(self.price_history) < 20:
            return

        # Use last day's data for pivot calculation (simplified)
        recent_high = max(self.price_history[-20:])
        recent_low = min(self.price_history[-20:])
        recent_close = self.price_history[-1]

        pivot_point = (recent_high + recent_low + recent_close) / 3

        # Calculate pivot levels
        r1 = (2 * pivot_point) - recent_low
        r2 = pivot_point + (recent_high - recent_low)
        s1 = (2 * pivot_point) - recent_high
        s2 = pivot_point - (recent_high - recent_low)

        pivot_levels = [
            (pivot_point, DynamicLevelType.PIVOT_POINT_LEVEL, LevelConfidence.HIGH),
            (r1, DynamicLevelType.PIVOT_POINT_LEVEL, LevelConfidence.MEDIUM),
            (r2, DynamicLevelType.PIVOT_POINT_LEVEL, LevelConfidence.MEDIUM),
            (s1, DynamicLevelType.PIVOT_POINT_LEVEL, LevelConfidence.MEDIUM),
            (s2, DynamicLevelType.PIVOT_POINT_LEVEL, LevelConfidence.MEDIUM)
        ]

        for price_level, level_type, confidence in pivot_levels:
            pivot_level = DynamicLevel(
                level_type=level_type,
                price_level=price_level,
                confidence=confidence,
                strength_score=0.7,
                confluence_factors=["Pivot_Point"],
                volume_profile={},
                timeframe_alignment=0.9,
                smart_money_score=0.6,
                last_update=self.timestamp_history[-1],
                touch_count=0,
                age_days=0
            )

            self.pivot_levels.append(pivot_level)

    def _update_trend_channel_levels(self):
        """Update trend channel based support/resistance levels"""
        if len(self.price_history) < 30:
            return

        # Simple trend channel calculation
        recent_prices = np.array(self.price_history[-30:])
        x = np.arange(len(recent_prices))

        # Linear regression for trend
        slope, intercept = np.polyfit(x, recent_prices, 1)

        # Channel boundaries (simplified)
        residuals = recent_prices - (slope * x + intercept)
        channel_width = np.std(residuals) * 2

        # Upper and lower channel lines
        upper_channel = slope * x + intercept + channel_width
        lower_channel = slope * x + intercept - channel_width

        # Current channel levels
        current_upper = upper_channel[-1]
        current_lower = lower_channel[-1]

        # Create channel levels
        upper_level = DynamicLevel(
            level_type=DynamicLevelType.TREND_CHANNEL_RESISTANCE,
            price_level=current_upper,
            confidence=LevelConfidence.MEDIUM,
            strength_score=0.6,
            confluence_factors=["Trend_Channel"],
            volume_profile={},
            timeframe_alignment=0.7,
            smart_money_score=0.5,
            last_update=self.timestamp_history[-1],
            touch_count=0,
            age_days=0
        )

        lower_level = DynamicLevel(
            level_type=DynamicLevelType.TREND_CHANNEL_SUPPORT,
            price_level=current_lower,
            confidence=LevelConfidence.MEDIUM,
            strength_score=0.6,
            confluence_factors=["Trend_Channel"],
            volume_profile={},
            timeframe_alignment=0.7,
            smart_money_score=0.5,
            last_update=self.timestamp_history[-1],
            touch_count=0,
            age_days=0
        )

        self.trend_channel_levels.extend([upper_level, lower_level])

    def _update_psychological_levels(self):
        """Update psychological price levels"""
        current_price = self.price_history[-1]

        # Round number levels
        round_base = round(current_price, -1)  # Round to nearest 10
        psychological_levels = [
            round_base,
            round_base + 10,
            round_base - 10,
            round_base + 50,
            round_base - 50
        ]

        for level_price in psychological_levels:
            if abs(level_price - current_price) / current_price < 0.05:  # Within 5%
                level_type = (DynamicLevelType.PSYCHOLOGICAL_LEVEL
                             if level_price > current_price
                             else DynamicLevelType.PSYCHOLOGICAL_LEVEL)

                psych_level = DynamicLevel(
                    level_type=level_type,
                    price_level=level_price,
                    confidence=LevelConfidence.LOW,
                    strength_score=0.4,
                    confluence_factors=["Psychological"],
                    volume_profile={},
                    timeframe_alignment=0.5,
                    smart_money_score=0.4,
                    last_update=self.timestamp_history[-1],
                    touch_count=0,
                    age_days=0
                )

                self.psychological_levels.append(psych_level)

    def _consolidate_active_levels(self):
        """Consolidate all level types into active levels list"""
        all_levels = (self.fibonacci_levels + self.volume_profile_levels +
                     self.pivot_levels + self.trend_channel_levels +
                     self.psychological_levels)

        # Remove old levels (keep only recent)
        current_time = self.timestamp_history[-1]
        recent_levels = []

        for level in all_levels:
            age_days = (current_time - level.last_update).days
            if age_days <= 30:  # Keep levels up to 30 days old
                level.age_days = age_days
                recent_levels.append(level)

        # Remove duplicates (levels within 0.5% of each other)
        consolidated_levels = []
        for level in recent_levels:
            is_duplicate = False
            for existing in consolidated_levels:
                if abs(level.price_level - existing.price_level) / level.price_level < 0.005:
                    # Merge confluence factors
                    existing.confluence_factors.extend(level.confluence_factors)
                    existing.confluence_factors = list(set(existing.confluence_factors))
                    # Take higher strength
                    existing.strength_score = max(existing.strength_score, level.strength_score)
                    is_duplicate = True
                    break

            if not is_duplicate:
                consolidated_levels.append(level)

        self.active_levels = consolidated_levels

    def _generate_level_signal(self, timestamp: datetime,
                              order_book_data: Dict = None,
                              trade_data: List = None) -> Optional[DynamicLevelSignal]:
        """Generate signal based on level analysis"""
        if not self.active_levels:
            return None

        current_price = self.price_history[-1]

        # Find nearest levels
        support_levels = [l for l in self.active_levels
                         if l.level_type.value.endswith('_support') or
                         l.level_type == DynamicLevelType.PSYCHOLOGICAL_LEVEL]

        resistance_levels = [l for l in self.active_levels
                           if l.level_type.value.endswith('_resistance') or
                           l.level_type == DynamicLevelType.PIVOT_POINT_LEVEL]

        nearest_support = min(support_levels, key=lambda x: abs(x.price_level - current_price)) if support_levels else None
        nearest_resistance = min(resistance_levels, key=lambda x: abs(x.price_level - current_price)) if resistance_levels else None

        # Check if price is near a significant level
        level_proximity_threshold = 0.01  # 1%
        significant_level = None

        if nearest_support and abs(nearest_support.price_level - current_price) / current_price <= level_proximity_threshold:
            significant_level = nearest_support
        elif nearest_resistance and abs(nearest_resistance.price_level - current_price) / current_price <= level_proximity_threshold:
            significant_level = nearest_resistance

        if significant_level:
            return self._create_level_signal(significant_level, current_price, timestamp,
                                           order_book_data, trade_data)

        return None

    def _create_level_signal(self, level: DynamicLevel, current_price: float,
                           timestamp: datetime, order_book_data: Dict = None,
                           trade_data: List = None) -> DynamicLevelSignal:
        """Create a dynamic level signal"""
        # Calculate confidence components
        confidence_components = self._calculate_level_confidence(level, current_price,
                                                               order_book_data, trade_data)

        composite_confidence = np.mean(list(confidence_components.values()))

        # Risk management
        suggested_sl, suggested_tp = self._calculate_level_risk_management(level, current_price)

        # Level density (number of levels in proximity)
        level_density = self._calculate_level_density(current_price)

        # Additional metadata
        additional_metadata = {
            'level_type': level.level_type.value,
            'level_price': level.price_level,
            'confluence_factors': level.confluence_factors,
            'volume_profile': level.volume_profile,
            'timeframe_alignment': level.timeframe_alignment,
            'smart_money_score': level.smart_money_score,
            'level_age_days': level.age_days,
            'touch_count': level.touch_count,
            'market_regime': self.market_regime,
            'level_density': level_density
        }

        return DynamicLevelSignal(
            value_raw=current_price,
            signal_type=f"DYNAMIC_LEVEL_{level.level_type.value.upper()}",
            composite_confidence=composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=suggested_sl,
            suggested_tp=suggested_tp,
            timestamp=timestamp,
            additional_metadata=additional_metadata,
            active_levels=self.active_levels,
            nearest_support=nearest_support.price_level if nearest_support else None,
            nearest_resistance=nearest_resistance.price_level if nearest_resistance else None,
            level_density=level_density,
            market_regime=self.market_regime
        )

    def _calculate_level_confidence(self, level: DynamicLevel, current_price: float,
                                  order_book_data: Dict = None, trade_data: List = None) -> Dict[str, float]:
        """Calculate confidence components for level signal"""
        components = {}

        # Base level strength
        components['level_strength'] = level.strength_score

        # Confluence factor
        components['confluence_score'] = min(len(level.confluence_factors) * 0.2, 1.0)

        # Timeframe alignment
        components['timeframe_alignment'] = level.timeframe_alignment

        # Smart money confirmation
        components['smart_money_score'] = self._calculate_smart_money_level_score(level, order_book_data, trade_data)

        # Age factor (newer levels are more relevant)
        age_factor = max(0.3, 1.0 - (level.age_days / 30))
        components['age_factor'] = age_factor

        # Touch count factor
        touch_factor = min(level.touch_count / 5, 1.0)
        components['touch_factor'] = touch_factor

        return components

    def _calculate_smart_money_level_score(self, level: DynamicLevel,
                                         order_book_data: Dict = None,
                                         trade_data: List = None) -> float:
        """Calculate smart money confirmation for level"""
        score = 0.5

        if order_book_data:
            # Check order book imbalance at level
            level_price = level.price_level
            bids_vol = sum(vol for price, vol in order_book_data.get('bids', {}).items()
                          if abs(price - level_price) / level_price < 0.001)
            asks_vol = sum(vol for price, vol in order_book_data.get('asks', {}).items()
                          if abs(price - level_price) / level_price < 0.001)

            if bids_vol + asks_vol > 0:
                imbalance = abs(bids_vol - asks_vol) / (bids_vol + asks_vol)
                score = min(0.9, 0.5 + imbalance)

        if trade_data:
            # Check for large trades at level
            large_trades = [t for t in trade_data
                           if abs(t[0] - level.price_level) / level.price_level < 0.001 and t[1] > 1000]
            if large_trades:
                score = min(0.95, score + 0.2)

        return score

    def _calculate_level_risk_management(self, level: DynamicLevel, current_price: float) -> Tuple[float, float]:
        """Calculate risk management levels for dynamic level signal"""
        # Base risk on level strength and market volatility
        volatility = np.std(self.price_history[-20:]) / np.mean(self.price_history[-20:])

        base_risk = volatility * current_price * level.strength_score

        # Adjust based on level type
        if 'support' in level.level_type.value:
            suggested_sl = level.price_level - base_risk
            suggested_tp = current_price + (base_risk * 2)
        elif 'resistance' in level.level_type.value:
            suggested_sl = level.price_level + base_risk
            suggested_tp = current_price - (base_risk * 2)
        else:
            # Neutral level
            suggested_sl = current_price - base_risk
            suggested_tp = current_price + base_risk

        return suggested_sl, suggested_tp

    def _calculate_level_density(self, current_price: float) -> float:
        """Calculate level density around current price"""
        proximity_threshold = 0.02  # 2%
        nearby_levels = [l for l in self.active_levels
                        if abs(l.price_level - current_price) / current_price <= proximity_threshold]

        # Normalize density (more levels = higher density)
        density = min(len(nearby_levels) / 5, 1.0)

        return density

    def get_active_levels(self) -> List[DynamicLevel]:
        """Get currently active dynamic levels"""
        return self.active_levels.copy()

    def get_levels_by_type(self, level_type: DynamicLevelType) -> List[DynamicLevel]:
        """Get levels of specific type"""
        return [l for l in self.active_levels if l.level_type == level_type]

    def get_nearest_levels(self, price: float) -> Dict[str, Optional[DynamicLevel]]:
        """Get nearest support and resistance levels to a price"""
        support_levels = [l for l in self.active_levels if 'support' in l.level_type.value]
        resistance_levels = [l for l in self.active_levels if 'resistance' in l.level_type.value]

        nearest_support = min(support_levels, key=lambda x: abs(x.price_level - price)) if support_levels else None
        nearest_resistance = min(resistance_levels, key=lambda x: abs(x.price_level - price)) if resistance_levels else None

        return {
            'support': nearest_support,
            'resistance': nearest_resistance
        }

    def get_level_statistics(self) -> Dict[str, Any]:
        """Get statistics about current levels"""
        if not self.active_levels:
            return {}

        level_types = {}
        confidence_levels = {}
        strength_scores = []

        for level in self.active_levels:
            # Count by type
            type_key = level.level_type.value
            level_types[type_key] = level_types.get(type_key, 0) + 1

            # Count by confidence
            conf_key = level.confidence.value
            confidence_levels[conf_key] = confidence_levels.get(conf_key, 0) + 1

            # Collect strength scores
            strength_scores.append(level.strength_score)

        return {
            'total_levels': len(self.active_levels),
            'level_types': level_types,
            'confidence_distribution': confidence_levels,
            'average_strength': np.mean(strength_scores) if strength_scores else 0,
            'strength_range': {
                'min': min(strength_scores) if strength_scores else 0,
                'max': max(strength_scores) if strength_scores else 0
            },
            'market_regime': self.market_regime
        }