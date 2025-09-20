# Pairs Trading Indicators and Strategies

A comprehensive market-neutral pairs trading system designed for algorithmic trading with spread/ratio-based technical indicators and candlestick patterns.

## Overview

This module provides a complete pairs trading framework that transforms traditional OHLCV data into spread and ratio relationships between correlated assets. It includes:

- **Spread/Ratio Calculations**: Basic, volume-weighted, and logarithmic variants
- **Technical Indicators**: Adapted for spread/ratio data (SMA, EMA, RSI, MACD, Bollinger Bands, etc.)
- **Candlestick Patterns**: Specialized pattern recognition for spread/ratio relationships
- **Strategy Implementation**: Complete trading strategies with signal generation and position management
- **Risk Management**: Built-in stop-loss, take-profit, and drawdown controls

## Module Structure

```
pairs_trading/
├── __init__.py                     # Module initialization and exports
├── pairs_trading_indicators.py     # Core indicators and calculations
├── pairs_candlestick_patterns.py   # Pattern recognition for pairs
├── pairs_trading_strategies.py     # Complete strategy implementations
└── README.md                       # This documentation
```

## Key Features

### 1. Spread/Ratio Calculations

#### Basic Calculations
```python
# Spread calculations
Spread_Open = Open_Stock1 - Open_Stock2
Spread_High = High_Stock1 - High_Stock2
Spread_Low = Low_Stock1 - Low_Stock2
Spread_Close = Close_Stock1 - Close_Stock2
Spread_Volume = Volume_Stock1 + Volume_Stock2

# Ratio calculations
Ratio_Open = Open_Stock1 / Open_Stock2
Ratio_High = High_Stock1 / High_Stock2
Ratio_Low = Low_Stock1 / Low_Stock2
Ratio_Close = Close_Stock1 / Close_Stock2
Ratio_Volume = (Volume_Stock1 + Volume_Stock2) / 2
```

#### Volume-Weighted Variants
```python
# Volume-weighted spread
VW_Spread = ((Price1 * Volume1) - (Price2 * Volume2)) / (Volume1 + Volume2)

# Volume-weighted ratio
VW_Ratio = (Price1 * Volume1) / (Price2 * Volume2)
```

### 2. Technical Indicators for Pairs Trading

#### Trend Indicators
- **Simple Moving Average (SMA)**: Spread/ratio trend identification
- **Exponential Moving Average (EMA)**: Responsive trend following
- **Volume-Weighted Moving Average (VWMA)**: Volume-confirmed trends
- **Hull Moving Average**: Reduced lag trend signals

#### Momentum Indicators
- **RSI**: Overbought/oversold conditions in spread/ratio
- **MACD**: Momentum changes and crossover signals
- **Stochastic**: Relative position within recent range
- **Williams %R**: Momentum oscillator for pairs

#### Volatility Indicators
- **Bollinger Bands**: Dynamic support/resistance levels
- **Average True Range (ATR)**: Volatility measurement
- **Keltner Channels**: Trend-following bands

#### Volume Indicators
- **Volume-Weighted Average Price (VWAP)**: Fair value estimation
- **On-Balance Volume (OBV)**: Volume-price relationship
- **Money Flow Index (MFI)**: Volume-weighted RSI

### 3. Candlestick Patterns for Pairs

#### Reversal Patterns
- **Spread Hammer/Hanging Man**: Potential trend reversals
- **Spread Shooting Star/Inverted Hammer**: Top/bottom formations
- **Spread Engulfing**: Strong reversal signals
- **Spread Morning/Evening Star**: Three-candle reversal patterns
- **Spread Doji Variants**: Indecision and potential reversals

#### Continuation Patterns
- **Spread Marubozu**: Strong directional movement
- **Spread Spinning Top**: Market indecision

#### Pairs-Specific Patterns
- **Ratio Convergence Hammer**: Mean reversion signals
- **Ratio Divergence Star**: Breakout patterns
- **Volume Confirmed Reversal**: High-confidence reversals

### 4. Strategy Components

#### Pair Selection
- **Correlation Analysis**: Identify highly correlated pairs
- **Cointegration Testing**: Statistical relationship validation
- **Beta Calculation**: Market-neutral positioning
- **Sector/Industry Filtering**: Logical pair relationships

