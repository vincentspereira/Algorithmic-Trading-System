"""
Augmented Accumulation/Distribution Indicator.

This module provides an augmented version of the Accumulation/Distribution (A/D)
indicator, incorporating a 5-pillar architecture for institutional-grade analysis.
"""

from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import (
    AugmentedIndicator,
    AugmentedIndicatorConfig,
)
from nautilus_trader_engine.indicators.volume.ad import (
    AD,
    ADConfig,
)


class AugmentedAD(AugmentedIndicator):
    """
    An augmented Accumulation/Distribution (A/D) indicator that integrates the
    5-pillar architecture for a more comprehensive market analysis.
    """

    def __init__(self, config: AugmentedIndicatorConfig):
        """
        Initializes the AugmentedAD indicator.

        Args:
            config (AugmentedIndicatorConfig): The configuration for the indicator.
        """
        super().__init__(config)
        ad_config = ADConfig(
            buffer_size=config.base_indicator_config.get("buffer_size", 100),
        )
        self.ad_line = AD(config=ad_config)

    @property
    def is_ready(self) -> bool:
        """Returns True if the indicator is ready."""
        return self.ad_line.is_ready

    def handle_bar(self, bar: Bar):
        """
        Handles a new bar.

        Args:
            bar (Bar): The new bar.
        """
        self.ad_line.handle_bar(bar)

    def reset(self):
        """
        Resets the indicator to its initial state.
        """
        super().reset()
        self.ad_line.reset()