"""Unit Tests for Base Strategy Module

This module contains comprehensive unit tests for the BaseStrategy class
and related components in the reorganized strategy structure.

Author: AI Assistant
Date: 2024-12-15
"""

import unittest
import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from decimal import Decimal

# Import the modules to test
try:
    from nautilus_trader_engine.strategies.base_strategy import (
        BaseStrategy,
        StrategyState,
        StrategyConfig,
        RiskParameters,
        PositionSizing,
        SignalType
    )
    from nautilus_trader_engine.strategies.utils.strategy_utilities import (
        StrategyUtilities,
        DataValidation,
        ValidationResult
    )
    from nautilus_trader_engine.strategies.utils.performance_tracker import (
        PerformanceTracker,
        TradeMetrics,
        PerformanceSnapshot
    )
    from nautilus_trader_engine.strategies.utils.logging_config import (
        get_logger,
        LogLevel
    )
except ImportError as e:
    # Handle import errors gracefully for testing
    print(f"Import warning: {e}")
    BaseStrategy = None


class TestBaseStrategy(unittest.TestCase):
    """Test cases for BaseStrategy class"""
    
    def setUp(self):
        """Set up test fixtures"""
        if BaseStrategy is None:
            self.skipTest("BaseStrategy not available")
        
        # Mock configuration
        self.config = StrategyConfig(
            strategy_id="test_strategy",
            instrument_id="EURUSD.SIM",
            bar_type="EURUSD.SIM-1-MINUTE-BID-INTERNAL",
            risk_parameters=RiskParameters(
                max_position_size=Decimal('100000'),
                max_daily_loss=Decimal('1000'),
                position_sizing=PositionSizing.FIXED
            )
        )
        
        # Create strategy instance
        self.strategy = BaseStrategy(config=self.config)
        
        # Mock logger
        self.strategy.log = Mock()
        
        # Sample market data
        self.sample_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='1min'),
            'open': np.random.uniform(1.0800, 1.0900, 100),
            'high': np.random.uniform(1.0850, 1.0950, 100),
            'low': np.random.uniform(1.0750, 1.0850, 100),
            'close': np.random.uniform(1.0800, 1.0900, 100),
            'volume': np.random.uniform(1000, 10000, 100)
        })
    
    def test_strategy_initialization(self):
        """Test strategy initialization"""
        self.assertEqual(self.strategy.config.strategy_id, "test_strategy")
        self.assertEqual(self.strategy.state, StrategyState.INITIALIZED)
        self.assertIsNotNone(self.strategy.performance_tracker)
        self.assertIsInstance(self.strategy.utilities, StrategyUtilities)
    
    def test_strategy_state_transitions(self):
        """Test strategy state transitions"""
        # Test start
        self.strategy.on_start()
        self.assertEqual(self.strategy.state, StrategyState.RUNNING)
        
        # Test stop
        self.strategy.on_stop()
        self.assertEqual(self.strategy.state, StrategyState.STOPPED)
        
        # Test reset
        self.strategy.on_reset()
        self.assertEqual(self.strategy.state, StrategyState.INITIALIZED)
    
    def test_risk_management(self):
        """Test risk management functionality"""
        # Test position size calculation
        position_size = self.strategy._calculate_position_size(
            signal_strength=0.8,
            current_price=Decimal('1.0850'),
            account_balance=Decimal('10000')
        )
        
        self.assertIsInstance(position_size, Decimal)
        self.assertGreater(position_size, 0)
        self.assertLessEqual(position_size, self.config.risk_parameters.max_position_size)
    
    def test_signal_generation(self):
        """Test signal generation methods"""
        # Mock market data
        with patch.object(self.strategy, '_get_current_market_data') as mock_data:
            mock_data.return_value = {
                'price': Decimal('1.0850'),
                'volume': 5000,
                'timestamp': datetime.now()
            }
            
            # Test signal generation
            signal = self.strategy._generate_signal()
            
            # Signal should be one of the valid types
            self.assertIn(signal, [SignalType.BUY, SignalType.SELL, SignalType.HOLD])
    
    def test_performance_tracking(self):
        """Test performance tracking integration"""
        # Simulate a trade
        trade_data = {
            'symbol': 'EURUSD',
            'side': 'buy',
            'quantity': 10000,
            'entry_price': 1.0850,
            'exit_price': 1.0870,
            'entry_time': datetime.now() - timedelta(hours=1),
            'exit_time': datetime.now(),
            'pnl': 200.0
        }
        
        # Add trade to performance tracker
        self.strategy.performance_tracker.add_trade(**trade_data)
        
        # Check that trade was recorded
        metrics = self.strategy.performance_tracker.get_current_metrics()
        self.assertEqual(metrics.total_trades, 1)
        self.assertEqual(metrics.total_pnl, 200.0)
    
    def test_error_handling(self):
        """Test error handling in strategy methods"""
        # Test with invalid data
        with patch.object(self.strategy, '_get_current_market_data') as mock_data:
            mock_data.side_effect = Exception("Data feed error")
            
            # Strategy should handle the error gracefully
            try:
                self.strategy._generate_signal()
            except Exception:
                self.fail("Strategy should handle data feed errors gracefully")
    
    def test_configuration_validation(self):
        """Test strategy configuration validation"""
        # Test valid configuration
        valid_config = StrategyConfig(
            strategy_id="valid_strategy",
            instrument_id="EURUSD.SIM",
            bar_type="EURUSD.SIM-1-MINUTE-BID-INTERNAL",
            risk_parameters=RiskParameters(
                max_position_size=Decimal('50000'),
                max_daily_loss=Decimal('500'),
                position_sizing=PositionSizing.PERCENTAGE
            )
        )
        
        strategy = BaseStrategy(config=valid_config)
        self.assertEqual(strategy.config.strategy_id, "valid_strategy")
        
        # Test invalid configuration (should raise exception)
        with self.assertRaises((ValueError, TypeError)):
            invalid_config = StrategyConfig(
                strategy_id="",  # Empty strategy ID
                instrument_id="INVALID",
                bar_type="",
                risk_parameters=None
            )
            BaseStrategy(config=invalid_config)


