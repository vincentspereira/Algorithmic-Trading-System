"""
Equity Asset Implementation
Equity-specific trading logic, dividend handling, and corporate actions
"""

import asyncio
import logging
import numpy as np
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, date
from decimal import Decimal

from .asset_base import (
    BaseAsset, AssetClass, AssetType, MarketInfo, PriceData,
    TradingSession
)


class CorporateActionType(Enum):
    """Corporate action types"""
    DIVIDEND = "dividend"
    STOCK_SPLIT = "stock_split"
    STOCK_DIVIDEND = "stock_dividend"
    SPIN_OFF = "spin_off"
    MERGER = "merger"
    RIGHTS_OFFERING = "rights_offering"
    SPECIAL_DIVIDEND = "special_dividend"
    RETURN_OF_CAPITAL = "return_of_capital"


@dataclass
class DividendInfo:
    """Dividend information"""
    symbol: str
    ex_date: date
    record_date: date
    payment_date: date
    amount: Decimal
    currency: str
    dividend_type: str = "regular"  # regular, special, interim, final
    frequency: str = "quarterly"  # monthly, quarterly, semi-annual, annual
    
    @property
    def is_upcoming(self) -> bool:
        """Check if dividend is upcoming"""
        return self.ex_date > date.today()
    
    @property
    def days_to_ex_date(self) -> int:
        """Days until ex-dividend date"""
        return (self.ex_date - date.today()).days


@dataclass
class CorporateAction:
    """Corporate action information"""
    symbol: str
    action_type: CorporateActionType
    announcement_date: date
    ex_date: date
    record_date: Optional[date] = None
    effective_date: Optional[date] = None
    
    # Action-specific data
    ratio: Optional[str] = None  # e.g., "2:1" for stock split
    amount: Optional[Decimal] = None  # e.g., dividend amount
    new_symbol: Optional[str] = None  # e.g., for spin-offs
    description: str = ""
    
    @property
    def is_upcoming(self) -> bool:
        """Check if corporate action is upcoming"""
        return self.ex_date > date.today()
    
    @property
    def days_to_ex_date(self) -> int:
        """Days until ex-date"""
        return (self.ex_date - date.today()).days


