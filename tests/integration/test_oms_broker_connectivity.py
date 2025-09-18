"""Integration tests for Order Management System with Broker Connectivity.

This module tests the integration between the OMS and broker connections,
including Interactive Brokers connectivity, order routing, execution,
and error handling scenarios.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, List, Any, Optional

import pandas as pd
import numpy as np

# Trading system imports
from shared.models.orders import (
    Order, OrderType, OrderStatus, Side, TimeInForce,
    OrderExecution, OrderReject
)
from shared.models.positions import Position
from shared.models.accounts import Account, AccountStatus
from shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


@pytest.mark.integration
@pytest.mark.trading
@pytest.mark.broker
@pytest.mark.order_management
class TestOMSBrokerConnectivity:
    """Integration tests for OMS and broker connectivity."""

    @pytest.fixture
    async def oms_service(self):
        """Mock Order Management System service."""
        oms = Mock()
        oms.submit_order = AsyncMock()
        oms.cancel_order = AsyncMock()
        oms.modify_order = AsyncMock()
        oms.get_order_status = AsyncMock()
        oms.get_open_orders = AsyncMock()
        oms.get_order_history = AsyncMock()
        return oms

    @pytest.fixture
    async def broker_connector(self):
        """Mock Interactive Brokers connector."""
        connector = Mock()
        connector.connect = AsyncMock()
        connector.disconnect = AsyncMock()
        connector.is_connected = Mock(return_value=True)
        connector.place_order = AsyncMock()
        connector.cancel_order = AsyncMock()
        connector.modify_order = AsyncMock()
        connector.get_account_info = AsyncMock()
        connector.get_positions = AsyncMock()
        connector.subscribe_to_executions = AsyncMock()
        return connector

    @pytest.fixture
    async def paper_trading_connector(self):
        """Mock paper trading connector."""
        connector = Mock()
        connector.connect = AsyncMock()
        connector.disconnect = AsyncMock()
        connector.is_connected = Mock(return_value=True)
        connector.is_paper_trading = Mock(return_value=True)
        connector.place_order = AsyncMock()
        connector.cancel_order = AsyncMock()
        connector.get_account_info = AsyncMock()
        return connector

    @pytest.fixture
    def sample_market_order(self):
        """Sample market order for testing."""
        return Order(
            id="order_001",
            client_order_id="client_001",
            symbol="AAPL",
            side=Side.BUY,
            order_type=OrderType.MARKET,
            quantity=100,
            status=OrderStatus.PENDING_NEW,
            time_in_force=TimeInForce.DAY,
            timestamp=datetime.now(),
            account_id="DU123456"
        )

    @pytest.fixture
    def sample_limit_order(self):
        """Sample limit order for testing."""
        return Order(
            id="order_002",
            client_order_id="client_002",
            symbol="TSLA",
            side=Side.SELL,
            order_type=OrderType.LIMIT,
            quantity=50,
            limit_price=Decimal("250.00"),
            status=OrderStatus.PENDING_NEW,
            time_in_force=TimeInForce.GTC,
            timestamp=datetime.now(),
            account_id="DU123456"
        )

    @pytest.fixture
    def sample_account(self):
        """Sample account information."""
        return Account(
            account_id="DU123456",
            account_type="PAPER",
            status=AccountStatus.ACTIVE,
            buying_power=Decimal("100000.00"),
            total_cash=Decimal("50000.00"),
            net_liquidation=Decimal("150000.00"),
            currency="USD"
        )

    @pytest.mark.asyncio
    async def test_broker_connection_establishment(
        self,
        oms_service,
        broker_connector
    ):
        """Test establishing connection to Interactive Brokers."""
        # Arrange
        connection_params = {
            "host": "127.0.0.1",
            "port": 7497,  # Paper trading port
            "client_id": 1,
            "account": "DU123456"
        }
        
        broker_connector.connect.return_value = True
        broker_connector.is_connected.return_value = True
        
        # Act
        connection_result = await broker_connector.connect(**connection_params)
        is_connected = broker_connector.is_connected()
        
        # Assert
        broker_connector.connect.assert_called_once_with(**connection_params)
        assert connection_result is True
        assert is_connected is True

    @pytest.mark.asyncio
    async def test_market_order_submission(
        self,
        oms_service,
        broker_connector,
        sample_market_order
    ):
        """Test market order submission through OMS to broker."""
        # Arrange
        broker_order_id = "IB_12345"
        oms_service.submit_order.return_value = {
            "order_id": sample_market_order.id,
            "status": "SUBMITTED",
            "broker_order_id": broker_order_id
        }
        
        broker_connector.place_order.return_value = {
            "broker_order_id": broker_order_id,
            "status": "SUBMITTED",
            "timestamp": datetime.now()
        }
        
        # Act
        oms_result = await oms_service.submit_order(sample_market_order)
        broker_result = await broker_connector.place_order(
            sample_market_order.symbol,
            sample_market_order.side.value,
            sample_market_order.quantity,
            sample_market_order.order_type.value
        )
        
        # Assert
        oms_service.submit_order.assert_called_once_with(sample_market_order)
        broker_connector.place_order.assert_called_once()
        
        assert oms_result["status"] == "SUBMITTED"
        assert oms_result["broker_order_id"] == broker_order_id
        assert broker_result["broker_order_id"] == broker_order_id

    @pytest.mark.asyncio
    async def test_limit_order_submission(
        self,
        oms_service,
        broker_connector,
        sample_limit_order
    ):
        """Test limit order submission with price validation."""
        # Arrange
        broker_order_id = "IB_12346"
        oms_service.submit_order.return_value = {
            "order_id": sample_limit_order.id,
            "status": "SUBMITTED",
            "broker_order_id": broker_order_id
        }
        
        broker_connector.place_order.return_value = {
            "broker_order_id": broker_order_id,
            "status": "SUBMITTED",
            "limit_price": sample_limit_order.limit_price
        }
        
        # Act
        oms_result = await oms_service.submit_order(sample_limit_order)
        broker_result = await broker_connector.place_order(
            sample_limit_order.symbol,
            sample_limit_order.side.value,
            sample_limit_order.quantity,
            sample_limit_order.order_type.value,
            limit_price=sample_limit_order.limit_price
        )
        
        # Assert
        assert oms_result["status"] == "SUBMITTED"
        assert broker_result["limit_price"] == sample_limit_order.limit_price
        assert broker_result["broker_order_id"] == broker_order_id

    @pytest.mark.asyncio
    async def test_order_cancellation(
        self,
        oms_service,
        broker_connector,
        sample_limit_order
    ):
        """Test order cancellation through OMS to broker."""
        # Arrange
        broker_order_id = "IB_12346"
        sample_limit_order.broker_order_id = broker_order_id
        sample_limit_order.status = OrderStatus.NEW
        
        oms_service.cancel_order.return_value = {
            "order_id": sample_limit_order.id,
            "status": "CANCEL_SUBMITTED"
        }
        
        broker_connector.cancel_order.return_value = {
            "broker_order_id": broker_order_id,
            "status": "CANCELLED"
        }
        
        # Act
        oms_result = await oms_service.cancel_order(sample_limit_order.id)
        broker_result = await broker_connector.cancel_order(broker_order_id)
        
        # Assert
        oms_service.cancel_order.assert_called_once_with(sample_limit_order.id)
        broker_connector.cancel_order.assert_called_once_with(broker_order_id)
        
        assert oms_result["status"] == "CANCEL_SUBMITTED"
        assert broker_result["status"] == "CANCELLED"

    @pytest.mark.asyncio
    async def test_order_execution_flow(
        self,
        oms_service,
        broker_connector,
        sample_market_order
    ):
        """Test complete order execution flow from submission to fill."""
        # Arrange
        broker_order_id = "IB_12347"
        execution_id = "EXEC_001"
        fill_price = Decimal("150.25")
        fill_quantity = 100
        
        # Mock execution report
        execution = OrderExecution(
            execution_id=execution_id,
            order_id=sample_market_order.id,
            broker_order_id=broker_order_id,
            symbol=sample_market_order.symbol,
            side=sample_market_order.side,
            quantity=fill_quantity,
            price=fill_price,
            timestamp=datetime.now(),
            commission=Decimal("1.00")
        )
        
        # Setup mocks
        oms_service.submit_order.return_value = {
            "order_id": sample_market_order.id,
            "status": "SUBMITTED",
            "broker_order_id": broker_order_id
        }
        
        broker_connector.place_order.return_value = {
            "broker_order_id": broker_order_id,
            "status": "SUBMITTED"
        }
        
        oms_service.get_order_status.return_value = {
            "order_id": sample_market_order.id,
            "status": "FILLED",
            "filled_quantity": fill_quantity,
            "avg_fill_price": fill_price,
            "executions": [execution]
        }
        
        # Act
        # 1. Submit order
        submit_result = await oms_service.submit_order(sample_market_order)
        await broker_connector.place_order(
            sample_market_order.symbol,
            sample_market_order.side.value,
            sample_market_order.quantity,
            sample_market_order.order_type.value
        )
        
        # 2. Check final status
        final_status = await oms_service.get_order_status(sample_market_order.id)
        
        # Assert
        assert submit_result["status"] == "SUBMITTED"
        assert final_status["status"] == "FILLED"
        assert final_status["filled_quantity"] == fill_quantity
        assert final_status["avg_fill_price"] == fill_price
        assert len(final_status["executions"]) == 1

    @pytest.mark.asyncio
    async def test_paper_trading_mode(
        self,
        oms_service,
        paper_trading_connector,
        sample_market_order
    ):
        """Test paper trading mode functionality."""
        # Arrange
        paper_trading_connector.is_paper_trading.return_value = True
        paper_trading_connector.place_order.return_value = {
            "broker_order_id": "PAPER_12345",
            "status": "FILLED",  # Paper orders fill immediately
            "fill_price": Decimal("150.00"),
            "fill_quantity": 100,
            "is_simulated": True
        }
        
        # Act
        is_paper = paper_trading_connector.is_paper_trading()
        result = await paper_trading_connector.place_order(
            sample_market_order.symbol,
            sample_market_order.side.value,
            sample_market_order.quantity,
            sample_market_order.order_type.value
        )
        
        # Assert
        assert is_paper is True
        assert result["status"] == "FILLED"
        assert result["is_simulated"] is True
        assert result["fill_quantity"] == sample_market_order.quantity

    @pytest.mark.asyncio
    async def test_account_information_retrieval(
        self,
        broker_connector,
        sample_account
    ):
        """Test retrieving account information from broker."""
        # Arrange
        broker_connector.get_account_info.return_value = {
            "account_id": sample_account.account_id,
            "account_type": sample_account.account_type,
            "buying_power": sample_account.buying_power,
            "total_cash": sample_account.total_cash,
            "net_liquidation": sample_account.net_liquidation,
            "currency": sample_account.currency
        }
        
        # Act
        account_info = await broker_connector.get_account_info(sample_account.account_id)
        
        # Assert
        broker_connector.get_account_info.assert_called_once_with(sample_account.account_id)
        assert account_info["account_id"] == sample_account.account_id
        assert account_info["buying_power"] == sample_account.buying_power
        assert account_info["total_cash"] == sample_account.total_cash

    @pytest.mark.asyncio
    async def test_position_retrieval(
        self,
        broker_connector
    ):
        """Test retrieving positions from broker."""
        # Arrange
        positions = [
            Position(
                symbol="AAPL",
                quantity=100,
                average_price=Decimal("149.50"),
                market_value=Decimal("15000.00"),
                unrealized_pnl=Decimal("50.00")
            ),
            Position(
                symbol="TSLA",
                quantity=-50,  # Short position
                average_price=Decimal("250.00"),
                market_value=Decimal("-12500.00"),
                unrealized_pnl=Decimal("-500.00")
            )
        ]
        
        broker_connector.get_positions.return_value = positions
        
        # Act
        retrieved_positions = await broker_connector.get_positions("DU123456")
        
        # Assert
        broker_connector.get_positions.assert_called_once_with("DU123456")
        assert len(retrieved_positions) == 2
        assert retrieved_positions[0].symbol == "AAPL"
        assert retrieved_positions[0].quantity == 100
        assert retrieved_positions[1].symbol == "TSLA"
        assert retrieved_positions[1].quantity == -50  # Short position

    @pytest.mark.asyncio
    async def test_connection_failure_handling(
        self,
        oms_service,
        broker_connector,
        sample_market_order
    ):
        """Test handling of broker connection failures."""
        # Arrange
        broker_connector.is_connected.return_value = False
        broker_connector.connect.side_effect = Exception("Connection failed")
        
        # Act & Assert
        with pytest.raises(Exception, match="Connection failed"):
            await broker_connector.connect(host="127.0.0.1", port=7497, client_id=1)
        
        # Verify connection status
        assert broker_connector.is_connected() is False
        
        # Test order submission failure when disconnected
        broker_connector.place_order.side_effect = Exception("Not connected")
        
        with pytest.raises(Exception, match="Not connected"):
            await broker_connector.place_order(
                sample_market_order.symbol,
                sample_market_order.side.value,
                sample_market_order.quantity,
                sample_market_order.order_type.value
            )

    @pytest.mark.asyncio
    async def test_order_rejection_handling(
        self,
        oms_service,
        broker_connector,
        sample_market_order
    ):
        """Test handling of order rejections from broker."""
        # Arrange
        rejection_reason = "Insufficient buying power"
        order_reject = OrderReject(
            order_id=sample_market_order.id,
            reason=rejection_reason,
            timestamp=datetime.now()
        )
        
        oms_service.submit_order.return_value = {
            "order_id": sample_market_order.id,
            "status": "REJECTED",
            "rejection_reason": rejection_reason
        }
        
        broker_connector.place_order.side_effect = Exception(rejection_reason)
        
        # Act
        with pytest.raises(Exception, match=rejection_reason):
            await broker_connector.place_order(
                sample_market_order.symbol,
                sample_market_order.side.value,
                sample_market_order.quantity,
                sample_market_order.order_type.value
            )
        
        # Verify OMS handles rejection
        oms_result = await oms_service.submit_order(sample_market_order)
        assert oms_result["status"] == "REJECTED"
        assert oms_result["rejection_reason"] == rejection_reason

    @pytest.mark.asyncio
    async def test_order_modification(
        self,
        oms_service,
        broker_connector,
        sample_limit_order
    ):
        """Test order modification through OMS to broker."""
        # Arrange
        broker_order_id = "IB_12348"
        new_limit_price = Decimal("245.00")
        new_quantity = 75
        
        sample_limit_order.broker_order_id = broker_order_id
        sample_limit_order.status = OrderStatus.NEW
        
        oms_service.modify_order.return_value = {
            "order_id": sample_limit_order.id,
            "status": "MODIFIED",
            "new_limit_price": new_limit_price,
            "new_quantity": new_quantity
        }
        
        broker_connector.modify_order.return_value = {
            "broker_order_id": broker_order_id,
            "status": "MODIFIED",
            "limit_price": new_limit_price,
            "quantity": new_quantity
        }
        
        # Act
        oms_result = await oms_service.modify_order(
            sample_limit_order.id,
            limit_price=new_limit_price,
            quantity=new_quantity
        )
        
        broker_result = await broker_connector.modify_order(
            broker_order_id,
            limit_price=new_limit_price,
            quantity=new_quantity
        )
        
        # Assert
        oms_service.modify_order.assert_called_once()
        broker_connector.modify_order.assert_called_once()
        
        assert oms_result["status"] == "MODIFIED"
        assert oms_result["new_limit_price"] == new_limit_price
        assert broker_result["limit_price"] == new_limit_price
        assert broker_result["quantity"] == new_quantity

    @pytest.mark.asyncio
    async def test_execution_subscription(
        self,
        broker_connector
    ):
        """Test subscribing to execution reports from broker."""
        # Arrange
        execution_callback = Mock()
        broker_connector.subscribe_to_executions.return_value = True
        
        # Act
        subscription_result = await broker_connector.subscribe_to_executions(
            callback=execution_callback,
            account_id="DU123456"
        )
        
        # Assert
        broker_connector.subscribe_to_executions.assert_called_once_with(
            callback=execution_callback,
            account_id="DU123456"
        )
        assert subscription_result is True

    @pytest.mark.asyncio
    async def test_multiple_order_types(
        self,
        oms_service,
        broker_connector
    ):
        """Test submission of various order types."""
        # Test different order types
        order_types = [
            (OrderType.MARKET, None, None),
            (OrderType.LIMIT, Decimal("150.00"), None),
            (OrderType.STOP, None, Decimal("148.00")),
            (OrderType.STOP_LIMIT, Decimal("149.00"), Decimal("148.50"))
        ]
        
        for order_type, limit_price, stop_price in order_types:
            # Arrange
            order = Order(
                id=f"order_{order_type.value}",
                symbol="AAPL",
                side=Side.BUY,
                order_type=order_type,
                quantity=100,
                limit_price=limit_price,
                stop_price=stop_price,
                status=OrderStatus.PENDING_NEW,
                timestamp=datetime.now()
            )
            
            broker_connector.place_order.return_value = {
                "broker_order_id": f"IB_{order_type.value}",
                "status": "SUBMITTED",
                "order_type": order_type.value
            }
            
            # Act
            result = await broker_connector.place_order(
                order.symbol,
                order.side.value,
                order.quantity,
                order.order_type.value,
                limit_price=limit_price,
                stop_price=stop_price
            )
            
            # Assert
            assert result["status"] == "SUBMITTED"
            assert result["order_type"] == order_type.value

    @pytest.mark.asyncio
    async def test_order_history_retrieval(
        self,
        oms_service
    ):
        """Test retrieving order history from OMS."""
        # Arrange
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        order_history = [
            {
                "order_id": "order_001",
                "symbol": "AAPL",
                "side": "BUY",
                "quantity": 100,
                "status": "FILLED",
                "timestamp": datetime.now() - timedelta(days=1)
            },
            {
                "order_id": "order_002",
                "symbol": "TSLA",
                "side": "SELL",
                "quantity": 50,
                "status": "CANCELLED",
                "timestamp": datetime.now() - timedelta(days=2)
            }
        ]
        
        oms_service.get_order_history.return_value = order_history
        
        # Act
        history = await oms_service.get_order_history(
            account_id="DU123456",
            start_date=start_date,
            end_date=end_date
        )
        
        # Assert
        oms_service.get_order_history.assert_called_once_with(
            account_id="DU123456",
            start_date=start_date,
            end_date=end_date
        )
        
        assert len(history) == 2
        assert history[0]["order_id"] == "order_001"
        assert history[0]["status"] == "FILLED"
        assert history[1]["order_id"] == "order_002"
        assert history[1]["status"] == "CANCELLED"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])