# Multi-Strategy Portfolio Testing

## Overview

The Multi-Strategy Portfolio Testing framework provides comprehensive capabilities for testing and optimizing portfolios composed of multiple trading strategies. This system enables sophisticated portfolio construction, risk management, and performance analysis across diverse strategy types.

## Key Features

### Portfolio Construction Methods
- **Equal Weight**: Simple equal allocation across strategies
- **Risk Parity**: Allocates based on equal risk contribution
- **Minimum Variance**: Minimizes portfolio volatility
- **Mean Variance**: Markowitz optimization balancing return and risk
- **Maximum Diversification**: Maximizes diversification ratio
- **Risk Budgeting**: Allocates based on predefined risk budgets
- **Black-Litterman**: Bayesian approach incorporating market views
- **Hierarchical Risk Parity**: Advanced diversification using clustering

### Correlation Analysis
- **Correlation Matrix**: Full correlation analysis between strategies
- **Diversification Metrics**: Effective number of strategies and diversification ratios
- **Cluster Detection**: Identifies groups of highly correlated strategies
- **Dynamic Correlation**: Rolling correlation analysis over time

### Risk Attribution
- **Component Risk**: Individual strategy risk contributions
- **Marginal Risk**: Impact of small allocation changes
- **Risk Budgeting**: Actual vs target risk allocations
- **Concentration Risk**: Portfolio concentration measures
- **Diversification Benefit**: Quantifies diversification effects

### Rebalancing Framework
- **Multiple Frequencies**: Daily, weekly, monthly, quarterly, annual
- **Threshold-Based**: Rebalance when allocations drift beyond limits
- **Transaction Costs**: Realistic cost modeling and optimization
- **Turnover Analysis**: Portfolio turnover tracking and optimization

## Architecture

### Core Components

```python
# Strategy Definition
@dataclass
class Strategy:
    name: str
    returns: pd.Series
    description: str = ""
    strategy_type: str = "generic"
    target_allocation: Optional[float] = None
    min_allocation: float = 0.0
    max_allocation: float = 1.0
    risk_budget: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

# Portfolio Constraints
@dataclass
class PortfolioConstraints:
    min_weight: float = 0.0
    max_weight: float = 1.0
    max_concentration: float = 0.5
    min_strategies: int = 1
    max_strategies: Optional[int] = None
    target_volatility: Optional[float] = None
    max_tracking_error: Optional[float] = None
    turnover_limit: Optional[float] = None
    sector_limits: Dict[str, float] = field(default_factory=dict)
    correlation_limit: float = 0.95
```

### Main Testing Framework

```python
class MultiStrategyPortfolioTester:
    """Main multi-strategy portfolio testing framework"""
    
    async def test_portfolio(self,
                           portfolio_name: str,
                           strategies: List[Strategy],
                           allocation_method: AllocationMethod = AllocationMethod.RISK_PARITY,
                           constraints: Optional[PortfolioConstraints] = None,
                           rebalancing_frequency: RebalancingFrequency = RebalancingFrequency.MONTHLY,
                           transaction_cost_bps: float = 5.0,
                           lookback_window: int = 252) -> PortfolioTestResult
```

## Usage Examples

### Basic Portfolio Testing

