"""
Edge Case and Boundary Testing Framework

This module provides comprehensive edge case and boundary testing capabilities,
including error condition testing, boundary value testing, and exception handling
validation for all functions and methods.
"""

import os
import sys
import inspect
import math
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import logging
from decimal import Decimal, InvalidOperation
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BoundaryType(Enum):
    """Boundary type enumeration"""
    MINIMUM = "minimum"
    MAXIMUM = "maximum"
    ZERO = "zero"
    NEGATIVE = "negative"
    POSITIVE = "positive"
    EMPTY = "empty"
    NULL = "null"
    INFINITY = "infinity"
    NAN = "nan"
    OVERFLOW = "overflow"
    UNDERFLOW = "underflow"


class EdgeCaseType(Enum):
    """Edge case type enumeration"""
    INVALID_INPUT = "invalid_input"
    MISSING_PARAMETER = "missing_parameter"
    TYPE_MISMATCH = "type_mismatch"
    RANGE_VIOLATION = "range_violation"
    FORMAT_ERROR = "format_error"
    PERMISSION_DENIED = "permission_denied"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    CONCURRENT_ACCESS = "concurrent_access"


@dataclass
class BoundaryTestCase:
    """Boundary test case definition"""
    name: str
    boundary_type: BoundaryType
    input_value: Any
    expected_result: Any = None
    expected_exception: Optional[Type[Exception]] = None
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EdgeCaseTestCase:
    """Edge case test case definition"""
    name: str
    edge_case_type: EdgeCaseType
    input_values: Dict[str, Any]
    expected_result: Any = None
    expected_exception: Optional[Type[Exception]] = None
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """Test execution result"""
    test_name: str
    test_type: str
    passed: bool
    actual_result: Any = None
    actual_exception: Optional[Exception] = None
    expected_result: Any = None
    expected_exception: Optional[Type[Exception]] = None
    execution_time: float = 0.0
    error_message: Optional[str] = None


@dataclass
class ValidationReport:
    """Comprehensive validation report"""
    function_name: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    boundary_tests: List[TestResult]
    edge_case_tests: List[TestResult]
    exception_tests: List[TestResult]
    coverage_percentage: float
    validation_summary: Dict[str, Any]
    recommendations: List[str]


