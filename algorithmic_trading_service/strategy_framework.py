"""Trading Strategy Framework

Comprehensive framework for implementing and managing trading strategies
with signal generation, backtesting, and live execution capabilities.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import asyncio
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
from dataclasses import dataclass, field
import logging
from collections import deque

from pydantic import BaseModel, Field, validator
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database.database_manager import DatabaseManager, Strategy as StrategyModel
from shared.utils.logging_utils import get_logger
from market_data.market_data_service import MarketDataService

logger = get_logger(__name__)

# ===========================================
# ENUMS AND CONSTANTS
# ===========================================

class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"

class StrategyStatus(str, Enum):
    INACTIVE = "INACTIVE"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ERROR = "ERROR"
    BACKTESTING = "BACKTESTING"

class TimeFrame(str, Enum):
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1w"
    MONTH_1 = "1M"

class IndicatorType(str, Enum):
    SMA = "SMA"  # Simple Moving Average
    EMA = "EMA"  # Exponential Moving Average
    RSI = "RSI"  # Relative Strength Index
    MACD = "MACD"  # Moving Average Convergence Divergence
    BOLLINGER = "BOLLINGER"  # Bollinger Bands
    STOCHASTIC = "STOCHASTIC"  # Stochastic Oscillator
    ATR = "ATR"  # Average True Range
    VOLUME = "VOLUME"  # Volume indicators

# ===========================================
# DATA MODELS
# ===========================================

@dataclass
class TradingSignal:
    """Trading signal data structure"""
    symbol: str
    signal_type: SignalType
    strength: float  # Signal strength (0.0 to 1.0)
    price: float
    timestamp: datetime
    strategy_name: str
    indicators: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5  # Confidence level (0.0 to 1.0)
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size: Optional[float] = None

@dataclass
class StrategyParameters:
    """Base strategy parameters"""
    symbol: str
    timeframe: TimeFrame
    lookback_period: int = 100
    risk_per_trade: float = 0.02  # 2% risk per trade
    max_positions: int = 5
    stop_loss_pct: float = 0.02  # 2% stop loss
    take_profit_pct: float = 0.04  # 4% take profit
    min_volume: int = 100000  # Minimum daily volume
    custom_params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StrategyPerformance:
    """Strategy performance metrics"""
    strategy_name: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class StrategyConfig(BaseModel):
    """Strategy configuration model"""
    name: str
    description: str
    parameters: Dict[str, Any]
    symbols: List[str]
    timeframes: List[TimeFrame]
    enabled: bool = True
    risk_management: Dict[str, Any] = Field(default_factory=dict)
    
class StrategySignalResponse(BaseModel):
    """Strategy signal response"""
    signals: List[Dict[str, Any]] = Field(default_factory=list)
    indicators: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    performance: Dict[str, Any] = Field(default_factory=dict)
    status: StrategyStatus
    last_updated: datetime

# ===========================================
# TECHNICAL INDICATORS
# ===========================================

class TechnicalIndicators:
    """Technical indicators calculation utilities"""
    
    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        return data.rolling(window=period).mean()
    
    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average"""
        return data.ewm(span=period).mean()
    
    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD (Moving Average Convergence Divergence)"""
        ema_fast = TechnicalIndicators.ema(data, fast)
        ema_slow = TechnicalIndicators.ema(data, slow)
        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators.ema(macd_line, signal)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Bollinger Bands"""
        sma = TechnicalIndicators.sma(data, period)
        std = data.rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        return upper_band, sma, lower_band
    
    @staticmethod
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Stochastic Oscillator"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()
        return k_percent, d_percent
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Average True Range"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return true_range.rolling(window=period).mean()

# ===========================================
# BASE STRATEGY CLASS
# ===========================================

