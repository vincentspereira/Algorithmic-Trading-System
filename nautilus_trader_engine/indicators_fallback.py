"""
Technical Indicators Fallback Module

This module provides fallback implementations for common TA-Lib indicators
using the 'ta' library and pandas/numpy when TA-Lib is not available.

Author: Kilo Code
Version: 1.0.0
"""

import pandas as pd
import numpy as np
import warnings
from typing import Union, Optional

# Try to import TA-Lib, fall back to 'ta' library if not available
TALIB_AVAILABLE = False
TA_AVAILABLE = False

try:
    import talib
    TALIB_AVAILABLE = True
    print("TA-Lib is available - using native TA-Lib functions")
except ImportError:
    print("TA-Lib not available - using fallback implementations")

try:
    import ta
    TA_AVAILABLE = True
    print("'ta' library is available for fallback implementations")
except ImportError:
    print("Warning: Neither TA-Lib nor 'ta' library is available")


class IndicatorError(Exception):
    """Custom exception for indicator calculation errors"""
    pass


def check_data(data: Union[pd.Series, np.ndarray], min_length: int = 1) -> np.ndarray:
    """
    Validate and convert input data to numpy array
    
    Args:
        data: Input price data
        min_length: Minimum required data length
        
    Returns:
        np.ndarray: Validated data array
        
    Raises:
        IndicatorError: If data is invalid or too short
    """
    if data is None:
        raise IndicatorError("Input data cannot be None")
    
    if isinstance(data, pd.Series):
        data = data.values
    elif not isinstance(data, np.ndarray):
        data = np.array(data)
    
    if len(data) < min_length:
        raise IndicatorError(f"Insufficient data: need at least {min_length} points, got {len(data)}")
    
    # Remove NaN values
    data = data[~np.isnan(data)]
    
    if len(data) < min_length:
        raise IndicatorError(f"Insufficient valid data after removing NaN values")
    
    return data


def SMA(close: Union[pd.Series, np.ndarray], timeperiod: int = 30) -> np.ndarray:
    """
    Simple Moving Average
    
    Args:
        close: Close prices
        timeperiod: Period for moving average
        
    Returns:
        np.ndarray: SMA values
    """
    if TALIB_AVAILABLE:
        return talib.SMA(close, timeperiod=timeperiod)
    
    close = check_data(close, timeperiod)
    
    if TA_AVAILABLE:
        df = pd.DataFrame({'close': close})
        return ta.trend.sma_indicator(df['close'], window=timeperiod).values
    
    # Manual calculation
    result = np.full(len(close), np.nan)
    for i in range(timeperiod - 1, len(close)):
        result[i] = np.mean(close[i - timeperiod + 1:i + 1])
    
    return result


def EMA(close: Union[pd.Series, np.ndarray], timeperiod: int = 30) -> np.ndarray:
    """
    Exponential Moving Average
    
    Args:
        close: Close prices
        timeperiod: Period for moving average
        
    Returns:
        np.ndarray: EMA values
    """
    if TALIB_AVAILABLE:
        return talib.EMA(close, timeperiod=timeperiod)
    
    close = check_data(close, timeperiod)
    
    if TA_AVAILABLE:
        df = pd.DataFrame({'close': close})
        return ta.trend.ema_indicator(df['close'], window=timeperiod).values
    
    # Manual calculation
    alpha = 2.0 / (timeperiod + 1.0)
    result = np.full(len(close), np.nan)
    result[timeperiod - 1] = np.mean(close[:timeperiod])
    
    for i in range(timeperiod, len(close)):
        result[i] = alpha * close[i] + (1 - alpha) * result[i - 1]
    
    return result


