"""
Realistic Market Simulation for Advanced Backtesting

This module provides comprehensive market simulation capabilities including:
- Realistic transaction cost modeling
- Market impact and slippage simulation
- Liquidity-based execution simulation
- Market regime-aware backtesting
"""

import logging
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import statistics
import random
import math

# Try to import optional dependencies
try:
    import scipy.stats as stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

try:
    import sklearn.linear_model as linear_model
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class MarketRegime(Enum):
    """Market regime types"""
    NORMAL = "normal"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    CRISIS = "crisis"
    RECOVERY = "recovery"


class OrderType(Enum):
    """Order types for simulation"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    """Order sides"""
    BUY = "buy"
    SELL = "sell"


@dataclass
class MarketData:
    """Market data point for simulation"""
    timestamp: datetime
    symbol: str
    bid_price: float
    ask_price: float
    bid_size: int
    ask_size: int
    last_price: float
    volume: int
    volatility: float = 0.0
    liquidity_score: float = 1.0
    spread_bps: float = 0.0
    market_impact_factor: float = 1.0


@dataclass
class Order:
    """Order for simulation"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Optional[float] = None
    stop_price: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    time_in_force: str = "DAY"
    strategy_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Execution:
    """Execution result from simulation"""
    execution_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: float
    timestamp: datetime
    commission: float = 0.0
    slippage: float = 0.0
    market_impact: float = 0.0
    liquidity_cost: float = 0.0
    total_cost: float = 0.0
    execution_quality: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransactionCostModel:
    """Transaction cost model parameters"""
    commission_rate: float = 0.001  # 0.1%
    bid_ask_spread_factor: float = 0.5  # Half spread cost
    market_impact_factor: float = 0.0001  # 1 bps per $1M
    liquidity_penalty: float = 0.0005  # 5 bps for low liquidity
    volatility_adjustment: float = 0.1  # Volatility multiplier
    minimum_commission: float = 1.0  # Minimum commission per trade
    maximum_commission: float = 100.0  # Maximum commission per trade


@dataclass
class SlippageModel:
    """Slippage model parameters"""
    base_slippage_bps: float = 1.0  # Base slippage in basis points
    volume_impact_factor: float = 0.5  # Volume impact on slippage
    volatility_multiplier: float = 2.0  # Volatility effect on slippage
    liquidity_adjustment: float = 1.5  # Liquidity effect on slippage
    regime_multipliers: Dict[MarketRegime, float] = field(default_factory=lambda: {
        MarketRegime.NORMAL: 1.0,
        MarketRegime.HIGH_VOLATILITY: 2.5,
        MarketRegime.LOW_VOLATILITY: 0.7,
        MarketRegime.TRENDING_UP: 1.2,
        MarketRegime.TRENDING_DOWN: 1.3,
        MarketRegime.CRISIS: 4.0,
        MarketRegime.RECOVERY: 1.8
    })


@dataclass
class LiquidityModel:
    """Liquidity model parameters"""
    base_liquidity: float = 1000000.0  # Base liquidity in USD
    time_of_day_factors: Dict[int, float] = field(default_factory=lambda: {
        9: 1.5,   # Market open
        10: 1.3,  # Morning
        11: 1.1,  # Late morning
        12: 0.8,  # Lunch
        13: 0.9,  # Early afternoon
        14: 1.0,  # Afternoon
        15: 1.2,  # Late afternoon
        16: 1.4   # Market close
    })
    volatility_impact: float = -0.5  # Higher volatility reduces liquidity
    volume_boost: float = 0.3  # Higher volume increases liquidity


class MarketRegimeDetector:
    """Detects market regimes based on price and volatility data"""
    
    def __init__(self, lookback_periods: int = 20):
        self.lookback_periods = lookback_periods
        self.logger = logging.getLogger(__name__)
    
    def detect_regime(self, price_history: List[float], 
                     volatility_history: List[float]) -> MarketRegime:
        """Detect current market regime"""
        try:
            if len(price_history) < self.lookback_periods:
                return MarketRegime.NORMAL
            
            recent_prices = price_history[-self.lookback_periods:]
            recent_volatility = volatility_history[-self.lookback_periods:]
            
            # Calculate trend
            if len(recent_prices) >= 2:
                returns = [(recent_prices[i] / recent_prices[i-1] - 1) 
                          for i in range(1, len(recent_prices))]
                avg_return = statistics.mean(returns)
                volatility = statistics.stdev(returns) if len(returns) > 1 else 0
            else:
                avg_return = 0
                volatility = 0
            
            current_volatility = statistics.mean(recent_volatility)
            
            # Regime detection logic - use input volatility data
            if current_volatility >= 0.08:  # Crisis threshold (very high volatility)
                return MarketRegime.CRISIS
            elif current_volatility >= 0.05:  # High volatility threshold
                return MarketRegime.HIGH_VOLATILITY
            elif current_volatility < 0.008:  # Low volatility threshold
                return MarketRegime.LOW_VOLATILITY
            elif avg_return > 0.015:  # Positive trend
                return MarketRegime.TRENDING_UP
            elif avg_return < -0.015:  # Negative trend
                return MarketRegime.TRENDING_DOWN
            else:
                return MarketRegime.NORMAL
                
        except Exception as e:
            self.logger.error(f"Error detecting market regime: {e}")
            return MarketRegime.NORMAL


