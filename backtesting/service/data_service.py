"""
Data service for fetching and managing historical market data.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import asyncio
import logging

import aiohttp
import pandas as pd
from pydantic import BaseModel
import clickhouse_driver
from kafka import KafkaConsumer, KafkaProducer
import redis

# Models
class MarketData(BaseModel):
    """Market data model"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    
class DataRequest(BaseModel):
    """Data request model"""
    symbol: str
    start_date: datetime
    end_date: datetime
    timeframe: str

class DataService:
    """Service for managing market data"""
    
    def __init__(
        self,
        clickhouse_host: str = 'localhost',
        redis_host: str = 'localhost',
        kafka_servers: List[str] = None
    ):
        self.clickhouse = clickhouse_driver.Client(
            host=clickhouse_host,
            settings={'use_numpy': True}
        )
        
        self.redis = redis.Redis(
            host=redis_host,
            port=6379,
            decode_responses=True
        )
        
        self.kafka_consumer = KafkaConsumer(
            'data_requests',
            bootstrap_servers=kafka_servers or ['localhost:9092'],
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=kafka_servers or ['localhost:9092'],
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        
    async def fetch_data(
        self,
        request: DataRequest
    ) -> Optional[pd.DataFrame]:
        """Fetch market data"""
        try:
            # Check cache first
            cache_key = (
                f"market_data:{request.symbol}:"
                f"{request.timeframe}:{request.start_date}:"
                f"{request.end_date}"
            )
            
            cached_data = self.redis.get(cache_key)
            if cached_data:
                return pd.read_json(cached_data)
                
            # Fetch from database
            query = """
                SELECT 
                    timestamp,
                    open,
                    high,
                    low,
                    close,
                    volume
                FROM market_data
                WHERE 
                    symbol = %(symbol)s
                    AND timestamp BETWEEN %(start)s AND %(end)s
                    AND timeframe = %(timeframe)s
                ORDER BY timestamp
            """
            
            data = self.clickhouse.query_dataframe(
                query,
                {
                    'symbol': request.symbol,
                    'start': request.start_date,
                    'end': request.end_date,
                    'timeframe': request.timeframe
                }
            )
            
            if not data.empty:
                # Cache the result
                self.redis.set(
                    cache_key,
                    data.to_json(),
                    ex=3600  # 1 hour expiry
                )
                return data
                
            # If not in database, fetch from external API
            return await self._fetch_from_external(request)
            
        except Exception as e:
            logging.error(f"Error fetching data: {str(e)}")
            return None
            
    async def _fetch_from_external(
        self,
        request: DataRequest
    ) -> Optional[pd.DataFrame]:
        """Fetch data from external API"""
        # TODO: Implement actual API calls
        # This is a placeholder that generates sample data
        dates = pd.date_range(
            request.start_date,
            request.end_date,
            freq=request.timeframe
        )
        
        data = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.normal(100, 10, len(dates)),
            'high': np.random.normal(105, 10, len(dates)),
            'low': np.random.normal(95, 10, len(dates)),
            'close': np.random.normal(100, 10, len(dates)),
            'volume': np.random.normal(1000000, 100000, len(dates))
        })
        
        # Store in database
        self.store_data(request.symbol, request.timeframe, data)
        
        return data
        
    def store_data(
        self,
        symbol: str,
        timeframe: str,
        data: pd.DataFrame
    ) -> bool:
        """Store market data in ClickHouse"""
        try:
            self.clickhouse.execute(
                """
                INSERT INTO market_data (
                    symbol,
                    timeframe,
                    timestamp,
                    open,
                    high,
                    low,
                    close,
                    volume
                ) VALUES
                """,
                [{
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'timestamp': row.timestamp,
                    'open': row.open,
                    'high': row.high,
                    'low': row.low,
                    'close': row.close,
                    'volume': row.volume
                } for _, row in data.iterrows()]
            )
            return True
            
        except Exception as e:
            logging.error(f"Error storing data: {str(e)}")
            return False
            
    async def start(self):
        """Start the data service"""
        try:
            for message in self.kafka_consumer:
                request = DataRequest(**message.value)
                data = await self.fetch_data(request)
                
                if data is not None:
                    # Publish data ready event
                    self.kafka_producer.send(
                        'data_ready',
                        {
                            'request_id': message.value.get('request_id'),
                            'symbol': request.symbol,
                            'timeframe': request.timeframe,
                            'data': data.to_dict(orient='records')
                        }
                    )
                else:
                    # Publish error event
                    self.kafka_producer.send(
                        'data_error',
                        {
                            'request_id': message.value.get('request_id'),
                            'error': 'Failed to fetch data'
                        }
                    )
                    
        except KeyboardInterrupt:
            self.kafka_consumer.close()
            self.kafka_producer.close()
            
if __name__ == '__main__':
    import numpy as np
    import json
    
    logging.basicConfig(level=logging.INFO)
    
    service = DataService()
    asyncio.run(service.start())
