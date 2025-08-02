#!/usr/bin/env python3
"""
Test Suite for Integration Testing Framework
Validates the integration testing framework components work correctly.
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import tempfile
import sys
import os

# Add the integration tests directory to the path
sys.path.insert(0, str(Path(__file__).parent / "integration"))

from comprehensive_integration_test_suite import (
    IntegrationTestFramework, 
    TestScenario, 
    TestResult,
    EndToEndTestScenarios,
    IntegrationTestRunner
)
from data_consistency_tests import DataConsistencyValidator
from integration_test_automation import (
    IntegrationTestAutomation,
    TestExecution,
    TestSuite,
    TestStatus
)

class TestIntegrationTestFramework:
    """Test the core integration test framework"""
    
    @pytest.fixture
    def framework(self):
        """Create a test framework instance"""
        return IntegrationTestFramework(
            base_url="http://test-server:8000",
            websocket_url="ws://test-server:8000/ws"
        )
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock HTTP session"""
        session = Mock()
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"test": "data"}
        response.text = "test response"
        session.get.return_value = response
        session.post.return_value = response
        session.put.return_value = response
        session.delete.return_value = response
        return session
    
    def test_framework_initialization(self, framework):
        """Test framework initialization"""
        assert framework.base_url == "http://test-server:8000"
        assert framework.websocket_url == "ws://test-server:8000/ws"
        assert framework.test_data == {}
        assert framework.cleanup_tasks == []
    
    @pytest.mark.asyncio
    async def test_api_call_execution(self, framework, mock_session):
        """Test API call step execution"""
        framework.session = mock_session
        
        step = {
            'type': 'api_call',
            'method': 'GET',
            'endpoint': '/test',
            'expected_status': 200,
            'store_response': 'test_response'
        }
        
        await framework._execute_step(step)
        
        # Verify API call was made
        mock_session.get.assert_called_once()
        
        # Verify response was stored
        assert 'test_response' in framework.test_data
        assert framework.test_data['test_response'] == {"test": "data"}
    
    @pytest.mark.asyncio
    async def test_placeholder_replacement(self, framework):
        """Test placeholder replacement in test data"""
        framework.test_data = {
            'auth_token': 'test-token-123',
            'user_id': 'user-456'
        }
        
        data = {
            'authorization': 'Bearer ${auth_token}',
            'user': '${user_id}',
            'static_value': 'unchanged'
        }
        
        result = framework._replace_placeholders(data)
        
        assert result['authorization'] == 'Bearer test-token-123'
        assert result['user'] == 'user-456'
        assert result['static_value'] == 'unchanged'
    
    @pytest.mark.asyncio
    async def test_validation_step(self, framework):
        """Test validation step execution"""
        framework.test_data = {
            'response': {'status': 'success', 'count': 5}
        }
        
        step = {
            'type': 'validation',
            'validations': [
                {
                    'condition': 'equals',
                    'actual_key': 'response',
                    'expected': {'status': 'success', 'count': 5}
                }
            ]
        }
        
        # Should not raise an exception
        await framework._execute_step(step)
        
        # Test failing validation
        step['validations'][0]['expected'] = {'status': 'failed'}
        
        with pytest.raises(AssertionError):
            await framework._execute_step(step)
    
    @pytest.mark.asyncio
    async def test_wait_step(self, framework):
        """Test wait step execution"""
        start_time = time.time()
        
        step = {
            'type': 'wait',
            'duration': 0.1  # 100ms
        }
        
        await framework._execute_step(step)
        
        elapsed = time.time() - start_time
        assert elapsed >= 0.1
        assert elapsed < 0.2  # Should not take too long
    
    @pytest.mark.asyncio
    async def test_scenario_execution_success(self, framework, mock_session):
        """Test successful scenario execution"""
        framework.session = mock_session
        
        scenario = TestScenario(
            name="Test Scenario",
            description="A test scenario",
            steps=[
                {
                    'type': 'api_call',
                    'name': 'Test API Call',
                    'method': 'GET',
                    'endpoint': '/test',
                    'expected_status': 200,
                    'store_response': 'test_data'
                },
                {
                    'type': 'validation',
                    'name': 'Validate Response',
                    'validations': [
                        {
                            'condition': 'exists',
                            'actual_key': 'test_data'
                        }
                    ]
                }
            ],
            expected_outcomes=['data_exists:test_data'],
            cleanup_steps=[]
        )
        
        result = await framework.run_scenario(scenario)
        
        assert result.success is True
        assert result.steps_completed == 2
        assert result.total_steps == 2
        assert result.error_message is None
        assert 'test_data' in result.artifacts
    
    @pytest.mark.asyncio
    async def test_scenario_execution_failure(self, framework, mock_session):
        """Test scenario execution with failure"""
        framework.session = mock_session
        
        # Mock a failed API response
        mock_session.get.return_value.status_code = 500
        
        scenario = TestScenario(
            name="Failing Scenario",
            description="A scenario that should fail",
            steps=[
                {
                    'type': 'api_call',
                    'method': 'GET',
                    'endpoint': '/test',
                    'expected_status': 200  # This will fail
                }
            ],
            expected_outcomes=[],
            cleanup_steps=[]
        )
        
        result = await framework.run_scenario(scenario)
        
        assert result.success is False
        assert result.steps_completed == 0
        assert result.error_message is not None
        assert "Expected status 200, got 500" in result.error_message


