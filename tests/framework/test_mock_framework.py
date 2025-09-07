"""
Test suite for MockFramework

This module contains comprehensive tests for the MockFramework,
validating all functionality including mock creation, behavior validation,
and data generation.
"""

import os
import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
from datetime import datetime, timedelta

# Add the framework directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mock_framework import (
    MockFactory,
    MockDataGenerator,
    MockType,
    MockBehavior,
    MockConfig,
    MockCall,
    MockValidationResult
)


class TestMockFactory:
    """Test suite for MockFactory class"""
    
    @pytest.fixture
    def mock_factory(self):
        """Create a MockFactory instance for testing"""
        return MockFactory()
    
    @pytest.fixture
    def success_config(self):
        """Create a success mock configuration"""
        return MockConfig(
            mock_type=MockType.API,
            behavior=MockBehavior.SUCCESS,
            success_rate=1.0
        )
    
    @pytest.fixture
    def failure_config(self):
        """Create a failure mock configuration"""
        return MockConfig(
            mock_type=MockType.API,
            behavior=MockBehavior.FAILURE,
            failure_exceptions=[ValueError("Test error")]
        )
    
    def test_init(self, mock_factory):
        """Test MockFactory initialization"""
        assert isinstance(mock_factory.created_mocks, dict)
        assert isinstance(mock_factory.mock_configs, dict)
        assert isinstance(mock_factory.call_history, dict)
        assert isinstance(mock_factory.active_patches, list)
        assert len(mock_factory.created_mocks) == 0
    
    def test_create_api_mock(self, mock_factory, success_config):
        """Test API mock creation"""
        endpoints = {
            'get_data': {'status': 'success', 'data': [1, 2, 3]},
            'post_data': {'status': 'created', 'id': 123}
        }
        
        api_mock = mock_factory.create_api_mock('test_api', success_config, endpoints)
        
        assert 'test_api' in mock_factory.created_mocks
        assert 'test_api' in mock_factory.mock_configs
        assert 'test_api' in mock_factory.call_history
        assert api_mock is not None
        assert hasattr(api_mock, 'get_data')
        assert hasattr(api_mock, 'post_data')
    
    def test_create_database_mock(self, mock_factory, success_config):
        """Test database mock creation"""
        tables = {
            'users': [
                {'id': 1, 'name': 'John', 'email': 'john@example.com'},
                {'id': 2, 'name': 'Jane', 'email': 'jane@example.com'}
            ],
            'orders': [
                {'id': 1, 'user_id': 1, 'amount': 100.0},
                {'id': 2, 'user_id': 2, 'amount': 200.0}
            ]
        }
        
        db_mock = mock_factory.create_database_mock('test_db', success_config, tables)
        
        assert 'test_db' in mock_factory.created_mocks
        assert db_mock is not None
        assert hasattr(db_mock, 'connect')
        assert hasattr(db_mock, 'connection')
        assert hasattr(db_mock, 'cursor')
    
    def test_create_market_data_mock(self, mock_factory, success_config):
        """Test market data mock creation"""
        symbols = ['AAPL', 'GOOGL', 'MSFT']
        
        market_mock = mock_factory.create_market_data_mock('test_market', success_config, symbols)
        
        assert 'test_market' in mock_factory.created_mocks
        assert market_mock is not None
        assert hasattr(market_mock, 'get_quote')
        assert hasattr(market_mock, 'get_historical_data')
        assert hasattr(market_mock, 'get_symbols')
        assert hasattr(market_mock, 'stream_data')
    
    def test_create_trading_service_mock(self, mock_factory, success_config):
        """Test trading service mock creation"""
        trading_mock = mock_factory.create_trading_service_mock('test_trading', success_config)
        
        assert 'test_trading' in mock_factory.created_mocks
        assert trading_mock is not None
        assert hasattr(trading_mock, 'place_order')
        assert hasattr(trading_mock, 'cancel_order')
        assert hasattr(trading_mock, 'get_order_status')
        assert hasattr(trading_mock, 'get_portfolio')
        assert hasattr(trading_mock, 'get_account_info')
    
    def test_create_external_service_mock(self, mock_factory, success_config):
        """Test external service mock creation"""
        endpoints = {
            'authenticate': {'token': 'abc123', 'expires_in': 3600},
            'get_user_info': {'id': 1, 'name': 'Test User'},
            'send_notification': {'status': 'sent', 'message_id': 'msg123'}
        }
        
        service_mock = mock_factory.create_external_service_mock('test_service', success_config, endpoints)
        
        assert 'test_service' in mock_factory.created_mocks
        assert service_mock is not None
        assert hasattr(service_mock, 'authenticate')
        assert hasattr(service_mock, 'get_user_info')
        assert hasattr(service_mock, 'send_notification')
    
    def test_mock_success_behavior(self, mock_factory, success_config):
        """Test mock with success behavior"""
        endpoints = {'test_endpoint': {'result': 'success'}}
        api_mock = mock_factory.create_api_mock('success_api', success_config, endpoints)
        
        # Call the mock method
        result = api_mock.test_endpoint()
        
        # Verify the call was recorded
        assert len(mock_factory.call_history['success_api']) == 1
        call = mock_factory.call_history['success_api'][0]
        assert call.method_name == 'success_api.test_endpoint'
        assert call.exception is None
    
    def test_mock_failure_behavior(self, mock_factory, failure_config):
        """Test mock with failure behavior"""
        endpoints = {'test_endpoint': {'result': 'success'}}
        api_mock = mock_factory.create_api_mock('failure_api', failure_config, endpoints)
        
        # Call the mock method and expect exception
        with pytest.raises(ValueError, match="Test error"):
            api_mock.test_endpoint()
        
        # Verify the call was recorded with exception
        assert len(mock_factory.call_history['failure_api']) == 1
        call = mock_factory.call_history['failure_api'][0]
        assert call.method_name == 'failure_api.test_endpoint'
        assert isinstance(call.exception, ValueError)
    
    def test_mock_intermittent_behavior(self, mock_factory):
        """Test mock with intermittent behavior"""
        intermittent_config = MockConfig(
            mock_type=MockType.API,
            behavior=MockBehavior.INTERMITTENT,
            success_rate=0.5,  # 50% success rate
            failure_exceptions=[RuntimeError("Intermittent failure")]
        )
        
        endpoints = {'test_endpoint': {'result': 'success'}}
        api_mock = mock_factory.create_api_mock('intermittent_api', intermittent_config, endpoints)
        
        # Call multiple times to test intermittent behavior
        success_count = 0
        failure_count = 0
        
        for _ in range(20):
            try:
                api_mock.test_endpoint()
                success_count += 1
            except RuntimeError:
                failure_count += 1
        
        # Should have both successes and failures
        assert success_count > 0
        assert failure_count > 0
        assert success_count + failure_count == 20
    
    def test_mock_with_delay(self, mock_factory):
        """Test mock with configured delay"""
        delay_config = MockConfig(
            mock_type=MockType.API,
            behavior=MockBehavior.SUCCESS,
            delay_range=(0.1, 0.2)  # 100-200ms delay
        )
        
        endpoints = {'test_endpoint': {'result': 'success'}}
        api_mock = mock_factory.create_api_mock('delay_api', delay_config, endpoints)
        
        start_time = time.time()
        api_mock.test_endpoint()
        end_time = time.time()
        
        duration = end_time - start_time
        assert duration >= 0.1  # Should have at least minimum delay
        
        # Check recorded duration
        call = mock_factory.call_history['delay_api'][0]
        assert call.duration >= 0.1
    
    def test_validate_mock_behavior_success(self, mock_factory, success_config):
        """Test successful mock behavior validation"""
        endpoints = {'method1': 'result1', 'method2': 'result2'}
        api_mock = mock_factory.create_api_mock('validation_api', success_config, endpoints)
        
        # Make some calls
        api_mock.method1()
        api_mock.method2()
        
        # Validate behavior
        result = mock_factory.validate_mock_behavior(
            'validation_api',
            expected_calls=2,
            expected_methods=['method1', 'method2']
        )
        
        assert result.success == True
        assert result.total_calls == 2
        assert result.call_matches == True
        assert result.behavior_matches == True
        assert len(result.validation_errors) == 0
    
    def test_validate_mock_behavior_failure(self, mock_factory, success_config):
        """Test failed mock behavior validation"""
        endpoints = {'method1': 'result1'}
        api_mock = mock_factory.create_api_mock('validation_api', success_config, endpoints)
        
        # Make only one call
        api_mock.method1()
        
        # Validate with wrong expectations
        result = mock_factory.validate_mock_behavior(
            'validation_api',
            expected_calls=3,
            expected_methods=['method1', 'method2', 'method3']
        )
        
        assert result.success == False
        assert result.total_calls == 1
        assert result.call_matches == False
        assert result.behavior_matches == False
        assert len(result.validation_errors) > 0
    
    def test_validate_nonexistent_mock(self, mock_factory):
        """Test validation of non-existent mock"""
        result = mock_factory.validate_mock_behavior('nonexistent_mock')
        
        assert result.success == False
        assert "Mock 'nonexistent_mock' not found" in result.validation_errors
    
    def test_get_mock_statistics(self, mock_factory, success_config):
        """Test getting mock statistics"""
        endpoints = {'test_method': 'result'}
        api_mock = mock_factory.create_api_mock('stats_api', success_config, endpoints)
        
        # Make multiple calls
        for _ in range(5):
            api_mock.test_method()
        
        stats = mock_factory.get_mock_statistics('stats_api')
        
        assert stats['mock_name'] == 'stats_api'
        assert stats['total_calls'] == 5
        assert 'stats_api.test_method' in stats['methods_called']
        assert stats['success_rate'] == 1.0
        assert stats['error_count'] == 0
        assert 'average_duration' in stats
        assert 'total_duration' in stats
    
    def test_get_statistics_nonexistent_mock(self, mock_factory):
        """Test getting statistics for non-existent mock"""
        stats = mock_factory.get_mock_statistics('nonexistent_mock')
        
        assert 'error' in stats
        assert "Mock 'nonexistent_mock' not found" in stats['error']
    
    def test_reset_mock(self, mock_factory, success_config):
        """Test resetting a mock"""
        endpoints = {'test_method': 'result'}
        api_mock = mock_factory.create_api_mock('reset_api', success_config, endpoints)
        
        # Make some calls
        api_mock.test_method()
        api_mock.test_method()
        
        assert len(mock_factory.call_history['reset_api']) == 2
        
        # Reset the mock
        success = mock_factory.reset_mock('reset_api')
        
        assert success == True
        assert len(mock_factory.call_history['reset_api']) == 0
    
    def test_reset_nonexistent_mock(self, mock_factory):
        """Test resetting non-existent mock"""
        success = mock_factory.reset_mock('nonexistent_mock')
        assert success == False
    
    def test_cleanup_mocks(self, mock_factory, success_config):
        """Test cleaning up all mocks"""
        # Create some mocks
        endpoints = {'method': 'result'}
        mock_factory.create_api_mock('api1', success_config, endpoints)
        mock_factory.create_api_mock('api2', success_config, endpoints)
        
        assert len(mock_factory.created_mocks) == 2
        assert len(mock_factory.mock_configs) == 2
        assert len(mock_factory.call_history) == 2
        
        # Cleanup
        mock_factory.cleanup_mocks()
        
        assert len(mock_factory.created_mocks) == 0
        assert len(mock_factory.mock_configs) == 0
        assert len(mock_factory.call_history) == 0
        assert len(mock_factory.active_patches) == 0


