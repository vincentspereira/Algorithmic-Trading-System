#!/usr/bin/env python3
"""
Regression Test Runner for Algorithmic Trading System

This module implements comprehensive regression testing functionality that validates
system behavior and prevents regressions after code changes.

Key Features:
- Automated regression test execution
- Regression detection and reporting
- Performance regression monitoring
- Functional regression validation
- Test result comparison and analysis
- Historical regression tracking
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
import hashlib
import pickle

# Testing framework imports
import pytest
import pytest_asyncio


class RegressionTestType(Enum):
    """Types of regression tests supported"""
    FUNCTIONAL = "functional"
    PERFORMANCE = "performance"
    SECURITY = "security"
    USABILITY = "usability"
    COMPATIBILITY = "compatibility"
    INTEGRATION = "integration"


class RegressionStatus(Enum):
    """Status of regression test execution"""
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    REGRESSION_DETECTED = "regression_detected"
    IMPROVEMENT = "improvement"


class PerformanceMetricType(Enum):
    """Types of performance metrics to track"""
    EXECUTION_TIME = "execution_time"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    THROUGHPUT = "throughput"
    LATENCY = "latency"


@dataclass
class RegressionTestCase:
    """Represents a single regression test case"""
    test_id: str
    test_name: str
    regression_type: RegressionTestType
    test_function: Callable
    setup_function: Optional[Callable] = None
    teardown_function: Optional[Callable] = None
    validation_function: Optional[Callable] = None
    baseline_data: Optional[Dict[str, Any]] = None
    timeout_seconds: int = 60
    performance_thresholds: Dict[PerformanceMetricType, float] = field(default_factory=dict)
    skip_conditions: List[str] = field(default_factory=list)


@dataclass
class RegressionTestResult:
    """Results of a single regression test"""
    test_case: RegressionTestCase
    status: RegressionStatus
    start_time: datetime
    end_time: datetime
    total_duration: float
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    test_metrics: Dict[str, Any] = field(default_factory=dict)
    baseline_metrics: Dict[str, Any] = field(default_factory=dict)
    regression_detected: bool = False
    improvement_detected: bool = False
    performance_regressions: List[str] = field(default_factory=list)
    functional_regressions: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class RegressionTestSuiteResult:
    """Results of a regression test suite execution"""
    suite_name: str
    start_time: datetime
    end_time: datetime
    total_duration: float
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int
    skipped_tests: int
    regression_detected_tests: int
    improvement_tests: int
    pass_rate: float
    test_results: List[RegressionTestResult]
    regression_summary: Dict[str, Any] = field(default_factory=dict)
    performance_summary: Dict[str, Any] = field(default_factory=dict)
    historical_comparison: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class RegressionTestRunner:
    """
    Comprehensive regression test runner for the algorithmic trading system.
    
    This class orchestrates regression testing to prevent functional and performance
    regressions after code changes.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the RegressionTestRunner.
        
        Args:
            config: Configuration dictionary for regression testing settings
        """
        self.config = config or {}
        self.logger = self._setup_logging()
        self.test_cases: Dict[str, RegressionTestCase] = {}
        self.test_results: Dict[str, RegressionTestResult] = {}
        self.suite_results: List[RegressionTestSuiteResult] = []
        
        # Regression testing configuration
        self.baseline_storage_path = Path(self.config.get('baseline_storage_path', './regression_baselines'))
        self.baseline_storage_path.mkdir(exist_ok=True)
        
        self.historical_data_path = Path(self.config.get('historical_data_path', './regression_history'))
        self.historical_data_path.mkdir(exist_ok=True)
        
        self.performance_degradation_threshold = self.config.get('performance_degradation_threshold', 0.1)  # 10%
        self.enable_performance_regression_detection = self.config.get('enable_performance_regression_detection', True)
        self.enable_functional_regression_detection = self.config.get('enable_functional_regression_detection', True)
        
        self.logger.info("RegressionTestRunner initialized")
        self.logger.info(f"Baseline storage path: {self.baseline_storage_path}")
        self.logger.info(f"Historical data path: {self.historical_data_path}")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the regression test runner"""
        logger = logging.getLogger('RegressionTestRunner')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def register_test_case(self, test_case: RegressionTestCase) -> None:
        """
        Register a new regression test case.
        
        Args:
            test_case: The regression test case to register
        """
        self.test_cases[test_case.test_id] = test_case
        self.logger.info(f"Registered regression test case: {test_case.test_name}")
    
    def register_functional_regression_test(
        self,
        test_name: str,
        test_function: Callable,
        validation_function: Callable,
        baseline_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Register a functional regression test.
        
        Args:
            test_name: Name of the test
            test_function: Function to execute for testing
            validation_function: Function to validate results
            baseline_data: Baseline data for regression comparison
            
        Returns:
            Test case ID
        """
        test_id = f"functional_{uuid.uuid4().hex[:8]}"
        
        test_case = RegressionTestCase(
            test_id=test_id,
            test_name=test_name,
            regression_type=RegressionTestType.FUNCTIONAL,
            test_function=test_function,
            validation_function=validation_function,
            baseline_data=baseline_data
        )
        
        self.register_test_case(test_case)
        return test_id
    
    def register_performance_regression_test(
        self,
        test_name: str,
        test_function: Callable,
        performance_thresholds: Dict[PerformanceMetricType, float],
        baseline_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Register a performance regression test.
        
        Args:
            test_name: Name of the test
            test_function: Function to execute for testing
            performance_thresholds: Performance thresholds for regression detection
            baseline_data: Baseline data for regression comparison
            
        Returns:
            Test case ID
        """
        test_id = f"performance_{uuid.uuid4().hex[:8]}"
        
        test_case = RegressionTestCase(
            test_id=test_id,
            test_name=test_name,
            regression_type=RegressionTestType.PERFORMANCE,
            test_function=test_function,
            performance_thresholds=performance_thresholds,
            baseline_data=baseline_data
        )
        
        self.register_test_case(test_case)
        return test_id
    
    def register_security_regression_test(
        self,
        test_name: str,
        test_function: Callable,
        validation_function: Callable,
        baseline_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Register a security regression test.
        
        Args:
            test_name: Name of the test
            test_function: Function to execute for testing
            validation_function: Function to validate security results
            baseline_data: Baseline data for regression comparison
            
        Returns:
            Test case ID
        """
        test_id = f"security_{uuid.uuid4().hex[:8]}"
        
        test_case = RegressionTestCase(
            test_id=test_id,
            test_name=test_name,
            regression_type=RegressionTestType.SECURITY,
            test_function=test_function,
            validation_function=validation_function,
            baseline_data=baseline_data
        )
        
        self.register_test_case(test_case)
        return test_id
    
    def register_integration_regression_test(
        self,
        test_name: str,
        test_function: Callable,
        validation_function: Callable,
        baseline_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Register an integration regression test.
        
        Args:
            test_name: Name of the test
            test_function: Function to execute for testing
            validation_function: Function to validate integration results
            baseline_data: Baseline data for regression comparison
            
        Returns:
            Test case ID
        """
        test_id = f"integration_{uuid.uuid4().hex[:8]}"
        
        test_case = RegressionTestCase(
            test_id=test_id,
            test_name=test_name,
            regression_type=RegressionTestType.INTEGRATION,
            test_function=test_function,
            validation_function=validation_function,
            baseline_data=baseline_data
        )
        
        self.register_test_case(test_case)
        return test_id

    async def execute_test_case(self, test_id: str) -> RegressionTestResult:
        """
        Execute a single regression test case.
        
        Args:
            test_id: ID of the test case to execute
            
        Returns:
            Regression test result
        """
        if test_id not in self.test_cases:
            raise ValueError(f"Test case {test_id} not found")
        
        test_case = self.test_cases[test_id]
        start_time = datetime.now()
        end_time = start_time
        
        self.logger.info(f"Executing regression test: {test_case.test_name}")
        
        # Check skip conditions
        if self._should_skip_test(test_case):
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            result = RegressionTestResult(
                test_case=test_case,
                status=RegressionStatus.SKIPPED,
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
            
            # Execute test
            test_start_time = datetime.now()
            test_result_data = await self._execute_with_timeout(
                test_case.test_function(), test_case.timeout_seconds
            )
            test_end_time = datetime.now()
            
            total_duration = (test_end_time - start_time).total_seconds()
            
            # Validate results and detect regressions
            validation_result = await self._validate_and_detect_regressions(
                test_case, test_result_data
            )
            
            # Determine final status based on validation
            if validation_result.get('regression_detected', False):
                status = RegressionStatus.REGRESSION_DETECTED
            elif validation_result.get('improvement_detected', False):
                status = RegressionStatus.IMPROVEMENT
            elif validation_result.get('test_passed', True):
                status = RegressionStatus.PASSED
            else:
                status = RegressionStatus.FAILED
            
            # Create result
            result = RegressionTestResult(
                test_case=test_case,
                status=status,
                start_time=start_time,
                end_time=test_end_time,
                total_duration=total_duration,
                test_metrics=validation_result.get('test_metrics', {}),
                baseline_metrics=validation_result.get('baseline_metrics', {}),
                regression_detected=validation_result.get('regression_detected', False),
                improvement_detected=validation_result.get('improvement_detected', False),
                performance_regressions=validation_result.get('performance_regressions', []),
                functional_regressions=validation_result.get('functional_regressions', [])
            )
            
        except asyncio.TimeoutError:
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            result = RegressionTestResult(
                test_case=test_case,
                status=RegressionStatus.ERROR,
                start_time=start_time,
                end_time=end_time,
                total_duration=total_duration,
                error_message=f"Test timed out after {test_case.timeout_seconds} seconds"
            )
            
        except Exception as e:
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            self.logger.error(f"Test {test_case.test_name} failed with error: {str(e)}")
            
            result = RegressionTestResult(
                test_case=test_case,
                status=RegressionStatus.FAILED,
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
        
        # Save test results for historical tracking
        await self._save_test_result(test_case, result)
        
        return result
    
    def _should_skip_test(self, test_case: RegressionTestCase) -> bool:
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
        if "not_security_testing" in condition and self.config.get('security_testing_enabled', True) is False:
            return True
        return False
    
    async def _execute_with_timeout(self, coro, timeout_seconds: int):
        """Execute a coroutine with timeout"""
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    
    async def _validate_and_detect_regressions(self, test_case: RegressionTestCase, 
                                             test_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate test results and detect regressions"""
        self.logger.info(f"Validating and detecting regressions for {test_case.test_name}")
        
        # Get baseline data
        baseline_data = test_case.baseline_data or await self._load_baseline_data(test_case.test_id)
        
        # If custom validation function is provided, use it
        if test_case.validation_function:
            return await test_case.validation_function(test_result, baseline_data)
        
        # Default validation and regression detection
        test_metrics = test_result.get('metrics', {})
        baseline_metrics = baseline_data.get('metrics', {}) if baseline_data else {}
        
        regression_detected = False
        improvement_detected = False
        performance_regressions = []
        functional_regressions = []
        
        # Performance regression detection
        if self.enable_performance_regression_detection and baseline_metrics:
            for metric_name, current_value in test_metrics.items():
                if metric_name in baseline_metrics:
                    baseline_value = baseline_metrics[metric_name]
                    if isinstance(current_value, (int, float)) and isinstance(baseline_value, (int, float)):
                        # Check for performance degradation
                        if current_value > baseline_value * (1 + self.performance_degradation_threshold):
                            regression_detected = True
                            performance_regressions.append(
                                f"{metric_name}: {current_value:.4f} vs baseline {baseline_value:.4f} "
                                f"({((current_value/baseline_value - 1) * 100):.1f}% degradation)"
                            )
                        elif current_value < baseline_value * (1 - self.performance_degradation_threshold):
                            improvement_detected = True
        
        # Functional regression detection
        if self.enable_functional_regression_detection and baseline_data:
            current_results = test_result.get('results', {})
            baseline_results = baseline_data.get('results', {})
            
            # Compare functional results
            if current_results != baseline_results:
                regression_detected = True
                functional_regressions.append("Functional results differ from baseline")
        
        # Save current results as new baseline if no regression detected
        if not regression_detected and test_case.regression_type in [
            RegressionTestType.FUNCTIONAL, RegressionTestType.PERFORMANCE
        ]:
            await self._save_baseline_data(test_case.test_id, test_result)
        
        return {
            'test_passed': True,  # Assume test passes unless explicitly failed
            'test_metrics': test_metrics,
            'baseline_metrics': baseline_metrics,
            'regression_detected': regression_detected,
            'improvement_detected': improvement_detected,
            'performance_regressions': performance_regressions,
            'functional_regressions': functional_regressions
        }
    
    async def _load_baseline_data(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Load baseline data for a test case"""
        baseline_file = self.baseline_storage_path / f"{test_id}_baseline.json"
        if baseline_file.exists():
            try:
                with open(baseline_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load baseline data for {test_id}: {e}")
        return None
    
    async def _save_baseline_data(self, test_id: str, test_result: Dict[str, Any]) -> None:
        """Save baseline data for a test case"""
        baseline_file = self.baseline_storage_path / f"{test_id}_baseline.json"
        try:
            # Create a clean baseline data structure
            baseline_data = {
                'test_id': test_id,
                'timestamp': datetime.now().isoformat(),
                'metrics': test_result.get('metrics', {}),
                'results': test_result.get('results', {}),
                'version': self.config.get('version', '1.0.0')
            }
            
            with open(baseline_file, 'w') as f:
                json.dump(baseline_data, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to save baseline data for {test_id}: {e}")
    
    async def _save_test_result(self, test_case: RegressionTestCase, result: RegressionTestResult) -> None:
        """Save test result for historical tracking"""
        try:
            # Create historical record
            historical_record = {
                'test_id': test_case.test_id,
                'test_name': test_case.test_name,
                'timestamp': result.start_time.isoformat(),
                'status': result.status.value,
                'duration': result.total_duration,
                'metrics': result.test_metrics,
                'regression_detected': result.regression_detected,
                'improvement_detected': result.improvement_detected
            }
            
            # Save to historical data file
            history_file = self.historical_data_path / f"{test_case.test_id}_history.jsonl"
            with open(history_file, 'a') as f:
                f.write(json.dumps(historical_record) + '\n')
                
        except Exception as e:
            self.logger.warning(f"Failed to save historical data for {test_case.test_name}: {e}")
    
    async def execute_test_suite(
        self,
        suite_name: str,
        test_ids: Optional[List[str]] = None,
        parallel_execution: bool = True
    ) -> RegressionTestSuiteResult:
        """
        Execute a suite of regression tests.
        
        Args:
            suite_name: Name of the test suite
            test_ids: List of test IDs to execute (None for all)
            parallel_execution: Whether to execute tests in parallel
            
        Returns:
            Regression test suite result
        """
        start_time = datetime.now()
        
        if test_ids is None:
            test_ids = list(self.test_cases.keys())
        
        self.logger.info(f"Executing regression test suite: {suite_name}")
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
        passed_tests = sum(1 for r in results if r.status == RegressionStatus.PASSED)
        failed_tests = sum(1 for r in results if r.status == RegressionStatus.FAILED)
        error_tests = sum(1 for r in results if r.status == RegressionStatus.ERROR)
        skipped_tests = sum(1 for r in results if r.status == RegressionStatus.SKIPPED)
        regression_detected_tests = sum(1 for r in results if r.status == RegressionStatus.REGRESSION_DETECTED)
        improvement_tests = sum(1 for r in results if r.status == RegressionStatus.IMPROVEMENT)
        
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Generate summaries
        regression_summary = self._generate_regression_summary(results)
        performance_summary = self._generate_performance_summary(results)
        historical_comparison = self._generate_historical_comparison(results)
        recommendations = self._generate_recommendations(results)
        
        suite_result = RegressionTestSuiteResult(
            suite_name=suite_name,
            start_time=start_time,
            end_time=end_time,
            total_duration=total_duration,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            error_tests=error_tests,
            skipped_tests=skipped_tests,
            regression_detected_tests=regression_detected_tests,
            improvement_tests=improvement_tests,
            pass_rate=pass_rate,
            test_results=results,
            regression_summary=regression_summary,
            performance_summary=performance_summary,
            historical_comparison=historical_comparison,
            recommendations=recommendations
        )
        
        self.suite_results.append(suite_result)
        
        self.logger.info(
            f"Suite {suite_name} completed: {passed_tests}/{total_tests} passed "
            f"({pass_rate:.1f}% pass rate), {regression_detected_tests} regressions detected"
        )
        
        return suite_result
    
    async def _execute_tests_parallel(self, test_ids: List[str]) -> List[RegressionTestResult]:
        """Execute tests in parallel"""
        tasks = []
        for test_id in test_ids:
            task = self.execute_test_case(test_id)
            tasks.append(task)
        return await asyncio.gather(*tasks, return_exceptions=False)
    
    async def _execute_tests_sequential(self, test_ids: List[str]) -> List[RegressionTestResult]:
        """Execute tests sequentially"""
        results = []
        for test_id in test_ids:
            result = await self.execute_test_case(test_id)
            results.append(result)
        return results
    
    def _generate_regression_summary(self, results: List[RegressionTestResult]) -> Dict[str, Any]:
        """Generate summary of regression test results"""
        if not results:
            return {}
        
        # Group results by regression type
        regression_types = {}
        for result in results:
            regression_type = result.test_case.regression_type.value
            if regression_type not in regression_types:
                regression_types[regression_type] = {
                    'total': 0,
                    'passed': 0,
                    'failed': 0,
                    'regressions': 0,
                    'improvements': 0,
                    'errors': 0
                }
            regression_types[regression_type]['total'] += 1
            if result.status == RegressionStatus.PASSED:
                regression_types[regression_type]['passed'] += 1
            elif result.status == RegressionStatus.FAILED:
                regression_types[regression_type]['failed'] += 1
            elif result.status == RegressionStatus.REGRESSION_DETECTED:
                regression_types[regression_type]['regressions'] += 1
            elif result.status == RegressionStatus.IMPROVEMENT:
                regression_types[regression_type]['improvements'] += 1
            elif result.status == RegressionStatus.ERROR:
                regression_types[regression_type]['errors'] += 1
        
        return regression_types
    
    def _generate_performance_summary(self, results: List[RegressionTestResult]) -> Dict[str, Any]:
        """Generate performance summary"""
        performance_stats = {
            'total_performance_tests': 0,
            'regressions_detected': 0,
            'improvements_detected': 0,
            'average_performance_degradation': 0.0,
            'worst_performance_degradation': 0.0
        }
        
        performance_degradations = []
        
        for result in results:
            if result.test_case.regression_type == RegressionTestType.PERFORMANCE:
                performance_stats['total_performance_tests'] += 1
                if result.regression_detected:
                    performance_stats['regressions_detected'] += 1
                if result.improvement_detected:
                    performance_stats['improvements_detected'] += 1
                
                # Calculate performance degradation
                for metric_name, current_value in result.test_metrics.items():
                    if metric_name in result.baseline_metrics:
                        baseline_value = result.baseline_metrics[metric_name]
                        if isinstance(current_value, (int, float)) and isinstance(baseline_value, (int, float)):
                            if baseline_value > 0:
                                degradation = (current_value / baseline_value - 1) * 100
                                performance_degradations.append(degradation)
        
        if performance_degradations:
            performance_stats['average_performance_degradation'] = sum(performance_degradations) / len(performance_degradations)
            performance_stats['worst_performance_degradation'] = max(performance_degradations)
        
        return performance_stats
    
    def _generate_historical_comparison(self, results: List[RegressionTestResult]) -> Dict[str, Any]:
        """Generate historical comparison data"""
        historical_stats = {
            'tests_with_history': 0,
            'consistent_tests': 0,
            'improved_tests': 0,
            'degraded_tests': 0
        }
        
        # In a real implementation, this would analyze historical data
        # For now, we'll use the current results
        for result in results:
            historical_stats['tests_with_history'] += 1
            if result.improvement_detected:
                historical_stats['improved_tests'] += 1
            elif result.regression_detected:
                historical_stats['degraded_tests'] += 1
            else:
                historical_stats['consistent_tests'] += 1
        
        return historical_stats
    
    def _generate_recommendations(self, results: List[RegressionTestResult]) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        regression_results = [r for r in results if r.status == RegressionStatus.REGRESSION_DETECTED]
        failed_results = [r for r in results if r.status == RegressionStatus.FAILED]
        performance_regressions = [r for r in results if r.performance_regressions]
        
        if regression_results:
            recommendations.append(
                f"Critical: {len(regression_results)} regressions detected - "
                f"investigate immediately to prevent user impact"
            )
        
        if failed_results:
            recommendations.append(
                f"Address {len(failed_results)} failed regression tests to improve system stability"
            )
        
        if performance_regressions:
            total_performance_issues = sum(len(r.performance_regressions) for r in performance_regressions)
            recommendations.append(
                f"Optimize {len(performance_regressions)} tests with performance regressions "
                f"({total_performance_issues} specific performance issues)"
            )
        
        # Critical performance degradations
        critical_degradations = []
        for result in performance_regressions:
            for regression in result.performance_regressions:
                if "degradation" in regression:
                    # Extract degradation percentage
                    try:
                        degradation_str = regression.split("(")[1].split("%")[0]
                        degradation = float(degradation_str)
                        if degradation > 50:  # More than 50% degradation
                            critical_degradations.append((result.test_case.test_name, degradation))
                    except:
                        pass
        
        if critical_degradations:
            recommendations.append(
                f"Critical performance degradations detected in {len(critical_degradations)} tests "
                f"(worst: {max(critical_degradations, key=lambda x: x[1])[1]:.1f}% degradation)"
            )
        
        return recommendations
    
    def generate_comprehensive_report(self, suite_result: RegressionTestSuiteResult) -> str:
        """
        Generate a comprehensive regression test report.
        
        Args:
            suite_result: The test suite result to generate report for
            
        Returns:
            Formatted test report string
        """
        report_lines = [
            "=" * 80,
            "REGRESSION TEST SUITE REPORT",
            "=" * 80,
            f"Suite Name: {suite_result.suite_name}",
            f"Execution Time: {suite_result.start_time.strftime('%Y-%m-%d %H:%M:%S')} - "
            f"{suite_result.end_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Duration: {suite_result.total_duration:.2f} seconds",
            "",
            "SUMMARY",
            "-" * 40,
            f"Total Tests: {suite_result.total_tests}",
            f"Passed: {suite_result.passed_tests}",
            f"Failed: {suite_result.failed_tests}",
            f"Errors: {suite_result.error_tests}",
            f"Skipped: {suite_result.skipped_tests}",
            f"Regressions Detected: {suite_result.regression_detected_tests}",
            f"Improvements: {suite_result.improvement_tests}",
            f"Pass Rate: {suite_result.pass_rate:.1f}%",
            ""
        ]
        
        # Regression summary
        if suite_result.regression_summary:
            report_lines.extend([
                "REGRESSION TYPE SUMMARY",
                "-" * 40
            ])
            for regression_type, stats in suite_result.regression_summary.items():
                success_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
                report_lines.append(
                    f"{regression_type.upper()}: {stats['passed']}/{stats['total']} "
                    f"({success_rate:.1f}% success) | "
                    f"Regressions: {stats['regressions']} | "
                    f"Improvements: {stats['improvements']}"
                )
            report_lines.append("")
        
        # Performance summary
        if suite_result.performance_summary:
            perf = suite_result.performance_summary
            report_lines.extend([
                "PERFORMANCE SUMMARY",
                "-" * 40,
                f"Performance Tests: {perf['total_performance_tests']}",
                f"Performance Regressions: {perf['regressions_detected']}",
                f"Performance Improvements: {perf['improvements_detected']}",
                f"Average Performance Degradation: {perf['average_performance_degradation']:.2f}%",
                f"Worst Performance Degradation: {perf['worst_performance_degradation']:.2f}%",
                ""
            ])
        
        # Historical comparison
        if suite_result.historical_comparison:
            hist = suite_result.historical_comparison
            report_lines.extend([
                "HISTORICAL COMPARISON",
                "-" * 40,
                f"Tests with History: {hist['tests_with_history']}",
                f"Consistent Tests: {hist['consistent_tests']}",
                f"Improved Tests: {hist['improved_tests']}",
                f"Degraded Tests: {hist['degraded_tests']}",
                ""
            ])
        
        # Regression details
        regression_tests = [r for r in suite_result.test_results if r.status == RegressionStatus.REGRESSION_DETECTED]
        if regression_tests:
            report_lines.extend([
                "REGRESSIONS DETECTED (CRITICAL)",
                "-" * 40
            ])
            for result in regression_tests[:10]:  # Limit to first 10 regressions
                report_lines.extend([
                    f"Test: {result.test_case.test_name}",
                    f"  Type: {result.test_case.regression_type.value}",
                    f"  Duration: {result.total_duration:.3f}s",
                    f"  Performance Regressions: {len(result.performance_regressions)}",
                    f"  Functional Regressions: {len(result.functional_regressions)}"
                ])
                # Add specific performance regressions
                for perf_regression in result.performance_regressions[:3]:  # Limit to first 3
                    report_lines.append(f"    - {perf_regression}")
                if len(result.performance_regressions) > 3:
                    report_lines.append(f"    ... and {len(result.performance_regressions) - 3} more")
                report_lines.append("")
            if len(regression_tests) > 10:
                report_lines.append(f"... and {len(regression_tests) - 10} more regressions")
                report_lines.append("")
        
        # Failed tests details
        failed_tests = [r for r in suite_result.test_results if r.status == RegressionStatus.FAILED]
        if failed_tests:
            report_lines.extend([
                "FAILED TESTS",
                "-" * 40
            ])
            for result in failed_tests[:10]:  # Limit to first 10 failures
                report_lines.extend([
                    f"Test: {result.test_case.test_name}",
                    f"  Type: {result.test_case.regression_type.value}",
                    f"  Duration: {result.total_duration:.3f}s",
                    f"  Error: {result.error_message}",
                    ""
                ])
            if len(failed_tests) > 10:
                report_lines.append(f"... and {len(failed_tests) - 10} more failures")
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
async def example_functional_test():
    """Example functional regression test function"""
    # Simulate some functional testing
    await asyncio.sleep(0.1)
    return {
        'results': {
            'function_a_result': 'success',
            'function_b_result': 'success',
            'function_c_result': 'success'
        },
        'metrics': {
            'test_execution_time': 0.1,
            'memory_usage_mb': 50
        }
    }


async def example_performance_test():
    """Example performance regression test function"""
    # Simulate some performance testing
    start_time = time.time()
    await asyncio.sleep(0.05)  # Simulate work
    end_time = time.time()
    
    return {
        'metrics': {
            'execution_time_ms': (end_time - start_time) * 1000,
            'throughput_ops_per_sec': 1000,
            'memory_peak_mb': 75
        }
    }


async def example_regression_validation(test_result: Dict[str, Any], baseline_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Example regression validation function"""
    # Simulate regression validation
    await asyncio.sleep(0.02)
    return {
        'test_passed': True,
        'test_metrics': test_result.get('metrics', {}),
        'baseline_metrics': baseline_data.get('metrics', {}) if baseline_data else {},
        'regression_detected': False,
        'improvement_detected': False
    }


# Example of how to use the regression test runner
if __name__ == "__main__":
    # Example usage
    async def main():
        config = {
            'baseline_storage_path': './test_baselines',
            'historical_data_path': './test_history',
            'performance_degradation_threshold': 0.1,
            'enable_performance_regression_detection': True,
            'enable_functional_regression_detection': True
        }
        
        runner = RegressionTestRunner(config)
        
        # Register test cases
        runner.register_functional_regression_test(
            "Core Functionality Test",
            example_functional_test,
            example_regression_validation,
            baseline_data={
                'results': {
                    'function_a_result': 'success',
                    'function_b_result': 'success',
                    'function_c_result': 'success'
                },
                'metrics': {
                    'test_execution_time': 0.09,
                    'memory_usage_mb': 45
                }
            }
        )
        
        runner.register_performance_regression_test(
            "Performance Benchmark Test",
            example_performance_test,
            {
                PerformanceMetricType.EXECUTION_TIME: 100.0,  # ms
                PerformanceMetricType.THROUGHPUT: 950.0  # ops/sec
            },
            baseline_data={
                'metrics': {
                    'execution_time_ms': 95.0,
                    'throughput_ops_per_sec': 1050.0,
                    'memory_peak_mb': 70
                }
            }
        )
        
        # Execute test suite
        suite_result = await runner.execute_test_suite("Example Regression Suite")
        
        # Generate report
        report = runner.generate_comprehensive_report(suite_result)
        print(report)
    
    # Run the example
    asyncio.run(main())