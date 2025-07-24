"""
Feature Store Package for Nautilus Trading System

This package provides Feast feature store integration for the algorithmic trading system,
including feature definitions, configuration, and setup utilities.

Modules:
- feature_store_config: Configuration and management for Feast feature store
- feature_definitions: Feature definitions for market data, indicators, and signals
- setup_feast: Setup script for initializing the feature store

Author: Kilo Code
Version: 1.0.0
"""

from .feature_store_config import (
    FeatureStoreConfig,
    FeatureStoreManager,
    create_feature_store_manager
)

from .feature_definitions import (
    get_all_feature_definitions,
    get_feature_list_by_category,
    create_entities,
    create_data_sources,
    create_market_data_features,
    create_technical_indicator_features,
    create_volume_profile_features,
    create_trading_signal_features,
    create_on_demand_features,
    create_feature_services
)

from .setup_feast import FeastSetupManager

__all__ = [
    # Configuration
    "FeatureStoreConfig",
    "FeatureStoreManager", 
    "create_feature_store_manager",
    
    # Feature definitions
    "get_all_feature_definitions",
    "get_feature_list_by_category",
    "create_entities",
    "create_data_sources",
    "create_market_data_features",
    "create_technical_indicator_features",
    "create_volume_profile_features",
    "create_trading_signal_features",
    "create_on_demand_features",
    "create_feature_services",
    
    # Setup
    "FeastSetupManager",
]

__version__ = "1.0.0"