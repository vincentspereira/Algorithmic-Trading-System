"""
Comprehensive test suite for the entire Data Feed System
"""

import unittest
import asyncio
import logging
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pandas as pd

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_feeds import (
    DataFeedManager,
    DataSource,
    AssetClass,
    DataRequest,
    DataResponse,
    DataFeedHealthMonitor,
    RateLimitManager
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestDataFeedSystem(unittest.TestCase):
    """Comprehensive test cases for the entire Data Feed System"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.data_feed_manager = DataFeedManager()
    
    def test_system_initialization(self):
        """Test that the entire data feed system initializes correctly"""
        # Check DataFeedManager
        self.assertIsInstance(self.data_feed_manager, DataFeedManager)
        self.assertIsNotNone(self.data_feed_manager.rate_limit_manager)
        self.assertIsNotNone(self.data_feed_manager.health_monitor)
        
        # Check RateLimitManager
        self.assertIsInstance(self.data_feed_manager.rate_limit_manager, RateLimitManager)
        
        # Check DataFeedHealthMonitor
        self.assertIsInstance(self.data_feed_manager.health_monitor, DataFeedHealthMonitor)
        
        # Check switching logic
        self.assertTrue(hasattr(self.data_feed_manager, 'switching_enabled'))
        self.assertTrue(hasattr(self.data_feed_manager, 'switching_thresholds'))
        self.assertTrue(hasattr(self.data_feed_manager, 'source_performance'))
        self.assertTrue(hasattr(self.data_feed_manager, 'preferred_sources'))
    
    def test_data_request_structure(self):
        """Test DataRequest structure"""
        request = DataRequest(
            ticker="AAPL",
            asset_class=AssetClass.STOCK,
            interval="1d",
            period="1mo",
            start_date="2023-01-01",
            end_date="2023-01-31"
        )
        
        self.assertEqual(request.ticker, "AAPL")
        self.assertEqual(request.asset_class, AssetClass.STOCK)
        self.assertEqual(request.interval, "1d")
        self.assertEqual(request.period, "1mo")
        self.assertEqual(request.start_date, "2023-01-01")
        self.assertEqual(request.end_date, "2023-01-31")
    
    def test_data_response_structure(self):
        """Test DataResponse structure"""
        data = pd.DataFrame({'close': [100, 101, 102]})
        response = DataResponse(
            data=data,
            source=DataSource.YAHOO_FINANCE,
            ticker="AAPL",
            asset_class=AssetClass.STOCK,
            metadata={"test": "data"},
            timestamp=1234567890.0,
            success=True,
            error_message=None
        )
        
        self.assertEqual(response.data.shape, (3, 1))
        self.assertEqual(response.source, DataSource.YAHOO_FINANCE)
        self.assertEqual(response.ticker, "AAPL")
        self.assertEqual(response.asset_class, AssetClass.STOCK)
        self.assertEqual(response.metadata, {"test": "data"})
        self.assertEqual(response.timestamp, 1234567890.0)
        self.assertTrue(response.success)
        self.assertIsNone(response.error_message)
    
    def test_rate_limit_manager(self):
        """Test RateLimitManager functionality"""
        rate_limiter = self.data_feed_manager.rate_limit_manager
        
        # Test can_make_request
        source = DataSource.YAHOO_FINANCE
        self.assertTrue(rate_limiter.can_make_request(source))
        
        # Test record_request
        rate_limiter.record_request(source)
        self.assertIn(source, rate_limiter.last_request_time)
        self.assertIn(source, rate_limiter.request_counts)
        self.assertEqual(rate_limiter.request_counts[source], 1)
    
    def test_health_monitor(self):
        """Test DataFeedHealthMonitor functionality"""
        health_monitor = self.data_feed_manager.health_monitor
        source = DataSource.YAHOO_FINANCE
        
        # Test record_health_check
        health_monitor.record_health_check(source, True, 0.5)
        health_monitor.record_health_check(source, False, 1.0)
        health_monitor.record_health_check(source, True, 0.8)
        
        # Test get_health_status
        health_status = health_monitor.get_health_status(source)
        self.assertIn('status', health_status)
        self.assertIn('success_rate', health_status)
        self.assertIn('avg_response_time', health_status)
        self.assertIn('total_checks', health_status)
        self.assertIn('successful_checks', health_status)
        
        # Test get_overall_health
        overall_health = health_monitor.get_overall_health()
        self.assertIn('overall_status', overall_health)
        self.assertIn('sources', overall_health)
    
    def test_source_priority_by_asset(self):
        """Test source priority configuration by asset class"""
        # Check that all asset classes have priority lists
        for asset_class in AssetClass:
            self.assertIn(asset_class, self.data_feed_manager.source_priority_by_asset)
            self.assertIsInstance(self.data_feed_manager.source_priority_by_asset[asset_class], list)
            self.assertGreater(len(self.data_feed_manager.source_priority_by_asset[asset_class]), 0)
    
    def test_get_supported_assets(self):
        """Test get_supported_assets functionality"""
        # Test with Yahoo Finance
        yahoo_assets = self.data_feed_manager.get_supported_assets(DataSource.YAHOO_FINANCE)
        self.assertIsInstance(yahoo_assets, list)
        self.assertIn(AssetClass.STOCK, yahoo_assets)
        self.assertIn(AssetClass.FOREX, yahoo_assets)
        
        # Test with Oanda
        oanda_assets = self.data_feed_manager.get_supported_assets(DataSource.OANDA)
        if oanda_assets:  # Only if Oanda is configured
            self.assertIn(AssetClass.FOREX, oanda_assets)
    
    def test_has_required_credentials(self):
        """Test _has_required_credentials functionality"""
        # Test with Yahoo Finance (no credentials required)
        self.assertTrue(self.data_feed_manager._has_required_credentials(DataSource.YAHOO_FINANCE))
        
        # Test with Alpha Vantage (requires API key)
        self.assertFalse(self.data_feed_manager._has_required_credentials(DataSource.ALPHA_VANTAGE))
        
        # Test with a manager that has credentials
        manager_with_keys = DataFeedManager(alpha_vantage_api_key="test_key")
        self.assertTrue(manager_with_keys._has_required_credentials(DataSource.ALPHA_VANTAGE))
    
    def test_switching_logic_integration(self):
        """Test integration of switching logic with core functionality"""
        # Test that switching is enabled by default
        self.assertTrue(self.data_feed_manager.switching_enabled)
        
        # Test setting switching thresholds
        self.data_feed_manager.set_switching_thresholds(
            success_rate=0.95,
            response_time=1.5,
            consecutive_failures=2
        )
        
        expected_thresholds = {
            'success_rate': 0.95,
            'response_time': 1.5,
            'consecutive_failures': 2
        }
        self.assertEqual(self.data_feed_manager.switching_thresholds, expected_thresholds)
        
        # Test enabling/disabling switching
        self.data_feed_manager.enable_switching(False)
        self.assertFalse(self.data_feed_manager.switching_enabled)
        
        self.data_feed_manager.enable_switching(True)
        self.assertTrue(self.data_feed_manager.switching_enabled)
        
        # Test performance tracking
        source = DataSource.YAHOO_FINANCE
        self.data_feed_manager._update_source_performance(source, True, 0.5)
        
        performance = self.data_feed_manager.get_source_performance(source)
        self.assertIn(source, performance)
        self.assertGreater(performance[source]['total_requests'], 0)
        
        # Test health checking with switching logic
        health_status = {'status': 'healthy'}
        is_healthy = self.data_feed_manager._is_source_healthy(source, health_status)
        self.assertTrue(is_healthy)
        
        # Test preferred source consideration
        asset_class = AssetClass.STOCK
        self.data_feed_manager.source_performance[source] = {
            'success_rate': 0.98,
            'avg_response_time': 0.3,
            'consecutive_failures': 0,
            'total_requests': 100,
            'successful_requests': 98
        }
        
        self.data_feed_manager._consider_preferred_source(asset_class, source)
        self.assertIn(asset_class, self.data_feed_manager.preferred_sources)
        self.assertEqual(self.data_feed_manager.preferred_sources[asset_class], source)
    
    def test_reset_functionality(self):
        """Test reset functionality for performance metrics"""
        source = DataSource.YAHOO_FINANCE
        
        # Set some performance data
        self.data_feed_manager.source_performance[source] = {
            'success_rate': 0.80,
            'avg_response_time': 2.0,
            'consecutive_failures': 3,
            'total_requests': 100,
            'successful_requests': 80
        }
        
        # Reset specific source
        self.data_feed_manager.reset_source_performance(source)
        
        # Should be reset to initial values
        performance = self.data_feed_manager.source_performance[source]
        self.assertEqual(performance['success_rate'], 1.0)
        self.assertEqual(performance['avg_response_time'], 0.0)
        self.assertEqual(performance['consecutive_failures'], 0)
        self.assertEqual(performance['total_requests'], 0)
        self.assertEqual(performance['successful_requests'], 0)


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestDataFeedSystem))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)