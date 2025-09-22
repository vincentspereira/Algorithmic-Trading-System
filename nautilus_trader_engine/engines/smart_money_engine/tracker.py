"""
Smart Money Tracking Engine for Institutional-Grade Trading

Features:
- Order flow imbalance analysis
- Cumulative delta calculation
- Volume profile analysis
- Institutional flow detection
- Order book analysis integration
- Smart money indicators
- Real-time alert generation
"""

import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

import pandas as pd
import numpy as np
from nautilus_trader.model.data import Bar


class SmartMoneySignal(Enum):
    """Smart money signal types"""
    ACCUMULATION = "accumulation"
    DISTRIBUTION = "distribution"
    NEUTRAL = "neutral"
    STRONG_ACCUMULATION = "strong_accumulation"
    STRONG_DISTRIBUTION = "strong_distribution"


@dataclass
class SmartMoneyAlert:
    """Smart money alert data"""
    timestamp: datetime
    signal_type: SmartMoneySignal
    confidence: float
    volume_imbalance: float
    cumulative_delta: float
    order_book_pressure: float
    metadata: Dict[str, Any]


class OrderBookAnalyzer:
    """Analyzes order book data for smart money detection"""

    def __init__(self, depth_levels: int = 10):
        self.depth_levels = depth_levels
        self.bid_ask_data = []

    def update_order_book(self, bids: List[Tuple[float, float]], asks: List[Tuple[float, float]]):
        """Update with new order book data"""
        self.bid_ask_data.append({
            'timestamp': datetime.now(),
            'bids': bids[:self.depth_levels],
            'asks': asks[:self.depth_levels]
        })

        # Keep only recent data
        if len(self.bid_ask_data) > 1000:
            self.bid_ask_data = self.bid_ask_data[-1000:]

    def calculate_order_book_imbalance(self) -> float:
        """Calculate order book imbalance (-1 to 1, negative = bearish, positive = bullish)"""
        if not self.bid_ask_data:
            return 0.0

        latest = self.bid_ask_data[-1]
        bids = latest['bids']
        asks = latest['asks']

        # Calculate total bid and ask volumes
        bid_volume = sum(vol for _, vol in bids)
        ask_volume = sum(vol for _, vol in asks)

        if bid_volume + ask_volume == 0:
            return 0.0

        # Calculate imbalance
        imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume)
        return imbalance

    def detect_large_orders(self, threshold_multiplier: float = 2.0) -> List[Dict[str, Any]]:
        """Detect large orders that might indicate institutional activity"""
        if len(self.bid_ask_data) < 2:
            return []

        current = self.bid_ask_data[-1]
        previous = self.bid_ask_data[-2]

        large_orders = []

        # Check for significant changes in order book
        for i, (current_bid, current_ask) in enumerate(zip(current['bids'], current['asks'])):
            if i < len(previous['bids']) and i < len(previous['asks']):
                prev_bid_vol = previous['bids'][i][1]
                prev_ask_vol = previous['asks'][i][1]

                # Detect large bid increases
                if current_bid[1] > prev_bid_vol * threshold_multiplier:
                    large_orders.append({
                        'type': 'large_bid',
                        'price': current_bid[0],
                        'volume': current_bid[1],
                        'change_ratio': current_bid[1] / prev_bid_vol if prev_bid_vol > 0 else float('inf')
                    })

                # Detect large ask increases
                if current_ask[1] > prev_ask_vol * threshold_multiplier:
                    large_orders.append({
                        'type': 'large_ask',
                        'price': current_ask[0],
                        'volume': current_ask[1],
                        'change_ratio': current_ask[1] / prev_ask_vol if prev_ask_vol > 0 else float('inf')
                    })

        return large_orders


