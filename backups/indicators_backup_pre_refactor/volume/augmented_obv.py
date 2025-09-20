"""Augmented On-Balance Volume (OBV) Indicator.

This module provides an augmented version of the On-Balance Volume (OBV)
indicator, incorporating a 5-pillar architecture for institutional-grade analysis.
"""

from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import (
    AugmentedIndicator,
    AugmentedIndicatorConfig,
)
from nautilus_trader_engine.indicators.volume.obv import OBV, OBVConfig


class AugmentedOBV(AugmentedIndicator):
    """
    An augmented On-Balance Volume (OBV) indicator that integrates the 5-pillar
    architecture for a more comprehensive market analysis.
    """

    def __init__(self, config: AugmentedIndicatorConfig):
        """
        Initializes the AugmentedOBV indicator.

        Args:
            config (AugmentedIndicatorConfig): The configuration for the indicator.
        """
        super().__init__(config)
        obv_config = OBVConfig(
            buffer_size=config.base_indicator_config.get("buffer_size", 100),
        )
        self.obv = OBV(config=obv_config)

    @property
    def is_ready(self) -> bool:
        """Returns True if the indicator is ready."""
        return self.obv.is_ready

    def handle_bar(self, bar: Bar):
        """
        Handles a new bar.

        Args:
            bar (Bar): The new bar.
        """
        self.obv.handle_bar(bar)

    def reset(self):
        """
        Resets the indicator to its initial state.
        """
        super().reset()
        self.obv.reset()