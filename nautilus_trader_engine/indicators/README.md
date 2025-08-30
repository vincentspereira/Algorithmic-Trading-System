# Enhanced Technical Indicators Library 📈

A comprehensive suite of **80+ technical indicators** and **25+ candlestick patterns** designed for professional algorithmic trading. This library provides both traditional indicators and innovative volume-weighted variants for enhanced market analysis.

## 🚀 Key Features

- **80+ Technical Indicators** across 5 categories
- **25+ Candlestick Patterns** with sophisticated recognition
- **Volume-Weighted Variants** for institutional-grade analysis
- **Real-time Signal Generation** with confidence scoring
- **Pattern Strength Analysis** with volume confirmation
- **Comprehensive Backtesting Support**
- **Concurrent Execution** for high-performance analysis

## 📊 Indicator Categories

### 1. Trend Indicators (25)
**Traditional Moving Averages:**
- Simple Moving Average (SMA) - Basic trend following
- Exponential Moving Average (EMA) - Responsive to recent prices
- Weighted Moving Average (WMA) - Linear weight distribution
- Volume Weighted Moving Average (VWMA) - Volume-based weighting

**Advanced Moving Averages:**
- Hull Moving Average (HMA) - Reduced lag, smooth trend
- Kaufman Adaptive MA (KAMA) - Market volatility adaptive
- Double Exponential MA (DEMA) - Enhanced responsiveness
- Triple Exponential MA (TEMA) - Ultra-responsive trend following
- McGinley Dynamic - Auto-adjusting to market speed
- Zero Lag EMA - Minimal delay trend indicator
- Linear Regression - Mathematical trend fitting

**Volume-Weighted Trend Indicators:**
- VW Simple Moving Average - Volume-weighted SMA
- VW Exponential Moving Average - Volume-weighted EMA
- VW Hull Moving Average - Volume-weighted HMA
- VW Adaptive Moving Average - Volume-weighted KAMA

**Specialized Trend Systems:**
- Ichimoku Cloud - Complete trend analysis system
- Parabolic SAR - Stop and reverse trend system
- Alligator Indicator - Bill Williams trend system

### 2. Momentum Oscillators (20)
**Classical Oscillators:**
- Relative Strength Index (RSI) - Overbought/oversold conditions
- MACD - Moving average convergence divergence
- Stochastic Oscillator - Price position within range
- Williams %R - Price position relative to high-low range
- Commodity Channel Index (CCI) - Price deviation analysis

**Advanced Oscillators:**
- Ultimate Oscillator - Multi-timeframe momentum
- TRIX - Triple exponential momentum
- Fisher Transform - Gaussian probability analysis
- Awesome Oscillator - Momentum with market structure
- Accelerator Oscillator - Rate of momentum change
- Rate of Change (ROC) - Pure momentum measurement
- Price Oscillator (PPO) - Percentage price oscillator

**Volume-Weighted Momentum:**
- VW RSI - Volume-weighted relative strength
- VW MACD - Volume-weighted MACD
- VW Stochastic - Volume-weighted stochastic
- VW Williams %R - Volume-weighted Williams
- VW CCI - Volume-weighted commodity channel index
- Money Flow Index (MFI) - Volume-weighted RSI

### 3. Volatility Indicators (15)
**Band-Based Indicators:**
- Bollinger Bands - Price volatility bands
- Keltner Channels - ATR-based channels
- Donchian Channels - Breakout system
- VW Bollinger Bands - Volume-weighted bands

**Range-Based Indicators:**
- Average True Range (ATR) - Price volatility measurement
- VW ATR - Volume-weighted ATR
- VW ATRP - Volume-weighted ATR percentage
- Chaikin Volatility - Price range volatility

**Advanced Volatility:**
- Historical Volatility - Statistical price volatility
- Average Directional Index (ADX) - Trend strength
- Mass Index - Reversal identification
- VW ADX - Volume-weighted directional index

### 4. Volume Indicators (20)
**Price-Volume Analysis:**
- Volume Weighted Average Price (VWAP) - Institutional benchmark
- Enhanced VWAP with Bands - VWAP with standard deviation bands
- On Balance Volume (OBV) - Cumulative volume analysis
- Accumulation/Distribution Line - Money flow accumulation

**Money Flow Indicators:**
- Money Flow Index (MFI) - Volume-weighted RSI
- Chaikin Money Flow (CMF) - Buying/selling pressure
- Chaikin Oscillator - A/D line momentum
- Force Index - Price and volume momentum

**Volume Momentum:**
- Volume Rate of Change (VROC) - Volume momentum
- Price Volume Trend (PVT) - Volume-weighted price trend
- Ease of Movement (EMV) - Price movement ease
- Negative Volume Index (NVI) - Smart money tracking

