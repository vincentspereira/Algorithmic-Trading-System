"""
Order Book Analytics Engine
Real-time order book analysis, market depth calculation, and liquidity analytics
"""

import asyncio
import time
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
from datetime import datetime, timedelta
import threading
from concurrent.futures import ThreadPoolExecutor
import uuid

# Import core components
from ..core.messaging.message_bus import MessageBus
from ..core.caching.cache_manager import CacheManager


class OrderBookSide(Enum):
    """Order book sides"""
    BID = "bid"
    ASK = "ask"


class ImbalanceType(Enum):
    """Types of order book imbalance"""
    BID_HEAVY = "bid_heavy"
    ASK_HEAVY = "ask_heavy"
    BALANCED = "balanced"
    EXTREME_BID = "extreme_bid"
    EXTREME_ASK = "extreme_ask"


class LiquidityTier(Enum):
    """Liquidity tier classifications"""
    TIER_1 = "tier_1"  # Top of book
    TIER_2 = "tier_2"  # Near touch
    TIER_3 = "tier_3"  # Mid-range
    TIER_4 = "tier_4"  # Deep book
    TIER_5 = "tier_5"  # Far from touch


@dataclass
class OrderBookLevel:
    """Individual order book level"""
    price: float
    size: float
    orders: int = 1
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if self.price <= 0:
            raise ValueError("Price must be positive")
        if self.size <= 0:
            raise ValueError("Size must be positive")


@dataclass
class OrderBookSnapshot:
    """Complete order book snapshot"""
    symbol: str
    timestamp: datetime
    bids: List[OrderBookLevel] = field(default_factory=list)
    asks: List[OrderBookLevel] = field(default_factory=list)
    
    # Market data
    last_price: Optional[float] = None
    last_size: Optional[float] = None
    volume: float = 0.0
    
    # Derived metrics
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    spread: Optional[float] = None
    mid_price: Optional[float] = None
    
    def __post_init__(self):
        # Sort levels
        self.bids.sort(key=lambda x: x.price, reverse=True)  # Highest first
        self.asks.sort(key=lambda x: x.price)  # Lowest first
        
        # Calculate derived metrics
        if self.bids:
            self.bid_price = self.bids[0].price
        if self.asks:
            self.ask_price = self.asks[0].price
        
        if self.bid_price and self.ask_price:
            self.spread = self.ask_price - self.bid_price
            self.mid_price = (self.bid_price + self.ask_price) / 2
    
    def get_total_size(self, side: OrderBookSide, levels: int = None) -> float:
        """Get total size for a side"""
        if side == OrderBookSide.BID:
            levels_to_use = self.bids[:levels] if levels else self.bids
        else:
            levels_to_use = self.asks[:levels] if levels else self.asks
        
        return sum(level.size for level in levels_to_use)
    
    def get_weighted_price(self, side: OrderBookSide, levels: int = None) -> Optional[float]:
        """Get size-weighted average price for a side"""
        if side == OrderBookSide.BID:
            levels_to_use = self.bids[:levels] if levels else self.bids
        else:
            levels_to_use = self.asks[:levels] if levels else self.asks
        
        if not levels_to_use:
            return None
        
        total_value = sum(level.price * level.size for level in levels_to_use)
        total_size = sum(level.size for level in levels_to_use)
        
        return total_value / total_size if total_size > 0 else None


@dataclass
class SpreadAnalysis:
    """Bid-ask spread analysis"""
    symbol: str
    timestamp: datetime
    
    # Current spread metrics
    absolute_spread: float
    relative_spread: float  # As percentage of mid price
    effective_spread: Optional[float] = None  # Based on trade prices
    
    # Statistical measures
    spread_volatility: float = 0.0
    avg_spread_1min: float = 0.0
    avg_spread_5min: float = 0.0
    avg_spread_15min: float = 0.0
    
    # Spread percentiles
    spread_p25: float = 0.0
    spread_p50: float = 0.0
    spread_p75: float = 0.0
    spread_p95: float = 0.0
    
    # Market quality indicators
    quoted_spread_ratio: float = 0.0  # Quoted vs effective spread
    spread_stability: float = 0.0  # Measure of spread consistency
    
    def get_spread_quality_score(self) -> float:
        """Calculate overall spread quality score (0-1)"""
        # Lower relative spread is better
        spread_score = max(0, 1 - (self.relative_spread / 0.01))  # 1% as reference
        
        # Higher stability is better
        stability_score = self.spread_stability
        
        # Lower volatility is better
        volatility_score = max(0, 1 - (self.spread_volatility / 0.005))  # 0.5% as reference
        
        return (spread_score + stability_score + volatility_score) / 3


