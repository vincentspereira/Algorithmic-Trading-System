"""
Test suite for Real-Time Compliance Engine
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from nautilus_trader_engine.trading.compliance_engine import (
    ComplianceEngine,
    ComplianceRule,
    ComplianceCheck,
    ComplianceResult,
    ComplianceViolation,
    Position,
    RuleType,
    RuleSeverity,
    ComplianceAction
)
from nautilus_trader_engine.core.messaging.message_bus import MessageBus
from nautilus_trader_engine.core.caching.cache_manager import CacheManager


class TestComplianceEngine:
    """Test cases for ComplianceEngine"""
    
    @pytest.fixture
    async def compliance_engine(self):
        """Create compliance engine for testing"""
        message_bus = Mock(spec=MessageBus)
        message_bus.publish = AsyncMock()
        
        cache_manager = Mock(spec=CacheManager)
        cache_manager.get = AsyncMock(return_value=None)
        cache_manager.set = AsyncMock()
        
        engine = ComplianceEngine(
            message_bus=message_bus,
            cache_manager=cache_manager,
            max_concurrent_checks=5,
            enable_real_time_monitoring=False  # Disable for testing
        )
        
        await engine.start()
        yield engine
        await engine.stop()
    
    @pytest.mark.asyncio
    async def test_position_limit_compliance(self, compliance_engine):
        """Test position limit compliance checking"""
        # Add position limit rule
        rule = ComplianceRule(
            rule_id="test_position_limit",
            rule_name="Test Position Limit",
            rule_type=RuleType.POSITION_LIMIT,
            severity=RuleSeverity.ERROR,
            action=ComplianceAction.BLOCK,
            parameters={
                'max_long_position': 1000.0,
                'max_short_position': 1000.0
            }
        )
        
        await compliance_engine.add_rule(rule)
        
        # Test order within limits
        checks = await compliance_engine.check_pre_trade_compliance(
            order_id="test_order_1",
            symbol="AAPL",
            side="buy",
            quantity=500.0,
            price=150.0,
            account_id="test_account"
        )
        
        assert len(checks) > 0
        position_check = next((c for c in checks if c.rule_id == "test_position_limit"), None)
        assert position_check is not None
        assert position_check.result == ComplianceResult.APPROVED
        
        # Add position
        position = Position(
            account_id="test_account",
            symbol="AAPL",
            quantity=800.0,
            avg_price=150.0,
            market_value=120000.0,
            unrealized_pnl=0.0
        )
        
        await compliance_engine.update_position("test_account", "AAPL", position)
        
        # Test order that would exceed limits
        checks = await compliance_engine.check_pre_trade_compliance(
            order_id="test_order_2",
            symbol="AAPL",
            side="buy",
            quantity=500.0,
            price=150.0,
            account_id="test_account"
        )
        
        position_check = next((c for c in checks if c.rule_id == "test_position_limit"), None)
        assert position_check is not None
        assert position_check.result == ComplianceResult.REJECTED
        assert "Position limit exceeded" in position_check.violation_message
    
    @pytest.mark.asyncio
    async def test_concentration_limit_compliance(self, compliance_engine):
        """Test concentration limit compliance checking"""
        # Add concentration limit rule
        rule = ComplianceRule(
            rule_id="test_concentration_limit",
            rule_name="Test Concentration Limit",
            rule_type=RuleType.CONCENTRATION_LIMIT,
            severity=RuleSeverity.WARNING,
            action=ComplianceAction.WARN,
            parameters={
                'max_concentration_percent': 5.0,
                'portfolio_value': 1000000.0
            }
        )
        
        await compliance_engine.add_rule(rule)
        
        # Test order within concentration limits
        checks = await compliance_engine.check_pre_trade_compliance(
            order_id="test_order_1",
            symbol="AAPL",
            side="buy",
            quantity=200.0,
            price=150.0,
            account_id="test_account"
        )
        
        concentration_check = next((c for c in checks if c.rule_id == "test_concentration_limit"), None)
        assert concentration_check is not None
        assert concentration_check.result == ComplianceResult.APPROVED
        
        # Test order that would exceed concentration limits
        checks = await compliance_engine.check_pre_trade_compliance(
            order_id="test_order_2",
            symbol="AAPL",
            side="buy",
            quantity=500.0,
            price=150.0,
            account_id="test_account"
        )
        
        concentration_check = next((c for c in checks if c.rule_id == "test_concentration_limit"), None)
        assert concentration_check is not None
        assert concentration_check.result in [ComplianceResult.WARNING, ComplianceResult.REJECTED]
    
    @pytest.mark.asyncio
    async def test_risk_limit_compliance(self, compliance_engine):
        """Test risk limit compliance checking"""
        # Add risk limit rule
        rule = ComplianceRule(
            rule_id="test_risk_limit",
            rule_name="Test Risk Limit",
            rule_type=RuleType.RISK_LIMIT,
            severity=RuleSeverity.ERROR,
            action=ComplianceAction.BLOCK,
            parameters={
                'max_var_1d': 10000.0,
                'max_var_10d': 30000.0,
                'max_beta_exposure': 100000.0
            }
        )
        
        await compliance_engine.add_rule(rule)
        
        # Update market data with high volatility
        await compliance_engine.update_market_data("AAPL", {
            'price': 150.0,
            'volatility': 0.05,  # 5% volatility
            'beta': 1.2
        })
        
        # Test order within risk limits
        checks = await compliance_engine.check_pre_trade_compliance(
            order_id="test_order_1",
            symbol="AAPL",
            side="buy",
            quantity=100.0,
            price=150.0,
            account_id="test_account"
        )
        
        risk_check = next((c for c in checks if c.rule_id == "test_risk_limit"), None)
        assert risk_check is not None
        assert risk_check.result == ComplianceResult.APPROVED
        
        # Test order that would exceed risk limits
        checks = await compliance_engine.check_pre_trade_compliance(
            order_id="test_order_2",
            symbol="AAPL",
            side="buy",
            quantity=2000.0,
            price=150.0,
            account_id="test_account"
        )
        
        risk_check = next((c for c in checks if c.rule_id == "test_risk_limit"), None)
        assert risk_check is not None
        assert risk_check.result in [ComplianceResult.WARNING, ComplianceResult.REJECTED]
    
    @pytest.mark.asyncio
    async def test_trading_limit_compliance(self, compliance_engine):
        """Test trading limit compliance checking"""
        # Add trading limit rule
        rule = ComplianceRule(
            rule_id="test_trading_limit",
            rule_name="Test Trading Limit",
            rule_type=RuleType.TRADING_LIMIT,
            severity=RuleSeverity.WARNING,
            action=ComplianceAction.WARN,
            parameters={
                'max_order_size': 1000.0,
                'max_daily_volume': 10000.0,
                'max_daily_trades': 50,
                'current_daily_volume': 5000.0,
                'current_daily_trades': 25
            }
        )
        
        await compliance_engine.add_rule(rule)
        
        # Test order within trading limits
        checks = await compliance_engine.check_pre_trade_compliance(
            order_id="test_order_1",
            symbol="AAPL",
            side="buy",
            quantity=500.0,
            price=150.0,
            account_id="test_account"
        )
        
        trading_check = next((c for c in checks if c.rule_id == "test_trading_limit"), None)
        assert trading_check is not None
        assert trading_check.result == ComplianceResult.APPROVED
        
        # Test order that would exceed order size limit
        checks = await compliance_engine.check_pre_trade_compliance(
            order_id="test_order_2",
            symbol="AAPL",
            side="buy",
            quantity=1500.0,
            price=150.0,
            account_id="test_account"
        )
        
        trading_check = next((c for c in checks if c.rule_id == "test_trading_limit"), None)
        assert trading_check is not None
        assert trading_check.result == ComplianceResult.REJECTED
        assert "Order size limit exceeded" in trading_check.violation_message
    
    @pytest.mark.asyncio
    async def test_regulatory_compliance(self, compliance_engine):
        """Test regulatory compliance checking"""
        # Add regulatory rule
        rule = ComplianceRule(
            rule_id="test_regulatory",
            rule_name="Test Regulatory Rule",
            rule_type=RuleType.REGULATORY,
            severity=RuleSeverity.ERROR,
            action=ComplianceAction.BLOCK,
            parameters={
                'regulation_type': 'pattern_day_trader',
                'account_equity': 30000.0,
                'day_trades_count': 2
            }
        )
        
        await compliance_engine.add_rule(rule)
        
        # Test compliant order
        checks = await compliance_engine.check_pre_trade_compliance(
            order_id="test_order_1",
            symbol="AAPL",
            side="buy",
            quantity=100.0,
            price=150.0,
            account_id="test_account"
        )
        
        regulatory_check = next((c for c in checks if c.rule_id == "test_regulatory"), None)
        assert regulatory_check is not None
        assert regulatory_check.result == ComplianceResult.APPROVED
        
        # Update rule to violate PDT rule
        await compliance_engine.update_rule("test_regulatory", {
            'parameters': {
                'regulation_type': 'pattern_day_trader',
                'account_equity': 20000.0,  # Below $25k
                'day_trades_count': 3  # At limit
            }
        })
        
        # Test order that would violate PDT rule
        checks = await compliance_engine.check_pre_trade_compliance(
            order_id="test_order_2",
            symbol="AAPL",
            side="buy",
            quantity=100.0,
            price=150.0,
            account_id="test_account"
        )
        
        regulatory_check = next((c for c in checks if c.rule_id == "test_regulatory"), None)
        assert regulatory_check is not None
        assert regulatory_check.result == ComplianceResult.REJECTED
        assert "Pattern Day Trader rule violation" in regulatory_check.violation_message
    
    @pytest.mark.asyncio
    async def test_custom_rule_compliance(self, compliance_engine):
        """Test custom rule compliance checking"""
        # Define custom rule logic
        async def custom_rule_logic(order_id, symbol, side, quantity, price, 
                                  account_id, strategy_id, position, market_data, parameters):
            # Custom logic: reject orders for symbols starting with 'X'
            if symbol.startswith('X'):
                return ComplianceCheck(
                    check_id="custom_check",
                    order_id=order_id,
                    rule_id="test_custom",
                    result=ComplianceResult.REJECTED,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    account_id=account_id,
                    violation_message="Custom rule: Symbol not allowed"
                )
            return True
        
        # Add custom rule
        rule = ComplianceRule(
            rule_id="test_custom",
            rule_name="Test Custom Rule",
            rule_type=RuleType.CUSTOM,
            severity=RuleSeverity.WARNING,
            action=ComplianceAction.BLOCK,
            rule_logic=custom_rule_logic
        )
        
        await compliance_engine.add_rule(rule)
        
        # Test allowed symbol
        checks = await compliance_engine.check_pre_trade_compliance(
            order_id="test_order_1",
            symbol="AAPL",
            side="buy",
            quantity=100.0,
            price=150.0,
            account_id="test_account"
        )
        
        custom_check = next((c for c in checks if c.rule_id == "test_custom"), None)
        assert custom_check is not None
        assert custom_check.result == ComplianceResult.APPROVED
        
        # Test blocked symbol
        checks = await compliance_engine.check_pre_trade_compliance(
            order_id="test_order_2",
            symbol="XABC",
            side="buy",
            quantity=100.0,
            price=150.0,
            account_id="test_account"
        )
        
        custom_check = next((c for c in checks if c.rule_id == "test_custom"), None)
        assert custom_check is not None
        assert custom_check.result == ComplianceResult.REJECTED
        assert "Custom rule: Symbol not allowed" in custom_check.violation_message
    
    @pytest.mark.asyncio
    async def test_rule_management(self, compliance_engine):
        """Test rule management operations"""
        # Test adding rule
        rule = ComplianceRule(
            rule_id="test_rule",
            rule_name="Test Rule",
            rule_type=RuleType.POSITION_LIMIT,
            severity=RuleSeverity.ERROR,
            action=ComplianceAction.BLOCK,
            parameters={'max_position': 1000.0}
        )
        
        await compliance_engine.add_rule(rule)
        assert "test_rule" in compliance_engine._rules
        
        # Test updating rule
        await compliance_engine.update_rule("test_rule", {
            'parameters': {'max_position': 2000.0}
        })
        
        updated_rule = compliance_engine._rules["test_rule"]
        assert updated_rule.parameters['max_position'] == 2000.0
        
        # Test removing rule
        await compliance_engine.remove_rule("test_rule")
        assert "test_rule" not in compliance_engine._rules
    
    @pytest.mark.asyncio
    async def test_violation_management(self, compliance_engine):
        """Test violation management"""
        # Add a rule that will be violated
        rule = ComplianceRule(
            rule_id="test_violation_rule",
            rule_name="Test Violation Rule",
            rule_type=RuleType.POSITION_LIMIT,
            severity=RuleSeverity.ERROR,
            action=ComplianceAction.BLOCK,
            parameters={'max_long_position': 100.0}
        )
        
        await compliance_engine.add_rule(rule)
        
        # Create order that violates rule
        checks = await compliance_engine.check_pre_trade_compliance(
            order_id="violation_order",
            symbol="AAPL",
            side="buy",
            quantity=200.0,
            price=150.0,
            account_id="test_account"
        )
        
        # Check that violation was created
        violations = compliance_engine.get_violations(resolved=False)
        assert len(violations) > 0
        
        violation = violations[0]
        assert violation.order_id == "violation_order"
        assert not violation.resolved
        
        # Resolve violation
        await compliance_engine.resolve_violation(
            violation.violation_id,
            "Resolved by test"
        )
        
        # Check that violation is resolved
        resolved_violations = compliance_engine.get_violations(resolved=True)
        assert len(resolved_violations) > 0
        assert resolved_violations[0].resolved
        assert resolved_violations[0].resolution_notes == "Resolved by test"
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, compliance_engine):
        """Test performance metrics tracking"""
        # Add a simple rule
        rule = ComplianceRule(
            rule_id="perf_test_rule",
            rule_name="Performance Test Rule",
            rule_type=RuleType.POSITION_LIMIT,
            severity=RuleSeverity.ERROR,
            action=ComplianceAction.BLOCK,
            parameters={'max_long_position': 1000.0}
        )
        
        await compliance_engine.add_rule(rule)
        
        # Perform multiple compliance checks
        for i in range(10):
            await compliance_engine.check_pre_trade_compliance(
                order_id=f"perf_order_{i}",
                symbol="AAPL",
                side="buy",
                quantity=100.0,
                price=150.0,
                account_id="test_account"
            )
        
        # Check metrics
        metrics = compliance_engine.get_metrics()
        assert metrics['total_checks'] >= 10
        assert metrics['approved_checks'] >= 10
        assert metrics['avg_check_time_ms'] > 0
        assert metrics['rules_active'] >= 1
    
    @pytest.mark.asyncio
    async def test_audit_trail(self, compliance_engine):
        """Test audit trail functionality"""
        # Add a rule
        rule = ComplianceRule(
            rule_id="audit_test_rule",
            rule_name="Audit Test Rule",
            rule_type=RuleType.POSITION_LIMIT,
            severity=RuleSeverity.ERROR,
            action=ComplianceAction.BLOCK,
            parameters={'max_long_position': 1000.0}
        )
        
        await compliance_engine.add_rule(rule)
        
        # Perform compliance check
        await compliance_engine.check_pre_trade_compliance(
            order_id="audit_order",
            symbol="AAPL",
            side="buy",
            quantity=100.0,
            price=150.0,
            account_id="test_account"
        )
        
        # Check audit trail
        audit_trail = compliance_engine.get_audit_trail()
        assert len(audit_trail) > 0
        
        # Should have rule_added and compliance_check entries
        rule_added_entries = [e for e in audit_trail if e['type'] == 'rule_added']
        compliance_check_entries = [e for e in audit_trail if e['type'] == 'compliance_check']
        
        assert len(rule_added_entries) > 0
        assert len(compliance_check_entries) > 0
        
        # Check entry structure
        check_entry = compliance_check_entries[0]
        assert 'id' in check_entry
        assert 'timestamp' in check_entry
        assert check_entry['order_id'] == "audit_order"
        assert check_entry['symbol'] == "AAPL"
    
    @pytest.mark.asyncio
    async def test_real_time_monitoring(self):
        """Test real-time monitoring capabilities"""
        # Create engine with real-time monitoring enabled
        message_bus = Mock(spec=MessageBus)
        message_bus.publish = AsyncMock()
        
        cache_manager = Mock(spec=CacheManager)
        cache_manager.get = AsyncMock(return_value=None)
        cache_manager.set = AsyncMock()
        
        engine = ComplianceEngine(
            message_bus=message_bus,
            cache_manager=cache_manager,
            enable_real_time_monitoring=True
        )
        
        await engine.start()
        
        try:
            # Add position limit rule
            rule = ComplianceRule(
                rule_id="rt_position_limit",
                rule_name="Real-time Position Limit",
                rule_type=RuleType.POSITION_LIMIT,
                severity=RuleSeverity.ERROR,
                action=ComplianceAction.BLOCK,
                parameters={'max_position': 500.0}
            )
            
            await engine.add_rule(rule)
            
            # Add position that exceeds limit
            position = Position(
                account_id="rt_account",
                symbol="AAPL",
                quantity=1000.0,  # Exceeds limit
                avg_price=150.0,
                market_value=150000.0,
                unrealized_pnl=0.0
            )
            
            await engine.update_position("rt_account", "AAPL", position)
            
            # Wait for monitoring to detect violation
            await asyncio.sleep(2)
            
            # Check that violation was detected
            violations = engine.get_violations(resolved=False)
            position_violations = [v for v in violations if v.order_id == "position_monitor"]
            assert len(position_violations) > 0
            
        finally:
            await engine.stop()
    
    @pytest.mark.asyncio
    async def test_concurrent_compliance_checks(self, compliance_engine):
        """Test concurrent compliance checking performance"""
        # Add multiple rules
        rules = [
            ComplianceRule(
                rule_id=f"concurrent_rule_{i}",
                rule_name=f"Concurrent Rule {i}",
                rule_type=RuleType.POSITION_LIMIT,
                severity=RuleSeverity.ERROR,
                action=ComplianceAction.BLOCK,
                parameters={'max_long_position': 1000.0}
            )
            for i in range(5)
        ]
        
        for rule in rules:
            await compliance_engine.add_rule(rule)
        
        # Perform concurrent compliance checks
        tasks = []
        for i in range(20):
            task = compliance_engine.check_pre_trade_compliance(
                order_id=f"concurrent_order_{i}",
                symbol="AAPL",
                side="buy",
                quantity=100.0,
                price=150.0,
                account_id="test_account"
            )
            tasks.append(task)
        
        # Wait for all checks to complete
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Verify all checks completed
        assert len(results) == 20
        for checks in results:
            assert len(checks) >= 5  # At least one check per rule
        
        # Check performance
        total_time = end_time - start_time
        assert total_time < 5.0  # Should complete within 5 seconds
        
        # Check metrics
        metrics = compliance_engine.get_metrics()
        assert metrics['total_checks'] >= 100  # 20 orders * 5 rules each


if __name__ == "__main__":
    pytest.main([__file__])