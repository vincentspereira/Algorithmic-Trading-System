# Realistic Market Simulation Documentation

## Overview

The Realistic Market Simulation module provides comprehensive market simulation capabilities for advanced backtesting. It includes realistic transaction cost modeling, market impact and slippage simulation, liquidity-based execution simulation, and market regime-aware backtesting to create highly accurate trading simulations.

## Key Features

- **Realistic Transaction Cost Modeling**: Comprehensive cost calculation including commissions, spreads, market impact, and liquidity penalties
- **Market Impact and Slippage Simulation**: Dynamic slippage calculation based on order size, volatility, and market conditions
- **Liquidity-Based Execution Simulation**: Partial fill simulation based on available market liquidity
- **Market Regime-Aware Backtesting**: Adaptive behavior based on detected market regimes (normal, high volatility, crisis, trending)
- **Multi-Factor Cost Models**: Configurable models for different market conditions and asset classes
- **Execution Quality Metrics**: Comprehensive execution quality scoring and analysis

## Architecture

### Core Components

1. **RealisticMarketSimulator**: Main orchestration class that coordinates all simulation components
2. **MarketRegimeDetector**: Detects current market regime based on price and volatility patterns
3. **TransactionCostCalculator**: Calculates comprehensive transaction costs
4. **SlippageCalculator**: Computes realistic slippage based on market conditions
5. **LiquiditySimulator**: Simulates liquidity-based execution and partial fills

### Market Regimes

The system recognizes several market regimes that affect execution costs and behavior:

- **NORMAL**: Standard market conditions
- **HIGH_VOLATILITY**: Elevated volatility periods
- **LOW_VOLATILITY**: Low volatility, stable conditions
- **TRENDING_UP**: Sustained upward price movement
- **TRENDING_DOWN**: Sustained downward price movement
- **CRISIS**: Extreme volatility with large price movements
- **RECOVERY**: Post-crisis recovery periods

## Usage Examples

### Basic Setup

```python
from nautilus_trader_engine.backtesting.realistic_market_simulation import (
    RealisticMarketSimulator,
    TransactionCostModel,
    SlippageModel,
    LiquidityModel,
    MarketData,
    Order,
    OrderSide,
    OrderType
)
import asyncio
from datetime import datetime

# Create custom cost models
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

# Initialize simulator
simulator = RealisticMarketSimulator(
    cost_model=cost_model,
    slippage_model=slippage_model
)
```

### Creating Market Data

```python
# Create realistic market data
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
```

### Order Execution Simulation

```python
# Create orders
buy_order = Order(
    order_id="buy_1",
    symbol="AAPL",
    side=OrderSide.BUY,
    order_type=OrderType.MARKET,
    quantity=1000,
    timestamp=datetime.now()
)

sell_order = Order(
    order_id="sell_1",
    symbol="AAPL",
    side=OrderSide.SELL,
    order_type=OrderType.MARKET,
    quantity=500,
    timestamp=datetime.now()
)

# Simulate executions
async def simulate_trading():
    # Execute buy order
    buy_executions = await simulator.simulate_execution(buy_order, market_data)
    
    for execution in buy_executions:
        print(f"Executed: {execution.quantity} @ ${execution.price:.4f}")
        print(f"Commission: ${execution.commission:.2f}")
        print(f"Slippage: ${execution.slippage:.4f}")
        print(f"Market Impact: ${execution.market_impact:.2f}")
        print(f"Total Cost: ${execution.total_cost:.2f}")
        print(f"Execution Quality: {execution.execution_quality:.3f}")
        print(f"Market Regime: {execution.metadata.get('regime')}")
    
    # Update market data with impact
    updated_market_data = await simulator.simulate_market_impact(
        buy_executions, market_data
    )
    
    # Execute sell order with updated market data
    sell_executions = await simulator.simulate_execution(sell_order, updated_market_data)
    
    return buy_executions + sell_executions

# Run simulation
executions = asyncio.run(simulate_trading())
```

## Transaction Cost Models

### Basic Cost Model