```python
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime
from nautilus_trader_engine.backtesting.multi_strategy_portfolio_testing import (
    MultiStrategyPortfolioTester,
    Strategy,
    AllocationMethod,
    RebalancingFrequency,
    PortfolioConstraints
)

async def test_basic_portfolio():
    # Create sample strategies
    dates = pd.date_range(start='2022-01-01', end='2023-12-31', freq='D')
    
    # Momentum strategy
    momentum_returns = np.random.normal(0.0008, 0.018, len(dates))
    momentum_strategy = Strategy(
        name="Momentum",
        returns=pd.Series(momentum_returns, index=dates),
        description="Momentum-based trading strategy",
        strategy_type="momentum",
        risk_budget=0.4
    )
    
    # Mean reversion strategy
    mean_reversion_returns = np.random.normal(0.0006, 0.015, len(dates))
    mean_reversion_strategy = Strategy(
        name="MeanReversion",
        returns=pd.Series(mean_reversion_returns, index=dates),
        description="Mean reversion trading strategy",
        strategy_type="mean_reversion",
        risk_budget=0.3
    )
    
    # Trend following strategy
    trend_returns = np.random.normal(0.0007, 0.020, len(dates))
    trend_strategy = Strategy(
        name="TrendFollowing",
        returns=pd.Series(trend_returns, index=dates),
        description="Trend following strategy",
        strategy_type="trend_following",
        risk_budget=0.3
    )
    
    strategies = [momentum_strategy, mean_reversion_strategy, trend_strategy]
    
    # Create portfolio tester
    tester = MultiStrategyPortfolioTester()
    
    # Test portfolio with risk parity allocation
    result = await tester.test_portfolio(
        portfolio_name="DiversifiedPortfolio",
        strategies=strategies,
        allocation_method=AllocationMethod.RISK_PARITY,
        rebalancing_frequency=RebalancingFrequency.MONTHLY,
        transaction_cost_bps=5.0
    )
    
    # Display results
    print(f"Portfolio: {result.portfolio_name}")
    print(f"Expected Return: {result.allocation_result.expected_return:.2%}")
    print(f"Expected Volatility: {result.allocation_result.expected_volatility:.2%}")
    print(f"Sharpe Ratio: {result.allocation_result.sharpe_ratio:.3f}")
    
    print("\\nStrategy Allocations:")
    for strategy_name, weight in result.allocation_result.weights.items():
        print(f"  {strategy_name}: {weight:.1%}")
    
    return result

# Run the test
result = asyncio.run(test_basic_portfolio())
```

### Advanced Portfolio Optimization

```python
async def test_advanced_portfolio():
    # Create strategies with different characteristics
    strategies = create_diverse_strategies()
    
    # Define portfolio constraints
    constraints = PortfolioConstraints(
        min_weight=0.05,
        max_weight=0.6,
        max_concentration=0.5,
        min_strategies=2,
        max_strategies=6,
        target_volatility=0.15,
        turnover_limit=0.5
    )
    
    tester = MultiStrategyPortfolioTester()
    
    # Test multiple allocation methods
    allocation_methods = [
        AllocationMethod.EQUAL_WEIGHT,
        AllocationMethod.RISK_PARITY,
        AllocationMethod.MINIMUM_VARIANCE,
        AllocationMethod.MAXIMUM_DIVERSIFICATION,
        AllocationMethod.RISK_BUDGETING
    ]
    
    results = []
    for method in allocation_methods:
        result = await tester.test_portfolio(
            portfolio_name=f"Portfolio_{method.value}",
            strategies=strategies,
            allocation_method=method,
            constraints=constraints,
            rebalancing_frequency=RebalancingFrequency.MONTHLY,
            transaction_cost_bps=8.0
        )
        results.append(result)
    
    # Compare results
    best_sharpe = max(results, key=lambda r: r.portfolio_performance.sharpe_ratio)
    best_return = max(results, key=lambda r: r.portfolio_performance.annualized_return)
    lowest_vol = min(results, key=lambda r: r.portfolio_performance.volatility)
    
    print(f"Best Sharpe Ratio: {best_sharpe.portfolio_name} ({best_sharpe.portfolio_performance.sharpe_ratio:.3f})")
    print(f"Best Return: {best_return.portfolio_name} ({best_return.portfolio_performance.annualized_return:.2%})")
    print(f"Lowest Volatility: {lowest_vol.portfolio_name} ({lowest_vol.portfolio_performance.volatility:.2%})")
    
    return results
```

### Correlation and Risk Analysis

