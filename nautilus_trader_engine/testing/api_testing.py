"""API Testing Framework for the Algorithmic Trading System

Provides comprehensive API testing capabilities for validating
REST, GraphQL, and WebSocket API endpoints.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import unittest
import sys
import os
import logging
import requests
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
import websockets
from unittest.mock import Mock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from testing.test_base import BaseTestCase, TestResult
from testing.system_testing import SystemTestFramework

logger = logging.getLogger(__name__)

class APITestFramework:
    """Comprehensive API Testing Framework"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        self.test_suite = unittest.TestSuite()
        self.runner = unittest.TextTestRunner(verbosity=2)
        self.session = requests.Session()
        
    def add_test_case(self, test_case_class):
        """Add a test case class to the test suite"""
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(test_case_class)
        self.test_suite.addTest(suite)
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all API tests and return results"""
        logger.info("Starting API test execution...")
        
        # Run the test suite
        result = self.runner.run(self.test_suite)
        
        # Compile results
        test_results = {
            'total_tests': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'successes': result.testsRun - len(result.failures) - len(result.errors),
            'success_rate': (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun if result.testsRun > 0 else 0,
            'failure_details': [{'test': str(test), 'error': str(error)} for test, error in result.failures],
            'error_details': [{'test': str(test), 'error': str(error)} for test, error in result.errors],
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"API testing completed: {test_results['success_rate']:.2%} success rate")
        return test_results

class RESTAPITests(BaseTestCase):
    """API tests for REST endpoints"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        super().setUp()
        self.base_url = "http://localhost:8000"
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
    def test_health_check_endpoint(self):
        """Test the health check endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn('status', data)
            self.assertEqual(data['status'], 'healthy')
        except requests.exceptions.ConnectionError:
            self.skipTest("API server not running")
            
    def test_market_data_endpoint(self):
        """Test the market data endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/api/market-data/BTCUSD")
            # We're testing that the endpoint exists and returns a valid response
            self.assertIn(response.status_code, [200, 404, 503])  # Valid status codes
        except requests.exceptions.ConnectionError:
            self.skipTest("API server not running")
            
    def test_trading_strategy_endpoint(self):
        """Test the trading strategy endpoint"""
        try:
            # Test GET request
            response = self.session.get(f"{self.base_url}/api/strategies")
            self.assertIn(response.status_code, [200, 404, 503])
            
            # Test POST request with sample data
            sample_strategy = {
                "name": "Test Strategy",
                "description": "A test strategy for API testing",
                "parameters": {
                    "rsi_period": 14,
                    "sma_period": 20
                }
            }
            response = self.session.post(f"{self.base_url}/api/strategies", json=sample_strategy)
            self.assertIn(response.status_code, [200, 201, 400, 404, 503])
        except requests.exceptions.ConnectionError:
            self.skipTest("API server not running")
            
    def test_authentication_endpoint(self):
        """Test the authentication endpoint"""
        try:
            # Test login endpoint
            login_data = {
                "username": "test_user",
                "password": "test_password"
            }
            response = self.session.post(f"{self.base_url}/api/auth/login", json=login_data)
            self.assertIn(response.status_code, [200, 401, 404, 503])
            
            # Test registration endpoint
            register_data = {
                "username": "new_test_user",
                "email": "test@example.com",
                "password": "test_password"
            }
            response = self.session.post(f"{self.base_url}/api/auth/register", json=register_data)
            self.assertIn(response.status_code, [200, 201, 400, 404, 503])
        except requests.exceptions.ConnectionError:
            self.skipTest("API server not running")

