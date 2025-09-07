"""Enhanced Market Structure Indicators

This module provides sophisticated market structure indicators that incorporate
volume analysis, institutional flow detection, and advanced support/resistance identification.
Builds upon the enhanced base classes for improved performance and reliability.
"""

from typing import Dict, List, Optional, Tuple, Any, NamedTuple
from datetime import datetime, timedelta
import numpy as np
from collections import deque
from dataclasses import dataclass
from enum import Enum

from .enhanced_base import (
    EnhancedVolumeWeightedIndicator,
    IndicatorResult,
    SignalType,
    IndicatorConfig,
    IndicatorType
)
from ..utils.logging_config import logger

class LevelType(Enum):
    """Types of support/resistance levels"""
    SUPPORT = "support"
    RESISTANCE = "resistance"
    PIVOT = "pivot"

@dataclass
class PriceLevel:
    """Represents a support or resistance level"""
    price: float
    level_type: LevelType
    strength: float
    volume: float
    touches: int
    first_touch: datetime
    last_touch: datetime
    institutional_interest: float = 0.0
    
    def update_touch(self, timestamp: datetime, volume: float, institutional_flow: float = 0.0):
        """Update level with new touch"""
        self.touches += 1
        self.last_touch = timestamp
        self.volume += volume
        self.institutional_interest += institutional_flow
        
        # Recalculate strength
        time_factor = max(0.1, 1.0 - (timestamp - self.first_touch).days / 365)
        self.strength = (self.touches * 0.4 + 
                        min(self.volume / 1000000, 10) * 0.3 + 
                        abs(self.institutional_interest) * 0.3) * time_factor

@dataclass
class VolumeNode:
    """Represents a volume concentration at a price level"""
    price: float
    volume: float
    transactions: int
    avg_trade_size: float
    institutional_percentage: float = 0.0
    
