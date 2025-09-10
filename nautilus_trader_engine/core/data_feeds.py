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
from collections import defaultdict
import pandas as pd
import yfinance as yf
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.fundamentaldata import FundamentalData
from alpha_vantage.cryptocurrencies import CryptoCurrencies
from alpha_vantage.foreignexchange import ForeignExchange
import structlog

# Add imports for additional data sources
try:
    import finnhub
    FINNHUB_AVAILABLE = True
except ImportError:
    FINNHUB_AVAILABLE = False
    logging.warning("Finnhub not available. Install finnhub-python for Finnhub support.")

try:
    import twelvedata
    TWELVE_DATA_AVAILABLE = True
except ImportError:
    TWELVE_DATA_AVAILABLE = False
    logging.warning("Twelve Data not available. Install twelvedata for Twelve Data support.")

try:
    import polygon
    POLYGON_AVAILABLE = True
except ImportError:
    POLYGON_AVAILABLE = False
    logging.warning("Polygon not available. Install polygon-api-client for Polygon support.")

try:
    import oandapyV20
    OANDA_AVAILABLE = True
except ImportError:
    OANDA_AVAILABLE = False
    logging.warning("Oanda not available. Install oandapyV20 for Oanda support.")

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


class DataFeedHealthMonitor:
    """Monitors the health and performance of data feeds"""
    
    def __init__(self):
        self.health_history = {}
        self.performance_metrics = {}
        self.alert_thresholds = {
            'success_rate': 0.95,  # 95% success rate
            'response_time': 5.0,  # 5 seconds
            'availability': 0.99   # 99% availability
        }
    
    def record_health_check(self, source: DataSource, success: bool, response_time: float):
        """Record a health check result"""
        if source not in self.health_history:
            self.health_history[source] = []
        
        check_result = {
            'timestamp': time.time(),
            'success': success,
            'response_time': response_time
        }
        
        self.health_history[source].append(check_result)
        
        # Keep only the last 1000 health checks
        if len(self.health_history[source]) > 1000:
            self.health_history[source] = self.health_history[source][-1000:]
    
    def get_health_status(self, source: DataSource) -> Dict[str, Any]:
        """Get health status for a specific data source"""
        if source not in self.health_history or not self.health_history[source]:
            return {'status': 'unknown', 'details': 'No health data available'}
        
        recent_checks = self.health_history[source][-100:]  # Last 100 checks
        total_checks = len(recent_checks)
        successful_checks = sum(1 for check in recent_checks if check['success'])
        avg_response_time = sum(check['response_time'] for check in recent_checks) / total_checks
        
        success_rate = successful_checks / total_checks
        
        # Determine status based on thresholds
        if success_rate >= self.alert_thresholds['success_rate'] and avg_response_time <= self.alert_thresholds['response_time']:
            status = 'healthy'
        elif success_rate >= 0.8 and avg_response_time <= self.alert_thresholds['response_time'] * 2:
            status = 'degraded'
        else:
            status = 'unhealthy'
        
        return {
            'status': status,
            'success_rate': success_rate,
            'avg_response_time': avg_response_time,
            'total_checks': total_checks,
            'successful_checks': successful_checks
        }
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall health status for all data sources"""
        overall_status = 'healthy'
        source_health = {}
        
        for source in DataSource:
            health = self.get_health_status(source)
            source_health[source.value] = health
            
            # If any source is unhealthy, overall status is degraded
            # If any source is degraded and none are unhealthy, overall status is degraded
            if health['status'] == 'unhealthy':
                overall_status = 'unhealthy'
            elif health['status'] == 'degraded' and overall_status == 'healthy':
                overall_status = 'degraded'
        
        return {
            'overall_status': overall_status,
            'sources': source_health
        }
    
    def should_alert(self, source: DataSource) -> bool:
        """Determine if an alert should be sent for a data source"""
        health = self.get_health_status(source)
        return health['status'] in ['degraded', 'unhealthy']


class DataFeedManager:
    """Main data feed management class with fallback logic"""
    
    def __init__(self, alpha_vantage_api_key: Optional[str] = None, 
                 finnhub_api_key: Optional[str] = None,
                 twelve_data_api_key: Optional[str] = None,
                 polygon_api_key: Optional[str] = None,
                 oanda_api_key: Optional[str] = None,
                 oanda_account_id: Optional[str] = None):
        self.alpha_vantage_api_key = alpha_vantage_api_key
        self.finnhub_api_key = finnhub_api_key
        self.twelve_data_api_key = twelve_data_api_key
        self.polygon_api_key = polygon_api_key
        self.oanda_api_key = oanda_api_key
        self.oanda_account_id = oanda_account_id
        self.rate_limit_manager = RateLimitManager()
        self.health_monitor = DataFeedHealthMonitor()
        
        # Define source priority by asset class
        self.source_priority_by_asset = {
            AssetClass.STOCK: [
                DataSource.YAHOO_FINANCE,
                DataSource.ALPHA_VANTAGE,
                DataSource.FINNHUB,
                DataSource.TWELVE_DATA,
                DataSource.POLYGON,
                DataSource.INVESTING_COM,
                DataSource.CME_GROUP,
                DataSource.BARCHART,
                DataSource.SPIDERROCK,
                DataSource.TRADING_CHARTS
            ],
            AssetClass.FUTURES: [
                DataSource.CME_GROUP,
                DataSource.YAHOO_FINANCE,
                DataSource.INVESTING_COM,
                DataSource.BARCHART,
                DataSource.TRADING_CHARTS
            ],
            AssetClass.OPTIONS: [
                DataSource.YAHOO_FINANCE,
                DataSource.POLYGON,
                DataSource.SPIDERROCK,
                DataSource.CME_GROUP
            ],
            AssetClass.FOREX: [
                DataSource.OANDA,
                DataSource.ALPHA_VANTAGE,
                DataSource.FINNHUB,
                DataSource.YAHOO_FINANCE,
                DataSource.INVESTING_COM
            ],
            AssetClass.COMMODITIES: [
                DataSource.YAHOO_FINANCE,
                DataSource.INVESTING_COM,
                DataSource.CME_GROUP,
                DataSource.TRADING_CHARTS,
                DataSource.BARCHART
            ],
            AssetClass.CRYPTO: [
                DataSource.YAHOO_FINANCE,
                DataSource.ALPHA_VANTAGE,
                DataSource.FINNHUB,
                DataSource.POLYGON
            ]
        }
        
        # Initialize Alpha Vantage clients if API key is provided
        if self.alpha_vantage_api_key:
            self.av_timeseries = TimeSeries(key=self.alpha_vantage_api_key, output_format='pandas')
            self.av_fundamentals = FundamentalData(key=self.alpha_vantage_api_key, output_format='pandas')
            self.av_crypto = CryptoCurrencies(key=self.alpha_vantage_api_key, output_format='pandas')
            self.av_forex = ForeignExchange(key=self.alpha_vantage_api_key, output_format='pandas')
        
        # Initialize Finnhub client if API key is provided
        if self.finnhub_api_key and FINNHUB_AVAILABLE:
            self.finnhub_client = finnhub.Client(api_key=self.finnhub_api_key)
        
        # Initialize Twelve Data client if API key is provided
        if self.twelve_data_api_key and TWELVE_DATA_AVAILABLE:
            self.td_client = twelvedata.TS(self.twelve_data_api_key)
        
        # Initialize Polygon client if API key is provided
        if self.polygon_api_key and POLYGON_AVAILABLE:
            self.polygon_client = polygon.RESTClient(self.polygon_api_key)
        
        # Initialize Oanda client if API key and account ID are provided
        if self.oanda_api_key and self.oanda_account_id and OANDA_AVAILABLE:
            self.oanda_client = oandapyV20.API(access_token=self.oanda_api_key)
        
        # Dynamic source switching configuration
        self.switching_enabled = True
        self.switching_thresholds = {
            'success_rate': 0.90,  # Switch if success rate drops below 90%
            'response_time': 3.0,  # Switch if response time exceeds 3 seconds
            'consecutive_failures': 3  # Switch after 3 consecutive failures
        }
        self.source_performance = defaultdict(lambda: {
            'success_rate': 1.0,
            'avg_response_time': 0.0,
            'consecutive_failures': 0,
            'total_requests': 0,
            'successful_requests': 0
        })
        self.preferred_sources = {}  # Asset class -> preferred source mapping
    
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
        
        # Record start time for performance monitoring
        start_time = time.time()
        
        # If specific source is requested, try only that source
        if source:
            response = self._fetch_from_source(source, request)
            response_time = time.time() - start_time
            self.health_monitor.record_health_check(source, response.success, response_time)
            self._update_source_performance(source, response.success, response_time)
            return response
        
        # Otherwise, try sources in priority order based on asset class
        # Check if we have a preferred source for this asset class
        if asset_class in self.preferred_sources:
            preferred_source = self.preferred_sources[asset_class]
            # Check if preferred source is healthy
            health = self.health_monitor.get_health_status(preferred_source)
            if self._is_source_healthy(preferred_source, health):
                try:
                    if not self._has_required_credentials(preferred_source):
                        logger.debug("Skipping preferred source due to missing credentials", 
                                   source=preferred_source.value)
                    elif not self.rate_limit_manager.can_make_request(preferred_source):
                        logger.warning("Rate limit exceeded for preferred source", 
                                     source=preferred_source.value)
                    else:
                        response = self._fetch_from_source(preferred_source, request)
                        response_time = time.time() - start_time
                        self.health_monitor.record_health_check(preferred_source, response.success, response_time)
                        self._update_source_performance(preferred_source, response.success, response_time)
                        
                        if response.success and not response.data.empty:
                            logger.info("Data successfully retrieved from preferred source", 
                                      source=preferred_source.value, 
                                      ticker=ticker,
                                      rows=len(response.data))
                            return response
                        else:
                            # Preferred source failed, remove it as preferred
                            logger.warning("Preferred source failed, removing from preferred list", 
                                         source=preferred_source.value)
                            del self.preferred_sources[asset_class]
                except Exception as e:
                    logger.warning("Preferred source failed with exception, removing from preferred list", 
                                 source=preferred_source.value, 
                                 error=str(e))
                    del self.preferred_sources[asset_class]
        
        # Use standard priority order
        source_priority = self.source_priority_by_asset.get(asset_class, self.source_priority_by_asset[AssetClass.STOCK])
        
        last_error = None
        for data_source in source_priority:
            try:
                # Check if we have the necessary API keys for this source
                if not self._has_required_credentials(data_source):
                    logger.debug("Skipping source due to missing credentials", 
                               source=data_source.value)
                    continue
                
                if not self.rate_limit_manager.can_make_request(data_source):
                    logger.warning("Rate limit exceeded, skipping source", 
                                 source=data_source.value)
                    continue
                
                response = self._fetch_from_source(data_source, request)
                response_time = time.time() - start_time
                self.health_monitor.record_health_check(data_source, response.success, response_time)
                self._update_source_performance(data_source, response.success, response_time)
                
                if response.success and not response.data.empty:
                    # If this source is performing well, consider making it preferred for this asset class
                    self._consider_preferred_source(asset_class, data_source)
                    
                    logger.info("Data successfully retrieved", 
                              source=data_source.value, 
                              ticker=ticker,
                              rows=len(response.data))
                    return response
                
            except NotImplementedError:
                # Skip sources that aren't implemented yet
                logger.debug("Source not implemented, skipping", 
                           source=data_source.value)
                continue
            except Exception as e:
                last_error = str(e)
                logger.warning("Data source failed, trying next", 
                             source=data_source.value, 
                             error=str(e))
                continue
        
        # All sources failed
        logger.error("All data sources failed", 
                    ticker=ticker, 
                    asset_class=asset_class.value,
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
    
    def _has_required_credentials(self, source: DataSource) -> bool:
        """Check if we have the required credentials for a data source"""
        credential_requirements = {
            DataSource.ALPHA_VANTAGE: self.alpha_vantage_api_key,
            DataSource.FINNHUB: self.finnhub_api_key,
            DataSource.TWELVE_DATA: self.twelve_data_api_key,
            DataSource.POLYGON: self.polygon_api_key,
            DataSource.OANDA: self.oanda_api_key and self.oanda_account_id
        }
        
        # If source doesn't require credentials, return True
        if source not in credential_requirements:
            return True
        
        # Check if we have the required credentials
        return bool(credential_requirements[source])
    
    def _fetch_from_source(self, source: DataSource, request: DataRequest) -> DataResponse:
        """Fetch data from a specific source"""
        
        self.rate_limit_manager.record_request(source)
        start_time = time.time()
        
        try:
            response = None
            if source == DataSource.YAHOO_FINANCE:
                response = self._fetch_yahoo_finance(request)
            elif source == DataSource.ALPHA_VANTAGE:
                response = self._fetch_alpha_vantage(request)
            elif source == DataSource.FINNHUB:
                response = self._fetch_finnhub(request)
            elif source == DataSource.INVESTING_COM:
                response = self._fetch_investing_com(request)
            elif source == DataSource.CME_GROUP:
                response = self._fetch_cme_group(request)
            elif source == DataSource.TWELVE_DATA:
                response = self._fetch_twelve_data(request)
            elif source == DataSource.POLYGON:
                response = self._fetch_polygon(request)
            elif source == DataSource.BARCHART:
                response = self._fetch_barchart(request)
            elif source == DataSource.SPIDERROCK:
                response = self._fetch_spiderrock(request)
            elif source == DataSource.TRADING_CHARTS:
                response = self._fetch_trading_charts(request)
            elif source == DataSource.OANDA:
                response = self._fetch_oanda(request)
            else:
                raise ValueError(f"Unsupported data source: {source}")
            
            # Record health check
            response_time = time.time() - start_time
            self.health_monitor.record_health_check(source, response.success, response_time)
            
            return response
                
        except Exception as e:
            # Record failed health check
            response_time = time.time() - start_time
            self.health_monitor.record_health_check(source, False, response_time)
            
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
        """Fetch data from Finnhub"""
        if not self.finnhub_api_key or not FINNHUB_AVAILABLE:
            raise ValueError("Finnhub API key not provided or library not available")
        
        try:
            # Get current timestamp for period calculation
            import datetime
            to_timestamp = int(datetime.datetime.now().timestamp())
            
            # Calculate from timestamp based on period
            period_days = {
                '1d': 1, '5d': 5, '1mo': 30, '3mo': 90, 
                '6mo': 180, '1y': 365, '2y': 730, '5y': 1825, '10y': 3650
            }
            days = period_days.get(request.period, 365)
            from_timestamp = to_timestamp - (days * 24 * 60 * 60)
            
            # Fetch data from Finnhub
            finnhub_data = self.finnhub_client.stock_candles(
                request.ticker, 
                request.interval, 
                from_timestamp, 
                to_timestamp
            )
            
            if finnhub_data['s'] == 'no_data':
                raise ValueError("No data returned from Finnhub")
            
            # Convert to DataFrame
            data = pd.DataFrame({
                'timestamp': finnhub_data['t'],
                'open': finnhub_data['o'],
                'high': finnhub_data['h'],
                'low': finnhub_data['l'],
                'close': finnhub_data['c'],
                'volume': finnhub_data['v']
            })
            
            # Convert timestamp to datetime
            data['timestamp'] = pd.to_datetime(data['timestamp'], unit='s')
            data.set_index('timestamp', inplace=True)
            
            if data.empty:
                raise ValueError("No data returned from Finnhub")
            
            return DataResponse(
                data=data,
                source=DataSource.FINNHUB,
                ticker=request.ticker,
                asset_class=request.asset_class,
                metadata={"from_timestamp": from_timestamp, "to_timestamp": to_timestamp},
                timestamp=time.time(),
                success=True
            )
            
        except Exception as e:
            raise Exception(f"Finnhub error: {str(e)}")
    
    def _fetch_twelve_data(self, request: DataRequest) -> DataResponse:
        """Fetch data from Twelve Data"""
        if not self.twelve_data_api_key or not TWELVE_DATA_AVAILABLE:
            raise ValueError("Twelve Data API key not provided or library not available")
        
        try:
            # Create Twelve Data time series object
            ts = self.td_client.time_series(
                symbol=request.ticker,
                interval=request.interval,
                outputsize=5000,  # Maximum output size
                timezone="UTC"
            )
            
            # Fetch data
            td_data = ts.as_pandas()
            
            if td_data.empty:
                raise ValueError("No data returned from Twelve Data")
            
            # Convert index to datetime if it's not already
            if not isinstance(td_data.index, pd.DatetimeIndex):
                td_data.index = pd.to_datetime(td_data.index)
            
            # Standardize column names
            td_data.columns = [col.lower().replace(' ', '_') for col in td_data.columns]
            
            return DataResponse(
                data=td_data,
                source=DataSource.TWELVE_DATA,
                ticker=request.ticker,
                asset_class=request.asset_class,
                metadata={"interval": request.interval, "outputsize": 5000},
                timestamp=time.time(),
                success=True
            )
            
        except Exception as e:
            raise Exception(f"Twelve Data error: {str(e)}")
    
    def _fetch_polygon(self, request: DataRequest) -> DataResponse:
        """Fetch data from Polygon"""
        if not self.polygon_api_key or not POLYGON_AVAILABLE:
            raise ValueError("Polygon API key not provided or library not available")
        
        try:
            import datetime
            from datetime import timedelta
            
            # Calculate date range
            end_date = datetime.datetime.now()
            period_days = {
                '1d': 1, '5d': 5, '1mo': 30, '3mo': 90, 
                '6mo': 180, '1y': 365, '2y': 730, '5y': 1825, '10y': 3650
            }
            days = period_days.get(request.period, 365)
            start_date = end_date - timedelta(days=days)
            
            # Fetch data from Polygon
            aggs = []
            for agg in self.polygon_client.list_aggs(
                ticker=request.ticker,
                multiplier=1,
                timespan=request.interval,
                from_=start_date.strftime('%Y-%m-%d'),
                to=end_date.strftime('%Y-%m-%d'),
                limit=50000
            ):
                aggs.append(agg)
            
            if not aggs:
                raise ValueError("No data returned from Polygon")
            
            # Convert to DataFrame
            data = pd.DataFrame([{
                'timestamp': agg.timestamp,
                'open': agg.open,
                'high': agg.high,
                'low': agg.low,
                'close': agg.close,
                'volume': agg.volume,
                'vwap': agg.vwap,
                'transactions': agg.transactions
            } for agg in aggs])
            
            # Convert timestamp to datetime
            data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
            data.set_index('timestamp', inplace=True)
            
            if data.empty:
                raise ValueError("No data returned from Polygon")
            
            return DataResponse(
                data=data,
                source=DataSource.POLYGON,
                ticker=request.ticker,
                asset_class=request.asset_class,
                metadata={"start_date": start_date.strftime('%Y-%m-%d'), 
                         "end_date": end_date.strftime('%Y-%m-%d')},
                timestamp=time.time(),
                success=True
            )
            
        except Exception as e:
            raise Exception(f"Polygon error: {str(e)}")
    
    def _fetch_oanda(self, request: DataRequest) -> DataResponse:
        """Fetch data from Oanda"""
        if not self.oanda_api_key or not self.oanda_account_id or not OANDA_AVAILABLE:
            raise ValueError("Oanda API key or account ID not provided or library not available")
        
        try:
            import datetime
            from datetime import timedelta
            from oandapyV20 import endpoints
            from oandapyV20.contrib.requests import InstrumentsCandlesFactory
            
            # Calculate date range
            end_date = datetime.datetime.now()
            period_days = {
                '1d': 1, '5d': 5, '1mo': 30, '3mo': 90, 
                '6mo': 180, '1y': 365, '2y': 730, '5y': 1825, '10y': 3650
            }
            days = period_days.get(request.period, 365)
            start_date = end_date - timedelta(days=days)
            
            # Prepare parameters
            params = {
                "from": start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "to": end_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "granularity": request.interval.upper(),  # Oanda uses different format
                "price": "MBA"  # Midpoint, Bid, Ask
            }
            
            # Create request
            request_obj = endpoints.instruments.InstrumentsCandles(
                instrument=request.ticker,
                params=params
            )
            
            # Fetch data
            response = self.oanda_client.request(request_obj)
            
            if not response or 'candles' not in response:
                raise ValueError("No data returned from Oanda")
            
            # Convert to DataFrame
            candles = response['candles']
            data = pd.DataFrame([{
                'timestamp': candle['time'],
                'open': float(candle['mid']['o']),
                'high': float(candle['mid']['h']),
                'low': float(candle['mid']['l']),
                'close': float(candle['mid']['c']),
                'volume': candle['volume'] if 'volume' in candle else 0
            } for candle in candles if candle['complete']])
            
            # Convert timestamp to datetime
            data['timestamp'] = pd.to_datetime(data['timestamp'])
            data.set_index('timestamp', inplace=True)
            
            if data.empty:
                raise ValueError("No data returned from Oanda")
            
            return DataResponse(
                data=data,
                source=DataSource.OANDA,
                ticker=request.ticker,
                asset_class=request.asset_class,
                metadata={"start_date": start_date.strftime('%Y-%m-%d'), 
                         "end_date": end_date.strftime('%Y-%m-%d'),
                         "granularity": request.interval.upper()},
                timestamp=time.time(),
                success=True
            )
            
        except Exception as e:
            raise Exception(f"Oanda error: {str(e)}")
    
    def _fetch_investing_com(self, request: DataRequest) -> DataResponse:
        """Fetch data from Investing.com (placeholder implementation)"""
        # TODO: Implement Investing.com integration
        raise NotImplementedError("Investing.com integration not yet implemented")
    
    def _fetch_cme_group(self, request: DataRequest) -> DataResponse:
        """Fetch data from CME Group (placeholder implementation)"""
        # TODO: Implement CME Group integration
        raise NotImplementedError("CME Group integration not yet implemented")
    
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
                start_time = time.time()
                test_response = self._fetch_from_source(
                    source, 
                    DataRequest(ticker="AAPL", asset_class=AssetClass.STOCK, period="1d")
                )
                response_time = time.time() - start_time
                health_status[source.value] = test_response.success
                self.health_monitor.record_health_check(source, test_response.success, response_time)
            except Exception as e:
                response_time = time.time() - start_time
                health_status[source.value] = False
                self.health_monitor.record_health_check(source, False, response_time)
        
        return health_status
    
    def get_detailed_health_report(self) -> Dict[str, Any]:
        """Get a detailed health report for all data sources"""
        return self.health_monitor.get_overall_health()
    
    def should_send_alert(self, source: DataSource) -> bool:
        """Determine if an alert should be sent for a specific data source"""
        return self.health_monitor.should_alert(source)
    
    def _update_source_performance(self, source: DataSource, success: bool, response_time: float):
        """Update performance metrics for a data source"""
        if not self.switching_enabled:
            return
            
        performance = self.source_performance[source]
        performance['total_requests'] += 1
        performance['successful_requests'] += 1 if success else 0
        
        # Update success rate
        if performance['total_requests'] > 0:
            performance['success_rate'] = performance['successful_requests'] / performance['total_requests']
        
        # Update average response time
        if performance['total_requests'] == 1:
            performance['avg_response_time'] = response_time
        else:
            # Exponential moving average
            alpha = 0.1
            performance['avg_response_time'] = (
                alpha * response_time + (1 - alpha) * performance['avg_response_time']
            )
        
        # Update consecutive failures
        if success:
            performance['consecutive_failures'] = 0
        else:
            performance['consecutive_failures'] += 1

    def _is_source_healthy(self, source: DataSource, health_status: Dict[str, Any]) -> bool:
        """Check if a source is healthy based on thresholds"""
        if not self.switching_enabled:
            return True
            
        # Check health status from monitor
        status = health_status.get('status', 'unknown')
        if status == 'unhealthy':
            return False
        if status == 'degraded':
            # Even degraded sources might be acceptable if within thresholds
            pass
        
        # Check performance metrics
        performance = self.source_performance[source]
        
        # Check success rate
        if performance['success_rate'] < self.switching_thresholds['success_rate']:
            return False
        
        # Check response time
        if performance['avg_response_time'] > self.switching_thresholds['response_time']:
            return False
        
        # Check consecutive failures
        if performance['consecutive_failures'] >= self.switching_thresholds['consecutive_failures']:
            return False
        
        return True

    def _consider_preferred_source(self, asset_class: AssetClass, source: DataSource):
        """Consider making a source preferred for an asset class based on performance"""
        if not self.switching_enabled:
            return
            
        performance = self.source_performance[source]
        
        # Make source preferred if it's performing well
        # Success rate > 95% and response time < 1 second
        if (performance['success_rate'] > 0.95 and 
            performance['avg_response_time'] < 1.0):
            self.preferred_sources[asset_class] = source
            logger.info("Source set as preferred for asset class", 
                       source=source.value,
                       asset_class=asset_class.value)

    def set_switching_thresholds(self, success_rate: float = 0.90, 
                               response_time: float = 3.0, 
                               consecutive_failures: int = 3):
        """Set thresholds for automatic source switching"""
        self.switching_thresholds = {
            'success_rate': success_rate,
            'response_time': response_time,
            'consecutive_failures': consecutive_failures
        }
        logger.info("Updated switching thresholds", thresholds=self.switching_thresholds)

    def enable_switching(self, enabled: bool = True):
        """Enable or disable automatic source switching"""
        self.switching_enabled = enabled
        logger.info("Automatic source switching", status="enabled" if enabled else "disabled")

    def get_source_performance(self, source: Optional[DataSource] = None) -> Dict[DataSource, Dict]:
        """Get performance metrics for data sources"""
        if source:
            return {source: self.source_performance[source].copy()}
        return {src: metrics.copy() for src, metrics in self.source_performance.items()}

    def reset_source_performance(self, source: Optional[DataSource] = None):
        """Reset performance metrics for a source or all sources"""
        if source:
            self.source_performance[source] = {
                'success_rate': 1.0,
                'avg_response_time': 0.0,
                'consecutive_failures': 0,
                'total_requests': 0,
                'successful_requests': 0
            }
        else:
            self.source_performance.clear()
            for source_enum in DataSource:
                self.source_performance[source_enum] = {
                    'success_rate': 1.0,
                    'avg_response_time': 0.0,
                    'consecutive_failures': 0,
                    'total_requests': 0,
                    'successful_requests': 0
                }
        logger.info("Reset source performance metrics", source=source.value if source else "all")


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