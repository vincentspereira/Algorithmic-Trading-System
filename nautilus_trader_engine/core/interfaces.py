"""
Core Interfaces for Institutional-Grade Trading System.

This module defines the abstract interfaces that implement the 5-pillar
institutional architecture:

1. Volume Integration & Confirmation
2. Market Regime Adaptation
3. Multi-Timeframe Convergence Analysis
4. Smart Money & Microstructure Proxies
5. Automated Risk Management Factory

All interfaces include:
- Type hints for static analysis
- Async support for high-performance operations
- Comprehensive error handling
- Performance monitoring hooks
- Configuration management
- Health monitoring capabilities
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Set, Tuple, Union
from enum import Enum


class MarketRegime(Enum):
    """Market regime classifications."""
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    TRENDING = "trending"
    RANGING = "ranging"


class SignalStrength(Enum):
    """Signal strength classifications."""
    VERY_WEAK = "very_weak"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class RiskLevel(Enum):
    """Risk level classifications."""
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class MarketData:
    """Standardized market data structure."""
    symbol: str
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float
    vwap: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_volume: Optional[float] = None
    ask_volume: Optional[float] = None
    additional_data: Dict[str, Any] = None


@dataclass
class Signal:
    """Trading signal structure."""
    signal_type: str
    symbol: str
    timestamp: float
    strength: SignalStrength
    confidence: float
    direction: str  # "buy", "sell", "hold"
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    metadata: Dict[str, Any] = None


@dataclass
class Position:
    """Position structure."""
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    timestamp: float
    metadata: Dict[str, Any] = None


@dataclass
class RiskMetrics:
    """Risk metrics structure."""
    symbol: str
    position_size: float
    max_drawdown: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_concentration: float
    risk_level: RiskLevel
    timestamp: float


# Pillar 1: Volume Integration & Confirmation
class IVolumeIntegration(Protocol):
    """
    Volume Integration & Confirmation Interface.

    Ensures all trading decisions incorporate volume analysis for confirmation.
    """

    @abstractmethod
    async def analyze_volume_confirmation(self, market_data: MarketData) -> Dict[str, Any]:
        """Analyze volume confirmation for price movements."""
        pass

    @abstractmethod
    async def calculate_volume_weighted_metrics(self, data: List[MarketData]) -> Dict[str, Any]:
        """Calculate volume-weighted technical metrics."""
        pass

    @abstractmethod
    async def detect_volume_divergence(self, price_data: List[float], volume_data: List[float]) -> Dict[str, Any]:
        """Detect volume divergences from price action."""
        pass


# Pillar 2: Market Regime Adaptation
class IMarketRegimeAdaptation(Protocol):
    """
    Market Regime Adaptation Interface.

    Adapts trading parameters based on current market conditions.
    """

    @abstractmethod
    async def detect_market_regime(self, market_data: List[MarketData]) -> MarketRegime:
        """Detect current market regime."""
        pass

    @abstractmethod
    async def adapt_parameters(self, regime: MarketRegime, base_params: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt trading parameters based on market regime."""
        pass

    @abstractmethod
    async def get_regime_confidence(self, regime: MarketRegime) -> float:
        """Get confidence level for regime detection."""
        pass


# Pillar 3: Multi-Timeframe Convergence Analysis
class IMultiTimeframeAnalysis(Protocol):
    """
    Multi-Timeframe Convergence Analysis Interface.

    Analyzes convergence across multiple timeframes for robust signals.
    """

    @abstractmethod
    async def analyze_timeframe_convergence(self, data_by_timeframe: Dict[str, List[MarketData]]) -> Dict[str, Any]:
        """Analyze convergence across multiple timeframes."""
        pass

    @abstractmethod
    async def calculate_timeframe_weights(self, timeframes: List[str]) -> Dict[str, float]:
        """Calculate weights for different timeframes."""
        pass

    @abstractmethod
    async def detect_timeframe_divergence(self, data_by_timeframe: Dict[str, List[MarketData]]) -> Dict[str, Any]:
        """Detect divergences between timeframes."""
        pass


