import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# 1) Bollinger Bands Using OHLC Average:
def BollingerBands_OHLC(df: pd.DataFrame, n=20, sd=2):
    """
    Function to calculate Bollinger Bands for a given dataframe.
    
    Parameters:
    df (pd.DataFrame): Input dataframe with columns "Mid_Open", "Mid_High", "Mid_Low", "Mid_Close".
    n (int): The number of periods for smoothing (default is 20).
    sd (int): The number of standard deviations for upper and lower band (default is 2).
    
    Returns:
    df (pd.DataFrame): Dataframe with added columns "BB_SMA{n}", "BB_Upper", "BB_Lower" representing 
                       the Bollinger Bands.
    """
    # Calculate the typical price
    typical_price = (df["Mid_Open"] + df["Mid_High"] + df["Mid_Low"] + df["Mid_Close"]) / 4
    
    # Calculate the standard deviation of the typical price
    stddev = typical_price.rolling(window=n).std()
    
    # Calculate the Simple Moving Average (SMA) of the typical price
    df[f"BB_SMA{n}"] = typical_price.rolling(window=n).mean()
    
    # Calculate the upper Bollinger Band
    df["BB_Upper"] = df[f"BB_SMA{n}"] + (sd * stddev)
    
    # Calculate the lower Bollinger Band
    df["BB_Lower"] = df[f"BB_SMA{n}"] - (sd * stddev)
    
    return df


# 2) Volume Weighted Bollinger Bands Using OHLC Average:
def VW_BollingerBands_OHLC(df: pd.DataFrame, n=20, sd=2):
    """
    Function to calculate Volume Weighted Bollinger Bands using OHLC (Open, High, Low, Close) Average.
    
    Parameters:
    df (pd.DataFrame): DataFrame containing the stock data
    n (int): The period for SMA calculation. Default is 20.
    sd (int): The standard deviation for the Bollinger Bands. Default is 2.
    
    Returns:
    df (pd.DataFrame): DataFrame with the calculated Bollinger Bands added as new columns.
    """
    
    # Calculate the typical price by taking the average of mid open, mid high, mid low and mid close prices
    typical_price = (df["Mid_Open"] + df["Mid_High"] + df["Mid_Low"] + df["Mid_Close"]) / 4
    
    # Multiply the typical price with the volume
    tp_vol = typical_price * df["Volume"]
    
    # Calculate the Simple Moving Average (SMA) of the typical price volume
    tp_vol_sma = tp_vol.rolling(window=n).mean()
    
    # Calculate the SMA of the volume
    vol_sma = df["Volume"].rolling(window=n).mean()
    
    # Calculate the Volume Weighted SMA and add it as a new column to the DataFrame
    df[f"VW_BB_SMA{n}"] = tp_vol_sma / vol_sma
    
    # Calculate the standard deviation of the Volume Weighted SMA
    stddev = df[f"VW_BB_SMA{n}"].rolling(window=n).std()
    
    # Calculate the upper Bollinger Band and add it as a new column to the DataFrame
    df["VW_BB_Upper"] = df[f"VW_BB_SMA{n}"] + (sd * stddev)
    
    # Calculate the lower Bollinger Band and add it as a new column to the DataFrame
    df["VW_BB_Lower"] = df[f"VW_BB_SMA{n}"] - (sd * stddev)
    
    return df

# 3) Volume Weighted Bollinger Bands Using High-Low Midpoint:
def VW_BollingerBands_HL(df: pd.DataFrame, n=20, sd=2):
    """
    Volume Weighted Bollinger Bands Using High-Low Midpoint (SMA: 20 Period | Standard Deviation: 2)

    Args:
        df (pd.DataFrame): The DataFrame containing the candlestick data
        n (int, optional): The period for the moving average. Defaults to 20.
        sd (int, optional): The number of standard deviations to use for the Bollinger Bands. Defaults to 2.

    Returns:
        pd.DataFrame: The DataFrame with the Bollinger Bands columns added
    """

    # Calculate the midpoint of the high and low prices
    mid_point = (df["Mid_High"] + df["Mid_Low"]) / 2

    # Calculate the volume weighted moving average of the midpoints
    mp_vol = mid_point * df["Volume"]
    mp_vol_sma = mp_vol.rolling(window=n).mean()

    # Calculate the moving average of the volume
    vol_sma = df["Volume"].rolling(window=n).mean()

    # Calculate the Volume Weighted Bollinger Bands
    df[f"VW_BB_HL_SMA{n}"] = mp_vol_sma / vol_sma

    # Calculate the standard deviation of the Volume Weighted Bollinger Bands
    stddev = df[f"VW_BB_HL_SMA{n}"].rolling(window=n).std()

    # Calculate the upper and lower bands
    df["VW_BB_HL_Upper"] = df[f"VW_BB_HL_SMA{n}"] + (sd * stddev)
    df["VW_BB_HL_Lower"] = df[f"VW_BB_HL_SMA{n}"] - (sd * stddev)

    return df


# 4) Volume Weighted Bollinger BandWidth High-Low Midpoint:
def VW_BollingerBandWidth_HL(df: pd.DataFrame, n=20, sd=2, bbwsma=10):
    """
    Volume Weighted Bollinger Band Width Using High-Low Midpoint (SMA: 20 Period | Standard Deviation: 2)

    Args:
        df (pd.DataFrame): Dataframe containing the data for which to calculate the Volume Weighted Bollinger Band Width
        n (int, optional): The period used to calculate the Bollinger Band (default is 20)
        sd (int, optional): The standard deviation used to calculate the Bollinger Band (default is 2)
        bbwsma (int, optional): The period used to calculate the VW BBW SMA (default is 10)

    Returns:
        pd.DataFrame: Dataframe with the calculated Volume Weighted Bollinger Band Width
    """

    # Calculate the midpoint of the high and low prices
    mid_point = (df["Mid_High"] + df["Mid_Low"]) / 2

    # Calculate the volume weighted moving average of the midpoint
    mp_vol = mid_point * df["Volume"]
    mp_vol_sma = mp_vol.rolling(window=n).mean()

    # Calculate the simple moving average of the volume
    vol_sma = df["Volume"].rolling(window=n).mean()

    # Calculate the Volume Weighted Bollinger Band SMA
    df[f"VW_BB_HL_SMA{n}"] = mp_vol_sma / vol_sma

    # Calculate the standard deviation of the Volume Weighted Bollinger Band SMA
    stddev = df[f"VW_BB_HL_SMA{n}"].rolling(window=n).std()

    # Calculate the upper and lower Bollinger Bands
    df["VW_BB_HL_Upper"] = df[f"VW_BB_HL_SMA{n}"] + (sd * stddev)
    df["VW_BB_HL_Lower"] = df[f"VW_BB_HL_SMA{n}"] - (sd * stddev)

    # Calculate the Volume Weighted Bollinger Band Width
    df["VW_BBW"] = (df["VW_BB_HL_Upper"] - df["VW_BB_HL_Lower"]) / df[f"VW_BB_HL_SMA{n}"]

    # Calculate the Volume Weighted Bollinger Band Width SMA
    df[f"VW_BBW_SMA{bbwsma}"] = df["VW_BBW"].rolling(window=bbwsma).mean()

    # Return the calculated Volume Weighted Bollinger Band Width
    return df


# 5) Volume Weighted Standard Deviation Using High-Low Midpoint:
def VW_StandardDeviation_HL(df: pd.DataFrame, n=20, sdsma=10, period=10):
    """
    Volume Weighted Standard Deviation Using High-Low Midpoint (EMA: 20 Period | Standard Deviation: 2)

    Formula:
    1) Calculate Mid-Point Price = (High + Low) / 2
    2) Calculate Volume Weighted Mid-Point Price = Mid-Point Price * Volume
    3) Calculate VW HL EMA = Volume Weighted Mid-Point Price n-period EMA / Volume n-period EMA
    4) Calculate VW Standard Deviation n = n-period Standard Deviation of VW HL EMA
    5) Calculate Smoothing VW Standard Deviation n = n-period Simple Moving Average of VW Standard Deviation n

    Args:
        df (pd.DataFrame): DataFrame containing historical OHLCV data
        n (int): Number of periods for EMA calculation (default: 20)
        sdsma (int): Number of periods for Smoothing VW Standard Deviation (default: 10)

    Returns:
        pd.DataFrame: DataFrame with added columns for VW Standard Deviation and its SMA
    """

    # Define the smoothing factor for the exponential moving average (EMA)
    alpha = 1.0 / n

    # Calculate the midpoint of the high and low prices
    mid_point = (df["Mid_High"] + df["Mid_Low"]) / 2

    # Calculate the volume weighted moving average of the midpoint
    mp_vol = mid_point * df["Volume"]
    mp_vol_ema = mp_vol.ewm(min_periods=n, alpha=alpha).mean()

    # Calculate the simple moving average of the volume
    vol_ema = df["Volume"].ewm(min_periods=n, alpha=alpha).mean()

    # Calculate the Volume Weighted SMA of HL Midpoint
    vw_hl = mp_vol_ema / vol_ema
    
    # Calculate VW Standard Deviation n
    df[f"VW_SD{n}"] = vw_hl.ewm(min_periods=n, alpha=alpha).std()

    # Calculate Smoothing VW Standard Deviation n
    df[f"VW_SD{n}_SMA{sdsma}"] = df[f"VW_SD{n}"].rolling(window=sdsma).mean()

    # Calculate the max and min values of VW Standard Deviation
    df[f"VW_SD_Max{period}"] = df[f"VW_SD{n}"].rolling(window=period).max()
    df[f"VW_SD_Min{period}"] = df[f"VW_SD{n}"].rolling(window=period).min()

    return df


# 6) Average True Range (ATR) with SMA of ATR:
def ATR(df: pd.DataFrame, n=14, atrsma=10):
    """
    Average True Range with SMA (IntraDay: 8 Period | Positional: 20 Period)

    Args:
        df (pd.DataFrame): The dataframe containing the candlestick data
        n (int, optional): The period for calculating the ATR. Defaults to 14.
        atrsma (int, optional): The period for calculating the SMA of the ATR. Defaults to 10.

    Returns:
        pd.DataFrame: The dataframe with the ATR and ATR_SMA columns
    """

    # Calculate the previous close price
    prev_Close = df["Mid_Close"].shift(1)

    # Calculate the true range using three different methods
    true_range_1 = (df["Mid_High"] - df["Mid_Low"])
    true_range_2 = abs(df["Mid_High"] - prev_Close)
    true_range_3 = abs(df["Mid_Low"] - prev_Close)

    # Find the maximum of the three true range values
    true_range = pd.DataFrame({"TrueRange_1": true_range_1, "TrueRange_2": true_range_2, "TrueRange_3": true_range_3}).max(axis=1)

    # Calculate the n-period ATR
    df[f"ATR{n}"] = true_range.rolling(window=n).mean()

    # Calculate the atrsma-period SMA of the ATR
    df[f"ATR{n}_SMA{atrsma}"] = df[f"ATR{n}"].rolling(window=atrsma).mean()

    # Return the dataframe with the ATR and ATR_SMA columns
    return df


# 5) Volume Weighted Average True Range (ATR) with SMA of ATR:
def VW_ATR(df: pd.DataFrame, n=14, atrsma=10):
    """
    Calculate the Volume Weighted Average True Range (VW ATR) and its Smoothed Moving Average (SMA).
    
    Parameters:
    df (pd.DataFrame): Input dataframe with columns ["Mid_Close", "Mid_High", "Mid_Low", "Volume"]
    n (int, optional): Number of periods for EMA calculation. Default is 14.
    atrsma (int, optional): Number of periods for SMA calculation. Default is 10.
    
    Returns:
    pd.DataFrame: Dataframe with added VW ATR and VW ATR SMA columns.
    
    References:
    https://www.macroption.com/normalized-atr/
    """

    # Calculate True Range
    # Shift the 'Mid_Close' column down by one row to get the previous close prices
    prev_Close = df["Mid_Close"].shift(1)
    # Calculate the difference between the high and low prices
    true_range_1 = (df["Mid_High"] - df["Mid_Low"])
    # Calculate the absolute difference between the high price and the previous close price
    true_range_2 = abs(df["Mid_High"] - prev_Close)
    # Calculate the absolute difference between the low price and the previous close price
    true_range_3 = abs(df["Mid_Low"] - prev_Close)
    # Get the maximum value among the three true ranges for each row
    true_range = pd.DataFrame({"TrueRange_1": true_range_1, "TrueRange_2": true_range_2, "TrueRange_3": true_range_3}).max(axis=1)

    # Calculate Volume Weighted Average True Range (VW ATR)
    # Define the smoothing factor for the exponential moving average (EMA)
    alpha = 1.0 / n
    # Multiply the true range by the volume to get the volume-weighted true range
    tr_vol = true_range * df["Volume"]
    # Calculate the EMA of the volume-weighted true range
    tr_vol_ema = tr_vol.ewm(min_periods=n, alpha=alpha).mean()
    # Calculate the EMA of the volume
    vol_ema = df["Volume"].ewm(min_periods=n, alpha=alpha).mean()
    # Divide the EMA of the volume-weighted true range by the EMA of the volume to get the VW ATR
    df[f"VW_ATR{n}"] = tr_vol_ema / vol_ema

    # Calculate Volume Weighted Average True Range Smoothed Moving Average (VW ATR SMA)
    # Multiply the VW ATR by the volume to get the volume-weighted VW ATR
    atr_vol = df[f"VW_ATR{n}"] * df["Volume"]
    # Calculate the simple moving average (SMA) of the volume-weighted VW ATR
    atr_vol_sma = atr_vol.rolling(window=atrsma).mean()
    # Calculate the SMA of the volume
    vol_sma = df["Volume"].rolling(window=atrsma).mean()
    # Divide the SMA of the volume-weighted VW ATR by the SMA of the volume to get the VW ATR SMA
    df[f"VW_ATR{n}_SMA{atrsma}"] = atr_vol_sma / vol_sma

    return df


# 12) Volume Weighted Average True Range Percent (ATRP) with SMA of ATRP:
def VW_ATRP(df: pd.DataFrame, n=14, atrsma=10):
    """
    Calculate the Volume Weighted Average True Range Percent (ATRP) with Simple Moving Average (SMA) of Average True Range (ATR).
    
    Parameters:
    df (pd.DataFrame): Input dataframe with columns ["Mid_Close", "Mid_High", "Mid_Low", "Volume"]
    n (int): The number of periods for exponential moving average calculation. Default is 14.
    atrsma (int): The number of periods for simple moving average calculation. Default is 10.
    
    Returns:
    pd.DataFrame: Dataframe with added VW_ATR, VW_ATRP and VW_ATRP_SMA columns.
    
    References:
    - https://traders.com/Documentation/FEEDbk_docs/2006/05/Abstracts_new/Forman/formn.html
    - https://www.macroption.com/normalized-atr/
    """

    # Calculate alpha
    alpha = 1.0 / n

    # Calculate True Range
    prev_Close = df["Mid_Close"].shift(1)
    true_range_1 = (df["Mid_High"] - df["Mid_Low"])
    true_range_2 = abs(df["Mid_High"] - prev_Close)
    true_range_3 = abs(df["Mid_Low"] - prev_Close)
    true_range = pd.DataFrame({"TrueRange_1": true_range_1, "TrueRange_2": true_range_2, "TrueRange_3": true_range_3}).max(axis=1)

    # Calculate Volume Weighted Average True Range (VW_ATR)
    tr_vol = true_range * df["Volume"]
    tr_vol_ema = tr_vol.ewm(min_periods=n, alpha=alpha).mean()
    vol_ema = df["Volume"].ewm(min_periods=n, alpha=alpha).mean()
    df[f"VW_ATR{n}"] = tr_vol_ema / vol_ema

    # Calculate Volume Weighted Average True Range Percent (VW_ATRP)
    df[f"VW_ATRP{n}"] = df[f"VW_ATR{n}"] / df["Mid_Close"] * 100

    # Calculate Simple Moving Average (SMA) of VW_ATRP
    atrp_vol = df[f"VW_ATRP{n}"] * df["Volume"]
    atrp_vol_sma = atrp_vol.rolling(window=atrsma).mean()
    vol_sma = df["Volume"].rolling(window=atrsma).mean()
    df[f"VW_ATRP{n}_SMA{atrsma}"] = atrp_vol_sma / vol_sma

    return df

# 6) Volume Weighted Normalised Average True Range Percent (NATRP) with SMA of NATRP:
def Normalised_VW_ATRP(df: pd.DataFrame, n=14, atrsma=10):
    """
    This function calculates the Volume Weighted Normalised Average True Range Percent (NATRP) with SMA of NATRP.
    
    Parameters:
    df (pd.DataFrame): The input dataframe with the stock data.
    n (int): The period for the exponential moving average calculation. Default is 14.
    atrsma (int): The period for the simple moving average calculation. Default is 10.
    
    Returns:
    df (pd.DataFrame): The dataframe with the added columns for Normalised VW ATRP and Normalised VW ATRP with SMA.
    
    References:
    https://www.macroption.com/normalized-atr/
    """
    # Define the alpha for the exponential moving average
    alpha = 1.0 / n

    # Calculate True Range
    # Shift the 'Mid_Close' column down by one row to get the previous close prices
    prev_Close = df["Mid_Close"].shift(1)
    # Calculate the difference between the high and low prices
    true_range_1 = (df["Mid_High"] - df["Mid_Low"])
    # Calculate the absolute difference between the high price and the previous close price
    true_range_2 = abs(df["Mid_High"] - prev_Close)
    # Calculate the absolute difference between the low price and the previous close price
    true_range_3 = abs(df["Mid_Low"] - prev_Close)
    # Get the maximum value among the three true ranges for each row
    true_range = pd.DataFrame({"TrueRange_1": true_range_1, "TrueRange_2": true_range_2, "TrueRange_3": true_range_3}).max(axis=1)

    # Calculate the normalised true range
    norm_true_range = true_range / df["Mid_Close"] * 100

    # Calculate the normalised true range volume
    norm_tr_vol = norm_true_range * df["Volume"]

    # Calculate the exponential moving average of the normalised true range volume
    norm_tr_vol_ema = norm_tr_vol.ewm(min_periods=n, alpha=alpha).mean()

    # Calculate the exponential moving average of the volume
    vol_ema = df["Volume"].ewm(min_periods=n, alpha=alpha).mean()

    # Calculate the Normalised VW ATRP
    df[f"Norm_VW_ATRP{n}"] = norm_tr_vol_ema / vol_ema

    # Calculate the volume of the Normalised VW ATRP
    n_atrp_vol = df[f"Norm_VW_ATRP{n}"] * df["Volume"]

    # Calculate the simple moving average of the volume of the Normalised VW ATRP
    n_atrp_vol_sma = n_atrp_vol.rolling(window=atrsma).mean()

    # Calculate the simple moving average of the volume
    vol_sma = df["Volume"].rolling(window=atrsma).mean()

    # Calculate the Normalised VW ATRP with SMA
    df[f"Norm_VW_ATRP{n}_SMA{atrsma}"] = n_atrp_vol_sma / vol_sma

    return df


