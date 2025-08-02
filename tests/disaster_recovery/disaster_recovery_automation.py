#!/usr/bin/env python3
"""
Disaster Recovery Automation
Provides automated disaster recovery testing, scheduling, and orchestration.
"""

import asyncio
import json
import logging
import schedule
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from disaster_recovery_framework import (
    DisasterRecoveryTestRunner, DisasterScenario, DisasterScenarioLibrary,
    RecoveryStatus, DisasterType
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class DisasterRecoverySchedule:
    """Represents a scheduled disaster recovery test"""
    schedule_id: str
    scenario_template: DisasterScenario
    cron_expression: str
    enabled: bool = True
    environment: str = "staging"
    notification_channels: List[str] = None
    max_retries: int = 2
    retry_delay: int = 600  # 10 minutes

@dataclass
class DisasterRecoveryDrill:
    """Represents a disaster recovery drill event"""
    drill_id: str
    name: str
    description: str
    scheduled_time: datetime
    duration_minutes: int
    scenarios: List[DisasterScenario]
    participants: List[str]
    objectives: List[str]
    success_criteria: List[str]
    communication_plan: str

class DisasterRecoveryAutomation:
    """Automated disaster recovery testing and management"""
    
    def __init__(self, config_path: str = "tests/disaster_recovery/dr_config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.test_runner = DisasterRecoveryTestRunner()
        self.scheduled_tests = {}
        self.active_tests = {}
        self.test_history = []
        self.drills = {}
        
        # Setup notification handlers
        self.notification_handlers = []
        self._setup_notifications()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load disaster recovery automation configuration"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        else:
            # Default configuration
            return {
                'automation': {
                    'enabled': True,
                    'max_concurrent_tests': 2,
                    'test_timeout': 1800,  # 30 minutes
                    'cleanup_retention_days': 90
                },
                'environments': {
                    'production': {
                        'enabled': False,
                        'allowed_disaster_types': [],
                        'max_severity': 0.0,
                        'approval_required': True
                    },
                    'staging': {
                        'enabled': True,
                        'allowed_disaster_types': [
                            'database_corruption',
                            'system_crash',
                            'network_failure'
                        ],
                        'max_severity': 0.8,
                        'approval_required': False
                    },
                    'development': {
                        'enabled': True,
                        'allowed_disaster_types': 'all',
                        'max_severity': 1.0,
                        'approval_required': False
                    }
                },
                'notifications': {
                    'email': {
                        'enabled': False,
                        'smtp_server': 'localhost',
                        'recipients': []
                    },
                    'slack': {
                        'enabled': False,
                        'webhook_url': '',
                        'channel': '#disaster-recovery'
                    },
                    'pagerduty': {
                        'enabled': False,
                        'integration_key': '',
                        'service_id': ''
                    }
                },
                'safety': {
                    'max_data_loss_minutes': 60,
                    'max_downtime_minutes': 30,
                    'require_approval_for_production': True,
                    'auto_abort_on_failure': True
                },
                'backup': {
                    'retention_days': 30,
                    'backup_frequency_hours': 6,
                    'verify_backups': True,
                    'encrypt_backups': True
                }
            }
    
    def _setup_notifications(self):
        """Setup notification handlers"""
        if self.config['notifications']['email']['enabled']:
            self.notification_handlers.append(self._send_email_notification)
        
        if self.config['notifications']['slack']['enabled']:
            self.notification_handlers.append(self._send_slack_notification)
        
        if self.config['notifications']['pagerduty']['enabled']:
            self.notification_handlers.append(self._send_pagerduty_notification)
    
    def schedule_disaster_recovery_test(self, schedule: DisasterRecoverySchedule):
        """Schedule a disaster recovery test for automated execution"""
        logger.info(f"Scheduling DR test: {schedule.scenario_template.name}")
        
        self.scheduled_tests[schedule.schedule_id] = schedule
        
        # Parse cron expression and schedule
        self._parse_and_schedule_dr_test(schedule)
    
    def _parse_and_schedule_dr_test(self, dr_schedule: DisasterRecoverySchedule):
        """Parse cron expression and schedule DR test"""
        cron_parts = dr_schedule.cron_expression.split()
        
        if len(cron_parts) != 5:
            logger.error(f"Invalid cron expression: {dr_schedule.cron_expression}")
            return
        
        minute, hour, day, month, weekday = cron_parts
        
        def job():
            asyncio.create_task(self._execute_scheduled_dr_test(dr_schedule))
        
        # Simplified cron parsing
        if hour != '*' and minute != '*' and hour.isdigit() and minute.isdigit():
            schedule.every().day.at(f"{hour.zfill(2)}:{minute.zfill(2)}").do(job)
        elif weekday != '*' and weekday.isdigit():
            # Weekly schedule
            days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            if int(weekday) < len(days):
                getattr(schedule.every(), days[int(weekday)]).at("02:00").do(job)
        else:
            schedule.every(24).hours.do(job)  # Default daily
        
        logger.info(f"Scheduled DR test {dr_schedule.scenario_template.name} with cron: {dr_schedule.cron_expression}")
    
    async def _execute_scheduled_dr_test(self, dr_schedule: DisasterRecoverySchedule):
        """Execute a scheduled disaster recovery test"""
        if not dr_schedule.enabled:
            logger.info(f"Skipping disabled DR test: {dr_schedule.scenario_template.name}")
            return
        
        # Check concurrent test limit
        if len(self.active_tests) >= self.config['automation']['max_concurrent_tests']:
            logger.warning(f"Max concurrent DR tests reached, skipping: {dr_schedule.scenario_template.name}")
            return
        
        # Validate environment permissions
        if not self._validate_test_for_environment(dr_schedule.scenario_template, dr_schedule.environment):
            logger.warning(f"DR test not allowed in environment {dr_schedule.environment}")
            return
        
        # Execute test with retry logic
        for attempt in range(dr_schedule.max_retries + 1):
            try:
                logger.info(f"Executing scheduled DR test: {dr_schedule.scenario_template.name} (attempt {attempt + 1})")
                
                # Create test instance
                scenario = self._create_scenario_instance(dr_schedule.scenario_template)
                
                # Add to active tests
                self.active_tests[scenario.scenario_id] = scenario
                
                # Execute test
                result = await self.test_runner.run_disaster_scenario(scenario)
                
                # Remove from active tests
                self.active_tests.pop(scenario.scenario_id, None)
                
                # Store in history
                self.test_history.append(result)
                
                # Send notifications
                await self._send_test_notifications(result, dr_schedule)
                
                # Save results
                await self._save_test_results(result)
                
                logger.info(f"Completed scheduled DR test: {scenario.name}")
                break
                
            except Exception as e:
                logger.error(f"Scheduled DR test failed (attempt {attempt + 1}): {e}")
                
                if attempt < dr_schedule.max_retries:
                    logger.info(f"Retrying in {dr_schedule.retry_delay} seconds")
                    await asyncio.sleep(dr_schedule.retry_delay)
                else:
                    logger.error(f"All retry attempts failed for DR test: {dr_schedule.scenario_template.name}")
                    
                    # Send failure notification
                    await self._send_failure_notification(dr_schedule, str(e))
    
    def _validate_test_for_environment(self, scenario: DisasterScenario, environment: str) -> bool:
        """Validate if DR test is allowed in the given environment"""
        env_config = self.config['environments'].get(environment, {})
        
        if not env_config.get('enabled', False):
            return False
        
        allowed_types = env_config.get('allowed_disaster_types', [])
        if allowed_types != 'all' and scenario.disaster_type.value not in allowed_types:
            return False
        
        max_severity = env_config.get('max_severity', 1.0)
        if scenario.severity > max_severity:
            return False
        
        return True
    
    def _create_scenario_instance(self, template: DisasterScenario) -> DisasterScenario:
        """Create a new scenario instance from template"""
        return DisasterScenario(
            scenario_id=f"{template.scenario_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name=template.name,
            description=template.description,
            disaster_type=template.disaster_type,
            affected_components=template.affected_components.copy(),
            severity=template.severity,
            expected_rto=template.expected_rto,
            expected_rpo=template.expected_rpo,
            prerequisites=template.prerequisites.copy(),
            recovery_steps=template.recovery_steps.copy(),
            validation_criteria=template.validation_criteria.copy(),
            rollback_plan=template.rollback_plan
        )
    
    async def _save_test_results(self, result):
        """Save DR test results to file"""
        results_dir = Path("tests/disaster_recovery/results")
        results_dir.mkdir(exist_ok=True)
        
        result_file = results_dir / f"{result.scenario_id}_results.json"
        
        with open(result_file, 'w') as f:
            json.dump({
                'result': asdict(result),
                'timestamp': datetime.now().isoformat()
            }, f, indent=2, default=str)
        
        logger.info(f"Saved DR test results to: {result_file}")
    
    async def _send_test_notifications(self, result, schedule: DisasterRecoverySchedule):
        """Send notifications about DR test completion"""
        if not schedule.notification_channels:
            return
        
        for handler in self.notification_handlers:
            try:
                await handler(result, schedule)
            except Exception as e:
                logger.error(f"Failed to send DR test notification: {e}")
    
    async def _send_failure_notification(self, schedule: DisasterRecoverySchedule, error: str):
        """Send notification about DR test failure"""
        logger.info(f"Sending failure notification for: {schedule.scenario_template.name}")
        # Implementation would depend on notification channels
    
    async def _send_email_notification(self, result, schedule: DisasterRecoverySchedule):
        """Send email notification"""
        logger.info(f"Email notification: DR test {result.scenario_id} completed with status {result.status.value}")
    
    async def _send_slack_notification(self, result, schedule: DisasterRecoverySchedule):
        """Send Slack notification"""
        logger.info(f"Slack notification: DR test {result.scenario_id} completed with status {result.status.value}")
    
    async def _send_pagerduty_notification(self, result, schedule: DisasterRecoverySchedule):
        """Send PagerDuty notification"""
        if result.status == RecoveryStatus.FAILED:
            logger.info(f"PagerDuty alert: DR test {result.scenario_id} failed")
    
    def create_disaster_recovery_drill(self, drill: DisasterRecoveryDrill):
        """Create a disaster recovery drill event"""
        logger.info(f"Creating DR drill: {drill.name}")
        self.drills[drill.drill_id] = drill
    
    async def execute_disaster_recovery_drill(self, drill_id: str) -> Dict[str, Any]:
        """Execute a disaster recovery drill"""
        if drill_id not in self.drills:
            raise ValueError(f"DR drill {drill_id} not found")
        
        drill = self.drills[drill_id]
        logger.info(f"Starting DR drill: {drill.name}")
        
        drill_results = {
            'drill_id': drill_id,
            'start_time': datetime.now(),
            'scenario_results': [],
            'objectives_met': [],
            'lessons_learned': [],
            'participants': drill.participants,
            'communication_log': []
        }
        
        try:
            # Execute scenarios in sequence
            for scenario in drill.scenarios:
                logger.info(f"Executing drill scenario: {scenario.name}")
                
                scenario_result = await self.test_runner.run_disaster_scenario(scenario)
                drill_results['scenario_results'].append({
                    'scenario_id': scenario.scenario_id,
                    'name': scenario.name,
                    'status': scenario_result.status.value,
                    'rto': scenario_result.actual_rto,
                    'rpo': scenario_result.actual_rpo,
                    'data_integrity': scenario_result.data_integrity_score
                })
                
                # Brief pause between scenarios
                await asyncio.sleep(60)  # 1 minute pause
            
            # Evaluate drill objectives
            drill_results['objectives_met'] = self._evaluate_drill_objectives(drill, drill_results)
            
            # Generate lessons learned
            drill_results['lessons_learned'] = self._generate_drill_lessons(drill_results)
            
        except Exception as e:
            logger.error(f"DR drill execution failed: {e}")
            drill_results['error'] = str(e)
        
        finally:
            drill_results['end_time'] = datetime.now()
            drill_results['duration'] = (drill_results['end_time'] - drill_results['start_time']).total_seconds()
        
        # Generate drill report
        await self._generate_drill_report(drill, drill_results)
        
        return drill_results
    
    def _evaluate_drill_objectives(self, drill: DisasterRecoveryDrill, results: Dict[str, Any]) -> List[str]:
        """Evaluate if drill objectives were met"""
        objectives_met = []
        
        # Simple evaluation based on scenario success
        successful_scenarios = sum(1 for r in results['scenario_results'] 
                                 if r['status'] == 'completed')
        total_scenarios = len(results['scenario_results'])
        
        if successful_scenarios == total_scenarios:
            objectives_met.append("All disaster scenarios completed successfully")
        
        if successful_scenarios / total_scenarios >= 0.8:
            objectives_met.append("80% or more scenarios succeeded")
        
        # Check RTO/RPO compliance
        rto_compliant = sum(1 for r in results['scenario_results'] 
                           if r.get('rto', 0) <= 900)  # 15 minutes
        
        if rto_compliant == total_scenarios:
            objectives_met.append("All scenarios met RTO requirements")
        
        return objectives_met
    
    def _generate_drill_lessons(self, results: Dict[str, Any]) -> List[str]:
        """Generate lessons learned from drill"""
        lessons = []
        
        # Analyze scenario results for patterns
        failed_scenarios = [r for r in results['scenario_results'] if r['status'] != 'completed']
        
        if failed_scenarios:
            lessons.append(f"{len(failed_scenarios)} scenarios failed - review recovery procedures")
        
        # Check for RTO/RPO issues
        slow_recoveries = [r for r in results['scenario_results'] if r.get('rto', 0) > 600]
        
        if slow_recoveries:
            lessons.append(f"{len(slow_recoveries)} scenarios exceeded 10-minute RTO - optimize recovery processes")
        
        # Data integrity issues
        integrity_issues = [r for r in results['scenario_results'] if r.get('data_integrity', 1.0) < 0.95]
        
        if integrity_issues:
            lessons.append(f"{len(integrity_issues)} scenarios had data integrity issues - review backup procedures")
        
        return lessons
    
    async def _generate_drill_report(self, drill: DisasterRecoveryDrill, results: Dict[str, Any]):
        """Generate disaster recovery drill report"""
        report = f"""
# Disaster Recovery Drill Report: {drill.name}

## Drill Details
- **Drill ID:** {drill.drill_id}
- **Description:** {drill.description}
- **Start Time:** {results['start_time']}
- **Duration:** {results.get('duration', 0):.2f} seconds
- **Participants:** {', '.join(drill.participants)}

## Objectives
"""
        for objective in drill.objectives:
            report += f"- {objective}\n"
        
        report += "\n## Scenario Results\n"
        
        for scenario_result in results['scenario_results']:
            status_emoji = "✅" if scenario_result['status'] == 'completed' else "❌"
            report += f"- {status_emoji} **{scenario_result['name']}:** {scenario_result['status']}\n"
            report += f"  - RTO: {scenario_result.get('rto', 'N/A')}s\n"
            report += f"  - RPO: {scenario_result.get('rpo', 'N/A')}s\n"
            report += f"  - Data Integrity: {scenario_result.get('data_integrity', 'N/A'):.2%}\n"
        
        report += "\n## Objectives Met\n"
        for objective in results['objectives_met']:
            report += f"- ✅ {objective}\n"
        
        report += "\n## Lessons Learned\n"
        for lesson in results['lessons_learned']:
            report += f"- {lesson}\n"
        
        report += f"\n## Success Criteria\n"
        for criteria in drill.success_criteria:
            report += f"- {criteria}\n"
        
        # Save report
        reports_dir = Path("tests/disaster_recovery/drill_reports")
        reports_dir.mkdir(exist_ok=True)
        
        report_file = reports_dir / f"{drill.drill_id}_report.md"
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"DR drill report saved to: {report_file}")
    
    async def run_scheduler(self):
        """Run the disaster recovery test scheduler"""
        logger.info("Starting disaster recovery test scheduler")
        
        while True:
            schedule.run_pending()
            await asyncio.sleep(60)  # Check every minute
    
    def get_test_statistics(self) -> Dict[str, Any]:
        """Get statistics about disaster recovery tests"""
        total_tests = len(self.test_history)
        
        if total_tests == 0:
            return {'total_tests': 0}
        
        successful_tests = sum(1 for result in self.test_history 
                             if result.status == RecoveryStatus.COMPLETED)
        
        failed_tests = sum(1 for result in self.test_history 
                         if result.status == RecoveryStatus.FAILED)
        
        # Calculate average RTO/RPO
        completed_tests = [result for result in self.test_history 
                         if result.status == RecoveryStatus.COMPLETED and result.actual_rto]
        
        avg_rto = 0
        avg_rpo = 0
        avg_data_integrity = 0
        
        if completed_tests:
            avg_rto = sum(result.actual_rto for result in completed_tests) / len(completed_tests)
            avg_rpo = sum(result.actual_rpo for result in completed_tests) / len(completed_tests)
            avg_data_integrity = sum(result.data_integrity_score for result in completed_tests) / len(completed_tests)
        
        # Disaster type distribution
        disaster_type_counts = {}
        for result in self.test_history:
            # Note: We'd need to store disaster type in result for this to work
            disaster_type = "unknown"  # Placeholder
            disaster_type_counts[disaster_type] = disaster_type_counts.get(disaster_type, 0) + 1
        
        return {
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'failed_tests': failed_tests,
            'success_rate': (successful_tests / total_tests) * 100,
            'average_rto': avg_rto,
            'average_rpo': avg_rpo,
            'average_data_integrity': avg_data_integrity,
            'disaster_type_distribution': disaster_type_counts,
            'active_tests': len(self.active_tests),
            'scheduled_tests': len(self.scheduled_tests)
        }

# Predefined disaster recovery schedules
class DisasterRecoveryScheduleLibrary:
    """Library of predefined disaster recovery schedules"""
    
    @staticmethod
    def daily_backup_validation() -> DisasterRecoverySchedule:
        """Daily backup validation schedule"""
        return DisasterRecoverySchedule(
            schedule_id="daily_backup_validation",
            scenario_template=DisasterScenarioLibrary.database_corruption_scenario(),
            cron_expression="0 3 * * *",  # Daily at 3 AM
            enabled=True,
            environment="staging",
            notification_channels=['email'],
            max_retries=1
        )
    
    @staticmethod
    def weekly_failover_test() -> DisasterRecoverySchedule:
        """Weekly failover test schedule"""
        return DisasterRecoverySchedule(
            schedule_id="weekly_failover_test",
            scenario_template=DisasterScenarioLibrary.network_partition_scenario(),
            cron_expression="0 2 * * 0",  # Weekly on Sunday at 2 AM
            enabled=True,
            environment="staging",
            notification_channels=['email', 'slack'],
            max_retries=2
        )
    
    @staticmethod
    def monthly_full_dr_test() -> DisasterRecoverySchedule:
        """Monthly full disaster recovery test"""
        return DisasterRecoverySchedule(
            schedule_id="monthly_full_dr_test",
            scenario_template=DisasterScenarioLibrary.complete_system_failure_scenario(),
            cron_expression="0 1 1 * *",  # Monthly on 1st at 1 AM
            enabled=True,
            environment="staging",
            notification_channels=['email', 'slack', 'pagerduty'],
            max_retries=1
        )
    
    @staticmethod
    def quarterly_dr_drill() -> DisasterRecoveryDrill:
        """Quarterly disaster recovery drill"""
        return DisasterRecoveryDrill(
            drill_id="quarterly_dr_drill",
            name="Quarterly Disaster Recovery Drill",
            description="Comprehensive disaster recovery exercise with multiple scenarios",
            scheduled_time=datetime.now().replace(day=1, hour=9, minute=0, second=0, microsecond=0),
            duration_minutes=240,  # 4 hours
            scenarios=[
                DisasterScenarioLibrary.database_corruption_scenario(),
                DisasterScenarioLibrary.network_partition_scenario(),
                DisasterScenarioLibrary.complete_system_failure_scenario()
            ],
            participants=[
                "DevOps Team",
                "Database Administrators",
                "Site Reliability Engineers",
                "Security Team",
                "Management"
            ],
            objectives=[
                "Validate all disaster recovery procedures",
                "Test team coordination and communication",
                "Identify gaps in recovery processes",
                "Ensure RTO/RPO compliance",
                "Train team on disaster response"
            ],
            success_criteria=[
                "All scenarios complete within expected timeframes",
                "Data integrity maintained throughout recovery",
                "Team follows established procedures",
                "Communication plan executed effectively",
                "Lessons learned documented and addressed"
            ],
            communication_plan="Use dedicated Slack channel #dr-drill for real-time coordination"
        )

if __name__ == "__main__":
    async def main():
        """Main disaster recovery automation execution"""
        print("🚨 Disaster Recovery Automation")
        print("=" * 50)
        
        automation = DisasterRecoveryAutomation()
        
        # Schedule some tests
        automation.schedule_disaster_recovery_test(DisasterRecoveryScheduleLibrary.daily_backup_validation())
        automation.schedule_disaster_recovery_test(DisasterRecoveryScheduleLibrary.weekly_failover_test())
        
        # Create a drill
        drill = DisasterRecoveryScheduleLibrary.quarterly_dr_drill()
        automation.create_disaster_recovery_drill(drill)
        
        print("Disaster recovery automation configured:")
        print(f"- Scheduled tests: {len(automation.scheduled_tests)}")
        print(f"- Drills: {len(automation.drills)}")
        
        # Get statistics
        stats = automation.get_test_statistics()
        print(f"- Total tests run: {stats['total_tests']}")
        
        return True
    
    asyncio.run(main())