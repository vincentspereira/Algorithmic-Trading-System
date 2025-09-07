
import pandas as pd
import pytest
from decimal import Decimal

from backtesting.service.executors.nautilus_executor import BacktestExecutor

@pytest.fixture
def executor():
    return BacktestExecutor()

@pytest.fixture
def sample_data():
    return pd.DataFrame({
        'timestamp': pd.to_datetime(['2023-01-01', '2023-01-02']),
        'open': [100.0, 101.0],
        'high': [102.0, 103.0],
        'low': [99.0, 100.0],
        'close': [101.0, 102.0],
        'volume': [1000, 1200]
    })

@pytest.mark.benchmark(group="prepare-data")
def test_benchmark_prepare_data(benchmark, executor, sample_data):
    def f():
        executor.prepare_data(sample_data)

    benchmark(f)
