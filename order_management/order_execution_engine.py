#!/usr/bin/env python3
"""
Order Execution Engine for Enhanced Order Management
Handles order routing, execution algorithms, and venue connectivity.
"""

import asyncio
import logging
import time
import random
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Set, Callable, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VenueType(Enum):
    """Trading venue types"""
    ECN = "ECN"
    MARKET_MAKER = "MARKET_MAKER"
    DARK_POOL = "DARK_POOL"
    EXCHANGE = "EXCHANGE"
    STP = "STP"

class ExecutionAlgorithm(Enum):
    """Execution algorithm types"""
    DIRECT = "DIRECT"
    TWAP = "TWAP"
    VWAP = "VWAP"
    ICEBERG = "ICEBERG"
    SNIPER = "SNIPER"
    STEALTH = "STEALTH"
    PARTICIPATION_RATE = "PARTICIPATION_RATE"

class OrderType(Enum):
    """Enhanced order types"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"
    TRAILING_STOP = "TRAILING_STOP"
    ICEBERG = "ICEBERG"
    TWAP = "TWAP"
    VWAP = "VWAP"
    BRACKET = "BRACKET"
    OCO = "OCO"
    CONDITIONAL = "CONDITIONAL"

class OrderSide(Enum):
    """Order side enumeration"""
    BUY = "BUY"
    SELL = "SELL"

@dataclass
class VenueConfig:
    """Trading venue configuration"""
    venue_id: str
    venue_type: VenueType
    symbols: Set[str]
    min_quantity: Decimal
    max_quantity: Decimal
    tick_size: Decimal
    commission_rate: Decimal
    latency_ms: float
    reliability: float  # 0.0 to 1.0
    market_hours: Dict[str, Tuple[str, str]]  # day -> (start, end)
    supports_algorithms: Set[ExecutionAlgorithm]
    priority: int = 1  # Lower number = higher priority
    enabled: bool = True

@dataclass
class MarketData:
    """Market data snapshot"""
    symbol: str
    timestamp: datetime
    bid_price: Decimal
    ask_price: Decimal
    bid_size: Decimal
    ask_size: Decimal
    last_price: Optional[Decimal] = None
    volume: Optional[Decimal] = None
    
    @property
    def spread(self) -> Decimal:
        return self.ask_price - self.bid_price
    
    @property
    def mid_price(self) -> Decimal:
        return (self.bid_price + self.ask_price) / 2

@dataclass
class OrderExecutionReport:
    """Order execution report"""
    order_id: str
    execution_id: str
    timestamp: datetime
    symbol: str
    side: OrderSide
    quantity: Decimal
    price: Decimal
    commission: Decimal
    execution_type: str
    venue: str
    liquidity_flag: str = "UNKNOWN"

@dataclass
class ExecutionSlice:
    """Execution slice for algorithmic trading"""
    slice_id: str
    parent_order_id: str
    symbol: str
    side: OrderSide
    quantity: Decimal
    target_price: Optional[Decimal]
    min_price: Optional[Decimal]
    max_price: Optional[Decimal]
    time_limit: Optional[datetime]
    venue_preference: Optional[str]
    urgency: float = 0.5  # 0.0 = patient, 1.0 = aggressive
    status: str = "PENDING"
    created_time: datetime = field(default_factory=datetime.now)

@dataclass
class EnhancedOrder:
    """Simplified order class for execution engine"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None

