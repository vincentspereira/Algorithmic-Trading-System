"""
Multi-Timeframe Aggregator for Institutional-Grade Trading

Features:
- Efficient data aggregation from base to higher timeframes
- Memory management with configurable buffers
- Real-time performance monitoring
- Error handling and data validation
- Integration with free data sources (Yahoo Finance, Alpha Vantage, Binance)
"""

import logging
import time
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
from nautilus_trader.model.data import Bar
from nautilus_trader.model.identifiers import InstrumentId


@dataclass
class AggregationMetrics:
    """Metrics for monitoring aggregation performance"""
    total_bars_processed: int = 0
    aggregation_latency_ms: float = 0.0
    memory_usage_mb: float = 0.0
    last_update_time: Optional[datetime] = None
    error_count: int = 0


class DataProvider(ABC):
    """Abstract base class for data providers"""

    @abstractmethod
    def fetch_historical_data(self, symbol: str, timeframe: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Fetch historical data for a symbol and timeframe"""
        pass

    @abstractmethod
    def fetch_real_time_data(self, symbol: str) -> Optional[Bar]:
        """Fetch real-time data for a symbol"""
        pass


class YahooFinanceProvider(DataProvider):
    """Data provider for Yahoo Finance (free tier)"""

    def fetch_historical_data(self, symbol: str, timeframe: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Fetch historical data from Yahoo Finance"""
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date, interval=timeframe)

            # Convert to our format
            df = pd.DataFrame({
                'open': data['Open'],
                'high': data['High'],
                'low': data['Low'],
                'close': data['Close'],
                'volume': data['Volume']
            })

            return df.dropna()

        except Exception as e:
            logging.error(f"Error fetching Yahoo Finance data for {symbol}: {e}")
            return pd.DataFrame()

    def fetch_real_time_data(self, symbol: str) -> Optional[Bar]:
        """Fetch real-time data from Yahoo Finance"""
        # Implementation would use yfinance for real-time data
        # For now, return None as Yahoo Finance has limitations for real-time
        return None


class AlphaVantageProvider(DataProvider):
    """Data provider for Alpha Vantage (free tier)"""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def fetch_historical_data(self, symbol: str, timeframe: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Fetch historical data from Alpha Vantage"""
        try:
            from alpha_vantage.timeseries import TimeSeries

            ts = TimeSeries(key=self.api_key, output_format='pandas')

            if timeframe == '1D':
                data, _ = ts.get_daily(symbol=symbol, outputsize='full')
            elif timeframe == '1H':
                data, _ = ts.get_intraday(symbol=symbol, interval='60min', outputsize='full')
            else:
                # For other timeframes, we'll need to resample
                data, _ = ts.get_intraday(symbol=symbol, interval='1min', outputsize='full')

            # Convert to our format
            df = pd.DataFrame({
                'open': data['1. open'],
                'high': data['2. high'],
                'low': data['3. low'],
                'close': data['4. close'],
                'volume': data['5. volume']
            })

            # Filter by date range
            df.index = pd.to_datetime(df.index)
            df = df[(df.index >= start_date) & (df.index <= end_date)]

            return df.dropna()

        except Exception as e:
            logging.error(f"Error fetching Alpha Vantage data for {symbol}: {e}")
            return pd.DataFrame()

    def fetch_real_time_data(self, symbol: str) -> Optional[Bar]:
        """Fetch real-time data from Alpha Vantage"""
        # Implementation would use Alpha Vantage real-time API
        return None


class BinanceProvider(DataProvider):
    """Data provider for Binance (crypto data)"""

    def fetch_historical_data(self, symbol: str, timeframe: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Fetch historical data from Binance"""
        try:
            from binance.client import Client

            # Note: Requires Binance API keys
            client = Client(api_key='', api_secret='')  # Would need actual keys

            # Convert timeframe to Binance format
            binance_interval = self._convert_timeframe(timeframe)

            klines = client.get_historical_klines(
                symbol, binance_interval,
                start_date.strftime("%d %b, %Y"),
                end_date.strftime("%d %b, %Y")
            )

            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])

            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            # Convert string columns to numeric
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            return df[['open', 'high', 'low', 'close', 'volume']].dropna()

        except Exception as e:
            logging.error(f"Error fetching Binance data for {symbol}: {e}")
            return pd.DataFrame()

    def fetch_real_time_data(self, symbol: str) -> Optional[Bar]:
        """Fetch real-time data from Binance WebSocket"""
        # Implementation would use Binance WebSocket streams
        return None

    def _convert_timeframe(self, timeframe: str) -> str:
        """Convert standard timeframe to Binance interval"""
        mapping = {
            '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m', '1h': '1h',
            '4h': '4h', '1d': '1d', '1w': '1w', '1M': '1M'
        }
        return mapping.get(timeframe, '1h')


