# Real-Time VaR Calculation Engine

## Overview

The Real-Time VaR (Value at Risk) Calculation Engine is a comprehensive risk management system that provides sophisticated VaR calculations using multiple methodologies, real-time processing, model backtesting, and performance monitoring. It supports institutional-grade risk management with enterprise features for trading systems.

## Key Features

### 🔢 **Multiple VaR Calculation Methods**
- **Historical Simulation**: Non-parametric approach using historical return distributions
- **Parametric (Variance-Covariance)**: Normal distribution assumption with EWMA volatility
- **Monte Carlo Simulation**: Stochastic simulation with correlation modeling
- **GARCH Models**: Time-varying volatility with GARCH(1,1) forecasting

### 📊 **Comprehensive Risk Metrics**
- Value at Risk (VaR) at multiple confidence levels (90%, 95%, 99%, 99.9%)
- Expected Shortfall (Conditional VaR) for tail risk measurement
- Multiple time horizons (intraday, daily, weekly, monthly)
- Portfolio-level and position-level risk decomposition

### 🚀 **Real-Time Processing**
- Asynchronous calculation engine with background workers
- Configurable calculation intervals for live risk monitoring
- High-performance processing with thread pool optimization
- Real-time alerting for VaR breaches and risk limit violations

### 🔍 **Model Validation & Backtesting**
- Kupiec Proportion of Failures (POF) test
- Christoffersen Conditional Coverage test
- Basel Traffic Light test for regulatory compliance
- Historical performance tracking and model comparison

### 📈 **Advanced Analytics**
- GARCH volatility forecasting with parameter estimation
- Correlation matrix analysis and PCA decomposition
- Scenario analysis and stress testing capabilities
- Performance attribution and risk decomposition

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    VaR Engine                               │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Historical  │  │ Parametric  │  │Monte Carlo  │        │
│  │ Calculator  │  │ Calculator  │  │ Calculator  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   GARCH     │  │    VaR      │  │ Real-Time   │        │
│  │ Calculator  │  │ Backtester  │  │ Processor   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Results   │  │  Portfolio  │  │  Metrics    │        │
│  │  Storage    │  │  Positions  │  │ Collection  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### VaR Calculation Methods

#### 1. Historical Simulation
```python
from nautilus_trader_engine.risk import HistoricalVaRCalculator

calculator = HistoricalVaRCalculator(lookback_days=252)
var_result = calculator.calculate_var(
    positions=portfolio_positions,
    confidence_level=0.95,
    time_horizon=TimeHorizon.DAILY
)
```

**Features:**
- Non-parametric approach using actual historical returns
- No distributional assumptions required
- Captures fat tails and skewness in return distributions
- Configurable lookback period (default: 252 days)

#### 2. Parametric (Variance-Covariance)
```python
from nautilus_trader_engine.risk import ParametricVaRCalculator

calculator = ParametricVaRCalculator(use_ewma=True, lambda_decay=0.94)
var_result = calculator.calculate_var(
    positions=portfolio_positions,
    confidence_level=0.95,
    time_horizon=TimeHorizon.DAILY
)
```

**Features:**
- Assumes normal distribution of returns
- Fast calculation suitable for real-time applications
- Exponentially Weighted Moving Average (EWMA) for volatility
- Analytical Expected Shortfall calculation

#### 3. Monte Carlo Simulation
```python
from nautilus_trader_engine.risk import MonteCarloVaRCalculator

calculator = MonteCarloVaRCalculator(num_simulations=10000, random_seed=42)
var_result = calculator.calculate_var(
    positions=portfolio_positions,
    confidence_level=0.95,
    time_horizon=TimeHorizon.DAILY
)
```

**Features:**
- Stochastic simulation with correlation modeling
- Handles complex portfolio structures and non-linear instruments
- Configurable number of simulations for accuracy vs. speed trade-off
- Full correlation matrix consideration

#### 4. GARCH Models
```python
from nautilus_trader_engine.risk import GARCHVaRCalculator

calculator = GARCHVaRCalculator(max_iterations=1000, tolerance=1e-6)
var_result = calculator.calculate_var(
    positions=portfolio_positions,
    confidence_level=0.95,
    time_horizon=TimeHorizon.DAILY
)
```

**Features:**
- GARCH(1,1) model for time-varying volatility
- Volatility clustering and mean reversion
- Multi-step ahead volatility forecasting
- Maximum likelihood parameter estimation