# 13) Keltner Channels Using OHLC Average:
def KeltnerChannels(df: pd.DataFrame, n=20, atr=14, num=2):
    """
    Function to calculate Keltner Channels using OHLC Average.
    
    Parameters:
    df (pd.DataFrame): Input dataframe with OHLC data.
    n (int, optional): Period for EMA calculation. Default is 20.
    atr (int, optional): Period for ATR calculation. Default is 14.
    num (int, optional): Multiplier for ATR in Keltner Channel calculation. Default is 2.
    
    Returns:
    df (pd.DataFrame): Dataframe with added Keltner Channel data.
    
    Note:
    EMA: Exponential Moving Average
    ATR: Average True Range
    OHLC: Open, High, Low, Close
    """
    # Calculate Typical Price
    typical_price = (df["Mid_Open"] + df["Mid_High"] + df["Mid_Low"] + df["Mid_Close"]) / 4

    # Calculate EMA of Typical Price
    df[f"KC_EMA{n}"] = typical_price.ewm(span=n, min_periods=n).mean()

    # Calculate Average True Range (ATR)
    df = ATR(df, n=atr)

    # Calculate Upper and Lower Keltner Channels
    df["KC_Upper"] = df[f"KC_EMA{n}"] + (num * df[f"ATR{atr}"])
    df["KC_Lower"] = df[f"KC_EMA{n}"] - (num * df[f"ATR{atr}"])

    return df


# 14) Volume Weighted Keltner Channels Using OHLC Average:
def VW_KeltnerChannels(df: pd.DataFrame, n=20, atr=14, num=2):
    """
    Function to calculate Volume Weighted Keltner Channels using OHLC Average.
    
    Parameters:
    df (pd.DataFrame): Input dataframe with OHLC (Open, High, Low, Close) data.
    n (int): The time period for EMA calculation. Default is 20.
    atr (int): The time period for ATR calculation. Default is 14.
    num (int): The multiplier for ATR to calculate the upper and lower Keltner Channels. Default is 2.
    
    Returns:
    df (pd.DataFrame): Output dataframe with added columns for EMA, ATR, upper and lower Keltner Channels.
    """
    # Calculate the typical price
    typical_price = (df["Mid_Open"] + df["Mid_High"] + df["Mid_Low"] + df["Mid_Close"]) / 4
    # Calculate the volume weighted typical price
    tp_vol = typical_price * df["Volume"]
    # Calculate the EMA of the volume weighted typical price
    tp_vol_ema = tp_vol.ewm(span=n, min_periods=n).mean()
    # Calculate the EMA of the volume
    vol_ema = df["Volume"].ewm(span=n, min_periods=n).mean()
    # Calculate the volume weighted EMA
    df[f"VW_KC_EMA{n}"] = tp_vol_ema / vol_ema
    # Calculate the ATR
    df = VW_ATR(df, n=atr)
    # Calculate the upper Keltner Channel
    df["VW_KC_Upper"] = df[f"VW_KC_EMA{n}"] + (num * df[f"VW_ATR{atr}"])
    # Calculate the lower Keltner Channel
    df["VW_KC_Lower"] = df[f"VW_KC_EMA{n}"] - (num * df[f"VW_ATR{atr}"])
    return df


# 15) Volume Weighted Keltner Channels Using OHLC Average and SMA of ATR:
def VW_KeltnerChannels_SMA(df: pd.DataFrame, n=20, atr=14, atrsma=10, num=2):
    """
    Calculate the Volume Weighted Keltner Channels using OHLC Average and SMA of ATR.

    Parameters:
    df (pd.DataFrame): Input dataframe with OHLC (Open, High, Low, Close) data and Volume.
    n (int): The period for the SMA calculation. Default is 20.
    atr (int): The period for the ATR calculation. Default is 14.
    atrsma (int): The period for the SMA of ATR calculation. Default is 10.
    num (int): The multiplier for the ATR to calculate the upper and lower Keltner Channels. Default is 2.

    Returns:
    df (pd.DataFrame): Output dataframe with added columns for VW_KC_SMA, VW_KC_SMA_Upper, and VW_KC_SMA_Lower.

    """

    # Calculate the typical price
    typical_price = (df["Mid_Open"] + df["Mid_High"] + df["Mid_Low"] + df["Mid_Close"]) / 4

    # Calculate the typical price volume
    tp_vol = typical_price * df["Volume"]

    # Calculate the EMA of the typical price volume
    tp_vol_ema = tp_vol.ewm(span=n, min_periods=n).mean()

    # Calculate the SMA of the volume
    vol_ema = df["Volume"].ewm(span=n, min_periods=n).mean()

    # Calculate the Volume Weighted Keltner Channel EMA
    df[f"VW_KC_EMA{n}"] = tp_vol_ema / vol_ema

    # Calculate the VW ATR
    df = VW_ATR(df, n=atr)

    # Calculate the upper Keltner Channel SMA
    df["VW_KC_SMA_Upper"] = df[f"VW_KC_EMA{n}"] + (num * df[f"VW_ATR{atr}_SMA{atrsma}"])

    # Calculate the lower Keltner Channel SMA
    df["VW_KC_SMA_Lower"] = df[f"VW_KC_EMA{n}"] - (num * df[f"VW_ATR{atr}_SMA{atrsma}"])

    return df


# 2) Volume Weighted Keltner Channels Using High-Low Midpoint and SMA of ATR:
def VW_KeltnerChannels_HL_SMA(df: pd.DataFrame, n=20, atr=14, atrsma=10, num=2):
    """
    Volume Weighted Keltner Channels Using High-Low Midpoint and SMA of ATR (SMA: 20 Period | IntraDay ATR: 8 Period | Positional ATR: 21 Period)

    Args:
        df (pd.DataFrame): The DataFrame containing the candlestick data
        n (int, optional): The period for the moving average. Defaults to 20.
        atr (int, optional): The period for the Average True Range. Defaults to 14.
        atrsma (int, optional): The period for the moving average of ATR. Defaults to 10.
        num (int, optional): The multiple of ATR to use for the Keltner Channels. Defaults to 2.

    Returns:
        pd.DataFrame: The DataFrame with the Keltner Channels columns added
    """

    # Calculate the mid-point of the high and low prices
    mid_point = (df["Mid_High"] + df["Mid_Low"]) / 2

    # Calculate the volume-weighted mid-point
    mp_vol = mid_point * df["Volume"]

    # Calculate the n-period moving average of the volume-weighted mid-point
    mp_vol_ema = mp_vol.ewm(span=n, min_periods=n).mean()

    # Calculate the n-period moving average of the volume
    vol_ema = df["Volume"].ewm(span=n, min_periods=n).mean()

    # Calculate the VW Keltner Channel using High-Low Midpoint and SMA of ATR
    df[f"VW_KC_HL_EMA{n}"] = mp_vol_ema / vol_ema

    # Calculate the VW ATR
    df = VW_ATR(df, n=atr)

    # Calculate the upper and lower bands of the VW Keltner Channel
    df["VW_KC_HL_SMA_Upper"] = df[f"VW_KC_HL_EMA{n}"] + (num * df[f"VW_ATR{atr}_SMA{atrsma}"])
    df["VW_KC_HL_SMA_Lower"] = df[f"VW_KC_HL_EMA{n}"] - (num * df[f"VW_ATR{atr}_SMA{atrsma}"])

    return df


# 16) Relative Strength Index (RSI) Using Close and with SMA of RSI:
def RSI(df: pd.DataFrame, n=14, rsisma=10, period=10):
    """
    Calculates the Relative Strength Index (RSI) and its Simple Moving Average (SMA) for a given DataFrame.

    Parameters:
    df (pd.DataFrame): The input DataFrame with a "Mid_Close" column representing closing prices.
    n (int, optional): The period for RSI calculation. Defaults to 14.
    rsisma (int, optional): The period for SMA calculation. Defaults to 10.
    period (int, optional): The look back period for calculating the maximum and minimum MFI values. Default is 10.

    Returns:
    pd.DataFrame: The input DataFrame with added columns for RSI and its SMA.
    """

    # Calculate alpha
    alpha = 1.0 / n

    # Calculate the price change
    price_change = df["Mid_Close"].diff()

    # Calculate the gain and loss
    gain = pd.Series([x if x >=0 else 0.0 for x in price_change], name="gain")
    loss = pd.Series([(x * -1) if x < 0 else 0.0 for x in price_change], name="loss")

    # Calculate the exponential weighted moving average of the gain and loss
    avgGain = gain.ewm(min_periods=n, alpha=alpha).mean()
    avgLoss = loss.ewm(min_periods=n, alpha=alpha).mean()

    # Calculate the relative strength
    rs = avgGain / avgLoss

    # Calculate the RSI
    df[f"RSI{n}"] = 100.0 - (100.0 / (1.0 + rs))

    # Calculate the SMA of the RSI
    df[f"RSI{n}_SMA{rsisma}"] = df[f"RSI{n}"].rolling(window=rsisma).mean()

    # Calculate the max and min values of Money Flow Index
    df[f"RSI_Max{period}"] = df[f"RSI{n}"].rolling(window=period).max()
    df[f"RSI_Min{period}"] = df[f"RSI{n}"].rolling(window=period).min()

    return df



# 18) Relative Strength Index (RSI) Using Open and with SMA of RSI:
def RSI_O(df: pd.DataFrame, n=14, rsisma=10, period=10):
    """
    Calculate the Relative Strength Index (RSI) using the opening price and apply a Simple Moving Average (SMA) to the RSI.

    Parameters:
    df (pd.DataFrame): Dataframe containing the stock data
    n (int, optional): The number of periods to consider for the RSI calculation. Default is 14.
    rsisma (int, optional): The number of periods to consider for the SMA calculation. Default is 10.
    period (int, optional): The look back period for calculating the maximum and minimum MFI values. Default is 10.

    Returns:
    df (pd.DataFrame): Dataframe with the calculated RSI and SMA values added as new columns.

    """
    # Calculate the alpha value
    alpha = 1.0 / n

    # Calculate the price change
    price_change = df["Mid_Open"].diff()

    # Calculate the gain and loss
    gain = pd.Series([x if x >=0 else 0.0 for x in price_change], name="gain")
    loss = pd.Series([(x * -1) if x < 0 else 0.0 for x in price_change], name="loss")

    # Calculate the average gain and loss
    avgGain = gain.ewm(min_periods=n, alpha=alpha).mean()
    avgLoss = loss.ewm(min_periods=n, alpha=alpha).mean()

    # Calculate the relative strength (RS)
    rs = avgGain / avgLoss

    # Calculate the RSI and add it to the dataframe
    df[f"RSI{n}_O"] = 100.0 - (100.0 / (1.0 + rs))

    # Calculate the SMA of the RSI and add it to the dataframe
    df[f"RSI{n}_O_SMA{rsisma}"] = df[f"RSI{n}_O"].rolling(window=rsisma).mean()

    # Calculate the max and min values of Money Flow Index
    df[f"RSI_O_Max{period}"] = df[f"RSI{n}_O"].rolling(window=period).max()
    df[f"RSI_O_Min{period}"] = df[f"RSI{n}_O"].rolling(window=period).min()

    return df


# 17) Relative Strength Index (RSI) Using OHLC Average and with SMA of RSI:
def RSI_OHLC(df: pd.DataFrame, n=14, rsisma=10, period=10):
    """
    Function to calculate the Relative Strength Index (RSI) using Open, High, Low, Close (OHLC) average and with Simple Moving Average (SMA) of RSI.
    
    Parameters:
    df (pd.DataFrame): Dataframe containing the OHLC data
    n (int, optional): The number of periods for which the RSI is calculated. Default is 14.
    rsisma (int, optional): The number of periods for the SMA of RSI. Default is 10.
    period (int, optional): The look back period for calculating the maximum and minimum MFI values. Default is 10.
    
    Returns:
    df (pd.DataFrame): Dataframe with the calculated RSI and SMA of RSI added as new columns.
    """
    # Calculate the alpha value
    alpha = 1.0 / n
    
    # Calculate the typical price
    typical_price = (df["Mid_Open"] + df["Mid_High"] + df["Mid_Low"] + df["Mid_Close"]) / 4
    
    # Calculate the price change
    price_change = typical_price.diff()
    
    # Calculate the gain and loss
    gain = pd.Series([x if x >=0 else 0.0 for x in price_change], name="gain")
    loss = pd.Series([(x * -1) if x < 0 else 0.0 for x in price_change], name="loss")
    
    # Calculate the average gain and loss
    avgGain = gain.ewm(min_periods=n, alpha=alpha).mean()
    avgLoss = loss.ewm(min_periods=n, alpha=alpha).mean()
    
    # Calculate the relative strength (RS)
    rs = avgGain / avgLoss
    
    # Calculate the RSI
    df[f"RSI{n}_OHLC"] = 100.0 - (100.0 / (1.0 + rs))
    
    # Calculate the SMA of RSI
    df[f"RSI{n}_OHLC_SMA{rsisma}"] = df[f"RSI{n}_OHLC"].rolling(window=rsisma).mean()

    # Calculate the max and min values of Money Flow Index
    df[f"RSI_OHLC_Max{period}"] = df[f"RSI{n}_OHLC"].rolling(window=period).max()
    df[f"RSI_OHLC_Min{period}"] = df[f"RSI{n}_OHLC"].rolling(window=period).min()
    
    return df


# 7) Relative Strength Index (RSI) Using High-Low Midpoint and with SMA of RSI:
def RSI_HL(df: pd.DataFrame, n=14, rsisma=10, period=10):
    """
    Relative Strength Index Using High-Low Midpoint and with SMA of RSI (14 Period)

    Args:
        df (pd.DataFrame): Pandas DataFrame with candlestick data
        n (int, optional): Period for RSI calculation. Defaults to 14.
        rsisma (int, optional): Period for smoothing RSI. Defaults to 10.
        period (int, optional): The look back period for calculating the maximum and minimum MFI values. Default is 10.

    Returns:
        pd.DataFrame: Pandas DataFrame with added RSI indicator
    """

    # Define the alpha for the exponential moving average
    alpha = 1.0 / n
    
    # Calculate mid point
    mid_point = (df["Mid_High"] + df["Mid_Low"]) / 2
    
    # Calculate price change
    price_change = mid_point.diff()

    # Calculate the Gain
    gain = pd.Series([x if x >=0 else 0.0 for x in price_change], name="gain")

    # Calculate Loss
    loss = pd.Series([(x * -1) if x < 0 else 0.0 for x in price_change], name="loss")

    # Calculate Average Gain
    avgGain = gain.ewm(min_periods=n, alpha=alpha).mean()

    # Calculate Average Loss
    avgLoss = loss.ewm(min_periods=n, alpha=alpha).mean()

    # Calculate RSI
    rs = avgGain / avgLoss
    df[f"RSI{n}_HL"] = 100.0 - (100.0 / (1.0 + rs))

    # Calculate the max and min values of RSI during the last n periods
    df[f"RSI_HL_Max{period}"] = df[f"RSI{n}_HL"].rolling(window=period).max()
    df[f"RSI_HL_Min{period}"] = df[f"RSI{n}_HL"].rolling(window=period).min()

    # Calculate the smoothed RSI
    df[f"RSI{n}_HL_SMA{rsisma}"] = df[f"RSI{n}_HL"].rolling(window=rsisma).mean()

    return df


# 19) Money Flow Index (MFI) Using Close and with SMA of MFI:
def MFI(df: pd.DataFrame, n=14, mfisma=10, period=10):
    """
    Calculates the Money Flow Index (MFI) and its Simple Moving Average (SMA) for a given DataFrame.

    Parameters:
    df (pd.DataFrame): The input DataFrame. It should contain columns "Mid_Close" and "Volume".
    n (int, optional): The period for the MFI calculation. Default is 14.
    mfisma (int, optional): The period for the SMA of MFI calculation. Default is 10.
    period (int, optional): The look back period for calculating the maximum and minimum MFI values. Default is 10.

    Returns:
    pd.DataFrame: The DataFrame with added MFI and MFI_SMA columns.

    """
    # Define the alpha for the exponential moving average
    alpha = 1.0 / n

    # Calculate the price change
    price_change = df["Mid_Close"].diff()
    
    # Calculate the gain and loss
    gain = pd.Series([x if x >=0 else 0.0 for x in price_change], name="gain")
    loss = pd.Series([(x * -1) if x < 0 else 0.0 for x in price_change], name="loss")
    
    # Calculate the gain volume and loss volume
    gain_vol = gain * df["Volume"]
    loss_vol = loss * df["Volume"]
    
    # Calculate the exponential moving average of gain volume and loss volume
    gain_vol_ema = gain_vol.ewm(min_periods=n, alpha=alpha).mean()
    loss_vol_ema = loss_vol.ewm(min_periods=n, alpha=alpha).mean()
    
    # Calculate the volume exponential moving average
    vol_ema = df["Volume"].ewm(min_periods=n, alpha=alpha).mean()
    
    # Calculate the average gain and average loss
    avgGain = gain_vol_ema / vol_ema
    avgLoss = loss_vol_ema / vol_ema
    
    # Calculate the relative strength
    rs = avgGain / avgLoss
    
    # Calculate the Money Flow Index
    df[f"MFI{n}"] = 100.0 - (100.0 / (1.0 + rs))
    
    # Calculate the simple moving average of Money Flow Index
    df[f"MFI{n}_SMA{mfisma}"] = df[f"MFI{n}"].rolling(window=mfisma).mean()

    # Calculate the max and min values of Money Flow Index
    df[f"MFI_Max{period}"] = df[f"MFI{n}"].rolling(window=period).max()
    df[f"MFI_Min{period}"] = df[f"MFI{n}"].rolling(window=period).min()
    
    return df



