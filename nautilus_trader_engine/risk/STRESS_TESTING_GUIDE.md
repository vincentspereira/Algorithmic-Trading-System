# Stress Testing Framework Guide

## Overview

The Stress Testing Framework is a comprehensive, enterprise-grade stress testing system that provides sophisticated stress testing methodologies including Scenario-Based, Historical, and Monte Carlo stress testing. It supports real-time portfolio monitoring, custom scenario creation, and comprehensive reporting for institutional trading systems.

## Key Features

### 🧪 **Multiple Stress Testing Methodologies**
- **Scenario-Based Stress Testing**: Predefined and custom stress scenarios with configurable shocks
- **Historical Stress Testing**: Replay of historical market events (2008 Financial Crisis, COVID-19 Pandemic)
- **Monte Carlo Stress Testing**: Statistical simulation with 10,000+ scenarios and correlation modeling
- **Risk Factor Coverage**: Equity markets, interest rates, credit spreads, currency, volatility, liquidity, and correlation shocks

### 📊 **Comprehensive Stress Scenarios**
- **Financial Crisis 2008**: 40% equity decline, credit spread widening, volatility spike, liquidity crisis
- **COVID-19 Pandemic**: 30% market selloff, extreme volatility, correlation breakdown
- **Interest Rate Shock**: 200bp rate increase with equity and credit impacts
- **Custom Scenarios**: User-defined stress scenarios with multiple risk factors

### 🎯 **Advanced Risk Metrics**
- **Portfolio Impact Analysis**: Absolute and relative loss calculations
- **Asset-Level Impacts**: Individual position stress testing results
- **Sector Impact Analysis**: Sector-wise stress impact aggregation
- **Recovery Time Estimation**: Scenario-based recovery time predictions
- **VaR and Expected Shortfall**: Risk metrics under stress conditions

### 📈 **Stress Test Suite Management**
- **Comprehensive Test Suites**: Multiple scenarios and methodologies in single execution
- **Aggregate Risk Metrics**: Worst-case loss, average loss, systemic risk score
- **Tail Risk Analysis**: Identification of extreme loss scenarios (>10% loss)
- **Diversification Analysis**: Portfolio diversification effectiveness under stress
- **Correlation Breakdown Impact**: Assessment of correlation structure failure

### 🚀 **Real-Time Monitoring Capabilities**
- **Background Monitoring**: Continuous stress testing for active portfolios
- **Alert System**: Automated alerts for portfolios exceeding stress thresholds (15% loss)
- **Performance Metrics**: Test completion rates, execution times, failure tracking
- **Portfolio Tracking**: Active portfolio monitoring with configurable intervals

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                Stress Testing Framework                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Scenario-   │  │ Historical  │  │ Monte Carlo │        │
│  │ Based       │  │ Stress      │  │ Stress      │        │
│  │ Tester      │  │ Tester      │  │ Tester      │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Stress      │  │ Test Suite  │  │ Real-Time   │        │
│  │ Scenarios   │  │ Manager     │  │ Monitor     │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Risk        │  │ Reporting   │  │ Alert       │        │
│  │ Metrics     │  │ Engine      │  │ System      │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### StressShock Class

Defines individual stress shocks that can be applied to portfolios:

```python
@dataclass
class StressShock:
    factor: RiskFactor          # Type of risk factor (EQUITY_MARKET, VOLATILITY, etc.)
    shock_type: str            # "absolute", "relative", "percentile"
    magnitude: float           # Size of the shock
    description: str           # Human-readable description
    affected_assets: Optional[List[str]] = None    # Specific assets to affect
    affected_sectors: Optional[List[str]] = None   # Specific sectors to affect
```

### StressScenarioDefinition Class

Defines complete stress scenarios with multiple shocks:

```python
@dataclass
class StressScenarioDefinition:
    name: str                  # Scenario name
    description: str           # Scenario description
    shocks: List[StressShock]  # List of shocks to apply
    historical_date: Optional[datetime] = None     # Historical reference date
    probability: Optional[float] = None            # Scenario probability
    severity: str = "medium"   # "low", "medium", "high", "extreme"
    is_simultaneous: bool = True                   # Apply shocks simultaneously
```

### StressTestResult Class

Contains results from a single stress test:

