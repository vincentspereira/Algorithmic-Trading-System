# Portfolio Optimization and Observability System

## Overview

The Portfolio Optimization and Observability System is an advanced portfolio management solution that integrates with the Nautilus Trader portfolio system. It provides comprehensive portfolio optimization capabilities using multiple methods and risk measures, along with real-time monitoring, metrics collection, and alerting functionality.

## Key Features

### Portfolio Optimization
- **Multiple Optimization Methods**: Mean-Variance, Black-Litterman, Hierarchical Risk Parity, Risk Parity, and more
- **Advanced Risk Measures**: Standard Deviation, CVaR, MAD, GMD, VaR, Max Drawdown, CDaR, and 20+ other risk measures
- **Constraint Handling**: Short positions, position limits, turnover constraints, transaction costs
- **Regularization**: L2 regularization to reduce negligible weights
- **Discrete Allocation**: Convert continuous weights to actual share allocations

### Portfolio Observability
- **Real-time Metrics**: Portfolio value, P&L, risk metrics, diversification measures
- **Risk Monitoring**: VaR, CVaR, drawdown, concentration risk, liquidity risk
- **Performance Attribution**: Asset, sector, and factor contribution analysis
- **Alerting System**: Configurable alerts for risk thresholds, performance metrics
- **Comprehensive Reporting**: Detailed portfolio reports with historical analysis

### Integration Capabilities
- **Nautilus Trader Integration**: Seamless integration with Nautilus Trader portfolio system
- **Market Data Handling**: Support for various market data sources and formats
- **Rebalancing Signals**: Automatic generation of rebalancing signals based on optimization results
- **Event-driven Architecture**: Integration with Nautilus Trader event system

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Nautilus Trader Engine                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐    ┌───────────────────────────────┐   │
│  │   Portfolio     │    │        Cache System           │   │
│  │   System        │◄──►│                               │   │
│  └─────────────────┘    └───────────────────────────────┘   │
│           ▲                                                 │
│           │                                                 │
│  ┌─────────────────┐                                        │
│  │  Portfolio      │                                        │
│  │  Integration    │                                        │
│  │  System         │                                        │
│  └─────────────────┘                                        │
│           ▲                                                 │
│    ┌──────┴──────┐                                          │
│    │             │                                          │
│┌────────────┐ ┌──────────────┐                             │
││  Portfolio │ │   Portfolio  │                             │
││Optimization│ │Observability │                             │
│└────────────┘ └──────────────┘                             │
│    │             │                                          │
│┌────────────┐ ┌──────────────┐                             │
││PyPortfolio │ │ Riskfolio-   │                             │
││Opt Library │ │ Lib Library  │                             │
│└────────────┘ └──────────────┘                             │
└─────────────────────────────────────────────────────────────┘
```

## Installation

### Requirements

The system requires the following Python packages:

```bash
# Core dependencies
numpy>=1.24.0
pandas>=2.0.0
scipy>=1.10.0

# Portfolio Optimization Libraries
pyportfolioopt>=1.5.0
riskfolio-lib>=5.0.0

# Mathematical optimization
cvxpy>=1.3.0
scs>=3.2.0

# Visualization (optional)
matplotlib>=3.7.0
seaborn>=0.12.0

# Monitoring and Observability
prometheus-client>=0.17.0
psutil>=5.9.0
```

Install the requirements:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Portfolio Optimization

```python
from portfolio_optimization import PortfolioOptimizer, PortfolioOptimizationConfig
from portfolio_optimization import OptimizationMethod

# Configure optimization
config = PortfolioOptimizationConfig(
    method=OptimizationMethod.MAXIMUM_SHARPE,
    risk_free_rate=0.02,
    allow_short=False,
    l2_regularization=0.1
)

# Create optimizer
optimizer = PortfolioOptimizer(config)

# Optimize portfolio (returns_data is a pandas DataFrame of asset returns)
result = optimizer.optimize_portfolio(returns_data)

print(f"Expected Return: {result.expected_return:.2%}")
print(f"Risk: {result.risk:.2%}")
print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
```

### Portfolio Observability

```python
from portfolio_observability import PortfolioObservability

# Create observability system
observability = PortfolioObservability(portfolio)

# Start monitoring
await observability.start()

# Collect metrics
await observability.collect_portfolio_metrics()

# Get portfolio metrics
metrics = observability.get_portfolio_metrics()

# Calculate risk metrics
risk_metrics = observability.calculate_risk_metrics(returns)

# Generate report
report = observability.generate_portfolio_report()
```

### Integrated System

```python
from portfolio_integration import IntegratedPortfolioSystem

# Create integrated system
integrated_system = IntegratedPortfolioSystem(
    portfolio=nautilus_portfolio,
    cache=nautilus_cache
)

# Start system
await integrated_system.start()

# Optimize portfolio
optimization_result = await integrated_system.optimize_portfolio(market_data)

# Generate comprehensive report
report = await integrated_system.generate_portfolio_report()

