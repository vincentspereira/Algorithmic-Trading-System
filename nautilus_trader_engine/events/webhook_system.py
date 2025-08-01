"""
Webhook Event System
Provides event-driven webhook notifications with security, authentication, retry logic,
and comprehensive management interface for the Nautilus Trader Engine.
"""

import logging
import asyncio
import json
import hmac
import hashlib
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import aiohttp
import jwt
from urllib.parse import urlparse
import ssl
import certifi

class WebhookEventType(Enum):
    """Webhook event types"""
    ORDER_CREATED = "order.created"
    ORDER_UPDATED = "order.updated"
    ORDER_FILLED = "order.filled"
    ORDER_CANCELLED = "order.cancelled"
    POSITION_OPENED = "position.opened"
    POSITION_UPDATED = "position.updated"
    POSITION_CLOSED = "position.closed"
    TRADE_EXECUTED = "trade.executed"
    PORTFOLIO_UPDATED = "portfolio.updated"
    RISK_ALERT = "risk.alert"
    MARKET_DATA_UPDATE = "market_data.update"
    SYSTEM_ALERT = "system.alert"
    STRATEGY_SIGNAL = "strategy.signal"
    BACKTEST_COMPLETED = "backtest.completed"
    CUSTOM_EVENT = "custom.event"

class WebhookStatus(Enum):
    """Webhook delivery status"""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    EXPIRED = "expired"

class WebhookSecurityType(Enum):
    """Webhook security types"""
    NONE = "none"
    HMAC_SHA256 = "hmac_sha256"
    JWT = "jwt"
    BASIC_AUTH = "basic_auth"
    API_KEY = "api_key"

@dataclass
class WebhookEndpoint:
    """Webhook endpoint configuration"""
    id: str
    url: str
    name: str
    description: str = ""
    events: List[WebhookEventType] = field(default_factory=list)
    security_type: WebhookSecurityType = WebhookSecurityType.NONE
    secret: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 5
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    failure_count: int = 0
    success_count: int = 0

@dataclass
class WebhookEvent:
    """Webhook event data"""
    id: str
    event_type: WebhookEventType
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "nautilus_trader"
    version: str = "1.0"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WebhookDelivery:
    """Webhook delivery record"""
    id: str
    webhook_id: str
    event_id: str
    endpoint_url: str
    status: WebhookStatus
    attempt_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    delivered_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None

