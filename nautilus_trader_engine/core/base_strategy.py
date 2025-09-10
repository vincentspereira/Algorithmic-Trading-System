"""Base Strategy Framework

This module provides the foundational classes for implementing trading strategies
in the Nautilus Trader Engine.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

import pandas as pd
from pydantic import BaseModel, Field


class StrategyState(Enum):
    """Strategy execution states"""
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class StrategyType(Enum):
    """Strategy types"""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    ARBITRAGE = "arbitrage"
    MARKET_MAKING = "market_making"
    ML_BASED = "ml_based"
    CUSTOM = "custom"


@dataclass
class StrategyMetrics:
    """Strategy performance metrics"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    avg_trade_duration: float = 0.0
    last_updated: Optional[datetime] = None


class StrategyConfig(BaseModel):
    """Base strategy configuration"""
    strategy_id: str = Field(..., description="Unique strategy identifier")
    strategy_type: StrategyType = Field(default=StrategyType.CUSTOM, description="Strategy type")
    enabled: bool = Field(default=True, description="Whether strategy is enabled")
    max_position_size: float = Field(default=1.0, description="Maximum position size")
    risk_limit: float = Field(default=0.02, description="Risk limit as fraction of portfolio")
    stop_loss_pct: Optional[float] = Field(default=None, description="Stop loss percentage")
    take_profit_pct: Optional[float] = Field(default=None, description="Take profit percentage")
    
    # Timing configuration
    execution_frequency: int = Field(default=60, description="Execution frequency in seconds")
    warmup_period: int = Field(default=100, description="Warmup period in bars")
    
    # Risk management
    max_daily_loss: Optional[float] = Field(default=None, description="Maximum daily loss")
    max_drawdown: Optional[float] = Field(default=None, description="Maximum drawdown threshold")
    
    # Logging and monitoring
    log_level: str = Field(default="INFO", description="Logging level")
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    
    class Config:
        use_enum_values = True


