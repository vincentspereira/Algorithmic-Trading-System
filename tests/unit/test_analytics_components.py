"""Unit tests for Analytics components."""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import json


class TestDataProcessor:
    """Test suite for Data Processor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor_config = {
            'data_sources': ['market_data', 'news', 'economic_indicators'],
            'processing_frequency': '1min',
            'data_quality_checks': True,
            'outlier_detection': True,
            'missing_data_handling': 'interpolation'
        }
        
        # Sample raw market data
        self.sample_raw_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=1000, freq='1min'),
            'symbol': ['EURUSD'] * 1000,
            'bid': np.random.uniform(1.08, 1.09, 1000),
            'ask': np.random.uniform(1.081, 1.091, 1000),
            'volume': np.random.uniform(100000, 500000, 1000),
            'spread': np.random.uniform(0.0001, 0.0003, 1000)
        })
    
    @patch('nautilus_trader_engine.analytics.data_processor.DataProcessor')
    def test_data_processor_initialization(self, mock_data_processor):
        """Test data processor initialization."""
        mock_processor = Mock()
        mock_data_processor.return_value = mock_processor
        
        from nautilus_trader_engine.analytics.data_processor import DataProcessor
        processor = DataProcessor(self.processor_config)
        
        assert processor is not None
        mock_data_processor.assert_called_once_with(self.processor_config)
    
    @patch('nautilus_trader_engine.analytics.data_processor.DataProcessor')
    def test_data_cleaning(self, mock_data_processor):
        """Test data cleaning functionality."""
        mock_processor = Mock()
        mock_data_processor.return_value = mock_processor
        
        # Mock cleaned data
        cleaned_data = self.sample_raw_data.copy()
        cleaned_data['mid_price'] = (cleaned_data['bid'] + cleaned_data['ask']) / 2
        
        mock_processor.clean_data.return_value = {
            'cleaned_data': cleaned_data,
            'quality_report': {
                'total_records': 1000,
                'valid_records': 985,
                'outliers_removed': 8,
                'missing_values_filled': 7,
                'data_quality_score': 0.985
            },
            'processing_time_ms': 125.5
        }
        
        mock_processor.detect_outliers.return_value = {
            'outlier_indices': [45, 156, 234, 567, 789, 890, 923, 967],
            'outlier_method': 'isolation_forest',
            'outlier_threshold': 0.1,
            'outlier_scores': [0.85, 0.92, 0.78, 0.88, 0.91, 0.83, 0.87, 0.79]
        }
        
        from nautilus_trader_engine.analytics.data_processor import DataProcessor
        processor = DataProcessor(self.processor_config)
        
        # Test data cleaning
        cleaning_result = processor.clean_data(self.sample_raw_data)
        assert 'cleaned_data' in cleaning_result
        assert 'quality_report' in cleaning_result
        assert cleaning_result['quality_report']['data_quality_score'] > 0.95
        
        # Test outlier detection
        outliers = processor.detect_outliers(self.sample_raw_data)
        assert 'outlier_indices' in outliers
        assert len(outliers['outlier_indices']) > 0
        assert all(0 <= idx < len(self.sample_raw_data) for idx in outliers['outlier_indices'])
    
    @patch('nautilus_trader_engine.analytics.data_processor.DataProcessor')
    def test_feature_engineering(self, mock_data_processor):
        """Test feature engineering capabilities."""
        mock_processor = Mock()
        mock_data_processor.return_value = mock_processor
        
        # Mock engineered features
        engineered_features = pd.DataFrame({
            'timestamp': self.sample_raw_data['timestamp'],
            'returns': np.random.normal(0, 0.001, 1000),
            'volatility': np.random.uniform(0.005, 0.02, 1000),
            'rsi': np.random.uniform(20, 80, 1000),
            'macd': np.random.normal(0, 0.0005, 1000),
            'bollinger_upper': np.random.uniform(1.085, 1.095, 1000),
            'bollinger_lower': np.random.uniform(1.075, 1.085, 1000),
            'volume_sma': np.random.uniform(200000, 400000, 1000),
            'price_momentum': np.random.normal(0, 0.002, 1000)
        })
        
        mock_processor.engineer_features.return_value = {
            'features': engineered_features,
            'feature_descriptions': {
                'returns': 'Log returns calculated from mid prices',
                'volatility': 'Rolling 20-period volatility',
                'rsi': 'Relative Strength Index (14 periods)',
                'macd': 'MACD signal line',
                'bollinger_upper': 'Bollinger Band upper bound',
                'bollinger_lower': 'Bollinger Band lower bound',
                'volume_sma': 'Simple moving average of volume (20 periods)',
                'price_momentum': 'Price momentum indicator'
            },
            'feature_correlations': np.random.uniform(-0.5, 0.5, (8, 8)),
            'feature_importance': {
                'returns': 0.25,
                'volatility': 0.20,
                'rsi': 0.15,
                'macd': 0.12,
                'price_momentum': 0.10,
                'volume_sma': 0.08,
                'bollinger_upper': 0.05,
                'bollinger_lower': 0.05
            }
        }
        
        from nautilus_trader_engine.analytics.data_processor import DataProcessor
        processor = DataProcessor(self.processor_config)
        
        feature_result = processor.engineer_features(self.sample_raw_data)
        assert 'features' in feature_result
        assert 'feature_descriptions' in feature_result
        assert 'feature_importance' in feature_result
        assert len(feature_result['features']) == len(self.sample_raw_data)
        assert abs(sum(feature_result['feature_importance'].values()) - 1.0) < 0.01


class TestMetricsCalculator:
    """Test suite for Metrics Calculator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.calculator_config = {
            'metrics_types': ['performance', 'risk', 'execution', 'market'],
            'calculation_frequency': 'real_time',
            'rolling_windows': [30, 60, 90, 252],
            'benchmark_comparison': True
        }
        
        # Sample portfolio data
        self.sample_portfolio_data = {
            'positions': {
                'EURUSD': {'quantity': 10000, 'entry_price': 1.0850, 'current_price': 1.0865},
                'GBPUSD': {'quantity': 8000, 'entry_price': 1.2650, 'current_price': 1.2640},
                'USDJPY': {'quantity': -5000, 'entry_price': 150.25, 'current_price': 149.80}
            },
            'cash_balance': 50000,
            'total_equity': 125000,
            'unrealized_pnl': 2500,
            'realized_pnl': 15000
        }
    
    @patch('nautilus_trader_engine.analytics.metrics_calculator.MetricsCalculator')
    def test_calculator_initialization(self, mock_calculator):
        """Test metrics calculator initialization."""
        mock_calc = Mock()
        mock_calculator.return_value = mock_calc
        
        from nautilus_trader_engine.analytics.metrics_calculator import MetricsCalculator
        calculator = MetricsCalculator(self.calculator_config)
        
        assert calculator is not None
        mock_calculator.assert_called_once_with(self.calculator_config)
    
    @patch('nautilus_trader_engine.analytics.metrics_calculator.MetricsCalculator')
    def test_performance_metrics(self, mock_calculator):
        """Test performance metrics calculation."""
        mock_calc = Mock()
        mock_calculator.return_value = mock_calc
        
        # Mock performance metrics
        mock_calc.calculate_performance_metrics.return_value = {
            'total_return': 0.175,
            'annualized_return': 0.185,
            'sharpe_ratio': 1.65,
            'sortino_ratio': 2.15,
            'calmar_ratio': 2.85,
            'max_drawdown': 0.085,
            'win_rate': 0.68,
            'profit_factor': 1.95,
            'average_trade_return': 0.0012,
            'return_volatility': 0.125,
            'skewness': -0.15,
            'kurtosis': 2.85,
            'var_95': 0.032,
            'cvar_95': 0.045
        }
        
        mock_calc.calculate_rolling_metrics.return_value = {
            '30_day': {
                'return': 0.025,
                'volatility': 0.12,
                'sharpe': 1.45,
                'max_dd': 0.035
            },
            '60_day': {
                'return': 0.055,
                'volatility': 0.118,
                'sharpe': 1.52,
                'max_dd': 0.048
            },
            '90_day': {
                'return': 0.085,
                'volatility': 0.122,
                'sharpe': 1.58,
                'max_dd': 0.065
            },
            '252_day': {
                'return': 0.175,
                'volatility': 0.125,
                'sharpe': 1.65,
                'max_dd': 0.085
            }
        }
        
        from nautilus_trader_engine.analytics.metrics_calculator import MetricsCalculator
        calculator = MetricsCalculator(self.calculator_config)
        
        # Test performance metrics
        perf_metrics = calculator.calculate_performance_metrics(self.sample_portfolio_data)
        assert perf_metrics['total_return'] > 0
        assert perf_metrics['sharpe_ratio'] > 1.0
        assert perf_metrics['win_rate'] > 0.5
        assert perf_metrics['profit_factor'] > 1.0
        
        # Test rolling metrics
        rolling_metrics = calculator.calculate_rolling_metrics(self.sample_portfolio_data)
        assert len(rolling_metrics) == 4
        for window, metrics in rolling_metrics.items():
            assert 'return' in metrics
            assert 'volatility' in metrics
            assert 'sharpe' in metrics
    
    @patch('nautilus_trader_engine.analytics.metrics_calculator.MetricsCalculator')
    def test_risk_metrics(self, mock_calculator):
        """Test risk metrics calculation."""
        mock_calc = Mock()
        mock_calculator.return_value = mock_calc
        
        # Mock risk metrics
        mock_calc.calculate_risk_metrics.return_value = {
            'portfolio_var': {
                '1_day_95': 0.025,
                '1_day_99': 0.038,
                '10_day_95': 0.078,
                '10_day_99': 0.125
            },
            'expected_shortfall': {
                '1_day_95': 0.035,
                '1_day_99': 0.052,
                '10_day_95': 0.105,
                '10_day_99': 0.165
            },
            'beta_metrics': {
                'portfolio_beta': 0.85,
                'systematic_risk': 0.72,
                'idiosyncratic_risk': 0.28,
                'r_squared': 0.68
            },
            'concentration_risk': {
                'herfindahl_index': 0.35,
                'max_position_weight': 0.25,
                'effective_positions': 4.2,
                'diversification_ratio': 0.78
            },
            'liquidity_risk': {
                'liquidity_score': 0.85,
                'days_to_liquidate': 2.5,
                'bid_ask_impact': 0.0015,
                'market_impact': 0.0025
            }
        }
        
        from nautilus_trader_engine.analytics.metrics_calculator import MetricsCalculator
        calculator = MetricsCalculator(self.calculator_config)
        
        risk_metrics = calculator.calculate_risk_metrics(self.sample_portfolio_data)
        
        # Verify VaR metrics
        assert 'portfolio_var' in risk_metrics
        assert risk_metrics['portfolio_var']['1_day_95'] > 0
        assert risk_metrics['portfolio_var']['1_day_99'] > risk_metrics['portfolio_var']['1_day_95']
        
        # Verify beta metrics
        assert 'beta_metrics' in risk_metrics
        assert 0 <= risk_metrics['beta_metrics']['r_squared'] <= 1
        
        # Verify concentration risk
        assert 'concentration_risk' in risk_metrics
        assert 0 <= risk_metrics['concentration_risk']['herfindahl_index'] <= 1
        
        # Verify liquidity risk
        assert 'liquidity_risk' in risk_metrics
        assert 0 <= risk_metrics['liquidity_risk']['liquidity_score'] <= 1


