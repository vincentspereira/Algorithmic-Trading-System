#!/usr/bin/env python3
"""
WebSocket Notifications System for Real-Time Order Status Tracking
Provides real-time order status updates via WebSocket connections
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Set, Optional, Any, Callable
from dataclasses import dataclass, asdict
import websockets
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed, WebSocketException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationType(Enum):
    """Types of notifications"""
    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    ORDER_ACCEPTED = "ORDER_ACCEPTED"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_PARTIALLY_FILLED = "ORDER_PARTIALLY_FILLED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_MODIFIED = "ORDER_MODIFIED"
    ORDER_EXPIRED = "ORDER_EXPIRED"
    EXECUTION_REPORT = "EXECUTION_REPORT"
    POSITION_UPDATE = "POSITION_UPDATE"
    PNL_UPDATE = "PNL_UPDATE"
    RISK_ALERT = "RISK_ALERT"
    SYSTEM_STATUS = "SYSTEM_STATUS"

class SubscriptionType(Enum):
    """Types of subscriptions"""
    ALL_ORDERS = "ALL_ORDERS"
    ACCOUNT_ORDERS = "ACCOUNT_ORDERS"
    STRATEGY_ORDERS = "STRATEGY_ORDERS"
    SYMBOL_ORDERS = "SYMBOL_ORDERS"
    SPECIFIC_ORDER = "SPECIFIC_ORDER"
    POSITIONS = "POSITIONS"
    PNL = "PNL"
    RISK_ALERTS = "RISK_ALERTS"
    SYSTEM_STATUS = "SYSTEM_STATUS"

@dataclass
class NotificationMessage:
    """Notification message structure"""
    id: str
    type: NotificationType
    timestamp: datetime
    data: Dict[str, Any]
    subscription_filters: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            'id': self.id,
            'type': self.type.value,
            'timestamp': self.timestamp.isoformat(),
            'data': self._serialize_data(self.data)
        }
        if self.subscription_filters:
            result['filters'] = self.subscription_filters
        return result
    
    def _serialize_data(self, data: Any) -> Any:
        """Serialize data for JSON transmission"""
        if isinstance(data, dict):
            return {k: self._serialize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._serialize_data(item) for item in data]
        elif isinstance(data, Decimal):
            return str(data)
        elif isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, Enum):
            return data.value
        elif hasattr(data, '__dict__'):
            return self._serialize_data(data.__dict__)
        else:
            return data

@dataclass
class Subscription:
    """Client subscription details"""
    client_id: str
    subscription_type: SubscriptionType
    filters: Dict[str, Any]
    created_at: datetime
    last_activity: datetime

class WebSocketNotificationServer:
    """WebSocket server for real-time order notifications"""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Dict[str, WebSocketServerProtocol] = {}
        self.subscriptions: Dict[str, List[Subscription]] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.running = False
        self.server = None
        self._background_tasks: Set[asyncio.Task] = set()
        
        logger.info(f"WebSocket Notification Server initialized on {host}:{port}")
    
    async def start(self):
        """Start the WebSocket server"""
        self.running = True
        
        # Start the WebSocket server
        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            ping_interval=30,
            ping_timeout=10
        )
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._message_processor()),
            asyncio.create_task(self._connection_monitor()),
            asyncio.create_task(self._heartbeat_sender())
        ]
        
        for task in tasks:
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
        
        logger.info(f"WebSocket server started on {self.host}:{self.port}")
    
    async def stop(self):
        """Stop the WebSocket server"""
        self.running = False
        
        # Close all client connections
        if self.clients:
            await asyncio.gather(
                *[client.close() for client in self.clients.values()],
                return_exceptions=True
            )
        
        # Stop the server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        logger.info("WebSocket server stopped")
    
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new client connection"""
        client_id = str(uuid.uuid4())
        self.clients[client_id] = websocket
        
        logger.info(f"Client {client_id} connected from {websocket.remote_address}")
        
        try:
            # Send welcome message
            welcome_msg = {
                'type': 'WELCOME',
                'client_id': client_id,
                'timestamp': datetime.now().isoformat(),
                'server_info': {
                    'version': '1.0.0',
                    'supported_subscriptions': [sub.value for sub in SubscriptionType]
                }
            }
            await websocket.send(json.dumps(welcome_msg))
            
            # Handle client messages
            async for message in websocket:
                try:
                    await self._handle_client_message(client_id, message)
                except json.JSONDecodeError as e:
                    await self._send_error(websocket, f"Invalid JSON: {e}")
                except Exception as e:
                    logger.error(f"Error handling message from {client_id}: {e}")
                    await self._send_error(websocket, f"Message processing error: {e}")
        
        except ConnectionClosed:
            logger.info(f"Client {client_id} disconnected")
        except WebSocketException as e:
            logger.error(f"WebSocket error for client {client_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error for client {client_id}: {e}")
        finally:
            # Clean up client
            self.clients.pop(client_id, None)
            self.subscriptions.pop(client_id, None)
            logger.info(f"Client {client_id} cleaned up")
    
    async def _handle_client_message(self, client_id: str, message: str):
        """Handle message from client"""
        data = json.loads(message)
        msg_type = data.get('type')
        
        if msg_type == 'SUBSCRIBE':
            await self._handle_subscription(client_id, data)
        elif msg_type == 'UNSUBSCRIBE':
            await self._handle_unsubscription(client_id, data)
        elif msg_type == 'PING':
            await self._handle_ping(client_id)
        else:
            logger.warning(f"Unknown message type from {client_id}: {msg_type}")
    
    async def _handle_subscription(self, client_id: str, data: Dict[str, Any]):
        """Handle subscription request"""
        try:
            subscription_type = SubscriptionType(data['subscription_type'])
            filters = data.get('filters', {})
            
            subscription = Subscription(
                client_id=client_id,
                subscription_type=subscription_type,
                filters=filters,
                created_at=datetime.now(),
                last_activity=datetime.now()
            )
            
            if client_id not in self.subscriptions:
                self.subscriptions[client_id] = []
            
            self.subscriptions[client_id].append(subscription)
            
            # Send confirmation
            response = {
                'type': 'SUBSCRIPTION_CONFIRMED',
                'subscription_type': subscription_type.value,
                'filters': filters,
                'timestamp': datetime.now().isoformat()
            }
            
            await self.clients[client_id].send(json.dumps(response))
            logger.info(f"Client {client_id} subscribed to {subscription_type.value} with filters {filters}")
            
        except ValueError as e:
            await self._send_error(self.clients[client_id], f"Invalid subscription type: {e}")
        except Exception as e:
            await self._send_error(self.clients[client_id], f"Subscription error: {e}")
    
    async def _handle_unsubscription(self, client_id: str, data: Dict[str, Any]):
        """Handle unsubscription request"""
        try:
            subscription_type = SubscriptionType(data['subscription_type'])
            
            if client_id in self.subscriptions:
                self.subscriptions[client_id] = [
                    sub for sub in self.subscriptions[client_id]
                    if sub.subscription_type != subscription_type
                ]
            
            response = {
                'type': 'UNSUBSCRIPTION_CONFIRMED',
                'subscription_type': subscription_type.value,
                'timestamp': datetime.now().isoformat()
            }
            
            await self.clients[client_id].send(json.dumps(response))
            logger.info(f"Client {client_id} unsubscribed from {subscription_type.value}")
            
        except ValueError as e:
            await self._send_error(self.clients[client_id], f"Invalid subscription type: {e}")
    
    async def _handle_ping(self, client_id: str):
        """Handle ping message"""
        response = {
            'type': 'PONG',
            'timestamp': datetime.now().isoformat()
        }
        await self.clients[client_id].send(json.dumps(response))
    
    async def _send_error(self, websocket: WebSocketServerProtocol, error_message: str):
        """Send error message to client"""
        error_response = {
            'type': 'ERROR',
            'message': error_message,
            'timestamp': datetime.now().isoformat()
        }
        try:
            await websocket.send(json.dumps(error_response))
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")
    
    async def send_notification(self, notification: NotificationMessage):
        """Send notification to subscribed clients"""
        await self.message_queue.put(notification)
    
    async def _message_processor(self):
        """Process queued messages and send to appropriate clients"""
        while self.running:
            try:
                # Wait for message with timeout
                try:
                    notification = await asyncio.wait_for(
                        self.message_queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Find matching subscriptions
                matching_clients = self._find_matching_clients(notification)
                
                # Send to matching clients
                if matching_clients:
                    message_json = json.dumps(notification.to_dict())
                    
                    send_tasks = []
                    for client_id in matching_clients:
                        if client_id in self.clients:
                            task = asyncio.create_task(
                                self._send_to_client(client_id, message_json)
                            )
                            send_tasks.append(task)
                    
                    if send_tasks:
                        await asyncio.gather(*send_tasks, return_exceptions=True)
                
            except Exception as e:
                logger.error(f"Message processor error: {e}")
                await asyncio.sleep(1)
    
    def _find_matching_clients(self, notification: NotificationMessage) -> List[str]:
        """Find clients that should receive this notification"""
        matching_clients = []
        
        for client_id, subscriptions in self.subscriptions.items():
            for subscription in subscriptions:
                if self._matches_subscription(notification, subscription):
                    matching_clients.append(client_id)
                    break  # Only add client once
        
        return matching_clients
    
    def _matches_subscription(self, notification: NotificationMessage, subscription: Subscription) -> bool:
        """Check if notification matches subscription criteria"""
        # Check subscription type
        if subscription.subscription_type == SubscriptionType.ALL_ORDERS:
            return notification.type in [
                NotificationType.ORDER_SUBMITTED,
                NotificationType.ORDER_ACCEPTED,
                NotificationType.ORDER_REJECTED,
                NotificationType.ORDER_FILLED,
                NotificationType.ORDER_PARTIALLY_FILLED,
                NotificationType.ORDER_CANCELLED,
                NotificationType.ORDER_MODIFIED,
                NotificationType.ORDER_EXPIRED,
                NotificationType.EXECUTION_REPORT
            ]
        
        elif subscription.subscription_type == SubscriptionType.ACCOUNT_ORDERS:
            account_id = subscription.filters.get('account_id')
            return (account_id and 
                    notification.data.get('account_id') == account_id and
                    notification.type in [
                        NotificationType.ORDER_SUBMITTED,
                        NotificationType.ORDER_ACCEPTED,
                        NotificationType.ORDER_REJECTED,
                        NotificationType.ORDER_FILLED,
                        NotificationType.ORDER_PARTIALLY_FILLED,
                        NotificationType.ORDER_CANCELLED,
                        NotificationType.ORDER_MODIFIED,
                        NotificationType.ORDER_EXPIRED,
                        NotificationType.EXECUTION_REPORT
                    ])
        
        elif subscription.subscription_type == SubscriptionType.STRATEGY_ORDERS:
            strategy_id = subscription.filters.get('strategy_id')
            return (strategy_id and 
                    notification.data.get('strategy_id') == strategy_id and
                    notification.type in [
                        NotificationType.ORDER_SUBMITTED,
                        NotificationType.ORDER_ACCEPTED,
                        NotificationType.ORDER_REJECTED,
                        NotificationType.ORDER_FILLED,
                        NotificationType.ORDER_PARTIALLY_FILLED,
                        NotificationType.ORDER_CANCELLED,
                        NotificationType.ORDER_MODIFIED,
                        NotificationType.ORDER_EXPIRED,
                        NotificationType.EXECUTION_REPORT
                    ])
        
        elif subscription.subscription_type == SubscriptionType.SYMBOL_ORDERS:
            symbol = subscription.filters.get('symbol')
            return (symbol and 
                    notification.data.get('symbol') == symbol and
                    notification.type in [
                        NotificationType.ORDER_SUBMITTED,
                        NotificationType.ORDER_ACCEPTED,
                        NotificationType.ORDER_REJECTED,
                        NotificationType.ORDER_FILLED,
                        NotificationType.ORDER_PARTIALLY_FILLED,
                        NotificationType.ORDER_CANCELLED,
                        NotificationType.ORDER_MODIFIED,
                        NotificationType.ORDER_EXPIRED,
                        NotificationType.EXECUTION_REPORT
                    ])
        
        elif subscription.subscription_type == SubscriptionType.SPECIFIC_ORDER:
            order_id = subscription.filters.get('order_id')
            return (order_id and 
                    notification.data.get('order_id') == order_id)
        
        elif subscription.subscription_type == SubscriptionType.POSITIONS:
            return notification.type == NotificationType.POSITION_UPDATE
        
        elif subscription.subscription_type == SubscriptionType.PNL:
            return notification.type == NotificationType.PNL_UPDATE
        
        elif subscription.subscription_type == SubscriptionType.RISK_ALERTS:
            return notification.type == NotificationType.RISK_ALERT
        
        elif subscription.subscription_type == SubscriptionType.SYSTEM_STATUS:
            return notification.type == NotificationType.SYSTEM_STATUS
        
        return False
    
    async def _send_to_client(self, client_id: str, message: str):
        """Send message to specific client"""
        try:
            if client_id in self.clients:
                await self.clients[client_id].send(message)
        except ConnectionClosed:
            logger.info(f"Client {client_id} connection closed during send")
            self.clients.pop(client_id, None)
            self.subscriptions.pop(client_id, None)
        except Exception as e:
            logger.error(f"Error sending to client {client_id}: {e}")
    
    async def _connection_monitor(self):
        """Monitor client connections and clean up stale ones"""
        while self.running:
            try:
                current_time = datetime.now()
                stale_clients = []
                
                for client_id, websocket in self.clients.items():
                    if websocket.closed:
                        stale_clients.append(client_id)
                
                # Clean up stale clients
                for client_id in stale_clients:
                    self.clients.pop(client_id, None)
                    self.subscriptions.pop(client_id, None)
                    logger.info(f"Cleaned up stale client {client_id}")
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Connection monitor error: {e}")
                await asyncio.sleep(60)
    
    async def _heartbeat_sender(self):
        """Send periodic heartbeat to all clients"""
        while self.running:
            try:
                if self.clients:
                    heartbeat_msg = {
                        'type': 'HEARTBEAT',
                        'timestamp': datetime.now().isoformat(),
                        'active_clients': len(self.clients),
                        'active_subscriptions': sum(len(subs) for subs in self.subscriptions.values())
                    }
                    
                    message_json = json.dumps(heartbeat_msg)
                    
                    send_tasks = []
                    for client_id in list(self.clients.keys()):
                        task = asyncio.create_task(
                            self._send_to_client(client_id, message_json)
                        )
                        send_tasks.append(task)
                    
                    if send_tasks:
                        await asyncio.gather(*send_tasks, return_exceptions=True)
                
                await asyncio.sleep(60)  # Send heartbeat every minute
                
            except Exception as e:
                logger.error(f"Heartbeat sender error: {e}")
                await asyncio.sleep(60)
    
    def get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        subscription_counts = {}
        for subscriptions in self.subscriptions.values():
            for sub in subscriptions:
                sub_type = sub.subscription_type.value
                subscription_counts[sub_type] = subscription_counts.get(sub_type, 0) + 1
        
        return {
            'active_clients': len(self.clients),
            'total_subscriptions': sum(len(subs) for subs in self.subscriptions.values()),
            'subscription_breakdown': subscription_counts,
            'server_uptime': time.time(),
            'message_queue_size': self.message_queue.qsize()
        }

class OrderNotificationManager:
    """Manager for order-related notifications"""
    
    def __init__(self, websocket_server: WebSocketNotificationServer):
        self.websocket_server = websocket_server
        self.notification_history: List[NotificationMessage] = []
        self.max_history_size = 1000
    
    async def notify_order_submitted(self, order_data: Dict[str, Any]):
        """Notify that an order was submitted"""
        notification = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.ORDER_SUBMITTED,
            timestamp=datetime.now(),
            data=order_data
        )
        
        await self._send_notification(notification)
    
    async def notify_order_accepted(self, order_data: Dict[str, Any]):
        """Notify that an order was accepted"""
        notification = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.ORDER_ACCEPTED,
            timestamp=datetime.now(),
            data=order_data
        )
        
        await self._send_notification(notification)
    
    async def notify_order_rejected(self, order_data: Dict[str, Any], reason: str):
        """Notify that an order was rejected"""
        data = order_data.copy()
        data['rejection_reason'] = reason
        
        notification = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.ORDER_REJECTED,
            timestamp=datetime.now(),
            data=data
        )
        
        await self._send_notification(notification)
    
    async def notify_order_filled(self, order_data: Dict[str, Any], execution_data: Dict[str, Any]):
        """Notify that an order was filled"""
        data = order_data.copy()
        data['execution'] = execution_data
        
        notification = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.ORDER_FILLED,
            timestamp=datetime.now(),
            data=data
        )
        
        await self._send_notification(notification)
    
    async def notify_order_partially_filled(self, order_data: Dict[str, Any], execution_data: Dict[str, Any]):
        """Notify that an order was partially filled"""
        data = order_data.copy()
        data['execution'] = execution_data
        
        notification = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.ORDER_PARTIALLY_FILLED,
            timestamp=datetime.now(),
            data=data
        )
        
        await self._send_notification(notification)
    
    async def notify_order_cancelled(self, order_data: Dict[str, Any], reason: str):
        """Notify that an order was cancelled"""
        data = order_data.copy()
        data['cancellation_reason'] = reason
        
        notification = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.ORDER_CANCELLED,
            timestamp=datetime.now(),
            data=data
        )
        
        await self._send_notification(notification)
    
    async def notify_order_modified(self, order_data: Dict[str, Any], changes: Dict[str, Any]):
        """Notify that an order was modified"""
        data = order_data.copy()
        data['changes'] = changes
        
        notification = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.ORDER_MODIFIED,
            timestamp=datetime.now(),
            data=data
        )
        
        await self._send_notification(notification)
    
    async def notify_execution_report(self, execution_data: Dict[str, Any]):
        """Notify of an execution report"""
        notification = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.EXECUTION_REPORT,
            timestamp=datetime.now(),
            data=execution_data
        )
        
        await self._send_notification(notification)
    
    async def notify_position_update(self, position_data: Dict[str, Any]):
        """Notify of position update"""
        notification = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.POSITION_UPDATE,
            timestamp=datetime.now(),
            data=position_data
        )
        
        await self._send_notification(notification)
    
    async def notify_pnl_update(self, pnl_data: Dict[str, Any]):
        """Notify of P&L update"""
        notification = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.PNL_UPDATE,
            timestamp=datetime.now(),
            data=pnl_data
        )
        
        await self._send_notification(notification)
    
    async def notify_risk_alert(self, alert_data: Dict[str, Any]):
        """Notify of risk alert"""
        notification = NotificationMessage(
            id=str(uuid.uuid4()),
            type=NotificationType.RISK_ALERT,
            timestamp=datetime.now(),
            data=alert_data
        )
        
        await self._send_notification(notification)
    
    async def _send_notification(self, notification: NotificationMessage):
        """Send notification and store in history"""
        await self.websocket_server.send_notification(notification)
        
        # Store in history
        self.notification_history.append(notification)
        
        # Trim history if needed
        if len(self.notification_history) > self.max_history_size:
            self.notification_history = self.notification_history[-self.max_history_size:]
    
    def get_notification_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent notification history"""
        recent_notifications = self.notification_history[-limit:]
        return [notification.to_dict() for notification in recent_notifications]

async def main():
    """Example usage of WebSocket notification system"""
    # Create and start WebSocket server
    websocket_server = WebSocketNotificationServer(host="localhost", port=8765)
    notification_manager = OrderNotificationManager(websocket_server)
    
    try:
        await websocket_server.start()
        print("WebSocket server started on ws://localhost:8765")
        print("Connect with a WebSocket client and send subscription messages")
        
        # Simulate some notifications
        await asyncio.sleep(2)
        
        # Simulate order events
        order_data = {
            'order_id': 'TEST_001',
            'symbol': 'EURUSD',
            'side': 'BUY',
            'quantity': '10000',
            'price': '1.1000',
            'account_id': 'ACCOUNT_001',
            'strategy_id': 'STRATEGY_001'
        }
        
        await notification_manager.notify_order_submitted(order_data)
        await asyncio.sleep(1)
        
        await notification_manager.notify_order_accepted(order_data)
        await asyncio.sleep(1)
        
        execution_data = {
            'execution_id': 'EXEC_001',
            'quantity': '10000',
            'price': '1.1001',
            'venue': 'ECN_PRIMARY'
        }
        
        await notification_manager.notify_order_filled(order_data, execution_data)
        
        # Keep server running
        print("Server running... Press Ctrl+C to stop")
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("Shutting down server...")
    finally:
        await websocket_server.stop()

if __name__ == "__main__":
    asyncio.run(main())