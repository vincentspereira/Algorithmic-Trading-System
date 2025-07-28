"""
Custom Volume-Weighted Technical Indicators - Phase 5 Enterprise Feature
Advanced technical analysis indicators incorporating volume data

This module implements the comprehensive list of volume-weighted indicators
specified in the Phase 5 requirements, including:
- Volume-Weighted Moving Averages (VW SMA, VW EMA)
- Volume-Weighted MACD and MFI
- Market Normalization with ATR
- Strength/Weakness calculations
- Risk and volatility metrics
"""

import numpy as np
import pandas as pd
from typing import Union, Optional, Tupleme
import warnings
from dataclasses import dataclass

# Suppress pandas warnings for cleaner output
warnings.filterwarnings('ignore', category=FutureWarning)


@dataclass
class MarketData:
    """Container for market data required by indicators"""
    open: pd.Series
    high: pd.Series
    low: pd.Series
    close: pd.Series
    volume: pd.Series
    
    def __post_init__(self):
        """Validate that all series have the same length"""
        lengths = [len(self.open), len(self.high), len(self.low), len(self.close), len(self.volume)]
        if len(set(lengths)) > 1:
            raise ValueError("All price and volume series must have the same length")


class VolumeWeightedIndicators:
    """
    Collection of volume-weighted technical indicators for advanced market analysis
    
    This class implements sophisticated indicators that incorporate volume data
    to provide more accurate signals than traditional price-only indicators.
    """
    
    @staticmethod
    def vw_sma(price: pd.Series, volume: pd.Series, window: int) -> pd.Series:
        """
        Volume-Weighted Simple Moving Average
        
        Args:
            price: Price series (typically close, but can be open, high, low)
            volume: Volume series
            window: Period for calculation
            
        Returns:
            Volume-weighted SMA series
        """
        if len(price) != len(volume):
            raise ValueError("Price and volume series must have the same length")
        
        # Calculate volume-weighted price
        vw_price = price * volume
        
        # Rolling sums
        vw_price_sum = vw_price.rolling(window=window).sum()
        volume_sum = volume.rolling(window=window).sum()
        
        # Avoid division by zero
        volume_sum = volume_sum.replace(0, np.nan)
        
        return vw_price_sum / volume_sum
    
    @staticmethod
    def vw_ema(price: pd.Series, volume: pd.Series, window: int) -> pd.Series:
        """
        Volume-Weighted Exponential Moving Average
        
        Args:
            price: Price series
            volume: Volume series
            window: Period for calculation
            
        Returns:
            Volume-weighted EMA series
        """
        if len(price) != len(volume):
            raise ValueError("Price and volume series must have the same length")
        
        # Calculate volume-weighted price
        vw_price = price * volume
        
        # Calculate EMA of volume-weighted price and volume separately
        vw_price_ema = vw_price.ewm(span=window).mean()
        volume_ema = volume.ewm(span=window).mean()
        
        # Avoid division by zero
        volume_ema = volume_ema.replace(0, np.nan)
        
        return vw_price_ema / volume_ema
    
    @staticmethod
    def hlc_average(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        """
        Calculate HLC (High, Low, Close) Average
        
        Args:
            high: High price series
            low: Low price series
            close: Close price series
            
        Returns:
            HLC average series
        """
        return (high + low + close) / 3
    
    @staticmethod
    def vw_macd(price: pd.Series, volume: pd.Series, 
                fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Volume-Weighted MACD (Moving Average Convergence Divergence)
        
        Args:
            price: Price series (typically HLC average)
            volume: Volume series
            fast_period: Fast EMA period (default 12)
            slow_period: Slow EMA period (default 26)
            signal_period: Signal line EMA period (default 9)
            
        Returns:
            Tuple of (MACD line, Signal line, Histogram)
        """
        # Calculate volume-weighted EMAs
        fast_ema = VolumeWeightedIndicators.vw_ema(price, volume, fast_period)
        slow_ema = VolumeWeightedIndicators.vw_ema(price, volume, slow_period)
        
        # MACD line
        macd_line = fast_ema - slow_ema
        
        # Signal line (EMA of MACD line)
        signal_line = macd_line.ewm(span=signal_period).mean()
        
        # Histogram
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def vw_mfi(data: MarketData, window: int = 14) -> pd.Series:
        """
        Volume-Weighted Money Flow Index
        
        Args:
            data: MarketData object containing OHLCV data
            window: Period for calculation (default 14)
            
        Returns:
            Volume-weighted MFI series
        """
        # Calculate typical price
        typical_price = (data.high + data.low + data.close) / 3
        
        # Calculate raw money flow
        raw_money_flow = typical_price * data.volume
        
        # Determine positive and negative money flow
        price_change = typical_price.diff()
        positive_flow = pd.Series(0.0, index=data.close.index)
        negative_flow = pd.Series(0.0, index=data.close.index)
        
        positive_flow[price_change > 0] = raw_money_flow[price_change > 0]
        negative_flow[price_change < 0] = raw_money_flow[price_change < 0]
        
        # Calculate money flow ratio
        positive_mf = positive_flow.rolling(window=window).sum()
        negative_mf = negative_flow.rolling(window=window).sum()
        
        # Avoid division by zero
        money_flow_ratio = positive_mf / (negative_mf + 1e-10)
        
        # Calculate MFI
        mfi = 100 - (100 / (1 + money_flow_ratio))
        
        return mfi
    
    @staticmethod
    def atr(data: MarketData, window: int = 21) -> pd.Series:
        """
        Average True Range
        
        Args:
            data: MarketData object containing OHLCV data
            window: Period for calculation
            
        Returns:
            ATR series
        """
        # Calculate True Range components
        tr1 = data.high - data.low
        tr2 = abs(data.high - data.close.shift(1))
        tr3 = abs(data.low - data.close.shift(1))
        
        # True Range is the maximum of the three
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # ATR is the moving average of True Range
        return true_range.rolling(window=window).mean()
    
    @staticmethod
    def atr_percent(data: MarketData, window: int = 21) -> pd.Series:
        """
        Average True Range Percent (Normalized ATR)
        
        Args:
            data: MarketData object containing OHLCV data
            window: Period for calculation
            
        Returns:
            ATR percentage series
        """
        atr = VolumeWeightedIndicators.atr(data, window)
        return (atr / data.close) * 100
    
    @staticmethod
    def market_normalization(data: MarketData, atr_window: int = 21) -> pd.Series:
        """
        Market Normalization using ATR (N value for position sizing)
        
        Args:
            data: MarketData object containing OHLCV data
            atr_window: Period for ATR calculation
            
        Returns:
            Market normalization factor (N)
        """
        return VolumeWeightedIndicators.atr(data, atr_window)
    
    @staticmethod
    def volatility_risk(data: MarketData, atr_window: int = 21, lot_size: int = 1, 
                       currency_multiplier: float = 1.0) -> pd.Series:
        """
        Calculate volatility/risk in currency terms
        
        Args:
            data: MarketData object containing OHLCV data
            atr_window: Period for ATR calculation
            lot_size: Number of shares/contracts per lot
            currency_multiplier: Multiplier for currency conversion
            
        Returns:
            Volatility risk in currency terms
        """
        n = VolumeWeightedIndicators.market_normalization(data, atr_window)
        return n * lot_size * currency_multiplier
    
    @staticmethod
    def contract_risk_units(data: MarketData, atr_window: int = 21, multiplier: float = 2.0) -> pd.Series:
        """
        Calculate contract risk in units (for position sizing)
        
        Args:
            data: MarketData object containing OHLCV data
            atr_window: Period for ATR calculation
            multiplier: Risk multiplier (2N for positional, 0.75N for intraday)
            
        Returns:
            Contract risk in units
        """
        n = VolumeWeightedIndicators.market_normalization(data, atr_window)
        return multiplier * n
    
    @staticmethod
    def max_lots_tradeable(account_balance: float, data: MarketData, 
                          atr_window: int = 21, risk_per_trade: float = 0.02) -> pd.Series:
        """
        Calculate maximum number of lots that can be traded
        
        Args:
            account_balance: Total account balance
            data: MarketData object containing OHLCV data
            atr_window: Period for ATR calculation
            risk_per_trade: Risk per trade as percentage of account
            
        Returns:
            Maximum lots tradeable
        """
        risk_amount = account_balance * risk_per_trade
        volatility_risk = VolumeWeightedIndicators.volatility_risk(data, atr_window)
        
        # Avoid division by zero
        volatility_risk = volatility_risk.replace(0, np.nan)
        
        return risk_amount / volatility_risk
    
    @staticmethod
    def strength_weakness_index(data: MarketData, hlc_window: int = 21, atr_window: int = 21) -> pd.Series:
        """
        Strength/Weakness Index based on Turtle Rules
        Formula: (LTP - Avg. HLC(21)) / ATR(21)
        
        Args:
            data: MarketData object containing OHLCV data
            hlc_window: Period for HLC average calculation
            atr_window: Period for ATR calculation
            
        Returns:
            Strength/Weakness index
        """
        # Calculate HLC average
        hlc_avg = VolumeWeightedIndicators.hlc_average(data.high, data.low, data.close)
        hlc_sma = hlc_avg.rolling(window=hlc_window).mean()
        
        # Calculate ATR
        atr = VolumeWeightedIndicators.atr(data, atr_window)
        
        # Strength/Weakness calculation
        # Using close price as Last Traded Price (LTP)
        strength_weakness = (data.close - hlc_sma) / atr
        
        return strength_weakness
    
    @staticmethod
    def high_low_range_average(data: MarketData, window: int = 21) -> pd.Series:
        """
        High-Low Range Average for Opening Range Breakout (ORB)
        
        Args:
            data: MarketData object containing OHLCV data
            window: Period for calculation
            
        Returns:
            High-Low range average
        """
        daily_range = data.high - data.low
        return daily_range.rolling(window=window).mean()
    
    @staticmethod
    def sma_average_percent_change(price: pd.Series, window: int) -> pd.Series:
        """
        Calculate average percentage change of SMA
        
        Args:
            price: Price series
            window: SMA period
            
        Returns:
            Average percentage change of SMA
        """
        sma = price.rolling(window=window).mean()
        sma_pct_change = sma.pct_change() * 100
        return sma_pct_change.rolling(window=window).mean()
    
    @staticmethod
    def buy_sell_easier_day(data: MarketData, window: int = 21) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate Buy Easier Day and Sell Easier Day indicators
        
        Args:
            data: MarketData object containing OHLCV data
            window: Period for calculation
            
        Returns:
            Tuple of (Buy Easier Day, Sell Easier Day) indicators
        """
        # Calculate daily ranges and volumes
        daily_range = data.high - data.low
        
        # Buy Easier Day: Higher volume on up days with smaller ranges
        up_days = data.close > data.open
        buy_easier = pd.Series(0.0, index=data.close.index)
        buy_easier[up_days] = data.volume[up_days] / (daily_range[up_days] + 1e-10)
        
        # Sell Easier Day: Higher volume on down days with smaller ranges
        down_days = data.close < data.open
        sell_easier = pd.Series(0.0, index=data.close.index)
        sell_easier[down_days] = data.volume[down_days] / (daily_range[down_days] + 1e-10)
        
        # Smooth with moving average
        buy_easier_smooth = buy_easier.rolling(window=window).mean()
        sell_easier_smooth = sell_easier.rolling(window=window).mean()
        
        return buy_easier_smooth, sell_easier_smooth
    
    @staticmethod
    def choppy_market_index(data: MarketData, window: int = 21) -> pd.Series:
        """
        Choppy Market Index to determine if market is trending or choppy
        
        Args:
            data: MarketData object containing OHLCV data
            window: Period for calculation
            
        Returns:
            Choppy Market Index (higher values indicate choppier markets)
        """
        # Calculate price changes
        price_changes = abs(data.close.diff())
        
        # Calculate sum of absolute price changes
        sum_changes = price_changes.rolling(window=window).sum()
        
        # Calculate net price change over period
        net_change = abs(data.close - data.close.shift(window))
        
        # Choppy Market Index
        # Higher values indicate more choppy (sideways) movement
        choppy_index = sum_changes / (net_change + 1e-10)
        
        return choppy_index
    
    @staticmethod
    def market_mode(data: MarketData, window: int = 21, threshold: float = 2.0) -> pd.Series:
        """
        Determine market mode: Trending or Choppy
        
        Args:
            data: MarketData object containing OHLCV data
            window: Period for calculation
            threshold: Threshold for determining choppy vs trending
            
        Returns:
            Market mode series (1 for trending, 0 for choppy)
        """
        choppy_index = VolumeWeightedIndicators.choppy_market_index(data, window)
        
        # Market is trending when choppy index is below threshold
        market_mode = (choppy_index < threshold).astype(int)
        
        return market_mode
    
    @staticmethod
    def beta_vs_market(stock_returns: pd.Series, market_returns: pd.Series, window: int = 252) -> pd.Series:
        """
        Calculate rolling Beta vis-à-vis Market Index
        
        Args:
            stock_returns: Stock return series
            market_returns: Market return series
            window: Period for calculation (default 252 for annual)
            
        Returns:
            Rolling beta series
        """
        # Calculate covariance and variance using rolling windows
        covariance = stock_returns.rolling(window=window).cov(market_returns)
        market_variance = market_returns.rolling(window=window).var()
        
        # Beta calculation
        beta = covariance / market_variance
        
        return beta
    
    @staticmethod
    def auto_correlation(price: pd.Series, lag: int = 1, window: int = 252) -> pd.Series:
        """
        Calculate rolling auto-correlation
        
        Args:
            price: Price series
            lag: Lag for auto-correlation
            window: Rolling window period
            
        Returns:
            Auto-correlation series
        """
        returns = price.pct_change()
        
        # Calculate rolling correlation with lagged series
        auto_corr = returns.rolling(window=window).corr(returns.shift(lag))
        
        return auto_corr
    
    @staticmethod
    def historical_annual_volatility(returns: pd.Series, window: int = 252) -> pd.Series:
        """
        Calculate historical annual volatility
        
        Args:
            returns: Return series
            window: Rolling window period (252 for annual)
            
        Returns:
            Annual volatility series
        """
        # Calculate rolling standard deviation and annualize
        rolling_std = returns.rolling(window=window).std()
        annual_vol = rolling_std * np.sqrt(252)  # Assuming 252 trading days per year
        
        return annual_vol
    
    @staticmethod
    def intraday_annual_volatility(intraday_returns: pd.Series, periods_per_day: int = 390) -> pd.Series:
        """
        Calculate intraday annual volatility
        
        Args:
            intraday_returns: Intraday return series
            periods_per_day: Number of periods per trading day (e.g., 390 for 1-minute bars)
            
        Returns:
            Intraday annual volatility series
        """
        # Calculate rolling standard deviation
        rolling_std = intraday_returns.rolling(window=periods_per_day).std()
        
        # Annualize: sqrt(periods_per_day * 252)
        annual_vol = rolling_std * np.sqrt(periods_per_day * 252)
        
        return annual_vol


# Convenience functions for common indicator combinations
def calculate_all_vw_sma_indicators(data: MarketData) -> dict:
    """
    Calculate all Volume-Weighted SMA indicators as specified in Phase 5
    
    Args:
        data: MarketData object containing OHLCV data
        
    Returns:
        Dictionary containing all VW SMA indicators
    """
    indicators = {}
    
    # Volume-Weighted SMAs for different periods and price types
    indicators['vw_sma_55_open'] = VolumeWeightedIndicators.vw_sma(data.open, data.volume, 55)
    indicators['vw_sma_13_open'] = VolumeWeightedIndicators.vw_sma(data.open, data.volume, 13)
    indicators['vw_sma_34_open'] = VolumeWeightedIndicators.vw_sma(data.open, data.volume, 34)
    
    indicators['vw_sma_5_high'] = VolumeWeightedIndicators.vw_sma(data.high, data.volume, 5)
    indicators['vw_sma_5_low'] = VolumeWeightedIndicators.vw_sma(data.low, data.volume, 5)
    indicators['vw_sma_13_high'] = VolumeWeightedIndicators.vw_sma(data.high, data.volume, 13)
    indicators['vw_sma_13_low'] = VolumeWeightedIndicators.vw_sma(data.low, data.volume, 13)
    
    # Volume-Weighted EMAs
    indicators['vw_ema_13_open'] = VolumeWeightedIndicators.vw_ema(data.open, data.volume, 13)
    
    # HLC Average and its VW EMA
    hlc_avg = VolumeWeightedIndicators.hlc_average(data.high, data.low, data.close)
    indicators['vw_ema_5_hlc'] = VolumeWeightedIndicators.vw_ema(hlc_avg, data.volume, 5)
    
    return indicators


def calculate_all_macd_indicators(data: MarketData) -> dict:
    """
    Calculate all MACD-related indicators
    
    Args:
        data: MarketData object containing OHLCV data
        
    Returns:
        Dictionary containing MACD indicators
    """
    indicators = {}
    
    # HLC Average for MACD calculation
    hlc_avg = VolumeWeightedIndicators.hlc_average(data.high, data.low, data.close)
    
    # Volume-Weighted MACD
    macd_line, signal_line, histogram = VolumeWeightedIndicators.vw_macd(hlc_avg, data.volume)
    indicators['vw_macd_hlc'] = macd_line
    indicators['vw_macd_signal_hlc'] = signal_line
    indicators['vw_macd_histogram_hlc'] = histogram
    
    return indicators


def calculate_all_risk_indicators(data: MarketData, account_balance: float = 100000) -> dict:
    """
    Calculate all risk and volatility indicators
    
    Args:
        data: MarketData object containing OHLCV data
        account_balance: Account balance for position sizing calculations
        
    Returns:
        Dictionary containing risk indicators
    """
    indicators = {}
    
    # ATR-based indicators for positional trading (21-day)
    indicators['atr_21'] = VolumeWeightedIndicators.atr(data, 21)
    indicators['atr_percent_21'] = VolumeWeightedIndicators.atr_percent(data, 21)
    indicators['market_norm_21'] = VolumeWeightedIndicators.market_normalization(data, 21)
    indicators['volatility_risk_21'] = VolumeWeightedIndicators.volatility_risk(data, 21)
    indicators['contract_risk_21'] = VolumeWeightedIndicators.contract_risk_units(data, 21, 2.0)
    indicators['max_lots_21'] = VolumeWeightedIndicators.max_lots_tradeable(account_balance, data, 21)
    
    # ATR-based indicators for intraday trading (8-day)
    indicators['atr_8'] = VolumeWeightedIndicators.atr(data, 8)
    indicators['atr_percent_8'] = VolumeWeightedIndicators.atr_percent(data, 8)
    indicators['market_norm_8'] = VolumeWeightedIndicators.market_normalization(data, 8)
    indicators['volatility_risk_8'] = VolumeWeightedIndicators.volatility_risk(data, 8)
    indicators['contract_risk_8'] = VolumeWeightedIndicators.contract_risk_units(data, 8, 0.75)
    
    # Strength/Weakness indicators
    indicators['strength_weakness_21'] = VolumeWeightedIndicators.strength_weakness_index(data, 21, 21)
    indicators['strength_weakness_8'] = VolumeWeightedIndicators.strength_weakness_index(data, 8, 8)
    
    return indicators


def calculate_all_market_mode_indicators(data: MarketData) -> dict:
    """
    Calculate market mode and trend indicators
    
    Args:
        data: MarketData object containing OHLCV data
        
    Returns:
        Dictionary containing market mode indicators
    """
    indicators = {}
    
    # Choppy Market Index and Market Mode
    indicators['choppy_index_21'] = VolumeWeightedIndicators.choppy_market_index(data, 21)
    indicators['market_mode_21'] = VolumeWeightedIndicators.market_mode(data, 21)
    indicators['choppy_index_8'] = VolumeWeightedIndicators.choppy_market_index(data, 8)
    indicators['market_mode_8'] = VolumeWeightedIndicators.market_mode(data, 8)
    
    # SMA Average Percent Changes
    indicators['sma_8_pct_change'] = VolumeWeightedIndicators.sma_average_percent_change(data.close, 8)
    indicators['sma_13_pct_change'] = VolumeWeightedIndicators.sma_average_percent_change(data.close, 13)
    indicators['sma_21_pct_change'] = VolumeWeightedIndicators.sma_average_percent_change(data.close, 21)
    
    # Buy/Sell Easier Days
    buy_easier, sell_easier = VolumeWeightedIndicators.buy_sell_easier_day(data, 21)
    indicators['buy_easier_day'] = buy_easier
    indicators['sell_easier_day'] = sell_easier
    
    # High-Low Range Average for ORB
    indicators['hl_range_avg'] = VolumeWeightedIndicators.high_low_range_average(data, 21)
    
    return indicators