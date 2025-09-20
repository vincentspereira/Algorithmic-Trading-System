"""
institutional_candlestick_patterns.py
"""

import logging
from collections import deque
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List
import numpy as np
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.events import BarEvent
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.indicators import Indicator
from nautilus_trader.model.objects import Price
from nautilus_trader.typing import BarGenerator
from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.core.message import Event
from nautilus_trader.indicators.base.indicator import Indicator
from nautilus_trader.indicators.data.bar import BarData
from nautilus_trader.indicators.data.candle import CandleData
from nautilus_trader.indicators.data.pattern import PatternResult
from nautilus_trader.indicators.enum.pattern import (
    PatternType,
    PatternSignal,
    PatternReliability,
)
from .single_candle_patterns import detect_single_candle_patterns
from .two_candle_patterns import detect_two_candle_patterns
from .three_candle_patterns import detect_three_candle_patterns
from .institutional_patterns import detect_institutional_patterns
from .utils import add_volume_confirmation, add_statistical_validation


class InstitutionalCandlestickPatterns(Indicator):
    """
    An advanced candlestick pattern detection indicator that incorporates
    institutional-grade features like volume confirmation, multi-timeframe
    analysis, and statistical validation.
    """

    def __init__(
        self,
        instrument: str,
        bar_type: str,
        volume_confirmation: bool = True,
        multi_timeframe_analysis: bool = True,
        statistical_validation: bool = True,
        min_confidence: float = 0.6,
        lookback_periods: int = 100,
    ):
        """
        Initializes the InstitutionalCandlestickPatterns indicator.

        Args:
            instrument (str): The instrument to analyze.
            bar_type (str): The bar type to use for analysis.
            volume_confirmation (bool): Whether to use volume confirmation.
            multi_timeframe_analysis (bool): Whether to perform multi-timeframe analysis.
            statistical_validation (bool): Whether to use statistical validation.
            min_confidence (float): The minimum confidence level for a pattern to be considered.
            lookback_periods (int): The number of lookback periods for analysis.
        """
        super().__init__(
            instrument=instrument,
            bar_type=bar_type,
            lookback_periods=lookback_periods,
        )
        self.volume_confirmation = volume_confirmation
        self.multi_timeframe_analysis = multi_timeframe_analysis
        self.statistical_validation = statistical_validation
        self.min_confidence = min_confidence
        self.lookback_periods = lookback_periods

        # Historical data storage
        self.candle_history: deque = deque(maxlen=lookback_periods)
        self.volume_history: deque = deque(maxlen=lookback_periods)
        self.pattern_history: deque = deque(maxlen=200)

        # Pattern performance tracking
        self.pattern_performance: Dict[PatternType, Dict] = {}
        self.success_rates: Dict[PatternType, float] = {}

        # Volume analysis
        self.avg_volume_periods = 20
        self.institutional_volume_threshold = 2.0  # 2x average volume

        # Trend context
        self.trend_periods = 20
        self.current_trend = "unknown"

        # Initialize pattern performance tracking
        self._initialize_pattern_tracking()

        self.logger = logging.getLogger(__name__)

    def _initialize_pattern_tracking(self) -> None:
        """Initialize pattern performance tracking"""
        for pattern in PatternType:
            self.pattern_performance[pattern] = {
                "total_occurrences": 0,
                "successful_predictions": 0,
                "avg_confidence": 0.0,
                "avg_strength": 0.0,
                "volume_confirmed_rate": 0.0,
                "last_seen": None,
            }
            self.success_rates[pattern] = 0.5  # Default 50%

    def add_candle(
        self,
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        volume: float,
        timestamp: datetime = None,
    ) -> None:
        """Add new candle data"""

        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        candle = CandleData(
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
            timestamp=timestamp,
        )

        self.candle_history.append(candle)
        self.volume_history.append(volume)

        # Update trend context
        self._update_trend_context()

    def detect_patterns(self) -> List[PatternResult]:
        """Detect all candlestick patterns in current data"""

        if len(self.candle_history) < 3:
            return []

        patterns = []

        # Single candle patterns
        patterns.extend(detect_single_candle_patterns(self))

        # Two candle patterns
        if len(self.candle_history) >= 2:
            patterns.extend(detect_two_candle_patterns(self))

        # Three candle patterns
        if len(self.candle_history) >= 3:
            patterns.extend(detect_three_candle_patterns(self))

        # Advanced institutional patterns
        if len(self.candle_history) >= 5:
            patterns.extend(detect_institutional_patterns(self))

        # Filter by minimum confidence
        patterns = [p for p in patterns if p.confidence >= self.min_confidence]

        # Enhance with volume confirmation
        if self.volume_confirmation:
            patterns = [add_volume_confirmation(self, p) for p in patterns]

        # Add statistical validation
        if self.statistical_validation:
            patterns = [add_statistical_validation(self, p) for p in patterns]

        # Store pattern history
        for pattern in patterns:
            self.pattern_history.append(pattern)

        return patterns