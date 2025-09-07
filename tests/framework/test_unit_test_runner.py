"""
Test suite for UnitTestRunner class

This module contains comprehensive tests for the UnitTestRunner class,
validating all functionality including test execution, coverage tracking,
and detailed reporting.
"""

import os
import sys
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import pytest
from datetime import datetime

# Add the framework directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from unit_test_runner import (
    UnitTestRunner,
    TestStatus,
    CoverageStatus,
    TestResult,
    TestSuiteResult,
    CoverageInfo,
    CoverageReport
)


class TestUnitTestRunner:
    """Test suite for UnitTestRunner class"""
    
    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory for testing"""
        temp_dir = Path(tempfile.mkdtemp())
        
        # Create source directory structure
        src_dir = temp_dir / "src"
        src_dir.mkdir()
        
        # Create sample source files
        (src_dir / "__init__.py").write_text("")
        (src_dir / "calculator.py").write_text("""
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
""")
        
        # Create test directory structure
        tests_dir = temp_dir / "tests"
        tests_dir.mkdir()
        
        # Create sample test files
        (tests_dir / "__init__.py").write_text("")
        (tests_dir / "test_calculator.py").write_text("""
import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from calculator import add, subtract, multiply, divide

def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0

def test_subtract():
    assert subtract(5, 3) == 2
    assert subtract(0, 5) == -5

def test_multiply():
    assert multiply(3, 4) == 12
    assert multiply(-2, 3) == -6

def test_divide():
    assert divide(10, 2) == 5
    assert divide(7, 2) == 3.5

def test_divide_by_zero():
    with pytest.raises(ValueError, match="Cannot divide by zero"):
        divide(10, 0)
""")
        
        yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def unit_test_runner(self, temp_project_dir):
        """Create a UnitTestRunner instance for testing"""
        return UnitTestRunner(project_root=temp_project_dir, src_directories=[str(temp_project_dir / "src")])
    
    def test_init(self, temp_project_dir):
        """Test UnitTestRunner initialization"""
        runner = UnitTestRunner(project_root=temp_project_dir)
        
        assert runner.project_root == temp_project_dir
        assert runner.coverage_threshold == 100.0
        assert runner.min_acceptable_coverage == 75.0
        assert runner.pytest_timeout == 300
        assert runner.max_test_duration == 30.0
    
    def test_init_with_custom_src_directories(self, temp_project_dir):
        """Test UnitTestRunner initialization with custom source directories"""
        custom_src = [str(temp_project_dir / "custom_src")]
        runner = UnitTestRunner(project_root=temp_project_dir, src_directories=custom_src)
        
        assert runner.src_directories == custom_src
    
    def test_discover_source_directories(self, temp_project_dir):
        """Test source directory discovery"""
        runner = UnitTestRunner(project_root=temp_project_dir)
        discovered = runner._discover_source_directories()
        
        # Should discover the src directory we created
        assert any("src" in path for path in discovered)
    
    def test_discover_tests(self, unit_test_runner):
        """Test test file discovery"""
        discovered_tests = unit_test_runner.discover_tests()
        
        assert len(discovered_tests) > 0
        assert any("test_calculator.py" in test_file for test_file in discovered_tests)
    
    def test_discover_tests_custom_directories(self, unit_test_runner):
        """Test test discovery with custom directories"""
        discovered_tests = unit_test_runner.discover_tests(test_directories=["tests"])
        
        assert len(discovered_tests) > 0
        assert any("test_calculator.py" in test_file for test_file in discovered_tests)
    
    def test_build_pytest_command(self, unit_test_runner):
        """Test pytest command building"""
        test_paths = ["tests/test_calculator.py"]
        pytest_args = ["--verbose"]
        
        cmd = unit_test_runner._build_pytest_command(test_paths, pytest_args)
        
        assert "python" in cmd
        assert "-m" in cmd
        assert "pytest" in cmd
        assert "tests/test_calculator.py" in cmd
        assert "--verbose" in cmd
        assert "-v" in cmd
        assert "--tb=short" in cmd
    
    def test_parse_stdout_output(self, unit_test_runner):
        """Test parsing pytest stdout output"""
        stdout = """
