import math
import random
from datetime import datetime, timedelta

try:
    from .momentum_indicators import (
        RSI, MACD, Stochastic, WilliamsR,
        create_rsi, create_macd, create_stochastic, create_williams_r
    )
    from .core_indicator_base import IndicatorConfig
except Exception as e:
    print(f"IMPORT_ERROR: {e}")
    raise


def run_sanity():
    random.seed(42)
    n = 300
    # Generate a synthetic price series with trend + noise
    prices = []
    t0 = 100.0
    for i in range(n):
        base = t0 + 0.05 * i + 2.0 * math.sin(i * 0.2)
        noise = random.uniform(-0.5, 0.5)
        prices.append(base + noise)
    volumes = [abs(1000.0 + 250.0 * math.sin(i * 0.37) + random.uniform(-200, 200)) for i in range(n)]

    # Instantiate via factories
    rsi = create_rsi(period=14, enable_volume_weighting=True)
    wr = create_williams_r(period=14, enable_volume_weighting=True)
    macd = create_macd(fast_period=12, slow_period=26, signal_period=9, enable_volume_weighting=True)
    stoch = create_stochastic(k_period=14, d_period=3, smooth_k=3, enable_volume_weighting=True)

    start = datetime.now() - timedelta(seconds=n)
    ts = start

    print("SANITY_START")
    for i in range(n):
        p = prices[i]
        v = volumes[i]
        ts = ts + timedelta(seconds=1)

        rsi_res = rsi.update(p, v, ts)
        wr_res = wr.update(p, v, ts)
        macd_res = macd.update(p, v, ts)
        stoch_res = stoch.update(p, v, ts)

        # Compose a single line summary per step (ensures > 200 lines total)
        rsi_sig = rsi_res.signal.signal_type.name if rsi_res.signal else 'NONE'
        wr_sig = wr_res.signal.signal_type.name if wr_res.signal else 'NONE'
        macd_sig = macd_res.signal.signal_type.name if macd_res.signal else 'NONE'
        stoch_sig = stoch_res.signal.signal_type.name if stoch_res.signal else 'NONE'
        rsi_val = f"{getattr(rsi, 'rsi', 0.0):.2f}"
        wr_val = f"{getattr(wr, 'williams_r_normalized', 0.0):.2f}"
        macd_val = f"{getattr(macd, 'histogram', 0.0):.4f}"
        stoch_val = f"{getattr(stoch, 'k_percent', 0.0):.2f}"
        print(f"i={i:03d} p={p:.2f} v={v:.1f} rsi={rsi_val} rsisig={rsi_sig} wr={wr_val} wrsig={wr_sig} macd_hist={macd_val} macdsig={macd_sig} stoch_k={stoch_val} stochsig={stoch_sig}")

    # Final attribute checks
    print("FINAL_ATTRS",
          isinstance(rsi, RSI), isinstance(wr, WilliamsR), isinstance(macd, MACD), isinstance(stoch, Stochastic))
    print("FACTORY_CHECKS",
          isinstance(create_rsi(), RSI), isinstance(create_williams_r(), WilliamsR))
    print("SANITY_END")


if __name__ == "__main__":
    run_sanity()