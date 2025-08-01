"""
Tests for Webhook Event System
"""

import pytest
import pytest_asyncio
import asyncio
import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import aiohttp
from aioresponses import aioresponses

from nautilus_trader_engine.events.webhook_system import (
    WebhookEventSystem, WebhookEndpoint, WebhookEvent, WebhookDelivery,
    WebhookEventType, WebhookStatus, WebhookSecurityType,
    WebhookSecurity, WebhookRetryManager, WebhookEvents,
    create_webhook_system
)

class TestWebhookSecurity:
    """Test webhook security functions"""
    
    def test_generate_hmac_signature(self):
        """Test HMAC signature generation"""
        payload = '{"test": "data"}'
        secret = "test-secret"
        
        signature = WebhookSecurity.generate_hmac_signature(payload, secret)
        
        assert signature.startswith("sha256=")
        assert len(signature) == 71  # sha256= + 64 hex chars
    
    def test_verify_hmac_signature(self):
        """Test HMAC signature verification"""
        payload = '{"test": "data"}'
        secret = "test-secret"
        
        signature = WebhookSecurity.generate_hmac_signature(payload, secret)
        
        # Valid signature should verify
        assert WebhookSecurity.verify_hmac_signature(payload, signature, secret)
        
        # Invalid signature should not verify
        assert not WebhookSecurity.verify_hmac_signature(payload, "invalid", secret)
        
        # Different payload should not verify
        assert not WebhookSecurity.verify_hmac_signature('{"different": "data"}', signature, secret)
    
    def test_generate_jwt_token(self):
        """Test JWT token generation"""
        payload = {"user_id": "123", "event": "test"}
        secret = "jwt-secret"
        
        token = WebhookSecurity.generate_jwt_token(payload, secret)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_jwt_token(self):
        """Test JWT token verification"""
        payload = {"user_id": "123", "event": "test"}
        secret = "jwt-secret"
        
        token = WebhookSecurity.generate_jwt_token(payload, secret)
        
        # Valid token should verify
        decoded = WebhookSecurity.verify_jwt_token(token, secret)
        assert decoded is not None
        assert decoded["user_id"] == "123"
        assert decoded["event"] == "test"
        
        # Invalid token should not verify
        assert WebhookSecurity.verify_jwt_token("invalid-token", secret) is None
        
        # Wrong secret should not verify
        assert WebhookSecurity.verify_jwt_token(token, "wrong-secret") is None

class TestWebhookRetryManager:
    """Test webhook retry manager"""
    
    def test_initialization(self):
        """Test retry manager initialization"""
        manager = WebhookRetryManager(max_retries=5, base_delay=10)
        
        assert manager.max_retries == 5
        assert manager.base_delay == 10
    
    def test_calculate_next_retry(self):
        """Test retry time calculation"""
        manager = WebhookRetryManager(base_delay=5)
        
        # First retry (attempt 1)
        next_retry = manager.calculate_next_retry(1)
        expected_delay = 5 * (2 ** 1)  # 10 seconds
        assert next_retry > datetime.now() + timedelta(seconds=expected_delay - 1)
        assert next_retry < datetime.now() + timedelta(seconds=expected_delay + 1)
        
        # Second retry (attempt 2)
        next_retry = manager.calculate_next_retry(2)
        expected_delay = 5 * (2 ** 2)  # 20 seconds
        assert next_retry > datetime.now() + timedelta(seconds=expected_delay - 1)
        assert next_retry < datetime.now() + timedelta(seconds=expected_delay + 1)
    
    def test_should_retry(self):
        """Test retry decision logic"""
        manager = WebhookRetryManager(max_retries=3)
        
        # Should retry for failed delivery within retry limit
        delivery = WebhookDelivery(
            id="test",
            webhook_id="webhook-1",
            event_id="event-1",
            endpoint_url="https://example.com",
            status=WebhookStatus.FAILED,
            attempt_count=1
        )
        assert manager.should_retry(delivery)
        
        # Should not retry if max attempts reached
        delivery.attempt_count = 3
        assert not manager.should_retry(delivery)
        
        # Should not retry if already delivered
        delivery.status = WebhookStatus.DELIVERED
        delivery.attempt_count = 1
        assert not manager.should_retry(delivery)
        
        # Should not retry for certain HTTP status codes
        delivery.status = WebhookStatus.FAILED
        delivery.response_status = 404
        assert not manager.should_retry(delivery)

