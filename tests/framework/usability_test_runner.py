#!/usr/bin/env python3
"""
Usability Test Runner for Algorithmic Trading System

This module implements comprehensive usability testing functionality that validates
user experience, interface accessibility, and workflow efficiency.

Key Features:
- User interface usability testing
- Workflow efficiency testing
- Accessibility compliance testing
- User experience validation
- Cognitive load assessment
- Task completion testing
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

# Testing framework imports
import pytest
import pytest_asyncio


class UsabilityTestType(Enum):
    """Types of usability tests supported"""
    INTERFACE_USABILITY = "interface_usability"
    WORKFLOW_EFFICIENCY = "workflow_efficiency"
    ACCESSIBILITY_COMPLIANCE = "accessibility_compliance"
    USER_EXPERIENCE = "user_experience"
    COGNITIVE_LOAD = "cognitive_load"
    TASK_COMPLETION = "task_completion"
    USER_SATISFACTION = "user_satisfaction"


class InteractionType(Enum):
    """Types of user interactions to test"""
    CLICK = "click"
    TYPE = "type"
    DRAG_DROP = "drag_drop"
    NAVIGATE = "navigate"
    SEARCH = "search"
    FILTER = "filter"
    SORT = "sort"
    SELECT = "select"


class UsabilityTestStatus(Enum):
    """Status of usability test execution"""
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    PARTIAL_SUCCESS = "partial_success"


class AccessibilityStandard(Enum):
    """Accessibility standards to test against"""
    WCAG_2_1_AA = "wcag_2_1_aa"
    WCAG_2_1_AAA = "wcag_2_1_aaa"
    SECTION_508 = "section_508"
    ADA_COMPLIANCE = "ada_compliance"


@dataclass
class UsabilityTestCase:
    """Represents a single usability test case"""
    test_id: str
    test_name: str
    usability_type: UsabilityTestType
    interaction_scenarios: List[InteractionType]
    test_function: Callable
    setup_function: Optional[Callable] = None
    teardown_function: Optional[Callable] = None
    validation_function: Optional[Callable] = None
    timeout_seconds: int = 60
    expected_completion_time: float = 30.0  # seconds
    expected_success_rate: float = 0.95  # 95%
    accessibility_standards: List[AccessibilityStandard] = field(default_factory=list)
    user_profiles: List[str] = field(default_factory=list)
    skip_conditions: List[str] = field(default_factory=list)


@dataclass
class UsabilityTestResult:
    """Results of a single usability test"""
    test_case: UsabilityTestCase
    user_profile: str
    status: UsabilityTestStatus
    start_time: datetime
    end_time: datetime
    total_duration: float
    task_completion_time: float
    interaction_count: int
    error_count: int
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    usability_metrics: Dict[str, Any] = field(default_factory=dict)
    accessibility_metrics: Dict[str, Any] = field(default_factory=dict)
    user_satisfaction_score: float = 0.0
    cognitive_load_score: float = 0.0
    workflow_efficiency_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)


@dataclass
class UsabilityTestSuiteResult:
    """Results of a usability test suite execution"""
    suite_name: str
    start_time: datetime
    end_time: datetime
    total_duration: float
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int
    skipped_tests: int
    partial_success_tests: int
    pass_rate: float
    test_results: List[UsabilityTestResult]
    usability_summary: Dict[str, Any] = field(default_factory=dict)
    user_profile_summary: Dict[str, Any] = field(default_factory=dict)
    accessibility_summary: Dict[str, Any] = field(default_factory=dict)
    performance_summary: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class UsabilityTestRunner:
    """
    Comprehensive usability test runner for the algorithmic trading system.
    
    This class orchestrates usability testing across various user interactions,
    validating user experience, accessibility, and workflow efficiency.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the UsabilityTestRunner.
        
        Args:
            config: Configuration dictionary for usability testing settings
        """
        self.config = config or {}
        self.logger = self._setup_logging()
        self.test_cases: Dict[str, UsabilityTestCase] = {}
        self.test_results: Dict[str, UsabilityTestResult] = {}
        self.suite_results: List[UsabilityTestSuiteResult] = []
        
        # Test configuration
        self.default_timeout = self.config.get('default_timeout', 60)
        self.default_expected_completion_time = self.config.get('default_expected_completion_time', 30.0)
        self.default_expected_success_rate = self.config.get('default_expected_success_rate', 0.95)
        
        # User profiles for testing
        self.user_profiles = self.config.get('user_profiles', [
            'beginner_trader', 'intermediate_trader', 'expert_trader',
            'risk_manager', 'compliance_officer', 'system_administrator'
        ])
        
        self.logger.info("UsabilityTestRunner initialized")
        self.logger.info(f"Configured user profiles: {self.user_profiles}")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the usability test runner"""
        logger = logging.getLogger('UsabilityTestRunner')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def register_test_case(self, test_case: UsabilityTestCase) -> None:
        """
        Register a new usability test case.
        
        Args:
            test_case: The usability test case to register
        """
        self.test_cases[test_case.test_id] = test_case
        self.logger.info(f"Registered usability test case: {test_case.test_name}")
    
    def register_interface_usability_test(
        self,
        test_name: str,
        interaction_scenarios: List[InteractionType],
        test_function: Callable,
        validation_function: Callable,
        expected_completion_time: float = 30.0,
        user_profiles: List[str] = None
    ) -> str:
        """
        Register an interface usability test.
        
        Args:
            test_name: Name of the test
            interaction_scenarios: List of interaction scenarios to test
            test_function: Function to execute for testing
            validation_function: Function to validate usability
            expected_completion_time: Expected time for task completion in seconds
            user_profiles: List of user profiles to test with
            
        Returns:
            Test case ID
        """
        test_id = f"interface_usability_{uuid.uuid4().hex[:8]}"
        
        test_case = UsabilityTestCase(
            test_id=test_id,
            test_name=test_name,
            usability_type=UsabilityTestType.INTERFACE_USABILITY,
            interaction_scenarios=interaction_scenarios,
            test_function=test_function,
            validation_function=validation_function,
            expected_completion_time=expected_completion_time,
            user_profiles=user_profiles or self.user_profiles
        )
        
        self.register_test_case(test_case)
        return test_id
    
    def register_workflow_efficiency_test(
        self,
        test_name: str,
        interaction_scenarios: List[InteractionType],
        test_function: Callable,
        validation_function: Callable,
        expected_completion_time: float = 45.0,
        user_profiles: List[str] = None
    ) -> str:
        """
        Register a workflow efficiency test.
        
        Args:
            test_name: Name of the test
            interaction_scenarios: List of interaction scenarios to test
            test_function: Function to execute for testing
            validation_function: Function to validate workflow efficiency
            expected_completion_time: Expected time for task completion in seconds
            user_profiles: List of user profiles to test with
            
        Returns:
            Test case ID
        """
        test_id = f"workflow_efficiency_{uuid.uuid4().hex[:8]}"
        
        test_case = UsabilityTestCase(
            test_id=test_id,
            test_name=test_name,
            usability_type=UsabilityTestType.WORKFLOW_EFFICIENCY,
            interaction_scenarios=interaction_scenarios,
            test_function=test_function,
            validation_function=validation_function,
            expected_completion_time=expected_completion_time,
            user_profiles=user_profiles or self.user_profiles
        )
        
        self.register_test_case(test_case)
        return test_id
    
    def register_accessibility_compliance_test(
        self,
        test_name: str,
        accessibility_standards: List[AccessibilityStandard],
        test_function: Callable,
        validation_function: Callable,
        user_profiles: List[str] = None
    ) -> str:
        """
        Register an accessibility compliance test.
        
        Args:
            test_name: Name of the test
            accessibility_standards: List of accessibility standards to test against
            test_function: Function to execute for testing
            validation_function: Function to validate accessibility compliance
            user_profiles: List of user profiles to test with
            
        Returns:
            Test case ID
        """
        test_id = f"accessibility_{uuid.uuid4().hex[:8]}"
        
        test_case = UsabilityTestCase(
            test_id=test_id,
            test_name=test_name,
            usability_type=UsabilityTestType.ACCESSIBILITY_COMPLIANCE,
            interaction_scenarios=[],  # Not applicable for accessibility tests
            test_function=test_function,
            validation_function=validation_function,
            accessibility_standards=accessibility_standards,
            user_profiles=user_profiles or self.user_profiles
        )
        
        self.register_test_case(test_case)
        return test_id
    
    def register_user_experience_test(
        self,
        test_name: str,
        interaction_scenarios: List[InteractionType],
        test_function: Callable,
        validation_function: Callable,
        expected_success_rate: float = 0.95,
        user_profiles: List[str] = None
    ) -> str:
        """
        Register a user experience test.
        
        Args:
            test_name: Name of the test
            interaction_scenarios: List of interaction scenarios to test
            test_function: Function to execute for testing
            validation_function: Function to validate user experience
            expected_success_rate: Expected success rate (0.0 to 1.0)
            user_profiles: List of user profiles to test with
            
        Returns:
            Test case ID
        """
        test_id = f"user_experience_{uuid.uuid4().hex[:8]}"
        
        test_case = UsabilityTestCase(
            test_id=test_id,
            test_name=test_name,
            usability_type=UsabilityTestType.USER_EXPERIENCE,
            interaction_scenarios=interaction_scenarios,
            test_function=test_function,
            validation_function=validation_function,
            expected_success_rate=expected_success_rate,
            user_profiles=user_profiles or self.user_profiles
        )
        
        self.register_test_case(test_case)
        return test_id
    
    def register_cognitive_load_test(
        self,
        test_name: str,
        interaction_scenarios: List[InteractionType],
        test_function: Callable,
        validation_function: Callable,
        user_profiles: List[str] = None
    ) -> str:
        """
        Register a cognitive load assessment test.
        
        Args:
            test_name: Name of the test
            interaction_scenarios: List of interaction scenarios to test
            test_function: Function to execute for testing
            validation_function: Function to validate cognitive load
            user_profiles: List of user profiles to test with
            
        Returns:
            Test case ID
        """
        test_id = f"cognitive_load_{uuid.uuid4().hex[:8]}"
        
        test_case = UsabilityTestCase(
            test_id=test_id,
            test_name=test_name,
            usability_type=UsabilityTestType.COGNITIVE_LOAD,
            interaction_scenarios=interaction_scenarios,
            test_function=test_function,
            validation_function=validation_function,
            user_profiles=user_profiles or self.user_profiles
        )
        
        self.register_test_case(test_case)
        return test_id
    
    def register_task_completion_test(
        self,
        test_name: str,
        interaction_scenarios: List[InteractionType],
        test_function: Callable,
        validation_function: Callable,
        expected_completion_time: float = 25.0,
        expected_success_rate: float = 0.95,
        user_profiles: List[str] = None
    ) -> str:
        """
        Register a task completion test.
        
        Args:
            test_name: Name of the test
            interaction_scenarios: List of interaction scenarios to test
            test_function: Function to execute for testing
            validation_function: Function to validate task completion
            expected_completion_time: Expected time for task completion in seconds
            expected_success_rate: Expected success rate (0.0 to 1.0)
            user_profiles: List of user profiles to test with
            
        Returns:
            Test case ID
        """
        test_id = f"task_completion_{uuid.uuid4().hex[:8]}"
        
        test_case = UsabilityTestCase(
            test_id=test_id,
            test_name=test_name,
            usability_type=UsabilityTestType.TASK_COMPLETION,
            interaction_scenarios=interaction_scenarios,
            test_function=test_function,
            validation_function=validation_function,
            expected_completion_time=expected_completion_time,
            expected_success_rate=expected_success_rate,
            user_profiles=user_profiles or self.user_profiles
        )
        
        self.register_test_case(test_case)
        return test_id

    async def execute_test_case(self, test_id: str, user_profile: str) -> UsabilityTestResult:
        """
        Execute a single usability test case.
        
        Args:
            test_id: ID of the test case to execute
            user_profile: User profile to test with
            
        Returns:
            Usability test result
        """
        if test_id not in self.test_cases:
            raise ValueError(f"Test case {test_id} not found")
        
        test_case = self.test_cases[test_id]
        start_time = datetime.now()
        end_time = start_time
        
        self.logger.info(f"Executing usability test: {test_case.test_name} with user profile: {user_profile}")
        
        # Check if this user profile is supported by the test
        if test_case.user_profiles and user_profile not in test_case.user_profiles:
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            result = UsabilityTestResult(
                test_case=test_case,
                user_profile=user_profile,
                status=UsabilityTestStatus.SKIPPED,
                start_time=start_time,
                end_time=end_time,
                total_duration=total_duration,
                task_completion_time=0.0,
                interaction_count=0,
                error_count=0,
                error_message=f"User profile {user_profile} not supported by this test"
            )
            self.test_results[test_id] = result
            return result
        
        # Check skip conditions
        if self._should_skip_test(test_case, user_profile):
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            result = UsabilityTestResult(
                test_case=test_case,
                user_profile=user_profile,
                status=UsabilityTestStatus.SKIPPED,
                start_time=start_time,
                end_time=end_time,
                total_duration=total_duration,
                task_completion_time=0.0,
                interaction_count=0,
                error_count=0,
                error_message="Test skipped due to skip conditions"
            )
            self.test_results[test_id] = result
            return result
        
        try:
            # Setup phase
            if test_case.setup_function:
                await self._execute_with_timeout(
                    test_case.setup_function(user_profile), test_case.timeout_seconds
                )
            
            # Execute test
            test_start_time = datetime.now()
            test_result_data = await self._execute_with_timeout(
                test_case.test_function(user_profile), test_case.timeout_seconds
            )
            test_end_time = datetime.now()
            
            task_completion_time = (test_end_time - test_start_time).total_seconds()
            total_duration = (test_end_time - start_time).total_seconds()
            
            # Validate results
            validation_result = await self._validate_usability(
                test_case, user_profile, test_result_data
            )
            
            # Determine final status based on validation
            success_rate = validation_result.get('success_rate', 1.0)
            if success_rate >= test_case.expected_success_rate:
                status = UsabilityTestStatus.PASSED
            elif success_rate >= test_case.expected_success_rate * 0.7:  # 70% of expected
                status = UsabilityTestStatus.PARTIAL_SUCCESS
            else:
                status = UsabilityTestStatus.FAILED
            
            # Create result
            result = UsabilityTestResult(
                test_case=test_case,
                user_profile=user_profile,
                status=status,
                start_time=start_time,
                end_time=test_end_time,
                total_duration=total_duration,
                task_completion_time=task_completion_time,
                interaction_count=validation_result.get('interaction_count', 0),
                error_count=validation_result.get('error_count', 0),
                usability_metrics=validation_result.get('usability_metrics', {}),
                accessibility_metrics=validation_result.get('accessibility_metrics', {}),
                user_satisfaction_score=validation_result.get('user_satisfaction_score', 0.0),
                cognitive_load_score=validation_result.get('cognitive_load_score', 0.0),
                workflow_efficiency_score=validation_result.get('workflow_efficiency_score', 0.0)
            )
            
        except asyncio.TimeoutError:
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            result = UsabilityTestResult(
                test_case=test_case,
                user_profile=user_profile,
                status=UsabilityTestStatus.ERROR,
                start_time=start_time,
                end_time=end_time,
                total_duration=total_duration,
                task_completion_time=0.0,
                interaction_count=0,
                error_count=1,
                error_message=f"Test timed out after {test_case.timeout_seconds} seconds"
            )
            
        except Exception as e:
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            self.logger.error(f"Test {test_case.test_name} failed with error: {str(e)}")
            
            result = UsabilityTestResult(
                test_case=test_case,
                user_profile=user_profile,
                status=UsabilityTestStatus.FAILED,
                start_time=start_time,
                end_time=end_time,
                total_duration=total_duration,
                task_completion_time=0.0,
                interaction_count=0,
                error_count=1,
                error_message=str(e),
                stack_trace=traceback.format_exc()
            )
            
        finally:
            # Teardown phase
            if test_case.teardown_function:
                try:
                    await self._execute_with_timeout(
                        test_case.teardown_function(user_profile), test_case.timeout_seconds
                    )
                except Exception as e:
                    self.logger.warning(f"Teardown failed for {test_case.test_name}: {e}")
        
        self.test_results[test_id] = result
        self.logger.info(f"Test {test_case.test_name} completed with status: {result.status.value}")
        
        return result
    
    def _should_skip_test(self, test_case: UsabilityTestCase, user_profile: str) -> bool:
        """Determine if a test should be skipped based on conditions"""
        # Check skip conditions
        if test_case.skip_conditions:
            for condition in test_case.skip_conditions:
                if self._evaluate_skip_condition(condition, user_profile):
                    return True
        return False
    
    def _evaluate_skip_condition(self, condition: str, user_profile: str) -> bool:
        """Evaluate a skip condition"""
        # Simple implementation - in a real system, this would be more sophisticated
        if "not_beginner" in condition and user_profile == "beginner_trader":
            return True
        if "not_expert" in condition and user_profile == "expert_trader":
            return True
        return False
    
    async def _execute_with_timeout(self, coro, timeout_seconds: int):
        """Execute a coroutine with timeout"""
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    
    async def _validate_usability(self, test_case: UsabilityTestCase, user_profile: str, 
                               test_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate usability test results"""
        self.logger.info(f"Validating usability for {test_case.test_name} with user profile: {user_profile}")
        
        # If custom validation function is provided, use it
        if test_case.validation_function:
            return await test_case.validation_function(user_profile, test_result)
        
        # Default validation
        return {
            'success_rate': 1.0,
            'interaction_count': test_result.get('interaction_count', 0),
            'error_count': test_result.get('error_count', 0),
            'usability_metrics': test_result.get('usability_metrics', {}),
            'accessibility_metrics': test_result.get('accessibility_metrics', {}),
            'user_satisfaction_score': test_result.get('user_satisfaction_score', 0.8),
            'cognitive_load_score': test_result.get('cognitive_load_score', 0.3),
            'workflow_efficiency_score': test_result.get('workflow_efficiency_score', 0.9)
        }
    
    async def execute_test_suite(
        self,
        suite_name: str,
        test_ids: Optional[List[str]] = None,
        user_profiles: Optional[List[str]] = None,
        parallel_execution: bool = True
    ) -> UsabilityTestSuiteResult:
        """
        Execute a suite of usability tests.
        
        Args:
            suite_name: Name of the test suite
            test_ids: List of test IDs to execute (None for all)
            user_profiles: List of user profiles to test with (None for all configured)
            parallel_execution: Whether to execute tests in parallel
            
        Returns:
            Usability test suite result
        """
        start_time = datetime.now()
        
        if test_ids is None:
            test_ids = list(self.test_cases.keys())
        
        user_profiles = user_profiles or self.user_profiles
        
        # Generate all test combinations
        test_combinations = []
        for test_id in test_ids:
            test_case = self.test_cases[test_id]
            profiles_to_test = [p for p in user_profiles if not test_case.user_profiles or p in test_case.user_profiles]
            for profile in profiles_to_test:
                test_combinations.append((test_id, profile))
        
        self.logger.info(f"Executing usability test suite: {suite_name}")
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
        passed_tests = sum(1 for r in results if r.status == UsabilityTestStatus.PASSED)
        failed_tests = sum(1 for r in results if r.status == UsabilityTestStatus.FAILED)
        error_tests = sum(1 for r in results if r.status == UsabilityTestStatus.ERROR)
        skipped_tests = sum(1 for r in results if r.status == UsabilityTestStatus.SKIPPED)
        partial_success_tests = sum(1 for r in results if r.status == UsabilityTestStatus.PARTIAL_SUCCESS)
        
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Generate summaries
        usability_summary = self._generate_usability_summary(results)
        user_profile_summary = self._generate_user_profile_summary(results)
        accessibility_summary = self._generate_accessibility_summary(results)
        performance_summary = self._generate_performance_summary(results)
        recommendations = self._generate_recommendations(results)
        
        suite_result = UsabilityTestSuiteResult(
            suite_name=suite_name,
            start_time=start_time,
            end_time=end_time,
            total_duration=total_duration,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            error_tests=error_tests,
            skipped_tests=skipped_tests,
            partial_success_tests=partial_success_tests,
            pass_rate=pass_rate,
            test_results=results,
            usability_summary=usability_summary,
            user_profile_summary=user_profile_summary,
            accessibility_summary=accessibility_summary,
            performance_summary=performance_summary,
            recommendations=recommendations
        )
        
        self.suite_results.append(suite_result)
        
        self.logger.info(
            f"Suite {suite_name} completed: {passed_tests}/{total_tests} passed "
            f"({pass_rate:.1f}% pass rate)"
        )
        
        return suite_result
    
    async def _execute_tests_parallel(self, test_combinations: List[Tuple]) -> List[UsabilityTestResult]:
        """Execute tests in parallel"""
        tasks = []
        for test_id, user_profile in test_combinations:
            task = self.execute_test_case(test_id, user_profile)
            tasks.append(task)
        return await asyncio.gather(*tasks, return_exceptions=False)
    
    async def _execute_tests_sequential(self, test_combinations: List[Tuple]) -> List[UsabilityTestResult]:
        """Execute tests sequentially"""
        results = []
        for test_id, user_profile in test_combinations:
            result = await self.execute_test_case(test_id, user_profile)
            results.append(result)
        return results
    
    def _generate_usability_summary(self, results: List[UsabilityTestResult]) -> Dict[str, Any]:
        """Generate summary of usability test results"""
        if not results:
            return {}
        
        # Group results by usability type
        usability_types = {}
        for result in results:
            usability_type = result.test_case.usability_type.value
            if usability_type not in usability_types:
                usability_types[usability_type] = {
                    'total': 0,
                    'passed': 0,
                    'failed': 0,
                    'partial': 0,
                    'errors': 0
                }
            usability_types[usability_type]['total'] += 1
            if result.status == UsabilityTestStatus.PASSED:
                usability_types[usability_type]['passed'] += 1
            elif result.status == UsabilityTestStatus.FAILED:
                usability_types[usability_type]['failed'] += 1
            elif result.status == UsabilityTestStatus.PARTIAL_SUCCESS:
                usability_types[usability_type]['partial'] += 1
            elif result.status == UsabilityTestStatus.ERROR:
                usability_types[usability_type]['errors'] += 1
        
        return usability_types
    
    def _generate_user_profile_summary(self, results: List[UsabilityTestResult]) -> Dict[str, Any]:
        """Generate user profile summary"""
        profile_stats = {}
        for result in results:
            profile = result.user_profile
            if profile not in profile_stats:
                profile_stats[profile] = {
                    'total': 0,
                    'passed': 0,
                    'failed': 0,
                    'partial': 0,
                    'avg_satisfaction': 0.0,
                    'avg_cognitive_load': 0.0
                }
            profile_stats[profile]['total'] += 1
            if result.status == UsabilityTestStatus.PASSED:
                profile_stats[profile]['passed'] += 1
            elif result.status == UsabilityTestStatus.FAILED:
                profile_stats[profile]['failed'] += 1
            elif result.status == UsabilityTestStatus.PARTIAL_SUCCESS:
                profile_stats[profile]['partial'] += 1
            profile_stats[profile]['avg_satisfaction'] += result.user_satisfaction_score
            profile_stats[profile]['avg_cognitive_load'] += result.cognitive_load_score
        
        # Calculate averages
        for profile in profile_stats:
            if profile_stats[profile]['total'] > 0:
                profile_stats[profile]['avg_satisfaction'] /= profile_stats[profile]['total']
                profile_stats[profile]['avg_cognitive_load'] /= profile_stats[profile]['total']
        
        return profile_stats
    
    def _generate_accessibility_summary(self, results: List[UsabilityTestResult]) -> Dict[str, Any]:
        """Generate accessibility summary"""
        accessibility_stats = {}
        for result in results:
            if result.accessibility_metrics:
                for standard, metrics in result.accessibility_metrics.items():
                    if standard not in accessibility_stats:
                        accessibility_stats[standard] = {
                            'total': 0,
                            'compliant': 0,
                            'issues': 0
                        }
                    accessibility_stats[standard]['total'] += 1
                    if metrics.get('compliant', False):
                        accessibility_stats[standard]['compliant'] += 1
                    accessibility_stats[standard]['issues'] += metrics.get('issues_count', 0)
        
        return accessibility_stats
    
    def _generate_performance_summary(self, results: List[UsabilityTestResult]) -> Dict[str, Any]:
        """Generate performance summary"""
        if not results:
            return {}
        
        completion_times = [r.task_completion_time for r in results if r.task_completion_time > 0]
        satisfaction_scores = [r.user_satisfaction_score for r in results]
        cognitive_load_scores = [r.cognitive_load_score for r in results]
        
        within_expected_time = sum(1 for r in results 
                                 if r.task_completion_time <= r.test_case.expected_completion_time)
        
        return {
            'average_completion_time': sum(completion_times) / len(completion_times) if completion_times else 0,
            'min_completion_time': min(completion_times) if completion_times else 0,
            'max_completion_time': max(completion_times) if completion_times else 0,
            'average_satisfaction_score': sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0,
            'average_cognitive_load_score': sum(cognitive_load_scores) / len(cognitive_load_scores) if cognitive_load_scores else 0,
            'completion_within_expected_time': within_expected_time,
            'success_rate': (within_expected_time / len(results) * 100) if results else 0
        }
    
    def _generate_recommendations(self, results: List[UsabilityTestResult]) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        failed_results = [r for r in results if r.status == UsabilityTestStatus.FAILED]
        partial_results = [r for r in results if r.status == UsabilityTestStatus.PARTIAL_SUCCESS]
        high_cognitive_load_results = [r for r in results if r.cognitive_load_score > 0.7]
        low_satisfaction_results = [r for r in results if r.user_satisfaction_score < 0.6]
        slow_completion_results = [r for r in results 
                                 if r.task_completion_time > r.test_case.expected_completion_time]
        
        if failed_results:
            recommendations.append(
                f"Address {len(failed_results)} failed usability tests to improve user experience"
            )
        
        if partial_results:
            recommendations.append(
                f"Improve {len(partial_results)} partially successful tests for better usability"
            )
        
        if high_cognitive_load_results:
            avg_load = sum(r.cognitive_load_score for r in high_cognitive_load_results) / len(high_cognitive_load_results)
            recommendations.append(
                f"Reduce cognitive load for {len(high_cognitive_load_results)} tests "
                f"(average load: {avg_load:.2f})"
            )
        
        if low_satisfaction_results:
            avg_satisfaction = sum(r.user_satisfaction_score for r in low_satisfaction_results) / len(low_satisfaction_results)
            recommendations.append(
                f"Improve user satisfaction for {len(low_satisfaction_results)} tests "
                f"(average satisfaction: {avg_satisfaction:.2f})"
            )
        
        if slow_completion_results:
            avg_slow_time = sum(r.task_completion_time for r in slow_completion_results) / len(slow_completion_results)
            recommendations.append(
                f"Optimize task completion time for {len(slow_completion_results)} slow tests "
                f"(average {avg_slow_time:.2f}s vs expected {slow_completion_results[0].test_case.expected_completion_time:.2f}s)"
            )
        
        # User profile specific issues
        profile_issues = {}
        for result in failed_results + partial_results:
            profile = result.user_profile
            if profile not in profile_issues:
                profile_issues[profile] = 0
            profile_issues[profile] += 1
        
        for profile, count in profile_issues.items():
            if count > (len(failed_results) + len(partial_results)) * 0.3:  # More than 30% of issues for one profile
                recommendations.append(
                    f"Significant usability issues found for {profile} profile ({count} issues) - "
                    f"investigate user-specific interface problems"
                )
        
        return recommendations
    
    def generate_comprehensive_report(self, suite_result: UsabilityTestSuiteResult) -> str:
        """
        Generate a comprehensive usability test report.
        
        Args:
            suite_result: The test suite result to generate report for
            
        Returns:
            Formatted test report string
        """
        report_lines = [
            "=" * 80,
            "USABILITY TEST SUITE REPORT",
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
            f"Partial Success: {suite_result.partial_success_tests}",
            f"Failed: {suite_result.failed_tests}",
            f"Errors: {suite_result.error_tests}",
            f"Skipped: {suite_result.skipped_tests}",
            f"Pass Rate: {suite_result.pass_rate:.1f}%",
            ""
        ]
        
        # Usability summary
        if suite_result.usability_summary:
            report_lines.extend([
                "USABILITY TYPE SUMMARY",
                "-" * 40
            ])
            for usability_type, stats in suite_result.usability_summary.items():
                success_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
                report_lines.append(
                    f"{usability_type.upper()}: {stats['passed']}/{stats['total']} "
                    f"({success_rate:.1f}% success)"
                )
            report_lines.append("")
        
        # User profile summary
        if suite_result.user_profile_summary:
            report_lines.extend([
                "USER PROFILE SUMMARY",
                "-" * 40
            ])
            for profile, stats in suite_result.user_profile_summary.items():
                success_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
                report_lines.append(
                    f"{profile.upper()}: {stats['passed']}/{stats['total']} "
                    f"({success_rate:.1f}% success) | "
                    f"Satisfaction: {stats['avg_satisfaction']:.2f} | "
                    f"Cognitive Load: {stats['avg_cognitive_load']:.2f}"
                )
            report_lines.append("")
        
        # Accessibility summary
        if suite_result.accessibility_summary:
            report_lines.extend([
                "ACCESSIBILITY COMPLIANCE SUMMARY",
                "-" * 40
            ])
            for standard, stats in suite_result.accessibility_summary.items():
                compliance_rate = (stats['compliant'] / stats['total'] * 100) if stats['total'] > 0 else 0
                report_lines.append(
                    f"{standard.upper()}: {stats['compliant']}/{stats['total']} "
                    f"({compliance_rate:.1f}% compliant) | "
                    f"Issues: {stats['issues']}"
                )
            report_lines.append("")
        
        # Performance summary
        if suite_result.performance_summary:
            perf = suite_result.performance_summary
            report_lines.extend([
                "PERFORMANCE SUMMARY",
                "-" * 40,
                f"Average Completion Time: {perf['average_completion_time']:.2f}s",
                f"Min/Max Completion Time: {perf['min_completion_time']:.2f}s / {perf['max_completion_time']:.2f}s",
                f"Average Satisfaction Score: {perf['average_satisfaction_score']:.2f}",
                f"Average Cognitive Load Score: {perf['average_cognitive_load_score']:.2f}",
                f"Completion Within Expected Time: {perf['completion_within_expected_time']}/{suite_result.total_tests}",
                f"Success Rate: {perf['success_rate']:.1f}%",
                ""
            ])
        
        # Failed tests details
        failed_tests = [r for r in suite_result.test_results if r.status == UsabilityTestStatus.FAILED]
        if failed_tests:
            report_lines.extend([
                "FAILED TESTS",
                "-" * 40
            ])
            for result in failed_tests[:10]:  # Limit to first 10 failures
                report_lines.extend([
                    f"Test: {result.test_case.test_name}",
                    f"  User Profile: {result.user_profile}",
                    f"  Usability Type: {result.test_case.usability_type.value}",
                    f"  Duration: {result.total_duration:.3f}s",
                    f"  Satisfaction Score: {result.user_satisfaction_score:.2f}",
                    f"  Cognitive Load: {result.cognitive_load_score:.2f}",
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
async def example_interface_test(user_profile: str):
    """Example interface usability test function"""
    # Simulate user interactions
    await asyncio.sleep(0.1)
    return {
        'interaction_count': 5,
        'error_count': 0,
        'usability_metrics': {
            'click_efficiency': 0.95,
            'navigation_time': 2.5
        }
    }


async def example_usability_validation(user_profile: str, test_result: Dict[str, Any]) -> Dict[str, Any]:
    """Example usability validation function"""
    # Simulate usability validation
    await asyncio.sleep(0.05)
    return {
        'success_rate': 1.0,
        'interaction_count': test_result.get('interaction_count', 0),
        'error_count': test_result.get('error_count', 0),
        'usability_metrics': test_result.get('usability_metrics', {}),
        'user_satisfaction_score': 0.85,
        'cognitive_load_score': 0.25,
        'workflow_efficiency_score': 0.92
    }


# Example of how to use the usability test runner
if __name__ == "__main__":
    # Example usage
    async def main():
        config = {
            'default_timeout': 60,
            'default_expected_completion_time': 30.0,
            'default_expected_success_rate': 0.95,
            'user_profiles': ['beginner_trader', 'expert_trader', 'risk_manager']
        }
        
        runner = UsabilityTestRunner(config)
        
        # Register test cases
        runner.register_interface_usability_test(
            "Dashboard Navigation Test",
            [InteractionType.CLICK, InteractionType.NAVIGATE],
            example_interface_test,
            example_usability_validation,
            expected_completion_time=20.0,
            user_profiles=['beginner_trader', 'expert_trader']
        )
        
        runner.register_user_experience_test(
            "Strategy Creation Workflow",
            [InteractionType.CLICK, InteractionType.TYPE, InteractionType.SELECT],
            example_interface_test,
            example_usability_validation,
            expected_success_rate=0.90,
            user_profiles=['beginner_trader', 'expert_trader']
        )
        
        # Execute test suite
        suite_result = await runner.execute_test_suite(
            "Example Usability Suite",
            user_profiles=['beginner_trader', 'expert_trader']
        )
        
        # Generate report
        report = runner.generate_comprehensive_report(suite_result)
        print(report)
    
    # Run the example
    asyncio.run(main())