"""Strategy Manager Module

This module provides a unified interface for managing all trading strategies across
the algorithmic trading system. It integrates pairs trading, machine learning,
and other strategy modules into a cohesive framework.

Key Features:
- Unified strategy registration and management
- Strategy lifecycle management (initialization, execution, monitoring)
- Performance tracking and analytics
- Risk management integration
- Multi-strategy portfolio coordination
- Real-time strategy monitoring and alerts

Architecture:
Follows the 5-Pillar Architecture with centralized strategy coordination,
event-driven communication, and comprehensive monitoring.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import threading
from collections import defaultdict

# Core trading components
try:
    import pandas as pd
    import numpy as np
except ImportError:
    pd = None
    np = None

# Strategy modules
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

# Base strategy interface
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

class StrategyStatus(Enum):
    """Strategy execution status"""
    INACTIVE = "inactive"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"

class StrategyCategory(Enum):
    """Strategy category classification"""
    PAIRS_TRADING = "pairs_trading"
    MACHINE_LEARNING = "machine_learning"
    TECHNICAL_ANALYSIS = "technical_analysis"
    ARBITRAGE = "arbitrage"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    CUSTOM = "custom"

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class StrategyMetrics:
    """Strategy performance metrics"""
    strategy_id: str
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    active_positions: int = 0
    last_updated: datetime = field(default_factory=datetime.now)
    
@dataclass
class StrategyAlert:
    """Strategy alert information"""
    strategy_id: str
    level: AlertLevel
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False

@dataclass
class StrategyRegistration:
    """Strategy registration information"""
    strategy_id: str
    strategy_instance: Any
    category: StrategyCategory
    config: StrategyConfig
    status: StrategyStatus = StrategyStatus.INACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    last_executed: Optional[datetime] = None
    metrics: Optional[StrategyMetrics] = None
    
class StrategyManager:
    """Unified strategy management system"""
    
    def __init__(self, max_concurrent_strategies: int = 10):
        self.strategies: Dict[str, StrategyRegistration] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_strategies)
        self.logger = logging.getLogger(__name__)
        self.alerts: List[StrategyAlert] = []
        self.performance_history: Dict[str, List[StrategyMetrics]] = defaultdict(list)
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        # Strategy factories
        self.strategy_factories = {
            StrategyCategory.PAIRS_TRADING: self._create_pairs_strategy,
            StrategyCategory.MACHINE_LEARNING: self._create_ml_strategy,
        }
        
    def register_strategy(
        self,
        strategy_id: str,
        strategy_type: Union[StrategyType, str],
        config: StrategyConfig,
        category: StrategyCategory = StrategyCategory.CUSTOM
    ) -> bool:
        """Register a new strategy"""
        try:
            if strategy_id in self.strategies:
                self.logger.warning(f"Strategy {strategy_id} already registered")
                return False
                
            # Create strategy instance
            strategy_instance = self._create_strategy_instance(
                strategy_type, config, category
            )
            
            if strategy_instance is None:
                self.logger.error(f"Failed to create strategy instance for {strategy_id}")
                return False
                
            # Register strategy
            registration = StrategyRegistration(
                strategy_id=strategy_id,
                strategy_instance=strategy_instance,
                category=category,
                config=config,
                metrics=StrategyMetrics(strategy_id=strategy_id)
            )
            
            self.strategies[strategy_id] = registration
            self.logger.info(f"Strategy {strategy_id} registered successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error registering strategy {strategy_id}: {e}")
            return False
    
    def _create_strategy_instance(self, strategy_type, config, category):
        """Create strategy instance based on type and category"""
        if category in self.strategy_factories:
            return self.strategy_factories[category](strategy_type, config)
        else:
            self.logger.warning(f"No factory for category {category}")
            return None
    
    def _create_pairs_strategy(self, strategy_type, config):
        """Create pairs trading strategy instance"""
        if PairsStrategy is None:
            self.logger.error("Pairs trading module not available")
            return None
            
        try:
            if strategy_type == StrategyType.CONVERGENCE:
                return ConvergenceStrategy(config)
            elif strategy_type == StrategyType.DIVERGENCE:
                return DivergenceStrategy(config)
            else:
                return PairsStrategy(config)
        except Exception as e:
            self.logger.error(f"Error creating pairs strategy: {e}")
            return None
    
    def _create_ml_strategy(self, strategy_type, config):
        """Create machine learning strategy instance"""
        if BaseMLStrategy is None:
            self.logger.error("Machine learning module not available")
            return None
            
        try:
            if strategy_type == "random_forest":
                return RandomForestStrategy(config)
            elif strategy_type == "xgboost":
                return XGBoostStrategy(config)
            elif strategy_type == "clustering":
                return ClusteringStrategy(config)
            elif strategy_type == "reinforcement_learning":
                return RLTradingStrategy(config)
            else:
                return BaseMLStrategy(config)
        except Exception as e:
            self.logger.error(f"Error creating ML strategy: {e}")
            return None
    
    async def start_strategy(self, strategy_id: str) -> bool:
        """Start a registered strategy"""
        if strategy_id not in self.strategies:
            self.logger.error(f"Strategy {strategy_id} not found")
            return False
            
        registration = self.strategies[strategy_id]
        
        try:
            registration.status = StrategyStatus.INITIALIZING
            
            # Initialize strategy
            if hasattr(registration.strategy_instance, 'initialize'):
                await self._run_async(registration.strategy_instance.initialize)
            
            registration.status = StrategyStatus.ACTIVE
            registration.last_executed = datetime.now()
            
            self.logger.info(f"Strategy {strategy_id} started successfully")
            return True
            
        except Exception as e:
            registration.status = StrategyStatus.ERROR
            self.logger.error(f"Error starting strategy {strategy_id}: {e}")
            self._add_alert(strategy_id, AlertLevel.ERROR, f"Failed to start: {e}")
            return False
    
    async def stop_strategy(self, strategy_id: str) -> bool:
        """Stop a running strategy"""
        if strategy_id not in self.strategies:
            self.logger.error(f"Strategy {strategy_id} not found")
            return False
            
        registration = self.strategies[strategy_id]
        
        try:
            # Stop strategy
            if hasattr(registration.strategy_instance, 'stop'):
                await self._run_async(registration.strategy_instance.stop)
            
            registration.status = StrategyStatus.STOPPED
            self.logger.info(f"Strategy {strategy_id} stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping strategy {strategy_id}: {e}")
            return False
    
    async def execute_strategy(self, strategy_id: str, market_data: Dict) -> Optional[List[TradingSignal]]:
        """Execute a strategy with market data"""
        if strategy_id not in self.strategies:
            self.logger.error(f"Strategy {strategy_id} not found")
            return None
            
        registration = self.strategies[strategy_id]
        
        if registration.status != StrategyStatus.ACTIVE:
            self.logger.warning(f"Strategy {strategy_id} is not active")
            return None
            
        try:
            # Execute strategy
            signals = None
            if hasattr(registration.strategy_instance, 'generate_signals'):
                signals = await self._run_async(
                    registration.strategy_instance.generate_signals,
                    market_data
                )
            elif hasattr(registration.strategy_instance, 'execute'):
                signals = await self._run_async(
                    registration.strategy_instance.execute,
                    market_data
                )
            
            registration.last_executed = datetime.now()
            
            # Update metrics
            await self._update_strategy_metrics(strategy_id, signals)
            
            return signals
            
        except Exception as e:
            registration.status = StrategyStatus.ERROR
            self.logger.error(f"Error executing strategy {strategy_id}: {e}")
            self._add_alert(strategy_id, AlertLevel.ERROR, f"Execution failed: {e}")
            return None
    
    async def _update_strategy_metrics(self, strategy_id: str, signals: Optional[List[TradingSignal]]):
        """Update strategy performance metrics"""
        registration = self.strategies[strategy_id]
        
        if registration.metrics is None:
            registration.metrics = StrategyMetrics(strategy_id=strategy_id)
        
        # Update basic metrics
        registration.metrics.last_updated = datetime.now()
        
        if signals:
            registration.metrics.total_trades += len(signals)
        
        # Store metrics history
        self.performance_history[strategy_id].append(registration.metrics)
    
    def get_strategy_status(self, strategy_id: str) -> Optional[StrategyStatus]:
        """Get strategy status"""
        if strategy_id in self.strategies:
            return self.strategies[strategy_id].status
        return None
    
    def get_strategy_metrics(self, strategy_id: str) -> Optional[StrategyMetrics]:
        """Get strategy performance metrics"""
        if strategy_id in self.strategies:
            return self.strategies[strategy_id].metrics
        return None
    
    def get_all_strategies(self) -> Dict[str, StrategyRegistration]:
        """Get all registered strategies"""
        return self.strategies.copy()
    
    def get_active_strategies(self) -> Dict[str, StrategyRegistration]:
        """Get all active strategies"""
        return {
            sid: reg for sid, reg in self.strategies.items()
            if reg.status == StrategyStatus.ACTIVE
        }
    
    def _add_alert(self, strategy_id: str, level: AlertLevel, message: str):
        """Add strategy alert"""
        alert = StrategyAlert(
            strategy_id=strategy_id,
            level=level,
            message=message
        )
        self.alerts.append(alert)
        
        # Keep only recent alerts
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-500:]
    
    def get_alerts(self, strategy_id: Optional[str] = None) -> List[StrategyAlert]:
        """Get strategy alerts"""
        if strategy_id:
            return [alert for alert in self.alerts if alert.strategy_id == strategy_id]
        return self.alerts.copy()
    
    async def _run_async(self, func, *args, **kwargs):
        """Run function asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, func, *args, **kwargs)
    
    def start_monitoring(self):
        """Start strategy monitoring"""
        if self._running:
            return
            
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_strategies)
        self._monitor_thread.start()
        self.logger.info("Strategy monitoring started")
    
    def stop_monitoring(self):
        """Stop strategy monitoring"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join()
        self.logger.info("Strategy monitoring stopped")
    
    def _monitor_strategies(self):
        """Monitor strategy health and performance"""
        while self._running:
            try:
                for strategy_id, registration in self.strategies.items():
                    # Check strategy health
                    if registration.status == StrategyStatus.ACTIVE:
                        # Check if strategy hasn't executed recently
                        if registration.last_executed:
                            time_since_execution = datetime.now() - registration.last_executed
                            if time_since_execution > timedelta(minutes=30):
                                self._add_alert(
                                    strategy_id,
                                    AlertLevel.WARNING,
                                    "Strategy hasn't executed in 30 minutes"
                                )
                
                # Sleep for monitoring interval
                threading.Event().wait(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in strategy monitoring: {e}")
    
    def shutdown(self):
        """Shutdown strategy manager"""
        self.stop_monitoring()
        self.executor.shutdown(wait=True)
        self.logger.info("Strategy manager shutdown complete")

# Global strategy manager instance
strategy_manager = StrategyManager()

# Convenience functions
def register_strategy(strategy_id: str, strategy_type: Union[StrategyType, str], 
                    config: StrategyConfig, category: StrategyCategory = StrategyCategory.CUSTOM) -> bool:
    """Register a strategy with the global manager"""
    return strategy_manager.register_strategy(strategy_id, strategy_type, config, category)

async def start_strategy(strategy_id: str) -> bool:
    """Start a strategy"""
    return await strategy_manager.start_strategy(strategy_id)

async def execute_strategy(strategy_id: str, market_data: Dict) -> Optional[List[TradingSignal]]:
    """Execute a strategy"""
    return await strategy_manager.execute_strategy(strategy_id, market_data)

def get_strategy_status(strategy_id: str) -> Optional[StrategyStatus]:
    """Get strategy status"""
    return strategy_manager.get_strategy_status(strategy_id)

def get_all_strategies() -> Dict[str, StrategyRegistration]:
    """Get all strategies"""
    return strategy_manager.get_all_strategies()