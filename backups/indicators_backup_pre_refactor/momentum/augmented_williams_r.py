"""
Augmented Williams %R Indicator.

This module provides an augmented version of the Williams %R indicator,
incorporating a 5-pillar architecture for institutional-grade analysis.
"""

from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import PriceType

from nautilus_trader_engine.indicators.base import (
    AugmentedIndicator,
    AugmentedIndicatorConfig,
)
from nautilus_trader_engine.indicators.momentum.williams_r import (
    WilliamsR,
    WilliamsRConfig,
)


class AugmentedWilliamsR(AugmentedIndicator):
    """
    An augmented Williams %R indicator that integrates the 5-pillar architecture
    for a more comprehensive market analysis.
    """

    def __init__(self, config: AugmentedIndicatorConfig):
        """
        Initializes the AugmentedWilliamsR indicator.

        Args:
            config (AugmentedIndicatorConfig): The configuration for the indicator.
        """
        super().__init__(config)
        williams_r_config = WilliamsRConfig(
            period=config.base_indicator_config.get("period", 14),
            price_type=config.base_indicator_config.get("price_type", PriceType.CLOSE),
        )
        self.williams_r = WilliamsR(williams_r_config)

    @property
    def is_ready(self) -> bool:
        """Returns True if the indicator is ready."""
        return self.williams_r.is_ready

    def handle_bar(self, bar: Bar):
        """
        Handles a new bar.

        Args:
            bar (Bar): The new bar.
        """
        self.williams_r.handle_bar(bar)
        if self.is_ready:
            self._update_pillars(bar)

    def reset(self):
        """Resets the indicator."""
        self.williams_r.reset()
        super().reset()