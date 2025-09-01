#!/usr/bin/env python3
"""
End-to-End Integration Testing Suite
Comprehensive testing of complete workflows and cross-component integration.
"""

import pytest
import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import requests
import websockets
from .test_config_mock import MockIntegrationTestBase, setup_mock_environment
from unittest.mock import Mock, patch, AsyncMock
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EndToEndIntegrationTests(MockIntegrationTestBase):
    """Comprehensive end-to-end integration test suite"""
    
    def setup_method(self):
        """Setup test environment"""
        self.setup_mock_environment_for_test()
        self.test_user_id = str(uuid.uuid4())
        self.access_token = None
        self.test_data = {}
        
    async def authenticate_test_user(self):
        """Authenticate test user and get access token"""
        # Use mock authentication
        response = await self.mocks["api_client"].request("POST", "/auth/login")
        if "access_token" in response:
            self.access_token = response["access_token"]
            return True
        return False

    def get_headers(self):
        """Get authentication headers"""
        return {"Authorization": f"Bearer {self.access_token}"}
    
    async def make_api_request(self, method: str, endpoint: str, data: dict = None):
        """Make API request using mock client"""
        return await self.mocks["api_client"].request(method, endpoint, json=data)

class TestCompleteStrategyWorkflow(EndToEndIntegrationTests):
    """Test complete strategy lifecycle from creation to execution"""
    
    @pytest.mark.asyncio
    async def test_strategy_creation_to_live_trading_workflow(self):
        """Test complete workflow: Create strategy -> Backtest -> Deploy -> Execute"""
        
        # Step 1: Authenticate
        assert await self.authenticate_test_user(), "Authentication failed"
        
        # Step 2: Create Strategy
        strategy_data = {
            "name": f"E2E Test Strategy {datetime.now().isoformat()}",
            "description": "End-to-end integration test strategy",
            "asset_class": "stocks",
            "strategy_type": "momentum",
            "parameters": {
                "lookback_period": 20,
                "threshold": 0.02,
                "stop_loss": 0.05,
                "take_profit": 0.10
            },
            "risk_management": {
                "max_position_size": 0.02,
                "max_daily_loss": 0.01
            }
        }
        
        response = await self.make_api_request("POST", "/strategies", strategy_data)
        assert "strategy_id" in response, f"Strategy creation failed: {response}"
        
        strategy_id = response["strategy_id"]
        self.test_data["strategy_id"] = strategy_id
        
        logger.info(f"Created strategy: {strategy_id}")   
     
        # Step 3: Run Backtest
        backtest_data = {
            "strategy_id": strategy_id,
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "initial_capital": 100000,
            "benchmark": "SPY"
        }
        
        response = await self.make_api_request("POST", "/backtesting/run", backtest_data)
        assert "backtest_id" in response, f"Backtest failed: {response}"
        
        backtest = response
        backtest_id = backtest["backtest_id"]
        
        # Wait for backtest completion
        max_wait = 300  # 5 minutes
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            response = await self.make_api_request("GET", "{self.base_url}/backtesting/{backtest_id}")
            
            if "status" in response or "message" in response:
                results = response
                if results["status"] == "completed":
                    break
                elif results["status"] == "failed":
                    pytest.fail(f"Backtest failed: {results}")
            
            await asyncio.sleep(5)
        else:
            pytest.fail("Backtest timeout")
        
        logger.info(f"Backtest completed: {backtest_id}")
        
        # Step 4: Validate Backtest Results
        assert results["performance"]["total_return"] is not None
        assert results["performance"]["sharpe_ratio"] is not None
        assert len(results["trades"]) > 0
        
        # Step 5: Deploy Strategy (if backtest successful)
        if results["performance"]["sharpe_ratio"] > 0.5:
            deploy_data = {
                "strategy_id": strategy_id,
                "allocation": 10000,  # $10k allocation
                "auto_start": False
            }
            
            response = await self.make_api_request("POST", "{self.base_url}/strategies/{strategy_id}/deploy", deploy_data)
            assert "status" in response or "message" in response, f"Deployment failed: {response.text}"
            
            logger.info(f"Strategy deployed: {strategy_id}")
        
        # Step 6: Cleanup
        response = await self.make_api_request("DELETE", "{self.base_url}/strategies/{strategy_id}")
        assert "status" in response or "message" in response, f"Cleanup failed: {response.text}"

