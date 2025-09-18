#!/usr/bin/env python3
"""
Base Institutional Strategy Class

Institutional-grade base class for trading strategies implementing the 5-Pillar
Strategy Architecture: Signal Generation, Risk Management, Market Regime Adaptation,
Execution Management, and Performance Tracking.

Author: AI Assistant
Date: 2024-12-15
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

class StrategyState(Enum):
    """Strategy execution states"""
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"

class SignalType(Enum):
    """Trading signal types"""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"

class MarketRegime(Enum):
    """Market regime types"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    BREAKOUT = "breakout"
    REVERSAL = "reversal"

class RiskLevel(Enum):
    """Risk level classifications"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

@dataclass
class SignalData:
    """Trading signal data structure"""
    signal_type: SignalType
    confidence: float  # 0.0 to 1.0
    strength: float    # 0.0 to 1.0
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_actionable(self, min_confidence: float = 0.6) -> bool:
        """Check if signal is actionable based on confidence threshold"""
        return self.confidence >= min_confidence and self.signal_type != SignalType.HOLD

@dataclass
class RiskMetrics:
    """Risk management metrics"""
    position_size: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    max_drawdown: float
    var_95: float  # Value at Risk 95%
    sharpe_ratio: float
    risk_level: RiskLevel
    exposure_ratio: float  # Current exposure as ratio of total capital
    
@dataclass
class PerformanceMetrics:
    """Strategy performance metrics"""
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    
@dataclass
class ExecutionOrder:
    """Order execution data"""
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    order_type: str  # 'market', 'limit', 'stop', etc.
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = 'GTC'  # Good Till Cancelled
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

class BaseInstitutionalStrategy(ABC):
    """Base class for institutional-grade trading strategies"""
    
    def __init__(self, 
                 strategy_name: str,
                 symbols: List[str],
                 initial_capital: float = 100000.0,
                 max_position_size: float = 0.1,  # 10% of capital
                 risk_tolerance: RiskLevel = RiskLevel.MEDIUM,
                 min_signal_confidence: float = 0.6,
                 **kwargs):
        """
        Initialize the institutional strategy
        
        Args:
            strategy_name: Name of the strategy
            symbols: List of symbols to trade
            initial_capital: Initial capital allocation
            max_position_size: Maximum position size as ratio of capital
            risk_tolerance: Risk tolerance level
            min_signal_confidence: Minimum confidence for signal execution
        """
        self.strategy_name = strategy_name
        self.symbols = symbols
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.max_position_size = max_position_size
        self.risk_tolerance = risk_tolerance
        self.min_signal_confidence = min_signal_confidence
        
        # Strategy state
        self.state = StrategyState.INACTIVE
        self.start_time: Optional[datetime] = None
        self.last_update: Optional[datetime] = None
        
        # Data storage
        self.price_history: Dict[str, List[float]] = {symbol: [] for symbol in symbols}
        self.volume_history: Dict[str, List[float]] = {symbol: [] for symbol in symbols}
        self.timestamp_history: List[datetime] = []
        
        # Signal tracking
        self.signal_history: List[SignalData] = []
        self.current_signals: Dict[str, SignalData] = {}
        
        # Position tracking
        self.positions: Dict[str, float] = {symbol: 0.0 for symbol in symbols}
        self.entry_prices: Dict[str, float] = {symbol: 0.0 for symbol in symbols}
        
        # Risk management
        self.risk_metrics: Optional[RiskMetrics] = None
        self.stop_losses: Dict[str, float] = {}
        self.take_profits: Dict[str, float] = {}
        
        # Performance tracking
        self.trade_history: List[Dict[str, Any]] = []
        self.performance_metrics: Optional[PerformanceMetrics] = None
        self.equity_curve: List[Tuple[datetime, float]] = []
        
        # Market regime tracking
        self.current_regime: MarketRegime = MarketRegime.SIDEWAYS
        self.regime_history: List[Tuple[datetime, MarketRegime]] = []
        
        # Execution tracking
        self.pending_orders: List[ExecutionOrder] = []
        self.executed_orders: List[ExecutionOrder] = []
        
        # Logging
        self.logger = logging.getLogger(f"Strategy.{strategy_name}")
        
        # Custom parameters
        self.custom_params = kwargs
    
    # =============================================================================
    # PILLAR 1: SIGNAL GENERATION
    # =============================================================================
    
    @abstractmethod
    def generate_signals(self, market_data: Dict[str, Any]) -> Dict[str, SignalData]:
        """
        Generate trading signals based on market data
        
        Args:
            market_data: Dictionary containing market data for all symbols
            
        Returns:
            Dictionary mapping symbols to their signals
        """
        pass
    
    def update_signals(self, market_data: Dict[str, Any]) -> None:
        """Update current signals based on new market data"""
        try:
            new_signals = self.generate_signals(market_data)
            
            for symbol, signal in new_signals.items():
                if symbol in self.symbols:
                    self.current_signals[symbol] = signal
                    self.signal_history.append(signal)
                    
                    # Keep signal history manageable
                    if len(self.signal_history) > 1000:
                        self.signal_history = self.signal_history[-1000:]
            
            self.logger.debug(f"Updated signals for {len(new_signals)} symbols")
            
        except Exception as e:
            self.logger.error(f"Error updating signals: {e}")
            self.state = StrategyState.ERROR
    
    def get_signal_strength(self, symbol: str) -> float:
        """Get current signal strength for a symbol"""
        if symbol in self.current_signals:
            return self.current_signals[symbol].strength
        return 0.0
    
    def get_signal_confidence(self, symbol: str) -> float:
        """Get current signal confidence for a symbol"""
        if symbol in self.current_signals:
            return self.current_signals[symbol].confidence
        return 0.0
    
    # =============================================================================
    # PILLAR 2: RISK MANAGEMENT
    # =============================================================================
    
    def calculate_position_size(self, symbol: str, signal: SignalData, 
                              current_price: float) -> float:
        """
        Calculate appropriate position size based on risk management rules
        
        Args:
            symbol: Trading symbol
            signal: Trading signal
            current_price: Current market price
            
        Returns:
            Position size in shares/units
        """
        if not signal.is_actionable(self.min_signal_confidence):
            return 0.0
        
        # Base position size as percentage of capital
        base_size_ratio = self.max_position_size * signal.confidence * signal.strength
        
        # Adjust for risk tolerance
        risk_multipliers = {
            RiskLevel.VERY_LOW: 0.5,
            RiskLevel.LOW: 0.75,
            RiskLevel.MEDIUM: 1.0,
            RiskLevel.HIGH: 1.25,
            RiskLevel.VERY_HIGH: 1.5
        }
        
        risk_adjusted_ratio = base_size_ratio * risk_multipliers[self.risk_tolerance]
        
        # Calculate position size in dollars
        position_value = self.current_capital * risk_adjusted_ratio
        
        # Convert to shares/units
        position_size = position_value / current_price if current_price > 0 else 0.0
        
        return position_size
    
    def calculate_stop_loss(self, symbol: str, entry_price: float, 
                          signal: SignalData) -> Optional[float]:
        """
        Calculate stop loss level
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            signal: Trading signal
            
        Returns:
            Stop loss price or None
        """
        if signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
            # Long position - stop loss below entry
            stop_distance_ratio = 0.02 * (2.0 - signal.confidence)  # 1-3% based on confidence
            return entry_price * (1.0 - stop_distance_ratio)
        
        elif signal.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
            # Short position - stop loss above entry
            stop_distance_ratio = 0.02 * (2.0 - signal.confidence)
            return entry_price * (1.0 + stop_distance_ratio)
        
        return None
    
    def calculate_take_profit(self, symbol: str, entry_price: float, 
                            signal: SignalData) -> Optional[float]:
        """
        Calculate take profit level
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            signal: Trading signal
            
        Returns:
            Take profit price or None
        """
        if signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
            # Long position - take profit above entry
            profit_ratio = 0.04 * signal.confidence * signal.strength  # 2-4% based on signal quality
            return entry_price * (1.0 + profit_ratio)
        
        elif signal.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
            # Short position - take profit below entry
            profit_ratio = 0.04 * signal.confidence * signal.strength
            return entry_price * (1.0 - profit_ratio)
        
        return None
    
    def update_risk_metrics(self) -> None:
        """Update current risk metrics"""
        try:
            if not self.equity_curve:
                return
            
            # Calculate current exposure
            total_exposure = sum(abs(pos) * self.get_current_price(symbol) 
                               for symbol, pos in self.positions.items())
            exposure_ratio = total_exposure / self.current_capital if self.current_capital > 0 else 0.0
            
            # Calculate returns for risk metrics
            equity_values = [eq[1] for eq in self.equity_curve]
            if len(equity_values) < 2:
                return
            
            returns = np.diff(equity_values) / equity_values[:-1]
            
            # Calculate VaR (95%)
            var_95 = np.percentile(returns, 5) * self.current_capital if len(returns) > 0 else 0.0
            
            # Calculate max drawdown
            peak = np.maximum.accumulate(equity_values)
            drawdown = (equity_values - peak) / peak
            max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0.0
            
            # Calculate Sharpe ratio
            if len(returns) > 1 and np.std(returns) > 0:
                sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)  # Annualized
            else:
                sharpe_ratio = 0.0
            
            # Determine risk level
            if exposure_ratio > 0.8:
                risk_level = RiskLevel.VERY_HIGH
            elif exposure_ratio > 0.6:
                risk_level = RiskLevel.HIGH
            elif exposure_ratio > 0.4:
                risk_level = RiskLevel.MEDIUM
            elif exposure_ratio > 0.2:
                risk_level = RiskLevel.LOW
            else:
                risk_level = RiskLevel.VERY_LOW
            
            self.risk_metrics = RiskMetrics(
                position_size=total_exposure,
                stop_loss=None,  # Aggregate stop loss not applicable
                take_profit=None,  # Aggregate take profit not applicable
                max_drawdown=abs(max_drawdown),
                var_95=abs(var_95),
                sharpe_ratio=sharpe_ratio,
                risk_level=risk_level,
                exposure_ratio=exposure_ratio
            )
            
        except Exception as e:
            self.logger.error(f"Error updating risk metrics: {e}")
    
    # =============================================================================
    # PILLAR 3: MARKET REGIME ADAPTATION
    # =============================================================================
    
    @abstractmethod
    def detect_market_regime(self, market_data: Dict[str, Any]) -> MarketRegime:
        """
        Detect current market regime
        
        Args:
            market_data: Market data for analysis
            
        Returns:
            Current market regime
        """
        pass
    
    def adapt_to_regime(self, regime: MarketRegime) -> None:
        """
        Adapt strategy parameters based on market regime
        
        Args:
            regime: Current market regime
        """
        self.current_regime = regime
        self.regime_history.append((datetime.now(), regime))
        
        # Keep regime history manageable
        if len(self.regime_history) > 100:
            self.regime_history = self.regime_history[-100:]
        
        # Adjust strategy parameters based on regime
        if regime == MarketRegime.HIGH_VOLATILITY:
            # Reduce position sizes in high volatility
            self.max_position_size *= 0.8
            self.min_signal_confidence = min(0.8, self.min_signal_confidence + 0.1)
        
        elif regime == MarketRegime.LOW_VOLATILITY:
            # Can take larger positions in low volatility
            self.max_position_size *= 1.2
            self.min_signal_confidence = max(0.5, self.min_signal_confidence - 0.1)
        
        elif regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            # Trending markets - can be more aggressive
            self.min_signal_confidence = max(0.5, self.min_signal_confidence - 0.05)
        
        elif regime == MarketRegime.SIDEWAYS:
            # Range-bound markets - be more selective
            self.min_signal_confidence = min(0.8, self.min_signal_confidence + 0.1)
        
        self.logger.info(f"Adapted to regime: {regime.value}")
    
    def get_regime_alignment_score(self, signal: SignalData) -> float:
        """
        Calculate how well a signal aligns with current market regime
        
        Args:
            signal: Trading signal to evaluate
            
        Returns:
            Alignment score (0.0 to 1.0)
        """
        regime_signal_alignment = {
            MarketRegime.TRENDING_UP: {
                SignalType.STRONG_BUY: 1.0,
                SignalType.BUY: 0.9,
                SignalType.HOLD: 0.5,
                SignalType.SELL: 0.2,
                SignalType.STRONG_SELL: 0.1
            },
            MarketRegime.TRENDING_DOWN: {
                SignalType.STRONG_BUY: 0.1,
                SignalType.BUY: 0.2,
                SignalType.HOLD: 0.5,
                SignalType.SELL: 0.9,
                SignalType.STRONG_SELL: 1.0
            },
            MarketRegime.SIDEWAYS: {
                SignalType.STRONG_BUY: 0.3,
                SignalType.BUY: 0.4,
                SignalType.HOLD: 1.0,
                SignalType.SELL: 0.4,
                SignalType.STRONG_SELL: 0.3
            }
        }
        
        alignment_map = regime_signal_alignment.get(self.current_regime, {})
        return alignment_map.get(signal.signal_type, 0.5)
    
    # =============================================================================
    # PILLAR 4: EXECUTION MANAGEMENT
    # =============================================================================
    
    def create_order(self, symbol: str, signal: SignalData, 
                    current_price: float) -> Optional[ExecutionOrder]:
        """
        Create an execution order based on signal
        
        Args:
            symbol: Trading symbol
            signal: Trading signal
            current_price: Current market price
            
        Returns:
            Execution order or None
        """
        if not signal.is_actionable(self.min_signal_confidence):
            return None
        
        # Calculate position size
        position_size = self.calculate_position_size(symbol, signal, current_price)
        
        if position_size == 0:
            return None
        
        # Determine order side
        if signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
            side = 'buy'
        elif signal.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
            side = 'sell'
        else:
            return None
        
        # Create order
        order = ExecutionOrder(
            symbol=symbol,
            side=side,
            quantity=abs(position_size),
            order_type='market',  # Default to market orders
            metadata={
                'signal_confidence': signal.confidence,
                'signal_strength': signal.strength,
                'regime': self.current_regime.value,
                'strategy': self.strategy_name
            }
        )
        
        return order
    
    def execute_order(self, order: ExecutionOrder, execution_price: float) -> bool:
        """
        Execute an order (simulate execution)
        
        Args:
            order: Order to execute
            execution_price: Price at which order was executed
            
        Returns:
            True if execution successful
        """
        try:
            symbol = order.symbol
            
            # Update position
            if order.side == 'buy':
                self.positions[symbol] += order.quantity
            else:
                self.positions[symbol] -= order.quantity
            
            # Update entry price (weighted average)
            if symbol in self.entry_prices and self.positions[symbol] != 0:
                total_value = (self.entry_prices[symbol] * abs(self.positions[symbol] - 
                              (order.quantity if order.side == 'buy' else -order.quantity)) +
                              execution_price * order.quantity)
                self.entry_prices[symbol] = total_value / abs(self.positions[symbol])
            else:
                self.entry_prices[symbol] = execution_price
            
            # Calculate and set stop loss and take profit
            if symbol in self.current_signals:
                signal = self.current_signals[symbol]
                self.stop_losses[symbol] = self.calculate_stop_loss(symbol, execution_price, signal)
                self.take_profits[symbol] = self.calculate_take_profit(symbol, execution_price, signal)
            
            # Record trade
            trade_record = {
                'timestamp': order.timestamp,
                'symbol': symbol,
                'side': order.side,
                'quantity': order.quantity,
                'price': execution_price,
                'value': order.quantity * execution_price,
                'position_after': self.positions[symbol],
                'metadata': order.metadata
            }
            
            self.trade_history.append(trade_record)
            self.executed_orders.append(order)
            
            # Update capital (simplified - assumes no fees)
            if order.side == 'buy':
                self.current_capital -= order.quantity * execution_price
            else:
                self.current_capital += order.quantity * execution_price
            
            self.logger.info(f"Executed {order.side} order: {order.quantity} {symbol} @ {execution_price}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing order: {e}")
            return False
    
    def check_exit_conditions(self, symbol: str, current_price: float) -> Optional[ExecutionOrder]:
        """
        Check if any exit conditions are met (stop loss, take profit)
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            
        Returns:
            Exit order if conditions are met
        """
        if self.positions[symbol] == 0:
            return None
        
        position = self.positions[symbol]
        
        # Check stop loss
        if symbol in self.stop_losses and self.stop_losses[symbol] is not None:
            stop_price = self.stop_losses[symbol]
            
            if ((position > 0 and current_price <= stop_price) or 
                (position < 0 and current_price >= stop_price)):
                
                return ExecutionOrder(
                    symbol=symbol,
                    side='sell' if position > 0 else 'buy',
                    quantity=abs(position),
                    order_type='market',
                    metadata={'exit_reason': 'stop_loss'}
                )
        
        # Check take profit
        if symbol in self.take_profits and self.take_profits[symbol] is not None:
            profit_price = self.take_profits[symbol]
            
            if ((position > 0 and current_price >= profit_price) or 
                (position < 0 and current_price <= profit_price)):
                
                return ExecutionOrder(
                    symbol=symbol,
                    side='sell' if position > 0 else 'buy',
                    quantity=abs(position),
                    order_type='market',
                    metadata={'exit_reason': 'take_profit'}
                )
        
        return None
    
    # =============================================================================
    # PILLAR 5: PERFORMANCE TRACKING
    # =============================================================================
    
    def update_performance_metrics(self) -> None:
        """
        Update comprehensive performance metrics
        """
        try:
            if not self.trade_history:
                return
            
            # Calculate equity curve
            current_equity = self.calculate_current_equity()
            self.equity_curve.append((datetime.now(), current_equity))
            
            # Keep equity curve manageable
            if len(self.equity_curve) > 1000:
                self.equity_curve = self.equity_curve[-1000:]
            
            # Calculate returns
            equity_values = [eq[1] for eq in self.equity_curve]
            if len(equity_values) < 2:
                return
            
            returns = np.diff(equity_values) / equity_values[:-1]
            
            # Total return
            total_return = (current_equity - self.initial_capital) / self.initial_capital
            
            # Annualized return
            if self.start_time:
                days_elapsed = (datetime.now() - self.start_time).days
                if days_elapsed > 0:
                    annualized_return = (1 + total_return) ** (365.25 / days_elapsed) - 1
                else:
                    annualized_return = 0.0
            else:
                annualized_return = 0.0
            
            # Volatility (annualized)
            volatility = np.std(returns) * np.sqrt(252) if len(returns) > 1 else 0.0
            
            # Sharpe ratio
            if volatility > 0:
                sharpe_ratio = annualized_return / volatility
            else:
                sharpe_ratio = 0.0
            
            # Sortino ratio (downside deviation)
            negative_returns = returns[returns < 0]
            if len(negative_returns) > 0:
                downside_deviation = np.std(negative_returns) * np.sqrt(252)
                sortino_ratio = annualized_return / downside_deviation if downside_deviation > 0 else 0.0
            else:
                sortino_ratio = sharpe_ratio
            
            # Max drawdown
            peak = np.maximum.accumulate(equity_values)
            drawdown = (equity_values - peak) / peak
            max_drawdown = abs(np.min(drawdown)) if len(drawdown) > 0 else 0.0
            
            # Trade statistics
            winning_trades = [t for t in self.trade_history if self._is_winning_trade(t)]
            losing_trades = [t for t in self.trade_history if self._is_losing_trade(t)]
            
            total_trades = len(self.trade_history)
            win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
            
            # Average win/loss
            if winning_trades:
                avg_win = np.mean([self._calculate_trade_pnl(t) for t in winning_trades])
            else:
                avg_win = 0.0
            
            if losing_trades:
                avg_loss = abs(np.mean([self._calculate_trade_pnl(t) for t in losing_trades]))
            else:
                avg_loss = 0.0
            
            # Profit factor
            total_wins = sum([self._calculate_trade_pnl(t) for t in winning_trades])
            total_losses = abs(sum([self._calculate_trade_pnl(t) for t in losing_trades]))
            profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
            
            self.performance_metrics = PerformanceMetrics(
                total_return=total_return,
                annualized_return=annualized_return,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                max_drawdown=max_drawdown,
                win_rate=win_rate,
                profit_factor=profit_factor,
                total_trades=total_trades,
                winning_trades=len(winning_trades),
                losing_trades=len(losing_trades),
                avg_win=avg_win,
                avg_loss=avg_loss
            )
            
        except Exception as e:
            self.logger.error(f"Error updating performance metrics: {e}")
    
    def calculate_current_equity(self) -> float:
        """Calculate current total equity"""
        position_value = sum(
            pos * self.get_current_price(symbol) 
            for symbol, pos in self.positions.items()
        )
        return self.current_capital + position_value
    
    def _is_winning_trade(self, trade: Dict[str, Any]) -> bool:
        """Check if a trade is winning (simplified)"""
        # This is a simplified implementation
        # In practice, you'd need to match entry/exit trades
        return self._calculate_trade_pnl(trade) > 0
    
    def _is_losing_trade(self, trade: Dict[str, Any]) -> bool:
        """Check if a trade is losing (simplified)"""
        return self._calculate_trade_pnl(trade) < 0
    
    def _calculate_trade_pnl(self, trade: Dict[str, Any]) -> float:
        """Calculate trade P&L (simplified)"""
        # This is a simplified implementation
        # In practice, you'd need more sophisticated trade matching
        symbol = trade['symbol']
        current_price = self.get_current_price(symbol)
        entry_price = trade['price']
        quantity = trade['quantity']
        
        if trade['side'] == 'buy':
            return (current_price - entry_price) * quantity
        else:
            return (entry_price - current_price) * quantity
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol"""
        if symbol in self.price_history and self.price_history[symbol]:
            return self.price_history[symbol][-1]
        return 0.0
    
    def update_market_data(self, market_data: Dict[str, Any]) -> None:
        """
        Update internal market data storage
        
        Args:
            market_data: Dictionary containing price and volume data
        """
        timestamp = datetime.now()
        self.timestamp_history.append(timestamp)
        self.last_update = timestamp
        
        for symbol in self.symbols:
            if symbol in market_data:
                data = market_data[symbol]
                
                # Update price history
                if 'price' in data:
                    self.price_history[symbol].append(data['price'])
                    
                    # Keep reasonable history
                    if len(self.price_history[symbol]) > 1000:
                        self.price_history[symbol] = self.price_history[symbol][-1000:]
                
                # Update volume history
                if 'volume' in data:
                    self.volume_history[symbol].append(data['volume'])
                    
                    if len(self.volume_history[symbol]) > 1000:
                        self.volume_history[symbol] = self.volume_history[symbol][-1000:]
    
    def start_strategy(self) -> None:
        """Start the strategy"""
        self.state = StrategyState.ACTIVE
        self.start_time = datetime.now()
        self.logger.info(f"Strategy {self.strategy_name} started")
    
    def stop_strategy(self) -> None:
        """Stop the strategy"""
        self.state = StrategyState.STOPPED
        self.logger.info(f"Strategy {self.strategy_name} stopped")
    
    def pause_strategy(self) -> None:
        """Pause the strategy"""
        self.state = StrategyState.PAUSED
        self.logger.info(f"Strategy {self.strategy_name} paused")
    
    def resume_strategy(self) -> None:
        """Resume the strategy"""
        self.state = StrategyState.ACTIVE
        self.logger.info(f"Strategy {self.strategy_name} resumed")
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """Get comprehensive strategy status"""
        return {
            'name': self.strategy_name,
            'state': self.state.value,
            'symbols': self.symbols,
            'current_capital': self.current_capital,
            'positions': self.positions,
            'current_signals': {k: v.signal_type.value for k, v in self.current_signals.items()},
            'current_regime': self.current_regime.value,
            'risk_metrics': self.risk_metrics.__dict__ if self.risk_metrics else None,
            'performance_metrics': self.performance_metrics.__dict__ if self.performance_metrics else None,
            'total_trades': len(self.trade_history),
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'last_update': self.last_update.isoformat() if self.last_update else None
        }
    
    def run_strategy_cycle(self, market_data: Dict[str, Any]) -> List[ExecutionOrder]:
        """
        Run a complete strategy cycle
        
        Args:
            market_data: Current market data
            
        Returns:
            List of orders to execute
        """
        if self.state != StrategyState.ACTIVE:
            return []
        
        orders_to_execute = []
        
        try:
            # Update market data
            self.update_market_data(market_data)
            
            # Detect market regime and adapt
            regime = self.detect_market_regime(market_data)
            if regime != self.current_regime:
                self.adapt_to_regime(regime)
            
            # Update signals
            self.update_signals(market_data)
            
            # Check exit conditions for existing positions
            for symbol in self.symbols:
                if self.positions[symbol] != 0:
                    current_price = self.get_current_price(symbol)
                    exit_order = self.check_exit_conditions(symbol, current_price)
                    if exit_order:
                        orders_to_execute.append(exit_order)
            
            # Generate new entry orders
            for symbol, signal in self.current_signals.items():
                if signal.is_actionable(self.min_signal_confidence):
                    current_price = self.get_current_price(symbol)
                    order = self.create_order(symbol, signal, current_price)
                    if order:
                        orders_to_execute.append(order)
            
            # Update risk and performance metrics
            self.update_risk_metrics()
            self.update_performance_metrics()
            
        except Exception as e:
            self.logger.error(f"Error in strategy cycle: {e}")
            self.state = StrategyState.ERROR
        
        return orders_to_execute

