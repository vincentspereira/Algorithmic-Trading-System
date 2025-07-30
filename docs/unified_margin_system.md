# Unified Margin System Documentation

## Overview

The Unified Margin System provides comprehensive margin calculation and management across all asset classes, including equities, options, futures, bonds, forex, and cryptocurrencies. It implements industry-standard margin methodologies including SPAN margin for futures, portfolio margin benefits, and advanced optimization strategies.

## Key Features

- **Multi-Asset Margin Calculation**: Unified system supporting all major asset classes
- **SPAN Margin Implementation**: Standard Portfolio Analysis of Risk for futures and options
- **Portfolio Margin Benefits**: Cross-margining and diversification benefits
- **Real-Time Compliance Monitoring**: Automated compliance checking and alerting
- **Margin Optimization**: AI-powered suggestions for capital efficiency
- **Risk-Based Adjustments**: Dynamic margin requirements based on volatility and risk metrics

## Architecture

### Core Components

1. **Asset-Specific Calculators**: Specialized margin calculation for each asset class
2. **SPAN Calculator**: Industry-standard SPAN margin implementation
3. **Portfolio Calculator**: Cross-margining and diversification benefits
4. **Margin Optimizer**: Capital efficiency optimization engine
5. **Unified System**: Main orchestration and compliance engine

### Supported Asset Classes

- **Equities**: Standard and portfolio margin with volatility adjustments
- **Options**: Long/short options with Greeks-based risk assessment
- **Futures**: SPAN margin with scenario-based risk analysis
- **Bonds**: Duration-based margin requirements
- **Forex**: Currency pair margin with leverage limits
- **Cryptocurrencies**: High-volatility adjusted margin requirements

## Usage Examples

### Basic Setup

```python
import asyncio
from datetime import datetime
from nautilus_trader_engine.risk.unified_margin_system import (
    UnifiedMarginSystem, Position, AssetClass
)

# Initialize the margin system
margin_system = UnifiedMarginSystem()
```

### Creating Positions

```python
# Create equity position
equity_position = Position(
    symbol="AAPL",
    asset_class=AssetClass.EQUITY,
    quantity=100,
    current_price=150.0,
    market_value=15000.0,
    volatility=0.25,
    beta=1.2
)

# Create options position
option_position = Position(
    symbol="AAPL240315C00160000",
    asset_class=AssetClass.OPTION,
    quantity=-2,  # Short position
    current_price=5.0,
    market_value=-1000.0,
    underlying_symbol="AAPL",
    strike_price=160.0,
    option_type="call",
    delta=0.6,
    gamma=0.05,
    theta=-0.02,
    vega=0.15,
    volatility=0.25
)

# Create futures position
futures_position = Position(
    symbol="ES_202406",
    asset_class=AssetClass.FUTURE,
    quantity=1,
    current_price=4500.0,
    market_value=225000.0,
    volatility=0.20
)
```

### Comprehensive Margin Calculation

```python
async def calculate_portfolio_margin():
    positions = [equity_position, option_position, futures_position]
    available_capital = 100000.0
    
    # Calculate comprehensive margin
    result = await margin_system.calculate_comprehensive_margin(
        positions, available_capital
    )
    
    # Access results
    portfolio_margin = result["portfolio_margin"]
    individual_margins = result["individual_margins"]
    optimization = result["optimization"]
    compliance = result["compliance"]
    summary = result["summary"]
    
    print(f"Total Margin Required: ${portfolio_margin.total_margin_required:,.2f}")
    print(f"Portfolio Leverage: {portfolio_margin.portfolio_leverage:.2f}x")
    print(f"Margin Utilization: {portfolio_margin.margin_utilization:.1%}")
    
    return result

# Run the calculation
result = asyncio.run(calculate_portfolio_margin())
```

### Individual Asset Class Calculations

```python
from nautilus_trader_engine.risk.unified_margin_system import (
    EquityMarginCalculator, OptionsMarginCalculator, SPANMarginCalculator
)

async def calculate_individual_margins():
    # Equity margin
    equity_calc = EquityMarginCalculator()
    equity_margin = await equity_calc.calculate_margin(equity_position)
    print(f"Equity Margin: ${equity_margin.required_margin:,.2f}")
    
    # Options margin
    options_calc = OptionsMarginCalculator()
    option_margin = await options_calc.calculate_margin(option_position)
    print(f"Options Margin: ${option_margin.required_margin:,.2f}")
    
    # SPAN margin for futures
    span_calc = SPANMarginCalculator()
    span_margins = await span_calc.calculate_span_margin([futures_position])
    for symbol, margin in span_margins.items():
        print(f"SPAN Margin for {symbol}: ${margin.required_margin:,.2f}")

asyncio.run(calculate_individual_margins())
```

