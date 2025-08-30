"""
Enhanced Technical Analysis Indicators Library - Part 1
Trend and Momentum Indicators (30+ indicators)

Author: Vincent S. Pereira
Version: 2.0.0
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple, Union, List, Dict
from dataclasses import dataclass
from enum import Enum
import warnings
from scipy import stats

warnings.filterwarnings('ignore')

class IndicatorType(Enum):
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    SUPPORT_RESISTANCE = "support_resistance"

@dataclass
class IndicatorResult:
    """Enhanced result structure for all indicators"""
    value: Union[float, pd.Series, np.ndarray, dict]
    signal: str  # BUY, SELL, NEUTRAL, STRONG_BUY, STRONG_SELL
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0  
    metadata: dict

class EnhancedTechnicalIndicators:
    """Comprehensive technical indicators library with 60+ indicators"""
    
    # ===========================================
    # TREND INDICATORS (15)
    # ===========================================
    
    @staticmethod
    def adaptive_moving_average(data: pd.Series, period: int = 20, fast_sc: float = 2, slow_sc: float = 30) -> IndicatorResult:
        """Kaufman's Adaptive Moving Average (KAMA)"""
        change = abs(data.diff(period))
        volatility = data.diff().abs().rolling(period).sum()
        efficiency_ratio = change / volatility.replace(0, 1e-10)
        
        fast_alpha = 2 / (fast_sc + 1)
        slow_alpha = 2 / (slow_sc + 1)
        sc = (efficiency_ratio * (fast_alpha - slow_alpha) + slow_alpha) ** 2
        
        kama = pd.Series(index=data.index, dtype=float)
        kama.iloc[period-1] = data.iloc[period-1]
        
        for i in range(period, len(data)):
            kama.iloc[i] = kama.iloc[i-1] + sc.iloc[i] * (data.iloc[i] - kama.iloc[i-1])
        
        signal = "BUY" if data.iloc[-1] > kama.iloc[-1] else "SELL"
        strength = abs(data.iloc[-1] - kama.iloc[-1]) / kama.iloc[-1]
        
        return IndicatorResult(kama, signal, min(strength, 1.0), efficiency_ratio.iloc[-1], 
                             {"period": period, "adaptive": True})
    
    @staticmethod
    def double_exponential_ma(data: pd.Series, period: int = 21) -> IndicatorResult:
        """Double Exponential Moving Average (DEMA)"""
        ema1 = data.ewm(span=period).mean()
        ema2 = ema1.ewm(span=period).mean()
        dema = 2 * ema1 - ema2
        
        signal = "BUY" if data.iloc[-1] > dema.iloc[-1] else "SELL"
        strength = abs(data.iloc[-1] - dema.iloc[-1]) / dema.iloc[-1]
        
        return IndicatorResult(dema, signal, min(strength, 1.0), 0.8, {"period": period, "lag_reduction": True})
    
    @staticmethod
    def triple_exponential_ma(data: pd.Series, period: int = 21) -> IndicatorResult:
        """Triple Exponential Moving Average (TEMA)"""
        ema1 = data.ewm(span=period).mean()
        ema2 = ema1.ewm(span=period).mean()
        ema3 = ema2.ewm(span=period).mean()
        tema = 3 * ema1 - 3 * ema2 + ema3
        
        signal = "BUY" if data.iloc[-1] > tema.iloc[-1] else "SELL"
        strength = abs(data.iloc[-1] - tema.iloc[-1]) / tema.iloc[-1]
        
        return IndicatorResult(tema, signal, min(strength, 1.0), 0.85, {"period": period})
    
    @staticmethod
    def hull_moving_average(data: pd.Series, period: int = 21) -> IndicatorResult:
        """Hull Moving Average (HMA) - Reduced lag moving average"""
        half_period = int(period / 2)
        sqrt_period = int(np.sqrt(period))
        
        wma_half = data.rolling(half_period).apply(lambda x: np.average(x, weights=range(1, len(x) + 1)))
        wma_full = data.rolling(period).apply(lambda x: np.average(x, weights=range(1, len(x) + 1)))
        
        raw_hma = 2 * wma_half - wma_full
        hma = raw_hma.rolling(sqrt_period).apply(lambda x: np.average(x, weights=range(1, len(x) + 1)))
        
        signal = "BUY" if data.iloc[-1] > hma.iloc[-1] else "SELL"
        strength = abs(data.iloc[-1] - hma.iloc[-1]) / hma.iloc[-1]
        
        return IndicatorResult(hma, signal, min(strength, 1.0), 0.9, {"period": period, "zero_lag": True})
    
    @staticmethod
    def mcginley_dynamic(data: pd.Series, period: int = 20) -> IndicatorResult:
        """McGinley Dynamic - Automatically adjusts for market speed"""
        md = pd.Series(index=data.index, dtype=float)
        md.iloc[0] = data.iloc[0]
        
        for i in range(1, len(data)):
            if md.iloc[i-1] != 0:
                k = data.iloc[i] / md.iloc[i-1]
                md.iloc[i] = md.iloc[i-1] + (data.iloc[i] - md.iloc[i-1]) / (period * k**4)
            else:
                md.iloc[i] = data.iloc[i]
        
        signal = "BUY" if data.iloc[-1] > md.iloc[-1] else "SELL"
        strength = abs(data.iloc[-1] - md.iloc[-1]) / md.iloc[-1]
        
        return IndicatorResult(md, signal, min(strength, 1.0), 0.85, {"period": period, "auto_adjusting": True})
    
    @staticmethod
    def zero_lag_ema(data: pd.Series, period: int = 21) -> IndicatorResult:
        """Zero Lag Exponential Moving Average"""
        ema = data.ewm(span=period).mean()
        zlema = data + (data - data.shift(int((period-1)/2)))
        zlema_final = zlema.ewm(span=period).mean()
        
        signal = "BUY" if data.iloc[-1] > zlema_final.iloc[-1] else "SELL"
        strength = abs(data.iloc[-1] - zlema_final.iloc[-1]) / zlema_final.iloc[-1]
        
        return IndicatorResult(zlema_final, signal, min(strength, 1.0), 0.85, {"period": period, "zero_lag": True})
    
    @staticmethod
    def linear_regression(data: pd.Series, period: int = 21) -> IndicatorResult:
        """Linear Regression Line"""
        lr_values = []
        for i in range(period-1, len(data)):
            y = data.iloc[i-period+1:i+1].values
            x = np.arange(len(y))
            slope, intercept = np.polyfit(x, y, 1)
            lr_values.append(slope * (len(y)-1) + intercept)
        
        lr_series = pd.Series([np.nan]*(period-1) + lr_values, index=data.index)
        
        signal = "BUY" if data.iloc[-1] > lr_series.iloc[-1] else "SELL"
        strength = abs(data.iloc[-1] - lr_series.iloc[-1]) / lr_series.iloc[-1]
        
        return IndicatorResult(lr_series, signal, min(strength, 1.0), 0.75, {"period": period, "linear_fit": True})
    
    # ===========================================
    # MOMENTUM OSCILLATORS (15)
    # ===========================================
    
    @staticmethod
    def stochastic_oscillator(high: pd.Series, low: pd.Series, close: pd.Series,
                            k_period: int = 14, d_period: int = 3, smooth_k: int = 3) -> IndicatorResult:
        """Stochastic Oscillator (%K and %D)"""
        lowest_low = low.rolling(k_period).min()
        highest_high = high.rolling(k_period).max()
        
        k_percent = 100 * (close - lowest_low) / (highest_high - lowest_low)
        k_smooth = k_percent.rolling(smooth_k).mean()
        d_percent = k_smooth.rolling(d_period).mean()
        
        if k_smooth.iloc[-1] < 20 and d_percent.iloc[-1] < 20:
            signal, strength = "STRONG_BUY", 0.9
        elif k_smooth.iloc[-1] < 30:
            signal, strength = "BUY", 0.7
        elif k_smooth.iloc[-1] > 80 and d_percent.iloc[-1] > 80:
            signal, strength = "STRONG_SELL", 0.9
        elif k_smooth.iloc[-1] > 70:
            signal, strength = "SELL", 0.7
        else:
            signal, strength = "NEUTRAL", 0.0
        
        return IndicatorResult({"k_percent": k_smooth, "d_percent": d_percent}, signal, strength, 0.8,
                             {"k_value": k_smooth.iloc[-1], "d_value": d_percent.iloc[-1]})
    
    @staticmethod
    def williams_percent_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> IndicatorResult:
        """Williams %R"""
        highest_high = high.rolling(period).max()
        lowest_low = low.rolling(period).min()
        
        williams_r = -100 * (highest_high - close) / (highest_high - lowest_low)
        
        if williams_r.iloc[-1] < -80:
            signal, strength = "STRONG_BUY", 0.9
        elif williams_r.iloc[-1] < -50:
            signal, strength = "BUY", 0.6
        elif williams_r.iloc[-1] > -20:
            signal, strength = "STRONG_SELL", 0.9
        else:
            signal, strength = "NEUTRAL", 0.0
        
        return IndicatorResult(williams_r, signal, strength, 0.75, {"period": period, "current_value": williams_r.iloc[-1]})
    
    @staticmethod
    def commodity_channel_index(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> IndicatorResult:
        """Commodity Channel Index (CCI)"""
        typical_price = (high + low + close) / 3
        sma_tp = typical_price.rolling(period).mean()
        mean_deviation = typical_price.rolling(period).apply(lambda x: np.mean(np.abs(x - x.mean())))
        
        cci = (typical_price - sma_tp) / (0.015 * mean_deviation)
        
        if cci.iloc[-1] > 200:
            signal, strength = "STRONG_SELL", 0.9
        elif cci.iloc[-1] > 100:
            signal, strength = "SELL", 0.7
        elif cci.iloc[-1] < -200:
            signal, strength = "STRONG_BUY", 0.9
        elif cci.iloc[-1] < -100:
            signal, strength = "BUY", 0.7
        else:
            signal, strength = "NEUTRAL", 0.0
        
        return IndicatorResult(cci, signal, strength, 0.8, {"period": period, "current_value": cci.iloc[-1]})
    
    @staticmethod
    def awesome_oscillator(high: pd.Series, low: pd.Series, short_period: int = 5, long_period: int = 34) -> IndicatorResult:
        """Awesome Oscillator"""
        midpoint = (high + low) / 2
        sma_short = midpoint.rolling(short_period).mean()
        sma_long = midpoint.rolling(long_period).mean()
        ao = sma_short - sma_long
        
        signal = "BUY" if ao.iloc[-1] > ao.iloc[-2] else "SELL"
        strength = abs(ao.iloc[-1]) / midpoint.iloc[-1] * 100
        
        return IndicatorResult(ao, signal, min(strength, 1.0), 0.7, 
                             {"short_period": short_period, "long_period": long_period})
    
    @staticmethod
    def accelerator_oscillator(high: pd.Series, low: pd.Series, close: pd.Series, 
                             ao_short: int = 5, ao_long: int = 34, signal_period: int = 5) -> IndicatorResult:
        """Accelerator Oscillator (AC)"""
        # First calculate AO
        midpoint = (high + low) / 2
        sma_short = midpoint.rolling(ao_short).mean()
        sma_long = midpoint.rolling(ao_long).mean()
        ao = sma_short - sma_long
        
        # Then calculate AC
        ao_sma = ao.rolling(signal_period).mean()
        ac = ao - ao_sma
        
        signal = "BUY" if ac.iloc[-1] > ac.iloc[-2] else "SELL"
        strength = abs(ac.iloc[-1]) / close.iloc[-1] * 100
        
        return IndicatorResult(ac, signal, min(strength, 1.0), 0.75, {"signal_period": signal_period})
    
    @staticmethod
    def fisher_transform(high: pd.Series, low: pd.Series, period: int = 10) -> IndicatorResult:
        """Fisher Transform"""
        hl2 = (high + low) / 2
        min_low = hl2.rolling(period).min()
        max_high = hl2.rolling(period).max()
        
        value1 = 0.66 * ((hl2 - min_low) / (max_high - min_low) - 0.5)
        value1 = value1.clip(-0.999, 0.999)  # Prevent division issues
        
        fisher = pd.Series(index=hl2.index, dtype=float)
        fisher.iloc[0] = 0
        
        for i in range(1, len(value1)):
            fisher.iloc[i] = 0.5 * np.log((1 + value1.iloc[i]) / (1 - value1.iloc[i])) + 0.5 * fisher.iloc[i-1]
        
        signal = "BUY" if fisher.iloc[-1] > fisher.iloc[-2] else "SELL"
        strength = abs(fisher.iloc[-1]) / 4  # Normalize to 0-1 range
        
        return IndicatorResult(fisher, signal, min(strength, 1.0), 0.8, {"period": period})