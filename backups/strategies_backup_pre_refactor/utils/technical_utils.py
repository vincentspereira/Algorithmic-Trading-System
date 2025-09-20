"""Technical analysis utility functions for trading strategies.

This module provides comprehensive technical analysis utilities including
indicators, pattern recognition, and signal generation.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import TA-Lib, fall back to basic implementations if not available
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    logger.warning("TA-Lib not available, using basic implementations")


def calculate_sma(data: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average.
    
    Args:
        data: Price series
        period: Period for SMA
        
    Returns:
        pd.Series: SMA values
    """
    if TALIB_AVAILABLE:
        return pd.Series(talib.SMA(data.values, timeperiod=period), index=data.index)
    else:
        return data.rolling(window=period).mean()


def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average.
    
    Args:
        data: Price series
        period: Period for EMA
        
    Returns:
        pd.Series: EMA values
    """
    if TALIB_AVAILABLE:
        return pd.Series(talib.EMA(data.values, timeperiod=period), index=data.index)
    else:
        return data.ewm(span=period).mean()


def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index.
    
    Args:
        data: Price series
        period: Period for RSI calculation
        
    Returns:
        pd.Series: RSI values
    """
    if TALIB_AVAILABLE:
        return pd.Series(talib.RSI(data.values, timeperiod=period), index=data.index)
    else:
        # Basic RSI implementation
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))


def calculate_macd(data: pd.Series, fast_period: int = 12, slow_period: int = 26, 
                  signal_period: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD indicator.
    
    Args:
        data: Price series
        fast_period: Fast EMA period
        slow_period: Slow EMA period
        signal_period: Signal line EMA period
        
    Returns:
        Tuple: (MACD line, Signal line, Histogram)
    """
    if TALIB_AVAILABLE:
        macd, signal, histogram = talib.MACD(data.values, fastperiod=fast_period,
                                           slowperiod=slow_period, signalperiod=signal_period)
        return (pd.Series(macd, index=data.index),
                pd.Series(signal, index=data.index),
                pd.Series(histogram, index=data.index))
    else:
        # Basic MACD implementation
        ema_fast = calculate_ema(data, fast_period)
        ema_slow = calculate_ema(data, slow_period)
        macd_line = ema_fast - ema_slow
        signal_line = calculate_ema(macd_line, signal_period)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram


def calculate_bollinger_bands(data: pd.Series, period: int = 20, 
                            std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Bollinger Bands.
    
    Args:
        data: Price series
        period: Period for moving average
        std_dev: Standard deviation multiplier
        
    Returns:
        Tuple: (Upper band, Middle band, Lower band)
    """
    if TALIB_AVAILABLE:
        upper, middle, lower = talib.BBANDS(data.values, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev)
        return (pd.Series(upper, index=data.index),
                pd.Series(middle, index=data.index),
                pd.Series(lower, index=data.index))
    else:
        # Basic Bollinger Bands implementation
        middle = calculate_sma(data, period)
        std = data.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, 
                 period: int = 14) -> pd.Series:
    """Calculate Average True Range.
    
    Args:
        high: High price series
        low: Low price series
        close: Close price series
        period: Period for ATR calculation
        
    Returns:
        pd.Series: ATR values
    """
    if TALIB_AVAILABLE:
        return pd.Series(talib.ATR(high.values, low.values, close.values, timeperiod=period),
                        index=close.index)
    else:
        # Basic ATR implementation
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return true_range.rolling(window=period).mean()


def calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
                        k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
    """Calculate Stochastic Oscillator.
    
    Args:
        high: High price series
        low: Low price series
        close: Close price series
        k_period: %K period
        d_period: %D period
        
    Returns:
        Tuple: (%K, %D)
    """
    if TALIB_AVAILABLE:
        k, d = talib.STOCH(high.values, low.values, close.values,
                          fastk_period=k_period, slowk_period=d_period, slowd_period=d_period)
        return pd.Series(k, index=close.index), pd.Series(d, index=close.index)
    else:
        # Basic Stochastic implementation
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()
        return k_percent, d_percent


