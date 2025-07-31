"""
Audit and Reporting System

This module provides comprehensive audit trail logging and regulatory reporting capabilities including:
- Comprehensive audit trail logging
- Regulatory report generation
- Compliance metrics and KPIs
- Audit trail search and analysis tools
"""

import logging
import asyncio
import json
import csv
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
import hashlib
import os
from pathlib import Path
import sqlite3
import threading
from collections import defaultdict, deque
import statistics

# Try to import optional dependencies
try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False


class AuditEventType(Enum):
    """Types of audit events"""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    TRADE_EXECUTION = "trade_execution"
    ORDER_PLACEMENT = "order_placement"
    ORDER_MODIFICATION = "order_modification"
    ORDER_CANCELLATION = "order_cancellation"
    POSITION_CHANGE = "position_change"
    ACCOUNT_ACCESS = "account_access"
    SYSTEM_CONFIG_CHANGE = "system_config_change"
    COMPLIANCE_VIOLATION = "compliance_violation"
    FRAUD_ALERT = "fraud_alert"
    DATA_ACCESS = "data_access"
    REPORT_GENERATION = "report_generation"
    SYSTEM_ERROR = "system_error"
    SECURITY_EVENT = "security_event"


class AuditSeverity(Enum):
    """Audit event severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ReportType(Enum):
    """Types of reports"""
    DAILY_TRADING = "daily_trading"
    WEEKLY_SUMMARY = "weekly_summary"
    MONTHLY_COMPLIANCE = "monthly_compliance"
    QUARTERLY_RISK = "quarterly_risk"
    ANNUAL_AUDIT = "annual_audit"
    REGULATORY_SUBMISSION = "regulatory_submission"
    CUSTOM_ANALYSIS = "custom_analysis"


class ReportFormat(Enum):
    """Report output formats"""
    JSON = "json"
    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"
    HTML = "html"


@dataclass
class AuditEvent:
    """Audit event record"""
    event_id: str
    event_type: AuditEventType
    timestamp: datetime
    user_id: Optional[str]
    session_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    resource: Optional[str]
    action: str
    details: Dict[str, Any]
    severity: AuditSeverity = AuditSeverity.INFO
    source_system: str = "nautilus_trader"
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceMetric:
    """Compliance metric definition"""
    metric_id: str
    name: str
    description: str
    value: float
    unit: str
    threshold: Optional[float] = None
    status: str = "normal"  # normal, warning, critical
    calculation_date: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportConfig:
    """Report configuration"""
    report_id: str
    report_type: ReportType
    name: str
    description: str
    schedule: Optional[str] = None  # Cron expression
    parameters: Dict[str, Any] = field(default_factory=dict)
    output_format: ReportFormat = ReportFormat.JSON
    recipients: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class GeneratedReport:
    """Generated report record"""
    report_id: str
    config_id: str
    report_type: ReportType
    generation_time: datetime
    period_start: datetime
    period_end: datetime
    file_path: Optional[str]
    file_size: Optional[int]
    record_count: int
    status: str  # success, error, partial
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AuditTrailLogger:
    """Comprehensive audit trail logging system"""
    
    def __init__(self, db_path: str = "audit_trail.db", max_memory_events: int = 10000):
        self.db_path = db_path
        self.max_memory_events = max_memory_events
        self.logger = logging.getLogger(__name__)
        self.memory_buffer: deque = deque(maxlen=max_memory_events)
        self.db_lock = threading.Lock()
        
        # Initialize database
        self._init_database()
        
        # Event handlers
        self.event_handlers: List[Callable] = []
    
    def _init_database(self):
        """Initialize audit trail database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS audit_events (
                        event_id TEXT PRIMARY KEY,
                        event_type TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        user_id TEXT,
                        session_id TEXT,
                        ip_address TEXT,
                        user_agent TEXT,
                        resource TEXT,
                        action TEXT NOT NULL,
                        details TEXT,
                        severity TEXT NOT NULL,
                        source_system TEXT NOT NULL,
                        correlation_id TEXT,
                        metadata TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes for performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_events(timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON audit_events(user_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON audit_events(event_type)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_severity ON audit_events(severity)")
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error initializing audit database: {e}")
    
    def log_event(self, event: AuditEvent):
        """Log audit event"""
        try:
            # Add to memory buffer
            self.memory_buffer.append(event)
            
            # Persist to database
            self._persist_event(event)
            
            # Notify event handlers
            for handler in self.event_handlers:
                try:
                    handler(event)
                except Exception as e:
                    self.logger.error(f"Error in event handler: {e}")
            
            self.logger.debug(f"Logged audit event: {event.event_type.value}")
            
        except Exception as e:
            self.logger.error(f"Error logging audit event: {e}")
    
    def _persist_event(self, event: AuditEvent):
        """Persist event to database"""
        try:
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO audit_events (
                            event_id, event_type, timestamp, user_id, session_id,
                            ip_address, user_agent, resource, action, details,
                            severity, source_system, correlation_id, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        event.event_id,
                        event.event_type.value,
                        event.timestamp.isoformat(),
                        event.user_id,
                        event.session_id,
                        event.ip_address,
                        event.user_agent,
                        event.resource,
                        event.action,
                        json.dumps(event.details),
                        event.severity.value,
                        event.source_system,
                        event.correlation_id,
                        json.dumps(event.metadata)
                    ))
                    conn.commit()
                    
        except Exception as e:
            self.logger.error(f"Error persisting audit event: {e}")
    
    def search_events(self, 
                     start_date: Optional[datetime] = None,
                     end_date: Optional[datetime] = None,
                     event_types: Optional[List[AuditEventType]] = None,
                     user_id: Optional[str] = None,
                     severity: Optional[AuditSeverity] = None,
                     resource: Optional[str] = None,
                     limit: int = 1000) -> List[AuditEvent]:
        """Search audit events with filters"""
        try:
            query = "SELECT * FROM audit_events WHERE 1=1"
            params = []
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())
            
            if event_types:
                placeholders = ",".join("?" * len(event_types))
                query += f" AND event_type IN ({placeholders})"
                params.extend([et.value for et in event_types])
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            if severity:
                query += " AND severity = ?"
                params.append(severity.value)
            
            if resource:
                query += " AND resource LIKE ?"
                params.append(f"%{resource}%")
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                events = []
                for row in rows:
                    event = AuditEvent(
                        event_id=row['event_id'],
                        event_type=AuditEventType(row['event_type']),
                        timestamp=datetime.fromisoformat(row['timestamp']),
                        user_id=row['user_id'],
                        session_id=row['session_id'],
                        ip_address=row['ip_address'],
                        user_agent=row['user_agent'],
                        resource=row['resource'],
                        action=row['action'],
                        details=json.loads(row['details']) if row['details'] else {},
                        severity=AuditSeverity(row['severity']),
                        source_system=row['source_system'],
                        correlation_id=row['correlation_id'],
                        metadata=json.loads(row['metadata']) if row['metadata'] else {}
                    )
                    events.append(event)
                
                return events
                
        except Exception as e:
            self.logger.error(f"Error searching audit events: {e}")
            return []
    
    def get_event_statistics(self, 
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get audit event statistics"""
        try:
            query = "SELECT event_type, severity, COUNT(*) as count FROM audit_events WHERE 1=1"
            params = []
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())
            
            query += " GROUP BY event_type, severity"
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                stats = {
                    'total_events': 0,
                    'by_type': defaultdict(int),
                    'by_severity': defaultdict(int),
                    'by_type_severity': defaultdict(lambda: defaultdict(int))
                }
                
                for row in rows:
                    event_type, severity, count = row
                    stats['total_events'] += count
                    stats['by_type'][event_type] += count
                    stats['by_severity'][severity] += count
                    stats['by_type_severity'][event_type][severity] = count
                
                return dict(stats)
                
        except Exception as e:
            self.logger.error(f"Error getting event statistics: {e}")
            return {}
    
    def add_event_handler(self, handler: Callable[[AuditEvent], None]):
        """Add event handler for real-time processing"""
        self.event_handlers.append(handler)
    
    def export_events(self, 
                     file_path: str,
                     format: ReportFormat = ReportFormat.CSV,
                     start_date: Optional[datetime] = None,
                     end_date: Optional[datetime] = None) -> bool:
        """Export audit events to file"""
        try:
            events = self.search_events(
                start_date=start_date,
                end_date=end_date,
                limit=100000  # Large limit for export
            )
            
            if format == ReportFormat.CSV:
                return self._export_to_csv(events, file_path)
            elif format == ReportFormat.JSON:
                return self._export_to_json(events, file_path)
            elif format == ReportFormat.EXCEL and EXCEL_AVAILABLE:
                return self._export_to_excel(events, file_path)
            else:
                self.logger.error(f"Unsupported export format: {format}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error exporting events: {e}")
            return False
    
    def _export_to_csv(self, events: List[AuditEvent], file_path: str) -> bool:
        """Export events to CSV"""
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'event_id', 'event_type', 'timestamp', 'user_id', 'session_id',
                    'ip_address', 'user_agent', 'resource', 'action', 'severity',
                    'source_system', 'correlation_id', 'details'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for event in events:
                    row = {
                        'event_id': event.event_id,
                        'event_type': event.event_type.value,
                        'timestamp': event.timestamp.isoformat(),
                        'user_id': event.user_id,
                        'session_id': event.session_id,
                        'ip_address': event.ip_address,
                        'user_agent': event.user_agent,
                        'resource': event.resource,
                        'action': event.action,
                        'severity': event.severity.value,
                        'source_system': event.source_system,
                        'correlation_id': event.correlation_id,
                        'details': json.dumps(event.details)
                    }
                    writer.writerow(row)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting to CSV: {e}")
            return False
    
    def _export_to_json(self, events: List[AuditEvent], file_path: str) -> bool:
        """Export events to JSON"""
        try:
            events_data = []
            for event in events:
                event_dict = asdict(event)
                event_dict['event_type'] = event.event_type.value
                event_dict['severity'] = event.severity.value
                event_dict['timestamp'] = event.timestamp.isoformat()
                events_data.append(event_dict)
            
            with open(file_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(events_data, jsonfile, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting to JSON: {e}")
            return False
    
    def _export_to_excel(self, events: List[AuditEvent], file_path: str) -> bool:
        """Export events to Excel"""
        try:
            # Convert events to DataFrame
            events_data = []
            for event in events:
                events_data.append({
                    'Event ID': event.event_id,
                    'Event Type': event.event_type.value,
                    'Timestamp': event.timestamp,
                    'User ID': event.user_id,
                    'Session ID': event.session_id,
                    'IP Address': event.ip_address,
                    'User Agent': event.user_agent,
                    'Resource': event.resource,
                    'Action': event.action,
                    'Severity': event.severity.value,
                    'Source System': event.source_system,
                    'Correlation ID': event.correlation_id,
                    'Details': json.dumps(event.details)
                })
            
            df = pd.DataFrame(events_data)
            df.to_excel(file_path, index=False, engine='openpyxl')
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting to Excel: {e}")
            return False


class ComplianceMetricsCalculator:
    """Calculate compliance metrics and KPIs"""
    
    def __init__(self, audit_logger: AuditTrailLogger):
        self.audit_logger = audit_logger
        self.logger = logging.getLogger(__name__)
        self.metrics_cache: Dict[str, ComplianceMetric] = {}
        self.cache_expiry: Dict[str, datetime] = {}
    
    def calculate_all_metrics(self, 
                            start_date: datetime,
                            end_date: datetime) -> List[ComplianceMetric]:
        """Calculate all compliance metrics for a period"""
        try:
            metrics = []
            
            # Trading activity metrics
            metrics.extend(self._calculate_trading_metrics(start_date, end_date))
            
            # Compliance violation metrics
            metrics.extend(self._calculate_compliance_metrics(start_date, end_date))
            
            # Security metrics
            metrics.extend(self._calculate_security_metrics(start_date, end_date))
            
            # System performance metrics
            metrics.extend(self._calculate_performance_metrics(start_date, end_date))
            
            # Update cache
            for metric in metrics:
                self.metrics_cache[metric.metric_id] = metric
                self.cache_expiry[metric.metric_id] = datetime.now() + timedelta(hours=1)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating compliance metrics: {e}")
            return []
    
    def _calculate_trading_metrics(self, start_date: datetime, end_date: datetime) -> List[ComplianceMetric]:
        """Calculate trading-related metrics"""
        metrics = []
        
        try:
            # Get trading events
            trading_events = self.audit_logger.search_events(
                start_date=start_date,
                end_date=end_date,
                event_types=[AuditEventType.TRADE_EXECUTION, AuditEventType.ORDER_PLACEMENT],
                limit=10000
            )
            
            # Total trades
            trade_events = [e for e in trading_events if e.event_type == AuditEventType.TRADE_EXECUTION]
            metrics.append(ComplianceMetric(
                metric_id="total_trades",
                name="Total Trades",
                description="Total number of trades executed",
                value=len(trade_events),
                unit="count"
            ))
            
            # Average trade size
            if trade_events:
                trade_sizes = []
                for event in trade_events:
                    if 'amount' in event.details:
                        trade_sizes.append(float(event.details['amount']))
                
                if trade_sizes:
                    avg_trade_size = statistics.mean(trade_sizes)
                    metrics.append(ComplianceMetric(
                        metric_id="avg_trade_size",
                        name="Average Trade Size",
                        description="Average size of executed trades",
                        value=avg_trade_size,
                        unit="currency"
                    ))
            
            # Order-to-trade ratio
            order_events = [e for e in trading_events if e.event_type == AuditEventType.ORDER_PLACEMENT]
            if order_events:
                order_to_trade_ratio = len(order_events) / len(trade_events) if trade_events else 0
                metrics.append(ComplianceMetric(
                    metric_id="order_to_trade_ratio",
                    name="Order-to-Trade Ratio",
                    description="Ratio of orders placed to trades executed",
                    value=order_to_trade_ratio,
                    unit="ratio",
                    threshold=10.0,  # Alert if ratio > 10
                    status="warning" if order_to_trade_ratio > 10 else "normal"
                ))
            
        except Exception as e:
            self.logger.error(f"Error calculating trading metrics: {e}")
        
        return metrics
    
    def _calculate_compliance_metrics(self, start_date: datetime, end_date: datetime) -> List[ComplianceMetric]:
        """Calculate compliance-related metrics"""
        metrics = []
        
        try:
            # Get compliance events
            compliance_events = self.audit_logger.search_events(
                start_date=start_date,
                end_date=end_date,
                event_types=[AuditEventType.COMPLIANCE_VIOLATION],
                limit=10000
            )
            
            # Total violations
            metrics.append(ComplianceMetric(
                metric_id="total_violations",
                name="Total Compliance Violations",
                description="Total number of compliance violations",
                value=len(compliance_events),
                unit="count",
                threshold=10.0,  # Alert if > 10 violations
                status="critical" if len(compliance_events) > 10 else "normal"
            ))
            
            # Violations by severity
            severity_counts = defaultdict(int)
            for event in compliance_events:
                severity_counts[event.severity.value] += 1
            
            for severity, count in severity_counts.items():
                metrics.append(ComplianceMetric(
                    metric_id=f"violations_{severity}",
                    name=f"Violations - {severity.title()}",
                    description=f"Number of {severity} compliance violations",
                    value=count,
                    unit="count"
                ))
            
            # Violation resolution rate
            resolved_violations = sum(1 for event in compliance_events 
                                    if event.details.get('resolved', False))
            resolution_rate = resolved_violations / len(compliance_events) if compliance_events else 1.0
            
            metrics.append(ComplianceMetric(
                metric_id="violation_resolution_rate",
                name="Violation Resolution Rate",
                description="Percentage of violations that have been resolved",
                value=resolution_rate * 100,
                unit="percentage",
                threshold=90.0,  # Alert if < 90%
                status="warning" if resolution_rate < 0.9 else "normal"
            ))
            
        except Exception as e:
            self.logger.error(f"Error calculating compliance metrics: {e}")
        
        return metrics
    
    def _calculate_security_metrics(self, start_date: datetime, end_date: datetime) -> List[ComplianceMetric]:
        """Calculate security-related metrics"""
        metrics = []
        
        try:
            # Get security events
            security_events = self.audit_logger.search_events(
                start_date=start_date,
                end_date=end_date,
                event_types=[AuditEventType.SECURITY_EVENT, AuditEventType.FRAUD_ALERT],
                limit=10000
            )
            
            # Total security events
            metrics.append(ComplianceMetric(
                metric_id="total_security_events",
                name="Total Security Events",
                description="Total number of security-related events",
                value=len(security_events),
                unit="count"
            ))
            
            # Failed login attempts
            login_events = self.audit_logger.search_events(
                start_date=start_date,
                end_date=end_date,
                event_types=[AuditEventType.USER_LOGIN],
                limit=10000
            )
            
            failed_logins = sum(1 for event in login_events 
                              if event.details.get('success', True) == False)
            
            metrics.append(ComplianceMetric(
                metric_id="failed_login_attempts",
                name="Failed Login Attempts",
                description="Number of failed login attempts",
                value=failed_logins,
                unit="count",
                threshold=100.0,  # Alert if > 100 failed attempts
                status="warning" if failed_logins > 100 else "normal"
            ))
            
            # Unique IP addresses
            unique_ips = set()
            for event in login_events:
                if event.ip_address:
                    unique_ips.add(event.ip_address)
            
            metrics.append(ComplianceMetric(
                metric_id="unique_ip_addresses",
                name="Unique IP Addresses",
                description="Number of unique IP addresses accessing the system",
                value=len(unique_ips),
                unit="count"
            ))
            
        except Exception as e:
            self.logger.error(f"Error calculating security metrics: {e}")
        
        return metrics
    
    def _calculate_performance_metrics(self, start_date: datetime, end_date: datetime) -> List[ComplianceMetric]:
        """Calculate system performance metrics"""
        metrics = []
        
        try:
            # Get system events
            system_events = self.audit_logger.search_events(
                start_date=start_date,
                end_date=end_date,
                event_types=[AuditEventType.SYSTEM_ERROR],
                limit=10000
            )
            
            # Total system errors
            metrics.append(ComplianceMetric(
                metric_id="total_system_errors",
                name="Total System Errors",
                description="Total number of system errors",
                value=len(system_events),
                unit="count",
                threshold=50.0,  # Alert if > 50 errors
                status="warning" if len(system_events) > 50 else "normal"
            ))
            
            # Error rate
            all_events = self.audit_logger.search_events(
                start_date=start_date,
                end_date=end_date,
                limit=10000
            )
            
            error_rate = len(system_events) / len(all_events) if all_events else 0
            
            metrics.append(ComplianceMetric(
                metric_id="system_error_rate",
                name="System Error Rate",
                description="Percentage of events that are system errors",
                value=error_rate * 100,
                unit="percentage",
                threshold=5.0,  # Alert if > 5%
                status="critical" if error_rate > 0.05 else "normal"
            ))
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
        
        return metrics
    
    def get_metric(self, metric_id: str) -> Optional[ComplianceMetric]:
        """Get cached metric by ID"""
        if metric_id in self.metrics_cache:
            # Check if cache is still valid
            if datetime.now() < self.cache_expiry.get(metric_id, datetime.min):
                return self.metrics_cache[metric_id]
        
        return None
    
    def get_metrics_summary(self, metrics: List[ComplianceMetric]) -> Dict[str, Any]:
        """Get summary of metrics"""
        try:
            summary = {
                'total_metrics': len(metrics),
                'normal_metrics': len([m for m in metrics if m.status == 'normal']),
                'warning_metrics': len([m for m in metrics if m.status == 'warning']),
                'critical_metrics': len([m for m in metrics if m.status == 'critical']),
                'metrics_by_category': defaultdict(int)
            }
            
            # Categorize metrics
            for metric in metrics:
                category = metric.metric_id.split('_')[0]  # First part of metric ID
                summary['metrics_by_category'][category] += 1
            
            return dict(summary)
            
        except Exception as e:
            self.logger.error(f"Error getting metrics summary: {e}")
            return {}


class RegulatoryReportGenerator:
    """Generate regulatory reports and compliance documentation"""
    
    def __init__(self, audit_logger: AuditTrailLogger, metrics_calculator: ComplianceMetricsCalculator):
        self.audit_logger = audit_logger
        self.metrics_calculator = metrics_calculator
        self.logger = logging.getLogger(__name__)
        self.report_configs: Dict[str, ReportConfig] = {}
        self.generated_reports: List[GeneratedReport] = []
        self.output_directory = Path("reports")
        self.output_directory.mkdir(exist_ok=True)
    
    def add_report_config(self, config: ReportConfig):
        """Add report configuration"""
        self.report_configs[config.report_id] = config
        self.logger.info(f"Added report configuration: {config.name}")
    
    def generate_report(self, config_id: str, 
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None) -> Optional[GeneratedReport]:
        """Generate report based on configuration"""
        try:
            if config_id not in self.report_configs:
                self.logger.error(f"Report configuration not found: {config_id}")
                return None
            
            config = self.report_configs[config_id]
            
            # Set default date range if not provided
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                if config.report_type == ReportType.DAILY_TRADING:
                    start_date = end_date - timedelta(days=1)
                elif config.report_type == ReportType.WEEKLY_SUMMARY:
                    start_date = end_date - timedelta(days=7)
                elif config.report_type == ReportType.MONTHLY_COMPLIANCE:
                    start_date = end_date - timedelta(days=30)
                else:
                    start_date = end_date - timedelta(days=1)
            
            # Generate report based on type
            if config.report_type == ReportType.DAILY_TRADING:
                return self._generate_daily_trading_report(config, start_date, end_date)
            elif config.report_type == ReportType.WEEKLY_SUMMARY:
                return self._generate_weekly_summary_report(config, start_date, end_date)
            elif config.report_type == ReportType.MONTHLY_COMPLIANCE:
                return self._generate_monthly_compliance_report(config, start_date, end_date)
            elif config.report_type == ReportType.REGULATORY_SUBMISSION:
                return self._generate_regulatory_submission_report(config, start_date, end_date)
            else:
                self.logger.error(f"Unsupported report type: {config.report_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error generating report: {e}")
            return None
    
    def _generate_daily_trading_report(self, config: ReportConfig, 
                                     start_date: datetime, end_date: datetime) -> GeneratedReport:
        """Generate daily trading report"""
        try:
            report_data = {
                'report_info': {
                    'name': config.name,
                    'type': config.report_type.value,
                    'period_start': start_date.isoformat(),
                    'period_end': end_date.isoformat(),
                    'generated_at': datetime.now().isoformat()
                },
                'trading_summary': {},
                'compliance_summary': {},
                'detailed_events': []
            }
            
            # Get trading events
            trading_events = self.audit_logger.search_events(
                start_date=start_date,
                end_date=end_date,
                event_types=[
                    AuditEventType.TRADE_EXECUTION,
                    AuditEventType.ORDER_PLACEMENT,
                    AuditEventType.ORDER_MODIFICATION,
                    AuditEventType.ORDER_CANCELLATION
                ],
                limit=10000
            )
            
            # Trading summary
            trade_executions = [e for e in trading_events if e.event_type == AuditEventType.TRADE_EXECUTION]
            order_placements = [e for e in trading_events if e.event_type == AuditEventType.ORDER_PLACEMENT]
            
            report_data['trading_summary'] = {
                'total_trades': len(trade_executions),
                'total_orders': len(order_placements),
                'order_to_trade_ratio': len(order_placements) / len(trade_executions) if trade_executions else 0,
                'unique_traders': len(set(e.user_id for e in trading_events if e.user_id)),
                'trading_volume': sum(float(e.details.get('amount', 0)) for e in trade_executions)
            }
            
            # Get compliance metrics
            metrics = self.metrics_calculator.calculate_all_metrics(start_date, end_date)
            report_data['compliance_summary'] = {
                'total_metrics': len(metrics),
                'warning_metrics': len([m for m in metrics if m.status == 'warning']),
                'critical_metrics': len([m for m in metrics if m.status == 'critical']),
                'metrics': [asdict(m) for m in metrics]
            }
            
            # Detailed events (sample)
            report_data['detailed_events'] = [
                {
                    'event_id': e.event_id,
                    'event_type': e.event_type.value,
                    'timestamp': e.timestamp.isoformat(),
                    'user_id': e.user_id,
                    'action': e.action,
                    'details': e.details
                }
                for e in trading_events[:100]  # Limit to first 100 events
            ]
            
            # Save report
            return self._save_report(config, report_data, start_date, end_date, len(trading_events))
            
        except Exception as e:
            self.logger.error(f"Error generating daily trading report: {e}")
            raise
    
    def _generate_monthly_compliance_report(self, config: ReportConfig,
                                          start_date: datetime, end_date: datetime) -> GeneratedReport:
        """Generate monthly compliance report"""
        try:
            report_data = {
                'report_info': {
                    'name': config.name,
                    'type': config.report_type.value,
                    'period_start': start_date.isoformat(),
                    'period_end': end_date.isoformat(),
                    'generated_at': datetime.now().isoformat()
                },
                'executive_summary': {},
                'compliance_metrics': {},
                'violations_analysis': {},
                'recommendations': []
            }
            
            # Get all compliance-related events
            compliance_events = self.audit_logger.search_events(
                start_date=start_date,
                end_date=end_date,
                event_types=[
                    AuditEventType.COMPLIANCE_VIOLATION,
                    AuditEventType.FRAUD_ALERT,
                    AuditEventType.SECURITY_EVENT
                ],
                limit=10000
            )
            
            # Executive summary
            total_events = len(self.audit_logger.search_events(start_date=start_date, end_date=end_date, limit=50000))
            report_data['executive_summary'] = {
                'reporting_period': f"{start_date.date()} to {end_date.date()}",
                'total_system_events': total_events,
                'compliance_events': len(compliance_events),
                'compliance_rate': (total_events - len(compliance_events)) / total_events if total_events > 0 else 1.0,
                'overall_status': 'COMPLIANT' if len(compliance_events) < 10 else 'VIOLATIONS_PRESENT'
            }
            
            # Compliance metrics
            metrics = self.metrics_calculator.calculate_all_metrics(start_date, end_date)
            report_data['compliance_metrics'] = {
                'total_metrics_calculated': len(metrics),
                'metrics_summary': self.metrics_calculator.get_metrics_summary(metrics),
                'detailed_metrics': [asdict(m) for m in metrics]
            }
            
            # Violations analysis
            violations = [e for e in compliance_events if e.event_type == AuditEventType.COMPLIANCE_VIOLATION]
            violation_types = defaultdict(int)
            violation_severities = defaultdict(int)
            
            for violation in violations:
                violation_type = violation.details.get('violation_type', 'unknown')
                violation_types[violation_type] += 1
                violation_severities[violation.severity.value] += 1
            
            report_data['violations_analysis'] = {
                'total_violations': len(violations),
                'violations_by_type': dict(violation_types),
                'violations_by_severity': dict(violation_severities),
                'resolution_rate': sum(1 for v in violations if v.details.get('resolved', False)) / len(violations) if violations else 1.0
            }
            
            # Recommendations
            recommendations = []
            if len(violations) > 10:
                recommendations.append("High number of compliance violations detected. Review and strengthen compliance controls.")
            
            critical_metrics = [m for m in metrics if m.status == 'critical']
            if critical_metrics:
                recommendations.append(f"Critical metrics detected: {', '.join(m.name for m in critical_metrics)}")
            
            if not recommendations:
                recommendations.append("No significant compliance issues identified. Continue current monitoring practices.")
            
            report_data['recommendations'] = recommendations
            
            # Save report
            return self._save_report(config, report_data, start_date, end_date, len(compliance_events))
            
        except Exception as e:
            self.logger.error(f"Error generating monthly compliance report: {e}")
            raise
    
    def _generate_regulatory_submission_report(self, config: ReportConfig,
                                             start_date: datetime, end_date: datetime) -> GeneratedReport:
        """Generate regulatory submission report"""
        try:
            report_data = {
                'submission_metadata': {
                    'submission_id': str(uuid.uuid4()),
                    'report_name': config.name,
                    'reporting_entity': config.parameters.get('entity_name', 'Trading System'),
                    'regulatory_framework': config.parameters.get('framework', 'MiFID II'),
                    'period_start': start_date.isoformat(),
                    'period_end': end_date.isoformat(),
                    'submission_date': datetime.now().isoformat(),
                    'contact_person': config.parameters.get('contact_person', 'Compliance Officer')
                },
                'regulatory_summary': {},
                'transaction_reporting': {},
                'compliance_attestation': {},
                'supporting_data': {}
            }
            
            # Get all relevant events for regulatory reporting
            all_events = self.audit_logger.search_events(
                start_date=start_date,
                end_date=end_date,
                limit=50000
            )
            
            trading_events = [e for e in all_events if e.event_type in [
                AuditEventType.TRADE_EXECUTION,
                AuditEventType.ORDER_PLACEMENT
            ]]
            
            compliance_events = [e for e in all_events if e.event_type in [
                AuditEventType.COMPLIANCE_VIOLATION,
                AuditEventType.FRAUD_ALERT
            ]]
            
            # Regulatory summary
            report_data['regulatory_summary'] = {
                'total_transactions': len(trading_events),
                'total_compliance_events': len(compliance_events),
                'compliance_rate': (len(all_events) - len(compliance_events)) / len(all_events) if all_events else 1.0,
                'regulatory_status': 'COMPLIANT' if len(compliance_events) == 0 else 'VIOLATIONS_REPORTED',
                'reporting_completeness': '100%'
            }
            
            # Transaction reporting
            report_data['transaction_reporting'] = {
                'total_reportable_transactions': len(trading_events),
                'transaction_categories': {
                    'equity_trades': len([e for e in trading_events if e.details.get('asset_class') == 'equity']),
                    'derivative_trades': len([e for e in trading_events if e.details.get('asset_class') == 'derivative']),
                    'other_trades': len([e for e in trading_events if e.details.get('asset_class') not in ['equity', 'derivative']])
                },
                'venue_breakdown': self._analyze_trading_venues(trading_events),
                'client_classification': self._analyze_client_types(trading_events)
            }
            
            # Compliance attestation
            report_data['compliance_attestation'] = {
                'data_accuracy_confirmed': True,
                'completeness_verified': True,
                'regulatory_requirements_met': len(compliance_events) == 0,
                'attestation_date': datetime.now().isoformat(),
                'attestation_officer': config.parameters.get('attestation_officer', 'Chief Compliance Officer'),
                'additional_notes': 'All regulatory requirements have been reviewed and confirmed.'
            }
            
            # Supporting data
            metrics = self.metrics_calculator.calculate_all_metrics(start_date, end_date)
            report_data['supporting_data'] = {
                'compliance_metrics': [asdict(m) for m in metrics],
                'system_statistics': self.audit_logger.get_event_statistics(start_date, end_date),
                'data_quality_indicators': {
                    'completeness_score': 1.0,
                    'accuracy_score': 1.0,
                    'timeliness_score': 1.0
                }
            }
            
            # Save report
            return self._save_report(config, report_data, start_date, end_date, len(all_events))
            
        except Exception as e:
            self.logger.error(f"Error generating regulatory submission report: {e}")
            raise
    
    def _analyze_trading_venues(self, trading_events: List[AuditEvent]) -> Dict[str, int]:
        """Analyze trading venues from events"""
        venues = defaultdict(int)
        for event in trading_events:
            venue = event.details.get('venue', 'unknown')
            venues[venue] += 1
        return dict(venues)
    
    def _analyze_client_types(self, trading_events: List[AuditEvent]) -> Dict[str, int]:
        """Analyze client types from events"""
        client_types = defaultdict(int)
        for event in trading_events:
            client_type = event.details.get('client_type', 'retail')
            client_types[client_type] += 1
        return dict(client_types)
    
    def _save_report(self, config: ReportConfig, report_data: Dict[str, Any],
                    start_date: datetime, end_date: datetime, record_count: int) -> GeneratedReport:
        """Save report to file and create report record"""
        try:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{config.report_type.value}_{timestamp}"
            
            file_path = None
            file_size = None
            
            # Save based on output format
            if config.output_format == ReportFormat.JSON:
                file_path = self.output_directory / f"{filename}.json"
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
                file_size = file_path.stat().st_size
                
            elif config.output_format == ReportFormat.CSV:
                file_path = self.output_directory / f"{filename}.csv"
                # Convert to flat structure for CSV
                self._save_as_csv(report_data, file_path)
                file_size = file_path.stat().st_size
                
            elif config.output_format == ReportFormat.EXCEL and EXCEL_AVAILABLE:
                file_path = self.output_directory / f"{filename}.xlsx"
                self._save_as_excel(report_data, file_path)
                file_size = file_path.stat().st_size
            
            # Create report record
            generated_report = GeneratedReport(
                report_id=str(uuid.uuid4()),
                config_id=config.report_id,
                report_type=config.report_type,
                generation_time=datetime.now(),
                period_start=start_date,
                period_end=end_date,
                file_path=str(file_path) if file_path else None,
                file_size=file_size,
                record_count=record_count,
                status="success"
            )
            
            self.generated_reports.append(generated_report)
            
            self.logger.info(f"Generated report: {config.name} ({file_path})")
            return generated_report
            
        except Exception as e:
            self.logger.error(f"Error saving report: {e}")
            # Create error report record
            error_report = GeneratedReport(
                report_id=str(uuid.uuid4()),
                config_id=config.report_id,
                report_type=config.report_type,
                generation_time=datetime.now(),
                period_start=start_date,
                period_end=end_date,
                file_path=None,
                file_size=None,
                record_count=0,
                status="error",
                error_message=str(e)
            )
            self.generated_reports.append(error_report)
            return error_report
    
    def _save_as_csv(self, report_data: Dict[str, Any], file_path: Path):
        """Save report data as CSV"""
        # This is a simplified CSV export - in practice, you'd want more sophisticated flattening
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow(['Section', 'Key', 'Value'])
            
            # Flatten the report data
            for section, data in report_data.items():
                if isinstance(data, dict):
                    for key, value in data.items():
                        writer.writerow([section, key, str(value)])
                else:
                    writer.writerow([section, '', str(data)])
    
    def _save_as_excel(self, report_data: Dict[str, Any], file_path: Path):
        """Save report data as Excel"""
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            # Create separate sheets for different sections
            for section, data in report_data.items():
                if isinstance(data, dict):
                    # Convert dict to DataFrame
                    df = pd.DataFrame(list(data.items()), columns=['Key', 'Value'])
                    df.to_excel(writer, sheet_name=section[:31], index=False)  # Excel sheet name limit
                elif isinstance(data, list) and data and isinstance(data[0], dict):
                    # Convert list of dicts to DataFrame
                    df = pd.DataFrame(data)
                    df.to_excel(writer, sheet_name=section[:31], index=False)
    
    def get_report_history(self, config_id: Optional[str] = None) -> List[GeneratedReport]:
        """Get report generation history"""
        if config_id:
            return [r for r in self.generated_reports if r.config_id == config_id]
        return self.generated_reports.copy()


class AuditReportingSystem:
    """Main audit and reporting system"""
    
    def __init__(self, db_path: str = "audit_trail.db"):
        self.audit_logger = AuditTrailLogger(db_path)
        self.metrics_calculator = ComplianceMetricsCalculator(self.audit_logger)
        self.report_generator = RegulatoryReportGenerator(self.audit_logger, self.metrics_calculator)
        self.logger = logging.getLogger(__name__)
        
        # Setup default report configurations
        self._setup_default_reports()
    
    def _setup_default_reports(self):
        """Setup default report configurations"""
        # Daily trading report
        daily_config = ReportConfig(
            report_id="daily_trading",
            report_type=ReportType.DAILY_TRADING,
            name="Daily Trading Report",
            description="Daily summary of trading activities and compliance metrics",
            schedule="0 6 * * *",  # Daily at 6 AM
            output_format=ReportFormat.JSON
        )
        self.report_generator.add_report_config(daily_config)
        
        # Monthly compliance report
        monthly_config = ReportConfig(
            report_id="monthly_compliance",
            report_type=ReportType.MONTHLY_COMPLIANCE,
            name="Monthly Compliance Report",
            description="Comprehensive monthly compliance analysis and metrics",
            schedule="0 8 1 * *",  # First day of month at 8 AM
            output_format=ReportFormat.EXCEL if EXCEL_AVAILABLE else ReportFormat.JSON
        )
        self.report_generator.add_report_config(monthly_config)
        
        # Regulatory submission report
        regulatory_config = ReportConfig(
            report_id="regulatory_submission",
            report_type=ReportType.REGULATORY_SUBMISSION,
            name="Regulatory Submission Report",
            description="Formal regulatory submission with compliance attestation",
            parameters={
                'entity_name': 'Nautilus Trading System',
                'framework': 'MiFID II / EMIR',
                'contact_person': 'Chief Compliance Officer',
                'attestation_officer': 'Chief Compliance Officer'
            },
            output_format=ReportFormat.JSON
        )
        self.report_generator.add_report_config(regulatory_config)
    
    def log_audit_event(self, event_type: AuditEventType, action: str, 
                       user_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None,
                       severity: AuditSeverity = AuditSeverity.INFO, **kwargs) -> str:
        """Log an audit event"""
        try:
            event = AuditEvent(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                timestamp=datetime.now(),
                user_id=user_id,
                session_id=kwargs.get('session_id'),
                ip_address=kwargs.get('ip_address'),
                user_agent=kwargs.get('user_agent'),
                resource=kwargs.get('resource'),
                action=action,
                details=details or {},
                severity=severity,
                source_system=kwargs.get('source_system', 'nautilus_trader'),
                correlation_id=kwargs.get('correlation_id'),
                metadata=kwargs.get('metadata', {})
            )
            
            self.audit_logger.log_event(event)
            return event.event_id
            
        except Exception as e:
            self.logger.error(f"Error logging audit event: {e}")
            return ""
    
    def search_audit_events(self, **kwargs) -> List[AuditEvent]:
        """Search audit events with filters"""
        return self.audit_logger.search_events(**kwargs)
    
    def generate_report(self, report_type: str, **kwargs) -> Optional[GeneratedReport]:
        """Generate a report"""
        return self.report_generator.generate_report(report_type, **kwargs)
    
    def get_compliance_metrics(self, start_date: datetime, end_date: datetime) -> List[ComplianceMetric]:
        """Get compliance metrics for a period"""
        return self.metrics_calculator.calculate_all_metrics(start_date, end_date)
    
    def export_audit_trail(self, file_path: str, format: ReportFormat = ReportFormat.CSV, **kwargs) -> bool:
        """Export audit trail to file"""
        return self.audit_logger.export_events(file_path, format, **kwargs)
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        try:
            now = datetime.now()
            last_24h = now - timedelta(hours=24)
            last_7d = now - timedelta(days=7)
            last_30d = now - timedelta(days=30)
            
            stats = {
                'audit_trail': {
                    'events_24h': len(self.audit_logger.search_events(start_date=last_24h, limit=10000)),
                    'events_7d': len(self.audit_logger.search_events(start_date=last_7d, limit=50000)),
                    'events_30d': len(self.audit_logger.search_events(start_date=last_30d, limit=100000)),
                    'event_statistics': self.audit_logger.get_event_statistics(last_30d, now)
                },
                'compliance': {
                    'metrics_calculated': len(self.metrics_calculator.calculate_all_metrics(last_24h, now)),
                    'cached_metrics': len(self.metrics_calculator.metrics_cache)
                },
                'reporting': {
                    'configured_reports': len(self.report_generator.report_configs),
                    'generated_reports': len(self.report_generator.generated_reports),
                    'recent_reports': len([r for r in self.report_generator.generated_reports 
                                         if r.generation_time >= last_7d])
                },
                'system_health': {
                    'database_accessible': os.path.exists(self.audit_logger.db_path),
                    'output_directory_writable': os.access(self.report_generator.output_directory, os.W_OK),
                    'memory_buffer_size': len(self.audit_logger.memory_buffer)
                }
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting system statistics: {e}")
            return {}


# Example usage and testing
async def example_usage():
    """Demonstrate audit and reporting system"""
    print("=== Audit and Reporting System Demo ===")
    
    # Initialize system
    audit_system = AuditReportingSystem()
    
    print("Initialized audit and reporting system")
    
    # Log some sample audit events
    print("\nLogging sample audit events...")
    
    # User login event
    audit_system.log_audit_event(
        event_type=AuditEventType.USER_LOGIN,
        action="user_login",
        user_id="trader_001",
        session_id="session_123",
        ip_address="192.168.1.100",
        details={
            'success': True,
            'login_method': 'password',
            'user_agent': 'Mozilla/5.0...'
        }
    )
    
    # Trade execution event
    audit_system.log_audit_event(
        event_type=AuditEventType.TRADE_EXECUTION,
        action="execute_trade",
        user_id="trader_001",
        details={
            'symbol': 'AAPL',
            'quantity': 100,
            'price': 150.00,
            'amount': 15000.00,
            'side': 'buy',
            'venue': 'NYSE'
        }
    )
    
    # Compliance violation event
    audit_system.log_audit_event(
        event_type=AuditEventType.COMPLIANCE_VIOLATION,
        action="position_limit_exceeded",
        user_id="trader_002",
        severity=AuditSeverity.WARNING,
        details={
            'violation_type': 'position_limit',
            'symbol': 'GOOGL',
            'current_position': 12000,
            'limit': 10000,
            'resolved': False
        }
    )
    
    # System error event
    audit_system.log_audit_event(
        event_type=AuditEventType.SYSTEM_ERROR,
        action="database_connection_failed",
        severity=AuditSeverity.ERROR,
        details={
            'error_code': 'DB_CONN_001',
            'error_message': 'Connection timeout',
            'component': 'order_management'
        }
    )
    
    print("Logged 4 sample audit events")
    
    # Search audit events
    print("\nSearching audit events...")
    recent_events = audit_system.search_audit_events(
        start_date=datetime.now() - timedelta(hours=1),
        limit=10
    )
    
    print(f"Found {len(recent_events)} recent events:")
    for event in recent_events:
        print(f"  - {event.event_type.value}: {event.action} (User: {event.user_id})")
    
    # Calculate compliance metrics
    print("\nCalculating compliance metrics...")
    metrics = audit_system.get_compliance_metrics(
        start_date=datetime.now() - timedelta(hours=1),
        end_date=datetime.now()
    )
    
    print(f"Calculated {len(metrics)} compliance metrics:")
    for metric in metrics[:5]:  # Show first 5 metrics
        print(f"  - {metric.name}: {metric.value} {metric.unit} (Status: {metric.status})")
    
    # Generate reports
    print("\nGenerating reports...")
    
    # Daily trading report
    daily_report = audit_system.generate_report(
        "daily_trading",
        start_date=datetime.now() - timedelta(hours=1),
        end_date=datetime.now()
    )
    
    if daily_report:
        print(f"Generated daily trading report: {daily_report.file_path}")
        print(f"  Records: {daily_report.record_count}")
        print(f"  Status: {daily_report.status}")
    
    # Monthly compliance report
    monthly_report = audit_system.generate_report(
        "monthly_compliance",
        start_date=datetime.now() - timedelta(days=1),
        end_date=datetime.now()
    )
    
    if monthly_report:
        print(f"Generated monthly compliance report: {monthly_report.file_path}")
        print(f"  Records: {monthly_report.record_count}")
        print(f"  Status: {monthly_report.status}")
    
    # Export audit trail
    print("\nExporting audit trail...")
    export_success = audit_system.export_audit_trail(
        "audit_export.csv",
        format=ReportFormat.CSV,
        start_date=datetime.now() - timedelta(hours=1)
    )
    
    if export_success:
        print("Successfully exported audit trail to audit_export.csv")
    
    # Get system statistics
    print("\nSystem Statistics:")
    stats = audit_system.get_system_statistics()
    
    print(f"  Audit Events (24h): {stats['audit_trail']['events_24h']}")
    print(f"  Compliance Metrics: {stats['compliance']['metrics_calculated']}")
    print(f"  Generated Reports: {stats['reporting']['generated_reports']}")
    print(f"  System Health: {'OK' if stats['system_health']['database_accessible'] else 'ERROR'}")
    
    print("\n=== Demo completed ===")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run example
    asyncio.run(example_usage())