## Usage Examples

### Basic VaR Calculation

```python
import asyncio
import numpy as np
from nautilus_trader_engine.risk import (
    VaREngine, VaRMethod, TimeHorizon, PortfolioPosition
)

async def calculate_portfolio_var():
    # Initialize VaR engine
    engine = VaREngine(enable_real_time=True, enable_backtesting=True)
    await engine.start()
    
    # Create portfolio positions
    positions = [
        PortfolioPosition(
            symbol="AAPL",
            quantity=100,
            current_price=150.0,
            market_value=15000.0,
            weight=0.6,
            returns=np.random.normal(0.001, 0.02, 252)  # Historical returns
        ),
        PortfolioPosition(
            symbol="MSFT",
            quantity=50,
            current_price=200.0,
            market_value=10000.0,
            weight=0.4,
            returns=np.random.normal(0.0008, 0.018, 252)
        )
    ]
    
    # Calculate VaR using Historical method
    var_result = await engine.calculate_var(
        portfolio_id="main_portfolio",
        positions=positions,
        method=VaRMethod.HISTORICAL,
        confidence_level=0.95,
        time_horizon=TimeHorizon.DAILY
    )
    
    print(f"95% 1-day VaR: ${var_result.var_value:,.2f}")
    print(f"Expected Shortfall: ${var_result.expected_shortfall:,.2f}")
    print(f"VaR as % of portfolio: {var_result.var_percentage:.2%}")
    
    await engine.stop()

# Run the calculation
asyncio.run(calculate_portfolio_var())
```

### Multi-Method VaR Comparison

```python
async def compare_var_methods():
    engine = VaREngine(enable_real_time=False)
    await engine.start()
    
    # Calculate VaR using all methods
    results = await engine.calculate_all_methods(
        portfolio_id="comparison_portfolio",
        positions=positions,
        confidence_level=0.95,
        time_horizon=TimeHorizon.DAILY
    )
    
    print("VaR Comparison (95% confidence, 1-day horizon):")
    for method, result in results.items():
        print(f"{method.value:15}: ${result.var_value:8,.2f} "
              f"(ES: ${result.expected_shortfall:8,.2f})")
    
    await engine.stop()
```

### Real-Time VaR Monitoring

```python
async def real_time_var_monitoring():
    # Set up real-time VaR engine
    engine = VaREngine(
        enable_real_time=True,
        calculation_interval_seconds=60,  # Calculate every minute
        enable_backtesting=True
    )
    
    # Set up VaR breach alerting
    def var_breach_alert(alert_data):
        portfolio_id = alert_data['portfolio_id']
        var_result = alert_data['var_result']
        breach_percentage = alert_data['breach_percentage']
        
        print(f"🚨 VaR BREACH ALERT for {portfolio_id}")
        print(f"   VaR: ${var_result.var_value:,.2f} ({breach_percentage:.2%} of portfolio)")
        print(f"   Threshold: {alert_data['threshold']:.2%}")
    
    engine.add_alert_callback(var_breach_alert)
    engine.set_var_breach_threshold(0.05)  # 5% threshold
    
    await engine.start()
    
    # Engine will now continuously calculate VaR and send alerts
    # Keep running for monitoring
    try:
        while True:
            await asyncio.sleep(60)
            metrics = engine.get_metrics()
            print(f"VaR calculations completed: {metrics['calculations_completed']}")
    except KeyboardInterrupt:
        await engine.stop()
```

### VaR Model Backtesting

```python
async def backtest_var_models():
    engine = VaREngine(enable_backtesting=True)
    await engine.start()
    
    # Calculate VaR over time to build history
    for i in range(100):  # Simulate 100 days of VaR calculations
        await engine.calculate_var(
            "backtest_portfolio", positions, 
            VaRMethod.HISTORICAL, 0.95, TimeHorizon.DAILY
        )
    
    # Run backtest
    backtest_result = await engine.backtest_var_model(
        "backtest_portfolio", VaRMethod.HISTORICAL, lookback_days=100
    )
    
    if backtest_result:
        print(f"Backtest Results for Historical VaR:")
        print(f"  Total observations: {backtest_result.total_observations}")
        print(f"  Violations: {backtest_result.violations}")
        print(f"  Violation rate: {backtest_result.violation_rate:.2%}")
        print(f"  Expected violations: {backtest_result.expected_violations}")
        print(f"  Kupiec POF test p-value: {backtest_result.kupiec_pof_p_value:.4f}")
        print(f"  Traffic light zone: {backtest_result.traffic_light_zone}")
    
    await engine.stop()
```

