# Technical Indicators Reference Guide

**Institutional-Grade Technical Analysis Library**  
**Version:** 6.0.0 (Enhanced with 5-Pillar Architecture)  
**Author:** Vincent S. Pereira  
**Last Updated:** January 2025

---

## Table of Contents

1. [Overview](#overview)
2. [5-Pillar Architecture](#5-pillar-architecture)
3. [Trend Indicators](#trend-indicators)
4. [Momentum Indicators](#momentum-indicators)
5. [Volatility Indicators](#volatility-indicators)
6. [Volume Indicators](#volume-indicators)
7. [Candlestick Patterns](#candlestick-patterns)
8. [Enhanced Features](#enhanced-features)
9. [Usage Examples](#usage-examples)
10. [API Reference](#api-reference)

---

## Overview

This library provides institutional-grade technical indicators with advanced features including volume weighting, smart money analysis, market regime adaptation, multi-timeframe convergence, and automated risk management. All indicators are built on the unified `AugmentedIndicator` base class that implements the 5-pillar architecture.

### Key Features
- **80+ Technical Indicators** across 6 categories
- **75+ Candlestick Patterns** with volume confirmation
- **Volume-Weighted Calculations** for institutional analysis
- **Smart Money Flow Detection** and order flow analysis
- **Market Regime Adaptation** with dynamic parameter adjustment
- **Multi-Timeframe Convergence** analysis
- **Automated Risk Management** with position sizing and stop-loss calculation
- **Real-Time Performance Optimization** for HFT environments

---

## 5-Pillar Architecture

All indicators implement the institutional-grade 5-pillar architecture:

### Pillar 1: Volume Integration & Confirmation
- **Volume Confirmation Scoring** (0-1 scale)
- **Institutional Volume Detection** (2+ standard deviations)
- **Volume-Price Relationship Analysis**
- **Volume Profile Tracking** (accumulation/distribution)
- **Volume Quality Assessment**

### Pillar 2: Market Regime Adaptation
- **Regime Detection Engine** with 7 market states
- **Dynamic Parameter Adjustment** based on regime
- **Volatility Regime Classification** (low/normal/high/extreme)
- **Trend Regime Analysis** (trending/sideways)
- **Regime Confidence Scoring**

### Pillar 3: Multi-Timeframe Convergence
- **Signal Convergence Analysis** across timeframes
- **Composite Signal Generation**
- **Timeframe Weight Optimization**
- **Signal Stack Ensemble Modeling**
- **Convergence Strength Measurement**

### Pillar 4: Smart Money & Microstructure Analysis
- **Institutional Flow Detection**
- **Order Flow Imbalance Analysis**
- **Large Order Detection** (volume spikes)
- **Institutional Bias Assessment** (-1 to +1 scale)
- **Smart Money Metrics Tracking**

### Pillar 5: Automated Risk Management Factory
- **7 Position Sizing Methods** (Kelly, Fixed Fractional, etc.)
- **7 Stop-Loss Calculation Methods** (ATR, Volatility-based, etc.)
- **Risk-Adjusted Signal Generation**
- **Dynamic Position Sizing** based on regime and confidence
- **Automated Stop-Loss/Take-Profit Calculation**

---

## Trend Indicators

### Simple Moving Average (SMA)
**File:** `trend_indicators.py`  
**Class:** `SMA`  
**Purpose:** Smooth price data to identify trend direction

**Parameters:**
- `period` (int): Lookback period (default: 20)
- `enable_volume_weighting` (bool): Enable volume weighting (default: True)
- `enable_regime_adaptation` (bool): Enable regime-based adaptation (default: True)

**Enhanced Features:**
- Volume-weighted calculation for institutional bias
- Adaptive period adjustment based on market regime
- Multi-timeframe convergence analysis
- Smart money flow confirmation

**Usage:**
```python
from nautilus_trader_engine.indicators import SMA, IndicatorConfig

config = IndicatorConfig(
    period=20,
    enable_volume_weighting=True,
    enable_regime_adaptation=True
)
sma = SMA(config)
result = sma.update(price=100.0, volume=1000)
```

### Exponential Moving Average (EMA)
**File:** `trend_indicators.py`  
**Class:** `EMA`  
**Purpose:** Exponentially weighted moving average with greater sensitivity to recent prices

**Parameters:**
- `period` (int): Lookback period (default: 12)
- `alpha` (float): Smoothing factor (default: auto-calculated)
- `enable_volume_weighting` (bool): Enable volume weighting (default: True)

**Enhanced Features:**
- Volume-weighted exponential smoothing
- Adaptive alpha adjustment based on volatility regime
- Institutional flow bias integration
- Multi-timeframe EMA convergence

### Volume Weighted Moving Average (VWMA)
**File:** `trend_indicators.py`  
**Class:** `VWMA`  
**Purpose:** Moving average weighted by volume for institutional analysis

**Parameters:**
- `period` (int): Lookback period (default: 20)
- `institutional_threshold` (float): Volume threshold for institutional detection (default: 2.0)

**Enhanced Features:**
- Native volume weighting with institutional bias
- Large order detection and weighting
- Smart money flow integration
- Volume quality assessment

### Hull Moving Average (HMA)
**File:** `trend_indicators.py`  
**Class:** `HMA`  
**Purpose:** Low-lag moving average with reduced noise

**Parameters:**
- `period` (int): Lookback period (default: 16)
- `enable_volume_weighting` (bool): Enable volume weighting (default: True)

**Enhanced Features:**
- Volume-weighted Hull calculation
- Regime-adaptive smoothing
- Reduced lag with institutional flow confirmation

---

## Momentum Indicators

### Relative Strength Index (RSI)
**File:** `momentum_indicators.py`  
**Class:** `RSI`  
**Purpose:** Momentum oscillator measuring speed and change of price movements

**Parameters:**
- `period` (int): Lookback period (default: 14)
- `overbought_threshold` (float): Overbought level (default: 70)
- `oversold_threshold` (float): Oversold level (default: 30)
- `enable_volume_weighting` (bool): Enable volume weighting (default: True)

**Enhanced Features:**
- Volume-weighted RSI calculation
- Adaptive thresholds based on market regime
- Institutional flow confirmation
- Multi-timeframe RSI divergence analysis
- Smart money bias integration

**Signal Generation:**
- **Strong Buy:** RSI < 20 with volume confirmation
- **Buy:** RSI < 30 with institutional flow support
- **Sell:** RSI > 70 with volume confirmation
- **Strong Sell:** RSI > 80 with institutional distribution

### MACD (Moving Average Convergence Divergence)
**File:** `momentum_indicators.py`  
**Class:** `MACD`  
**Purpose:** Trend-following momentum indicator

**Parameters:**
- `fast_period` (int): Fast EMA period (default: 12)
- `slow_period` (int): Slow EMA period (default: 26)
- `signal_period` (int): Signal line EMA period (default: 9)
- `enable_volume_weighting` (bool): Enable volume weighting (default: True)

**Enhanced Features:**
- Volume-weighted MACD calculation
- Institutional flow histogram
- Regime-adaptive signal line
- Multi-timeframe MACD convergence
- Smart money divergence detection

### Stochastic Oscillator
**File:** `momentum_indicators.py`  
**Class:** `StochasticOscillator`  
**Purpose:** Momentum indicator comparing closing price to price range

**Parameters:**
- `k_period` (int): %K period (default: 14)
- `d_period` (int): %D smoothing period (default: 3)
- `enable_volume_weighting` (bool): Enable volume weighting (default: True)

**Enhanced Features:**
- Volume-weighted stochastic calculation
- Institutional flow confirmation
- Adaptive smoothing based on volatility regime
- Multi-timeframe stochastic analysis

### Williams %R
**File:** `momentum_indicators.py`  
**Class:** `WilliamsR`  
**Purpose:** Momentum indicator measuring overbought/oversold conditions

**Parameters:**
- `period` (int): Lookback period (default: 14)
- `enable_volume_weighting` (bool): Enable volume weighting (default: True)

**Enhanced Features:**
- Volume-weighted Williams %R
- Smart money flow confirmation
- Regime-adaptive thresholds
- Institutional bias integration

---

## Volatility Indicators

### Bollinger Bands
**File:** `volatility_indicators.py`  
**Class:** `BollingerBands`  
**Purpose:** Volatility bands around moving average

**Parameters:**
- `period` (int): Moving average period (default: 20)
- `std_dev` (float): Standard deviation multiplier (default: 2.0)
- `enable_volume_weighting` (bool): Enable volume weighting (default: True)

**Enhanced Features:**
- Volume-weighted center line and bands
- Adaptive band width based on volatility regime
- Institutional squeeze detection
- Multi-timeframe band analysis
- Smart money breakout confirmation

### Average True Range (ATR)
**File:** `volatility_indicators.py`  
**Class:** `ATR`  
**Purpose:** Measure of market volatility

**Parameters:**
- `period` (int): Lookback period (default: 14)
- `enable_volume_weighting` (bool): Enable volume weighting (default: True)

**Enhanced Features:**
- Volume-weighted ATR calculation
- Regime-based volatility classification
- Institutional activity impact on volatility
- Multi-timeframe ATR convergence

### Keltner Channels
**File:** `volatility_indicators.py`  
**Class:** `KeltnerChannels`  
**Purpose:** Volatility-based trading channels

**Parameters:**
- `period` (int): EMA period (default: 20)
- `atr_period` (int): ATR period (default: 10)
- `multiplier` (float): ATR multiplier (default: 2.0)

**Enhanced Features:**
- Volume-weighted EMA center line
- Adaptive channel width
- Institutional breakout detection
- Smart money flow confirmation

### Standard Deviation
**File:** `volatility_indicators.py`  
**Class:** `StandardDeviation`  
**Purpose:** Statistical measure of price volatility

**Parameters:**
- `period` (int): Lookback period (default: 20)
- `enable_volume_weighting` (bool): Enable volume weighting (default: True)

**Enhanced Features:**
- Volume-weighted standard deviation
- Regime-based volatility classification
- Institutional impact measurement

---

## Volume Indicators

### Volume Weighted Average Price (VWAP)
**File:** `volume_indicators.py`  
**Class:** `VWAP`  
**Purpose:** Average price weighted by volume

**Parameters:**
- `reset_period` (str): Reset frequency ('daily', 'weekly', 'monthly')
- `enable_institutional_analysis` (bool): Enable institutional flow analysis (default: True)

**Enhanced Features:**
- Institutional VWAP deviation analysis
- Smart money flow tracking
- Multi-timeframe VWAP levels
- Volume profile integration

### On-Balance Volume (OBV)
**File:** `volume_indicators.py`  
**Class:** `OBV`  
**Purpose:** Momentum indicator using volume flow

**Parameters:**
- `enable_smart_money_analysis` (bool): Enable smart money detection (default: True)

**Enhanced Features:**
- Institutional flow detection
- Smart money accumulation/distribution
- Multi-timeframe OBV divergence
- Volume quality assessment

### Money Flow Index (MFI)
**File:** `volume_indicators.py`  
**Class:** `MFI`  
**Purpose:** Volume-weighted RSI

**Parameters:**
- `period` (int): Lookback period (default: 14)
- `overbought_threshold` (float): Overbought level (default: 80)
- `oversold_threshold` (float): Oversold level (default: 20)

**Enhanced Features:**
- Enhanced money flow calculation
- Institutional flow bias
- Adaptive thresholds
- Smart money confirmation

### Accumulation/Distribution Line (A/D Line)
**File:** `volume_indicators.py`  
**Class:** `AccumulationDistribution`  
**Purpose:** Volume-based accumulation/distribution indicator

**Parameters:**
- `enable_institutional_analysis` (bool): Enable institutional analysis (default: True)

**Enhanced Features:**
- Institutional accumulation detection
- Smart money flow analysis
- Volume quality weighting
- Multi-timeframe A/D analysis

---

## Candlestick Patterns

### Single Candlestick Patterns
**File:** `pattern_single.py`  
**Class:** `SingleCandlestickPatterns`

#### Doji Patterns
1. **Standard Doji**
   - **Recognition:** Open ≈ Close (within 0.1% of range)
   - **Volume Confirmation:** Above-average volume increases reliability
   - **Institutional Features:** Large volume doji indicates institutional indecision

2. **Long Legged Doji**
   - **Recognition:** Long upper and lower shadows, small body
   - **Volume Confirmation:** High volume confirms market uncertainty
   - **Smart Money Analysis:** Institutional testing of support/resistance levels

3. **Dragonfly Doji**
   - **Recognition:** Long lower shadow, no upper shadow, small body
   - **Volume Confirmation:** High volume at lows indicates buying interest
   - **Institutional Features:** Smart money accumulation at support

4. **Gravestone Doji**
   - **Recognition:** Long upper shadow, no lower shadow, small body
   - **Volume Confirmation:** High volume at highs indicates selling pressure
   - **Institutional Features:** Smart money distribution at resistance

#### Hammer Patterns
5. **Hammer/Hanging Man**
   - **Recognition:** Small body, long lower shadow (2x body size)
   - **Volume Confirmation:** High volume increases reversal probability
   - **Position Context:** Hammer at lows (bullish), Hanging Man at highs (bearish)
   - **Institutional Features:** Large volume indicates institutional support/resistance

6. **Shooting Star/Inverted Hammer**
   - **Recognition:** Small body, long upper shadow (2x body size)
   - **Volume Confirmation:** High volume confirms reversal potential
   - **Institutional Features:** Smart money rejection of higher prices

#### Other Single Patterns
7. **Marubozu**
   - **Recognition:** No shadows, body spans entire range
   - **Volume Confirmation:** High volume confirms strong directional move
   - **Institutional Features:** Institutional conviction in direction

8. **Spinning Top**
   - **Recognition:** Small body with upper and lower shadows
   - **Volume Confirmation:** Low volume indicates indecision
   - **Institutional Features:** Lack of institutional participation

### Double Candlestick Patterns
**File:** `pattern_double.py`  
**Class:** `DoubleCandlestickPatterns`

#### Engulfing Patterns
1. **Bullish Engulfing**
   - **Recognition:** Large white body engulfs previous black body
   - **Volume Confirmation:** Volume spike on engulfing candle
   - **Institutional Features:** Smart money accumulation signal
   - **Multi-timeframe:** Stronger when confirmed across timeframes

2. **Bearish Engulfing**
   - **Recognition:** Large black body engulfs previous white body
   - **Volume Confirmation:** High volume confirms distribution
   - **Institutional Features:** Smart money selling pressure

#### Harami Patterns
3. **Bullish Harami**
   - **Recognition:** Small white body within previous large black body
   - **Volume Confirmation:** Decreasing volume on second candle
   - **Institutional Features:** Institutional buying at support

4. **Bearish Harami**
   - **Recognition:** Small black body within previous large white body
   - **Volume Confirmation:** Low volume indicates weakening momentum
   - **Institutional Features:** Institutional profit-taking

#### Piercing Patterns
5. **Piercing Line**
   - **Recognition:** White candle opens below previous close, closes above midpoint
   - **Volume Confirmation:** High volume on white candle
   - **Institutional Features:** Smart money bottom fishing

6. **Dark Cloud Cover**
   - **Recognition:** Black candle opens above previous close, closes below midpoint
   - **Volume Confirmation:** High volume confirms selling pressure
   - **Institutional Features:** Institutional distribution

7. **Tweezer Tops/Bottoms**
   - **Recognition:** Two candles with same high/low levels
   - **Volume Confirmation:** High volume on both candles
   - **Institutional Features:** Institutional support/resistance levels

### Triple Candlestick Patterns
**File:** `pattern_triple.py`  
**Class:** `TripleCandlestickPatterns`

#### Star Patterns
1. **Morning Star**
   - **Recognition:** Black candle, small body (star), white candle
   - **Volume Confirmation:** Increasing volume through pattern
   - **Institutional Features:** Smart money accumulation sequence
   - **Gap Requirements:** Gaps enhance pattern reliability

2. **Evening Star**
   - **Recognition:** White candle, small body (star), black candle
   - **Volume Confirmation:** High volume on final black candle
   - **Institutional Features:** Institutional distribution sequence

3. **Doji Star (Morning/Evening)**
   - **Recognition:** Star candle is a doji
   - **Volume Confirmation:** High volume on doji indicates indecision
   - **Institutional Features:** Institutional uncertainty at turning points

#### Soldier Patterns
4. **Three White Soldiers**
   - **Recognition:** Three consecutive white candles with higher closes
   - **Volume Confirmation:** Increasing volume confirms strength
   - **Institutional Features:** Sustained institutional buying
   - **Body Requirements:** Each body should be substantial

5. **Three Black Crows**
   - **Recognition:** Three consecutive black candles with lower closes
   - **Volume Confirmation:** High volume confirms selling pressure
   - **Institutional Features:** Institutional distribution campaign

6. **Advanced Patterns**
   - **Three Inside Up/Down:** Harami followed by confirmation
   - **Three Outside Up/Down:** Engulfing followed by confirmation
   - **Abandoned Baby:** Rare reversal pattern with gaps

---

## Enhanced Features

### Volume Confirmation Engine
**File:** `volume_confirmation.py`

**Components:**
- **Volume Confirmation Score** (0-1 scale)
- **Price-Volume Synchronization**
- **Volume Breakout Detection**
- **Volume Persistence Analysis**
- **Institutional Presence Scoring**
- **Volume Quality Assessment**

### Smart Money Analysis Engine
**File:** `smart_money_analysis.py`

**Components:**
- **Institutional Flow Detection**
- **Large Order Identification**
- **Order Flow Imbalance Analysis**
- **Smart Money Bias Calculation**
- **Institutional Activity Metrics**

### Regime Adaptation Engine
**File:** `regime_adaptation_engine.py`

**Components:**
- **Market Regime Detection** (7 states)
- **Volatility Regime Classification**
- **Trend Regime Analysis**
- **Parameter Adaptation Logic**
- **Regime Confidence Scoring**
- **Regime Transition Detection**

### Multi-Timeframe Engine
**File:** `multi_timeframe_engine.py`

**Components:**
- **Signal Convergence Analysis**
- **Composite Signal Generation**
- **Timeframe Weight Optimization**
- **Signal Stack Management**
- **Convergence Strength Measurement**

### Enhanced Risk Factory
**File:** `enhanced_risk_factory.py`

**Components:**
- **7 Position Sizing Methods**
- **7 Stop-Loss Calculation Methods**
- **Risk-Adjusted Signal Generation**
- **Dynamic Risk Assessment**
- **Portfolio Risk Management**

---

## Usage Examples

### Basic Indicator Usage
```python
from nautilus_trader_engine.indicators import RSI, IndicatorConfig
from datetime import datetime

# Create enhanced configuration
config = IndicatorConfig(
    period=14,
    enable_volume_weighting=True,
    enable_smart_money_analysis=True,
    enable_regime_adaptation=True,
    enable_multi_timeframe=True,
    enable_risk_management=True
)

# Initialize RSI with institutional features
rsi = RSI(config)

# Update with price and volume data
result = rsi.update(price=100.0, volume=1000, timestamp=datetime.now())

# Access enhanced metrics
print(f"RSI Value: {result.value}")
print(f"Volume Confirmation: {rsi.volume_confirmation_score}")
print(f"Smart Money Activity: {rsi.smart_money_metrics.institutional_activity}")
print(f"Market Regime: {rsi.current_regime}")
print(f"Risk Level: {rsi.risk_metrics.risk_level}")
print(f"Auto Stop Loss: {rsi.auto_stop_loss}")
print(f"Position Sizing Factor: {rsi.position_sizing_factor}")
```

### Multi-Timeframe Analysis
```python
from nautilus_trader_engine.indicators import MACD, IndicatorConfig

# Initialize MACD with multi-timeframe support
config = IndicatorConfig(enable_multi_timeframe=True)
macd = MACD(config)

# Add data from different timeframes
macd.update(price=100.0, volume=1000)  # Primary timeframe (1m)
macd.add_timeframe_data('5m', price=99.8, volume=5000)
macd.add_timeframe_data('15m', price=100.2, volume=15000)
macd.add_timeframe_data('1h', price=99.5, volume=60000)

# Analyze convergence
convergence = macd.timeframe_convergence
print(f"Timeframe Convergence: {convergence}")
```

### Pattern Recognition with Volume Confirmation
```python
from nautilus_trader_engine.indicators import ConsolidatedPatternDetector

# Initialize pattern detector
pattern_detector = ConsolidatedPatternDetector()

# Add OHLCV data
pattern_detector.add_candle(
    open_price=99.0,
    high_price=101.0,
    low_price=98.5,
    close_price=100.5,
    volume=2000
)

# Get detected patterns with institutional features
patterns = pattern_detector.get_current_patterns()
for pattern in patterns:
    print(f"Pattern: {pattern.name}")
    print(f"Strength: {pattern.strength}")
    print(f"Volume Confirmation: {pattern.volume_confirmation}")
    print(f"Institutional Bias: {pattern.institutional_bias}")
```

---

## API Reference

### Base Classes

#### AugmentedIndicator
**Base class for all institutional-grade indicators**

**Methods:**
- `update(price, volume, timestamp)` → `IndicatorResult`
- `add_timeframe_data(timeframe, price, volume, timestamp)` → `None`
- `get_signal()` → `IndicatorSignal`
- `get_risk_metrics()` → `RiskMetrics`
- `get_smart_money_metrics()` → `SmartMoneyMetrics`

**Properties:**
- `volume_confirmation_score` (float): Volume confirmation score (0-1)
- `current_regime` (MarketRegime): Current market regime
- `regime_confidence` (float): Regime confidence score (0-1)
- `smart_money_metrics` (SmartMoneyMetrics): Smart money analysis results
- `risk_metrics` (RiskMetrics): Risk management metrics
- `auto_stop_loss` (float): Calculated stop-loss level
- `auto_take_profit` (float): Calculated take-profit level
- `position_sizing_factor` (float): Position sizing multiplier

### Configuration Classes

#### IndicatorConfig
**Configuration class for indicator parameters**

**Parameters:**
- `period` (int): Primary lookback period
- `signal_threshold` (float): Signal generation threshold
- `enable_volume_weighting` (bool): Enable volume weighting
- `enable_smart_money_analysis` (bool): Enable smart money analysis
- `enable_regime_adaptation` (bool): Enable regime adaptation
- `enable_multi_timeframe` (bool): Enable multi-timeframe analysis
- `enable_risk_management` (bool): Enable risk management
- `enable_hft_optimizations` (bool): Enable HFT optimizations

### Result Classes

#### IndicatorResult
**Result class for indicator calculations**

**Properties:**
- `value` (float): Primary indicator value
- `timestamp` (datetime): Calculation timestamp
- `signal` (IndicatorSignal): Generated trading signal
- `metadata` (dict): Additional metrics and information

#### IndicatorSignal
**Enhanced trading signal with institutional features**

**Properties:**
- `signal_type` (SignalType): Signal classification
- `strength` (float): Signal strength (-1 to 1)
- `confidence` (float): Signal confidence (0-1)
- `volume_confirmation` (bool): Volume confirmation status
- `market_regime` (MarketRegime): Market regime context
- `smart_money_metrics` (SmartMoneyMetrics): Smart money analysis
- `risk_metrics` (RiskMetrics): Risk assessment
- `institutional_bias` (float): Institutional bias (-1 to 1)

---

## Performance Considerations

### HFT Optimizations
- **Memory Management:** Circular buffers with configurable limits
- **Batch Processing:** Vectorized calculations where possible
- **Thread Safety:** Lock-free operations for concurrent access
- **Garbage Collection:** Proactive memory cleanup
- **Performance Monitoring:** Built-in timing and profiling

### Memory Usage
- **Default Memory Limit:** 10,000 data points per indicator
- **Configurable Limits:** Adjustable via `IndicatorConfig.memory_limit`
- **Automatic Cleanup:** Old data automatically purged
- **Memory Efficient Decorators:** `@memory_efficient` for optimization

### Threading
- **Thread-Safe Operations:** All indicators support concurrent access
- **Thread Pool Execution:** Optional parallel processing
- **Lock Management:** Minimal locking for performance

---

## Error Handling

### Robust Calculation
- **Input Validation:** Automatic data validation and sanitization
- **Error Recovery:** Graceful handling of invalid data
- **Fallback Mechanisms:** Alternative calculations when primary methods fail
- **Logging:** Comprehensive error logging and debugging

### Exception Types
- `InvalidDataError`: Invalid input data
- `InsufficientDataError`: Not enough data for calculation
- `ConfigurationError`: Invalid configuration parameters
- `CalculationError`: Calculation-specific errors

---

## Contributing

When adding new indicators or patterns:

1. **Inherit from AugmentedIndicator** for full institutional features
2. **Implement all 5 pillars** of the architecture
3. **Add comprehensive tests** with volume and regime scenarios
4. **Update this documentation** with detailed descriptions
5. **Follow naming conventions** and code style guidelines
6. **Add performance benchmarks** for HFT compatibility

---

## License

This library is proprietary software developed for institutional trading applications.

---

**End of Reference Guide**