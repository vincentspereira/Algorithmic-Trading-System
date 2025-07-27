# nautilus_trader_engine/rl/training/data_preprocessor.py

"""
Data preprocessing for RL trading models.

This module provides functions to clean, format, and prepare historical market
data for use in the RL training pipeline.
"""

import pandas as pd
from nautilus_trader.model.data import Bar, Quote, Trade

def bars_to_dataframe(bars: list[Bar]) -> pd.DataFrame:
    """
    Converts a list of Nautilus Bar objects to a pandas DataFrame.

    Args:
        bars (list[Bar]): A list of Bar objects.

    Returns:
        A pandas DataFrame with columns for ohlcv data.
    """
    records = [
        {
            "timestamp": bar.ts_event,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
        }
        for bar in bars
    ]
    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ns")
    df.set_index("timestamp", inplace=True)
    return df

def preprocess_data(
    df: pd.DataFrame,
    resample_period: str = "1H",
    interpolate: bool = True,
    drop_na: bool = True,
) -> pd.DataFrame:
    """
    Preprocesses the market data by resampling, interpolating, and handling
    missing values.

    Args:
        df (pd.DataFrame): The input DataFrame of market data.
        resample_period (str): The time period to resample the data to (e.g., '1H', '4H', '1D').
        interpolate (bool): Whether to interpolate missing values.
        drop_na (bool): Whether to drop any remaining NaN values.

    Returns:
        The preprocessed DataFrame.
    """
    # Ensure DataFrame has a datetime index
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame must have a DatetimeIndex.")

    # Resample to the desired frequency
    resampled_df = df.resample(resample_period).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    })

    # Handle missing values
    if interpolate:
        resampled_df.interpolate(method="time", inplace=True)
    
    if drop_na:
        resampled_df.dropna(inplace=True)

    return resampled_df

async def load_historical_data(
    client,
    instrument_id: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """
    Loads historical bar data from a data client.

    Args:
        client: The data client (e.g., from NautilusTrader).
        instrument_id (str): The ID of the instrument.
        start_date (str): The start date in 'YYYY-MM-DD' format.
        end_date (str): The end date in 'YYYY-MM-DD' format.

    Returns:
        A DataFrame containing the historical bar data.
    """
    bars = await client.get_historical_bars(
        instrument_id=instrument_id,
        start_date=start_date,
        end_date=end_date,
    )
    return bars_to_dataframe(bars)