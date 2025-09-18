"""
Smart Money Analysis Module

This module provides comprehensive smart money flow detection, institutional bias assessment,
and order flow analysis for institutional-grade trading systems.

Features:
- Smart money flow detection using volume profile analysis
- Institutional bias assessment through order flow patterns
- Large order detection and tracking
- Market maker vs taker analysis
- Liquidity analysis and absorption detection
- Dark pool activity estimation
- Institutional footprint analysis

Author: Vincent S. Pereira
Version: 1.0.0
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, List, Any, Tuple, Union, NamedTuple
from datetime import datetime, timedelta
from collections import deque, defaultdict
from enum import Enum
from dataclasses import dataclass
import logging
from nautilus_trader_engine.indicators.consolidated_indicators import ConsolidatedIndicators


logger = logging.getLogger(__name__)

# ===========================================
# ENUMS AND DATA STRUCTURES
# ===========================================

class SmartMoneyBias(Enum):
    """Smart money directional bias"""
    STRONG_BULLISH = "strong_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    STRONG_BEARISH = "strong_bearish"

class InstitutionalActivity(Enum):
    """Level of institutional activity"""
    VERY_HIGH = "very_high"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    MINIMAL = "minimal"

class OrderFlowType(Enum):
    """Type of order flow detected"""
    AGGRESSIVE_BUYING = "aggressive_buying"
    AGGRESSIVE_SELLING = "aggressive_selling"
    PASSIVE_ACCUMULATION = "passive_accumulation"
    PASSIVE_DISTRIBUTION = "passive_distribution"
    BALANCED = "balanced"
    ABSORPTION = "absorption"

class LiquidityCondition(Enum):
    """Market liquidity conditions"""
    ABUNDANT = "abundant"
    NORMAL = "normal"
    THIN = "thin"
    VERY_THIN = "very_thin"
    ILLIQUID = "illiquid"

@dataclass
class SmartMoneyMetrics:
    """Comprehensive smart money analysis metrics"""
    # Core metrics
    smart_money_index: float  # 0-1 scale
    institutional_bias: SmartMoneyBias
    activity_level: InstitutionalActivity
    confidence: float  # 0-1 scale
    
    # Order flow analysis
    order_flow_type: OrderFlowType
    # New: unified flow direction enum-like object with .value (for compatibility with consumers)
    flow_direction: object  # Provides a .value attribute with strings like 'accumulation', 'distribution', etc.
    buy_pressure: float  # 0-1 scale
    sell_pressure: float  # 0-1 scale
    net_flow: float  # -1 to 1 scale
    
    # Volume analysis
    large_order_ratio: float  # Ratio of large orders to total volume
    # New: numeric institutional activity score (0-1) expected by consumers
    institutional_activity: float  # 0-1 scale
    block_trade_activity: float  # 0-1 scale
    dark_pool_estimate: float  # Estimated dark pool activity 0-1
    # New: dark pool activity alias for compatibility
    dark_pool_activity: float  # 0-1 scale
    # New: institutional flow ratio alias for compatibility
    institutional_flow_ratio: float  # Alias to large_order_ratio for downstream consumers
    
    # Liquidity metrics
    liquidity_condition: LiquidityCondition
    absorption_detected: bool
    liquidity_stress: float  # 0-1 scale
    
    # Timing analysis
    accumulation_phase: bool
    distribution_phase: bool
    breakout_preparation: bool
    
    # Market structure
    support_strength: float  # 0-1 scale
    resistance_strength: float  # 0-1 scale
    structural_shift: bool

@dataclass
class OrderFlowData:
    """Order flow data point"""
    timestamp: datetime
    price: float
    volume: float
    is_buy: bool
    size_category: str  # 'small', 'medium', 'large', 'block'
    urgency_score: float  # 0-1 scale

# ===========================================
# SMART MONEY ANALYSIS ENGINE
# ===========================================

class SmartMoneyAnalysisEngine:
    """Advanced smart money flow detection and analysis engine"""
    
    def __init__(self, 
                 lookback_period: int = 100,
                 large_order_threshold: float = 2.0,  # Multiple of average volume
                 block_trade_threshold: float = 5.0,  # Multiple of average volume
                 institutional_threshold: float = 10.0):  # Multiple of average volume
        
        self.lookback_period = lookback_period
        self.large_order_threshold = large_order_threshold
        self.block_trade_threshold = block_trade_threshold
        self.institutional_threshold = institutional_threshold
        
        # Data storage
        self.price_data = deque(maxlen=lookback_period * 2)
        self.volume_data = deque(maxlen=lookback_period * 2)
        self.timestamp_data = deque(maxlen=lookback_period * 2)
        self.order_flow_data = deque(maxlen=lookback_period)
        
        # Analysis components
        self.volume_profile = defaultdict(float)
        self.price_levels = deque(maxlen=50)  # Key price levels
        self.support_resistance = {'support': [], 'resistance': []}
        
        # Metrics tracking
        self.avg_volume = 0.0
        self.volume_std = 0.0
        self.current_metrics: Optional[SmartMoneyMetrics] = None
        
        # State tracking
        self.accumulation_zones = []
        self.distribution_zones = []
        self.absorption_events = []
        
    def update(self, price: float, volume: float, timestamp: datetime = None) -> SmartMoneyMetrics:
        """Update smart money analysis with new data point"""
        timestamp = timestamp or datetime.now()
        
        # Add data point
        self.price_data.append(price)
        self.volume_data.append(volume)
        self.timestamp_data.append(timestamp)
        
        # Update volume statistics
        self._update_volume_statistics()
        
        # Analyze order flow
        order_flow = self._analyze_order_flow(price, volume, timestamp)
        if order_flow:
            self.order_flow_data.append(order_flow)
        
        # Update volume profile
        self._update_volume_profile(price, volume)
        
        # Detect key levels
        self._detect_key_levels()
        
        # Generate comprehensive analysis
        self.current_metrics = self._generate_smart_money_metrics()
        
        return self.current_metrics
    
    def _update_volume_statistics(self):
        """Update volume statistics for threshold calculations"""
        if len(self.volume_data) < 20:
            return
        
        recent_volumes = list(self.volume_data)[-50:] if len(self.volume_data) >= 50 else list(self.volume_data)
        self.avg_volume = np.mean(recent_volumes)
        self.volume_std = np.std(recent_volumes)
    
    def _analyze_order_flow(self, price: float, volume: float, timestamp: datetime) -> Optional[OrderFlowData]:
        """Analyze individual order flow characteristics"""
        if len(self.price_data) < 2 or self.avg_volume == 0:
            return None
        
        prev_price = self.price_data[-2]
        
        # Determine if buy or sell based on price movement
        is_buy = price > prev_price
        
        # Categorize order size
        volume_ratio = volume / self.avg_volume if self.avg_volume > 0 else 1.0
        
        if volume_ratio >= self.institutional_threshold:
            size_category = 'institutional'
        elif volume_ratio >= self.block_trade_threshold:
            size_category = 'block'
        elif volume_ratio >= self.large_order_threshold:
            size_category = 'large'
        elif volume_ratio >= 1.5:
            size_category = 'medium'
        else:
            size_category = 'small'
        
        # Calculate urgency score based on price impact and volume
        price_change = abs(price - prev_price) / prev_price if prev_price != 0 else 0
        urgency_score = min(1.0, (price_change * 100 + volume_ratio / 10) / 2)
        
        return OrderFlowData(
            timestamp=timestamp,
            price=price,
            volume=volume,
            is_buy=is_buy,
            size_category=size_category,
            urgency_score=urgency_score
        )
    
    def _update_volume_profile(self, price: float, volume: float):
        """Update volume profile for price level analysis"""
        # Round price to nearest tick for grouping
        price_level = round(price, 2)
        self.volume_profile[price_level] += volume
        
        # Keep only recent price levels (sliding window)
        if len(self.volume_profile) > 200:
            # Remove oldest entries
            sorted_levels = sorted(self.volume_profile.items(), key=lambda x: x[1])
            for level, _ in sorted_levels[:50]:
                del self.volume_profile[level]
    
    def _detect_key_levels(self):
        """Detect key support and resistance levels from volume profile"""
        if len(self.volume_profile) < 10:
            return
        
        # Find high volume nodes (HVN) and low volume nodes (LVN)
        sorted_profile = sorted(self.volume_profile.items(), key=lambda x: x[1], reverse=True)
        
        # Top 20% volume levels are potential support/resistance
        hvn_count = max(3, len(sorted_profile) // 5)
        hvn_levels = [level for level, volume in sorted_profile[:hvn_count]]
        
        current_price = self.price_data[-1] if self.price_data else 0
        
        # Classify as support or resistance based on current price
        self.support_resistance = {'support': [], 'resistance': []}
        
        for level in hvn_levels:
            if level < current_price:
                self.support_resistance['support'].append(level)
            else:
                self.support_resistance['resistance'].append(level)
        
        # Sort levels
        self.support_resistance['support'].sort(reverse=True)  # Closest support first
        self.support_resistance['resistance'].sort()  # Closest resistance first
    
    def _generate_smart_money_metrics(self) -> SmartMoneyMetrics:
        """Generate comprehensive smart money analysis metrics"""
        if len(self.order_flow_data) < 10:
            return self._default_metrics()
        
        # Analyze recent order flow (last 20 data points)
        recent_flow = list(self.order_flow_data)[-20:]
        
        # Calculate buy/sell pressure
        buy_volume = sum(flow.volume for flow in recent_flow if flow.is_buy)
        sell_volume = sum(flow.volume for flow in recent_flow if not flow.is_buy)
        total_volume = buy_volume + sell_volume
        
        buy_pressure = buy_volume / total_volume if total_volume > 0 else 0.5
        sell_pressure = sell_volume / total_volume if total_volume > 0 else 0.5
        net_flow = buy_pressure - sell_pressure
        
        # Calculate large order metrics
        large_orders = [flow for flow in recent_flow if flow.size_category in ['large', 'block', 'institutional']]
        large_order_volume = sum(flow.volume for flow in large_orders)
        large_order_ratio = large_order_volume / total_volume if total_volume > 0 else 0
        
        # Block trade activity
        block_trades = [flow for flow in recent_flow if flow.size_category in ['block', 'institutional']]
        block_trade_activity = len(block_trades) / len(recent_flow) if recent_flow else 0
        
        # Smart money index calculation
        smart_money_index = self._calculate_smart_money_index(recent_flow)
        
        # Institutional bias
        institutional_bias = self._determine_institutional_bias(net_flow, smart_money_index)
        
        # Activity level
        activity_level = self._determine_activity_level(large_order_ratio, block_trade_activity)
        
        # Order flow type
        order_flow_type = self._determine_order_flow_type(recent_flow, net_flow)
        
        # Liquidity analysis
        liquidity_condition, absorption_detected, liquidity_stress = self._analyze_liquidity(recent_flow)
        
        # Phase detection
        accumulation_phase, distribution_phase, breakout_preparation = self._detect_market_phases()
        
        # Support/resistance strength
        support_strength, resistance_strength = self._calculate_level_strength()
        
        # Structural shift detection
        structural_shift = self._detect_structural_shift()
        
        # Dark pool estimation
        dark_pool_estimate = self._estimate_dark_pool_activity(recent_flow)
        
        # Confidence calculation
        confidence = self._calculate_confidence(smart_money_index, large_order_ratio, len(recent_flow))
        
        # New: compute unified institutional activity score and mappings for compatibility
        institutional_activity = min(1.0, max(0.0, (large_order_ratio + block_trade_activity) / 2.0))
        dark_pool_activity = dark_pool_estimate
        institutional_flow_ratio = large_order_ratio
        
        # New: determine flow_direction as an object with a .value attribute compatible with SmartMoneyFlow
        class _Flow:  # local lightweight carrier for .value
            def __init__(self, value: str):
                self.value = value
        
        if dark_pool_estimate > 0.6:
            flow_direction = _Flow('dark_pool_activity')
        elif institutional_bias == SmartMoneyBias.BULLISH:
            if institutional_activity > 0.6:
                flow_direction = _Flow('institutional_buying')
            elif net_flow > 0.05:
                flow_direction = _Flow('accumulation')
            else:
                flow_direction = _Flow('neutral')
        elif institutional_bias == SmartMoneyBias.BEARISH:
            if institutional_activity > 0.6:
                flow_direction = _Flow('institutional_selling')
            elif net_flow < -0.05:
                flow_direction = _Flow('distribution')
            else:
                flow_direction = _Flow('neutral')
        else:
            flow_direction = _Flow('neutral')
        
        return SmartMoneyMetrics(
            smart_money_index=smart_money_index,
            institutional_bias=institutional_bias,
            activity_level=activity_level,
            confidence=confidence,
            order_flow_type=order_flow_type,
            flow_direction=flow_direction,
            buy_pressure=buy_pressure,
            sell_pressure=sell_pressure,
            net_flow=net_flow,
            large_order_ratio=large_order_ratio,
            institutional_activity=institutional_activity,
            block_trade_activity=block_trade_activity,
            dark_pool_estimate=dark_pool_estimate,
            dark_pool_activity=dark_pool_activity,
            institutional_flow_ratio=institutional_flow_ratio,
            liquidity_condition=liquidity_condition,
            absorption_detected=absorption_detected,
            liquidity_stress=liquidity_stress,
            accumulation_phase=accumulation_phase,
            distribution_phase=distribution_phase,
            breakout_preparation=breakout_preparation,
            support_strength=support_strength,
            resistance_strength=resistance_strength,
            structural_shift=structural_shift
        )
    
    def _calculate_smart_money_index(self, recent_flow: List[OrderFlowData]) -> float:
        """Calculate smart money index based on order flow characteristics"""
        if not recent_flow:
            return 0.5
        
        # Weight factors
        size_weight = 0.4
        urgency_weight = 0.3
        timing_weight = 0.3
        
        total_score = 0.0
        total_weight = 0.0
        
        for flow in recent_flow:
            # Size score
            size_scores = {
                'small': 0.1,
                'medium': 0.3,
                'large': 0.7,
                'block': 0.9,
                'institutional': 1.0
            }
            size_score = size_scores.get(flow.size_category, 0.1)
            
            # Urgency score (already calculated)
            urgency_score = flow.urgency_score
            
            # Timing score (higher for off-hours or unusual timing)
            timing_score = 0.5  # Simplified for now
            
            # Combined score
            flow_score = (size_score * size_weight + 
                         urgency_score * urgency_weight + 
                         timing_score * timing_weight)
            
            total_score += flow_score * flow.volume
            total_weight += flow.volume
        
        return total_score / total_weight if total_weight > 0 else 0.5
    
    def _determine_institutional_bias(self, net_flow: float, smart_money_index: float) -> SmartMoneyBias:
        """Determine institutional directional bias"""
        # Combine net flow and smart money index
        bias_score = (net_flow + (smart_money_index - 0.5) * 2) / 2
        
        if bias_score > 0.6:
            return SmartMoneyBias.STRONG_BULLISH
        elif bias_score > 0.2:
            return SmartMoneyBias.BULLISH
        elif bias_score < -0.6:
            return SmartMoneyBias.STRONG_BEARISH
        elif bias_score < -0.2:
            return SmartMoneyBias.BEARISH
        else:
            return SmartMoneyBias.NEUTRAL
    
    def _determine_activity_level(self, large_order_ratio: float, block_trade_activity: float) -> InstitutionalActivity:
        """Determine level of institutional activity"""
        activity_score = (large_order_ratio + block_trade_activity) / 2
        
        if activity_score > 0.8:
            return InstitutionalActivity.VERY_HIGH
        elif activity_score > 0.6:
            return InstitutionalActivity.HIGH
        elif activity_score > 0.4:
            return InstitutionalActivity.MODERATE
        elif activity_score > 0.2:
            return InstitutionalActivity.LOW
        else:
            return InstitutionalActivity.MINIMAL
    
    def _determine_order_flow_type(self, recent_flow: List[OrderFlowData], net_flow: float) -> OrderFlowType:
        """Determine the type of order flow pattern"""
        if not recent_flow:
            return OrderFlowType.BALANCED
        
        # Analyze urgency and size patterns
        high_urgency_flows = [f for f in recent_flow if f.urgency_score > 0.7]
        large_flows = [f for f in recent_flow if f.size_category in ['large', 'block', 'institutional']]
        
        urgency_ratio = len(high_urgency_flows) / len(recent_flow)
        large_ratio = len(large_flows) / len(recent_flow)
        
        # Determine flow type
        if urgency_ratio > 0.6 and net_flow > 0.3:
            return OrderFlowType.AGGRESSIVE_BUYING
        elif urgency_ratio > 0.6 and net_flow < -0.3:
            return OrderFlowType.AGGRESSIVE_SELLING
        elif large_ratio > 0.4 and net_flow > 0.2:
            return OrderFlowType.PASSIVE_ACCUMULATION
        elif large_ratio > 0.4 and net_flow < -0.2:
            return OrderFlowType.PASSIVE_DISTRIBUTION
        elif urgency_ratio > 0.8:
            return OrderFlowType.ABSORPTION
        else:
            return OrderFlowType.BALANCED
    
    def _analyze_liquidity(self, recent_flow: List[OrderFlowData]) -> Tuple[LiquidityCondition, bool, float]:
        """Analyze market liquidity conditions"""
        if not recent_flow:
            return LiquidityCondition.NORMAL, False, 0.0
        
        # Calculate liquidity metrics
        avg_urgency = np.mean([f.urgency_score for f in recent_flow])
        volume_variance = np.var([f.volume for f in recent_flow])
        
        # Normalize volume variance
        avg_volume = np.mean([f.volume for f in recent_flow])
        normalized_variance = volume_variance / (avg_volume ** 2) if avg_volume > 0 else 0
        
        # Liquidity stress calculation
        liquidity_stress = min(1.0, (avg_urgency + normalized_variance) / 2)
        
        # Absorption detection
        absorption_detected = avg_urgency > 0.8 and normalized_variance > 0.5
        
        # Liquidity condition
        if liquidity_stress > 0.8:
            condition = LiquidityCondition.ILLIQUID
        elif liquidity_stress > 0.6:
            condition = LiquidityCondition.VERY_THIN
        elif liquidity_stress > 0.4:
            condition = LiquidityCondition.THIN
        elif liquidity_stress > 0.2:
            condition = LiquidityCondition.NORMAL
        else:
            condition = LiquidityCondition.ABUNDANT
        
        return condition, absorption_detected, liquidity_stress
    
    def _detect_market_phases(self) -> Tuple[bool, bool, bool]:
        """Detect market phases (accumulation, distribution, breakout preparation)"""
        if len(self.price_data) < 20:
            return False, False, False
        
        recent_prices = list(self.price_data)[-20:]
        recent_volumes = list(self.volume_data)[-20:]
        
        # Price volatility
        price_volatility = np.std(recent_prices) / np.mean(recent_prices) if np.mean(recent_prices) > 0 else 0
        
        # Volume trend
        volume_trend = np.polyfit(range(len(recent_volumes)), recent_volumes, 1)[0]
        avg_volume = np.mean(recent_volumes)
        volume_trend_normalized = volume_trend / avg_volume if avg_volume > 0 else 0
        
        # Phase detection logic
        accumulation_phase = (price_volatility < 0.02 and  # Low volatility
                             volume_trend_normalized > 0.1)  # Increasing volume
        
        distribution_phase = (price_volatility < 0.02 and  # Low volatility
                             volume_trend_normalized < -0.1)  # Decreasing volume
        
        breakout_preparation = (price_volatility < 0.015 and  # Very low volatility
                               abs(volume_trend_normalized) > 0.15)  # Strong volume trend
        
        return accumulation_phase, distribution_phase, breakout_preparation
    
    def _calculate_level_strength(self) -> Tuple[float, float]:
        """Calculate support and resistance level strength"""
        if not self.support_resistance['support'] and not self.support_resistance['resistance']:
            return 0.0, 0.0
        
        current_price = self.price_data[-1] if self.price_data else 0
        
        # Support strength (based on volume at support levels)
        support_strength = 0.0
        if self.support_resistance['support']:
            closest_support = self.support_resistance['support'][0]
            support_volume = self.volume_profile.get(closest_support, 0)
            total_volume = sum(self.volume_profile.values())
            support_strength = support_volume / total_volume if total_volume > 0 else 0
        
        # Resistance strength
        resistance_strength = 0.0
        if self.support_resistance['resistance']:
            closest_resistance = self.support_resistance['resistance'][0]
            resistance_volume = self.volume_profile.get(closest_resistance, 0)
            total_volume = sum(self.volume_profile.values())
            resistance_strength = resistance_volume / total_volume if total_volume > 0 else 0
        
        return support_strength, resistance_strength
    
    def _detect_structural_shift(self) -> bool:
        """Detect structural market shifts"""
        if len(self.price_data) < 50:
            return False
        
        # Compare recent price action to historical
        recent_prices = list(self.price_data)[-20:]
        historical_prices = list(self.price_data)[-50:-20]
        
        recent_volatility = np.std(recent_prices)
        historical_volatility = np.std(historical_prices)
        
        # Structural shift if volatility changed significantly
        volatility_ratio = recent_volatility / historical_volatility if historical_volatility > 0 else 1
        
        return volatility_ratio > 2.0 or volatility_ratio < 0.5
    
    def _estimate_dark_pool_activity(self, recent_flow: List[OrderFlowData]) -> float:
        """Estimate dark pool activity based on order flow patterns"""
        if not recent_flow:
            return 0.0
        
        # Look for signs of hidden liquidity
        # - Large orders with low urgency
        # - Unusual volume without corresponding price movement
        
        large_low_urgency = [f for f in recent_flow 
                           if f.size_category in ['large', 'block', 'institutional'] 
                           and f.urgency_score < 0.3]
        
        dark_pool_ratio = len(large_low_urgency) / len(recent_flow)
        
        return min(1.0, dark_pool_ratio * 2)  # Scale up the estimate
    
    def _calculate_confidence(self, smart_money_index: float, large_order_ratio: float, sample_size: int) -> float:
        """Calculate confidence in the analysis"""
        # Base confidence on data quality and signal strength
        data_quality = min(1.0, sample_size / 20)  # Full confidence with 20+ samples
        signal_strength = abs(smart_money_index - 0.5) * 2  # Distance from neutral
        order_quality = large_order_ratio  # Higher with more large orders
        
        confidence = (data_quality * 0.4 + signal_strength * 0.4 + order_quality * 0.2)
        return min(1.0, confidence)
    
    def _default_metrics(self) -> SmartMoneyMetrics:
        """Return default metrics when insufficient data"""
        # Local lightweight carrier for .value to match SmartMoneyFlow usage
        class _Flow:
            def __init__(self, value: str):
                self.value = value
        return SmartMoneyMetrics(
            smart_money_index=0.5,
            institutional_bias=SmartMoneyBias.NEUTRAL,
            activity_level=InstitutionalActivity.MINIMAL,
            confidence=0.0,
            order_flow_type=OrderFlowType.BALANCED,
            flow_direction=_Flow('neutral'),
            buy_pressure=0.5,
            sell_pressure=0.5,
            net_flow=0.0,
            large_order_ratio=0.0,
            institutional_activity=0.0,
            block_trade_activity=0.0,
            dark_pool_estimate=0.0,
            dark_pool_activity=0.0,
            institutional_flow_ratio=0.0,
            liquidity_condition=LiquidityCondition.NORMAL,
            absorption_detected=False,
            liquidity_stress=0.0,
            accumulation_phase=False,
            distribution_phase=False,
            breakout_preparation=False,
            support_strength=0.0,
            resistance_strength=0.0,
            structural_shift=False
        )

# ===========================================
# SMART MONEY MIXIN
# ===========================================

class SmartMoneyMixin:
    """Mixin class to add smart money analysis to indicators"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.smart_money_engine = SmartMoneyAnalysisEngine()
        self.smart_money_metrics: Optional[SmartMoneyMetrics] = None
    
    def update_with_smart_money_analysis(self, price: float, volume: float, timestamp: datetime = None) -> Dict[str, Any]:
        """Update smart money analysis and return metrics"""
        timestamp = timestamp or datetime.now()
        
        # Update smart money analysis
        self.smart_money_metrics = self.smart_money_engine.update(price, volume, timestamp)
        
        return {
            'smart_money_metrics': self.smart_money_metrics,
            'institutional_bias': self.smart_money_metrics.institutional_bias,
            # Provide enum activity level for downstream compatibility
            'institutional_activity': self.smart_money_metrics.activity_level,
            'smart_money_index': self.smart_money_metrics.smart_money_index,
            'order_flow_type': self.smart_money_metrics.order_flow_type
        }
    
    def get_smart_money_signal_adjustment(self, base_strength: float) -> float:
        """Adjust signal strength based on smart money analysis"""
        if not self.smart_money_metrics:
            return base_strength
        
        # Adjustment factors
        smi_factor = self.smart_money_metrics.smart_money_index
        confidence_factor = self.smart_money_metrics.confidence
        activity_factor = {
            InstitutionalActivity.VERY_HIGH: 1.3,
            InstitutionalActivity.HIGH: 1.2,
            InstitutionalActivity.MODERATE: 1.1,
            InstitutionalActivity.LOW: 1.0,
            InstitutionalActivity.MINIMAL: 0.9
        }.get(self.smart_money_metrics.activity_level, 1.0)
        
        # Calculate adjustment
        smart_money_adjustment = (smi_factor * confidence_factor * activity_factor)
        
        # Apply adjustment (weighted average)
        adjusted_strength = (base_strength * 0.7 + smart_money_adjustment * 0.3)
        
        return min(1.0, adjusted_strength)

# Export all classes and functions
__all__ = [
    # Enums
    'SmartMoneyBias', 'InstitutionalActivity', 'OrderFlowType', 'LiquidityCondition',
    
    # Data classes
    'SmartMoneyMetrics', 'OrderFlowData',
    
    # Main classes
    'SmartMoneyAnalysisEngine', 'SmartMoneyMixin'
]