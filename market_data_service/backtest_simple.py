import asyncio
import os
from datetime import datetime

import pandas as pd
from decimal import Decimal
from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.backtest.config import BacktestVenueConfig, BacktestDataConfig, BacktestRunConfig, BacktestEngineConfig
from nautilus_trader.config import ImportableStrategyConfig
from nautilus_trader.model.data import BarType, BarSpecification, Bar
from nautilus_trader.model.enums import AggregationSource, BarAggregation, PriceType
from nautilus_trader.persistence.catalog import ParquetDataCatalog
from nautilus_trader.model.identifiers import InstrumentId, Venue, Symbol
from nautilus_trader.model.instruments.equity import Equity
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.model.currencies import USD

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from market_data_service.data_fetcher import MultiSourceFetcher
from shared.utils.logging_utils import get_logger

logger = get_logger(__name__)

CATALOG_PATH = os.path.join(os.getcwd(), "catalog")

async def run_simple_backtest():
    # Fetch data
    fetcher = MultiSourceFetcher()
    await fetcher.start()
    try:
        symbol = "AAPL"
        asset_class = "stocks_etfs"
        start = "2023-01-01"
        end = "2023-12-31"
        interval = "1d"
        df = await fetcher.fetch_historical_bars(asset_class, symbol, start, end, interval)
    finally:
        await fetcher.stop()

    # Write to catalog
    catalog = ParquetDataCatalog(CATALOG_PATH)
    
    # Create instrument
    instrument_id = InstrumentId.from_str(f"{symbol}.XNAS")
    instrument = Equity(
        instrument_id=instrument_id,
        raw_symbol=Symbol(symbol),
        currency=USD,
        price_precision=2,
        price_increment=Price(0.01, precision=2),
        lot_size=Quantity(1, precision=0),
        isin="US0378331005",
        ts_event=0,
        ts_init=0,
    )
    catalog.write_data([instrument])

    # Process bars
    bar_spec = BarSpecification(1, BarAggregation.DAY, PriceType.LAST)
    bar_type = BarType(instrument_id, bar_spec, AggregationSource.EXTERNAL)
    
    bars = []
    for _, row in df.iterrows():
        bar = Bar(
            bar_type=bar_type,
            open=Price(row['Open'], 2),
            high=Price(row['High'], 2),
            low=Price(row['Low'], 2),
            close=Price(row['Close'], 2),
            volume=Quantity(row['Volume'], 0),
            ts_event=pd.Timestamp(row.name).timestamp() * 1_000_000_000,  # to ns
            ts_init=pd.Timestamp(row.name).timestamp() * 1_000_000_000,
        )
        bars.append(bar)
    
    catalog.write_data(bars)

    # Set up backtest
    venue_configs = [
        BacktestVenueConfig(
            name="XNAS",
            oms_type="HEDGING",
            account_type="MARGIN",
            base_currency="USD",
            starting_balances=["1_000_000 USD"],
        )
    ]
    data_configs = [BacktestDataConfig(
        catalog_path=CATALOG_PATH,
        data_cls=Bar,
        instrument_id=instrument_id.value,
        start_time=datetime.fromisoformat(start).timestamp(),
        end_time=datetime.fromisoformat(end).timestamp(),
    )]
    
    strategies = [
        ImportableStrategyConfig(
            strategy_path="nautilus_trader.examples.strategies.ema_cross:EMACross",
            config_path="nautilus_trader.examples.strategies.ema_cross:EMACrossConfig",
            config=dict(
                instrument_id=instrument.id.value,
                bar_type=str(bar_type),
                fast_ema_period=10,
                slow_ema_period=20,
                trade_size=Decimal(100),
            ),
        ),
    ]

    engine_config = BacktestEngineConfig(strategies=strategies)
    
    run_config = BacktestRunConfig(
        engine=engine_config,
        venues=venue_configs,
        data=data_configs,
    )
    
    # Run backtest
    node = BacktestNode(configs=[run_config])
    results = node.run()
    
    logger.info(f"Backtest results: {results}")
    return results

if __name__ == "__main__":
    asyncio.run(run_simple_backtest())