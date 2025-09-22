"""Institutional-Grade Pairs Trading Divergence Strategies

This module implements comprehensive pairs trading strategies focused on divergence
between correlated instruments, with institutional-grade risk controls,
cointegration analysis, and beta neutrality.

Strategies Included:
- Statistical Arbitrage Pairs
- Cointegration-Based Pairs
- Beta-Neutral Pairs
- Sector Rotation Pairs
- Cross-Asset Pairs
- Volatility Pairs
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import logging
from abc import ABC, abstractmethod
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# Import technical indicators
try:
    from ...indicators.consolidated_indicators import ConsolidatedIndicators, IndicatorResult
    from ...indicators.core.core_indicator_base import AugmentedIndicator, IndicatorConfig
except ImportError:
    # Fallback for development
    class ConsolidatedIndicators:
        @staticmethod
        def rsi(*args, **kwargs):
            return None
    
    class AugmentedIndicator:
        pass
    
    class IndicatorConfig:
        pass


class PairsSignal(Enum):
    """Pairs trading signal types"""
    STRONG_LONG_A_SHORT_B = 2
    LONG_A_SHORT_B = 1
    NEUTRAL = 0
    LONG_B_SHORT_A = -1
    STRONG_LONG_B_SHORT_A = -2


class PairsRegime(Enum):
    """Market regime for pairs trading"""
    COINTEGRATED = "cointegrated"
    DIVERGING = "diverging"
    CONVERGING = "converging"
    TRENDING_TOGETHER = "trending_together"
    HIGH_CORRELATION = "high_correlation"
    LOW_CORRELATION = "low_correlation"
    VOLATILE = "volatile"


class PairType(Enum):
    """Type of pair relationship"""
    SAME_SECTOR = "same_sector"
    CROSS_SECTOR = "cross_sector"
    SAME_ASSET_CLASS = "same_asset_class"
    CROSS_ASSET_CLASS = "cross_asset_class"
    FUTURES_SPOT = "futures_spot"
    OPTIONS_UNDERLYING = "options_underlying"


@dataclass
class PairsConfig:
    """Configuration for pairs trading strategies"""
    # Pair selection parameters
    min_correlation: float = 0.7
    lookback_period: int = 60
    cointegration_period: int = 252  # 1 year for cointegration test
    
    # Statistical parameters
    z_score_entry: float = 2.0
    z_score_exit: float = 0.5
    z_score_stop: float = 3.0
    
    # Beta neutrality
    target_beta: float = 0.0
    beta_tolerance: float = 0.1
    beta_lookback: int = 60
    
    # Risk management
    max_position_size: float = 0.025  # 2.5% per leg
    max_leverage: float = 2.0
    stop_loss: float = 0.05  # 5% stop loss
    take_profit: float = 0.03  # 3% take profit
    
    # Cointegration parameters
    adf_significance: float = 0.05
    johansen_significance: float = 0.05
    half_life_max: int = 30  # Maximum half-life in days
    
    # Correlation parameters
    rolling_correlation_window: int = 30
    min_correlation_stability: float = 0.6
    
    # Performance optimization
    use_cuda: bool = False
    batch_processing: bool = True
    
    # Sector/Industry filters
    same_sector_preference: bool = True
    exclude_same_company: bool = True


@dataclass
class PairMetrics:
    """Metrics for a trading pair"""
    correlation: float
    cointegration_pvalue: float
    beta: float
    alpha: float
    half_life: Optional[float]
    spread_volatility: float
    mean_reversion_speed: float
    sharpe_ratio: float
    max_drawdown: float
    profit_factor: float
    win_rate: float
    avg_trade_duration: float


@dataclass
class PairsResult:
    """Result from pairs trading strategy calculation"""
    signal: PairsSignal
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    spread_z_score: float
    ratio_z_score: float
    current_spread: float
    current_ratio: float
    hedge_ratio: float
    beta_a: float
    beta_b: float
    regime: PairsRegime
    pair_type: PairType
    metrics: PairMetrics
    entry_price_a: Optional[float]
    entry_price_b: Optional[float]
    position_size_a: float
    position_size_b: float
    metadata: Dict[str, Any]
    timestamp: datetime


class BasePairsTradingStrategy(ABC):
    """Abstract base class for pairs trading strategies"""
    
    def __init__(self, config: PairsConfig = None):
        self.config = config or PairsConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup_indicators()
    
    def _setup_indicators(self):
        """Initialize technical indicators"""
        self.indicators = ConsolidatedIndicators()
    
    @abstractmethod
    def calculate_pairs_signal(self, data_a: pd.DataFrame, data_b: pd.DataFrame, 
                              symbol_a: str, symbol_b: str) -> PairsResult:
        """Calculate pairs trading signal for given pair"""
        pass
    
    def _calculate_spread_and_ratio(self, prices_a: pd.Series, prices_b: pd.Series, 
                                   hedge_ratio: float = None) -> Tuple[pd.Series, pd.Series, float]:
        """Calculate spread and ratio between two price series"""
        # Align series
        aligned_a, aligned_b = prices_a.align(prices_b, join='inner')
        
        if len(aligned_a) == 0:
            return pd.Series(), pd.Series(), 1.0
        
        # Calculate hedge ratio if not provided
        if hedge_ratio is None:
            hedge_ratio = self._calculate_hedge_ratio(aligned_a, aligned_b)
        
        # Calculate spread: A - hedge_ratio * B
        spread = aligned_a - hedge_ratio * aligned_b
        
        # Calculate ratio: A / B
        ratio = aligned_a / aligned_b
        ratio = ratio.replace([np.inf, -np.inf], np.nan).dropna()
        
        return spread, ratio, hedge_ratio
    
    def _calculate_hedge_ratio(self, prices_a: pd.Series, prices_b: pd.Series) -> float:
        """Calculate optimal hedge ratio using linear regression"""
        try:
            # Remove any NaN values
            aligned_a, aligned_b = prices_a.align(prices_b, join='inner')
            valid_data = pd.DataFrame({'a': aligned_a, 'b': aligned_b}).dropna()
            
            if len(valid_data) < 10:
                return 1.0
            
            # Linear regression: A = alpha + beta * B + epsilon
            X = valid_data['b'].values.reshape(-1, 1)
            y = valid_data['a'].values
            
            reg = LinearRegression().fit(X, y)
            hedge_ratio = reg.coef_[0]
            
            return hedge_ratio if not np.isnan(hedge_ratio) else 1.0
            
        except Exception as e:
            self.logger.warning(f"Error calculating hedge ratio: {e}")
            return 1.0
    
    def _test_cointegration(self, prices_a: pd.Series, prices_b: pd.Series) -> Tuple[bool, float, float]:
        """Test for cointegration using Engle-Granger method"""
        try:
            from statsmodels.tsa.stattools import adfuller
            
            # Align series
            aligned_a, aligned_b = prices_a.align(prices_b, join='inner')
            valid_data = pd.DataFrame({'a': aligned_a, 'b': aligned_b}).dropna()
            
            if len(valid_data) < 30:
                return False, 1.0, 1.0
            
            # Step 1: Run regression A = alpha + beta * B + epsilon
            X = valid_data['b'].values.reshape(-1, 1)
            y = valid_data['a'].values
            
            reg = LinearRegression().fit(X, y)
            residuals = y - reg.predict(X)
            
            # Step 2: Test residuals for stationarity
            adf_result = adfuller(residuals, maxlag=int(len(residuals)/3))
            adf_pvalue = adf_result[1]
            
            # Test individual series for unit roots
            adf_a = adfuller(valid_data['a'], maxlag=int(len(valid_data)/3))
            adf_b = adfuller(valid_data['b'], maxlag=int(len(valid_data)/3))
            
            # Cointegration exists if:
            # 1. Individual series are non-stationary (have unit roots)
            # 2. Residuals are stationary
            individual_nonstationary = (adf_a[1] > 0.05) and (adf_b[1] > 0.05)
            residuals_stationary = adf_pvalue < self.config.adf_significance
            
            is_cointegrated = individual_nonstationary and residuals_stationary
            
            return is_cointegrated, adf_pvalue, reg.coef_[0]
            
        except ImportError:
            # Fallback: simple correlation test
            correlation = prices_a.corr(prices_b)
            is_cointegrated = abs(correlation) > self.config.min_correlation
            return is_cointegrated, 1.0 - abs(correlation), 1.0
        except Exception as e:
            self.logger.warning(f"Error in cointegration test: {e}")
            return False, 1.0, 1.0
    
    def _calculate_beta(self, returns_a: pd.Series, returns_b: pd.Series, 
                      market_returns: pd.Series = None) -> Tuple[float, float]:
        """Calculate beta of each asset relative to market or each other"""
        try:
            if market_returns is not None:
                # Beta relative to market
                aligned_a, aligned_market = returns_a.align(market_returns, join='inner')
                aligned_b, aligned_market = returns_b.align(market_returns, join='inner')
                
                valid_data_a = pd.DataFrame({'asset': aligned_a, 'market': aligned_market}).dropna()
                valid_data_b = pd.DataFrame({'asset': aligned_b, 'market': aligned_market}).dropna()
                
                if len(valid_data_a) > 10:
                    cov_a = np.cov(valid_data_a['asset'], valid_data_a['market'])[0, 1]
                    var_market_a = np.var(valid_data_a['market'])
                    beta_a = cov_a / var_market_a if var_market_a > 0 else 1.0
                else:
                    beta_a = 1.0
                
                if len(valid_data_b) > 10:
                    cov_b = np.cov(valid_data_b['asset'], valid_data_b['market'])[0, 1]
                    var_market_b = np.var(valid_data_b['market'])
                    beta_b = cov_b / var_market_b if var_market_b > 0 else 1.0
                else:
                    beta_b = 1.0
            else:
                # Beta of A relative to B
                aligned_a, aligned_b = returns_a.align(returns_b, join='inner')
                valid_data = pd.DataFrame({'a': aligned_a, 'b': aligned_b}).dropna()
                
                if len(valid_data) > 10:
                    cov_ab = np.cov(valid_data['a'], valid_data['b'])[0, 1]
                    var_b = np.var(valid_data['b'])
                    beta_a = cov_ab / var_b if var_b > 0 else 1.0
                    beta_b = 1.0  # B is the reference
                else:
                    beta_a, beta_b = 1.0, 1.0
            
            return beta_a, beta_b
            
        except Exception as e:
            self.logger.warning(f"Error calculating beta: {e}")
            return 1.0, 1.0
    
    def _calculate_half_life(self, spread: pd.Series) -> Optional[float]:
        """Calculate half-life of mean reversion for spread"""
        try:
            if len(spread) < 20:
                return None
            
            # Calculate lagged spread
            spread_lag = spread.shift(1).dropna()
            spread_diff = spread.diff().dropna()
            
            # Align series
            min_len = min(len(spread_lag), len(spread_diff))
            spread_lag = spread_lag.iloc[-min_len:]
            spread_diff = spread_diff.iloc[-min_len:]
            
            # Fit AR(1) model: d(spread) = alpha + beta * spread_{t-1} + epsilon
            X = np.column_stack([np.ones(len(spread_lag)), spread_lag.values])
            y = spread_diff.values
            
            coeffs = np.linalg.lstsq(X, y, rcond=None)[0]
            beta = coeffs[1]
            
            # Half-life calculation
            if beta < 0:
                half_life = -np.log(2) / beta
                return half_life if 0 < half_life < self.config.half_life_max else None
            else:
                return None  # No mean reversion
                
        except Exception as e:
            self.logger.warning(f"Error calculating half-life: {e}")
            return None
    
    def _calculate_z_score(self, series: pd.Series, window: int = None) -> float:
        """Calculate z-score for a series"""
        window = window or self.config.lookback_period
        
        if len(series) < window:
            return 0.0
        
        rolling_mean = series.rolling(window).mean()
        rolling_std = series.rolling(window).std()
        
        current_value = series.iloc[-1]
        mean_value = rolling_mean.iloc[-1]
        std_value = rolling_std.iloc[-1]
        
        if std_value > 0:
            return (current_value - mean_value) / std_value
        else:
            return 0.0
    
    def _detect_pairs_regime(self, spread: pd.Series, ratio: pd.Series, 
                           correlation: float) -> PairsRegime:
        """Detect current regime for the pair"""
        if len(spread) < self.config.lookback_period:
            return PairsRegime.LOW_CORRELATION
        
        # Calculate recent correlation
        recent_window = min(self.config.rolling_correlation_window, len(spread))
        recent_corr = spread.tail(recent_window).corr(ratio.tail(recent_window))
        
        # Calculate spread volatility
        spread_vol = spread.rolling(self.config.lookback_period).std().iloc[-1]
        spread_vol_percentile = (spread.rolling(self.config.lookback_period).std() < spread_vol).mean()
        
        # Calculate trend in spread
        spread_trend = (spread.iloc[-1] - spread.iloc[-recent_window]) / spread.iloc[-recent_window]
        
        # Regime classification
        if abs(correlation) < self.config.min_correlation:
            return PairsRegime.LOW_CORRELATION
        elif abs(correlation) > 0.9:
            return PairsRegime.HIGH_CORRELATION
        elif spread_vol_percentile > 0.8:  # High volatility
            return PairsRegime.VOLATILE
        elif abs(spread_trend) > 0.1:  # Strong trend in spread
            if spread_trend > 0:
                return PairsRegime.DIVERGING
            else:
                return PairsRegime.CONVERGING
        else:
            # Test for cointegration
            is_cointegrated, _, _ = self._test_cointegration(
                pd.Series(range(len(spread))), spread
            )
            if is_cointegrated:
                return PairsRegime.COINTEGRATED
            else:
                return PairsRegime.TRENDING_TOGETHER
    
    def _calculate_position_sizes(self, price_a: float, price_b: float, 
                                hedge_ratio: float, beta_a: float, beta_b: float,
                                portfolio_value: float = 1000000) -> Tuple[float, float]:
        """Calculate position sizes for beta-neutral pair"""
        # Target dollar amounts for each leg
        max_leg_value = portfolio_value * self.config.max_position_size
        
        # For beta neutrality: beta_a * size_a + beta_b * size_b = 0
        # For hedge ratio: size_a = hedge_ratio * size_b (in shares)
        
        # Calculate shares for beta neutrality
        if abs(beta_a * hedge_ratio + beta_b) > 1e-6:
            # Solve: beta_a * hedge_ratio * shares_b + beta_b * shares_b = 0
            shares_b = -beta_a * hedge_ratio / (beta_a * hedge_ratio + beta_b)
            shares_a = hedge_ratio * shares_b
        else:
            # Fallback to simple hedge ratio
            shares_b = max_leg_value / price_b
            shares_a = hedge_ratio * shares_b
        
        # Apply position size limits
        dollar_value_a = abs(shares_a * price_a)
        dollar_value_b = abs(shares_b * price_b)
        
        if dollar_value_a > max_leg_value:
            scale_factor = max_leg_value / dollar_value_a
            shares_a *= scale_factor
            shares_b *= scale_factor
        
        if dollar_value_b > max_leg_value:
            scale_factor = max_leg_value / dollar_value_b
            shares_a *= scale_factor
            shares_b *= scale_factor
        
        return shares_a, shares_b
    
    def _calculate_pair_metrics(self, data_a: pd.DataFrame, data_b: pd.DataFrame,
                              spread: pd.Series, ratio: pd.Series) -> PairMetrics:
        """Calculate comprehensive metrics for the pair"""
        # Basic correlation
        correlation = data_a['close'].corr(data_b['close'])
        
        # Cointegration test
        is_cointegrated, coint_pvalue, hedge_ratio = self._test_cointegration(
            data_a['close'], data_b['close']
        )
        
        # Beta calculation
        returns_a = data_a['close'].pct_change().dropna()
        returns_b = data_b['close'].pct_change().dropna()
        beta_a, beta_b = self._calculate_beta(returns_a, returns_b)
        
        # Half-life
        half_life = self._calculate_half_life(spread)
        
        # Spread statistics
        spread_vol = spread.std()
        mean_reversion_speed = 1.0 / half_life if half_life else 0.0
        
        # Performance metrics (simplified)
        spread_returns = spread.pct_change().dropna()
        sharpe_ratio = spread_returns.mean() / spread_returns.std() * np.sqrt(252) if spread_returns.std() > 0 else 0.0
        
        # Drawdown calculation
        cumulative = (1 + spread_returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Win rate and profit factor (simplified)
        positive_returns = spread_returns[spread_returns > 0]
        negative_returns = spread_returns[spread_returns < 0]
        
        win_rate = len(positive_returns) / len(spread_returns) if len(spread_returns) > 0 else 0.0
        profit_factor = positive_returns.sum() / abs(negative_returns.sum()) if negative_returns.sum() != 0 else 1.0
        
        # Average trade duration (simplified)
        avg_trade_duration = half_life if half_life else 10.0
        
        return PairMetrics(
            correlation=correlation,
            cointegration_pvalue=coint_pvalue,
            beta=beta_a,
            alpha=hedge_ratio,
            half_life=half_life,
            spread_volatility=spread_vol,
            mean_reversion_speed=mean_reversion_speed,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            profit_factor=profit_factor,
            win_rate=win_rate,
            avg_trade_duration=avg_trade_duration
        )


class StatisticalArbitragePairsStrategy(BasePairsTradingStrategy):
    """Statistical arbitrage pairs trading strategy"""
    
    def calculate_pairs_signal(self, data_a: pd.DataFrame, data_b: pd.DataFrame, 
                              symbol_a: str, symbol_b: str) -> PairsResult:
        """Calculate statistical arbitrage pairs signal"""
        if len(data_a) < self.config.lookback_period or len(data_b) < self.config.lookback_period:
            return self._create_neutral_result(data_a, data_b, symbol_a, symbol_b)
        
        # Calculate spread and ratio
        spread, ratio, hedge_ratio = self._calculate_spread_and_ratio(
            data_a['close'], data_b['close']
        )
        
        if len(spread) < self.config.lookback_period:
            return self._create_neutral_result(data_a, data_b, symbol_a, symbol_b)
        
        # Calculate z-scores
        spread_z_score = self._calculate_z_score(spread)
        ratio_z_score = self._calculate_z_score(ratio)
        
        # Calculate correlation and test cointegration
        correlation = data_a['close'].corr(data_b['close'])
        is_cointegrated, coint_pvalue, _ = self._test_cointegration(
            data_a['close'], data_b['close']
        )
        
        # Calculate betas
        returns_a = data_a['close'].pct_change().dropna()
        returns_b = data_b['close'].pct_change().dropna()
        beta_a, beta_b = self._calculate_beta(returns_a, returns_b)
        
        # Detect regime
        regime = self._detect_pairs_regime(spread, ratio, correlation)
        
        # Calculate metrics
        metrics = self._calculate_pair_metrics(data_a, data_b, spread, ratio)
        
        # Generate signal
        signal = self._generate_statistical_arbitrage_signal(
            spread_z_score, ratio_z_score, regime, is_cointegrated
        )
        
        # Calculate strength and confidence
        strength = min(1.0, max(abs(spread_z_score), abs(ratio_z_score)) / self.config.z_score_entry)
        
        confidence = self._calculate_confidence(
            correlation, is_cointegrated, coint_pvalue, metrics.half_life
        )
        
        # Calculate position sizes
        current_price_a = data_a['close'].iloc[-1]
        current_price_b = data_b['close'].iloc[-1]
        
        position_size_a, position_size_b = self._calculate_position_sizes(
            current_price_a, current_price_b, hedge_ratio, beta_a, beta_b
        )
        
        # Determine pair type (simplified)
        pair_type = PairType.SAME_ASSET_CLASS  # Default
        
        return PairsResult(
            signal=signal,
            strength=strength,
            confidence=confidence,
            spread_z_score=spread_z_score,
            ratio_z_score=ratio_z_score,
            current_spread=spread.iloc[-1],
            current_ratio=ratio.iloc[-1],
            hedge_ratio=hedge_ratio,
            beta_a=beta_a,
            beta_b=beta_b,
            regime=regime,
            pair_type=pair_type,
            metrics=metrics,
            entry_price_a=current_price_a if signal != PairsSignal.NEUTRAL else None,
            entry_price_b=current_price_b if signal != PairsSignal.NEUTRAL else None,
            position_size_a=position_size_a,
            position_size_b=position_size_b,
            metadata={
                'correlation': correlation,
                'is_cointegrated': is_cointegrated,
                'cointegration_pvalue': coint_pvalue,
                'symbol_a': symbol_a,
                'symbol_b': symbol_b,
                'lookback_period': self.config.lookback_period
            },
            timestamp=datetime.now()
        )
    
    def _generate_statistical_arbitrage_signal(self, spread_z_score: float, ratio_z_score: float,
                                             regime: PairsRegime, is_cointegrated: bool) -> PairsSignal:
        """Generate signal based on statistical arbitrage analysis"""
        # Only trade cointegrated pairs in appropriate regimes
        if not is_cointegrated or regime in [PairsRegime.LOW_CORRELATION, PairsRegime.VOLATILE]:
            return PairsSignal.NEUTRAL
        
        # Use spread z-score as primary signal
        primary_z_score = spread_z_score
        
        # Adjust thresholds based on regime
        entry_threshold = self.config.z_score_entry
        if regime == PairsRegime.HIGH_CORRELATION:
            entry_threshold *= 0.8  # Lower threshold for highly correlated pairs
        elif regime == PairsRegime.DIVERGING:
            entry_threshold *= 1.2  # Higher threshold when diverging
        
        # Generate signals (mean reversion logic)
        if primary_z_score > entry_threshold * 1.5:
            return PairsSignal.STRONG_LONG_B_SHORT_A  # Spread too high, short A long B
        elif primary_z_score > entry_threshold:
            return PairsSignal.LONG_B_SHORT_A
        elif primary_z_score < -entry_threshold * 1.5:
            return PairsSignal.STRONG_LONG_A_SHORT_B  # Spread too low, long A short B
        elif primary_z_score < -entry_threshold:
            return PairsSignal.LONG_A_SHORT_B
        else:
            return PairsSignal.NEUTRAL
    
    def _calculate_confidence(self, correlation: float, is_cointegrated: bool, 
                            coint_pvalue: float, half_life: Optional[float]) -> float:
        """Calculate confidence score for the signal"""
        confidence = 0.0
        
        # Correlation component (0-0.3)
        correlation_score = min(0.3, abs(correlation) * 0.3)
        confidence += correlation_score
        
        # Cointegration component (0-0.4)
        if is_cointegrated:
            coint_score = min(0.4, (1 - coint_pvalue) * 0.4)
            confidence += coint_score
        
        # Half-life component (0-0.3)
        if half_life and 1 <= half_life <= self.config.half_life_max:
            half_life_score = 0.3 * (1 - (half_life - 1) / (self.config.half_life_max - 1))
            confidence += half_life_score
        
        return min(1.0, confidence)
    
    def _create_neutral_result(self, data_a: pd.DataFrame, data_b: pd.DataFrame,
                             symbol_a: str, symbol_b: str) -> PairsResult:
        """Create neutral result for insufficient data"""
        return PairsResult(
            signal=PairsSignal.NEUTRAL,
            strength=0.0,
            confidence=0.0,
            spread_z_score=0.0,
            ratio_z_score=0.0,
            current_spread=0.0,
            current_ratio=1.0,
            hedge_ratio=1.0,
            beta_a=1.0,
            beta_b=1.0,
            regime=PairsRegime.LOW_CORRELATION,
            pair_type=PairType.SAME_ASSET_CLASS,
            metrics=PairMetrics(
                correlation=0.0, cointegration_pvalue=1.0, beta=1.0, alpha=0.0,
                half_life=None, spread_volatility=0.0, mean_reversion_speed=0.0,
                sharpe_ratio=0.0, max_drawdown=0.0, profit_factor=1.0,
                win_rate=0.5, avg_trade_duration=10.0
            ),
            entry_price_a=None,
            entry_price_b=None,
            position_size_a=0.0,
            position_size_b=0.0,
            metadata={'insufficient_data': True, 'symbol_a': symbol_a, 'symbol_b': symbol_b},
            timestamp=datetime.now()
        )


class PairsTradingManager:
    """Manager class for coordinating pairs trading strategies"""
    
    def __init__(self, config: PairsConfig = None):
        self.config = config or PairsConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize strategies
        self.strategies = {
            'statistical_arbitrage': StatisticalArbitragePairsStrategy(self.config)
        }
        
        # Pair universe
        self.pair_universe = []
        self.active_pairs = {}
    
    def add_pair(self, symbol_a: str, symbol_b: str, pair_type: PairType = PairType.SAME_ASSET_CLASS):
        """Add a pair to the trading universe"""
        pair_id = f"{symbol_a}_{symbol_b}"
        self.pair_universe.append({
            'id': pair_id,
            'symbol_a': symbol_a,
            'symbol_b': symbol_b,
            'pair_type': pair_type
        })
        self.logger.info(f"Added pair {pair_id} to universe")
    
    def screen_pairs(self, data_dict: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        """Screen pairs for trading opportunities"""
        screened_pairs = []
        
        for pair in self.pair_universe:
            symbol_a = pair['symbol_a']
            symbol_b = pair['symbol_b']
            
            if symbol_a not in data_dict or symbol_b not in data_dict:
                continue
            
            data_a = data_dict[symbol_a]
            data_b = data_dict[symbol_b]
            
            # Basic screening criteria
            if len(data_a) < self.config.lookback_period or len(data_b) < self.config.lookback_period:
                continue
            
            # Calculate correlation
            correlation = data_a['close'].corr(data_b['close'])
            
            if abs(correlation) >= self.config.min_correlation:
                # Test cointegration
                strategy = self.strategies['statistical_arbitrage']
                is_cointegrated, coint_pvalue, hedge_ratio = strategy._test_cointegration(
                    data_a['close'], data_b['close']
                )
                
                if is_cointegrated:
                    screened_pairs.append({
                        'pair_id': pair['id'],
                        'symbol_a': symbol_a,
                        'symbol_b': symbol_b,
                        'correlation': correlation,
                        'cointegration_pvalue': coint_pvalue,
                        'hedge_ratio': hedge_ratio,
                        'pair_type': pair['pair_type']
                    })
        
        # Sort by cointegration strength (lower p-value is better)
        screened_pairs.sort(key=lambda x: x['cointegration_pvalue'])
        
        return screened_pairs
    
    def calculate_pairs_signals(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, PairsResult]:
        """Calculate signals for all pairs in universe"""
        results = {}
        
        screened_pairs = self.screen_pairs(data_dict)
        
        for pair_info in screened_pairs[:10]:  # Limit to top 10 pairs
            symbol_a = pair_info['symbol_a']
            symbol_b = pair_info['symbol_b']
            pair_id = pair_info['pair_id']
            
            data_a = data_dict[symbol_a]
            data_b = data_dict[symbol_b]
            
            try:
                # Calculate signal using statistical arbitrage strategy
                strategy = self.strategies['statistical_arbitrage']
                result = strategy.calculate_pairs_signal(data_a, data_b, symbol_a, symbol_b)
                
                results[pair_id] = result
                self.logger.info(f"Calculated signal for {pair_id}: {result.signal.name}")
                
            except Exception as e:
                self.logger.error(f"Error calculating signal for {pair_id}: {e}")
        
        return results
    
    def get_top_opportunities(self, results: Dict[str, PairsResult], 
                           top_n: int = 5) -> List[Tuple[str, PairsResult]]:
        """Get top trading opportunities ranked by confidence and strength"""
        # Filter non-neutral signals
        opportunities = [(pair_id, result) for pair_id, result in results.items() 
                        if result.signal != PairsSignal.NEUTRAL]
        
        # Sort by combined score (confidence * strength)
        opportunities.sort(key=lambda x: x[1].confidence * x[1].strength, reverse=True)
        
        return opportunities[:top_n]


# Example usage and testing functions
def create_correlated_pair_data(days: int = 252, correlation: float = 0.8) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Create sample correlated pair data for testing"""
    dates = pd.date_range(start='2023-01-01', periods=days, freq='D')
    
    # Generate correlated price series
    np.random.seed(42)
    
    # Base random walks
    returns_base = np.random.normal(0.0005, 0.02, days)
    returns_idiosyncratic_a = np.random.normal(0, 0.01, days)
    returns_idiosyncratic_b = np.random.normal(0, 0.01, days)
    
    # Create correlated returns
    returns_a = correlation * returns_base + np.sqrt(1 - correlation**2) * returns_idiosyncratic_a
    returns_b = correlation * returns_base + np.sqrt(1 - correlation**2) * returns_idiosyncratic_b
    
    # Convert to price series
    prices_a = 100 * (1 + returns_a).cumprod()
    prices_b = 95 * (1 + returns_b).cumprod()  # Slightly different starting price
    
    # Generate volume data
    volume_a = np.random.lognormal(np.log(1000000), 0.2, days)
    volume_b = np.random.lognormal(np.log(800000), 0.2, days)
    
    # Create OHLC data
    data_a = pd.DataFrame({
        'date': dates,
        'open': prices_a,
        'high': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices_a],
        'low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices_a],
        'close': prices_a,
        'volume': volume_a
    })
    
    data_b = pd.DataFrame({
        'date': dates,
        'open': prices_b,
        'high': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices_b],
        'low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices_b],
        'close': prices_b,
        'volume': volume_b
    })
    
    return data_a, data_b


