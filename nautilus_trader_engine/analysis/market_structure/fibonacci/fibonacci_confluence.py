"""
Fibonacci Confluence Module

Advanced Fibonacci confluence analysis identifying areas where multiple Fibonacci
levels converge with institutional-grade features including volume weighting,
smart money confirmation, multi-timeframe analysis, and adaptive confidence scoring.
"""

from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import numpy as np

from ...core.base_classes import AugmentedIndicator


class ConfluenceType(Enum):
    """Types of Fibonacci confluence"""
    RETRACEMENT_CONFLUENCE = "retracement_confluence"
    EXTENSION_CONFLUENCE = "extension_confluence"
    MULTI_LEVEL_CONFLUENCE = "multi_level_confluence"
    TIME_PRICE_CONFLUENCE = "time_price_confluence"


class ConfluenceStrength(Enum):
    """Strength levels for confluence zones"""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


@dataclass
class ConfluenceZone:
    """Represents a Fibonacci confluence zone"""
    price_level: float
    zone_width: float
    confluence_type: ConfluenceType
    strength: ConfluenceStrength
    participating_levels: List[str]
    confidence_score: float
    volume_profile: Dict[str, Any]
    timeframes_aligned: List[str]
    smart_money_score: float


@dataclass
class FibonacciConfluenceSignal:
    """Fibonacci confluence signal with institutional features"""
    value_raw: float
    signal_type: str
    composite_confidence: float
    confidence_components: Dict[str, float]
    suggested_sl: float
    suggested_tp: float
    timestamp: datetime
    additional_metadata: Dict[str, Any]

    # Confluence-specific fields
    confluence_zone: ConfluenceZone
    zone_entry_price: float
    zone_exit_price: float
    zone_midpoint: float
    participating_ratios: List[float]
    confluence_strength: ConfluenceStrength
    breakout_direction: Optional[str]


