import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, timedelta

# Import from BaseInstitutionalStrategy
from BaseInstitutionalStrategy import (
    ExecutionAction, ExecutionAlgorithm, ExecutionUrgency, 
    TimeInForce, ExecutionIntent, SignalType
)


class MarketCondition(Enum):
    """Market condition enumeration for execution optimization"""
    LIQUID = "LIQUID"
    ILLIQUID = "ILLIQUID"
    VOLATILE = "VOLATILE"
    STABLE = "STABLE"
    OPENING = "OPENING"
    CLOSING = "CLOSING"
    MIDDAY = "MIDDAY"


class SlippageModel(Enum):
    """Slippage model types"""
    LINEAR = "LINEAR"
    SQUARE_ROOT = "SQUARE_ROOT"
    EXPONENTIAL = "EXPONENTIAL"
    HISTORICAL = "HISTORICAL"


@dataclass
class MarketImpactEstimate:
    """Market impact estimation for order execution"""
    temporary_impact: float  # Temporary price impact
    permanent_impact: float  # Permanent price impact
    total_cost: float       # Total transaction cost
    optimal_participation_rate: float  # Optimal participation rate
    estimated_fill_time: timedelta     # Estimated time to fill
    confidence_interval: Tuple[float, float]  # 95% confidence interval


@dataclass
class ExecutionConstraints:
    """Execution constraints for order management"""
    max_participation_rate: float = 0.1  # Max % of volume
    max_order_size: Optional[float] = None
    min_order_size: Optional[float] = None
    time_horizon: Optional[timedelta] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    allow_dark_pools: bool = True
    allow_crossing_networks: bool = True
    price_improvement_threshold: float = 0.0001  # Minimum price improvement


