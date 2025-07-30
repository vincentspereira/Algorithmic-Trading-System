# Cross-Asset Analytics System Documentation

## Overview

The Cross-Asset Analytics System provides comprehensive analysis capabilities for multi-asset portfolios, including correlation analysis, arbitrage detection, spread trading opportunities, and risk attribution across different asset classes.

## Key Features

- **Cross-Asset Correlation Analysis**: Real-time correlation monitoring with breakdown detection
- **Arbitrage Detection**: Statistical, triangular, and calendar arbitrage opportunities
- **Spread Trading Analysis**: Pairs trading, calendar spreads, and yield curve strategies
- **Risk Attribution**: Portfolio-level risk decomposition and attribution
- **Multi-Asset Support**: Equities, bonds, currencies, futures, and cryptocurrencies

## Architecture

### Core Components

1. **CrossAssetCorrelationAnalyzer**: Analyzes correlations between assets
2. **ArbitrageDetector**: Identifies arbitrage opportunities
3. **SpreadTradingAnalyzer**: Finds spread trading opportunities
4. **CrossAssetRiskAttributor**: Performs risk attribution analysis
5. **CrossAssetAnalyticsEngine**: Main orchestration engine

## Usage Examples

### Basic Setup

```python
import asyncio
import numpy as np
from nautilus_trader_engine.analytics.cross_asset_analytics import (
    CrossAssetAnalyticsEngine
)

# Initialize the analytics engine
engine = CrossAssetAnalyticsEngine()
```

### Comprehensive Analysis

```python
async def run_analysis():
    # Prepare market data
    market_data = {
        "AAPL": {
            "prices": np.array([150, 151, 149, 152, 148]),
            "weight": 0.4
        },
        "SPY": {
            "prices": np.array([450, 452, 448, 455, 447]),
            "weight": 0.6
        }
    }
    
    # Run comprehensive analysis
    results = await engine.run_comprehensive_analysis(market_data)
    
    print(f"Analysis completed: {results['summary']}")
    return results

# Run the analysis
results = asyncio.run(run_analysis())
```

### Correlation Analysis

```python
from nautilus_trader_engine.analytics.cross_asset_analytics import (
    CrossAssetCorrelationAnalyzer
)

async def analyze_correlations():
    analyzer = CrossAssetCorrelationAnalyzer()
    
    # Price data for multiple assets
    price_data = {
        "AAPL": np.array([150, 151, 149, 152, 148]),
        "GOOGL": np.array([2800, 2820, 2790, 2850, 2780]),
        "SPY": np.array([450, 452, 448, 455, 447])
    }
    
    # Calculate correlation matrix
    correlation_matrix = await analyzer.calculate_correlation_matrix(price_data)
    print("Correlation Matrix:")
    print(correlation_matrix)
    
    # Pairwise correlation analysis
    correlation_result = await analyzer.analyze_pairwise_correlation(
        price_data["AAPL"], price_data["SPY"], "AAPL", "SPY"
    )
    
    print(f"AAPL-SPY Correlation: {correlation_result.correlation:.3f}")
    print(f"P-value: {correlation_result.p_value:.3f}")
    print(f"Confidence Interval: {correlation_result.confidence_interval}")

asyncio.run(analyze_correlations())
```

### Arbitrage Detection

```python
from nautilus_trader_engine.analytics.cross_asset_analytics import (
    ArbitrageDetector, ArbitrageType
)

async def detect_arbitrage():
    detector = ArbitrageDetector(min_profit_threshold=0.001)
    
    # Statistical arbitrage detection
    price_data = {
        "ASSET1": np.array([100, 101, 99, 102, 98]),
        "ASSET2": np.array([200, 203, 197, 206, 194])  # Diverging ratio
    }
    
    opportunities = await detector.detect_statistical_arbitrage(price_data)
    
    for opp in opportunities:
        print(f"Arbitrage Opportunity:")
        print(f"  Type: {opp.arbitrage_type.value}")
        print(f"  Assets: {opp.assets_involved}")
        print(f"  Expected Profit: {opp.expected_profit:.4f}")
        print(f"  Confidence: {opp.confidence_score:.3f}")
    
    # Triangular arbitrage (currency example)
    currency_pairs = {
        "EURUSD": 1.1000,
        "GBPUSD": 1.3000,
        "EURGBP": 0.8500  # Potential arbitrage opportunity
    }
    
    triangular_opportunities = await detector.detect_triangular_arbitrage(currency_pairs)
    
    for opp in triangular_opportunities:
        print(f"Triangular Arbitrage:")
        print(f"  Assets: {opp.assets_involved}")
        print(f"  Expected Profit: {opp.expected_profit:.4f}")

asyncio.run(detect_arbitrage())
```

