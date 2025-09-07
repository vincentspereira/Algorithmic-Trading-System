#!/usr/bin/env python3
"""
Demonstration script for UnitTestRunner

This script demonstrates the key functionality of the UnitTestRunner class,
showing how it executes tests with coverage tracking and generates detailed reports.
"""

import sys
import time
from pathlib import Path

# Add the framework directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from unit_test_runner import UnitTestRunner, TestStatus, CoverageStatus


def main():
    """Demonstrate UnitTestRunner functionality"""
    print("=" * 80)
    print("UNIT TEST RUNNER DEMONSTRATION")
    print("=" * 80)
    
    # Initialize UnitTestRunner
    print("\n1. Initializing UnitTestRunner...")
    runner = UnitTestRunner()
    print(f"   Project Root: {runner.project_root}")
    print(f"   Source Directories: {runner.src_directories}")
    print(f"   Coverage Threshold: {runner.coverage_threshold}%")
    print(f"   Coverage Instance Available: {runner.coverage_instance is not None}")
    
    # Discover source directories
    print("\n2. Source Directory Discovery...")
    discovered_dirs = runner._discover_source_directories()
    print(f"   Discovered {len(discovered_dirs)} source directories:")
    for i, dir_path in enumerate(discovered_dirs[:5], 1):
        print(f"     {i}. {Path(dir_path).name}")
    if len(discovered_dirs) > 5:
        print(f"     ... and {len(discovered_dirs) - 5} more")
    
    # Discover tests
    print("\n3. Test Discovery...")
    discovered_tests = runner.discover_tests()
    print(f"   Discovered {len(discovered_tests)} test files:")
    for i, test_file in enumerate(discovered_tests[:10], 1):
        print(f"     {i}. {Path(test_file).name}")
    if len(discovered_tests) > 10:
        print(f"     ... and {len(discovered_tests) - 10} more")
    
    if not discovered_tests:
        print("   ⚠️ No test files found. Creating a sample test for demonstration...")
        
        # Create a simple test for demonstration
        demo_test_dir = runner.project_root / "demo_tests"
        demo_test_dir.mkdir(exist_ok=True)
        
        demo_test_file = demo_test_dir / "test_demo.py"
        demo_test_content = '''
def test_simple_addition():
    """Test simple addition"""
    assert 2 + 2 == 4

def test_simple_subtraction():
    """Test simple subtraction"""
    assert 5 - 3 == 2

def test_string_operations():
    """Test string operations"""
    assert "hello" + " world" == "hello world"
    assert "test".upper() == "TEST"

def test_list_operations():
    """Test list operations"""
    test_list = [1, 2, 3]
    test_list.append(4)
    assert len(test_list) == 4
    assert test_list[-1] == 4
'''
        demo_test_file.write_text(demo_test_content.strip())
        print(f"   Created demo test file: {demo_test_file}")
        
        # Re-discover tests
        discovered_tests = runner.discover_tests(test_directories=["demo_tests"])
        print(f"   Re-discovered {len(discovered_tests)} test files")
    
    # Ask user about running tests
    if discovered_tests:
        print("\n4. Test Execution Options...")
        print("   The following test execution options are available:")
        print("     - Run all tests with coverage")
        print("     - Run specific test patterns")
        print("     - Generate coverage reports")
        
        run_tests = input("   Run tests with coverage measurement? (y/N): ").lower().strip()
        
        if run_tests == 'y':
            print("\n5. Executing Tests with Coverage...")
            print("   This may take a moment...")
            
            try:
                # Run tests with coverage
                result = runner.run_tests_with_coverage(test_paths=discovered_tests[:3])  # Limit to first 3 for demo
                
                print(f"   Test execution completed!")
                print(f"   Exit Code: {result.exit_code}")
                print(f"   Total Duration: {result.total_duration:.2f} seconds")
                
                # Display test results summary
                print("\n6. Test Results Summary...")
                print(f"   Total Tests: {result.total_tests}")
                print(f"   Passed: {result.passed_tests} ({result.passed_tests/result.total_tests*100:.1f}%)" if result.total_tests > 0 else "   Passed: 0")
                print(f"   Failed: {result.failed_tests}")
                print(f"   Skipped: {result.skipped_tests}")
                print(f"   Errors: {result.error_tests}")
                
                # Display coverage summary
                print("\n7. Coverage Summary...")
                print(f"   Overall Coverage: {result.overall_coverage:.2f}%")
                print(f"   Coverage Status: {result.coverage_status.value.upper()}")
                print(f"   Files Analyzed: {len(result.coverage_info)}")
                
                # Show coverage by file
                if result.coverage_info:
                    print("   Coverage by File:")
                    for file_path, coverage_info in list(result.coverage_info.items())[:5]:
                        file_name = Path(file_path).name
                        status_icon = "✅" if coverage_info.coverage_percentage >= 90 else "⚠️" if coverage_info.coverage_percentage >= 75 else "❌"
                        print(f"     {status_icon} {file_name}: {coverage_info.coverage_percentage:.1f}% ({coverage_info.covered_lines}/{coverage_info.total_lines} lines)")
                
                # Show failed tests if any
                failed_tests = [t for t in result.test_results if t.status == TestStatus.FAILED]
                if failed_tests:
                    print("\n   Failed Tests:")
                    for test in failed_tests[:3]:
                        print(f"     ❌ {test.name}")
                        if test.failure_message:
                            print(f"        {test.failure_message[:100]}...")
                
                # Show warnings and errors
                if result.warnings:
                    print("\n   Warnings:")
                    for warning in result.warnings[:3]:
                        print(f"     ⚠️ {warning}")
                
                if result.errors:
                    print("\n   Errors:")
                    for error in result.errors[:3]:
                        print(f"     🚨 {error}")
                
                # Coverage validation
                print("\n8. Coverage Validation...")
                if runner.coverage_instance:
                    success, issues = runner.validate_100_percent_coverage()
                    
                    if success:
                        print("   ✅ 100% coverage requirement validated successfully!")
                    else:
                        print(f"   ❌ Coverage validation failed with {len(issues)} issues:")
                        for issue in issues[:3]:
                            print(f"     - {issue}")
                        if len(issues) > 3:
                            print(f"     ... and {len(issues) - 3} more issues")
                else:
                    print("   ⚠️ Coverage measurement not available")
                
                # Generate detailed report
                print("\n9. Generating Test Report...")
                report = runner.generate_test_report(result)
                print("   Test report generated successfully!")
                print(f"   Report length: {len(report)} characters")
                
                # Show report summary
                report_lines = report.split('\n')
                summary_start = next((i for i, line in enumerate(report_lines) if "TEST RESULTS SUMMARY:" in line), 0)
                summary_end = min(summary_start + 10, len(report_lines))
                
                if summary_start > 0:
                    print("   Report Summary:")
                    for line in report_lines[summary_start:summary_end]:
                        if line.strip():
                            print(f"   {line}")
                
                # Ask about saving report
                save_report = input("\n   Save full test report to file? (y/N): ").lower().strip()
                if save_report == 'y':
                    report_file = Path("unit_test_report.txt")
                    report_file.write_text(report)
                    print(f"   Report saved to: {report_file.absolute()}")
                
                # Demonstrate specific test execution
                if result.total_tests > 1:
                    print("\n10. Specific Test Execution Demo...")
                    specific_patterns = ["test_simple", "test_string"]
                    print(f"   Running tests matching patterns: {specific_patterns}")
                    
                    specific_result = runner.run_specific_tests(specific_patterns)
                    print(f"   Specific tests executed: {specific_result.total_tests}")
                    print(f"   Passed: {specific_result.passed_tests}")
                
                # Coverage threshold demonstration
                print("\n11. Coverage Threshold Configuration...")
                original_threshold = runner.coverage_threshold
                print(f"   Current threshold: {original_threshold}%")
                
                # Try different thresholds
                test_thresholds = [95.0, 85.0, 75.0]
                for threshold in test_thresholds:
                    runner.set_coverage_threshold(threshold)
                    status = "✅ PASS" if result.overall_coverage >= threshold else "❌ FAIL"
                    print(f"   Threshold {threshold}%: {status} (Coverage: {result.overall_coverage:.1f}%)")
                
                # Restore original threshold
                runner.set_coverage_threshold(original_threshold)
                
            except Exception as e:
                print(f"   ❌ Test execution failed: {str(e)}")
                print("   This might be due to missing dependencies or test configuration issues")
        
        else:
            print("   Skipping test execution")
    
    else:
        print("\n4. No tests available for execution")
        print("   In a real project, you would have test files in directories like:")
        print("     - tests/")
        print("     - test/")
        print("     - Files matching test_*.py or *_test.py patterns")
    
    # Demonstrate coverage analysis features
    print("\n" + "=" * 80)
    print("COVERAGE ANALYSIS FEATURES")
    print("=" * 80)
    
    print("\nCoverage Status Levels:")
    coverage_examples = [
        (98.0, "Excellent coverage"),
        (90.0, "Good coverage"),
        (80.0, "Acceptable coverage"),
        (65.0, "Poor coverage"),
        (45.0, "Critical coverage")
    ]
    
    for percentage, description in coverage_examples:
        status = runner._determine_coverage_status(percentage)
        status_icon = {
            CoverageStatus.EXCELLENT: "🟢",
            CoverageStatus.GOOD: "🔵", 
            CoverageStatus.ACCEPTABLE: "🟡",
            CoverageStatus.POOR: "🟠",
            CoverageStatus.CRITICAL: "🔴"
        }.get(status, "⚪")
        
        print(f"  {status_icon} {percentage:5.1f}% - {status.value.upper()} ({description})")
    
    # Show configuration options
    print("\nConfiguration Options:")
    print(f"  Coverage Threshold: {runner.coverage_threshold}%")
    print(f"  Min Acceptable Coverage: {runner.min_acceptable_coverage}%")
    print(f"  Pytest Timeout: {runner.pytest_timeout} seconds")
    print(f"  Max Test Duration: {runner.max_test_duration} seconds")
    
    print("\nTest Discovery Patterns:")
    for pattern in runner.test_patterns:
        print(f"  - {pattern}")
    
    print("\nCoverage Exclusions:")
    for exclusion in runner.coverage_config['exclude_lines'][:5]:
        print(f"  - {exclusion}")
    
    # Cleanup demonstration
    print("\n" + "=" * 80)
    print("CLEANUP AND MAINTENANCE")
    print("=" * 80)
    
    print("\nTest Artifacts Cleanup...")
    print("   The following artifacts can be cleaned up:")
    artifacts = ['test-results.xml', 'test-report.json', 'coverage.xml', 'coverage.json', '.coverage', 'htmlcov/']
    for artifact in artifacts:
        print(f"     - {artifact}")
    
    cleanup = input("   Clean up test artifacts? (y/N): ").lower().strip()
    if cleanup == 'y':
        runner.cleanup_test_artifacts()
        print("   ✅ Test artifacts cleaned up")
    
    # Final summary
    print("\n" + "=" * 80)
    print("DEMONSTRATION SUMMARY")
    print("=" * 80)
    
    print(f"Project Root: {runner.project_root}")
    print(f"Source Directories: {len(runner.src_directories)} discovered")
    print(f"Test Files: {len(discovered_tests)} discovered")
    print(f"Coverage Threshold: {runner.coverage_threshold}%")
    print(f"Coverage Available: {'✅ Yes' if runner.coverage_instance else '❌ No'}")
    
    print("\nUnitTestRunner demonstration completed!")
    print("\nKey Features Demonstrated:")
    print("  ✅ Test discovery and execution")
    print("  ✅ Coverage measurement and tracking")
    print("  ✅ 100% coverage validation")
    print("  ✅ Detailed test reporting")
    print("  ✅ Line-by-line coverage analysis")
    print("  ✅ Configurable coverage thresholds")
    print("  ✅ Test artifact management")
    print("  ✅ Specific test pattern execution")


if __name__ == "__main__":
    main()