from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.model.data import Bar
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Price
from nautilus_trader.core.message import Event

import indicators.trend_indicators as trend
import indicators.momentum_indicators as momentum
import indicators.volume_indicators as volume
import indicators.volatility_indicators as volatility  # Assuming this exists based on previous patches
from nautilus_trader_engine.indicators.consolidated_indicators import ConsolidatedIndicators


class IndicatorTestStrategy(Strategy):
    """
    A strategy to test all implemented indicators by initializing and updating them without actual trading.
    """

    def __init__(self):
        super().__init__()
        self.instrument_id = None
        # Trend Indicators
        self.sma = trend.SMA(period=10)
        self.ema = trend.EMA(period=10)
        self.vwma = trend.VWMA(period=10)
        self.hma = trend.HMA(period=10)
        self.kama = trend.KAMA(period=10, er_period=10, fast_period=2, slow_period=30)
        self.dema = trend.DEMA(period=10)
        self.tema = trend.TEMA(period=10)
        self.adx = trend.ADX(period=14)
        self.donchian = trend.DonchianChannels(period=20)
        self.choppiness = trend.ChoppinessIndex(period=14)
        # Momentum Indicators
        self.rsi = momentum.RSI(period=14)
        self.macd = momentum.MACD(fast_period=12, slow_period=26, signal_period=9)
        self.stochastic = momentum.StochasticOscillator(k_period=14, d_period=3)
        self.cci = momentum.CCI(period=20)
        self.roc = momentum.ROC(period=12)
        self.ppo = momentum.PPO(fast_period=12, slow_period=26, signal_period=9)
        self.trix = momentum.TRIX(period=15)
        # Volume Indicators
        self.vwap = volume.VWAP(period=10)
        self.obv = volume.OBV()
        self.mfi = volume.MFI(period=14)
        self.cmf = volume.CMF(period=20)
        self.eom = volume.EOM(period=14)
        self.nvi = volume.NVI()
        # Volatility Indicators (assuming implemented)
        self.atr = volatility.ATR(period=14)  # Example, add all

    def on_start(self):
        self.instrument_id = self.cache.instruments()[0].id  # Assume first instrument
        bar_type = self.cache.bar_types(self.instrument_id)[0]  # Assume first bar type
        self.register_indicator_for_bars(bar_type, self.sma)
        self.register_indicator_for_bars(bar_type, self.ema)
        self.register_indicator_for_bars(bar_type, self.vwma)
        self.register_indicator_for_bars(bar_type, self.hma)
        self.register_indicator_for_bars(bar_type, self.kama)
        self.register_indicator_for_bars(bar_type, self.dema)
        self.register_indicator_for_bars(bar_type, self.tema)
        self.register_indicator_for_bars(bar_type, self.adx)
        self.register_indicator_for_bars(bar_type, self.donchian)
        self.register_indicator_for_bars(bar_type, self.choppiness)
        self.register_indicator_for_bars(bar_type, self.rsi)
        self.register_indicator_for_bars(bar_type, self.macd)
        self.register_indicator_for_bars(bar_type, self.stochastic)
        self.register_indicator_for_bars(bar_type, self.cci)
        self.register_indicator_for_bars(bar_type, self.roc)
        self.register_indicator_for_bars(bar_type, self.ppo)
        self.register_indicator_for_bars(bar_type, self.trix)
        self.register_indicator_for_bars(bar_type, self.vwap)
        self.register_indicator_for_bars(bar_type, self.obv)
        self.register_indicator_for_bars(bar_type, self.mfi)
        self.register_indicator_for_bars(bar_type, self.cmf)
        self.register_indicator_for_bars(bar_type, self.eom)
        self.register_indicator_for_bars(bar_type, self.nvi)
        self.register_indicator_for_bars(bar_type, self.atr)  # Add more

    def on_bar(self, bar: Bar):
        # Log values to verify updates
        self.log.info(f"SMA: {self.sma.value}")
        self.log.info(f"EMA: {self.ema.value}")
        # Add logging for all indicators
        # For testing, we don't submit orders

    def on_event(self, event: Event):
        pass  # Handle events if needed

    def on_stop(self):
        pass

    def on_reset(self):
        pass