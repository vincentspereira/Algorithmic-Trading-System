"""
Base Asset Class Framework
Core abstractions and interfaces for multi-asset class trading
"""

import asyncio
import logging
import numpy as np
from typing import Dict, List, Optional, Any, Union, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, time, timedelta
from abc import ABC, abstractmethod
from decimal import Decimal


class AssetClass(Enum):
    """Asset class enumeration"""
    EQUITY = "equity"
    OPTION = "option"
    FUTURE = "future"
    BOND = "bond"
    FOREX = "forex"
    CRYPTO = "crypto"
    COMMODITY = "commodity"
    ETF = "etf"
    MUTUAL_FUND = "mutual_fund"


class AssetType(Enum):
    """Asset type enumeration"""
    STOCK = "stock"
    CALL_OPTION = "call_option"
    PUT_OPTION = "put_option"
    FUTURE_CONTRACT = "future_contract"
    GOVERNMENT_BOND = "government_bond"
    CORPORATE_BOND = "corporate_bond"
    CURRENCY_PAIR = "currency_pair"
    CRYPTOCURRENCY = "cryptocurrency"


class TradingSession(Enum):
    """Trading session enumeration"""
    PRE_MARKET = "pre_market"
    REGULAR = "regular"
    AFTER_HOURS = "after_hours"
    EXTENDED = "extended"
    CLOSED = "closed"


class MarketDataType(Enum):
    """Market data type enumeration"""
    TRADE = "trade"
    QUOTE = "quote"
    DEPTH = "depth"
    IMBALANCE = "imbalance"
    NEWS = "news"
    CORPORATE_ACTION = "corporate_action"


@dataclass
class TradingHours:
    """Trading hours specification"""
    pre_market_open: Optional[time] = None
    pre_market_close: Optional[time] = None
    regular_open: time = time(9, 30)
    regular_close: time = time(16, 0)
    after_hours_open: Optional[time] = None
    after_hours_close: Optional[time] = None
    timezone: str = "US/Eastern"


@dataclass
class MarketInfo:
    """Market information"""
    market_id: str
    name: str
    country: str
    currency: str
    trading_hours: TradingHours
    tick_size: Decimal
    lot_size: int = 1
    settlement_days: int = 2


@dataclass
class PriceData:
    """Price data structure"""
    symbol: str
    timestamp: datetime
    price: Decimal
    volume: int
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None


class BaseAsset(ABC):
    """Abstract base class for all tradeable assets"""
    
    def __init__(self,
                 symbol: str,
                 asset_class: AssetClass,
                 asset_type: AssetType,
                 market_info: MarketInfo,
                 **kwargs):
        self.symbol = symbol
        self.asset_class = asset_class
        self.asset_type = asset_type
        self.market_info = market_info
        
        # Common asset properties
        self.name = kwargs.get('name', symbol)
        self.description = kwargs.get('description', '')
        self.currency = kwargs.get('currency', market_info.currency)
        self.is_active = kwargs.get('is_active', True)
        
        # Trading properties
        self.min_order_size = kwargs.get('min_order_size', Decimal('1'))
        self.max_order_size = kwargs.get('max_order_size', Decimal('1000000'))
        self.price_increment = kwargs.get('price_increment', market_info.tick_size)
        
        # Risk properties
        self.margin_requirement = kwargs.get('margin_requirement', Decimal('0'))
        self.position_limit = kwargs.get('position_limit', None)
        
        # Metadata
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.metadata = kwargs.get('metadata', {})
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def validate_order(self, order_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate order for this asset type"""
        pass
    
    @abstractmethod
    def calculate_margin_requirement(self, quantity: int, price: Decimal) -> Decimal:
        """Calculate margin requirement for position"""
        pass
    
    @abstractmethod
    def get_market_value(self, quantity: int, current_price: Decimal) -> Decimal:
        """Calculate market value of position"""
        pass
    
    @abstractmethod
    def is_tradeable(self, current_time: datetime) -> bool:
        """Check if asset is tradeable at given time"""
        pass
    
    def get_trading_session(self, current_time: datetime) -> TradingSession:
        """Get current trading session"""
        current_time_only = current_time.time()
        hours = self.market_info.trading_hours
        
        if hours.pre_market_open and hours.pre_market_close:
            if hours.pre_market_open <= current_time_only < hours.pre_market_close:
                return TradingSession.PRE_MARKET
        
        if hours.regular_open <= current_time_only < hours.regular_close:
            return TradingSession.REGULAR
        
        if hours.after_hours_open and hours.after_hours_close:
            if hours.after_hours_open <= current_time_only < hours.after_hours_close:
                return TradingSession.AFTER_HOURS
        
        return TradingSession.CLOSED
    
    def round_price(self, price: Decimal) -> Decimal:
        """Round price to valid increment"""
        if self.price_increment <= 0:
            return price
        
        return (price / self.price_increment).quantize(Decimal('1')) * self.price_increment
    
    def validate_quantity(self, quantity: int) -> Tuple[bool, Optional[str]]:
        """Validate order quantity"""
        if quantity <= 0:
            return False, "Quantity must be positive"
        
        if quantity < self.min_order_size:
            return False, f"Quantity below minimum: {self.min_order_size}"
        
        if quantity > self.max_order_size:
            return False, f"Quantity above maximum: {self.max_order_size}"
        
        if quantity % self.market_info.lot_size != 0:
            return False, f"Quantity must be multiple of lot size: {self.market_info.lot_size}"
        
        return True, None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert asset to dictionary"""
        return {
            'symbol': self.symbol,
            'asset_class': self.asset_class.value,
            'asset_type': self.asset_type.value,
            'name': self.name,
            'description': self.description,
            'currency': self.currency,
            'is_active': self.is_active,
            'min_order_size': float(self.min_order_size),
            'max_order_size': float(self.max_order_size),
            'price_increment': float(self.price_increment),
            'margin_requirement': float(self.margin_requirement),
            'position_limit': float(self.position_limit) if self.position_limit else None,
            'market_info': {
                'market_id': self.market_info.market_id,
                'name': self.market_info.name,
                'country': self.market_info.country,
                'currency': self.market_info.currency,
                'tick_size': float(self.market_info.tick_size),
                'lot_size': self.market_info.lot_size,
                'settlement_days': self.market_info.settlement_days
            },
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'metadata': self.metadata
        }
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.symbol})"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(symbol='{self.symbol}', asset_class={self.asset_class}, asset_type={self.asset_type})"