class WebhookSecurity:
    """Webhook security handler"""
    
    @staticmethod
    def generate_hmac_signature(payload: str, secret: str) -> str:
        """Generate HMAC SHA256 signature"""
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    @staticmethod
    def verify_hmac_signature(payload: str, signature: str, secret: str) -> bool:
        """Verify HMAC SHA256 signature"""
        expected_signature = WebhookSecurity.generate_hmac_signature(payload, secret)
        return hmac.compare_digest(signature, expected_signature)
    
    @staticmethod
    def generate_jwt_token(payload: Dict[str, Any], secret: str, expires_in: int = 300) -> str:
        """Generate JWT token"""
        payload.update({
            'iat': int(time.time()),
            'exp': int(time.time()) + expires_in,
            'iss': 'nautilus_trader'
        })
        return jwt.encode(payload, secret, algorithm='HS256')
    
    @staticmethod
    def verify_jwt_token(token: str, secret: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token"""
        try:
            return jwt.decode(token, secret, algorithms=['HS256'])
        except jwt.InvalidTokenError:
            return None

class WebhookRetryManager:
    """Manages webhook retry logic"""
    
    def __init__(self, max_retries: int = 3, base_delay: int = 5):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.logger = logging.getLogger(__name__)
    
    def calculate_next_retry(self, attempt: int, base_delay: int = None) -> datetime:
        """Calculate next retry time with exponential backoff"""
        delay = base_delay or self.base_delay
        backoff_delay = delay * (2 ** attempt)  # Exponential backoff
        return datetime.now() + timedelta(seconds=backoff_delay)
    
    def should_retry(self, delivery: WebhookDelivery) -> bool:
        """Determine if delivery should be retried"""
        if delivery.attempt_count >= self.max_retries:
            return False
        
        if delivery.status == WebhookStatus.DELIVERED:
            return False
        
        # Don't retry for certain HTTP status codes
        if delivery.response_status in [400, 401, 403, 404, 410]:
            return False
        
        return True

class WebhookEventSystem:
    """Main webhook event system"""
    
    def __init__(self, max_concurrent_deliveries: int = 100):
        self.logger = logging.getLogger(__name__)
        self.endpoints: Dict[str, WebhookEndpoint] = {}
        self.deliveries: Dict[str, WebhookDelivery] = {}
        self.event_handlers: Dict[WebhookEventType, List[Callable]] = {}
        self.retry_manager = WebhookRetryManager()
        self.max_concurrent_deliveries = max_concurrent_deliveries
        self.delivery_semaphore = asyncio.Semaphore(max_concurrent_deliveries)
        self.is_running = False
        self.retry_task: Optional[asyncio.Task] = None
        
        # SSL context for secure connections
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        # HTTP session for webhook deliveries
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def start(self):
        """Start the webhook system"""
        if self.is_running:
            return
        
        self.logger.info("Starting webhook event system")
        self.is_running = True
        
        # Create HTTP session
        connector = aiohttp.TCPConnector(ssl=self.ssl_context, limit=100)
        timeout = aiohttp.ClientTimeout(total=60)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        
        # Start retry task
        self.retry_task = asyncio.create_task(self._retry_failed_deliveries())
        
        self.logger.info("Webhook event system started")
    
    async def stop(self):
        """Stop the webhook system"""
        if not self.is_running:
            return
        
        self.logger.info("Stopping webhook event system")
        self.is_running = False
        
        # Cancel retry task
        if self.retry_task:
            self.retry_task.cancel()
            try:
                await self.retry_task
            except asyncio.CancelledError:
                pass
        
        # Close HTTP session
        if self.session:
            await self.session.close()
        
        self.logger.info("Webhook event system stopped")
    
    def register_endpoint(self, endpoint: WebhookEndpoint) -> str:
        """Register a webhook endpoint"""
        if not endpoint.id:
            endpoint.id = str(uuid.uuid4())
        
        # Validate URL
        parsed_url = urlparse(endpoint.url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError(f"Invalid webhook URL: {endpoint.url}")
        
        # Validate security configuration
        if endpoint.security_type != WebhookSecurityType.NONE and not endpoint.secret:
            raise ValueError("Secret is required for secure webhooks")
        
        endpoint.updated_at = datetime.now()
        self.endpoints[endpoint.id] = endpoint
        
        self.logger.info(f"Registered webhook endpoint: {endpoint.name} ({endpoint.id})")
        return endpoint.id
    
    def unregister_endpoint(self, endpoint_id: str) -> bool:
        """Unregister a webhook endpoint"""
        if endpoint_id in self.endpoints:
            endpoint = self.endpoints.pop(endpoint_id)
            self.logger.info(f"Unregistered webhook endpoint: {endpoint.name} ({endpoint_id})")
            return True
        return False
    
    def get_endpoint(self, endpoint_id: str) -> Optional[WebhookEndpoint]:
        """Get webhook endpoint by ID"""
        return self.endpoints.get(endpoint_id)
    
    def list_endpoints(self) -> List[WebhookEndpoint]:
        """List all webhook endpoints"""
        return list(self.endpoints.values())
    
    def update_endpoint(self, endpoint_id: str, **kwargs) -> bool:
        """Update webhook endpoint"""
        if endpoint_id not in self.endpoints:
            return False
        
        endpoint = self.endpoints[endpoint_id]
        for key, value in kwargs.items():
            if hasattr(endpoint, key):
                setattr(endpoint, key, value)
        
        endpoint.updated_at = datetime.now()
        self.logger.info(f"Updated webhook endpoint: {endpoint.name} ({endpoint_id})")
        return True
    
    async def emit_event(self, event_type: WebhookEventType, data: Dict[str, Any], 
                        metadata: Dict[str, Any] = None) -> str:
        """Emit a webhook event"""
        event = WebhookEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            data=data,
            metadata=metadata or {}
        )
        
        # Find matching endpoints
        matching_endpoints = [
            endpoint for endpoint in self.endpoints.values()
            if endpoint.is_active and (
                not endpoint.events or event_type in endpoint.events
            )
        ]
        
        if not matching_endpoints:
            self.logger.debug(f"No endpoints registered for event type: {event_type.value}")
            return event.id
        
        # Create deliveries for each endpoint
        deliveries = []
        for endpoint in matching_endpoints:
            delivery = WebhookDelivery(
                id=str(uuid.uuid4()),
                webhook_id=endpoint.id,
                event_id=event.id,
                endpoint_url=endpoint.url,
                status=WebhookStatus.PENDING
            )
            self.deliveries[delivery.id] = delivery
            deliveries.append(delivery)
        
        # Schedule deliveries
        for delivery in deliveries:
            asyncio.create_task(self._deliver_webhook(delivery, event))
        
        self.logger.info(f"Emitted event {event_type.value} to {len(deliveries)} endpoints")
        return event.id
    
    async def _deliver_webhook(self, delivery: WebhookDelivery, event: WebhookEvent):
        """Deliver webhook to endpoint"""
        async with self.delivery_semaphore:
            endpoint = self.endpoints.get(delivery.webhook_id)
            if not endpoint:
                delivery.status = WebhookStatus.FAILED
                delivery.error_message = "Endpoint not found"
                return
            
            try:
                await self._attempt_delivery(delivery, event, endpoint)
            except Exception as e:
                self.logger.error(f"Unexpected error in webhook delivery: {e}")
                delivery.status = WebhookStatus.FAILED
                delivery.error_message = str(e)
    
    async def _attempt_delivery(self, delivery: WebhookDelivery, event: WebhookEvent, 
                               endpoint: WebhookEndpoint):
        """Attempt webhook delivery"""
        delivery.attempt_count += 1
        start_time = time.time()
        
        try:
            # Prepare payload
            payload = {
                'id': event.id,
                'event': event.event_type.value,
                'data': event.data,
                'timestamp': event.timestamp.isoformat(),
                'source': event.source,
                'version': event.version,
                'metadata': event.metadata
            }
            
            payload_json = json.dumps(payload, default=str)
            
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Nautilus-Trader-Webhook/1.0',
                'X-Webhook-Event': event.event_type.value,
                'X-Webhook-ID': event.id,
                'X-Webhook-Timestamp': str(int(event.timestamp.timestamp())),
                **endpoint.headers
            }
            
            # Add security headers
            if endpoint.security_type == WebhookSecurityType.HMAC_SHA256:
                signature = WebhookSecurity.generate_hmac_signature(payload_json, endpoint.secret)
                headers['X-Webhook-Signature'] = signature
            
            elif endpoint.security_type == WebhookSecurityType.JWT:
                token = WebhookSecurity.generate_jwt_token(payload, endpoint.secret)
                headers['Authorization'] = f'Bearer {token}'
            
            elif endpoint.security_type == WebhookSecurityType.BASIC_AUTH:
                # Assume secret is in format "username:password"
                import base64
                encoded = base64.b64encode(endpoint.secret.encode()).decode()
                headers['Authorization'] = f'Basic {encoded}'
            
            elif endpoint.security_type == WebhookSecurityType.API_KEY:
                headers['X-API-Key'] = endpoint.secret
            
            # Make HTTP request
            async with self.session.post(
                endpoint.url,
                data=payload_json,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=endpoint.timeout)
            ) as response:
                duration_ms = int((time.time() - start_time) * 1000)
                delivery.duration_ms = duration_ms
                delivery.response_status = response.status
                delivery.response_body = await response.text()
                
                if 200 <= response.status < 300:
                    # Success
                    delivery.status = WebhookStatus.DELIVERED
                    delivery.delivered_at = datetime.now()
                    endpoint.success_count += 1
                    endpoint.last_success = datetime.now()
                    endpoint.failure_count = 0  # Reset failure count on success
                    
                    self.logger.info(
                        f"Webhook delivered successfully to {endpoint.name} "
                        f"({response.status}) in {duration_ms}ms"
                    )
                else:
                    # HTTP error
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"HTTP {response.status}"
                    )
        
        except asyncio.TimeoutError:
            delivery.status = WebhookStatus.FAILED
            delivery.error_message = "Request timeout"
            endpoint.failure_count += 1
            endpoint.last_failure = datetime.now()
            
        except aiohttp.ClientError as e:
            delivery.status = WebhookStatus.FAILED
            delivery.error_message = str(e)
            endpoint.failure_count += 1
            endpoint.last_failure = datetime.now()
            
        except Exception as e:
            delivery.status = WebhookStatus.FAILED
            delivery.error_message = f"Unexpected error: {str(e)}"
            endpoint.failure_count += 1
            endpoint.last_failure = datetime.now()
        
        # Schedule retry if needed
        if delivery.status == WebhookStatus.FAILED and self.retry_manager.should_retry(delivery):
            delivery.status = WebhookStatus.RETRYING
            delivery.next_retry_at = self.retry_manager.calculate_next_retry(
                delivery.attempt_count, endpoint.retry_delay
            )
            
            self.logger.info(
                f"Webhook delivery failed, will retry at {delivery.next_retry_at} "
                f"(attempt {delivery.attempt_count}/{endpoint.max_retries})"
            )
        elif delivery.status == WebhookStatus.FAILED:
            delivery.status = WebhookStatus.EXPIRED
            self.logger.warning(f"Webhook delivery expired after {delivery.attempt_count} attempts")
    
    async def _retry_failed_deliveries(self):
        """Background task to retry failed deliveries"""
        while self.is_running:
            try:
                now = datetime.now()
                retry_deliveries = [
                    delivery for delivery in self.deliveries.values()
                    if (delivery.status == WebhookStatus.RETRYING and 
                        delivery.next_retry_at and 
                        delivery.next_retry_at <= now)
                ]
                
                for delivery in retry_deliveries:
                    endpoint = self.endpoints.get(delivery.webhook_id)
                    if endpoint:
                        # Find the original event (in a real implementation, this would be stored)
                        # For now, we'll create a mock event
                        event = WebhookEvent(
                            id=delivery.event_id,
                            event_type=WebhookEventType.CUSTOM_EVENT,
                            data={"retry": True}
                        )
                        asyncio.create_task(self._attempt_delivery(delivery, event, endpoint))
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Error in retry task: {e}")
                await asyncio.sleep(10)
    
    def get_delivery_stats(self, endpoint_id: str = None) -> Dict[str, Any]:
        """Get delivery statistics"""
        deliveries = list(self.deliveries.values())
        
        if endpoint_id:
            deliveries = [d for d in deliveries if d.webhook_id == endpoint_id]
        
        total = len(deliveries)
        if total == 0:
            return {
                'total': 0,
                'delivered': 0,
                'failed': 0,
                'pending': 0,
                'retrying': 0,
                'expired': 0,
                'success_rate': 0.0,
                'avg_duration_ms': 0.0
            }
        
        delivered = len([d for d in deliveries if d.status == WebhookStatus.DELIVERED])
        failed = len([d for d in deliveries if d.status == WebhookStatus.FAILED])
        pending = len([d for d in deliveries if d.status == WebhookStatus.PENDING])
        retrying = len([d for d in deliveries if d.status == WebhookStatus.RETRYING])
        expired = len([d for d in deliveries if d.status == WebhookStatus.EXPIRED])
        
        success_rate = (delivered / total) * 100 if total > 0 else 0
        
        durations = [d.duration_ms for d in deliveries if d.duration_ms is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            'total': total,
            'delivered': delivered,
            'failed': failed,
            'pending': pending,
            'retrying': retrying,
            'expired': expired,
            'success_rate': success_rate,
            'avg_duration_ms': avg_duration
        }
    
    def get_recent_deliveries(self, endpoint_id: str = None, limit: int = 100) -> List[WebhookDelivery]:
        """Get recent webhook deliveries"""
        deliveries = list(self.deliveries.values())
        
        if endpoint_id:
            deliveries = [d for d in deliveries if d.webhook_id == endpoint_id]
        
        # Sort by creation time (most recent first)
        deliveries.sort(key=lambda x: x.created_at, reverse=True)
        
        return deliveries[:limit]
    
    def cleanup_old_deliveries(self, days: int = 7):
        """Clean up old delivery records"""
        cutoff_date = datetime.now() - timedelta(days=days)
        old_deliveries = [
            delivery_id for delivery_id, delivery in self.deliveries.items()
            if delivery.created_at < cutoff_date
        ]
        
        for delivery_id in old_deliveries:
            del self.deliveries[delivery_id]
        
        self.logger.info(f"Cleaned up {len(old_deliveries)} old delivery records")
        return len(old_deliveries)

# Convenience functions for common webhook events
class WebhookEvents:
    """Common webhook event emitters"""
    
    def __init__(self, webhook_system: WebhookEventSystem):
        self.webhook_system = webhook_system
    
    async def order_created(self, order_data: Dict[str, Any]):
        """Emit order created event"""
        return await self.webhook_system.emit_event(
            WebhookEventType.ORDER_CREATED,
            order_data
        )
    
    async def order_filled(self, order_data: Dict[str, Any], fill_data: Dict[str, Any]):
        """Emit order filled event"""
        return await self.webhook_system.emit_event(
            WebhookEventType.ORDER_FILLED,
            {
                'order': order_data,
                'fill': fill_data
            }
        )
    
    async def position_opened(self, position_data: Dict[str, Any]):
        """Emit position opened event"""
        return await self.webhook_system.emit_event(
            WebhookEventType.POSITION_OPENED,
            position_data
        )
    
    async def risk_alert(self, alert_data: Dict[str, Any]):
        """Emit risk alert event"""
        return await self.webhook_system.emit_event(
            WebhookEventType.RISK_ALERT,
            alert_data,
            metadata={'priority': 'high'}
        )
    
    async def strategy_signal(self, signal_data: Dict[str, Any]):
        """Emit strategy signal event"""
        return await self.webhook_system.emit_event(
            WebhookEventType.STRATEGY_SIGNAL,
            signal_data
        )

# Factory function
def create_webhook_system(max_concurrent_deliveries: int = 100) -> WebhookEventSystem:
    """Create webhook event system"""
    return WebhookEventSystem(max_concurrent_deliveries)

# Example usage
if __name__ == "__main__":
    async def main():
        # Create webhook system
        webhook_system = create_webhook_system()
        await webhook_system.start()
        
        # Register a test endpoint
        endpoint = WebhookEndpoint(
            id="test-endpoint",
            url="https://httpbin.org/post",
            name="Test Endpoint",
            description="Test webhook endpoint",
            events=[WebhookEventType.ORDER_CREATED, WebhookEventType.ORDER_FILLED],
            security_type=WebhookSecurityType.HMAC_SHA256,
            secret="test-secret-key"
        )
        
        webhook_system.register_endpoint(endpoint)
        
        # Create webhook events helper
        events = WebhookEvents(webhook_system)
        
        # Emit test events
        await events.order_created({
            'id': 'order-123',
            'symbol': 'AAPL',
            'side': 'buy',
            'quantity': 100,
            'price': 150.25
        })
        
        # Wait a bit for delivery
        await asyncio.sleep(2)
        
        # Get stats
        stats = webhook_system.get_delivery_stats()
        print(f"Delivery stats: {stats}")
        
        # Stop system
        await webhook_system.stop()
    
    asyncio.run(main())