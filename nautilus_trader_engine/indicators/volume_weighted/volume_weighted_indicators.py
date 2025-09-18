"""
Volume-weighted indicators compatibility layer for tests.

Provides a minimal MarketData container and a VolumeWeightedIndicators
API expected by tests in tests/test_basic_components.py.

This module implements lightweight versions of:
- vw_sma
- vw_ema
- vw_macd (returns line, signal, histogram)
- vw_mfi (Money Flow Index)
- atr (wrapper over high/low/close)
- choppy_market_index (Choppiness Index)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
import pandas as pd

# Reuse existing implementations where possible
from ..consolidated_indicators import ConsolidatedIndicators as TechnicalIndicators



@dataclass
class MarketData:
    open: pd.Series
    high: pd.Series
    low: pd.Series
    close: pd.Series
    volume: pd.Series


class VolumeWeightedIndicators:
    @staticmethod
    def vw_sma(close: pd.Series, volume: pd.Series, period: int = 20) -> pd.Series:
        vol_sum = volume.rolling(window=period, min_periods=1).sum()
        pv_sum = (close * volume).rolling(window=period, min_periods=1).sum()
        return pv_sum / vol_sum.replace(0, np.nan)

    @staticmethod
    def vw_ema(close: pd.Series, volume: pd.Series, period: int = 20) -> pd.Series:
        a = 1.0 / max(int(period), 1)
        num = (close * volume).ewm(alpha=a, adjust=False, min_periods=1).mean()
        den = volume.ewm(alpha=a, adjust=False, min_periods=1).mean()
        return num / den.replace(0, np.nan)

    @staticmethod
    def vw_macd(
        close: pd.Series,
        volume: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal_period: int = 9,
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        # Compute MACD using volume-weighted EMA prices
        a_fast = 1.0 / max(int(fast), 1)
        a_slow = 1.0 / max(int(slow), 1)
        a_sig = 1.0 / max(int(signal_period), 1)

        vw_price_fast = (close * volume).ewm(alpha=a_fast, adjust=False, min_periods=1).mean() / (
            volume.ewm(alpha=a_fast, adjust=False, min_periods=1).mean()
        )
        vw_price_slow = (close * volume).ewm(alpha=a_slow, adjust=False, min_periods=1).mean() / (
            volume.ewm(alpha=a_slow, adjust=False, min_periods=1).mean()
        )
        vw_macd_line = vw_price_fast - vw_price_slow
        vw_signal = vw_macd_line.ewm(alpha=a_sig, adjust=False, min_periods=1).mean()
        vw_histogram = vw_macd_line - vw_signal
        return vw_macd_line, vw_signal, vw_histogram

    @staticmethod
    def vw_mfi(market_data: MarketData, period: int = 14) -> pd.Series:
        # Typical price
        tp = (market_data.high + market_data.low + market_data.close) / 3.0
        # Raw money flow
        rmf = tp * market_data.volume
        # Determine positive/negative flow compared to previous typical price
        delta_tp = tp.diff()
        pos_flow = rmf.where(delta_tp > 0, 0.0)
        neg_flow = rmf.where(delta_tp < 0, 0.0)
        # Rolling sums
        pos_sum = pos_flow.rolling(window=period, min_periods=1).sum()
        neg_sum = neg_flow.rolling(window=period, min_periods=1).sum()
        # Money Flow Index
        mr = pos_sum / neg_sum.replace(0, np.nan)
        mfi = 100.0 - (100.0 / (1.0 + mr))
        # Fill initial values sensibly
        return mfi.fillna(50.0)

    @staticmethod
    def atr(market_data: MarketData, period: int = 14) -> pd.Series:
        res = TechnicalIndicators.atr(market_data.high, market_data.low, market_data.close, period)
        return res.value if hasattr(res, "value") else res

    @staticmethod
    def choppy_market_index(market_data: MarketData, period: int = 14) -> pd.Series:
        # True Range
        prev_close = market_data.close.shift(1)
        tr1 = market_data.high - market_data.low
        tr2 = (market_data.high - prev_close).abs()
        tr3 = (market_data.low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Sum of TR over period
        sum_tr = tr.rolling(window=period, min_periods=1).sum()
        # Price range over period
        hh = market_data.high.rolling(window=period, min_periods=1).max()
        ll = market_data.low.rolling(window=period, min_periods=1).min()
        range_ = (hh - ll).replace(0, np.nan)

        # Choppiness Index (scaled 0..100)
        with np.errstate(divide="ignore", invalid="ignore"):
            chop = 100.0 * (np.log10(sum_tr / range_)) / np.log10(float(max(int(period), 1)))
        chop = chop.replace([np.inf, -np.inf], np.nan).fillna(50.0)
        return chop.clip(lower=0.0, upper=100.0)