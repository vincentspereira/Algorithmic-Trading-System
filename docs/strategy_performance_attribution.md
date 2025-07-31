# Strategy Performance Attribution Documentation

## Overview

The Strategy Performance Attribution framework provides comprehensive analysis of trading strategy performance including factor-based attribution analysis, risk-adjusted performance metrics, benchmark comparison and tracking error analysis, and performance decomposition tools. This system helps understand the sources of strategy returns and risk.

## Key Features

- **Factor-Based Attribution**: Decompose returns into factor contributions using multi-factor models
- **Risk-Adjusted Performance Metrics**: Comprehensive performance metrics including Sharpe, Sortino, and Calmar ratios
- **Benchmark Comparison**: Detailed comparison against benchmarks with tracking error analysis
- **Performance Decomposition**: Break down performance into selection, allocation, and interaction effects
- **Risk Decomposition**: Separate systematic and specific risk components
- **Multiple Attribution Methods**: Support for Brinson, factor model, and returns-based attribution

## Architecture

### Core Components

1. **StrategyPerformanceAttributor**: Main orchestration class for performance attribution
2. **PerformanceCalculator**: Calculates comprehensive performance metrics
3. **BenchmarkAnalyzer**: Analyzes performance relative to benchmarks
4. **AttributionAnalyzer**: Performs attribution analysis using various methods
5. **FactorModelBuilder**: Builds factor models for attribution analysis

### Attribution Methods

- **FACTOR_MODEL**: Multi-factor model attribution using regression analysis
- **BRINSON**: Brinson attribution analysis for allocation and selection effects
- **RETURNS_BASED**: Simple returns-based attribution analysis
- **HOLDINGS_BASED**: Holdings-based attribution (future enhancement)
- **RISK_MODEL**: Risk model-based attribution (future enhancement)

## Usage Examples

### Basic Setup

```python
from nautilus_trader_engine.backtesting.strategy_performance_attribution import (
    StrategyPerformanceAttributor,
    Factor,
    AttributionMethod
)
import pandas as pd
import numpy as np
import asyncio

# Create sample strategy and benchmark returns
dates = pd.date_range(start='2022-01-01', end='2023-12-31', freq='D')
strategy_returns = pd.Series(np.random.normal(0.001, 0.02, len(dates)), index=dates)
benchmark_returns = pd.Series(np.random.normal(0.0008, 0.015, len(dates)), index=dates)

# Initialize attributor
attributor = StrategyPerformanceAttributor()
```

### Defining Factors

```python
# Create market factor
market_factor = Factor(
    name="Market",
    description="Broad market exposure factor",
    factor_type="market",
    data=benchmark_returns,  # Use benchmark as market factor
    benchmark_exposure=1.0
)

# Create style factors
value_factor = Factor(
    name="Value",
    description="Value vs Growth factor",
    factor_type="style",
    data=pd.Series(np.random.normal(0.0003, 0.012, len(dates)), index=dates),
    benchmark_exposure=0.0
)

momentum_factor = Factor(
    name="Momentum",
    description="Price momentum factor",
    factor_type="style",
    data=pd.Series(np.random.normal(0.0001, 0.010, len(dates)), index=dates),
    benchmark_exposure=0.0
)

size_factor = Factor(
    name="Size",
    description="Size factor (small vs large cap)",
    factor_type="style",
    data=pd.Series(np.random.normal(-0.0001, 0.008, len(dates)), index=dates),
    benchmark_exposure=0.0
)

# Combine factors
factors = [market_factor, value_factor, momentum_factor, size_factor]
```

### Running Attribution Analysis

```python
async def run_attribution_analysis():
    # Perform comprehensive attribution analysis
    attribution = await attributor.analyze_strategy_performance(
        strategy_name="My Trading Strategy",
        strategy_returns=strategy_returns,
        benchmark_returns=benchmark_returns,
        factors=factors,
        benchmark_names=["Market Index"],
        attribution_method=AttributionMethod.FACTOR_MODEL
    )
    
    return attribution

# Execute analysis
attribution = asyncio.run(run_attribution_analysis())
```

### Analyzing Results

