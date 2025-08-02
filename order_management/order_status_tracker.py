#!/usr/bin/env python3
"""
Real-Time Order Status Tracking and Notification System
Provides comprehensive order status monitoring, real-time updates, and notification management.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import websockets
from collections import defaultdict, deque

from order_lifecycle_manager import Order, OrderStatus, OrderSide, TCAMetrics

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class NotificationType(Enum):
    """Types of notifications"""
    ORDER_STATUS_CHANGE = "order_status_change"
    EXECUTION_UPDATE = "execution_update"
    RISK_ALERT = "risk_alert"
    PERFORMANCE_ALERT = "performance_alert"
    SYSTEM_ALERT = "system_alert"
    TCA_ALERT = "tca_alert"

@dataclass
class OrderStatusUpdate:
    """Order status update notification"""
    order_id: str
    previous_status: OrderStatus
    current_status: OrderStatus
    timestamp: datetime
    reason: str = ""
    metadata: Dict[str, Any] = None

@dataclass
class ExecutionNotification:
    """Execution notification"""
    order_id: str
    execution_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    venue: str
    timestamp: datetime
    cumulative_quantity: float
    remaining_quantity: float
    average_price: float

@dataclass
class RiskAlert:
    """Risk-related alert"""
    alert_id: str
    order_id: str
    alert_type: str
    severity: NotificationPriority
    message: str
    threshold_value: float
    current_value: float
    timestamp: datetime
    auto_action_taken: bool = False

@dataclass
class PerformanceAlert:
    """Performance-related alert"""
    alert_id: str
    metric_name: str
    threshold_value: float
    current_value: float
    severity: NotificationPriority
    message: str
    timestamp: datetime
    affected_orders: List[str] = None

@dataclass
class NotificationSubscription:
    """Notification subscription configuration"""
    subscription_id: str
    client_id: str
    notification_types: Set[NotificationType]
    order_filters: Dict[str, Any] = None  # symbol, strategy_id, account_id, etc.
    priority_filter: NotificationPriority = NotificationPriority.LOW
    websocket: Optional[websockets.WebSocketServerProtocol] = None
    email: Optional[str] = None
    webhook_url: Optional[str] = None

class OrderStatusTracker:
    """Real-time order status tracking and notification system"""
    
    def __init__(self, order_lifecycle_manager):
        self.order_manager = order_lifecycle_manager
        self.subscriptions: Dict[str, NotificationSubscription] = {}
        self.notification_history: deque = deque(maxlen=10000)
        self.status_history: Dict[str, List[OrderStatusUpdate]] = defaultdict(list)
        self.execution_history: Dict[str, List[ExecutionNotification]] = defaultdict(list)
        self.risk_alerts: Dict[str, List[RiskAlert]] = defaultdict(list)
        self.performance_alerts: List[PerformanceAlert] = []
        
        # Performance monitoring
        self.performance_metrics = {
            'notification_latency': deque(maxlen=1000),
            'websocket_connections': 0,
            'notifications_sent': 0,
            'notifications_failed': 0
        }
        
        # Risk thresholds
        self.risk_thresholds = {
            'max_order_value': 1000000,  # $1M
            'max_position_size': 10000,   # 10K shares
            'max_daily_loss': 50000,      # $50K
            'max_execution_slippage': 0.005,  # 0.5%
            'min_fill_rate': 0.8,         # 80%
        }
        
        # Register event handlers with order manager
        self._register_event_handlers()
        
        # Start background tasks
        asyncio.create_task(self._monitor_performance())
        asyncio.create_task(self._cleanup_old_data())
    
    def _register_event_handlers(self):
        """Register event handlers with the order lifecycle manager"""
        self.order_manager.add_event_handler('order_created', self._handle_order_created)
        self.order_manager.add_event_handler('order_modified', self._handle_order_modified)
        self.order_manager.add_event_handler('order_cancelled', self._handle_order_cancelled)
        self.order_manager.add_event_handler('order_executed', self._handle_order_executed)
        self.order_manager.add_event_handler('tca_calculated', self._handle_tca_calculated)
    
    async def _handle_order_created(self, order: Order):
        """Handle order creation event"""
        await self._track_status_change(order, None, order.status, "Order created")
        await self._check_risk_limits(order)
    
    async def _handle_order_modified(self, order: Order, modification):
        """Handle order modification event"""
        await self._track_status_change(order, order.status, order.status, "Order modified")
    
    async def _handle_order_cancelled(self, order: Order):
        """Handle order cancellation event"""
        await self._track_status_change(order, OrderStatus.SUBMITTED, order.status, "Order cancelled")
    
    async def _handle_order_executed(self, order: Order, execution):
        """Handle order execution event"""
        # Track status change if applicable
        if order.status in [OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED]:
            previous_status = OrderStatus.SUBMITTED if order.filled_quantity == execution.quantity else OrderStatus.PARTIALLY_FILLED
            await self._track_status_change(order, previous_status, order.status, "Order executed")
        
        # Create execution notification
        execution_notification = ExecutionNotification(
            order_id=order.order_id,
            execution_id=execution.execution_id,
            symbol=order.symbol,
            side=order.side,
            quantity=execution.quantity,
            price=execution.price,
            venue=execution.venue,
            timestamp=execution.timestamp,
            cumulative_quantity=order.filled_quantity,
            remaining_quantity=order.remaining_quantity,
            average_price=order.average_fill_price
        )
        
        self.execution_history[order.order_id].append(execution_notification)
        await self._send_notification(NotificationType.EXECUTION_UPDATE, execution_notification)
        
        # Check for execution-related risks
        await self._check_execution_risks(order, execution)
    
    async def _handle_tca_calculated(self, order: Order, tca_metrics: TCAMetrics):
        """Handle TCA calculation event"""
        await self._check_tca_alerts(order, tca_metrics)
    
    async def _track_status_change(self, order: Order, previous_status: Optional[OrderStatus], 
                                 current_status: OrderStatus, reason: str):
        """Track order status changes"""
        status_update = OrderStatusUpdate(
            order_id=order.order_id,
            previous_status=previous_status,
            current_status=current_status,
            timestamp=datetime.now(),
            reason=reason,
            metadata={
                'symbol': order.symbol,
                'side': order.side.value,
                'quantity': order.quantity,
                'filled_quantity': order.filled_quantity,
                'remaining_quantity': order.remaining_quantity
            }
        )
        
        self.status_history[order.order_id].append(status_update)
        await self._send_notification(NotificationType.ORDER_STATUS_CHANGE, status_update)
        
        logger.info(f"Order {order.order_id} status changed: {previous_status} -> {current_status}")
    
    async def _check_risk_limits(self, order: Order):
        """Check order against risk limits"""
        alerts = []
        
        # Check order value
        order_value = order.quantity * (order.price or 0)
        if order_value > self.risk_thresholds['max_order_value']:
            alert = RiskAlert(
                alert_id=f"risk_{order.order_id}_{int(time.time())}",
                order_id=order.order_id,
                alert_type="order_value_limit",
                severity=NotificationPriority.HIGH,
                message=f"Order value ${order_value:,.2f} exceeds limit ${self.risk_thresholds['max_order_value']:,.2f}",
                threshold_value=self.risk_thresholds['max_order_value'],
                current_value=order_value,
                timestamp=datetime.now()
            )
            alerts.append(alert)
        
        # Check position size
        if order.quantity > self.risk_thresholds['max_position_size']:
            alert = RiskAlert(
                alert_id=f"risk_{order.order_id}_{int(time.time())}_pos",
                order_id=order.order_id,
                alert_type="position_size_limit",
                severity=NotificationPriority.HIGH,
                message=f"Order quantity {order.quantity:,.0f} exceeds position limit {self.risk_thresholds['max_position_size']:,.0f}",
                threshold_value=self.risk_thresholds['max_position_size'],
                current_value=order.quantity,
                timestamp=datetime.now()
            )
            alerts.append(alert)
        
        # Send risk alerts
        for alert in alerts:
            self.risk_alerts[order.order_id].append(alert)
            await self._send_notification(NotificationType.RISK_ALERT, alert)
    
    async def _check_execution_risks(self, order: Order, execution):
        """Check execution-related risks"""
        alerts = []
        
        # Check slippage
        if order.price and execution.price:
            slippage = abs(execution.price - order.price) / order.price
            if slippage > self.risk_thresholds['max_execution_slippage']:
                alert = RiskAlert(
                    alert_id=f"risk_{order.order_id}_{execution.execution_id}_slippage",
                    order_id=order.order_id,
                    alert_type="execution_slippage",
                    severity=NotificationPriority.MEDIUM,
                    message=f"Execution slippage {slippage:.2%} exceeds threshold {self.risk_thresholds['max_execution_slippage']:.2%}",
                    threshold_value=self.risk_thresholds['max_execution_slippage'],
                    current_value=slippage,
                    timestamp=datetime.now()
                )
                alerts.append(alert)
        
        # Check fill rate for completed orders
        if order.status == OrderStatus.FILLED:
            fill_rate = order.filled_quantity / order.quantity
            if fill_rate < self.risk_thresholds['min_fill_rate']:
                alert = RiskAlert(
                    alert_id=f"risk_{order.order_id}_fill_rate",
                    order_id=order.order_id,
                    alert_type="low_fill_rate",
                    severity=NotificationPriority.MEDIUM,
                    message=f"Fill rate {fill_rate:.2%} below threshold {self.risk_thresholds['min_fill_rate']:.2%}",
                    threshold_value=self.risk_thresholds['min_fill_rate'],
                    current_value=fill_rate,
                    timestamp=datetime.now()
                )
                alerts.append(alert)
        
        # Send risk alerts
        for alert in alerts:
            self.risk_alerts[order.order_id].append(alert)
            await self._send_notification(NotificationType.RISK_ALERT, alert)
    
    async def _check_tca_alerts(self, order: Order, tca_metrics: TCAMetrics):
        """Check TCA metrics for alerts"""
        alerts = []
        
        # Check high implementation shortfall
        if abs(tca_metrics.implementation_shortfall) > 1000:  # $1000 threshold
            alert = RiskAlert(
                alert_id=f"tca_{order.order_id}_shortfall",
                order_id=order.order_id,
                alert_type="high_implementation_shortfall",
                severity=NotificationPriority.MEDIUM,
                message=f"High implementation shortfall: ${tca_metrics.implementation_shortfall:,.2f}",
                threshold_value=1000,
                current_value=abs(tca_metrics.implementation_shortfall),
                timestamp=datetime.now()
            )
            alerts.append(alert)
        
        # Check high total cost
        cost_threshold = tca_metrics.quantity * tca_metrics.average_fill_price * 0.01  # 1% of order value
        if tca_metrics.total_cost > cost_threshold:
            alert = RiskAlert(
                alert_id=f"tca_{order.order_id}_cost",
                order_id=order.order_id,
                alert_type="high_transaction_cost",
                severity=NotificationPriority.MEDIUM,
                message=f"High transaction cost: ${tca_metrics.total_cost:,.2f} (>{cost_threshold:,.2f})",
                threshold_value=cost_threshold,
                current_value=tca_metrics.total_cost,
                timestamp=datetime.now()
            )
            alerts.append(alert)
        
        # Send TCA alerts
        for alert in alerts:
            self.risk_alerts[order.order_id].append(alert)
            await self._send_notification(NotificationType.TCA_ALERT, alert)
    
    async def subscribe_to_notifications(self, subscription: NotificationSubscription) -> str:
        """Subscribe to order notifications"""
        self.subscriptions[subscription.subscription_id] = subscription
        
        if subscription.websocket:
            self.performance_metrics['websocket_connections'] += 1
        
        logger.info(f"Added notification subscription: {subscription.subscription_id}")
        return subscription.subscription_id
    
    async def unsubscribe_from_notifications(self, subscription_id: str) -> bool:
        """Unsubscribe from notifications"""
        if subscription_id in self.subscriptions:
            subscription = self.subscriptions[subscription_id]
            if subscription.websocket:
                self.performance_metrics['websocket_connections'] -= 1
            
            del self.subscriptions[subscription_id]
            logger.info(f"Removed notification subscription: {subscription_id}")
            return True
        
        return False
    
    async def _send_notification(self, notification_type: NotificationType, data: Any):
        """Send notification to all relevant subscribers"""
        start_time = time.time()
        
        notification = {
            'type': notification_type.value,
            'timestamp': datetime.now().isoformat(),
            'data': asdict(data) if hasattr(data, '__dataclass_fields__') else data
        }
        
        # Add to history
        self.notification_history.append(notification)
        
        # Send to subscribers
        for subscription in self.subscriptions.values():
            try:
                # Check if subscriber is interested in this notification type
                if notification_type not in subscription.notification_types:
                    continue
                
                # Apply filters
                if not self._matches_filters(notification, subscription):
                    continue
                
                # Send via WebSocket
                if subscription.websocket:
                    try:
                        await subscription.websocket.send(json.dumps(notification, default=str))
                        self.performance_metrics['notifications_sent'] += 1
                    except websockets.exceptions.ConnectionClosed:
                        # Mark for cleanup
                        subscription.websocket = None
                        self.performance_metrics['websocket_connections'] -= 1
                    except Exception as e:
                        logger.error(f"Failed to send WebSocket notification: {e}")
                        self.performance_metrics['notifications_failed'] += 1
                
                # Send via webhook (placeholder)
                if subscription.webhook_url:
                    # Would implement HTTP POST to webhook URL
                    pass
                
                # Send via email (placeholder)
                if subscription.email:
                    # Would implement email notification
                    pass
                    
            except Exception as e:
                logger.error(f"Error sending notification to subscription {subscription.subscription_id}: {e}")
                self.performance_metrics['notifications_failed'] += 1
        
        # Track latency
        latency = (time.time() - start_time) * 1000  # milliseconds
        self.performance_metrics['notification_latency'].append(latency)
    
    def _matches_filters(self, notification: Dict[str, Any], subscription: NotificationSubscription) -> bool:
        """Check if notification matches subscription filters"""
        if not subscription.order_filters:
            return True
        
        data = notification.get('data', {})
        
        # Check order-specific filters
        for filter_key, filter_value in subscription.order_filters.items():
            if filter_key in data:
                if isinstance(filter_value, list):
                    if data[filter_key] not in filter_value:
                        return False
                else:
                    if data[filter_key] != filter_value:
                        return False
        
        return True
    
    def get_order_status_history(self, order_id: str) -> List[OrderStatusUpdate]:
        """Get status history for an order"""
        return self.status_history.get(order_id, [])
    
    def get_execution_history(self, order_id: str) -> List[ExecutionNotification]:
        """Get execution history for an order"""
        return self.execution_history.get(order_id, [])
    
    def get_risk_alerts(self, order_id: str = None) -> List[RiskAlert]:
        """Get risk alerts for an order or all orders"""
        if order_id:
            return self.risk_alerts.get(order_id, [])
        
        all_alerts = []
        for alerts in self.risk_alerts.values():
            all_alerts.extend(alerts)
        return sorted(all_alerts, key=lambda x: x.timestamp, reverse=True)
    
    def get_performance_alerts(self) -> List[PerformanceAlert]:
        """Get performance alerts"""
        return sorted(self.performance_alerts, key=lambda x: x.timestamp, reverse=True)
    
    def get_notification_statistics(self) -> Dict[str, Any]:
        """Get notification system statistics"""
        latencies = list(self.performance_metrics['notification_latency'])
        
        return {
            'active_subscriptions': len(self.subscriptions),
            'websocket_connections': self.performance_metrics['websocket_connections'],
            'notifications_sent': self.performance_metrics['notifications_sent'],
            'notifications_failed': self.performance_metrics['notifications_failed'],
            'notification_history_size': len(self.notification_history),
            'average_latency_ms': sum(latencies) / len(latencies) if latencies else 0,
            'max_latency_ms': max(latencies) if latencies else 0,
            'total_risk_alerts': sum(len(alerts) for alerts in self.risk_alerts.values()),
            'total_performance_alerts': len(self.performance_alerts)
        }
    
    async def _monitor_performance(self):
        """Monitor system performance and generate alerts"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Check notification latency
                latencies = list(self.performance_metrics['notification_latency'])
                if latencies:
                    avg_latency = sum(latencies) / len(latencies)
                    if avg_latency > 100:  # 100ms threshold
                        alert = PerformanceAlert(
                            alert_id=f"perf_latency_{int(time.time())}",
                            metric_name="notification_latency",
                            threshold_value=100,
                            current_value=avg_latency,
                            severity=NotificationPriority.MEDIUM,
                            message=f"High notification latency: {avg_latency:.2f}ms",
                            timestamp=datetime.now()
                        )
                        
                        self.performance_alerts.append(alert)
                        await self._send_notification(NotificationType.PERFORMANCE_ALERT, alert)
                
                # Check failure rate
                total_notifications = (self.performance_metrics['notifications_sent'] + 
                                     self.performance_metrics['notifications_failed'])
                if total_notifications > 0:
                    failure_rate = self.performance_metrics['notifications_failed'] / total_notifications
                    if failure_rate > 0.05:  # 5% threshold
                        alert = PerformanceAlert(
                            alert_id=f"perf_failure_{int(time.time())}",
                            metric_name="notification_failure_rate",
                            threshold_value=0.05,
                            current_value=failure_rate,
                            severity=NotificationPriority.HIGH,
                            message=f"High notification failure rate: {failure_rate:.2%}",
                            timestamp=datetime.now()
                        )
                        
                        self.performance_alerts.append(alert)
                        await self._send_notification(NotificationType.PERFORMANCE_ALERT, alert)
                
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
    
    async def _cleanup_old_data(self):
        """Clean up old data to prevent memory leaks"""
        while True:
            try:
                await asyncio.sleep(3600)  # Clean up every hour
                
                cutoff_time = datetime.now() - timedelta(days=7)  # Keep 7 days of data
                
                # Clean up old status history
                for order_id in list(self.status_history.keys()):
                    self.status_history[order_id] = [
                        update for update in self.status_history[order_id]
                        if update.timestamp > cutoff_time
                    ]
                    if not self.status_history[order_id]:
                        del self.status_history[order_id]
                
                # Clean up old execution history
                for order_id in list(self.execution_history.keys()):
                    self.execution_history[order_id] = [
                        exec_notif for exec_notif in self.execution_history[order_id]
                        if exec_notif.timestamp > cutoff_time
                    ]
                    if not self.execution_history[order_id]:
                        del self.execution_history[order_id]
                
                # Clean up old risk alerts
                for order_id in list(self.risk_alerts.keys()):
                    self.risk_alerts[order_id] = [
                        alert for alert in self.risk_alerts[order_id]
                        if alert.timestamp > cutoff_time
                    ]
                    if not self.risk_alerts[order_id]:
                        del self.risk_alerts[order_id]
                
                # Clean up old performance alerts
                self.performance_alerts = [
                    alert for alert in self.performance_alerts
                    if alert.timestamp > cutoff_time
                ]
                
                logger.info("Completed data cleanup")
                
            except Exception as e:
                logger.error(f"Error in data cleanup: {e}")