```python
@dataclass
class StressTestResult:
    scenario_name: str                    # Name of tested scenario
    stress_type: StressTestType          # Type of stress test
    portfolio_id: str                    # Portfolio identifier
    base_portfolio_value: float          # Original portfolio value
    stressed_portfolio_value: float      # Portfolio value after stress
    absolute_loss: float                 # Absolute loss amount
    relative_loss: float                 # Relative loss percentage
    stressed_var: Optional[float]        # VaR under stress
    stressed_expected_shortfall: Optional[float]  # Expected shortfall
    asset_impacts: Dict[str, float]      # Asset-level impacts
    sector_impacts: Dict[str, float]     # Sector-level impacts
    recovery_time_estimate: Optional[int] # Estimated recovery time in days
```

## Usage Examples

### Basic Stress Testing

```python
import asyncio
from nautilus_trader_engine.risk.stress_testing import (
    StressTestingFramework, StressTestType, RiskFactor,
    create_stress_shock, create_stress_scenario
)

async def basic_stress_test():
    # Initialize framework
    framework = StressTestingFramework(enable_real_time=False)
    await framework.start()
    
    # Create sample portfolio positions
    class MockPosition:
        def __init__(self, symbol, current_price, quantity, sector="Unknown"):
            self.symbol = symbol
            self.current_price = current_price
            self.quantity = quantity
            self.market_value = current_price * quantity
            self.sector = sector
            self.volatility = 0.20
    
    positions = [
        MockPosition("AAPL", 150.0, 100, "Technology"),
        MockPosition("MSFT", 300.0, 50, "Technology"),
        MockPosition("JPM", 140.0, 75, "Financial"),
        MockPosition("JNJ", 160.0, 60, "Healthcare")
    ]
    
    # Run comprehensive stress test suite
    test_suite = await framework.run_stress_test_suite(
        "sample_portfolio",
        positions,
        scenarios=None,  # Use all predefined scenarios
        test_types=[StressTestType.SCENARIO_BASED, StressTestType.HISTORICAL, StressTestType.MONTE_CARLO]
    )
    
    # Display results
    print(f"Worst case loss: {test_suite.worst_case_loss:.2%}")
    print(f"Worst case scenario: {test_suite.worst_case_scenario}")
    print(f"Average loss: {test_suite.average_loss:.2%}")
    print(f"Systemic risk score: {test_suite.systemic_risk_score:.3f}")
    
    await framework.stop()

# Run the example
asyncio.run(basic_stress_test())
```

### Custom Scenario Creation

```python
async def custom_scenario_example():
    framework = StressTestingFramework()
    await framework.start()
    
    # Create custom stress shocks
    custom_shocks = [
        create_stress_shock(
            RiskFactor.EQUITY_MARKET, 
            "relative", 
            -0.25, 
            "25% equity market decline"
        ),
        create_stress_shock(
            RiskFactor.VOLATILITY, 
            "relative", 
            2.0, 
            "Volatility doubling"
        ),
        create_stress_shock(
            RiskFactor.LIQUIDITY, 
            "relative", 
            0.20, 
            "20% liquidity impact"
        )
    ]
    
    # Create custom scenario
    custom_scenario = create_stress_scenario(
        "Custom Market Crash",
        "Severe market stress with liquidity crisis",
        custom_shocks,
        "high"
    )
    
    # Run stress test with custom scenario
    test_suite = await framework.run_stress_test_suite(
        "custom_test_portfolio",
        positions,
        scenarios=[custom_scenario],
        test_types=[StressTestType.SCENARIO_BASED]
    )
    
    print(f"Custom scenario loss: {test_suite.scenario_results[0].relative_loss:.2%}")
    
    await framework.stop()
```

### Real-Time Monitoring

```python
async def real_time_monitoring_example():
    # Enable real-time monitoring
    framework = StressTestingFramework(enable_real_time=True)
    await framework.start()
    
    # Add portfolios for monitoring
    await framework.run_stress_test_suite("portfolio_1", positions_1)
    await framework.run_stress_test_suite("portfolio_2", positions_2)
    
    # Framework will now continuously monitor portfolios
    # and generate alerts if stress losses exceed 15%
    
    try:
        # Keep running for monitoring
        while True:
            await asyncio.sleep(60)
            
            # Check metrics
            metrics = framework.get_metrics()
            print(f"Tests completed: {metrics['tests_completed']}")
            print(f"Active portfolios: {metrics['active_portfolios']}")
            
    except KeyboardInterrupt:
        await framework.stop()
```

### Comprehensive Reporting

