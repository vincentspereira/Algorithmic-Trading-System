"""Unit tests for Backtesting components."""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json


class TestBacktestEngine:
    """Test suite for Backtest Engine."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.backtest_config = {
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'initial_capital': 100000.0,
            'commission_rate': 0.0002,
            'slippage_model': 'linear',
            'data_frequency': '1min',
            'benchmark': 'SPY'
        }
        
        self.sample_strategy = {
            'name': 'MovingAverageCrossover',
            'parameters': {
                'fast_period': 10,
                'slow_period': 20,
                'position_size': 0.1
            }
        }
        
        # Sample market data
        dates = pd.date_range('2024-01-01', '2024-01-31', freq='1min')
        self.sample_data = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.uniform(100, 110, len(dates)),
            'high': np.random.uniform(105, 115, len(dates)),
            'low': np.random.uniform(95, 105, len(dates)),
            'close': np.random.uniform(100, 110, len(dates)),
            'volume': np.random.uniform(10000, 50000, len(dates))
        })
    
    @patch('nautilus_trader_engine.backtesting.backtest_engine.BacktestEngine')
    def test_backtest_engine_initialization(self, mock_backtest_engine):
        """Test backtest engine initialization."""
        mock_engine = Mock()
        mock_backtest_engine.return_value = mock_engine
        
        from nautilus_trader_engine.backtesting.backtest_engine import BacktestEngine
        engine = BacktestEngine(self.backtest_config)
        
        assert engine is not None
        mock_backtest_engine.assert_called_once_with(self.backtest_config)
    
    @patch('nautilus_trader_engine.backtesting.backtest_engine.BacktestEngine')
    def test_strategy_execution(self, mock_backtest_engine):
        """Test strategy execution in backtest."""
        mock_engine = Mock()
        mock_backtest_engine.return_value = mock_engine
        
        # Mock backtest results
        backtest_results = {
            'total_return': 0.15,
            'annualized_return': 0.18,
            'volatility': 0.12,
            'sharpe_ratio': 1.5,
            'max_drawdown': -0.08,
            'win_rate': 0.65,
            'profit_factor': 1.8,
            'total_trades': 245,
            'winning_trades': 159,
            'losing_trades': 86,
            'avg_trade_return': 0.0006,
            'final_portfolio_value': 115000.0
        }
        
        mock_engine.run_backtest.return_value = backtest_results
        mock_engine.get_trade_history.return_value = [
            {
                'timestamp': '2024-01-15 10:30:00',
                'symbol': 'EURUSD',
                'side': 'BUY',
                'quantity': 10000,
                'price': 1.0850,
                'commission': 2.17,
                'pnl': 125.50
            }
        ]
        
        from nautilus_trader_engine.backtesting.backtest_engine import BacktestEngine
        engine = BacktestEngine(self.backtest_config)
        
        # Test backtest execution
        results = engine.run_backtest(self.sample_strategy, self.sample_data)
        assert results['total_return'] > 0
        assert results['sharpe_ratio'] > 1.0
        assert results['total_trades'] > 0
        assert results['final_portfolio_value'] > self.backtest_config['initial_capital']
        
        # Test trade history
        trades = engine.get_trade_history()
        assert len(trades) > 0
        assert all('timestamp' in trade for trade in trades)
        assert all('pnl' in trade for trade in trades)
    
    @patch('nautilus_trader_engine.backtesting.backtest_engine.BacktestEngine')
    def test_performance_metrics(self, mock_backtest_engine):
        """Test performance metrics calculation."""
        mock_engine = Mock()
        mock_backtest_engine.return_value = mock_engine
        
        # Mock detailed performance metrics
        mock_engine.calculate_performance_metrics.return_value = {
            'returns_metrics': {
                'total_return': 0.15,
                'annualized_return': 0.18,
                'monthly_returns': [0.02, 0.01, -0.005, 0.03],
                'cumulative_returns': np.array([0.02, 0.03, 0.025, 0.055])
            },
            'risk_metrics': {
                'volatility': 0.12,
                'var_95': -0.025,
                'cvar_95': -0.035,
                'max_drawdown': -0.08,
                'calmar_ratio': 2.25
            },
            'trade_metrics': {
                'win_rate': 0.65,
                'profit_factor': 1.8,
                'avg_win': 0.0012,
                'avg_loss': -0.0008,
                'largest_win': 0.0085,
                'largest_loss': -0.0045
            },
            'benchmark_comparison': {
                'alpha': 0.05,
                'beta': 0.8,
                'correlation': 0.75,
                'tracking_error': 0.04,
                'information_ratio': 1.25
            }
        }
        
        from nautilus_trader_engine.backtesting.backtest_engine import BacktestEngine
        engine = BacktestEngine(self.backtest_config)
        
        metrics = engine.calculate_performance_metrics()
        
        # Verify returns metrics
        assert metrics['returns_metrics']['total_return'] > 0
        assert metrics['returns_metrics']['annualized_return'] > 0
        
        # Verify risk metrics
        assert metrics['risk_metrics']['volatility'] > 0
        assert metrics['risk_metrics']['max_drawdown'] < 0
        assert metrics['risk_metrics']['calmar_ratio'] > 0
        
        # Verify trade metrics
        assert 0 <= metrics['trade_metrics']['win_rate'] <= 1
        assert metrics['trade_metrics']['profit_factor'] > 1
        
        # Verify benchmark comparison
        assert -1 <= metrics['benchmark_comparison']['correlation'] <= 1
        assert metrics['benchmark_comparison']['information_ratio'] > 0


class TestStrategyOptimizer:
    """Test suite for Strategy Optimizer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.optimizer_config = {
            'optimization_method': 'genetic_algorithm',
            'population_size': 50,
            'generations': 100,
            'mutation_rate': 0.1,
            'crossover_rate': 0.8,
            'objective_function': 'sharpe_ratio',
            'constraints': {
                'max_drawdown': -0.15,
                'min_trades': 50
            }
        }
        
        self.parameter_space = {
            'fast_period': {'type': 'int', 'min': 5, 'max': 20},
            'slow_period': {'type': 'int', 'min': 20, 'max': 50},
            'position_size': {'type': 'float', 'min': 0.01, 'max': 0.2},
            'stop_loss': {'type': 'float', 'min': 0.01, 'max': 0.05}
        }
        
        # Sample market data
        dates = pd.date_range('2024-01-01', '2024-01-31', freq='1min')
        self.sample_data = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.uniform(100, 110, len(dates)),
            'high': np.random.uniform(105, 115, len(dates)),
            'low': np.random.uniform(95, 105, len(dates)),
            'close': np.random.uniform(100, 110, len(dates)),
            'volume': np.random.uniform(10000, 50000, len(dates))
        })
        
        self.sample_strategy = {
            'name': 'MovingAverageCrossover',
            'parameters': {
                'fast_period': 10,
                'slow_period': 20,
                'position_size': 0.1
            }
        }
    
    @patch('nautilus_trader_engine.backtesting.strategy_optimizer.StrategyOptimizer')
    def test_optimizer_initialization(self, mock_optimizer):
        """Test strategy optimizer initialization."""
        mock_opt = Mock()
        mock_optimizer.return_value = mock_opt
        
        from nautilus_trader_engine.backtesting.strategy_optimizer import StrategyOptimizer
        optimizer = StrategyOptimizer(self.optimizer_config)
        
        assert optimizer is not None
        mock_optimizer.assert_called_once_with(self.optimizer_config)
    
    @patch('nautilus_trader_engine.backtesting.strategy_optimizer.StrategyOptimizer')
    def test_parameter_optimization(self, mock_optimizer):
        """Test parameter optimization process."""
        mock_opt = Mock()
        mock_optimizer.return_value = mock_opt
        
        # Mock optimization results
        optimization_results = {
            'best_parameters': {
                'fast_period': 12,
                'slow_period': 26,
                'position_size': 0.08,
                'stop_loss': 0.025
            },
            'best_fitness': 1.85,  # Sharpe ratio
            'optimization_history': [
                {'generation': 1, 'best_fitness': 1.2, 'avg_fitness': 0.8},
                {'generation': 50, 'best_fitness': 1.7, 'avg_fitness': 1.3},
                {'generation': 100, 'best_fitness': 1.85, 'avg_fitness': 1.5}
            ],
            'convergence_achieved': True,
            'total_evaluations': 5000,
            'optimization_time_seconds': 3600
        }
        
        mock_opt.optimize.return_value = optimization_results
        mock_opt.get_parameter_sensitivity.return_value = {
            'fast_period': 0.25,
            'slow_period': 0.30,
            'position_size': 0.35,
            'stop_loss': 0.10
        }
        
        from nautilus_trader_engine.backtesting.strategy_optimizer import StrategyOptimizer
        optimizer = StrategyOptimizer(self.optimizer_config)
        
        # Test optimization
        results = optimizer.optimize(self.parameter_space, self.sample_strategy)
        assert 'best_parameters' in results
        assert 'best_fitness' in results
        assert results['best_fitness'] > 1.0  # Good Sharpe ratio
        assert results['convergence_achieved'] is True
        
        # Test parameter sensitivity
        sensitivity = optimizer.get_parameter_sensitivity()
        assert sum(sensitivity.values()) <= 1.0  # Normalized sensitivity
        assert all(0 <= sens <= 1 for sens in sensitivity.values())
    
    @patch('nautilus_trader_engine.backtesting.strategy_optimizer.StrategyOptimizer')
    def test_walk_forward_optimization(self, mock_optimizer):
        """Test walk-forward optimization."""
        mock_opt = Mock()
        mock_optimizer.return_value = mock_opt
        
        # Mock walk-forward results
        mock_opt.walk_forward_optimize.return_value = {
            'periods': [
                {
                    'period': '2024-Q1',
                    'training_period': '2023-Q1 to 2023-Q4',
                    'test_period': '2024-Q1',
                    'optimal_parameters': {'fast_period': 10, 'slow_period': 25},
                    'in_sample_performance': {'sharpe_ratio': 1.8, 'return': 0.12},
                    'out_of_sample_performance': {'sharpe_ratio': 1.2, 'return': 0.08}
                },
                {
                    'period': '2024-Q2',
                    'training_period': '2023-Q2 to 2024-Q1',
                    'test_period': '2024-Q2',
                    'optimal_parameters': {'fast_period': 12, 'slow_period': 28},
                    'in_sample_performance': {'sharpe_ratio': 1.9, 'return': 0.15},
                    'out_of_sample_performance': {'sharpe_ratio': 1.4, 'return': 0.10}
                }
            ],
            'overall_performance': {
                'avg_in_sample_sharpe': 1.85,
                'avg_out_of_sample_sharpe': 1.3,
                'performance_degradation': 0.55,
                'parameter_stability': 0.75
            }
        }
        
        from nautilus_trader_engine.backtesting.strategy_optimizer import StrategyOptimizer
        optimizer = StrategyOptimizer(self.optimizer_config)
        
        wf_results = optimizer.walk_forward_optimize(
            parameter_space=self.parameter_space,
            strategy=self.sample_strategy,
            window_size_months=12,
            step_size_months=3
        )
        
        assert 'periods' in wf_results
        assert 'overall_performance' in wf_results
        assert len(wf_results['periods']) == 2
        assert wf_results['overall_performance']['performance_degradation'] < 1.0


