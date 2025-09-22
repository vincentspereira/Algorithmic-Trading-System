"""
Core Infrastructure for Institutional-Grade Trading System.

This module provides the foundational components that implement the 5-pillar
institutional architecture:

1. Volume Integration & Confirmation
2. Market Regime Adaptation
3. Multi-Timeframe Convergence Analysis
4. Smart Money & Microstructure Proxies
5. Automated Risk Management Factory

Key Components:
- Dependency Injection Container: Advanced DI framework with institutional features
- Base Classes: Enhanced base classes for indicators, strategies, and engines
- Interfaces: Comprehensive interface definitions for all system components
- Configuration Management: Centralized configuration with validation
- Health Monitoring: Real-time health checks and metrics collection
- Performance Tracking: Detailed performance monitoring and analytics
"""

from .dependency_injection import (
    DependencyInjectionContainer,
    get_container,
    register_service,
    get_service,
    has_service,
    injectable,
    singleton,
    scoped,
    ServiceLifetime,
    ServiceScope,
    ServiceNotFoundError,
    CircularDependencyError,
    ServiceResolutionError
)

from .configuration_manager import (
    ConfigurationManager,
    get_config_manager,
    load_config,
    get_config,
    set_config,
    ConfigurationError,
    ConfigurationValidationError,
    ConfigurationNotFoundError,
    ConfigurationLoadError,
    SystemConfig,
    DatabaseConfig,
    RedisConfig,
    TradingConfig,
    IndicatorConfig,
    StrategyConfig
)

from .plugin_system import (
    PluginManager,
    get_plugin_manager,
    load_plugin,
    unload_plugin,
    get_loaded_plugins,
    get_plugin_info,
    PluginError,
    PluginLoadError,
    PluginUnloadError,
    PluginValidationError,
    PluginDependencyError
)

from .event_system import (
    EventBus,
    get_event_bus,
    publish_event,
    subscribe,
    unsubscribe,
    create_event,
    Event,
    EventType,
    EventPriority,
    EventHandler,
    EventFilter,
    EventAggregator,
    SimpleEventHandler
)

from .adaptive_parameters import (
    AdaptiveParameterManager,
    get_adaptive_manager,
    register_adaptive_parameters,
    adapt_parameters,
    create_adaptive_parameter,
    AdaptiveParameter,
    ParameterBounds,
    ParameterType,
    AdaptationStrategy,
    MarketCondition,
    AdaptationContext,
    VolatilityBasedAdapter,
    TrendStrengthAdapter,
    MarketRegimeAdapter,
    PerformanceBasedAdapter
)

from .ensemble_methods import (
    EnsembleManager,
    get_ensemble_manager,
    combine_signals,
    register_indicator_performance,
    update_ensemble_weights,
    get_ensemble_performance,
    EnsembleMethod,
    VotingScheme,
    IndicatorSignal,
    EnsembleSignal,
    IndicatorPerformance,
    EnsembleWeights,
    WeightedVotingCombiner,
    BayesianCombiner,
    ConsensusCombiner,
    AdaptiveEnsembleCombiner
)

from .validation_system import (
    ValidationManager,
    get_validation_manager,
    validate_signal,
    validate_market_data,
    validate_system_health,
    ValidationStatus,
    ValidationType,
    ValidationResult,
    ValidationRule,
    ValidationMetrics,
    SignalValidator,
    DataQualityValidator,
    SystemHealthValidator
)

from .backtesting_system import (
    BacktestEngine,
    get_backtest_engine,
    run_backtest,
    get_backtest_result,
    get_backtest_history,
    BacktestMode,
    OptimizationMethod,
    BacktestConfig,
    BacktestResult,
    WalkForwardWindow,
    MonteCarloResult,
    Trade,
    Position,
    Strategy
)

from .strategy_components import (
    StrategyComposer,
    get_strategy_composer,
    define_strategy,
    activate_strategy,
    execute_strategy,
    ComponentType,
    SignalType,
    StrategySignal,
    PortfolioState,
    Order,
    StrategyComponent,
    EntrySignalGenerator,
    ExitSignalGenerator,
    PositionSizer,
    RiskManager,
    OrderExecutor,
    PerformanceTracker
)

from .risk_adaptive_strategies import (
    RiskAdaptiveStrategyManager,
    get_risk_adaptive_manager,
    adapt_strategy,
    generate_adaptive_signals,
    calculate_adaptive_risk_metrics,
    AdaptationTrigger,
    AdaptationStrategy,
    RiskProfile,
    MarketCondition,
    AdaptationRule,
    StrategyState,
    RiskAdaptiveStrategy,
    MarketRegimeAdapter,
    VolatilityAdaptiveStrategy,
    PerformanceAdaptiveStrategy
)