```python
# Performance metrics
metrics = attribution.performance_metrics
print(f"Total Return: {metrics.total_return:.2%}")
print(f"Annualized Return: {metrics.annualized_return:.2%}")
print(f"Volatility: {metrics.volatility:.2%}")
print(f"Sharpe Ratio: {metrics.sharpe_ratio:.3f}")
print(f"Max Drawdown: {metrics.max_drawdown:.2%}")
print(f"Alpha: {metrics.alpha:.4f}")
print(f"Beta: {metrics.beta:.3f}")
print(f"Information Ratio: {metrics.information_ratio:.3f}")

# Benchmark comparison
if attribution.benchmark_comparisons:
    benchmark = attribution.benchmark_comparisons[0]
    print(f"\\nBenchmark Analysis:")
    print(f"Correlation: {benchmark.correlation:.3f}")
    print(f"Tracking Error: {benchmark.tracking_error:.2%}")
    print(f"Up Capture: {benchmark.up_capture_ratio:.3f}")
    print(f"Down Capture: {benchmark.down_capture_ratio:.3f}")
    print(f"Outperformance Ratio: {benchmark.outperformance_ratio:.2%}")

# Factor exposures
print(f"\\nFactor Exposures:")
for factor_name, exposure in attribution.factor_exposures.items():
    print(f"{factor_name}: {exposure:.3f}")

# Risk decomposition
print(f"\\nRisk Decomposition:")
risk_decomp = attribution.risk_decomposition
print(f"Total Risk: {risk_decomp['total_risk']:.2%}")
print(f"Systematic Risk: {risk_decomp['systematic_risk']:.2%}")
print(f"Specific Risk: {risk_decomp['specific_risk']:.2%}")
print(f"Systematic %: {risk_decomp.get('systematic_risk_pct', 0):.1%}")
print(f"Specific %: {risk_decomp.get('specific_risk_pct', 0):.1%}")

# Attribution results
if attribution.attribution_results:
    attr_result = attribution.attribution_results[0]
    print(f"\\nAttribution Analysis:")
    print(f"Excess Return: {attr_result.excess_return:.2%}")
    print(f"Selection Effect: {attr_result.selection_effect:.4f}")
    print(f"Allocation Effect: {attr_result.allocation_effect:.4f}")
    
    print(f"\\nFactor Contributions:")
    for factor_name, contribution in attr_result.factor_contributions.items():
        print(f"  {factor_name}: {contribution:.4f}")
```

## Advanced Features

### Custom Factor Creation

```python
def create_custom_factors(price_data, volume_data):
    """Create custom factors from price and volume data"""
    
    # Volatility factor
    volatility_factor = Factor(
        name="Volatility",
        description="Realized volatility factor",
        factor_type="custom",
        data=price_data.pct_change().rolling(20).std(),
        benchmark_exposure=0.0
    )
    
    # Volume factor
    volume_factor = Factor(
        name="Volume",
        description="Trading volume factor",
        factor_type="custom",
        data=volume_data.pct_change(),
        benchmark_exposure=0.0
    )
    
    # Mean reversion factor
    returns = price_data.pct_change()
    mean_reversion_factor = Factor(
        name="MeanReversion",
        description="Mean reversion factor",
        factor_type="custom",
        data=-returns.rolling(5).mean(),  # Negative of recent returns
        benchmark_exposure=0.0
    )
    
    return [volatility_factor, volume_factor, mean_reversion_factor]

# Use custom factors
custom_factors = create_custom_factors(price_data, volume_data)
```

### Multi-Period Attribution