```python
def analyze_portfolio_risk(result: PortfolioTestResult):
    """Analyze portfolio risk characteristics"""
    
    print(f"=== Risk Analysis for {result.portfolio_name} ===")
    
    # Correlation Analysis
    corr = result.correlation_analysis
    print(f"\\nCorrelation Analysis:")
    print(f"  Average Correlation: {corr.average_correlation:.3f}")
    print(f"  Max Correlation: {corr.max_correlation:.3f}")
    print(f"  Min Correlation: {corr.min_correlation:.3f}")
    print(f"  Diversification Ratio: {corr.diversification_ratio:.3f}")
    print(f"  Effective Strategies: {corr.effective_strategies:.1f}")
    
    if corr.correlation_clusters:
        print(f"  Correlation Clusters:")
        for i, cluster in enumerate(corr.correlation_clusters):
            print(f"    Cluster {i+1}: {', '.join(cluster)}")
    
    # Risk Attribution
    risk = result.risk_attribution
    print(f"\\nRisk Attribution:")
    print(f"  Diversification Benefit: {risk.diversification_benefit:.2%}")
    print(f"  Concentration Risk: {risk.concentration_risk:.3f}")
    
    print(f"  Strategy Risk Contributions:")
    for strategy_name, contribution in risk.strategy_risk_contributions.items():
        percentage = risk.strategy_risk_percentages.get(strategy_name, 0)
        print(f"    {strategy_name}: {contribution:.4f} ({percentage:.1%})")
    
    # Performance Metrics
    perf = result.portfolio_performance
    print(f"\\nPerformance Metrics:")
    print(f"  Total Return: {perf.total_return:.2%}")
    print(f"  Annualized Return: {perf.annualized_return:.2%}")
    print(f"  Volatility: {perf.volatility:.2%}")
    print(f"  Sharpe Ratio: {perf.sharpe_ratio:.3f}")
    print(f"  Sortino Ratio: {perf.sortino_ratio:.3f}")
    print(f"  Max Drawdown: {perf.max_drawdown:.2%}")
    print(f"  Win Rate: {perf.win_rate:.2%}")
    print(f"  VaR (95%): {perf.var_95:.2%}")
    print(f"  CVaR (95%): {perf.cvar_95:.2%}")
```

### Rebalancing Analysis

```python
def analyze_rebalancing(result: PortfolioTestResult):
    """Analyze portfolio rebalancing characteristics"""
    
    print(f"=== Rebalancing Analysis for {result.portfolio_name} ===")
    
    print(f"Total Transaction Costs: {result.transaction_costs:.4f}")
    print(f"Number of Rebalancing Events: {len(result.rebalancing_history)}")
    
    if result.rebalancing_history:
        turnovers = [rb['turnover'] for rb in result.rebalancing_history]
        costs = [rb['transaction_cost'] for rb in result.rebalancing_history]
        
        print(f"Average Turnover: {np.mean(turnovers):.2%}")
        print(f"Max Turnover: {np.max(turnovers):.2%}")
        print(f"Average Transaction Cost: {np.mean(costs):.4f}")
        
        # Show recent rebalancing events
        print(f"\\nRecent Rebalancing Events:")
        for rb in result.rebalancing_history[-3:]:
            print(f"  Date: {rb['date'].strftime('%Y-%m-%d')}")
            print(f"  Turnover: {rb['turnover']:.2%}")
            print(f"  Cost: {rb['transaction_cost']:.4f}")
            print(f"  Weights: {', '.join([f'{k}: {v:.1%}' for k, v in rb['weights'].items()])}")
            print()
```

## Performance Metrics

### Portfolio-Level Metrics
- **Total Return**: Cumulative portfolio return
- **Annualized Return**: Geometric mean annual return
- **Volatility**: Annualized standard deviation
- **Sharpe Ratio**: Risk-adjusted return measure
- **Sortino Ratio**: Downside risk-adjusted return
- **Calmar Ratio**: Return to maximum drawdown ratio
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Value at Risk (VaR)**: Potential loss at confidence level
- **Conditional VaR**: Expected loss beyond VaR threshold

### Risk Metrics
- **Component Risk**: Individual strategy risk contributions
- **Marginal Risk**: Risk impact of allocation changes
- **Diversification Benefit**: Risk reduction from diversification
- **Concentration Risk**: Portfolio concentration measures
- **Correlation Metrics**: Strategy correlation analysis

### Transaction Cost Analysis
- **Total Costs**: Cumulative transaction costs
- **Turnover**: Portfolio turnover rates
- **Cost per Rebalance**: Average cost per rebalancing event
- **Cost Impact**: Impact on net returns

## Best Practices

### Strategy Selection
1. **Diversification**: Choose strategies with low correlations
2. **Risk Characteristics**: Balance high and low volatility strategies
3. **Return Profiles**: Mix momentum, mean reversion, and trend strategies
4. **Time Horizons**: Include short and long-term strategies

