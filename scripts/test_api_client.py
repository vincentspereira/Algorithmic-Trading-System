#!/usr/bin/env python3
"""
Comprehensive API Test Client
Tests all endpoints of the Algorithmic Trading System API

Usage:
    python test_api_client.py [--host HOST] [--port PORT]
"""

import asyncio
import json
import time
import websockets
import requests
from datetime import datetime
from typing import Dict, Any
import argparse

class APITestClient:
    """Test client for the Algorithmic Trading System API"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.headers = {"Authorization": "Bearer test-token"}
        self.test_results = []
    
    def log_test(self, name: str, success: bool, details: str = "", duration: float = 0):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append({
            "name": name,
            "success": success,
            "details": details,
            "duration": duration
        })
        print(f"{status} {name} ({duration:.3f}s) - {details}")
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        start_time = time.time()
        try:
            response = requests.get(f"{self.base_url}/health")
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                services_healthy = all(data.get("services", {}).values() or [True])
                self.log_test("Health Check", True, 
                             f"Status: {data.get('status')}, Services: {data.get('services')}", duration)
            else:
                self.log_test("Health Check", False, f"Status code: {response.status_code}", duration)
        except Exception as e:
            self.log_test("Health Check", False, str(e), time.time() - start_time)
    
    def test_indicators_available(self):
        """Test available indicators endpoint"""
        start_time = time.time()
        try:
            response = requests.get(f"{self.base_url}/api/v1/indicators/available", headers=self.headers)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                indicator_count = len(data.get("data", {}))
                self.log_test("Available Indicators", True, 
                             f"Retrieved {indicator_count} indicator categories", duration)
            else:
                self.log_test("Available Indicators", False, f"Status code: {response.status_code}", duration)
        except Exception as e:
            self.log_test("Available Indicators", False, str(e), time.time() - start_time)
    
    def test_market_data_endpoint(self):
        """Test market data endpoint"""
        start_time = time.time()
        try:
            payload = {
                "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ", "asset_class": "STK"}],
                "period": "1d",
                "interval": "1m"
            }
            response = requests.post(f"{self.base_url}/api/v1/market-data", 
                                   json=payload, headers=self.headers)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                symbols_count = len(data.get("data", {}))
                self.log_test("Market Data", True, 
                             f"Retrieved data for {symbols_count} symbols", duration)
            else:
                self.log_test("Market Data", False, f"Status code: {response.status_code}", duration)
        except Exception as e:
            self.log_test("Market Data", False, str(e), time.time() - start_time)
    
    def test_real_time_quote(self):
        """Test real-time quote endpoint"""
        start_time = time.time()
        try:
            response = requests.get(f"{self.base_url}/api/v1/market-data/quote/AAPL", headers=self.headers)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                quote_data = data.get("data", {})
                self.log_test("Real-time Quote", True, 
                             f"Price: ${quote_data.get('price', 'N/A')}", duration)
            else:
                self.log_test("Real-time Quote", False, f"Status code: {response.status_code}", duration)
        except Exception as e:
            self.log_test("Real-time Quote", False, str(e), time.time() - start_time)
    
    def test_indicators_calculation(self):
        """Test indicators calculation endpoint"""
        start_time = time.time()
        try:
            payload = {
                "symbol": {"symbol": "AAPL", "exchange": "NASDAQ", "asset_class": "STK"},
                "indicator_types": ["rsi", "macd", "bollinger_bands"],
                "include_volume_weighted": True,
                "include_patterns": True
            }
            response = requests.post(f"{self.base_url}/api/v1/indicators", 
                                   json=payload, headers=self.headers)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                indicators_count = len(data.get("data", {}).get("indicators", {}))
                self.log_test("Indicators Calculation", True, 
                             f"Calculated {indicators_count} indicators", duration)
            else:
                self.log_test("Indicators Calculation", False, f"Status code: {response.status_code}", duration)
        except Exception as e:
            self.log_test("Indicators Calculation", False, str(e), time.time() - start_time)
    
    def test_order_submission(self):
        """Test order submission endpoint"""
        start_time = time.time()
        try:
            payload = {
                "symbol": {"symbol": "AAPL", "exchange": "NASDAQ", "asset_class": "STK"},
                "order_type": "MARKET",
                "side": "BUY",
                "quantity": 10.0,
                "time_in_force": "DAY"
            }
            response = requests.post(f"{self.base_url}/api/v1/orders", 
                                   json=payload, headers=self.headers)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                order_id = data.get("data", {}).get("order_id", "Unknown")
                self.log_test("Order Submission", True, 
                             f"Order ID: {order_id}", duration)
                return order_id
            else:
                self.log_test("Order Submission", False, f"Status code: {response.status_code}", duration)
        except Exception as e:
            self.log_test("Order Submission", False, str(e), time.time() - start_time)
        return None
    
    def test_get_orders(self):
        """Test get orders endpoint"""
        start_time = time.time()
        try:
            response = requests.get(f"{self.base_url}/api/v1/orders", headers=self.headers)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                orders_count = data.get("data", {}).get("count", 0)
                self.log_test("Get Orders", True, 
                             f"Retrieved {orders_count} orders", duration)
            else:
                self.log_test("Get Orders", False, f"Status code: {response.status_code}", duration)
        except Exception as e:
            self.log_test("Get Orders", False, str(e), time.time() - start_time)
    
    def test_portfolio_positions(self):
        """Test portfolio positions endpoint"""
        start_time = time.time()
        try:
            response = requests.get(f"{self.base_url}/api/v1/portfolio/positions", headers=self.headers)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                positions_count = data.get("data", {}).get("summary", {}).get("position_count", 0)
                total_value = data.get("data", {}).get("summary", {}).get("total_value", 0)
                self.log_test("Portfolio Positions", True, 
                             f"{positions_count} positions, Total: ${total_value:,.2f}", duration)
            else:
                self.log_test("Portfolio Positions", False, f"Status code: {response.status_code}", duration)
        except Exception as e:
            self.log_test("Portfolio Positions", False, str(e), time.time() - start_time)
    
    def test_portfolio_performance(self):
        """Test portfolio performance endpoint"""
        start_time = time.time()
        try:
            response = requests.get(f"{self.base_url}/api/v1/portfolio/performance?period=1d", 
                                  headers=self.headers)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                performance = data.get("data", {})
                total_return = performance.get("total_return_pct", 0)
                self.log_test("Portfolio Performance", True, 
                             f"1D Return: {total_return}%", duration)
            else:
                self.log_test("Portfolio Performance", False, f"Status code: {response.status_code}", duration)
        except Exception as e:
            self.log_test("Portfolio Performance", False, str(e), time.time() - start_time)
    
    async def test_websocket_market_data(self):
        """Test WebSocket market data stream"""
        start_time = time.time()
        try:
            uri = f"ws://localhost:8080/ws/market-data/test-client"
            async with websockets.connect(uri) as websocket:
                # Subscribe to AAPL
                await websocket.send(json.dumps({
                    "type": "subscribe",
                    "symbol": "AAPL"
                }))
                
                # Wait for confirmation
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                
                duration = time.time() - start_time
                if data.get("type") == "subscription_confirmed":
                    self.log_test("WebSocket Market Data", True, 
                                 f"Subscribed to {data.get('symbol')}", duration)
                else:
                    self.log_test("WebSocket Market Data", False, 
                                 f"Unexpected response: {data}", duration)
        except Exception as e:
            self.log_test("WebSocket Market Data", False, str(e), time.time() - start_time)
    
    async def test_websocket_trading(self):
        """Test WebSocket trading stream"""
        start_time = time.time()
        try:
            uri = f"ws://localhost:8080/ws/trading/test-client"
            async with websockets.connect(uri) as websocket:
                # Subscribe to order updates
                await websocket.send(json.dumps({
                    "type": "subscribe_orders"
                }))
                
                # Wait for confirmation
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                
                duration = time.time() - start_time
                if data.get("type") == "order_subscription_confirmed":
                    self.log_test("WebSocket Trading", True, 
                                 "Subscribed to order updates", duration)
                else:
                    self.log_test("WebSocket Trading", False, 
                                 f"Unexpected response: {data}", duration)
        except Exception as e:
            self.log_test("WebSocket Trading", False, str(e), time.time() - start_time)
    
    def test_metrics_endpoint(self):
        """Test Prometheus metrics endpoint"""
        start_time = time.time()
        try:
            response = requests.get(f"{self.base_url}/metrics")
            duration = time.time() - start_time
            
            if response.status_code == 200 and "# HELP" in response.text:
                metrics_count = response.text.count("# HELP")
                self.log_test("Metrics Endpoint", True, 
                             f"Retrieved {metrics_count} metrics", duration)
            else:
                self.log_test("Metrics Endpoint", False, f"Status code: {response.status_code}", duration)
        except Exception as e:
            self.log_test("Metrics Endpoint", False, str(e), time.time() - start_time)
    
    async def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting Comprehensive API Tests")
        print("=" * 60)
        
        # REST API Tests
        print("\n📡 Testing REST API Endpoints:")
        self.test_health_endpoint()
        self.test_indicators_available()
        self.test_market_data_endpoint()
        self.test_real_time_quote()
        self.test_indicators_calculation()
        
        # Trading API Tests
        print("\n💰 Testing Trading API Endpoints:")
        order_id = self.test_order_submission()
        self.test_get_orders()
        self.test_portfolio_positions()
        self.test_portfolio_performance()
        
        # WebSocket Tests
        print("\n🔌 Testing WebSocket Endpoints:")
        await self.test_websocket_market_data()
        await self.test_websocket_trading()
        
        # Monitoring Tests
        print("\n📊 Testing Monitoring Endpoints:")
        self.test_metrics_endpoint()
        
        # Summary
        print("\n" + "=" * 60)
        print("🎯 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        success_rate = (passed / total) * 100 if total > 0 else 0
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Status assessment
        if success_rate >= 90:
            status = "🟢 EXCELLENT"
        elif success_rate >= 75:
            status = "🟡 GOOD"
        elif success_rate >= 50:
            status = "🟠 NEEDS IMPROVEMENT"
        else:
            status = "🔴 CRITICAL ISSUES"
        
        print(f"Overall Status: {status}")
        
        # Failed tests details
        failed_tests = [r for r in self.test_results if not r["success"]]
        if failed_tests:
            print(f"\n❌ Failed Tests:")
            for test in failed_tests:
                print(f"  - {test['name']}: {test['details']}")
        
        return success_rate

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="API Test Client")
    parser.add_argument("--host", default="localhost", help="API host")
    parser.add_argument("--port", type=int, default=8080, help="API port")
    
    args = parser.parse_args()
    base_url = f"http://{args.host}:{args.port}"
    
    # Create test client
    client = APITestClient(base_url)
    
    # Run tests
    success_rate = await client.run_all_tests()
    
    # Exit with appropriate code
    exit_code = 0 if success_rate >= 80 else 1
    exit(exit_code)

if __name__ == "__main__":
    asyncio.run(main())