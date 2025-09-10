# Technical Indicators Reference Guide

**Version:** 5.0.0 (Consolidated & Optimized)  
**Author:** Vincent S. Pereira  
**Last Updated:** January 2024

## Overview

This comprehensive reference guide covers all technical indicators and candlestick patterns available in the consolidated Nautilus Trader indicators package. Each indicator has been optimized for performance, supports volume weighting, and includes institutional-grade features for professional trading applications.

## Package Structure

The indicators package has been completely refactored to eliminate redundancy and improve maintainability:

- **Core Infrastructure:** `core_base.py` - Base classes, decorators, utilities
- **Trend Indicators:** `trend_indicators.py` - Moving averages and trend analysis
- **Momentum Indicators:** `momentum_indicators.py` - Oscillators and momentum analysis  
- **Volatility Indicators:** `volatility_indicators.py` - Volatility and range analysis
- **Volume Indicators:** `volume_indicators.py` - Volume and money flow analysis
- **Pattern Recognition:** `pattern_single.py` - Candlestick pattern detection

---

# TREND INDICATORS

## Simple Moving Average (SMA)

**Category:** Trend Following  
**File Location:** `trend_indicators.py`  
**Class Name:** `SMA`

### Core Functionality
Calculates the arithmetic mean of prices over a specified period, with optional volume weighting for institutional analysis.

### Interpretation & Trading Signals

**Bullish Signals:**
- Price crosses above SMA line
- SMA slope is positive (upward trending)
- Price consistently stays above SMA with increasing volume

**Bearish Signals:**
- Price crosses below SMA line  
- SMA slope is negative (downward trending)
- Price consistently stays below SMA with increasing volume

### Pros & Cons

**Pros:**
- Simple and reliable trend identification
- Excellent for identifying major trend changes
- Works well in trending markets
- Volume weighting adds institutional insight

**Cons:**
- Lagging indicator - signals come after trend has started
- Generates false signals in sideways markets
- Slower response to price changes compared to EMA

### Optimal Usage & Maximising Benefit

**Recommended Market Conditions:**
- Strong trending markets (up or down)
- Medium to long-term trading strategies
- Use with volume confirmation for better signals

**Combination Strategies:**
- Combine with RSI to avoid overbought/oversold entries
- Use multiple SMA periods (20, 50, 200) for trend hierarchy
- Pair with volume indicators for confirmation

**Parameter Optimisation:**
- **Short-term trading:** 10-20 periods
- **Medium-term trading:** 20-50 periods  
- **Long-term investing:** 50-200 periods
- **Volume weighting:** Enable for institutional analysis

### Implementation Reference

```python
from nautilus_trader_engine.indicators import create_sma

# Basic SMA
sma = create_sma(period=20)

# Volume-weighted SMA for institutional analysis
vw_sma = create_sma(period=20, volume_weighted=True)

# HFT-optimized SMA
hft_sma = create_sma(period=20, hft_mode=True, performance_monitoring=True)
```

**Standard Parameters:**
- `period`: 20 (default), range 5-200
- `volume_weighted`: False (default), True for institutional analysis
- `hft_mode`: False (default), True for high-frequency trading
- `adaptive`: False (default), True for dynamic period adjustment

---

## Exponential Moving Average (EMA)

**Category:** Trend Following  
**File Location:** `trend_indicators.py`  
**Class Name:** `EMA`

### Core Functionality
Calculates exponentially weighted moving average giving more weight to recent prices, with adaptive alpha based on volume for institutional analysis.

### Interpretation & Trading Signals

**Bullish Signals:**
- Price crosses above EMA line
- EMA momentum is positive and increasing
- Strong volume confirmation on breakout above EMA

**Bearish Signals:**
- Price crosses below EMA line
- EMA momentum is negative and decreasing  
- Strong volume confirmation on breakdown below EMA

### Pros & Cons

**Pros:**
- More responsive to recent price changes than SMA
- Better for short-term trading strategies
- Adaptive alpha provides volume-based sensitivity
- Excellent momentum indicator

**Cons:**
- More prone to false signals in choppy markets
- Can be too sensitive in volatile conditions
- Requires careful parameter tuning

### Optimal Usage & Maximising Benefit

**Recommended Market Conditions:**
- Trending markets with moderate volatility
- Short to medium-term trading strategies
- Markets with consistent volume patterns

