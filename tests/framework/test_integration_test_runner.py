#!/usr/bin/env python3
"""
Test suite for IntegrationTestRunner

This module contains comprehensive tests for the IntegrationTestRunner class,
validating all integration testing functionality including data flow testing,
message passing, database integration, API integration, and failure recovery.
"""

import asyncio
import pytest
import pytest_asyncio
import time
import uuid
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

# Import the classes to test
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from integration_test_runner import (
    IntegrationTestRunner,
    IntegrationTestCase,
    IntegrationTestResult,
    IntegrationTestSuiteResult,
    IntegrationTestType,
    IntegrationTestStatus,
    IntegrationPointType,
    DataFlowValidation,
    MessagePassingValidation,
    IntegrationDatabaseManager,
    IntegrationMessageManager,
    IntegrationAPIManager,
    DataFlowTracker,
    MessagePassingTracker
)


class TestIntegrationTestRunner:
    """Test cases for IntegrationTestRunner class"""
    
    @pytest.fixture
    def runner(self):
        """Create an IntegrationTestRunner instance for testing"""
        config = {
            'test_database_path': ':memory:',
            'test_redis_host': 'localhost',
            'test_redis_port': 6379,
            'default_timeout': 30
        }
        return IntegrationTestRunner(config)
    
    @pytest.fixture
    def sample_test_case(self):
        """Create a sample test case for testing"""
        async def sample_test():
            return {'test_result': 'success'}
        
        return IntegrationTestCase(
            test_id='test_001',
            test_name='Sample Integration Test',
            test_type=IntegrationTestType.MODULE_BOUNDARY,
            description='A sample test case',
            modules_under_test=['module_a', 'module_b'],
            integration_points=[IntegrationPointType.INTERNAL_MODULE],
            test_function=sample_test
        )
    
    def test_initialization(self, runner):
        """Test IntegrationTestRunner initialization"""
        assert runner is not None
        assert runner.config is not None
        assert runner.logger is not None
        assert isinstance(runner.test_cases, dict)
        assert isinstance(runner.test_results, dict)
        assert isinstance(runner.suite_results, list)
        assert runner.test_database_path == ':memory:'
        assert runner.test_redis_host == 'localhost'
        assert runner.test_redis_port == 6379
        assert runner.test_timeout == 30
    
    def test_register_test_case(self, runner, sample_test_case):
        """Test registering a test case"""
        runner.register_test_case(sample_test_case)
        
        assert sample_test_case.test_id in runner.test_cases
        assert runner.test_cases[sample_test_case.test_id] == sample_test_case
    
    def test_register_data_flow_test(self, runner):
        """Test registering a data flow test"""
        def transform1(data):
            data['step1'] = 'completed'
            return data
        
        def transform2(data):
            data['step2'] = 'completed'
            return data
        
        validation_criteria = {
            'required_fields': ['step1', 'step2'],
            'expected_types': {'step1': str, 'step2': str}
        }
        
        test_id = runner.register_data_flow_test(
            'Data Flow Test',
            'source_module',
            'target_module',
            [transform1, transform2],
            validation_criteria
        )
        
        assert test_id in runner.test_cases
        test_case = runner.test_cases[test_id]
        assert test_case.test_type == IntegrationTestType.DATA_FLOW
        assert 'source_module' in test_case.modules_under_test
        assert 'target_module' in test_case.modules_under_test
        assert IntegrationPointType.INTERNAL_MODULE in test_case.integration_points
    
    def test_register_message_passing_test(self, runner):
        """Test registering a message passing test"""
        message_content = {'type': 'order', 'symbol': 'AAPL', 'quantity': 100}
        
        test_id = runner.register_message_passing_test(
            'Message Passing Test',
            'sender_module',
            'receiver_module',
            'order_message',
            message_content
        )
        
        assert test_id in runner.test_cases
        test_case = runner.test_cases[test_id]
        assert test_case.test_type == IntegrationTestType.MESSAGE_PASSING
        assert 'sender_module' in test_case.modules_under_test
        assert 'receiver_module' in test_case.modules_under_test
        assert IntegrationPointType.MESSAGE_QUEUE in test_case.integration_points
    
    def test_register_database_integration_test(self, runner):
        """Test registering a database integration test"""
        test_data = {'id': 1, 'name': 'test_record', 'value': 100.0}
        operations = ['create', 'read', 'update', 'delete']
        
        test_id = runner.register_database_integration_test(
            'Database Integration Test',
            'data_module',
            operations,
            test_data
        )
        
        assert test_id in runner.test_cases
        test_case = runner.test_cases[test_id]
        assert test_case.test_type == IntegrationTestType.DATABASE_INTEGRATION
        assert 'data_module' in test_case.modules_under_test
        assert IntegrationPointType.DATABASE in test_case.integration_points
    
    def test_register_api_integration_test(self, runner):
        """Test registering an API integration test"""
        endpoints = ['/api/orders', '/api/positions']
        requests = [
            {'method': 'POST', 'data': {'symbol': 'AAPL', 'quantity': 100}},
            {'method': 'GET', 'params': {'account_id': '12345'}}
        ]
        
        test_id = runner.register_api_integration_test(
            'API Integration Test',
            'api_module',
            endpoints,
            requests
        )
        
        assert test_id in runner.test_cases
        test_case = runner.test_cases[test_id]
        assert test_case.test_type == IntegrationTestType.API_INTEGRATION
        assert 'api_module' in test_case.modules_under_test
        assert IntegrationPointType.API_ENDPOINT in test_case.integration_points
    
    def test_register_failure_recovery_test(self, runner):
        """Test registering a failure recovery test"""
        modules = ['module_a', 'module_b', 'module_c']
        failure_scenarios = [
            {'name': 'network_failure', 'type': 'network', 'affected_modules': ['module_a']},
            {'name': 'database_failure', 'type': 'database', 'affected_modules': ['module_b']}
        ]
        recovery_validation = {
            'max_recovery_time': 30,
            'data_integrity_required': True
        }
        
        test_id = runner.register_failure_recovery_test(
            'Failure Recovery Test',
            modules,
            failure_scenarios,
            recovery_validation
        )
        
        assert test_id in runner.test_cases
        test_case = runner.test_cases[test_id]
        assert test_case.test_type == IntegrationTestType.FAILURE_RECOVERY
        assert all(module in test_case.modules_under_test for module in modules)
        assert IntegrationPointType.INTERNAL_MODULE in test_case.integration_points
    
    @pytest.mark.asyncio
    async def test_execute_test_case_success(self, runner, sample_test_case):
        """Test successful execution of a test case"""
        runner.register_test_case(sample_test_case)
        
        result = await runner.execute_test_case(sample_test_case.test_id)
        
        assert result.status == IntegrationTestStatus.PASSED
        assert result.test_case == sample_test_case
        assert result.duration > 0
        assert result.error_message is None
        assert result.stack_trace is None
    
    @pytest.mark.asyncio
    async def test_execute_test_case_failure(self, runner):
        """Test execution of a failing test case"""
        async def failing_test():
            raise ValueError("Test failure")
        
        test_case = IntegrationTestCase(
            test_id='failing_test',
            test_name='Failing Test',
            test_type=IntegrationTestType.MODULE_BOUNDARY,
            description='A test that fails',
            modules_under_test=['module_a'],
            integration_points=[IntegrationPointType.INTERNAL_MODULE],
            test_function=failing_test
        )
        
        runner.register_test_case(test_case)
        result = await runner.execute_test_case(test_case.test_id)
        
        assert result.status == IntegrationTestStatus.FAILED
        assert result.error_message == "Test failure"
        assert result.stack_trace is not None
    
    @pytest.mark.asyncio
    async def test_execute_test_case_timeout(self, runner):
        """Test execution of a test case that times out"""
        async def slow_test():
            await asyncio.sleep(2)  # Sleep longer than timeout
            return {'result': 'success'}
        
        test_case = IntegrationTestCase(
            test_id='slow_test',
            test_name='Slow Test',
            test_type=IntegrationTestType.MODULE_BOUNDARY,
            description='A test that times out',
            modules_under_test=['module_a'],
            integration_points=[IntegrationPointType.INTERNAL_MODULE],
            test_function=slow_test,
            timeout_seconds=1  # Short timeout
        )
        
        runner.register_test_case(test_case)
        result = await runner.execute_test_case(test_case.test_id)
        
        assert result.status == IntegrationTestStatus.TIMEOUT
        assert "timed out" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_execute_test_suite(self, runner):
        """Test execution of a test suite"""
        # Create multiple test cases
        async def test1():
            return {'result': 'test1_success'}
        
        async def test2():
            return {'result': 'test2_success'}
        
        async def test3():
            raise ValueError("Test3 failed")
        
        test_cases = [
            IntegrationTestCase(
                test_id='test1',
                test_name='Test 1',
                test_type=IntegrationTestType.MODULE_BOUNDARY,
                description='First test',
                modules_under_test=['module_a'],
                integration_points=[IntegrationPointType.INTERNAL_MODULE],
                test_function=test1
            ),
            IntegrationTestCase(
                test_id='test2',
                test_name='Test 2',
                test_type=IntegrationTestType.DATA_FLOW,
                description='Second test',
                modules_under_test=['module_b'],
                integration_points=[IntegrationPointType.INTERNAL_MODULE],
                test_function=test2
            ),
            IntegrationTestCase(
                test_id='test3',
                test_name='Test 3',
                test_type=IntegrationTestType.MESSAGE_PASSING,
                description='Third test',
                modules_under_test=['module_c'],
                integration_points=[IntegrationPointType.MESSAGE_QUEUE],
                test_function=test3
            )
        ]
        
        for test_case in test_cases:
            runner.register_test_case(test_case)
        
        suite_result = await runner.execute_test_suite(
            'Test Suite',
            ['test1', 'test2', 'test3'],
            parallel_execution=False
        )
        
        assert suite_result.suite_name == 'Test Suite'
        assert suite_result.total_tests == 3
        assert suite_result.passed_tests == 2
        assert suite_result.failed_tests == 1
        assert suite_result.pass_rate == 2/3 * 100
        assert len(suite_result.test_results) == 3
    
    @pytest.mark.asyncio
    async def test_data_flow_execution(self, runner):
        """Test data flow test execution"""
        def transform1(data):
            data['transformed'] = True
            return data
        
        def transform2(data):
            data['final'] = 'processed'
            return data
        
        validation_criteria = {
            'required_fields': ['transformed', 'final'],
            'expected_types': {'transformed': bool, 'final': str}
        }
        
        result = await runner._execute_data_flow_test(
            'source_module',
            'target_module',
            [transform1, transform2],
            validation_criteria
        )
        
        assert 'data_flow_validation' in result
        assert 'performance_metrics' in result
        
        flow_validation = result['data_flow_validation']
        assert flow_validation['validation_passed'] == True
        assert len(flow_validation['data_transformations']) == 2
        assert flow_validation['source_module'] == 'source_module'
        assert flow_validation['target_module'] == 'target_module'
    
    @pytest.mark.asyncio
    async def test_message_passing_execution(self, runner):
        """Test message passing test execution"""
        message_content = {'type': 'order', 'symbol': 'AAPL'}
        
        result = await runner._execute_message_passing_test(
            'sender_module',
            'receiver_module',
            'order_message',
            message_content
        )
        
        assert 'message_passing_validation' in result
        assert 'performance_metrics' in result
        
        validation = result['message_passing_validation']
        assert validation['message_type'] == 'order_message'
        assert validation['sender_module'] == 'sender_module'
        assert validation['receiver_module'] == 'receiver_module'
        assert validation['delivery_confirmed'] == True
        assert validation['processing_confirmed'] == True
        assert validation['response_received'] == True
    
    @pytest.mark.asyncio
    async def test_database_integration_execution(self, runner):
        """Test database integration test execution"""
        test_data = {'id': 1, 'name': 'test', 'value': 100.0}
        operations = ['create', 'read', 'update', 'delete']
        
        result = await runner._execute_database_integration_test(
            'data_module',
            operations,
            test_data
        )
        
        assert 'integration_point_results' in result
        assert 'performance_metrics' in result
        
        results = result['integration_point_results']
        assert all(op in results for op in operations)
        assert all(results[op]['success'] for op in operations)
        
        metrics = result['performance_metrics']
        assert all(f'{op}_time_ms' in metrics for op in operations)
    
    @pytest.mark.asyncio
    async def test_api_integration_execution(self, runner):
        """Test API integration test execution"""
        endpoints = ['/api/test1', '/api/test2']
        requests = [
            {'method': 'GET', 'params': {}},
            {'method': 'POST', 'data': {'test': 'data'}}
        ]
        
        result = await runner._execute_api_integration_test(
            'api_module',
            endpoints,
            requests
        )
        
        assert 'integration_point_results' in result
        assert 'performance_metrics' in result
        
        results = result['integration_point_results']
        assert all(endpoint in results for endpoint in endpoints)
        assert all(results[endpoint]['success'] for endpoint in endpoints)
        
        metrics = result['performance_metrics']
        assert 'endpoint_0_response_time_ms' in metrics
        assert 'endpoint_1_response_time_ms' in metrics
    
    @pytest.mark.asyncio
    async def test_failure_recovery_execution(self, runner):
        """Test failure recovery test execution"""
        modules = ['module_a', 'module_b']
        failure_scenarios = [
            {'name': 'network_failure', 'type': 'network'},
            {'name': 'database_failure', 'type': 'database'}
        ]
        recovery_validation = {'max_recovery_time': 30}
        
        result = await runner._execute_failure_recovery_test(
            modules,
            failure_scenarios,
            recovery_validation
        )
        
        assert 'recovery_validation' in result
        assert 'performance_metrics' in result
        
        recovery_results = result['recovery_validation']
        assert 'network_failure' in recovery_results
        assert 'database_failure' in recovery_results
        
        for scenario_result in recovery_results.values():
            assert 'failure_simulated' in scenario_result
            assert 'recovery_successful' in scenario_result
            assert 'recovery_time_seconds' in scenario_result
            assert 'data_integrity_maintained' in scenario_result
    
    def test_data_flow_validation(self, runner):
        """Test data flow result validation"""
        test_data = {
            'field1': 'value1',
            'field2': 42,
            'field3': 3.14
        }
        
        validation_criteria = {
            'required_fields': ['field1', 'field2'],
            'expected_types': {'field1': str, 'field2': int},
            'value_ranges': {'field2': (0, 100)}
        }
        
        result = runner._validate_data_flow_result(test_data, validation_criteria)
        
        assert result['passed'] == True
        assert len(result['errors']) == 0
        assert result['integrity_check'] == True
    
    def test_data_flow_validation_failure(self, runner):
        """Test data flow validation with failures"""
        test_data = {
            'field1': 'value1',
            'field2': 'wrong_type',  # Should be int
            'field3': 150  # Out of range
        }
        
        validation_criteria = {
            'required_fields': ['field1', 'field2', 'missing_field'],
            'expected_types': {'field1': str, 'field2': int},
            'value_ranges': {'field3': (0, 100)}
        }
        
        result = runner._validate_data_flow_result(test_data, validation_criteria)
        
        assert result['passed'] == False
        assert len(result['errors']) > 0
        assert any('missing_field' in error for error in result['errors'])
        assert any('wrong type' in error for error in result['errors'])
        assert any('not in range' in error for error in result['errors'])
    
    def test_generate_comprehensive_report(self, runner):
        """Test comprehensive report generation"""
        # Create sample test results
        start_time = datetime.now()
        end_time = datetime.now()
        
        test_results = [
            IntegrationTestResult(
                test_case=IntegrationTestCase(
                    test_id='test1',
                    test_name='Test 1',
                    test_type=IntegrationTestType.DATA_FLOW,
                    description='Data flow test',
                    modules_under_test=['module_a'],
                    integration_points=[IntegrationPointType.INTERNAL_MODULE],
                    test_function=lambda: None
                ),
                status=IntegrationTestStatus.PASSED,
                start_time=start_time,
                end_time=end_time,
                duration=1.5
            ),
            IntegrationTestResult(
                test_case=IntegrationTestCase(
                    test_id='test2',
                    test_name='Test 2',
                    test_type=IntegrationTestType.MESSAGE_PASSING,
                    description='Message passing test',
                    modules_under_test=['module_b'],
                    integration_points=[IntegrationPointType.MESSAGE_QUEUE],
                    test_function=lambda: None
                ),
                status=IntegrationTestStatus.FAILED,
                start_time=start_time,
                end_time=end_time,
                duration=2.0,
                error_message='Test failed'
            )
        ]
        
        suite_result = IntegrationTestSuiteResult(
            suite_name='Test Suite',
            start_time=start_time,
            end_time=end_time,
            total_duration=3.5,
            total_tests=2,
            passed_tests=1,
            failed_tests=1,
            error_tests=0,
            skipped_tests=0,
            timeout_tests=0,
            pass_rate=50.0,
            test_results=test_results,
            recommendations=['Fix failed test']
        )
        
        report = runner.generate_comprehensive_report(suite_result)
        
        assert 'INTEGRATION TEST SUITE REPORT' in report
        assert 'Test Suite' in report
        assert 'Total Tests: 2' in report
        assert 'Passed: 1' in report
        assert 'Failed: 1' in report
        assert 'Pass Rate: 50.0%' in report
        assert 'FAILED TESTS' in report
        assert 'Test 2' in report
        assert 'RECOMMENDATIONS' in report
        assert 'Fix failed test' in report


