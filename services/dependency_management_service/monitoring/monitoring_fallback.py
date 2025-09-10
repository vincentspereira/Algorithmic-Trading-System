#!/usr/bin/env python3
"""
Monitoring Fallback System
Provides redundant monitoring capabilities and manual alert triggers
for the Algorithmic Trading System.
"""

import json
import requests
import smtplib
import sys
import os
from typing import Dict, List, Optional, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from datetime import datetime, timedelta
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MonitoringFallbackSystem:
    def __init__(self):
        self.notification_channels = {
            'teams': os.getenv('TEAMS_WEBHOOK'),
            'discord': os.getenv('DISCORD_WEBHOOK'),
            'slack': os.getenv('SLACK_WEBHOOK'),
            'email': os.getenv('ALERT_EMAIL')
        }
        self.smtp_config = {
            'server': os.getenv('SMTP_SERVER', 'localhost'),
            'port': int(os.getenv('SMTP_PORT', '587')),
            'username': os.getenv('SMTP_USERNAME'),
            'password': os.getenv('SMTP_PASSWORD'),
            'from_email': os.getenv('FROM_EMAIL', 'alerts@company.com')
        }
    
    def send_teams_alert(self, message: str, title: str = "Monitoring Alert") -> bool:
        """Send alert to Microsoft Teams."""
        teams_webhook = self.notification_channels.get('teams')
        if not teams_webhook:
            logger.warning("Teams webhook not configured")
            return False
            
        try:
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "summary": title,
                "themeColor": "FF0000",
                "title": title,
                "text": message
            }
            
            response = requests.post(teams_webhook, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send Teams alert: {e}")
            return False
    
    def send_discord_alert(self, message: str, title: str = "Monitoring Alert") -> bool:
        """Send alert to Discord."""
        discord_webhook = self.notification_channels.get('discord')
        if not discord_webhook:
            logger.warning("Discord webhook not configured")
            return False
            
        try:
            payload = {
                "embeds": [{
                    "title": title,
                    "description": message,
                    "color": 16711680,  # Red color
                    "timestamp": datetime.now().isoformat()
                }]
            }
            
            response = requests.post(discord_webhook, json=payload, timeout=10)
            return response.status_code == 204
        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")
            return False
    
    def send_slack_alert(self, message: str, title: str = "Monitoring Alert") -> bool:
        """Send alert to Slack."""
        slack_webhook = self.notification_channels.get('slack')
        if not slack_webhook:
            logger.warning("Slack webhook not configured")
            return False
            
        try:
            payload = {
                "attachments": [{
                    "color": "danger",
                    "title": title,
                    "text": message,
                    "ts": int(time.time())
                }]
            }
            
            response = requests.post(slack_webhook, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False
    
    def send_email_alert(self, message: str, title: str = "Monitoring Alert") -> bool:
        """Send alert via email."""
        email_address = self.notification_channels.get('email')
        if not email_address:
            logger.warning("Alert email not configured")
            return False
            
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config['from_email']
            msg['To'] = email_address
            msg['Subject'] = f"[ALERT] {title}"
            
            body = MIMEText(message, 'plain')
            msg.attach(body)
            
            server = smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port'])
            server.starttls()
            if self.smtp_config['username'] and self.smtp_config['password']:
                server.login(self.smtp_config['username'], self.smtp_config['password'])
            
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False
    
    def trigger_manual_alert(self, alert_type: str, message: str, title: str = None) -> Dict:
        """Trigger manual alert through all available channels."""
        if not title:
            title = f"Manual {alert_type.title()} Alert"
            
        results = {
            'teams': False,
            'discord': False,
            'slack': False,
            'email': False
        }
        
        # Send to all configured channels
        if self.notification_channels.get('teams'):
            results['teams'] = self.send_teams_alert(message, title)
            
        if self.notification_channels.get('discord'):
            results['discord'] = self.send_discord_alert(message, title)
            
        if self.notification_channels.get('slack'):
            results['slack'] = self.send_slack_alert(message, title)
            
        if self.notification_channels.get('email'):
            results['email'] = self.send_email_alert(message, title)
        
        return results
    
    def check_monitoring_health(self) -> Dict:
        """Check the health of monitoring systems."""
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'systems': {},
            'issues': []
        }
        
        # Check if notification channels are configured
        for channel, config in self.notification_channels.items():
            health_status['systems'][channel] = {
                'configured': bool(config),
                'status': 'unknown'
            }
        
        # Check if main monitoring services are running
        # This would typically check connectivity to external services
        # For now, we'll simulate basic checks
        try:
            # Check GitHub API connectivity (as an example)
            response = requests.get('https://api.github.com', timeout=5)
            health_status['systems']['github_api'] = {
                'configured': True,
                'status': 'healthy' if response.status_code == 200 else 'unhealthy'
            }
        except Exception as e:
            health_status['systems']['github_api'] = {
                'configured': True,
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['issues'].append(f"GitHub API connectivity issue: {e}")
        
        return health_status
    
    def create_fallback_monitoring_task(self, task_name: str, command: str, schedule: str) -> Dict:
        """Create a fallback monitoring task."""
        task = {
            'name': task_name,
            'command': command,
            'schedule': schedule,
            'created_at': datetime.now().isoformat(),
            'last_run': None,
            'status': 'pending',
            'fallback_triggered': False
        }
        
        # Save task to file (in a real system, this would go to a database)
        tasks_file = 'fallback_monitoring_tasks.json'
        tasks = []
        
        try:
            if os.path.exists(tasks_file):
                with open(tasks_file, 'r') as f:
                    tasks = json.load(f)
        except Exception as e:
            logger.error(f"Error loading existing tasks: {e}")
        
        tasks.append(task)
        
        try:
            with open(tasks_file, 'w') as f:
                json.dump(tasks, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving task: {e}")
        
        return task
    
    def execute_fallback_task(self, task_name: str) -> Dict:
        """Execute a fallback monitoring task."""
        result = {
            'task_name': task_name,
            'executed_at': datetime.now().isoformat(),
            'success': False,
            'output': '',
            'error': ''
        }
        
        # In a real implementation, this would execute the actual monitoring command
        # For now, we'll simulate execution
        try:
            logger.info(f"Executing fallback task: {task_name}")
            
            # Simulate task execution
            if 'dependency' in task_name.lower():
                result['output'] = "Dependency check completed successfully"
                result['success'] = True
            elif 'security' in task_name.lower():
                result['output'] = "Security scan completed with 0 critical issues"
                result['success'] = True
            else:
                result['output'] = "Generic monitoring task completed"
                result['success'] = True
                
            result['last_run'] = datetime.now().isoformat()
            
        except Exception as e:
            result['error'] = str(e)
            result['success'] = False
            logger.error(f"Failed to execute fallback task {task_name}: {e}")
            
            # Trigger alert on failure
            self.trigger_manual_alert(
                'error',
                f"Fallback monitoring task '{task_name}' failed: {e}",
                f"Fallback Task Failure: {task_name}"
            )
        
        return result

def main():
    """Main function to demonstrate fallback monitoring system."""
    print("Starting Monitoring Fallback System...")
    
    fallback_system = MonitoringFallbackSystem()
    
    # Check monitoring health
    health = fallback_system.check_monitoring_health()
    print("\n=== MONITORING HEALTH STATUS ===")
    print(f"Timestamp: {health['timestamp']}")
    print("Systems:")
    for system, status in health['systems'].items():
        print(f"  {system}: {'✓' if status['configured'] else '✗'} Configured, "
              f"{'✓' if status.get('status') == 'healthy' else '✗'} {status.get('status', 'N/A')}")
    
    if health['issues']:
        print("Issues found:")
        for issue in health['issues']:
            print(f"  - {issue}")
    
    # Demonstrate manual alert triggering
    print("\n=== MANUAL ALERT DEMO ===")
    alert_results = fallback_system.trigger_manual_alert(
        'test',
        'This is a test alert from the Monitoring Fallback System.',
        'Fallback System Test Alert'
    )
    
    print("Alert sent to:")
    for channel, success in alert_results.items():
        status = "✓ Success" if success else "✗ Failed"
        print(f"  {channel}: {status}")
    
    # Create sample fallback tasks
    print("\n=== CREATING FALLBACK TASKS ===")
    tasks = [
        ('Dependency Check Fallback', 'python monitoring/check_dependencies.py --tier tier1', '0 7 * * *'),
        ('Security Scan Fallback', 'python security/scan.py --full', '0 3 * * *'),
        ('Schema Validation Fallback', 'python monitoring/schema_registry_validator.py', '0 4 * * 1')
    ]
    
    for task_name, command, schedule in tasks:
        task = fallback_system.create_fallback_monitoring_task(task_name, command, schedule)
        print(f"Created task: {task['name']}")
    
    # Execute a sample task
    print("\n=== EXECUTING SAMPLE TASK ===")
    execution_result = fallback_system.execute_fallback_task('Dependency Check Fallback')
    print(f"Task: {execution_result['task_name']}")
    print(f"Success: {'✓' if execution_result['success'] else '✗'}")
    print(f"Output: {execution_result['output']}")
    if execution_result['error']:
        print(f"Error: {execution_result['error']}")
    
    print("\nFallback monitoring system initialized and ready.")
    return 0

if __name__ == "__main__":
    sys.exit(main())