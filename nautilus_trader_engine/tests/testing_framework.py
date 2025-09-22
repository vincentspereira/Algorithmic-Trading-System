"""
Comprehensive Testing Framework for Nautilus Trader Engine
Provides complete testing infrastructure with unit, integration, performance, and stress tests.
"""

import unittest
import time
import logging
from typing import Dict, List, Any, Optional, Callable, Tuple, Union, Type
from dataclasses import dataclass, field
from enum import Enum
import traceback
from datetime import datetime, timedelta
from collections import defaultdict
import threading
import concurrent.futures
import psutil
import cProfile
import pstats
import io
import gc
from functools import wraps
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock

logger = logging.getLogger(__name__)


class TestType(Enum):
    """Types of tests."""
    UNIT = "unit"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    STRESS = "stress"
    REGRESSION = "regression"
    SMOKE = "smoke"


class TestPriority(Enum):
    """Test priorities."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class TestStatus(Enum):
    """Test execution status."""
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


@dataclass
class TestResult:
    """Result of a test execution."""
    test_name: str
    test_type: TestType
    status: TestStatus
    execution_time: float
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    assertions_passed: int = 0
    assertions_failed: int = 0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestSuiteResult:
    """Result of a test suite execution."""
    suite_name: str
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    error_tests: int = 0
    skipped_tests: int = 0
    timeout_tests: int = 0
    total_execution_time: float = 0.0
    test_results: List[TestResult] = field(default_factory=list)
    coverage_percentage: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PerformanceMetrics:
    """Performance test metrics."""
    operation_name: str
    execution_time: float
    memory_usage: float
    cpu_usage: float
    throughput: float
    latency_p50: float
    latency_p95: float
    latency_p99: float
    error_rate: float
    timestamp: datetime = field(default_factory=datetime.now)


class TestCase(unittest.TestCase):
    """
    Enhanced test case with additional functionality.
    """

    def setUp(self):
        """Set up test case."""
        super().setUp()
        self.start_time = time.time()
        self.memory_start = psutil.Process().memory_info().rss / 1024 / 1024  # MB

    def tearDown(self):
        """Clean up after test case."""
        super().tearDown()
        execution_time = time.time() - self.start_time
        memory_end = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        memory_usage = memory_end - self.memory_start

        # Store metrics for later retrieval
        self._execution_time = execution_time
        self._memory_usage = memory_usage

    def assertDataFrameEqual(self, df1: pd.DataFrame, df2: pd.DataFrame,
                           check_dtype: bool = True, rtol: float = 1e-5, atol: float = 1e-8):
        """Assert that two DataFrames are equal."""
        try:
            pd.testing.assert_frame_equal(df1, df2, check_dtype=check_dtype, rtol=rtol, atol=atol)
        except AssertionError as e:
            self.fail(f"DataFrames are not equal: {e}")

    def assertSeriesEqual(self, s1: pd.Series, s2: pd.Series,
                         check_dtype: bool = True, rtol: float = 1e-5, atol: float = 1e-8):
        """Assert that two Series are equal."""
        try:
            pd.testing.assert_series_equal(s1, s2, check_dtype=check_dtype, rtol=rtol, atol=atol)
        except AssertionError as e:
            self.fail(f"Series are not equal: {e}")

    def assertAlmostEqualRecursive(self, obj1: Any, obj2: Any, rtol: float = 1e-5, atol: float = 1e-8):
        """Assert that two objects are almost equal recursively."""
        if isinstance(obj1, dict) and isinstance(obj2, dict):
            self.assertEqual(set(obj1.keys()), set(obj2.keys()))
            for key in obj1.keys():
                self.assertAlmostEqualRecursive(obj1[key], obj2[key], rtol, atol)
        elif isinstance(obj1, (list, tuple)) and isinstance(obj2, (list, tuple)):
            self.assertEqual(len(obj1), len(obj2))
            for item1, item2 in zip(obj1, obj2):
                self.assertAlmostEqualRecursive(item1, item2, rtol, atol)
        elif isinstance(obj1, (int, float)) and isinstance(obj2, (int, float)):
            self.assertAlmostEqual(obj1, obj2, delta=atol + rtol * abs(obj2))
        else:
            self.assertEqual(obj1, obj2)


class TestDecorator:
    """
    Decorator for test functions with metadata and profiling.
    """

    def __init__(self, test_type: TestType = TestType.UNIT,
                 priority: TestPriority = TestPriority.MEDIUM,
                 timeout: float = 30.0,
                 tags: List[str] = None):
        self.test_type = test_type
        self.priority = priority
        self.timeout = timeout
        self.tags = tags or []

    def __call__(self, func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Add metadata to function
            func._test_metadata = {
                'type': self.test_type,
                'priority': self.priority,
                'timeout': self.timeout,
                'tags': self.tags
            }

            # Profile the function if it's a performance test
            if self.test_type == TestType.PERFORMANCE:
                profiler = cProfile.Profile()
                profiler.enable()

            start_time = time.time()
            memory_start = psutil.Process().memory_info().rss / 1024 / 1024

            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                memory_end = psutil.Process().memory_info().rss / 1024 / 1024
                memory_usage = memory_end - memory_start

                # Store performance metrics
                func._performance_metrics = {
                    'execution_time': execution_time,
                    'memory_usage': memory_usage,
                    'timestamp': datetime.now()
                }

                if self.test_type == TestType.PERFORMANCE:
                    profiler.disable()
                    s = io.StringIO()
                    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
                    ps.print_stats()
                    func._profile_output = s.getvalue()

                return result

            except Exception as e:
                if self.test_type == TestType.PERFORMANCE:
                    profiler.disable()
                raise e

        return wrapper


class TestRunner:
    """
    Advanced test runner with parallel execution and comprehensive reporting.
    """

    def __init__(self, parallel: bool = True, max_workers: int = None):
        self.parallel = parallel
        self.max_workers = max_workers or min(4, psutil.cpu_count())
        self.test_results: List[TestResult] = []
        self.test_suites: Dict[str, TestSuiteResult] = {}

    def run_test_suite(self, test_suite: unittest.TestSuite,
                      suite_name: str = "default") -> TestSuiteResult:
        """Run a test suite with comprehensive tracking."""
        logger.info(f"Running test suite: {suite_name}")

        start_time = time.time()
        suite_result = TestSuiteResult(suite_name=suite_name)

        if self.parallel and len(test_suite) > 1:
            # Run tests in parallel
            results = self._run_parallel(test_suite)
        else:
            # Run tests sequentially
            results = self._run_sequential(test_suite)

        suite_result.test_results = results
        suite_result.total_tests = len(results)
        suite_result.passed_tests = sum(1 for r in results if r.status == TestStatus.PASSED)
        suite_result.failed_tests = sum(1 for r in results if r.status == TestStatus.FAILED)
        suite_result.error_tests = sum(1 for r in results if r.status == TestStatus.ERROR)
        suite_result.skipped_tests = sum(1 for r in results if r.status == TestStatus.SKIPPED)
        suite_result.timeout_tests = sum(1 for r in results if r.status == TestStatus.TIMEOUT)
        suite_result.total_execution_time = time.time() - start_time

        self.test_suites[suite_name] = suite_result
        self.test_results.extend(results)

        logger.info(f"Test suite {suite_name} completed: {suite_result.passed_tests}/{suite_result.total_tests} passed")
        return suite_result

    def _run_sequential(self, test_suite: unittest.TestSuite) -> List[TestResult]:
        """Run tests sequentially."""
        results = []

        for test_group in test_suite:
            if isinstance(test_group, unittest.TestSuite):
                for test_case in test_group:
                    result = self._run_single_test(test_case)
                    results.append(result)
            else:
                result = self._run_single_test(test_group)
                results.append(result)

        return results

    def _run_parallel(self, test_suite: unittest.TestSuite) -> List[TestResult]:
        """Run tests in parallel."""
        test_cases = []

        # Flatten test suite
        for test_group in test_suite:
            if isinstance(test_group, unittest.TestSuite):
                test_cases.extend(test_group)
            else:
                test_cases.append(test_group)

        results = []

        # Run tests in parallel batches
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_test = {
                executor.submit(self._run_single_test, test_case): test_case
                for test_case in test_cases
            }

            for future in concurrent.futures.as_completed(future_to_test):
                result = future.result()
                results.append(result)

        return results

    def _run_single_test(self, test_case: unittest.TestCase) -> TestResult:
        """Run a single test case."""
        test_name = f"{test_case.__class__.__name__}.{test_case._testMethodName}"

        # Get test metadata
        test_metadata = getattr(test_case, '_test_metadata', {})
        test_type = test_metadata.get('type', TestType.UNIT)
        timeout = test_metadata.get('timeout', 30.0)

        start_time = time.time()
        memory_start = psutil.Process().memory_info().rss / 1024 / 1024
        cpu_start = psutil.cpu_percent()

        try:
            # Set up test
            test_case.setUp()

            # Run test with timeout
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(test_case.run)
                result = future.result(timeout=timeout)

            # Clean up
            test_case.tearDown()

            # Get performance metrics
            execution_time = time.time() - start_time
            memory_end = psutil.Process().memory_info().rss / 1024 / 1024
            cpu_end = psutil.cpu_percent()

            memory_usage = memory_end - memory_start
            cpu_usage = (cpu_start + cpu_end) / 2  # Average CPU usage

            return TestResult(
                test_name=test_name,
                test_type=test_type,
                status=TestStatus.PASSED,
                execution_time=execution_time,
                memory_usage=memory_usage,
                cpu_usage=cpu_usage,
                metadata=test_metadata
            )

        except unittest.SkipTest as e:
            return TestResult(
                test_name=test_name,
                test_type=test_type,
                status=TestStatus.SKIPPED,
                execution_time=time.time() - start_time,
                error_message=str(e)
            )

        except concurrent.futures.TimeoutError:
            return TestResult(
                test_name=test_name,
                test_type=test_type,
                status=TestStatus.TIMEOUT,
                execution_time=timeout,
                error_message=f"Test timed out after {timeout} seconds"
            )

        except AssertionError as e:
            return TestResult(
                test_name=test_name,
                test_type=test_type,
                status=TestStatus.FAILED,
                execution_time=time.time() - start_time,
                error_message=str(e),
                stack_trace=traceback.format_exc()
            )

        except Exception as e:
            return TestResult(
                test_name=test_name,
                test_type=test_type,
                status=TestStatus.ERROR,
                execution_time=time.time() - start_time,
                error_message=str(e),
                stack_trace=traceback.format_exc()
            )

    def generate_report(self, format: str = "text") -> str:
        """Generate a comprehensive test report."""
        if format == "text":
            return self._generate_text_report()
        elif format == "json":
            return self._generate_json_report()
        elif format == "html":
            return self._generate_html_report()
        else:
            raise ValueError(f"Unsupported report format: {format}")

    def _generate_text_report(self) -> str:
        """Generate a text-based test report."""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("NAUTILUS TRADER ENGINE - TEST REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")

        total_suites = len(self.test_suites)
        total_tests = sum(suite.total_tests for suite in self.test_suites.values())
        total_passed = sum(suite.passed_tests for suite in self.test_suites.values())
        total_failed = sum(suite.failed_tests for suite in self.test_suites.values())
        total_errors = sum(suite.error_tests for suite in self.test_suites.values())
        total_execution_time = sum(suite.total_execution_time for suite in self.test_suites.values())

        report_lines.append("SUMMARY:")
        report_lines.append(f"  Test Suites: {total_suites}")
        report_lines.append(f"  Total Tests: {total_tests}")
        report_lines.append(f"  Passed: {total_passed}")
        report_lines.append(f"  Failed: {total_failed}")
        report_lines.append(f"  Errors: {total_errors}")
        report_lines.append(".1f")
        report_lines.append(".2f")
        report_lines.append("")

        # Suite details
        for suite_name, suite in self.test_suites.items():
            report_lines.append(f"SUITE: {suite_name}")
            report_lines.append(f"  Tests: {suite.total_tests}")
            report_lines.append(f"  Passed: {suite.passed_tests}")
            report_lines.append(f"  Failed: {suite.failed_tests}")
            report_lines.append(f"  Errors: {suite.error_tests}")
            report_lines.append(".2f")
            report_lines.append("")

            # Failed tests
            failed_results = [r for r in suite.test_results if r.status in [TestStatus.FAILED, TestStatus.ERROR]]
            if failed_results:
                report_lines.append("  FAILED TESTS:")
                for result in failed_results:
                    report_lines.append(f"    {result.test_name}")
                    report_lines.append(f"      Status: {result.status.value}")
                    report_lines.append(f"      Error: {result.error_message}")
                    if result.stack_trace:
                        report_lines.append(f"      Stack Trace: {result.stack_trace[:200]}...")
                    report_lines.append("")

        return "\n".join(report_lines)

    def _generate_json_report(self) -> str:
        """Generate a JSON test report."""
        import json

        report_data = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_suites": len(self.test_suites),
                "total_tests": sum(s.total_tests for s in self.test_suites.values()),
                "total_passed": sum(s.passed_tests for s in self.test_suites.values()),
                "total_failed": sum(s.failed_tests for s in self.test_suites.values()),
                "total_errors": sum(s.error_tests for s in self.test_suites.values()),
                "total_execution_time": sum(s.total_execution_time for s in self.test_suites.values())
            },
            "suites": {}
        }

        for suite_name, suite in self.test_suites.items():
            report_data["suites"][suite_name] = {
                "total_tests": suite.total_tests,
                "passed_tests": suite.passed_tests,
                "failed_tests": suite.failed_tests,
                "error_tests": suite.error_tests,
                "execution_time": suite.total_execution_time,
                "tests": [
                    {
                        "name": result.test_name,
                        "status": result.status.value,
                        "execution_time": result.execution_time,
                        "error_message": result.error_message,
                        "memory_usage": result.memory_usage,
                        "cpu_usage": result.cpu_usage
                    }
                    for result in suite.test_results
                ]
            }

        return json.dumps(report_data, indent=2)

    def _generate_html_report(self) -> str:
        """Generate an HTML test report."""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Nautilus Trader Engine - Test Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .summary { background-color: #f0f0f0; padding: 20px; border-radius: 5px; }
                .suite { margin: 20px 0; padding: 10px; border: 1px solid #ddd; }
                .passed { color: green; }
                .failed { color: red; }
                .error { color: orange; }
                .test { margin: 5px 0; padding: 5px; }
            </style>
        </head>
        <body>
            <h1>Nautilus Trader Engine - Test Report</h1>
            <p>Generated: {timestamp}</p>

            <div class="summary">
                <h2>Summary</h2>
                <p>Test Suites: {total_suites}</p>
                <p>Total Tests: {total_tests}</p>
                <p>Passed: <span class="passed">{total_passed}</span></p>
                <p>Failed: <span class="failed">{total_failed}</span></p>
                <p>Errors: <span class="error">{total_errors}</span></p>
                <p>Total Execution Time: {total_time:.2f}s</p>
            </div>

            {suite_details}
        </body>
        </html>
        """

        total_suites = len(self.test_suites)
        total_tests = sum(s.total_tests for s in self.test_suites.values())
        total_passed = sum(s.passed_tests for s in self.test_suites.values())
        total_failed = sum(s.failed_tests for s in self.test_suites.values())
        total_errors = sum(s.error_tests for s in self.test_suites.values())
        total_time = sum(s.total_execution_time for s in self.test_suites.values())

        suite_details = []
        for suite_name, suite in self.test_suites.items():
            suite_html = f"<div class='suite'><h3>{suite_name}</h3>"
            suite_html += f"<p>Tests: {suite.total_tests}, Passed: {suite.passed_tests}, Failed: {suite.failed_tests}</p>"

            for result in suite.test_results:
                status_class = result.status.value
                suite_html += f"<div class='test {status_class}'>{result.test_name} - {result.status.value}</div>"

            suite_html += "</div>"
            suite_details.append(suite_html)

        return html_template.format(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            total_suites=total_suites,
            total_tests=total_tests,
            total_passed=total_passed,
            total_failed=total_failed,
            total_errors=total_errors,
            total_time=total_time,
            suite_details="".join(suite_details)
        )


