#!/usr/bin/env python3
"""
Event Processing Integration Tests
Tests event-driven architecture, event handlers, and event processing workflows.
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import logging
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventType(Enum):
    """Event types for the trading system"""
    MARKET_DATA_UPDATE = "market_data_update"
    ORDER_CREATED = "order_created"
    ORDER_EXECUTED = "order_executed"
    ORDER_CANCELLED = "order_cancelled"
    PORTFOLIO_UPDATED = "portfolio_updated"
    RISK_ALERT = "risk_alert"
    POSITION_CHANGED = "position_changed"
    TRADE_EXECUTED = "trade_executed"
    SYSTEM_HEALTH = "system_health"
    USER_ACTION = "user_action"


@dataclass
class Event:
    """Base event class"""
    event_id: str
    event_type: EventType
    timestamp: datetime
    source: str
    data: Dict[str, Any]
    correlation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "data": self.data,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata or {}
        }


class MockEventHandler:
    """Mock event handler for testing"""
    
    def __init__(self, handler_id: str, event_types: List[EventType]):
        self.handler_id = handler_id
        self.event_types = event_types
        self.processed_events = []
        self.processing_time = 0.1
        self.success_rate = 1.0
        self.enabled = True
        
    async def handle_event(self, event: Event) -> Dict[str, Any]:
        """Handle incoming event"""
        if not self.enabled:
            raise Exception(f"Handler {self.handler_id} is disabled")
            
        if event.event_type not in self.event_types:
            raise Exception(f"Handler {self.handler_id} cannot process {event.event_type}")
            
        # Simulate processing time
        await asyncio.sleep(self.processing_time)
        
        # Simulate occasional failures
        import random
        if random.random() > self.success_rate:
            raise Exception(f"Handler {self.handler_id} processing failed")
            
        # Process the event
        result = {
            "handler_id": self.handler_id,
            "event_id": event.event_id,
            "processed_at": datetime.now().isoformat(),
            "processing_result": self._process_event_data(event)
        }
        
        self.processed_events.append({
            "event": event,
            "result": result,
            "timestamp": datetime.now()
        })
        
        logger.info(f"Handler {self.handler_id} processed event {event.event_id}")
        return result
        
    def _process_event_data(self, event: Event) -> Dict[str, Any]:
        """Process specific event data based on type"""
        if event.event_type == EventType.MARKET_DATA_UPDATE:
            return self._process_market_data(event.data)
        elif event.event_type == EventType.ORDER_CREATED:
            return self._process_order_created(event.data)
        elif event.event_type == EventType.ORDER_EXECUTED:
            return self._process_order_executed(event.data)
        elif event.event_type == EventType.PORTFOLIO_UPDATED:
            return self._process_portfolio_update(event.data)
        elif event.event_type == EventType.RISK_ALERT:
            return self._process_risk_alert(event.data)
        else:
            return {"status": "processed", "data": event.data}
            
    def _process_market_data(self, data: Dict) -> Dict:
        """Process market data event"""
        return {
            "status": "market_data_processed",
            "symbol": data.get("symbol"),
            "price_change": data.get("price", 0) - data.get("previous_price", 0),
            "volume_analysis": "high" if data.get("volume", 0) > 10000 else "normal"
        }
        
    def _process_order_created(self, data: Dict) -> Dict:
        """Process order created event"""
        return {
            "status": "order_validated",
            "order_id": data.get("order_id"),
            "risk_check": "passed",
            "estimated_execution_time": "2-5 minutes"
        }
        
    def _process_order_executed(self, data: Dict) -> Dict:
        """Process order executed event"""
        return {
            "status": "execution_confirmed",
            "order_id": data.get("order_id"),
            "settlement_date": (datetime.now() + timedelta(days=2)).isoformat(),
            "commission": data.get("executed_quantity", 0) * 0.005
        }
        
    def _process_portfolio_update(self, data: Dict) -> Dict:
        """Process portfolio update event"""
        return {
            "status": "portfolio_rebalanced",
            "portfolio_id": data.get("portfolio_id"),
            "new_total_value": data.get("total_value"),
            "rebalancing_required": data.get("total_value", 0) > 1000000
        }
        
    def _process_risk_alert(self, data: Dict) -> Dict:
        """Process risk alert event"""
        return {
            "status": "risk_alert_processed",
            "alert_type": data.get("alert_type"),
            "action_required": data.get("severity") == "critical",
            "notification_sent": True
        }


class MockEventBus:
    """Mock event bus for testing"""
    
    def __init__(self):
        self.handlers = {}
        self.published_events = []
        self.event_history = []
        self.subscribers = {}
        self.processing_stats = {
            "total_events": 0,
            "successful_events": 0,
            "failed_events": 0,
            "average_processing_time": 0.0
        }
        
    def register_handler(self, handler: MockEventHandler):
        """Register event handler"""
        self.handlers[handler.handler_id] = handler
        
        # Subscribe handler to its event types
        for event_type in handler.event_types:
            if event_type not in self.subscribers:
                self.subscribers[event_type] = []
            self.subscribers[event_type].append(handler)
            
        logger.info(f"Registered handler {handler.handler_id} for events: {[et.value for et in handler.event_types]}")
        
    def unregister_handler(self, handler_id: str):
        """Unregister event handler"""
        if handler_id in self.handlers:
            handler = self.handlers[handler_id]
            
            # Remove from subscribers
            for event_type in handler.event_types:
                if event_type in self.subscribers:
                    self.subscribers[event_type] = [
                        h for h in self.subscribers[event_type] 
                        if h.handler_id != handler_id
                    ]
                    
            del self.handlers[handler_id]
            logger.info(f"Unregistered handler {handler_id}")
            
    async def publish_event(self, event: Event) -> Dict[str, Any]:
        """Publish event to all subscribers"""
        start_time = time.time()
        
        self.published_events.append(event)
        self.processing_stats["total_events"] += 1
        
        # Get handlers for this event type
        handlers = self.subscribers.get(event.event_type, [])
        
        if not handlers:
            logger.warning(f"No handlers registered for event type {event.event_type}")
            return {"status": "no_handlers", "event_id": event.event_id}
            
        # Process event with all handlers
        results = []
        failed_handlers = []
        
        for handler in handlers:
            try:
                result = await handler.handle_event(event)
                results.append(result)
            except Exception as e:
                failed_handlers.append({
                    "handler_id": handler.handler_id,
                    "error": str(e)
                })
                logger.error(f"Handler {handler.handler_id} failed to process event {event.event_id}: {e}")
                
        # Update statistics
        processing_time = time.time() - start_time
        if failed_handlers:
            self.processing_stats["failed_events"] += 1
        else:
            self.processing_stats["successful_events"] += 1
            
        # Update average processing time
        total_events = self.processing_stats["total_events"]
        current_avg = self.processing_stats["average_processing_time"]
        self.processing_stats["average_processing_time"] = (
            (current_avg * (total_events - 1) + processing_time) / total_events
        )
        
        # Store in history
        self.event_history.append({
            "event": event,
            "results": results,
            "failed_handlers": failed_handlers,
            "processing_time": processing_time,
            "timestamp": datetime.now()
        })
        
        return {
            "status": "processed" if not failed_handlers else "partial_failure",
            "event_id": event.event_id,
            "handlers_processed": len(results),
            "handlers_failed": len(failed_handlers),
            "processing_time": processing_time,
            "results": results,
            "failures": failed_handlers
        }
        
    async def publish_batch(self, events: List[Event]) -> List[Dict[str, Any]]:
        """Publish multiple events"""
        results = []
        for event in events:
            result = await self.publish_event(event)
            results.append(result)
        return results
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get event processing statistics"""
        return {
            **self.processing_stats,
            "registered_handlers": len(self.handlers),
            "event_types_covered": len(self.subscribers),
            "total_published_events": len(self.published_events)
        }


