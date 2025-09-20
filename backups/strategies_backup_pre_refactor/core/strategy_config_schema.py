import json
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import jsonschema
from jsonschema import validate, ValidationError

# Import from BaseInstitutionalStrategy
from .base_institutional_strategy import (
    MarketRegime, SignalType, ExecutionAction, ExecutionAlgorithm,
    ExecutionUrgency, TimeInForce
)


class AssetClass(Enum):
    """Supported asset classes"""
    EQUITY = "EQUITY"
    FOREX = "FOREX"
    COMMODITY = "COMMODITY"
    CRYPTO = "CRYPTO"
    BOND = "BOND"
    OPTION = "OPTION"
    FUTURE = "FUTURE"
    ETF = "ETF"


class TimeFrame(Enum):
    """Supported timeframes"""
    TICK = "TICK"
    SECOND_1 = "1S"
    SECOND_5 = "5S"
    SECOND_15 = "15S"
    SECOND_30 = "30S"
    MINUTE_1 = "1M"
    MINUTE_5 = "5M"
    MINUTE_15 = "15M"
    MINUTE_30 = "30M"
    HOUR_1 = "1H"
    HOUR_4 = "4H"
    DAILY = "1D"
    WEEKLY = "1W"
    MONTHLY = "1MO"


class StrategyCategory(Enum):
    """Strategy categories"""
    MOMENTUM = "MOMENTUM"
    MEAN_REVERSION = "MEAN_REVERSION"
    VOLATILITY_BREAKOUT = "VOLATILITY_BREAKOUT"
    PAIRS_TRADING = "PAIRS_TRADING"
    ARBITRAGE = "ARBITRAGE"
    ADVANCED_TECHNICAL = "ADVANCED_TECHNICAL"
    ML_BASED = "ML_BASED"
    SEASONAL = "SEASONAL"
    NEWS_SENTIMENT = "NEWS_SENTIMENT"
    MULTI_FACTOR = "MULTI_FACTOR"


@dataclass
class IndicatorConfig:
    """Configuration for technical indicators"""
    name: str
    parameters: Dict[str, Any]
    volume_weighted: bool = False
    smoothing_factor: Optional[float] = None
    lookback_period: Optional[int] = None


@dataclass
class SignalConfig:
    """Configuration for signal generation"""
    primary_indicators: List[IndicatorConfig]
    secondary_indicators: Optional[List[IndicatorConfig]] = None
    candlestick_patterns: Optional[List[str]] = None
    signal_threshold: float = 0.6
    confirmation_required: bool = True
    volume_confirmation: bool = False
    regime_filter: bool = True
    lookback_bars: int = 20


@dataclass
class RiskConfig:
    """Configuration for risk management"""
    position_sizing_method: str = "FIXED_FRACTIONAL"  # FIXED_FRACTIONAL, KELLY, VOLATILITY_ADJUSTED
    base_position_size: float = 0.02  # 2% of portfolio
    max_position_size: float = 0.1    # 10% of portfolio
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    trailing_stop_pct: Optional[float] = None
    max_drawdown_pct: float = 0.15    # 15% maximum drawdown
    var_confidence: float = 0.95      # 95% VaR confidence
    correlation_threshold: float = 0.7 # Maximum correlation with existing positions
    leverage_limit: float = 1.0       # Maximum leverage
    risk_free_rate: float = 0.02      # Risk-free rate for calculations


@dataclass
class RegimeConfig:
    """Configuration for market regime detection"""
    enabled: bool = True
    detection_method: str = "VOLATILITY_REGIME"  # VOLATILITY_REGIME, TREND_REGIME, CORRELATION_REGIME
    lookback_period: int = 252  # 1 year of daily data
    regime_threshold: float = 0.5
    adaptation_speed: float = 0.1
    regime_filters: Dict[MarketRegime, bool] = None
    
    def __post_init__(self):
        if self.regime_filters is None:
            self.regime_filters = {
                MarketRegime.BULL_MARKET: True,
                MarketRegime.BEAR_MARKET: True,
                MarketRegime.SIDEWAYS_MARKET: True,
                MarketRegime.HIGH_VOLATILITY: True,
                MarketRegime.LOW_VOLATILITY: True
            }


