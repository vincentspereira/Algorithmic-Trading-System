"""
Data Feed Management System with Fallback Logic

This module provides a unified interface for retrieving financial data from multiple sources
with automatic fallback capabilities. It supports various asset classes including stocks,
futures, options, forex, commodities, and cryptocurrencies.

Data Source Priority Order:
1. Yahoo Finance (yfinance)
2. Alpha Vantage
3. Finnhub
4. Investing.com
5. CME Group
6. Twelve Data
7. Polygon
8. Barchart
9. SpiderRock
10. TradingCharts
11. Oanda

Author: Vincent S. Pereira
Version: 1.0.0
"""

import logging
import time
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import yfinance as yf
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.fundamentaldata import FundamentalData
from alpha_vantage.cryptocurrencies import CryptoCurrencies
from alpha_vantage.foreignexchange import ForeignExchange
import structlog

# Configure structured logging
logger = structlog.get_logger(__name__)


class AssetClass(Enum):
    """Supported asset classes"""
    STOCK = "stock"
    FUTURES = "futures"
    OPTIONS = "options"
    FOREX = "forex"
    COMMODITIES = "commodities"
    CRYPTO = "crypto"


class DataSource(Enum):
    """Available data sources in priority order"""
    YAHOO_FINANCE = "yahoo_finance"
    ALPHA_VANTAGE = "alpha_vantage"
    FINNHUB = "finnhub"
    INVESTING_COM = "investing_com"
    CME_GROUP = "cme_group"
    TWELVE_DATA = "twelve_data"
    POLYGON = "polygon"
    BARCHART = "barchart"
    SPIDERROCK = "spiderrock"
    TRADING_CHARTS = "trading_charts"
    OANDA = "oanda"


@dataclass
class DataRequest:
    """Data request configuration"""
    ticker: str
    asset_class: AssetClass
    interval: str = "1d"  # 1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo
    period: str = "1y"    # 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@dataclass
class DataResponse:
    """Standardized data response"""
    data: pd.DataFrame
    source: DataSource
    ticker: str
    asset_class: AssetClass
    metadata: Dict[str, Any]
    timestamp: float
    success: bool = True
    error_message: Optional[str] = None


class RateLimitManager:
    """Manages API rate limits for different data sources"""
    
    def __init__(self):
        self.last_request_time = {}
        self.request_counts = {}
        self.rate_limits = {
            DataSource.YAHOO_FINANCE: {"requests_per_second": 2, "requests_per_hour": 2000},
            DataSource.ALPHA_VANTAGE: {"requests_per_minute": 5, "requests_per_day": 500},
            DataSource.FINNHUB: {"requests_per_minute": 60, "requests_per_month": 1000000},
            DataSource.TWELVE_DATA: {"requests_per_minute": 8, "requests_per_day": 800},
            DataSource.POLYGON: {"requests_per_minute": 5, "requests_per_month": 1000000},
        }
    
    def can_make_request(self, source: DataSource) -> bool:
        """Check if a request can be made to the specified source"""
        current_time = time.time()
        
        if source not in self.rate_limits:
            return True
        
        limits = self.rate_limits[source]
        last_time = self.last_request_time.get(source, 0)
        
        # Simple rate limiting - wait at least 1 second between requests
        if current_time - last_time < 1.0:
            return False
        
        return True
    
    def record_request(self, source: DataSource):
        """Record that a request was made to the specified source"""
        self.last_request_time[source] = time.time()
        self.request_counts[source] = self.request_counts.get(source, 0) + 1


