#!/usr/bin/env python3
"""
Recovery Test Runner for Algorithmic Trading System

This module implements comprehensive recovery testing functionality that validates
system behavior and recovery capabilities after various failure scenarios.

Key Features:
- System crash recovery testing
- Data corruption recovery testing
- Network failure recovery testing
- Database failure recovery testing
- Service failure recovery testing
- Graceful degradation testing
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
from typing import Any, Dict, List, Optional, Tuple, Union, Callable, Set
from unittest.mock import Mock, patch, MagicMock
import random
import shutil
import tempfile

# Testing framework imports
import pytest
import pytest_asyncio


class RecoveryTestType(Enum):
    """Types of recovery tests supported"""
    SYSTEM_CRASH = "system_crash"
    DATA_CORRUPTION = "data_corruption"
    NETWORK_FAILURE = "network_failure"
    DATABASE_FAILURE = "database_failure"
    SERVICE_FAILURE = "service_failure"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    DISASTER_RECOVERY = "disaster_recovery"


class FailureType(Enum):
    """Types of failures to simulate"""
    HARDWARE_FAILURE = "hardware_failure"
    SOFTWARE_CRASH = "software_crash"
    NETWORK_PARTITION = "network_partition"
    DATABASE_CORRUPTION = "database_corruption"
    SERVICE_UNAVAILABLE = "service_unavailable"
    POWER_OUTAGE = "power_outage"
    MEMORY_EXHAUSTION = "memory_exhaustion"


class RecoveryTestStatus(Enum):
    """Status of recovery test execution"""
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    PARTIAL_RECOVERY = "partial_recovery"
    NO_RECOVERY = "no_recovery"


@dataclass
class RecoveryTestCase:
    """Represents a single recovery test case"""
    test_id: str
    test_name: str
    recovery_type: RecoveryTestType
    failure_scenarios: List[FailureType]
    test_function: Callable
    setup_function: Optional[Callable] = None
    teardown_function: Optional[Callable] = None
    recovery_validation_function: Optional[Callable] = None
    timeout_seconds: int = 60
    recovery_timeout_seconds: int = 120
    expected_recovery_time: float = 30.0  # seconds
    data_integrity_required: bool = True
    skip_conditions: List[str] = field(default_factory=list)


@dataclass
class RecoveryTestResult:
    """Results of a single recovery test"""
    test_case: RecoveryTestCase
    failure_scenario: FailureType
    status: RecoveryTestStatus
    start_time: datetime
    failure_time: datetime
    recovery_start_time: datetime
    end_time: datetime
    total_duration: float
    failure_duration: float
    recovery_duration: float
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    recovery_metrics: Dict[str, Any] = field(default_factory=dict)
    data_integrity_check: bool = True
    service_availability_check: bool = True
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    recovery_steps: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class RecoveryTestSuiteResult:
    """Results of a recovery test suite execution"""
    suite_name: str
    start_time: datetime
    end_time: datetime
    total_duration: float
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int
    skipped_tests: int
    partial_recovery_tests: int
    no_recovery_tests: int
    pass_rate: float
    test_results: List[RecoveryTestResult]
    recovery_summary: Dict[str, Any] = field(default_factory=dict)
    failure_type_summary: Dict[str, Any] = field(default_factory=dict)
    performance_summary: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class RecoveryTestRunner:
    """
    Comprehensive recovery test runner for the algorithmic trading system.
    
    This class orchestrates recovery testing across various failure scenarios,
    validating system behavior and recovery capabilities.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the RecoveryTestRunner.
        
        Args:
            config: Configuration dictionary for recovery testing settings
        """
        self.config = config or {}
        self.logger = self._setup_logging()
        self.test_cases: Dict[str, RecoveryTestCase] = {}
        self.test_results: Dict[str, RecoveryTestResult] = {}
        self.suite_results: List[RecoveryTestSuiteResult] = []
        
        # Test environment
        self.test_temp_dir = tempfile.mkdtemp(prefix="recovery_test_")
        self.logger.info(f"Created temporary directory for recovery tests: {self.test_temp_dir}")
        
        # Recovery configuration
        self.default_recovery_timeout = self.config.get('default_recovery_timeout', 120)
        self.default_expected_recovery_time = self.config.get('default_expected_recovery_time', 30.0)
        
        self.logger.info("RecoveryTestRunner initialized")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the recovery test runner"""
        logger = logging.getLogger('RecoveryTestRunner')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def __del__(self):
        """Cleanup temporary directory"""
        try:
            if hasattr(self, 'test_temp_dir') and self.test_temp_dir:
                shutil.rmtree(self.test_temp_dir, ignore_errors=True)
                self.logger.info(f"Cleaned up temporary directory: {self.test_temp_dir}")
        except Exception as e:
            self.logger.warning(f"Failed to cleanup temporary directory: {e}")
    
    def register_test_case(self, test_case: RecoveryTestCase) -> None:
        """
        Register a new recovery test case.
        
        Args:
            test_case: The recovery test case to register
        """
        self.test_cases[test_case.test_id] = test_case
        self.logger.info(f"Registered recovery test case: {test_case.test_name}")
    
    def register_system_crash_recovery_test(
        self,
        test_name: str,
        failure_scenarios: List[FailureType],
        test_function: Callable,
        recovery_validation_function: Callable,
        expected_recovery_time: float = 30.0
    ) -> str:
        """
        Register a system crash recovery test.
        
        Args:
            test_name: Name of the test
            failure_scenarios: List of failure scenarios to test
            test_function: Function to execute for testing
            recovery_validation_function: Function to validate recovery
            expected_recovery_time: Expected time for recovery in seconds
            
        Returns:
            Test case ID
        """
        test_id = f"system_crash_{uuid.uuid4().hex[:8]}"
        
        test_case = RecoveryTestCase(
            test_id=test_id,
            test_name=test_name,
            recovery_type=RecoveryTestType.SYSTEM_CRASH,
            failure_scenarios=failure_scenarios,
            test_function=test_function,
            recovery_validation_function=recovery_validation_function,
            expected_recovery_time=expected_recovery_time
        )
        
        self.register_test_case(test_case)
        return test_id
    
    def register_data_corruption_recovery_test(
        self,
        test_name: str,
        failure_scenarios: List[FailureType],
        test_function: Callable,
        recovery_validation_function: Callable,
        data_integrity_required: bool = True,
        expected_recovery_time: float = 45.0
    ) -> str:
        """
        Register a data corruption recovery test.
        
        Args:
            test_name: Name of the test
            failure_scenarios: List of failure scenarios to test
            test_function: Function to execute for testing
            recovery_validation_function: Function to validate recovery
            data_integrity_required: Whether data integrity is required after recovery
            expected_recovery_time: Expected time for recovery in seconds
            
        Returns:
            Test case ID
        """
        test_id = f"data_corruption_{uuid.uuid4().hex[:8]}"
        
        test_case = RecoveryTestCase(
            test_id=test_id,
            test_name=test_name,
            recovery_type=RecoveryTestType.DATA_CORRUPTION,
            failure_scenarios=failure_scenarios,
            test_function=test_function,
            recovery_validation_function=recovery_validation_function,
            data_integrity_required=data_integrity_required,
            expected_recovery_time=expected_recovery_time
        )
        
        self.register_test_case(test_case)
        return test_id
    
    def register_network_failure_recovery_test(
        self,
        test_name: str,
        failure_scenarios: List[FailureType],
        test_function: Callable,
        recovery_validation_function: Callable,
        expected_recovery_time: float = 20.0
    ) -> str:
        """
        Register a network failure recovery test.
        
        Args:
            test_name: Name of the test
            failure_scenarios: List of failure scenarios to test
            test_function: Function to execute for testing
            recovery_validation_function: Function to validate recovery
            expected_recovery_time: Expected time for recovery in seconds
            
        Returns:
            Test case ID
        """
        test_id = f"network_failure_{uuid.uuid4().hex[:8]}"
        
        test_case = RecoveryTestCase(
            test_id=test_id,
            test_name=test_name,
            recovery_type=RecoveryTestType.NETWORK_FAILURE,
            failure_scenarios=failure_scenarios,
            test_function=test_function,
            recovery_validation_function=recovery_validation_function,
            expected_recovery_time=expected_recovery_time
        )
        
        self.register_test_case(test_case)
        return test_id
    
    def register_database_failure_recovery_test(
        self,
        test_name: str,
        failure_scenarios: List[FailureType],
        test_function: Callable,
        recovery_validation_function: Callable,
        data_integrity_required: bool = True,
        expected_recovery_time: float = 60.0
    ) -> str:
        """
        Register a database failure recovery test.
        
        Args:
            test_name: Name of the test
            failure_scenarios: List of failure scenarios to test
            test_function: Function to execute for testing
            recovery_validation_function: Function to validate recovery
            data_integrity_required: Whether data integrity is required after recovery
            expected_recovery_time: Expected time for recovery in seconds
            
        Returns:
            Test case ID
        """
        test_id = f"database_failure_{uuid.uuid4().hex[:8]}"
        
        test_case = RecoveryTestCase(
            test_id=test_id,
            test_name=test_name,
            recovery_type=RecoveryTestType.DATABASE_FAILURE,
            failure_scenarios=failure_scenarios,
            test_function=test_function,
            recovery_validation_function=recovery_validation_function,
            data_integrity_required=data_integrity_required,
            expected_recovery_time=expected_recovery_time
        )
        
        self.register_test_case(test_case)
        return test_id
    
    def register_service_failure_recovery_test(
        self,
        test_name: str,
        failure_scenarios: List[FailureType],
        test_function: Callable,
        recovery_validation_function: Callable,
        expected_recovery_time: float = 25.0
    ) -> str:
        """
        Register a service failure recovery test.
        
        Args:
            test_name: Name of the test
            failure_scenarios: List of failure scenarios to test
            test_function: Function to execute for testing
            recovery_validation_function: Function to validate recovery
            expected_recovery_time: Expected time for recovery in seconds
            
        Returns:
            Test case ID
        """
        test_id = f"service_failure_{uuid.uuid4().hex[:8]}"
        
        test_case = RecoveryTestCase(
            test_id=test_id,
            test_name=test_name,
            recovery_type=RecoveryTestType.SERVICE_FAILURE,
            failure_scenarios=failure_scenarios,
            test_function=test_function,
            recovery_validation_function=recovery_validation_function,
            expected_recovery_time=expected_recovery_time
        )
        
        self.register_test_case(test_case)
        return test_id
    
    def register_graceful_degradation_test(
        self,
        test_name: str,
        failure_scenarios: List[FailureType],
        test_function: Callable,
        recovery_validation_function: Callable,
        expected_recovery_time: float = 15.0
    ) -> str:
        """
        Register a graceful degradation test.
        
        Args:
            test_name: Name of the test
            failure_scenarios: List of failure scenarios to test
            test_function: Function to execute for testing
            recovery_validation_function: Function to validate recovery
            expected_recovery_time: Expected time for recovery in seconds
            
        Returns:
            Test case ID
        """
        test_id = f"graceful_degradation_{uuid.uuid4().hex[:8]}"
        
        test_case = RecoveryTestCase(
            test_id=test_id,
            test_name=test_name,
            recovery_type=RecoveryTestType.GRACEFUL_DEGRADATION,
            failure_scenarios=failure_scenarios,
            test_function=test_function,
            recovery_validation_function=recovery_validation_function,
            expected_recovery_time=expected_recovery_time
        )
        
        self.register_test_case(test_case)
        return test_id

    async def execute_test_case(self, test_id: str, failure_scenario: FailureType) -> RecoveryTestResult:
        """
        Execute a single recovery test case.
        
        Args:
            test_id: ID of the test case to execute
            failure_scenario: Specific failure scenario to test
            
        Returns:
            Recovery test result
        """
        if test_id not in self.test_cases:
            raise ValueError(f"Test case {test_id} not found")
        
        test_case = self.test_cases[test_id]
        start_time = datetime.now()
        failure_time = start_time
        recovery_start_time = start_time
        end_time = start_time
        
        self.logger.info(f"Executing recovery test: {test_case.test_name} with {failure_scenario.value}")
        
        # Check if this failure scenario is supported by the test
        if failure_scenario not in test_case.failure_scenarios:
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            result = RecoveryTestResult(
                test_case=test_case,
                failure_scenario=failure_scenario,
                status=RecoveryTestStatus.SKIPPED,
                start_time=start_time,
                failure_time=failure_time,
                recovery_start_time=recovery_start_time,
                end_time=end_time,
                total_duration=total_duration,
                failure_duration=0.0,
                recovery_duration=0.0,
                error_message=f"Failure scenario {failure_scenario.value} not supported by this test"
            )
            self.test_results[test_id] = result
            return result
        
        # Check skip conditions
        if self._should_skip_test(test_case, failure_scenario):
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            result = RecoveryTestResult(
                test_case=test_case,
                failure_scenario=failure_scenario,
                status=RecoveryTestStatus.SKIPPED,
                start_time=start_time,
                failure_time=failure_time,
                recovery_start_time=recovery_start_time,
                end_time=end_time,
                total_duration=total_duration,
                failure_duration=0.0,
                recovery_duration=0.0,
                error_message="Test skipped due to skip conditions"
            )
            self.test_results[test_id] = result
            return result
        
        try:
            # Setup phase
            if test_case.setup_function:
                await self._execute_with_timeout(
                    test_case.setup_function(), test_case.timeout_seconds
                )
            
            # Simulate failure and execute test
            failure_time = datetime.now()
            test_result_data = await self._execute_with_timeout(
                test_case.test_function(failure_scenario), test_case.timeout_seconds
            )
            
            # Start recovery process
            recovery_start_time = datetime.now()
            recovery_result_data = await self._execute_with_timeout(
                self._perform_recovery(test_case, failure_scenario), 
                test_case.recovery_timeout_seconds
            )
            
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            failure_duration = (recovery_start_time - failure_time).total_seconds()
            recovery_duration = (end_time - recovery_start_time).total_seconds()
            
            # Validate recovery
            validation_result = await self._validate_recovery(
                test_case, failure_scenario, recovery_result_data
            )
            
            # Determine final status based on validation
            if validation_result.get('full_recovery', False):
                status = RecoveryTestStatus.PASSED
            elif validation_result.get('partial_recovery', False):
                status = RecoveryTestStatus.PARTIAL_RECOVERY
            else:
                status = RecoveryTestStatus.NO_RECOVERY
            
            # Create result
            result = RecoveryTestResult(
                test_case=test_case,
                failure_scenario=failure_scenario,
                status=status,
                start_time=start_time,
                failure_time=failure_time,
                recovery_start_time=recovery_start_time,
                end_time=end_time,
                total_duration=total_duration,
                failure_duration=failure_duration,
                recovery_duration=recovery_duration,
                data_integrity_check=validation_result.get('data_integrity', True),
                service_availability_check=validation_result.get('service_availability', True),
                recovery_metrics=validation_result.get('metrics', {}),
                recovery_steps=validation_result.get('recovery_steps', []),
                performance_metrics={
                    'total_test_time': total_duration,
                    'failure_simulation_time': failure_duration,
                    'recovery_time': recovery_duration,
                    'recovery_time_within_expected': recovery_duration <= test_case.expected_recovery_time
                }
            )
            
        except asyncio.TimeoutError:
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            failure_duration = (recovery_start_time - failure_time).total_seconds()
            recovery_duration = (end_time - recovery_start_time).total_seconds()
            
            result = RecoveryTestResult(
                test_case=test_case,
                failure_scenario=failure_scenario,
                status=RecoveryTestStatus.ERROR,
                start_time=start_time,
                failure_time=failure_time,
                recovery_start_time=recovery_start_time,
                end_time=end_time,
                total_duration=total_duration,
                failure_duration=failure_duration,
                recovery_duration=recovery_duration,
                error_message=f"Test timed out after {test_case.timeout_seconds + test_case.recovery_timeout_seconds} seconds"
            )
            
        except Exception as e:
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            failure_duration = (recovery_start_time - failure_time).total_seconds()
            recovery_duration = (end_time - recovery_start_time).total_seconds()
            
            self.logger.error(f"Test {test_case.test_name} failed with error: {str(e)}")
            
            result = RecoveryTestResult(
                test_case=test_case,
                failure_scenario=failure_scenario,
                status=RecoveryTestStatus.FAILED,
                start_time=start_time,
                failure_time=failure_time,
                recovery_start_time=recovery_start_time,
                end_time=end_time,
                total_duration=total_duration,
                failure_duration=failure_duration,
                recovery_duration=recovery_duration,
                error_message=str(e),
                stack_trace=traceback.format_exc()
            )
            
        finally:
            # Teardown phase
            if test_case.teardown_function:
                try:
                    await self._execute_with_timeout(
                        test_case.teardown_function(), test_case.timeout_seconds
                    )
                except Exception as e:
                    self.logger.warning(f"Teardown failed for {test_case.test_name}: {e}")
        
        self.test_results[test_id] = result
        self.logger.info(f"Test {test_case.test_name} completed with status: {result.status.value}")
        
        return result
    
    def _should_skip_test(self, test_case: RecoveryTestCase, failure_scenario: FailureType) -> bool:
        """Determine if a test should be skipped based on conditions"""
        # Check skip conditions
        if test_case.skip_conditions:
            for condition in test_case.skip_conditions:
                if self._evaluate_skip_condition(condition, failure_scenario):
                    return True
        return False
    
    def _evaluate_skip_condition(self, condition: str, failure_scenario: FailureType) -> bool:
        """Evaluate a skip condition"""
        # Simple implementation - in a real system, this would be more sophisticated
        if "not_hardware_failure" in condition and failure_scenario == FailureType.HARDWARE_FAILURE:
            return True
        if "not_network_failure" in condition and failure_scenario == FailureType.NETWORK_PARTITION:
            return True
        return False
    
    async def _execute_with_timeout(self, coro, timeout_seconds: int):
        """Execute a coroutine with timeout"""
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    
    async def _perform_recovery(self, test_case: RecoveryTestCase, failure_scenario: FailureType) -> Dict[str, Any]:
        """Perform recovery process"""
        self.logger.info(f"Performing recovery for {test_case.test_name} after {failure_scenario.value}")
        
        # Simulate recovery time
        recovery_time = random.uniform(1.0, test_case.expected_recovery_time)
        await asyncio.sleep(recovery_time / 10)  # Scale down for testing
        
        # Mock recovery steps
        recovery_steps = [
            "Detecting failure",
            "Isolating affected components",
            "Initiating recovery procedures",
            "Restoring services",
            "Validating system state"
        ]
        
        return {
            'recovery_steps': recovery_steps,
            'recovery_time': recovery_time,
            'recovery_successful': True
        }
    
    async def _validate_recovery(self, test_case: RecoveryTestCase, failure_scenario: FailureType, 
                               recovery_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate recovery process"""
        self.logger.info(f"Validating recovery for {test_case.test_name} after {failure_scenario.value}")
        
        # If custom validation function is provided, use it
        if test_case.recovery_validation_function:
            return await test_case.recovery_validation_function(failure_scenario, recovery_result)
        
        # Default validation
        return {
            'full_recovery': recovery_result.get('recovery_successful', False),
            'partial_recovery': False,
            'data_integrity': True,
            'service_availability': True,
            'metrics': recovery_result.get('recovery_metrics', {}),
            'recovery_steps': recovery_result.get('recovery_steps', [])
        }
    
    async def execute_test_suite(
        self,
        suite_name: str,
        test_ids: Optional[List[str]] = None,
        failure_scenarios: Optional[List[FailureType]] = None,
        parallel_execution: bool = True
    ) -> RecoveryTestSuiteResult:
        """
        Execute a suite of recovery tests.
        
        Args:
            suite_name: Name of the test suite
            test_ids: List of test IDs to execute (None for all)
            failure_scenarios: List of failure scenarios to test (None for all supported by each test)
            parallel_execution: Whether to execute tests in parallel
            
        Returns:
            Recovery test suite result
        """
        start_time = datetime.now()
        
        if test_ids is None:
            test_ids = list(self.test_cases.keys())
        
        # Generate all test combinations
        test_combinations = []
        for test_id in test_ids:
            test_case = self.test_cases[test_id]
            scenarios_to_test = failure_scenarios or test_case.failure_scenarios
            for scenario in scenarios_to_test:
                if scenario in test_case.failure_scenarios:
                    test_combinations.append((test_id, scenario))
        
        self.logger.info(f"Executing recovery test suite: {suite_name}")
        self.logger.info(f"Total test combinations: {len(test_combinations)}")
        
        # Execute tests
        if parallel_execution:
            results = await self._execute_tests_parallel(test_combinations)
        else:
            results = await self._execute_tests_sequential(test_combinations)
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        # Calculate statistics
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.status == RecoveryTestStatus.PASSED)
        failed_tests = sum(1 for r in results if r.status == RecoveryTestStatus.FAILED)
        error_tests = sum(1 for r in results if r.status == RecoveryTestStatus.ERROR)
        skipped_tests = sum(1 for r in results if r.status == RecoveryTestStatus.SKIPPED)
        partial_recovery_tests = sum(1 for r in results if r.status == RecoveryTestStatus.PARTIAL_RECOVERY)
        no_recovery_tests = sum(1 for r in results if r.status == RecoveryTestStatus.NO_RECOVERY)
        
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Generate summaries
        recovery_summary = self._generate_recovery_summary(results)
        failure_type_summary = self._generate_failure_type_summary(results)
        performance_summary = self._generate_performance_summary(results)
        recommendations = self._generate_recommendations(results)
        
        suite_result = RecoveryTestSuiteResult(
            suite_name=suite_name,
            start_time=start_time,
            end_time=end_time,
            total_duration=total_duration,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            error_tests=error_tests,
            skipped_tests=skipped_tests,
            partial_recovery_tests=partial_recovery_tests,
            no_recovery_tests=no_recovery_tests,
            pass_rate=pass_rate,
            test_results=results,
            recovery_summary=recovery_summary,
            failure_type_summary=failure_type_summary,
            performance_summary=performance_summary,
            recommendations=recommendations
        )
        
        self.suite_results.append(suite_result)
        
        self.logger.info(
            f"Suite {suite_name} completed: {passed_tests}/{total_tests} passed "
            f"({pass_rate:.1f}% pass rate)"
        )
        
        return suite_result
    
    async def _execute_tests_parallel(self, test_combinations: List[Tuple]) -> List[RecoveryTestResult]:
        """Execute tests in parallel"""
        tasks = []
        for test_id, failure_scenario in test_combinations:
            task = self.execute_test_case(test_id, failure_scenario)
            tasks.append(task)
        return await asyncio.gather(*tasks, return_exceptions=False)
    
    async def _execute_tests_sequential(self, test_combinations: List[Tuple]) -> List[RecoveryTestResult]:
        """Execute tests sequentially"""
        results = []
        for test_id, failure_scenario in test_combinations:
            result = await self.execute_test_case(test_id, failure_scenario)
            results.append(result)
        return results
    
    def _generate_recovery_summary(self, results: List[RecoveryTestResult]) -> Dict[str, Any]:
        """Generate summary of recovery test results"""
        if not results:
            return {}
        
        # Group results by recovery type
        recovery_types = {}
        for result in results:
            recovery_type = result.test_case.recovery_type.value
            if recovery_type not in recovery_types:
                recovery_types[recovery_type] = {
                    'total': 0,
                    'passed': 0,
                    'failed': 0,
                    'partial': 0,
                    'no_recovery': 0,
                    'errors': 0
                }
            recovery_types[recovery_type]['total'] += 1
            if result.status == RecoveryTestStatus.PASSED:
                recovery_types[recovery_type]['passed'] += 1
            elif result.status == RecoveryTestStatus.FAILED:
                recovery_types[recovery_type]['failed'] += 1
            elif result.status == RecoveryTestStatus.PARTIAL_RECOVERY:
                recovery_types[recovery_type]['partial'] += 1
            elif result.status == RecoveryTestStatus.NO_RECOVERY:
                recovery_types[recovery_type]['no_recovery'] += 1
            elif result.status == RecoveryTestStatus.ERROR:
                recovery_types[recovery_type]['errors'] += 1
        
        return recovery_types
    
    def _generate_failure_type_summary(self, results: List[RecoveryTestResult]) -> Dict[str, Any]:
        """Generate failure type summary"""
        failure_stats = {}
        for result in results:
            failure_type = result.failure_scenario.value
            if failure_type not in failure_stats:
                failure_stats[failure_type] = {
                    'total': 0,
                    'passed': 0,
                    'failed': 0,
                    'partial': 0,
                    'no_recovery': 0
                }
            failure_stats[failure_type]['total'] += 1
            if result.status == RecoveryTestStatus.PASSED:
                failure_stats[failure_type]['passed'] += 1
            elif result.status == RecoveryTestStatus.FAILED:
                failure_stats[failure_type]['failed'] += 1
            elif result.status == RecoveryTestStatus.PARTIAL_RECOVERY:
                failure_stats[failure_type]['partial'] += 1
            elif result.status == RecoveryTestStatus.NO_RECOVERY:
                failure_stats[failure_type]['no_recovery'] += 1
        
        return failure_stats
    
    def _generate_performance_summary(self, results: List[RecoveryTestResult]) -> Dict[str, Any]:
        """Generate performance summary"""
        if not results:
            return {}
        
        recovery_times = [r.recovery_duration for r in results if r.recovery_duration > 0]
        failure_times = [r.failure_duration for r in results if r.failure_duration > 0]
        
        within_expected_time = sum(1 for r in results 
                                 if r.recovery_duration <= r.test_case.expected_recovery_time)
        
        return {
            'average_recovery_time': sum(recovery_times) / len(recovery_times) if recovery_times else 0,
            'min_recovery_time': min(recovery_times) if recovery_times else 0,
            'max_recovery_time': max(recovery_times) if recovery_times else 0,
            'average_failure_time': sum(failure_times) / len(failure_times) if failure_times else 0,
            'recovery_within_expected_time': within_expected_time,
            'recovery_success_rate': (within_expected_time / len(results) * 100) if results else 0
        }
    
    def _generate_recommendations(self, results: List[RecoveryTestResult]) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        failed_results = [r for r in results if r.status == RecoveryTestStatus.FAILED]
        no_recovery_results = [r for r in results if r.status == RecoveryTestStatus.NO_RECOVERY]
        partial_recovery_results = [r for r in results if r.status == RecoveryTestStatus.PARTIAL_RECOVERY]
        slow_recovery_results = [r for r in results 
                               if r.recovery_duration > r.test_case.expected_recovery_time]
        
        if failed_results:
            recommendations.append(
                f"Address {len(failed_results)} failed recovery tests to improve system reliability"
            )
        
        if no_recovery_results:
            recommendations.append(
                f"Critical: {len(no_recovery_results)} tests showed no recovery - "
                f"investigate immediate recovery mechanisms"
            )
        
        if partial_recovery_results:
            recommendations.append(
                f"Improve {len(partial_recovery_results)} partial recovery cases to ensure full recovery"
            )
        
        if slow_recovery_results:
            avg_slow_time = sum(r.recovery_duration for r in slow_recovery_results) / len(slow_recovery_results)
            recommendations.append(
                f"Optimize recovery time for {len(slow_recovery_results)} slow recovery tests "
                f"(average {avg_slow_time:.2f}s vs expected {slow_recovery_results[0].test_case.expected_recovery_time:.2f}s)"
            )
        
        # Data integrity issues
        integrity_failures = [r for r in results if not r.data_integrity_check]
        if integrity_failures:
            recommendations.append(
                f"Address {len(integrity_failures)} data integrity failures in recovery processes"
            )
        
        return recommendations
    
    def generate_comprehensive_report(self, suite_result: RecoveryTestSuiteResult) -> str:
        """
        Generate a comprehensive recovery test report.
        
        Args:
            suite_result: The test suite result to generate report for
            
        Returns:
            Formatted test report string
        """
        report_lines = [
            "=" * 80,
            "RECOVERY TEST SUITE REPORT",
            "=" * 80,
            f"Suite Name: {suite_result.suite_name}",
            f"Execution Time: {suite_result.start_time.strftime('%Y-%m-%d %H:%M:%S')} - "
            f"{suite_result.end_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Duration: {suite_result.total_duration:.2f} seconds",
            "",
            "SUMMARY",
            "-" * 40,
            f"Total Tests: {suite_result.total_tests}",
            f"Full Recovery: {suite_result.passed_tests}",
            f"Partial Recovery: {suite_result.partial_recovery_tests}",
            f"No Recovery: {suite_result.no_recovery_tests}",
            f"Failed: {suite_result.failed_tests}",
            f"Errors: {suite_result.error_tests}",
            f"Skipped: {suite_result.skipped_tests}",
            f"Recovery Success Rate: {suite_result.pass_rate:.1f}%",
            ""
        ]
        
        # Recovery summary
        if suite_result.recovery_summary:
            report_lines.extend([
                "RECOVERY TYPE SUMMARY",
                "-" * 40
            ])
            for recovery_type, stats in suite_result.recovery_summary.items():
                success_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
                report_lines.append(
                    f"{recovery_type.upper()}: {stats['passed']}/{stats['total']} "
                    f"({success_rate:.1f}% full recovery)"
                )
            report_lines.append("")
        
        # Failure type summary
        if suite_result.failure_type_summary:
            report_lines.extend([
                "FAILURE TYPE SUMMARY",
                "-" * 40
            ])
            for failure_type, stats in suite_result.failure_type_summary.items():
                success_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
                report_lines.append(
                    f"{failure_type.upper()}: {stats['passed']}/{stats['total']} "
                    f"({success_rate:.1f}% full recovery)"
                )
            report_lines.append("")
        
        # Performance summary
        if suite_result.performance_summary:
            perf = suite_result.performance_summary
            report_lines.extend([
                "PERFORMANCE SUMMARY",
                "-" * 40,
                f"Average Recovery Time: {perf['average_recovery_time']:.2f}s",
                f"Min/Max Recovery Time: {perf['min_recovery_time']:.2f}s / {perf['max_recovery_time']:.2f}s",
                f"Recovery Within Expected Time: {perf['recovery_within_expected_time']}/{suite_result.total_tests}",
                f"Recovery Success Rate: {perf['recovery_success_rate']:.1f}%",
                ""
            ])
        
        # Failed tests details
        failed_tests = [r for r in suite_result.test_results if r.status == RecoveryTestStatus.FAILED]
        if failed_tests:
            report_lines.extend([
                "FAILED TESTS",
                "-" * 40
            ])
            for result in failed_tests[:10]:  # Limit to first 10 failures
                report_lines.extend([
                    f"Test: {result.test_case.test_name}",
                    f"  Failure Type: {result.failure_scenario.value}",
                    f"  Recovery Type: {result.test_case.recovery_type.value}",
                    f"  Duration: {result.total_duration:.3f}s",
                    f"  Error: {result.error_message}",
                    ""
                ])
            if len(failed_tests) > 10:
                report_lines.append(f"... and {len(failed_tests) - 10} more failures")
                report_lines.append("")
        
        # No recovery tests details
        no_recovery_tests = [r for r in suite_result.test_results if r.status == RecoveryTestStatus.NO_RECOVERY]
        if no_recovery_tests:
            report_lines.extend([
                "NO RECOVERY TESTS (CRITICAL)",
                "-" * 40
            ])
            for result in no_recovery_tests[:5]:  # Limit to first 5 critical failures
                report_lines.extend([
                    f"Test: {result.test_case.test_name}",
                    f"  Failure Type: {result.failure_scenario.value}",
                    f"  Recovery Time: {result.recovery_duration:.3f}s",
                    f"  Data Integrity: {'PASS' if result.data_integrity_check else 'FAIL'}",
                    f"  Service Availability: {'PASS' if result.service_availability_check else 'FAIL'}",
                    ""
                ])
            if len(no_recovery_tests) > 5:
                report_lines.append(f"... and {len(no_recovery_tests) - 5} more critical failures")
                report_lines.append("")
        
        # Recommendations
        if suite_result.recommendations:
            report_lines.extend([
                "RECOMMENDATIONS",
                "-" * 40
            ])
            for i, recommendation in enumerate(suite_result.recommendations, 1):
                report_lines.append(f"{i}. {recommendation}")
            report_lines.append("")
        
        report_lines.extend([
            "=" * 80,
            "END OF REPORT",
            "=" * 80
        ])
        
        return "\n".join(report_lines)


# Example usage and test functions
async def example_system_crash_test(failure_scenario: FailureType):
    """Example system crash test function"""
    # Simulate system crash
    await asyncio.sleep(0.1)
    return {
        'crash_simulated': True,
        'crash_type': failure_scenario.value
    }


async def example_recovery_validation(failure_scenario: FailureType, recovery_result: Dict[str, Any]) -> Dict[str, Any]:
    """Example recovery validation function"""
    # Simulate recovery validation
    await asyncio.sleep(0.05)
    return {
        'full_recovery': True,
        'data_integrity': True,
        'service_availability': True,
        'metrics': {
            'recovery_time_ms': 1500,
            'data_restored': 100
        }
    }


# Example of how to use the recovery test runner
if __name__ == "__main__":
    # Example usage
    async def main():
        config = {
            'default_recovery_timeout': 120,
            'default_expected_recovery_time': 30.0
        }
        
        runner = RecoveryTestRunner(config)
        
        # Register test cases
        runner.register_system_crash_recovery_test(
            "System Crash Recovery Test",
            [FailureType.SOFTWARE_CRASH, FailureType.HARDWARE_FAILURE],
            example_system_crash_test,
            example_recovery_validation,
            expected_recovery_time=25.0
        )
        
        runner.register_data_corruption_recovery_test(
            "Data Corruption Recovery Test",
            [FailureType.DATABASE_CORRUPTION],
            example_system_crash_test,
            example_recovery_validation,
            data_integrity_required=True,
            expected_recovery_time=40.0
        )
        
        # Execute test suite
        suite_result = await runner.execute_test_suite(
            "Example Recovery Suite",
            failure_scenarios=[FailureType.SOFTWARE_CRASH, FailureType.DATABASE_CORRUPTION]
        )
        
        # Generate report
        report = runner.generate_comprehensive_report(suite_result)
        print(report)
    
    # Run the example
    asyncio.run(main())