"""
Candlestick pattern indicator.
"""
from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import BarSpecification
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.indicators import Indicator
from nautilus_trader.model.objects import Price

from nautilus_trader_engine.indicators.patterns.pattern_detectors.consolidated_detector import ConsolidatedPatternDetector

class PatternIndicator(Indicator):
    """
    A candlestick pattern indicator that uses a consolidated pattern detector.
    """
    def __init__(
        self,
        instrument_id: InstrumentId,
        bar_spec: BarSpecification,
        name: str = "PatternIndicator",
    ):
        super().__init__(instrument_id, bar_spec, name)
        self.detector = ConsolidatedPatternDetector()

    def calculate(self, bar: Bar) -> None:
        """
        Calculates the pattern analysis for the given bar.

        :param bar: The bar to analyze.
        """
        # The consolidated detector needs a list of candles.
        # We need to manage the history of bars to pass to the detector.
        # For now, we'll just pass the current bar, but this needs to be improved.
        candles = [bar]
        results = self.detector.detect(candles)
        if results:
            for pattern_name, pattern_info in results.items():
                self.value = f"{pattern_name}: {pattern_info}"