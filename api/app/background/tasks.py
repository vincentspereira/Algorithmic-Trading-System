
import asyncio
from datetime import datetime

import structlog

from api.app.websockets import ConnectionManager
from nautilus_trader_engine.core.data_feed_manager import DataFeedManager
from nautilus_trader_engine.indicators.comprehensive_indicators import ComprehensiveIndicators

logger = structlog.get_logger()

async def market_data_streamer(connection_manager: ConnectionManager, data_feed_manager: DataFeedManager):
    """Background task to stream real-time market data"""
    while True:
        try:
            # Get active symbol subscriptions
            active_symbols = list(connection_manager.symbol_subscriptions.keys())

            if active_symbols:
                # Fetch real-time data for subscribed symbols
                for symbol in active_symbols:
                    try:
                        quote = await data_feed_manager.get_real_time_quote(symbol)
                        if quote:
                            await connection_manager.broadcast_to_symbol(symbol, {
                                "type": "market_data",
                                "symbol": symbol,
                                "data": quote,
                                "timestamp": datetime.now().isoformat()
                            })
                    except Exception as e:
                        logger.error("Failed to stream data", symbol=symbol, error=str(e))

            await asyncio.sleep(1)  # Update frequency: 1 second

        except Exception as e:
            logger.error("Market data streamer error", error=str(e))
            await asyncio.sleep(5)  # Error recovery delay

async def indicator_calculator(connection_manager: ConnectionManager, data_feed_manager: DataFeedManager, indicators_engine: ComprehensiveIndicators):
    """Background task to calculate indicators for subscribed symbols"""
    while True:
        try:
            active_symbols = list(connection_manager.symbol_subscriptions.keys())

            if active_symbols:
                for symbol in active_symbols:
                    try:
                        # Calculate key indicators
                        market_data = await data_feed_manager.get_historical_data(
                            symbol=symbol, period="1d", interval="1m"
                        )

                        if not market_data.empty:
                            # Quick indicator calculation
                            data_dict = {
                                'open': market_data['Open'],
                                'high': market_data['High'],
                                'low': market_data['Low'],
                                'close': market_data['Close'],
                                'volume': market_data['Volume']
                            }

                            # Calculate a subset of key indicators
                            rsi_result = indicators_engine.traditional_indicators.rsi(data_dict['close'], 14)
                            macd_result = indicators_engine.traditional_indicators.macd(data_dict['close'], 12, 26, 9)

                            indicator_update = {
                                "type": "indicators",
                                "symbol": symbol,
                                "data": {
                                    "rsi": {
                                        "value": float(rsi_result.value.iloc[-1]) if hasattr(rsi_result.value, 'iloc') else rsi_result.value,
                                        "signal": rsi_result.signal,
                                        "strength": rsi_result.strength
                                    },
                                    "macd": {
                                        "signal": macd_result.signal,
                                        "strength": macd_result.strength
                                    }
                                },
                                "timestamp": datetime.now().isoformat()
                            }

                            await connection_manager.broadcast_to_symbol(symbol, indicator_update)

                    except Exception as e:
                        logger.error("Failed to calculate indicators", symbol=symbol, error=str(e))

            await asyncio.sleep(30)  # Update frequency: 30 seconds

        except Exception as e:
            logger.error("Indicator calculator error", error=str(e))
            await asyncio.sleep(60)  # Error recovery delay
