import pandas as pd
import talib
from typing import Tuple

class TechnicalIndicators:
    """A utility class for calculating technical indicators."""

    @staticmethod
    def rsi(close: pd.Series, period: int) -> pd.Series:
        """Calculate RSI using TA-Lib with proper gain/loss handling."""
        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
        avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
        
        # Handle division by zero
        rs = avg_gain / avg_loss.where(avg_loss != 0, 0.000001)
        
        rsi = 100 - (100 / (1 + rs))
        
        return rsi

    @staticmethod
    def bollinger_bands(close: pd.Series, period: int, std_dev: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands using TA-Lib."""
        return talib.BBANDS(close, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev, matype=0)

    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
        """Calculate ATR using TA-Lib."""
        return talib.ATR(high, low, close, timeperiod=period)

    @staticmethod
    def sma(series: pd.Series, period: int) -> pd.Series:
        """Calculate Simple Moving Average."""
        return talib.SMA(series, timeperiod=period)
        
    @staticmethod
    def trend_strength(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate ADX for trend strength."""
        return talib.ADX(high, low, close, timeperiod=period)

    @staticmethod
    def volume_sma(volume: pd.Series, period: int) -> pd.Series:
        """Calculate Simple Moving Average of volume."""
        return talib.SMA(volume, timeperiod=period)