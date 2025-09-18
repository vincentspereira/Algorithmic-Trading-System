**Comprehensive List of Technical Indicators and Candlestick Patterns**

**Technical Indicators**

**Traditional Indicators**

1. **comprehensive_indicators.py**
    - Type: Multi-Indicator System
    - Purpose: Complete suite of traditional indicators with volume weighting
    - Parameters: Configurable for all included indicators
2. **unified_enhanced_indicators.py**
    - Type: Unified Indicator System
    - Purpose: Combines 80+ traditional and volume-weighted indicators
    - Parameters: Configurable across all indicator categories

**Moving Average Indicators**

1. **volume_weighted_moving_averages.py**
    - Type: Moving Average Indicators
    - Purpose: Implements volume-weighted moving averages including VW SMA, VW EMA, VW AMA, TEMA, KAMA, HMA, and ZLEMA
    - Parameters: Configurable period, volume weighting, adaptive parameters
2. **enhanced_moving_averages.py**
    - Type: Enhanced Moving Averages
    - Purpose: Volume-weighted simple and exponential moving averages with dynamic signal generation
    - Parameters: Period, volume weighting, adaptive smoothing
3. **augmented_volume_weighted_moving_averages.py**
    - Type: Augmented Moving Averages (Institutional Grade)
    - Purpose: Enhanced VWMA with adaptive periods, smart money confirmation, VW Hull MA, adaptive VW EMA
    - Parameters: 5-pillar institutional architecture, low-latency processing, explainable AI, behavioral overlay, automated risk management
4. **augmented_moving_average_crossover.py**
    - Type: Augmented Moving Average Crossover System (Institutional Grade)
    - Purpose: Multi-timeframe MA analysis, adaptive period adjustment, Golden/Death cross detection
    - Parameters: Fast/slow periods, MA types (SMA, EMA, WMA, VWMA, HULL, ADAPTIVE), volume weighting, trend strength analysis

**Oscillator Indicators**

1. **volume_weighted_oscillators.py**
    - Type: Oscillator Indicators
    - Purpose: Implements volume-weighted RSI, MACD, Stochastic, Williams %R, and Money Flow Index
    - Parameters: Period, overbought/oversold thresholds, volume weighting
2. **enhanced_oscillators.py**
    - Type: Enhanced Oscillators
    - Purpose: Advanced RSI implementation with volume weighting and adaptive smoothing
    - Parameters: Period, adaptive parameters, overbought/oversold thresholds
3. **augmented_volume_weighted_oscillators.py**
    - Type: Augmented Oscillators (Institutional Grade)
    - Purpose: Enhanced Stochastic, Williams %R, CCI, Ultimate Oscillator, Money Flow Index with institutional features
    - Parameters: 5-pillar institutional architecture, volume weighting, smart money detection, regime adaptation, multi-timeframe convergence
4. **augmented_rsi.py**
    - Type: Augmented RSI (Institutional Grade)
    - Purpose: Enhanced RSI with volume weighting, adaptive thresholds, divergence detection
    - Parameters: Period, overbought/oversold levels, volume weighting, divergence detection, market regime adaptation

**Momentum Indicators**

1. **volume_weighted_momentum.py**
    - Type: Momentum Indicators
    - Purpose: Volume-weighted ROC and Momentum indicators with adaptive features
    - Parameters: Period, volume weighting, adaptive features
2. **augmented_volume_weighted_momentum.py**
    - Type: Augmented Momentum Indicators (Institutional Grade)
    - Purpose: Enhanced RSI, ROC, Stochastic, Williams %R, CCI with institutional features
    - Parameters: 5-pillar institutional architecture, smart money detection, regime adaptation, multi-timeframe convergence
3. **enhanced_market_structure.py**
    - Type: Market Structure Indicators
    - Purpose: Support and resistance level detection with volume-weighted price action analysis
    - Parameters: Lookback period, minimum touches, strength threshold
4. **augmented_volume_weighted_market_structure.py**
    - Type: Augmented Market Structure (Institutional Grade)
    - Purpose: Enhanced Support/Resistance, Market Profile, Order Flow Imbalance, Liquidity Zones
    - Parameters: 5-pillar institutional architecture, smart money detection, multi-timeframe analysis, automated risk management

**Volatility Indicators**

1. **volume_weighted_volatility.py**
    - Type: Volatility Indicators
    - Purpose: Volume-weighted ATR, Bollinger Bands, and volatility analysis
    - Parameters: Period, volume weighting, adaptive smoothing
2. **enhanced_volatility.py**
    - Type: Enhanced Volatility Indicators
    - Purpose: Advanced ATR with volume weighting and market condition classification
    - Parameters: Period, adaptive smoothing, volume weighting
