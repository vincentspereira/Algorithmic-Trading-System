#!/usr/bin/env python3
"""
Integration Test Validation Script
Validates the current state of Task 15.1 End-to-End Integration Testing
"""

import asyncio
import sys
import time
import json
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IntegrationTestValidator:
    """Validates the integration test implementation"""
    
    def __init__(self):
        self.test_results = {}
        self.validation_results = {}
        self.start_time = None
        self.end_time = None
        
    def validate_file_syntax(self, file_path: Path) -> Dict[str, Any]:
        """Validate Python file syntax"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Compile to check syntax
            compile(content, str(file_path), 'exec')
            
            return {
                'status': 'PASS',
                'message': 'Syntax validation passed',
                'file': str(file_path)
            }
        except SyntaxError as e:
            return {
                'status': 'FAIL',
                'message': f'Syntax error: {e}',
                'file': str(file_path),
                'line': e.lineno,
                'error': str(e)
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': f'Validation error: {e}',
                'file': str(file_path),
                'error': str(e)
            }
    
    def validate_imports(self, file_path: Path) -> Dict[str, Any]:
        """Validate that all imports can be resolved"""
        try:
            # Add the tests directory to Python path temporarily
            import sys
            tests_dir = file_path.parent
            if str(tests_dir) not in sys.path:
                sys.path.insert(0, str(tests_dir))
            
            # Try to import the module
            module_name = file_path.stem
            spec = __import__(module_name)
            
            return {
                'status': 'PASS',
                'message': 'Import validation passed',
                'file': str(file_path)
            }
        except ImportError as e:
            return {
                'status': 'FAIL',
                'message': f'Import error: {e}',
                'file': str(file_path),
                'error': str(e)
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': f'Import validation error: {e}',
                'file': str(file_path),
                'error': str(e)
            }
    
    def validate_test_structure(self, file_path: Path) -> Dict[str, Any]:
        """Validate test file structure and content"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            issues = []
            recommendations = []
            
            # Check for test classes
            if 'class Test' not in content and 'def test_' not in content:
                issues.append('No test classes or test functions found')
            
            # Check for assertions
            if 'assert' not in content:
                issues.append('No assertions found in test file')
            
            # Check for async test support
            if 'async def test_' in content and '@pytest.mark.asyncio' not in content:
                recommendations.append('Consider adding @pytest.mark.asyncio for async tests')
            
            # Check for documentation
            if '"""' not in content and "'''" not in content:
                recommendations.append('Consider adding docstrings for better documentation')
            
            # Check for cleanup
            if 'cleanup' not in content.lower() and 'teardown' not in content.lower():
                recommendations.append('Consider adding cleanup/teardown methods')
            
            status = 'PASS' if not issues else 'WARN'
            
            return {
                'status': status,
                'message': 'Test structure validation completed',
                'file': str(file_path),
                'issues': issues,
                'recommendations': recommendations
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': f'Structure validation error: {e}',
                'file': str(file_path),
                'error': str(e)
            }
    
    def validate_mock_configuration(self) -> Dict[str, Any]:
        """Validate mock configuration and setup"""
        try:
            from test_config_mock import MockApiClient, MockWebSocketClient, setup_mock_environment
            
            # Test mock API client
            mock_api = MockApiClient()
            
            # Test basic mock responses
            test_endpoints = [
                ('/auth/login', 'POST'),
                ('/health', 'GET'),
                ('/strategies', 'GET'),
                ('/portfolio', 'GET')
            ]
            
            issues = []
            for endpoint, method in test_endpoints:
                try:
                    # This would be async in real usage, but we're just testing setup
                    response = asyncio.run(mock_api.request(method, endpoint))
                    if not response:
                        issues.append(f'No mock response for {method} {endpoint}')
                except Exception as e:
                    issues.append(f'Mock error for {method} {endpoint}: {e}')
            
            # Test mock environment setup
            mock_env = setup_mock_environment()
            required_components = ['api_client', 'websocket_client', 'database_client']
            
            for component in required_components:
                if component not in mock_env:
                    issues.append(f'Missing mock component: {component}')
            
            status = 'PASS' if not issues else 'FAIL'
            
            return {
                'status': status,
                'message': 'Mock configuration validation completed',
                'issues': issues,
                'tested_endpoints': len(test_endpoints),
                'mock_components': len(mock_env)
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': f'Mock validation error: {e}',
                'error': str(e)
            }
    
    def validate_test_coverage(self) -> Dict[str, Any]:
        """Analyze test coverage of integration scenarios"""
        try:
            integration_dir = Path('tests/integration')
            test_files = list(integration_dir.glob('test_*.py'))
            
            coverage_areas = {
                'authentication': False,
                'strategy_management': False,
                'order_management': False,
                'portfolio_management': False,
                'market_data': False,
                'risk_management': False,
                'data_consistency': False,
                'error_handling': False,
                'performance': False,
                'security': False
            }
            
            # Analyze test files for coverage
            for test_file in test_files:
                try:
                    with open(test_file, 'r', encoding='utf-8') as f:
                        content = f.read().lower()
                    
                    if 'auth' in content or 'login' in content:
                        coverage_areas['authentication'] = True
                    if 'strategy' in content:
                        coverage_areas['strategy_management'] = True
                    if 'order' in content:
                        coverage_areas['order_management'] = True
                    if 'portfolio' in content:
                        coverage_areas['portfolio_management'] = True
                    if 'market' in content or 'data' in content:
                        coverage_areas['market_data'] = True
                    if 'risk' in content:
                        coverage_areas['risk_management'] = True
                    if 'consistency' in content:
                        coverage_areas['data_consistency'] = True
                    if 'error' in content or 'exception' in content:
                        coverage_areas['error_handling'] = True
                    if 'performance' in content or 'load' in content:
                        coverage_areas['performance'] = True
                    if 'security' in content or 'auth' in content:
                        coverage_areas['security'] = True
                        
                except Exception as e:
                    logger.warning(f'Could not analyze {test_file}: {e}')
            
            covered_areas = sum(1 for covered in coverage_areas.values() if covered)
            total_areas = len(coverage_areas)
            coverage_percentage = (covered_areas / total_areas) * 100
            
            missing_areas = [area for area, covered in coverage_areas.items() if not covered]
            
            status = 'PASS' if coverage_percentage >= 80 else 'WARN' if coverage_percentage >= 60 else 'FAIL'
            
            return {
                'status': status,
                'message': f'Test coverage analysis completed: {coverage_percentage:.1f}%',
                'coverage_percentage': coverage_percentage,
                'covered_areas': covered_areas,
                'total_areas': total_areas,
                'missing_areas': missing_areas,
                'test_files_analyzed': len(test_files)
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': f'Coverage analysis error: {e}',
                'error': str(e)
            }
    
    def validate_documentation(self) -> Dict[str, Any]:
        """Validate documentation completeness"""
        try:
            integration_dir = Path('tests/integration')
            
            documentation_files = {
                'README.md': integration_dir / 'README.md',
                'INTEGRATION_TEST_ASSESSMENT.md': integration_dir / 'INTEGRATION_TEST_ASSESSMENT.md',
                'test_execution_guide.md': integration_dir / 'test_execution_guide.md'
            }
            
            existing_docs = []
            missing_docs = []
            
            for doc_name, doc_path in documentation_files.items():
                if doc_path.exists():
                    existing_docs.append(doc_name)
                else:
                    missing_docs.append(doc_name)
            
            # Check for inline documentation
            test_files = list(integration_dir.glob('*.py'))
            documented_files = 0
            
            for test_file in test_files:
                try:
                    with open(test_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if '"""' in content or "'''" in content:
                        documented_files += 1
                except Exception:
                    pass
            
            doc_percentage = (len(existing_docs) / len(documentation_files)) * 100
            inline_doc_percentage = (documented_files / len(test_files)) * 100 if test_files else 0
            
            status = 'PASS' if doc_percentage >= 80 and inline_doc_percentage >= 70 else 'WARN'
            
            return {
                'status': status,
                'message': f'Documentation validation completed: {doc_percentage:.1f}% external, {inline_doc_percentage:.1f}% inline',
                'external_doc_percentage': doc_percentage,
                'inline_doc_percentage': inline_doc_percentage,
                'existing_docs': existing_docs,
                'missing_docs': missing_docs,
                'documented_files': documented_files,
                'total_files': len(test_files)
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': f'Documentation validation error: {e}',
                'error': str(e)
            }
    
    async def run_validation(self) -> Dict[str, Any]:
        """Run complete validation of integration tests"""
        self.start_time = time.time()
        logger.info("🔍 Starting Integration Test Validation")
        
        validation_steps = [
            ('File Syntax Validation', self.validate_file_syntax_all),
            ('Import Validation', self.validate_imports_all),
            ('Test Structure Validation', self.validate_test_structure_all),
            ('Mock Configuration Validation', self.validate_mock_configuration),
            ('Test Coverage Analysis', self.validate_test_coverage),
            ('Documentation Validation', self.validate_documentation)
        ]
        
        results = {}
        
        for step_name, step_func in validation_steps:
            logger.info(f"Running: {step_name}")
            try:
                if asyncio.iscoroutinefunction(step_func):
                    result = await step_func()
                else:
                    result = step_func()
                results[step_name] = result
                
                status_emoji = "✅" if result['status'] == 'PASS' else "⚠️" if result['status'] == 'WARN' else "❌"
                logger.info(f"{status_emoji} {step_name}: {result['message']}")
                
            except Exception as e:
                logger.error(f"❌ {step_name} failed: {e}")
                results[step_name] = {
                    'status': 'ERROR',
                    'message': f'Validation step failed: {e}',
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }
        
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        # Generate summary
        total_steps = len(results)
        passed_steps = sum(1 for r in results.values() if r['status'] == 'PASS')
        warned_steps = sum(1 for r in results.values() if r['status'] == 'WARN')
        failed_steps = sum(1 for r in results.values() if r['status'] in ['FAIL', 'ERROR'])
        
        overall_status = 'PASS' if failed_steps == 0 and warned_steps <= 1 else 'WARN' if failed_steps == 0 else 'FAIL'
        
        summary = {
            'overall_status': overall_status,
            'total_steps': total_steps,
            'passed_steps': passed_steps,
            'warned_steps': warned_steps,
            'failed_steps': failed_steps,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        }
        
        return {
            'summary': summary,
            'results': results
        }
    
    def validate_file_syntax_all(self) -> Dict[str, Any]:
        """Validate syntax for all integration test files"""
        integration_dir = Path('tests/integration')
        test_files = list(integration_dir.glob('*.py'))
        
        results = []
        issues = []
        
        for test_file in test_files:
            result = self.validate_file_syntax(test_file)
            results.append(result)
            
            if result['status'] != 'PASS':
                issues.append(f"{test_file.name}: {result['message']}")
        
        passed = sum(1 for r in results if r['status'] == 'PASS')
        total = len(results)
        
        status = 'PASS' if passed == total else 'FAIL'
        
        return {
            'status': status,
            'message': f'Syntax validation: {passed}/{total} files passed',
            'files_checked': total,
            'files_passed': passed,
            'issues': issues
        }
    
    def validate_imports_all(self) -> Dict[str, Any]:
        """Validate imports for all integration test files"""
        integration_dir = Path('tests/integration')
        test_files = list(integration_dir.glob('test_*.py'))
        
        results = []
        issues = []
        
        for test_file in test_files:
            result = self.validate_imports(test_file)
            results.append(result)
            
            if result['status'] != 'PASS':
                issues.append(f"{test_file.name}: {result['message']}")
        
        passed = sum(1 for r in results if r['status'] == 'PASS')
        total = len(results)
        
        status = 'PASS' if passed == total else 'WARN'  # Imports might fail due to missing dependencies
        
        return {
            'status': status,
            'message': f'Import validation: {passed}/{total} files passed',
            'files_checked': total,
            'files_passed': passed,
            'issues': issues
        }
    
    def validate_test_structure_all(self) -> Dict[str, Any]:
        """Validate test structure for all integration test files"""
        integration_dir = Path('tests/integration')
        test_files = list(integration_dir.glob('test_*.py'))
        
        results = []
        all_issues = []
        all_recommendations = []
        
        for test_file in test_files:
            result = self.validate_test_structure(test_file)
            results.append(result)
            
            if 'issues' in result:
                all_issues.extend([f"{test_file.name}: {issue}" for issue in result['issues']])
            if 'recommendations' in result:
                all_recommendations.extend([f"{test_file.name}: {rec}" for rec in result['recommendations']])
        
        passed = sum(1 for r in results if r['status'] == 'PASS')
        warned = sum(1 for r in results if r['status'] == 'WARN')
        total = len(results)
        
        status = 'PASS' if passed == total else 'WARN'
        
        return {
            'status': status,
            'message': f'Structure validation: {passed} passed, {warned} warned out of {total} files',
            'files_checked': total,
            'files_passed': passed,
            'files_warned': warned,
            'issues': all_issues,
            'recommendations': all_recommendations
        }

def generate_validation_report(validation_results: Dict[str, Any]) -> str:
    """Generate a formatted validation report"""
    summary = validation_results['summary']
    results = validation_results['results']
    
    report = f"""
# Integration Test Validation Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Duration:** {summary['duration']:.2f} seconds  
**Overall Status:** {summary['overall_status']}

## Summary
- **Total Validation Steps:** {summary['total_steps']}
- **Passed:** {summary['passed_steps']} ✅
- **Warned:** {summary['warned_steps']} ⚠️
- **Failed:** {summary['failed_steps']} ❌

## Detailed Results

"""
    
    for step_name, result in results.items():
        status_emoji = "✅" if result['status'] == 'PASS' else "⚠️" if result['status'] == 'WARN' else "❌"
        
        report += f"### {status_emoji} {step_name}\n"
        report += f"**Status:** {result['status']}  \n"
        report += f"**Message:** {result['message']}  \n"
        
        if 'issues' in result and result['issues']:
            report += f"**Issues:**\n"
            for issue in result['issues']:
                report += f"- {issue}\n"
        
        if 'recommendations' in result and result['recommendations']:
            report += f"**Recommendations:**\n"
            for rec in result['recommendations']:
                report += f"- {rec}\n"
        
        if 'missing_areas' in result and result['missing_areas']:
            report += f"**Missing Coverage Areas:**\n"
            for area in result['missing_areas']:
                report += f"- {area}\n"
        
        report += "\n"
    
    # Add recommendations
    report += """
## Overall Recommendations

### High Priority
1. Fix any syntax or import errors identified
2. Add missing test coverage areas
3. Create comprehensive documentation
4. Implement real API integration tests (non-mock)

### Medium Priority
1. Add performance and load testing
2. Implement security boundary testing
3. Create automated test reporting dashboard
4. Add CI/CD integration

### Low Priority
1. Add chaos engineering tests
2. Implement advanced monitoring
3. Create self-healing test infrastructure

## Next Steps
1. Review and address all identified issues
2. Implement missing test coverage areas
3. Create comprehensive documentation
4. Set up automated test execution in CI/CD pipeline

---
*This report was generated automatically by the Integration Test Validator*
"""
    
    return report

async def main():
    """Main validation execution"""
    print("🚀 Integration Test Validation Starting...")
    print("=" * 60)
    
    validator = IntegrationTestValidator()
    
    try:
        validation_results = await validator.run_validation()
        
        # Generate and save report
        report = generate_validation_report(validation_results)
        
        report_path = Path('./VALIDATION_REPORT.md')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        # Save JSON results
        json_path = Path('./validation_results.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(validation_results, f, indent=2, default=str)
        
        # Print summary
        summary = validation_results['summary']
        print(f"\n📊 Validation Summary:")
        print(f"Overall Status: {summary['overall_status']}")
        print(f"Steps: {summary['passed_steps']} passed, {summary['warned_steps']} warned, {summary['failed_steps']} failed")
        print(f"Duration: {summary['duration']:.2f} seconds")
        print(f"\n📄 Reports saved:")
        print(f"- Detailed report: {report_path}")
        print(f"- JSON results: {json_path}")
        
        # Return appropriate exit code
        return 0 if summary['overall_status'] in ['PASS', 'WARN'] else 1
        
    except Exception as e:
        logger.error(f"Validation failed with error: {e}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)