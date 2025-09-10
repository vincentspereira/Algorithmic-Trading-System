"""Unit tests for Risk Management system."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from nautilus_trader_engine.core.risk_management import RiskManager, RiskLevel


class TestRiskManagement:
    """Test suite for Risk Management system."""

    def setup_method(self):
        """Set up test fixtures."""
        self.sample_position = {
            'symbol': 'EURUSD',
            'quantity': 100000,
            'side': 'LONG',
            'entry_price': 1.0850,
            'current_price': 1.0860,
            'notional_value': 108600.0
        }

        self.sample_portfolio = {
            'portfolio_id': 'PORT_001',
            'total_value': 100000.0,
            'positions': [self.sample_position],
            'cash': 50000.0
        }

    @patch('nautilus_trader_engine.core.risk_management.RiskManager')
    def test_position_risk_assessment(self, mock_risk_manager):
        """Test position-level risk assessment."""
        # Mock risk manager
        mock_manager = Mock()
        mock_risk_manager.return_value = mock_manager
        mock_manager.assess_position_risk.return_value = {
            'risk_score': 0.35,
            'risk_level': RiskLevel.MEDIUM.value,
            'risk_factors': {
                'position_size': 0.25,
                'leverage': 0.15,
                'volatility': 0.30,
                'correlation': 0.20
            },
            'var_1d_95': 1250.0,
            'var_1d_99': 2000.0,
            'max_loss_potential': 5000.0,
            'recommendations': [
                'Consider reducing position size',
                'Monitor volatility closely'
            ]
        }

        # Test position risk assessment
        manager = RiskManager()
        result = manager.assess_position_risk(self.sample_position)

        assert result['risk_level'] == RiskLevel.MEDIUM.value
        assert result['risk_score'] == 0.35
        assert 'risk_factors' in result
        assert 'var_1d_95' in result
        assert len(result['recommendations']) > 0

    @patch('nautilus_trader_engine.core.risk_management.RiskManager')
    def test_portfolio_risk_assessment(self, mock_risk_manager):
        """Test portfolio-level risk assessment."""
        # Mock risk manager
        mock_manager = Mock()
        mock_risk_manager.return_value = mock_manager
        mock_manager.assess_portfolio_risk.return_value = {
            'overall_risk_score': 0.42,
            'risk_level': RiskLevel.MEDIUM.value,
            'diversification_score': 0.65,
            'concentration_risk': 0.30,
            'correlation_risk': 0.25,
            'var_portfolio_1d_95': 2800.0,
            'var_portfolio_1d_99': 4200.0,
            'expected_shortfall': 5500.0,
            'risk_by_asset_class': {
                'forex': 0.80,
                'equities': 0.15,
                'commodities': 0.05
            },
            'risk_decomposition': {
                'systematic_risk': 0.60,
                'idiosyncratic_risk': 0.40
            }
        }

        # Test portfolio risk assessment
        manager = RiskManager()
        result = manager.assess_portfolio_risk(self.sample_portfolio)

        assert result['risk_level'] == RiskLevel.MEDIUM.value
        assert result['overall_risk_score'] == 0.42
        assert result['diversification_score'] == 0.65
        assert 'var_portfolio_1d_95' in result
        assert 'risk_by_asset_class' in result

    @patch('nautilus_trader_engine.core.risk_management.RiskManager')
    def test_var_calculation(self, mock_risk_manager):
        """Test Value at Risk (VaR) calculation."""
        # Mock risk manager
        mock_manager = Mock()
        mock_risk_manager.return_value = mock_manager
        mock_manager.calculate_var.return_value = {
            'var_1d_95': 2500.0,
            'var_1d_99': 4000.0,
            'var_10d_95': 7900.0,
            'var_10d_99': 12650.0,
            'var_method': 'historical_simulation',
            'confidence_levels': [0.95, 0.99],
            'time_horizons': [1, 10],
            'calculation_date': datetime.now().date().isoformat(),
            'data_points_used': 252,
            'var_components': {
                'EURUSD': 1500.0,
                'GBPUSD': 1000.0
            }
        }

        # Test VaR calculation
        manager = RiskManager()
        result = manager.calculate_var(
            'PORT_001', confidence_level=0.95, time_horizon=1
        )

        assert result['var_1d_95'] == 2500.0
        assert result['var_method'] == 'historical_simulation'
        assert result['data_points_used'] == 252
        assert 'var_components' in result

    @patch('nautilus_trader_engine.core.risk_management.RiskManager')
    def test_stress_testing(self, mock_risk_manager):
        """Test stress testing functionality."""
        # Mock risk manager
        mock_manager = Mock()
        mock_risk_manager.return_value = mock_manager
        mock_manager.run_stress_test.return_value = {
            'stress_test_id': 'STRESS_001',
            'test_date': datetime.now().isoformat(),
            'scenarios': {
                '2008_financial_crisis': {
                    'portfolio_loss': -18500.0,
                    'percentage_loss': -18.5,
                    'worst_position': 'EURUSD',
                    'position_losses': {
                        'EURUSD': -12000.0,
                        'GBPUSD': -6500.0
                    }
                },
                'covid_market_crash': {
                    'portfolio_loss': -22000.0,
                    'percentage_loss': -22.0,
                    'worst_position': 'GBPUSD',
                    'position_losses': {
                        'EURUSD': -10000.0,
                        'GBPUSD': -12000.0
                    }
                },
                'interest_rate_shock': {
                    'portfolio_loss': -8500.0,
                    'percentage_loss': -8.5,
                    'worst_position': 'EURUSD',
                    'position_losses': {
                        'EURUSD': -5500.0,
                        'GBPUSD': -3000.0
                    }
                }
            },
            'worst_case_scenario': 'covid_market_crash',
            'stress_test_summary': {
                'max_loss': -22000.0,
                'average_loss': -16333.33,
                'scenarios_passed': 3,
                'scenarios_failed': 0
            }
        }

        # Test stress testing
        manager = RiskManager()
        scenarios = [
            '2008_financial_crisis',
            'covid_market_crash',
            'interest_rate_shock'
        ]
        result = manager.run_stress_test('PORT_001', scenarios)

        assert result['worst_case_scenario'] == 'covid_market_crash'
        assert len(result['scenarios']) == 3
        assert result['stress_test_summary']['max_loss'] == -22000.0
        assert result['stress_test_summary']['scenarios_passed'] == 3

    @patch('nautilus_trader_engine.core.risk_management.RiskManager')
    def test_risk_limits_monitoring(self, mock_risk_manager):
        """Test risk limits monitoring."""
        # Mock risk manager
        mock_manager = Mock()
        mock_risk_manager.return_value = mock_manager
        mock_manager.check_risk_limits.return_value = {
            'limits_status': 'within_limits',
            'limit_checks': {
                'position_limit': {
                    'current': 108600.0,
                    'limit': 200000.0,
                    'utilization': 0.543,
                    'status': 'ok'
                },
                'var_limit': {
                    'current': 2500.0,
                    'limit': 5000.0,
                    'utilization': 0.50,
                    'status': 'ok'
                },
                'concentration_limit': {
                    'current': 0.30,
                    'limit': 0.40,
                    'utilization': 0.75,
                    'status': 'warning'
                },
                'leverage_limit': {
                    'current': 2.17,
                    'limit': 5.0,
                    'utilization': 0.434,
                    'status': 'ok'
                }
            },
            'violations': [],
            'warnings': [
                'Concentration limit approaching threshold'
            ],
            'last_check': datetime.now().isoformat()
        }

        # Test risk limits monitoring
        manager = RiskManager()
        result = manager.check_risk_limits('PORT_001')

        assert result['limits_status'] == 'within_limits'
        assert len(result['violations']) == 0
        assert len(result['warnings']) == 1
        assert 'limit_checks' in result
        assert result['limit_checks']['concentration_limit']['status'] == \
            'warning'

    @patch('nautilus_trader_engine.core.risk_management.RiskManager')
    def test_correlation_analysis(self, mock_risk_manager):
        """Test correlation analysis functionality."""
        # Mock risk manager
        mock_manager = Mock()
        mock_risk_manager.return_value = mock_manager
        mock_manager.analyze_correlations.return_value = {
            'correlation_matrix': {
                'EURUSD': {'EURUSD': 1.0, 'GBPUSD': 0.75, 'USDJPY': -0.45},
                'GBPUSD': {'EURUSD': 0.75, 'GBPUSD': 1.0, 'USDJPY': -0.35},
                'USDJPY': {'EURUSD': -0.45, 'GBPUSD': -0.35, 'USDJPY': 1.0}
            },
            'high_correlations': [
                {'pair': ['EURUSD', 'GBPUSD'], 'correlation': 0.75}
            ],
            'diversification_ratio': 0.68,
            'effective_positions': 2.1,
            'concentration_risk': 0.32,
            'analysis_period': '2024-01-01 to 2024-06-01',
            'data_frequency': 'daily'
        }

        # Test correlation analysis
        manager = RiskManager()
        result = manager.analyze_correlations('PORT_001')

        assert result['diversification_ratio'] == 0.68
        assert result['effective_positions'] == 2.1
        assert len(result['high_correlations']) == 1
        assert 'correlation_matrix' in result

    @patch('nautilus_trader_engine.core.risk_management.RiskManager')
    def test_liquidity_risk_assessment(self, mock_risk_manager):
        """Test liquidity risk assessment."""
        # Mock risk manager
        mock_manager = Mock()
        mock_risk_manager.return_value = mock_manager
        mock_manager.assess_liquidity_risk.return_value = {
            'overall_liquidity_score': 0.75,
            'liquidity_level': 'good',
            'position_liquidity': {
                'EURUSD': {
                    'liquidity_score': 0.95,
                    'avg_daily_volume': 1500000000,
                    'bid_ask_spread': 0.0001,
                    'market_impact': 0.02,
                    'time_to_liquidate': '< 1 minute'
                },
                'GBPUSD': {
                    'liquidity_score': 0.85,
                    'avg_daily_volume': 800000000,
                    'bid_ask_spread': 0.0002,
                    'market_impact': 0.05,
                    'time_to_liquidate': '< 5 minutes'
                }
            },
            'liquidity_buffer': 0.20,
            'emergency_liquidation_time': '< 10 minutes',
            'liquidity_warnings': []
        }

        # Test liquidity risk assessment
        manager = RiskManager()
        result = manager.assess_liquidity_risk('PORT_001')

        assert result['liquidity_level'] == 'good'
        assert result['overall_liquidity_score'] == 0.75
        assert 'position_liquidity' in result
        assert len(result['liquidity_warnings']) == 0

    @patch('nautilus_trader_engine.core.risk_management.RiskManager')
    def test_risk_reporting(self, mock_risk_manager):
        """Test risk reporting functionality."""
        # Mock risk manager
        mock_manager = Mock()
        mock_risk_manager.return_value = mock_manager
        mock_manager.generate_risk_report.return_value = {
            'report_id': 'RISK_RPT_001',
            'report_date': datetime.now().date().isoformat(),
            'portfolio_id': 'PORT_001',
            'executive_summary': {
                'overall_risk_level': RiskLevel.MEDIUM.value,
                'key_risks': ['concentration_risk', 'correlation_risk'],
                'risk_score': 0.42,
                'recommendations': [
                    'Reduce EURUSD concentration',
                    'Add uncorrelated assets'
                ]
            },
            'detailed_metrics': {
                'var_95_1d': 2500.0,
                'expected_shortfall': 3800.0,
                'sharpe_ratio': 1.25,
                'max_drawdown': 0.08,
                'volatility': 0.15
            },
            'risk_decomposition': {
                'market_risk': 0.70,
                'credit_risk': 0.10,
                'operational_risk': 0.15,
                'liquidity_risk': 0.05
            },
            'compliance_status': {
                'all_limits_compliant': True,
                'violations': [],
                'warnings': 1
            }
        }

        # Test risk reporting
        manager = RiskManager()
        result = manager.generate_risk_report('PORT_001')

        assert result['executive_summary']['overall_risk_level'] == \
            RiskLevel.MEDIUM.value
        assert result['compliance_status']['all_limits_compliant'] is True
        assert 'detailed_metrics' in result
        assert 'risk_decomposition' in result

    @patch('nautilus_trader_engine.core.risk_management.RiskManager')
    def test_real_time_risk_monitoring(self, mock_risk_manager):
        """Test real-time risk monitoring."""
        # Mock risk manager
        mock_manager = Mock()
        mock_risk_manager.return_value = mock_manager
        mock_manager.monitor_real_time_risk.return_value = {
            'monitoring_status': 'active',
            'last_update': datetime.now().isoformat(),
            'current_risk_metrics': {
                'portfolio_var': 2650.0,
                'risk_score': 0.38,
                'leverage': 2.1,
                'concentration': 0.32
            },
            'alerts': [],
            'threshold_breaches': [],
            'risk_trend': 'stable',
            'next_assessment': (
                datetime.now() + timedelta(minutes=15)
            ).isoformat()
        }

        # Test real-time risk monitoring
        manager = RiskManager()
        result = manager.monitor_real_time_risk('PORT_001')

        assert result['monitoring_status'] == 'active'
        assert result['risk_trend'] == 'stable'
        assert len(result['alerts']) == 0
        assert len(result['threshold_breaches']) == 0
        assert 'current_risk_metrics' in result


if __name__ == '__main__':
    pytest.main([__file__])