def RSI(close: Union[pd.Series, np.ndarray], timeperiod: int = 14) -> np.ndarray:
    """
    Relative Strength Index
    
    Args:
        close: Close prices
        timeperiod: Period for RSI calculation
        
    Returns:
        np.ndarray: RSI values
    """
    if TALIB_AVAILABLE:
        return talib.RSI(close, timeperiod=timeperiod)
    
    close = check_data(close, timeperiod + 1)
    
    if TA_AVAILABLE:
        df = pd.DataFrame({'close': close})
        return ta.momentum.rsi(df['close'], window=timeperiod).values
    
    # Manual calculation
    delta = np.diff(close)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    
    avg_gain = np.full(len(close), np.nan)
    avg_loss = np.full(len(close), np.nan)
    
    # Initial averages
    avg_gain[timeperiod] = np.mean(gain[:timeperiod])
    avg_loss[timeperiod] = np.mean(loss[:timeperiod])
    
    # Smoothed averages
    for i in range(timeperiod + 1, len(close)):
        avg_gain[i] = (avg_gain[i-1] * (timeperiod - 1) + gain[i-1]) / timeperiod
        avg_loss[i] = (avg_loss[i-1] * (timeperiod - 1) + loss[i-1]) / timeperiod
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def MACD(close: Union[pd.Series, np.ndarray], 
         fastperiod: int = 12, 
         slowperiod: int = 26, 
         signalperiod: int = 9) -> tuple:
    """
    Moving Average Convergence Divergence
    
    Args:
        close: Close prices
        fastperiod: Fast EMA period
        slowperiod: Slow EMA period
        signalperiod: Signal line EMA period
        
    Returns:
        tuple: (macd, macdsignal, macdhist)
    """
    if TALIB_AVAILABLE:
        return talib.MACD(close, fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=signalperiod)
    
    close = check_data(close, slowperiod)
    
    if TA_AVAILABLE:
        df = pd.DataFrame({'close': close})
        macd_line = ta.trend.macd(df['close'], window_fast=fastperiod, window_slow=slowperiod).values
        macd_signal = ta.trend.macd_signal(df['close'], window_fast=fastperiod, window_slow=slowperiod, window_sign=signalperiod).values
        macd_hist = ta.trend.macd_diff(df['close'], window_fast=fastperiod, window_slow=slowperiod, window_sign=signalperiod).values
        return macd_line, macd_signal, macd_hist
    
    # Manual calculation
    ema_fast = EMA(close, fastperiod)
    ema_slow = EMA(close, slowperiod)
    macd_line = ema_fast - ema_slow
    macd_signal = EMA(macd_line, signalperiod)
    macd_hist = macd_line - macd_signal
    
    return macd_line, macd_signal, macd_hist


def BBANDS(close: Union[pd.Series, np.ndarray], 
           timeperiod: int = 20, 
           nbdevup: float = 2.0, 
           nbdevdn: float = 2.0) -> tuple:
    """
    Bollinger Bands
    
    Args:
        close: Close prices
        timeperiod: Period for moving average
        nbdevup: Number of standard deviations for upper band
        nbdevdn: Number of standard deviations for lower band
        
    Returns:
        tuple: (upperband, middleband, lowerband)
    """
    if TALIB_AVAILABLE:
        return talib.BBANDS(close, timeperiod=timeperiod, nbdevup=nbdevup, nbdevdn=nbdevdn)
    
    close = check_data(close, timeperiod)
    
    if TA_AVAILABLE:
        df = pd.DataFrame({'close': close})
        upper = ta.volatility.bollinger_hband(df['close'], window=timeperiod, window_dev=nbdevup).values
        middle = ta.volatility.bollinger_mavg(df['close'], window=timeperiod).values
        lower = ta.volatility.bollinger_lband(df['close'], window=timeperiod, window_dev=nbdevdn).values
        return upper, middle, lower
    
    # Manual calculation
    sma = SMA(close, timeperiod)
    std = np.full(len(close), np.nan)
    
    for i in range(timeperiod - 1, len(close)):
        std[i] = np.std(close[i - timeperiod + 1:i + 1])
    
    upper = sma + (std * nbdevup)
    lower = sma - (std * nbdevdn)
    
    return upper, sma, lower