@dataclass
class MarketDepthAnalysis:
    """Market depth analysis"""
    symbol: str
    timestamp: datetime
    
    # Depth metrics
    bid_depth_1: float = 0.0  # Size at best bid
    ask_depth_1: float = 0.0  # Size at best ask
    bid_depth_5: float = 0.0  # Total size in top 5 bid levels
    ask_depth_5: float = 0.0  # Total size in top 5 ask levels
    bid_depth_10: float = 0.0  # Total size in top 10 bid levels
    ask_depth_10: float = 0.0  # Total size in top 10 ask levels
    
    # Depth ratios
    depth_ratio_1: float = 0.0  # bid_depth_1 / ask_depth_1
    depth_ratio_5: float = 0.0  # bid_depth_5 / ask_depth_5
    depth_ratio_10: float = 0.0  # bid_depth_10 / ask_depth_10
    
    # Price impact estimates
    impact_1000: float = 0.0  # Price impact for $1000 trade
    impact_5000: float = 0.0  # Price impact for $5000 trade
    impact_10000: float = 0.0  # Price impact for $10000 trade
    
    # Liquidity tiers
    tier_1_liquidity: float = 0.0  # Top of book liquidity
    tier_2_liquidity: float = 0.0  # Near touch liquidity
    tier_3_liquidity: float = 0.0  # Mid-range liquidity
    
    # Market depth quality
    depth_consistency: float = 0.0  # How consistent depth is across levels
    depth_resilience: float = 0.0  # How quickly depth replenishes
    
    def get_liquidity_score(self) -> float:
        """Calculate overall liquidity score (0-1)"""
        # Normalize depth metrics
        total_depth = self.bid_depth_10 + self.ask_depth_10
        depth_score = min(1.0, total_depth / 100000)  # $100k as reference
        
        # Balance score (closer to 1.0 is better balanced)
        balance_score = 1.0 - abs(self.depth_ratio_10 - 1.0) / max(self.depth_ratio_10, 1.0)
        
        # Consistency and resilience
        quality_score = (self.depth_consistency + self.depth_resilience) / 2
        
        return (depth_score + balance_score + quality_score) / 3


@dataclass
class OrderBookImbalance:
    """Order book imbalance analysis"""
    symbol: str
    timestamp: datetime
    
    # Imbalance metrics
    imbalance_ratio: float  # (bid_size - ask_size) / (bid_size + ask_size)
    imbalance_type: ImbalanceType
    imbalance_strength: float  # 0-1 scale
    
    # Level-specific imbalances
    level_1_imbalance: float = 0.0
    level_5_imbalance: float = 0.0
    level_10_imbalance: float = 0.0
    
    # Weighted imbalances (closer levels have more weight)
    weighted_imbalance: float = 0.0
    
    # Temporal analysis
    imbalance_persistence: float = 0.0  # How long imbalance lasts
    imbalance_momentum: float = 0.0  # Rate of imbalance change
    
    # Predictive indicators
    price_pressure: float = 0.0  # Expected price movement direction
    urgency_score: float = 0.0  # How urgent the imbalance is
    
    def is_significant(self, threshold: float = 0.3) -> bool:
        """Check if imbalance is significant"""
        return abs(self.imbalance_ratio) > threshold
    
    def get_direction_signal(self) -> str:
        """Get directional signal from imbalance"""
        if self.imbalance_ratio > 0.2:
            return "bullish"
        elif self.imbalance_ratio < -0.2:
            return "bearish"
        else:
            return "neutral"


@dataclass
class PriceLevelCluster:
    """Price level clustering analysis"""
    symbol: str
    timestamp: datetime
    
    # Cluster identification
    cluster_id: str
    price_center: float
    price_range: Tuple[float, float]
    total_size: float
    level_count: int
    
    # Cluster characteristics
    cluster_strength: float  # Size concentration
    cluster_density: float  # Levels per price unit
    cluster_persistence: float  # How long cluster exists
    
    # Support/resistance properties
    is_support: bool = False
    is_resistance: bool = False
    break_probability: float = 0.0
    
    # Historical performance
    touch_count: int = 0  # How many times price touched this cluster
    hold_rate: float = 0.0  # How often cluster held
    break_rate: float = 0.0  # How often cluster was broken


