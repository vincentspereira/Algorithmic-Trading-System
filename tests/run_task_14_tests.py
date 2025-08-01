#!/usr/bin/env python3
"""
Task 14 Test Runner
Comprehensive test execution for all Task 14 Documentation and Training components.
"""

import sys
import subprocess
import time
from pathlib import Path
import json
import xml.etree.ElementTree as ET

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class Task14TestRunner:
    """Test runner for Task 14 components"""
    
    def __init__(self):
        self.project_root = project_root
        self.test_results = {}
        self.start_time = time.time()
    
    def run_test_suite(self, test_file, suite_name):
        """Run a specific test suite and capture results"""
        print(f"\n{'='*60}")
        print(f"Running {suite_name}")
        print(f"{'='*60}")
        
        test_path = self.project_root / "tests" / test_file
        results_file = self.project_root / f"test_results_{suite_name.lower().replace(' ', '_')}.xml"
        
        cmd = [
            sys.executable, "-m", "pytest",
            str(test_path),
            "-v",
            "--tb=short",
            "--durations=10",
            f"--junitxml={results_file}"
        ]
        
        start_time = time.time()
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            duration = time.time() - start_time
            
            # Parse results
            passed, failed, errors = self.parse_junit_results(results_file)
            
            self.test_results[suite_name] = {
                'return_code': result.returncode,
                'duration': duration,
                'passed': passed,
                'failed': failed,
                'errors': errors,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            # Print summary
            if result.returncode == 0:
                print(f"✅ {suite_name}: PASSED ({passed} tests, {duration:.2f}s)")
            else:
                print(f"❌ {suite_name}: FAILED ({failed} failed, {errors} errors, {duration:.2f}s)")
                if result.stderr:
                    print(f"Errors: {result.stderr[:500]}...")
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            print(f"⏰ {suite_name}: TIMEOUT (exceeded 5 minutes)")
            self.test_results[suite_name] = {
                'return_code': -1,
                'duration': 300,
                'passed': 0,
                'failed': 0,
                'errors': 1,
                'stdout': '',
                'stderr': 'Test suite timed out'
            }
            return False
        
        except Exception as e:
            print(f"💥 {suite_name}: ERROR ({str(e)})")
            self.test_results[suite_name] = {
                'return_code': -1,
                'duration': time.time() - start_time,
                'passed': 0,
                'failed': 0,
                'errors': 1,
                'stdout': '',
                'stderr': str(e)
            }
            return False
    
    def parse_junit_results(self, results_file):
        """Parse JUnit XML results"""
        try:
            if not results_file.exists():
                return 0, 0, 1
            
            tree = ET.parse(results_file)
            root = tree.getroot()
            
            # Get test counts from testsuite element
            testsuite = root.find('testsuite') or root
            
            tests = int(testsuite.get('tests', 0))
            failures = int(testsuite.get('failures', 0))
            errors = int(testsuite.get('errors', 0))
            
            passed = tests - failures - errors
            
            return passed, failures, errors
            
        except Exception as e:
            print(f"Warning: Could not parse results file {results_file}: {e}")
            return 0, 0, 1
    
    def run_syntax_checks(self):
        """Run syntax checks on all code files"""
        print(f"\n{'='*60}")
        print("Running Syntax Checks")
        print(f"{'='*60}")
        
        files_to_check = [
            "docs/api/api_testing_suite.py",
            "docs/api/examples/javascript_examples.js",
            "docs/api/examples/TradingSystemClient.java"
        ]
        
        syntax_results = {}
        
        for file_path in files_to_check:
            full_path = self.project_root / file_path
            
            if not full_path.exists():
                print(f"❌ {file_path}: FILE NOT FOUND")
                syntax_results[file_path] = False
                continue
            
            # Check Python files
            if file_path.endswith('.py'):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                    compile(code, str(full_path), 'exec')
                    print(f"✅ {file_path}: Python syntax OK")
                    syntax_results[file_path] = True
                except SyntaxError as e:
                    print(f"❌ {file_path}: Python syntax error - {e}")
                    syntax_results[file_path] = False
            
            # Check JavaScript files
            elif file_path.endswith('.js'):
                try:
                    result = subprocess.run(
                        ["node", "--check", str(full_path)],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        print(f"✅ {file_path}: JavaScript syntax OK")
                        syntax_results[file_path] = True
                    else:
                        print(f"❌ {file_path}: JavaScript syntax error - {result.stderr}")
                        syntax_results[file_path] = False
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    print(f"⚠️  {file_path}: Node.js not available, skipping syntax check")
                    syntax_results[file_path] = True  # Don't fail if Node.js not available
            
            # Check Java files (basic check)
            elif file_path.endswith('.java'):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Basic syntax checks
                    if content.count('{') != content.count('}'):
                        print(f"❌ {file_path}: Mismatched braces")
                        syntax_results[file_path] = False
                    elif content.count('(') != content.count(')'):
                        print(f"❌ {file_path}: Mismatched parentheses")
                        syntax_results[file_path] = False
                    else:
                        print(f"✅ {file_path}: Java basic syntax OK")
                        syntax_results[file_path] = True
                        
                except Exception as e:
                    print(f"❌ {file_path}: Error checking Java file - {e}")
                    syntax_results[file_path] = False
        
        return all(syntax_results.values())
    
    def run_file_existence_checks(self):
        """Check that all required files exist"""
        print(f"\n{'='*60}")
        print("Running File Existence Checks")
        print(f"{'='*60}")
        
        required_files = [
            "docs/interactive_api_documentation.md",
            "docs/api/openapi.yaml",
            "docs/api/api_testing_suite.py",
            "docs/api/examples/javascript_examples.js",
            "docs/api/examples/TradingSystemClient.java",
            "docs/training/video_tutorial_scripts.md",
            "docs/training/hands_on_workshops.md",
            "docs/training/certification_program.md"
        ]
        
        all_exist = True
        
        for file_path in required_files:
            full_path = self.project_root / file_path
            
            if full_path.exists():
                size = full_path.stat().st_size
                if size > 0:
                    print(f"✅ {file_path}: EXISTS ({size:,} bytes)")
                else:
                    print(f"❌ {file_path}: EMPTY FILE")
                    all_exist = False
            else:
                print(f"❌ {file_path}: NOT FOUND")
                all_exist = False
        
        return all_exist
    
    def run_content_validation(self):
        """Run basic content validation"""
        print(f"\n{'='*60}")
        print("Running Content Validation")
        print(f"{'='*60}")
        
        validations = []
        
        # Validate OpenAPI YAML
        try:
            import yaml
            openapi_path = self.project_root / "docs" / "api" / "openapi.yaml"
            with open(openapi_path, 'r', encoding='utf-8') as f:
                yaml.safe_load(f)
            print("✅ OpenAPI YAML: Valid YAML syntax")
            validations.append(True)
        except Exception as e:
            print(f"❌ OpenAPI YAML: Invalid - {e}")
            validations.append(False)
        
        # Validate markdown structure
        markdown_files = [
            "docs/interactive_api_documentation.md",
            "docs/training/video_tutorial_scripts.md",
            "docs/training/hands_on_workshops.md",
            "docs/training/certification_program.md"
        ]
        
        for file_path in markdown_files:
            full_path = self.project_root / file_path
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Basic markdown validation
                if content.startswith('#'):
                    print(f"✅ {file_path}: Valid markdown structure")
                    validations.append(True)
                else:
                    print(f"❌ {file_path}: Should start with heading")
                    validations.append(False)
                    
            except Exception as e:
                print(f"❌ {file_path}: Error reading file - {e}")
                validations.append(False)
        
        return all(validations)
    
    def generate_summary_report(self):
        """Generate comprehensive summary report"""
        total_duration = time.time() - self.start_time
        
        print(f"\n{'='*80}")
        print("TASK 14 COMPREHENSIVE TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Total execution time: {total_duration:.2f} seconds")
        print()
        
        # Calculate totals
        total_passed = sum(result['passed'] for result in self.test_results.values())
        total_failed = sum(result['failed'] for result in self.test_results.values())
        total_errors = sum(result['errors'] for result in self.test_results.values())
        total_tests = total_passed + total_failed + total_errors
        
        # Print individual suite results
        print("Test Suite Results:")
        print("-" * 50)
        
        all_passed = True
        for suite_name, result in self.test_results.items():
            status = "✅ PASS" if result['return_code'] == 0 else "❌ FAIL"
            print(f"{suite_name:<35} {status} ({result['passed']}P/{result['failed']}F/{result['errors']}E)")
            
            if result['return_code'] != 0:
                all_passed = False
        
        print()
        print("Overall Statistics:")
        print("-" * 50)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {total_passed}")
        print(f"Failed: {total_failed}")
        print(f"Errors: {total_errors}")
        
        if total_tests > 0:
            success_rate = (total_passed / total_tests) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        
        print()
        
        if all_passed and total_tests > 0:
            print("🎉 ALL TASK 14 TESTS PASSED!")
            print()
            print("Task 14 Documentation and Training is ready for production:")
            print("- Interactive API Documentation: Complete and validated")
            print("- API Testing Suite: Functional and comprehensive")
            print("- Code Examples: Syntactically correct and complete")
            print("- Training Materials: Comprehensive and well-structured")
            print("- Certification Program: Professional and detailed")
            return True
        else:
            print("⚠️  SOME TESTS FAILED OR NO TESTS RUN")
            print()
            print("Please review the detailed results above and fix any issues.")
            return False
    
    def save_results_json(self):
        """Save test results to JSON file"""
        results_file = self.project_root / "task_14_test_results.json"
        
        summary = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_duration': time.time() - self.start_time,
            'test_suites': self.test_results,
            'summary': {
                'total_passed': sum(result['passed'] for result in self.test_results.values()),
                'total_failed': sum(result['failed'] for result in self.test_results.values()),
                'total_errors': sum(result['errors'] for result in self.test_results.values()),
                'all_passed': all(result['return_code'] == 0 for result in self.test_results.values())
            }
        }
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        print(f"Detailed results saved to: {results_file}")
    
    def run_all_tests(self):
        """Run all Task 14 tests"""
        print("🚀 Starting Task 14 Comprehensive Test Suite")
        print(f"Project root: {self.project_root}")
        
        # Step 1: File existence checks
        files_ok = self.run_file_existence_checks()
        
        # Step 2: Syntax checks
        syntax_ok = self.run_syntax_checks()
        
        # Step 3: Content validation
        content_ok = self.run_content_validation()
        
        # Step 4: Run comprehensive test suites
        test_suites = [
            ("test_task_14_documentation_training.py", "Documentation and Training Tests"),
            ("test_api_documentation_validation.py", "API Documentation Validation")
        ]
        
        suite_results = []
        for test_file, suite_name in test_suites:
            result = self.run_test_suite(test_file, suite_name)
            suite_results.append(result)
        
        # Step 5: Generate summary
        overall_success = self.generate_summary_report()
        
        # Step 6: Save results
        self.save_results_json()
        
        # Return overall success
        return overall_success and files_ok and syntax_ok and content_ok and all(suite_results)


def main():
    """Main entry point"""
    runner = Task14TestRunner()
    success = runner.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()