@dataclass
class ExecutionConfig:
    """Configuration for execution logic"""
    default_algorithm: ExecutionAlgorithm = ExecutionAlgorithm.LIMIT
    default_urgency: ExecutionUrgency = ExecutionUrgency.MEDIUM
    default_time_in_force: TimeInForce = TimeInForce.GTC
    max_participation_rate: float = 0.1
    price_improvement_threshold: float = 0.0001
    slippage_tolerance: float = 0.001
    allow_partial_fills: bool = True
    min_fill_size: Optional[float] = None
    execution_delay_ms: int = 100
    smart_routing: bool = True
    dark_pool_preference: float = 0.3  # 30% preference for dark pools


@dataclass
class PerformanceConfig:
    """Configuration for performance tracking"""
    benchmark_symbol: Optional[str] = "SPY"  # Benchmark for comparison
    track_intraday: bool = True
    calculate_attribution: bool = True
    risk_metrics_enabled: bool = True
    performance_frequency: str = "DAILY"  # TICK, MINUTE, HOURLY, DAILY
    rolling_window_days: int = 30
    save_trades: bool = True
    save_signals: bool = True
    export_format: str = "JSON"  # JSON, CSV, PARQUET


@dataclass
class BacktestConfig:
    """Configuration for backtesting"""
    start_date: str  # YYYY-MM-DD format
    end_date: str    # YYYY-MM-DD format
    initial_capital: float = 100000.0
    commission_per_trade: float = 1.0
    commission_pct: float = 0.001  # 0.1%
    slippage_pct: float = 0.001    # 0.1%
    market_impact_model: str = "SQUARE_ROOT"
    transaction_cost_model: str = "FIXED_PLUS_PERCENTAGE"
    benchmark_comparison: bool = True
    monte_carlo_runs: int = 1000
    confidence_intervals: List[float] = None
    
    def __post_init__(self):
        if self.confidence_intervals is None:
            self.confidence_intervals = [0.95, 0.99]


@dataclass
class StrategyConfig:
    """Complete strategy configuration"""
    # Strategy Metadata
    name: str
    version: str
    description: str
    category: StrategyCategory
    author: str
    created_date: str
    last_modified: str
    
    # Market Configuration
    asset_classes: List[AssetClass]
    symbols: List[str]
    timeframes: List[TimeFrame]
    primary_timeframe: TimeFrame
    
    # 5-Pillar Configuration
    signal_config: SignalConfig
    risk_config: RiskConfig
    regime_config: RegimeConfig
    execution_config: ExecutionConfig
    performance_config: PerformanceConfig
    
    # Backtesting Configuration
    backtest_config: BacktestConfig
    
    # Strategy-Specific Parameters
    strategy_parameters: Dict[str, Any]
    
    # Operational Configuration
    enabled: bool = True
    live_trading_enabled: bool = False
    paper_trading_enabled: bool = True
    max_concurrent_positions: int = 10
    position_timeout_hours: Optional[int] = None
    
    # Logging and Monitoring
    log_level: str = "INFO"
    alert_conditions: Dict[str, Any] = None
    notification_settings: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.alert_conditions is None:
            self.alert_conditions = {
                "max_drawdown_breach": True,
                "position_size_breach": True,
                "correlation_breach": True,
                "execution_failure": True
            }
        
        if self.notification_settings is None:
            self.notification_settings = {
                "email_enabled": False,
                "sms_enabled": False,
                "webhook_enabled": False
            }


