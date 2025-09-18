from datetime import datetime, timedelta
import math
import sys
sys.path.append('nautilus_trader_engine')
from indicators.volume_indicators import MFI, AccumulationDistribution
from indicators.core_indicator_base import IndicatorConfig

def run():
    cfg = IndicatorConfig(period=14)
    mfi = MFI(cfg)
    ad = AccumulationDistribution(cfg)
    t = datetime.utcnow()
    last_mfi = None
    last_ad = None
    for i in range(40):
        base = 100 + math.sin(i/3.0)*2
        h = base + 1
        l = base - 1
        c = base + 0.3
        price = {'high': h, 'low': l, 'close': c}
        vol = 1000 + ((i % 10) * 100)
        r1 = mfi.calculate(price, vol, t + timedelta(minutes=i))
        r2 = ad.calculate(price, vol, t + timedelta(minutes=i))
        if r1 is not None:
            last_mfi = r1.value
        if r2 is not None:
            last_ad = r2.value
    print('MFI:', last_mfi)
    print('AD:', last_ad)

if __name__ == '__main__':
    run()