### Spread Trading Analysis

```python
from nautilus_trader_engine.analytics.cross_asset_analytics import (
    SpreadTradingAnalyzer, SpreadType
)

async def analyze_spreads():
    analyzer = SpreadTradingAnalyzer(z_score_threshold=2.0)
    
    # Pairs trading analysis
    asset1_prices = np.array([100, 101, 99, 102, 98, 105])  # Diverging
    asset2_prices = np.array([200, 202, 198, 204, 196, 200])  # Mean reverting
    
    pairs_opportunity = await analyzer.analyze_pairs_trading(
        asset1_prices, asset2_prices, "ASSET1", "ASSET2"
    )
    
    if pairs_opportunity and pairs_opportunity.entry_signal:
        print(f"Pairs Trading Opportunity:")
        print(f"  Long: {pairs_opportunity.long_asset}")
        print(f"  Short: {pairs_opportunity.short_asset}")
        print(f"  Z-Score: {pairs_opportunity.z_score:.2f}")
        print(f"  Target Profit: {pairs_opportunity.target_profit:.4f}")
        print(f"  Confidence: {pairs_opportunity.confidence:.3f}")
    
    # Calendar spread analysis
    near_prices = np.array([100, 101, 99, 102, 98])
    far_prices = np.array([102, 103, 101, 104, 100])
    
    calendar_opportunity = await analyzer.analyze_calendar_spread(
        near_prices, far_prices, "NEAR_CONTRACT", "FAR_CONTRACT"
    )
    
    if calendar_opportunity and calendar_opportunity.entry_signal:
        print(f"Calendar Spread Opportunity:")
        print(f"  Long: {calendar_opportunity.long_asset}")
        print(f"  Short: {calendar_opportunity.short_asset}")
        print(f"  Current Spread: {calendar_opportunity.current_spread:.2f}")
        print(f"  Z-Score: {calendar_opportunity.z_score:.2f}")

asyncio.run(analyze_spreads())
```

### Risk Attribution

```python
from nautilus_trader_engine.analytics.cross_asset_analytics import (
    CrossAssetRiskAttributor
)

async def analyze_risk():
    attributor = CrossAssetRiskAttributor()
    
    # Returns data for portfolio assets
    returns_data = {
        "ASSET1": np.random.normal(0.001, 0.02, 100),
        "ASSET2": np.random.normal(0.0008, 0.025, 100),
        "ASSET3": np.random.normal(0.0005, 0.015, 100)
    }
    
    # Portfolio weights
    weights = {"ASSET1": 0.5, "ASSET2": 0.3, "ASSET3": 0.2}
    
    # Calculate risk attribution
    attribution = await attributor.calculate_portfolio_risk_attribution(
        returns_data, weights
    )
    
    print(f"Portfolio Risk Attribution:")
    print(f"  Portfolio VaR: {attribution.portfolio_var:.4f}")
    print(f"  Diversification Ratio: {attribution.diversification_ratio:.3f}")
    print(f"  Concentration Risk: {attribution.concentration_risk:.3f}")
    print(f"  Correlation Risk: {attribution.correlation_risk:.3f}")
    
    print(f"\nComponent Contributions:")
    for asset, contribution in attribution.component_contributions.items():
        print(f"  {asset}: {contribution:.4f}")
    
    # Correlation risk analysis
    correlation_analysis = await attributor.analyze_correlation_risk(returns_data)
    
    if "normal" in correlation_analysis:
        normal_stats = correlation_analysis["normal"]
        print(f"\nCorrelation Analysis (Normal Conditions):")
        print(f"  Mean Correlation: {normal_stats['mean_correlation']:.3f}")
        print(f"  Max Correlation: {normal_stats['max_correlation']:.3f}")
        print(f"  Min Correlation: {normal_stats['min_correlation']:.3f}")

asyncio.run(analyze_risk())
```

## Data Structures

### CorrelationResult

```python
@dataclass
class CorrelationResult:
    asset1: str
    asset2: str
    correlation: float
    p_value: float
    confidence_interval: Tuple[float, float]
    rolling_correlation: List[float]
    correlation_stability: float
    last_updated: datetime
```

### ArbitrageOpportunity

```python
@dataclass
class ArbitrageOpportunity:
    opportunity_id: str
    arbitrage_type: ArbitrageType
    assets_involved: List[str]
    expected_profit: float
    confidence_score: float
    risk_score: float
    execution_complexity: str
    time_horizon: str
    market_conditions: Dict[str, Any]
    detected_at: datetime
    expires_at: Optional[datetime]
```