class DataFeedManager:
    """Main data feed management class with fallback logic"""
    
    def __init__(self, alpha_vantage_api_key: Optional[str] = None):
        self.alpha_vantage_api_key = alpha_vantage_api_key
        self.rate_limit_manager = RateLimitManager()
        self.source_priority = [
            DataSource.YAHOO_FINANCE,
            DataSource.ALPHA_VANTAGE,
            DataSource.FINNHUB,
            DataSource.INVESTING_COM,
            DataSource.CME_GROUP,
            DataSource.TWELVE_DATA,
            DataSource.POLYGON,
            DataSource.BARCHART,
            DataSource.SPIDERROCK,
            DataSource.TRADING_CHARTS,
            DataSource.OANDA,
        ]
        
        # Initialize Alpha Vantage clients if API key is provided
        if self.alpha_vantage_api_key:
            self.av_timeseries = TimeSeries(key=self.alpha_vantage_api_key, output_format='pandas')
            self.av_fundamentals = FundamentalData(key=self.alpha_vantage_api_key, output_format='pandas')
            self.av_crypto = CryptoCurrencies(key=self.alpha_vantage_api_key, output_format='pandas')
            self.av_forex = ForeignExchange(key=self.alpha_vantage_api_key, output_format='pandas')
    
    def get_data(self, ticker: str, source: Optional[DataSource] = None, 
                 asset_class: AssetClass = AssetClass.STOCK, **kwargs) -> DataResponse:
        """
        Get financial data with automatic fallback logic
        
        Args:
            ticker: Symbol/ticker to retrieve data for
            source: Specific data source to use (optional, will use fallback if None)
            asset_class: Type of asset (stock, futures, options, etc.)
            **kwargs: Additional parameters for data request
        
        Returns:
            DataResponse: Standardized response with data and metadata
        """
        request = DataRequest(
            ticker=ticker,
            asset_class=asset_class,
            interval=kwargs.get('interval', '1d'),
            period=kwargs.get('period', '1y'),
            start_date=kwargs.get('start_date'),
            end_date=kwargs.get('end_date')
        )
        
        logger.info("Data request initiated", 
                   ticker=ticker, 
                   asset_class=asset_class.value,
                   source=source.value if source else "auto_fallback")
        
        # If specific source is requested, try only that source
        if source:
            return self._fetch_from_source(source, request)
        
        # Otherwise, try sources in priority order
        last_error = None
        for data_source in self.source_priority:
            try:
                if not self.rate_limit_manager.can_make_request(data_source):
                    logger.warning("Rate limit exceeded, skipping source", 
                                 source=data_source.value)
                    continue
                
                response = self._fetch_from_source(data_source, request)
                if response.success and not response.data.empty:
                    logger.info("Data successfully retrieved", 
                              source=data_source.value, 
                              ticker=ticker,
                              rows=len(response.data))
                    return response
                
            except Exception as e:
                last_error = str(e)
                logger.warning("Data source failed, trying next", 
                             source=data_source.value, 
                             error=str(e))
                continue
        
        # All sources failed
        logger.error("All data sources failed", 
                    ticker=ticker, 
                    last_error=last_error)
        
        return DataResponse(
            data=pd.DataFrame(),
            source=DataSource.YAHOO_FINANCE,  # Default
            ticker=ticker,
            asset_class=asset_class,
            metadata={"error": "All data sources failed"},
            timestamp=time.time(),
            success=False,
            error_message=f"All data sources failed. Last error: {last_error}"
        )
    
    def _fetch_from_source(self, source: DataSource, request: DataRequest) -> DataResponse:
        """Fetch data from a specific source"""
        
        self.rate_limit_manager.record_request(source)
        
        try:
            if source == DataSource.YAHOO_FINANCE:
                return self._fetch_yahoo_finance(request)
            elif source == DataSource.ALPHA_VANTAGE:
                return self._fetch_alpha_vantage(request)
            elif source == DataSource.FINNHUB:
                return self._fetch_finnhub(request)
            elif source == DataSource.INVESTING_COM:
                return self._fetch_investing_com(request)
            elif source == DataSource.CME_GROUP:
                return self._fetch_cme_group(request)
            elif source == DataSource.TWELVE_DATA:
                return self._fetch_twelve_data(request)
            elif source == DataSource.POLYGON:
                return self._fetch_polygon(request)
            elif source == DataSource.BARCHART:
                return self._fetch_barchart(request)
            elif source == DataSource.SPIDERROCK:
                return self._fetch_spiderrock(request)
            elif source == DataSource.TRADING_CHARTS:
                return self._fetch_trading_charts(request)
            elif source == DataSource.OANDA:
                return self._fetch_oanda(request)
            else:
                raise ValueError(f"Unsupported data source: {source}")
                
        except Exception as e:
            logger.error("Error fetching from source", 
                        source=source.value, 
                        error=str(e))
            return DataResponse(
                data=pd.DataFrame(),
                source=source,
                ticker=request.ticker,
                asset_class=request.asset_class,
                metadata={"error": str(e)},
                timestamp=time.time(),
                success=False,
                error_message=str(e)
            )
    
    def _fetch_yahoo_finance(self, request: DataRequest) -> DataResponse:
        """Fetch data from Yahoo Finance using yfinance"""
        try:
            ticker_obj = yf.Ticker(request.ticker)
            
            # Get historical data
            if request.start_date and request.end_date:
                data = ticker_obj.history(
                    start=request.start_date,
                    end=request.end_date,
                    interval=request.interval
                )
            else:
                data = ticker_obj.history(
                    period=request.period,
                    interval=request.interval
                )
            
            if data.empty:
                raise ValueError("No data returned from Yahoo Finance")
            
            # Standardize column names
            data.columns = [col.lower().replace(' ', '_') for col in data.columns]
            
            # Get additional metadata
            info = ticker_obj.info
            
            return DataResponse(
                data=data,
                source=DataSource.YAHOO_FINANCE,
                ticker=request.ticker,
                asset_class=request.asset_class,
                metadata={
                    "info": info,
                    "interval": request.interval,
                    "period": request.period
                },
                timestamp=time.time(),
                success=True
            )
            
        except Exception as e:
            raise Exception(f"Yahoo Finance error: {str(e)}")
    
    def _fetch_alpha_vantage(self, request: DataRequest) -> DataResponse:
        """Fetch data from Alpha Vantage"""
        if not self.alpha_vantage_api_key:
            raise ValueError("Alpha Vantage API key not provided")
        
        try:
            if request.asset_class == AssetClass.STOCK:
                data, meta_data = self.av_timeseries.get_daily(
                    symbol=request.ticker, 
                    outputsize='full'
                )
            elif request.asset_class == AssetClass.CRYPTO:
                data, meta_data = self.av_crypto.get_digital_currency_daily(
                    symbol=request.ticker, 
                    market='USD'
                )
            elif request.asset_class == AssetClass.FOREX:
                # For forex, ticker should be in format "EUR/USD"
                from_symbol, to_symbol = request.ticker.split('/')
                data, meta_data = self.av_forex.get_currency_exchange_daily(
                    from_symbol=from_symbol,
                    to_symbol=to_symbol
                )
            else:
                raise ValueError(f"Asset class {request.asset_class} not supported by Alpha Vantage")
            
            if data.empty:
                raise ValueError("No data returned from Alpha Vantage")
            
            # Standardize column names
            data.columns = [col.lower().replace(' ', '_').replace('.', '_') for col in data.columns]
            
            return DataResponse(
                data=data,
                source=DataSource.ALPHA_VANTAGE,
                ticker=request.ticker,
                asset_class=request.asset_class,
                metadata={"meta_data": meta_data},
                timestamp=time.time(),
                success=True
            )
            
        except Exception as e:
            raise Exception(f"Alpha Vantage error: {str(e)}")
    
    def _fetch_finnhub(self, request: DataRequest) -> DataResponse:
        """Fetch data from Finnhub (placeholder implementation)"""
        # TODO: Implement Finnhub integration
        raise NotImplementedError("Finnhub integration not yet implemented")
    
    def _fetch_investing_com(self, request: DataRequest) -> DataResponse:
        """Fetch data from Investing.com (placeholder implementation)"""
        # TODO: Implement Investing.com integration
        raise NotImplementedError("Investing.com integration not yet implemented")
    
    def _fetch_cme_group(self, request: DataRequest) -> DataResponse:
        """Fetch data from CME Group (placeholder implementation)"""
        # TODO: Implement CME Group integration
        raise NotImplementedError("CME Group integration not yet implemented")
    
    def _fetch_twelve_data(self, request: DataRequest) -> DataResponse:
        """Fetch data from Twelve Data (placeholder implementation)"""
        # TODO: Implement Twelve Data integration
        raise NotImplementedError("Twelve Data integration not yet implemented")
    
    def _fetch_polygon(self, request: DataRequest) -> DataResponse:
        """Fetch data from Polygon (placeholder implementation)"""
        # TODO: Implement Polygon integration
        raise NotImplementedError("Polygon integration not yet implemented")
    
    def _fetch_barchart(self, request: DataRequest) -> DataResponse:
        """Fetch data from Barchart (placeholder implementation)"""
        # TODO: Implement Barchart integration
        raise NotImplementedError("Barchart integration not yet implemented")
    
    def _fetch_spiderrock(self, request: DataRequest) -> DataResponse:
        """Fetch data from SpiderRock (placeholder implementation)"""
        # TODO: Implement SpiderRock integration
        raise NotImplementedError("SpiderRock integration not yet implemented")
    
    def _fetch_trading_charts(self, request: DataRequest) -> DataResponse:
        """Fetch data from TradingCharts (placeholder implementation)"""
        # TODO: Implement TradingCharts integration
        raise NotImplementedError("TradingCharts integration not yet implemented")
    
    def _fetch_oanda(self, request: DataRequest) -> DataResponse:
        """Fetch data from Oanda (placeholder implementation)"""
        # TODO: Implement Oanda integration
        raise NotImplementedError("Oanda integration not yet implemented")
    
    def get_supported_assets(self, source: DataSource) -> List[AssetClass]:
        """Get list of supported asset classes for a given source"""
        support_matrix = {
            DataSource.YAHOO_FINANCE: [AssetClass.STOCK, AssetClass.FUTURES, AssetClass.OPTIONS, 
                                     AssetClass.FOREX, AssetClass.COMMODITIES, AssetClass.CRYPTO],
            DataSource.ALPHA_VANTAGE: [AssetClass.STOCK, AssetClass.FOREX, AssetClass.CRYPTO],
            DataSource.FINNHUB: [AssetClass.STOCK, AssetClass.FOREX, AssetClass.CRYPTO],
            DataSource.POLYGON: [AssetClass.STOCK, AssetClass.OPTIONS, AssetClass.FOREX, AssetClass.CRYPTO],
            DataSource.OANDA: [AssetClass.FOREX],
        }
        
        return support_matrix.get(source, [])
    
    def health_check(self) -> Dict[str, bool]:
        """Check the health/availability of all data sources"""
        health_status = {}
        
        for source in self.source_priority:
            try:
                # Try to fetch a simple data point to test connectivity
                test_response = self._fetch_from_source(
                    source, 
                    DataRequest(ticker="AAPL", asset_class=AssetClass.STOCK, period="1d")
                )
                health_status[source.value] = test_response.success
            except Exception:
                health_status[source.value] = False
        
        return health_status


