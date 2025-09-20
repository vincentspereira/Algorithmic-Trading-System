"""
Base class for pattern detectors.
"""
from abc import ABC, abstractmethod

class BaseDetector(ABC):
    """
    Abstract base class for all pattern detectors.
    """
    def __init__(self, bar_count: int):
        self.bar_count = bar_count

    @abstractmethod
    def detect(self, candles):
        """
        Detects the pattern in the given candles.

        :param candles: A list of candles to analyze.
        :return: A tuple containing a boolean indicating if the pattern was detected,
                 and a dictionary with pattern-specific information.
        """
        raise NotImplementedError

    def _calculate_body(self, candle):
        """Calculates the size of the candle body."""
        return abs(candle.close - candle.open)

    def _is_bullish(self, candle):
        """Determines if a candle is bullish."""
        return candle.close > candle.open

    def _is_bearish(self, candle):
        """Determines if a candle is bearish."""
        return candle.close < candle.open