class ExecutionIntentUtils:
    """
    Utility class for execution intent generation and order management.
    Provides sophisticated execution algorithms and market impact modeling.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    def determine_execution_algorithm(signal_strength: float, urgency: ExecutionUrgency,
                                   market_condition: MarketCondition, 
                                   order_size: float, avg_volume: float) -> ExecutionAlgorithm:
        """
        Determine optimal execution algorithm based on market conditions and order characteristics.
        
        Args:
            signal_strength: Strength of trading signal (0-1)
            urgency: Execution urgency level
            market_condition: Current market condition
            order_size: Size of the order
            avg_volume: Average daily volume
            
        Returns:
            Optimal execution algorithm
        """
        participation_rate = order_size / avg_volume if avg_volume > 0 else 0
        
        # High urgency or strong signal -> Market order
        if urgency == ExecutionUrgency.URGENT or signal_strength > 0.9:
            return ExecutionAlgorithm.MARKET
        
        # Large orders relative to volume -> TWAP or VWAP
        if participation_rate > 0.1:
            if market_condition in [MarketCondition.VOLATILE, MarketCondition.ILLIQUID]:
                return ExecutionAlgorithm.TWAP  # More predictable in volatile markets
            else:
                return ExecutionAlgorithm.VWAP  # Better price in stable markets
        
        # Medium orders -> Implementation Shortfall or VWAP
        if participation_rate > 0.05:
            if urgency == ExecutionUrgency.HIGH:
                return ExecutionAlgorithm.IMPLEMENTATION_SHORTFALL
            else:
                return ExecutionAlgorithm.VWAP
        
        # Small orders -> Limit or Iceberg
        if market_condition == MarketCondition.LIQUID:
            return ExecutionAlgorithm.LIMIT
        else:
            return ExecutionAlgorithm.ICEBERG
    
    @staticmethod
    def determine_execution_urgency(signal_confidence: float, signal_type: SignalType,
                                  time_decay_factor: float = 1.0,
                                  market_close_proximity: float = 1.0) -> ExecutionUrgency:
        """
        Determine execution urgency based on signal characteristics and market timing.
        
        Args:
            signal_confidence: Confidence in the trading signal (0-1)
            signal_type: Type of signal (BULLISH, BEARISH, etc.)
            time_decay_factor: Factor representing signal time decay (0-1)
            market_close_proximity: Factor for proximity to market close (0-1)
            
        Returns:
            Appropriate execution urgency level
        """
        # Base urgency from signal confidence
        base_urgency = signal_confidence
        
        # Adjust for signal strength
        if signal_type in [SignalType.STRONG_BULLISH, SignalType.STRONG_BEARISH]:
            base_urgency *= 1.2
        
        # Adjust for time decay
        adjusted_urgency = base_urgency * time_decay_factor
        
        # Adjust for market close proximity
        if market_close_proximity < 0.1:  # Close to market close
            adjusted_urgency *= 1.5
        
        # Map to urgency levels
        if adjusted_urgency > 0.9:
            return ExecutionUrgency.URGENT
        elif adjusted_urgency > 0.7:
            return ExecutionUrgency.HIGH
        elif adjusted_urgency > 0.4:
            return ExecutionUrgency.MEDIUM
        else:
            return ExecutionUrgency.LOW
    
    @staticmethod
    def determine_time_in_force(execution_algorithm: ExecutionAlgorithm,
                              urgency: ExecutionUrgency,
                              market_condition: MarketCondition,
                              session_end_time: Optional[datetime] = None) -> TimeInForce:
        """
        Determine appropriate time-in-force based on execution parameters.
        
        Args:
            execution_algorithm: Selected execution algorithm
            urgency: Execution urgency
            market_condition: Current market condition
            session_end_time: End of trading session
            
        Returns:
            Appropriate time-in-force
        """
        # Market orders typically use IOC or FOK
        if execution_algorithm == ExecutionAlgorithm.MARKET:
            if urgency == ExecutionUrgency.URGENT:
                return TimeInForce.FOK  # Fill or Kill for urgent market orders
            else:
                return TimeInForce.IOC  # Immediate or Cancel
        
        # TWAP and VWAP algorithms need time to work
        if execution_algorithm in [ExecutionAlgorithm.TWAP, ExecutionAlgorithm.VWAP]:
            if session_end_time and datetime.now() > session_end_time - timedelta(hours=1):
                return TimeInForce.DAY  # Day order if close to session end
            else:
                return TimeInForce.GTC  # Good Till Cancelled for longer algorithms
        
        # Limit orders depend on market conditions
        if execution_algorithm == ExecutionAlgorithm.LIMIT:
            if market_condition == MarketCondition.VOLATILE:
                return TimeInForce.DAY  # Don't let limit orders sit in volatile markets
            elif urgency in [ExecutionUrgency.HIGH, ExecutionUrgency.URGENT]:
                return TimeInForce.IOC  # Immediate execution for urgent limit orders
            else:
                return TimeInForce.GTC  # Let limit orders work
        
        # Default to GTC for other algorithms
        return TimeInForce.GTC
    
    @staticmethod
    def estimate_market_impact(order_size: float, avg_volume: float, 
                             volatility: float, spread: float,
                             model: SlippageModel = SlippageModel.SQUARE_ROOT) -> MarketImpactEstimate:
        """
        Estimate market impact of an order using various models.
        
        Args:
            order_size: Size of the order
            avg_volume: Average daily volume
            volatility: Asset volatility
            spread: Bid-ask spread
            model: Slippage model to use
            
        Returns:
            Market impact estimate
        """
        if avg_volume <= 0:
            return MarketImpactEstimate(
                temporary_impact=spread/2,
                permanent_impact=0.0,
                total_cost=spread/2,
                optimal_participation_rate=0.05,
                estimated_fill_time=timedelta(minutes=30),
                confidence_interval=(0.0, spread)
            )
        
        participation_rate = order_size / avg_volume
        
        # Calculate temporary impact based on model
        if model == SlippageModel.LINEAR:
            temporary_impact = volatility * participation_rate * 0.1
        elif model == SlippageModel.SQUARE_ROOT:
            temporary_impact = volatility * np.sqrt(participation_rate) * 0.1
        elif model == SlippageModel.EXPONENTIAL:
            temporary_impact = volatility * (np.exp(participation_rate) - 1) * 0.05
        else:  # HISTORICAL - simplified
            temporary_impact = volatility * participation_rate * 0.08
        
        # Permanent impact (typically smaller)
        permanent_impact = temporary_impact * 0.3
        
        # Add bid-ask spread cost
        spread_cost = spread / 2
        total_cost = temporary_impact + permanent_impact + spread_cost
        
        # Optimal participation rate (minimize total cost)
        optimal_participation_rate = min(0.2, max(0.01, 0.1 / np.sqrt(participation_rate)))
        
        # Estimated fill time
        if participation_rate > 0.2:
            fill_time = timedelta(hours=2)
        elif participation_rate > 0.1:
            fill_time = timedelta(hours=1)
        elif participation_rate > 0.05:
            fill_time = timedelta(minutes=30)
        else:
            fill_time = timedelta(minutes=10)
        
        # Confidence interval (simplified)
        confidence_lower = total_cost * 0.7
        confidence_upper = total_cost * 1.5
        
        return MarketImpactEstimate(
            temporary_impact=temporary_impact,
            permanent_impact=permanent_impact,
            total_cost=total_cost,
            optimal_participation_rate=optimal_participation_rate,
            estimated_fill_time=fill_time,
            confidence_interval=(confidence_lower, confidence_upper)
        )
    
    @staticmethod
    def optimize_order_slicing(total_quantity: float, time_horizon: timedelta,
                             avg_volume: float, volatility: float) -> List[Dict[str, Any]]:
        """
        Optimize order slicing for large orders.
        
        Args:
            total_quantity: Total quantity to trade
            time_horizon: Time available for execution
            avg_volume: Average volume per period
            volatility: Asset volatility
            
        Returns:
            List of order slices with timing and size
        """
        if time_horizon.total_seconds() <= 0:
            return [{
                'quantity': total_quantity,
                'delay_minutes': 0,
                'participation_rate': min(0.1, total_quantity / avg_volume)
            }]
        
        # Calculate optimal number of slices
        total_minutes = time_horizon.total_seconds() / 60
        max_participation_rate = 0.1  # Maximum 10% of volume per slice
        
        # Determine slice size based on volume and volatility
        base_slice_size = avg_volume * max_participation_rate
        volatility_adjustment = max(0.5, min(2.0, 1.0 / volatility))  # Adjust for volatility
        optimal_slice_size = base_slice_size * volatility_adjustment
        
        num_slices = max(1, int(np.ceil(total_quantity / optimal_slice_size)))
        slice_size = total_quantity / num_slices
        
        # Calculate timing between slices
        if num_slices > 1:
            delay_between_slices = total_minutes / (num_slices - 1)
        else:
            delay_between_slices = 0
        
        # Generate slice schedule
        slices = []
        for i in range(num_slices):
            slices.append({
                'quantity': slice_size,
                'delay_minutes': i * delay_between_slices,
                'participation_rate': slice_size / avg_volume if avg_volume > 0 else 0.05
            })
        
        return slices
    
    @staticmethod
    def create_execution_intent(action: ExecutionAction, symbol: str, quantity: float,
                              signal_confidence: float, signal_type: SignalType,
                              market_data: Dict[str, Any],
                              constraints: Optional[ExecutionConstraints] = None) -> ExecutionIntent:
        """
        Create optimized execution intent based on comprehensive analysis.
        
        Args:
            action: Execution action (ENTER_LONG, ENTER_SHORT, etc.)
            symbol: Trading symbol
            quantity: Order quantity
            signal_confidence: Confidence in trading signal
            signal_type: Type of trading signal
            market_data: Current market data (price, volume, spread, etc.)
            constraints: Execution constraints
            
        Returns:
            Optimized execution intent
        """
        if constraints is None:
            constraints = ExecutionConstraints()
        
        # Extract market data
        current_price = market_data.get('price', 0)
        avg_volume = market_data.get('avg_volume', 1000000)
        volatility = market_data.get('volatility', 0.02)
        spread = market_data.get('spread', current_price * 0.001)
        
        # Determine market condition
        volume_ratio = market_data.get('current_volume', avg_volume) / avg_volume
        if volume_ratio > 2.0 and volatility > 0.03:
            market_condition = MarketCondition.VOLATILE
        elif volume_ratio < 0.5:
            market_condition = MarketCondition.ILLIQUID
        else:
            market_condition = MarketCondition.LIQUID
        
        # Determine execution parameters
        urgency = ExecutionIntentUtils.determine_execution_urgency(
            signal_confidence, signal_type
        )
        
        algorithm = ExecutionIntentUtils.determine_execution_algorithm(
            signal_confidence, urgency, market_condition, quantity, avg_volume
        )
        
        time_in_force = ExecutionIntentUtils.determine_time_in_force(
            algorithm, urgency, market_condition
        )
        
        # Estimate market impact
        impact_estimate = ExecutionIntentUtils.estimate_market_impact(
            quantity, avg_volume, volatility, spread
        )
        
        # Set limit price for limit orders
        limit_price = None
        if algorithm == ExecutionAlgorithm.LIMIT:
            if action in [ExecutionAction.ENTER_LONG, ExecutionAction.EXIT_SHORT]:
                # Buy orders: bid below current price
                limit_price = current_price * (1 - constraints.price_improvement_threshold)
            else:
                # Sell orders: offer above current price
                limit_price = current_price * (1 + constraints.price_improvement_threshold)
        
        # Create metadata with execution analysis
        metadata = {
            'signal_confidence': signal_confidence,
            'signal_type': signal_type.value,
            'market_condition': market_condition.value,
            'estimated_impact': {
                'temporary': impact_estimate.temporary_impact,
                'permanent': impact_estimate.permanent_impact,
                'total_cost': impact_estimate.total_cost
            },
            'optimal_participation_rate': impact_estimate.optimal_participation_rate,
            'estimated_fill_time_minutes': impact_estimate.estimated_fill_time.total_seconds() / 60,
            'volatility': volatility,
            'spread_bps': (spread / current_price) * 10000 if current_price > 0 else 0
        }
        
        # Add order slicing recommendation for large orders
        participation_rate = quantity / avg_volume if avg_volume > 0 else 0
        if participation_rate > 0.1 and constraints.time_horizon:
            slices = ExecutionIntentUtils.optimize_order_slicing(
                quantity, constraints.time_horizon, avg_volume, volatility
            )
            metadata['recommended_slicing'] = slices
        
        return ExecutionIntent(
            action=action,
            symbol=symbol,
            quantity=quantity,
            algorithm=algorithm,
            urgency=urgency,
            time_in_force=time_in_force,
            limit_price=limit_price,
            metadata=metadata
        )
    
    @staticmethod
    def validate_execution_intent(intent: ExecutionIntent, 
                                current_positions: Dict[str, float],
                                risk_limits: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate execution intent against risk limits and position constraints.
        
        Args:
            intent: Execution intent to validate
            current_positions: Current portfolio positions
            risk_limits: Risk limit configuration
            
        Returns:
            Tuple of (is_valid, reason)
        """
        # Check maximum position size
        max_position = risk_limits.get('max_position_size', float('inf'))
        if abs(intent.quantity) > max_position:
            return False, f"Order size {intent.quantity} exceeds maximum position size {max_position}"
        
        # Check position limits after execution
        current_position = current_positions.get(intent.symbol, 0)
        
        if intent.action in [ExecutionAction.ENTER_LONG, ExecutionAction.INCREASE_POSITION]:
            new_position = current_position + intent.quantity
        elif intent.action in [ExecutionAction.ENTER_SHORT]:
            new_position = current_position - intent.quantity
        elif intent.action in [ExecutionAction.EXIT_LONG, ExecutionAction.EXIT_SHORT]:
            new_position = 0  # Assuming full exit
        else:
            new_position = current_position
        
        max_long_position = risk_limits.get('max_long_position', float('inf'))
        max_short_position = risk_limits.get('max_short_position', float('inf'))
        
        if new_position > max_long_position:
            return False, f"New long position {new_position} exceeds limit {max_long_position}"
        
        if new_position < -max_short_position:
            return False, f"New short position {abs(new_position)} exceeds limit {max_short_position}"
        
        # Check concentration limits
        max_concentration = risk_limits.get('max_single_position_concentration', 1.0)
        total_portfolio_value = sum(abs(pos) for pos in current_positions.values())
        
        if total_portfolio_value > 0:
            concentration = abs(new_position) / total_portfolio_value
            if concentration > max_concentration:
                return False, f"Position concentration {concentration:.2%} exceeds limit {max_concentration:.2%}"
        
        return True, "Execution intent validated successfully"