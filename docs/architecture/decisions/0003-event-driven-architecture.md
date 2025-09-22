# ADR 0003: Event-Driven Architecture

## Status
Accepted

## Context
The trading system needs to handle multiple asynchronous events:

- Market data updates (high frequency)
- Signal generation events
- Order execution confirmations
- Risk limit breaches
- System health alerts
- Configuration changes

A synchronous, request-response architecture would not scale to handle the volume and variety of events in a real-time trading system.

## Decision
Implement an **event-driven architecture** with the following components:

1. **Event Bus**: Central hub for event routing and delivery
2. **Event Types**: Strongly typed event hierarchy
3. **Event Handlers**: Asynchronous event processing
4. **Event Priorities**: Priority-based event processing
5. **Event Filtering**: Selective event subscription
6. **Event Persistence**: Optional event logging and replay

## Implementation Details

### Event Hierarchy
```python
class EventType(Enum):
    MARKET_DATA = "market_data"
    SIGNAL_GENERATED = "signal_generated"
    ORDER_EXECUTED = "order_executed"
    RISK_BREACH = "risk_breach"
    SYSTEM_ALERT = "system_alert"

class Event:
    def __init__(self, event_type: EventType, data: dict, priority: EventPriority = EventPriority.NORMAL):
        self.type = event_type
        self.data = data
        self.priority = priority
        self.timestamp = datetime.now()
        self.id = uuid.uuid4()
```

### Event Bus Interface
```python
class EventBus:
    async def publish_event(self, event: Event) -> None:
        """Publish an event to all subscribers."""

    async def subscribe(self, event_type: EventType, handler: Callable, priority: EventPriority = EventPriority.NORMAL) -> None:
        """Subscribe to events of a specific type."""

    def create_event(self, event_type: EventType, source: str, data: dict) -> Event:
        """Create a new event instance."""
```

### Event Processing
```python
# Subscribe to events
await event_bus.subscribe(EventType.SIGNAL_GENERATED, process_signal)

# Publish events
event = event_bus.create_event(EventType.SIGNAL_GENERATED, "rsi_indicator", {"strength": 0.8})
await event_bus.publish_event(event)
```

## Consequences

### Positive
- **Decoupling**: Producers and consumers are loosely coupled
- **Scalability**: Can handle high event volumes
- **Extensibility**: Easy to add new event types and handlers
- **Asynchronous Processing**: Non-blocking event handling
- **Monitoring**: Built-in event tracking and metrics

### Negative
- **Complexity**: Event flow can be harder to debug
- **Ordering**: Event ordering guarantees may be complex
- **Testing**: Event-driven code can be harder to test
- **Resource Usage**: Event storage and processing overhead

### Mitigation
- Implement comprehensive logging and tracing
- Provide event replay capabilities for debugging
- Use correlation IDs for request tracking
- Implement circuit breakers for event processing
- Provide synchronous testing utilities

## Performance Considerations

### Event Throughput
- Target: 10,000+ events/second
- Implementation: Async processing with priority queues
- Monitoring: Event processing latency and throughput metrics

### Memory Management
- Event object pooling to reduce GC pressure
- Configurable event retention policies
- Memory usage monitoring and alerts

## Related ADRs
- ADR 0001: Layered Architecture Pattern
- ADR 0005: Streaming Architecture