class SmartMoneyTracker:
    """
    Institutional-grade smart money tracking system

    Analyzes:
    - Order flow imbalances
    - Cumulative delta
    - Volume profiles
    - Institutional activity patterns
    - Order book pressure
    """

    def __init__(self,
                 volume_threshold: float = 2.0,
                 delta_threshold: float = 1000,
                 lookback_period: int = 20):
        """
        Initialize smart money tracker

        Args:
            volume_threshold: Multiplier for volume threshold detection
            delta_threshold: Minimum delta for signal generation
            lookback_period: Period for calculating moving averages
        """
        self.volume_threshold = volume_threshold
        self.delta_threshold = delta_threshold
        self.lookback_period = lookback_period

        # Data storage
        self.price_data = []
        self.volume_data = []
        self.cumulative_delta = 0.0
        self.delta_history = []

        # Order book analyzer
        self.order_book_analyzer = OrderBookAnalyzer()

        # Volume profile
        self.volume_profile = {}

        # Alerts
        self.alerts = []

        # Performance tracking
        self.total_signals = 0
        self.accurate_signals = 0

        self.logger = logging.getLogger(self.__class__.__name__)

    def update_with_bar(self, bar: Bar) -> Optional[SmartMoneyAlert]:
        """
        Update with new bar data and return smart money alert if detected

        Args:
            bar: New bar data

        Returns:
            SmartMoneyAlert if smart money activity detected, None otherwise
        """
        try:
            # Store data
            self.price_data.append({
                'timestamp': datetime.fromtimestamp(bar.ts_event / 1e9),
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume
            })

            self.volume_data.append(bar.volume)

            # Maintain data size
            max_size = self.lookback_period * 10
            if len(self.price_data) > max_size:
                self.price_data = self.price_data[-max_size:]
                self.volume_data = self.volume_data[-max_size:]

            # Calculate volume profile
            self._update_volume_profile(bar)

            # Analyze for smart money signals
            alert = self._analyze_smart_money_signals(bar)

            if alert:
                self.alerts.append(alert)
                self.total_signals += 1

                # Keep alerts manageable
                if len(self.alerts) > 100:
                    self.alerts = self.alerts[-100:]

            return alert

        except Exception as e:
            self.logger.error(f"Error updating smart money tracker: {e}")
            return None

    def update_order_book(self, bids: List[Tuple[float, float]], asks: List[Tuple[float, float]]):
        """Update with order book data"""
        self.order_book_analyzer.update_order_book(bids, asks)

    def _update_volume_profile(self, bar: Bar):
        """Update volume profile analysis"""
        # Simple volume profile - count volume at price levels
        price_level = round(bar.close, 2)  # Round to 2 decimal places

        if price_level not in self.volume_profile:
            self.volume_profile[price_level] = 0

        self.volume_profile[price_level] += bar.volume

        # Keep only recent price levels
        if len(self.volume_profile) > 100:
            # Remove least active levels
            sorted_levels = sorted(self.volume_profile.items(), key=lambda x: x[1])
            for level, _ in sorted_levels[:10]:  # Remove 10 least active
                del self.volume_profile[level]

    def _analyze_smart_money_signals(self, bar: Bar) -> Optional[SmartMoneyAlert]:
        """Analyze current data for smart money signals"""
        if len(self.price_data) < self.lookback_period:
            return None

        # Calculate volume metrics
        volume_sma = np.mean(self.volume_data[-self.lookback_period:])
        volume_ratio = bar.volume / volume_sma if volume_sma > 0 else 1.0

        # Calculate price action metrics
        recent_prices = [p['close'] for p in self.price_data[-self.lookback_period:]]
        price_volatility = np.std(recent_prices) / np.mean(recent_prices)

        # Order book imbalance
        ob_imbalance = self.order_book_analyzer.calculate_order_book_imbalance()

        # Large order detection
        large_orders = self.order_book_analyzer.detect_large_orders()

        # Calculate cumulative delta (simplified)
        # In real implementation, this would use tick-by-tick data
        price_change = bar.close - bar.open
        if price_change > 0:
            delta = bar.volume * 0.7  # Assume 70% buying pressure
        elif price_change < 0:
            delta = -bar.volume * 0.7  # Assume 70% selling pressure
        else:
            delta = 0

        self.cumulative_delta += delta
        self.delta_history.append(delta)

        # Keep delta history manageable
        if len(self.delta_history) > 1000:
            self.delta_history = self.delta_history[-1000:]
            # Recalculate cumulative delta
            self.cumulative_delta = sum(self.delta_history)

        # Determine signal type
        signal_type = self._determine_signal_type(
            volume_ratio, ob_imbalance, self.cumulative_delta, large_orders
        )

        if signal_type == SmartMoneySignal.NEUTRAL:
            return None

        # Calculate confidence
        confidence = self._calculate_signal_confidence(
            volume_ratio, abs(ob_imbalance), abs(self.cumulative_delta), len(large_orders)
        )

        # Create alert
        alert = SmartMoneyAlert(
            timestamp=datetime.fromtimestamp(bar.ts_event / 1e9),
            signal_type=signal_type,
            confidence=confidence,
            volume_imbalance=volume_ratio,
            cumulative_delta=self.cumulative_delta,
            order_book_pressure=ob_imbalance,
            metadata={
                'price': bar.close,
                'volume': bar.volume,
                'volume_sma': volume_sma,
                'price_volatility': price_volatility,
                'large_orders_count': len(large_orders),
                'volume_profile_levels': len(self.volume_profile)
            }
        )

        return alert

    def _determine_signal_type(self, volume_ratio: float, ob_imbalance: float,
                              cumulative_delta: float, large_orders: List[Dict]) -> SmartMoneySignal:
        """Determine the type of smart money signal"""

        # Strong accumulation signals
        if (volume_ratio > self.volume_threshold * 1.5 and
            ob_imbalance > 0.3 and
            cumulative_delta > self.delta_threshold and
            len(large_orders) > 0):
            return SmartMoneySignal.STRONG_ACCUMULATION

        # Accumulation signals
        elif (volume_ratio > self.volume_threshold and
              ob_imbalance > 0.1 and
              cumulative_delta > self.delta_threshold * 0.5):
            return SmartMoneySignal.ACCUMULATION

        # Strong distribution signals
        elif (volume_ratio > self.volume_threshold * 1.5 and
              ob_imbalance < -0.3 and
              cumulative_delta < -self.delta_threshold and
              len(large_orders) > 0):
            return SmartMoneySignal.STRONG_DISTRIBUTION

        # Distribution signals
        elif (volume_ratio > self.volume_threshold and
              ob_imbalance < -0.1 and
              cumulative_delta < -self.delta_threshold * 0.5):
            return SmartMoneySignal.DISTRIBUTION

        return SmartMoneySignal.NEUTRAL

    def _calculate_signal_confidence(self, volume_ratio: float, ob_imbalance: float,
                                   delta_abs: float, large_orders_count: int) -> float:
        """Calculate confidence score for the signal (0.0 to 1.0)"""

        # Volume confidence
        volume_conf = min(1.0, volume_ratio / (self.volume_threshold * 2))

        # Order book confidence
        ob_conf = min(1.0, abs(ob_imbalance) * 2)

        # Delta confidence
        delta_conf = min(1.0, delta_abs / (self.delta_threshold * 2))

        # Large orders confidence
        large_order_conf = min(1.0, large_orders_count / 5)  # Max confidence at 5+ large orders

        # Weighted average
        weights = [0.3, 0.25, 0.25, 0.2]
        confidence = np.average([volume_conf, ob_conf, delta_conf, large_order_conf], weights=weights)

        return confidence

    def get_volume_profile(self, price_range: Optional[Tuple[float, float]] = None) -> Dict[float, float]:
        """Get volume profile for specified price range"""
        if price_range:
            min_price, max_price = price_range
            filtered_profile = {
                price: volume for price, volume in self.volume_profile.items()
                if min_price <= price <= max_price
            }
            return filtered_profile

        return self.volume_profile.copy()

    def get_cumulative_delta(self) -> float:
        """Get current cumulative delta"""
        return self.cumulative_delta

    def get_recent_alerts(self, hours: int = 24) -> List[SmartMoneyAlert]:
        """Get recent smart money alerts"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [alert for alert in self.alerts if alert.timestamp > cutoff_time]

    def get_signal_accuracy(self) -> float:
        """Get signal accuracy rate"""
        if self.total_signals == 0:
            return 0.0
        return self.accurate_signals / self.total_signals

    def reset(self):
        """Reset the tracker to initial state"""
        self.price_data.clear()
        self.volume_data.clear()
        self.cumulative_delta = 0.0
        self.delta_history.clear()
        self.volume_profile.clear()
        self.alerts.clear()
        self.total_signals = 0
        self.accurate_signals = 0
        self.logger.info("Smart money tracker reset")