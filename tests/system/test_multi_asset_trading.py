#!/usr/bin/env python3
"""
Multi-Asset Trading System Tests
End-to-end system tests for multi-asset trading capabilities across different asset classes.
"""

import pytest
import asyncio
import time
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import logging
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
import uuid
import random
from decimal import Decimal
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AssetClass(Enum):
    """Asset class enumeration"""
    EQUITY = "equity"
    FOREX = "forex"
    CRYPTOCURRENCY = "cryptocurrency"
    COMMODITY = "commodity"
    BOND = "bond"
    OPTION = "option"
    FUTURE = "future"
    ETF = "etf"
    INDEX = "index"


class OrderType(Enum):
    """Order type enumeration"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"
    ICEBERG = "iceberg"
    TWAP = "twap"
    VWAP = "vwap"


class OrderStatus(Enum):
    """Order status enumeration"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class Asset:
    """Asset definition"""
    symbol: str
    name: str
    asset_class: AssetClass
    exchange: str
    currency: str
    tick_size: Decimal
    lot_size: Decimal
    margin_requirement: Decimal = Decimal('0.1')
    trading_hours: Dict[str, str] = field(default_factory=dict)
    is_tradable: bool = True
    last_price: Optional[Decimal] = None
    bid_price: Optional[Decimal] = None
    ask_price: Optional[Decimal] = None
    volume: Optional[int] = None


@dataclass
class Order:
    """Order definition"""
    order_id: str
    symbol: str
    asset_class: AssetClass
    order_type: OrderType
    side: str  # 'buy' or 'sell'
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: str = "DAY"
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: Decimal = Decimal('0')
    average_fill_price: Optional[Decimal] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    exchange: Optional[str] = None
    commission: Decimal = Decimal('0')
    tags: List[str] = field(default_factory=list)


@dataclass
class Position:
    """Position definition"""
    symbol: str
    asset_class: AssetClass
    quantity: Decimal
    average_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal = Decimal('0')
    cost_basis: Decimal = Decimal('0')
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class Portfolio:
    """Portfolio definition"""
    portfolio_id: str
    name: str
    base_currency: str
    total_value: Decimal
    cash_balance: Decimal
    positions: Dict[str, Position] = field(default_factory=dict)
    daily_pnl: Decimal = Decimal('0')
    total_pnl: Decimal = Decimal('0')
    margin_used: Decimal = Decimal('0')
    margin_available: Decimal = Decimal('0')
    last_updated: datetime = field(default_factory=datetime.now)