```python
async def multi_period_attribution(strategy_returns, benchmark_returns, factors):
    """Perform attribution analysis over multiple periods"""
    
    # Split data into quarters
    quarterly_results = []
    
    for year in [2022, 2023]:
        for quarter in [1, 2, 3, 4]:
            start_date = pd.Timestamp(f"{year}-{(quarter-1)*3+1:02d}-01")
            end_date = pd.Timestamp(f"{year}-{quarter*3:02d}-{[31,30,30,31][quarter-1]:02d}")
            
            # Filter data for period
            period_strategy = strategy_returns[start_date:end_date]
            period_benchmark = benchmark_returns[start_date:end_date]
            period_factors = []
            
            for factor in factors:
                period_factor = Factor(
                    name=factor.name,
                    description=factor.description,
                    factor_type=factor.factor_type,
                    data=factor.data[start_date:end_date],
                    benchmark_exposure=factor.benchmark_exposure
                )
                period_factors.append(period_factor)
            
            # Perform attribution for period
            if len(period_strategy) > 20:  # Minimum data requirement
                attribution = await attributor.analyze_strategy_performance(
                    strategy_name=f"Strategy Q{quarter} {year}",
                    strategy_returns=period_strategy,
                    benchmark_returns=period_benchmark,
                    factors=period_factors
                )
                quarterly_results.append(attribution)
    
    return quarterly_results

# Run multi-period analysis
quarterly_attributions = asyncio.run(multi_period_attribution(
    strategy_returns, benchmark_returns, factors
))

# Analyze quarterly results
for i, attribution in enumerate(quarterly_attributions):
    print(f"\\nQuarter {i+1}:")
    print(f"  Return: {attribution.performance_metrics.total_return:.2%}")
    print(f"  Alpha: {attribution.performance_metrics.alpha:.4f}")
    print(f"  Beta: {attribution.performance_metrics.beta:.3f}")
```

### Risk-Adjusted Attribution

```python
def calculate_risk_adjusted_attribution(attribution_results):
    """Calculate risk-adjusted attribution metrics"""
    
    risk_adjusted_metrics = {}
    
    for attribution in attribution_results:
        metrics = attribution.performance_metrics
        
        # Risk-adjusted return
        risk_adjusted_return = metrics.total_return / metrics.volatility if metrics.volatility > 0 else 0
        
        # Risk-adjusted alpha
        risk_adjusted_alpha = metrics.alpha / metrics.volatility if metrics.volatility > 0 else 0
        
        # Information ratio components
        excess_return = metrics.total_return - (metrics.beta * 0.08)  # Assuming 8% market return
        tracking_error = metrics.tracking_error
        
        risk_adjusted_metrics[attribution.strategy_name] = {
            'risk_adjusted_return': risk_adjusted_return,
            'risk_adjusted_alpha': risk_adjusted_alpha,
            'sharpe_ratio': metrics.sharpe_ratio,
            'information_ratio': metrics.information_ratio,
            'calmar_ratio': metrics.calmar_ratio,
            'sortino_ratio': metrics.sortino_ratio
        }
    
    return risk_adjusted_metrics

# Calculate risk-adjusted metrics
risk_metrics = calculate_risk_adjusted_attribution([attribution])
```

### Factor Timing Analysis

```python
def analyze_factor_timing(attribution_results):
    """Analyze factor timing ability"""
    
    timing_analysis = {}
    
    for attribution in attribution_results:
        if not attribution.attribution_results:
            continue
            
        attr_result = attribution.attribution_results[0]
        factor_contributions = attr_result.factor_contributions
        
        # Analyze factor timing
        for factor_name, contribution in factor_contributions.items():
            if factor_name not in timing_analysis:
                timing_analysis[factor_name] = []
            
            timing_analysis[factor_name].append({
                'period': attribution.analysis_period,
                'contribution': contribution,
                'strategy': attribution.strategy_name
            })
    
    # Calculate timing statistics
    timing_stats = {}
    for factor_name, contributions in timing_analysis.items():
        values = [c['contribution'] for c in contributions]
        
        timing_stats[factor_name] = {
            'mean_contribution': np.mean(values),
            'std_contribution': np.std(values),
            'positive_periods': sum(1 for v in values if v > 0),
            'total_periods': len(values),
            'consistency': sum(1 for v in values if v > 0) / len(values) if values else 0
        }
    
    return timing_stats

# Analyze factor timing
timing_stats = analyze_factor_timing(quarterly_attributions)

print("Factor Timing Analysis:")
for factor_name, stats in timing_stats.items():
    print(f"\\n{factor_name}:")
    print(f"  Mean Contribution: {stats['mean_contribution']:.4f}")
    print(f"  Consistency: {stats['consistency']:.2%}")
    print(f"  Positive Periods: {stats['positive_periods']}/{stats['total_periods']}")
```

## Performance Metrics Reference

### Basic Performance Metrics

