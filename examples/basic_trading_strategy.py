#!/usr/bin/env python3
"""
Basic Trading Strategy Example for Nautilus Trader Engine.

This example demonstrates how to create and run a simple momentum-based
trading strategy using the institutional-grade trading system.

Features demonstrated:
- Strategy implementation using the modular strategy framework
- Indicator integration with adaptive parameters
- Risk management integration
- Order execution through the broker abstraction
- Performance tracking and reporting

Usage:
    python examples/basic_trading_strategy.py
"""

import asyncio
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, '..')

from nautilus_trader_engine.core.dependency_injection import get_container
from nautilus_trader_engine.core.event_system import get_event_bus, EventType
from nautilus_trader_engine.core.adaptive_parameters import (
    get_adaptive_manager, ParameterBounds, ParameterType,
    AdaptationStrategy, create_adaptive_parameter
)
from nautilus_trader_engine.strategies.modular_strategy_components import (
    BaseTradingStrategy, StrategySignal, StrategyState
)
from nautilus_trader_engine.analysis.indicators.technical_indicators import (
    RSI, MACD, BollingerBands
)
from nautilus_trader_engine.brokers.broker_abstraction import OrderSide, OrderType
from nautilus_trader_engine.core.interfaces import SignalStrength


class MomentumTradingStrategy(BaseTradingStrategy):
    """
    Momentum-based trading strategy using RSI and MACD indicators.

    This strategy demonstrates:
    - Multi-indicator signal combination
    - Adaptive parameter management
    - Risk-adjusted position sizing
    - Stop-loss and take-profit management
    """

    def __init__(self, symbol: str = "AAPL", initial_balance: float = 100000.0):
        super().__init__(
            name="MomentumStrategy",
            symbol=symbol,
            initial_balance=initial_balance
        )

        # Initialize indicators
        self.rsi = None
        self.macd = None
        self.bollinger = None

        # Strategy parameters
        self.rsi_overbought = 70
        self.rsi_oversold = 30
        self.macd_signal_threshold = 0.0
        self.stop_loss_pct = 0.02
        self.take_profit_pct = 0.05
        self.position_size_pct = 0.1  # 10% of portfolio per trade

        # State tracking
        self.last_signal = None
        self.entry_price = 0.0
        self.stop_loss_price = 0.0
        self.take_profit_price = 0.0

    async def initialize(self):
        """Initialize strategy components."""
        print(f"Initializing {self.name} for {self.symbol}")

        # Get dependency injection container
        container = get_container()

        # Initialize indicators with adaptive parameters
        adaptive_manager = get_adaptive_manager()

        # Register adaptive parameters for RSI
        rsi_bounds = ParameterBounds(min_value=5, max_value=50)
        rsi_param = create_adaptive_parameter(
            name="rsi_period",
            parameter_type=ParameterType.PERIOD,
            base_value=14,
            bounds=rsi_bounds,
            adaptation_strategy=AdaptationStrategy.VOLATILITY_BASED
        )
        adaptive_manager.register_indicator_parameters("rsi", {"period": rsi_param})

        # Register adaptive parameters for MACD
        macd_bounds = ParameterBounds(min_value=5, max_value=50)
        macd_fast_param = create_adaptive_parameter(
            name="macd_fast",
            parameter_type=ParameterType.PERIOD,
            base_value=12,
            bounds=macd_bounds,
            adaptation_strategy=AdaptationStrategy.VOLATILITY_BASED
        )
        macd_slow_param = create_adaptive_parameter(
            name="macd_slow",
            parameter_type=ParameterType.PERIOD,
            base_value=26,
            bounds=macd_bounds,
            adaptation_strategy=AdaptationStrategy.VOLATILITY_BASED
        )
        adaptive_manager.register_indicator_parameters("macd", {
            "fast_period": macd_fast_param,
            "slow_period": macd_slow_param
        })

        # Create indicators
        self.rsi = RSI(period=14, enable_volume_weighting=True)
        self.macd = MACD(fast_period=12, slow_period=26, signal_period=9)
        self.bollinger = BollingerBands(period=20, std_dev=2.0)

        # Subscribe to market data events
        event_bus = get_event_bus()
        await event_bus.subscribe(EventType.MARKET_DATA, self.on_market_data)

        print(f"✓ Strategy initialized with indicators: RSI, MACD, Bollinger Bands")

    async def on_market_data(self, event):
        """Handle incoming market data."""
        if event.symbol != self.symbol:
            return

        # Extract OHLCV data
        data = {
            'open': event.data.get('open', 0),
            'high': event.data.get('high', 0),
            'low': event.data.get('low', 0),
            'close': event.data.get('close', 0),
            'volume': event.data.get('volume', 0),
            'timestamp': event.timestamp
        }

        # Update indicators
        await self.update_indicators(data)

        # Generate trading signals
        signal = await self.generate_signal(data)

        # Execute trades based on signals
        if signal:
            await self.execute_trade(signal, data)

    async def update_indicators(self, data: Dict):
        """Update all technical indicators."""
        try:
            # Update RSI
            rsi_result = self.rsi.update(
                price=data['close'],
                volume=data['volume'],
                timestamp=data['timestamp']
            )

            # Update MACD
            macd_result = self.macd.update(
                price=data['close'],
                volume=data['volume'],
                timestamp=data['timestamp']
            )

            # Update Bollinger Bands
            bb_result = self.bollinger.update(
                price=data['close'],
                volume=data['volume'],
                timestamp=data['timestamp']
            )

        except Exception as e:
            print(f"Error updating indicators: {e}")

    async def generate_signal(self, data: Dict) -> Optional[StrategySignal]:
        """Generate trading signals based on indicator analysis."""
        try:
            # Get current indicator values
            rsi_value = getattr(self.rsi, 'rsi', 50)
            macd_histogram = getattr(self.macd, 'histogram', 0)
            bb_upper = getattr(self.bollinger, 'upper_band', data['close'] * 1.1)
            bb_lower = getattr(self.bollinger, 'lower_band', data['close'] * 0.9)

            current_price = data['close']

            # Momentum strategy logic
            signal = None
            strength = SignalStrength.MODERATE
            confidence = 0.6

            # Bullish signals
            if (rsi_value < self.rsi_oversold and
                macd_histogram > self.macd_signal_threshold and
                current_price <= bb_lower):
                signal = "BUY"
                strength = SignalStrength.STRONG
                confidence = 0.8

            # Bearish signals
            elif (rsi_value > self.rsi_overbought and
                  macd_histogram < -self.macd_signal_threshold and
                  current_price >= bb_upper):
                signal = "SELL"
                strength = SignalStrength.STRONG
                confidence = 0.8

            # Exit signals (if in position)
            elif self.last_signal == "BUY":
                if (current_price >= self.take_profit_price or
                    current_price <= self.stop_loss_price):
                    signal = "EXIT_LONG"
                    strength = SignalStrength.STRONG
                    confidence = 0.9

            elif self.last_signal == "SELL":
                if (current_price <= self.take_profit_price or
                    current_price >= self.stop_loss_price):
                    signal = "EXIT_SHORT"
                    strength = SignalStrength.STRONG
                    confidence = 0.9

            if signal:
                return StrategySignal(
                    signal_type=signal,
                    strength=strength,
                    confidence=confidence,
                    price=current_price,
                    timestamp=data['timestamp'],
                    metadata={
                        'rsi': rsi_value,
                        'macd_histogram': macd_histogram,
                        'bb_upper': bb_upper,
                        'bb_lower': bb_lower
                    }
                )

        except Exception as e:
            print(f"Error generating signal: {e}")

        return None

    async def execute_trade(self, signal: StrategySignal, data: Dict):
        """Execute trade based on signal."""
        try:
            current_price = data['close']

            if signal.signal_type == "BUY":
                # Calculate position size
                position_value = self.current_balance * self.position_size_pct
                quantity = int(position_value / current_price)

                if quantity > 0:
                    # Place buy order
                    order = await self.place_order(
                        symbol=self.symbol,
                        side=OrderSide.BUY,
                        quantity=quantity,
                        order_type=OrderType.MARKET,
                        price=current_price
                    )

                    if order:
                        self.last_signal = "BUY"
                        self.entry_price = current_price
                        self.stop_loss_price = current_price * (1 - self.stop_loss_pct)
                        self.take_profit_price = current_price * (1 + self.take_profit_pct)

                        print(f"✓ BUY {quantity} {self.symbol} @ ${current_price:.2f}")
                        print(f"  Stop Loss: ${self.stop_loss_price:.2f}")
                        print(f"  Take Profit: ${self.take_profit_price:.2f}")

            elif signal.signal_type == "SELL":
                # Calculate position size
                position_value = self.current_balance * self.position_size_pct
                quantity = int(position_value / current_price)

                if quantity > 0:
                    # Place sell order (short)
                    order = await self.place_order(
                        symbol=self.symbol,
                        side=OrderSide.SELL,
                        quantity=quantity,
                        order_type=OrderType.MARKET,
                        price=current_price
                    )

                    if order:
                        self.last_signal = "SELL"
                        self.entry_price = current_price
                        self.stop_loss_price = current_price * (1 + self.stop_loss_pct)
                        self.take_profit_price = current_price * (1 - self.take_profit_pct)

                        print(f"✓ SELL {quantity} {self.symbol} @ ${current_price:.2f}")
                        print(f"  Stop Loss: ${self.stop_loss_price:.2f}")
                        print(f"  Take Profit: ${self.take_profit_price:.2f}")

            elif signal.signal_type in ["EXIT_LONG", "EXIT_SHORT"]:
                # Close position
                # In a real implementation, this would close existing positions
                self.last_signal = None
                self.entry_price = 0.0
                self.stop_loss_price = 0.0
                self.take_profit_price = 0.0

                print(f"✓ EXIT position in {self.symbol}")

        except Exception as e:
            print(f"Error executing trade: {e}")

    async def get_strategy_status(self) -> Dict:
        """Get current strategy status."""
        return {
            'name': self.name,
            'symbol': self.symbol,
            'balance': self.current_balance,
            'last_signal': self.last_signal,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss_price,
            'take_profit': self.take_profit_price,
            'indicators': {
                'rsi': getattr(self.rsi, 'rsi', None),
                'macd_histogram': getattr(self.macd, 'histogram', None),
                'bb_upper': getattr(self.bollinger, 'upper_band', None),
                'bb_lower': getattr(self.bollinger, 'lower_band', None)
            }
        }


