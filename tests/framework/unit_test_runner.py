"""
Unit Test Runner for Testing Framework

This module provides comprehensive unit testing infrastructure with 100% coverage
requirement, pytest execution with coverage tracking, and detailed reporting.
"""

import os
import sys
import subprocess
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union, Set
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime, timedelta
import re
import ast
import importlib.util
import coverage
import pytest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """Test execution status enumeration"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    XFAIL = "xfail"
    XPASS = "xpass"
    UNKNOWN = "unknown"


class CoverageStatus(Enum):
    """Coverage status enumeration"""
    EXCELLENT = "excellent"  # 95-100%
    GOOD = "good"           # 85-94%
    ACCEPTABLE = "acceptable"  # 75-84%
    POOR = "poor"           # 60-74%
    CRITICAL = "critical"   # <60%


@dataclass
class TestResult:
    """Individual test result information"""
    name: str
    status: TestStatus
    duration: float
    file_path: str
    line_number: Optional[int] = None
    error_message: Optional[str] = None
    failure_message: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CoverageInfo:
    """Coverage information for a file or module"""
    file_path: str
    total_lines: int
    covered_lines: int
    missing_lines: List[int]
    excluded_lines: List[int]
    coverage_percentage: float
    status: CoverageStatus
    branch_coverage: Optional[float] = None
    missing_branches: List[Tuple[int, int]] = field(default_factory=list)


@dataclass
class TestSuiteResult:
    """Test suite execution results"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    error_tests: int
    total_duration: float
    test_results: List[TestResult]
    coverage_info: Dict[str, CoverageInfo]
    overall_coverage: float
    coverage_status: CoverageStatus
    execution_timestamp: datetime
    command_line: str
    exit_code: int
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class CoverageReport:
    """Detailed coverage report"""
    overall_coverage: float
    line_coverage: float
    branch_coverage: float
    total_files: int
    covered_files: int
    uncovered_files: List[str]
    file_coverage: Dict[str, CoverageInfo]
    missing_coverage_details: Dict[str, List[int]]
    coverage_by_directory: Dict[str, float]
    status: CoverageStatus
    report_timestamp: datetime