# 8) Money Flow Index (MFI) Using High-Low Midpoint and with SMA of MFI:
def MFI_HL(df: pd.DataFrame, n=14, mfisma=10, period=10):
    """
    Money Flow Index (Volume Weighted Relative Strength Index) Using High-Low Midpoint and with SMA of MFI (14 Period)

    Args:
        df (pd.DataFrame): Pandas DataFrame with candlestick data
        n (int, optional): Period for RSI calculation. Defaults to 14.
        mfisma (int, optional): Period for smoothing MFI. Defaults to 10.
        period (int, optional): The look back period for calculating the maximum and minimum MFI values. Default is 10.

    Returns:
        pd.DataFrame: Pandas DataFrame with added RSI indicator
    """
    # Calculate alpha
    alpha = 1.0 / n
    
    # Calculate mid point
    mid_point = (df["Mid_High"] + df["Mid_Low"]) / 2
    
    # Calculate price change
    price_change = mid_point.diff()
    
    # Calculate gain and gain volume
    gain = pd.Series([x if x >=0 else 0.0 for x in price_change], name="gain")
    gain_vol = gain * df["Volume"]
    gain_vol_ema = gain_vol.ewm(min_periods=n, alpha=alpha).mean()
    
    # Calculate loss and loss volume
    loss = pd.Series([(x * -1) if x < 0 else 0.0 for x in price_change], name="loss")
    loss_vol = loss * df["Volume"]
    loss_vol_ema = loss_vol.ewm(min_periods=n, alpha=alpha).mean()
    
    # Calculate relative strength
    rs = gain_vol_ema / loss_vol_ema
    
    # Add MFI_HL and MFI_HL_SMA to the dataframe
    df[f"MFI{n}_HL"] = 100.0 - (100.0 / (1.0 + rs))
    df[f"MFI{n}_HL_SMA{mfisma}"] = df[f"MFI{n}_HL"].rolling(window=mfisma).mean()

    # Calculate the max and min values of Money Flow Index
    df[f"MFI_HL_Max{period}"] = df[f"MFI{n}_HL"].rolling(window=period).max()
    df[f"MFI_HL_Min{period}"] = df[f"MFI{n}_HL"].rolling(window=period).min()
    
    return df


# 5) Moving Average Convergence Divergence (MACD):
def MACD(df: pd.DataFrame, n_fast=12, n_slow=26, n_signal=9):
    """
    Moving Average Convergence Divergence (Fast EMA: 12 Period | Slow EMA: 26 Period | Signal Line EMA: 9 Period)

    Args:
        df (pd.DataFrame): The DataFrame containing the OHLCV data.
        n_fast (int, optional): The number of periods for the fast EMA. Defaults to 12.
        n_slow (int, optional): The number of periods for the slow EMA. Defaults to 26.
        n_signal (int, optional): The number of periods for the signal EMA. Defaults to 9.

    Returns:
        pd.DataFrame: The DataFrame with the MACD, Signal, and Histogram columns added.
    """

    # Calculate the fast EMA
    ema_fast = df["Mid_Close"].ewm(min_periods=n_fast, span=n_fast).mean()

    # Calculate the slow EMA
    ema_slow = df["Mid_Close"].ewm(min_periods=n_slow, span=n_slow).mean()

    # Calculate the MACD
    df["MACD"] = ema_fast - ema_slow

    # Calculate the signal EMA
    df["Signal"] = df["MACD"].ewm(min_periods=n_signal, span=n_signal).mean()

    # Calculate the histogram
    df["Histogram"] = df["MACD"] - df["Signal"]

    return df


# 5) Moving Average Convergence Divergence (MACD) of Open:
def MACD_O(df: pd.DataFrame, n_fast=12, n_slow=26, n_signal=9):
    """
    Moving Average Convergence Divergence of Open (Fast EMA: 12 Period | Slow EMA: 26 Period | Signal Line EMA: 9 Period)

    Args:
        df (pd.DataFrame): The DataFrame containing the OHLCV data.
        n_fast (int, optional): The number of periods for the fast EMA. Defaults to 12.
        n_slow (int, optional): The number of periods for the slow EMA. Defaults to 26.
        n_signal (int, optional): The number of periods for the signal EMA. Defaults to 9.

    Returns:
        pd.DataFrame: The DataFrame with the MACD, Signal, and Histogram columns added.
    """

    # Calculate the fast EMA
    ema_fast = df["Mid_Open"].ewm(min_periods=n_fast, span=n_fast).mean()

    # Calculate the slow EMA
    ema_slow = df["Mid_Open"].ewm(min_periods=n_slow, span=n_slow).mean()

    # Calculate the MACD
    df["MACD_O"] = ema_fast - ema_slow

    # Calculate the signal EMA
    df["Signal_O"] = df["MACD_O"].ewm(min_periods=n_signal, span=n_signal).mean()

    # Calculate the histogram
    df["Histogram_O"] = df["MACD_O"] - df["Signal_O"]

    return df


# 8) Moving Average Convergence Divergence (MACD) of OHLC:
def MACD_OHLC(df: pd.DataFrame, n_fast=12, n_slow=26, n_signal=9):
    """
    Moving Average Convergence Divergence of OHLC (Fast EMA: 12 Period | Slow EMA: 26 Period | Signal Line EMA: 9 Period)

    Args:
        df (pd.DataFrame): The DataFrame containing the OHLCV data.
        n_fast (int, optional): The number of periods for the fast EMA. Defaults to 12.
        n_slow (int, optional): The number of periods for the slow EMA. Defaults to 26.
        n_signal (int, optional): The number of periods for the signal EMA. Defaults to 9.

    Returns:
        pd.DataFrame: The DataFrame with the MACD, Signal, and Histogram columns added.
    """

    alpha_fast = 1.0 / n_fast
    alpha_slow = 1.0 / n_slow
    alpha_signal = 1.0 / n_signal
    
    # Calculate the typical price
    typical_price = (df["Mid_Open"] + df["Mid_High"] + df["Mid_Low"] + df["Mid_Close"]) / 4

    # Calculate the fast EMA
    ema_fast = typical_price.ewm(min_periods=n_fast, alpha=alpha_fast).mean()

    # Calculate the slow EMA
    ema_slow = typical_price.ewm(min_periods=n_slow, alpha=alpha_slow).mean()

    # Calculate the MACD
    df["MACD_OHLC"] = ema_fast - ema_slow

    # Calculate the signal EMA
    df["Signal_OHLC"] = df["MACD_OHLC"].ewm(min_periods=n_signal, alpha=alpha_signal).mean()

    # Calculate the histogram
    df["Histogram_OHLC"] = df["MACD_OHLC"] - df["Signal_OHLC"]

    return df


# 8) Moving Average Convergence Divergence (MACD) of High Low:
def MACD_HL(df: pd.DataFrame, n_fast=12, n_slow=26, n_signal=9):
    """
    Moving Average Convergence Divergence of High Low (Fast EMA: 12 Period | Slow EMA: 26 Period | Signal Line EMA: 9 Period)

    Args:
        df (pd.DataFrame): The DataFrame containing the OHLCV data.
        n_fast (int, optional): The number of periods for the fast EMA. Defaults to 12.
        n_slow (int, optional): The number of periods for the slow EMA. Defaults to 26.
        n_signal (int, optional): The number of periods for the signal EMA. Defaults to 9.

    Returns:
        pd.DataFrame: The DataFrame with the MACD, Signal, and Histogram columns added.
    """

    alpha_fast = 1.0 / n_fast
    alpha_slow = 1.0 / n_slow
    alpha_signal = 1.0 / n_signal
    
    # Calculate the typical price
    mid_point = (df["Mid_High"] + df["Mid_Low"]) / 2

    # Calculate the fast EMA
    ema_fast = mid_point.ewm(min_periods=n_fast, alpha=alpha_fast).mean()

    # Calculate the slow EMA
    ema_slow = mid_point.ewm(min_periods=n_slow, alpha=alpha_slow).mean()

    # Calculate the MACD
    df["MACD_HL"] = ema_fast - ema_slow

    # Calculate the signal EMA
    df["Signal_HL"] = df["MACD_HL"].ewm(min_periods=n_signal, alpha=alpha_signal).mean()

    # Calculate the histogram
    df["Histogram_HL"] = df["MACD_HL"] - df["Signal_HL"]

    return df


# 8) Volume Weighted Moving Average Convergence Divergence (MACD):
def VW_MACD(df: pd.DataFrame, n_fast=12, n_slow=26, n_signal=9):
    """
    Volume Weighted Moving Average Convergence Divergence (Fast EMA: 12 Period | Slow EMA: 26 Period | Signal Line EMA: 9 Period)

    Args:
        df (pd.DataFrame): The DataFrame containing the OHLCV data.
        n_fast (int, optional): The number of periods for the fast EMA. Defaults to 12.
        n_slow (int, optional): The number of periods for the slow EMA. Defaults to 26.
        n_signal (int, optional): The number of periods for the signal EMA. Defaults to 9.

    Returns:
        pd.DataFrame: The DataFrame with the MACD, Signal, and Histogram columns added.
    """

    # Calculate the alpha value
    alpha_fast = 1.0 / n_fast
    alpha_slow = 1.0 / n_slow
    alpha_signal = 1.0 / n_signal
    
    # Calculate the Close x Volume
    c_vol = df["Mid_Close"] * df["Volume"]

    # Calculate the fast EMA
    c_vol_ema_fast = c_vol.ewm(min_periods=n_fast, alpha=alpha_fast).mean()

    # Calculate the slow EMA
    c_vol_ema_slow = c_vol.ewm(min_periods=n_slow, alpha=alpha_slow).mean()

    # Calculate the Fast and Slow EMA of the volume
    vol_ema_fast = df["Volume"].ewm(min_periods=n_fast, alpha=alpha_fast).mean()
    vol_ema_slow = df["Volume"].ewm(min_periods=n_slow, alpha=alpha_slow).mean()

    # Calculate the Volume Weighted EMAs of Fast and Slow EMA
    vw_ema_fast = c_vol_ema_fast / vol_ema_fast
    vw_ema_slow = c_vol_ema_slow / vol_ema_slow

        # Calculate the MACD
    df["VW_MACD"] = vw_ema_fast - vw_ema_slow

    # Calculate the signal EMA
    df["VW_Signal"] = df["VW_MACD"].ewm(min_periods=n_signal, alpha=alpha_signal).mean()

    # Calculate the histogram
    df["VW_Histogram"] = df["VW_MACD"] - df["VW_Signal"]

    return df


# 8) Volume Weighted Moving Average Convergence Divergence (MACD) of Open:
def VW_MACD_O(df: pd.DataFrame, n_fast=12, n_slow=26, n_signal=9):
    """
    Volume Weighted Moving Average Convergence Divergence of Open (Fast EMA: 12 Period | Slow EMA: 26 Period | Signal Line EMA: 9 Period)

    Args:
        df (pd.DataFrame): The DataFrame containing the OHLCV data.
        n_fast (int, optional): The number of periods for the fast EMA. Defaults to 12.
        n_slow (int, optional): The number of periods for the slow EMA. Defaults to 26.
        n_signal (int, optional): The number of periods for the signal EMA. Defaults to 9.

    Returns:
        pd.DataFrame: The DataFrame with the MACD, Signal, and Histogram columns added.
    """

    # Calculate the alpha value
    alpha_fast = 1.0 / n_fast
    alpha_slow = 1.0 / n_slow
    alpha_signal = 1.0 / n_signal
    
    # Calculate the Close x Volume
    o_vol = df["Mid_Open"] * df["Volume"]

    # Calculate the fast EMA
    o_vol_ema_fast = o_vol.ewm(min_periods=n_fast, alpha=alpha_fast).mean()

    # Calculate the slow EMA
    o_vol_ema_slow = o_vol.ewm(min_periods=n_slow, alpha=alpha_slow).mean()

    # Calculate the Fast and Slow EMA of the volume
    vol_ema_fast = df["Volume"].ewm(min_periods=n_fast, alpha=alpha_fast).mean()
    vol_ema_slow = df["Volume"].ewm(min_periods=n_slow, alpha=alpha_slow).mean()

    # Calculate the Volume Weighted EMAs of Fast and Slow EMA
    vw_ema_fast = o_vol_ema_fast / vol_ema_fast
    vw_ema_slow = o_vol_ema_slow / vol_ema_slow

        # Calculate the MACD
    df["VW_MACD_O"] = vw_ema_fast - vw_ema_slow

    # Calculate the signal EMA
    df["VW_Signal_O"] = df["VW_MACD"].ewm(min_periods=n_signal, alpha=alpha_signal).mean()

    # Calculate the histogram
    df["VW_Histogram_O"] = df["VW_MACD_O"] - df["VW_Signal_O"]

    return df


# 8) Volume Weighted Moving Average Convergence Divergence (MACD) of OHLC:
def VW_MACD_OHLC(df: pd.DataFrame, n_fast=12, n_slow=26, n_signal=9):
    """
    Volume Weighted Moving Average Convergence Divergence of OHLC (Fast EMA: 12 Period | Slow EMA: 26 Period | Signal Line EMA: 9 Period)

    Args:
        df (pd.DataFrame): The DataFrame containing the OHLCV data.
        n_fast (int, optional): The number of periods for the fast EMA. Defaults to 12.
        n_slow (int, optional): The number of periods for the slow EMA. Defaults to 26.
        n_signal (int, optional): The number of periods for the signal EMA. Defaults to 9.

    Returns:
        pd.DataFrame: The DataFrame with the MACD, Signal, and Histogram columns added.
    """

    alpha_fast = 1.0 / n_fast
    alpha_slow = 1.0 / n_slow
    alpha_signal = 1.0 / n_signal
    
    # Calculate the typical price
    typical_price = (df["Mid_Open"] + df["Mid_High"] + df["Mid_Low"] + df["Mid_Close"]) / 4

    # Calculate the typical price volume
    tp_vol = typical_price * df["Volume"]

    # Calculate the fast EMA
    tp_vol_ema_fast = tp_vol.ewm(min_periods=n_fast, alpha=alpha_fast).mean()

    # Calculate the slow EMA
    tp_vol_ema_slow = tp_vol.ewm(min_periods=n_slow, alpha=alpha_slow).mean()

    # Calculate the Fast and Slow EMA of the volume
    vol_ema_fast = df["Volume"].ewm(min_periods=n_fast, alpha=alpha_fast).mean()
    vol_ema_slow = df["Volume"].ewm(min_periods=n_slow, alpha=alpha_slow).mean()

    # Calculate the Volume Weighted EMAs of Fast and Slow EMA
    vw_ema_fast = tp_vol_ema_fast / vol_ema_fast
    vw_ema_slow = tp_vol_ema_slow / vol_ema_slow

    # Calculate the MACD
    df["VW_MACD_OHLC"] = vw_ema_fast - vw_ema_slow

    # Calculate the signal EMA
    df["VW_Signal_OHLC"] = df["VW_MACD_OHLC"].ewm(min_periods=n_signal, alpha=alpha_signal).mean()

    # Calculate the histogram
    df["VW_Histogram_OHLC"] = df["VW_MACD_OHLC"] - df["VW_Signal_OHLC"]

    return df


# 8) Volume Weighted Moving Average Convergence Divergence (MACD) of High Low:
def VW_MACD_HL(df: pd.DataFrame, n_fast=12, n_slow=26, n_signal=9):
    """
    Volume Weighted Moving Average Convergence Divergence of High Low (Fast EMA: 12 Period | Slow EMA: 26 Period | Signal Line EMA: 9 Period)

    Args:
        df (pd.DataFrame): The DataFrame containing the OHLCV data.
        n_fast (int, optional): The number of periods for the fast EMA. Defaults to 12.
        n_slow (int, optional): The number of periods for the slow EMA. Defaults to 26.
        n_signal (int, optional): The number of periods for the signal EMA. Defaults to 9.

    Returns:
        pd.DataFrame: The DataFrame with the MACD, Signal, and Histogram columns added.
    """

    alpha_fast = 1.0 / n_fast
    alpha_slow = 1.0 / n_slow
    alpha_signal = 1.0 / n_signal
    
    # Calculate the typical price
    mid_point = (df["Mid_High"] + df["Mid_Low"]) / 2

    # Calculate the typical price volume
    mp_vol = mid_point * df["Volume"]

    # Calculate the fast EMA
    mp_vol_ema_fast = mp_vol.ewm(min_periods=n_fast, alpha=alpha_fast).mean()

    # Calculate the slow EMA
    mp_vol_ema_slow = mp_vol.ewm(min_periods=n_slow, alpha=alpha_slow).mean()

    # Calculate the Fast and Slow EMA of the volume
    vol_ema_fast = df["Volume"].ewm(min_periods=n_fast, alpha=alpha_fast).mean()
    vol_ema_slow = df["Volume"].ewm(min_periods=n_slow, alpha=alpha_slow).mean()

    # Calculate the Volume Weighted EMAs of Fast and Slow EMA
    vw_ema_fast = mp_vol_ema_fast / vol_ema_fast
    vw_ema_slow = mp_vol_ema_slow / vol_ema_slow

    # Calculate the MACD
    df["VW_MACD_HL"] = vw_ema_fast - vw_ema_slow

    # Calculate the signal EMA
    df["VW_Signal_HL"] = df["VW_MACD_HL"].ewm(min_periods=n_signal, alpha=alpha_signal).mean()

    # Calculate the histogram
    df["VW_Histogram_HL"] = df["VW_MACD_HL"] - df["VW_Signal_HL"]

    return df


