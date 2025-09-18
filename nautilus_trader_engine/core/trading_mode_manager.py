""".
trading_mode_manager.py

Trading Mode Manager for seamless switching between paper and live trading.

This module provides:
- Safe mode switching with validation
- Configuration management for different modes
- Risk controls and compliance checks
- Event logging for audit trails
"""

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional, Any

from nautilus_trader.config import TradingNodeConfig
from nautilus_trader.live.node import TradingNode

from nautilus_trader_engine.config.ib_config import (
    get_ib_paper_trading_config,
    get_ib_live_trading_config
)
from shared.config import settings


class TradingMode(Enum):
    """Trading mode enumeration."""
    PAPER = "paper"
    LIVE = "live"
    SIMULATION = "simulation"


class TradingModeManager:
    """Manages trading mode switching and configuration."""

    def __init__(self):
        self._current_mode = TradingMode.PAPER
        self._trading_node: Optional[TradingNode] = None
        self._is_running = False
        self._logger = logging.getLogger(__name__)
        self._mode_history = []
        self._risk_limits = {
            TradingMode.PAPER: {
                "max_position_size": 1000000,  # $1M
                "max_daily_loss": 50000,      # $50K
                "max_orders_per_minute": 100
            },
            TradingMode.LIVE: {
                "max_position_size": 100000,   # $100K
                "max_daily_loss": 5000,       # $5K
                "max_orders_per_minute": 10
            }
        }

    @property
    def current_mode(self) -> TradingMode:
        """Get the current trading mode."""
        return self._current_mode

    @property
    def is_running(self) -> bool:
        """Check if trading node is running."""
        return self._is_running

    async def initialize(self, mode: TradingMode = TradingMode.PAPER) -> bool:
        """Initialize the trading mode manager.
        
        Args:
            mode: Initial trading mode
            
        Returns:
            True if initialization successful
        """
        try:
            self._current_mode = mode
            config = self._get_config_for_mode(mode)
            
            self._trading_node = TradingNode(config=config)
            
            self._log_mode_change(None, mode, "initialization")
            self._logger.info(f"Trading mode manager initialized in {mode.value} mode")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to initialize trading mode manager: {e}")
            return False

    async def start_trading(self) -> bool:
        """Start the trading node.
        
        Returns:
            True if started successfully
        """
        if not self._trading_node:
            self._logger.error("Trading node not initialized")
            return False
            
        try:
            await self._trading_node.start_async()
            self._is_running = True
            self._logger.info(f"Trading started in {self._current_mode.value} mode")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to start trading: {e}")
            return False

    async def stop_trading(self) -> bool:
        """Stop the trading node.
        
        Returns:
            True if stopped successfully
        """
        if not self._trading_node or not self._is_running:
            return True
            
        try:
            await self._trading_node.stop_async()
            self._is_running = False
            self._logger.info(f"Trading stopped in {self._current_mode.value} mode")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to stop trading: {e}")
            return False

    async def switch_mode(self, new_mode: TradingMode, force: bool = False) -> bool:
        """Switch trading mode with safety checks.
        
        Args:
            new_mode: Target trading mode
            force: Skip safety checks if True
            
        Returns:
            True if mode switch successful
        """
        if new_mode == self._current_mode:
            self._logger.info(f"Already in {new_mode.value} mode")
            return True

        # Safety checks
        if not force and not await self._validate_mode_switch(new_mode):
            return False

        old_mode = self._current_mode
        
        try:
            # Stop current trading
            if self._is_running:
                await self.stop_trading()

            # Switch configuration
            config = self._get_config_for_mode(new_mode)
            self._trading_node = TradingNode(config=config)
            self._current_mode = new_mode

            # Restart if it was running
            if self._is_running:
                await self.start_trading()

            self._log_mode_change(old_mode, new_mode, "manual_switch")
            self._logger.info(f"Successfully switched from {old_mode.value} to {new_mode.value}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to switch mode: {e}")
            # Try to revert
            try:
                config = self._get_config_for_mode(old_mode)
                self._trading_node = TradingNode(config=config)
                self._current_mode = old_mode
                self._logger.info(f"Reverted to {old_mode.value} mode")
            except Exception as revert_error:
                self._logger.critical(f"Failed to revert mode: {revert_error}")
            return False

    async def _validate_mode_switch(self, new_mode: TradingMode) -> bool:
        """Validate if mode switch is safe.
        
        Args:
            new_mode: Target trading mode
            
        Returns:
            True if switch is safe
        """
        # Check if switching to live mode
        if new_mode == TradingMode.LIVE:
            # Additional validation for live trading
            if not self._validate_live_trading_requirements():
                return False
                
            # Check recent performance in paper mode
            if not self._validate_paper_trading_performance():
                self._logger.warning("Paper trading performance validation failed")
                return False

        # Check for open positions
        if self._trading_node and await self._has_open_positions():
            self._logger.warning("Cannot switch modes with open positions")
            return False

        return True

    def _validate_live_trading_requirements(self) -> bool:
        """Validate requirements for live trading.
        
        Returns:
            True if requirements are met
        """
        # Check if live trading is enabled
        if not getattr(settings, 'ENABLE_LIVE_TRADING', False):
            self._logger.error("Live trading is not enabled in configuration")
            return False

        # Check account configuration
        if not settings.IB_LIVE_ACCOUNT or settings.IB_LIVE_ACCOUNT == "U1234567":
            self._logger.error("Live trading account not properly configured")
            return False

        return True

    def _validate_paper_trading_performance(self) -> bool:
        """Validate paper trading performance before switching to live.
        
        Returns:
            True if performance is acceptable
        """
        # This would typically check recent P&L, Sharpe ratio, etc.
        # For now, return True as a placeholder
        return True

    async def _has_open_positions(self) -> bool:
        """Check if there are open positions.
        
        Returns:
            True if there are open positions
        """
        if not self._trading_node:
            return False
            
        try:
            # This would check the portfolio for open positions
            # For now, return False as a placeholder
            return False
        except Exception:
            return False

    def _get_config_for_mode(self, mode: TradingMode) -> TradingNodeConfig:
        """Get configuration for the specified mode.
        
        Args:
            mode: Trading mode
            
        Returns:
            TradingNodeConfig for the mode
        """
        if mode == TradingMode.PAPER:
            return get_ib_paper_trading_config()
        elif mode == TradingMode.LIVE:
            return get_ib_live_trading_config()
        else:
            raise ValueError(f"Unsupported trading mode: {mode}")

    def _log_mode_change(self, old_mode: Optional[TradingMode], 
                        new_mode: TradingMode, reason: str):
        """Log mode change for audit trail.
        
        Args:
            old_mode: Previous mode
            new_mode: New mode
            reason: Reason for change
        """
        change_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "old_mode": old_mode.value if old_mode else None,
            "new_mode": new_mode.value,
            "reason": reason
        }
        
        self._mode_history.append(change_record)
        
        # Keep only last 100 records
        if len(self._mode_history) > 100:
            self._mode_history = self._mode_history[-100:]

    def get_mode_history(self) -> list:
        """Get mode change history.
        
        Returns:
            List of mode change records
        """
        return self._mode_history.copy()

    def get_risk_limits(self, mode: Optional[TradingMode] = None) -> Dict[str, Any]:
        """Get risk limits for the specified mode.
        
        Args:
            mode: Trading mode (current mode if None)
            
        Returns:
            Risk limits dictionary
        """
        target_mode = mode or self._current_mode
        return self._risk_limits.get(target_mode, {}).copy()

    async def emergency_stop(self) -> bool:
        """Emergency stop all trading activities.
        
        Returns:
            True if emergency stop successful
        """
        try:
            if self._trading_node and self._is_running:
                await self._trading_node.stop_async()
                self._is_running = False
                
            self._log_mode_change(self._current_mode, self._current_mode, "emergency_stop")
            self._logger.critical("Emergency stop executed")
            return True
            
        except Exception as e:
            self._logger.critical(f"Emergency stop failed: {e}")
            return False


# Global instance
trading_mode_manager = TradingModeManager()