# Custom Volume-Weighted Technical Indicators Specification

## Overview

This document provides the comprehensive specification for custom volume-weighted technical indicators integrated into the Algorithmic Trading System. These indicators enhance traditional technical analysis by incorporating trading volume as a weighting factor, providing more accurate signals for multi-asset trading strategies across stocks, ETFs, futures, options, forex, commodities, and cryptocurrencies.

## Implementation Framework

### Primary Libraries
- **TA-Lib/ta-lib-python**: Primary wrapper for core technical analysis functions
- **Bukosabino/ta**: Secondary wrapper for additional indicator support
- **NumPy**: Efficient volume-weighted computation engine
- **Integration Target**: Direct integration into NautilusTrader strategy engine

### Core Principles
1. **Volume Weighting**: All indicators incorporate trading volume as a weighting factor
2. **Multi-Asset Support**: Compatible across all supported asset classes
3. **Real-Time Processing**: Live calculation capability for active trading
4. **Performance Optimization**: NumPy vectorization for efficient calculations
5. **Accuracy Verification**: Historical data validation with comprehensive unit testing

---

## Volume-Weighted Moving Averages

### Entry Signal Indicators
- **55 Day VW SMA of Open**: Long-term entry signal for trend following
- **34 Day VW SMA of Open**: Medium-term entry signal for momentum strategies  
- **13 Day VW SMA of Open**: Short-term entry signal for active trading
- **13 Day VW EMA of Open**: Exponentially weighted entry signal with recent bias

### Exit Signal Indicators  
- **13 Day VW SMA of High**: Exit signal based on volume-weighted highs
- **13 Day VW SMA of Low**: Exit signal based on volume-weighted lows
- **5 Day VW SMA of High**: Short-term exit signal for quick profits
- **5 Day VW SMA of Low**: Short-term exit signal for stop-loss management

### Trend Detection
- **5 Day VW EMA of HLC Average**: Trend finder using High-Low-Close average
  - **Formula**: VW_EMA = Σ(HLC_avg × Volume) / Σ(Volume) with exponential decay
  - **Usage**: Identify short-term trend changes with volume confirmation

---

## Volume-Weighted Momentum & Oscillators

### MACD Family
- **VW MACD of HLC Average (12, 26, 9)**: Volume-weighted MACD with standard parameters
  - **Fast Line**: 12-day VW EMA of HLC
  - **Slow Line**: 26-day VW EMA of HLC  
  - **Signal Line**: 9-day VW EMA of MACD line
- **VW MACD Histogram of HLC Average**: Difference between MACD line and signal line
  - **Formula**: Histogram = VW_MACD - VW_Signal_Line
  - **Usage**: Momentum acceleration/deceleration identification

### Money Flow Indicators
- **14 Day VW MFI of HLC Average**: Volume-weighted Money Flow Index
  - **Calculation**: Incorporates typical price, volume, and price direction
  - **Range**: 0-100 (oversold <20, overbought >80)
- **34 Day VW SMA of MFI(14) of HLC Average**: Long-term entry signal
- **21 Day VW SMA of MFI(14) of HLC Average**: Medium-term exit signal

---

## Risk Management & Volatility Indicators

### Average True Range (ATR) Calculations

#### Position Sizing Components
- **21 Day VW ATR for Positional Trades [N]**: Market normalization unit
  - **Usage**: Base unit for position sizing calculations
  - **Formula**: VW_ATR = Σ(TR × Volume) / Σ(Volume) over 21 periods
- **8 Day VW ATR for Intraday Trades [N]**: Short-term volatility measure
  - **Usage**: Intraday position sizing and risk management

#### Currency-Based Risk Calculations
- **Rupee Volatility/Risk [N × Lot Size]**: For Indian exchanges (NSE, BSE)
- **Dollar Volatility/Risk [N × Lot Size]**: For US exchanges (NYSE, NASDAQ)  
- **Pound Sterling Volatility/Risk [N × Lot Size]**: For London Stock Exchange (LSE)

