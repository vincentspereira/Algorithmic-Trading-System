"""Volume-Weighted Money Flow Index (VW-MFI) Indicator."""

from collections import deque

import numpy as np
from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import (
    MultiTimeframeIndicator,
    MultiTimeframeIndicatorConfig,
)


class VWMFIConfig(MultiTimeframeIndicatorConfig):
    """
    Configuration for the VW-MFI indicator.

    Attributes:
        period (int): The period for the MFI calculation.
    """

    period: int = 14


class VWMFI(MultiTimeframeIndicator):
    """
    Volume-Weighted Money Flow Index (VW-MFI) indicator.
    """

    def __init__(self, config: VWMFIConfig):
        super().__init__(config)
        self.period = config.period
        self.values = deque(maxlen=config.buffer_size)
        self.typical_prices = deque(maxlen=self.period + 1)
        self.positive_flow = deque(maxlen=self.period)
        self.negative_flow = deque(maxlen=self.period)

    @property
    def is_ready(self) -> bool:
        return len(self.values) > 0

    def on_aggregated_bar(self, bar: Bar):
        typical_price = (bar.high + bar.low + bar.close) / 3.0
        self.typical_prices.append(typical_price)

        if len(self.typical_prices) < 2:
            self.values.append(50.0)  # Default value when not enough data
            return

        raw_money_flow = typical_price * bar.volume

        if typical_price > self.typical_prices[-2]:
            self.positive_flow.append(raw_money_flow)
            self.negative_flow.append(0.0)
        elif typical_price < self.typical_prices[-2]:
            self.positive_flow.append(0.0)
            self.negative_flow.append(raw_money_flow)
        else:
            self.positive_flow.append(0.0)
            self.negative_flow.append(0.0)

        if len(self.positive_flow) < self.period:
            self.values.append(50.0)  # Default value during warm-up
            return

        sum_pos_flow = sum(self.positive_flow)
        sum_neg_flow = sum(self.negative_flow)

        if sum_neg_flow == 0:
            mfi = 100.0
        else:
            money_ratio = sum_pos_flow / sum_neg_flow
            mfi = 100.0 - (100.0 / (1.0 + money_ratio))

        self.values.append(mfi)

    def reset(self):
        super().reset()
        self.values.clear()
        self.typical_prices.clear()
        self.positive_flow.clear()
        self.negative_flow.clear()