```python
async def reporting_example():
    framework = StressTestingFramework()
    await framework.start()
    
    # Run stress tests
    test_suite = await framework.run_stress_test_suite("reporting_portfolio", positions)
    
    # Generate comprehensive report
    report = framework.generate_stress_test_report("reporting_portfolio")
    
    print("=== STRESS TEST REPORT ===")
    print(f"Portfolio ID: {report['portfolio_id']}")
    print(f"Test Date: {report['test_date']}")
    print(f"Base Portfolio Value: ${report['base_portfolio_value']:,.2f}")
    
    print("\\n=== SUMMARY ===")
    summary = report['summary']
    print(f"Worst Case Loss: {summary['worst_case_loss']:.2%}")
    print(f"Worst Case Scenario: {summary['worst_case_scenario']}")
    print(f"Average Loss: {summary['average_loss']:.2%}")
    print(f"Systemic Risk Score: {summary['systemic_risk_score']:.3f}")
    print(f"Diversification Ratio: {summary['diversification_ratio']:.3f}")
    print(f"Tail Risk Scenarios: {len(summary['tail_risk_scenarios'])}")
    
    print("\\n=== SCENARIO RESULTS ===")
    for result in report['scenario_results']:
        print(f"{result['scenario_name']} ({result['stress_type']}):")
        print(f"  Loss: {result['relative_loss']:.2%}")
        print(f"  Recovery Time: {result['recovery_time_estimate']} days")
        if result['stressed_var']:
            print(f"  Stressed VaR: {result['stressed_var']:.2%}")
    
    await framework.stop()
```

## Predefined Stress Scenarios

### Financial Crisis 2008
- **Equity Market**: -40% decline
- **Credit Spreads**: +600bp widening
- **Volatility**: +250% increase
- **Liquidity**: 30% impact
- **Severity**: Extreme
- **Historical Date**: September 15, 2008

### COVID-19 Pandemic
- **Equity Market**: -30% decline
- **Volatility**: +300% increase
- **Correlation**: 50% breakdown
- **Severity**: High
- **Historical Date**: February 19, 2020

### Interest Rate Shock
- **Interest Rates**: +200bp increase
- **Equity Market**: -15% decline
- **Credit Spreads**: +100bp widening
- **Severity**: Medium

## Risk Factors

The framework supports comprehensive risk factor coverage:

### RiskFactor Enum
- **EQUITY_MARKET**: Stock market movements
- **INTEREST_RATES**: Interest rate changes
- **CREDIT_SPREADS**: Credit spread movements
- **CURRENCY**: Foreign exchange rate changes
- **COMMODITY**: Commodity price movements
- **VOLATILITY**: Volatility changes
- **LIQUIDITY**: Liquidity availability changes
- **CORRELATION**: Correlation structure changes

## Stress Test Types

### StressTestType Enum
- **SCENARIO_BASED**: Predefined or custom scenario testing
- **HISTORICAL**: Historical event replay testing
- **MONTE_CARLO**: Statistical simulation testing

## Performance Characteristics

### Execution Performance
- **Scenario-Based**: Sub-millisecond execution for typical portfolios
- **Historical**: ~1-2ms execution including data lookup
- **Monte Carlo**: ~10-50ms for 10,000 simulations depending on portfolio size

### Memory Usage
- **Per Portfolio**: ~10KB base memory + position data
- **Position Data**: ~1KB per position
- **Results Storage**: ~5KB per stress test result
- **Framework Overhead**: ~50KB base framework

### Scalability
- **Portfolio Size**: Efficiently handles 100+ positions
- **Concurrent Tests**: Supports multiple portfolios simultaneously
- **Real-Time Monitoring**: Configurable intervals (default 5 minutes)
- **Historical Data**: Efficient lookup and caching

## Integration Points

### Risk Management Systems
```python
# Integration with VaR engine
from nautilus_trader_engine.risk import get_var_engine

async def integrated_risk_analysis():
    var_engine = get_var_engine()
    stress_framework = get_stress_testing_framework()
    
    # Run VaR calculation
    var_result = await var_engine.calculate_var(
        "portfolio_1", positions, VaRMethod.HISTORICAL, 0.95
    )
    
    # Run stress tests
    stress_suite = await stress_framework.run_stress_test_suite(
        "portfolio_1", positions
    )
    
    # Compare normal VaR vs stressed VaR
    print(f"Normal VaR: {var_result.var_percentage:.2%}")
    print(f"Stressed VaR: {stress_suite.scenario_results[0].stressed_var:.2%}")
```