```python
# Total and annualized returns
total_return = (1 + returns).prod() - 1
annualized_return = (1 + total_return) ** (252 / len(returns)) - 1

# Risk metrics
volatility = returns.std() * np.sqrt(252)
max_drawdown = ((1 + returns).cumprod() / (1 + returns).cumprod().expanding().max() - 1).min()

# Risk-adjusted ratios
sharpe_ratio = (annualized_return - risk_free_rate) / volatility
sortino_ratio = (annualized_return - risk_free_rate) / downside_deviation
calmar_ratio = annualized_return / abs(max_drawdown)
```

### Benchmark-Relative Metrics

```python
# Beta and alpha calculation
excess_returns = strategy_returns - benchmark_returns
beta = np.cov(strategy_returns, benchmark_returns)[0,1] / np.var(benchmark_returns)
alpha = np.mean(strategy_returns) - beta * np.mean(benchmark_returns)

# Tracking error and information ratio
tracking_error = excess_returns.std() * np.sqrt(252)
information_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252)

# Capture ratios
up_periods = benchmark_returns > 0
down_periods = benchmark_returns < 0
up_capture = strategy_returns[up_periods].mean() / benchmark_returns[up_periods].mean()
down_capture = strategy_returns[down_periods].mean() / benchmark_returns[down_periods].mean()
```

### Factor Model Metrics

```python
# Multi-factor model
# Returns = Alpha + Beta1*Factor1 + Beta2*Factor2 + ... + Specific_Return

# Factor loadings (betas)
factor_loadings = regression_coefficients

# R-squared (explained variance)
r_squared = 1 - (residual_variance / total_variance)

# Specific risk (idiosyncratic risk)
specific_risk = np.std(residuals) * np.sqrt(252)

# Systematic risk (factor-related risk)
systematic_risk = np.sqrt(sum((loading * factor_vol)**2 for loading, factor_vol in zip(loadings, factor_vols)))
```

## Attribution Methods

### Factor Model Attribution

```python
# Factor contribution = (Strategy Loading - Benchmark Loading) × Factor Return
factor_contribution = (strategy_beta - benchmark_beta) * factor_return

# Selection effect = Strategy Alpha - Benchmark Alpha
selection_effect = strategy_alpha - benchmark_alpha

# Allocation effect = Sum of factor contributions
allocation_effect = sum(factor_contributions.values())

# Total excess return = Selection + Allocation + Interaction
excess_return = selection_effect + allocation_effect + interaction_effect
```

### Brinson Attribution

```python
# Allocation effect = (Portfolio Weight - Benchmark Weight) × Benchmark Return
allocation_effect = (portfolio_weight - benchmark_weight) * benchmark_return

# Selection effect = Portfolio Weight × (Portfolio Return - Benchmark Return)
selection_effect = portfolio_weight * (portfolio_return - benchmark_return)

# Interaction effect = (Portfolio Weight - Benchmark Weight) × (Portfolio Return - Benchmark Return)
interaction_effect = (portfolio_weight - benchmark_weight) * (portfolio_return - benchmark_return)
```

## Risk Decomposition

### Systematic vs Specific Risk

```python
# Total risk decomposition
total_variance = strategy_returns.var()

# Systematic variance (from factors)
systematic_variance = sum((beta_i * factor_vol_i)**2 for beta_i, factor_vol_i in factor_exposures)

# Specific variance (idiosyncratic)
specific_variance = total_variance - systematic_variance

# Risk percentages
systematic_risk_pct = systematic_variance / total_variance
specific_risk_pct = specific_variance / total_variance
```

### Factor Risk Contributions

```python
def calculate_factor_risk_contributions(factor_loadings, factor_covariance_matrix):
    """Calculate individual factor risk contributions"""
    
    risk_contributions = {}
    
    for i, (factor_name, loading) in enumerate(factor_loadings.items()):
        # Marginal contribution to risk
        marginal_risk = 2 * loading * factor_covariance_matrix[i, i]
        
        # Component contribution to risk
        component_risk = loading**2 * factor_covariance_matrix[i, i]
        
        risk_contributions[factor_name] = {
            'marginal_risk': marginal_risk,
            'component_risk': component_risk,
            'risk_percentage': component_risk / total_variance
        }
    
    return risk_contributions
```

## Visualization and Reporting

### Performance Attribution Report

