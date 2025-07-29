"""
Smart Order Router Implementation
Advanced order routing with venue selection, dark pool detection, and market impact estimation
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Tuple, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import threading
from concurrent.futures import ThreadPoolExecutor
import heapq

# Import core components
from ..core.messaging.message_bus import MessageBus
from ..core.caching.cache_manager import CacheManager
from ..ai.inference_engine import InferenceEngine, InferenceRequest, InferencePriority


class VenueType(Enum):
    """Types of trading venues"""
    EXCHANGE = "exchange"
    DARK_POOL = "dark_pool"
    ECN = "ecn"
    MARKET_MAKER = "market_maker"
    CROSSING_NETWORK = "crossing_network"
    RETAIL_WHOLESALER = "retail_wholesaler"


class OrderType(Enum):
    """Order types for routing"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    ICEBERG = "iceberg"
    HIDDEN = "hidden"
    PEGGED = "pegged"


class RoutingStrategy(Enum):
    """Order routing strategies"""
    BEST_PRICE = "best_price"
    LOWEST_COST = "lowest_cost"
    FASTEST_FILL = "fastest_fill"
    MINIMAL_IMPACT = "minimal_impact"
    DARK_FIRST = "dark_first"
    SMART_ROUTING = "smart_routing"
    LIQUIDITY_SEEKING = "liquidity_seeking"


@dataclass
class VenueInfo:
    """Information about a trading venue"""
    venue_id: str
    venue_name: str
    venue_type: VenueType
    
    # Connectivity and performance
    latency_ms: float = 0.0
    uptime_percentage: float = 99.9
    connection_status: str = "connected"
    
    # Cost structure
    maker_fee: float = 0.0
    taker_fee: float = 0.0
    rebate: float = 0.0
    
    # Liquidity metrics
    avg_spread_bps: float = 0.0
    avg_depth: float = 0.0
    fill_rate: float = 0.0
    
    # Market data
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    bid_size: Optional[float] = None
    ask_size: Optional[float] = None
    last_update: Optional[datetime] = None
    
    # Performance metrics
    avg_fill_time_ms: float = 0.0
    rejection_rate: float = 0.0
    partial_fill_rate: float = 0.0
    
    # Dark pool specific
    is_dark: bool = False
    hidden_liquidity_score: float = 0.0
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrderRequest:
    """Order routing request"""
    order_id: str
    symbol: str
    side: str  # "buy" or "sell"
    quantity: float
    order_type: OrderType
    
    # Price constraints
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    
    # Routing preferences
    routing_strategy: RoutingStrategy = RoutingStrategy.SMART_ROUTING
    max_venues: int = 5
    min_fill_size: float = 0.0
    max_participation_rate: float = 0.2
    
    # Time constraints
    time_in_force: str = "DAY"
    expire_time: Optional[datetime] = None
    
    # Execution preferences
    allow_dark_pools: bool = True
    allow_hidden_orders: bool = True
    minimize_market_impact: bool = True
    
    # Client information
    client_id: str = ""
    account_id: str = ""
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RoutingDecision:
    """Order routing decision"""
    order_id: str
    venue_allocations: List[Tuple[str, float, float]]  # (venue_id, quantity, price)
    routing_strategy: RoutingStrategy
    expected_cost: float
    expected_impact: float
    confidence: float
    
    # Timing
    decision_time: datetime = field(default_factory=datetime.now)
    expected_fill_time_ms: float = 0.0
    
    # Risk metrics
    execution_risk: float = 0.0
    liquidity_risk: float = 0.0
    
    # Reasoning
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VenuePerformance:
    """Venue performance tracking"""
    venue_id: str
    
    # Fill metrics
    total_orders: int = 0
    filled_orders: int = 0
    partially_filled: int = 0
    rejected_orders: int = 0
    
    # Timing metrics
    avg_fill_time_ms: float = 0.0
    avg_ack_time_ms: float = 0.0
    
    # Cost metrics
    avg_effective_spread: float = 0.0
    avg_implementation_shortfall: float = 0.0
    
    # Quality metrics
    price_improvement_rate: float = 0.0
    avg_price_improvement: float = 0.0
    
    # Recent performance (sliding window)
    recent_fill_rate: float = 0.0
    recent_avg_fill_time: float = 0.0
    recent_rejection_rate: float = 0.0
    
    # Last update
    last_updated: datetime = field(default_factory=datetime.now)