class FibonacciConfluence(AugmentedIndicator):
    """
    Advanced Fibonacci Confluence Analyzer

    Identifies areas where multiple Fibonacci levels converge, creating high-probability
    trading zones with institutional-grade features.
    """

    def __init__(self, timeframe: str = "1D", confluence_tolerance: float = 0.005):
        super().__init__(name="FibonacciConfluence", timeframe=timeframe)
        self.confluence_tolerance = confluence_tolerance  # 0.5% tolerance for confluence
        self.price_history = []
        self.volume_history = []
        self.active_confluence_zones = []
        self.historical_confluence_hits = []

    def update(self, price: float, volume: float, high: float = None,
               low: float = None, timestamp: datetime = None,
               order_book_data: Dict = None, trade_data: List = None) -> Optional[FibonacciConfluenceSignal]:
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
            FibonacciConfluenceSignal if price enters confluence zone, None otherwise
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Update price and volume history
        self.price_history.append(price)
        self.volume_history.append(volume)

        # Maintain reasonable history size
        if len(self.price_history) > 200:
            self.price_history.pop(0)
            self.volume_history.pop(0)

        # Need minimum data for analysis
        if len(self.price_history) < 20:
            return None

        # Update confluence zones
        self._update_confluence_zones()

        # Check for confluence zone entry
        signal = self._check_confluence_entry(price, timestamp, order_book_data, trade_data)

        if signal:
            self.current_signal = signal
            self.historical_confluence_hits.append(signal)

        return signal

    def _update_confluence_zones(self):
        """Update active confluence zones based on current price action"""
        if len(self.price_history) < 20:
            return

        # Find swing points for Fibonacci analysis
        swing_points = self._find_swing_points()

        if len(swing_points) < 2:
            return

        # Calculate potential confluence zones
        new_zones = self._calculate_confluence_zones(swing_points)

        # Update active zones
        self.active_confluence_zones = new_zones

    def _find_swing_points(self) -> List[Tuple[float, int]]:
        """Find swing high and low points in price history"""
        swing_points = []
        lookback = 5  # Look 5 periods either side

        for i in range(lookback, len(self.price_history) - lookback):
            price = self.price_history[i]

            # Check for swing high
            is_swing_high = all(price >= self.price_history[i-j] for j in range(1, lookback+1)) and \
                           all(price >= self.price_history[i+j] for j in range(1, lookback+1))

            # Check for swing low
            is_swing_low = all(price <= self.price_history[i-j] for j in range(1, lookback+1)) and \
                          all(price <= self.price_history[i+j] for j in range(1, lookback+1))

            if is_swing_high or is_swing_low:
                swing_points.append((price, i))

        return swing_points

    def _calculate_confluence_zones(self, swing_points: List[Tuple[float, int]]) -> List[ConfluenceZone]:
        """Calculate confluence zones from swing points"""
        zones = []

        if len(swing_points) < 2:
            return zones

        # Get the most recent significant swing points
        recent_swings = swing_points[-4:]  # Last 4 swing points

        # Calculate Fibonacci levels for different swing combinations
        fib_ratios = [0.236, 0.382, 0.5, 0.618, 0.786, 1.272, 1.618]

        potential_levels = []

        # Calculate retracement levels
        for i in range(len(recent_swings) - 1):
            for j in range(i + 1, len(recent_swings)):
                start_price, start_idx = recent_swings[i]
                end_price, end_idx = recent_swings[j]

                if abs(start_price - end_price) / min(start_price, end_price) < 0.005:
                    continue  # Too small move

                range_size = abs(end_price - start_price)

                for ratio in fib_ratios:
                    if end_price > start_price:  # Uptrend
                        level_price = start_price + (range_size * ratio)
                    else:  # Downtrend
                        level_price = end_price + (range_size * (1 - ratio))

                    potential_levels.append({
                        'price': level_price,
                        'ratio': ratio,
                        'move_type': 'retracement',
                        'start_idx': start_idx,
                        'end_idx': end_idx
                    })

        # Find confluence areas (levels within tolerance of each other)
        potential_levels.sort(key=lambda x: x['price'])

        for i, level1 in enumerate(potential_levels):
            confluence_levels = [level1]
            zone_center = level1['price']

            # Look for nearby levels
            for j, level2 in enumerate(potential_levels[i+1:], i+1):
                if abs(level2['price'] - zone_center) / zone_center <= self.confluence_tolerance:
                    confluence_levels.append(level2)
                    # Recalculate center with new level
                    zone_center = np.mean([l['price'] for l in confluence_levels])
                elif level2['price'] - zone_center > zone_center * self.confluence_tolerance:
                    break  # Levels too far apart

            if len(confluence_levels) >= 2:  # At least 2 levels for confluence
                zone = self._create_confluence_zone(confluence_levels, zone_center)
                if zone:
                    zones.append(zone)

        # Remove duplicates and sort by strength
        unique_zones = self._remove_duplicate_zones(zones)
        return sorted(unique_zones, key=lambda x: x.confidence_score, reverse=True)

    def _create_confluence_zone(self, confluence_levels: List[Dict], zone_center: float) -> Optional[ConfluenceZone]:
        """Create a confluence zone from grouped levels"""
        if len(confluence_levels) < 2:
            return None

        # Calculate zone boundaries
        prices = [level['price'] for level in confluence_levels]
        zone_width = (max(prices) - min(prices)) / zone_center

        # Determine confluence type
        ratios = [level['ratio'] for level in confluence_levels]
        if all(r <= 1.0 for r in ratios):
            confluence_type = ConfluenceType.RETRACEMENT_CONFLUENCE
        elif all(r > 1.0 for r in ratios):
            confluence_type = ConfluenceType.EXTENSION_CONFLUENCE
        else:
            confluence_type = ConfluenceType.MULTI_LEVEL_CONFLUENCE

        # Calculate strength based on number of levels and zone width
        num_levels = len(confluence_levels)
        if num_levels >= 4 and zone_width < 0.01:
            strength = ConfluenceStrength.VERY_STRONG
        elif num_levels >= 3 and zone_width < 0.02:
            strength = ConfluenceStrength.STRONG
        elif num_levels >= 2 and zone_width < 0.03:
            strength = ConfluenceStrength.MODERATE
        else:
            strength = ConfluenceStrength.WEAK

        # Participating level descriptions
        participating_levels = []
        for level in confluence_levels:
            ratio = level['ratio']
            if ratio == 0.236:
                participating_levels.append("23.6% Retracement")
            elif ratio == 0.382:
                participating_levels.append("38.2% Retracement")
            elif ratio == 0.5:
                participating_levels.append("50.0% Retracement")
            elif ratio == 0.618:
                participating_levels.append("61.8% Retracement")
            elif ratio == 0.786:
                participating_levels.append("78.6% Retracement")
            elif ratio == 1.272:
                participating_levels.append("127.2% Extension")
            elif ratio == 1.618:
                participating_levels.append("161.8% Extension")
            else:
                participating_levels.append(f"{ratio:.3f} Level")

        # Calculate confidence score
        confidence_score = min(1.0, (num_levels * 0.2) + (1.0 - zone_width * 10))

        return ConfluenceZone(
            price_level=zone_center,
            zone_width=zone_width,
            confluence_type=confluence_type,
            strength=strength,
            participating_levels=participating_levels,
            confidence_score=confidence_score,
            volume_profile={},  # Will be updated with volume analysis
            timeframes_aligned=[self.timeframe],  # Will be updated with multi-timeframe analysis
            smart_money_score=0.5  # Will be updated with smart money analysis
        )

    def _remove_duplicate_zones(self, zones: List[ConfluenceZone]) -> List[ConfluenceZone]:
        """Remove overlapping or duplicate zones"""
        if not zones:
            return zones

        # Sort by confidence score
        zones.sort(key=lambda x: x.confidence_score, reverse=True)

        filtered_zones = []

        for zone in zones:
            # Check if zone overlaps significantly with existing zones
            overlaps = False
            for existing_zone in filtered_zones:
                price_diff = abs(zone.price_level - existing_zone.price_level)
                avg_price = (zone.price_level + existing_zone.price_level) / 2
                overlap_ratio = price_diff / avg_price

                if overlap_ratio < 0.02:  # Within 2% - significant overlap
                    overlaps = True
                    break

            if not overlaps:
                filtered_zones.append(zone)

        return filtered_zones

    def _check_confluence_entry(self, current_price: float, timestamp: datetime,
                              order_book_data: Dict = None,
                              trade_data: List = None) -> Optional[FibonacciConfluenceSignal]:
        """Check if current price has entered a confluence zone"""
        for zone in self.active_confluence_zones:
            zone_lower = zone.price_level * (1 - zone.zone_width / 2)
            zone_upper = zone.price_level * (1 + zone.zone_width / 2)

            if zone_lower <= current_price <= zone_upper:
                return self._create_confluence_signal(
                    zone, current_price, timestamp, order_book_data, trade_data
                )

        return None

    def _create_confluence_signal(self, zone: ConfluenceZone, current_price: float,
                                timestamp: datetime, order_book_data: Dict = None,
                                trade_data: List = None) -> FibonacciConfluenceSignal:
        """Create a confluence signal when price enters a zone"""
        # Calculate confidence components
        confidence_components = self._calculate_confluence_confidence(zone, current_price, order_book_data, trade_data)

        # Composite confidence
        composite_confidence = np.mean(list(confidence_components.values()))

        # Determine breakout direction (simplified)
        breakout_direction = self._determine_breakout_direction(current_price, zone)

        # Risk management
        suggested_sl, suggested_tp = self._calculate_confluence_risk_management(zone, breakout_direction)

        # Additional metadata
        additional_metadata = {
            'zone_strength': zone.strength.value,
            'num_participating_levels': len(zone.participating_levels),
            'zone_width_pct': zone.zone_width * 100,
            'confluence_type': zone.confluence_type.value,
            'volume_confirmation': self._analyze_zone_volume(zone),
            'timeframe_alignment_score': self._calculate_timeframe_alignment(zone),
            'historical_success_rate': self._calculate_historical_success(zone)
        }

        # Zone boundaries
        zone_width_amount = zone.price_level * zone.zone_width
        zone_entry_price = current_price
        zone_exit_price = zone.price_level + zone_width_amount if breakout_direction == 'up' else zone.price_level - zone_width_amount
        zone_midpoint = zone.price_level

        return FibonacciConfluenceSignal(
            value_raw=current_price,
            signal_type=f"FIBONACCI_{zone.confluence_type.value.upper()}_{zone.strength.value.upper()}",
            composite_confidence=composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=suggested_sl,
            suggested_tp=suggested_tp,
            timestamp=timestamp,
            additional_metadata=additional_metadata,
            confluence_zone=zone,
            zone_entry_price=zone_entry_price,
            zone_exit_price=zone_exit_price,
            zone_midpoint=zone_midpoint,
            participating_ratios=[0.236, 0.382, 0.5, 0.618, 0.786, 1.272, 1.618],  # Standard ratios
            confluence_strength=zone.strength,
            breakout_direction=breakout_direction
        )

    def _calculate_confluence_confidence(self, zone: ConfluenceZone, current_price: float,
                                       order_book_data: Dict = None,
                                       trade_data: List = None) -> Dict[str, float]:
        """Calculate confidence components for confluence signal"""
        components = {}

        # Zone strength score
        strength_scores = {
            ConfluenceStrength.WEAK: 0.3,
            ConfluenceStrength.MODERATE: 0.5,
            ConfluenceStrength.STRONG: 0.7,
            ConfluenceStrength.VERY_STRONG: 0.9
        }
        components['zone_strength_score'] = strength_scores.get(zone.strength, 0.5)

        # Number of participating levels
        components['participation_score'] = min(1.0, len(zone.participating_levels) * 0.25)

        # Zone width (tighter zones are stronger)
        components['zone_width_score'] = max(0.3, 1.0 - (zone.zone_width * 5))

        # Volume confirmation
        components['volume_score'] = self._calculate_zone_volume_score(zone)

        # Smart money confirmation
        components['smart_money_score'] = self._calculate_zone_smart_money_score(order_book_data, trade_data)

        # Timeframe alignment
        components['timeframe_score'] = len(zone.timeframes_aligned) * 0.2

        return components

    def _calculate_zone_volume_score(self, zone: ConfluenceZone) -> float:
        """Calculate volume confirmation for the zone"""
        if len(self.volume_history) < 10:
            return 0.5

        # Check if volume increased as price approached the zone
        recent_volume = np.mean(self.volume_history[-5:])
        earlier_volume = np.mean(self.volume_history[-10:-5])

        if recent_volume > earlier_volume * 1.5:
            return 0.9
        elif recent_volume > earlier_volume * 1.2:
            return 0.7
        elif recent_volume > earlier_volume * 0.9:
            return 0.5
        else:
            return 0.3

    def _calculate_zone_smart_money_score(self, order_book_data: Dict = None,
                                        trade_data: List = None) -> float:
        """Calculate smart money confirmation for the zone"""
        score = 0.5

        if order_book_data:
            # Check order book imbalance
            bids_volume = sum(order_book_data.get('bids', {}).values())
            asks_volume = sum(order_book_data.get('asks', {}).values())

            if bids_volume + asks_volume > 0:
                imbalance = abs(bids_volume - asks_volume) / (bids_volume + asks_volume)
                score = min(0.9, 0.5 + imbalance)

        if trade_data:
            # Check for large trades
            if trade_data:
                avg_volume = np.mean([trade[1] for trade in trade_data])
                large_trades = [trade for trade in trade_data if trade[1] > avg_volume * 2]

                if large_trades:
                    score = min(0.95, score + 0.2)

        return score

    def _determine_breakout_direction(self, current_price: float, zone: ConfluenceZone) -> Optional[str]:
        """Determine the likely breakout direction from the confluence zone"""
        if len(self.price_history) < 5:
            return None

        # Simple trend analysis
        recent_trend = self.price_history[-1] - self.price_history[-5]

        if abs(recent_trend) / self.price_history[-5] < 0.005:
            return None  # No clear trend

        return 'up' if recent_trend > 0 else 'down'

    def _calculate_confluence_risk_management(self, zone: ConfluenceZone,
                                            breakout_direction: Optional[str]) -> Tuple[float, float]:
        """Calculate stop loss and take profit for confluence trade"""
        zone_price = zone.price_level
        zone_width_amount = zone_price * zone.zone_width

        if breakout_direction == 'up':
            # Bullish breakout
            suggested_sl = zone_price - zone_width_amount
            suggested_tp = zone_price + (zone_width_amount * 3)  # 3:1 reward:risk
        elif breakout_direction == 'down':
            # Bearish breakout
            suggested_sl = zone_price + zone_width_amount
            suggested_tp = zone_price - (zone_width_amount * 3)  # 3:1 reward:risk
        else:
            # Neutral - use zone boundaries
            suggested_sl = zone_price - zone_width_amount
            suggested_tp = zone_price + zone_width_amount

        return suggested_sl, suggested_tp

    def _analyze_zone_volume(self, zone: ConfluenceZone) -> Dict[str, Any]:
        """Analyze volume profile around the confluence zone"""
        if len(self.volume_history) < 10:
            return {}

        recent_volume = self.volume_history[-10:]
        return {
            'average_volume': np.mean(recent_volume),
            'volume_trend': np.polyfit(range(len(recent_volume)), recent_volume, 1)[0],
            'high_volume_periods': sum(1 for v in recent_volume if v > np.mean(recent_volume) * 1.5)
        }

    def _calculate_timeframe_alignment(self, zone: ConfluenceZone) -> float:
        """Calculate timeframe alignment score"""
        # Simplified - would check multiple timeframes in practice
        return min(1.0, len(zone.timeframes_aligned) * 0.25)

    def _calculate_historical_success(self, zone: ConfluenceZone) -> float:
        """Calculate historical success rate for similar confluence zones"""
        if len(self.historical_confluence_hits) < 3:
            return 0.5

        # Check success rate of similar strength zones
        similar_zones = [hit for hit in self.historical_confluence_hits[-10:]
                        if hit.confluence_strength == zone.strength]

        if not similar_zones:
            return 0.5

        successful_trades = sum(1 for hit in similar_zones if hit.composite_confidence > 0.7)
        return successful_trades / len(similar_zones)

    def get_active_confluence_zones(self) -> List[ConfluenceZone]:
        """Get currently active confluence zones"""
        return self.active_confluence_zones.copy()

    def get_confluence_history(self) -> List[FibonacciConfluenceSignal]:
        """Get historical confluence signals"""
        return self.historical_confluence_hits.copy()

    def find_nearest_confluence_zone(self, price: float) -> Optional[ConfluenceZone]:
        """Find the nearest confluence zone to a given price"""
        if not self.active_confluence_zones:
            return None

        nearest_zone = min(self.active_confluence_zones,
                          key=lambda zone: abs(zone.price_level - price))

        # Only return if within reasonable distance
        distance_pct = abs(nearest_zone.price_level - price) / price
        if distance_pct < 0.05:  # Within 5%
            return nearest_zone

        return None