class TransactionCostCalculator:
    """Calculates realistic transaction costs"""
    
    def __init__(self, cost_model: TransactionCostModel):
        self.cost_model = cost_model
        self.logger = logging.getLogger(__name__)
    
    def calculate_costs(self, order: Order, market_data: MarketData,
                       execution_price: float, regime: MarketRegime) -> Dict[str, float]:
        """Calculate comprehensive transaction costs"""
        try:
            notional_value = order.quantity * execution_price
            
            # Base commission
            commission = max(
                min(notional_value * self.cost_model.commission_rate,
                    self.cost_model.maximum_commission),
                self.cost_model.minimum_commission
            )
            
            # Bid-ask spread cost
            spread = market_data.ask_price - market_data.bid_price
            spread_cost = (spread * self.cost_model.bid_ask_spread_factor * 
                          order.quantity)
            
            # Market impact cost
            market_impact = (notional_value * self.cost_model.market_impact_factor *
                           market_data.market_impact_factor)
            
            # Liquidity penalty
            liquidity_penalty = 0.0
            if market_data.liquidity_score < 0.5:
                liquidity_penalty = (notional_value * 
                                   self.cost_model.liquidity_penalty *
                                   (1 - market_data.liquidity_score))
            
            # Volatility adjustment
            volatility_adjustment = (notional_value * 
                                   market_data.volatility * 
                                   self.cost_model.volatility_adjustment)
            
            # Regime adjustment
            regime_multiplier = self._get_regime_multiplier(regime)
            total_variable_costs = ((spread_cost + market_impact + 
                                   liquidity_penalty + volatility_adjustment) * 
                                  regime_multiplier)
            
            total_cost = commission + total_variable_costs
            
            return {
                "commission": commission,
                "spread_cost": spread_cost,
                "market_impact": market_impact,
                "liquidity_penalty": liquidity_penalty,
                "volatility_adjustment": volatility_adjustment,
                "regime_multiplier": regime_multiplier,
                "total_cost": total_cost
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating transaction costs: {e}")
            return {"total_cost": 0.0}
    
    def _get_regime_multiplier(self, regime: MarketRegime) -> float:
        """Get cost multiplier for market regime"""
        multipliers = {
            MarketRegime.NORMAL: 1.0,
            MarketRegime.HIGH_VOLATILITY: 1.5,
            MarketRegime.LOW_VOLATILITY: 0.8,
            MarketRegime.TRENDING_UP: 1.1,
            MarketRegime.TRENDING_DOWN: 1.2,
            MarketRegime.CRISIS: 3.0,
            MarketRegime.RECOVERY: 1.4
        }
        return multipliers.get(regime, 1.0)


class SlippageCalculator:
    """Calculates realistic slippage"""
    
    def __init__(self, slippage_model: SlippageModel):
        self.slippage_model = slippage_model
        self.logger = logging.getLogger(__name__)
    
    def calculate_slippage(self, order: Order, market_data: MarketData,
                          regime: MarketRegime) -> float:
        """Calculate slippage for order execution"""
        try:
            # Base slippage
            base_slippage = self.slippage_model.base_slippage_bps / 10000.0
            
            # Volume impact
            order_value = order.quantity * market_data.last_price
            daily_volume_estimate = market_data.volume * 8  # Assume 8 hours trading
            volume_ratio = order_value / max(daily_volume_estimate, 1)
            volume_impact = (volume_ratio * 
                           self.slippage_model.volume_impact_factor)
            
            # Volatility impact
            volatility_impact = (market_data.volatility * 
                               self.slippage_model.volatility_multiplier)
            
            # Liquidity impact
            liquidity_impact = ((1 - market_data.liquidity_score) * 
                              self.slippage_model.liquidity_adjustment)
            
            # Regime impact
            regime_multiplier = self.slippage_model.regime_multipliers.get(
                regime, 1.0
            )
            
            # Total slippage
            total_slippage = ((base_slippage + volume_impact + 
                             volatility_impact + liquidity_impact) * 
                            regime_multiplier)
            
            # Apply direction (slippage is always adverse)
            if order.side == OrderSide.BUY:
                return total_slippage  # Positive slippage increases buy price
            else:
                return -total_slippage  # Negative slippage decreases sell price
                
        except Exception as e:
            self.logger.error(f"Error calculating slippage: {e}")
            return 0.0


class LiquiditySimulator:
    """Simulates liquidity-based execution"""
    
    def __init__(self, liquidity_model: LiquidityModel):
        self.liquidity_model = liquidity_model
        self.logger = logging.getLogger(__name__)
    
    def calculate_available_liquidity(self, market_data: MarketData,
                                    timestamp: datetime) -> float:
        """Calculate available liquidity at given time"""
        try:
            # Base liquidity
            base_liquidity = self.liquidity_model.base_liquidity
            
            # Time of day adjustment
            hour = timestamp.hour
            time_factor = self.liquidity_model.time_of_day_factors.get(hour, 1.0)
            
            # Volatility impact
            volatility_adjustment = (1 + market_data.volatility * 
                                   self.liquidity_model.volatility_impact)
            
            # Volume boost
            volume_boost = (1 + market_data.volume / 1000000 * 
                          self.liquidity_model.volume_boost)
            
            # Market data liquidity score
            liquidity_score_factor = market_data.liquidity_score
            
            total_liquidity = (base_liquidity * time_factor * 
                             volatility_adjustment * volume_boost * 
                             liquidity_score_factor)
            
            return max(total_liquidity, 10000)  # Minimum liquidity
            
        except Exception as e:
            self.logger.error(f"Error calculating liquidity: {e}")
            return self.liquidity_model.base_liquidity
    
    def simulate_partial_fill(self, order: Order, available_liquidity: float,
                            market_data: MarketData) -> Tuple[int, bool]:
        """Simulate partial fill based on available liquidity"""
        try:
            order_value = order.quantity * market_data.last_price
            
            if order_value <= available_liquidity:
                # Full fill
                return order.quantity, True
            else:
                # Partial fill based on available liquidity
                max_quantity = int(available_liquidity / market_data.last_price)
                fill_quantity = min(max_quantity, order.quantity)
                return max(fill_quantity, 0), False
                
        except Exception as e:
            self.logger.error(f"Error simulating partial fill: {e}")
            return 0, False


class RealisticMarketSimulator:
    """Main realistic market simulator"""
    
    def __init__(self, 
                 cost_model: Optional[TransactionCostModel] = None,
                 slippage_model: Optional[SlippageModel] = None,
                 liquidity_model: Optional[LiquidityModel] = None):
        
        self.cost_model = cost_model or TransactionCostModel()
        self.slippage_model = slippage_model or SlippageModel()
        self.liquidity_model = liquidity_model or LiquidityModel()
        
        self.regime_detector = MarketRegimeDetector()
        self.cost_calculator = TransactionCostCalculator(self.cost_model)
        self.slippage_calculator = SlippageCalculator(self.slippage_model)
        self.liquidity_simulator = LiquiditySimulator(self.liquidity_model)
        
        self.price_history: Dict[str, List[float]] = {}
        self.volatility_history: Dict[str, List[float]] = {}
        self.execution_counter = 0
        
        self.logger = logging.getLogger(__name__)
    
    async def simulate_execution(self, order: Order, 
                               market_data: MarketData) -> List[Execution]:
        """Simulate realistic order execution"""
        try:
            # Update price and volatility history
            self._update_history(order.symbol, market_data)
            
            # Detect market regime
            regime = self.regime_detector.detect_regime(
                self.price_history.get(order.symbol, []),
                self.volatility_history.get(order.symbol, [])
            )
            
            # Calculate available liquidity
            available_liquidity = self.liquidity_simulator.calculate_available_liquidity(
                market_data, order.timestamp
            )
            
            # Simulate partial fill
            fill_quantity, is_full_fill = self.liquidity_simulator.simulate_partial_fill(
                order, available_liquidity, market_data
            )
            
            if fill_quantity <= 0:
                return []  # No execution
            
            # Calculate execution price with slippage
            slippage = self.slippage_calculator.calculate_slippage(
                order, market_data, regime
            )
            
            if order.side == OrderSide.BUY:
                base_price = market_data.ask_price
                execution_price = base_price * (1 + slippage)
            else:
                base_price = market_data.bid_price
                execution_price = base_price * (1 + slippage)
            
            # Calculate transaction costs
            fill_order = Order(
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                quantity=fill_quantity,
                price=order.price,
                timestamp=order.timestamp
            )
            
            costs = self.cost_calculator.calculate_costs(
                fill_order, market_data, execution_price, regime
            )
            
            # Calculate execution quality
            execution_quality = self._calculate_execution_quality(
                order, execution_price, market_data, slippage
            )
            
            # Create execution
            self.execution_counter += 1
            execution = Execution(
                execution_id=f"exec_{self.execution_counter}",
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=fill_quantity,
                price=execution_price,
                timestamp=market_data.timestamp,
                commission=costs.get("commission", 0.0),
                slippage=abs(slippage * execution_price),
                market_impact=costs.get("market_impact", 0.0),
                liquidity_cost=costs.get("liquidity_penalty", 0.0),
                total_cost=costs.get("total_cost", 0.0),
                execution_quality=execution_quality,
                metadata={
                    "regime": regime.value,
                    "available_liquidity": available_liquidity,
                    "is_full_fill": is_full_fill,
                    "spread_cost": costs.get("spread_cost", 0.0),
                    "volatility_adjustment": costs.get("volatility_adjustment", 0.0),
                    "regime_multiplier": costs.get("regime_multiplier", 1.0)
                }
            )
            
            return [execution]
            
        except Exception as e:
            self.logger.error(f"Error simulating execution: {e}")
            return []
    
    def _update_history(self, symbol: str, market_data: MarketData):
        """Update price and volatility history"""
        if symbol not in self.price_history:
            self.price_history[symbol] = []
            self.volatility_history[symbol] = []
        
        self.price_history[symbol].append(market_data.last_price)
        self.volatility_history[symbol].append(market_data.volatility)
        
        # Keep only recent history
        max_history = 100
        if len(self.price_history[symbol]) > max_history:
            self.price_history[symbol] = self.price_history[symbol][-max_history:]
            self.volatility_history[symbol] = self.volatility_history[symbol][-max_history:]
    
    def _calculate_execution_quality(self, order: Order, execution_price: float,
                                   market_data: MarketData, slippage: float) -> float:
        """Calculate execution quality score (0-1)"""
        try:
            # Base quality starts at 1.0
            quality = 1.0
            
            # Penalize for slippage
            slippage_penalty = min(abs(slippage) * 10, 0.5)  # Max 50% penalty
            quality -= slippage_penalty
            
            # Penalize for wide spreads
            spread = market_data.ask_price - market_data.bid_price
            spread_bps = (spread / market_data.last_price) * 10000
            spread_penalty = min(spread_bps / 100, 0.3)  # Max 30% penalty
            quality -= spread_penalty
            
            # Bonus for good liquidity
            liquidity_bonus = market_data.liquidity_score * 0.1
            quality += liquidity_bonus
            
            return max(min(quality, 1.0), 0.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating execution quality: {e}")
            return 0.5
    
    async def simulate_market_impact(self, executions: List[Execution],
                                   market_data: MarketData) -> MarketData:
        """Simulate market impact on subsequent market data"""
        try:
            if not executions:
                return market_data
            
            # Calculate total impact
            total_volume = sum(exec.quantity for exec in executions)
            total_value = sum(exec.quantity * exec.price for exec in executions)
            
            # Estimate impact on price
            daily_volume_estimate = market_data.volume * 8
            volume_ratio = total_volume / max(daily_volume_estimate, 1)
            
            # Price impact (temporary)
            price_impact = volume_ratio * 0.001  # 0.1% per 100% of daily volume
            
            # Apply impact based on order direction
            net_buy_volume = sum(exec.quantity if exec.side == OrderSide.BUY else -exec.quantity 
                               for exec in executions)
            
            if net_buy_volume > 0:
                # Net buying pressure - increase prices
                new_bid = market_data.bid_price * (1 + price_impact)
                new_ask = market_data.ask_price * (1 + price_impact)
                new_last = market_data.last_price * (1 + price_impact)
            else:
                # Net selling pressure - decrease prices
                new_bid = market_data.bid_price * (1 - price_impact)
                new_ask = market_data.ask_price * (1 - price_impact)
                new_last = market_data.last_price * (1 - price_impact)
            
            # Update market data
            updated_market_data = MarketData(
                timestamp=market_data.timestamp,
                symbol=market_data.symbol,
                bid_price=new_bid,
                ask_price=new_ask,
                bid_size=market_data.bid_size,
                ask_size=market_data.ask_size,
                last_price=new_last,
                volume=market_data.volume + total_volume,
                volatility=market_data.volatility,
                liquidity_score=max(market_data.liquidity_score - volume_ratio * 0.1, 0.1),
                spread_bps=market_data.spread_bps,
                market_impact_factor=market_data.market_impact_factor
            )
            
            return updated_market_data
            
        except Exception as e:
            self.logger.error(f"Error simulating market impact: {e}")
            return market_data
    
    def get_simulation_statistics(self) -> Dict[str, Any]:
        """Get simulation statistics"""
        return {
            "total_executions": self.execution_counter,
            "symbols_tracked": len(self.price_history),
            "cost_model": {
                "commission_rate": self.cost_model.commission_rate,
                "market_impact_factor": self.cost_model.market_impact_factor,
                "liquidity_penalty": self.cost_model.liquidity_penalty
            },
            "slippage_model": {
                "base_slippage_bps": self.slippage_model.base_slippage_bps,
                "volume_impact_factor": self.slippage_model.volume_impact_factor,
                "volatility_multiplier": self.slippage_model.volatility_multiplier
            }
        }


# Example usage and testing
async def example_usage():
    """Demonstrate realistic market simulation"""
    print("=== Realistic Market Simulation Demo ===")
    
    # Create simulator with custom models
    cost_model = TransactionCostModel(
        commission_rate=0.0005,  # 5 bps
        market_impact_factor=0.0002,  # 2 bps per $1M
        liquidity_penalty=0.001  # 10 bps for low liquidity
    )
    
    slippage_model = SlippageModel(
        base_slippage_bps=2.0,
        volume_impact_factor=0.8,
        volatility_multiplier=1.5
    )
    
    simulator = RealisticMarketSimulator(
        cost_model=cost_model,
        slippage_model=slippage_model
    )
    
    # Create sample market data
    market_data = MarketData(
        timestamp=datetime.now(),
        symbol="AAPL",
        bid_price=150.00,
        ask_price=150.05,
        bid_size=1000,
        ask_size=1200,
        last_price=150.02,
        volume=1000000,
        volatility=0.02,
        liquidity_score=0.8,
        spread_bps=3.33,
        market_impact_factor=1.0
    )
    
    # Create sample orders
    orders = [
        Order(
            order_id="order_1",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1000,
            timestamp=datetime.now()
        ),
        Order(
            order_id="order_2",
            symbol="AAPL",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=500,
            timestamp=datetime.now()
        ),
        Order(
            order_id="order_3",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=2000,  # Large order
            timestamp=datetime.now()
        )
    ]
    
    print("\\nSimulating order executions...")
    all_executions = []
    
    for i, order in enumerate(orders):
        print(f"\\nOrder {i+1}: {order.side.value} {order.quantity} {order.symbol}")
        
        # Simulate execution
        executions = await simulator.simulate_execution(order, market_data)
        
        if executions:
            for exec in executions:
                print(f"  Executed: {exec.quantity} @ ${exec.price:.4f}")
                print(f"  Commission: ${exec.commission:.2f}")
                print(f"  Slippage: ${exec.slippage:.4f}")
                print(f"  Market Impact: ${exec.market_impact:.2f}")
                print(f"  Total Cost: ${exec.total_cost:.2f}")
                print(f"  Execution Quality: {exec.execution_quality:.3f}")
                print(f"  Market Regime: {exec.metadata.get('regime', 'unknown')}")
                
                all_executions.append(exec)
        else:
            print("  No execution (insufficient liquidity)")
        
        # Update market data with impact
        market_data = await simulator.simulate_market_impact(executions, market_data)
        print(f"  Updated market price: ${market_data.last_price:.4f}")
    
    # Show simulation statistics
    print("\\n=== Simulation Statistics ===")
    stats = simulator.get_simulation_statistics()
    print(f"Total executions: {stats['total_executions']}")
    print(f"Symbols tracked: {stats['symbols_tracked']}")
    
    # Calculate aggregate metrics
    if all_executions:
        total_volume = sum(exec.quantity for exec in all_executions)
        total_value = sum(exec.quantity * exec.price for exec in all_executions)
        total_costs = sum(exec.total_cost for exec in all_executions)
        avg_quality = statistics.mean(exec.execution_quality for exec in all_executions)
        
        print(f"\\nAggregate Metrics:")
        print(f"Total volume: {total_volume:,} shares")
        print(f"Total value: ${total_value:,.2f}")
        print(f"Total costs: ${total_costs:.2f}")
        print(f"Cost as % of value: {(total_costs/total_value)*100:.3f}%")
        print(f"Average execution quality: {avg_quality:.3f}")
    
    print("\\nRealistic market simulation demo completed!")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run example
    asyncio.run(example_usage())