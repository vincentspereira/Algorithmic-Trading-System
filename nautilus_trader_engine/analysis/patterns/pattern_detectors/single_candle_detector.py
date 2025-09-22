"""
Detectors for single-candle patterns.
"""
from .base_detector import BaseDetector

class Hammer(BaseDetector):
    def __init__(self):
        super().__init__(bar_count=1)

    def detect(self, candles):
        # Logic for Hammer detection
        pass

class InvertedHammer(BaseDetector):
    def __init__(self):
        super().__init__(bar_count=1)

    def detect(self, candles):
        # Logic for Inverted Hammer detection
        pass

class ShootingStar(BaseDetector):
    def __init__(self):
        super().__init__(bar_count=1)

    def detect(self, candles):
        # Logic for Shooting Star detection
        pass

class Doji(BaseDetector):
    def __init__(self):
        super().__init__(bar_count=1)

    def detect(self, candles):
        # Logic for Doji detection
        pass

class Marubozu(BaseDetector):
    def __init__(self):
        super().__init__(bar_count=1)

    def detect(self, candles):
        # Logic for Marubozu detection
        pass