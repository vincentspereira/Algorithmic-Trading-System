"""
Streaming Architecture for Nautilus Trader Engine
Provides real-time data processing and streaming analytics capabilities.
"""

import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Callable, Tuple, Union, Type, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from collections import deque
import time
import json
from concurrent.futures import ThreadPoolExecutor
import websockets
import aiohttp
from queue import Queue, Empty
import threading

logger = logging.getLogger(__name__)


class StreamType(Enum):
    """Types of data streams."""
    MARKET_DATA = "market_data"
    ORDER_BOOK = "order_book"
    TRADES = "trades"
    NEWS = "news"
    SOCIAL_MEDIA = "social_media"
    FUNDAMENTAL_DATA = "fundamental_data"
    TECHNICAL_INDICATORS = "technical_indicators"
    STRATEGY_SIGNALS = "strategy_signals"


class ProcessingMode(Enum):
    """Stream processing modes."""
    REAL_TIME = "real_time"
    MICRO_BATCH = "micro_batch"
    BATCH = "batch"
    WINDOWED = "windowed"


class WindowType(Enum):
    """Types of time windows."""
    TUMBLING = "tumbling"
    SLIDING = "sliding"
    SESSION = "session"
    CUSTOM = "custom"


@dataclass
class StreamMessage:
    """A message in the streaming pipeline."""
    stream_type: StreamType
    symbol: str
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    sequence_number: int = 0
    source: str = "unknown"


@dataclass
class StreamWindow:
    """A time window for stream processing."""
    window_type: WindowType
    window_size: timedelta
    slide_interval: Optional[timedelta] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    data: List[StreamMessage] = field(default_factory=list)


@dataclass
class StreamMetrics:
    """Metrics for stream processing."""
    messages_processed: int = 0
    processing_latency: float = 0.0
    throughput: float = 0.0
    error_count: int = 0
    last_update: datetime = field(default_factory=datetime.now)


class StreamProcessor(ABC):
    """Abstract base class for stream processors."""

    @abstractmethod
    async def process(self, message: StreamMessage) -> Optional[StreamMessage]:
        """Process a stream message."""
        pass

    @abstractmethod
    def get_metrics(self) -> StreamMetrics:
        """Get processing metrics."""
        pass


class MarketDataProcessor(StreamProcessor):
    """Processor for market data streams."""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.price_history: deque = deque(maxlen=1000)
        self.volume_history: deque = deque(maxlen=1000)
        self.metrics = StreamMetrics()

    async def process(self, message: StreamMessage) -> Optional[StreamMessage]:
        """Process market data message."""
        try:
            start_time = time.time()

            if message.stream_type == StreamType.MARKET_DATA:
                # Extract price and volume data
                price = message.data.get('close', message.data.get('price'))
                volume = message.data.get('volume', 0)

                if price is not None:
                    self.price_history.append((message.timestamp, price))
                    self.volume_history.append((message.timestamp, volume))

                    # Calculate basic metrics
                    if len(self.price_history) >= 2:
                        current_price = self.price_history[-1][1]
                        previous_price = self.price_history[-2][1]
                        price_change = (current_price - previous_price) / previous_price

                        # Create processed message
                        processed_data = {
                            'price': current_price,
                            'volume': volume,
                            'price_change': price_change,
                            'price_history_length': len(self.price_history),
                            'vwap': self._calculate_vwap()
                        }

                        processed_message = StreamMessage(
                            stream_type=StreamType.TECHNICAL_INDICATORS,
                            symbol=message.symbol,
                            timestamp=message.timestamp,
                            data=processed_data,
                            metadata={'processor': 'market_data', 'original_sequence': message.sequence_number}
                        )

                        processing_time = time.time() - start_time
                        self.metrics.processing_latency = processing_time
                        self.metrics.messages_processed += 1

                        return processed_message

            return None

        except Exception as e:
            logger.error(f"Error processing market data: {e}")
            self.metrics.error_count += 1
            return None

    def _calculate_vwap(self) -> float:
        """Calculate Volume Weighted Average Price."""
        if not self.price_history or not self.volume_history:
            return 0.0

        total_volume = sum(volume for _, volume in self.volume_history)
        if total_volume == 0:
            return 0.0

        weighted_sum = sum(price * volume for (timestamp, price), (_, volume) in zip(self.price_history, self.volume_history))
        return weighted_sum / total_volume

    def get_metrics(self) -> StreamMetrics:
        return self.metrics