tests/test_calculator.py::test_add PASSED [100%]
tests/test_calculator.py::test_subtract PASSED [100%]
tests/test_calculator.py::test_multiply FAILED [100%]
tests/test_calculator.py::test_divide SKIPPED [100%]
"""
        
        test_results = unit_test_runner._parse_stdout_output(stdout)
        
        assert len(test_results) == 4
        
        # Check status parsing
        statuses = [result.status for result in test_results]
        assert TestStatus.PASSED in statuses
        assert TestStatus.FAILED in statuses
        assert TestStatus.SKIPPED in statuses
    
    def test_parse_json_report(self, unit_test_runner, temp_project_dir):
        """Test parsing pytest JSON report"""
        # Create mock JSON report
        json_data = {
            "tests": [
                {
                    "nodeid": "tests/test_calculator.py::test_add",
                    "outcome": "PASSED",
                    "duration": 0.001,
                    "file": "tests/test_calculator.py",
                    "line": 10
                },
                {
                    "nodeid": "tests/test_calculator.py::test_divide_by_zero",
                    "outcome": "FAILED",
                    "duration": 0.002,
                    "file": "tests/test_calculator.py",
                    "line": 25,
                    "call": {
                        "longrepr": "AssertionError: Test failed"
                    }
                }
            ]
        }
        
        json_path = temp_project_dir / "test-report.json"
        with open(json_path, 'w') as f:
            json.dump(json_data, f)
        
        test_results = unit_test_runner._parse_json_report(json_path)
        
        assert len(test_results) == 2
        assert test_results[0].status == TestStatus.PASSED
        assert test_results[1].status == TestStatus.FAILED
        assert test_results[1].failure_message == "AssertionError: Test failed"
    
    def test_determine_coverage_status(self, unit_test_runner):
        """Test coverage status determination"""
        assert unit_test_runner._determine_coverage_status(98.0) == CoverageStatus.EXCELLENT
        assert unit_test_runner._determine_coverage_status(90.0) == CoverageStatus.GOOD
        assert unit_test_runner._determine_coverage_status(80.0) == CoverageStatus.ACCEPTABLE
        assert unit_test_runner._determine_coverage_status(65.0) == CoverageStatus.POOR
        assert unit_test_runner._determine_coverage_status(50.0) == CoverageStatus.CRITICAL
    
    @patch('subprocess.run')
    @patch('coverage.Coverage')
    def test_run_tests_with_coverage_success(self, mock_coverage_class, mock_subprocess, unit_test_runner):
        """Test successful test execution with coverage"""
        # Mock subprocess result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "tests/test_calculator.py::test_add PASSED [100%]"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        # Mock coverage
        mock_coverage = Mock()
        mock_coverage.report.return_value = 95.0
        mock_coverage.get_data.return_value.measured_files.return_value = []
        mock_coverage_class.return_value = mock_coverage
        unit_test_runner.coverage_instance = mock_coverage
        
        # Mock test discovery
        with patch.object(unit_test_runner, 'discover_tests', return_value=['tests/test_calculator.py']):
            result = unit_test_runner.run_tests_with_coverage()
        
        assert isinstance(result, TestSuiteResult)
        assert result.exit_code == 0
        assert result.overall_coverage == 95.0
        mock_coverage.start.assert_called_once()
        mock_coverage.stop.assert_called_once()
        mock_coverage.save.assert_called_once()
    
    @patch('subprocess.run')
    def test_run_tests_with_coverage_timeout(self, mock_subprocess, unit_test_runner):
        """Test test execution timeout"""
        import subprocess
        mock_subprocess.side_effect = subprocess.TimeoutExpired("pytest", 300)
        
        with patch.object(unit_test_runner, 'discover_tests', return_value=['tests/test_calculator.py']):
            result = unit_test_runner.run_tests_with_coverage()
        
        assert isinstance(result, TestSuiteResult)
        assert result.exit_code == -1
        assert "timed out" in result.errors[0]
    
    @patch('subprocess.run')
    def test_run_tests_with_coverage_error(self, mock_subprocess, unit_test_runner):
        """Test test execution error"""
        mock_subprocess.side_effect = Exception("Test execution failed")
        
        with patch.object(unit_test_runner, 'discover_tests', return_value=['tests/test_calculator.py']):
            result = unit_test_runner.run_tests_with_coverage()
        
        assert isinstance(result, TestSuiteResult)
        assert result.exit_code == -1
        assert "Test execution failed" in result.errors[0]
    
    def test_run_tests_no_tests_discovered(self, unit_test_runner):
        """Test running tests when no tests are discovered"""
        with patch.object(unit_test_runner, 'discover_tests', return_value=[]):
            result = unit_test_runner.run_tests_with_coverage()
        
        assert isinstance(result, TestSuiteResult)
        assert result.total_tests == 0
        assert "No tests discovered" in result.warnings
    
    @patch('coverage.Coverage')
    def test_generate_coverage_report(self, mock_coverage_class, unit_test_runner):
        """Test coverage report generation"""
        # Mock coverage analysis
        mock_analysis = Mock()
        mock_analysis.statements = [1, 2, 3, 4, 5]
        mock_analysis.missing = [4, 5]
        mock_analysis.excluded = []
        
        mock_coverage = Mock()
        mock_coverage.report.return_value = 80.0
        mock_coverage.get_data.return_value.measured_files.return_value = ["src/calculator.py"]
        mock_coverage.analysis2.return_value = mock_analysis
        
        unit_test_runner.coverage_instance = mock_coverage
        
        coverage_info, overall_coverage = unit_test_runner._generate_coverage_report()
        
        assert overall_coverage == 80.0
        assert "src/calculator.py" in coverage_info
        assert coverage_info["src/calculator.py"].coverage_percentage == 60.0  # 3/5 * 100
        assert coverage_info["src/calculator.py"].missing_lines == [4, 5]
    
    @patch('coverage.Coverage')
    def test_validate_100_percent_coverage_success(self, mock_coverage_class, unit_test_runner):
        """Test successful 100% coverage validation"""
        # Mock coverage analysis with no missing lines
        mock_analysis = Mock()
        mock_analysis.missing = []
        
        mock_coverage = Mock()
        mock_coverage.report.return_value = 100.0
        mock_coverage.get_data.return_value.measured_files.return_value = ["src/calculator.py"]
        mock_coverage.analysis2.return_value = mock_analysis
        
        unit_test_runner.coverage_instance = mock_coverage
        
        success, issues = unit_test_runner.validate_100_percent_coverage()
        
        assert success == True
        assert len(issues) == 0
    
    @patch('coverage.Coverage')
    def test_validate_100_percent_coverage_failure(self, mock_coverage_class, unit_test_runner):
        """Test failed 100% coverage validation"""
        # Mock coverage analysis with missing lines
        mock_analysis = Mock()
        mock_analysis.missing = [10, 15, 20]
        
        mock_coverage = Mock()
        mock_coverage.report.return_value = 85.0
        mock_coverage.get_data.return_value.measured_files.return_value = ["src/calculator.py"]
        mock_coverage.analysis2.return_value = mock_analysis
        
        unit_test_runner.coverage_instance = mock_coverage
        
        success, issues = unit_test_runner.validate_100_percent_coverage()
        
        assert success == False
        assert len(issues) > 0
        assert "Missing coverage on lines [10, 15, 20]" in issues[0]
        assert "Overall coverage 85.00% is below required 100.0%" in issues[1]
    
    def test_validate_100_percent_coverage_no_coverage(self, unit_test_runner):
        """Test coverage validation when coverage is not available"""
        unit_test_runner.coverage_instance = None
        
        success, issues = unit_test_runner.validate_100_percent_coverage()
        
        assert success == False
        assert "Coverage measurement not available" in issues
    
    @patch('coverage.Coverage')
    def test_generate_line_by_line_coverage_analysis(self, mock_coverage_class, unit_test_runner, temp_project_dir):
        """Test line-by-line coverage analysis"""
        # Create a test file
        test_file = temp_project_dir / "src" / "test_file.py"
        test_file.write_text("""def function1():
    return True