**Advanced Volume Analysis:**
- Volume Profile - Price level volume distribution
- Volume Weighted Moving Average - True volume weighting
- Volume Oscillator - Volume momentum analysis

### 5. Support/Resistance Indicators (8)
**Pivot Analysis:**
- Classical Pivot Points - Traditional S/R levels
- Fibonacci Retracements - Mathematical S/R levels
- Camarilla Pivots - Intraday S/R system
- Woodie's Pivots - Modified pivot calculation

**Dynamic S/R:**
- Swing High/Low Detection - Automatic S/R identification
- Fractal Analysis - Market structure fractals
- Supply/Demand Zones - Institutional S/R areas
- Volume Profile S/R - Volume-based S/R levels

## 🕯️ Candlestick Patterns (25+)

### Single Candlestick Patterns (8)
1. **Doji** - Market indecision, potential reversal
   - Standard Doji - Equal open/close
   - Long Legged Doji - Long shadows, high indecision
   - Dragonfly Doji - Long lower shadow, potential bullish reversal
   - Gravestone Doji - Long upper shadow, potential bearish reversal

2. **Hammer/Hanging Man** - Reversal pattern with long lower shadow
   - Context-dependent: Hammer (bullish in downtrend), Hanging Man (bearish in uptrend)

3. **Shooting Star/Inverted Hammer** - Reversal pattern with long upper shadow
   - Context-dependent: Shooting Star (bearish in uptrend), Inverted Hammer (bullish in downtrend)

4. **Marubozu** - Strong directional movement
   - White Marubozu - Strong bullish continuation
   - Black Marubozu - Strong bearish continuation

5. **Spinning Top** - Indecision with long wicks on both sides

### Two Candlestick Patterns (7)
1. **Engulfing Patterns** - Complete body engulfment
   - Bullish Engulfing - Green candle engulfs previous red candle
   - Bearish Engulfing - Red candle engulfs previous green candle

2. **Harami Patterns** - Inside candle formation
   - Bullish Harami - Small green inside large red
   - Bearish Harami - Small red inside large green

3. **Piercing Line** - Bullish reversal with 50%+ penetration
4. **Dark Cloud Cover** - Bearish reversal with 50%+ penetration
5. **Tweezer Tops/Bottoms** - Double top/bottom formation
6. **Belt Hold** - Strong opening in trend direction

### Three Candlestick Patterns (6)
1. **Morning Star** - Bullish reversal: Red → Small → Green
2. **Evening Star** - Bearish reversal: Green → Small → Red
3. **Three White Soldiers** - Strong bullish continuation
4. **Three Black Crows** - Strong bearish continuation
5. **Abandoned Baby** - Island reversal pattern
6. **Three Inside Up/Down** - Harami followed by confirmation

### Complex Patterns (4)
1. **Island Reversal** - Gap-based reversal
2. **Rising/Falling Three Methods** - Continuation patterns
3. **Breakaway Gaps** - Strong momentum patterns
4. **Exhaustion Gaps** - Trend ending patterns

## 🎯 Usage Examples

### Basic Indicator Calculation
```python
from indicators.comprehensive_indicators import ComprehensiveIndicators
import pandas as pd

# Initialize the comprehensive indicators
indicators = ComprehensiveIndicators()

# Prepare your data
data = {
    'open': df['open'],
    'high': df['high'],
    'low': df['low'],
    'close': df['close'],
    'volume': df['volume']
}

# Calculate all indicators
results = indicators.calculate_all_indicators(data)

# Get overall summary
summary = indicators.get_indicator_summary(results)
print(f"Total indicators calculated: {summary['total_indicators']}")
print(f"Strong signals detected: {len(summary['strong_signals'])}")
```

### Specific Indicator Examples
```python
# RSI with volume weighting
rsi_result = indicators.traditional_indicators.rsi(close_data, 14)
vw_rsi_result = indicators.traditional_indicators.vw_rsi(close_data, volume_data, 14)

print(f"Traditional RSI: {rsi_result.value.iloc[-1]:.2f} - Signal: {rsi_result.signal}")
print(f"Volume-Weighted RSI: {vw_rsi_result.value.iloc[-1]:.2f} - Signal: {vw_rsi_result.signal}")

# MACD analysis
macd_result = indicators.traditional_indicators.macd(close_data, 12, 26, 9)
macd_data = macd_result.value
print(f"MACD Line: {macd_data['macd'].iloc[-1]:.4f}")
print(f"Signal Line: {macd_data['signal'].iloc[-1]:.4f}")
print(f"Histogram: {macd_data['histogram'].iloc[-1]:.4f}")
```

