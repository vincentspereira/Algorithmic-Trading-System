#!/usr/bin/env python3
"""
Execution Optimization for Pairs Trading

This module implements advanced execution optimization features including:
- Smart Order Routing: Minimize market impact across multiple venues
- Transaction Cost Analysis: Model and minimize execution costs
- Latency Optimization: High-frequency execution capabilities
- Slippage Modeling: More realistic backtesting assumptions

Author: Algorithmic Trading System
Version: 1.0.0
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime, timedelta
import time
import threading
from queue import Queue, PriorityQueue
import warnings
warnings.filterwarnings('ignore')

# Advanced libraries
try:
    from scipy.optimize import minimize, differential_evolution
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logging.warning("SciPy not available. Some optimization features will be limited.")

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    logging.warning("Plotting libraries not available. Visualization features disabled.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrderType(Enum):
    """Order types for execution"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    ICEBERG = "iceberg"
    TWAP = "twap"
    VWAP = "vwap"
    POV = "pov"  # Percentage of Volume
    IMPLEMENTATION_SHORTFALL = "implementation_shortfall"

class VenueType(Enum):
    """Trading venue types"""
    PRIMARY_EXCHANGE = "primary_exchange"
    DARK_POOL = "dark_pool"
    ECN = "ecn"
    ALTERNATIVE_TRADING_SYSTEM = "ats"
    CROSSING_NETWORK = "crossing_network"

class ExecutionUrgency(Enum):
    """Execution urgency levels"""
    LOW = "low"  # Patient execution over hours/days
    MEDIUM = "medium"  # Moderate execution over minutes/hours
    HIGH = "high"  # Aggressive execution over seconds/minutes
    CRITICAL = "critical"  # Immediate execution

@dataclass
class VenueCharacteristics:
    """Trading venue characteristics"""
    venue_id: str
    venue_type: VenueType
    typical_spread: float  # Basis points
    market_impact_coefficient: float
    latency_ms: float
    fill_probability: float
    dark_pool_ratio: float  # For dark pools
    min_order_size: int
    max_order_size: int
    trading_hours: Tuple[int, int]  # (start_hour, end_hour)
    fees: Dict[str, float]  # Various fee types
    liquidity_score: float  # 0-1 scale

@dataclass
class OrderSlice:
    """Individual order slice for execution"""
    slice_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: int
    order_type: OrderType
    venue: str
    price_limit: Optional[float] = None
    time_in_force: str = "DAY"
    urgency: ExecutionUrgency = ExecutionUrgency.MEDIUM
    parent_order_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    expected_fill_time: Optional[datetime] = None
    max_participation_rate: float = 0.1  # Max % of volume

@dataclass
class ExecutionResult:
    """Execution result for an order slice"""
    slice_id: str
    filled_quantity: int
    average_fill_price: float
    total_cost: float
    execution_time: float  # Seconds
    venue: str
    slippage: float  # Basis points
    market_impact: float  # Basis points
    fees: float
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class TransactionCostComponents:
    """Breakdown of transaction costs"""
    spread_cost: float  # Bid-ask spread cost
    market_impact: float  # Price impact from order
    timing_cost: float  # Opportunity cost of delayed execution
    fees_and_commissions: float  # Explicit costs
    slippage: float  # Execution shortfall
    total_cost: float  # Sum of all components
    cost_basis_points: float  # Total cost in basis points

@dataclass
class LatencyMetrics:
    """Latency measurement metrics"""
    order_to_market_latency: float  # Microseconds
    market_data_latency: float  # Microseconds
    processing_latency: float  # Microseconds
    network_latency: float  # Microseconds
    total_latency: float  # Microseconds
    timestamp: datetime = field(default_factory=datetime.now)

