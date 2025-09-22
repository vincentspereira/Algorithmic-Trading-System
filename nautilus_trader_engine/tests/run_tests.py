#!/usr/bin/env python3
"""
Test Runner Script for Nautilus Trader Engine.

This script provides a comprehensive test execution environment with:
- Automated test discovery and execution
- Coverage analysis and reporting
- Performance benchmarking
- Stress testing capabilities
- CI/CD integration
- Quality gate enforcement
- Detailed reporting and analytics

Usage:
    python run_tests.py [options]

Options:
    --unit              Run unit tests only
    --integration       Run integration tests only
    --performance       Run performance tests only
    --stress           Run stress tests only
    --all              Run all test types (default)
    --coverage         Generate coverage report
    --html-report      Generate HTML coverage report
    --fail-fast        Stop on first failure
    --verbose          Verbose output
    --parallel         Run tests in parallel
    --ci               CI mode (stricter checks)
"""

import sys
import os
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import subprocess
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from nautilus_trader_engine.tests.coverage_analyzer import CoverageAnalyzer, run_coverage_analysis
from nautilus_trader_engine.tests.testing_framework import get_test_runner, TestSuiteResult


class TestRunner:
    """
    Comprehensive test runner for the Nautilus Trader Engine.

    Features:
    - Multi-type test execution (unit, integration, performance, stress)
    - Coverage analysis and quality gates
    - Parallel execution support
    - CI/CD integration
    - Detailed reporting and analytics
    - Performance benchmarking
    """

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_results: Dict[str, Any] = {}
        self.coverage_report = None

    def run_tests(self, test_types: List[str] = None, **kwargs) -> bool:
        """
        Run tests with specified configuration.

        Args:
            test_types: List of test types to run
            **kwargs: Additional configuration options

        Returns:
            Success status
        """
        if test_types is None:
            test_types = ['unit', 'integration']

        print("=" * 80)
        print("NAUTILUS TRADER ENGINE - TEST SUITE")
        print("=" * 80)

        start_time = time.time()
        overall_success = True

        # Run each test type
        for test_type in test_types:
            print(f"\n{'='*50}")
            print(f"Running {test_type.upper()} tests")
            print(f"{'='*50}")

            success = self._run_test_type(test_type, **kwargs)
            overall_success &= success

            if kwargs.get('fail_fast') and not success:
                print("❌ FAIL-FAST: Stopping due to test failure")
                break

        # Generate coverage report if requested
        if kwargs.get('coverage') and overall_success:
            print(f"\n{'='*50}")
            print("GENERATING COVERAGE REPORT")
            print(f"{'='*50}")

            self._generate_coverage_report(**kwargs)

        # Print summary
        self._print_summary(start_time, overall_success)

        return overall_success

    def _run_test_type(self, test_type: str, **kwargs) -> bool:
        """Run a specific type of tests."""
        try:
            if test_type == 'unit':
                return self._run_unit_tests(**kwargs)
            elif test_type == 'integration':
                return self._run_integration_tests(**kwargs)
            elif test_type == 'performance':
                return self._run_performance_tests(**kwargs)
            elif test_type == 'stress':
                return self._run_stress_tests(**kwargs)
            else:
                print(f"❌ Unknown test type: {test_type}")
                return False

        except Exception as e:
            print(f"❌ Failed to run {test_type} tests: {e}")
            return False

    def _run_unit_tests(self, **kwargs) -> bool:
        """Run unit tests."""
        cmd = [
            sys.executable, '-m', 'pytest',
            'nautilus_trader_engine/tests/unit/',
            '-v',
            '--tb=short',
            '-m', 'unit'
        ]

        if kwargs.get('parallel'):
            cmd.extend(['-n', 'auto'])

        if kwargs.get('fail_fast'):
            cmd.append('--exitfirst')

        return self._execute_command(cmd, "Unit Tests")

    def _run_integration_tests(self, **kwargs) -> bool:
        """Run integration tests."""
        cmd = [
            sys.executable, '-m', 'pytest',
            'nautilus_trader_engine/tests/integration/',
            '-v',
            '--tb=short',
            '-m', 'integration'
        ]

        if kwargs.get('fail_fast'):
            cmd.append('--exitfirst')

        return self._execute_command(cmd, "Integration Tests")

    def _run_performance_tests(self, **kwargs) -> bool:
        """Run performance tests."""
        cmd = [
            sys.executable, '-m', 'pytest',
            'nautilus_trader_engine/tests/performance/',
            '-v',
            '--tb=short',
            '-m', 'performance',
            '--durations=10'
        ]

        return self._execute_command(cmd, "Performance Tests")

    def _run_stress_tests(self, **kwargs) -> bool:
        """Run stress tests."""
        cmd = [
            sys.executable, '-m', 'pytest',
            'nautilus_trader_engine/tests/stress/',
            '-v',
            '--tb=short',
            '-m', 'stress'
        ]

        return self._execute_command(cmd, "Stress Tests")

    def _execute_command(self, cmd: List[str], test_name: str) -> bool:
        """Execute a test command and return success status."""
        try:
            print(f"Executing: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )

            # Print output
            if result.stdout:
                print(result.stdout)

            if result.stderr:
                print("STDERR:", result.stderr, file=sys.stderr)

            success = result.returncode == 0

            if success:
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED (exit code: {result.returncode})")

            return success

        except subprocess.TimeoutExpired:
            print(f"❌ {test_name} TIMED OUT")
            return False
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
            return False

    def _generate_coverage_report(self, **kwargs):
        """Generate coverage report."""
        try:
            output_format = 'html' if kwargs.get('html_report') else 'text'
            report = run_coverage_analysis(
                target_coverage=95.0,
                output_format=output_format,
                save_report=True
            )

            self.coverage_report = report

            # Check coverage thresholds
            analyzer = CoverageAnalyzer(target_coverage=95.0)
            coverage_ok = analyzer.check_coverage_thresholds(report)

            if coverage_ok:
                print("✅ Coverage requirements met")
            else:
                print("❌ Coverage requirements not met")

            return coverage_ok

        except Exception as e:
            print(f"❌ Coverage analysis failed: {e}")
            return False

    def _print_summary(self, start_time: float, overall_success: bool):
        """Print test execution summary."""
        total_time = time.time() - start_time

        print(f"\n{'='*80}")
        print("TEST EXECUTION SUMMARY")
        print(f"{'='*80}")

        print(f"Total execution time: {total_time:.2f} seconds")

        if overall_success:
            print("🎉 ALL TESTS PASSED")
            exit_code = 0
        else:
            print("💥 SOME TESTS FAILED")
            exit_code = 1

        if self.coverage_report:
            print(".1f")
            print(".1f")

        print(f"Exit code: {exit_code}")
        return exit_code


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test Runner for Nautilus Trader Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Test type selection
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument('--unit', action='store_true', help='Run unit tests only')
    test_group.add_argument('--integration', action='store_true', help='Run integration tests only')
    test_group.add_argument('--performance', action='store_true', help='Run performance tests only')
    test_group.add_argument('--stress', action='store_true', help='Run stress tests only')
    test_group.add_argument('--all', action='store_true', default=True, help='Run all test types')

    # Options
    parser.add_argument('--coverage', action='store_true', help='Generate coverage report')
    parser.add_argument('--html-report', action='store_true', help='Generate HTML coverage report')
    parser.add_argument('--fail-fast', action='store_true', help='Stop on first failure')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--parallel', action='store_true', help='Run tests in parallel')
    parser.add_argument('--ci', action='store_true', help='CI mode (stricter checks)')

    args = parser.parse_args()

    # Determine test types to run
    if args.unit:
        test_types = ['unit']
    elif args.integration:
        test_types = ['integration']
    elif args.performance:
        test_types = ['performance']
    elif args.stress:
        test_types = ['stress']
    else:
        test_types = ['unit', 'integration']  # Default

    # CI mode adjustments
    if args.ci:
        args.coverage = True
        args.fail_fast = True
        # In CI, don't run performance/stress by default unless explicitly requested
        if not any([args.performance, args.stress]):
            test_types = [t for t in test_types if t not in ['performance', 'stress']]

    # Create and run test runner
    runner = TestRunner()
    success = runner.run_tests(
        test_types=test_types,
        coverage=args.coverage,
        html_report=args.html_report,
        fail_fast=args.fail_fast,
        verbose=args.verbose,
        parallel=args.parallel,
        ci=args.ci
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()