class TestEventProcessing:
    """Test suite for event processing integration"""
    
    def setup_method(self):
        """Setup test environment"""
        self.event_bus = MockEventBus()
        
        # Create event handlers
        self.market_data_handler = MockEventHandler(
            "market_data_processor",
            [EventType.MARKET_DATA_UPDATE]
        )
        
        self.order_handler = MockEventHandler(
            "order_processor",
            [EventType.ORDER_CREATED, EventType.ORDER_EXECUTED, EventType.ORDER_CANCELLED]
        )
        
        self.portfolio_handler = MockEventHandler(
            "portfolio_processor",
            [EventType.PORTFOLIO_UPDATED, EventType.POSITION_CHANGED]
        )
        
        self.risk_handler = MockEventHandler(
            "risk_processor",
            [EventType.RISK_ALERT, EventType.POSITION_CHANGED]
        )
        
        self.audit_handler = MockEventHandler(
            "audit_processor",
            list(EventType)  # Handles all event types
        )
        
        # Register handlers
        self.event_bus.register_handler(self.market_data_handler)
        self.event_bus.register_handler(self.order_handler)
        self.event_bus.register_handler(self.portfolio_handler)
        self.event_bus.register_handler(self.risk_handler)
        self.event_bus.register_handler(self.audit_handler)
        
        logger.info("Event processing test setup completed")
        
    async def teardown_method(self):
        """Cleanup test environment"""
        logger.info("Event processing test cleanup completed")
        
    @pytest.mark.asyncio
    async def test_event_handler_registration(self):
        """Test event handler registration"""
        assert len(self.event_bus.handlers) == 5
        assert "market_data_processor" in self.event_bus.handlers
        assert "order_processor" in self.event_bus.handlers
        assert "portfolio_processor" in self.event_bus.handlers
        assert "risk_processor" in self.event_bus.handlers
        assert "audit_processor" in self.event_bus.handlers
        
        # Check subscribers
        assert EventType.MARKET_DATA_UPDATE in self.event_bus.subscribers
        assert len(self.event_bus.subscribers[EventType.MARKET_DATA_UPDATE]) == 2  # market_data + audit
        
    @pytest.mark.asyncio
    async def test_market_data_event_processing(self):
        """Test market data event processing"""
        # Create market data event
        event = Event(
            event_id="md_001",
            event_type=EventType.MARKET_DATA_UPDATE,
            timestamp=datetime.now(),
            source="market_data_feed",
            data={
                "symbol": "AAPL",
                "price": 150.25,
                "previous_price": 149.80,
                "volume": 15000,
                "bid": 150.20,
                "ask": 150.30
            }
        )
        
        # Publish event
        result = await self.event_bus.publish_event(event)
        
        assert result["status"] == "processed"
        assert result["handlers_processed"] == 2  # market_data + audit handlers
        assert result["handlers_failed"] == 0
        
        # Check handler processing
        assert len(self.market_data_handler.processed_events) == 1
        assert len(self.audit_handler.processed_events) == 1
        
    @pytest.mark.asyncio
    async def test_order_lifecycle_events(self):
        """Test order lifecycle event processing"""
        correlation_id = "order_flow_001"
        
        # Order created event
        order_created = Event(
            event_id="order_created_001",
            event_type=EventType.ORDER_CREATED,
            timestamp=datetime.now(),
            source="order_management_system",
            correlation_id=correlation_id,
            data={
                "order_id": "order_123",
                "symbol": "GOOGL",
                "side": "buy",
                "quantity": 100,
                "price": 2750.00,
                "order_type": "limit"
            }
        )
        
        # Order executed event
        order_executed = Event(
            event_id="order_executed_001",
            event_type=EventType.ORDER_EXECUTED,
            timestamp=datetime.now() + timedelta(minutes=2),
            source="execution_engine",
            correlation_id=correlation_id,
            data={
                "order_id": "order_123",
                "executed_quantity": 100,
                "executed_price": 2749.50,
                "execution_time": datetime.now().isoformat()
            }
        )
        
        # Publish events
        create_result = await self.event_bus.publish_event(order_created)
        execute_result = await self.event_bus.publish_event(order_executed)
        
        # Verify processing
        assert create_result["status"] == "processed"
        assert execute_result["status"] == "processed"
        
        # Check order handler processed both events
        assert len(self.order_handler.processed_events) == 2
        
        # Verify correlation
        processed_events = self.order_handler.processed_events
        assert all(e["event"].correlation_id == correlation_id for e in processed_events)
        
    @pytest.mark.asyncio
    async def test_portfolio_update_processing(self):
        """Test portfolio update event processing"""
        # Portfolio update event
        portfolio_event = Event(
            event_id="portfolio_001",
            event_type=EventType.PORTFOLIO_UPDATED,
            timestamp=datetime.now(),
            source="portfolio_manager",
            data={
                "portfolio_id": "portfolio_456",
                "total_value": 1250000.00,
                "cash_balance": 125000.00,
                "positions": [
                    {"symbol": "AAPL", "quantity": 1000, "market_value": 150250.00},
                    {"symbol": "GOOGL", "quantity": 400, "market_value": 1100000.00}
                ]
            }
        )
        
        # Position change event
        position_event = Event(
            event_id="position_001",
            event_type=EventType.POSITION_CHANGED,
            timestamp=datetime.now(),
            source="position_manager",
            data={
                "portfolio_id": "portfolio_456",
                "symbol": "TSLA",
                "old_quantity": 0,
                "new_quantity": 50,
                "price": 800.00
            }
        )
        
        # Publish events
        portfolio_result = await self.event_bus.publish_event(portfolio_event)
        position_result = await self.event_bus.publish_event(position_event)
        
        # Verify processing
        assert portfolio_result["status"] == "processed"
        assert position_result["status"] == "processed"
        
        # Check both portfolio and risk handlers processed position change
        assert len(self.portfolio_handler.processed_events) == 2
        assert len(self.risk_handler.processed_events) == 1  # Only position change
        
    @pytest.mark.asyncio
    async def test_risk_alert_processing(self):
        """Test risk alert event processing"""
        # High severity risk alert
        risk_alert = Event(
            event_id="risk_001",
            event_type=EventType.RISK_ALERT,
            timestamp=datetime.now(),
            source="risk_engine",
            data={
                "alert_type": "var_breach",
                "portfolio_id": "portfolio_789",
                "current_var": 75000.00,
                "var_limit": 50000.00,
                "severity": "critical",
                "confidence_level": 0.95
            }
        )
        
        # Publish event
        result = await self.event_bus.publish_event(risk_alert)
        
        assert result["status"] == "processed"
        
        # Check risk handler processing
        assert len(self.risk_handler.processed_events) == 1
        processed_event = self.risk_handler.processed_events[0]
        
        # Verify critical alert triggers action
        processing_result = processed_event["result"]["processing_result"]
        assert processing_result["action_required"] is True
        assert processing_result["notification_sent"] is True
        
    @pytest.mark.asyncio
    async def test_batch_event_processing(self):
        """Test batch event processing"""
        # Create batch of market data events
        events = []
        symbols = ["AAPL", "GOOGL", "TSLA", "NVDA", "MSFT"]
        
        for i, symbol in enumerate(symbols):
            event = Event(
                event_id=f"batch_md_{i}",
                event_type=EventType.MARKET_DATA_UPDATE,
                timestamp=datetime.now(),
                source="market_data_feed",
                data={
                    "symbol": symbol,
                    "price": 100.0 + i * 50,
                    "volume": 1000 * (i + 1)
                }
            )
            events.append(event)
            
        # Publish batch
        results = await self.event_bus.publish_batch(events)
        
        # Verify all events processed
        assert len(results) == 5
        assert all(r["status"] == "processed" for r in results)
        
        # Check handler received all events
        assert len(self.market_data_handler.processed_events) == 5
        
    @pytest.mark.asyncio
    async def test_event_handler_failure(self):
        """Test event handler failure scenarios"""
        # Create handler with low success rate
        failing_handler = MockEventHandler(
            "failing_processor",
            [EventType.MARKET_DATA_UPDATE]
        )
        failing_handler.success_rate = 0.0  # Always fail
        
        self.event_bus.register_handler(failing_handler)
        
        # Create event
        event = Event(
            event_id="failure_test_001",
            event_type=EventType.MARKET_DATA_UPDATE,
            timestamp=datetime.now(),
            source="test",
            data={"symbol": "TEST", "price": 100.0}
        )
        
        # Publish event
        result = await self.event_bus.publish_event(event)
        
        # Should have partial failure
        assert result["status"] == "partial_failure"
        assert result["handlers_failed"] == 1
        assert len(result["failures"]) == 1
        assert result["failures"][0]["handler_id"] == "failing_processor"
        
    @pytest.mark.asyncio
    async def test_event_processing_performance(self):
        """Test event processing performance"""
        # Reduce processing time for performance test
        for handler in self.event_bus.handlers.values():
            handler.processing_time = 0.01
            
        start_time = time.time()
        
        # Create and publish many events
        events = []
        for i in range(50):
            event = Event(
                event_id=f"perf_test_{i}",
                event_type=EventType.MARKET_DATA_UPDATE,
                timestamp=datetime.now(),
                source="performance_test",
                data={"symbol": f"STOCK{i}", "price": 100.0 + i}
            )
            events.append(event)
            
        results = await self.event_bus.publish_batch(events)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify performance
        assert len(results) == 50
        assert all(r["status"] == "processed" for r in results)
        assert total_time < 5.0  # Should complete within 5 seconds
        
        # Check statistics
        stats = self.event_bus.get_statistics()
        assert stats["total_events"] >= 50
        assert stats["successful_events"] >= 50
        
    @pytest.mark.asyncio
    async def test_event_correlation_tracking(self):
        """Test event correlation tracking"""
        correlation_id = "trade_flow_001"
        
        # Create correlated events
        events = [
            Event(
                event_id="trade_001",
                event_type=EventType.ORDER_CREATED,
                timestamp=datetime.now(),
                source="trading_system",
                correlation_id=correlation_id,
                data={"order_id": "order_001", "symbol": "AAPL"}
            ),
            Event(
                event_id="trade_002",
                event_type=EventType.ORDER_EXECUTED,
                timestamp=datetime.now(),
                source="execution_engine",
                correlation_id=correlation_id,
                data={"order_id": "order_001", "executed_quantity": 100}
            ),
            Event(
                event_id="trade_003",
                event_type=EventType.PORTFOLIO_UPDATED,
                timestamp=datetime.now(),
                source="portfolio_manager",
                correlation_id=correlation_id,
                data={"portfolio_id": "port_001", "symbol": "AAPL"}
            )
        ]
        
        # Publish correlated events
        for event in events:
            await self.event_bus.publish_event(event)
            
        # Verify correlation tracking in audit handler
        audit_events = self.audit_handler.processed_events
        correlated_events = [
            e for e in audit_events 
            if e["event"].correlation_id == correlation_id
        ]
        
        assert len(correlated_events) == 3
        
    @pytest.mark.asyncio
    async def test_event_statistics_tracking(self):
        """Test event processing statistics"""
        # Publish various events
        events = [
            Event("stat_001", EventType.MARKET_DATA_UPDATE, datetime.now(), "test", {}),
            Event("stat_002", EventType.ORDER_CREATED, datetime.now(), "test", {}),
            Event("stat_003", EventType.PORTFOLIO_UPDATED, datetime.now(), "test", {})
        ]
        
        for event in events:
            await self.event_bus.publish_event(event)
            
        # Get statistics
        stats = self.event_bus.get_statistics()
        
        assert stats["total_events"] >= 3
        assert stats["successful_events"] >= 3
        assert stats["registered_handlers"] == 5
        assert stats["average_processing_time"] > 0
        
    @pytest.mark.asyncio
    async def test_handler_unregistration(self):
        """Test event handler unregistration"""
        # Unregister market data handler
        self.event_bus.unregister_handler("market_data_processor")
        
        # Create market data event
        event = Event(
            event_id="unreg_test_001",
            event_type=EventType.MARKET_DATA_UPDATE,
            timestamp=datetime.now(),
            source="test",
            data={"symbol": "TEST", "price": 100.0}
        )
        
        # Publish event
        result = await self.event_bus.publish_event(event)
        
        # Should only be processed by audit handler now
        assert result["status"] == "processed"
        assert result["handlers_processed"] == 1  # Only audit handler
        
        # Verify handler was removed
        assert "market_data_processor" not in self.event_bus.handlers
        assert len(self.event_bus.subscribers[EventType.MARKET_DATA_UPDATE]) == 1


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])