class TestStrategyUtilities(unittest.TestCase):
    """Test cases for StrategyUtilities class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.utilities = StrategyUtilities()
        
        # Sample price data
        self.price_data = pd.Series([
            1.0800, 1.0820, 1.0810, 1.0830, 1.0850,
            1.0840, 1.0860, 1.0870, 1.0850, 1.0880
        ])
        
        self.volume_data = pd.Series([
            1000, 1500, 1200, 1800, 2000,
            1600, 2200, 2500, 1900, 2100
        ])
    
    def test_position_sizing_fixed(self):
        """Test fixed position sizing"""
        position_size = self.utilities.calculate_position_size(
            method=PositionSizing.FIXED,
            account_balance=10000,
            risk_per_trade=0.02,
            entry_price=1.0850,
            stop_loss_price=1.0800,
            fixed_amount=1000
        )
        
        self.assertEqual(position_size, 1000)
    
    def test_position_sizing_percentage(self):
        """Test percentage-based position sizing"""
        position_size = self.utilities.calculate_position_size(
            method=PositionSizing.PERCENTAGE,
            account_balance=10000,
            risk_per_trade=0.02,
            entry_price=1.0850,
            stop_loss_price=1.0800,
            percentage=0.1
        )
        
        expected_size = 10000 * 0.1
        self.assertEqual(position_size, expected_size)
    
    def test_stop_loss_calculation(self):
        """Test stop loss calculation"""
        stop_loss = self.utilities.calculate_stop_loss(
            entry_price=1.0850,
            atr=0.0020,
            multiplier=2.0,
            side='buy'
        )
        
        expected_stop = 1.0850 - (0.0020 * 2.0)
        self.assertAlmostEqual(stop_loss, expected_stop, places=4)
    
    def test_take_profit_calculation(self):
        """Test take profit calculation"""
        take_profit = self.utilities.calculate_take_profit(
            entry_price=1.0850,
            stop_loss_price=1.0800,
            risk_reward_ratio=2.0,
            side='buy'
        )
        
        risk = 1.0850 - 1.0800
        expected_tp = 1.0850 + (risk * 2.0)
        self.assertAlmostEqual(take_profit, expected_tp, places=4)
    
    def test_risk_metrics(self):
        """Test risk metrics calculation"""
        returns = pd.Series([0.01, -0.005, 0.02, -0.01, 0.015])
        
        sharpe_ratio = self.utilities.calculate_sharpe_ratio(returns)
        max_drawdown = self.utilities.calculate_max_drawdown(returns.cumsum())
        
        self.assertIsInstance(sharpe_ratio, float)
        self.assertIsInstance(max_drawdown, float)
        self.assertLessEqual(max_drawdown, 0)  # Max drawdown should be negative or zero
    
    def test_data_normalization(self):
        """Test data normalization"""
        normalized = self.utilities.normalize_data(self.price_data)
        
        # Normalized data should have mean ~0 and std ~1
        self.assertAlmostEqual(normalized.mean(), 0, places=10)
        self.assertAlmostEqual(normalized.std(), 1, places=10)
    
    def test_outlier_detection(self):
        """Test outlier detection"""
        # Add some outliers to the data
        data_with_outliers = self.price_data.copy()
        data_with_outliers.iloc[0] = 2.0  # Clear outlier
        
        outliers = self.utilities.detect_outliers(data_with_outliers)
        
        self.assertIsInstance(outliers, pd.Series)
        self.assertTrue(outliers.iloc[0])  # First value should be detected as outlier
    
    def test_correlation_matrix(self):
        """Test correlation matrix calculation"""
        data = pd.DataFrame({
            'price': self.price_data,
            'volume': self.volume_data
        })
        
        corr_matrix = self.utilities.calculate_correlation_matrix(data)
        
        self.assertIsInstance(corr_matrix, pd.DataFrame)
        self.assertEqual(corr_matrix.shape, (2, 2))
        self.assertEqual(corr_matrix.loc['price', 'price'], 1.0)


class TestDataValidation(unittest.TestCase):
    """Test cases for DataValidation class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = DataValidation()
        
        # Valid price data
        self.valid_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='1min'),
            'open': [1.08] * 10,
            'high': [1.09] * 10,
            'low': [1.07] * 10,
            'close': [1.08] * 10,
            'volume': [1000] * 10
        })
    
    def test_valid_price_data(self):
        """Test validation of valid price data"""
        result = self.validator.validate_price_data(self.valid_data)
        
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_invalid_price_data_missing_columns(self):
        """Test validation with missing columns"""
        invalid_data = self.valid_data.drop(columns=['high', 'low'])
        result = self.validator.validate_price_data(invalid_data)
        
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
    
    def test_invalid_price_data_negative_values(self):
        """Test validation with negative prices"""
        invalid_data = self.valid_data.copy()
        invalid_data.loc[0, 'close'] = -1.0
        
        result = self.validator.validate_price_data(invalid_data)
        
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
    
    def test_invalid_price_data_ohlc_logic(self):
        """Test validation of OHLC logic"""
        invalid_data = self.valid_data.copy()
        invalid_data.loc[0, 'high'] = 1.06  # High < Low
        invalid_data.loc[0, 'low'] = 1.09
        
        result = self.validator.validate_price_data(invalid_data)
        
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
    
    def test_strategy_config_validation(self):
        """Test strategy configuration validation"""
        valid_config = {
            'strategy_id': 'test_strategy',
            'instrument_id': 'EURUSD.SIM',
            'max_position_size': 100000,
            'risk_per_trade': 0.02
        }
        
        result = self.validator.validate_strategy_config(valid_config)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_invalid_strategy_config(self):
        """Test invalid strategy configuration"""
        invalid_config = {
            'strategy_id': '',  # Empty ID
            'instrument_id': 'INVALID',
            'max_position_size': -1000,  # Negative size
            'risk_per_trade': 1.5  # Risk > 100%
        }
        
        result = self.validator.validate_strategy_config(invalid_config)
        
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)


