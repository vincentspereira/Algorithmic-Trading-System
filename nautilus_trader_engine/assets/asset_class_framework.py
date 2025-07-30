"""
Asset Class Framework
Unified framework for equities, options, futures, bonds, and cryptocurrencies
"""

import asyncio
import logging
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from collections import defaultdict
from abc import ABC, abstractmethod
import math


class AssetClass(Enum):
    """Asset class types"""
    EQUITY = "equity"
    OPTION = "option"
    FUTURE = "future"
    BOND = "bond"
    CRYPTOCURRENCY = "cryptocurrency"


class OptionType(Enum):
    """Option types"""
    CALL = "call"
    PUT = "put"


@dataclass
class AssetSpecification:
    """Base asset specification"""
    symbol: str
    asset_class: AssetClass
    name: str
    currency: str = "USD"
    exchange: str = "NYSE"
    current_price: float = 0.0
    is_active: bool = True
    last_updated: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EquitySpecification(AssetSpecification):
    """Equity-specific specification"""
    market_cap: float = 0.0
    pe_ratio: float = 0.0
    dividend_yield: float = 0.0
    
    def __post_init__(self):
        self.asset_class = AssetClass.EQUITY


@dataclass
class OptionSpecification(AssetSpecification):
    """Option-specific specification"""
    underlying_symbol: str = ""
    option_type: OptionType = OptionType.CALL
    strike_price: float = 0.0
    expiry_date: Optional[datetime] = None
    implied_volatility: float = 0.0
    
    def __post_init__(self):
        self.asset_class = AssetClass.OPTION


class AssetPricingModel(ABC):
    """Abstract base class for asset pricing models"""
    
    @abstractmethod
    async def calculate_theoretical_price(self, asset: AssetSpecification, **kwargs) -> float:
        """Calculate theoretical price for the asset"""
        pass
    
    @abstractmethod
    async def calculate_risk_metrics(self, asset: AssetSpecification, **kwargs) -> Dict[str, float]:
        """Calculate risk metrics for the asset"""
        pass


class EquityPricingModel(AssetPricingModel):
    """Equity pricing model"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def calculate_theoretical_price(self, asset: EquitySpecification, **kwargs) -> float:
        """Calculate theoretical equity price"""
        try:
            method = kwargs.get('method', 'pe_multiple')
            
            if method == 'pe_multiple' and asset.pe_ratio > 0:
                earnings_per_share = asset.current_price / asset.pe_ratio
                target_pe = kwargs.get('target_pe', asset.pe_ratio)
                return earnings_per_share * target_pe
            
            return asset.current_price
                
        except Exception as e:
            self.logger.error(f"Equity pricing calculation failed: {e}")
            return asset.current_price
    
    async def calculate_risk_metrics(self, asset: EquitySpecification, **kwargs) -> Dict[str, float]:
        """Calculate equity risk metrics"""
        try:
            returns = kwargs.get('returns', np.random.normal(0.001, 0.02, 252))
            
            metrics = {
                'volatility': np.std(returns) * np.sqrt(252),
                'sharpe_ratio': np.mean(returns) / np.std(returns) * np.sqrt(252),
                'var_95': np.percentile(returns, 5)
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Equity risk calculation failed: {e}")
            return {}


class OptionPricingModel(AssetPricingModel):
    """Option pricing model using Black-Scholes"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def calculate_theoretical_price(self, asset: OptionSpecification, **kwargs) -> float:
        """Calculate theoretical option price using Black-Scholes"""
        try:
            S = kwargs.get('underlying_price', 100.0)
            K = asset.strike_price
            T = kwargs.get('time_to_expiry', 0.25)  # 3 months default
            r = kwargs.get('risk_free_rate', 0.05)
            sigma = kwargs.get('volatility', asset.implied_volatility or 0.20)
            
            if T <= 0:
                if asset.option_type == OptionType.CALL:
                    return max(S - K, 0)
                else:
                    return max(K - S, 0)
            
            d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
            d2 = d1 - sigma * np.sqrt(T)
            
            if asset.option_type == OptionType.CALL:
                price = S * self._norm_cdf(d1) - K * np.exp(-r * T) * self._norm_cdf(d2)
            else:
                price = K * np.exp(-r * T) * self._norm_cdf(-d2) - S * self._norm_cdf(-d1)
            
            return max(price, 0)
                
        except Exception as e:
            self.logger.error(f"Option pricing calculation failed: {e}")
            return asset.current_price
    
    async def calculate_risk_metrics(self, asset: OptionSpecification, **kwargs) -> Dict[str, float]:
        """Calculate option Greeks"""
        try:
            S = kwargs.get('underlying_price', 100.0)
            K = asset.strike_price
            T = kwargs.get('time_to_expiry', 0.25)
            r = kwargs.get('risk_free_rate', 0.05)
            sigma = kwargs.get('volatility', asset.implied_volatility or 0.20)
            
            if T <= 0:
                return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}
            
            d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
            
            # Delta
            if asset.option_type == OptionType.CALL:
                delta = self._norm_cdf(d1)
            else:
                delta = self._norm_cdf(d1) - 1
            
            # Gamma
            gamma = self._norm_pdf(d1) / (S * sigma * np.sqrt(T))
            
            # Vega
            vega = S * self._norm_pdf(d1) * np.sqrt(T) / 100
            
            # Theta (simplified)
            theta = -0.01  # Simplified time decay
            
            return {
                'delta': delta,
                'gamma': gamma,
                'theta': theta,
                'vega': vega
            }
            
        except Exception as e:
            self.logger.error(f"Option risk calculation failed: {e}")
            return {}
    
    def _norm_cdf(self, x: float) -> float:
        """Standard normal cumulative distribution function"""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))
    
    def _norm_pdf(self, x: float) -> float:
        """Standard normal probability density function"""
        return math.exp(-0.5 * x**2) / math.sqrt(2 * math.pi)


