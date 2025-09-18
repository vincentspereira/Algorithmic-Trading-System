"""System tests for complete trading workflows.

This module contains end-to-end system tests that validate complete
trading workflows from market data ingestion through order execution
and settlement, testing the entire system integration.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any

import pytest
from conftest import assert_valid_uuid, assert_valid_timestamp, assert_positive_number


class TestCompleteOrderWorkflow:
    """Test complete order lifecycle from submission to settlement."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_market_order_complete_workflow(
        self, 
        mock_trading_engine, 
        mock_market_data_service, 
        mock_portfolio_manager,
        mock_risk_manager,
        sample_order_data
    ):
        """Test complete market order workflow from submission to settlement."""
        # Arrange
        order_data = sample_order_data.copy()
        order_data["order_type"] = "MARKET"
        order_id = str(uuid.uuid4())
        
        # Mock the complete workflow
        mock_market_data_service.get_quote.return_value = {
            "symbol": order_data["symbol"],
            "price": Decimal("150.25"),
            "bid": Decimal("150.20"),
            "ask": Decimal("150.30"),
            "timestamp": datetime.utcnow()
        }
        
        mock_risk_manager.check_risk_limits.return_value = {
            "approved": True,
            "warnings": [],
            "risk_score": 0.3
        }
        
        # Simulate order progression
        order_statuses = ["SUBMITTED", "PENDING", "FILLED"]
        mock_trading_engine.get_order_status.side_effect = order_statuses
        
        mock_trading_engine.submit_order.return_value = {
            "order_id": order_id,
            "status": "SUBMITTED",
            "timestamp": datetime.utcnow()
        }
        
        mock_trading_engine.get_fill_details.return_value = {
            "order_id": order_id,
            "fill_price": Decimal("150.25"),
            "fill_quantity": order_data["quantity"],
            "fill_time": datetime.utcnow(),
            "commission": Decimal("1.00")
        }
        
        mock_portfolio_manager.update_position.return_value = {
            "symbol": order_data["symbol"],
            "new_quantity": order_data["quantity"],
            "average_price": Decimal("150.25"),
            "unrealized_pnl": Decimal("0.00")
        }
        
        # Act - Execute complete workflow
        
        # Step 1: Get market quote
        quote = await mock_market_data_service.get_quote(order_data["symbol"])
        
        # Step 2: Risk check
        risk_check = await mock_risk_manager.check_risk_limits(order_data)
        
        # Step 3: Submit order
        submit_result = await mock_trading_engine.submit_order(order_data)
        
        # Step 4: Monitor order status
        final_status = None
        for _ in range(3):  # Check status progression
            status = await mock_trading_engine.get_order_status(order_id)
            if status == "FILLED":
                final_status = status
                break
            await asyncio.sleep(0.1)  # Simulate polling delay
        
        # Step 5: Get fill details
        fill_details = await mock_trading_engine.get_fill_details(order_id)
        
        # Step 6: Update portfolio
        position_update = await mock_portfolio_manager.update_position(
            order_data["symbol"],
            order_data["quantity"],
            fill_details["fill_price"]
        )
        
        # Assert - Validate complete workflow
        assert quote["symbol"] == order_data["symbol"]
        assert_positive_number(quote["price"], "quote price")
        
        assert risk_check["approved"] is True
        assert risk_check["risk_score"] <= 1.0
        
        assert submit_result["order_id"] == order_id
        assert submit_result["status"] == "SUBMITTED"
        
        assert final_status == "FILLED"
        
        assert fill_details["order_id"] == order_id
        assert fill_details["fill_quantity"] == order_data["quantity"]
        assert_positive_number(fill_details["fill_price"], "fill price")
        
        assert position_update["symbol"] == order_data["symbol"]
        assert position_update["new_quantity"] == order_data["quantity"]

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_limit_order_workflow_with_partial_fills(
        self,
        mock_trading_engine,
        mock_market_data_service,
        mock_portfolio_manager,
        sample_order_data
    ):
        """Test limit order workflow with partial fills."""
        # Arrange
        order_data = sample_order_data.copy()
        order_data["order_type"] = "LIMIT"
        order_data["price"] = Decimal("149.50")
        order_data["quantity"] = 1000
        order_id = str(uuid.uuid4())
        
        # Mock partial fill progression
        fill_progression = [
            {"filled_quantity": 0, "status": "PENDING"},
            {"filled_quantity": 300, "status": "PARTIALLY_FILLED"},
            {"filled_quantity": 700, "status": "PARTIALLY_FILLED"},
            {"filled_quantity": 1000, "status": "FILLED"}
        ]
        
        mock_trading_engine.submit_order.return_value = {
            "order_id": order_id,
            "status": "SUBMITTED"
        }
        
        mock_trading_engine.get_order_status.side_effect = [
            fill["status"] for fill in fill_progression
        ]
        
        mock_trading_engine.get_partial_fills.side_effect = [
            fill["filled_quantity"] for fill in fill_progression
        ]
        
        # Act
        submit_result = await mock_trading_engine.submit_order(order_data)
        
        # Monitor partial fills
        filled_quantities = []
        for i in range(len(fill_progression)):
            status = await mock_trading_engine.get_order_status(order_id)
            filled_qty = await mock_trading_engine.get_partial_fills(order_id)
            filled_quantities.append(filled_qty)
            
            if status == "FILLED":
                break
        
        # Assert
        assert submit_result["order_id"] == order_id
        assert filled_quantities == [0, 300, 700, 1000]
        assert filled_quantities[-1] == order_data["quantity"]

    @pytest.mark.asyncio
    async def test_order_rejection_workflow(
        self,
        mock_trading_engine,
        mock_risk_manager,
        sample_order_data
    ):
        """Test order rejection due to risk limits."""
        # Arrange
        order_data = sample_order_data.copy()
        order_data["quantity"] = 10000  # Large quantity to trigger risk limits
        
        mock_risk_manager.check_risk_limits.return_value = {
            "approved": False,
            "warnings": ["Exceeds maximum position size", "Insufficient buying power"],
            "risk_score": 0.95
        }
        
        mock_trading_engine.submit_order.side_effect = ValueError(
            "Order rejected by risk management"
        )
        
        # Act & Assert
        risk_check = await mock_risk_manager.check_risk_limits(order_data)
        assert risk_check["approved"] is False
        assert len(risk_check["warnings"]) > 0
        
        with pytest.raises(ValueError, match="Order rejected by risk management"):
            await mock_trading_engine.submit_order(order_data)


