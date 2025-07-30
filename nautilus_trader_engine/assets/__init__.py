"""
Multi-Asset Class Trading Support
Asset class abstractions, equity trading, options trading, and futures trading
"""

from .asset_base import (
    AssetClass, AssetType, TradingSession, MarketDataType,
    BaseAsset, AssetManager
)

from .equity import (
    EquityAsset, DividendInfo, CorporateAction, CorporateActionType
)

# Options and futures modules will be implemented in future phases

from .asset_class_framework import (
    AssetClassFramework,
    AssetSpecification,
    EquitySpecification,
    OptionSpecification,
    EquityPricingModel,
    OptionPricingModel,
    create_equity_asset,
    create_option_asset
)

__all__ = [
    # Base classes
    'AssetClass', 'AssetType', 'TradingSession', 'MarketDataType',
    'BaseAsset', 'AssetManager',
    
    # Equity classes
    'EquityAsset', 'DividendInfo', 'CorporateAction', 'CorporateActionType',
    
    # Asset Class Framework
    'AssetClassFramework',
    'AssetSpecification',
    'EquitySpecification',
    'OptionSpecification',
    'EquityPricingModel',
    'OptionPricingModel',
    'create_equity_asset',
    'create_option_asset'
]