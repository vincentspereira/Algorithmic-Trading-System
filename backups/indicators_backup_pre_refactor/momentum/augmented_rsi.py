"""Augmented Relative Strength Index (RSI) Indicator.

This module provides an augmented version of the Relative Strength Index (RSI)
indicator, incorporating a 5-pillar architecture for institutional-grade
analysis.
"""

from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import (
    AugmentedIndicator,
    AugmentedIndicatorConfig,
)
from nautilus_trader_engine.indicators.momentum.rsi import RSI, RSIConfig


class AugmentedRSI(AugmentedIndicator):
    """
    An augmented Relative Strength Index (RSI) indicator that integrates the
    5-pillar architecture for a more comprehensive market analysis.
    """

    def __init__(self, config: AugmentedIndicatorConfig):
        super().__init__(config)
        rsi_config = RSIConfig(
            period=config.base_indicator_config.get("period", 14),
            price_type=config.base_indicator_config.get("price_type", "CLOSE"),
        )
        self.rsi = RSI(rsi_config)

    @property
    def is_ready(self) -> bool:
        """Returns True if the indicator is ready to provide values."""
        return self.rsi.is_ready

    def handle_bar(self, bar: Bar):
        """
        Handles a new bar of data, updating the RSI and the 5-pillar analysis.

        Args:
            bar (Bar): The new bar of data.
        """
        self.rsi.handle_bar(bar)
        if self.is_ready:
            self._update_pillars(bar)

    def reset(self):
        """Resets the indicator to its initial state."""
        super().reset()
        self.rsi.reset()