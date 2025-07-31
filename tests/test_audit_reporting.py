"""
Tests for Audit and Reporting System
"""

import pytest
import asyncio
import tempfile
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from nautilus_trader_engine.reporting.audit_reporting import (
    AuditReportingSystem,
    AuditTrailLogger,
    ComplianceMetricsCalculator,
    RegulatoryReportGenerator,
    AuditEvent,
    ComplianceMetric,
    ReportConfig,
    GeneratedReport,
    AuditEventType,
    AuditSeverity,
    ReportType,
    ReportFormat
)


class TestAuditEvent:
    """Test AuditEvent data class"""
    
    def test_audit_event_creation(self):
        """Test creating an audit event"""
        event = AuditEvent(
            event_id="test_001",
            event_type=AuditEventType.USER_LOGIN,
            timestamp=datetime.now(),
            user_id="user_123",
            session_id="session_456",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            resource="/login",
            action="user_login",
            details={"success": True},
            severity=AuditSeverity.INFO
        )
        
        assert event.event_id == "test_001"
        assert event.event_type == AuditEventType.USER_LOGIN
        assert event.user_id == "user_123"
        assert event.details["success"] is True
        assert event.severity == AuditSeverity.INFO


class TestAuditTrailLogger:
    """Test audit trail logging"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        # Cleanup - try multiple times on Windows
        import time
        for _ in range(3):
            try:
                if os.path.exists(db_path):
                    os.unlink(db_path)
                break
            except PermissionError:
                time.sleep(0.1)
                continue
    
    @pytest.fixture
    def audit_logger(self, temp_db):
        return AuditTrailLogger(db_path=temp_db, max_memory_events=100)
    
    @pytest.fixture
    def sample_event(self):
        return AuditEvent(
            event_id="test_001",
            event_type=AuditEventType.TRADE_EXECUTION,
            timestamp=datetime.now(),
            user_id="trader_001",
            session_id="session_123",
            ip_address="192.168.1.1",
            user_agent="TradingApp/1.0",
            resource="/api/trades",
            action="execute_trade",
            details={
                "symbol": "AAPL",
                "quantity": 100,
                "price": 150.0,
                "side": "buy"
            },
            severity=AuditSeverity.INFO
        )
    
    def test_database_initialization(self, audit_logger):
        """Test database initialization"""
        assert os.path.exists(audit_logger.db_path)
        
        # Check if tables exist
        import sqlite3
        with sqlite3.connect(audit_logger.db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            assert 'audit_events' in tables  
  
    def test_log_event(self, audit_logger, sample_event):
        """Test logging an audit event"""
        audit_logger.log_event(sample_event)
        
        # Check memory buffer
        assert len(audit_logger.memory_buffer) == 1
        assert audit_logger.memory_buffer[0] == sample_event
        
        # Check database persistence
        events = audit_logger.search_events(limit=10)
        assert len(events) == 1
        assert events[0].event_id == sample_event.event_id
        assert events[0].event_type == sample_event.event_type
    
    def test_search_events_by_date(self, audit_logger):
        """Test searching events by date range"""
        now = datetime.now()
        
        # Create events with different timestamps
        event1 = AuditEvent(
            event_id="event_1",
            event_type=AuditEventType.USER_LOGIN,
            timestamp=now - timedelta(hours=2),
            user_id="user_1",
            session_id="session_1",
            ip_address="192.168.1.1",
            user_agent="TestAgent",
            resource="/login",
            action="login",
            details={}
        )
        
        event2 = AuditEvent(
            event_id="event_2",
            event_type=AuditEventType.USER_LOGIN,
            timestamp=now - timedelta(minutes=30),
            user_id="user_2",
            session_id="session_2",
            ip_address="192.168.1.2",
            user_agent="TestAgent",
            resource="/login",
            action="login",
            details={}
        )
        
        audit_logger.log_event(event1)
        audit_logger.log_event(event2)
        
        # Search for events in last hour
        recent_events = audit_logger.search_events(
            start_date=now - timedelta(hours=1)
        )
        
        assert len(recent_events) == 1
        assert recent_events[0].event_id == "event_2"
    
    def test_search_events_by_type(self, audit_logger):
        """Test searching events by type"""
        # Create events of different types
        login_event = AuditEvent(
            event_id="login_1",
            event_type=AuditEventType.USER_LOGIN,
            timestamp=datetime.now(),
            user_id="user_1",
            action="login",
            details={}
        )
        
        trade_event = AuditEvent(
            event_id="trade_1",
            event_type=AuditEventType.TRADE_EXECUTION,
            timestamp=datetime.now(),
            user_id="user_1",
            action="execute_trade",
            details={}
        )
        
        audit_logger.log_event(login_event)
        audit_logger.log_event(trade_event)
        
        # Search for login events only
        login_events = audit_logger.search_events(
            event_types=[AuditEventType.USER_LOGIN]
        )
        
        assert len(login_events) == 1
        assert login_events[0].event_type == AuditEventType.USER_LOGIN
    
    def test_search_events_by_user(self, audit_logger):
        """Test searching events by user ID"""
        # Create events for different users
        event1 = AuditEvent(
            event_id="event_1",
            event_type=AuditEventType.USER_LOGIN,
            timestamp=datetime.now(),
            user_id="user_1",
            action="login",
            details={}
        )
        
        event2 = AuditEvent(
            event_id="event_2",
            event_type=AuditEventType.USER_LOGIN,
            timestamp=datetime.now(),
            user_id="user_2",
            action="login",
            details={}
        )
        
        audit_logger.log_event(event1)
        audit_logger.log_event(event2)
        
        # Search for user_1 events
        user1_events = audit_logger.search_events(user_id="user_1")
        
        assert len(user1_events) == 1
        assert user1_events[0].user_id == "user_1"
    
    def test_get_event_statistics(self, audit_logger):
        """Test getting event statistics"""
        # Create events with different types and severities
        events = [
            AuditEvent(
                event_id=f"event_{i}",
                event_type=AuditEventType.USER_LOGIN if i % 2 == 0 else AuditEventType.TRADE_EXECUTION,
                timestamp=datetime.now(),
                user_id=f"user_{i}",
                action="test_action",
                details={},
                severity=AuditSeverity.INFO if i % 3 == 0 else AuditSeverity.WARNING
            )
            for i in range(5)
        ]
        
        for event in events:
            audit_logger.log_event(event)
        
        stats = audit_logger.get_event_statistics()
        
        assert stats['total_events'] == 5
        assert 'by_type' in stats
        assert 'by_severity' in stats
        assert stats['by_type']['user_login'] > 0
        assert stats['by_type']['trade_execution'] > 0
    
    def test_export_events_csv(self, audit_logger, sample_event):
        """Test exporting events to CSV"""
        audit_logger.log_event(sample_event)
        
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            csv_path = f.name
        
        try:
            success = audit_logger.export_events(csv_path, ReportFormat.CSV)
            assert success is True
            assert os.path.exists(csv_path)
            
            # Check file content
            with open(csv_path, 'r') as f:
                content = f.read()
                assert 'event_id' in content
                assert sample_event.event_id in content
        finally:
            if os.path.exists(csv_path):
                os.unlink(csv_path)
    
    def test_export_events_json(self, audit_logger, sample_event):
        """Test exporting events to JSON"""
        audit_logger.log_event(sample_event)
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            json_path = f.name
        
        try:
            success = audit_logger.export_events(json_path, ReportFormat.JSON)
            assert success is True
            assert os.path.exists(json_path)
            
            # Check file content
            with open(json_path, 'r') as f:
                data = json.load(f)
                assert isinstance(data, list)
                assert len(data) == 1
                assert data[0]['event_id'] == sample_event.event_id
        finally:
            if os.path.exists(json_path):
                os.unlink(json_path)


class TestComplianceMetricsCalculator:
    """Test compliance metrics calculation"""
    
    @pytest.fixture
    def temp_db(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def audit_logger(self, temp_db):
        return AuditTrailLogger(db_path=temp_db)
    
    @pytest.fixture
    def metrics_calculator(self, audit_logger):
        return ComplianceMetricsCalculator(audit_logger)
    
    def test_calculate_trading_metrics(self, metrics_calculator, audit_logger):
        """Test calculating trading metrics"""
        # Create sample trading events
        now = datetime.now()
        
        trade_events = [
            AuditEvent(
                event_id=f"trade_{i}",
                event_type=AuditEventType.TRADE_EXECUTION,
                timestamp=now - timedelta(minutes=i),
                user_id=f"trader_{i}",
                action="execute_trade",
                details={"amount": 1000 + i * 100}
            )
            for i in range(5)
        ]
        
        for event in trade_events:
            audit_logger.log_event(event)
        
        # Calculate metrics
        start_date = now - timedelta(hours=1)
        end_date = now
        
        metrics = metrics_calculator._calculate_trading_metrics(start_date, end_date)
        
        # Check that we got some trading metrics
        assert len(metrics) > 0
        
        # Check for specific metrics
        metric_names = [m.name for m in metrics]
        assert "Total Trades" in metric_names
    
    def test_calculate_compliance_metrics(self, metrics_calculator, audit_logger):
        """Test calculating compliance metrics"""
        # Create sample compliance events
        now = datetime.now()
        
        compliance_events = [
            AuditEvent(
                event_id=f"violation_{i}",
                event_type=AuditEventType.COMPLIANCE_VIOLATION,
                timestamp=now - timedelta(minutes=i),
                user_id=f"trader_{i}",
                action="position_limit_exceeded",
                details={"resolved": i % 2 == 0},
                severity=AuditSeverity.WARNING if i % 2 == 0 else AuditSeverity.ERROR
            )
            for i in range(3)
        ]
        
        for event in compliance_events:
            audit_logger.log_event(event)
        
        # Calculate metrics
        start_date = now - timedelta(hours=1)
        end_date = now
        
        metrics = metrics_calculator._calculate_compliance_metrics(start_date, end_date)
        
        # Check that we got compliance metrics
        assert len(metrics) > 0
        
        # Check for specific metrics
        metric_names = [m.name for m in metrics]
        assert "Total Compliance Violations" in metric_names
    
    def test_calculate_all_metrics(self, metrics_calculator, audit_logger):
        """Test calculating all metrics"""
        # Create various types of events
        now = datetime.now()
        
        events = [
            AuditEvent(
                event_id="trade_1",
                event_type=AuditEventType.TRADE_EXECUTION,
                timestamp=now,
                user_id="trader_1",
                action="execute_trade",
                details={"amount": 1000}
            ),
            AuditEvent(
                event_id="violation_1",
                event_type=AuditEventType.COMPLIANCE_VIOLATION,
                timestamp=now,
                user_id="trader_1",
                action="position_limit_exceeded",
                details={"resolved": False},
                severity=AuditSeverity.WARNING
            ),
            AuditEvent(
                event_id="login_1",
                event_type=AuditEventType.USER_LOGIN,
                timestamp=now,
                user_id="trader_1",
                action="login",
                details={"success": True}
            )
        ]
        
        for event in events:
            audit_logger.log_event(event)
        
        # Calculate all metrics
        start_date = now - timedelta(hours=1)
        end_date = now + timedelta(minutes=1)
        
        metrics = metrics_calculator.calculate_all_metrics(start_date, end_date)
        
        # Should have metrics from different categories
        assert len(metrics) > 0
        
        # Check metric types
        metric_categories = set()
        for metric in metrics:
            category = metric.metric_id.split('_')[0]
            metric_categories.add(category)
        
        # Should have multiple categories
        assert len(metric_categories) > 1
    
    def test_get_metrics_summary(self, metrics_calculator):
        """Test getting metrics summary"""
        # Create sample metrics
        metrics = [
            ComplianceMetric(
                metric_id="test_metric_1",
                name="Test Metric 1",
                description="Test metric",
                value=100,
                unit="count",
                status="normal"
            ),
            ComplianceMetric(
                metric_id="test_metric_2",
                name="Test Metric 2",
                description="Test metric",
                value=200,
                unit="count",
                status="warning"
            ),
            ComplianceMetric(
                metric_id="other_metric_1",
                name="Other Metric 1",
                description="Other metric",
                value=50,
                unit="count",
                status="critical"
            )
        ]
        
        summary = metrics_calculator.get_metrics_summary(metrics)
        
        assert summary['total_metrics'] == 3
        assert summary['normal_metrics'] == 1
        assert summary['warning_metrics'] == 1
        assert summary['critical_metrics'] == 1
        assert 'metrics_by_category' in summary
        assert summary['metrics_by_category']['test'] == 2
        assert summary['metrics_by_category']['other'] == 1


class TestRegulatoryReportGenerator:
    """Test regulatory report generation"""
    
    @pytest.fixture
    def temp_db(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def audit_logger(self, temp_db):
        return AuditTrailLogger(db_path=temp_db)
    
    @pytest.fixture
    def metrics_calculator(self, audit_logger):
        return ComplianceMetricsCalculator(audit_logger)
    
    @pytest.fixture
    def report_generator(self, audit_logger, metrics_calculator):
        return RegulatoryReportGenerator(audit_logger, metrics_calculator)
    
    def test_add_report_config(self, report_generator):
        """Test adding report configuration"""
        config = ReportConfig(
            report_id="test_report",
            report_type=ReportType.DAILY_TRADING,
            name="Test Report",
            description="Test report configuration"
        )
        
        report_generator.add_report_config(config)
        
        assert "test_report" in report_generator.report_configs
        assert report_generator.report_configs["test_report"] == config
    
    def test_generate_daily_trading_report(self, report_generator, audit_logger):
        """Test generating daily trading report"""
        # Add report configuration
        config = ReportConfig(
            report_id="daily_test",
            report_type=ReportType.DAILY_TRADING,
            name="Daily Test Report",
            description="Test daily trading report",
            output_format=ReportFormat.JSON
        )
        report_generator.add_report_config(config)
        
        # Create sample trading events
        now = datetime.now()
        events = [
            AuditEvent(
                event_id=f"trade_{i}",
                event_type=AuditEventType.TRADE_EXECUTION,
                timestamp=now - timedelta(minutes=i),
                user_id=f"trader_{i}",
                action="execute_trade",
                details={"amount": 1000 + i * 100}
            )
            for i in range(3)
        ]
        
        for event in events:
            audit_logger.log_event(event)
        
        # Generate report
        start_date = now - timedelta(hours=1)
        end_date = now
        
        generated_report = report_generator.generate_report("daily_test", start_date, end_date)
        
        assert generated_report is not None
        assert generated_report.status == "success"
        assert generated_report.record_count > 0
        assert generated_report.file_path is not None
        
        # Check if file was created
        assert os.path.exists(generated_report.file_path)
        
        # Check file content
        with open(generated_report.file_path, 'r') as f:
            report_data = json.load(f)
            assert 'report_info' in report_data
            assert 'trading_summary' in report_data
            assert report_data['trading_summary']['total_trades'] == 3
    
    def test_generate_monthly_compliance_report(self, report_generator, audit_logger):
        """Test generating monthly compliance report"""
        # Add report configuration
        config = ReportConfig(
            report_id="monthly_test",
            report_type=ReportType.MONTHLY_COMPLIANCE,
            name="Monthly Test Report",
            description="Test monthly compliance report",
            output_format=ReportFormat.JSON
        )
        report_generator.add_report_config(config)
        
        # Create sample compliance events
        now = datetime.now()
        events = [
            AuditEvent(
                event_id=f"violation_{i}",
                event_type=AuditEventType.COMPLIANCE_VIOLATION,
                timestamp=now - timedelta(hours=i),
                user_id=f"trader_{i}",
                action="position_limit_exceeded",
                details={"resolved": i % 2 == 0},
                severity=AuditSeverity.WARNING
            )
            for i in range(2)
        ]
        
        for event in events:
            audit_logger.log_event(event)
        
        # Generate report
        start_date = now - timedelta(days=1)
        end_date = now
        
        generated_report = report_generator.generate_report("monthly_test", start_date, end_date)
        
        assert generated_report is not None
        assert generated_report.status == "success"
        assert generated_report.file_path is not None
        
        # Check file content
        with open(generated_report.file_path, 'r') as f:
            report_data = json.load(f)
            assert 'executive_summary' in report_data
            assert 'compliance_metrics' in report_data
            assert 'violations_analysis' in report_data
    
    def test_get_report_history(self, report_generator):
        """Test getting report history"""
        # Initially no reports
        history = report_generator.get_report_history()
        initial_count = len(history)
        
        # Add a mock generated report
        mock_report = GeneratedReport(
            report_id="test_report_001",
            config_id="test_config",
            report_type=ReportType.DAILY_TRADING,
            generation_time=datetime.now(),
            period_start=datetime.now() - timedelta(days=1),
            period_end=datetime.now(),
            file_path="/tmp/test_report.json",
            file_size=1024,
            record_count=100,
            status="success"
        )
        
        report_generator.generated_reports.append(mock_report)
        
        # Check history
        history = report_generator.get_report_history()
        assert len(history) == initial_count + 1
        
        # Check filtered history
        filtered_history = report_generator.get_report_history("test_config")
        assert len(filtered_history) == 1
        assert filtered_history[0].config_id == "test_config"


class TestAuditReportingSystem:
    """Test main audit and reporting system"""
    
    @pytest.fixture
    def temp_db(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def audit_system(self, temp_db):
        return AuditReportingSystem(db_path=temp_db)
    
    def test_system_initialization(self, audit_system):
        """Test system initialization"""
        assert audit_system.audit_logger is not None
        assert audit_system.metrics_calculator is not None
        assert audit_system.report_generator is not None
        
        # Check default report configurations
        configs = audit_system.report_generator.report_configs
        assert len(configs) > 0
        assert "daily_trading" in configs
        assert "monthly_compliance" in configs
    
    def test_log_audit_event(self, audit_system):
        """Test logging audit event through main system"""
        event_id = audit_system.log_audit_event(
            event_type=AuditEventType.USER_LOGIN,
            action="user_login",
            user_id="test_user",
            details={"success": True}
        )
        
        assert event_id != ""
        
        # Verify event was logged
        events = audit_system.search_audit_events(user_id="test_user")
        assert len(events) == 1
        assert events[0].user_id == "test_user"
        assert events[0].action == "user_login"
    
    def test_search_audit_events(self, audit_system):
        """Test searching audit events"""
        # Log some events
        audit_system.log_audit_event(
            event_type=AuditEventType.TRADE_EXECUTION,
            action="execute_trade",
            user_id="trader_1",
            details={"symbol": "AAPL"}
        )
        
        audit_system.log_audit_event(
            event_type=AuditEventType.USER_LOGIN,
            action="login",
            user_id="trader_2",
            details={"success": True}
        )
        
        # Search all events
        all_events = audit_system.search_audit_events()
        assert len(all_events) >= 2
        
        # Search by user
        trader1_events = audit_system.search_audit_events(user_id="trader_1")
        assert len(trader1_events) == 1
        assert trader1_events[0].user_id == "trader_1"
    
    def test_generate_report(self, audit_system):
        """Test generating report through main system"""
        # Log some events first
        audit_system.log_audit_event(
            event_type=AuditEventType.TRADE_EXECUTION,
            action="execute_trade",
            user_id="trader_1",
            details={"amount": 1000}
        )
        
        # Generate daily report
        report = audit_system.generate_report(
            "daily_trading",
            start_date=datetime.now() - timedelta(hours=1),
            end_date=datetime.now()
        )
        
        assert report is not None
        assert report.status == "success"
        assert os.path.exists(report.file_path)
    
    def test_get_compliance_metrics(self, audit_system):
        """Test getting compliance metrics"""
        # Log some events
        audit_system.log_audit_event(
            event_type=AuditEventType.COMPLIANCE_VIOLATION,
            action="position_limit_exceeded",
            user_id="trader_1",
            severity=AuditSeverity.WARNING,
            details={"resolved": False}
        )
        
        # Get metrics
        start_date = datetime.now() - timedelta(hours=1)
        end_date = datetime.now()
        
        metrics = audit_system.get_compliance_metrics(start_date, end_date)
        
        assert isinstance(metrics, list)
        assert len(metrics) > 0
    
    def test_export_audit_trail(self, audit_system):
        """Test exporting audit trail"""
        # Log an event
        audit_system.log_audit_event(
            event_type=AuditEventType.USER_LOGIN,
            action="login",
            user_id="test_user",
            details={"success": True}
        )
        
        # Export to temporary file
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            export_path = f.name
        
        try:
            success = audit_system.export_audit_trail(
                export_path,
                format=ReportFormat.CSV,
                start_date=datetime.now() - timedelta(hours=1)
            )
            
            assert success is True
            assert os.path.exists(export_path)
            
            # Check file has content
            with open(export_path, 'r') as f:
                content = f.read()
                assert len(content) > 0
                assert 'event_id' in content
        finally:
            if os.path.exists(export_path):
                os.unlink(export_path)
    
    def test_get_system_statistics(self, audit_system):
        """Test getting system statistics"""
        # Log some events
        audit_system.log_audit_event(
            event_type=AuditEventType.USER_LOGIN,
            action="login",
            user_id="user_1"
        )
        
        audit_system.log_audit_event(
            event_type=AuditEventType.TRADE_EXECUTION,
            action="execute_trade",
            user_id="user_1"
        )
        
        # Get statistics
        stats = audit_system.get_system_statistics()
        
        assert isinstance(stats, dict)
        assert 'audit_trail' in stats
        assert 'compliance' in stats
        assert 'reporting' in stats
        assert 'system_health' in stats
        
        # Check audit trail stats
        assert stats['audit_trail']['events_24h'] >= 2
        
        # Check system health
        assert stats['system_health']['database_accessible'] is True


class TestIntegration:
    """Integration tests for audit and reporting system"""
    
    @pytest.mark.asyncio
    async def test_complete_audit_workflow(self):
        """Test complete audit and reporting workflow"""
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            # Initialize system
            audit_system = AuditReportingSystem(db_path=db_path)
            
            # Simulate user session
            session_id = "session_123"
            user_id = "trader_001"
            
            # 1. User login
            audit_system.log_audit_event(
                event_type=AuditEventType.USER_LOGIN,
                action="user_login",
                user_id=user_id,
                session_id=session_id,
                ip_address="192.168.1.100",
                details={"success": True, "method": "password"}
            )
            
            # 2. Multiple trades
            for i in range(5):
                audit_system.log_audit_event(
                    event_type=AuditEventType.TRADE_EXECUTION,
                    action="execute_trade",
                    user_id=user_id,
                    session_id=session_id,
                    details={
                        "symbol": f"STOCK{i}",
                        "quantity": 100 + i * 10,
                        "price": 50.0 + i,
                        "amount": (100 + i * 10) * (50.0 + i),
                        "side": "buy" if i % 2 == 0 else "sell"
                    }
                )
            
            # 3. Compliance violation
            audit_system.log_audit_event(
                event_type=AuditEventType.COMPLIANCE_VIOLATION,
                action="position_limit_exceeded",
                user_id=user_id,
                session_id=session_id,
                severity=AuditSeverity.WARNING,
                details={
                    "violation_type": "position_limit",
                    "symbol": "STOCK0",
                    "current_position": 12000,
                    "limit": 10000,
                    "resolved": False
                }
            )
            
            # 4. User logout
            audit_system.log_audit_event(
                event_type=AuditEventType.USER_LOGOUT,
                action="user_logout",
                user_id=user_id,
                session_id=session_id,
                details={"session_duration": 3600}
            )
            
            # Verify events were logged
            all_events = audit_system.search_audit_events(user_id=user_id)
            assert len(all_events) == 8  # 1 login + 5 trades + 1 violation + 1 logout
            
            # Generate compliance metrics
            start_date = datetime.now() - timedelta(hours=1)
            end_date = datetime.now()
            
            metrics = audit_system.get_compliance_metrics(start_date, end_date)
            assert len(metrics) > 0
            
            # Find violation metrics
            violation_metrics = [m for m in metrics if 'violation' in m.name.lower()]
            assert len(violation_metrics) > 0
            
            # Generate daily report
            daily_report = audit_system.generate_report(
                "daily_trading",
                start_date=start_date,
                end_date=end_date
            )
            
            assert daily_report is not None
            assert daily_report.status == "success"
            assert daily_report.record_count > 0
            
            # Verify report content
            with open(daily_report.file_path, 'r') as f:
                report_data = json.load(f)
                assert report_data['trading_summary']['total_trades'] == 5
                assert report_data['trading_summary']['unique_traders'] == 1
            
            # Generate monthly compliance report
            monthly_report = audit_system.generate_report(
                "monthly_compliance",
                start_date=start_date,
                end_date=end_date
            )
            
            assert monthly_report is not None
            assert monthly_report.status == "success"
            
            # Export audit trail
            with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
                export_path = f.name
            
            try:
                export_success = audit_system.export_audit_trail(
                    export_path,
                    format=ReportFormat.CSV,
                    start_date=start_date
                )
                
                assert export_success is True
                assert os.path.exists(export_path)
                
                # Verify export content
                with open(export_path, 'r') as f:
                    content = f.read()
                    assert user_id in content
                    assert session_id in content
                    
            finally:
                if os.path.exists(export_path):
                    os.unlink(export_path)
            
            # Get system statistics
            stats = audit_system.get_system_statistics()
            assert stats['audit_trail']['events_24h'] >= 8
            assert stats['system_health']['database_accessible'] is True
            
            print("Complete audit workflow test passed!")
            
        finally:
            # Cleanup
            if os.path.exists(db_path):
                os.unlink(db_path)


if __name__ == "__main__":
    pytest.main([__file__])