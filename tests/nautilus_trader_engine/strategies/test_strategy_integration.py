"""
Integration tests for strategy module interactions.

This module tests the integration between different strategy components including:
- BaseStrategy with utility functions
- Performance tracking integration
- Signal processing workflows
- Logging and monitoring integration
- End-to-end strategy execution flows
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
import logging
import tempfile
import os

# Import strategy modules
from nautilus_trader_engine.strategies.core.base_strategy import (
    BaseStrategy, StrategyConfig, RiskParameters, Position, Signal,
    StrategyType, PositionSide, SignalType, SignalStrength, StrategyState
)
from nautilus_trader_engine.strategies.utils.strategy_utilities import (
    StrategyUtilities, DataValidation, PositionSizing, RiskLevel
)
from nautilus_trader_engine.strategies.utils.performance_tracker import (
    PerformanceTracker, TradeMetrics, PerformanceSnapshot
)
from nautilus_trader_engine.strategies.utils.signal_processing import (
    SignalProcessor, TradingSignal, SignalAggregationResult
)
from nautilus_trader_engine.strategies.utils.logging_config import (
    setup_trading_logger, PerformanceMonitor, performance_monitor, trade_event
)


class TestStrategyIntegration:
    """Test integration between strategy components."""
    
    @pytest.fixture
    def strategy_config(self):
        """Create a test strategy configuration."""
        return StrategyConfig(
            name="test_integration_strategy",
            strategy_type=StrategyType.MOMENTUM,
            risk_parameters=RiskParameters(
                max_position_size=Decimal('10000'),
                stop_loss_pct=Decimal('0.02'),
                take_profit_pct=Decimal('0.05'),
                max_daily_loss=Decimal('1000'),
                position_sizing=PositionSizing.FIXED
            ),
            parameters={'lookback_period': 20, 'threshold': 0.02}
        )
    
    @pytest.fixture
    def mock_strategy(self, strategy_config):
        """Create a mock strategy for testing."""
        class MockStrategy(BaseStrategy):
            def generate_signals(self, market_data: pd.DataFrame) -> list[Signal]:
                """Generate mock signals."""
                if len(market_data) < 2:
                    return []
                
                current_price = market_data['close'].iloc[-1]
                signal = Signal(
                    signal_type=SignalType.BUY,
                    strength=SignalStrength.STRONG,
                    price=Decimal(str(current_price)),
                    confidence=0.8,
                    timestamp=datetime.now()
                )
                return [signal]
            
            def calculate_position_size(self, signal: Signal, account_balance: Decimal) -> Decimal:
                """Calculate position size."""
                return StrategyUtilities.calculate_position_size(
                    account_balance=account_balance,
                    risk_per_trade=Decimal('0.02'),
                    entry_price=signal.price,
                    stop_loss_price=signal.price * Decimal('0.98')
                )
        
        return MockStrategy(strategy_config)
    
    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        np.random.seed(42)
        
        # Generate realistic price data
        returns = np.random.normal(0.001, 0.02, 100)
        prices = 100 * np.exp(np.cumsum(returns))
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices * (1 + np.random.normal(0, 0.001, 100)),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.005, 100))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.005, 100))),
            'close': prices,
            'volume': np.random.randint(1000, 10000, 100)
        })
    
    def test_strategy_initialization_integration(self, mock_strategy):
        """Test strategy initialization with all components."""
        # Verify strategy is properly initialized
        assert mock_strategy.state == StrategyState.INITIALIZED
        assert mock_strategy.performance_tracker is not None
        assert mock_strategy.positions == {}
        assert mock_strategy.total_pnl == Decimal('0')
        
        # Verify configuration is properly set
        assert mock_strategy.config.name == "test_integration_strategy"
        assert mock_strategy.config.strategy_type == StrategyType.MOMENTUM
    
    def test_signal_generation_and_processing_integration(self, mock_strategy, sample_market_data):
        """Test integration between signal generation and processing."""
        # Generate signals
        signals = mock_strategy.generate_signals(sample_market_data)
        
        assert len(signals) > 0
        signal = signals[0]
        assert isinstance(signal, Signal)
        assert signal.signal_type == SignalType.BUY
        assert signal.strength == SignalStrength.STRONG
        
        # Process signals with SignalProcessor
        signal_processor = SignalProcessor()
        trading_signal = TradingSignal(
            signal_type=signal.signal_type,
            strength=signal.strength,
            price=float(signal.price),
            confidence=signal.confidence,
            timestamp=signal.timestamp,
            metadata={'source': 'integration_test'}
        )
        
        # Test signal aggregation
        aggregation_result = signal_processor.aggregate_signals([trading_signal])
        assert isinstance(aggregation_result, SignalAggregationResult)
        assert aggregation_result.consensus_signal == signal.signal_type
    
    def test_position_management_integration(self, mock_strategy, sample_market_data):
        """Test position management with utility functions."""
        # Generate signal and calculate position size
        signals = mock_strategy.generate_signals(sample_market_data)
        signal = signals[0]
        
        account_balance = Decimal('100000')
        position_size = mock_strategy.calculate_position_size(signal, account_balance)
        
        assert position_size > 0
        assert position_size <= account_balance
        
        # Create and add position
        position = Position(
            symbol="TEST",
            side=PositionSide.LONG,
            size=position_size,
            entry_price=signal.price,
            timestamp=datetime.now()
        )
        
        mock_strategy.add_position("TEST", position)
        assert "TEST" in mock_strategy.positions
        
        # Update position price and verify PnL calculation
        new_price = signal.price * Decimal('1.05')  # 5% gain
        position.update_price(new_price)
        
        expected_pnl = position_size * (new_price - signal.price)
        assert abs(position.pnl - expected_pnl) < Decimal('0.01')
    
    def test_performance_tracking_integration(self, mock_strategy, sample_market_data):
        """Test performance tracking integration."""
        # Execute a complete trade cycle
        signals = mock_strategy.generate_signals(sample_market_data)
        signal = signals[0]
        
        account_balance = Decimal('100000')
        position_size = mock_strategy.calculate_position_size(signal, account_balance)
        
        # Create position
        position = Position(
            symbol="TEST",
            side=PositionSide.LONG,
            size=position_size,
            entry_price=signal.price,
            timestamp=datetime.now()
        )
        
        mock_strategy.add_position("TEST", position)
        
        # Simulate price movement and close position
        exit_price = signal.price * Decimal('1.03')  # 3% gain
        position.update_price(exit_price)
        
        # Record trade in performance tracker
        trade_pnl = position.pnl
        mock_strategy.performance_tracker.record_trade(
            symbol="TEST",
            entry_price=float(signal.price),
            exit_price=float(exit_price),
            quantity=float(position_size),
            side="long",
            entry_time=position.timestamp,
            exit_time=datetime.now(),
            pnl=float(trade_pnl)
        )
        
        # Verify performance metrics
        metrics = mock_strategy.performance_tracker.get_performance_summary()
        assert metrics.total_trades == 1
        assert metrics.winning_trades == 1
        assert metrics.total_pnl > 0
    
    def test_risk_management_integration(self, mock_strategy):
        """Test risk management integration across components."""
        # Test position sizing with risk parameters
        signal_price = Decimal('100')
        account_balance = Decimal('50000')
        
        # Calculate position size using utility functions
        position_size = StrategyUtilities.calculate_position_size(
            account_balance=account_balance,
            risk_per_trade=mock_strategy.config.risk_parameters.stop_loss_pct,
            entry_price=signal_price,
            stop_loss_price=signal_price * Decimal('0.98')
        )
        
        # Verify position size respects maximum limits
        max_position = mock_strategy.config.risk_parameters.max_position_size
        assert position_size <= max_position
        
        # Test risk metrics calculation
        risk_metrics = StrategyUtilities.calculate_risk_metrics(
            returns=pd.Series([0.01, -0.005, 0.02, -0.01, 0.015]),
            risk_free_rate=0.02
        )
        
        assert 'sharpe_ratio' in risk_metrics
        assert 'max_drawdown' in risk_metrics
        assert 'var_95' in risk_metrics
    
    def test_logging_integration(self, mock_strategy, sample_market_data):
        """Test logging integration across strategy components."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, 'test_strategy.log')
            
            # Setup logger
            logger = setup_trading_logger(
                name="test_integration",
                log_file=log_file,
                level=logging.INFO
            )
            
            # Test performance monitoring decorator
            @performance_monitor(logger)
            def test_strategy_operation():
                signals = mock_strategy.generate_signals(sample_market_data)
                return len(signals)
            
            # Test trade event logging decorator
            @trade_event(logger)
            def test_trade_execution(symbol: str, action: str, quantity: float):
                return f"Executed {action} {quantity} shares of {symbol}"
            
            # Execute operations
            signal_count = test_strategy_operation()
            trade_result = test_trade_execution("TEST", "BUY", 100.0)
            
            assert signal_count > 0
            assert "Executed BUY" in trade_result
            
            # Verify log file was created and contains entries
            assert os.path.exists(log_file)
            with open(log_file, 'r') as f:
                log_content = f.read()
                assert 'test_strategy_operation' in log_content
                assert 'test_trade_execution' in log_content
    
    def test_data_validation_integration(self, sample_market_data):
        """Test data validation integration."""
        # Test valid data
        assert DataValidation.validate_price_data(sample_market_data)
        
        # Test invalid data
        invalid_data = sample_market_data.copy()
        invalid_data.loc[0, 'close'] = -10  # Invalid negative price
        
        assert not DataValidation.validate_price_data(invalid_data)
        
        # Test strategy config validation
        valid_config = {
            'name': 'test_strategy',
            'lookback_period': 20,
            'threshold': 0.02
        }
        assert DataValidation.validate_strategy_config(valid_config)
        
        invalid_config = {
            'name': '',  # Invalid empty name
            'lookback_period': -5,  # Invalid negative period
            'threshold': 2.0  # Invalid threshold > 1
        }
        assert not DataValidation.validate_strategy_config(invalid_config)
    
    def test_end_to_end_strategy_execution(self, mock_strategy, sample_market_data):
        """Test complete end-to-end strategy execution flow."""
        # Initialize performance monitoring
        performance_monitor = PerformanceMonitor()
        
        # Execute complete strategy cycle
        account_balance = Decimal('100000')
        
        # 1. Generate signals
        signals = mock_strategy.generate_signals(sample_market_data)
        assert len(signals) > 0
        
        # 2. Process each signal
        for signal in signals:
            # Calculate position size
            position_size = mock_strategy.calculate_position_size(signal, account_balance)
            
            # Create position
            position = Position(
                symbol="TEST",
                side=PositionSide.LONG if signal.signal_type == SignalType.BUY else PositionSide.SHORT,
                size=position_size,
                entry_price=signal.price,
                timestamp=signal.timestamp
            )
            
            # Add position to strategy
            mock_strategy.add_position("TEST", position)
            
            # Simulate market movement
            price_change = 0.02 if signal.signal_type == SignalType.BUY else -0.02
            new_price = signal.price * Decimal(str(1 + price_change))
            position.update_price(new_price)
            
            # Record trade
            mock_strategy.performance_tracker.record_trade(
                symbol="TEST",
                entry_price=float(signal.price),
                exit_price=float(new_price),
                quantity=float(position_size),
                side="long" if signal.signal_type == SignalType.BUY else "short",
                entry_time=signal.timestamp,
                exit_time=datetime.now(),
                pnl=float(position.pnl)
            )
        
        # 3. Verify final state
        performance_summary = mock_strategy.performance_tracker.get_performance_summary()
        assert performance_summary.total_trades > 0
        
        # 4. Update strategy performance metrics
        mock_strategy.update_performance_metrics()
        
        # Verify strategy state is consistent
        assert mock_strategy.state in [StrategyState.RUNNING, StrategyState.INITIALIZED]
        assert len(mock_strategy.positions) > 0
    
    @pytest.mark.asyncio
    async def test_async_strategy_operations(self, mock_strategy, sample_market_data):
        """Test asynchronous strategy operations integration."""
        async def async_signal_generation():
            """Simulate async signal generation."""
            await asyncio.sleep(0.1)  # Simulate processing time
            return mock_strategy.generate_signals(sample_market_data)
        
        async def async_position_update():
            """Simulate async position updates."""
            await asyncio.sleep(0.05)
            return "Position updated"
        
        # Execute async operations concurrently
        signals_task = asyncio.create_task(async_signal_generation())
        update_task = asyncio.create_task(async_position_update())
        
        signals, update_result = await asyncio.gather(signals_task, update_task)
        
        assert len(signals) > 0
        assert update_result == "Position updated"
    
    def test_error_handling_integration(self, mock_strategy):
        """Test error handling across integrated components."""
        # Test invalid market data handling
        invalid_data = pd.DataFrame()  # Empty dataframe
        
        signals = mock_strategy.generate_signals(invalid_data)
        assert len(signals) == 0  # Should handle gracefully
        
        # Test invalid position size calculation
        with pytest.raises((ValueError, TypeError)):
            StrategyUtilities.calculate_position_size(
                account_balance=Decimal('-1000'),  # Invalid negative balance
                risk_per_trade=Decimal('0.02'),
                entry_price=Decimal('100'),
                stop_loss_price=Decimal('98')
            )
        
        # Test invalid signal processing
        signal_processor = SignalProcessor()
        invalid_signals = []  # Empty signal list
        
        result = signal_processor.aggregate_signals(invalid_signals)
        assert result.consensus_signal is None  # Should handle gracefully
    
    def test_memory_and_performance_integration(self, mock_strategy, sample_market_data):
        """Test memory usage and performance across integrated components."""
        import psutil
        import time
        
        # Measure initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Execute multiple strategy cycles
        start_time = time.time()
        
        for i in range(10):
            signals = mock_strategy.generate_signals(sample_market_data)
            for signal in signals:
                position_size = mock_strategy.calculate_position_size(
                    signal, Decimal('100000')
                )
                
                position = Position(
                    symbol=f"TEST_{i}",
                    side=PositionSide.LONG,
                    size=position_size,
                    entry_price=signal.price,
                    timestamp=datetime.now()
                )
                
                mock_strategy.add_position(f"TEST_{i}", position)
        
        execution_time = time.time() - start_time
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Verify performance constraints
        assert execution_time < 5.0  # Should complete within 5 seconds
        assert memory_increase < 50 * 1024 * 1024  # Should not increase by more than 50MB
        
        # Cleanup
        mock_strategy.positions.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])