#### Contract Risk Units
- **Contract Risk (Units) [2N]**: For positional trades
  - **Calculation**: 2 × ATR × Lot Size
  - **Usage**: Maximum risk per position for swing trading
- **Contract Risk (Units) [0.75N]**: For intraday trades
  - **Calculation**: 0.75 × ATR × Lot Size
  - **Usage**: Reduced risk for day trading strategies

#### Position Sizing Calculations
- **Max. Lots Calculation**: [Available Capital / Contract Risk]
  - **Formula**: Floor(Available_Capital / (ATR × Lot_Size × Risk_Multiplier))
  - **Risk_Multiplier**: 2.0 for positional, 0.75 for intraday

### Normalized Volatility Measures

#### ATR Percentage (Normalized ATR)
- **21 Day Average True Range Percent**: (ATR/Close) × 100
- **8 Day Average True Range Percent**: Short-term normalized volatility

#### Usage Guidelines for ATR vs ATRP
**Use ATRP (Normalized ATR) for**:
- Cross-security comparison and screening
- Strategy filtering based on volatility regime
- Long-term volatility pattern analysis
- Seasonality studies

**Use Traditional ATR for**:
- Position sizing calculations
- Stop-loss distance determination  
- Profit target setting
- Risk budget allocation

---

## Market Strength & Direction Indicators

### Turtle Trading Strength/Weakness (Curtis Faith Methodology)

#### Strength Calculation Formula
```
Strength = [LTP - Avg.HLC(N)] / ATR(N)
```

#### Time Frame Variants
- **21 Day Positional Strength**: `[LTP - Avg.HLC(21)] / ATR(21)`
  - **Usage**: Long-term trend strength for position trading
  - **Interpretation**: Highest values = strongest markets, lowest = weakest
- **8 Day Intraday Strength**: `[LTP - Avg.HLC(8)] / ATR(8)`
  - **Usage**: Short-term momentum for day trading
  - **Ranking**: Compare across asset universe for relative strength

#### Market Selection Logic
- **Buy Strategy**: Select markets with highest strength values
- **Sell Strategy**: Select markets with lowest strength values
- **Normalization**: ATR division enables cross-market comparison

### Market Regime Detection

#### Choppy Market Index
- **21 Day Choppy Market Index**: Long-term trend vs. range identification
  - **Calculation**: Measures price efficiency vs. total movement
  - **Formula**: CMI = 100 × (Close - Close[N]) / (Sum of daily ranges over N periods)
- **8 Day Choppy Market Index**: Short-term market regime detection
  - **Threshold**: CMI > 50 = Trending, CMI < 50 = Choppy

#### Market Mode Classification
- **21 Day Market Mode**: Trending vs. Choppy classification
- **8 Day Market Mode**: Short-term regime identification
- **Usage**: Adapt strategy selection based on market environment

#### Directional Bias Indicators
- **Buy Easier Day**: Conditions favoring long positions
  - **Calculation**: Based on volume, volatility, and price action patterns
- **Sell Easier Day**: Conditions favoring short positions
  - **Implementation**: Multi-factor model considering market microstructure

---

## Statistical & Correlation Measures

### Market Relationship Indicators
- **Beta vis-à-vis Market Index**: Systematic risk measurement
  - **Calculation**: Covariance(Asset, Market) / Variance(Market)
  - **Usage**: Portfolio risk assessment and hedging decisions
- **Auto Correlation**: Price series self-correlation for trend persistence
  - **Lag Periods**: 1, 5, 10, 21 days for different time horizons
  - **Usage**: Trend continuation probability assessment

### Volatility Measurements
- **Historical Annual Volatility**: Long-term volatility using daily returns
  - **Formula**: StdDev(Daily_Returns) × √252
  - **Usage**: Risk budgeting and portfolio allocation
- **Intraday Annual Volatility**: Short-term volatility patterns
  - **Calculation**: Using intraday price ranges scaled to annual terms
  - **Usage**: Intraday strategy calibration

---

## Momentum & Change Indicators