#### Convergence Trading
- **Mean Reversion**: Trade spread deviations from historical mean
- **Z-Score Thresholds**: Entry/exit based on statistical significance
- **Dynamic Thresholds**: Adaptive entry/exit levels

#### Divergence Trading
- **Breakout Detection**: Identify new price relationships
- **Momentum Confirmation**: Trend-following signals
- **Volume Validation**: Confirm breakout strength

## Usage Examples

### Basic Indicator Calculation

```python
from pairs_trading_indicators import PairsTradingIndicators, SpreadCalculator

# Initialize calculator
indicators = PairsTradingIndicators()
spread_calc = SpreadCalculator()

# Calculate spread data
spread_data = spread_calc.calculate_spread(
    stock1_open, stock1_high, stock1_low, stock1_close, stock1_volume,
    stock2_open, stock2_high, stock2_low, stock2_close, stock2_volume
)

# Calculate technical indicators
spread_indicators = indicators.calculate_spread_indicators(
    spread_data['spread_open'],
    spread_data['spread_high'],
    spread_data['spread_low'],
    spread_data['spread_close'],
    spread_data['spread_volume']
)

# Access indicators
print(f"Spread SMA: {spread_indicators['sma'][-1]}")
print(f"Spread RSI: {spread_indicators['rsi'][-1]}")
print(f"Spread Bollinger Bands: {spread_indicators['bollinger_bands']}")
```

### Pattern Recognition

```python
from pairs_candlestick_patterns import SpreadPatternAnalyzer

# Initialize pattern analyzer
analyzer = SpreadPatternAnalyzer()

# Analyze spread patterns
spread_analysis = analyzer.analyze_spread_patterns(
    spread_open, spread_high, spread_low, spread_close, spread_volume
)

# Get pattern recommendations
for recommendation in spread_analysis['recommendations']:
    print(f"Action: {recommendation['action']}")
    print(f"Reason: {recommendation['reason']}")
    print(f"Confidence: {recommendation['confidence']:.2f}")
```

### Complete Strategy Implementation

```python
from pairs_trading_strategies import PairsTradingEngine, StrategyConfig, StrategyType

# Configure strategy
config = StrategyConfig(
    strategy_type=StrategyType.HYBRID,
    lookback_period=20,
    entry_threshold=2.0,
    exit_threshold=0.5,
    max_pairs=10,
    use_candlestick_patterns=True
)

# Initialize trading engine
engine = PairsTradingEngine(config)

# Initialize with universe data
init_result = engine.initialize_strategy(universe_data)

# Generate trading signals
signals = engine.generate_signals(current_data)

# Execute signals
execution_results = engine.execute_signals(signals)

# Monitor performance
performance = engine.get_strategy_performance()
print(f"Win Rate: {performance['win_rate']:.2%}")
print(f"Total PnL: ${performance['total_pnl']:.2f}")
print(f"Sharpe Ratio: {performance['sharpe_ratio']:.2f}")
```

## Strategy Types

### 1. Mean Reversion Strategy
- **Concept**: Trade when spread/ratio deviates significantly from historical mean
- **Entry**: Z-score > threshold (short spread) or Z-score < -threshold (long spread)
- **Exit**: Z-score returns to near zero (mean reversion)
- **Best For**: Stable, cointegrated pairs with strong mean-reverting behavior

### 2. Momentum Strategy
- **Concept**: Follow trends in spread/ratio relationships
- **Entry**: MACD crossovers, RSI momentum, trend confirmations
- **Exit**: Momentum reversal signals
- **Best For**: Pairs experiencing structural changes or trending markets

### 3. Hybrid Strategy
- **Concept**: Combine mean reversion and momentum signals
- **Entry**: Consensus between multiple signal types
- **Exit**: Adaptive based on market conditions
- **Best For**: Diverse market conditions and robust performance

## Risk Management Features

### Position Sizing
- **Equal Dollar**: Equal dollar amounts in each leg
- **Beta Neutral**: Adjust for beta differences
- **Volatility Adjusted**: Scale by historical volatility

### Risk Controls
- **Stop Loss**: Automatic exit at predefined loss levels
- **Take Profit**: Lock in profits at target levels
- **Maximum Drawdown**: Portfolio-level risk limits
- **Position Limits**: Maximum number of active pairs
- **Correlation Limits**: Avoid over-concentration

