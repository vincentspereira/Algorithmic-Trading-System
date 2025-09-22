=================
API Modules
=================

This section provides an overview of all API modules in the Nautilus Trader Engine.

Core Modules
============

.. autosummary::
   :toctree: _autosummary

   nautilus_trader_engine.core.dependency_injection
   nautilus_trader_engine.core.event_system
   nautilus_trader_engine.core.adaptive_parameters
   nautilus_trader_engine.core.ensemble_methods
   nautilus_trader_engine.core.validation_system
   nautilus_trader_engine.core.streaming_architecture
   nautilus_trader_engine.core.caching_layer
   nautilus_trader_engine.core.fault_tolerance
   nautilus_trader_engine.core.parallel_processing
   nautilus_trader_engine.core.configuration_management
   nautilus_trader_engine.core.plugin_system

Analysis Modules
================

.. autosummary::
   :toctree: _autosummary

   nautilus_trader_engine.analysis.indicators.adaptive_parameters
   nautilus_trader_engine.analysis.indicators.ensemble_methods
   nautilus_trader_engine.analysis.indicators.realtime_validation
   nautilus_trader_engine.analysis.indicators.technical_indicators
   nautilus_trader_engine.analysis.patterns.candlestick_patterns
   nautilus_trader_engine.analysis.market_structure.market_regime
   nautilus_trader_engine.analysis.market_structure.support_resistance
   nautilus_trader_engine.analysis.market_structure.trend_analysis

Strategy Modules
================

.. autosummary::
   :toctree: _autosummary

   nautilus_trader_engine.strategies.modular_strategy_components
   nautilus_trader_engine.strategies.risk_adaptive_strategies
   nautilus_trader_engine.strategies.multi_strategy_portfolios
   nautilus_trader_engine.strategies.strategy_performance_attribution
   nautilus_trader_engine.strategies.dynamic_hedging_strategies

Engine Modules
==============

.. autosummary::
   :toctree: _autosummary

   nautilus_trader_engine.engines.execution_engine
   nautilus_trader_engine.engines.risk_engine
   nautilus_trader_engine.engines.portfolio_engine
   nautilus_trader_engine.engines.order_management_engine

Backtesting Modules
===================

.. autosummary::
   :toctree: _autosummary

   nautilus_trader_engine.backtesting.backtesting_integration
   nautilus_trader_engine.backtesting.walk_forward_optimization
   nautilus_trader_engine.backtesting.strategy_optimization
   nautilus_trader_engine.backtesting.performance_attribution

Data Feed Modules
=================

.. autosummary::
   :toctree: _autosummary

   nautilus_trader_engine.data_feeds.market_data_feed
   nautilus_trader_engine.data_feeds.alternative_data_feeds
   nautilus_trader_engine.data_feeds.data_feed_monitoring
   nautilus_trader_engine.data_feeds.multi_source_feeds

Broker Integration
==================

.. autosummary::
   :toctree: _autosummary

   nautilus_trader_engine.brokers.interactive_brokers
   nautilus_trader_engine.brokers.broker_abstraction
   nautilus_trader_engine.brokers.order_routing
   nautilus_trader_engine.brokers.execution_algorithms

Compliance and Risk
===================

.. autosummary::
   :toctree: _autosummary

   nautilus_trader_engine.compliance.regulatory_compliance
   nautilus_trader_engine.compliance.risk_management
   nautilus_trader_engine.compliance.audit_reporting
   nautilus_trader_engine.compliance.fraud_detection

Monitoring and Alerting
========================

.. autosummary::
   :toctree: _autosummary

   nautilus_trader_engine.monitoring.system_monitoring
   nautilus_trader_engine.monitoring.performance_monitoring
   nautilus_trader_engine.monitoring.alerting_system
   nautilus_trader_engine.monitoring.metrics_collection

API and Interfaces
==================

.. autosummary::
   :toctree: _autosummary

   nautilus_trader_engine.api.rest_api
   nautilus_trader_engine.api.graphql_api
   nautilus_trader_engine.api.websocket_api
   nautilus_trader_engine.api.mobile_api

Utilities
=========

.. autosummary::
   :toctree: _autosummary

   nautilus_trader_engine.utils.logging_utils
   nautilus_trader_engine.utils.data_utils
   nautilus_trader_engine.utils.math_utils
   nautilus_trader_engine.utils.time_utils
   nautilus_trader_engine.utils.serialization_utils

Testing Framework
=================

.. autosummary::
   :toctree: _autosummary

   nautilus_trader_engine.tests.testing_framework
   nautilus_trader_engine.tests.test_utils
   nautilus_trader_engine.tests.coverage_analyzer
   nautilus_trader_engine.tests.performance_test_runner