class EdgeCaseFramework:
    """
    Framework for comprehensive edge case and boundary testing.
    
    This class provides methods to generate and execute edge case tests,
    boundary value tests, and exception handling validation for functions.
    """
    
    def __init__(self):
        """Initialize the EdgeCaseFramework."""
        self.test_cases: Dict[str, List[Union[BoundaryTestCase, EdgeCaseTestCase]]] = {}
        self.test_results: Dict[str, List[TestResult]] = {}
        
        # Boundary value generators
        self.boundary_generators = {
            int: self._generate_int_boundaries,
            float: self._generate_float_boundaries,
            str: self._generate_string_boundaries,
            list: self._generate_list_boundaries,
            dict: self._generate_dict_boundaries,
            bool: self._generate_bool_boundaries
        }
        
        # Common edge case values
        self.edge_values = {
            'integers': [0, 1, -1, sys.maxsize, -sys.maxsize-1, 2**31-1, -2**31],
            'floats': [0.0, 1.0, -1.0, float('inf'), float('-inf'), float('nan'), 
                      sys.float_info.max, sys.float_info.min, sys.float_info.epsilon],
            'strings': ['', ' ', '\n', '\t', '\0', 'a' * 1000, '🚀', 'null', 'None', 'undefined'],
            'lists': [[], [None], [1], list(range(1000))],
            'dicts': [{}, {'key': None}, {'': ''}, {str(i): i for i in range(100)}],
            'bools': [True, False],
            'none_values': [None]
        }
    
    def generate_boundary_tests(self, func: Callable, param_types: Dict[str, Type]) -> List[BoundaryTestCase]:
        """
        Generate boundary test cases for a function.
        
        Args:
            func: Function to test
            param_types: Dictionary mapping parameter names to their types
            
        Returns:
            List[BoundaryTestCase]: Generated boundary test cases
        """
        boundary_tests = []
        
        for param_name, param_type in param_types.items():
            if param_type in self.boundary_generators:
                generator = self.boundary_generators[param_type]
                param_boundaries = generator(param_name)
                boundary_tests.extend(param_boundaries)
        
        # Store test cases
        func_name = func.__name__
        if func_name not in self.test_cases:
            self.test_cases[func_name] = []
        self.test_cases[func_name].extend(boundary_tests)
        
        logger.info(f"Generated {len(boundary_tests)} boundary test cases for {func_name}")
        return boundary_tests
    
    def generate_edge_case_tests(self, func: Callable, param_types: Dict[str, Type]) -> List[EdgeCaseTestCase]:
        """
        Generate edge case test cases for a function.
        
        Args:
            func: Function to test
            param_types: Dictionary mapping parameter names to their types
            
        Returns:
            List[EdgeCaseTestCase]: Generated edge case test cases
        """
        edge_tests = []
        
        # Generate type mismatch tests
        edge_tests.extend(self._generate_type_mismatch_tests(func, param_types))
        
        # Generate invalid input tests
        edge_tests.extend(self._generate_invalid_input_tests(func, param_types))
        
        # Generate missing parameter tests
        edge_tests.extend(self._generate_missing_parameter_tests(func, param_types))
        
        # Generate range violation tests
        edge_tests.extend(self._generate_range_violation_tests(func, param_types))
        
        # Store test cases
        func_name = func.__name__
        if func_name not in self.test_cases:
            self.test_cases[func_name] = []
        self.test_cases[func_name].extend(edge_tests)
        
        logger.info(f"Generated {len(edge_tests)} edge case test cases for {func_name}")
        return edge_tests
    
    def execute_boundary_tests(self, func: Callable, boundary_tests: List[BoundaryTestCase]) -> List[TestResult]:
        """
        Execute boundary test cases.
        
        Args:
            func: Function to test
            boundary_tests: List of boundary test cases
            
        Returns:
            List[TestResult]: Test execution results
        """
        results = []
        
        for test_case in boundary_tests:
            result = self._execute_single_test(func, test_case)
            results.append(result)
        
        # Store results
        func_name = func.__name__
        if func_name not in self.test_results:
            self.test_results[func_name] = []
        self.test_results[func_name].extend(results)
        
        return results
    
    def execute_edge_case_tests(self, func: Callable, edge_tests: List[EdgeCaseTestCase]) -> List[TestResult]:
        """
        Execute edge case test cases.
        
        Args:
            func: Function to test
            edge_tests: List of edge case test cases
            
        Returns:
            List[TestResult]: Test execution results
        """
        results = []
        
        for test_case in edge_tests:
            result = self._execute_single_test(func, test_case)
            results.append(result)
        
        # Store results
        func_name = func.__name__
        if func_name not in self.test_results:
            self.test_results[func_name] = []
        self.test_results[func_name].extend(results)
        
        return results
    
    def validate_exception_handling(self, func: Callable, 
                                  exception_scenarios: List[Dict[str, Any]]) -> List[TestResult]:
        """
        Validate exception handling for various error conditions.
        
        Args:
            func: Function to test
            exception_scenarios: List of scenarios that should raise exceptions
            
        Returns:
            List[TestResult]: Exception handling test results
        """
        results = []
        
        for scenario in exception_scenarios:
            test_name = f"exception_{scenario.get('name', 'unnamed')}"
            expected_exception = scenario.get('expected_exception', Exception)
            input_args = scenario.get('args', ())
            input_kwargs = scenario.get('kwargs', {})
            
            start_time = datetime.now()
            
            try:
                actual_result = func(*input_args, **input_kwargs)
                # If we reach here, no exception was raised
                result = TestResult(
                    test_name=test_name,
                    test_type="exception_handling",
                    passed=False,
                    actual_result=actual_result,
                    expected_exception=expected_exception,
                    execution_time=(datetime.now() - start_time).total_seconds(),
                    error_message=f"Expected {expected_exception.__name__} but no exception was raised"
                )
            except Exception as e:
                # Check if the raised exception matches expected
                passed = isinstance(e, expected_exception)
                result = TestResult(
                    test_name=test_name,
                    test_type="exception_handling",
                    passed=passed,
                    actual_exception=e,
                    expected_exception=expected_exception,
                    execution_time=(datetime.now() - start_time).total_seconds(),
                    error_message=None if passed else f"Expected {expected_exception.__name__} but got {type(e).__name__}"
                )
            
            results.append(result)
        
        # Store results
        func_name = func.__name__
        if func_name not in self.test_results:
            self.test_results[func_name] = []
        self.test_results[func_name].extend(results)
        
        return results
    
    def comprehensive_function_validation(self, func: Callable, 
                                        param_types: Optional[Dict[str, Type]] = None,
                                        exception_scenarios: Optional[List[Dict[str, Any]]] = None) -> ValidationReport:
        """
        Perform comprehensive validation of a function.
        
        Args:
            func: Function to validate
            param_types: Parameter types (auto-detected if not provided)
            exception_scenarios: Exception scenarios to test
            
        Returns:
            ValidationReport: Comprehensive validation report
        """
        func_name = func.__name__
        logger.info(f"Starting comprehensive validation for {func_name}")
        
        # Auto-detect parameter types if not provided
        if param_types is None:
            param_types = self._detect_parameter_types(func)
        
        # Generate and execute boundary tests
        boundary_tests = self.generate_boundary_tests(func, param_types)
        boundary_results = self.execute_boundary_tests(func, boundary_tests)
        
        # Generate and execute edge case tests
        edge_tests = self.generate_edge_case_tests(func, param_types)
        edge_results = self.execute_edge_case_tests(func, edge_tests)
        
        # Execute exception handling tests
        exception_results = []
        if exception_scenarios:
            exception_results = self.validate_exception_handling(func, exception_scenarios)
        
        # Calculate statistics
        all_results = boundary_results + edge_results + exception_results
        total_tests = len(all_results)
        passed_tests = sum(1 for r in all_results if r.passed)
        failed_tests = total_tests - passed_tests
        coverage_percentage = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Generate recommendations
        recommendations = self._generate_recommendations(all_results, param_types)
        
        # Create validation summary
        validation_summary = {
            'boundary_tests': len(boundary_results),
            'edge_case_tests': len(edge_results),
            'exception_tests': len(exception_results),
            'boundary_passed': sum(1 for r in boundary_results if r.passed),
            'edge_case_passed': sum(1 for r in edge_results if r.passed),
            'exception_passed': sum(1 for r in exception_results if r.passed),
            'validation_timestamp': datetime.now().isoformat()
        }
        
        report = ValidationReport(
            function_name=func_name,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            boundary_tests=boundary_results,
            edge_case_tests=edge_results,
            exception_tests=exception_results,
            coverage_percentage=coverage_percentage,
            validation_summary=validation_summary,
            recommendations=recommendations
        )
        
        logger.info(f"Validation completed for {func_name}: {passed_tests}/{total_tests} tests passed")
        return report  
  
    def _execute_single_test(self, func: Callable, 
                           test_case: Union[BoundaryTestCase, EdgeCaseTestCase]) -> TestResult:
        """Execute a single test case."""
        start_time = datetime.now()
        
        try:
            # Prepare arguments
            if isinstance(test_case, BoundaryTestCase):
                # For boundary tests, we typically test one parameter at a time
                sig = inspect.signature(func)
                params = list(sig.parameters.keys())
                if params:
                    args = [test_case.input_value]
                    kwargs = {}
                else:
                    args = []
                    kwargs = {}
            else:
                # For edge case tests, we use the input_values dict
                args = []
                kwargs = test_case.input_values
            
            # Execute function
            actual_result = func(*args, **kwargs)
            
            # Check if exception was expected but not raised
            if test_case.expected_exception:
                return TestResult(
                    test_name=test_case.name,
                    test_type=type(test_case).__name__,
                    passed=False,
                    actual_result=actual_result,
                    expected_exception=test_case.expected_exception,
                    execution_time=(datetime.now() - start_time).total_seconds(),
                    error_message=f"Expected {test_case.expected_exception.__name__} but no exception was raised"
                )
            
            # Check result if expected result is specified
            if test_case.expected_result is not None:
                passed = actual_result == test_case.expected_result
                error_message = None if passed else f"Expected {test_case.expected_result}, got {actual_result}"
            else:
                passed = True
                error_message = None
            
            return TestResult(
                test_name=test_case.name,
                test_type=type(test_case).__name__,
                passed=passed,
                actual_result=actual_result,
                expected_result=test_case.expected_result,
                execution_time=(datetime.now() - start_time).total_seconds(),
                error_message=error_message
            )
            
        except Exception as e:
            # Check if this exception was expected
            if test_case.expected_exception and isinstance(e, test_case.expected_exception):
                passed = True
                error_message = None
            else:
                passed = False
                error_message = f"Unexpected exception: {type(e).__name__}: {str(e)}"
            
            return TestResult(
                test_name=test_case.name,
                test_type=type(test_case).__name__,
                passed=passed,
                actual_exception=e,
                expected_exception=test_case.expected_exception,
                execution_time=(datetime.now() - start_time).total_seconds(),
                error_message=error_message
            )
    
    def _detect_parameter_types(self, func: Callable) -> Dict[str, Type]:
        """Auto-detect parameter types from function signature."""
        param_types = {}
        
        try:
            sig = inspect.signature(func)
            for param_name, param in sig.parameters.items():
                if param.annotation != inspect.Parameter.empty:
                    param_types[param_name] = param.annotation
                else:
                    # Default to common types for testing
                    param_types[param_name] = str
        except Exception as e:
            logger.warning(f"Could not detect parameter types for {func.__name__}: {str(e)}")
        
        return param_types
    
    def _generate_int_boundaries(self, param_name: str) -> List[BoundaryTestCase]:
        """Generate boundary test cases for integer parameters."""
        return [
            BoundaryTestCase(
                name=f"{param_name}_zero",
                boundary_type=BoundaryType.ZERO,
                input_value=0,
                description="Test with zero value"
            ),
            BoundaryTestCase(
                name=f"{param_name}_positive_one",
                boundary_type=BoundaryType.POSITIVE,
                input_value=1,
                description="Test with positive one"
            ),
            BoundaryTestCase(
                name=f"{param_name}_negative_one",
                boundary_type=BoundaryType.NEGATIVE,
                input_value=-1,
                description="Test with negative one"
            ),
            BoundaryTestCase(
                name=f"{param_name}_max_int",
                boundary_type=BoundaryType.MAXIMUM,
                input_value=sys.maxsize,
                description="Test with maximum integer value"
            ),
            BoundaryTestCase(
                name=f"{param_name}_min_int",
                boundary_type=BoundaryType.MINIMUM,
                input_value=-sys.maxsize-1,
                description="Test with minimum integer value"
            )
        ]
    
    def _generate_float_boundaries(self, param_name: str) -> List[BoundaryTestCase]:
        """Generate boundary test cases for float parameters."""
        return [
            BoundaryTestCase(
                name=f"{param_name}_zero_float",
                boundary_type=BoundaryType.ZERO,
                input_value=0.0,
                description="Test with zero float"
            ),
            BoundaryTestCase(
                name=f"{param_name}_positive_infinity",
                boundary_type=BoundaryType.INFINITY,
                input_value=float('inf'),
                description="Test with positive infinity"
            ),
            BoundaryTestCase(
                name=f"{param_name}_negative_infinity",
                boundary_type=BoundaryType.INFINITY,
                input_value=float('-inf'),
                description="Test with negative infinity"
            ),
            BoundaryTestCase(
                name=f"{param_name}_nan",
                boundary_type=BoundaryType.NAN,
                input_value=float('nan'),
                description="Test with NaN value"
            ),
            BoundaryTestCase(
                name=f"{param_name}_max_float",
                boundary_type=BoundaryType.MAXIMUM,
                input_value=sys.float_info.max,
                description="Test with maximum float value"
            ),
            BoundaryTestCase(
                name=f"{param_name}_min_float",
                boundary_type=BoundaryType.MINIMUM,
                input_value=sys.float_info.min,
                description="Test with minimum float value"
            )
        ]
    
    def _generate_string_boundaries(self, param_name: str) -> List[BoundaryTestCase]:
        """Generate boundary test cases for string parameters."""
        return [
            BoundaryTestCase(
                name=f"{param_name}_empty_string",
                boundary_type=BoundaryType.EMPTY,
                input_value="",
                description="Test with empty string"
            ),
            BoundaryTestCase(
                name=f"{param_name}_single_char",
                boundary_type=BoundaryType.MINIMUM,
                input_value="a",
                description="Test with single character"
            ),
            BoundaryTestCase(
                name=f"{param_name}_whitespace",
                boundary_type=BoundaryType.EMPTY,
                input_value=" ",
                description="Test with whitespace"
            ),
            BoundaryTestCase(
                name=f"{param_name}_newline",
                boundary_type=BoundaryType.EMPTY,
                input_value="\n",
                description="Test with newline character"
            ),
            BoundaryTestCase(
                name=f"{param_name}_long_string",
                boundary_type=BoundaryType.MAXIMUM,
                input_value="a" * 10000,
                description="Test with very long string"
            ),
            BoundaryTestCase(
                name=f"{param_name}_unicode",
                boundary_type=BoundaryType.MAXIMUM,
                input_value="🚀🌟💫",
                description="Test with unicode characters"
            )
        ]
    
    def _generate_list_boundaries(self, param_name: str) -> List[BoundaryTestCase]:
        """Generate boundary test cases for list parameters."""
        return [
            BoundaryTestCase(
                name=f"{param_name}_empty_list",
                boundary_type=BoundaryType.EMPTY,
                input_value=[],
                description="Test with empty list"
            ),
            BoundaryTestCase(
                name=f"{param_name}_single_item",
                boundary_type=BoundaryType.MINIMUM,
                input_value=[1],
                description="Test with single item list"
            ),
            BoundaryTestCase(
                name=f"{param_name}_large_list",
                boundary_type=BoundaryType.MAXIMUM,
                input_value=list(range(10000)),
                description="Test with large list"
            ),
            BoundaryTestCase(
                name=f"{param_name}_none_items",
                boundary_type=BoundaryType.NULL,
                input_value=[None, None, None],
                description="Test with list of None values"
            )
        ]
    
    def _generate_dict_boundaries(self, param_name: str) -> List[BoundaryTestCase]:
        """Generate boundary test cases for dictionary parameters."""
        return [
            BoundaryTestCase(
                name=f"{param_name}_empty_dict",
                boundary_type=BoundaryType.EMPTY,
                input_value={},
                description="Test with empty dictionary"
            ),
            BoundaryTestCase(
                name=f"{param_name}_single_key",
                boundary_type=BoundaryType.MINIMUM,
                input_value={"key": "value"},
                description="Test with single key dictionary"
            ),
            BoundaryTestCase(
                name=f"{param_name}_large_dict",
                boundary_type=BoundaryType.MAXIMUM,
                input_value={f"key_{i}": i for i in range(1000)},
                description="Test with large dictionary"
            ),
            BoundaryTestCase(
                name=f"{param_name}_none_values",
                boundary_type=BoundaryType.NULL,
                input_value={"key1": None, "key2": None},
                description="Test with None values"
            )
        ]
    
    def _generate_bool_boundaries(self, param_name: str) -> List[BoundaryTestCase]:
        """Generate boundary test cases for boolean parameters."""
        return [
            BoundaryTestCase(
                name=f"{param_name}_true",
                boundary_type=BoundaryType.POSITIVE,
                input_value=True,
                description="Test with True value"
            ),
            BoundaryTestCase(
                name=f"{param_name}_false",
                boundary_type=BoundaryType.NEGATIVE,
                input_value=False,
                description="Test with False value"
            )
        ]
    
    def _generate_type_mismatch_tests(self, func: Callable, param_types: Dict[str, Type]) -> List[EdgeCaseTestCase]:
        """Generate type mismatch test cases."""
        tests = []
        
        for param_name, expected_type in param_types.items():
            # Generate wrong type values
            wrong_types = {
                int: ["string", [], {}, None],
                float: ["string", [], {}, None],
                str: [123, [], {}, None],
                list: ["string", 123, {}, None],
                dict: ["string", 123, [], None],
                bool: ["string", 123, [], {}]
            }
            
            if expected_type in wrong_types:
                for wrong_value in wrong_types[expected_type]:
                    tests.append(EdgeCaseTestCase(
                        name=f"{param_name}_type_mismatch_{type(wrong_value).__name__}",
                        edge_case_type=EdgeCaseType.TYPE_MISMATCH,
                        input_values={param_name: wrong_value},
                        expected_exception=TypeError,
                        description=f"Test {param_name} with wrong type {type(wrong_value).__name__}"
                    ))
        
        return tests
    
    def _generate_invalid_input_tests(self, func: Callable, param_types: Dict[str, Type]) -> List[EdgeCaseTestCase]:
        """Generate invalid input test cases."""
        tests = []
        
        for param_name, param_type in param_types.items():
            if param_type == str:
                # Invalid string formats
                invalid_strings = ["", " ", "\0", "\n\r\t"]
                for invalid_str in invalid_strings:
                    tests.append(EdgeCaseTestCase(
                        name=f"{param_name}_invalid_string_{repr(invalid_str)}",
                        edge_case_type=EdgeCaseType.INVALID_INPUT,
                        input_values={param_name: invalid_str},
                        description=f"Test {param_name} with invalid string format"
                    ))
            
            elif param_type in [int, float]:
                # Invalid numeric values
                tests.append(EdgeCaseTestCase(
                    name=f"{param_name}_division_by_zero",
                    edge_case_type=EdgeCaseType.INVALID_INPUT,
                    input_values={param_name: 0},
                    expected_exception=ZeroDivisionError,
                    description=f"Test {param_name} with zero (potential division by zero)"
                ))
        
        return tests
    
    def _generate_missing_parameter_tests(self, func: Callable, param_types: Dict[str, Type]) -> List[EdgeCaseTestCase]:
        """Generate missing parameter test cases."""
        tests = []
        
        # Test with completely empty parameters
        tests.append(EdgeCaseTestCase(
            name="missing_all_parameters",
            edge_case_type=EdgeCaseType.MISSING_PARAMETER,
            input_values={},
            expected_exception=TypeError,
            description="Test with no parameters provided"
        ))
        
        # Test with missing individual parameters
        for param_name in param_types.keys():
            other_params = {k: self._get_default_value(v) for k, v in param_types.items() if k != param_name}
            tests.append(EdgeCaseTestCase(
                name=f"missing_{param_name}",
                edge_case_type=EdgeCaseType.MISSING_PARAMETER,
                input_values=other_params,
                expected_exception=TypeError,
                description=f"Test with missing {param_name} parameter"
            ))
        
        return tests
    
    def _generate_range_violation_tests(self, func: Callable, param_types: Dict[str, Type]) -> List[EdgeCaseTestCase]:
        """Generate range violation test cases."""
        tests = []
        
        for param_name, param_type in param_types.items():
            if param_type == int:
                # Test with extreme values
                extreme_values = [sys.maxsize + 1, -sys.maxsize - 2, 2**63, -2**63]
                for extreme_val in extreme_values:
                    try:
                        tests.append(EdgeCaseTestCase(
                            name=f"{param_name}_extreme_value_{extreme_val}",
                            edge_case_type=EdgeCaseType.RANGE_VIOLATION,
                            input_values={param_name: extreme_val},
                            expected_exception=OverflowError,
                            description=f"Test {param_name} with extreme value {extreme_val}"
                        ))
                    except OverflowError:
                        # Skip values that can't even be created
                        pass
            
            elif param_type == float:
                # Test with extreme float values
                tests.append(EdgeCaseTestCase(
                    name=f"{param_name}_overflow",
                    edge_case_type=EdgeCaseType.RANGE_VIOLATION,
                    input_values={param_name: 1e308 * 10},
                    expected_exception=OverflowError,
                    description=f"Test {param_name} with overflow value"
                ))
        
        return tests
    
    def _get_default_value(self, param_type: Type) -> Any:
        """Get a default value for a parameter type."""
        defaults = {
            int: 0,
            float: 0.0,
            str: "",
            list: [],
            dict: {},
            bool: False
        }
        return defaults.get(param_type, None)
    
    def _generate_recommendations(self, results: List[TestResult], param_types: Dict[str, Type]) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        failed_tests = [r for r in results if not r.passed]
        
        if failed_tests:
            recommendations.append(f"Consider adding input validation for {len(failed_tests)} failing test cases")
        
        # Check for specific patterns
        type_errors = [r for r in failed_tests if r.actual_exception and isinstance(r.actual_exception, TypeError)]
        if type_errors:
            recommendations.append("Add type checking and validation for input parameters")
        
        value_errors = [r for r in failed_tests if r.actual_exception and isinstance(r.actual_exception, ValueError)]
        if value_errors:
            recommendations.append("Add value range validation and better error messages")
        
        zero_division_errors = [r for r in failed_tests if r.actual_exception and isinstance(r.actual_exception, ZeroDivisionError)]
        if zero_division_errors:
            recommendations.append("Add checks to prevent division by zero")
        
        # Check for missing exception handling
        unexpected_exceptions = [r for r in failed_tests if r.actual_exception and not r.expected_exception]
        if unexpected_exceptions:
            recommendations.append("Consider adding exception handling for unexpected error conditions")
        
        if not recommendations:
            recommendations.append("Function handles edge cases and boundary conditions well")
        
        return recommendations
    
    def generate_test_report(self, validation_report: ValidationReport) -> str:
        """
        Generate a comprehensive test report.
        
        Args:
            validation_report: Validation report to format
            
        Returns:
            str: Formatted test report
        """
        report_lines = [
            "=" * 80,
            f"EDGE CASE AND BOUNDARY TESTING REPORT: {validation_report.function_name}",
            "=" * 80,
            f"Validation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Tests: {validation_report.total_tests}",
            f"Passed: {validation_report.passed_tests}",
            f"Failed: {validation_report.failed_tests}",
            f"Success Rate: {validation_report.coverage_percentage:.1f}%",
            "",
            "TEST BREAKDOWN:",
            f"  Boundary Tests: {len(validation_report.boundary_tests)} ({sum(1 for t in validation_report.boundary_tests if t.passed)} passed)",
            f"  Edge Case Tests: {len(validation_report.edge_case_tests)} ({sum(1 for t in validation_report.edge_case_tests if t.passed)} passed)",
            f"  Exception Tests: {len(validation_report.exception_tests)} ({sum(1 for t in validation_report.exception_tests if t.passed)} passed)",
            ""
        ]
        
        # Failed tests details
        all_tests = validation_report.boundary_tests + validation_report.edge_case_tests + validation_report.exception_tests
        failed_tests = [t for t in all_tests if not t.passed]
        
        if failed_tests:
            report_lines.extend([
                "FAILED TESTS:",
                *[f"  ❌ {test.test_name}: {test.error_message or 'Unknown error'}" for test in failed_tests[:10]],
                f"  ... and {len(failed_tests) - 10} more" if len(failed_tests) > 10 else "",
                ""
            ])
        
        # Recommendations
        if validation_report.recommendations:
            report_lines.extend([
                "RECOMMENDATIONS:",
                *[f"  • {rec}" for rec in validation_report.recommendations],
                ""
            ])
        
        # Summary statistics
        report_lines.extend([
            "VALIDATION SUMMARY:",
            *[f"  {key}: {value}" for key, value in validation_report.validation_summary.items()],
            "=" * 80
        ])
        
        return "\n".join(report_lines)
    
    def get_test_statistics(self, func_name: str) -> Dict[str, Any]:
        """Get test statistics for a function."""
        if func_name not in self.test_results:
            return {'error': f"No test results found for {func_name}"}
        
        results = self.test_results[func_name]
        
        return {
            'function_name': func_name,
            'total_tests': len(results),
            'passed_tests': sum(1 for r in results if r.passed),
            'failed_tests': sum(1 for r in results if not r.passed),
            'success_rate': sum(1 for r in results if r.passed) / len(results) * 100 if results else 0,
            'average_execution_time': sum(r.execution_time for r in results) / len(results) if results else 0,
            'test_types': {
                'boundary': sum(1 for r in results if r.test_type == 'BoundaryTestCase'),
                'edge_case': sum(1 for r in results if r.test_type == 'EdgeCaseTestCase'),
                'exception': sum(1 for r in results if r.test_type == 'exception_handling')
            }
        }