class TechnicalIndicatorProcessor(StreamProcessor):
    """Processor for technical indicators."""

    def __init__(self, indicators: List[str] = None):
        self.indicators = indicators or ['SMA', 'RSI', 'MACD']
        self.price_data: deque = deque(maxlen=200)
        self.metrics = StreamMetrics()

    async def process(self, message: StreamMessage) -> Optional[StreamMessage]:
        """Process message and calculate technical indicators."""
        try:
            start_time = time.time()

            if message.stream_type == StreamType.MARKET_DATA:
                price = message.data.get('close', message.data.get('price'))
                if price is not None:
                    self.price_data.append(price)

                    if len(self.price_data) >= 20:  # Minimum data for calculations
                        indicators_data = {}

                        # Calculate SMA
                        if 'SMA' in self.indicators:
                            sma_20 = np.mean(list(self.price_data)[-20:])
                            sma_50 = np.mean(list(self.price_data)[-50:]) if len(self.price_data) >= 50 else None
                            indicators_data['SMA_20'] = sma_20
                            indicators_data['SMA_50'] = sma_50

                        # Calculate RSI
                        if 'RSI' in self.indicators and len(self.price_data) >= 14:
                            rsi = self._calculate_rsi(list(self.price_data))
                            indicators_data['RSI'] = rsi

                        # Calculate MACD
                        if 'MACD' in self.indicators and len(self.price_data) >= 26:
                            macd, signal, histogram = self._calculate_macd(list(self.price_data))
                            indicators_data['MACD'] = macd
                            indicators_data['MACD_Signal'] = signal
                            indicators_data['MACD_Histogram'] = histogram

                        if indicators_data:
                            processed_message = StreamMessage(
                                stream_type=StreamType.TECHNICAL_INDICATORS,
                                symbol=message.symbol,
                                timestamp=message.timestamp,
                                data=indicators_data,
                                metadata={'processor': 'technical_indicators', 'indicators': self.indicators}
                            )

                            processing_time = time.time() - start_time
                            self.metrics.processing_latency = processing_time
                            self.metrics.messages_processed += 1

                            return processed_message

            return None

        except Exception as e:
            logger.error(f"Error processing technical indicators: {e}")
            self.metrics.error_count += 1
            return None

    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI."""
        if len(prices) < period + 1:
            return 50.0

        gains = []
        losses = []

        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _calculate_macd(self, prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[float, float, float]:
        """Calculate MACD."""
        if len(prices) < slow:
            return 0.0, 0.0, 0.0

        # Calculate EMAs
        fast_ema = self._calculate_ema(prices, fast)
        slow_ema = self._calculate_ema(prices, slow)

        # MACD line
        macd = fast_ema - slow_ema

        # Signal line (EMA of MACD)
        macd_values = [self._calculate_ema(prices[:i+1], fast) - self._calculate_ema(prices[:i+1], slow)
                      for i in range(slow-1, len(prices))]

        if len(macd_values) >= signal:
            signal_line = self._calculate_ema(macd_values, signal)
        else:
            signal_line = macd

        histogram = macd - signal_line

        return macd, signal_line, histogram

    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return np.mean(prices)

        multiplier = 2 / (period + 1)
        ema = np.mean(prices[:period])

        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))

        return ema

    def get_metrics(self) -> StreamMetrics:
        return self.metrics


class StrategySignalProcessor(StreamProcessor):
    """Processor for strategy signals."""

    def __init__(self, strategy_name: str):
        self.strategy_name = strategy_name
        self.signal_history: deque = deque(maxlen=100)
        self.metrics = StreamMetrics()

    async def process(self, message: StreamMessage) -> Optional[StreamMessage]:
        """Process message and generate strategy signals."""
        try:
            start_time = time.time()

            if message.stream_type == StreamType.TECHNICAL_INDICATORS:
                # Simple strategy: Buy when RSI < 30 and MACD > Signal, Sell when RSI > 70
                rsi = message.data.get('RSI')
                macd = message.data.get('MACD')
                macd_signal = message.data.get('MACD_Signal')

                signal = None
                confidence = 0.0

                if rsi is not None and macd is not None and macd_signal is not None:
                    if rsi < 30 and macd > macd_signal:
                        signal = 'BUY'
                        confidence = min(1.0, (30 - rsi) / 30 * 0.5 + (macd - macd_signal) / abs(macd_signal) * 0.5)
                    elif rsi > 70:
                        signal = 'SELL'
                        confidence = min(1.0, (rsi - 70) / 30)

                if signal:
                    self.signal_history.append({
                        'timestamp': message.timestamp,
                        'signal': signal,
                        'confidence': confidence,
                        'rsi': rsi,
                        'macd': macd,
                        'macd_signal': macd_signal
                    })

                    processed_message = StreamMessage(
                        stream_type=StreamType.STRATEGY_SIGNALS,
                        symbol=message.symbol,
                        timestamp=message.timestamp,
                        data={
                            'signal': signal,
                            'confidence': confidence,
                            'strategy': self.strategy_name,
                            'indicators': {
                                'rsi': rsi,
                                'macd': macd,
                                'macd_signal': macd_signal
                            }
                        },
                        metadata={'processor': 'strategy_signals', 'strategy_name': self.strategy_name}
                    )

                    processing_time = time.time() - start_time
                    self.metrics.processing_latency = processing_time
                    self.metrics.messages_processed += 1

                    return processed_message

            return None

        except Exception as e:
            logger.error(f"Error processing strategy signals: {e}")
            self.metrics.error_count += 1
            return None

    def get_metrics(self) -> StreamMetrics:
        return self.metrics


class StreamPipeline:
    """
    Streaming data processing pipeline.
    """

    def __init__(self, name: str):
        self.name = name
        self.processors: List[StreamProcessor] = []
        self.input_queue: asyncio.Queue = asyncio.Queue()
        self.output_queues: Dict[str, asyncio.Queue] = {}
        self.is_running = False
        self.metrics = StreamMetrics()

    def add_processor(self, processor: StreamProcessor) -> None:
        """Add a processor to the pipeline."""
        self.processors.append(processor)

    def add_output_queue(self, name: str, queue: asyncio.Queue) -> None:
        """Add an output queue for processed messages."""
        self.output_queues[name] = queue

    async def start(self) -> None:
        """Start the streaming pipeline."""
        if self.is_running:
            return

        self.is_running = True
        logger.info(f"Starting streaming pipeline: {self.name}")

        # Start processing tasks
        tasks = []
        for i in range(len(self.processors)):
            task = asyncio.create_task(self._process_messages(i))
            tasks.append(task)

        # Wait for all tasks
        await asyncio.gather(*tasks, return_exceptions=True)

    async def stop(self) -> None:
        """Stop the streaming pipeline."""
        self.is_running = False
        logger.info(f"Stopping streaming pipeline: {self.name}")

    async def ingest_message(self, message: StreamMessage) -> None:
        """Ingest a message into the pipeline."""
        await self.input_queue.put(message)

    async def _process_messages(self, processor_index: int) -> None:
        """Process messages through the pipeline."""
        processor = self.processors[processor_index]

        while self.is_running:
            try:
                # Get input message
                if processor_index == 0:
                    # First processor gets from input queue
                    message = await self.input_queue.get()
                else:
                    # Subsequent processors get from previous processor's output
                    # This is simplified - in practice you'd need inter-processor queues
                    message = await self.input_queue.get()

                start_time = time.time()

                # Process message
                processed_message = await processor.process(message)

                processing_time = time.time() - start_time
                self.metrics.processing_latency = processing_time
                self.metrics.messages_processed += 1

                # Send to output queues
                if processed_message:
                    for queue in self.output_queues.values():
                        try:
                            await queue.put(processed_message)
                        except Exception as e:
                            logger.error(f"Error sending to output queue: {e}")

                # Mark task as done
                self.input_queue.task_done()

            except Exception as e:
                logger.error(f"Error in pipeline processor {processor_index}: {e}")
                self.metrics.error_count += 1

    def get_pipeline_metrics(self) -> Dict[str, Any]:
        """Get comprehensive pipeline metrics."""
        processor_metrics = {}
        for i, processor in enumerate(self.processors):
            processor_metrics[f"processor_{i}"] = {
                "type": processor.__class__.__name__,
                "metrics": processor.get_metrics().__dict__
            }

        return {
            "pipeline_name": self.name,
            "is_running": self.is_running,
            "processor_count": len(self.processors),
            "output_queue_count": len(self.output_queues),
            "overall_metrics": self.metrics.__dict__,
            "processor_metrics": processor_metrics
        }


class StreamSource(ABC):
    """Abstract base class for stream sources."""

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the data source."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the data source."""
        pass

    @abstractmethod
    async def stream_data(self) -> AsyncGenerator[StreamMessage, None]:
        """Stream data from the source."""
        pass


