"""
Enhanced Volume-Weighted Indicators Example and Testing
Demonstrates the integration of technical indicators, candlestick patterns, and price adjustments
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import warnings

from .enhanced_volume_weighted import (
    EnhancedMarketData, 
    EnhancedVolumeWeightedIndicators,
    calculate_all_enhanced_indicators,
    calculate_pattern_based_indicators,
    calculate_technical_enhanced_indicators
)

warnings.filterwarnings('ignore')


def generate_sample_data(days: int = 252) -> EnhancedMarketData:
    """
    Generate sample market data for testing
    
    Args:
        days: Number of days of data to generate
        
    Returns:
        EnhancedMarketData object with sample data
    """
    # Generate dates
    dates = pd.date_range(start='2023-01-01', periods=days, freq='D')
    
    # Generate realistic price data with trends and volatility
    np.random.seed(42)  # For reproducible results
    
    # Base price trend
    base_price = 100
    trend = np.cumsum(np.random.normal(0.001, 0.02, days))  # Small upward trend with volatility
    prices = base_price * np.exp(trend)
    
    # Generate OHLC data
    close_prices = prices
    
    # Generate realistic OHLC relationships
    daily_volatility = np.random.uniform(0.01, 0.05, days)  # 1-5% daily volatility
    
    high_prices = close_prices * (1 + daily_volatility * np.random.uniform(0.3, 1.0, days))
    low_prices = close_prices * (1 - daily_volatility * np.random.uniform(0.3, 1.0, days))
    
    # Open prices (close to previous close with some gap)
    open_prices = np.zeros(days)
    open_prices[0] = close_prices[0]
    for i in range(1, days):
        gap = np.random.normal(0, 0.005)  # Small gaps
        open_prices[i] = close_prices[i-1] * (1 + gap)
    
    # Ensure OHLC relationships are maintained
    for i in range(days):
        high_prices[i] = max(high_prices[i], open_prices[i], close_prices[i])
        low_prices[i] = min(low_prices[i], open_prices[i], close_prices[i])
    
    # Generate volume data (higher volume on volatile days)
    base_volume = 1000000
    volume_multiplier = 1 + daily_volatility * 2  # Higher volume on volatile days
    volumes = base_volume * volume_multiplier * np.random.uniform(0.5, 2.0, days)
    
    # Generate corporate actions data
    stock_splits = pd.Series(0.0, index=dates)
    dividends = pd.Series(0.0, index=dates)
    
    # Add a few stock splits and dividends
    if days > 100:
        stock_splits.iloc[100] = 1.0  # 2:1 split (100% stock dividend)
        dividends.iloc[50] = 2.5      # $2.50 dividend
        dividends.iloc[150] = 3.0     # $3.00 dividend
    
    return EnhancedMarketData(
        open=pd.Series(open_prices, index=dates),
        high=pd.Series(high_prices, index=dates),
        low=pd.Series(low_prices, index=dates),
        close=pd.Series(close_prices, index=dates),
        volume=pd.Series(volumes, index=dates),
        stock_splits=stock_splits,
        dividends=dividends
    )


def demonstrate_enhanced_indicators():
    """
    Demonstrate the enhanced volume-weighted indicators
    """
    print("=== Enhanced Volume-Weighted Indicators Demonstration ===\n")
    
    # Generate sample data
    print("1. Generating sample market data...")
    data = generate_sample_data(252)  # 1 year of data
    print(f"   Generated {len(data.close)} days of OHLCV data")
    print(f"   Price range: ${data.close.min():.2f} - ${data.close.max():.2f}")
    print(f"   Average volume: {data.volume.mean():,.0f}")
    
    if data.adjusted_close is not None:
        print(f"   Adjusted close available (corporate actions applied)")
    print()
    
    # Calculate all enhanced indicators
    print("2. Calculating enhanced indicators...")
    enhanced_indicators = calculate_all_enhanced_indicators(data)
    print(f"   Calculated {len(enhanced_indicators)} enhanced indicators")
    
    # Display some key indicators
    print("\n3. Key Enhanced Indicators (last 5 values):")
    key_indicators = [
        'pattern_vwap',
        'enhanced_vw_sma_21',
        'vw_sma_21',
        'vw_ema_13',
        'pattern_strength',
        'vw_atr',
        'vw_bb_sma_21'
    ]
    
    for indicator in key_indicators:
        if indicator in enhanced_indicators:
            values = enhanced_indicators[indicator].dropna().tail(5)
            print(f"   {indicator:25}: {values.iloc[-1]:.4f}")
    
    # Pattern-based analysis
    print("\n4. Pattern-based indicators...")
    pattern_indicators = calculate_pattern_based_indicators(data)
    print(f"   Calculated {len(pattern_indicators)} pattern-based indicators")
    
    # Show pattern strength distribution
    if 'pattern_strength' in pattern_indicators:
        pattern_strength = pattern_indicators['pattern_strength']
        strong_patterns = (pattern_strength > 0.5).sum()
        print(f"   Days with strong patterns (>0.5): {strong_patterns}")
        print(f"   Average pattern strength: {pattern_strength.mean():.3f}")
    
    # Technical enhanced indicators
    print("\n5. Technical enhanced indicators...")
    tech_indicators = calculate_technical_enhanced_indicators(data)
    print(f"   Calculated {len(tech_indicators)} technical enhanced indicators")
    
    # Multi-timeframe analysis
    timeframes = [5, 13, 21, 55]
    print(f"\n6. Multi-timeframe analysis (timeframes: {timeframes}):")
    for tf in timeframes:
        vw_sma_key = f'vw_sma_{tf}'
        vw_ema_key = f'vw_ema_{tf}'
        if vw_sma_key in enhanced_indicators and vw_ema_key in enhanced_indicators:
            sma_val = enhanced_indicators[vw_sma_key].dropna().iloc[-1]
            ema_val = enhanced_indicators[vw_ema_key].dropna().iloc[-1]
            print(f"   TF {tf:2d} - VW SMA: {sma_val:.2f}, VW EMA: {ema_val:.2f}")
    
    # Volatility analysis
    print("\n7. Volatility analysis:")
    if 'vw_atr' in enhanced_indicators:
        vw_atr = enhanced_indicators['vw_atr'].dropna()
        print(f"   VW ATR (current): {vw_atr.iloc[-1]:.4f}")
        print(f"   VW ATR (average): {vw_atr.mean():.4f}")
    
    if 'atr_percent' in enhanced_indicators:
        atr_pct = enhanced_indicators['atr_percent'].dropna()
        print(f"   ATR Percent (current): {atr_pct.iloc[-1]:.2f}%")
        print(f"   ATR Percent (average): {atr_pct.mean():.2f}%")
    
    # Comparison with original indicators
    print("\n8. Comparison with original indicators:")
    comparisons = [
        ('enhanced_vw_sma_21', 'original_vw_sma_21', 'VW SMA 21'),
        ('pattern_vwap', 'original_vw_sma_21', 'Pattern VWAP vs VW SMA'),
    ]
    
    for enhanced_key, original_key, description in comparisons:
        if enhanced_key in enhanced_indicators and original_key in enhanced_indicators:
            enhanced_val = enhanced_indicators[enhanced_key].dropna().iloc[-1]
            original_val = enhanced_indicators[original_key].dropna().iloc[-1]
            diff_pct = ((enhanced_val - original_val) / original_val) * 100
            print(f"   {description:25}: Enhanced={enhanced_val:.4f}, Original={original_val:.4f}, Diff={diff_pct:+.2f}%")
    
    return enhanced_indicators, data


def analyze_pattern_impact():
    """
    Analyze the impact of candlestick patterns on volume weighting
    """
    print("\n=== Pattern Impact Analysis ===\n")
    
    # Generate data
    data = generate_sample_data(100)  # Smaller dataset for detailed analysis
    
    # Calculate pattern indicators
    pattern_indicators = calculate_pattern_based_indicators(data)
    
    # Create DataFrame for pattern analysis
    df = pd.DataFrame({
        'Mid_Open': data.open,
        'Mid_High': data.high,
        'Mid_Low': data.low,
        'Mid_Close': data.close,
        'Volume': data.volume
    })
    
    # Apply candlestick pattern recognition
    from .candle_patterns import apply_candle_patterns
    df_patterns = apply_candle_patterns(df)
    
    # Analyze pattern frequency
    pattern_columns = ['Hanging_Man', 'Shooting_Star', 'Spinning_Top', 'Marubozu', 
                      'Engulfing', 'Tweezer_Top', 'Tweezer_Bottom', 'Morning_Star', 'Evening_Star']
    
    print("Pattern frequency analysis:")
    for pattern in pattern_columns:
        if pattern in df_patterns.columns:
            count = df_patterns[pattern].sum()
            percentage = (count / len(df_patterns)) * 100
            print(f"   {pattern:15}: {count:3d} occurrences ({percentage:5.1f}%)")
    
    # Show impact on volume weighting
    if 'pattern_strength' in pattern_indicators and 'volume_multiplier' in pattern_indicators:
        pattern_strength = pattern_indicators['pattern_strength']
        volume_multiplier = pattern_indicators['volume_multiplier']
        
        print(f"\nVolume weighting impact:")
        print(f"   Average volume multiplier: {volume_multiplier.mean():.3f}")
        print(f"   Max volume multiplier: {volume_multiplier.max():.3f}")
        print(f"   Days with volume boost (>1.1x): {(volume_multiplier > 1.1).sum()}")
        
        # Show correlation between pattern strength and price movement
        price_change = data.close.pct_change()
        correlation = pattern_strength.corr(abs(price_change))
        print(f"   Correlation (pattern strength vs |price change|): {correlation:.3f}")


def demonstrate_technical_integration():
    """
    Demonstrate integration with technical indicators
    """
    print("\n=== Technical Indicators Integration ===\n")
    
    # Generate data
    data = generate_sample_data(200)
    
    # Create DataFrame for technical analysis
    df = pd.DataFrame({
        'Mid_Open': data.open,
        'Mid_High': data.high,
        'Mid_Low': data.low,
        'Mid_Close': data.close,
        'Volume': data.volume
    })
    
    # Import and apply technical indicators
    from . import technical_indicators as ti
    
    print("1. Volume-Weighted Bollinger Bands:")
    df_bb = ti.VW_BollingerBands_OHLC(df.copy(), n=20)
    bb_sma = df_bb['VW_BB_SMA20'].dropna()
    bb_upper = df_bb['VW_BB_Upper'].dropna()
    bb_lower = df_bb['VW_BB_Lower'].dropna()
    
    current_price = data.close.iloc[-1]
    bb_position = (current_price - bb_sma.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1])
    
    print(f"   Current price: ${current_price:.2f}")
    print(f"   BB SMA: ${bb_sma.iloc[-1]:.2f}")
    print(f"   BB Upper: ${bb_upper.iloc[-1]:.2f}")
    print(f"   BB Lower: ${bb_lower.iloc[-1]:.2f}")
    print(f"   Position in BB: {bb_position:.2f} (0=middle, +0.5=upper, -0.5=lower)")
    
    print("\n2. Volume-Weighted ATR Analysis:")
    df_atr = ti.VW_ATR(df.copy(), n=14)
    vw_atr = df_atr['VW_ATR14'].dropna()
    
    print(f"   Current VW ATR: ${vw_atr.iloc[-1]:.4f}")
    print(f"   VW ATR as % of price: {(vw_atr.iloc[-1]/current_price)*100:.2f}%")
    print(f"   Average VW ATR: ${vw_atr.mean():.4f}")
    
    print("\n3. Volume-Weighted RSI Variations:")
    df_rsi = ti.RSI(df.copy(), n=14)
    df_rsi_ohlc = ti.RSI_OHLC(df.copy(), n=14)
    df_rsi_hl = ti.RSI_HL(df.copy(), n=14)
    
    rsi_close = df_rsi['RSI14'].dropna().iloc[-1]
    rsi_ohlc = df_rsi_ohlc['RSI14_OHLC'].dropna().iloc[-1]
    rsi_hl = df_rsi_hl['RSI14_HL'].dropna().iloc[-1]
    
    print(f"   RSI (Close): {rsi_close:.1f}")
    print(f"   RSI (OHLC): {rsi_ohlc:.1f}")
    print(f"   RSI (HL): {rsi_hl:.1f}")
    
    # Determine RSI signals
    if rsi_close > 70:
        rsi_signal = "Overbought"
    elif rsi_close < 30:
        rsi_signal = "Oversold"
    else:
        rsi_signal = "Neutral"
    print(f"   RSI Signal: {rsi_signal}")


def create_performance_comparison():
    """
    Compare performance of enhanced vs original indicators
    """
    print("\n=== Performance Comparison ===\n")
    
    # Generate longer dataset for meaningful comparison
    data = generate_sample_data(500)
    
    # Calculate both enhanced and original indicators
    enhanced_indicators = calculate_all_enhanced_indicators(data)
    
    # Compare key indicators
    comparisons = [
        ('pattern_vwap', 'Pattern-weighted VWAP'),
        ('enhanced_vw_sma_21', 'Enhanced VW SMA 21'),
        ('original_vw_sma_21', 'Original VW SMA 21'),
        ('vw_sma_21', 'Multi-timeframe VW SMA 21'),
    ]
    
    print("Indicator statistics (last 100 days):")
    for indicator_key, description in comparisons:
        if indicator_key in enhanced_indicators:
            indicator_data = enhanced_indicators[indicator_key].dropna().tail(100)
            if len(indicator_data) > 0:
                mean_val = indicator_data.mean()
                std_val = indicator_data.std()
                min_val = indicator_data.min()
                max_val = indicator_data.max()
                
                print(f"\n   {description}:")
                print(f"     Mean: ${mean_val:.2f}")
                print(f"     Std:  ${std_val:.2f}")
                print(f"     Range: ${min_val:.2f} - ${max_val:.2f}")
    
    # Calculate correlation between enhanced and original indicators
    if 'enhanced_vw_sma_21' in enhanced_indicators and 'original_vw_sma_21' in enhanced_indicators:
        enhanced_sma = enhanced_indicators['enhanced_vw_sma_21'].dropna()
        original_sma = enhanced_indicators['original_vw_sma_21'].dropna()
        
        # Align series for correlation
        common_index = enhanced_sma.index.intersection(original_sma.index)
        if len(common_index) > 10:
            correlation = enhanced_sma[common_index].corr(original_sma[common_index])
            print(f"\nCorrelation between Enhanced and Original VW SMA 21: {correlation:.4f}")
    
    # Analyze volatility-adjusted indicators
    if 'vw_sma_volatility_adjusted' in enhanced_indicators:
        vol_adj_sma = enhanced_indicators['vw_sma_volatility_adjusted'].dropna()
        print(f"\nVolatility-adjusted VW SMA:")
        print(f"   Data points: {len(vol_adj_sma)}")
        print(f"   Current value: ${vol_adj_sma.iloc[-1]:.2f}")
        print(f"   Average value: ${vol_adj_sma.mean():.2f}")


if __name__ == "__main__":
    """
    Run all demonstrations
    """
    try:
        # Main demonstration
        enhanced_indicators, sample_data = demonstrate_enhanced_indicators()
        
        # Pattern impact analysis
        analyze_pattern_impact()
        
        # Technical integration demonstration
        demonstrate_technical_integration()
        
        # Performance comparison
        create_performance_comparison()
        
        print("\n=== Summary ===")
        print("Enhanced volume-weighted indicators successfully demonstrated!")
        print(f"Total indicators calculated: {len(enhanced_indicators)}")
        print("\nKey enhancements:")
        print("✓ Candlestick pattern recognition and volume weighting")
        print("✓ Integration with comprehensive technical indicators")
        print("✓ Price adjustment for corporate actions")
        print("✓ Multi-timeframe analysis")
        print("✓ Volatility-adjusted calculations")
        print("✓ Pattern strength-based volume weighting")
        
    except Exception as e:
        print(f"Error during demonstration: {e}")
        import traceback
        traceback.print_exc()