def calculate_williams_r(high: pd.Series, low: pd.Series, close: pd.Series,
                        period: int = 14) -> pd.Series:
    """Calculate Williams %R.
    
    Args:
        high: High price series
        low: Low price series
        close: Close price series
        period: Period for calculation
        
    Returns:
        pd.Series: Williams %R values
    """
    if TALIB_AVAILABLE:
        return pd.Series(talib.WILLR(high.values, low.values, close.values, timeperiod=period),
                        index=close.index)
    else:
        # Basic Williams %R implementation
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()
        return -100 * ((highest_high - close) / (highest_high - lowest_low))


def calculate_cci(high: pd.Series, low: pd.Series, close: pd.Series,
                 period: int = 20) -> pd.Series:
    """Calculate Commodity Channel Index.
    
    Args:
        high: High price series
        low: Low price series
        close: Close price series
        period: Period for calculation
        
    Returns:
        pd.Series: CCI values
    """
    if TALIB_AVAILABLE:
        return pd.Series(talib.CCI(high.values, low.values, close.values, timeperiod=period),
                        index=close.index)
    else:
        # Basic CCI implementation
        typical_price = (high + low + close) / 3
        sma_tp = typical_price.rolling(window=period).mean()
        mean_deviation = typical_price.rolling(window=period).apply(
            lambda x: np.mean(np.abs(x - x.mean()))
        )
        return (typical_price - sma_tp) / (0.015 * mean_deviation)


def detect_support_resistance(data: pd.Series, window: int = 20, 
                            min_touches: int = 2) -> Dict[str, List[float]]:
    """Detect support and resistance levels.
    
    Args:
        data: Price series
        window: Window for local extrema detection
        min_touches: Minimum touches to confirm level
        
    Returns:
        Dict: Support and resistance levels
    """
    # Find local maxima and minima
    highs = data.rolling(window=window, center=True).max() == data
    lows = data.rolling(window=window, center=True).min() == data
    
    resistance_levels = []
    support_levels = []
    
    # Get resistance levels (local maxima)
    resistance_prices = data[highs].dropna()
    for price in resistance_prices:
        touches = sum(abs(data - price) < (price * 0.01))  # 1% tolerance
        if touches >= min_touches:
            resistance_levels.append(price)
    
    # Get support levels (local minima)
    support_prices = data[lows].dropna()
    for price in support_prices:
        touches = sum(abs(data - price) < (price * 0.01))  # 1% tolerance
        if touches >= min_touches:
            support_levels.append(price)
    
    return {
        'resistance': sorted(list(set(resistance_levels)), reverse=True),
        'support': sorted(list(set(support_levels)))
    }


def identify_candlestick_patterns(open_prices: pd.Series, high_prices: pd.Series,
                                low_prices: pd.Series, close_prices: pd.Series) -> Dict[str, pd.Series]:
    """Identify common candlestick patterns.
    
    Args:
        open_prices: Open price series
        high_prices: High price series
        low_prices: Low price series
        close_prices: Close price series
        
    Returns:
        Dict: Candlestick pattern signals
    """
    patterns = {}
    
    if TALIB_AVAILABLE:
        # Use TA-Lib pattern recognition functions
        patterns['hammer'] = pd.Series(talib.CDLHAMMER(open_prices.values, high_prices.values,
                                                      low_prices.values, close_prices.values),
                                     index=close_prices.index)
        patterns['doji'] = pd.Series(talib.CDLDOJI(open_prices.values, high_prices.values,
                                                 low_prices.values, close_prices.values),
                                   index=close_prices.index)
        patterns['engulfing'] = pd.Series(talib.CDLENGULFING(open_prices.values, high_prices.values,
                                                            low_prices.values, close_prices.values),
                                         index=close_prices.index)
    else:
        # Basic pattern implementations
        body_size = abs(close_prices - open_prices)
        upper_shadow = high_prices - np.maximum(open_prices, close_prices)
        lower_shadow = np.minimum(open_prices, close_prices) - low_prices
        
        # Hammer pattern (simplified)
        hammer_condition = (
            (lower_shadow > 2 * body_size) &
            (upper_shadow < 0.1 * body_size) &
            (body_size > 0)
        )
        patterns['hammer'] = hammer_condition.astype(int) * 100
        
        # Doji pattern (simplified)
        doji_condition = body_size < (high_prices - low_prices) * 0.1
        patterns['doji'] = doji_condition.astype(int) * 100
    
    return patterns