class TestEndToEndScenarios:
    """Test the predefined end-to-end scenarios"""
    
    def test_complete_trading_workflow_scenario(self):
        """Test the complete trading workflow scenario structure"""
        scenario = EndToEndTestScenarios.complete_trading_workflow()
        
        assert scenario.name == "Complete Trading Workflow"
        assert len(scenario.steps) > 0
        assert len(scenario.expected_outcomes) > 0
        assert len(scenario.cleanup_steps) > 0
        
        # Verify key steps are present
        step_names = [step.get('name', '') for step in scenario.steps]
        assert any('Authentication' in name for name in step_names)
        assert any('Strategy' in name for name in step_names)
        assert any('Order' in name for name in step_names)
    
    def test_real_time_data_flow_scenario(self):
        """Test the real-time data flow scenario structure"""
        scenario = EndToEndTestScenarios.real_time_data_flow()
        
        assert scenario.name == "Real-time Data Flow"
        assert len(scenario.steps) > 0
        
        # Should have WebSocket steps
        websocket_steps = [step for step in scenario.steps if step.get('type') == 'websocket']
        assert len(websocket_steps) > 0
    
    def test_portfolio_management_workflow_scenario(self):
        """Test the portfolio management workflow scenario"""
        scenario = EndToEndTestScenarios.portfolio_management_workflow()
        
        assert scenario.name == "Portfolio Management Workflow"
        assert len(scenario.steps) > 0
        
        # Should have portfolio and risk management steps
        endpoints = [step.get('endpoint', '') for step in scenario.steps]
        assert any('/portfolio' in endpoint for endpoint in endpoints)
        assert any('/risk' in endpoint for endpoint in endpoints)
    
    def test_error_handling_scenario(self):
        """Test the error handling scenario"""
        scenario = EndToEndTestScenarios.error_handling_and_recovery()
        
        assert scenario.name == "Error Handling and Recovery"
        assert len(scenario.steps) > 0
        
        # Should test various error conditions
        expected_statuses = [step.get('expected_status') for step in scenario.steps]
        assert 401 in expected_statuses  # Unauthorized
        assert 422 in expected_statuses  # Validation error