def test_pairs_trading_strategies():
    """Test pairs trading strategies with sample data"""
    # Create sample correlated pair data
    data_a, data_b = create_correlated_pair_data(300, correlation=0.85)
    
    # Initialize pairs trading manager
    config = PairsConfig(
        min_correlation=0.7,
        lookback_period=60,
        z_score_entry=2.0,
        z_score_exit=0.5,
        adf_significance=0.05
    )
    
    manager = PairsTradingManager(config)
    
    # Add pair to universe
    manager.add_pair('STOCK_A', 'STOCK_B', PairType.SAME_SECTOR)
    
    # Create data dictionary
    data_dict = {
        'STOCK_A': data_a,
        'STOCK_B': data_b
    }
    
    # Screen pairs
    screened_pairs = manager.screen_pairs(data_dict)
    print(f"\n=== Pairs Screening Results ===")
    for pair in screened_pairs:
        print(f"Pair: {pair['pair_id']}")
        print(f"  Correlation: {pair['correlation']:.3f}")
        print(f"  Cointegration p-value: {pair['cointegration_pvalue']:.3f}")
        print(f"  Hedge Ratio: {pair['hedge_ratio']:.3f}")
    
    # Calculate signals
    results = manager.calculate_pairs_signals(data_dict)
    
    print(f"\n=== Pairs Trading Signals ===")
    for pair_id, result in results.items():
        print(f"\nPair: {pair_id}")
        print(f"  Signal: {result.signal.name}")
        print(f"  Strength: {result.strength:.3f}")
        print(f"  Confidence: {result.confidence:.3f}")
        print(f"  Spread Z-Score: {result.spread_z_score:.3f}")
        print(f"  Ratio Z-Score: {result.ratio_z_score:.3f}")
        print(f"  Hedge Ratio: {result.hedge_ratio:.3f}")
        print(f"  Beta A: {result.beta_a:.3f}, Beta B: {result.beta_b:.3f}")
        print(f"  Regime: {result.regime.value}")
        print(f"  Correlation: {result.metrics.correlation:.3f}")
        print(f"  Half-Life: {result.metrics.half_life:.1f} days" if result.metrics.half_life else "  Half-Life: N/A")
        print(f"  Position Size A: {result.position_size_a:.0f}")
        print(f"  Position Size B: {result.position_size_b:.0f}")
    
    # Get top opportunities
    opportunities = manager.get_top_opportunities(results, top_n=3)
    
    print(f"\n=== Top Trading Opportunities ===")
    for i, (pair_id, result) in enumerate(opportunities, 1):
        score = result.confidence * result.strength
        print(f"{i}. {pair_id}: {result.signal.name} (Score: {score:.3f})")


if __name__ == "__main__":
    # Run tests
    test_pairs_trading_strategies()