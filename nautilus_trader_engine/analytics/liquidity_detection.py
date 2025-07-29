"""
Liquidity Detection System
Advanced algorithms for detecting hidden liquidity, iceberg orders, and dark pool activity
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
import statistics

# Import core components
from ..core.messaging.message_bus import MessageBus
from ..core.caching.cache_manager import CacheManager
from .order_book_analytics import OrderBookSnapshot, OrderBookLevel, OrderBookSide


class LiquidityType(Enum):
    """Types of liquidity"""
    VISIBLE = "visible"
    HIDDEN = "hidden"
    ICEBERG = "iceberg"
    DARK_POOL = "dark_pool"
    RESERVE = "reserve"
    PHANTOM = "phantom"


class LiquidityTier(Enum):
    """Liquidity quality tiers"""
    TIER_1 = "tier_1"  # Highest quality, most reliable
    TIER_2 = "tier_2"  # Good quality
    TIER_3 = "tier_3"  # Average quality
    TIER_4 = "tier_4"  # Lower quality
    TIER_5 = "tier_5"  # Lowest quality


class VenueType(Enum):
    """Types of trading venues"""
    LIT_EXCHANGE = "lit_exchange"
    DARK_POOL = "dark_pool"
    ECN = "ecn"
    CROSSING_NETWORK = "crossing_network"
    INTERNALIZATION = "internalization"


@dataclass
class LiquiditySignal:
    """Signal indicating presence of hidden liquidity"""
    signal_id: str
    symbol: str
    timestamp: datetime
    liquidity_type: LiquidityType
    
    # Location information
    price_level: float
    estimated_size: float
    confidence: float  # 0-1 scale
    
    # Detection method
    detection_method: str
    detection_confidence: float
    
    # Characteristics
    persistence_score: float = 0.0  # How long liquidity persists
    aggressiveness_score: float = 0.0  # How aggressively it trades
    stealth_score: float = 0.0  # How well hidden it is
    
    # Venue information
    venue_type: Optional[VenueType] = None
    venue_name: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.confidence < 0 or self.confidence > 1:
            raise ValueError("Confidence must be between 0 and 1")
        if self.detection_confidence < 0 or self.detection_confidence > 1:
            raise ValueError("Detection confidence must be between 0 and 1")


@dataclass
class IcebergOrderSignal:
    """Signal indicating presence of iceberg order"""
    signal_id: str
    symbol: str
    timestamp: datetime
    
    # Order characteristics
    price_level: float
    visible_size: float
    estimated_total_size: float
    estimated_hidden_size: float
    
    # Detection metrics
    refresh_pattern_score: float  # How consistent the refresh pattern is
    size_consistency_score: float  # How consistent visible sizes are
    timing_pattern_score: float  # How consistent timing is
    
    # Behavioral analysis
    aggression_level: float = 0.0  # How aggressively it trades
    patience_score: float = 0.0  # How long it waits
    stealth_effectiveness: float = 0.0  # How well it hides
    
    # Overall confidence
    confidence: float = 0.0
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DarkPoolActivity:
    """Analysis of dark pool trading activity"""
    symbol: str
    timestamp: datetime
    
    # Activity metrics
    estimated_dark_volume: float
    dark_volume_ratio: float  # Dark volume / Total volume
    
    # Price impact analysis
    price_improvement: float = 0.0  # Average price improvement
    execution_quality: float = 0.0  # Quality of executions
    
    # Timing analysis
    activity_concentration: float = 0.0  # How concentrated activity is
    timing_predictability: float = 0.0  # How predictable timing is
    
    # Venue analysis
    venue_distribution: Dict[str, float] = field(default_factory=dict)
    dominant_venue: Optional[str] = None
    
    # Confidence metrics
    detection_confidence: float = 0.0
    volume_confidence: float = 0.0
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VenueLiquidityScore:
    """Liquidity scoring for trading venues"""
    venue_name: str
    venue_type: VenueType
    symbol: str
    timestamp: datetime
    
    # Core liquidity metrics
    available_liquidity: float
    average_spread: float
    market_depth: float
    fill_rate: float
    
    # Quality metrics
    price_improvement: float = 0.0
    execution_speed: float = 0.0  # Average execution time
    reliability_score: float = 0.0  # How reliable the venue is
    
    # Cost metrics
    explicit_costs: float = 0.0  # Fees, commissions
    implicit_costs: float = 0.0  # Market impact, timing costs
    total_cost: float = 0.0
    
    # Overall scores
    liquidity_tier: LiquidityTier = LiquidityTier.TIER_3
    overall_score: float = 0.0  # 0-1 scale
    
    # Historical performance
    historical_fill_rate: float = 0.0
    historical_price_improvement: float = 0.0
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_overall_score(self) -> float:
        """Calculate overall venue liquidity score"""
        # Weighted combination of factors
        weights = {
            'liquidity': 0.3,
            'spread': 0.2,
            'depth': 0.2,
            'fill_rate': 0.15,
            'reliability': 0.1,
            'cost': 0.05
        }
        
        # Normalize metrics (higher is better)
        liquidity_norm = min(1.0, self.available_liquidity / 100000)  # $100k reference
        spread_norm = max(0.0, 1.0 - (self.average_spread / 0.01))  # 1% reference
        depth_norm = min(1.0, self.market_depth / 50000)  # $50k reference
        fill_rate_norm = self.fill_rate
        reliability_norm = self.reliability_score
        cost_norm = max(0.0, 1.0 - (self.total_cost / 0.005))  # 0.5% reference
        
        score = (
            weights['liquidity'] * liquidity_norm +
            weights['spread'] * spread_norm +
            weights['depth'] * depth_norm +
            weights['fill_rate'] * fill_rate_norm +
            weights['reliability'] * reliability_norm +
            weights['cost'] * cost_norm
        )
        
        self.overall_score = score
        return score


class LiquidityDetectionEngine:
    """
    Advanced Liquidity Detection Engine
    
    Features:
    - Hidden liquidity identification using volume analysis
    - Iceberg order detection through pattern recognition
    - Dark pool activity estimation
    - Venue liquidity scoring and ranking
    - Real-time liquidity monitoring
    - Machine learning-based detection algorithms
    """
    
    def __init__(self,
                 message_bus: Optional[MessageBus] = None,
                 cache_manager: Optional[CacheManager] = None,
                 detection_window_seconds: int = 300,
                 min_confidence_threshold: float = 0.6,
                 enable_real_time: bool = True):
        
        self.message_bus = message_bus
        self.cache_manager = cache_manager
        self.detection_window_seconds = detection_window_seconds
        self.min_confidence_threshold = min_confidence_threshold
        self.enable_real_time = enable_real_time
        
        # Data storage
        self._order_books: Dict[str, OrderBookSnapshot] = {}
        self._trade_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._volume_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._price_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Detection results
        self._liquidity_signals: Dict[str, List[LiquiditySignal]] = defaultdict(list)
        self._iceberg_signals: Dict[str, List[IcebergOrderSignal]] = defaultdict(list)
        self._dark_pool_activity: Dict[str, DarkPoolActivity] = {}
        self._venue_scores: Dict[str, Dict[str, VenueLiquidityScore]] = defaultdict(dict)
        
        # Detection algorithms
        self._detectors = {
            'volume_anomaly': self._detect_volume_anomaly_liquidity,
            'size_pattern': self._detect_size_pattern_liquidity,
            'refresh_pattern': self._detect_refresh_pattern_liquidity,
            'iceberg_order': self._detect_iceberg_orders,
            'dark_pool': self._detect_dark_pool_activity,
            'hidden_depth': self._detect_hidden_depth
        }
        
        # Real-time processing
        self._processing_queue = asyncio.Queue(maxsize=5000)
        self._detection_tasks: List[asyncio.Task] = []
        self._running = False
        
        # Thread pool for intensive calculations
        self._thread_pool = ThreadPoolExecutor(
            max_workers=4,
            thread_name_prefix="liquidity-detection"
        )
        
        # Configuration
        self._config = {
            'volume_anomaly_threshold': 2.0,  # Standard deviations
            'iceberg_refresh_tolerance': 0.1,  # 10% tolerance
            'dark_pool_min_volume': 1000.0,   # Minimum volume to consider
            'hidden_liquidity_min_size': 5000.0,  # Minimum size for hidden liquidity
            'venue_score_update_interval': 60,  # Seconds
            'detection_sensitivity': 0.7,      # Detection sensitivity (0-1)
            'max_signals_per_symbol': 50       # Maximum signals to keep per symbol
        }
        
        # Performance metrics
        self._metrics = {
            'signals_detected': 0,
            'iceberg_orders_detected': 0,
            'dark_pool_activities_detected': 0,
            'venue_scores_calculated': 0,
            'avg_detection_time_ms': 0.0,
            'false_positive_rate': 0.0,
            'detection_accuracy': 0.0
        }
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start the liquidity detection engine"""
        if self._running:
            return
        
        self._running = True
        
        # Start detection workers
        if self.enable_real_time:
            for i in range(4):
                task = asyncio.create_task(self._detection_worker(f"liquidity-detector-{i}"))
                self._detection_tasks.append(task)
        
        # Start venue scoring task
        asyncio.create_task(self._venue_scoring_task())
        
        # Start metrics tracking
        asyncio.create_task(self._metrics_tracker())
        
        self.logger.info("Liquidity Detection Engine started")
    
    async def stop(self):
        """Stop the liquidity detection engine"""
        self._running = False
        
        # Cancel detection tasks
        for task in self._detection_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._detection_tasks:
            await asyncio.gather(*self._detection_tasks, return_exceptions=True)
        
        # Shutdown thread pool
        self._thread_pool.shutdown(wait=True)
        
        self.logger.info("Liquidity Detection Engine stopped")
    
    async def update_order_book(self, symbol: str, order_book: OrderBookSnapshot):
        """Update order book and trigger liquidity detection"""
        try:
            # Store order book
            self._order_books[symbol] = order_book
            
            # Cache the order book
            if self.cache_manager:
                await self.cache_manager.set(
                    f"liquidity:orderbook:{symbol}",
                    order_book,
                    ttl=60
                )
            
            # Queue for detection if real-time enabled
            if self.enable_real_time:
                try:
                    detection_request = {
                        'type': 'order_book_update',
                        'symbol': symbol,
                        'order_book': order_book,
                        'timestamp': time.time_ns()
                    }
                    await self._processing_queue.put(detection_request)
                except asyncio.QueueFull:
                    self.logger.warning(f"Detection queue full, dropping update for {symbol}")
            
        except Exception as e:
            self.logger.error(f"Failed to update order book for {symbol}: {e}")
    
    async def update_trade_data(self, symbol: str, price: float, size: float, timestamp: datetime):
        """Update trade data for liquidity analysis"""
        try:
            trade_data = {
                'price': price,
                'size': size,
                'timestamp': timestamp,
                'value': price * size
            }
            
            self._trade_history[symbol].append(trade_data)
            self._volume_history[symbol].append(size)
            self._price_history[symbol].append(price)
            
            # Queue for analysis
            if self.enable_real_time:
                try:
                    detection_request = {
                        'type': 'trade_update',
                        'symbol': symbol,
                        'trade_data': trade_data,
                        'timestamp': time.time_ns()
                    }
                    await self._processing_queue.put(detection_request)
                except asyncio.QueueFull:
                    self.logger.warning(f"Detection queue full, dropping trade update for {symbol}")
            
        except Exception as e:
            self.logger.error(f"Failed to update trade data for {symbol}: {e}")
    
    async def _detection_worker(self, worker_name: str):
        """Background worker for liquidity detection"""
        self.logger.debug(f"Detection worker {worker_name} started")
        
        while self._running:
            try:
                # Get detection request from queue
                try:
                    request = await asyncio.wait_for(
                        self._processing_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process the detection request
                await self._process_detection_request(request, worker_name)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Detection worker {worker_name} error: {e}")
                await asyncio.sleep(1)
        
        self.logger.debug(f"Detection worker {worker_name} stopped")
    
    async def _process_detection_request(self, request: Dict[str, Any], worker_name: str):
        """Process a liquidity detection request"""
        start_time = time.time_ns()
        
        try:
            symbol = request['symbol']
            request_type = request['type']
            
            # Run appropriate detectors based on request type
            if request_type == 'order_book_update':
                order_book = request['order_book']
                await self._run_order_book_detectors(symbol, order_book)
            elif request_type == 'trade_update':
                trade_data = request['trade_data']
                await self._run_trade_detectors(symbol, trade_data)
            
            # Update metrics
            processing_time = (time.time_ns() - start_time) / 1_000_000
            self._update_processing_metrics(processing_time)
            
        except Exception as e:
            self.logger.error(f"Detection processing failed: {e}")
    
    async def _run_order_book_detectors(self, symbol: str, order_book: OrderBookSnapshot):
        """Run order book-based detection algorithms"""
        try:
            # Run detectors concurrently
            detection_tasks = [
                self._detectors['volume_anomaly'](symbol, order_book),
                self._detectors['size_pattern'](symbol, order_book),
                self._detectors['refresh_pattern'](symbol, order_book),
                self._detectors['hidden_depth'](symbol, order_book)
            ]
            
            results = await asyncio.gather(*detection_tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"Order book detector {i} failed for {symbol}: {result}")
                elif result:
                    await self._process_detection_results(symbol, result)
            
        except Exception as e:
            self.logger.error(f"Order book detection failed for {symbol}: {e}")
    
    async def _run_trade_detectors(self, symbol: str, trade_data: Dict[str, Any]):
        """Run trade-based detection algorithms"""
        try:
            # Run trade-based detectors
            detection_tasks = [
                self._detectors['iceberg_order'](symbol, trade_data),
                self._detectors['dark_pool'](symbol, trade_data)
            ]
            
            results = await asyncio.gather(*detection_tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"Trade detector {i} failed for {symbol}: {result}")
                elif result:
                    await self._process_detection_results(symbol, result)
            
        except Exception as e:
            self.logger.error(f"Trade detection failed for {symbol}: {e}")
    
    async def _detect_volume_anomaly_liquidity(self, symbol: str, order_book: OrderBookSnapshot) -> Optional[List[LiquiditySignal]]:
        """Detect hidden liquidity through volume anomalies"""
        try:
            signals = []
            
            if len(self._volume_history[symbol]) < 20:
                return signals
            
            # Analyze recent volume patterns
            recent_volumes = list(self._volume_history[symbol])[-20:]
            volume_mean = statistics.mean(recent_volumes)
            volume_std = statistics.stdev(recent_volumes) if len(recent_volumes) > 1 else 0
            
            if volume_std == 0:
                return signals
            
            # Check for volume spikes that might indicate hidden liquidity
            current_volume = recent_volumes[-1] if recent_volumes else 0
            z_score = (current_volume - volume_mean) / volume_std
            
            if abs(z_score) > self._config['volume_anomaly_threshold']:
                # Potential hidden liquidity signal
                confidence = min(0.9, abs(z_score) / 5.0)  # Scale z-score to confidence
                
                # Determine likely price level (use mid price as estimate)
                price_level = order_book.mid_price if order_book.mid_price else 0
                
                signal = LiquiditySignal(
                    signal_id=f"vol_anomaly_{symbol}_{int(time.time_ns())}",
                    symbol=symbol,
                    timestamp=datetime.now(),
                    liquidity_type=LiquidityType.HIDDEN,
                    price_level=price_level,
                    estimated_size=current_volume * 2,  # Estimate hidden size
                    confidence=confidence,
                    detection_method="volume_anomaly",
                    detection_confidence=confidence,
                    persistence_score=0.5,  # Placeholder
                    stealth_score=0.7,  # High stealth for volume anomalies
                    metadata={
                        'z_score': z_score,
                        'volume_mean': volume_mean,
                        'volume_std': volume_std,
                        'current_volume': current_volume
                    }
                )
                
                signals.append(signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Volume anomaly detection failed for {symbol}: {e}")
            return []
    
    async def _detect_size_pattern_liquidity(self, symbol: str, order_book: OrderBookSnapshot) -> Optional[List[LiquiditySignal]]:
        """Detect hidden liquidity through size patterns"""
        try:
            signals = []
            
            # Analyze order book for unusual size patterns
            for side in [OrderBookSide.BID, OrderBookSide.ASK]:
                levels = order_book.bids if side == OrderBookSide.BID else order_book.asks
                
                if len(levels) < 5:
                    continue
                
                # Look for size patterns that might indicate hidden liquidity
                sizes = [level.size for level in levels[:10]]
                
                # Check for unusually consistent sizes (might indicate iceberg)
                size_variance = np.var(sizes) if len(sizes) > 1 else 0
                size_mean = np.mean(sizes)
                
                if size_variance < (size_mean * 0.1) and size_mean > self._config['hidden_liquidity_min_size']:
                    # Potential iceberg or hidden liquidity
                    confidence = 0.6 + min(0.3, (size_mean - self._config['hidden_liquidity_min_size']) / 10000)
                    
                    signal = LiquiditySignal(
                        signal_id=f"size_pattern_{symbol}_{side.value}_{int(time.time_ns())}",
                        symbol=symbol,
                        timestamp=datetime.now(),
                        liquidity_type=LiquidityType.ICEBERG,
                        price_level=levels[0].price,
                        estimated_size=size_mean * 5,  # Estimate total hidden size
                        confidence=confidence,
                        detection_method="size_pattern",
                        detection_confidence=confidence,
                        persistence_score=0.8,  # Icebergs tend to persist
                        stealth_score=0.6,
                        metadata={
                            'size_variance': size_variance,
                            'size_mean': size_mean,
                            'consistent_sizes': sizes[:5],
                            'side': side.value
                        }
                    )
                    
                    signals.append(signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Size pattern detection failed for {symbol}: {e}")
            return []
    
    async def _detect_refresh_pattern_liquidity(self, symbol: str, order_book: OrderBookSnapshot) -> Optional[List[LiquiditySignal]]:
        """Detect hidden liquidity through order refresh patterns"""
        try:
            signals = []
            
            # This would require historical order book data to detect refresh patterns
            # For now, return empty list as placeholder
            # In a real implementation, we would:
            # 1. Track order book changes over time
            # 2. Identify orders that get refreshed at the same price/size
            # 3. Calculate refresh timing patterns
            # 4. Detect iceberg-like behavior
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Refresh pattern detection failed for {symbol}: {e}")
            return []
    
    async def _detect_iceberg_orders(self, symbol: str, trade_data: Dict[str, Any]) -> Optional[List[IcebergOrderSignal]]:
        """Detect iceberg orders through trade analysis"""
        try:
            signals = []
            
            if len(self._trade_history[symbol]) < 10:
                return signals
            
            # Analyze recent trades for iceberg patterns
            recent_trades = list(self._trade_history[symbol])[-20:]
            
            # Group trades by price level
            price_groups = defaultdict(list)
            for trade in recent_trades:
                price_key = round(trade['price'], 2)  # Group by price to 2 decimals
                price_groups[price_key].append(trade)
            
            # Look for price levels with multiple similar-sized trades
            for price, trades in price_groups.items():
                if len(trades) < 3:  # Need at least 3 trades to detect pattern
                    continue
                
                sizes = [trade['size'] for trade in trades]
                size_mean = np.mean(sizes)
                size_std = np.std(sizes)
                
                # Check for consistent sizing (iceberg characteristic)
                if size_std < (size_mean * 0.2) and size_mean > 100:  # Low variance, reasonable size
                    # Calculate pattern scores
                    size_consistency = 1.0 - (size_std / size_mean) if size_mean > 0 else 0
                    refresh_pattern = min(1.0, len(trades) / 10.0)  # More trades = higher score
                    
                    # Calculate timing pattern
                    timestamps = [trade['timestamp'] for trade in trades]
                    time_diffs = [(timestamps[i+1] - timestamps[i]).total_seconds() 
                                 for i in range(len(timestamps)-1)]
                    timing_consistency = 1.0 - (np.std(time_diffs) / np.mean(time_diffs)) if time_diffs and np.mean(time_diffs) > 0 else 0
                    timing_consistency = max(0, min(1.0, timing_consistency))
                    
                    # Overall confidence
                    confidence = (size_consistency + refresh_pattern + timing_consistency) / 3
                    
                    if confidence > self.min_confidence_threshold:
                        signal = IcebergOrderSignal(
                            signal_id=f"iceberg_{symbol}_{price}_{int(time.time_ns())}",
                            symbol=symbol,
                            timestamp=datetime.now(),
                            price_level=price,
                            visible_size=size_mean,
                            estimated_total_size=size_mean * len(trades) * 2,  # Estimate
                            estimated_hidden_size=size_mean * len(trades),
                            refresh_pattern_score=refresh_pattern,
                            size_consistency_score=size_consistency,
                            timing_pattern_score=timing_consistency,
                            confidence=confidence,
                            metadata={
                                'trade_count': len(trades),
                                'size_std': size_std,
                                'time_diffs': time_diffs[:5],  # First 5 time differences
                                'total_volume': sum(sizes)
                            }
                        )
                        
                        signals.append(signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Iceberg detection failed for {symbol}: {e}")
            return []
    
    async def _detect_dark_pool_activity(self, symbol: str, trade_data: Dict[str, Any]) -> Optional[List[DarkPoolActivity]]:
        """Detect dark pool activity through trade analysis"""
        try:
            activities = []
            
            if len(self._trade_history[symbol]) < 50:
                return activities
            
            # Analyze recent trading activity
            recent_trades = list(self._trade_history[symbol])[-100:]
            total_volume = sum(trade['size'] for trade in recent_trades)
            
            if total_volume < self._config['dark_pool_min_volume']:
                return activities
            
            # Look for signs of dark pool activity
            # 1. Large block trades
            # 2. Trades at mid-price or with price improvement
            # 3. Unusual timing patterns
            
            large_trades = [trade for trade in recent_trades if trade['size'] > 1000]
            mid_price_trades = []
            
            # Estimate mid-price for each trade (simplified)
            for trade in recent_trades:
                # This would need order book data at trade time
                # For now, assume trades near round numbers might be mid-price
                if abs(trade['price'] - round(trade['price'], 1)) < 0.01:
                    mid_price_trades.append(trade)
            
            # Calculate dark pool indicators
            large_trade_ratio = len(large_trades) / len(recent_trades) if recent_trades else 0
            mid_price_ratio = len(mid_price_trades) / len(recent_trades) if recent_trades else 0
            
            # Estimate dark volume
            estimated_dark_volume = sum(trade['size'] for trade in large_trades)
            dark_volume_ratio = estimated_dark_volume / total_volume if total_volume > 0 else 0
            
            # If significant dark activity detected
            if dark_volume_ratio > 0.1 or large_trade_ratio > 0.2:
                confidence = min(0.9, (dark_volume_ratio + large_trade_ratio) / 2)
                
                activity = DarkPoolActivity(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    estimated_dark_volume=estimated_dark_volume,
                    dark_volume_ratio=dark_volume_ratio,
                    price_improvement=0.0,  # Would need more data to calculate
                    execution_quality=0.7,  # Placeholder
                    activity_concentration=large_trade_ratio,
                    detection_confidence=confidence,
                    volume_confidence=min(1.0, total_volume / 10000),
                    metadata={
                        'large_trades_count': len(large_trades),
                        'mid_price_trades_count': len(mid_price_trades),
                        'total_trades': len(recent_trades),
                        'total_volume': total_volume
                    }
                )
                
                activities.append(activity)
            
            return activities
            
        except Exception as e:
            self.logger.error(f"Dark pool detection failed for {symbol}: {e}")
            return []
    
    async def _detect_hidden_depth(self, symbol: str, order_book: OrderBookSnapshot) -> Optional[List[LiquiditySignal]]:
        """Detect hidden depth in order book"""
        try:
            signals = []
            
            # Look for signs of hidden depth
            # 1. Unusually thin order book for liquid symbols
            # 2. Large gaps between price levels
            # 3. Inconsistent depth patterns
            
            total_bid_depth = order_book.get_total_size(OrderBookSide.BID, 10)
            total_ask_depth = order_book.get_total_size(OrderBookSide.ASK, 10)
            total_depth = total_bid_depth + total_ask_depth
            
            # If depth seems unusually low, there might be hidden liquidity
            if total_depth < 10000:  # Threshold for "thin" book
                # Check for large price gaps
                bid_gaps = []
                ask_gaps = []
                
                if len(order_book.bids) > 1:
                    for i in range(len(order_book.bids) - 1):
                        gap = order_book.bids[i].price - order_book.bids[i+1].price
                        bid_gaps.append(gap)
                
                if len(order_book.asks) > 1:
                    for i in range(len(order_book.asks) - 1):
                        gap = order_book.asks[i+1].price - order_book.asks[i].price
                        ask_gaps.append(gap)
                
                # Large gaps might indicate hidden liquidity
                avg_bid_gap = np.mean(bid_gaps) if bid_gaps else 0
                avg_ask_gap = np.mean(ask_gaps) if ask_gaps else 0
                
                if order_book.spread and (avg_bid_gap > order_book.spread * 2 or avg_ask_gap > order_book.spread * 2):
                    confidence = 0.5 + min(0.4, (avg_bid_gap + avg_ask_gap) / (order_book.spread * 10))
                    
                    signal = LiquiditySignal(
                        signal_id=f"hidden_depth_{symbol}_{int(time.time_ns())}",
                        symbol=symbol,
                        timestamp=datetime.now(),
                        liquidity_type=LiquidityType.HIDDEN,
                        price_level=order_book.mid_price or 0,
                        estimated_size=total_depth * 2,  # Estimate hidden size
                        confidence=confidence,
                        detection_method="hidden_depth",
                        detection_confidence=confidence,
                        persistence_score=0.6,
                        stealth_score=0.8,  # High stealth for hidden depth
                        metadata={
                            'total_depth': total_depth,
                            'avg_bid_gap': avg_bid_gap,
                            'avg_ask_gap': avg_ask_gap,
                            'spread': order_book.spread
                        }
                    )
                    
                    signals.append(signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Hidden depth detection failed for {symbol}: {e}")
            return []   
 
    async def _process_detection_results(self, symbol: str, results: Union[List[LiquiditySignal], List[IcebergOrderSignal], List[DarkPoolActivity]]):
        """Process and store detection results"""
        try:
            if not results:
                return
            
            # Process different types of results
            for result in results:
                if isinstance(result, LiquiditySignal):
                    await self._process_liquidity_signal(symbol, result)
                elif isinstance(result, IcebergOrderSignal):
                    await self._process_iceberg_signal(symbol, result)
                elif isinstance(result, DarkPoolActivity):
                    await self._process_dark_pool_activity(symbol, result)
            
        except Exception as e:
            self.logger.error(f"Failed to process detection results for {symbol}: {e}")
    
    async def _process_liquidity_signal(self, symbol: str, signal: LiquiditySignal):
        """Process and store liquidity signal"""
        try:
            # Store signal
            self._liquidity_signals[symbol].append(signal)
            
            # Limit number of signals per symbol
            max_signals = self._config['max_signals_per_symbol']
            if len(self._liquidity_signals[symbol]) > max_signals:
                self._liquidity_signals[symbol] = self._liquidity_signals[symbol][-max_signals:]
            
            # Update metrics
            self._metrics['signals_detected'] += 1
            
            # Publish signal if confidence is high enough
            if signal.confidence >= self.min_confidence_threshold:
                await self._publish_liquidity_signal(symbol, signal)
            
            # Cache signal
            if self.cache_manager:
                await self.cache_manager.set(
                    f"liquidity:signal:{signal.signal_id}",
                    signal,
                    ttl=300
                )
            
        except Exception as e:
            self.logger.error(f"Failed to process liquidity signal: {e}")
    
    async def _process_iceberg_signal(self, symbol: str, signal: IcebergOrderSignal):
        """Process and store iceberg signal"""
        try:
            # Store signal
            self._iceberg_signals[symbol].append(signal)
            
            # Limit number of signals per symbol
            max_signals = self._config['max_signals_per_symbol']
            if len(self._iceberg_signals[symbol]) > max_signals:
                self._iceberg_signals[symbol] = self._iceberg_signals[symbol][-max_signals:]
            
            # Update metrics
            self._metrics['iceberg_orders_detected'] += 1
            
            # Publish signal if confidence is high enough
            if signal.confidence >= self.min_confidence_threshold:
                await self._publish_iceberg_signal(symbol, signal)
            
        except Exception as e:
            self.logger.error(f"Failed to process iceberg signal: {e}")
    
    async def _process_dark_pool_activity(self, symbol: str, activity: DarkPoolActivity):
        """Process and store dark pool activity"""
        try:
            # Store activity
            self._dark_pool_activity[symbol] = activity
            
            # Update metrics
            self._metrics['dark_pool_activities_detected'] += 1
            
            # Publish activity if confidence is high enough
            if activity.detection_confidence >= self.min_confidence_threshold:
                await self._publish_dark_pool_activity(symbol, activity)
            
        except Exception as e:
            self.logger.error(f"Failed to process dark pool activity: {e}")
    
    async def _publish_liquidity_signal(self, symbol: str, signal: LiquiditySignal):
        """Publish liquidity signal to message bus"""
        try:
            if not self.message_bus:
                return
            
            message = {
                'type': 'liquidity_signal',
                'signal_id': signal.signal_id,
                'symbol': symbol,
                'timestamp': signal.timestamp.isoformat(),
                'liquidity_type': signal.liquidity_type.value,
                'price_level': signal.price_level,
                'estimated_size': signal.estimated_size,
                'confidence': signal.confidence,
                'detection_method': signal.detection_method,
                'stealth_score': signal.stealth_score,
                'metadata': signal.metadata
            }
            
            await self.message_bus.publish(
                topic=f"liquidity.signals.{symbol}",
                message=message
            )
            
        except Exception as e:
            self.logger.error(f"Failed to publish liquidity signal: {e}")
    
    async def _publish_iceberg_signal(self, symbol: str, signal: IcebergOrderSignal):
        """Publish iceberg signal to message bus"""
        try:
            if not self.message_bus:
                return
            
            message = {
                'type': 'iceberg_signal',
                'signal_id': signal.signal_id,
                'symbol': symbol,
                'timestamp': signal.timestamp.isoformat(),
                'price_level': signal.price_level,
                'visible_size': signal.visible_size,
                'estimated_total_size': signal.estimated_total_size,
                'estimated_hidden_size': signal.estimated_hidden_size,
                'confidence': signal.confidence,
                'refresh_pattern_score': signal.refresh_pattern_score,
                'size_consistency_score': signal.size_consistency_score,
                'metadata': signal.metadata
            }
            
            await self.message_bus.publish(
                topic=f"liquidity.iceberg.{symbol}",
                message=message
            )
            
        except Exception as e:
            self.logger.error(f"Failed to publish iceberg signal: {e}")
    
    async def _publish_dark_pool_activity(self, symbol: str, activity: DarkPoolActivity):
        """Publish dark pool activity to message bus"""
        try:
            if not self.message_bus:
                return
            
            message = {
                'type': 'dark_pool_activity',
                'symbol': symbol,
                'timestamp': activity.timestamp.isoformat(),
                'estimated_dark_volume': activity.estimated_dark_volume,
                'dark_volume_ratio': activity.dark_volume_ratio,
                'detection_confidence': activity.detection_confidence,
                'activity_concentration': activity.activity_concentration,
                'venue_distribution': activity.venue_distribution,
                'metadata': activity.metadata
            }
            
            await self.message_bus.publish(
                topic=f"liquidity.darkpool.{symbol}",
                message=message
            )
            
        except Exception as e:
            self.logger.error(f"Failed to publish dark pool activity: {e}")
    
    async def _venue_scoring_task(self):
        """Background task for venue liquidity scoring"""
        while self._running:
            try:
                # Update venue scores periodically
                await self._update_venue_scores()
                
                # Wait for next update
                await asyncio.sleep(self._config['venue_score_update_interval'])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Venue scoring task error: {e}")
                await asyncio.sleep(30)
    
    async def _update_venue_scores(self):
        """Update venue liquidity scores"""
        try:
            # This would integrate with venue data feeds
            # For now, create sample venue scores
            
            sample_venues = [
                ("NYSE", VenueType.LIT_EXCHANGE),
                ("NASDAQ", VenueType.LIT_EXCHANGE),
                ("BATS", VenueType.ECN),
                ("IEX", VenueType.ECN),
                ("DARK_POOL_1", VenueType.DARK_POOL)
            ]
            
            for symbol in self._order_books.keys():
                for venue_name, venue_type in sample_venues:
                    # Create sample venue score
                    score = VenueLiquidityScore(
                        venue_name=venue_name,
                        venue_type=venue_type,
                        symbol=symbol,
                        timestamp=datetime.now(),
                        available_liquidity=np.random.uniform(10000, 100000),
                        average_spread=np.random.uniform(0.001, 0.01),
                        market_depth=np.random.uniform(5000, 50000),
                        fill_rate=np.random.uniform(0.7, 0.95),
                        price_improvement=np.random.uniform(0, 0.002),
                        execution_speed=np.random.uniform(1, 10),
                        reliability_score=np.random.uniform(0.8, 0.98),
                        explicit_costs=np.random.uniform(0.0001, 0.001),
                        implicit_costs=np.random.uniform(0.0005, 0.002)
                    )
                    
                    score.total_cost = score.explicit_costs + score.implicit_costs
                    score.calculate_overall_score()
                    
                    # Assign tier based on score
                    if score.overall_score >= 0.8:
                        score.liquidity_tier = LiquidityTier.TIER_1
                    elif score.overall_score >= 0.6:
                        score.liquidity_tier = LiquidityTier.TIER_2
                    elif score.overall_score >= 0.4:
                        score.liquidity_tier = LiquidityTier.TIER_3
                    elif score.overall_score >= 0.2:
                        score.liquidity_tier = LiquidityTier.TIER_4
                    else:
                        score.liquidity_tier = LiquidityTier.TIER_5
                    
                    # Store score
                    self._venue_scores[symbol][venue_name] = score
                    
                    # Update metrics
                    self._metrics['venue_scores_calculated'] += 1
            
        except Exception as e:
            self.logger.error(f"Failed to update venue scores: {e}")
    
    async def _metrics_tracker(self):
        """Track and update metrics"""
        while self._running:
            try:
                # Log metrics periodically
                if self._metrics['signals_detected'] % 50 == 0 and self._metrics['signals_detected'] > 0:
                    self.logger.info(
                        f"Liquidity Detection Metrics: "
                        f"Signals: {self._metrics['signals_detected']}, "
                        f"Icebergs: {self._metrics['iceberg_orders_detected']}, "
                        f"Dark pools: {self._metrics['dark_pool_activities_detected']}, "
                        f"Venue scores: {self._metrics['venue_scores_calculated']}, "
                        f"Avg detection time: {self._metrics['avg_detection_time_ms']:.2f}ms"
                    )
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Metrics tracking error: {e}")
                await asyncio.sleep(10)
    
    def _update_processing_metrics(self, processing_time_ms: float):
        """Update processing time metrics"""
        try:
            current_avg = self._metrics['avg_detection_time_ms']
            total_detections = (self._metrics['signals_detected'] + 
                              self._metrics['iceberg_orders_detected'] + 
                              self._metrics['dark_pool_activities_detected'])
            
            if total_detections > 0:
                self._metrics['avg_detection_time_ms'] = (
                    (current_avg * (total_detections - 1) + processing_time_ms) / total_detections
                )
            
        except Exception as e:
            self.logger.error(f"Failed to update processing metrics: {e}")
    
    # Public API methods
    
    async def get_liquidity_signals(self, symbol: str, limit: int = 10) -> List[LiquiditySignal]:
        """Get recent liquidity signals for symbol"""
        signals = self._liquidity_signals.get(symbol, [])
        return signals[-limit:] if signals else []
    
    async def get_iceberg_signals(self, symbol: str, limit: int = 10) -> List[IcebergOrderSignal]:
        """Get recent iceberg signals for symbol"""
        signals = self._iceberg_signals.get(symbol, [])
        return signals[-limit:] if signals else []
    
    async def get_dark_pool_activity(self, symbol: str) -> Optional[DarkPoolActivity]:
        """Get latest dark pool activity for symbol"""
        return self._dark_pool_activity.get(symbol)
    
    async def get_venue_scores(self, symbol: str) -> Dict[str, VenueLiquidityScore]:
        """Get venue liquidity scores for symbol"""
        return self._venue_scores.get(symbol, {})
    
    async def get_best_venues(self, symbol: str, limit: int = 5) -> List[VenueLiquidityScore]:
        """Get best venues for symbol by liquidity score"""
        venue_scores = self._venue_scores.get(symbol, {})
        sorted_venues = sorted(venue_scores.values(), key=lambda x: x.overall_score, reverse=True)
        return sorted_venues[:limit]
    
    async def get_hidden_liquidity_estimate(self, symbol: str) -> Dict[str, float]:
        """Get estimated hidden liquidity for symbol"""
        try:
            signals = self._liquidity_signals.get(symbol, [])
            
            # Aggregate estimates by liquidity type
            estimates = defaultdict(float)
            
            for signal in signals[-20:]:  # Recent signals only
                if signal.confidence >= self.min_confidence_threshold:
                    estimates[signal.liquidity_type.value] += signal.estimated_size
            
            # Add total estimate
            estimates['total'] = sum(estimates.values())
            
            return dict(estimates)
            
        except Exception as e:
            self.logger.error(f"Failed to get hidden liquidity estimate for {symbol}: {e}")
            return {}
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get engine metrics"""
        return self._metrics.copy()
    
    async def update_config(self, config_updates: Dict[str, Any]):
        """Update engine configuration"""
        try:
            for key, value in config_updates.items():
                if key in self._config:
                    self._config[key] = value
                    self.logger.info(f"Updated liquidity detection config {key} = {value}")
                else:
                    self.logger.warning(f"Unknown config key: {key}")
        except Exception as e:
            self.logger.error(f"Failed to update config: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return self._config.copy()
    
    async def analyze_liquidity_for_order(self, 
                                        symbol: str, 
                                        side: str, 
                                        size: float, 
                                        max_price_impact: float = 0.01) -> Dict[str, Any]:
        """Analyze available liquidity for a potential order"""
        try:
            analysis = {
                'symbol': symbol,
                'side': side,
                'requested_size': size,
                'max_price_impact': max_price_impact,
                'timestamp': datetime.now().isoformat(),
                'visible_liquidity': 0.0,
                'hidden_liquidity_estimate': 0.0,
                'total_liquidity_estimate': 0.0,
                'recommended_venues': [],
                'execution_strategy': 'market',
                'estimated_fill_rate': 0.0,
                'estimated_price_impact': 0.0
            }
            
            # Get current order book
            order_book = self._order_books.get(symbol)
            if not order_book:
                return analysis
            
            # Calculate visible liquidity
            book_side = OrderBookSide.ASK if side.lower() == 'buy' else OrderBookSide.BID
            visible_liquidity = order_book.get_total_size(book_side, 10)
            analysis['visible_liquidity'] = visible_liquidity
            
            # Get hidden liquidity estimates
            hidden_estimates = await self.get_hidden_liquidity_estimate(symbol)
            hidden_liquidity = hidden_estimates.get('total', 0.0)
            analysis['hidden_liquidity_estimate'] = hidden_liquidity
            analysis['total_liquidity_estimate'] = visible_liquidity + hidden_liquidity
            
            # Get best venues
            best_venues = await self.get_best_venues(symbol, 3)
            analysis['recommended_venues'] = [
                {
                    'venue': venue.venue_name,
                    'type': venue.venue_type.value,
                    'score': venue.overall_score,
                    'tier': venue.liquidity_tier.value
                }
                for venue in best_venues
            ]
            
            # Estimate fill rate and price impact
            if analysis['total_liquidity_estimate'] >= size:
                analysis['estimated_fill_rate'] = min(1.0, analysis['total_liquidity_estimate'] / size)
            else:
                analysis['estimated_fill_rate'] = analysis['total_liquidity_estimate'] / size
            
            # Simple price impact estimation
            if order_book.mid_price and visible_liquidity > 0:
                impact_ratio = size / visible_liquidity
                analysis['estimated_price_impact'] = min(max_price_impact, impact_ratio * 0.001)
            
            # Recommend execution strategy
            if size <= visible_liquidity * 0.1:
                analysis['execution_strategy'] = 'market'
            elif size <= analysis['total_liquidity_estimate'] * 0.5:
                analysis['execution_strategy'] = 'iceberg'
            else:
                analysis['execution_strategy'] = 'twap'
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Failed to analyze liquidity for order: {e}")
            return {'error': str(e)}