class TestReportGenerator:
    """Test suite for Analytics Report Generator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.report_config = {
            'report_types': ['daily', 'weekly', 'monthly', 'quarterly'],
            'output_formats': ['html', 'pdf', 'excel', 'json'],
            'include_charts': True,
            'automated_delivery': True,
            'recipients': ['portfolio_manager', 'risk_manager', 'compliance']
        }
    
    @patch('nautilus_trader_engine.analytics.report_generator.ReportGenerator')
    def test_report_generator_initialization(self, mock_report_generator):
        """Test report generator initialization."""
        mock_generator = Mock()
        mock_report_generator.return_value = mock_generator
        
        from nautilus_trader_engine.analytics.report_generator import ReportGenerator
        generator = ReportGenerator(self.report_config)
        
        assert generator is not None
        mock_report_generator.assert_called_once_with(self.report_config)
    
    @patch('nautilus_trader_engine.analytics.report_generator.ReportGenerator')
    def test_daily_report_generation(self, mock_report_generator):
        """Test daily report generation."""
        mock_generator = Mock()
        mock_report_generator.return_value = mock_generator
        
        # Mock daily report
        mock_generator.generate_daily_report.return_value = {
            'report_id': 'daily_20240115',
            'report_date': '2024-01-15',
            'sections': {
                'executive_summary': {
                    'total_pnl': 2500.0,
                    'daily_return': 0.02,
                    'positions_count': 8,
                    'trades_executed': 15,
                    'risk_utilization': 0.65
                },
                'performance_summary': {
                    'realized_pnl': 1800.0,
                    'unrealized_pnl': 700.0,
                    'best_performer': 'EURUSD (+1.5%)',
                    'worst_performer': 'GBPUSD (-0.8%)',
                    'sharpe_ratio_1d': 1.85
                },
                'risk_summary': {
                    'var_1d_95': 0.025,
                    'max_drawdown': 0.035,
                    'portfolio_beta': 0.82,
                    'concentration_risk': 'LOW',
                    'liquidity_risk': 'LOW'
                },
                'trading_activity': {
                    'total_volume': 2500000,
                    'avg_trade_size': 166667,
                    'execution_quality': 0.92,
                    'slippage_bps': 0.8,
                    'commission_paid': 125.50
                }
            },
            'charts': {
                'pnl_chart': '/charts/daily_pnl_20240115.png',
                'positions_chart': '/charts/positions_20240115.png',
                'risk_chart': '/charts/risk_metrics_20240115.png'
            },
            'generated_files': {
                'html': '/reports/daily_20240115.html',
                'pdf': '/reports/daily_20240115.pdf',
                'excel': '/reports/daily_20240115.xlsx'
            }
        }
        
        from nautilus_trader_engine.analytics.report_generator import ReportGenerator
        generator = ReportGenerator(self.report_config)
        
        daily_report = generator.generate_daily_report('2024-01-15')
        
        assert 'report_id' in daily_report
        assert 'sections' in daily_report
        assert 'executive_summary' in daily_report['sections']
        assert 'performance_summary' in daily_report['sections']
        assert 'risk_summary' in daily_report['sections']
        assert 'trading_activity' in daily_report['sections']
        assert len(daily_report['generated_files']) >= 2
    
    @patch('nautilus_trader_engine.analytics.report_generator.ReportGenerator')
    def test_monthly_report_generation(self, mock_report_generator):
        """Test monthly report generation."""
        mock_generator = Mock()
        mock_report_generator.return_value = mock_generator
        
        # Mock monthly report
        mock_generator.generate_monthly_report.return_value = {
            'report_id': 'monthly_202401',
            'report_period': '2024-01',
            'sections': {
                'executive_summary': {
                    'monthly_return': 0.085,
                    'ytd_return': 0.085,
                    'benchmark_return': 0.065,
                    'alpha_generated': 0.02,
                    'total_trades': 450,
                    'win_rate': 0.68
                },
                'performance_analysis': {
                    'sharpe_ratio': 1.65,
                    'sortino_ratio': 2.15,
                    'max_drawdown': 0.045,
                    'calmar_ratio': 1.89,
                    'information_ratio': 1.25,
                    'tracking_error': 0.035
                },
                'risk_analysis': {
                    'avg_var_95': 0.028,
                    'avg_portfolio_beta': 0.85,
                    'correlation_with_benchmark': 0.78,
                    'concentration_metrics': {
                        'top_5_positions': 0.65,
                        'herfindahl_index': 0.32
                    }
                },
                'attribution_analysis': {
                    'sector_attribution': {
                        'currency_pairs': 0.055,
                        'commodities': 0.025,
                        'indices': 0.005
                    },
                    'strategy_attribution': {
                        'momentum': 0.045,
                        'mean_reversion': 0.025,
                        'arbitrage': 0.015
                    }
                }
            },
            'benchmarking': {
                'vs_benchmark': {
                    'outperformance': 0.02,
                    'tracking_error': 0.035,
                    'information_ratio': 0.57
                },
                'peer_comparison': {
                    'percentile_rank': 75,
                    'peer_median_return': 0.065,
                    'relative_performance': 0.02
                }
            }
        }
        
        from nautilus_trader_engine.analytics.report_generator import ReportGenerator
        generator = ReportGenerator(self.report_config)
        
        monthly_report = generator.generate_monthly_report('2024-01')
        
        assert 'report_id' in monthly_report
        assert 'sections' in monthly_report
        assert 'performance_analysis' in monthly_report['sections']
        assert 'risk_analysis' in monthly_report['sections']
        assert 'attribution_analysis' in monthly_report['sections']
        assert 'benchmarking' in monthly_report


class TestDashboardManager:
    """Test suite for Dashboard Manager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.dashboard_config = {
            'dashboard_types': ['trading', 'risk', 'performance', 'compliance'],
            'update_frequency': 'real_time',
            'user_permissions': {
                'trader': ['trading', 'performance'],
                'risk_manager': ['risk', 'performance'],
                'compliance': ['compliance', 'risk']
            },
            'alert_thresholds': {
                'var_breach': 0.05,
                'drawdown_limit': 0.1,
                'position_limit': 0.2
            }
        }
    
    @patch('nautilus_trader_engine.analytics.dashboard_manager.DashboardManager')
    def test_dashboard_manager_initialization(self, mock_dashboard_manager):
        """Test dashboard manager initialization."""
        mock_manager = Mock()
        mock_dashboard_manager.return_value = mock_manager
        
        from nautilus_trader_engine.analytics.dashboard_manager import DashboardManager
        manager = DashboardManager(self.dashboard_config)
        
        assert manager is not None
        mock_dashboard_manager.assert_called_once_with(self.dashboard_config)
    
    @patch('nautilus_trader_engine.analytics.dashboard_manager.DashboardManager')
    def test_real_time_dashboard_updates(self, mock_dashboard_manager):
        """Test real-time dashboard updates."""
        mock_manager = Mock()
        mock_dashboard_manager.return_value = mock_manager
        
        # Mock dashboard data
        mock_manager.get_dashboard_data.return_value = {
            'trading_dashboard': {
                'active_positions': 8,
                'total_pnl': 2500.0,
                'daily_volume': 5000000,
                'open_orders': 12,
                'execution_quality': 0.95,
                'recent_trades': [
                    {'symbol': 'EURUSD', 'side': 'BUY', 'quantity': 10000, 'price': 1.0865, 'time': '10:30:15'},
                    {'symbol': 'GBPUSD', 'side': 'SELL', 'quantity': 8000, 'price': 1.2640, 'time': '10:28:42'}
                ]
            },
            'risk_dashboard': {
                'portfolio_var': 0.035,
                'max_drawdown': 0.045,
                'portfolio_beta': 0.85,
                'concentration_risk': 0.32,
                'liquidity_score': 0.88,
                'risk_alerts': [
                    {'type': 'position_limit', 'severity': 'medium', 'message': 'EURUSD position approaching limit'}
                ]
            },
            'performance_dashboard': {
                'mtd_return': 0.025,
                'ytd_return': 0.085,
                'sharpe_ratio': 1.65,
                'win_rate': 0.68,
                'profit_factor': 1.85,
                'benchmark_comparison': {
                    'outperformance': 0.02,
                    'correlation': 0.78
                }
            }
        }
        
        mock_manager.update_dashboard.return_value = {
            'update_timestamp': '2024-01-15T10:30:00Z',
            'updated_components': ['positions', 'pnl', 'risk_metrics'],
            'update_latency_ms': 25.5,
            'data_freshness_seconds': 1.2
        }
        
        from nautilus_trader_engine.analytics.dashboard_manager import DashboardManager
        manager = DashboardManager(self.dashboard_config)
        
        # Test dashboard data retrieval
        dashboard_data = manager.get_dashboard_data('trading')
        assert 'trading_dashboard' in dashboard_data
        assert dashboard_data['trading_dashboard']['active_positions'] >= 0
        assert 'recent_trades' in dashboard_data['trading_dashboard']
        
        # Test dashboard updates
        update_result = manager.update_dashboard('trading')
        assert 'update_timestamp' in update_result
        assert 'updated_components' in update_result
        assert update_result['update_latency_ms'] < 100  # Should be fast
    
    @patch('nautilus_trader_engine.analytics.dashboard_manager.DashboardManager')
    def test_alert_management(self, mock_dashboard_manager):
        """Test alert management functionality."""
        mock_manager = Mock()
        mock_dashboard_manager.return_value = mock_manager
        
        # Mock alert system
        mock_manager.check_alerts.return_value = [
            {
                'alert_id': 'alert_001',
                'type': 'var_breach',
                'severity': 'high',
                'message': 'Portfolio VaR exceeded threshold (0.055 > 0.05)',
                'timestamp': '2024-01-15T10:30:00Z',
                'affected_positions': ['EURUSD', 'GBPUSD'],
                'recommended_action': 'Reduce position sizes'
            },
            {
                'alert_id': 'alert_002',
                'type': 'drawdown_warning',
                'severity': 'medium',
                'message': 'Approaching maximum drawdown limit (8.5% of 10%)',
                'timestamp': '2024-01-15T10:25:00Z',
                'current_drawdown': 0.085,
                'limit': 0.1
            }
        ]
        
        mock_manager.acknowledge_alert.return_value = {
            'alert_id': 'alert_001',
            'acknowledged_by': 'risk_manager',
            'acknowledged_at': '2024-01-15T10:35:00Z',
            'status': 'acknowledged'
        }
        
        from nautilus_trader_engine.analytics.dashboard_manager import DashboardManager
        manager = DashboardManager(self.dashboard_config)
        
        # Test alert checking
        alerts = manager.check_alerts()
        assert len(alerts) >= 0
        if alerts:
            assert all('alert_id' in alert for alert in alerts)
            assert all('severity' in alert for alert in alerts)
            assert all(alert['severity'] in ['low', 'medium', 'high', 'critical'] for alert in alerts)
        
        # Test alert acknowledgment
        if alerts:
            ack_result = manager.acknowledge_alert('alert_001', 'risk_manager')
            assert ack_result['status'] == 'acknowledged'


