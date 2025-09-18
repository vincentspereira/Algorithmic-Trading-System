"""Strategy Factory Module

This module provides factory classes for creating and configuring different types
of trading strategies. It serves as a centralized creation point for all strategy
types in the algorithmic trading system.

Key Features:
- Strategy type registration and creation
- Configuration validation and defaults
- Strategy parameter optimization
- Template-based strategy creation
- Strategy cloning and modification

Architecture:
Follows the Factory Pattern with strategy-specific factories and a unified
factory manager for coordinated strategy creation.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type, Union
from dataclasses import dataclass, field
from enum import Enum

# Core trading components
try:
    import pandas as pd
    import numpy as np
except ImportError:
    pd = None
    np = None

# Strategy modules - import from actual pairs_trading directory
try:
    from ..pairs_trading.pairs_strategies import (
        StrategyType, PositionType, SignalStrength,
        TradingSignal, Position, StrategyConfig
    )
except ImportError:
    # Define basic types if pairs_trading not available
    from enum import Enum
    
    class StrategyType(Enum):
        PAIRS_TRADING = "pairs_trading"
        MOMENTUM = "momentum"
        MEAN_REVERSION = "mean_reversion"
    
    class PositionType(Enum):
        LONG = "long"
        SHORT = "short"
        NEUTRAL = "neutral"
    
    class SignalStrength(Enum):
        WEAK = "weak"
        MEDIUM = "medium"
        STRONG = "strong"
    
    class TradingSignal:
        pass
    
    class Position:
        pass
    
    class StrategyConfig:
        pass

try:
    from ..pairs_trading import (
        PairsStrategy, ConvergenceStrategy, DivergenceStrategy,
        PairSelector, CorrelationAnalyzer, SpreadIndicators,
        PairsRiskManager, PairsPerformanceAnalyzer
    )
except ImportError:
    PairsStrategy = None

try:
    from .machine_learning import (
        BaseMLStrategy, RandomForestStrategy, XGBoostStrategy,
        ClusteringStrategy, RLTradingStrategy, FeatureEngineer,
        AdvancedModelManager
    )
except ImportError:
    BaseMLStrategy = None

class StrategyTemplate(Enum):
    """Pre-defined strategy templates"""
    CONSERVATIVE_PAIRS = "conservative_pairs"
    AGGRESSIVE_PAIRS = "aggressive_pairs"
    ML_MOMENTUM = "ml_momentum"
    ML_MEAN_REVERSION = "ml_mean_reversion"
    REGIME_ADAPTIVE = "regime_adaptive"
    HIGH_FREQUENCY = "high_frequency"
    SWING_TRADING = "swing_trading"
    SCALPING = "scalping"

@dataclass
class StrategyBlueprint:
    """Strategy creation blueprint"""
    name: str
    strategy_type: Union[StrategyType, str]
    category: str
    default_config: StrategyConfig
    description: str
    risk_level: str = "medium"
    min_capital: float = 10000.0
    recommended_timeframes: List[str] = field(default_factory=lambda: ["1h", "4h", "1d"])
    asset_classes: List[str] = field(default_factory=lambda: ["stocks", "etfs"])
    
class BaseStrategyFactory(ABC):
    """Base factory for creating trading strategies"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.blueprints: Dict[str, StrategyBlueprint] = {}
        self._register_blueprints()
    
    @abstractmethod
    def _register_blueprints(self):
        """Register strategy blueprints"""
        pass
    
    @abstractmethod
    def create_strategy(self, blueprint_name: str, config: Optional[StrategyConfig] = None) -> Any:
        """Create strategy instance"""
        pass
    
    def get_blueprint(self, name: str) -> Optional[StrategyBlueprint]:
        """Get strategy blueprint"""
        return self.blueprints.get(name)
    
    def list_blueprints(self) -> List[str]:
        """List available blueprints"""
        return list(self.blueprints.keys())
    
    def validate_config(self, blueprint_name: str, config: StrategyConfig) -> bool:
        """Validate strategy configuration"""
        blueprint = self.get_blueprint(blueprint_name)
        if not blueprint:
            return False
        
        # Basic validation
        if config.initial_capital < blueprint.min_capital:
            self.logger.warning(f"Capital {config.initial_capital} below minimum {blueprint.min_capital}")
            return False
        
        return True