class TestPerformanceTracker(unittest.TestCase):
    """Test cases for PerformanceTracker class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tracker = PerformanceTracker()
        
        # Sample trades
        self.sample_trades = [
            {
                'symbol': 'EURUSD',
                'side': 'buy',
                'quantity': 10000,
                'entry_price': 1.0800,
                'exit_price': 1.0820,
                'entry_time': datetime(2024, 1, 1, 10, 0),
                'exit_time': datetime(2024, 1, 1, 11, 0),
                'pnl': 200.0
            },
            {
                'symbol': 'EURUSD',
                'side': 'sell',
                'quantity': 10000,
                'entry_price': 1.0850,
                'exit_price': 1.0830,
                'entry_time': datetime(2024, 1, 1, 12, 0),
                'exit_time': datetime(2024, 1, 1, 13, 0),
                'pnl': 200.0
            },
            {
                'symbol': 'EURUSD',
                'side': 'buy',
                'quantity': 10000,
                'entry_price': 1.0870,
                'exit_price': 1.0860,
                'entry_time': datetime(2024, 1, 1, 14, 0),
                'exit_time': datetime(2024, 1, 1, 15, 0),
                'pnl': -100.0
            }
        ]
    
    def test_add_trades(self):
        """Test adding trades to tracker"""
        for trade in self.sample_trades:
            self.tracker.add_trade(**trade)
        
        metrics = self.tracker.get_current_metrics()
        
        self.assertEqual(metrics.total_trades, 3)
        self.assertEqual(metrics.winning_trades, 2)
        self.assertEqual(metrics.losing_trades, 1)
        self.assertEqual(metrics.total_pnl, 300.0)
    
    def test_performance_metrics_calculation(self):
        """Test performance metrics calculation"""
        for trade in self.sample_trades:
            self.tracker.add_trade(**trade)
        
        metrics = self.tracker.get_current_metrics()
        
        # Test win rate
        expected_win_rate = 2 / 3  # 2 winning trades out of 3
        self.assertAlmostEqual(metrics.win_rate, expected_win_rate, places=2)
        
        # Test average win/loss
        self.assertEqual(metrics.average_win, 200.0)
        self.assertEqual(metrics.average_loss, -100.0)
        
        # Test profit factor
        expected_profit_factor = 400.0 / 100.0  # Total wins / Total losses
        self.assertAlmostEqual(metrics.profit_factor, expected_profit_factor, places=2)
    
    def test_performance_snapshot(self):
        """Test performance snapshot generation"""
        for trade in self.sample_trades:
            self.tracker.add_trade(**trade)
        
        snapshot = self.tracker.get_performance_snapshot()
        
        self.assertIsInstance(snapshot, PerformanceSnapshot)
        self.assertEqual(snapshot.total_trades, 3)
        self.assertEqual(snapshot.total_pnl, 300.0)
        self.assertIsInstance(snapshot.timestamp, datetime)
    
    def test_time_based_analysis(self):
        """Test time-based performance analysis"""
        for trade in self.sample_trades:
            self.tracker.add_trade(**trade)
        
        # Test daily analysis
        daily_analysis = self.tracker.analyze_performance_by_time('daily')
        
        self.assertIsInstance(daily_analysis, dict)
        # All trades are on the same day, so should have one entry
        self.assertEqual(len(daily_analysis), 1)
    
    def test_risk_analysis(self):
        """Test risk analysis functionality"""
        for trade in self.sample_trades:
            self.tracker.add_trade(**trade)
        
        risk_metrics = self.tracker.calculate_risk_metrics()
        
        self.assertIsInstance(risk_metrics, dict)
        self.assertIn('max_drawdown', risk_metrics)
        self.assertIn('sharpe_ratio', risk_metrics)
        self.assertIn('sortino_ratio', risk_metrics)
    
    def test_generate_report(self):
        """Test report generation"""
        for trade in self.sample_trades:
            self.tracker.add_trade(**trade)
        
        report = self.tracker.generate_report()
        
        self.assertIsInstance(report, dict)
        self.assertIn('summary', report)
        self.assertIn('trades', report)
        self.assertIn('risk_metrics', report)


if __name__ == '__main__':
    # Configure test logging
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run tests
    unittest.main(verbosity=2)