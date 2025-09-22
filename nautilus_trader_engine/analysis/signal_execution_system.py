"""Signal-Driven Execution System

Maps signal types and characteristics to appropriate execution algorithms,
optimizing execution strategy based on signal urgency, market conditions,
and risk parameters.

Key Features:
- Dynamic execution algorithm selection
- Signal urgency classification
- Market impact optimization
- Adaptive order sizing
- Real-time execution monitoring
- Performance tracking and optimization
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple, Union, Callable
from collections import deque, defaultdict
from dataclasses import dataclass, field
from enum import Enum
import json
from abc import ABC, abstractmethod

from .enhanced_base import SignalType
from .ml_enhanced_system import MarketRegime, SignalQuality

try:
    from utils.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

class ExecutionAlgorithm(Enum):
    """Available execution algorithms"""
    MARKET = "market"  # Immediate market order
    LIMIT = "limit"    # Limit order at specified price
    TWAP = "twap"      # Time-Weighted Average Price
    VWAP = "vwap"      # Volume-Weighted Average Price
    POV = "pov"        # Percentage of Volume
    ICEBERG = "iceberg" # Iceberg order (hidden quantity)
    SNIPER = "sniper"   # Aggressive liquidity taking
    STEALTH = "stealth" # Passive liquidity providing
    ADAPTIVE = "adaptive" # Adaptive algorithm selection
    CUSTOM = "custom"   # Custom execution logic

class SignalUrgency(Enum):
    """Signal urgency levels"""
    IMMEDIATE = "immediate"    # Execute immediately
    HIGH = "high"             # Execute within seconds
    MEDIUM = "medium"         # Execute within minutes
    LOW = "low"               # Execute within hours
    PASSIVE = "passive"       # Execute opportunistically

class ExecutionStyle(Enum):
    """Execution style preferences"""
    AGGRESSIVE = "aggressive"  # Prioritize speed over cost
    BALANCED = "balanced"      # Balance speed and cost
    CONSERVATIVE = "conservative" # Prioritize cost over speed
    STEALTH = "stealth"        # Minimize market impact

@dataclass
class ExecutionConfig:
    """Configuration for execution system"""
    # Default algorithm mappings
    default_algorithm: ExecutionAlgorithm = ExecutionAlgorithm.ADAPTIVE
    
    # Urgency thresholds
    immediate_confidence_threshold: float = 0.9
    high_urgency_confidence_threshold: float = 0.75
    medium_urgency_confidence_threshold: float = 0.6
    
    # Market impact parameters
    max_participation_rate: float = 0.20  # Max 20% of volume
    min_participation_rate: float = 0.01  # Min 1% of volume
    impact_threshold: float = 0.001       # 10 bps impact threshold
    
    # Order sizing
    max_order_size_ratio: float = 0.05    # Max 5% of ADV
    min_order_size: float = 100           # Minimum order size
    iceberg_slice_ratio: float = 0.1      # 10% of total order
    
    # Timing parameters
    twap_duration_minutes: int = 30
    vwap_duration_minutes: int = 60
    passive_timeout_minutes: int = 120
    
    # Risk parameters
    max_slippage_tolerance: float = 0.002  # 20 bps max slippage
    stop_loss_threshold: float = 0.01      # 1% stop loss
    
    # Performance tracking
    enable_performance_tracking: bool = True
    benchmark_against_arrival_price: bool = True
    
@dataclass
class SignalCharacteristics:
    """Characteristics of a trading signal"""
    signal_type: SignalType
    confidence: float
    urgency: SignalUrgency
    expected_duration: timedelta
    market_regime: MarketRegime
    signal_quality: SignalQuality
    
    # Market context
    current_volatility: float
    current_spread: float
    current_volume: float
    average_daily_volume: float
    
    # Position context
    target_quantity: float
    current_position: float
    risk_limit: float
    
    # Additional metadata
    signal_source: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExecutionPlan:
    """Execution plan for a signal"""
    algorithm: ExecutionAlgorithm
    execution_style: ExecutionStyle
    urgency: SignalUrgency
    
    # Order parameters
    total_quantity: float
    slice_size: float
    participation_rate: float
    time_horizon: timedelta
    
    # Price parameters
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    price_tolerance: float = 0.001
    
    # Execution parameters
    max_slices: int = 10
    slice_interval: timedelta = timedelta(minutes=1)
    adaptive_sizing: bool = True
    
    # Risk parameters
    max_market_impact: float = 0.002
    timeout: timedelta = timedelta(minutes=30)
    
    # Metadata
    plan_id: str = field(default_factory=lambda: f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    created_at: datetime = field(default_factory=datetime.now)
    rationale: str = ""

@dataclass
class ExecutionResult:
    """Result of execution"""
    plan_id: str
    executed_quantity: float
    average_price: float
    total_cost: float
    
    # Performance metrics
    arrival_price: float
    benchmark_price: float
    slippage: float
    market_impact: float
    
    # Timing metrics
    start_time: datetime
    end_time: datetime
    execution_duration: timedelta
    
    # Order statistics
    total_orders: int
    filled_orders: int
    cancelled_orders: int
    
    # Status
    status: str  # "completed", "partial", "cancelled", "failed"
    error_message: Optional[str] = None
    
class SignalUrgencyClassifier:
    """Classifies signal urgency based on characteristics"""
    
    def __init__(self, config: ExecutionConfig):
        self.config = config
    
    def classify_urgency(self, characteristics: SignalCharacteristics) -> SignalUrgency:
        """Classify signal urgency"""
        confidence = characteristics.confidence
        regime = characteristics.market_regime
        quality = characteristics.signal_quality
        volatility = characteristics.current_volatility
        
        # Immediate urgency conditions
        if (confidence >= self.config.immediate_confidence_threshold and
            quality == SignalQuality.EXCELLENT and
            regime in [MarketRegime.BREAKOUT, MarketRegime.HIGH_VOLATILITY]):
            return SignalUrgency.IMMEDIATE
        
        # High urgency conditions
        if (confidence >= self.config.high_urgency_confidence_threshold and
            quality in [SignalQuality.EXCELLENT, SignalQuality.GOOD]):
            return SignalUrgency.HIGH
        
        # Medium urgency conditions
        if confidence >= self.config.medium_urgency_confidence_threshold:
            return SignalUrgency.MEDIUM
        
        # Low urgency for weak signals
        if confidence >= 0.4:
            return SignalUrgency.LOW
        
        # Passive for very weak signals
        return SignalUrgency.PASSIVE

class ExecutionAlgorithmSelector:
    """Selects appropriate execution algorithm based on signal characteristics"""
    
    def __init__(self, config: ExecutionConfig):
        self.config = config
        self.algorithm_performance = defaultdict(list)
    
    def select_algorithm(self, characteristics: SignalCharacteristics, 
                        urgency: SignalUrgency) -> ExecutionAlgorithm:
        """Select optimal execution algorithm"""
        
        # Immediate execution
        if urgency == SignalUrgency.IMMEDIATE:
            return ExecutionAlgorithm.MARKET
        
        # High urgency - aggressive algorithms
        if urgency == SignalUrgency.HIGH:
            if characteristics.current_volatility > 0.03:
                return ExecutionAlgorithm.SNIPER
            else:
                return ExecutionAlgorithm.LIMIT
        
        # Medium urgency - balanced approach
        if urgency == SignalUrgency.MEDIUM:
            if characteristics.target_quantity > characteristics.average_daily_volume * 0.05:
                return ExecutionAlgorithm.TWAP
            else:
                return ExecutionAlgorithm.VWAP
        
        # Low urgency - cost-optimized
        if urgency == SignalUrgency.LOW:
            if characteristics.target_quantity > characteristics.average_daily_volume * 0.1:
                return ExecutionAlgorithm.ICEBERG
            else:
                return ExecutionAlgorithm.POV
        
        # Passive - stealth execution
        return ExecutionAlgorithm.STEALTH
    
    def get_execution_style(self, algorithm: ExecutionAlgorithm, 
                           characteristics: SignalCharacteristics) -> ExecutionStyle:
        """Determine execution style based on algorithm and characteristics"""
        
        aggressive_algorithms = [ExecutionAlgorithm.MARKET, ExecutionAlgorithm.SNIPER]
        conservative_algorithms = [ExecutionAlgorithm.STEALTH, ExecutionAlgorithm.POV]
        
        if algorithm in aggressive_algorithms:
            return ExecutionStyle.AGGRESSIVE
        elif algorithm in conservative_algorithms:
            return ExecutionStyle.CONSERVATIVE
        else:
            return ExecutionStyle.BALANCED

class ExecutionPlanGenerator:
    """Generates detailed execution plans"""
    
    def __init__(self, config: ExecutionConfig):
        self.config = config
    
    def generate_plan(self, characteristics: SignalCharacteristics,
                     algorithm: ExecutionAlgorithm, urgency: SignalUrgency,
                     execution_style: ExecutionStyle) -> ExecutionPlan:
        """Generate detailed execution plan"""
        
        # Calculate basic parameters
        total_quantity = abs(characteristics.target_quantity)
        
        # Determine participation rate
        participation_rate = self._calculate_participation_rate(
            characteristics, algorithm, urgency
        )
        
        # Calculate slice size
        slice_size = self._calculate_slice_size(
            total_quantity, characteristics.average_daily_volume, algorithm
        )
        
        # Determine time horizon
        time_horizon = self._calculate_time_horizon(
            algorithm, urgency, total_quantity, characteristics.average_daily_volume
        )
        
        # Calculate price parameters
        limit_price, stop_price = self._calculate_price_parameters(
            characteristics, algorithm, execution_style
        )
        
        # Generate execution plan
        plan = ExecutionPlan(
            algorithm=algorithm,
            execution_style=execution_style,
            urgency=urgency,
            total_quantity=total_quantity,
            slice_size=slice_size,
            participation_rate=participation_rate,
            time_horizon=time_horizon,
            limit_price=limit_price,
            stop_price=stop_price,
            price_tolerance=self._calculate_price_tolerance(characteristics, execution_style),
            max_slices=max(1, int(total_quantity / slice_size)),
            slice_interval=self._calculate_slice_interval(time_horizon, total_quantity, slice_size),
            adaptive_sizing=algorithm in [ExecutionAlgorithm.ADAPTIVE, ExecutionAlgorithm.VWAP],
            max_market_impact=self._calculate_max_impact(characteristics, execution_style),
            timeout=time_horizon * 2,  # Timeout is 2x expected duration
            rationale=self._generate_rationale(characteristics, algorithm, urgency)
        )
        
        return plan
    
    def _calculate_participation_rate(self, characteristics: SignalCharacteristics,
                                    algorithm: ExecutionAlgorithm, 
                                    urgency: SignalUrgency) -> float:
        """Calculate participation rate"""
        base_rate = 0.1  # 10% base rate
        
        # Adjust for urgency
        urgency_multipliers = {
            SignalUrgency.IMMEDIATE: 2.0,
            SignalUrgency.HIGH: 1.5,
            SignalUrgency.MEDIUM: 1.0,
            SignalUrgency.LOW: 0.7,
            SignalUrgency.PASSIVE: 0.3
        }
        
        rate = base_rate * urgency_multipliers.get(urgency, 1.0)
        
        # Adjust for algorithm
        if algorithm == ExecutionAlgorithm.POV:
            rate *= 0.8  # More conservative for POV
        elif algorithm == ExecutionAlgorithm.SNIPER:
            rate *= 1.5  # More aggressive for sniper
        
        # Apply limits
        return max(self.config.min_participation_rate, 
                  min(self.config.max_participation_rate, rate))
    
    def _calculate_slice_size(self, total_quantity: float, adv: float, 
                            algorithm: ExecutionAlgorithm) -> float:
        """Calculate order slice size"""
        # Base slice as percentage of ADV
        base_slice_ratio = 0.01  # 1% of ADV
        
        if algorithm == ExecutionAlgorithm.ICEBERG:
            slice_ratio = self.config.iceberg_slice_ratio
        elif algorithm in [ExecutionAlgorithm.MARKET, ExecutionAlgorithm.SNIPER]:
            slice_ratio = 0.05  # Larger slices for aggressive algorithms
        else:
            slice_ratio = base_slice_ratio
        
        slice_size = min(total_quantity, adv * slice_ratio)
        return max(self.config.min_order_size, slice_size)
    
    def _calculate_time_horizon(self, algorithm: ExecutionAlgorithm, urgency: SignalUrgency,
                              total_quantity: float, adv: float) -> timedelta:
        """Calculate execution time horizon"""
        
        # Base time based on algorithm
        if algorithm == ExecutionAlgorithm.MARKET:
            return timedelta(seconds=30)
        elif algorithm == ExecutionAlgorithm.TWAP:
            return timedelta(minutes=self.config.twap_duration_minutes)
        elif algorithm == ExecutionAlgorithm.VWAP:
            return timedelta(minutes=self.config.vwap_duration_minutes)
        elif algorithm == ExecutionAlgorithm.STEALTH:
            return timedelta(minutes=self.config.passive_timeout_minutes)
        
        # Adjust based on urgency
        urgency_minutes = {
            SignalUrgency.IMMEDIATE: 1,
            SignalUrgency.HIGH: 5,
            SignalUrgency.MEDIUM: 15,
            SignalUrgency.LOW: 60,
            SignalUrgency.PASSIVE: 120
        }
        
        base_minutes = urgency_minutes.get(urgency, 30)
        
        # Adjust for order size relative to ADV
        size_ratio = total_quantity / adv if adv > 0 else 1
        if size_ratio > 0.1:  # Large order
            base_minutes *= 2
        elif size_ratio > 0.05:  # Medium order
            base_minutes *= 1.5
        
        return timedelta(minutes=base_minutes)
    
    def _calculate_price_parameters(self, characteristics: SignalCharacteristics,
                                  algorithm: ExecutionAlgorithm,
                                  execution_style: ExecutionStyle) -> Tuple[Optional[float], Optional[float]]:
        """Calculate limit and stop prices"""
        
        # Market orders don't need limit prices
        if algorithm == ExecutionAlgorithm.MARKET:
            return None, None
        
        # Estimate current market price (would come from market data in real implementation)
        current_price = 100.0  # Placeholder
        spread = characteristics.current_spread
        
        # Calculate limit price based on signal direction and execution style
        if characteristics.signal_type == SignalType.BUY:
            if execution_style == ExecutionStyle.AGGRESSIVE:
                limit_price = current_price + spread * 0.5  # Cross spread partially
            elif execution_style == ExecutionStyle.CONSERVATIVE:
                limit_price = current_price - spread * 0.2  # Inside bid
            else:  # BALANCED
                limit_price = current_price + spread * 0.1  # Near mid
        elif characteristics.signal_type == SignalType.SELL:
            if execution_style == ExecutionStyle.AGGRESSIVE:
                limit_price = current_price - spread * 0.5
            elif execution_style == ExecutionStyle.CONSERVATIVE:
                limit_price = current_price + spread * 0.2
            else:
                limit_price = current_price - spread * 0.1
        else:
            limit_price = current_price
        
        # Calculate stop price (for risk management)
        stop_distance = current_price * self.config.stop_loss_threshold
        if characteristics.signal_type == SignalType.BUY:
            stop_price = current_price - stop_distance
        elif characteristics.signal_type == SignalType.SELL:
            stop_price = current_price + stop_distance
        else:
            stop_price = None
        
        return limit_price, stop_price
    
    def _calculate_price_tolerance(self, characteristics: SignalCharacteristics,
                                 execution_style: ExecutionStyle) -> float:
        """Calculate price tolerance"""
        base_tolerance = characteristics.current_spread
        
        if execution_style == ExecutionStyle.AGGRESSIVE:
            return base_tolerance * 2.0
        elif execution_style == ExecutionStyle.CONSERVATIVE:
            return base_tolerance * 0.5
        else:
            return base_tolerance
    
    def _calculate_max_impact(self, characteristics: SignalCharacteristics,
                            execution_style: ExecutionStyle) -> float:
        """Calculate maximum acceptable market impact"""
        base_impact = self.config.impact_threshold
        
        if execution_style == ExecutionStyle.AGGRESSIVE:
            return base_impact * 3.0
        elif execution_style == ExecutionStyle.CONSERVATIVE:
            return base_impact * 0.5
        else:
            return base_impact
    
    def _generate_rationale(self, characteristics: SignalCharacteristics,
                          algorithm: ExecutionAlgorithm, urgency: SignalUrgency) -> str:
        """Generate human-readable rationale for execution plan"""
        
        rationale_parts = []
        
        # Signal characteristics
        rationale_parts.append(f"Signal: {characteristics.signal_type.value} with {characteristics.confidence:.1%} confidence")
        
        # Urgency reasoning
        rationale_parts.append(f"Urgency: {urgency.value} based on signal quality and market regime")
        
        # Algorithm selection
        rationale_parts.append(f"Algorithm: {algorithm.value} selected for optimal execution")
        
        # Market conditions
        if characteristics.current_volatility > 0.03:
            rationale_parts.append("High volatility detected - using adaptive sizing")
        
        if characteristics.target_quantity > characteristics.average_daily_volume * 0.1:
            rationale_parts.append("Large order size - using stealth execution to minimize impact")
        
        return "; ".join(rationale_parts)

class ExecutionMonitor:
    """Monitors execution progress and performance"""
    
    def __init__(self, config: ExecutionConfig):
        self.config = config
        self.active_executions: Dict[str, Dict[str, Any]] = {}
        self.execution_history = deque(maxlen=1000)
        self.performance_metrics = defaultdict(list)
    
    def start_execution(self, plan: ExecutionPlan, arrival_price: float):
        """Start monitoring an execution"""
        self.active_executions[plan.plan_id] = {
            'plan': plan,
            'start_time': datetime.now(),
            'arrival_price': arrival_price,
            'executed_quantity': 0.0,
            'total_cost': 0.0,
            'orders': [],
            'status': 'active'
        }
        
        logger.info(f"Started execution monitoring for plan {plan.plan_id}")
    
    def update_execution(self, plan_id: str, executed_qty: float, 
                        execution_price: float, order_id: str = None):
        """Update execution progress"""
        if plan_id not in self.active_executions:
            logger.warning(f"Unknown execution plan: {plan_id}")
            return
        
        execution = self.active_executions[plan_id]
        execution['executed_quantity'] += executed_qty
        execution['total_cost'] += executed_qty * execution_price
        
        # Record order
        execution['orders'].append({
            'order_id': order_id,
            'quantity': executed_qty,
            'price': execution_price,
            'timestamp': datetime.now()
        })
        
        # Check if execution is complete
        plan = execution['plan']
        if execution['executed_quantity'] >= plan.total_quantity * 0.95:  # 95% filled
            self._complete_execution(plan_id)
    
    def _complete_execution(self, plan_id: str):
        """Complete an execution and calculate performance metrics"""
        if plan_id not in self.active_executions:
            return
        
        execution = self.active_executions[plan_id]
        plan = execution['plan']
        
        # Calculate performance metrics
        end_time = datetime.now()
        duration = end_time - execution['start_time']
        
        executed_qty = execution['executed_quantity']
        total_cost = execution['total_cost']
        avg_price = total_cost / executed_qty if executed_qty > 0 else 0
        
        arrival_price = execution['arrival_price']
        slippage = (avg_price - arrival_price) / arrival_price if arrival_price > 0 else 0
        
        # Create execution result
        result = ExecutionResult(
            plan_id=plan_id,
            executed_quantity=executed_qty,
            average_price=avg_price,
            total_cost=total_cost,
            arrival_price=arrival_price,
            benchmark_price=arrival_price,  # Simplified benchmark
            slippage=slippage,
            market_impact=abs(slippage),  # Simplified impact calculation
            start_time=execution['start_time'],
            end_time=end_time,
            execution_duration=duration,
            total_orders=len(execution['orders']),
            filled_orders=len(execution['orders']),
            cancelled_orders=0,
            status="completed"
        )
        
        # Store result
        self.execution_history.append(result)
        
        # Update performance metrics
        self.performance_metrics[plan.algorithm.value].append({
            'slippage': slippage,
            'market_impact': abs(slippage),
            'duration': duration.total_seconds() / 60,  # minutes
            'fill_rate': executed_qty / plan.total_quantity
        })
        
        # Remove from active executions
        del self.active_executions[plan_id]
        
        logger.info(f"Completed execution {plan_id}: {executed_qty:.0f} @ {avg_price:.4f} (slippage: {slippage:.2%})")
    
    def get_execution_status(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get current execution status"""
        return self.active_executions.get(plan_id)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary across all executions"""
        if not self.execution_history:
            return {}
        
        recent_executions = list(self.execution_history)[-50:]  # Last 50 executions
        
        summary = {
            'total_executions': len(self.execution_history),
            'recent_executions': len(recent_executions),
            'average_slippage': np.mean([e.slippage for e in recent_executions]),
            'average_market_impact': np.mean([e.market_impact for e in recent_executions]),
            'average_duration_minutes': np.mean([e.execution_duration.total_seconds() / 60 for e in recent_executions]),
            'completion_rate': np.mean([1.0 if e.status == "completed" else 0.0 for e in recent_executions]),
            'algorithm_performance': {}
        }
        
        # Algorithm-specific performance
        for algorithm, metrics in self.performance_metrics.items():
            if metrics:
                recent_metrics = metrics[-20:]  # Last 20 for each algorithm
                summary['algorithm_performance'][algorithm] = {
                    'average_slippage': np.mean([m['slippage'] for m in recent_metrics]),
                    'average_impact': np.mean([m['market_impact'] for m in recent_metrics]),
                    'average_duration': np.mean([m['duration'] for m in recent_metrics]),
                    'average_fill_rate': np.mean([m['fill_rate'] for m in recent_metrics]),
                    'execution_count': len(recent_metrics)
                }
        
        return summary

class SignalExecutionSystem:
    """Main signal-driven execution system"""
    
    def __init__(self, config: ExecutionConfig = None):
        self.config = config or ExecutionConfig()
        
        # Initialize components
        self.urgency_classifier = SignalUrgencyClassifier(self.config)
        self.algorithm_selector = ExecutionAlgorithmSelector(self.config)
        self.plan_generator = ExecutionPlanGenerator(self.config)
        self.monitor = ExecutionMonitor(self.config)
        
        # System state
        self.active_plans: Dict[str, ExecutionPlan] = {}
        
        logger.info("Signal Execution System initialized")
    
    def process_signal(self, characteristics: SignalCharacteristics) -> ExecutionPlan:
        """Process signal and generate execution plan"""
        
        # Classify urgency
        urgency = self.urgency_classifier.classify_urgency(characteristics)
        
        # Select algorithm
        algorithm = self.algorithm_selector.select_algorithm(characteristics, urgency)
        
        # Determine execution style
        execution_style = self.algorithm_selector.get_execution_style(algorithm, characteristics)
        
        # Generate execution plan
        plan = self.plan_generator.generate_plan(
            characteristics, algorithm, urgency, execution_style
        )
        
        # Store active plan
        self.active_plans[plan.plan_id] = plan
        
        logger.info(f"Generated execution plan {plan.plan_id}: {algorithm.value} for {plan.total_quantity} shares")
        
        return plan
    
    def execute_plan(self, plan: ExecutionPlan, arrival_price: float) -> str:
        """Execute a plan (returns execution ID for tracking)"""
        
        # Start monitoring
        self.monitor.start_execution(plan, arrival_price)
        
        # In a real implementation, this would interface with the order management system
        # For now, we'll simulate execution
        self._simulate_execution(plan, arrival_price)
        
        return plan.plan_id
    
    def _simulate_execution(self, plan: ExecutionPlan, arrival_price: float):
        """Simulate execution for demonstration purposes"""
        
        # Simulate execution over time
        import threading
        import time
        
        def simulate():
            remaining_qty = plan.total_quantity
            executed_qty = 0
            
            while remaining_qty > 0 and executed_qty < plan.total_quantity:
                # Simulate order execution
                slice_qty = min(plan.slice_size, remaining_qty)
                
                # Simulate price with some randomness
                price_noise = np.random.normal(0, 0.001)  # 10 bps noise
                execution_price = arrival_price * (1 + price_noise)
                
                # Update execution
                self.monitor.update_execution(
                    plan.plan_id, slice_qty, execution_price, f"order_{executed_qty}"
                )
                
                executed_qty += slice_qty
                remaining_qty -= slice_qty
                
                # Wait for next slice
                time.sleep(plan.slice_interval.total_seconds() / 10)  # Accelerated for demo
        
        # Start simulation in background thread
        thread = threading.Thread(target=simulate)
        thread.daemon = True
        thread.start()
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution status"""
        return self.monitor.get_execution_status(execution_id)
    
    def get_system_performance(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        performance = self.monitor.get_performance_summary()
        
        # Add system-level metrics
        performance.update({
            'active_executions': len(self.monitor.active_executions),
            'total_plans_generated': len(self.active_plans),
            'config': {
                'max_participation_rate': self.config.max_participation_rate,
                'max_slippage_tolerance': self.config.max_slippage_tolerance,
                'default_algorithm': self.config.default_algorithm.value
            }
        })
        
        return performance
    
    def optimize_parameters(self):
        """Optimize execution parameters based on historical performance"""
        performance = self.monitor.get_performance_summary()
        
        if not performance.get('algorithm_performance'):
            return
        
        # Simple optimization: adjust participation rates based on performance
        for algorithm, metrics in performance['algorithm_performance'].items():
            avg_impact = metrics.get('average_impact', 0)
            
            if avg_impact > self.config.impact_threshold * 1.5:
                # Reduce participation rate for high-impact algorithms
                logger.info(f"High impact detected for {algorithm}, consider reducing participation rate")
            elif avg_impact < self.config.impact_threshold * 0.5:
                # Can increase participation rate for low-impact algorithms
                logger.info(f"Low impact detected for {algorithm}, can increase participation rate")

# Factory function
def create_execution_system(config: ExecutionConfig = None) -> SignalExecutionSystem:
    """Create signal execution system"""
    return SignalExecutionSystem(config)

# Utility functions
def create_signal_characteristics(signal_type: SignalType, confidence: float,
                                target_quantity: float, **kwargs) -> SignalCharacteristics:
    """Create signal characteristics with defaults"""
    return SignalCharacteristics(
        signal_type=signal_type,
        confidence=confidence,
        urgency=SignalUrgency.MEDIUM,  # Will be classified automatically
        expected_duration=timedelta(minutes=30),
        market_regime=MarketRegime.UNKNOWN,
        signal_quality=SignalQuality.GOOD,
        current_volatility=0.02,
        current_spread=0.001,
        current_volume=1000,
        average_daily_volume=100000,
        target_quantity=target_quantity,
        current_position=0,
        risk_limit=target_quantity * 2,
        **kwargs
    )