class OrderBookAnalyticsEngine:
    """
    Advanced Order Book Analytics Engine
    
    Features:
    - Real-time bid-ask spread analysis
    - Market depth calculation and visualization
    - Order book imbalance detection
    - Price level clustering analysis
    - Liquidity tier analysis
    - Market impact estimation
    - Support/resistance level detection
    """
    
    def __init__(self,
                 message_bus: Optional[MessageBus] = None,
                 cache_manager: Optional[CacheManager] = None,
                 max_book_levels: int = 20,
                 analysis_window_seconds: int = 300,
                 enable_real_time: bool = True):
        
        self.message_bus = message_bus
        self.cache_manager = cache_manager
        self.max_book_levels = max_book_levels
        self.analysis_window_seconds = analysis_window_seconds
        self.enable_real_time = enable_real_time
        
        # Order book storage
        self._order_books: Dict[str, OrderBookSnapshot] = {}
        self._book_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Analysis results storage
        self._spread_analysis: Dict[str, SpreadAnalysis] = {}
        self._depth_analysis: Dict[str, MarketDepthAnalysis] = {}
        self._imbalance_analysis: Dict[str, OrderBookImbalance] = {}
        self._price_clusters: Dict[str, List[PriceLevelCluster]] = defaultdict(list)
        
        # Real-time processing
        self._processing_queue = asyncio.Queue(maxsize=10000)
        self._analysis_tasks: List[asyncio.Task] = []
        self._running = False
        
        # Thread pool for intensive calculations
        self._thread_pool = ThreadPoolExecutor(
            max_workers=4,
            thread_name_prefix="orderbook-analytics"
        )
        
        # Performance metrics
        self._metrics = {
            'books_processed': 0,
            'analyses_completed': 0,
            'avg_processing_time_ms': 0.0,
            'queue_size': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Analysis configuration
        self._config = {
            'spread_analysis_enabled': True,
            'depth_analysis_enabled': True,
            'imbalance_analysis_enabled': True,
            'clustering_analysis_enabled': True,
            'min_spread_for_analysis': 0.0001,  # Minimum spread to analyze
            'max_spread_for_analysis': 0.1,     # Maximum spread to analyze
            'imbalance_threshold': 0.1,         # Minimum imbalance to report
            'cluster_min_size': 1000.0,         # Minimum size for cluster
            'cluster_price_tolerance': 0.001    # Price tolerance for clustering
        }
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start the order book analytics engine"""
        if self._running:
            return
        
        self._running = True
        
        # Start analysis workers
        if self.enable_real_time:
            for i in range(4):  # 4 analysis workers
                task = asyncio.create_task(self._analysis_worker(f"analytics-{i}"))
                self._analysis_tasks.append(task)
        
        # Start metrics tracking
        asyncio.create_task(self._metrics_tracker())
        
        self.logger.info("Order Book Analytics Engine started")
    
    async def stop(self):
        """Stop the order book analytics engine"""
        self._running = False
        
        # Cancel analysis tasks
        for task in self._analysis_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._analysis_tasks:
            await asyncio.gather(*self._analysis_tasks, return_exceptions=True)
        
        # Shutdown thread pool
        self._thread_pool.shutdown(wait=True)
        
        self.logger.info("Order Book Analytics Engine stopped")
    
    async def update_order_book(self, symbol: str, order_book: OrderBookSnapshot):
        """Update order book and trigger analysis"""
        try:
            # Store current book
            self._order_books[symbol] = order_book
            
            # Add to history
            self._book_history[symbol].append(order_book)
            
            # Cache the order book
            if self.cache_manager:
                await self.cache_manager.set(
                    f"orderbook:{symbol}",
                    order_book,
                    ttl=60
                )
            
            # Queue for analysis if real-time enabled
            if self.enable_real_time:
                try:
                    analysis_request = {
                        'type': 'order_book_update',
                        'symbol': symbol,
                        'order_book': order_book,
                        'timestamp': time.time_ns()
                    }
                    await self._processing_queue.put(analysis_request)
                except asyncio.QueueFull:
                    self.logger.warning(f"Analysis queue full, dropping update for {symbol}")
            
            self._metrics['books_processed'] += 1
            
        except Exception as e:
            self.logger.error(f"Failed to update order book for {symbol}: {e}")
    
    async def _analysis_worker(self, worker_name: str):
        """Background worker for order book analysis"""
        self.logger.debug(f"Analysis worker {worker_name} started")
        
        while self._running:
            try:
                # Get analysis request from queue
                try:
                    request = await asyncio.wait_for(
                        self._processing_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process the analysis request
                await self._process_analysis_request(request, worker_name)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Analysis worker {worker_name} error: {e}")
                await asyncio.sleep(1)
        
        self.logger.debug(f"Analysis worker {worker_name} stopped")
    
    async def _process_analysis_request(self, request: Dict[str, Any], worker_name: str):
        """Process an analysis request"""
        start_time = time.time_ns()
        
        try:
            symbol = request['symbol']
            order_book = request['order_book']
            
            # Run all enabled analyses
            analyses = []
            
            if self._config['spread_analysis_enabled']:
                analyses.append(self._analyze_spread(symbol, order_book))
            
            if self._config['depth_analysis_enabled']:
                analyses.append(self._analyze_market_depth(symbol, order_book))
            
            if self._config['imbalance_analysis_enabled']:
                analyses.append(self._analyze_imbalance(symbol, order_book))
            
            if self._config['clustering_analysis_enabled']:
                analyses.append(self._analyze_price_clustering(symbol, order_book))
            
            # Execute analyses concurrently
            results = await asyncio.gather(*analyses, return_exceptions=True)
            
            # Handle results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"Analysis {i} failed for {symbol}: {result}")
            
            # Publish analysis results
            await self._publish_analysis_results(symbol)
            
            # Update metrics
            processing_time = (time.time_ns() - start_time) / 1_000_000
            self._metrics['analyses_completed'] += 1
            
            # Update average processing time
            current_avg = self._metrics['avg_processing_time_ms']
            total_analyses = self._metrics['analyses_completed']
            self._metrics['avg_processing_time_ms'] = (
                (current_avg * (total_analyses - 1) + processing_time) / total_analyses
            )
            
        except Exception as e:
            self.logger.error(f"Analysis processing failed: {e}")
    
    async def _analyze_spread(self, symbol: str, order_book: OrderBookSnapshot):
        """Analyze bid-ask spread"""
        try:
            if not order_book.bid_price or not order_book.ask_price:
                return
            
            # Calculate current spread metrics
            absolute_spread = order_book.spread
            relative_spread = absolute_spread / order_book.mid_price if order_book.mid_price else 0
            
            # Skip analysis if spread is outside configured range
            if (absolute_spread < self._config['min_spread_for_analysis'] or
                absolute_spread > self._config['max_spread_for_analysis']):
                return
            
            # Get historical spreads for statistical analysis
            historical_books = list(self._book_history[symbol])
            if len(historical_books) < 10:
                # Not enough history for statistical analysis
                spread_analysis = SpreadAnalysis(
                    symbol=symbol,
                    timestamp=order_book.timestamp,
                    absolute_spread=absolute_spread,
                    relative_spread=relative_spread
                )
            else:
                # Calculate statistical measures
                spreads = []
                for book in historical_books[-100:]:  # Last 100 books
                    if book.spread:
                        spreads.append(book.spread)
                
                if spreads:
                    spreads_array = np.array(spreads)
                    
                    # Time-based averages (approximate based on available data)
                    avg_spread_1min = np.mean(spreads_array[-20:]) if len(spreads) >= 20 else absolute_spread
                    avg_spread_5min = np.mean(spreads_array[-100:]) if len(spreads) >= 100 else absolute_spread
                    avg_spread_15min = np.mean(spreads_array) if len(spreads) >= 300 else absolute_spread
                    
                    # Percentiles
                    spread_p25 = np.percentile(spreads_array, 25)
                    spread_p50 = np.percentile(spreads_array, 50)
                    spread_p75 = np.percentile(spreads_array, 75)
                    spread_p95 = np.percentile(spreads_array, 95)
                    
                    # Volatility
                    spread_volatility = np.std(spreads_array) / np.mean(spreads_array) if np.mean(spreads_array) > 0 else 0
                    
                    # Stability (inverse of coefficient of variation)
                    spread_stability = 1.0 / (1.0 + spread_volatility)
                    
                    spread_analysis = SpreadAnalysis(
                        symbol=symbol,
                        timestamp=order_book.timestamp,
                        absolute_spread=absolute_spread,
                        relative_spread=relative_spread,
                        spread_volatility=spread_volatility,
                        avg_spread_1min=avg_spread_1min,
                        avg_spread_5min=avg_spread_5min,
                        avg_spread_15min=avg_spread_15min,
                        spread_p25=spread_p25,
                        spread_p50=spread_p50,
                        spread_p75=spread_p75,
                        spread_p95=spread_p95,
                        spread_stability=spread_stability
                    )
                else:
                    spread_analysis = SpreadAnalysis(
                        symbol=symbol,
                        timestamp=order_book.timestamp,
                        absolute_spread=absolute_spread,
                        relative_spread=relative_spread
                    )
            
            # Store analysis
            self._spread_analysis[symbol] = spread_analysis
            
        except Exception as e:
            self.logger.error(f"Spread analysis failed for {symbol}: {e}")
    
    async def _analyze_market_depth(self, symbol: str, order_book: OrderBookSnapshot):
        """Analyze market depth"""
        try:
            # Calculate depth metrics
            bid_depth_1 = order_book.get_total_size(OrderBookSide.BID, 1)
            ask_depth_1 = order_book.get_total_size(OrderBookSide.ASK, 1)
            bid_depth_5 = order_book.get_total_size(OrderBookSide.BID, 5)
            ask_depth_5 = order_book.get_total_size(OrderBookSide.ASK, 5)
            bid_depth_10 = order_book.get_total_size(OrderBookSide.BID, 10)
            ask_depth_10 = order_book.get_total_size(OrderBookSide.ASK, 10)
            
            # Calculate depth ratios
            depth_ratio_1 = bid_depth_1 / ask_depth_1 if ask_depth_1 > 0 else 0
            depth_ratio_5 = bid_depth_5 / ask_depth_5 if ask_depth_5 > 0 else 0
            depth_ratio_10 = bid_depth_10 / ask_depth_10 if ask_depth_10 > 0 else 0
            
            # Estimate price impact for different trade sizes
            impact_1000 = self._estimate_price_impact(order_book, 1000.0)
            impact_5000 = self._estimate_price_impact(order_book, 5000.0)
            impact_10000 = self._estimate_price_impact(order_book, 10000.0)
            
            # Calculate liquidity tiers
            tier_1_liquidity = bid_depth_1 + ask_depth_1
            tier_2_liquidity = order_book.get_total_size(OrderBookSide.BID, 3) + order_book.get_total_size(OrderBookSide.ASK, 3) - tier_1_liquidity
            tier_3_liquidity = bid_depth_5 + ask_depth_5 - tier_1_liquidity - tier_2_liquidity
            
            # Calculate depth consistency (how evenly distributed depth is)
            depth_consistency = self._calculate_depth_consistency(order_book)
            
            # Calculate depth resilience (simplified - would need historical data)
            depth_resilience = 0.5  # Placeholder
            
            depth_analysis = MarketDepthAnalysis(
                symbol=symbol,
                timestamp=order_book.timestamp,
                bid_depth_1=bid_depth_1,
                ask_depth_1=ask_depth_1,
                bid_depth_5=bid_depth_5,
                ask_depth_5=ask_depth_5,
                bid_depth_10=bid_depth_10,
                ask_depth_10=ask_depth_10,
                depth_ratio_1=depth_ratio_1,
                depth_ratio_5=depth_ratio_5,
                depth_ratio_10=depth_ratio_10,
                impact_1000=impact_1000,
                impact_5000=impact_5000,
                impact_10000=impact_10000,
                tier_1_liquidity=tier_1_liquidity,
                tier_2_liquidity=tier_2_liquidity,
                tier_3_liquidity=tier_3_liquidity,
                depth_consistency=depth_consistency,
                depth_resilience=depth_resilience
            )
            
            # Store analysis
            self._depth_analysis[symbol] = depth_analysis
            
        except Exception as e:
            self.logger.error(f"Market depth analysis failed for {symbol}: {e}")
    
    def _estimate_price_impact(self, order_book: OrderBookSnapshot, trade_value: float) -> float:
        """Estimate price impact for a given trade value"""
        try:
            if not order_book.mid_price:
                return 0.0
            
            # Determine trade side (assume we're buying)
            remaining_value = trade_value
            total_shares = 0
            weighted_price = 0
            
            for level in order_book.asks:
                level_value = level.price * level.size
                if remaining_value <= level_value:
                    # Partial fill at this level
                    shares_needed = remaining_value / level.price
                    weighted_price += level.price * shares_needed
                    total_shares += shares_needed
                    break
                else:
                    # Full fill at this level
                    weighted_price += level.price * level.size
                    total_shares += level.size
                    remaining_value -= level_value
            
            if total_shares == 0:
                return 0.0
            
            avg_execution_price = weighted_price / total_shares
            impact = (avg_execution_price - order_book.mid_price) / order_book.mid_price
            
            return impact
            
        except Exception as e:
            self.logger.error(f"Price impact estimation failed: {e}")
            return 0.0
    
    def _calculate_depth_consistency(self, order_book: OrderBookSnapshot) -> float:
        """Calculate how consistently depth is distributed across levels"""
        try:
            # Calculate coefficient of variation for bid and ask sizes
            bid_sizes = [level.size for level in order_book.bids[:10]]
            ask_sizes = [level.size for level in order_book.asks[:10]]
            
            if not bid_sizes or not ask_sizes:
                return 0.0
            
            bid_cv = np.std(bid_sizes) / np.mean(bid_sizes) if np.mean(bid_sizes) > 0 else 0
            ask_cv = np.std(ask_sizes) / np.mean(ask_sizes) if np.mean(ask_sizes) > 0 else 0
            
            # Consistency is inverse of coefficient of variation
            avg_cv = (bid_cv + ask_cv) / 2
            consistency = 1.0 / (1.0 + avg_cv)
            
            return consistency
            
        except Exception as e:
            self.logger.error(f"Depth consistency calculation failed: {e}")
            return 0.0
    
    async def _analyze_imbalance(self, symbol: str, order_book: OrderBookSnapshot):
        """Analyze order book imbalance"""
        try:
            # Calculate basic imbalance metrics
            bid_size_1 = order_book.get_total_size(OrderBookSide.BID, 1)
            ask_size_1 = order_book.get_total_size(OrderBookSide.ASK, 1)
            bid_size_5 = order_book.get_total_size(OrderBookSide.BID, 5)
            ask_size_5 = order_book.get_total_size(OrderBookSide.ASK, 5)
            bid_size_10 = order_book.get_total_size(OrderBookSide.BID, 10)
            ask_size_10 = order_book.get_total_size(OrderBookSide.ASK, 10)
            
            # Calculate imbalance ratios
            total_size_1 = bid_size_1 + ask_size_1
            level_1_imbalance = (bid_size_1 - ask_size_1) / total_size_1 if total_size_1 > 0 else 0
            
            total_size_5 = bid_size_5 + ask_size_5
            level_5_imbalance = (bid_size_5 - ask_size_5) / total_size_5 if total_size_5 > 0 else 0
            
            total_size_10 = bid_size_10 + ask_size_10
            level_10_imbalance = (bid_size_10 - ask_size_10) / total_size_10 if total_size_10 > 0 else 0
            
            # Calculate weighted imbalance (closer levels have more weight)
            weights = [0.5, 0.3, 0.2]  # Weights for levels 1, 5, 10
            weighted_imbalance = (
                weights[0] * level_1_imbalance +
                weights[1] * level_5_imbalance +
                weights[2] * level_10_imbalance
            )
            
            # Determine imbalance type and strength
            imbalance_ratio = level_5_imbalance  # Use 5-level as primary
            imbalance_strength = abs(imbalance_ratio)
            
            if imbalance_ratio > 0.5:
                imbalance_type = ImbalanceType.EXTREME_BID
            elif imbalance_ratio > 0.2:
                imbalance_type = ImbalanceType.BID_HEAVY
            elif imbalance_ratio < -0.5:
                imbalance_type = ImbalanceType.EXTREME_ASK
            elif imbalance_ratio < -0.2:
                imbalance_type = ImbalanceType.ASK_HEAVY
            else:
                imbalance_type = ImbalanceType.BALANCED
            
            # Calculate temporal metrics (simplified - would need historical data)
            imbalance_persistence = 0.5  # Placeholder
            imbalance_momentum = 0.0     # Placeholder
            
            # Calculate predictive indicators
            price_pressure = imbalance_ratio * imbalance_strength
            urgency_score = min(1.0, imbalance_strength * 2)
            
            imbalance_analysis = OrderBookImbalance(
                symbol=symbol,
                timestamp=order_book.timestamp,
                imbalance_ratio=imbalance_ratio,
                imbalance_type=imbalance_type,
                imbalance_strength=imbalance_strength,
                level_1_imbalance=level_1_imbalance,
                level_5_imbalance=level_5_imbalance,
                level_10_imbalance=level_10_imbalance,
                weighted_imbalance=weighted_imbalance,
                imbalance_persistence=imbalance_persistence,
                imbalance_momentum=imbalance_momentum,
                price_pressure=price_pressure,
                urgency_score=urgency_score
            )
            
            # Store analysis
            self._imbalance_analysis[symbol] = imbalance_analysis
            
            # Check if imbalance is significant enough to report
            if imbalance_analysis.is_significant(self._config['imbalance_threshold']):
                await self._publish_imbalance_alert(symbol, imbalance_analysis)
            
        except Exception as e:
            self.logger.error(f"Imbalance analysis failed for {symbol}: {e}")
    
    async def _analyze_price_clustering(self, symbol: str, order_book: OrderBookSnapshot):
        """Analyze price level clustering"""
        try:
            clusters = []
            
            # Analyze bid side clusters
            bid_clusters = self._find_price_clusters(
                order_book.bids, 
                OrderBookSide.BID,
                symbol,
                order_book.timestamp
            )
            clusters.extend(bid_clusters)
            
            # Analyze ask side clusters
            ask_clusters = self._find_price_clusters(
                order_book.asks,
                OrderBookSide.ASK,
                symbol,
                order_book.timestamp
            )
            clusters.extend(ask_clusters)
            
            # Store clusters
            self._price_clusters[symbol] = clusters
            
            # Identify potential support/resistance levels
            await self._identify_support_resistance(symbol, clusters, order_book)
            
        except Exception as e:
            self.logger.error(f"Price clustering analysis failed for {symbol}: {e}")
    
    def _find_price_clusters(self, 
                           levels: List[OrderBookLevel], 
                           side: OrderBookSide,
                           symbol: str,
                           timestamp: datetime) -> List[PriceLevelCluster]:
        """Find price clusters in order book levels"""
        clusters = []
        
        try:
            if len(levels) < 2:
                return clusters
            
            # Group nearby price levels
            current_cluster = []
            cluster_tolerance = self._config['cluster_price_tolerance']
            
            for i, level in enumerate(levels):
                if not current_cluster:
                    current_cluster.append(level)
                else:
                    # Check if level is close enough to current cluster
                    cluster_center = sum(l.price for l in current_cluster) / len(current_cluster)
                    
                    if abs(level.price - cluster_center) / cluster_center <= cluster_tolerance:
                        current_cluster.append(level)
                    else:
                        # Finalize current cluster if it meets minimum size
                        if self._is_significant_cluster(current_cluster):
                            cluster = self._create_cluster(current_cluster, side, symbol, timestamp)
                            clusters.append(cluster)
                        
                        # Start new cluster
                        current_cluster = [level]
            
            # Handle last cluster
            if current_cluster and self._is_significant_cluster(current_cluster):
                cluster = self._create_cluster(current_cluster, side, symbol, timestamp)
                clusters.append(cluster)
            
        except Exception as e:
            self.logger.error(f"Price cluster finding failed: {e}")
        
        return clusters
    
    def _is_significant_cluster(self, levels: List[OrderBookLevel]) -> bool:
        """Check if cluster is significant enough to analyze"""
        total_size = sum(level.size for level in levels)
        return (len(levels) >= 2 and 
                total_size >= self._config['cluster_min_size'])
    
    def _create_cluster(self, 
                       levels: List[OrderBookLevel],
                       side: OrderBookSide,
                       symbol: str,
                       timestamp: datetime) -> PriceLevelCluster:
        """Create a price level cluster from levels"""
        prices = [level.price for level in levels]
        sizes = [level.size for level in levels]
        
        price_center = sum(level.price * level.size for level in levels) / sum(sizes)
        price_range = (min(prices), max(prices))
        total_size = sum(sizes)
        level_count = len(levels)
        
        # Calculate cluster characteristics
        cluster_strength = total_size / (price_range[1] - price_range[0] + 1e-10)
        cluster_density = level_count / (price_range[1] - price_range[0] + 1e-10)
        
        # Determine if it's support or resistance (simplified)
        is_support = side == OrderBookSide.BID
        is_resistance = side == OrderBookSide.ASK
        
        cluster = PriceLevelCluster(
            symbol=symbol,
            timestamp=timestamp,
            cluster_id=str(uuid.uuid4()),
            price_center=price_center,
            price_range=price_range,
            total_size=total_size,
            level_count=level_count,
            cluster_strength=cluster_strength,
            cluster_density=cluster_density,
            cluster_persistence=0.5,  # Placeholder
            is_support=is_support,
            is_resistance=is_resistance,
            break_probability=0.1,  # Placeholder
            touch_count=0,
            hold_rate=0.0,
            break_rate=0.0
        )
        
        return cluster
    
    async def _identify_support_resistance(self, 
                                         symbol: str, 
                                         clusters: List[PriceLevelCluster],
                                         order_book: OrderBookSnapshot):
        """Identify support and resistance levels from clusters"""
        try:
            if not order_book.mid_price:
                return
            
            # Find strongest clusters near current price
            nearby_clusters = [
                cluster for cluster in clusters
                if abs(cluster.price_center - order_book.mid_price) / order_book.mid_price < 0.05
            ]
            
            # Sort by strength
            nearby_clusters.sort(key=lambda x: x.cluster_strength, reverse=True)
            
            # Identify top support and resistance levels
            support_levels = [c for c in nearby_clusters if c.is_support][:3]
            resistance_levels = [c for c in nearby_clusters if c.is_resistance][:3]
            
            # Store in metadata for later use
            if not hasattr(self, '_support_resistance'):
                self._support_resistance = {}
            
            self._support_resistance[symbol] = {
                'support_levels': support_levels,
                'resistance_levels': resistance_levels,
                'timestamp': order_book.timestamp
            }
            
        except Exception as e:
            self.logger.error(f"Support/resistance identification failed for {symbol}: {e}")
    
    async def _publish_analysis_results(self, symbol: str):
        """Publish analysis results to message bus"""
        try:
            if not self.message_bus:
                return
            
            # Prepare analysis summary
            analysis_summary = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'spread_analysis': self._spread_analysis.get(symbol),
                'depth_analysis': self._depth_analysis.get(symbol),
                'imbalance_analysis': self._imbalance_analysis.get(symbol),
                'price_clusters': len(self._price_clusters.get(symbol, [])),
                'support_resistance': self._support_resistance.get(symbol) if hasattr(self, '_support_resistance') else None
            }
            
            # Convert dataclasses to dicts for serialization
            if analysis_summary['spread_analysis']:
                analysis_summary['spread_analysis'] = {
                    'symbol': analysis_summary['spread_analysis'].symbol,
                    'absolute_spread': analysis_summary['spread_analysis'].absolute_spread,
                    'relative_spread': analysis_summary['spread_analysis'].relative_spread,
                    'spread_quality_score': analysis_summary['spread_analysis'].get_spread_quality_score()
                }
            
            if analysis_summary['depth_analysis']:
                analysis_summary['depth_analysis'] = {
                    'symbol': analysis_summary['depth_analysis'].symbol,
                    'liquidity_score': analysis_summary['depth_analysis'].get_liquidity_score(),
                    'tier_1_liquidity': analysis_summary['depth_analysis'].tier_1_liquidity,
                    'depth_ratio_5': analysis_summary['depth_analysis'].depth_ratio_5
                }
            
            if analysis_summary['imbalance_analysis']:
                analysis_summary['imbalance_analysis'] = {
                    'symbol': analysis_summary['imbalance_analysis'].symbol,
                    'imbalance_ratio': analysis_summary['imbalance_analysis'].imbalance_ratio,
                    'imbalance_type': analysis_summary['imbalance_analysis'].imbalance_type.value,
                    'direction_signal': analysis_summary['imbalance_analysis'].get_direction_signal()
                }
            
            # Publish to message bus
            await self.message_bus.publish(
                topic=f"analytics.orderbook.{symbol}",
                message=analysis_summary
            )
            
        except Exception as e:
            self.logger.error(f"Failed to publish analysis results for {symbol}: {e}")
    
    async def _publish_imbalance_alert(self, symbol: str, imbalance: OrderBookImbalance):
        """Publish significant imbalance alert"""
        try:
            if not self.message_bus:
                return
            
            alert = {
                'type': 'order_book_imbalance',
                'symbol': symbol,
                'timestamp': imbalance.timestamp.isoformat(),
                'imbalance_ratio': imbalance.imbalance_ratio,
                'imbalance_type': imbalance.imbalance_type.value,
                'strength': imbalance.imbalance_strength,
                'direction_signal': imbalance.get_direction_signal(),
                'urgency_score': imbalance.urgency_score
            }
            
            await self.message_bus.publish(
                topic=f"alerts.imbalance.{symbol}",
                message=alert
            )
            
        except Exception as e:
            self.logger.error(f"Failed to publish imbalance alert for {symbol}: {e}")
    
    async def _metrics_tracker(self):
        """Track and update metrics"""
        while self._running:
            try:
                # Update queue size metric
                self._metrics['queue_size'] = self._processing_queue.qsize()
                
                # Log metrics periodically
                if self._metrics['analyses_completed'] % 100 == 0 and self._metrics['analyses_completed'] > 0:
                    self.logger.info(
                        f"Order Book Analytics Metrics: "
                        f"Books processed: {self._metrics['books_processed']}, "
                        f"Analyses completed: {self._metrics['analyses_completed']}, "
                        f"Avg processing time: {self._metrics['avg_processing_time_ms']:.2f}ms, "
                        f"Queue size: {self._metrics['queue_size']}"
                    )
                
                await asyncio.sleep(10)  # Update every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Metrics tracking error: {e}")
                await asyncio.sleep(5)
    
    # Public API methods
    
    async def get_spread_analysis(self, symbol: str) -> Optional[SpreadAnalysis]:
        """Get latest spread analysis for symbol"""
        return self._spread_analysis.get(symbol)
    
    async def get_depth_analysis(self, symbol: str) -> Optional[MarketDepthAnalysis]:
        """Get latest depth analysis for symbol"""
        return self._depth_analysis.get(symbol)
    
    async def get_imbalance_analysis(self, symbol: str) -> Optional[OrderBookImbalance]:
        """Get latest imbalance analysis for symbol"""
        return self._imbalance_analysis.get(symbol)
    
    async def get_price_clusters(self, symbol: str) -> List[PriceLevelCluster]:
        """Get latest price clusters for symbol"""
        return self._price_clusters.get(symbol, [])
    
    async def get_support_resistance_levels(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get support and resistance levels for symbol"""
        return getattr(self, '_support_resistance', {}).get(symbol)
    
    async def get_current_order_book(self, symbol: str) -> Optional[OrderBookSnapshot]:
        """Get current order book snapshot"""
        # Try cache first
        if self.cache_manager:
            cached_book = await self.cache_manager.get(f"orderbook:{symbol}")
            if cached_book:
                self._metrics['cache_hits'] += 1
                return cached_book
            else:
                self._metrics['cache_misses'] += 1
        
        return self._order_books.get(symbol)
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get engine metrics"""
        return self._metrics.copy()
    
    async def update_config(self, config_updates: Dict[str, Any]):
        """Update engine configuration"""
        try:
            for key, value in config_updates.items():
                if key in self._config:
                    self._config[key] = value
                    self.logger.info(f"Updated config {key} = {value}")
                else:
                    self.logger.warning(f"Unknown config key: {key}")
        except Exception as e:
            self.logger.error(f"Failed to update config: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return self._config.copy()