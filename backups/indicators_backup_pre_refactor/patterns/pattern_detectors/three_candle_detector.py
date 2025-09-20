"""
Detectors for three-candle patterns.
"""
from .base_detector import BaseDetector

class MorningStar(BaseDetector):
    def __init__(self):
        super().__init__(bar_count=3)

    def detect(self, candles):
        # Logic for Morning Star detection
        pass

class EveningStar(BaseDetector):
    def __init__(self):
        super().__init__(bar_count=3)

    def detect(self, candles):
        # Logic for Evening Star detection
        pass

class ThreeWhiteSoldiers(BaseDetector):
    def __init__(self):
        super().__init__(bar_count=3)

    def detect(self, candles):
        # Logic for Three White Soldiers detection
        pass

class ThreeBlackCrows(BaseDetector):
    def __init__(self):
        super().__init__(bar_count=3)

    def detect(self, candles):
        # Logic for Three Black Crows detection
        pass

class ThreeInsideUpDown(BaseDetector):
    def __init__(self):
        super().__init__(bar_count=3)

    def detect(self, candles):
        # Logic for Three Inside Up/Down detection
        pass

class AbandonedBaby(BaseDetector):
    def __init__(self):
        super().__init__(bar_count=3)

    def detect(self, candles):
        # Logic for Abandoned Baby detection
        pass