def calculate_pivot_points(high: float, low: float, close: float) -> Dict[str, float]:
    """Calculate pivot points and support/resistance levels.
    
    Args:
        high: Previous day's high
        low: Previous day's low
        close: Previous day's close
        
    Returns:
        Dict: Pivot points and levels
    """
    pivot = (high + low + close) / 3
    
    return {
        'pivot': pivot,
        'r1': 2 * pivot - low,
        'r2': pivot + (high - low),
        'r3': high + 2 * (pivot - low),
        's1': 2 * pivot - high,
        's2': pivot - (high - low),
        's3': low - 2 * (high - pivot)
    }


def calculate_fibonacci_retracements(high: float, low: float) -> Dict[str, float]:
    """Calculate Fibonacci retracement levels.
    
    Args:
        high: Swing high
        low: Swing low
        
    Returns:
        Dict: Fibonacci levels
    """
    diff = high - low
    
    return {
        '0%': high,
        '23.6%': high - 0.236 * diff,
        '38.2%': high - 0.382 * diff,
        '50%': high - 0.5 * diff,
        '61.8%': high - 0.618 * diff,
        '78.6%': high - 0.786 * diff,
        '100%': low
    }


def generate_trading_signals(data: Dict[str, pd.Series], 
                           strategy_params: Dict[str, any]) -> pd.DataFrame:
    """Generate trading signals based on multiple indicators.
    
    Args:
        data: Dictionary containing OHLCV data
        strategy_params: Strategy parameters
        
    Returns:
        pd.DataFrame: Trading signals
    """
    signals = pd.DataFrame(index=data['close'].index)
    
    # Calculate indicators
    rsi = calculate_rsi(data['close'], strategy_params.get('rsi_period', 14))
    macd, macd_signal, _ = calculate_macd(data['close'])
    sma_short = calculate_sma(data['close'], strategy_params.get('sma_short', 20))
    sma_long = calculate_sma(data['close'], strategy_params.get('sma_long', 50))
    
    # Generate signals
    signals['rsi_oversold'] = rsi < strategy_params.get('rsi_oversold', 30)
    signals['rsi_overbought'] = rsi > strategy_params.get('rsi_overbought', 70)
    signals['macd_bullish'] = macd > macd_signal
    signals['sma_bullish'] = sma_short > sma_long
    
    # Combine signals
    signals['buy_signal'] = (
        signals['rsi_oversold'] & 
        signals['macd_bullish'] & 
        signals['sma_bullish']
    )
    
    signals['sell_signal'] = (
        signals['rsi_overbought'] & 
        ~signals['macd_bullish'] & 
        ~signals['sma_bullish']
    )
    
    return signals


def calculate_indicator_divergence(price: pd.Series, indicator: pd.Series, 
                                 window: int = 20) -> pd.Series:
    """Detect divergence between price and indicator.
    
    Args:
        price: Price series
        indicator: Indicator series
        window: Window for divergence detection
        
    Returns:
        pd.Series: Divergence signals (1 for bullish, -1 for bearish, 0 for none)
    """
    price_trend = price.rolling(window=window).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0])
    indicator_trend = indicator.rolling(window=window).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0])
    
    # Bullish divergence: price declining, indicator rising
    bullish_div = (price_trend < 0) & (indicator_trend > 0)
    
    # Bearish divergence: price rising, indicator declining
    bearish_div = (price_trend > 0) & (indicator_trend < 0)
    
    divergence = pd.Series(0, index=price.index)
    divergence[bullish_div] = 1
    divergence[bearish_div] = -1
    
    return divergence