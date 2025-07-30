"""
Comprehensive tests for Forex and Cryptocurrency Trading Support
Tests exchange connectors, trading engine, order management, and market data
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from nautilus_trader_engine.assets.forex_crypto_support import (
    CurrencyType, ExchangeType, OrderSide, OrderType, OrderStatus,
    Currency, CurrencyPair, TradingOrder,
    ExchangeConnector, ForexConnector, CryptoConnector,
    ForexCryptoTradingEngine
)


class TestCurrency:
    """Test Currency class"""
    
    def test_fiat_currency_creation(self):
        """Test fiat currency creation"""
        currency = Currency(
            code="USD",
            name="US Dollar",
            currency_type=CurrencyType.FIAT,
            precision=2,
            country="United States",
            central_bank="Federal Reserve"
        )
        
        assert currency.code == "USD"
        assert currency.currency_type == CurrencyType.FIAT
        assert currency.precision == 2
        assert currency.country == "United States"
        assert currency.is_active is True
    
    def test_crypto_currency_creation(self):
        """Test cryptocurrency creation"""
        currency = Currency(
            code="BTC",
            name="Bitcoin",
            currency_type=CurrencyType.CRYPTOCURRENCY,
            precision=8,
            blockchain="Bitcoin",
            total_supply=21000000,
            circulating_supply=19000000
        )
        
        assert currency.code == "BTC"
        assert currency.currency_type == CurrencyType.CRYPTOCURRENCY
        assert currency.precision == 8
        assert currency.blockchain == "Bitcoin"
        assert currency.total_supply == 21000000


class TestCurrencyPair:
    """Test CurrencyPair class"""
    
    def test_currency_pair_creation(self):
        """Test currency pair creation"""
        usd = Currency("USD", "US Dollar", CurrencyType.FIAT)
        eur = Currency("EUR", "Euro", CurrencyType.FIAT)
        
        pair = CurrencyPair(
            base_currency=eur,
            quote_currency=usd,
            min_trade_size=1000,
            tick_size=0.00001
        )
        
        assert pair.symbol == "EUR/USD"
        assert pair.base_currency.code == "EUR"
        assert pair.quote_currency.code == "USD"
        assert pair.min_trade_size == 1000
        assert pair.tick_size == 0.00001
    
    def test_custom_symbol(self):
        """Test currency pair with custom symbol"""
        btc = Currency("BTC", "Bitcoin", CurrencyType.CRYPTOCURRENCY)
        usdt = Currency("USDT", "Tether", CurrencyType.CRYPTOCURRENCY)
        
        pair = CurrencyPair(
            base_currency=btc,
            quote_currency=usdt,
            symbol="BTCUSDT"
        )
        
        assert pair.symbol == "BTCUSDT"


class TestTradingOrder:
    """Test TradingOrder class"""
    
    def test_order_creation(self):
        """Test trading order creation"""
        order = TradingOrder(
            order_id="test_001",
            symbol="EUR/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10000,
            price=1.1000
        )
        
        assert order.order_id == "test_001"
        assert order.symbol == "EUR/USD"
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.LIMIT
        assert order.quantity == 10000
        assert order.price == 1.1000
        assert order.status == OrderStatus.PENDING
    
    def test_market_order(self):
        """Test market order creation"""
        order = TradingOrder(
            order_id="market_001",
            symbol="BTC/USD",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=0.1
        )
        
        assert order.order_type == OrderType.MARKET
        assert order.price == 0.0  # Market orders don't have price
    
    def test_order_status_updates(self):
        """Test order status updates"""
        order = TradingOrder(
            order_id="status_test",
            symbol="EUR/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1000,
            price=1.1000
        )
        
        # Update to filled
        order.status = OrderStatus.FILLED
        order.filled_quantity = 1000
        order.average_price = 1.1005
        order.filled_at = datetime.now()
        
        assert order.status == OrderStatus.FILLED
        assert order.filled_quantity == 1000
        assert order.average_price == 1.1005
        assert order.filled_at is not None


class TestForexConnector:
    """Test ForexConnector class"""
    
    @pytest.fixture
    def forex_connector(self):
        return ForexConnector("TestForex")
    
    def test_connector_initialization(self, forex_connector):
        """Test forex connector initialization"""
        assert forex_connector.exchange_name == "TestForex"
        assert forex_connector.exchange_type == ExchangeType.FOREX
        assert forex_connector.is_connected is False
        assert forex_connector.sandbox_mode is True
    
    @pytest.mark.asyncio
    async def test_connect_without_requests(self, forex_connector):
        """Test connection when requests library is not available"""
        with patch('nautilus_trader_engine.assets.forex_crypto_support.requests', None):
            result = await forex_connector.connect()
            assert result is False
    
    @pytest.mark.asyncio
    async def test_connect_success(self, forex_connector):
        """Test successful connection"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'accounts': [{'id': 'test_account_123'}]
        }
        mock_session.get.return_value = mock_response
        
        with patch('requests.Session', return_value=mock_session):
            forex_connector.api_key = "test_key"
            result = await forex_connector.connect()
            
            assert result is True
            assert forex_connector.is_connected is True
            assert forex_connector.account_id == "test_account_123"
    
    @pytest.mark.asyncio
    async def test_get_account_balance(self, forex_connector):
        """Test getting account balance"""
        forex_connector.is_connected = True
        forex_connector.account_id = "test_account"
        
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'account': {
                'balance': '10000.00',
                'unrealizedPL': '150.50',
                'marginUsed': '2000.00',
                'marginAvailable': '8000.00'
            }
        }
        mock_session.get.return_value = mock_response
        forex_connector.session = mock_session
        
        balance = await forex_connector.get_account_balance()
        
        assert balance['balance'] == 10000.0
        assert balance['unrealized_pl'] == 150.5
        assert balance['margin_used'] == 2000.0
        assert balance['margin_available'] == 8000.0
    
    @pytest.mark.asyncio
    async def test_place_order(self, forex_connector):
        """Test placing forex order"""
        forex_connector.is_connected = True
        forex_connector.account_id = "test_account"
        
        order = TradingOrder(
            order_id="forex_001",
            symbol="EUR/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10000,
            price=1.1000
        )
        
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'orderCreateTransaction': {'id': 'oanda_123'}
        }
        mock_session.post.return_value = mock_response
        forex_connector.session = mock_session
        
        result_order = await forex_connector.place_order(order)
        
        assert result_order.status == OrderStatus.OPEN
        assert result_order.exchange_order_id == "oanda_123"
    
    @pytest.mark.asyncio
    async def test_get_market_data(self, forex_connector):
        """Test getting forex market data"""
        forex_connector.is_connected = True
        
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'candles': [{
                'bid': {'c': '1.1000'},
                'ask': {'c': '1.1002'},
                'mid': {'c': '1.1001'},
                'volume': '1000',
                'time': '2024-01-01T12:00:00Z'
            }]
        }
        mock_session.get.return_value = mock_response
        forex_connector.session = mock_session
        
        market_data = await forex_connector.get_market_data("EUR/USD")
        
        assert market_data['symbol'] == "EUR/USD"
        assert market_data['bid'] == 1.1000
        assert market_data['ask'] == 1.1002
        assert market_data['mid'] == 1.1001
        assert market_data['volume'] == 1000.0


