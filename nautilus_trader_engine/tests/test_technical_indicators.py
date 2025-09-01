"""
Test script for technical indicators

This script tests the volume-weighted technical indicators implementation
including VW SMA, VW EMA, VW MACD, and other custom indicators.

Author: Vincent S. Pereira
Version: 1.1.0
"""

import sys
import os
import pandas as pd
import numpy as np
import pytest

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nautilus_trader_engine.indicators.volume_weighted import VolumeWeightedIndicators, MarketData
from nautilus_trader_engine.indicators.enhanced_volume_weighted import EnhancedMarketData

@pytest.fixture
def market_data():
    """Provides mock market data for testing."""
    np.random.seed(42)  # For reproducible results
    n = 100
    dates = pd.date_range('2023-01-01', periods=n, freq='D')
    
    close_prices = 100 + np.cumsum(np.random.randn(n) * 0.5)
    open_prices = close_prices + np.random.randn(n) * 0.2
    high_prices = np.maximum(close_prices, open_prices) + np.abs(np.random.randn(n) * 0.3)
    low_prices = np.minimum(close_prices, open_prices) - np.abs(np.random.randn(n) * 0.3)
    volumes = np.random.randint(1000, 10000, n)
    
    return MarketData(
        open=pd.Series(open_prices, index=dates),
        high=pd.Series(high_prices, index=dates),
        low=pd.Series(low_prices, index=dates),
        close=pd.Series(close_prices, index=dates),
        volume=pd.Series(volumes, index=dates)
    )

@pytest.fixture
def enhanced_market_data():
    """Provides mock enhanced market data for testing."""
    np.random.seed(42)
    n = 100
    dates = pd.date_range('2023-01-01', periods=n, freq='D')
    
    close_prices = 100 + np.cumsum(np.random.randn(n) * 0.5)
    open_prices = close_prices + np.random.randn(n) * 0.2
    high_prices = np.maximum(close_prices, open_prices) + np.abs(np.random.randn(n) * 0.3)
    low_prices = np.minimum(close_prices, open_prices) - np.abs(np.random.randn(n) * 0.3)
    volumes = np.random.randint(1000, 10000, n)
    
    return EnhancedMarketData(
        open=pd.Series(open_prices, index=dates),
        high=pd.Series(high_prices, index=dates),
        low=pd.Series(low_prices, index=dates),
        close=pd.Series(close_prices, index=dates),
        volume=pd.Series(volumes, index=dates)
    )

def test_vw_sma(market_data):
    """Tests the Volume-Weighted Simple Moving Average (VW SMA) indicator."""
    vw_sma_20 = VolumeWeightedIndicators.vw_sma(market_data.close, market_data.volume, 20)
    assert isinstance(vw_sma_20, pd.Series)
    assert not vw_sma_20.isnull().all()
    assert len(vw_sma_20) == len(market_data.close)
    # Check a known value
    assert np.isclose(vw_sma_20.iloc[25], 99.8394, atol=1e-4)

def test_vw_ema(market_data):
    """Tests the Volume-Weighted Exponential Moving Average (VW EMA) indicator."""
    vw_ema_12 = VolumeWeightedIndicators.vw_ema(market_data.close, market_data.volume, 12)
    assert isinstance(vw_ema_12, pd.Series)
    assert not vw_ema_12.isnull().all()
    assert len(vw_ema_12) == len(market_data.close)

def test_vw_macd(market_data):
    """Tests the Volume-Weighted Moving Average Convergence Divergence (VW MACD) indicator."""
    vw_macd_line, vw_macd_signal, vw_macd_histogram = VolumeWeightedIndicators.vw_macd(
        market_data.close, market_data.volume, 12, 26, 9)
    assert isinstance(vw_macd_line, pd.Series)
    assert isinstance(vw_macd_signal, pd.Series)
    assert isinstance(vw_macd_histogram, pd.Series)
    assert not vw_macd_line.isnull().all()
    assert not vw_macd_signal.isnull().all()
    assert not vw_macd_histogram.isnull().all()

def test_vw_mfi(market_data):
    """Tests the Volume-Weighted Money Flow Index (VW MFI) indicator."""
    vw_mfi = VolumeWeightedIndicators.vw_mfi(market_data, 14)
    assert isinstance(vw_mfi, pd.Series)
    assert not vw_mfi.isnull().all()

def test_atr(market_data):
    """Tests the Average True Range (ATR) indicator."""
    atr = VolumeWeightedIndicators.atr(market_data, 14)
    assert isinstance(atr, pd.Series)
    assert not atr.isnull().all()

def test_choppy_market_index(market_data):
    """Tests the Choppy Market Index (CMI) indicator."""
    cmi = VolumeWeightedIndicators.choppy_market_index(market_data, 21)
    assert isinstance(cmi, pd.Series)
    assert not cmi.isnull().all()

def test_strength_weakness_index(enhanced_market_data):
    """Tests the Strength/Weakness Index indicator."""
    strength_weakness = VolumeWeightedIndicators.strength_weakness_index(
        enhanced_market_data, 21, 21)
    assert isinstance(strength_weakness, pd.Series)
    assert not strength_weakness.isnull().all()
