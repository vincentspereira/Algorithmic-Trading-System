"""
Notification Service for Algorithmic Trading System
Handles multi-channel notifications for dependency monitoring
"""

import logging
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any
import json
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for sending multi-channel notifications"""
    
    def __init__(self):
        self.slack_webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        self.teams_webhook_url = os.getenv('TEAMS_WEBHOOK_URL')
        self.smtp_server = os.getenv('SMTP_SERVER')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.email_user = os.getenv('EMAIL_USER')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        
    def send_slack_notification(self, message: str, channel: str = '#dependencies') -> bool:
        """Send notification to Slack"""
        if not self.slack_webhook_url:
            logger.warning("Slack webhook URL not configured")
            return False
            
        try:
            payload = {
                "channel": channel,
                "text": message,
                "username": "DependencyMonitor",
                "icon_emoji": ":robot_face:"
            }
            
            response = requests.post(self.slack_webhook_url, json=payload)
            response.raise_for_status()
            logger.info("Slack notification sent successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {str(e)}")
            return False
    
    def send_teams_notification(self, message: str, title: str = "Dependency Monitoring Alert") -> bool:
        """Send notification to Microsoft Teams"""
        if not self.teams_webhook_url:
            logger.warning("Teams webhook URL not configured")
            return False
            
        try:
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": "0076D7",
                "summary": title,
                "sections": [{
                    "activityTitle": title,
                    "activitySubtitle": f"Alert generated at {datetime.now(timezone.utc).isoformat()}",
                    "activityImage": "https://teamsnodesample.azurewebsites.net/static/img/image5.png",
                    "facts": [
                        {
                            "name": "Category",
                            "value": "Dependency Monitoring"
                        },
                        {
                            "name": "Message",
                            "value": message
                        }
                    ],
                    "markdown": True
                }]
            }
            
            response = requests.post(self.teams_webhook_url, json=payload)
            response.raise_for_status()
            logger.info("Teams notification sent successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to send Teams notification: {str(e)}")
            return False
    
    def send_email_notification(self, subject: str, body: str, recipients: List[str]) -> bool:
        """Send email notification"""
        if not all([self.smtp_server, self.email_user, self.email_password]):
            logger.warning("Email configuration not complete")
            return False
            
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_user
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_user, self.email_password)
            text = msg.as_string()
            server.sendmail(self.email_user, recipients, text)
            server.quit()
            
            logger.info(f"Email notification sent to {', '.join(recipients)}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
            return False
    
    def send_github_issue(self, title: str, body: str, labels: List[str] = None) -> bool:
        """Create GitHub issue for critical alerts"""
        github_token = os.getenv('GITHUB_TOKEN')
        repo_owner = os.getenv('GITHUB_REPO_OWNER')
        repo_name = os.getenv('GITHUB_REPO_NAME')
        
        if not all([github_token, repo_owner, repo_name]):
            logger.warning("GitHub configuration not complete")
            return False
            
        try:
            url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues"
            headers = {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            payload = {
                "title": title,
                "body": body,
                "labels": labels or ["dependency", "monitoring"]
            }
            
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            logger.info("GitHub issue created successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to create GitHub issue: {str(e)}")
            return False
    
    def send_consolidated_report(self, report_data: Dict[str, Any], recipients: List[str]) -> bool:
        """Send consolidated weekly report via multiple channels"""
        try:
            # Generate report content
            report_content = self._generate_report_content(report_data)
            
            # Send to all configured channels
            results = []
            
            # Email report
            if self.email_user:
                subject = f"Weekly Dependency Monitoring Report - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
                results.append(self.send_email_notification(subject, report_content, recipients))
            
            # Slack notification
            if self.slack_webhook_url:
                slack_message = f"Weekly Dependency Monitoring Report available. Key findings: {report_data.get('summary', 'See attached report')}"
                results.append(self.send_slack_notification(slack_message))
            
            # Teams notification
            if self.teams_webhook_url:
                teams_message = f"Weekly Dependency Monitoring Report available. Key findings: {report_data.get('summary', 'See attached report')}"
                results.append(self.send_teams_notification(teams_message, "Weekly Dependency Report"))
            
            return any(results)
        except Exception as e:
            logger.error(f"Failed to send consolidated report: {str(e)}")
            return False
    
    def _generate_report_content(self, report_data: Dict[str, Any]) -> str:
        """Generate formatted report content"""
        content = f"""
ALGORITHMIC TRADING SYSTEM - DEPENDENCY MONITORING REPORT
Generated: {datetime.now(timezone.utc).isoformat()}

SUMMARY:
{report_data.get('summary', 'No summary available')}

KEY METRICS:
{json.dumps(report_data.get('metrics', {}), indent=2)}

CRITICAL ISSUES:
{json.dumps(report_data.get('critical_issues', []), indent=2)}

RECOMMENDATIONS:
{json.dumps(report_data.get('recommendations', []), indent=2)}

For detailed information, please check the GitHub repository and Grafana dashboards.

---
This is an automated report from the Dependency Monitoring System.
"""
        return content
    
    def send_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Send alert based on severity level"""
        severity = alert_data.get('severity', 'info').lower()
        message = alert_data.get('message', '')
        component = alert_data.get('component', 'Unknown')
        
        try:
            # Determine channels based on severity
            channels = []
            if severity in ['critical', 'high']:
                channels = ['slack', 'teams', 'email', 'github']
            elif severity in ['medium', 'low']:
                channels = ['slack', 'email']
            else:
                channels = ['slack']
            
            results = []
            
            # Send to appropriate channels
            if 'slack' in channels and self.slack_webhook_url:
                slack_msg = f"[{severity.upper()}] {component}: {message}"
                results.append(self.send_slack_notification(slack_msg))
            
            if 'teams' in channels and self.teams_webhook_url:
                results.append(self.send_teams_notification(message, f"{severity.upper()} Alert - {component}"))
            
            if 'email' in channels and self.email_user:
                subject = f"[{severity.upper()}] Dependency Alert - {component}"
                results.append(self.send_email_notification(subject, message, [self.email_user]))
            
            if 'github' in channels:
                issue_title = f"[{severity.upper()}] {component} Issue Detected"
                results.append(self.send_github_issue(issue_title, message, ['dependency', 'alert', severity]))
            
            return any(results)
        except Exception as e:
            logger.error(f"Failed to send alert: {str(e)}")
            return False

# Global instance
notification_service = NotificationService()

def get_notification_service() -> NotificationService:
    """Get the global notification service instance"""
    return notification_service