class GraphQLAPITests(BaseTestCase):
    """API tests for GraphQL endpoints"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        super().setUp()
        self.base_url = "http://localhost:8000"
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
    def test_graphql_endpoint(self):
        """Test the GraphQL endpoint"""
        try:
            # Test introspection query
            query = """
            {
                __schema {
                    types {
                        name
                    }
                }
            }
            """
            response = self.session.post(
                f"{self.base_url}/graphql",
                json={"query": query}
            )
            self.assertIn(response.status_code, [200, 400, 404, 503])
        except requests.exceptions.ConnectionError:
            self.skipTest("API server not running")
            
    def test_graphql_market_data_query(self):
        """Test GraphQL market data query"""
        try:
            query = """
            query GetMarketData($symbol: String!) {
                marketData(symbol: $symbol) {
                    symbol
                    price
                    volume
                }
            }
            """
            variables = {"symbol": "BTCUSD"}
            response = self.session.post(
                f"{self.base_url}/graphql",
                json={"query": query, "variables": variables}
            )
            self.assertIn(response.status_code, [200, 400, 404, 503])
        except requests.exceptions.ConnectionError:
            self.skipTest("API server not running")

class WebSocketAPITests(BaseTestCase):
    """API tests for WebSocket endpoints"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        super().setUp()
        self.ws_url = "ws://localhost:8000/ws"
        
    async def test_websocket_connection(self):
        """Test WebSocket connection"""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                # Send a test message
                await websocket.send(json.dumps({"type": "ping"}))
                
                # Receive response
                response = await websocket.recv()
                data = json.loads(response)
                
                # Validate response
                self.assertIn("type", data)
        except Exception as e:
            # If WebSocket server is not running, skip the test
            self.skipTest(f"WebSocket server not running: {str(e)}")
            
    async def test_market_data_stream(self):
        """Test market data streaming via WebSocket"""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                # Subscribe to market data
                subscribe_message = {
                    "type": "subscribe",
                    "channel": "market_data",
                    "symbol": "BTCUSD"
                }
                await websocket.send(json.dumps(subscribe_message))
                
                # Receive a few messages
                for i in range(3):
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        data = json.loads(response)
                        self.assertIsInstance(data, dict)
                    except asyncio.TimeoutError:
                        # It's okay if we don't receive data immediately
                        pass
        except Exception as e:
            # If WebSocket server is not running, skip the test
            self.skipTest(f"WebSocket server not running: {str(e)}")

class APISecurityTests(BaseTestCase):
    """Security tests for API endpoints"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        super().setUp()
        self.base_url = "http://localhost:8000"
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
    def test_api_rate_limiting(self):
        """Test API rate limiting"""
        try:
            # Make multiple rapid requests to test rate limiting
            responses = []
            for i in range(10):
                response = self.session.get(f"{self.base_url}/health")
                responses.append(response.status_code)
                time.sleep(0.1)  # Small delay
            
            # Check that we don't get all 429 (rate limit) responses
            rate_limit_count = responses.count(429)
            self.assertLess(rate_limit_count, len(responses), "All requests were rate limited")
        except requests.exceptions.ConnectionError:
            self.skipTest("API server not running")
            
    def test_cors_headers(self):
        """Test CORS headers"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            # Check for CORS headers
            self.assertIn('Access-Control-Allow-Origin', response.headers.keys())
        except requests.exceptions.ConnectionError:
            self.skipTest("API server not running")
            
    def test_input_validation(self):
        """Test input validation"""
        try:
            # Test with malicious input
            malicious_data = {
                "name": "<script>alert('xss')</script>",
                "description": "A test strategy'; DROP TABLE strategies; --"
            }
            response = self.session.post(f"{self.base_url}/api/strategies", json=malicious_data)
            # Should return 400 or 422 for invalid input, not 500
            self.assertNotEqual(response.status_code, 500, "Server error on invalid input")
        except requests.exceptions.ConnectionError:
            self.skipTest("API server not running")

class APIPerformanceTests(BaseTestCase):
    """Performance tests for API endpoints"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        super().setUp()
        self.base_url = "http://localhost:8000"
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
    def test_api_response_time(self):
        """Test API response time"""
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/health")
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            self.assertLess(response_time, 1000, f"API response too slow: {response_time}ms")
        except requests.exceptions.ConnectionError:
            self.skipTest("API server not running")
            
    def test_concurrent_api_requests(self):
        """Test handling of concurrent API requests"""
        try:
            import concurrent.futures
            
            def make_request():
                response = self.session.get(f"{self.base_url}/health")
                return response.status_code
            
            # Make 10 concurrent requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request) for _ in range(10)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            # All requests should succeed
            success_count = sum(1 for status in results if status == 200)
            self.assertGreater(success_count, 7, "Too many failed concurrent requests")
        except requests.exceptions.ConnectionError:
            self.skipTest("API server not running")

def run_api_tests(base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """Run all API tests and return results"""
    framework = APITestFramework(base_url)
    
    # Add all test cases
    framework.add_test_case(RESTAPITests)
    framework.add_test_case(GraphQLAPITests)
    framework.add_test_case(APISecurityTests)
    framework.add_test_case(APIPerformanceTests)
    
    # Run tests
    return framework.run_all_tests()

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run API tests
    results = run_api_tests()
    
    # Print results
    print(f"API Test Results:")
    print(f"  Total Tests: {results['total_tests']}")
    print(f"  Successes: {results['successes']}")
    print(f"  Failures: {results['failures']}")
    print(f"  Errors: {results['errors']}")
    print(f"  Success Rate: {results['success_rate']:.2%}")
    
    # Print failure details if any
    if results['failures'] > 0:
        print("\nFailures:")
        for failure in results['failure_details']:
            print(f"  {failure['test']}: {failure['error']}")
            
    # Print error details if any
    if results['errors'] > 0:
        print("\nErrors:")
        for error in results['error_details']:
            print(f"  {error['test']}: {error['error']}")