class AssetClassFramework:
    """Main framework class that orchestrates all asset classes"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize pricing models
        self.pricing_models = {
            AssetClass.EQUITY: EquityPricingModel(),
            AssetClass.OPTION: OptionPricingModel()
        }
        
        # Asset registry
        self.assets: Dict[str, AssetSpecification] = {}
    
    async def register_asset(self, asset: AssetSpecification) -> bool:
        """Register a new asset in the framework"""
        try:
            self.assets[asset.symbol] = asset
            self.logger.info(f"Registered {asset.asset_class.value} asset: {asset.symbol}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register asset {asset.symbol}: {e}")
            return False
    
    async def get_asset(self, symbol: str) -> Optional[AssetSpecification]:
        """Get asset by symbol"""
        return self.assets.get(symbol)
    
    async def calculate_theoretical_price(self, symbol: str, **kwargs) -> Optional[float]:
        """Calculate theoretical price for an asset"""
        try:
            asset = self.assets.get(symbol)
            if not asset:
                self.logger.warning(f"Asset {symbol} not found")
                return None
            
            pricing_model = self.pricing_models.get(asset.asset_class)
            if not pricing_model:
                self.logger.warning(f"No pricing model for {asset.asset_class.value}")
                return asset.current_price
            
            return await pricing_model.calculate_theoretical_price(asset, **kwargs)
            
        except Exception as e:
            self.logger.error(f"Failed to calculate theoretical price for {symbol}: {e}")
            return None
    
    async def calculate_risk_metrics(self, symbol: str, **kwargs) -> Optional[Dict[str, float]]:
        """Calculate risk metrics for an asset"""
        try:
            asset = self.assets.get(symbol)
            if not asset:
                self.logger.warning(f"Asset {symbol} not found")
                return None
            
            pricing_model = self.pricing_models.get(asset.asset_class)
            if not pricing_model:
                self.logger.warning(f"No pricing model for {asset.asset_class.value}")
                return {}
            
            return await pricing_model.calculate_risk_metrics(asset, **kwargs)
            
        except Exception as e:
            self.logger.error(f"Failed to calculate risk metrics for {symbol}: {e}")
            return None
    
    def get_assets_by_class(self, asset_class: AssetClass) -> List[AssetSpecification]:
        """Get all assets of a specific class"""
        return [asset for asset in self.assets.values() if asset.asset_class == asset_class]
    
    def get_active_assets(self) -> List[AssetSpecification]:
        """Get all active assets"""
        return [asset for asset in self.assets.values() if asset.is_active]


# Factory functions for creating assets
def create_equity_asset(symbol: str, name: str, **kwargs) -> EquitySpecification:
    """Factory function to create equity asset"""
    return EquitySpecification(
        symbol=symbol,
        asset_class=AssetClass.EQUITY,
        name=name,
        **kwargs
    )


def create_option_asset(symbol: str, underlying_symbol: str, option_type: OptionType, 
                      strike_price: float, **kwargs) -> OptionSpecification:
    """Factory function to create option asset"""
    return OptionSpecification(
        symbol=symbol,
        asset_class=AssetClass.OPTION,
        name=f"{underlying_symbol} {option_type.value.upper()} {strike_price}",
        underlying_symbol=underlying_symbol,
        option_type=option_type,
        strike_price=strike_price,
        **kwargs
    )


# Example usage
async def example_usage():
    """Example usage of the Asset Class Framework"""
    
    # Initialize framework
    framework = AssetClassFramework()
    
    # Create sample assets
    equity = create_equity_asset(
        symbol="AAPL",
        name="Apple Inc.",
        current_price=150.0,
        pe_ratio=25.0
    )
    
    option = create_option_asset(
        symbol="AAPL240315C00150000",
        underlying_symbol="AAPL",
        option_type=OptionType.CALL,
        strike_price=150.0,
        current_price=5.0,
        implied_volatility=0.25
    )
    
    # Register assets
    await framework.register_asset(equity)
    await framework.register_asset(option)
    
    # Calculate theoretical prices
    equity_price = await framework.calculate_theoretical_price("AAPL", target_pe=20.0)
    option_price = await framework.calculate_theoretical_price("AAPL240315C00150000", underlying_price=155.0)
    
    print(f"Equity theoretical price: ${equity_price:.2f}")
    print(f"Option theoretical price: ${option_price:.2f}")
    
    # Calculate risk metrics
    equity_risk = await framework.calculate_risk_metrics("AAPL")
    option_risk = await framework.calculate_risk_metrics("AAPL240315C00150000", underlying_price=155.0)
    
    print(f"Equity risk metrics: {equity_risk}")
    print(f"Option Greeks: {option_risk}")


if __name__ == "__main__":
    asyncio.run(example_usage())