class TestIntegrationDatabaseManager:
    """Test cases for IntegrationDatabaseManager"""
    
    def test_initialization(self):
        """Test database manager initialization"""
        manager = IntegrationDatabaseManager(':memory:')
        assert manager.database_path == ':memory:'
        assert manager.connection is None
    
    def test_get_test_transaction(self):
        """Test getting a test transaction"""
        manager = IntegrationDatabaseManager(':memory:')
        
        with manager.get_test_transaction() as conn:
            assert conn is not None
            # Test that we can execute SQL
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE test (id INTEGER)')
            cursor.execute('INSERT INTO test (id) VALUES (1)')
            
            # Verify data exists within transaction
            cursor.execute('SELECT COUNT(*) FROM test')
            count = cursor.fetchone()[0]
            assert count == 1
        
        # After transaction, data should be rolled back
        with manager.get_test_transaction() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('SELECT COUNT(*) FROM test')
                # Should fail because table was rolled back
                assert False, "Table should not exist after rollback"
            except Exception:
                # Expected - table doesn't exist
                pass


class TestIntegrationMessageManager:
    """Test cases for IntegrationMessageManager"""
    
    def test_initialization(self):
        """Test message manager initialization"""
        manager = IntegrationMessageManager('localhost', 6379)
        assert manager.redis_host == 'localhost'
        assert manager.redis_port == 6379
        assert manager.redis_client is None
    
    @pytest.mark.asyncio
    async def test_send_message(self):
        """Test sending a message"""
        manager = IntegrationMessageManager('localhost', 6379)
        
        result = await manager.send_message(
            'sender', 'receiver', 'test_message', {'data': 'test'}
        )
        
        assert result['success'] == True
        assert 'message_id' in result
        assert 'delivery_time_ms' in result
    
    @pytest.mark.asyncio
    async def test_wait_for_processing_confirmation(self):
        """Test waiting for processing confirmation"""
        manager = IntegrationMessageManager('localhost', 6379)
        
        result = await manager.wait_for_processing_confirmation('test_message_id', 10)
        
        assert result['success'] == True
        assert 'processing_time_ms' in result
    
    @pytest.mark.asyncio
    async def test_wait_for_response(self):
        """Test waiting for response"""
        manager = IntegrationMessageManager('localhost', 6379)
        
        result = await manager.wait_for_response('test_message_id', 10)
        
        assert result['success'] == True
        assert 'response_data' in result