class AssetManager:
    """Asset manager for multi-asset class trading"""
    
    def __init__(self):
        self.assets: Dict[str, BaseAsset] = {}
        self.asset_classes: Dict[AssetClass, List[BaseAsset]] = {}
        self.market_data_handlers: Dict[AssetClass, Callable] = {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize asset class lists
        for asset_class in AssetClass:
            self.asset_classes[asset_class] = []
    
    def register_asset(self, asset: BaseAsset) -> bool:
        """Register a new asset"""
        try:
            if asset.symbol in self.assets:
                self.logger.warning(f"Asset {asset.symbol} already registered, updating...")
            
            self.assets[asset.symbol] = asset
            
            # Add to asset class list
            if asset not in self.asset_classes[asset.asset_class]:
                self.asset_classes[asset.asset_class].append(asset)
            
            self.logger.info(f"Registered asset: {asset.symbol} ({asset.asset_class.value})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register asset {asset.symbol}: {e}")
            return False
    
    def unregister_asset(self, symbol: str) -> bool:
        """Unregister an asset"""
        try:
            if symbol not in self.assets:
                self.logger.warning(f"Asset {symbol} not found for unregistration")
                return False
            
            asset = self.assets[symbol]
            
            # Remove from asset class list
            if asset in self.asset_classes[asset.asset_class]:
                self.asset_classes[asset.asset_class].remove(asset)
            
            # Remove from main registry
            del self.assets[symbol]
            
            self.logger.info(f"Unregistered asset: {symbol}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unregister asset {symbol}: {e}")
            return False
    
    def get_asset(self, symbol: str) -> Optional[BaseAsset]:
        """Get asset by symbol"""
        return self.assets.get(symbol)
    
    def get_assets_by_class(self, asset_class: AssetClass) -> List[BaseAsset]:
        """Get all assets of a specific class"""
        return self.asset_classes.get(asset_class, []).copy()
    
    def get_assets_by_type(self, asset_type: AssetType) -> List[BaseAsset]:
        """Get all assets of a specific type"""
        return [asset for asset in self.assets.values() if asset.asset_type == asset_type]
    
    def get_tradeable_assets(self, current_time: datetime = None) -> List[BaseAsset]:
        """Get all currently tradeable assets"""
        if current_time is None:
            current_time = datetime.now()
        
        return [asset for asset in self.assets.values() 
                if asset.is_active and asset.is_tradeable(current_time)]
    
    def validate_order_for_asset(self, symbol: str, order_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate order for specific asset"""
        asset = self.get_asset(symbol)
        if not asset:
            return False, f"Asset {symbol} not found"
        
        if not asset.is_active:
            return False, f"Asset {symbol} is not active"
        
        return asset.validate_order(order_data)
    
    def calculate_portfolio_margin(self, positions: Dict[str, Tuple[int, Decimal]]) -> Decimal:
        """Calculate total margin requirement for portfolio"""
        total_margin = Decimal('0')
        
        for symbol, (quantity, price) in positions.items():
            asset = self.get_asset(symbol)
            if asset:
                margin = asset.calculate_margin_requirement(quantity, price)
                total_margin += margin
        
        return total_margin
    
    def get_portfolio_market_value(self, positions: Dict[str, Tuple[int, Decimal]]) -> Decimal:
        """Calculate total market value of portfolio"""
        total_value = Decimal('0')
        
        for symbol, (quantity, price) in positions.items():
            asset = self.get_asset(symbol)
            if asset:
                value = asset.get_market_value(quantity, price)
                total_value += value
        
        return total_value
    
    def register_market_data_handler(self, asset_class: AssetClass, handler: Callable):
        """Register market data handler for asset class"""
        self.market_data_handlers[asset_class] = handler
        self.logger.info(f"Registered market data handler for {asset_class.value}")
    
    def process_market_data(self, symbol: str, data: PriceData):
        """Process market data for asset"""
        asset = self.get_asset(symbol)
        if not asset:
            return
        
        handler = self.market_data_handlers.get(asset.asset_class)
        if handler:
            try:
                handler(asset, data)
            except Exception as e:
                self.logger.error(f"Market data handler failed for {symbol}: {e}")
    
    def get_asset_statistics(self) -> Dict[str, Any]:
        """Get asset registry statistics"""
        stats = {
            'total_assets': len(self.assets),
            'by_class': {},
            'by_type': {},
            'active_assets': sum(1 for asset in self.assets.values() if asset.is_active),
            'tradeable_assets': len(self.get_tradeable_assets())
        }
        
        # Count by asset class
        for asset_class in AssetClass:
            count = len(self.asset_classes[asset_class])
            if count > 0:
                stats['by_class'][asset_class.value] = count
        
        # Count by asset type
        type_counts = {}
        for asset in self.assets.values():
            asset_type = asset.asset_type.value
            type_counts[asset_type] = type_counts.get(asset_type, 0) + 1
        
        stats['by_type'] = type_counts
        
        return stats
    
    def export_assets(self) -> List[Dict[str, Any]]:
        """Export all assets to dictionary format"""
        return [asset.to_dict() for asset in self.assets.values()]
    
    def clear_assets(self):
        """Clear all registered assets"""
        self.assets.clear()
        for asset_class in AssetClass:
            self.asset_classes[asset_class].clear()
        self.logger.info("Cleared all registered assets")


# Global asset manager instance
_asset_manager: Optional[AssetManager] = None


def get_asset_manager() -> AssetManager:
    """Get or create the global asset manager instance"""
    global _asset_manager
    
    if _asset_manager is None:
        _asset_manager = AssetManager()
    
    return _asset_manager


# Utility functions
def create_market_info(market_id: str,
                      name: str,
                      country: str,
                      currency: str,
                      tick_size: Union[float, Decimal],
                      **kwargs) -> MarketInfo:
    """Convenience function to create market info"""
    trading_hours = TradingHours(
        pre_market_open=kwargs.get('pre_market_open'),
        pre_market_close=kwargs.get('pre_market_close'),
        regular_open=kwargs.get('regular_open', time(9, 30)),
        regular_close=kwargs.get('regular_close', time(16, 0)),
        after_hours_open=kwargs.get('after_hours_open'),
        after_hours_close=kwargs.get('after_hours_close'),
        timezone=kwargs.get('timezone', 'US/Eastern')
    )
    
    return MarketInfo(
        market_id=market_id,
        name=name,
        country=country,
        currency=currency,
        trading_hours=trading_hours,
        tick_size=Decimal(str(tick_size)),
        lot_size=kwargs.get('lot_size', 1),
        settlement_days=kwargs.get('settlement_days', 2)
    )


def create_price_data(symbol: str,
                     price: Union[float, Decimal],
                     volume: int,
                     timestamp: datetime = None,
                     **kwargs) -> PriceData:
    """Convenience function to create price data"""
    return PriceData(
        symbol=symbol,
        timestamp=timestamp or datetime.now(),
        price=Decimal(str(price)),
        volume=volume,
        bid=Decimal(str(kwargs['bid'])) if 'bid' in kwargs else None,
        ask=Decimal(str(kwargs['ask'])) if 'ask' in kwargs else None,
        bid_size=kwargs.get('bid_size'),
        ask_size=kwargs.get('ask_size')
    )