# 9) Impulse Moving Average Convergence Divergence (Impulse_MACD):
def Impulse_MACD(df: pd.DataFrame, length_ma=34, length_signal=9):
    """
    Calculates Impulse MACD values and colors.
    This is the main function. It takes a DataFrame (df) containing OHLC (Open, High, Low, Close) data as input, along with optional parameters for the length of the moving averages (length_ma) and the length of the signal line (length_signal). 
    - It determines the color of bars (mdc) based on the comparison between the close price and mi, hi, and lo.
    - It returns a DataFrame containing the calculated values.
    """
    # Calculate the typical price (src) from the high, low, and close prices.
    src = (df["Mid_High"] + df["Mid_Low"] + df["Mid_Close"]) / 3
    
    # Compute the SMMA for the high and low prices (hi and lo) and the ZLEMA for the typical price (mi).
    hi = df["Mid_High"].rolling(window=length_ma, min_periods=1).mean()
    lo = df["Mid_Low"].rolling(window=length_ma, min_periods=1).mean()
    ema1 = src.ewm(span=length_ma, adjust=False).mean()
    ema2 = ema1.ewm(span=length_ma, adjust=False).mean()
    d = ema1 - ema2
    mi = ema1 + d
    
    # Compute the MACD-like value (md) based on the comparison between mi, hi, and lo.
    df["ImpulseMACD"] = np.where(mi > hi, mi - hi, np.where(mi < lo, mi - lo, 0))

    # Calculate the signal line df["ImpulseMACDSignal"] by taking the moving average of df["ImpulseMACD"].
    df["ImpulseMACDSignal"] = df["ImpulseMACD"].rolling(window=length_signal, min_periods=1).mean()

    # Compute the histogram df["ImpulseHistogram"] by subtracting the signal line df["ImpulseMACDSignal"] from df["ImpulseMACD"].
    df["ImpulseHistogram"] = df["ImpulseMACD"] - df["ImpulseMACDSignal"]
    
    # Determine the colour of bars df["BarColour"] based on the comparison between the close price and mi, hi, and lo.
    df["BarColour"] = np.where(df["Mid_Close"] > mi,
                      np.where(df["Mid_Close"] > hi, "lime", "green"),
                      np.where(df["Mid_Close"] < lo, "red", "orange"))
    
    return df

# Plotting of Impulse_MACD
def Plot_Impulse_MACD(df: pd.DataFrame):
    """
    Plots Impulse MACD values and histogram
    """
    plt.figure(figsize=(20, 10))
    plt.plot(df.index, df["ImpulseMACD"], label="Impulse MACD", color="blue")
    plt.plot(df.index, df["ImpulseMACDSignal"], label="Signal Line", color="red", linestyle="--")
    plt.bar(df.index, df["ImpulseHistogram"], label="Histogram", color=df["BarColour"])
    plt.title("Impulse MACD")
    plt.legend()
    plt.show()


# 5) Volume Weighted Impulse Moving Average Convergence Divergence (VW_Impulse_MACD):
def VW_Impulse_MACD(df: pd.DataFrame, length_ma=34, length_signal=9):
    """
    Calculates Impulse MACD values and colors.
    This is the main function. It takes a DataFrame (df) containing OHLC (Open, High, Low, Close) data as input, along with optional parameters for the length of the moving averages (length_ma) and the length of the signal line (length_signal). 
    - It determines the color of bars (mdc) based on the comparison between the close price and mi, hi, and lo.
    - It returns a DataFrame containing the calculated values.
    """
    # Calculate the typical price (src) from the high, low, and close prices.
    src = ((df["Mid_High"] * df["Volume"]) + (df["Mid_Low"] * df["Volume"]) + (df["Mid_Close"] * df["Volume"])) / 3
    vw_src = src / df["Volume"]
    
    # Compute the SMMA for the high and low prices (hi and lo).
    hi_vol = df["Mid_High"] * df["Volume"]
    hi = hi_vol.rolling(window=length_ma, min_periods=1).mean()

    lo_vol = df["Mid_Low"] * df["Volume"]
    lo = lo_vol.rolling(window=length_ma, min_periods=1).mean()

    vol = df["Volume"].rolling(window=length_ma, min_periods=1).mean()

    vw_hi = hi / vol
    vw_lo = lo / vol

    # Compute the ZLEMA for the typical price (mi).
    ema1 = vw_src.ewm(span=length_ma, adjust=False).mean()
    ema2 = ema1.ewm(span=length_ma, adjust=False).mean()
    d = ema1 - ema2
    vw_mi = ema1 + d
    
    # Compute the MACD-like value (md) based on the comparison between mi, hi, and lo.
    df["VW_ImpulseMACD"] = np.where(vw_mi > vw_hi, vw_mi - vw_hi, np.where(vw_mi < vw_lo, vw_mi - vw_lo, 0))

    # Calculate the signal line df["ImpulseMACDSignal"] by taking the moving average of df["ImpulseMACD"].
    df["VW_ImpulseMACDSignal"] = df["VW_ImpulseMACD"].rolling(window=length_signal, min_periods=1).mean()

    # Compute the histogram df["ImpulseHistogram"] by subtracting the signal line df["ImpulseMACDSignal"] from df["ImpulseMACD"].
    df["VW_ImpulseHistogram"] = df["VW_ImpulseMACD"] - df["VW_ImpulseMACDSignal"]
    
    # Determine the colour of bars df["BarColour"] based on the comparison between the close price and mi, hi, and lo.
    df["VW_BarColour"] = np.where(df["Mid_Close"] > vw_mi,
                      np.where(df["Mid_Close"] > vw_hi, "lime", "green"),
                      np.where(df["Mid_Close"] < vw_lo, "red", "orange"))
    
    return df

# Plotting of VW_Impulse_MACD
def Plot_VW_Impulse_MACD(df: pd.DataFrame):
    """
    Plots Volume Weighted Impulse MACD values and histogram
    """
    plt.figure(figsize=(20, 10))
    plt.plot(df.index, df["VW_ImpulseMACD"], label="Volume Weighted Impulse MACD", color="blue")
    plt.plot(df.index, df["VW_ImpulseMACDSignal"], label="Volume Weighted Signal Line", color="red", linestyle="--")
    plt.bar(df.index, df["VW_ImpulseHistogram"], label="Volume Weighted Histogram", color=df["VW_BarColour"])
    plt.title("Volume Weighted Impulse MACD")
    plt.legend()
    plt.show()


# Pivot Levels:
def PivotPoints(df: pd.DataFrame):
    """
    Pivot Levels    
    Use the VWHLCP PP Calculation for Day Trading
    Use the VWMA PP Calculation for Trading over 10 Days
    """
    pass


# Volume:
def Volume_SMA(df: pd.DataFrame, n=10):
    """
    Volume with n Period of SMA 
    """
    df[f"Volume_SMA{n}"] = df["Volume"].rolling(window=n).mean()

    return df

# 6) Historical Annual Volatility (HAV):
def HAV(df: pd.DataFrame, lookback: int = 2, price_source: str = "Mid_Close") -> pd.Series:
    """
    Historical Annual Volatility [Log(Curr_Close / Prev_Close): 2 Period]
    """
    log_returns = np.log(df[price_source] / df[price_source].shift(1))
    return log_returns.rolling(window=lookback).std() * np.sqrt(252)


def IAV(df: pd.DataFrame, lookback: int = 2) -> pd.Series:
    """
    IntraDay Annual Volatility [Log(High / Low): 2 Period]
    """
    log_returns = np.log(df["Mid_High"] / df["Mid_Low"])
    return log_returns.rolling(window=lookback).std() * np.sqrt(252)


def RAVI(df: pd.DataFrame, n_fast: int = 3, n_slow: int = 10) -> pd.Series:
    """
    The Range Action Verification Index (RAVI) is used to identify if the market is in a trend.
    It was developed by Tushar Chande.
    Use VM EMA and HLC Average
    """
    # Calculate the typical price (HLC average)
    typical_price = (df["Mid_High"] + df["Mid_Low"] + df["Mid_Close"]) / 3

    # Calculate fast and slow EMAs of the typical price
    ema_fast = typical_price.ewm(span=n_fast, adjust=False).mean()
    ema_slow = typical_price.ewm(span=n_slow, adjust=False).mean()

    # Calculate RAVI
    ravi = 100 * (ema_fast - ema_slow) / ema_slow
    return ravi


def VW_RAVI(df: pd.DataFrame, n_fast: int = 3, n_slow: int = 10) -> pd.Series:
    """
    The Range Action Verification Index (RAVI) is used to identify if the market is in a trend.
    It was developed by Tushar Chande.
    Use VM EMA and HLC Average
    """
    # Calculate the typical price (HLC average)
    typical_price = (df["Mid_High"] + df["Mid_Low"] + df["Mid_Close"]) / 3

    # Calculate volume-weighted typical price
    vw_typical_price = typical_price * df["Volume"]

    # Calculate fast and slow EMAs of the volume-weighted typical price and volume
    vw_ema_fast_num = vw_typical_price.ewm(span=n_fast, adjust=False).mean()
    vw_ema_fast_den = df["Volume"].ewm(span=n_fast, adjust=False).mean()
    vw_ema_fast = vw_ema_fast_num / vw_ema_fast_den

    vw_ema_slow_num = vw_typical_price.ewm(span=n_slow, adjust=False).mean()
    vw_ema_slow_den = df["Volume"].ewm(span=n_slow, adjust=False).mean()
    vw_ema_slow = vw_ema_slow_num / vw_ema_slow_den

    # Calculate Volume Weighted RAVI
    vw_ravi = 100 * (vw_ema_fast - vw_ema_slow) / vw_ema_slow
    return vw_ravi


import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# 1) Bollinger Bands Using OHLC Average:
def BollingerBands_OHLC(df: pd.DataFrame, n=20, sd=2):
    """
    Function to calculate Bollinger Bands for a given dataframe.
    
    Parameters:
    df (pd.DataFrame): Input dataframe with columns "Mid_Open", "Mid_High", "Mid_Low", "Mid_Close".
    n (int): The number of periods for smoothing (default is 20).
    sd (int): The number of standard deviations for upper and lower band (default is 2).
    
    Returns:
    df (pd.DataFrame): Dataframe with added columns "BB_SMA{n}", "BB_Upper", "BB_Lower" representing 
                       the Bollinger Bands.
    """
    # Calculate the typical price
    typical_price = (df["Mid_Open"] + df["Mid_High"] + df["Mid_Low"] + df["Mid_Close"]) / 4
    
    # Calculate the standard deviation of the typical price
    stddev = typical_price.rolling(window=n).std()
    
    # Calculate the Simple Moving Average (SMA) of the typical price
    df[f"BB_SMA{n}"] = typical_price.rolling(window=n).mean()
    
    # Calculate the upper Bollinger Band
    df["BB_Upper"] = df[f"BB_SMA{n}"] + (sd * stddev)
    
    # Calculate the lower Bollinger Band
    df["BB_Lower"] = df[f"BB_SMA{n}"] - (sd * stddev)
    
    return df


# 2) Volume Weighted Bollinger Bands Using OHLC Average:
def VW_BollingerBands_OHLC(df: pd.DataFrame, n=20, sd=2):
    """
    Function to calculate Volume Weighted Bollinger Bands using OHLC (Open, High, Low, Close) Average.
    
    Parameters:
    df (pd.DataFrame): DataFrame containing the stock data
    n (int): The period for SMA calculation. Default is 20.
    sd (int): The standard deviation for the Bollinger Bands. Default is 2.
    
    Returns:
    df (pd.DataFrame): DataFrame with the calculated Bollinger Bands added as new columns.
    """
    
    # Calculate the typical price by taking the average of mid open, mid high, mid low and mid close prices
    typical_price = (df["Mid_Open"] + df["Mid_High"] + df["Mid_Low"] + df["Mid_Close"]) / 4
    
    # Multiply the typical price with the volume
    tp_vol = typical_price * df["Volume"]
    
    # Calculate the Simple Moving Average (SMA) of the typical price volume
    tp_vol_sma = tp_vol.rolling(window=n).mean()
    
    # Calculate the SMA of the volume
    vol_sma = df["Volume"].rolling(window=n).mean()
    
    # Calculate the Volume Weighted SMA and add it as a new column to the DataFrame
    df[f"VW_BB_SMA{n}"] = tp_vol_sma / vol_sma
    
    # Calculate the standard deviation of the Volume Weighted SMA
    stddev = df[f"VW_BB_SMA{n}"].rolling(window=n).std()
    
    # Calculate the upper Bollinger Band and add it as a new column to the DataFrame
    df["VW_BB_Upper"] = df[f"VW_BB_SMA{n}"] + (sd * stddev)
    
    # Calculate the lower Bollinger Band and add it as a new column to the DataFrame
    df["VW_BB_Lower"] = df[f"VW_BB_SMA{n}"] - (sd * stddev)
    
    return df

# 3) Volume Weighted Bollinger Bands Using High-Low Midpoint:
def VW_BollingerBands_HL(df: pd.DataFrame, n=20, sd=2):
    """
    Volume Weighted Bollinger Bands Using High-Low Midpoint (SMA: 20 Period | Standard Deviation: 2)

    Args:
        df (pd.DataFrame): The DataFrame containing the candlestick data
        n (int, optional): The period for the moving average. Defaults to 20.
        sd (int, optional): The number of standard deviations to use for the Bollinger Bands. Defaults to 2.

    Returns:
        pd.DataFrame: The DataFrame with the Bollinger Bands columns added
    """

    # Calculate the midpoint of the high and low prices
    mid_point = (df["Mid_High"] + df["Mid_Low"]) / 2

    # Calculate the volume weighted moving average of the midpoints
    mp_vol = mid_point * df["Volume"]
    mp_vol_sma = mp_vol.rolling(window=n).mean()

    # Calculate the moving average of the volume
    vol_sma = df["Volume"].rolling(window=n).mean()

    # Calculate the Volume Weighted Bollinger Bands
    df[f"VW_BB_HL_SMA{n}"] = mp_vol_sma / vol_sma

    # Calculate the standard deviation of the Volume Weighted Bollinger Bands
    stddev = df[f"VW_BB_HL_SMA{n}"].rolling(window=n).std()

    # Calculate the upper and lower bands
    df["VW_BB_HL_Upper"] = df[f"VW_BB_HL_SMA{n}"] + (sd * stddev)
    df["VW_BB_HL_Lower"] = df[f"VW_BB_HL_SMA{n}"] - (sd * stddev)

    return df


# 4) Volume Weighted Bollinger BandWidth High-Low Midpoint:
def VW_BollingerBandWidth_HL(df: pd.DataFrame, n=20, sd=2, bbwsma=10):
    """
    Volume Weighted Bollinger Band Width Using High-Low Midpoint (SMA: 20 Period | Standard Deviation: 2)

    Args:
        df (pd.DataFrame): Dataframe containing the data for which to calculate the Volume Weighted Bollinger Band Width
        n (int, optional): The period used to calculate the Bollinger Band (default is 20)
        sd (int, optional): The standard deviation used to calculate the Bollinger Band (default is 2)
        bbwsma (int, optional): The period used to calculate the VW BBW SMA (default is 10)

    Returns:
        pd.DataFrame: Dataframe with the calculated Volume Weighted Bollinger Band Width
    """

    # Calculate the midpoint of the high and low prices
    mid_point = (df["Mid_High"] + df["Mid_Low"]) / 2

    # Calculate the volume weighted moving average of the midpoint
    mp_vol = mid_point * df["Volume"]
    mp_vol_sma = mp_vol.rolling(window=n).mean()

    # Calculate the simple moving average of the volume
    vol_sma = df["Volume"].rolling(window=n).mean()

    # Calculate the Volume Weighted Bollinger Band SMA
    df[f"VW_BB_HL_SMA{n}"] = mp_vol_sma / vol_sma

    # Calculate the standard deviation of the Volume Weighted Bollinger Band SMA
    stddev = df[f"VW_BB_HL_SMA{n}"].rolling(window=n).std()

    # Calculate the upper and lower Bollinger Bands
    df["VW_BB_HL_Upper"] = df[f"VW_BB_HL_SMA{n}"] + (sd * stddev)
    df["VW_BB_HL_Lower"] = df[f"VW_BB_HL_SMA{n}"] - (sd * stddev)

    # Calculate the Volume Weighted Bollinger Band Width
    df["VW_BBW"] = (df["VW_BB_HL_Upper"] - df["VW_BB_HL_Lower"]) / df[f"VW_BB_HL_SMA{n}"]

    # Calculate the Volume Weighted Bollinger Band Width SMA
    df[f"VW_BBW_SMA{bbwsma}"] = df["VW_BBW"].rolling(window=bbwsma).mean()

    # Return the calculated Volume Weighted Bollinger Band Width
    return df


# 5) Volume Weighted Standard Deviation Using High-Low Midpoint:
def VW_StandardDeviation_HL(df: pd.DataFrame, n=20, sdsma=10, period=10):
    """
    Volume Weighted Standard Deviation Using High-Low Midpoint (EMA: 20 Period | Standard Deviation: 2)

    Formula:
    1) Calculate Mid-Point Price = (High + Low) / 2
    2) Calculate Volume Weighted Mid-Point Price = Mid-Point Price * Volume
    3) Calculate VW HL EMA = Volume Weighted Mid-Point Price n-period EMA / Volume n-period EMA
    4) Calculate VW Standard Deviation n = n-period Standard Deviation of VW HL EMA
    5) Calculate Smoothing VW Standard Deviation n = n-period Simple Moving Average of VW Standard Deviation n

    Args:
        df (pd.DataFrame): DataFrame containing historical OHLCV data
        n (int): Number of periods for EMA calculation (default: 20)
        sdsma (int): Number of periods for Smoothing VW Standard Deviation (default: 10)

    Returns:
        pd.DataFrame: DataFrame with added columns for VW Standard Deviation and its SMA
    """

    # Define the smoothing factor for the exponential moving average (EMA)
    alpha = 1.0 / n

    # Calculate the midpoint of the high and low prices
    mid_point = (df["Mid_High"] + df["Mid_Low"]) / 2

    # Calculate the volume weighted moving average of the midpoint
    mp_vol = mid_point * df["Volume"]
    mp_vol_ema = mp_vol.ewm(min_periods=n, alpha=alpha).mean()

    # Calculate the simple moving average of the volume
    vol_ema = df["Volume"].ewm(min_periods=n, alpha=alpha).mean()

    # Calculate the Volume Weighted SMA of HL Midpoint
    vw_hl = mp_vol_ema / vol_ema
    
    # Calculate VW Standard Deviation n
    df[f"VW_SD{n}"] = vw_hl.ewm(min_periods=n, alpha=alpha).std()

    # Calculate Smoothing VW Standard Deviation n
    df[f"VW_SD{n}_SMA{sdsma}"] = df[f"VW_SD{n}"].rolling(window=sdsma).mean()

    # Calculate the max and min values of VW Standard Deviation
    df[f"VW_SD_Max{period}"] = df[f"VW_SD{n}"].rolling(window=period).max()
    df[f"VW_SD_Min{period}"] = df[f"VW_SD{n}"].rolling(window=period).min()

    return df


