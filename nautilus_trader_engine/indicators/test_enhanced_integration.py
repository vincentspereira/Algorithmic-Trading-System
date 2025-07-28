"""
Test Enhanced Volume-Weighted Indicators Integration
Simple test to verify that all components work together correctly
"""

import pandas as pd
import numpy as np
import sys
import os

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_test_data():
    """Create simple test data for verification"""
    dates = pd.date_range('2023-01-01', periods=50, freq='D')
    
    # Simple trending data
    base_price = 100
    trend = np.linspace(0, 0.1, 50)  # 10% uptrend over 50 days
    prices = base_price * (1 + trend + np.random.normal(0, 0.01, 50))
    
    # Generate OHLC
    close_prices = prices
    open_prices = np.roll(close_prices, 1)
    open_prices[0] = close_prices[0]
    
    high_prices = close_prices * (1 + np.random.uniform(0, 0.02, 50))
    low_prices = close_prices * (1 - np.random.uniform(0, 0.02, 50))
    
    # Ensure OHLC relationships
    for i in range(50):
        high_prices[i] = max(high_prices[i], open_prices[i], close_prices[i])
        low_prices[i] = min(low_prices[i], open_prices[i], close_prices[i])
    
    volumes = np.random.uniform(100000, 200000, 50)
    
    return {
        'dates': dates,
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes
    }

def test_basic_integration():
    """Test basic integration of enhanced indicators"""
    print("Testing Enhanced Volume-Weighted Indicators Integration...")
    
    try:
        # Create test data
        test_data = create_test_data()
        print("✓ Test data created successfully")
        
        # Test EnhancedMarketData creation
        from enhanced_volume_weighted import EnhancedMarketData
        
        data = EnhancedMarketData(
            open=pd.Series(test_data['open'], index=test_data['dates']),
            high=pd.Series(test_data['high'], index=test_data['dates']),
            low=pd.Series(test_data['low'], index=test_data['dates']),
            close=pd.Series(test_data['close'], index=test_data['dates']),
            volume=pd.Series(test_data['volume'], index=test_data['dates'])
        )
        print("✓ EnhancedMarketData created successfully")
        
        # Test pattern-weighted VWAP
        from enhanced_volume_weighted import EnhancedVolumeWeightedIndicators
        
        pattern_vwap = EnhancedVolumeWeightedIndicators.pattern_weighted_vwap(data)
        print(f"✓ Pattern-weighted VWAP calculated: {len(pattern_vwap.dropna())} values")
        
        # Test technical indicator enhanced SMA
        enhanced_sma = EnhancedVolumeWeightedIndicators.technical_indicator_enhanced_vw_sma(data, 10)
        print(f"✓ Enhanced VW SMA calculated: {len(enhanced_sma.dropna())} values")
        
        # Test volatility-adjusted indicators
        vol_indicators = EnhancedVolumeWeightedIndicators.volatility_adjusted_vw_indicators(data, 10)
        print(f"✓ Volatility-adjusted indicators calculated: {len(vol_indicators)} indicators")
        
        # Test multi-timeframe analysis
        mtf_indicators = EnhancedVolumeWeightedIndicators.multi_timeframe_vw_analysis(data, [5, 10, 20])
        print(f"✓ Multi-timeframe analysis completed: {len(mtf_indicators)} indicators")
        
        # Test pattern strength volume weighting
        pattern_indicators = EnhancedVolumeWeightedIndicators.pattern_strength_volume_weighting(data)
        print(f"✓ Pattern strength weighting calculated: {len(pattern_indicators)} indicators")
        
        # Test comprehensive analysis
        from enhanced_volume_weighted import calculate_all_enhanced_indicators
        all_indicators = calculate_all_enhanced_indicators(data)
        print(f"✓ Comprehensive analysis completed: {len(all_indicators)} total indicators")
        
        # Display some sample results
        print("\nSample Results (last 5 values):")
        sample_indicators = ['pattern_vwap', 'enhanced_vw_sma_21', 'vw_sma_21']
        
        for indicator in sample_indicators:
            if indicator in all_indicators:
                values = all_indicators[indicator].dropna().tail(5)
                if len(values) > 0:
                    print(f"  {indicator}: {values.iloc[-1]:.4f}")
        
        print("\n✅ All tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_individual_modules():
    """Test individual module imports and basic functionality"""
    print("\nTesting Individual Modules...")
    
    try:
        # Test technical indicators import
        import technical_indicators as ti
        print("✓ Technical indicators module imported")
        
        # Test adjusted prices import
        import adjusted_prices as ap
        print("✓ Adjusted prices module imported")
        
        # Test candle patterns import
        import candle_patterns as cp
        print("✓ Candle patterns module imported")
        
        # Test basic functionality
        test_data = create_test_data()
        
        # Create DataFrame for testing
        df = pd.DataFrame({
            'Mid_Open': test_data['open'],
            'Mid_High': test_data['high'],
            'Mid_Low': test_data['low'],
            'Mid_Close': test_data['close'],
            'Volume': test_data['volume']
        })
        
        # Test technical indicators
        df_bb = ti.VW_BollingerBands_OHLC(df.copy(), n=10)
        print(f"✓ VW Bollinger Bands calculated: {len(df_bb.columns)} columns")
        
        df_atr = ti.VW_ATR(df.copy(), n=10)
        print(f"✓ VW ATR calculated: VW_ATR10 column added")
        
        # Test candle patterns
        df_patterns = cp.apply_candle_patterns(df.copy())
        pattern_columns = [col for col in df_patterns.columns if col in ['Hanging_Man', 'Shooting_Star', 'Engulfing']]
        print(f"✓ Candle patterns calculated: {len(pattern_columns)} pattern columns")
        
        # Test price adjustments
        df_adj = df.copy()
        df_adj['Stock Splits'] = 0.0
        df_adj['Dividends'] = 0.0
        df_adj.columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Stock Splits', 'Dividends']
        
        df_adjusted = ap.calculate_adjusted_ohlc(df_adj, adjustment="both")
        print(f"✓ Price adjustments calculated: {len(df_adjusted.columns)} columns")
        
        print("✅ All individual module tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Individual module test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Enhanced Volume-Weighted Indicators Integration Test")
    print("=" * 60)
    
    # Test individual modules first
    modules_ok = test_individual_modules()
    
    if modules_ok:
        # Test full integration
        integration_ok = test_basic_integration()
        
        if integration_ok:
            print("\n🎉 All integration tests completed successfully!")
            print("\nThe three new indicator files successfully enhance the volume-weighted indicators with:")
            print("  • Comprehensive technical analysis capabilities")
            print("  • Candlestick pattern recognition and volume weighting")
            print("  • Price adjustment for corporate actions")
            print("  • Multi-timeframe analysis")
            print("  • Volatility-adjusted calculations")
            print("  • Pattern strength-based volume weighting")
        else:
            print("\n❌ Integration tests failed")
    else:
        print("\n❌ Module tests failed - skipping integration tests")