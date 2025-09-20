"""Augmented Donchian Channels Indicator.

This module provides an augmented version of the Donchian Channels indicator.
"""

from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import (
    AugmentedIndicator,
    AugmentedIndicatorConfig,
)
from nautilus_trader_engine.indicators.volatility.donchian_channels import (
    DonchianChannels,
    DCConfig,
)


class AugmentedDonchianChannels(AugmentedIndicator):
    """
    An augmented Donchian Channels indicator.
    """

    def __init__(self, config: AugmentedIndicatorConfig):
        """
        Initializes the AugmentedDonchianChannels indicator.

        Args:
            config (AugmentedIndicatorConfig): The configuration for the indicator.
        """
        super().__init__(config)
        dc_config = DCConfig(
            period=config.base_indicator_config.get("period", 20),
        )
        self.donchian_channels = DonchianChannels(dc_config)

    @property
    def is_ready(self) -> bool:
        """Returns True if the indicator is ready."""
        return self.donchian_channels.is_ready

    def handle_bar(self, bar: Bar):
        """
        Handles a new bar.

        Args:
            bar (Bar): The new bar.
        """
        self.donchian_channels.handle_bar(bar)

    def reset(self):
        """
        Resets the indicator to its initial state.
        """
        super().reset()
        self.donchian_channels.reset()