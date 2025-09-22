"""
Money Flow Index (MFI) Indicator.
"""

from collections import deque
from dataclasses import dataclass

from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import (
    Indicator,
    IndicatorConfig,
)


@dataclass
class MFIConfig(IndicatorConfig):
    """Configuration for the MFI indicator."""
    period: int = 14


class MFI(Indicator):
    """
    Money Flow Index (MFI) indicator.
    """

    def __init__(self, config: MFIConfig):
        super().__init__(config)
        self.config = config
        self._mfi_values = deque(maxlen=self.config.buffer_size)
        self._typical_prices = deque(maxlen=self.config.period + 1)
        self._positive_flows = deque(maxlen=self.config.period)
        self._negative_flows = deque(maxlen=self.config.period)

    @property
    def mfi(self) -> float:
        """Returns the most recent MFI value."""
        return self._mfi_values[-1] if self._mfi_values else 0.0

    @property
    def is_ready(self) -> bool:
        """Returns True if the indicator is ready."""
        return len(self._mfi_values) > 0

    def handle_bar(self, bar: Bar):
        """
        Handles a new bar.

        Args:
            bar (Bar): The new bar.
        """
        high = float(bar.high)
        low = float(bar.low)
        close = float(bar.close)
        volume = float(bar.volume)

        typical_price = (high + low + close) / 3.0
        self._typical_prices.append(typical_price)

        if len(self._typical_prices) < 2:
            return

        # Calculate money flow
        raw_money_flow = typical_price * volume
        if typical_price > self._typical_prices[-2]:
            self._positive_flows.append(raw_money_flow)
            self._negative_flows.append(0)
        elif typical_price < self._typical_prices[-2]:
            self._negative_flows.append(raw_money_flow)
            self._positive_flows.append(0)
        else:
            self._positive_flows.append(0)
            self._negative_flows.append(0)

        if len(self._positive_flows) < self.config.period:
            return

        # Calculate Money Flow Ratio and MFI
        sum_positive_flow = sum(self._positive_flows)
        sum_negative_flow = sum(self._negative_flows)

        if sum_negative_flow == 0:
            mfi = 100.0
        else:
            money_ratio = sum_positive_flow / sum_negative_flow
            mfi = 100.0 - (100.0 / (1.0 + money_ratio))

        self._mfi_values.append(mfi)

    def reset(self):
        """
        Resets the indicator to its initial state.
        """
        super().reset()
        self._mfi_values.clear()
        self._typical_prices.clear()
        self._positive_flows.clear()
        self._negative_flows.clear()