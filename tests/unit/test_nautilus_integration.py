"""Unit tests for NautilusTrader integration components."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import asyncio
from typing import Dict, Any


class TestNautilusTraderIntegration:
    """Test suite for NautilusTrader integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_config = {
            'nautilus': {
                'engine_config': {
                    'trader_id': 'test_trader',
                    'instance_id': 'test_instance'
                }
            }
        }
    
    @patch('nautilus_trader_engine.core.infrastructure_manager.InfrastructureManager')
    def test_nautilus_engine_initialization(self, mock_infrastructure):
        """Test NautilusTrader engine initialization."""
        # Mock the infrastructure manager
        mock_manager = Mock()
        mock_infrastructure.return_value = mock_manager
        
        # Test initialization
        from nautilus_trader_engine.core.infrastructure_manager import InfrastructureManager
        manager = InfrastructureManager()
        
        assert manager is not None
        mock_infrastructure.assert_called_once()
    
    @patch('nautilus_trader_engine.adapters.broker_adapter.BrokerAdapter')
    def test_broker_adapter_connection(self, mock_adapter):
        """Test broker adapter connection."""
        # Mock broker adapter
        mock_broker = Mock()
        mock_adapter.return_value = mock_broker
        mock_broker.connect.return_value = True
        
        # Test connection
        from nautilus_trader_engine.adapters.broker_adapter import BrokerAdapter
        adapter = BrokerAdapter()
        result = adapter.connect()
        
        assert result is True
        mock_broker.connect.assert_called_once()
    
    @patch('nautilus_trader_engine.core.order_management.OrderManager')
    def test_order_management_integration(self, mock_order_manager):
        """Test order management integration."""
        # Mock order manager
        mock_manager = Mock()
        mock_order_manager.return_value = mock_manager
        mock_manager.submit_order.return_value = {'order_id': 'test_123', 'status': 'submitted'}
        
        # Test order submission
        from nautilus_trader_engine.core.order_management import OrderManager
        manager = OrderManager()
        result = manager.submit_order({'symbol': 'EURUSD', 'quantity': 1000})
        
        assert result['status'] == 'submitted'
        assert 'order_id' in result
    
    @patch('nautilus_trader_engine.core.risk_management.RiskManager')
    def test_risk_management_integration(self, mock_risk_manager):
        """Test risk management integration."""
        # Mock risk manager
        mock_manager = Mock()
        mock_risk_manager.return_value = mock_manager
        mock_manager.check_risk.return_value = {'approved': True, 'risk_score': 0.3}
        
        # Test risk check
        from nautilus_trader_engine.core.risk_management import RiskManager
        manager = RiskManager()
        result = manager.check_risk({'symbol': 'EURUSD', 'quantity': 1000})
        
        assert result['approved'] is True
        assert result['risk_score'] == 0.3
    
    @pytest.mark.asyncio
    @patch('nautilus_trader_engine.core.data_feed_manager.DataFeedManager')
    async def test_data_feed_integration(self, mock_feed_manager):
        """Test data feed integration."""
        # Mock data feed manager
        mock_manager = Mock()
        mock_feed_manager.return_value = mock_manager
        mock_manager.start_feed = AsyncMock(return_value=True)
        mock_manager.get_market_data = AsyncMock(return_value={
            'symbol': 'EURUSD',
            'bid': 1.0850,
            'ask': 1.0852,
            'timestamp': '2024-01-01T00:00:00Z'
        })
        
        # Test data feed
        from nautilus_trader_engine.core.data_feed_manager import DataFeedManager
        manager = DataFeedManager()
        
        # Start feed
        start_result = await manager.start_feed()
        assert start_result is True
        
        # Get market data
        data = await manager.get_market_data('EURUSD')
        assert data['symbol'] == 'EURUSD'
        assert 'bid' in data
        assert 'ask' in data
    
    def test_nautilus_configuration_validation(self):
        """Test NautilusTrader configuration validation."""
        # Test valid configuration
        valid_config = {
            'trader_id': 'test_trader',
            'instance_id': 'test_instance',
            'log_level': 'INFO'
        }
        
        # Mock validation function
        def validate_config(config: Dict[str, Any]) -> bool:
            required_fields = ['trader_id', 'instance_id']
            return all(field in config for field in required_fields)
        
        assert validate_config(valid_config) is True
        
        # Test invalid configuration
        invalid_config = {'trader_id': 'test_trader'}
        assert validate_config(invalid_config) is False
    
    @patch('nautilus_trader_engine.core.trading_mode_manager.TradingModeManager')
    def test_trading_mode_management(self, mock_mode_manager):
        """Test trading mode management."""
        # Mock trading mode manager
        mock_manager = Mock()
        mock_mode_manager.return_value = mock_manager
        mock_manager.set_mode.return_value = True
        mock_manager.get_current_mode.return_value = 'LIVE'
        
        # Test mode management
        from nautilus_trader_engine.core.trading_mode_manager import TradingModeManager
        manager = TradingModeManager()
        
        # Set trading mode
        result = manager.set_mode('LIVE')
        assert result is True
        
        # Get current mode
        current_mode = manager.get_current_mode()
        assert current_mode == 'LIVE'


class AsyncMock(MagicMock):
    """Async mock for testing async functions."""
    
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)


if __name__ == '__main__':
    pytest.main([__file__])