class MarketImpactModel:
    """Market impact modeling for execution optimization"""
    
    def __init__(self, model_type: str = "almgren_chriss"):
        self.model_type = model_type
        self.calibrated_parameters = {}
        self.historical_impacts = []
        
    def calibrate_model(self, historical_executions: List[ExecutionResult], 
                       market_data: pd.DataFrame) -> Dict[str, float]:
        """Calibrate market impact model from historical data"""
        
        if len(historical_executions) < 50:
            logger.warning("Insufficient data for model calibration")
            return self._get_default_parameters()
        
        try:
            # Extract features for calibration
            impacts = []
            order_sizes = []
            participation_rates = []
            volatilities = []
            
            for execution in historical_executions:
                if execution.market_impact > 0:
                    impacts.append(execution.market_impact)
                    order_sizes.append(execution.filled_quantity)
                    
                    # Calculate participation rate (simplified)
                    participation_rates.append(min(0.5, execution.filled_quantity / 10000))
                    
                    # Get volatility around execution time
                    volatilities.append(self._get_volatility_at_time(market_data, execution.timestamp))
            
            if len(impacts) < 10:
                return self._get_default_parameters()
            
            # Fit model based on type
            if self.model_type == "almgren_chriss":
                return self._calibrate_almgren_chriss(impacts, order_sizes, participation_rates, volatilities)
            elif self.model_type == "linear":
                return self._calibrate_linear_model(impacts, order_sizes, participation_rates)
            elif self.model_type == "square_root":
                return self._calibrate_square_root_model(impacts, order_sizes, participation_rates, volatilities)
            else:
                return self._get_default_parameters()
                
        except Exception as e:
            logger.error(f"Model calibration failed: {e}")
            return self._get_default_parameters()
    
    def _calibrate_almgren_chriss(self, impacts: List[float], order_sizes: List[int], 
                                 participation_rates: List[float], volatilities: List[float]) -> Dict[str, float]:
        """Calibrate Almgren-Chriss model parameters"""
        
        # Convert to numpy arrays
        impacts = np.array(impacts)
        order_sizes = np.array(order_sizes)
        participation_rates = np.array(participation_rates)
        volatilities = np.array(volatilities)
        
        # Almgren-Chriss model: Impact = η * (σ/σ₀) * (x/V)^α
        # Where η is permanent impact, σ is volatility, x is order size, V is volume
        
        def objective(params):
            eta, alpha = params
            predicted_impacts = eta * (volatilities / np.mean(volatilities)) * (participation_rates ** alpha)
            return np.mean((impacts - predicted_impacts) ** 2)
        
        if SCIPY_AVAILABLE:
            result = minimize(objective, x0=[50.0, 0.6], bounds=[(1.0, 200.0), (0.1, 1.0)])
            eta, alpha = result.x
        else:
            # Simple linear regression fallback
            eta = np.mean(impacts) / np.mean(participation_rates)
            alpha = 0.6
        
        self.calibrated_parameters = {
            'eta': eta,
            'alpha': alpha,
            'model_type': 'almgren_chriss'
        }
        
        return self.calibrated_parameters
    
    def _calibrate_linear_model(self, impacts: List[float], order_sizes: List[int], 
                               participation_rates: List[float]) -> Dict[str, float]:
        """Calibrate simple linear impact model"""
        
        impacts = np.array(impacts)
        participation_rates = np.array(participation_rates)
        
        # Linear model: Impact = β * participation_rate
        if len(participation_rates) > 0 and np.var(participation_rates) > 0:
            beta = np.cov(impacts, participation_rates)[0, 1] / np.var(participation_rates)
        else:
            beta = 50.0  # Default
        
        self.calibrated_parameters = {
            'beta': beta,
            'model_type': 'linear'
        }
        
        return self.calibrated_parameters
    
    def _calibrate_square_root_model(self, impacts: List[float], order_sizes: List[int], 
                                    participation_rates: List[float], volatilities: List[float]) -> Dict[str, float]:
        """Calibrate square root impact model"""
        
        impacts = np.array(impacts)
        participation_rates = np.array(participation_rates)
        volatilities = np.array(volatilities)
        
        # Square root model: Impact = γ * σ * sqrt(participation_rate)
        sqrt_participation = np.sqrt(participation_rates)
        
        if len(sqrt_participation) > 0 and np.var(sqrt_participation * volatilities) > 0:
            gamma = np.cov(impacts, sqrt_participation * volatilities)[0, 1] / np.var(sqrt_participation * volatilities)
        else:
            gamma = 10.0  # Default
        
        self.calibrated_parameters = {
            'gamma': gamma,
            'model_type': 'square_root'
        }
        
        return self.calibrated_parameters
    
    def _get_default_parameters(self) -> Dict[str, float]:
        """Get default model parameters"""
        if self.model_type == "almgren_chriss":
            return {'eta': 50.0, 'alpha': 0.6, 'model_type': 'almgren_chriss'}
        elif self.model_type == "linear":
            return {'beta': 50.0, 'model_type': 'linear'}
        elif self.model_type == "square_root":
            return {'gamma': 10.0, 'model_type': 'square_root'}
        else:
            return {'beta': 50.0, 'model_type': 'linear'}
    
    def _get_volatility_at_time(self, market_data: pd.DataFrame, timestamp: datetime) -> float:
        """Get volatility estimate at specific time"""
        try:
            # Find closest market data point
            if 'timestamp' in market_data.columns:
                closest_idx = (market_data['timestamp'] - timestamp).abs().idxmin()
                if 'volatility' in market_data.columns:
                    return market_data.loc[closest_idx, 'volatility']
                elif 'returns' in market_data.columns:
                    # Calculate rolling volatility
                    returns = market_data['returns']
                    vol = returns.rolling(20).std().iloc[closest_idx]
                    return vol if not pd.isna(vol) else 0.02
            
            return 0.02  # Default volatility
            
        except Exception:
            return 0.02  # Default volatility
    
    def predict_market_impact(self, order_size: int, participation_rate: float, 
                            volatility: float = 0.02, adv: float = 1000000) -> float:
        """Predict market impact for given order characteristics"""
        
        if not self.calibrated_parameters:
            self.calibrated_parameters = self._get_default_parameters()
        
        model_type = self.calibrated_parameters.get('model_type', 'linear')
        
        if model_type == 'almgren_chriss':
            eta = self.calibrated_parameters.get('eta', 50.0)
            alpha = self.calibrated_parameters.get('alpha', 0.6)
            impact = eta * (volatility / 0.02) * (participation_rate ** alpha)
            
        elif model_type == 'linear':
            beta = self.calibrated_parameters.get('beta', 50.0)
            impact = beta * participation_rate
            
        elif model_type == 'square_root':
            gamma = self.calibrated_parameters.get('gamma', 10.0)
            impact = gamma * volatility * np.sqrt(participation_rate)
            
        else:
            impact = 50.0 * participation_rate  # Fallback
        
        return max(0.0, impact)  # Ensure non-negative impact

