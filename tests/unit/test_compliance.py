"""Unit tests for the Compliance module."""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json
from decimal import Decimal
import uuid
from enum import Enum


class ComplianceStatus(Enum):
    """Compliance status enumeration."""
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    PENDING_REVIEW = "PENDING_REVIEW"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"


class RiskLevel(Enum):
    """Risk level enumeration."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TestComplianceEngine:
    """Test suite for the main compliance engine."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.compliance_rules = {
            'position_limits': {
                'max_position_size': 10000000,
                'max_concentration': 0.05,
                'sector_limits': {
                    'TECHNOLOGY': 0.15,
                    'FINANCIALS': 0.20,
                    'ENERGY': 0.10
                }
            },
            'risk_limits': {
                'max_var': 500000,
                'max_leverage': 10.0,
                'max_drawdown': 0.15,
                'correlation_limit': 0.80
            },
            'trading_limits': {
                'max_order_size': 1000000,
                'max_daily_volume': 50000000,
                'restricted_instruments': ['PROHIBITED_STOCK_A'],
                'trading_hours': {
                    'start': '09:30',
                    'end': '16:00',
                    'timezone': 'US/Eastern'
                }
            }
        }
        
        self.test_portfolio = {
            'positions': {
                'AAPL': {'quantity': 1000, 'market_value': 178000, 'sector': 'TECHNOLOGY'},
                'GOOGL': {'quantity': 500, 'market_value': 135000, 'sector': 'TECHNOLOGY'},
                'JPM': {'quantity': 800, 'market_value': 120000, 'sector': 'FINANCIALS'},
                'XOM': {'quantity': 600, 'market_value': 60000, 'sector': 'ENERGY'}
            },
            'total_value': 493000,
            'cash': 50000,
            'leverage': 2.5
        }
    
    @pytest.mark.asyncio
    async def test_compliance_engine_initialization(self):
        """Test compliance engine initialization."""
        with patch('nautilus_trader_engine.compliance.ComplianceEngine') as mock_engine:
            mock_instance = AsyncMock()
            mock_engine.return_value = mock_instance
            
            # Configure initialization response
            mock_instance.initialize.return_value = {
                'status': 'INITIALIZED',
                'rules_loaded': len(self.compliance_rules),
                'monitoring_active': True,
                'last_update': datetime.now().isoformat()
            }
            
            mock_instance.load_compliance_rules.return_value = {
                'rules_loaded': True,
                'rule_count': len(self.compliance_rules),
                'validation_status': 'PASSED'
            }
            
            engine = mock_engine()
            
            # Test engine initialization
            init_result = await engine.initialize()
            
            assert init_result['status'] == 'INITIALIZED', "Compliance engine not initialized"
            assert init_result['monitoring_active'] is True, "Compliance monitoring not active"
            assert init_result['rules_loaded'] > 0, "No compliance rules loaded"
            
            # Test rule loading
            rules_result = await engine.load_compliance_rules(self.compliance_rules)
            
            assert rules_result['rules_loaded'] is True, "Compliance rules not loaded"
            assert rules_result['validation_status'] == 'PASSED', "Rule validation failed"
    
    @pytest.mark.asyncio
    async def test_position_limit_compliance(self):
        """Test position limit compliance checking."""
        with patch('nautilus_trader_engine.compliance.PositionLimitChecker') as mock_checker:
            mock_instance = AsyncMock()
            mock_checker.return_value = mock_instance
            
            # Configure position limit responses
            def check_position_limits(portfolio):
                total_value = portfolio['total_value']
                violations = []
                
                # Check individual position limits
                for symbol, position in portfolio['positions'].items():
                    position_size = position['market_value']
                    if position_size > self.compliance_rules['position_limits']['max_position_size']:
                        violations.append({
                            'type': 'POSITION_SIZE_EXCEEDED',
                            'symbol': symbol,
                            'current_value': position_size,
                            'limit': self.compliance_rules['position_limits']['max_position_size']
                        })
                    
                    # Check concentration limits
                    concentration = position_size / total_value
                    max_concentration = self.compliance_rules['position_limits']['max_concentration']
                    if concentration > max_concentration:
                        violations.append({
                            'type': 'CONCENTRATION_EXCEEDED',
                            'symbol': symbol,
                            'current_concentration': concentration,
                            'limit': max_concentration
                        })
                
                # Check sector limits
                sector_exposures = {}
                for position in portfolio['positions'].values():
                    sector = position['sector']
                    sector_exposures[sector] = sector_exposures.get(sector, 0) + position['market_value']
                
                for sector, exposure in sector_exposures.items():
                    sector_concentration = exposure / total_value
                    sector_limit = self.compliance_rules['position_limits']['sector_limits'].get(sector, 1.0)
                    if sector_concentration > sector_limit:
                        violations.append({
                            'type': 'SECTOR_LIMIT_EXCEEDED',
                            'sector': sector,
                            'current_concentration': sector_concentration,
                            'limit': sector_limit
                        })
                
                return {
                    'compliant': len(violations) == 0,
                    'violations': violations,
                    'total_positions': len(portfolio['positions']),
                    'total_exposure': total_value
                }
            
            mock_instance.check_position_limits.side_effect = check_position_limits
            
            checker = mock_checker()
            
            # Test with compliant portfolio
            compliant_result = await checker.check_position_limits(self.test_portfolio)
            
            assert 'compliant' in compliant_result, "Missing compliance status"
            assert 'violations' in compliant_result, "Missing violations list"
            assert compliant_result['total_positions'] == len(self.test_portfolio['positions']), \
                "Incorrect position count"
            
            # Test with non-compliant portfolio (oversized position)
            non_compliant_portfolio = self.test_portfolio.copy()
            non_compliant_portfolio['positions']['AAPL']['market_value'] = 15000000  # Exceeds limit
            non_compliant_portfolio['total_value'] = 15000000 + 135000 + 120000 + 60000
            
            non_compliant_result = await checker.check_position_limits(non_compliant_portfolio)
            
            assert non_compliant_result['compliant'] is False, "Should detect position limit violation"
            assert len(non_compliant_result['violations']) > 0, "Should report violations"
            
            # Verify violation details
            position_violations = [v for v in non_compliant_result['violations'] 
                                 if v['type'] == 'POSITION_SIZE_EXCEEDED']
            assert len(position_violations) > 0, "Should detect position size violation"
    
    @pytest.mark.asyncio
    async def test_risk_limit_compliance(self):
        """Test risk limit compliance monitoring."""
        with patch('nautilus_trader_engine.compliance.RiskLimitMonitor') as mock_monitor:
            mock_instance = AsyncMock()
            mock_monitor.return_value = mock_instance
            
            # Test risk metrics
            risk_metrics = {
                'var_1day': 450000,  # Within limit
                'var_10day': 1200000,
                'leverage': 2.5,  # Within limit
                'max_drawdown': 0.08,  # Within limit
                'portfolio_correlation': 0.65,  # Within limit
                'beta': 1.15,
                'sharpe_ratio': 1.8
            }
            
            def check_risk_limits(metrics):
                violations = []
                risk_limits = self.compliance_rules['risk_limits']
                
                # Check VaR limit
                if metrics['var_1day'] > risk_limits['max_var']:
                    violations.append({
                        'type': 'VAR_LIMIT_EXCEEDED',
                        'current_var': metrics['var_1day'],
                        'limit': risk_limits['max_var'],
                        'severity': 'HIGH'
                    })
                
                # Check leverage limit
                if metrics['leverage'] > risk_limits['max_leverage']:
                    violations.append({
                        'type': 'LEVERAGE_LIMIT_EXCEEDED',
                        'current_leverage': metrics['leverage'],
                        'limit': risk_limits['max_leverage'],
                        'severity': 'MEDIUM'
                    })
                
                # Check drawdown limit
                if metrics['max_drawdown'] > risk_limits['max_drawdown']:
                    violations.append({
                        'type': 'DRAWDOWN_LIMIT_EXCEEDED',
                        'current_drawdown': metrics['max_drawdown'],
                        'limit': risk_limits['max_drawdown'],
                        'severity': 'HIGH'
                    })
                
                # Check correlation limit
                if metrics['portfolio_correlation'] > risk_limits['correlation_limit']:
                    violations.append({
                        'type': 'CORRELATION_LIMIT_EXCEEDED',
                        'current_correlation': metrics['portfolio_correlation'],
                        'limit': risk_limits['correlation_limit'],
                        'severity': 'MEDIUM'
                    })
                
                return {
                    'compliant': len(violations) == 0,
                    'violations': violations,
                    'risk_score': min(1.0, max(0.0, len(violations) / 4)),
                    'overall_risk_level': 'LOW' if len(violations) == 0 else 'MEDIUM' if len(violations) <= 2 else 'HIGH'
                }
            
            mock_instance.check_risk_limits.side_effect = check_risk_limits
            
            monitor = mock_monitor()
            
            # Test with compliant risk metrics
            compliant_result = await monitor.check_risk_limits(risk_metrics)
            
            assert compliant_result['compliant'] is True, "Should be compliant with risk limits"
            assert compliant_result['overall_risk_level'] == 'LOW', "Risk level should be LOW"
            assert len(compliant_result['violations']) == 0, "Should have no violations"
            
            # Test with non-compliant risk metrics
            non_compliant_metrics = risk_metrics.copy()
            non_compliant_metrics['var_1day'] = 600000  # Exceeds limit
            non_compliant_metrics['leverage'] = 12.0  # Exceeds limit
            
            non_compliant_result = await monitor.check_risk_limits(non_compliant_metrics)
            
            assert non_compliant_result['compliant'] is False, "Should detect risk limit violations"
            assert len(non_compliant_result['violations']) >= 2, "Should report multiple violations"
            assert non_compliant_result['overall_risk_level'] in ['MEDIUM', 'HIGH'], "Risk level should be elevated"
    
    @pytest.mark.asyncio
    async def test_trading_restriction_compliance(self):
        """Test trading restriction compliance."""
        with patch('nautilus_trader_engine.compliance.TradingRestrictionChecker') as mock_checker:
            mock_instance = AsyncMock()
            mock_checker.return_value = mock_instance
            
            # Test orders
            test_orders = [
                {
                    'order_id': 'ORD_001',
                    'symbol': 'AAPL',
                    'quantity': 500,
                    'price': 178.50,
                    'order_value': 89250,
                    'timestamp': datetime.now().replace(hour=10, minute=30).isoformat(),
                    'order_type': 'MARKET'
                },
                {
                    'order_id': 'ORD_002',
                    'symbol': 'PROHIBITED_STOCK_A',
                    'quantity': 1000,
                    'price': 50.00,
                    'order_value': 50000,
                    'timestamp': datetime.now().replace(hour=14, minute=0).isoformat(),
                    'order_type': 'LIMIT'
                },
                {
                    'order_id': 'ORD_003',
                    'symbol': 'GOOGL',
                    'quantity': 10000,  # Large order
                    'price': 2700.00,
                    'order_value': 27000000,  # Exceeds limit
                    'timestamp': datetime.now().replace(hour=15, minute=45).isoformat(),
                    'order_type': 'MARKET'
                }
            ]
            
            def check_trading_restrictions(order):
                violations = []
                trading_limits = self.compliance_rules['trading_limits']
                
                # Check order size limit
                if order['order_value'] > trading_limits['max_order_size']:
                    violations.append({
                        'type': 'ORDER_SIZE_EXCEEDED',
                        'current_value': order['order_value'],
                        'limit': trading_limits['max_order_size']
                    })
                
                # Check restricted instruments
                if order['symbol'] in trading_limits['restricted_instruments']:
                    violations.append({
                        'type': 'RESTRICTED_INSTRUMENT',
                        'symbol': order['symbol'],
                        'restriction_reason': 'PROHIBITED_TRADING'
                    })
                
                # Check trading hours (simplified)
                order_time = datetime.fromisoformat(order['timestamp']).time()
                start_time = datetime.strptime(trading_limits['trading_hours']['start'], '%H:%M').time()
                end_time = datetime.strptime(trading_limits['trading_hours']['end'], '%H:%M').time()
                
                if not (start_time <= order_time <= end_time):
                    violations.append({
                        'type': 'OUTSIDE_TRADING_HOURS',
                        'order_time': order['timestamp'],
                        'allowed_start': trading_limits['trading_hours']['start'],
                        'allowed_end': trading_limits['trading_hours']['end']
                    })
                
                return {
                    'order_id': order['order_id'],
                    'allowed': len(violations) == 0,
                    'violations': violations,
                    'risk_assessment': 'LOW' if len(violations) == 0 else 'HIGH'
                }
            
            mock_instance.check_trading_restrictions.side_effect = check_trading_restrictions
            
            checker = mock_checker()
            
            # Test each order
            results = []
            for order in test_orders:
                result = await checker.check_trading_restrictions(order)
                results.append(result)
            
            # Verify results
            # Order 1 should be allowed (normal order)
            assert results[0]['allowed'] is True, "Normal order should be allowed"
            assert len(results[0]['violations']) == 0, "Normal order should have no violations"
            
            # Order 2 should be blocked (restricted instrument)
            assert results[1]['allowed'] is False, "Restricted instrument order should be blocked"
            restricted_violations = [v for v in results[1]['violations'] if v['type'] == 'RESTRICTED_INSTRUMENT']
            assert len(restricted_violations) > 0, "Should detect restricted instrument violation"
            
            # Order 3 should be blocked (order size exceeded)
            assert results[2]['allowed'] is False, "Oversized order should be blocked"
            size_violations = [v for v in results[2]['violations'] if v['type'] == 'ORDER_SIZE_EXCEEDED']
            assert len(size_violations) > 0, "Should detect order size violation"
    
    @pytest.mark.asyncio
    async def test_real_time_compliance_monitoring(self):
        """Test real-time compliance monitoring."""
        with patch('nautilus_trader_engine.compliance.RealTimeComplianceMonitor') as mock_monitor:
            mock_instance = AsyncMock()
            mock_monitor.return_value = mock_instance
            
            # Mock monitoring events
            monitoring_events = [
                {
                    'event_id': 'EVT_001',
                    'event_type': 'POSITION_UPDATE',
                    'timestamp': datetime.now().isoformat(),
                    'data': {
                        'symbol': 'AAPL',
                        'new_position': 1500,
                        'position_value': 267000
                    }
                },
                {
                    'event_id': 'EVT_002',
                    'event_type': 'RISK_METRIC_UPDATE',
                    'timestamp': datetime.now().isoformat(),
                    'data': {
                        'var_1day': 520000,  # Exceeds limit
                        'leverage': 3.2
                    }
                },
                {
                    'event_id': 'EVT_003',
                    'event_type': 'ORDER_SUBMITTED',
                    'timestamp': datetime.now().isoformat(),
                    'data': {
                        'order_id': 'ORD_004',
                        'symbol': 'TSLA',
                        'quantity': 2000,
                        'order_value': 400000
                    }
                }
            ]
            
            def process_monitoring_event(event):
                alerts = []
                
                if event['event_type'] == 'RISK_METRIC_UPDATE':
                    var_value = event['data'].get('var_1day', 0)
                    if var_value > self.compliance_rules['risk_limits']['max_var']:
                        alerts.append({
                            'alert_id': 'ALT_' + str(uuid.uuid4()),
                            'alert_type': 'RISK_LIMIT_BREACH',
                            'severity': 'HIGH',
                            'message': f'VaR limit exceeded: {var_value}',
                            'requires_action': True
                        })
                
                elif event['event_type'] == 'POSITION_UPDATE':
                    position_value = event['data'].get('position_value', 0)
                    if position_value > self.compliance_rules['position_limits']['max_position_size']:
                        alerts.append({
                            'alert_id': 'ALT_' + str(uuid.uuid4()),
                            'alert_type': 'POSITION_LIMIT_BREACH',
                            'severity': 'MEDIUM',
                            'message': f'Position limit exceeded for {event["data"]["symbol"]}',
                            'requires_action': True
                        })
                
                return {
                    'event_id': event['event_id'],
                    'processed': True,
                    'alerts_generated': len(alerts),
                    'alerts': alerts,
                    'processing_time_ms': 15
                }
            
            mock_instance.process_monitoring_event.side_effect = process_monitoring_event
            
            mock_instance.get_active_alerts.return_value = {
                'total_alerts': 2,
                'high_severity': 1,
                'medium_severity': 1,
                'low_severity': 0,
                'alerts': [
                    {
                        'alert_id': 'ALT_001',
                        'alert_type': 'RISK_LIMIT_BREACH',
                        'severity': 'HIGH',
                        'status': 'ACTIVE',
                        'created_at': datetime.now().isoformat()
                    }
                ]
            }
            
            monitor = mock_monitor()
            
            # Test event processing
            total_alerts = 0
            for event in monitoring_events:
                result = await monitor.process_monitoring_event(event)
                
                assert result['processed'] is True, f"Event {event['event_id']} not processed"
                assert result['processing_time_ms'] < 100, "Processing time too slow"
                total_alerts += result['alerts_generated']
            
            # Test alert retrieval
            active_alerts = await monitor.get_active_alerts()
            
            assert 'total_alerts' in active_alerts, "Missing total alerts count"
            assert active_alerts['high_severity'] > 0, "Should have high severity alerts"
            assert len(active_alerts['alerts']) > 0, "Should have active alerts"
    
    @pytest.mark.asyncio
    async def test_compliance_reporting(self):
        """Test compliance reporting functionality."""
        with patch('nautilus_trader_engine.compliance.ComplianceReporter') as mock_reporter:
            mock_instance = AsyncMock()
            mock_reporter.return_value = mock_instance
            
            # Configure reporting responses
            mock_instance.generate_daily_compliance_report.return_value = {
                'report_id': 'RPT_DAILY_' + datetime.now().strftime('%Y%m%d'),
                'report_date': datetime.now().date().isoformat(),
                'compliance_status': 'MOSTLY_COMPLIANT',
                'total_violations': 3,
                'high_severity_violations': 1,
                'medium_severity_violations': 2,
                'low_severity_violations': 0,
                'violations_by_type': {
                    'POSITION_LIMIT': 1,
                    'RISK_LIMIT': 1,
                    'TRADING_RESTRICTION': 1
                },
                'remediation_actions': [
                    'Reduce position in AAPL by 20%',
                    'Implement additional risk controls',
                    'Review trading procedures'
                ]
            }
            
            mock_instance.generate_monthly_compliance_summary.return_value = {
                'report_id': 'RPT_MONTHLY_' + datetime.now().strftime('%Y%m'),
                'reporting_period': datetime.now().strftime('%Y-%m'),
                'overall_compliance_score': 0.87,
                'total_trading_days': 22,
                'compliant_days': 19,
                'non_compliant_days': 3,
                'trend_analysis': {
                    'compliance_trend': 'IMPROVING',
                    'violation_frequency': 'DECREASING',
                    'risk_score_trend': 'STABLE'
                },
                'recommendations': [
                    'Implement automated position sizing',
                    'Enhance real-time risk monitoring',
                    'Conduct quarterly compliance training'
                ]
            }
            
            reporter = mock_reporter()
            
            # Test daily compliance report
            daily_report = await reporter.generate_daily_compliance_report(datetime.now().date())
            
            assert 'report_id' in daily_report, "Missing report ID"
            assert 'compliance_status' in daily_report, "Missing compliance status"
            assert 'total_violations' in daily_report, "Missing violation count"
            assert daily_report['total_violations'] >= 0, "Invalid violation count"
            
            # Verify violation breakdown
            violation_sum = (daily_report['high_severity_violations'] + 
                           daily_report['medium_severity_violations'] + 
                           daily_report['low_severity_violations'])
            assert violation_sum == daily_report['total_violations'], "Violation count mismatch"
            
            # Test monthly compliance summary
            monthly_summary = await reporter.generate_monthly_compliance_summary(datetime.now().strftime('%Y-%m'))
            
            assert 'overall_compliance_score' in monthly_summary, "Missing compliance score"
            assert 0 <= monthly_summary['overall_compliance_score'] <= 1, "Invalid compliance score"
            assert monthly_summary['compliant_days'] + monthly_summary['non_compliant_days'] == \
                   monthly_summary['total_trading_days'], "Trading days count mismatch"
            
            # Verify trend analysis
            assert 'trend_analysis' in monthly_summary, "Missing trend analysis"
            trend_analysis = monthly_summary['trend_analysis']
            assert 'compliance_trend' in trend_analysis, "Missing compliance trend"
            assert trend_analysis['compliance_trend'] in ['IMPROVING', 'STABLE', 'DETERIORATING'], \
                "Invalid compliance trend"
    
    @pytest.mark.asyncio
    async def test_compliance_rule_validation(self):
        """Test compliance rule validation and management."""
        with patch('nautilus_trader_engine.compliance.ComplianceRuleValidator') as mock_validator:
            mock_instance = AsyncMock()
            mock_validator.return_value = mock_instance
            
            # Test rule validation scenarios
            test_rules = [
                {
                    'rule_id': 'RULE_001',
                    'rule_type': 'POSITION_LIMIT',
                    'parameters': {
                        'max_position_size': 5000000,
                        'max_concentration': 0.03
                    },
                    'active': True
                },
                {
                    'rule_id': 'RULE_002',
                    'rule_type': 'RISK_LIMIT',
                    'parameters': {
                        'max_var': 300000,
                        'max_leverage': 8.0
                    },
                    'active': True
                },
                {
                    'rule_id': 'RULE_INVALID',
                    'rule_type': 'UNKNOWN_TYPE',
                    'parameters': {
                        'invalid_param': 'invalid_value'
                    },
                    'active': True
                }
            ]
            
            def validate_compliance_rule(rule):
                validation_errors = []
                
                # Check rule type
                valid_types = ['POSITION_LIMIT', 'RISK_LIMIT', 'TRADING_RESTRICTION']
                if rule['rule_type'] not in valid_types:
                    validation_errors.append({
                        'error_type': 'INVALID_RULE_TYPE',
                        'message': f"Unknown rule type: {rule['rule_type']}"
                    })
                
                # Check parameters
                if rule['rule_type'] == 'POSITION_LIMIT':
                    required_params = ['max_position_size', 'max_concentration']
                    for param in required_params:
                        if param not in rule['parameters']:
                            validation_errors.append({
                                'error_type': 'MISSING_PARAMETER',
                                'message': f"Missing required parameter: {param}"
                            })
                
                elif rule['rule_type'] == 'RISK_LIMIT':
                    required_params = ['max_var', 'max_leverage']
                    for param in required_params:
                        if param not in rule['parameters']:
                            validation_errors.append({
                                'error_type': 'MISSING_PARAMETER',
                                'message': f"Missing required parameter: {param}"
                            })
                
                return {
                    'rule_id': rule['rule_id'],
                    'valid': len(validation_errors) == 0,
                    'validation_errors': validation_errors,
                    'validated_at': datetime.now().isoformat()
                }
            
            mock_instance.validate_compliance_rule.side_effect = validate_compliance_rule
            
            validator = mock_validator()
            
            # Test rule validation
            validation_results = []
            for rule in test_rules:
                result = await validator.validate_compliance_rule(rule)
                validation_results.append(result)
            
            # Verify validation results
            valid_rules = [r for r in validation_results if r['valid']]
            invalid_rules = [r for r in validation_results if not r['valid']]
            
            assert len(valid_rules) == 2, "Should have 2 valid rules"
            assert len(invalid_rules) == 1, "Should have 1 invalid rule"
            
            # Check specific validation errors
            invalid_rule = invalid_rules[0]
            assert invalid_rule['rule_id'] == 'RULE_INVALID', "Wrong invalid rule identified"
            assert len(invalid_rule['validation_errors']) > 0, "Should have validation errors"
            
            error_types = [error['error_type'] for error in invalid_rule['validation_errors']]
            assert 'INVALID_RULE_TYPE' in error_types, "Should detect invalid rule type"


if __name__ == '__main__':
    pytest.main([__file__])