```python
def generate_attribution_report(attribution):
    """Generate comprehensive attribution report"""
    
    report = {
        'executive_summary': {
            'strategy_name': attribution.strategy_name,
            'analysis_period': attribution.analysis_period,
            'total_return': attribution.performance_metrics.total_return,
            'excess_return': attribution.attribution_results[0].excess_return if attribution.attribution_results else 0,
            'information_ratio': attribution.performance_metrics.information_ratio,
            'tracking_error': attribution.performance_metrics.tracking_error
        },
        
        'performance_metrics': {
            'return_metrics': {
                'total_return': attribution.performance_metrics.total_return,
                'annualized_return': attribution.performance_metrics.annualized_return,
                'volatility': attribution.performance_metrics.volatility
            },
            'risk_adjusted_metrics': {
                'sharpe_ratio': attribution.performance_metrics.sharpe_ratio,
                'sortino_ratio': attribution.performance_metrics.sortino_ratio,
                'calmar_ratio': attribution.performance_metrics.calmar_ratio
            },
            'drawdown_metrics': {
                'max_drawdown': attribution.performance_metrics.max_drawdown,
                'recovery_factor': attribution.performance_metrics.recovery_factor
            }
        },
        
        'benchmark_analysis': {},
        'factor_analysis': {
            'factor_exposures': attribution.factor_exposures,
            'risk_decomposition': attribution.risk_decomposition
        },
        
        'attribution_analysis': {}
    }
    
    # Add benchmark analysis
    if attribution.benchmark_comparisons:
        benchmark = attribution.benchmark_comparisons[0]
        report['benchmark_analysis'] = {
            'alpha': benchmark.alpha,
            'beta': benchmark.beta,
            'correlation': benchmark.correlation,
            'r_squared': benchmark.r_squared,
            'tracking_error': benchmark.tracking_error,
            'information_ratio': benchmark.information_ratio,
            'up_capture': benchmark.up_capture_ratio,
            'down_capture': benchmark.down_capture_ratio
        }
    
    # Add attribution analysis
    if attribution.attribution_results:
        attr_result = attribution.attribution_results[0]
        report['attribution_analysis'] = {
            'excess_return': attr_result.excess_return,
            'selection_effect': attr_result.selection_effect,
            'allocation_effect': attr_result.allocation_effect,
            'interaction_effect': attr_result.interaction_effect,
            'factor_contributions': attr_result.factor_contributions
        }
    
    return report

# Generate report
report = generate_attribution_report(attribution)

# Print formatted report
print("=== PERFORMANCE ATTRIBUTION REPORT ===")
print(f"Strategy: {report['executive_summary']['strategy_name']}")
print(f"Period: {report['executive_summary']['analysis_period'][0].date()} to {report['executive_summary']['analysis_period'][1].date()}")
print(f"Total Return: {report['executive_summary']['total_return']:.2%}")
print(f"Information Ratio: {report['executive_summary']['information_ratio']:.3f}")
```

## Best Practices

### 1. Factor Selection

```python
def select_relevant_factors(strategy_returns, candidate_factors, min_r_squared=0.05):
    """Select relevant factors based on explanatory power"""
    
    selected_factors = []
    
    for factor in candidate_factors:
        # Test individual factor explanatory power
        model = FactorModelBuilder().build_factor_model(strategy_returns, [factor])
        
        if model['r_squared'] >= min_r_squared:
            selected_factors.append(factor)
    
    return selected_factors
```

### 2. Attribution Validation

```python
def validate_attribution_results(attribution_result):
    """Validate attribution results for consistency"""
    
    validation_checks = {
        'excess_return_consistency': abs(
            attribution_result.excess_return - 
            (attribution_result.total_return - attribution_result.benchmark_return)
        ) < 0.0001,
        
        'attribution_sum': abs(
            attribution_result.excess_return - 
            (attribution_result.selection_effect + 
             attribution_result.allocation_effect + 
             attribution_result.interaction_effect)
        ) < 0.001,
        
        'factor_contributions_reasonable': all(
            abs(contrib) < 1.0 for contrib in attribution_result.factor_contributions.values()
        )
    }
    
    return validation_checks
```

### 3. Performance Monitoring