class TestCryptoConnector:
    """Test CryptoConnector class"""
    
    @pytest.fixture
    def crypto_connector(self):
        return CryptoConnector("TestCrypto")
    
    def test_connector_initialization(self, crypto_connector):
        """Test crypto connector initialization"""
        assert crypto_connector.exchange_name == "TestCrypto"
        assert crypto_connector.exchange_type == ExchangeType.CRYPTO
        assert crypto_connector.is_connected is False
    
    def test_signature_generation(self, crypto_connector):
        """Test HMAC signature generation"""
        crypto_connector.api_secret = "test_secret"
        query_string = "symbol=BTCUSDT&side=BUY&type=LIMIT&quantity=1&price=50000&timestamp=1640995200000"
        
        signature = crypto_connector._generate_signature(query_string)
        
        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256 hex digest length
    
    @pytest.mark.asyncio
    async def test_connect_success(self, crypto_connector):
        """Test successful connection to crypto exchange"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_session.get.return_value = mock_response
        
        with patch('requests.Session', return_value=mock_session):
            result = await crypto_connector.connect()
            
            assert result is True
            assert crypto_connector.is_connected is True
    
    @pytest.mark.asyncio
    async def test_get_account_balance(self, crypto_connector):
        """Test getting crypto account balance"""
        crypto_connector.is_connected = True
        crypto_connector.api_key = "test_key"
        crypto_connector.api_secret = "test_secret"
        
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'balances': [
                {'asset': 'BTC', 'free': '1.5', 'locked': '0.5'},
                {'asset': 'USDT', 'free': '10000.0', 'locked': '0.0'},
                {'asset': 'ETH', 'free': '0.0', 'locked': '0.0'}  # Should be filtered out
            ]
        }
        mock_session.get.return_value = mock_response
        crypto_connector.session = mock_session
        
        balance = await crypto_connector.get_account_balance()
        
        assert 'BTC' in balance
        assert balance['BTC']['free'] == 1.5
        assert balance['BTC']['locked'] == 0.5
        assert balance['BTC']['total'] == 2.0
        assert 'USDT' in balance
        assert 'ETH' not in balance  # Zero balance should be filtered
    
    @pytest.mark.asyncio
    async def test_place_limit_order(self, crypto_connector):
        """Test placing crypto limit order"""
        crypto_connector.is_connected = True
        crypto_connector.api_key = "test_key"
        crypto_connector.api_secret = "test_secret"
        
        order = TradingOrder(
            order_id="crypto_001",
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.1,
            price=50000
        )
        
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'orderId': 12345,
            'status': 'NEW',
            'executedQty': '0.0',
            'fills': []
        }
        mock_session.post.return_value = mock_response
        crypto_connector.session = mock_session
        
        result_order = await crypto_connector.place_order(order)
        
        assert result_order.status == OrderStatus.OPEN
        assert result_order.exchange_order_id == "12345"
    
    @pytest.mark.asyncio
    async def test_place_market_order(self, crypto_connector):
        """Test placing crypto market order"""
        crypto_connector.is_connected = True
        crypto_connector.api_key = "test_key"
        crypto_connector.api_secret = "test_secret"
        
        order = TradingOrder(
            order_id="crypto_market_001",
            symbol="BTC/USDT",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=0.05
        )
        
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'orderId': 12346,
            'status': 'FILLED',
            'executedQty': '0.05',
            'price': '49500.0',
            'fills': [{'price': '49500.0', 'qty': '0.05'}]
        }
        mock_session.post.return_value = mock_response
        crypto_connector.session = mock_session
        
        result_order = await crypto_connector.place_order(order)
        
        assert result_order.status == OrderStatus.FILLED
        assert result_order.filled_quantity == 0.05
    
    @pytest.mark.asyncio
    async def test_get_market_data(self, crypto_connector):
        """Test getting crypto market data"""
        crypto_connector.is_connected = True
        
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'lastPrice': '50000.0',
            'bidPrice': '49995.0',
            'askPrice': '50005.0',
            'volume': '1000.5',
            'quoteVolume': '50000000.0',
            'priceChangePercent': '2.5',
            'highPrice': '51000.0',
            'lowPrice': '49000.0',
            'closeTime': 1640995200000
        }
        mock_session.get.return_value = mock_response
        crypto_connector.session = mock_session
        
        market_data = await crypto_connector.get_market_data("BTC/USDT")
        
        assert market_data['symbol'] == "BTC/USDT"
        assert market_data['price'] == 50000.0
        assert market_data['bid'] == 49995.0
        assert market_data['ask'] == 50005.0
        assert market_data['volume'] == 1000.5
        assert market_data['change_24h'] == 2.5
    
    @pytest.mark.asyncio
    async def test_get_supported_pairs(self, crypto_connector):
        """Test getting supported crypto pairs"""
        crypto_connector.is_connected = True
        
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'symbols': [
                {
                    'symbol': 'BTCUSDT',
                    'status': 'TRADING',
                    'baseAsset': 'BTC',
                    'quoteAsset': 'USDT',
                    'baseAssetPrecision': 8,
                    'quoteAssetPrecision': 8,
                    'filters': [
                        {'filterType': 'LOT_SIZE', 'minQty': '0.00001'},
                        {'filterType': 'PRICE_FILTER', 'tickSize': '0.01'}
                    ]
                },
                {
                    'symbol': 'ETHBTC',
                    'status': 'BREAK',  # Should be filtered out
                    'baseAsset': 'ETH',
                    'quoteAsset': 'BTC'
                }
            ]
        }
        mock_session.get.return_value = mock_response
        crypto_connector.session = mock_session
        
        pairs = await crypto_connector.get_supported_pairs()
        
        assert len(pairs) == 1  # Only trading pairs should be included
        assert pairs[0].symbol == "BTC/USDT"
        assert pairs[0].base_currency.code == "BTC"
        assert pairs[0].quote_currency.code == "USDT"
        assert pairs[0].min_trade_size == 0.00001
        assert pairs[0].tick_size == 0.01


class TestForexCryptoTradingEngine:
    """Test ForexCryptoTradingEngine class"""
    
    @pytest.fixture
    def trading_engine(self):
        return ForexCryptoTradingEngine()
    
    @pytest.fixture
    def mock_forex_connector(self):
        connector = Mock(spec=ForexConnector)
        connector.exchange_name = "MockForex"
        connector.exchange_type = ExchangeType.FOREX
        connector.is_connected = False
        return connector
    
    @pytest.fixture
    def mock_crypto_connector(self):
        connector = Mock(spec=CryptoConnector)
        connector.exchange_name = "MockCrypto"
        connector.exchange_type = ExchangeType.CRYPTO
        connector.is_connected = False
        return connector
    
    def test_engine_initialization(self, trading_engine):
        """Test trading engine initialization"""
        assert len(trading_engine.connectors) == 0
        assert len(trading_engine.currency_pairs) == 0
        assert len(trading_engine.active_orders) == 0
        assert trading_engine.daily_pnl == 0.0
        assert trading_engine.max_position_size == 1000000
    
    def test_add_connector(self, trading_engine, mock_forex_connector):
        """Test adding exchange connector"""
        trading_engine.add_connector(mock_forex_connector)
        
        assert "MockForex" in trading_engine.connectors
        assert trading_engine.connectors["MockForex"] == mock_forex_connector
    
    @pytest.mark.asyncio
    async def test_connect_all_success(self, trading_engine, mock_forex_connector, mock_crypto_connector):
        """Test connecting to all exchanges successfully"""
        # Setup mocks
        mock_forex_connector.connect = AsyncMock(return_value=True)
        mock_forex_connector.get_supported_pairs = AsyncMock(return_value=[
            CurrencyPair(
                Currency("EUR", "Euro", CurrencyType.FIAT),
                Currency("USD", "US Dollar", CurrencyType.FIAT),
                symbol="EUR/USD"
            )
        ])
        
        mock_crypto_connector.connect = AsyncMock(return_value=True)
        mock_crypto_connector.get_supported_pairs = AsyncMock(return_value=[
            CurrencyPair(
                Currency("BTC", "Bitcoin", CurrencyType.CRYPTOCURRENCY),
                Currency("USDT", "Tether", CurrencyType.CRYPTOCURRENCY),
                symbol="BTC/USDT"
            )
        ])
        
        trading_engine.add_connector(mock_forex_connector)
        trading_engine.add_connector(mock_crypto_connector)
        
        results = await trading_engine.connect_all()
        
        assert results["MockForex"] is True
        assert results["MockCrypto"] is True
        assert len(trading_engine.currency_pairs) == 2
        assert "EUR/USD" in trading_engine.currency_pairs
        assert "BTC/USDT" in trading_engine.currency_pairs
    
    @pytest.mark.asyncio
    async def test_connect_all_partial_failure(self, trading_engine, mock_forex_connector, mock_crypto_connector):
        """Test connecting with partial failures"""
        mock_forex_connector.connect = AsyncMock(return_value=True)
        mock_forex_connector.get_supported_pairs = AsyncMock(return_value=[])
        
        mock_crypto_connector.connect = AsyncMock(return_value=False)
        
        trading_engine.add_connector(mock_forex_connector)
        trading_engine.add_connector(mock_crypto_connector)
        
        results = await trading_engine.connect_all()
        
        assert results["MockForex"] is True
        assert results["MockCrypto"] is False
    
    def test_order_validation_success(self, trading_engine):
        """Test successful order validation"""
        # Add a currency pair
        pair = CurrencyPair(
            Currency("EUR", "Euro", CurrencyType.FIAT),
            Currency("USD", "US Dollar", CurrencyType.FIAT),
            symbol="EUR/USD",
            min_trade_size=1000
        )
        trading_engine.currency_pairs["EUR/USD"] = pair
        
        order = TradingOrder(
            order_id="test_001",
            symbol="EUR/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10000,
            price=1.1000
        )
        
        assert trading_engine._validate_order(order) is True
    
    def test_order_validation_unsupported_pair(self, trading_engine):
        """Test order validation with unsupported pair"""
        order = TradingOrder(
            order_id="test_001",
            symbol="UNSUPPORTED/PAIR",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10000,
            price=1.1000
        )
        
        assert trading_engine._validate_order(order) is False
    
    def test_order_validation_below_minimum(self, trading_engine):
        """Test order validation below minimum trade size"""
        pair = CurrencyPair(
            Currency("EUR", "Euro", CurrencyType.FIAT),
            Currency("USD", "US Dollar", CurrencyType.FIAT),
            symbol="EUR/USD",
            min_trade_size=1000
        )
        trading_engine.currency_pairs["EUR/USD"] = pair
        
        order = TradingOrder(
            order_id="test_001",
            symbol="EUR/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=500,  # Below minimum
            price=1.1000
        )
        
        assert trading_engine._validate_order(order) is False
    
    def test_order_validation_exceeds_maximum(self, trading_engine):
        """Test order validation exceeding maximum position size"""
        pair = CurrencyPair(
            Currency("EUR", "Euro", CurrencyType.FIAT),
            Currency("USD", "US Dollar", CurrencyType.FIAT),
            symbol="EUR/USD",
            min_trade_size=1000
        )
        trading_engine.currency_pairs["EUR/USD"] = pair
        
        order = TradingOrder(
            order_id="test_001",
            symbol="EUR/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=2000000,  # Exceeds maximum
            price=1.1000
        )
        
        assert trading_engine._validate_order(order) is False
    
    def test_order_validation_daily_loss_limit(self, trading_engine):
        """Test order validation with daily loss limit exceeded"""
        pair = CurrencyPair(
            Currency("EUR", "Euro", CurrencyType.FIAT),
            Currency("USD", "US Dollar", CurrencyType.FIAT),
            symbol="EUR/USD",
            min_trade_size=1000
        )
        trading_engine.currency_pairs["EUR/USD"] = pair
        trading_engine.daily_pnl = -15000  # Exceeds max daily loss
        
        order = TradingOrder(
            order_id="test_001",
            symbol="EUR/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10000,
            price=1.1000
        )
        
        assert trading_engine._validate_order(order) is False
    
    @pytest.mark.asyncio
    async def test_place_order_success(self, trading_engine, mock_forex_connector):
        """Test successful order placement"""
        # Setup
        pair = CurrencyPair(
            Currency("EUR", "Euro", CurrencyType.FIAT),
            Currency("USD", "US Dollar", CurrencyType.FIAT),
            symbol="EUR/USD",
            min_trade_size=1000
        )
        trading_engine.currency_pairs["EUR/USD"] = pair
        trading_engine.add_connector(mock_forex_connector)
        mock_forex_connector.is_connected = True
        
        order = TradingOrder(
            order_id="test_001",
            symbol="EUR/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10000,
            price=1.1000
        )
        
        # Mock successful order placement
        filled_order = TradingOrder(
            order_id="test_001",
            symbol="EUR/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10000,
            price=1.1000,
            status=OrderStatus.OPEN,
            exchange_order_id="exchange_123"
        )
        mock_forex_connector.place_order = AsyncMock(return_value=filled_order)
        
        result = await trading_engine.place_order("MockForex", order)
        
        assert result.status == OrderStatus.OPEN
        assert result.exchange_order_id == "exchange_123"
        assert "test_001" in trading_engine.active_orders
        assert len(trading_engine.order_history) == 1
    
    @pytest.mark.asyncio
    async def test_place_order_validation_failure(self, trading_engine, mock_forex_connector):
        """Test order placement with validation failure"""
        trading_engine.add_connector(mock_forex_connector)
        mock_forex_connector.is_connected = True
        
        # Order with unsupported pair
        order = TradingOrder(
            order_id="test_001",
            symbol="UNSUPPORTED/PAIR",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10000,
            price=1.1000
        )
        
        result = await trading_engine.place_order("MockForex", order)
        
        assert result.status == OrderStatus.REJECTED
        assert len(trading_engine.active_orders) == 0
    
    @pytest.mark.asyncio
    async def test_cancel_order_success(self, trading_engine, mock_forex_connector):
        """Test successful order cancellation"""
        trading_engine.add_connector(mock_forex_connector)
        mock_forex_connector.is_connected = True
        mock_forex_connector.cancel_order = AsyncMock(return_value=True)
        
        # Add an active order
        order = TradingOrder(
            order_id="test_001",
            symbol="EUR/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=10000,
            price=1.1000,
            status=OrderStatus.OPEN
        )
        trading_engine.active_orders["test_001"] = order
        
        result = await trading_engine.cancel_order("MockForex", "test_001")
        
        assert result is True
        assert "test_001" not in trading_engine.active_orders
    
    @pytest.mark.asyncio
    async def test_get_all_balances(self, trading_engine, mock_forex_connector, mock_crypto_connector):
        """Test getting balances from all exchanges"""
        trading_engine.add_connector(mock_forex_connector)
        trading_engine.add_connector(mock_crypto_connector)
        
        mock_forex_connector.is_connected = True
        mock_forex_connector.get_account_balance = AsyncMock(return_value={
            'balance': 10000.0,
            'margin_used': 2000.0
        })
        
        mock_crypto_connector.is_connected = True
        mock_crypto_connector.get_account_balance = AsyncMock(return_value={
            'BTC': {'free': 1.5, 'locked': 0.5, 'total': 2.0},
            'USDT': {'free': 5000.0, 'locked': 0.0, 'total': 5000.0}
        })
        
        balances = await trading_engine.get_all_balances()
        
        assert "MockForex" in balances
        assert "MockCrypto" in balances
        assert balances["MockForex"]["balance"] == 10000.0
        assert balances["MockCrypto"]["BTC"]["total"] == 2.0
    
    def test_get_supported_pairs(self, trading_engine):
        """Test getting supported pairs"""
        pair1 = CurrencyPair(
            Currency("EUR", "Euro", CurrencyType.FIAT),
            Currency("USD", "US Dollar", CurrencyType.FIAT),
            symbol="EUR/USD"
        )
        pair2 = CurrencyPair(
            Currency("BTC", "Bitcoin", CurrencyType.CRYPTOCURRENCY),
            Currency("USDT", "Tether", CurrencyType.CRYPTOCURRENCY),
            symbol="BTC/USDT"
        )
        
        trading_engine.currency_pairs["EUR/USD"] = pair1
        trading_engine.currency_pairs["BTC/USDT"] = pair2
        
        pairs = trading_engine.get_supported_pairs()
        
        assert len(pairs) == 2
        assert "EUR/USD" in pairs
        assert "BTC/USDT" in pairs
    
    def test_get_pair_info(self, trading_engine):
        """Test getting currency pair information"""
        pair = CurrencyPair(
            Currency("EUR", "Euro", CurrencyType.FIAT),
            Currency("USD", "US Dollar", CurrencyType.FIAT),
            symbol="EUR/USD",
            min_trade_size=1000,
            tick_size=0.00001
        )
        trading_engine.currency_pairs["EUR/USD"] = pair
        
        info = trading_engine.get_pair_info("EUR/USD")
        
        assert info is not None
        assert info.symbol == "EUR/USD"
        assert info.min_trade_size == 1000
        assert info.tick_size == 0.00001
        
        # Test non-existent pair
        assert trading_engine.get_pair_info("NON/EXISTENT") is None
    
    def test_get_active_orders(self, trading_engine):
        """Test getting active orders"""
        order1 = TradingOrder("order1", "EUR/USD", OrderSide.BUY, OrderType.LIMIT, 1000, 1.1000)
        order2 = TradingOrder("order2", "BTC/USDT", OrderSide.SELL, OrderType.MARKET, 0.1)
        
        trading_engine.active_orders["order1"] = order1
        trading_engine.active_orders["order2"] = order2
        
        active_orders = trading_engine.get_active_orders()
        
        assert len(active_orders) == 2
        assert order1 in active_orders
        assert order2 in active_orders
    
    def test_get_order_history(self, trading_engine):
        """Test getting order history"""
        # Add some orders to history
        for i in range(150):  # More than default limit
            order = TradingOrder(f"order_{i}", "EUR/USD", OrderSide.BUY, OrderType.LIMIT, 1000, 1.1000)
            trading_engine.order_history.append(order)
        
        # Test default limit
        history = trading_engine.get_order_history()
        assert len(history) == 100  # Default limit
        
        # Test custom limit
        history = trading_engine.get_order_history(limit=50)
        assert len(history) == 50
        
        # Test that we get the most recent orders
        assert history[-1].order_id == "order_149"
    
    def test_get_performance_summary(self, trading_engine):
        """Test getting performance summary"""
        # Setup some data
        trading_engine.daily_pnl = 150.50
        trading_engine.active_orders["order1"] = TradingOrder("order1", "EUR/USD", OrderSide.BUY, OrderType.LIMIT, 1000, 1.1000)
        trading_engine.order_history = [TradingOrder("order2", "BTC/USDT", OrderSide.SELL, OrderType.MARKET, 0.1)]
        
        # Add connected exchange
        mock_connector = Mock()
        mock_connector.is_connected = True
        trading_engine.connectors["TestExchange"] = mock_connector
        
        trading_engine.currency_pairs["EUR/USD"] = CurrencyPair(
            Currency("EUR", "Euro", CurrencyType.FIAT),
            Currency("USD", "US Dollar", CurrencyType.FIAT)
        )
        
        summary = trading_engine.get_performance_summary()
        
        assert summary['daily_pnl'] == 150.50
        assert summary['active_orders_count'] == 1
        assert summary['total_orders'] == 1
        assert summary['connected_exchanges'] == ["TestExchange"]
        assert summary['supported_pairs_count'] == 1


@pytest.mark.asyncio
async def test_integration_scenario():
    """Test complete integration scenario"""
    engine = ForexCryptoTradingEngine()
    
    # Create mock connectors
    forex_connector = Mock(spec=ForexConnector)
    forex_connector.exchange_name = "TestForex"
    forex_connector.exchange_type = ExchangeType.FOREX
    forex_connector.is_connected = False
    
    crypto_connector = Mock(spec=CryptoConnector)
    crypto_connector.exchange_name = "TestCrypto"
    crypto_connector.exchange_type = ExchangeType.CRYPTO
    crypto_connector.is_connected = False
    
    # Setup mock responses
    forex_connector.connect = AsyncMock(return_value=True)
    forex_connector.get_supported_pairs = AsyncMock(return_value=[
        CurrencyPair(
            Currency("EUR", "Euro", CurrencyType.FIAT),
            Currency("USD", "US Dollar", CurrencyType.FIAT),
            symbol="EUR/USD",
            min_trade_size=1000
        )
    ])
    
    crypto_connector.connect = AsyncMock(return_value=True)
    crypto_connector.get_supported_pairs = AsyncMock(return_value=[
        CurrencyPair(
            Currency("BTC", "Bitcoin", CurrencyType.CRYPTOCURRENCY),
            Currency("USDT", "Tether", CurrencyType.CRYPTOCURRENCY),
            symbol="BTC/USDT",
            min_trade_size=0.001
        )
    ])
    
    # Add connectors
    engine.add_connector(forex_connector)
    engine.add_connector(crypto_connector)
    
    # Connect all
    connections = await engine.connect_all()
    assert connections["TestForex"] is True
    assert connections["TestCrypto"] is True
    
    # Check supported pairs
    pairs = engine.get_supported_pairs()
    assert len(pairs) == 2
    assert "EUR/USD" in pairs
    assert "BTC/USDT" in pairs
    
    # Test order placement
    forex_order = TradingOrder(
        order_id="forex_001",
        symbol="EUR/USD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=10000,
        price=1.1000
    )
    
    # Mock successful order placement
    filled_order = TradingOrder(
        order_id="forex_001",
        symbol="EUR/USD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=10000,
        price=1.1000,
        status=OrderStatus.OPEN,
        exchange_order_id="forex_123"
    )
    forex_connector.place_order = AsyncMock(return_value=filled_order)
    forex_connector.is_connected = True
    
    result = await engine.place_order("TestForex", forex_order)
    assert result.status == OrderStatus.OPEN
    
    # Get performance summary
    summary = engine.get_performance_summary()
    assert summary['active_orders_count'] == 1
    assert summary['total_orders'] == 1
    
    print("Integration test completed successfully!")


if __name__ == "__main__":
    # Run the integration test
    asyncio.run(test_integration_scenario())