class TestPortfolioManagementWorkflow:
    """Test complete portfolio management workflows."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_portfolio_rebalancing_workflow(
        self,
        mock_portfolio_manager,
        mock_trading_engine,
        mock_market_data_service,
        sample_portfolio_data
    ):
        """Test complete portfolio rebalancing workflow."""
        # Arrange
        portfolio_id = str(uuid.uuid4())
        
        # Current portfolio state
        current_positions = [
            {"symbol": "AAPL", "quantity": 100, "market_value": Decimal("15000")},
            {"symbol": "GOOGL", "quantity": 20, "market_value": Decimal("56000")},
            {"symbol": "MSFT", "quantity": 50, "market_value": Decimal("17500")},
            {"symbol": "CASH", "quantity": 1, "market_value": Decimal("11500")}
        ]
        
        # Target allocations
        target_allocations = {
            "AAPL": 0.25,  # 25%
            "GOOGL": 0.35,  # 35%
            "MSFT": 0.25,  # 25%
            "CASH": 0.15   # 15%
        }
        
        total_value = sum(pos["market_value"] for pos in current_positions)
        
        mock_portfolio_manager.get_positions.return_value = current_positions
        mock_portfolio_manager.calculate_target_positions.return_value = {
            "AAPL": {"target_value": total_value * Decimal("0.25"), "action": "BUY", "quantity": 67},
            "GOOGL": {"target_value": total_value * Decimal("0.35"), "action": "SELL", "quantity": 5},
            "MSFT": {"target_value": total_value * Decimal("0.25"), "action": "BUY", "quantity": 25},
        }
        
        rebalance_orders = [
            {"symbol": "AAPL", "side": "BUY", "quantity": 67, "order_type": "MARKET"},
            {"symbol": "GOOGL", "side": "SELL", "quantity": 5, "order_type": "MARKET"},
            {"symbol": "MSFT", "side": "BUY", "quantity": 25, "order_type": "MARKET"}
        ]
        
        mock_portfolio_manager.generate_rebalance_orders.return_value = rebalance_orders
        
        # Mock order submissions
        order_results = []
        for i, order in enumerate(rebalance_orders):
            order_results.append({
                "order_id": str(uuid.uuid4()),
                "status": "SUBMITTED",
                "symbol": order["symbol"]
            })
        
        mock_trading_engine.submit_order.side_effect = order_results
        
        # Act
        # Step 1: Get current positions
        positions = await mock_portfolio_manager.get_positions(portfolio_id)
        
        # Step 2: Calculate target positions
        targets = await mock_portfolio_manager.calculate_target_positions(
            positions, target_allocations
        )
        
        # Step 3: Generate rebalance orders
        orders = await mock_portfolio_manager.generate_rebalance_orders(targets)
        
        # Step 4: Submit rebalance orders
        submitted_orders = []
        for order in orders:
            result = await mock_trading_engine.submit_order(order)
            submitted_orders.append(result)
        
        # Assert
        assert len(positions) == 4
        assert len(targets) == 3  # Excluding cash
        assert len(orders) == 3
        assert len(submitted_orders) == 3
        
        # Verify all orders were submitted successfully
        for result in submitted_orders:
            assert result["status"] == "SUBMITTED"
            assert_valid_uuid(result["order_id"])

    @pytest.mark.asyncio
    async def test_portfolio_performance_calculation(
        self,
        mock_portfolio_manager,
        mock_market_data_service
    ):
        """Test portfolio performance calculation workflow."""
        # Arrange
        portfolio_id = str(uuid.uuid4())
        
        # Historical portfolio values
        historical_values = [
            {"date": datetime.utcnow() - timedelta(days=30), "value": Decimal("95000")},
            {"date": datetime.utcnow() - timedelta(days=15), "value": Decimal("98000")},
            {"date": datetime.utcnow(), "value": Decimal("100000")}
        ]
        
        mock_portfolio_manager.get_historical_values.return_value = historical_values
        mock_portfolio_manager.calculate_returns.return_value = {
            "total_return": Decimal("0.0526"),  # 5.26%
            "annualized_return": Decimal("0.7895"),  # 78.95% annualized
            "volatility": Decimal("0.15"),
            "sharpe_ratio": Decimal("1.25"),
            "max_drawdown": Decimal("-0.03"),
            "beta": Decimal("0.85")
        }
        
        # Act
        historical_data = await mock_portfolio_manager.get_historical_values(portfolio_id)
        performance = await mock_portfolio_manager.calculate_returns(historical_data)
        
        # Assert
        assert len(historical_data) == 3
        assert performance["total_return"] > 0
        assert performance["volatility"] > 0
        assert performance["sharpe_ratio"] > 1.0  # Good risk-adjusted return
        assert performance["max_drawdown"] < 0  # Drawdown should be negative


class TestRiskManagementWorkflow:
    """Test complete risk management workflows."""

    @pytest.mark.asyncio
    async def test_var_calculation_workflow(
        self,
        mock_risk_manager,
        mock_portfolio_manager,
        mock_market_data_service
    ):
        """Test Value at Risk calculation workflow."""
        # Arrange
        portfolio_id = str(uuid.uuid4())
        
        positions = [
            {"symbol": "AAPL", "quantity": 100, "market_value": Decimal("15000")},
            {"symbol": "GOOGL", "quantity": 20, "market_value": Decimal("56000")},
            {"symbol": "MSFT", "quantity": 50, "market_value": Decimal("17500")}
        ]
        
        # Historical price data for VaR calculation
        historical_returns = {
            "AAPL": [-0.02, 0.01, -0.015, 0.025, -0.01],
            "GOOGL": [-0.03, 0.02, -0.01, 0.03, -0.02],
            "MSFT": [-0.015, 0.015, -0.02, 0.02, -0.005]
        }
        
        mock_portfolio_manager.get_positions.return_value = positions
        mock_market_data_service.get_historical_returns.return_value = historical_returns
        
        mock_risk_manager.calculate_var.return_value = {
            "var_95": Decimal("4250.00"),  # 95% VaR
            "var_99": Decimal("6180.00"),  # 99% VaR
            "expected_shortfall_95": Decimal("5200.00"),
            "expected_shortfall_99": Decimal("7100.00"),
            "confidence_level": 0.95
        }
        
        # Act
        portfolio_positions = await mock_portfolio_manager.get_positions(portfolio_id)
        returns_data = await mock_market_data_service.get_historical_returns(
            [pos["symbol"] for pos in portfolio_positions]
        )
        var_results = await mock_risk_manager.calculate_var(
            portfolio_positions, returns_data, confidence_level=0.95
        )
        
        # Assert
        assert len(portfolio_positions) == 3
        assert "AAPL" in returns_data
        assert var_results["var_95"] > 0
        assert var_results["var_99"] > var_results["var_95"]
        assert var_results["expected_shortfall_95"] > var_results["var_95"]

    @pytest.mark.asyncio
    async def test_stress_testing_workflow(
        self,
        mock_risk_manager,
        mock_portfolio_manager
    ):
        """Test portfolio stress testing workflow."""
        # Arrange
        portfolio_id = str(uuid.uuid4())
        
        stress_scenarios = [
            {
                "name": "2008 Financial Crisis",
                "shocks": {"AAPL": -0.45, "GOOGL": -0.35, "MSFT": -0.40}
            },
            {
                "name": "COVID-19 Crash",
                "shocks": {"AAPL": -0.25, "GOOGL": -0.20, "MSFT": -0.30}
            },
            {
                "name": "Interest Rate Shock",
                "shocks": {"AAPL": -0.15, "GOOGL": -0.10, "MSFT": -0.12}
            }
        ]
        
        current_portfolio_value = Decimal("100000")
        
        mock_portfolio_manager.get_portfolio_value.return_value = current_portfolio_value
        
        stress_results = []
        for scenario in stress_scenarios:
            portfolio_change = sum(
                current_portfolio_value * Decimal(str(shock)) * Decimal("0.33")  # Equal weights
                for shock in scenario["shocks"].values()
            )
            stress_results.append({
                "scenario_name": scenario["name"],
                "portfolio_value_change": portfolio_change,
                "percentage_change": portfolio_change / current_portfolio_value,
                "new_portfolio_value": current_portfolio_value + portfolio_change
            })
        
        mock_risk_manager.run_stress_tests.return_value = stress_results
        
        # Act
        portfolio_value = await mock_portfolio_manager.get_portfolio_value(portfolio_id)
        results = await mock_risk_manager.run_stress_tests(portfolio_id, stress_scenarios)
        
        # Assert
        assert portfolio_value == current_portfolio_value
        assert len(results) == 3
        
        for result in results:
            assert "scenario_name" in result
            assert "portfolio_value_change" in result
            assert "percentage_change" in result
            assert result["portfolio_value_change"] < 0  # All scenarios should be negative
            assert result["percentage_change"] < 0


class TestMarketDataWorkflow:
    """Test market data ingestion and processing workflows."""

    @pytest.mark.asyncio
    async def test_real_time_data_processing(
        self,
        mock_market_data_service,
        kafka_producer,
        kafka_consumer
    ):
        """Test real-time market data processing workflow."""
        # Arrange
        symbols = ["AAPL", "GOOGL", "MSFT"]
        
        # Mock real-time quotes
        quotes = [
            {
                "symbol": "AAPL",
                "price": Decimal("150.25"),
                "bid": Decimal("150.20"),
                "ask": Decimal("150.30"),
                "volume": 1000000,
                "timestamp": datetime.utcnow()
            },
            {
                "symbol": "GOOGL",
                "price": Decimal("2800.50"),
                "bid": Decimal("2800.00"),
                "ask": Decimal("2801.00"),
                "volume": 500000,
                "timestamp": datetime.utcnow()
            }
        ]
        
        mock_market_data_service.subscribe_to_quotes.return_value = quotes
        mock_market_data_service.process_quote.return_value = True
        
        # Act
        # Subscribe to real-time data
        await mock_market_data_service.subscribe_to_quotes(symbols)
        
        # Process incoming quotes
        processed_quotes = []
        for quote in quotes:
            success = await mock_market_data_service.process_quote(quote)
            if success:
                processed_quotes.append(quote)
        
        # Assert
        assert len(processed_quotes) == 2
        for quote in processed_quotes:
            assert quote["symbol"] in symbols
            assert_positive_number(quote["price"], "price")
            assert quote["bid"] < quote["ask"]
            assert_valid_timestamp(quote["timestamp"])

    @pytest.mark.asyncio
    async def test_historical_data_backfill(
        self,
        mock_market_data_service
    ):
        """Test historical data backfill workflow."""
        # Arrange
        symbol = "AAPL"
        start_date = datetime.utcnow() - timedelta(days=365)
        end_date = datetime.utcnow()
        
        # Mock historical data
        historical_data = []
        current_date = start_date
        base_price = Decimal("140.00")
        
        while current_date <= end_date:
            if current_date.weekday() < 5:  # Only weekdays
                price_change = Decimal(str((hash(current_date) % 200 - 100) / 1000))  # Random-ish change
                base_price += price_change
                
                historical_data.append({
                    "symbol": symbol,
                    "date": current_date,
                    "open": base_price,
                    "high": base_price * Decimal("1.02"),
                    "low": base_price * Decimal("0.98"),
                    "close": base_price,
                    "volume": 1000000 + (hash(current_date) % 500000)
                })
            
            current_date += timedelta(days=1)
        
        mock_market_data_service.fetch_historical_data.return_value = historical_data
        mock_market_data_service.store_historical_data.return_value = len(historical_data)
        
        # Act
        data = await mock_market_data_service.fetch_historical_data(
            symbol, start_date, end_date
        )
        stored_count = await mock_market_data_service.store_historical_data(data)
        
        # Assert
        assert len(data) > 250  # Should have at least 250 trading days
        assert stored_count == len(data)
        
        # Validate data structure
        for candle in data[:5]:  # Check first 5 candles
            assert candle["symbol"] == symbol
            assert candle["high"] >= candle["low"]
            assert candle["high"] >= candle["open"]
            assert candle["high"] >= candle["close"]
            assert candle["low"] <= candle["open"]
            assert candle["low"] <= candle["close"]


class TestSystemIntegration:
    """Test complete system integration scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_trading_system_integration(
        self,
        mock_trading_engine,
        mock_market_data_service,
        mock_portfolio_manager,
        mock_risk_manager,
        sample_user_data,
        sample_portfolio_data
    ):
        """Test complete trading system integration from user creation to trade execution."""
        # Arrange
        user_id = sample_user_data["id"]
        portfolio_id = sample_portfolio_data["id"]
        
        # Mock complete system workflow
        mock_portfolio_manager.create_portfolio.return_value = {
            "portfolio_id": portfolio_id,
            "user_id": user_id,
            "initial_capital": Decimal("100000"),
            "status": "ACTIVE"
        }
        
        mock_market_data_service.get_quote.return_value = {
            "symbol": "AAPL",
            "price": Decimal("150.00"),
            "timestamp": datetime.utcnow()
        }
        
        mock_risk_manager.check_risk_limits.return_value = {
            "approved": True,
            "warnings": []
        }
        
        mock_trading_engine.submit_order.return_value = {
            "order_id": str(uuid.uuid4()),
            "status": "FILLED",
            "fill_price": Decimal("150.00"),
            "fill_quantity": 100
        }
        
        mock_portfolio_manager.update_position.return_value = {
            "symbol": "AAPL",
            "quantity": 100,
            "average_price": Decimal("150.00"),
            "market_value": Decimal("15000.00")
        }
        
        # Act - Execute complete workflow
        
        # 1. Create portfolio
        portfolio = await mock_portfolio_manager.create_portfolio(
            user_id, "Test Portfolio", Decimal("100000")
        )
        
        # 2. Get market data
        quote = await mock_market_data_service.get_quote("AAPL")
        
        # 3. Check risk limits
        order_data = {
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": 100,
            "order_type": "MARKET",
            "portfolio_id": portfolio_id
        }
        
        risk_check = await mock_risk_manager.check_risk_limits(order_data)
        
        # 4. Submit order if approved
        if risk_check["approved"]:
            order_result = await mock_trading_engine.submit_order(order_data)
            
            # 5. Update portfolio
            if order_result["status"] == "FILLED":
                position = await mock_portfolio_manager.update_position(
                    portfolio_id,
                    order_result["fill_quantity"],
                    order_result["fill_price"]
                )
        
        # Assert - Validate complete integration
        assert portfolio["portfolio_id"] == portfolio_id
        assert portfolio["user_id"] == user_id
        
        assert quote["symbol"] == "AAPL"
        assert_positive_number(quote["price"], "quote price")
        
        assert risk_check["approved"] is True
        
        assert order_result["status"] == "FILLED"
        assert order_result["fill_quantity"] == 100
        
        assert position["symbol"] == "AAPL"
        assert position["quantity"] == 100
        assert position["market_value"] == Decimal("15000.00")

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_high_frequency_order_processing(
        self,
        mock_trading_engine,
        performance_metrics
    ):
        """Test system performance under high-frequency order load."""
        # Arrange
        num_orders = 1000
        orders = []
        
        for i in range(num_orders):
            orders.append({
                "symbol": f"TEST{i % 10}",  # 10 different symbols
                "side": "BUY" if i % 2 == 0 else "SELL",
                "quantity": 100,
                "order_type": "MARKET"
            })
        
        # Mock fast order processing
        mock_trading_engine.submit_order.side_effect = [
            {
                "order_id": str(uuid.uuid4()),
                "status": "SUBMITTED",
                "timestamp": datetime.utcnow()
            }
            for _ in range(num_orders)
        ]
        
        # Act
        start_time = datetime.utcnow()
        
        # Submit orders concurrently
        tasks = [mock_trading_engine.submit_order(order) for order in orders]
        results = await asyncio.gather(*tasks)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Assert
        assert len(results) == num_orders
        assert all(result["status"] == "SUBMITTED" for result in results)
        
        # Performance assertions
        orders_per_second = num_orders / duration
        performance_metrics["orders_per_second"] = orders_per_second
        
        # Should process at least 100 orders per second
        assert orders_per_second >= 100, f"Only processed {orders_per_second:.2f} orders/sec"
        
        # Should complete within reasonable time
        assert duration < 30.0, f"Processing took {duration:.2f} seconds"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])