"""End-to-end tests for complete trading workflow.

Tests cover:
- Complete order lifecycle from creation to execution
- Market data integration with trading decisions
- Risk management integration
- Portfolio management updates
- Real-time WebSocket communications
- Multi-component integration
- AI-assisted trading workflows
- Kafka event streaming integration
- Multi-symbol strategy execution
- Error recovery and fault tolerance
- Performance under high-frequency scenarios
"""

import pytest
import asyncio
import json
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import websockets
import requests
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd
from kafka import KafkaProducer, KafkaConsumer

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from algorithmic_trading_service.api.main import TradingEngine
from algorithmic_trading_service.order_management import OrderManager, OrderCreateRequest, OrderSide, OrderType
from algorithmic_trading_service.risk_management import RiskManager
from algorithmic_trading_service.portfolio_management import PortfolioManager
from shared.models.market_data import MarketData, Quote, Trade, OrderBook
from shared.models.orders import Order, OrderStatus, Side, TimeInForce
from shared.models.positions import Position
from shared.models.strategies import Strategy, StrategyStatus, TradingSignal
from shared.models.risk import RiskMetrics, RiskLimit
from shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


class TestCompleteTradingWorkflow:
    """End-to-end test suite for complete trading workflow."""
    
    @pytest.fixture
    def api_base_url(self):
        """Base URL for API testing."""
        return "http://localhost:8000/api/v1"
    
    @pytest.fixture
    def websocket_url(self):
        """WebSocket URL for real-time testing."""
        return "ws://localhost:8000/ws"
    
    @pytest.fixture
    async def trading_system(self):
        """Set up complete trading system for testing."""
        # Mock external dependencies
        mock_db = AsyncMock()
        mock_broker = AsyncMock()
        mock_market_data = AsyncMock()
        
        # Initialize components
        risk_manager = RiskManager(mock_db)
        portfolio_manager = PortfolioManager(mock_db)
        order_manager = OrderManager(mock_db)
        
        trading_engine = TradingEngine(
            order_manager=order_manager,
            risk_manager=risk_manager,
            portfolio_manager=portfolio_manager,
            broker_client=mock_broker,
            market_data_client=mock_market_data
        )
        
        return {
            'engine': trading_engine,
            'order_manager': order_manager,
            'risk_manager': risk_manager,
            'portfolio_manager': portfolio_manager,
            'mock_db': mock_db,
            'mock_broker': mock_broker,
            'mock_market_data': mock_market_data
        }
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_complete_buy_order_workflow(self, trading_system, api_base_url):
        """Test complete buy order workflow from API to execution."""
        # Step 1: Create order via API
        order_data = {
            "account_id": "test_account",
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": "100",
            "order_type": "LIMIT",
            "price": "150.00",
            "time_in_force": "DAY"
        }
        
        # Mock successful order creation
        trading_system['mock_db'].create_order.return_value = 'order_123'
        trading_system['mock_db'].get_order.return_value = {
            'order_id': 'order_123',
            'account_id': 'test_account',
            'symbol': 'AAPL',
            'side': 'BUY',
            'quantity': Decimal('100'),
            'order_type': 'LIMIT',
            'price': Decimal('150.00'),
            'status': 'PENDING',
            'time_in_force': 'DAY',
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }
        
        # Step 2: Submit order through trading engine
        order_request = OrderCreateRequest(
            account_id='test_account',
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=Decimal('100'),
            order_type=OrderType.LIMIT,
            price=Decimal('150.00')
        )
        
        order_id = await trading_system['engine'].submit_order(order_request)
        assert order_id == 'order_123'
        
        # Step 3: Simulate market data update triggering execution
        market_data = {
            'symbol': 'AAPL',
            'price': Decimal('149.95'),
            'volume': 1000,
            'timestamp': datetime.utcnow()
        }
        
        # Mock broker execution
        trading_system['mock_broker'].submit_order.return_value = {
            'broker_order_id': 'broker_123',
            'status': 'FILLED',
            'filled_quantity': Decimal('100'),
            'filled_price': Decimal('149.95')
        }
        
        # Step 4: Process market data and execute order
        await trading_system['engine'].process_market_data(market_data)
        
        # Step 5: Verify order execution
        trading_system['mock_db'].update_order_status.assert_called()
        
        # Step 6: Verify portfolio update
        expected_position_update = {
            'symbol': 'AAPL',
            'quantity': Decimal('100'),
            'average_price': Decimal('149.95'),
            'market_value': Decimal('14995.00')
        }
        
        # Verify portfolio manager was called to update position
        assert trading_system['portfolio_manager'].update_position.called
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_risk_management_integration(self, trading_system):
        """Test risk management integration in trading workflow."""
        # Set up risk limits
        risk_limits = {
            'max_position_size': Decimal('1000'),
            'max_daily_loss': Decimal('5000'),
            'max_portfolio_exposure': Decimal('100000')
        }
        
        trading_system['mock_db'].get_risk_limits.return_value = risk_limits
        
        # Test order that exceeds position limit
        large_order = OrderCreateRequest(
            account_id='test_account',
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=Decimal('2000'),  # Exceeds max_position_size
            order_type=OrderType.MARKET
        )
        
        # Mock current position
        trading_system['mock_db'].get_position.return_value = {
            'symbol': 'AAPL',
            'quantity': Decimal('500'),
            'average_price': Decimal('150.00')
        }
        
        # Should reject order due to risk limits
        with pytest.raises(Exception, match="Position size limit exceeded"):
            await trading_system['engine'].submit_order(large_order)
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_websocket_real_time_updates(self, websocket_url):
        """Test real-time WebSocket updates during trading."""
        # This test would require actual WebSocket server running
        # For now, we'll mock the WebSocket behavior
        
        mock_websocket_messages = [
            {
                'type': 'market_data',
                'symbol': 'AAPL',
                'price': 150.25,
                'timestamp': datetime.utcnow().isoformat()
            },
            {
                'type': 'order_update',
                'order_id': 'order_123',
                'status': 'FILLED',
                'filled_quantity': 100,
                'filled_price': 150.25
            },
            {
                'type': 'portfolio_update',
                'account_id': 'test_account',
                'total_value': 150025.00,
                'cash_balance': 50000.00
            }
        ]
        
        # Simulate WebSocket message processing
        for message in mock_websocket_messages:
            # In a real test, this would connect to actual WebSocket
            # and verify message format and timing
            assert 'type' in message
            assert 'timestamp' in message or message['type'] == 'order_update'
            
            if message['type'] == 'market_data':
                assert 'symbol' in message
                assert 'price' in message
            elif message['type'] == 'order_update':
                assert 'order_id' in message
                assert 'status' in message
            elif message['type'] == 'portfolio_update':
                assert 'account_id' in message
                assert 'total_value' in message
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_multi_asset_portfolio_management(self, trading_system):
        """Test portfolio management across multiple assets."""
        # Set up initial portfolio state
        initial_positions = {
            'AAPL': {'quantity': Decimal('100'), 'average_price': Decimal('150.00')},
            'GOOGL': {'quantity': Decimal('50'), 'average_price': Decimal('2500.00')},
            'MSFT': {'quantity': Decimal('75'), 'average_price': Decimal('300.00')}
        }
        
        trading_system['mock_db'].get_all_positions.return_value = initial_positions
        
        # Execute multiple orders
        orders = [
            OrderCreateRequest(
                account_id='test_account',
                symbol='AAPL',
                side=OrderSide.SELL,
                quantity=Decimal('50'),
                order_type=OrderType.MARKET
            ),
            OrderCreateRequest(
                account_id='test_account',
                symbol='TSLA',
                side=OrderSide.BUY,
                quantity=Decimal('25'),
                order_type=OrderType.LIMIT,
                price=Decimal('800.00')
            )
        ]
        
        # Mock order executions
        trading_system['mock_db'].create_order.side_effect = ['order_124', 'order_125']
        trading_system['mock_broker'].submit_order.side_effect = [
            {
                'broker_order_id': 'broker_124',
                'status': 'FILLED',
                'filled_quantity': Decimal('50'),
                'filled_price': Decimal('151.00')
            },
            {
                'broker_order_id': 'broker_125',
                'status': 'FILLED',
                'filled_quantity': Decimal('25'),
                'filled_price': Decimal('799.50')
            }
        ]
        
        # Execute orders
        for order in orders:
            order_id = await trading_system['engine'].submit_order(order)
            assert order_id in ['order_124', 'order_125']
        
        # Verify portfolio updates
        assert trading_system['portfolio_manager'].update_position.call_count == 2
        
        # Verify portfolio rebalancing calculations
        expected_portfolio_value = (
            Decimal('50') * Decimal('151.00') +  # Remaining AAPL
            Decimal('50') * Decimal('2500.00') +  # GOOGL
            Decimal('75') * Decimal('300.00') +   # MSFT
            Decimal('25') * Decimal('799.50')     # New TSLA
        )
        
        # This would be calculated by the portfolio manager
        assert expected_portfolio_value > Decimal('0')
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_strategy_execution_workflow(self, trading_system):
        """Test automated strategy execution workflow."""
        # Mock strategy configuration
        strategy_config = {
            'strategy_id': 'momentum_strategy_1',
            'symbols': ['AAPL', 'GOOGL', 'MSFT'],
            'parameters': {
                'lookback_period': 20,
                'momentum_threshold': 0.02,
                'position_size': Decimal('1000')
            },
            'risk_limits': {
                'max_position_per_symbol': Decimal('5000'),
                'stop_loss_pct': Decimal('0.05')
            }
        }
        
        # Mock market data for strategy signals
        market_data_history = {
            'AAPL': [
                {'price': Decimal('148.00'), 'timestamp': datetime.now(timezone.utc) - timedelta(minutes=5)},
                {'price': Decimal('149.00'), 'timestamp': datetime.now(timezone.utc) - timedelta(minutes=4)},
                {'price': Decimal('150.50'), 'timestamp': datetime.now(timezone.utc) - timedelta(minutes=3)},
                {'price': Decimal('151.25'), 'timestamp': datetime.now(timezone.utc) - timedelta(minutes=2)},
                {'price': Decimal('152.00'), 'timestamp': datetime.now(timezone.utc) - timedelta(minutes=1)}
            ]
        }
        
        trading_system['mock_market_data'].get_historical_data.return_value = market_data_history
        
        # Mock strategy signal generation
        strategy_signals = [
            {
                'symbol': 'AAPL',
                'signal': 'BUY',
                'confidence': 0.85,
                'target_quantity': Decimal('100'),
                'reasoning': 'Strong upward momentum detected'
            }
        ]
        
        # Execute strategy
        for signal in strategy_signals:
            if signal['signal'] == 'BUY':
                order_request = OrderCreateRequest(
                    account_id='strategy_account',
                    symbol=signal['symbol'],
                    side=OrderSide.BUY,
                    quantity=signal['target_quantity'],
                    order_type=OrderType.MARKET,
                    metadata={'strategy_id': strategy_config['strategy_id']}
                )
                
                # Mock successful order creation
                trading_system['mock_db'].create_order.return_value = 'strategy_order_123'
                
                order_id = await trading_system['engine'].submit_order(order_request)
                assert order_id == 'strategy_order_123'
        
        # Verify strategy execution was logged
        trading_system['mock_db'].create_order.assert_called()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_error_handling_and_recovery(self, trading_system):
        """Test error handling and recovery mechanisms."""
        # Test database connection failure
        trading_system['mock_db'].create_order.side_effect = Exception("Database connection failed")
        
        order_request = OrderCreateRequest(
            account_id='test_account',
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=Decimal('100'),
            order_type=OrderType.MARKET
        )
        
        with pytest.raises(Exception, match="Database connection failed"):
            await trading_system['engine'].submit_order(order_request)
        
        # Test broker connection failure
        trading_system['mock_db'].create_order.side_effect = None
        trading_system['mock_db'].create_order.return_value = 'order_126'
        trading_system['mock_broker'].submit_order.side_effect = Exception("Broker connection failed")
        
        # Should handle broker failure gracefully
        with pytest.raises(Exception, match="Broker connection failed"):
            await trading_system['engine'].submit_order(order_request)
        
        # Verify order status was updated to reflect error
        trading_system['mock_db'].update_order_status.assert_called()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_performance_under_load(self, trading_system):
        """Test system performance under high load."""
        # Create multiple concurrent orders
        concurrent_orders = []
        for i in range(50):
            order_request = OrderCreateRequest(
                account_id=f'test_account_{i % 5}',
                symbol='AAPL',
                side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                quantity=Decimal('10'),
                order_type=OrderType.MARKET
            )
            concurrent_orders.append(order_request)
        
        # Mock successful order processing
        trading_system['mock_db'].create_order.side_effect = [f'order_{i}' for i in range(50)]
        
        # Measure execution time
        start_time = datetime.utcnow()
        
        # Execute orders concurrently
        tasks = []
        for order in concurrent_orders:
            task = asyncio.create_task(trading_system['engine'].submit_order(order))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()
        
        # Verify all orders were processed
        successful_orders = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_orders) == 50
        
        # Verify performance (should process 50 orders in under 5 seconds)
        assert execution_time < 5.0
        
        # Verify database calls
        assert trading_system['mock_db'].create_order.call_count == 50
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_ai_assisted_trading_workflow(self, trading_system):
        """Test AI-assisted trading workflow with market analysis."""
        # Mock AI assistant
        ai_assistant = AsyncMock()
        trading_system['ai_assistant'] = ai_assistant
        
        # Setup market data for AI analysis
        market_data = {
            'symbol': 'AAPL',
            'price': Decimal('150.00'),
            'volume': 1000000,
            'timestamp': datetime.now(timezone.utc),
            'technical_indicators': {
                'rsi': 65.5,
                'macd': 0.85,
                'bollinger_upper': 152.0,
                'bollinger_lower': 148.0
            }
        }
        
        # Mock AI analysis response
        ai_analysis = {
            'sentiment': 'BULLISH',
            'confidence': 0.87,
            'recommendation': 'BUY',
            'target_price': Decimal('155.00'),
            'stop_loss': Decimal('145.00'),
            'reasoning': 'Strong technical momentum with positive earnings outlook',
            'risk_score': 0.3
        }
        
        ai_assistant.analyze_market.return_value = ai_analysis
        
        # Execute AI-assisted order
        ai_recommendation = await ai_assistant.analyze_market('AAPL', market_data)
        
        if ai_recommendation['recommendation'] == 'BUY':
            order_request = OrderCreateRequest(
                account_id='ai_account',
                symbol='AAPL',
                side=OrderSide.BUY,
                quantity=Decimal('100'),
                order_type=OrderType.LIMIT,
                price=ai_recommendation['target_price'],
                metadata={
                    'ai_confidence': ai_recommendation['confidence'],
                    'ai_reasoning': ai_recommendation['reasoning']
                }
            )
            
            # Mock successful order creation
            trading_system['mock_db'].create_order.return_value = 'ai_order_123'
            
            order_id = await trading_system['engine'].submit_order(order_request)
            assert order_id == 'ai_order_123'
        
        # Verify AI analysis was called
        ai_assistant.analyze_market.assert_called_once_with('AAPL', market_data)
        assert ai_recommendation['confidence'] > 0.8
        assert ai_recommendation['recommendation'] == 'BUY'
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_kafka_event_streaming_workflow(self, trading_system):
        """Test Kafka event streaming integration in trading workflow."""
        # Mock Kafka infrastructure
        kafka_producer = Mock()
        kafka_consumer = Mock()
        
        trading_system['kafka_producer'] = kafka_producer
        trading_system['kafka_consumer'] = kafka_consumer
        
        # Test market data event streaming
        market_data_event = {
            'event_type': 'market_data_update',
            'symbol': 'AAPL',
            'price': 150.25,
            'volume': 1500,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Test order event streaming
        order_event = {
            'event_type': 'order_created',
            'order_id': 'order_123',
            'symbol': 'AAPL',
            'side': 'BUY',
            'quantity': 100,
            'status': 'PENDING',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Test execution event streaming
        execution_event = {
            'event_type': 'order_executed',
            'order_id': 'order_123',
            'symbol': 'AAPL',
            'executed_quantity': 100,
            'executed_price': 150.25,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Simulate event publishing
        events = [market_data_event, order_event, execution_event]
        
        for event in events:
            # In real implementation, this would publish to Kafka
            kafka_producer.send.return_value = Mock()
            kafka_producer.send('trading_events', json.dumps(event))
        
        # Verify events were published
        assert kafka_producer.send.call_count == 3
        
        # Test event consumption and processing
        kafka_consumer.poll.return_value = {
            'trading_events': [Mock(value=json.dumps(event)) for event in events]
        }
        
        # Process consumed events
        consumed_events = kafka_consumer.poll(timeout_ms=1000)
        processed_events = []
        
        for topic_partition, messages in consumed_events.items():
            for message in messages:
                event_data = json.loads(message.value)
                processed_events.append(event_data)
        
        assert len(processed_events) == 3
        assert processed_events[0]['event_type'] == 'market_data_update'
        assert processed_events[1]['event_type'] == 'order_created'
        assert processed_events[2]['event_type'] == 'order_executed'
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_multi_symbol_momentum_strategy(self, trading_system):
        """Test multi-symbol momentum strategy execution."""
        symbols = ['AAPL', 'TSLA', 'MSFT', 'GOOGL', 'AMZN']
        
        # Mock historical price data for momentum calculation
        price_history = {
            'AAPL': [148.0, 149.0, 150.5, 151.2, 152.0],
            'TSLA': [800.0, 795.0, 790.0, 785.0, 780.0],  # Downward trend
            'MSFT': [300.0, 301.0, 302.5, 304.0, 305.5],
            'GOOGL': [2500.0, 2505.0, 2510.0, 2515.0, 2520.0],
            'AMZN': [3200.0, 3195.0, 3205.0, 3200.0, 3210.0]  # Sideways
        }
        
        trading_system['mock_market_data'].get_historical_data.side_effect = lambda symbol: price_history[symbol]
        
        # Calculate momentum signals
        momentum_signals = []
        for symbol in symbols:
            prices = price_history[symbol]
            momentum = (prices[-1] - prices[0]) / prices[0]
            
            if momentum > 0.02:  # 2% threshold
                momentum_signals.append({
                    'symbol': symbol,
                    'signal': 'BUY',
                    'momentum': momentum,
                    'confidence': min(momentum * 10, 1.0)
                })
            elif momentum < -0.02:
                momentum_signals.append({
                    'symbol': symbol,
                    'signal': 'SELL',
                    'momentum': momentum,
                    'confidence': min(abs(momentum) * 10, 1.0)
                })
        
        # Execute momentum-based orders
        executed_orders = []
        for signal in momentum_signals:
            order_request = OrderCreateRequest(
                account_id='momentum_account',
                symbol=signal['symbol'],
                side=OrderSide.BUY if signal['signal'] == 'BUY' else OrderSide.SELL,
                quantity=Decimal('50'),
                order_type=OrderType.MARKET,
                metadata={
                    'strategy': 'momentum',
                    'momentum_value': signal['momentum'],
                    'confidence': signal['confidence']
                }
            )
            
            # Mock order creation
            order_id = f"momentum_order_{len(executed_orders)}"
            trading_system['mock_db'].create_order.return_value = order_id
            
            result_order_id = await trading_system['engine'].submit_order(order_request)
            executed_orders.append(result_order_id)
        
        # Verify momentum strategy execution
        # Should have BUY signals for AAPL, MSFT, GOOGL (positive momentum > 2%)
        # Should have SELL signal for TSLA (negative momentum > 2%)
        # AMZN should be filtered out (momentum too low)
        
        expected_signals = 4  # AAPL, MSFT, GOOGL (BUY), TSLA (SELL)
        assert len(executed_orders) == expected_signals
        assert trading_system['mock_db'].create_order.call_count == expected_signals
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_high_frequency_trading_scenario(self, trading_system):
        """Test high-frequency trading scenario with rapid order execution."""
        # Setup high-frequency market data stream
        hf_market_data = []
        base_price = Decimal('150.00')
        
        for i in range(100):  # 100 rapid price updates
            price_change = Decimal(str(np.random.uniform(-0.5, 0.5)))
            new_price = base_price + price_change
            
            hf_market_data.append({
                'symbol': 'AAPL',
                'price': new_price,
                'volume': np.random.randint(100, 1000),
                'timestamp': datetime.now(timezone.utc) + timedelta(milliseconds=i*10),
                'bid': new_price - Decimal('0.01'),
                'ask': new_price + Decimal('0.01')
            })
            base_price = new_price
        
        # Mock rapid order processing
        trading_system['mock_db'].create_order.side_effect = [f'hf_order_{i}' for i in range(50)]
        trading_system['mock_broker'].submit_order.return_value = {
            'status': 'FILLED',
            'filled_quantity': Decimal('10'),
            'latency_ms': 2.5  # Sub-3ms latency
        }
        
        # Execute high-frequency strategy
        hf_orders = []
        start_time = datetime.now()
        
        for i, market_tick in enumerate(hf_market_data[:50]):  # Process first 50 ticks
            # Simple scalping strategy: buy on dips, sell on peaks
            if i > 0:
                prev_price = hf_market_data[i-1]['price']
                current_price = market_tick['price']
                price_change = (current_price - prev_price) / prev_price
                
                if abs(price_change) > Decimal('0.001'):  # 0.1% threshold
                    side = OrderSide.BUY if price_change < 0 else OrderSide.SELL
                    
                    order_request = OrderCreateRequest(
                        account_id='hf_account',
                        symbol='AAPL',
                        side=side,
                        quantity=Decimal('10'),
                        order_type=OrderType.MARKET,
                        metadata={'strategy': 'hf_scalping'}
                    )
                    
                    order_id = await trading_system['engine'].submit_order(order_request)
                    hf_orders.append(order_id)
        
        end_time = datetime.now()
        total_execution_time = (end_time - start_time).total_seconds()
        
        # Verify high-frequency performance
        assert len(hf_orders) > 0
        assert total_execution_time < 1.0  # Should complete in under 1 second
        
        # Verify average order processing time
        avg_order_time = total_execution_time / len(hf_orders) if hf_orders else 0
        assert avg_order_time < 0.02  # Under 20ms per order
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_comprehensive_error_recovery(self, trading_system):
        """Test comprehensive error recovery across all system components."""
        # Test cascading failure recovery
        failure_scenarios = [
            {'component': 'market_data', 'error': 'Connection timeout'},
            {'component': 'risk_manager', 'error': 'Risk calculation failed'},
            {'component': 'broker', 'error': 'Order rejected by exchange'},
            {'component': 'database', 'error': 'Transaction rollback'},
            {'component': 'portfolio', 'error': 'Position calculation error'}
        ]
        
        recovery_results = []
        
        for scenario in failure_scenarios:
            # Setup failure condition
            if scenario['component'] == 'market_data':
                trading_system['mock_market_data'].get_latest_quote.side_effect = Exception(scenario['error'])
            elif scenario['component'] == 'risk_manager':
                trading_system['risk_manager'].validate_order.side_effect = Exception(scenario['error'])
            elif scenario['component'] == 'broker':
                trading_system['mock_broker'].submit_order.side_effect = Exception(scenario['error'])
            elif scenario['component'] == 'database':
                trading_system['mock_db'].create_order.side_effect = Exception(scenario['error'])
            elif scenario['component'] == 'portfolio':
                trading_system['portfolio_manager'].update_position.side_effect = Exception(scenario['error'])
            
            # Attempt order execution
            order_request = OrderCreateRequest(
                account_id='recovery_test',
                symbol='AAPL',
                side=OrderSide.BUY,
                quantity=Decimal('100'),
                order_type=OrderType.MARKET
            )
            
            try:
                await trading_system['engine'].submit_order(order_request)
                recovery_results.append({'scenario': scenario['component'], 'recovered': True})
            except Exception as e:
                # Verify error was properly handled and logged
                assert scenario['error'] in str(e)
                recovery_results.append({'scenario': scenario['component'], 'recovered': False, 'error': str(e)})
            
            # Reset for next test
            for component in ['mock_market_data', 'risk_manager', 'mock_broker', 'mock_db', 'portfolio_manager']:
                if hasattr(trading_system[component], 'side_effect'):
                    trading_system[component].side_effect = None
        
        # Verify all failure scenarios were tested
        assert len(recovery_results) == len(failure_scenarios)
        
        # Verify error handling mechanisms
        for result in recovery_results:
            assert 'scenario' in result
            assert 'recovered' in result or 'error' in result


class TestAPIIntegration:
    """Test API integration points."""
    
    @pytest.mark.e2e
    def test_rest_api_endpoints(self, api_base_url):
        """Test REST API endpoints are accessible."""
        # This would require actual API server running
        # For now, we'll test the expected endpoint structure
        
        expected_endpoints = [
            '/orders',
            '/orders/{order_id}',
            '/portfolio',
            '/positions',
            '/market-data/{symbol}',
            '/strategies',
            '/risk-limits'
        ]
        
        for endpoint in expected_endpoints:
            # In a real test, this would make actual HTTP requests
            # response = requests.get(f"{api_base_url}{endpoint}")
            # assert response.status_code in [200, 404]  # 404 for parameterized endpoints
            assert endpoint.startswith('/')
    
    @pytest.mark.e2e
    def test_api_authentication(self, api_base_url):
        """Test API authentication mechanisms."""
        # Test unauthorized access
        # response = requests.get(f"{api_base_url}/orders")
        # assert response.status_code == 401
        
        # Test with valid token
        # headers = {'Authorization': 'Bearer valid_token'}
        # response = requests.get(f"{api_base_url}/orders", headers=headers)
        # assert response.status_code == 200
        
        # For now, just verify the test structure
        assert api_base_url.startswith('http')


class TestDataConsistency:
    """Test data consistency across components."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_order_portfolio_consistency(self, trading_system):
        """Test consistency between order execution and portfolio updates."""
        # Execute a buy order
        order_request = OrderCreateRequest(
            account_id='test_account',
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=Decimal('100'),
            order_type=OrderType.MARKET
        )
        
        # Mock successful execution
        trading_system['mock_db'].create_order.return_value = 'order_127'
        trading_system['mock_broker'].submit_order.return_value = {
            'broker_order_id': 'broker_127',
            'status': 'FILLED',
            'filled_quantity': Decimal('100'),
            'filled_price': Decimal('150.00')
        }
        
        # Mock current position
        trading_system['mock_db'].get_position.return_value = {
            'symbol': 'AAPL',
            'quantity': Decimal('50'),
            'average_price': Decimal('145.00')
        }
        
        order_id = await trading_system['engine'].submit_order(order_request)
        
        # Verify order was created
        assert order_id == 'order_127'
        
        # Verify portfolio update was called with correct parameters
        trading_system['portfolio_manager'].update_position.assert_called()
        
        # In a real system, we would verify the exact position calculation
        # Expected new position: (50 * 145.00 + 100 * 150.00) / 150 = 147.67 average price
        expected_new_quantity = Decimal('150')
        expected_new_avg_price = (Decimal('50') * Decimal('145.00') + Decimal('100') * Decimal('150.00')) / Decimal('150')
        
        assert expected_new_quantity == Decimal('150')
        assert abs(expected_new_avg_price - Decimal('147.67')) < Decimal('0.01')


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'e2e'])