### Candlestick Pattern Detection
```python
# Detect all patterns
pattern_df = pd.DataFrame(data)
patterns = indicators.pattern_detector.detect_all_patterns(pattern_df)
pattern_summary = indicators.pattern_detector.get_pattern_summary(patterns)

print(f"Patterns detected: {pattern_summary['total_patterns']}")
print("Strongest patterns:")
for signal in pattern_summary['strongest_signals'][:5]:
    print(f"- {signal['pattern']}: {signal['strength']:.2f} strength")
```

## ⚙️ Configuration Options

### Indicator Parameters
Most indicators support customizable parameters:

```python
# RSI with different periods
rsi_14 = indicators.traditional_indicators.rsi(close_data, period=14)  # Standard
rsi_21 = indicators.traditional_indicators.rsi(close_data, period=21)  # Longer period

# Bollinger Bands with different settings
bb_standard = indicators.traditional_indicators.bollinger_bands(close_data, period=20, std_dev=2.0)
bb_tight = indicators.traditional_indicators.bollinger_bands(close_data, period=20, std_dev=1.5)
bb_wide = indicators.traditional_indicators.bollinger_bands(close_data, period=20, std_dev=2.5)

# MACD with custom settings
macd_fast = indicators.traditional_indicators.macd(close_data, fast=8, slow=21, signal_period=5)
```

### Volume-Weighted Enhancements
Enable volume-weighted calculations for institutional-grade analysis:

```python
# Calculate with volume-weighted variants
results = indicators.calculate_all_indicators(
    data,
    include_patterns=True,
    include_volume_weighted=True  # Enable VW variants
)

# Filter only volume-weighted indicators
vw_indicators = {k: v for k, v in results.items() if v.volume_weighted}
print(f"Volume-weighted indicators: {len(vw_indicators)}")
```

## 📈 Signal Interpretation

### Signal Strength Levels
- **0.0 - 0.3**: Weak signal
- **0.3 - 0.7**: Moderate signal  
- **0.7 - 1.0**: Strong signal

### Signal Types
- **STRONG_BUY**: High conviction bullish signal
- **BUY**: Moderate bullish signal
- **NEUTRAL**: No clear directional bias
- **SELL**: Moderate bearish signal
- **STRONG_SELL**: High conviction bearish signal

### Confidence Scoring
Each indicator provides a confidence score (0.0 - 1.0) based on:
- Market conditions suitability
- Historical reliability
- Volume confirmation (where applicable)
- Pattern completion quality

## 🔧 Advanced Features

### Pattern Strength Analysis
```python
# Get detailed pattern analysis
pattern_result = indicators.traditional_indicators.pattern_strength_analysis(
    open_data, high_data, low_data, close_data, volume_data
)

print(f"Pattern strength: {pattern_result.strength:.2f}")
print(f"Volume confirmation: {pattern_result.metadata['volume_confirmation']:.2f}")
print(f"Confidence level: {pattern_result.metadata['confidence_level']}")
```

### Multi-Timeframe Analysis
```python
# Analyze multiple timeframes
timeframes = ['1H', '4H', '1D']
multi_tf_results = {}

for tf in timeframes:
    tf_data = resample_data(data, tf)  # Your resampling function
    multi_tf_results[tf] = indicators.calculate_all_indicators(tf_data)

# Compare signals across timeframes
for tf, results in multi_tf_results.items():
    summary = indicators.get_indicator_summary(results)
    print(f"{tf} sentiment: {summary['sentiment_percentages']}")
```

### Custom Indicator Combinations
```python
# Create custom signal combinations
def trend_momentum_combo(results):
    """Combine trend and momentum signals"""
    trend_signals = [v for k, v in results.items() if v.category.value == 'trend']
    momentum_signals = [v for k, v in results.items() if v.category.value == 'momentum']
    
    trend_score = sum(1 if 'BUY' in s.signal else -1 if 'SELL' in s.signal else 0 
                     for s in trend_signals) / len(trend_signals)
    momentum_score = sum(1 if 'BUY' in s.signal else -1 if 'SELL' in s.signal else 0 
                        for s in momentum_signals) / len(momentum_signals)
    
    combined_score = (trend_score + momentum_score) / 2
    
    if combined_score > 0.3:
        return "BULLISH"
    elif combined_score < -0.3:
        return "BEARISH"
    else:
        return "NEUTRAL"

# Apply custom combination
combo_signal = trend_momentum_combo(results)
print(f"Combined trend-momentum signal: {combo_signal}")
```

## 🧪 Testing and Validation

### Comprehensive Test Suite
Run the complete test suite to validate all indicators:

```bash
python test_comprehensive_indicators.py
```

