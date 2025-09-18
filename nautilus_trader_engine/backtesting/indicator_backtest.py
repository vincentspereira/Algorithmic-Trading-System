import os
import shutil
from decimal import Decimal
import pandas as pd
import yfinance as yf

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.engine import BacktestEngineConfig
from nautilus_trader.model.enums import AccountType
from nautilus_trader.model.enums import OmsType
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.objects import Money
from nautilus_trader.persistence.catalog import ParquetDataCatalog
from nautilus_trader.test_kit.providers import TestInstrumentProvider
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import Symbol
from nautilus_trader.model.data import BarSpecification, BarType, Bar
from nautilus_trader.model.enums import AggregationSource, BarAggregation, PriceType
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.model.currencies import USD
from nautilus_trader.core.datetime import dt_to_unix_nanos, unix_nanos_to_dt
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'forks', 'tier1', 'nautilus_trader')))

from nautilus_trader_engine.strategies.indicator_test_strategy import IndicatorTestStrategy

CATALOG_PATH = os.path.join(os.getcwd(), "catalog")
if os.path.exists(CATALOG_PATH):
    shutil.rmtree(CATALOG_PATH)
os.mkdir(CATALOG_PATH)

# Download data using yfinance
symbol = "AAPL"
data = yf.download(symbol, start="2023-01-01", end="2023-12-31", interval="1d")

# Create instrument
venue = Venue("SIM")  # Simulated venue
instrument_id = InstrumentId(Symbol(symbol), venue)
instrument = TestInstrumentProvider.equity(instrument_id, price_precision=2, size_precision=0)

# Convert to Nautilus bars
bars = []
for idx, row in data.iterrows():
    ts = pd.to_datetime(idx).value // 1_000_000_000  # to unix ns
    bar_type = BarType(instrument_id, BarSpecification(1, BarAggregation.DAY, PriceType.CLOSE))
    bar = Bar(
        bar_type=bar_type,
        open=Price(row["Open"], 2),
        high=Price(row["High"], 2),
        low=Price(row["Low"], 2),
        close=Price(row["Close"], 2),
        volume=Quantity(row["Volume"], 0),
        ts_event=ts,
        ts_init=ts,
    )
    bars.append(bar)

# Write to catalog
catalog = ParquetDataCatalog(CATALOG_PATH)
catalog.write_data(bars)

# Set up backtest
config = BacktestEngineConfig(
    trader_id="TESTER-001",
)
engine = BacktestEngine(config=config)

# Add venue
engine.add_venue(
    venue=venue,
    oms_type=OmsType.HEDGING,
    account_type=AccountType.MARGIN,
    base_currency=None,
    starting_balances=[Money(1_000_000, USD)],
)

# Add instrument
engine.add_instrument(instrument)

# Add data from catalog
start = dt_to_unix_nanos(pd.Timestamp("2023-01-01"))
end = dt_to_unix_nanos(pd.Timestamp("2023-12-31"))
engine.add_data(catalog.bars(bar_type=bar_type, from_datetime=unix_nanos_to_dt(start), to_datetime=unix_nanos_to_dt(end)))

# Add strategy
strategy = IndicatorTestStrategy()
engine.add_strategy(strategy)

# Run backtest
engine.run()

# Analyze results
print(engine.trader.generate_account_report(venue))
print(engine.analyzer.to_dict())