class BaseStrategy(ABC):
    """Abstract base class for all trading strategies"""
    
    def __init__(
        self, 
        name: str, 
        parameters: StrategyParameters,
        market_data_service: MarketDataService,
        db_manager: DatabaseManager
    ):
        self.name = name
        self.parameters = parameters
        self.market_data_service = market_data_service
        self.db_manager = db_manager
        self.status = StrategyStatus.INACTIVE
        self.performance = StrategyPerformance(strategy_name=name)
        self.indicators = TechnicalIndicators()
        self.data_cache: Dict[str, pd.DataFrame] = {}
        self.signal_history: deque = deque(maxlen=1000)
        self.last_signals: Dict[str, TradingSignal] = {}
        
    @abstractmethod
    async def generate_signals(self, symbol: str) -> List[TradingSignal]:
        """Generate trading signals for a symbol"""
        pass
    
    @abstractmethod
    async def calculate_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate technical indicators"""
        pass
    
    async def initialize(self):
        """Initialize strategy"""
        try:
            await self._load_historical_data()
            self.status = StrategyStatus.ACTIVE
            logger.info(f"Strategy {self.name} initialized successfully")
        except Exception as e:
            self.status = StrategyStatus.ERROR
            logger.error(f"Error initializing strategy {self.name}: {e}")
            raise
    
    async def update_data(self, symbol: str, timeframe: TimeFrame) -> pd.DataFrame:
        """Update market data for symbol"""
        try:
            # Get latest data from market data service
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=self.parameters.lookback_period)
            
            # This would call the actual market data service
            # For now, return mock data structure
            data = await self._get_mock_data(symbol, start_time, end_time, timeframe)
            
            # Cache the data
            cache_key = f"{symbol}_{timeframe.value}"
            self.data_cache[cache_key] = data
            
            return data
            
        except Exception as e:
            logger.error(f"Error updating data for {symbol}: {e}")
            raise
    
    async def run_strategy(self, symbols: List[str]) -> List[TradingSignal]:
        """Run strategy for multiple symbols"""
        all_signals = []
        
        try:
            for symbol in symbols:
                # Update data
                await self.update_data(symbol, self.parameters.timeframe)
                
                # Generate signals
                signals = await self.generate_signals(symbol)
                all_signals.extend(signals)
                
                # Store latest signal
                if signals:
                    self.last_signals[symbol] = signals[-1]
                    self.signal_history.extend(signals)
            
            # Update performance metrics
            await self._update_performance_metrics()
            
            return all_signals
            
        except Exception as e:
            logger.error(f"Error running strategy {self.name}: {e}")
            self.status = StrategyStatus.ERROR
            return []
    
    async def backtest(self, start_date: datetime, end_date: datetime, symbols: List[str]) -> StrategyPerformance:
        """Backtest strategy over historical period"""
        try:
            self.status = StrategyStatus.BACKTESTING
            
            # Initialize backtest metrics
            backtest_performance = StrategyPerformance(
                strategy_name=f"{self.name}_backtest",
                start_date=start_date,
                end_date=end_date
            )
            
            # Run backtest simulation
            for symbol in symbols:
                # Get historical data
                historical_data = await self._get_historical_data(symbol, start_date, end_date)
                
                # Simulate strategy execution
                trades = await self._simulate_trades(symbol, historical_data)
                
                # Update performance metrics
                backtest_performance = self._calculate_backtest_performance(backtest_performance, trades)
            
            self.status = StrategyStatus.ACTIVE
            return backtest_performance
            
        except Exception as e:
            logger.error(f"Error backtesting strategy {self.name}: {e}")
            self.status = StrategyStatus.ERROR
            raise
    
    def get_current_performance(self) -> StrategyPerformance:
        """Get current strategy performance"""
        return self.performance
    
    def pause(self):
        """Pause strategy execution"""
        self.status = StrategyStatus.PAUSED
        logger.info(f"Strategy {self.name} paused")
    
    def resume(self):
        """Resume strategy execution"""
        self.status = StrategyStatus.ACTIVE
        logger.info(f"Strategy {self.name} resumed")
    
    def stop(self):
        """Stop strategy execution"""
        self.status = StrategyStatus.INACTIVE
        logger.info(f"Strategy {self.name} stopped")
    
    # ===========================================
    # PRIVATE HELPER METHODS
    # ===========================================
    
    async def _load_historical_data(self):
        """Load initial historical data"""
        # This would load historical data for initialization
        pass
    
    async def _get_mock_data(self, symbol: str, start_time: datetime, end_time: datetime, timeframe: TimeFrame) -> pd.DataFrame:
        """Generate mock market data for testing"""
        # Generate mock OHLCV data
        periods = 100
        dates = pd.date_range(start=start_time, end=end_time, periods=periods)
        
        # Generate realistic price data
        np.random.seed(42)  # For reproducible results
        base_price = 100.0
        returns = np.random.normal(0.001, 0.02, periods)  # Daily returns
        prices = [base_price]
        
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        # Create OHLCV data
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': np.random.randint(10000, 1000000, periods)
        })
        
        data.set_index('timestamp', inplace=True)
        return data
    
    async def _get_historical_data(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Get historical data for backtesting"""
        return await self._get_mock_data(symbol, start_date, end_date, self.parameters.timeframe)
    
    async def _simulate_trades(self, symbol: str, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Simulate trades for backtesting"""
        trades = []
        position = None
        
        for i in range(len(data)):
            current_data = data.iloc[:i+1]
            if len(current_data) < 20:  # Need minimum data for indicators
                continue
            
            # Generate signal
            signals = await self.generate_signals(symbol)
            if not signals:
                continue
            
            signal = signals[0]
            current_price = current_data['close'].iloc[-1]
            
            # Execute trades based on signals
            if signal.signal_type == SignalType.BUY and position is None:
                position = {
                    'entry_price': current_price,
                    'entry_time': current_data.index[-1],
                    'type': 'LONG'
                }
            elif signal.signal_type == SignalType.SELL and position is not None:
                exit_price = current_price
                exit_time = current_data.index[-1]
                
                pnl = (exit_price - position['entry_price']) / position['entry_price']
                
                trades.append({
                    'symbol': symbol,
                    'entry_price': position['entry_price'],
                    'exit_price': exit_price,
                    'entry_time': position['entry_time'],
                    'exit_time': exit_time,
                    'pnl': pnl,
                    'type': position['type']
                })
                
                position = None
        
        return trades
    
    def _calculate_backtest_performance(self, performance: StrategyPerformance, trades: List[Dict[str, Any]]) -> StrategyPerformance:
        """Calculate backtest performance metrics"""
        if not trades:
            return performance
        
        # Calculate basic metrics
        performance.total_trades += len(trades)
        
        pnls = [trade['pnl'] for trade in trades]
        winning_trades = [pnl for pnl in pnls if pnl > 0]
        losing_trades = [pnl for pnl in pnls if pnl < 0]
        
        performance.winning_trades += len(winning_trades)
        performance.losing_trades += len(losing_trades)
        performance.total_return += sum(pnls)
        
        if performance.total_trades > 0:
            performance.win_rate = performance.winning_trades / performance.total_trades
        
        if winning_trades:
            performance.avg_win = sum(winning_trades) / len(winning_trades)
        
        if losing_trades:
            performance.avg_loss = sum(losing_trades) / len(losing_trades)
        
        # Calculate profit factor
        total_wins = sum(winning_trades) if winning_trades else 0
        total_losses = abs(sum(losing_trades)) if losing_trades else 1
        performance.profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Calculate max drawdown (simplified)
        cumulative_returns = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = cumulative_returns - running_max
        performance.max_drawdown = abs(min(drawdowns)) if len(drawdowns) > 0 else 0
        
        # Calculate Sharpe ratio (simplified)
        if len(pnls) > 1:
            returns_std = np.std(pnls)
            if returns_std > 0:
                performance.sharpe_ratio = (np.mean(pnls) / returns_std) * np.sqrt(252)  # Annualized
        
        return performance
    
    async def _update_performance_metrics(self):
        """Update real-time performance metrics"""
        # This would update performance based on actual trade results
        self.performance.last_updated = datetime.now(timezone.utc)

# ===========================================
# CONCRETE STRATEGY IMPLEMENTATIONS
# ===========================================

class MovingAverageCrossoverStrategy(BaseStrategy):
    """Moving Average Crossover Strategy"""
    
    def __init__(self, parameters: StrategyParameters, market_data_service: MarketDataService, db_manager: DatabaseManager):
        super().__init__("MA_Crossover", parameters, market_data_service, db_manager)
        
        # Strategy-specific parameters
        self.fast_period = parameters.custom_params.get('fast_period', 10)
        self.slow_period = parameters.custom_params.get('slow_period', 20)
        self.volume_threshold = parameters.custom_params.get('volume_threshold', 100000)
    
    async def calculate_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate moving averages and volume indicators"""
        indicators = {}
        
        # Calculate moving averages
        indicators['sma_fast'] = self.indicators.sma(data['close'], self.fast_period)
        indicators['sma_slow'] = self.indicators.sma(data['close'], self.slow_period)
        
        # Calculate volume moving average
        indicators['volume_ma'] = self.indicators.sma(data['volume'], 20)
        
        # Calculate RSI for additional confirmation
        indicators['rsi'] = self.indicators.rsi(data['close'])
        
        return indicators
    
    async def generate_signals(self, symbol: str) -> List[TradingSignal]:
        """Generate signals based on moving average crossover"""
        try:
            # Get cached data
            cache_key = f"{symbol}_{self.parameters.timeframe.value}"
            if cache_key not in self.data_cache:
                await self.update_data(symbol, self.parameters.timeframe)
            
            data = self.data_cache[cache_key]
            if len(data) < max(self.fast_period, self.slow_period) + 1:
                return []
            
            # Calculate indicators
            indicators = await self.calculate_indicators(data)
            
            # Get latest values
            current_price = data['close'].iloc[-1]
            current_volume = data['volume'].iloc[-1]
            
            sma_fast_current = indicators['sma_fast'].iloc[-1]
            sma_fast_prev = indicators['sma_fast'].iloc[-2]
            sma_slow_current = indicators['sma_slow'].iloc[-1]
            sma_slow_prev = indicators['sma_slow'].iloc[-2]
            
            rsi_current = indicators['rsi'].iloc[-1]
            volume_ma = indicators['volume_ma'].iloc[-1]
            
            signals = []
            
            # Check for crossover conditions
            # Bullish crossover: fast MA crosses above slow MA
            if (sma_fast_prev <= sma_slow_prev and sma_fast_current > sma_slow_current and 
                current_volume > volume_ma and rsi_current < 70):
                
                signal = TradingSignal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    strength=0.8,
                    price=current_price,
                    timestamp=datetime.now(timezone.utc),
                    strategy_name=self.name,
                    indicators={
                        'sma_fast': sma_fast_current,
                        'sma_slow': sma_slow_current,
                        'rsi': rsi_current,
                        'volume_ratio': current_volume / volume_ma
                    },
                    confidence=0.75,
                    stop_loss=current_price * (1 - self.parameters.stop_loss_pct),
                    take_profit=current_price * (1 + self.parameters.take_profit_pct)
                )
                signals.append(signal)
            
            # Bearish crossover: fast MA crosses below slow MA
            elif (sma_fast_prev >= sma_slow_prev and sma_fast_current < sma_slow_current and 
                  current_volume > volume_ma and rsi_current > 30):
                
                signal = TradingSignal(
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    strength=0.8,
                    price=current_price,
                    timestamp=datetime.now(timezone.utc),
                    strategy_name=self.name,
                    indicators={
                        'sma_fast': sma_fast_current,
                        'sma_slow': sma_slow_current,
                        'rsi': rsi_current,
                        'volume_ratio': current_volume / volume_ma
                    },
                    confidence=0.75,
                    stop_loss=current_price * (1 + self.parameters.stop_loss_pct),
                    take_profit=current_price * (1 - self.parameters.take_profit_pct)
                )
                signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating MA crossover signals for {symbol}: {e}")
            return []