### SpreadOpportunity

```python
@dataclass
class SpreadOpportunity:
    spread_id: str
    spread_type: SpreadType
    long_asset: str
    short_asset: str
    current_spread: float
    historical_mean: float
    z_score: float
    entry_signal: bool
    exit_signal: bool
    target_profit: float
    stop_loss: float
    confidence: float
    detected_at: datetime
```

### RiskAttribution

```python
@dataclass
class RiskAttribution:
    portfolio_var: float
    component_vars: Dict[str, float]
    marginal_vars: Dict[str, float]
    component_contributions: Dict[str, float]
    diversification_ratio: float
    concentration_risk: float
    correlation_risk: float
    attribution_date: datetime
```

## Analysis Types

### Correlation Analysis

- **Pearson Correlation**: Linear relationship measurement
- **Spearman Correlation**: Rank-based correlation for non-linear relationships
- **Rolling Correlation**: Time-varying correlation analysis
- **Correlation Breakdown Detection**: Identifies periods of correlation instability

### Arbitrage Detection

- **Statistical Arbitrage**: Mean-reversion based opportunities
- **Triangular Arbitrage**: Currency cross-rate inconsistencies
- **Calendar Arbitrage**: Futures contract spread opportunities
- **Cross-Exchange Arbitrage**: Price differences across venues

### Spread Trading

- **Pairs Trading**: Cointegrated asset pair strategies
- **Calendar Spreads**: Time-based spread strategies
- **Inter-Commodity Spreads**: Related commodity strategies
- **Yield Curve Spreads**: Interest rate curve strategies

### Risk Attribution

- **Component VaR**: Individual asset risk contributions
- **Marginal VaR**: Incremental risk from position changes
- **Diversification Benefits**: Portfolio vs. sum of parts
- **Concentration Risk**: Portfolio concentration measures

## Configuration Options

### Correlation Analyzer

```python
analyzer = CrossAssetCorrelationAnalyzer(
    lookback_periods=[30, 60, 120, 252]  # Different time horizons
)
```

### Arbitrage Detector

```python
detector = ArbitrageDetector(
    min_profit_threshold=0.001  # Minimum profit threshold (0.1%)
)
```

### Spread Analyzer

```python
analyzer = SpreadTradingAnalyzer(
    z_score_threshold=2.0  # Entry signal threshold
)
```

## Performance Considerations

- **Vectorized Calculations**: Uses NumPy for efficient computation
- **Async Processing**: Non-blocking analysis operations
- **Caching**: Results caching for repeated calculations
- **Memory Management**: Efficient handling of large datasets

## Error Handling

The system includes comprehensive error handling:

- Graceful degradation for insufficient data
- Validation of input data quality
- Logging of analysis failures
- Fallback mechanisms for missing dependencies

## Testing

Run the test suite:

```bash
# Run all tests
python -m pytest tests/test_cross_asset_analytics.py -v

# Run specific test categories
python -m pytest tests/test_cross_asset_analytics.py::TestCrossAssetCorrelationAnalyzer -v
python -m pytest tests/test_cross_asset_analytics.py::TestArbitrageDetector -v
python -m pytest tests/test_cross_asset_analytics.py::TestSpreadTradingAnalyzer -v

# Run integration test
python -m pytest tests/test_cross_asset_analytics.py::test_integration_scenario -v
```

## Integration with Trading System

The Cross-Asset Analytics system integrates with:

- **Asset Class Framework**: Multi-asset support
- **Risk Management System**: Portfolio risk analysis
- **Order Management System**: Trade execution for opportunities
- **Market Data System**: Real-time price feeds

## Future Enhancements

Planned improvements:

- **Machine Learning Models**: Advanced pattern recognition
- **Real-Time Streaming**: Continuous analysis updates
- **Alternative Data**: News, sentiment, and social media integration
- **Advanced Strategies**: Multi-leg arbitrage and complex spreads
- **Performance Attribution**: Return-based analysis

## API Reference

### CrossAssetAnalyticsEngine

Main engine for comprehensive analysis.

#### Methods

- `run_comprehensive_analysis(market_data)`: Complete analysis suite
- Individual component access via analyzer properties

### Component Analyzers

- `CrossAssetCorrelationAnalyzer`: Correlation analysis
- `ArbitrageDetector`: Arbitrage opportunity detection
- `SpreadTradingAnalyzer`: Spread trading analysis
- `CrossAssetRiskAttributor`: Risk attribution analysis

## Examples

See `nautilus_trader_engine/analytics/cross_asset_analytics.py` for the complete example in the `example_usage()` function.