# Example usage
async def main():
    """Example usage of the Order Status Tracker"""
    from order_lifecycle_manager import OrderLifecycleManager
    
    # Create order manager and status tracker
    order_manager = OrderLifecycleManager()
    status_tracker = OrderStatusTracker(order_manager)
    
    # Create a subscription
    subscription = NotificationSubscription(
        subscription_id="test_subscription",
        client_id="test_client",
        notification_types={
            NotificationType.ORDER_STATUS_CHANGE,
            NotificationType.EXECUTION_UPDATE,
            NotificationType.RISK_ALERT
        },
        order_filters={'symbol': 'AAPL'},
        priority_filter=NotificationPriority.LOW
    )
    
    await status_tracker.subscribe_to_notifications(subscription)
    
    # Create and execute some orders to generate notifications
    order_data = {
        'symbol': 'AAPL',
        'side': 'buy',
        'order_type': 'limit',
        'quantity': 1000,
        'price': 150.00
    }
    
    order = await order_manager.create_order(order_data)
    
    # Simulate execution
    from order_lifecycle_manager import OrderExecution
    import uuid
    
    execution = OrderExecution(
        execution_id=str(uuid.uuid4()),
        order_id=order.order_id,
        symbol=order.symbol,
        side=order.side,
        quantity=500,
        price=150.05,
        timestamp=datetime.now(),
        venue='NYSE',
        commission=2.50
    )
    
    await order_manager.add_execution(execution)
    
    # Print statistics
    stats = status_tracker.get_notification_statistics()
    print(f"Notification Statistics: {json.dumps(stats, indent=2)}")
    
    # Keep running to demonstrate real-time notifications
    await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())