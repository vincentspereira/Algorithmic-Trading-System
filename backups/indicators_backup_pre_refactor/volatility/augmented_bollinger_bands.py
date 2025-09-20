"""Augmented Bollinger Bands Indicator.

This module provides an augmented version of the Bollinger Bands indicator.
"""

from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import (
    AugmentedIndicator,
    AugmentedIndicatorConfig,
)
from nautilus_trader_engine.indicators.volatility.bollinger_bands import (
    BollingerBands,
    BBConfig,
)


class AugmentedBollingerBands(AugmentedIndicator):
    """
    An augmented Bollinger Bands indicator.
    """

    def __init__(self, config: AugmentedIndicatorConfig):
        """
        Initializes the AugmentedBollingerBands indicator.

        Args:
            config (AugmentedIndicatorConfig): The configuration for the indicator.
        """
        super().__init__(config)
        bb_config = BBConfig(
            period=config.base_indicator_config.get("period", 20),
            std_dev=config.base_indicator_config.get("std_dev", 2.0),
        )
        self.bollinger_bands = BollingerBands(bb_config)

    @property
    def is_ready(self) -> bool:
        """Returns True if the indicator is ready."""
        return self.bollinger_bands.is_ready

    def handle_bar(self, bar: Bar):
        """
        Handles a new bar.

        Args:
            bar (Bar): The new bar.
        """
        self.bollinger_bands.handle_bar(bar)

    def reset(self):
        """
        Resets the indicator to its initial state.
        """
        super().reset()
        self.bollinger_bands.reset()