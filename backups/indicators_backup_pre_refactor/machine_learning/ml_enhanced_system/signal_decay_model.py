import math
from datetime import datetime, timedelta


class SignalDecayModel:
    """Applies a time-based decay to trading signals"""

    def __init__(self, decay_rate: float = 0.05, time_unit: str = "hours"):
        self.decay_rate = decay_rate
        self.time_unit_seconds = self._get_time_unit_seconds(time_unit)

    def _get_time_unit_seconds(self, time_unit: str) -> int:
        if time_unit == "minutes":
            return 60
        if time_unit == "hours":
            return 3600
        if time_unit == "days":
            return 86400
        return 3600  # Default to hours

    def calculate_decayed_signal(
        self, original_signal: float, signal_timestamp: datetime, current_timestamp: datetime
    ) -> float:
        """Calculate the decayed value of a signal"""
        time_diff = (current_timestamp - signal_timestamp).total_seconds()
        decay_factor = self._calculate_decay_factor(time_diff)
        return original_signal * decay_factor

    def _calculate_decay_factor(self, time_diff_seconds: float) -> float:
        """Calculate the decay factor based on elapsed time"""
        time_units_elapsed = time_diff_seconds / self.time_unit_seconds
        return math.exp(-self.decay_rate * time_units_elapsed)