# 6) Average True Range (ATR) with SMA of ATR:
def ATR(df: pd.DataFrame, n=14, atrsma=10):
    """
    Average True Range with SMA (IntraDay: 8 Period | Positional: 20 Period)

    Args:
        df (pd.DataFrame): The dataframe containing the candlestick data
        n (int, optional): The period for calculating the ATR. Defaults to 14.
        atrsma (int, optional): The period for calculating the SMA of the ATR. Defaults to 10.

    Returns:
        pd.DataFrame: The dataframe with the ATR and ATR_SMA columns
    """

    # Calculate the previous close price
    prev_Close = df["Mid_Close"].shift(1)

    # Calculate the true range using three different methods
    true_range_1 = (df["Mid_High"] - df["Mid_Low"])
    true_range_2 = abs(df["Mid_High"] - prev_Close)
    true_range_3 = abs(df["Mid_Low"] - prev_Close)

    # Find the maximum of the three true range values
    true_range = pd.DataFrame({"TrueRange_1": true_range_1, "TrueRange_2": true_range_2, "TrueRange_3": true_range_3}).max(axis=1)

    # Calculate the n-period ATR
    df[f"ATR{n}"] = true_range.rolling(window=n).mean()

    # Calculate the atrsma-period SMA of the ATR
    df[f"ATR{n}_SMA{atrsma}"] = df[f"ATR{n}"].rolling(window=atrsma).mean()

    # Return the dataframe with the ATR and ATR_SMA columns
    return df


# 5) Volume Weighted Average True Range (ATR) with SMA of ATR:
def VW_ATR(df: pd.DataFrame, n=14, atrsma=10):
    """
    Calculate the Volume Weighted Average True Range (VW ATR) and its Smoothed Moving Average (SMA).
    
    Parameters:
    df (pd.DataFrame): Input dataframe with columns ["Mid_Close", "Mid_High", "Mid_Low", "Volume"]
    n (int, optional): Number of periods for EMA calculation. Default is 14.
    atrsma (int, optional): Number of periods for SMA calculation. Default is 10.
    
    Returns:
    pd.DataFrame: Dataframe with added VW ATR and VW ATR SMA columns.
    
    References:
    https://www.macroption.com/normalized-atr/
    """

    # Calculate True Range
    # Shift the 'Mid_Close' column down by one row to get the previous close prices
    prev_Close = df["Mid_Close"].shift(1)
    # Calculate the difference between the high and low prices
    true_range_1 = (df["Mid_High"] - df["Mid_Low"])
    # Calculate the absolute difference between the high price and the previous close price
    true_range_2 = abs(df["Mid_High"] - prev_Close)
    # Calculate the absolute difference between the low price and the previous close price
    true_range_3 = abs(df["Mid_Low"] - prev_Close)
    # Get the maximum value among the three true ranges for each row
    true_range = pd.DataFrame({"TrueRange_1": true_range_1, "TrueRange_2": true_range_2, "TrueRange_3": true_range_3}).max(axis=1)

    # Calculate Volume Weighted Average True Range (VW ATR)
    # Define the smoothing factor for the exponential moving average (EMA)
    alpha = 1.0 / n
    # Multiply the true range by the volume to get the volume-weighted true range
    tr_vol = true_range * df["Volume"]
    # Calculate the EMA of the volume-weighted true range
    tr_vol_ema = tr_vol.ewm(min_periods=n, alpha=alpha).mean()
    # Calculate the EMA of the volume
    vol_ema = df["Volume"].ewm(min_periods=n, alpha=alpha).mean()
    # Divide the EMA of the volume-weighted true range by the EMA of the volume to get the VW ATR
    df[f"VW_ATR{n}"] = tr_vol_ema / vol_ema

    # Calculate Volume Weighted Average True Range Smoothed Moving Average (VW ATR SMA)
    # Multiply the VW ATR by the volume to get the volume-weighted VW ATR
    atr_vol = df[f"VW_ATR{n}"] * df["Volume"]
    # Calculate the simple moving average (SMA) of the volume-weighted VW ATR
    atr_vol_sma = atr_vol.rolling(window=atrsma).mean()
    # Calculate the SMA of the volume
    vol_sma = df["Volume"].rolling(window=atrsma).mean()
    # Divide the SMA of the volume-weighted VW ATR by the SMA of the volume to get the VW ATR SMA
    df[f"VW_ATR{n}_SMA{atrsma}"] = atr_vol_sma / vol_sma

    return df


# 12) Volume Weighted Average True Range Percent (ATRP) with SMA of ATRP:
def VW_ATRP(df: pd.DataFrame, n=14, atrsma=10):
    """
    Calculate the Volume Weighted Average True Range Percent (ATRP) with Simple Moving Average (SMA) of Average True Range (ATR).
    
    Parameters:
    df (pd.DataFrame): Input dataframe with columns ["Mid_Close", "Mid_High", "Mid_Low", "Volume"]
    n (int): The number of periods for exponential moving average calculation. Default is 14.
    atrsma (int): The number of periods for simple moving average calculation. Default is 10.
    
    Returns:
    pd.DataFrame: Dataframe with added VW_ATR, VW_ATRP and VW_ATRP_SMA columns.
    
    References:
    - https://traders.com/Documentation/FEEDbk_docs/2006/05/Abstracts_new/Forman/formn.html
    - https://www.macroption.com/normalized-atr/
    """

    # Calculate alpha
    alpha = 1.0 / n

    # Calculate True Range
    prev_Close = df["Mid_Close"].shift(1)
    true_range_1 = (df["Mid_High"] - df["Mid_Low"])
    true_range_2 = abs(df["Mid_High"] - prev_Close)
    true_range_3 = abs(df["Mid_Low"] - prev_Close)
    true_range = pd.DataFrame({"TrueRange_1": true_range_1, "TrueRange_2": true_range_2, "TrueRange_3": true_range_3}).max(axis=1)

    # Calculate Volume Weighted Average True Range (VW_ATR)
    tr_vol = true_range * df["Volume"]
    tr_vol_ema = tr_vol.ewm(min_periods=n, alpha=alpha).mean()
    vol_ema = df["Volume"].ewm(min_periods=n, alpha=alpha).mean()
    df[f"VW_ATR{n}"] = tr_vol_ema / vol_ema

    # Calculate Volume Weighted Average True Range Percent (VW_ATRP)
    df[f"VW_ATRP{n}"] = df[f"VW_ATR{n}"] / df["Mid_Close"] * 100

    # Calculate Simple Moving Average (SMA) of VW_ATRP
    atrp_vol = df[f"VW_ATRP{n}"] * df["Volume"]
    atrp_vol_sma = atrp_vol.rolling(window=atrsma).mean()
    vol_sma = df["Volume"].rolling(window=atrsma).mean()
    df[f"VW_ATRP{n}_SMA{atrsma}"] = atrp_vol_sma / vol_sma

    return df

# 6) Volume Weighted Normalised Average True Range Percent (NATRP) with SMA of NATRP:
def Normalised_VW_ATRP(df: pd.DataFrame, n=14, atrsma=10):
    """
    This function calculates the Volume Weighted Normalised Average True Range Percent (NATRP) with SMA of NATRP.
    
    Parameters:
    df (pd.DataFrame): The input dataframe with the stock data.
    n (int): The period for the exponential moving average calculation. Default is 14.
    atrsma (int): The period for the simple moving average calculation. Default is 10.
    
    Returns:
    df (pd.DataFrame): The dataframe with the added columns for Normalised VW ATRP and Normalised VW ATRP with SMA.
    
    References:
    https://www.macroption.com/normalized-atr/
    """
    # Define the alpha for the exponential moving average
    alpha = 1.0 / n

    # Calculate True Range
    # Shift the 'Mid_Close' column down by one row to get the previous close prices
    prev_Close = df["Mid_Close"].shift(1)
    # Calculate the difference between the high and low prices
    true_range_1 = (df["Mid_High"] - df["Mid_Low"])
    # Calculate the absolute difference between the high price and the previous close price
    true_range_2 = abs(df["Mid_High"] - prev_Close)
    # Calculate the absolute difference between the low price and the previous close price
    true_range_3 = abs(df["Mid_Low"] - prev_Close)
    # Get the maximum value among the three true ranges for each row
    true_range = pd.DataFrame({"TrueRange_1": true_range_1, "TrueRange_2": true_range_2, "TrueRange_3": true_range_3}).max(axis=1)

    # Calculate the normalised true range
    norm_true_range = true_range / df["Mid_Close"] * 100

    # Calculate the normalised true range volume
    norm_tr_vol = norm_true_range * df["Volume"]

    # Calculate the exponential moving average of the normalised true range volume
    norm_tr_vol_ema = norm_tr_vol.ewm(min_periods=n, alpha=alpha).mean()

    # Calculate the exponential moving average of the volume
    vol_ema = df["Volume"].ewm(min_periods=n, alpha=alpha).mean()

    # Calculate the Normalised VW ATRP
    df[f"Norm_VW_ATRP{n}"] = norm_tr_vol_ema / vol_ema

    # Calculate the volume of the Normalised VW ATRP
    n_atrp_vol = df[f"Norm_VW_ATRP{n}"] * df["Volume"]

    # Calculate the simple moving average of the volume of the Normalised VW ATRP
    n_atrp_vol_sma = n_atrp_vol.rolling(window=atrsma).mean()

    # Calculate the simple moving average of the volume
    vol_sma = df["Volume"].rolling(window=atrsma).mean()

    # Calculate the Normalised VW ATRP with SMA
    df[f"Norm_VW_ATRP{n}_SMA{atrsma}"] = n_atrp_vol_sma / vol_sma

    return df


# 13) Keltner Channels Using OHLC Average:
def KeltnerChannels(df: pd.DataFrame, n=20, atr=14, num=2):
    """
    Function to calculate Keltner Channels using OHLC Average.
    
    Parameters:
    df (pd.DataFrame): Input dataframe with OHLC data.
    n (int, optional): Period for EMA calculation. Default is 20.
    atr (int, optional): Period for ATR calculation. Default is 14.
    num (int, optional): Multiplier for ATR in Keltner Channel calculation. Default is 2.
    
    Returns:
    df (pd.DataFrame): Dataframe with added Keltner Channel data.
    
    Note:
    EMA: Exponential Moving Average
    ATR: Average True Range
    OHLC: Open, High, Low, Close
    """
    # Calculate Typical Price
    typical_price = (df["Mid_Open"] + df["Mid_High"] + df["Mid_Low"] + df["Mid_Close"]) / 4

    # Calculate EMA of Typical Price
    df[f"KC_EMA{n}"] = typical_price.ewm(span=n, min_periods=n).mean()

    # Calculate Average True Range (ATR)
    df = ATR(df, n=atr)

    # Calculate Upper and Lower Keltner Channels
    df["KC_Upper"] = df[f"KC_EMA{n}"] + (num * df[f"ATR{atr}"])
    df["KC_Lower"] = df[f"KC_EMA{n}"] - (num * df[f"ATR{atr}"])

    return df


# 14) Volume Weighted Keltner Channels Using OHLC Average:
def VW_KeltnerChannels(df: pd.DataFrame, n=20, atr=14, num=2):
    """
    Function to calculate Volume Weighted Keltner Channels using OHLC Average.
    
    Parameters:
    df (pd.DataFrame): Input dataframe with OHLC (Open, High, Low, Close) data.
    n (int): The time period for EMA calculation. Default is 20.
    atr (int): The time period for ATR calculation. Default is 14.
    num (int): The multiplier for ATR to calculate the upper and lower Keltner Channels. Default is 2.
    
    Returns:
    df (pd.DataFrame): Output dataframe with added columns for EMA, ATR, upper and lower Keltner Channels.
    """
    # Calculate the typical price
    typical_price = (df["Mid_Open"] + df["Mid_High"] + df["Mid_Low"] + df["Mid_Close"]) / 4
    # Calculate the volume weighted typical price
    tp_vol = typical_price * df["Volume"]
    # Calculate the EMA of the volume weighted typical price
    tp_vol_ema = tp_vol.ewm(span=n, min_periods=n).mean()
    # Calculate the EMA of the volume
    vol_ema = df["Volume"].ewm(span=n, min_periods=n).mean()
    # Calculate the volume weighted EMA
    df[f"VW_KC_EMA{n}"] = tp_vol_ema / vol_ema
    # Calculate the ATR
    df = VW_ATR(df, n=atr)
    # Calculate the upper Keltner Channel
    df["VW_KC_Upper"] = df[f"VW_KC_EMA{n}"] + (num * df[f"VW_ATR{atr}"])
    # Calculate the lower Keltner Channel
    df["VW_KC_Lower"] = df[f"VW_KC_EMA{n}"] - (num * df[f"VW_ATR{atr}"])
    return df


# 15) Volume Weighted Keltner Channels Using OHLC Average and SMA of ATR:
def VW_KeltnerChannels_SMA(df: pd.DataFrame, n=20, atr=14, atrsma=10, num=2):
    """
    Calculate the Volume Weighted Keltner Channels using OHLC Average and SMA of ATR.

    Parameters:
    df (pd.DataFrame): Input dataframe with OHLC (Open, High, Low, Close) data and Volume.
    n (int): The period for the SMA calculation. Default is 20.
    atr (int): The period for the ATR calculation. Default is 14.
    atrsma (int): The period for the SMA of ATR calculation. Default is 10.
    num (int): The multiplier for the ATR to calculate the upper and lower Keltner Channels. Default is 2.

    Returns:
    df (pd.DataFrame): Output dataframe with added columns for VW_KC_SMA, VW_KC_SMA_Upper, and VW_KC_SMA_Lower.

    """

    # Calculate the typical price
    typical_price = (df["Mid_Open"] + df["Mid_High"] + df["Mid_Low"] + df["Mid_Close"]) / 4

    # Calculate the typical price volume
    tp_vol = typical_price * df["Volume"]

    # Calculate the EMA of the typical price volume
    tp_vol_ema = tp_vol.ewm(span=n, min_periods=n).mean()

    # Calculate the SMA of the volume
    vol_ema = df["Volume"].ewm(span=n, min_periods=n).mean()

    # Calculate the Volume Weighted Keltner Channel EMA
    df[f"VW_KC_EMA{n}"] = tp_vol_ema / vol_ema

    # Calculate the VW ATR
    df = VW_ATR(df, n=atr)

    # Calculate the upper Keltner Channel SMA
    df["VW_KC_SMA_Upper"] = df[f"VW_KC_EMA{n}"] + (num * df[f"VW_ATR{atr}_SMA{atrsma}"])

    # Calculate the lower Keltner Channel SMA
    df["VW_KC_SMA_Lower"] = df[f"VW_KC_EMA{n}"] - (num * df[f"VW_ATR{atr}_SMA{atrsma}"])

    return df


# 2) Volume Weighted Keltner Channels Using High-Low Midpoint and SMA of ATR:
def VW_KeltnerChannels_HL_SMA(df: pd.DataFrame, n=20, atr=14, atrsma=10, num=2):
    """
    Volume Weighted Keltner Channels Using High-Low Midpoint and SMA of ATR (SMA: 20 Period | IntraDay ATR: 8 Period | Positional ATR: 21 Period)

    Args:
        df (pd.DataFrame): The DataFrame containing the candlestick data
        n (int, optional): The period for the moving average. Defaults to 20.
        atr (int, optional): The period for the Average True Range. Defaults to 14.
        atrsma (int, optional): The period for the moving average of ATR. Defaults to 10.
        num (int, optional): The multiple of ATR to use for the Keltner Channels. Defaults to 2.

    Returns:
        pd.DataFrame: The DataFrame with the Keltner Channels columns added
    """

    # Calculate the mid-point of the high and low prices
    mid_point = (df["Mid_High"] + df["Mid_Low"]) / 2

    # Calculate the volume-weighted mid-point
    mp_vol = mid_point * df["Volume"]

    # Calculate the n-period moving average of the volume-weighted mid-point
    mp_vol_ema = mp_vol.ewm(span=n, min_periods=n).mean()

    # Calculate the n-period moving average of the volume
    vol_ema = df["Volume"].ewm(span=n, min_periods=n).mean()

    # Calculate the VW Keltner Channel using High-Low Midpoint and SMA of ATR
    df[f"VW_KC_HL_EMA{n}"] = mp_vol_ema / vol_ema

    # Calculate the VW ATR
    df = VW_ATR(df, n=atr)

    # Calculate the upper and lower bands of the VW Keltner Channel
    df["VW_KC_HL_SMA_Upper"] = df[f"VW_KC_HL_EMA{n}"] + (num * df[f"VW_ATR{atr}_SMA{atrsma}"])
    df["VW_KC_HL_SMA_Lower"] = df[f"VW_KC_HL_EMA{n}"] - (num * df[f"VW_ATR{atr}_SMA{atrsma}"])

    return df


