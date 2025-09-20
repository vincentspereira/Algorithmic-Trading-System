"""
Augmented Stochastic Oscillator Indicator.

This module provides an augmented version of the Stochastic Oscillator indicator,
incorporating a 5-pillar architecture for institutional-grade analysis.
"""

from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import PriceType

from nautilus_trader_engine.indicators.base import (
    AugmentedIndicator,
    AugmentedIndicatorConfig,
)
from nautilus_trader_engine.indicators.momentum.stochastic import (
    Stochastic,
    StochasticConfig,
)


class AugmentedStochastic(AugmentedIndicator):
    """
    An augmented Stochastic Oscillator indicator that integrates the 5-pillar
    architecture for a more comprehensive market analysis.
    """

    def __init__(self, config: AugmentedIndicatorConfig):
        """
        Initializes the AugmentedStochastic indicator.

        Args:
            config (AugmentedIndicatorConfig): The configuration for the indicator.
        """
        super().__init__(config)
        stochastic_config = StochasticConfig(
            period=config.base_indicator_config.get("period", 14),
            smoothing_period=config.base_indicator_config.get("smoothing_period", 3),
            price_type=config.base_indicator_config.get("price_type", PriceType.CLOSE),
        )
        self.stochastic = Stochastic(stochastic_config)

    @property
    def is_ready(self) -> bool:
        """Returns True if the indicator is ready."""
        return self.stochastic.is_ready

    def handle_bar(self, bar: Bar):
        """
        Handles a new bar.

        Args:
            bar (Bar): The new bar.
        """
        self.stochastic.handle_bar(bar)
        if self.is_ready:
            self._update_pillars(bar)

    def reset(self):
        """Resets the indicator."""
        self.stochastic.reset()
        super().reset()