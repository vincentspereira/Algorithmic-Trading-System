"""
Async Event System for Nautilus Trader Engine
Provides a robust event-driven architecture for real-time processing.
"""

import asyncio
import threading
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Callable, Optional, Set, Awaitable, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor
import queue
import weakref

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """Event priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Event:
    """Base event class."""
    event_type: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: str = ""
    priority: EventPriority = EventPriority.NORMAL
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class EventHandler(ABC):
    """Base class for event handlers."""

    @abstractmethod
    async def handle_event(self, event: Event) -> None:
        """Handle an event asynchronously."""
        pass

    @property
    @abstractmethod
    def event_types(self) -> List[str]:
        """Return list of event types this handler can process."""
        pass


class SyncEventHandler(EventHandler):
    """Synchronous event handler wrapper."""

    def __init__(self, sync_handler: Callable[[Event], None], event_types: List[str]):
        self.sync_handler = sync_handler
        self._event_types = event_types

    async def handle_event(self, event: Event) -> None:
        """Handle event by running sync handler in thread pool."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.sync_handler, event)

    @property
    def event_types(self) -> List[str]:
        return self._event_types


class EventBus:
    """
    Advanced event bus with features:
    - Async event processing
    - Event filtering and routing
    - Dead letter queue
    - Event replay
    - Metrics and monitoring
    - Circuit breaker pattern
    """

    def __init__(self, max_workers: int = 10, queue_size: int = 1000):
        self.handlers: Dict[str, List[weakref.ReferenceType[EventHandler]]] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.event_queue = asyncio.Queue(maxsize=queue_size)
        self.dead_letter_queue: List[Event] = []
        self.event_history: List[Event] = []
        self.max_history_size = 10000
        self.processing_task: Optional[asyncio.Task] = None
        self.is_running = False
        self.metrics = EventMetrics()
        self.circuit_breaker = CircuitBreaker()

    async def start(self) -> None:
        """Start the event bus."""
        if self.is_running:
            return

        self.is_running = True
        self.processing_task = asyncio.create_task(self._process_events())
        logger.info("Event bus started")

    async def stop(self) -> None:
        """Stop the event bus."""
        if not self.is_running:
            return

        self.is_running = False
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass

        self.executor.shutdown(wait=True)
        logger.info("Event bus stopped")

    def register_handler(self, handler: EventHandler) -> None:
        """Register an event handler."""
        for event_type in handler.event_types:
            if event_type not in self.handlers:
                self.handlers[event_type] = []

            # Use weak reference to prevent memory leaks
            self.handlers[event_type].append(weakref.ref(handler))
            logger.debug(f"Registered handler for event type: {event_type}")

    def unregister_handler(self, handler: EventHandler) -> None:
        """Unregister an event handler."""
        for event_type in handler.event_types:
            if event_type in self.handlers:
                # Remove dead references and the specific handler
                self.handlers[event_type] = [
                    ref for ref in self.handlers[event_type]
                    if ref() is not None and ref() is not handler
                ]

    async def publish(self, event: Event) -> None:
        """Publish an event to the bus."""
        if not self.is_running:
            logger.warning("Event bus is not running, event dropped")
            return

        try:
            await self.event_queue.put(event)
            self.metrics.record_published_event(event)
        except asyncio.QueueFull:
            logger.warning("Event queue is full, moving to dead letter queue")
            self.dead_letter_queue.append(event)
            self.metrics.record_dead_letter_event(event)

    async def _process_events(self) -> None:
        """Process events from the queue."""
        while self.is_running:
            try:
                event = await self.event_queue.get()

                # Store in history
                self._add_to_history(event)

                # Process the event
                await self._process_event(event)

                self.event_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing event: {e}")
                self.metrics.record_processing_error()

    async def _process_event(self, event: Event) -> None:
        """Process a single event."""
        if event.event_type not in self.handlers:
            logger.debug(f"No handlers registered for event type: {event.event_type}")
            return

        # Get valid handlers (filter out dead references)
        valid_handlers = [
            ref() for ref in self.handlers[event.event_type]
            if ref() is not None
        ]

        if not valid_handlers:
            logger.debug(f"No valid handlers for event type: {event.event_type}")
            return

        # Process with circuit breaker
        if not self.circuit_breaker.can_proceed():
            logger.warning("Circuit breaker is open, skipping event processing")
            return

        # Process event with all handlers
        tasks = []
        for handler in valid_handlers:
            try:
                task = asyncio.create_task(self._safe_handle_event(handler, event))
                tasks.append(task)
            except Exception as e:
                logger.error(f"Error creating task for handler: {e}")
                self.metrics.record_handler_error()

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_handle_event(self, handler: EventHandler, event: Event) -> None:
        """Safely handle an event with error handling."""
        try:
            start_time = time.time()
            await handler.handle_event(event)
            processing_time = time.time() - start_time

            self.metrics.record_handler_success(processing_time)

        except Exception as e:
            logger.error(f"Error in event handler: {e}")
            self.metrics.record_handler_error()
            self.circuit_breaker.record_failure()

    def _add_to_history(self, event: Event) -> None:
        """Add event to history with size limit."""
        self.event_history.append(event)
        if len(self.event_history) > self.max_history_size:
            self.event_history.pop(0)

    def get_event_history(self, event_type: Optional[str] = None,
                         limit: int = 100) -> List[Event]:
        """Get event history, optionally filtered by type."""
        history = self.event_history
        if event_type:
            history = [e for e in history if e.event_type == event_type]

        return history[-limit:]

    def replay_events(self, event_type: Optional[str] = None,
                     start_time: Optional[float] = None) -> None:
        """Replay events from history."""
        events_to_replay = self.event_history

        if event_type:
            events_to_replay = [e for e in events_to_replay if e.event_type == event_type]

        if start_time:
            events_to_replay = [e for e in events_to_replay if e.timestamp >= start_time]

        async def replay():
            for event in events_to_replay:
                await self.publish(event)

        asyncio.create_task(replay())

    def get_dead_letter_events(self) -> List[Event]:
        """Get events in the dead letter queue."""
        return self.dead_letter_queue.copy()

    def clear_dead_letter_queue(self) -> None:
        """Clear the dead letter queue."""
        self.dead_letter_queue.clear()


