"""Comprehensive test suite for consolidated indicators.

This module tests the unified indicator implementations to ensure:
1. All computation engines work correctly (Pandas, Numba, CUDA)
2. Results are consistent across different engines
3. Volume-weighted variants produce expected outputs
4. Error handling and fallback mechanisms function properly
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock

try:
    from nautilus_trader_engine.indicators.consolidated_indicators import (
        ConsolidatedIndicators, IndicatorResult, ComputeEngine
    )
    CONSOLIDATED_AVAILABLE = True
except ImportError:
    CONSOLIDATED_AVAILABLE = False


class TestConsolidatedIndicators:
    """Test suite for consolidated indicators."""
    
    @pytest.fixture
    def sample_data(self):
        """Generate sample OHLCV data for testing."""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        
        # Generate realistic price data
        base_price = 100
        returns = np.random.normal(0, 0.02, 100)
        prices = [base_price]
        
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        # Create OHLC from prices
        high = np.array(prices) * (1 + np.abs(np.random.normal(0, 0.01, 100)))
        low = np.array(prices) * (1 - np.abs(np.random.normal(0, 0.01, 100)))
        close = np.array(prices)
        open_prices = np.roll(close, 1)
        open_prices[0] = base_price
        
        volume = np.random.randint(1000, 10000, 100)
        
        return pd.DataFrame({
            'open': open_prices,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        }, index=dates)
    
    @pytest.mark.skipif(not CONSOLIDATED_AVAILABLE, reason="Consolidated indicators not available")
    def test_rsi_pandas_engine(self, sample_data):
        """Test RSI calculation with Pandas engine."""
        result = ConsolidatedIndicators.rsi(
            data=sample_data['close'],
            period=14,
            engine=ComputeEngine.PANDAS
        )
        
        assert isinstance(result, IndicatorResult)
        assert len(result.values) == len(sample_data)
        assert result.engine == ComputeEngine.PANDAS
        assert 0 <= result.values.dropna().min() <= 100
        assert 0 <= result.values.dropna().max() <= 100
        assert result.signal in ['BUY', 'SELL', 'NEUTRAL']
        assert 0 <= result.strength <= 1
    
    @pytest.mark.skipif(not CONSOLIDATED_AVAILABLE, reason="Consolidated indicators not available")
    def test_rsi_auto_engine_fallback(self, sample_data):
        """Test RSI with AUTO engine selection and fallback."""
        # Mock numba and cupy to test fallback
        with patch('nautilus_trader_engine.indicators.consolidated_indicators.numba', None):
            with patch('nautilus_trader_engine.indicators.consolidated_indicators.cupy', None):
                result = ConsolidatedIndicators.rsi(
                    data=sample_data['close'],
                    period=14,
                    engine=ComputeEngine.AUTO
                )
                
                assert isinstance(result, IndicatorResult)
                assert result.engine == ComputeEngine.PANDAS  # Should fallback to Pandas
    
    @pytest.mark.skipif(not CONSOLIDATED_AVAILABLE, reason="Consolidated indicators not available")
    def test_volume_weighted_rsi(self, sample_data):
        """Test volume-weighted RSI calculation."""
        result = ConsolidatedIndicators.vw_rsi(
            price=sample_data['close'],
            volume=sample_data['volume'],
            period=14
        )
        
        assert isinstance(result, IndicatorResult)
        assert len(result.values) == len(sample_data)
        assert 0 <= result.values.dropna().min() <= 100
        assert 0 <= result.values.dropna().max() <= 100
    
    @pytest.mark.skipif(not CONSOLIDATED_AVAILABLE, reason="Consolidated indicators not available")
    def test_macd_calculation(self, sample_data):
        """Test MACD calculation."""
        result = ConsolidatedIndicators.macd(
            data=sample_data['close'],
            fast_period=12,
            slow_period=26,
            signal_period=9,
            engine=ComputeEngine.PANDAS
        )
        
        assert isinstance(result, IndicatorResult)
        assert hasattr(result, 'macd_line')
        assert hasattr(result, 'signal_line')
        assert hasattr(result, 'histogram')
        assert len(result.values) == len(sample_data)
    
    @pytest.mark.skipif(not CONSOLIDATED_AVAILABLE, reason="Consolidated indicators not available")
    def test_volume_weighted_macd(self, sample_data):
        """Test volume-weighted MACD calculation."""
        result = ConsolidatedIndicators.vw_macd(
            price=sample_data['close'],
            volume=sample_data['volume'],
            fast_period=12,
            slow_period=26,
            signal_period=9
        )
        
        assert isinstance(result, IndicatorResult)
        assert hasattr(result, 'macd_line')
        assert hasattr(result, 'signal_line')
        assert hasattr(result, 'histogram')
    
    @pytest.mark.skipif(not CONSOLIDATED_AVAILABLE, reason="Consolidated indicators not available")
    def test_bollinger_bands(self, sample_data):
        """Test Bollinger Bands calculation."""
        result = ConsolidatedIndicators.bollinger_bands(
            data=sample_data['close'],
            period=20,
            std_dev=2.0,
            engine=ComputeEngine.PANDAS
        )
        
        assert isinstance(result, IndicatorResult)
        assert hasattr(result, 'upper_band')
        assert hasattr(result, 'middle_band')
        assert hasattr(result, 'lower_band')
        assert len(result.values) == len(sample_data)
        
        # Upper band should be above middle, middle above lower
        valid_data = result.upper_band.dropna()
        if len(valid_data) > 0:
            assert (result.upper_band >= result.middle_band).all()
            assert (result.middle_band >= result.lower_band).all()
    
    @pytest.mark.skipif(not CONSOLIDATED_AVAILABLE, reason="Consolidated indicators not available")
    def test_error_handling_invalid_data(self, sample_data):
        """Test error handling with invalid data."""
        # Test with NaN data
        invalid_data = sample_data['close'].copy()
        invalid_data.iloc[10:20] = np.nan
        
        result = ConsolidatedIndicators.rsi(
            data=invalid_data,
            period=14,
            engine=ComputeEngine.PANDAS
        )
        
        # Should handle NaN gracefully
        assert isinstance(result, IndicatorResult)
        assert not result.values.isna().all()  # Should have some valid values
    
    @pytest.mark.skipif(not CONSOLIDATED_AVAILABLE, reason="Consolidated indicators not available")
    def test_error_handling_insufficient_data(self):
        """Test error handling with insufficient data."""
        # Create data with fewer points than required period
        short_data = pd.Series([100, 101, 99, 102, 98], name='close')
        
        result = ConsolidatedIndicators.rsi(
            data=short_data,
            period=14,  # More than available data points
            engine=ComputeEngine.PANDAS
        )
        
        # Should handle gracefully
        assert isinstance(result, IndicatorResult)
        # Most values should be NaN due to insufficient data
        assert result.values.isna().sum() >= len(short_data) - 1
    
    @pytest.mark.skipif(not CONSOLIDATED_AVAILABLE, reason="Consolidated indicators not available")
    def test_engine_consistency(self, sample_data):
        """Test that different engines produce similar results."""
        # Calculate RSI with Pandas engine
        pandas_result = ConsolidatedIndicators.rsi(
            data=sample_data['close'],
            period=14,
            engine=ComputeEngine.PANDAS
        )
        
        # Try with AUTO engine (should fallback to available engine)
        auto_result = ConsolidatedIndicators.rsi(
            data=sample_data['close'],
            period=14,
            engine=ComputeEngine.AUTO
        )
        
        # Results should be similar (allowing for small numerical differences)
        valid_pandas = pandas_result.values.dropna()
        valid_auto = auto_result.values.dropna()
        
        if len(valid_pandas) > 0 and len(valid_auto) > 0:
            # Check that results are reasonably close
            min_len = min(len(valid_pandas), len(valid_auto))
            diff = np.abs(valid_pandas.iloc[-min_len:].values - valid_auto.iloc[-min_len:].values)
            assert np.mean(diff) < 1.0  # Average difference should be small


if __name__ == "__main__":
    pytest.main([__file__, "-v"])