class PairsStrategyFactory(BaseStrategyFactory):
    """Factory for pairs trading strategies"""
    
    def _register_blueprints(self):
        """Register pairs trading blueprints"""
        # Conservative pairs trading
        self.blueprints["conservative_pairs"] = StrategyBlueprint(
            name="Conservative Pairs Trading",
            strategy_type=StrategyType.CONVERGENCE,
            category="pairs_trading",
            default_config=StrategyConfig(
                strategy_type=StrategyType.CONVERGENCE,
                symbols=["SPY", "QQQ"],
                timeframe="1h",
                initial_capital=50000.0,
                max_position_size=0.1,
                stop_loss=0.02,
                take_profit=0.04,
                parameters={
                    "lookback_period": 60,
                    "entry_threshold": 2.0,
                    "exit_threshold": 0.5,
                    "correlation_threshold": 0.8,
                    "cointegration_pvalue": 0.05
                }
            ),
            description="Conservative pairs trading with strict risk controls",
            risk_level="low",
            min_capital=25000.0,
            recommended_timeframes=["1h", "4h", "1d"],
            asset_classes=["stocks", "etfs"]
        )
        
        # Aggressive pairs trading
        self.blueprints["aggressive_pairs"] = StrategyBlueprint(
            name="Aggressive Pairs Trading",
            strategy_type=StrategyType.DIVERGENCE,
            category="pairs_trading",
            default_config=StrategyConfig(
                strategy_type=StrategyType.DIVERGENCE,
                symbols=["TQQQ", "SQQQ"],
                timeframe="15m",
                initial_capital=100000.0,
                max_position_size=0.25,
                stop_loss=0.05,
                take_profit=0.08,
                parameters={
                    "lookback_period": 30,
                    "entry_threshold": 1.5,
                    "exit_threshold": 0.3,
                    "correlation_threshold": -0.7,
                    "momentum_period": 14
                }
            ),
            description="Aggressive pairs trading with higher risk/reward",
            risk_level="high",
            min_capital=50000.0,
            recommended_timeframes=["5m", "15m", "1h"],
            asset_classes=["stocks", "etfs", "leveraged_etfs"]
        )
    
    def create_strategy(self, blueprint_name: str, config: Optional[StrategyConfig] = None) -> Any:
        """Create pairs trading strategy"""
        if PairsStrategy is None:
            self.logger.error("Pairs trading module not available")
            return None
        
        blueprint = self.get_blueprint(blueprint_name)
        if not blueprint:
            self.logger.error(f"Blueprint {blueprint_name} not found")
            return None
        
        # Use provided config or default
        strategy_config = config or blueprint.default_config
        
        # Validate configuration
        if not self.validate_config(blueprint_name, strategy_config):
            self.logger.error(f"Invalid configuration for {blueprint_name}")
            return None
        
        try:
            # Create strategy based on type
            if blueprint.strategy_type == StrategyType.CONVERGENCE:
                return ConvergenceStrategy(strategy_config)
            elif blueprint.strategy_type == StrategyType.DIVERGENCE:
                return DivergenceStrategy(strategy_config)
            else:
                return PairsStrategy(strategy_config)
        
        except Exception as e:
            self.logger.error(f"Error creating pairs strategy: {e}")
            return None