async def simulate_market_data(strategy: MomentumTradingStrategy, symbol: str, days: int = 30):
    """Simulate market data for testing the strategy."""
    print(f"Simulating {days} days of market data for {symbol}...")

    # Generate synthetic OHLCV data
    import numpy as np
    import pandas as pd

    # Create date range
    dates = pd.date_range(start=datetime.now() - timedelta(days=days), periods=days*24, freq='H')

    # Generate synthetic price data with trend and volatility
    np.random.seed(42)  # For reproducible results

    # Base price and trend
    base_price = 150.0
    trend = 0.001  # Slight upward trend
    volatility = 0.02

    prices = []
    current_price = base_price

    for i in range(len(dates)):
        # Random walk with trend
        price_change = np.random.normal(trend, volatility)
        current_price *= (1 + price_change)
        prices.append(current_price)

    # Generate OHLCV from close prices
    event_bus = get_event_bus()

    for i, (date, close_price) in enumerate(zip(dates, prices)):
        # Generate OHLC around close price
        volatility_factor = np.random.uniform(0.01, 0.03)
        high = close_price * (1 + volatility_factor)
        low = close_price * (1 - volatility_factor)
        open_price = close_price * (1 + np.random.normal(0, volatility_factor/2))
        volume = int(np.random.normal(1000000, 200000))

        # Create market data event
        from nautilus_trader_engine.core.event_system import Event
        event = Event(
            event_type=EventType.MARKET_DATA,
            data={
                'symbol': symbol,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close_price,
                'volume': volume,
                'timestamp': date.timestamp()
            }
        )

        # Publish event
        await event_bus.publish_event(event)

        # Small delay to simulate real-time data
        await asyncio.sleep(0.001)

        # Print progress
        if (i + 1) % 100 == 0:
            print(f"Processed {i + 1}/{len(dates)} data points...")

    print(f"✓ Simulation completed: {len(dates)} data points")


