"""Augmented Choppiness Index Indicator.

This module provides an augmented version of the Choppiness Index.
"""

from nautilus_trader.model.data import Bar

from nautilus_trader_engine.analysis.indicators.base import (
    AugmentedIndicator,
    AugmentedIndicatorConfig,
)
from nautilus_trader_engine.analysis.indicators.volatility.choppiness_index import (
    ChoppinessIndex,
    ChoppinessIndexConfig,
)


class AugmentedChoppinessIndex(AugmentedIndicator):
    """
    Augmented Choppiness Index.
    """

    def __init__(self, config: AugmentedIndicatorConfig):
        super().__init__(config)
        choppiness_config = ChoppinessIndexConfig(
            period=config.base_indicator_config.get("period", 14),
        )
        self.choppiness_index = ChoppinessIndex(config=choppiness_config)

    @property
    def is_ready(self) -> bool:
        return self.choppiness_index.is_ready

    def handle_bar(self, bar: Bar):
        self.choppiness_index.handle_bar(bar)

    def reset(self):
        """Resets the indicator."""
        super().reset()
        self.choppiness_index.reset()