class MockAssetManager:
    """Mock asset manager for multi-asset trading"""
    
    def __init__(self):
        self.assets = {}
        self.market_data = {}
        self.trading_sessions = {}
        self._initialize_sample_assets()
        
    def _initialize_sample_assets(self):
        """Initialize sample assets across different asset classes"""
        sample_assets = [
            # Equities
            Asset("AAPL", "Apple Inc.", AssetClass.EQUITY, "NASDAQ", "USD", Decimal('0.01'), Decimal('1')),
            Asset("GOOGL", "Alphabet Inc.", AssetClass.EQUITY, "NASDAQ", "USD", Decimal('0.01'), Decimal('1')),
            Asset("TSLA", "Tesla Inc.", AssetClass.EQUITY, "NASDAQ", "USD", Decimal('0.01'), Decimal('1')),
            
            # Forex
            Asset("EURUSD", "Euro/US Dollar", AssetClass.FOREX, "FX", "USD", Decimal('0.00001'), Decimal('1000')),
            Asset("GBPUSD", "British Pound/US Dollar", AssetClass.FOREX, "FX", "USD", Decimal('0.00001'), Decimal('1000')),
            Asset("USDJPY", "US Dollar/Japanese Yen", AssetClass.FOREX, "FX", "JPY", Decimal('0.001'), Decimal('1000')),
            
            # Cryptocurrencies
            Asset("BTCUSD", "Bitcoin/US Dollar", AssetClass.CRYPTOCURRENCY, "CRYPTO", "USD", Decimal('0.01'), Decimal('0.001')),
            Asset("ETHUSD", "Ethereum/US Dollar", AssetClass.CRYPTOCURRENCY, "CRYPTO", "USD", Decimal('0.01'), Decimal('0.01')),
            Asset("ADAUSD", "Cardano/US Dollar", AssetClass.CRYPTOCURRENCY, "CRYPTO", "USD", Decimal('0.0001'), Decimal('1')),
            
            # Commodities
            Asset("XAUUSD", "Gold/US Dollar", AssetClass.COMMODITY, "COMEX", "USD", Decimal('0.01'), Decimal('0.1')),
            Asset("XAGUSD", "Silver/US Dollar", AssetClass.COMMODITY, "COMEX", "USD", Decimal('0.001'), Decimal('1')),
            Asset("WTIUSD", "WTI Crude Oil", AssetClass.COMMODITY, "NYMEX", "USD", Decimal('0.01'), Decimal('1')),
            
            # ETFs
            Asset("SPY", "SPDR S&P 500 ETF", AssetClass.ETF, "NYSE", "USD", Decimal('0.01'), Decimal('1')),
            Asset("QQQ", "Invesco QQQ ETF", AssetClass.ETF, "NASDAQ", "USD", Decimal('0.01'), Decimal('1')),
            
            # Bonds
            Asset("US10Y", "US 10-Year Treasury", AssetClass.BOND, "TREASURY", "USD", Decimal('0.001'), Decimal('1000')),
        ]
        
        for asset in sample_assets:
            self.assets[asset.symbol] = asset
            # Initialize with sample market data
            self._generate_sample_market_data(asset)
            
        logger.info(f"Initialized {len(self.assets)} assets across {len(set(a.asset_class for a in self.assets.values()))} asset classes")
        
    def _generate_sample_market_data(self, asset: Asset):
        """Generate sample market data for an asset"""
        # Base prices by asset class
        base_prices = {
            AssetClass.EQUITY: Decimal('150.00'),
            AssetClass.FOREX: Decimal('1.1000'),
            AssetClass.CRYPTOCURRENCY: Decimal('45000.00'),
            AssetClass.COMMODITY: Decimal('1800.00'),
            AssetClass.ETF: Decimal('400.00'),
            AssetClass.BOND: Decimal('100.00')
        }
        
        base_price = base_prices.get(asset.asset_class, Decimal('100.00'))
        
        # Add some randomness
        price_variation = Decimal(str(random.uniform(0.95, 1.05)))
        last_price = base_price * price_variation
        
        spread = last_price * Decimal('0.001')  # 0.1% spread
        
        asset.last_price = last_price
        asset.bid_price = last_price - spread / 2
        asset.ask_price = last_price + spread / 2
        asset.volume = random.randint(10000, 1000000)
        
        self.market_data[asset.symbol] = {
            'timestamp': datetime.now(),
            'last_price': asset.last_price,
            'bid_price': asset.bid_price,
            'ask_price': asset.ask_price,
            'volume': asset.volume,
            'high': asset.last_price * Decimal('1.02'),
            'low': asset.last_price * Decimal('0.98'),
            'open': asset.last_price * Decimal('0.995')
        }
        
    def get_asset(self, symbol: str) -> Optional[Asset]:
        """Get asset by symbol"""
        return self.assets.get(symbol)
        
    def get_assets_by_class(self, asset_class: AssetClass) -> List[Asset]:
        """Get all assets of a specific class"""
        return [asset for asset in self.assets.values() if asset.asset_class == asset_class]
        
    def get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get market data for a symbol"""
        return self.market_data.get(symbol)
        
    def update_market_data(self, symbol: str, price_change_pct: float = None):
        """Update market data with price movement"""
        if symbol not in self.assets or symbol not in self.market_data:
            return
            
        if price_change_pct is None:
            price_change_pct = random.uniform(-0.02, 0.02)  # ±2% random movement
            
        asset = self.assets[symbol]
        current_data = self.market_data[symbol]
        
        new_price = current_data['last_price'] * Decimal(str(1 + price_change_pct))
        spread = new_price * Decimal('0.001')
        
        asset.last_price = new_price
        asset.bid_price = new_price - spread / 2
        asset.ask_price = new_price + spread / 2
        
        self.market_data[symbol].update({
            'timestamp': datetime.now(),
            'last_price': new_price,
            'bid_price': asset.bid_price,
            'ask_price': asset.ask_price
        })
        
    def is_market_open(self, symbol: str) -> bool:
        """Check if market is open for trading"""
        # Simplified - assume all markets are open for testing
        return True
        
    def get_trading_session_info(self, symbol: str) -> Dict[str, Any]:
        """Get trading session information"""
        asset = self.get_asset(symbol)
        if not asset:
            return {}
            
        return {
            'symbol': symbol,
            'exchange': asset.exchange,
            'is_open': self.is_market_open(symbol),
            'session_start': '09:30:00',
            'session_end': '16:00:00',
            'timezone': 'US/Eastern'
        }


class MockOrderManager:
    """Mock order manager for multi-asset trading"""
    
    def __init__(self, asset_manager: MockAssetManager):
        self.asset_manager = asset_manager
        self.orders = {}
        self.order_history = []
        self.execution_latency = {}  # Track execution latency by asset class
        
    async def place_order(self, order: Order) -> Dict[str, Any]:
        """Place an order"""
        start_time = time.time()
        
        # Validate asset
        asset = self.asset_manager.get_asset(order.symbol)
        if not asset:
            raise ValueError(f"Unknown asset: {order.symbol}")
            
        if not asset.is_tradable:
            raise ValueError(f"Asset not tradable: {order.symbol}")
            
        # Check market hours
        if not self.asset_manager.is_market_open(order.symbol):
            raise ValueError(f"Market closed for {order.symbol}")
            
        # Generate order ID if not provided
        if not order.order_id:
            order.order_id = f"ORD_{uuid.uuid4().hex[:8].upper()}"
            
        # Set exchange
        order.exchange = asset.exchange
        
        # Validate order parameters
        self._validate_order(order, asset)
        
        # Store order
        order.status = OrderStatus.SUBMITTED
        order.updated_at = datetime.now()
        self.orders[order.order_id] = order
        
        # Simulate order processing delay based on asset class
        processing_delay = self._get_processing_delay(asset.asset_class)
        await asyncio.sleep(processing_delay)
        
        # Simulate order execution
        execution_result = await self._execute_order(order, asset)
        
        # Track execution latency
        execution_time = time.time() - start_time
        if asset.asset_class not in self.execution_latency:
            self.execution_latency[asset.asset_class] = []
        self.execution_latency[asset.asset_class].append(execution_time)
        
        logger.info(f"Order {order.order_id} for {order.symbol} executed in {execution_time:.3f}s")
        
        return execution_result
        
    def _validate_order(self, order: Order, asset: Asset):
        """Validate order parameters"""
        # Check minimum quantity
        if order.quantity < asset.lot_size:
            raise ValueError(f"Quantity below minimum lot size: {asset.lot_size}")
            
        # Check quantity is multiple of lot size
        if order.quantity % asset.lot_size != 0:
            raise ValueError(f"Quantity must be multiple of lot size: {asset.lot_size}")
            
        # Check price tick size for limit orders
        if order.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT] and order.price:
            if order.price % asset.tick_size != 0:
                raise ValueError(f"Price must be multiple of tick size: {asset.tick_size}")
                
    def _get_processing_delay(self, asset_class: AssetClass) -> float:
        """Get processing delay based on asset class"""
        delays = {
            AssetClass.EQUITY: 0.01,  # 10ms
            AssetClass.FOREX: 0.005,  # 5ms
            AssetClass.CRYPTOCURRENCY: 0.02,  # 20ms
            AssetClass.COMMODITY: 0.015,  # 15ms
            AssetClass.ETF: 0.01,  # 10ms
            AssetClass.BOND: 0.05,  # 50ms
            AssetClass.OPTION: 0.03,  # 30ms
            AssetClass.FUTURE: 0.008,  # 8ms
        }
        return delays.get(asset_class, 0.01)
        
    async def _execute_order(self, order: Order, asset: Asset) -> Dict[str, Any]:
        """Simulate order execution"""
        market_data = self.asset_manager.get_market_data(order.symbol)
        
        # Determine execution price
        if order.order_type == OrderType.MARKET:
            if order.side == 'buy':
                execution_price = market_data['ask_price']
            else:
                execution_price = market_data['bid_price']
        elif order.order_type == OrderType.LIMIT:
            execution_price = order.price
        else:
            execution_price = market_data['last_price']
            
        # Simulate partial or full fill
        fill_probability = 0.95  # 95% chance of full fill
        if random.random() < fill_probability:
            # Full fill
            order.filled_quantity = order.quantity
            order.status = OrderStatus.FILLED
        else:
            # Partial fill
            fill_ratio = random.uniform(0.3, 0.8)
            order.filled_quantity = order.quantity * Decimal(str(fill_ratio))
            order.status = OrderStatus.PARTIALLY_FILLED
            
        order.average_fill_price = execution_price
        order.updated_at = datetime.now()
        
        # Calculate commission
        commission_rate = Decimal('0.001')  # 0.1%
        order.commission = order.filled_quantity * execution_price * commission_rate
        
        # Add to history
        self.order_history.append(order)
        
        return {
            'order_id': order.order_id,
            'status': order.status.value,
            'filled_quantity': order.filled_quantity,
            'average_fill_price': order.average_fill_price,
            'commission': order.commission,
            'execution_time': datetime.now().isoformat()
        }
        
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        if order_id not in self.orders:
            return False
            
        order = self.orders[order_id]
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
            return False
            
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now()
        
        logger.info(f"Order {order_id} cancelled")
        return True
        
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self.orders.get(order_id)
        
    def get_orders_by_symbol(self, symbol: str) -> List[Order]:
        """Get all orders for a symbol"""
        return [order for order in self.orders.values() if order.symbol == symbol]
        
    def get_orders_by_asset_class(self, asset_class: AssetClass) -> List[Order]:
        """Get all orders for an asset class"""
        return [order for order in self.orders.values() if order.asset_class == asset_class]
        
    def get_execution_statistics(self) -> Dict[str, Any]:
        """Get execution statistics by asset class"""
        stats = {}
        
        for asset_class, latencies in self.execution_latency.items():
            if latencies:
                stats[asset_class.value] = {
                    'count': len(latencies),
                    'avg_latency_ms': sum(latencies) / len(latencies) * 1000,
                    'min_latency_ms': min(latencies) * 1000,
                    'max_latency_ms': max(latencies) * 1000,
                    'p95_latency_ms': sorted(latencies)[int(len(latencies) * 0.95)] * 1000 if len(latencies) > 1 else latencies[0] * 1000
                }
                
        return stats


class MockPortfolioManager:
    """Mock portfolio manager for multi-asset trading"""
    
    def __init__(self, asset_manager: MockAssetManager):
        self.asset_manager = asset_manager
        self.portfolios = {}
        self.position_history = []
        
    def create_portfolio(self, portfolio_id: str, name: str, base_currency: str, initial_cash: Decimal) -> Portfolio:
        """Create a new portfolio"""
        portfolio = Portfolio(
            portfolio_id=portfolio_id,
            name=name,
            base_currency=base_currency,
            total_value=initial_cash,
            cash_balance=initial_cash,
            margin_available=initial_cash * Decimal('0.5')  # 50% margin
        )
        
        self.portfolios[portfolio_id] = portfolio
        logger.info(f"Created portfolio {portfolio_id} with {initial_cash} {base_currency}")
        
        return portfolio
        
    async def update_position(self, portfolio_id: str, order: Order) -> Position:
        """Update position based on order execution"""
        if portfolio_id not in self.portfolios:
            raise ValueError(f"Portfolio not found: {portfolio_id}")
            
        portfolio = self.portfolios[portfolio_id]
        symbol = order.symbol
        
        # Get or create position
        if symbol not in portfolio.positions:
            asset = self.asset_manager.get_asset(symbol)
            portfolio.positions[symbol] = Position(
                symbol=symbol,
                asset_class=asset.asset_class,
                quantity=Decimal('0'),
                average_price=Decimal('0'),
                market_value=Decimal('0'),
                unrealized_pnl=Decimal('0')
            )
            
        position = portfolio.positions[symbol]
        
        # Update position based on order
        if order.status == OrderStatus.FILLED and order.filled_quantity > 0:
            trade_value = order.filled_quantity * order.average_fill_price
            
            if order.side == 'buy':
                # Calculate new average price
                total_cost = (position.quantity * position.average_price) + trade_value
                new_quantity = position.quantity + order.filled_quantity
                
                if new_quantity > 0:
                    position.average_price = total_cost / new_quantity
                    
                position.quantity = new_quantity
                portfolio.cash_balance -= trade_value + order.commission
                
            else:  # sell
                # Calculate realized P&L
                if position.quantity > 0:
                    realized_pnl = (order.average_fill_price - position.average_price) * order.filled_quantity
                    position.realized_pnl += realized_pnl
                    portfolio.total_pnl += realized_pnl
                    
                position.quantity -= order.filled_quantity
                portfolio.cash_balance += trade_value - order.commission
                
            # Update market value and unrealized P&L
            await self._update_position_market_value(position)
            
            # Update portfolio totals
            await self._update_portfolio_totals(portfolio)
            
            position.last_updated = datetime.now()
            
            # Add to history
            self.position_history.append({
                'timestamp': datetime.now(),
                'portfolio_id': portfolio_id,
                'symbol': symbol,
                'action': order.side,
                'quantity': order.filled_quantity,
                'price': order.average_fill_price,
                'position_quantity': position.quantity,
                'realized_pnl': position.realized_pnl
            })
            
        return position
        
    async def _update_position_market_value(self, position: Position):
        """Update position market value and unrealized P&L"""
        market_data = self.asset_manager.get_market_data(position.symbol)
        if market_data and position.quantity != 0:
            current_price = market_data['last_price']
            position.market_value = position.quantity * current_price
            position.unrealized_pnl = (current_price - position.average_price) * position.quantity
        else:
            position.market_value = Decimal('0')
            position.unrealized_pnl = Decimal('0')
            
    async def _update_portfolio_totals(self, portfolio: Portfolio):
        """Update portfolio total values"""
        total_market_value = Decimal('0')
        total_unrealized_pnl = Decimal('0')
        
        for position in portfolio.positions.values():
            await self._update_position_market_value(position)
            total_market_value += position.market_value
            total_unrealized_pnl += position.unrealized_pnl
            
        portfolio.total_value = portfolio.cash_balance + total_market_value
        portfolio.daily_pnl = total_unrealized_pnl  # Simplified
        portfolio.last_updated = datetime.now()
        
    def get_portfolio(self, portfolio_id: str) -> Optional[Portfolio]:
        """Get portfolio by ID"""
        return self.portfolios.get(portfolio_id)
        
    def get_positions_by_asset_class(self, portfolio_id: str, asset_class: AssetClass) -> List[Position]:
        """Get positions by asset class"""
        if portfolio_id not in self.portfolios:
            return []
            
        portfolio = self.portfolios[portfolio_id]
        return [pos for pos in portfolio.positions.values() if pos.asset_class == asset_class]
        
    def get_portfolio_summary(self, portfolio_id: str) -> Dict[str, Any]:
        """Get portfolio summary"""
        portfolio = self.get_portfolio(portfolio_id)
        if not portfolio:
            return {}
            
        # Group positions by asset class
        positions_by_class = {}
        for position in portfolio.positions.values():
            asset_class = position.asset_class.value
            if asset_class not in positions_by_class:
                positions_by_class[asset_class] = {
                    'count': 0,
                    'total_value': Decimal('0'),
                    'total_pnl': Decimal('0')
                }
                
            positions_by_class[asset_class]['count'] += 1
            positions_by_class[asset_class]['total_value'] += position.market_value
            positions_by_class[asset_class]['total_pnl'] += position.unrealized_pnl + position.realized_pnl
            
        return {
            'portfolio_id': portfolio.portfolio_id,
            'name': portfolio.name,
            'base_currency': portfolio.base_currency,
            'total_value': portfolio.total_value,
            'cash_balance': portfolio.cash_balance,
            'total_positions': len(portfolio.positions),
            'positions_by_asset_class': positions_by_class,
            'daily_pnl': portfolio.daily_pnl,
            'total_pnl': portfolio.total_pnl,
            'last_updated': portfolio.last_updated.isoformat()
        }


class MockRiskManager:
    """Mock risk manager for multi-asset trading"""
    
    def __init__(self, portfolio_manager: MockPortfolioManager):
        self.portfolio_manager = portfolio_manager
        self.risk_limits = {
            'max_position_size': Decimal('0.1'),  # 10% of portfolio
            'max_asset_class_exposure': Decimal('0.3'),  # 30% per asset class
            'max_single_asset_exposure': Decimal('0.05'),  # 5% per asset
            'max_leverage': Decimal('2.0'),  # 2:1 leverage
            'max_daily_loss': Decimal('0.02'),  # 2% daily loss limit
        }
        self.risk_violations = []
        
    async def validate_order(self, portfolio_id: str, order: Order) -> Dict[str, Any]:
        """Validate order against risk limits"""
        portfolio = self.portfolio_manager.get_portfolio(portfolio_id)
        if not portfolio:
            return {'valid': False, 'reason': 'Portfolio not found'}
            
        violations = []
        
        # Check position size limit
        asset = self.portfolio_manager.asset_manager.get_asset(order.symbol)
        market_data = self.portfolio_manager.asset_manager.get_market_data(order.symbol)
        
        if asset and market_data:
            order_value = order.quantity * market_data['last_price']
            position_size_pct = order_value / portfolio.total_value
            
            if position_size_pct > self.risk_limits['max_position_size']:
                violations.append(f"Position size {position_size_pct:.2%} exceeds limit {self.risk_limits['max_position_size']:.2%}")
                
            # Check asset class exposure
            asset_class_positions = self.portfolio_manager.get_positions_by_asset_class(portfolio_id, asset.asset_class)
            current_exposure = sum(pos.market_value for pos in asset_class_positions)
            new_exposure_pct = (current_exposure + order_value) / portfolio.total_value
            
            if new_exposure_pct > self.risk_limits['max_asset_class_exposure']:
                violations.append(f"Asset class exposure {new_exposure_pct:.2%} exceeds limit {self.risk_limits['max_asset_class_exposure']:.2%}")
                
        # Check cash availability
        if order.side == 'buy':
            required_cash = order.quantity * (order.price or market_data['ask_price'])
            if required_cash > portfolio.cash_balance:
                violations.append(f"Insufficient cash: required {required_cash}, available {portfolio.cash_balance}")
                
        if violations:
            self.risk_violations.extend(violations)
            return {'valid': False, 'violations': violations}
            
        return {'valid': True}
        
    async def monitor_portfolio_risk(self, portfolio_id: str) -> Dict[str, Any]:
        """Monitor portfolio risk metrics"""
        portfolio = self.portfolio_manager.get_portfolio(portfolio_id)
        if not portfolio:
            return {}
            
        risk_metrics = {
            'portfolio_id': portfolio_id,
            'total_value': portfolio.total_value,
            'cash_percentage': (portfolio.cash_balance / portfolio.total_value) * 100,
            'daily_pnl_percentage': (portfolio.daily_pnl / portfolio.total_value) * 100,
            'position_count': len(portfolio.positions),
            'asset_class_distribution': {},
            'risk_violations': [],
            'risk_score': 0.0
        }
        
        # Calculate asset class distribution
        for position in portfolio.positions.values():
            asset_class = position.asset_class.value
            if asset_class not in risk_metrics['asset_class_distribution']:
                risk_metrics['asset_class_distribution'][asset_class] = Decimal('0')
            risk_metrics['asset_class_distribution'][asset_class] += position.market_value
            
        # Convert to percentages
        for asset_class in risk_metrics['asset_class_distribution']:
            risk_metrics['asset_class_distribution'][asset_class] = (
                risk_metrics['asset_class_distribution'][asset_class] / portfolio.total_value * 100
            )
            
        # Check for risk violations
        if risk_metrics['daily_pnl_percentage'] < -self.risk_limits['max_daily_loss'] * 100:
            risk_metrics['risk_violations'].append('Daily loss limit exceeded')
            
        # Calculate risk score (0-100, higher is riskier)
        risk_score = 0
        risk_score += min(abs(risk_metrics['daily_pnl_percentage']) * 10, 50)  # P&L volatility
        risk_score += max(0, (100 - risk_metrics['cash_percentage']) * 0.3)  # Cash buffer
        risk_score += len(risk_metrics['risk_violations']) * 20  # Violations penalty
        
        risk_metrics['risk_score'] = min(risk_score, 100)
        
        return risk_metrics
        
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get risk management summary"""
        return {
            'risk_limits': {k: float(v) for k, v in self.risk_limits.items()},
            'total_violations': len(self.risk_violations),
            'recent_violations': self.risk_violations[-10:] if self.risk_violations else []
        }