class MomentumStrategy(BaseStrategy):
    """Momentum Strategy based on RSI and MACD"""
    
    def __init__(self, parameters: StrategyParameters, market_data_service: MarketDataService, db_manager: DatabaseManager):
        super().__init__("Momentum", parameters, market_data_service, db_manager)
        
        # Strategy-specific parameters
        self.rsi_period = parameters.custom_params.get('rsi_period', 14)
        self.rsi_oversold = parameters.custom_params.get('rsi_oversold', 30)
        self.rsi_overbought = parameters.custom_params.get('rsi_overbought', 70)
        self.macd_fast = parameters.custom_params.get('macd_fast', 12)
        self.macd_slow = parameters.custom_params.get('macd_slow', 26)
        self.macd_signal = parameters.custom_params.get('macd_signal', 9)
    
    async def calculate_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate momentum indicators"""
        indicators = {}
        
        # Calculate RSI
        indicators['rsi'] = self.indicators.rsi(data['close'], self.rsi_period)
        
        # Calculate MACD
        macd_line, signal_line, histogram = self.indicators.macd(
            data['close'], self.macd_fast, self.macd_slow, self.macd_signal
        )
        indicators['macd'] = macd_line
        indicators['macd_signal'] = signal_line
        indicators['macd_histogram'] = histogram
        
        # Calculate price momentum
        indicators['price_momentum'] = data['close'].pct_change(periods=10)
        
        # Calculate volume momentum
        indicators['volume_momentum'] = data['volume'].pct_change(periods=5)
        
        return indicators
    
    async def generate_signals(self, symbol: str) -> List[TradingSignal]:
        """Generate signals based on momentum indicators"""
        try:
            # Get cached data
            cache_key = f"{symbol}_{self.parameters.timeframe.value}"
            if cache_key not in self.data_cache:
                await self.update_data(symbol, self.parameters.timeframe)
            
            data = self.data_cache[cache_key]
            if len(data) < max(self.rsi_period, self.macd_slow) + 1:
                return []
            
            # Calculate indicators
            indicators = await self.calculate_indicators(data)
            
            # Get latest values
            current_price = data['close'].iloc[-1]
            
            rsi_current = indicators['rsi'].iloc[-1]
            macd_current = indicators['macd'].iloc[-1]
            macd_signal_current = indicators['macd_signal'].iloc[-1]
            macd_histogram_current = indicators['macd_histogram'].iloc[-1]
            macd_histogram_prev = indicators['macd_histogram'].iloc[-2]
            
            price_momentum = indicators['price_momentum'].iloc[-1]
            volume_momentum = indicators['volume_momentum'].iloc[-1]
            
            signals = []
            
            # Bullish momentum conditions
            if (rsi_current > 50 and rsi_current < self.rsi_overbought and
                macd_current > macd_signal_current and
                macd_histogram_current > macd_histogram_prev and
                price_momentum > 0.01 and volume_momentum > 0):
                
                # Determine signal strength based on momentum
                strength = min(0.9, 0.5 + abs(price_momentum) * 10)
                confidence = 0.6 + (rsi_current - 50) / 100
                
                signal = TradingSignal(
                    symbol=symbol,
                    signal_type=SignalType.BUY if strength > 0.7 else SignalType.BUY,
                    strength=strength,
                    price=current_price,
                    timestamp=datetime.now(timezone.utc),
                    strategy_name=self.name,
                    indicators={
                        'rsi': rsi_current,
                        'macd': macd_current,
                        'macd_signal': macd_signal_current,
                        'price_momentum': price_momentum,
                        'volume_momentum': volume_momentum
                    },
                    confidence=confidence,
                    stop_loss=current_price * (1 - self.parameters.stop_loss_pct),
                    take_profit=current_price * (1 + self.parameters.take_profit_pct * 1.5)  # Higher target for momentum
                )
                signals.append(signal)
            
            # Bearish momentum conditions
            elif (rsi_current < 50 and rsi_current > self.rsi_oversold and
                  macd_current < macd_signal_current and
                  macd_histogram_current < macd_histogram_prev and
                  price_momentum < -0.01 and volume_momentum > 0):
                
                # Determine signal strength based on momentum
                strength = min(0.9, 0.5 + abs(price_momentum) * 10)
                confidence = 0.6 + (50 - rsi_current) / 100
                
                signal = TradingSignal(
                    symbol=symbol,
                    signal_type=SignalType.SELL if strength > 0.7 else SignalType.SELL,
                    strength=strength,
                    price=current_price,
                    timestamp=datetime.now(timezone.utc),
                    strategy_name=self.name,
                    indicators={
                        'rsi': rsi_current,
                        'macd': macd_current,
                        'macd_signal': macd_signal_current,
                        'price_momentum': price_momentum,
                        'volume_momentum': volume_momentum
                    },
                    confidence=confidence,
                    stop_loss=current_price * (1 + self.parameters.stop_loss_pct),
                    take_profit=current_price * (1 - self.parameters.take_profit_pct * 1.5)
                )
                signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating momentum signals for {symbol}: {e}")
            return []

# ===========================================
# STRATEGY MANAGER
# ===========================================

class StrategyManager:
    """Manages multiple trading strategies"""
    
    def __init__(self, market_data_service: MarketDataService, db_manager: DatabaseManager):
        self.market_data_service = market_data_service
        self.db_manager = db_manager
        self.strategies: Dict[str, BaseStrategy] = {}
        self.active_strategies: List[str] = []
        
    async def initialize(self):
        """Initialize strategy manager"""
        await self._load_strategies_from_db()
        logger.info("Strategy Manager initialized successfully")
    
    async def add_strategy(self, strategy: BaseStrategy) -> bool:
        """Add a new strategy"""
        try:
            await strategy.initialize()
            self.strategies[strategy.name] = strategy
            
            if strategy.status == StrategyStatus.ACTIVE:
                self.active_strategies.append(strategy.name)
            
            logger.info(f"Strategy {strategy.name} added successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error adding strategy {strategy.name}: {e}")
            return False
    
    async def remove_strategy(self, strategy_name: str) -> bool:
        """Remove a strategy"""
        try:
            if strategy_name in self.strategies:
                strategy = self.strategies[strategy_name]
                strategy.stop()
                
                del self.strategies[strategy_name]
                if strategy_name in self.active_strategies:
                    self.active_strategies.remove(strategy_name)
                
                logger.info(f"Strategy {strategy_name} removed successfully")
                return True
            else:
                logger.warning(f"Strategy {strategy_name} not found")
                return False
                
        except Exception as e:
            logger.error(f"Error removing strategy {strategy_name}: {e}")
            return False
    
    async def run_all_strategies(self, symbols: List[str]) -> Dict[str, List[TradingSignal]]:
        """Run all active strategies"""
        all_signals = {}
        
        for strategy_name in self.active_strategies:
            try:
                strategy = self.strategies[strategy_name]
                if strategy.status == StrategyStatus.ACTIVE:
                    signals = await strategy.run_strategy(symbols)
                    all_signals[strategy_name] = signals
                    
            except Exception as e:
                logger.error(f"Error running strategy {strategy_name}: {e}")
                all_signals[strategy_name] = []
        
        return all_signals
    
    async def get_strategy_performance(self, strategy_name: str) -> Optional[StrategyPerformance]:
        """Get performance metrics for a strategy"""
        if strategy_name in self.strategies:
            return self.strategies[strategy_name].get_current_performance()
        return None
    
    async def pause_strategy(self, strategy_name: str) -> bool:
        """Pause a strategy"""
        if strategy_name in self.strategies:
            self.strategies[strategy_name].pause()
            if strategy_name in self.active_strategies:
                self.active_strategies.remove(strategy_name)
            return True
        return False
    
    async def resume_strategy(self, strategy_name: str) -> bool:
        """Resume a strategy"""
        if strategy_name in self.strategies:
            self.strategies[strategy_name].resume()
            if strategy_name not in self.active_strategies:
                self.active_strategies.append(strategy_name)
            return True
        return False
    
    def get_all_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all strategies"""
        strategy_info = {}
        
        for name, strategy in self.strategies.items():
            strategy_info[name] = {
                'name': strategy.name,
                'status': strategy.status.value,
                'parameters': {
                    'symbol': strategy.parameters.symbol,
                    'timeframe': strategy.parameters.timeframe.value,
                    'risk_per_trade': strategy.parameters.risk_per_trade,
                    'stop_loss_pct': strategy.parameters.stop_loss_pct,
                    'take_profit_pct': strategy.parameters.take_profit_pct
                },
                'performance': {
                    'total_trades': strategy.performance.total_trades,
                    'win_rate': strategy.performance.win_rate,
                    'total_return': strategy.performance.total_return,
                    'sharpe_ratio': strategy.performance.sharpe_ratio
                },
                'last_updated': strategy.performance.last_updated.isoformat()
            }
        
        return strategy_info
    
    # ===========================================
    # PRIVATE HELPER METHODS
    # ===========================================
    
    async def _load_strategies_from_db(self):
        """Load strategies from database"""
        # This would load strategy configurations from database
        # For now, create some default strategies
        
        # Create default MA Crossover strategy
        ma_params = StrategyParameters(
            symbol="AAPL",
            timeframe=TimeFrame.HOUR_1,
            custom_params={'fast_period': 10, 'slow_period': 20}
        )
        ma_strategy = MovingAverageCrossoverStrategy(ma_params, self.market_data_service, self.db_manager)
        await self.add_strategy(ma_strategy)
        
        # Create default Momentum strategy
        momentum_params = StrategyParameters(
            symbol="TSLA",
            timeframe=TimeFrame.HOUR_1,
            custom_params={'rsi_period': 14, 'rsi_oversold': 30, 'rsi_overbought': 70}
        )
        momentum_strategy = MomentumStrategy(momentum_params, self.market_data_service, self.db_manager)
        await self.add_strategy(momentum_strategy)