class PerformanceTestRunner:
    """
    Specialized runner for performance tests.
    """

    def __init__(self, iterations: int = 100, warmup_iterations: int = 10):
        self.iterations = iterations
        self.warmup_iterations = warmup_iterations
        self.results: List[PerformanceMetrics] = []

    def run_performance_test(self, operation: Callable, operation_name: str,
                           *args, **kwargs) -> PerformanceMetrics:
        """Run a performance test for an operation."""
        logger.info(f"Running performance test: {operation_name}")

        # Warmup
        for _ in range(self.warmup_iterations):
            operation(*args, **kwargs)

        # Performance test
        execution_times = []
        memory_usages = []
        cpu_usages = []

        for _ in range(self.iterations):
            gc.collect()  # Clean up before each iteration

            memory_start = psutil.Process().memory_info().rss / 1024 / 1024
            cpu_start = psutil.cpu_percent()
            start_time = time.time()

            try:
                result = operation(*args, **kwargs)
                execution_time = time.time() - start_time
                memory_end = psutil.Process().memory_info().rss / 1024 / 1024
                cpu_end = psutil.cpu_percent()

                execution_times.append(execution_time)
                memory_usages.append(memory_end - memory_start)
                cpu_usages.append((cpu_start + cpu_end) / 2)

            except Exception as e:
                logger.error(f"Performance test iteration failed: {e}")
                continue

        if not execution_times:
            raise RuntimeError("All performance test iterations failed")

        # Calculate metrics
        execution_times_array = np.array(execution_times)
        avg_execution_time = np.mean(execution_times_array)
        throughput = self.iterations / sum(execution_times)

        metrics = PerformanceMetrics(
            operation_name=operation_name,
            execution_time=avg_execution_time,
            memory_usage=np.mean(memory_usages),
            cpu_usage=np.mean(cpu_usages),
            throughput=throughput,
            latency_p50=np.percentile(execution_times_array, 50),
            latency_p95=np.percentile(execution_times_array, 95),
            latency_p99=np.percentile(execution_times_array, 99),
            error_rate=0.0  # No errors in successful iterations
        )

        self.results.append(metrics)
        return metrics

    def get_performance_report(self) -> str:
        """Generate performance test report."""
        if not self.results:
            return "No performance test results available"

        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("PERFORMANCE TEST REPORT")
        report_lines.append("=" * 80)

        for metrics in self.results:
            report_lines.append(f"Operation: {metrics.operation_name}")
            report_lines.append(f"  Average Execution Time: {metrics.execution_time:.4f}s")
            report_lines.append(f"  Memory Usage: {metrics.memory_usage:.2f}MB")
            report_lines.append(f"  CPU Usage: {metrics.cpu_usage:.2f}%")
            report_lines.append(f"  Throughput: {metrics.throughput:.2f} ops/sec")
            report_lines.append(f"  Latency P50: {metrics.latency_p50:.4f}s")
            report_lines.append(f"  Latency P95: {metrics.latency_p95:.4f}s")
            report_lines.append(f"  Latency P99: {metrics.latency_p99:.4f}s")
            report_lines.append("")

        return "\n".join(report_lines)