# 16) Relative Strength Index (RSI) Using Close and with SMA of RSI:
def RSI(df: pd.DataFrame, n=14, rsisma=10, period=10):
    """
    Calculates the Relative Strength Index (RSI) and its Simple Moving Average (SMA) for a given DataFrame.

    Parameters:
    df (pd.DataFrame): The input DataFrame with a "Mid_Close" column representing closing prices.
    n (int, optional): The period for RSI calculation. Defaults to 14.
    rsisma (int, optional): The period for SMA calculation. Defaults to 10.
    period (int, optional): The look back period for calculating the maximum and minimum MFI values. Default is 10.

    Returns:
    pd.DataFrame: The input DataFrame with added columns for RSI and its SMA.
    """

    # Calculate alpha
    alpha = 1.0 / n

    # Calculate the price change
    price_change = df["Mid_Close"].diff()

    # Calculate the gain and loss
    gain = pd.Series([x if x >=0 else 0.0 for x in price_change], name="gain")
    loss = pd.Series([(x * -1) if x < 0 else 0.0 for x in price_change], name="loss")

    # Calculate the exponential weighted moving average of the gain and loss
    avgGain = gain.ewm(min_periods=n, alpha=alpha).mean()
    avgLoss = loss.ewm(min_periods=n, alpha=alpha).mean()

    # Calculate the relative strength
    rs = avgGain / avgLoss

    # Calculate the RSI
    df[f"RSI{n}"] = 100.0 - (100.0 / (1.0 + rs))

    # Calculate the SMA of the RSI
    df[f"RSI{n}_SMA{rsisma}"] = df[f"RSI{n}"].rolling(window=rsisma).mean()

    # Calculate the max and min values of Money Flow Index
    df[f"RSI_Max{period}"] = df[f"RSI{n}"].rolling(window=period).max()
    df[f"RSI_Min{period}"] = df[f"RSI{n}"].rolling(window=period).min()

    return df



# 18) Relative Strength Index (RSI) Using Open and with SMA of RSI:
def RSI_O(df: pd.DataFrame, n=14, rsisma=10, period=10):
    """
    Calculate the Relative Strength Index (RSI) using the opening price and apply a Simple Moving Average (SMA) to the RSI.

    Parameters:
    df (pd.DataFrame): Dataframe containing the stock data
    n (int, optional): The number of periods to consider for the RSI calculation. Default is 14.
    rsisma (int, optional): The number of periods to consider for the SMA calculation. Default is 10.
    period (int, optional): The look back period for calculating the maximum and minimum MFI values. Default is 10.

    Returns:
    df (pd.DataFrame): Dataframe with the calculated RSI and SMA values added as new columns.

    """
    # Calculate the alpha value
    alpha = 1.0 / n

    # Calculate the price change
    price_change = df["Mid_Open"].diff()

    # Calculate the gain and loss
    gain = pd.Series([x if x >=0 else 0.0 for x in price_change], name="gain")
    loss = pd.Series([(x * -1) if x < 0 else 0.0 for x in price_change], name="loss")

    # Calculate the average gain and loss
    avgGain = gain.ewm(min_periods=n, alpha=alpha).mean()
    avgLoss = loss.ewm(min_periods=n, alpha=alpha).mean()

    # Calculate the relative strength (RS)
    rs = avgGain / avgLoss

    # Calculate the RSI and add it to the dataframe
    df[f"RSI{n}_O"] = 100.0 - (100.0 / (1.0 + rs))

    # Calculate the SMA of the RSI and add it to the dataframe
    df[f"RSI{n}_O_SMA{rsisma}"] = df[f"RSI{n}_O"].rolling(window=rsisma).mean()

    # Calculate the max and min values of Money Flow Index
    df[f"RSI_O_Max{period}"] = df[f"RSI{n}_O"].rolling(window=period).max()
    df[f"RSI_O_Min{period}"] = df[f"RSI{n}_O"].rolling(window=period).min()

    return df


# 17) Relative Strength Index (RSI) Using OHLC Average and with SMA of RSI:
def RSI_OHLC(df: pd.DataFrame, n=14, rsisma=10, period=10):
    """
    Function to calculate the Relative Strength Index (RSI) using Open, High, Low, Close (OHLC) average and with Simple Moving Average (SMA) of RSI.
    
    Parameters:
    df (pd.DataFrame): Dataframe containing the OHLC data
    n (int, optional): The number of periods for which the RSI is calculated. Default is 14.
    rsisma (int, optional): The number of periods for the SMA of RSI. Default is 10.
    period (int, optional): The look back period for calculating the maximum and minimum MFI values. Default is 10.
    
    Returns:
    df (pd.DataFrame): Dataframe with the calculated RSI and SMA of RSI added as new columns.
    """
    # Calculate the alpha value
    alpha = 1.0 / n
    
    # Calculate the typical price
    typical_price = (df["Mid_Open"] + df["Mid_High"] + df["Mid_Low"] + df["Mid_Close"]) / 4
    
    # Calculate the price change
    price_change = typical_price.diff()
    
    # Calculate the gain and loss
    gain = pd.Series([x if x >=0 else 0.0 for x in price_change], name="gain")
    loss = pd.Series([(x * -1) if x < 0 else 0.0 for x in price_change], name="loss")
    
    # Calculate the average gain and loss
    avgGain = gain.ewm(min_periods=n, alpha=alpha).mean()
    avgLoss = loss.ewm(min_periods=n, alpha=alpha).mean()
    
    # Calculate the relative strength (RS)
    rs = avgGain / avgLoss
    
    # Calculate the RSI
    df[f"RSI{n}_OHLC"] = 100.0 - (100.0 / (1.0 + rs))
    
    # Calculate the SMA of RSI
    df[f"RSI{n}_OHLC_SMA{rsisma}"] = df[f"RSI{n}_OHLC"].rolling(window=rsisma).mean()

    # Calculate the max and min values of Money Flow Index
    df[f"RSI_OHLC_Max{period}"] = df[f"RSI{n}_OHLC"].rolling(window=period).max()
    df[f"RSI_OHLC_Min{period}"] = df[f"RSI{n}_OHLC"].rolling(window=period).min()
    
    return df


# 7) Relative Strength Index (RSI) Using High-Low Midpoint and with SMA of RSI:
def RSI_HL(df: pd.DataFrame, n=14, rsisma=10, period=10):
    """
    Relative Strength Index Using High-Low Midpoint and with SMA of RSI (14 Period)

    Args:
        df (pd.DataFrame): Pandas DataFrame with candlestick data
        n (int, optional): Period for RSI calculation. Defaults to 14.
        rsisma (int, optional): Period for smoothing RSI. Defaults to 10.
        period (int, optional): The look back period for calculating the maximum and minimum MFI values. Default is 10.

    Returns:
        pd.DataFrame: Pandas DataFrame with added RSI indicator
    """

    # Define the alpha for the exponential moving average
    alpha = 1.0 / n
    
    # Calculate mid point
    mid_point = (df["Mid_High"] + df["Mid_Low"]) / 2
    
    # Calculate price change
    price_change = mid_point.diff()

    # Calculate the Gain
    gain = pd.Series([x if x >=0 else 0.0 for x in price_change], name="gain")

    # Calculate Loss
    loss = pd.Series([(x * -1) if x < 0 else 0.0 for x in price_change], name="loss")

    # Calculate Average Gain
    avgGain = gain.ewm(min_periods=n, alpha=alpha).mean()

    # Calculate Average Loss
    avgLoss = loss.ewm(min_periods=n, alpha=alpha).mean()

    # Calculate RSI
    rs = avgGain / avgLoss
    df[f"RSI{n}_HL"] = 100.0 - (100.0 / (1.0 + rs))

    # Calculate the max and min values of RSI during the last n periods
    df[f"RSI_HL_Max{period}"] = df[f"RSI{n}_HL"].rolling(window=period).max()
    df[f"RSI_HL_Min{period}"] = df[f"RSI{n}_HL"].rolling(window=period).min()

    # Calculate the smoothed RSI
    df[f"RSI{n}_HL_SMA{rsisma}"] = df[f"RSI{n}_HL"].rolling(window=rsisma).mean()

    return df


# 19) Money Flow Index (MFI) Using Close and with SMA of MFI:
def MFI(df: pd.DataFrame, n=14, mfisma=10, period=10):
    """
    Calculates the Money Flow Index (MFI) and its Simple Moving Average (SMA) for a given DataFrame.

    Parameters:
    df (pd.DataFrame): The input DataFrame. It should contain columns "Mid_Close" and "Volume".
    n (int, optional): The period for the MFI calculation. Default is 14.
    mfisma (int, optional): The period for the SMA of MFI calculation. Default is 10.
    period (int, optional): The look back period for calculating the maximum and minimum MFI values. Default is 10.

    Returns:
    pd.DataFrame: The DataFrame with added MFI and MFI_SMA columns.

    """
    # Define the alpha for the exponential moving average
    alpha = 1.0 / n

    # Calculate the price change
    price_change = df["Mid_Close"].diff()
    
    # Calculate the gain and loss
    gain = pd.Series([x if x >=0 else 0.0 for x in price_change], name="gain")
    loss = pd.Series([(x * -1) if x < 0 else 0.0 for x in price_change], name="loss")
    
    # Calculate the gain volume and loss volume
    gain_vol = gain * df["Volume"]
    loss_vol = loss * df["Volume"]
    
    # Calculate the exponential moving average of gain volume and loss volume
    gain_vol_ema = gain_vol.ewm(min_periods=n, alpha=alpha).mean()
    loss_vol_ema = loss_vol.ewm(min_periods=n, alpha=alpha).mean()
    
    # Calculate the volume exponential moving average
    vol_ema = df["Volume"].ewm(min_periods=n, alpha=alpha).mean()
    
    # Calculate the average gain and average loss
    avgGain = gain_vol_ema / vol_ema
    avgLoss = loss_vol_ema / vol_ema
    
    # Calculate the relative strength
    rs = avgGain / avgLoss
    
    # Calculate the Money Flow Index
    df[f"MFI{n}"] = 100.0 - (100.0 / (1.0 + rs))
    
    # Calculate the simple moving average of Money Flow Index
    df[f"MFI{n}_SMA{mfisma}"] = df[f"MFI{n}"].rolling(window=mfisma).mean()

    # Calculate the max and min values of Money Flow Index
    df[f"MFI_Max{period}"] = df[f"MFI{n}"].rolling(window=period).max()
    df[f"MFI_Min{period}"] = df[f"MFI{n}"].rolling(window=period).min()
    
    return df



# 8) Money Flow Index (MFI) Using High-Low Midpoint and with SMA of MFI:
def MFI_HL(df: pd.DataFrame, n=14, mfisma=10, period=10):
    """
    Money Flow Index (Volume Weighted Relative Strength Index) Using High-Low Midpoint and with SMA of MFI (14 Period)

    Args:
        df (pd.DataFrame): Pandas DataFrame with candlestick data
        n (int, optional): Period for RSI calculation. Defaults to 14.
        mfisma (int, optional): Period for smoothing MFI. Defaults to 10.
        period (int, optional): The look back period for calculating the maximum and minimum MFI values. Default is 10.

    Returns:
        pd.DataFrame: Pandas DataFrame with added RSI indicator
    """
    # Calculate alpha
    alpha = 1.0 / n
    
    # Calculate mid point
    mid_point = (df["Mid_High"] + df["Mid_Low"]) / 2
    
    # Calculate price change
    price_change = mid_point.diff()
    
    # Calculate gain and gain volume
    gain = pd.Series([x if x >=0 else 0.0 for x in price_change], name="gain")
    gain_vol = gain * df["Volume"]
    gain_vol_ema = gain_vol.ewm(min_periods=n, alpha=alpha).mean()
    
    # Calculate loss and loss volume
    loss = pd.Series([(x * -1) if x < 0 else 0.0 for x in price_change], name="loss")
    loss_vol = loss * df["Volume"]
    loss_vol_ema = loss_vol.ewm(min_periods=n, alpha=alpha).mean()
    
    # Calculate relative strength
    rs = gain_vol_ema / loss_vol_ema
    
    # Add MFI_HL and MFI_HL_SMA to the dataframe
    df[f"MFI{n}_HL"] = 100.0 - (100.0 / (1.0 + rs))
    df[f"MFI{n}_HL_SMA{mfisma}"] = df[f"MFI{n}_HL"].rolling(window=mfisma).mean()

    # Calculate the max and min values of Money Flow Index
    df[f"MFI_HL_Max{period}"] = df[f"MFI{n}_HL"].rolling(window=period).max()
    df[f"MFI_HL_Min{period}"] = df[f"MFI{n}_HL"].rolling(window=period).min()
    
    return df


# 5) Moving Average Convergence Divergence (MACD):
def MACD(df: pd.DataFrame, n_fast=12, n_slow=26, n_signal=9):
    """
    Moving Average Convergence Divergence (Fast EMA: 12 Period | Slow EMA: 26 Period | Signal Line EMA: 9 Period)

    Args:
        df (pd.DataFrame): The DataFrame containing the OHLCV data.
        n_fast (int, optional): The number of periods for the fast EMA. Defaults to 12.
        n_slow (int, optional): The number of periods for the slow EMA. Defaults to 26.
        n_signal (int, optional): The number of periods for the signal EMA. Defaults to 9.

    Returns:
        pd.DataFrame: The DataFrame with the MACD, Signal, and Histogram columns added.
    """

    # Calculate the fast EMA
    ema_fast = df["Mid_Close"].ewm(min_periods=n_fast, span=n_fast).mean()

    # Calculate the slow EMA
    ema_slow = df["Mid_Close"].ewm(min_periods=n_slow, span=n_slow).mean()

    # Calculate the MACD
    df["MACD"] = ema_fast - ema_slow

    # Calculate the signal EMA
    df["Signal"] = df["MACD"].ewm(min_periods=n_signal, span=n_signal).mean()

    # Calculate the histogram
    df["Histogram"] = df["MACD"] - df["Signal"]

    return df


# 5) Moving Average Convergence Divergence (MACD) of Open:
def MACD_O(df: pd.DataFrame, n_fast=12, n_slow=26, n_signal=9):
    """
    Moving Average Convergence Divergence of Open (Fast EMA: 12 Period | Slow EMA: 26 Period | Signal Line EMA: 9 Period)

    Args:
        df (pd.DataFrame): The DataFrame containing the OHLCV data.
        n_fast (int, optional): The number of periods for the fast EMA. Defaults to 12.
        n_slow (int, optional): The number of periods for the slow EMA. Defaults to 26.
        n_signal (int, optional): The number of periods for the signal EMA. Defaults to 9.

    Returns:
        pd.DataFrame: The DataFrame with the MACD, Signal, and Histogram columns added.
    """

    # Calculate the fast EMA
    ema_fast = df["Mid_Open"].ewm(min_periods=n_fast, span=n_fast).mean()

    # Calculate the slow EMA
    ema_slow = df["Mid_Open"].ewm(min_periods=n_slow, span=n_slow).mean()

    # Calculate the MACD
    df["MACD_O"] = ema_fast - ema_slow

    # Calculate the signal EMA
    df["Signal_O"] = df["MACD_O"].ewm(min_periods=n_signal, span=n_signal).mean()

    # Calculate the histogram
    df["Histogram_O"] = df["MACD_O"] - df["Signal_O"]

    return df


# 8) Moving Average Convergence Divergence (MACD) of OHLC:
def MACD_OHLC(df: pd.DataFrame, n_fast=12, n_slow=26, n_signal=9):
    """
    Moving Average Convergence Divergence of OHLC (Fast EMA: 12 Period | Slow EMA: 26 Period | Signal Line EMA: 9 Period)

    Args:
        df (pd.DataFrame): The DataFrame containing the OHLCV data.
        n_fast (int, optional): The number of periods for the fast EMA. Defaults to 12.
        n_slow (int, optional): The number of periods for the slow EMA. Defaults to 26.
        n_signal (int, optional): The number of periods for the signal EMA. Defaults to 9.

    Returns:
        pd.DataFrame: The DataFrame with the MACD, Signal, and Histogram columns added.
    """

    alpha_fast = 1.0 / n_fast
    alpha_slow = 1.0 / n_slow
    alpha_signal = 1.0 / n_signal
    
    # Calculate the typical price
    typical_price = (df["Mid_Open"] + df["Mid_High"] + df["Mid_Low"] + df["Mid_Close"]) / 4

    # Calculate the fast EMA
    ema_fast = typical_price.ewm(min_periods=n_fast, alpha=alpha_fast).mean()

    # Calculate the slow EMA
    ema_slow = typical_price.ewm(min_periods=n_slow, alpha=alpha_slow).mean()

    # Calculate the MACD
    df["MACD_OHLC"] = ema_fast - ema_slow

    # Calculate the signal EMA
    df["Signal_OHLC"] = df["MACD_OHLC"].ewm(min_periods=n_signal, alpha=alpha_signal).mean()

    # Calculate the histogram
    df["Histogram_OHLC"] = df["MACD_OHLC"] - df["Signal_OHLC"]

    return df


# 8) Moving Average Convergence Divergence (MACD) of High Low:
def MACD_HL(df: pd.DataFrame, n_fast=12, n_slow=26, n_signal=9):
    """
    Moving Average Convergence Divergence of High Low (Fast EMA: 12 Period | Slow EMA: 26 Period | Signal Line EMA: 9 Period)

    Args:
        df (pd.DataFrame): The DataFrame containing the OHLCV data.
        n_fast (int, optional): The number of periods for the fast EMA. Defaults to 12.
        n_slow (int, optional): The number of periods for the slow EMA. Defaults to 26.
        n_signal (int, optional): The number of periods for the signal EMA. Defaults to 9.

    Returns:
        pd.DataFrame: The DataFrame with the MACD, Signal, and Histogram columns added.
    """

    alpha_fast = 1.0 / n_fast
    alpha_slow = 1.0 / n_slow
    alpha_signal = 1.0 / n_signal
    
    # Calculate the typical price
    mid_point = (df["Mid_High"] + df["Mid_Low"]) / 2

    # Calculate the typical price volume
    mp_vol = mid_point * df["Volume"]

    # Calculate the fast EMA
    mp_vol_ema_fast = mp_vol.ewm(min_periods=n_fast, alpha=alpha_fast).mean()

    # Calculate the slow EMA
    mp_vol_ema_slow = mp_vol.ewm(min_periods=n_slow, alpha=alpha_slow).mean()

    # Calculate the Fast and Slow EMA of the volume
    vol_ema_fast = df["Volume"].ewm(min_periods=n_fast, alpha=alpha_fast).mean()
    vol_ema_slow = df["Volume"].ewm(min_periods=n_slow, alpha=alpha_slow).mean()

    # Calculate the Volume Weighted EMAs of Fast and Slow EMA
    vw_ema_fast = mp_vol_ema_fast / vol_ema_fast
    vw_ema_slow = mp_vol_ema_slow / vol_ema_slow

    # Calculate the MACD
    df["VW_MACD_HL"] = vw_ema_fast - vw_ema_slow

    # Calculate the signal EMA
    df["VW_Signal_HL"] = df["VW_MACD_HL"].ewm(min_periods=n_signal, alpha=alpha_signal).mean()

    # Calculate the histogram
    df["VW_Histogram_HL"] = df["VW_MACD_HL"] - df["VW_Signal_HL"]

    return df


