"""Portfolio package initialization.

This file makes `nautilus_trader_engine.portfolio` a proper Python package
so submodules like `advanced_portfolio_manager` can be imported in tests.
"""

from .advanced_portfolio_manager import (
    AdvancedPortfolioManager,
    AssetClass,
    RebalancingStrategy,
    RebalancingFrequency,
    AssetAllocation,
    PortfolioConstraints,
    RebalancingConfig,
    PortfolioMetrics,
    get_advanced_portfolio_manager,
    initialize_advanced_portfolio_manager,
)

__all__ = [
    "AdvancedPortfolioManager",
    "AssetClass",
    "RebalancingStrategy",
    "RebalancingFrequency",
    "AssetAllocation",
    "PortfolioConstraints",
    "RebalancingConfig",
    "PortfolioMetrics",
    "get_advanced_portfolio_manager",
    "initialize_advanced_portfolio_manager",
]