class StrategyConfigValidator:
    """Validator for strategy configurations"""
    
    @staticmethod
    def get_json_schema() -> Dict[str, Any]:
        """Get JSON schema for strategy configuration validation"""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "version": {"type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$"},
                "description": {"type": "string", "minLength": 10},
                "category": {"type": "string", "enum": [e.value for e in StrategyCategory]},
                "author": {"type": "string", "minLength": 1},
                "created_date": {"type": "string", "format": "date"},
                "last_modified": {"type": "string", "format": "date"},
                "asset_classes": {
                    "type": "array",
                    "items": {"type": "string", "enum": [e.value for e in AssetClass]},
                    "minItems": 1
                },
                "symbols": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                    "minItems": 1
                },
                "timeframes": {
                    "type": "array",
                    "items": {"type": "string", "enum": [e.value for e in TimeFrame]},
                    "minItems": 1
                },
                "primary_timeframe": {"type": "string", "enum": [e.value for e in TimeFrame]},
                "signal_config": {
                    "type": "object",
                    "properties": {
                        "primary_indicators": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "parameters": {"type": "object"},
                                    "volume_weighted": {"type": "boolean"},
                                    "smoothing_factor": {"type": ["number", "null"]},
                                    "lookback_period": {"type": ["integer", "null"]}
                                },
                                "required": ["name", "parameters"]
                            },
                            "minItems": 1
                        },
                        "signal_threshold": {"type": "number", "minimum": 0, "maximum": 1},
                        "lookback_bars": {"type": "integer", "minimum": 1}
                    },
                    "required": ["primary_indicators"]
                },
                "risk_config": {
                    "type": "object",
                    "properties": {
                        "base_position_size": {"type": "number", "minimum": 0, "maximum": 1},
                        "max_position_size": {"type": "number", "minimum": 0, "maximum": 1},
                        "max_drawdown_pct": {"type": "number", "minimum": 0, "maximum": 1},
                        "leverage_limit": {"type": "number", "minimum": 0}
                    }
                },
                "backtest_config": {
                    "type": "object",
                    "properties": {
                        "start_date": {"type": "string", "format": "date"},
                        "end_date": {"type": "string", "format": "date"},
                        "initial_capital": {"type": "number", "minimum": 0}
                    },
                    "required": ["start_date", "end_date"]
                },
                "strategy_parameters": {"type": "object"},
                "enabled": {"type": "boolean"}
            },
            "required": [
                "name", "version", "description", "category", "author",
                "created_date", "asset_classes", "symbols", "timeframes",
                "primary_timeframe", "signal_config", "backtest_config",
                "strategy_parameters"
            ]
        }
    
    @staticmethod
    def validate_config(config: Union[StrategyConfig, Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """
        Validate strategy configuration against schema and business rules.
        
        Args:
            config: Strategy configuration to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Convert to dict if StrategyConfig object
        if isinstance(config, StrategyConfig):
            config_dict = asdict(config)
        else:
            config_dict = config
        
        # JSON Schema validation
        try:
            validate(instance=config_dict, schema=StrategyConfigValidator.get_json_schema())
        except ValidationError as e:
            errors.append(f"Schema validation error: {e.message}")
        
        # Business rule validations
        try:
            # Date validation
            from datetime import datetime
            start_date = datetime.strptime(config_dict['backtest_config']['start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(config_dict['backtest_config']['end_date'], '%Y-%m-%d')
            
            if start_date >= end_date:
                errors.append("Backtest start date must be before end date")
            
            # Risk parameter validation
            risk_config = config_dict.get('risk_config', {})
            base_size = risk_config.get('base_position_size', 0)
            max_size = risk_config.get('max_position_size', 1)
            
            if base_size > max_size:
                errors.append("Base position size cannot exceed maximum position size")
            
            # Signal threshold validation
            signal_config = config_dict.get('signal_config', {})
            threshold = signal_config.get('signal_threshold', 0.5)
            
            if not 0 <= threshold <= 1:
                errors.append("Signal threshold must be between 0 and 1")
            
            # Timeframe consistency
            timeframes = config_dict.get('timeframes', [])
            primary_tf = config_dict.get('primary_timeframe')
            
            if primary_tf not in timeframes:
                errors.append("Primary timeframe must be included in timeframes list")
            
        except (KeyError, ValueError, TypeError) as e:
            errors.append(f"Business rule validation error: {str(e)}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def create_template_config(strategy_name: str, category: StrategyCategory) -> StrategyConfig:
        """
        Create a template configuration for a new strategy.
        
        Args:
            strategy_name: Name of the strategy
            category: Strategy category
            
        Returns:
            Template strategy configuration
        """
        from datetime import datetime, timedelta
        
        today = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        return StrategyConfig(
            name=strategy_name,
            version="1.0.0",
            description=f"Template configuration for {strategy_name} strategy",
            category=category,
            author="Strategy Developer",
            created_date=today,
            last_modified=today,
            asset_classes=[AssetClass.EQUITY],
            symbols=["SPY", "QQQ", "IWM"],
            timeframes=[TimeFrame.DAILY, TimeFrame.HOUR_1],
            primary_timeframe=TimeFrame.DAILY,
            signal_config=SignalConfig(
                primary_indicators=[
                    IndicatorConfig(
                        name="SMA",
                        parameters={"period": 20},
                        volume_weighted=False
                    ),
                    IndicatorConfig(
                        name="RSI",
                        parameters={"period": 14},
                        volume_weighted=True
                    )
                ],
                signal_threshold=0.6,
                confirmation_required=True,
                volume_confirmation=True,
                regime_filter=True,
                lookback_bars=20
            ),
            risk_config=RiskConfig(),
            regime_config=RegimeConfig(),
            execution_config=ExecutionConfig(),
            performance_config=PerformanceConfig(),
            backtest_config=BacktestConfig(
                start_date=start_date,
                end_date=today
            ),
            strategy_parameters={
                "example_parameter": 1.0,
                "another_parameter": "example_value"
            }
        )


def save_config_to_file(config: StrategyConfig, filepath: str) -> bool:
    """
    Save strategy configuration to JSON file.
    
    Args:
        config: Strategy configuration
        filepath: Path to save the configuration
        
    Returns:
        Success status
    """
    try:
        config_dict = asdict(config)
        
        # Convert enums to strings for JSON serialization
        def convert_enums(obj):
            if isinstance(obj, dict):
                return {k: convert_enums(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_enums(item) for item in obj]
            elif isinstance(obj, Enum):
                return obj.value
            else:
                return obj
        
        config_dict = convert_enums(config_dict)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"Error saving configuration: {e}")
        return False


def load_config_from_file(filepath: str) -> Optional[StrategyConfig]:
    """
    Load strategy configuration from JSON file.
    
    Args:
        filepath: Path to the configuration file
        
    Returns:
        Strategy configuration or None if failed
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            config_dict = json.load(f)
        
        # Validate configuration
        is_valid, errors = StrategyConfigValidator.validate_config(config_dict)
        if not is_valid:
            print(f"Configuration validation failed: {errors}")
            return None
        
        # Convert string enums back to enum objects
        # This is a simplified conversion - in practice, you'd want more robust handling
        return StrategyConfig(**config_dict)
        
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return None


# Example usage and testing
if __name__ == "__main__":
    # Create a template configuration
    template_config = StrategyConfigValidator.create_template_config(
        "Moving Average Crossover",
        StrategyCategory.MOMENTUM
    )
    
    # Validate the configuration
    is_valid, errors = StrategyConfigValidator.validate_config(template_config)
    print(f"Template configuration valid: {is_valid}")
    if errors:
        print(f"Validation errors: {errors}")
    
    # Save to file (example)
    # save_config_to_file(template_config, "ma_crossover_config.json")
    
    print("Strategy configuration schema created successfully!")