class TestWebhookEndpoint:
    """Test webhook endpoint"""
    
    def test_endpoint_creation(self):
        """Test webhook endpoint creation"""
        endpoint = WebhookEndpoint(
            id="test-endpoint",
            url="https://example.com/webhook",
            name="Test Endpoint",
            description="Test webhook endpoint",
            events=[WebhookEventType.ORDER_CREATED],
            security_type=WebhookSecurityType.HMAC_SHA256,
            secret="test-secret"
        )
        
        assert endpoint.id == "test-endpoint"
        assert endpoint.url == "https://example.com/webhook"
        assert endpoint.name == "Test Endpoint"
        assert WebhookEventType.ORDER_CREATED in endpoint.events
        assert endpoint.security_type == WebhookSecurityType.HMAC_SHA256
        assert endpoint.secret == "test-secret"
        assert endpoint.is_active is True

class TestWebhookEvent:
    """Test webhook event"""
    
    def test_event_creation(self):
        """Test webhook event creation"""
        event_data = {"order_id": "123", "symbol": "AAPL"}
        metadata = {"priority": "high"}
        
        event = WebhookEvent(
            id="test-event",
            event_type=WebhookEventType.ORDER_CREATED,
            data=event_data,
            metadata=metadata
        )
        
        assert event.id == "test-event"
        assert event.event_type == WebhookEventType.ORDER_CREATED
        assert event.data == event_data
        assert event.metadata == metadata
        assert event.source == "nautilus_trader"
        assert event.version == "1.0"