from .multi_strategy_portfolios import (
    MultiStrategyPortfolioManager,
    get_multi_strategy_manager,
    create_portfolio,
    optimize_portfolio,
    rebalance_portfolio,
    update_portfolio_metrics,
    AllocationMethod,
    RebalancingFrequency,
    StrategyStatus,
    StrategyAllocation,
    PortfolioConstraints,
    PortfolioMetrics,
    RebalancingSignal,
    AllocationOptimizer,
    RiskParityOptimizer,
    MeanVarianceOptimizer,
    KellyCriterionOptimizer
)

from .performance_attribution import (
    PerformanceAttributionManager,
    get_performance_attribution_manager,
    calculate_portfolio_attribution,
    get_strategy_attribution,
    generate_attribution_report,
    AttributionMethod,
    AttributionPeriod,
    AttributionResult,
    BrinsonAttribution,
    RiskAttribution,
    FactorAttribution,
    StrategyAttribution,
    AttributionCalculator,
    BrinsonAttributionCalculator,
    RiskAttributionCalculator,
    MultiFactorAttributionCalculator
)

from .parallel_processing import (
    ParallelProcessingEngine,
    get_parallel_engine,
    submit_parallel_task,
    submit_parallel_batch,
    get_parallel_result,
    get_parallel_metrics,
    parallel_indicator_calculation,
    parallel_portfolio_optimization,
    parallel_backtest_strategies,
    ProcessingMode,
    TaskPriority,
    TaskStatus,
    ParallelTask,
    WorkerNode,
    ProcessingMetrics,
    TaskExecutor,
    ThreadPoolExecutorWrapper,
    ProcessPoolExecutorWrapper,
    GPUAccelerator
)

from .caching_layer import (
    IntelligentCacheManager,
    get_cache_manager,
    cache_get,
    cache_set,
    cache_delete,
    cached,
    cache_indicator_result,
    get_cached_indicator,
    invalidate_symbol_cache,
    warm_market_data_cache,
    CacheLevel,
    CacheStrategy,
    CompressionType,
    CacheEntry,
    CacheMetrics,
    CacheConfig,
    CacheBackend,
    MemoryCacheBackend,
    DiskCacheBackend
)

from .streaming_architecture import (
    StreamingEngine,
    get_streaming_engine,
    create_market_data_stream,
    create_signal_stream,
    publish_market_event,
    publish_signal_event,
    filter_by_symbol,
    filter_by_signal_strength,
    map_to_price,
    map_to_volume,
    aggregate_to_vwap,
    aggregate_to_average,
    aggregate_to_sum,
    aggregate_to_count,
    StreamType,
    StreamMode,
    WindowType,
    StreamEvent,
    StreamSubscription,
    StreamMetrics,
    StreamWindow,
    StreamObservable,
    StreamOperator,
    MapOperator,
    FilterOperator,
    WindowOperator,
    AggregateOperator
)

from .fault_tolerance import (
    FaultToleranceManager,
    get_fault_tolerance_manager,
    SystemHealthMonitor,
    FailureRecoveryManager,
    CircuitBreaker,
    CircuitBreakerOpenException,
    HealthChecker,
    check_system_health,
    get_circuit_breaker_status,
    reset_circuit_breaker,
    circuit_breaker,
    with_fault_tolerance,
    CircuitBreakerState,
    FailureType,
    RecoveryStrategy,
    CircuitBreakerConfig,
    HealthCheck,
    FailureRecord,
    SystemHealth
)

from .base_classes import (
    BaseComponent,
    BaseIndicator,
    BaseStrategy,
    BaseEngine,
    ComponentStatus,
    ComponentHealth,
    ComponentMetrics,
    create_indicator,
    create_strategy,
    create_engine
)

from .interfaces import (
    # Enums
    MarketRegime,
    SignalStrength,
    RiskLevel,

    # Data Structures
    MarketData,
    Signal,
    Position,
    RiskMetrics,

    # 5-Pillar Interfaces
    IVolumeIntegration,
    IMarketRegimeAdaptation,
    IMultiTimeframeAnalysis,
    ISmartMoneyAnalysis,
    IRiskManagementFactory,

    # Core Trading Interfaces
    IIndicator,
    IStrategy,
    IEngine,
    IDataFeed,
    IBroker,
    IPerformanceTracker,

    # System Interfaces
    IConfigurationManager,
    IHealthMonitor,

    # Factory Interfaces
    IIndicatorFactory,
    IStrategyFactory,
    IEngineFactory,

    # Plugin System
    IPluginManager
)