class MultiTimeframeAggregator:
    """
    Enhanced multi-timeframe aggregator with institutional-grade features

    Supports:
    - Multiple data providers (Yahoo Finance, Alpha Vantage, Binance)
    - Efficient memory management
    - Performance monitoring
    - Error handling and recovery
    - Real-time data integration
    """

    def __init__(self,
                 base_timeframe: str,
                 higher_timeframes: List[str],
                 max_buffer_size: int = 10000,
                 data_provider: Optional[DataProvider] = None):
        """
        Initialize the multi-timeframe aggregator

        Args:
            base_timeframe: Base timeframe (e.g., '1m', '5m')
            higher_timeframes: List of higher timeframes to aggregate to
            max_buffer_size: Maximum number of bars to keep in memory
            data_provider: Data provider for fetching historical data
        """
        self.base_timeframe = base_timeframe
        self.higher_timeframes = higher_timeframes
        self.max_buffer_size = max_buffer_size
        self.data_provider = data_provider

        # Initialize data storage
        self._data = {}
        self._initialize_data_stores()

        # Performance monitoring
        self.metrics = AggregationMetrics()
        self.logger = logging.getLogger(self.__class__.__name__)

        # Error recovery
        self.last_error_time = None
        self.error_backoff_seconds = 60

    def _initialize_data_stores(self):
        """Initialize data storage for all timeframes"""
        columns = ["open", "high", "low", "close", "volume", "timestamp"]
        for tf in [self.base_timeframe] + self.higher_timeframes:
            self._data[tf] = pd.DataFrame(columns=columns)
            self._data[tf] = self._data[tf].set_index('timestamp')

    def update(self, bar: Bar) -> bool:
        """
        Update with new bar data

        Args:
            bar: New bar data

        Returns:
            True if update successful, False otherwise
        """
        start_time = time.time()

        try:
            # Update base timeframe data
            timestamp = pd.to_datetime(bar.ts_event, unit='ns')

            new_row = pd.DataFrame([{
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
            }], index=[timestamp])

            self._data[self.base_timeframe] = pd.concat([self._data[self.base_timeframe], new_row])

            # Maintain buffer size
            if len(self._data[self.base_timeframe]) > self.max_buffer_size:
                self._data[self.base_timeframe] = self._data[self.base_timeframe].iloc[-self.max_buffer_size:]

            # Resample to higher timeframes
            self._resample_higher_timeframes()

            # Update metrics
            self.metrics.total_bars_processed += 1
            self.metrics.aggregation_latency_ms = (time.time() - start_time) * 1000
            self.metrics.last_update_time = datetime.now()

            return True

        except Exception as e:
            self.logger.error(f"Error updating aggregator: {e}")
            self.metrics.error_count += 1
            self.last_error_time = datetime.now()
            return False

    def _resample_higher_timeframes(self):
        """Resample base timeframe data to higher timeframes"""
        base_data = self._data[self.base_timeframe]

        if len(base_data) == 0:
            return

        for tf in self.higher_timeframes:
            try:
                # Resample with proper OHLC aggregation
                resampled = base_data.resample(tf).agg({
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                }).dropna()

                # Update higher timeframe data
                self._data[tf] = pd.concat([self._data[tf], resampled])
                self._data[tf] = self._data[tf][~self._data[tf].index.duplicated(keep='last')]

                # Maintain buffer size
                if len(self._data[tf]) > self.max_buffer_size // 10:  # Smaller buffer for higher TFs
                    self._data[tf] = self._data[tf].iloc[-self.max_buffer_size // 10:]

            except Exception as e:
                self.logger.error(f"Error resampling to {tf}: {e}")

    def get_data(self, timeframe: str) -> pd.DataFrame:
        """Get data for specified timeframe"""
        return self._data.get(timeframe, pd.DataFrame())

    def get_latest_bar(self, timeframe: str) -> Optional[Dict[str, Any]]:
        """Get latest bar for specified timeframe"""
        data = self.get_data(timeframe)
        if len(data) == 0:
            return None

        latest = data.iloc[-1]
        return {
            'timestamp': latest.name,
            'open': latest['open'],
            'high': latest['high'],
            'low': latest['low'],
            'close': latest['close'],
            'volume': latest['volume']
        }

    def load_historical_data(self, symbol: str, start_date: datetime, end_date: datetime) -> bool:
        """Load historical data using configured data provider"""
        if not self.data_provider:
            self.logger.warning("No data provider configured for historical data loading")
            return False

        try:
            # Load base timeframe data
            base_data = self.data_provider.fetch_historical_data(
                symbol, self.base_timeframe, start_date, end_date
            )

            if len(base_data) > 0:
                # Convert index to timestamp if needed
                if not isinstance(base_data.index, pd.DatetimeIndex):
                    base_data.index = pd.to_datetime(base_data.index)

                # Add timestamp column
                base_data['timestamp'] = base_data.index

                self._data[self.base_timeframe] = pd.concat([
                    self._data[self.base_timeframe],
                    base_data
                ]).drop_duplicates()

                # Resample higher timeframes
                self._resample_higher_timeframes()

                self.logger.info(f"Loaded {len(base_data)} historical bars for {symbol}")
                return True

        except Exception as e:
            self.logger.error(f"Error loading historical data for {symbol}: {e}")

        return False

    def get_metrics(self) -> AggregationMetrics:
        """Get current performance metrics"""
        # Update memory usage
        total_memory = 0
        for df in self._data.values():
            total_memory += df.memory_usage(deep=True).sum()
        self.metrics.memory_usage_mb = total_memory / (1024 * 1024)

        return self.metrics

    def reset(self):
        """Reset the aggregator to initial state"""
        self._initialize_data_stores()
        self.metrics = AggregationMetrics()
        self.logger.info("Aggregator reset to initial state")