class EnhancedSupportResistance(EnhancedVolumeWeightedIndicator):
    """Enhanced Support and Resistance Level Detection
    
    Identifies support and resistance levels using volume-weighted price action
    and institutional flow analysis.
    """
    
    def __init__(self, config: IndicatorConfig, lookback_period: int = 50, 
                 min_touches: int = 2, strength_threshold: float = 0.5):
        super().__init__(config, "ENHANCED_SUPPORT_RESISTANCE")
        self.indicator_type = IndicatorType.MARKET_STRUCTURE
        
        self.lookback_period = lookback_period
        self.min_touches = min_touches
        self.strength_threshold = strength_threshold
        
        # Price and volume tracking
        self.highs = deque(maxlen=lookback_period)
        self.lows = deque(maxlen=lookback_period)
        self.closes = deque(maxlen=lookback_period)
        self.volumes_window = deque(maxlen=lookback_period)
        self.timestamps = deque(maxlen=lookback_period)
        
        # Support and resistance levels
        self.levels: List[PriceLevel] = []
        
        # Institutional flow tracking
        self.institutional_flows = deque(maxlen=lookback_period)
        self.large_volume_threshold = 0.0
        
        # Swing point detection
        self.swing_highs = deque(maxlen=20)
        self.swing_lows = deque(maxlen=20)
        
    def calculate_values(self, price: float, volume: float, timestamp: datetime,
                        high: float = None, low: float = None) -> Dict[str, Any]:
        """Calculate enhanced support/resistance levels"""
        if high is None:
            high = price
        if low is None:
            low = price
        
        self.highs.append(high)
        self.lows.append(low)
        self.closes.append(price)
        self.volumes_window.append(volume)
        self.timestamps.append(timestamp)
        
        # Detect institutional flow
        institutional_flow = self._detect_institutional_flow(volume, price)
        self.institutional_flows.append(institutional_flow)
        
        if len(self.closes) < 10:
            return {
                'support_levels': [],
                'resistance_levels': [],
                'nearest_support': None,
                'nearest_resistance': None,
                'level_strength': 0.0
            }
        
        # Find swing points
        self._find_swing_points()
        
        # Update existing levels and find new ones
        self._update_levels(price, volume, timestamp, institutional_flow)
        
        # Clean up old/weak levels
        self._cleanup_levels(timestamp)
        
        # Find nearest levels
        nearest_support, nearest_resistance = self._find_nearest_levels(price)
        
        # Calculate overall level strength
        level_strength = self._calculate_overall_strength(price)
        
        # Separate levels by type
        support_levels = [level for level in self.levels if level.level_type == LevelType.SUPPORT]
        resistance_levels = [level for level in self.levels if level.level_type == LevelType.RESISTANCE]
        
        return {
            'support_levels': [{'price': l.price, 'strength': l.strength, 'touches': l.touches} for l in support_levels],
            'resistance_levels': [{'price': l.price, 'strength': l.strength, 'touches': l.touches} for l in resistance_levels],
            'nearest_support': {'price': nearest_support.price, 'strength': nearest_support.strength} if nearest_support else None,
            'nearest_resistance': {'price': nearest_resistance.price, 'strength': nearest_resistance.strength} if nearest_resistance else None,
            'level_strength': level_strength,
            'institutional_flow': institutional_flow,
            'total_levels': len(self.levels)
        }
    
    def _detect_institutional_flow(self, volume: float, price: float) -> float:
        """Detect institutional money flow"""
        if len(self.volumes) < 20:
            return 0.0
        
        # Update volume threshold
        recent_volumes = list(self.volumes)[-20:]
        self.large_volume_threshold = np.percentile(recent_volumes, 90)
        
        if volume > self.large_volume_threshold:
            # Determine flow direction
            if len(self.prices) >= 2:
                price_direction = 1 if price > self.prices[-1] else -1
                volume_strength = min(volume / self.large_volume_threshold, 3.0)
                return price_direction * volume_strength * 0.1
        
        return 0.0
    
    def _find_swing_points(self):
        """Find swing highs and lows"""
        if len(self.highs) < 5:
            return
        
        # Look for swing highs (local maxima)
        for i in range(2, len(self.highs) - 2):
            if (self.highs[i] > self.highs[i-1] and self.highs[i] > self.highs[i-2] and
                self.highs[i] > self.highs[i+1] and self.highs[i] > self.highs[i+2]):
                
                swing_high = {
                    'price': self.highs[i],
                    'timestamp': self.timestamps[i],
                    'volume': self.volumes_window[i],
                    'institutional_flow': self.institutional_flows[i] if len(self.institutional_flows) > i else 0
                }
                
                # Avoid duplicates
                if not any(abs(sh['price'] - swing_high['price']) < swing_high['price'] * 0.001 for sh in self.swing_highs):
                    self.swing_highs.append(swing_high)
        
        # Look for swing lows (local minima)
        for i in range(2, len(self.lows) - 2):
            if (self.lows[i] < self.lows[i-1] and self.lows[i] < self.lows[i-2] and
                self.lows[i] < self.lows[i+1] and self.lows[i] < self.lows[i+2]):
                
                swing_low = {
                    'price': self.lows[i],
                    'timestamp': self.timestamps[i],
                    'volume': self.volumes_window[i],
                    'institutional_flow': self.institutional_flows[i] if len(self.institutional_flows) > i else 0
                }
                
                # Avoid duplicates
                if not any(abs(sl['price'] - swing_low['price']) < swing_low['price'] * 0.001 for sl in self.swing_lows):
                    self.swing_lows.append(swing_low)
    
    def _update_levels(self, current_price: float, volume: float, timestamp: datetime, institutional_flow: float):
        """Update existing levels and create new ones"""
        tolerance = current_price * 0.002  # 0.2% tolerance
        
        # Check for touches of existing levels
        for level in self.levels:
            if abs(current_price - level.price) <= tolerance:
                level.update_touch(timestamp, volume, institutional_flow)
        
        # Create new levels from swing points
        for swing_high in self.swing_highs:
            if not any(abs(level.price - swing_high['price']) <= tolerance for level in self.levels):
                new_level = PriceLevel(
                    price=swing_high['price'],
                    level_type=LevelType.RESISTANCE,
                    strength=1.0,
                    volume=swing_high['volume'],
                    touches=1,
                    first_touch=swing_high['timestamp'],
                    last_touch=swing_high['timestamp'],
                    institutional_interest=swing_high['institutional_flow']
                )
                self.levels.append(new_level)
        
        for swing_low in self.swing_lows:
            if not any(abs(level.price - swing_low['price']) <= tolerance for level in self.levels):
                new_level = PriceLevel(
                    price=swing_low['price'],
                    level_type=LevelType.SUPPORT,
                    strength=1.0,
                    volume=swing_low['volume'],
                    touches=1,
                    first_touch=swing_low['timestamp'],
                    last_touch=swing_low['timestamp'],
                    institutional_interest=swing_low['institutional_flow']
                )
                self.levels.append(new_level)
    
    def _cleanup_levels(self, current_timestamp: datetime):
        """Remove old or weak levels"""
        # Remove levels that are too old or too weak
        self.levels = [
            level for level in self.levels
            if (level.strength >= self.strength_threshold and
                level.touches >= self.min_touches and
                (current_timestamp - level.last_touch).days <= 30)
        ]
        
        # Merge nearby levels
        merged_levels = []
        for level in sorted(self.levels, key=lambda x: x.price):
            merged = False
            for existing in merged_levels:
                if abs(level.price - existing.price) <= level.price * 0.005:  # 0.5% tolerance for merging
                    # Merge levels - keep the stronger one
                    if level.strength > existing.strength:
                        merged_levels.remove(existing)
                        merged_levels.append(level)
                    merged = True
                    break
            
            if not merged:
                merged_levels.append(level)
        
        self.levels = merged_levels
    
    def _find_nearest_levels(self, price: float) -> Tuple[Optional[PriceLevel], Optional[PriceLevel]]:
        """Find nearest support and resistance levels"""
        support_levels = [l for l in self.levels if l.level_type == LevelType.SUPPORT and l.price < price]
        resistance_levels = [l for l in self.levels if l.level_type == LevelType.RESISTANCE and l.price > price]
        
        nearest_support = max(support_levels, key=lambda x: x.price) if support_levels else None
        nearest_resistance = min(resistance_levels, key=lambda x: x.price) if resistance_levels else None
        
        return nearest_support, nearest_resistance
    
    def _calculate_overall_strength(self, price: float) -> float:
        """Calculate overall strength of nearby levels"""
        if not self.levels:
            return 0.0
        
        # Find levels within 5% of current price
        nearby_levels = [
            level for level in self.levels
            if abs(level.price - price) / price <= 0.05
        ]
        
        if not nearby_levels:
            return 0.0
        
        # Weight by distance and strength
        total_strength = 0.0
        total_weight = 0.0
        
        for level in nearby_levels:
            distance_factor = 1.0 - (abs(level.price - price) / price) / 0.05
            weight = distance_factor * level.strength
            total_strength += weight
            total_weight += distance_factor
        
        return total_strength / total_weight if total_weight > 0 else 0.0
    
    def generate_signal(self, values: Dict[str, Any], price: float, volume: float) -> Tuple[SignalType, float]:
        """Generate signals based on support/resistance analysis"""
        nearest_support = values.get('nearest_support')
        nearest_resistance = values.get('nearest_resistance')
        level_strength = values.get('level_strength', 0)
        institutional_flow = values.get('institutional_flow', 0)
        
        # Support bounce signal
        if nearest_support and abs(price - nearest_support['price']) / price < 0.01:
            if institutional_flow > 0 and nearest_support['strength'] > 0.7:
                confidence = min(nearest_support['strength'] + institutional_flow, 0.9)
                return SignalType.BUY, confidence
        
        # Resistance rejection signal
        elif nearest_resistance and abs(price - nearest_resistance['price']) / price < 0.01:
            if institutional_flow < 0 and nearest_resistance['strength'] > 0.7:
                confidence = min(nearest_resistance['strength'] + abs(institutional_flow), 0.9)
                return SignalType.SELL, confidence
        
        # Breakout signals
        elif nearest_resistance and price > nearest_resistance['price'] * 1.002:  # 0.2% above resistance
            if institutional_flow > 0.1 and volume > np.mean(list(self.volumes)[-10:]) * 1.5:
                confidence = min(level_strength + institutional_flow, 0.8)
                return SignalType.BUY, confidence
        
        elif nearest_support and price < nearest_support['price'] * 0.998:  # 0.2% below support
            if institutional_flow < -0.1 and volume > np.mean(list(self.volumes)[-10:]) * 1.5:
                confidence = min(level_strength + abs(institutional_flow), 0.8)
                return SignalType.SELL, confidence
        
        return SignalType.NEUTRAL, 0.0

