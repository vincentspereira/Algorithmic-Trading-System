#!/usr/bin/env python3
"""
Chaos Engineering Automation
Provides automated chaos experiment scheduling, execution, and reporting.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import schedule
import yaml
from chaos_engineering_framework import (
    ChaosExperiment, ChaosExperimentRunner, ChaosExperimentLibrary,
    FailureType, ChaosExperimentStatus
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ChaosSchedule:
    """Represents a scheduled chaos experiment"""
    schedule_id: str
    experiment_template: ChaosExperiment
    cron_expression: str
    enabled: bool = True
    max_concurrent: int = 1
    retry_count: int = 3
    retry_delay: int = 300  # seconds
    notification_channels: List[str] = None
    environment_filters: List[str] = None

@dataclass
class ChaosGameDay:
    """Represents a chaos game day event"""
    game_day_id: str
    name: str
    description: str
    start_time: datetime
    duration: int  # minutes
    experiments: List[ChaosExperiment]
    participants: List[str]
    objectives: List[str]
    success_criteria: List[str]

class ChaosAutomation:
    """Automated chaos engineering execution and management"""
    
    def __init__(self, config_path: str = "tests/chaos/chaos_config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.experiment_runner = ChaosExperimentRunner()
        self.scheduled_experiments = {}
        self.active_experiments = {}
        self.experiment_history = []
        self.game_days = {}
        
        # Setup notification handlers
        self.notification_handlers = []
        self._setup_notifications()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load chaos automation configuration"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        else:
            # Default configuration
            return {
                'automation': {
                    'enabled': True,
                    'max_concurrent_experiments': 3,
                    'experiment_timeout': 3600,  # 1 hour
                    'cleanup_retention_days': 30
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
                        'channel': '#chaos-engineering'
                    },
                    'webhook': {
                        'enabled': False,
                        'url': '',
                        'headers': {}
                    }
                },
                'environments': {
                    'production': {
                        'enabled': False,
                        'allowed_failure_types': ['network_latency'],
                        'max_intensity': 0.3
                    },
                    'staging': {
                        'enabled': True,
                        'allowed_failure_types': ['network_latency', 'service_crash', 'memory_pressure'],
                        'max_intensity': 0.8
                    },
                    'development': {
                        'enabled': True,
                        'allowed_failure_types': 'all',
                        'max_intensity': 1.0
                    }
                },
                'safety': {
                    'circuit_breaker_enabled': True,
                    'max_error_rate': 15.0,
                    'max_response_time': 10000,  # milliseconds
                    'abort_on_critical_failure': True
                }
            }
    
    def _setup_notifications(self):
        """Setup notification handlers"""
        if self.config['notifications']['email']['enabled']:
            self.notification_handlers.append(self._send_email_notification)
        
        if self.config['notifications']['slack']['enabled']:
            self.notification_handlers.append(self._send_slack_notification)
        
        if self.config['notifications']['webhook']['enabled']:
            self.notification_handlers.append(self._send_webhook_notification)
    
    def schedule_experiment(self, schedule: ChaosSchedule):
        """Schedule a chaos experiment for automated execution"""
        logger.info(f"Scheduling chaos experiment: {schedule.experiment_template.name}")
        
        self.scheduled_experiments[schedule.schedule_id] = schedule
        
        # Parse cron expression and schedule
        self._parse_and_schedule(schedule)
    
    def _parse_and_schedule(self, chaos_schedule: ChaosSchedule):
        """Parse cron expression and schedule experiment"""
        cron_parts = chaos_schedule.cron_expression.split()
        
        if len(cron_parts) != 5:
            logger.error(f"Invalid cron expression: {chaos_schedule.cron_expression}")
            return
        
        minute, hour, day, month, weekday = cron_parts
        
        def job():
            asyncio.create_task(self._execute_scheduled_experiment(chaos_schedule))
        
        # Simplified cron parsing - extend as needed
        if hour != '*' and minute != '*' and hour.isdigit() and minute.isdigit():
            schedule.every().day.at(f"{hour.zfill(2)}:{minute.zfill(2)}").do(job)
        elif minute != '*' and minute.isdigit():
            schedule.every().hour.at(f":{minute.zfill(2)}").do(job)
        else:
            schedule.every(10).minutes.do(job)  # Default fallback
        
        logger.info(f"Scheduled experiment {chaos_schedule.experiment_template.name} with cron: {chaos_schedule.cron_expression}")
    
    async def _execute_scheduled_experiment(self, chaos_schedule: ChaosSchedule):
        """Execute a scheduled chaos experiment"""
        if not chaos_schedule.enabled:
            logger.info(f"Skipping disabled experiment: {chaos_schedule.experiment_template.name}")
            return
        
        # Check concurrent experiment limit
        if len(self.active_experiments) >= self.config['automation']['max_concurrent_experiments']:
            logger.warning(f"Max concurrent experiments reached, skipping: {chaos_schedule.experiment_template.name}")
            return
        
        # Check environment filters
        current_env = self._get_current_environment()
        if chaos_schedule.environment_filters and current_env not in chaos_schedule.environment_filters:
            logger.info(f"Environment {current_env} not in filters, skipping experiment")
            return
        
        # Validate experiment against environment constraints
        if not self._validate_experiment_for_environment(chaos_schedule.experiment_template, current_env):
            logger.warning(f"Experiment not allowed in environment {current_env}")
            return
        
        # Execute experiment with retry logic
        for attempt in range(chaos_schedule.retry_count + 1):
            try:
                logger.info(f"Executing scheduled experiment: {chaos_schedule.experiment_template.name} (attempt {attempt + 1})")
                
                # Create experiment instance
                experiment = self._create_experiment_instance(chaos_schedule.experiment_template)
                
                # Add to active experiments
                self.active_experiments[experiment.experiment_id] = experiment
                
                # Execute experiment
                results = await self.experiment_runner.run_experiment(experiment)
                
                # Remove from active experiments
                self.active_experiments.pop(experiment.experiment_id, None)
                
                # Store in history
                self.experiment_history.append(experiment)
                
                # Send notifications
                await self._send_experiment_notifications(experiment, chaos_schedule)
                
                # Save results
                await self._save_experiment_results(experiment)
                
                logger.info(f"Completed scheduled experiment: {experiment.name}")
                break
                
            except Exception as e:
                logger.error(f"Scheduled experiment failed (attempt {attempt + 1}): {e}")
                
                if attempt < chaos_schedule.retry_count:
                    logger.info(f"Retrying in {chaos_schedule.retry_delay} seconds")
                    await asyncio.sleep(chaos_schedule.retry_delay)
                else:
                    logger.error(f"All retry attempts failed for experiment: {chaos_schedule.experiment_template.name}")
                    
                    # Send failure notification
                    await self._send_failure_notification(chaos_schedule, str(e))
    
    def _get_current_environment(self) -> str:
        """Get current environment (would integrate with actual environment detection)"""
        # This would typically read from environment variables or configuration
        return "development"  # Default for testing
    
    def _validate_experiment_for_environment(self, experiment: ChaosExperiment, environment: str) -> bool:
        """Validate if experiment is allowed in the given environment"""
        env_config = self.config['environments'].get(environment, {})
        
        if not env_config.get('enabled', False):
            return False
        
        allowed_failures = env_config.get('allowed_failure_types', [])
        if allowed_failures != 'all' and experiment.failure_type.value not in allowed_failures:
            return False
        
        max_intensity = env_config.get('max_intensity', 1.0)
        if experiment.intensity > max_intensity:
            return False
        
        return True
    
    def _create_experiment_instance(self, template: ChaosExperiment) -> ChaosExperiment:
        """Create a new experiment instance from template"""
        return ChaosExperiment(
            experiment_id=f"{template.experiment_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name=template.name,
            description=template.description,
            failure_type=template.failure_type,
            target_component=template.target_component,
            duration=template.duration,
            intensity=template.intensity,
            parameters=template.parameters.copy(),
            hypothesis=template.hypothesis,
            success_criteria=template.success_criteria.copy(),
            rollback_strategy=template.rollback_strategy
        )
    
    async def _save_experiment_results(self, experiment: ChaosExperiment):
        """Save experiment results to file"""
        results_dir = Path("tests/chaos/results")
        results_dir.mkdir(exist_ok=True)
        
        result_file = results_dir / f"{experiment.experiment_id}_results.json"
        
        with open(result_file, 'w') as f:
            json.dump({
                'experiment': asdict(experiment),
                'timestamp': datetime.now().isoformat()
            }, f, indent=2, default=str)
        
        logger.info(f"Saved experiment results to: {result_file}")
    
    async def _send_experiment_notifications(self, experiment: ChaosExperiment, schedule: ChaosSchedule):
        """Send notifications about experiment completion"""
        if not schedule.notification_channels:
            return
        
        for handler in self.notification_handlers:
            try:
                await handler(experiment, schedule)
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
    
    async def _send_failure_notification(self, schedule: ChaosSchedule, error: str):
        """Send notification about experiment failure"""
        logger.info(f"Sending failure notification for: {schedule.experiment_template.name}")
        # Implementation would depend on notification channels
    
    async def _send_email_notification(self, experiment: ChaosExperiment, schedule: ChaosSchedule):
        """Send email notification"""
        logger.info(f"Email notification: Experiment {experiment.name} completed with status {experiment.status.value}")
    
    async def _send_slack_notification(self, experiment: ChaosExperiment, schedule: ChaosSchedule):
        """Send Slack notification"""
        logger.info(f"Slack notification: Experiment {experiment.name} completed with status {experiment.status.value}")
    
    async def _send_webhook_notification(self, experiment: ChaosExperiment, schedule: ChaosSchedule):
        """Send webhook notification"""
        logger.info(f"Webhook notification: Experiment {experiment.name} completed with status {experiment.status.value}")
    
    def create_game_day(self, game_day: ChaosGameDay):
        """Create a chaos game day event"""
        logger.info(f"Creating chaos game day: {game_day.name}")
        self.game_days[game_day.game_day_id] = game_day
    
    async def execute_game_day(self, game_day_id: str) -> Dict[str, Any]:
        """Execute a chaos game day"""
        if game_day_id not in self.game_days:
            raise ValueError(f"Game day {game_day_id} not found")
        
        game_day = self.game_days[game_day_id]
        logger.info(f"Starting chaos game day: {game_day.name}")
        
        results = {
            'game_day_id': game_day_id,
            'start_time': datetime.now(),
            'experiment_results': [],
            'objectives_met': [],
            'lessons_learned': []
        }
        
        try:
            # Execute experiments in sequence or parallel based on configuration
            for experiment in game_day.experiments:
                logger.info(f"Executing game day experiment: {experiment.name}")
                
                experiment_results = await self.experiment_runner.run_experiment(experiment)
                results['experiment_results'].append({
                    'experiment_id': experiment.experiment_id,
                    'name': experiment.name,
                    'status': experiment.status.value,
                    'results': experiment_results
                })
                
                # Brief pause between experiments
                await asyncio.sleep(30)
            
            # Evaluate objectives
            results['objectives_met'] = self._evaluate_game_day_objectives(game_day, results)
            
        except Exception as e:
            logger.error(f"Game day execution failed: {e}")
            results['error'] = str(e)
        
        finally:
            results['end_time'] = datetime.now()
            results['duration'] = (results['end_time'] - results['start_time']).total_seconds()
        
        # Generate game day report
        await self._generate_game_day_report(game_day, results)
        
        return results
    
    def _evaluate_game_day_objectives(self, game_day: ChaosGameDay, results: Dict[str, Any]) -> List[str]:
        """Evaluate if game day objectives were met"""
        objectives_met = []
        
        # Simple evaluation based on experiment success
        successful_experiments = sum(1 for r in results['experiment_results'] 
                                   if r['status'] == 'completed')
        total_experiments = len(results['experiment_results'])
        
        if successful_experiments == total_experiments:
            objectives_met.append("All experiments completed successfully")
        
        if successful_experiments / total_experiments >= 0.8:
            objectives_met.append("80% or more experiments succeeded")
        
        return objectives_met
    
    async def _generate_game_day_report(self, game_day: ChaosGameDay, results: Dict[str, Any]):
        """Generate chaos game day report"""
        report = f"""