# 9) Impulse Moving Average Convergence Divergence (Impulse_MACD):
def Impulse_MACD(df: pd.DataFrame, length_ma=34, length_signal=9):
    """
    Calculates Impulse MACD values and colors.
    This is the main function. It takes a DataFrame (df) containing OHLC (Open, High, Low, Close) data as input, along with optional parameters for the length of the moving averages (length_ma) and the length of the signal line (length_signal). 
    - It determines the color of bars (mdc) based on the comparison between the close price and mi, hi, and lo.
    - It returns a DataFrame containing the calculated values.
    """
    # Calculate the typical price (src) from the high, low, and close prices.
    src = (df["Mid_High"] + df["Mid_Low"] + df["Mid_Close"]) / 3
    
    # Compute the SMMA for the high and low prices (hi and lo) and the ZLEMA for the typical price (mi).
    hi = df["Mid_High"].rolling(window=length_ma, min_periods=1).mean()
    lo = df["Mid_Low"].rolling(window=length_ma, min_periods=1).mean()
    ema1 = src.ewm(span=length_ma, adjust=False).mean()
    ema2 = ema1.ewm(span=length_ma, adjust=False).mean()
    d = ema1 - ema2
    mi = ema1 + d
    
    # Compute the MACD-like value (md) based on the comparison between mi, hi, and lo.
    df["ImpulseMACD"] = np.where(mi > hi, mi - hi, np.where(mi < lo, mi - lo, 0))

    # Calculate the signal line df["ImpulseMACDSignal"] by taking the moving average of df["ImpulseMACD"].
    df["ImpulseMACDSignal"] = df["ImpulseMACD"].rolling(window=length_signal, min_periods=1).mean()

    # Compute the histogram df["ImpulseHistogram"] by subtracting the signal line df["ImpulseMACDSignal"] from df["ImpulseMACD"].
    df["ImpulseHistogram"] = df["ImpulseMACD"] - df["ImpulseMACDSignal"]
    
    # Determine the colour of bars df["BarColour"] based on the comparison between the close price and mi, hi, and lo.
    df["BarColour"] = np.where(df["Mid_Close"] > mi,
                      np.where(df["Mid_Close"] > hi, "lime", "green"),
                      np.where(df["Mid_Close"] < lo, "red", "orange"))
    
    return df

# Plotting of Impulse_MACD
def Plot_Impulse_MACD(df: pd.DataFrame):
    """
    Plots Impulse MACD values and histogram
    """
    plt.figure(figsize=(20, 10))
    plt.plot(df.index, df["ImpulseMACD"], label="Impulse MACD", color="blue")
    plt.plot(df.index, df["ImpulseMACDSignal"], label="Signal Line", color="red", linestyle="--")
    plt.bar(df.index, df["ImpulseHistogram"], label="Histogram", color=df["BarColour"])
    plt.title("Impulse MACD")
    plt.legend()
    plt.show()


# 5) Volume Weighted Impulse Moving Average Convergence Divergence (VW_Impulse_MACD):
def VW_Impulse_MACD(df: pd.DataFrame, length_ma=34, length_signal=9):
    """
    Calculates Impulse MACD values and colors.
    This is the main function. It takes a DataFrame (df) containing OHLC (Open, High, Low, Close) data as input, along with optional parameters for the length of the moving averages (length_ma) and the length of the signal line (length_signal). 
    - It determines the color of bars (mdc) based on the comparison between the close price and mi, hi, and lo.
    - It returns a DataFrame containing the calculated values.
    """
    # Calculate the typical price (src) from the high, low, and close prices.
    src = ((df["Mid_High"] * df["Volume"]) + (df["Mid_Low"] * df["Volume"]) + (df["Mid_Close"] * df["Volume"])) / 3
    vw_src = src / df["Volume"]
    
    # Compute the SMMA for the high and low prices (hi and lo).
    hi_vol = df["Mid_High"] * df["Volume"]
    hi = hi_vol.rolling(window=length_ma, min_periods=1).mean()

    lo_vol = df["Mid_Low"] * df["Volume"]
    lo = lo_vol.rolling(window=length_ma, min_periods=1).mean()

    vol = df["Volume"].rolling(window=length_ma, min_periods=1).mean()

    vw_hi = hi / vol
    vw_lo = lo / vol

    # Compute the ZLEMA for the typical price (mi).
    ema1 = vw_src.ewm(span=length_ma, adjust=False).mean()
    ema2 = ema1.ewm(span=length_ma, adjust=False).mean()
    d = ema1 - ema2
    vw_mi = ema1 + d
    
    # Compute the MACD-like value (md) based on the comparison between mi, hi, and lo.
    df["VW_ImpulseMACD"] = np.where(vw_mi > vw_hi, vw_mi - vw_hi, np.where(vw_mi < vw_lo, vw_mi - vw_lo, 0))

    # Calculate the signal line df["ImpulseMACDSignal"] by taking the moving average of df["ImpulseMACD"].
    df["VW_ImpulseMACDSignal"] = df["VW_ImpulseMACD"].rolling(window=length_signal, min_periods=1).mean()

    # Compute the histogram df["ImpulseHistogram"] by subtracting the signal line df["ImpulseMACDSignal"] from df["ImpulseMACD"].
    df["VW_ImpulseHistogram"] = df["VW_ImpulseMACD"] - df["VW_ImpulseMACDSignal"]
    
    # Determine the colour of bars df["BarColour"] based on the comparison between the close price and mi, hi, and lo.
    df["VW_BarColour"] = np.where(df["Mid_Close"] > vw_mi,
                      np.where(df["Mid_Close"] > vw_hi, "lime", "green"),
                      np.where(df["Mid_Close"] < vw_lo, "red", "orange"))
    
    return df

# Plotting of VW_Impulse_MACD
def Plot_VW_Impulse_MACD(df: pd.DataFrame):
    """
    Plots Volume Weighted Impulse MACD values and histogram
    """
    plt.figure(figsize=(20, 10))
    plt.plot(df.index, df["VW_ImpulseMACD"], label="Volume Weighted Impulse MACD", color="blue")
    plt.plot(df.index, df["VW_ImpulseMACDSignal"], label="Volume Weighted Signal Line", color="red", linestyle="--")
    plt.bar(df.index, df["VW_ImpulseHistogram"], label="Volume Weighted Histogram", color=df["VW_BarColour"])
    plt.title("Volume Weighted Impulse MACD")
    plt.legend()
    plt.show()


# Pivot Levels:
def PivotPoints(df: pd.DataFrame):
    """
    Pivot Levels    
    Use the VWHLCP PP Calculation for Day Trading
    Use the VWMA PP Calculation for Trading over 10 Days
    """
    pass


# Volume:
def Volume_SMA(df: pd.DataFrame, n=10):
    """
    Volume with n Period of SMA 
    """
    df[f"Volume_SMA{n}"] = df["Volume"].rolling(window=n).mean()

    return df

# 6) Historical Annual Volatility (HAV):
def HAV(df: pd.DataFrame, lookback: int = 2, price_source: str = "Mid_Close") -> pd.Series:
    """
    Historical Annual Volatility [Log(Curr_Close / Prev_Close): 2 Period]
    """
    log_returns = np.log(df[price_source] / df[price_source].shift(1))
    return log_returns.rolling(window=lookback).std() * np.sqrt(252)


def IAV(df: pd.DataFrame, lookback: int = 2) -> pd.Series:
    """
    IntraDay Annual Volatility [Log(High / Low): 2 Period]
    """
    log_returns = np.log(df["Mid_High"] / df["Mid_Low"])
    return log_returns.rolling(window=lookback).std() * np.sqrt(252)


# 10) Range Action Verification Index (RAVI):
def RAVI(df: pd.DataFrame, n_fast: int = 3, n_slow: int = 10) -> pd.Series:
    """
    The Range Action Verification Index (RAVI) is used to identify if the market is in a trend.
    It was developed by Tushar Chande.
    Use VM EMA and HLC Average
    """
    # Calculate the typical price (HLC average)
    typical_price = (df["Mid_High"] + df["Mid_Low"] + df["Mid_Close"]) / 3

    # Calculate fast and slow EMAs of the typical price
    ema_fast = typical_price.ewm(span=n_fast, adjust=False).mean()
    ema_slow = typical_price.ewm(span=n_slow, adjust=False).mean()

    # Calculate RAVI
    ravi = 100 * (ema_fast - ema_slow) / ema_slow
    return ravi


# 10) Volume Weighted Range Action Verification Index (VW_RAVI):
def VW_RAVI(df: pd.DataFrame, n_fast: int = 3, n_slow: int = 10) -> pd.Series:
    """
    The Range Action Verification Index (RAVI) is used to identify if the market is in a trend. It was developed by Tushar Chande.
    Use VM EMA and HLC Average 
    """
    # Calculate the typical price (HLC average)
    typical_price = (df["Mid_High"] + df["Mid_Low"] + df["Mid_Close"]) / 3

    # Calculate volume-weighted typical price
    vw_typical_price = typical_price * df["Volume"]

    # Calculate fast and slow EMAs of the volume-weighted typical price and volume
    vw_ema_fast_num = vw_typical_price.ewm(span=n_fast, adjust=False).mean()
    vw_ema_fast_den = df["Volume"].ewm(span=n_fast, adjust=False).mean()
    vw_ema_fast = vw_ema_fast_num / vw_ema_fast_den

    vw_ema_slow_num = vw_typical_price.ewm(span=n_slow, adjust=False).mean()
    vw_ema_slow_den = df["Volume"].ewm(span=n_slow, adjust=False).mean()
    vw_ema_slow = vw_ema_slow_num / vw_ema_slow_den

    # Calculate Volume Weighted RAVI
    vw_ravi = 100 * (vw_ema_fast - vw_ema_slow) / vw_ema_slow
    return vw_ravi


