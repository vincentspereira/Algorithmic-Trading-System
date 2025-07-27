# nautilus_trader_engine/rl/training/feature_extractor.py

"""
Feature extraction for RL trading models.

This module adds technical indicators and other market features to the
preprocessed data, creating the final feature set for training RL agents.
"""

import pandas as pd
import talib as ta

from nautilus_trader_engine.rl.finrl_config import OBSERVATION_SPACE_FEATURES

def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a comprehensive set of technical indicators to the DataFrame.

    Args:
        df (pd.DataFrame): The preprocessed market data.

    Returns:
        A DataFrame with the added technical indicators.
    """
    # Simple Moving Average (SMA)
    df["sma_30"] = ta.SMA(df["close"], timeperiod=30)
    df["sma_50"] = ta.SMA(df["close"], timeperiod=50)

    # Exponential Moving Average (EMA)
    df["ema_14"] = ta.EMA(df["close"], timeperiod=14)
    df["ema_20"] = ta.EMA(df["close"], timeperiod=20)

    # Relative Strength Index (RSI)
    df["rsi_14"] = ta.RSI(df["close"], timeperiod=14)

    # Moving Average Convergence Divergence (MACD)
    macd, macdsignal, _ = ta.MACD(
        df["close"], fastperiod=12, slowperiod=26, signalperiod=9
    )
    df["macd"] = macd
    df["macdsignal"] = macdsignal

    # Bollinger Bands (BBands)
    upper, middle, lower = ta.BBANDS(
        df["close"], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0
    )
    df["bbands_upper"] = upper
    df["bbands_middle"] = middle
    df["bbands_lower"] = lower

    # Average True Range (ATR)
    df["atr_14"] = ta.ATR(df["high"], df["low"], df["close"], timeperiod=14)
    
    # Stochastic Oscillator
    slowk, slowd = ta.STOCH(df['high'], df['low'], df['close'], 
                            fastk_period=14, slowk_period=3, slowd_period=3)
    df['stoch_k'] = slowk
    df['stoch_d'] = slowd

    # Fill any initial NaN values created by indicators
    df.fillna(method="bfill", inplace=True)
    df.dropna(inplace=True)

    return df

def select_features(df: pd.DataFrame, feature_list: list[str]) -> pd.DataFrame:
    """
    Selects the specified features from the DataFrame.

    Args:
        df (pd.DataFrame): The DataFrame with all features.
        feature_list (list[str]): The list of features to select.

    Returns:
        A DataFrame containing only the selected features.
    """
    return df[feature_list]

def build_feature_set(df: pd.DataFrame) -> pd.DataFrame:
    """
    Builds the full feature set for the RL model.

    Args:
        df (pd.DataFrame): The raw preprocessed data.

    Returns:
        A DataFrame with all necessary features for model training.
    """
    df_with_indicators = add_technical_indicators(df)
    feature_df = select_features(df_with_indicators, OBSERVATION_SPACE_FEATURES)
    return feature_df