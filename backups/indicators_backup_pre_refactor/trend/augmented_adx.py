"""Augmented Average Directional Index (ADX) Indicator.

This module provides an augmented version of the ADX indicator, incorporating a
5-pillar architecture for institutional-grade analysis.
"""

from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import (
    AugmentedIndicator,
    AugmentedIndicatorConfig,
)
from nautilus_trader_engine.indicators.trend.adx import ADX, ADXConfig


class AugmentedADX(AugmentedIndicator):
    """
    Augmented ADX indicator with a 5-pillar architecture.
    """

    def __init__(self, config: AugmentedIndicatorConfig):
        """
        Initializes the AugmentedADX indicator.

        Args:
            config (AugmentedIndicatorConfig): The configuration for the indicator.
        """
        super().__init__(config)
        adx_config = ADXConfig(
            period=config.base_indicator_config.get("period", 14),
        )
        self.adx = ADX(adx_config)

    @property
    def is_ready(self) -> bool:
        """Returns True if the indicator is ready."""
        return self.adx.is_ready

    def handle_bar(self, bar: Bar):
        """
        Handles a new bar.

        Args:
            bar (Bar): The new bar.
        """
        self.adx.handle_bar(bar)

    def reset(self):
        """
        Resets the indicator to its initial state.
        """
        super().reset()
        self.adx.reset()