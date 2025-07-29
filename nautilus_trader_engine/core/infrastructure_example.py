"""
Infrastructure Usage Example
Demonstrates how to use the integrated core infrastructure components
"""

import asyncio
import logging
from typing import Dict, Any

from nautilus_trader_engine.core import (
    InfrastructureManager, InfrastructureConfig,
    start_infrastructure, stop_infrastructure
)


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def trading_data_pipeline_example():
    """
    Example of a complete trading data pipeline using all infrastructure components
    """
    
    # Configure infrastructure for high-performance trading
    config = InfrastructureConfig(
        # Message bus - high throughput configuration
        message_bus_buffer_size=131072,  # 128K buffer
        message_bus_batch_size=500,
        
        # Cache - multi-level for ultra-low latency
        cache_l1_size=50000,  # Large L1 cache for hot data
        cache_l2_enabled=True,
        cache_l3_enabled=True,
        
        # Network - optimized for trading
        network_enable_kernel_bypass=False,  # Would be True in production
        network_enable_numa=False,           # Would be True in production
        network_pool_size=200,
        network_cpu_cores=[0, 1, 2, 3, 4, 5, 6, 7],
        
        # Monitoring
        metrics_enabled=True,
        metrics_collection_interval=0.5,  # High frequency metrics
        
        log_level="INFO"
    )
    
    # Start infrastructure
    logger.info("🚀 Starting trading infrastructure...")
    infrastructure = await start_infrastructure(config)
    
    try:
        # Example 1: Market data processing pipeline
        await market_data_pipeline(infrastructure)
        
        # Example 2: Order processing pipeline  
        await order_processing_pipeline(infrastructure)
        
        # Example 3: Risk monitoring pipeline
        await risk_monitoring_pipeline(infrastructure)
        
        # Show comprehensive metrics
        await show_infrastructure_metrics(infrastructure)
        
    finally:
        # Clean shutdown
        logger.info("🛑 Stopping trading infrastructure...")
        await stop_infrastructure()


async def market_data_pipeline(infrastructure: InfrastructureManager):
    """Example market data processing pipeline"""
    logger.info("📊 Setting up market data pipeline...")
    
    # Market data cache for ultra-fast lookups
    market_data_cache = {}
    
    async def process_market_data(message: Dict[str, Any]):
        """Process incoming market data with caching"""
        symbol = message.get('symbol')
        price = message.get('price')
        timestamp = message.get('timestamp')
        
        # Cache key for latest price
        cache_key = f"latest_price:{symbol}"
        
        # Get previous price from cache
        previous_data = await infrastructure.cache_get(cache_key)
        
        # Calculate price change
        price_change = 0.0
        if previous_data:
            price_change = price - previous_data.get('price', price)
        
        # Create enriched market data
        enriched_data = {
            'symbol': symbol,
            'price': price,
            'timestamp': timestamp,
            'price_change': price_change,
            'price_change_pct': (price_change / price * 100) if price > 0 else 0.0
        }
        
        # Cache the latest data
        await infrastructure.cache_set(cache_key, enriched_data, ttl=60)
        
        # Publish enriched data for downstream processing
        await infrastructure.publish_message("market.enriched", enriched_data)
        
        logger.info(f"📈 Processed {symbol}: ${price:.2f} ({price_change:+.2f})")
    
    # Subscribe to raw market data
    await infrastructure.subscribe_to_topic("market.raw", process_market_data)
    
    # Simulate market data feed
    test_data = [
        {'symbol': 'AAPL', 'price': 150.00, 'timestamp': '2024-01-01T10:00:00Z'},
        {'symbol': 'AAPL', 'price': 150.50, 'timestamp': '2024-01-01T10:00:01Z'},
        {'symbol': 'TSLA', 'price': 800.00, 'timestamp': '2024-01-01T10:00:00Z'},
        {'symbol': 'TSLA', 'price': 802.50, 'timestamp': '2024-01-01T10:00:01Z'},
    ]
    
    for data in test_data:
        await infrastructure.publish_message("market.raw", data)
        await asyncio.sleep(0.1)  # Simulate real-time feed


async def order_processing_pipeline(infrastructure: InfrastructureManager):
    """Example order processing pipeline"""
    logger.info("📋 Setting up order processing pipeline...")
    
    async def process_order(message: Dict[str, Any]):
        """Process trading orders with validation and caching"""
        order_id = message.get('order_id')
        symbol = message.get('symbol')
        quantity = message.get('quantity')
        order_type = message.get('type', 'market')
        
        # Get latest market data from cache for validation
        market_data = await infrastructure.cache_get(f"latest_price:{symbol}")
        
        if not market_data:
            logger.warning(f"⚠️  No market data available for {symbol}")
            return
        
        # Validate order
        current_price = market_data.get('price', 0)
        estimated_value = current_price * quantity
        
        # Cache order for tracking
        order_cache_key = f"order:{order_id}"
        order_data = {
            'order_id': order_id,
            'symbol': symbol,
            'quantity': quantity,
            'type': order_type,
            'estimated_value': estimated_value,
            'status': 'validated',
            'market_price': current_price
        }
        
        await infrastructure.cache_set(order_cache_key, order_data, ttl=3600)
        
        # Publish for execution
        await infrastructure.publish_message("orders.validated", order_data)
        
        logger.info(f"✅ Order {order_id}: {quantity} {symbol} @ ~${current_price:.2f}")
    
    # Subscribe to order processing
    await infrastructure.subscribe_to_topic("orders.new", process_order)
    
    # Simulate some orders
    test_orders = [
        {'order_id': 'ORD001', 'symbol': 'AAPL', 'quantity': 100, 'type': 'market'},
        {'order_id': 'ORD002', 'symbol': 'TSLA', 'quantity': 50, 'type': 'limit'},
    ]
    
    await asyncio.sleep(0.5)  # Wait for market data to be processed
    
    for order in test_orders:
        await infrastructure.publish_message("orders.new", order)
        await asyncio.sleep(0.1)