### Performance Monitoring
- **Real-time PnL**: Track profit/loss for all positions
- **Win Rate**: Percentage of profitable trades
- **Sharpe Ratio**: Risk-adjusted returns
- **Maximum Drawdown**: Worst peak-to-trough decline
- **Average Holding Period**: Trade duration statistics

## Advanced Features

### Volume Weighting
All indicators support volume weighting using the methodology:
```python
vw_indicator = (price * volume).ewm(span=period).mean() / volume.ewm(span=period).mean()
```

### Pattern Confirmation
Candlestick patterns can be used to confirm technical indicator signals:
- **Volume Confirmation**: Patterns with above-average volume
- **Trend Context**: Patterns interpreted based on current trend
- **Signal Consensus**: Multiple patterns supporting same direction

### Multi-Timeframe Analysis
- **Primary Timeframe**: Main trading signals
- **Higher Timeframe**: Trend confirmation
- **Lower Timeframe**: Precise entry/exit timing

## Recommendations for Improvement

### 1. Enhanced Data Sources
- **Real-time Data**: Integrate with professional data providers
- **Alternative Data**: News sentiment, social media, earnings estimates
- **Fundamental Data**: Financial ratios, earnings, cash flow metrics

### 2. Advanced Statistical Methods
- **Kalman Filtering**: Dynamic hedge ratios
- **GARCH Models**: Time-varying volatility
- **Copula Models**: Non-linear dependency structures
- **Machine Learning**: Pattern recognition and signal generation

### 3. Risk Management Enhancements
- **Dynamic Hedging**: Continuous hedge ratio adjustments
- **Regime Detection**: Adapt strategies to market conditions
- **Stress Testing**: Monte Carlo simulations
- **Correlation Monitoring**: Real-time correlation tracking

### 4. Execution Improvements
- **Smart Order Routing**: Optimize execution across venues
- **Transaction Cost Analysis**: Minimize market impact
- **Slippage Modeling**: Realistic backtesting assumptions
- **Latency Optimization**: High-frequency execution capabilities

### 5. Portfolio Optimization
- **Multi-Pair Optimization**: Portfolio-level risk management
- **Sector Diversification**: Balanced exposure across sectors
- **Currency Hedging**: International pairs currency risk
- **Leverage Management**: Optimal leverage utilization

### 6. Performance Analytics
- **Attribution Analysis**: Source of returns breakdown
- **Regime Analysis**: Performance across market conditions
- **Benchmark Comparison**: Relative performance metrics
- **Risk Decomposition**: Factor-based risk analysis

### 7. Technology Enhancements
- **GPU Acceleration**: Parallel computation for indicators
- **Real-time Streaming**: Low-latency data processing
- **Cloud Deployment**: Scalable infrastructure
- **API Integration**: Seamless broker connectivity

## Integration with NautilusTrader

This module is designed to integrate seamlessly with the NautilusTrader engine:

```python
# Example integration
from nautilus_trader.indicators.base import Indicator
from pairs_trading_indicators import PairsTradingIndicators

class PairsIndicatorAdapter(Indicator):
    """Adapter for NautilusTrader integration."""
    
    def __init__(self, pair_symbols, config):
        super().__init__()
        self.pairs_indicators = PairsTradingIndicators()
        self.pair_symbols = pair_symbols
        self.config = config
    
    def handle_bar(self, bar):
        # Process incoming bar data
        # Calculate pairs indicators
        # Generate signals
        pass
```

## Testing and Validation

The module includes comprehensive testing functions:

```python
# Run all tests
python pairs_trading_indicators.py
python pairs_candlestick_patterns.py
python pairs_trading_strategies.py
```

Each module includes:
- **Unit Tests**: Individual function validation
- **Integration Tests**: End-to-end workflow testing
- **Performance Tests**: Computational efficiency validation
- **Backtesting**: Historical performance validation

## Dependencies

- **NumPy**: Numerical computations
- **Pandas**: Data manipulation and analysis
- **SciPy**: Statistical functions (optional)
- **TA-Lib**: Technical analysis library (optional)
- **Matplotlib**: Visualization (optional)
- **NautilusTrader**: Trading engine integration

## License

This module is part of the Algorithmic Trading System and follows the same licensing terms.

## Contributing

Contributions are welcome! Please follow the project's coding standards and include appropriate tests for new features.

## Support

For questions, issues, or feature requests, please refer to the main project documentation or create an issue in the project repository.