class EnhancedVolumeProfile(EnhancedVolumeWeightedIndicator):
    """Enhanced Volume Profile Analysis
    
    Analyzes volume distribution across price levels with institutional flow detection.
    """
    
    def __init__(self, config: IndicatorConfig, session_length: int = 390, 
                 num_bins: int = 50, value_area_percentage: float = 70.0):
        super().__init__(config, "ENHANCED_VOLUME_PROFILE")
        self.indicator_type = IndicatorType.MARKET_STRUCTURE
        
        self.session_length = session_length  # minutes in trading session
        self.num_bins = num_bins
        self.value_area_percentage = value_area_percentage
        
        # Volume profile data
        self.volume_nodes: List[VolumeNode] = []
        self.session_data = deque(maxlen=session_length)
        
        # Profile metrics
        self.point_of_control = None  # Price level with highest volume
        self.value_area_high = None
        self.value_area_low = None
        
        # Institutional analysis
        self.institutional_nodes = deque(maxlen=100)
        self.large_trade_threshold = 0.0
        
        # Session tracking
        self.session_start = None
        self.current_session_volume = 0.0
        
    def calculate_values(self, price: float, volume: float, timestamp: datetime) -> Dict[str, Any]:
        """Calculate enhanced volume profile values"""
        # Add data to current session
        self.session_data.append({
            'price': price,
            'volume': volume,
            'timestamp': timestamp,
            'institutional_flow': self._detect_institutional_activity(volume, price)
        })
        
        self.current_session_volume += volume
        
        # Initialize session start
        if self.session_start is None:
            self.session_start = timestamp
        
        # Check if we need to reset session (new trading day)
        if self._is_new_session(timestamp):
            self._process_session()
            self._reset_session(timestamp)
        
        if len(self.session_data) < 10:
            return {
                'point_of_control': price,
                'value_area_high': price,
                'value_area_low': price,
                'volume_nodes': [],
                'institutional_activity': 0.0
            }
        
        # Calculate volume profile for current session
        self._calculate_volume_profile()
        
        # Calculate institutional activity metrics
        institutional_activity = self._calculate_institutional_activity()
        
        # Find high volume nodes
        high_volume_nodes = self._find_high_volume_nodes()
        
        return {
            'point_of_control': self.point_of_control.price if self.point_of_control else price,
            'value_area_high': self.value_area_high,
            'value_area_low': self.value_area_low,
            'volume_nodes': [{
                'price': node.price,
                'volume': node.volume,
                'institutional_percentage': node.institutional_percentage
            } for node in high_volume_nodes],
            'institutional_activity': institutional_activity,
            'session_volume': self.current_session_volume,
            'poc_strength': self.point_of_control.volume / self.current_session_volume if self.point_of_control and self.current_session_volume > 0 else 0
        }
    
    def _detect_institutional_activity(self, volume: float, price: float) -> float:
        """Detect institutional trading activity"""
        if len(self.volumes) < 20:
            return 0.0
        
        # Update large trade threshold
        recent_volumes = list(self.volumes)[-20:]
        self.large_trade_threshold = np.percentile(recent_volumes, 95)
        
        if volume > self.large_trade_threshold:
            # Calculate institutional flow strength
            volume_ratio = min(volume / self.large_trade_threshold, 5.0)
            return (volume_ratio - 1.0) / 4.0  # Normalize to 0-1
        
        return 0.0
    
    def _is_new_session(self, timestamp: datetime) -> bool:
        """Check if we're in a new trading session"""
        if self.session_start is None:
            return False
        
        # Simple check: new day
        return timestamp.date() != self.session_start.date()
    
    def _process_session(self):
        """Process completed session data"""
        if len(self.session_data) < 10:
            return
        
        # Calculate final volume profile for the session
        self._calculate_volume_profile()
        
        # Store institutional nodes
        if self.point_of_control:
            institutional_percentage = sum(
                data['institutional_flow'] for data in self.session_data
                if abs(data['price'] - self.point_of_control.price) <= self.point_of_control.price * 0.001
            ) / len(self.session_data)
            
            self.institutional_nodes.append({
                'price': self.point_of_control.price,
                'volume': self.point_of_control.volume,
                'institutional_percentage': institutional_percentage,
                'timestamp': self.session_start
            })
    
    def _reset_session(self, timestamp: datetime):
        """Reset for new session"""
        self.session_start = timestamp
        self.current_session_volume = 0.0
        self.session_data.clear()
        self.volume_nodes.clear()
    
    def _calculate_volume_profile(self):
        """Calculate volume profile from session data"""
        if len(self.session_data) < 5:
            return
        
        # Get price range
        prices = [data['price'] for data in self.session_data]
        min_price = min(prices)
        max_price = max(prices)
        
        if max_price == min_price:
            return
        
        # Create price bins
        bin_size = (max_price - min_price) / self.num_bins
        bins = [min_price + i * bin_size for i in range(self.num_bins + 1)]
        
        # Calculate volume for each bin
        self.volume_nodes.clear()
        
        for i in range(self.num_bins):
            bin_low = bins[i]
            bin_high = bins[i + 1]
            bin_center = (bin_low + bin_high) / 2
            
            # Sum volume in this bin
            bin_volume = 0.0
            bin_transactions = 0
            institutional_volume = 0.0
            
            for data in self.session_data:
                if bin_low <= data['price'] < bin_high:
                    bin_volume += data['volume']
                    bin_transactions += 1
                    if data['institutional_flow'] > 0.1:
                        institutional_volume += data['volume']
            
            if bin_volume > 0:
                avg_trade_size = bin_volume / bin_transactions if bin_transactions > 0 else 0
                institutional_percentage = institutional_volume / bin_volume if bin_volume > 0 else 0
                
                node = VolumeNode(
                    price=bin_center,
                    volume=bin_volume,
                    transactions=bin_transactions,
                    avg_trade_size=avg_trade_size,
                    institutional_percentage=institutional_percentage
                )
                self.volume_nodes.append(node)
        
        # Find Point of Control (highest volume node)
        if self.volume_nodes:
            self.point_of_control = max(self.volume_nodes, key=lambda x: x.volume)
            
            # Calculate Value Area
            self._calculate_value_area()
    
    def _calculate_value_area(self):
        """Calculate Value Area High and Low"""
        if not self.volume_nodes or not self.point_of_control:
            return
        
        # Sort nodes by volume (descending)
        sorted_nodes = sorted(self.volume_nodes, key=lambda x: x.volume, reverse=True)
        
        # Calculate target volume for value area
        total_volume = sum(node.volume for node in self.volume_nodes)
        target_volume = total_volume * (self.value_area_percentage / 100.0)
        
        # Find nodes that make up the value area
        value_area_volume = 0.0
        value_area_nodes = []
        
        for node in sorted_nodes:
            value_area_nodes.append(node)
            value_area_volume += node.volume
            
            if value_area_volume >= target_volume:
                break
        
        # Find price range of value area
        if value_area_nodes:
            value_area_prices = [node.price for node in value_area_nodes]
            self.value_area_high = max(value_area_prices)
            self.value_area_low = min(value_area_prices)
    
    def _calculate_institutional_activity(self) -> float:
        """Calculate overall institutional activity level"""
        if not self.session_data:
            return 0.0
        
        institutional_flows = [data['institutional_flow'] for data in self.session_data]
        return np.mean([flow for flow in institutional_flows if flow > 0]) if institutional_flows else 0.0
    
    def _find_high_volume_nodes(self) -> List[VolumeNode]:
        """Find high volume nodes (top 20%)"""
        if not self.volume_nodes:
            return []
        
        # Sort by volume and return top 20%
        sorted_nodes = sorted(self.volume_nodes, key=lambda x: x.volume, reverse=True)
        top_count = max(1, len(sorted_nodes) // 5)  # Top 20%
        
        return sorted_nodes[:top_count]
    
    def generate_signal(self, values: Dict[str, Any], price: float, volume: float) -> Tuple[SignalType, float]:
        """Generate signals based on volume profile analysis"""
        poc_price = values.get('point_of_control', price)
        value_area_high = values.get('value_area_high', price)
        value_area_low = values.get('value_area_low', price)
        institutional_activity = values.get('institutional_activity', 0)
        poc_strength = values.get('poc_strength', 0)
        
        # POC rejection/acceptance signals
        poc_distance = abs(price - poc_price) / poc_price if poc_price > 0 else 0
        
        if poc_distance < 0.005:  # Within 0.5% of POC
            if institutional_activity > 0.3 and poc_strength > 0.1:
                # Strong institutional interest at POC
                return SignalType.BUY, min(institutional_activity + poc_strength, 0.8)
        
        # Value area signals
        if value_area_low and value_area_high:
            # Price at value area low (support)
            if abs(price - value_area_low) / price < 0.01 and institutional_activity > 0.2:
                return SignalType.BUY, min(institutional_activity + 0.3, 0.7)
            
            # Price at value area high (resistance)
            elif abs(price - value_area_high) / price < 0.01 and institutional_activity > 0.2:
                return SignalType.SELL, min(institutional_activity + 0.3, 0.7)
            
            # Price outside value area
            elif price > value_area_high * 1.01:  # Above value area
                if institutional_activity > 0.4:
                    return SignalType.BUY, min(institutional_activity, 0.8)  # Breakout
                else:
                    return SignalType.SELL, 0.5  # Mean reversion
            
            elif price < value_area_low * 0.99:  # Below value area
                if institutional_activity > 0.4:
                    return SignalType.SELL, min(institutional_activity, 0.8)  # Breakdown
                else:
                    return SignalType.BUY, 0.5  # Mean reversion
        
        return SignalType.NEUTRAL, 0.0

# Factory function for creating market structure indicators
def create_market_structure_indicator(indicator_type: str, config: IndicatorConfig, **kwargs) -> EnhancedVolumeWeightedIndicator:
    """Factory function to create enhanced market structure indicators"""
    indicators = {
        'enhanced_support_resistance': lambda cfg: EnhancedSupportResistance(cfg, **kwargs),
        'enhanced_volume_profile': lambda cfg: EnhancedVolumeProfile(cfg, **kwargs)
    }
    
    indicator_factory = indicators.get(indicator_type.lower())
    if not indicator_factory:
        raise ValueError(f"Unknown enhanced market structure indicator type: {indicator_type}")
    
    return indicator_factory(config)