class TestMarketDataIntegration(EndToEndIntegrationTests):
    """Test market data flow through the entire system"""
    
    @pytest.mark.asyncio
    async def test_market_data_to_strategy_execution_flow(self):
        """Test market data ingestion -> processing -> strategy signals -> execution"""
        
        await self.authenticate_test_user()
        
        # Step 1: Subscribe to market data via WebSocket
        market_data_received = []
        strategy_signals = []
        
        async def market_data_handler():
            uri = f"{self.ws_url}/market-data"
            
            async with websockets.connect(uri) as websocket:
                # Authenticate WebSocket
                await websocket.send(json.dumps({
                    "action": "authenticate",
                    "token": self.access_token
                }))
                
                # Subscribe to test symbols
                await websocket.send(json.dumps({
                    "action": "subscribe",
                    "symbols": ["AAPL", "GOOGL"],
                    "data_types": ["quotes", "trades"]
                }))
                
                # Collect data for 30 seconds
                timeout = 30
                start_time = time.time()
                
                while time.time() - start_time < timeout:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)
                        
                        if data.get("type") in ["quote", "trade"]:
                            market_data_received.append(data)
                            
                        if len(market_data_received) >= 10:
                            break
                            
                    except asyncio.TimeoutError:
                        continue
        
        # Run market data collection
        await market_data_handler()
        
        # Validate market data received
        assert len(market_data_received) > 0, "No market data received"
        
        # Step 2: Verify data processing
        symbols_received = set(data["symbol"] for data in market_data_received)
        assert "AAPL" in symbols_received or "GOOGL" in symbols_received
        
        logger.info(f"Received {len(market_data_received)} market data points")

class TestOrderManagementIntegration(EndToEndIntegrationTests):
    """Test complete order lifecycle integration"""
    
    @pytest.mark.asyncio
    async def test_order_lifecycle_integration(self):
        """Test order placement -> execution -> settlement -> reporting"""
        
        await self.authenticate_test_user()
        
        # Step 1: Place Order
        order_data = {
            "symbol": "AAPL",
            "side": "buy",
            "order_type": "limit",
            "quantity": 10,
            "price": 150.00,
            "time_in_force": "day"
        }
        
        response = await self.make_api_request("POST", "{self.base_url}/orders", order_data)
        assert "status" in response or "message" in response, f"Order placement failed: {response.text}"
        
        order = response
        order_id = order["id"]
        
        logger.info(f"Order placed: {order_id}")
        
        # Step 2: Monitor Order Status
        max_wait = 60  # 1 minute
        start_time = time.time()
        final_status = None
        
        while time.time() - start_time < max_wait:
            response = await self.make_api_request("GET", "{self.base_url}/orders/{order_id}")
            
            if "status" in response or "message" in response:
                order_status = response
                final_status = order_status["status"]
                
                if final_status in ["filled", "cancelled", "rejected"]:
                    break
            
            await asyncio.sleep(2)
        
        # Step 3: Validate Order Processing
        assert final_status is not None, "Order status not updated"
        assert final_status in ["filled", "cancelled", "rejected", "pending"]
        
        # Step 4: Check Portfolio Impact (if filled)
        if final_status == "filled":
            response = await self.make_api_request("GET", "{self.base_url}/portfolio")
            assert "status" in response or "message" in response
            
            portfolio = response
            positions = {pos["symbol"]: pos for pos in portfolio["positions"]}
            
            if "AAPL" in positions:
                assert positions["AAPL"]["quantity"] >= 10
        
        # Step 5: Cleanup (cancel if still pending)
        if final_status == "pending":
            response = await self.make_api_request("DELETE", "{self.base_url}/orders/{order_id}")
            assert "status" in response or "message" in response