class StressTestRunner:
    """
    Runner for stress tests with load generation.
    """

    def __init__(self, duration: int = 60, concurrent_users: int = 10):
        self.duration = duration
        self.concurrent_users = concurrent_users
        self.results: Dict[str, List] = defaultdict(list)

    def run_stress_test(self, operation: Callable, operation_name: str,
                       *args, **kwargs) -> Dict[str, Any]:
        """Run a stress test with concurrent load."""
        logger.info(f"Running stress test: {operation_name} for {self.duration}s with {self.concurrent_users} users")

        start_time = time.time()
        end_time = start_time + self.duration

        results = {
            'operation_name': operation_name,
            'duration': self.duration,
            'concurrent_users': self.concurrent_users,
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_response_time': 0.0,
            'min_response_time': float('inf'),
            'max_response_time': float('inf'),
            'response_times': [],
            'errors': []
        }

        def worker():
            """Worker function for each concurrent user."""
            while time.time() < end_time:
                request_start = time.time()

                try:
                    operation(*args, **kwargs)
                    response_time = time.time() - request_start

                    results['total_requests'] += 1
                    results['successful_requests'] += 1
                    results['response_times'].append(response_time)
                    results['min_response_time'] = min(results['min_response_time'], response_time)
                    results['max_response_time'] = max(results['max_response_time'], response_time)

                except Exception as e:
                    results['total_requests'] += 1
                    results['failed_requests'] += 1
                    results['errors'].append(str(e))

        # Start worker threads
        threads = []
        for _ in range(self.concurrent_users):
            thread = threading.Thread(target=worker)
            thread.start()
            threads.append(thread)

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Calculate final metrics
        if results['response_times']:
            results['average_response_time'] = np.mean(results['response_times'])
            results['min_response_time'] = min(results['response_times'])
            results['max_response_time'] = max(results['response_times'])

        # Calculate throughput
        results['throughput'] = results['total_requests'] / self.duration
        results['error_rate'] = results['failed_requests'] / max(1, results['total_requests'])

        return results

    def get_stress_report(self, results: Dict[str, Any]) -> str:
        """Generate stress test report."""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("STRESS TEST REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Operation: {results['operation_name']}")
        report_lines.append(f"Duration: {results['duration']}s")
        report_lines.append(f"Concurrent Users: {results['concurrent_users']}")
        report_lines.append(f"Total Requests: {results['total_requests']}")
        report_lines.append(f"Successful Requests: {results['successful_requests']}")
        report_lines.append(f"Failed Requests: {results['failed_requests']}")
        report_lines.append(".2f")
        report_lines.append(".4f")
        report_lines.append(".4f")
        report_lines.append(".4f")
        report_lines.append(".2f")
        report_lines.append("")

        if results['errors']:
            report_lines.append("SAMPLE ERRORS:")
            for error in results['errors'][:5]:  # Show first 5 errors
                report_lines.append(f"  {error}")

        return "\n".join(report_lines)