```python
# Standard cost model for equities
equity_cost_model = TransactionCostModel(
    commission_rate=0.0005,  # 5 bps commission
    bid_ask_spread_factor=0.5,  # Pay half the spread
    market_impact_factor=0.0001,  # 1 bps per $1M traded
    liquidity_penalty=0.0005,  # 5 bps penalty for low liquidity
    volatility_adjustment=0.1,  # 10% volatility multiplier
    minimum_commission=1.0,  # $1 minimum
    maximum_commission=100.0  # $100 maximum
)
```

### High-Frequency Trading Cost Model

```python
# Low-cost model for HFT
hft_cost_model = TransactionCostModel(
    commission_rate=0.0001,  # 1 bps commission
    bid_ask_spread_factor=0.3,  # Better spread capture
    market_impact_factor=0.00005,  # Lower market impact
    liquidity_penalty=0.0002,  # Lower liquidity penalty
    volatility_adjustment=0.05,  # Lower volatility sensitivity
    minimum_commission=0.1,  # $0.10 minimum
    maximum_commission=10.0  # $10 maximum
)
```

### Institutional Cost Model

```python
# Higher cost model for large institutional orders
institutional_cost_model = TransactionCostModel(
    commission_rate=0.002,  # 20 bps commission
    bid_ask_spread_factor=0.8,  # Pay most of the spread
    market_impact_factor=0.0005,  # 5 bps per $1M traded
    liquidity_penalty=0.002,  # 20 bps penalty for low liquidity
    volatility_adjustment=0.3,  # Higher volatility sensitivity
    minimum_commission=10.0,  # $10 minimum
    maximum_commission=1000.0  # $1000 maximum
)
```

## Slippage Models

### Conservative Slippage Model

```python
conservative_slippage = SlippageModel(
    base_slippage_bps=0.5,  # Low base slippage
    volume_impact_factor=0.3,  # Lower volume impact
    volatility_multiplier=1.0,  # Standard volatility effect
    liquidity_adjustment=1.0,  # Standard liquidity effect
    regime_multipliers={
        MarketRegime.NORMAL: 1.0,
        MarketRegime.HIGH_VOLATILITY: 1.8,
        MarketRegime.CRISIS: 2.5
    }
)
```

### Aggressive Slippage Model

```python
aggressive_slippage = SlippageModel(
    base_slippage_bps=3.0,  # Higher base slippage
    volume_impact_factor=1.0,  # Higher volume impact
    volatility_multiplier=3.0,  # Higher volatility sensitivity
    liquidity_adjustment=2.0,  # Higher liquidity sensitivity
    regime_multipliers={
        MarketRegime.NORMAL: 1.0,
        MarketRegime.HIGH_VOLATILITY: 3.0,
        MarketRegime.CRISIS: 5.0
    }
)
```

## Liquidity Models

### Standard Liquidity Model

```python
standard_liquidity = LiquidityModel(
    base_liquidity=1000000.0,  # $1M base liquidity
    time_of_day_factors={
        9: 1.5,   # Market open - high liquidity
        10: 1.3,  # Morning
        11: 1.1,  # Late morning
        12: 0.8,  # Lunch - low liquidity
        13: 0.9,  # Early afternoon
        14: 1.0,  # Afternoon
        15: 1.2,  # Late afternoon
        16: 1.4   # Market close - high liquidity
    },
    volatility_impact=-0.5,  # Higher volatility reduces liquidity
    volume_boost=0.3  # Higher volume increases liquidity
)
```

### High-Liquidity Model (Large Cap Stocks)

```python
high_liquidity = LiquidityModel(
    base_liquidity=10000000.0,  # $10M base liquidity
    time_of_day_factors={
        9: 2.0, 10: 1.8, 11: 1.5, 12: 1.2,
        13: 1.3, 14: 1.4, 15: 1.6, 16: 1.8
    },
    volatility_impact=-0.3,  # Less volatility impact
    volume_boost=0.5  # Higher volume boost
)
```

### Low-Liquidity Model (Small Cap Stocks)

```python
low_liquidity = LiquidityModel(
    base_liquidity=100000.0,  # $100K base liquidity
    time_of_day_factors={
        9: 1.2, 10: 1.1, 11: 1.0, 12: 0.6,
        13: 0.7, 14: 0.8, 15: 0.9, 16: 1.1
    },
    volatility_impact=-0.8,  # Higher volatility impact
    volume_boost=0.2  # Lower volume boost
)
```

