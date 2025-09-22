"""
Detectors for five-candle patterns.
"""
from .base_detector import BaseDetector

class MatHold(BaseDetector):
    def __init__(self):
        super().__init__(bar_count=5)

    def detect(self, candles):
        # Logic for Mat Hold detection
        pass