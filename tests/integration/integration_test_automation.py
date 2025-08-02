#!/usr/bin/env python3
"""
Integration Test Automation Framework
Provides automated test execution, scheduling, and reporting capabilities.
"""

import asyncio
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False
    schedule = None
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestStatus(Enum):
    """Test execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"

@dataclass
class TestExecution:
    """Represents a test execution instance"""
    test_id: str
    test_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: TestStatus = TestStatus.PENDING
    duration: float = 0.0
    error_message: Optional[str] = None
    artifacts: Dict[str, Any] = None
    retry_count: int = 0

@dataclass
class TestSuite:
    """Represents a collection of related tests"""
    name: str
    description: str
    tests: List[str]
    dependencies: List[str] = None
    timeout: int = 3600  # 1 hour default
    retry_policy: Dict[str, Any] = None
    schedule: Optional[str] = None  # Cron-like schedule

class IntegrationTestAutomation:
    """Main automation framework for integration tests"""
    
    def __init__(self, config_path: str = "tests/integration/config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.test_history = []
        self.active_executions = {}
        self.test_registry = {}
        self.notification_handlers = []
        
        # Setup notification handlers
        self._setup_notifications()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        else:
            # Default configuration
            return {
                'test_suites': [],
                'notifications': {
                    'email': {
                        'enabled': False,
                        'smtp_server': 'localhost',
                        'smtp_port': 587,
                        'username': '',
                        'password': '',
                        'recipients': []
                    },
                    'webhook': {
                        'enabled': False,
                        'url': '',
                        'headers': {}
                    }
                },
                'reporting': {
                    'output_dir': 'test_reports',
                    'formats': ['json', 'html'],
                    'retention_days': 30
                },
                'execution': {
                    'parallel_limit': 5,
                    'default_timeout': 3600,
                    'retry_attempts': 3,
                    'retry_delay': 60
                }
            }
    
    def _setup_notifications(self):
        """Setup notification handlers based on configuration"""
        if self.config['notifications']['email']['enabled']:
            self.notification_handlers.append(self._send_email_notification)
        
        if self.config['notifications'].get('webhook', {}).get('enabled', False):
            self.notification_handlers.append(self._send_webhook_notification)
    
    def register_test(self, test_id: str, test_func: Callable, 
                     metadata: Dict[str, Any] = None):
        """Register a test function for automated execution"""
        self.test_registry[test_id] = {
            'function': test_func,
            'metadata': metadata or {}
        }
        logger.info(f"Registered test: {test_id}")
    
    def register_test_suite(self, suite: TestSuite):
        """Register a test suite for automated execution"""
        suite_config = asdict(suite)
        self.config['test_suites'].append(suite_config)
        logger.info(f"Registered test suite: {suite.name}")
    
    async def execute_test(self, test_id: str, context: Dict[str, Any] = None) -> TestExecution:
        """Execute a single test"""
        if test_id not in self.test_registry:
            raise ValueError(f"Test {test_id} not registered")
        
        execution = TestExecution(
            test_id=test_id,
            test_name=self.test_registry[test_id]['metadata'].get('name', test_id),
            start_time=datetime.now()
        )
        
        self.active_executions[test_id] = execution
        execution.status = TestStatus.RUNNING
        
        try:
            logger.info(f"Starting test execution: {test_id}")
            
            test_func = self.test_registry[test_id]['function']
            
            # Execute test with timeout
            timeout = self.config['execution']['default_timeout']
            result = await asyncio.wait_for(test_func(context or {}), timeout=timeout)
            
            execution.end_time = datetime.now()
            execution.duration = (execution.end_time - execution.start_time).total_seconds()
            execution.status = TestStatus.PASSED
            execution.artifacts = result if isinstance(result, dict) else {'result': result}
            
            logger.info(f"Test {test_id} passed in {execution.duration:.2f}s")
            
        except asyncio.TimeoutError:
            execution.end_time = datetime.now()
            execution.duration = (execution.end_time - execution.start_time).total_seconds()
            execution.status = TestStatus.TIMEOUT
            execution.error_message = f"Test timed out after {timeout} seconds"
            logger.error(f"Test {test_id} timed out")
            
        except Exception as e:
            execution.end_time = datetime.now()
            execution.duration = (execution.end_time - execution.start_time).total_seconds()
            execution.status = TestStatus.FAILED
            execution.error_message = str(e)
            logger.error(f"Test {test_id} failed: {e}")
        
        finally:
            self.active_executions.pop(test_id, None)
            self.test_history.append(execution)
        
        return execution
    
    async def execute_test_suite(self, suite_name: str) -> List[TestExecution]:
        """Execute a complete test suite"""
        suite_config = next(
            (s for s in self.config['test_suites'] if s['name'] == suite_name), 
            None
        )
        
        if not suite_config:
            raise ValueError(f"Test suite {suite_name} not found")
        
        suite = TestSuite(**suite_config)
        executions = []
        
        logger.info(f"Starting test suite execution: {suite_name}")
        
        # Check dependencies
        if suite.dependencies:
            for dep in suite.dependencies:
                dep_result = await self.execute_test_suite(dep)
                if any(e.status == TestStatus.FAILED for e in dep_result):
                    logger.error(f"Dependency {dep} failed, skipping suite {suite_name}")
                    return []
        
        # Execute tests with parallelism control
        parallel_limit = self.config['execution']['parallel_limit']
        semaphore = asyncio.Semaphore(parallel_limit)
        
        async def execute_with_semaphore(test_id):
            async with semaphore:
                return await self.execute_test(test_id)
        
        # Execute tests
        tasks = [execute_with_semaphore(test_id) for test_id in suite.tests]
        executions = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        for i, result in enumerate(executions):
            if isinstance(result, Exception):
                execution = TestExecution(
                    test_id=suite.tests[i],
                    test_name=suite.tests[i],
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    status=TestStatus.FAILED,
                    error_message=str(result)
                )
                executions[i] = execution
        
        # Generate suite report
        await self._generate_suite_report(suite_name, executions)
        
        # Send notifications
        await self._send_notifications(suite_name, executions)
        
        logger.info(f"Test suite {suite_name} completed")
        return executions
    
    async def execute_with_retry(self, test_id: str, max_retries: int = None) -> TestExecution:
        """Execute a test with retry logic"""
        max_retries = max_retries or self.config['execution']['retry_attempts']
        retry_delay = self.config['execution']['retry_delay']
        
        last_execution = None
        
        for attempt in range(max_retries + 1):
            execution = await self.execute_test(test_id)
            execution.retry_count = attempt
            
            if execution.status == TestStatus.PASSED:
                return execution
            
            last_execution = execution
            
            if attempt < max_retries:
                logger.info(f"Test {test_id} failed, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(retry_delay)
        
        logger.error(f"Test {test_id} failed after {max_retries} retries")
        return last_execution
    
    def schedule_test_suite(self, suite_name: str, schedule_expr: str):
        """Schedule a test suite for automated execution"""
        if not SCHEDULE_AVAILABLE:
            logger.warning("Schedule module not available, skipping scheduling")
            return
            
        def job():
            asyncio.create_task(self.execute_test_suite(suite_name))
        
        # Parse schedule expression (simplified cron-like)
        if schedule_expr.startswith('every'):
            parts = schedule_expr.split()
            if len(parts) >= 3:
                interval = int(parts[1])
                unit = parts[2]
                
                if unit.startswith('minute'):
                    schedule.every(interval).minutes.do(job)
                elif unit.startswith('hour'):
                    schedule.every(interval).hours.do(job)
                elif unit.startswith('day'):
                    schedule.every(interval).days.do(job)
        
        logger.info(f"Scheduled test suite {suite_name}: {schedule_expr}")
    
    async def run_scheduler(self):
        """Run the test scheduler"""
        logger.info("Starting test scheduler")
        
        while True:
            schedule.run_pending()
            await asyncio.sleep(60)  # Check every minute
    
    async def _generate_suite_report(self, suite_name: str, executions: List[TestExecution]):
        """Generate test suite report"""
        report_dir = Path(self.config['reporting']['output_dir'])
        report_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Generate JSON report
        if 'json' in self.config['reporting']['formats']:
            json_report = {
                'suite_name': suite_name,
                'timestamp': timestamp,
                'summary': {
                    'total_tests': len(executions),
                    'passed': sum(1 for e in executions if e.status == TestStatus.PASSED),
                    'failed': sum(1 for e in executions if e.status == TestStatus.FAILED),
                    'timeout': sum(1 for e in executions if e.status == TestStatus.TIMEOUT),
                    'total_duration': sum(e.duration for e in executions)
                },
                'executions': [asdict(e) for e in executions]
            }
            
            json_file = report_dir / f"{suite_name}_{timestamp}.json"
            with open(json_file, 'w') as f:
                json.dump(json_report, f, indent=2, default=str)
        
        # Generate HTML report
        if 'html' in self.config['reporting']['formats']:
            html_content = self._generate_html_report(suite_name, executions)
            html_file = report_dir / f"{suite_name}_{timestamp}.html"
            with open(html_file, 'w') as f:
                f.write(html_content)
        
        logger.info(f"Generated reports for suite {suite_name}")
    
    def _generate_html_report(self, suite_name: str, executions: List[TestExecution]) -> str:
        """Generate HTML report"""
        passed = sum(1 for e in executions if e.status == TestStatus.PASSED)
        failed = sum(1 for e in executions if e.status == TestStatus.FAILED)
        total_duration = sum(e.duration for e in executions)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Integration Test Report - {suite_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
                .passed {{ color: green; }}
                .failed {{ color: red; }}
                .timeout {{ color: orange; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>Integration Test Report: {suite_name}</h1>
            <div class="summary">
                <h2>Summary</h2>
                <p>Total Tests: {len(executions)}</p>
                <p class="passed">Passed: {passed}</p>
                <p class="failed">Failed: {failed}</p>
                <p>Total Duration: {total_duration:.2f}s</p>
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <h2>Test Results</h2>
            <table>
                <tr>
                    <th>Test Name</th>
                    <th>Status</th>
                    <th>Duration</th>
                    <th>Error Message</th>
                </tr>
        """
        
        for execution in executions:
            status_class = execution.status.value
            error_msg = execution.error_message or ""
            
            html += f"""
                <tr>
                    <td>{execution.test_name}</td>
                    <td class="{status_class}">{execution.status.value.upper()}</td>
                    <td>{execution.duration:.2f}s</td>
                    <td>{error_msg}</td>
                </tr>
            """
        
        html += """
            </table>
        </body>
        </html>
        """
        
        return html
    
    async def _send_notifications(self, suite_name: str, executions: List[TestExecution]):
        """Send notifications about test results"""
        failed_tests = [e for e in executions if e.status == TestStatus.FAILED]
        
        if failed_tests or self.config['notifications'].get('always_notify', False):
            for handler in self.notification_handlers:
                try:
                    await handler(suite_name, executions)
                except Exception as e:
                    logger.error(f"Notification handler failed: {e}")
    
    async def _send_email_notification(self, suite_name: str, executions: List[TestExecution]):
        """Send email notification"""
        email_config = self.config['notifications']['email']
        
        if not email_config['enabled']:
            return
        
        passed = sum(1 for e in executions if e.status == TestStatus.PASSED)
        failed = sum(1 for e in executions if e.status == TestStatus.FAILED)
        
        subject = f"Integration Test Results: {suite_name} - {passed} Passed, {failed} Failed"
        
        body = f"""
        Integration Test Suite: {suite_name}
        Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        Summary:
        - Total Tests: {len(executions)}
        - Passed: {passed}
        - Failed: {failed}
        
        """
        
        if failed > 0:
            body += "\nFailed Tests:\n"
            for execution in executions:
                if execution.status == TestStatus.FAILED:
                    body += f"- {execution.test_name}: {execution.error_message}\n"
        
        # Send email (simplified implementation)
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = email_config['username']
        msg['To'] = ', '.join(email_config['recipients'])
        
        # Note: In production, implement proper SMTP sending
        logger.info(f"Email notification prepared: {subject}")
    
    async def _send_webhook_notification(self, suite_name: str, executions: List[TestExecution]):
        """Send webhook notification"""
        webhook_config = self.config['notifications']['webhook']
        
        if not webhook_config['enabled']:
            return
        
        payload = {
            'suite_name': suite_name,
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total': len(executions),
                'passed': sum(1 for e in executions if e.status == TestStatus.PASSED),
                'failed': sum(1 for e in executions if e.status == TestStatus.FAILED)
            },
            'failed_tests': [
                {
                    'name': e.test_name,
                    'error': e.error_message
                }
                for e in executions if e.status == TestStatus.FAILED
            ]
        }
        
        # Note: In production, implement actual HTTP request
        logger.info(f"Webhook notification prepared for {webhook_config['url']}")
    
    def get_test_history(self, test_id: str = None, days: int = 7) -> List[TestExecution]:
        """Get test execution history"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        history = [e for e in self.test_history if e.start_time >= cutoff_date]
        
        if test_id:
            history = [e for e in history if e.test_id == test_id]
        
        return history
    
    def get_test_metrics(self, test_id: str = None, days: int = 30) -> Dict[str, Any]:
        """Get test metrics and statistics"""
        history = self.get_test_history(test_id, days)
        
        if not history:
            return {}
        
        total_executions = len(history)
        passed_executions = sum(1 for e in history if e.status == TestStatus.PASSED)
        failed_executions = sum(1 for e in history if e.status == TestStatus.FAILED)
        
        avg_duration = sum(e.duration for e in history) / total_executions
        
        return {
            'total_executions': total_executions,
            'success_rate': (passed_executions / total_executions) * 100,
            'failure_rate': (failed_executions / total_executions) * 100,
            'average_duration': avg_duration,
            'min_duration': min(e.duration for e in history),
            'max_duration': max(e.duration for e in history)
        }

# Example usage and configuration
def create_default_test_suites() -> List[TestSuite]:
    """Create default test suites for the trading system"""
    return [
        TestSuite(
            name="smoke_tests",
            description="Quick smoke tests for basic functionality",
            tests=[
                "test_api_health",
                "test_authentication",
                "test_basic_market_data"
            ],
            timeout=300,  # 5 minutes
            schedule="every 15 minutes"
        ),
        TestSuite(
            name="integration_tests",
            description="Comprehensive integration tests",
            tests=[
                "test_complete_trading_workflow",
                "test_real_time_data_flow",
                "test_portfolio_management",
                "test_data_consistency"
            ],
            dependencies=["smoke_tests"],
            timeout=1800,  # 30 minutes
            schedule="every 4 hours"
        ),
        TestSuite(
            name="regression_tests",
            description="Full regression test suite",
            tests=[
                "test_all_api_endpoints",
                "test_error_scenarios",
                "test_performance_benchmarks",
                "test_security_compliance"
            ],
            dependencies=["integration_tests"],
            timeout=3600,  # 1 hour
            schedule="every 1 day"
        )
    ]

if __name__ == "__main__":
    async def main():
        print("🤖 Integration Test Automation Framework")
        print("=" * 50)
        
        automation = IntegrationTestAutomation()
        
        # Register default test suites
        for suite in create_default_test_suites():
            automation.register_test_suite(suite)
        
        print("Registered test suites:")
        for suite_config in automation.config['test_suites']:
            print(f"- {suite_config['name']}: {len(suite_config['tests'])} tests")
        
        print("\nAutomation framework ready for test execution")
        return True
    
    asyncio.run(main())