# Chaos Game Day Report: {game_day.name}

## Event Details
- **Game Day ID:** {game_day.game_day_id}
- **Description:** {game_day.description}
- **Start Time:** {results['start_time']}
- **Duration:** {results.get('duration', 0):.2f} seconds
- **Participants:** {', '.join(game_day.participants)}

## Objectives
"""
        for objective in game_day.objectives:
            report += f"- {objective}\n"
        
        report += "\n## Experiment Results\n"
        
        for exp_result in results['experiment_results']:
            status_emoji = "✅" if exp_result['status'] == 'completed' else "❌"
            report += f"- {status_emoji} **{exp_result['name']}:** {exp_result['status']}\n"
        
        report += "\n## Objectives Met\n"
        for objective in results['objectives_met']:
            report += f"- ✅ {objective}\n"
        
        report += "\n## Success Criteria\n"
        for criteria in game_day.success_criteria:
            report += f"- {criteria}\n"
        
        # Save report
        reports_dir = Path("tests/chaos/game_day_reports")
        reports_dir.mkdir(exist_ok=True)
        
        report_file = reports_dir / f"{game_day.game_day_id}_report.md"
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"Game day report saved to: {report_file}")
    
    async def run_scheduler(self):
        """Run the chaos experiment scheduler"""
        logger.info("Starting chaos experiment scheduler")
        
        while True:
            schedule.run_pending()
            await asyncio.sleep(60)  # Check every minute
    
    def get_experiment_statistics(self) -> Dict[str, Any]:
        """Get statistics about chaos experiments"""
        total_experiments = len(self.experiment_history)
        
        if total_experiments == 0:
            return {'total_experiments': 0}
        
        successful_experiments = sum(1 for exp in self.experiment_history 
                                   if exp.status == ChaosExperimentStatus.COMPLETED)
        
        failed_experiments = sum(1 for exp in self.experiment_history 
                               if exp.status == ChaosExperimentStatus.FAILED)
        
        # Calculate average duration
        completed_experiments = [exp for exp in self.experiment_history 
                               if exp.status == ChaosExperimentStatus.COMPLETED and exp.results]
        
        avg_duration = 0
        if completed_experiments:
            total_duration = sum(exp.results.get('experiment_duration', 0) 
                               for exp in completed_experiments)
            avg_duration = total_duration / len(completed_experiments)
        
        # Failure type distribution
        failure_type_counts = {}
        for exp in self.experiment_history:
            failure_type = exp.failure_type.value
            failure_type_counts[failure_type] = failure_type_counts.get(failure_type, 0) + 1
        
        return {
            'total_experiments': total_experiments,
            'successful_experiments': successful_experiments,
            'failed_experiments': failed_experiments,
            'success_rate': (successful_experiments / total_experiments) * 100,
            'average_duration': avg_duration,
            'failure_type_distribution': failure_type_counts,
            'active_experiments': len(self.active_experiments),
            'scheduled_experiments': len(self.scheduled_experiments)
        }

# Predefined chaos schedules
class ChaosScheduleLibrary:
    """Library of predefined chaos schedules"""
    
    @staticmethod
    def daily_resilience_check() -> ChaosSchedule:
        """Daily resilience check schedule"""
        return ChaosSchedule(
            schedule_id="daily_resilience",
            experiment_template=ChaosExperimentLibrary.network_latency_experiment(),
            cron_expression="0 2 * * *",  # Daily at 2 AM
            enabled=True,
            max_concurrent=1,
            retry_count=2,
            notification_channels=['email', 'slack'],
            environment_filters=['staging', 'development']
        )
    
    @staticmethod
    def weekly_stress_test() -> ChaosSchedule:
        """Weekly comprehensive stress test"""
        return ChaosSchedule(
            schedule_id="weekly_stress",
            experiment_template=ChaosExperimentLibrary.memory_pressure_experiment(),
            cron_expression="0 1 * * 0",  # Weekly on Sunday at 1 AM
            enabled=True,
            max_concurrent=1,
            retry_count=1,
            notification_channels=['email'],
            environment_filters=['staging']
        )
    
    @staticmethod
    def monthly_game_day() -> ChaosGameDay:
        """Monthly chaos game day"""
        return ChaosGameDay(
            game_day_id="monthly_chaos_game_day",
            name="Monthly Chaos Engineering Game Day",
            description="Comprehensive chaos engineering exercise to test system resilience",
            start_time=datetime.now().replace(day=1, hour=10, minute=0, second=0, microsecond=0),
            duration=240,  # 4 hours
            experiments=[
                ChaosExperimentLibrary.network_latency_experiment(),
                ChaosExperimentLibrary.service_crash_experiment(),
                ChaosExperimentLibrary.memory_pressure_experiment(),
                ChaosExperimentLibrary.network_partition_experiment()
            ],
            participants=[
                "DevOps Team",
                "Backend Engineers",
                "Site Reliability Engineers",
                "Product Team"
            ],
            objectives=[
                "Validate system resilience under various failure conditions",
                "Test incident response procedures",
                "Identify system weaknesses and improvement opportunities",
                "Train team on chaos engineering practices"
            ],
            success_criteria=[
                "All experiments complete without system-wide outages",
                "Recovery time for each failure is under 5 minutes",
                "No data loss occurs during any experiment",
                "Team successfully follows incident response procedures"
            ]
        )

if __name__ == "__main__":
    async def main():
        """Main chaos automation execution"""
        print("🤖 Chaos Engineering Automation")
        print("=" * 50)
        
        automation = ChaosAutomation()
        
        # Schedule some experiments
        automation.schedule_experiment(ChaosScheduleLibrary.daily_resilience_check())
        automation.schedule_experiment(ChaosScheduleLibrary.weekly_stress_test())
        
        # Create a game day
        game_day = ChaosScheduleLibrary.monthly_game_day()
        automation.create_game_day(game_day)
        
        print("Chaos automation configured:")
        print(f"- Scheduled experiments: {len(automation.scheduled_experiments)}")
        print(f"- Game days: {len(automation.game_days)}")
        
        # Get statistics
        stats = automation.get_experiment_statistics()
        print(f"- Total experiments run: {stats['total_experiments']}")
        
        return True
    
    asyncio.run(main())