# Nautilus Trader Engine - Main Package

# This is the main package for the Nautilus Trader Engine
# It exposes all the core modules and components

# Import core modules to make them available
from . import adapters
from . import ai
from . import analytics
from . import api
from . import assets
from . import audit
from . import backtesting
from . import brokers
from . import caching
from . import compliance
from . import config
from . import core
from . import data
from . import data_feeds
from . import database
from . import events
from . import failover
from . import feature_store
from . import indicators
from . import kafka
from . import mobile
from . import models
from . import monitoring
from . import order_management
from . import orders
from . import portfolio
from . import privacy
from . import pnl
from . import reporting
from . import research
from . import risk
from . import rl
from . import security
from . import services
from . import storage
from . import strategies
from . import strategy_execution
from . import tests
from . import trading
from . import utils
from . import validation
from . import visualization

# Import key classes for easier access
from .core.data_feed_manager import DataFeedManager
from .core.order_management import OrderManager

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
    
    # Key classes
    'ComprehensiveIndicators',
    'ComprehensiveIndicatorResult',
    'IndicatorCategory',
    'DataFeedManager',
    'OrderManager'
]