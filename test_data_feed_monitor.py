#!/usr/bin/env python3
"""
Test script for Data Feed Monitoring System
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nautilus_trader_engine.monitoring.data_feed_monitor import DataFeedMonitor, DataFeedAlertManager
from nautilus_trader_engine.core.data_feeds import DataFeedManager
from nautilus_trader_engine.monitoring.metrics_collection import MetricCollector

async def test_data_feed_monitoring():
    """Test the data feed monitoring system"""
    print("Testing Data Feed Monitoring System")
    print("=" * 50)
    
    # Initialize components
    data_feed_manager = DataFeedManager()
    metric_collector = MetricCollector()
    monitor = DataFeedMonitor(data_feed_manager, metric_collector)
    
    print("✓ DataFeedMonitor initialized successfully")
    
    # Test health checks
    print("\nPerforming health checks...")
    health_status = await monitor.perform_health_checks()
    print(f"✓ Health checks completed for {len(health_status)} data sources")
    
    # Test connectivity to a few sources
    print("\nTesting connectivity...")
    try:
        from nautilus_trader_engine.core.data_feeds import DataSource
        await monitor.test_data_feed_connectivity(DataSource.YAHOO_FINANCE)
        print("✓ Connectivity test completed for Yahoo Finance")
    except Exception as e:
        print(f"⚠ Connectivity test failed for Yahoo Finance: {e}")
    
    # Generate health report
    print("\nGenerating health report...")
    report = monitor.generate_health_report()
    print(f"✓ Health report generated")
    print(f"  Overall Health Score: {report['overall_health_score']:.2f}%")
    print(f"  Total Sources: {report['summary']['total_sources']}")
    print(f"  Healthy Sources: {report['summary']['healthy_sources']}")
    
    # Test alert manager
    print("\nTesting alert manager...")
    alert_manager = DataFeedAlertManager(monitor)
    alerts = alert_manager.evaluate_alerts()
    print(f"✓ Alert evaluation completed with {len(alerts)} active alerts")
    
    print("\n" + "=" * 50)
    print("Data Feed Monitoring Test Completed Successfully!")

if __name__ == "__main__":
    asyncio.run(test_data_feed_monitoring())