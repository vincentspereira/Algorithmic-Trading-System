"""
Enhanced Base Classes for Institutional-Grade Trading System.

This module provides the foundational base classes that integrate with the
dependency injection framework and implement the 5-pillar institutional architecture:

1. Volume Integration & Confirmation
2. Market Regime Adaptation
3. Multi-Timeframe Convergence Analysis
4. Smart Money & Microstructure Proxies
5. Automated Risk Management Factory

All base classes include:
- Dependency injection integration
- Comprehensive logging and monitoring
- Performance metrics collection
- Error handling and recovery
- Configuration management
- Health monitoring
- Thread safety
- Async support
"""

import asyncio
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Type, Union
from weakref import WeakSet

from loguru import logger

from .dependency_injection import (
    DependencyInjectionContainer,
    get_container,
    injectable,
    singleton,
    ServiceLifetime,
    ServiceScope
)


class ComponentStatus(Enum):
    """Component lifecycle status."""
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    DEGRADED = "degraded"


class ComponentHealth(Enum):
    """Component health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentMetrics:
    """Component performance metrics."""
    component_name: str
    start_time: float = field(default_factory=time.time)
    operation_count: int = 0
    error_count: int = 0
    last_operation_time: float = 0.0
    total_operation_time: float = 0.0
    memory_usage: int = 0
    cpu_usage: float = 0.0
    custom_metrics: Dict[str, Any] = field(default_factory=dict)

    def record_operation(self, duration: float):
        """Record an operation."""
        self.operation_count += 1
        self.last_operation_time = time.time()
        self.total_operation_time += duration

    def record_error(self):
        """Record an error."""
        self.error_count += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        uptime = time.time() - self.start_time
        avg_operation_time = (
            self.total_operation_time / self.operation_count
            if self.operation_count > 0 else 0
        )

        return {
            "component_name": self.component_name,
            "uptime_seconds": uptime,
            "total_operations": self.operation_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / self.operation_count if self.operation_count > 0 else 0,
            "average_operation_time": avg_operation_time,
            "operations_per_second": self.operation_count / uptime if uptime > 0 else 0,
            "memory_usage_mb": self.memory_usage / 1024 / 1024 if self.memory_usage > 0 else 0,
            "cpu_usage_percent": self.cpu_usage,
            "custom_metrics": self.custom_metrics
        }


class BaseComponent(ABC):
    """
    Enhanced base class for all system components.

    Provides:
    - Dependency injection integration
    - Lifecycle management
    - Health monitoring
    - Performance metrics
    - Error handling and recovery
    - Configuration management
    - Thread safety
    """

    def __init__(self, name: str, container: Optional[DependencyInjectionContainer] = None):
        self._name = name
        self._container = container or get_container()
        self._status = ComponentStatus.INITIALIZING
        self._health = ComponentHealth.UNKNOWN
        self._metrics = ComponentMetrics(component_name=name)
        self._lock = threading.RLock()
        self._event_handlers: Dict[str, Set[callable]] = {}
        self._shutdown_event = asyncio.Event()
        self._background_tasks: Set[asyncio.Task] = set()

        # Register with container for health monitoring
        self._register_with_container()

    @property
    def name(self) -> str:
        """Component name."""
        return self._name

    @property
    def status(self) -> ComponentStatus:
        """Component status."""
        with self._lock:
            return self._status

    @property
    def health(self) -> ComponentHealth:
        """Component health."""
        with self._lock:
            return self._health

    @property
    def metrics(self) -> ComponentMetrics:
        """Component metrics."""
        return self._metrics

    def _register_with_container(self):
        """Register component with dependency injection container."""
        try:
            # This would be enhanced in a real implementation
            # to register health checks and metrics collection
            pass
        except Exception as e:
            logger.warning(f"Failed to register {self._name} with container: {e}")

    async def initialize(self) -> bool:
        """
        Initialize the component.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            with self._lock:
                if self._status != ComponentStatus.INITIALIZING:
                    logger.warning(f"Component {self._name} already initialized")
                    return True

                logger.info(f"Initializing component: {self._name}")
                self._status = ComponentStatus.INITIALIZING

                # Perform component-specific initialization
                success = await self._initialize_impl()

                if success:
                    self._status = ComponentStatus.READY
                    self._health = ComponentHealth.HEALTHY
                    logger.info(f"Component {self._name} initialized successfully")
                else:
                    self._status = ComponentStatus.ERROR
                    self._health = ComponentHealth.UNHEALTHY
                    logger.error(f"Component {self._name} initialization failed")

                return success

        except Exception as e:
            logger.error(f"Error initializing component {self._name}: {e}")
            with self._lock:
                self._status = ComponentStatus.ERROR
                self._health = ComponentHealth.UNHEALTHY
            return False

    async def start(self) -> bool:
        """
        Start the component.

        Returns:
            True if start successful, False otherwise
        """
        try:
            with self._lock:
                if self._status != ComponentStatus.READY:
                    logger.warning(f"Component {self._name} not ready to start")
                    return False

                logger.info(f"Starting component: {self._name}")
                self._status = ComponentStatus.RUNNING

                # Perform component-specific startup
                success = await self._start_impl()

                if success:
                    logger.info(f"Component {self._name} started successfully")
                else:
                    self._status = ComponentStatus.ERROR
                    self._health = ComponentHealth.UNHEALTHY
                    logger.error(f"Component {self._name} startup failed")

                return success

        except Exception as e:
            logger.error(f"Error starting component {self._name}: {e}")
            with self._lock:
                self._status = ComponentStatus.ERROR
                self._health = ComponentHealth.UNHEALTHY
            return False

    async def stop(self) -> bool:
        """
        Stop the component.

        Returns:
            True if stop successful, False otherwise
        """
        try:
            with self._lock:
                if self._status in [ComponentStatus.STOPPING, ComponentStatus.STOPPED]:
                    return True

                logger.info(f"Stopping component: {self._name}")
                self._status = ComponentStatus.STOPPING

                # Cancel background tasks
                for task in self._background_tasks:
                    if not task.done():
                        task.cancel()

                # Perform component-specific shutdown
                success = await self._stop_impl()

                self._status = ComponentStatus.STOPPED
                self._shutdown_event.set()

                if success:
                    logger.info(f"Component {self._name} stopped successfully")
                else:
                    logger.warning(f"Component {self._name} stop completed with issues")

                return success

        except Exception as e:
            logger.error(f"Error stopping component {self._name}: {e}")
            with self._lock:
                self._status = ComponentStatus.ERROR
            return False

    def add_event_handler(self, event_type: str, handler: callable):
        """Add an event handler."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = set()
        self._event_handlers[event_type].add(handler)

    def remove_event_handler(self, event_type: str, handler: callable):
        """Remove an event handler."""
        if event_type in self._event_handlers:
            self._event_handlers[event_type].discard(handler)

    def emit_event(self, event_type: str, **kwargs):
        """Emit an event to all registered handlers."""
        if event_type in self._event_handlers:
            for handler in self._event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler(**kwargs))
                    else:
                        handler(**kwargs)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_type}: {e}")

    async def wait_for_shutdown(self):
        """Wait for component shutdown."""
        await self._shutdown_event.wait()

    def get_health_status(self) -> Dict[str, Any]:
        """Get component health status."""
        with self._lock:
            return {
                "name": self._name,
                "status": self._status.value,
                "health": self._health.value,
                "metrics": self._metrics.get_summary()
            }

    # Abstract methods to be implemented by subclasses
    @abstractmethod
    async def _initialize_impl(self) -> bool:
        """Component-specific initialization logic."""
        pass

    @abstractmethod
    async def _start_impl(self) -> bool:
        """Component-specific startup logic."""
        pass

    @abstractmethod
    async def _stop_impl(self) -> bool:
        """Component-specific shutdown logic."""
        pass


class BaseIndicator(BaseComponent):
    """
    Enhanced base class for technical indicators.

    Implements the 5-pillar institutional architecture:
    1. Volume Integration & Confirmation
    2. Market Regime Adaptation
    3. Multi-Timeframe Convergence Analysis
    4. Smart Money & Microstructure Proxies
    5. Automated Risk Management Factory
    """

    def __init__(self, name: str, timeframe: str = "1m",
                 container: Optional[DependencyInjectionContainer] = None):
        super().__init__(name, container)
        self._timeframe = timeframe
        self._last_calculation_time = 0.0
        self._calculation_count = 0
        self._is_warmed_up = False

    @property
    def timeframe(self) -> str:
        """Indicator timeframe."""
        return self._timeframe

    @property
    def is_warmed_up(self) -> bool:
        """Check if indicator is warmed up."""
        return self._is_warmed_up

    def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate indicator values.

        Args:
            data: Market data dictionary

        Returns:
            Dictionary with calculated indicator values
        """
        start_time = time.time()

        try:
            # Validate input data
            if not self._validate_input_data(data):
                logger.warning(f"Invalid input data for {self._name}")
                return {}

            # Perform calculation
            result = self._calculate_impl(data)

            # Update metrics
            calculation_time = time.time() - start_time
            self._metrics.record_operation(calculation_time)
            self._last_calculation_time = time.time()
            self._calculation_count += 1

            # Check if warmed up
            if not self._is_warmed_up and self._is_warmed_up_condition_met():
                self._is_warmed_up = True
                logger.info(f"Indicator {self._name} is now warmed up")

            return result

        except Exception as e:
            logger.error(f"Error calculating {self._name}: {e}")
            self._metrics.record_error()
            return {}

    def get_indicator_info(self) -> Dict[str, Any]:
        """Get indicator information and metadata."""
        return {
            "name": self._name,
            "timeframe": self._timeframe,
            "is_warmed_up": self._is_warmed_up,
            "calculation_count": self._calculation_count,
            "last_calculation_time": self._last_calculation_time,
            "health_status": self.get_health_status()
        }

    # Abstract methods
    @abstractmethod
    def _validate_input_data(self, data: Dict[str, Any]) -> bool:
        """Validate input data for calculation."""
        pass

    @abstractmethod
    def _calculate_impl(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform the actual indicator calculation."""
        pass

    @abstractmethod
    def _is_warmed_up_condition_met(self) -> bool:
        """Check if indicator warm-up conditions are met."""
        pass

    # Base component implementation
    async def _initialize_impl(self) -> bool:
        """Initialize indicator."""
        try:
            # Indicator-specific initialization
            await self._initialize_indicator()
            return True
        except Exception as e:
            logger.error(f"Failed to initialize indicator {self._name}: {e}")
            return False

    async def _start_impl(self) -> bool:
        """Start indicator."""
        try:
            # Indicator-specific startup
            await self._start_indicator()
            return True
        except Exception as e:
            logger.error(f"Failed to start indicator {self._name}: {e}")
            return False

    async def _stop_impl(self) -> bool:
        """Stop indicator."""
        try:
            # Indicator-specific shutdown
            await self._stop_indicator()
            return True
        except Exception as e:
            logger.error(f"Failed to stop indicator {self._name}: {e}")
            return False

    # Indicator-specific lifecycle methods (can be overridden)
    async def _initialize_indicator(self):
        """Indicator-specific initialization."""
        pass

    async def _start_indicator(self):
        """Indicator-specific startup."""
        pass

    async def _stop_indicator(self):
        """Indicator-specific shutdown."""
        pass


class BaseStrategy(BaseComponent):
    """
    Enhanced base class for trading strategies.

    Implements comprehensive strategy management with:
    - Multi-timeframe analysis
    - Risk management integration
    - Performance tracking
    - Signal generation and execution
    - Market regime adaptation
    """

    def __init__(self, name: str, config: Dict[str, Any],
                 container: Optional[DependencyInjectionContainer] = None):
        super().__init__(name, container)
        self._config = config
        self._indicators: Dict[str, BaseIndicator] = {}
        self._active_positions: Dict[str, Any] = {}
        self._signal_history: List[Dict[str, Any]] = []
        self._performance_metrics: Dict[str, Any] = {}

    @property
    def config(self) -> Dict[str, Any]:
        """Strategy configuration."""
        return self._config

    @property
    def indicators(self) -> Dict[str, BaseIndicator]:
        """Strategy indicators."""
        return self._indicators

    def add_indicator(self, name: str, indicator: BaseIndicator):
        """Add an indicator to the strategy."""
        self._indicators[name] = indicator
        logger.info(f"Added indicator {name} to strategy {self._name}")

    def remove_indicator(self, name: str):
        """Remove an indicator from the strategy."""
        if name in self._indicators:
            del self._indicators[name]
            logger.info(f"Removed indicator {name} from strategy {self._name}")

    def generate_signals(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate trading signals.

        Args:
            market_data: Current market data

        Returns:
            List of trading signals
        """
        start_time = time.time()

        try:
            signals = self._generate_signals_impl(market_data)

            # Record signals
            for signal in signals:
                signal_entry = {
                    "timestamp": time.time(),
                    "signal": signal,
                    "market_data": market_data.copy()
                }
                self._signal_history.append(signal_entry)

            # Update metrics
            calculation_time = time.time() - start_time
            self._metrics.record_operation(calculation_time)

            return signals

        except Exception as e:
            logger.error(f"Error generating signals for {self._name}: {e}")
            self._metrics.record_error()
            return []

    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy information and metadata."""
        return {
            "name": self._name,
            "config": self._config,
            "indicator_count": len(self._indicators),
            "active_positions": len(self._active_positions),
            "total_signals": len(self._signal_history),
            "performance_metrics": self._performance_metrics,
            "health_status": self.get_health_status()
        }

    # Abstract methods
    @abstractmethod
    def _generate_signals_impl(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate trading signals implementation."""
        pass

    # Base component implementation
    async def _initialize_impl(self) -> bool:
        """Initialize strategy."""
        try:
            # Initialize indicators
            for indicator in self._indicators.values():
                if not await indicator.initialize():
                    logger.error(f"Failed to initialize indicator for strategy {self._name}")
                    return False

            # Strategy-specific initialization
            await self._initialize_strategy()
            return True
        except Exception as e:
            logger.error(f"Failed to initialize strategy {self._name}: {e}")
            return False

    async def _start_impl(self) -> bool:
        """Start strategy."""
        try:
            # Start indicators
            for indicator in self._indicators.values():
                if not await indicator.start():
                    logger.error(f"Failed to start indicator for strategy {self._name}")
                    return False

            # Strategy-specific startup
            await self._start_strategy()
            return True
        except Exception as e:
            logger.error(f"Failed to start strategy {self._name}: {e}")
            return False

    async def _stop_impl(self) -> bool:
        """Stop strategy."""
        try:
            # Stop indicators
            for indicator in self._indicators.values():
                await indicator.stop()

            # Strategy-specific shutdown
            await self._stop_strategy()
            return True
        except Exception as e:
            logger.error(f"Failed to stop strategy {self._name}: {e}")
            return False

    # Strategy-specific lifecycle methods (can be overridden)
    async def _initialize_strategy(self):
        """Strategy-specific initialization."""
        pass

    async def _start_strategy(self):
        """Strategy-specific startup."""
        pass

    async def _stop_strategy(self):
        """Strategy-specific shutdown."""
        pass


class BaseEngine(BaseComponent):
    """
    Enhanced base class for analysis engines.

    Provides:
    - Parallel processing capabilities
    - Multi-timeframe analysis
    - Smart money tracking
    - Market regime detection
    - Performance optimization
    """

    def __init__(self, name: str, config: Dict[str, Any],
                 container: Optional[DependencyInjectionContainer] = None):
        super().__init__(name, container)
        self._config = config
        self._workers: Set[asyncio.Task] = set()
        self._processing_queue = asyncio.Queue()
        self._results_cache: Dict[str, Any] = {}

    @property
    def config(self) -> Dict[str, Any]:
        """Engine configuration."""
        return self._config

    async def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process data through the engine.

        Args:
            data: Input data for processing

        Returns:
            Processing results
        """
        start_time = time.time()

        try:
            # Add to processing queue
            await self._processing_queue.put(data)

            # Process data
            result = await self._process_data_impl(data)

            # Update metrics
            processing_time = time.time() - start_time
            self._metrics.record_operation(processing_time)

            return result

        except Exception as e:
            logger.error(f"Error processing data in {self._name}: {e}")
            self._metrics.record_error()
            return {}

    def get_engine_info(self) -> Dict[str, Any]:
        """Get engine information and metadata."""
        return {
            "name": self._name,
            "config": self._config,
            "active_workers": len(self._workers),
            "queue_size": self._processing_queue.qsize(),
            "cache_size": len(self._results_cache),
            "health_status": self.get_health_status()
        }

    # Abstract methods
    @abstractmethod
    async def _process_data_impl(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data implementation."""
        pass

    # Base component implementation
    async def _initialize_impl(self) -> bool:
        """Initialize engine."""
        try:
            # Engine-specific initialization
            await self._initialize_engine()
            return True
        except Exception as e:
            logger.error(f"Failed to initialize engine {self._name}: {e}")
            return False

    async def _start_impl(self) -> bool:
        """Start engine."""
        try:
            # Start worker tasks
            worker_count = self._config.get('worker_count', 4)
            for i in range(worker_count):
                task = asyncio.create_task(self._worker_loop(i))
                self._workers.add(task)

            # Engine-specific startup
            await self._start_engine()
            return True
        except Exception as e:
            logger.error(f"Failed to start engine {self._name}: {e}")
            return False

    async def _stop_impl(self) -> bool:
        """Stop engine."""
        try:
            # Stop worker tasks
            for task in self._workers:
                if not task.done():
                    task.cancel()

            # Wait for tasks to complete
            await asyncio.gather(*self._workers, return_exceptions=True)

            # Engine-specific shutdown
            await self._stop_engine()
            return True
        except Exception as e:
            logger.error(f"Failed to stop engine {self._name}: {e}")
            return False

    async def _worker_loop(self, worker_id: int):
        """Worker task loop."""
        logger.info(f"Starting worker {worker_id} for engine {self._name}")

        try:
            while True:
                # Get data from queue
                data = await self._processing_queue.get()

                try:
                    # Process data
                    result = await self._process_worker_data(data, worker_id)

                    # Handle result
                    await self._handle_worker_result(result, worker_id)

                except Exception as e:
                    logger.error(f"Error in worker {worker_id}: {e}")
                finally:
                    self._processing_queue.task_done()

        except asyncio.CancelledError:
            logger.info(f"Worker {worker_id} cancelled")
        except Exception as e:
            logger.error(f"Fatal error in worker {worker_id}: {e}")

    async def _process_worker_data(self, data: Dict[str, Any], worker_id: int) -> Dict[str, Any]:
        """Process data in worker (can be overridden)."""
        return await self._process_data_impl(data)

    async def _handle_worker_result(self, result: Dict[str, Any], worker_id: int):
        """Handle worker result (can be overridden)."""
        pass

    # Engine-specific lifecycle methods (can be overridden)
    async def _initialize_engine(self):
        """Engine-specific initialization."""
        pass

    async def _start_engine(self):
        """Engine-specific startup."""
        pass

    async def _stop_engine(self):
        """Engine-specific shutdown."""
        pass


# Convenience functions for creating components
def create_indicator(name: str, indicator_class: Type[BaseIndicator], **kwargs) -> BaseIndicator:
    """Create an indicator instance with dependency injection."""
    container = get_container()
    return container.get_service(indicator_class)(name=name, **kwargs)


def create_strategy(name: str, strategy_class: Type[BaseStrategy], config: Dict[str, Any], **kwargs) -> BaseStrategy:
    """Create a strategy instance with dependency injection."""
    container = get_container()
    return container.get_service(strategy_class)(name=name, config=config, **kwargs)


def create_engine(name: str, engine_class: Type[BaseEngine], config: Dict[str, Any], **kwargs) -> BaseEngine:
    """Create an engine instance with dependency injection."""
    container = get_container()
    return container.get_service(engine_class)(name=name, config=config, **kwargs)


@dataclass
class IndicatorSignal:
    """Rich signal output for augmented indicators"""
    value_raw: float
    signal_type: str  # e.g., "BULLISH", "BEARISH", "NEUTRAL"
    composite_confidence: float  # 0.0 to 1.0
    confidence_components: Dict[str, float]
    suggested_sl: float
    suggested_tp: float
    timestamp: datetime
    additional_metadata: Optional[Dict[str, Any]] = None


class AugmentedIndicator(BaseIndicator):
    """
    Institutional-grade augmented indicator base class.

    Extends BaseIndicator with the 5-pillar institutional architecture:
    1. Volume Integration & Confirmation
    2. Market Regime Adaptation
    3. Multi-Timeframe Convergence Analysis
    4. Smart Money & Microstructure Proxies
    5. Automated Risk Management Factory

    All technical indicators should inherit from this class to provide rich,
    probabilistic signal outputs instead of simple values.
    """

    def __init__(self, name: str, timeframe: str = "1m",
                 container: Optional[DependencyInjectionContainer] = None):
        super().__init__(name, timeframe, container)
        self._current_signal: Optional[IndicatorSignal] = None

    @property
    def value_meta(self) -> Optional[IndicatorSignal]:
        """Return the current rich signal output."""
        return self._current_signal

    def update(self, price: float, volume: float, high: float, low: float,
               timestamp: Optional[datetime] = None) -> Optional[IndicatorSignal]:
        """
        Update the indicator with new price/volume data and generate signal.

        Args:
            price: Current closing price
            volume: Current volume
            high: Current high price
            low: Current low price
            timestamp: Current timestamp

        Returns:
            IndicatorSignal if generated, None otherwise
        """
        # This should be implemented by subclasses
        raise NotImplementedError("Subclasses must implement update method")

    def _calculate_volume_score(self, current_volume: float, volume_ma: float,
                               min_threshold: float = 1.2) -> float:
        """Calculate volume confirmation score."""
        if volume_ma <= 0:
            return 0.5
        volume_ratio = current_volume / volume_ma
        return min(volume_ratio / min_threshold, 2.0)  # Cap at 2.0

    def _calculate_regime_score(self, price: float, trend_indicator: float,
                               volatility: float) -> float:
        """Calculate market regime adaptation score."""
        # Simplified regime scoring
        trend_alignment = 1.0 if (trend_indicator > 0 and price > trend_indicator) else 0.7
        volatility_factor = min(volatility * 100, 1.0)  # Normalize high volatility
        return (trend_alignment + volatility_factor) / 2

    def _calculate_mtf_score(self, current_signal: str, higher_tf_signals: List[str]) -> float:
        """Calculate multi-timeframe convergence score."""
        if not higher_tf_signals:
            return 0.8  # Default neutral score

        matching_signals = sum(1 for sig in higher_tf_signals if sig == current_signal)
        return matching_signals / len(higher_tf_signals)

    def _calculate_smart_money_score(self, order_flow_data: Optional[Dict] = None) -> float:
        """Calculate smart money/microstructure proxy score."""
        # Placeholder for order flow analysis
        # Would analyze tick data, order book imbalance, etc.
        return 0.8  # Default neutral score

    def _calculate_risk_parameters(self, entry_price: float, atr: float,
                                 risk_reward_ratio: float = 2.0) -> Tuple[float, float]:
        """Calculate stop loss and take profit levels."""
        if atr <= 0:
            atr = entry_price * 0.02  # Default 2% ATR

        stop_loss_distance = atr * 1.5
        take_profit_distance = stop_loss_distance * risk_reward_ratio

        # For long positions
        stop_loss = entry_price - stop_loss_distance
        take_profit = entry_price + take_profit_distance

        return stop_loss, take_profit

    def _combine_confidence_scores(self, scores: Dict[str, float],
                                 weights: Optional[Dict[str, float]] = None) -> float:
        """Combine multiple confidence scores into composite score."""
        if not scores:
            return 0.5

        if weights is None:
            # Equal weights
            weights = {k: 1.0 / len(scores) for k in scores.keys()}

        composite = sum(weights.get(k, 0) * v for k, v in scores.items())
        return min(max(composite, 0.0), 1.0)  # Clamp to [0, 1]