### Margin Optimization

```python
from nautilus_trader_engine.risk.unified_margin_system import MarginOptimizer

async def optimize_margin_usage():
    optimizer = MarginOptimizer()
    
    positions = [equity_position, option_position]
    available_capital = 50000.0
    target_leverage = 2.0
    
    optimization_result = await optimizer.optimize_margin_usage(
        positions, available_capital, target_leverage
    )
    
    print("Optimization Suggestions:")
    for suggestion in optimization_result["optimization_suggestions"]:
        print(f"- {suggestion.get('strategy', suggestion.get('type'))}")
    
    improvements = optimization_result["potential_improvements"]
    print(f"Potential margin reduction: ${improvements['margin_reduction']:,.2f}")
    print(f"Capital efficiency improvement: {improvements['capital_efficiency']:.1f}%")

asyncio.run(optimize_margin_usage())
```

### Trade Impact Simulation

```python
async def simulate_trade_impact():
    current_positions = [equity_position, option_position]
    
    # Proposed new trades
    proposed_trades = [
        {
            "symbol": "GOOGL",
            "quantity": 20,
            "price": 2800.0,
            "asset_class": AssetClass.EQUITY
        },
        {
            "symbol": "TSLA",
            "quantity": 50,
            "price": 200.0,
            "asset_class": AssetClass.EQUITY
        }
    ]
    
    impact = await margin_system.simulate_margin_impact(
        current_positions, proposed_trades
    )
    
    print(f"Current Margin: ${impact['current_margin']:,.2f}")
    print(f"New Margin: ${impact['new_margin']:,.2f}")
    print(f"Margin Change: ${impact['margin_change']:,.2f}")
    print(f"Leverage Change: {impact['leverage_change']:.2f}x")
    print(f"Recommendation: {impact['recommendation'].upper()}")

asyncio.run(simulate_trade_impact())
```

## Margin Calculation Methods

### Equity Margin

Standard equity margin calculation with risk-based adjustments:

- **Long Positions**: 50% initial margin (customizable)
- **Short Positions**: 150% initial margin
- **Volatility Adjustment**: Higher volatility increases margin requirements
- **Beta Adjustment**: Higher beta stocks require additional margin

```python
# Margin calculation formula for long equity:
# Adjusted Margin = Market Value × Margin Rate × (1 + Volatility × 2) × (1 + |Beta - 1| × 0.5)
```

### Options Margin

Comprehensive options margin supporting various strategies:

- **Long Options**: Premium paid only, no additional margin
- **Short Options**: Standard margin calculation with Greeks adjustments
- **Covered Positions**: Reduced margin for covered calls/puts
- **Spread Strategies**: Net margin requirements for complex strategies

```python
# Short call margin formula:
# Margin = Premium + max(20% × Underlying - Out-of-Money, 10% × Underlying)
```

### SPAN Margin

Industry-standard SPAN (Standard Portfolio Analysis of Risk) implementation:

- **Risk Scenarios**: 16 standard price/volatility scenarios
- **Cross-Margining**: Benefits for offsetting positions
- **Commodity Grouping**: Positions grouped by underlying commodity
- **Minimum Charges**: Exchange-specified minimum margin amounts

### Portfolio Margin

Advanced portfolio margining with diversification benefits:

- **Cross-Asset Benefits**: Margin reduction for diversified portfolios
- **Correlation Analysis**: Dynamic correlation-based adjustments
- **Hedging Recognition**: Automatic detection of hedging strategies
- **Concentration Penalties**: Additional margin for concentrated positions

## Risk Management Features

### Real-Time Compliance

- **Leverage Limits**: Configurable maximum leverage ratios
- **Margin Buffers**: Safety buffers above minimum requirements
- **Position Limits**: Maximum position size controls
- **Concentration Limits**: Portfolio concentration monitoring

### Dynamic Adjustments

- **Volatility Scaling**: Real-time volatility-based margin adjustments
- **Market Regime Detection**: Increased margins during stressed markets
- **Liquidity Adjustments**: Higher margins for illiquid securities
- **Credit Quality**: Margin adjustments based on credit ratings

### Optimization Strategies

- **Capital Efficiency**: Maximize trading capacity within risk limits
- **Hedging Suggestions**: Automated hedging strategy recommendations
- **Cross-Margining**: Identify cross-margining opportunities
- **Position Sizing**: Optimal position sizing recommendations

## Configuration Options

### System Configuration

```python
margin_system = UnifiedMarginSystem()

# Configure system parameters
margin_system.margin_buffer = 0.10  # 10% buffer above required margin
margin_system.max_leverage = 3.0    # Maximum 3:1 leverage
```

### Asset-Specific Configuration