class OrderExecutionEngine:
    """Advanced order execution engine with smart routing and algorithms"""
    
    def __init__(self):
        self.venues: Dict[str, VenueConfig] = {}
        self.market_data: Dict[str, MarketData] = {}
        self.execution_algorithms: Dict[str, Callable] = {}
        self.active_executions: Dict[str, List[ExecutionSlice]] = {}
        self.execution_callbacks: List[Callable] = []
        self.routing_callbacks: List[Callable] = []
        self.venue_sessions: Dict[str, bool] = {}
        self.execution_stats: Dict[str, Dict] = defaultdict(dict)
        self.order_book_cache: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._running = False
        self._background_tasks: Set[asyncio.Task] = set()
        
        # Initialize default venues
        self._initialize_default_venues()
        
        # Initialize execution algorithms
        self._initialize_execution_algorithms()
        
        logger.info("Order Execution Engine initialized")
    
    def _initialize_default_venues(self):
        """Initialize default trading venues"""
        # Primary ECN
        self.venues["ECN_PRIMARY"] = VenueConfig(
            venue_id="ECN_PRIMARY",
            venue_type=VenueType.ECN,
            symbols={'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD'},
            min_quantity=Decimal('1000'),
            max_quantity=Decimal('10000000'),
            tick_size=Decimal('0.00001'),
            commission_rate=Decimal('0.00002'),
            latency_ms=2.5,
            reliability=0.99,
            market_hours={'MON-FRI': ('00:00', '23:59')},
            supports_algorithms={ExecutionAlgorithm.DIRECT, ExecutionAlgorithm.ICEBERG, ExecutionAlgorithm.TWAP},
            priority=1
        )
        
        # Secondary ECN
        self.venues["ECN_SECONDARY"] = VenueConfig(
            venue_id="ECN_SECONDARY",
            venue_type=VenueType.ECN,
            symbols={'EURUSD', 'GBPUSD', 'USDJPY'},
            min_quantity=Decimal('5000'),
            max_quantity=Decimal('5000000'),
            tick_size=Decimal('0.00001'),
            commission_rate=Decimal('0.00003'),
            latency_ms=3.2,
            reliability=0.97,
            market_hours={'MON-FRI': ('00:00', '23:59')},
            supports_algorithms={ExecutionAlgorithm.DIRECT, ExecutionAlgorithm.VWAP},
            priority=2
        )
        
        # Dark Pool
        self.venues["DARK_POOL_1"] = VenueConfig(
            venue_id="DARK_POOL_1",
            venue_type=VenueType.DARK_POOL,
            symbols={'EURUSD', 'GBPUSD'},
            min_quantity=Decimal('50000'),
            max_quantity=Decimal('50000000'),
            tick_size=Decimal('0.00001'),
            commission_rate=Decimal('0.00001'),
            latency_ms=5.0,
            reliability=0.95,
            market_hours={'MON-FRI': ('00:00', '23:59')},
            supports_algorithms={ExecutionAlgorithm.STEALTH, ExecutionAlgorithm.PARTICIPATION_RATE},
            priority=3
        )
    
    def _initialize_execution_algorithms(self):
        """Initialize execution algorithms"""
        self.execution_algorithms = {
            ExecutionAlgorithm.DIRECT.value: self._execute_direct,
            ExecutionAlgorithm.TWAP.value: self._execute_twap,
            ExecutionAlgorithm.VWAP.value: self._execute_vwap,
            ExecutionAlgorithm.ICEBERG.value: self._execute_iceberg,
            ExecutionAlgorithm.SNIPER.value: self._execute_sniper,
            ExecutionAlgorithm.STEALTH.value: self._execute_stealth,
            ExecutionAlgorithm.PARTICIPATION_RATE.value: self._execute_participation_rate
        }
    
    async def start(self):
        """Start the execution engine"""
        self._running = True
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._market_data_processor()),
            asyncio.create_task(self._execution_monitor()),
            asyncio.create_task(self._venue_health_monitor())
        ]
        
        for task in tasks:
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
        
        logger.info("Order Execution Engine started")
    
    async def stop(self):
        """Stop the execution engine"""
        self._running = False
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        logger.info("Order Execution Engine stopped")
    
    async def execute_order(self, order: EnhancedOrder) -> List[OrderExecutionReport]:
        """Execute an order using smart routing and algorithms"""
        logger.info(f"Executing order {order.order_id} for {order.symbol}")
        
        try:
            # Determine execution strategy
            execution_strategy = self._determine_execution_strategy(order)
            
            # Route order to appropriate venues
            venue_routes = await self._smart_route_order(order)
            
            # Execute using selected algorithm
            algorithm = execution_strategy.get('algorithm', ExecutionAlgorithm.DIRECT)
            execution_reports = await self.execution_algorithms[algorithm.value](order, venue_routes)
            
            # Update execution statistics
            self._update_execution_stats(order, execution_reports)
            
            # Trigger callbacks
            for callback in self.execution_callbacks:
                try:
                    await callback(order, execution_reports)
                except Exception as e:
                    logger.error(f"Execution callback error: {e}")
            
            logger.info(f"Order {order.order_id} execution completed with {len(execution_reports)} fills")
            return execution_reports
            
        except Exception as e:
            logger.error(f"Order execution failed: {e}")
            raise
    
    def _determine_execution_strategy(self, order: EnhancedOrder) -> Dict[str, Any]:
        """Determine optimal execution strategy for an order"""
        strategy = {
            'algorithm': ExecutionAlgorithm.DIRECT,
            'urgency': 0.5,
            'max_participation_rate': 0.2,
            'time_horizon': timedelta(minutes=30)
        }
        
        # Determine algorithm based on order characteristics
        if order.order_type == OrderType.MARKET:
            strategy['algorithm'] = ExecutionAlgorithm.DIRECT
            strategy['urgency'] = 1.0
        elif order.order_type == OrderType.LIMIT:
            # For limit orders, check if price is favorable
            market_data = self.market_data.get(order.symbol)
            if market_data and not self._is_favorable_price(order, market_data):
                # Don't execute immediately if price is not favorable
                strategy['algorithm'] = ExecutionAlgorithm.SNIPER  # Wait for better price
                strategy['urgency'] = 0.1
            else:
                strategy['algorithm'] = ExecutionAlgorithm.DIRECT
        elif order.order_type == OrderType.TWAP:
            strategy['algorithm'] = ExecutionAlgorithm.TWAP
            strategy['time_horizon'] = timedelta(hours=1)
        elif order.order_type == OrderType.VWAP:
            strategy['algorithm'] = ExecutionAlgorithm.VWAP
            strategy['time_horizon'] = timedelta(hours=2)
        elif order.order_type == OrderType.ICEBERG:
            strategy['algorithm'] = ExecutionAlgorithm.ICEBERG
            strategy['slice_size'] = min(order.quantity / 10, Decimal('100000'))
        elif order.quantity > Decimal('1000000'):  # Large orders
            strategy['algorithm'] = ExecutionAlgorithm.STEALTH
            strategy['urgency'] = 0.3
            strategy['max_participation_rate'] = 0.1
        
        # Adjust based on market conditions
        market_data = self.market_data.get(order.symbol)
        if market_data:
            spread_bps = (market_data.spread / market_data.mid_price) * 10000
            if spread_bps > 2.0:  # Wide spread
                strategy['urgency'] = min(strategy['urgency'] * 0.8, 1.0)
        
        return strategy
    
    async def _smart_route_order(self, order: EnhancedOrder) -> List[Tuple[str, Decimal]]:
        """Smart route order across venues"""
        suitable_venues = []
        
        # Find suitable venues
        for venue_id, venue_config in self.venues.items():
            if (venue_config.enabled and 
                order.symbol in venue_config.symbols and
                order.quantity >= venue_config.min_quantity and
                order.quantity <= venue_config.max_quantity and
                self.venue_sessions.get(venue_id, True)):
                
                suitable_venues.append((venue_id, venue_config))
        
        if not suitable_venues:
            raise Exception(f"No suitable venues found for {order.symbol}")
        
        # Sort by priority and reliability
        suitable_venues.sort(key=lambda x: (x[1].priority, -x[1].reliability))
        
        # Allocate quantity across venues
        routes = []
        remaining_quantity = order.quantity
        
        if len(suitable_venues) == 1:
            # Single venue
            routes.append((suitable_venues[0][0], remaining_quantity))
        else:
            # Multi-venue routing
            primary_venue = suitable_venues[0]
            secondary_venues = suitable_venues[1:3]  # Up to 2 additional venues
            
            # Allocate 70% to primary, 30% to secondary venues
            primary_allocation = remaining_quantity * Decimal('0.7')
            routes.append((primary_venue[0], primary_allocation))
            remaining_quantity -= primary_allocation
            
            # Distribute remaining across secondary venues
            if secondary_venues and remaining_quantity > 0:
                per_venue = remaining_quantity / len(secondary_venues)
                for venue_id, _ in secondary_venues:
                    allocation = min(per_venue, remaining_quantity)
                    if allocation > 0:
                        routes.append((venue_id, allocation))
                        remaining_quantity -= allocation
        
        # Trigger routing callbacks
        for callback in self.routing_callbacks:
            try:
                await callback(order, routes)
            except Exception as e:
                logger.error(f"Routing callback error: {e}")
        
        logger.info(f"Order {order.order_id} routed to {len(routes)} venues")
        return routes
    
    async def _execute_direct(self, order: EnhancedOrder, routes: List[Tuple[str, Decimal]]) -> List[OrderExecutionReport]:
        """Direct execution algorithm"""
        execution_reports = []
        
        for venue_id, quantity in routes:
            venue_config = self.venues[venue_id]
            
            # Simulate venue execution
            await asyncio.sleep(venue_config.latency_ms / 1000)
            
            # Determine execution price
            market_data = self.market_data.get(order.symbol)
            if market_data:
                if order.side == OrderSide.BUY:
                    execution_price = market_data.ask_price
                else:
                    execution_price = market_data.bid_price
            else:
                # Fallback price
                execution_price = order.price or Decimal('1.0000')
            
            # Calculate commission
            commission = quantity * execution_price * venue_config.commission_rate
            
            # Create execution report
            execution_report = OrderExecutionReport(
                order_id=order.order_id,
                execution_id=f"EXEC_{int(time.time() * 1000000)}",
                timestamp=datetime.now(),
                symbol=order.symbol,
                side=order.side,
                quantity=quantity,
                price=execution_price,
                commission=commission,
                execution_type="DIRECT",
                venue=venue_id,
                liquidity_flag="TAKER"
            )
            
            execution_reports.append(execution_report)
            logger.info(f"Direct execution: {quantity} {order.symbol} @ {execution_price} on {venue_id}")
        
        return execution_reports
    
    async def _execute_twap(self, order: EnhancedOrder, routes: List[Tuple[str, Decimal]]) -> List[OrderExecutionReport]:
        """Time-Weighted Average Price execution algorithm"""
        execution_reports = []
        
        # TWAP parameters
        time_horizon = timedelta(minutes=30)  # Default 30 minutes
        slice_interval = timedelta(minutes=2)  # Execute every 2 minutes
        num_slices = int(time_horizon.total_seconds() / slice_interval.total_seconds())
        
        for venue_id, total_quantity in routes:
            slice_quantity = total_quantity / num_slices
            
            for i in range(num_slices):
                # Wait for slice interval (except first slice)
                if i > 0:
                    await asyncio.sleep(slice_interval.total_seconds())
                
                # Execute slice
                slice_reports = await self._execute_slice(order, venue_id, slice_quantity, "TWAP")
                execution_reports.extend(slice_reports)
        
        return execution_reports
    
    async def _execute_vwap(self, order: EnhancedOrder, routes: List[Tuple[str, Decimal]]) -> List[OrderExecutionReport]:
        """Volume-Weighted Average Price execution algorithm"""
        execution_reports = []
        
        # VWAP parameters (simplified - would use historical volume patterns)
        volume_profile = [0.1, 0.15, 0.2, 0.25, 0.2, 0.1]  # Hourly volume distribution
        
        for venue_id, total_quantity in routes:
            for i, volume_weight in enumerate(volume_profile):
                slice_quantity = total_quantity * Decimal(str(volume_weight))
                
                if i > 0:
                    await asyncio.sleep(600)  # 10 minutes between slices
                
                slice_reports = await self._execute_slice(order, venue_id, slice_quantity, "VWAP")
                execution_reports.extend(slice_reports)
        
        return execution_reports
    
    async def _execute_iceberg(self, order: EnhancedOrder, routes: List[Tuple[str, Decimal]]) -> List[OrderExecutionReport]:
        """Iceberg execution algorithm"""
        execution_reports = []
        
        # Iceberg parameters
        slice_size = min(order.quantity / 10, Decimal('100000'))
        
        for venue_id, total_quantity in routes:
            remaining = total_quantity
            
            while remaining > 0:
                current_slice = min(slice_size, remaining)
                
                slice_reports = await self._execute_slice(order, venue_id, current_slice, "ICEBERG")
                execution_reports.extend(slice_reports)
                
                remaining -= current_slice
                
                if remaining > 0:
                    # Wait between slices
                    await asyncio.sleep(random.uniform(5, 15))
        
        return execution_reports
    
    async def _execute_sniper(self, order: EnhancedOrder, routes: List[Tuple[str, Decimal]]) -> List[OrderExecutionReport]:
        """Sniper execution algorithm - aggressive execution at favorable prices"""
        execution_reports = []
        
        for venue_id, quantity in routes:
            # Wait for favorable market conditions
            max_wait_time = 2  # Maximum 2 seconds for testing
            start_time = time.time()
            
            price_is_favorable = False
            while time.time() - start_time < max_wait_time:
                market_data = self.market_data.get(order.symbol)
                if market_data and self._is_favorable_price(order, market_data):
                    price_is_favorable = True
                    break
                await asyncio.sleep(0.1)
            
            # Only execute if price is favorable
            if price_is_favorable:
                slice_reports = await self._execute_slice(order, venue_id, quantity, "SNIPER")
                execution_reports.extend(slice_reports)
            else:
                logger.info(f"Sniper order {order.order_id} waiting for favorable price")
        
        return execution_reports
    
    async def _execute_stealth(self, order: EnhancedOrder, routes: List[Tuple[str, Decimal]]) -> List[OrderExecutionReport]:
        """Stealth execution algorithm - minimize market impact"""
        execution_reports = []
        
        # Stealth parameters
        max_participation_rate = 0.1  # Maximum 10% of market volume
        slice_size = order.quantity * Decimal('0.05')  # 5% slices
        
        for venue_id, total_quantity in routes:
            remaining = total_quantity
            
            while remaining > 0:
                # Determine slice size based on market conditions
                current_slice = min(slice_size, remaining)
                
                # Add randomization to avoid detection
                randomization = random.uniform(0.8, 1.2)
                current_slice = current_slice * Decimal(str(randomization))
                current_slice = min(current_slice, remaining)
                
                slice_reports = await self._execute_slice(order, venue_id, current_slice, "STEALTH")
                execution_reports.extend(slice_reports)
                
                remaining -= current_slice
                
                if remaining > 0:
                    # Random wait time to avoid pattern detection
                    wait_time = random.uniform(30, 120)
                    await asyncio.sleep(wait_time)
        
        return execution_reports
    
    async def _execute_participation_rate(self, order: EnhancedOrder, routes: List[Tuple[str, Decimal]]) -> List[OrderExecutionReport]:
        """Participation rate execution algorithm"""
        execution_reports = []
        
        # Participation rate parameters
        target_participation_rate = 0.2  # 20% of market volume
        
        for venue_id, total_quantity in routes:
            remaining = total_quantity
            
            while remaining > 0:
                # Estimate market volume (simplified)
                estimated_volume = Decimal('1000000')  # Would use real market data
                max_slice = estimated_volume * Decimal(str(target_participation_rate))
                
                current_slice = min(max_slice, remaining)
                
                slice_reports = await self._execute_slice(order, venue_id, current_slice, "PARTICIPATION_RATE")
                execution_reports.extend(slice_reports)
                
                remaining -= current_slice
                
                if remaining > 0:
                    await asyncio.sleep(60)  # Wait 1 minute between slices
        
        return execution_reports
    
    async def _execute_slice(self, order: EnhancedOrder, venue_id: str, quantity: Decimal, algorithm: str) -> List[OrderExecutionReport]:
        """Execute a single slice of an order"""
        venue_config = self.venues[venue_id]
        
        # Simulate venue latency
        await asyncio.sleep(venue_config.latency_ms / 1000)
        
        # Simulate execution reliability
        if random.random() > venue_config.reliability:
            logger.warning(f"Execution failed on {venue_id} due to venue issues")
            return []
        
        # Determine execution price
        market_data = self.market_data.get(order.symbol)
        if market_data:
            if order.side == OrderSide.BUY:
                base_price = market_data.ask_price
            else:
                base_price = market_data.bid_price
            
            # Add some price improvement for certain algorithms
            if algorithm in ["STEALTH", "PARTICIPATION_RATE"]:
                improvement = market_data.spread * Decimal('0.3')
                if order.side == OrderSide.BUY:
                    execution_price = base_price - improvement
                else:
                    execution_price = base_price + improvement
            else:
                execution_price = base_price
        else:
            execution_price = order.price or Decimal('1.0000')
        
        # Calculate commission
        commission = quantity * execution_price * venue_config.commission_rate
        
        # Create execution report
        execution_report = OrderExecutionReport(
            order_id=order.order_id,
            execution_id=f"EXEC_{algorithm}_{int(time.time() * 1000000)}",
            timestamp=datetime.now(),
            symbol=order.symbol,
            side=order.side,
            quantity=quantity,
            price=execution_price,
            commission=commission,
            execution_type=algorithm,
            venue=venue_id,
            liquidity_flag="MAKER" if algorithm in ["STEALTH", "PARTICIPATION_RATE"] else "TAKER"
        )
        
        logger.info(f"{algorithm} slice executed: {quantity} {order.symbol} @ {execution_price} on {venue_id}")
        return [execution_report]
    
    def _is_favorable_price(self, order: EnhancedOrder, market_data: MarketData) -> bool:
        """Check if current market price is favorable for execution"""
        if order.price is None:
            return True
        
        if order.side == OrderSide.BUY:
            return market_data.ask_price <= order.price
        else:
            return market_data.bid_price >= order.price
    
    async def _market_data_processor(self):
        """Background task to process market data updates"""
        while self._running:
            try:
                # Simulate market data updates
                await self._simulate_market_data_update()
                await asyncio.sleep(0.1)  # Update every 100ms
            except Exception as e:
                logger.error(f"Market data processor error: {e}")
                await asyncio.sleep(1)
    
    async def _simulate_market_data_update(self):
        """Simulate market data updates"""
        symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD']
        
        for symbol in symbols:
            # Generate realistic market data
            if symbol not in self.market_data:
                # Initialize with base prices
                base_prices = {
                    'EURUSD': Decimal('1.1000'),
                    'GBPUSD': Decimal('1.2500'),
                    'USDJPY': Decimal('110.00'),
                    'AUDUSD': Decimal('0.7500'),
                    'USDCAD': Decimal('1.2500')
                }
                mid_price = base_prices.get(symbol, Decimal('1.0000'))
            else:
                mid_price = self.market_data[symbol].mid_price
            
            # Add random walk
            change = Decimal(str(random.uniform(-0.0001, 0.0001)))
            new_mid = mid_price + change
            
            # Generate bid/ask around mid
            spread = Decimal('0.00002')  # 0.2 pips
            bid_price = new_mid - spread / 2
            ask_price = new_mid + spread / 2
            
            # Generate sizes
            bid_size = Decimal(str(random.uniform(100000, 1000000)))
            ask_size = Decimal(str(random.uniform(100000, 1000000)))
            
            self.market_data[symbol] = MarketData(
                symbol=symbol,
                timestamp=datetime.now(),
                bid_price=bid_price,
                ask_price=ask_price,
                bid_size=bid_size,
                ask_size=ask_size,
                last_price=new_mid,
                volume=Decimal(str(random.uniform(10000000, 50000000)))
            )
    
    async def _execution_monitor(self):
        """Monitor active executions"""
        while self._running:
            try:
                # Monitor execution progress
                current_time = datetime.now()
                
                for order_id, slices in self.active_executions.items():
                    for slice_obj in slices:
                        if (slice_obj.status == "PENDING" and 
                            slice_obj.time_limit and 
                            current_time > slice_obj.time_limit):
                            slice_obj.status = "EXPIRED"
                            logger.warning(f"Execution slice {slice_obj.slice_id} expired")
                
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Execution monitor error: {e}")
                await asyncio.sleep(10)
    
    async def _venue_health_monitor(self):
        """Monitor venue health and connectivity"""
        while self._running:
            try:
                for venue_id, venue_config in self.venues.items():
                    # Simulate venue health check
                    health_check_success = random.random() < venue_config.reliability
                    self.venue_sessions[venue_id] = health_check_success
                    
                    if not health_check_success:
                        logger.warning(f"Venue {venue_id} health check failed")
                
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Venue health monitor error: {e}")
                await asyncio.sleep(60)
    
    def _update_execution_stats(self, order: EnhancedOrder, execution_reports: List[OrderExecutionReport]):
        """Update execution statistics"""
        if order.symbol not in self.execution_stats:
            self.execution_stats[order.symbol] = {
                'total_orders': 0,
                'total_volume': Decimal('0'),
                'total_commission': Decimal('0'),
                'venue_breakdown': defaultdict(int),
                'algorithm_breakdown': defaultdict(int),
                'avg_execution_time': 0.0
            }
        
        stats = self.execution_stats[order.symbol]
        stats['total_orders'] += 1
        
        for report in execution_reports:
            stats['total_volume'] += report.quantity
            stats['total_commission'] += report.commission
            stats['venue_breakdown'][report.venue] += 1
            stats['algorithm_breakdown'][report.execution_type] += 1
    
    def add_venue(self, venue_config: VenueConfig):
        """Add a new trading venue"""
        self.venues[venue_config.venue_id] = venue_config
        self.venue_sessions[venue_config.venue_id] = True
        logger.info(f"Added venue: {venue_config.venue_id}")
    
    def remove_venue(self, venue_id: str):
        """Remove a trading venue"""
        if venue_id in self.venues:
            del self.venues[venue_id]
            self.venue_sessions.pop(venue_id, None)
            logger.info(f"Removed venue: {venue_id}")
    
    def update_market_data(self, symbol: str, market_data: MarketData):
        """Update market data for a symbol"""
        self.market_data[symbol] = market_data
        
        # Cache for order book analysis
        self.order_book_cache[symbol].append({
            'timestamp': market_data.timestamp,
            'bid': market_data.bid_price,
            'ask': market_data.ask_price,
            'bid_size': market_data.bid_size,
            'ask_size': market_data.ask_size
        })
    
    def get_execution_statistics(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get execution statistics"""
        if symbol:
            return self.execution_stats.get(symbol, {})
        else:
            return dict(self.execution_stats)
    
    def get_venue_status(self) -> Dict[str, Dict[str, Any]]:
        """Get venue status information"""
        status = {}
        for venue_id, venue_config in self.venues.items():
            status[venue_id] = {
                'enabled': venue_config.enabled,
                'connected': self.venue_sessions.get(venue_id, False),
                'venue_type': venue_config.venue_type.value,
                'symbols': list(venue_config.symbols),
                'reliability': venue_config.reliability,
                'latency_ms': venue_config.latency_ms,
                'priority': venue_config.priority
            }
        return status
    
    def register_execution_callback(self, callback: Callable):
        """Register callback for execution events"""
        self.execution_callbacks.append(callback)
    
    def register_routing_callback(self, callback: Callable):
        """Register callback for routing events"""
        self.routing_callbacks.append(callback)

async def main():
    """Example usage of Order Execution Engine"""
    # Create execution engine
    execution_engine = OrderExecutionEngine()
    
    try:
        # Start the execution engine
        await execution_engine.start()
        
        # Create test orders
        market_order = EnhancedOrder(
            order_id="TEST_001",
            symbol='EURUSD',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100000')
        )
        
        limit_order = EnhancedOrder(
            order_id="TEST_002",
            symbol='GBPUSD',
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=Decimal('50000'),
            price=Decimal('1.2500')
        )
        
        # Execute orders
        market_executions = await execution_engine.execute_order(market_order)
        limit_executions = await execution_engine.execute_order(limit_order)
        
        print(f"Market order executions: {len(market_executions)}")
        print(f"Limit order executions: {len(limit_executions)}")
        
        # Print venue status
        venue_status = execution_engine.get_venue_status()
        print(f"Venue Status: {venue_status}")
        
        # Print execution statistics
        stats = execution_engine.get_execution_statistics()
        print(f"Execution Statistics: {stats}")
        
        # Wait a bit
        await asyncio.sleep(5)
        
    finally:
        # Stop the execution engine
        await execution_engine.stop()

if __name__ == "__main__":
    asyncio.run(main())