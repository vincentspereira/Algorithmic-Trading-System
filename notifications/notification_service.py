#!/usr/bin/env python3
"""
Multi-Channel Notification Service
Institutional-grade notification system with escalation protocols

Features:
- Multi-channel delivery (Teams, Discord, Email, PagerDuty, SMS)
- Escalation protocols with automatic escalation
- Rate limiting and deduplication
- Health monitoring and metrics
- Compliance and audit logging
- Zero-trust security architecture
"""

import asyncio
import json
import logging
import smtplib
import time
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import yaml
import aiohttp
import redis
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from cryptography.fernet import Fernet
import structlog
from twilio.rest import Client as TwilioClient
import os
from pathlib import Path

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class AlertCategory(Enum):
    """Alert categories"""
    SECURITY = "security"
    TRADING = "trading"
    INFRASTRUCTURE = "infrastructure"
    COMPLIANCE = "compliance"
    PERFORMANCE = "performance"
    DATA = "data"

class NotificationChannel(Enum):
    """Notification channels"""
    TEAMS = "teams"
    DISCORD = "discord"
    EMAIL = "email"
    PAGERDUTY = "pagerduty"
    SLACK = "slack"
    SMS = "sms"

@dataclass
class Alert:
    """Alert data structure"""
    id: str
    title: str
    description: str
    severity: AlertSeverity
    category: AlertCategory
    system: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    resolved: bool = False
    escalation_level: int = 0
    hash: str = field(init=False)
    
    def __post_init__(self):
        """Generate alert hash for deduplication"""
        content = f"{self.title}{self.description}{self.system}{self.category.value}"
        self.hash = hashlib.sha256(content.encode()).hexdigest()[:16]

@dataclass
class NotificationResult:
    """Notification delivery result"""
    channel: NotificationChannel
    success: bool
    error: Optional[str] = None
    delivery_time: float = 0.0
    retry_count: int = 0