# Stop system
await integrated_system.stop()
```

## Configuration Options

### PortfolioOptimizationConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| method | OptimizationMethod | MEAN_VARIANCE | Optimization method to use |
| risk_measure | RiskMeasure | STANDARD_DEVIATION | Risk measure for optimization |
| target_return | float | None | Target return for optimization |
| target_risk | float | None | Target risk for optimization |
| risk_free_rate | float | 0.02 | Risk-free rate |
| risk_aversion | float | 1.0 | Risk aversion parameter |
| allow_short | bool | False | Allow short positions |
| max_short_weight | float | 0.3 | Maximum short position weight |
| max_long_weight | float | 1.0 | Maximum long position weight |
| l2_regularization | float | 0.0 | L2 regularization parameter |
| use_black_litterman | bool | False | Use Black-Litterman model |
| use_hierarchical | bool | False | Use Hierarchical Risk Parity |
| confidence_level | float | 0.95 | Confidence level for risk measures |

## Risk Measures

The system supports 24+ convex risk measures:

### Dispersion Risk Measures
- Standard Deviation
- Variance
- Mean Absolute Deviation (MAD)
- Gini Mean Difference (GMD)
- Range

### Downside Risk Measures
- Semi Standard Deviation
- Conditional Value at Risk (CVaR)
- Tail Gini
- Entropic Value at Risk (EVaR)
- Worst Case Realization (Minimax)

### Drawdown Risk Measures
- Average Drawdown
- Ulcer Index
- Conditional Drawdown at Risk (CDaR)
- Entropic Drawdown at Risk (EDaR)
- Maximum Drawdown

## Optimization Methods

### Classical Methods
- **Mean-Variance Optimization**: Traditional Markowitz optimization
- **Minimum Variance**: Minimum risk portfolio
- **Maximum Sharpe**: Maximum risk-adjusted return
- **Maximum Return**: Maximum expected return
- **Risk Parity**: Equal risk contribution from all assets

### Advanced Methods
- **Black-Litterman**: Incorporate investor views with market equilibrium
- **Hierarchical Risk Parity**: Tree-based clustering approach
- **CVaR Optimization**: Optimize for Conditional Value at Risk
- **Semivariance Optimization**: Focus on downside risk only

## API Reference

### PortfolioOptimizer

#### Methods
- `optimize_portfolio(returns_data, market_caps=None, views=None, confidence=None)`: Optimize portfolio
- `generate_discrete_allocation(weights, latest_prices, total_portfolio_value)`: Convert to discrete shares
- `get_optimization_history()`: Get history of optimizations

#### Properties
- `config`: Current configuration
- `_previous_weights`: Previous portfolio weights
- `_optimization_history`: History of optimizations

### PortfolioObservability

#### Methods
- `start()`: Start observability system
- `stop()`: Stop observability system
- `collect_portfolio_metrics()`: Collect current metrics
- `calculate_risk_metrics(returns, benchmark_returns=None)`: Calculate risk metrics
- `calculate_performance_attribution()`: Calculate performance attribution
- `generate_portfolio_report()`: Generate comprehensive report
- `add_alert(alert_type, message, severity)`: Add alert
- `get_alerts(hours=24, severity=None)`: Get recent alerts

#### Properties
- `portfolio`: Linked Nautilus Trader portfolio
- `_historical_metrics`: Historical metrics data
- `_risk_metrics`: Risk metrics history
- `_alerts`: Alert history

### IntegratedPortfolioSystem

#### Methods
- `start()`: Start integrated system
- `stop()`: Stop integrated system
- `optimize_portfolio(market_data, market_caps=None, views=None, confidence=None)`: Optimize portfolio
- `collect_market_data(instrument_ids, lookback_period=252)`: Collect market data
- `get_portfolio_summary()`: Get portfolio summary
- `generate_portfolio_report()`: Generate detailed report
- `get_instrument_exposure(instrument_id)`: Get instrument exposure
- `rebalance_portfolio(target_weights)`: Rebalance portfolio

## Testing

The system includes comprehensive tests:

```bash
# Run tests
python -m pytest test_portfolio_system.py -v
```

## Example Usage

See `portfolio_example.py` for a complete demonstration of the system capabilities.

## Integration with Nautilus Trader

The system integrates with Nautilus Trader through:

1. **Portfolio Interface**: Uses the existing Portfolio and PortfolioFacade classes
2. **Event System**: Integrates with the Nautilus message bus for event handling
3. **Cache System**: Uses the Nautilus cache for market data and instrument information
4. **Metrics Collection**: Integrates with the existing monitoring infrastructure

## Performance Considerations

1. **Computational Complexity**: Some optimization methods (especially with many constraints) can be computationally intensive
2. **Memory Usage**: Historical metrics are stored in memory with automatic cleanup
3. **Real-time Processing**: The system is designed for real-time monitoring with configurable update frequencies
4. **Scalability**: Can handle portfolios with hundreds of assets

## Troubleshooting

### Common Issues

1. **Optimization Fails to Converge**: Try adjusting constraints or using regularization
2. **Missing Data**: Ensure complete market data for all assets
3. **Memory Issues**: Reduce historical data retention period
4. **Performance Problems**: Use simpler optimization methods for large portfolios

### Error Handling

The system includes comprehensive error handling with detailed logging. All exceptions are caught and logged with context information.

## Contributing

Contributions are welcome! Please follow the existing code style and include tests for new functionality.

## License

This system is part of the Algorithmic Trading System project and follows the same licensing terms.