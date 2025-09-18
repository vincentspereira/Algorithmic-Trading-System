"""
Notification Service for Dependency Management System

Handles multi-channel notifications (Slack, Email, Teams) with different
priorities based on dependency tiers and issue severity.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import json
import logging
from typing import List, Dict, Optional
import os
from datetime import datetime, timezone
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiohttp
import asyncio
from pydantic import BaseModel
import jinja2

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationConfig(BaseModel):
    """Configuration for notification channels"""
    slack_webhook_url: Optional[str]
    teams_webhook_url: Optional[str]
    email_config: Optional[Dict[str, str]]
    notification_preferences: Dict[str, List[str]]  # user_id -> [channels]

from typing import Literal, ClassVar
from pydantic import BaseModel

class NotificationPriority(BaseModel):
    """Priority levels for notifications"""
    CRITICAL: ClassVar[str] = "critical"
    HIGH: ClassVar[str] = "high"
    MEDIUM: ClassVar[str] = "medium"
    LOW: ClassVar[str] = "low"

class NotificationPayload(BaseModel):
    """Data structure for notifications"""
    title: str
    message: str
    priority: str
    tier: int
    timestamp: datetime
    details: Dict
    recipients: List[str]

class NotificationService:
    """Handles notification distribution across multiple channels"""
    
    def __init__(self):
        self.config = self._load_config()
        self.template_env = self._setup_templates()
        
    def _load_config(self) -> NotificationConfig:
        """Load notification configuration from file and environment"""
        config_path = os.path.join(os.path.dirname(__file__), "config", "notification_config.json")
        
        # Load base configuration from file
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
        except FileNotFoundError:
            # Fallback configuration if file doesn't exist
            config_data = {
                "email_config": {},
                "teams_webhook_url": None,
                "slack_webhook_url": None,
                "notification_preferences": {},
                "email_recipients": {}
            }
        
        # Override with environment variables
        email_config = {
            "smtp_server": os.getenv("EMAIL_HOST", "smtp.gmail.com"),
            "smtp_port": int(os.getenv("EMAIL_PORT", "587")),
            "username": os.getenv("EMAIL_HOST_USER"),
            "password": os.getenv("EMAIL_HOST_PASSWORD"),
            "sender": os.getenv("EMAIL_HOST_USER"),
            "use_tls": os.getenv("EMAIL_USE_TLS", "true").lower() == "true",
            "use_ssl": os.getenv("EMAIL_USE_SSL", "false").lower() == "true"
        } if os.getenv("EMAIL_HOST_USER") else None
        
        return NotificationConfig(
            email_config=email_config,
            teams_webhook_url=os.getenv("TEAMS_WEBHOOK_URL", config_data.get("teams_webhook_url")),
            slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL", config_data.get("slack_webhook_url")),
            notification_preferences=config_data.get("notification_preferences", {})
        )
    
    def _setup_templates(self) -> jinja2.Environment:
        """Setup Jinja2 templates for notifications"""
        template_loader = jinja2.FileSystemLoader(
            searchpath=os.path.join(os.path.dirname(__file__), "templates")
        )
        return jinja2.Environment(loader=template_loader)
    
    async def send_notification(self, payload: NotificationPayload):
        """Send notification through configured channels"""
        tasks = []
        
        for recipient in payload.recipients:
            channels = self.config.notification_preferences.get(recipient, [])
            
            for channel in channels:
                if channel == "slack" and self.config.slack_webhook_url:
                    tasks.append(self._send_slack_notification(payload))
                elif channel == "teams" and self.config.teams_webhook_url:
                    tasks.append(self._send_teams_notification(payload))
                elif channel == "email" and self.config.email_config:
                    tasks.append(self._send_email_notification(payload, recipient))
        
        # Execute all notifications concurrently
        await asyncio.gather(*tasks)
        
    async def _send_slack_notification(self, payload: NotificationPayload):
        """Send notification to Slack"""
        try:
            template = self.template_env.get_template("slack_notification.j2")
            message = template.render(
                title=payload.title,
                message=payload.message,
                priority=payload.priority,
                tier=payload.tier,
                details=payload.details
            )
            
            async with aiohttp.ClientSession() as session:
                await session.post(
                    self.config.slack_webhook_url,
                    json={"text": message}
                )
            logger.info(f"Sent Slack notification: {payload.title}")
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
    
    async def _send_teams_notification(self, payload: NotificationPayload):
        """Send notification to Microsoft Teams"""
        try:
            template = self.template_env.get_template("teams_notification.j2")
            card = template.render(
                title=payload.title,
                message=payload.message,
                priority=payload.priority,
                tier=payload.tier,
                details=payload.details
            )
            
            async with aiohttp.ClientSession() as session:
                await session.post(
                    self.config.teams_webhook_url,
                    json=json.loads(card)
                )
            logger.info(f"Sent Teams notification: {payload.title}")
        except Exception as e:
            logger.error(f"Failed to send Teams notification: {e}")
    
    async def _send_email_notification(self, payload: NotificationPayload, recipient: str):
        """Send notification via email"""
        if not self.config.email_config:
            logger.warning("Email configuration not available, skipping email notification")
            return
            
        try:
            template = self.template_env.get_template("email_notification.j2")
            html_content = template.render(
                title=payload.title,
                message=payload.message,
                priority=payload.priority,
                tier=payload.tier,
                details=payload.details,
                timestamp=payload.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
            )
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{payload.priority.upper()}] Algorithmic Trading System - {payload.title}"
            msg['From'] = self.config.email_config["sender"]
            msg['To'] = recipient
            msg['X-Priority'] = '1' if payload.priority == 'critical' else '3'
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Create plain text version as fallback
            text_content = f"""
{payload.title}