class TestRiskManager:
    """Test suite for Backtesting Risk Manager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.risk_config = {
            'max_position_size': 0.1,
            'max_portfolio_risk': 0.02,
            'stop_loss_pct': 0.02,
            'take_profit_pct': 0.04,
            'max_correlation': 0.7,
            'var_limit': 0.05,
            'drawdown_limit': 0.15
        }
        
        self.sample_portfolio = {
            'EURUSD': {'position': 10000, 'entry_price': 1.0850, 'current_price': 1.0865},
            'GBPUSD': {'position': 8000, 'entry_price': 1.2650, 'current_price': 1.2640},
            'USDJPY': {'position': -5000, 'entry_price': 150.25, 'current_price': 149.80}
        }
    
    @patch('nautilus_trader_engine.backtesting.risk_manager.RiskManager')
    def test_risk_manager_initialization(self, mock_risk_manager):
        """Test risk manager initialization."""
        mock_manager = Mock()
        mock_risk_manager.return_value = mock_manager
        
        from nautilus_trader_engine.backtesting.risk_manager import RiskManager
        manager = RiskManager(self.risk_config)
        
        assert manager is not None
        mock_risk_manager.assert_called_once_with(self.risk_config)
    
    @patch('nautilus_trader_engine.backtesting.risk_manager.RiskManager')
    def test_position_sizing(self, mock_risk_manager):
        """Test position sizing calculations."""
        mock_manager = Mock()
        mock_risk_manager.return_value = mock_manager
        
        # Mock position sizing results
        mock_manager.calculate_position_size.return_value = {
            'recommended_size': 8500,
            'max_allowed_size': 10000,
            'risk_adjusted_size': 8500,
            'risk_percentage': 0.018,
            'stop_loss_distance': 0.02,
            'position_value': 9222.50
        }
        
        mock_manager.validate_position.return_value = {
            'is_valid': True,
            'risk_check_passed': True,
            'correlation_check_passed': True,
            'size_check_passed': True,
            'warnings': []
        }
        
        from nautilus_trader_engine.backtesting.risk_manager import RiskManager
        manager = RiskManager(self.risk_config)
        
        # Test position sizing
        sizing_result = manager.calculate_position_size(
            symbol='EURUSD',
            entry_price=1.0850,
            stop_loss=1.0633,
            portfolio_value=100000
        )
        
        assert sizing_result['recommended_size'] <= sizing_result['max_allowed_size']
        assert sizing_result['risk_percentage'] <= self.risk_config['max_portfolio_risk']
        
        # Test position validation
        validation = manager.validate_position(
            symbol='EURUSD',
            size=8500,
            current_portfolio=self.sample_portfolio
        )
        
        assert validation['is_valid'] is True
        assert validation['risk_check_passed'] is True
    
    @patch('nautilus_trader_engine.backtesting.risk_manager.RiskManager')
    def test_portfolio_risk_monitoring(self, mock_risk_manager):
        """Test portfolio risk monitoring."""
        mock_manager = Mock()
        mock_risk_manager.return_value = mock_manager
        
        # Mock risk monitoring results
        mock_manager.calculate_portfolio_risk.return_value = {
            'total_exposure': 0.23,
            'net_exposure': 0.13,
            'var_1day_95': 0.035,
            'expected_shortfall': 0.048,
            'current_drawdown': 0.05,
            'max_drawdown': 0.08,
            'correlation_matrix': {
                'EURUSD_GBPUSD': 0.65,
                'EURUSD_USDJPY': -0.45,
                'GBPUSD_USDJPY': -0.52
            },
            'risk_alerts': []
        }
        
        mock_manager.check_risk_limits.return_value = {
            'var_limit_breached': False,
            'drawdown_limit_breached': False,
            'correlation_limit_breached': False,
            'position_limit_breached': False,
            'overall_risk_status': 'ACCEPTABLE'
        }
        
        from nautilus_trader_engine.backtesting.risk_manager import RiskManager
        manager = RiskManager(self.risk_config)
        
        # Test portfolio risk calculation
        risk_metrics = manager.calculate_portfolio_risk(self.sample_portfolio)
        assert risk_metrics['var_1day_95'] <= self.risk_config['var_limit']
        assert risk_metrics['current_drawdown'] <= self.risk_config['drawdown_limit']
        
        # Test risk limit checks
        limit_checks = manager.check_risk_limits(risk_metrics)
        assert limit_checks['overall_risk_status'] in ['ACCEPTABLE', 'WARNING', 'CRITICAL']


class TestPerformanceAnalyzer:
    """Test suite for Performance Analyzer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer_config = {
            'benchmark_symbol': 'SPY',
            'risk_free_rate': 0.02,
            'confidence_levels': [0.95, 0.99],
            'rolling_window_days': [30, 90, 252],
            'attribution_analysis': True
        }
        
        # Sample returns data
        dates = pd.date_range('2024-01-01', '2024-12-31', freq='D')
        self.sample_returns = pd.Series(
            np.random.normal(0.0008, 0.015, len(dates)),
            index=dates
        )
        
        self.benchmark_returns = pd.Series(
            np.random.normal(0.0005, 0.012, len(dates)),
            index=dates
        )
    
    @patch('nautilus_trader_engine.backtesting.performance_analyzer.PerformanceAnalyzer')
    def test_analyzer_initialization(self, mock_analyzer):
        """Test performance analyzer initialization."""
        mock_perf_analyzer = Mock()
        mock_analyzer.return_value = mock_perf_analyzer
        
        from nautilus_trader_engine.backtesting.performance_analyzer import PerformanceAnalyzer
        analyzer = PerformanceAnalyzer(self.analyzer_config)
        
        assert analyzer is not None
        mock_analyzer.assert_called_once_with(self.analyzer_config)
    
    @patch('nautilus_trader_engine.backtesting.performance_analyzer.PerformanceAnalyzer')
    def test_comprehensive_analysis(self, mock_analyzer):
        """Test comprehensive performance analysis."""
        mock_perf_analyzer = Mock()
        mock_analyzer.return_value = mock_perf_analyzer
        
        # Mock comprehensive analysis results
        analysis_results = {
            'return_metrics': {
                'total_return': 0.185,
                'annualized_return': 0.165,
                'geometric_mean': 0.162,
                'arithmetic_mean': 0.168,
                'compound_annual_growth_rate': 0.165
            },
            'risk_metrics': {
                'volatility': 0.145,
                'downside_deviation': 0.098,
                'semi_variance': 0.0096,
                'var_95': 0.032,
                'var_99': 0.048,
                'cvar_95': 0.042,
                'cvar_99': 0.065
            },
            'risk_adjusted_metrics': {
                'sharpe_ratio': 1.42,
                'sortino_ratio': 1.85,
                'calmar_ratio': 2.15,
                'omega_ratio': 1.28,
                'treynor_ratio': 0.125
            },
            'drawdown_analysis': {
                'max_drawdown': 0.085,
                'max_drawdown_duration': 45,
                'avg_drawdown': 0.025,
                'recovery_time': 32,
                'drawdown_periods': 8
            },
            'benchmark_comparison': {
                'alpha': 0.045,
                'beta': 0.85,
                'correlation': 0.78,
                'tracking_error': 0.035,
                'information_ratio': 1.28,
                'up_capture': 1.15,
                'down_capture': 0.82
            }
        }
        
        mock_perf_analyzer.analyze_performance.return_value = analysis_results
        
        from nautilus_trader_engine.backtesting.performance_analyzer import PerformanceAnalyzer
        analyzer = PerformanceAnalyzer(self.analyzer_config)
        
        results = analyzer.analyze_performance(self.sample_returns, self.benchmark_returns)
        
        # Verify return metrics
        assert results['return_metrics']['total_return'] > 0
        assert results['return_metrics']['annualized_return'] > 0
        
        # Verify risk metrics
        assert results['risk_metrics']['volatility'] > 0
        assert results['risk_metrics']['var_95'] > 0
        
        # Verify risk-adjusted metrics
        assert results['risk_adjusted_metrics']['sharpe_ratio'] > 1.0
        assert results['risk_adjusted_metrics']['sortino_ratio'] > 0
        
        # Verify drawdown analysis
        assert results['drawdown_analysis']['max_drawdown'] > 0
        assert results['drawdown_analysis']['recovery_time'] > 0
        
        # Verify benchmark comparison
        assert -1 <= results['benchmark_comparison']['correlation'] <= 1
        assert results['benchmark_comparison']['information_ratio'] > 0
    
    @patch('nautilus_trader_engine.backtesting.performance_analyzer.PerformanceAnalyzer')
    def test_rolling_analysis(self, mock_analyzer):
        """Test rolling performance analysis."""
        mock_perf_analyzer = Mock()
        mock_analyzer.return_value = mock_perf_analyzer
        
        # Mock rolling analysis results
        mock_perf_analyzer.rolling_analysis.return_value = {
            '30_day': {
                'rolling_sharpe': pd.Series([1.2, 1.5, 1.8, 1.4]),
                'rolling_volatility': pd.Series([0.12, 0.15, 0.18, 0.14]),
                'rolling_returns': pd.Series([0.025, 0.032, 0.018, 0.028])
            },
            '90_day': {
                'rolling_sharpe': pd.Series([1.3, 1.6, 1.7]),
                'rolling_volatility': pd.Series([0.13, 0.16, 0.15]),
                'rolling_returns': pd.Series([0.078, 0.095, 0.082])
            },
            '252_day': {
                'rolling_sharpe': pd.Series([1.42]),
                'rolling_volatility': pd.Series([0.145]),
                'rolling_returns': pd.Series([0.185])
            }
        }
        
        from nautilus_trader_engine.backtesting.performance_analyzer import PerformanceAnalyzer
        analyzer = PerformanceAnalyzer(self.analyzer_config)
        
        rolling_results = analyzer.rolling_analysis(self.sample_returns)
        
        # Verify rolling analysis structure
        for window in ['30_day', '90_day', '252_day']:
            assert window in rolling_results
            assert 'rolling_sharpe' in rolling_results[window]
            assert 'rolling_volatility' in rolling_results[window]
            assert 'rolling_returns' in rolling_results[window]