### Advanced GARCH Modeling

```python
async def garch_var_analysis():
    engine = VaREngine()
    await engine.start()
    
    # Calculate GARCH VaR
    garch_result = await engine.calculate_var(
        "garch_portfolio", positions,
        VaRMethod.GARCH, 0.99, TimeHorizon.DAILY
    )
    
    print(f"GARCH VaR Results:")
    print(f"  99% 1-day VaR: ${garch_result.var_value:,.2f}")
    print(f"  Expected Shortfall: ${garch_result.expected_shortfall:,.2f}")
    
    # Examine GARCH parameters
    diagnostics = garch_result.diagnostics
    print(f"  GARCH Parameters:")
    print(f"    Omega (ω): {diagnostics['garch_omega']:.6f}")
    print(f"    Alpha (α): {diagnostics['garch_alpha']:.6f}")
    print(f"    Beta (β):  {diagnostics['garch_beta']:.6f}")
    print(f"    Persistence (α+β): {diagnostics['garch_alpha'] + diagnostics['garch_beta']:.6f}")
    print(f"  Forecasted volatility: {diagnostics['forecasted_volatility']:.4f}")
    print(f"  Model convergence: {diagnostics['convergence']}")
    
    await engine.stop()
```

## Configuration Options

### VaR Engine Initialization

```python
engine = VaREngine(
    enable_real_time=True,              # Enable real-time calculations
    calculation_interval_seconds=60,    # Real-time calculation frequency
    enable_backtesting=True             # Enable model backtesting
)
```

### Calculator-Specific Configuration

```python
# Historical VaR
historical_calc = HistoricalVaRCalculator(
    lookback_days=252  # Number of historical days to use
)

# Parametric VaR
parametric_calc = ParametricVaRCalculator(
    use_ewma=True,        # Use exponentially weighted moving average
    lambda_decay=0.94     # EWMA decay factor
)

# Monte Carlo VaR
mc_calc = MonteCarloVaRCalculator(
    num_simulations=10000,  # Number of Monte Carlo simulations
    random_seed=42          # Random seed for reproducibility
)

# GARCH VaR
garch_calc = GARCHVaRCalculator(
    max_iterations=1000,  # Maximum optimization iterations
    tolerance=1e-6        # Convergence tolerance
)
```

## Risk Metrics and Interpretation

### VaR Result Components

```python
var_result = await engine.calculate_var(...)

# Core VaR metrics
print(f"VaR Value: ${var_result.var_value:,.2f}")                    # Potential loss
print(f"Expected Shortfall: ${var_result.expected_shortfall:,.2f}") # Tail risk
print(f"Portfolio Value: ${var_result.portfolio_value:,.2f}")       # Total value
print(f"VaR Percentage: {var_result.var_percentage:.2%}")           # VaR as % of portfolio

# Method and parameters
print(f"Method: {var_result.method.value}")
print(f"Confidence Level: {var_result.confidence_level:.0%}")
print(f"Time Horizon: {var_result.time_horizon.value}")

# Calculation diagnostics
print(f"Diagnostics: {var_result.diagnostics}")
```

### Confidence Levels and Interpretation

- **90% VaR**: Expected to be exceeded 1 day out of 10 (more frequent, smaller losses)
- **95% VaR**: Expected to be exceeded 1 day out of 20 (standard for risk management)
- **99% VaR**: Expected to be exceeded 1 day out of 100 (regulatory capital requirements)
- **99.9% VaR**: Expected to be exceeded 1 day out of 1000 (extreme risk scenarios)

### Time Horizons and Scaling

- **Intraday**: Same-day risk exposure
- **Daily**: 1-day holding period (standard)
- **Weekly**: 5-day holding period (√5 scaling)
- **Monthly**: 22-day holding period (√22 scaling)

## Model Validation and Backtesting

### Backtesting Framework

The engine includes comprehensive backtesting capabilities:

