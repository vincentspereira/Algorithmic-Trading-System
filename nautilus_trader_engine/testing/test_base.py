"""Base Test Classes for the Comprehensive Testing Framework

Provides base classes and utilities for all types of testing in the system.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import unittest
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Standard test result structure"""
    test_name: str
    passed: bool
    execution_time: float
    error_message: str = ""
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}

class BaseTestCase(unittest.TestCase):
    """Base test case class with common functionality"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.start_time = datetime.now()
        logger.info(f"Starting test: {self._testMethodName}")
        
    def tearDown(self):
        """Tear down test fixtures after each test method."""
        end_time = datetime.now()
        execution_time = (end_time - self.start_time).total_seconds()
        logger.info(f"Completed test: {self._testMethodName} in {execution_time:.4f}s")
        
    def assertAlmostEqualRelative(self, first, second, tolerance=0.01, msg=None):
        """Assert that two values are almost equal within a relative tolerance."""
        if first == 0 and second == 0:
            return
            
        if first == 0 or second == 0:
            self.assertEqual(first, second, msg)
            return
            
        relative_diff = abs((first - second) / first)
        if relative_diff > tolerance:
            raise self.failureException(
                msg or f'{first} != {second} within {tolerance*100}% tolerance'
            )
            
    def assertValidPrice(self, price, msg=None):
        """Assert that a price is valid (positive and reasonable)."""
        self.assertIsInstance(price, (int, float), msg)
        self.assertGreater(price, 0, msg)
        self.assertLess(price, 1000000, msg or "Price seems unreasonably high")
        
    def assertValidVolume(self, volume, msg=None):
        """Assert that a volume is valid (non-negative)."""
        self.assertIsInstance(volume, (int, float), msg)
        self.assertGreaterEqual(volume, 0, msg)
        
    def assertValidIndicatorResult(self, result, msg=None):
        """Assert that an indicator result is valid."""
        self.assertIsNotNone(result, msg)
        self.assertTrue(hasattr(result, 'value'), msg)
        self.assertTrue(hasattr(result, 'signal'), msg)
        
    def assertValidDataFrame(self, df, msg=None):
        """Assert that a DataFrame is valid."""
        self.assertIsNotNone(df, msg)
        self.assertFalse(df.empty, msg)

class TestSuiteManager:
    """Manager for organizing and running test suites"""
    
    def __init__(self):
        self.test_suites = {}
        
    def add_suite(self, suite_name: str, test_suite):
        """Add a test suite to the manager."""
        self.test_suites[suite_name] = test_suite
        
    def get_suite(self, suite_name: str):
        """Get a test suite by name."""
        return self.test_suites.get(suite_name)
        
    def list_suites(self):
        """List all available test suites."""
        return list(self.test_suites.keys())
        
    def run_suite(self, suite_name: str):
        """Run a specific test suite."""
        if suite_name not in self.test_suites:
            raise ValueError(f"Test suite '{suite_name}' not found")
            
        suite = self.test_suites[suite_name]
        runner = unittest.TextTestRunner(verbosity=2)
        return runner.run(suite)
        
    def run_all_suites(self):
        """Run all test suites."""
        results = {}
        for suite_name, suite in self.test_suites.items():
            logger.info(f"Running test suite: {suite_name}")
            runner = unittest.TextTestRunner(verbosity=2)
            results[suite_name] = runner.run(suite)
        return results