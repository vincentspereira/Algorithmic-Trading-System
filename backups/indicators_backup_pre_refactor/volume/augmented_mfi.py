"""
Augmented Money Flow Index (MFI) Indicator.

This module provides an augmented version of the Money Flow Index (MFI)
indicator, incorporating a 5-pillar architecture for institutional-grade analysis.
"""

from nautilus_trader.model.data import Bar

from nautilus_trader_engine.indicators.base import (
    AugmentedIndicator,
    AugmentedIndicatorConfig,
)
from nautilus_trader_engine.indicators.volume.mfi import MFI, MFIConfig


class AugmentedMFI(AugmentedIndicator):
    """
    An augmented Money Flow Index (MFI) indicator that integrates the 5-pillar
    architecture for a more comprehensive market analysis.
    """

    def __init__(self, config: AugmentedIndicatorConfig):
        """
        Initializes the AugmentedMFI indicator.

        Args:
            config (AugmentedIndicatorConfig): The configuration for the indicator.
        """
        super().__init__(config)
        mfi_config = MFIConfig(
            period=config.base_indicator_config.get("period", 14),
            buffer_size=config.base_indicator_config.get("buffer_size", 100),
        )
        self.mfi = MFI(config=mfi_config)

    @property
    def is_ready(self) -> bool:
        """Returns True if the indicator is ready."""
        return self.mfi.is_ready

    def handle_bar(self, bar: Bar):
        """
        Handles a new bar.

        Args:
            bar (Bar): The new bar.
        """
        self.mfi.handle_bar(bar)

    def reset(self):
        """
        Resets the indicator to its initial state.
        """
        super().reset()
        self.mfi.reset()