class BaseStrategy(ABC):
    """Base class for all trading strategies
    
    Provides common functionality and interface for strategy implementation.
    All custom strategies should inherit from this class.
    """
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.strategy_id = config.strategy_id
        self.logger = logging.getLogger(f"Strategy.{self.strategy_id}")
        
        # Strategy state
        self.state = StrategyState.INITIALIZED
        self.is_active = False
        self.start_time: Optional[datetime] = None
        self.stop_time: Optional[datetime] = None
        
        # Performance tracking
        self.metrics = StrategyMetrics()
        self.trade_history: List[Dict[str, Any]] = []
        self.position_history: List[Dict[str, Any]] = []
        
        # Data storage
        self.market_data: Dict[str, Any] = {}
        self.indicators: Dict[str, Any] = {}
        self.signals: List[Dict[str, Any]] = []
        
        # Risk management
        self.current_positions: Dict[str, float] = {}
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        
        # Event handlers
        self._event_handlers: Dict[str, List[callable]] = {}
        
        self.logger.info(f"Strategy {self.strategy_id} initialized")
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the strategy
        
        This method should be implemented by subclasses to perform
        strategy-specific initialization.
        """
        pass
    
    @abstractmethod
    async def on_market_data(self, data: Dict[str, Any]) -> None:
        """Handle incoming market data
        
        Args:
            data: Market data dictionary containing price, volume, etc.
        """
        pass
    
    @abstractmethod
    async def generate_signals(self) -> List[Dict[str, Any]]:
        """Generate trading signals
        
        Returns:
            List of trading signals
        """
        pass
    
    async def start(self) -> None:
        """Start the strategy"""
        try:
            if self.state != StrategyState.INITIALIZED:
                raise RuntimeError(f"Cannot start strategy in state: {self.state}")
            
            self.logger.info(f"Starting strategy {self.strategy_id}")
            
            # Initialize strategy-specific components
            await self.initialize()
            
            # Update state
            self.state = StrategyState.RUNNING
            self.is_active = True
            self.start_time = datetime.now()
            
            # Emit start event
            await self._emit_event('strategy_started', {'strategy_id': self.strategy_id})
            
            self.logger.info(f"Strategy {self.strategy_id} started successfully")
            
        except Exception as e:
            self.state = StrategyState.ERROR
            self.logger.error(f"Failed to start strategy {self.strategy_id}: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the strategy"""
        try:
            self.logger.info(f"Stopping strategy {self.strategy_id}")
            
            # Update state
            self.state = StrategyState.STOPPED
            self.is_active = False
            self.stop_time = datetime.now()
            
            # Perform cleanup
            await self.cleanup()
            
            # Emit stop event
            await self._emit_event('strategy_stopped', {'strategy_id': self.strategy_id})
            
            self.logger.info(f"Strategy {self.strategy_id} stopped")
            
        except Exception as e:
            self.state = StrategyState.ERROR
            self.logger.error(f"Error stopping strategy {self.strategy_id}: {e}")
            raise
    
    async def pause(self) -> None:
        """Pause the strategy"""
        if self.state == StrategyState.RUNNING:
            self.state = StrategyState.PAUSED
            self.is_active = False
            await self._emit_event('strategy_paused', {'strategy_id': self.strategy_id})
            self.logger.info(f"Strategy {self.strategy_id} paused")
    
    async def resume(self) -> None:
        """Resume the strategy"""
        if self.state == StrategyState.PAUSED:
            self.state = StrategyState.RUNNING
            self.is_active = True
            await self._emit_event('strategy_resumed', {'strategy_id': self.strategy_id})
            self.logger.info(f"Strategy {self.strategy_id} resumed")
    
    async def cleanup(self) -> None:
        """Cleanup strategy resources
        
        Override this method to perform strategy-specific cleanup.
        """
        pass
    
    def update_metrics(self, trade_result: Dict[str, Any]) -> None:
        """Update strategy performance metrics
        
        Args:
            trade_result: Dictionary containing trade information
        """
        if not self.config.enable_metrics:
            return
        
        pnl = trade_result.get('pnl', 0.0)
        
        self.metrics.total_trades += 1
        self.metrics.total_pnl += pnl
        
        if pnl > 0:
            self.metrics.winning_trades += 1
        else:
            self.metrics.losing_trades += 1
        
        # Update win rate
        self.metrics.win_rate = self.metrics.winning_trades / self.metrics.total_trades
        
        # Update drawdown
        if pnl < 0:
            self.metrics.max_drawdown = min(self.metrics.max_drawdown, pnl)
        
        self.metrics.last_updated = datetime.now()
        
        # Store trade history
        self.trade_history.append({
            'timestamp': datetime.now(),
            'pnl': pnl,
            **trade_result
        })
    
    def get_metrics(self) -> StrategyMetrics:
        """Get current strategy metrics
        
        Returns:
            Current strategy metrics
        """
        return self.metrics
    
    def get_state(self) -> Dict[str, Any]:
        """Get current strategy state
        
        Returns:
            Dictionary containing strategy state information
        """
        return {
            'strategy_id': self.strategy_id,
            'state': self.state.value,
            'is_active': self.is_active,
            'start_time': self.start_time,
            'stop_time': self.stop_time,
            'metrics': self.metrics,
            'current_positions': self.current_positions,
            'daily_pnl': self.daily_pnl,
            'total_pnl': self.total_pnl
        }
    
    def add_event_handler(self, event_type: str, handler: callable) -> None:
        """Add event handler
        
        Args:
            event_type: Type of event to handle
            handler: Callable to handle the event
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit event to registered handlers
        
        Args:
            event_type: Type of event
            data: Event data
        """
        if event_type in self._event_handlers:
            for handler in self._event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    self.logger.error(f"Error in event handler for {event_type}: {e}")
    
    def validate_config(self) -> bool:
        """Validate strategy configuration
        
        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            # Basic validation
            if not self.config.strategy_id:
                self.logger.error("Strategy ID is required")
                return False
            
            if self.config.max_position_size <= 0:
                self.logger.error("Max position size must be positive")
                return False
            
            if self.config.risk_limit <= 0 or self.config.risk_limit > 1:
                self.logger.error("Risk limit must be between 0 and 1")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Configuration validation error: {e}")
            return False
    
    def __str__(self) -> str:
        return f"Strategy({self.strategy_id}, {self.state.value})"
    
    def __repr__(self) -> str:
        return f"BaseStrategy(strategy_id='{self.strategy_id}', state='{self.state.value}')"


# Factory function for creating strategies
def create_strategy(strategy_class: type, config: StrategyConfig) -> BaseStrategy:
    """Factory function to create strategy instances
    
    Args:
        strategy_class: Strategy class to instantiate
        config: Strategy configuration
    
    Returns:
        Strategy instance
    """
    if not issubclass(strategy_class, BaseStrategy):
        raise ValueError("Strategy class must inherit from BaseStrategy")
    
    return strategy_class(config)


# Example usage
if __name__ == "__main__":
    # Example configuration
    config = StrategyConfig(
        strategy_id="example_strategy",
        strategy_type=StrategyType.MOMENTUM,
        max_position_size=1000.0,
        risk_limit=0.02
    )
    
    print(f"Created strategy config: {config.strategy_id}")