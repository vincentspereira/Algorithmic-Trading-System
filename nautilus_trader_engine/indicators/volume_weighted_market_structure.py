"""Volume-Weighted Market Structure Indicators

Implements various volume-weighted market structure indicators including:
- Volume-Weighted Support and Resistance Levels
- Volume-Weighted Pivot Points (Standard, Fibonacci, Camarilla)
- Volume Profile Analysis
- Market Profile Indicators
- Volume-Weighted Price Levels
- Institutional Flow Detection
- Smart Money Tracking
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple, NamedTuple
from collections import deque, defaultdict
from dataclasses import dataclass

from .base import (
    VolumeWeightedIndicator, 
    MultiValueIndicator,
    IndicatorConfig, 
    IndicatorResult, 
    IndicatorType,
    SignalType
)
import logging

logger = logging.getLogger(__name__)

@dataclass
class PriceLevel:
    """Represents a significant price level with volume data"""
    price: float
    volume: float
    touches: int
    strength: float
    level_type: str  # 'support', 'resistance', 'pivot'
    timestamp: datetime

@dataclass
class VolumeNode:
    """Volume profile node"""
    price_level: float
    volume: float
    buy_volume: float
    sell_volume: float
    trades_count: int

class VolumeWeightedSupportResistance(VolumeWeightedIndicator):
    """Volume-Weighted Support and Resistance Levels
    
    Identifies key support and resistance levels using volume-weighted
    price action analysis and institutional flow detection.
    """
    
    def __init__(self, config: IndicatorConfig, lookback_periods: int = 50, min_touches: int = 2):
        super().__init__(config, "VW_SUPPORT_RESISTANCE")
        self.indicator_type = IndicatorType.MARKET_STRUCTURE
        
        self.lookback_periods = lookback_periods
        self.min_touches = min_touches
        
        # Price level tracking
        self.price_levels: List[PriceLevel] = []
        self.high_prices = deque(maxlen=lookback_periods)
        self.low_prices = deque(maxlen=lookback_periods)
        self.close_prices = deque(maxlen=lookback_periods)
        self.volume_data = deque(maxlen=lookback_periods)
        self.timestamps = deque(maxlen=lookback_periods)
        
        # Level validation parameters
        self.price_tolerance = 0.002  # 0.2% tolerance for level matching
        self.volume_threshold_percentile = 70  # Top 30% volume for significant levels
    
    def calculate(self, price: float, volume: float, timestamp: datetime, 
                 high: float = None, low: float = None) -> Optional[IndicatorResult]:
        """Calculate Support and Resistance Levels"""
        start_time = datetime.now()
        
        # Use price as high/low if not provided
        if high is None:
            high = price
        if low is None:
            low = price
        
        self._add_data_point(price, volume, timestamp)
        
        # Store OHLC data
        self.high_prices.append(high)
        self.low_prices.append(low)
        self.close_prices.append(price)
        self.volume_data.append(volume)
        self.timestamps.append(timestamp)
        
        if len(self.close_prices) < self.lookback_periods:
            return None
        
        # Identify significant price levels
        self._identify_price_levels()
        
        # Calculate current level strength and proximity
        nearest_support, nearest_resistance = self._find_nearest_levels(price)
        
        # Generate signals based on level interaction
        signal, confidence = self._generate_level_signal(price, volume, nearest_support, nearest_resistance)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=price,
            signal=signal,
            confidence=confidence,
            metadata={
                'nearest_support': nearest_support.price if nearest_support else None,
                'nearest_resistance': nearest_resistance.price if nearest_resistance else None,
                'support_strength': nearest_support.strength if nearest_support else 0,
                'resistance_strength': nearest_resistance.strength if nearest_resistance else 0,
                'total_levels': len(self.price_levels),
                'strong_levels': len([l for l in self.price_levels if l.strength > 0.7]),
                'price_levels': [{
                    'price': level.price,
                    'type': level.level_type,
                    'strength': level.strength,
                    'touches': level.touches
                } for level in self.price_levels[-10:]]  # Last 10 levels
            }
        )
        
        self.results.append(result)
        
        # Track performance
        calc_time = (datetime.now() - start_time).total_seconds()
        self.calculation_times.append(calc_time)
        
        if not self.initialized and len(self.results) >= self.config.min_periods:
            self.initialized = True
            logger.info(f"{self.name} initialized with {len(self.results)} periods")
        
        return result
    
    def _identify_price_levels(self) -> None:
        """Identify significant support and resistance levels"""
        if len(self.close_prices) < 10:
            return
        
        # Convert to lists for easier processing
        highs = list(self.high_prices)
        lows = list(self.low_prices)
        closes = list(self.close_prices)
        volumes = list(self.volume_data)
        timestamps = list(self.timestamps)
        
        # Calculate volume threshold
        volume_threshold = np.percentile(volumes, self.volume_threshold_percentile)
        
        # Find swing highs and lows
        swing_highs = self._find_swing_points(highs, 'high')
        swing_lows = self._find_swing_points(lows, 'low')
        
        # Process swing points into levels
        new_levels = []
        
        # Process swing highs (potential resistance)
        for idx in swing_highs:
            if volumes[idx] >= volume_threshold:
                level = PriceLevel(
                    price=highs[idx],
                    volume=volumes[idx],
                    touches=1,
                    strength=self._calculate_level_strength(highs[idx], volumes[idx], 'resistance'),
                    level_type='resistance',
                    timestamp=timestamps[idx]
                )
                new_levels.append(level)
        
        # Process swing lows (potential support)
        for idx in swing_lows:
            if volumes[idx] >= volume_threshold:
                level = PriceLevel(
                    price=lows[idx],
                    volume=volumes[idx],
                    touches=1,
                    strength=self._calculate_level_strength(lows[idx], volumes[idx], 'support'),
                    level_type='support',
                    timestamp=timestamps[idx]
                )
                new_levels.append(level)
        
        # Merge with existing levels and update touches
        self._merge_and_update_levels(new_levels)
        
        # Clean up old and weak levels
        self._cleanup_levels()
    
    def _find_swing_points(self, prices: List[float], point_type: str) -> List[int]:
        """Find swing high/low points"""
        swing_points = []
        window = 3  # Look 3 periods before and after
        
        for i in range(window, len(prices) - window):
            if point_type == 'high':
                # Check if current point is higher than surrounding points
                if all(prices[i] >= prices[j] for j in range(i - window, i + window + 1) if j != i):
                    swing_points.append(i)
            else:  # 'low'
                # Check if current point is lower than surrounding points
                if all(prices[i] <= prices[j] for j in range(i - window, i + window + 1) if j != i):
                    swing_points.append(i)
        
        return swing_points
    
    def _calculate_level_strength(self, price: float, volume: float, level_type: str) -> float:
        """Calculate the strength of a price level"""
        # Base strength from volume
        max_volume = max(self.volume_data) if self.volume_data else 1
        volume_strength = volume / max_volume
        
        # Additional strength factors
        touches_strength = 0  # Will be updated when merging levels
        
        # Time-based decay (newer levels are stronger)
        time_strength = 1.0  # Assume recent for new levels
        
        # Combine factors
        strength = (volume_strength * 0.4 + touches_strength * 0.4 + time_strength * 0.2)
        
        return min(1.0, strength)
    
    def _merge_and_update_levels(self, new_levels: List[PriceLevel]) -> None:
        """Merge new levels with existing ones and update touch counts"""
        for new_level in new_levels:
            merged = False
            
            # Check if this level is close to an existing one
            for existing_level in self.price_levels:
                price_diff = abs(new_level.price - existing_level.price) / existing_level.price
                
                if (price_diff <= self.price_tolerance and 
                    new_level.level_type == existing_level.level_type):
                    
                    # Merge levels - update with volume-weighted average
                    total_volume = existing_level.volume + new_level.volume
                    existing_level.price = (
                        (existing_level.price * existing_level.volume + 
                         new_level.price * new_level.volume) / total_volume
                    )
                    existing_level.volume = total_volume
                    existing_level.touches += 1
                    existing_level.timestamp = new_level.timestamp  # Update to latest
                    
                    # Recalculate strength with updated touches
                    touches_strength = min(1.0, existing_level.touches / 5)  # Max at 5 touches
                    max_volume = max(self.volume_data) if self.volume_data else 1
                    volume_strength = existing_level.volume / (max_volume * existing_level.touches)
                    existing_level.strength = (volume_strength * 0.4 + touches_strength * 0.6)
                    
                    merged = True
                    break
            
            if not merged:
                self.price_levels.append(new_level)
    
    def _cleanup_levels(self) -> None:
        """Remove old and weak levels"""
        current_time = self.timestamps[-1] if self.timestamps else datetime.now()
        
        # Remove levels that are too old or too weak
        self.price_levels = [
            level for level in self.price_levels
            if (level.touches >= self.min_touches and 
                level.strength > 0.3 and
                (current_time - level.timestamp).days < 30)  # Keep levels for 30 days max
        ]
        
        # Keep only the strongest levels if we have too many
        if len(self.price_levels) > 20:
            self.price_levels.sort(key=lambda x: x.strength, reverse=True)
            self.price_levels = self.price_levels[:20]
    
    def _find_nearest_levels(self, current_price: float) -> Tuple[Optional[PriceLevel], Optional[PriceLevel]]:
        """Find nearest support and resistance levels"""
        support_levels = [l for l in self.price_levels if l.level_type == 'support' and l.price < current_price]
        resistance_levels = [l for l in self.price_levels if l.level_type == 'resistance' and l.price > current_price]
        
        nearest_support = max(support_levels, key=lambda x: x.price) if support_levels else None
        nearest_resistance = min(resistance_levels, key=lambda x: x.price) if resistance_levels else None
        
        return nearest_support, nearest_resistance
    
    def _generate_level_signal(self, price: float, volume: float, 
                              support: Optional[PriceLevel], 
                              resistance: Optional[PriceLevel]) -> Tuple[SignalType, float]:
        """Generate signals based on level interaction"""
        # Check proximity to levels
        if support:
            support_distance = (price - support.price) / price
            if support_distance < 0.01:  # Within 1% of support
                # Strong volume at support suggests bounce
                avg_volume = np.mean(list(self.volume_data)[-10:]) if len(self.volume_data) >= 10 else volume
                if volume > avg_volume * 1.5:
                    confidence = min(1.0, support.strength * (volume / avg_volume) * 0.5)
                    return SignalType.BUY, confidence
        
        if resistance:
            resistance_distance = (resistance.price - price) / price
            if resistance_distance < 0.01:  # Within 1% of resistance
                # Strong volume at resistance suggests rejection
                avg_volume = np.mean(list(self.volume_data)[-10:]) if len(self.volume_data) >= 10 else volume
                if volume > avg_volume * 1.5:
                    confidence = min(1.0, resistance.strength * (volume / avg_volume) * 0.5)
                    return SignalType.SELL, confidence
        
        return SignalType.NEUTRAL, 0.0

class VolumeWeightedPivotPoints(VolumeWeightedIndicator):
    """Volume-Weighted Pivot Points
    
    Calculates various pivot point types with volume weighting for
    more accurate intraday trading levels.
    """
    
    def __init__(self, config: IndicatorConfig, pivot_type: str = 'standard'):
        super().__init__(config, "VW_PIVOT_POINTS")
        self.indicator_type = IndicatorType.MARKET_STRUCTURE
        
        self.pivot_type = pivot_type.lower()  # 'standard', 'fibonacci', 'camarilla'
        
        # Daily OHLC data for pivot calculation
        self.daily_data = {}
        self.current_day = None
        
        # Pivot levels
        self.pivot_levels = {}
    
    def calculate(self, price: float, volume: float, timestamp: datetime,
                 high: float = None, low: float = None, open_price: float = None) -> Optional[IndicatorResult]:
        """Calculate Volume-Weighted Pivot Points"""
        start_time = datetime.now()
        
        # Use price as OHLC if not provided
        if high is None:
            high = price
        if low is None:
            low = price
        if open_price is None:
            open_price = price
        
        self._add_data_point(price, volume, timestamp)
        
        # Track daily data
        day_key = timestamp.date()
        
        if day_key != self.current_day:
            # New day - calculate pivot points from previous day
            if self.current_day and self.current_day in self.daily_data:
                self._calculate_pivot_points(self.current_day)
            
            # Initialize new day
            self.current_day = day_key
            self.daily_data[day_key] = {
                'open': open_price,
                'high': high,
                'low': low,
                'close': price,
                'volume': volume,
                'vwap': price * volume,
                'total_volume': volume
            }
        else:
            # Update current day data
            if day_key in self.daily_data:
                data = self.daily_data[day_key]
                data['high'] = max(data['high'], high)
                data['low'] = min(data['low'], low)
                data['close'] = price
                data['volume'] = max(data['volume'], volume)  # Peak volume
                data['vwap'] += price * volume
                data['total_volume'] += volume
        
        # Generate signals based on current pivot levels
        signal, confidence = self._generate_pivot_signal(price, volume)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=self.pivot_levels.get('PP', price),
            signal=signal,
            confidence=confidence,
            metadata={
                'pivot_points': self.pivot_levels.copy(),
                'pivot_type': self.pivot_type,
                'current_day': str(day_key),
                'price_vs_pivot': (price - self.pivot_levels.get('PP', price)) / self.pivot_levels.get('PP', price) * 100 if self.pivot_levels.get('PP') else 0
            }
        )
        
        self.results.append(result)
        
        # Track performance
        calc_time = (datetime.now() - start_time).total_seconds()
        self.calculation_times.append(calc_time)
        
        if not self.initialized and len(self.results) >= self.config.min_periods:
            self.initialized = True
            logger.info(f"{self.name} initialized with {len(self.results)} periods")
        
        return result
    
    def _calculate_pivot_points(self, day_key) -> None:
        """Calculate pivot points for the given day"""
        data = self.daily_data[day_key]
        
        # Calculate volume-weighted average price for the day
        if data['total_volume'] > 0:
            vwap = data['vwap'] / data['total_volume']
        else:
            vwap = (data['high'] + data['low'] + data['close']) / 3
        
        # Use VWAP instead of simple average for more accurate pivots
        if self.config.volume_weighted:
            pivot_base = vwap
        else:
            pivot_base = (data['high'] + data['low'] + data['close']) / 3
        
        high = data['high']
        low = data['low']
        close = data['close']
        
        if self.pivot_type == 'standard':
            self.pivot_levels = self._calculate_standard_pivots(pivot_base, high, low)
        elif self.pivot_type == 'fibonacci':
            self.pivot_levels = self._calculate_fibonacci_pivots(pivot_base, high, low)
        elif self.pivot_type == 'camarilla':
            self.pivot_levels = self._calculate_camarilla_pivots(high, low, close)
        
        logger.debug(f"Calculated {self.pivot_type} pivot points for {day_key}: {self.pivot_levels}")
    
    def _calculate_standard_pivots(self, pivot: float, high: float, low: float) -> Dict[str, float]:
        """Calculate standard pivot points"""
        return {
            'PP': pivot,
            'R1': 2 * pivot - low,
            'R2': pivot + (high - low),
            'R3': high + 2 * (pivot - low),
            'S1': 2 * pivot - high,
            'S2': pivot - (high - low),
            'S3': low - 2 * (high - pivot)
        }
    
    def _calculate_fibonacci_pivots(self, pivot: float, high: float, low: float) -> Dict[str, float]:
        """Calculate Fibonacci pivot points"""
        range_hl = high - low
        return {
            'PP': pivot,
            'R1': pivot + 0.382 * range_hl,
            'R2': pivot + 0.618 * range_hl,
            'R3': pivot + range_hl,
            'S1': pivot - 0.382 * range_hl,
            'S2': pivot - 0.618 * range_hl,
            'S3': pivot - range_hl
        }
    
    def _calculate_camarilla_pivots(self, high: float, low: float, close: float) -> Dict[str, float]:
        """Calculate Camarilla pivot points"""
        range_hl = high - low
        return {
            'PP': close,
            'R1': close + range_hl * 1.1 / 12,
            'R2': close + range_hl * 1.1 / 6,
            'R3': close + range_hl * 1.1 / 4,
            'R4': close + range_hl * 1.1 / 2,
            'S1': close - range_hl * 1.1 / 12,
            'S2': close - range_hl * 1.1 / 6,
            'S3': close - range_hl * 1.1 / 4,
            'S4': close - range_hl * 1.1 / 2
        }
    
    def _generate_pivot_signal(self, price: float, volume: float) -> Tuple[SignalType, float]:
        """Generate signals based on pivot level interaction"""
        if not self.pivot_levels:
            return SignalType.NEUTRAL, 0.0
        
        # Check proximity to pivot levels
        tolerance = 0.001  # 0.1% tolerance
        
        # Support levels (S1, S2, S3)
        for level_name in ['S1', 'S2', 'S3']:
            if level_name in self.pivot_levels:
                level_price = self.pivot_levels[level_name]
                if abs(price - level_price) / level_price < tolerance:
                    # Near support - potential bounce
                    strength = 0.8 if level_name == 'S1' else 0.6 if level_name == 'S2' else 0.4
                    return SignalType.BUY, strength
        
        # Resistance levels (R1, R2, R3)
        for level_name in ['R1', 'R2', 'R3']:
            if level_name in self.pivot_levels:
                level_price = self.pivot_levels[level_name]
                if abs(price - level_price) / level_price < tolerance:
                    # Near resistance - potential rejection
                    strength = 0.8 if level_name == 'R1' else 0.6 if level_name == 'R2' else 0.4
                    return SignalType.SELL, strength
        
        # Pivot point crossover
        if 'PP' in self.pivot_levels:
            pp = self.pivot_levels['PP']
            if len(self.results) >= 2:
                prev_price = self.results[-2].metadata.get('price_vs_pivot', 0)
                current_vs_pivot = (price - pp) / pp * 100
                
                # Bullish crossover above pivot
                if prev_price <= 0 and current_vs_pivot > 0:
                    return SignalType.BUY, 0.5
                # Bearish crossover below pivot
                elif prev_price >= 0 and current_vs_pivot < 0:
                    return SignalType.SELL, 0.5
        
        return SignalType.NEUTRAL, 0.0

class VolumeProfile(VolumeWeightedIndicator):
    """Volume Profile Analysis
    
    Analyzes volume distribution across price levels to identify
    high-volume nodes, value areas, and point of control.
    """
    
    def __init__(self, config: IndicatorConfig, price_bins: int = 50):
        super().__init__(config, "VOLUME_PROFILE")
        self.indicator_type = IndicatorType.MARKET_STRUCTURE
        
        self.price_bins = price_bins
        self.volume_nodes: Dict[float, VolumeNode] = {}
        
        # Profile analysis parameters
        self.value_area_percentage = 0.70  # 70% of volume for value area
        
        # Price range tracking
        self.session_high = None
        self.session_low = None
    
    def calculate(self, price: float, volume: float, timestamp: datetime,
                 is_buy: bool = None) -> Optional[IndicatorResult]:
        """Calculate Volume Profile"""
        start_time = datetime.now()
        
        self._add_data_point(price, volume, timestamp)
        
        # Update session range
        if self.session_high is None or price > self.session_high:
            self.session_high = price
        if self.session_low is None or price < self.session_low:
            self.session_low = price
        
        # Determine price bin
        price_bin = self._get_price_bin(price)
        
        # Update volume node
        if price_bin not in self.volume_nodes:
            self.volume_nodes[price_bin] = VolumeNode(
                price_level=price_bin,
                volume=0,
                buy_volume=0,
                sell_volume=0,
                trades_count=0
            )
        
        node = self.volume_nodes[price_bin]
        node.volume += volume
        node.trades_count += 1
        
        # Update buy/sell volume if direction is known
        if is_buy is not None:
            if is_buy:
                node.buy_volume += volume
            else:
                node.sell_volume += volume
        else:
            # Estimate based on price movement
            if len(self.prices) >= 2:
                if price > self.prices[-2]:
                    node.buy_volume += volume * 0.6
                    node.sell_volume += volume * 0.4
                else:
                    node.buy_volume += volume * 0.4
                    node.sell_volume += volume * 0.6
            else:
                node.buy_volume += volume * 0.5
                node.sell_volume += volume * 0.5
        
        # Calculate profile metrics
        poc_price, value_area_high, value_area_low = self._calculate_profile_metrics()
        
        # Generate signals
        signal, confidence = self._generate_profile_signal(price, volume, poc_price, value_area_high, value_area_low)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=poc_price,
            signal=signal,
            confidence=confidence,
            metadata={
                'poc_price': poc_price,
                'value_area_high': value_area_high,
                'value_area_low': value_area_low,
                'session_high': self.session_high,
                'session_low': self.session_low,
                'total_volume': sum(node.volume for node in self.volume_nodes.values()),
                'price_in_value_area': value_area_low <= price <= value_area_high if value_area_low and value_area_high else False,
                'distance_from_poc': abs(price - poc_price) / price * 100 if poc_price else 0
            }
        )
        
        self.results.append(result)
        
        # Track performance
        calc_time = (datetime.now() - start_time).total_seconds()
        self.calculation_times.append(calc_time)
        
        if not self.initialized and len(self.results) >= self.config.min_periods:
            self.initialized = True
            logger.info(f"{self.name} initialized with {len(self.results)} periods")
        
        return result
    
    def _get_price_bin(self, price: float) -> float:
        """Get the price bin for volume aggregation"""
        if self.session_high is None or self.session_low is None:
            return price
        
        # Calculate bin size
        price_range = self.session_high - self.session_low
        if price_range == 0:
            return price
        
        bin_size = price_range / self.price_bins
        
        # Find the bin center
        bin_index = int((price - self.session_low) / bin_size)
        bin_center = self.session_low + (bin_index + 0.5) * bin_size
        
        return round(bin_center, 6)  # Round to avoid floating point issues
    
    def _calculate_profile_metrics(self) -> Tuple[float, float, float]:
        """Calculate Point of Control and Value Area"""
        if not self.volume_nodes:
            return 0.0, 0.0, 0.0
        
        # Find Point of Control (highest volume node)
        poc_node = max(self.volume_nodes.values(), key=lambda x: x.volume)
        poc_price = poc_node.price_level
        
        # Calculate Value Area (70% of volume)
        total_volume = sum(node.volume for node in self.volume_nodes.values())
        target_volume = total_volume * self.value_area_percentage
        
        # Sort nodes by volume (descending)
        sorted_nodes = sorted(self.volume_nodes.values(), key=lambda x: x.volume, reverse=True)
        
        # Find value area by including highest volume nodes
        value_area_volume = 0
        value_area_nodes = []
        
        for node in sorted_nodes:
            value_area_nodes.append(node)
            value_area_volume += node.volume
            
            if value_area_volume >= target_volume:
                break
        
        # Calculate value area bounds
        if value_area_nodes:
            value_area_prices = [node.price_level for node in value_area_nodes]
            value_area_high = max(value_area_prices)
            value_area_low = min(value_area_prices)
        else:
            value_area_high = poc_price
            value_area_low = poc_price
        
        return poc_price, value_area_high, value_area_low
    
    def _generate_profile_signal(self, price: float, volume: float, 
                               poc_price: float, va_high: float, va_low: float) -> Tuple[SignalType, float]:
        """Generate signals based on volume profile analysis"""
        if not poc_price:
            return SignalType.NEUTRAL, 0.0
        
        # Distance from POC
        poc_distance = abs(price - poc_price) / price
        
        # Value area analysis
        in_value_area = va_low <= price <= va_high if va_low and va_high else False
        
        # High volume at POC suggests strong support/resistance
        if poc_distance < 0.005:  # Within 0.5% of POC
            poc_node = self.volume_nodes.get(self._get_price_bin(poc_price))
            if poc_node:
                avg_volume = sum(node.volume for node in self.volume_nodes.values()) / len(self.volume_nodes)
                if poc_node.volume > avg_volume * 2:  # High volume node
                    # Direction based on buy/sell imbalance
                    if poc_node.buy_volume > poc_node.sell_volume * 1.2:
                        return SignalType.BUY, 0.7
                    elif poc_node.sell_volume > poc_node.buy_volume * 1.2:
                        return SignalType.SELL, 0.7
        
        # Value area breakout/breakdown
        if not in_value_area:
            if price > va_high:
                return SignalType.BUY, 0.5  # Breakout above value area
            elif price < va_low:
                return SignalType.SELL, 0.5  # Breakdown below value area
        
        # Mean reversion within value area
        if in_value_area:
            va_center = (va_high + va_low) / 2
            if price < va_center:
                return SignalType.BUY, 0.3  # Below center, expect reversion up
            elif price > va_center:
                return SignalType.SELL, 0.3  # Above center, expect reversion down
        
        return SignalType.NEUTRAL, 0.0

# Factory function for creating market structure indicators
def create_market_structure_indicator(indicator_type: str, config: IndicatorConfig, **kwargs) -> VolumeWeightedIndicator:
    """Factory function to create market structure indicators"""
    indicators = {
        'vw_support_resistance': lambda cfg: VolumeWeightedSupportResistance(cfg, **kwargs),
        'vw_pivot_points': lambda cfg: VolumeWeightedPivotPoints(cfg, **kwargs),
        'volume_profile': lambda cfg: VolumeProfile(cfg, **kwargs)
    }
    
    indicator_factory = indicators.get(indicator_type.lower())
    if not indicator_factory:
        raise ValueError(f"Unknown market structure indicator type: {indicator_type}")
    
    return indicator_factory(config)