### Individual Indicator Testing
```python
# Test specific indicators
from tests.test_comprehensive_indicators import test_individual_indicators

test_results = test_individual_indicators(['rsi_14', 'macd', 'bollinger_bands'])
print(f"Test results: {test_results}")
```

### Backtesting Integration
```python
# Backtest with indicators
def backtest_strategy(data, results):
    """Simple strategy using multiple indicators"""
    signals = []
    
    for i in range(len(data)):
        # Get indicator signals for current bar
        current_signals = {k: v for k, v in results.items() 
                         if hasattr(v.value, 'iloc') and len(v.value) > i}
        
        # Apply your strategy logic
        bullish_count = sum(1 for v in current_signals.values() if 'BUY' in v.signal)
        bearish_count = sum(1 for v in current_signals.values() if 'SELL' in v.signal)
        
        if bullish_count > bearish_count * 1.5:
            signals.append('BUY')
        elif bearish_count > bullish_count * 1.5:
            signals.append('SELL')
        else:
            signals.append('HOLD')
    
    return signals

# Run backtest
strategy_signals = backtest_strategy(data, results)
```

## 📚 Indicator Specifications

### What Each Indicator Excels At

#### Trend Indicators
- **SMA/EMA**: Basic trend identification, smooth price action
- **VWMA**: Institutional-level trend analysis with volume weighting
- **Hull MA**: Fast trend changes with minimal lag
- **KAMA**: Adaptive to market volatility, reduces whipsaws
- **Ichimoku**: Complete trend system with support/resistance
- **Parabolic SAR**: Trend reversal identification

#### Momentum Indicators  
- **RSI**: Overbought/oversold conditions, divergence analysis
- **MACD**: Trend changes, momentum shifts
- **Stochastic**: Short-term reversal signals
- **Williams %R**: Fast oscillator for quick reversals
- **CCI**: Cyclical turning points
- **MFI**: Volume-confirmed momentum analysis

#### Volatility Indicators
- **Bollinger Bands**: Price extremes, volatility expansion/contraction
- **ATR**: Risk management, stop-loss placement
- **Keltner Channels**: Trend-following with volatility adjustment
- **ADX**: Trend strength measurement

#### Volume Indicators
- **VWAP**: Institutional benchmarking, fair value
- **OBV**: Volume-price trend confirmation
- **MFI**: Money flow analysis
- **CMF**: Buying/selling pressure assessment

### Best Use Cases by Market Condition

#### Trending Markets
- Hull Moving Average
- Parabolic SAR  
- ADX
- MACD
- Volume-weighted indicators

#### Range-Bound Markets
- RSI
- Stochastic
- Williams %R
- Bollinger Bands
- Oscillators

#### High Volatility
- ATR-based indicators
- Bollinger Bands
- Volume indicators
- Pattern recognition

#### Low Volatility
- Momentum oscillators
- Trend-following MAs
- Breakout indicators

## 🚀 Performance Optimization

The library is optimized for high-performance analysis:

- **Vectorized Calculations**: All indicators use pandas/numpy vectorization
- **Efficient Memory Usage**: Minimal memory footprint for large datasets
- **Concurrent Execution**: Parallel calculation of independent indicators
- **Caching Support**: Built-in caching for repeated calculations

## 📖 References and Further Reading

### Technical Analysis Books
- "Technical Analysis of the Financial Markets" by John J. Murphy
- "New Concepts in Technical Trading Systems" by J. Welles Wilder
- "Japanese Candlestick Charting Techniques" by Steve Nison
- "Technical Analysis Explained" by Martin J. Pring

### Research Papers
- "Volume-Weighted Moving Averages" - Financial Markets Research
- "Adaptive Moving Averages" - Kaufman, P.J.
- "The New Science of Technical Analysis" - DeMark, T.

## 🤝 Contributing

We welcome contributions to enhance the indicator library:

1. Fork the repository
2. Create a feature branch
3. Add new indicators or improve existing ones
4. Include comprehensive tests
5. Submit a pull request

### Adding New Indicators
Follow the established patterns:
```python
@staticmethod
def your_new_indicator(data: pd.Series, period: int = 20) -> IndicatorResult:
    """Your new indicator description"""
    # Calculation logic
    result_value = your_calculation(data, period)
    
    # Signal generation
    signal = "BUY" if condition else "SELL"
    strength = calculate_strength()
    
    return IndicatorResult(
        result_value, signal, strength, confidence,
        {"period": period, "custom_metadata": True}
    )
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For questions, issues, or contributions:
- Create an issue on GitHub
- Contact: vincent.pereira@tradingtech.com
- Documentation: [Link to full documentation]

---

**Happy Trading! 📈🚀**

*Remember: This library provides tools for analysis. Always combine technical analysis with fundamental analysis and proper risk management for successful trading.*