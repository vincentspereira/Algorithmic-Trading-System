"""
Detectors for two-candle patterns.
"""
from .base_detector import BaseDetector

class Engulfing(BaseDetector):
    def __init__(self):
        super().__init__(bar_count=2)

    def detect(self, candles):
        # Logic for Engulfing detection
        pass

class TweezerTop(BaseDetector):
    def __init__(self):
        super().__init__(bar_count=2)

    def detect(self, candles):
        # Logic for Tweezer Top detection
        pass

class TweezerBottom(BaseDetector):
    def __init__(self):
        super().__init__(bar_count=2)

    def detect(self, candles):
        # Logic for Tweezer Bottom detection
        pass