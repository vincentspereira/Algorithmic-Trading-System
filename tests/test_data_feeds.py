"""
Test script for data feeds functionality

This script validates the data feed implementation and security scan setup.
"""

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

from nautilus_trader_engine.data_feeds import (
    DataFeedManager, 
    AssetClass, 
    DataSource, 
    DataRequest, 
    DataResponse,
    get_data,
    RateLimitManager
)


class TestDataFeeds(unittest.TestCase):
    """Test cases for data feed functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = DataFeedManager()
        self.test_ticker = "AAPL"
    
    def test_data_request_creation(self):
        """Test DataRequest object creation"""
        request = DataRequest(
            ticker=self.test_ticker,
            asset_class=AssetClass.STOCK,
            interval="1d",
            period="1y"
        )
        
        self.assertEqual(request.ticker, self.test_ticker)
        self.assertEqual(request.asset_class, AssetClass.STOCK)
        self.assertEqual(request.interval, "1d")
        self.assertEqual(request.period, "1y")
    
    def test_asset_class_enum(self):
        """Test AssetClass enum values"""
        self.assertEqual(AssetClass.STOCK.value, "stock")
        self.assertEqual(AssetClass.FUTURES.value, "futures")
        self.assertEqual(AssetClass.OPTIONS.value, "options")
        self.assertEqual(AssetClass.FOREX.value, "forex")
        self.assertEqual(AssetClass.COMMODITIES.value, "commodities")
        self.assertEqual(AssetClass.CRYPTO.value, "crypto")
    
    def test_data_source_enum(self):
        """Test DataSource enum values"""
        self.assertEqual(DataSource.YAHOO_FINANCE.value, "yahoo_finance")
        self.assertEqual(DataSource.ALPHA_VANTAGE.value, "alpha_vantage")
        self.assertEqual(DataSource.FINNHUB.value, "finnhub")
    
    def test_supported_assets(self):
        """Test supported assets for different sources"""
        yahoo_assets = self.manager.get_supported_assets(DataSource.YAHOO_FINANCE)
        self.assertIn(AssetClass.STOCK, yahoo_assets)
        self.assertIn(AssetClass.CRYPTO, yahoo_assets)
        
        alpha_vantage_assets = self.manager.get_supported_assets(DataSource.ALPHA_VANTAGE)
        self.assertIn(AssetClass.STOCK, alpha_vantage_assets)
        self.assertIn(AssetClass.FOREX, alpha_vantage_assets)
    
    def test_rate_limit_manager(self):
        """Test rate limit management"""
        from data_feeds import RateLimitManager
        
        rate_manager = RateLimitManager()
        
        # Should be able to make first request
        self.assertTrue(rate_manager.can_make_request(DataSource.YAHOO_FINANCE))
        
        # Record request
        rate_manager.record_request(DataSource.YAHOO_FINANCE)
        
        # Should not be able to make immediate second request (rate limited)
        self.assertFalse(rate_manager.can_make_request(DataSource.YAHOO_FINANCE))
    
    @patch('yfinance.Ticker')
    def test_yahoo_finance_fetch(self, mock_ticker):
        """Test Yahoo Finance data fetching with mocked response"""
        # Mock the yfinance response
        mock_data = pd.DataFrame({
            'Open': [150.0, 151.0, 152.0],
            'High': [155.0, 156.0, 157.0],
            'Low': [149.0, 150.0, 151.0],
            'Close': [154.0, 155.0, 156.0],
            'Volume': [1000000, 1100000, 1200000]
        })
        
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = mock_data
        mock_ticker_instance.info = {'symbol': 'AAPL', 'shortName': 'Apple Inc.'}
        mock_ticker.return_value = mock_ticker_instance
        
        # Test the fetch
        request = DataRequest(
            ticker=self.test_ticker,
            asset_class=AssetClass.STOCK
        )
        
        response = self.manager._fetch_yahoo_finance(request)
        
        self.assertTrue(response.success)
        self.assertEqual(response.source, DataSource.YAHOO_FINANCE)
        self.assertEqual(response.ticker, self.test_ticker)
        self.assertFalse(response.data.empty)
        self.assertEqual(len(response.data), 3)
    
    def test_convenience_function(self):
        """Test the convenience get_data function"""
        with patch.object(DataFeedManager, 'get_data') as mock_get_data:
            mock_response = DataResponse(
                data=pd.DataFrame({'close': [100, 101, 102]}),
                source=DataSource.YAHOO_FINANCE,
                ticker="AAPL",
                asset_class=AssetClass.STOCK,
                metadata={},
                timestamp=1234567890,
                success=True
            )
            mock_get_data.return_value = mock_response
            
            response = get_data("AAPL", asset_class="stock")
            
            self.assertTrue(response.success)
            self.assertEqual(response.ticker, "AAPL")
    
    def test_error_handling(self):
        """Test error handling for invalid requests"""
        # Test with invalid asset class
        with self.assertRaises(ValueError):
            AssetClass("invalid_asset")
        
        # Test with invalid data source
        with self.assertRaises(ValueError):
            DataSource("invalid_source")
    
    def test_fallback_logic(self):
        """Test fallback logic when primary source fails"""
        with patch.object(self.manager, '_fetch_yahoo_finance') as mock_yahoo, \
             patch.object(self.manager, '_fetch_alpha_vantage') as mock_alpha:
            
            # Make Yahoo Finance fail
            mock_yahoo.side_effect = Exception("Yahoo Finance unavailable")
            
            # Make Alpha Vantage succeed
            mock_alpha.return_value = DataResponse(
                data=pd.DataFrame({'close': [100, 101, 102]}),
                source=DataSource.ALPHA_VANTAGE,
                ticker="AAPL",
                asset_class=AssetClass.STOCK,
                metadata={},
                timestamp=1234567890,
                success=True
            )
            
            response = self.manager.get_data("AAPL", asset_class=AssetClass.STOCK)
            
            # Should have fallen back to Alpha Vantage
            self.assertTrue(response.success)
            self.assertEqual(response.source, DataSource.ALPHA_VANTAGE)


def test_security_setup():
    """Test security setup files exist and are properly configured"""
    
    # Check if requirements.txt exists and contains security tools
    requirements_path = os.path.join(os.path.dirname(__file__), '..', 'nautilus_trader_engine', 'requirements.txt')
    assert os.path.exists(requirements_path), "requirements.txt not found"
    
    with open(requirements_path, 'r') as f:
        requirements_content = f.read()
        assert 'bandit' in requirements_content, "bandit not found in requirements.txt"
        assert 'pre-commit' in requirements_content, "pre-commit not found in requirements.txt"
        assert 'yfinance' in requirements_content, "yfinance not found in requirements.txt"
        assert 'alpha_vantage' in requirements_content, "alpha_vantage not found in requirements.txt"
    
    # Check if .pre-commit-config.yaml exists
    precommit_path = os.path.join(os.path.dirname(__file__), '..', '.pre-commit-config.yaml')
    assert os.path.exists(precommit_path), ".pre-commit-config.yaml not found"
    
    with open(precommit_path, 'r') as f:
        precommit_content = f.read()
        assert 'bandit' in precommit_content, "bandit not configured in pre-commit"
        assert 'PyCQA/bandit' in precommit_content, "bandit repo not found in pre-commit config"
    
    # Check if security documentation exists
    security_doc_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'SECURITY_SETUP.md')
    assert os.path.exists(security_doc_path), "SECURITY_SETUP.md not found"
    
    print("✓ All security setup files exist and are properly configured")


def test_data_feeds_module():
    """Test data feeds module can be imported and basic functionality works"""
    
    # Test module import
    try:
        from data_feeds import DataFeedManager, AssetClass, DataSource
        print("✓ Data feeds module imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import data feeds module: {e}")
        return False
    
    # Test basic instantiation
    try:
        manager = DataFeedManager()
        print("✓ DataFeedManager instantiated successfully")
    except Exception as e:
        print(f"✗ Failed to instantiate DataFeedManager: {e}")
        return False
    
    # Test enum values
    try:
        assert AssetClass.STOCK.value == "stock"
        assert DataSource.YAHOO_FINANCE.value == "yahoo_finance"
        print("✓ Enum values are correct")
    except AssertionError as e:
        print(f"✗ Enum values are incorrect: {e}")
        return False
    
    return True


if __name__ == "__main__":
    print("Running Phase 1 Task 3 & 4 Validation Tests")
    print("=" * 50)
    
    # Test security setup
    print("\n1. Testing Security Setup...")
    try:
        test_security_setup()
    except Exception as e:
        print(f"✗ Security setup test failed: {e}")
    
    # Test data feeds module
    print("\n2. Testing Data Feeds Module...")
    test_data_feeds_module()
    
    # Run unit tests
    print("\n3. Running Unit Tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    print("\n" + "=" * 50)
    print("Validation tests completed!")