"""RSI(2) Strategy

A classic mean reversion strategy using the 2-period RSI indicator.
This strategy buys when RSI(2) is oversold and sells when overbought.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass
import logging

# Technical analysis
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False

from ..base_strategy import BaseStrategy, StrategyConfig, Signal, SignalType
from ..backtesting.results import Trade, TradeType

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RSI2Config(StrategyConfig):
    """Configuration for RSI(2) strategy"""
    rsi_period: int = 2
    sma_period: int = 200
    oversold_threshold: float = 10.0
    overbought_threshold: float = 90.0
    position_size: float = 0.1  # 10% of portfolio per position
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.oversold_threshold >= self.overbought_threshold:
            raise ValueError("Oversold threshold must be less than overbought threshold")


class RSI2Strategy(BaseStrategy):
    """RSI(2) Mean Reversion Strategy
    
    This strategy implements the classic RSI(2) mean reversion approach:
    1. Calculate 2-period RSI
    2. Calculate 200-period SMA for trend filter
    3. Buy when RSI(2) < oversold_threshold and price > SMA(200)
    4. Sell when RSI(2) > overbought_threshold and price < SMA(200)
    5. Exit positions when RSI(2) crosses back above/below middle levels
    """
    
    def __init__(self, config: RSI2Config):
        super().__init__(config)
        self.config = config
        self.rsi_values = []
        self.sma_values = []
        self.price_history = []
        
        # Strategy state
        self.current_position = 0.0
        self.entry_price = None
        self.entry_time = None
        
        logger.info(f"Initialized RSI(2) strategy with config: {config}")
    
    def calculate_rsi(self, prices: pd.Series, period: int = 2) -> pd.Series:
        """Calculate RSI indicator
        
        Args:
            prices: Price series
            period: RSI period
        
        Returns:
            RSI values
        """
        if TALIB_AVAILABLE:
            return pd.Series(talib.RSI(prices.values, timeperiod=period), index=prices.index)
        else:
            # Manual RSI calculation
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
    
    def calculate_sma(self, prices: pd.Series, period: int = 200) -> pd.Series:
        """Calculate Simple Moving Average
        
        Args:
            prices: Price series
            period: SMA period
        
        Returns:
            SMA values
        """
        if TALIB_AVAILABLE:
            return pd.Series(talib.SMA(prices.values, timeperiod=period), index=prices.index)
        else:
            return prices.rolling(window=period).mean()
    
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """Generate trading signals based on RSI(2) strategy
        
        Args:
            data: OHLCV data with columns ['open', 'high', 'low', 'close', 'volume']
        
        Returns:
            List of trading signals
        """
        if len(data) < max(self.config.rsi_period, self.config.sma_period):
            return []
        
        signals = []
        
        # Calculate indicators
        close_prices = data['close']
        rsi = self.calculate_rsi(close_prices, self.config.rsi_period)
        sma = self.calculate_sma(close_prices, self.config.sma_period)
        
        # Store for analysis
        self.rsi_values = rsi.tolist()
        self.sma_values = sma.tolist()
        self.price_history = close_prices.tolist()
        
        for i in range(len(data)):
            if pd.isna(rsi.iloc[i]) or pd.isna(sma.iloc[i]):
                continue
            
            timestamp = data.index[i]
            current_price = close_prices.iloc[i]
            current_rsi = rsi.iloc[i]
            current_sma = sma.iloc[i]
            
            # Generate signals
            signal = self._evaluate_signal(
                timestamp, current_price, current_rsi, current_sma
            )
            
            if signal:
                signals.append(signal)
        
        return signals
    
    def _evaluate_signal(self, timestamp: datetime, price: float, 
                        rsi: float, sma: float) -> Optional[Signal]:
        """Evaluate trading signal for current market conditions
        
        Args:
            timestamp: Current timestamp
            price: Current price
            rsi: Current RSI value
            sma: Current SMA value
        
        Returns:
            Trading signal if conditions are met
        """
        # Long entry conditions
        if (self.current_position == 0 and 
            rsi < self.config.oversold_threshold and 
            price > sma):
            
            self.current_position = self.config.position_size
            self.entry_price = price
            self.entry_time = timestamp
            
            return Signal(
                timestamp=timestamp,
                signal_type=SignalType.BUY,
                symbol=self.config.symbol,
                strength=1.0 - (rsi / 100.0),  # Stronger signal for lower RSI
                price=price,
                quantity=self.config.position_size,
                metadata={
                    'rsi': rsi,
                    'sma': sma,
                    'strategy': 'RSI2_long_entry'
                }
            )
        
        # Short entry conditions
        elif (self.current_position == 0 and 
              rsi > self.config.overbought_threshold and 
              price < sma):
            
            self.current_position = -self.config.position_size
            self.entry_price = price
            self.entry_time = timestamp
            
            return Signal(
                timestamp=timestamp,
                signal_type=SignalType.SELL,
                symbol=self.config.symbol,
                strength=rsi / 100.0,  # Stronger signal for higher RSI
                price=price,
                quantity=self.config.position_size,
                metadata={
                    'rsi': rsi,
                    'sma': sma,
                    'strategy': 'RSI2_short_entry'
                }
            )
        
        # Long exit conditions
        elif (self.current_position > 0 and 
              (rsi > 50.0 or self._check_stop_conditions(price))):
            
            position_size = self.current_position
            self.current_position = 0.0
            
            return Signal(
                timestamp=timestamp,
                signal_type=SignalType.SELL,
                symbol=self.config.symbol,
                strength=0.8,
                price=price,
                quantity=position_size,
                metadata={
                    'rsi': rsi,
                    'sma': sma,
                    'strategy': 'RSI2_long_exit',
                    'entry_price': self.entry_price,
                    'pnl': (price - self.entry_price) * position_size if self.entry_price else 0
                }
            )
        
        # Short exit conditions
        elif (self.current_position < 0 and 
              (rsi < 50.0 or self._check_stop_conditions(price))):
            
            position_size = abs(self.current_position)
            self.current_position = 0.0
            
            return Signal(
                timestamp=timestamp,
                signal_type=SignalType.BUY,
                symbol=self.config.symbol,
                strength=0.8,
                price=price,
                quantity=position_size,
                metadata={
                    'rsi': rsi,
                    'sma': sma,
                    'strategy': 'RSI2_short_exit',
                    'entry_price': self.entry_price,
                    'pnl': (self.entry_price - price) * position_size if self.entry_price else 0
                }
            )
        
        return None
    
    def _check_stop_conditions(self, current_price: float) -> bool:
        """Check stop loss and take profit conditions
        
        Args:
            current_price: Current market price
        
        Returns:
            True if stop conditions are met
        """
        if not self.entry_price:
            return False
        
        # Calculate P&L percentage
        if self.current_position > 0:  # Long position
            pnl_pct = (current_price - self.entry_price) / self.entry_price
        else:  # Short position
            pnl_pct = (self.entry_price - current_price) / self.entry_price
        
        # Check stop loss
        if self.config.stop_loss and pnl_pct <= -abs(self.config.stop_loss):
            return True
        
        # Check take profit
        if self.config.take_profit and pnl_pct >= self.config.take_profit:
            return True
        
        return False
    
    def update_state(self, market_data: Dict[str, Any]) -> None:
        """Update strategy state with new market data
        
        Args:
            market_data: Current market data
        """
        # Update internal state if needed
        pass
    
    def get_current_signals(self) -> List[Signal]:
        """Get current active signals
        
        Returns:
            List of current signals
        """
        return []  # RSI2 strategy generates signals on-demand
    
    def get_strategy_state(self) -> Dict[str, Any]:
        """Get current strategy state
        
        Returns:
            Dictionary containing strategy state
        """
        return {
            'current_position': self.current_position,
            'entry_price': self.entry_price,
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'rsi_values': self.rsi_values[-10:] if self.rsi_values else [],
            'sma_values': self.sma_values[-10:] if self.sma_values else [],
            'price_history': self.price_history[-10:] if self.price_history else []
        }
    
    def reset(self) -> None:
        """Reset strategy state"""
        self.current_position = 0.0
        self.entry_price = None
        self.entry_time = None
        self.rsi_values.clear()
        self.sma_values.clear()
        self.price_history.clear()
        logger.info("RSI(2) strategy state reset")


# Factory function
def create_rsi2_strategy(symbol: str = "AAPL", **kwargs) -> RSI2Strategy:
    """Create RSI(2) strategy instance
    
    Args:
        symbol: Trading symbol
        **kwargs: Additional configuration parameters
    
    Returns:
        RSI2Strategy instance
    """
    config = RSI2Config(symbol=symbol, **kwargs)
    return RSI2Strategy(config)


# Example usage
if __name__ == "__main__":
    # Create strategy
    strategy = create_rsi2_strategy(
        symbol="AAPL",
        rsi_period=2,
        sma_period=200,
        oversold_threshold=10.0,
        overbought_threshold=90.0,
        position_size=0.1
    )
    
    # Generate sample data
    dates = pd.date_range('2023-01-01', periods=300, freq='D')
    np.random.seed(42)
    
    # Simulate price data
    returns = np.random.normal(0.001, 0.02, 300)
    prices = 100 * np.exp(np.cumsum(returns))
    
    data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.001, 300)),
        'high': prices * (1 + np.abs(np.random.normal(0, 0.01, 300))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.01, 300))),
        'close': prices,
        'volume': np.random.randint(1000000, 5000000, 300)
    }, index=dates)
    
    # Generate signals
    signals = strategy.generate_signals(data)
    
    print(f"Generated {len(signals)} signals")
    for signal in signals[:5]:  # Show first 5 signals
        print(f"{signal.timestamp}: {signal.signal_type.value} {signal.symbol} @ {signal.price:.2f}")
    
    # Show strategy state
    state = strategy.get_strategy_state()
    print(f"\nStrategy state: {state}")