class NotificationService:
    """Multi-channel notification service with escalation protocols"""
    
    def __init__(self, config_path: str = "notifications/notification_config.yaml"):
        self.config = self._load_config(config_path)
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )
        
        # Initialize encryption
        self.cipher = Fernet(os.getenv('NOTIFICATION_ENCRYPTION_KEY', Fernet.generate_key()))
        
        # Initialize Twilio client
        self.twilio_client = None
        if self.config['channels']['sms']['enabled']:
            self.twilio_client = TwilioClient(
                os.getenv('TWILIO_ACCOUNT_SID'),
                os.getenv('TWILIO_AUTH_TOKEN')
            )
        
        # Prometheus metrics
        self.alerts_sent_total = Counter(
            'alerts_sent_total',
            'Total number of alerts sent',
            ['channel', 'severity', 'category']
        )
        
        self.alert_delivery_duration = Histogram(
            'alert_delivery_duration_seconds',
            'Time taken to deliver alerts',
            ['channel']
        )
        
        self.escalation_triggered_total = Counter(
            'escalation_triggered_total',
            'Total number of escalations triggered',
            ['level', 'category']
        )
        
        self.active_alerts = Gauge(
            'active_alerts_total',
            'Number of active alerts',
            ['severity', 'category']
        )
        
        # Rate limiting tracking
        self.rate_limits: Dict[str, List[float]] = {}
        self.duplicate_cache: Set[str] = set()
        
        # Start metrics server
        if self.config['metrics']['prometheus']['enabled']:
            start_http_server(self.config['metrics']['prometheus']['port'])
        
        logger.info("Notification service initialized", config=config_path)
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load notification configuration"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info("Configuration loaded successfully", path=config_path)
            return config
        except Exception as e:
            logger.error("Failed to load configuration", error=str(e), path=config_path)
            raise
    
    async def send_alert(self, alert: Alert) -> List[NotificationResult]:
        """Send alert through configured channels"""
        start_time = time.time()
        
        try:
            # Check for duplicates
            if self._is_duplicate(alert):
                logger.info("Duplicate alert suppressed", alert_id=alert.id, hash=alert.hash)
                return []
            
            # Check rate limits
            if not self._check_rate_limits(alert):
                logger.warning("Alert rate limited", alert_id=alert.id, category=alert.category.value)
                return []
            
            # Get channels for severity level
            channels = self._get_channels_for_severity(alert.severity)
            
            # Send notifications
            results = []
            for channel in channels:
                result = await self._send_to_channel(alert, channel)
                results.append(result)
                
                # Update metrics
                self.alerts_sent_total.labels(
                    channel=channel.value,
                    severity=alert.severity.value,
                    category=alert.category.value
                ).inc()
                
                if result.success:
                    self.alert_delivery_duration.labels(channel=channel.value).observe(result.delivery_time)
            
            # Store alert for escalation tracking
            await self._store_alert(alert)
            
            # Schedule escalation if needed
            if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]:
                await self._schedule_escalation(alert)
            
            # Update active alerts metric
            self.active_alerts.labels(
                severity=alert.severity.value,
                category=alert.category.value
            ).inc()
            
            # Add to duplicate cache
            self.duplicate_cache.add(alert.hash)
            
            total_time = time.time() - start_time
            logger.info(
                "Alert sent successfully",
                alert_id=alert.id,
                channels=len(channels),
                total_time=total_time
            )
            
            return results
            
        except Exception as e:
            logger.error("Failed to send alert", alert_id=alert.id, error=str(e))
            raise
    
    def _is_duplicate(self, alert: Alert) -> bool:
        """Check if alert is a duplicate"""
        if not self.config['rate_limiting']['deduplication']['enabled']:
            return False
        
        return alert.hash in self.duplicate_cache
    
    def _check_rate_limits(self, alert: Alert) -> bool:
        """Check if alert exceeds rate limits"""
        if not self.config['rate_limiting']['enabled']:
            return True
        
        current_time = time.time()
        category = alert.category.value
        
        # Initialize rate limit tracking for category
        if category not in self.rate_limits:
            self.rate_limits[category] = []
        
        # Clean old entries (older than 1 hour)
        self.rate_limits[category] = [
            t for t in self.rate_limits[category] 
            if current_time - t < 3600
        ]
        
        # Check per-category limit
        category_limit = self.config['rate_limiting']['per_category'].get(category, 100)
        if len(self.rate_limits[category]) >= category_limit:
            return False
        
        # Add current time
        self.rate_limits[category].append(current_time)
        return True
    
    def _get_channels_for_severity(self, severity: AlertSeverity) -> List[NotificationChannel]:
        """Get notification channels for severity level"""
        severity_config = self.config['severity_levels'][severity.value]
        channel_names = severity_config['channels']
        
        channels = []
        for channel_name in channel_names:
            try:
                channel = NotificationChannel(channel_name)
                if self.config['channels'][channel_name]['enabled']:
                    channels.append(channel)
            except ValueError:
                logger.warning("Unknown channel", channel=channel_name)
        
        return channels
    
    async def _send_to_channel(self, alert: Alert, channel: NotificationChannel) -> NotificationResult:
        """Send alert to specific channel"""
        start_time = time.time()
        
        try:
            if channel == NotificationChannel.TEAMS:
                success, error = await self._send_teams(alert)
            elif channel == NotificationChannel.DISCORD:
                success, error = await self._send_discord(alert)
            elif channel == NotificationChannel.EMAIL:
                success, error = await self._send_email(alert)
            elif channel == NotificationChannel.PAGERDUTY:
                success, error = await self._send_pagerduty(alert)
            elif channel == NotificationChannel.SMS:
                success, error = await self._send_sms(alert)
            else:
                success, error = False, f"Unsupported channel: {channel.value}"
            
            delivery_time = time.time() - start_time
            
            return NotificationResult(
                channel=channel,
                success=success,
                error=error,
                delivery_time=delivery_time
            )
            
        except Exception as e:
            delivery_time = time.time() - start_time
            logger.error("Channel delivery failed", channel=channel.value, error=str(e))
            
            return NotificationResult(
                channel=channel,
                success=False,
                error=str(e),
                delivery_time=delivery_time
            )
    
    async def _send_teams(self, alert: Alert) -> tuple[bool, Optional[str]]:
        """Send alert to Microsoft Teams"""
        try:
            webhook_url = os.getenv('TEAMS_WEBHOOK_URL')
            if not webhook_url:
                return False, "Teams webhook URL not configured"
            
            # Get template and format message
            template = self.config['templates']['teams'][alert.severity.value]
            message = self._format_message(template, alert)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=json.loads(message),
                    timeout=self.config['channels']['teams']['timeout']
                ) as response:
                    if response.status == 200:
                        return True, None
                    else:
                        return False, f"HTTP {response.status}: {await response.text()}"
                        
        except Exception as e:
            return False, str(e)
    
    async def _send_discord(self, alert: Alert) -> tuple[bool, Optional[str]]:
        """Send alert to Discord"""
        try:
            webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
            if not webhook_url:
                return False, "Discord webhook URL not configured"
            
            # Get template and format message
            template = self.config['templates']['discord'][alert.severity.value]
            message = self._format_message(template, alert)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=json.loads(message),
                    timeout=self.config['channels']['discord']['timeout']
                ) as response:
                    if response.status in [200, 204]:
                        return True, None
                    else:
                        return False, f"HTTP {response.status}: {await response.text()}"
                        
        except Exception as e:
            return False, str(e)
    
    async def _send_email(self, alert: Alert) -> tuple[bool, Optional[str]]:
        """Send alert via email"""
        try:
            smtp_config = self.config['channels']['email']
            
            # Get template and format message
            template = self.config['templates']['email'][alert.severity.value]
            message_content = self._format_message(template, alert)
            
            # Parse subject and body
            lines = message_content.split('\n')
            subject = lines[0].replace('Subject: ', '')
            body = '\n'.join(lines[2:])  # Skip subject and empty line
            
            # Get recipients
            recipients = self._get_recipients_for_alert(alert)
            
            # Send email
            msg = MIMEMultipart()
            msg['From'] = smtp_config['from_address']
            msg['To'] = ', '.join([r['email'] for r in recipients if 'email' in r])
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(smtp_config['smtp_server'], smtp_config['smtp_port'])
            if smtp_config['use_tls']:
                server.starttls()
            
            server.login(os.getenv('SMTP_USERNAME'), os.getenv('SMTP_PASSWORD'))
            server.send_message(msg)
            server.quit()
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    async def _send_pagerduty(self, alert: Alert) -> tuple[bool, Optional[str]]:
        """Send alert to PagerDuty"""
        try:
            integration_key = os.getenv('PAGERDUTY_INTEGRATION_KEY')
            if not integration_key:
                return False, "PagerDuty integration key not configured"
            
            payload = {
                "routing_key": integration_key,
                "event_action": "trigger",
                "dedup_key": alert.hash,
                "payload": {
                    "summary": alert.title,
                    "source": alert.system,
                    "severity": alert.severity.value,
                    "component": alert.category.value,
                    "group": "algorithmic-trading",
                    "class": "alert",
                    "custom_details": {
                        "description": alert.description,
                        "timestamp": alert.timestamp.isoformat(),
                        "metadata": alert.metadata
                    }
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://events.pagerduty.com/v2/enqueue",
                    json=payload,
                    timeout=self.config['channels']['pagerduty']['timeout']
                ) as response:
                    if response.status == 202:
                        return True, None
                    else:
                        return False, f"HTTP {response.status}: {await response.text()}"
                        
        except Exception as e:
            return False, str(e)
    
    async def _send_sms(self, alert: Alert) -> tuple[bool, Optional[str]]:
        """Send alert via SMS"""
        try:
            if not self.twilio_client:
                return False, "Twilio client not configured"
            
            # Get recipients with phone numbers
            recipients = self._get_recipients_for_alert(alert)
            phone_recipients = [r for r in recipients if 'phone' in r]
            
            if not phone_recipients:
                return False, "No phone recipients configured"
            
            # Format SMS message
            message = f"🚨 {alert.severity.value.upper()}: {alert.title}\n{alert.description}\nSystem: {alert.system}"
            
            # Send to all phone recipients
            for recipient in phone_recipients:
                self.twilio_client.messages.create(
                    body=message,
                    from_=os.getenv('TWILIO_FROM_NUMBER'),
                    to=recipient['phone']
                )
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    def _format_message(self, template: str, alert: Alert) -> str:
        """Format message template with alert data"""
        return template.format(
            title=alert.title,
            description=alert.description,
            system=alert.system,
            severity=alert.severity.value,
            category=alert.category.value,
            timestamp=alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'),
            iso_timestamp=alert.timestamp.isoformat(),
            dashboard_url=os.getenv('DASHBOARD_URL', 'https://dashboard.algotrading.system')
        )
    
    def _get_recipients_for_alert(self, alert: Alert) -> List[Dict[str, str]]:
        """Get recipients for alert based on escalation level"""
        escalation_config = self.config['escalation'][f'level_{alert.escalation_level + 1}']
        recipients = []
        
        for recipient_config in escalation_config['recipients']:
            if recipient_config['type'] == 'role':
                role_recipients = self.config['recipient_groups'].get(recipient_config['value'], [])
                recipients.extend(role_recipients)
        
        return recipients
    
    async def _store_alert(self, alert: Alert) -> None:
        """Store alert for escalation tracking"""
        try:
            alert_data = {
                'id': alert.id,
                'title': alert.title,
                'description': alert.description,
                'severity': alert.severity.value,
                'category': alert.category.value,
                'system': alert.system,
                'timestamp': alert.timestamp.isoformat(),
                'escalation_level': alert.escalation_level,
                'acknowledged': alert.acknowledged,
                'resolved': alert.resolved
            }
            
            # Store in Redis with TTL
            self.redis_client.setex(
                f"alert:{alert.id}",
                86400,  # 24 hours
                json.dumps(alert_data)
            )
            
        except Exception as e:
            logger.error("Failed to store alert", alert_id=alert.id, error=str(e))
    
    async def _schedule_escalation(self, alert: Alert) -> None:
        """Schedule alert escalation"""
        try:
            if not self.config['escalation']['enabled']:
                return
            
            severity_config = self.config['severity_levels'][alert.severity.value]
            escalation_time = severity_config['escalation_time']
            
            if escalation_time is None:
                return
            
            # Schedule escalation task
            escalation_data = {
                'alert_id': alert.id,
                'escalation_level': alert.escalation_level + 1,
                'scheduled_time': (datetime.utcnow() + timedelta(seconds=escalation_time)).isoformat()
            }
            
            self.redis_client.setex(
                f"escalation:{alert.id}:{alert.escalation_level + 1}",
                escalation_time + 3600,  # TTL with buffer
                json.dumps(escalation_data)
            )
            
            logger.info(
                "Escalation scheduled",
                alert_id=alert.id,
                level=alert.escalation_level + 1,
                delay=escalation_time
            )
            
        except Exception as e:
            logger.error("Failed to schedule escalation", alert_id=alert.id, error=str(e))
    
    async def process_escalations(self) -> None:
        """Process pending escalations"""
        try:
            # Get all escalation keys
            escalation_keys = self.redis_client.keys("escalation:*")
            
            for key in escalation_keys:
                escalation_data = json.loads(self.redis_client.get(key))
                scheduled_time = datetime.fromisoformat(escalation_data['scheduled_time'])
                
                if datetime.utcnow() >= scheduled_time:
                    await self._execute_escalation(escalation_data)
                    self.redis_client.delete(key)
                    
        except Exception as e:
            logger.error("Failed to process escalations", error=str(e))
    
    async def _execute_escalation(self, escalation_data: Dict[str, Any]) -> None:
        """Execute alert escalation"""
        try:
            alert_id = escalation_data['alert_id']
            escalation_level = escalation_data['escalation_level']
            
            # Get original alert
            alert_data = self.redis_client.get(f"alert:{alert_id}")
            if not alert_data:
                logger.warning("Alert not found for escalation", alert_id=alert_id)
                return
            
            alert_dict = json.loads(alert_data)
            
            # Check if alert is already acknowledged or resolved
            if alert_dict['acknowledged'] or alert_dict['resolved']:
                logger.info("Skipping escalation for resolved alert", alert_id=alert_id)
                return
            
            # Create escalated alert
            alert = Alert(
                id=alert_dict['id'],
                title=f"ESCALATED: {alert_dict['title']}",
                description=f"Alert escalated to level {escalation_level}\n\n{alert_dict['description']}",
                severity=AlertSeverity(alert_dict['severity']),
                category=AlertCategory(alert_dict['category']),
                system=alert_dict['system'],
                escalation_level=escalation_level
            )
            
            # Send escalated alert
            await self.send_alert(alert)
            
            # Update metrics
            self.escalation_triggered_total.labels(
                level=escalation_level,
                category=alert.category.value
            ).inc()
            
            logger.info(
                "Alert escalated",
                alert_id=alert_id,
                level=escalation_level
            )
            
        except Exception as e:
            logger.error("Failed to execute escalation", error=str(e))
    
    async def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """Acknowledge an alert"""
        try:
            alert_data = self.redis_client.get(f"alert:{alert_id}")
            if not alert_data:
                return False
            
            alert_dict = json.loads(alert_data)
            alert_dict['acknowledged'] = True
            alert_dict['acknowledged_by'] = user
            alert_dict['acknowledged_at'] = datetime.utcnow().isoformat()
            
            self.redis_client.setex(
                f"alert:{alert_id}",
                86400,
                json.dumps(alert_dict)
            )
            
            # Update metrics
            self.active_alerts.labels(
                severity=alert_dict['severity'],
                category=alert_dict['category']
            ).dec()
            
            logger.info("Alert acknowledged", alert_id=alert_id, user=user)
            return True
            
        except Exception as e:
            logger.error("Failed to acknowledge alert", alert_id=alert_id, error=str(e))
            return False
    
    async def resolve_alert(self, alert_id: str, user: str) -> bool:
        """Resolve an alert"""
        try:
            alert_data = self.redis_client.get(f"alert:{alert_id}")
            if not alert_data:
                return False
            
            alert_dict = json.loads(alert_data)
            alert_dict['resolved'] = True
            alert_dict['resolved_by'] = user
            alert_dict['resolved_at'] = datetime.utcnow().isoformat()
            
            self.redis_client.setex(
                f"alert:{alert_id}",
                86400,
                json.dumps(alert_dict)
            )
            
            # Update metrics
            if not alert_dict.get('acknowledged', False):
                self.active_alerts.labels(
                    severity=alert_dict['severity'],
                    category=alert_dict['category']
                ).dec()
            
            logger.info("Alert resolved", alert_id=alert_id, user=user)
            return True
            
        except Exception as e:
            logger.error("Failed to resolve alert", alert_id=alert_id, error=str(e))
            return False
    
    async def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts"""
        try:
            alert_keys = self.redis_client.keys("alert:*")
            active_alerts = []
            
            for key in alert_keys:
                alert_data = json.loads(self.redis_client.get(key))
                if not alert_data['acknowledged'] and not alert_data['resolved']:
                    active_alerts.append(alert_data)
            
            return active_alerts
            
        except Exception as e:
            logger.error("Failed to get active alerts", error=str(e))
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all channels"""
        health_status = {
            'overall': 'healthy',
            'channels': {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Check each enabled channel
        for channel_name, channel_config in self.config['channels'].items():
            if not channel_config['enabled']:
                continue
            
            try:
                if channel_name == 'teams':
                    status = await self._check_teams_health()
                elif channel_name == 'discord':
                    status = await self._check_discord_health()
                elif channel_name == 'email':
                    status = await self._check_email_health()
                elif channel_name == 'pagerduty':
                    status = await self._check_pagerduty_health()
                else:
                    status = {'healthy': True, 'message': 'Not implemented'}
                
                health_status['channels'][channel_name] = status
                
                if not status['healthy']:
                    health_status['overall'] = 'degraded'
                    
            except Exception as e:
                health_status['channels'][channel_name] = {
                    'healthy': False,
                    'error': str(e)
                }
                health_status['overall'] = 'degraded'
        
        return health_status
    
    async def _check_teams_health(self) -> Dict[str, Any]:
        """Check Teams webhook health"""
        try:
            webhook_url = os.getenv('TEAMS_WEBHOOK_URL')
            if not webhook_url:
                return {'healthy': False, 'message': 'Webhook URL not configured'}
            
            # Send a minimal test message
            test_payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "text": "Health check"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=test_payload, timeout=10) as response:
                    if response.status == 200:
                        return {'healthy': True, 'message': 'OK'}
                    else:
                        return {'healthy': False, 'message': f'HTTP {response.status}'}
                        
        except Exception as e:
            return {'healthy': False, 'error': str(e)}
    
    async def _check_discord_health(self) -> Dict[str, Any]:
        """Check Discord webhook health"""
        try:
            webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
            if not webhook_url:
                return {'healthy': False, 'message': 'Webhook URL not configured'}
            
            # Send a minimal test message
            test_payload = {"content": "Health check"}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=test_payload, timeout=10) as response:
                    if response.status in [200, 204]:
                        return {'healthy': True, 'message': 'OK'}
                    else:
                        return {'healthy': False, 'message': f'HTTP {response.status}'}
                        
        except Exception as e:
            return {'healthy': False, 'error': str(e)}
    
    async def _check_email_health(self) -> Dict[str, Any]:
        """Check email server health"""
        try:
            smtp_config = self.config['channels']['email']
            
            server = smtplib.SMTP(smtp_config['smtp_server'], smtp_config['smtp_port'])
            if smtp_config['use_tls']:
                server.starttls()
            
            server.login(os.getenv('SMTP_USERNAME'), os.getenv('SMTP_PASSWORD'))
            server.quit()
            
            return {'healthy': True, 'message': 'OK'}
            
        except Exception as e:
            return {'healthy': False, 'error': str(e)}
    
    async def _check_pagerduty_health(self) -> Dict[str, Any]:
        """Check PagerDuty API health"""
        try:
            integration_key = os.getenv('PAGERDUTY_INTEGRATION_KEY')
            if not integration_key:
                return {'healthy': False, 'message': 'Integration key not configured'}
            
            # Check API connectivity
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.pagerduty.com/incidents",
                    headers={"Authorization": f"Token token={integration_key}"},
                    timeout=10
                ) as response:
                    if response.status in [200, 401]:  # 401 is OK, means API is reachable
                        return {'healthy': True, 'message': 'OK'}
                    else:
                        return {'healthy': False, 'message': f'HTTP {response.status}'}
                        
        except Exception as e:
            return {'healthy': False, 'error': str(e)}

# Example usage and testing
if __name__ == "__main__":
    async def main():
        # Initialize notification service
        service = NotificationService()
        
        # Create test alert
        test_alert = Alert(
            id="test-001",
            title="Test Critical Alert",
            description="This is a test critical alert for system validation",
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.SECURITY,
            system="notification-service",
            metadata={"test": True, "environment": "development"}
        )
        
        # Send test alert
        results = await service.send_alert(test_alert)
        
        print("Notification Results:")
        for result in results:
            print(f"  {result.channel.value}: {'✓' if result.success else '✗'} ({result.delivery_time:.2f}s)")
            if result.error:
                print(f"    Error: {result.error}")
        
        # Health check
        health = await service.health_check()
        print(f"\nHealth Status: {health['overall']}")
        for channel, status in health['channels'].items():
            print(f"  {channel}: {'✓' if status['healthy'] else '✗'}")
    
    # Run the example
    asyncio.run(main())