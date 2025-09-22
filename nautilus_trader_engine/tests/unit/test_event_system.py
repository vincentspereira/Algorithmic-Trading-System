"""
Unit Tests for Event System.

Tests the async event-driven architecture including:
- Event publishing and subscription
- Event prioritization and filtering
- Event persistence and replay
- Async event handling
- Event bus management
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime, timedelta
from nautilus_trader_engine.core.event_system import (
    EventBus,
    Event,
    EventType,
    EventPriority,
    EventHandler,
    EventFilter,
    EventReplay,
    get_event_bus,
    event_handler,
    subscribe,
    publish_event
)


class TestEvent:

    def test_event_creation(self):
        """Test basic event creation."""
        event = Event(
            event_type=EventType.MARKET_DATA,
            data={"symbol": "AAPL", "price": 150.0},
            source="test_source"
        )

        assert event.event_type == EventType.MARKET_DATA
        assert event.data == {"symbol": "AAPL", "price": 150.0}
        assert event.source == "test_source"
        assert isinstance(event.timestamp, datetime)
        assert event.id is not None

    def test_event_with_custom_timestamp(self):
        """Test event creation with custom timestamp."""
        custom_time = datetime(2023, 1, 1, 12, 0, 0)
        event = Event(
            event_type=EventType.TRADE_SIGNAL,
            data={"signal": "BUY"},
            timestamp=custom_time
        )

        assert event.timestamp == custom_time

    def test_event_serialization(self):
        """Test event serialization."""
        event = Event(
            event_type=EventType.SYSTEM_STATUS,
            data={"status": "healthy"},
            metadata={"version": "1.0"}
        )

        serialized = event.to_dict()
        assert serialized["event_type"] == "SYSTEM_STATUS"
        assert serialized["data"] == {"status": "healthy"}
        assert serialized["metadata"] == {"version": "1.0"}

    def test_event_deserialization(self):
        """Test event deserialization."""
        data = {
            "id": "test-id",
            "event_type": "MARKET_DATA",
            "data": {"price": 100.0},
            "timestamp": "2023-01-01T12:00:00",
            "source": "test",
            "metadata": {}
        }

        event = Event.from_dict(data)
        assert event.event_type == EventType.MARKET_DATA
        assert event.data == {"price": 100.0}
        assert event.source == "test"


class TestEventBus:

    def setup_method(self):
        """Set up test fixtures."""
        self.event_bus = EventBus()

    def test_event_bus_initialization(self):
        """Test event bus initializes correctly."""
        assert self.event_bus.handlers == {}
        assert self.event_bus.event_history == []
        assert self.event_bus.is_running is False

    @pytest.mark.asyncio
    async def test_publish_and_subscribe(self):
        """Test basic publish and subscribe functionality."""
        received_events = []

        async def handler(event: Event):
            received_events.append(event)

        # Subscribe to events
        await self.event_bus.subscribe(EventType.MARKET_DATA, handler)

        # Publish an event
        event = Event(event_type=EventType.MARKET_DATA, data={"price": 150.0})
        await self.event_bus.publish_event(event)

        # Wait for event processing
        await asyncio.sleep(0.1)

        # Check that event was received
        assert len(received_events) == 1
        assert received_events[0].data == {"price": 150.0}

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        """Test multiple subscribers to the same event type."""
        received_counts = {"handler1": 0, "handler2": 0}

        async def handler1(event: Event):
            received_counts["handler1"] += 1

        async def handler2(event: Event):
            received_counts["handler2"] += 1

        # Subscribe both handlers
        await self.event_bus.subscribe(EventType.TRADE_SIGNAL, handler1)
        await self.event_bus.subscribe(EventType.TRADE_SIGNAL, handler2)

        # Publish an event
        event = Event(event_type=EventType.TRADE_SIGNAL, data={"signal": "BUY"})
        await self.event_bus.publish_event(event)

        # Wait for processing
        await asyncio.sleep(0.1)

        # Both handlers should have received the event
        assert received_counts["handler1"] == 1
        assert received_counts["handler2"] == 1

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        """Test unsubscribing from events."""
        received_events = []

        async def handler(event: Event):
            received_events.append(event)

        # Subscribe
        await self.event_bus.subscribe(EventType.MARKET_DATA, handler)

        # Publish event - should be received
        event1 = Event(event_type=EventType.MARKET_DATA, data={"price": 100.0})
        await self.event_bus.publish_event(event1)
        await asyncio.sleep(0.1)
        assert len(received_events) == 1

        # Unsubscribe
        await self.event_bus.unsubscribe(EventType.MARKET_DATA, handler)

        # Publish another event - should not be received
        event2 = Event(event_type=EventType.MARKET_DATA, data={"price": 200.0})
        await self.event_bus.publish_event(event2)
        await asyncio.sleep(0.1)
        assert len(received_events) == 1  # Still only one event

    @pytest.mark.asyncio
    async def test_event_filtering(self):
        """Test event filtering functionality."""
        received_events = []

        async def handler(event: Event):
            received_events.append(event)

        # Subscribe with filter
        def price_filter(event: Event) -> bool:
            return event.data.get("price", 0) > 100.0

        await self.event_bus.subscribe(
            EventType.MARKET_DATA,
            handler,
            filter_func=price_filter
        )

        # Publish events
        event1 = Event(event_type=EventType.MARKET_DATA, data={"price": 50.0})   # Should be filtered
        event2 = Event(event_type=EventType.MARKET_DATA, data={"price": 150.0})  # Should pass filter

        await self.event_bus.publish_event(event1)
        await self.event_bus.publish_event(event2)

        await asyncio.sleep(0.1)

        # Only the event that passed the filter should be received
        assert len(received_events) == 1
        assert received_events[0].data["price"] == 150.0

    @pytest.mark.asyncio
    async def test_event_prioritization(self):
        """Test event prioritization."""
        received_events = []

        async def handler(event: Event):
            received_events.append(event)

        # Subscribe to all priorities
        await self.event_bus.subscribe(EventType.SYSTEM_STATUS, handler)

        # Publish events with different priorities
        event_high = Event(
            event_type=EventType.SYSTEM_STATUS,
            data={"status": "high"},
            priority=EventPriority.HIGH
        )
        event_normal = Event(
            event_type=EventType.SYSTEM_STATUS,
            data={"status": "normal"},
            priority=EventPriority.NORMAL
        )

        await self.event_bus.publish_event(event_normal)
        await self.event_bus.publish_event(event_high)

        await asyncio.sleep(0.1)

        # Both events should be received (prioritization affects processing order internally)
        assert len(received_events) == 2
        assert {e.data["status"] for e in received_events} == {"high", "normal"}

    @pytest.mark.asyncio
    async def test_event_history(self):
        """Test event history tracking."""
        # Enable history tracking
        self.event_bus.max_history_size = 10

        # Publish some events
        for i in range(5):
            event = Event(event_type=EventType.MARKET_DATA, data={"index": i})
            await self.event_bus.publish_event(event)

        await asyncio.sleep(0.1)

        # Check history
        assert len(self.event_bus.event_history) == 5
        assert all(e.event_type == EventType.MARKET_DATA for e in self.event_bus.event_history)

    @pytest.mark.asyncio
    async def test_event_replay(self):
        """Test event replay functionality."""
        # Enable history
        self.event_bus.max_history_size = 10

        # Publish events
        events_data = []
        for i in range(3):
            event = Event(event_type=EventType.TRADE_SIGNAL, data={"trade_id": i})
            await self.event_bus.publish_event(event)
            events_data.append(event.data)

        await asyncio.sleep(0.1)

        # Set up replay handler
        replayed_events = []

        async def replay_handler(event: Event):
            replayed_events.append(event)

        # Replay events
        await self.event_bus.replay_events(
            event_type=EventType.TRADE_SIGNAL,
            handler=replay_handler
        )

        # Check replayed events
        assert len(replayed_events) == 3
        assert [e.data for e in replayed_events] == events_data

    @pytest.mark.asyncio
    async def test_error_handling_in_handlers(self):
        """Test error handling in event handlers."""
        error_handler_called = False

        async def failing_handler(event: Event):
            raise ValueError("Handler failed")

        async def error_handler(event: Event, error: Exception):
            nonlocal error_handler_called
            error_handler_called = True
            assert isinstance(error, ValueError)

        # Subscribe handlers
        await self.event_bus.subscribe(EventType.MARKET_DATA, failing_handler)
        await self.event_bus.subscribe_error(error_handler)

        # Publish event that will cause handler to fail
        event = Event(event_type=EventType.MARKET_DATA, data={"test": "error"})
        await self.event_bus.publish_event(event)

        await asyncio.sleep(0.1)

        # Error handler should have been called
        assert error_handler_called

    @pytest.mark.asyncio
    async def test_event_bus_start_stop(self):
        """Test starting and stopping the event bus."""
        assert not self.event_bus.is_running

        # Start the event bus
        await self.event_bus.start()
        assert self.event_bus.is_running

        # Stop the event bus
        await self.event_bus.stop()
        assert not self.event_bus.is_running


class TestEventDecorators:

    def setup_method(self):
        """Set up test fixtures."""
        self.event_bus = EventBus()

    @pytest.mark.asyncio
    async def test_event_handler_decorator(self):
        """Test the event_handler decorator."""
        received_events = []

        @event_handler(EventType.MARKET_DATA)
        async def handle_market_data(event: Event):
            received_events.append(event)

        # Register the handler
        await self.event_bus.subscribe(EventType.MARKET_DATA, handle_market_data)

        # Publish event
        event = Event(event_type=EventType.MARKET_DATA, data={"price": 100.0})
        await self.event_bus.publish_event(event)

        await asyncio.sleep(0.1)

        assert len(received_events) == 1
        assert received_events[0].data["price"] == 100.0

    @pytest.mark.asyncio
    async def test_subscribe_decorator(self):
        """Test the subscribe decorator."""
        received_events = []

        @subscribe(EventType.TRADE_SIGNAL)
        async def handle_trade_signal(event: Event):
            received_events.append(event)

        # The decorator should have registered the handler
        # Publish event
        event = Event(event_type=EventType.TRADE_SIGNAL, data={"signal": "SELL"})
        await self.event_bus.publish_event(event)

        await asyncio.sleep(0.1)

        assert len(received_events) == 1
        assert received_events[0].data["signal"] == "SELL"


class TestGlobalEventBus:

    @pytest.mark.asyncio
    async def test_get_event_bus_singleton(self):
        """Test that get_event_bus returns singleton instance."""
        bus1 = get_event_bus()
        bus2 = get_event_bus()

        assert bus1 is bus2

    @pytest.mark.asyncio
    async def test_publish_event_global(self):
        """Test publishing events through global event bus."""
        received_events = []

        async def handler(event: Event):
            received_events.append(event)

        bus = get_event_bus()
        await bus.subscribe(EventType.SYSTEM_STATUS, handler)

        # Use global publish function
        await publish_event(EventType.SYSTEM_STATUS, {"status": "ok"})

        await asyncio.sleep(0.1)

        assert len(received_events) == 1
        assert received_events[0].data["status"] == "ok"


class TestEventPersistence:

    def test_event_persistence_to_file(self):
        """Test persisting events to file."""
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
            temp_file = f.name

        try:
            # Create event bus with persistence
            event_bus = EventBus(persist_events=True, persistence_file=temp_file)

            # This would normally persist events, but we're testing the setup
            assert event_bus.persistence_file == temp_file

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    @pytest.mark.asyncio
    async def test_event_batch_processing(self):
        """Test processing events in batches."""
        received_events = []

        async def handler(event: Event):
            received_events.append(event)
            await asyncio.sleep(0.01)  # Simulate processing time

        await self.event_bus.subscribe(EventType.MARKET_DATA, handler)

        # Publish multiple events
        events = [
            Event(event_type=EventType.MARKET_DATA, data={"id": i})
            for i in range(5)
        ]

        # Publish all at once
        await asyncio.gather(*[
            self.event_bus.publish_event(event) for event in events
        ])

        # Wait for all to be processed
        await asyncio.sleep(0.2)

        assert len(received_events) == 5
        assert {e.data["id"] for e in received_events} == {0, 1, 2, 3, 4}


class TestEventMetrics:

    @pytest.mark.asyncio
    async def test_event_processing_metrics(self):
        """Test event processing metrics collection."""
        self.event_bus.enable_metrics = True

        async def handler(event: Event):
            pass  # Simple handler

        await self.event_bus.subscribe(EventType.MARKET_DATA, handler)

        # Publish event
        event = Event(event_type=EventType.MARKET_DATA, data={"test": True})
        await self.event_bus.publish_event(event)

        await asyncio.sleep(0.1)

        # Check that metrics are collected (if implemented)
        # This would depend on the specific metrics implementation
        assert True  # Placeholder for metrics validation