class TestWebhookEventSystem:
    """Test webhook event system"""
    
    @pytest_asyncio.fixture
    async def webhook_system(self):
        """Create webhook system for testing"""
        system = create_webhook_system()
        await system.start()
        yield system
        await system.stop()
    
    @pytest.fixture
    def sample_endpoint(self):
        """Create sample webhook endpoint"""
        return WebhookEndpoint(
            id="test-endpoint",
            url="https://httpbin.org/post",
            name="Test Endpoint",
            events=[WebhookEventType.ORDER_CREATED, WebhookEventType.ORDER_FILLED],
            security_type=WebhookSecurityType.HMAC_SHA256,
            secret="test-secret"
        )
    
    def test_system_creation(self):
        """Test webhook system creation"""
        system = create_webhook_system(max_concurrent_deliveries=50)
        
        assert system.max_concurrent_deliveries == 50
        assert not system.is_running
        assert len(system.endpoints) == 0
    
    @pytest.mark.asyncio
    async def test_system_start_stop(self):
        """Test webhook system start/stop"""
        system = create_webhook_system()
        
        # Initially not running
        assert not system.is_running
        
        # Start system
        await system.start()
        assert system.is_running
        assert system.session is not None
        
        # Stop system
        await system.stop()
        assert not system.is_running
    
    @pytest.mark.asyncio
    async def test_register_endpoint(self, webhook_system, sample_endpoint):
        """Test endpoint registration"""
        endpoint_id = webhook_system.register_endpoint(sample_endpoint)
        
        assert endpoint_id == sample_endpoint.id
        assert endpoint_id in webhook_system.endpoints
        
        registered_endpoint = webhook_system.get_endpoint(endpoint_id)
        assert registered_endpoint.name == sample_endpoint.name
        assert registered_endpoint.url == sample_endpoint.url
    
    @pytest.mark.asyncio
    async def test_register_endpoint_validation(self, webhook_system):
        """Test endpoint registration validation"""
        # Invalid URL should raise error
        with pytest.raises(ValueError, match="Invalid webhook URL"):
            invalid_endpoint = WebhookEndpoint(
                id="invalid",
                url="not-a-url",
                name="Invalid Endpoint"
            )
            webhook_system.register_endpoint(invalid_endpoint)
        
        # Secure endpoint without secret should raise error
        with pytest.raises(ValueError, match="Secret is required"):
            secure_endpoint = WebhookEndpoint(
                id="secure",
                url="https://example.com",
                name="Secure Endpoint",
                security_type=WebhookSecurityType.HMAC_SHA256
            )
            webhook_system.register_endpoint(secure_endpoint)
    
    @pytest.mark.asyncio
    async def test_unregister_endpoint(self, webhook_system, sample_endpoint):
        """Test endpoint unregistration"""
        endpoint_id = webhook_system.register_endpoint(sample_endpoint)
        
        # Unregister existing endpoint
        assert webhook_system.unregister_endpoint(endpoint_id) is True
        assert endpoint_id not in webhook_system.endpoints
        
        # Unregister non-existent endpoint
        assert webhook_system.unregister_endpoint("non-existent") is False
    
    @pytest.mark.asyncio
    async def test_update_endpoint(self, webhook_system, sample_endpoint):
        """Test endpoint update"""
        endpoint_id = webhook_system.register_endpoint(sample_endpoint)
        
        # Update endpoint
        success = webhook_system.update_endpoint(
            endpoint_id,
            name="Updated Endpoint",
            description="Updated description"
        )
        
        assert success is True
        
        updated_endpoint = webhook_system.get_endpoint(endpoint_id)
        assert updated_endpoint.name == "Updated Endpoint"
        assert updated_endpoint.description == "Updated description"
        
        # Update non-existent endpoint
        assert webhook_system.update_endpoint("non-existent", name="Test") is False
    
    @pytest.mark.asyncio
    async def test_list_endpoints(self, webhook_system, sample_endpoint):
        """Test endpoint listing"""
        # Initially empty
        assert len(webhook_system.list_endpoints()) == 0
        
        # Add endpoint
        webhook_system.register_endpoint(sample_endpoint)
        endpoints = webhook_system.list_endpoints()
        
        assert len(endpoints) == 1
        assert endpoints[0].id == sample_endpoint.id
    
    @pytest.mark.asyncio
    async def test_emit_event_no_endpoints(self, webhook_system):
        """Test event emission with no registered endpoints"""
        event_id = await webhook_system.emit_event(
            WebhookEventType.ORDER_CREATED,
            {"order_id": "123"}
        )
        
        assert event_id is not None
        assert len(webhook_system.deliveries) == 0
    
    @pytest.mark.asyncio
    async def test_emit_event_with_endpoints(self, webhook_system, sample_endpoint):
        """Test event emission with registered endpoints"""
        webhook_system.register_endpoint(sample_endpoint)
        
        with aioresponses() as m:
            m.post(sample_endpoint.url, status=200, payload={"success": True})
            
            event_id = await webhook_system.emit_event(
                WebhookEventType.ORDER_CREATED,
                {"order_id": "123", "symbol": "AAPL"}
            )
            
            assert event_id is not None
            
            # Wait for delivery
            await asyncio.sleep(0.1)
            
            # Check delivery was created
            assert len(webhook_system.deliveries) == 1
    
    @pytest.mark.asyncio
    async def test_webhook_delivery_success(self, webhook_system, sample_endpoint):
        """Test successful webhook delivery"""
        webhook_system.register_endpoint(sample_endpoint)
        
        with aioresponses() as m:
            m.post(sample_endpoint.url, status=200, payload={"received": True})
            
            await webhook_system.emit_event(
                WebhookEventType.ORDER_CREATED,
                {"order_id": "123"}
            )
            
            # Wait for delivery
            await asyncio.sleep(0.1)
            
            # Check delivery status
            deliveries = list(webhook_system.deliveries.values())
            assert len(deliveries) == 1
            
            delivery = deliveries[0]
            assert delivery.status == WebhookStatus.DELIVERED
            assert delivery.response_status == 200
            assert delivery.delivered_at is not None
    
    @pytest.mark.asyncio
    async def test_webhook_delivery_failure(self, webhook_system, sample_endpoint):
        """Test failed webhook delivery"""
        webhook_system.register_endpoint(sample_endpoint)
        
        with aioresponses() as m:
            m.post(sample_endpoint.url, status=500, payload={"error": "Internal Server Error"})
            
            await webhook_system.emit_event(
                WebhookEventType.ORDER_CREATED,
                {"order_id": "123"}
            )
            
            # Wait for delivery
            await asyncio.sleep(0.1)
            
            # Check delivery status
            deliveries = list(webhook_system.deliveries.values())
            assert len(deliveries) == 1
            
            delivery = deliveries[0]
            assert delivery.status in [WebhookStatus.FAILED, WebhookStatus.RETRYING]
            assert delivery.response_status == 500
    
    @pytest.mark.asyncio
    async def test_webhook_security_hmac(self, webhook_system):
        """Test webhook HMAC security"""
        endpoint = WebhookEndpoint(
            id="secure-endpoint",
            url="https://httpbin.org/post",
            name="Secure Endpoint",
            security_type=WebhookSecurityType.HMAC_SHA256,
            secret="test-secret"
        )
        
        webhook_system.register_endpoint(endpoint)
        
        with aioresponses() as m:
            def callback(url, **kwargs):
                # Verify HMAC signature is present
                headers = kwargs.get('headers', {})
                assert 'X-Webhook-Signature' in headers
                assert headers['X-Webhook-Signature'].startswith('sha256=')
                return aioresponses.CallbackResult(status=200, payload={"verified": True})
            
            m.post(endpoint.url, callback=callback)
            
            await webhook_system.emit_event(
                WebhookEventType.ORDER_CREATED,
                {"order_id": "123"}
            )
            
            # Wait for delivery
            await asyncio.sleep(0.1)
    
    @pytest.mark.asyncio
    async def test_delivery_stats(self, webhook_system, sample_endpoint):
        """Test delivery statistics"""
        webhook_system.register_endpoint(sample_endpoint)
        
        # Initially no stats
        stats = webhook_system.get_delivery_stats()
        assert stats['total'] == 0
        assert stats['success_rate'] == 0.0
        
        with aioresponses() as m:
            m.post(sample_endpoint.url, status=200, payload={"success": True})
            
            # Emit event
            await webhook_system.emit_event(
                WebhookEventType.ORDER_CREATED,
                {"order_id": "123"}
            )
            
            # Wait for delivery
            await asyncio.sleep(0.1)
            
            # Check stats
            stats = webhook_system.get_delivery_stats()
            assert stats['total'] == 1
            assert stats['delivered'] == 1
            assert stats['success_rate'] == 100.0
    
    @pytest.mark.asyncio
    async def test_recent_deliveries(self, webhook_system, sample_endpoint):
        """Test recent deliveries retrieval"""
        webhook_system.register_endpoint(sample_endpoint)
        
        with aioresponses() as m:
            m.post(sample_endpoint.url, status=200, payload={"success": True})
            
            # Emit multiple events
            for i in range(3):
                await webhook_system.emit_event(
                    WebhookEventType.ORDER_CREATED,
                    {"order_id": f"order-{i}"}
                )
            
            # Wait for deliveries
            await asyncio.sleep(0.2)
            
            # Get recent deliveries
            deliveries = webhook_system.get_recent_deliveries(limit=2)
            assert len(deliveries) == 2
            
            # Should be sorted by creation time (most recent first)
            assert deliveries[0].created_at >= deliveries[1].created_at
    
    @pytest.mark.asyncio
    async def test_cleanup_old_deliveries(self, webhook_system):
        """Test cleanup of old delivery records"""
        # Create some mock old deliveries
        old_delivery = WebhookDelivery(
            id="old-delivery",
            webhook_id="webhook-1",
            event_id="event-1",
            endpoint_url="https://example.com",
            status=WebhookStatus.DELIVERED,
            created_at=datetime.now() - timedelta(days=10)
        )
        
        recent_delivery = WebhookDelivery(
            id="recent-delivery",
            webhook_id="webhook-1",
            event_id="event-2",
            endpoint_url="https://example.com",
            status=WebhookStatus.DELIVERED,
            created_at=datetime.now()
        )
        
        webhook_system.deliveries["old-delivery"] = old_delivery
        webhook_system.deliveries["recent-delivery"] = recent_delivery
        
        # Cleanup deliveries older than 7 days
        cleaned_count = webhook_system.cleanup_old_deliveries(days=7)
        
        assert cleaned_count == 1
        assert "old-delivery" not in webhook_system.deliveries
        assert "recent-delivery" in webhook_system.deliveries