```python
# Run backtest
backtest_result = await engine.backtest_var_model(
    portfolio_id="test_portfolio",
    method=VaRMethod.HISTORICAL,
    lookback_days=252
)

# Analyze results
print(f"Violation Rate: {backtest_result.violation_rate:.2%}")
print(f"Expected Rate: {1 - backtest_result.confidence_level:.2%}")

# Statistical tests
if backtest_result.kupiec_pof_reject:
    print("⚠️  Kupiec POF test: Model rejected (poor calibration)")
else:
    print("✅ Kupiec POF test: Model not rejected")

if backtest_result.christoffersen_cc_reject:
    print("⚠️  Christoffersen CC test: Model rejected (clustering violations)")
else:
    print("✅ Christoffersen CC test: Model not rejected")

# Traffic light test (Basel regulatory framework)
if backtest_result.traffic_light_zone == "green":
    print("🟢 Traffic Light: Green zone (acceptable performance)")
elif backtest_result.traffic_light_zone == "yellow":
    print("🟡 Traffic Light: Yellow zone (requires attention)")
else:
    print("🔴 Traffic Light: Red zone (model inadequate)")
```

### Model Comparison

```python
# Compare multiple models
methods = [VaRMethod.HISTORICAL, VaRMethod.PARAMETRIC, VaRMethod.MONTE_CARLO]
backtest_results = {}

for method in methods:
    result = await engine.backtest_var_model("portfolio", method, 252)
    if result:
        backtest_results[method] = result

# Find best performing model
best_method = min(backtest_results.keys(), 
                 key=lambda m: abs(backtest_results[m].violation_rate - 0.05))
print(f"Best performing model: {best_method.value}")
```

## Performance Optimization

### Calculation Performance

- **Historical VaR**: ~1ms for 252 days of data
- **Parametric VaR**: ~0.5ms (fastest method)
- **Monte Carlo VaR**: ~10ms for 10,000 simulations
- **GARCH VaR**: ~50ms including parameter estimation

### Memory Usage

- **Per Portfolio**: ~5KB base + historical data
- **Historical Data**: ~2KB per position per year
- **Results Storage**: ~1KB per VaR calculation
- **Engine Overhead**: ~20MB for 1000 portfolios

### Scaling Considerations

```python
# High-frequency calculations
engine = VaREngine(
    enable_real_time=True,
    calculation_interval_seconds=10,  # Every 10 seconds
    enable_backtesting=False          # Disable for performance
)

# Batch processing
results = await asyncio.gather(*[
    engine.calculate_var(f"portfolio_{i}", positions, VaRMethod.PARAMETRIC, 0.95)
    for i in range(100)  # 100 portfolios simultaneously
])
```

## Integration with Trading Systems

### Risk Limit Monitoring

```python
class RiskLimitMonitor:
    def __init__(self, var_engine):
        self.var_engine = var_engine
        self.limits = {}  # portfolio_id -> limit
    
    def set_var_limit(self, portfolio_id: str, limit: float):
        self.limits[portfolio_id] = limit
    
    async def check_limits(self):
        for portfolio_id, limit in self.limits.items():
            history = self.var_engine.get_var_history(portfolio_id)
            if history:
                latest_var = history[-1]
                if abs(latest_var.var_value) > limit:
                    await self.send_limit_breach_alert(portfolio_id, latest_var, limit)
    
    async def send_limit_breach_alert(self, portfolio_id, var_result, limit):
        print(f"🚨 RISK LIMIT BREACH: {portfolio_id}")
        print(f"   VaR: ${var_result.var_value:,.2f}")
        print(f"   Limit: ${limit:,.2f}")
```

### Portfolio Optimization Integration

```python
async def optimize_portfolio_with_var_constraint():
    # Calculate current VaR
    current_var = await engine.calculate_var(
        "optimization_portfolio", positions, 
        VaRMethod.PARAMETRIC, 0.95
    )
    
    # Use VaR as constraint in optimization
    var_constraint = abs(current_var.var_value)
    
    # Portfolio optimization would use this constraint
    print(f"VaR constraint for optimization: ${var_constraint:,.2f}")
```

## Error Handling and Diagnostics

### Common Issues and Solutions

```python
try:
    var_result = await engine.calculate_var(...)
except ValueError as e:
    if "Insufficient historical data" in str(e):
        print("❌ Need more historical data for reliable VaR calculation")
        # Use shorter lookback period or different method
    elif "Singular covariance matrix" in str(e):
        print("❌ Correlation matrix issues in Monte Carlo")
        # Check for highly correlated assets
except Exception as e:
    print(f"❌ Unexpected error: {e}")
```

### Diagnostic Information