class TestIntegrationAPIManager:
    """Test cases for IntegrationAPIManager"""
    
    @pytest.mark.asyncio
    async def test_make_test_request(self):
        """Test making a test API request"""
        manager = IntegrationAPIManager()
        
        result = await manager.make_test_request(
            '/api/test', {'method': 'GET', 'params': {}}
        )
        
        assert result['status_code'] == 200
        assert 'data' in result
        assert result['data']['result'] == 'success'
        assert result['data']['endpoint'] == '/api/test'


class TestDataFlowTracker:
    """Test cases for DataFlowTracker"""
    
    def test_flow_tracking(self):
        """Test data flow tracking"""
        tracker = DataFlowTracker()
        
        flow_id = tracker.start_flow_tracking('source', 'target')
        assert flow_id in tracker.active_flows
        assert tracker.active_flows[flow_id]['source'] == 'source'
        assert tracker.active_flows[flow_id]['target'] == 'target'
        assert 'start_time' in tracker.active_flows[flow_id]
        
        tracker.end_flow_tracking(flow_id)
        assert 'end_time' in tracker.active_flows[flow_id]


class TestMessagePassingTracker:
    """Test cases for MessagePassingTracker"""
    
    def test_message_tracking(self):
        """Test message passing tracking"""
        tracker = MessagePassingTracker()
        
        message_id = tracker.start_message_tracking('sender', 'receiver', 'test_type')
        assert message_id in tracker.active_messages
        assert tracker.active_messages[message_id]['sender'] == 'sender'
        assert tracker.active_messages[message_id]['receiver'] == 'receiver'
        assert tracker.active_messages[message_id]['message_type'] == 'test_type'
        assert 'start_time' in tracker.active_messages[message_id]
        
        tracker.end_message_tracking(message_id)
        assert 'end_time' in tracker.active_messages[message_id]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])