### Portfolio Management Systems
```python
# Integration with portfolio optimizer
from nautilus_trader_engine.risk import get_portfolio_optimizer

async def stress_aware_optimization():
    optimizer = get_portfolio_optimizer()
    stress_framework = get_stress_testing_framework()
    
    # Optimize portfolio
    optimized_result = await optimizer.optimize_portfolio(
        "optimized_portfolio", assets, OptimizationMethod.MEAN_VARIANCE
    )
    
    # Stress test optimized portfolio
    optimized_positions = create_positions_from_weights(
        optimized_result.weights, assets
    )
    
    stress_suite = await stress_framework.run_stress_test_suite(
        "optimized_portfolio", optimized_positions
    )
    
    print(f"Optimized portfolio stress loss: {stress_suite.worst_case_loss:.2%}")
```

### Alert Systems
```python
# Custom alert handling
async def setup_stress_alerts():
    framework = StressTestingFramework(enable_real_time=True)
    
    # Custom alert callback
    async def stress_alert_handler(alert_data):
        portfolio_id = alert_data['portfolio_id']
        scenario = alert_data['scenario_name']
        loss = alert_data['percentage_loss']
        
        print(f"🚨 STRESS ALERT: {portfolio_id}")
        print(f"   Scenario: {scenario}")
        print(f"   Loss: {loss:.2%}")
        
        # Send to external alert system
        await send_to_slack(f"Stress test alert for {portfolio_id}: {loss:.2%} loss")
        await send_email_alert(portfolio_id, scenario, loss)
    
    # Add alert callback
    framework.add_alert_callback(stress_alert_handler)
    
    await framework.start()
```

## Best Practices

### Scenario Design
1. **Realistic Scenarios**: Base scenarios on historical events or plausible market conditions
2. **Multiple Risk Factors**: Include correlated risk factors for comprehensive testing
3. **Severity Levels**: Use appropriate severity classifications for recovery time estimation
4. **Regular Updates**: Update scenarios based on changing market conditions

### Portfolio Testing
1. **Comprehensive Coverage**: Test all major portfolios regularly
2. **Diversification Analysis**: Monitor diversification effectiveness under stress
3. **Threshold Management**: Set appropriate alert thresholds based on risk tolerance
4. **Historical Validation**: Validate stress test results against historical performance

### Performance Optimization
1. **Batch Testing**: Group multiple portfolios for efficient testing
2. **Monitoring Intervals**: Balance monitoring frequency with system performance
3. **Result Storage**: Implement appropriate result retention policies
4. **Resource Management**: Monitor memory usage for large portfolios

### Risk Management Integration
1. **VaR Comparison**: Compare stress test results with normal VaR calculations
2. **Limit Monitoring**: Integrate with position and risk limit systems
3. **Reporting Integration**: Include stress test results in risk reports
4. **Decision Support**: Use stress test results for portfolio management decisions

## Error Handling and Diagnostics

### Common Issues and Solutions

```python
try:
    result = await framework.run_stress_test_suite(portfolio_id, positions)
except Exception as e:
    if "Invalid position data" in str(e):
        print("❌ Check position data format and required fields")
    elif "Scenario not found" in str(e):
        print("❌ Verify scenario name or create custom scenario")
    elif "Insufficient data" in str(e):
        print("❌ Ensure positions have required market data")
    else:
        print(f"❌ Unexpected error: {e}")
```

### Diagnostic Information

```python
# Check framework metrics
metrics = framework.get_metrics()
print(f"Tests completed: {metrics['tests_completed']}")
print(f"Tests failed: {metrics['tests_failed']}")
print(f"Average test time: {metrics['avg_test_time_ms']:.2f}ms")
print(f"Active portfolios: {metrics['active_portfolios']}")

# Validate stress test results
for result in test_suite.scenario_results:
    if result.diagnostics:
        print(f"Scenario: {result.scenario_name}")
        print(f"  Shocks applied: {result.diagnostics.get('shocks_applied', 0)}")
        print(f"  Simultaneous: {result.diagnostics.get('simultaneous_shocks', True)}")
```

## Conclusion

The Stress Testing Framework provides a comprehensive, enterprise-grade solution for portfolio stress testing in trading systems. With multiple testing methodologies, predefined scenarios, real-time monitoring, and extensive customization capabilities, it supports both simple and sophisticated stress testing requirements.

The framework's modular design allows for easy integration with existing trading infrastructure while providing the flexibility to scale from small investment operations to large institutional asset management. The combination of performance, accuracy, and comprehensive reporting makes it suitable for production use in demanding investment environments.

For additional examples and advanced usage patterns, refer to the test files and inline documentation within the framework code.