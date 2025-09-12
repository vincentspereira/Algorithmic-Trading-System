#!/usr/bin/env python3
"""
Load Test Runner for Algorithmic Trading System

This module implements comprehensive load testing functionality that validates
system performance and stability under various load conditions.

Key Features:
- Concurrent user load testing
- Transaction throughput testing
- Resource utilization monitoring
- Stress testing capabilities
- Load pattern simulation
- Performance bottleneck identification
- Scalability validation
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
import statistics
import psutil
import threading

# Testing framework imports
import pytest
import pytest_asyncio


class LoadTestType(Enum):
    """Types of load tests supported"""
    CONCURRENT_USERS = "concurrent_users"
    TRANSACTION_THROUGHPUT = "transaction_throughput"
    STRESS_TESTING = "stress_testing"
    SOAK_TESTING = "soak_testing"
    SPIKE_TESTING = "spike_testing"
    ENDURANCE_TESTING = "endurance_testing"
    VOLUME_TESTING = "volume_testing"


class LoadPattern(Enum):
    """Load patterns for testing"""
    CONSTANT = "constant"
    RAMP_UP = "ramp_up"
    RAMP_DOWN = "ramp_down"
    PEAK_LOAD = "peak_load"
    RANDOM = "random"
    STEP = "step"


class LoadTestStatus(Enum):
    """Status of load test execution"""
    NOT_STARTED = "not_started"
    INITIALIZING = "initializing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"
    ABORTED = "aborted"


@dataclass
class LoadTestCase:
    """Represents a single load test case"""
    test_id: str
    test_name: str
    load_type: LoadTestType
    load_pattern: LoadPattern
    test_function: Callable
    setup_function: Optional[Callable] = None
    teardown_function: Optional[Callable] = None
    validation_function: Optional[Callable] = None
    target_load: int = 100  # Number of concurrent users, transactions per second, etc.
    duration_seconds: int = 60
    ramp_up_duration: int = 10
    ramp_down_duration: int = 10
    timeout_seconds: int = 300
    error_threshold: float = 0.05  # 5% error rate
    response_time_threshold: float = 5.0  # seconds
    resource_utilization_thresholds: Dict[str, float] = field(default_factory=dict)
    skip_conditions: List[str] = field(default_factory=list)


@dataclass
class LoadTestMetrics:
    """Metrics collected during load testing"""
    timestamp: datetime
    concurrent_users: int
    requests_per_second: float
    average_response_time: float
    min_response_time: float
    max_response_time: float
    error_rate: float
    throughput: float
    cpu_usage_percent: float
    memory_usage_percent: float
    network_io: Dict[str, float] = field(default_factory=dict)
    database_metrics: Dict[str, float] = field(default_factory=dict)
    custom_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class LoadTestResult:
    """Results of a single load test"""
    test_case: LoadTestCase
    status: LoadTestStatus
    start_time: datetime
    end_time: datetime
    total_duration: float
    metrics_history: List[LoadTestMetrics] = field(default_factory=list)
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    peak_metrics: Dict[str, float] = field(default_factory=dict)
    average_metrics: Dict[str, float] = field(default_factory=dict)
    performance_bottlenecks: List[str] = field(default_factory=list)
    resource_utilization_issues: List[str] = field(default_factory=list)
    scalability_limitations: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class LoadTestSuiteResult:
    """Results of a load test suite execution"""
    suite_name: str
    start_time: datetime
    end_time: datetime
    total_duration: float
    total_tests: int
    completed_tests: int
    failed_tests: int
    error_tests: int
    timeout_tests: int
    aborted_tests: int
    success_rate: float
    test_results: List[LoadTestResult]
    load_summary: Dict[str, Any] = field(default_factory=dict)
    performance_summary: Dict[str, Any] = field(default_factory=dict)
    resource_utilization_summary: Dict[str, Any] = field(default_factory=dict)
    bottleneck_summary: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class LoadTestRunner:
    """
    Comprehensive load test runner for the algorithmic trading system.
    
    This class orchestrates load testing to validate system performance and
    stability under various load conditions.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the LoadTestRunner.
        
        Args:
            config: Configuration dictionary for load testing settings
        """
        self.config = config or {}
        self.logger = self._setup_logging()
        self.test_cases: Dict[str, LoadTestCase] = {}
        self.test_results: Dict[str, LoadTestResult] = {}
        self.suite_results: List[LoadTestSuiteResult] = []
        
        # Load testing configuration
        self.default_duration = self.config.get('default_duration_seconds', 60)
        self.default_target_load = self.config.get('default_target_load', 100)
        self.default_error_threshold = self.config.get('default_error_threshold', 0.05)
        self.default_response_time_threshold = self.config.get('default_response_time_threshold', 5.0)
        
        # Resource monitoring
        self.enable_resource_monitoring = self.config.get('enable_resource_monitoring', True)
        self.monitoring_interval = self.config.get('monitoring_interval', 1.0)  # seconds
        
        self.logger.info("LoadTestRunner initialized")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the load test runner"""
        logger = logging.getLogger('LoadTestRunner')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def register_test_case(self, test_case: LoadTestCase) -> None:
        """
        Register a new load test case.
        
        Args:
            test_case: The load test case to register
        """
        self.test_cases[test_case.test_id] = test_case
        self.logger.info(f"Registered load test case: {test_case.test_name}")
    
    def register_concurrent_users_test(
        self,
        test_name: str,
        target_concurrent_users: int,
        test_function: Callable,
        duration_seconds: int = 60,
        ramp_up_duration: int = 10,
        validation_function: Optional[Callable] = None
    ) -> str:
        """
        Register a concurrent users load test.
        
        Args:
            test_name: Name of the test
            target_concurrent_users: Target number of concurrent users
            test_function: Function to execute for testing
            duration_seconds: Duration of the test in seconds
            ramp_up_duration: Ramp up duration in seconds
            validation_function: Function to validate results
            
        Returns:
            Test case ID
        """
        test_id = f"concurrent_users_{uuid.uuid4().hex[:8]}"
        
        test_case = LoadTestCase(
            test_id=test_id,
            test_name=test_name,
            load_type=LoadTestType.CONCURRENT_USERS,
            load_pattern=LoadPattern.RAMP_UP,
            test_function=test_function,
            validation_function=validation_function,
            target_load=target_concurrent_users,
            duration_seconds=duration_seconds,
            ramp_up_duration=ramp_up_duration
        )
        
        self.register_test_case(test_case)
        return test_id
    
    def register_transaction_throughput_test(
        self,
        test_name: str,
        target_transactions_per_second: int,
        test_function: Callable,
        duration_seconds: int = 60,
        validation_function: Optional[Callable] = None
    ) -> str:
        """
        Register a transaction throughput load test.
        
        Args:
            test_name: Name of the test
            target_transactions_per_second: Target transactions per second
            test_function: Function to execute for testing
            duration_seconds: Duration of the test in seconds
            validation_function: Function to validate results
            
        Returns:
            Test case ID
        """
        test_id = f"transaction_throughput_{uuid.uuid4().hex[:8]}"
        
        test_case = LoadTestCase(
            test_id=test_id,
            test_name=test_name,
            load_type=LoadTestType.TRANSACTION_THROUGHPUT,
            load_pattern=LoadPattern.CONSTANT,
            test_function=test_function,
            validation_function=validation_function,
            target_load=target_transactions_per_second,
            duration_seconds=duration_seconds
        )
        
        self.register_test_case(test_case)
        return test_id
    
    def register_stress_test(
        self,
        test_name: str,
        peak_load: int,
        test_function: Callable,
        duration_seconds: int = 120,
        ramp_up_duration: int = 30,
        validation_function: Optional[Callable] = None
    ) -> str:
        """
        Register a stress test.
        
        Args:
            test_name: Name of the test
            peak_load: Peak load to test
            test_function: Function to execute for testing
            duration_seconds: Duration of the test in seconds
            ramp_up_duration: Ramp up duration in seconds
            validation_function: Function to validate results
            
        Returns:
            Test case ID
        """
        test_id = f"stress_test_{uuid.uuid4().hex[:8]}"
        
        test_case = LoadTestCase(
            test_id=test_id,
            test_name=test_name,
            load_type=LoadTestType.STRESS_TESTING,
            load_pattern=LoadPattern.PEAK_LOAD,
            test_function=test_function,
            validation_function=validation_function,
            target_load=peak_load,
            duration_seconds=duration_seconds,
            ramp_up_duration=ramp_up_duration
        )
        
        self.register_test_case(test_case)
        return test_id
    
    def register_soak_test(
        self,
        test_name: str,
        target_load: int,
        test_function: Callable,
        duration_seconds: int = 3600,  # 1 hour
        validation_function: Optional[Callable] = None
    ) -> str:
        """
        Register a soak test.
        
        Args:
            test_name: Name of the test
            target_load: Target load to maintain
            test_function: Function to execute for testing
            duration_seconds: Duration of the test in seconds (default 1 hour)
            validation_function: Function to validate results
            
        Returns:
            Test case ID
        """
        test_id = f"soak_test_{uuid.uuid4().hex[:8]}"
        
        test_case = LoadTestCase(
            test_id=test_id,
            test_name=test_name,
            load_type=LoadTestType.SOAK_TESTING,
            load_pattern=LoadPattern.CONSTANT,
            test_function=test_function,
            validation_function=validation_function,
            target_load=target_load,
            duration_seconds=duration_seconds
        )
        
        self.register_test_case(test_case)
        return test_id

    async def execute_test_case(self, test_id: str) -> LoadTestResult:
        """
        Execute a single load test case.
        
        Args:
            test_id: ID of the test case to execute
            
        Returns:
            Load test result
        """
        if test_id not in self.test_cases:
            raise ValueError(f"Test case {test_id} not found")
        
        test_case = self.test_cases[test_id]
        start_time = datetime.now()
        end_time = start_time
        
        self.logger.info(f"Executing load test: {test_case.test_name}")
        self.logger.info(f"Load Type: {test_case.load_type.value}, Target Load: {test_case.target_load}")
        
        # Check skip conditions
        if self._should_skip_test(test_case):
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            result = LoadTestResult(
                test_case=test_case,
                status=LoadTestStatus.ERROR,
                start_time=start_time,
                end_time=end_time,
                total_duration=total_duration,
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
            
            # Execute load test
            test_result = await self._execute_load_test(test_case)
            
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            # Validate results
            validation_result = await self._validate_load_test(
                test_case, test_result
            )
            
            # Create final result
            result = LoadTestResult(
                test_case=test_case,
                status=LoadTestStatus.COMPLETED,
                start_time=start_time,
                end_time=end_time,
                total_duration=total_duration,
                metrics_history=test_result.get('metrics_history', []),
                peak_metrics=validation_result.get('peak_metrics', {}),
                average_metrics=validation_result.get('average_metrics', {}),
                performance_bottlenecks=validation_result.get('performance_bottlenecks', []),
                resource_utilization_issues=validation_result.get('resource_utilization_issues', []),
                scalability_limitations=validation_result.get('scalability_limitations', [])
            )
            
        except asyncio.TimeoutError:
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            result = LoadTestResult(
                test_case=test_case,
                status=LoadTestStatus.TIMEOUT,
                start_time=start_time,
                end_time=end_time,
                total_duration=total_duration,
                error_message=f"Test timed out after {test_case.timeout_seconds} seconds"
            )
            
        except Exception as e:
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            self.logger.error(f"Test {test_case.test_name} failed with error: {str(e)}")
            
            result = LoadTestResult(
                test_case=test_case,
                status=LoadTestStatus.FAILED,
                start_time=start_time,
                end_time=end_time,
                total_duration=total_duration,
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
    
    def _should_skip_test(self, test_case: LoadTestCase) -> bool:
        """Determine if a test should be skipped based on conditions"""
        # Check skip conditions
        if test_case.skip_conditions:
            for condition in test_case.skip_conditions:
                if self._evaluate_skip_condition(condition):
                    return True
        return False
    
    def _evaluate_skip_condition(self, condition: str) -> bool:
        """Evaluate a skip condition"""
        # Simple implementation - in a real system, this would be more sophisticated
        if "not_performance_testing" in condition and self.config.get('performance_testing_enabled', True) is False:
            return True
        if "low_resource_environment" in condition:
            # Check if we're in a low-resource environment
            memory_gb = psutil.virtual_memory().total / (1024**3)
            if memory_gb < 8:  # Less than 8GB RAM
                return True
        return False
    
    async def _execute_with_timeout(self, coro, timeout_seconds: int):
        """Execute a coroutine with timeout"""
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    
    async def _execute_load_test(self, test_case: LoadTestCase) -> Dict[str, Any]:
        """Execute the actual load test"""
        self.logger.info(f"Starting load test execution for {test_case.test_name}")
        
        metrics_history = []
        start_time = time.time()
        end_time = start_time + test_case.duration_seconds
        
        # Start resource monitoring
        monitoring_task = None
        if self.enable_resource_monitoring:
            monitoring_task = asyncio.create_task(self._monitor_resources(metrics_history, start_time, end_time))
        
        try:
            # Execute based on load type
            if test_case.load_type == LoadTestType.CONCURRENT_USERS:
                result = await self._execute_concurrent_users_test(test_case, start_time, end_time)
            elif test_case.load_type == LoadTestType.TRANSACTION_THROUGHPUT:
                result = await self._execute_transaction_throughput_test(test_case, start_time, end_time)
            elif test_case.load_type == LoadTestType.STRESS_TESTING:
                result = await self._execute_stress_test(test_case, start_time, end_time)
            elif test_case.load_type == LoadTestType.SOAK_TESTING:
                result = await self._execute_soak_test(test_case, start_time, end_time)
            else:
                # Default execution
                result = await self._execute_generic_load_test(test_case, start_time, end_time)
            
            result['metrics_history'] = metrics_history
            return result
            
        finally:
            # Stop resource monitoring
            if monitoring_task and not monitoring_task.done():
                monitoring_task.cancel()
                try:
                    await monitoring_task
                except asyncio.CancelledError:
                    pass
    
    async def _monitor_resources(self, metrics_history: List[LoadTestMetrics], 
                               start_time: float, end_time: float) -> None:
        """Monitor system resources during load testing"""
        while time.time() < end_time:
            try:
                # Collect system metrics
                cpu_percent = psutil.cpu_percent(interval=None)
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                network = psutil.net_io_counters()
                
                # Create metrics snapshot
                metrics = LoadTestMetrics(
                    timestamp=datetime.now(),
                    concurrent_users=0,  # Will be updated by test execution
                    requests_per_second=0.0,
                    average_response_time=0.0,
                    min_response_time=0.0,
                    max_response_time=0.0,
                    error_rate=0.0,
                    throughput=0.0,
                    cpu_usage_percent=cpu_percent,
                    memory_usage_percent=memory_percent,
                    network_io={
                        'bytes_sent': network.bytes_sent,
                        'bytes_recv': network.bytes_recv
                    }
                )
                
                metrics_history.append(metrics)
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.warning(f"Resource monitoring error: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    async def _execute_concurrent_users_test(self, test_case: LoadTestCase, 
                                           start_time: float, end_time: float) -> Dict[str, Any]:
        """Execute concurrent users load test"""
        self.logger.info(f"Executing concurrent users test with {test_case.target_load} users")
        
        # Create user tasks
        user_tasks = []
        results = {'success_count': 0, 'error_count': 0, 'response_times': []}
        
        # Ramp up users
        ramp_up_end_time = start_time + test_case.ramp_up_duration
        users_per_second = test_case.target_load / test_case.ramp_up_duration if test_case.ramp_up_duration > 0 else test_case.target_load
        
        current_users = 0
        while time.time() < min(ramp_up_end_time, end_time):
            # Add users gradually
            users_to_add = int(users_per_second * (time.time() - start_time)) - current_users
            if users_to_add > 0:
                for _ in range(users_to_add):
                    if len(user_tasks) < test_case.target_load:
                        task = asyncio.create_task(self._simulate_user(test_case.test_function, results))
                        user_tasks.append(task)
                        current_users += 1
            
            await asyncio.sleep(0.1)  # Small delay to control ramp up
        
        # Maintain target load for remaining duration
        steady_state_end_time = end_time - test_case.ramp_down_duration if test_case.ramp_down_duration > 0 else end_time
        while time.time() < steady_state_end_time and len(user_tasks) < test_case.target_load:
            task = asyncio.create_task(self._simulate_user(test_case.test_function, results))
            user_tasks.append(task)
        
        # Wait for tasks to complete or timeout
        try:
            await asyncio.wait_for(asyncio.gather(*user_tasks, return_exceptions=True), 
                                 timeout=end_time - time.time())
        except asyncio.TimeoutError:
            # Cancel remaining tasks
            for task in user_tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for cancellations
            await asyncio.gather(*user_tasks, return_exceptions=True)
        
        return results
    
    async def _execute_transaction_throughput_test(self, test_case: LoadTestCase, 
                                                 start_time: float, end_time: float) -> Dict[str, Any]:
        """Execute transaction throughput load test"""
        self.logger.info(f"Executing transaction throughput test with {test_case.target_load} TPS")
        
        results = {'success_count': 0, 'error_count': 0, 'response_times': []}
        transactions_sent = 0
        
        # Calculate delay between transactions to achieve target TPS
        delay_between_transactions = 1.0 / test_case.target_load if test_case.target_load > 0 else 0
        
        while time.time() < end_time:
            start_transaction_time = time.time()
            
            # Execute transaction
            try:
                await test_case.test_function()
                results['success_count'] += 1
                response_time = time.time() - start_transaction_time
                results['response_times'].append(response_time)
            except Exception:
                results['error_count'] += 1
            
            transactions_sent += 1
            
            # Wait to maintain target TPS
            elapsed_time = time.time() - start_transaction_time
            if elapsed_time < delay_between_transactions:
                await asyncio.sleep(delay_between_transactions - elapsed_time)
        
        return results
    
    async def _execute_stress_test(self, test_case: LoadTestCase, 
                                 start_time: float, end_time: float) -> Dict[str, Any]:
        """Execute stress test"""
        self.logger.info(f"Executing stress test with peak load of {test_case.target_load}")
        
        # For stress testing, we'll gradually increase load
        results = {'success_count': 0, 'error_count': 0, 'response_times': []}
        peak_load_reached = False
        
        # Ramp up to peak load
        ramp_up_end_time = start_time + test_case.ramp_up_duration
        peak_duration = test_case.duration_seconds - test_case.ramp_up_duration - test_case.ramp_down_duration
        peak_end_time = ramp_up_end_time + peak_duration
        
        current_load = 0
        max_load = test_case.target_load
        
        while time.time() < end_time:
            current_time = time.time()
            
            # Determine current load level
            if current_time < ramp_up_end_time:
                # Ramp up phase
                elapsed_ramp_up = current_time - start_time
                current_load = int((elapsed_ramp_up / test_case.ramp_up_duration) * max_load)
            elif current_time < peak_end_time:
                # Peak load phase
                current_load = max_load
                peak_load_reached = True
            else:
                # Ramp down phase
                elapsed_ramp_down = current_time - peak_end_time
                ramp_down_duration = test_case.duration_seconds - test_case.ramp_up_duration - peak_duration
                if ramp_down_duration > 0:
                    current_load = int(max_load * (1 - (elapsed_ramp_down / ramp_down_duration)))
                else:
                    current_load = 0
            
            # Execute load for current level
            tasks = []
            for _ in range(current_load):
                task = asyncio.create_task(self._execute_single_transaction(test_case.test_function, results))
                tasks.append(task)
            
            # Wait a short time before next iteration
            await asyncio.sleep(0.1)
        
        return results
    
    async def _execute_soak_test(self, test_case: LoadTestCase, 
                               start_time: float, end_time: float) -> Dict[str, Any]:
        """Execute soak test"""
        self.logger.info(f"Executing soak test with {test_case.target_load} load for {test_case.duration_seconds} seconds")
        
        results = {'success_count': 0, 'error_count': 0, 'response_times': []}
        
        # Maintain constant load for entire duration
        while time.time() < end_time:
            tasks = []
            for _ in range(test_case.target_load):
                task = asyncio.create_task(self._execute_single_transaction(test_case.test_function, results))
                tasks.append(task)
            
            # Wait a short time before next batch
            await asyncio.sleep(0.5)
        
        return results
    
    async def _execute_generic_load_test(self, test_case: LoadTestCase, 
                                       start_time: float, end_time: float) -> Dict[str, Any]:
        """Execute generic load test"""
        self.logger.info(f"Executing generic load test")
        
        results = {'success_count': 0, 'error_count': 0, 'response_times': []}
        
        while time.time() < end_time:
            try:
                await test_case.test_function()
                results['success_count'] += 1
            except Exception:
                results['error_count'] += 1
            
            await asyncio.sleep(0.1)
        
        return results
    
    async def _simulate_user(self, test_function: Callable, results: Dict[str, Any]) -> None:
        """Simulate a user performing actions"""
        try:
            start_time = time.time()
            await test_function()
            response_time = time.time() - start_time
            results['success_count'] += 1
            results['response_times'].append(response_time)
        except Exception:
            results['error_count'] += 1
    
    async def _execute_single_transaction(self, test_function: Callable, results: Dict[str, Any]) -> None:
        """Execute a single transaction"""
        try:
            start_time = time.time()
            await test_function()
            response_time = time.time() - start_time
            results['success_count'] += 1
            results['response_times'].append(response_time)
        except Exception:
            results['error_count'] += 1
    
    async def _validate_load_test(self, test_case: LoadTestCase, 
                                test_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate load test results"""
        self.logger.info(f"Validating load test results for {test_case.test_name}")
        
        # If custom validation function is provided, use it
        if test_case.validation_function:
            return await test_case.validation_function(test_result)
        
        # Default validation
        success_count = test_result.get('success_count', 0)
        error_count = test_result.get('error_count', 0)
        response_times = test_result.get('response_times', [])
        
        total_transactions = success_count + error_count
        error_rate = error_count / total_transactions if total_transactions > 0 else 0
        
        # Calculate response time statistics
        avg_response_time = statistics.mean(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        
        # Identify performance bottlenecks
        performance_bottlenecks = []
        resource_issues = []
        scalability_limitations = []
        
        # Check error rate threshold
        if error_rate > test_case.error_threshold:
            performance_bottlenecks.append(
                f"High error rate: {error_rate:.2%} (threshold: {test_case.error_threshold:.2%})"
            )
        
        # Check response time threshold
        if avg_response_time > test_case.response_time_threshold:
            performance_bottlenecks.append(
                f"Slow response time: {avg_response_time:.3f}s (threshold: {test_case.response_time_threshold:.3f}s)"
            )
        
        # Check for resource utilization issues (if monitoring enabled)
        # This would be implemented with actual resource data in a real system
        
        peak_metrics = {
            'peak_concurrent_users': test_case.target_load,
            'peak_transactions_per_second': len(response_times) / test_case.duration_seconds if test_case.duration_seconds > 0 else 0,
            'peak_response_time': max_response_time,
            'peak_error_rate': error_rate
        }
        
        average_metrics = {
            'avg_concurrent_users': test_case.target_load,
            'avg_transactions_per_second': len(response_times) / test_case.duration_seconds if test_case.duration_seconds > 0 else 0,
            'avg_response_time': avg_response_time,
            'avg_error_rate': error_rate
        }
        
        return {
            'peak_metrics': peak_metrics,
            'average_metrics': average_metrics,
            'performance_bottlenecks': performance_bottlenecks,
            'resource_utilization_issues': resource_issues,
            'scalability_limitations': scalability_limitations
        }
    
    async def execute_test_suite(
        self,
        suite_name: str,
        test_ids: Optional[List[str]] = None,
        parallel_execution: bool = True
    ) -> LoadTestSuiteResult:
        """
        Execute a suite of load tests.
        
        Args:
            suite_name: Name of the test suite
            test_ids: List of test IDs to execute (None for all)
            parallel_execution: Whether to execute tests in parallel
            
        Returns:
            Load test suite result
        """
        start_time = datetime.now()
        
        if test_ids is None:
            test_ids = list(self.test_cases.keys())
        
        self.logger.info(f"Executing load test suite: {suite_name}")
        self.logger.info(f"Total tests: {len(test_ids)}")
        
        # Execute tests
        if parallel_execution:
            results = await self._execute_tests_parallel(test_ids)
        else:
            results = await self._execute_tests_sequential(test_ids)
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        # Calculate statistics
        total_tests = len(results)
        completed_tests = sum(1 for r in results if r.status == LoadTestStatus.COMPLETED)
        failed_tests = sum(1 for r in results if r.status == LoadTestStatus.FAILED)
        error_tests = sum(1 for r in results if r.status == LoadTestStatus.ERROR)
        timeout_tests = sum(1 for r in results if r.status == LoadTestStatus.TIMEOUT)
        aborted_tests = sum(1 for r in results if r.status == LoadTestStatus.ABORTED)
        
        success_rate = (completed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Generate summaries
        load_summary = self._generate_load_summary(results)
        performance_summary = self._generate_performance_summary(results)
        resource_utilization_summary = self._generate_resource_utilization_summary(results)
        bottleneck_summary = self._generate_bottleneck_summary(results)
        recommendations = self._generate_recommendations(results)
        
        suite_result = LoadTestSuiteResult(
            suite_name=suite_name,
            start_time=start_time,
            end_time=end_time,
            total_duration=total_duration,
            total_tests=total_tests,
            completed_tests=completed_tests,
            failed_tests=failed_tests,
            error_tests=error_tests,
            timeout_tests=timeout_tests,
            aborted_tests=aborted_tests,
            success_rate=success_rate,
            test_results=results,
            load_summary=load_summary,
            performance_summary=performance_summary,
            resource_utilization_summary=resource_utilization_summary,
            bottleneck_summary=bottleneck_summary,
            recommendations=recommendations
        )
        
        self.suite_results.append(suite_result)
        
        self.logger.info(
            f"Suite {suite_name} completed: {completed_tests}/{total_tests} completed "
            f"({success_rate:.1f}% success rate)"
        )
        
        return suite_result
    
    async def _execute_tests_parallel(self, test_ids: List[str]) -> List[LoadTestResult]:
        """Execute tests in parallel"""
        tasks = []
        for test_id in test_ids:
            task = self.execute_test_case(test_id)
            tasks.append(task)
        return await asyncio.gather(*tasks, return_exceptions=False)
    
    async def _execute_tests_sequential(self, test_ids: List[str]) -> List[LoadTestResult]:
        """Execute tests sequentially"""
        results = []
        for test_id in test_ids:
            result = await self.execute_test_case(test_id)
            results.append(result)
        return results
    
    def _generate_load_summary(self, results: List[LoadTestResult]) -> Dict[str, Any]:
        """Generate summary of load test results"""
        if not results:
            return {}
        
        # Group results by load type
        load_types = {}
        for result in results:
            load_type = result.test_case.load_type.value
            if load_type not in load_types:
                load_types[load_type] = {
                    'total': 0,
                    'completed': 0,
                    'failed': 0,
                    'avg_target_load': 0,
                    'total_target_load': 0
                }
            load_types[load_type]['total'] += 1
            if result.status == LoadTestStatus.COMPLETED:
                load_types[load_type]['completed'] += 1
            elif result.status in [LoadTestStatus.FAILED, LoadTestStatus.ERROR]:
                load_types[load_type]['failed'] += 1
            load_types[load_type]['total_target_load'] += result.test_case.target_load
        
        # Calculate averages
        for load_type in load_types:
            if load_types[load_type]['total'] > 0:
                load_types[load_type]['avg_target_load'] = (
                    load_types[load_type]['total_target_load'] / load_types[load_type]['total']
                )
        
        return load_types
    
    def _generate_performance_summary(self, results: List[LoadTestResult]) -> Dict[str, Any]:
        """Generate performance summary"""
        performance_stats = {
            'total_transactions': 0,
            'successful_transactions': 0,
            'failed_transactions': 0,
            'average_response_time': 0.0,
            'peak_response_time': 0.0,
            'average_throughput': 0.0,
            'average_error_rate': 0.0
        }
        
        total_response_times = []
        total_throughputs = []
        total_error_rates = []
        
        for result in results:
            if result.average_metrics:
                total_response_times.append(result.average_metrics.get('avg_response_time', 0))
                total_throughputs.append(result.average_metrics.get('avg_transactions_per_second', 0))
                total_error_rates.append(result.average_metrics.get('avg_error_rate', 0))
            
            # Count transactions
            performance_stats['total_transactions'] += (
                result.average_metrics.get('avg_transactions_per_second', 0) * 
                result.test_case.duration_seconds
            ) if result.average_metrics and result.test_case.duration_seconds else 0
        
        if total_response_times:
            performance_stats['average_response_time'] = statistics.mean(total_response_times)
            performance_stats['peak_response_time'] = max(total_response_times)
        
        if total_throughputs:
            performance_stats['average_throughput'] = statistics.mean(total_throughputs)
        
        if total_error_rates:
            performance_stats['average_error_rate'] = statistics.mean(total_error_rates)
        
        return performance_stats
    
    def _generate_resource_utilization_summary(self, results: List[LoadTestResult]) -> Dict[str, Any]:
        """Generate resource utilization summary"""
        resource_stats = {
            'peak_cpu_usage': 0.0,
            'average_cpu_usage': 0.0,
            'peak_memory_usage': 0.0,
            'average_memory_usage': 0.0,
            'high_resource_tests': 0
        }
        
        cpu_usages = []
        memory_usages = []
        
        for result in results:
            for metrics in result.metrics_history:
                cpu_usages.append(metrics.cpu_usage_percent)
                memory_usages.append(metrics.memory_usage_percent)
        
        if cpu_usages:
            resource_stats['peak_cpu_usage'] = max(cpu_usages)
            resource_stats['average_cpu_usage'] = statistics.mean(cpu_usages)
        
        if memory_usages:
            resource_stats['peak_memory_usage'] = max(memory_usages)
            resource_stats['average_memory_usage'] = statistics.mean(memory_usages)
        
        # Count tests with high resource usage
        for result in results:
            peak_cpu = resource_stats['peak_cpu_usage']
            peak_memory = resource_stats['peak_memory_usage']
            if peak_cpu > 80 or peak_memory > 80:  # 80% threshold
                resource_stats['high_resource_tests'] += 1
        
        return resource_stats
    
    def _generate_bottleneck_summary(self, results: List[LoadTestResult]) -> Dict[str, Any]:
        """Generate bottleneck summary"""
        bottleneck_stats = {
            'total_bottlenecks': 0,
            'performance_bottlenecks': 0,
            'resource_bottlenecks': 0,
            'scalability_issues': 0,
            'high_error_rate_tests': 0
        }
        
        for result in results:
            bottleneck_stats['total_bottlenecks'] += len(result.performance_bottlenecks)
            bottleneck_stats['performance_bottlenecks'] += len(result.performance_bottlenecks)
            bottleneck_stats['resource_bottlenecks'] += len(result.resource_utilization_issues)
            bottleneck_stats['scalability_issues'] += len(result.scalability_limitations)
            
            # Count tests with high error rates
            if result.average_metrics.get('avg_error_rate', 0) > 0.05:  # 5% threshold
                bottleneck_stats['high_error_rate_tests'] += 1
        
        return bottleneck_stats
    
    def _generate_recommendations(self, results: List[LoadTestResult]) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        failed_results = [r for r in results if r.status in [LoadTestStatus.FAILED, LoadTestStatus.ERROR]]
        timeout_results = [r for r in results if r.status == LoadTestStatus.TIMEOUT]
        bottleneck_results = [r for r in results if r.performance_bottlenecks]
        high_error_results = [r for r in results if r.average_metrics.get('avg_error_rate', 0) > 0.05]
        slow_response_results = [r for r in results if r.average_metrics.get('avg_response_time', 0) > 2.0]
        
        if failed_results:
            recommendations.append(
                f"Address {len(failed_results)} failed load tests to improve system stability"
            )
        
        if timeout_results:
            recommendations.append(
                f"Investigate {len(timeout_results)} timeout issues to improve system responsiveness"
            )
        
        if bottleneck_results:
            total_bottlenecks = sum(len(r.performance_bottlenecks) for r in bottleneck_results)
            recommendations.append(
                f"Resolve {total_bottlenecks} performance bottlenecks across {len(bottleneck_results)} tests"
            )
        
        if high_error_results:
            avg_error_rate = statistics.mean(
                r.average_metrics.get('avg_error_rate', 0) for r in high_error_results
            )
            recommendations.append(
                f"Reduce error rates for {len(high_error_results)} tests "
                f"(average error rate: {avg_error_rate:.2%})"
            )
        
        if slow_response_results:
            avg_response_time = statistics.mean(
                r.average_metrics.get('avg_response_time', 0) for r in slow_response_results
            )
            recommendations.append(
                f"Optimize response times for {len(slow_response_results)} slow tests "
                f"(average response time: {avg_response_time:.3f}s)"
            )
        
        # Resource utilization issues
        high_cpu_tests = [r for r in results if any(
            m.cpu_usage_percent > 80 for m in r.metrics_history
        )]
        high_memory_tests = [r for r in results if any(
            m.memory_usage_percent > 80 for m in r.metrics_history
        )]
        
        if high_cpu_tests:
            recommendations.append(
                f"Optimize CPU usage for {len(high_cpu_tests)} tests with high CPU utilization"
            )
        
        if high_memory_tests:
            recommendations.append(
                f"Optimize memory usage for {len(high_memory_tests)} tests with high memory utilization"
            )
        
        return recommendations
    
    def generate_comprehensive_report(self, suite_result: LoadTestSuiteResult) -> str:
        """
        Generate a comprehensive load test report.
        
        Args:
            suite_result: The test suite result to generate report for
            
        Returns:
            Formatted test report string
        """
        report_lines = [
            "=" * 80,
            "LOAD TEST SUITE REPORT",
            "=" * 80,
            f"Suite Name: {suite_result.suite_name}",
            f"Execution Time: {suite_result.start_time.strftime('%Y-%m-%d %H:%M:%S')} - "
            f"{suite_result.end_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Duration: {suite_result.total_duration:.2f} seconds",
            "",
            "SUMMARY",
            "-" * 40,
            f"Total Tests: {suite_result.total_tests}",
            f"Completed: {suite_result.completed_tests}",
            f"Failed: {suite_result.failed_tests}",
            f"Errors: {suite_result.error_tests}",
            f"Timeouts: {suite_result.timeout_tests}",
            f"Aborted: {suite_result.aborted_tests}",
            f"Success Rate: {suite_result.success_rate:.1f}%",
            ""
        ]
        
        # Load summary
        if suite_result.load_summary:
            report_lines.extend([
                "LOAD TYPE SUMMARY",
                "-" * 40
            ])
            for load_type, stats in suite_result.load_summary.items():
                success_rate = (stats['completed'] / stats['total'] * 100) if stats['total'] > 0 else 0
                report_lines.append(
                    f"{load_type.upper()}: {stats['completed']}/{stats['total']} "
                    f"({success_rate:.1f}% success) | "
                    f"Avg Load: {stats['avg_target_load']:.0f}"
                )
            report_lines.append("")
        
        # Performance summary
        if suite_result.performance_summary:
            perf = suite_result.performance_summary
            report_lines.extend([
                "PERFORMANCE SUMMARY",
                "-" * 40,
                f"Total Transactions: {perf['total_transactions']:,.0f}",
                f"Average Response Time: {perf['average_response_time']:.3f}s",
                f"Peak Response Time: {perf['peak_response_time']:.3f}s",
                f"Average Throughput: {perf['average_throughput']:.2f} TPS",
                f"Average Error Rate: {perf['average_error_rate']:.2%}",
                ""
            ])
        
        # Resource utilization summary
        if suite_result.resource_utilization_summary:
            resource = suite_result.resource_utilization_summary
            report_lines.extend([
                "RESOURCE UTILIZATION SUMMARY",
                "-" * 40,
                f"Peak CPU Usage: {resource['peak_cpu_usage']:.1f}%",
                f"Average CPU Usage: {resource['average_cpu_usage']:.1f}%",
                f"Peak Memory Usage: {resource['peak_memory_usage']:.1f}%",
                f"Average Memory Usage: {resource['average_memory_usage']:.1f}%",
                f"High Resource Tests: {resource['high_resource_tests']}",
                ""
            ])
        
        # Bottleneck summary
        if suite_result.bottleneck_summary:
            bottleneck = suite_result.bottleneck_summary
            report_lines.extend([
                "BOTTLENECK SUMMARY",
                "-" * 40,
                f"Total Bottlenecks: {bottleneck['total_bottlenecks']}",
                f"Performance Bottlenecks: {bottleneck['performance_bottlenecks']}",
                f"Resource Bottlenecks: {bottleneck['resource_bottlenecks']}",
                f"Scalability Issues: {bottleneck['scalability_issues']}",
                f"High Error Rate Tests: {bottleneck['high_error_rate_tests']}",
                ""
            ])
        
        # Failed tests details
        failed_tests = [r for r in suite_result.test_results 
                       if r.status in [LoadTestStatus.FAILED, LoadTestStatus.ERROR]]
        if failed_tests:
            report_lines.extend([
                "FAILED TESTS",
                "-" * 40
            ])
            for result in failed_tests[:10]:  # Limit to first 10 failures
                report_lines.extend([
                    f"Test: {result.test_case.test_name}",
                    f"  Load Type: {result.test_case.load_type.value}",
                    f"  Target Load: {result.test_case.target_load}",
                    f"  Status: {result.status.value}",
                    f"  Duration: {result.total_duration:.3f}s",
                    f"  Error: {result.error_message}",
                    ""
                ])
            if len(failed_tests) > 10:
                report_lines.append(f"... and {len(failed_tests) - 10} more failures")
                report_lines.append("")
        
        # Performance bottlenecks
        bottleneck_tests = [r for r in suite_result.test_results if r.performance_bottlenecks]
        if bottleneck_tests:
            report_lines.extend([
                "PERFORMANCE BOTTLENECKS",
                "-" * 40
            ])
            for result in bottleneck_tests[:5]:  # Limit to first 5 tests with bottlenecks
                report_lines.append(f"Test: {result.test_case.test_name}")
                for bottleneck in result.performance_bottlenecks[:3]:  # Limit to first 3 bottlenecks
                    report_lines.append(f"  - {bottleneck}")
                if len(result.performance_bottlenecks) > 3:
                    report_lines.append(f"  ... and {len(result.performance_bottlenecks) - 3} more")
                report_lines.append("")
            if len(bottleneck_tests) > 5:
                report_lines.append(f"... and {len(bottleneck_tests) - 5} more tests with bottlenecks")
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
async def example_user_simulation():
    """Example user simulation function"""
    # Simulate user actions
    await asyncio.sleep(random.uniform(0.1, 0.5))  # Simulate processing time
    if random.random() < 0.02:  # 2% error rate
        raise Exception("Simulated user error")
    return {"status": "success"}


async def example_transaction_function():
    """Example transaction function"""
    # Simulate transaction processing
    await asyncio.sleep(random.uniform(0.05, 0.2))  # Simulate processing time
    if random.random() < 0.01:  # 1% error rate
        raise Exception("Simulated transaction error")
    return {"transaction_id": str(uuid.uuid4())}


async def example_load_validation(test_result: Dict[str, Any]) -> Dict[str, Any]:
    """Example load validation function"""
    # Simulate load validation
    await asyncio.sleep(0.01)
    return {
        'peak_metrics': {
            'peak_concurrent_users': 100,
            'peak_transactions_per_second': 50.0,
            'peak_response_time': 0.5,
            'peak_error_rate': 0.02
        },
        'average_metrics': {
            'avg_concurrent_users': 80,
            'avg_transactions_per_second': 45.0,
            'avg_response_time': 0.3,
            'avg_error_rate': 0.01
        },
        'performance_bottlenecks': [],
        'resource_utilization_issues': [],
        'scalability_limitations': []
    }


# Example of how to use the load test runner
if __name__ == "__main__":
    # Example usage
    async def main():
        config = {
            'default_duration_seconds': 30,
            'default_target_load': 50,
            'default_error_threshold': 0.05,
            'default_response_time_threshold': 2.0,
            'enable_resource_monitoring': True,
            'monitoring_interval': 1.0
        }
        
        runner = LoadTestRunner(config)
        
        # Register test cases
        runner.register_concurrent_users_test(
            "Concurrent User Load Test",
            target_concurrent_users=100,
            test_function=example_user_simulation,
            duration_seconds=30,
            ramp_up_duration=5
        )
        
        runner.register_transaction_throughput_test(
            "Transaction Throughput Test",
            target_transactions_per_second=50,
            test_function=example_transaction_function,
            duration_seconds=30
        )
        
        # Execute test suite
        suite_result = await runner.execute_test_suite("Example Load Test Suite")
        
        # Generate report
        report = runner.generate_comprehensive_report(suite_result)
        print(report)
    
    # Run the example
    asyncio.run(main())