class EquityAsset(BaseAsset):
    """Equity asset implementation"""
    
    def __init__(self,
                 symbol: str,
                 market_info: MarketInfo,
                 **kwargs):
        super().__init__(
            symbol=symbol,
            asset_class=AssetClass.EQUITY,
            asset_type=AssetType.STOCK,
            market_info=market_info,
            **kwargs
        )
        
        # Equity-specific properties
        self.company_name = kwargs.get('company_name', '')
        self.sector = kwargs.get('sector', '')
        self.industry = kwargs.get('industry', '')
        self.market_cap = kwargs.get('market_cap', Decimal('0'))
        self.shares_outstanding = kwargs.get('shares_outstanding', 0)
        
        # Trading properties
        self.is_shortable = kwargs.get('is_shortable', True)
        self.short_locate_required = kwargs.get('short_locate_required', False)
        self.day_trading_buying_power = kwargs.get('day_trading_buying_power', Decimal('4'))
        
        # Dividend and corporate action tracking
        self.dividends: List[DividendInfo] = []
        self.corporate_actions: List[CorporateAction] = []
        
        # Risk metrics
        self.beta = kwargs.get('beta', Decimal('1.0'))
        self.volatility = kwargs.get('volatility', Decimal('0.20'))
        
    def validate_order(self, order_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate equity order"""
        # Basic quantity validation
        quantity = order_data.get('quantity', 0)
        is_valid, error_msg = self.validate_quantity(abs(quantity))
        if not is_valid:
            return False, error_msg
        
        # Check if short selling is allowed
        if quantity < 0 and not self.is_shortable:
            return False, f"Short selling not allowed for {self.symbol}"
        
        # Check short locate requirement
        if quantity < 0 and self.short_locate_required:
            if not order_data.get('short_locate_exempt', False):
                return False, f"Short locate required for {self.symbol}"
        
        # Price validation
        price = order_data.get('price')
        if price is not None:
            price = Decimal(str(price))
            if price <= 0:
                return False, "Price must be positive"
            
            # Check minimum price increment
            rounded_price = self.round_price(price)
            if rounded_price != price:
                return False, f"Price must be in increments of {self.price_increment}"
        
        # Order type validation
        order_type = order_data.get('order_type', 'market')
        if order_type not in ['market', 'limit', 'stop', 'stop_limit']:
            return False, f"Invalid order type: {order_type}"
        
        # Time in force validation
        time_in_force = order_data.get('time_in_force', 'day')
        if time_in_force not in ['day', 'gtc', 'ioc', 'fok']:
            return False, f"Invalid time in force: {time_in_force}"
        
        return True, None
    
    def calculate_margin_requirement(self, quantity: int, price: Decimal) -> Decimal:
        """Calculate margin requirement for equity position"""
        market_value = abs(quantity) * price
        
        if quantity > 0:  # Long position
            # Reg T margin requirement (50% for most stocks)
            return market_value * Decimal('0.5')
        else:  # Short position
            # Short margin requirement (150% of market value)
            return market_value * Decimal('1.5')
    
    def get_market_value(self, quantity: int, current_price: Decimal) -> Decimal:
        """Calculate market value of equity position"""
        return quantity * current_price
    
    def is_tradeable(self, current_time: datetime) -> bool:
        """Check if equity is tradeable"""
        if not self.is_active:
            return False
        
        session = self.get_trading_session(current_time)
        
        # Most equities are tradeable during regular and extended hours
        return session in [TradingSession.PRE_MARKET, TradingSession.REGULAR, TradingSession.AFTER_HOURS]
    
    def add_dividend(self, dividend: DividendInfo):
        """Add dividend information"""
        # Remove existing dividend with same ex-date
        self.dividends = [d for d in self.dividends if d.ex_date != dividend.ex_date]
        self.dividends.append(dividend)
        self.dividends.sort(key=lambda d: d.ex_date, reverse=True)
        self.logger.info(f"Added dividend for {self.symbol}: ${dividend.amount} ex-date {dividend.ex_date}")
    
    def add_corporate_action(self, action: CorporateAction):
        """Add corporate action information"""
        # Remove existing action with same ex-date and type
        self.corporate_actions = [
            a for a in self.corporate_actions 
            if not (a.ex_date == action.ex_date and a.action_type == action.action_type)
        ]
        self.corporate_actions.append(action)
        self.corporate_actions.sort(key=lambda a: a.ex_date, reverse=True)
        self.logger.info(f"Added corporate action for {self.symbol}: {action.action_type.value} ex-date {action.ex_date}")
    
    def get_upcoming_dividends(self, days_ahead: int = 30) -> List[DividendInfo]:
        """Get upcoming dividends within specified days"""
        cutoff_date = date.today() + datetime.timedelta(days=days_ahead)
        return [d for d in self.dividends if d.ex_date <= cutoff_date and d.is_upcoming]
    
    def get_upcoming_corporate_actions(self, days_ahead: int = 30) -> List[CorporateAction]:
        """Get upcoming corporate actions within specified days"""
        cutoff_date = date.today() + datetime.timedelta(days=days_ahead)
        return [a for a in self.corporate_actions if a.ex_date <= cutoff_date and a.is_upcoming]
    
    def get_annual_dividend_yield(self, current_price: Decimal) -> Decimal:
        """Calculate annual dividend yield"""
        if current_price <= 0:
            return Decimal('0')
        
        # Get dividends from last 12 months
        one_year_ago = date.today() - datetime.timedelta(days=365)
        recent_dividends = [d for d in self.dividends if d.ex_date >= one_year_ago]
        
        annual_dividend = sum(d.amount for d in recent_dividends)
        return (annual_dividend / current_price) * 100  # Return as percentage
    
    def adjust_for_corporate_action(self, action: CorporateAction, quantity: int, price: Decimal) -> Tuple[int, Decimal]:
        """Adjust position for corporate action"""
        if action.action_type == CorporateActionType.STOCK_SPLIT:
            if action.ratio:
                # Parse ratio like "2:1" or "3:2"
                parts = action.ratio.split(':')
                if len(parts) == 2:
                    new_shares = int(parts[0])
                    old_shares = int(parts[1])
                    split_ratio = new_shares / old_shares
                    
                    new_quantity = int(quantity * split_ratio)
                    new_price = price / Decimal(str(split_ratio))
                    
                    return new_quantity, new_price
        
        elif action.action_type == CorporateActionType.STOCK_DIVIDEND:
            if action.ratio:
                # Parse ratio like "10%" or "0.1:1"
                if '%' in action.ratio:
                    dividend_rate = Decimal(action.ratio.replace('%', '')) / 100
                else:
                    parts = action.ratio.split(':')
                    if len(parts) == 2:
                        dividend_rate = Decimal(parts[0]) / Decimal(parts[1])
                    else:
                        dividend_rate = Decimal('0')
                
                additional_shares = int(quantity * dividend_rate)
                new_quantity = quantity + additional_shares
                new_price = price * quantity / new_quantity  # Adjust price to maintain market value
                
                return new_quantity, new_price
        
        # Return unchanged if action type not handled
        return quantity, price
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert equity asset to dictionary"""
        base_dict = super().to_dict()
        base_dict.update({
            'company_name': self.company_name,
            'sector': self.sector,
            'industry': self.industry,
            'market_cap': float(self.market_cap),
            'shares_outstanding': self.shares_outstanding,
            'is_shortable': self.is_shortable,
            'short_locate_required': self.short_locate_required,
            'day_trading_buying_power': float(self.day_trading_buying_power),
            'beta': float(self.beta),
            'volatility': float(self.volatility),
            'dividends': [
                {
                    'ex_date': d.ex_date.isoformat(),
                    'record_date': d.record_date.isoformat(),
                    'payment_date': d.payment_date.isoformat(),
                    'amount': float(d.amount),
                    'currency': d.currency,
                    'dividend_type': d.dividend_type,
                    'frequency': d.frequency
                }
                for d in self.dividends
            ],
            'corporate_actions': [
                {
                    'action_type': a.action_type.value,
                    'announcement_date': a.announcement_date.isoformat(),
                    'ex_date': a.ex_date.isoformat(),
                    'record_date': a.record_date.isoformat() if a.record_date else None,
                    'effective_date': a.effective_date.isoformat() if a.effective_date else None,
                    'ratio': a.ratio,
                    'amount': float(a.amount) if a.amount else None,
                    'new_symbol': a.new_symbol,
                    'description': a.description
                }
                for a in self.corporate_actions
            ]
        })
        return base_dict