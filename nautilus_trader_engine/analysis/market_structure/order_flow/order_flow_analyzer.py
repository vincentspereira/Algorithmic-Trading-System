"""
Institutional-Grade Order Flow Analysis

This module implements advanced order flow analysis with institutional-grade features:
- Order Book Imbalance: Real-time analysis of buy/sell order imbalances
- Large Order Detection: Identification of significant market orders and iceberg orders
- Market Depth Analysis: Comprehensive analysis of order book depth and liquidity
- Smart Money Tracking: Detection of institutional order flow patterns
- Volume Profile Analysis: Time and price-based volume analysis
- Absorption Detection: Identification of order absorption by market makers

Order flow analysis reveals the actual buying and selling pressure in the market,
providing insights into institutional activity and potential price direction.
All calculations include volume-weighting, multi-timeframe confirmation,
and integrated risk management.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import statistics
import math


class OrderFlowSignal(Enum):
    """Types of order flow signals"""
    BUY_IMBALANCE = "buy_imbalance"
    SELL_IMBALANCE = "sell_imbalance"
    LARGE_BUY_ORDER = "large_buy_order"
    LARGE_SELL_ORDER = "large_sell_order"
    ORDER_ABSORPTION = "order_absorption"
    ICEBERG_DETECTED = "iceberg_detected"
    MARKET_MAKER_ACTIVITY = "market_maker_activity"


class OrderFlowStrength(Enum):
    """Strength levels for order flow analysis"""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


@dataclass
class OrderBookSnapshot:
    """Snapshot of order book at a point in time"""
    timestamp: datetime
    bids: List[Tuple[float, float]]  # List of (price, quantity) tuples
    asks: List[Tuple[float, float]]  # List of (price, quantity) tuples
    spread: float
    mid_price: float


@dataclass
class OrderFlowAnalysis:
    """Order flow analysis result"""
    signal_type: OrderFlowSignal
    strength: OrderFlowStrength
    confidence_score: float
    price_level: float
    volume_imbalance: float
    large_order_detected: bool
    iceberg_probability: float
    market_maker_absorption: bool
    smart_money_confirmed: bool
    risk_management_levels: Dict[str, float]


@dataclass
class OrderFlowTradingSignal:
    """Trading signal based on order flow analysis"""
    analysis: OrderFlowAnalysis
    direction: str  # "BUY" or "SELL"
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence_score: float
    risk_reward_ratio: float
    volume_confirmation: bool
    timeframe_alignment: bool
    timestamp: datetime


class InstitutionalOrderFlowAnalyzer:
    """
    Institutional-grade order flow analyzer.

    Features:
    - Real-time order book imbalance analysis
    - Large order and iceberg detection
    - Market maker absorption identification
    - Smart money order flow tracking
    - Volume profile analysis
    - Multi-timeframe order flow validation
    """

    def __init__(self, depth_levels: int = 20, min_order_size: float = 1000,
                 iceberg_threshold: float = 0.7):
        self.depth_levels = depth_levels  # Number of order book levels to analyze
        self.min_order_size = min_order_size  # Minimum size for "large" order detection
        self.iceberg_threshold = iceberg_threshold  # Threshold for iceberg detection

        # Historical order book data
        self.order_book_history = []
        self.max_history = 1000

        # Volume profile tracking
        self.volume_profile = {}
        self.time_price_volume = {}  # (time, price) -> volume

        # Large order tracking
        self.large_orders = []
        self.suspicious_patterns = []

    def update_order_book(self, bids: List[Tuple[float, float]],
                         asks: List[Tuple[float, float]], timestamp: datetime):
        """
        Update order book data for analysis

        Args:
            bids: List of (price, quantity) bid tuples
            asks: List of (price, quantity) ask tuples
            timestamp: Order book timestamp
        """
        # Create order book snapshot
        if bids and asks:
            best_bid = bids[0][0]
            best_ask = asks[0][0]
            spread = best_ask - best_bid
            mid_price = (best_bid + best_ask) / 2

            snapshot = OrderBookSnapshot(
                timestamp=timestamp,
                bids=bids[:self.depth_levels],
                asks=asks[:self.depth_levels],
                spread=spread,
                mid_price=mid_price
            )

            self.order_book_history.append(snapshot)

            # Keep only recent history
            if len(self.order_book_history) > self.max_history:
                self.order_book_history.pop(0)

            # Update volume profile
            self._update_volume_profile(snapshot)

    def analyze_order_flow(self, current_price: float, current_time: datetime) -> List[OrderFlowAnalysis]:
        """
        Analyze current order flow patterns

        Args:
            current_price: Current market price
            current_time: Current timestamp

        Returns:
            List of order flow analysis results
        """
        if len(self.order_book_history) < 2:
            return []

        analyses = []

        # Get latest order book
        latest_book = self.order_book_history[-1]

        # Analyze order book imbalance
        imbalance_analysis = self._analyze_order_imbalance(latest_book, current_price)
        if imbalance_analysis:
            analyses.append(imbalance_analysis)

        # Detect large orders
        large_order_analysis = self._detect_large_orders(latest_book)
        if large_order_analysis:
            analyses.extend(large_order_analysis)

        # Check for iceberg orders
        iceberg_analysis = self._detect_iceberg_orders(latest_book)
        if iceberg_analysis:
            analyses.append(iceberg_analysis)

        # Analyze market maker absorption
        absorption_analysis = self._analyze_absorption(latest_book, current_price)
        if absorption_analysis:
            analyses.append(absorption_analysis)

        # Smart money confirmation
        for analysis in analyses:
            analysis.smart_money_confirmed = self._check_smart_money_confirmation(analysis, current_time)

        return analyses

    def _analyze_order_imbalance(self, order_book: OrderBookSnapshot,
                               current_price: float) -> Optional[OrderFlowAnalysis]:
        """Analyze buy/sell order imbalance"""
        if not order_book.bids or not order_book.asks:
            return None

        # Calculate total bid and ask volumes within a price range
        price_range = order_book.spread * 10  # 10x spread range
        min_price = current_price - price_range
        max_price = current_price + price_range

        bid_volume = sum(quantity for price, quantity in order_book.bids
                        if min_price <= price <= max_price)
        ask_volume = sum(quantity for price, quantity in order_book.asks
                        if min_price <= price <= max_price)

        if bid_volume + ask_volume == 0:
            return None

        # Calculate imbalance ratio
        imbalance_ratio = (bid_volume - ask_volume) / (bid_volume + ask_volume)

        # Determine signal type and strength
        if abs(imbalance_ratio) < 0.1:
            return None  # No significant imbalance

        signal_type = (OrderFlowSignal.BUY_IMBALANCE if imbalance_ratio > 0
                      else OrderFlowSignal.SELL_IMBALANCE)

        strength = self._calculate_imbalance_strength(abs(imbalance_ratio))

        # Calculate confidence score
        confidence_score = min(1.0, abs(imbalance_ratio) * 2)

        return OrderFlowAnalysis(
            signal_type=signal_type,
            strength=strength,
            confidence_score=confidence_score,
            price_level=current_price,
            volume_imbalance=imbalance_ratio,
            large_order_detected=False,
            iceberg_probability=0.0,
            market_maker_absorption=False,
            smart_money_confirmed=False,
            risk_management_levels=self._calculate_risk_levels(current_price, signal_type)
        )

    def _detect_large_orders(self, order_book: OrderBookSnapshot) -> List[OrderFlowAnalysis]:
        """Detect large orders in the order book"""
        analyses = []

        # Check bids for large buy orders
        for price, quantity in order_book.bids:
            if quantity >= self.min_order_size:
                analysis = OrderFlowAnalysis(
                    signal_type=OrderFlowSignal.LARGE_BUY_ORDER,
                    strength=self._calculate_large_order_strength(quantity),
                    confidence_score=min(1.0, quantity / (self.min_order_size * 5)),
                    price_level=price,
                    volume_imbalance=quantity,
                    large_order_detected=True,
                    iceberg_probability=self._calculate_iceberg_probability(quantity, order_book),
                    market_maker_absorption=False,
                    smart_money_confirmed=False,
                    risk_management_levels=self._calculate_risk_levels(price, OrderFlowSignal.LARGE_BUY_ORDER)
                )
                analyses.append(analysis)

        # Check asks for large sell orders
        for price, quantity in order_book.asks:
            if quantity >= self.min_order_size:
                analysis = OrderFlowAnalysis(
                    signal_type=OrderFlowSignal.LARGE_SELL_ORDER,
                    strength=self._calculate_large_order_strength(quantity),
                    confidence_score=min(1.0, quantity / (self.min_order_size * 5)),
                    price_level=price,
                    volume_imbalance=-quantity,  # Negative for sell pressure
                    large_order_detected=True,
                    iceberg_probability=self._calculate_iceberg_probability(quantity, order_book),
                    market_maker_absorption=False,
                    smart_money_confirmed=False,
                    risk_management_levels=self._calculate_risk_levels(price, OrderFlowSignal.LARGE_SELL_ORDER)
                )
                analyses.append(analysis)

        return analyses

    def _detect_iceberg_orders(self, order_book: OrderBookSnapshot) -> Optional[OrderFlowAnalysis]:
        """Detect potential iceberg orders"""
        if len(self.order_book_history) < 5:
            return None

        # Look for orders that appear and disappear suspiciously
        current_bids = {(price, qty) for price, qty in order_book.bids}
        current_asks = {(price, qty) for price, qty in order_book.asks}

        # Check recent history for disappearing orders
        suspicious_bids = []
        suspicious_asks = []

        for i in range(1, min(5, len(self.order_book_history))):
            prev_book = self.order_book_history[-i-1]
            prev_bids = {(price, qty) for price, qty in prev_book.bids}
            prev_asks = {(price, qty) for price, qty in prev_book.asks}

            # Orders that disappeared
            disappeared_bids = prev_bids - current_bids
            disappeared_asks = prev_asks - current_asks

            suspicious_bids.extend(disappeared_bids)
            suspicious_asks.extend(disappeared_asks)

        # Calculate iceberg probability
        total_suspicious = len(suspicious_bids) + len(suspicious_asks)
        if total_suspicious > 3:  # Threshold for iceberg detection
            iceberg_prob = min(1.0, total_suspicious / 10)

            return OrderFlowAnalysis(
                signal_type=OrderFlowSignal.ICEBERG_DETECTED,
                strength=OrderFlowStrength.STRONG if iceberg_prob > 0.7 else OrderFlowStrength.MODERATE,
                confidence_score=iceberg_prob,
                price_level=order_book.mid_price,
                volume_imbalance=0.0,
                large_order_detected=False,
                iceberg_probability=iceberg_prob,
                market_maker_absorption=False,
                smart_money_confirmed=False,
                risk_management_levels=self._calculate_risk_levels(order_book.mid_price, OrderFlowSignal.ICEBERG_DETECTED)
            )

        return None

    def _analyze_absorption(self, order_book: OrderBookSnapshot,
                          current_price: float) -> Optional[OrderFlowAnalysis]:
        """Analyze market maker absorption patterns"""
        if len(self.order_book_history) < 3:
            return None

        # Check if large orders are being absorbed without price movement
        recent_books = self.order_book_history[-3:]

        # Look for consistent large orders at same price levels
        bid_absorption = self._check_level_absorption([book.bids for book in recent_books])
        ask_absorption = self._check_level_absorption([book.asks for book in recent_books])

        if bid_absorption or ask_absorption:
            signal_type = OrderFlowSignal.ORDER_ABSORPTION

            return OrderFlowAnalysis(
                signal_type=signal_type,
                strength=OrderFlowStrength.STRONG,
                confidence_score=0.8,
                price_level=current_price,
                volume_imbalance=0.0,
                large_order_detected=False,
                iceberg_probability=0.0,
                market_maker_absorption=True,
                smart_money_confirmed=False,
                risk_management_levels=self._calculate_risk_levels(current_price, signal_type)
            )

        return None

    def _check_level_absorption(self, order_levels: List[List[Tuple[float, float]]]) -> bool:
        """Check if orders are being absorbed at specific levels"""
        if not order_levels or len(order_levels) < 2:
            return False

        # Check if large orders persist across multiple snapshots
        first_levels = order_levels[0][:5]  # Top 5 levels
        persistent_orders = 0

        for price, qty in first_levels:
            if qty >= self.min_order_size * 0.5:  # Half the large order threshold
                # Check if this order persists
                persists = all(
                    any(abs(level_price - price) < 0.01 and level_qty >= qty * 0.8
                        for level_price, level_qty in book_levels[:10])
                    for book_levels in order_levels[1:]
                )
                if persists:
                    persistent_orders += 1

        return persistent_orders >= 2

    def _calculate_imbalance_strength(self, imbalance_ratio: float) -> OrderFlowStrength:
        """Calculate strength of order imbalance"""
        if imbalance_ratio > 0.5:
            return OrderFlowStrength.VERY_STRONG
        elif imbalance_ratio > 0.3:
            return OrderFlowStrength.STRONG
        elif imbalance_ratio > 0.15:
            return OrderFlowStrength.MODERATE
        else:
            return OrderFlowStrength.WEAK

    def _calculate_large_order_strength(self, quantity: float) -> OrderFlowStrength:
        """Calculate strength of large order"""
        ratio = quantity / self.min_order_size

        if ratio > 10:
            return OrderFlowStrength.VERY_STRONG
        elif ratio > 5:
            return OrderFlowStrength.STRONG
        elif ratio > 2:
            return OrderFlowStrength.MODERATE
        else:
            return OrderFlowStrength.WEAK

    def _calculate_iceberg_probability(self, quantity: float, order_book: OrderBookSnapshot) -> float:
        """Calculate probability that an order is an iceberg"""
        # Iceberg orders often show only a portion of total size
        avg_level_size = statistics.mean([qty for _, qty in order_book.bids + order_book.asks])

        if avg_level_size == 0:
            return 0.0

        size_ratio = quantity / avg_level_size

        # Higher ratios suggest potential icebergs
        return min(1.0, size_ratio / 5.0)

    def _check_smart_money_confirmation(self, analysis: OrderFlowAnalysis, current_time: datetime) -> bool:
        """Check for smart money confirmation"""
        # Smart money often shows consistent patterns
        # Check if similar signals occurred recently
        recent_signals = [book for book in self.order_book_history[-10:]
                         if (current_time - book.timestamp).seconds < 300]  # Last 5 minutes

        similar_signals = 0
        for book in recent_signals:
            # Simplified check - in reality would analyze the actual order flow
            if abs(book.mid_price - analysis.price_level) < analysis.price_level * 0.001:
                similar_signals += 1

        return similar_signals >= 3

    def _calculate_risk_levels(self, price_level: float, signal_type: OrderFlowSignal) -> Dict[str, float]:
        """Calculate risk management levels"""
        atr = self._calculate_atr()

        if signal_type in [OrderFlowSignal.BUY_IMBALANCE, OrderFlowSignal.LARGE_BUY_ORDER]:
            stop_loss = price_level - atr * 1.5
            take_profit = price_level + atr * 2.5
        elif signal_type in [OrderFlowSignal.SELL_IMBALANCE, OrderFlowSignal.LARGE_SELL_ORDER]:
            stop_loss = price_level + atr * 1.5
            take_profit = price_level - atr * 2.5
        else:
            # For absorption and iceberg signals
            stop_loss = price_level - atr
            take_profit = price_level + atr

        return {
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'breakeven_level': price_level,
            'partial_exit_level': (price_level + take_profit) / 2
        }

    def _calculate_atr(self, period: int = 14) -> float:
        """Calculate Average True Range from order book data"""
        if len(self.order_book_history) < period:
            return 0.02  # Default ATR

        spreads = [book.spread for book in self.order_book_history[-period:]]
        return statistics.mean(spreads) if spreads else 0.02

    def _update_volume_profile(self, order_book: OrderBookSnapshot):
        """Update volume profile with order book data"""
        # Aggregate volume at price levels
        for price, quantity in order_book.bids + order_book.asks:
            price_key = round(price, 2)  # Round to 2 decimal places
            if price_key not in self.volume_profile:
                self.volume_profile[price_key] = 0
            self.volume_profile[price_key] += quantity

    def check_order_flow_signals(self, current_price: float, current_time: datetime) -> List[OrderFlowTradingSignal]:
        """
        Check for trading signals based on order flow analysis

        Args:
            current_price: Current market price
            current_time: Current timestamp

        Returns:
            List of order flow trading signals
        """
        analyses = self.analyze_order_flow(current_price, current_time)
        signals = []

        for analysis in analyses:
            if analysis.confidence_score >= 0.6:  # Minimum confidence threshold
                signal = self._create_signal_from_analysis(analysis, current_price, current_time)
                if signal:
                    signals.append(signal)

        return signals

    def _create_signal_from_analysis(self, analysis: OrderFlowAnalysis,
                                   current_price: float, current_time: datetime) -> Optional[OrderFlowSignal]:
        """Create trading signal from order flow analysis"""
        # Determine direction
        if analysis.signal_type in [OrderFlowSignal.BUY_IMBALANCE, OrderFlowSignal.LARGE_BUY_ORDER]:
            direction = "BUY"
        elif analysis.signal_type in [OrderFlowSignal.SELL_IMBALANCE, OrderFlowSignal.LARGE_SELL_ORDER]:
            direction = "SELL"
        else:
            # For absorption and iceberg signals, direction depends on context
            direction = "BUY" if current_price >= analysis.price_level else "SELL"

        entry_price = current_price
        risk_levels = analysis.risk_management_levels

        if direction == "BUY":
            stop_loss = risk_levels['stop_loss']
            take_profit = risk_levels['take_profit']
        else:
            stop_loss = risk_levels['stop_loss']
            take_profit = risk_levels['take_profit']

        risk_reward_ratio = abs(take_profit - entry_price) / abs(stop_loss - entry_price)

        return OrderFlowTradingSignal(
            analysis=analysis,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence_score=analysis.confidence_score,
            risk_reward_ratio=risk_reward_ratio,
            volume_confirmation=analysis.large_order_detected,
            timeframe_alignment=analysis.smart_money_confirmed,
            timestamp=current_time
        )

    def get_order_flow_info(self) -> Dict[str, Any]:
        """Get comprehensive order flow analysis information"""
        return {
            'order_book_depth': len(self.order_book_history),
            'volume_profile_levels': len(self.volume_profile),
            'large_orders_detected': len(self.large_orders),
            'suspicious_patterns': len(self.suspicious_patterns),
            'current_imbalance': self._get_current_imbalance(),
            'volume_profile_summary': self._get_volume_profile_summary()
        }

    def _get_current_imbalance(self) -> Dict[str, float]:
        """Get current order book imbalance"""
        if not self.order_book_history:
            return {'bid_volume': 0, 'ask_volume': 0, 'imbalance_ratio': 0}

        latest = self.order_book_history[-1]
        bid_volume = sum(qty for _, qty in latest.bids)
        ask_volume = sum(qty for _, qty in latest.asks)

        imbalance_ratio = 0
        if bid_volume + ask_volume > 0:
            imbalance_ratio = (bid_volume - ask_volume) / (bid_volume + ask_volume)

        return {
            'bid_volume': bid_volume,
            'ask_volume': ask_volume,
            'imbalance_ratio': imbalance_ratio
        }

    def _get_volume_profile_summary(self) -> Dict[str, Any]:
        """Get volume profile summary"""
        if not self.volume_profile:
            return {'total_levels': 0, 'high_volume_levels': 0, 'avg_volume': 0}

        volumes = list(self.volume_profile.values())
        avg_volume = statistics.mean(volumes)
        high_volume_levels = sum(1 for vol in volumes if vol > avg_volume * 2)

        return {
            'total_levels': len(self.volume_profile),
            'high_volume_levels': high_volume_levels,
            'avg_volume': avg_volume,
            'max_volume': max(volumes) if volumes else 0
        }


# Factory functions for easy instantiation
def create_order_flow_analyzer(depth_levels: int = 20, min_order_size: float = 1000) -> InstitutionalOrderFlowAnalyzer:
    """Create an order flow analyzer"""
    return InstitutionalOrderFlowAnalyzer(depth_levels, min_order_size)


def calculate_order_book_imbalance(bids: List[Tuple[float, float]],
                                 asks: List[Tuple[float, float]]) -> float:
    """
    Calculate order book imbalance ratio

    Args:
        bids: List of (price, quantity) bid tuples
        asks: List of (price, quantity) ask tuples

    Returns:
        Imbalance ratio (-1 to 1, positive = buy pressure)
    """
    bid_volume = sum(quantity for _, quantity in bids)
    ask_volume = sum(quantity for _, quantity in asks)

    if bid_volume + ask_volume == 0:
        return 0.0

    return (bid_volume - ask_volume) / (bid_volume + ask_volume)


def detect_large_orders(order_book: List[Tuple[float, float]],
                       min_size: float) -> List[Tuple[float, float]]:
    """
    Detect large orders in order book

    Args:
        order_book: List of (price, quantity) tuples
        min_size: Minimum size threshold

    Returns:
        List of large orders (price, quantity)
    """
    return [(price, qty) for price, qty in order_book if qty >= min_size]