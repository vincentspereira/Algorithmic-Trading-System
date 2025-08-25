"""
Multi-channel notification system for dependency monitoring alerts.
Handles notifications through Slack, Teams, Email, and other channels.
"""

import json
import logging
import os
import smtplib
from dataclasses import dataclass
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional, Set

import requests
from jinja2 import Environment, FileSystemLoader

from .dependency_monitor import DependencyStatus, VulnerabilityInfo, UpdateInfo

logger = logging.getLogger(__name__)

@dataclass
class NotificationChannel:
    """Configuration for a notification channel"""
    enabled: bool
    config: Dict

@dataclass
class NotificationConfig:
    """Overall notification configuration"""
    slack: NotificationChannel
    teams: NotificationChannel
    email: NotificationChannel
    notification_levels: Dict[str, str]

class NotificationManager:
    """Manages notifications across multiple channels"""
    
    def __init__(
        self,
        config_path: str,
        template_dir: str = "templates"
    ):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.template_env = Environment(
            loader=FileSystemLoader(template_dir)
        )
        self.sent_notifications: Set[str] = set()
        
    def _load_config(self) -> NotificationConfig:
        """Load notification configuration"""
        with open(self.config_path) as f:
            config = json.load(f)
            
        return NotificationConfig(
            slack=NotificationChannel(
                enabled=config["notification_channels"]["slack"]["enabled"],
                config=config["notification_channels"]["slack"]
            ),
            teams=NotificationChannel(
                enabled=config["notification_channels"]["teams"]["enabled"],
                config=config["notification_channels"]["teams"]
            ),
            email=NotificationChannel(
                enabled=config["notification_channels"]["email"]["enabled"],
                config=config["notification_channels"]["email"]
            ),
            notification_levels=config.get("notification_levels", {})
        )
        
    def _get_notification_level(
        self,
        issue_type: str,
        tier: str
    ) -> str:
        """Get notification level for an issue"""
        if issue_type == "vulnerability":
            return "critical"
        elif issue_type == "breaking_change" and tier in ("tier1", "tier2"):
            return "high"
        elif issue_type == "error" and tier == "tier1":
            return "high"
        return "normal"
        
    def _should_notify(
        self,
        issue_id: str,
        level: str
    ) -> bool:
        """Check if notification should be sent"""
        if issue_id in self.sent_notifications:
            return False
            
        self.sent_notifications.add(issue_id)
        return True
        
    def send_slack_notification(
        self,
        channel: str,
        message: str,
        level: str = "normal"
    ) -> bool:
        """Send notification to Slack"""
        try:
            webhook_url = os.getenv("SLACK_WEBHOOK_URL")
            if not webhook_url:
                logger.error("SLACK_WEBHOOK_URL not set")
                return False
                
            color = {
                "critical": "#FF0000",
                "high": "#FFA500",
                "normal": "#36A64F"
            }.get(level, "#36A64F")
            
            payload = {
                "channel": channel,
                "attachments": [
                    {
                        "color": color,
                        "text": message,
                        "footer": "Dependency Monitor",
                        "ts": datetime.utcnow().timestamp()
                    }
                ]
            }
            
            response = requests.post(webhook_url, json=payload)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error sending Slack notification: {str(e)}")
            return False
            
    def send_teams_notification(
        self,
        channel: str,
        message: str,
        level: str = "normal"
    ) -> bool:
        """Send notification to Microsoft Teams"""
        try:
            webhook_url = os.getenv("TEAMS_WEBHOOK_URL")
            if not webhook_url:
                logger.error("TEAMS_WEBHOOK_URL not set")
                return False
                
            color = {
                "critical": "#FF0000",
                "high": "#FFA500",
                "normal": "#36A64F"
            }.get(level, "#36A64F")
            
            payload = {
                "type": "message",
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "content": {
                            "type": "AdaptiveCard",
                            "body": [
                                {
                                    "type": "TextBlock",
                                    "text": message,
                                    "wrap": True,
                                    "color": color
                                }
                            ],
                            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                            "version": "1.0"
                        }
                    }
                ]
            }
            
            response = requests.post(webhook_url, json=payload)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error sending Teams notification: {str(e)}")
            return False
            
    def send_email_notification(
        self,
        recipients: List[str],
        subject: str,
        message: str,
        level: str = "normal"
    ) -> bool:
        """Send email notification"""
        try:
            smtp_host = os.getenv("SMTP_HOST")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER")
            smtp_pass = os.getenv("SMTP_PASS")
            
            if not all([smtp_host, smtp_user, smtp_pass]):
                logger.error("SMTP configuration not complete")
                return False
                
            msg = MIMEMultipart()
            msg["From"] = smtp_user
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = f"[{level.upper()}] {subject}"
            
            # Create HTML message
            template = self.template_env.get_template("email_notification.html")
            html = template.render(
                message=message,
                level=level,
                timestamp=datetime.utcnow().isoformat()
            )
            
            msg.attach(MIMEText(html, "html"))
            
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
                
            return True
            
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            return False
            
    def format_notification(
        self,
        issue: Dict,
        template_name: str
    ) -> str:
        """Format notification message using template"""
        template = self.template_env.get_template(template_name)
        return template.render(**issue)
        
    def notify_issue(
        self,
        issue: Dict
    ) -> bool:
        """Send notification for an issue across all channels"""
        issue_id = f"{issue['dependency']}:{issue['type']}"
        level = self._get_notification_level(issue["type"], issue["tier"])
        
        if not self._should_notify(issue_id, level):
            return False
            
        success = True
        
        # Format messages for each channel
        slack_msg = self.format_notification(issue, "slack_notification.j2")
        teams_msg = self.format_notification(issue, "teams_notification.j2")
        email_msg = self.format_notification(issue, "email_notification.j2")
        
        # Send Slack notification
        if self.config.slack.enabled:
            channel = self.config.slack.config["channels"][issue["tier"]]
            if not self.send_slack_notification(channel, slack_msg, level):
                success = False
                
        # Send Teams notification
        if self.config.teams.enabled:
            channel = self.config.teams.config["channels"][issue["tier"]]
            if not self.send_teams_notification(channel, teams_msg, level):
                success = False
                
        # Send email notification
        if self.config.email.enabled:
            recipients = self.config.email.config["lists"][issue["tier"]]
            subject = f"Dependency Issue: {issue['dependency']}"
            if not self.send_email_notification(
                recipients,
                subject,
                email_msg,
                level
            ):
                success = False
                
        return success
        
    def notify_weekly_summary(
        self,
        status_updates: List[DependencyStatus]
    ) -> bool:
        """Send weekly summary notification"""
        try:
            # Group updates by tier
            updates_by_tier = {}
            for status in status_updates:
                if status.tier not in updates_by_tier:
                    updates_by_tier[status.tier] = []
                updates_by_tier[status.tier].append(status)
                
            # Generate summary
            template = self.template_env.get_template("weekly_summary.j2")
            summary = template.render(
                updates_by_tier=updates_by_tier,
                timestamp=datetime.utcnow().isoformat()
            )
            
            success = True
            
            # Send to all channels
            if self.config.slack.enabled:
                for tier, channel in self.config.slack.config["channels"].items():
                    if tier in updates_by_tier:
                        if not self.send_slack_notification(
                            channel,
                            summary,
                            "normal"
                        ):
                            success = False
                            
            if self.config.teams.enabled:
                for tier, channel in self.config.teams.config["channels"].items():
                    if tier in updates_by_tier:
                        if not self.send_teams_notification(
                            channel,
                            summary,
                            "normal"
                        ):
                            success = False
                            
            if self.config.email.enabled:
                for tier, recipients in self.config.email.config["lists"].items():
                    if tier in updates_by_tier:
                        if not self.send_email_notification(
                            recipients,
                            "Weekly Dependency Status Summary",
                            summary,
                            "normal"
                        ):
                            success = False
                            
            return success
            
        except Exception as e:
            logger.error(f"Error sending weekly summary: {str(e)}")
            return False
            
def main():
    """Main entry point for notification system"""
    logging.basicConfig(level=logging.INFO)
    
    config_path = os.getenv(
        "NOTIFICATION_CONFIG",
        "config/repository_management.json"
    )
    template_dir = os.getenv(
        "TEMPLATE_DIR",
        "templates"
    )
    
    manager = NotificationManager(config_path, template_dir)
    
    # Example notification
    issue = {
        "dependency": "TestRepo",
        "tier": "tier1",
        "type": "vulnerability",
        "details": {
            "severity": "CRITICAL",
            "description": "Security vulnerability detected"
        }
    }
    
    if manager.notify_issue(issue):
        logger.info("Successfully sent notifications")
    else:
        logger.error("Failed to send some notifications")
        
if __name__ == "__main__":
    main()
