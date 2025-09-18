#!/usr/bin/env python3
"""
Security Alert Service
Real-time security alerting and notification system for institutional-grade monitoring
"""

import json
import os
import asyncio
import aiohttp
import smtplib
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging
import yaml
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SecurityAlert:
    """Represents a security alert"""
    alert_id: str
    timestamp: str
    severity: str
    category: str
    title: str
    description: str
    affected_systems: List[str]
    risk_score: float
    compliance_impact: str
    remediation_priority: str
    source: str
    metadata: Dict[str, Any]

@dataclass
class NotificationChannel:
    """Represents a notification channel configuration"""
    name: str
    type: str  # teams, discord, email, slack, pagerduty
    endpoint: str
    enabled: bool
    severity_threshold: str
    escalation_delay: int  # minutes
    retry_count: int
    
class SecurityAlertService:
    def __init__(self, config_path: str = None):
        self.config_path = config_path or 'security/alert_config.yaml'
        self.config = self._load_config()
        self.notification_channels = self._load_notification_channels()
        self.alert_history = []
        self.escalation_rules = self._load_escalation_rules()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load alert service configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {self.config_path} not found, using defaults")
            return self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'alert_retention_days': 30,
            'max_alerts_per_hour': 50,
            'escalation_enabled': True,
            'deduplication_window': 300,  # 5 minutes
            'severity_levels': ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'],
            'notification_templates': {
                'teams': 'templates/teams_alert.json',
                'discord': 'templates/discord_alert.json',
                'email': 'templates/email_alert.html'
            }
        }
    
    def _load_notification_channels(self) -> List[NotificationChannel]:
        """Load notification channel configurations"""
        channels = []
        
        # Teams channel
        teams_webhook = os.getenv('TEAMS_SECURITY_WEBHOOK')
        if teams_webhook:
            channels.append(NotificationChannel(
                name='security-teams',
                type='teams',
                endpoint=teams_webhook,
                enabled=True,
                severity_threshold='MEDIUM',
                escalation_delay=15,
                retry_count=3
            ))
        
        # Discord channel
        discord_webhook = os.getenv('DISCORD_SECURITY_WEBHOOK')
        if discord_webhook:
            channels.append(NotificationChannel(
                name='security-discord',
                type='discord',
                endpoint=discord_webhook,
                enabled=True,
                severity_threshold='HIGH',
                escalation_delay=10,
                retry_count=3
            ))
        
        # Email notifications
        smtp_server = os.getenv('SMTP_SERVER')
        if smtp_server:
            channels.append(NotificationChannel(
                name='security-email',
                type='email',
                endpoint=os.getenv('SECURITY_EMAIL_RECIPIENTS', ''),
                enabled=True,
                severity_threshold='CRITICAL',
                escalation_delay=5,
                retry_count=2
            ))
        
        # PagerDuty integration
        pagerduty_key = os.getenv('PAGERDUTY_INTEGRATION_KEY')
        if pagerduty_key:
            channels.append(NotificationChannel(
                name='security-pagerduty',
                type='pagerduty',
                endpoint=f"https://events.pagerduty.com/v2/enqueue",
                enabled=True,
                severity_threshold='CRITICAL',
                escalation_delay=0,  # Immediate
                retry_count=5
            ))
        
        return channels
    
    def _load_escalation_rules(self) -> Dict[str, Any]:
        """Load escalation rules"""
        return {
            'CRITICAL': {
                'immediate_channels': ['pagerduty', 'email'],
                'escalation_channels': ['teams', 'discord'],
                'escalation_delay': 5,  # minutes
                'max_escalations': 3
            },
            'HIGH': {
                'immediate_channels': ['teams', 'discord'],
                'escalation_channels': ['email'],
                'escalation_delay': 15,
                'max_escalations': 2
            },
            'MEDIUM': {
                'immediate_channels': ['teams'],
                'escalation_channels': ['discord'],
                'escalation_delay': 30,
                'max_escalations': 1
            },
            'LOW': {
                'immediate_channels': ['teams'],
                'escalation_channels': [],
                'escalation_delay': 60,
                'max_escalations': 0
            }
        }
    
    async def create_alert(self, 
                          severity: str,
                          category: str,
                          title: str,
                          description: str,
                          affected_systems: List[str] = None,
                          risk_score: float = 0.0,
                          compliance_impact: str = 'UNKNOWN',
                          source: str = 'SECURITY_SCANNER',
                          metadata: Dict[str, Any] = None) -> SecurityAlert:
        """Create a new security alert"""
        
        alert_id = f"SEC-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{len(self.alert_history):04d}"
        
        alert = SecurityAlert(
            alert_id=alert_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            severity=severity,
            category=category,
            title=title,
            description=description,
            affected_systems=affected_systems or [],
            risk_score=risk_score,
            compliance_impact=compliance_impact,
            remediation_priority=self._calculate_remediation_priority(severity, risk_score),
            source=source,
            metadata=metadata or {}
        )
        
        # Check for duplicate alerts
        if not self._is_duplicate_alert(alert):
            self.alert_history.append(alert)
            logger.info(f"Created security alert: {alert_id} - {title}")
            
            # Send notifications
            await self._process_alert_notifications(alert)
            
            # Save alert to persistent storage
            await self._save_alert(alert)
            
        else:
            logger.info(f"Duplicate alert suppressed: {title}")
        
        return alert
    
    def _calculate_remediation_priority(self, severity: str, risk_score: float) -> str:
        """Calculate remediation priority based on severity and risk score"""
        if severity == 'CRITICAL' or risk_score >= 90:
            return 'IMMEDIATE'
        elif severity == 'HIGH' or risk_score >= 70:
            return 'URGENT'
        elif severity == 'MEDIUM' or risk_score >= 50:
            return 'HIGH'
        else:
            return 'NORMAL'
    
    def _is_duplicate_alert(self, alert: SecurityAlert) -> bool:
        """Check if alert is a duplicate within deduplication window"""
        dedup_window = self.config.get('deduplication_window', 300)
        current_time = datetime.now(timezone.utc)
        
        for existing_alert in self.alert_history[-50:]:  # Check last 50 alerts
            existing_time = datetime.fromisoformat(existing_alert.timestamp.replace('Z', '+00:00'))
            time_diff = (current_time - existing_time).total_seconds()
            
            if (time_diff <= dedup_window and
                existing_alert.title == alert.title and
                existing_alert.category == alert.category and
                existing_alert.severity == alert.severity):
                return True
        
        return False
    
    async def _process_alert_notifications(self, alert: SecurityAlert) -> None:
        """Process alert notifications based on escalation rules"""
        escalation_rule = self.escalation_rules.get(alert.severity, {})
        immediate_channels = escalation_rule.get('immediate_channels', [])
        
        # Send immediate notifications
        tasks = []
        for channel in self.notification_channels:
            if (channel.enabled and 
                channel.name.split('-')[1] in immediate_channels and
                self._should_notify(channel, alert)):
                tasks.append(self._send_notification(channel, alert))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Schedule escalation if configured
        if escalation_rule.get('escalation_channels'):
            asyncio.create_task(self._schedule_escalation(alert, escalation_rule))
    
    def _should_notify(self, channel: NotificationChannel, alert: SecurityAlert) -> bool:
        """Determine if channel should receive notification"""
        severity_levels = self.config.get('severity_levels', ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'])
        
        alert_level = severity_levels.index(alert.severity) if alert.severity in severity_levels else 0
        threshold_level = severity_levels.index(channel.severity_threshold) if channel.severity_threshold in severity_levels else 0
        
        return alert_level >= threshold_level
    
    async def _schedule_escalation(self, alert: SecurityAlert, escalation_rule: Dict[str, Any]) -> None:
        """Schedule alert escalation"""
        escalation_delay = escalation_rule.get('escalation_delay', 15) * 60  # Convert to seconds
        escalation_channels = escalation_rule.get('escalation_channels', [])
        max_escalations = escalation_rule.get('max_escalations', 1)
        
        for escalation_level in range(max_escalations):
            await asyncio.sleep(escalation_delay)
            
            # Check if alert has been resolved
            if self._is_alert_resolved(alert.alert_id):
                logger.info(f"Alert {alert.alert_id} resolved, cancelling escalation")
                break
            
            # Send escalation notifications
            tasks = []
            for channel in self.notification_channels:
                if (channel.enabled and 
                    channel.name.split('-')[1] in escalation_channels):
                    escalated_alert = self._create_escalation_alert(alert, escalation_level + 1)
                    tasks.append(self._send_notification(channel, escalated_alert))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            logger.info(f"Escalation level {escalation_level + 1} sent for alert {alert.alert_id}")
    
    def _is_alert_resolved(self, alert_id: str) -> bool:
        """Check if alert has been resolved"""
        # In a real implementation, this would check a resolution database
        # For now, we'll assume alerts are not automatically resolved
        return False
    
    def _create_escalation_alert(self, original_alert: SecurityAlert, escalation_level: int) -> SecurityAlert:
        """Create escalated version of alert"""
        escalated_alert = SecurityAlert(
            alert_id=f"{original_alert.alert_id}-ESC{escalation_level}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            severity=original_alert.severity,
            category=original_alert.category,
            title=f"[ESCALATION {escalation_level}] {original_alert.title}",
            description=f"ESCALATED ALERT: {original_alert.description}",
            affected_systems=original_alert.affected_systems,
            risk_score=original_alert.risk_score,
            compliance_impact=original_alert.compliance_impact,
            remediation_priority='IMMEDIATE',
            source=original_alert.source,
            metadata={**original_alert.metadata, 'escalation_level': escalation_level}
        )
        return escalated_alert
    
    async def _send_notification(self, channel: NotificationChannel, alert: SecurityAlert) -> bool:
        """Send notification to specific channel"""
        try:
            if channel.type == 'teams':
                return await self._send_teams_notification(channel, alert)
            elif channel.type == 'discord':
                return await self._send_discord_notification(channel, alert)
            elif channel.type == 'email':
                return await self._send_email_notification(channel, alert)
            elif channel.type == 'pagerduty':
                return await self._send_pagerduty_notification(channel, alert)
            elif channel.type == 'slack':
                return await self._send_slack_notification(channel, alert)
            else:
                logger.warning(f"Unknown notification channel type: {channel.type}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to send notification to {channel.name}: {e}")
            return False
    
    async def _send_teams_notification(self, channel: NotificationChannel, alert: SecurityAlert) -> bool:
        """Send notification to Microsoft Teams"""
        color_map = {
            'CRITICAL': 'FF0000',
            'HIGH': 'FFA500',
            'MEDIUM': 'FFFF00',
            'LOW': '00FF00'
        }
        
        payload = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": f"Security Alert: {alert.title}",
            "themeColor": color_map.get(alert.severity, '808080'),
            "sections": [{
                "activityTitle": f"🚨 {alert.severity} Security Alert",
                "activitySubtitle": alert.category,
                "activityImage": "https://example.com/security-icon.png",
                "facts": [
                    {"name": "Alert ID", "value": alert.alert_id},
                    {"name": "Severity", "value": alert.severity},
                    {"name": "Risk Score", "value": f"{alert.risk_score:.1f}/100"},
                    {"name": "Compliance Impact", "value": alert.compliance_impact},
                    {"name": "Remediation Priority", "value": alert.remediation_priority},
                    {"name": "Affected Systems", "value": ", ".join(alert.affected_systems) or "N/A"},
                    {"name": "Source", "value": alert.source},
                    {"name": "Timestamp", "value": alert.timestamp}
                ],
                "text": alert.description
            }],
            "potentialAction": [{
                "@type": "OpenUri",
                "name": "View Security Dashboard",
                "targets": [{
                    "os": "default",
                    "uri": "https://security-dashboard.example.com"
                }]
            }]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(channel.endpoint, json=payload) as response:
                if response.status == 200:
                    logger.info(f"Teams notification sent successfully to {channel.name}")
                    return True
                else:
                    logger.error(f"Teams notification failed: {response.status}")
                    return False
    
    async def _send_discord_notification(self, channel: NotificationChannel, alert: SecurityAlert) -> bool:
        """Send notification to Discord"""
        color_map = {
            'CRITICAL': 0xFF0000,
            'HIGH': 0xFFA500,
            'MEDIUM': 0xFFFF00,
            'LOW': 0x00FF00
        }
        
        embed = {
            "title": f"🚨 {alert.severity} Security Alert",
            "description": alert.description,
            "color": color_map.get(alert.severity, 0x808080),
            "fields": [
                {"name": "Alert ID", "value": alert.alert_id, "inline": True},
                {"name": "Category", "value": alert.category, "inline": True},
                {"name": "Risk Score", "value": f"{alert.risk_score:.1f}/100", "inline": True},
                {"name": "Compliance Impact", "value": alert.compliance_impact, "inline": True},
                {"name": "Remediation Priority", "value": alert.remediation_priority, "inline": True},
                {"name": "Source", "value": alert.source, "inline": True}
            ],
            "timestamp": alert.timestamp,
            "footer": {
                "text": "Algorithmic Trading Security System"
            }
        }
        
        if alert.affected_systems:
            embed["fields"].append({
                "name": "Affected Systems",
                "value": "\n".join(alert.affected_systems),
                "inline": False
            })
        
        payload = {"embeds": [embed]}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(channel.endpoint, json=payload) as response:
                if response.status == 204:
                    logger.info(f"Discord notification sent successfully to {channel.name}")
                    return True
                else:
                    logger.error(f"Discord notification failed: {response.status}")
                    return False
    
    async def _send_email_notification(self, channel: NotificationChannel, alert: SecurityAlert) -> bool:
        """Send email notification"""
        try:
            smtp_server = os.getenv('SMTP_SERVER')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            smtp_username = os.getenv('SMTP_USERNAME')
            smtp_password = os.getenv('SMTP_PASSWORD')
            sender_email = os.getenv('SENDER_EMAIL', smtp_username)
            
            if not all([smtp_server, smtp_username, smtp_password]):
                logger.error("SMTP configuration incomplete")
                return False
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{alert.severity}] Security Alert: {alert.title}"
            msg['From'] = sender_email
            msg['To'] = channel.endpoint
            
            # Create HTML content
            html_content = self._create_email_html(alert)
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email notification sent successfully to {channel.endpoint}")
            return True
            
        except Exception as e:
            logger.error(f"Email notification failed: {e}")
            return False
    
    def _create_email_html(self, alert: SecurityAlert) -> str:
        """Create HTML content for email notification"""
        color_map = {
            'CRITICAL': '#FF0000',
            'HIGH': '#FFA500',
            'MEDIUM': '#FFFF00',
            'LOW': '#00FF00'
        }
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: {color_map.get(alert.severity, '#808080')}; color: white; padding: 15px; border-radius: 5px; }}
                .content {{ margin: 20px 0; }}
                .details {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; }}
                .field {{ margin: 10px 0; }}
                .label {{ font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🚨 {alert.severity} Security Alert</h2>
                <p>{alert.title}</p>
            </div>
            
            <div class="content">
                <p>{alert.description}</p>
            </div>
            
            <div class="details">
                <div class="field"><span class="label">Alert ID:</span> {alert.alert_id}</div>
                <div class="field"><span class="label">Category:</span> {alert.category}</div>
                <div class="field"><span class="label">Risk Score:</span> {alert.risk_score:.1f}/100</div>
                <div class="field"><span class="label">Compliance Impact:</span> {alert.compliance_impact}</div>
                <div class="field"><span class="label">Remediation Priority:</span> {alert.remediation_priority}</div>
                <div class="field"><span class="label">Source:</span> {alert.source}</div>
                <div class="field"><span class="label">Timestamp:</span> {alert.timestamp}</div>
                {f'<div class="field"><span class="label">Affected Systems:</span> {", ".join(alert.affected_systems)}</div>' if alert.affected_systems else ''}
            </div>
            
            <p><strong>Please review and take appropriate action immediately.</strong></p>
        </body>
        </html>
        """
    
    async def _send_pagerduty_notification(self, channel: NotificationChannel, alert: SecurityAlert) -> bool:
        """Send notification to PagerDuty"""
        integration_key = os.getenv('PAGERDUTY_INTEGRATION_KEY')
        if not integration_key:
            logger.error("PagerDuty integration key not configured")
            return False
        
        payload = {
            "routing_key": integration_key,
            "event_action": "trigger",
            "dedup_key": f"security-alert-{alert.alert_id}",
            "payload": {
                "summary": f"{alert.severity}: {alert.title}",
                "source": alert.source,
                "severity": alert.severity.lower(),
                "component": "security-scanner",
                "group": alert.category,
                "class": "security",
                "custom_details": {
                    "alert_id": alert.alert_id,
                    "risk_score": alert.risk_score,
                    "compliance_impact": alert.compliance_impact,
                    "remediation_priority": alert.remediation_priority,
                    "affected_systems": alert.affected_systems,
                    "description": alert.description
                }
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(channel.endpoint, json=payload) as response:
                if response.status == 202:
                    logger.info(f"PagerDuty notification sent successfully")
                    return True
                else:
                    logger.error(f"PagerDuty notification failed: {response.status}")
                    return False
    
    async def _send_slack_notification(self, channel: NotificationChannel, alert: SecurityAlert) -> bool:
        """Send notification to Slack"""
        color_map = {
            'CRITICAL': 'danger',
            'HIGH': 'warning',
            'MEDIUM': 'warning',
            'LOW': 'good'
        }
        
        payload = {
            "text": f"🚨 {alert.severity} Security Alert: {alert.title}",
            "attachments": [{
                "color": color_map.get(alert.severity, '#808080'),
                "fields": [
                    {"title": "Alert ID", "value": alert.alert_id, "short": True},
                    {"title": "Category", "value": alert.category, "short": True},
                    {"title": "Risk Score", "value": f"{alert.risk_score:.1f}/100", "short": True},
                    {"title": "Compliance Impact", "value": alert.compliance_impact, "short": True},
                    {"title": "Description", "value": alert.description, "short": False}
                ],
                "ts": int(datetime.fromisoformat(alert.timestamp.replace('Z', '+00:00')).timestamp())
            }]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(channel.endpoint, json=payload) as response:
                if response.status == 200:
                    logger.info(f"Slack notification sent successfully to {channel.name}")
                    return True
                else:
                    logger.error(f"Slack notification failed: {response.status}")
                    return False
    
    async def _save_alert(self, alert: SecurityAlert) -> None:
        """Save alert to persistent storage"""
        try:
            alerts_dir = Path('security/alerts')
            alerts_dir.mkdir(parents=True, exist_ok=True)
            
            alert_file = alerts_dir / f"{alert.alert_id}.json"
            with open(alert_file, 'w') as f:
                json.dump(asdict(alert), f, indent=2)
            
            logger.debug(f"Alert saved to {alert_file}")
            
        except Exception as e:
            logger.error(f"Failed to save alert {alert.alert_id}: {e}")
    
    async def resolve_alert(self, alert_id: str, resolution_notes: str = "") -> bool:
        """Mark alert as resolved"""
        try:
            # Find alert in history
            alert = next((a for a in self.alert_history if a.alert_id == alert_id), None)
            if not alert:
                logger.warning(f"Alert {alert_id} not found")
                return False
            
            # Update alert metadata
            alert.metadata['resolved'] = True
            alert.metadata['resolution_timestamp'] = datetime.now(timezone.utc).isoformat()
            alert.metadata['resolution_notes'] = resolution_notes
            
            # Save updated alert
            await self._save_alert(alert)
            
            logger.info(f"Alert {alert_id} marked as resolved")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve alert {alert_id}: {e}")
            return False
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        total_alerts = len(self.alert_history)
        
        if total_alerts == 0:
            return {
                'total_alerts': 0,
                'by_severity': {},
                'by_category': {},
                'resolved_count': 0,
                'average_risk_score': 0.0
            }
        
        # Count by severity
        by_severity = {}
        for alert in self.alert_history:
            by_severity[alert.severity] = by_severity.get(alert.severity, 0) + 1
        
        # Count by category
        by_category = {}
        for alert in self.alert_history:
            by_category[alert.category] = by_category.get(alert.category, 0) + 1
        
        # Count resolved alerts
        resolved_count = sum(1 for alert in self.alert_history 
                           if alert.metadata.get('resolved', False))
        
        # Calculate average risk score
        avg_risk_score = sum(alert.risk_score for alert in self.alert_history) / total_alerts
        
        return {
            'total_alerts': total_alerts,
            'by_severity': by_severity,
            'by_category': by_category,
            'resolved_count': resolved_count,
            'resolution_rate': resolved_count / total_alerts if total_alerts > 0 else 0,
            'average_risk_score': avg_risk_score
        }

# Example usage and testing
async def main():
    """Example usage of SecurityAlertService"""
    alert_service = SecurityAlertService()
    
    # Create a test alert
    alert = await alert_service.create_alert(
        severity='HIGH',
        category='VULNERABILITY',
        title='Critical SQL Injection Vulnerability Detected',
        description='A critical SQL injection vulnerability was detected in the trading module',
        affected_systems=['trading-engine', 'order-management'],
        risk_score=85.0,
        compliance_impact='HIGH',
        source='BANDIT_SCANNER',
        metadata={
            'file': 'trading/orders.py',
            'line': 142,
            'test_id': 'B608'
        }
    )
    
    print(f"Created alert: {alert.alert_id}")
    
    # Get statistics
    stats = alert_service.get_alert_statistics()
    print(f"Alert statistics: {stats}")

if __name__ == '__main__':
    asyncio.run(main())