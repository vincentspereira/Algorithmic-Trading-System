#!/usr/bin/env python3
"""
Multi-Channel Notification System
Provides comprehensive notification capabilities across multiple channels
for the Algorithmic Trading System's dependency management.
"""

import json
import requests
import smtplib
import sys
import os
from typing import Dict, List, Optional, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging
from datetime import datetime, timedelta, timezone
import time
from dataclasses import dataclass, asdict
from enum import Enum

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(Enum):
    """Types of alerts."""
    DEPENDENCY_UPDATE = "dependency_update"
    SECURITY_VULNERABILITY = "security_vulnerability"
    BREAKING_CHANGE = "breaking_change"
    MONITORING_FAILURE = "monitoring_failure"
    WEEKLY_SUMMARY = "weekly_summary"
    SYSTEM_HEALTH = "system_health"

@dataclass
class Alert:
    """Alert data structure."""
    title: str
    message: str
    severity: AlertSeverity
    alert_type: AlertType
    timestamp: str
    details: Dict[str, Any]
    recipients: List[str]
    channels: List[str]

class MultiChannelNotifier:
    def __init__(self):
        self.notification_channels = {
            'teams': os.getenv('TEAMS_WEBHOOK'),
            'discord': os.getenv('DISCORD_WEBHOOK'),
            'slack': os.getenv('SLACK_WEBHOOK'),
            'email': os.getenv('ALERT_EMAIL_RECIPIENTS', '').split(','),
            'github_issues': os.getenv('GITHUB_TOKEN')
        }
        self.smtp_config = {
            'server': os.getenv('SMTP_SERVER', 'localhost'),
            'port': int(os.getenv('SMTP_PORT', '587')),
            'username': os.getenv('SMTP_USERNAME'),
            'password': os.getenv('SMTP_PASSWORD'),
            'from_email': os.getenv('FROM_EMAIL', 'alerts@company.com')
        }
        self.github_repo = os.getenv('GITHUB_REPOSITORY', 'vincentspereira/Algorithmic-Trading-System')
        self.github_api_url = 'https://api.github.com'
    
    def send_teams_notification(self, alert: Alert) -> bool:
        """Send notification to Microsoft Teams."""
        teams_webhook = self.notification_channels.get('teams')
        if not teams_webhook:
            logger.warning("Teams webhook not configured")
            return False
            
        try:
            # Determine color based on severity
            color_map = {
                AlertSeverity.LOW: '0078D4',      # Blue
                AlertSeverity.MEDIUM: 'FFA500',   # Orange
                AlertSeverity.HIGH: 'FF0000',     # Red
                AlertSeverity.CRITICAL: '8B0000'  # Dark Red
            }
            color = color_map.get(alert.severity, '0078D4')
            
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "summary": alert.title,
                "themeColor": color,
                "title": alert.title,
                "sections": [{
                    "activityTitle": alert.title,
                    "activitySubtitle": f"Severity: {alert.severity.value} | Type: {alert.alert_type.value}",
                    "activityImage": "https://raw.githubusercontent.com/microsoft/teams-ui-component-library/main/assets/icons/alert.svg",
                    "text": alert.message,
                    "facts": [
                        {
                            "name": "Timestamp",
                            "value": alert.timestamp
                        },
                        {
                            "name": "Channels",
                            "value": ", ".join(alert.channels)
                        }
                    ]
                }]
            }
            
            # Add details if present
            if alert.details:
                payload["sections"][0]["facts"].append({
                    "name": "Details",
                    "value": json.dumps(alert.details, indent=2)
                })
            
            response = requests.post(teams_webhook, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send Teams notification: {e}")
            return False
    
    def send_discord_notification(self, alert: Alert) -> bool:
        """Send notification to Discord."""
        discord_webhook = self.notification_channels.get('discord')
        if not discord_webhook:
            logger.warning("Discord webhook not configured")
            return False
            
        try:
            # Determine color based on severity
            color_map = {
                AlertSeverity.LOW: 3447003,      # Blue
                AlertSeverity.MEDIUM: 15105570,  # Orange
                AlertSeverity.HIGH: 15548997,    # Red
                AlertSeverity.CRITICAL: 10038562 # Dark Red
            }
            color = color_map.get(alert.severity, 3447003)
            
            payload = {
                "embeds": [{
                    "title": alert.title,
                    "description": alert.message,
                    "color": color,
                    "timestamp": alert.timestamp,
                    "fields": [
                        {
                            "name": "Severity",
                            "value": alert.severity.value,
                            "inline": True
                        },
                        {
                            "name": "Type",
                            "value": alert.alert_type.value,
                            "inline": True
                        },
                        {
                            "name": "Channels",
                            "value": ", ".join(alert.channels),
                            "inline": True
                        }
                    ]
                }]
            }
            
            # Add details if present
            if alert.details:
                payload["embeds"][0]["fields"].append({
                    "name": "Details",
                    "value": f"```json\n{json.dumps(alert.details, indent=2)[:1000]}\n```"  # Limit size
                })
            
            response = requests.post(discord_webhook, json=payload, timeout=10)
            return response.status_code == 204
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False
    
    def send_slack_notification(self, alert: Alert) -> bool:
        """Send notification to Slack."""
        slack_webhook = self.notification_channels.get('slack')
        if not slack_webhook:
            logger.warning("Slack webhook not configured")
            return False
            
        try:
            # Determine color based on severity
            color_map = {
                AlertSeverity.LOW: "good",        # Green
                AlertSeverity.MEDIUM: "warning",  # Yellow
                AlertSeverity.HIGH: "danger",     # Red
                AlertSeverity.CRITICAL: "#8B0000" # Dark Red
            }
            color = color_map.get(alert.severity, "good")
            
            payload = {
                "attachments": [{
                    "color": color,
                    "title": alert.title,
                    "text": alert.message,
                    "fields": [
                        {
                            "title": "Severity",
                            "value": alert.severity.value,
                            "short": True
                        },
                        {
                            "title": "Type",
                            "value": alert.alert_type.value,
                            "short": True
                        },
                        {
                            "title": "Timestamp",
                            "value": alert.timestamp,
                            "short": True
                        }
                    ],
                    "ts": int(time.time())
                }]
            }
            
            # Add details if present
            if alert.details:
                payload["attachments"][0]["fields"].append({
                    "title": "Details",
                    "value": f"```{json.dumps(alert.details, indent=2)[:1000]}```",  # Limit size
                    "short": False
                })
            
            response = requests.post(slack_webhook, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False
    
    def send_email_notification(self, alert: Alert) -> bool:
        """Send notification via email."""
        email_recipients = self.notification_channels.get('email', [])
        if not email_recipients or not any(email_recipients):
            logger.warning("Email recipients not configured")
            return False
            
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config['from_email']
            msg['To'] = ", ".join([email for email in email_recipients if email])
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"
            
            # Create email body
            body_text = f"""
{alert.title}

Severity: {alert.severity.value}
Type: {alert.alert_type.value}
Timestamp: {alert.timestamp}
Channels: {', '.join(alert.channels)}

Message:
{alert.message}

"""
            
            if alert.details:
                body_text += f"""
Details:
{json.dumps(alert.details, indent=2)}
"""
            
            body = MIMEText(body_text, 'plain')
            msg.attach(body)
            
            # Connect to SMTP server and send
            server = smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port'])
            server.starttls()
            if self.smtp_config['username'] and self.smtp_config['password']:
                server.login(self.smtp_config['username'], self.smtp_config['password'])
            
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    def create_github_issue(self, alert: Alert) -> Optional[str]:
        """Create a GitHub issue for the alert."""
        github_token = self.notification_channels.get('github_issues')
        if not github_token:
            logger.warning("GitHub token not configured")
            return None
            
        try:
            # Create issue title and body
            issue_title = f"[{alert.severity.value.upper()}] {alert.title}"
            
            issue_body = f"""
**Alert Details:**
- Severity: {alert.severity.value}
- Type: {alert.alert_type.value}
- Timestamp: {alert.timestamp}
- Channels: {', '.join(alert.channels)}

**Message:**
{alert.message}

**Details:**
```
{json.dumps(alert.details, indent=2) if alert.details else "No additional details"}
```

**Recipients:**
{', '.join(alert.recipients) if alert.recipients else "No specific recipients"}

*This issue was automatically created by the Dependency Management Notification System.*
"""
            
            # Create GitHub issue
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            payload = {
                'title': issue_title,
                'body': issue_body,
                'labels': [alert.severity.value, alert.alert_type.value, 'automated']
            }
            
            url = f'{self.github_api_url}/repos/{self.github_repo}/issues'
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 201:
                issue_data = response.json()
                return issue_data.get('html_url')
            else:
                logger.error(f"Failed to create GitHub issue: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to create GitHub issue: {e}")
            return None
    
    def send_notification(self, alert: Alert) -> Dict[str, bool]:
        """Send notification through all specified channels."""
        results = {}
        
        # Send to specified channels
        for channel in alert.channels:
            if channel == 'teams' and self.notification_channels.get('teams'):
                results['teams'] = self.send_teams_notification(alert)
            elif channel == 'discord' and self.notification_channels.get('discord'):
                results['discord'] = self.send_discord_notification(alert)
            elif channel == 'slack' and self.notification_channels.get('slack'):
                results['slack'] = self.send_slack_notification(alert)
            elif channel == 'email' and self.notification_channels.get('email'):
                results['email'] = self.send_email_notification(alert)
            elif channel == 'github_issues' and self.notification_channels.get('github_issues'):
                issue_url = self.create_github_issue(alert)
                results['github_issues'] = bool(issue_url)
                if issue_url:
                    logger.info(f"GitHub issue created: {issue_url}")
        
        return results
    
    def send_weekly_summary(self, summary_data: Dict[str, Any]) -> Dict[str, bool]:
        """Send weekly dependency management summary."""
        # Create alert for weekly summary
        alert = Alert(
            title="Weekly Dependency Management Summary",
            message="Comprehensive report of dependency updates, security vulnerabilities, and system health.",
            severity=AlertSeverity.MEDIUM,
            alert_type=AlertType.WEEKLY_SUMMARY,
            timestamp=datetime.now(timezone.utc).isoformat(),
            details=summary_data,
            recipients=[],
            channels=['teams', 'email']  # Send to Teams and email for summaries
        )
        
        return self.send_notification(alert)
    
    def send_critical_alert(self, title: str, message: str, details: Dict[str, Any] = None) -> Dict[str, bool]:
        """Send critical alert to all channels."""
        alert = Alert(
            title=title,
            message=message,
            severity=AlertSeverity.CRITICAL,
            alert_type=AlertType.SECURITY_VULNERABILITY,
            timestamp=datetime.now(timezone.utc).isoformat(),
            details=details or {},
            recipients=[],
            channels=['teams', 'discord', 'slack', 'email']  # All channels for critical alerts
        )
        
        return self.send_notification(alert)
    
    def send_security_alert(self, vulnerability_data: Dict[str, Any]) -> Dict[str, bool]:
        """Send security vulnerability alert."""
        severity_map = {
            'critical': AlertSeverity.CRITICAL,
            'high': AlertSeverity.HIGH,
            'medium': AlertSeverity.MEDIUM,
            'low': AlertSeverity.LOW
        }
        
        severity = severity_map.get(vulnerability_data.get('severity', 'medium').lower(), AlertSeverity.MEDIUM)
        
        alert = Alert(
            title=f"Security Vulnerability Detected: {vulnerability_data.get('package', 'Unknown Package')}",
            message=f"Vulnerability {vulnerability_data.get('id', 'Unknown')} found in {vulnerability_data.get('package', 'unknown package')} version {vulnerability_data.get('version', 'unknown')}",
            severity=severity,
            alert_type=AlertType.SECURITY_VULNERABILITY,
            timestamp=datetime.now(timezone.utc).isoformat(),
            details=vulnerability_data,
            recipients=[],
            channels=['teams', 'discord', 'email']  # Security alerts to key channels
        )
        
        return self.send_notification(alert)
    
    def send_breaking_change_alert(self, change_data: Dict[str, Any]) -> Dict[str, bool]:
        """Send breaking change alert."""
        alert = Alert(
            title=f"Breaking Change Detected: {change_data.get('dependency', 'Unknown Dependency')}",
            message=f"Breaking changes detected in {change_data.get('dependency', 'unknown dependency')} from version {change_data.get('from_version', 'unknown')} to {change_data.get('to_version', 'unknown')}",
            severity=AlertSeverity.HIGH,
            alert_type=AlertType.BREAKING_CHANGE,
            timestamp=datetime.now(timezone.utc).isoformat(),
            details=change_data,
            recipients=[],
            channels=['teams', 'discord', 'email']  # Breaking changes to key channels
        )
        
        return self.send_notification(alert)

def load_notification_config() -> Dict[str, Any]:
    """Load notification configuration from file."""
    config_file = 'dependency_management/notifications/notification_config.json'
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading notification config: {e}")
    return {}

def main():
    """Main function to demonstrate notification system."""
    print("Starting Multi-Channel Notification System...")
    
    notifier = MultiChannelNotifier()
    
    # Demonstrate different types of notifications
    
    # 1. Critical security alert
    print("\n=== SENDING CRITICAL SECURITY ALERT ===")
    security_results = notifier.send_critical_alert(
        "Critical Security Vulnerability Found",
        "A critical vulnerability (CVE-2023-XXXX) has been detected in the NautilusTrader dependency.",
        {
            "package": "nautilus_trader",
            "current_version": "1.2.3",
            "vulnerable_version": "< 1.2.5",
            "cvss_score": 9.8,
            "recommendation": "Update to version 1.2.5 or later immediately",
            "affected_services": ["trading_engine", "backtesting_service"]
        }
    )
    
    print("Security alert sent to:")
    for channel, success in security_results.items():
        status = "✓ Success" if success else "✗ Failed"
        print(f"  {channel}: {status}")
    
    # 2. Breaking change alert
    print("\n=== SENDING BREAKING CHANGE ALERT ===")
    breaking_results = notifier.send_breaking_change_alert({
        "dependency": "kafka-python",
        "from_version": "2.0.2",
        "to_version": "3.0.0",
        "breaking_changes": [
            "API signature changes in KafkaConsumer",
            "Removed deprecated methods",
            "Changed default configuration values"
        ],
        "affected_services": ["market_data_service", "order_processor"],
        "migration_required": True,
        "estimated_effort": "4 hours"
    })
    
    print("Breaking change alert sent to:")
    for channel, success in breaking_results.items():
        status = "✓ Success" if success else "✗ Failed"
        print(f"  {channel}: {status}")
    
    # 3. Weekly summary
    print("\n=== SENDING WEEKLY SUMMARY ===")
    summary_results = notifier.send_weekly_summary({
        "period": "2023-10-01 to 2023-10-07",
        "updates_available": 15,
        "critical_updates": 2,
        "security_vulnerabilities": 3,
        "breaking_changes": 1,
        "system_health": "Good",
        "next_scheduled_scan": "2023-10-14 06:00 UTC"
    })
    
    print("Weekly summary sent to:")
    for channel, success in summary_results.items():
        status = "✓ Success" if success else "✗ Failed"
        print(f"  {channel}: {status}")
    
    # 4. Custom alert
    print("\n=== SENDING CUSTOM ALERT ===")
    custom_alert = Alert(
        title="Dependency Monitoring System Health Check",
        message="All monitoring systems are operational and up to date.",
        severity=AlertSeverity.LOW,
        alert_type=AlertType.SYSTEM_HEALTH,
        timestamp=datetime.now(timezone.utc).isoformat(),
        details={
            "monitoring_systems": ["GitHub Actions", "Renovate", "Dependabot"],
            "status": "All systems operational",
            "last_check": datetime.now(timezone.utc).isoformat()
        },
        recipients=["devops@company.com"],
        channels=['teams', 'email']
    )
    
    custom_results = notifier.send_notification(custom_alert)
    
    print("Custom alert sent to:")
    for channel, success in custom_results.items():
        status = "✓ Success" if success else "✗ Failed"
        print(f"  {channel}: {status}")
    
    print("\nMulti-Channel Notification System demonstration completed.")
    return 0

if __name__ == "__main__":
    sys.exit(main())