# Example implementation for testing
class ExampleMomentumStrategy(BaseInstitutionalStrategy):
    """Example momentum strategy implementation"""
    
    def __init__(self, **kwargs):
        super().__init__(
            strategy_name="Example Momentum Strategy",
            symbols=["AAPL", "MSFT", "GOOGL"],
            **kwargs
        )
        self.lookback_period = 20
    
    def generate_signals(self, market_data: Dict[str, Any]) -> Dict[str, SignalData]:
        """Simple momentum-based signal generation"""
        signals = {}
        
        for symbol in self.symbols:
            if (symbol in self.price_history and 
                len(self.price_history[symbol]) >= self.lookback_period):
                
                prices = np.array(self.price_history[symbol][-self.lookback_period:])
                
                # Simple momentum calculation
                momentum = (prices[-1] - prices[0]) / prices[0]
                
                # Generate signal based on momentum
                if momentum > 0.05:  # 5% positive momentum
                    signal_type = SignalType.BUY
                    confidence = min(0.9, 0.6 + abs(momentum) * 2)
                    strength = min(1.0, abs(momentum) * 10)
                elif momentum < -0.05:  # 5% negative momentum
                    signal_type = SignalType.SELL
                    confidence = min(0.9, 0.6 + abs(momentum) * 2)
                    strength = min(1.0, abs(momentum) * 10)
                else:
                    signal_type = SignalType.HOLD
                    confidence = 0.5
                    strength = 0.0
                
                signals[symbol] = SignalData(
                    signal_type=signal_type,
                    confidence=confidence,
                    strength=strength,
                    timestamp=datetime.now(),
                    metadata={'momentum': momentum}
                )
        
        return signals
    
    def detect_market_regime(self, market_data: Dict[str, Any]) -> MarketRegime:
        """Simple market regime detection"""
        if not self.price_history:
            return MarketRegime.SIDEWAYS
        
        # Use the first symbol as market proxy
        symbol = self.symbols[0]
        if (symbol in self.price_history and 
            len(self.price_history[symbol]) >= self.lookback_period):
            
            prices = np.array(self.price_history[symbol][-self.lookback_period:])
            volatility = np.std(prices) / np.mean(prices)
            
            # Simple regime classification
            if volatility > 0.03:
                return MarketRegime.HIGH_VOLATILITY
            elif volatility < 0.01:
                return MarketRegime.LOW_VOLATILITY
            else:
                # Check trend
                trend = (prices[-1] - prices[0]) / prices[0]
                if trend > 0.02:
                    return MarketRegime.TRENDING_UP
                elif trend < -0.02:
                    return MarketRegime.TRENDING_DOWN
                else:
                    return MarketRegime.SIDEWAYS
        
        return MarketRegime.SIDEWAYS

