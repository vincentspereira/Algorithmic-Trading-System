#!/usr/bin/env python3
"""
Phase 1 Comprehensive Test Execution Framework

This script executes all four types of testing for Phase 1:
1. Unit Testing - Individual component validation
2. Integration Testing - Component interaction verification
3. System Testing - End-to-end system validation
4. User Acceptance Testing - Business requirement validation

Generates comprehensive test reports with coverage metrics and defect tracking.
"""

import os
import sys
import json
import time
import subprocess
import unittest
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_execution.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TestType(Enum):
    UNIT = "unit"
    INTEGRATION = "integration"
    SYSTEM = "system"
    UAT = "uat"

class TestStatus(Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"

class DefectSeverity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

@dataclass
class TestResult:
    test_name: str
    test_type: TestType
    status: TestStatus
    duration: float
    error_message: Optional[str] = None
    coverage: Optional[float] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

@dataclass
class Defect:
    defect_id: str
    severity: DefectSeverity
    description: str
    test_case: str
    component: str
    status: str = "OPEN"
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

class Phase1TestExecutor:
    """Comprehensive test executor for Phase 1 validation"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_results: List[TestResult] = []
        self.defects: List[Defect] = []
        self.start_time = None
        self.end_time = None
        
        # Test configuration
        self.test_config = {
            'unit_test_paths': [
                'tests/unit',
                'nautilus_trader_engine/*/test_*.py',
                'api/tests',
                'services/*/tests'
            ],
            'integration_test_paths': [
                'tests/integration',
                'tests/e2e'
            ],
            'system_test_paths': [
                'tests/standalone',
                'performance/test_*.py'
            ],
            'uat_test_paths': [
                'tests/uat',
                'tests/acceptance'
            ]
        }
    
    def execute_all_tests(self) -> Dict[str, Any]:
        """Execute all test types and generate comprehensive report"""
        logger.info("Starting Phase 1 Comprehensive Test Execution")
        self.start_time = datetime.now()
        
        try:
            # Execute each test type
            self._execute_unit_tests()
            self._execute_integration_tests()
            self._execute_system_tests()
            self._execute_uat_tests()
            
            # Generate comprehensive report
            report = self._generate_comprehensive_report()
            
            # Save results
            self._save_test_results(report)
            
            return report
            
        except Exception as e:
            logger.error(f"Test execution failed: {str(e)}")
            raise
        finally:
            self.end_time = datetime.now()
    
    def _execute_unit_tests(self):
        """Execute unit tests for individual components"""
        logger.info("Executing Unit Tests...")
        
        unit_test_cases = [
            # Core Trading Engine Tests
            {'name': 'NautilusTrader Integration', 'path': 'nautilus_trader_engine/tests/test_nautilus_imports.py'},
            {'name': 'Order Management', 'path': 'nautilus_trader_engine/tests/test_broker_simple.py'},
            {'name': 'Risk Management', 'path': 'nautilus_trader_engine/risk/test_*.py'},
            {'name': 'Portfolio Management', 'path': 'nautilus_trader_engine/tests/test_portfolio_value.py'},
            
            # Database Tests
            {'name': 'PostgreSQL Integration', 'path': 'database/tests/test_postgres.py'},
            {'name': 'ClickHouse Integration', 'path': 'database/tests/test_clickhouse.py'},
            {'name': 'Redis Integration', 'path': 'database/tests/test_redis.py'},
            {'name': 'Qdrant Integration', 'path': 'tests/integration/test_qdrant_integration.py'},
            
            # API Tests
            {'name': 'REST API', 'path': 'api/tests/test_health.py'},
            {'name': 'GraphQL API', 'path': 'test_graphql_api.py'},
            {'name': 'WebSocket API', 'path': 'api/tests/test_market_data.py'},
            {'name': 'gRPC API', 'path': 'api/trading.proto'},
            
            # Security Tests
            {'name': 'Authentication', 'path': 'security/test_zero_trust_security.py'},
            {'name': 'Authorization', 'path': 'security/test_zero_trust_security.py'},
            {'name': 'Encryption', 'path': 'security/test_zero_trust_security.py'},
            
            # Technical Indicators
            {'name': 'Volume-Weighted Indicators', 'path': 'nautilus_trader_engine/tests/test_technical_indicators.py'},
            
            # Data Feed Management
            {'name': 'Market Data Service', 'path': 'test_data_feeds.py'},
            {'name': 'Data Normalization', 'path': 'test_data_feeds.py'}
        ]
        
        for test_case in unit_test_cases:
            self._run_test_case(test_case['name'], TestType.UNIT, test_case['path'])
    
    def _execute_integration_tests(self):
        """Execute integration tests for component interactions"""
        logger.info("Executing Integration Tests...")
        
        integration_test_cases = [
            # System Integration
            {'name': 'End-to-End Trading Workflow', 'path': 'tests/integration/test_end_to_end_integration.py'},
            {'name': 'Database Integration Suite', 'path': 'tests/integration/test_database_integration.py'},
            {'name': 'API Integration Suite', 'path': 'tests/integration/test_api_integration.py'},
            
            # Event-Driven Architecture
            {'name': 'Kafka Event Bus', 'path': 'tests/integration/test_kafka_integration.py'},
            {'name': 'Event Processing', 'path': 'tests/integration/test_event_processing.py'},
            
            # Data Flow Integration
            {'name': 'Data Pipeline Integration', 'path': 'tests/integration/test_data_pipeline.py'},
            {'name': 'Market Data Flow', 'path': 'tests/integration/test_data_pipeline.py'},
            
            # Security Integration
            {'name': 'Zero-Trust Architecture', 'path': 'tests/integration/test_security_integration.py'},
            {'name': 'RBAC Integration', 'path': 'tests/integration/test_security_integration.py'}
        ]
        
        for test_case in integration_test_cases:
            self._run_test_case(test_case['name'], TestType.INTEGRATION, test_case['path'])
    
    def _execute_system_tests(self):
        """Execute system tests for end-to-end validation"""
        logger.info("Executing System Tests...")
        
        system_test_cases = [
            # Complete System Validation
            {'name': 'Complete Trading System', 'path': 'performance/test_complete_system.py'},
            {'name': 'Multi-Asset Trading', 'path': 'tests/system/test_multi_asset_trading.py'},
            {'name': 'High-Frequency Trading', 'path': 'tests/system/test_end_to_end_trading.py'},
            
            # Performance Validation
            {'name': 'Latency Requirements (<100ms)', 'path': 'performance/test_latency.py'},
            {'name': 'Throughput Requirements', 'path': 'performance/test_performance_systems.py'},
            {'name': 'Scalability Testing', 'path': 'tests/system/test_scalability.py'},
            
            # Disaster Recovery
            {'name': 'Backup and Recovery', 'path': 'tests/system/test_system_disaster_recovery.py'},
            {'name': 'Failover Testing', 'path': 'tests/system/test_system_disaster_recovery.py'},
            
            # Compliance and Audit
            {'name': 'Audit Trail Validation', 'path': 'tests/test_audit_reporting.py'},
            {'name': 'Compliance Engine', 'path': 'tests/test_automated_compliance.py'}
        ]
        
        for test_case in system_test_cases:
            self._run_test_case(test_case['name'], TestType.SYSTEM, test_case['path'])
    
    def _execute_uat_tests(self):
        """Execute user acceptance tests for business validation"""
        logger.info("Executing User Acceptance Tests...")
        
        uat_test_cases = [
            # Business Process Validation
            {'name': 'Strategy Creation Workflow', 'path': 'tests/uat/test_strategy_creation.py'},
            {'name': 'Portfolio Management Workflow', 'path': 'tests/uat/test_uat_portfolio_management.py'},
            {'name': 'Risk Management Workflow', 'path': 'tests/uat/test_uat_risk_management.py'},
            
            # User Interface Validation
            {'name': 'Trading Dashboard Usability', 'path': 'tests/uat/test_dashboard_usability.py'},
            {'name': 'API Documentation Completeness', 'path': 'tests/uat/test_api_documentation.py'},
            
            # Business Requirements
            {'name': 'Multi-Asset Support', 'path': 'tests/uat/test_multi_asset_support.py'},
            {'name': 'Real-Time Data Processing', 'path': 'tests/uat/test_realtime_processing.py'},
            {'name': 'Regulatory Compliance', 'path': 'tests/uat/test_regulatory_compliance.py'}
        ]
        
        for test_case in uat_test_cases:
            self._run_test_case(test_case['name'], TestType.UAT, test_case['path'])
    
    def _run_test_case(self, test_name: str, test_type: TestType, test_path: str):
        """Run individual test case and record results"""
        logger.info(f"Running {test_type.value} test: {test_name}")
        start_time = time.time()
        
        try:
            # Check if test file exists
            full_path = self.project_root / test_path
            if not self._test_exists(full_path):
                logger.warning(f"Test file not found: {test_path}")
                result = TestResult(
                    test_name=test_name,
                    test_type=test_type,
                    status=TestStatus.SKIPPED,
                    duration=0,
                    error_message=f"Test file not found: {test_path}"
                )
                self.test_results.append(result)
                return
            
            # Execute test using pytest
            cmd = [sys.executable, '-m', 'pytest', str(full_path), '-v', '--tb=short']
            result_process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root)
            )
            
            duration = time.time() - start_time
            
            if result_process.returncode == 0:
                status = TestStatus.PASSED
                error_message = None
            else:
                status = TestStatus.FAILED
                error_message = result_process.stderr or result_process.stdout
                
                # Create defect for failed test
                self._create_defect_from_failure(test_name, error_message, test_type)
            
            result = TestResult(
                test_name=test_name,
                test_type=test_type,
                status=status,
                duration=duration,
                error_message=error_message
            )
            
            self.test_results.append(result)
            logger.info(f"Test {test_name}: {status.value} ({duration:.2f}s)")
            
        except Exception as e:
            duration = time.time() - start_time
            error_message = str(e)
            
            result = TestResult(
                test_name=test_name,
                test_type=test_type,
                status=TestStatus.ERROR,
                duration=duration,
                error_message=error_message
            )
            
            self.test_results.append(result)
            self._create_defect_from_failure(test_name, error_message, test_type)
            logger.error(f"Test {test_name} error: {error_message}")
    
    def _test_exists(self, test_path: Path) -> bool:
        """Check if test file or pattern exists"""
        if test_path.exists():
            return True
        
        # Check for glob patterns
        if '*' in str(test_path):
            parent = test_path.parent
            pattern = test_path.name
            if parent.exists():
                matches = list(parent.glob(pattern))
                return len(matches) > 0
        
        return False
    
    def _create_defect_from_failure(self, test_name: str, error_message: str, test_type: TestType):
        """Create defect record from test failure"""
        # Determine severity based on test type and error
        severity = DefectSeverity.MEDIUM
        if test_type in [TestType.SYSTEM, TestType.INTEGRATION]:
            severity = DefectSeverity.HIGH
        if "critical" in error_message.lower() or "fatal" in error_message.lower():
            severity = DefectSeverity.CRITICAL
        
        defect = Defect(
            defect_id=f"DEF-{len(self.defects) + 1:04d}",
            severity=severity,
            description=error_message[:500],  # Truncate long messages
            test_case=test_name,
            component=self._extract_component_from_test(test_name)
        )
        
        self.defects.append(defect)
    
    def _extract_component_from_test(self, test_name: str) -> str:
        """Extract component name from test name"""
        component_mapping = {
            'NautilusTrader': 'Trading Engine',
            'PostgreSQL': 'Database',
            'ClickHouse': 'Database',
            'Redis': 'Database',
            'Qdrant': 'Database',
            'REST API': 'API Layer',
            'GraphQL': 'API Layer',
            'WebSocket': 'API Layer',
            'gRPC': 'API Layer',
            'Authentication': 'Security',
            'Authorization': 'Security',
            'Encryption': 'Security',
            'Kafka': 'Event Bus',
            'Market Data': 'Data Feed'
        }
        
        for key, component in component_mapping.items():
            if key.lower() in test_name.lower():
                return component
        
        return 'Unknown'
    
    def _generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive test execution report"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r.status == TestStatus.PASSED])
        failed_tests = len([r for r in self.test_results if r.status == TestStatus.FAILED])
        skipped_tests = len([r for r in self.test_results if r.status == TestStatus.SKIPPED])
        error_tests = len([r for r in self.test_results if r.status == TestStatus.ERROR])
        
        # Calculate metrics by test type
        test_type_metrics = {}
        for test_type in TestType:
            type_results = [r for r in self.test_results if r.test_type == test_type]
            test_type_metrics[test_type.value] = {
                'total': len(type_results),
                'passed': len([r for r in type_results if r.status == TestStatus.PASSED]),
                'failed': len([r for r in type_results if r.status == TestStatus.FAILED]),
                'skipped': len([r for r in type_results if r.status == TestStatus.SKIPPED]),
                'error': len([r for r in type_results if r.status == TestStatus.ERROR]),
                'pass_rate': (len([r for r in type_results if r.status == TestStatus.PASSED]) / len(type_results) * 100) if type_results else 0
            }
        
        # Defect analysis
        defect_by_severity = {}
        for severity in DefectSeverity:
            defect_by_severity[severity.value] = len([d for d in self.defects if d.severity == severity])
        
        report = {
            'execution_summary': {
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'end_time': self.end_time.isoformat() if self.end_time else None,
                'duration': (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else 0,
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'skipped': skipped_tests,
                'error': error_tests,
                'pass_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            'test_type_breakdown': test_type_metrics,
            'defect_summary': {
                'total_defects': len(self.defects),
                'by_severity': defect_by_severity
            },
            'detailed_results': [self._serialize_test_result(result) for result in self.test_results],
            'defects': [self._serialize_defect(defect) for defect in self.defects],
            'coverage_analysis': self._analyze_coverage(),
            'recommendations': self._generate_recommendations()
        }
        
        return report
    
    def _serialize_test_result(self, result: TestResult) -> Dict[str, Any]:
        """Serialize TestResult with proper enum handling"""
        return {
            'test_name': result.test_name,
            'test_type': result.test_type.value,
            'status': result.status.value,
            'duration': result.duration,
            'error_message': result.error_message,
            'coverage': result.coverage,
            'timestamp': result.timestamp
        }
    
    def _serialize_defect(self, defect: Defect) -> Dict[str, Any]:
        """Serialize Defect with proper enum handling"""
        return {
            'defect_id': defect.defect_id,
            'severity': defect.severity.value,
            'description': defect.description,
            'test_case': defect.test_case,
            'component': defect.component,
            'status': defect.status,
            'timestamp': defect.timestamp
        }
    
    def _analyze_coverage(self) -> Dict[str, Any]:
        """Analyze test coverage across components"""
        components_tested = set()
        for result in self.test_results:
            component = self._extract_component_from_test(result.test_name)
            components_tested.add(component)
        
        # Define expected components for Phase 1
        expected_components = {
            'Trading Engine', 'Database', 'API Layer', 'Security', 
            'Event Bus', 'Data Feed', 'Risk Management', 'Portfolio Management',
            'Technical Indicators', 'Compliance', 'Audit Trail'
        }
        
        coverage_percentage = (len(components_tested) / len(expected_components)) * 100
        
        return {
            'components_tested': list(components_tested),
            'expected_components': list(expected_components),
            'missing_components': list(expected_components - components_tested),
            'coverage_percentage': coverage_percentage
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Check pass rate
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r.status == TestStatus.PASSED])
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        if pass_rate < 90:
            recommendations.append(f"Overall pass rate is {pass_rate:.1f}%. Recommend addressing failed tests before production deployment.")
        
        # Check critical defects
        critical_defects = len([d for d in self.defects if d.severity == DefectSeverity.CRITICAL])
        if critical_defects > 0:
            recommendations.append(f"Found {critical_defects} critical defects. These must be resolved before production.")
        
        # Check skipped tests
        skipped_tests = len([r for r in self.test_results if r.status == TestStatus.SKIPPED])
        if skipped_tests > 0:
            recommendations.append(f"{skipped_tests} tests were skipped. Implement missing test files for complete coverage.")
        
        # Check coverage
        coverage = self._analyze_coverage()
        if coverage['coverage_percentage'] < 100:
            recommendations.append(f"Component coverage is {coverage['coverage_percentage']:.1f}%. Add tests for: {', '.join(coverage['missing_components'])}")
        
        if not recommendations:
            recommendations.append("All tests passed successfully. System is ready for production deployment.")
        
        return recommendations
    
    def _save_test_results(self, report: Dict[str, Any]):
        """Save test results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON report
        json_file = self.project_root / f"tests/results/phase1_test_report_{timestamp}.json"
        json_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(json_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Save HTML report
        html_file = self.project_root / f"tests/results/phase1_test_report_{timestamp}.html"
        self._generate_html_report(report, html_file)
        
        logger.info(f"Test results saved to {json_file} and {html_file}")
    
    def _generate_html_report(self, report: Dict[str, Any], output_file: Path):
        """Generate HTML test report"""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Phase 1 Comprehensive Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .metric {{ text-align: center; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }}
        .passed {{ background-color: #d4edda; }}
        .failed {{ background-color: #f8d7da; }}
        .skipped {{ background-color: #fff3cd; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .defect-critical {{ background-color: #dc3545; color: white; }}
        .defect-high {{ background-color: #fd7e14; color: white; }}
        .defect-medium {{ background-color: #ffc107; }}
        .defect-low {{ background-color: #28a745; color: white; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Phase 1 Comprehensive Test Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Duration: {report['execution_summary']['duration']:.2f} seconds</p>
    </div>
    
    <div class="summary">
        <div class="metric passed">
            <h3>{report['execution_summary']['passed']}</h3>
            <p>Passed</p>
        </div>
        <div class="metric failed">
            <h3>{report['execution_summary']['failed']}</h3>
            <p>Failed</p>
        </div>
        <div class="metric skipped">
            <h3>{report['execution_summary']['skipped']}</h3>
            <p>Skipped</p>
        </div>
        <div class="metric">
            <h3>{report['execution_summary']['pass_rate']:.1f}%</h3>
            <p>Pass Rate</p>
        </div>
    </div>
    
    <h2>Test Results by Type</h2>
    <table>
        <tr><th>Test Type</th><th>Total</th><th>Passed</th><th>Failed</th><th>Skipped</th><th>Pass Rate</th></tr>
"""
        
        for test_type, metrics in report['test_type_breakdown'].items():
            html_content += f"""
        <tr>
            <td>{test_type.title()}</td>
            <td>{metrics['total']}</td>
            <td>{metrics['passed']}</td>
            <td>{metrics['failed']}</td>
            <td>{metrics['skipped']}</td>
            <td>{metrics['pass_rate']:.1f}%</td>
        </tr>
"""
        
        html_content += """
    </table>
    
    <h2>Defects Summary</h2>
    <table>
        <tr><th>Severity</th><th>Count</th></tr>
"""
        
        for severity, count in report['defect_summary']['by_severity'].items():
            css_class = f"defect-{severity.lower()}"
            html_content += f'<tr class="{css_class}"><td>{severity}</td><td>{count}</td></tr>'
        
        html_content += """
    </table>
    
    <h2>Recommendations</h2>
    <ul>
"""
        
        for recommendation in report['recommendations']:
            html_content += f"<li>{recommendation}</li>"
        
        html_content += """
    </ul>
    
    <h2>Detailed Test Results</h2>
    <table>
        <tr><th>Test Name</th><th>Type</th><th>Status</th><th>Duration</th><th>Error</th></tr>
"""
        
        for result in report['detailed_results']:
            status_class = result['status'].lower()
            error_msg = result.get('error_message', '')[:100] if result.get('error_message') else ''
            html_content += f"""
        <tr class="{status_class}">
            <td>{result['test_name']}</td>
            <td>{result['test_type']}</td>
            <td>{result['status']}</td>
            <td>{result['duration']:.2f}s</td>
            <td>{error_msg}</td>
        </tr>
"""
        
        html_content += """
    </table>
</body>
</html>
"""
        
        with open(output_file, 'w') as f:
            f.write(html_content)

def main():
    """Main execution function"""
    try:
        executor = Phase1TestExecutor()
        report = executor.execute_all_tests()
        
        print("\n" + "="*80)
        print("PHASE 1 COMPREHENSIVE TEST EXECUTION COMPLETE")
        print("="*80)
        print(f"Total Tests: {report['execution_summary']['total_tests']}")
        print(f"Passed: {report['execution_summary']['passed']}")
        print(f"Failed: {report['execution_summary']['failed']}")
        print(f"Skipped: {report['execution_summary']['skipped']}")
        print(f"Pass Rate: {report['execution_summary']['pass_rate']:.1f}%")
        print(f"Total Defects: {report['defect_summary']['total_defects']}")
        print(f"Duration: {report['execution_summary']['duration']:.2f} seconds")
        
        print("\nRecommendations:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"{i}. {rec}")
        
        return report['execution_summary']['pass_rate'] >= 90
        
    except Exception as e:
        logger.error(f"Test execution failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)