class TestWebhookEvents:
    """Test webhook events helper"""
    
    @pytest_asyncio.fixture
    async def webhook_events(self):
        """Create webhook events helper"""
        system = create_webhook_system()
        await system.start()
        events = WebhookEvents(system)
        yield events
        await system.stop()
    
    @pytest.mark.asyncio
    async def test_order_created_event(self, webhook_events):
        """Test order created event"""
        order_data = {
            "id": "order-123",
            "symbol": "AAPL",
            "side": "buy",
            "quantity": 100
        }
        
        event_id = await webhook_events.order_created(order_data)
        assert event_id is not None
    
    @pytest.mark.asyncio
    async def test_order_filled_event(self, webhook_events):
        """Test order filled event"""
        order_data = {"id": "order-123", "symbol": "AAPL"}
        fill_data = {"quantity": 100, "price": 150.25}
        
        event_id = await webhook_events.order_filled(order_data, fill_data)
        assert event_id is not None
    
    @pytest.mark.asyncio
    async def test_risk_alert_event(self, webhook_events):
        """Test risk alert event"""
        alert_data = {
            "type": "position_limit",
            "message": "Position limit exceeded",
            "severity": "high"
        }
        
        event_id = await webhook_events.risk_alert(alert_data)
        assert event_id is not None