class UnitTestRunner:
    """
    Manages unit test execution with comprehensive coverage tracking.
    
    This class handles pytest execution, 100% coverage validation,
    detailed reporting, and line-by-line coverage analysis.
    """
    
    def __init__(self, project_root: Optional[Path] = None, src_directories: Optional[List[str]] = None):
        """
        Initialize the UnitTestRunner.
        
        Args:
            project_root: Path to the project root directory. If None, uses current directory.
            src_directories: List of source directories to analyze for coverage. If None, uses common patterns.
        """
        self.project_root = project_root or Path.cwd()
        self.src_directories = src_directories or self._discover_source_directories()
        
        # Configuration
        self.coverage_threshold = 100.0  # 100% coverage requirement
        self.min_acceptable_coverage = 75.0
        self.pytest_timeout = 300  # 5 minutes default timeout
        self.max_test_duration = 30.0  # Maximum duration for a single test
        
        # Coverage configuration
        self.coverage_config = {
            'source': self.src_directories,
            'omit': [
                '*/tests/*',
                '*/test_*',
                '*/__pycache__/*',
                '*/venv/*',
                '*/.venv/*',
                '*/migrations/*',
                '*/settings/*',
                '*/config/*'
            ],
            'include': ['*.py'],
            'exclude_lines': [
                'pragma: no cover',
                'def __repr__',
                'if self.debug:',
                'if settings.DEBUG',
                'raise AssertionError',
                'raise NotImplementedError',
                'if 0:',
                'if __name__ == .__main__.:',
                r'class .*\bProtocol\):',
                r'@(abc\.)?abstractmethod'
            ]
        }
        
        # Test discovery patterns
        self.test_patterns = [
            'test_*.py',
            '*_test.py',
            'tests.py'
        ]
        
        # Initialize coverage instance
        self.coverage_instance = None
        self._setup_coverage()
    
    def _discover_source_directories(self) -> List[str]:
        """Discover source directories in the project."""
        potential_dirs = [
            'src', 'lib', 'app', 'core', 'api', 'services', 'models',
            'nautilus_trader_engine', 'market_data_service', 'order_management',
            'database', 'shared', 'kafka_service', 'backtesting'
        ]
        
        discovered_dirs = []
        for dir_name in potential_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists() and dir_path.is_dir():
                # Check if it contains Python files
                if any(dir_path.rglob('*.py')):
                    discovered_dirs.append(str(dir_path))
        
        # If no specific source directories found, use project root
        if not discovered_dirs:
            discovered_dirs = [str(self.project_root)]
        
        logger.info(f"Discovered source directories: {discovered_dirs}")
        return discovered_dirs
    
    def _setup_coverage(self) -> None:
        """Setup coverage measurement configuration."""
        try:
            self.coverage_instance = coverage.Coverage(
                source=self.coverage_config['source'],
                omit=self.coverage_config['omit'],
                include=self.coverage_config['include']
            )
            
            # Configure exclusions
            for line in self.coverage_config['exclude_lines']:
                self.coverage_instance.exclude(line)
                
            logger.info("Coverage measurement configured successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup coverage: {str(e)}")
            self.coverage_instance = None
    
    def discover_tests(self, test_directories: Optional[List[str]] = None) -> List[str]:
        """
        Discover test files in the project.
        
        Args:
            test_directories: List of directories to search for tests. If None, searches common locations.
            
        Returns:
            List[str]: List of discovered test file paths
        """
        if test_directories is None:
            test_directories = ['tests', 'test', '.']
        
        discovered_tests = []
        
        for test_dir in test_directories:
            test_path = self.project_root / test_dir
            if test_path.exists():
                for pattern in self.test_patterns:
                    test_files = list(test_path.rglob(pattern))
                    discovered_tests.extend([str(f) for f in test_files])
        
        # Remove duplicates and sort
        discovered_tests = sorted(list(set(discovered_tests)))
        
        logger.info(f"Discovered {len(discovered_tests)} test files")
        return discovered_tests
    
    def run_tests_with_coverage(self, test_paths: Optional[List[str]] = None, 
                               pytest_args: Optional[List[str]] = None) -> TestSuiteResult:
        """
        Run tests with coverage measurement.
        
        Args:
            test_paths: List of specific test paths to run. If None, discovers all tests.
            pytest_args: Additional pytest arguments.
            
        Returns:
            TestSuiteResult: Comprehensive test execution results
        """
        logger.info("Starting test execution with coverage measurement...")
        
        start_time = datetime.now()
        
        # Discover tests if not provided
        if test_paths is None:
            test_paths = self.discover_tests()
        
        if not test_paths:
            logger.warning("No test files discovered")
            return self._create_empty_result(start_time)
        
        # Prepare pytest command
        pytest_cmd = self._build_pytest_command(test_paths, pytest_args)
        
        # Start coverage measurement
        if self.coverage_instance:
            self.coverage_instance.start()
        
        try:
            # Execute tests
            result = subprocess.run(
                pytest_cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=self.pytest_timeout
            )
            
            # Stop coverage measurement
            if self.coverage_instance:
                self.coverage_instance.stop()
                self.coverage_instance.save()
            
            # Parse test results
            test_results = self._parse_pytest_output(result.stdout, result.stderr)
            
            # Generate coverage report
            coverage_info, overall_coverage = self._generate_coverage_report()
            
            # Create comprehensive result
            suite_result = TestSuiteResult(
                total_tests=len(test_results),
                passed_tests=sum(1 for t in test_results if t.status == TestStatus.PASSED),
                failed_tests=sum(1 for t in test_results if t.status == TestStatus.FAILED),
                skipped_tests=sum(1 for t in test_results if t.status == TestStatus.SKIPPED),
                error_tests=sum(1 for t in test_results if t.status == TestStatus.ERROR),
                total_duration=(datetime.now() - start_time).total_seconds(),
                test_results=test_results,
                coverage_info=coverage_info,
                overall_coverage=overall_coverage,
                coverage_status=self._determine_coverage_status(overall_coverage),
                execution_timestamp=start_time,
                command_line=' '.join(pytest_cmd),
                exit_code=result.returncode
            )
            
            # Validate coverage requirements
            self._validate_coverage_requirements(suite_result)
            
            logger.info(f"Test execution completed: {suite_result.passed_tests}/{suite_result.total_tests} passed, {overall_coverage:.2f}% coverage")
            return suite_result
            
        except subprocess.TimeoutExpired:
            logger.error(f"Test execution timed out after {self.pytest_timeout} seconds")
            return self._create_timeout_result(start_time, pytest_cmd)
            
        except Exception as e:
            logger.error(f"Test execution failed: {str(e)}")
            return self._create_error_result(start_time, pytest_cmd, str(e))
    
    def _build_pytest_command(self, test_paths: List[str], pytest_args: Optional[List[str]]) -> List[str]:
        """Build the pytest command with appropriate arguments."""
        cmd = ['python', '-m', 'pytest']
        
        # Add test paths
        cmd.extend(test_paths)
        
        # Add standard arguments
        cmd.extend([
            '-v',  # Verbose output
            '--tb=short',  # Short traceback format
            '--strict-markers',  # Strict marker handling
            '--junit-xml=test-results.xml',  # JUnit XML output
            '--json-report',  # JSON report
            '--json-report-file=test-report.json'
        ])
        
        # Add coverage arguments if coverage is enabled
        if self.coverage_instance:
            cmd.extend([
                '--cov=' + ','.join(self.src_directories),
                '--cov-report=term-missing',
                '--cov-report=html:htmlcov',
                '--cov-report=xml:coverage.xml',
                '--cov-report=json:coverage.json',
                f'--cov-fail-under={self.coverage_threshold}'
            ])
        
        # Add custom pytest arguments
        if pytest_args:
            cmd.extend(pytest_args)
        
        logger.info(f"Pytest command: {' '.join(cmd)}")
        return cmd
    
    def _parse_pytest_output(self, stdout: str, stderr: str) -> List[TestResult]:
        """Parse pytest output to extract test results."""
        test_results = []
        
        try:
            # Try to parse JSON report first
            json_report_path = self.project_root / 'test-report.json'
            if json_report_path.exists():
                test_results = self._parse_json_report(json_report_path)
            else:
                # Fallback to parsing stdout
                test_results = self._parse_stdout_output(stdout)
                
        except Exception as e:
            logger.error(f"Failed to parse test output: {str(e)}")
            # Create basic results from stdout parsing
            test_results = self._parse_stdout_output(stdout)
        
        return test_results
    
    def _parse_json_report(self, json_path: Path) -> List[TestResult]:
        """Parse pytest JSON report."""
        test_results = []
        
        try:
            with open(json_path, 'r') as f:
                report_data = json.load(f)
            
            for test in report_data.get('tests', []):
                status_map = {
                    'PASSED': TestStatus.PASSED,
                    'FAILED': TestStatus.FAILED,
                    'SKIPPED': TestStatus.SKIPPED,
                    'ERROR': TestStatus.ERROR,
                    'XFAIL': TestStatus.XFAIL,
                    'XPASS': TestStatus.XPASS
                }
                
                test_result = TestResult(
                    name=test.get('nodeid', ''),
                    status=status_map.get(test.get('outcome', '').upper(), TestStatus.UNKNOWN),
                    duration=test.get('duration', 0.0),
                    file_path=test.get('file', ''),
                    line_number=test.get('line'),
                    error_message=test.get('call', {}).get('longrepr') if test.get('outcome') == 'ERROR' else None,
                    failure_message=test.get('call', {}).get('longrepr') if test.get('outcome') == 'FAILED' else None,
                    stdout=test.get('call', {}).get('stdout'),
                    stderr=test.get('call', {}).get('stderr')
                )
                
                test_results.append(test_result)
                
        except Exception as e:
            logger.error(f"Failed to parse JSON report: {str(e)}")
        
        return test_results
    
    def _parse_stdout_output(self, stdout: str) -> List[TestResult]:
        """Parse pytest stdout output as fallback."""
        test_results = []
        
        # Simple regex patterns for test results
        patterns = {
            TestStatus.PASSED: r'(.+?)\s+PASSED\s+\[(.+?)\]',
            TestStatus.FAILED: r'(.+?)\s+FAILED\s+\[(.+?)\]',
            TestStatus.SKIPPED: r'(.+?)\s+SKIPPED\s+\[(.+?)\]',
            TestStatus.ERROR: r'(.+?)\s+ERROR\s+\[(.+?)\]'
        }
        
        for status, pattern in patterns.items():
            matches = re.findall(pattern, stdout)
            for match in matches:
                test_name = match[0].strip()
                duration_str = match[1].strip()
                
                # Parse duration
                duration = 0.0
                try:
                    duration = float(duration_str.replace('s', ''))
                except:
                    pass
                
                test_result = TestResult(
                    name=test_name,
                    status=status,
                    duration=duration,
                    file_path=test_name.split('::')[0] if '::' in test_name else ''
                )
                
                test_results.append(test_result)
        
        return test_results
    
    def _generate_coverage_report(self) -> Tuple[Dict[str, CoverageInfo], float]:
        """Generate detailed coverage report."""
        coverage_info = {}
        overall_coverage = 0.0
        
        if not self.coverage_instance:
            return coverage_info, overall_coverage
        
        try:
            # Get coverage data
            self.coverage_instance.load()
            
            # Calculate overall coverage
            overall_coverage = self.coverage_instance.report(show_missing=False)
            
            # Get detailed file coverage
            for file_path in self.coverage_instance.get_data().measured_files():
                try:
                    analysis = self.coverage_instance.analysis2(file_path)
                    
                    total_lines = len(analysis.statements)
                    covered_lines = len(analysis.statements) - len(analysis.missing)
                    coverage_percentage = (covered_lines / total_lines * 100) if total_lines > 0 else 100.0
                    
                    coverage_info[file_path] = CoverageInfo(
                        file_path=file_path,
                        total_lines=total_lines,
                        covered_lines=covered_lines,
                        missing_lines=list(analysis.missing),
                        excluded_lines=list(analysis.excluded),
                        coverage_percentage=coverage_percentage,
                        status=self._determine_coverage_status(coverage_percentage)
                    )
                    
                except Exception as e:
                    logger.warning(f"Failed to analyze coverage for {file_path}: {str(e)}")
            
        except Exception as e:
            logger.error(f"Failed to generate coverage report: {str(e)}")
        
        return coverage_info, overall_coverage
    
    def _determine_coverage_status(self, coverage_percentage: float) -> CoverageStatus:
        """Determine coverage status based on percentage."""
        if coverage_percentage >= 95.0:
            return CoverageStatus.EXCELLENT
        elif coverage_percentage >= 85.0:
            return CoverageStatus.GOOD
        elif coverage_percentage >= 75.0:
            return CoverageStatus.ACCEPTABLE
        elif coverage_percentage >= 60.0:
            return CoverageStatus.POOR
        else:
            return CoverageStatus.CRITICAL
    
    def _validate_coverage_requirements(self, suite_result: TestSuiteResult) -> None:
        """Validate coverage requirements and add warnings/errors."""
        if suite_result.overall_coverage < self.coverage_threshold:
            error_msg = f"Coverage {suite_result.overall_coverage:.2f}% is below required {self.coverage_threshold}%"
            suite_result.errors.append(error_msg)
            logger.error(error_msg)
        
        # Check for files with poor coverage
        poor_coverage_files = [
            file_path for file_path, info in suite_result.coverage_info.items()
            if info.coverage_percentage < self.min_acceptable_coverage
        ]
        
        if poor_coverage_files:
            warning_msg = f"{len(poor_coverage_files)} files have coverage below {self.min_acceptable_coverage}%"
            suite_result.warnings.append(warning_msg)
            logger.warning(warning_msg)
        
        # Check for long-running tests
        slow_tests = [
            test for test in suite_result.test_results
            if test.duration > self.max_test_duration
        ]
        
        if slow_tests:
            warning_msg = f"{len(slow_tests)} tests exceed maximum duration of {self.max_test_duration}s"
            suite_result.warnings.append(warning_msg)
            logger.warning(warning_msg)
    
    def generate_coverage_report_detailed(self) -> CoverageReport:
        """Generate a detailed coverage report with line-by-line analysis."""
        if not self.coverage_instance:
            return self._create_empty_coverage_report()
        
        try:
            self.coverage_instance.load()
            
            # Get overall coverage metrics
            overall_coverage = self.coverage_instance.report(show_missing=False)
            
            # Get file-level coverage
            file_coverage = {}
            missing_coverage_details = {}
            coverage_by_directory = {}
            uncovered_files = []
            
            for file_path in self.coverage_instance.get_data().measured_files():
                try:
                    analysis = self.coverage_instance.analysis2(file_path)
                    
                    total_lines = len(analysis.statements)
                    covered_lines = len(analysis.statements) - len(analysis.missing)
                    coverage_percentage = (covered_lines / total_lines * 100) if total_lines > 0 else 100.0
                    
                    file_coverage[file_path] = CoverageInfo(
                        file_path=file_path,
                        total_lines=total_lines,
                        covered_lines=covered_lines,
                        missing_lines=list(analysis.missing),
                        excluded_lines=list(analysis.excluded),
                        coverage_percentage=coverage_percentage,
                        status=self._determine_coverage_status(coverage_percentage)
                    )
                    
                    if analysis.missing:
                        missing_coverage_details[file_path] = list(analysis.missing)
                    
                    if coverage_percentage == 0:
                        uncovered_files.append(file_path)
                    
                    # Calculate directory coverage
                    directory = str(Path(file_path).parent)
                    if directory not in coverage_by_directory:
                        coverage_by_directory[directory] = []
                    coverage_by_directory[directory].append(coverage_percentage)
                    
                except Exception as e:
                    logger.warning(f"Failed to analyze {file_path}: {str(e)}")
            
            # Calculate average coverage by directory
            for directory in coverage_by_directory:
                coverage_by_directory[directory] = sum(coverage_by_directory[directory]) / len(coverage_by_directory[directory])
            
            return CoverageReport(
                overall_coverage=overall_coverage,
                line_coverage=overall_coverage,  # For now, same as overall
                branch_coverage=0.0,  # Would need branch coverage enabled
                total_files=len(file_coverage),
                covered_files=len([f for f in file_coverage.values() if f.coverage_percentage > 0]),
                uncovered_files=uncovered_files,
                file_coverage=file_coverage,
                missing_coverage_details=missing_coverage_details,
                coverage_by_directory=coverage_by_directory,
                status=self._determine_coverage_status(overall_coverage),
                report_timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to generate detailed coverage report: {str(e)}")
            return self._create_empty_coverage_report()
    
    def validate_100_percent_coverage(self, src_directory: Optional[str] = None) -> Tuple[bool, List[str]]:
        """
        Validate 100% coverage requirement on specified source directory.
        
        Args:
            src_directory: Specific source directory to validate. If None, validates all source directories.
            
        Returns:
            Tuple[bool, List[str]]: Success status and list of issues
        """
        logger.info("Validating 100% coverage requirement...")
        
        issues = []
        
        if not self.coverage_instance:
            issues.append("Coverage measurement not available")
            return False, issues
        
        try:
            self.coverage_instance.load()
            
            # Get coverage data
            coverage_data = self.coverage_instance.get_data()
            
            # Check each measured file
            for file_path in coverage_data.measured_files():
                # Filter by source directory if specified
                if src_directory and not file_path.startswith(src_directory):
                    continue
                
                analysis = self.coverage_instance.analysis2(file_path)
                
                if analysis.missing:
                    missing_lines = list(analysis.missing)
                    issues.append(f"{file_path}: Missing coverage on lines {missing_lines}")
            
            # Check overall coverage
            overall_coverage = self.coverage_instance.report(show_missing=False)
            if overall_coverage < self.coverage_threshold:
                issues.append(f"Overall coverage {overall_coverage:.2f}% is below required {self.coverage_threshold}%")
            
            success = len(issues) == 0
            
            if success:
                logger.info("✅ 100% coverage requirement validated successfully")
            else:
                logger.error(f"❌ Coverage validation failed with {len(issues)} issues")
            
            return success, issues
            
        except Exception as e:
            error_msg = f"Coverage validation error: {str(e)}"
            logger.error(error_msg)
            issues.append(error_msg)
            return False, issues
    
    def generate_line_by_line_coverage_analysis(self, file_path: str) -> Dict[str, Any]:
        """
        Generate line-by-line coverage analysis for a specific file.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            Dict[str, Any]: Detailed line-by-line coverage information
        """
        if not self.coverage_instance:
            return {'error': 'Coverage measurement not available'}
        
        try:
            self.coverage_instance.load()
            analysis = self.coverage_instance.analysis2(file_path)
            
            # Read the source file
            with open(file_path, 'r', encoding='utf-8') as f:
                source_lines = f.readlines()
            
            # Create line-by-line analysis
            line_analysis = {}
            for line_num, line_content in enumerate(source_lines, 1):
                status = 'excluded'
                if line_num in analysis.statements:
                    status = 'covered' if line_num not in analysis.missing else 'missing'
                elif line_num in analysis.excluded:
                    status = 'excluded'
                else:
                    status = 'not_executable'
                
                line_analysis[line_num] = {
                    'content': line_content.rstrip(),
                    'status': status,
                    'executable': line_num in analysis.statements
                }
            
            return {
                'file_path': file_path,
                'total_lines': len(source_lines),
                'executable_lines': len(analysis.statements),
                'covered_lines': len(analysis.statements) - len(analysis.missing),
                'missing_lines': list(analysis.missing),
                'excluded_lines': list(analysis.excluded),
                'coverage_percentage': ((len(analysis.statements) - len(analysis.missing)) / len(analysis.statements) * 100) if analysis.statements else 100.0,
                'line_analysis': line_analysis
            }
            
        except Exception as e:
            logger.error(f"Failed to generate line-by-line analysis for {file_path}: {str(e)}")
            return {'error': str(e)}
    
    def run_specific_tests(self, test_patterns: List[str]) -> TestSuiteResult:
        """
        Run specific tests matching the given patterns.
        
        Args:
            test_patterns: List of test patterns (file paths, test names, etc.)
            
        Returns:
            TestSuiteResult: Test execution results
        """
        logger.info(f"Running specific tests: {test_patterns}")
        
        # Build pytest arguments for specific tests
        pytest_args = ['-k', ' or '.join(test_patterns)] if test_patterns else []
        
        return self.run_tests_with_coverage(pytest_args=pytest_args)
    
    def _create_empty_result(self, start_time: datetime) -> TestSuiteResult:
        """Create an empty test suite result."""
        return TestSuiteResult(
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            skipped_tests=0,
            error_tests=0,
            total_duration=0.0,
            test_results=[],
            coverage_info={},
            overall_coverage=0.0,
            coverage_status=CoverageStatus.CRITICAL,
            execution_timestamp=start_time,
            command_line="",
            exit_code=0,
            warnings=["No tests discovered"],
            errors=[]
        )
    
    def _create_timeout_result(self, start_time: datetime, pytest_cmd: List[str]) -> TestSuiteResult:
        """Create a timeout test suite result."""
        return TestSuiteResult(
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            skipped_tests=0,
            error_tests=0,
            total_duration=(datetime.now() - start_time).total_seconds(),
            test_results=[],
            coverage_info={},
            overall_coverage=0.0,
            coverage_status=CoverageStatus.CRITICAL,
            execution_timestamp=start_time,
            command_line=' '.join(pytest_cmd),
            exit_code=-1,
            warnings=[],
            errors=[f"Test execution timed out after {self.pytest_timeout} seconds"]
        )
    
    def _create_error_result(self, start_time: datetime, pytest_cmd: List[str], error_message: str) -> TestSuiteResult:
        """Create an error test suite result."""
        return TestSuiteResult(
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            skipped_tests=0,
            error_tests=0,
            total_duration=(datetime.now() - start_time).total_seconds(),
            test_results=[],
            coverage_info={},
            overall_coverage=0.0,
            coverage_status=CoverageStatus.CRITICAL,
            execution_timestamp=start_time,
            command_line=' '.join(pytest_cmd),
            exit_code=-1,
            warnings=[],
            errors=[error_message]
        )
    
    def _create_empty_coverage_report(self) -> CoverageReport:
        """Create an empty coverage report."""
        return CoverageReport(
            overall_coverage=0.0,
            line_coverage=0.0,
            branch_coverage=0.0,
            total_files=0,
            covered_files=0,
            uncovered_files=[],
            file_coverage={},
            missing_coverage_details={},
            coverage_by_directory={},
            status=CoverageStatus.CRITICAL,
            report_timestamp=datetime.now()
        )
    
    def generate_test_report(self, suite_result: TestSuiteResult) -> str:
        """
        Generate a comprehensive test execution report.
        
        Args:
            suite_result: Test suite execution results
            
        Returns:
            str: Formatted test report
        """
        report_lines = [
            "=" * 80,
            "UNIT TEST EXECUTION REPORT",
            "=" * 80,
            f"Execution Time: {suite_result.execution_timestamp.isoformat()}",
            f"Total Duration: {suite_result.total_duration:.2f} seconds",
            f"Command: {suite_result.command_line}",
            f"Exit Code: {suite_result.exit_code}",
            "",
            "TEST RESULTS SUMMARY:",
            f"  Total Tests: {suite_result.total_tests}",
            f"  Passed: {suite_result.passed_tests} ({suite_result.passed_tests/suite_result.total_tests*100:.1f}%)" if suite_result.total_tests > 0 else "  Passed: 0",
            f"  Failed: {suite_result.failed_tests}",
            f"  Skipped: {suite_result.skipped_tests}",
            f"  Errors: {suite_result.error_tests}",
            "",
            "COVERAGE SUMMARY:",
            f"  Overall Coverage: {suite_result.overall_coverage:.2f}%",
            f"  Coverage Status: {suite_result.coverage_status.value.upper()}",
            f"  Files Analyzed: {len(suite_result.coverage_info)}",
            ""
        ]
        
        # Add coverage details
        if suite_result.coverage_info:
            report_lines.extend([
                "COVERAGE BY FILE:",
                *[f"  {Path(file_path).name}: {info.coverage_percentage:.1f}% ({info.covered_lines}/{info.total_lines} lines)"
                  for file_path, info in sorted(suite_result.coverage_info.items())],
                ""
            ])
        
        # Add failed tests
        failed_tests = [t for t in suite_result.test_results if t.status == TestStatus.FAILED]
        if failed_tests:
            report_lines.extend([
                "FAILED TESTS:",
                *[f"  ❌ {test.name}: {test.failure_message or 'No details'}" for test in failed_tests[:10]],
                f"  ... and {len(failed_tests) - 10} more" if len(failed_tests) > 10 else "",
                ""
            ])
        
        # Add errors
        if suite_result.errors:
            report_lines.extend([
                "ERRORS:",
                *[f"  🚨 {error}" for error in suite_result.errors],
                ""
            ])
        
        # Add warnings
        if suite_result.warnings:
            report_lines.extend([
                "WARNINGS:",
                *[f"  ⚠️ {warning}" for warning in suite_result.warnings],
                ""
            ])
        
        # Add coverage requirements validation
        if suite_result.overall_coverage < self.coverage_threshold:
            report_lines.extend([
                "COVERAGE REQUIREMENTS:",
                f"  ❌ Required: {self.coverage_threshold}%",
                f"  ❌ Actual: {suite_result.overall_coverage:.2f}%",
                f"  ❌ Gap: {self.coverage_threshold - suite_result.overall_coverage:.2f}%",
                ""
            ])
        else:
            report_lines.extend([
                "COVERAGE REQUIREMENTS:",
                f"  ✅ Required: {self.coverage_threshold}%",
                f"  ✅ Actual: {suite_result.overall_coverage:.2f}%",
                ""
            ])
        
        report_lines.extend([
            "=" * 80
        ])
        
        return "\n".join(report_lines)
    
    def set_coverage_threshold(self, threshold: float) -> None:
        """
        Set the coverage threshold requirement.
        
        Args:
            threshold: Coverage threshold percentage (0-100)
        """
        if 0 <= threshold <= 100:
            self.coverage_threshold = threshold
            logger.info(f"Coverage threshold set to {threshold}%")
        else:
            raise ValueError("Coverage threshold must be between 0 and 100")
    
    def cleanup_test_artifacts(self) -> None:
        """Clean up test artifacts and temporary files."""
        artifacts = [
            'test-results.xml',
            'test-report.json',
            'coverage.xml',
            'coverage.json',
            '.coverage',
            'htmlcov'
        ]
        
        for artifact in artifacts:
            artifact_path = self.project_root / artifact
            try:
                if artifact_path.exists():
                    if artifact_path.is_file():
                        artifact_path.unlink()
                    else:
                        import shutil
                        shutil.rmtree(artifact_path)
                    logger.info(f"Cleaned up {artifact}")
            except Exception as e:
                logger.warning(f"Failed to clean up {artifact}: {str(e)}")
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        try:
            if self.coverage_instance:
                self.coverage_instance.stop()
        except:
            pass