async def risk_monitoring_pipeline(infrastructure: InfrastructureManager):
    """Example risk monitoring pipeline"""
    logger.info("🛡️  Setting up risk monitoring pipeline...")
    
    # Risk limits
    POSITION_LIMIT = 1000000  # $1M position limit
    DAILY_LOSS_LIMIT = 50000  # $50K daily loss limit
    
    async def monitor_risk(message: Dict[str, Any]):
        """Monitor risk for validated orders"""
        order_id = message.get('order_id')
        estimated_value = message.get('estimated_value', 0)
        
        # Get current portfolio exposure from cache
        portfolio_key = "portfolio:exposure"
        current_exposure = await infrastructure.cache_get(portfolio_key) or 0
        
        # Calculate new exposure
        new_exposure = current_exposure + estimated_value
        
        # Check position limit
        if new_exposure > POSITION_LIMIT:
            risk_alert = {
                'type': 'POSITION_LIMIT_BREACH',
                'order_id': order_id,
                'current_exposure': current_exposure,
                'new_exposure': new_exposure,
                'limit': POSITION_LIMIT,
                'severity': 'HIGH'
            }
            
            await infrastructure.publish_message("risk.alerts", risk_alert)
            logger.warning(f"🚨 Position limit breach: ${new_exposure:,.2f} > ${POSITION_LIMIT:,.2f}")
            return
        
        # Update portfolio exposure
        await infrastructure.cache_set(portfolio_key, new_exposure, ttl=86400)
        
        # Publish risk assessment
        risk_assessment = {
            'order_id': order_id,
            'risk_level': 'LOW' if new_exposure < POSITION_LIMIT * 0.8 else 'MEDIUM',
            'portfolio_exposure': new_exposure,
            'utilization_pct': (new_exposure / POSITION_LIMIT) * 100
        }
        
        await infrastructure.publish_message("risk.assessments", risk_assessment)
        logger.info(f"🛡️  Risk OK: {risk_assessment['utilization_pct']:.1f}% utilization")
    
    # Subscribe to validated orders for risk monitoring
    await infrastructure.subscribe_to_topic("orders.validated", monitor_risk)


async def show_infrastructure_metrics(infrastructure: InfrastructureManager):
    """Display comprehensive infrastructure metrics"""
    logger.info("📊 Infrastructure Performance Metrics:")
    
    # Wait a bit for metrics to accumulate
    await asyncio.sleep(2.0)
    
    metrics = infrastructure.get_comprehensive_metrics()
    health = infrastructure.get_health_status()
    
    print("\n" + "="*60)
    print("INFRASTRUCTURE PERFORMANCE REPORT")
    print("="*60)
    
    # Health status
    print(f"\n🏥 HEALTH STATUS:")
    print(f"   Overall Healthy: {'✅' if health['overall_healthy'] else '❌'}")
    print(f"   Message Bus: {'✅' if health['message_bus'] else '❌'}")
    print(f"   Cache Manager: {'✅' if health['cache_manager'] else '❌'}")
    print(f"   Network Manager: {'✅' if health['network_manager'] else '❌'}")
    
    # Messaging metrics
    if 'messaging' in metrics:
        msg_metrics = metrics['messaging']
        print(f"\n📨 MESSAGING METRICS:")
        print(f"   Messages Processed: {msg_metrics.get('messages_processed', 0):,}")
        print(f"   Messages/Second: {msg_metrics.get('messages_per_second', 0):.1f}")
        print(f"   Average Latency: {msg_metrics.get('average_latency_us', 0):.1f}μs")
        print(f"   Queue Depth: {msg_metrics.get('queue_depth', 0)}")
    
    # Caching metrics
    if 'caching' in metrics:
        cache_metrics = metrics['caching']
        print(f"\n💾 CACHING METRICS:")
        print(f"   Hit Rate: {cache_metrics.get('hit_rate', 0):.1%}")
        print(f"   Total Requests: {cache_metrics.get('total_requests', 0):,}")
        print(f"   Cache Hits: {cache_metrics.get('hits', 0):,}")
        print(f"   Cache Misses: {cache_metrics.get('misses', 0):,}")
        print(f"   L1 Size: {cache_metrics.get('l1_size', 0):,}")
    
    # Network metrics
    if 'networking' in metrics:
        net_metrics = metrics['networking']
        print(f"\n🌐 NETWORKING METRICS:")
        print(f"   Active Connections: {net_metrics.get('active_connections', 0)}")
        print(f"   Total Connections: {net_metrics.get('total_connections', 0)}")
        print(f"   Average Latency: {net_metrics.get('average_latency_ms', 0):.2f}ms")
        print(f"   Bytes Sent: {net_metrics.get('bytes_sent', 0):,}")
        print(f"   Bytes Received: {net_metrics.get('bytes_received', 0):,}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    # Run the complete example
    asyncio.run(trading_data_pipeline_example())