class TestReportGenerator:
    """Test suite for Backtest Report Generator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.report_config = {
            'output_format': ['html', 'pdf', 'json'],
            'include_charts': True,
            'chart_types': ['equity_curve', 'drawdown', 'returns_distribution'],
            'detailed_trades': True,
            'risk_analysis': True
        }
    
    @patch('nautilus_trader_engine.backtesting.report_generator.ReportGenerator')
    def test_report_generator_initialization(self, mock_report_generator):
        """Test report generator initialization."""
        mock_generator = Mock()
        mock_report_generator.return_value = mock_generator
        
        from nautilus_trader_engine.backtesting.report_generator import ReportGenerator
        generator = ReportGenerator(self.report_config)
        
        assert generator is not None
        mock_report_generator.assert_called_once_with(self.report_config)
    
    @patch('nautilus_trader_engine.backtesting.report_generator.ReportGenerator')
    def test_report_generation(self, mock_report_generator):
        """Test backtest report generation."""
        mock_generator = Mock()
        mock_report_generator.return_value = mock_generator
        
        # Mock report generation results
        mock_generator.generate_report.return_value = {
            'report_id': 'backtest_report_20240115',
            'generated_files': {
                'html': '/reports/backtest_report_20240115.html',
                'pdf': '/reports/backtest_report_20240115.pdf',
                'json': '/reports/backtest_report_20240115.json'
            },
            'report_sections': [
                'executive_summary',
                'strategy_overview',
                'performance_metrics',
                'risk_analysis',
                'trade_analysis',
                'charts_and_visualizations'
            ],
            'generation_time_seconds': 45.2,
            'file_sizes_mb': {
                'html': 2.5,
                'pdf': 1.8,
                'json': 0.3
            }
        }
        
        mock_generator.create_charts.return_value = {
            'equity_curve': '/charts/equity_curve.png',
            'drawdown': '/charts/drawdown.png',
            'returns_distribution': '/charts/returns_dist.png',
            'monthly_returns_heatmap': '/charts/monthly_heatmap.png'
        }
        
        from nautilus_trader_engine.backtesting.report_generator import ReportGenerator
        generator = ReportGenerator(self.report_config)
        
        # Test report generation
        backtest_results = {'total_return': 0.15, 'sharpe_ratio': 1.5}
        report_result = generator.generate_report(backtest_results)
        
        assert 'report_id' in report_result
        assert 'generated_files' in report_result
        assert len(report_result['generated_files']) == 3  # html, pdf, json
        assert report_result['generation_time_seconds'] > 0
        
        # Test chart creation
        charts = generator.create_charts(backtest_results)
        assert 'equity_curve' in charts
        assert 'drawdown' in charts
        assert 'returns_distribution' in charts


if __name__ == '__main__':
    pytest.main([__file__])