# ===========================================
# FACTORY FUNCTIONS
# ===========================================

async def create_strategy_manager(market_data_service: MarketDataService, db_manager: DatabaseManager) -> StrategyManager:
    """Factory function to create StrategyManager instance"""
    strategy_manager = StrategyManager(market_data_service, db_manager)
    await strategy_manager.initialize()
    return strategy_manager

async def create_ma_crossover_strategy(
    symbol: str, 
    timeframe: TimeFrame, 
    fast_period: int = 10, 
    slow_period: int = 20,
    market_data_service: MarketDataService = None,
    db_manager: DatabaseManager = None
) -> MovingAverageCrossoverStrategy:
    """Factory function to create MA Crossover strategy"""
    parameters = StrategyParameters(
        symbol=symbol,
        timeframe=timeframe,
        custom_params={
            'fast_period': fast_period,
            'slow_period': slow_period
        }
    )
    
    strategy = MovingAverageCrossoverStrategy(parameters, market_data_service, db_manager)
    await strategy.initialize()
    return strategy

async def create_momentum_strategy(
    symbol: str, 
    timeframe: TimeFrame, 
    rsi_period: int = 14,
    market_data_service: MarketDataService = None,
    db_manager: DatabaseManager = None
) -> MomentumStrategy:
    """Factory function to create Momentum strategy"""
    parameters = StrategyParameters(
        symbol=symbol,
        timeframe=timeframe,
        custom_params={
            'rsi_period': rsi_period,
            'rsi_oversold': 30,
            'rsi_overbought': 70
        }
    )
    
    strategy = MomentumStrategy(parameters, market_data_service, db_manager)
    await strategy.initialize()
    return strategy