def ADX(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """
    Calculates the Average Directional Index (ADX).
    """
    # Calculate True Range (TR)
    df['TR'] = ATR(df, n=1)['ATR1'] # Using ATR function for TR calculation

    # Calculate Directional Movement (DM)
    df['UpMove'] = df['Mid_High'] - df['Mid_High'].shift(1)
    df['DownMove'] = df['Mid_Low'].shift(1) - df['Mid_Low']

    df['PlusDM'] = np.where((df['UpMove'] > df['DownMove']) & (df['UpMove'] > 0), df['UpMove'], 0)
    df['MinusDM'] = np.where((df['DownMove'] > df['UpMove']) & (df['DownMove'] > 0), df['DownMove'], 0)

    # Calculate Smoothed True Range and Directional Movement
    alpha = 1.0 / n
    df['SmoothedTR'] = df['TR'].ewm(span=n, adjust=False).mean()
    df['SmoothedPlusDM'] = df['PlusDM'].ewm(span=n, adjust=False).mean()
    df['SmoothedMinusDM'] = df['MinusDM'].ewm(span=n, adjust=False).mean()

    # Calculate Directional Indicators (DI)
    df['PlusDI'] = (df['SmoothedPlusDM'] / df['SmoothedTR']) * 100
    df['MinusDI'] = (df['SmoothedMinusDM'] / df['SmoothedTR']) * 100

    # Calculate Directional Movement Index (DX)
    df['DX'] = (abs(df['PlusDI'] - df['MinusDI']) / (df['PlusDI'] + df['MinusDI'])) * 100

    # Calculate Average Directional Index (ADX)
    df['ADX'] = df['DX'].ewm(span=n, adjust=False).mean()

    return df['ADX']

def VW_ADX(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """
    Calculates the Volume Weighted Average Directional Index (VW_ADX).
    """
    # Calculate True Range (TR) using VW_ATR
    df['VW_TR'] = VW_ATR(df, n=1)['VW_ATR1'] # Using VW_ATR function for VW_TR calculation

    # Calculate Directional Movement (DM)
    df['UpMove'] = df['Mid_High'] - df['Mid_High'].shift(1)
    df['DownMove'] = df['Mid_Low'].shift(1) - df['Mid_Low']

    df['PlusDM'] = np.where((df['UpMove'] > df['DownMove']) & (df['UpMove'] > 0), df['UpMove'], 0)
    df['MinusDM'] = np.where((df['DownMove'] > df['UpMove']) & (df['DownMove'] > 0), df['DownMove'], 0)

    # Calculate Volume Weighted Smoothed True Range and Directional Movement
    alpha = 1.0 / n
    df['VW_SmoothedTR_Num'] = (df['VW_TR'] * df['Volume']).ewm(span=n, adjust=False).mean()
    df['VW_SmoothedTR_Den'] = df['Volume'].ewm(span=n, adjust=False).mean()
    df['VW_SmoothedTR'] = df['VW_SmoothedTR_Num'] / df['VW_SmoothedTR_Den']

    df['VW_SmoothedPlusDM_Num'] = (df['PlusDM'] * df['Volume']).ewm(span=n, adjust=False).mean()
    df['VW_SmoothedPlusDM_Den'] = df['Volume'].ewm(span=n, adjust=False).mean()
    df['VW_SmoothedPlusDM'] = df['VW_SmoothedPlusDM_Num'] / df['VW_SmoothedPlusDM_Den']

    df['VW_SmoothedMinusDM_Num'] = (df['MinusDM'] * df['Volume']).ewm(span=n, adjust=False).mean()
    df['VW_SmoothedMinusDM_Den'] = df['Volume'].ewm(span=n, adjust=False).mean()
    df['VW_SmoothedMinusDM'] = df['VW_SmoothedMinusDM_Num'] / df['VW_SmoothedMinusDM_Den']

    # Calculate Directional Indicators (DI)
    df['VW_PlusDI'] = (df['VW_SmoothedPlusDM'] / df['VW_SmoothedTR']) * 100
    df['VW_MinusDI'] = (df['VW_SmoothedMinusDM'] / df['VW_SmoothedTR']) * 100

    # Calculate Directional Movement Index (DX)
    df['VW_DX'] = (abs(df['VW_PlusDI'] - df['VW_MinusDI']) / (df['VW_PlusDI'] + df['VW_MinusDI'])) * 100

    # Calculate Average Directional Index (ADX)
    df['VW_ADX'] = df['VW_DX'].ewm(span=n, adjust=False).mean()

    return df['VW_ADX']


# 11) Volume Weighted Alligator's Jaw
def VW_AlligatorsJaw(df: pd.DataFrame, jaw_period: int = 13, jaw_shift: int = 8) -> pd.Series:
    """
    Alligator's Jaw with Volume Weighted EMA 13 and 3 Period Displaced EMA
    """
    # Calculate the typical price (HLC/3)
    typical_price = (df["Mid_High"] + df["Mid_Low"] + df["Mid_Close"]) / 3

    # Calculate volume-weighted typical price
    vw_typical_price = typical_price * df["Volume"]

    # Calculate EMA of volume-weighted typical price and volume for Jaw
    jaw_ema_num = vw_typical_price.ewm(span=jaw_period, adjust=False).mean()
    jaw_ema_den = df["Volume"].ewm(span=jaw_period, adjust=False).mean()
    vw_jaw = (jaw_ema_num / jaw_ema_den).shift(jaw_shift)

    return vw_jaw



def VW_SMA(df: pd.DataFrame, period: int, price_source: str = "Mid_Close") -> pd.Series:
    """
    Calculates the Volume Weighted Simple Moving Average (VW_SMA) for a given period and price source.

    Args:
        df (pd.DataFrame): DataFrame with columns for price (e.g., "Mid_Open", "Mid_Close") and "Volume".
        period (int): The lookback period for the moving average.
        price_source (str, optional): The price column to use. Defaults to "Mid_Close".
                                      Can be "Mid_Open", "Mid_High", "Mid_Low", "Mid_Close".

    Returns:
        pd.Series: A pandas Series containing the VW_SMA values.
    """
    if price_source not in ["Mid_Open", "Mid_High", "Mid_Low", "Mid_Close"]:
        raise ValueError("price_source must be one of 'Mid_Open', 'Mid_High', 'Mid_Low', 'Mid_Close'")

    price_x_vol = df[price_source] * df["Volume"]
    sum_pxv = price_x_vol.rolling(window=period, min_periods=period).sum()
    sum_vol = df["Volume"].rolling(window=period, min_periods=period).sum()
    
    # Avoid division by zero
    vw_sma = sum_pxv / sum_vol
    return vw_sma.fillna(0)


def VW_EMA(df: pd.DataFrame, period: int, price_source: str = "Mid_Close") -> pd.Series:
    """
    Calculates the Volume Weighted Exponential Moving Average (VW_EMA) for a given period and price source.

    Args:
        df (pd.DataFrame): DataFrame with columns for price and "Volume".
        period (int): The lookback period for the moving average.
        price_source (str, optional): The price column to use. Defaults to "Mid_Close".

    Returns:
        pd.Series: A pandas Series containing the VW_EMA values.
    """
    if price_source not in df.columns:
        raise ValueError(f"Price source '{price_source}' not found in DataFrame columns")

    price_x_vol = df[price_source] * df["Volume"]
    
    # Calculate the EMA of price * volume and the EMA of volume
    ema_pxv = price_x_vol.ewm(span=period, adjust=False).mean()
    ema_vol = df["Volume"].ewm(span=period, adjust=False).mean()
    
    # Avoid division by zero
    vw_ema = ema_pxv / ema_vol
    return vw_ema.fillna(0)


# 16) Market Normalisation with Volume Weighted ATR:
def Mkt_Norm(df: pd.DataFrame, n: int = 21) -> pd.Series:
    """
    Market Normalisation with Volume Weighted ATR
    """
    # Calculate Volume Weighted ATR
    vw_atr = VW_ATR(df, n=n)[f'VW_ATR{n}']

    # Calculate Market Normalisation
    # Assuming 'Mid_Close' is the price to normalize
    market_norm = df['Mid_Close'] / vw_atr
    return market_norm


# 17) Percentage Change of Price:
def PcChange(curr_price, prev_price):
    pc_change = np.log(curr_price / prev_price)
    return pc_change


def Beta(asset_returns: pd.Series, market_returns: pd.Series, lookback: int = 252) -> float:
    """
    Calculates the beta of an asset relative to the market.

    Args:
        asset_returns (pd.Series): A pandas Series of the asset's returns.
        market_returns (pd.Series): A pandas Series of the market's returns.
        lookback (int, optional): The lookback period for the calculation. Defaults to 252 (one year).

    Returns:
        float: The beta value.
    """
    # Ensure the series are aligned
    combined = pd.concat([asset_returns, market_returns], axis=1).dropna()
    
    # Calculate covariance and variance over the lookback period
    rolling_cov = combined.iloc[:, 0].rolling(window=lookback).cov(combined.iloc[:, 1])
    rolling_var = combined.iloc[:, 1].rolling(window=lookback).var()
    
    # Calculate beta
    beta = rolling_cov / rolling_var
    
    return beta.iloc[-1] if not beta.empty else np.nan


#19) Choppiness Index:
def ChoppyIndex(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """
    Calculates the Choppiness Index (CHOP) for a given DataFrame.

    Args:
        df (pd.DataFrame): DataFrame with columns "Mid_High", "Mid_Low", "Mid_Close".
        n (int, optional): The lookback period. Defaults to 14.

    Returns:
        pd.Series: A pandas Series containing the Choppiness Index values.
    """
    # Calculate True Range
    tr1 = pd.DataFrame(df["Mid_High"] - df["Mid_Low"])
    tr2 = pd.DataFrame(abs(df["Mid_High"] - df["Mid_Close"].shift(1)))
    tr3 = pd.DataFrame(abs(df["Mid_Low"] - df["Mid_Close"].shift(1)))
    tr = pd.concat([tr1, tr2, tr3], axis=1, join='inner').max(axis=1)

    # Sum of True Range over the lookback period
    atr_sum = tr.rolling(window=n, min_periods=n).sum()

    # Highest High and Lowest Low over the lookback period
    max_hi = df["Mid_High"].rolling(window=n, min_periods=n).max()
    min_lo = df["Mid_Low"].rolling(window=n, min_periods=n).max()

    # Calculate Choppiness Index
    chop = 100 * np.log10(atr_sum / (max_hi - min_lo)) / np.log10(n)

    return chop.fillna(0)

# 20) AutoCorrelation:
def AutoCorrelation(df: pd.DataFrame, column: str = "Mid_Close", lag: int = 1) -> float:
    """
    Calculates the autocorrelation of a series for a specified lag.

    Args:
        df (pd.DataFrame): DataFrame containing the time series data.
        column (str, optional): The column to calculate autocorrelation on. Defaults to "Mid_Close".
        lag (int, optional): The lag to use for the calculation. Defaults to 1.

    Returns:
        float: The autocorrelation value.
    """
    return df[column].autocorr(lag=lag)


# 21) Gann Angles:
def GannAngles(df: pd.DataFrame, trade_type=0, price_digit_threshold: int = 100):
    """
    Gann Angles
    trade_type: 0 if IntraDay Trade or 1 if Positional Trade
    price_digit_threshold: Threshold to determine if price is a 1 or 2 digit number
    """
    open_price = df["Mid_Open"]
    high_price = df["Mid_High"]
    low_price = df["Mid_Low"]
    close_price = df["Mid_Close"]

    # 0 if Price IS NOT a 1 or 2 digit number and 1 if Price IS a 1 or 2 digit number
    price_digit = [0 if (x >= price_digit_threshold) else 1 for x in close_price]

    # Gann angles are typically drawn from significant highs and lows.
    # This implementation will focus on identifying potential pivot points
    # and calculating basic Gann angle lines based on price and time ratios.
    # This is a simplified representation and a full Gann analysis is complex.

    # For simplicity, let's define some common Gann ratios for price and time
    # These ratios represent angles like 1x1, 1x2, 2x1, etc.
    gann_ratios = [0.25, 0.33, 0.5, 0.66, 1.0, 1.5, 2.0, 3.0, 4.0]

    # We'll calculate Gann lines from a recent significant pivot (e.g., highest high or lowest low)
    # For a more robust implementation, one would need to identify true Gann pivots.

    # Example: Calculate Gann lines from the highest high in the last 'n' periods
    n_periods = 20  # Example lookback for a pivot
    highest_high_idx = df["Mid_High"].rolling(window=n_periods).apply(lambda x: x.idxmax(), raw=False)
    lowest_low_idx = df[ "Mid_Low"].rolling(window=n_periods).apply(lambda x: x.idxmin(), raw=False)

    # Initialize columns for Gann angles (simplified)
    for ratio in gann_ratios:
        df[f'Gann_Up_{str(ratio).replace(".", "p")}x1'] = np.nan
        df[f'Gann_Down_1x{str(ratio).replace(".", "p')}'] = np.nan

    # This is a highly simplified example. A proper Gann analysis involves:
    # 1. Identifying significant pivots (major highs/lows)
    # 2. Drawing angles from these pivots based on price and time scales
    # 3. Considering squaring of price and time
    # 4. Using Gann squares and circles

    # For demonstration, let's just mark the pivot points
    df['Highest_High_Pivot'] = df["Mid_High"].rolling(window=n_periods).max()
    df['Lowest_Low_Pivot'] = df["Mid_Low"].rolling(window=n_periods).min()

    # You would typically iterate through identified pivots and draw lines
    # For example, a 1x1 Gann angle from a low would rise 1 unit of price for 1 unit of time.
    # The 'unit' depends on the scaling of your chart.

    # This function primarily serves as a placeholder for a more complex Gann analysis.
    # The 'price_digit' calculation is retained as it was in the original placeholder.
    df['Price_Digit_Category'] = price_digit

    return df


def VW_ADX(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """
    Calculates the Volume Weighted Average Directional Index (VW_ADX).
    """
    # Calculate True Range (TR) using VW_ATR
    df['VW_TR'] = VW_ATR(df, n=1)['VW_ATR1'] # Using VW_ATR function for VW_TR calculation

    # Calculate Directional Movement (DM)
    df['UpMove'] = df['Mid_High'] - df['Mid_High'].shift(1)
    df['DownMove'] = df['Mid_Low'].shift(1) - df['Mid_Low']

    df['PlusDM'] = np.where((df['UpMove'] > df['DownMove']) & (df['UpMove'] > 0), df['UpMove'], 0)
    df['MinusDM'] = np.where((df['DownMove'] > df['UpMove']) & (df['DownMove'] > 0), df['DownMove'], 0)

    # Calculate Volume Weighted Smoothed True Range and Directional Movement
    alpha = 1.0 / n
    df['VW_SmoothedTR_Num'] = (df['VW_TR'] * df['Volume']).ewm(span=n, adjust=False).mean()
    df['VW_SmoothedTR_Den'] = df['Volume'].ewm(span=n, adjust=False).mean()
    df['VW_SmoothedTR'] = df['VW_SmoothedTR_Num'] / df['VW_SmoothedTR_Den']

    df['VW_SmoothedPlusDM_Num'] = (df['PlusDM'] * df['Volume']).ewm(span=n, adjust=False).mean()
    df['VW_SmoothedPlusDM_Den'] = df['Volume'].ewm(span=n, adjust=False).mean()
    df['VW_SmoothedPlusDM'] = df['VW_SmoothedPlusDM_Num'] / df['VW_SmoothedPlusDM_Den']

    df['VW_SmoothedMinusDM_Num'] = (df['MinusDM'] * df['Volume']).ewm(span=n, adjust=False).mean()
    df['VW_SmoothedMinusDM_Den'] = df['Volume'].ewm(span=n, adjust=False).mean()
    df['VW_SmoothedMinusDM'] = df['VW_SmoothedMinusDM_Num'] / df['VW_SmoothedMinusDM_Den']

    # Calculate Directional Indicators (DI)
    df['VW_PlusDI'] = (df['VW_SmoothedPlusDM'] / df['VW_SmoothedTR']) * 100
    df['VW_MinusDI'] = (df['VW_SmoothedMinusDM'] / df['VW_SmoothedTR']) * 100

    # Calculate Directional Movement Index (DX)
    df['VW_DX'] = (abs(df['VW_PlusDI'] - df['VW_MinusDI']) / (df['VW_PlusDI'] + df['VW_MinusDI'])) * 100

    # Calculate Average Directional Index (ADX)
    df['VW_ADX'] = df['VW_DX'].ewm(span=n, adjust=False).mean()

    return df['VW_ADX']


def VW_AlligatorsJaw(df: pd.DataFrame, jaw_period: int = 13, jaw_shift: int = 8) -> pd.Series:
    """
    Alligator's Jaw with Volume Weighted EMA 13 and 3 Period Displaced EMA
    """
    # Calculate the typical price (HLC/3)
    typical_price = (df["Mid_High"] + df["Mid_Low"] + df["Mid_Close"]) / 3

    # Calculate volume-weighted typical price
    vw_typical_price = typical_price * df["Volume"]

    # Calculate EMA of volume-weighted typical price and volume for Jaw
    jaw_ema_num = vw_typical_price.ewm(span=jaw_period, adjust=False).mean()
    jaw_ema_den = df["Volume"].ewm(span=jaw_period, adjust=False).mean()
    vw_jaw = (jaw_ema_num / jaw_ema_den).shift(jaw_shift)

    return vw_jaw


def VW_SMA(df: pd.DataFrame, period: int, price_source: str = "Mid_Close") -> pd.Series:
    """
    Calculates the Volume Weighted Simple Moving Average (VW_SMA) for a given period and price source.

    Args:
        df (pd.DataFrame): DataFrame with columns for price (e.g., "Mid_Open", "Mid_Close") and "Volume".
        period (int): The lookback period for the moving average.
        price_source (str, optional): The price column to use. Defaults to "Mid_Close".
                                      Can be "Mid_Open", "Mid_High", "Mid_Low", "Mid_Close".

    Returns:
        pd.Series: A pandas Series containing the VW_SMA values.
    """
    if price_source not in ["Mid_Open", "Mid_High", "Mid_Low", "Mid_Close"]:
        raise ValueError("price_source must be one of 'Mid_Open', 'Mid_High', 'Mid_Low', 'Mid_Close'")

    price_x_vol = df[price_source] * df["Volume"]
    sum_pxv = price_x_vol.rolling(window=period, min_periods=period).sum()
    sum_vol = df["Volume"].rolling(window=period, min_periods=period).sum()
    
    # Avoid division by zero
    vw_sma = sum_pxv / sum_vol
    return vw_sma.fillna(0)


def VW_EMA(df: pd.DataFrame, period: int, price_source: str = "Mid_Close") -> pd.Series:
    """
    Calculates the Volume Weighted Exponential Moving Average (VW_EMA) for a given period and price source.

    Args:
        df (pd.DataFrame): DataFrame with columns for price and "Volume".
        period (int): The lookback period for the moving average.
        price_source (str, optional): The price column to use. Defaults to "Mid_Close".

    Returns:
        pd.Series: A pandas Series containing the VW_EMA values.
    """
    if price_source not in df.columns:
        raise ValueError(f"Price source '{price_source}' not found in DataFrame columns")

    price_x_vol = df[price_source] * df["Volume"]
    
    # Calculate the EMA of price * volume and the EMA of volume
    ema_pxv = price_x_vol.ewm(span=period, adjust=False).mean()
    ema_vol = df["Volume"].ewm(span=period, adjust=False).mean()
    
    # Avoid division by zero
    vw_ema = ema_pxv / ema_vol
    return vw_ema.fillna(0)


def Mkt_Norm(df: pd.DataFrame, n: int = 21) -> pd.Series:
    """
    Market Normalisation with Volume Weighted ATR
    """
    # Calculate Volume Weighted ATR
    vw_atr = VW_ATR(df, n=n)[f'VW_ATR{n}']

    # Calculate Market Normalisation
    # Assuming 'Mid_Close' is the price to normalize
    market_norm = df['Mid_Close'] / vw_atr
    return market_norm


# 17) Percentage Change of Price:
def PcChange(curr_price, prev_price):
    pc_change = np.log(curr_price / prev_price)
    return pc_change


def Beta(asset_returns: pd.Series, market_returns: pd.Series, lookback: int = 252) -> float:
    """
    Calculates the beta of an asset relative to the market.

    Args:
        asset_returns (pd.Series): A pandas Series of the asset's returns.
        market_returns (pd.Series): A pandas Series of the market's returns.
        lookback (int, optional): The lookback period for the calculation. Defaults to 252 (one year).

    Returns:
        float: The beta value.
    """
    # Ensure the series are aligned
    combined = pd.concat([asset_returns, market_returns], axis=1).dropna()
    
    # Calculate covariance and variance over the lookback period
    rolling_cov = combined.iloc[:, 0].rolling(window=lookback).cov(combined.iloc[:, 1])
    rolling_var = combined.iloc[:, 1].rolling(window=lookback).var()
    
    # Calculate beta
    beta = rolling_cov / rolling_var
    
    return beta.iloc[-1] if not beta.empty else np.nan


#19) Choppiness Index:
def ChoppyIndex(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """
    Calculates the Choppiness Index (CHOP) for a given DataFrame.

    Args:
        df (pd.DataFrame): DataFrame with columns "Mid_High", "Mid_Low", "Mid_Close".
        n (int, optional): The lookback period. Defaults to 14.

    Returns:
        pd.Series: A pandas Series containing the Choppiness Index values.
    """
    # Calculate True Range
    tr1 = pd.DataFrame(df["Mid_High"] - df["Mid_Low"])
    tr2 = pd.DataFrame(abs(df["Mid_High"] - df["Mid_Close"].shift(1)))
    tr3 = pd.DataFrame(abs(df["Mid_Low"] - df["Mid_Close"].shift(1)))
    tr = pd.concat([tr1, tr2, tr3], axis=1, join='inner').max(axis=1)

    # Sum of True Range over the lookback period
    atr_sum = tr.rolling(window=n, min_periods=n).sum()

    # Highest High and Lowest Low over the lookback period
    max_hi = df["Mid_High"].rolling(window=n, min_periods=n).max()
    min_lo = df["Mid_Low"].rolling(window=n, min_periods=n).max()

    # Calculate Choppiness Index
    chop = 100 * np.log10(atr_sum / (max_hi - min_lo)) / np.log10(n)

    return chop.fillna(0)

# 20) AutoCorrelation:
def AutoCorrelation(df: pd.DataFrame, column: str = "Mid_Close", lag: int = 1) -> float:
    """
    Calculates the autocorrelation of a series for a specified lag.

    Args:
        df (pd.DataFrame): DataFrame containing the time series data.
        column (str, optional): The column to calculate autocorrelation on. Defaults to "Mid_Close".
        lag (int, optional): The lag to use for the calculation. Defaults to 1.

    Returns:
        float: The autocorrelation value.
    """
    return df[column].autocorr(lag=lag)


# 21) Gann Angles:
def GannAngles(df: pd.DataFrame, trade_type=0, ):
    """
    trade_type: 0 if IntraDay Trade or 1 if Positional Trade
    #price_digit: 

    """
    open = df["Mid_Open"]
    high = df["Mid_High"]
    low = df["Mid_Low"]
    close = df["Mid_Close"]
    price_digit = [0 if (x >= 100) else 1 for x in close]            #0 if Price IS NOT a 1 or 2 digit number and 1 if Price IS a 1 or 2 digit number
    pass

"""
#N:Open, O:High, P:Low, Q:Close, R:Volume,
#Z:%Change, AB:Beta, [AD:%Change with Lag, AE:AutoCorrelation],
#HAV- AH: Log(Curr_Close/Prev_Close), AI: Prev. Daily Vol, AJ: Curr. Daily Vol, AK: HAV(2),
#IAV- AP: Log(High/Low), AQ: Prev. Daily Vol, AR: Curr. Daily Vol, AS: IAV(2),
#VW_SMA(TrendFinder)- AX: (Open x Vol), AY: VS SMA 55 (Open),
#VW_EMA(TrendFinder)- BB: EMA 13 (Open X Vol), BC: EMA 13 (Vol), BD: VW EMA 13 (Open), BE: HLC Avg, BF: (HLC Avg x Vol), BG: EMA 5 (HLC Avg x Vol), BH: EMA 5 (Vol), BI: VW EMA 5 (HLC Avg)
#VW_SMA_CrossOver(Strategy)- BR: (Low x Vol), BS: (High x Vol), BT: Entry VW SMA 13 (Open), BU: Exit VW SMA 5 (Low), BV: Exit VW SMA 5 (High),    BW: Entry VW SMA 34 (Open), BX: Exit VW SMA 13 (Low), BY: Exit VW SMA 13 (High)
#VW_MACD- CH: EMA 12 (HLC Avg x Vol), CI: EMA 12 (Vol), CJ: VM EMA 12 (HLC Avg), CK: EMA 26 (HLC Avg x Vol), CL: EMA 26 (Vol), CM: VM EMA 26 (HLC Avg), CN: VM MACD Line (HLC Avg), CO: VM Signal Line HLC Avg (VM EMA 9 MACD Line), CP: VM MACD Histogram (HLC Avg)
#VM_MFI(Strategy)- CZ: HLC Avg Price Change, DA: +veMF (HLC Avg x Vol), DB: -veMF (HLC Avg x Vol), DC: VM EMA 14 (+veMF), DD: VM EMA 14 (-veMF), DE: Relative Strength, DF: MFI, DG: VM SMA 34 (Entry), DH: VM SMA 21 (Exit)
#MM(Market Normalisation) with VM ATR 21- DR: True Range, DS: True Range x Vol, DT: VM EMA 21 (True Range x Vol), DU: VM EMA 21 (Vol), DV: VM ATR 21 (N), DW: Rupee Volatility / Risk (N x Lot Size), DX: Current Risk (Unit) [2N], DY: Max No. of Lots, DZ: ATRP 21
#MM(Market Normalisation) with VM ATR 8- EJ: True Range, EK: True Range x Vol, EL: VM EMA 8 (True Range x Vol), EM: VM EMA 8 (Vol), EN: VM ATR 8 (N), EO: Rupee Volatility / Risk (N x Lot Size), EP: Current Risk (Unit) [2N], EQ: Max No. of Lots, ER: ATRP 8
#High-Low Range Avg for ORB- FF: High-Low Range, FG: %Change (High-Low Range with Open), FH: %Change SMA 8, FI: FJ:
"""
