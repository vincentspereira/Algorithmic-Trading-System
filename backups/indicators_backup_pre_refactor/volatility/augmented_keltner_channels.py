"""Augmented Keltner Channels Indicator.

This module provides an augmented version of the Keltner Channels indicator.
"""

from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import (
    AugmentedIndicator, 
    AugmentedIndicatorConfig,
)
from nautilus_trader_engine.indicators.volatility.keltner_channels import (
    KeltnerChannels,
    KCConfig,
)


class AugmentedKeltnerChannels(AugmentedIndicator):
    """
    An augmented Keltner Channels indicator.
    """

    def __init__(self, config: AugmentedIndicatorConfig):
        """
        Initializes the AugmentedKeltnerChannels indicator.

        Args:
            config (AugmentedIndicatorConfig): The configuration for the indicator.
        """
        super().__init__(config)
        kc_config = KCConfig(
            ema_period=config.base_indicator_config.get("ema_period", 20),
            atr_period=config.base_indicator_config.get("atr_period", 10),
            atr_multiplier=config.base_indicator_config.get("atr_multiplier", 2.0),
        )
        self.keltner_channels = KeltnerChannels(kc_config)

    @property
    def is_ready(self) -> bool:
        """Returns True if the indicator is ready."""
        return self.keltner_channels.is_ready

    def handle_bar(self, bar: Bar):
        """
        Handles a new bar.

        Args:
            bar (Bar): The new bar.
        """
        self.keltner_channels.handle_bar(bar)

    def reset(self):
        """
        Resets the indicator to its initial state.
        """
        super().reset()
        self.keltner_channels.reset()