### Portfolio Construction
1. **Risk Budgeting**: Set appropriate risk budgets for each strategy
2. **Constraints**: Define realistic weight and concentration limits
3. **Rebalancing**: Choose appropriate rebalancing frequency
4. **Transaction Costs**: Account for realistic trading costs

### Optimization Process
1. **Lookback Window**: Use sufficient historical data
2. **Method Selection**: Choose optimization method based on objectives
3. **Constraint Validation**: Ensure constraints are achievable
4. **Robustness Testing**: Test across different market conditions

### Risk Management
1. **Correlation Monitoring**: Track strategy correlations over time
2. **Risk Attribution**: Monitor individual strategy risk contributions
3. **Drawdown Control**: Implement drawdown limits
4. **Stress Testing**: Test portfolio under extreme scenarios

## Integration with Other Systems

### Backtesting Integration
```python
from nautilus_trader_engine.backtesting.walk_forward_optimization import WalkForwardOptimizer

# Combine with walk-forward optimization
wfo = WalkForwardOptimizer()
portfolio_tester = MultiStrategyPortfolioTester()

# Optimize portfolio allocation over time
optimized_results = await wfo.optimize_portfolio_allocation(
    strategies=strategies,
    portfolio_tester=portfolio_tester,
    optimization_window=252,
    rebalancing_frequency=RebalancingFrequency.QUARTERLY
)
```

### Performance Monitoring
```python
from nautilus_trader_engine.monitoring.performance_dashboard import PerformanceDashboard

# Create dashboard for portfolio monitoring
dashboard = PerformanceDashboard()
dashboard.add_portfolio_results(portfolio_results)
dashboard.generate_portfolio_report()
```

### Risk Management
```python
from nautilus_trader_engine.monitoring.intelligent_alerting import IntelligentAlerting

# Set up alerts for portfolio risk
alerting = IntelligentAlerting()
alerting.add_portfolio_risk_alerts(portfolio_result)
```

## Configuration

### Environment Variables
```bash
# Optional dependencies
SCIPY_AVAILABLE=true
SKLEARN_AVAILABLE=true

# Performance settings
PORTFOLIO_OPTIMIZATION_TIMEOUT=300
MAX_OPTIMIZATION_ITERATIONS=1000
CORRELATION_LOOKBACK_WINDOW=252
```

### Logging Configuration
```python
import logging

# Configure logging for portfolio testing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable detailed optimization logging
logging.getLogger('nautilus_trader_engine.backtesting.multi_strategy_portfolio_testing').setLevel(logging.DEBUG)
```

## Troubleshooting

### Common Issues

1. **Optimization Failures**
   - Check strategy return data quality
   - Verify constraint feasibility
   - Increase optimization iterations

2. **Poor Diversification**
   - Review strategy correlations
   - Consider additional strategy types
   - Adjust allocation constraints

3. **High Transaction Costs**
   - Reduce rebalancing frequency
   - Implement threshold-based rebalancing
   - Optimize turnover limits

4. **Memory Issues**
   - Reduce lookback window
   - Process strategies in batches
   - Use data sampling for large datasets

### Performance Optimization

1. **Parallel Processing**: Use async/await for concurrent operations
2. **Data Caching**: Cache correlation and covariance calculations
3. **Efficient Algorithms**: Use optimized numerical libraries
4. **Memory Management**: Process large datasets in chunks

## Future Enhancements

### Planned Features
- **Machine Learning Integration**: ML-based allocation methods
- **Alternative Risk Models**: Factor models and regime-aware optimization
- **Dynamic Rebalancing**: Adaptive rebalancing based on market conditions
- **Multi-Objective Optimization**: Pareto-optimal portfolio selection
- **Real-Time Optimization**: Live portfolio optimization capabilities

### Research Areas
- **Behavioral Finance**: Incorporating behavioral biases
- **ESG Integration**: Environmental, social, governance factors
- **Cryptocurrency Strategies**: Digital asset portfolio optimization
- **High-Frequency Strategies**: Ultra-short-term strategy allocation

This comprehensive multi-strategy portfolio testing framework provides the foundation for sophisticated portfolio management and optimization in quantitative trading systems.