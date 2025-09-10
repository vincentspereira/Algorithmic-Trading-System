"""
Example demonstrating data feed switching functionality
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_feeds import DataFeedManager, DataSource, AssetClass


async def demonstrate_switching():
    """Demonstrate data feed switching functionality"""
    print("=== Data Feed Switching Example ===\n")
    
    # Initialize data feed manager
    manager = DataFeedManager()
    
    # Show initial configuration
    print("1. Initial Configuration:")
    print(f"   Switching enabled: {manager.switching_enabled}")
    print(f"   Switching thresholds: {manager.switching_thresholds}")
    print(f"   Preferred sources: {dict(manager.preferred_sources)}")
    print()
    
    # Update switching thresholds
    print("2. Updating switching thresholds:")
    manager.set_switching_thresholds(
        success_rate=0.95,
        response_time=2.0,
        consecutive_failures=2
    )
    print(f"   New thresholds: {manager.switching_thresholds}")
    print()
    
    # Simulate some performance data
    print("3. Simulating performance data:")
    yahoo_source = DataSource.YAHOO_FINANCE
    alpha_source = DataSource.ALPHA_VANTAGE
    
    # Simulate good performance for Yahoo Finance
    for i in range(10):
        success = i != 7  # Simulate one failure
        response_time = 0.5 + (i * 0.1)  # Gradually increasing response time
        manager._update_source_performance(yahoo_source, success, response_time)
    
    # Simulate excellent performance for Alpha Vantage
    for i in range(10):
        success = True
        response_time = 0.3 + (i * 0.05)  # Fast and consistent
        manager._update_source_performance(alpha_source, success, response_time)
    
    # Check performance metrics
    yahoo_perf = manager.get_source_performance(yahoo_source)
    alpha_perf = manager.get_source_performance(alpha_source)
    
    print(f"   Yahoo Finance performance: {yahoo_perf[yahoo_source]}")
    print(f"   Alpha Vantage performance: {alpha_perf[alpha_source]}")
    print()
    
    # Check health status
    print("4. Health status checks:")
    yahoo_healthy = manager._is_source_healthy(yahoo_source, {'status': 'healthy'})
    alpha_healthy = manager._is_source_healthy(alpha_source, {'status': 'healthy'})
    
    print(f"   Yahoo Finance healthy: {yahoo_healthy}")
    print(f"   Alpha Vantage healthy: {alpha_healthy}")
    print()
    
    # Consider preferred sources
    print("5. Considering preferred sources:")
    stock_asset = AssetClass.STOCK
    manager._consider_preferred_source(stock_asset, yahoo_source)
    manager._consider_preferred_source(stock_asset, alpha_source)
    
    print(f"   Preferred source for stocks: {manager.preferred_sources.get(stock_asset, 'None')}")
    print()
    
    # Reset performance for demonstration
    print("6. Resetting performance metrics:")
    manager.reset_source_performance()
    reset_perf = manager.get_source_performance(yahoo_source)
    print(f"   Yahoo Finance performance after reset: {reset_perf[yahoo_source]}")
    print()
    
    print("=== Example completed successfully ===")


if __name__ == "__main__":
    asyncio.run(demonstrate_switching())