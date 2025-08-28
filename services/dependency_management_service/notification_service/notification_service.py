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
from datetime import datetime
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
        """Load notification configuration"""
        config_path = os.path.join(os.path.dirname(__file__), "config", "notification_config.json")
        with open(config_path, 'r') as f:
            return NotificationConfig(**json.load(f))
    
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
        try:
            template = self.template_env.get_template("email_notification.j2")
            html_content = template.render(
                title=payload.title,
                message=payload.message,
                priority=payload.priority,
                tier=payload.tier,
                details=payload.details
            )
            
            msg = MIMEMultipart()
            msg['Subject'] = f"[{payload.priority.upper()}] {payload.title}"
            msg['From'] = self.config.email_config["sender"]
            msg['To'] = recipient
            
            msg.attach(MIMEText(html_content, 'html'))
            
            with smtplib.SMTP(
                self.config.email_config["smtp_server"],
                self.config.email_config["smtp_port"]
            ) as server:
                server.starttls()
                server.login(
                    self.config.email_config["username"],
                    self.config.email_config["password"]
                )
                server.send_message(msg)
            
            logger.info(f"Sent email notification to {recipient}: {payload.title}")
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")

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
        timestamp=datetime.utcnow(),
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
        timestamp=datetime.utcnow(),
        details={
            "dependency": dependency_name,
            "cve_id": vulnerability["cve_id"],
            "severity": vulnerability["severity"],
            "description": vulnerability["description"],
            "remediation": vulnerability["remediation"]
        },
        recipients=["security-team", "team-leads"]  # Would come from config
    )
