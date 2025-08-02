#!/usr/bin/env python3
"""
Enhanced Order Management System Integration
Integrates order lifecycle management, status tracking, and TCA into a unified system.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import asdict

from order_lifecycle_manager import OrderLifecycleManager, Order, OrderExecution
from order_status_tracker import (
    OrderStatusTracker, NotificationSubscription, NotificationType, NotificationPriority
)
from transaction_cost_analysis import TransactionCostAnalyzer, TCABenchmark

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedOrderManagementSystem:
    """
    Enhanced Order Management System that integrates:
    - Order lifecycle management with parent-child relationships
    - Real-time status tracking and notifications
    - Transaction cost analysis and execution quality measurement
    """
    
    def __init__(self):
        # Initialize core components
        self.order_manager = OrderLifecycleManager()
        self.status_tracker = OrderStatusTracker(self.order_manager)
        self.tca_analyzer = TransactionCostAnalyzer()
        
        # System statistics
        self.stats = {
            'orders_created': 0,
            'orders_executed': 0,
            'orders_cancelled': 0,
            'tca_analyses_completed': 0,
            'notifications_sent': 0
        }
        
        # Register additional event handlers
        self._register_integration_handlers()
        
        logger.info("Enhanced Order Management System initialized")
    
    def _register_integration_handlers(self):
        """Register integration event handlers"""
        self.order_manager.add_event_handler('order_created', self._handle_order_created)
        self.order_manager.add_event_handler('order_executed', self._handle_order_executed)
        self.order_manager.add_event_handler('order_cancelled', self._handle_order_cancelled)
        self.order_manager.add_event_handler('tca_calculated', self._handle_tca_completed)
    
    async def _handle_order_created(self, order: Order):
        """Handle order creation for integration"""
        self.stats['orders_created'] += 1
        logger.info(f"Order created: {order.order_id} for {order.symbol}")
    
    async def _handle_order_executed(self, order: Order, execution: OrderExecution):
        """Handle order execution for integration"""
        self.stats['orders_executed'] += 1
        
        # Trigger TCA analysis for completed orders
        if order.status.value in ['filled', 'partially_filled']:
            try:
                await self.tca_analyzer.analyze_order_execution(order)
                logger.info(f"TCA analysis completed for order {order.order_id}")
            except Exception as e:
                logger.error(f"TCA analysis failed for order {order.order_id}: {e}")
    
    async def _handle_order_cancelled(self, order: Order):
        """Handle order cancellation for integration"""
        self.stats['orders_cancelled'] += 1
        logger.info(f"Order cancelled: {order.order_id}")
    
    async def _handle_tca_completed(self, order: Order, tca_metrics):
        """Handle TCA completion for integration"""
        self.stats['tca_analyses_completed'] += 1
    
    # Order Management Interface
    async def create_order(self, order_data: Dict[str, Any]) -> Order:
        """Create a new order"""
        return await self.order_manager.create_order(order_data)
    
    async def modify_order(self, order_id: str, modifications: Dict[str, Any]):
        """Modify an existing order"""
        return await self.order_manager.modify_order(order_id, modifications)
    
    async def cancel_order(self, order_id: str, reason: str = "") -> bool:
        """Cancel an order"""
        return await self.order_manager.cancel_order(order_id, reason)
    
    async def add_execution(self, execution: OrderExecution) -> None:
        """Add an execution to an order"""
        await self.order_manager.add_execution(execution)
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self.order_manager.get_order(order_id)
    
    def get_orders_by_symbol(self, symbol: str) -> List[Order]:
        """Get orders by symbol"""
        return self.order_manager.get_orders_by_symbol(symbol)
    
    def get_orders_by_status(self, status) -> List[Order]:
        """Get orders by status"""
        return self.order_manager.get_orders_by_status(status)
    
    # Notification Management Interface
    async def subscribe_to_notifications(self, subscription: NotificationSubscription) -> str:
        """Subscribe to order notifications"""
        subscription_id = await self.status_tracker.subscribe_to_notifications(subscription)
        self.stats['notifications_sent'] += 1
        return subscription_id
    
    async def unsubscribe_from_notifications(self, subscription_id: str) -> bool:
        """Unsubscribe from notifications"""
        return await self.status_tracker.unsubscribe_from_notifications(subscription_id)
    
    def get_order_status_history(self, order_id: str):
        """Get order status history"""
        return self.status_tracker.get_order_status_history(order_id)
    
    def get_risk_alerts(self, order_id: str = None):
        """Get risk alerts"""
        return self.status_tracker.get_risk_alerts(order_id)
    
    # TCA Interface
    async def get_tca_analysis(self, order_id: str, benchmark: TCABenchmark = None):
        """Get TCA analysis for an order"""
        order = self.get_order(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        return await self.tca_analyzer.analyze_order_execution(order, benchmark)
    
    def get_tca_report(self, order_id: str):
        """Get existing TCA report"""
        return self.tca_analyzer.get_tca_report(order_id)
    
    def get_symbol_analytics(self, symbol: str, days: int = 30):
        """Get symbol analytics"""
        return self.tca_analyzer.get_symbol_analytics(symbol, days)
    
    # System Management Interface
    def get_system_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        order_stats = self.order_manager.get_order_statistics()
        notification_stats = self.status_tracker.get_notification_statistics()
        
        return {
            'system_stats': self.stats,
            'order_stats': order_stats,
            'notification_stats': notification_stats,
            'timestamp': datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform system health check"""
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'components': {}
        }
        
        try:
            # Check order manager
            order_count = len(self.order_manager.orders)
            health_status['components']['order_manager'] = {
                'status': 'healthy',
                'orders_count': order_count
            }
        except Exception as e:
            health_status['components']['order_manager'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['status'] = 'degraded'
        
        try:
            # Check status tracker
            subscription_count = len(self.status_tracker.subscriptions)
            health_status['components']['status_tracker'] = {
                'status': 'healthy',
                'subscriptions_count': subscription_count
            }
        except Exception as e:
            health_status['components']['status_tracker'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['status'] = 'degraded'
        
        try:
            # Check TCA analyzer
            tca_reports_count = len(self.tca_analyzer.tca_reports)
            health_status['components']['tca_analyzer'] = {
                'status': 'healthy',
                'reports_count': tca_reports_count
            }
        except Exception as e:
            health_status['components']['tca_analyzer'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['status'] = 'degraded'
        
        return health_status
    
    def export_system_data(self, format: str = 'json') -> str:
        """Export system data for backup or analysis"""
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'system_version': '1.0.0',
            'orders': {},
            'tca_reports': {},
            'statistics': self.get_system_statistics()
        }
        
        # Export orders
        for order_id, order in self.order_manager.orders.items():
            export_data['orders'][order_id] = asdict(order)
        
        # Export TCA reports
        for order_id, report in self.tca_analyzer.tca_reports.items():
            export_data['tca_reports'][order_id] = asdict(report)
        
        if format.lower() == 'json':
            return json.dumps(export_data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")

# Example usage and demonstration
async def main():
    """Demonstrate the Enhanced Order Management System"""
    print("🚀 Enhanced Order Management System Demo")
    print("=" * 50)
    
    # Initialize the system
    oms = EnhancedOrderManagementSystem()
    
    # Create a notification subscription
    subscription = NotificationSubscription(
        subscription_id="demo_subscription",
        client_id="demo_client",
        notification_types={
            NotificationType.ORDER_STATUS_CHANGE,
            NotificationType.EXECUTION_UPDATE,
            NotificationType.RISK_ALERT
        },
        priority_filter=NotificationPriority.LOW
    )
    
    await oms.subscribe_to_notifications(subscription)
    print("✅ Notification subscription created")
    
    # Create a parent order
    parent_order_data = {
        'symbol': 'AAPL',
        'side': 'buy',
        'order_type': 'limit',
        'quantity': 1000,
        'price': 150.00,
        'strategy_id': 'momentum_strategy',
        'account_id': 'demo_account'
    }
    
    parent_order = await oms.create_order(parent_order_data)
    print(f"✅ Created parent order: {parent_order.order_id}")
    
    # Create child orders
    child_orders = []
    for i in range(2):
        child_data = {
            'parent_order_id': parent_order.order_id,
            'symbol': 'AAPL',
            'side': 'buy',
            'order_type': 'limit',
            'quantity': 400 + i * 100,
            'price': 149.75 + i * 0.25,
            'strategy_id': 'momentum_strategy',
            'account_id': 'demo_account'
        }
        
        child_order = await oms.create_order(child_data)
        child_orders.append(child_order)
        print(f"✅ Created child order: {child_order.order_id}")
    
    # Simulate executions
    for i, child_order in enumerate(child_orders):
        execution = OrderExecution(
            execution_id=f"exec_{i+1}_{int(datetime.now().timestamp())}",
            order_id=child_order.order_id,
            symbol=child_order.symbol,
            side=child_order.side,
            quantity=child_order.quantity,
            price=child_order.price * 1.001,  # Slight slippage
            timestamp=datetime.now(),
            venue='NYSE' if i == 0 else 'NASDAQ',
            commission=2.50,
            fees=0.50,
            liquidity_flag='taker'
        )
        
        await oms.add_execution(execution)
        print(f"✅ Added execution for order {child_order.order_id}")
    
    # Wait a moment for TCA analysis
    await asyncio.sleep(1)
    
    # Get TCA reports
    for child_order in child_orders:
        tca_report = oms.get_tca_report(child_order.order_id)
        if tca_report:
            print(f"📊 TCA Report for {child_order.order_id}:")
            print(f"   Total Cost: ${tca_report.cost_breakdown.total_cost:.2f}")
            print(f"   Fill Rate: {tca_report.execution_quality.fill_rate:.1%}")
            print(f"   Recommendations: {len(tca_report.recommendations)}")
    
    # Get system statistics
    stats = oms.get_system_statistics()
    print(f"\n📈 System Statistics:")
    print(f"   Orders Created: {stats['system_stats']['orders_created']}")
    print(f"   Orders Executed: {stats['system_stats']['orders_executed']}")
    print(f"   TCA Analyses: {stats['system_stats']['tca_analyses_completed']}")
    
    # Perform health check
    health = await oms.health_check()
    print(f"\n🏥 System Health: {health['status'].upper()}")
    
    # Get symbol analytics
    symbol_analytics = oms.get_symbol_analytics('AAPL')
    if symbol_analytics:
        print(f"\n📊 AAPL Analytics:")
        print(f"   Orders Analyzed: {symbol_analytics['total_orders_analyzed']}")
        print(f"   Average Fill Rate: {symbol_analytics['average_fill_rate']:.1%}")
    
    print(f"\n🎉 Demo completed successfully!")
    print("WebSocket server running on ws://localhost:8765 for real-time notifications")

if __name__ == "__main__":
    asyncio.run(main())