class TestWebhookIntegration:
    """Integration tests for webhook system"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_webhook_flow(self):
        """Test complete webhook flow"""
        # Create system
        system = create_webhook_system()
        await system.start()
        
        try:
            # Register endpoint
            endpoint = WebhookEndpoint(
                id="integration-test",
                url="https://httpbin.org/post",
                name="Integration Test Endpoint",
                events=[WebhookEventType.ORDER_CREATED],
                security_type=WebhookSecurityType.HMAC_SHA256,
                secret="integration-secret"
            )
            
            system.register_endpoint(endpoint)
            
            # Create events helper
            events = WebhookEvents(system)
            
            with aioresponses() as m:
                m.post(endpoint.url, status=200, payload={"success": True})
                
                # Emit event
                event_id = await events.order_created({
                    "id": "integration-order",
                    "symbol": "AAPL",
                    "side": "buy",
                    "quantity": 100,
                    "price": 150.25
                })
                
                # Wait for delivery
                await asyncio.sleep(0.1)
                
                # Verify delivery
                stats = system.get_delivery_stats()
                assert stats['total'] == 1
                assert stats['delivered'] == 1
                
                deliveries = system.get_recent_deliveries()
                assert len(deliveries) == 1
                assert deliveries[0].status == WebhookStatus.DELIVERED
        
        finally:
            await system.stop()
    
    @pytest.mark.asyncio
    async def test_multiple_endpoints_same_event(self):
        """Test event delivery to multiple endpoints"""
        system = create_webhook_system()
        await system.start()
        
        try:
            # Register multiple endpoints
            endpoints = []
            for i in range(3):
                endpoint = WebhookEndpoint(
                    id=f"endpoint-{i}",
                    url=f"https://httpbin.org/post/{i}",
                    name=f"Endpoint {i}",
                    events=[WebhookEventType.ORDER_CREATED]
                )
                system.register_endpoint(endpoint)
                endpoints.append(endpoint)
            
            with aioresponses() as m:
                for endpoint in endpoints:
                    m.post(endpoint.url, status=200, payload={"success": True})
                
                # Emit event
                await system.emit_event(
                    WebhookEventType.ORDER_CREATED,
                    {"order_id": "multi-test"}
                )
                
                # Wait for deliveries
                await asyncio.sleep(0.2)
                
                # Verify all endpoints received the event
                stats = system.get_delivery_stats()
                assert stats['total'] == 3
                assert stats['delivered'] == 3
        
        finally:
            await system.stop()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])