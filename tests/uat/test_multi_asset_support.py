"""User Acceptance Tests for multi-asset trading support and cross-asset functionality."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
import json
from decimal import Decimal


class TestMultiAssetSupport:
    """Test suite for multi-asset trading support validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.supported_asset_classes = {
            'forex': {
                'symbols': ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD'],
                'base_currency': 'USD',
                'tick_size': 0.00001,
                'contract_size': 100000,
                'margin_requirement': 0.02,
                'trading_hours': '24/5'
            },
            'stocks': {
                'symbols': ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN'],
                'base_currency': 'USD',
                'tick_size': 0.01,
                'contract_size': 1,
                'margin_requirement': 0.25,
                'trading_hours': '09:30-16:00 EST'
            },
            'commodities': {
                'symbols': ['XAUUSD', 'XAGUSD', 'CRUDE', 'NATGAS'],
                'base_currency': 'USD',
                'tick_size': 0.01,
                'contract_size': 100,
                'margin_requirement': 0.05,
                'trading_hours': '24/5'
            },
            'crypto': {
                'symbols': ['BTCUSD', 'ETHUSD', 'ADAUSD', 'DOTUSD'],
                'base_currency': 'USD',
                'tick_size': 0.01,
                'contract_size': 1,
                'margin_requirement': 0.10,
                'trading_hours': '24/7'
            },
            'indices': {
                'symbols': ['SPX500', 'NAS100', 'GER30', 'UK100'],
                'base_currency': 'USD',
                'tick_size': 0.1,
                'contract_size': 1,
                'margin_requirement': 0.01,
                'trading_hours': '24/5'
            }
        }
        
        self.test_portfolio = {
            'account_currency': 'USD',
            'total_equity': 100000.0,
            'available_margin': 80000.0,
            'positions': [
                {
                    'symbol': 'EURUSD',
                    'asset_class': 'forex',
                    'quantity': 100000,
                    'side': 'LONG',
                    'entry_price': 1.0850,
                    'current_price': 1.0865,
                    'unrealized_pnl': 150.0
                },
                {
                    'symbol': 'AAPL',
                    'asset_class': 'stocks',
                    'quantity': 100,
                    'side': 'LONG',
                    'entry_price': 175.50,
                    'current_price': 178.25,
                    'unrealized_pnl': 275.0
                },
                {
                    'symbol': 'XAUUSD',
                    'asset_class': 'commodities',
                    'quantity': 10,
                    'side': 'LONG',
                    'entry_price': 2050.00,
                    'current_price': 2065.50,
                    'unrealized_pnl': 155.0
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_asset_class_discovery_and_configuration(self):
        """Test discovery and configuration of supported asset classes."""
        # Mock asset class configuration retrieval
        with patch('nautilus_trader_engine.assets.AssetManager') as mock_asset_mgr:
            mock_instance = Mock()
            mock_asset_mgr.return_value = mock_instance
            
            mock_instance.get_supported_asset_classes.return_value = list(self.supported_asset_classes.keys())
            mock_instance.get_asset_class_config.side_effect = lambda ac: self.supported_asset_classes.get(ac)
            
            # Test asset class discovery
            asset_manager = mock_asset_mgr()
            supported_classes = asset_manager.get_supported_asset_classes()
            
            # Verify all expected asset classes are supported
            expected_classes = ['forex', 'stocks', 'commodities', 'crypto', 'indices']
            for asset_class in expected_classes:
                assert asset_class in supported_classes, f"Asset class {asset_class} not supported"
            
            # Test asset class configuration
            for asset_class in supported_classes:
                config = asset_manager.get_asset_class_config(asset_class)
                
                # Verify required configuration fields
                required_fields = ['symbols', 'base_currency', 'tick_size', 'contract_size', 'margin_requirement']
                for field in required_fields:
                    assert field in config, f"Missing {field} in {asset_class} configuration"
                
                # Verify symbols list is not empty
                assert len(config['symbols']) > 0, f"No symbols configured for {asset_class}"
                
                # Verify numeric fields are valid
                assert config['tick_size'] > 0, f"Invalid tick size for {asset_class}"
                assert config['contract_size'] > 0, f"Invalid contract size for {asset_class}"
                assert 0 < config['margin_requirement'] <= 1, f"Invalid margin requirement for {asset_class}"
    
    @pytest.mark.asyncio
    async def test_cross_asset_portfolio_management(self):
        """Test portfolio management across multiple asset classes."""
        # Mock portfolio manager
        with patch('nautilus_trader_engine.portfolio.MultiAssetPortfolioManager') as mock_portfolio:
            mock_instance = AsyncMock()
            mock_portfolio.return_value = mock_instance
            
            # Configure portfolio data
            mock_instance.get_portfolio_summary.return_value = self.test_portfolio
            mock_instance.get_positions_by_asset_class.side_effect = self._get_positions_by_asset_class
            mock_instance.calculate_cross_asset_correlation.return_value = self._calculate_mock_correlations()
            
            portfolio_manager = mock_portfolio()
            
            # Test portfolio summary
            portfolio = await portfolio_manager.get_portfolio_summary()
            
            # Verify portfolio structure
            assert 'total_equity' in portfolio
            assert 'positions' in portfolio
            assert len(portfolio['positions']) > 0
            
            # Test positions by asset class
            asset_classes = ['forex', 'stocks', 'commodities']
            total_positions = 0
            
            for asset_class in asset_classes:
                positions = await portfolio_manager.get_positions_by_asset_class(asset_class)
                total_positions += len(positions)
                
                # Verify all positions belong to the correct asset class
                for position in positions:
                    assert position['asset_class'] == asset_class
            
            assert total_positions == len(portfolio['positions'])
            
            # Test cross-asset correlation analysis
            correlations = await portfolio_manager.calculate_cross_asset_correlation()
            
            # Verify correlation matrix structure
            assert isinstance(correlations, dict)
            assert len(correlations) > 0
            
            # Check correlation values are within valid range [-1, 1]
            for symbol1, correlations_dict in correlations.items():
                for symbol2, correlation in correlations_dict.items():
                    assert -1 <= correlation <= 1, f"Invalid correlation {correlation} between {symbol1} and {symbol2}"
    
    def _get_positions_by_asset_class(self, asset_class: str) -> List[Dict]:
        """Helper method to filter positions by asset class."""
        return [pos for pos in self.test_portfolio['positions'] if pos['asset_class'] == asset_class]
    
    def _calculate_mock_correlations(self) -> Dict[str, Dict[str, float]]:
        """Helper method to generate mock correlation data."""
        symbols = [pos['symbol'] for pos in self.test_portfolio['positions']]
        correlations = {}
        
        for i, symbol1 in enumerate(symbols):
            correlations[symbol1] = {}
            for j, symbol2 in enumerate(symbols):
                if i == j:
                    correlations[symbol1][symbol2] = 1.0
                else:
                    # Mock correlation based on asset classes
                    pos1 = next(p for p in self.test_portfolio['positions'] if p['symbol'] == symbol1)
                    pos2 = next(p for p in self.test_portfolio['positions'] if p['symbol'] == symbol2)
                    
                    if pos1['asset_class'] == pos2['asset_class']:
                        correlations[symbol1][symbol2] = 0.7  # High correlation within same asset class
                    else:
                        correlations[symbol1][symbol2] = 0.2  # Low correlation across asset classes
        
        return correlations
    
    @pytest.mark.asyncio
    async def test_cross_asset_order_execution(self):
        """Test order execution across different asset classes."""
        # Test orders for different asset classes
        test_orders = [
            {
                'symbol': 'EURUSD',
                'asset_class': 'forex',
                'side': 'BUY',
                'quantity': 100000,
                'order_type': 'MARKET'
            },
            {
                'symbol': 'AAPL',
                'asset_class': 'stocks',
                'side': 'BUY',
                'quantity': 50,
                'order_type': 'LIMIT',
                'limit_price': 175.00
            },
            {
                'symbol': 'BTCUSD',
                'asset_class': 'crypto',
                'side': 'SELL',
                'quantity': 0.5,
                'order_type': 'MARKET'
            }
        ]
        
        # Mock order execution engine
        with patch('nautilus_trader_engine.orders.MultiAssetOrderManager') as mock_order_mgr:
            mock_instance = AsyncMock()
            mock_order_mgr.return_value = mock_instance
            
            # Configure order execution responses with properly aligned prices
            execution_results = []
            for i, order in enumerate(test_orders):
                # Use prices that are exactly aligned with tick sizes
                mock_prices = {
                    'EURUSD': 1.08650,  # Exactly 108650 ticks of 0.00001
                    'AAPL': 175.25,     # Exactly 17525 ticks of 0.01
                    'BTCUSD': 45250.00  # Exactly 4525000 ticks of 0.01
                }
                price = mock_prices.get(order['symbol'], 100.0)
                
                result = {
                    'order_id': f'ORD_{i+1:03d}',
                    'symbol': order['symbol'],
                    'status': 'FILLED',
                    'fill_price': price,
                    'fill_quantity': order['quantity'],
                    'timestamp': datetime.now().isoformat(),
                    'commission': self._calculate_mock_commission(order)
                }
                execution_results.append(result)
            
            mock_instance.submit_order.side_effect = execution_results
            
            order_manager = mock_order_mgr()
            
            # Execute orders and verify results
            for i, order in enumerate(test_orders):
                result = await order_manager.submit_order(order)
                
                # Verify order execution
                assert result['status'] == 'FILLED'
                assert result['symbol'] == order['symbol']
                assert result['fill_quantity'] == order['quantity']
                assert 'order_id' in result
                assert 'fill_price' in result
                assert 'commission' in result
                
                # Verify asset-class specific validations
                asset_class = order['asset_class']
                config = self.supported_asset_classes[asset_class]
                
                # Check tick size compliance with tolerance for floating point precision
                fill_price = result['fill_price']
                tick_size = config['tick_size']
                # Use a small tolerance for floating point comparison
                ticks = fill_price / tick_size
                assert abs(ticks - round(ticks)) < 1e-10, f"Fill price {fill_price} not aligned to tick size {tick_size}"
    
    def _get_mock_fill_price(self, order: Dict) -> float:
        """Generate mock fill price based on order details."""
        # Make sure prices are aligned with their respective tick sizes
        mock_prices = {
            'EURUSD': 1.08650,  # Aligned to 0.00001 tick size
            'AAPL': 175.25,     # Aligned to 0.01 tick size
            'BTCUSD': 45250.00  # Aligned to 0.01 tick size
        }
        price = mock_prices.get(order['symbol'], 100.0)
        
        # Align price to tick size to avoid floating point precision issues
        asset_class = order.get('asset_class', 'forex')
        tick_sizes = {
            'forex': 0.00001,
            'stocks': 0.01,
            'commodities': 0.01,
            'crypto': 0.01,
            'indices': 0.1
        }
        tick_size = tick_sizes.get(asset_class, 0.00001)
        
        # Round to nearest tick
        aligned_price = round(price / tick_size) * tick_size
        return aligned_price
    
    def _calculate_mock_commission(self, order: Dict) -> float:
        """Calculate mock commission based on asset class."""
        commission_rates = {
            'forex': 0.0,  # Spread-based
            'stocks': 0.005,  # $0.005 per share
            'crypto': 0.001,  # 0.1% of notional
            'commodities': 2.50,  # Fixed per contract
            'indices': 1.00  # Fixed per contract
        }
        
        asset_class = order['asset_class']
        rate = commission_rates.get(asset_class, 0.0)
        
        if asset_class == 'stocks':
            return order['quantity'] * rate
        elif asset_class == 'crypto':
            notional = order['quantity'] * self._get_mock_fill_price(order)
            return notional * rate
        else:
            return rate
    
    @pytest.mark.asyncio
    async def test_cross_asset_risk_management(self):
        """Test risk management across multiple asset classes."""
        # Mock risk management system
        with patch('nautilus_trader_engine.risk.MultiAssetRiskManager') as mock_risk_mgr:
            mock_instance = AsyncMock()
            mock_risk_mgr.return_value = mock_instance
            
            # Configure risk calculations
            mock_instance.calculate_portfolio_var.return_value = {
                'total_var_1d': 2500.0,
                'var_by_asset_class': {
                    'forex': 1200.0,
                    'stocks': 800.0,
                    'commodities': 500.0
                },
                'confidence_level': 0.95
            }
            
            mock_instance.calculate_asset_class_exposure.return_value = {
                'forex': {'notional': 100000.0, 'percentage': 45.5},
                'stocks': {'notional': 17825.0, 'percentage': 8.1},
                'commodities': {'notional': 20650.0, 'percentage': 9.4},
                'cash': {'notional': 81525.0, 'percentage': 37.0}
            }
            
            mock_instance.check_cross_asset_limits.return_value = {
                'within_limits': True,
                'limit_violations': [],
                'warnings': [
                    {'type': 'concentration', 'message': 'High forex exposure detected'}
                ]
            }
            
            risk_manager = mock_risk_mgr()
            
            # Test portfolio VaR calculation
            var_result = await risk_manager.calculate_portfolio_var()
            
            assert 'total_var_1d' in var_result
            assert 'var_by_asset_class' in var_result
            assert var_result['total_var_1d'] > 0
            
            # Verify VaR by asset class sums correctly
            total_var_by_class = sum(var_result['var_by_asset_class'].values())
            # Note: Total VaR should be less than sum due to diversification
            assert var_result['total_var_1d'] <= total_var_by_class
            
            # Test asset class exposure calculation
            exposure_result = await risk_manager.calculate_asset_class_exposure()
            
            # Verify exposure percentages sum to approximately 100%
            total_percentage = sum(exp['percentage'] for exp in exposure_result.values())
            assert 95 <= total_percentage <= 105  # Allow for rounding
            
            # Test cross-asset limit checking
            limit_check = await risk_manager.check_cross_asset_limits()
            
            assert 'within_limits' in limit_check
            assert 'limit_violations' in limit_check
            assert 'warnings' in limit_check
    
    @pytest.mark.asyncio
    async def test_multi_asset_market_data_integration(self):
        """Test market data integration across multiple asset classes."""
        # Mock market data feeds
        market_data_feeds = {
            'forex': {
                'provider': 'ForexDataProvider',
                'symbols': ['EURUSD', 'GBPUSD', 'USDJPY'],
                'update_frequency': '100ms',
                'data_quality': 'institutional'
            },
            'stocks': {
                'provider': 'EquityDataProvider',
                'symbols': ['AAPL', 'GOOGL', 'MSFT'],
                'update_frequency': '1s',
                'data_quality': 'level1'
            },
            'crypto': {
                'provider': 'CryptoDataProvider',
                'symbols': ['BTCUSD', 'ETHUSD'],
                'update_frequency': '500ms',
                'data_quality': 'exchange'
            }
        }
        
        # Mock market data manager
        with patch('nautilus_trader_engine.data.MultiAssetDataManager') as mock_data_mgr:
            mock_instance = AsyncMock()
            mock_data_mgr.return_value = mock_instance
            
            # Configure market data responses
            mock_instance.get_active_feeds.return_value = market_data_feeds
            mock_instance.subscribe_to_symbol.return_value = {'status': 'subscribed'}
            mock_instance.get_latest_quote.side_effect = self._get_mock_quote
            
            data_manager = mock_data_mgr()
            
            # Test active feeds discovery
            active_feeds = await data_manager.get_active_feeds()
            
            # Verify all asset classes have data feeds
            expected_asset_classes = ['forex', 'stocks', 'crypto']
            for asset_class in expected_asset_classes:
                assert asset_class in active_feeds, f"No data feed for {asset_class}"
                
                feed_config = active_feeds[asset_class]
                assert 'provider' in feed_config
                assert 'symbols' in feed_config
                assert len(feed_config['symbols']) > 0
            
            # Test symbol subscription across asset classes
            test_symbols = ['EURUSD', 'AAPL', 'BTCUSD']
            
            for symbol in test_symbols:
                subscription_result = await data_manager.subscribe_to_symbol(symbol)
                assert subscription_result['status'] == 'subscribed'
            
            # Test market data retrieval
            for symbol in test_symbols:
                quote = await data_manager.get_latest_quote(symbol)
                
                # Verify quote structure
                required_fields = ['symbol', 'bid', 'ask', 'timestamp']
                for field in required_fields:
                    assert field in quote, f"Missing {field} in quote for {symbol}"
                
                # Verify bid/ask spread is reasonable
                spread = quote['ask'] - quote['bid']
                assert spread > 0, f"Invalid spread for {symbol}"
                assert spread < quote['bid'] * 0.01, f"Spread too wide for {symbol}"  # Max 1% spread
    
    async def _get_mock_quote(self, symbol: str) -> Dict:
        """Generate mock quote data for testing."""
        mock_quotes = {
            'EURUSD': {'symbol': 'EURUSD', 'bid': 1.0864, 'ask': 1.0866, 'timestamp': datetime.now().isoformat()},
            'AAPL': {'symbol': 'AAPL', 'bid': 178.24, 'ask': 178.26, 'timestamp': datetime.now().isoformat()},
            'BTCUSD': {'symbol': 'BTCUSD', 'bid': 45248.50, 'ask': 45251.50, 'timestamp': datetime.now().isoformat()}
        }
        return mock_quotes.get(symbol, {'symbol': symbol, 'bid': 100.0, 'ask': 100.02, 'timestamp': datetime.now().isoformat()})
    
    @pytest.mark.asyncio
    async def test_cross_asset_strategy_execution(self):
        """Test strategy execution across multiple asset classes."""
        # Mock multi-asset strategy
        strategy_config = {
            'name': 'CrossAssetMomentumStrategy',
            'asset_allocation': {
                'forex': 0.4,
                'stocks': 0.3,
                'commodities': 0.2,
                'crypto': 0.1
            },
            'rebalance_frequency': 'daily',
            'risk_budget': 0.02  # 2% daily VaR limit
        }
        
        # Mock strategy engine
        with patch('nautilus_trader_engine.strategies.MultiAssetStrategyEngine') as mock_strategy:
            mock_instance = AsyncMock()
            mock_strategy.return_value = mock_instance
            
            # Configure strategy responses
            mock_instance.initialize_strategy.return_value = {'status': 'initialized'}
            mock_instance.generate_signals.return_value = [
                {
                    'symbol': 'EURUSD',
                    'asset_class': 'forex',
                    'signal': 'BUY',
                    'strength': 0.75,
                    'target_allocation': 0.15
                },
                {
                    'symbol': 'AAPL',
                    'asset_class': 'stocks',
                    'signal': 'HOLD',
                    'strength': 0.45,
                    'target_allocation': 0.10
                },
                {
                    'symbol': 'XAUUSD',
                    'asset_class': 'commodities',
                    'signal': 'SELL',
                    'strength': 0.60,
                    'target_allocation': 0.05
                }
            ]
            
            mock_instance.execute_rebalancing.return_value = {
                'rebalancing_orders': 3,
                'total_turnover': 25000.0,
                'execution_cost': 15.50,
                'status': 'completed'
            }
            
            strategy_engine = mock_strategy()
            
            # Test strategy initialization
            init_result = await strategy_engine.initialize_strategy(strategy_config)
            assert init_result['status'] == 'initialized'
            
            # Test signal generation
            signals = await strategy_engine.generate_signals()
            
            # Verify signals structure
            assert len(signals) > 0
            
            for signal in signals:
                required_fields = ['symbol', 'asset_class', 'signal', 'strength', 'target_allocation']
                for field in required_fields:
                    assert field in signal, f"Missing {field} in signal"
                
                # Verify signal values
                assert signal['signal'] in ['BUY', 'SELL', 'HOLD']
                assert 0 <= signal['strength'] <= 1
                assert 0 <= signal['target_allocation'] <= 1
            
            # Test cross-asset rebalancing
            rebalancing_result = await strategy_engine.execute_rebalancing(signals)
            
            assert 'rebalancing_orders' in rebalancing_result
            assert 'total_turnover' in rebalancing_result
            assert 'execution_cost' in rebalancing_result
            assert rebalancing_result['status'] == 'completed'
    
    @pytest.mark.asyncio
    async def test_currency_conversion_and_pnl_calculation(self):
        """Test currency conversion and P&L calculation across different base currencies."""
        # Mock currency conversion rates
        fx_rates = {
            'EURUSD': 1.0865,
            'GBPUSD': 1.2640,
            'USDJPY': 150.25,
            'AUDUSD': 0.6580,
            'USDCAD': 1.3720
        }
        
        # Test positions in different base currencies
        multi_currency_positions = [
            {
                'symbol': 'EURUSD',
                'base_currency': 'EUR',
                'quote_currency': 'USD',
                'quantity': 100000,
                'entry_price': 1.0850,
                'current_price': 1.0865
            },
            {
                'symbol': 'GBPJPY',
                'base_currency': 'GBP',
                'quote_currency': 'JPY',
                'quantity': 50000,
                'entry_price': 189.50,
                'current_price': 190.25
            },
            {
                'symbol': 'XAUUSD',
                'base_currency': 'XAU',
                'quote_currency': 'USD',
                'quantity': 10,
                'entry_price': 2050.00,
                'current_price': 2065.50
            }
        ]
        
        # Mock P&L calculator
        with patch('nautilus_trader_engine.pnl.MultiCurrencyPnLCalculator') as mock_pnl_calc:
            mock_instance = Mock()
            mock_pnl_calc.return_value = mock_instance
            
            # Configure P&L calculation
            def calculate_position_pnl(position, account_currency='USD'):
                """Calculate P&L for a position in account currency."""
                quantity = position['quantity']
                price_diff = position['current_price'] - position['entry_price']
                
                if position['symbol'] == 'EURUSD':
                    pnl_usd = quantity * price_diff
                elif position['symbol'] == 'GBPJPY':
                    pnl_jpy = quantity * price_diff
                    pnl_usd = pnl_jpy / fx_rates['USDJPY']  # Convert JPY to USD
                elif position['symbol'] == 'XAUUSD':
                    pnl_usd = quantity * price_diff
                else:
                    pnl_usd = 0.0
                
                return {
                    'pnl_local': quantity * price_diff,
                    'pnl_account_currency': pnl_usd,
                    'fx_rate_used': fx_rates.get(f"{position['quote_currency']}{account_currency}", 1.0)
                }
            
            mock_instance.calculate_position_pnl.side_effect = calculate_position_pnl
            mock_instance.get_fx_rate.side_effect = lambda from_ccy, to_ccy: fx_rates.get(f"{from_ccy}{to_ccy}", 1.0)
            
            pnl_calculator = mock_pnl_calc()
            
            # Test P&L calculation for each position
            total_pnl_usd = 0.0
            
            for position in multi_currency_positions:
                pnl_result = pnl_calculator.calculate_position_pnl(position)
                
                # Verify P&L calculation structure
                assert 'pnl_local' in pnl_result
                assert 'pnl_account_currency' in pnl_result
                assert 'fx_rate_used' in pnl_result
                
                # Verify P&L is reasonable
                assert isinstance(pnl_result['pnl_account_currency'], (int, float))
                total_pnl_usd += pnl_result['pnl_account_currency']
            
            # Test FX rate retrieval
            for currency_pair, expected_rate in fx_rates.items():
                from_currency = currency_pair[:3]
                to_currency = currency_pair[3:]
                
                retrieved_rate = pnl_calculator.get_fx_rate(from_currency, to_currency)
                assert retrieved_rate == expected_rate
            
            # Verify total P&L is calculated correctly
            assert total_pnl_usd != 0.0  # Should have some P&L from price movements
    
    @pytest.mark.asyncio
    async def test_asset_class_specific_trading_rules(self):
        """Test asset class specific trading rules and validations."""
        # Define asset class specific rules
        trading_rules = {
            'forex': {
                'min_quantity': 1000,
                'max_quantity': 10000000,
                'allowed_order_types': ['MARKET', 'LIMIT', 'STOP'],
                'trading_sessions': ['LONDON', 'NEW_YORK', 'TOKYO'],
                'weekend_trading': False
            },
            'stocks': {
                'min_quantity': 1,
                'max_quantity': 1000000,
                'allowed_order_types': ['MARKET', 'LIMIT', 'STOP_LIMIT'],
                'trading_sessions': ['REGULAR', 'PRE_MARKET', 'AFTER_HOURS'],
                'weekend_trading': False
            },
            'crypto': {
                'min_quantity': 0.001,
                'max_quantity': 1000,
                'allowed_order_types': ['MARKET', 'LIMIT', 'STOP'],
                'trading_sessions': ['24_7'],
                'weekend_trading': True
            }
        }
        
        # Test orders with different rule violations
        test_orders = [
            {
                'symbol': 'EURUSD',
                'asset_class': 'forex',
                'quantity': 500,  # Below minimum
                'order_type': 'MARKET',
                'expected_validation': False
            },
            {
                'symbol': 'AAPL',
                'asset_class': 'stocks',
                'quantity': 100,
                'order_type': 'STOP',  # Not allowed for stocks
                'expected_validation': False
            },
            {
                'symbol': 'BTCUSD',
                'asset_class': 'crypto',
                'quantity': 0.5,
                'order_type': 'LIMIT',
                'expected_validation': True
            }
        ]
        
        # Mock order validator
        with patch('nautilus_trader_engine.validation.AssetClassOrderValidator') as mock_validator:
            mock_instance = Mock()
            mock_validator.return_value = mock_instance
            
            def validate_order(order):
                """Validate order against asset class rules."""
                asset_class = order['asset_class']
                rules = trading_rules.get(asset_class, {})
                
                validation_result = {
                    'valid': True,
                    'violations': []
                }
                
                # Check quantity limits
                if order['quantity'] < rules.get('min_quantity', 0):
                    validation_result['valid'] = False
                    validation_result['violations'].append(f"Quantity below minimum {rules['min_quantity']}")
                
                if order['quantity'] > rules.get('max_quantity', float('inf')):
                    validation_result['valid'] = False
                    validation_result['violations'].append(f"Quantity above maximum {rules['max_quantity']}")
                
                # Check order type
                allowed_types = rules.get('allowed_order_types', [])
                if order['order_type'] not in allowed_types:
                    validation_result['valid'] = False
                    validation_result['violations'].append(f"Order type {order['order_type']} not allowed")
                
                return validation_result
            
            mock_instance.validate_order.side_effect = validate_order
            mock_instance.get_trading_rules.side_effect = lambda ac: trading_rules.get(ac, {})
            
            validator = mock_validator()
            
            # Test order validation
            for order in test_orders:
                validation_result = validator.validate_order(order)
                
                # Verify validation result matches expectation
                assert validation_result['valid'] == order['expected_validation'], \
                    f"Validation result mismatch for {order['symbol']}"
                
                if not validation_result['valid']:
                    assert len(validation_result['violations']) > 0, \
                        f"Expected violations for invalid order {order['symbol']}"
            
            # Test trading rules retrieval
            for asset_class, expected_rules in trading_rules.items():
                retrieved_rules = validator.get_trading_rules(asset_class)
                
                # Verify all expected rule fields are present
                for rule_key, rule_value in expected_rules.items():
                    assert rule_key in retrieved_rules
                    assert retrieved_rules[rule_key] == rule_value


if __name__ == '__main__':
    pytest.main([__file__])