def STOCH(high: Union[pd.Series, np.ndarray],
          low: Union[pd.Series, np.ndarray],
          close: Union[pd.Series, np.ndarray],
          fastk_period: int = 5,
          slowk_period: int = 3,
          slowd_period: int = 3) -> tuple:
    """
    Stochastic Oscillator
    
    Args:
        high: High prices
        low: Low prices
        close: Close prices
        fastk_period: Fast %K period
        slowk_period: Slow %K period
        slowd_period: Slow %D period
        
    Returns:
        tuple: (slowk, slowd)
    """
    if TALIB_AVAILABLE:
        return talib.STOCH(high, low, close, 
                          fastk_period=fastk_period,
                          slowk_period=slowk_period,
                          slowd_period=slowd_period)
    
    high = check_data(high, fastk_period)
    low = check_data(low, fastk_period)
    close = check_data(close, fastk_period)
    
    if TA_AVAILABLE:
        df = pd.DataFrame({'high': high, 'low': low, 'close': close})
        slowk = ta.momentum.stoch(df['high'], df['low'], df['close'], 
                                 window=fastk_period, smooth_window=slowk_period).values
        slowd = ta.momentum.stoch_signal(df['high'], df['low'], df['close'],
                                        window=fastk_period, smooth_window=slowk_period,
                                        window_sign=slowd_period).values
        return slowk, slowd
    
    # Manual calculation
    fastk = np.full(len(close), np.nan)
    
    for i in range(fastk_period - 1, len(close)):
        highest_high = np.max(high[i - fastk_period + 1:i + 1])
        lowest_low = np.min(low[i - fastk_period + 1:i + 1])
        if highest_high != lowest_low:
            fastk[i] = 100 * (close[i] - lowest_low) / (highest_high - lowest_low)
        else:
            fastk[i] = 50
    
    slowk = SMA(fastk, slowk_period)
    slowd = SMA(slowk, slowd_period)
    
    return slowk, slowd


def get_available_indicators() -> dict:
    """
    Get information about available indicators and their sources
    
    Returns:
        dict: Information about available indicators
    """
    return {
        'talib_available': TALIB_AVAILABLE,
        'ta_available': TA_AVAILABLE,
        'indicators': {
            'SMA': 'Simple Moving Average',
            'EMA': 'Exponential Moving Average', 
            'RSI': 'Relative Strength Index',
            'MACD': 'Moving Average Convergence Divergence',
            'BBANDS': 'Bollinger Bands',
            'STOCH': 'Stochastic Oscillator'
        },
        'fallback_method': 'ta library' if TA_AVAILABLE else 'manual calculation'
    }


def test_indicators():
    """Test all indicators with sample data"""
    print("Testing Technical Indicators...")
    print(f"TA-Lib available: {TALIB_AVAILABLE}")
    print(f"'ta' library available: {TA_AVAILABLE}")
    print()
    
    # Generate sample data
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
    high = prices + np.random.rand(100) * 2
    low = prices - np.random.rand(100) * 2
    close = prices
    
    try:
        # Test SMA
        sma = SMA(close, 20)
        print(f"SMA(20) - Last value: {sma[-1]:.2f}")
        
        # Test EMA
        ema = EMA(close, 20)
        print(f"EMA(20) - Last value: {ema[-1]:.2f}")
        
        # Test RSI
        rsi = RSI(close, 14)
        print(f"RSI(14) - Last value: {rsi[-1]:.2f}")
        
        # Test MACD
        macd, signal, hist = MACD(close)
        print(f"MACD - Last values: {macd[-1]:.2f}, {signal[-1]:.2f}, {hist[-1]:.2f}")
        
        # Test Bollinger Bands
        upper, middle, lower = BBANDS(close, 20)
        print(f"BBANDS(20) - Last values: {upper[-1]:.2f}, {middle[-1]:.2f}, {lower[-1]:.2f}")
        
        # Test Stochastic
        slowk, slowd = STOCH(high, low, close)
        print(f"STOCH - Last values: {slowk[-1]:.2f}, {slowd[-1]:.2f}")
        
        print("\nAll indicators tested successfully!")
        
    except Exception as e:
        print(f"Error testing indicators: {e}")


if __name__ == "__main__":
    test_indicators()