## Market Regime Detection

### Custom Regime Detection

```python
from nautilus_trader_engine.backtesting.realistic_market_simulation import MarketRegimeDetector

# Create detector with custom parameters
detector = MarketRegimeDetector(lookback_periods=20)

# Detect regime from price and volatility history
price_history = [100.0, 101.0, 99.5, 102.0, 98.0, 103.0]
volatility_history = [0.01, 0.015, 0.02, 0.018, 0.025, 0.03]

regime = detector.detect_regime(price_history, volatility_history)
print(f"Detected regime: {regime.value}")
```

### Regime-Specific Behavior

```python
# Adjust simulation parameters based on regime
async def regime_aware_execution(order, market_data):
    executions = await simulator.simulate_execution(order, market_data)
    
    for execution in executions:
        regime = execution.metadata.get('regime')
        
        if regime == 'crisis':
            print("⚠️ Crisis regime detected - high costs expected")
        elif regime == 'high_volatility':
            print("📈 High volatility - increased slippage")
        elif regime == 'low_volatility':
            print("📉 Low volatility - favorable execution")
        
        print(f"Execution in {regime} regime:")
        print(f"  Price: ${execution.price:.4f}")
        print(f"  Total Cost: ${execution.total_cost:.2f}")
        print(f"  Quality Score: {execution.execution_quality:.3f}")
    
    return executions
```

## Advanced Features

### Partial Fill Simulation

```python
# Large order that may partially fill
large_order = Order(
    order_id="large_order",
    symbol="AAPL",
    side=OrderSide.BUY,
    order_type=OrderType.MARKET,
    quantity=50000,  # Large quantity
    timestamp=datetime.now()
)

# Low liquidity market data
low_liquidity_data = MarketData(
    timestamp=datetime.now(),
    symbol="AAPL",
    bid_price=150.00,
    ask_price=150.10,
    bid_size=500,
    ask_size=600,
    last_price=150.05,
    volume=50000,  # Low volume
    volatility=0.03,
    liquidity_score=0.3,  # Low liquidity score
    spread_bps=6.67,
    market_impact_factor=2.0
)

# Simulate execution - may result in partial fill
executions = await simulator.simulate_execution(large_order, low_liquidity_data)

for execution in executions:
    is_full_fill = execution.metadata.get('is_full_fill', False)
    if not is_full_fill:
        print(f"Partial fill: {execution.quantity} of {large_order.quantity}")
    else:
        print(f"Full fill: {execution.quantity}")
```

### Market Impact Simulation

```python
# Simulate market impact from large trades
async def simulate_market_impact_scenario():
    current_market_data = market_data
    all_executions = []
    
    # Series of large orders
    large_orders = [
        Order("order_1", "AAPL", OrderSide.BUY, OrderType.MARKET, 5000),
        Order("order_2", "AAPL", OrderSide.BUY, OrderType.MARKET, 3000),
        Order("order_3", "AAPL", OrderSide.SELL, OrderType.MARKET, 4000),
    ]
    
    print("Initial price:", current_market_data.last_price)
    
    for i, order in enumerate(large_orders):
        # Execute order
        executions = await simulator.simulate_execution(order, current_market_data)
        all_executions.extend(executions)
        
        # Update market data with impact
        current_market_data = await simulator.simulate_market_impact(
            executions, current_market_data
        )
        
        print(f"After order {i+1}: ${current_market_data.last_price:.4f}")
    
    return all_executions, current_market_data

# Run impact simulation
executions, final_market_data = asyncio.run(simulate_market_impact_scenario())
```

### Execution Quality Analysis

```python
def analyze_execution_quality(executions):
    """Analyze execution quality metrics"""
    if not executions:
        return
    
    qualities = [exec.execution_quality for exec in executions]
    costs = [exec.total_cost for exec in executions]
    slippages = [exec.slippage for exec in executions]
    
    print("=== Execution Quality Analysis ===")
    print(f"Average Quality Score: {statistics.mean(qualities):.3f}")
    print(f"Quality Range: {min(qualities):.3f} - {max(qualities):.3f}")
    print(f"Total Costs: ${sum(costs):.2f}")
    print(f"Average Slippage: ${statistics.mean(slippages):.4f}")
    
    # Quality distribution
    high_quality = sum(1 for q in qualities if q > 0.8)
    medium_quality = sum(1 for q in qualities if 0.5 <= q <= 0.8)
    low_quality = sum(1 for q in qualities if q < 0.5)
    
    print(f"Quality Distribution:")
    print(f"  High (>0.8): {high_quality} executions")
    print(f"  Medium (0.5-0.8): {medium_quality} executions")
    print(f"  Low (<0.5): {low_quality} executions")

# Analyze execution results
analyze_execution_quality(executions)
```