class SmartOrderRouter:
    """
    Advanced Smart Order Router with intelligent venue selection
    
    Features:
    - Multi-venue routing with cost optimization
    - Dark pool detection and routing
    - Market impact estimation and minimization
    - Real-time venue performance monitoring
    - ML-powered routing decisions
    - Liquidity detection and hidden order identification
    """
    
    def __init__(self,
                 message_bus: Optional[MessageBus] = None,
                 cache_manager: Optional[CacheManager] = None,
                 inference_engine: Optional[InferenceEngine] = None,
                 enable_ml_routing: bool = True,
                 max_concurrent_routes: int = 100,
                 performance_window_minutes: int = 60):
        
        self.message_bus = message_bus
        self.cache_manager = cache_manager
        self.inference_engine = inference_engine
        self.enable_ml_routing = enable_ml_routing
        self.max_concurrent_routes = max_concurrent_routes
        self.performance_window_minutes = performance_window_minutes
        
        # Venue management
        self._venues: Dict[str, VenueInfo] = {}
        self._venue_performance: Dict[str, VenuePerformance] = {}
        self._venue_connectivity: Dict[str, bool] = {}
        
        # Market data
        self._market_data: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._order_book_data: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # Routing engine
        self._routing_queue = asyncio.Queue(maxsize=1000)
        self._routing_tasks: List[asyncio.Task] = []
        self._running = False
        
        # Thread pool for CPU-intensive routing calculations
        self._thread_pool = ThreadPoolExecutor(
            max_workers=max_concurrent_routes,
            thread_name_prefix="order-routing"
        )
        
        # Performance tracking
        self._routing_metrics = {
            'total_routes': 0,
            'successful_routes': 0,
            'failed_routes': 0,
            'avg_routing_time_ms': 0.0,
            'ml_routing_decisions': 0,
            'dark_pool_routes': 0,
            'cost_savings_bps': 0.0
        }
        
        # Market impact models
        self._impact_models: Dict[str, Callable] = {
            'linear': self._linear_impact_model,
            'square_root': self._square_root_impact_model,
            'almgren_chriss': self._almgren_chriss_model
        }
        
        # Liquidity detection
        self._liquidity_detectors: Dict[str, Any] = {}
        self._hidden_liquidity_cache: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        # Routing strategies
        self._strategy_handlers = {
            RoutingStrategy.BEST_PRICE: self._route_best_price,
            RoutingStrategy.LOWEST_COST: self._route_lowest_cost,
            RoutingStrategy.FASTEST_FILL: self._route_fastest_fill,
            RoutingStrategy.MINIMAL_IMPACT: self._route_minimal_impact,
            RoutingStrategy.DARK_FIRST: self._route_dark_first,
            RoutingStrategy.SMART_ROUTING: self._route_smart,
            RoutingStrategy.LIQUIDITY_SEEKING: self._route_liquidity_seeking
        }
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start the smart order router"""
        if self._running:
            return
        
        self._running = True
        
        # Start routing workers
        for i in range(min(10, self.max_concurrent_routes)):
            task = asyncio.create_task(self._routing_worker(f"router-{i}"))
            self._routing_tasks.append(task)
        
        # Start venue monitoring
        asyncio.create_task(self._venue_monitor())
        
        # Start performance tracking
        asyncio.create_task(self._performance_tracker())
        
        # Initialize ML models if available
        if self.enable_ml_routing and self.inference_engine:
            await self._initialize_ml_models()
        
        self.logger.info("Smart Order Router started")
    
    async def stop(self):
        """Stop the smart order router"""
        self._running = False
        
        # Cancel routing tasks
        for task in self._routing_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._routing_tasks:
            await asyncio.gather(*self._routing_tasks, return_exceptions=True)
        
        # Shutdown thread pool
        self._thread_pool.shutdown(wait=True)
        
        self.logger.info("Smart Order Router stopped")
    
    async def route_order(self, order_request: OrderRequest) -> RoutingDecision:
        """Route an order using smart routing algorithms"""
        start_time = time.time_ns()
        
        try:
            # Validate order request
            if not self._validate_order_request(order_request):
                raise ValueError("Invalid order request")
            
            # Add to routing queue
            future = asyncio.Future()
            await self._routing_queue.put({
                'order_request': order_request,
                'future': future,
                'timestamp': time.time_ns()
            })
            
            # Wait for routing decision
            decision = await future
            
            # Update metrics
            routing_time_ms = (time.time_ns() - start_time) / 1_000_000
            self._routing_metrics['total_routes'] += 1
            self._routing_metrics['avg_routing_time_ms'] = (
                (self._routing_metrics['avg_routing_time_ms'] * 
                 (self._routing_metrics['total_routes'] - 1) + routing_time_ms) /
                self._routing_metrics['total_routes']
            )
            
            if decision:
                self._routing_metrics['successful_routes'] += 1
            else:
                self._routing_metrics['failed_routes'] += 1
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Order routing failed: {e}")
            self._routing_metrics['failed_routes'] += 1
            raise
    
    async def _routing_worker(self, worker_name: str):
        """Background worker for order routing"""
        self.logger.debug(f"Routing worker {worker_name} started")
        
        while self._running:
            try:
                # Get routing request from queue
                try:
                    request = await asyncio.wait_for(
                        self._routing_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process routing request
                decision = await self._process_routing_request(
                    request['order_request'], 
                    worker_name
                )
                
                # Set result
                request['future'].set_result(decision)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Routing worker {worker_name} error: {e}")
                if 'future' in locals() and not request['future'].done():
                    request['future'].set_exception(e)
                await asyncio.sleep(1)
        
        self.logger.debug(f"Routing worker {worker_name} stopped")
    
    async def _process_routing_request(self, 
                                     order_request: OrderRequest, 
                                     worker_name: str) -> RoutingDecision:
        """Process an order routing request"""
        try:
            # Get current market data
            market_data = await self._get_market_data(order_request.symbol)
            
            # Get available venues
            available_venues = await self._get_available_venues(order_request.symbol)
            
            # Filter venues based on order preferences
            filtered_venues = self._filter_venues(order_request, available_venues)
            
            # Calculate market impact
            impact_estimate = await self._estimate_market_impact(
                order_request, market_data
            )
            
            # Detect hidden liquidity
            hidden_liquidity = await self._detect_hidden_liquidity(
                order_request.symbol, filtered_venues
            )
            
            # Execute routing strategy
            strategy_handler = self._strategy_handlers.get(
                order_request.routing_strategy,
                self._route_smart
            )
            
            decision = await strategy_handler(
                order_request, 
                filtered_venues, 
                market_data, 
                impact_estimate,
                hidden_liquidity
            )
            
            # Enhance with ML if available
            if self.enable_ml_routing and self.inference_engine:
                decision = await self._enhance_with_ml(decision, order_request)
            
            # Validate routing decision
            if not self._validate_routing_decision(decision, order_request):
                raise ValueError("Invalid routing decision generated")
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Routing request processing failed: {e}")
            # Return fallback decision
            return self._create_fallback_decision(order_request)
    
    def _validate_order_request(self, order_request: OrderRequest) -> bool:
        """Validate order request"""
        try:
            # Basic validation
            if not order_request.order_id or not order_request.symbol:
                return False
            
            if order_request.quantity <= 0:
                return False
            
            if order_request.side not in ["buy", "sell"]:
                return False
            
            # Price validation for limit orders
            if order_request.order_type == OrderType.LIMIT:
                if order_request.limit_price is None or order_request.limit_price <= 0:
                    return False
            
            # Stop price validation
            if order_request.order_type in [OrderType.STOP, OrderType.STOP_LIMIT]:
                if order_request.stop_price is None or order_request.stop_price <= 0:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Order request validation failed: {e}")
            return False
    
    async def _get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get current market data for symbol"""
        try:
            # Check cache first
            if self.cache_manager:
                cached_data = await self.cache_manager.get(f"market_data:{symbol}")
                if cached_data:
                    return cached_data
            
            # Get from market data store
            market_data = self._market_data.get(symbol, {})
            
            # Add order book data
            order_book = self._order_book_data.get(symbol, {})
            market_data.update(order_book)
            
            # Cache the data
            if self.cache_manager:
                await self.cache_manager.set(
                    f"market_data:{symbol}", 
                    market_data, 
                    ttl=1  # 1 second TTL for market data
                )
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"Failed to get market data for {symbol}: {e}")
            return {}
    
    async def _get_available_venues(self, symbol: str) -> List[VenueInfo]:
        """Get available venues for symbol"""
        try:
            available_venues = []
            
            for venue_id, venue_info in self._venues.items():
                # Check connectivity
                if not self._venue_connectivity.get(venue_id, False):
                    continue
                
                # Check if venue supports the symbol
                if not self._venue_supports_symbol(venue_id, symbol):
                    continue
                
                # Update venue market data
                await self._update_venue_market_data(venue_info, symbol)
                
                available_venues.append(venue_info)
            
            return available_venues
            
        except Exception as e:
            self.logger.error(f"Failed to get available venues: {e}")
            return []
    
    def _filter_venues(self, 
                      order_request: OrderRequest, 
                      venues: List[VenueInfo]) -> List[VenueInfo]:
        """Filter venues based on order preferences"""
        try:
            filtered_venues = []
            
            for venue in venues:
                # Check dark pool preference
                if venue.is_dark and not order_request.allow_dark_pools:
                    continue
                
                # Check venue type restrictions
                # (Add any specific venue type filtering logic here)
                
                # Check minimum size requirements
                if (venue.metadata.get('min_order_size', 0) > 
                    order_request.quantity):
                    continue
                
                # Check maximum size limits
                if (venue.metadata.get('max_order_size', float('inf')) < 
                    order_request.quantity):
                    continue
                
                filtered_venues.append(venue)
            
            # Sort by preference (can be customized)
            filtered_venues.sort(
                key=lambda v: (
                    -v.fill_rate,  # Higher fill rate first
                    v.avg_fill_time_ms,  # Lower fill time first
                    v.taker_fee  # Lower fees first
                )
            )
            
            # Limit to max venues
            return filtered_venues[:order_request.max_venues]
            
        except Exception as e:
            self.logger.error(f"Venue filtering failed: {e}")
            return venues
    
    async def _estimate_market_impact(self, 
                                    order_request: OrderRequest, 
                                    market_data: Dict[str, Any]) -> Dict[str, float]:
        """Estimate market impact of the order"""
        try:
            # Get relevant market data
            bid_price = market_data.get('bid_price', 0.0)
            ask_price = market_data.get('ask_price', 0.0)
            bid_size = market_data.get('bid_size', 0.0)
            ask_size = market_data.get('ask_size', 0.0)
            avg_volume = market_data.get('avg_daily_volume', 1000000.0)
            volatility = market_data.get('volatility', 0.02)
            
            if bid_price <= 0 or ask_price <= 0:
                return {'temporary_impact': 0.0, 'permanent_impact': 0.0}
            
            mid_price = (bid_price + ask_price) / 2
            spread = ask_price - bid_price
            
            # Calculate participation rate
            participation_rate = min(
                order_request.quantity / avg_volume,
                order_request.max_participation_rate
            )
            
            # Use different impact models
            impact_estimates = {}
            
            for model_name, model_func in self._impact_models.items():
                impact = await model_func(
                    order_request.quantity,
                    mid_price,
                    spread,
                    volatility,
                    participation_rate,
                    order_request.side
                )
                impact_estimates[model_name] = impact
            
            # Use ensemble average
            temporary_impact = np.mean([
                est['temporary_impact'] 
                for est in impact_estimates.values()
            ])
            
            permanent_impact = np.mean([
                est['permanent_impact'] 
                for est in impact_estimates.values()
            ])
            
            return {
                'temporary_impact': temporary_impact,
                'permanent_impact': permanent_impact,
                'total_impact': temporary_impact + permanent_impact,
                'participation_rate': participation_rate,
                'model_estimates': impact_estimates
            }
            
        except Exception as e:
            self.logger.error(f"Market impact estimation failed: {e}")
            return {'temporary_impact': 0.0, 'permanent_impact': 0.0}
    
    async def _linear_impact_model(self, 
                                 quantity: float, 
                                 price: float, 
                                 spread: float, 
                                 volatility: float, 
                                 participation_rate: float, 
                                 side: str) -> Dict[str, float]:
        """Linear market impact model"""
        try:
            # Simple linear model: impact = alpha * participation_rate
            alpha = 0.1  # Impact coefficient
            
            temporary_impact = alpha * participation_rate * spread / 2
            permanent_impact = alpha * participation_rate * volatility * price * 0.1
            
            return {
                'temporary_impact': temporary_impact,
                'permanent_impact': permanent_impact
            }
            
        except Exception as e:
            self.logger.error(f"Linear impact model failed: {e}")
            return {'temporary_impact': 0.0, 'permanent_impact': 0.0}
    
    async def _square_root_impact_model(self, 
                                      quantity: float, 
                                      price: float, 
                                      spread: float, 
                                      volatility: float, 
                                      participation_rate: float, 
                                      side: str) -> Dict[str, float]:
        """Square root market impact model"""
        try:
            # Square root model: impact = alpha * sqrt(participation_rate)
            alpha = 0.05
            
            temporary_impact = alpha * np.sqrt(participation_rate) * spread / 2
            permanent_impact = alpha * np.sqrt(participation_rate) * volatility * price * 0.05
            
            return {
                'temporary_impact': temporary_impact,
                'permanent_impact': permanent_impact
            }
            
        except Exception as e:
            self.logger.error(f"Square root impact model failed: {e}")
            return {'temporary_impact': 0.0, 'permanent_impact': 0.0}
    
    async def _almgren_chriss_model(self, 
                                  quantity: float, 
                                  price: float, 
                                  spread: float, 
                                  volatility: float, 
                                  participation_rate: float, 
                                  side: str) -> Dict[str, float]:
        """Almgren-Chriss market impact model"""
        try:
            # Simplified Almgren-Chriss model
            eta = 2.5e-6  # Temporary impact parameter
            gamma = 2.5e-7  # Permanent impact parameter
            
            temporary_impact = eta * quantity * volatility
            permanent_impact = gamma * quantity * volatility
            
            return {
                'temporary_impact': temporary_impact,
                'permanent_impact': permanent_impact
            }
            
        except Exception as e:
            self.logger.error(f"Almgren-Chriss model failed: {e}")
            return {'temporary_impact': 0.0, 'permanent_impact': 0.0}  
  
    async def _detect_hidden_liquidity(self, 
                                     symbol: str, 
                                     venues: List[VenueInfo]) -> Dict[str, float]:
        """Detect hidden liquidity across venues"""
        try:
            hidden_liquidity = {}
            
            for venue in venues:
                if venue.is_dark:
                    # For dark pools, use historical patterns and ML
                    liquidity_score = await self._estimate_dark_pool_liquidity(
                        venue, symbol
                    )
                    hidden_liquidity[venue.venue_id] = liquidity_score
                else:
                    # For lit venues, detect iceberg orders
                    iceberg_liquidity = await self._detect_iceberg_orders(
                        venue, symbol
                    )
                    hidden_liquidity[venue.venue_id] = iceberg_liquidity
            
            return hidden_liquidity
            
        except Exception as e:
            self.logger.error(f"Hidden liquidity detection failed: {e}")
            return {}
    
    async def _estimate_dark_pool_liquidity(self, 
                                          venue: VenueInfo, 
                                          symbol: str) -> float:
        """Estimate liquidity in dark pool"""
        try:
            # Use historical fill rates and venue-specific patterns
            base_score = venue.hidden_liquidity_score
            
            # Adjust based on recent performance
            recent_performance = self._venue_performance.get(venue.venue_id)
            if recent_performance:
                fill_rate_adjustment = recent_performance.recent_fill_rate - 0.5
                base_score += fill_rate_adjustment * 0.2
            
            # Time-of-day adjustments
            current_hour = datetime.now().hour
            if 9 <= current_hour <= 16:  # Market hours
                base_score *= 1.2
            elif 16 <= current_hour <= 20:  # After hours
                base_score *= 0.8
            else:  # Overnight
                base_score *= 0.3
            
            return max(0.0, min(1.0, base_score))
            
        except Exception as e:
            self.logger.error(f"Dark pool liquidity estimation failed: {e}")
            return 0.0
    
    async def _detect_iceberg_orders(self, 
                                   venue: VenueInfo, 
                                   symbol: str) -> float:
        """Detect iceberg orders in lit venues"""
        try:
            # Analyze order book patterns for iceberg detection
            order_book = self._order_book_data.get(symbol, {})
            
            if not order_book:
                return 0.0
            
            # Look for repeated order sizes at same price levels
            bid_levels = order_book.get('bids', [])
            ask_levels = order_book.get('asks', [])
            
            iceberg_score = 0.0
            
            # Check for consistent order sizes (iceberg signature)
            for levels in [bid_levels, ask_levels]:
                if len(levels) >= 3:
                    sizes = [level[1] for level in levels[:5]]  # Top 5 levels
                    size_consistency = 1.0 - (np.std(sizes) / (np.mean(sizes) + 1e-10))
                    iceberg_score += size_consistency * 0.5
            
            return max(0.0, min(1.0, iceberg_score))
            
        except Exception as e:
            self.logger.error(f"Iceberg order detection failed: {e}")
            return 0.0
    
    # Routing Strategy Implementations
    
    async def _route_best_price(self, 
                              order_request: OrderRequest,
                              venues: List[VenueInfo],
                              market_data: Dict[str, Any],
                              impact_estimate: Dict[str, float],
                              hidden_liquidity: Dict[str, float]) -> RoutingDecision:
        """Route to venues with best prices"""
        try:
            venue_allocations = []
            
            # Sort venues by best price
            if order_request.side == "buy":
                # For buy orders, prefer lower ask prices
                sorted_venues = sorted(
                    venues, 
                    key=lambda v: v.ask_price or float('inf')
                )
            else:
                # For sell orders, prefer higher bid prices
                sorted_venues = sorted(
                    venues, 
                    key=lambda v: -(v.bid_price or 0.0)
                )
            
            remaining_quantity = order_request.quantity
            
            for venue in sorted_venues:
                if remaining_quantity <= 0:
                    break
                
                # Determine available liquidity
                if order_request.side == "buy":
                    available_size = venue.ask_size or 0.0
                    price = venue.ask_price or 0.0
                else:
                    available_size = venue.bid_size or 0.0
                    price = venue.bid_price or 0.0
                
                if price <= 0 or available_size <= 0:
                    continue
                
                # Add hidden liquidity estimate
                hidden_size = hidden_liquidity.get(venue.venue_id, 0.0) * available_size
                total_available = available_size + hidden_size
                
                # Allocate quantity
                allocated_quantity = min(remaining_quantity, total_available)
                
                if allocated_quantity >= order_request.min_fill_size:
                    venue_allocations.append((
                        venue.venue_id, 
                        allocated_quantity, 
                        price
                    ))
                    remaining_quantity -= allocated_quantity
            
            # Calculate expected cost
            expected_cost = sum(
                qty * price for _, qty, price in venue_allocations
            )
            
            return RoutingDecision(
                order_id=order_request.order_id,
                venue_allocations=venue_allocations,
                routing_strategy=RoutingStrategy.BEST_PRICE,
                expected_cost=expected_cost,
                expected_impact=impact_estimate.get('total_impact', 0.0),
                confidence=0.8,
                reasoning="Routed to venues with best available prices"
            )
            
        except Exception as e:
            self.logger.error(f"Best price routing failed: {e}")
            return self._create_fallback_decision(order_request)
    
    async def _route_lowest_cost(self, 
                               order_request: OrderRequest,
                               venues: List[VenueInfo],
                               market_data: Dict[str, Any],
                               impact_estimate: Dict[str, float],
                               hidden_liquidity: Dict[str, float]) -> RoutingDecision:
        """Route to minimize total execution cost"""
        try:
            venue_costs = []
            
            for venue in venues:
                # Calculate total cost including fees and impact
                if order_request.side == "buy":
                    price = venue.ask_price or 0.0
                    fee_rate = venue.taker_fee
                else:
                    price = venue.bid_price or 0.0
                    fee_rate = venue.taker_fee - venue.rebate  # Net fee after rebate
                
                if price <= 0:
                    continue
                
                # Calculate costs
                execution_cost = price * order_request.quantity
                fee_cost = execution_cost * fee_rate
                impact_cost = impact_estimate.get('total_impact', 0.0) * order_request.quantity
                
                total_cost = execution_cost + fee_cost + impact_cost
                
                venue_costs.append((venue, total_cost, price))
            
            # Sort by total cost
            venue_costs.sort(key=lambda x: x[1])
            
            # Allocate to lowest cost venues
            venue_allocations = []
            remaining_quantity = order_request.quantity
            
            for venue, cost, price in venue_costs:
                if remaining_quantity <= 0:
                    break
                
                # Determine available liquidity
                if order_request.side == "buy":
                    available_size = venue.ask_size or 0.0
                else:
                    available_size = venue.bid_size or 0.0
                
                # Add hidden liquidity
                hidden_size = hidden_liquidity.get(venue.venue_id, 0.0) * available_size
                total_available = available_size + hidden_size
                
                allocated_quantity = min(remaining_quantity, total_available)
                
                if allocated_quantity >= order_request.min_fill_size:
                    venue_allocations.append((
                        venue.venue_id, 
                        allocated_quantity, 
                        price
                    ))
                    remaining_quantity -= allocated_quantity
            
            expected_cost = sum(
                qty * price for _, qty, price in venue_allocations
            )
            
            return RoutingDecision(
                order_id=order_request.order_id,
                venue_allocations=venue_allocations,
                routing_strategy=RoutingStrategy.LOWEST_COST,
                expected_cost=expected_cost,
                expected_impact=impact_estimate.get('total_impact', 0.0),
                confidence=0.85,
                reasoning="Routed to minimize total execution cost including fees and impact"
            )
            
        except Exception as e:
            self.logger.error(f"Lowest cost routing failed: {e}")
            return self._create_fallback_decision(order_request)
    
    async def _route_fastest_fill(self, 
                                order_request: OrderRequest,
                                venues: List[VenueInfo],
                                market_data: Dict[str, Any],
                                impact_estimate: Dict[str, float],
                                hidden_liquidity: Dict[str, float]) -> RoutingDecision:
        """Route for fastest execution"""
        try:
            # Sort venues by fill speed and connectivity
            sorted_venues = sorted(
                venues,
                key=lambda v: (
                    v.avg_fill_time_ms,  # Faster fill time first
                    -v.fill_rate,  # Higher fill rate first
                    v.latency_ms  # Lower latency first
                )
            )
            
            venue_allocations = []
            remaining_quantity = order_request.quantity
            
            for venue in sorted_venues:
                if remaining_quantity <= 0:
                    break
                
                # Prioritize venues with good connectivity and performance
                if venue.connection_status != "connected":
                    continue
                
                if venue.rejection_rate > 0.1:  # Skip high rejection rate venues
                    continue
                
                # Determine price and available size
                if order_request.side == "buy":
                    price = venue.ask_price or 0.0
                    available_size = venue.ask_size or 0.0
                else:
                    price = venue.bid_price or 0.0
                    available_size = venue.bid_size or 0.0
                
                if price <= 0 or available_size <= 0:
                    continue
                
                # For fastest fill, use all available liquidity
                allocated_quantity = min(remaining_quantity, available_size)
                
                if allocated_quantity >= order_request.min_fill_size:
                    venue_allocations.append((
                        venue.venue_id, 
                        allocated_quantity, 
                        price
                    ))
                    remaining_quantity -= allocated_quantity
            
            expected_cost = sum(
                qty * price for _, qty, price in venue_allocations
            )
            
            # Calculate expected fill time
            expected_fill_time = 0.0
            if venue_allocations:
                fill_times = []
                for venue_id, qty, _ in venue_allocations:
                    venue = next(v for v in venues if v.venue_id == venue_id)
                    fill_times.append(venue.avg_fill_time_ms)
                expected_fill_time = max(fill_times)  # Parallel execution
            
            return RoutingDecision(
                order_id=order_request.order_id,
                venue_allocations=venue_allocations,
                routing_strategy=RoutingStrategy.FASTEST_FILL,
                expected_cost=expected_cost,
                expected_impact=impact_estimate.get('total_impact', 0.0),
                expected_fill_time_ms=expected_fill_time,
                confidence=0.75,
                reasoning="Routed to venues with fastest execution capabilities"
            )
            
        except Exception as e:
            self.logger.error(f"Fastest fill routing failed: {e}")
            return self._create_fallback_decision(order_request)
    
    async def _route_minimal_impact(self, 
                                  order_request: OrderRequest,
                                  venues: List[VenueInfo],
                                  market_data: Dict[str, Any],
                                  impact_estimate: Dict[str, float],
                                  hidden_liquidity: Dict[str, float]) -> RoutingDecision:
        """Route to minimize market impact"""
        try:
            # Calculate impact for each venue
            venue_impacts = []
            
            for venue in venues:
                # Estimate venue-specific impact
                venue_volume = venue.metadata.get('daily_volume', 1000000.0)
                venue_depth = venue.avg_depth
                
                # Impact is inversely related to venue size and depth
                impact_factor = order_request.quantity / (venue_volume * venue_depth + 1e-10)
                
                # Dark pools have lower impact
                if venue.is_dark:
                    impact_factor *= 0.5
                
                venue_impacts.append((venue, impact_factor))
            
            # Sort by lowest impact
            venue_impacts.sort(key=lambda x: x[1])
            
            # Allocate across multiple venues to spread impact
            venue_allocations = []
            remaining_quantity = order_request.quantity
            
            # Use more venues for large orders
            max_venues_to_use = min(
                len(venue_impacts),
                max(3, int(order_request.quantity / 10000))  # More venues for larger orders
            )
            
            for i, (venue, impact) in enumerate(venue_impacts[:max_venues_to_use]):
                if remaining_quantity <= 0:
                    break
                
                # Determine available liquidity
                if order_request.side == "buy":
                    price = venue.ask_price or 0.0
                    available_size = venue.ask_size or 0.0
                else:
                    price = venue.bid_price or 0.0
                    available_size = venue.bid_size or 0.0
                
                if price <= 0:
                    continue
                
                # Add hidden liquidity
                hidden_size = hidden_liquidity.get(venue.venue_id, 0.0) * available_size
                total_available = available_size + hidden_size
                
                # Allocate proportionally, but respect venue limits
                if i == max_venues_to_use - 1:  # Last venue gets remainder
                    allocated_quantity = remaining_quantity
                else:
                    # Allocate based on venue capacity and impact
                    allocation_ratio = 1.0 / (impact + 1e-10)
                    total_ratio = sum(1.0 / (imp + 1e-10) for _, imp in venue_impacts[:max_venues_to_use])
                    target_allocation = order_request.quantity * (allocation_ratio / total_ratio)
                    allocated_quantity = min(target_allocation, total_available, remaining_quantity)
                
                if allocated_quantity >= order_request.min_fill_size:
                    venue_allocations.append((
                        venue.venue_id, 
                        allocated_quantity, 
                        price
                    ))
                    remaining_quantity -= allocated_quantity
            
            expected_cost = sum(
                qty * price for _, qty, price in venue_allocations
            )
            
            # Calculate reduced impact due to spreading
            impact_reduction = min(0.5, len(venue_allocations) * 0.1)
            adjusted_impact = impact_estimate.get('total_impact', 0.0) * (1 - impact_reduction)
            
            return RoutingDecision(
                order_id=order_request.order_id,
                venue_allocations=venue_allocations,
                routing_strategy=RoutingStrategy.MINIMAL_IMPACT,
                expected_cost=expected_cost,
                expected_impact=adjusted_impact,
                confidence=0.9,
                reasoning=f"Spread across {len(venue_allocations)} venues to minimize market impact"
            )
            
        except Exception as e:
            self.logger.error(f"Minimal impact routing failed: {e}")
            return self._create_fallback_decision(order_request)
    
    async def _route_dark_first(self, 
                              order_request: OrderRequest,
                              venues: List[VenueInfo],
                              market_data: Dict[str, Any],
                              impact_estimate: Dict[str, float],
                              hidden_liquidity: Dict[str, float]) -> RoutingDecision:
        """Route to dark pools first, then lit venues"""
        try:
            # Separate dark and lit venues
            dark_venues = [v for v in venues if v.is_dark]
            lit_venues = [v for v in venues if not v.is_dark]
            
            # Sort dark venues by liquidity score
            dark_venues.sort(key=lambda v: -v.hidden_liquidity_score)
            
            # Sort lit venues by best price
            if order_request.side == "buy":
                lit_venues.sort(key=lambda v: v.ask_price or float('inf'))
            else:
                lit_venues.sort(key=lambda v: -(v.bid_price or 0.0))
            
            venue_allocations = []
            remaining_quantity = order_request.quantity
            
            # First, try dark venues
            for venue in dark_venues:
                if remaining_quantity <= 0:
                    break
                
                # Estimate dark pool liquidity
                liquidity_estimate = hidden_liquidity.get(venue.venue_id, 0.0)
                
                if liquidity_estimate < 0.3:  # Skip low liquidity dark pools
                    continue
                
                # Determine price (use mid-price for dark pools)
                bid_price = market_data.get('bid_price', 0.0)
                ask_price = market_data.get('ask_price', 0.0)
                
                if bid_price <= 0 or ask_price <= 0:
                    continue
                
                mid_price = (bid_price + ask_price) / 2
                
                # Estimate available size based on liquidity score
                estimated_size = liquidity_estimate * remaining_quantity * 0.5
                allocated_quantity = min(remaining_quantity, estimated_size)
                
                if allocated_quantity >= order_request.min_fill_size:
                    venue_allocations.append((
                        venue.venue_id, 
                        allocated_quantity, 
                        mid_price
                    ))
                    remaining_quantity -= allocated_quantity
            
            # Then, use lit venues for remainder
            for venue in lit_venues:
                if remaining_quantity <= 0:
                    break
                
                if order_request.side == "buy":
                    price = venue.ask_price or 0.0
                    available_size = venue.ask_size or 0.0
                else:
                    price = venue.bid_price or 0.0
                    available_size = venue.bid_size or 0.0
                
                if price <= 0 or available_size <= 0:
                    continue
                
                allocated_quantity = min(remaining_quantity, available_size)
                
                if allocated_quantity >= order_request.min_fill_size:
                    venue_allocations.append((
                        venue.venue_id, 
                        allocated_quantity, 
                        price
                    ))
                    remaining_quantity -= allocated_quantity
            
            expected_cost = sum(
                qty * price for _, qty, price in venue_allocations
            )
            
            # Dark-first routing typically reduces impact
            impact_reduction = 0.3 if any(v.is_dark for v in venues 
                                        if v.venue_id in [va[0] for va in venue_allocations]) else 0.0
            adjusted_impact = impact_estimate.get('total_impact', 0.0) * (1 - impact_reduction)
            
            return RoutingDecision(
                order_id=order_request.order_id,
                venue_allocations=venue_allocations,
                routing_strategy=RoutingStrategy.DARK_FIRST,
                expected_cost=expected_cost,
                expected_impact=adjusted_impact,
                confidence=0.8,
                reasoning="Prioritized dark pools to minimize market impact and information leakage"
            )
            
        except Exception as e:
            self.logger.error(f"Dark first routing failed: {e}")
            return self._create_fallback_decision(order_request)
    
    async def _route_smart(self, 
                         order_request: OrderRequest,
                         venues: List[VenueInfo],
                         market_data: Dict[str, Any],
                         impact_estimate: Dict[str, float],
                         hidden_liquidity: Dict[str, float]) -> RoutingDecision:
        """Smart routing using multiple factors"""
        try:
            # Calculate composite scores for each venue
            venue_scores = []
            
            for venue in venues:
                score = await self._calculate_venue_score(
                    venue, order_request, market_data, 
                    impact_estimate, hidden_liquidity
                )
                venue_scores.append((venue, score))
            
            # Sort by composite score
            venue_scores.sort(key=lambda x: -x[1])
            
            # Allocate using smart algorithm
            venue_allocations = []
            remaining_quantity = order_request.quantity
            
            # Use top venues based on order size
            num_venues = min(
                len(venue_scores),
                max(1, min(5, int(order_request.quantity / 5000)))
            )
            
            total_score = sum(score for _, score in venue_scores[:num_venues])
            
            for i, (venue, score) in enumerate(venue_scores[:num_venues]):
                if remaining_quantity <= 0:
                    break
                
                # Determine available liquidity
                if order_request.side == "buy":
                    price = venue.ask_price or 0.0
                    available_size = venue.ask_size or 0.0
                else:
                    price = venue.bid_price or 0.0
                    available_size = venue.bid_size or 0.0
                
                if price <= 0:
                    continue
                
                # Add hidden liquidity
                hidden_size = hidden_liquidity.get(venue.venue_id, 0.0) * available_size
                total_available = available_size + hidden_size
                
                # Allocate proportionally to score
                if i == num_venues - 1:  # Last venue gets remainder
                    allocated_quantity = remaining_quantity
                else:
                    target_allocation = order_request.quantity * (score / total_score)
                    allocated_quantity = min(target_allocation, total_available, remaining_quantity)
                
                if allocated_quantity >= order_request.min_fill_size:
                    venue_allocations.append((
                        venue.venue_id, 
                        allocated_quantity, 
                        price
                    ))
                    remaining_quantity -= allocated_quantity
            
            expected_cost = sum(
                qty * price for _, qty, price in venue_allocations
            )
            
            return RoutingDecision(
                order_id=order_request.order_id,
                venue_allocations=venue_allocations,
                routing_strategy=RoutingStrategy.SMART_ROUTING,
                expected_cost=expected_cost,
                expected_impact=impact_estimate.get('total_impact', 0.0),
                confidence=0.95,
                reasoning="Smart routing using composite venue scoring algorithm"
            )
            
        except Exception as e:
            self.logger.error(f"Smart routing failed: {e}")
            return self._create_fallback_decision(order_request)
    
    async def _route_liquidity_seeking(self, 
                                     order_request: OrderRequest,
                                     venues: List[VenueInfo],
                                     market_data: Dict[str, Any],
                                     impact_estimate: Dict[str, float],
                                     hidden_liquidity: Dict[str, float]) -> RoutingDecision:
        """Route to venues with highest liquidity"""
        try:
            # Calculate liquidity scores
            venue_liquidity = []
            
            for venue in venues:
                # Base liquidity from order book
                if order_request.side == "buy":
                    base_liquidity = venue.ask_size or 0.0
                else:
                    base_liquidity = venue.bid_size or 0.0
                
                # Add hidden liquidity
                hidden_size = hidden_liquidity.get(venue.venue_id, 0.0) * base_liquidity
                total_liquidity = base_liquidity + hidden_size
                
                # Adjust for venue depth and volume
                depth_factor = venue.avg_depth
                volume_factor = venue.metadata.get('daily_volume', 1000000.0) / 1000000.0
                
                liquidity_score = total_liquidity * depth_factor * volume_factor
                
                venue_liquidity.append((venue, liquidity_score, total_liquidity))
            
            # Sort by liquidity score
            venue_liquidity.sort(key=lambda x: -x[1])
            
            # Allocate to highest liquidity venues
            venue_allocations = []
            remaining_quantity = order_request.quantity
            
            for venue, liquidity_score, available_liquidity in venue_liquidity:
                if remaining_quantity <= 0:
                    break
                
                if available_liquidity < order_request.min_fill_size:
                    continue
                
                # Determine price
                if order_request.side == "buy":
                    price = venue.ask_price or 0.0
                else:
                    price = venue.bid_price or 0.0
                
                if price <= 0:
                    continue
                
                allocated_quantity = min(remaining_quantity, available_liquidity)
                
                venue_allocations.append((
                    venue.venue_id, 
                    allocated_quantity, 
                    price
                ))
                remaining_quantity -= allocated_quantity
            
            expected_cost = sum(
                qty * price for _, qty, price in venue_allocations
            )
            
            return RoutingDecision(
                order_id=order_request.order_id,
                venue_allocations=venue_allocations,
                routing_strategy=RoutingStrategy.LIQUIDITY_SEEKING,
                expected_cost=expected_cost,
                expected_impact=impact_estimate.get('total_impact', 0.0),
                confidence=0.85,
                reasoning="Routed to venues with highest available liquidity"
            )
            
        except Exception as e:
            self.logger.error(f"Liquidity seeking routing failed: {e}")
            return self._create_fallback_decision(order_request)
    
    async def _calculate_venue_score(self, 
                                   venue: VenueInfo,
                                   order_request: OrderRequest,
                                   market_data: Dict[str, Any],
                                   impact_estimate: Dict[str, float],
                                   hidden_liquidity: Dict[str, float]) -> float:
        """Calculate composite score for venue"""
        try:
            score = 0.0
            
            # Price competitiveness (30% weight)
            price_score = self._calculate_price_score(venue, order_request, market_data)
            score += price_score * 0.3
            
            # Liquidity availability (25% weight)
            liquidity_score = self._calculate_liquidity_score(venue, order_request, hidden_liquidity)
            score += liquidity_score * 0.25
            
            # Execution quality (20% weight)
            quality_score = self._calculate_quality_score(venue)
            score += quality_score * 0.2
            
            # Cost efficiency (15% weight)
            cost_score = self._calculate_cost_score(venue, order_request)
            score += cost_score * 0.15
            
            # Speed and reliability (10% weight)
            speed_score = self._calculate_speed_score(venue)
            score += speed_score * 0.1
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            self.logger.error(f"Venue score calculation failed: {e}")
            return 0.0
    
    def _calculate_price_score(self, 
                              venue: VenueInfo, 
                              order_request: OrderRequest, 
                              market_data: Dict[str, Any]) -> float:
        """Calculate price competitiveness score"""
        try:
            if order_request.side == "buy":
                venue_price = venue.ask_price or float('inf')
                best_price = market_data.get('best_ask', venue_price)
            else:
                venue_price = venue.bid_price or 0.0
                best_price = market_data.get('best_bid', venue_price)
            
            if best_price <= 0 or venue_price <= 0:
                return 0.0
            
            if order_request.side == "buy":
                # Lower ask price is better
                score = best_price / venue_price if venue_price > 0 else 0.0
            else:
                # Higher bid price is better
                score = venue_price / best_price if best_price > 0 else 0.0
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            self.logger.error(f"Price score calculation failed: {e}")
            return 0.0
    
    def _calculate_liquidity_score(self, 
                                  venue: VenueInfo, 
                                  order_request: OrderRequest, 
                                  hidden_liquidity: Dict[str, float]) -> float:
        """Calculate liquidity availability score"""
        try:
            if order_request.side == "buy":
                base_size = venue.ask_size or 0.0
            else:
                base_size = venue.bid_size or 0.0
            
            # Add hidden liquidity
            hidden_size = hidden_liquidity.get(venue.venue_id, 0.0) * base_size
            total_size = base_size + hidden_size
            
            # Score based on how much of the order can be filled
            if order_request.quantity <= 0:
                return 0.0
            
            fill_ratio = min(1.0, total_size / order_request.quantity)
            
            # Bonus for venues that can fill the entire order
            if fill_ratio >= 1.0:
                fill_ratio = 1.2
            
            return max(0.0, min(1.0, fill_ratio))
            
        except Exception as e:
            self.logger.error(f"Liquidity score calculation failed: {e}")
            return 0.0
    
    def _calculate_quality_score(self, venue: VenueInfo) -> float:
        """Calculate execution quality score"""
        try:
            # Base score from fill rate
            quality_score = venue.fill_rate
            
            # Adjust for rejection rate
            quality_score *= (1.0 - venue.rejection_rate)
            
            # Adjust for partial fill rate (prefer complete fills)
            quality_score *= (1.0 - venue.partial_fill_rate * 0.5)
            
            # Get recent performance
            performance = self._venue_performance.get(venue.venue_id)
            if performance:
                # Weight recent performance more heavily
                recent_quality = performance.recent_fill_rate * (1.0 - performance.recent_rejection_rate)
                quality_score = quality_score * 0.3 + recent_quality * 0.7
            
            return max(0.0, min(1.0, quality_score))
            
        except Exception as e:
            self.logger.error(f"Quality score calculation failed: {e}")
            return 0.0
    
    def _calculate_cost_score(self, venue: VenueInfo, order_request: OrderRequest) -> float:
        """Calculate cost efficiency score"""
        try:
            # Calculate net fee (fee - rebate)
            net_fee = venue.taker_fee - venue.rebate
            
            # Normalize fee (assume typical range 0-0.003 or 30 bps)
            max_fee = 0.003
            fee_score = max(0.0, 1.0 - (net_fee / max_fee))
            
            # Adjust for spread cost
            if venue.avg_spread_bps > 0:
                spread_score = max(0.0, 1.0 - (venue.avg_spread_bps / 50.0))  # Normalize to 50 bps
                cost_score = (fee_score + spread_score) / 2
            else:
                cost_score = fee_score
            
            return max(0.0, min(1.0, cost_score))
            
        except Exception as e:
            self.logger.error(f"Cost score calculation failed: {e}")
            return 0.0
    
    def _calculate_speed_score(self, venue: VenueInfo) -> float:
        """Calculate speed and reliability score"""
        try:
            # Speed score (lower latency and fill time is better)
            max_latency = 10.0  # 10ms max
            max_fill_time = 1000.0  # 1 second max
            
            latency_score = max(0.0, 1.0 - (venue.latency_ms / max_latency))
            fill_time_score = max(0.0, 1.0 - (venue.avg_fill_time_ms / max_fill_time))
            
            # Reliability score
            uptime_score = venue.uptime_percentage / 100.0
            connection_score = 1.0 if venue.connection_status == "connected" else 0.0
            
            # Combine scores
            speed_score = (latency_score + fill_time_score) / 2
            reliability_score = (uptime_score + connection_score) / 2
            
            return (speed_score + reliability_score) / 2
            
        except Exception as e:
            self.logger.error(f"Speed score calculation failed: {e}")
            return 0.0    

    # ML Enhancement and Utility Methods
    
    async def _enhance_with_ml(self, 
                             decision: RoutingDecision, 
                             order_request: OrderRequest) -> RoutingDecision:
        """Enhance routing decision with ML predictions"""
        try:
            if not self.inference_engine:
                return decision
            
            # Prepare features for ML model
            features = await self._prepare_routing_features(decision, order_request)
            
            # Make ML prediction
            request = InferenceRequest(
                request_id=f"routing_{order_request.order_id}_{int(time.time_ns())}",
                model_id="smart_routing_model",
                input_data=features,
                priority=InferencePriority.HIGH,
                timeout_ms=50.0,  # Fast inference for routing
                use_cache=True
            )
            
            response = await self.inference_engine.predict(request)
            
            if response.status.value == 'completed':
                # Interpret ML prediction
                ml_decision = await self._interpret_ml_routing_prediction(
                    response, decision, order_request
                )
                
                if ml_decision:
                    self._routing_metrics['ml_routing_decisions'] += 1
                    return ml_decision
            
            return decision
            
        except Exception as e:
            self.logger.error(f"ML enhancement failed: {e}")
            return decision
    
    async def _prepare_routing_features(self, 
                                      decision: RoutingDecision, 
                                      order_request: OrderRequest) -> np.ndarray:
        """Prepare features for ML routing model"""
        try:
            features = []
            
            # Order characteristics
            features.extend([
                order_request.quantity,
                1.0 if order_request.side == "buy" else 0.0,
                order_request.order_type.value.__hash__() % 10,  # Simplified encoding
                order_request.max_participation_rate,
                1.0 if order_request.allow_dark_pools else 0.0,
                1.0 if order_request.minimize_market_impact else 0.0
            ])
            
            # Market conditions
            market_data = await self._get_market_data(order_request.symbol)
            bid_price = market_data.get('bid_price', 0.0)
            ask_price = market_data.get('ask_price', 0.0)
            
            if bid_price > 0 and ask_price > 0:
                spread = ask_price - bid_price
                mid_price = (bid_price + ask_price) / 2
                spread_bps = (spread / mid_price) * 10000
                features.extend([spread_bps, mid_price])
            else:
                features.extend([0.0, 0.0])
            
            # Venue characteristics
            num_venues = len(decision.venue_allocations)
            features.append(num_venues)
            
            # Add venue-specific features (top 3 venues)
            for i in range(3):
                if i < len(decision.venue_allocations):
                    venue_id, qty, price = decision.venue_allocations[i]
                    venue = self._venues.get(venue_id)
                    if venue:
                        features.extend([
                            qty / order_request.quantity,  # Allocation ratio
                            venue.fill_rate,
                            venue.avg_fill_time_ms,
                            venue.taker_fee,
                            1.0 if venue.is_dark else 0.0
                        ])
                    else:
                        features.extend([0.0, 0.0, 0.0, 0.0, 0.0])
                else:
                    features.extend([0.0, 0.0, 0.0, 0.0, 0.0])
            
            # Time features
            current_hour = datetime.now().hour
            features.extend([
                current_hour / 24.0,  # Normalized hour
                1.0 if 9 <= current_hour <= 16 else 0.0,  # Market hours
                datetime.now().weekday() / 7.0  # Day of week
            ])
            
            # Pad or truncate to fixed size
            target_size = 50
            if len(features) < target_size:
                features.extend([0.0] * (target_size - len(features)))
            else:
                features = features[:target_size]
            
            return np.array(features).reshape(1, -1)
            
        except Exception as e:
            self.logger.error(f"Feature preparation failed: {e}")
            return np.zeros((1, 50))
    
    async def _interpret_ml_routing_prediction(self, 
                                             response, 
                                             original_decision: RoutingDecision, 
                                             order_request: OrderRequest) -> Optional[RoutingDecision]:
        """Interpret ML model prediction for routing"""
        try:
            prediction = response.prediction
            confidence = response.confidence or 0.0
            
            # If ML confidence is low, stick with original decision
            if confidence < 0.7:
                return original_decision
            
            # Interpret prediction (assuming it suggests venue allocation adjustments)
            if isinstance(prediction, (list, np.ndarray)) and len(prediction) >= 2:
                # Prediction format: [quality_score, cost_adjustment, speed_preference, ...]
                quality_score = prediction[0]
                cost_adjustment = prediction[1] if len(prediction) > 1 else 0.0
                speed_preference = prediction[2] if len(prediction) > 2 else 0.0
                
                # Adjust original decision based on ML insights
                enhanced_decision = RoutingDecision(
                    order_id=original_decision.order_id,
                    venue_allocations=original_decision.venue_allocations,
                    routing_strategy=original_decision.routing_strategy,
                    expected_cost=original_decision.expected_cost * (1 + cost_adjustment * 0.1),
                    expected_impact=original_decision.expected_impact,
                    confidence=min(1.0, original_decision.confidence * quality_score),
                    expected_fill_time_ms=original_decision.expected_fill_time_ms * (1 - speed_preference * 0.2),
                    reasoning=f"{original_decision.reasoning} (ML-enhanced with {confidence:.2f} confidence)",
                    metadata={
                        **original_decision.metadata,
                        'ml_enhanced': True,
                        'ml_confidence': confidence,
                        'ml_quality_score': quality_score
                    }
                )
                
                return enhanced_decision
            
            return original_decision
            
        except Exception as e:
            self.logger.error(f"ML prediction interpretation failed: {e}")
            return original_decision
    
    def _create_fallback_decision(self, order_request: OrderRequest) -> RoutingDecision:
        """Create fallback routing decision"""
        try:
            # Simple fallback: route to first available venue
            available_venues = [v for v in self._venues.values() 
                              if self._venue_connectivity.get(v.venue_id, False)]
            
            if not available_venues:
                # No venues available
                return RoutingDecision(
                    order_id=order_request.order_id,
                    venue_allocations=[],
                    routing_strategy=order_request.routing_strategy,
                    expected_cost=0.0,
                    expected_impact=0.0,
                    confidence=0.0,
                    reasoning="No venues available for routing"
                )
            
            # Use first available venue
            venue = available_venues[0]
            
            # Estimate price
            if order_request.side == "buy":
                price = venue.ask_price or 100.0  # Fallback price
            else:
                price = venue.bid_price or 100.0
            
            return RoutingDecision(
                order_id=order_request.order_id,
                venue_allocations=[(venue.venue_id, order_request.quantity, price)],
                routing_strategy=order_request.routing_strategy,
                expected_cost=order_request.quantity * price,
                expected_impact=0.01,  # Assume 1% impact
                confidence=0.5,
                reasoning="Fallback routing to first available venue"
            )
            
        except Exception as e:
            self.logger.error(f"Fallback decision creation failed: {e}")
            return RoutingDecision(
                order_id=order_request.order_id,
                venue_allocations=[],
                routing_strategy=order_request.routing_strategy,
                expected_cost=0.0,
                expected_impact=0.0,
                confidence=0.0,
                reasoning="Fallback routing failed"
            )
    
    def _validate_routing_decision(self, 
                                 decision: RoutingDecision, 
                                 order_request: OrderRequest) -> bool:
        """Validate routing decision"""
        try:
            # Check if decision has allocations
            if not decision.venue_allocations:
                return False
            
            # Check total allocated quantity
            total_allocated = sum(qty for _, qty, _ in decision.venue_allocations)
            if abs(total_allocated - order_request.quantity) > 0.01:  # Allow small rounding errors
                return False
            
            # Check venue existence
            for venue_id, qty, price in decision.venue_allocations:
                if venue_id not in self._venues:
                    return False
                if qty <= 0 or price <= 0:
                    return False
            
            # Check confidence bounds
            if decision.confidence < 0 or decision.confidence > 1:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Routing decision validation failed: {e}")
            return False
    
    # Venue Management and Monitoring
    
    async def add_venue(self, venue_info: VenueInfo):
        """Add a new trading venue"""
        try:
            self._venues[venue_info.venue_id] = venue_info
            self._venue_connectivity[venue_info.venue_id] = True
            
            # Initialize performance tracking
            self._venue_performance[venue_info.venue_id] = VenuePerformance(
                venue_id=venue_info.venue_id
            )
            
            self.logger.info(f"Added venue: {venue_info.venue_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to add venue {venue_info.venue_id}: {e}")
    
    async def remove_venue(self, venue_id: str):
        """Remove a trading venue"""
        try:
            if venue_id in self._venues:
                del self._venues[venue_id]
            
            if venue_id in self._venue_connectivity:
                del self._venue_connectivity[venue_id]
            
            if venue_id in self._venue_performance:
                del self._venue_performance[venue_id]
            
            self.logger.info(f"Removed venue: {venue_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to remove venue {venue_id}: {e}")
    
    async def update_venue_market_data(self, venue_id: str, symbol: str, market_data: Dict[str, Any]):
        """Update venue market data"""
        try:
            if venue_id in self._venues:
                venue = self._venues[venue_id]
                venue.bid_price = market_data.get('bid_price')
                venue.ask_price = market_data.get('ask_price')
                venue.bid_size = market_data.get('bid_size')
                venue.ask_size = market_data.get('ask_size')
                venue.last_update = datetime.now()
                
        except Exception as e:
            self.logger.error(f"Failed to update venue market data: {e}")
    
    async def _update_venue_market_data(self, venue: VenueInfo, symbol: str):
        """Update venue market data from internal sources"""
        try:
            # This would typically fetch from market data feeds
            # For now, use cached data or defaults
            pass
            
        except Exception as e:
            self.logger.error(f"Failed to update venue market data: {e}")
    
    def _venue_supports_symbol(self, venue_id: str, symbol: str) -> bool:
        """Check if venue supports trading the symbol"""
        try:
            venue = self._venues.get(venue_id)
            if not venue:
                return False
            
            # Check venue metadata for supported symbols
            supported_symbols = venue.metadata.get('supported_symbols', [])
            if supported_symbols and symbol not in supported_symbols:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Symbol support check failed: {e}")
            return False
    
    async def _venue_monitor(self):
        """Monitor venue connectivity and performance"""
        while self._running:
            try:
                for venue_id, venue in self._venues.items():
                    # Check connectivity (simplified)
                    # In practice, this would ping the venue or check heartbeats
                    if venue.connection_status == "connected":
                        self._venue_connectivity[venue_id] = True
                    else:
                        self._venue_connectivity[venue_id] = False
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Venue monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def _performance_tracker(self):
        """Track venue performance metrics"""
        while self._running:
            try:
                # Update performance metrics
                for venue_id, performance in self._venue_performance.items():
                    # Calculate recent metrics (sliding window)
                    # This would typically analyze recent order executions
                    performance.last_updated = datetime.now()
                
                await asyncio.sleep(60)  # Update every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Performance tracking error: {e}")
                await asyncio.sleep(60)
    
    async def _initialize_ml_models(self):
        """Initialize ML models for routing"""
        try:
            # This would load and initialize ML models
            # For now, just log that ML is available
            self.logger.info("ML routing models initialized")
            
        except Exception as e:
            self.logger.error(f"ML model initialization failed: {e}")
    
    # Public API Methods
    
    def get_venue_info(self, venue_id: str) -> Optional[VenueInfo]:
        """Get venue information"""
        return self._venues.get(venue_id)
    
    def get_all_venues(self) -> List[VenueInfo]:
        """Get all venue information"""
        return list(self._venues.values())
    
    def get_venue_performance(self, venue_id: str) -> Optional[VenuePerformance]:
        """Get venue performance metrics"""
        return self._venue_performance.get(venue_id)
    
    def get_routing_metrics(self) -> Dict[str, Any]:
        """Get routing engine metrics"""
        return self._routing_metrics.copy()
    
    async def get_routing_recommendation(self, 
                                       symbol: str, 
                                       side: str, 
                                       quantity: float) -> Dict[str, Any]:
        """Get routing recommendation without placing order"""
        try:
            # Create temporary order request
            temp_request = OrderRequest(
                order_id=f"temp_{int(time.time_ns())}",
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=OrderType.MARKET,
                routing_strategy=RoutingStrategy.SMART_ROUTING
            )
            
            # Get routing decision
            decision = await self.route_order(temp_request)
            
            return {
                'recommended_venues': [
                    {
                        'venue_id': venue_id,
                        'quantity': qty,
                        'price': price,
                        'venue_info': self._venues.get(venue_id, {})
                    }
                    for venue_id, qty, price in decision.venue_allocations
                ],
                'expected_cost': decision.expected_cost,
                'expected_impact': decision.expected_impact,
                'confidence': decision.confidence,
                'reasoning': decision.reasoning
            }
            
        except Exception as e:
            self.logger.error(f"Routing recommendation failed: {e}")
            return {
                'recommended_venues': [],
                'expected_cost': 0.0,
                'expected_impact': 0.0,
                'confidence': 0.0,
                'reasoning': f"Recommendation failed: {e}"
            }