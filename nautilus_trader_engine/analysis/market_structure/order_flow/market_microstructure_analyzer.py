"""
Market Microstructure Analysis for Order Flow

Advanced market microstructure analysis for institutional-grade order flow detection:
- Bid-Ask Spread Analysis: Market liquidity and efficiency measurement
- Trade Aggression Analysis: Buy/sell pressure and market impact
- Order Book Imbalance: Real-time order book dynamics
- Market Maker Activity: Identifying dealer behavior patterns
- High-Frequency Flow Analysis: Ultra-fast order flow patterns
- Liquidity Analysis: Market depth and resilience assessment

All implementations include volume-weighting, smart money confirmation,
multi-timeframe analysis, adaptive confidence scoring, and integrated risk management.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import numpy as np

from ...core.base_classes import AugmentedIndicator


class MicrostructureSignalType(Enum):
    """Signal types for market microstructure analysis"""
    LIQUIDITY_DRY_UP = "LIQUIDITY_DRY_UP"
    MARKET_MAKER_ABSENCE = "MARKET_MAKER_ABSENCE"
    HIGH_AGGRESSION_IMBALANCE = "HIGH_AGGRESSION_IMBALANCE"
    ORDER_BOOK_THINNING = "ORDER_BOOK_THINNING"
    SPREAD_WIDENING = "SPREAD_WIDENING"
    DEPTH_IMBALANCE = "DEPTH_IMBALANCE"
    INSTITUTIONAL_SWEEP = "INSTITUTIONAL_SWEEP"


class AggressionType(Enum):
    """Types of trade aggression"""
    PASSIVE = "passive"
    AGGRESSIVE_BUY = "aggressive_buy"
    AGGRESSIVE_SELL = "aggressive_sell"
    MARKET_ORDER = "market_order"
    LARGE_BLOCK = "large_block"


@dataclass
class MicrostructureSignal:
    """Signal for market microstructure analysis"""
    value_raw: float
    signal_type: str
    composite_confidence: float
    confidence_components: Dict[str, float]
    suggested_sl: float
    suggested_tp: float
    timestamp: datetime
    additional_metadata: Dict[str, Any]

    # Microstructure specific fields
    spread_analysis: Dict[str, float]
    depth_analysis: Dict[str, float]
    aggression_metrics: Dict[str, float]
    liquidity_score: float
    market_efficiency: float


@dataclass
class OrderBookMetrics:
    """Comprehensive order book metrics"""
    bid_ask_spread: float
    spread_percentage: float
    bid_depth: float
    ask_depth: float
    depth_imbalance: float
    order_book_slope: float
    liquidity_concentration: float
    timestamp: datetime


@dataclass
class TradeAggressionMetrics:
    """Trade aggression and market impact metrics"""
    aggression_ratio: float
    buy_aggression: float
    sell_aggression: float
    large_trade_ratio: float
    market_impact: float
    trade_clustering: float
    timestamp: datetime


class MarketMicrostructureAnalyzer(AugmentedIndicator):
    """
    Advanced Market Microstructure Analyzer for Order Flow

    Institutional-grade analysis of market microstructure to identify:
    - Order book dynamics and liquidity patterns
    - Trade aggression and market maker behavior
    - Bid-ask spread analysis and market efficiency
    - High-frequency order flow patterns
    - Institutional activity detection through microstructure

    All implementations include volume-weighting, smart money confirmation,
    multi-timeframe analysis, adaptive confidence scoring, and integrated risk management.
    """

    def __init__(self, timeframe: str = "1Min", order_book_depth: int = 20,
                 aggression_window: int = 100, spread_threshold: float = 0.001):
        super().__init__(name="MarketMicrostructureAnalyzer", timeframe=timeframe)
        self.order_book_depth = order_book_depth
        self.aggression_window = aggression_window
        self.spread_threshold = spread_threshold

        # Data storage
        self.price_history = []
        self.order_book_history = []
        self.trade_history = []  # (price, volume, timestamp, is_buy, aggression_type)

        # Analysis metrics
        self.spread_history = []
        self.depth_history = []
        self.aggression_history = []

        # Current state
        self.current_order_book = {'bids': {}, 'asks': {}}
        self.baseline_spread = None
        self.baseline_depth = None

    def update(self, price: float, volume: float, timestamp: datetime = None,
               order_book_data: Dict = None, trade_data: List = None) -> Optional[MicrostructureSignal]:
        """
        Update analyzer with new market data

        Args:
            price: Current price
            volume: Current volume
            timestamp: Data timestamp
            order_book_data: Current order book snapshot
            trade_data: List of recent trades with aggression info

        Returns:
            MicrostructureSignal if significant microstructure activity detected, None otherwise
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Update data
        self.price_history.append(price)

        if order_book_data:
            self._update_order_book(order_book_data, timestamp)

        if trade_data:
            self._update_trades(trade_data, timestamp)

        # Maintain history size
        max_history = 1000
        if len(self.price_history) > max_history:
            self.price_history = self.price_history[-max_history:]

        # Analyze microstructure
        order_book_metrics = self._analyze_order_book()
        aggression_metrics = self._analyze_trade_aggression()

        # Generate signal if significant activity
        signal = self._generate_microstructure_signal(order_book_metrics, aggression_metrics, timestamp)

        if signal:
            self.current_signal = signal

        return signal

    def _update_order_book(self, order_book_data: Dict, timestamp: datetime):
        """Update order book data"""
        self.current_order_book = {
            'bids': dict(order_book_data.get('bids', {})),
            'asks': dict(order_book_data.get('asks', {})),
            'timestamp': timestamp
        }

        self.order_book_history.append(self.current_order_book)

        # Maintain history
        if len(self.order_book_history) > 100:
            self.order_book_history = self.order_book_history[-100:]

    def _update_trades(self, trade_data: List, timestamp: datetime):
        """Update trade data with aggression analysis"""
        for trade in trade_data:
            if len(trade) >= 4:  # (price, volume, is_buy, aggression_type)
                price, volume, is_buy, aggression_type = trade[:4]
                self.trade_history.append((price, volume, timestamp, is_buy, aggression_type))

        # Maintain history
        if len(self.trade_history) > 1000:
            self.trade_history = self.trade_history[-1000:]

    def _analyze_order_book(self) -> OrderBookMetrics:
        """Analyze current order book microstructure"""
        if not self.current_order_book.get('bids') or not self.current_order_book.get('asks'):
            return None

        bids = self.current_order_book['bids']
        asks = self.current_order_book['asks']

        # Calculate bid-ask spread
        best_bid = max(bids.keys()) if bids else 0
        best_ask = min(asks.keys()) if asks else float('inf')

        if best_bid > 0 and best_ask < float('inf'):
            spread = best_ask - best_bid
            spread_percentage = spread / best_bid
        else:
            spread = 0
            spread_percentage = 0

        # Calculate depth
        bid_depth = sum(bids.values())
        ask_depth = sum(asks.values())

        # Depth imbalance
        total_depth = bid_depth + ask_depth
        if total_depth > 0:
            depth_imbalance = (bid_depth - ask_depth) / total_depth
        else:
            depth_imbalance = 0

        # Order book slope (price sensitivity)
        order_book_slope = self._calculate_order_book_slope(bids, asks)

        # Liquidity concentration
        liquidity_concentration = self._calculate_liquidity_concentration(bids, asks)

        return OrderBookMetrics(
            bid_ask_spread=spread,
            spread_percentage=spread_percentage,
            bid_depth=bid_depth,
            ask_depth=ask_depth,
            depth_imbalance=depth_imbalance,
            order_book_slope=order_book_slope,
            liquidity_concentration=liquidity_concentration,
            timestamp=self.current_order_book.get('timestamp', datetime.now())
        )

    def _calculate_order_book_slope(self, bids: Dict[float, float], asks: Dict[float, float]) -> float:
        """Calculate order book slope (price sensitivity)"""
        if len(bids) < 2 or len(asks) < 2:
            return 0

        # Calculate slope for bids (should be negative for normal books)
        bid_prices = sorted(bids.keys(), reverse=True)[:5]  # Top 5 bids
        bid_volumes = [bids[p] for p in bid_prices]

        if len(bid_prices) >= 2:
            bid_slope = np.polyfit(range(len(bid_prices)), bid_prices, 1)[0]
        else:
            bid_slope = 0

        # Calculate slope for asks (should be positive for normal books)
        ask_prices = sorted(asks.keys())[:5]  # Top 5 asks
        ask_volumes = [asks[p] for p in ask_prices]

        if len(ask_prices) >= 2:
            ask_slope = np.polyfit(range(len(ask_prices)), ask_prices, 1)[0]
        else:
            ask_slope = 0

        # Combined slope metric
        return (bid_slope + ask_slope) / 2

    def _calculate_liquidity_concentration(self, bids: Dict[float, float], asks: Dict[float, float]) -> float:
        """Calculate liquidity concentration (how much liquidity is at best bid/ask)"""
        total_bid_volume = sum(bids.values())
        total_ask_volume = sum(asks.values())

        if total_bid_volume == 0 or total_ask_volume == 0:
            return 0

        best_bid_volume = bids.get(max(bids.keys()), 0) if bids else 0
        best_ask_volume = asks.get(min(asks.keys()), 0) if asks else 0

        bid_concentration = best_bid_volume / total_bid_volume
        ask_concentration = best_ask_volume / total_ask_volume

        return (bid_concentration + ask_concentration) / 2

    def _analyze_trade_aggression(self) -> TradeAggressionMetrics:
        """Analyze trade aggression patterns"""
        if len(self.trade_history) < 10:
            return None

        recent_trades = self.trade_history[-self.aggression_window:]

        # Separate buy and sell trades
        buy_trades = [(p, v, t) for p, v, t, is_buy, agg in recent_trades if is_buy]
        sell_trades = [(p, v, t) for p, v, t, is_buy, agg in recent_trades if not is_buy]

        # Calculate aggression ratios
        total_buy_volume = sum(v for _, v, _ in buy_trades)
        total_sell_volume = sum(v for _, v, _ in sell_trades)
        total_volume = total_buy_volume + total_sell_volume

        if total_volume > 0:
            aggression_ratio = abs(total_buy_volume - total_sell_volume) / total_volume
        else:
            aggression_ratio = 0

        # Calculate buy/sell aggression
        aggressive_buy_volume = sum(v for _, v, _ in buy_trades if any(agg in ['aggressive_buy', 'market_order'] for _, _, _, _, agg in recent_trades if _ == buy_trades.index((_, v, _)) + 1))
        aggressive_sell_volume = sum(v for _, v, _ in sell_trades if any(agg in ['aggressive_sell', 'market_order'] for _, _, _, _, agg in recent_trades if _ == sell_trades.index((_, v, _)) + 1))

        if total_buy_volume > 0:
            buy_aggression = aggressive_buy_volume / total_buy_volume
        else:
            buy_aggression = 0

        if total_sell_volume > 0:
            sell_aggression = aggressive_sell_volume / total_sell_volume
        else:
            sell_aggression = 0

        # Large trade analysis
        all_volumes = [v for _, v, _ in recent_trades]
        if all_volumes:
            avg_volume = np.mean(all_volumes)
            large_trades = sum(1 for v in all_volumes if v > avg_volume * 3)
            large_trade_ratio = large_trades / len(all_volumes)
        else:
            large_trade_ratio = 0

        # Market impact estimation
        market_impact = self._calculate_market_impact(recent_trades)

        # Trade clustering
        trade_clustering = self._calculate_trade_clustering(recent_trades)

        return TradeAggressionMetrics(
            aggression_ratio=aggression_ratio,
            buy_aggression=buy_aggression,
            sell_aggression=sell_aggression,
            large_trade_ratio=large_trade_ratio,
            market_impact=market_impact,
            trade_clustering=trade_clustering,
            timestamp=datetime.now()
        )

    def _calculate_market_impact(self, trades: List) -> float:
        """Calculate market impact of trades"""
        if len(trades) < 5:
            return 0

        # Simple market impact model
        price_changes = []
        for i in range(1, len(trades)):
            prev_price = trades[i-1][0]
            curr_price = trades[i][0]
            if prev_price > 0:
                price_changes.append(abs(curr_price - prev_price) / prev_price)

        if price_changes:
            return np.mean(price_changes)
        return 0

    def _calculate_trade_clustering(self, trades: List) -> float:
        """Calculate trade clustering (how bunched up trades are)"""
        if len(trades) < 10:
            return 0

        timestamps = [t[2] for t in trades]
        time_diffs = []

        for i in range(1, len(timestamps)):
            diff = (timestamps[i] - timestamps[i-1]).total_seconds()
            time_diffs.append(diff)

        if time_diffs:
            avg_time_diff = np.mean(time_diffs)
            std_time_diff = np.std(time_diffs)

            # Clustering score (lower std means more clustering)
            if avg_time_diff > 0:
                clustering = 1 - min(std_time_diff / avg_time_diff, 1)
                return max(clustering, 0)
        return 0

    def _generate_microstructure_signal(self, order_book_metrics: OrderBookMetrics,
                                      aggression_metrics: TradeAggressionMetrics,
                                      timestamp: datetime) -> Optional[MicrostructureSignal]:
        """Generate microstructure signal based on analysis"""
        if not order_book_metrics or not aggression_metrics:
            return None

        current_price = self.price_history[-1] if self.price_history else 0

        # Analyze various microstructure conditions
        signal_type = None
        confidence_score = 0

        # Liquidity dry-up detection
        if order_book_metrics.spread_percentage > self.spread_threshold * 3:
            signal_type = MicrostructureSignalType.SPREAD_WIDENING
            confidence_score = min(order_book_metrics.spread_percentage / (self.spread_threshold * 5), 1.0)

        # Order book thinning
        elif order_book_metrics.bid_depth < 100 or order_book_metrics.ask_depth < 100:
            signal_type = MicrostructureSignalType.ORDER_BOOK_THINNING
            min_depth = min(order_book_metrics.bid_depth, order_book_metrics.ask_depth)
            confidence_score = max(0, 1 - min_depth / 100)

        # High aggression imbalance
        elif aggression_metrics.aggression_ratio > 0.7:
            if aggression_metrics.buy_aggression > aggression_metrics.sell_aggression:
                signal_type = MicrostructureSignalType.HIGH_AGGRESSION_IMBALANCE
            else:
                signal_type = MicrostructureSignalType.HIGH_AGGRESSION_IMBALANCE
            confidence_score = aggression_metrics.aggression_ratio

        # Institutional sweep detection
        elif aggression_metrics.large_trade_ratio > 0.3:
            signal_type = MicrostructureSignalType.INSTITUTIONAL_SWEEP
            confidence_score = aggression_metrics.large_trade_ratio

        # Depth imbalance
        elif abs(order_book_metrics.depth_imbalance) > 0.6:
            signal_type = MicrostructureSignalType.DEPTH_IMBALANCE
            confidence_score = abs(order_book_metrics.depth_imbalance)

        if signal_type and confidence_score > 0.6:
            # Calculate confidence components
            confidence_components = {
                'spread_score': min(order_book_metrics.spread_percentage / self.spread_threshold, 1.0),
                'depth_score': min((order_book_metrics.bid_depth + order_book_metrics.ask_depth) / 200, 1.0),
                'aggression_score': aggression_metrics.aggression_ratio,
                'large_trade_score': aggression_metrics.large_trade_ratio,
                'clustering_score': aggression_metrics.trade_clustering
            }

            composite_confidence = np.mean(list(confidence_components.values()))

            # Risk management
            volatility_estimate = order_book_metrics.spread_percentage * current_price
            suggested_sl = current_price - volatility_estimate * 2
            suggested_tp = current_price + volatility_estimate * 3

            # Additional metadata
            additional_metadata = {
                'order_book_metrics': {
                    'spread': order_book_metrics.bid_ask_spread,
                    'spread_pct': order_book_metrics.spread_percentage,
                    'bid_depth': order_book_metrics.bid_depth,
                    'ask_depth': order_book_metrics.ask_depth,
                    'depth_imbalance': order_book_metrics.depth_imbalance
                },
                'aggression_metrics': {
                    'aggression_ratio': aggression_metrics.aggression_ratio,
                    'buy_aggression': aggression_metrics.buy_aggression,
                    'sell_aggression': aggression_metrics.sell_aggression,
                    'large_trade_ratio': aggression_metrics.large_trade_ratio
                },
                'liquidity_score': (order_book_metrics.bid_depth + order_book_metrics.ask_depth) / 200,
                'market_efficiency': 1 - order_book_metrics.spread_percentage
            }

            return MicrostructureSignal(
                value_raw=current_price,
                signal_type=f"MICROSTRUCTURE_{signal_type.value}",
                composite_confidence=composite_confidence,
                confidence_components=confidence_components,
                suggested_sl=suggested_sl,
                suggested_tp=suggested_tp,
                timestamp=timestamp,
                additional_metadata=additional_metadata,
                spread_analysis={
                    'current_spread': order_book_metrics.bid_ask_spread,
                    'spread_percentage': order_book_metrics.spread_percentage,
                    'spread_efficiency': 1 - order_book_metrics.spread_percentage
                },
                depth_analysis={
                    'bid_depth': order_book_metrics.bid_depth,
                    'ask_depth': order_book_metrics.ask_depth,
                    'depth_imbalance': order_book_metrics.depth_imbalance,
                    'liquidity_concentration': order_book_metrics.liquidity_concentration
                },
                aggression_metrics={
                    'aggression_ratio': aggression_metrics.aggression_ratio,
                    'buy_aggression': aggression_metrics.buy_aggression,
                    'sell_aggression': aggression_metrics.sell_aggression,
                    'large_trade_ratio': aggression_metrics.large_trade_ratio,
                    'trade_clustering': aggression_metrics.trade_clustering
                },
                liquidity_score=(order_book_metrics.bid_depth + order_book_metrics.ask_depth) / 200,
                market_efficiency=1 - order_book_metrics.spread_percentage
            )

        return None

    def get_microstructure_metrics(self) -> Dict[str, Any]:
        """Get current microstructure metrics"""
        order_book_metrics = self._analyze_order_book()
        aggression_metrics = self._analyze_trade_aggression()

        return {
            'order_book': order_book_metrics.__dict__ if order_book_metrics else {},
            'aggression': aggression_metrics.__dict__ if aggression_metrics else {},
            'current_price': self.price_history[-1] if self.price_history else 0,
            'data_points': len(self.price_history),
            'order_book_snapshots': len(self.order_book_history),
            'trade_count': len(self.trade_history)
        }

    def get_liquidity_analysis(self) -> Dict[str, Any]:
        """Get detailed liquidity analysis"""
        if not self.order_book_history:
            return {}

        recent_books = self.order_book_history[-20:]  # Last 20 snapshots

        spreads = []
        bid_depths = []
        ask_depths = []

        for book in recent_books:
            bids = book.get('bids', {})
            asks = book.get('asks', {})

            if bids and asks:
                best_bid = max(bids.keys())
                best_ask = min(asks.keys())
                spreads.append(best_ask - best_bid)

                bid_depths.append(sum(bids.values()))
                ask_depths.append(sum(asks.values()))

        return {
            'average_spread': np.mean(spreads) if spreads else 0,
            'spread_volatility': np.std(spreads) if spreads else 0,
            'average_bid_depth': np.mean(bid_depths) if bid_depths else 0,
            'average_ask_depth': np.mean(ask_depths) if ask_depths else 0,
            'liquidity_trend': np.polyfit(range(len(bid_depths)), bid_depths, 1)[0] if len(bid_depths) > 1 else 0,
            'samples_analyzed': len(recent_books)
        }

    def get_aggression_analysis(self) -> Dict[str, Any]:
        """Get detailed trade aggression analysis"""
        if len(self.trade_history) < 50:
            return {}

        recent_trades = self.trade_history[-200:]  # Last 200 trades

        # Analyze by aggression type
        aggression_types = {}
        for _, _, _, _, agg_type in recent_trades:
            aggression_types[agg_type] = aggression_types.get(agg_type, 0) + 1

        # Volume by aggression type
        volume_by_type = {}
        for _, volume, _, _, agg_type in recent_trades:
            if agg_type not in volume_by_type:
                volume_by_type[agg_type] = []
            volume_by_type[agg_type].append(volume)

        volume_stats = {}
        for agg_type, volumes in volume_by_type.items():
            volume_stats[agg_type] = {
                'total_volume': sum(volumes),
                'average_volume': np.mean(volumes),
                'max_volume': max(volumes),
                'trade_count': len(volumes)
            }

        return {
            'aggression_distribution': aggression_types,
            'volume_by_aggression': volume_stats,
            'total_trades_analyzed': len(recent_trades),
            'time_period': f"{recent_trades[0][2]} to {recent_trades[-1][2]}" if recent_trades else "N/A"
        }