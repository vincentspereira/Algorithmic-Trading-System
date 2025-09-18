"""MultiValueIndicator base class for indicators that return multiple values.

This class provides a foundation for technical indicators that produce multiple output values,
such as MACD (value, signal, histogram) or Bollinger Bands (mid, upper, lower).
It incorporates performance monitoring, robust calculation, and optional volume confirmation.

Author: Vincent S. Pereira
Version: 1.0.0
"""

from abc import ABC, abstractmethod
import numpy as np

from .core_indicator_base import performance_monitor, robust_calculation

try:
    from nautilus_trader.indicators.base.indicator import Indicator
    NAUTILUS_AVAILABLE = True
except ImportError:
    NAUTILUS_AVAILABLE = False
    class Indicator(ABC):
        pass  # Mock base class

# Safe import for VolumeConfirmationMixin with availability flag
try:
    from .volume_confirmation import VolumeConfirmationMixin
    VOLUME_CONFIRMATION_AVAILABLE = True
except ImportError:
    VOLUME_CONFIRMATION_AVAILABLE = False
    class VolumeConfirmationMixin:
        pass  # Mock if not available

class MultiValueIndicator(Indicator, VolumeConfirmationMixin, ABC):
    """
    Abstract base class for multi-value indicators.
    
    Parameters
    ----------
    params : dict
        Dictionary of initialization parameters
    volume_confirmation : bool, optional
        Whether to enable volume confirmation (default: True)
    """

    def __init__(self, params: dict = None, volume_confirmation: bool = True):
        super().__init__()
        self.params = params or {}
        self.values = {}  # Dictionary to hold multiple output values
        self.initialized = False
        self.has_inputs = False
        self._enable_volume_confirmation = volume_confirmation
        if self._enable_volume_confirmation and VOLUME_CONFIRMATION_AVAILABLE:
            self.initialize_volume_confirmation()

    @abstractmethod
    def name(self) -> str:
        """Return the name of the indicator."""
        pass

    @performance_monitor
    @robust_calculation(default_value={})
    def update_raw(self, *args) -> None:
        """
        Update the indicator with raw input values.
        
        This method should be implemented by subclasses to perform the actual calculation
        and update self.values dictionary.
        """
        self.has_inputs = True
        # Subclasses should implement the calculation here
        # Example: self.values = {'value1': ..., 'value2': ...}
        
        if self._enable_volume_confirmation and VOLUME_CONFIRMATION_AVAILABLE:
            self.apply_volume_confirmation(self.values)

        if not self.initialized:
            self.initialized = self._check_initialization()

    def value(self) -> dict:
        """Return the current values dictionary."""
        return self.values.copy()

    def reset(self) -> None:
        """Reset the indicator to initial state."""
        self.values = {}
        self.initialized = False
        self.has_inputs = False
        if self._enable_volume_confirmation and VOLUME_CONFIRMATION_AVAILABLE:
            self.reset_volume_confirmation()

    def _check_initialization(self) -> bool:
        """Check if the indicator is fully initialized.
        
        Subclasses can override this for custom initialization logic.
        """
        return all(np.isfinite(val) for val in self.values.values() if isinstance(val, (int, float)))

    def __repr__(self) -> str:
        return f"{self.name()}({self.params}) - Values: {self.values}"