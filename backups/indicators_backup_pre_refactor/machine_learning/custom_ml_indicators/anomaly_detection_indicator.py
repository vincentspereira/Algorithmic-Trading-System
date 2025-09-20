import random
from nautilus_trader.core.message import Event
from nautilus_trader.indicators.base.indicator import Indicator
from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import BarAggregation

from ....multi_timeframe_engine.aggregator import MultiTimeframeAggregator


class AnomalyDetectionIndicator(Indicator):
    def __init__(
        self,
        period: int = 50,
        threshold: float = 2.5,
        timeframe: str | None = None,
        aggregator: MultiTimeframeAggregator | None = None,
    ):
        super().__init__()
        self.period = period
        self.threshold = threshold
        self.timeframe = timeframe
        self.aggregator = aggregator
        self._returns = []
        self.add_managed_variable("_returns", list)

    def handle_event(self, event: Event) -> None:
        if isinstance(event, Bar) and event.bar_type.aggregation == BarAggregation.NATURAL:
            if self.aggregator and self.timeframe:
                data = self.aggregator.get_data(self.timeframe)
                if len(data) > 1:
                    self._returns = data["close"].pct_change().dropna().tolist()
            else:
                if len(self.values) > 0:
                    current_return = (event.close - self.values[-1].value) / self.values[-1].value
                    self._returns.append(current_return)

            if len(self._returns) > self.period:
                self._returns.pop(0)

            if self.is_ready:
                mean_return = sum(self._returns) / len(self._returns)
                std_dev = (sum([(x - mean_return) ** 2 for x in self._returns]) / len(self._returns)) ** 0.5

                if std_dev > 0:
                    z_score = (self._returns[-1] - mean_return) / std_dev
                    if abs(z_score) > self.threshold:
                        self.append(value=z_score, ts=event.ts_event)
                    else:
                        self.append(value=0, ts=event.ts_event)
                else:
                    self.append(value=0, ts=event.ts_event)
            else:
                self.append(value=event.close, ts=event.ts_event)  # Initial value to calculate returns

    @property
    def is_ready(self) -> bool:
        if self.aggregator and self.timeframe:
            data = self.aggregator.get_data(self.timeframe)
            return len(data) >= self.period
        return len(self._returns) >= self.period