class SmartOrderRouter:
    """Smart order routing across multiple venues"""
    
    def __init__(self):
        self.venues = {}
        self.routing_rules = {}
        self.execution_history = []
        self.market_impact_model = MarketImpactModel()
        
    def add_venue(self, venue: VenueCharacteristics):
        """Add trading venue to router"""
        self.venues[venue.venue_id] = venue
        logger.info(f"Added venue: {venue.venue_id} ({venue.venue_type.value})")
    
    def set_routing_rules(self, rules: Dict[str, Any]):
        """Set routing rules and preferences"""
        self.routing_rules = rules
    
    def optimize_order_routing(self, symbol: str, side: str, total_quantity: int, 
                             urgency: ExecutionUrgency = ExecutionUrgency.MEDIUM,
                             max_market_impact: float = 100.0) -> List[OrderSlice]:
        """Optimize order routing across venues"""
        
        if not self.venues:
            logger.warning("No venues available for routing")
            return []
        
        # Filter available venues based on order characteristics
        available_venues = self._filter_venues(symbol, total_quantity, urgency)
        
        if not available_venues:
            logger.warning("No suitable venues found")
            return []
        
        # Optimize allocation across venues
        venue_allocations = self._optimize_venue_allocation(
            available_venues, total_quantity, max_market_impact
        )
        
        # Create order slices
        order_slices = []
        slice_counter = 0
        
        for venue_id, allocation in venue_allocations.items():
            if allocation['quantity'] > 0:
                # Determine optimal order type for venue
                order_type = self._select_order_type(venue_id, urgency, allocation['quantity'])
                
                # Create time slices if needed
                time_slices = self._create_time_slices(
                    venue_id, allocation['quantity'], urgency, order_type
                )
                
                for time_slice in time_slices:
                    slice_counter += 1
                    order_slice = OrderSlice(
                        slice_id=f"{symbol}_{slice_counter:04d}",
                        symbol=symbol,
                        side=side,
                        quantity=time_slice['quantity'],
                        order_type=order_type,
                        venue=venue_id,
                        price_limit=time_slice.get('price_limit'),
                        urgency=urgency,
                        expected_fill_time=time_slice.get('expected_fill_time'),
                        max_participation_rate=time_slice.get('participation_rate', 0.1)
                    )
                    order_slices.append(order_slice)
        
        return order_slices
    
    def _filter_venues(self, symbol: str, quantity: int, urgency: ExecutionUrgency) -> Dict[str, VenueCharacteristics]:
        """Filter venues based on order requirements"""
        available_venues = {}
        
        for venue_id, venue in self.venues.items():
            # Check quantity limits
            if quantity < venue.min_order_size or quantity > venue.max_order_size:
                continue
            
            # Check urgency vs latency
            if urgency == ExecutionUrgency.CRITICAL and venue.latency_ms > 10:
                continue
            
            # Check trading hours (simplified)
            current_hour = datetime.now().hour
            if not (venue.trading_hours[0] <= current_hour <= venue.trading_hours[1]):
                continue
            
            available_venues[venue_id] = venue
        
        return available_venues
    
    def _optimize_venue_allocation(self, venues: Dict[str, VenueCharacteristics], 
                                 total_quantity: int, max_market_impact: float) -> Dict[str, Dict[str, Any]]:
        """Optimize quantity allocation across venues"""
        
        if len(venues) == 1:
            venue_id = list(venues.keys())[0]
            return {venue_id: {'quantity': total_quantity, 'expected_cost': 0.0}}
        
        # Multi-venue optimization
        venue_ids = list(venues.keys())
        n_venues = len(venue_ids)
        
        def objective(allocations):
            """Minimize total execution cost"""
            total_cost = 0.0
            
            for i, venue_id in enumerate(venue_ids):
                quantity = int(allocations[i] * total_quantity)
                if quantity > 0:
                    venue = venues[venue_id]
                    
                    # Estimate costs
                    spread_cost = venue.typical_spread * quantity
                    
                    # Market impact
                    participation_rate = min(0.5, quantity / 100000)  # Simplified
                    market_impact = self.market_impact_model.predict_market_impact(
                        quantity, participation_rate
                    )
                    impact_cost = market_impact * quantity / 10000  # Convert from bps
                    
                    # Fees
                    fee_cost = venue.fees.get('per_share', 0.001) * quantity
                    
                    # Liquidity penalty
                    liquidity_penalty = (1 - venue.liquidity_score) * quantity * 0.01
                    
                    total_cost += spread_cost + impact_cost + fee_cost + liquidity_penalty
            
            return total_cost
        
        def constraint(allocations):
            """Ensure allocations sum to 1"""
            return np.sum(allocations) - 1.0
        
        # Optimize allocation
        if SCIPY_AVAILABLE:
            from scipy.optimize import minimize
            
            initial_guess = np.ones(n_venues) / n_venues
            bounds = [(0.0, 1.0) for _ in range(n_venues)]
            constraints = {'type': 'eq', 'fun': constraint}
            
            result = minimize(objective, initial_guess, bounds=bounds, constraints=constraints)
            optimal_allocations = result.x
        else:
            # Equal allocation fallback
            optimal_allocations = np.ones(n_venues) / n_venues
        
        # Convert to venue allocations
        venue_allocations = {}
        for i, venue_id in enumerate(venue_ids):
            quantity = int(optimal_allocations[i] * total_quantity)
            venue_allocations[venue_id] = {
                'quantity': quantity,
                'allocation_ratio': optimal_allocations[i],
                'expected_cost': 0.0  # Could calculate detailed cost here
            }
        
        return venue_allocations
    
    def _select_order_type(self, venue_id: str, urgency: ExecutionUrgency, quantity: int) -> OrderType:
        """Select optimal order type for venue and urgency"""
        
        venue = self.venues[venue_id]
        
        if urgency == ExecutionUrgency.CRITICAL:
            return OrderType.MARKET
        elif urgency == ExecutionUrgency.HIGH:
            if venue.venue_type == VenueType.DARK_POOL:
                return OrderType.LIMIT
            else:
                return OrderType.MARKET
        elif urgency == ExecutionUrgency.MEDIUM:
            if quantity > 10000:  # Large order
                return OrderType.TWAP
            else:
                return OrderType.LIMIT
        else:  # LOW urgency
            if quantity > 50000:  # Very large order
                return OrderType.VWAP
            else:
                return OrderType.TWAP
    
    def _create_time_slices(self, venue_id: str, quantity: int, urgency: ExecutionUrgency, 
                           order_type: OrderType) -> List[Dict[str, Any]]:
        """Create time-based order slices"""
        
        if order_type in [OrderType.MARKET, OrderType.LIMIT]:
            # Single slice for immediate orders
            return [{
                'quantity': quantity,
                'expected_fill_time': datetime.now() + timedelta(seconds=30),
                'participation_rate': min(0.3, quantity / 50000)
            }]
        
        elif order_type == OrderType.TWAP:
            # Time-weighted average price slicing
            if urgency == ExecutionUrgency.LOW:
                n_slices = min(20, max(5, quantity // 1000))
                duration_hours = 4
            else:
                n_slices = min(10, max(3, quantity // 2000))
                duration_hours = 1
            
            slice_size = quantity // n_slices
            remainder = quantity % n_slices
            
            slices = []
            for i in range(n_slices):
                slice_quantity = slice_size + (1 if i < remainder else 0)
                expected_time = datetime.now() + timedelta(hours=duration_hours * i / n_slices)
                
                slices.append({
                    'quantity': slice_quantity,
                    'expected_fill_time': expected_time,
                    'participation_rate': 0.05  # Conservative for TWAP
                })
            
            return slices
        
        elif order_type == OrderType.VWAP:
            # Volume-weighted average price slicing
            # Simplified: assume higher participation during high volume periods
            n_slices = min(15, max(4, quantity // 5000))
            
            slices = []
            for i in range(n_slices):
                # Vary participation rate (higher in middle of day)
                participation_rate = 0.03 + 0.07 * np.sin(np.pi * i / (n_slices - 1))
                slice_quantity = int(quantity * participation_rate / np.sum(
                    [0.03 + 0.07 * np.sin(np.pi * j / (n_slices - 1)) for j in range(n_slices)]
                ))
                
                expected_time = datetime.now() + timedelta(minutes=30 * i)
                
                slices.append({
                    'quantity': slice_quantity,
                    'expected_fill_time': expected_time,
                    'participation_rate': participation_rate
                })
            
            return slices
        
        else:
            # Default single slice
            return [{
                'quantity': quantity,
                'expected_fill_time': datetime.now() + timedelta(minutes=5),
                'participation_rate': 0.1
            }]

class TransactionCostAnalyzer:
    """Comprehensive transaction cost analysis"""
    
    def __init__(self):
        self.cost_history = []
        self.benchmark_costs = {}
        self.cost_models = {}
        
    def analyze_execution_costs(self, execution_results: List[ExecutionResult], 
                              benchmark_price: float, order_quantity: int) -> TransactionCostComponents:
        """Analyze comprehensive transaction costs"""
        
        if not execution_results:
            return TransactionCostComponents(
                spread_cost=0.0, market_impact=0.0, timing_cost=0.0,
                fees_and_commissions=0.0, slippage=0.0, total_cost=0.0, cost_basis_points=0.0
            )
        
        # Calculate weighted average execution price
        total_quantity = sum(r.filled_quantity for r in execution_results)
        if total_quantity == 0:
            return TransactionCostComponents(
                spread_cost=0.0, market_impact=0.0, timing_cost=0.0,
                fees_and_commissions=0.0, slippage=0.0, total_cost=0.0, cost_basis_points=0.0
            )
        
        weighted_avg_price = sum(r.average_fill_price * r.filled_quantity for r in execution_results) / total_quantity
        
        # 1. Spread Cost (estimated)
        typical_spread = 0.05  # 5 cents default
        spread_cost = typical_spread * total_quantity / 2  # Half spread
        
        # 2. Market Impact
        market_impact_bps = sum(r.market_impact * r.filled_quantity for r in execution_results) / total_quantity
        market_impact_cost = market_impact_bps * weighted_avg_price * total_quantity / 10000
        
        # 3. Timing Cost (opportunity cost)
        price_difference = weighted_avg_price - benchmark_price
        timing_cost = abs(price_difference) * total_quantity
        
        # 4. Fees and Commissions
        total_fees = sum(r.fees for r in execution_results)
        
        # 5. Slippage (execution shortfall)
        slippage_cost = abs(weighted_avg_price - benchmark_price) * total_quantity
        
        # Total cost
        total_cost = spread_cost + market_impact_cost + timing_cost + total_fees + slippage_cost
        
        # Convert to basis points
        notional_value = benchmark_price * order_quantity
        cost_basis_points = (total_cost / notional_value) * 10000 if notional_value > 0 else 0
        
        return TransactionCostComponents(
            spread_cost=spread_cost,
            market_impact=market_impact_cost,
            timing_cost=timing_cost,
            fees_and_commissions=total_fees,
            slippage=slippage_cost,
            total_cost=total_cost,
            cost_basis_points=cost_basis_points
        )
    
    def benchmark_execution(self, execution_results: List[ExecutionResult], 
                          benchmark_strategy: str = "vwap") -> Dict[str, float]:
        """Benchmark execution against standard strategies"""
        
        if not execution_results:
            return {'relative_performance': 0.0, 'benchmark_cost': 0.0}
        
        # Calculate actual execution metrics
        total_quantity = sum(r.filled_quantity for r in execution_results)
        weighted_avg_price = sum(r.average_fill_price * r.filled_quantity for r in execution_results) / total_quantity
        total_execution_time = max(r.execution_time for r in execution_results)
        
        # Estimate benchmark costs
        if benchmark_strategy == "vwap":
            # VWAP benchmark (simplified)
            benchmark_cost_bps = 15.0  # Typical VWAP cost
        elif benchmark_strategy == "twap":
            # TWAP benchmark
            benchmark_cost_bps = 20.0  # Typical TWAP cost
        elif benchmark_strategy == "market":
            # Market order benchmark
            benchmark_cost_bps = 50.0  # Typical market order cost
        else:
            benchmark_cost_bps = 25.0  # Default
        
        # Calculate actual cost in basis points
        actual_cost_bps = sum(r.market_impact for r in execution_results) / len(execution_results)
        
        # Relative performance
        relative_performance = (benchmark_cost_bps - actual_cost_bps) / benchmark_cost_bps if benchmark_cost_bps > 0 else 0
        
        return {
            'relative_performance': relative_performance,
            'benchmark_cost_bps': benchmark_cost_bps,
            'actual_cost_bps': actual_cost_bps,
            'cost_savings_bps': benchmark_cost_bps - actual_cost_bps
        }
    
    def optimize_execution_strategy(self, symbol: str, quantity: int, urgency: ExecutionUrgency,
                                  market_conditions: Dict[str, float]) -> Dict[str, Any]:
        """Optimize execution strategy based on market conditions"""
        
        volatility = market_conditions.get('volatility', 0.02)
        volume = market_conditions.get('average_daily_volume', 1000000)
        spread = market_conditions.get('bid_ask_spread', 0.05)
        
        # Calculate participation rate constraint
        max_participation = min(0.3, 0.1 + 0.2 * (1 - volatility / 0.05))  # Lower participation in high vol
        
        # Estimate optimal execution time
        if urgency == ExecutionUrgency.CRITICAL:
            optimal_duration_minutes = 1
        elif urgency == ExecutionUrgency.HIGH:
            optimal_duration_minutes = 15
        elif urgency == ExecutionUrgency.MEDIUM:
            optimal_duration_minutes = 60
        else:
            optimal_duration_minutes = 240
        
        # Adjust for market conditions
        if volatility > 0.03:  # High volatility
            optimal_duration_minutes *= 0.7  # Execute faster
        if volume < 500000:  # Low volume
            optimal_duration_minutes *= 1.5  # Execute slower
        
        # Select optimal strategy
        participation_rate = min(max_participation, quantity / (volume * optimal_duration_minutes / 390))  # 390 min trading day
        
        if participation_rate > 0.2:
            recommended_strategy = OrderType.VWAP
        elif participation_rate > 0.1:
            recommended_strategy = OrderType.TWAP
        elif urgency in [ExecutionUrgency.CRITICAL, ExecutionUrgency.HIGH]:
            recommended_strategy = OrderType.MARKET
        else:
            recommended_strategy = OrderType.LIMIT
        
        # Estimate costs
        estimated_market_impact = self._estimate_market_impact(quantity, participation_rate, volatility)
        estimated_spread_cost = spread * quantity / 2
        estimated_total_cost = estimated_market_impact + estimated_spread_cost
        
        return {
            'recommended_strategy': recommended_strategy,
            'optimal_duration_minutes': optimal_duration_minutes,
            'max_participation_rate': max_participation,
            'estimated_cost_bps': estimated_total_cost / (quantity * market_conditions.get('price', 100)) * 10000,
            'risk_factors': self._assess_execution_risks(market_conditions)
        }
    
    def _estimate_market_impact(self, quantity: int, participation_rate: float, volatility: float) -> float:
        """Estimate market impact cost"""
        # Simplified square-root model
        impact_bps = 10 * volatility * np.sqrt(participation_rate) * 100  # Convert to basis points
        return impact_bps * quantity / 10000
    
    def _assess_execution_risks(self, market_conditions: Dict[str, float]) -> List[str]:
        """Assess execution risks based on market conditions"""
        risks = []
        
        volatility = market_conditions.get('volatility', 0.02)
        volume = market_conditions.get('average_daily_volume', 1000000)
        spread = market_conditions.get('bid_ask_spread', 0.05)
        
        if volatility > 0.04:
            risks.append("High volatility - increased market impact risk")
        
        if volume < 100000:
            risks.append("Low liquidity - execution may be difficult")
        
        if spread > 0.10:
            risks.append("Wide spreads - high crossing costs")
        
        # Time-based risks
        current_hour = datetime.now().hour
        if current_hour < 10 or current_hour > 15:
            risks.append("Outside core trading hours - reduced liquidity")
        
        return risks

class LatencyOptimizer:
    """Latency optimization for high-frequency execution"""
    
    def __init__(self):
        self.latency_measurements = []
        self.optimization_settings = {}
        self.performance_targets = {
            'order_to_market_latency_us': 100,  # 100 microseconds
            'market_data_latency_us': 50,       # 50 microseconds
            'processing_latency_us': 25,        # 25 microseconds
            'total_latency_us': 200             # 200 microseconds total
        }
    
    def measure_latency(self, operation: str) -> LatencyMetrics:
        """Measure latency for specific operation"""
        
        start_time = time.perf_counter_ns()
        
        # Simulate operation (in real implementation, this would be actual operation)
        if operation == "order_submission":
            time.sleep(0.0001)  # 100 microseconds
        elif operation == "market_data_processing":
            time.sleep(0.00005)  # 50 microseconds
        elif operation == "risk_check":
            time.sleep(0.00002)  # 20 microseconds
        
        end_time = time.perf_counter_ns()
        
        # Calculate latency components (simplified)
        total_latency_us = (end_time - start_time) / 1000  # Convert to microseconds
        
        metrics = LatencyMetrics(
            order_to_market_latency=total_latency_us * 0.6,
            market_data_latency=total_latency_us * 0.2,
            processing_latency=total_latency_us * 0.15,
            network_latency=total_latency_us * 0.05,
            total_latency=total_latency_us
        )
        
        self.latency_measurements.append(metrics)
        return metrics
    
    def optimize_latency(self) -> Dict[str, Any]:
        """Optimize system latency"""
        
        if len(self.latency_measurements) < 10:
            return {'status': 'insufficient_data', 'recommendations': []}
        
        # Analyze recent measurements
        recent_measurements = self.latency_measurements[-100:]  # Last 100 measurements
        
        avg_total_latency = np.mean([m.total_latency for m in recent_measurements])
        p95_total_latency = np.percentile([m.total_latency for m in recent_measurements], 95)
        
        recommendations = []
        
        # Check against targets
        if avg_total_latency > self.performance_targets['total_latency_us']:
            recommendations.append("Total latency exceeds target - investigate bottlenecks")
        
        # Identify bottlenecks
        avg_order_latency = np.mean([m.order_to_market_latency for m in recent_measurements])
        avg_data_latency = np.mean([m.market_data_latency for m in recent_measurements])
        avg_processing_latency = np.mean([m.processing_latency for m in recent_measurements])
        
        if avg_order_latency > self.performance_targets['order_to_market_latency_us']:
            recommendations.append("Order submission latency high - optimize order routing")
        
        if avg_data_latency > self.performance_targets['market_data_latency_us']:
            recommendations.append("Market data latency high - optimize data feed")
        
        if avg_processing_latency > self.performance_targets['processing_latency_us']:
            recommendations.append("Processing latency high - optimize algorithms")
        
        # Performance optimizations
        optimizations = self._generate_optimization_recommendations(recent_measurements)
        
        return {
            'status': 'analyzed',
            'avg_latency_us': avg_total_latency,
            'p95_latency_us': p95_total_latency,
            'recommendations': recommendations,
            'optimizations': optimizations,
            'performance_vs_target': {
                'total_latency_ratio': avg_total_latency / self.performance_targets['total_latency_us'],
                'meets_target': avg_total_latency <= self.performance_targets['total_latency_us']
            }
        }
    
    def _generate_optimization_recommendations(self, measurements: List[LatencyMetrics]) -> List[str]:
        """Generate specific optimization recommendations"""
        optimizations = []
        
        # Analyze latency distribution
        total_latencies = [m.total_latency for m in measurements]
        latency_std = np.std(total_latencies)
        
        if latency_std > np.mean(total_latencies) * 0.3:
            optimizations.append("High latency variance - implement latency smoothing")
        
        # Component-specific optimizations
        order_latencies = [m.order_to_market_latency for m in measurements]
        if np.mean(order_latencies) > 150:  # 150 microseconds
            optimizations.append("Implement direct market access (DMA) for faster order routing")
        
        data_latencies = [m.market_data_latency for m in measurements]
        if np.mean(data_latencies) > 75:  # 75 microseconds
            optimizations.append("Optimize market data parsing and processing")
        
        processing_latencies = [m.processing_latency for m in measurements]
        if np.mean(processing_latencies) > 50:  # 50 microseconds
            optimizations.append("Implement algorithmic optimizations and caching")
        
        # Infrastructure optimizations
        optimizations.extend([
            "Consider co-location services for reduced network latency",
            "Implement kernel bypass networking (DPDK)",
            "Use CPU affinity and real-time scheduling",
            "Optimize memory allocation and garbage collection",
            "Implement lock-free data structures"
        ])
        
        return optimizations[:5]  # Return top 5 recommendations

class SlippageModel:
    """Advanced slippage modeling for realistic backtesting"""
    
    def __init__(self):
        self.historical_slippage = []
        self.model_parameters = {}
        self.market_regimes = {}
        
    def calibrate_slippage_model(self, execution_data: List[ExecutionResult], 
                                market_data: pd.DataFrame) -> Dict[str, float]:
        """Calibrate slippage model from historical execution data"""
        
        if len(execution_data) < 30:
            return self._get_default_slippage_parameters()
        
        try:
            # Extract slippage observations
            slippages = []
            order_sizes = []
            volatilities = []
            spreads = []
            
            for execution in execution_data:
                if execution.slippage is not None:
                    slippages.append(execution.slippage)
                    order_sizes.append(execution.filled_quantity)
                    
                    # Get market conditions at execution time
                    vol = self._get_market_condition(market_data, execution.timestamp, 'volatility', 0.02)
                    spread = self._get_market_condition(market_data, execution.timestamp, 'spread', 0.05)
                    
                    volatilities.append(vol)
                    spreads.append(spread)
            
            if len(slippages) < 10:
                return self._get_default_slippage_parameters()
            
            # Fit slippage model: Slippage = α + β*OrderSize + γ*Volatility + δ*Spread + ε
            slippages = np.array(slippages)
            order_sizes = np.array(order_sizes)
            volatilities = np.array(volatilities)
            spreads = np.array(spreads)
            
            # Normalize order sizes
            normalized_sizes = order_sizes / np.mean(order_sizes)
            
            # Simple linear regression (could use more sophisticated methods)
            X = np.column_stack([np.ones(len(slippages)), normalized_sizes, volatilities, spreads])
            
            if SCIPY_AVAILABLE:
                from scipy.linalg import lstsq
                coefficients, _, _, _ = lstsq(X, slippages)
                alpha, beta, gamma, delta = coefficients
            else:
                # Fallback to simple correlations
                alpha = np.mean(slippages)
                beta = np.corrcoef(slippages, normalized_sizes)[0, 1] * np.std(slippages) / np.std(normalized_sizes)
                gamma = np.corrcoef(slippages, volatilities)[0, 1] * np.std(slippages) / np.std(volatilities)
                delta = np.corrcoef(slippages, spreads)[0, 1] * np.std(slippages) / np.std(spreads)
            
            # Calculate model fit
            predicted_slippage = alpha + beta * normalized_sizes + gamma * volatilities + delta * spreads
            r_squared = 1 - np.var(slippages - predicted_slippage) / np.var(slippages)
            
            self.model_parameters = {
                'alpha': alpha,
                'beta': beta,
                'gamma': gamma,
                'delta': delta,
                'r_squared': r_squared,
                'mean_order_size': np.mean(order_sizes)
            }
            
            return self.model_parameters
            
        except Exception as e:
            logger.error(f"Slippage model calibration failed: {e}")
            return self._get_default_slippage_parameters()
    
    def _get_default_slippage_parameters(self) -> Dict[str, float]:
        """Get default slippage model parameters"""
        return {
            'alpha': 2.0,      # Base slippage (bps)
            'beta': 1.5,       # Order size coefficient
            'gamma': 100.0,    # Volatility coefficient
            'delta': 50.0,     # Spread coefficient
            'r_squared': 0.3,
            'mean_order_size': 10000
        }
    
    def _get_market_condition(self, market_data: pd.DataFrame, timestamp: datetime, 
                            condition: str, default_value: float) -> float:
        """Get market condition at specific timestamp"""
        try:
            if 'timestamp' in market_data.columns:
                closest_idx = (market_data['timestamp'] - timestamp).abs().idxmin()
                if condition in market_data.columns:
                    return market_data.loc[closest_idx, condition]
            return default_value
        except Exception:
            return default_value
    
    def predict_slippage(self, order_size: int, volatility: float, spread: float, 
                        order_type: OrderType = OrderType.MARKET) -> float:
        """Predict slippage for given order characteristics"""
        
        if not self.model_parameters:
            self.model_parameters = self._get_default_slippage_parameters()
        
        # Normalize order size
        normalized_size = order_size / self.model_parameters['mean_order_size']
        
        # Base slippage prediction
        predicted_slippage = (
            self.model_parameters['alpha'] +
            self.model_parameters['beta'] * normalized_size +
            self.model_parameters['gamma'] * volatility +
            self.model_parameters['delta'] * spread
        )
        
        # Adjust for order type
        if order_type == OrderType.MARKET:
            slippage_multiplier = 1.0
        elif order_type == OrderType.LIMIT:
            slippage_multiplier = 0.3  # Lower slippage for limit orders
        elif order_type in [OrderType.TWAP, OrderType.VWAP]:
            slippage_multiplier = 0.5  # Moderate slippage for algorithmic orders
        else:
            slippage_multiplier = 0.7
        
        # Add random component
        random_component = np.random.normal(0, predicted_slippage * 0.2)  # 20% random variation
        
        final_slippage = max(0.0, predicted_slippage * slippage_multiplier + random_component)
        
        return final_slippage
    
    def simulate_realistic_execution(self, order_size: int, market_conditions: Dict[str, float],
                                   execution_strategy: OrderType = OrderType.TWAP) -> Dict[str, Any]:
        """Simulate realistic execution with slippage"""
        
        volatility = market_conditions.get('volatility', 0.02)
        spread = market_conditions.get('spread', 0.05)
        price = market_conditions.get('price', 100.0)
        
        # Predict slippage
        predicted_slippage_bps = self.predict_slippage(order_size, volatility, spread, execution_strategy)
        
        # Convert to dollar amount
        slippage_cost = predicted_slippage_bps * price * order_size / 10000
        
        # Simulate execution time based on strategy
        if execution_strategy == OrderType.MARKET:
            execution_time_seconds = np.random.exponential(30)  # Average 30 seconds
        elif execution_strategy in [OrderType.TWAP, OrderType.VWAP]:
            execution_time_seconds = np.random.exponential(1800)  # Average 30 minutes
        else:
            execution_time_seconds = np.random.exponential(300)  # Average 5 minutes
        
        # Calculate fill probability
        if execution_strategy == OrderType.MARKET:
            fill_probability = 0.98
        elif execution_strategy == OrderType.LIMIT:
            fill_probability = 0.75  # Lower for limit orders
        else:
            fill_probability = 0.90
        
        # Simulate partial fills
        if np.random.random() > fill_probability:
            filled_quantity = int(order_size * np.random.uniform(0.5, 0.9))
        else:
            filled_quantity = order_size
        
        return {
            'filled_quantity': filled_quantity,
            'slippage_bps': predicted_slippage_bps,
            'slippage_cost': slippage_cost,
            'execution_time_seconds': execution_time_seconds,
            'fill_probability': fill_probability,
            'average_fill_price': price + (predicted_slippage_bps * price / 10000)
        }

# Example usage and testing
def test_execution_optimization():
    """Test the execution optimization components"""
    print("Testing Execution Optimization")
    print("=" * 50)
    
    # 1. Test Smart Order Router
    print("\n1. Testing Smart Order Router:")
    router = SmartOrderRouter()
    
    # Add sample venues
    venues = [
        VenueCharacteristics(
            venue_id="NYSE",
            venue_type=VenueType.PRIMARY_EXCHANGE,
            typical_spread=5.0,
            market_impact_coefficient=1.0,
            latency_ms=2.0,
            fill_probability=0.95,
            dark_pool_ratio=0.0,
            min_order_size=100,
            max_order_size=1000000,
            trading_hours=(9, 16),
            fees={'per_share': 0.001},
            liquidity_score=0.9
        ),
        VenueCharacteristics(
            venue_id="DARK_POOL_1",
            venue_type=VenueType.DARK_POOL,
            typical_spread=3.0,
            market_impact_coefficient=0.5,
            latency_ms=5.0,
            fill_probability=0.70,
            dark_pool_ratio=1.0,
            min_order_size=500,
            max_order_size=500000,
            trading_hours=(9, 16),
            fees={'per_share': 0.0005},
            liquidity_score=0.7
        )
    ]
    
    for venue in venues:
        router.add_venue(venue)
    
    # Optimize order routing
    order_slices = router.optimize_order_routing(
        symbol="AAPL",
        side="buy",
        total_quantity=50000,
        urgency=ExecutionUrgency.MEDIUM
    )
    
    print(f"Generated {len(order_slices)} order slices:")
    for i, slice_obj in enumerate(order_slices[:3], 1):  # Show first 3
        print(f"  Slice {i}: {slice_obj.quantity} shares via {slice_obj.venue} ({slice_obj.order_type.value})")
    
    # 2. Test Transaction Cost Analyzer
    print("\n2. Testing Transaction Cost Analyzer:")
    cost_analyzer = TransactionCostAnalyzer()
    
    # Create sample execution results
    sample_executions = [
        ExecutionResult(
            slice_id="AAPL_0001",
            filled_quantity=25000,
            average_fill_price=150.05,
            total_cost=3751250.0,
            execution_time=300.0,
            venue="NYSE",
            slippage=2.5,
            market_impact=3.0,
            fees=25.0
        ),
        ExecutionResult(
            slice_id="AAPL_0002",
            filled_quantity=25000,
            average_fill_price=150.03,
            total_cost=3750750.0,
            execution_time=450.0,
            venue="DARK_POOL_1",
            slippage=1.8,
            market_impact=2.0,
            fees=12.5
        )
    ]
    
    cost_analysis = cost_analyzer.analyze_execution_costs(
        sample_executions, benchmark_price=150.00, order_quantity=50000
    )
    
    print(f"Transaction Cost Analysis:")
    print(f"  Total Cost: ${cost_analysis.total_cost:,.2f}")
    print(f"  Cost (bps): {cost_analysis.cost_basis_points:.2f}")
    print(f"  Market Impact: ${cost_analysis.market_impact:,.2f}")
    print(f"  Slippage: ${cost_analysis.slippage:,.2f}")
    
    # 3. Test Latency Optimizer
    print("\n3. Testing Latency Optimizer:")
    latency_optimizer = LatencyOptimizer()
    
    # Simulate latency measurements
    for _ in range(20):
        latency_optimizer.measure_latency("order_submission")
    
    optimization_results = latency_optimizer.optimize_latency()
    print(f"Latency Optimization Results:")
    print(f"  Average Latency: {optimization_results['avg_latency_us']:.1f} μs")
    print(f"  Meets Target: {optimization_results['performance_vs_target']['meets_target']}")
    print(f"  Recommendations: {len(optimization_results['recommendations'])}")
    
    # 4. Test Slippage Model
    print("\n4. Testing Slippage Model:")
    slippage_model = SlippageModel()
    
    # Simulate execution
    market_conditions = {
        'volatility': 0.025,
        'spread': 0.08,
        'price': 150.0
    }
    
    simulation_result = slippage_model.simulate_realistic_execution(
        order_size=10000,
        market_conditions=market_conditions,
        execution_strategy=OrderType.TWAP
    )
    
    print(f"Slippage Simulation:")
    print(f"  Filled Quantity: {simulation_result['filled_quantity']:,}")
    print(f"  Slippage: {simulation_result['slippage_bps']:.2f} bps")
    print(f"  Execution Time: {simulation_result['execution_time_seconds']:.1f} seconds")
    print(f"  Average Fill Price: ${simulation_result['average_fill_price']:.2f}")

if __name__ == "__main__":
    test_execution_optimization()