### Percentage Change Series
- **8 Day SMA Average % Change**: Short-term momentum measurement
  - **Calculation**: SMA of daily percentage changes over 8 periods
  - **Usage**: Short-term trend acceleration detection
- **13 Day SMA Average % Change**: Medium-term momentum
  - **Usage**: Intermediate trend strength assessment  
- **21 Day SMA Average % Change**: Long-term momentum
  - **Usage**: Primary trend confirmation

### Opening Range Breakout (ORB)
- **High Low Range Average for ORB**: Opening range volatility measurement
  - **Calculation**: Average of (High - Low) during opening hour
  - **Usage**: Breakout strategy calibration and position sizing

---

## Implementation Requirements

### Technical Specifications

#### Performance Requirements
- **Real-Time Calculation**: <10ms latency for live indicator updates
- **Historical Calculation**: Process 5+ years of data in <60 seconds
- **Memory Efficiency**: <1GB RAM for 10,000 symbol universe
- **CPU Optimization**: Utilize NumPy vectorization for 10x speed improvement

#### Integration Requirements
- **NautilusTrader Integration**: Direct embedding in strategy execution engine
- **Event-Driven Updates**: Kafka-based real-time indicator updates
- **Multi-Asset Support**: Uniform interface across all asset classes
- **API Exposure**: RESTful endpoints for external strategy access

#### Data Requirements
- **Volume Data**: Tick-by-tick or minute-level volume data required
- **Price Data**: OHLC data with millisecond timestamps
- **Corporate Actions**: Dividend and split adjustments for historical accuracy
- **Market Hours**: Exchange-specific trading session handling

### Quality Assurance

#### Testing Framework
- **Unit Tests**: Individual indicator accuracy validation
- **Integration Tests**: End-to-end strategy pipeline testing
- **Performance Tests**: Latency and throughput benchmarking
- **Regression Tests**: Historical backtest result consistency

#### Validation Methodology
- **Known Value Testing**: Compare against manually calculated examples
- **Cross-Platform Validation**: Verify against established platforms (Bloomberg, Reuters)
- **Edge Case Testing**: Handle missing data, market holidays, extreme volatility
- **Precision Testing**: Maintain 6-decimal precision for all calculations

### Documentation Requirements

#### Code Documentation
- **Function Docstrings**: Complete parameter and return value descriptions
- **Mathematical Formulas**: LaTeX-formatted equations for all calculations
- **Usage Examples**: Code snippets for each indicator implementation
- **Performance Notes**: Complexity analysis and optimization recommendations

#### User Documentation
- **Indicator Reference**: Complete catalog with descriptions and use cases
- **Strategy Examples**: Sample strategies using custom indicators
- **Best Practices**: Guidelines for effective indicator combination
- **Troubleshooting**: Common issues and resolution procedures

---

## Deployment & Maintenance

### Continuous Integration
- **Automated Testing**: Run full test suite on every commit
- **Performance Monitoring**: Track calculation latency in production
- **Alert System**: Notify on indicator calculation failures
- **Version Control**: Semantic versioning for indicator library updates

### Production Monitoring
- **Error Tracking**: Log and alert on calculation exceptions
- **Performance Metrics**: Monitor calculation times and resource usage
- **Data Quality**: Validate input data completeness and accuracy
- **System Health**: Overall indicator service availability monitoring

### Scaling Considerations
- **Horizontal Scaling**: Distribute calculations across multiple nodes
- **Caching Strategy**: Cache frequently requested historical calculations
- **Load Balancing**: Distribute indicator requests across compute resources
- **Database Optimization**: Efficient storage and retrieval of indicator values

---

## Conclusion

This comprehensive specification provides the foundation for implementing enterprise-grade volume-weighted technical indicators that enhance the Algorithmic Trading System's analytical capabilities. The indicators combine traditional technical analysis with volume weighting to provide more accurate signals across diverse market conditions and asset classes.

The implementation will integrate seamlessly with the existing NautilusTrader engine and support the system's multi-asset, high-performance trading requirements while maintaining the flexibility needed for custom strategy development.