## Integration with Backtesting

### Backtesting Integration

```python
class RealisticBacktester:
    """Backtesting engine with realistic market simulation"""
    
    def __init__(self, simulator: RealisticMarketSimulator):
        self.simulator = simulator
        self.portfolio_value = 1000000.0  # $1M starting capital
        self.positions = {}
        self.cash = self.portfolio_value
        self.execution_history = []
    
    async def execute_strategy_order(self, order: Order, market_data: MarketData):
        """Execute strategy order with realistic simulation"""
        executions = await self.simulator.simulate_execution(order, market_data)
        
        for execution in executions:
            # Update portfolio
            if execution.side == OrderSide.BUY:
                self.cash -= (execution.quantity * execution.price + execution.total_cost)
                self.positions[execution.symbol] = self.positions.get(execution.symbol, 0) + execution.quantity
            else:
                self.cash += (execution.quantity * execution.price - execution.total_cost)
                self.positions[execution.symbol] = self.positions.get(execution.symbol, 0) - execution.quantity
            
            self.execution_history.append(execution)
        
        return executions
    
    def get_portfolio_summary(self):
        """Get current portfolio summary"""
        return {
            "cash": self.cash,
            "positions": self.positions.copy(),
            "total_executions": len(self.execution_history),
            "total_costs": sum(exec.total_cost for exec in self.execution_history),
            "average_quality": statistics.mean(exec.execution_quality for exec in self.execution_history) if self.execution_history else 0
        }

# Use realistic backtester
backtester = RealisticBacktester(simulator)

# Execute strategy orders
strategy_orders = [
    Order("strat_1", "AAPL", OrderSide.BUY, OrderType.MARKET, 1000),
    Order("strat_2", "AAPL", OrderSide.SELL, OrderType.MARKET, 500),
]

for order in strategy_orders:
    await backtester.execute_strategy_order(order, market_data)

# Get results
summary = backtester.get_portfolio_summary()
print("Portfolio Summary:", summary)
```

## Performance Considerations

### Optimization Tips

1. **Batch Processing**: Process multiple orders together when possible
2. **Caching**: Cache regime detection results for similar market conditions
3. **Vectorization**: Use numpy for mathematical calculations when available
4. **Memory Management**: Limit history size to prevent memory bloat

```python
# Optimized simulator configuration
optimized_simulator = RealisticMarketSimulator(
    cost_model=TransactionCostModel(
        # Use simpler calculations for better performance
        volatility_adjustment=0.0  # Disable if not needed
    )
)

# Batch execution simulation
async def batch_simulate_executions(orders, market_data):
    """Simulate multiple orders efficiently"""
    all_executions = []
    current_market_data = market_data
    
    for order in orders:
        executions = await optimized_simulator.simulate_execution(order, current_market_data)
        all_executions.extend(executions)
        
        # Update market data less frequently for performance
        if len(executions) > 0 and order.quantity > 1000:
            current_market_data = await optimized_simulator.simulate_market_impact(
                executions, current_market_data
            )
    
    return all_executions
```

## Error Handling

### Robust Error Handling

```python
async def safe_execution_simulation(order, market_data):
    """Safely simulate execution with error handling"""
    try:
        executions = await simulator.simulate_execution(order, market_data)
        
        if not executions:
            print(f"Warning: No execution for order {order.order_id}")
            return []
        
        # Validate execution results
        for execution in executions:
            if execution.price <= 0:
                print(f"Error: Invalid execution price for {execution.execution_id}")
                continue
            
            if execution.execution_quality < 0 or execution.execution_quality > 1:
                print(f"Warning: Invalid quality score for {execution.execution_id}")
        
        return executions
        
    except Exception as e:
        print(f"Error simulating execution for order {order.order_id}: {e}")
        return []

# Use safe execution
safe_executions = await safe_execution_simulation(order, market_data)
```

