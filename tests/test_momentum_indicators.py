import math
from datetime import datetime, timedelta

import pytest

from nautilus_trader_engine.indicators import (
    RSI,
    MACD,
    Stochastic,
    WilliamsR,
    create_rsi,
    create_macd,
    create_stochastic,
    create_williams_r,
)
from nautilus_trader_engine.indicators.core_indicator_base import IndicatorResult


def generate_series(start: float = 100.0, steps: int = 50, step: float = 1.0):
    """Utility to generate a simple monotonic price series with volumes."""
    prices = [start + i * step for i in range(steps)]
    # moderate increasing volume with some variation
    volumes = [1000.0 + (i % 5) * 50.0 for i in range(steps)]
    times = [datetime.now() + timedelta(seconds=i) for i in range(steps)]
    return list(zip(prices, volumes, times))


@pytest.mark.parametrize("period", [14, 10])
def test_rsi_runs_and_outputs_signal(period):
    rsi = create_rsi(period=period)
    series = generate_series(steps=period * 3, step=0.5)

    last_result = None
    for price, vol, ts in series:
        last_result = rsi.update(price=price, volume=vol, timestamp=ts)
        assert isinstance(last_result, IndicatorResult)
        assert isinstance(last_result.value, float)
        assert 0.0 <= last_result.value <= 100.0

    assert isinstance(rsi, RSI)
    assert last_result is not None
    # Expect bullish RSI in an uptrend
    assert rsi.rsi >= 50.0
    assert 0.0 <= rsi.volume_weighted_rsi <= 100.0
    assert last_result.signal is not None
    # Check metadata has RSI components
    meta = last_result.signal.metadata
    assert "rsi_components" in meta
    comps = meta["rsi_components"]
    assert math.isfinite(comps.rsi)
    assert math.isfinite(comps.avg_gain)
    assert math.isfinite(comps.avg_loss)
    # Factory should produce same type
    assert isinstance(create_rsi(period=period), RSI)


def test_macd_runs_and_produces_values():
    macd = create_macd()
    series = generate_series(steps=120, step=0.25)

    last_result = None
    for price, vol, ts in series:
        last_result = macd.update(price=price, volume=vol, timestamp=ts)
        assert isinstance(last_result, IndicatorResult)
        assert isinstance(last_result.value, float)

    assert isinstance(macd, MACD)
    assert last_result is not None
    # MACD line and components should be finite numbers
    assert math.isfinite(macd.macd_line)
    assert math.isfinite(macd.signal_line)
    assert math.isfinite(macd.histogram)
    # Factory sanity
    assert isinstance(create_macd(), MACD)


def test_stochastic_runs_and_within_bounds():
    stoch = create_stochastic()
    # Use a wave-like series to exercise %K/%D logic
    series = []
    base = 100.0
    for i in range(120):
        price = base + 2.0 * math.sin(i / 5.0)
        vol = 1000.0 + (i % 7) * 40.0
        ts = datetime.now() + timedelta(seconds=i)
        series.append((price, vol, ts))

    last_result = None
    for price, vol, ts in series:
        last_result = stoch.update(price=price, volume=vol, timestamp=ts)
        assert isinstance(last_result, IndicatorResult)
        assert isinstance(last_result.value, float)
        assert 0.0 <= last_result.value <= 100.0

    assert isinstance(stoch, Stochastic)
    assert last_result is not None
    assert last_result.signal is not None
    # Factory sanity
    assert isinstance(create_stochastic(), Stochastic)


def test_williams_r_runs_and_metadata():
    wr = create_williams_r(period=14)
    series = generate_series(steps=100, step=0.75)

    last_result = None
    for price, vol, ts in series:
        last_result = wr.update(price=price, volume=vol, timestamp=ts)
        assert isinstance(last_result, IndicatorResult)
        assert isinstance(last_result.value, float)
        assert 0.0 <= last_result.value <= 100.0

    assert isinstance(wr, WilliamsR)
    assert last_result is not None
    assert last_result.signal is not None
    meta = last_result.signal.metadata
    assert "williams_r_components" in meta
    comps = meta["williams_r_components"]
    assert math.isfinite(comps.williams_r_normalized)
    assert 0.0 <= comps.williams_r_normalized <= 100.0
    # Factory sanity
    assert isinstance(create_williams_r(), WilliamsR)