class TestMockDataGenerator:
    """Test suite for MockDataGenerator class"""
    
    @pytest.fixture
    def data_generator(self):
        """Create a MockDataGenerator instance for testing"""
        return MockDataGenerator(seed=42)  # Use seed for reproducible tests
    
    def test_init(self, data_generator):
        """Test MockDataGenerator initialization"""
        assert isinstance(data_generator.symbols, list)
        assert isinstance(data_generator.currencies, list)
        assert isinstance(data_generator.crypto_symbols, list)
        assert len(data_generator.symbols) > 0
        assert 'AAPL' in data_generator.symbols
        assert 'USD' in data_generator.currencies
        assert 'BTC' in data_generator.crypto_symbols
    
    def test_generate_market_data(self, data_generator):
        """Test market data generation"""
        symbol = 'AAPL'
        days = 10
        
        market_data = data_generator.generate_market_data(symbol, days)
        
        assert len(market_data) == days
        
        for data_point in market_data:
            assert data_point['symbol'] == symbol
            assert 'date' in data_point
            assert 'timestamp' in data_point
            assert 'open' in data_point
            assert 'high' in data_point
            assert 'low' in data_point
            assert 'close' in data_point
            assert 'volume' in data_point
            
            # Validate OHLC relationships
            assert data_point['high'] >= data_point['open']
            assert data_point['high'] >= data_point['close']
            assert data_point['low'] <= data_point['open']
            assert data_point['low'] <= data_point['close']
            assert data_point['volume'] > 0
    
    def test_generate_order_book(self, data_generator):
        """Test order book generation"""
        symbol = 'GOOGL'
        levels = 5
        
        order_book = data_generator.generate_order_book(symbol, levels)
        
        assert order_book['symbol'] == symbol
        assert 'timestamp' in order_book
        assert len(order_book['bids']) == levels
        assert len(order_book['asks']) == levels
        assert 'spread' in order_book
        assert 'mid_price' in order_book
        
        # Validate bid/ask structure
        for bid in order_book['bids']:
            assert 'price' in bid
            assert 'size' in bid
            assert 'orders' in bid
            assert bid['size'] > 0
            assert bid['orders'] > 0
        
        for ask in order_book['asks']:
            assert 'price' in ask
            assert 'size' in ask
            assert 'orders' in ask
            assert ask['size'] > 0
            assert ask['orders'] > 0
        
        # Validate price ordering
        for i in range(1, levels):
            assert order_book['bids'][i]['price'] < order_book['bids'][i-1]['price']
            assert order_book['asks'][i]['price'] > order_book['asks'][i-1]['price']
    
    def test_generate_trade_data(self, data_generator):
        """Test trade data generation"""
        symbol = 'MSFT'
        count = 20
        
        trades = data_generator.generate_trade_data(symbol, count)
        
        assert len(trades) == count
        
        for trade in trades:
            assert trade['symbol'] == symbol
            assert 'trade_id' in trade
            assert 'timestamp' in trade
            assert 'price' in trade
            assert 'size' in trade
            assert trade['side'] in ['BUY', 'SELL']
            assert trade['trade_type'] in ['MARKET', 'LIMIT', 'STOP']
            assert 'venue' in trade
            assert trade['size'] > 0
            assert trade['price'] > 0
    
    def test_generate_portfolio_data(self, data_generator):
        """Test portfolio data generation"""
        symbols = ['AAPL', 'GOOGL', 'MSFT']
        
        portfolio = data_generator.generate_portfolio_data(symbols)
        
        assert 'account_id' in portfolio
        assert 'timestamp' in portfolio
        assert 'cash_balance' in portfolio
        assert 'total_market_value' in portfolio
        assert 'total_value' in portfolio
        assert 'positions' in portfolio
        
        assert len(portfolio['positions']) == len(symbols)
        
        # Validate position structure
        total_weight = 0
        for position in portfolio['positions']:
            assert position['symbol'] in symbols
            assert 'quantity' in position
            assert 'average_price' in position
            assert 'current_price' in position
            assert 'market_value' in position
            assert 'unrealized_pnl' in position
            assert 'weight' in position
            
            assert position['quantity'] > 0
            assert position['average_price'] > 0
            assert position['current_price'] > 0
            assert position['market_value'] > 0
            
            total_weight += position['weight']
        
        # Weights should sum to approximately 100%
        assert abs(total_weight - 100.0) < 1.0
    
    def test_generate_user_data(self, data_generator):
        """Test user data generation"""
        count = 5
        
        users = data_generator.generate_user_data(count)
        
        assert len(users) == count
        
        for user in users:
            assert 'user_id' in user
            assert 'username' in user
            assert 'email' in user
            assert 'first_name' in user
            assert 'last_name' in user
            assert 'created_at' in user
            assert 'last_login' in user
            assert 'account_type' in user
            assert 'status' in user
            assert 'preferences' in user
            
            # Validate email format
            assert '@' in user['email']
            assert '.' in user['email']
            
            # Validate account type
            assert user['account_type'] in ['BASIC', 'PREMIUM', 'PROFESSIONAL']
            
            # Validate status
            assert user['status'] in ['ACTIVE', 'INACTIVE', 'SUSPENDED']
    
    def test_generate_api_response_market_quote(self, data_generator):
        """Test API response generation for market quote"""
        response = data_generator.generate_api_response('market_quote', symbol='AAPL')
        
        assert response['status'] == 'success'
        assert 'timestamp' in response
        assert 'request_id' in response
        assert 'data' in response
        
        data = response['data']
        assert data['symbol'] == 'AAPL'
        assert 'price' in data
        assert 'bid' in data
        assert 'ask' in data
        assert 'volume' in data
        assert 'change' in data
        assert 'change_percent' in data
    
    def test_generate_api_response_order_status(self, data_generator):
        """Test API response generation for order status"""
        order_id = 'test_order_123'
        response = data_generator.generate_api_response(
            'order_status', 
            order_id=order_id,
            symbol='GOOGL',
            quantity=100
        )
        
        assert response['status'] == 'success'
        assert 'data' in response
        
        data = response['data']
        assert data['order_id'] == order_id
        assert data['symbol'] == 'GOOGL'
        assert data['quantity'] == 100
        assert data['status'] in ['PENDING', 'FILLED', 'CANCELLED']
        assert 'filled_quantity' in data
        assert 'average_price' in data
    
    def test_generate_api_response_error(self, data_generator):
        """Test API response generation for error"""
        response = data_generator.generate_api_response(
            'error',
            error_code='INVALID_SYMBOL',
            error_message='Symbol not found',
            error_details={'symbol': 'INVALID'}
        )
        
        assert response['status'] == 'error'
        assert 'error' in response
        
        error = response['error']
        assert error['code'] == 'INVALID_SYMBOL'
        assert error['message'] == 'Symbol not found'
        assert error['details']['symbol'] == 'INVALID'
    
    def test_reproducible_data_generation(self):
        """Test that data generation is reproducible with same seed"""
        generator1 = MockDataGenerator(seed=123)
        generator2 = MockDataGenerator(seed=123)
        
        data1 = generator1.generate_market_data('AAPL', 5)
        data2 = generator2.generate_market_data('AAPL', 5)
        
        # Should generate identical data with same seed
        assert len(data1) == len(data2)
        for i in range(len(data1)):
            assert data1[i]['close'] == data2[i]['close']
            assert data1[i]['volume'] == data2[i]['volume']


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])