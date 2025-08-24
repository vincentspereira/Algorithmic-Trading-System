"""
Test script for technical indicators

This script tests the volume-weighted technical indicators implementation
including VW SMA, VW EMA, VW MACD, and other custom indicators.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import sys
import os
import pandas as pd
import numpy as np

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nautilus_trader_engine.indicators.volume_weighted import VolumeWeightedIndicators, MarketData
from nautilus_trader_engine.indicators.enhanced_volume_weighted import EnhancedMarketData


def test_volume_weighted_indicators():
    """Test the volume-weighted indicators implementation."""
    print("Testing Volume-Weighted Technical Indicators...")
    
    # Create mock market data
    np.random.seed(42)  # For reproducible results
    n = 100
    dates = pd.date_range('2023-01-01', periods=n, freq='D')
    
    # Generate realistic price data
    close_prices = 100 + np.cumsum(np.random.randn(n) * 0.5)
    open_prices = close_prices + np.random.randn(n) * 0.2
    high_prices = np.maximum(close_prices, open_prices) + np.abs(np.random.randn(n) * 0.3)
    low_prices = np.minimum(close_prices, open_prices) - np.abs(np.random.randn(n) * 0.3)
    volumes = np.random.randint(1000, 10000, n)
    
    # Create market data object
    market_data = MarketData(
        open=pd.Series(open_prices, index=dates),
        high=pd.Series(high_prices, index=dates),
        low=pd.Series(low_prices, index=dates),
        close=pd.Series(close_prices, index=dates),
        volume=pd.Series(volumes, index=dates)
    )
    
    print(f"✓ Created mock market data with {n} periods")
    
    # Test VW SMA
    try:
        vw_sma_20 = VolumeWeightedIndicators.vw_sma(market_data.close, market_data.volume, 20)
        print(f"✓ VW SMA (20-period) calculated, shape: {vw_sma_20.shape}")
    except Exception as e:
        print(f"✗ Error calculating VW SMA: {e}")
        return False
    
    # Test VW EMA
    try:
        vw_ema_12 = VolumeWeightedIndicators.vw_ema(market_data.close, market_data.volume, 12)
        print(f"✓ VW EMA (12-period) calculated, shape: {vw_ema_12.shape}")
    except Exception as e:
        print(f"✗ Error calculating VW EMA: {e}")
        return False
    
    # Test VW MACD
    try:
        vw_macd_line, vw_macd_signal, vw_macd_histogram = VolumeWeightedIndicators.vw_macd(
            market_data.close, market_data.volume, 12, 26, 9)
        print(f"✓ VW MACD calculated:")
        print(f"  - MACD Line shape: {vw_macd_line.shape}")
        print(f"  - Signal Line shape: {vw_macd_signal.shape}")
        print(f"  - Histogram shape: {vw_macd_histogram.shape}")
    except Exception as e:
        print(f"✗ Error calculating VW MACD: {e}")
        return False
    
    # Test VW MFI
    try:
        vw_mfi = VolumeWeightedIndicators.vw_mfi(market_data, 14)
        print(f"✓ VW MFI (14-period) calculated, shape: {vw_mfi.shape}")
    except Exception as e:
        print(f"✗ Error calculating VW MFI: {e}")
        return False
    
    # Test Normalized ATR
    try:
        atr = VolumeWeightedIndicators.atr(market_data, 14)
        print(f"✓ ATR (14-period) calculated, shape: {atr.shape}")
    except Exception as e:
        print(f"✗ Error calculating ATR: {e}")
        return False
    
    # Test Choppy Market Index
    try:
        cmi = VolumeWeightedIndicators.choppy_market_index(market_data, 21)
        print(f"✓ Choppy Market Index (21-period) calculated, shape: {cmi.shape}")
    except Exception as e:
        print(f"✗ Error calculating Choppy Market Index: {e}")
        return False
    
    print("\nVolume-weighted indicators test completed successfully.")
    return True


def test_enhanced_indicators():
    """Test the enhanced volume-weighted indicators."""
    print("\nTesting Enhanced Volume-Weighted Technical Indicators...")
    
    # Create mock enhanced market data
    np.random.seed(42)  # For reproducible results
    n = 100
    dates = pd.date_range('2023-01-01', periods=n, freq='D')
    
    # Generate realistic price data
    close_prices = 100 + np.cumsum(np.random.randn(n) * 0.5)
    open_prices = close_prices + np.random.randn(n) * 0.2
    high_prices = np.maximum(close_prices, open_prices) + np.abs(np.random.randn(n) * 0.3)
    low_prices = np.minimum(close_prices, open_prices) - np.abs(np.random.randn(n) * 0.3)
    volumes = np.random.randint(1000, 10000, n)
    
    # Create enhanced market data object (without corporate actions for simplicity)
    enhanced_market_data = EnhancedMarketData(
        open=pd.Series(open_prices, index=dates),
        high=pd.Series(high_prices, index=dates),
        low=pd.Series(low_prices, index=dates),
        close=pd.Series(close_prices, index=dates),
        volume=pd.Series(volumes, index=dates)
    )
    
    print(f"✓ Created enhanced mock market data with {n} periods")
    
    # Test strength/weakness indicator
    try:
        strength_weakness = VolumeWeightedIndicators.strength_weakness_index(
            enhanced_market_data, 21, 21)
        print(f"✓ Strength/Weakness indicator calculated, shape: {strength_weakness.shape}")
    except Exception as e:
        print(f"✗ Error calculating Strength/Weakness indicator: {e}")
        return False
    
    print("\nEnhanced indicators test completed successfully.")
    return True


if __name__ == "__main__":
    # Run the tests
    result1 = test_volume_weighted_indicators()
    result2 = test_enhanced_indicators()
    
    if result1 and result2:
        print("\n✓ All technical indicators tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some technical indicators tests failed!")
        sys.exit(1)