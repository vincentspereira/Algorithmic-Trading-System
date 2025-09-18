"""
Simplified End-to-End Pipeline Test Script

This script tests the core pipeline: data fetching, indicator calculation,
and trading connection without external dependencies.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import asyncio
import sys
import os
import pandas as pd
import numpy as np

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nautilus_trader_engine.data_feeds import DataFeedManager, DataRequest, DataResponse, AssetClass
from nautilus_trader_engine.indicators.volume_weighted.volume_weighted_indicators import VolumeWeightedIndicators, MarketData
from nautilus_trader_engine.adapters.ibkr_adapter import initialize_ibkr_adapter, get_ibkr_adapter


async def test_simple_pipeline():
    """Test the simplified end-to-end pipeline."""
    print("Testing Simplified End-to-End Pipeline...")
    
    # Step 1: Initialize components
    print("\n1. Initializing components...")
    
    # Initialize data feed manager
    data_feed_manager = DataFeedManager()
    print("  ✓ Data feed manager initialized")
    
    # Initialize IBKR adapter
    ibkr_adapter = initialize_ibkr_adapter(paper_trading=True)
    print("  ✓ IBKR adapter initialized in paper trading mode")
    
    # Step 2: Fetch data via feeds
    print("\n2. Preparing mock data...")
    
    try:
        # Create mock data for testing (in a real scenario, this would fetch actual data)
        np.random.seed(42)
        n = 100
        dates = pd.date_range('2023-01-01', periods=n, freq='D')
        
        close_prices = 100 + np.cumsum(np.random.randn(n) * 0.5)
        open_prices = close_prices + np.random.randn(n) * 0.2
        high_prices = np.maximum(close_prices, open_prices) + np.abs(np.random.randn(n) * 0.3)
        low_prices = np.minimum(close_prices, open_prices) - np.abs(np.random.randn(n) * 0.3)
        volumes = np.random.randint(1000, 10000, n)
        
        mock_data = pd.DataFrame({
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': volumes
        }, index=dates)
        
        data_response = DataResponse(
            data=mock_data,
            source="yahoo_finance",  # Mock source
            ticker="AAPL",
            asset_class=AssetClass.STOCK,
            metadata={"test": True},
            timestamp=pd.Timestamp.now().timestamp(),
            success=True
        )
        
        print(f"  ✓ Mock data created with {len(mock_data)} rows")
    except Exception as e:
        print(f"  ✗ Error creating mock data: {e}")
        return False
    
    # Step 3: Calculate indicators
    print("\n3. Calculating indicators...")
    
    try:
        # Create market data object
        market_data = MarketData(
            open=data_response.data['open'],
            high=data_response.data['high'],
            low=data_response.data['low'],
            close=data_response.data['close'],
            volume=data_response.data['volume']
        )
        
        # Calculate VW SMA
        vw_sma = VolumeWeightedIndicators.vw_sma(market_data.close, market_data.volume, 20)
        print(f"  ✓ VW SMA calculated: {len(vw_sma)} values")
        
        # Calculate VW MACD
        vw_macd_line, vw_macd_signal, vw_macd_histogram = VolumeWeightedIndicators.vw_macd(
            market_data.close, market_data.volume, 12, 26, 9)
        print(f"  ✓ VW MACD calculated: {len(vw_macd_line)} values")
        
        # Calculate ATR
        atr = VolumeWeightedIndicators.atr(market_data, 14)
        print(f"  ✓ ATR calculated: {len(atr)} values")
        
    except Exception as e:
        print(f"  ✗ Error calculating indicators: {e}")
        return False
    
    # Step 4: Test paper trading connection (simulated)
    print("\n4. Testing paper trading connection...")
    
    try:
        # Connect to paper trading (simulated)
        connected = await ibkr_adapter.connect()
        if connected:
            print("  ✓ Connected to paper trading system (simulated)")
        else:
            print("  ✗ Failed to connect to paper trading system")
            return False
            
        # Get account info
        account_info = await ibkr_adapter.get_account_info()
        print(f"  ✓ Account info retrieved: {account_info['balance']} {account_info['currency']}")
        
        # Disconnect
        await ibkr_adapter.disconnect()
        print("  ✓ Disconnected from paper trading system")
        
    except Exception as e:
        print(f"  ✗ Error with paper trading connection: {e}")
        return False
    
    print("\n✓ Simplified end-to-end pipeline test completed successfully!")
    return True


if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_simple_pipeline())
    sys.exit(0 if result else 1)