```python
def monitor_attribution_stability(historical_attributions):
    """Monitor attribution stability over time"""
    
    stability_metrics = {}
    
    # Factor exposure stability
    for factor_name in historical_attributions[0].factor_exposures.keys():
        exposures = [attr.factor_exposures[factor_name] for attr in historical_attributions]
        stability_metrics[f"{factor_name}_exposure_stability"] = 1 - (np.std(exposures) / np.mean(np.abs(exposures)))
    
    # Alpha stability
    alphas = [attr.performance_metrics.alpha for attr in historical_attributions]
    stability_metrics['alpha_stability'] = 1 - (np.std(alphas) / np.mean(np.abs(alphas)))
    
    return stability_metrics
```

## Testing

### Unit Testing

```bash
# Run all attribution tests
python -m pytest tests/test_strategy_performance_attribution.py -v

# Run specific test categories
python -m pytest tests/test_strategy_performance_attribution.py::TestPerformanceCalculator -v
python -m pytest tests/test_strategy_performance_attribution.py::TestBenchmarkAnalyzer -v
python -m pytest tests/test_strategy_performance_attribution.py::TestAttributionAnalyzer -v

# Run integration test
python -m pytest tests/test_strategy_performance_attribution.py::test_integration_scenario -v
```

### Performance Testing

```python
import time

async def performance_test():
    """Test attribution performance with large datasets"""
    
    # Generate large dataset
    dates = pd.date_range(start='2010-01-01', end='2023-12-31', freq='D')
    strategy_returns = pd.Series(np.random.normal(0.001, 0.02, len(dates)), index=dates)
    benchmark_returns = pd.Series(np.random.normal(0.0008, 0.015, len(dates)), index=dates)
    
    # Create multiple factors
    factors = []
    for i in range(10):
        factor = Factor(
            name=f"Factor_{i}",
            description=f"Test factor {i}",
            factor_type="style",
            data=pd.Series(np.random.normal(0, 0.01, len(dates)), index=dates)
        )
        factors.append(factor)
    
    # Time the attribution analysis
    start_time = time.time()
    
    attribution = await attributor.analyze_strategy_performance(
        strategy_name="Performance Test Strategy",
        strategy_returns=strategy_returns,
        benchmark_returns=benchmark_returns,
        factors=factors
    )
    
    end_time = time.time()
    
    print(f"Attribution analysis completed in {end_time - start_time:.2f} seconds")
    print(f"Data points: {len(dates)}")
    print(f"Factors: {len(factors)}")

# Run performance test
asyncio.run(performance_test())
```

## Future Enhancements

Planned improvements:

- **Holdings-Based Attribution**: Attribution based on portfolio holdings
- **Sector Attribution**: Sector-specific attribution analysis
- **Currency Attribution**: Multi-currency attribution for global strategies
- **Options Attribution**: Attribution for options strategies
- **Real-Time Attribution**: Live attribution monitoring
- **Machine Learning Attribution**: ML-based factor discovery and attribution

## API Reference

### StrategyPerformanceAttributor

Main attribution analysis class.

#### Methods

- `analyze_strategy_performance(...)`: Perform comprehensive attribution analysis
- `_calculate_risk_decomposition(...)`: Calculate risk decomposition
- `_create_performance_summary(...)`: Create performance summary

### PerformanceCalculator

Performance metrics calculation.

#### Methods

- `calculate_performance_metrics(returns, benchmark_returns, risk_free_rate)`: Calculate comprehensive metrics
- `_infer_frequency(returns)`: Infer data frequency for annualization

### BenchmarkAnalyzer

Benchmark comparison analysis.

#### Methods

- `compare_to_benchmark(strategy_returns, benchmark_returns, benchmark_name)`: Compare to benchmark

### AttributionAnalyzer

Attribution analysis implementation.

#### Methods

- `perform_attribution_analysis(...)`: Perform attribution analysis
- `_factor_based_attribution(...)`: Factor model attribution
- `_brinson_attribution(...)`: Brinson attribution
- `_returns_based_attribution(...)`: Simple returns attribution

### FactorModelBuilder

Factor model construction.

#### Methods

- `build_factor_model(returns, factors, method)`: Build multi-factor model
- `_simple_factor_model(...)`: Simple factor model fallback

## Examples

See `nautilus_trader_engine/backtesting/strategy_performance_attribution.py` for the complete example in the `example_usage()` function, which demonstrates:

- Factor definition and creation
- Comprehensive attribution analysis
- Performance metrics calculation
- Benchmark comparison
- Risk decomposition analysis
- Factor exposure analysis