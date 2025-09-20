"""
Detectors for four-candle patterns.
"""
from .base_detector import BaseDetector

class Hikkake(BaseDetector):
    def __init__(self):
        super().__init__(bar_count=4)

    def detect(self, candles):
        # Logic for Hikkake detection
        pass

class MatHold(BaseDetector):
    def __init__(self):
        super().__init__(bar_count=5) # Mat Hold is a five-candle pattern, but often grouped with 4-candle patterns in some contexts

    def detect(self, candles):
        # Logic for Mat Hold detection
        pass