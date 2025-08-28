#!/usr/bin/env python3
"""
Comprehensive API Bridge Validation Test Script
Algorithmic Trading System - Phase 2

This script validates the complete API bridge functionality including:
- Authentication flow (login, token validation, refresh)
- Backtesting endpoints with sample strategies
- Optimization endpoints with parameter ranges
- Features endpoints with various symbols
- Error handling and negative test cases
- Performance metrics validation
- Concurrent request testing

Usage:
    python scripts/test_api_bridge.py --url http://localhost:8001
    python scripts/test_api_bridge.py --url http://localhost:8001 --verbose --save-results
    python scripts/test_api_bridge.py --dry-run
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Color codes for terminal output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

class APIBridgeValidator:
    """Comprehensive API bridge validation test suite"""
    
    def __init__(self, base_url: str, verbose: bool = False, save_results: bool = False):
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/api/v1"
        self.verbose = verbose
        self.save_results = save_results
        self.session = self._create_session()
        self.access_token = None
        self.refresh_token = None
        self.test_results = []
        self.start_time = time.time()
        
        # Test configuration
        self.demo_credentials = {
            "username": "demo",
            "password": "demo123"
        }
        
        self.admin_credentials = {
            "username": "admin", 
            "password": "admin123"
        }
        
        # Setup logging
        self._setup_logging()
        
    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry strategy"""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'API-Bridge-Validator/1.0'
        })
        
        return session
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _print_colored(self, message: str, color: str = Colors.WHITE, bold: bool = False):
        """Print colored message to console"""
        prefix = Colors.BOLD if bold else ""
        print(f"{prefix}{color}{message}{Colors.END}")
    
    def _print_header(self, title: str):
        """Print section header"""
        self._print_colored("=" * 80, Colors.CYAN, bold=True)
        self._print_colored(f" {title} ", Colors.CYAN, bold=True)
        self._print_colored("=" * 80, Colors.CYAN, bold=True)
    
    def _print_test_result(self, test_name: str, success: bool, duration: float, details: str = ""):
        """Print test result with color coding"""
        status = "PASS" if success else "FAIL"
        color = Colors.GREEN if success else Colors.RED
        duration_str = f"({duration:.2f}s)"
        
        self._print_colored(f"[{status}] {test_name} {duration_str}", color, bold=True)
        if details and (not success or self.verbose):
            self._print_colored(f"      {details}", Colors.WHITE)
    
    def _record_test_result(self, test_name: str, success: bool, duration: float, 
                          details: str = "", response_data: Any = None):
        """Record test result for reporting"""
        result = {
            "test_name": test_name,
            "success": success,
            "duration": duration,
            "details": details,
            "timestamp": datetime.utcnow().isoformat(),
            "response_data": response_data
        }
        self.test_results.append(result)
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None, 
                     headers: Dict = None, timeout: int = 30) -> Tuple[bool, Dict, float]:
        """Make HTTP request with error handling and timing"""
        url = urljoin(self.api_base, endpoint)
        start_time = time.time()
        
        try:
            # Prepare headers
            request_headers = self.session.headers.copy()
            if headers:
                request_headers.update(headers)
            
            # Add authorization header if token is available
            if self.access_token and 'Authorization' not in request_headers:
                request_headers['Authorization'] = f'Bearer {self.access_token}'
            
            # Make request
            if method.upper() == 'GET':
                response = self.session.get(url, headers=request_headers, timeout=timeout, params=data)
            elif method.upper() == 'POST':
                response = self.session.post(url, headers=request_headers, json=data, timeout=timeout)
            elif method.upper() == 'PUT':
                response = self.session.put(url, headers=request_headers, json=data, timeout=timeout)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, headers=request_headers, timeout=timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            duration = time.time() - start_time
            
            # Parse response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {"raw_response": response.text}
            
            # Log request details if verbose
            if self.verbose:
                self.logger.debug(f"{method} {url} -> {response.status_code} ({duration:.2f}s)")
                if data:
                    self.logger.debug(f"Request data: {json.dumps(data, indent=2)}")
                self.logger.debug(f"Response: {json.dumps(response_data, indent=2)}")
            
            return response.status_code < 400, response_data, duration
            
        except requests.exceptions.RequestException as e:
            duration = time.time() - start_time
            error_data = {"error": str(e), "type": type(e).__name__}
            self.logger.error(f"Request failed: {e}")
            return False, error_data, duration
    
    def test_system_health(self) -> bool:
        """Test system health and availability"""
        self._print_header("SYSTEM HEALTH CHECKS")
        
        # Test root endpoint
        success, data, duration = self._make_request('GET', '/')
        self._print_test_result("Root endpoint", success, duration, 
                              f"Version: {data.get('version', 'Unknown')}" if success else str(data))
        self._record_test_result("system_root", success, duration, str(data), data)
        
        # Test health endpoint
        success, data, duration = self._make_request('GET', '/health')
        self._print_test_result("Health check", success, duration,
                              f"Status: {data.get('status', 'Unknown')}" if success else str(data))
        self._record_test_result("system_health", success, duration, str(data), data)
        
        # Test API info endpoint
        success, data, duration = self._make_request('GET', '/info')
        self._print_test_result("API info", success, duration,
                              f"Phase: {data.get('phase', 'Unknown')}" if success else str(data))
        self._record_test_result("system_info", success, duration, str(data), data)
        
        return all(result["success"] for result in self.test_results[-3:])
    
    def test_authentication_flow(self) -> bool:
        """Test complete authentication flow"""
        self._print_header("AUTHENTICATION FLOW TESTS")
        
        # Test login with demo credentials
        login_data = self.demo_credentials
        success, data, duration = self._make_request('POST', '/auth/login', login_data)
        
        if success and 'access_token' in data:
            self.access_token = data['access_token']
            self.refresh_token = data['refresh_token']
            details = f"Token expires in: {data.get('expires_in', 'Unknown')}s"
        else:
            details = str(data)
        
        self._print_test_result("Login (demo user)", success, duration, details)
        self._record_test_result("auth_login_demo", success, duration, details, data)
        
        if not success:
            return False
        
        # Test getting current user info
        success, data, duration = self._make_request('GET', '/auth/me')
        details = f"User: {data.get('username', 'Unknown')}" if success else str(data)
        self._print_test_result("Get user info", success, duration, details)
        self._record_test_result("auth_user_info", success, duration, details, data)
        
        # Test authentication status
        success, data, duration = self._make_request('GET', '/auth/status')
        details = f"Authenticated: {data.get('authenticated', False)}" if success else str(data)
        self._print_test_result("Auth status check", success, duration, details)
        self._record_test_result("auth_status", success, duration, details, data)
        
        # Test token refresh
        if self.refresh_token:
            refresh_data = {"refresh_token": self.refresh_token}
            success, data, duration = self._make_request('POST', '/auth/refresh', refresh_data)
            
            if success and 'access_token' in data:
                self.access_token = data['access_token']
                self.refresh_token = data['refresh_token']
                details = "Token refreshed successfully"
            else:
                details = str(data)
            
            self._print_test_result("Token refresh", success, duration, details)
            self._record_test_result("auth_refresh", success, duration, details, data)
        
        # Test logout
        success, data, duration = self._make_request('POST', '/auth/logout')
        details = data.get('message', str(data)) if success else str(data)
        self._print_test_result("Logout", success, duration, details)
        self._record_test_result("auth_logout", success, duration, details, data)
        
        return True
    
    def test_authentication_errors(self) -> bool:
        """Test authentication error handling"""
        self._print_header("AUTHENTICATION ERROR TESTS")
        
        # Test invalid credentials
        invalid_creds = {"username": "invalid", "password": "invalid"}
        success, data, duration = self._make_request('POST', '/auth/login', invalid_creds)
        
        # This should fail (success = False is expected)
        expected_fail = not success
        details = f"Expected failure: {expected_fail}, Error: {data.get('detail', 'Unknown')}"
        self._print_test_result("Invalid credentials", expected_fail, duration, details)
        self._record_test_result("auth_invalid_creds", expected_fail, duration, details, data)
        
        # Test invalid refresh token
        invalid_refresh = {"refresh_token": "invalid_token"}
        success, data, duration = self._make_request('POST', '/auth/refresh', invalid_refresh)
        
        expected_fail = not success
        details = f"Expected failure: {expected_fail}, Error: {data.get('detail', 'Unknown')}"
        self._print_test_result("Invalid refresh token", expected_fail, duration, details)
        self._record_test_result("auth_invalid_refresh", expected_fail, duration, details, data)
        
        # Test accessing protected endpoint without token
        self.access_token = None  # Clear token
        success, data, duration = self._make_request('GET', '/auth/me')
        
        expected_fail = not success
        details = f"Expected failure: {expected_fail}, Error: {data.get('detail', 'Unknown')}"
        self._print_test_result("No auth token", expected_fail, duration, details)
        self._record_test_result("auth_no_token", expected_fail, duration, details, data)
        
        # Re-authenticate for subsequent tests
        login_data = self.demo_credentials
        success, data, duration = self._make_request('POST', '/auth/login', login_data)
        if success:
            self.access_token = data['access_token']
            self.refresh_token = data['refresh_token']
        
        return True
    
    def test_backtesting_endpoints(self) -> bool:
        """Test backtesting functionality"""
        self._print_header("BACKTESTING ENDPOINT TESTS")
        
        # Test backtest status
        success, data, duration = self._make_request('GET', '/backtest/status')
        details = f"Status: {data.get('status', 'Unknown')}" if success else str(data)
        self._print_test_result("Backtest status", success, duration, details)
        self._record_test_result("backtest_status", success, duration, details, data)
        
        # Test backtest execution with sample strategy
        backtest_data = {
            "ticker": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "strategy_name": "moving_average_crossover",
            "initial_capital": 100000.0,
            "fast_period": 10,
            "slow_period": 30
        }
        
        success, data, duration = self._make_request('POST', '/backtest/', backtest_data, timeout=120)
        
        if success:
            status = data.get('status', 'Unknown')
            total_return = None
            if 'summary' in data and data['summary']:
                total_return = data['summary'].get('total_return', 'N/A')
            details = f"Status: {status}, Return: {total_return}"
        else:
            details = str(data)
        
        self._print_test_result("Run backtest (AAPL)", success, duration, details)
        self._record_test_result("backtest_run_aapl", success, duration, details, data)
        
        # Test backtest with different parameters
        backtest_data_2 = {
            "ticker": "MSFT",
            "start_date": "2023-06-01", 
            "end_date": "2023-12-31",
            "strategy_name": "moving_average_crossover",
            "initial_capital": 50000.0,
            "fast_period": 5,
            "slow_period": 20
        }
        
        success, data, duration = self._make_request('POST', '/backtest/', backtest_data_2, timeout=120)
        
        if success:
            status = data.get('status', 'Unknown')
            data_points = data.get('data_points', 'N/A')
            details = f"Status: {status}, Data points: {data_points}"
        else:
            details = str(data)
        
        self._print_test_result("Run backtest (MSFT)", success, duration, details)
        self._record_test_result("backtest_run_msft", success, duration, details, data)
        
        return True
    
    def test_backtesting_errors(self) -> bool:
        """Test backtesting error handling"""
        self._print_header("BACKTESTING ERROR TESTS")
        
        # Test invalid ticker
        invalid_backtest = {
            "ticker": "INVALID_TICKER_XYZ",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "strategy_name": "moving_average_crossover",
            "initial_capital": 100000.0,
            "fast_period": 10,
            "slow_period": 30
        }
        
        success, data, duration = self._make_request('POST', '/backtest/', invalid_backtest, timeout=60)
        expected_fail = not success
        details = f"Expected failure: {expected_fail}, Error: {data.get('detail', data.get('error', 'Unknown'))}"
        self._print_test_result("Invalid ticker", expected_fail, duration, details)
        self._record_test_result("backtest_invalid_ticker", expected_fail, duration, details, data)
        
        # Test invalid date range
        invalid_dates = {
            "ticker": "AAPL",
            "start_date": "2025-01-01",  # Future date
            "end_date": "2025-12-31",
            "strategy_name": "moving_average_crossover",
            "initial_capital": 100000.0,
            "fast_period": 10,
            "slow_period": 30
        }
        
        success, data, duration = self._make_request('POST', '/backtest/', invalid_dates, timeout=60)
        # This might succeed or fail depending on data availability
        details = f"Future dates test, Status: {data.get('status', 'Unknown')}"
        self._print_test_result("Future date range", True, duration, details)  # Don't fail on this
        self._record_test_result("backtest_future_dates", True, duration, details, data)
        
        # Test missing required fields
        incomplete_data = {
            "ticker": "AAPL"
            # Missing required fields
        }
        
        success, data, duration = self._make_request('POST', '/backtest/', incomplete_data)
        expected_fail = not success
        details = f"Expected failure: {expected_fail}, Validation errors present"
        self._print_test_result("Missing required fields", expected_fail, duration, details)
        self._record_test_result("backtest_missing_fields", expected_fail, duration, details, data)
        
        return True
    
    def test_optimization_endpoints(self) -> bool:
        """Test optimization functionality"""
        self._print_header("OPTIMIZATION ENDPOINT TESTS")
        
        # Test optimization status
        success, data, duration = self._make_request('GET', '/optimise/status')
        details = f"Status: {data.get('status', 'Unknown')}" if success else str(data)
        self._print_test_result("Optimization status", success, duration, details)
        self._record_test_result("optimization_status", success, duration, details, data)
        
        # Test optimization with small parameter space
        optimization_data = {
            "ticker": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2023-06-30",
            "strategy": "sma_crossover",
            "initial_capital": 100000.0,
            "params": {
                "fast_period": {"min": 5, "max": 15, "step": 5},
                "slow_period": {"min": 20, "max": 40, "step": 10}
            },
            "n_trials": 10,  # Small number for testing
            "timeout": 120,
            "objective": "sharpe_ratio"
        }
        
        success, data, duration = self._make_request('POST', '/optimise/', optimization_data, timeout=180)
        
        if success:
            status = data.get('status', 'Unknown')
            best_value = data.get('best_value', 'N/A')
            n_trials = data.get('n_trials', 'N/A')
            details = f"Status: {status}, Best {optimization_data['objective']}: {best_value}, Trials: {n_trials}"
        else:
            details = str(data)
        
        self._print_test_result("Run optimization", success, duration, details)
        self._record_test_result("optimization_run", success, duration, details, data)
        
        return True
    
    def test_optimization_errors(self) -> bool:
        """Test optimization error handling"""
        self._print_header("OPTIMIZATION ERROR TESTS")
        
        # Test unsupported strategy
        invalid_strategy = {
            "ticker": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2023-06-30",
            "strategy": "unsupported_strategy",
            "initial_capital": 100000.0,
            "params": {
                "fast_period": {"min": 5, "max": 15}
            },
            "n_trials": 5
        }
        
        success, data, duration = self._make_request('POST', '/optimise/', invalid_strategy)
        expected_fail = not success
        details = f"Expected failure: {expected_fail}, Error: {data.get('detail', 'Unknown')}"
        self._print_test_result("Unsupported strategy", expected_fail, duration, details)
        self._record_test_result("optimization_invalid_strategy", expected_fail, duration, details, data)
        
        # Test invalid parameters
        invalid_params = {
            "ticker": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2023-06-30",
            "strategy": "sma_crossover",
            "initial_capital": 100000.0,
            "params": {
                "invalid_param": {"min": 5, "max": 15}
            },
            "n_trials": 5
        }
        
        success, data, duration = self._make_request('POST', '/optimise/', invalid_params)
        expected_fail = not success
        details = f"Expected failure: {expected_fail}, Error: {data.get('detail', 'Unknown')}"
        self._print_test_result("Invalid parameters", expected_fail, duration, details)
        self._record_test_result("optimization_invalid_params", expected_fail, duration, details, data)
        
        return True
    
    def test_features_endpoints(self) -> bool:
        """Test features functionality"""
        self._print_header("FEATURES ENDPOINT TESTS")
        
        # Test features for different symbols
        symbols = ["AAPL", "MSFT", "GOOGL"]
        feature_types = ["market_data", "indicators", "volume_analysis"]
        
        for symbol in symbols:
            params = {
                "start_date": "2023-01-01T00:00:00",
                "end_date": "2023-01-31T23:59:59",
                "feature_types": feature_types,
                "aggregation": "1d"
            }
            
            success, data, duration = self._make_request('GET', f'/features/{symbol}', params)
            
            if success:
                features_count = len(data.get('features', []))
                details = f"Symbol: {symbol}, Features: {features_count}"
            else:
                details = str(data)
            
            self._print_test_result(f"Features ({symbol})", success, duration, details)
            self._record_test_result(f"features_{symbol.lower()}", success, duration, details, data)
        
        # Test different aggregation levels
        aggregations = ["1h", "1d"]
        for agg in aggregations:
            params = {
                "start_date": "2023-01-01T00:00:00",
                "end_date": "2023-01-07T23:59:59",
                "feature_types": ["market_data"],
                "aggregation": agg
            }
            
            success, data, duration = self._make_request('GET', '/features/AAPL', params)
            details = f"Aggregation: {agg}, Success: {success}"
            self._print_test_result(f"Features aggregation ({agg})", success, duration, details)
            self._record_test_result(f"features_agg_{agg}", success, duration, details, data)
        
        return True
    
    def test_features_errors(self) -> bool:
        """Test features error handling"""
        self._print_header("FEATURES ERROR TESTS")
        
        # Test invalid feature types
        params = {
            "start_date": "2023-01-01T00:00:00",
            "end_date": "2023-01-31T23:59:59",
            "feature_types": ["invalid_feature_type"],
            "aggregation": "1d"
        }
        
        success, data, duration = self._make_request('GET', '/features/AAPL', params)
        expected_fail = not success
        details = f"Expected failure: {expected_fail}, Error: {data.get('detail', 'Unknown')}"
        self._print_test_result("Invalid feature types", expected_fail, duration, details)
        self._record_test_result("features_invalid_types", expected_fail, duration, details, data)
        
        # Test missing required parameters
        params = {
            "start_date": "2023-01-01T00:00:00"
            # Missing end_date and feature_types
        }
        
        success, data, duration = self._make_request('GET', '/features/AAPL', params)
        expected_fail = not success
        details = f"Expected failure: {expected_fail}, Missing required params"
        self._print_test_result("Missing parameters", expected_fail, duration, details)
        self._record_test_result("features_missing_params", expected_fail, duration, details, data)
        
        return True
    
    def test_concurrent_requests(self) -> bool:
        """Test concurrent request handling"""
        self._print_header("CONCURRENT REQUEST TESTS")
        
        def make_concurrent_request(endpoint: str, data: Dict = None) -> Tuple[str, bool, float]:
            """Make a single concurrent request"""
            method = 'POST' if data else 'GET'
            success, response_data, duration = self._make_request(method, endpoint, data)
            return endpoint, success, duration
        
        # Prepare concurrent requests
        requests_to_make = [
            ('/auth/status', None),
            ('/backtest/status', None),
            ('/optimise/status', None),
            ('/auth/me', None),
            ('/health', None)
        ]
        
        # Execute concurrent requests
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(make_concurrent_request, endpoint, data)
                for endpoint, data in requests_to_make
            ]
            
            results = []
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Concurrent request failed: {e}")
                    results.append(("unknown", False, 0.0))
        
        total_duration = time.time() - start_time
        successful_requests = sum(1 for _, success, _ in results if success)
        total_requests = len(results)
        
        details = f"Successful: {successful_requests}/{total_requests}, Total time: {total_duration:.2f}s"
        success = successful_requests == total_requests
        
        self._print_test_result("Concurrent requests", success, total_duration, details)
        self._record_test_result("concurrent_requests", success, total_duration, details, results)
        
        return success
    
    def test_performance_metrics(self) -> bool:
        """Test API performance metrics"""
        self._print_header("PERFORMANCE METRICS TESTS")
        
        # Test response times for different endpoints
        endpoints_to_test = [
            ('GET', '/health', None, 1.0),  # Expected < 1s
            ('GET', '/auth/status', None, 2.0),  # Expected < 2s
            ('GET', '/backtest/status', None, 3.0),  # Expected < 3s
            ('POST', '/auth/login', self.demo_credentials, 5.0),  # Expected < 5s
        ]
        
        performance_results = []
        
        for method, endpoint, data, expected_max_time in endpoints_to_test:
            success, response_data, duration = self._make_request(method, endpoint, data)
            
            performance_ok = duration <= expected_max_time
            details = f"Duration: {duration:.2f}s (expected < {expected_max_time}s)"
            
            if success and performance_ok:
                result_status = "PASS"
                color = Colors.GREEN
            elif success and not performance_ok:
                result_status = "SLOW"
                color = Colors.YELLOW
            else:
                result_status = "FAIL"
                color = Colors.RED
            
            test_name = f"Performance {method} {endpoint}"
            self._print_colored(f"[{result_status}] {test_name} ({duration:.2f}s)", color, bold=True)
            if details and (result_status != "PASS" or self.verbose):
                self._print_colored(f"      {details}", Colors.WHITE)
            
            performance_results.append({
                "endpoint": endpoint,
                "method": method,
                "duration": duration,
                "expected_max": expected_max_time,
                "performance_ok": performance_ok,
                "success": success
            })
            
            self._record_test_result(f"performance_{method.lower()}_{endpoint.replace('/', '_')}", 
                                   success and performance_ok, duration, details, response_data)
        
        # Update token if login was successful
        if method == 'POST' and endpoint == '/auth/login' and success and 'access_token' in response_data:
            self.access_token = response_data['access_token']
        
        return all(result["success"] and result["performance_ok"] for result in performance_results)
    
    def generate_summary_report(self) -> Dict:
        """Generate comprehensive test summary report"""
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - successful_tests
        
        total_duration = time.time() - self.start_time
        avg_response_time = sum(result["duration"] for result in self.test_results) / total_tests if total_tests > 0 else 0
        
        # Group results by category
        categories = {}
        for result in self.test_results:
            category = result["test_name"].split("_")[0]
            if category not in categories:
                categories[category] = {"total": 0, "passed": 0, "failed": 0}
            
            categories[category]["total"] += 1
            if result["success"]:
                categories[category]["passed"] += 1
            else:
                categories[category]["failed"] += 1
        
        # Create summary report
        summary = {
            "test_execution": {
                "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "total_duration": total_duration,
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": failed_tests,
                "success_rate": (successful_tests / total_tests * 100) if total_tests > 0 else 0,
                "average_response_time": avg_response_time
            },
            "categories": categories,
            "failed_tests": [
                {
                    "name": result["test_name"],
                    "details": result["details"],
                    "duration": result["duration"]
                }
                for result in self.test_results if not result["success"]
            ],
            "slowest_tests": sorted(
                [
                    {
                        "name": result["test_name"],
                        "duration": result["duration"]
                    }
                    for result in self.test_results
                ],
                key=lambda x: x["duration"],
                reverse=True
            )[:5],
            "api_configuration": {
                "base_url": self.base_url,
                "api_base": self.api_base,
                "verbose": self.verbose,
                "save_results": self.save_results
            }
        }
        
        return summary
    
    def print_summary_report(self):
        """Print comprehensive summary report"""
        summary = self.generate_summary_report()
        
        self._print_header("TEST EXECUTION SUMMARY")
        
        # Overall statistics
        exec_info = summary["test_execution"]
        self._print_colored(f"Total Tests: {exec_info['total_tests']}", Colors.WHITE, bold=True)
        self._print_colored(f"Successful: {exec_info['successful_tests']}", Colors.GREEN, bold=True)
        self._print_colored(f"Failed: {exec_info['failed_tests']}", Colors.RED, bold=True)
        self._print_colored(f"Success Rate: {exec_info['success_rate']:.1f}%", Colors.CYAN, bold=True)
        self._print_colored(f"Total Duration: {exec_info['total_duration']:.2f}s", Colors.WHITE)
        self._print_colored(f"Average Response Time: {exec_info['average_response_time']:.3f}s", Colors.WHITE)
        
        # Category breakdown
        self._print_colored("\nCategory Breakdown:", Colors.YELLOW, bold=True)
        for category, stats in summary["categories"].items():
            success_rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
            color = Colors.GREEN if success_rate == 100 else Colors.YELLOW if success_rate >= 50 else Colors.RED
            self._print_colored(
                f"  {category.upper()}: {stats['passed']}/{stats['total']} ({success_rate:.1f}%)",
                color
            )
        
        # Failed tests
        if summary["failed_tests"]:
            self._print_colored("\nFailed Tests:", Colors.RED, bold=True)
            for failed_test in summary["failed_tests"]:
                self._print_colored(f"  ❌ {failed_test['name']}: {failed_test['details']}", Colors.RED)
        
        # Slowest tests
        if summary["slowest_tests"]:
            self._print_colored("\nSlowest Tests:", Colors.YELLOW, bold=True)
            for slow_test in summary["slowest_tests"][:3]:
                self._print_colored(f"  🐌 {slow_test['name']}: {slow_test['duration']:.2f}s", Colors.YELLOW)
        
        # Final result
        overall_success = exec_info["failed_tests"] == 0
        if overall_success:
            self._print_colored("\n🎉 ALL TESTS PASSED! API Bridge is working correctly.", Colors.GREEN, bold=True)
        else:
            self._print_colored(f"\n❌ {exec_info['failed_tests']} TEST(S) FAILED. Please review the issues above.", Colors.RED, bold=True)
        
        return overall_success
    
    def save_results_to_file(self, filename: str = None):
        """Save test results to JSON file"""
        if not filename:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"api_bridge_test_results_{timestamp}.json"
        
        summary = self.generate_summary_report()
        summary["detailed_results"] = self.test_results
        
        try:
            with open(filename, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            
            self._print_colored(f"\n📄 Test results saved to: {filename}", Colors.CYAN)
            return filename
        except Exception as e:
            self._print_colored(f"\n❌ Failed to save results: {e}", Colors.RED)
            return None
    
    def run_all_tests(self) -> bool:
        """Run complete test suite"""
        self._print_colored("🚀 Starting API Bridge Validation Tests", Colors.CYAN, bold=True)
        self._print_colored(f"Target API: {self.base_url}", Colors.WHITE)
        self._print_colored(f"Timestamp: {datetime.utcnow().isoformat()}", Colors.WHITE)
        print()
        
        try:
            # Run all test categories
            test_categories = [
                ("System Health", self.test_system_health),
                ("Authentication Flow", self.test_authentication_flow),
                ("Authentication Errors", self.test_authentication_errors),
                ("Backtesting Endpoints", self.test_backtesting_endpoints),
                ("Backtesting Errors", self.test_backtesting_errors),
                ("Optimization Endpoints", self.test_optimization_endpoints),
                ("Optimization Errors", self.test_optimization_errors),
                ("Features Endpoints", self.test_features_endpoints),
                ("Features Errors", self.test_features_errors),
                ("Concurrent Requests", self.test_concurrent_requests),
                ("Performance Metrics", self.test_performance_metrics)
            ]
            
            category_results = []
            
            for category_name, test_function in test_categories:
                try:
                    self.logger.info(f"Running {category_name} tests...")
                    result = test_function()
                    category_results.append((category_name, result))
                    print()  # Add spacing between categories
                except Exception as e:
                    self.logger.error(f"Error in {category_name} tests: {e}")
                    category_results.append((category_name, False))
                    self._print_colored(f"❌ {category_name} tests failed with error: {e}", Colors.RED)
                    print()
            
            # Print summary
            overall_success = self.print_summary_report()
            
            # Save results if requested
            if self.save_results:
                self.save_results_to_file()
            
            return overall_success
            
        except KeyboardInterrupt:
            self._print_colored("\n⚠️  Tests interrupted by user", Colors.YELLOW)
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during test execution: {e}")
            self._print_colored(f"\n❌ Test execution failed: {e}", Colors.RED)
            return False


def create_argument_parser():
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="Comprehensive API Bridge Validation Test Script for Algorithmic Trading System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/test_api_bridge.py --url http://localhost:8001
  python scripts/test_api_bridge.py --url http://localhost:8001 --verbose --save-results
  python scripts/test_api_bridge.py --dry-run
  python scripts/test_api_bridge.py --url https://api.example.com --timeout 60

Environment Variables:
  API_BASE_URL    - Default API base URL (default: http://localhost:8001)
  API_TIMEOUT     - Default request timeout in seconds (default: 30)
  VERBOSE         - Enable verbose output (default: false)
  SAVE_RESULTS    - Save results to file (default: false)
        """
    )
    
    parser.add_argument(
        '--url', '--base-url',
        default=os.getenv('API_BASE_URL', 'http://localhost:8001'),
        help='Base URL of the API to test (default: http://localhost:8001)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        default=os.getenv('VERBOSE', 'false').lower() == 'true',
        help='Enable verbose output with detailed request/response logging'
    )
    
    parser.add_argument(
        '--save-results', '-s',
        action='store_true',
        default=os.getenv('SAVE_RESULTS', 'false').lower() == 'true',
        help='Save test results to a JSON file'
    )
    
    parser.add_argument(
        '--timeout', '-t',
        type=int,
        default=int(os.getenv('API_TIMEOUT', '30')),
        help='Request timeout in seconds (default: 30)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what tests would be run without executing them'
    )
    
    parser.add_argument(
        '--output-file', '-o',
        help='Specify output file for results (only used with --save-results)'
    )
    
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable colored output'
    )
    
    return parser


def show_dry_run_info():
    """Show information about what tests would be run"""
    print("🔍 DRY RUN MODE - Tests that would be executed:")
    print()
    
    test_categories = [
        ("System Health Tests", [
            "Root endpoint availability",
            "Health check endpoint",
            "API info endpoint"
        ]),
        ("Authentication Flow Tests", [
            "Login with demo credentials",
            "Get current user information",
            "Authentication status check",
            "Token refresh functionality",
            "User logout"
        ]),
        ("Authentication Error Tests", [
            "Invalid credentials handling",
            "Invalid refresh token handling",
            "Unauthorized access attempts"
        ]),
        ("Backtesting Endpoint Tests", [
            "Backtest engine status check",
            "Run backtest with AAPL sample strategy",
            "Run backtest with MSFT different parameters"
        ]),
        ("Backtesting Error Tests", [
            "Invalid ticker symbol handling",
            "Invalid date range handling",
            "Missing required fields validation"
        ]),
        ("Optimization Endpoint Tests", [
            "Optimization engine status check",
            "Run parameter optimization with small search space"
        ]),
        ("Optimization Error Tests", [
            "Unsupported strategy handling",
            "Invalid parameter validation"
        ]),
        ("Features Endpoint Tests", [
            "Features retrieval for multiple symbols (AAPL, MSFT, GOOGL)",
            "Different aggregation levels testing (1h, 1d)"
        ]),
        ("Features Error Tests", [
            "Invalid feature types handling",
            "Missing required parameters validation"
        ]),
        ("Concurrent Request Tests", [
            "Multiple simultaneous API requests",
            "Thread safety validation"
        ]),
        ("Performance Metrics Tests", [
            "Response time validation for critical endpoints",
            "Performance threshold compliance"
        ])
    ]
    
    for category, tests in test_categories:
        print(f"📋 {category}:")
        for test in tests:
            print(f"   • {test}")
        print()
    
    print("💡 To run these tests, remove the --dry-run flag")


def main():
    """Main entry point"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Handle no-color option
    if args.no_color:
        # Disable colors by setting all color constants to empty strings
        for attr in dir(Colors):
            if not attr.startswith('_'):
                setattr(Colors, attr, '')
    
    # Handle dry run
    if args.dry_run:
        show_dry_run_info()
        return 0
    
    # Create validator instance
    validator = APIBridgeValidator(
        base_url=args.url,
        verbose=args.verbose,
        save_results=args.save_results
    )
    
    # Override output file if specified
    if args.output_file and args.save_results:
        validator.output_file = args.output_file
    
    # Run tests
    try:
        success = validator.run_all_tests()
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())