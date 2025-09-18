import sys
from datetime import datetime, timedelta, timezone

# Ensure current directory is on path
if __name__ == "__main__":
    try:
        from indicators.core_indicator_base import IndicatorConfig
        from indicators.volume_indicators import MFI, AccumulationDistribution
    except Exception as e:
        print("Import error:", e)
        print("sys.path:", sys.path)
        raise

    cfg = IndicatorConfig(period=14, hft_mode=False)

    mfi = MFI(cfg)
    ad = AccumulationDistribution(cfg)

    now = datetime.now(timezone.utc)

    # Generate 40 bars of synthetic OHLCV
    for i in range(40):
        # Create a simple oscillating price series with OHLC
        base = 100.0 + i * 0.2
        high = base + (i % 5) * 0.1
        low = base - (i % 5) * 0.1
        close = base + ((-1)**i) * 0.05
        vol = 1000 + ((i % 10) * 100)
        ts = now + timedelta(minutes=i)

        ohlc = {"high": high, "low": low, "close": close}

        mfi_res = mfi.calculate(ohlc, vol, ts)
        ad_res = ad.calculate(ohlc, vol, ts)

        if mfi_res is not None and ad_res is not None and i % 5 == 0:
            print(f"i={i:02d} MFI={mfi_res.value:.2f} signal={mfi_res.signal.name} conf={mfi_res.confidence:.2f} | AD={ad_res.value:.2f} signal={ad_res.signal.name} conf={ad_res.confidence:.2f}")

    # Print final results
    last_mfi = mfi.results[-1] if mfi.results else None
    last_ad = ad.results[-1] if ad.results else None

    print("Final MFI:", None if last_mfi is None else {
        "value": round(last_mfi.value, 4),
        "signal": last_mfi.signal.name,
        "conf": round(last_mfi.confidence, 4)
    })
    print("Final AD:", None if last_ad is None else {
        "value": round(last_ad.value, 4),
        "signal": last_ad.signal.name,
        "conf": round(last_ad.confidence, 4)
    })