class TestDataConsistencyValidator:
    """Test the data consistency validation framework"""
    
    @pytest.fixture
    def mock_api_client(self):
        """Create a mock API client"""
        client = Mock()
        
        # Mock portfolio data
        client.get = AsyncMock()
        client.post = AsyncMock()
        client.put = AsyncMock()
        client.delete = AsyncMock()
        
        return client
    
    @pytest.fixture
    def validator(self, mock_api_client):
        """Create a data consistency validator"""
        return DataConsistencyValidator(mock_api_client)
    
    @pytest.mark.asyncio
    async def test_portfolio_consistency_validation_success(self, validator, mock_api_client):
        """Test successful portfolio consistency validation"""
        # Mock consistent portfolio data
        mock_api_client.get.side_effect = [
            # Portfolio summary
            {
                'total_value': 110000.0,
                'cash': 10000.0,
                'daily_pnl': 1000.0
            },
            # Positions data
            {
                'positions': [
                    {
                        'symbol': 'AAPL',
                        'market_value': 50000.0,
                        'unrealized_pnl': 500.0
                    },
                    {
                        'symbol': 'GOOGL',
                        'market_value': 50000.0,
                        'unrealized_pnl': 500.0
                    }
                ]
            },
            # Performance data
            {
                'total_return': 0.1,
                'sharpe_ratio': 1.2
            }
        ]
        
        result = await validator.validate_portfolio_consistency()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_portfolio_consistency_validation_failure(self, validator, mock_api_client):
        """Test portfolio consistency validation failure"""
        # Mock inconsistent portfolio data
        mock_api_client.get.side_effect = [
            # Portfolio summary
            {
                'total_value': 110000.0,  # This doesn't match calculated total
                'cash': 10000.0,
                'daily_pnl': 1000.0
            },
            # Positions data
            {
                'positions': [
                    {
                        'symbol': 'AAPL',
                        'market_value': 60000.0,  # Total would be 120000 + 10000 = 130000
                        'unrealized_pnl': 500.0
                    },
                    {
                        'symbol': 'GOOGL',
                        'market_value': 60000.0,
                        'unrealized_pnl': 500.0
                    }
                ]
            },
            # Performance data
            {
                'total_return': 0.1,
                'sharpe_ratio': 1.2
            }
        ]
        
        result = await validator.validate_portfolio_consistency()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_order_lifecycle_consistency(self, validator, mock_api_client):
        """Test order lifecycle consistency validation"""
        order_id = "test-order-123"
        
        mock_api_client.post.return_value = {'id': order_id}
        mock_api_client.get.side_effect = [
            # Orders list
            {
                'orders': [
                    {
                        'id': order_id,
                        'symbol': 'AAPL',
                        'side': 'buy',
                        'quantity': 10,
                        'price': 150.0
                    }
                ]
            },
            # Order details
            {
                'id': order_id,
                'symbol': 'AAPL',
                'side': 'buy',
                'quantity': 10,
                'price': 150.0,
                'status': 'pending'
            }
        ]
        
        result = await validator.validate_order_lifecycle_consistency()
        assert result is True