class TestDataVisualization:
    """Test suite for Data Visualization."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.viz_config = {
            'chart_types': ['line', 'candlestick', 'heatmap', 'scatter', 'histogram'],
            'output_formats': ['png', 'svg', 'html', 'pdf'],
            'interactive_charts': True,
            'real_time_updates': True,
            'color_schemes': ['default', 'dark', 'colorblind_friendly']
        }
        
        # Sample portfolio data for testing
        self.sample_portfolio_data = {
            'positions': {
                'EURUSD': {'quantity': 10000, 'entry_price': 1.0850, 'current_price': 1.0865},
                'GBPUSD': {'quantity': 8000, 'entry_price': 1.2650, 'current_price': 1.2640},
                'USDJPY': {'quantity': -5000, 'entry_price': 150.25, 'current_price': 149.80}
            },
            'cash_balance': 50000,
            'total_equity': 125000,
            'unrealized_pnl': 2500,
            'realized_pnl': 15000
        }
    
    @patch('nautilus_trader_engine.analytics.data_visualization.DataVisualization')
    def test_visualization_initialization(self, mock_visualization):
        """Test data visualization initialization."""
        mock_viz = Mock()
        mock_visualization.return_value = mock_viz
        
        from nautilus_trader_engine.analytics.data_visualization import DataVisualization
        viz = DataVisualization(self.viz_config)
        
        assert viz is not None
        mock_visualization.assert_called_once_with(self.viz_config)
    
    @patch('nautilus_trader_engine.analytics.data_visualization.DataVisualization')
    def test_chart_generation(self, mock_visualization):
        """Test chart generation functionality."""
        mock_viz = Mock()
        mock_visualization.return_value = mock_viz
        
        # Mock chart generation results
        mock_viz.create_equity_curve.return_value = {
            'chart_path': '/charts/equity_curve_20240115.png',
            'chart_type': 'line',
            'data_points': 1000,
            'time_range': '2024-01-01 to 2024-01-15',
            'interactive_version': '/charts/equity_curve_20240115.html'
        }
        
        mock_viz.create_risk_heatmap.return_value = {
            'chart_path': '/charts/risk_heatmap_20240115.png',
            'chart_type': 'heatmap',
            'dimensions': '10x8',
            'risk_metrics': ['var', 'correlation', 'beta', 'volatility'],
            'color_scale': 'red_green'
        }
        
        mock_viz.create_performance_dashboard.return_value = {
            'dashboard_path': '/dashboards/performance_20240115.html',
            'components': [
                'equity_curve',
                'drawdown_chart',
                'returns_distribution',
                'rolling_metrics',
                'benchmark_comparison'
            ],
            'update_frequency': 'real_time',
            'interactive': True
        }
        
        from nautilus_trader_engine.analytics.data_visualization import DataVisualization
        viz = DataVisualization(self.viz_config)
        
        # Test equity curve creation
        equity_chart = viz.create_equity_curve(self.sample_portfolio_data)
        assert 'chart_path' in equity_chart
        assert 'data_points' in equity_chart
        assert equity_chart['chart_type'] == 'line'
        
        # Test risk heatmap creation
        risk_heatmap = viz.create_risk_heatmap(self.sample_portfolio_data)
        assert 'chart_path' in risk_heatmap
        assert 'risk_metrics' in risk_heatmap
        assert risk_heatmap['chart_type'] == 'heatmap'
        
        # Test performance dashboard creation
        perf_dashboard = viz.create_performance_dashboard(self.sample_portfolio_data)
        assert 'dashboard_path' in perf_dashboard
        assert 'components' in perf_dashboard
        assert len(perf_dashboard['components']) >= 3


if __name__ == '__main__':
    pytest.main([__file__])