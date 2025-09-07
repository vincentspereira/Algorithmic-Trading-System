"""
Test suite for EdgeCaseFramework

This module contains comprehensive tests for the EdgeCaseFramework,
validating all functionality including boundary testing, edge case testing,
and exception handling validation.
"""

import os
import sys
import math
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
from datetime import datetime

# Add the framework directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from edge_case_framework import (
    EdgeCaseFramework,
    BoundaryType,
    EdgeCaseType,
    BoundaryTestCase,
    EdgeCaseTestCase,
    TestResult,
    ValidationReport
)


class TestEdgeCaseFramework:
    """Test suite for EdgeCaseFramework class"""
    
    @pytest.fixture
    def framework(self):
        """Create an EdgeCaseFramework instance for testing"""
        return EdgeCaseFramework()
    
    @pytest.fixture
    def sample_function(self):
        """Create a sample function for testing"""
        def add_numbers(a: int, b: int) -> int:
            """Add two numbers together"""
            if not isinstance(a, int) or not isinstance(b, int):
                raise TypeError("Both arguments must be integers")
            return a + b
        
        return add_numbers
    
    @pytest.fixture
    def division_function(self):
        """Create a division function for testing"""
        def divide_numbers(a: float, b: float) -> float:
            """Divide two numbers"""
            if b == 0:
                raise ZeroDivisionError("Cannot divide by zero")
            return a / b
        
        return division_function
    
    def test_init(self, framework):
        """Test EdgeCaseFramework initialization"""
        assert isinstance(framework.test_cases, dict)
        assert isinstance(framework.test_results, dict)
        assert isinstance(framework.boundary_generators, dict)
        assert isinstance(framework.edge_values, dict)
        assert len(framework.test_cases) == 0
        assert len(framework.test_results) == 0
    
    def test_generate_int_boundaries(self, framework):
        """Test integer boundary generation"""
        boundaries = framework._generate_int_boundaries('test_param')
        
        assert len(boundaries) == 5
        
        # Check boundary types
        boundary_types = [b.boundary_type for b in boundaries]
        assert BoundaryType.ZERO in boundary_types
        assert BoundaryType.POSITIVE in boundary_types
        assert BoundaryType.NEGATIVE in boundary_types
        assert BoundaryType.MAXIMUM in boundary_types
        assert BoundaryType.MINIMUM in boundary_types
        
        # Check specific values
        zero_test = next(b for b in boundaries if b.boundary_type == BoundaryType.ZERO)
        assert zero_test.input_value == 0
        
        max_test = next(b for b in boundaries if b.boundary_type == BoundaryType.MAXIMUM)
        assert max_test.input_value == sys.maxsize
    
    def test_generate_float_boundaries(self, framework):
        """Test float boundary generation"""
        boundaries = framework._generate_float_boundaries('test_param')
        
        assert len(boundaries) == 6
        
        # Check for infinity and NaN tests
        boundary_types = [b.boundary_type for b in boundaries]
        assert BoundaryType.INFINITY in boundary_types
        assert BoundaryType.NAN in boundary_types
        
        # Check specific values
        nan_test = next(b for b in boundaries if b.boundary_type == BoundaryType.NAN)
        assert math.isnan(nan_test.input_value)
        
        inf_tests = [b for b in boundaries if b.boundary_type == BoundaryType.INFINITY]
        assert len(inf_tests) == 2  # positive and negative infinity
    
    def test_generate_string_boundaries(self, framework):
        """Test string boundary generation"""
        boundaries = framework._generate_string_boundaries('test_param')
        
        assert len(boundaries) == 6
        
        # Check for empty string test
        empty_test = next(b for b in boundaries if b.boundary_type == BoundaryType.EMPTY and b.input_value == "")
        assert empty_test.input_value == ""
        
        # Check for long string test
        long_test = next(b for b in boundaries if b.boundary_type == BoundaryType.MAXIMUM)
        assert len(long_test.input_value) == 10000
    
    def test_generate_list_boundaries(self, framework):
        """Test list boundary generation"""
        boundaries = framework._generate_list_boundaries('test_param')
        
        assert len(boundaries) == 4
        
        # Check for empty list test
        empty_test = next(b for b in boundaries if b.boundary_type == BoundaryType.EMPTY)
        assert empty_test.input_value == []
        
        # Check for large list test
        large_test = next(b for b in boundaries if b.boundary_type == BoundaryType.MAXIMUM)
        assert len(large_test.input_value) == 10000
    
    def test_generate_boundary_tests(self, framework, sample_function):
        """Test boundary test generation for a function"""
        param_types = {'a': int, 'b': int}
        
        boundary_tests = framework.generate_boundary_tests(sample_function, param_types)
        
        assert len(boundary_tests) > 0
        assert sample_function.__name__ in framework.test_cases
        
        # Should have generated tests for both parameters
        param_a_tests = [t for t in boundary_tests if 'a_' in t.name]
        param_b_tests = [t for t in boundary_tests if 'b_' in t.name]
        assert len(param_a_tests) > 0
        assert len(param_b_tests) > 0
    
    def test_generate_edge_case_tests(self, framework, sample_function):
        """Test edge case test generation for a function"""
        param_types = {'a': int, 'b': int}
        
        edge_tests = framework.generate_edge_case_tests(sample_function, param_types)
        
        assert len(edge_tests) > 0
        assert sample_function.__name__ in framework.test_cases
        
        # Should have different types of edge cases
        edge_types = [t.edge_case_type for t in edge_tests]
        assert EdgeCaseType.TYPE_MISMATCH in edge_types
        assert EdgeCaseType.MISSING_PARAMETER in edge_types
    
    def test_execute_boundary_tests(self, framework, sample_function):
        """Test boundary test execution"""
        boundary_tests = [
            BoundaryTestCase(
                name="test_zero",
                boundary_type=BoundaryType.ZERO,
                input_value=0,
                expected_result=5  # 0 + 5 = 5 (assuming second param is 5)
            ),
            BoundaryTestCase(
                name="test_positive",
                boundary_type=BoundaryType.POSITIVE,
                input_value=1,
                expected_result=6  # 1 + 5 = 6
            )
        ]
        
        # Mock the function to return predictable results
        def mock_add(a):
            return a + 5
        
        results = framework.execute_boundary_tests(mock_add, boundary_tests)
        
        assert len(results) == 2
        assert all(isinstance(r, TestResult) for r in results)
        assert results[0].test_name == "test_zero"
        assert results[1].test_name == "test_positive"
    
    def test_execute_edge_case_tests(self, framework, sample_function):
        """Test edge case test execution"""
        edge_tests = [
            EdgeCaseTestCase(
                name="test_type_mismatch",
                edge_case_type=EdgeCaseType.TYPE_MISMATCH,
                input_values={'a': "string", 'b': 5},
                expected_exception=TypeError
            )
        ]
        
        results = framework.execute_edge_case_tests(sample_function, edge_tests)
        
        assert len(results) == 1
        assert results[0].test_name == "test_type_mismatch"
        assert results[0].passed == True  # Should pass because TypeError is expected
    
    def test_validate_exception_handling(self, framework, division_function):
        """Test exception handling validation"""
        exception_scenarios = [
            {
                'name': 'division_by_zero',
                'args': (10.0, 0.0),
                'expected_exception': ZeroDivisionError
            },
            {
                'name': 'valid_division',
                'args': (10.0, 2.0),
                'expected_exception': None
            }
        ]
        
        results = framework.validate_exception_handling(division_function, exception_scenarios)
        
        assert len(results) == 2
        
        # First test should pass (exception expected and raised)
        assert results[0].test_name == "exception_division_by_zero"
        assert results[0].passed == True
        
        # Second test should fail (no exception expected but might be implementation dependent)
        assert results[1].test_name == "exception_valid_division"
    
    def test_comprehensive_function_validation(self, framework, sample_function):
        """Test comprehensive function validation"""
        param_types = {'a': int, 'b': int}
        exception_scenarios = [
            {
                'name': 'type_error',
                'args': ("string", 5),
                'expected_exception': TypeError
            }
        ]
        
        report = framework.comprehensive_function_validation(
            sample_function, 
            param_types, 
            exception_scenarios
        )
        
        assert isinstance(report, ValidationReport)
        assert report.function_name == sample_function.__name__
        assert report.total_tests > 0
        assert len(report.boundary_tests) > 0
        assert len(report.edge_case_tests) > 0
        assert len(report.exception_tests) > 0
        assert isinstance(report.recommendations, list)
    
    def test_detect_parameter_types(self, framework):
        """Test parameter type detection"""
        def typed_function(a: int, b: str, c: float) -> str:
            return f"{a}_{b}_{c}"
        
        param_types = framework._detect_parameter_types(typed_function)
        
        assert param_types['a'] == int
        assert param_types['b'] == str
        assert param_types['c'] == float
    
    def test_detect_parameter_types_no_annotations(self, framework):
        """Test parameter type detection without annotations"""
        def untyped_function(a, b, c):
            return a + b + c
        
        param_types = framework._detect_parameter_types(untyped_function)
        
        # Should default to str for all parameters
        assert param_types['a'] == str
        assert param_types['b'] == str
        assert param_types['c'] == str
    
    def test_generate_type_mismatch_tests(self, framework, sample_function):
        """Test type mismatch test generation"""
        param_types = {'a': int, 'b': str}
        
        type_tests = framework._generate_type_mismatch_tests(sample_function, param_types)
        
        assert len(type_tests) > 0
        
        # Should have tests for both parameters
        param_a_tests = [t for t in type_tests if 'a_type_mismatch' in t.name]
        param_b_tests = [t for t in type_tests if 'b_type_mismatch' in t.name]
        assert len(param_a_tests) > 0
        assert len(param_b_tests) > 0
        
        # All should expect TypeError
        assert all(t.expected_exception == TypeError for t in type_tests)
    
    def test_generate_missing_parameter_tests(self, framework, sample_function):
        """Test missing parameter test generation"""
        param_types = {'a': int, 'b': int}
        
        missing_tests = framework._generate_missing_parameter_tests(sample_function, param_types)
        
        assert len(missing_tests) > 0
        
        # Should have test for missing all parameters
        all_missing = next((t for t in missing_tests if t.name == 'missing_all_parameters'), None)
        assert all_missing is not None
        assert all_missing.expected_exception == TypeError
        
        # Should have tests for missing individual parameters
        missing_a = next((t for t in missing_tests if t.name == 'missing_a'), None)
        missing_b = next((t for t in missing_tests if t.name == 'missing_b'), None)
        assert missing_a is not None
        assert missing_b is not None
    
    def test_get_default_value(self, framework):
        """Test getting default values for types"""
        assert framework._get_default_value(int) == 0
        assert framework._get_default_value(float) == 0.0
        assert framework._get_default_value(str) == ""
        assert framework._get_default_value(list) == []
        assert framework._get_default_value(dict) == {}
        assert framework._get_default_value(bool) == False
        assert framework._get_default_value(object) is None
    
    def test_generate_recommendations_no_failures(self, framework):
        """Test recommendation generation with no failures"""
        results = [
            TestResult(test_name="test1", test_type="boundary", passed=True),
            TestResult(test_name="test2", test_type="edge_case", passed=True)
        ]
        
        recommendations = framework._generate_recommendations(results, {'a': int})
        
        assert len(recommendations) == 1
        assert "handles edge cases and boundary conditions well" in recommendations[0]
    
    def test_generate_recommendations_with_failures(self, framework):
        """Test recommendation generation with failures"""
        results = [
            TestResult(
                test_name="test1", 
                test_type="boundary", 
                passed=False,
                actual_exception=TypeError("Type error")
            ),
            TestResult(
                test_name="test2", 
                test_type="edge_case", 
                passed=False,
                actual_exception=ValueError("Value error")
            ),
            TestResult(
                test_name="test3", 
                test_type="boundary", 
                passed=False,
                actual_exception=ZeroDivisionError("Division by zero")
            )
        ]
        
        recommendations = framework._generate_recommendations(results, {'a': int})
        
        assert len(recommendations) > 1
        assert any("type checking" in rec.lower() for rec in recommendations)
        assert any("value range validation" in rec.lower() for rec in recommendations)
        assert any("division by zero" in rec.lower() for rec in recommendations)
    
    def test_generate_test_report(self, framework):
        """Test test report generation"""
        # Create mock validation report
        boundary_results = [
            TestResult(test_name="boundary1", test_type="boundary", passed=True),
            TestResult(test_name="boundary2", test_type="boundary", passed=False, error_message="Boundary error")
        ]
        
        edge_results = [
            TestResult(test_name="edge1", test_type="edge_case", passed=True),
            TestResult(test_name="edge2", test_type="edge_case", passed=False, error_message="Edge error")
        ]
        
        exception_results = [
            TestResult(test_name="exception1", test_type="exception", passed=True)
        ]
        
        validation_report = ValidationReport(
            function_name="test_function",
            total_tests=5,
            passed_tests=3,
            failed_tests=2,
            boundary_tests=boundary_results,
            edge_case_tests=edge_results,
            exception_tests=exception_results,
            coverage_percentage=60.0,
            validation_summary={'test': 'value'},
            recommendations=["Add input validation", "Handle edge cases better"]
        )
        
        report = framework.generate_test_report(validation_report)
        
        assert "EDGE CASE AND BOUNDARY TESTING REPORT" in report
        assert "test_function" in report
        assert "Total Tests: 5" in report
        assert "Passed: 3" in report
        assert "Failed: 2" in report
        assert "Success Rate: 60.0%" in report
        assert "FAILED TESTS:" in report
        assert "RECOMMENDATIONS:" in report
        assert "Add input validation" in report
    
    def test_get_test_statistics(self, framework):
        """Test getting test statistics"""
        # Add some mock results
        results = [
            TestResult(test_name="test1", test_type="BoundaryTestCase", passed=True, execution_time=0.001),
            TestResult(test_name="test2", test_type="EdgeCaseTestCase", passed=False, execution_time=0.002),
            TestResult(test_name="test3", test_type="exception_handling", passed=True, execution_time=0.003)
        ]
        
        framework.test_results['test_function'] = results
        
        stats = framework.get_test_statistics('test_function')
        
        assert stats['function_name'] == 'test_function'
        assert stats['total_tests'] == 3
        assert stats['passed_tests'] == 2
        assert stats['failed_tests'] == 1
        assert stats['success_rate'] == 200/3  # 2/3 * 100
        assert stats['average_execution_time'] == 0.002  # (0.001 + 0.002 + 0.003) / 3
        assert stats['test_types']['boundary'] == 1
        assert stats['test_types']['edge_case'] == 1
        assert stats['test_types']['exception'] == 1
    
    def test_get_test_statistics_no_results(self, framework):
        """Test getting statistics for function with no results"""
        stats = framework.get_test_statistics('nonexistent_function')
        
        assert 'error' in stats
        assert "No test results found" in stats['error']
    
    def test_boundary_test_case_dataclass(self):
        """Test BoundaryTestCase dataclass"""
        test_case = BoundaryTestCase(
            name="test_zero",
            boundary_type=BoundaryType.ZERO,
            input_value=0,
            expected_result=5,
            description="Test with zero value"
        )
        
        assert test_case.name == "test_zero"
        assert test_case.boundary_type == BoundaryType.ZERO
        assert test_case.input_value == 0
        assert test_case.expected_result == 5
        assert test_case.expected_exception is None
        assert test_case.description == "Test with zero value"
        assert test_case.metadata == {}
    
    def test_edge_case_test_case_dataclass(self):
        """Test EdgeCaseTestCase dataclass"""
        test_case = EdgeCaseTestCase(
            name="test_type_mismatch",
            edge_case_type=EdgeCaseType.TYPE_MISMATCH,
            input_values={'a': "string", 'b': 5},
            expected_exception=TypeError,
            description="Test with type mismatch"
        )
        
        assert test_case.name == "test_type_mismatch"
        assert test_case.edge_case_type == EdgeCaseType.TYPE_MISMATCH
        assert test_case.input_values == {'a': "string", 'b': 5}
        assert test_case.expected_exception == TypeError
        assert test_case.description == "Test with type mismatch"
        assert test_case.metadata == {}
    
    def test_test_result_dataclass(self):
        """Test TestResult dataclass"""
        result = TestResult(
            test_name="test_example",
            test_type="boundary",
            passed=True,
            actual_result=10,
            expected_result=10,
            execution_time=0.001
        )
        
        assert result.test_name == "test_example"
        assert result.test_type == "boundary"
        assert result.passed == True
        assert result.actual_result == 10
        assert result.expected_result == 10
        assert result.execution_time == 0.001
        assert result.actual_exception is None
        assert result.error_message is None
    
    def test_validation_report_dataclass(self):
        """Test ValidationReport dataclass"""
        report = ValidationReport(
            function_name="test_func",
            total_tests=10,
            passed_tests=8,
            failed_tests=2,
            boundary_tests=[],
            edge_case_tests=[],
            exception_tests=[],
            coverage_percentage=80.0,
            validation_summary={},
            recommendations=["Recommendation 1", "Recommendation 2"]
        )
        
        assert report.function_name == "test_func"
        assert report.total_tests == 10
        assert report.passed_tests == 8
        assert report.failed_tests == 2
        assert report.coverage_percentage == 80.0
        assert len(report.recommendations) == 2


# Sample functions for testing the framework
def sample_calculator_function(a: int, b: int) -> int:
    """Sample function for testing - adds two integers"""
    if not isinstance(a, int) or not isinstance(b, int):
        raise TypeError("Both arguments must be integers")
    if a < 0 or b < 0:
        raise ValueError("Arguments must be non-negative")
    return a + b


def sample_division_function(numerator: float, denominator: float) -> float:
    """Sample function for testing - divides two numbers"""
    if denominator == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    if not isinstance(numerator, (int, float)) or not isinstance(denominator, (int, float)):
        raise TypeError("Arguments must be numeric")
    return numerator / denominator


def sample_string_function(text: str, max_length: int = 100) -> str:
    """Sample function for testing - processes strings"""
    if not isinstance(text, str):
        raise TypeError("Text must be a string")
    if len(text) > max_length:
        raise ValueError(f"Text length exceeds maximum of {max_length}")
    if not text.strip():
        raise ValueError("Text cannot be empty or whitespace only")
    return text.upper()


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])