# Pillar 4: Smart Money & Microstructure Proxies
class ISmartMoneyAnalysis(Protocol):
    """
    Smart Money & Microstructure Proxies Interface.

    Tracks institutional activity and order flow patterns.
    """

    @abstractmethod
    async def analyze_order_flow(self, market_data: List[MarketData]) -> Dict[str, Any]:
        """Analyze order flow patterns."""
        pass

    @abstractmethod
    async def detect_institutional_activity(self, market_data: List[MarketData]) -> Dict[str, Any]:
        """Detect institutional trading activity."""
        pass

    @abstractmethod
    async def calculate_market_impact(self, trade_size: float, market_data: MarketData) -> float:
        """Calculate expected market impact of a trade."""
        pass


# Pillar 5: Automated Risk Management Factory
class IRiskManagementFactory(Protocol):
    """
    Automated Risk Management Factory Interface.

    Provides comprehensive risk management across all strategies.
    """

    @abstractmethod
    async def calculate_position_size(self, capital: float, risk_per_trade: float, stop_loss: float) -> float:
        """Calculate optimal position size."""
        pass

    @abstractmethod
    async def assess_portfolio_risk(self, positions: List[Position]) -> RiskMetrics:
        """Assess overall portfolio risk."""
        pass

    @abstractmethod
    async def generate_risk_limits(self, strategy_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate risk limits for a strategy."""
        pass


# Core Trading Interfaces
class IIndicator(ABC):
    """
    Technical Indicator Interface.

    Defines the contract for all technical indicators in the system.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Indicator name."""
        pass

    @property
    @abstractmethod
    def timeframe(self) -> str:
        """Indicator timeframe."""
        pass

    @property
    @abstractmethod
    def is_warmed_up(self) -> bool:
        """Check if indicator is warmed up."""
        pass

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the indicator."""
        pass

    @abstractmethod
    async def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate indicator values."""
        pass

    @abstractmethod
    async def get_indicator_info(self) -> Dict[str, Any]:
        """Get indicator information and metadata."""
        pass


class IStrategy(ABC):
    """
    Trading Strategy Interface.

    Defines the contract for all trading strategies in the system.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name."""
        pass

    @property
    @abstractmethod
    def config(self) -> Dict[str, Any]:
        """Strategy configuration."""
        pass

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the strategy."""
        pass

    @abstractmethod
    async def generate_signals(self, market_data: Dict[str, Any]) -> List[Signal]:
        """Generate trading signals."""
        pass

    @abstractmethod
    async def execute_signal(self, signal: Signal) -> bool:
        """Execute a trading signal."""
        pass

    @abstractmethod
    async def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy information and metadata."""
        pass


class IEngine(ABC):
    """
    Analysis Engine Interface.

    Defines the contract for all analysis engines in the system.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Engine name."""
        pass

    @property
    @abstractmethod
    def config(self) -> Dict[str, Any]:
        """Engine configuration."""
        pass

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the engine."""
        pass

    @abstractmethod
    async def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data through the engine."""
        pass

    @abstractmethod
    async def get_engine_info(self) -> Dict[str, Any]:
        """Get engine information and metadata."""
        pass


class IDataFeed(ABC):
    """
    Market Data Feed Interface.

    Defines the contract for market data feeds.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Data feed name."""
        pass

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the data feed."""
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the data feed."""
        pass

    @abstractmethod
    async def subscribe(self, symbols: List[str]) -> bool:
        """Subscribe to market data for symbols."""
        pass

    @abstractmethod
    async def unsubscribe(self, symbols: List[str]) -> bool:
        """Unsubscribe from market data for symbols."""
        pass

    @abstractmethod
    async def get_historical_data(self, symbol: str, start_time: float, end_time: float) -> List[MarketData]:
        """Get historical market data."""
        pass


class IBroker(ABC):
    """
    Broker Interface.

    Defines the contract for broker integrations.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Broker name."""
        pass

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the broker."""
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the broker."""
        pass

    @abstractmethod
    async def place_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Place a trading order."""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a trading order."""
        pass

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get current positions."""
        pass

    @abstractmethod
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information."""
        pass


class IPerformanceTracker(ABC):
    """
    Performance Tracking Interface.

    Defines the contract for performance tracking and analytics.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Performance tracker name."""
        pass

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the performance tracker."""
        pass

    @abstractmethod
    async def record_trade(self, trade: Dict[str, Any]) -> bool:
        """Record a completed trade."""
        pass

    @abstractmethod
    async def calculate_metrics(self, start_time: float, end_time: float) -> Dict[str, Any]:
        """Calculate performance metrics."""
        pass

    @abstractmethod
    async def generate_report(self, report_type: str) -> Dict[str, Any]:
        """Generate a performance report."""
        pass


class IConfigurationManager(ABC):
    """
    Configuration Management Interface.

    Defines the contract for configuration management.
    """

    @abstractmethod
    async def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from file."""
        pass

    @abstractmethod
    async def save_config(self, config: Dict[str, Any], config_path: str) -> bool:
        """Save configuration to file."""
        pass

    @abstractmethod
    async def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        pass

    @abstractmethod
    async def set_config_value(self, key: str, value: Any) -> bool:
        """Set a configuration value."""
        pass

    @abstractmethod
    async def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate configuration."""
        pass


class IHealthMonitor(ABC):
    """
    Health Monitoring Interface.

    Defines the contract for system health monitoring.
    """

    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        """Check overall system health."""
        pass

    @abstractmethod
    async def get_component_health(self, component_name: str) -> Dict[str, Any]:
        """Get health status of a specific component."""
        pass

    @abstractmethod
    async def register_health_check(self, name: str, check_func: callable) -> bool:
        """Register a health check function."""
        pass

    @abstractmethod
    async def unregister_health_check(self, name: str) -> bool:
        """Unregister a health check function."""
        pass


# Factory Interfaces
class IIndicatorFactory(ABC):
    """
    Indicator Factory Interface.

    Defines the contract for creating indicators.
    """

    @abstractmethod
    async def create_indicator(self, indicator_type: str, config: Dict[str, Any]) -> IIndicator:
        """Create an indicator instance."""
        pass

    @abstractmethod
    async def get_available_indicators(self) -> List[str]:
        """Get list of available indicator types."""
        pass

    @abstractmethod
    async def validate_indicator_config(self, indicator_type: str, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate indicator configuration."""
        pass


class IStrategyFactory(ABC):
    """
    Strategy Factory Interface.

    Defines the contract for creating strategies.
    """

    @abstractmethod
    async def create_strategy(self, strategy_type: str, config: Dict[str, Any]) -> IStrategy:
        """Create a strategy instance."""
        pass

    @abstractmethod
    async def get_available_strategies(self) -> List[str]:
        """Get list of available strategy types."""
        pass

    @abstractmethod
    async def validate_strategy_config(self, strategy_type: str, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate strategy configuration."""
        pass


class IEngineFactory(ABC):
    """
    Engine Factory Interface.

    Defines the contract for creating engines.
    """

    @abstractmethod
    async def create_engine(self, engine_type: str, config: Dict[str, Any]) -> IEngine:
        """Create an engine instance."""
        pass

    @abstractmethod
    async def get_available_engines(self) -> List[str]:
        """Get list of available engine types."""
        pass

    @abstractmethod
    async def validate_engine_config(self, engine_type: str, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate engine configuration."""
        pass


# Plugin System Interface
class IPluginManager(ABC):
    """
    Plugin Manager Interface.

    Defines the contract for plugin management.
    """

    @abstractmethod
    async def load_plugin(self, plugin_path: str) -> bool:
        """Load a plugin from path."""
        pass

    @abstractmethod
    async def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin."""
        pass

    @abstractmethod
    async def get_loaded_plugins(self) -> List[str]:
        """Get list of loaded plugins."""
        pass

    @abstractmethod
    async def get_plugin_info(self, plugin_name: str) -> Dict[str, Any]:
        """Get information about a plugin."""
        pass