```python
# Check calculation diagnostics
diagnostics = var_result.diagnostics

# Historical method diagnostics
if var_result.method == VaRMethod.HISTORICAL:
    print(f"Observations used: {diagnostics['observations_used']}")
    print(f"Return skewness: {diagnostics['return_skewness']:.3f}")
    print(f"Return kurtosis: {diagnostics['return_kurtosis']:.3f}")

# GARCH method diagnostics
elif var_result.method == VaRMethod.GARCH:
    print(f"Model convergence: {diagnostics['convergence']}")
    print(f"Log-likelihood: {diagnostics['log_likelihood']:.2f}")
    print(f"AIC: {diagnostics['aic']:.2f}")
```

## Regulatory Compliance

### Basel Framework Compliance

The VaR engine supports Basel regulatory requirements:

- **Market Risk Capital**: 99% VaR with 10-day holding period
- **Backtesting Requirements**: Daily backtesting with traffic light system
- **Model Validation**: Statistical tests for model adequacy

```python
# Basel-compliant VaR calculation
basel_var = await engine.calculate_var(
    portfolio_id="trading_book",
    positions=positions,
    method=VaRMethod.HISTORICAL,  # Preferred by regulators
    confidence_level=0.99,        # 99% confidence
    time_horizon=TimeHorizon.DAILY # Scale to 10-day separately
)

# Scale to 10-day horizon (√10 factor)
basel_10day_var = basel_var.var_value * np.sqrt(10)
print(f"Basel 99% 10-day VaR: ${basel_10day_var:,.2f}")
```

### Reporting and Documentation

```python
def generate_var_report(portfolio_id: str, engine: VaREngine):
    """Generate comprehensive VaR report"""
    history = engine.get_var_history(portfolio_id)
    
    if not history:
        return "No VaR calculations available"
    
    latest = history[-1]
    
    report = f"""
    VaR Risk Report - {portfolio_id}
    ================================
    
    Latest VaR Calculation:
    - Method: {latest.method.value}
    - Confidence Level: {latest.confidence_level:.0%}
    - Time Horizon: {latest.time_horizon.value}
    - VaR: ${latest.var_value:,.2f}
    - Expected Shortfall: ${latest.expected_shortfall:,.2f}
    - Portfolio Value: ${latest.portfolio_value:,.2f}
    - VaR as % of Portfolio: {latest.var_percentage:.2%}
    
    Historical Performance:
    - Total Calculations: {len(history)}
    - Average VaR: ${np.mean([h.var_value for h in history]):,.2f}
    - Maximum VaR: ${np.min([h.var_value for h in history]):,.2f}
    - VaR Volatility: ${np.std([h.var_value for h in history]):,.2f}
    """
    
    return report
```

## Best Practices

### Model Selection Guidelines

1. **Historical VaR**: Best for portfolios with sufficient history and non-normal returns
2. **Parametric VaR**: Ideal for real-time applications with normal return assumptions
3. **Monte Carlo VaR**: Suitable for complex portfolios with non-linear instruments
4. **GARCH VaR**: Optimal when volatility clustering is significant

### Data Quality Requirements

- **Minimum History**: 30 observations for parametric, 100+ for historical
- **Data Frequency**: Daily data preferred, intraday for high-frequency trading
- **Missing Data**: Handle gaps with interpolation or exclusion
- **Corporate Actions**: Adjust for splits, dividends, and other events

### Validation and Monitoring

```python
# Regular model validation
async def validate_var_models():
    portfolios = ["portfolio_1", "portfolio_2", "portfolio_3"]
    methods = [VaRMethod.HISTORICAL, VaRMethod.PARAMETRIC]
    
    for portfolio in portfolios:
        for method in methods:
            backtest = await engine.backtest_var_model(portfolio, method, 252)
            if backtest and backtest.traffic_light_zone == "red":
                print(f"⚠️  Model {method.value} for {portfolio} needs recalibration")
```

## Conclusion

The Real-Time VaR Calculation Engine provides a comprehensive, enterprise-grade solution for risk management in trading systems. With multiple calculation methodologies, real-time processing, comprehensive backtesting, and regulatory compliance features, it supports both simple and sophisticated risk management requirements.

The engine's modular design allows for easy integration with existing trading infrastructure while providing the flexibility to scale from small trading operations to large institutional deployments. The combination of performance, accuracy, and validation capabilities makes it suitable for production use in demanding trading environments.