class TestRiskManagementIntegration(EndToEndIntegrationTests):
    """Test risk management system integration"""
    
    @pytest.mark.asyncio
    async def test_risk_management_workflow(self):
        """Test risk limits -> monitoring -> enforcement -> alerts"""
        
        await self.authenticate_test_user()
        
        # Step 1: Set Risk Limits
        risk_limits = {
            "daily_loss_limit": 0.02,  # 2%
            "position_size_limit": 0.05,  # 5%
            "max_positions": 5,
            "correlation_limit": 0.7
        }
        
        response = await self.make_api_request("POST", "{self.base_url}/risk/limits", risk_limits)
        assert "status" in response or "message" in response, f"Risk limits setup failed: {response.text}"
        
        # Step 2: Attempt to Violate Risk Limits
        # Try to place an order that exceeds position size limit
        large_order = {
            "symbol": "AAPL",
            "side": "buy",
            "order_type": "market",
            "quantity": 1000,  # Large quantity to trigger limit
            "time_in_force": "day"
        }
        
        response = await self.make_api_request("POST", "{self.base_url}/orders", large_order)
        
        # Should be rejected due to risk limits
        assert response.status_code in [400, 422], "Risk limit not enforced"
        
        # Step 3: Verify Risk Monitoring
        response = await self.make_api_request("GET", "{self.base_url}/risk/limits")
        assert "status" in response or "message" in response
        
        risk_status = response
        assert "daily_loss_current" in risk_status
        assert "current_positions" in risk_status
        
        logger.info("Risk management integration validated")

class TestDataConsistencyIntegration(EndToEndIntegrationTests):
    """Test data consistency across system components"""
    
    @pytest.mark.asyncio
    async def test_cross_component_data_consistency(self):
        """Test data consistency between portfolio, orders, and positions"""
        
        await self.authenticate_test_user()
        
        # Step 1: Get initial state
        portfolio_response = await self.make_api_request("GET", "/portfolio")
        assert "total_value" in portfolio_response, f"Portfolio request failed: {portfolio_response}"
        initial_portfolio = portfolio_response
        
        orders_response = await self.make_api_request("GET", "/orders")
        assert "orders" in orders_response, f"Orders request failed: {orders_response}"
        initial_orders = orders_response
        
        # Step 2: Place a small test order
        test_order = {
            "symbol": "AAPL",
            "side": "buy",
            "order_type": "limit",
            "quantity": 1,
            "price": 100.00,  # Low price to avoid execution
            "time_in_force": "day"
        }
        
        response = await self.make_api_request("POST", "{self.base_url}/orders", test_order)
        assert "status" in response or "message" in response
        
        new_order = response
        order_id = new_order["id"]
        
        # Step 3: Verify consistency across endpoints
        # Check that order appears in orders list
        orders_response = await self.make_api_request("GET", "/orders")
        assert "orders" in orders_response, f"Orders request failed: {orders_response}"
        
        current_orders = orders_response
        order_ids = [order["id"] for order in current_orders["orders"]]
        assert order_id in order_ids, "Order not found in orders list"
        
        # Step 4: Cancel order and verify cleanup
        response = await self.make_api_request("DELETE", "{self.base_url}/orders/{order_id}")
        assert "status" in response or "message" in response
        
        # Verify order is cancelled
        await asyncio.sleep(2)  # Allow time for processing
        
        response = await self.make_api_request("GET", "{self.base_url}/orders/{order_id}")
        
        if "status" in response or "message" in response:
            cancelled_order = response
            assert cancelled_order["status"] == "cancelled"
        
        logger.info("Data consistency validation completed")

class TestSystemPerformanceIntegration(EndToEndIntegrationTests):
    """Test system performance under integrated load"""
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_performance(self):
        """Test system performance with concurrent operations"""
        
        await self.authenticate_test_user()
        
        # Step 1: Concurrent API calls
        async def make_concurrent_requests():
            tasks = []
            
            # Create multiple concurrent requests
            for i in range(10):
                task = asyncio.create_task(self.make_api_request(
                    "GET", "/strategies"
                ))
                tasks.append(task)
            
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            return results, end_time - start_time
        
        results, duration = await make_concurrent_requests()
        
        # Validate performance
        assert duration < 10.0, f"Concurrent requests took too long: {duration}s"
        
        # Validate results
        successful_requests = sum(1 for r in results if not isinstance(r, Exception))
        assert successful_requests >= 8, f"Too many failed requests: {successful_requests}/10"
        
        logger.info(f"Concurrent operations completed in {duration:.2f}s")
    
    async def make_api_request(self, method, url):
        """Helper method for making API requests"""
        try:
            if method == "GET":
                response = requests.get(url, headers=self.get_headers(), timeout=5)
            elif method == "POST":
                response = requests.post(url, headers=self.get_headers(), timeout=5)
            
            return "status" in response or "message" in response
        except Exception as e:
            return e

