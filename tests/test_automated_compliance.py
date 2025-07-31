"""
Tests for Automated Compliance System
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from nautilus_trader_engine.compliance.automated_compliance import (
    AutomatedComplianceSystem,
    ComplianceRuleEngine,
    RealTimeTradeMonitor,
    RegulatoryReportGenerator,
    ComplianceDashboard,
    ComplianceRule,
    Trade,
    Position,
    ComplianceViolation,
    ComplianceRuleType,
    ComplianceStatus,
    AlertSeverity
)


class TestComplianceRuleEngine:
    """Test compliance rule engine"""
    
    @pytest.fixture
    def rule_engine(self):
        return ComplianceRuleEngine()
    
    @pytest.fixture
    def sample_rule(self):
        return ComplianceRule(
            rule_id="test_rule_001",
            name="Test Position Limit",
            rule_type=ComplianceRuleType.POSITION_LIMIT,
            description="Test rule for position limits",
            parameters={'max_position': 10000, 'symbol': 'AAPL'}
        )
    
    def test_add_rule(self, rule_engine, sample_rule):
        """Test adding compliance rule"""
        rule_engine.add_rule(sample_rule)
        
        assert sample_rule.rule_id in rule_engine.rules
        assert rule_engine.rules[sample_rule.rule_id] == sample_rule
    
    def test_remove_rule(self, rule_engine, sample_rule):
        """Test removing compliance rule"""
        rule_engine.add_rule(sample_rule)
        rule_engine.remove_rule(sample_rule.rule_id)
        
        assert sample_rule.rule_id not in rule_engine.rules
    
    def test_update_rule(self, rule_engine, sample_rule):
        """Test updating compliance rule"""
        rule_engine.add_rule(sample_rule)
        
        updates = {'name': 'Updated Test Rule', 'is_active': False}
        rule_engine.update_rule(sample_rule.rule_id, updates)
        
        updated_rule = rule_engine.rules[sample_rule.rule_id]
        assert updated_rule.name == 'Updated Test Rule'
        assert updated_rule.is_active is False
    
    def test_get_active_rules(self, rule_engine):
        """Test getting active rules"""
        # Add active rule
        active_rule = ComplianceRule(
            rule_id="active_rule",
            name="Active Rule",
            rule_type=ComplianceRuleType.POSITION_LIMIT,
            description="Active rule",
            parameters={},
            is_active=True
        )
        
        # Add inactive rule
        inactive_rule = ComplianceRule(
            rule_id="inactive_rule",
            name="Inactive Rule",
            rule_type=ComplianceRuleType.TRADING_LIMIT,
            description="Inactive rule",
            parameters={},
            is_active=False
        )
        
        rule_engine.add_rule(active_rule)
        rule_engine.add_rule(inactive_rule)
        
        active_rules = rule_engine.get_active_rules()
        assert len(active_rules) == 1
        assert active_rules[0].rule_id == "active_rule"
        
        # Test filtering by type
        position_rules = rule_engine.get_active_rules(ComplianceRuleType.POSITION_LIMIT)
        assert len(position_rules) == 1
        assert position_rules[0].rule_type == ComplianceRuleType.POSITION_LIMIT
    
    def test_check_position_limit_violation(self, rule_engine):
        """Test position limit violation"""
        # Add position limit rule
        rule = ComplianceRule(
            rule_id="pos_limit",
            name="Position Limit",
            rule_type=ComplianceRuleType.POSITION_LIMIT,
            description="Position limit rule",
            parameters={'max_position': 5000, 'symbol': 'AAPL'}
        )
        rule_engine.add_rule(rule)
        
        # Create trade that would exceed limit
        trade = Trade(
            trade_id="trade_001",
            symbol="AAPL",
            side="buy",
            quantity=Decimal('6000'),
            price=Decimal('150.00'),
            timestamp=datetime.now(),
            trader_id="trader_001",
            portfolio_id="portfolio_001",
            order_type="market",
            venue="NYSE"
        )
        
        # Current position
        positions = [
            Position(
                symbol="AAPL",
                quantity=Decimal('2000'),
                market_value=Decimal('300000'),
                portfolio_id="portfolio_001",
                trader_id="trader_001",
                timestamp=datetime.now()
            )
        ]
        
        violations = rule_engine.check_trade_compliance(trade, positions)
        
        assert len(violations) == 1
        assert violations[0].rule_id == "pos_limit"
        assert violations[0].status == ComplianceStatus.VIOLATION
        assert violations[0].severity == AlertSeverity.HIGH
    
    def test_check_concentration_limit_violation(self, rule_engine):
        """Test concentration limit violation"""
        # Add concentration limit rule
        rule = ComplianceRule(
            rule_id="conc_limit",
            name="Concentration Limit",
            rule_type=ComplianceRuleType.CONCENTRATION_LIMIT,
            description="Concentration limit rule",
            parameters={'max_concentration': 0.1}  # 10%
        )
        rule_engine.add_rule(rule)
        
        # Create large trade
        trade = Trade(
            trade_id="trade_001",
            symbol="AAPL",
            side="buy",
            quantity=Decimal('1000'),
            price=Decimal('200.00'),  # $200k trade
            timestamp=datetime.now(),
            trader_id="trader_001",
            portfolio_id="portfolio_001",
            order_type="market",
            venue="NYSE"
        )
        
        # Small portfolio (trade would be >10%)
        positions = [
            Position(
                symbol="GOOGL",
                quantity=Decimal('500'),
                market_value=Decimal('1000000'),  # $1M total portfolio
                portfolio_id="portfolio_001",
                trader_id="trader_001",
                timestamp=datetime.now()
            )
        ]
        
        violations = rule_engine.check_trade_compliance(trade, positions)
        
        assert len(violations) == 1
        assert violations[0].rule_id == "conc_limit"
        assert violations[0].status == ComplianceStatus.WARNING
    
    def test_check_trading_limit_violation(self, rule_engine):
        """Test trading limit violation"""
        # Add trading limit rule
        rule = ComplianceRule(
            rule_id="trade_limit",
            name="Trading Limit",
            rule_type=ComplianceRuleType.TRADING_LIMIT,
            description="Trading limit rule",
            parameters={'max_trade_size': 1000}
        )
        rule_engine.add_rule(rule)
        
        # Create large trade
        trade = Trade(
            trade_id="trade_001",
            symbol="AAPL",
            side="buy",
            quantity=Decimal('2000'),  # Exceeds limit
            price=Decimal('150.00'),
            timestamp=datetime.now(),
            trader_id="trader_001",
            portfolio_id="portfolio_001",
            order_type="market",
            venue="NYSE"
        )
        
        violations = rule_engine.check_trade_compliance(trade, [])
        
        assert len(violations) == 1
        assert violations[0].rule_id == "trade_limit"
        assert violations[0].status == ComplianceStatus.VIOLATION


class TestRealTimeTradeMonitor:
    """Test real-time trade monitor"""
    
    @pytest.fixture
    def rule_engine(self):
        engine = ComplianceRuleEngine()
        # Add a test rule
        rule = ComplianceRule(
            rule_id="test_rule",
            name="Test Rule",
            rule_type=ComplianceRuleType.POSITION_LIMIT,
            description="Test rule",
            parameters={'max_position': 5000}
        )
        engine.add_rule(rule)
        return engine
    
    @pytest.fixture
    def trade_monitor(self, rule_engine):
        return RealTimeTradeMonitor(rule_engine)
    
    @pytest.mark.asyncio
    async def test_monitor_trade(self, trade_monitor):
        """Test trade monitoring"""
        trade = Trade(
            trade_id="trade_001",
            symbol="AAPL",
            side="buy",
            quantity=Decimal('1000'),
            price=Decimal('150.00'),
            timestamp=datetime.now(),
            trader_id="trader_001",
            portfolio_id="portfolio_001",
            order_type="market",
            venue="NYSE"
        )
        
        violations = await trade_monitor.monitor_trade(trade)
        
        assert trade in trade_monitor.monitored_trades
        assert isinstance(violations, list)
    
    def test_update_positions(self, trade_monitor):
        """Test updating positions cache"""
        positions = [
            Position(
                symbol="AAPL",
                quantity=Decimal('1000'),
                market_value=Decimal('150000'),
                portfolio_id="portfolio_001",
                trader_id="trader_001",
                timestamp=datetime.now()
            )
        ]
        
        trade_monitor.update_positions("portfolio_001", positions)
        
        assert "portfolio_001" in trade_monitor.positions_cache
        assert trade_monitor.positions_cache["portfolio_001"] == positions


class TestRegulatoryReportGenerator:
    """Test regulatory report generator"""
    
    @pytest.fixture
    def rule_engine_with_violations(self):
        engine = ComplianceRuleEngine()
        
        # Add some test violations
        violation1 = ComplianceViolation(
            violation_id="v1",
            rule_id="rule1",
            rule_name="Test Rule 1",
            status=ComplianceStatus.VIOLATION,
            severity=AlertSeverity.HIGH,
            description="Test violation 1",
            trade_id="trade1",
            trader_id="trader1",
            portfolio_id="portfolio1",
            timestamp=datetime.now() - timedelta(hours=2)
        )
        
        violation2 = ComplianceViolation(
            violation_id="v2",
            rule_id="rule2",
            rule_name="Test Rule 2",
            status=ComplianceStatus.WARNING,
            severity=AlertSeverity.MEDIUM,
            description="Test violation 2",
            trade_id="trade2",
            trader_id="trader2",
            portfolio_id="portfolio2",
            timestamp=datetime.now() - timedelta(hours=1),
            resolved=True,
            resolved_at=datetime.now()
        )
        
        engine.violations = [violation1, violation2]
        return engine
    
    @pytest.fixture
    def report_generator(self, rule_engine_with_violations):
        return RegulatoryReportGenerator(rule_engine_with_violations)
    
    def test_generate_daily_report(self, report_generator):
        """Test daily report generation"""
        report_date = datetime.now()
        report = report_generator.generate_daily_report(report_date)
        
        assert report.report_type == "daily_compliance"
        assert report.period_start.date() == report_date.date()
        assert len(report.violations) == 2  # Both violations are from today
        assert report.summary['total_violations'] == 2
        assert report.summary['resolved_violations'] == 1
        assert report.summary['high_violations'] == 1
        assert report.summary['medium_violations'] == 1
    
    def test_generate_monthly_report(self, report_generator):
        """Test monthly report generation"""
        now = datetime.now()
        report = report_generator.generate_monthly_report(now.year, now.month)
        
        assert report.report_type == "monthly_compliance"
        assert report.period_start.month == now.month
        assert report.period_start.year == now.year
        assert len(report.violations) == 2
        assert 'violations_by_severity' in report.summary
        assert 'violations_by_type' in report.summary
        assert 'resolution_rate' in report.summary


class TestComplianceDashboard:
    """Test compliance dashboard"""
    
    @pytest.fixture
    def dashboard_setup(self):
        rule_engine = ComplianceRuleEngine()
        report_generator = RegulatoryReportGenerator(rule_engine)
        dashboard = ComplianceDashboard(rule_engine, report_generator)
        
        # Add test rule
        rule = ComplianceRule(
            rule_id="test_rule",
            name="Test Rule",
            rule_type=ComplianceRuleType.POSITION_LIMIT,
            description="Test rule",
            parameters={}
        )
        rule_engine.add_rule(rule)
        
        # Add test violation
        violation = ComplianceViolation(
            violation_id="test_violation",
            rule_id="test_rule",
            rule_name="Test Rule",
            status=ComplianceStatus.VIOLATION,
            severity=AlertSeverity.CRITICAL,
            description="Test violation",
            trade_id="trade1",
            trader_id="trader1",
            portfolio_id="portfolio1",
            timestamp=datetime.now()
        )
        rule_engine.violations.append(violation)
        
        return dashboard
    
    def test_get_dashboard_data(self, dashboard_setup):
        """Test getting dashboard data"""
        dashboard_data = dashboard_setup.get_dashboard_data()
        
        assert 'timestamp' in dashboard_data
        assert 'summary' in dashboard_data
        assert 'recent_violations' in dashboard_data
        assert 'unresolved_violations' in dashboard_data
        assert 'rule_status' in dashboard_data
        assert 'alerts' in dashboard_data
        
        # Check summary
        summary = dashboard_data['summary']
        assert summary['total_active_rules'] == 1
        assert summary['unresolved_violations'] == 1
        assert summary['critical_violations'] == 1
        
        # Check alerts
        alerts = dashboard_data['alerts']
        assert len(alerts) >= 1  # Should have critical violation alert
        assert any(alert['type'] == 'critical_violations' for alert in alerts)


class TestAutomatedComplianceSystem:
    """Test main automated compliance system"""
    
    @pytest.fixture
    def compliance_system(self):
        return AutomatedComplianceSystem()
    
    def test_initialization(self, compliance_system):
        """Test system initialization"""
        assert compliance_system.rule_engine is not None
        assert compliance_system.trade_monitor is not None
        assert compliance_system.report_generator is not None
        assert compliance_system.dashboard is not None
        
        # Check default rules are loaded
        active_rules = compliance_system.rule_engine.get_active_rules()
        assert len(active_rules) > 0
    
    @pytest.mark.asyncio
    async def test_process_trade(self, compliance_system):
        """Test trade processing"""
        trade = Trade(
            trade_id="trade_001",
            symbol="AAPL",
            side="buy",
            quantity=Decimal('1000'),
            price=Decimal('150.00'),
            timestamp=datetime.now(),
            trader_id="trader_001",
            portfolio_id="portfolio_001",
            order_type="market",
            venue="NYSE"
        )
        
        positions = [
            Position(
                symbol="AAPL",
                quantity=Decimal('500'),
                market_value=Decimal('75000'),
                portfolio_id="portfolio_001",
                trader_id="trader_001",
                timestamp=datetime.now()
            )
        ]
        
        violations = await compliance_system.process_trade(trade, positions)
        
        assert isinstance(violations, list)
        # May have concentration limit violations with default rules
        # This is expected behavior
    
    @pytest.mark.asyncio
    async def test_process_large_trade_violation(self, compliance_system):
        """Test processing trade that violates rules"""
        # Large trade that should violate default rules
        trade = Trade(
            trade_id="trade_002",
            symbol="AAPL",
            side="buy",
            quantity=Decimal('15000'),  # Exceeds default position limit
            price=Decimal('150.00'),
            timestamp=datetime.now(),
            trader_id="trader_001",
            portfolio_id="portfolio_001",
            order_type="market",
            venue="NYSE"
        )
        
        positions = []
        
        violations = await compliance_system.process_trade(trade, positions)
        
        assert len(violations) > 0
        # Should violate position limit and trade size limit
        violation_types = [v.rule_name for v in violations]
        assert any("Position" in vtype for vtype in violation_types)
    
    def test_resolve_violation(self, compliance_system):
        """Test resolving violations"""
        # Create a violation
        violation = ComplianceViolation(
            violation_id="test_violation",
            rule_id="test_rule",
            rule_name="Test Rule",
            status=ComplianceStatus.VIOLATION,
            severity=AlertSeverity.HIGH,
            description="Test violation",
            trade_id="trade1",
            trader_id="trader1",
            portfolio_id="portfolio1",
            timestamp=datetime.now()
        )
        
        compliance_system.rule_engine.violations.append(violation)
        
        # Resolve the violation
        success = compliance_system.resolve_violation("test_violation", "Resolved by test")
        
        assert success is True
        assert violation.resolved is True
        assert violation.resolved_at is not None
        assert violation.details['resolution_notes'] == "Resolved by test"
    
    def test_get_compliance_status(self, compliance_system):
        """Test getting compliance status"""
        status = compliance_system.get_compliance_status()
        
        assert 'overall_status' in status
        assert 'total_violations' in status
        assert 'unresolved_violations' in status
        assert 'critical_violations' in status
        assert 'active_rules' in status
        assert 'last_updated' in status
        
        # With no violations, should be compliant
        assert status['overall_status'] == 'compliant'
        assert status['total_violations'] == 0
        assert status['unresolved_violations'] == 0


class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.asyncio
    async def test_complete_compliance_workflow(self):
        """Test complete compliance workflow"""
        # Create compliance system
        compliance_system = AutomatedComplianceSystem()
        
        # Create a trade that will violate multiple rules
        large_trade = Trade(
            trade_id="large_trade_001",
            symbol="AAPL",
            side="buy",
            quantity=Decimal('20000'),  # Very large trade
            price=Decimal('150.00'),
            timestamp=datetime.now(),
            trader_id="trader_001",
            portfolio_id="portfolio_001",
            order_type="market",
            venue="NYSE"
        )
        
        # Small portfolio to trigger concentration limit
        positions = [
            Position(
                symbol="GOOGL",
                quantity=Decimal('100'),
                market_value=Decimal('200000'),  # Small portfolio
                portfolio_id="portfolio_001",
                trader_id="trader_001",
                timestamp=datetime.now()
            )
        ]
        
        # Process trade
        violations = await compliance_system.process_trade(large_trade, positions)
        
        # Should have multiple violations
        assert len(violations) > 0
        print(f"Found {len(violations)} violations:")
        for violation in violations:
            print(f"  - {violation.rule_name}: {violation.description}")
        
        # Check compliance status
        status = compliance_system.get_compliance_status()
        assert status['overall_status'] == 'violations_present'
        assert status['unresolved_violations'] > 0
        
        # Generate daily report
        daily_report = compliance_system.report_generator.generate_daily_report(datetime.now())
        assert daily_report.summary['total_violations'] > 0
        
        # Get dashboard data
        dashboard_data = compliance_system.dashboard.get_dashboard_data()
        assert dashboard_data['summary']['unresolved_violations'] > 0
        # Alerts may or may not be present depending on violation severity
        assert isinstance(dashboard_data['alerts'], list)
        
        # Resolve violations
        for violation in violations:
            success = compliance_system.resolve_violation(
                violation.violation_id, 
                "Resolved during integration test"
            )
            assert success is True
        
        # Check status after resolution
        final_status = compliance_system.get_compliance_status()
        assert final_status['unresolved_violations'] == 0
        
        print("Complete compliance workflow test passed!")


if __name__ == "__main__":
    pytest.main([__file__])