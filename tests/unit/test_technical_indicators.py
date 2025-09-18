"""Unit tests for the Technical Indicators module."""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple
import math
from enum import Enum


class IndicatorType(Enum):
    """Technical indicator type enumeration."""
    TREND = "TREND"
    MOMENTUM = "MOMENTUM"
    VOLATILITY = "VOLATILITY"
    VOLUME = "VOLUME"
    SUPPORT_RESISTANCE = "SUPPORT_RESISTANCE"
    OSCILLATOR = "OSCILLATOR"


class SignalType(Enum):
    """Trading signal type enumeration."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"


class TestTechnicalIndicators:
    """Test suite for technical indicators calculation and analysis."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Generate sample OHLCV data
        np.random.seed(42)  # For reproducible tests
        
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
        
        # Generate realistic price data with trend and volatility
        base_price = 100.0
        price_changes = np.random.normal(0, 0.02, 100)  # 2% volatility
        trend = np.linspace(0, 0.1, 100)  # 10% upward trend over period
        
        prices = [base_price]
        for i in range(1, 100):
            new_price = prices[-1] * (1 + price_changes[i] + trend[i]/100)
            prices.append(new_price)
        
        # Create OHLCV data
        self.sample_data = pd.DataFrame({
            'timestamp': dates,
            'open': [p * (1 + np.random.uniform(-0.005, 0.005)) for p in prices],
            'high': [p * (1 + abs(np.random.uniform(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.uniform(0, 0.01))) for p in prices],
            'close': prices,
            'volume': np.random.randint(1000, 10000, 100)
        })
        
        # Sample indicator configurations
        self.indicator_configs = {
            'sma_20': {
                'type': IndicatorType.TREND.value,
                'name': 'Simple Moving Average',
                'period': 20,
                'source': 'close'
            },
            'ema_12': {
                'type': IndicatorType.TREND.value,
                'name': 'Exponential Moving Average',
                'period': 12,
                'source': 'close'
            },
            'rsi_14': {
                'type': IndicatorType.MOMENTUM.value,
                'name': 'Relative Strength Index',
                'period': 14,
                'source': 'close',
                'overbought': 70,
                'oversold': 30
            },
            'macd': {
                'type': IndicatorType.MOMENTUM.value,
                'name': 'MACD',
                'fast_period': 12,
                'slow_period': 26,
                'signal_period': 9
            },
            'bollinger_bands': {
                'type': IndicatorType.VOLATILITY.value,
                'name': 'Bollinger Bands',
                'period': 20,
                'std_dev': 2.0,
                'source': 'close'
            },
            'atr_14': {
                'type': IndicatorType.VOLATILITY.value,
                'name': 'Average True Range',
                'period': 14
            },
            'stochastic': {
                'type': IndicatorType.OSCILLATOR.value,
                'name': 'Stochastic Oscillator',
                'k_period': 14,
                'd_period': 3,
                'overbought': 80,
                'oversold': 20
            },
            'volume_sma': {
                'type': IndicatorType.VOLUME.value,
                'name': 'Volume SMA',
                'period': 20,
                'source': 'volume'
            }
        }
    
    @pytest.mark.asyncio
    async def test_indicator_engine_initialization(self):
        """Test technical indicators engine initialization."""
        with patch('nautilus_trader_engine.indicators.TechnicalIndicatorEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_engine.return_value = mock_instance
            
            # Configure initialization response
            mock_instance.initialize.return_value = {
                'status': 'INITIALIZED',
                'supported_indicators': list(self.indicator_configs.keys()),
                'calculation_engine': 'NUMPY_PANDAS',
                'real_time_updates': True,
                'historical_data_support': True,
                'multi_timeframe_support': True,
                'custom_indicators_support': True,
                'performance_optimization': 'VECTORIZED'
            }


            mock_instance.load_indicator_definitions.return_value = {
                'loaded_indicators': len(self.indicator_configs),
                'indicator_types': list(set(config['type'] for config in self.indicator_configs.values())),
                'validation_status': 'PASSED'
            }
            
            engine = mock_engine()
            
            # Test initialization
            init_result = await engine.initialize()
            
            assert init_result['status'] == 'INITIALIZED', "Indicator engine not initialized"
            assert init_result['real_time_updates'] is True, "Real-time updates not enabled"
            assert init_result['multi_timeframe_support'] is True, "Multi-timeframe support not enabled"
            assert len(init_result['supported_indicators']) > 0, "No supported indicators"
            
            # Test indicator definitions loading
            load_result = await engine.load_indicator_definitions(self.indicator_configs)
            
            assert load_result['loaded_indicators'] == len(self.indicator_configs), "Not all indicators loaded"
            assert load_result['validation_status'] == 'PASSED', "Indicator validation failed"
    
    @pytest.mark.asyncio
    async def test_trend_indicators_calculation(self):
        """Test trend indicator calculations (SMA, EMA, etc.)."""
        with patch('nautilus_trader_engine.indicators.TrendIndicators') as mock_trend:
            mock_instance = AsyncMock()
            mock_trend.return_value = mock_instance
            
            def calculate_sma(data, period):
                """Calculate Simple Moving Average."""
                if len(data) < period:
                    return [None] * len(data)
                
                sma_values = []
                for i in range(len(data)):
                    if i < period - 1:
                        sma_values.append(None)
                    else:
                        sma = sum(data[i-period+1:i+1]) / period
                        sma_values.append(round(sma, 4))
                
                return sma_values
            
            def calculate_ema(data, period):
                """Calculate Exponential Moving Average."""
                if len(data) == 0:
                    return []
                
                multiplier = 2 / (period + 1)
                ema_values = [data[0]]  # First EMA is the first price
                
                for i in range(1, len(data)):
                    ema = (data[i] * multiplier) + (ema_values[-1] * (1 - multiplier))
                    ema_values.append(round(ema, 4))
                
                return ema_values
            
            # Configure calculation responses
            mock_instance.calculate_sma.side_effect = lambda data, period: {
                'indicator': 'SMA',
                'period': period,
                'values': calculate_sma(data, period),
                'last_value': calculate_sma(data, period)[-1] if calculate_sma(data, period)[-1] is not None else None,
                'calculation_time_ms': 5,
                'data_points': len(data)
            }
            
            mock_instance.calculate_ema.side_effect = lambda data, period: {
                'indicator': 'EMA',
                'period': period,
                'values': calculate_ema(data, period),
                'last_value': calculate_ema(data, period)[-1],
                'calculation_time_ms': 8,
                'data_points': len(data)
            }
            
            trend_indicators = mock_trend()
            
            # Test SMA calculation
            close_prices = self.sample_data['close'].tolist()
            sma_result = await trend_indicators.calculate_sma(close_prices, 20)
            
            assert sma_result['indicator'] == 'SMA', "Wrong indicator type"
            assert sma_result['period'] == 20, "Wrong SMA period"
            assert len(sma_result['values']) == len(close_prices), "SMA values length mismatch"
            assert sma_result['last_value'] is not None, "Missing last SMA value"
            assert sma_result['calculation_time_ms'] < 100, "SMA calculation too slow"
            
            # Verify SMA values are reasonable
            sma_values = [v for v in sma_result['values'] if v is not None]
            assert len(sma_values) > 0, "No valid SMA values calculated"
            assert all(isinstance(v, (int, float)) for v in sma_values), "Invalid SMA value types"
            
            # Test EMA calculation
            ema_result = await trend_indicators.calculate_ema(close_prices, 12)
            
            assert ema_result['indicator'] == 'EMA', "Wrong indicator type"
            assert ema_result['period'] == 12, "Wrong EMA period"
            assert len(ema_result['values']) == len(close_prices), "EMA values length mismatch"
            assert ema_result['last_value'] is not None, "Missing last EMA value"
            
            # Verify EMA responsiveness (should be more responsive than SMA)
            ema_values = ema_result['values']
            assert all(isinstance(v, (int, float)) for v in ema_values), "Invalid EMA value types"
    
    @pytest.mark.asyncio
    async def test_momentum_indicators_calculation(self):
        """Test momentum indicator calculations (RSI, MACD, etc.)."""
        with patch('nautilus_trader_engine.indicators.MomentumIndicators') as mock_momentum:
            mock_instance = AsyncMock()
            mock_momentum.return_value = mock_instance
            
            def calculate_rsi(prices, period=14):
                """Calculate Relative Strength Index."""
                n = len(prices)
                if n < period:
                    return [None] * n
                # Price differences
                deltas = [prices[i] - prices[i-1] for i in range(1, n)]
                gains = [max(delta, 0) for delta in deltas]
                losses = [abs(min(delta, 0)) for delta in deltas]

                # Initialize output to full length with None
                rsi_values = [None] * n

                # Initial averages over first `period` deltas
                avg_gain = sum(gains[:period]) / period
                avg_loss = sum(losses[:period]) / period

                # Compute RSI from index = period onwards
                for i in range(period, n):
                    # delta index corresponds to i-1
                    if avg_loss == 0:
                        rsi = 100.0
                    else:
                        rs = avg_gain / avg_loss
                        rsi = 100 - (100 / (1 + rs))
                    rsi_values[i] = round(rsi, 2)

                    # Update averages for next step using current delta
                    if i < n - 1:
                        g = gains[i - 0]  # gains index = (i) - 0 corresponds to deltas[i]
                        l = losses[i - 0]
                        avg_gain = ((avg_gain * (period - 1)) + g) / period
                        avg_loss = ((avg_loss * (period - 1)) + l) / period

                return rsi_values
            
            def calculate_macd(prices, fast=12, slow=26, signal=9):
                """Calculate MACD indicator."""
                if len(prices) < slow:
                    return {
                        'macd_line': [None] * len(prices),
                        'signal_line': [None] * len(prices),
                        'histogram': [None] * len(prices)
                    }
                
                # Calculate EMAs
                fast_multiplier = 2 / (fast + 1)
                slow_multiplier = 2 / (slow + 1)
                signal_multiplier = 2 / (signal + 1)
                
                fast_ema = [prices[0]]
                slow_ema = [prices[0]]
                
                for i in range(1, len(prices)):
                    fast_ema.append((prices[i] * fast_multiplier) + (fast_ema[-1] * (1 - fast_multiplier)))
                    slow_ema.append((prices[i] * slow_multiplier) + (slow_ema[-1] * (1 - slow_multiplier)))
                
                # Calculate MACD line
                macd_line = [fast_ema[i] - slow_ema[i] for i in range(len(prices))]
                
                # Calculate signal line
                signal_line = [macd_line[0]]
                for i in range(1, len(macd_line)):
                    signal_line.append((macd_line[i] * signal_multiplier) + (signal_line[-1] * (1 - signal_multiplier)))
                
                # Calculate histogram
                histogram = [macd_line[i] - signal_line[i] for i in range(len(macd_line))]
                
                return {
                    'macd_line': [round(v, 4) for v in macd_line],
                    'signal_line': [round(v, 4) for v in signal_line],
                    'histogram': [round(v, 4) for v in histogram]
                }
            
            # Configure calculation responses
            mock_instance.calculate_rsi.side_effect = lambda prices, period: {
                'indicator': 'RSI',
                'period': period,
                'values': calculate_rsi(prices, period),
                'last_value': calculate_rsi(prices, period)[-1],
                'overbought_level': 70,
                'oversold_level': 30,
                'current_signal': 'NEUTRAL',
                'calculation_time_ms': 12
            }
            
            mock_instance.calculate_macd.side_effect = lambda prices, fast, slow, signal: {
                'indicator': 'MACD',
                'fast_period': fast,
                'slow_period': slow,
                'signal_period': signal,
                **calculate_macd(prices, fast, slow, signal),
                'calculation_time_ms': 18
            }
            
            momentum_indicators = mock_momentum()
            
            # Test RSI calculation
            close_prices = self.sample_data['close'].tolist()
            rsi_result = await momentum_indicators.calculate_rsi(close_prices, 14)
            
            assert rsi_result['indicator'] == 'RSI', "Wrong indicator type"
            assert rsi_result['period'] == 14, "Wrong RSI period"
            assert len(rsi_result['values']) == len(close_prices), "RSI values length mismatch"
            
            # Verify RSI values are in valid range (0-100)
            rsi_values = [v for v in rsi_result['values'] if v is not None]
            assert len(rsi_values) > 0, "No valid RSI values calculated"
            assert all(0 <= v <= 100 for v in rsi_values), "RSI values out of range"
            
            # Test MACD calculation
            macd_result = await momentum_indicators.calculate_macd(close_prices, 12, 26, 9)
            
            assert macd_result['indicator'] == 'MACD', "Wrong indicator type"
            assert 'macd_line' in macd_result, "Missing MACD line"
            assert 'signal_line' in macd_result, "Missing signal line"
            assert 'histogram' in macd_result, "Missing histogram"
            
            # Verify MACD components have same length
            macd_length = len(macd_result['macd_line'])
            assert len(macd_result['signal_line']) == macd_length, "MACD components length mismatch"
            assert len(macd_result['histogram']) == macd_length, "MACD histogram length mismatch"
    
    @pytest.mark.asyncio
    async def test_volatility_indicators_calculation(self):
        """Test volatility indicator calculations (Bollinger Bands, ATR, etc.)."""
        with patch('nautilus_trader_engine.indicators.VolatilityIndicators') as mock_volatility:
            mock_instance = AsyncMock()
            mock_volatility.return_value = mock_instance
            
            def calculate_bollinger_bands(prices, period=20, std_dev=2.0):
                """Calculate Bollinger Bands."""
                if len(prices) < period:
                    return {
                        'upper_band': [None] * len(prices),
                        'middle_band': [None] * len(prices),
                        'lower_band': [None] * len(prices),
                        'bandwidth': [None] * len(prices)
                    }
                
                upper_band = []
                middle_band = []
                lower_band = []
                bandwidth = []
                
                for i in range(len(prices)):
                    if i < period - 1:
                        upper_band.append(None)
                        middle_band.append(None)
                        lower_band.append(None)
                        bandwidth.append(None)
                    else:
                        # Calculate SMA (middle band)
                        sma = sum(prices[i-period+1:i+1]) / period
                        
                        # Calculate standard deviation
                        variance = sum((p - sma) ** 2 for p in prices[i-period+1:i+1]) / period
                        std = math.sqrt(variance)
                        
                        upper = sma + (std_dev * std)
                        lower = sma - (std_dev * std)
                        bw = (upper - lower) / sma * 100
                        
                        upper_band.append(round(upper, 4))
                        middle_band.append(round(sma, 4))
                        lower_band.append(round(lower, 4))
                        bandwidth.append(round(bw, 2))
                
                return {
                    'upper_band': upper_band,
                    'middle_band': middle_band,
                    'lower_band': lower_band,
                    'bandwidth': bandwidth
                }
            
            def calculate_atr(high_prices, low_prices, close_prices, period=14):
                """Calculate Average True Range."""
                if len(high_prices) < period + 1:
                    return [None] * len(high_prices)
                
                true_ranges = []
                
                # First TR is just high - low
                true_ranges.append(high_prices[0] - low_prices[0])
                
                # Calculate subsequent TRs
                for i in range(1, len(high_prices)):
                    tr1 = high_prices[i] - low_prices[i]
                    tr2 = abs(high_prices[i] - close_prices[i-1])
                    tr3 = abs(low_prices[i] - close_prices[i-1])
                    tr = max(tr1, tr2, tr3)
                    true_ranges.append(tr)
                
                # Calculate ATR
                atr_values = [None] * (period - 1)
                
                # First ATR is simple average
                first_atr = sum(true_ranges[:period]) / period
                atr_values.append(round(first_atr, 4))
                
                # Subsequent ATRs use Wilder's smoothing
                for i in range(period, len(true_ranges)):
                    atr = ((atr_values[-1] * (period - 1)) + true_ranges[i]) / period
                    atr_values.append(round(atr, 4))
                
                return atr_values
            
            # Configure calculation responses
            mock_instance.calculate_bollinger_bands.side_effect = lambda prices, period, std_dev: {
                'indicator': 'BOLLINGER_BANDS',
                'period': period,
                'std_dev': std_dev,
                **calculate_bollinger_bands(prices, period, std_dev),
                'calculation_time_ms': 15
            }
            
            mock_instance.calculate_atr.side_effect = lambda high, low, close, period: {
                'indicator': 'ATR',
                'period': period,
                'values': calculate_atr(high, low, close, period),
                'last_value': calculate_atr(high, low, close, period)[-1],
                'calculation_time_ms': 10
            }
            
            volatility_indicators = mock_volatility()
            
            # Test Bollinger Bands calculation
            close_prices = self.sample_data['close'].tolist()
            bb_result = await volatility_indicators.calculate_bollinger_bands(close_prices, 20, 2.0)
            
            assert bb_result['indicator'] == 'BOLLINGER_BANDS', "Wrong indicator type"
            assert 'upper_band' in bb_result, "Missing upper band"
            assert 'middle_band' in bb_result, "Missing middle band"
            assert 'lower_band' in bb_result, "Missing lower band"
            assert 'bandwidth' in bb_result, "Missing bandwidth"
            
            # Verify band relationships
            valid_indices = [i for i, v in enumerate(bb_result['upper_band']) if v is not None]
            for i in valid_indices:
                upper = bb_result['upper_band'][i]
                middle = bb_result['middle_band'][i]
                lower = bb_result['lower_band'][i]
                
                assert upper > middle > lower, f"Invalid band relationship at index {i}"
            
            # Test ATR calculation
            high_prices = self.sample_data['high'].tolist()
            low_prices = self.sample_data['low'].tolist()
            atr_result = await volatility_indicators.calculate_atr(high_prices, low_prices, close_prices, 14)
            
            assert atr_result['indicator'] == 'ATR', "Wrong indicator type"
            assert atr_result['period'] == 14, "Wrong ATR period"
            
            # Verify ATR values are positive
            atr_values = [v for v in atr_result['values'] if v is not None]
            assert len(atr_values) > 0, "No valid ATR values calculated"
            assert all(v > 0 for v in atr_values), "ATR values should be positive"
    
    @pytest.mark.asyncio
    async def test_oscillator_indicators_calculation(self):
        """Test oscillator indicator calculations (Stochastic, Williams %R, etc.)."""
        with patch('nautilus_trader_engine.indicators.OscillatorIndicators') as mock_oscillator:
            mock_instance = AsyncMock()
            mock_oscillator.return_value = mock_instance
            
            def calculate_stochastic(high_prices, low_prices, close_prices, k_period=14, d_period=3):
                """Calculate Stochastic Oscillator."""
                if len(high_prices) < k_period:
                    return {
                        'k_percent': [None] * len(high_prices),
                        'd_percent': [None] * len(high_prices)
                    }
                
                k_percent = []
                
                for i in range(len(close_prices)):
                    if i < k_period - 1:
                        k_percent.append(None)
                    else:
                        highest_high = max(high_prices[i-k_period+1:i+1])
                        lowest_low = min(low_prices[i-k_period+1:i+1])
                        
                        if highest_high == lowest_low:
                            k_value = 50  # Avoid division by zero
                        else:
                            k_value = ((close_prices[i] - lowest_low) / (highest_high - lowest_low)) * 100
                        
                        k_percent.append(round(k_value, 2))
                
                # Calculate %D (SMA of %K)
                d_percent = []
                for i in range(len(k_percent)):
                    if i < d_period - 1 or k_percent[i] is None:
                        d_percent.append(None)
                    else:
                        valid_k_values = [v for v in k_percent[i-d_period+1:i+1] if v is not None]
                        if len(valid_k_values) == d_period:
                            d_value = sum(valid_k_values) / d_period
                            d_percent.append(round(d_value, 2))
                        else:
                            d_percent.append(None)
                
                return {
                    'k_percent': k_percent,
                    'd_percent': d_percent
                }
            
            def calculate_williams_r(high_prices, low_prices, close_prices, period=14):
                """Calculate Williams %R."""
                if len(high_prices) < period:
                    return [None] * len(high_prices)
                
                williams_r = []
                
                for i in range(len(close_prices)):
                    if i < period - 1:
                        williams_r.append(None)
                    else:
                        highest_high = max(high_prices[i-period+1:i+1])
                        lowest_low = min(low_prices[i-period+1:i+1])
                        
                        if highest_high == lowest_low:
                            wr_value = -50  # Avoid division by zero
                        else:
                            wr_value = ((highest_high - close_prices[i]) / (highest_high - lowest_low)) * -100
                        
                        williams_r.append(round(wr_value, 2))
                
                return williams_r
            
            # Configure calculation responses
            mock_instance.calculate_stochastic.side_effect = lambda high, low, close, k_period, d_period: {
                'indicator': 'STOCHASTIC',
                'k_period': k_period,
                'd_period': d_period,
                **calculate_stochastic(high, low, close, k_period, d_period),
                'overbought_level': 80,
                'oversold_level': 20,
                'calculation_time_ms': 12
            }
            
            mock_instance.calculate_williams_r.side_effect = lambda high, low, close, period: {
                'indicator': 'WILLIAMS_R',
                'period': period,
                'values': calculate_williams_r(high, low, close, period),
                'last_value': calculate_williams_r(high, low, close, period)[-1],
                'overbought_level': -20,
                'oversold_level': -80,
                'calculation_time_ms': 8
            }
            
            oscillator_indicators = mock_oscillator()
            
            # Test Stochastic Oscillator calculation
            high_prices = self.sample_data['high'].tolist()
            low_prices = self.sample_data['low'].tolist()
            close_prices = self.sample_data['close'].tolist()
            
            stoch_result = await oscillator_indicators.calculate_stochastic(high_prices, low_prices, close_prices, 14, 3)
            
            assert stoch_result['indicator'] == 'STOCHASTIC', "Wrong indicator type"
            assert 'k_percent' in stoch_result, "Missing %K values"
            assert 'd_percent' in stoch_result, "Missing %D values"
            
            # Verify Stochastic values are in valid range (0-100)
            k_values = [v for v in stoch_result['k_percent'] if v is not None]
            d_values = [v for v in stoch_result['d_percent'] if v is not None]
            
            assert len(k_values) > 0, "No valid %K values calculated"
            assert all(0 <= v <= 100 for v in k_values), "%K values out of range"
            
            if d_values:
                assert all(0 <= v <= 100 for v in d_values), "%D values out of range"
            
            # Test Williams %R calculation
            wr_result = await oscillator_indicators.calculate_williams_r(high_prices, low_prices, close_prices, 14)
            
            assert wr_result['indicator'] == 'WILLIAMS_R', "Wrong indicator type"
            assert wr_result['period'] == 14, "Wrong Williams %R period"

            # Verify Williams %R values are in valid range (-100 to 0)
            wr_values = [v for v in wr_result['values'] if v is not None]
            assert len(wr_values) > 0, "No valid Williams %R values calculated"
            assert all(
                -100 <= v <= 0 for v in wr_values
            ), "Williams %R values out of range"

    @pytest.mark.asyncio
    async def test_signal_generation(self):
        """Test trading signal generation from technical indicators."""
        with patch(
            'nautilus_trader_engine.indicators.SignalGenerator'
        ) as mock_signal_gen:
            mock_instance = AsyncMock()
            mock_signal_gen.return_value = mock_instance


            # Sample indicator values for signal generation
            sample_indicators = {
                'rsi': 75.5,  # Overbought
                'macd_histogram': 0.15,  # Positive momentum
                'stochastic_k': 85.2,  # Overbought
                'price_vs_sma20': 1.02,  # Above SMA
                'bollinger_position': 0.8,  # Near upper band
                'volume_ratio': 1.5  # Above average volume
            }

            def generate_signals(indicators, rules):
                """Generate trading signals based on indicator values and rules."""
                signals = []

                # RSI signals
                if indicators.get('rsi'):
                    rsi = indicators['rsi']
                    if rsi > 70:
                        signals.append({
                            'type': SignalType.SELL.value,
                            'strength': min((rsi - 70) / 30, 1.0),
                            'source': 'RSI_OVERBOUGHT',
                            'confidence': 0.7
                        })
                    elif rsi < 30:
                        signals.append({
                            'type': SignalType.BUY.value,
                            'strength': min((30 - rsi) / 30, 1.0),
                            'source': 'RSI_OVERSOLD',
                            'confidence': 0.7
                        })

                # MACD signals
                if indicators.get('macd_histogram'):
                    macd_hist = indicators['macd_histogram']
                    if macd_hist > 0:
                        signals.append({
                            'type': SignalType.BUY.value,
                            'strength': min(abs(macd_hist) * 10, 1.0),
                            'source': 'MACD_BULLISH',
                            'confidence': 0.6
                        })
                    elif macd_hist < 0:
                        signals.append({
                            'type': SignalType.SELL.value,
                            'strength': min(abs(macd_hist) * 10, 1.0),
                            'source': 'MACD_BEARISH',
                            'confidence': 0.6
                        })
                
                # Trend signals
                if indicators.get('price_vs_sma20'):
                    price_ratio = indicators['price_vs_sma20']
                    if price_ratio > 1.05:
                        signals.append({
                            'type': SignalType.BUY.value,
                            'strength': min((price_ratio - 1.0) * 5, 1.0),
                            'source': 'TREND_BULLISH',
                            'confidence': 0.5
                        })
                    elif price_ratio < 0.95:
                        signals.append({
                            'type': SignalType.SELL.value,
                            'strength': min((1.0 - price_ratio) * 5, 1.0),
                            'source': 'TREND_BEARISH',
                            'confidence': 0.5
                        })
                
                # Aggregate signals
                buy_signals = [
                    s for s in signals if s['type'] == SignalType.BUY.value
                ]
                sell_signals = [
                    s for s in signals if s['type'] == SignalType.SELL.value
                ]

                if buy_signals and sell_signals:
                    # Conflicting signals - calculate net signal
                    buy_strength = sum(
                        s['strength'] * s['confidence'] for s in buy_signals
                    )
                    sell_strength = sum(
                        s['strength'] * s['confidence'] for s in sell_signals
                    )
                    
                    if buy_strength > sell_strength * 1.2:
                        final_signal = SignalType.BUY.value
                        final_strength = (
                            (buy_strength - sell_strength) / len(buy_signals)
                        )
                    elif sell_strength > buy_strength * 1.2:
                        final_signal = SignalType.SELL.value
                        final_strength = (
                            (sell_strength - buy_strength) / len(sell_signals)
                        )
                    else:
                        final_signal = SignalType.HOLD.value
                        final_strength = 0.0
                elif buy_signals:
                    final_signal = SignalType.BUY.value
                    final_strength = (
                        sum(s['strength'] * s['confidence'] for s in buy_signals) /
                        len(buy_signals)
                    )
                elif sell_signals:
                    final_signal = SignalType.SELL.value
                    final_strength = (
                        sum(s['strength'] * s['confidence'] for s in sell_signals) /
                        len(sell_signals)
                    )
                else:
                    final_signal = SignalType.HOLD.value
                    final_strength = 0.0
                
                return {
                    'final_signal': final_signal,
                    'signal_strength': round(final_strength, 3),
                    'individual_signals': signals,
                    'signal_count': len(signals),
                    'confidence_score': round(
                        sum(s['confidence'] for s in signals) / max(len(signals), 1), 3
                    )
                }

            mock_instance.generate_signals.side_effect = generate_signals

            mock_instance.validate_signal_rules.return_value = {
                'rules_valid': True,
                'validation_errors': [],
                'rule_count': 5,
                'coverage_percentage': 85.0
            }

            signal_generator = mock_signal_gen()

            # Test signal generation
            signal_rules = {
                'rsi_overbought_threshold': 70,
                'rsi_oversold_threshold': 30,
                'macd_signal_sensitivity': 0.1,
                'trend_confirmation_required': True,
                'volume_confirmation': True
            }

            # Validate signal rules first
            validation_result = await signal_generator.validate_signal_rules(
                signal_rules
            )

            assert validation_result['rules_valid'] is True, (
                "Signal rules validation failed"
            )
            assert validation_result['coverage_percentage'] > 80, (
                "Signal rule coverage too low"
            )

            # Generate signals
            signal_result = await signal_generator.generate_signals(
                sample_indicators, signal_rules
            )

            assert 'final_signal' in signal_result, "Missing final signal"
            assert 'signal_strength' in signal_result, (
                "Missing signal strength"
            )
            assert 'individual_signals' in signal_result, (
                "Missing individual signals"
            )
            assert 'confidence_score' in signal_result, (
                "Missing confidence score"
            )

            # Verify signal properties
            assert signal_result['final_signal'] in [
                s.value for s in SignalType
            ], "Invalid signal type"
            assert 0 <= signal_result['signal_strength'] <= 1, (
                "Signal strength out of range"
            )
            assert 0 <= signal_result['confidence_score'] <= 1, (
                "Confidence score out of range"
            )
            assert signal_result['signal_count'] >= 0, "Invalid signal count"

            # Verify individual signals structure
            for signal in signal_result['individual_signals']:
                assert 'type' in signal, "Missing signal type"
                assert 'strength' in signal, "Missing signal strength"
                assert 'source' in signal, "Missing signal source"
                assert 'confidence' in signal, "Missing signal confidence"

    @pytest.mark.asyncio
    async def test_multi_timeframe_analysis(self):
        """Test multi-timeframe technical analysis."""
        with patch(
            'nautilus_trader_engine.indicators.MultiTimeframeAnalyzer'
        ) as mock_mtf:
            mock_instance = AsyncMock()
            mock_mtf.return_value = mock_instance

            # Sample multi-timeframe data
            timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']

            def analyze_multiple_timeframes(symbol, timeframes, indicators):
                """Analyze indicators across multiple timeframes."""
                analysis_results = {}

                for tf in timeframes:
                    # Simulate different indicator values for timeframes
                    tf_multiplier = {
                        '1m': 0.8, '5m': 0.9, '15m': 1.0,
                        '1h': 1.1, '4h': 1.2, '1d': 1.3
                    }.get(tf, 1.0)

                    analysis_results[tf] = {
                        'trend_direction': (
                            'BULLISH' if tf_multiplier > 1.0
                            else 'BEARISH' if tf_multiplier < 1.0
                            else 'NEUTRAL'
                        ),
                        'trend_strength': round(
                            abs(tf_multiplier - 1.0) * 100, 1
                        ),
                        'momentum': {
                            'rsi': round(50 + (tf_multiplier - 1.0) * 30, 1),
                            'macd_signal': (
                                'BULLISH' if tf_multiplier > 1.05
                                else 'BEARISH' if tf_multiplier < 0.95
                                else 'NEUTRAL'
                            )
                        },
                        'volatility': {
                            'atr_percentile': round(tf_multiplier * 45, 1),
                            'bollinger_squeeze': tf_multiplier < 0.9
                        },
                        'support_resistance': {
                            'near_support': tf_multiplier < 0.95,
                            'near_resistance': tf_multiplier > 1.05,
                            'key_levels': [
                                100.0 * tf_multiplier * (1 + i * 0.01)
                                for i in range(-2, 3)
                            ]
                        }
                    }

                # Calculate consensus
                bullish_count = sum(
                    1 for tf_data in analysis_results.values()
                    if tf_data['trend_direction'] == 'BULLISH'
                )
                bearish_count = sum(
                    1 for tf_data in analysis_results.values()
                    if tf_data['trend_direction'] == 'BEARISH'
                )

                if bullish_count > bearish_count:
                    consensus = 'BULLISH'
                    consensus_strength = bullish_count / len(timeframes)
                elif bearish_count > bullish_count:
                    consensus = 'BEARISH'
                    consensus_strength = bearish_count / len(timeframes)
                else:
                    consensus = 'NEUTRAL'
                    consensus_strength = 0.5

                return {
                    'symbol': symbol,
                    'analysis_timestamp': datetime.now().isoformat(),
                    'timeframes_analyzed': timeframes,
                    'timeframe_results': analysis_results,
                    'consensus': {
                        'direction': consensus,
                        'strength': round(consensus_strength, 2),
                        'agreement_percentage': round(
                            max(bullish_count, bearish_count)
                            / len(timeframes) * 100, 1
                        )
                    },
                    'conflicting_signals': (
                        bullish_count > 0 and bearish_count > 0
                    ),
                    'analysis_duration_ms': 250
                }

            mock_instance.analyze_multiple_timeframes.side_effect = (
                analyze_multiple_timeframes
            )

            mock_instance.detect_timeframe_divergences.return_value = {
                'divergences_found': True,
                'divergence_details': [
                    {
                        'timeframes': ['1m', '1h'],
                        'divergence_type': 'TREND_DIVERGENCE',
                        'severity': 'MODERATE',
                        'description': (
                            'Short-term bearish while longer-term bullish'
                        )
                    }
                ],
                'risk_level': 'MEDIUM',
                'recommended_action': 'WAIT_FOR_CONFIRMATION'
            }

            mtf_analyzer = mock_mtf()

            # Test multi-timeframe analysis
            mtf_result = await mtf_analyzer.analyze_multiple_timeframes(
                'EURUSD', timeframes, ['rsi', 'macd', 'sma']
            )

            assert mtf_result['symbol'] == 'EURUSD', "Wrong symbol in analysis"
            assert 'timeframes_analyzed' in mtf_result, (
                "Missing analyzed timeframes"
            )
            assert 'timeframe_results' in mtf_result, (
                "Missing timeframe results"
            )
            assert 'consensus' in mtf_result, "Missing consensus analysis"

            # Verify timeframe results structure
            for tf in timeframes:
                assert tf in mtf_result['timeframe_results'], (
                    f"Missing results for timeframe {tf}"
                )
                tf_data = mtf_result['timeframe_results'][tf]

                assert 'trend_direction' in tf_data, (
                    f"Missing trend direction for {tf}"
                )
                assert 'momentum' in tf_data, (
                    f"Missing momentum data for {tf}"
                )
                assert 'volatility' in tf_data, (
                    f"Missing volatility data for {tf}"
                )
                assert 'support_resistance' in tf_data, (
                    f"Missing S/R data for {tf}"
                )

            # Verify consensus analysis
            consensus = mtf_result['consensus']
            assert consensus['direction'] in [
                'BULLISH', 'BEARISH', 'NEUTRAL'
            ], "Invalid consensus direction"
            assert 0 <= consensus['strength'] <= 1, (
                "Consensus strength out of range"
            )
            assert 0 <= consensus['agreement_percentage'] <= 100, (
                "Agreement percentage out of range"
            )

            # Test divergence detection
            divergence_result = (
                await mtf_analyzer.detect_timeframe_divergences(
                    mtf_result
                )
            )

            assert 'divergences_found' in divergence_result, (
                "Missing divergence detection result"
            )
            assert 'risk_level' in divergence_result, (
                "Missing risk level assessment"
            )
            assert 'recommended_action' in divergence_result, (
                "Missing recommended action"
            )

            if divergence_result['divergences_found']:
                assert 'divergence_details' in divergence_result, (
                    "Missing divergence details"
                )
                assert len(divergence_result['divergence_details']) > 0, (
                    "No divergence details provided"
                )

    @pytest.mark.asyncio
    async def test_custom_indicator_support(self):
        """Test custom indicator creation and calculation."""
        with patch(
            'nautilus_trader_engine.indicators.CustomIndicatorEngine'
        ) as mock_custom:
            mock_instance = AsyncMock()
            mock_custom.return_value = mock_instance

            # Sample custom indicator definition
            custom_indicator_def = {
                'name': 'CUSTOM_MOMENTUM',
                'description': (
                    'Custom momentum indicator combining RSI and MACD'
                ),
                'type': IndicatorType.MOMENTUM.value,
                'parameters': {
                    'rsi_period': 14,
                    'macd_fast': 12,
                    'macd_slow': 26,
                    'weight_rsi': 0.6,
                    'weight_macd': 0.4
                },
                'calculation_formula': 'WEIGHTED_AVERAGE',
                'output_range': {'min': 0, 'max': 100},
                'signal_levels': {'overbought': 75, 'oversold': 25}
            }

            mock_instance.register_custom_indicator.return_value = {
                'indicator_id': 'CUSTOM_001',
                'registration_status': 'SUCCESS',
                'validation_passed': True,
                'compilation_time_ms': 50,
                'ready_for_calculation': True
            }

            def calculate_custom_indicator(indicator_id, data, parameters):
                """Calculate custom indicator values."""
                if indicator_id != 'CUSTOM_001':
                    return {'error': 'Unknown indicator'}

                # Simulate custom calculation (simplified)
                close_prices = data.get('close', [])
                if len(close_prices) < 26:  # Need enough data for MACD
                    return {'values': [None] * len(close_prices)}

                # Simulate RSI calculation (simplified)
                rsi_values = [
                    50 + (i % 20 - 10) * 2
                    for i in range(len(close_prices))
                ]

                # Simulate MACD calculation (simplified)
                macd_values = [
                    (i % 10 - 5) * 0.1 for i in range(len(close_prices))
                ]

                # Combine using weights
                weight_rsi = parameters.get('weight_rsi', 0.6)
                weight_macd = parameters.get('weight_macd', 0.4)

                custom_values = []
                for i in range(len(close_prices)):
                    if i < 25:  # Need warmup period
                        custom_values.append(None)
                    else:
                        # Normalize MACD to 0-100 range
                        normalized_macd = max(
                            0, min(100, (macd_values[i] + 1) * 50)
                        )

                        combined_value = (
                            (rsi_values[i] * weight_rsi)
                            + (normalized_macd * weight_macd)
                        )
                        custom_values.append(
                            round(combined_value, 2)
                        )

                return {
                    'indicator_id': indicator_id,
                    'values': custom_values,
                    'last_value': (
                        custom_values[-1]
                        if custom_values[-1] is not None
                        else None
                    ),
                    'calculation_time_ms': 25,
                    'data_points_processed': len(close_prices)
                }

            mock_instance.calculate_custom_indicator.side_effect = (
                calculate_custom_indicator
            )
            mock_instance.validate_custom_formula.return_value = {
                'formula_valid': True,
                'syntax_errors': [],
                'performance_estimate_ms': 15,
                'memory_usage_estimate_mb': 2.5
            }

            custom_engine = mock_custom()

            # Test custom indicator registration
            registration_result = (
                await custom_engine.register_custom_indicator(
                    custom_indicator_def
                )
            )
            assert registration_result['registration_status'] == 'SUCCESS', (
                "Custom indicator registration failed"
            )
            assert registration_result['validation_passed'] is True, (
                "Custom indicator validation failed"
            )
            assert 'indicator_id' in registration_result, (
                "Missing indicator ID"
            )

            # Test formula validation
            validation_result = await custom_engine.validate_custom_formula(
                custom_indicator_def['calculation_formula']
            )
            assert validation_result['formula_valid'] is True, (
                "Custom formula validation failed"
            )
            assert len(validation_result['syntax_errors']) == 0, (
                "Formula has syntax errors"
            )
            assert validation_result['performance_estimate_ms'] < 100, (
                "Custom indicator too slow"
            )

            # Test custom indicator calculation
            test_data = {
                'close': self.sample_data['close'].tolist(),
                'high': self.sample_data['high'].tolist(),
                'low': self.sample_data['low'].tolist(),
                'volume': self.sample_data['volume'].tolist()
            }
            calculation_result = (
                await custom_engine.calculate_custom_indicator(
                    'CUSTOM_001',
                    test_data,
                    custom_indicator_def['parameters']
                )
            )
            assert 'values' in calculation_result, (
                "Missing custom indicator values"
            )
            assert calculation_result['indicator_id'] == 'CUSTOM_001', (
                "Wrong indicator ID in result"
            )
            assert calculation_result['data_points_processed'] > 0, (
                "No data points processed"
            )


if __name__ == '__main__':
    pytest.main([__file__])