## Testing

### Unit Testing

```bash
# Run all simulation tests
python -m pytest tests/test_realistic_market_simulation.py -v

# Run specific test categories
python -m pytest tests/test_realistic_market_simulation.py::TestMarketRegimeDetector -v
python -m pytest tests/test_realistic_market_simulation.py::TestTransactionCostCalculator -v
python -m pytest tests/test_realistic_market_simulation.py::TestSlippageCalculator -v

# Run integration test
python -m pytest tests/test_realistic_market_simulation.py::test_integration_scenario -v
```

### Custom Testing

```python
# Create test scenarios
async def test_custom_scenario():
    """Test custom trading scenario"""
    simulator = RealisticMarketSimulator()
    
    # Test data
    test_market_data = MarketData(
        timestamp=datetime.now(),
        symbol="TEST",
        bid_price=100.0,
        ask_price=100.1,
        bid_size=1000,
        ask_size=1000,
        last_price=100.05,
        volume=1000000,
        volatility=0.02,
        liquidity_score=0.8,
        spread_bps=10.0,
        market_impact_factor=1.0
    )
    
    test_order = Order(
        order_id="test_order",
        symbol="TEST",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=1000,
        timestamp=datetime.now()
    )
    
    # Execute test
    executions = await simulator.simulate_execution(test_order, test_market_data)
    
    # Validate results
    assert len(executions) > 0, "Should have at least one execution"
    assert executions[0].quantity > 0, "Execution quantity should be positive"
    assert executions[0].price > 0, "Execution price should be positive"
    assert 0 <= executions[0].execution_quality <= 1, "Quality should be between 0 and 1"
    
    print("Custom test scenario passed!")

# Run custom test
asyncio.run(test_custom_scenario())
```

## Best Practices

1. **Model Calibration**: Regularly calibrate cost and slippage models using real execution data
2. **Regime Awareness**: Always consider market regime when interpreting simulation results
3. **Liquidity Modeling**: Use realistic liquidity models based on actual market depth data
4. **Cost Attribution**: Break down execution costs to understand their sources
5. **Quality Monitoring**: Track execution quality metrics to validate simulation accuracy
6. **Scenario Testing**: Test extreme scenarios (crisis, low liquidity) to understand edge cases
7. **Performance Validation**: Compare simulation results with actual execution data when available

## Future Enhancements

Planned improvements:

- **Machine Learning Models**: ML-based cost and slippage prediction
- **Real-Time Calibration**: Dynamic model parameter adjustment
- **Cross-Asset Models**: Specialized models for different asset classes
- **Venue-Specific Modeling**: Different models for different execution venues
- **Intraday Patterns**: More sophisticated time-of-day modeling
- **Correlation Effects**: Cross-asset correlation impact on execution

## API Reference

### RealisticMarketSimulator

Main simulation class.

#### Methods

- `simulate_execution(order, market_data)`: Simulate order execution
- `simulate_market_impact(executions, market_data)`: Simulate market impact
- `get_simulation_statistics()`: Get simulation statistics

### MarketRegimeDetector

Market regime detection.

#### Methods

- `detect_regime(price_history, volatility_history)`: Detect current market regime

### TransactionCostCalculator

Transaction cost calculation.

#### Methods

- `calculate_costs(order, market_data, execution_price, regime)`: Calculate comprehensive costs

### SlippageCalculator

Slippage calculation.

#### Methods

- `calculate_slippage(order, market_data, regime)`: Calculate execution slippage

### LiquiditySimulator

Liquidity simulation.

#### Methods

- `calculate_available_liquidity(market_data, timestamp)`: Calculate available liquidity
- `simulate_partial_fill(order, available_liquidity, market_data)`: Simulate partial fills

## Examples

See `nautilus_trader_engine/backtesting/realistic_market_simulation.py` for the complete example in the `example_usage()` function, which demonstrates:

- Custom cost and slippage model configuration
- Order execution simulation with different order types and sizes
- Market impact simulation
- Execution quality analysis
- Comprehensive simulation statistics