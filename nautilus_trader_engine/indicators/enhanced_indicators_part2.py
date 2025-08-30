"""
Enhanced Technical Analysis Indicators Library - Part 2
Volatility and Volume Indicators (25+ indicators)

Author: Vincent S. Pereira
Version: 2.0.0
"""

import numpy as np
import pandas as pd
from typing import Union, Dict
from dataclasses import dataclass
from scipy import stats

@dataclass
class IndicatorResult:
    """Enhanced result structure for all indicators"""
    value: Union[float, pd.Series, np.ndarray, dict]
    signal: str  # BUY, SELL, NEUTRAL, STRONG_BUY, STRONG_SELL
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0  
    metadata: dict

class EnhancedVolatilityVolumeIndicators:
    """Volatility and Volume indicators"""
    
    # ===========================================
    # VOLATILITY INDICATORS (12)
    # ===========================================
    
    @staticmethod
    def bollinger_bands_enhanced(data: pd.Series, period: int = 20, std_dev: float = 2.0) -> IndicatorResult:
        """Enhanced Bollinger Bands with %B and bandwidth"""
        sma = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        
        bb_percent = (data - lower) / (upper - lower)
        bandwidth = (upper - lower) / sma
        
        current_price = data.iloc[-1]
        bb_current = bb_percent.iloc[-1]
        bw_current = bandwidth.iloc[-1]
        bw_avg = bandwidth.rolling(50).mean().iloc[-1]
        
        if bb_current > 1.0:
            signal, strength = "SELL", min((bb_current - 1.0) * 2, 1.0)
        elif bb_current < 0.0:
            signal, strength = "BUY", min(abs(bb_current) * 2, 1.0)
        elif bb_current > 0.8 and bw_current < bw_avg:
            signal, strength = "SELL", 0.6
        elif bb_current < 0.2 and bw_current < bw_avg:
            signal, strength = "BUY", 0.6
        else:
            signal, strength = "NEUTRAL", 0.0
        
        return IndicatorResult(
            {"upper": upper, "middle": sma, "lower": lower, "percent_b": bb_percent, "bandwidth": bandwidth},
            signal, strength, 0.85,
            {"current_bb_percent": bb_current, "bandwidth_current": bw_current}
        )
    
    @staticmethod
    def keltner_channels(high: pd.Series, low: pd.Series, close: pd.Series, 
                       period: int = 20, multiplier: float = 2.0) -> IndicatorResult:
        """Keltner Channels"""
        ema = close.ewm(span=period).mean()
        
        prev_close = close.shift(1)
        tr = pd.concat([high - low, abs(high - prev_close), abs(low - prev_close)], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        upper = ema + (multiplier * atr)
        lower = ema - (multiplier * atr)
        kc_percent = (close - lower) / (upper - lower)
        
        if kc_percent.iloc[-1] > 1.0:
            signal, strength = "SELL", min((kc_percent.iloc[-1] - 1.0) * 2, 1.0)
        elif kc_percent.iloc[-1] < 0.0:
            signal, strength = "BUY", min(abs(kc_percent.iloc[-1]) * 2, 1.0)
        elif close.iloc[-1] > ema.iloc[-1]:
            signal, strength = "BUY", kc_percent.iloc[-1] * 0.5
        else:
            signal, strength = "SELL", (1 - kc_percent.iloc[-1]) * 0.5
        
        return IndicatorResult(
            {"upper": upper, "middle": ema, "lower": lower, "percent": kc_percent},
            signal, strength, 0.8, {"current_position": kc_percent.iloc[-1]}
        )
    
    @staticmethod
    def donchian_channels(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> IndicatorResult:
        """Donchian Channels"""
        upper = high.rolling(period).max()
        lower = low.rolling(period).min()
        middle = (upper + lower) / 2
        dc_percent = (close - lower) / (upper - lower)
        
        if close.iloc[-1] >= upper.iloc[-1]:
            signal, strength = "STRONG_BUY", 1.0
        elif close.iloc[-1] <= lower.iloc[-1]:
            signal, strength = "STRONG_SELL", 1.0
        elif dc_percent.iloc[-1] > 0.8:
            signal, strength = "BUY", dc_percent.iloc[-1]
        elif dc_percent.iloc[-1] < 0.2:
            signal, strength = "SELL", 1 - dc_percent.iloc[-1]
        else:
            signal, strength = "NEUTRAL", 0.0
        
        return IndicatorResult(
            {"upper": upper, "middle": middle, "lower": lower, "percent": dc_percent},
            signal, strength, 0.9, {"breakout_system": True}
        )
    
    @staticmethod
    def historical_volatility(data: pd.Series, period: int = 30, trading_periods: int = 252) -> IndicatorResult:
        """Historical Volatility (Annualized)"""
        log_returns = np.log(data / data.shift(1))
        volatility = log_returns.rolling(period).std() * np.sqrt(trading_periods)
        
        vol_percentile = stats.percentileofscore(volatility.dropna(), volatility.iloc[-1])
        
        if vol_percentile > 80:
            signal, strength = "SELL", (vol_percentile - 80) / 20
        elif vol_percentile < 20:
            signal, strength = "BUY", (20 - vol_percentile) / 20
        else:
            signal, strength = "NEUTRAL", 0.0
        
        return IndicatorResult(volatility, signal, strength, 0.7, {"volatility_percentile": vol_percentile})
    
    @staticmethod
    def average_directional_index(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> IndicatorResult:
        """Average Directional Index (ADX)"""
        # True Range
        prev_close = close.shift(1)
        tr = pd.concat([high - low, abs(high - prev_close), abs(low - prev_close)], axis=1).max(axis=1)
        
        # Directional Movement
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        plus_dm[(plus_dm - minus_dm) <= 0] = 0
        minus_dm[(minus_dm - plus_dm) <= 0] = 0
        
        # Smoothed values
        tr_smooth = tr.rolling(period).mean()
        plus_dm_smooth = plus_dm.rolling(period).mean()
        minus_dm_smooth = minus_dm.rolling(period).mean()
        
        # Directional Indicators
        plus_di = 100 * plus_dm_smooth / tr_smooth
        minus_di = 100 * minus_dm_smooth / tr_smooth
        
        # ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(period).mean()
        
        if adx.iloc[-1] > 25 and plus_di.iloc[-1] > minus_di.iloc[-1]:
            signal, strength = "BUY", min(adx.iloc[-1] / 50, 1.0)
        elif adx.iloc[-1] > 25 and minus_di.iloc[-1] > plus_di.iloc[-1]:
            signal, strength = "SELL", min(adx.iloc[-1] / 50, 1.0)
        else:
            signal, strength = "NEUTRAL", 0.0
        
        return IndicatorResult(
            {"adx": adx, "plus_di": plus_di, "minus_di": minus_di},
            signal, strength, 0.8, {"trend_strength": adx.iloc[-1]}
        )
    
    @staticmethod
    def mass_index(high: pd.Series, low: pd.Series, period: int = 9, ma_period: int = 25) -> IndicatorResult:
        """Mass Index"""
        hl_range = high - low
        ema1 = hl_range.ewm(span=period).mean()
        ema2 = ema1.ewm(span=period).mean()
        mass_index = (ema1 / ema2).rolling(ma_period).sum()
        
        if mass_index.iloc[-1] > 27:
            signal, strength = "SELL", min((mass_index.iloc[-1] - 27) / 10, 1.0)
        elif mass_index.iloc[-1] < 26.5:
            signal, strength = "BUY", 0.5
        else:
            signal, strength = "NEUTRAL", 0.0
        
        return IndicatorResult(mass_index, signal, strength, 0.6, {"reversal_indicator": True})
    
    # ===========================================
    # VOLUME INDICATORS (15)
    # ===========================================
    
    @staticmethod
    def volume_weighted_average_price(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> IndicatorResult:
        """Enhanced VWAP with bands"""
        typical_price = (high + low + close) / 3
        vwap = (typical_price * volume).cumsum() / volume.cumsum()
        
        # VWAP Standard Deviation Bands
        price_vol_product = typical_price * volume
        squared_diff = ((typical_price - vwap) ** 2) * volume
        variance = squared_diff.cumsum() / volume.cumsum()
        std_dev = np.sqrt(variance)
        
        upper_band_1 = vwap + std_dev
        lower_band_1 = vwap - std_dev
        upper_band_2 = vwap + 2 * std_dev
        lower_band_2 = vwap - 2 * std_dev
        
        current_price = close.iloc[-1]
        if current_price > upper_band_2.iloc[-1]:
            signal, strength = "STRONG_SELL", 0.9
        elif current_price > upper_band_1.iloc[-1]:
            signal, strength = "SELL", 0.6
        elif current_price < lower_band_2.iloc[-1]:
            signal, strength = "STRONG_BUY", 0.9
        elif current_price < lower_band_1.iloc[-1]:
            signal, strength = "BUY", 0.6
        else:
            signal, strength = "NEUTRAL", 0.0
        
        return IndicatorResult(
            {"vwap": vwap, "upper_1": upper_band_1, "lower_1": lower_band_1, 
             "upper_2": upper_band_2, "lower_2": lower_band_2},
            signal, strength, 0.85, {"institutional_level": True}
        )
    
    @staticmethod
    def on_balance_volume_enhanced(close: pd.Series, volume: pd.Series) -> IndicatorResult:
        """Enhanced On Balance Volume with trend analysis"""
        # Ensure volume is a pandas Series
        if not isinstance(volume, pd.Series):
            volume = pd.Series(volume)
        
        obv = pd.Series(0, index=close.index)
        obv.iloc[0] = volume.iloc[0]
        
        for i in range(1, len(close)):
            if close.iloc[i] > close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
            elif close.iloc[i] < close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        
        # OBV trends
        obv_sma_short = obv.rolling(10).mean()
        obv_sma_long = obv.rolling(20).mean()
        
        if obv.iloc[-1] > obv_sma_short.iloc[-1] and obv_sma_short.iloc[-1] > obv_sma_long.iloc[-1]:
            signal, strength = "BUY", 0.8
        elif obv.iloc[-1] < obv_sma_short.iloc[-1] and obv_sma_short.iloc[-1] < obv_sma_long.iloc[-1]:
            signal, strength = "SELL", 0.8
        else:
            signal, strength = "NEUTRAL", 0.0
        
        return IndicatorResult(
            {"obv": obv, "obv_sma_short": obv_sma_short, "obv_sma_long": obv_sma_long},
            signal, strength, 0.7, {"volume_trend": True}
        )
    
    @staticmethod
    def accumulation_distribution_line(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> IndicatorResult:
        """Accumulation/Distribution Line"""
        mfm = ((close - low) - (high - close)) / (high - low)
        mfm = mfm.fillna(0)  # Handle division by zero
        mfv = mfm * volume
        ad_line = mfv.cumsum()
        
        # Trend analysis
        ad_sma = ad_line.rolling(20).mean()
        signal = "BUY" if ad_line.iloc[-1] > ad_sma.iloc[-1] else "SELL"
        strength = abs(ad_line.iloc[-1] - ad_sma.iloc[-1]) / abs(ad_sma.iloc[-1]) if ad_sma.iloc[-1] != 0 else 0
        
        return IndicatorResult(ad_line, signal, min(strength, 1.0), 0.75, {"accumulation_distribution": True})
    
    @staticmethod
    def money_flow_index(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 14) -> IndicatorResult:
        """Money Flow Index (Volume-weighted RSI)"""
        typical_price = (high + low + close) / 3
        money_flow = typical_price * volume
        
        # Positive and negative money flow
        positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
        negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0)
        
        # Money Flow Ratio
        positive_flow_sum = positive_flow.rolling(period).sum()
        negative_flow_sum = negative_flow.rolling(period).sum()
        money_ratio = positive_flow_sum / negative_flow_sum
        
        mfi = 100 - (100 / (1 + money_ratio))
        
        if mfi.iloc[-1] > 80:
            signal, strength = "SELL", (mfi.iloc[-1] - 80) / 20
        elif mfi.iloc[-1] < 20:
            signal, strength = "BUY", (20 - mfi.iloc[-1]) / 20
        else:
            signal, strength = "NEUTRAL", 0.0
        
        return IndicatorResult(mfi, signal, strength, 0.8, {"period": period, "volume_rsi": True})
    
    @staticmethod
    def chaikin_money_flow(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 20) -> IndicatorResult:
        """Chaikin Money Flow"""
        mfm = ((close - low) - (high - close)) / (high - low)
        mfm = mfm.fillna(0)
        mfv = mfm * volume
        
        cmf = mfv.rolling(period).sum() / volume.rolling(period).sum()
        
        if cmf.iloc[-1] > 0.1:
            signal, strength = "BUY", min(cmf.iloc[-1] * 2, 1.0)
        elif cmf.iloc[-1] < -0.1:
            signal, strength = "SELL", min(abs(cmf.iloc[-1]) * 2, 1.0)
        else:
            signal, strength = "NEUTRAL", 0.0
        
        return IndicatorResult(cmf, signal, strength, 0.75, {"period": period, "buying_pressure": True})
    
    @staticmethod
    def volume_rate_of_change(volume: pd.Series, period: int = 12) -> IndicatorResult:
        """Volume Rate of Change"""
        # Ensure volume is a pandas Series
        if not isinstance(volume, pd.Series):
            volume = pd.Series(volume)
        
        # Calculate volume rate of change with safety checks
        volume_shifted = volume.shift(period)
        vroc = ((volume - volume_shifted) / volume_shifted.replace(0, np.nan)) * 100
        vroc = vroc.fillna(0)  # Replace NaN with 0
        vroc = vroc.replace([np.inf, -np.inf], 0)  # Replace infinite values with 0
        
        vroc_sma = vroc.rolling(10).mean()
        
        if not vroc.empty and not vroc_sma.empty:
            signal = "BUY" if vroc.iloc[-1] > vroc_sma.iloc[-1] else "SELL"
            strength = min(abs(vroc.iloc[-1]) / 100, 1.0)
        else:
            signal = "NEUTRAL"
            strength = 0.0
        
        return IndicatorResult(vroc, signal, strength, 0.6, {"period": period, "volume_momentum": True})
    
    @staticmethod
    def price_volume_trend(close: pd.Series, volume: pd.Series) -> IndicatorResult:
        """Price Volume Trend"""
        price_change_pct = close.pct_change()
        pvt = (price_change_pct * volume).cumsum()
        
        pvt_sma = pvt.rolling(20).mean()
        signal = "BUY" if pvt.iloc[-1] > pvt_sma.iloc[-1] else "SELL"
        strength = abs(pvt.iloc[-1] - pvt_sma.iloc[-1]) / abs(pvt_sma.iloc[-1]) if pvt_sma.iloc[-1] != 0 else 0
        
        return IndicatorResult(pvt, signal, min(strength, 1.0), 0.7, {"volume_trend": True})
    
    @staticmethod
    def ease_of_movement(high: pd.Series, low: pd.Series, volume: pd.Series, period: int = 14) -> IndicatorResult:
        """Ease of Movement"""
        distance_moved = ((high + low) / 2) - ((high.shift(1) + low.shift(1)) / 2)
        box_height = volume / (high - low)
        
        emv = distance_moved / box_height
        emv = emv.replace([np.inf, -np.inf], 0)  # Handle division issues
        emv_sma = emv.rolling(period).mean()
        
        signal = "BUY" if emv_sma.iloc[-1] > 0 else "SELL"
        strength = abs(emv_sma.iloc[-1])
        
        return IndicatorResult(emv_sma, signal, min(strength, 1.0), 0.6, {"period": period, "price_volume": True})