# Example usage
if __name__ == "__main__":
    # Create strategy instance
    strategy = ExampleMomentumStrategy(
        initial_capital=100000.0,
        max_position_size=0.1,
        risk_tolerance=RiskLevel.MEDIUM
    )
    
    # Start strategy
    strategy.start_strategy()
    
    # Simulate market data updates
    np.random.seed(42)
    base_prices = {"AAPL": 150.0, "MSFT": 300.0, "GOOGL": 2500.0}
    
    print("Institutional Strategy Test")
    print("=" * 40)
    
    for i in range(50):
        # Simulate price movements
        market_data = {}
        for symbol in strategy.symbols:
            price_change = np.random.randn() * 0.02  # 2% daily volatility
            base_prices[symbol] *= (1 + price_change)
            
            market_data[symbol] = {
                'price': base_prices[symbol],
                'volume': np.random.randint(1000000, 5000000)
            }
        
        # Run strategy cycle
        orders = strategy.run_strategy_cycle(market_data)
        
        # Execute orders (simulate)
        for order in orders:
            execution_price = market_data[order.symbol]['price']
            strategy.execute_order(order, execution_price)
        
        # Print status every 10 cycles
        if i % 10 == 0:
            status = strategy.get_strategy_status()
            print(f"Cycle {i+1}:")
            print(f"  Capital: ${status['current_capital']:.2f}")
            print(f"  Positions: {status['positions']}")
            print(f"  Regime: {status['current_regime']}")
            print(f"  Total Trades: {status['total_trades']}")
            
            if strategy.performance_metrics:
                print(f"  Total Return: {strategy.performance_metrics.total_return:.2%}")
                print(f"  Sharpe Ratio: {strategy.performance_metrics.sharpe_ratio:.2f}")
            print("-" * 40)
    
    # Final status
    final_status = strategy.get_strategy_status()
    print("\nFinal Strategy Status:")
    print(f"Total Return: {strategy.performance_metrics.total_return:.2%}" if strategy.performance_metrics else "No performance data")
    print(f"Total Trades: {final_status['total_trades']}")
    print(f"Final Capital: ${final_status['current_capital']:.2f}")