# Convenience decorators
def unit_test(priority: TestPriority = TestPriority.MEDIUM, timeout: float = 30.0):
    """Decorator for unit tests."""
    return TestDecorator(TestType.UNIT, priority, timeout)


def integration_test(priority: TestPriority = TestPriority.MEDIUM, timeout: float = 60.0):
    """Decorator for integration tests."""
    return TestDecorator(TestType.INTEGRATION, priority, timeout)


def performance_test(priority: TestPriority = TestPriority.HIGH, timeout: float = 300.0):
    """Decorator for performance tests."""
    return TestDecorator(TestType.PERFORMANCE, priority, timeout)


def stress_test(priority: TestPriority = TestPriority.HIGH, timeout: float = 600.0):
    """Decorator for stress tests."""
    return TestDecorator(TestType.STRESS, priority, timeout)


# Global test runner instances
_test_runner = TestRunner()
_performance_runner = PerformanceTestRunner()
_stress_runner = StressTestRunner()


def get_test_runner() -> TestRunner:
    """Get the global test runner."""
    return _test_runner


def get_performance_runner() -> PerformanceTestRunner:
    """Get the global performance test runner."""
    return _performance_runner


def get_stress_runner() -> StressTestRunner:
    """Get the global stress test runner."""
    return _stress_runner


if __name__ == "__main__":
    # Example usage
    import sys
    import os

    # Add the project root to the path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Create a simple test
    class ExampleTest(TestCase):
        @unit_test()
        def test_simple_assertion(self):
            self.assertEqual(1 + 1, 2)

        @performance_test()
        def test_performance_operation(self):
            # Simulate some work
            time.sleep(0.01)
            return sum(range(1000))

    # Run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(ExampleTest)

    runner = get_test_runner()
    result = runner.run_test_suite(suite, "example_suite")

    # Generate report
    report = runner.generate_report("text")
    print(report)

    # Performance test
    def sample_operation(n):
        return sum(i * i for i in range(n))

    perf_runner = get_performance_runner()
    metrics = perf_runner.run_performance_test(sample_operation, "sum_of_squares", 1000)
    perf_report = perf_runner.get_performance_report()
    print(perf_report)

    # Stress test
    stress_runner = get_stress_runner()
    stress_results = stress_runner.run_stress_test(sample_operation, "stress_sum_of_squares", 1000)
    stress_report = stress_runner.get_stress_report(stress_results)
    print(stress_report)