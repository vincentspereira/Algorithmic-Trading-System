"""
Specialized Technical Indicators - Completing the 30+ Indicator Suite
Final set of advanced momentum, volume, and composite indicators

Total indicators across all modules: 34
- Technical Indicators: 10 basic indicators
- Advanced Indicators: 10 advanced indicators  
- Specialized Indicators: 14 specialized indicators
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple, Union, List
from .technical_indicators import IndicatorResult

class SpecializedIndicators:
    """Specialized and composite technical indicators"""
    
    @staticmethod
    def dema(data: pd.Series, period: int = 20) -> IndicatorResult:
        """Double Exponential Moving Average"""
        ema1 = data.ewm(span=period).mean()
        ema2 = ema1.ewm(span=period).mean()
        dema = 2 * ema1 - ema2
        
        signal = "BUY" if data.iloc[-1] > dema.iloc[-1] else "SELL"
        strength = abs(data.iloc[-1] - dema.iloc[-1]) / dema.iloc[-1]
        
        return IndicatorResult(dema, signal, min(strength, 1.0), {"period": period})

    @staticmethod
    def tema(data: pd.Series, period: int = 20) -> IndicatorResult:
        """Triple Exponential Moving Average"""
        ema1 = data.ewm(span=period).mean()
        ema2 = ema1.ewm(span=period).mean()
        ema3 = ema2.ewm(span=period).mean()
        tema = 3 * ema1 - 3 * ema2 + ema3
        
        signal = "BUY" if data.iloc[-1] > tema.iloc[-1] else "SELL"
        strength = abs(data.iloc[-1] - tema.iloc[-1]) / tema.iloc[-1]
        
        return IndicatorResult(tema, signal, min(strength, 1.0), {"period": period})

    @staticmethod
    def wma(data: pd.Series, period: int = 20) -> IndicatorResult:
        """Weighted Moving Average"""
        weights = np.arange(1, period + 1)
        wma = data.rolling(window=period).apply(
            lambda x: np.sum(x * weights) / np.sum(weights), raw=True
        )
        
        signal = "BUY" if data.iloc[-1] > wma.iloc[-1] else "SELL"
        strength = abs(data.iloc[-1] - wma.iloc[-1]) / wma.iloc[-1]
        
        return IndicatorResult(wma, signal, min(strength, 1.0), {"period": period})

    @staticmethod
    def roc(data: pd.Series, period: int = 12) -> IndicatorResult:
        """Rate of Change"""
        roc = ((data - data.shift(period)) / data.shift(period)) * 100
        
        if roc.iloc[-1] > 10:
            signal, strength = "BUY", min(roc.iloc[-1] / 20, 1.0)
        elif roc.iloc[-1] < -10:
            signal, strength = "SELL", min(abs(roc.iloc[-1]) / 20, 1.0)
        else:
            signal, strength = "NEUTRAL", 0.0
            
        return IndicatorResult(roc, signal, strength, {"period": period})

    @staticmethod
    def momentum(data: pd.Series, period: int = 10) -> IndicatorResult:
        """Momentum Indicator"""
        momentum = data - data.shift(period)
        
        # Normalize momentum
        momentum_sma = momentum.rolling(20).mean()
        signal = "BUY" if momentum.iloc[-1] > momentum_sma.iloc[-1] else "SELL"
        strength = abs(momentum.iloc[-1] - momentum_sma.iloc[-1]) / abs(momentum_sma.iloc[-1]) if momentum_sma.iloc[-1] != 0 else 0
        
        return IndicatorResult(momentum, signal, min(strength, 1.0), {"period": period})

    @staticmethod
    def ppo(data: pd.Series, fast: int = 12, slow: int = 26) -> IndicatorResult:
        """Percentage Price Oscillator"""
        ema_fast = data.ewm(span=fast).mean()
        ema_slow = data.ewm(span=slow).mean()
        ppo = ((ema_fast - ema_slow) / ema_slow) * 100
        
        signal = "BUY" if ppo.iloc[-1] > 0 else "SELL"
        strength = min(abs(ppo.iloc[-1]) / 5, 1.0)  # Normalize to 5%
        
        return IndicatorResult(ppo, signal, strength, {"fast": fast, "slow": slow})

    @staticmethod
    def trix(data: pd.Series, period: int = 14) -> IndicatorResult:
        """TRIX - Triple smoothed exponential moving average"""
        ema1 = data.ewm(span=period).mean()
        ema2 = ema1.ewm(span=period).mean()
        ema3 = ema2.ewm(span=period).mean()
        trix = ema3.pct_change() * 10000  # Convert to basis points
        
        signal = "BUY" if trix.iloc[-1] > 0 else "SELL"
        strength = min(abs(trix.iloc[-1]) / 50, 1.0)  # Normalize
        
        return IndicatorResult(trix, signal, strength, {"period": period})

    @staticmethod
    def ultimate_oscillator(high: pd.Series, low: pd.Series, close: pd.Series, 
                           period1: int = 7, period2: int = 14, period3: int = 28) -> IndicatorResult:
        """Ultimate Oscillator"""
        bp = close - pd.concat([low, close.shift()], axis=1).min(axis=1)
        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        
        avg7 = bp.rolling(period1).sum() / tr.rolling(period1).sum()
        avg14 = bp.rolling(period2).sum() / tr.rolling(period2).sum()
        avg28 = bp.rolling(period3).sum() / tr.rolling(period3).sum()
        
        uo = 100 * (4 * avg7 + 2 * avg14 + avg28) / 7
        
        if uo.iloc[-1] > 70:
            signal, strength = "SELL", (uo.iloc[-1] - 70) / 30
        elif uo.iloc[-1] < 30:
            signal, strength = "BUY", (30 - uo.iloc[-1]) / 30
        else:
            signal, strength = "NEUTRAL", 0.0
            
        return IndicatorResult(uo, signal, strength, {"period1": period1, "period2": period2, "period3": period3})

    @staticmethod
    def chaikin_oscillator(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, 
                          fast: int = 3, slow: int = 10) -> IndicatorResult:
        """Chaikin Oscillator"""
        ad_line = (((close - low) - (high - close)) / (high - low) * volume).fillna(0).cumsum()
        chaikin = ad_line.ewm(span=fast).mean() - ad_line.ewm(span=slow).mean()
        
        signal = "BUY" if chaikin.iloc[-1] > 0 else "SELL"
        chaikin_sma = chaikin.rolling(20).mean()
        strength = abs(chaikin.iloc[-1] - chaikin_sma.iloc[-1]) / abs(chaikin_sma.iloc[-1]) if chaikin_sma.iloc[-1] != 0 else 0
        
        return IndicatorResult(chaikin, signal, min(strength, 1.0), {"fast": fast, "slow": slow})

    @staticmethod
    def volume_rate_of_change(volume: pd.Series, period: int = 14) -> IndicatorResult:
        """Volume Rate of Change"""
        vroc = ((volume - volume.shift(period)) / volume.shift(period)) * 100
        
        # Volume expansion/contraction signals
        if vroc.iloc[-1] > 50:
            signal, strength = "BUY", min(vroc.iloc[-1] / 100, 1.0)
        elif vroc.iloc[-1] < -50:
            signal, strength = "SELL", min(abs(vroc.iloc[-1]) / 100, 1.0)
        else:
            signal, strength = "NEUTRAL", 0.0
            
        return IndicatorResult(vroc, signal, strength, {"period": period})

    @staticmethod
    def ease_of_movement(high: pd.Series, low: pd.Series, volume: pd.Series, period: int = 14) -> IndicatorResult:
        """Ease of Movement"""
        distance = (high + low) / 2 - (high.shift() + low.shift()) / 2
        box_height = (volume / 100000) / (high - low)
        eom = distance / box_height
        eom_sma = eom.rolling(period).mean()
        
        signal = "BUY" if eom_sma.iloc[-1] > 0 else "SELL"
        strength = min(abs(eom_sma.iloc[-1]) / 1000, 1.0)  # Normalize
        
        return IndicatorResult(eom_sma, signal, strength, {"period": period})

    @staticmethod
    def negative_volume_index(close: pd.Series, volume: pd.Series) -> IndicatorResult:
        """Negative Volume Index"""
        nvi = pd.Series(index=close.index, dtype=float)
        nvi.iloc[0] = 1000  # Starting value
        
        for i in range(1, len(close)):
            if volume.iloc[i] < volume.iloc[i-1]:
                nvi.iloc[i] = nvi.iloc[i-1] * (close.iloc[i] / close.iloc[i-1])
            else:
                nvi.iloc[i] = nvi.iloc[i-1]
        
        nvi_sma = nvi.rolling(255).mean()  # 1-year moving average
        signal = "BUY" if nvi.iloc[-1] > nvi_sma.iloc[-1] else "SELL"
        strength = abs(nvi.iloc[-1] - nvi_sma.iloc[-1]) / nvi_sma.iloc[-1]
        
        return IndicatorResult(nvi, signal, min(strength, 1.0), {"current": nvi.iloc[-1]})

    @staticmethod
    def standard_deviation(data: pd.Series, period: int = 20) -> IndicatorResult:
        """Standard Deviation (Volatility)"""
        std = data.rolling(window=period).std()
        std_sma = std.rolling(20).mean()
        
        # High volatility = potential reversal
        if std.iloc[-1] > std_sma.iloc[-1] * 1.5:
            signal, strength = "SELL", min((std.iloc[-1] / std_sma.iloc[-1] - 1.5) / 0.5, 1.0)
        elif std.iloc[-1] < std_sma.iloc[-1] * 0.7:
            signal, strength = "BUY", min((0.7 - std.iloc[-1] / std_sma.iloc[-1]) / 0.3, 1.0)
        else:
            signal, strength = "NEUTRAL", 0.0
            
        return IndicatorResult(std, signal, strength, {"period": period})

    @staticmethod
    def average_deviation(data: pd.Series, period: int = 20) -> IndicatorResult:
        """Average Deviation from Mean"""
        sma = data.rolling(window=period).mean()
        avg_dev = data.rolling(window=period).apply(lambda x: np.mean(np.abs(x - x.mean())))
        
        avg_dev_sma = avg_dev.rolling(20).mean()
        signal = "SELL" if avg_dev.iloc[-1] > avg_dev_sma.iloc[-1] else "BUY"
        strength = abs(avg_dev.iloc[-1] - avg_dev_sma.iloc[-1]) / avg_dev_sma.iloc[-1]
        
        return IndicatorResult(avg_dev, signal, min(strength, 1.0), {"period": period})