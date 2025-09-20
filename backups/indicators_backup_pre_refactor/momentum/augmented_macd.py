"""Augmented Moving Average Convergence Divergence (MACD) Indicator.

This module provides an augmented version of the Moving Average Convergence
Divergence (MACD) indicator, incorporating a 5-pillar architecture for
institutional-grade analysis.
"""

from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import (
    AugmentedIndicator,
    AugmentedIndicatorConfig,
)
from nautilus_trader_engine.indicators.momentum.macd import MACD, MACDConfig


class AugmentedMACD(AugmentedIndicator):
    """
    An augmented Moving Average Convergence Divergence (MACD) indicator that
    integrates the 5-pillar architecture for a more comprehensive market analysis.
    """

    def __init__(self, config: AugmentedIndicatorConfig):
        super().__init__(config)
        macd_config = MACDConfig(
            fast_period=config.base_indicator_config.get("fast_period", 12),
            slow_period=config.base_indicator_config.get("slow_period", 26),
            signal_period=config.base_indicator_config.get("signal_period", 9),
        )
        self.macd = MACD(macd_config)

    @property
    def is_ready(self) -> bool:
        """Returns True if the indicator is ready to provide values."""
        return self.macd.is_ready

    def handle_bar(self, bar: Bar):
        """
        Handles a new bar of data, updating the MACD and the 5-pillar analysis.

        Args:
            bar (Bar): The new bar of data.
        """
        self.macd.handle_bar(bar)
        if self.is_ready:
            self._update_pillars(bar)

    def reset(self):
        """Resets the indicator to its initial state."""
        super().reset()
        self.macd.reset()