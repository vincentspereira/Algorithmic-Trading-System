"""
Async Event System for Institutional-Grade Trading System.

This module provides a comprehensive event-driven architecture that enables:
- Asynchronous event publishing and subscription
- Event filtering and routing
- Event persistence and replay
- Event-driven processing pipelines
- Real-time event streaming
- Event correlation and aggregation
- Performance monitoring and metrics
- Fault-tolerant event handling
- Distributed event processing

The event system serves as the nervous system of the trading platform,
enabling reactive, real-time responses to market events and system changes.
"""

import asyncio
import json
import threading
import time
import uuid
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from weakref import WeakSet

import aiofiles
from loguru import logger

from .dependency_injection import (
    DependencyInjectionContainer,
    get_container,
    injectable,
    singleton,
    ServiceLifetime
)


class EventPriority(Enum):
    """Event priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class EventType(Enum):
    """Standard event types."""
    MARKET_DATA = "market_data"
    SIGNAL_GENERATED = "signal_generated"
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    POSITION_UPDATED = "position_updated"
    STRATEGY_STATE_CHANGED = "strategy_state_changed"
    INDICATOR_UPDATED = "indicator_updated"
    RISK_LIMIT_BREACHED = "risk_limit_breached"
    SYSTEM_HEALTH_CHANGED = "system_health_changed"
    CONFIGURATION_CHANGED = "configuration_changed"
    PLUGIN_LOADED = "plugin_loaded"
    PERFORMANCE_METRIC = "performance_metric"
    ERROR_OCCURRED = "error_occurred"
    CUSTOM = "custom"


@dataclass
class Event:
    """Event data structure."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.CUSTOM
    timestamp: float = field(default_factory=time.time)
    source: str = ""
    priority: EventPriority = EventPriority.NORMAL
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    parent_event_id: Optional[str] = None
    ttl: Optional[float] = None  # Time to live in seconds

    def is_expired(self) -> bool:
        """Check if event has expired."""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp > self.ttl

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "source": self.source,
            "priority": self.priority.value,
            "data": self.data,
            "metadata": self.metadata,
            "correlation_id": self.correlation_id,
            "parent_event_id": self.parent_event_id,
            "ttl": self.ttl
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary."""
        event_type = EventType(data.get("event_type", "custom"))
        priority = EventPriority(data.get("priority", "normal"))

        return cls(
            event_id=data.get("event_id", str(uuid.uuid4())),
            event_type=event_type,
            timestamp=data.get("timestamp", time.time()),
            source=data.get("source", ""),
            priority=priority,
            data=data.get("data", {}),
            metadata=data.get("metadata", {}),
            correlation_id=data.get("correlation_id"),
            parent_event_id=data.get("parent_event_id"),
            ttl=data.get("ttl")
        )


@dataclass
class EventSubscription:
    """Event subscription configuration."""
    subscriber_id: str
    event_types: Set[EventType]
    filter_func: Optional[Callable[[Event], bool]] = None
    priority: EventPriority = EventPriority.NORMAL
    is_active: bool = True
    created_at: float = field(default_factory=time.time)
    last_triggered: Optional[float] = None
    trigger_count: int = 0


@dataclass
class EventMetrics:
    """Event system performance metrics."""
    total_events_published: int = 0
    total_events_processed: int = 0
    total_subscriptions: int = 0
    average_processing_time: float = 0.0
    events_per_second: float = 0.0
    error_count: int = 0
    queue_size: int = 0
    last_event_timestamp: Optional[float] = None


class EventHandler(ABC):
    """Abstract base class for event handlers."""

    @abstractmethod
    async def handle_event(self, event: Event) -> None:
        """Handle an event asynchronously."""
        pass

    @property
    @abstractmethod
    def supported_event_types(self) -> Set[EventType]:
        """Return set of supported event types."""
        pass

    @property
    @abstractmethod
    def handler_id(self) -> str:
        """Return unique handler identifier."""
        pass


class EventFilter:
    """Event filtering and routing logic."""

    def __init__(self):
        self._filters: Dict[str, Callable[[Event], bool]] = {}

    def add_filter(self, filter_id: str, filter_func: Callable[[Event], bool]):
        """Add a filter function."""
        self._filters[filter_id] = filter_func

    def remove_filter(self, filter_id: str):
        """Remove a filter function."""
        self._filters.pop(filter_id, None)

    def apply_filters(self, event: Event) -> bool:
        """Apply all filters to an event."""
        for filter_func in self._filters.values():
            if not filter_func(event):
                return False
        return True


@injectable
@singleton
class EventBus:
    """
    Advanced Event Bus for Institutional-Grade Trading System.

    Features:
    - Asynchronous event publishing and subscription
    - Event filtering and routing
    - Event persistence and replay
    - Performance monitoring and metrics
    - Fault-tolerant event handling
    - Thread-safe operations
    - Event correlation and aggregation
    """

    def __init__(self, container: Optional[DependencyInjectionContainer] = None):
        self._container = container or get_container()
        self._subscriptions: Dict[str, EventSubscription] = {}
        self._handlers: Dict[str, EventHandler] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self._processing_task: Optional[asyncio.Task] = None
        self._lock = threading.RLock()
        self._metrics = EventMetrics()
        self._filter = EventFilter()
        self._event_history: List[Event] = []
        self._max_history_size = 10000
        self._persistence_enabled = False
        self._persistence_path: Optional[str] = None

        # Background tasks
        self._background_tasks: Set[asyncio.Task] = set()

    async def initialize(self) -> bool:
        """Initialize the event bus."""
        try:
            self._processing_task = asyncio.create_task(self._event_processing_loop())
            logger.info("Event bus initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize event bus: {e}")
            return False

    async def shutdown(self) -> bool:
        """Shutdown the event bus."""
        try:
            # Cancel processing task
            if self._processing_task and not self._processing_task.done():
                self._processing_task.cancel()

            # Cancel background tasks
            for task in self._background_tasks:
                if not task.done():
                    task.cancel()

            # Wait for tasks to complete
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

            logger.info("Event bus shutdown successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to shutdown event bus: {e}")
            return False

    async def publish_event(self, event: Event) -> bool:
        """
        Publish an event to the bus.

        Args:
            event: Event to publish

        Returns:
            True if published successfully, False otherwise
        """
        try:
            # Check if event is expired
            if event.is_expired():
                logger.warning(f"Discarding expired event: {event.event_id}")
                return False

            # Add to queue
            await self._event_queue.put(event)

            # Update metrics
            with self._lock:
                self._metrics.total_events_published += 1
                self._metrics.last_event_timestamp = event.timestamp
                self._metrics.queue_size = self._event_queue.qsize()

            # Add to history
            self._add_to_history(event)

            # Persist if enabled
            if self._persistence_enabled:
                await self._persist_event(event)

            logger.debug(f"Event published: {event.event_type.value} from {event.source}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            with self._lock:
                self._metrics.error_count += 1
            return False

    def subscribe(self, subscriber_id: str, event_types: Union[EventType, Set[EventType]],
                  handler: Optional[Callable[[Event], None]] = None,
                  filter_func: Optional[Callable[[Event], bool]] = None,
                  priority: EventPriority = EventPriority.NORMAL) -> str:
        """
        Subscribe to events.

        Args:
            subscriber_id: Unique subscriber identifier
            event_types: Event types to subscribe to
            handler: Optional event handler function
            filter_func: Optional event filter function
            priority: Subscription priority

        Returns:
            Subscription ID
        """
        if isinstance(event_types, EventType):
            event_types = {event_types}

        subscription = EventSubscription(
            subscriber_id=subscriber_id,
            event_types=event_types,
            filter_func=filter_func,
            priority=priority
        )

        with self._lock:
            self._subscriptions[subscriber_id] = subscription
            self._metrics.total_subscriptions = len(self._subscriptions)

        if handler:
            # Register handler if provided
            self.register_handler(subscriber_id, handler, event_types)

        logger.info(f"Subscription created: {subscriber_id} for {len(event_types)} event types")
        return subscriber_id

    def unsubscribe(self, subscriber_id: str) -> bool:
        """
        Unsubscribe from events.

        Args:
            subscriber_id: Subscriber identifier

        Returns:
            True if unsubscribed successfully, False otherwise
        """
        with self._lock:
            if subscriber_id in self._subscriptions:
                del self._subscriptions[subscriber_id]
                self._metrics.total_subscriptions = len(self._subscriptions)

                # Remove handler if exists
                self._handlers.pop(subscriber_id, None)

                logger.info(f"Unsubscribed: {subscriber_id}")
                return True

        return False

    def register_handler(self, handler_id: str, handler: Callable[[Event], None],
                        event_types: Set[EventType]):
        """Register an event handler."""
        # Create a simple event handler wrapper
        async def async_handler(event: Event):
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                # Run sync handler in thread pool
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, handler, event)

        handler_obj = SimpleEventHandler(handler_id, event_types, async_handler)

        with self._lock:
            self._handlers[handler_id] = handler_obj

    def unregister_handler(self, handler_id: str) -> bool:
        """Unregister an event handler."""
        with self._lock:
            if handler_id in self._handlers:
                del self._handlers[handler_id]
                return True
        return False

    async def get_event_history(self, event_type: Optional[EventType] = None,
                               limit: int = 100) -> List[Event]:
        """Get event history."""
        with self._lock:
            history = self._event_history

            if event_type:
                history = [e for e in history if e.event_type == event_type]

            return history[-limit:]

    def get_metrics(self) -> Dict[str, Any]:
        """Get event system metrics."""
        with self._lock:
            return {
                "total_events_published": self._metrics.total_events_published,
                "total_events_processed": self._metrics.total_events_processed,
                "total_subscriptions": self._metrics.total_subscriptions,
                "average_processing_time": self._metrics.average_processing_time,
                "events_per_second": self._metrics.events_per_second,
                "error_count": self._metrics.error_count,
                "queue_size": self._metrics.queue_size,
                "uptime": time.time() - (self._metrics.last_event_timestamp or time.time())
            }

    def enable_persistence(self, persistence_path: str):
        """Enable event persistence."""
        self._persistence_enabled = True
        self._persistence_path = persistence_path
        logger.info(f"Event persistence enabled: {persistence_path}")

    def disable_persistence(self):
        """Disable event persistence."""
        self._persistence_enabled = False
        self._persistence_path = None
        logger.info("Event persistence disabled")

    async def replay_events(self, start_time: float, end_time: Optional[float] = None) -> List[Event]:
        """Replay events from history."""
        with self._lock:
            events = [e for e in self._event_history
                     if e.timestamp >= start_time and
                     (end_time is None or e.timestamp <= end_time)]

        # Publish events for replay
        for event in events:
            await self.publish_event(event)

        return events

    async def _event_processing_loop(self):
        """Main event processing loop."""
        logger.info("Event processing loop started")

        try:
            while True:
                # Get event from queue
                event = await self._event_queue.get()

                try:
                    start_time = time.time()

                    # Process event
                    await self._process_event(event)

                    # Update metrics
                    processing_time = time.time() - start_time
                    with self._lock:
                        self._metrics.total_events_processed += 1
                        self._metrics.average_processing_time = (
                            (self._metrics.average_processing_time * (self._metrics.total_events_processed - 1)) +
                            processing_time
                        ) / self._metrics.total_events_processed
                        self._metrics.queue_size = self._event_queue.qsize()

                except Exception as e:
                    logger.error(f"Error processing event {event.event_id}: {e}")
                    with self._lock:
                        self._metrics.error_count += 1
                finally:
                    self._event_queue.task_done()

        except asyncio.CancelledError:
            logger.info("Event processing loop cancelled")
        except Exception as e:
            logger.error(f"Fatal error in event processing loop: {e}")

    async def _process_event(self, event: Event):
        """Process a single event."""
        # Apply filters
        if not self._filter.apply_filters(event):
            return

        # Find matching subscriptions
        matching_subscriptions = []
        with self._lock:
            for subscription in self._subscriptions.values():
                if (subscription.is_active and
                    event.event_type in subscription.event_types and
                    (subscription.filter_func is None or subscription.filter_func(event))):
                    matching_subscriptions.append(subscription)

        # Sort by priority
        matching_subscriptions.sort(key=lambda s: s.priority.value, reverse=True)

        # Process subscriptions
        tasks = []
        for subscription in matching_subscriptions:
            # Update subscription metrics
            subscription.last_triggered = time.time()
            subscription.trigger_count += 1

            # Get handler
            handler = self._handlers.get(subscription.subscriber_id)
            if handler:
                task = asyncio.create_task(self._dispatch_event(handler, event))
                tasks.append(task)

        # Wait for all handlers to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _dispatch_event(self, handler: EventHandler, event: Event):
        """Dispatch event to handler."""
        try:
            await handler.handle_event(event)
        except Exception as e:
            logger.error(f"Error in event handler {handler.handler_id}: {e}")

    def _add_to_history(self, event: Event):
        """Add event to history."""
        with self._lock:
            self._event_history.append(event)

            # Maintain max history size
            if len(self._event_history) > self._max_history_size:
                self._event_history.pop(0)

    async def _persist_event(self, event: Event):
        """Persist event to storage."""
        if not self._persistence_path:
            return

        try:
            event_data = event.to_dict()
            async with aiofiles.open(self._persistence_path, 'a', encoding='utf-8') as f:
                await f.write(json.dumps(event_data) + '\n')
        except Exception as e:
            logger.error(f"Failed to persist event: {e}")


class SimpleEventHandler(EventHandler):
    """Simple event handler implementation."""

    def __init__(self, handler_id: str, event_types: Set[EventType],
                 handler_func: Callable[[Event], None]):
        self._handler_id = handler_id
        self._event_types = event_types
        self._handler_func = handler_func

    async def handle_event(self, event: Event) -> None:
        """Handle an event."""
        await self._handler_func(event)

    @property
    def supported_event_types(self) -> Set[EventType]:
        """Return supported event types."""
        return self._event_types

    @property
    def handler_id(self) -> str:
        """Return handler ID."""
        return self._handler_id


class EventAggregator:
    """Event aggregation and correlation engine."""

    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
        self._event_groups: Dict[str, List[Event]] = {}
        self._correlation_rules: Dict[str, Callable[[List[Event]], Optional[Event]]] = {}

    def add_correlation_rule(self, rule_id: str, rule_func: Callable[[List[Event]], Optional[Event]]):
        """Add an event correlation rule."""
        self._correlation_rules[rule_id] = rule_func

    def remove_correlation_rule(self, rule_id: str):
        """Remove an event correlation rule."""
        self._correlation_rules.pop(rule_id, None)

    async def process_event_group(self, group_id: str) -> Optional[Event]:
        """Process an event group with correlation rules."""
        if group_id not in self._event_groups:
            return None

        events = self._event_groups[group_id]

        for rule_func in self._correlation_rules.values():
            correlated_event = rule_func(events)
            if correlated_event:
                return correlated_event

        return None


# Global event bus instance
_event_bus = EventBus()


def get_event_bus() -> EventBus:
    """Get the global event bus."""
    return _event_bus


# Convenience functions
async def publish_event(event: Event) -> bool:
    """Publish an event using the global event bus."""
    return await _event_bus.publish_event(event)


def subscribe(subscriber_id: str, event_types: Union[EventType, Set[EventType]],
              handler: Optional[Callable[[Event], None]] = None,
              filter_func: Optional[Callable[[Event], bool]] = None,
              priority: EventPriority = EventPriority.NORMAL) -> str:
    """Subscribe to events using the global event bus."""
    return _event_bus.subscribe(subscriber_id, event_types, handler, filter_func, priority)


def unsubscribe(subscriber_id: str) -> bool:
    """Unsubscribe from events using the global event bus."""
    return _event_bus.unsubscribe(subscriber_id)


def create_event(event_type: EventType, source: str, data: Dict[str, Any],
                priority: EventPriority = EventPriority.NORMAL,
                correlation_id: Optional[str] = None) -> Event:
    """Create a new event."""
    return Event(
        event_type=event_type,
        source=source,
        priority=priority,
        data=data,
        correlation_id=correlation_id
    )