class TestMultiAssetTradingSystem:
    """Test suite for multi-asset trading system"""
    
    @pytest.fixture(autouse=True)
    async def setup_method(self):
        """Setup test environment"""
        self.asset_manager = MockAssetManager()
        self.order_manager = MockOrderManager(self.asset_manager)
        self.portfolio_manager = MockPortfolioManager(self.asset_manager)
        self.risk_manager = MockRiskManager(self.portfolio_manager)
        
        # Create test portfolio
        self.test_portfolio = self.portfolio_manager.create_portfolio(
            "TEST_PORTFOLIO_001",
            "Multi-Asset Test Portfolio",
            "USD",
            Decimal('1000000')  # $1M initial cash
        )
        
        logger.info("Multi-asset trading system test setup completed")
        
    async def teardown_method(self):
        """Cleanup test environment"""
        logger.info("Multi-asset trading system test cleanup completed")
        
    @pytest.mark.asyncio
    async def test_asset_manager_initialization(self):
        """Test asset manager initialization with multiple asset classes"""
        # Verify assets are loaded
        assert len(self.asset_manager.assets) > 0
        
        # Check asset classes are represented
        asset_classes = set(asset.asset_class for asset in self.asset_manager.assets.values())
        expected_classes = {AssetClass.EQUITY, AssetClass.FOREX, AssetClass.CRYPTOCURRENCY, AssetClass.COMMODITY, AssetClass.ETF, AssetClass.BOND}
        
        assert asset_classes.intersection(expected_classes) == expected_classes
        
        # Verify market data is available
        for symbol in self.asset_manager.assets.keys():
            market_data = self.asset_manager.get_market_data(symbol)
            assert market_data is not None
            assert 'last_price' in market_data
            assert 'bid_price' in market_data
            assert 'ask_price' in market_data
            
    @pytest.mark.asyncio
    async def test_equity_trading(self):
        """Test equity trading functionality"""
        # Get equity assets
        equity_assets = self.asset_manager.get_assets_by_class(AssetClass.EQUITY)
        assert len(equity_assets) > 0
        
        # Place equity order
        equity_symbol = equity_assets[0].symbol
        order = Order(
            order_id="",
            symbol=equity_symbol,
            asset_class=AssetClass.EQUITY,
            order_type=OrderType.MARKET,
            side="buy",
            quantity=Decimal('100')
        )
        
        result = await self.order_manager.place_order(order)
        
        assert result['status'] in ['filled', 'partially_filled']
        assert 'order_id' in result
        assert 'average_fill_price' in result
        
        # Update portfolio
        position = await self.portfolio_manager.update_position(self.test_portfolio.portfolio_id, order)
        
        assert position.symbol == equity_symbol
        assert position.asset_class == AssetClass.EQUITY
        assert position.quantity > 0
        
    @pytest.mark.asyncio
    async def test_forex_trading(self):
        """Test forex trading functionality"""
        # Get forex assets
        forex_assets = self.asset_manager.get_assets_by_class(AssetClass.FOREX)
        assert len(forex_assets) > 0
        
        # Place forex order
        forex_symbol = forex_assets[0].symbol
        order = Order(
            order_id="",
            symbol=forex_symbol,
            asset_class=AssetClass.FOREX,
            order_type=OrderType.LIMIT,
            side="buy",
            quantity=Decimal('10000'),  # Standard lot
            price=self.asset_manager.get_market_data(forex_symbol)['bid_price']
        )
        
        result = await self.order_manager.place_order(order)
        
        assert result['status'] in ['filled', 'partially_filled']
        
        # Update portfolio
        position = await self.portfolio_manager.update_position(self.test_portfolio.portfolio_id, order)
        
        assert position.symbol == forex_symbol
        assert position.asset_class == AssetClass.FOREX
        
    @pytest.mark.asyncio
    async def test_cryptocurrency_trading(self):
        """Test cryptocurrency trading functionality"""
        # Get crypto assets
        crypto_assets = self.asset_manager.get_assets_by_class(AssetClass.CRYPTOCURRENCY)
        assert len(crypto_assets) > 0
        
        # Place crypto order
        crypto_symbol = crypto_assets[0].symbol
        order = Order(
            order_id="",
            symbol=crypto_symbol,
            asset_class=AssetClass.CRYPTOCURRENCY,
            order_type=OrderType.MARKET,
            side="buy",
            quantity=Decimal('0.1')  # 0.1 BTC
        )
        
        result = await self.order_manager.place_order(order)
        
        assert result['status'] in ['filled', 'partially_filled']
        
        # Update portfolio
        position = await self.portfolio_manager.update_position(self.test_portfolio.portfolio_id, order)
        
        assert position.symbol == crypto_symbol
        assert position.asset_class == AssetClass.CRYPTOCURRENCY
        
    @pytest.mark.asyncio
    async def test_commodity_trading(self):
        """Test commodity trading functionality"""
        # Get commodity assets
        commodity_assets = self.asset_manager.get_assets_by_class(AssetClass.COMMODITY)
        assert len(commodity_assets) > 0
        
        # Place commodity order
        commodity_symbol = commodity_assets[0].symbol
        order = Order(
            order_id="",
            symbol=commodity_symbol,
            asset_class=AssetClass.COMMODITY,
            order_type=OrderType.MARKET,
            side="buy",
            quantity=Decimal('1')  # 1 oz gold
        )
        
        result = await self.order_manager.place_order(order)
        
        assert result['status'] in ['filled', 'partially_filled']
        
        # Update portfolio
        position = await self.portfolio_manager.update_position(self.test_portfolio.portfolio_id, order)
        
        assert position.symbol == commodity_symbol
        assert position.asset_class == AssetClass.COMMODITY
        
    @pytest.mark.asyncio
    async def test_multi_asset_portfolio(self):
        """Test portfolio with multiple asset classes"""
        # Place orders across different asset classes
        orders = [
            Order("", "AAPL", AssetClass.EQUITY, OrderType.MARKET, "buy", Decimal('50')),
            Order("", "EURUSD", AssetClass.FOREX, OrderType.MARKET, "buy", Decimal('5000')),
            Order("", "BTCUSD", AssetClass.CRYPTOCURRENCY, OrderType.MARKET, "buy", Decimal('0.05')),
            Order("", "XAUUSD", AssetClass.COMMODITY, OrderType.MARKET, "buy", Decimal('2')),
            Order("", "SPY", AssetClass.ETF, OrderType.MARKET, "buy", Decimal('25'))
        ]
        
        # Execute all orders
        for order in orders:
            result = await self.order_manager.place_order(order)
            assert result['status'] in ['filled', 'partially_filled']
            
            # Update portfolio
            await self.portfolio_manager.update_position(self.test_portfolio.portfolio_id, order)
            
        # Verify portfolio has positions in multiple asset classes
        portfolio_summary = self.portfolio_manager.get_portfolio_summary(self.test_portfolio.portfolio_id)
        
        assert portfolio_summary['total_positions'] == len(orders)
        assert len(portfolio_summary['positions_by_asset_class']) >= 4  # At least 4 different asset classes
        
        # Verify each asset class has positions
        expected_classes = ['equity', 'forex', 'cryptocurrency', 'commodity', 'etf']
        for asset_class in expected_classes:
            assert asset_class in portfolio_summary['positions_by_asset_class']
            
    @pytest.mark.asyncio
    async def test_cross_asset_risk_management(self):
        """Test risk management across multiple asset classes"""
        # Place large order that should trigger risk limits
        large_order = Order(
            order_id="",
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            order_type=OrderType.MARKET,
            side="buy",
            quantity=Decimal('10000')  # Large position
        )
        
        # Validate order against risk limits
        validation_result = await self.risk_manager.validate_order(self.test_portfolio.portfolio_id, large_order)
        
        # Should fail due to position size limit
        assert validation_result['valid'] is False
        assert 'violations' in validation_result
        assert len(validation_result['violations']) > 0
        
        # Test with reasonable order size
        reasonable_order = Order(
            order_id="",
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            order_type=OrderType.MARKET,
            side="buy",
            quantity=Decimal('100')
        )
        
        validation_result = await self.risk_manager.validate_order(self.test_portfolio.portfolio_id, reasonable_order)
        assert validation_result['valid'] is True
        
    @pytest.mark.asyncio
    async def test_execution_latency_by_asset_class(self):
        """Test execution latency varies by asset class"""
        # Place orders for different asset classes
        test_orders = [
            ("AAPL", AssetClass.EQUITY),
            ("EURUSD", AssetClass.FOREX),
            ("BTCUSD", AssetClass.CRYPTOCURRENCY),
            ("XAUUSD", AssetClass.COMMODITY)
        ]
        
        for symbol, asset_class in test_orders:
            order = Order(
                order_id="",
                symbol=symbol,
                asset_class=asset_class,
                order_type=OrderType.MARKET,
                side="buy",
                quantity=Decimal('1')
            )
            
            await self.order_manager.place_order(order)
            
        # Get execution statistics
        stats = self.order_manager.get_execution_statistics()
        
        # Verify statistics are collected for each asset class
        assert len(stats) > 0
        
        for asset_class_name, stat in stats.items():
            assert 'avg_latency_ms' in stat
            assert 'count' in stat
            assert stat['avg_latency_ms'] > 0
            assert stat['count'] > 0
            
        # Verify forex has lower latency than crypto (based on our mock delays)
        if 'forex' in stats and 'cryptocurrency' in stats:
            assert stats['forex']['avg_latency_ms'] < stats['cryptocurrency']['avg_latency_ms']
            
    @pytest.mark.asyncio
    async def test_concurrent_multi_asset_trading(self):
        """Test concurrent trading across multiple asset classes"""
        # Create orders for different asset classes
        concurrent_orders = [
            Order("", "AAPL", AssetClass.EQUITY, OrderType.MARKET, "buy", Decimal('10')),
            Order("", "GOOGL", AssetClass.EQUITY, OrderType.MARKET, "buy", Decimal('5')),
            Order("", "EURUSD", AssetClass.FOREX, OrderType.MARKET, "buy", Decimal('1000')),
            Order("", "GBPUSD", AssetClass.FOREX, OrderType.MARKET, "buy", Decimal('1000')),
            Order("", "BTCUSD", AssetClass.CRYPTOCURRENCY, OrderType.MARKET, "buy", Decimal('0.01')),
            Order("", "ETHUSD", AssetClass.CRYPTOCURRENCY, OrderType.MARKET, "buy", Decimal('0.1')),
        ]
        
        # Execute orders concurrently
        tasks = [self.order_manager.place_order(order) for order in concurrent_orders]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all orders executed successfully
        assert len(results) == len(concurrent_orders)
        
        for result in results:
            assert not isinstance(result, Exception)
            assert result['status'] in ['filled', 'partially_filled']
            
        # Update portfolio positions
        for order in concurrent_orders:
            await self.portfolio_manager.update_position(self.test_portfolio.portfolio_id, order)
            
        # Verify portfolio state
        portfolio_summary = self.portfolio_manager.get_portfolio_summary(self.test_portfolio.portfolio_id)
        assert portfolio_summary['total_positions'] == len(concurrent_orders)
        
    @pytest.mark.asyncio
    async def test_market_data_updates_across_assets(self):
        """Test market data updates across different asset classes"""
        # Get initial market data
        test_symbols = ["AAPL", "EURUSD", "BTCUSD", "XAUUSD"]
        initial_prices = {}
        
        for symbol in test_symbols:
            market_data = self.asset_manager.get_market_data(symbol)
            initial_prices[symbol] = market_data['last_price']
            
        # Update market data
        for symbol in test_symbols:
            self.asset_manager.update_market_data(symbol, 0.01)  # 1% price increase
            
        # Verify prices updated
        for symbol in test_symbols:
            market_data = self.asset_manager.get_market_data(symbol)
            new_price = market_data['last_price']
            
            assert new_price != initial_prices[symbol]
            assert new_price > initial_prices[symbol]  # Should be higher due to 1% increase
            
    @pytest.mark.asyncio
    async def test_portfolio_risk_monitoring(self):
        """Test portfolio risk monitoring across asset classes"""
        # Build diversified portfolio
        orders = [
            Order("", "AAPL", AssetClass.EQUITY, OrderType.MARKET, "buy", Decimal('100')),
            Order("", "EURUSD", AssetClass.FOREX, OrderType.MARKET, "buy", Decimal('10000')),
            Order("", "BTCUSD", AssetClass.CRYPTOCURRENCY, OrderType.MARKET, "buy", Decimal('0.1')),
            Order("", "XAUUSD", AssetClass.COMMODITY, OrderType.MARKET, "buy", Decimal('5')),
        ]
        
        # Execute orders and update positions
        for order in orders:
            await self.order_manager.place_order(order)
            await self.portfolio_manager.update_position(self.test_portfolio.portfolio_id, order)
            
        # Monitor portfolio risk
        risk_metrics = await self.risk_manager.monitor_portfolio_risk(self.test_portfolio.portfolio_id)
        
        assert 'portfolio_id' in risk_metrics
        assert 'total_value' in risk_metrics
        assert 'asset_class_distribution' in risk_metrics
        assert 'risk_score' in risk_metrics
        
        # Verify asset class distribution
        distribution = risk_metrics['asset_class_distribution']
        assert len(distribution) >= 3  # At least 3 asset classes
        
        # Verify risk score is calculated
        assert 0 <= risk_metrics['risk_score'] <= 100
        
    @pytest.mark.asyncio
    async def test_order_validation_by_asset_class(self):
        """Test order validation rules specific to asset classes"""
        # Test equity order validation
        equity_asset = self.asset_manager.get_asset("AAPL")
        
        # Invalid quantity (below lot size)
        invalid_order = Order(
            order_id="",
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            order_type=OrderType.MARKET,
            side="buy",
            quantity=Decimal('0.5')  # Below lot size of 1
        )
        
        with pytest.raises(ValueError, match="Quantity below minimum lot size"):
            await self.order_manager.place_order(invalid_order)
            
        # Test forex order validation
        forex_asset = self.asset_manager.get_asset("EURUSD")
        
        # Invalid quantity (not multiple of lot size)
        invalid_forex_order = Order(
            order_id="",
            symbol="EURUSD",
            asset_class=AssetClass.FOREX,
            order_type=OrderType.MARKET,
            side="buy",
            quantity=Decimal('1500')  # Not multiple of 1000
        )
        
        with pytest.raises(ValueError, match="Quantity must be multiple of lot size"):
            await self.order_manager.place_order(invalid_forex_order)
            
    @pytest.mark.asyncio
    async def test_performance_across_asset_classes(self):
        """Test system performance across different asset classes"""
        # Measure execution time for each asset class
        asset_class_performance = {}
        
        test_cases = [
            ("AAPL", AssetClass.EQUITY),
            ("EURUSD", AssetClass.FOREX),
            ("BTCUSD", AssetClass.CRYPTOCURRENCY),
            ("XAUUSD", AssetClass.COMMODITY),
            ("SPY", AssetClass.ETF)
        ]
        
        for symbol, asset_class in test_cases:
            start_time = time.time()
            
            order = Order(
                order_id="",
                symbol=symbol,
                asset_class=asset_class,
                order_type=OrderType.MARKET,
                side="buy",
                quantity=Decimal('1')
            )
            
            await self.order_manager.place_order(order)
            
            execution_time = time.time() - start_time
            asset_class_performance[asset_class.value] = execution_time
            
        # Verify all executions completed within reasonable time
        for asset_class, exec_time in asset_class_performance.items():
            assert exec_time < 1.0  # Should complete within 1 second
            
        logger.info(f"Asset class performance: {asset_class_performance}")
        
    @pytest.mark.asyncio
    async def test_system_scalability_multi_asset(self):
        """Test system scalability with multiple asset classes"""
        # Create large number of orders across asset classes
        num_orders_per_class = 10
        asset_symbols = {
            AssetClass.EQUITY: ["AAPL", "GOOGL", "TSLA"],
            AssetClass.FOREX: ["EURUSD", "GBPUSD", "USDJPY"],
            AssetClass.CRYPTOCURRENCY: ["BTCUSD", "ETHUSD", "ADAUSD"]
        }
        
        all_orders = []
        
        for asset_class, symbols in asset_symbols.items():
            for i in range(num_orders_per_class):
                symbol = symbols[i % len(symbols)]
                order = Order(
                    order_id="",
                    symbol=symbol,
                    asset_class=asset_class,
                    order_type=OrderType.MARKET,
                    side="buy" if i % 2 == 0 else "sell",
                    quantity=Decimal('1')
                )
                all_orders.append(order)
                
        # Execute orders in batches
        batch_size = 5
        start_time = time.time()
        
        for i in range(0, len(all_orders), batch_size):
            batch = all_orders[i:i + batch_size]
            tasks = [self.order_manager.place_order(order) for order in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
            
        total_time = time.time() - start_time
        
        # Verify performance
        orders_per_second = len(all_orders) / total_time
        assert orders_per_second > 10  # Should handle at least 10 orders per second
        
        logger.info(f"Processed {len(all_orders)} orders in {total_time:.2f}s ({orders_per_second:.1f} orders/sec)")
        
    @pytest.mark.asyncio
    async def test_end_to_end_multi_asset_workflow(self):
        """Test complete end-to-end multi-asset trading workflow"""
        # 1. Initialize portfolio
        portfolio_id = self.test_portfolio.portfolio_id
        initial_cash = self.test_portfolio.cash_balance
        
        # 2. Place diversified orders
        trading_plan = [
            {"symbol": "AAPL", "asset_class": AssetClass.EQUITY, "quantity": Decimal('50'), "side": "buy"},
            {"symbol": "EURUSD", "asset_class": AssetClass.FOREX, "quantity": Decimal('5000'), "side": "buy"},
            {"symbol": "BTCUSD", "asset_class": AssetClass.CRYPTOCURRENCY, "quantity": Decimal('0.1'), "side": "buy"},
            {"symbol": "XAUUSD", "asset_class": AssetClass.COMMODITY, "quantity": Decimal('2'), "side": "buy"},
            {"symbol": "SPY", "asset_class": AssetClass.ETF, "quantity": Decimal('25'), "side": "buy"}
        ]
        
        executed_orders = []
        
        for plan in trading_plan:
            # 3. Risk validation
            order = Order(
                order_id="",
                symbol=plan["symbol"],
                asset_class=plan["asset_class"],
                order_type=OrderType.MARKET,
                side=plan["side"],
                quantity=plan["quantity"]
            )
            
            risk_validation = await self.risk_manager.validate_order(portfolio_id, order)
            assert risk_validation['valid'] is True
            
            # 4. Order execution
            execution_result = await self.order_manager.place_order(order)
            assert execution_result['status'] in ['filled', 'partially_filled']
            
            # 5. Portfolio update
            position = await self.portfolio_manager.update_position(portfolio_id, order)
            assert position.quantity > 0
            
            executed_orders.append(order)
            
        # 6. Portfolio analysis
        portfolio_summary = self.portfolio_manager.get_portfolio_summary(portfolio_id)
        
        assert portfolio_summary['total_positions'] == len(trading_plan)
        assert portfolio_summary['cash_balance'] < initial_cash  # Cash should be reduced
        assert len(portfolio_summary['positions_by_asset_class']) == len(set(plan["asset_class"] for plan in trading_plan))
        
        # 7. Risk monitoring
        risk_metrics = await self.risk_manager.monitor_portfolio_risk(portfolio_id)
        
        assert risk_metrics['portfolio_id'] == portfolio_id
        assert len(risk_metrics['asset_class_distribution']) >= 4
        assert risk_metrics['risk_score'] >= 0
        
        # 8. Performance analysis
        execution_stats = self.order_manager.get_execution_statistics()
        assert len(execution_stats) > 0
        
        # 9. Simulate market movements and rebalancing
        for symbol in ["AAPL", "EURUSD", "BTCUSD"]:
            self.asset_manager.update_market_data(symbol, random.uniform(-0.02, 0.02))
            
        # 10. Final portfolio valuation
        await self.portfolio_manager._update_portfolio_totals(self.test_portfolio)
        final_summary = self.portfolio_manager.get_portfolio_summary(portfolio_id)
        
        assert final_summary['total_value'] > 0
        
        logger.info(f"End-to-end workflow completed successfully")
        logger.info(f"Portfolio value: {final_summary['total_value']}")
        logger.info(f"Asset class distribution: {final_summary['positions_by_asset_class']}")
        
        # Verify workflow success
        assert final_summary['total_positions'] == len(trading_plan)
        assert len(final_summary['positions_by_asset_class']) >= 4
        

if __name__ == "__main__":
    pytest.main([__file__, "-v"])