class MLStrategyFactory(BaseStrategyFactory):
    """Factory for machine learning strategies"""
    
    def _register_blueprints(self):
        """Register ML strategy blueprints"""
        # ML Momentum strategy
        self.blueprints["ml_momentum"] = StrategyBlueprint(
            name="ML Momentum Strategy",
            strategy_type="random_forest",
            category="machine_learning",
            default_config=StrategyConfig(
                strategy_type=StrategyType.MOMENTUM,
                symbols=["SPY", "QQQ", "IWM"],
                timeframe="1h",
                initial_capital=100000.0,
                max_position_size=0.15,
                stop_loss=0.03,
                take_profit=0.06,
                parameters={
                    "lookback_period": 100,
                    "feature_window": 20,
                    "n_estimators": 100,
                    "max_depth": 10,
                    "prediction_threshold": 0.6,
                    "retrain_frequency": 168  # hours
                }
            ),
            description="Random Forest based momentum strategy",
            risk_level="medium",
            min_capital=50000.0,
            recommended_timeframes=["1h", "4h", "1d"],
            asset_classes=["stocks", "etfs", "indices"]
        )
        
        # ML Mean Reversion strategy
        self.blueprints["ml_mean_reversion"] = StrategyBlueprint(
            name="ML Mean Reversion Strategy",
            strategy_type="xgboost",
            category="machine_learning",
            default_config=StrategyConfig(
                strategy_type=StrategyType.MEAN_REVERSION,
                symbols=["SPY", "TLT", "GLD"],
                timeframe="4h",
                initial_capital=75000.0,
                max_position_size=0.2,
                stop_loss=0.025,
                take_profit=0.05,
                parameters={
                    "lookback_period": 200,
                    "feature_window": 50,
                    "n_estimators": 200,
                    "learning_rate": 0.1,
                    "max_depth": 8,
                    "prediction_threshold": 0.65,
                    "retrain_frequency": 336  # hours
                }
            ),
            description="XGBoost based mean reversion strategy",
            risk_level="medium",
            min_capital=40000.0,
            recommended_timeframes=["2h", "4h", "1d"],
            asset_classes=["stocks", "etfs", "bonds", "commodities"]
        )
        
        # Regime Adaptive strategy
        self.blueprints["regime_adaptive"] = StrategyBlueprint(
            name="Regime Adaptive Strategy",
            strategy_type="clustering",
            category="machine_learning",
            default_config=StrategyConfig(
                strategy_type=StrategyType.ADAPTIVE,
                symbols=["SPY", "QQQ", "IWM", "TLT", "GLD"],
                timeframe="1d",
                initial_capital=150000.0,
                max_position_size=0.3,
                stop_loss=0.04,
                take_profit=0.08,
                parameters={
                    "lookback_period": 252,
                    "n_clusters": 4,
                    "regime_window": 60,
                    "adaptation_speed": 0.1,
                    "confidence_threshold": 0.7
                }
            ),
            description="Market regime detection with adaptive behavior",
            risk_level="medium",
            min_capital=100000.0,
            recommended_timeframes=["1d", "1w"],
            asset_classes=["stocks", "etfs", "bonds", "commodities", "currencies"]
        )
    
    def create_strategy(self, blueprint_name: str, config: Optional[StrategyConfig] = None) -> Any:
        """Create ML strategy"""
        if BaseMLStrategy is None:
            self.logger.error("Machine learning module not available")
            return None
        
        blueprint = self.get_blueprint(blueprint_name)
        if not blueprint:
            self.logger.error(f"Blueprint {blueprint_name} not found")
            return None
        
        # Use provided config or default
        strategy_config = config or blueprint.default_config
        
        # Validate configuration
        if not self.validate_config(blueprint_name, strategy_config):
            self.logger.error(f"Invalid configuration for {blueprint_name}")
            return None
        
        try:
            # Create strategy based on type
            if blueprint.strategy_type == "random_forest":
                return RandomForestStrategy(strategy_config)
            elif blueprint.strategy_type == "xgboost":
                return XGBoostStrategy(strategy_config)
            elif blueprint.strategy_type == "clustering":
                return ClusteringStrategy(strategy_config)
            elif blueprint.strategy_type == "reinforcement_learning":
                return RLTradingStrategy(strategy_config)
            else:
                return BaseMLStrategy(strategy_config)
        
        except Exception as e:
            self.logger.error(f"Error creating ML strategy: {e}")
            return None