def function2():
    return False
""")
        
        # Mock coverage analysis
        mock_analysis = Mock()
        mock_analysis.statements = [1, 2, 4, 5]
        mock_analysis.missing = [4, 5]
        mock_analysis.excluded = []
        
        mock_coverage = Mock()
        mock_coverage.analysis2.return_value = mock_analysis
        
        unit_test_runner.coverage_instance = mock_coverage
        
        analysis = unit_test_runner.generate_line_by_line_coverage_analysis(str(test_file))
        
        assert 'file_path' in analysis
        assert 'total_lines' in analysis
        assert 'line_analysis' in analysis
        assert analysis['coverage_percentage'] == 50.0  # 2/4 * 100
        assert analysis['missing_lines'] == [4, 5]
    
    def test_generate_line_by_line_coverage_analysis_no_coverage(self, unit_test_runner):
        """Test line-by-line analysis when coverage is not available"""
        unit_test_runner.coverage_instance = None
        
        analysis = unit_test_runner.generate_line_by_line_coverage_analysis("dummy_file.py")
        
        assert 'error' in analysis
        assert analysis['error'] == 'Coverage measurement not available'
    
    @patch('subprocess.run')
    def test_run_specific_tests(self, mock_subprocess, unit_test_runner):
        """Test running specific tests"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test_add PASSED"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        with patch.object(unit_test_runner, 'discover_tests', return_value=['tests/test_calculator.py']):
            result = unit_test_runner.run_specific_tests(['test_add', 'test_subtract'])
        
        assert isinstance(result, TestSuiteResult)
        # Check that -k argument was used
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert '-k' in call_args
        assert 'test_add or test_subtract' in call_args
    
    def test_generate_test_report(self, unit_test_runner):
        """Test test report generation"""
        # Create mock test suite result
        test_results = [
            TestResult(
                name="test_add",
                status=TestStatus.PASSED,
                duration=0.001,
                file_path="tests/test_calculator.py"
            ),
            TestResult(
                name="test_divide_by_zero",
                status=TestStatus.FAILED,
                duration=0.002,
                file_path="tests/test_calculator.py",
                failure_message="AssertionError: Test failed"
            )
        ]
        
        coverage_info = {
            "src/calculator.py": CoverageInfo(
                file_path="src/calculator.py",
                total_lines=10,
                covered_lines=8,
                missing_lines=[9, 10],
                excluded_lines=[],
                coverage_percentage=80.0,
                status=CoverageStatus.ACCEPTABLE
            )
        }
        
        suite_result = TestSuiteResult(
            total_tests=2,
            passed_tests=1,
            failed_tests=1,
            skipped_tests=0,
            error_tests=0,
            total_duration=10.5,
            test_results=test_results,
            coverage_info=coverage_info,
            overall_coverage=80.0,
            coverage_status=CoverageStatus.ACCEPTABLE,
            execution_timestamp=datetime.now(),
            command_line="pytest tests/",
            exit_code=1,
            warnings=["Some warning"],
            errors=["Some error"]
        )
        
        report = unit_test_runner.generate_test_report(suite_result)
        
        assert "UNIT TEST EXECUTION REPORT" in report
        assert "Total Tests: 2" in report
        assert "Passed: 1 (50.0%)" in report
        assert "Overall Coverage: 80.00%" in report
        assert "FAILED TESTS:" in report
        assert "test_divide_by_zero" in report
        assert "ERRORS:" in report
        assert "WARNINGS:" in report
    
    def test_set_coverage_threshold(self, unit_test_runner):
        """Test setting coverage threshold"""
        unit_test_runner.set_coverage_threshold(95.0)
        assert unit_test_runner.coverage_threshold == 95.0
        
        unit_test_runner.set_coverage_threshold(85.0)
        assert unit_test_runner.coverage_threshold == 85.0
    
    def test_set_coverage_threshold_invalid(self, unit_test_runner):
        """Test setting invalid coverage threshold"""
        with pytest.raises(ValueError, match="Coverage threshold must be between 0 and 100"):
            unit_test_runner.set_coverage_threshold(150.0)
        
        with pytest.raises(ValueError, match="Coverage threshold must be between 0 and 100"):
            unit_test_runner.set_coverage_threshold(-10.0)
    
    def test_cleanup_test_artifacts(self, unit_test_runner, temp_project_dir):
        """Test cleanup of test artifacts"""
        # Create some test artifacts
        artifacts = [
            'test-results.xml',
            'test-report.json',
            'coverage.xml',
            '.coverage'
        ]
        
        for artifact in artifacts:
            (temp_project_dir / artifact).write_text("test content")
        
        # Create htmlcov directory
        htmlcov_dir = temp_project_dir / 'htmlcov'
        htmlcov_dir.mkdir()
        (htmlcov_dir / 'index.html').write_text("test content")
        
        unit_test_runner.cleanup_test_artifacts()
        
        # Check that artifacts were removed
        for artifact in artifacts:
            assert not (temp_project_dir / artifact).exists()
        assert not htmlcov_dir.exists()
    
    def test_validate_coverage_requirements(self, unit_test_runner):
        """Test coverage requirements validation"""
        # Create test suite result with low coverage
        suite_result = TestSuiteResult(
            total_tests=5,
            passed_tests=5,
            failed_tests=0,
            skipped_tests=0,
            error_tests=0,
            total_duration=10.0,
            test_results=[],
            coverage_info={
                "file1.py": CoverageInfo(
                    file_path="file1.py",
                    total_lines=100,
                    covered_lines=60,
                    missing_lines=list(range(61, 101)),
                    excluded_lines=[],
                    coverage_percentage=60.0,
                    status=CoverageStatus.POOR
                )
            },
            overall_coverage=60.0,
            coverage_status=CoverageStatus.POOR,
            execution_timestamp=datetime.now(),
            command_line="pytest",
            exit_code=0,
            warnings=[],
            errors=[]
        )
        
        unit_test_runner._validate_coverage_requirements(suite_result)
        
        # Should have added error for low coverage
        assert len(suite_result.errors) > 0
        assert "Coverage 60.00% is below required 100.0%" in suite_result.errors[0]
        
        # Should have added warning for poor coverage files
        assert len(suite_result.warnings) > 0
        assert "files have coverage below 75.0%" in suite_result.warnings[0]
    
    @patch('coverage.Coverage')
    def test_generate_coverage_report_detailed(self, mock_coverage_class, unit_test_runner):
        """Test detailed coverage report generation"""
        # Mock coverage data
        mock_analysis = Mock()
        mock_analysis.statements = [1, 2, 3, 4, 5]
        mock_analysis.missing = [4, 5]
        mock_analysis.excluded = []
        
        mock_coverage = Mock()
        mock_coverage.report.return_value = 80.0
        mock_coverage.get_data.return_value.measured_files.return_value = ["src/file1.py", "src/file2.py"]
        mock_coverage.analysis2.return_value = mock_analysis
        
        unit_test_runner.coverage_instance = mock_coverage
        
        report = unit_test_runner.generate_coverage_report_detailed()
        
        assert isinstance(report, CoverageReport)
        assert report.overall_coverage == 80.0
        assert report.total_files == 2
        assert report.status == CoverageStatus.ACCEPTABLE
        assert len(report.file_coverage) == 2
    
    def test_test_result_dataclass(self):
        """Test TestResult dataclass"""
        test_result = TestResult(
            name="test_example",
            status=TestStatus.PASSED,
            duration=1.5,
            file_path="tests/test_example.py",
            line_number=10,
            error_message=None,
            failure_message=None
        )
        
        assert test_result.name == "test_example"
        assert test_result.status == TestStatus.PASSED
        assert test_result.duration == 1.5
        assert test_result.file_path == "tests/test_example.py"
        assert test_result.line_number == 10
        assert test_result.metadata == {}
    
    def test_coverage_info_dataclass(self):
        """Test CoverageInfo dataclass"""
        coverage_info = CoverageInfo(
            file_path="src/example.py",
            total_lines=100,
            covered_lines=85,
            missing_lines=[90, 95, 100],
            excluded_lines=[1, 2],
            coverage_percentage=85.0,
            status=CoverageStatus.GOOD
        )
        
        assert coverage_info.file_path == "src/example.py"
        assert coverage_info.total_lines == 100
        assert coverage_info.covered_lines == 85
        assert coverage_info.coverage_percentage == 85.0
        assert coverage_info.status == CoverageStatus.GOOD
        assert coverage_info.missing_lines == [90, 95, 100]
    
    def test_test_suite_result_dataclass(self):
        """Test TestSuiteResult dataclass"""
        timestamp = datetime.now()
        
        suite_result = TestSuiteResult(
            total_tests=10,
            passed_tests=8,
            failed_tests=1,
            skipped_tests=1,
            error_tests=0,
            total_duration=25.5,
            test_results=[],
            coverage_info={},
            overall_coverage=90.0,
            coverage_status=CoverageStatus.GOOD,
            execution_timestamp=timestamp,
            command_line="pytest tests/",
            exit_code=0
        )
        
        assert suite_result.total_tests == 10
        assert suite_result.passed_tests == 8
        assert suite_result.overall_coverage == 90.0
        assert suite_result.coverage_status == CoverageStatus.GOOD
        assert suite_result.execution_timestamp == timestamp
        assert suite_result.warnings == []
        assert suite_result.errors == []


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])