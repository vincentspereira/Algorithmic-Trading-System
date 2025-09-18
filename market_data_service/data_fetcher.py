import asyncio
import logging
import pandas as pd
from datetime import datetime

import yfinance as yf
from alpha_vantage.timeseries import TimeSeries  # Requires pip install alpha-vantage

import sys
import os.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from kafka_service.producer import KafkaEventProducer
from shared.config import settings
from shared.utils.logging_utils import get_logger
import finnhub
from twelvedata import TDClient
from polygon import RESTClient
import os
import oandapyV20
import oandapyV20.endpoints.instruments as instruments
import investpy
from binance.client import Client as BinanceClient
import fxcmpy

logger = get_logger(__name__)

class MultiSourceFetcher:
    def __init__(self):
        self.producer = KafkaEventProducer()
        self.fallback_chains = {
            'stocks_etfs': ['yahoo', 'alpha_vantage', 'finnhub', 'twelve_data', 'polygon', 'investing'],
            'stock_futures_index_futures': ['yahoo', 'investing', 'cme', 'barchart'],
            'stock_options_index_options': ['yahoo', 'cboe', 'spiderrock'],
            'forex': ['yahoo', 'alpha_vantage', 'finnhub', 'oanda'],
            'commodity_futures_options': ['yahoo', 'cme', 'tradingcharts', 'barchart'],
            'crypto': ['alpha_vantage', 'finnhub', 'coinbase', 'binance'],
        }

    async def start(self):
        await self.producer.start()

    async def stop(self):
        await self.producer.stop()

    async def fetch_historical_bars(self, asset_class: str, symbol: str, start: str, end: str, interval: str) -> pd.DataFrame:
        chain = self.fallback_chains.get(asset_class, [])
        for source in chain:
            try:
                data = self._fetch_from_source(source, symbol, start, end, interval)
                data = self._normalize_data(data)
                if not data.empty:
                    await self._publish_to_kafka(data, symbol, asset_class)
                    logger.info(f"Successfully fetched data from {source} for {symbol}")
                    return data
            except Exception as e:
                logger.error(f"Source {source} failed for {symbol}: {str(e)}")
        raise ValueError(f"All sources failed to fetch data for {symbol}")

    def _normalize_data(self, data: pd.DataFrame) -> pd.DataFrame:
        if data.empty:
            return data

        # Standardize column names (case insensitive)
        col_map = {
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume',
            'adj close': 'Adj Close',
        }
        lower_cols = {c.lower(): c for c in data.columns}
        rename_dict = {}
        for std_lower, std in col_map.items():
            if std_lower in lower_cols:
                rename_dict[lower_cols[std_lower]] = std

        data = data.rename(columns=rename_dict)

        # Ensure datetime index
        if not isinstance(data.index, pd.DatetimeIndex):
            if 'Date' in data.columns:
                data.index = pd.to_datetime(data['Date'])
                data = data.drop('Date', axis=1)
            elif 'timestamp' in data.columns:
                data.index = pd.to_datetime(data['timestamp'])
                data = data.drop('timestamp', axis=1)
            # Add more if needed

        # Select standard columns
        standard_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        available_cols = [col for col in standard_cols if col in data.columns]
        if available_cols:
            data = data[available_cols]
        return data

    def _fetch_from_source(self, source: str, symbol: str, start: str, end: str, interval: str) -> pd.DataFrame:
        if source == 'yahoo':
            return yf.download(symbol, start=start, end=end, interval=interval)
        elif source == 'alpha_vantage':
            ts = TimeSeries(key=settings.ALPHA_VANTAGE_KEY, output_format='pandas')
            data, _ = ts.get_daily(symbol=symbol, outputsize='full')
            data.index = pd.to_datetime(data.index)
            data = data[(data.index >= start) & (data.index <= end)]
            data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']  # Standardize columns
            return data
        elif source == 'finnhub':
            client = finnhub.Client(api_key=os.getenv('FINNHUB_API_KEY'))
            start_ts = int(datetime.strptime(start, '%Y-%m-%d').timestamp())
            end_ts = int(datetime.strptime(end, '%Y-%m-%d').timestamp())
            res = client.stock_candles(symbol, self._map_interval_to_finnhub(interval), start_ts, end_ts)
            if res['s'] != 'ok':
                raise ValueError(f"Finnhub fetch failed: {res['s']}")
            df = pd.DataFrame({
                'Open': res['o'],
                'High': res['h'],
                'Low': res['l'],
                'Close': res['c'],
                'Volume': res['v'],
            }, index=pd.to_datetime(res['t'], unit='s'))
            return df
        elif source == 'twelve_data':
            td = TDClient(apikey=os.getenv('TWELVE_DATA_API_KEY'))
            ts = td.time_series(symbol=symbol, interval=interval, start_date=start, end_date=end)
            return ts.as_pandas()
        elif source == 'polygon':
            client = RESTClient(os.getenv('POLYGON_API_KEY'))
            bars = []
            for bar in client.get_aggs(symbol, 1, self._map_interval_to_polygon(interval), start, end):
                bars.append([bar.timestamp, bar.open, bar.high, bar.low, bar.close, bar.volume])
            if not bars:
                return pd.DataFrame()
            df = pd.DataFrame(bars, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
        elif source == 'oanda':
            client = oandapyV20.API(access_token=os.getenv('OANDA_API_KEY'))
            params = {
                'from': start,
                'to': end,
                'granularity': self._map_interval_to_oanda(interval),
                'price': 'M'
            }
            r = instruments.InstrumentsCandles(instrument=symbol, params=params)
            client.request(r)
            if 'candles' not in r:
                return pd.DataFrame()
            data = []
            for candle in r['candles']:
                time = pd.to_datetime(candle['time'])
                mid = candle['mid']
                data.append([time, float(mid['o']), float(mid['h']), float(mid['l']), float(mid['c']), int(candle['volume'])])
            df = pd.DataFrame(data, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df.set_index('timestamp', inplace=True)
            return df
        elif source == 'investing':
            from_date = datetime.strptime(start, '%Y-%m-%d').strftime('%d/%m/%Y')
            to_date = datetime.strptime(end, '%Y-%m-%d').strftime('%d/%m/%Y')
            df = investpy.get_stock_historical_data(stock=symbol, country='united states', from_date=from_date, to_date=to_date)
            return df
        elif source == 'binance':
            client = BinanceClient(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_API_SECRET'))
            klines = client.get_historical_klines(symbol, self._map_interval_to_binance(interval), start, end)
            if not klines:
                return pd.DataFrame()
            df = pd.DataFrame(klines, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
            df = df.astype(float)
            return df
        elif source == 'fxcm':
            con = fxcmpy.fxcmpy(access_token=os.getenv('FXCM_API_KEY'), log_level='error')
            df = con.get_candles(symbol, period=self._map_interval_to_fxcm(interval), start=start, end=end)
            if df.empty:
                con.close()
                return df
            df = df[['bidopen', 'bidhigh', 'bidlow', 'bidclose', 'tickqty']]
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            con.close()
            return df
        return pd.DataFrame()

    async def _publish_to_kafka(self, data: pd.DataFrame, symbol: str, asset_class: str):
        for index, row in data.iterrows():
            message = {
                'timestamp': index.isoformat(),
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'volume': int(row['Volume']) if 'Volume' in row else 0,
                'symbol': symbol,
                'asset_class': asset_class
            }
            await self.producer.send_message('market_data', message)

    def _map_interval_to_finnhub(self, interval: str) -> str:
        mapping = {'1min': '1', '5min': '5', '1h': '60', '1d': 'D', '1w': 'W', '1mo': 'M'}
        return mapping.get(interval, 'D')

    def _map_interval_to_polygon(self, interval: str) -> str:
        mapping = {'1min': 'minute', '1h': 'hour', '1d': 'day', '1w': 'week', '1mo': 'month'}
        return mapping.get(interval, 'day')

    def _map_interval_to_oanda(self, interval: str) -> str:
        mapping = {'1min': 'M1', '5min': 'M5', '1h': 'H1', '1d': 'D', '1w': 'W'}
        return mapping.get(interval, 'D')

    def _map_interval_to_binance(self, interval: str) -> str:
        mapping = {'1min': BinanceClient.KLINE_INTERVAL_1MINUTE, '5min': BinanceClient.KLINE_INTERVAL_5MINUTE, '1h': BinanceClient.KLINE_INTERVAL_1HOUR, '1d': BinanceClient.KLINE_INTERVAL_1DAY, '1w': BinanceClient.KLINE_INTERVAL_1WEEK, '1mo': BinanceClient.KLINE_INTERVAL_1MONTH}
        return mapping.get(interval, BinanceClient.KLINE_INTERVAL_1DAY)

    def _map_interval_to_fxcm(self, interval: str) -> str:
        mapping = {'1min': 'm1', '5min': 'm5', '1h': 'H1', '1d': 'D1', '1w': 'W1'}
        return mapping.get(interval, 'D1')

# Example usage
if __name__ == "__main__":
    async def main():
        fetcher = MultiSourceFetcher()
        await fetcher.start()
        try:
            data = await fetcher.fetch_historical_bars('crypto', 'BTC-USD', '2023-01-01', '2023-12-31', '1d')
            print(data.head())
        finally:
            await fetcher.stop()

    asyncio.run(main())