@dataclass
class EventMetrics:
    """Metrics for event processing."""
    events_published: int = 0
    events_processed: int = 0
    handler_successes: int = 0
    handler_errors: int = 0
    dead_letter_events: int = 0
    processing_errors: int = 0
    total_processing_time: float = 0.0

    def record_published_event(self, event: Event) -> None:
        self.events_published += 1

    def record_processed_event(self) -> None:
        self.events_processed += 1

    def record_handler_success(self, processing_time: float) -> None:
        self.handler_successes += 1
        self.total_processing_time += processing_time

    def record_handler_error(self) -> None:
        self.handler_errors += 1

    def record_dead_letter_event(self, event: Event) -> None:
        self.dead_letter_events += 1

    def record_processing_error(self) -> None:
        self.processing_errors += 1

    def get_summary(self) -> Dict[str, Any]:
        return {
            "events_published": self.events_published,
            "events_processed": self.events_processed,
            "handler_successes": self.handler_successes,
            "handler_errors": self.handler_errors,
            "dead_letter_events": self.dead_letter_events,
            "processing_errors": self.processing_errors,
            "average_processing_time": (
                self.total_processing_time / self.handler_successes
                if self.handler_successes > 0 else 0
            ),
            "success_rate": (
                self.handler_successes / (self.handler_successes + self.handler_errors)
                if (self.handler_successes + self.handler_errors) > 0 else 0
            )
        }


@dataclass
class CircuitBreaker:
    """Circuit breaker for fault tolerance."""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    failure_count: int = 0
    last_failure_time: Optional[float] = None
    state: str = "closed"  # closed, open, half_open

    def can_proceed(self) -> bool:
        """Check if the circuit breaker allows requests."""
        if self.state == "closed":
            return True

        if self.state == "open":
            if (time.time() - (self.last_failure_time or 0)) > self.recovery_timeout:
                self.state = "half_open"
                return True
            return False

        # Half-open state
        return True

    def record_failure(self) -> None:
        """Record a failure."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning("Circuit breaker opened due to failures")

    def record_success(self) -> None:
        """Record a success."""
        if self.state == "half_open":
            self.state = "closed"
            self.failure_count = 0
            logger.info("Circuit breaker closed - service recovered")


# Global event bus instance
_event_bus = EventBus()


def get_event_bus() -> EventBus:
    """Get the global event bus."""
    return _event_bus


# Convenience functions
async def publish_event(event: Event) -> None:
    """Publish an event globally."""
    await _event_bus.publish(event)


def register_event_handler(handler: EventHandler) -> None:
    """Register an event handler globally."""
    _event_bus.register_handler(handler)


def unregister_event_handler(handler: EventHandler) -> None:
    """Unregister an event handler globally."""
    _event_bus.unregister_handler(handler)


# Example event handlers
class MarketDataHandler(EventHandler):
    """Example market data event handler."""

    @property
    def event_types(self) -> List[str]:
        return ["market_data", "price_update"]

    async def handle_event(self, event: Event) -> None:
        logger.info(f"Processing market data: {event.data}")


class TradingSignalHandler(EventHandler):
    """Example trading signal event handler."""

    @property
    def event_types(self) -> List[str]:
        return ["trading_signal", "order_signal"]

    async def handle_event(self, event: Event) -> None:
        logger.info(f"Processing trading signal: {event.data}")


# Example usage
async def example_usage():
    """Example of using the event system."""
    # Start the event bus
    await _event_bus.start()

    # Register handlers
    register_event_handler(MarketDataHandler())
    register_event_handler(TradingSignalHandler())

    # Publish events
    await publish_event(Event(
        event_type="market_data",
        data={"symbol": "AAPL", "price": 150.0},
        source="market_feed"
    ))

    await publish_event(Event(
        event_type="trading_signal",
        data={"signal": "BUY", "symbol": "AAPL", "confidence": 0.85},
        source="strategy_engine",
        priority=EventPriority.HIGH
    ))

    # Get metrics
    metrics = _event_bus.metrics.get_summary()
    print(f"Event processing metrics: {metrics}")

    # Stop the event bus
    await _event_bus.stop()


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())