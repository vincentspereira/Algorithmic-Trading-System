#!/usr/bin/env python3
"""
Institutional Volume Profile and Liquidity Analysis

Advanced volume profile analysis with institutional-grade features:
- Market Profile (TPO) Analysis
- Volume-at-Price Distribution
- Point of Control (POC) Detection
- Value Area Analysis
- Liquidity Pool Identification
- Order Flow Imbalance Detection
- TWAP/VWAP Deviation Analysis
- Smart Money Footprint Analysis

Author: Enhanced Trading System
Version: 1.0.0
Optimized for: Institutional trading and high-frequency environments
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union, Any, NamedTuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
import bisect
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

class VolumeProfileType(Enum):
    """Volume profile analysis types"""
    MARKET_PROFILE = "market_profile"
    VOLUME_AT_PRICE = "volume_at_price"
    LIQUIDITY_ANALYSIS = "liquidity_analysis"
    ORDER_FLOW = "order_flow"
    INSTITUTIONAL_FLOW = "institutional_flow"

class LiquidityLevel(Enum):
    """Liquidity level classification"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    CRITICAL = "critical"

class OrderFlowType(Enum):
    """Order flow types"""
    AGGRESSIVE_BUY = "aggressive_buy"
    AGGRESSIVE_SELL = "aggressive_sell"
    PASSIVE_BUY = "passive_buy"
    PASSIVE_SELL = "passive_sell"
    BALANCED = "balanced"

@dataclass
class VolumeNode:
    """Volume profile node representing price level activity"""
    price_level: float
    total_volume: float
    buy_volume: float
    sell_volume: float
    trade_count: int
    time_spent: int  # Time Price Opportunity (TPO)
    institutional_volume: float = 0.0
    large_order_volume: float = 0.0
    average_trade_size: float = 0.0
    volume_imbalance: float = 0.0
    liquidity_level: LiquidityLevel = LiquidityLevel.MEDIUM
    
    def __post_init__(self):
        if self.trade_count > 0:
            self.average_trade_size = self.total_volume / self.trade_count
        
        # Calculate volume imbalance
        total_directional = self.buy_volume + self.sell_volume
        if total_directional > 0:
            self.volume_imbalance = (self.buy_volume - self.sell_volume) / total_directional
        
        # Classify liquidity level
        self._classify_liquidity()
    
    def _classify_liquidity(self):
        """Classify liquidity level based on volume and activity"""
        if self.total_volume > 10000 and self.trade_count > 100:
            self.liquidity_level = LiquidityLevel.HIGH
        elif self.total_volume > 5000 and self.trade_count > 50:
            self.liquidity_level = LiquidityLevel.MEDIUM
        elif self.total_volume > 1000:
            self.liquidity_level = LiquidityLevel.LOW
        else:
            self.liquidity_level = LiquidityLevel.CRITICAL

@dataclass
class ValueArea:
    """Value area analysis result"""
    value_area_high: float
    value_area_low: float
    point_of_control: float
    poc_volume: float
    value_area_volume_percent: float
    total_volume: float
    price_range: float
    volume_distribution: Dict[float, float] = field(default_factory=dict)
    institutional_activity: float = 0.0
    smart_money_concentration: float = 0.0

@dataclass
class LiquidityPool:
    """Liquidity pool identification"""
    price_level: float
    depth: float
    width: float
    volume: float
    pool_type: str  # 'support', 'resistance', 'neutral'
    strength: float
    institutional_presence: float
    time_formation: datetime
    last_test: Optional[datetime] = None
    test_count: int = 0
    absorption_capacity: float = 0.0

@dataclass
class OrderFlowImbalance:
    """Order flow imbalance analysis"""
    price_level: float
    buy_imbalance: float
    sell_imbalance: float
    net_imbalance: float
    imbalance_strength: float
    flow_type: OrderFlowType
    institutional_bias: float
    timestamp: datetime
    confidence: float = 0.0

