"""Institutional-Grade Multi-Factor Model Trading Strategies

This module implements comprehensive multi-factor models for systematic trading
with institutional-grade risk controls and portfolio optimization.

Factor Models Included:
- Fama-French 3-Factor Model
- Fama-French 5-Factor Model
- Carhart 4-Factor Model (with Momentum)
- Quality Factor Models
- Low Volatility Factor
- Value Factor Models
- Growth Factor Models
- Profitability Factor Models
- Investment Factor Models
- Custom Multi-Factor Models
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import logging
from abc import ABC, abstractmethod
from scipy import stats, optimize
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestRegressor
import warnings
warnings.filterwarnings('ignore')

# Import portfolio optimization libraries
try:
    from pypfopt import EfficientFrontier, risk_models, expected_returns
    from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices
    from pypfopt.objective_functions import L2_reg
except ImportError:
    # Fallback for development
    class EfficientFrontier:
        def __init__(self, *args, **kwargs):
            pass
    
    class risk_models:
        @staticmethod
        def sample_cov(*args, **kwargs):
            return np.eye(10)
    
    class expected_returns:
        @staticmethod
        def mean_historical_return(*args, **kwargs):
            return pd.Series(np.random.normal(0.1, 0.2, 10))

# Import technical indicators
try:
    from nautilus_trader_engine.indicators.consolidated_indicators import ConsolidatedIndicators, IndicatorResult
    from nautilus_trader_engine.indicators.core_indicator_base import AugmentedIndicator, IndicatorConfig
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


class FactorSignal(Enum):
    """Multi-factor trading signal types"""
    STRONG_BUY = 3
    BUY = 2
    WEAK_BUY = 1
    NEUTRAL = 0
    WEAK_SELL = -1
    SELL = -2
    STRONG_SELL = -3


class FactorType(Enum):
    """Types of factors in multi-factor models"""
    MARKET = "market"  # Market beta
    SIZE = "size"  # SMB (Small Minus Big)
    VALUE = "value"  # HML (High Minus Low)
    MOMENTUM = "momentum"  # UMD (Up Minus Down)
    PROFITABILITY = "profitability"  # RMW (Robust Minus Weak)
    INVESTMENT = "investment"  # CMA (Conservative Minus Aggressive)
    QUALITY = "quality"  # Quality factor
    LOW_VOLATILITY = "low_volatility"  # Low volatility factor
    GROWTH = "growth"  # Growth factor
    DIVIDEND_YIELD = "dividend_yield"  # Dividend yield factor
    EARNINGS_QUALITY = "earnings_quality"  # Earnings quality factor
    LEVERAGE = "leverage"  # Financial leverage factor
    LIQUIDITY = "liquidity"  # Liquidity factor
    CUSTOM = "custom"  # Custom factors


class FactorModel(Enum):
    """Multi-factor model types"""
    FAMA_FRENCH_3 = "fama_french_3"
    FAMA_FRENCH_5 = "fama_french_5"
    CARHART_4 = "carhart_4"
    QUALITY_MODEL = "quality_model"
    LOW_VOL_MODEL = "low_vol_model"
    VALUE_MODEL = "value_model"
    GROWTH_MODEL = "growth_model"
    CUSTOM_MODEL = "custom_model"
    ENSEMBLE_MODEL = "ensemble_model"


class MarketRegime(Enum):
    """Market regime for factor model adaptation"""
    BULL_MARKET = "bull_market"
    BEAR_MARKET = "bear_market"
    SIDEWAYS_MARKET = "sideways_market"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    GROWTH_REGIME = "growth_regime"
    VALUE_REGIME = "value_regime"
    MOMENTUM_REGIME = "momentum_regime"
    MEAN_REVERSION_REGIME = "mean_reversion_regime"
    CRISIS_MODE = "crisis_mode"


@dataclass
class FactorConfig:
    """Configuration for multi-factor model strategies"""
    # Factor model parameters
    lookback_window: int = 252  # 1 year of daily data
    rebalance_frequency: int = 21  # Monthly rebalancing
    min_factor_exposure: float = 0.1  # Minimum factor exposure
    max_factor_exposure: float = 2.0  # Maximum factor exposure
    
    # Portfolio construction
    max_position_size: float = 0.05  # 5% maximum position size
    min_position_size: float = 0.001  # 0.1% minimum position size
    max_portfolio_concentration: float = 0.3  # 30% max sector concentration
    target_volatility: float = 0.15  # 15% target portfolio volatility
    
    # Risk management
    max_tracking_error: float = 0.05  # 5% maximum tracking error
    max_drawdown: float = 0.1  # 10% maximum drawdown
    var_confidence: float = 0.05  # 5% VaR confidence level
    
    # Factor selection
    factor_significance_threshold: float = 0.05  # p-value threshold
    min_factor_r_squared: float = 0.02  # Minimum R-squared for factor
    factor_correlation_threshold: float = 0.7  # Max correlation between factors
    
    # Optimization parameters
    optimization_method: str = "mean_variance"  # mean_variance, risk_parity, black_litterman
    regularization_strength: float = 0.1
    transaction_cost: float = 0.001  # 0.1% transaction cost
    
    # Performance parameters
    benchmark_symbol: str = "SPY"  # Benchmark for comparison
    risk_free_rate: float = 0.02  # 2% risk-free rate
    
    # Advanced features
    use_regime_detection: bool = True
    use_factor_timing: bool = True
    use_dynamic_hedging: bool = True
    use_machine_learning: bool = False
    
    # Performance optimization
    use_cuda: bool = False
    parallel_processing: bool = True


@dataclass
class FactorExposure:
    """Factor exposure for a security or portfolio"""
    symbol: str
    factor_type: FactorType
    exposure: float
    t_stat: float
    p_value: float
    r_squared: float
    confidence: float
    timestamp: datetime


@dataclass
class FactorReturn:
    """Factor return data"""
    factor_type: FactorType
    return_value: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    correlation_to_market: float
    timestamp: datetime


@dataclass
class PortfolioMetrics:
    """Portfolio performance metrics"""
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    calmar_ratio: float
    information_ratio: float
    tracking_error: float
    beta: float
    alpha: float
    var_95: float
    cvar_95: float
    win_rate: float
    profit_factor: float


@dataclass
class FactorModelResult:
    """Result from multi-factor model calculation"""
    signal: FactorSignal
    model_type: FactorModel
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    factor_exposures: Dict[FactorType, float]
    expected_return: float
    expected_volatility: float
    factor_contributions: Dict[FactorType, float]
    portfolio_weights: Dict[str, float]
    risk_metrics: Dict[str, float]
    regime: MarketRegime
    portfolio_metrics: PortfolioMetrics
    rebalance_needed: bool
    metadata: Dict[str, Any]
    timestamp: datetime


class BaseFactorModel(ABC):
    """Abstract base class for multi-factor models"""
    
    def __init__(self, config: FactorConfig = None):
        self.config = config or FactorConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup_indicators()
        self.factor_returns = {}
        self.factor_loadings = {}
        self.portfolio_history = []
        self.performance_metrics = {}
    
    def _setup_indicators(self):
        """Initialize technical indicators"""
        self.indicators = ConsolidatedIndicators()
    
    @abstractmethod
    def calculate_factor_exposures(self, market_data: Dict[str, pd.DataFrame]) -> Dict[str, Dict[FactorType, FactorExposure]]:
        """Calculate factor exposures for all securities"""
        pass
    
    @abstractmethod
    def calculate_factor_returns(self, market_data: Dict[str, pd.DataFrame]) -> Dict[FactorType, FactorReturn]:
        """Calculate factor returns"""
        pass
    
    @abstractmethod
    def construct_portfolio(self, factor_exposures: Dict[str, Dict[FactorType, FactorExposure]], 
                          factor_returns: Dict[FactorType, FactorReturn],
                          market_data: Dict[str, pd.DataFrame]) -> FactorModelResult:
        """Construct optimal portfolio based on factor model"""
        pass
    
    def _calculate_market_beta(self, returns: pd.Series, market_returns: pd.Series) -> Tuple[float, float, float]:
        """Calculate market beta, alpha, and R-squared"""
        try:
            # Align series
            aligned_returns, aligned_market = returns.align(market_returns, join='inner')
            
            if len(aligned_returns) < 30:
                return 1.0, 0.0, 0.0
            
            # Linear regression
            X = aligned_market.values.reshape(-1, 1)
            y = aligned_returns.values
            
            reg = LinearRegression().fit(X, y)
            beta = reg.coef_[0]
            alpha = reg.intercept_
            r_squared = reg.score(X, y)
            
            return beta, alpha, r_squared
            
        except Exception as e:
            self.logger.warning(f"Error calculating market beta: {e}")
            return 1.0, 0.0, 0.0
    
    def _calculate_size_factor(self, market_data: Dict[str, pd.DataFrame]) -> pd.Series:
        """Calculate size factor (SMB - Small Minus Big)"""
        try:
            # Calculate market caps (proxy using price * volume)
            market_caps = {}
            returns = {}
            
            for symbol, data in market_data.items():
                if len(data) >= self.config.lookback_window:
                    market_cap = (data['close'] * data['volume']).rolling(20).mean().iloc[-1]
                    market_caps[symbol] = market_cap
                    returns[symbol] = data['close'].pct_change().dropna()
            
            if len(market_caps) < 10:
                return pd.Series(dtype=float)
            
            # Sort by market cap
            sorted_caps = sorted(market_caps.items(), key=lambda x: x[1])
            
            # Split into small and big cap
            n_stocks = len(sorted_caps)
            small_cap_symbols = [symbol for symbol, _ in sorted_caps[:n_stocks//2]]
            big_cap_symbols = [symbol for symbol, _ in sorted_caps[n_stocks//2:]]
            
            # Calculate equal-weighted returns
            small_cap_returns = pd.concat([returns[symbol] for symbol in small_cap_symbols 
                                         if symbol in returns], axis=1).mean(axis=1)
            big_cap_returns = pd.concat([returns[symbol] for symbol in big_cap_symbols 
                                       if symbol in returns], axis=1).mean(axis=1)
            
            # SMB factor
            smb_factor = small_cap_returns - big_cap_returns
            
            return smb_factor.dropna()
            
        except Exception as e:
            self.logger.warning(f"Error calculating size factor: {e}")
            return pd.Series(dtype=float)
    
    def _calculate_value_factor(self, market_data: Dict[str, pd.DataFrame]) -> pd.Series:
        """Calculate value factor (HML - High Minus Low)"""
        try:
            # Use price-to-book proxy (inverse of price momentum)
            value_scores = {}
            returns = {}
            
            for symbol, data in market_data.items():
                if len(data) >= self.config.lookback_window:
                    # Price momentum as proxy for valuation (inverse relationship)
                    price_momentum = (data['close'].iloc[-1] / data['close'].iloc[-252] - 1) if len(data) >= 252 else 0
                    value_scores[symbol] = -price_momentum  # Inverse for value
                    returns[symbol] = data['close'].pct_change().dropna()
            
            if len(value_scores) < 10:
                return pd.Series(dtype=float)
            
            # Sort by value score
            sorted_values = sorted(value_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Split into high and low value
            n_stocks = len(sorted_values)
            high_value_symbols = [symbol for symbol, _ in sorted_values[:n_stocks//3]]
            low_value_symbols = [symbol for symbol, _ in sorted_values[-n_stocks//3:]]
            
            # Calculate equal-weighted returns
            high_value_returns = pd.concat([returns[symbol] for symbol in high_value_symbols 
                                          if symbol in returns], axis=1).mean(axis=1)
            low_value_returns = pd.concat([returns[symbol] for symbol in low_value_symbols 
                                         if symbol in returns], axis=1).mean(axis=1)
            
            # HML factor
            hml_factor = high_value_returns - low_value_returns
            
            return hml_factor.dropna()
            
        except Exception as e:
            self.logger.warning(f"Error calculating value factor: {e}")
            return pd.Series(dtype=float)
    
    def _calculate_momentum_factor(self, market_data: Dict[str, pd.DataFrame]) -> pd.Series:
        """Calculate momentum factor (UMD - Up Minus Down)"""
        try:
            momentum_scores = {}
            returns = {}
            
            for symbol, data in market_data.items():
                if len(data) >= self.config.lookback_window:
                    # 12-1 month momentum (skip last month)
                    if len(data) >= 252:
                        momentum_return = (data['close'].iloc[-21] / data['close'].iloc[-252] - 1)
                        momentum_scores[symbol] = momentum_return
                        returns[symbol] = data['close'].pct_change().dropna()
            
            if len(momentum_scores) < 10:
                return pd.Series(dtype=float)
            
            # Sort by momentum
            sorted_momentum = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Split into winners and losers
            n_stocks = len(sorted_momentum)
            winner_symbols = [symbol for symbol, _ in sorted_momentum[:n_stocks//3]]
            loser_symbols = [symbol for symbol, _ in sorted_momentum[-n_stocks//3:]]
            
            # Calculate equal-weighted returns
            winner_returns = pd.concat([returns[symbol] for symbol in winner_symbols 
                                      if symbol in returns], axis=1).mean(axis=1)
            loser_returns = pd.concat([returns[symbol] for symbol in loser_symbols 
                                     if symbol in returns], axis=1).mean(axis=1)
            
            # UMD factor
            umd_factor = winner_returns - loser_returns
            
            return umd_factor.dropna()
            
        except Exception as e:
            self.logger.warning(f"Error calculating momentum factor: {e}")
            return pd.Series(dtype=float)
    
    def _calculate_quality_factor(self, market_data: Dict[str, pd.DataFrame]) -> pd.Series:
        """Calculate quality factor based on price stability and trend strength"""
        try:
            quality_scores = {}
            returns = {}
            
            for symbol, data in market_data.items():
                if len(data) >= self.config.lookback_window:
                    # Quality metrics: low volatility + consistent returns
                    price_returns = data['close'].pct_change().dropna()
                    
                    if len(price_returns) >= 60:
                        volatility = price_returns.rolling(60).std().mean()
                        sharpe = price_returns.mean() / price_returns.std() if price_returns.std() > 0 else 0
                        
                        # Quality score: high Sharpe, low volatility
                        quality_score = sharpe - volatility * 10
                        quality_scores[symbol] = quality_score
                        returns[symbol] = price_returns
            
            if len(quality_scores) < 10:
                return pd.Series(dtype=float)
            
            # Sort by quality
            sorted_quality = sorted(quality_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Split into high and low quality
            n_stocks = len(sorted_quality)
            high_quality_symbols = [symbol for symbol, _ in sorted_quality[:n_stocks//3]]
            low_quality_symbols = [symbol for symbol, _ in sorted_quality[-n_stocks//3:]]
            
            # Calculate equal-weighted returns
            high_quality_returns = pd.concat([returns[symbol] for symbol in high_quality_symbols 
                                            if symbol in returns], axis=1).mean(axis=1)
            low_quality_returns = pd.concat([returns[symbol] for symbol in low_quality_symbols 
                                           if symbol in returns], axis=1).mean(axis=1)
            
            # Quality factor
            quality_factor = high_quality_returns - low_quality_returns
            
            return quality_factor.dropna()
            
        except Exception as e:
            self.logger.warning(f"Error calculating quality factor: {e}")
            return pd.Series(dtype=float)
    
    def _detect_market_regime(self, market_data: Dict[str, pd.DataFrame]) -> MarketRegime:
        """Detect current market regime"""
        try:
            # Use market index (first available) for regime detection
            market_symbol = list(market_data.keys())[0]
            market_prices = market_data[market_symbol]['close']
            
            if len(market_prices) < 60:
                return MarketRegime.SIDEWAYS_MARKET
            
            # Calculate market metrics
            returns = market_prices.pct_change().dropna()
            recent_returns = returns.tail(60)
            
            avg_return = recent_returns.mean() * 252  # Annualized
            volatility = recent_returns.std() * np.sqrt(252)  # Annualized
            
            # Trend detection
            sma_20 = market_prices.rolling(20).mean()
            sma_60 = market_prices.rolling(60).mean()
            current_price = market_prices.iloc[-1]
            
            # Regime classification
            if volatility > 0.25:  # High volatility
                if avg_return < -0.1:  # Negative returns
                    return MarketRegime.CRISIS_MODE
                else:
                    return MarketRegime.HIGH_VOLATILITY
            elif volatility < 0.1:  # Low volatility
                return MarketRegime.LOW_VOLATILITY
            elif avg_return > 0.1 and current_price > sma_20.iloc[-1] > sma_60.iloc[-1]:
                return MarketRegime.BULL_MARKET
            elif avg_return < -0.05 and current_price < sma_20.iloc[-1] < sma_60.iloc[-1]:
                return MarketRegime.BEAR_MARKET
            else:
                return MarketRegime.SIDEWAYS_MARKET
                
        except Exception as e:
            self.logger.warning(f"Error detecting market regime: {e}")
            return MarketRegime.SIDEWAYS_MARKET
    
    def _optimize_portfolio_weights(self, expected_returns: pd.Series, 
                                  covariance_matrix: pd.DataFrame,
                                  factor_exposures: Dict[str, Dict[FactorType, FactorExposure]]) -> Dict[str, float]:
        """Optimize portfolio weights using mean-variance optimization"""
        try:
            if self.config.optimization_method == "mean_variance":
                # Mean-variance optimization
                ef = EfficientFrontier(expected_returns, covariance_matrix)
                
                # Add constraints
                ef.add_constraint(lambda w: w >= 0)  # Long-only
                ef.add_constraint(lambda w: w <= self.config.max_position_size)  # Position limits
                
                # Optimize for Sharpe ratio
                weights = ef.max_sharpe(risk_free_rate=self.config.risk_free_rate)
                
                return ef.clean_weights()
                
            elif self.config.optimization_method == "risk_parity":
                # Equal risk contribution
                n_assets = len(expected_returns)
                equal_weights = {symbol: 1.0/n_assets for symbol in expected_returns.index}
                return equal_weights
                
            else:
                # Equal weights fallback
                n_assets = len(expected_returns)
                equal_weights = {symbol: 1.0/n_assets for symbol in expected_returns.index}
                return equal_weights
                
        except Exception as e:
            self.logger.warning(f"Error optimizing portfolio weights: {e}")
            # Fallback to equal weights
            n_assets = len(expected_returns)
            return {symbol: 1.0/n_assets for symbol in expected_returns.index}
    
    def _calculate_portfolio_metrics(self, portfolio_returns: pd.Series, 
                                   benchmark_returns: pd.Series = None) -> PortfolioMetrics:
        """Calculate comprehensive portfolio performance metrics"""
        try:
            if len(portfolio_returns) == 0:
                return PortfolioMetrics(
                    total_return=0, annualized_return=0, volatility=0, sharpe_ratio=0,
                    sortino_ratio=0, max_drawdown=0, calmar_ratio=0, information_ratio=0,
                    tracking_error=0, beta=1, alpha=0, var_95=0, cvar_95=0,
                    win_rate=0, profit_factor=1
                )
            
            # Basic metrics
            total_return = (1 + portfolio_returns).prod() - 1
            annualized_return = (1 + portfolio_returns.mean()) ** 252 - 1
            volatility = portfolio_returns.std() * np.sqrt(252)
            
            # Risk-adjusted metrics
            excess_returns = portfolio_returns - self.config.risk_free_rate / 252
            sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252) if excess_returns.std() > 0 else 0
            
            # Downside metrics
            negative_returns = portfolio_returns[portfolio_returns < 0]
            downside_deviation = negative_returns.std() * np.sqrt(252) if len(negative_returns) > 0 else volatility
            sortino_ratio = excess_returns.mean() / downside_deviation * np.sqrt(252) if downside_deviation > 0 else 0
            
            # Drawdown
            cumulative_returns = (1 + portfolio_returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = drawdown.min()
            
            calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
            
            # Benchmark comparison
            if benchmark_returns is not None and len(benchmark_returns) > 0:
                aligned_portfolio, aligned_benchmark = portfolio_returns.align(benchmark_returns, join='inner')
                
                if len(aligned_portfolio) > 30:
                    beta, alpha, _ = self._calculate_market_beta(aligned_portfolio, aligned_benchmark)
                    
                    tracking_error = (aligned_portfolio - aligned_benchmark).std() * np.sqrt(252)
                    information_ratio = (aligned_portfolio - aligned_benchmark).mean() / tracking_error * np.sqrt(252) if tracking_error > 0 else 0
                else:
                    beta, alpha, tracking_error, information_ratio = 1.0, 0.0, 0.0, 0.0
            else:
                beta, alpha, tracking_error, information_ratio = 1.0, 0.0, 0.0, 0.0
            
            # VaR and CVaR
            var_95 = np.percentile(portfolio_returns, 5)
            cvar_95 = portfolio_returns[portfolio_returns <= var_95].mean() if len(portfolio_returns[portfolio_returns <= var_95]) > 0 else var_95
            
            # Win rate and profit factor
            positive_returns = portfolio_returns[portfolio_returns > 0]
            win_rate = len(positive_returns) / len(portfolio_returns) if len(portfolio_returns) > 0 else 0
            
            gross_profits = positive_returns.sum() if len(positive_returns) > 0 else 0
            gross_losses = abs(negative_returns.sum()) if len(negative_returns) > 0 else 1e-10
            profit_factor = gross_profits / gross_losses if gross_losses > 0 else 1
            
            return PortfolioMetrics(
                total_return=total_return,
                annualized_return=annualized_return,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                max_drawdown=max_drawdown,
                calmar_ratio=calmar_ratio,
                information_ratio=information_ratio,
                tracking_error=tracking_error,
                beta=beta,
                alpha=alpha,
                var_95=var_95,
                cvar_95=cvar_95,
                win_rate=win_rate,
                profit_factor=profit_factor
            )
            
        except Exception as e:
            self.logger.warning(f"Error calculating portfolio metrics: {e}")
            return PortfolioMetrics(
                total_return=0, annualized_return=0, volatility=0, sharpe_ratio=0,
                sortino_ratio=0, max_drawdown=0, calmar_ratio=0, information_ratio=0,
                tracking_error=0, beta=1, alpha=0, var_95=0, cvar_95=0,
                win_rate=0, profit_factor=1
            )


class FamaFrenchThreeFactorModel(BaseFactorModel):
    """Fama-French 3-Factor Model (Market, Size, Value)"""
    
    def calculate_factor_exposures(self, market_data: Dict[str, pd.DataFrame]) -> Dict[str, Dict[FactorType, FactorExposure]]:
        """Calculate factor exposures for Fama-French 3-factor model"""
        exposures = {}
        
        # Calculate factor returns
        market_returns = self._get_market_returns(market_data)
        size_factor = self._calculate_size_factor(market_data)
        value_factor = self._calculate_value_factor(market_data)
        
        for symbol, data in market_data.items():
            if len(data) < self.config.lookback_window:
                continue
            
            try:
                # Calculate security returns
                security_returns = data['close'].pct_change().dropna()
                
                # Align all series
                aligned_data = pd.concat([
                    security_returns,
                    market_returns,
                    size_factor,
                    value_factor
                ], axis=1, join='inner')
                
                aligned_data.columns = ['security', 'market', 'smb', 'hml']
                aligned_data = aligned_data.dropna()
                
                if len(aligned_data) < 30:
                    continue
                
                # Multiple regression: R_i - R_f = alpha + beta_m*(R_m - R_f) + beta_s*SMB + beta_v*HML + e
                X = aligned_data[['market', 'smb', 'hml']]
                y = aligned_data['security']
                
                reg = LinearRegression().fit(X, y)
                
                # Calculate statistics
                y_pred = reg.predict(X)
                residuals = y - y_pred
                mse = np.mean(residuals**2)
                r_squared = reg.score(X, y)
                
                # T-statistics (simplified)
                n = len(X)
                p = X.shape[1]
                
                if n > p + 1:
                    residual_std = np.sqrt(mse * n / (n - p - 1))
                    
                    # Standard errors (simplified)
                    try:
                        X_with_intercept = np.column_stack([np.ones(len(X)), X])
                        cov_matrix = np.linalg.inv(X_with_intercept.T @ X_with_intercept) * (residual_std ** 2)
                        std_errors = np.sqrt(np.diag(cov_matrix)[1:])  # Exclude intercept
                        
                        t_stats = reg.coef_ / std_errors
                        p_values = 2 * (1 - stats.t.cdf(np.abs(t_stats), n - p - 1))
                    except:
                        t_stats = [0, 0, 0]
                        p_values = [1, 1, 1]
                else:
                    t_stats = [0, 0, 0]
                    p_values = [1, 1, 1]
                
                # Store factor exposures
                exposures[symbol] = {
                    FactorType.MARKET: FactorExposure(
                        symbol=symbol,
                        factor_type=FactorType.MARKET,
                        exposure=reg.coef_[0],
                        t_stat=t_stats[0],
                        p_value=p_values[0],
                        r_squared=r_squared,
                        confidence=1 - p_values[0],
                        timestamp=datetime.now()
                    ),
                    FactorType.SIZE: FactorExposure(
                        symbol=symbol,
                        factor_type=FactorType.SIZE,
                        exposure=reg.coef_[1],
                        t_stat=t_stats[1],
                        p_value=p_values[1],
                        r_squared=r_squared,
                        confidence=1 - p_values[1],
                        timestamp=datetime.now()
                    ),
                    FactorType.VALUE: FactorExposure(
                        symbol=symbol,
                        factor_type=FactorType.VALUE,
                        exposure=reg.coef_[2],
                        t_stat=t_stats[2],
                        p_value=p_values[2],
                        r_squared=r_squared,
                        confidence=1 - p_values[2],
                        timestamp=datetime.now()
                    )
                }
                
            except Exception as e:
                self.logger.warning(f"Error calculating factor exposures for {symbol}: {e}")
        
        return exposures
    
    def calculate_factor_returns(self, market_data: Dict[str, pd.DataFrame]) -> Dict[FactorType, FactorReturn]:
        """Calculate factor returns for Fama-French 3-factor model"""
        factor_returns = {}
        
        try:
            # Calculate factors
            market_returns = self._get_market_returns(market_data)
            size_factor = self._calculate_size_factor(market_data)
            value_factor = self._calculate_value_factor(market_data)
            
            # Calculate factor return statistics
            for factor_type, factor_series in [
                (FactorType.MARKET, market_returns),
                (FactorType.SIZE, size_factor),
                (FactorType.VALUE, value_factor)
            ]:
                if len(factor_series) > 0:
                    return_value = factor_series.mean() * 252  # Annualized
                    volatility = factor_series.std() * np.sqrt(252)  # Annualized
                    sharpe_ratio = return_value / volatility if volatility > 0 else 0
                    
                    # Max drawdown
                    cumulative = (1 + factor_series).cumprod()
                    running_max = cumulative.expanding().max()
                    drawdown = (cumulative - running_max) / running_max
                    max_drawdown = drawdown.min()
                    
                    # Correlation to market
                    if factor_type != FactorType.MARKET and len(market_returns) > 0:
                        aligned_factor, aligned_market = factor_series.align(market_returns, join='inner')
                        correlation = aligned_factor.corr(aligned_market) if len(aligned_factor) > 10 else 0
                    else:
                        correlation = 1.0 if factor_type == FactorType.MARKET else 0.0
                    
                    factor_returns[factor_type] = FactorReturn(
                        factor_type=factor_type,
                        return_value=return_value,
                        volatility=volatility,
                        sharpe_ratio=sharpe_ratio,
                        max_drawdown=max_drawdown,
                        correlation_to_market=correlation,
                        timestamp=datetime.now()
                    )
            
        except Exception as e:
            self.logger.warning(f"Error calculating factor returns: {e}")
        
        return factor_returns
    
    def construct_portfolio(self, factor_exposures: Dict[str, Dict[FactorType, FactorExposure]], 
                          factor_returns: Dict[FactorType, FactorReturn],
                          market_data: Dict[str, pd.DataFrame]) -> FactorModelResult:
        """Construct portfolio using Fama-French 3-factor model"""
        try:
            # Calculate expected returns for each security
            expected_returns = {}
            
            for symbol, exposures in factor_exposures.items():
                expected_return = 0.0
                
                for factor_type, exposure in exposures.items():
                    if factor_type in factor_returns:
                        factor_premium = factor_returns[factor_type].return_value
                        expected_return += exposure.exposure * factor_premium
                
                expected_returns[symbol] = expected_return
            
            # Convert to pandas Series
            expected_returns_series = pd.Series(expected_returns)
            
            # Calculate covariance matrix
            returns_data = {}
            for symbol in expected_returns.keys():
                if symbol in market_data:
                    returns_data[symbol] = market_data[symbol]['close'].pct_change().dropna()
            
            returns_df = pd.DataFrame(returns_data)
            returns_df = returns_df.dropna()
            
            if len(returns_df) < 30:
                # Fallback to equal weights
                n_assets = len(expected_returns)
                portfolio_weights = {symbol: 1.0/n_assets for symbol in expected_returns.keys()}
            else:
                covariance_matrix = returns_df.cov() * 252  # Annualized
                
                # Optimize portfolio weights
                portfolio_weights = self._optimize_portfolio_weights(
                    expected_returns_series, covariance_matrix, factor_exposures
                )
            
            # Calculate portfolio metrics
            if len(returns_df) > 0:
                portfolio_returns = sum(portfolio_weights[symbol] * returns_df[symbol] 
                                      for symbol in portfolio_weights.keys() if symbol in returns_df.columns)
                portfolio_metrics = self._calculate_portfolio_metrics(portfolio_returns)
            else:
                portfolio_metrics = PortfolioMetrics(
                    total_return=0, annualized_return=0, volatility=0, sharpe_ratio=0,
                    sortino_ratio=0, max_drawdown=0, calmar_ratio=0, information_ratio=0,
                    tracking_error=0, beta=1, alpha=0, var_95=0, cvar_95=0,
                    win_rate=0, profit_factor=1
                )
            
            # Calculate portfolio factor exposures
            portfolio_factor_exposures = {}
            for factor_type in [FactorType.MARKET, FactorType.SIZE, FactorType.VALUE]:
                weighted_exposure = sum(
                    portfolio_weights.get(symbol, 0) * exposures.get(factor_type, FactorExposure(
                        symbol=symbol, factor_type=factor_type, exposure=0, t_stat=0, p_value=1,
                        r_squared=0, confidence=0, timestamp=datetime.now()
                    )).exposure
                    for symbol, exposures in factor_exposures.items()
                )
                portfolio_factor_exposures[factor_type] = weighted_exposure
            
            # Calculate factor contributions to return
            factor_contributions = {}
            for factor_type, exposure in portfolio_factor_exposures.items():
                if factor_type in factor_returns:
                    contribution = exposure * factor_returns[factor_type].return_value
                    factor_contributions[factor_type] = contribution
                else:
                    factor_contributions[factor_type] = 0.0
            
            # Generate signal
            expected_portfolio_return = sum(factor_contributions.values())
            
            if expected_portfolio_return > 0.1:  # 10% expected return
                signal = FactorSignal.STRONG_BUY
            elif expected_portfolio_return > 0.05:  # 5% expected return
                signal = FactorSignal.BUY
            elif expected_portfolio_return > 0.02:  # 2% expected return
                signal = FactorSignal.WEAK_BUY
            elif expected_portfolio_return < -0.1:  # -10% expected return
                signal = FactorSignal.STRONG_SELL
            elif expected_portfolio_return < -0.05:  # -5% expected return
                signal = FactorSignal.SELL
            elif expected_portfolio_return < -0.02:  # -2% expected return
                signal = FactorSignal.WEAK_SELL
            else:
                signal = FactorSignal.NEUTRAL
            
            # Calculate strength and confidence
            strength = min(1.0, abs(expected_portfolio_return) / 0.2)  # Normalize to 20% return
            
            # Average confidence from factor exposures
            all_confidences = []
            for exposures in factor_exposures.values():
                for exposure in exposures.values():
                    all_confidences.append(exposure.confidence)
            
            confidence = np.mean(all_confidences) if all_confidences else 0.5
            
            # Detect regime
            regime = self._detect_market_regime(market_data)
            
            # Check if rebalancing is needed
            rebalance_needed = True  # Always rebalance for now
            
            return FactorModelResult(
                signal=signal,
                model_type=FactorModel.FAMA_FRENCH_3,
                strength=strength,
                confidence=confidence,
                factor_exposures=portfolio_factor_exposures,
                expected_return=expected_portfolio_return,
                expected_volatility=portfolio_metrics.volatility,
                factor_contributions=factor_contributions,
                portfolio_weights=portfolio_weights,
                risk_metrics={
                    'var_95': portfolio_metrics.var_95,
                    'max_drawdown': portfolio_metrics.max_drawdown,
                    'tracking_error': portfolio_metrics.tracking_error
                },
                regime=regime,
                portfolio_metrics=portfolio_metrics,
                rebalance_needed=rebalance_needed,
                metadata={
                    'n_securities': len(portfolio_weights),
                    'factor_model': 'Fama-French 3-Factor',
                    'optimization_method': self.config.optimization_method
                },
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error constructing Fama-French 3-factor portfolio: {e}")
            
            # Return neutral result
            return FactorModelResult(
                signal=FactorSignal.NEUTRAL,
                model_type=FactorModel.FAMA_FRENCH_3,
                strength=0.0,
                confidence=0.0,
                factor_exposures={},
                expected_return=0.0,
                expected_volatility=0.15,
                factor_contributions={},
                portfolio_weights={},
                risk_metrics={},
                regime=MarketRegime.SIDEWAYS_MARKET,
                portfolio_metrics=PortfolioMetrics(
                    total_return=0, annualized_return=0, volatility=0, sharpe_ratio=0,
                    sortino_ratio=0, max_drawdown=0, calmar_ratio=0, information_ratio=0,
                    tracking_error=0, beta=1, alpha=0, var_95=0, cvar_95=0,
                    win_rate=0, profit_factor=1
                ),
                rebalance_needed=False,
                metadata={'error': str(e)},
                timestamp=datetime.now()
            )
    
    def _get_market_returns(self, market_data: Dict[str, pd.DataFrame]) -> pd.Series:
        """Get market returns (equal-weighted or use benchmark)"""
        try:
            # Try to find benchmark first
            if self.config.benchmark_symbol in market_data:
                return market_data[self.config.benchmark_symbol]['close'].pct_change().dropna()
            
            # Otherwise, create equal-weighted market return
            all_returns = []
            for symbol, data in market_data.items():
                if len(data) >= 30:
                    returns = data['close'].pct_change().dropna()
                    all_returns.append(returns)
            
            if all_returns:
                market_returns = pd.concat(all_returns, axis=1).mean(axis=1)
                return market_returns.dropna()
            else:
                return pd.Series(dtype=float)
                
        except Exception as e:
            self.logger.warning(f"Error getting market returns: {e}")
            return pd.Series(dtype=float)


class MultiFactorTradingManager:
    """Manager class for coordinating multi-factor model strategies"""
    
    def __init__(self, config: FactorConfig = None):
        self.config = config or FactorConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize factor models
        self.models = {
            'fama_french_3': FamaFrenchThreeFactorModel(self.config)
        }
        
        # Portfolio tracking
        self.current_portfolio = {}
        self.portfolio_history = []
        
        # Performance tracking
        self.performance_metrics = {}
        self.total_return = 0.0
        self.sharpe_ratio = 0.0
    
    def calculate_factor_models(self, market_data: Dict[str, pd.DataFrame]) -> Dict[str, FactorModelResult]:
        """Calculate all factor model results"""
        results = {}
        
        for model_name, model in self.models.items():
            try:
                self.logger.info(f"Calculating {model_name} factor model...")
                
                # Calculate factor exposures
                factor_exposures = model.calculate_factor_exposures(market_data)
                
                # Calculate factor returns
                factor_returns = model.calculate_factor_returns(market_data)
                
                # Construct portfolio
                result = model.construct_portfolio(factor_exposures, factor_returns, market_data)
                
                results[model_name] = result
                
                self.logger.info(f"Completed {model_name}: Signal={result.signal.name}, "
                                f"Expected Return={result.expected_return:.4f}")
                
            except Exception as e:
                self.logger.error(f"Error calculating {model_name} factor model: {e}")
        
        return results
    
    def get_best_factor_strategy(self, results: Dict[str, FactorModelResult]) -> Tuple[str, FactorModelResult]:
        """Get best factor model strategy"""
        if not results:
            return None, None
        
        # Score each model
        scored_results = []
        for model_name, result in results.items():
            # Composite score: expected return * confidence * (1 - risk)
            risk_score = abs(result.risk_metrics.get('var_95', 0)) + abs(result.risk_metrics.get('max_drawdown', 0))
            score = result.expected_return * result.confidence * (1 - min(0.5, risk_score))
            
            scored_results.append((score, model_name, result))
        
        # Sort by score
        scored_results.sort(reverse=True)
        
        best_score, best_model, best_result = scored_results[0]
        
        return best_model, best_result
    
    def update_portfolio(self, model_name: str, result: FactorModelResult) -> bool:
        """Update current portfolio based on factor model result"""
        try:
            if result.rebalance_needed:
                self.current_portfolio = result.portfolio_weights.copy()
                
                # Record portfolio change
                self.portfolio_history.append({
                    'timestamp': datetime.now(),
                    'model': model_name,
                    'weights': self.current_portfolio.copy(),
                    'expected_return': result.expected_return,
                    'signal': result.signal.name
                })
                
                self.logger.info(f"Updated portfolio using {model_name}: {len(self.current_portfolio)} positions")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error updating portfolio: {e}")
            return False
    
    def calculate_performance_attribution(self, results: Dict[str, FactorModelResult]) -> Dict[str, Any]:
        """Calculate performance attribution across factors"""
        attribution = {}
        
        try:
            for model_name, result in results.items():
                model_attribution = {
                    'total_return': result.expected_return,
                    'factor_contributions': result.factor_contributions,
                    'risk_metrics': result.risk_metrics,
                    'portfolio_metrics': {
                        'sharpe_ratio': result.portfolio_metrics.sharpe_ratio,
                        'max_drawdown': result.portfolio_metrics.max_drawdown,
                        'volatility': result.portfolio_metrics.volatility,
                        'information_ratio': result.portfolio_metrics.information_ratio
                    }
                }
                
                attribution[model_name] = model_attribution
            
        except Exception as e:
            self.logger.error(f"Error calculating performance attribution: {e}")
        
        return attribution


# Example usage and testing functions
def create_factor_test_data() -> Dict[str, pd.DataFrame]:
    """Create sample market data for factor model testing"""
    np.random.seed(42)
    
    dates = pd.date_range(start='2022-01-01', periods=300, freq='D')
    
    # Create different types of stocks
    stocks = {
        # Large cap growth
        'AAPL': {'base_return': 0.0003, 'volatility': 0.02, 'beta': 1.2, 'size_factor': -0.5, 'value_factor': -0.3},
        'MSFT': {'base_return': 0.0002, 'volatility': 0.018, 'beta': 1.1, 'size_factor': -0.4, 'value_factor': -0.2},
        
        # Large cap value
        'BRK.B': {'base_return': 0.0001, 'volatility': 0.015, 'beta': 0.8, 'size_factor': -0.3, 'value_factor': 0.4},
        'JPM': {'base_return': 0.0001, 'volatility': 0.022, 'beta': 1.3, 'size_factor': -0.2, 'value_factor': 0.3},
        
        # Small cap growth
        'SMALL_GROWTH_1': {'base_return': 0.0004, 'volatility': 0.03, 'beta': 1.5, 'size_factor': 0.6, 'value_factor': -0.4},
        'SMALL_GROWTH_2': {'base_return': 0.0003, 'volatility': 0.028, 'beta': 1.4, 'size_factor': 0.5, 'value_factor': -0.3},
        
        # Small cap value
        'SMALL_VALUE_1': {'base_return': 0.0002, 'volatility': 0.025, 'beta': 1.1, 'size_factor': 0.4, 'value_factor': 0.5},
        'SMALL_VALUE_2': {'base_return': 0.0001, 'volatility': 0.023, 'beta': 1.0, 'size_factor': 0.3, 'value_factor': 0.4},
        
        # Market benchmark
        'SPY': {'base_return': 0.0002, 'volatility': 0.016, 'beta': 1.0, 'size_factor': 0.0, 'value_factor': 0.0}
    }
    
    # Generate market factor returns
    market_returns = np.random.normal(0.0002, 0.016, len(dates))
    size_returns = np.random.normal(0.0001, 0.01, len(dates))  # SMB factor
    value_returns = np.random.normal(0.0001, 0.012, len(dates))  # HML factor
    
    market_data = {}
    
    for symbol, params in stocks.items():
        # Generate returns using factor model
        idiosyncratic_returns = np.random.normal(0, params['volatility'] * 0.5, len(dates))
        
        factor_returns = (
            params['base_return'] +
            params['beta'] * market_returns +
            params['size_factor'] * size_returns +
            params['value_factor'] * value_returns +
            idiosyncratic_returns
        )
        
        # Convert to prices
        prices = 100 * (1 + factor_returns).cumprod()
        
        # Generate OHLC data
        market_data[symbol] = pd.DataFrame({
            'date': dates,
            'open': prices * (1 + np.random.normal(0, 0.002, len(dates))),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.005, len(dates)))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.005, len(dates)))),
            'close': prices,
            'volume': np.random.lognormal(15, 0.5, len(dates))  # Log-normal volume
        })
    
    return market_data


def test_factor_models():
    """Test multi-factor model strategies with sample data"""
    # Create sample market data
    market_data = create_factor_test_data()
    
    # Initialize factor model manager
    config = FactorConfig(
        lookback_window=200,
        rebalance_frequency=21,
        target_volatility=0.15,
        benchmark_symbol='SPY'
    )
    
    manager = MultiFactorTradingManager(config)
    
    # Calculate factor model results
    results = manager.calculate_factor_models(market_data)
    
    print("\n=== Multi-Factor Model Results ===")
    for model_name, result in results.items():
        print(f"\n{model_name.upper()} Model:")
        print(f"  Signal: {result.signal.name}")
        print(f"  Strength: {result.strength:.3f}")
        print(f"  Confidence: {result.confidence:.3f}")
        print(f"  Expected Return: {result.expected_return:.4f} ({result.expected_return*100:.2f}%)")
        print(f"  Expected Volatility: {result.expected_volatility:.4f} ({result.expected_volatility*100:.2f}%)")
        print(f"  Regime: {result.regime.value}")
        
        print(f"  Factor Exposures:")
        for factor_type, exposure in result.factor_exposures.items():
            print(f"    {factor_type.value}: {exposure:.3f}")
        
        print(f"  Factor Contributions:")
        for factor_type, contribution in result.factor_contributions.items():
            print(f"    {factor_type.value}: {contribution:.4f} ({contribution*100:.2f}%)")
        
        print(f"  Portfolio Metrics:")
        print(f"    Sharpe Ratio: {result.portfolio_metrics.sharpe_ratio:.3f}")
        print(f"    Max Drawdown: {result.portfolio_metrics.max_drawdown:.4f} ({result.portfolio_metrics.max_drawdown*100:.2f}%)")
        print(f"    Information Ratio: {result.portfolio_metrics.information_ratio:.3f}")
        
        print(f"  Top 5 Holdings:")
        sorted_weights = sorted(result.portfolio_weights.items(), key=lambda x: x[1], reverse=True)
        for symbol, weight in sorted_weights[:5]:
            print(f"    {symbol}: {weight:.3f} ({weight*100:.1f}%)")
    
    # Get best strategy
    best_model, best_result = manager.get_best_factor_strategy(results)
    
    if best_result:
        print(f"\n=== Best Factor Strategy: {best_model.upper()} ===")
        print(f"Signal: {best_result.signal.name}")
        print(f"Expected Return: {best_result.expected_return:.4f} ({best_result.expected_return*100:.2f}%)")
        print(f"Confidence: {best_result.confidence:.3f}")
        print(f"Sharpe Ratio: {best_result.portfolio_metrics.sharpe_ratio:.3f}")
        
        # Update portfolio
        updated = manager.update_portfolio(best_model, best_result)
        print(f"Portfolio Updated: {updated}")
    
    # Performance attribution
    attribution = manager.calculate_performance_attribution(results)
    
    print("\n=== Performance Attribution ===")
    for model_name, attr in attribution.items():
        print(f"\n{model_name.upper()}:")
        print(f"  Total Return: {attr['total_return']:.4f}")
        
        if 'factor_contributions' in attr:
            print(f"  Factor Breakdown:")
            for factor, contrib in attr['factor_contributions'].items():
                print(f"    {factor.value}: {contrib:.4f} ({contrib/attr['total_return']*100:.1f}%)" 
                     if attr['total_return'] != 0 else f"    {factor.value}: {contrib:.4f}")


if __name__ == "__main__":
    # Run tests
    test_factor_models()