class WebSocketStreamSource(StreamSource):
    """WebSocket-based stream source."""

    def __init__(self, url: str, symbols: List[str]):
        self.url = url
        self.symbols = symbols
        self.websocket = None
        self.connected = False

    async def connect(self) -> None:
        """Connect to WebSocket."""
        try:
            self.websocket = await websockets.connect(self.url)
            self.connected = True
            logger.info(f"Connected to WebSocket: {self.url}")
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from WebSocket."""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            logger.info("Disconnected from WebSocket")

    async def stream_data(self) -> AsyncGenerator[StreamMessage, None]:
        """Stream data from WebSocket."""
        if not self.connected:
            await self.connect()

        sequence_number = 0

        try:
            while self.connected:
                message = await self.websocket.recv()
                data = json.loads(message)

                # Convert to StreamMessage
                stream_message = StreamMessage(
                    stream_type=StreamType.MARKET_DATA,
                    symbol=data.get('symbol', 'UNKNOWN'),
                    timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat())),
                    data=data,
                    sequence_number=sequence_number
                )

                sequence_number += 1
                yield stream_message

        except Exception as e:
            logger.error(f"Error streaming from WebSocket: {e}")
            await self.disconnect()


class StreamManager:
    """
    Manager for streaming data processing.
    """

    def __init__(self):
        self.pipelines: Dict[str, StreamPipeline] = {}
        self.sources: Dict[str, StreamSource] = {}
        self.is_running = False

    def create_pipeline(self, name: str) -> StreamPipeline:
        """Create a new streaming pipeline."""
        pipeline = StreamPipeline(name)
        self.pipelines[name] = pipeline
        return pipeline

    def add_source(self, name: str, source: StreamSource) -> None:
        """Add a stream source."""
        self.sources[name] = source

    async def start_streaming(self) -> None:
        """Start all streaming pipelines and sources."""
        if self.is_running:
            return

        self.is_running = True
        logger.info("Starting stream manager")

        # Start all pipelines
        pipeline_tasks = []
        for pipeline in self.pipelines.values():
            task = asyncio.create_task(pipeline.start())
            pipeline_tasks.append(task)

        # Start all sources
        source_tasks = []
        for source in self.sources.values():
            task = asyncio.create_task(self._run_source(source))
            source_tasks.append(task)

        # Wait for all tasks
        await asyncio.gather(*pipeline_tasks, *source_tasks, return_exceptions=True)

    async def stop_streaming(self) -> None:
        """Stop all streaming pipelines and sources."""
        if not self.is_running:
            return

        self.is_running = False
        logger.info("Stopping stream manager")

        # Stop pipelines
        for pipeline in self.pipelines.values():
            await pipeline.stop()

        # Disconnect sources
        for source in self.sources.values():
            await source.disconnect()

    async def _run_source(self, source: StreamSource) -> None:
        """Run a stream source."""
        try:
            await source.connect()

            async for message in source.stream_data():
                # Route message to appropriate pipelines
                for pipeline in self.pipelines.values():
                    await pipeline.ingest_message(message)

        except Exception as e:
            logger.error(f"Error running stream source: {e}")

    def get_streaming_status(self) -> Dict[str, Any]:
        """Get status of all streaming components."""
        pipeline_status = {}
        for name, pipeline in self.pipelines.items():
            pipeline_status[name] = pipeline.get_pipeline_metrics()

        return {
            "is_running": self.is_running,
            "pipeline_count": len(self.pipelines),
            "source_count": len(self.sources),
            "pipelines": pipeline_status
        }


# Global stream manager instance
_stream_manager: Optional[StreamManager] = None


def get_stream_manager() -> StreamManager:
    """Get the global stream manager."""
    global _stream_manager
    if _stream_manager is None:
        _stream_manager = StreamManager()
    return _stream_manager


# Convenience functions
def create_stream_pipeline(name: str) -> StreamPipeline:
    """Create a new streaming pipeline."""
    return get_stream_manager().create_pipeline(name)


async def start_streaming() -> None:
    """Start the streaming system."""
    await get_stream_manager().start_streaming()


async def stop_streaming() -> None:
    """Stop the streaming system."""
    await get_stream_manager().stop_streaming()


def get_streaming_status() -> Dict[str, Any]:
    """Get streaming system status."""
    return get_stream_manager().get_streaming_status()


if __name__ == "__main__":
    # Example usage
    async def main():
        # Create stream manager
        manager = get_stream_manager()

        # Create pipeline
        pipeline = manager.create_pipeline("market_data_pipeline")

        # Add processors
        market_processor = MarketDataProcessor("AAPL")
        indicator_processor = TechnicalIndicatorProcessor(['SMA', 'RSI', 'MACD'])
        strategy_processor = StrategySignalProcessor("Simple_RSI_MACD")

        pipeline.add_processor(market_processor)
        pipeline.add_processor(indicator_processor)
        pipeline.add_processor(strategy_processor)

        # Create output queue
        output_queue = asyncio.Queue()
        pipeline.add_output_queue("signals", output_queue)

        # Create sample data source (simulated)
        class SimulatedDataSource(StreamSource):
            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def stream_data(self):
                # Simulate market data
                for i in range(100):
                    price = 150 + np.random.normal(0, 2)
                    volume = np.random.randint(100000, 500000)

                    message = StreamMessage(
                        stream_type=StreamType.MARKET_DATA,
                        symbol="AAPL",
                        timestamp=datetime.now(),
                        data={
                            'open': price - 0.5,
                            'high': price + 1.0,
                            'low': price - 1.0,
                            'close': price,
                            'volume': volume
                        },
                        sequence_number=i
                    )

                    yield message
                    await asyncio.sleep(0.1)  # Simulate real-time delay

        source = SimulatedDataSource()
        manager.add_source("simulated", source)

        # Start streaming
        print("Starting streaming system...")
        await start_streaming()

        # Process some messages
        processed_count = 0
        try:
            while processed_count < 10:
                message = await output_queue.get()
                print(f"Processed signal: {message.data}")
                processed_count += 1
                output_queue.task_done()
        except KeyboardInterrupt:
            pass

        # Stop streaming
        await stop_streaming()

        # Get final status
        status = get_streaming_status()
        print(f"Final streaming status: {status}")

    # Run example
    asyncio.run(main())