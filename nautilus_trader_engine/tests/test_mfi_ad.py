"""
Focused unit tests for consolidated MFI and Accumulation/Distribution indicators

Ensures:
- Correct imports from consolidated indicators API
- Proper handling of OHLC inputs and volume
- Reasonable value ranges and metadata presence
- Robustness of reset behavior
"""
import os
import sys
from datetime import datetime, timedelta
import math
import random
import numpy as np
import pytest

# Ensure project root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nautilus_trader_engine.indicators.traditional.volume_indicators import (
    MFI,
    AccumulationDistribution,
)
from nautilus_trader_engine.indicators.core_indicator_base import (
    IndicatorConfig,
    SignalType,
)


def _generate_ohlcv(n: int = 150, seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    base_price = 100.0
    close = [base_price]
    for _ in range(n):
        close.append(max(0.01, close[-1] * (1.0 + np.random.normal(0, 0.01))))
    close = close[1:]
    close = np.array(close)

    # Construct OHLC around close with realistic ranges
    high = close * (1 + np.abs(np.random.normal(0, 0.01, size=n)))
    low = close * (1 - np.abs(np.random.normal(0, 0.01, size=n)))
    # Ensure high >= max(open, close) and low <= min(open, close)
    open_ = np.r_[close[0], close[:-1]]
    high = np.maximum.reduce([high, close, open_])
    low = np.minimum.reduce([low, close, open_])

    # Lognormal volumes
    volume = np.random.lognormal(mean=12.5, sigma=0.6, size=n)
    volume = volume.astype(float)

    # Timestamps
    start = datetime(2023, 1, 1)
    times = [start + timedelta(minutes=i) for i in range(n)]

    # Build bar dicts compatible with indicator duck-typing
    bars = [
        {"high": float(h), "low": float(l), "close": float(c)}
        for h, l, c in zip(high, low, close)
    ]
    return bars, volume.tolist(), times


@pytest.mark.parametrize("period", [10, 14, 21])
def test_mfi_values_and_metadata(period):
    config = IndicatorConfig(period=period, memory_limit=512, enable_hft_optimizations=False)
    mfi = MFI(config)

    bars, vols, times = _generate_ohlcv(n=160)
    results = []
    for bar, v, ts in zip(bars, vols, times):
        res = mfi.calculate(bar, v, ts)
        if res is not None:
            results.append(res)

    # Expect at least (n - period) results
    assert len(results) >= max(0, len(bars) - period)

    last = results[-1]
    # MFI value should be within [0, 100]
    assert 0.0 <= float(last.value) <= 100.0
    # Signal is a SignalType enum member
    assert isinstance(last.signal, SignalType)
    assert 0.0 <= float(last.confidence) <= 1.0

    # Metadata checks
    md = last.metadata or {}
    for key in [
        "period",
        "positive_flow",
        "negative_flow",
        "money_ratio",
        "typical_price",
        "money_flow",
        "classic_mfi",
        "ewm_pos_flow",
        "ewm_neg_flow",
        "alpha",
        "overbought_threshold",
        "oversold_threshold",
    ]:
        assert key in md

    # Reset behavior: after reset, first compute should return None
    mfi.reset()
    assert mfi.calculate(bars[0], vols[0], times[0]) is None


@pytest.mark.parametrize("period", [10, 14, 21])
def test_accumulation_distribution_values_and_metadata(period):
    config = IndicatorConfig(period=period, memory_limit=512, enable_hft_optimizations=False)
    ad = AccumulationDistribution(config)

    bars, vols, times = _generate_ohlcv(n=160)
    results = []
    for bar, v, ts in zip(bars, vols, times):
        res = ad.calculate(bar, v, ts)
        if res is not None:
            results.append(res)

    assert len(results) > 0
    last = results[-1]

    # A/D can be any real number; ensure it's finite
    assert isinstance(last.value, (int, float))
    assert math.isfinite(float(last.value))

    assert isinstance(last.signal, SignalType)
    assert 0.0 <= float(last.confidence) <= 1.0

    md = last.metadata or {}
    for key in [
        "mf_multiplier",
        "mf_volume",
        "ad_momentum",
        "accumulation_strength",
        "ad_trend",
        "ewm_ad",
        "alpha",
    ]:
        assert key in md

    # Reset behavior
    ad.reset()
    res0 = ad.calculate(bars[0], vols[0], times[0])
    assert res0 is not None
    assert math.isfinite(float(res0.value))