Message: {payload.message}
Priority: {payload.priority.upper()}
Tier: {payload.tier}
Time: {payload.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}

Details:
{chr(10).join([f"- {k}: {v}" for k, v in payload.details.items()])}

---
Algorithmic Trading System
Dependency Management Alert
            """.strip()
            
            text_part = MIMEText(text_content, 'plain')
            msg.attach(text_part)
            
            # Send email
            if self.config.email_config["use_ssl"]:
                server = smtplib.SMTP_SSL(
                    self.config.email_config["smtp_server"],
                    self.config.email_config["smtp_port"]
                )
            else:
                server = smtplib.SMTP(
                    self.config.email_config["smtp_server"],
                    self.config.email_config["smtp_port"]
                )
                
            try:
                if self.config.email_config["use_tls"] and not self.config.email_config["use_ssl"]:
                    server.starttls()
                    
                if self.config.email_config["username"] and self.config.email_config["password"]:
                    server.login(
                        self.config.email_config["username"],
                        self.config.email_config["password"]
                    )
                    
                server.send_message(msg)
                logger.info(f"Successfully sent email notification to {recipient}: {payload.title}")
                
            finally:
                server.quit()
                
        except Exception as e:
            logger.error(f"Failed to send email notification to {recipient}: {e}")
            # Optional: You could implement a retry mechanism here

# Notification templates
def create_update_notification(
    dependency_name: str,
    current_version: str,
    new_version: str,
    tier: int,
    breaking_changes: bool
) -> NotificationPayload:
    """Create notification for dependency updates"""
    priority = "critical" if tier == 1 or breaking_changes else "high"
    return NotificationPayload(
        title=f"Dependency Update Available: {dependency_name}",
        message=f"New version {new_version} available (current: {current_version})",
        priority=priority,
        tier=tier,
        timestamp=datetime.now(timezone.utc),
        details={
            "dependency": dependency_name,
            "current_version": current_version,
            "new_version": new_version,
            "breaking_changes": breaking_changes
        },
        recipients=["team-leads", "developers"]  # Would come from config
    )

def create_security_notification(
    dependency_name: str,
    vulnerability: Dict,
    tier: int
) -> NotificationPayload:
    """Create notification for security vulnerabilities"""
    return NotificationPayload(
        title=f"Security Vulnerability: {dependency_name}",
        message=f"CVE-{vulnerability['cve_id']}: {vulnerability['description']}",
        priority="critical",
        tier=tier,
        timestamp=datetime.now(timezone.utc),
        details={
            "dependency": dependency_name,
            "cve_id": vulnerability["cve_id"],
            "severity": vulnerability["severity"],
            "description": vulnerability["description"],
            "remediation": vulnerability["remediation"]
        },
        recipients=[""]  # Would come from config
    )

# Enhanced email notification methods
class EmailNotificationService:
    """Enhanced email notification service with batch and priority features"""
    
    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service
        self.batch_notifications = []
        
    async def send_immediate_email(self, recipients: List[str], payload: NotificationPayload):
        """Send immediate email notification to multiple recipients"""
        tasks = []
        for recipient in recipients:
            tasks.append(self.notification_service._send_email_notification(payload, recipient))
        await asyncio.gather(*tasks)
        
    async def send_critical_alert_email(self, dependency_name: str, issue_description: str, tier: int):
        """Send critical alert email with high priority"""
        config_data = self.notification_service.config.notification_preferences
        recipients = self._get_recipients_for_priority("critical")
        
        payload = NotificationPayload(
            title=f"🚨 CRITICAL ALERT: {dependency_name}",
            message=issue_description,
            priority="critical",
            tier=tier,
            timestamp=datetime.now(timezone.utc),
            details={
                "dependency": dependency_name,
                "issue_type": "critical_failure",
                "action_required": "immediate",
                "escalation_level": "tier1"
            },
            recipients=recipients
        )
        
        await self.send_immediate_email(recipients, payload)
        
    async def send_security_alert_email(self, dependency_name: str, cve_details: Dict):
        """Send security vulnerability alert email"""
        recipients = self._get_recipients_for_priority("critical")
        
        payload = NotificationPayload(
            title=f"🛡️ SECURITY ALERT: {dependency_name}",
            message=f"Security vulnerability detected: {cve_details.get('cve_id', 'Unknown CVE')}",
            priority="critical",
            tier=1,  # Security issues are always tier 1
            timestamp=datetime.now(timezone.utc),
            details={
                "dependency": dependency_name,
                "cve_id": cve_details.get("cve_id", "Unknown"),
                "severity": cve_details.get("severity", "Unknown"),
                "cvss_score": cve_details.get("cvss_score", "Unknown"),
                "description": cve_details.get("description", "No description available"),
                "remediation": cve_details.get("remediation", "Update to latest secure version")
            },
            recipients=recipients
        )
        
        await self.send_immediate_email(recipients, payload)
        
    async def send_batch_summary_email(self, summary_period: str = "daily"):
        """Send batch summary of accumulated notifications"""
        if not self.batch_notifications:
            return
            
        recipients = self._get_recipients_for_priority("medium")
        
        # Group notifications by tier and priority
        grouped_notifications = {}
        for notification in self.batch_notifications:
            key = f"tier{notification['tier']}_{notification['priority']}"
            if key not in grouped_notifications:
                grouped_notifications[key] = []
            grouped_notifications[key].append(notification)
            
        summary_details = {
            "period": summary_period,
            "total_notifications": len(self.batch_notifications),
            "grouped_summary": grouped_notifications,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
        payload = NotificationPayload(
            title=f"📊 {summary_period.title()} Dependency Summary",
            message=f"Summary of {len(self.batch_notifications)} dependency notifications",
            priority="medium",
            tier=0,  # Summary notifications
            timestamp=datetime.now(timezone.utc),
            details=summary_details,
            recipients=recipients
        )
        
        await self.send_immediate_email(recipients, payload)
        
        # Clear batch notifications after sending
        self.batch_notifications.clear()
        
    def _get_recipients_for_priority(self, priority: str) -> List[str]:
        """Get email recipients based on priority level"""
        # This would typically come from configuration
        recipients_map = {
            "critical": ["vincyspereira@gmail.com", "admin@trading.com"],
            "high": ["vincyspereira@gmail.com", "dev-team@trading.com"],
            "medium": ["dev-team@trading.com"],
            "low": ["dev-team@trading.com"]
        }
        return recipients_map.get(priority, ["vincyspereira@gmail.com"])
        
    def add_to_batch(self, notification_data: Dict):
        """Add notification to batch queue for summary emails"""
        self.batch_notifications.append(notification_data)
        
# Utility functions for creating specific notification types
async def send_dependency_update_email(email_service: EmailNotificationService, 
                                     dependency_name: str, 
                                     old_version: str, 
                                     new_version: str, 
                                     tier: int,
                                     breaking_changes: bool = False):
    """Send dependency update notification email"""
    priority = "high" if tier <= 2 or breaking_changes else "medium"
    recipients = email_service._get_recipients_for_priority(priority)
    
    payload = NotificationPayload(
        title=f"📦 Dependency Update: {dependency_name}",
        message=f"Update available: {old_version} → {new_version}",
        priority=priority,
        tier=tier,
        timestamp=datetime.now(timezone.utc),
        details={
            "dependency": dependency_name,
            "old_version": old_version,
            "new_version": new_version,
            "breaking_changes": breaking_changes,
            "tier": tier,
            "update_type": "major" if breaking_changes else "minor"
        },
        recipients=recipients
    )
    
    await email_service.send_immediate_email(recipients, payload)
