import unittest
import os
import sys

# This script is designed for the CI/CD pipeline to run all integration tests
# and provide a consolidated report of the results. It discovers and runs
# all test cases in the 'tests/integration' directory.

def run_all_integration_tests():
    """
    Discover and run all integration tests.
    """
    # Discover all tests in the 'integration' subdirectory
    loader = unittest.TestLoader()
    # The start_dir should be the directory containing this script.
    start_dir = os.path.dirname(os.path.abspath(__file__))
    suite = loader.discover(start_dir=start_dir, pattern='test_*.py')
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with a non-zero status code if tests failed
    if not result.wasSuccessful():
        sys.exit(1)

if __name__ == '__main__':
    print("Running all integration tests...")
    run_all_integration_tests()
    print("All integration tests passed successfully.")