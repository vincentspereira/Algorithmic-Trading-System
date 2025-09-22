#!/usr/bin/env python3
"""
Data Manager Module

Manages market data for backtesting, including:
- Data loading and preprocessing
- Data validation and cleaning
- Multi-asset data synchronization
- Historical data caching
- Real-time data simulation
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import logging
from abc import ABC, abstractmethod

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    import pandas_datareader as pdr
    PANDAS_DATAREADER_AVAILABLE = True
except ImportError:
    PANDAS_DATAREADER_AVAILABLE = False

from ...indicators.consolidated_indicators import ConsolidatedIndicators


@dataclass
class DataConfig:
    """Configuration for data management."""
    start_date: datetime
    end_date: datetime
    symbols: List[str]
    frequency: str = '1D'  # '1D', '1H', '1M', etc.
    data_source: str = 'yahoo'  # 'yahoo', 'alpha_vantage', etc.
    cache_dir: Optional[str] = None
    validate_data: bool = True
    fill_missing: bool = True
    adjust_prices: bool = True
    

@dataclass
class MarketData:
    """Container for market data."""
    symbol: str
    data: pd.DataFrame
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        """Validate data structure."""
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in self.data.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
    
    @property
    def ohlcv(self) -> pd.DataFrame:
        """Get OHLCV data."""
        return self.data[['open', 'high', 'low', 'close', 'volume']]
    
    @property
    def returns(self) -> pd.Series:
        """Calculate returns."""
        return self.data['close'].pct_change().dropna()
    
    @property
    def log_returns(self) -> pd.Series:
        """Calculate log returns."""
        return np.log(self.data['close'] / self.data['close'].shift(1)).dropna()
    
    def resample(self, frequency: str) -> 'MarketData':
        """Resample data to different frequency."""
        resampled = self.data.resample(frequency).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        return MarketData(
            symbol=self.symbol,
            data=resampled,
            metadata={**self.metadata, 'frequency': frequency}
        )


class DataSource(ABC):
    """Abstract base class for data sources."""
    
    @abstractmethod
    def fetch_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        frequency: str = '1D'
    ) -> pd.DataFrame:
        """Fetch data for a symbol."""
        pass
    
    @abstractmethod
    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols."""
        pass


class YahooFinanceSource(DataSource):
    """Yahoo Finance data source."""
    
    def __init__(self):
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance package is required for Yahoo Finance data source")
    
    def fetch_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        frequency: str = '1D'
    ) -> pd.DataFrame:
        """Fetch data from Yahoo Finance."""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(
                start=start_date,
                end=end_date,
                interval=self._convert_frequency(frequency)
            )
            
            # Standardize column names
            data.columns = data.columns.str.lower()
            
            return data
        except Exception as e:
            logging.error(f"Failed to fetch data for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols (simplified)."""
        # This would typically query Yahoo Finance for available symbols
        # For now, return a sample list
        return ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'SPY', 'QQQ']
    
    def _convert_frequency(self, frequency: str) -> str:
        """Convert frequency to Yahoo Finance format."""
        frequency_map = {
            '1M': '1m',
            '5M': '5m',
            '15M': '15m',
            '30M': '30m',
            '1H': '1h',
            '1D': '1d',
            '1W': '1wk',
            '1MO': '1mo'
        }
        return frequency_map.get(frequency, '1d')


class MockDataSource(DataSource):
    """Mock data source for testing."""
    
    def fetch_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        frequency: str = '1D'
    ) -> pd.DataFrame:
        """Generate mock data."""
        # Generate date range
        if frequency == '1D':
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
        elif frequency == '1H':
            dates = pd.date_range(start=start_date, end=end_date, freq='H')
        else:
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Generate mock price data
        np.random.seed(hash(symbol) % 2**32)  # Consistent seed per symbol
        
        n_periods = len(dates)
        returns = np.random.normal(0.001, 0.02, n_periods)  # Daily returns
        
        # Starting price
        start_price = 100.0
        prices = [start_price]
        
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        prices = np.array(prices)
        
        # Generate OHLC from close prices
        high = prices * (1 + np.abs(np.random.normal(0, 0.01, n_periods)))
        low = prices * (1 - np.abs(np.random.normal(0, 0.01, n_periods)))
        open_prices = np.roll(prices, 1)
        open_prices[0] = start_price
        
        # Generate volume
        volume = np.random.randint(1000000, 10000000, n_periods)
        
        data = pd.DataFrame({
            'open': open_prices,
            'high': high,
            'low': low,
            'close': prices,
            'volume': volume
        }, index=dates)
        
        return data
    
    def get_available_symbols(self) -> List[str]:
        """Get list of mock symbols."""
        return ['MOCK_AAPL', 'MOCK_GOOGL', 'MOCK_MSFT', 'MOCK_SPY']