class TestIntegrationTestAutomation:
    """Test the integration test automation framework"""
    
    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config = {
                'test_suites': [],
                'notifications': {'email': {'enabled': False}},
                'reporting': {'output_dir': 'test_reports'},
                'execution': {'parallel_limit': 2, 'default_timeout': 60}
            }
            import yaml
            yaml.dump(config, f)
            yield f.name
        
        # Cleanup
        os.unlink(f.name)
    
    @pytest.fixture
    def automation(self, temp_config_file):
        """Create automation framework instance"""
        return IntegrationTestAutomation(temp_config_file)
    
    def test_automation_initialization(self, automation):
        """Test automation framework initialization"""
        assert automation.config is not None
        assert 'test_suites' in automation.config
        assert 'notifications' in automation.config
        assert 'reporting' in automation.config
        assert 'execution' in automation.config
    
    def test_test_registration(self, automation):
        """Test test function registration"""
        async def dummy_test(context):
            return {'result': 'success'}
        
        automation.register_test('test_dummy', dummy_test, {'name': 'Dummy Test'})
        
        assert 'test_dummy' in automation.test_registry
        assert automation.test_registry['test_dummy']['function'] == dummy_test
        assert automation.test_registry['test_dummy']['metadata']['name'] == 'Dummy Test'
    
    def test_test_suite_registration(self, automation):
        """Test test suite registration"""
        suite = TestSuite(
            name="test_suite",
            description="A test suite",
            tests=["test1", "test2"]
        )
        
        automation.register_test_suite(suite)
        
        assert len(automation.config['test_suites']) == 1
        assert automation.config['test_suites'][0]['name'] == "test_suite"
    
    @pytest.mark.asyncio
    async def test_single_test_execution_success(self, automation):
        """Test successful single test execution"""
        async def successful_test(context):
            await asyncio.sleep(0.01)  # Simulate work
            return {'status': 'passed'}
        
        automation.register_test('test_success', successful_test)
        
        execution = await automation.execute_test('test_success')
        
        assert execution.status == TestStatus.PASSED
        assert execution.error_message is None
        assert execution.artifacts is not None
        assert execution.duration > 0
    
    @pytest.mark.asyncio
    async def test_single_test_execution_failure(self, automation):
        """Test failed single test execution"""
        async def failing_test(context):
            raise ValueError("Test failure")
        
        automation.register_test('test_failure', failing_test)
        
        execution = await automation.execute_test('test_failure')
        
        assert execution.status == TestStatus.FAILED
        assert "Test failure" in execution.error_message
        assert execution.duration > 0
    
    @pytest.mark.asyncio
    async def test_single_test_execution_timeout(self, automation):
        """Test test execution timeout"""
        async def slow_test(context):
            await asyncio.sleep(2)  # Longer than timeout
            return {'status': 'passed'}
        
        automation.register_test('test_timeout', slow_test)
        automation.config['execution']['default_timeout'] = 0.1  # Very short timeout
        
        execution = await automation.execute_test('test_timeout')
        
        assert execution.status == TestStatus.TIMEOUT
        assert "timed out" in execution.error_message.lower()
    
    def test_test_metrics_calculation(self, automation):
        """Test test metrics calculation"""
        # Add some test history
        automation.test_history = [
            TestExecution(
                test_id="test1",
                test_name="Test 1",
                start_time=datetime.now() - timedelta(hours=1),
                end_time=datetime.now() - timedelta(hours=1) + timedelta(seconds=10),
                status=TestStatus.PASSED,
                duration=10.0
            ),
            TestExecution(
                test_id="test1",
                test_name="Test 1",
                start_time=datetime.now() - timedelta(minutes=30),
                end_time=datetime.now() - timedelta(minutes=30) + timedelta(seconds=15),
                status=TestStatus.FAILED,
                duration=15.0,
                error_message="Test failed"
            ),
            TestExecution(
                test_id="test2",
                test_name="Test 2",
                start_time=datetime.now() - timedelta(minutes=10),
                end_time=datetime.now() - timedelta(minutes=10) + timedelta(seconds=5),
                status=TestStatus.PASSED,
                duration=5.0
            )
        ]
        
        # Test metrics for specific test
        metrics = automation.get_test_metrics("test1")
        
        assert metrics['total_executions'] == 2
        assert metrics['success_rate'] == 50.0
        assert metrics['failure_rate'] == 50.0
        assert metrics['average_duration'] == 12.5
        assert metrics['min_duration'] == 10.0
        assert metrics['max_duration'] == 15.0
        
        # Test metrics for all tests
        all_metrics = automation.get_test_metrics()
        assert all_metrics['total_executions'] == 3