```python
# Equity calculator configuration
equity_calc = EquityMarginCalculator()
equity_calc.default_initial_margin_rate = 0.60  # 60% for long positions
equity_calc.short_margin_rate = 1.75            # 175% for short positions

# SPAN calculator configuration
span_calc = SPANMarginCalculator()
span_calc.default_price_scan_range = 0.08       # 8% price scan range
span_calc.default_volatility_scan_range = 0.40  # 40% volatility scan range
```

## Data Structures

### Position

```python
@dataclass
class Position:
    symbol: str
    asset_class: AssetClass
    quantity: float
    current_price: float
    market_value: float
    
    # Optional asset-specific attributes
    underlying_symbol: Optional[str] = None
    strike_price: Optional[float] = None
    expiry_date: Optional[datetime] = None
    option_type: Optional[str] = None
    
    # Risk attributes
    volatility: float = 0.0
    beta: float = 1.0
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
```

### MarginRequirement

```python
@dataclass
class MarginRequirement:
    position_id: str
    margin_type: MarginType
    required_margin: float
    excess_margin: float
    margin_utilization: float
    
    # Breakdown
    initial_margin: float = 0.0
    maintenance_margin: float = 0.0
    portfolio_margin: float = 0.0
    
    # Risk metrics
    leverage: float = 1.0
    risk_score: float = 0.0
    
    # Calculation details
    calculation_method: str = ""
    risk_scenarios: Dict[str, float] = field(default_factory=dict)
```

### PortfolioMarginResult

```python
@dataclass
class PortfolioMarginResult:
    total_margin_required: float
    total_excess_margin: float
    portfolio_leverage: float
    margin_utilization: float
    
    # By asset class
    margin_by_asset_class: Dict[str, float]
    
    # Risk metrics
    portfolio_var: float = 0.0
    diversification_benefit: float = 0.0
    concentration_risk: float = 0.0
    
    # Optimization
    optimization_opportunities: List[str]
    potential_savings: float = 0.0
```

## Performance Considerations

- **Async Processing**: Non-blocking margin calculations
- **Caching**: Intelligent caching of calculation results
- **Vectorized Operations**: NumPy-based calculations for performance
- **Parallel Processing**: Concurrent calculation of individual margins

## Error Handling

The system includes comprehensive error handling:

- **Graceful Degradation**: Fallback calculations when data is missing
- **Validation**: Input data validation and sanitization
- **Logging**: Detailed logging of calculation failures
- **Recovery**: Automatic recovery from transient failures

## Testing

Run the comprehensive test suite:

```bash
# Run all margin system tests
python -m pytest tests/test_unified_margin_system.py -v

# Run specific test categories
python -m pytest tests/test_unified_margin_system.py::TestEquityMarginCalculator -v
python -m pytest tests/test_unified_margin_system.py::TestOptionsMarginCalculator -v
python -m pytest tests/test_unified_margin_system.py::TestSPANMarginCalculator -v

# Run integration test
python -m pytest tests/test_unified_margin_system.py::test_integration_scenario -v
```

## Integration with Trading System

The Unified Margin System integrates with:

- **Order Management System**: Pre-trade margin checks
- **Risk Management System**: Real-time risk monitoring
- **Portfolio Management**: Position sizing and optimization
- **Compliance System**: Regulatory compliance monitoring

## Regulatory Compliance

The system supports various regulatory requirements:

- **Reg T**: Federal Reserve margin requirements
- **FINRA Rules**: Broker-dealer margin rules
- **Exchange Requirements**: Exchange-specific margin rules
- **International Standards**: Support for global margin standards

## Future Enhancements

Planned improvements:

- **Machine Learning**: AI-powered margin optimization
- **Real-Time Streaming**: Continuous margin monitoring
- **Advanced Strategies**: Support for complex multi-leg strategies
- **Stress Testing**: Integration with stress testing framework
- **Cloud Scaling**: Distributed calculation capabilities

## API Reference

### UnifiedMarginSystem

Main system class for comprehensive margin management.

#### Methods

- `calculate_comprehensive_margin(positions, available_capital)`: Complete margin analysis
- `simulate_margin_impact(current_positions, proposed_trades)`: Trade impact simulation
- Individual calculator access via properties

### Component Calculators

- `EquityMarginCalculator`: Equity margin calculations
- `OptionsMarginCalculator`: Options margin with Greeks
- `SPANMarginCalculator`: SPAN margin for futures/options
- `PortfolioMarginCalculator`: Portfolio-level calculations
- `MarginOptimizer`: Capital efficiency optimization

## Examples

See `nautilus_trader_engine/risk/unified_margin_system.py` for the complete example in the `example_usage()` function, which demonstrates:

- Multi-asset portfolio margin calculation
- Individual position margin requirements
- Optimization suggestions
- Compliance monitoring
- Trade impact simulation