async def main():
    """Main execution function."""
    print("🚀 Nautilus Trader Engine - Basic Trading Strategy Example")
    print("=" * 60)

    # Create and initialize strategy
    strategy = MomentumTradingStrategy(symbol="AAPL", initial_balance=100000.0)

    try:
        # Initialize strategy
        await strategy.initialize()

        # Get initial status
        status = await strategy.get_strategy_status()
        print(f"📊 Initial Strategy Status:")
        print(f"  Symbol: {status['symbol']}")
        print(f"  Balance: ${status['balance']:,.2f}")
        print()

        # Simulate market data
        await simulate_market_data(strategy, "AAPL", days=7)  # 1 week of hourly data

        # Get final status
        final_status = await strategy.get_strategy_status()
        print(f"📊 Final Strategy Status:")
        print(f"  Balance: ${final_status['balance']:,.2f}")
        print(f"  Last Signal: {final_status['last_signal']}")
        if final_status['entry_price'] > 0:
            print(f"  Entry Price: ${final_status['entry_price']:.2f}")
            print(f"  Stop Loss: ${final_status['stop_loss']:.2f}")
            print(f"  Take Profit: ${final_status['take_profit']:.2f}")

        print()
        print("✅ Strategy execution completed successfully!")

    except Exception as e:
        print(f"❌ Error running strategy: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        await strategy.cleanup()


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())