class TestIntegrationTestRunner:
    """Test the integration test runner"""
    
    @pytest.fixture
    def runner(self):
        """Create test runner instance"""
        return IntegrationTestRunner({
            'base_url': 'http://test-server:8000',
            'websocket_url': 'ws://test-server:8000/ws'
        })
    
    def test_runner_initialization(self, runner):
        """Test runner initialization"""
        assert runner.framework is not None
        assert runner.results == []
        assert runner.config is not None
    
    def test_report_generation_empty(self, runner):
        """Test report generation with no results"""
        report = runner.generate_report()
        
        assert report['summary']['total_tests'] == 0
        assert report['summary']['passed'] == 0
        assert report['summary']['failed'] == 0
        assert report['summary']['success_rate'] == 0
        assert len(report['results']) == 0
        assert len(report['failed_scenarios']) == 0
    
    def test_report_generation_with_results(self, runner):
        """Test report generation with test results"""
        # Add some mock results
        runner.results = [
            TestResult(
                scenario_name="Test 1",
                success=True,
                duration=10.0,
                steps_completed=3,
                total_steps=3
            ),
            TestResult(
                scenario_name="Test 2",
                success=False,
                duration=5.0,
                steps_completed=1,
                total_steps=2,
                error_message="Test failed"
            )
        ]
        
        report = runner.generate_report()
        
        assert report['summary']['total_tests'] == 2
        assert report['summary']['passed'] == 1
        assert report['summary']['failed'] == 1
        assert report['summary']['success_rate'] == 50.0
        assert report['summary']['total_duration'] == 15.0
        assert report['summary']['average_duration'] == 7.5
        
        assert len(report['results']) == 2
        assert len(report['failed_scenarios']) == 1
        assert report['failed_scenarios'][0]['scenario'] == "Test 2"


# Integration test for the entire framework
class TestFrameworkIntegration:
    """Integration tests for the entire testing framework"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_framework_workflow(self):
        """Test the complete framework workflow"""
        # Create a mock API server response
        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'access_token': 'test-token',
                'id': 'test-id-123'
            }
            mock_session.post.return_value = mock_response
            mock_session.get.return_value = mock_response
            mock_session.delete.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            # Create framework and run a simple scenario
            framework = IntegrationTestFramework()
            
            scenario = TestScenario(
                name="Integration Test",
                description="Test framework integration",
                steps=[
                    {
                        'type': 'api_call',
                        'name': 'Login',
                        'method': 'POST',
                        'endpoint': '/auth/login',
                        'data': {'username': 'test', 'password': 'test'},
                        'expected_status': 200,
                        'store_response': 'auth'
                    },
                    {
                        'type': 'api_call',
                        'name': 'Create Resource',
                        'method': 'POST',
                        'endpoint': '/resource',
                        'headers': {'Authorization': 'Bearer ${auth.access_token}'},
                        'data': {'name': 'test resource'},
                        'expected_status': 200,
                        'store_response': 'resource'
                    }
                ],
                expected_outcomes=['data_exists:auth', 'data_exists:resource'],
                cleanup_steps=[
                    {
                        'type': 'api_call',
                        'name': 'Cleanup',
                        'method': 'DELETE',
                        'endpoint': '/resource/${resource.id}',
                        'headers': {'Authorization': 'Bearer ${auth.access_token}'},
                        'expected_status': 200
                    }
                ]
            )
            
            result = await framework.run_scenario(scenario)
            
            # Verify the test completed successfully
            assert result.success is True
            assert result.steps_completed == 2
            assert 'auth' in result.artifacts
            assert 'resource' in result.artifacts
            
            # Verify API calls were made correctly
            assert mock_session.post.call_count >= 2  # Login + Create
            assert mock_session.delete.call_count >= 1  # Cleanup


# Test runner for the integration framework tests
def run_integration_framework_tests():
    """Run all integration framework tests"""
    print("🧪 Running Integration Framework Tests")
    print("=" * 50)
    
    # Run pytest on this file
    import subprocess
    result = subprocess.run([
        'python', '-m', 'pytest', __file__, '-v', '--tb=short'
    ], capture_output=True, text=True)
    
    print("STDOUT:")
    print(result.stdout)
    
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    success = result.returncode == 0
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All Integration Framework Tests Passed!")
    else:
        print("❌ Some Integration Framework Tests Failed!")
    
    return success


if __name__ == "__main__":
    success = run_integration_framework_tests()
    exit(0 if success else 1)