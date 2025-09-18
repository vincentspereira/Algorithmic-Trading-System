"""Institutional-Grade Real-Time Performance Monitoring System

Real-time performance monitoring for production deployments with:
- Critical performance threshold alerts
- Resource utilization tracking
- Comprehensive logging and troubleshooting
- Integration with Apache Kafka event bus

Compliance: Institutional-Grade Technical Standards
Author: Vincent S. Pereira
Version: 1.0.0
"""

import time
import json
import psutil
import logging
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque, defaultdict
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from contextlib import contextmanager
try:
    import smtplib
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False
    print("Warning: Email functionality not available - alerts will use logging only")

try:
    import kafka
    from kafka import KafkaProducer, KafkaConsumer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    print("Warning: Kafka not available - using local monitoring only")

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("Warning: Redis not available - using in-memory storage")


@dataclass
class PerformanceMetric:
    """Container for performance metrics with institutional-grade tracking."""
    name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    component: str = "system"
    severity: str = "info"  # info, warning, critical
    threshold_breached: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'value': self.value,
            'unit': self.unit,
            'timestamp': self.timestamp.isoformat(),
            'component': self.component,
            'severity': self.severity,
            'threshold_breached': self.threshold_breached
        }


@dataclass
class AlertRule:
    """Alert rule configuration for performance thresholds."""
    metric_name: str
    threshold: float
    operator: str  # '>', '<', '>=', '<=', '==', '!='
    severity: str  # 'warning', 'critical'
    cooldown_minutes: int = 5
    description: str = ""
    enabled: bool = True
    last_triggered: Optional[datetime] = None
    
    def should_trigger(self, value: float) -> bool:
        """Check if alert should be triggered."""
        if not self.enabled:
            return False
            
        # Check cooldown period
        if self.last_triggered:
            cooldown_delta = timedelta(minutes=self.cooldown_minutes)
            if datetime.now() - self.last_triggered < cooldown_delta:
                return False
        
        # Evaluate threshold
        if self.operator == '>':
            return value > self.threshold
        elif self.operator == '<':
            return value < self.threshold
        elif self.operator == '>=':
            return value >= self.threshold
        elif self.operator == '<=':
            return value <= self.threshold
        elif self.operator == '==':
            return value == self.threshold
        elif self.operator == '!=':
            return value != self.threshold
        
        return False


class AlertHandler(ABC):
    """Abstract base class for alert handlers."""
    
    @abstractmethod
    def send_alert(self, metric: PerformanceMetric, rule: AlertRule) -> bool:
        """Send alert notification."""
        pass


class EmailAlertHandler(AlertHandler):
    """Email alert handler for critical notifications."""
    
    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str,
                 recipients: List[str]):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.recipients = recipients
        self.email_available = EMAIL_AVAILABLE
    
    def send_alert(self, metric: PerformanceMetric, rule: AlertRule) -> bool:
        """Send email alert."""
        if not self.email_available:
            logging.warning("Email functionality not available - skipping email alert")
            return False
            
        try:
            msg = MimeMultipart()
            msg['From'] = self.username
            msg['To'] = ', '.join(self.recipients)
            msg['Subject'] = f"[{rule.severity.upper()}] Performance Alert: {metric.name}"
            
            body = f"""
            Performance Alert Triggered
            
            Metric: {metric.name}
            Current Value: {metric.value} {metric.unit}
            Threshold: {rule.threshold} {metric.unit}
            Severity: {rule.severity}
            Component: {metric.component}
            Time: {metric.timestamp}
            
            Description: {rule.description}
            
            Please investigate immediately.
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to send email alert: {str(e)}")
            return False


class LogAlertHandler(AlertHandler):
    """Log-based alert handler for all notifications."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def send_alert(self, metric: PerformanceMetric, rule: AlertRule) -> bool:
        """Log alert message."""
        try:
            alert_msg = (
                f"ALERT [{rule.severity.upper()}]: {metric.name} = {metric.value} {metric.unit} "
                f"(threshold: {rule.threshold}, component: {metric.component})"
            )
            
            if rule.severity == 'critical':
                self.logger.critical(alert_msg)
            elif rule.severity == 'warning':
                self.logger.warning(alert_msg)
            else:
                self.logger.info(alert_msg)
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to log alert: {str(e)}")
            return False