3. **augmented_volume_weighted_volatility.py**
    - Type: Augmented Volatility Indicators (Institutional Grade)
    - Purpose: Enhanced Bollinger Bands, ATR, Volatility Index, Keltner Channels, Donchian Channels
    - Parameters: 5-pillar institutional architecture, dynamic width adjustment, smart money detection, multi-timeframe analysis

**Trend Indicators**

1. **volume_weighted_trend.py**
    - Type: Trend Indicators
    - Purpose: Volume-weighted MACD, ADX and other trend-following indicators
    - Parameters: Various periods for different components, volume weighting
2. **augmented_volume_weighted_trend.py**
    - Type: Augmented Trend Indicators (Institutional Grade)
    - Purpose: Enhanced MACD, ADX, Aroon, Parabolic SAR, TSI with institutional features
    - Parameters: 5-pillar institutional architecture, smart money detection, regime adaptation, multi-timeframe convergence
3. **augmented_macd.py**
    - Type: Augmented MACD (Institutional Grade)
    - Purpose: Enhanced MACD with volume weighting, histogram analysis, signal line crossover analysis
    - Parameters: Fast/slow/signal periods, volume weighting, histogram analysis, zero-line analysis

**Volume Indicators**

1. **institutional_volume_profile.py**
    - Type: Volume Analysis Indicators
    - Purpose: Advanced volume profile analysis with institutional flow detection
    - Parameters: Volume lookback period, institutional thresholds

**Composite/Multi-Indicator Systems**

1. **ensemble_indicator_system.py**
    - Type: Ensemble Indicator System
    - Purpose: Combines multiple indicators for consensus-based signals
    - Parameters: Configurable ensemble of indicators, weighting schemes
2. **ml_enhanced_system.py**
    - Type: Machine Learning Enhanced System
    - Purpose: ML-based market regime detection, meta-labeling, and probabilistic forecasting
    - Parameters: ML models, market regime detection parameters, forecasting horizons

**Candlestick Patterns**

**Pattern Detection Systems**

1. **unified_pattern_detector.py**
    - Type: Pattern Detection System
    - Purpose: Unified interface to all pattern detectors with backward compatibility
    - Parameters: Volume lookback, smart money thresholds, confidence thresholds
2. **pattern_base.py**
    - Type: Pattern Base Classes
    - Purpose: Base classes and utilities for pattern detection
    - Parameters: Pattern reliability metrics, volume profile classifications

**Single Candle Patterns**

1. **single_candle_patterns.py**
    - Type: Candlestick Patterns
    - Purpose: Detection of single candle patterns including:
        - Hammer and Inverted Hammer
        - Shooting Star and Hanging Man
        - Doji variations
        - Marubozu
        - Spinning Top
        - High Wave
        - Belt Hold
    - Parameters: Volume lookback period, smart money thresholds

**Two Candle Patterns**

1. **two_candle_patterns.py**
    - Type: Candlestick Patterns
    - Purpose: Detection of two candle patterns including:
        - Bullish/Bearish Engulfing
        - Harami (Bullish/Bearish)
        - Piercing Line
        - Dark Cloud Cover
        - Tweezer Tops/Bottoms
        - Kicking Pattern
    - Parameters: Volume lookback period, confidence thresholds

**Three Candle Patterns**

1. **three_candle_patterns.py**
    - Type: Candlestick Patterns
    - Purpose: Detection of three candle patterns including:
        - Morning Star
        - Evening Star
        - Three White Soldiers
        - Three Black Crows
        - Abandoned Baby
        - Three Inside Up/Down
    - Parameters: Volume lookback period, pattern reliability factors

**Four Candle Patterns**

1. **four_candle_patterns.py**
    - Type: Candlestick Patterns
    - Purpose: Detection of four candle patterns including:
        - Three Line Strike (Bullish/Bearish)
        - Concealing Baby Swallow
        - Unique Three River
        - Breakaway patterns
    - Parameters: Volume lookback period, engulfment ratios

**Complex Patterns**

1. **complex_patterns.py**
    - Type: Advanced Pattern Detection
    - Purpose: Detection of complex chart patterns with volume weighting
    - Parameters: Volume lookback period, pattern complexity settings

**Pattern Management**

1. **pattern_risk_management.py**
    - Type: Pattern Risk Management
    - Purpose: Integrated risk management for pattern-based trading
    - Parameters: Risk levels, position sizing, stop-loss parameters

This system includes over 100 technical indicators and 25+ candlestick patterns, all enhanced with volume weighting, institutional flow detection, adaptive features, and comprehensive risk management for improved accuracy and reliability in algorithmic trading applications.