"""
TechnicalIndicators compatibility shim

Provides a simplified set of technical indicator computations with
method names and signatures used by the test suite. The focus is on
correct interfaces and reasonable calculations rather than
institutional-grade precision. This can be swapped with
full-featured implementations later while keeping tests stable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd


@dataclass
class IndicatorResult:
    value: Any
    signal: str = "neutral"
    strength: float = 0.0
    metadata: Optional[Dict[str, Any]] = None


class TechnicalIndicators:
    @staticmethod
    def _alpha(period: int) -> float:
        period = max(int(period), 1)
        return 1.0 / float(period)

    @staticmethod
    def _safe_last(series: pd.Series) -> float:
        if isinstance(series, pd.Series) and len(series) > 0:
            return float(series.iloc[-1])
        return float("nan")

    # Trend / Moving Averages
    @staticmethod
    def sma(close: pd.Series, period: int = 20) -> IndicatorResult:
        sma_series = close.rolling(window=period, min_periods=1).mean()
        last_close = TechnicalIndicators._safe_last(close)
        last_sma = TechnicalIndicators._safe_last(sma_series)
        signal = "neutral"
        if np.isfinite(last_close) and np.isfinite(last_sma) and last_sma != 0:
            if last_close > last_sma:
                signal = "buy"
            elif last_close < last_sma:
                signal = "sell"
        strength = 0.0 if not np.isfinite(last_sma) or last_sma == 0 else abs(last_close - last_sma) / abs(last_sma)
        return IndicatorResult(value=sma_series, signal=signal, strength=float(np.clip(strength, 0.0, 1.0)))

    @staticmethod
    def vwma(close: pd.Series, volume: pd.Series, period: int = 20) -> IndicatorResult:
        vol_sum = volume.rolling(window=period, min_periods=1).sum()
        pv_sum = (close * volume).rolling(window=period, min_periods=1).sum()
        vwma_series = pv_sum / vol_sum.replace(0, np.nan)
        last_close = TechnicalIndicators._safe_last(close)
        last_vwma = TechnicalIndicators._safe_last(vwma_series)
        signal = "neutral"
        if np.isfinite(last_close) and np.isfinite(last_vwma):
            signal = "buy" if last_close > last_vwma else "sell" if last_close < last_vwma else "neutral"
        strength = 0.0 if not np.isfinite(last_vwma) or last_vwma == 0 else abs(last_close - last_vwma) / abs(last_vwma)
        return IndicatorResult(value=vwma_series, signal=signal, strength=float(np.clip(strength, 0.0, 1.0)))

    @staticmethod
    def vw_ema(close: pd.Series, volume: pd.Series, period: int = 20) -> IndicatorResult:
        a = TechnicalIndicators._alpha(period)
        num = (close * volume).ewm(alpha=a, adjust=False, min_periods=1).mean()
        den = volume.ewm(alpha=a, adjust=False, min_periods=1).mean()
        vw_ema_series = num / den.replace(0, np.nan)
        last_close = TechnicalIndicators._safe_last(close)
        last_vwema = TechnicalIndicators._safe_last(vw_ema_series)
        signal = "neutral"
        if np.isfinite(last_close) and np.isfinite(last_vwema):
            signal = "buy" if last_close > last_vwema else "sell" if last_close < last_vwema else "neutral"
        strength = 0.0 if not np.isfinite(last_vwema) or last_vwema == 0 else abs(last_close - last_vwema) / abs(last_vwema)
        return IndicatorResult(value=vw_ema_series, signal=signal, strength=float(np.clip(strength, 0.0, 1.0)))

    # Momentum
    @staticmethod
    def rsi(close: pd.Series, period: int = 14) -> IndicatorResult:
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        a = TechnicalIndicators._alpha(period)
        avg_gain = gain.ewm(alpha=a, adjust=False, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=a, adjust=False, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        last_rsi = TechnicalIndicators._safe_last(rsi)
        signal = "neutral"
        if np.isfinite(last_rsi):
            if last_rsi > 70:
                signal = "sell"
            elif last_rsi < 30:
                signal = "buy"
            else:
                signal = "neutral"
        strength = 0.0 if not np.isfinite(last_rsi) else abs(last_rsi - 50.0) / 50.0
        return IndicatorResult(value=rsi, signal=signal, strength=float(np.clip(strength, 0.0, 1.0)))

    @staticmethod
    def vw_rsi(close: pd.Series, volume: pd.Series, period: int = 14) -> IndicatorResult:
        # Compute volume-weighted price using EMA ratio, then apply RSI
        a = TechnicalIndicators._alpha(period)
        num = (close * volume).ewm(alpha=a, adjust=False, min_periods=1).mean()
        den = volume.ewm(alpha=a, adjust=False, min_periods=1).mean()
        vw_price = num / den.replace(0, np.nan)
        return TechnicalIndicators.rsi(vw_price, period)

    @staticmethod
    def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal_period: int = 9) -> IndicatorResult:
        a_fast = TechnicalIndicators._alpha(fast)
        a_slow = TechnicalIndicators._alpha(slow)
        ema_fast = close.ewm(alpha=a_fast, adjust=False, min_periods=1).mean()
        ema_slow = close.ewm(alpha=a_slow, adjust=False, min_periods=1).mean()
        macd = ema_fast - ema_slow
        a_sig = TechnicalIndicators._alpha(signal_period)
        sig = macd.ewm(alpha=a_sig, adjust=False, min_periods=1).mean()
        hist = macd - sig
        value = {
            "macd": macd,
            "signal": sig,
            "histogram": hist,
        }
        last_hist = TechnicalIndicators._safe_last(hist)
        last_macd = TechnicalIndicators._safe_last(macd)
        signal = "buy" if last_hist > 0 else "sell" if last_hist < 0 else "neutral"
        denom = abs(last_macd) + 1e-9
        strength = float(np.clip(abs(last_hist) / denom, 0.0, 1.0))
        return IndicatorResult(value=value, signal=signal, strength=strength)

    @staticmethod
    def vw_macd(close: pd.Series, volume: pd.Series, fast: int = 12, slow: int = 26, signal_period: int = 9) -> IndicatorResult:
        a_slow = TechnicalIndicators._alpha(slow)
        a_fast = TechnicalIndicators._alpha(fast)
        a_sig = TechnicalIndicators._alpha(signal_period)
        vw_price_fast = (close * volume).ewm(alpha=a_fast, adjust=False, min_periods=1).mean() / volume.ewm(alpha=a_fast, adjust=False, min_periods=1).mean()
        vw_price_slow = (close * volume).ewm(alpha=a_slow, adjust=False, min_periods=1).mean() / volume.ewm(alpha=a_slow, adjust=False, min_periods=1).mean()
        vw_macd = vw_price_fast - vw_price_slow
        vw_signal = vw_macd.ewm(alpha=a_sig, adjust=False, min_periods=1).mean()
        vw_hist = vw_macd - vw_signal
        value = {
            "vw_macd": vw_macd,
            "vw_signal": vw_signal,
            "vw_histogram": vw_hist,
        }
        last_hist = TechnicalIndicators._safe_last(vw_hist)
        last_macd = TechnicalIndicators._safe_last(vw_macd)
        signal = "buy" if last_hist > 0 else "sell" if last_hist < 0 else "neutral"
        denom = abs(last_macd) + 1e-9
        strength = float(np.clip(abs(last_hist) / denom, 0.0, 1.0))
        return IndicatorResult(value=value, signal=signal, strength=strength)

    # Volatility
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> IndicatorResult:
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        a = TechnicalIndicators._alpha(period)
        atr_series = tr.ewm(alpha=a, adjust=False, min_periods=1).mean()
        return IndicatorResult(value=atr_series, signal="neutral", strength=0.0)

    @staticmethod
    def vw_atr(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 14) -> IndicatorResult:
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        a = TechnicalIndicators._alpha(period)
        num = (tr * volume).ewm(alpha=a, adjust=False, min_periods=1).mean()
        den = volume.ewm(alpha=a, adjust=False, min_periods=1).mean()
        vw_atr_series = num / den.replace(0, np.nan)
        return IndicatorResult(value=vw_atr_series, signal="neutral", strength=0.0)

    @staticmethod
    def vw_atrp(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 14) -> IndicatorResult:
        atr_res = TechnicalIndicators.vw_atr(high, low, close, volume, period)
        atrp = (atr_res.value / close.replace(0, np.nan)) * 100.0
        return IndicatorResult(value=atrp, signal="neutral", strength=0.0)

    # Volatility Bands
    @staticmethod
    def bollinger_bands(close: pd.Series, period: int = 20, num_std: float = 2.0) -> IndicatorResult:
        mid = close.rolling(window=period, min_periods=1).mean()
        std = close.rolling(window=period, min_periods=1).std(ddof=0).fillna(0.0)
        upper = mid + num_std * std
        lower = mid - num_std * std
        last_upper = TechnicalIndicators._safe_last(upper)
        last_lower = TechnicalIndicators._safe_last(lower)
        last_mid = TechnicalIndicators._safe_last(mid)
        last_close = TechnicalIndicators._safe_last(close)
        width = (last_upper - last_lower) if np.isfinite(last_upper) and np.isfinite(last_lower) else np.nan
        percent = (last_close - last_lower) / width if width and width != 0 else np.nan
        value = {
            "upper": last_upper,
            "middle": last_mid,
            "lower": last_lower,
            "percent": float(np.clip(percent, 0.0, 1.0)) if np.isfinite(percent) else float("nan"),
        }
        signal = "buy" if percent is not np.nan and percent < 0.2 else "sell" if percent is not np.nan and percent > 0.8 else "neutral"
        return IndicatorResult(value=value, signal=signal, strength=0.0)

    # Volume / Price-Volume
    @staticmethod
    def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> IndicatorResult:
        typical = (high + low + close) / 3.0
        cum_pv = (typical * volume).cumsum()
        cum_v = volume.cumsum()
        vwap_series = cum_pv / cum_v.replace(0, np.nan)
        last_close = TechnicalIndicators._safe_last(close)
        last_vwap = TechnicalIndicators._safe_last(vwap_series)
        signal = "neutral"
        if np.isfinite(last_close) and np.isfinite(last_vwap):
            signal = "buy" if last_close > last_vwap else "sell" if last_close < last_vwap else "neutral"
        strength = 0.0 if not np.isfinite(last_vwap) or last_vwap == 0 else abs(last_close - last_vwap) / abs(last_vwap)
        return IndicatorResult(value=vwap_series, signal=signal, strength=float(np.clip(strength, 0.0, 1.0)))