class KafkaAlertHandler(AlertHandler):
    """Kafka-based alert handler for event-driven notifications."""
    
    def __init__(self, kafka_servers: List[str], topic: str = "performance_alerts"):
        self.kafka_servers = kafka_servers
        self.topic = topic
        self.producer = None
        
        if KAFKA_AVAILABLE:
            try:
                self.producer = KafkaProducer(
                    bootstrap_servers=kafka_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8')
                )
            except Exception as e:
                logging.error(f"Failed to initialize Kafka producer: {str(e)}")
    
    def send_alert(self, metric: PerformanceMetric, rule: AlertRule) -> bool:
        """Send alert to Kafka topic."""
        if not self.producer:
            return False
            
        try:
            alert_data = {
                'alert_type': 'performance_threshold',
                'metric': metric.to_dict(),
                'rule': {
                    'name': rule.metric_name,
                    'threshold': rule.threshold,
                    'operator': rule.operator,
                    'severity': rule.severity,
                    'description': rule.description
                },
                'timestamp': datetime.now().isoformat()
            }
            
            self.producer.send(self.topic, alert_data)
            self.producer.flush()
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to send Kafka alert: {str(e)}")
            return False


class InstitutionalPerformanceMonitor:
    """Institutional-grade real-time performance monitoring system."""
    
    def __init__(self, config_path: str = "monitoring/config.json"):
        self.config_path = Path(config_path)
        self.monitoring_active = False
        self.metrics_history = defaultdict(lambda: deque(maxlen=1000))
        self.alert_rules: Dict[str, AlertRule] = {}
        self.alert_handlers: List[AlertHandler] = []
        
        # Create monitoring directory
        self.monitoring_dir = Path("monitoring/logs")
        self.monitoring_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        log_file = self.monitoring_dir / f"performance_monitor_{datetime.now().strftime('%Y%m%d')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self._load_configuration()
        self._setup_alert_handlers()
        self._setup_default_alert_rules()
        
        # Monitoring thread
        self.monitoring_thread = None
        self.stop_monitoring = threading.Event()
        
        self.logger.info("Institutional Performance Monitor initialized")
    
    def _load_configuration(self):
        """Load monitoring configuration from file."""
        default_config = {
            "monitoring_interval": 5,  # seconds
            "metrics_retention_hours": 24,
            "kafka_servers": ["localhost:9092"],
            "redis_host": "localhost",
            "redis_port": 6379,
            "email_alerts": {
                "enabled": False,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "",
                "password": "",
                "recipients": []
            }
        }
        
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
                self.logger.info(f"Configuration loaded from {self.config_path}")
            except Exception as e:
                self.logger.warning(f"Failed to load config, using defaults: {str(e)}")
                self.config = default_config
        else:
            self.config = default_config
            # Save default configuration
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            self.logger.info(f"Default configuration saved to {self.config_path}")
    
    def _setup_alert_handlers(self):
        """Setup alert handlers based on configuration."""
        # Always add log handler
        self.alert_handlers.append(LogAlertHandler(self.logger))
        
        # Add email handler if configured
        email_config = self.config.get("email_alerts", {})
        if email_config.get("enabled", False):
            try:
                email_handler = EmailAlertHandler(
                    smtp_server=email_config["smtp_server"],
                    smtp_port=email_config["smtp_port"],
                    username=email_config["username"],
                    password=email_config["password"],
                    recipients=email_config["recipients"]
                )
                self.alert_handlers.append(email_handler)
                self.logger.info("Email alert handler configured")
            except Exception as e:
                self.logger.error(f"Failed to setup email alerts: {str(e)}")
        
        # Add Kafka handler if available
        if KAFKA_AVAILABLE:
            try:
                kafka_handler = KafkaAlertHandler(self.config["kafka_servers"])
                self.alert_handlers.append(kafka_handler)
                self.logger.info("Kafka alert handler configured")
            except Exception as e:
                self.logger.error(f"Failed to setup Kafka alerts: {str(e)}")
    
    def _setup_default_alert_rules(self):
        """Setup default alert rules for critical performance metrics."""
        default_rules = [
            AlertRule(
                metric_name="cpu_usage_percent",
                threshold=80.0,
                operator=">",
                severity="warning",
                description="High CPU usage detected"
            ),
            AlertRule(
                metric_name="cpu_usage_percent",
                threshold=95.0,
                operator=">",
                severity="critical",
                description="Critical CPU usage detected"
            ),
            AlertRule(
                metric_name="memory_usage_percent",
                threshold=85.0,
                operator=">",
                severity="warning",
                description="High memory usage detected"
            ),
            AlertRule(
                metric_name="memory_usage_percent",
                threshold=95.0,
                operator=">",
                severity="critical",
                description="Critical memory usage detected"
            ),
            AlertRule(
                metric_name="disk_usage_percent",
                threshold=90.0,
                operator=">",
                severity="warning",
                description="High disk usage detected"
            ),
            AlertRule(
                metric_name="execution_time_ms",
                threshold=1000.0,
                operator=">",
                severity="warning",
                description="Slow execution time detected"
            ),
            AlertRule(
                metric_name="execution_time_ms",
                threshold=5000.0,
                operator=">",
                severity="critical",
                description="Critical execution time detected"
            )
        ]
        
        for rule in default_rules:
            self.alert_rules[f"{rule.metric_name}_{rule.severity}"] = rule
        
        self.logger.info(f"Configured {len(default_rules)} default alert rules")
    
    def add_alert_rule(self, rule: AlertRule) -> str:
        """Add custom alert rule."""
        rule_id = f"{rule.metric_name}_{rule.severity}_{int(time.time())}"
        self.alert_rules[rule_id] = rule
        self.logger.info(f"Added alert rule: {rule_id}")
        return rule_id
    
    def remove_alert_rule(self, rule_id: str) -> bool:
        """Remove alert rule."""
        if rule_id in self.alert_rules:
            del self.alert_rules[rule_id]
            self.logger.info(f"Removed alert rule: {rule_id}")
            return True
        return False
    
    def collect_system_metrics(self) -> List[PerformanceMetric]:
        """Collect system performance metrics."""
        metrics = []
        
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics.append(PerformanceMetric(
                name="cpu_usage_percent",
                value=cpu_percent,
                unit="%",
                component="system"
            ))
            
            # Memory metrics
            memory = psutil.virtual_memory()
            metrics.append(PerformanceMetric(
                name="memory_usage_percent",
                value=memory.percent,
                unit="%",
                component="system"
            ))
            
            metrics.append(PerformanceMetric(
                name="memory_available_gb",
                value=memory.available / (1024**3),
                unit="GB",
                component="system"
            ))
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            metrics.append(PerformanceMetric(
                name="disk_usage_percent",
                value=(disk.used / disk.total) * 100,
                unit="%",
                component="system"
            ))
            
            # Network metrics
            network = psutil.net_io_counters()
            metrics.append(PerformanceMetric(
                name="network_bytes_sent",
                value=network.bytes_sent,
                unit="bytes",
                component="network"
            ))
            
            metrics.append(PerformanceMetric(
                name="network_bytes_recv",
                value=network.bytes_recv,
                unit="bytes",
                component="network"
            ))
            
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {str(e)}")
        
        return metrics
    
    def record_metric(self, metric: PerformanceMetric):
        """Record a performance metric and check alert rules."""
        # Store metric in history
        self.metrics_history[metric.name].append(metric)
        
        # Check alert rules
        self._check_alert_rules(metric)
        
        # Log metric (debug level)
        self.logger.debug(f"Recorded metric: {metric.name} = {metric.value} {metric.unit}")
    
    def _check_alert_rules(self, metric: PerformanceMetric):
        """Check if metric triggers any alert rules."""
        for rule_id, rule in self.alert_rules.items():
            if rule.metric_name == metric.name and rule.should_trigger(metric.value):
                # Update rule trigger time
                rule.last_triggered = datetime.now()
                
                # Mark metric as threshold breached
                metric.threshold_breached = True
                metric.severity = rule.severity
                
                # Send alerts
                self._send_alerts(metric, rule)
    
    def _send_alerts(self, metric: PerformanceMetric, rule: AlertRule):
        """Send alerts through all configured handlers."""
        for handler in self.alert_handlers:
            try:
                success = handler.send_alert(metric, rule)
                if not success:
                    self.logger.warning(f"Alert handler {type(handler).__name__} failed")
            except Exception as e:
                self.logger.error(f"Error in alert handler {type(handler).__name__}: {str(e)}")
    
    @contextmanager
    def performance_context(self, operation_name: str, component: str = "application"):
        """Context manager for measuring operation performance."""
        start_time = time.perf_counter()
        start_memory = psutil.Process().memory_info().rss
        
        try:
            yield
        finally:
            end_time = time.perf_counter()
            end_memory = psutil.Process().memory_info().rss
            
            # Record execution time
            execution_time_ms = (end_time - start_time) * 1000
            self.record_metric(PerformanceMetric(
                name="execution_time_ms",
                value=execution_time_ms,
                unit="ms",
                component=component
            ))
            
            # Record memory delta
            memory_delta_mb = (end_memory - start_memory) / (1024 * 1024)
            self.record_metric(PerformanceMetric(
                name="memory_delta_mb",
                value=memory_delta_mb,
                unit="MB",
                component=component
            ))
    
    def start_monitoring(self):
        """Start continuous performance monitoring."""
        if self.monitoring_active:
            self.logger.warning("Monitoring already active")
            return
        
        self.monitoring_active = True
        self.stop_monitoring.clear()
        
        def monitoring_loop():
            self.logger.info("Performance monitoring started")
            
            while not self.stop_monitoring.is_set():
                try:
                    # Collect system metrics
                    metrics = self.collect_system_metrics()
                    
                    # Record all metrics
                    for metric in metrics:
                        self.record_metric(metric)
                    
                    # Wait for next collection interval
                    self.stop_monitoring.wait(self.config["monitoring_interval"])
                    
                except Exception as e:
                    self.logger.error(f"Error in monitoring loop: {str(e)}")
                    time.sleep(5)  # Brief pause before retrying
            
            self.logger.info("Performance monitoring stopped")
        
        self.monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
        self.monitoring_thread.start()
    
    def stop_monitoring_service(self):
        """Stop continuous performance monitoring."""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        self.stop_monitoring.set()
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10)
        
        self.logger.info("Performance monitoring service stopped")
    
    def get_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get summary of metrics for the specified time period."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        summary = {}
        
        for metric_name, metric_history in self.metrics_history.items():
            recent_metrics = [
                m for m in metric_history 
                if m.timestamp >= cutoff_time
            ]
            
            if recent_metrics:
                values = [m.value for m in recent_metrics]
                summary[metric_name] = {
                    'count': len(values),
                    'avg': float(np.mean(values)),
                    'min': float(np.min(values)),
                    'max': float(np.max(values)),
                    'std': float(np.std(values)),
                    'latest': float(values[-1]),
                    'unit': recent_metrics[-1].unit
                }
        
        return summary
    
    def export_metrics(self, filename: str = None) -> str:
        """Export metrics history to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_metrics_{timestamp}.json"
        
        filepath = self.monitoring_dir / filename
        
        # Convert metrics to serializable format
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'metrics_summary': self.get_metrics_summary(24),  # Last 24 hours
            'alert_rules': {
                rule_id: {
                    'metric_name': rule.metric_name,
                    'threshold': rule.threshold,
                    'operator': rule.operator,
                    'severity': rule.severity,
                    'description': rule.description,
                    'enabled': rule.enabled
                }
                for rule_id, rule in self.alert_rules.items()
            },
            'configuration': self.config
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        self.logger.info(f"Metrics exported to: {filepath}")
        return str(filepath)


def main():
    """Main execution function for performance monitoring."""
    print("Institutional-Grade Real-Time Performance Monitor")
    print("=" * 50)
    
    # Initialize monitor
    monitor = InstitutionalPerformanceMonitor()
    
    try:
        # Start monitoring
        print("\nStarting performance monitoring...")
        monitor.start_monitoring()
        
        # Run for demonstration (in production, this would run continuously)
        print("Monitoring active. Press Ctrl+C to stop.")
        
        # Simulate some operations
        for i in range(10):
            with monitor.performance_context(f"demo_operation_{i}", "demo"):
                # Simulate work
                time.sleep(0.1)
                # Simulate memory allocation
                data = np.random.random(1000)
                result = np.sum(data)
            
            time.sleep(2)
        
        # Get metrics summary
        print("\nMetrics Summary (last hour):")
        summary = monitor.get_metrics_summary(1)
        for metric_name, stats in summary.items():
            print(f"- {metric_name}: avg={stats['avg']:.2f} {stats['unit']}, "
                  f"min={stats['min']:.2f}, max={stats['max']:.2f}")
        
        # Export metrics
        export_file = monitor.export_metrics()
        print(f"\nMetrics exported to: {export_file}")
        
    except KeyboardInterrupt:
        print("\nStopping monitoring...")
    finally:
        monitor.stop_monitoring_service()
        print("Performance monitoring stopped.")


if __name__ == "__main__":
    main()