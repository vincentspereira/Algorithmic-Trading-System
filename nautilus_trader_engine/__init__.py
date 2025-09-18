# Nautilus Trader Engine - Main Package

# This is the main package for the Nautilus Trader Engine
# It exposes all the core modules and components

# Avoid eager submodule imports to prevent heavy side-effects during import time.
# Submodules remain importable via `nautilus_trader_engine.<submodule>` without being
# imported here.

__all__ = [
    # Submodules
    'adapters',
    'ai',
    'analytics',
    'api',
    'assets',
    'audit',
    'backtesting',
    'brokers',
    'caching',
    'compliance',
    'config',
    'core',
    'data_feeds',
    'database',
    'events',
    'failover',
    'feature_store',
    'indicators',
    'kafka',
    'mobile',
    'models',
    'monitoring',
    'order_management',
    'orders',
    'portfolio',
    'privacy',
    'pnl',
    'reporting',
    'research',
    'risk',
    'rl',
    'security',
    'services',
    'storage',
    'strategies',
    'strategy_execution',
    'tests',
    'trading',
    'utils',
    'validation',
    'visualization',
]