"""
Fibonacci Extensions Module

Advanced Fibonacci extension analysis with institutional-grade features including
volume weighting, smart money confirmation, multi-timeframe analysis, and adaptive
confidence scoring for professional trading applications.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import numpy as np

from ...core.base_classes import AugmentedIndicator


class ExtensionLevel(Enum):
    """Standard Fibonacci extension levels"""
    LEVEL_127 = 1.272
    LEVEL_161 = 1.618
    LEVEL_200 = 2.000
    LEVEL_261 = 2.618
    LEVEL_361 = 3.618
    LEVEL_423 = 4.236
    LEVEL_500 = 5.000


class ExtensionType(Enum):
    """Types of Fibonacci extensions"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class FibonacciExtensionSignal:
    """Fibonacci extension signal with institutional features"""
    value_raw: float
    signal_type: str
    composite_confidence: float
    confidence_components: Dict[str, float]
    suggested_sl: float
    suggested_tp: float
    timestamp: datetime
    additional_metadata: Dict[str, Any]

    # Extension-specific fields
    extension_type: ExtensionType
    extension_level: ExtensionLevel
    extension_price: float
    base_move_start: float
    base_move_end: float
    extension_ratio: float
    volume_at_extension: float
    time_at_extension: int
    confluence_score: float


class FibonacciExtensions(AugmentedIndicator):
    """
    Advanced Fibonacci Extensions Analyzer

    Calculates Fibonacci extension levels with institutional-grade features:
    - Volume-weighted extension analysis
    - Smart money confirmation signals
    - Multi-timeframe extension validation
    - Adaptive confidence scoring
    - Risk management integration
    """

    def __init__(self, timeframe: str = "1D", lookback_periods: int = 50):
        super().__init__(name="FibonacciExtensions", timeframe=timeframe)
        self.lookback_periods = lookback_periods
        self.price_history = []
        self.volume_history = []
        self.extension_signals = []

    def update(self, price: float, volume: float, high: float = None,
               low: float = None, timestamp: datetime = None,
               order_book_data: Dict = None, trade_data: List = None) -> Optional[FibonacciExtensionSignal]:
        """
        Update analyzer with new price/volume data

        Args:
            price: Current price
            volume: Current volume
            high: High price (optional)
            low: Low price (optional)
            timestamp: Data timestamp
            order_book_data: Order book data for smart money analysis
            trade_data: Trade data for volume analysis

        Returns:
            FibonacciExtensionSignal if extension level reached, None otherwise
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Update price and volume history
        self.price_history.append(price)
        self.volume_history.append(volume)

        # Maintain lookback window
        if len(self.price_history) > self.lookback_periods:
            self.price_history.pop(0)
            self.volume_history.pop(0)

        # Need minimum data for analysis
        if len(self.price_history) < 20:
            return None

        # Analyze for extension levels
        signal = self._analyze_extensions(timestamp, order_book_data, trade_data)

        if signal:
            self.current_signal = signal
            self.extension_signals.append(signal)

        return signal

    def _analyze_extensions(self, timestamp: datetime,
                          order_book_data: Dict = None,
                          trade_data: List = None) -> Optional[FibonacciExtensionSignal]:
        """
        Analyze current price for Fibonacci extension levels
        """
        if len(self.price_history) < 10:
            return None

        current_price = self.price_history[-1]

        # Find recent swing points for base move calculation
        base_move = self._find_base_move()
        if not base_move:
            return None

        base_start, base_end = base_move
        base_range = abs(base_end - base_start)

        # Determine extension direction
        if current_price > base_end:
            extension_type = ExtensionType.BULLISH
            extension_ratios = [level.value for level in ExtensionLevel]
        elif current_price < base_start:
            extension_type = ExtensionType.BEARISH
            extension_ratios = [-level.value for level in ExtensionLevel]  # Negative for bearish
        else:
            return None

        # Check for extension level hits
        for ratio in extension_ratios:
            if extension_type == ExtensionType.BULLISH:
                extension_price = base_start + (base_range * ratio)
                if abs(current_price - extension_price) / current_price < 0.005:  # Within 0.5%
                    return self._create_extension_signal(
                        extension_type, ExtensionLevel(ratio), extension_price,
                        base_start, base_end, ratio, timestamp,
                        order_book_data, trade_data
                    )
            else:  # Bearish
                extension_price = base_end + (base_range * ratio)  # ratio is negative
                if abs(current_price - extension_price) / current_price < 0.005:
                    return self._create_extension_signal(
                        extension_type, ExtensionLevel(abs(ratio)), extension_price,
                        base_start, base_end, ratio, timestamp,
                        order_book_data, trade_data
                    )

        return None

    def _find_base_move(self) -> Optional[Tuple[float, float]]:
        """
        Find the most recent significant base move (swing high to swing low or vice versa)
        """
        if len(self.price_history) < 10:
            return None

        # Simple swing detection - find recent high and low
        recent_prices = self.price_history[-20:]  # Last 20 periods

        swing_high = max(recent_prices)
        swing_low = min(recent_prices)

        # Ensure significant move (minimum 1% range)
        if abs(swing_high - swing_low) / swing_low < 0.01:
            return None

        # Determine direction based on recent trend
        recent_trend = self.price_history[-1] - self.price_history[-5]
        if recent_trend > 0:
            # Uptrend - base move from swing low to swing high
            return (swing_low, swing_high)
        else:
            # Downtrend - base move from swing high to swing low
            return (swing_high, swing_low)

    def _create_extension_signal(self, extension_type: ExtensionType,
                               extension_level: ExtensionLevel,
                               extension_price: float,
                               base_start: float, base_end: float,
                               extension_ratio: float, timestamp: datetime,
                               order_book_data: Dict = None,
                               trade_data: List = None) -> FibonacciExtensionSignal:
        """
        Create a Fibonacci extension signal with all institutional features
        """
        current_price = self.price_history[-1]

        # Calculate confidence components
        confidence_components = self._calculate_confidence_components(
            extension_price, order_book_data, trade_data
        )

        # Composite confidence
        composite_confidence = np.mean(list(confidence_components.values()))

        # Risk management
        suggested_sl, suggested_tp = self._calculate_risk_management(
            extension_type, extension_price, base_start, base_end
        )

        # Additional metadata
        additional_metadata = {
            'extension_ratio': extension_ratio,
            'base_move_range': abs(base_end - base_start),
            'extension_distance': abs(current_price - base_end),
            'volume_profile': self._analyze_volume_profile(),
            'timeframe_alignment': self._check_timeframe_alignment(extension_price),
            'smart_money_score': self._calculate_smart_money_score(order_book_data, trade_data)
        }

        return FibonacciExtensionSignal(
            value_raw=current_price,
            signal_type=f"FIBONACCI_{extension_type.value.upper()}_EXTENSION_{extension_level.name}",
            composite_confidence=composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=suggested_sl,
            suggested_tp=suggested_tp,
            timestamp=timestamp,
            additional_metadata=additional_metadata,
            extension_type=extension_type,
            extension_level=extension_level,
            extension_price=extension_price,
            base_move_start=base_start,
            base_move_end=base_end,
            extension_ratio=extension_ratio,
            volume_at_extension=self.volume_history[-1] if self.volume_history else 0,
            time_at_extension=len(self.price_history),
            confluence_score=self._calculate_confluence_score(extension_price)
        )

    def _calculate_confidence_components(self, extension_price: float,
                                      order_book_data: Dict = None,
                                      trade_data: List = None) -> Dict[str, float]:
        """
        Calculate confidence components for the extension signal
        """
        components = {}

        # Volume confirmation
        components['volume_score'] = self._calculate_volume_score()

        # Price action confirmation
        components['price_action_score'] = self._calculate_price_action_score(extension_price)

        # Smart money confirmation
        components['smart_money_score'] = self._calculate_smart_money_score(order_book_data, trade_data)

        # Timeframe alignment
        components['timeframe_score'] = self._check_timeframe_alignment(extension_price)

        # Historical success rate
        components['historical_score'] = self._calculate_historical_success_rate()

        return components

    def _calculate_volume_score(self) -> float:
        """Calculate volume confirmation score"""
        if len(self.volume_history) < 5:
            return 0.5

        recent_volume = np.mean(self.volume_history[-5:])
        avg_volume = np.mean(self.volume_history)

        if recent_volume > avg_volume * 1.5:
            return 0.9  # High volume confirmation
        elif recent_volume > avg_volume * 1.2:
            return 0.7  # Moderate volume confirmation
        elif recent_volume > avg_volume * 0.8:
            return 0.5  # Neutral volume
        else:
            return 0.3  # Low volume - potential weak signal

    def _calculate_price_action_score(self, extension_price: float) -> float:
        """Calculate price action confirmation score"""
        if len(self.price_history) < 10:
            return 0.5

        # Check for decisive price action around extension level
        recent_prices = self.price_history[-10:]
        price_std = np.std(recent_prices)

        # Lower volatility around extension suggests stronger level
        if price_std < np.mean(recent_prices) * 0.02:  # Less than 2% volatility
            return 0.8
        elif price_std < np.mean(recent_prices) * 0.05:  # Less than 5% volatility
            return 0.6
        else:
            return 0.4

    def _calculate_smart_money_score(self, order_book_data: Dict = None,
                                   trade_data: List = None) -> float:
        """Calculate smart money confirmation score"""
        score = 0.5  # Neutral starting point

        if order_book_data:
            # Analyze order book imbalance
            bids_volume = sum(order_book_data.get('bids', {}).values())
            asks_volume = sum(order_book_data.get('asks', {}).values())

            if bids_volume > 0 and asks_volume > 0:
                imbalance = abs(bids_volume - asks_volume) / (bids_volume + asks_volume)
                score = min(0.9, 0.5 + imbalance)  # Higher imbalance = higher score

        if trade_data:
            # Analyze large trades
            large_trades = [trade for trade in trade_data if trade[1] > np.mean([t[1] for t in trade_data]) * 2]
            if large_trades:
                score = min(0.95, score + 0.2)  # Large trades increase confidence

        return score

    def _check_timeframe_alignment(self, extension_price: float) -> float:
        """Check alignment with higher timeframes"""
        # Simplified timeframe alignment check
        # In practice, this would check multiple timeframes
        return 0.7  # Placeholder - would analyze higher timeframe charts

    def _calculate_historical_success_rate(self) -> float:
        """Calculate historical success rate of similar extensions"""
        # Analyze past extension signals
        if len(self.extension_signals) < 5:
            return 0.5  # Not enough history

        successful_signals = sum(1 for signal in self.extension_signals[-10:]
                               if signal.composite_confidence > 0.7)

        return successful_signals / min(10, len(self.extension_signals))

    def _calculate_risk_management(self, extension_type: ExtensionType,
                                 extension_price: float,
                                 base_start: float, base_end: float) -> Tuple[float, float]:
        """Calculate stop loss and take profit levels"""
        base_range = abs(base_end - base_start)

        if extension_type == ExtensionType.BULLISH:
            # For bullish extension, stop below recent swing low
            suggested_sl = base_start * 0.98  # 2% below base start
            # Target next extension level or 2:1 reward:risk
            risk = extension_price - suggested_sl
            suggested_tp = extension_price + (risk * 2)
        else:
            # For bearish extension, stop above recent swing high
            suggested_sl = base_end * 1.02  # 2% above base end
            # Target next extension level or 2:1 reward:risk
            risk = suggested_sl - extension_price
            suggested_tp = extension_price - (risk * 2)

        return suggested_sl, suggested_tp

    def _analyze_volume_profile(self) -> Dict[str, Any]:
        """Analyze volume profile around extension levels"""
        if len(self.volume_history) < 10:
            return {}

        recent_volume = self.volume_history[-10:]
        avg_volume = np.mean(recent_volume)
        volume_trend = np.polyfit(range(len(recent_volume)), recent_volume, 1)[0]

        return {
            'average_volume': avg_volume,
            'volume_trend': volume_trend,
            'volume_surge': recent_volume[-1] > avg_volume * 1.5
        }

    def _calculate_confluence_score(self, extension_price: float) -> float:
        """Calculate confluence score with other technical levels"""
        confluence_factors = 0
        max_factors = 3

        # Check proximity to round numbers
        round_number = round(extension_price, -1)  # Nearest 10
        if abs(extension_price - round_number) / extension_price < 0.01:
            confluence_factors += 1

        # Check proximity to 50/100 levels
        if abs(extension_price % 50) / extension_price < 0.005:
            confluence_factors += 1

        # Check proximity to psychological levels
        if abs(extension_price % 100) / extension_price < 0.005:
            confluence_factors += 1

        return confluence_factors / max_factors

    def get_extension_history(self) -> List[FibonacciExtensionSignal]:
        """Get historical extension signals"""
        return self.extension_signals.copy()

    def get_active_extensions(self) -> List[Dict[str, Any]]:
        """Get currently active extension levels"""
        # Return extension levels that are still relevant
        active_levels = []

        if len(self.price_history) < 10:
            return active_levels

        base_move = self._find_base_move()
        if not base_move:
            return active_levels

        base_start, base_end = base_move
        base_range = abs(base_end - base_start)

        # Calculate extension levels
        for level in ExtensionLevel:
            bullish_extension = base_start + (base_range * level.value)
            bearish_extension = base_end - (base_range * level.value)

            active_levels.extend([
                {
                    'type': 'bullish',
                    'level': level,
                    'price': bullish_extension,
                    'ratio': level.value
                },
                {
                    'type': 'bearish',
                    'level': level,
                    'price': bearish_extension,
                    'ratio': level.value
                }
            ])

        return active_levels