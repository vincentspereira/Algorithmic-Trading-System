
import logging

try:
    from clickhouse_driver import Client as ClickHouseClient
    from clickhouse_driver.errors import Error as ClickHouseError
    CLICKHOUSE_AVAILABLE = True
except ImportError:
    ClickHouseClient = None
    ClickHouseError = None
    CLICKHOUSE_AVAILABLE = False

from database.app.core.config import db_settings

logger = logging.getLogger(__name__)

class ClickHouseManager:
    def __init__(self):
        self.client = None
        self.is_healthy = False

    async def initialize(self):
        try:
            if not CLICKHOUSE_AVAILABLE:
                logger.warning("ClickHouse driver not available")
                return

            self.client = ClickHouseClient(
                host=db_settings.CLICKHOUSE_HOST,
                port=db_settings.CLICKHOUSE_PORT,
                user=db_settings.CLICKHOUSE_USER,
                password=db_settings.CLICKHOUSE_PASSWORD,
                database=db_settings.CLICKHOUSE_DATABASE,
                connect_timeout=db_settings.CONNECTION_TIMEOUT,
                send_receive_timeout=db_settings.QUERY_TIMEOUT
            )

            result = self.client.execute("SELECT 1")
            if result:
                self.is_healthy = True
                logger.info("ClickHouse connection established")

        except Exception as e:
            logger.error(f"Failed to initialize ClickHouse: {e}")
            self.is_healthy = False

    async def create_tables(self):
        if not self.client:
            logger.warning("ClickHouse not available, skipping table creation")
            return

        # Market data table
        market_data_ddl = """
        CREATE TABLE IF NOT EXISTS market_data (
            timestamp DateTime64(3),
            symbol String,
            open Float64,
            high Float64,
            low Float64,
            close Float64,
            volume UInt64,
            interval String,
            source String
        ) ENGINE = MergeTree()
        ORDER BY (symbol, timestamp)
        PARTITION BY toYYYYMM(timestamp)
        """

        # Tick data table
        tick_data_ddl = """
        CREATE TABLE IF NOT EXISTS tick_data (
            timestamp DateTime64(6),
            symbol String,
            price Float64,
            size UInt32,
            bid Float64,
            ask Float64,
            bid_size UInt32,
            ask_size UInt32,
            exchange String
        ) ENGINE = MergeTree()
        ORDER BY (symbol, timestamp)
        PARTITION BY toYYYYMMDD(timestamp)
        """

        # Indicator data table
        indicator_data_ddl = """
        CREATE TABLE IF NOT EXISTS indicator_data (
            timestamp DateTime64(3),
            symbol String,
            indicator_name String,
            value Float64,
            signal String,
            strength Float64,
            metadata String
        ) ENGINE = MergeTree()
        ORDER BY (symbol, indicator_name, timestamp)
        PARTITION BY toYYYYMM(timestamp)
        """

        try:
            self.client.execute(market_data_ddl)
            self.client.execute(tick_data_ddl)
            self.client.execute(indicator_data_ddl)
            logger.info("ClickHouse tables created")
        except Exception as e:
            logger.error(f"Failed to create ClickHouse tables: {e}")

    async def insert_market_data(self, data: list):
        if not self.client:
            return

        try:
            self.client.execute(
                "INSERT INTO market_data VALUES",
                data
            )
        except Exception as e:
            logger.error(f"Failed to insert market data: {e}")

    async def query_market_data(self, symbol: str, start_time: datetime, end_time: datetime) -> list:
        if not self.client:
            return []

        query = """
        SELECT timestamp, open, high, low, close, volume
        FROM market_data
        WHERE symbol = %(symbol)s
        AND timestamp >= %(start_time)s
        AND timestamp <= %(end_time)s
        ORDER BY timestamp
        """

        try:
            result = self.client.execute(query, {
                'symbol': symbol,
                'start_time': start_time,
                'end_time': end_time
            })
            return [dict(zip(['timestamp', 'open', 'high', 'low', 'close', 'volume'], row)) for row in result]
        except Exception as e:
            logger.error(f"Failed to query market data: {e}")
            return []

    async def cleanup(self):
        if self.client:
            self.client.disconnect()
