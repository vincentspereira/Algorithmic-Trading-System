"""
Augmented Volume-Weighted Average Price (VWAP) Indicator.

This module provides an augmented version of the Volume-Weighted Average Price
(VWAP) indicator, incorporating a 5-pillar architecture for institutional-grade
analysis.
"""

from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import (
    AugmentedIndicator,
    AugmentedIndicatorConfig,
)
from nautilus_trader_engine.indicators.volume.vwap import VWAP, VWAPConfig


class AugmentedVWAP(AugmentedIndicator):
    """
    An augmented Volume-Weighted Average Price (VWAP) indicator that integrates
    the 5-pillar architecture for a more comprehensive market analysis.
    """

    def __init__(self, config: AugmentedIndicatorConfig):
        super().__init__(config)
        self.config = config

        base_indicator_config = self.config.base_indicator_config.dict()
        vwap_config = VWAPConfig(
            buffer_size=base_indicator_config.get("buffer_size", 100),
            reset_period=base_indicator_config.get("reset_period", "daily"),
        )
        self.vwap = VWAP(config=vwap_config)

    @property
    def is_ready(self) -> bool:
        """Returns True if the indicator is ready."""
        return self.vwap.is_ready

    def handle_bar(self, bar: Bar):
        """
        Handles a new bar.

        Args:
            bar (Bar): The new bar.
        """
        self.vwap.handle_bar(bar)

    def reset(self):
        """
        Resets the indicator to its initial state.
        """
        super().reset()
        self.vwap.reset()