class StrategyFactory:
    """Unified strategy factory manager"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.factories: Dict[str, BaseStrategyFactory] = {
            "pairs_trading": PairsStrategyFactory(),
            "machine_learning": MLStrategyFactory()
        }
    
    def create_strategy(self, category: str, blueprint_name: str, 
                      config: Optional[StrategyConfig] = None) -> Any:
        """Create strategy using appropriate factory"""
        if category not in self.factories:
            self.logger.error(f"No factory for category {category}")
            return None
        
        factory = self.factories[category]
        return factory.create_strategy(blueprint_name, config)
    
    def create_from_template(self, template: StrategyTemplate, 
                           symbols: Optional[List[str]] = None,
                           capital: Optional[float] = None) -> Any:
        """Create strategy from predefined template"""
        template_mapping = {
            StrategyTemplate.CONSERVATIVE_PAIRS: ("pairs_trading", "conservative_pairs"),
            StrategyTemplate.AGGRESSIVE_PAIRS: ("pairs_trading", "aggressive_pairs"),
            StrategyTemplate.ML_MOMENTUM: ("machine_learning", "ml_momentum"),
            StrategyTemplate.ML_MEAN_REVERSION: ("machine_learning", "ml_mean_reversion"),
            StrategyTemplate.REGIME_ADAPTIVE: ("machine_learning", "regime_adaptive")
        }
        
        if template not in template_mapping:
            self.logger.error(f"Template {template} not supported")
            return None
        
        category, blueprint_name = template_mapping[template]
        factory = self.factories[category]
        blueprint = factory.get_blueprint(blueprint_name)
        
        if not blueprint:
            self.logger.error(f"Blueprint {blueprint_name} not found")
            return None
        
        # Customize configuration
        config = blueprint.default_config
        if symbols:
            config.symbols = symbols
        if capital:
            config.initial_capital = capital
        
        return factory.create_strategy(blueprint_name, config)
    
    def list_categories(self) -> List[str]:
        """List available strategy categories"""
        return list(self.factories.keys())
    
    def list_blueprints(self, category: Optional[str] = None) -> Dict[str, List[str]]:
        """List available blueprints"""
        if category:
            if category in self.factories:
                return {category: self.factories[category].list_blueprints()}
            else:
                return {}
        
        return {
            cat: factory.list_blueprints()
            for cat, factory in self.factories.items()
        }
    
    def get_blueprint_info(self, category: str, blueprint_name: str) -> Optional[StrategyBlueprint]:
        """Get detailed blueprint information"""
        if category not in self.factories:
            return None
        
        return self.factories[category].get_blueprint(blueprint_name)
    
    def register_factory(self, category: str, factory: BaseStrategyFactory):
        """Register custom strategy factory"""
        self.factories[category] = factory
        self.logger.info(f"Registered factory for category {category}")
    
    def clone_strategy(self, strategy_instance: Any, new_config: StrategyConfig) -> Any:
        """Clone existing strategy with new configuration"""
        try:
            # Get strategy class
            strategy_class = strategy_instance.__class__
            
            # Create new instance with new config
            return strategy_class(new_config)
        
        except Exception as e:
            self.logger.error(f"Error cloning strategy: {e}")
            return None

# Global factory instance
strategy_factory = StrategyFactory()

# Convenience functions
def create_strategy(category: str, blueprint_name: str, 
                  config: Optional[StrategyConfig] = None) -> Any:
    """Create strategy using global factory"""
    return strategy_factory.create_strategy(category, blueprint_name, config)

def create_from_template(template: StrategyTemplate, 
                        symbols: Optional[List[str]] = None,
                        capital: Optional[float] = None) -> Any:
    """Create strategy from template"""
    return strategy_factory.create_from_template(template, symbols, capital)

def list_available_strategies() -> Dict[str, List[str]]:
    """List all available strategy blueprints"""
    return strategy_factory.list_blueprints()

def get_strategy_info(category: str, blueprint_name: str) -> Optional[StrategyBlueprint]:
    """Get strategy blueprint information"""
    return strategy_factory.get_blueprint_info(category, blueprint_name)