**Combination Strategies:**
- Use EMA crossovers (fast EMA crossing slow EMA)
- Combine with MACD for momentum confirmation
- Pair with volume indicators for institutional flow detection

**Parameter Optimisation:**
- **Scalping:** 5-12 periods
- **Day trading:** 12-26 periods
- **Swing trading:** 26-50 periods
- **Volume weighting:** Enable during high institutional activity

### Implementation Reference

```python
from nautilus_trader_engine.indicators import create_ema

# Standard EMA
ema = create_ema(period=20)

# Volume-weighted EMA with adaptive alpha
vw_ema = create_ema(period=20, volume_weighted=True, adaptive=True)
```

---

# MOMENTUM INDICATORS

## Relative Strength Index (RSI)

**Category:** Momentum Oscillator  
**File Location:** `momentum_indicators.py`  
**Class Name:** `RSI`

### Core Functionality
Measures the speed and magnitude of price changes, oscillating between 0 and 100 to identify overbought and oversold conditions.

### Interpretation & Trading Signals

**Bullish Signals:**
- RSI crosses above 30 from oversold territory
- Bullish divergence: price makes lower lows while RSI makes higher lows
- RSI breaks above 50 indicating momentum shift to bullish

**Bearish Signals:**
- RSI crosses below 70 from overbought territory
- Bearish divergence: price makes higher highs while RSI makes lower highs
- RSI breaks below 50 indicating momentum shift to bearish

### Pros & Cons

**Pros:**
- Excellent for identifying overbought/oversold conditions
- Reliable divergence signals for trend reversals
- Works well in ranging markets
- Volume weighting adds institutional insight

**Cons:**
- Can remain in extreme territories during strong trends
- False signals in trending markets
- Requires confirmation from other indicators

### Optimal Usage & Maximising Benefit

**Recommended Market Conditions:**
- Ranging or sideways markets
- Markets with regular oscillations
- When combined with trend-following indicators

**Combination Strategies:**
- Use with moving averages to confirm trend direction
- Combine with volume indicators for signal confirmation
- Look for divergences with price action

**Parameter Optimisation:**
- **Standard period:** 14 (most common)
- **Short-term trading:** 7-10 periods
- **Long-term analysis:** 21-25 periods
- **Overbought/Oversold levels:** Adjust based on market volatility

### Implementation Reference

```python
from nautilus_trader_engine.indicators import create_rsi

# Standard RSI
rsi = create_rsi(period=14)

# Volume-weighted RSI with adaptive thresholds
vw_rsi = create_rsi(period=14, volume_weighted=True, adaptive=True)
```

---

# USAGE EXAMPLES

## Basic Indicator Usage

```python
from nautilus_trader_engine.indicators import *
from datetime import datetime

# Create indicators
sma = create_sma(period=20, volume_weighted=True)
rsi = create_rsi(period=14, adaptive=True)

# Calculate indicator values
price = 100.0
volume = 10000
timestamp = datetime.now()

sma_result = sma.calculate(price, volume, timestamp)
rsi_result = rsi.calculate(price, volume, timestamp)

# Access results
if sma_result:
    print(f"SMA: {sma_result.value:.2f}")
    print(f"Signal: {sma_result.signal.value}")
    print(f"Confidence: {sma_result.confidence:.2f}")
```

## Creating Indicator Suites

```python
# Create comprehensive indicator suite
suite = create_indicator_suite(
    trend=True,
    momentum=True,
    volatility=True,
    volume=True,
    patterns=True,
    volume_weighted=True
)

# Validate indicators
validation = validate_consolidated_indicators()
print(f"Available modules: {validation['total_available']}/6")
```

---

# BEST PRACTICES

## General Guidelines

1. **Always use volume confirmation** when available for better signal quality
2. **Combine multiple indicators** from different categories for robust analysis
3. **Consider market context** - trending vs ranging markets require different approaches
4. **Use appropriate timeframes** for your trading strategy
5. **Backtest thoroughly** before live implementation

## Performance Optimization

1. **Enable HFT mode** for high-frequency applications
2. **Use batch processing** for large datasets
3. **Monitor memory usage** in long-running applications
4. **Set appropriate memory limits** to prevent memory leaks
5. **Use performance monitoring** to identify bottlenecks

---

**End of Reference Guide**

This comprehensive guide covers all consolidated indicators in the Nautilus Trader package. Each indicator has been optimized for performance while maintaining accuracy and providing institutional-grade features for professional trading applications.