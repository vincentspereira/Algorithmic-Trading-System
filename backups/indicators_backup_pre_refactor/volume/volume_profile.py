"""
Volume Profile Indicator.
"""
from collections import defaultdict

import numpy as np
from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import (
    MultiTimeframeIndicator,
    MultiTimeframeIndicatorConfig,
)


class VolumeProfileConfig(MultiTimeframeIndicatorConfig):
    """
    Configuration for the Volume Profile indicator.

    Attributes:
        num_levels (int): The number of price levels to use in the profile.
    """

    num_levels: int = 20


class VolumeProfile(MultiTimeframeIndicator):
    """
    Volume Profile indicator.
    """

    def __init__(self, config: VolumeProfileConfig):
        super().__init__(config)
        self.num_levels = config.num_levels
        self.volume_data = defaultdict(float)

    def on_aggregated_bar(self, bar: Bar):
        price_range = np.linspace(bar.low, bar.high, self.num_levels)
        volume_per_level = bar.volume / self.num_levels

        for price in price_range:
            self.volume_data[price] += volume_per_level

    def reset(self):
        super().reset()
        self.volume_data.clear()