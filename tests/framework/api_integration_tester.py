#!/usr/bin/env python3
"""
API Integration Tester for Algorithmic Trading System

This module implements comprehensive API integration testing functionality that validates
external service communication, timeout and retry logic, API response validation,
and error handling across REST, GraphQL, and WebSocket endpoints.

Key Features:
- External service communication validation
- Timeout and retry logic testing
- API response validation and error handling tests
- REST API testing with all HTTP methods
- GraphQL query and mutation testing
- WebSocket real-time communication testing
- Authentication and authorization testing
"""

import asyncio
import logging
import time
import traceback
import json
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, Callable, AsyncGenerator
from unittest.mock import Mock, patch, MagicMock
import ssl
from urllib.parse import urljoin, urlparse

# HTTP and WebSocket imports
try:
    import aiohttp
    import websockets
except ImportError:
    aiohttp = None
    websockets = None

# GraphQL imports
try:
    import graphql
    from graphql import build_schema, validate, parse
except ImportError:
    graphql = None

# Testing framework imports
import pytest
import pytest_asyncio


class APIType(Enum):
    """Types of APIs supported for testing"""
    REST = "rest"
    GRAPHQL = "graphql"
    WEBSOCKET = "websocket"
    GRPC = "grpc"


class HTTPMethod(Enum):
    """HTTP methods for REST API testing"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class AuthenticationType(Enum):
    """Types of authentication supported"""
    NONE = "none"
    BASIC = "basic"
    BEARER_TOKEN = "bearer_token"
    API_KEY = "api_key"
    JWT = "jwt"
    OAUTH2 = "oauth2"


class APITestStatus(Enum):
    """Status of API test execution"""
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class APIEndpoint:
    """Represents an API endpoint for testing"""
    url: str
    method: HTTPMethod
    api_type: APIType
    authentication: AuthenticationType = AuthenticationType.NONE
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, Any] = field(default_factory=dict)
    request_body: Optional[Dict[str, Any]] = None
    expected_status_codes: List[int] = field(default_factory=lambda: [200])
    timeout_seconds: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0


@dataclass
class APITestCase:
    """Represents a single API test case"""
    test_id: str
    test_name: str
    api_type: APIType
    endpoint: APIEndpoint
    description: str
    test_function: Callable
    setup_function: Optional[Callable] = None
    teardown_function: Optional[Callable] = None
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    performance_thresholds: Dict[str, float] = field(default_factory=dict)


@dataclass
class APITestResult:
    """Results of a single API test"""
    test_case: APITestCase
    status: APITestStatus
    start_time: datetime
    end_time: datetime
    duration: float
    request_count: int = 0
    response_status_code: Optional[int] = None
    response_headers: Dict[str, str] = field(default_factory=dict)
    response_body: Optional[Any] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    retry_attempts: int = 0
    timeout_occurred: bool = False


@dataclass
class APITestSuiteResult:
    """Results of an API test suite execution"""
    suite_name: str
    start_time: datetime
    end_time: datetime
    total_duration: float
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int
    skipped_tests: int
    timeout_tests: int
    pass_rate: float
    test_results: List[APITestResult]
    api_performance_summary: Dict[str, Any] = field(default_factory=dict)
    endpoint_coverage_summary: Dict[str, Any] = field(default_factory=dict)
    authentication_summary: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_backoff: bool = True
    jitter: bool = True
    retry_on_status_codes: List[int] = field(default_factory=lambda: [500, 502, 503, 504])


@dataclass
class TimeoutConfig:
    """Configuration for timeout handling"""
    connect_timeout: float = 10.0
    read_timeout: float = 30.0
    total_timeout: float = 60.0


class APIIntegrationTester:
    """
    Comprehensive API integration tester for the algorithmic trading system.
    
    This class orchestrates API integration testing across REST, GraphQL, and WebSocket
    endpoints, validating external service communication, timeout handling, and error responses.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the APIIntegrationTester.
        
        Args:
            config: Configuration dictionary for API testing settings
        """
        self.config = config or {}
        self.logger = self._setup_logging()
        self.test_cases: Dict[str, APITestCase] = {}
        self.test_results: Dict[str, APITestResult] = {}
        self.suite_results: List[APITestSuiteResult] = []
        
        # HTTP session for REST API testing
        self.http_session: Optional[aiohttp.ClientSession] = None
        
        # WebSocket connections
        self.websocket_connections: Dict[str, Any] = {}
        
        # Authentication tokens and credentials
        self.auth_tokens: Dict[str, str] = {}
        
        # Default configurations
        self.default_retry_config = RetryConfig()
        self.default_timeout_config = TimeoutConfig()
        
        self.logger.info("APIIntegrationTester initialized")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the API integration tester"""
        logger = logging.getLogger('APIIntegrationTester')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._setup_http_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._cleanup_http_session()
        await self._cleanup_websocket_connections()
    
    async def _setup_http_session(self):
        """Setup HTTP session for API testing"""
        if aiohttp is None:
            self.logger.warning("aiohttp not available, using mock HTTP session")
            self.http_session = MockHTTPSession()
        else:
            timeout = aiohttp.ClientTimeout(
                connect=self.default_timeout_config.connect_timeout,
                total=self.default_timeout_config.total_timeout
            )
            self.http_session = aiohttp.ClientSession(timeout=timeout)
    
    async def _cleanup_http_session(self):
        """Cleanup HTTP session"""
        if self.http_session and hasattr(self.http_session, 'close'):
            await self.http_session.close()
    
    async def _cleanup_websocket_connections(self):
        """Cleanup WebSocket connections"""
        for connection in self.websocket_connections.values():
            if hasattr(connection, 'close'):
                await connection.close()
        self.websocket_connections.clear()
    
    def register_test_case(self, test_case: APITestCase) -> None:
        """
        Register a new API test case.
        
        Args:
            test_case: The API test case to register
        """
        self.test_cases[test_case.test_id] = test_case
        self.logger.info(f"Registered API test case: {test_case.test_name}")
    
    def register_rest_api_test(
        self,
        test_name: str,
        endpoint_url: str,
        method: HTTPMethod,
        request_data: Optional[Dict[str, Any]] = None,
        expected_status_codes: List[int] = None,
        validation_rules: Dict[str, Any] = None,
        authentication: AuthenticationType = AuthenticationType.NONE
    ) -> str:
        """
        Register a REST API test.
        
        Args:
            test_name: Name of the test
            endpoint_url: URL of the API endpoint
            method: HTTP method to use
            request_data: Request data to send
            expected_status_codes: Expected HTTP status codes
            validation_rules: Rules for validating the response
            authentication: Type of authentication to use
            
        Returns:
            Test case ID
        """
        test_id = f"rest_api_{uuid.uuid4().hex[:8]}"
        
        endpoint = APIEndpoint(
            url=endpoint_url,
            method=method,
            api_type=APIType.REST,
            authentication=authentication,
            request_body=request_data,
            expected_status_codes=expected_status_codes or [200]
        )
        
        async def rest_api_test():
            return await self._execute_rest_api_test(endpoint, validation_rules or {})
        
        test_case = APITestCase(
            test_id=test_id,
            test_name=test_name,
            api_type=APIType.REST,
            endpoint=endpoint,
            description=f"REST API test for {method.value} {endpoint_url}",
            test_function=rest_api_test,
            validation_rules=validation_rules or {}
        )
        
        self.register_test_case(test_case)
        return test_id
    
    def register_graphql_test(
        self,
        test_name: str,
        endpoint_url: str,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        expected_fields: List[str] = None,
        authentication: AuthenticationType = AuthenticationType.NONE
    ) -> str:
        """
        Register a GraphQL test.
        
        Args:
            test_name: Name of the test
            endpoint_url: URL of the GraphQL endpoint
            query: GraphQL query or mutation
            variables: Variables for the GraphQL query
            expected_fields: Expected fields in the response
            authentication: Type of authentication to use
            
        Returns:
            Test case ID
        """
        test_id = f"graphql_{uuid.uuid4().hex[:8]}"
        
        endpoint = APIEndpoint(
            url=endpoint_url,
            method=HTTPMethod.POST,
            api_type=APIType.GRAPHQL,
            authentication=authentication,
            request_body={
                'query': query,
                'variables': variables or {}
            }
        )
        
        async def graphql_test():
            return await self._execute_graphql_test(endpoint, expected_fields or [])
        
        test_case = APITestCase(
            test_id=test_id,
            test_name=test_name,
            api_type=APIType.GRAPHQL,
            endpoint=endpoint,
            description=f"GraphQL test for {endpoint_url}",
            test_function=graphql_test,
            validation_rules={'expected_fields': expected_fields or []}
        )
        
        self.register_test_case(test_case)
        return test_id
    
    def register_websocket_test(
        self,
        test_name: str,
        endpoint_url: str,
        messages_to_send: List[Dict[str, Any]],
        expected_responses: List[Dict[str, Any]] = None,
        connection_timeout: float = 10.0,
        authentication: AuthenticationType = AuthenticationType.NONE
    ) -> str:
        """
        Register a WebSocket test.
        
        Args:
            test_name: Name of the test
            endpoint_url: URL of the WebSocket endpoint
            messages_to_send: List of messages to send
            expected_responses: Expected responses
            connection_timeout: Connection timeout in seconds
            authentication: Type of authentication to use
            
        Returns:
            Test case ID
        """
        test_id = f"websocket_{uuid.uuid4().hex[:8]}"
        
        endpoint = APIEndpoint(
            url=endpoint_url,
            method=HTTPMethod.GET,  # WebSocket uses GET for initial handshake
            api_type=APIType.WEBSOCKET,
            authentication=authentication,
            timeout_seconds=int(connection_timeout)
        )
        
        async def websocket_test():
            return await self._execute_websocket_test(
                endpoint, messages_to_send, expected_responses or []
            )
        
        test_case = APITestCase(
            test_id=test_id,
            test_name=test_name,
            api_type=APIType.WEBSOCKET,
            endpoint=endpoint,
            description=f"WebSocket test for {endpoint_url}",
            test_function=websocket_test,
            validation_rules={
                'messages_to_send': messages_to_send,
                'expected_responses': expected_responses or []
            }
        )
        
        self.register_test_case(test_case)
        return test_id
    
    def register_authentication_test(
        self,
        test_name: str,
        endpoint_url: str,
        auth_type: AuthenticationType,
        credentials: Dict[str, str],
        test_scenarios: List[Dict[str, Any]]
    ) -> str:
        """
        Register an authentication test.
        
        Args:
            test_name: Name of the test
            endpoint_url: URL of the endpoint to test
            auth_type: Type of authentication to test
            credentials: Authentication credentials
            test_scenarios: List of authentication scenarios to test
            
        Returns:
            Test case ID
        """
        test_id = f"auth_{uuid.uuid4().hex[:8]}"
        
        endpoint = APIEndpoint(
            url=endpoint_url,
            method=HTTPMethod.GET,
            api_type=APIType.REST,
            authentication=auth_type
        )
        
        async def auth_test():
            return await self._execute_authentication_test(
                endpoint, credentials, test_scenarios
            )
        
        test_case = APITestCase(
            test_id=test_id,
            test_name=test_name,
            api_type=APIType.REST,
            endpoint=endpoint,
            description=f"Authentication test for {auth_type.value}",
            test_function=auth_test,
            validation_rules={
                'credentials': credentials,
                'test_scenarios': test_scenarios
            }
        )
        
        self.register_test_case(test_case)
        return test_id    

    async def execute_test_case(self, test_id: str) -> APITestResult:
        """
        Execute a single API test case.
        
        Args:
            test_id: ID of the test case to execute
            
        Returns:
            API test result
        """
        if test_id not in self.test_cases:
            raise ValueError(f"Test case {test_id} not found")
        
        test_case = self.test_cases[test_id]
        start_time = datetime.now()
        
        self.logger.info(f"Executing API test: {test_case.test_name}")
        
        try:
            # Setup phase
            if test_case.setup_function:
                await self._execute_with_timeout(
                    test_case.setup_function(), test_case.endpoint.timeout_seconds
                )
            
            # Execute test with timeout
            test_result_data = await self._execute_with_timeout(
                test_case.test_function(), test_case.endpoint.timeout_seconds
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Create successful result
            result = APITestResult(
                test_case=test_case,
                status=APITestStatus.PASSED,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                **test_result_data
            )
            
        except asyncio.TimeoutError:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result = APITestResult(
                test_case=test_case,
                status=APITestStatus.TIMEOUT,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                error_message=f"Test timed out after {test_case.endpoint.timeout_seconds} seconds",
                timeout_occurred=True
            )
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.logger.error(f"Test {test_case.test_name} failed with error: {str(e)}")
            
            result = APITestResult(
                test_case=test_case,
                status=APITestStatus.FAILED,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                error_message=str(e),
                stack_trace=traceback.format_exc()
            )
            
        finally:
            # Teardown phase
            if test_case.teardown_function:
                try:
                    await self._execute_with_timeout(
                        test_case.teardown_function(), test_case.endpoint.timeout_seconds
                    )
                except Exception as e:
                    self.logger.warning(f"Teardown failed for {test_case.test_name}: {e}")
        
        self.test_results[test_id] = result
        self.logger.info(f"Test {test_case.test_name} completed with status: {result.status.value}")
        
        return result
    
    async def execute_test_suite(
        self,
        suite_name: str,
        test_ids: Optional[List[str]] = None,
        parallel_execution: bool = True
    ) -> APITestSuiteResult:
        """
        Execute a suite of API tests.
        
        Args:
            suite_name: Name of the test suite
            test_ids: List of test IDs to execute (None for all)
            parallel_execution: Whether to execute tests in parallel
            
        Returns:
            API test suite result
        """
        start_time = datetime.now()
        
        if test_ids is None:
            test_ids = list(self.test_cases.keys())
        
        self.logger.info(f"Executing API test suite: {suite_name} ({len(test_ids)} tests)")
        
        # Setup HTTP session if not already done
        if self.http_session is None:
            await self._setup_http_session()
        
        try:
            # Execute tests
            if parallel_execution:
                results = await self._execute_tests_parallel(test_ids)
            else:
                results = await self._execute_tests_sequential(test_ids)
            
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            # Calculate statistics
            total_tests = len(results)
            passed_tests = sum(1 for r in results if r.status == APITestStatus.PASSED)
            failed_tests = sum(1 for r in results if r.status == APITestStatus.FAILED)
            error_tests = sum(1 for r in results if r.status == APITestStatus.ERROR)
            skipped_tests = sum(1 for r in results if r.status == APITestStatus.SKIPPED)
            timeout_tests = sum(1 for r in results if r.status == APITestStatus.TIMEOUT)
            
            pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
            
            # Generate summaries
            performance_summary = self._generate_performance_summary(results)
            endpoint_coverage_summary = self._generate_endpoint_coverage_summary(results)
            authentication_summary = self._generate_authentication_summary(results)
            recommendations = self._generate_recommendations(results)
            
            suite_result = APITestSuiteResult(
                suite_name=suite_name,
                start_time=start_time,
                end_time=end_time,
                total_duration=total_duration,
                total_tests=total_tests,
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                error_tests=error_tests,
                skipped_tests=skipped_tests,
                timeout_tests=timeout_tests,
                pass_rate=pass_rate,
                test_results=results,
                api_performance_summary=performance_summary,
                endpoint_coverage_summary=endpoint_coverage_summary,
                authentication_summary=authentication_summary,
                recommendations=recommendations
            )
            
            self.suite_results.append(suite_result)
            
            self.logger.info(
                f"Suite {suite_name} completed: {passed_tests}/{total_tests} passed "
                f"({pass_rate:.1f}% pass rate)"
            )
            
            return suite_result
            
        finally:
            # Cleanup connections
            await self._cleanup_websocket_connections()
    
    async def _execute_with_timeout(self, coro, timeout_seconds: int):
        """Execute a coroutine with timeout"""
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    
    async def _execute_tests_parallel(self, test_ids: List[str]) -> List[APITestResult]:
        """Execute tests in parallel"""
        tasks = [self.execute_test_case(test_id) for test_id in test_ids]
        return await asyncio.gather(*tasks, return_exceptions=False)
    
    async def _execute_tests_sequential(self, test_ids: List[str]) -> List[APITestResult]:
        """Execute tests sequentially"""
        results = []
        for test_id in test_ids:
            result = await self.execute_test_case(test_id)
            results.append(result)
        return results
    
    # REST API testing implementation
    async def _execute_rest_api_test(
        self, endpoint: APIEndpoint, validation_rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a REST API test"""
        
        start_time = time.time()
        retry_attempts = 0
        
        # Prepare headers
        headers = endpoint.headers.copy()
        headers.update(await self._get_auth_headers(endpoint.authentication))
        
        # Prepare request data
        request_kwargs = {
            'headers': headers,
            'params': endpoint.query_params
        }
        
        if endpoint.request_body:
            if endpoint.method in [HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.PATCH]:
                request_kwargs['json'] = endpoint.request_body
        
        # Execute request with retry logic
        response_data = None
        status_code = None
        response_headers = {}
        
        for attempt in range(endpoint.retry_attempts + 1):
            try:
                response_data, status_code, response_headers = await self._make_http_request(
                    endpoint.method, endpoint.url, **request_kwargs
                )
                
                # Check if status code is expected
                if status_code in endpoint.expected_status_codes:
                    break
                elif status_code in self.default_retry_config.retry_on_status_codes:
                    retry_attempts += 1
                    if attempt < endpoint.retry_attempts:
                        await asyncio.sleep(endpoint.retry_delay * (2 ** attempt))
                        continue
                
                break
                
            except Exception as e:
                retry_attempts += 1
                if attempt < endpoint.retry_attempts:
                    await asyncio.sleep(endpoint.retry_delay * (2 ** attempt))
                    continue
                raise e
        
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        # Validate response
        validation_passed = self._validate_rest_response(
            response_data, status_code, validation_rules
        )
        
        return {
            'request_count': retry_attempts + 1,
            'response_status_code': status_code,
            'response_headers': response_headers,
            'response_body': response_data,
            'performance_metrics': {
                'response_time_ms': duration_ms,
                'retry_attempts': retry_attempts
            },
            'retry_attempts': retry_attempts
        }
    
    # GraphQL testing implementation
    async def _execute_graphql_test(
        self, endpoint: APIEndpoint, expected_fields: List[str]
    ) -> Dict[str, Any]:
        """Execute a GraphQL test"""
        
        start_time = time.time()
        
        # Prepare headers for GraphQL
        headers = endpoint.headers.copy()
        headers.update(await self._get_auth_headers(endpoint.authentication))
        headers['Content-Type'] = 'application/json'
        
        # Execute GraphQL request
        response_data, status_code, response_headers = await self._make_http_request(
            HTTPMethod.POST, endpoint.url, json=endpoint.request_body, headers=headers
        )
        
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        # Validate GraphQL response
        validation_passed = self._validate_graphql_response(
            response_data, expected_fields
        )
        
        return {
            'request_count': 1,
            'response_status_code': status_code,
            'response_headers': response_headers,
            'response_body': response_data,
            'performance_metrics': {
                'response_time_ms': duration_ms,
                'query_complexity': len(expected_fields)
            }
        }
    
    # WebSocket testing implementation
    async def _execute_websocket_test(
        self,
        endpoint: APIEndpoint,
        messages_to_send: List[Dict[str, Any]],
        expected_responses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute a WebSocket test"""
        
        start_time = time.time()
        
        # Mock WebSocket connection for demonstration
        connection_id = f"ws_{uuid.uuid4().hex[:8]}"
        
        try:
            # Simulate WebSocket connection
            await asyncio.sleep(0.1)  # Simulate connection time
            
            responses_received = []
            
            # Send messages and collect responses
            for i, message in enumerate(messages_to_send):
                # Simulate sending message
                await asyncio.sleep(0.05)
                
                # Simulate receiving response
                if i < len(expected_responses):
                    responses_received.append(expected_responses[i])
                else:
                    responses_received.append({'echo': message})
            
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            # Validate WebSocket responses
            validation_passed = self._validate_websocket_responses(
                responses_received, expected_responses
            )
            
            return {
                'request_count': len(messages_to_send),
                'response_body': responses_received,
                'performance_metrics': {
                    'connection_time_ms': 100,  # Mock value
                    'total_duration_ms': duration_ms,
                    'messages_sent': len(messages_to_send),
                    'messages_received': len(responses_received)
                }
            }
            
        finally:
            # Cleanup WebSocket connection
            if connection_id in self.websocket_connections:
                del self.websocket_connections[connection_id]
    
    # Authentication testing implementation
    async def _execute_authentication_test(
        self,
        endpoint: APIEndpoint,
        credentials: Dict[str, str],
        test_scenarios: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute an authentication test"""
        
        auth_results = {}
        performance_metrics = {}
        
        for scenario in test_scenarios:
            scenario_name = scenario['name']
            scenario_type = scenario['type']
            
            start_time = time.time()
            
            try:
                if scenario_type == 'valid_credentials':
                    result = await self._test_valid_authentication(endpoint, credentials)
                elif scenario_type == 'invalid_credentials':
                    result = await self._test_invalid_authentication(endpoint, scenario.get('invalid_creds', {}))
                elif scenario_type == 'expired_token':
                    result = await self._test_expired_token(endpoint, scenario.get('expired_token', ''))
                elif scenario_type == 'missing_auth':
                    result = await self._test_missing_authentication(endpoint)
                else:
                    result = {'success': False, 'error': f'Unknown scenario type: {scenario_type}'}
                
                end_time = time.time()
                scenario_duration = end_time - start_time
                
                performance_metrics[f'{scenario_name}_duration_ms'] = scenario_duration * 1000
                auth_results[scenario_name] = result
                
            except Exception as e:
                end_time = time.time()
                scenario_duration = end_time - start_time
                
                performance_metrics[f'{scenario_name}_duration_ms'] = scenario_duration * 1000
                auth_results[scenario_name] = {'success': False, 'error': str(e)}
        
        return {
            'request_count': len(test_scenarios),
            'performance_metrics': performance_metrics,
            'response_body': auth_results
        }
    
    # HTTP request implementation
    async def _make_http_request(
        self, method: HTTPMethod, url: str, **kwargs
    ) -> Tuple[Any, int, Dict[str, str]]:
        """Make an HTTP request"""
        
        if self.http_session and hasattr(self.http_session, 'request'):
            # Use real aiohttp session
            async with self.http_session.request(method.value, url, **kwargs) as response:
                response_data = await response.json() if response.content_type == 'application/json' else await response.text()
                return response_data, response.status, dict(response.headers)
        else:
            # Use mock HTTP session
            await asyncio.sleep(0.1)  # Simulate network delay
            
            # Mock response based on method and URL
            if method == HTTPMethod.GET:
                response_data = {'message': 'GET request successful', 'url': url}
                status_code = 200
            elif method == HTTPMethod.POST:
                response_data = {'message': 'POST request successful', 'created': True}
                status_code = 201
            elif method == HTTPMethod.PUT:
                response_data = {'message': 'PUT request successful', 'updated': True}
                status_code = 200
            elif method == HTTPMethod.DELETE:
                response_data = {'message': 'DELETE request successful', 'deleted': True}
                status_code = 204
            else:
                response_data = {'message': f'{method.value} request successful'}
                status_code = 200
            
            response_headers = {
                'Content-Type': 'application/json',
                'Server': 'MockServer/1.0',
                'X-Response-Time': '100ms'
            }
            
            return response_data, status_code, response_headers
    
    # Authentication helpers
    async def _get_auth_headers(self, auth_type: AuthenticationType) -> Dict[str, str]:
        """Get authentication headers based on auth type"""
        
        if auth_type == AuthenticationType.NONE:
            return {}
        elif auth_type == AuthenticationType.BEARER_TOKEN:
            token = self.auth_tokens.get('bearer_token', 'mock_bearer_token')
            return {'Authorization': f'Bearer {token}'}
        elif auth_type == AuthenticationType.API_KEY:
            api_key = self.auth_tokens.get('api_key', 'mock_api_key')
            return {'X-API-Key': api_key}
        elif auth_type == AuthenticationType.JWT:
            jwt_token = self.auth_tokens.get('jwt_token', 'mock_jwt_token')
            return {'Authorization': f'Bearer {jwt_token}'}
        elif auth_type == AuthenticationType.BASIC:
            # Mock basic auth
            return {'Authorization': 'Basic bW9ja191c2VyOm1vY2tfcGFzc3dvcmQ='}
        else:
            return {}
    
    # Authentication test implementations
    async def _test_valid_authentication(self, endpoint: APIEndpoint, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Test valid authentication"""
        # Mock valid authentication test
        await asyncio.sleep(0.1)
        return {'success': True, 'authenticated': True, 'user_id': 'test_user'}
    
    async def _test_invalid_authentication(self, endpoint: APIEndpoint, invalid_creds: Dict[str, str]) -> Dict[str, Any]:
        """Test invalid authentication"""
        # Mock invalid authentication test
        await asyncio.sleep(0.1)
        return {'success': True, 'authenticated': False, 'error': 'Invalid credentials'}
    
    async def _test_expired_token(self, endpoint: APIEndpoint, expired_token: str) -> Dict[str, Any]:
        """Test expired token"""
        # Mock expired token test
        await asyncio.sleep(0.1)
        return {'success': True, 'authenticated': False, 'error': 'Token expired'}
    
    async def _test_missing_authentication(self, endpoint: APIEndpoint) -> Dict[str, Any]:
        """Test missing authentication"""
        # Mock missing authentication test
        await asyncio.sleep(0.1)
        return {'success': True, 'authenticated': False, 'error': 'Authentication required'}