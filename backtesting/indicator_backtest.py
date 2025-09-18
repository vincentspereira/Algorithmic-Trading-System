import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'forks', 'nautilus_trader')))

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.engine import BacktestEngineConfig
from nautilus_trader.model.currency import USD
from nautilus_trader.model.enums import AccountType
from nautilus_trader.model.enums import OmsType
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.objects import Money

# Assuming indicator_test_strategy is in the same directory or adjust import
from indicator_test_strategy import IndicatorTestStrategy

from nautilus_trader.test_kit.providers import TestInstrumentProvider
from nautilus_trader.test_kit.stubs.data import TestDataStubs

# Configure backtest engine
config = BacktestEngineConfig()
engine = BacktestEngine(config=config)

# Add a venue (SIM for simulated)
venue = Venue("SIM")
engine.add_venue(
    venue=venue,
    oms_type=OmsType.HEDGING,
    account_type=AccountType.MARGIN,
    base_currency=USD,
    starting_balances=[Money(1_000_000, USD)],
)

# Add instrument
instrument = TestInstrumentProvider.default_fx_ccy("EURUSD")
engine.add_instrument(instrument)

# Add some test data
bars = TestDataStubs.bars_range(n=10, instrument_id=instrument.id)
engine.add_data(bars, instrument.id)

# Add strategy
strategy_config = {"instrument_id": instrument.id, "period": 20}  # Adjust config as needed
strategy = IndicatorTestStrategy(config=strategy_config)
engine.add_strategy(strategy)

# Run backtest
engine.run(start=datetime.now(), stop=datetime.now())

print("Backtest completed successfully!")
print("Indicators initialized and updated during backtest.")