class DataManager:
    """Manages market data for backtesting."""
    
    def __init__(self, config: DataConfig):
        self.config = config
        self.data_cache: Dict[str, MarketData] = {}
        self.data_source = self._create_data_source()
        
        # Setup caching
        if config.cache_dir:
            self.cache_dir = Path(config.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.cache_dir = None
    
    def _create_data_source(self) -> DataSource:
        """Create appropriate data source."""
        if self.config.data_source == 'yahoo':
            if YFINANCE_AVAILABLE:
                return YahooFinanceSource()
            else:
                logging.warning("Yahoo Finance not available, using mock data")
                return MockDataSource()
        elif self.config.data_source == 'mock':
            return MockDataSource()
        else:
            raise ValueError(f"Unsupported data source: {self.config.data_source}")
    
    def load_data(self, symbols: Optional[List[str]] = None) -> Dict[str, MarketData]:
        """Load data for specified symbols."""
        symbols = symbols or self.config.symbols
        
        for symbol in symbols:
            if symbol not in self.data_cache:
                self.data_cache[symbol] = self._load_symbol_data(symbol)
        
        return {symbol: self.data_cache[symbol] for symbol in symbols}
    
    def _load_symbol_data(self, symbol: str) -> MarketData:
        """Load data for a single symbol."""
        # Check cache first
        if self.cache_dir:
            cache_file = self.cache_dir / f"{symbol}_{self.config.frequency}.parquet"
            if cache_file.exists():
                try:
                    data = pd.read_parquet(cache_file)
                    logging.info(f"Loaded {symbol} from cache")
                    return MarketData(
                        symbol=symbol,
                        data=data,
                        metadata={'source': 'cache', 'frequency': self.config.frequency}
                    )
                except Exception as e:
                    logging.warning(f"Failed to load cache for {symbol}: {e}")
        
        # Fetch from data source
        logging.info(f"Fetching {symbol} from {self.config.data_source}")
        data = self.data_source.fetch_data(
            symbol=symbol,
            start_date=self.config.start_date,
            end_date=self.config.end_date,
            frequency=self.config.frequency
        )
        
        if data.empty:
            raise ValueError(f"No data available for symbol: {symbol}")
        
        # Validate and clean data
        if self.config.validate_data:
            data = self._validate_and_clean_data(data)
        
        # Adjust prices if requested
        if self.config.adjust_prices:
            data = self._adjust_prices(data)
        
        # Cache data
        if self.cache_dir:
            cache_file = self.cache_dir / f"{symbol}_{self.config.frequency}.parquet"
            try:
                data.to_parquet(cache_file)
                logging.info(f"Cached {symbol} data")
            except Exception as e:
                logging.warning(f"Failed to cache {symbol}: {e}")
        
        return MarketData(
            symbol=symbol,
            data=data,
            metadata={
                'source': self.config.data_source,
                'frequency': self.config.frequency,
                'start_date': self.config.start_date,
                'end_date': self.config.end_date
            }
        )
    
    def _validate_and_clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Validate and clean market data."""
        # Remove rows with invalid prices
        data = data[(data['high'] >= data['low']) & 
                   (data['high'] >= data['close']) & 
                   (data['low'] <= data['close']) &
                   (data['volume'] >= 0)]
        
        # Fill missing values if requested
        if self.config.fill_missing:
            data = data.fillna(method='ffill').fillna(method='bfill')
        
        # Remove outliers (prices that change more than 50% in one period)
        price_change = data['close'].pct_change().abs()
        data = data[price_change < 0.5]
        
        return data
    
    def _adjust_prices(self, data: pd.DataFrame) -> pd.DataFrame:
        """Adjust prices for splits and dividends (simplified)."""
        # This is a simplified adjustment - in practice, you'd use
        # actual adjustment factors from the data provider
        return data
    
    def get_synchronized_data(
        self,
        symbols: Optional[List[str]] = None,
        method: str = 'inner'
    ) -> pd.DataFrame:
        """Get synchronized data for multiple symbols.
        
        Args:
            symbols: List of symbols to synchronize
            method: Join method ('inner', 'outer', 'left', 'right')
            
        Returns:
            DataFrame with synchronized data
        """
        symbols = symbols or self.config.symbols
        data_dict = self.load_data(symbols)
        
        # Create multi-level columns DataFrame
        dfs = []
        for symbol, market_data in data_dict.items():
            df = market_data.data.copy()
            df.columns = pd.MultiIndex.from_product([[symbol], df.columns])
            dfs.append(df)
        
        # Concatenate and synchronize
        synchronized = pd.concat(dfs, axis=1, join=method)
        
        return synchronized
    
    def get_returns_matrix(self, symbols: Optional[List[str]] = None) -> pd.DataFrame:
        """Get returns matrix for multiple symbols."""
        symbols = symbols or self.config.symbols
        data_dict = self.load_data(symbols)
        
        returns_dict = {}
        for symbol, market_data in data_dict.items():
            returns_dict[symbol] = market_data.returns
        
        returns_df = pd.DataFrame(returns_dict)
        return returns_df.dropna()
    
    def get_correlation_matrix(self, symbols: Optional[List[str]] = None) -> pd.DataFrame:
        """Get correlation matrix for symbols."""
        returns_df = self.get_returns_matrix(symbols)
        return returns_df.corr()
    
    def clear_cache(self):
        """Clear data cache."""
        self.data_cache.clear()
        if self.cache_dir and self.cache_dir.exists():
            for cache_file in self.cache_dir.glob("*.parquet"):
                cache_file.unlink()
    
    def get_data_summary(self) -> Dict[str, Any]:
        """Get summary of loaded data."""
        summary = {
            'symbols': list(self.data_cache.keys()),
            'date_range': {
                'start': self.config.start_date,
                'end': self.config.end_date
            },
            'frequency': self.config.frequency,
            'data_source': self.config.data_source
        }
        
        if self.data_cache:
            # Get data statistics
            first_symbol = list(self.data_cache.keys())[0]
            sample_data = self.data_cache[first_symbol]
            summary['data_points'] = len(sample_data.data)
            summary['columns'] = list(sample_data.data.columns)
        
        return summary


def create_data_manager(
    symbols: List[str],
    start_date: datetime,
    end_date: datetime,
    frequency: str = '1D',
    data_source: str = 'yahoo',
    cache_dir: Optional[str] = None
) -> DataManager:
    """Factory function to create a DataManager instance.
    
    Args:
        symbols: List of symbols to load
        start_date: Start date for data
        end_date: End date for data
        frequency: Data frequency
        data_source: Data source to use
        cache_dir: Directory for caching data
        
    Returns:
        DataManager instance
    """
    config = DataConfig(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        frequency=frequency,
        data_source=data_source,
        cache_dir=cache_dir
    )
    
    return DataManager(config)


# Example usage
if __name__ == "__main__":
    # Create data manager
    symbols = ['AAPL', 'GOOGL', 'MSFT']
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 12, 31)
    
    data_manager = create_data_manager(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        data_source='mock'  # Use mock data for example
    )
    
    # Load data
    data_dict = data_manager.load_data()
    
    # Get synchronized data
    sync_data = data_manager.get_synchronized_data()
    
    # Get correlation matrix
    corr_matrix = data_manager.get_correlation_matrix()
    
    print(f"Loaded data for {len(data_dict)} symbols")
    print(f"Data summary: {data_manager.get_data_summary()}")
    print(f"Correlation matrix shape: {corr_matrix.shape}")