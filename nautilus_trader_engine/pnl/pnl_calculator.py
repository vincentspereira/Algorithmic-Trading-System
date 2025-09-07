"""P&L Calculator for Multi-Currency Trading
Calculates profit and loss across different currencies and asset classes.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class PnLResult:
    """Result of P&L calculation."""
    pnl_local: float
    pnl_account_currency: float
    fx_rate_used: float


class MultiCurrencyPnLCalculator:
    """Calculates P&L across multiple currencies."""
    
    def __init__(self, account_currency: str = 'USD'):
        """Initialize the P&L calculator.
        
        Args:
            account_currency: Base currency for P&L reporting
        """
        self.account_currency = account_currency
        self.fx_rates = {
            'EURUSD': 1.0865,
            'GBPUSD': 1.2640,
            'USDJPY': 150.25,
            'AUDUSD': 0.6580,
            'USDCAD': 1.3720
        }
    
    def calculate_position_pnl(self, position: Dict[str, Any], 
                              account_currency: Optional[str] = None) -> PnLResult:
        """Calculate P&L for a position in account currency.
        
        Args:
            position: Position details dictionary
            account_currency: Account currency (defaults to instance setting)
            
        Returns:
            PnLResult with calculation details
        """
        if account_currency is None:
            account_currency = self.account_currency
            
        quantity = position['quantity']
        price_diff = position['current_price'] - position['entry_price']
        
        if position['symbol'] == 'EURUSD':
            pnl_usd = quantity * price_diff
        elif position['symbol'] == 'GBPJPY':
            pnl_jpy = quantity * price_diff
            pnl_usd = pnl_jpy / self.fx_rates['USDJPY']  # Convert JPY to USD
        elif position['symbol'] == 'XAUUSD':
            pnl_usd = quantity * price_diff
        else:
            pnl_usd = 0.0
        
        return PnLResult(
            pnl_local=quantity * price_diff,
            pnl_account_currency=pnl_usd,
            fx_rate_used=self.fx_rates.get(f"{position['quote_currency']}{account_currency}", 1.0)
        )
    
    def get_fx_rate(self, from_currency: str, to_currency: str) -> float:
        """Get FX rate between two currencies.
        
        Args:
            from_currency: Source currency
            to_currency: Target currency
            
        Returns:
            FX rate
        """
        if from_currency == to_currency:
            return 1.0
            
        # Try direct pair
        pair = f"{from_currency}{to_currency}"
        if pair in self.fx_rates:
            return self.fx_rates[pair]
            
        # Try inverse pair
        inverse_pair = f"{to_currency}{from_currency}"
        if inverse_pair in self.fx_rates:
            return 1.0 / self.fx_rates[inverse_pair]
            
        # Default to 1.0 if no rate found
        return 1.0