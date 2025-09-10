"""
Test suite for Data Feed Switching Logic
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
    DataResponse
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestDataFeedSwitching(unittest.TestCase):
    """Test cases for Data Feed Switching Logic"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.data_feed_manager = DataFeedManager()
    
    def test_switching_initialization(self):
        """Test that switching logic is properly initialized"""
        self.assertTrue(hasattr(self.data_feed_manager, 'switching_enabled'))
        self.assertTrue(hasattr(self.data_feed_manager, 'switching_thresholds'))
        self.assertTrue(hasattr(self.data_feed_manager, 'source_performance'))
        self.assertTrue(hasattr(self.data_feed_manager, 'preferred_sources'))
        
        # Check default values
        self.assertTrue(self.data_feed_manager.switching_enabled)
        self.assertEqual(self.data_feed_manager.switching_thresholds['success_rate'], 0.90)
        self.assertEqual(self.data_feed_manager.switching_thresholds['response_time'], 3.0)
        self.assertEqual(self.data_feed_manager.switching_thresholds['consecutive_failures'], 3)
    
    def test_update_source_performance(self):
        """Test updating source performance metrics"""
        source = DataSource.YAHOO_FINANCE
        
        # Initial state
        performance = self.data_feed_manager.source_performance[source]
        self.assertEqual(performance['success_rate'], 1.0)
        self.assertEqual(performance['avg_response_time'], 0.0)
        self.assertEqual(performance['consecutive_failures'], 0)
        self.assertEqual(performance['total_requests'], 0)
        self.assertEqual(performance['successful_requests'], 0)
        
        # Update with successful request
        self.data_feed_manager._update_source_performance(source, True, 0.5)
        
        performance = self.data_feed_manager.source_performance[source]
        self.assertEqual(performance['total_requests'], 1)
        self.assertEqual(performance['successful_requests'], 1)
        self.assertEqual(performance['success_rate'], 1.0)
        self.assertEqual(performance['avg_response_time'], 0.5)
        self.assertEqual(performance['consecutive_failures'], 0)
        
        # Update with another successful request
        self.data_feed_manager._update_source_performance(source, True, 0.3)
        
        performance = self.data_feed_manager.source_performance[source]
        self.assertEqual(performance['total_requests'], 2)
        self.assertEqual(performance['successful_requests'], 2)
        self.assertEqual(performance['success_rate'], 1.0)
        # EMA: 0.1 * 0.3 + 0.9 * 0.5 = 0.48
        self.assertAlmostEqual(performance['avg_response_time'], 0.48, places=2)
        self.assertEqual(performance['consecutive_failures'], 0)
        
        # Update with failed request
        self.data_feed_manager._update_source_performance(source, False, 1.0)
        
        performance = self.data_feed_manager.source_performance[source]
        self.assertEqual(performance['total_requests'], 3)
        self.assertEqual(performance['successful_requests'], 2)
        self.assertAlmostEqual(performance['success_rate'], 2/3, places=2)
        # EMA: 0.1 * 1.0 + 0.9 * 0.48 = 0.532
        self.assertAlmostEqual(performance['avg_response_time'], 0.532, places=2)
        self.assertEqual(performance['consecutive_failures'], 1)
    
    def test_is_source_healthy(self):
        """Test source health checking"""
        source = DataSource.YAHOO_FINANCE
        
        # Mock health status
        healthy_status = {'status': 'healthy'}
        degraded_status = {'status': 'degraded'}
        unhealthy_status = {'status': 'unhealthy'}
        
        # Test with healthy status and good performance
        self.data_feed_manager.source_performance[source] = {
            'success_rate': 0.95,
            'avg_response_time': 0.5,
            'consecutive_failures': 0,
            'total_requests': 100,
            'successful_requests': 95
        }
        
        self.assertTrue(self.data_feed_manager._is_source_healthy(source, healthy_status))
        self.assertTrue(self.data_feed_manager._is_source_healthy(source, degraded_status))
        self.assertFalse(self.data_feed_manager._is_source_healthy(source, unhealthy_status))
        
        # Test with poor success rate
        self.data_feed_manager.source_performance[source] = {
            'success_rate': 0.80,  # Below threshold of 0.90
            'avg_response_time': 0.5,
            'consecutive_failures': 0,
            'total_requests': 100,
            'successful_requests': 80
        }
        
        self.assertFalse(self.data_feed_manager._is_source_healthy(source, healthy_status))
        
        # Test with slow response time
        self.data_feed_manager.source_performance[source] = {
            'success_rate': 0.95,
            'avg_response_time': 4.0,  # Above threshold of 3.0
            'consecutive_failures': 0,
            'total_requests': 100,
            'successful_requests': 95
        }
        
        self.assertFalse(self.data_feed_manager._is_source_healthy(source, healthy_status))
        
        # Test with too many consecutive failures
        self.data_feed_manager.source_performance[source] = {
            'success_rate': 0.95,
            'avg_response_time': 0.5,
            'consecutive_failures': 5,  # Above threshold of 3
            'total_requests': 100,
            'successful_requests': 95
        }
        
        self.assertFalse(self.data_feed_manager._is_source_healthy(source, healthy_status))
    
    def test_consider_preferred_source(self):
        """Test considering a source as preferred"""
        asset_class = AssetClass.STOCK
        source = DataSource.YAHOO_FINANCE
        
        # Initially no preferred source
        self.assertNotIn(asset_class, self.data_feed_manager.preferred_sources)
        
        # Update performance to excellent levels
        self.data_feed_manager.source_performance[source] = {
            'success_rate': 0.98,  # Above 0.95 threshold
            'avg_response_time': 0.5,  # Below 1.0 threshold
            'consecutive_failures': 0,
            'total_requests': 100,
            'successful_requests': 98
        }
        
        # Consider for preferred status
        self.data_feed_manager._consider_preferred_source(asset_class, source)
        
        # Should now be preferred
        self.assertIn(asset_class, self.data_feed_manager.preferred_sources)
        self.assertEqual(self.data_feed_manager.preferred_sources[asset_class], source)
    
    def test_set_switching_thresholds(self):
        """Test setting switching thresholds"""
        # Set custom thresholds
        self.data_feed_manager.set_switching_thresholds(
            success_rate=0.95,
            response_time=2.0,
            consecutive_failures=5
        )
        
        thresholds = self.data_feed_manager.switching_thresholds
        self.assertEqual(thresholds['success_rate'], 0.95)
        self.assertEqual(thresholds['response_time'], 2.0)
        self.assertEqual(thresholds['consecutive_failures'], 5)
    
    def test_enable_switching(self):
        """Test enabling/disabling switching"""
        # Initially enabled
        self.assertTrue(self.data_feed_manager.switching_enabled)
        
        # Disable switching
        self.data_feed_manager.enable_switching(False)
        self.assertFalse(self.data_feed_manager.switching_enabled)
        
        # Re-enable switching
        self.data_feed_manager.enable_switching(True)
        self.assertTrue(self.data_feed_manager.switching_enabled)
    
    def test_get_source_performance(self):
        """Test getting source performance metrics"""
        source = DataSource.YAHOO_FINANCE
        
        # Set some performance data
        self.data_feed_manager.source_performance[source] = {
            'success_rate': 0.90,
            'avg_response_time': 1.0,
            'consecutive_failures': 1,
            'total_requests': 50,
            'successful_requests': 45
        }
        
        # Get performance for specific source
        performance = self.data_feed_manager.get_source_performance(source)
        self.assertIn(source, performance)
        self.assertEqual(performance[source]['success_rate'], 0.90)
        self.assertEqual(performance[source]['consecutive_failures'], 1)
        
        # Get performance for all sources
        all_performance = self.data_feed_manager.get_source_performance()
        self.assertIn(source, all_performance)
        self.assertEqual(all_performance[source]['success_rate'], 0.90)
    
    def test_reset_source_performance(self):
        """Test resetting source performance metrics"""
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
        
        # Set performance data for multiple sources
        self.data_feed_manager.source_performance[DataSource.YAHOO_FINANCE] = {
            'success_rate': 0.80,
            'avg_response_time': 2.0,
            'consecutive_failures': 3,
            'total_requests': 100,
            'successful_requests': 80
        }
        self.data_feed_manager.source_performance[DataSource.ALPHA_VANTAGE] = {
            'success_rate': 0.70,
            'avg_response_time': 3.0,
            'consecutive_failures': 5,
            'total_requests': 50,
            'successful_requests': 35
        }
        
        # Reset all sources
        self.data_feed_manager.reset_source_performance()
        
        # All sources should be reset
        yahoo_performance = self.data_feed_manager.source_performance[DataSource.YAHOO_FINANCE]
        alpha_performance = self.data_feed_manager.source_performance[DataSource.ALPHA_VANTAGE]
        self.assertEqual(yahoo_performance['success_rate'], 1.0)
        self.assertEqual(alpha_performance['success_rate'], 1.0)

    def test_get_data_with_preferred_source(self):
        """Test get_data with preferred source"""
        asset_class = AssetClass.STOCK
        preferred_source = DataSource.YAHOO_FINANCE
        
        # Set up preferred source
        self.data_feed_manager.preferred_sources[asset_class] = preferred_source
        
        # Mock health status to be healthy
        with patch.object(self.data_feed_manager.health_monitor, 'get_health_status', 
                         return_value={'status': 'healthy'}):
            # Mock _has_required_credentials to return True
            with patch.object(self.data_feed_manager, '_has_required_credentials', 
                             return_value=True):
                # Mock rate_limit_manager to allow requests
                with patch.object(self.data_feed_manager.rate_limit_manager, 'can_make_request', 
                                 return_value=True):
                    # Mock _fetch_from_source to return a successful response
                    with patch.object(self.data_feed_manager, '_fetch_from_source') as mock_fetch:
                        mock_response = DataResponse(
                            data=pd.DataFrame({'close': [100, 101, 102]}),
                            source=preferred_source,
                            ticker="AAPL",
                            asset_class=asset_class,
                            metadata={},
                            timestamp=1234567890.0,
                            success=True
                        )
                        mock_fetch.return_value = mock_response
                        
                        response = self.data_feed_manager.get_data("AAPL", asset_class=asset_class)
                        
                        # Should use preferred source
                        self.assertEqual(response.source, preferred_source)
                        self.assertTrue(response.success)
                        mock_fetch.assert_called_once_with(preferred_source, 
                                                         DataRequest(ticker="AAPL", asset_class=asset_class))

    def test_get_data_preferred_source_failure(self):
        """Test get_data when preferred source fails"""
        asset_class = AssetClass.STOCK
        preferred_source = DataSource.YAHOO_FINANCE
        fallback_source = DataSource.ALPHA_VANTAGE
        
        # Set up preferred source
        self.data_feed_manager.preferred_sources[asset_class] = preferred_source
        
        # Mock health status to be healthy
        with patch.object(self.data_feed_manager.health_monitor, 'get_health_status', 
                         return_value={'status': 'healthy'}):
            # Mock _has_required_credentials to return True
            with patch.object(self.data_feed_manager, '_has_required_credentials', 
                             return_value=True):
                # Mock rate_limit_manager to allow requests
                with patch.object(self.data_feed_manager.rate_limit_manager, 'can_make_request', 
                                 return_value=True):
                    # Mock _fetch_from_source to simulate preferred source failure and fallback success
                    with patch.object(self.data_feed_manager, '_fetch_from_source') as mock_fetch:
                        def mock_fetch_side_effect(source, request):
                            if source == preferred_source:
                                return DataResponse(
                                    data=pd.DataFrame(),
                                    source=preferred_source,
                                    ticker="AAPL",
                                    asset_class=asset_class,
                                    metadata={},
                                    timestamp=1234567890.0,
                                    success=False,
                                    error_message="API error"
                                )
                            elif source == fallback_source:
                                return DataResponse(
                                    data=pd.DataFrame({'close': [100, 101, 102]}),
                                    source=fallback_source,
                                    ticker="AAPL",
                                    asset_class=asset_class,
                                    metadata={},
                                    timestamp=1234567890.0,
                                    success=True
                                )
                            else:
                                # For other sources in the priority list
                                return DataResponse(
                                    data=pd.DataFrame(),
                                    source=source,
                                    ticker="AAPL",
                                    asset_class=asset_class,
                                    metadata={},
                                    timestamp=1234567890.0,
                                    success=False,
                                    error_message="Not implemented"
                                )
                        
                        mock_fetch.side_effect = mock_fetch_side_effect
                        
                        # Set up source priority to include fallback source
                        self.data_feed_manager.source_priority_by_asset[asset_class] = [
                            preferred_source, fallback_source
                        ]
                        
                        response = self.data_feed_manager.get_data("AAPL", asset_class=asset_class)
                        
                        # Should use fallback source after preferred source fails
                        self.assertEqual(response.source, fallback_source)
                        self.assertTrue(response.success)
                        
                        # The fallback source performed well, so it should now be the preferred source
                        self.assertIn(asset_class, self.data_feed_manager.preferred_sources)
                        self.assertEqual(self.data_feed_manager.preferred_sources[asset_class], fallback_source)

def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestDataFeedSwitching))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)