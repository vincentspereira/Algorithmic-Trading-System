import numpy as np
from nautilus_trader.core.datetime import dt_to_nanos
from nautilus_trader.core.message import Event
from nautilus_trader.indicators.base.indicator import Indicator
from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import BarAggregation, PriceType

from ....multi_timeframe_engine.aggregator import MultiTimeframeAggregator


class ForecastingIndicator(Indicator):
    def __init__(
        self,
        period: int = 20,
        forecast_horizon: int = 5,
        timeframe: str | None = None,
        aggregator: MultiTimeframeAggregator | None = None,
    ):
        super().__init__()
        self.period = period
        self.forecast_horizon = forecast_horizon
        self.timeframe = timeframe
        self.aggregator = aggregator
        self.warmup = period + forecast_horizon
        self._close_prices = []
        self.add_managed_variable("_close_prices", list)

    def handle_event(self, event: Event) -> None:
        if isinstance(event, Bar) and event.bar_type.aggregation == BarAggregation.NATURAL:
            if self.aggregator and self.timeframe:
                data = self.aggregator.get_data(self.timeframe)
                if not data.empty:
                    self._close_prices = data["close"].tolist()
            else:
                self._close_prices.append(event.close)

            if len(self._close_prices) > self.warmup:
                self._close_prices.pop(0)

            if self.is_ready:
                forecast = self._generate_forecast()
                ts = event.ts_event
                if self.aggregator and self.timeframe:
                    data = self.aggregator.get_data(self.timeframe)
                    if not data.empty:
                        ts = dt_to_nanos(data.index[-1])

                self.append(value=forecast, ts=ts)

    def _generate_forecast(self):
        # Placeholder for a real forecasting model
        # Using a simple moving average for now
        if len(self._close_prices) < self.period:
            return np.nan
        return np.mean(self._close_prices[-self.period :])

    @property
    def is_ready(self) -> bool:
        if self.aggregator and self.timeframe:
            data = self.aggregator.get_data(self.timeframe)
            if data.empty:
                return False
            return len(data) >= self.warmup
        return len(self._close_prices) >= self.warmup