# Convenience function for easy access
def get_data(ticker: str, source: Optional[str] = None, 
             asset_class: str = "stock", **kwargs) -> DataResponse:
    """
    Convenience function to get financial data
    
    Args:
        ticker: Symbol/ticker to retrieve data for
        source: Specific data source to use (optional)
        asset_class: Type of asset (stock, futures, options, etc.)
        **kwargs: Additional parameters
    
    Returns:
        DataResponse: Standardized response with data and metadata
    """
    # Convert string parameters to enums
    asset_class_enum = AssetClass(asset_class.lower())
    source_enum = DataSource(source.lower()) if source else None
    
    # Initialize data feed manager
    manager = DataFeedManager()
    
    return manager.get_data(
        ticker=ticker,
        source=source_enum,
        asset_class=asset_class_enum,
        **kwargs
    )


if __name__ == "__main__":
    # Example usage
    import os
    
    # Initialize with Alpha Vantage API key from environment
    alpha_vantage_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    manager = DataFeedManager(alpha_vantage_api_key=alpha_vantage_key)
    
    # Test data retrieval with fallback
    response = manager.get_data("AAPL", asset_class=AssetClass.STOCK)
    
    if response.success:
        print(f"Successfully retrieved data from {response.source.value}")
        print(f"Data shape: {response.data.shape}")
        print(response.data.head())
    else:
        print(f"Failed to retrieve data: {response.error_message}")
    
    # Test health check
    health = manager.health_check()
    print("\nData source health check:")
    for source, status in health.items():
        print(f"{source}: {'✓' if status else '✗'}")