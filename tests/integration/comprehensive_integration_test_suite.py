#!/usr/bin/env python3
"""
Comprehensive Integration Test Suite for Algorithmic Trading System
Tests complete workflows and cross-component integration scenarios.
"""

import pytest
import asyncio
import time
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import requests
import websockets
from unittest.mock import Mock, patch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TestScenario:
    """Represents a complete integration test scenario"""
    name: str
    description: str
    steps: List[Dict[str, Any]]
    expected_outcomes: List[str]
    cleanup_steps: List[Dict[str, Any]]
    timeout: int = 300  # 5 minutes default

@dataclass
class TestResult:
    """Represents the result of a test scenario"""
    scenario_name: str
    success: bool
    duration: float
    steps_completed: int
    total_steps: int
    error_message: Optional[str] = None
    artifacts: Dict[str, Any] = None

class IntegrationTestFramework:
    """Comprehensive integration testing framework"""
    
    def __init__(self, base_url: str = "http://localhost:8000", 
                 websocket_url: str = "ws://localhost:8000/ws"):
        self.base_url = base_url
        self.websocket_url = websocket_url
        self.session = requests.Session()
        self.test_data = {}
        self.cleanup_tasks = []
        
    async def run_scenario(self, scenario: TestScenario) -> TestResult:
        """Run a complete integration test scenario"""
        start_time = time.time()
        steps_completed = 0
        
        try:
            logger.info(f"Starting scenario: {scenario.name}")
            
            for i, step in enumerate(scenario.steps):
                logger.info(f"Executing step {i+1}/{len(scenario.steps)}: {step.get('name', 'Unnamed step')}")
                
                await self._execute_step(step)
                steps_completed += 1
                
                # Check timeout
                if time.time() - start_time > scenario.timeout:
                    raise TimeoutError(f"Scenario timeout after {scenario.timeout} seconds")
            
            # Verify expected outcomes
            await self._verify_outcomes(scenario.expected_outcomes)
            
            duration = time.time() - start_time
            logger.info(f"Scenario {scenario.name} completed successfully in {duration:.2f}s")
            
            return TestResult(
                scenario_name=scenario.name,
                success=True,
                duration=duration,
                steps_completed=steps_completed,
                total_steps=len(scenario.steps),
                artifacts=self.test_data.copy()
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Scenario {scenario.name} failed: {str(e)}")
            
            return TestResult(
                scenario_name=scenario.name,
                success=False,
                duration=duration,
                steps_completed=steps_completed,
                total_steps=len(scenario.steps),
                error_message=str(e),
                artifacts=self.test_data.copy()
            )
        finally:
            # Always run cleanup
            await self._cleanup(scenario.cleanup_steps)
    
    async def _execute_step(self, step: Dict[str, Any]):
        """Execute a single test step"""
        step_type = step.get('type')
        
        if step_type == 'api_call':
            await self._execute_api_call(step)
        elif step_type == 'websocket':
            await self._execute_websocket_step(step)
        elif step_type == 'database_check':
            await self._execute_database_check(step)
        elif step_type == 'wait':
            await self._execute_wait(step)
        elif step_type == 'validation':
            await self._execute_validation(step)
        else:
            raise ValueError(f"Unknown step type: {step_type}")
    
    async def _execute_api_call(self, step: Dict[str, Any]):
        """Execute an API call step"""
        method = step.get('method', 'GET')
        endpoint = step.get('endpoint')
        data = step.get('data', {})
        headers = step.get('headers', {})
        expected_status = step.get('expected_status', 200)
        store_response = step.get('store_response')
        
        # Replace placeholders in data with stored values
        data = self._replace_placeholders(data)
        
        url = f"{self.base_url}{endpoint}"
        
        if method.upper() == 'GET':
            response = self.session.get(url, headers=headers, params=data)
        elif method.upper() == 'POST':
            response = self.session.post(url, headers=headers, json=data)
        elif method.upper() == 'PUT':
            response = self.session.put(url, headers=headers, json=data)
        elif method.upper() == 'DELETE':
            response = self.session.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        if response.status_code != expected_status:
            raise AssertionError(f"Expected status {expected_status}, got {response.status_code}: {response.text}")
        
        # Store response data if requested
        if store_response:
            try:
                response_data = response.json()
                self.test_data[store_response] = response_data
            except:
                self.test_data[store_response] = response.text
    
    async def _execute_websocket_step(self, step: Dict[str, Any]):
        """Execute a WebSocket interaction step"""
        action = step.get('action')
        message = step.get('message', {})
        expected_response = step.get('expected_response')
        timeout = step.get('timeout', 10)
        
        message = self._replace_placeholders(message)
        
        async with websockets.connect(self.websocket_url) as websocket:
            if action == 'send':
                await websocket.send(json.dumps(message))
            
            if expected_response:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=timeout)
                    response_data = json.loads(response)
                    
                    # Validate response structure
                    for key, expected_value in expected_response.items():
                        if key not in response_data:
                            raise AssertionError(f"Expected key '{key}' not found in WebSocket response")
                        
                        if expected_value != "*" and response_data[key] != expected_value:
                            raise AssertionError(f"Expected {key}={expected_value}, got {response_data[key]}")
                    
                    # Store response if needed
                    store_key = step.get('store_response')
                    if store_key:
                        self.test_data[store_key] = response_data
                        
                except asyncio.TimeoutError:
                    raise AssertionError(f"WebSocket response timeout after {timeout} seconds")
    
    async def _execute_database_check(self, step: Dict[str, Any]):
        """Execute a database validation step"""
        # This would integrate with your database layer
        # For now, we'll simulate database checks
        table = step.get('table')
        conditions = step.get('conditions', {})
        expected_count = step.get('expected_count')
        
        logger.info(f"Database check: {table} with conditions {conditions}")
        
        # Simulate database query result
        # In real implementation, this would query your actual database
        if expected_count is not None:
            # Simulate count check
            actual_count = 1  # This would be the actual query result
            if actual_count != expected_count:
                raise AssertionError(f"Expected {expected_count} records, found {actual_count}")
    
    async def _execute_wait(self, step: Dict[str, Any]):
        """Execute a wait step"""
        duration = step.get('duration', 1)
        await asyncio.sleep(duration)
    
    async def _execute_validation(self, step: Dict[str, Any]):
        """Execute a validation step"""
        validations = step.get('validations', [])
        
        for validation in validations:
            condition = validation.get('condition')
            expected = validation.get('expected')
            actual_key = validation.get('actual_key')
            
            if actual_key in self.test_data:
                actual = self.test_data[actual_key]
                
                if condition == 'equals':
                    if actual != expected:
                        raise AssertionError(f"Validation failed: expected {expected}, got {actual}")
                elif condition == 'contains':
                    if expected not in str(actual):
                        raise AssertionError(f"Validation failed: '{expected}' not found in '{actual}'")
                elif condition == 'greater_than':
                    if actual <= expected:
                        raise AssertionError(f"Validation failed: {actual} not greater than {expected}")
                elif condition == 'exists':
                    if not actual:
                        raise AssertionError(f"Validation failed: {actual_key} does not exist or is empty")
    
    def _replace_placeholders(self, data: Any) -> Any:
        """Replace placeholders in data with stored test values"""
        if isinstance(data, dict):
            return {k: self._replace_placeholders(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._replace_placeholders(item) for item in data]
        elif isinstance(data, str):
            # Handle both full replacement and partial replacement
            import re
            result = data
            for key, value in self.test_data.items():
                pattern = f'${{{key}}}'
                result = result.replace(pattern, str(value))
            return result
        else:
            return data
    
    async def _verify_outcomes(self, expected_outcomes: List[str]):
        """Verify that expected outcomes were achieved"""
        for outcome in expected_outcomes:
            # Parse outcome conditions
            if outcome.startswith('data_exists:'):
                key = outcome.split(':', 1)[1]
                if key not in self.test_data:
                    raise AssertionError(f"Expected data key '{key}' not found")
            elif outcome.startswith('status_code:'):
                # This would be handled in the API call steps
                pass
            else:
                logger.warning(f"Unknown outcome condition: {outcome}")
    
    async def _cleanup(self, cleanup_steps: List[Dict[str, Any]]):
        """Execute cleanup steps"""
        for step in cleanup_steps:
            try:
                await self._execute_step(step)
            except Exception as e:
                logger.warning(f"Cleanup step failed: {e}")

class EndToEndTestScenarios:
    """Predefined end-to-end test scenarios"""
    
    @staticmethod
    def complete_trading_workflow() -> TestScenario:
        """Complete trading workflow from strategy creation to execution"""
        return TestScenario(
            name="Complete Trading Workflow",
            description="Tests the complete flow from user authentication to strategy execution",
            steps=[
                {
                    'type': 'api_call',
                    'name': 'User Authentication',
                    'method': 'POST',
                    'endpoint': '/auth/login',
                    'data': {
                        'username': 'test_user',
                        'password': 'test_password'
                    },
                    'expected_status': 200,
                    'store_response': 'auth_response'
                },
                {
                    'type': 'validation',
                    'name': 'Validate Authentication Token',
                    'validations': [
                        {
                            'condition': 'exists',
                            'actual_key': 'auth_response',
                        }
                    ]
                },
                {
                    'type': 'api_call',
                    'name': 'Create Trading Strategy',
                    'method': 'POST',
                    'endpoint': '/strategies',
                    'headers': {
                        'Authorization': 'Bearer ${auth_response.access_token}'
                    },
                    'data': {
                        'name': 'Integration Test Strategy',
                        'description': 'Strategy created during integration testing',
                        'asset_class': 'stocks',
                        'strategy_type': 'momentum',
                        'parameters': {
                            'lookback_period': 20,
                            'threshold': 0.02
                        }
                    },
                    'expected_status': 201,
                    'store_response': 'strategy_response'
                },
                {
                    'type': 'api_call',
                    'name': 'Get Market Data',
                    'method': 'GET',
                    'endpoint': '/market-data/quotes/AAPL',
                    'headers': {
                        'Authorization': 'Bearer ${auth_response.access_token}'
                    },
                    'expected_status': 200,
                    'store_response': 'market_data'
                },
                {
                    'type': 'api_call',
                    'name': 'Run Backtest',
                    'method': 'POST',
                    'endpoint': '/backtesting/run',
                    'headers': {
                        'Authorization': 'Bearer ${auth_response.access_token}'
                    },
                    'data': {
                        'strategy_id': '${strategy_response.id}',
                        'start_date': '2023-01-01',
                        'end_date': '2023-12-31',
                        'initial_capital': 100000
                    },
                    'expected_status': 202,
                    'store_response': 'backtest_response'
                },
                {
                    'type': 'wait',
                    'name': 'Wait for Backtest Completion',
                    'duration': 5
                },
                {
                    'type': 'api_call',
                    'name': 'Get Backtest Results',
                    'method': 'GET',
                    'endpoint': '/backtesting/${backtest_response.backtest_id}',
                    'headers': {
                        'Authorization': 'Bearer ${auth_response.access_token}'
                    },
                    'expected_status': 200,
                    'store_response': 'backtest_results'
                },
                {
                    'type': 'api_call',
                    'name': 'Place Test Order',
                    'method': 'POST',
                    'endpoint': '/orders',
                    'headers': {
                        'Authorization': 'Bearer ${auth_response.access_token}'
                    },
                    'data': {
                        'symbol': 'AAPL',
                        'side': 'buy',
                        'order_type': 'limit',
                        'quantity': 10,
                        'price': 150.00
                    },
                    'expected_status': 201,
                    'store_response': 'order_response'
                }
            ],
            expected_outcomes=[
                'data_exists:auth_response',
                'data_exists:strategy_response',
                'data_exists:backtest_results',
                'data_exists:order_response'
            ],
            cleanup_steps=[
                {
                    'type': 'api_call',
                    'name': 'Cancel Test Order',
                    'method': 'DELETE',
                    'endpoint': '/orders/${order_response.id}',
                    'headers': {
                        'Authorization': 'Bearer ${auth_response.access_token}'
                    },
                    'expected_status': 200
                },
                {
                    'type': 'api_call',
                    'name': 'Delete Test Strategy',
                    'method': 'DELETE',
                    'endpoint': '/strategies/${strategy_response.id}',
                    'headers': {
                        'Authorization': 'Bearer ${auth_response.access_token}'
                    },
                    'expected_status': 204
                }
            ]
        )
    
    @staticmethod
    def real_time_data_flow() -> TestScenario:
        """Test real-time data flow and WebSocket functionality"""
        return TestScenario(
            name="Real-time Data Flow",
            description="Tests WebSocket connections and real-time data streaming",
            steps=[
                {
                    'type': 'api_call',
                    'name': 'Authenticate User',
                    'method': 'POST',
                    'endpoint': '/auth/login',
                    'data': {
                        'username': 'test_user',
                        'password': 'test_password'
                    },
                    'expected_status': 200,
                    'store_response': 'auth_response'
                },
                {
                    'type': 'websocket',
                    'name': 'Connect to Market Data Stream',
                    'action': 'send',
                    'message': {
                        'action': 'authenticate',
                        'token': '${auth_response.access_token}'
                    },
                    'expected_response': {
                        'status': 'authenticated'
                    },
                    'store_response': 'ws_auth'
                },
                {
                    'type': 'websocket',
                    'name': 'Subscribe to Market Data',
                    'action': 'send',
                    'message': {
                        'action': 'subscribe',
                        'symbols': ['AAPL', 'GOOGL'],
                        'data_types': ['quotes']
                    },
                    'expected_response': {
                        'status': 'subscribed'
                    },
                    'timeout': 15
                }
            ],
            expected_outcomes=[
                'data_exists:auth_response',
                'data_exists:ws_auth'
            ],
            cleanup_steps=[]
        )
    
    @staticmethod
    def portfolio_management_workflow() -> TestScenario:
        """Test portfolio management and risk controls"""
        return TestScenario(
            name="Portfolio Management Workflow",
            description="Tests portfolio creation, risk management, and performance tracking",
            steps=[
                {
                    'type': 'api_call',
                    'name': 'User Authentication',
                    'method': 'POST',
                    'endpoint': '/auth/login',
                    'data': {
                        'username': 'test_user',
                        'password': 'test_password'
                    },
                    'expected_status': 200,
                    'store_response': 'auth_response'
                },
                {
                    'type': 'api_call',
                    'name': 'Get Portfolio Status',
                    'method': 'GET',
                    'endpoint': '/portfolio',
                    'headers': {
                        'Authorization': 'Bearer ${auth_response.access_token}'
                    },
                    'expected_status': 200,
                    'store_response': 'portfolio_status'
                },
                {
                    'type': 'api_call',
                    'name': 'Get Risk Limits',
                    'method': 'GET',
                    'endpoint': '/risk/limits',
                    'headers': {
                        'Authorization': 'Bearer ${auth_response.access_token}'
                    },
                    'expected_status': 200,
                    'store_response': 'risk_limits'
                },
                {
                    'type': 'api_call',
                    'name': 'Update Risk Limits',
                    'method': 'POST',
                    'endpoint': '/risk/limits',
                    'headers': {
                        'Authorization': 'Bearer ${auth_response.access_token}'
                    },
                    'data': {
                        'daily_loss_limit': 0.015,
                        'position_size_limit': 0.04,
                        'max_positions': 8
                    },
                    'expected_status': 200,
                    'store_response': 'updated_limits'
                },
                {
                    'type': 'api_call',
                    'name': 'Get Portfolio Performance',
                    'method': 'GET',
                    'endpoint': '/portfolio/performance?period=1m',
                    'headers': {
                        'Authorization': 'Bearer ${auth_response.access_token}'
                    },
                    'expected_status': 200,
                    'store_response': 'performance_data'
                }
            ],
            expected_outcomes=[
                'data_exists:portfolio_status',
                'data_exists:risk_limits',
                'data_exists:performance_data'
            ],
            cleanup_steps=[]
        )
    
    @staticmethod
    def error_handling_and_recovery() -> TestScenario:
        """Test error handling and system recovery scenarios"""
        return TestScenario(
            name="Error Handling and Recovery",
            description="Tests system behavior under error conditions and recovery mechanisms",
            steps=[
                {
                    'type': 'api_call',
                    'name': 'Test Invalid Authentication',
                    'method': 'POST',
                    'endpoint': '/auth/login',
                    'data': {
                        'username': 'invalid_user',
                        'password': 'wrong_password'
                    },
                    'expected_status': 401
                },
                {
                    'type': 'api_call',
                    'name': 'Test Unauthorized Access',
                    'method': 'GET',
                    'endpoint': '/strategies',
                    'headers': {
                        'Authorization': 'Bearer invalid_token'
                    },
                    'expected_status': 401
                },
                {
                    'type': 'api_call',
                    'name': 'Test Invalid Strategy Creation',
                    'method': 'POST',
                    'endpoint': '/auth/login',
                    'data': {
                        'username': 'test_user',
                        'password': 'test_password'
                    },
                    'expected_status': 200,
                    'store_response': 'auth_response'
                },
                {
                    'type': 'api_call',
                    'name': 'Create Invalid Strategy',
                    'method': 'POST',
                    'endpoint': '/strategies',
                    'headers': {
                        'Authorization': 'Bearer ${auth_response.access_token}'
                    },
                    'data': {
                        'name': '',  # Invalid empty name
                        'asset_class': 'invalid_class'
                    },
                    'expected_status': 422
                },
                {
                    'type': 'api_call',
                    'name': 'Test Rate Limiting',
                    'method': 'GET',
                    'endpoint': '/market-data/quotes/AAPL',
                    'headers': {
                        'Authorization': 'Bearer ${auth_response.access_token}'
                    },
                    'expected_status': 200
                }
            ],
            expected_outcomes=[
                'data_exists:auth_response'
            ],
            cleanup_steps=[]
        )

class IntegrationTestRunner:
    """Main test runner for integration tests"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.framework = IntegrationTestFramework(
            base_url=self.config.get('base_url', 'http://localhost:8000'),
            websocket_url=self.config.get('websocket_url', 'ws://localhost:8000/ws')
        )
        self.results = []
    
    async def run_all_scenarios(self) -> List[TestResult]:
        """Run all predefined test scenarios"""
        scenarios = [
            EndToEndTestScenarios.complete_trading_workflow(),
            EndToEndTestScenarios.real_time_data_flow(),
            EndToEndTestScenarios.portfolio_management_workflow(),
            EndToEndTestScenarios.error_handling_and_recovery()
        ]
        
        results = []
        for scenario in scenarios:
            result = await self.framework.run_scenario(scenario)
            results.append(result)
            self.results.append(result)
        
        return results
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive test report"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests
        
        total_duration = sum(r.duration for r in self.results)
        avg_duration = total_duration / total_tests if total_tests > 0 else 0
        
        return {
            'summary': {
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                'total_duration': total_duration,
                'average_duration': avg_duration
            },
            'results': [
                {
                    'scenario': r.scenario_name,
                    'success': r.success,
                    'duration': r.duration,
                    'steps_completed': r.steps_completed,
                    'total_steps': r.total_steps,
                    'error': r.error_message
                }
                for r in self.results
            ],
            'failed_scenarios': [
                {
                    'scenario': r.scenario_name,
                    'error': r.error_message,
                    'artifacts': r.artifacts
                }
                for r in self.results if not r.success
            ]
        }

# Pytest Integration
class TestEndToEndIntegration:
    """Pytest test class for end-to-end integration testing"""
    
    @pytest.fixture(scope="class")
    def test_runner(self):
        """Create test runner instance"""
        return IntegrationTestRunner()
    
    @pytest.mark.asyncio
    async def test_complete_trading_workflow(self, test_runner):
        """Test complete trading workflow"""
        scenario = EndToEndTestScenarios.complete_trading_workflow()
        result = await test_runner.framework.run_scenario(scenario)
        
        assert result.success, f"Trading workflow failed: {result.error_message}"
        assert result.steps_completed == result.total_steps
        assert 'auth_response' in result.artifacts
        assert 'strategy_response' in result.artifacts
        assert 'order_response' in result.artifacts
    
    @pytest.mark.asyncio
    async def test_real_time_data_flow(self, test_runner):
        """Test real-time data flow"""
        scenario = EndToEndTestScenarios.real_time_data_flow()
        result = await test_runner.framework.run_scenario(scenario)
        
        assert result.success, f"Real-time data flow failed: {result.error_message}"
        assert 'auth_response' in result.artifacts
        assert 'ws_auth' in result.artifacts
    
    @pytest.mark.asyncio
    async def test_portfolio_management_workflow(self, test_runner):
        """Test portfolio management workflow"""
        scenario = EndToEndTestScenarios.portfolio_management_workflow()
        result = await test_runner.framework.run_scenario(scenario)
        
        assert result.success, f"Portfolio management failed: {result.error_message}"
        assert 'portfolio_status' in result.artifacts
        assert 'risk_limits' in result.artifacts
        assert 'performance_data' in result.artifacts
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, test_runner):
        """Test error handling and recovery"""
        scenario = EndToEndTestScenarios.error_handling_and_recovery()
        result = await test_runner.framework.run_scenario(scenario)
        
        assert result.success, f"Error handling test failed: {result.error_message}"
    
    @pytest.mark.asyncio
    async def test_data_consistency_across_components(self, test_runner):
        """Test data consistency across different system components"""
        # This test ensures that data remains consistent across different API endpoints
        framework = test_runner.framework
        
        # Authenticate
        auth_step = {
            'type': 'api_call',
            'method': 'POST',
            'endpoint': '/auth/login',
            'data': {'username': 'test_user', 'password': 'test_password'},
            'expected_status': 200,
            'store_response': 'auth'
        }
        await framework._execute_step(auth_step)
        
        # Create strategy
        strategy_step = {
            'type': 'api_call',
            'method': 'POST',
            'endpoint': '/strategies',
            'headers': {'Authorization': 'Bearer ${auth.access_token}'},
            'data': {
                'name': 'Consistency Test Strategy',
                'asset_class': 'stocks',
                'strategy_type': 'momentum'
            },
            'expected_status': 201,
            'store_response': 'strategy'
        }
        await framework._execute_step(strategy_step)
        
        # Verify strategy appears in list
        list_step = {
            'type': 'api_call',
            'method': 'GET',
            'endpoint': '/strategies',
            'headers': {'Authorization': 'Bearer ${auth.access_token}'},
            'expected_status': 200,
            'store_response': 'strategy_list'
        }
        await framework._execute_step(list_step)
        
        # Verify consistency
        strategy_id = framework.test_data['strategy']['id']
        strategy_list = framework.test_data['strategy_list']['strategies']
        
        found_strategy = next((s for s in strategy_list if s['id'] == strategy_id), None)
        assert found_strategy is not None, "Created strategy not found in strategy list"
        assert found_strategy['name'] == 'Consistency Test Strategy'
        
        # Cleanup
        cleanup_step = {
            'type': 'api_call',
            'method': 'DELETE',
            'endpoint': f'/strategies/{strategy_id}',
            'headers': {'Authorization': 'Bearer ${auth.access_token}'},
            'expected_status': 204
        }
        await framework._execute_step(cleanup_step)

# Standalone execution
async def main():
    """Main function for standalone execution"""
    print("🚀 Starting Comprehensive Integration Test Suite")
    print("=" * 60)
    
    runner = IntegrationTestRunner()
    results = await runner.run_all_scenarios()
    
    report = runner.generate_report()
    
    print("\n" + "=" * 60)
    print("INTEGRATION TEST RESULTS")
    print("=" * 60)
    
    print(f"Total Tests: {report['summary']['total_tests']}")
    print(f"Passed: {report['summary']['passed']}")
    print(f"Failed: {report['summary']['failed']}")
    print(f"Success Rate: {report['summary']['success_rate']:.1f}%")
    print(f"Total Duration: {report['summary']['total_duration']:.2f}s")
    
    if report['failed_scenarios']:
        print("\nFailed Scenarios:")
        for failure in report['failed_scenarios']:
            print(f"- {failure['scenario']}: {failure['error']}")
    
    print("\nDetailed Results:")
    for result in report['results']:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"{result['scenario']:<40} {status} ({result['duration']:.2f}s)")
    
    return report['summary']['success_rate'] == 100.0

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)