@dataclass
class InstitutionalVolumeProfileResult:
    """Comprehensive volume profile analysis result"""
    timestamp: datetime
    profile_type: VolumeProfileType
    value_area: ValueArea
    volume_nodes: List[VolumeNode]
    liquidity_pools: List[LiquidityPool]
    order_flow_imbalances: List[OrderFlowImbalance]
    twap: float
    vwap: float
    vwap_deviation: float
    market_efficiency: float
    institutional_activity_score: float
    smart_money_flow: float
    dominant_price_level: float
    volume_concentration: float
    metadata: Dict[str, Any] = field(default_factory=dict)

class InstitutionalVolumeProfile:
    """
    Institutional-Grade Volume Profile Analysis
    
    Provides comprehensive volume profile analysis with institutional features:
    - Market Profile (TPO) construction
    - Volume-at-Price distribution
    - Value Area calculation
    - Liquidity pool identification
    - Order flow imbalance detection
    - Institutional activity tracking
    """
    
    def __init__(self, 
                 tick_size: float = 0.01,
                 value_area_percent: float = 0.70,
                 min_volume_threshold: float = 100.0,
                 institutional_threshold: float = 10000.0,
                 lookback_periods: int = 100):
        
        self.tick_size = tick_size
        self.value_area_percent = value_area_percent
        self.min_volume_threshold = min_volume_threshold
        self.institutional_threshold = institutional_threshold
        self.lookback_periods = lookback_periods
        
        # Data storage
        self.price_levels: Dict[float, VolumeNode] = {}
        self.trade_history = deque(maxlen=lookback_periods * 10)
        self.volume_history = deque(maxlen=lookback_periods)
        self.price_history = deque(maxlen=lookback_periods)
        self.timestamp_history = deque(maxlen=lookback_periods)
        
        # Analysis components
        self.liquidity_pools: List[LiquidityPool] = []
        self.order_flow_tracker = OrderFlowTracker()
        self.institutional_detector = InstitutionalActivityDetector(institutional_threshold)
        
        # TWAP/VWAP tracking
        self.twap_calculator = TWAPCalculator()
        self.vwap_calculator = VWAPCalculator()
    
    def update(self, high: float, low: float, close: float, volume: float,
               buy_volume: float = None, sell_volume: float = None,
               trade_count: int = 1, timestamp: datetime = None) -> InstitutionalVolumeProfileResult:
        """Update volume profile with new market data"""
        
        if timestamp is None:
            timestamp = datetime.now()
        
        # Estimate buy/sell volume if not provided
        if buy_volume is None or sell_volume is None:
            buy_volume, sell_volume = self._estimate_buy_sell_volume(high, low, close, volume)
        
        # Store historical data
        self.price_history.append(close)
        self.volume_history.append(volume)
        self.timestamp_history.append(timestamp)
        
        # Update TWAP/VWAP
        self.twap_calculator.update(close, timestamp)
        self.vwap_calculator.update(close, volume, timestamp)
        
        # Process price levels within the bar range
        self._process_price_levels(high, low, close, volume, buy_volume, sell_volume, trade_count, timestamp)
        
        # Update institutional activity detection
        institutional_score = self.institutional_detector.analyze(close, volume, timestamp)
        
        # Update order flow analysis
        order_flow_imbalances = self.order_flow_tracker.analyze(
            high, low, close, volume, buy_volume, sell_volume, timestamp
        )
        
        # Calculate value area
        value_area = self._calculate_value_area()
        
        # Identify liquidity pools
        self._update_liquidity_pools(timestamp)
        
        # Calculate market efficiency metrics
        market_efficiency = self._calculate_market_efficiency()
        
        # Get volume nodes
        volume_nodes = self._get_significant_volume_nodes()
        
        # Calculate concentration metrics
        volume_concentration = self._calculate_volume_concentration()
        dominant_price_level = self._find_dominant_price_level()
        
        return InstitutionalVolumeProfileResult(
            timestamp=timestamp,
            profile_type=VolumeProfileType.INSTITUTIONAL_FLOW,
            value_area=value_area,
            volume_nodes=volume_nodes,
            liquidity_pools=self.liquidity_pools.copy(),
            order_flow_imbalances=order_flow_imbalances,
            twap=self.twap_calculator.get_twap(),
            vwap=self.vwap_calculator.get_vwap(),
            vwap_deviation=self._calculate_vwap_deviation(close),
            market_efficiency=market_efficiency,
            institutional_activity_score=institutional_score,
            smart_money_flow=self._calculate_smart_money_flow(),
            dominant_price_level=dominant_price_level,
            volume_concentration=volume_concentration,
            metadata={
                "total_price_levels": len(self.price_levels),
                "active_liquidity_pools": len([p for p in self.liquidity_pools if p.strength > 0.5]),
                "order_flow_imbalances": len(order_flow_imbalances),
                "institutional_threshold": self.institutional_threshold,
                "value_area_percent": self.value_area_percent
            }
        )
    
    def _estimate_buy_sell_volume(self, high: float, low: float, close: float, volume: float) -> Tuple[float, float]:
        """Estimate buy/sell volume based on price action"""
        if len(self.price_history) == 0:
            return volume * 0.5, volume * 0.5
        
        prev_close = self.price_history[-1]
        price_change = close - prev_close
        range_position = (close - low) / (high - low) if high != low else 0.5
        
        # Estimate based on price change and range position
        if price_change > 0:
            buy_ratio = 0.5 + (range_position * 0.3) + min(0.2, price_change / prev_close * 10)
        else:
            buy_ratio = 0.5 - ((1 - range_position) * 0.3) + max(-0.2, price_change / prev_close * 10)
        
        buy_ratio = max(0.1, min(0.9, buy_ratio))
        buy_volume = volume * buy_ratio
        sell_volume = volume * (1 - buy_ratio)
        
        return buy_volume, sell_volume
    
    def _process_price_levels(self, high: float, low: float, close: float, volume: float,
                             buy_volume: float, sell_volume: float, trade_count: int, timestamp: datetime):
        """Process and update price levels within the bar range"""
        
        # Round prices to tick size
        high_level = self._round_to_tick(high)
        low_level = self._round_to_tick(low)
        close_level = self._round_to_tick(close)
        
        # Distribute volume across price levels
        price_levels = self._get_price_levels_in_range(low_level, high_level)
        
        if not price_levels:
            price_levels = [close_level]
        
        # Distribute volume proportionally
        volume_per_level = volume / len(price_levels)
        buy_volume_per_level = buy_volume / len(price_levels)
        sell_volume_per_level = sell_volume / len(price_levels)
        trades_per_level = max(1, trade_count // len(price_levels))
        
        # Weight distribution based on proximity to close
        for price_level in price_levels:
            # Calculate weight based on distance from close
            distance = abs(price_level - close)
            max_distance = max(abs(high - close), abs(low - close))
            weight = 1.0 - (distance / max_distance) if max_distance > 0 else 1.0
            weight = max(0.1, weight)  # Minimum weight
            
            # Adjust volume by weight
            level_volume = volume_per_level * weight
            level_buy_volume = buy_volume_per_level * weight
            level_sell_volume = sell_volume_per_level * weight
            
            # Update or create volume node
            if price_level in self.price_levels:
                node = self.price_levels[price_level]
                node.total_volume += level_volume
                node.buy_volume += level_buy_volume
                node.sell_volume += level_sell_volume
                node.trade_count += trades_per_level
                node.time_spent += 1
            else:
                # Detect institutional volume
                institutional_vol = level_volume if level_volume > self.institutional_threshold else 0.0
                large_order_vol = level_volume if level_volume > self.institutional_threshold * 0.5 else 0.0
                
                self.price_levels[price_level] = VolumeNode(
                    price_level=price_level,
                    total_volume=level_volume,
                    buy_volume=level_buy_volume,
                    sell_volume=level_sell_volume,
                    trade_count=trades_per_level,
                    time_spent=1,
                    institutional_volume=institutional_vol,
                    large_order_volume=large_order_vol
                )
    
    def _round_to_tick(self, price: float) -> float:
        """Round price to nearest tick size"""
        return round(price / self.tick_size) * self.tick_size
    
    def _get_price_levels_in_range(self, low: float, high: float) -> List[float]:
        """Get all price levels within range"""
        levels = []
        current = low
        while current <= high:
            levels.append(current)
            current += self.tick_size
            current = self._round_to_tick(current)  # Handle floating point precision
        return levels
    
    def _calculate_value_area(self) -> ValueArea:
        """Calculate value area (70% of volume by default)"""
        if not self.price_levels:
            return ValueArea(
                value_area_high=0.0,
                value_area_low=0.0,
                point_of_control=0.0,
                poc_volume=0.0,
                value_area_volume_percent=0.0,
                total_volume=0.0,
                price_range=0.0
            )
        
        # Sort nodes by volume (descending)
        sorted_nodes = sorted(self.price_levels.values(), key=lambda x: x.total_volume, reverse=True)
        
        total_volume = sum(node.total_volume for node in sorted_nodes)
        target_volume = total_volume * self.value_area_percent
        
        # Find Point of Control (highest volume level)
        poc_node = sorted_nodes[0]
        point_of_control = poc_node.price_level
        poc_volume = poc_node.total_volume
        
        # Build value area around POC
        value_area_nodes = [poc_node]
        current_volume = poc_volume
        
        # Add nodes alternately above and below POC until target volume reached
        remaining_nodes = sorted_nodes[1:]
        
        while current_volume < target_volume and remaining_nodes:
            # Find closest nodes to current value area
            va_prices = [node.price_level for node in value_area_nodes]
            va_high = max(va_prices)
            va_low = min(va_prices)
            
            best_node = None
            best_distance = float('inf')
            
            for node in remaining_nodes:
                if node.price_level > va_high:
                    distance = node.price_level - va_high
                elif node.price_level < va_low:
                    distance = va_low - node.price_level
                else:
                    distance = 0  # Already within range
                
                if distance < best_distance:
                    best_distance = distance
                    best_node = node
            
            if best_node:
                value_area_nodes.append(best_node)
                current_volume += best_node.total_volume
                remaining_nodes.remove(best_node)
            else:
                break
        
        # Calculate value area bounds
        va_prices = [node.price_level for node in value_area_nodes]
        value_area_high = max(va_prices)
        value_area_low = min(va_prices)
        
        # Calculate institutional activity in value area
        institutional_activity = sum(node.institutional_volume for node in value_area_nodes) / current_volume if current_volume > 0 else 0.0
        
        # Calculate smart money concentration
        large_order_volume = sum(node.large_order_volume for node in value_area_nodes)
        smart_money_concentration = large_order_volume / current_volume if current_volume > 0 else 0.0
        
        # Create volume distribution
        volume_distribution = {node.price_level: node.total_volume for node in value_area_nodes}
        
        return ValueArea(
            value_area_high=value_area_high,
            value_area_low=value_area_low,
            point_of_control=point_of_control,
            poc_volume=poc_volume,
            value_area_volume_percent=current_volume / total_volume if total_volume > 0 else 0.0,
            total_volume=total_volume,
            price_range=value_area_high - value_area_low,
            volume_distribution=volume_distribution,
            institutional_activity=institutional_activity,
            smart_money_concentration=smart_money_concentration
        )
    
    def _update_liquidity_pools(self, timestamp: datetime):
        """Identify and update liquidity pools"""
        # Clear old pools
        self.liquidity_pools = [pool for pool in self.liquidity_pools 
                               if (timestamp - pool.time_formation).seconds < 3600]  # Keep pools for 1 hour
        
        # Find high-volume clusters
        if len(self.price_levels) < 3:
            return
        
        sorted_levels = sorted(self.price_levels.items(), key=lambda x: x[0])  # Sort by price
        
        # Look for volume clusters
        for i in range(1, len(sorted_levels) - 1):
            price, node = sorted_levels[i]
            prev_price, prev_node = sorted_levels[i-1]
            next_price, next_node = sorted_levels[i+1]
            
            # Check if this is a local volume maximum
            if (node.total_volume > prev_node.total_volume and 
                node.total_volume > next_node.total_volume and
                node.total_volume > self.min_volume_threshold * 5):
                
                # Calculate pool characteristics
                depth = node.total_volume
                width = min(price - prev_price, next_price - price)
                
                # Determine pool type based on volume imbalance
                if node.volume_imbalance > 0.2:
                    pool_type = 'support'
                elif node.volume_imbalance < -0.2:
                    pool_type = 'resistance'
                else:
                    pool_type = 'neutral'
                
                # Calculate strength
                avg_volume = sum(n.total_volume for _, n in sorted_levels) / len(sorted_levels)
                strength = min(1.0, node.total_volume / (avg_volume * 3)) if avg_volume > 0 else 0.0
                
                # Calculate institutional presence
                institutional_presence = node.institutional_volume / node.total_volume if node.total_volume > 0 else 0.0
                
                # Check if pool already exists at this level
                existing_pool = None
                for pool in self.liquidity_pools:
                    if abs(pool.price_level - price) < self.tick_size * 2:
                        existing_pool = pool
                        break
                
                if existing_pool:
                    # Update existing pool
                    existing_pool.depth = max(existing_pool.depth, depth)
                    existing_pool.volume += node.total_volume
                    existing_pool.strength = max(existing_pool.strength, strength)
                    existing_pool.institutional_presence = max(existing_pool.institutional_presence, institutional_presence)
                else:
                    # Create new pool
                    pool = LiquidityPool(
                        price_level=price,
                        depth=depth,
                        width=width,
                        volume=node.total_volume,
                        pool_type=pool_type,
                        strength=strength,
                        institutional_presence=institutional_presence,
                        time_formation=timestamp,
                        absorption_capacity=depth * 0.8  # 80% of depth before exhaustion
                    )
                    self.liquidity_pools.append(pool)
    
    def _calculate_market_efficiency(self) -> float:
        """Calculate market efficiency based on volume distribution"""
        if not self.price_levels:
            return 0.5
        
        # Calculate volume concentration (Herfindahl index)
        total_volume = sum(node.total_volume for node in self.price_levels.values())
        if total_volume == 0:
            return 0.5
        
        concentration_index = sum((node.total_volume / total_volume) ** 2 for node in self.price_levels.values())
        
        # Convert to efficiency score (lower concentration = higher efficiency)
        max_concentration = 1.0  # Perfect concentration
        min_concentration = 1.0 / len(self.price_levels)  # Perfect distribution
        
        if max_concentration == min_concentration:
            return 0.5
        
        efficiency = 1.0 - ((concentration_index - min_concentration) / (max_concentration - min_concentration))
        return max(0.0, min(1.0, efficiency))
    
    def _get_significant_volume_nodes(self, min_significance: float = 0.05) -> List[VolumeNode]:
        """Get volume nodes with significant activity"""
        if not self.price_levels:
            return []
        
        total_volume = sum(node.total_volume for node in self.price_levels.values())
        min_volume = total_volume * min_significance
        
        significant_nodes = [
            node for node in self.price_levels.values() 
            if node.total_volume >= min_volume
        ]
        
        # Sort by volume (descending)
        significant_nodes.sort(key=lambda x: x.total_volume, reverse=True)
        
        return significant_nodes[:20]  # Return top 20 nodes
    
    def _calculate_volume_concentration(self) -> float:
        """Calculate volume concentration ratio"""
        if not self.price_levels:
            return 0.0
        
        volumes = [node.total_volume for node in self.price_levels.values()]
        volumes.sort(reverse=True)
        
        total_volume = sum(volumes)
        if total_volume == 0:
            return 0.0
        
        # Calculate top 20% concentration
        top_20_percent_count = max(1, len(volumes) // 5)
        top_20_percent_volume = sum(volumes[:top_20_percent_count])
        
        return top_20_percent_volume / total_volume
    
    def _find_dominant_price_level(self) -> float:
        """Find the price level with highest volume"""
        if not self.price_levels:
            return 0.0
        
        return max(self.price_levels.items(), key=lambda x: x[1].total_volume)[0]
    
    def _calculate_vwap_deviation(self, current_price: float) -> float:
        """Calculate deviation from VWAP"""
        vwap = self.vwap_calculator.get_vwap()
        if vwap == 0:
            return 0.0
        
        return (current_price - vwap) / vwap
    
    def _calculate_smart_money_flow(self) -> float:
        """Calculate smart money flow indicator"""
        if not self.price_levels:
            return 0.0
        
        total_volume = sum(node.total_volume for node in self.price_levels.values())
        institutional_volume = sum(node.institutional_volume for node in self.price_levels.values())
        
        if total_volume == 0:
            return 0.0
        
        return institutional_volume / total_volume
    
    def get_liquidity_at_price(self, price: float, tolerance: float = None) -> float:
        """Get total liquidity at specific price level"""
        if tolerance is None:
            tolerance = self.tick_size
        
        total_liquidity = 0.0
        target_price = self._round_to_tick(price)
        
        for price_level, node in self.price_levels.items():
            if abs(price_level - target_price) <= tolerance:
                total_liquidity += node.total_volume
        
        return total_liquidity
    
    def get_support_resistance_levels(self, min_strength: float = 0.5) -> Dict[str, List[float]]:
        """Get significant support and resistance levels"""
        support_levels = []
        resistance_levels = []
        
        for pool in self.liquidity_pools:
            if pool.strength >= min_strength:
                if pool.pool_type == 'support':
                    support_levels.append(pool.price_level)
                elif pool.pool_type == 'resistance':
                    resistance_levels.append(pool.price_level)
        
        return {
            'support': sorted(support_levels),
            'resistance': sorted(resistance_levels, reverse=True)
        }

class OrderFlowTracker:
    """Order flow imbalance tracking"""
    
    def __init__(self, imbalance_threshold: float = 0.3):
        self.imbalance_threshold = imbalance_threshold
        self.flow_history = deque(maxlen=50)
    
    def analyze(self, high: float, low: float, close: float, volume: float,
               buy_volume: float, sell_volume: float, timestamp: datetime) -> List[OrderFlowImbalance]:
        """Analyze order flow imbalances"""
        imbalances = []
        
        # Calculate net imbalance
        total_directional = buy_volume + sell_volume
        if total_directional > 0:
            net_imbalance = (buy_volume - sell_volume) / total_directional
            
            # Determine flow type
            if abs(net_imbalance) > self.imbalance_threshold:
                if net_imbalance > 0:
                    flow_type = OrderFlowType.AGGRESSIVE_BUY
                else:
                    flow_type = OrderFlowType.AGGRESSIVE_SELL
                
                # Calculate strength and confidence
                strength = min(1.0, abs(net_imbalance) * 2)
                confidence = min(1.0, volume / 10000)  # Higher volume = higher confidence
                
                # Estimate institutional bias
                institutional_bias = min(1.0, volume / 50000) if volume > 10000 else 0.0
                
                imbalance = OrderFlowImbalance(
                    price_level=close,
                    buy_imbalance=buy_volume / total_directional,
                    sell_imbalance=sell_volume / total_directional,
                    net_imbalance=net_imbalance,
                    imbalance_strength=strength,
                    flow_type=flow_type,
                    institutional_bias=institutional_bias,
                    timestamp=timestamp,
                    confidence=confidence
                )
                
                imbalances.append(imbalance)
                self.flow_history.append(imbalance)
        
        return imbalances

class InstitutionalActivityDetector:
    """Detect institutional trading activity"""
    
    def __init__(self, threshold: float = 10000.0):
        self.threshold = threshold
        self.activity_history = deque(maxlen=100)
    
    def analyze(self, price: float, volume: float, timestamp: datetime) -> float:
        """Analyze institutional activity level"""
        # Base score from volume
        volume_score = min(1.0, volume / (self.threshold * 5))
        
        # Time-based clustering analysis
        clustering_score = self._analyze_clustering(volume, timestamp)
        
        # Combine scores
        institutional_score = (volume_score * 0.6 + clustering_score * 0.4)
        
        self.activity_history.append({
            'timestamp': timestamp,
            'volume': volume,
            'price': price,
            'score': institutional_score
        })
        
        return institutional_score
    
    def _analyze_clustering(self, volume: float, timestamp: datetime) -> float:
        """Analyze volume clustering patterns"""
        if len(self.activity_history) < 5:
            return 0.0
        
        # Look for volume clustering in recent periods
        recent_volumes = [entry['volume'] for entry in list(self.activity_history)[-5:]]
        avg_recent = np.mean(recent_volumes)
        
        # Check if current volume fits clustering pattern
        if volume > self.threshold and avg_recent > self.threshold * 0.5:
            return min(1.0, volume / (avg_recent * 2))
        
        return 0.0

class TWAPCalculator:
    """Time-Weighted Average Price calculator"""
    
    def __init__(self, period_minutes: int = 60):
        self.period_minutes = period_minutes
        self.price_time_data = deque(maxlen=period_minutes * 10)
    
    def update(self, price: float, timestamp: datetime):
        """Update TWAP with new price data"""
        self.price_time_data.append({
            'price': price,
            'timestamp': timestamp
        })
        
        # Clean old data
        cutoff_time = timestamp - timedelta(minutes=self.period_minutes)
        while (self.price_time_data and 
               self.price_time_data[0]['timestamp'] < cutoff_time):
            self.price_time_data.popleft()
    
    def get_twap(self) -> float:
        """Get current TWAP"""
        if not self.price_time_data:
            return 0.0
        
        return np.mean([entry['price'] for entry in self.price_time_data])

class VWAPCalculator:
    """Volume-Weighted Average Price calculator"""
    
    def __init__(self, period_minutes: int = 60):
        self.period_minutes = period_minutes
        self.price_volume_data = deque(maxlen=period_minutes * 10)
    
    def update(self, price: float, volume: float, timestamp: datetime):
        """Update VWAP with new price/volume data"""
        self.price_volume_data.append({
            'price': price,
            'volume': volume,
            'timestamp': timestamp
        })
        
        # Clean old data
        cutoff_time = timestamp - timedelta(minutes=self.period_minutes)
        while (self.price_volume_data and 
               self.price_volume_data[0]['timestamp'] < cutoff_time):
            self.price_volume_data.popleft()
    
    def get_vwap(self) -> float:
        """Get current VWAP"""
        if not self.price_volume_data:
            return 0.0
        
        total_pv = sum(entry['price'] * entry['volume'] for entry in self.price_volume_data)
        total_volume = sum(entry['volume'] for entry in self.price_volume_data)
        
        return total_pv / total_volume if total_volume > 0 else 0.0

# Factory functions
def create_institutional_volume_profile(**kwargs) -> InstitutionalVolumeProfile:
    """Create institutional volume profile analyzer"""
    return InstitutionalVolumeProfile(**kwargs)

def analyze_volume_profile(high: float, low: float, close: float, volume: float,
                          buy_volume: float = None, sell_volume: float = None,
                          **kwargs) -> InstitutionalVolumeProfileResult:
    """Analyze volume profile for single bar"""
    analyzer = create_institutional_volume_profile(**kwargs)
    return analyzer.update(high, low, close, volume, buy_volume, sell_volume)

if __name__ == "__main__":
    # Example usage
    print("Institutional Volume Profile Analysis")
    print("====================================")
    
    # Create sample data
    import random
    from datetime import datetime, timedelta
    
    # Initialize volume profile analyzer
    vp_analyzer = create_institutional_volume_profile(
        tick_size=0.01,
        value_area_percent=0.70,
        institutional_threshold=5000.0
    )
    
    # Generate sample OHLCV data
    base_price = 100.0
    current_time = datetime.now()
    
    print("\nProcessing sample market data...")
    
    for i in range(100):
        # Generate realistic OHLCV data
        price_change = random.uniform(-1, 1)
        base_price += price_change
        
        high = base_price + random.uniform(0, 0.5)
        low = base_price - random.uniform(0, 0.5)
        close = base_price + random.uniform(-0.25, 0.25)
        volume = random.randint(1000, 20000)
        
        # Generate buy/sell volume
        buy_ratio = random.uniform(0.3, 0.7)
        buy_volume = volume * buy_ratio
        sell_volume = volume * (1 - buy_ratio)
        
        timestamp = current_time + timedelta(minutes=i)
        
        # Update volume profile
        result = vp_analyzer.update(high, low, close, volume, buy_volume, sell_volume, timestamp=timestamp)
        
        if i >= 50 and i % 10 == 0:  # Show results periodically
            print(f"\nTimestamp: {timestamp.strftime('%H:%M:%S')}")
            print(f"Price: {close:.2f}, Volume: {volume}")
            print(f"VWAP: {result.vwap:.2f}, TWAP: {result.twap:.2f}")
            print(f"POC: {result.value_area.point_of_control:.2f} (Volume: {result.value_area.poc_volume:.0f})")
            print(f"Value Area: {result.value_area.value_area_low:.2f} - {result.value_area.value_area_high:.2f}")
            print(f"Market Efficiency: {result.market_efficiency:.2f}")
            print(f"Institutional Activity: {result.institutional_activity_score:.2f}")
            print(f"Smart Money Flow: {result.smart_money_flow:.2f}")
            print(f"Active Liquidity Pools: {result.metadata['active_liquidity_pools']}")
            
            if i == 90:  # Last detailed output
                print("\n" + "="*50)
                print("Volume Profile Analysis Summary:")
                print(f"Total Price Levels: {result.metadata['total_price_levels']}")
                print(f"Volume Concentration: {result.volume_concentration:.2f}")
                print(f"Dominant Price Level: {result.dominant_price_level:.2f}")
                print(f"VWAP Deviation: {result.vwap_deviation:.3f}")
                
                # Show top volume nodes
                print("\nTop Volume Nodes:")
                for i, node in enumerate(result.volume_nodes[:5]):
                    print(f"{i+1}. Price: {node.price_level:.2f}, Volume: {node.total_volume:.0f}, "
                          f"Imbalance: {node.volume_imbalance:.2f}, Liquidity: {node.liquidity_level.value}")
                
                # Show liquidity pools
                if result.liquidity_pools:
                    print("\nLiquidity Pools:")
                    for pool in result.liquidity_pools[:3]:
                        print(f"Price: {pool.price_level:.2f}, Type: {pool.pool_type}, "
                              f"Strength: {pool.strength:.2f}, Institutional: {pool.institutional_presence:.2f}")
                
                break
    
    print("\nInstitutional volume profile analysis completed!")