__all__ = [
    # Dependency Injection
    "DependencyInjectionContainer",
    "get_container",
    "register_service",
    "get_service",
    "has_service",
    "injectable",
    "singleton",
    "scoped",
    "ServiceLifetime",
    "ServiceScope",
    "ServiceNotFoundError",
    "CircularDependencyError",
    "ServiceResolutionError",

    # Configuration Management
    "ConfigurationManager",
    "get_config_manager",
    "load_config",
    "get_config",
    "set_config",
    "ConfigurationError",
    "ConfigurationValidationError",
    "ConfigurationNotFoundError",
    "ConfigurationLoadError",
    "SystemConfig",
    "DatabaseConfig",
    "RedisConfig",
    "TradingConfig",
    "IndicatorConfig",
    "StrategyConfig",

    # Base Classes
    "BaseComponent",
    "BaseIndicator",
    "BaseStrategy",
    "BaseEngine",
    "ComponentStatus",
    "ComponentHealth",
    "ComponentMetrics",
    "create_indicator",
    "create_strategy",
    "create_engine",

    # Interfaces - Enums
    "MarketRegime",
    "SignalStrength",
    "RiskLevel",

    # Interfaces - Data Structures
    "MarketData",
    "Signal",
    "Position",
    "RiskMetrics",

    # Interfaces - 5-Pillar Architecture
    "IVolumeIntegration",
    "IMarketRegimeAdaptation",
    "IMultiTimeframeAnalysis",
    "ISmartMoneyAnalysis",
    "IRiskManagementFactory",

    # Interfaces - Core Trading
    "IIndicator",
    "IStrategy",
    "IEngine",
    "IDataFeed",
    "IBroker",
    "IPerformanceTracker",

    # Interfaces - System
    "IConfigurationManager",
    "IHealthMonitor",

    # Interfaces - Factories
    "IIndicatorFactory",
    "IStrategyFactory",
    "IEngineFactory",

    # Interfaces - Plugin System
    "IPluginManager",

    # Plugin System
    "PluginManager",
    "get_plugin_manager",
    "load_plugin",
    "unload_plugin",
    "get_loaded_plugins",
    "get_plugin_info",
    "PluginError",
    "PluginLoadError",
    "PluginUnloadError",
    "PluginValidationError",
    "PluginDependencyError",

    # Event System
    "EventBus",
    "get_event_bus",
    "publish_event",
    "subscribe",
    "unsubscribe",
    "create_event",
    "Event",
    "EventType",
    "EventPriority",
    "EventHandler",
    "EventFilter",
    "EventAggregator",
    "SimpleEventHandler",

    # Adaptive Parameters
    "AdaptiveParameterManager",
    "get_adaptive_manager",
    "register_adaptive_parameters",
    "adapt_parameters",
    "create_adaptive_parameter",
    "AdaptiveParameter",
    "ParameterBounds",
    "ParameterType",
    "AdaptationStrategy",
    "MarketCondition",
    "AdaptationContext",
    "VolatilityBasedAdapter",
    "TrendStrengthAdapter",
    "MarketRegimeAdapter",
    "PerformanceBasedAdapter",

    # Ensemble Methods
    "EnsembleManager",
    "get_ensemble_manager",
    "combine_signals",
    "register_indicator_performance",
    "update_ensemble_weights",
    "get_ensemble_performance",
    "EnsembleMethod",
    "VotingScheme",
    "IndicatorSignal",
    "EnsembleSignal",
    "IndicatorPerformance",
    "EnsembleWeights",
    "WeightedVotingCombiner",
    "BayesianCombiner",
    "ConsensusCombiner",
    "AdaptiveEnsembleCombiner",

    # Validation System
    "ValidationManager",
    "get_validation_manager",
    "validate_signal",
    "validate_market_data",
    "validate_system_health",
    "ValidationStatus",
    "ValidationType",
    "ValidationResult",
    "ValidationRule",
    "ValidationMetrics",
    "SignalValidator",
    "DataQualityValidator",
    "SystemHealthValidator",

    # Backtesting System
    "BacktestEngine",
    "get_backtest_engine",
    "run_backtest",
    "get_backtest_result",
    "get_backtest_history",
    "BacktestMode",
    "OptimizationMethod",
    "BacktestConfig",
    "BacktestResult",
    "WalkForwardWindow",
    "MonteCarloResult",
    "Trade",
    "Position",
    "Strategy",

    # Strategy Components
    "StrategyComposer",
    "get_strategy_composer",
    "define_strategy",
    "activate_strategy",
    "execute_strategy",
    "ComponentType",
    "SignalType",
    "StrategySignal",
    "PortfolioState",
    "Order",
    "StrategyComponent",
    "EntrySignalGenerator",
    "ExitSignalGenerator",
    "PositionSizer",
    "RiskManager",
    "OrderExecutor",
    "PerformanceTracker",

    # Risk-Adaptive Strategies
    "RiskAdaptiveStrategyManager",
    "get_risk_adaptive_manager",
    "adapt_strategy",
    "generate_adaptive_signals",
    "calculate_adaptive_risk_metrics",
    "AdaptationTrigger",
    "AdaptationStrategy",
    "RiskProfile",
    "MarketCondition",
    "AdaptationRule",
    "StrategyState",
    "RiskAdaptiveStrategy",
    "MarketRegimeAdapter",
    "VolatilityAdaptiveStrategy",
    "PerformanceAdaptiveStrategy",

    # Multi-Strategy Portfolios
    "MultiStrategyPortfolioManager",
    "get_multi_strategy_manager",
    "create_portfolio",
    "optimize_portfolio",
    "rebalance_portfolio",
    "update_portfolio_metrics",
    "AllocationMethod",
    "RebalancingFrequency",
    "StrategyStatus",
    "StrategyAllocation",
    "PortfolioConstraints",
    "PortfolioMetrics",
    "RebalancingSignal",
    "AllocationOptimizer",
    "RiskParityOptimizer",
    "MeanVarianceOptimizer",
    "KellyCriterionOptimizer",

    # Performance Attribution
    "PerformanceAttributionManager",
    "get_performance_attribution_manager",
    "calculate_portfolio_attribution",
    "get_strategy_attribution",
    "generate_attribution_report",
    "AttributionMethod",
    "AttributionPeriod",
    "AttributionResult",
    "BrinsonAttribution",
    "RiskAttribution",
    "FactorAttribution",
    "StrategyAttribution",
    "AttributionCalculator",
    "BrinsonAttributionCalculator",
    "RiskAttributionCalculator",
    "MultiFactorAttributionCalculator",

    # Parallel Processing
    "ParallelProcessingEngine",
    "get_parallel_engine",
    "submit_parallel_task",
    "submit_parallel_batch",
    "get_parallel_result",
    "get_parallel_metrics",
    "parallel_indicator_calculation",
    "parallel_portfolio_optimization",
    "parallel_backtest_strategies",
    "ProcessingMode",
    "TaskPriority",
    "TaskStatus",
    "ParallelTask",
    "WorkerNode",
    "ProcessingMetrics",
    "TaskExecutor",
    "ThreadPoolExecutorWrapper",
    "ProcessPoolExecutorWrapper",
    "GPUAccelerator",

    # Caching Layer
    "IntelligentCacheManager",
    "get_cache_manager",
    "cache_get",
    "cache_set",
    "cache_delete",
    "cached",
    "cache_indicator_result",
    "get_cached_indicator",
    "invalidate_symbol_cache",
    "warm_market_data_cache",
    "CacheLevel",
    "CacheStrategy",
    "CompressionType",
    "CacheEntry",
    "CacheMetrics",
    "CacheConfig",
    "CacheBackend",
    "MemoryCacheBackend",
    "DiskCacheBackend",

    # Streaming Architecture
    "StreamingEngine",
    "get_streaming_engine",
    "create_market_data_stream",
    "create_signal_stream",
    "publish_market_event",
    "publish_signal_event",
    "filter_by_symbol",
    "filter_by_signal_strength",
    "map_to_price",
    "map_to_volume",
    "aggregate_to_vwap",
    "aggregate_to_average",
    "aggregate_to_sum",
    "aggregate_to_count",
    "StreamType",
    "StreamMode",
    "WindowType",
    "StreamEvent",
    "StreamSubscription",
    "StreamMetrics",
    "StreamWindow",
    "StreamObservable",
    "StreamOperator",
    "MapOperator",
    "FilterOperator",
    "WindowOperator",
    "AggregateOperator",

    # Fault Tolerance
    "FaultToleranceManager",
    "get_fault_tolerance_manager",
    "SystemHealthMonitor",
    "FailureRecoveryManager",
    "CircuitBreaker",
    "CircuitBreakerOpenException",
    "HealthChecker",
    "check_system_health",
    "get_circuit_breaker_status",
    "reset_circuit_breaker",
    "circuit_breaker",
    "with_fault_tolerance",
    "CircuitBreakerState",
    "FailureType",
    "RecoveryStrategy",
    "CircuitBreakerConfig",
    "HealthCheck",
    "FailureRecord",
    "SystemHealth"
]

__version__ = "5.0.0"
__author__ = "Institutional Trading System"
__description__ = "Core infrastructure for institutional-grade algorithmic trading"