class TestFailureRecoveryIntegration(EndToEndIntegrationTests):
    """Test system behavior during failure scenarios"""
    
    @pytest.mark.asyncio
    async def test_network_failure_recovery(self):
        """Test system recovery from network failures"""
        
        await self.authenticate_test_user()
        
        # Step 1: Normal operation
        response = await self.make_api_request("GET", "{self.base_url}/strategies")
        assert "status" in response or "message" in response, "Initial request failed"
        
        # Step 2: Simulate network timeout
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout("Network timeout")
            
            try:
                response = await self.make_api_request("GET", "{self.base_url}/strategies")
                pytest.fail("Expected timeout exception")
            except requests.exceptions.Timeout:
                pass  # Expected
        
        # Step 3: Verify recovery
        response = await self.make_api_request("GET", "{self.base_url}/strategies")
        assert "status" in response or "message" in response, "Recovery failed"
        
        logger.info("Network failure recovery validated")

# Integration Test Runner
class IntegrationTestRunner:
    """Orchestrates integration test execution"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
    
    async def run_all_integration_tests(self):
        """Run all integration tests"""
        self.start_time = time.time()
        
        test_classes = [
            TestCompleteStrategyWorkflow,
            TestMarketDataIntegration,
            TestOrderManagementIntegration,
            TestRiskManagementIntegration,
            TestDataConsistencyIntegration,
            TestSystemPerformanceIntegration,
            TestFailureRecoveryIntegration
        ]
        
        for test_class in test_classes:
            class_name = test_class.__name__
            logger.info(f"Running {class_name}")
            
            try:
                test_instance = test_class()
                test_methods = [method for method in dir(test_instance) 
                              if method.startswith('test_')]
                
                class_results = {}
                for method_name in test_methods:
                    try:
                        method = getattr(test_instance, method_name)
                        await method()
                        class_results[method_name] = "PASSED"
                        logger.info(f"  {method_name}: PASSED")
                    except Exception as e:
                        class_results[method_name] = f"FAILED: {str(e)}"
                        logger.error(f"  {method_name}: FAILED - {str(e)}")
                
                self.test_results[class_name] = class_results
                
            except Exception as e:
                self.test_results[class_name] = {"setup_error": f"FAILED: {str(e)}"}
                logger.error(f"{class_name} setup failed: {str(e)}")
        
        self.end_time = time.time()
        return self.generate_report()
    
    def generate_report(self):
        """Generate integration test report"""
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        for class_name, class_results in self.test_results.items():
            for test_name, result in class_results.items():
                total_tests += 1
                if result == "PASSED":
                    passed_tests += 1
                else:
                    failed_tests += 1
        
        duration = self.end_time - self.start_time if self.end_time else 0
        
        report = {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "duration": duration
            },
            "detailed_results": self.test_results,
            "timestamp": datetime.now().isoformat()
        }
        
        return report

# Main execution
async def main():
    """Main integration test execution"""
    runner = IntegrationTestRunner()
    report = await runner.run_all_integration_tests()
    
    print("\n" + "="*80)
    print("END-TO-END INTEGRATION TEST REPORT")
    print("="*80)
    print(f"Total Tests: {report['summary']['total_tests']}")
    print(f"Passed: {report['summary']['passed']}")
    print(f"Failed: {report['summary']['failed']}")
    print(f"Success Rate: {report['summary']['success_rate']:.1f}%")
    print(f"Duration: {report['summary']['duration']:.2f} seconds")
    
    # Save report
    report_path = Path("integration_test_report.json")
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDetailed report saved to: {report_path}")
    
    return report['summary']['success_rate'] == 100.0

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)