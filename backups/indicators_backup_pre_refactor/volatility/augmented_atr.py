"""
Augmented Average True Range (ATR) Indicator.

This module provides an augmented version of the Average True Range (ATR) 
indicator.
"""

from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import (
    AugmentedIndicator,
    AugmentedIndicatorConfig,
)
from nautilus_trader_engine.indicators.volatility.atr import ATR, ATRConfig


class AugmentedATR(AugmentedIndicator):
    """
    An augmented Average True Range (ATR) indicator.
    """

    def __init__(self, config: AugmentedIndicatorConfig):
        """
        Initializes the AugmentedATR indicator.

        Args:
            config (AugmentedIndicatorConfig): The configuration for the indicator.
        """
        super().__init__(config)
        atr_config = ATRConfig(
            period=config.base_indicator_config.get("period", 14),
            smoothing_type=config.base_indicator_config.get("smoothing_type", "smma"),
        )
        self.atr = ATR(atr_config)

    @property
    def is_ready(self) -> bool:
        """Returns True if the indicator is ready."""
        return self.atr.is_ready

    def handle_bar(self, bar: Bar):
        """
        Handles a new bar.

        Args:
            bar (Bar): The new bar.
        """
        self.atr.handle_bar(bar)

    def reset(self):
        """
        Resets the indicator to its initial state.
        """
        super().reset()
        self.atr.reset()
