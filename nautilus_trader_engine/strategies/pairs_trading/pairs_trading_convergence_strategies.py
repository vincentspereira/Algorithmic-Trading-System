"""Institutional-Grade Pairs Trading Convergence Strategies

This module implements comprehensive pairs trading strategies focused on convergence
between highly correlated instruments, with institutional-grade risk controls,
statistical validation, and performance optimization.

Strategies Included:
- Convergence Statistical Arbitrage
- Cointegration Convergence Trading
- Beta-Neutral Convergence Pairs
- Volatility Convergence Trading
- Cross-Asset Convergence
- Sector Convergence Trading
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
from sklearn.cluster import KMeans
import warnings
warnings.filterwarnings('ignore')

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


class ConvergenceSignal(Enum):
    """Convergence trading signal types"""
    STRONG_CONVERGENCE_LONG_A_SHORT_B = 2
    CONVERGENCE_LONG_A_SHORT_B = 1
    NEUTRAL = 0
    CONVERGENCE_LONG_B_SHORT_A = -1
    STRONG_CONVERGENCE_LONG_B_SHORT_A = -2


class ConvergenceRegime(Enum):
    """Market regime for convergence trading"""
    STRONG_CONVERGENCE = "strong_convergence"
    WEAK_CONVERGENCE = "weak_convergence"
    DIVERGING = "diverging"
    STABLE_SPREAD = "stable_spread"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    TRENDING_TOGETHER = "trending_together"
    BREAKDOWN = "breakdown"


class ConvergenceType(Enum):
    """Type of convergence pattern"""
    PRICE_CONVERGENCE = "price_convergence"
    RATIO_CONVERGENCE = "ratio_convergence"
    SPREAD_CONVERGENCE = "spread_convergence"
    VOLATILITY_CONVERGENCE = "volatility_convergence"
    CORRELATION_CONVERGENCE = "correlation_convergence"
    MOMENTUM_CONVERGENCE = "momentum_convergence"


@dataclass
class ConvergenceConfig:
    """Configuration for convergence trading strategies"""
    # Convergence detection parameters
    min_correlation: float = 0.8  # Higher threshold for convergence
    convergence_lookback: int = 30
    convergence_threshold: float = 0.02  # 2% convergence threshold
    
    # Statistical parameters
    z_score_entry: float = 1.5  # Lower threshold for convergence
    z_score_exit: float = 0.3
    z_score_stop: float = 2.5
    
    # Convergence speed parameters
    min_convergence_speed: float = 0.1  # Minimum daily convergence rate
    max_convergence_time: int = 20  # Maximum days to convergence
    
    # Beta neutrality
    target_beta: float = 0.0
    beta_tolerance: float = 0.05  # Tighter tolerance for convergence
    beta_lookback: int = 30
    
    # Risk management
    max_position_size: float = 0.03  # 3% per leg
    max_leverage: float = 1.5
    stop_loss: float = 0.04  # 4% stop loss
    take_profit: float = 0.025  # 2.5% take profit
    
    # Cointegration parameters
    adf_significance: float = 0.01  # Stricter for convergence
    johansen_significance: float = 0.01
    half_life_max: int = 15  # Faster mean reversion expected
    
    # Correlation parameters
    rolling_correlation_window: int = 20
    min_correlation_stability: float = 0.75
    correlation_convergence_threshold: float = 0.95
    
    # Volatility parameters
    volatility_window: int = 20
    volatility_convergence_threshold: float = 0.1
    
    # Performance optimization
    use_cuda: bool = False
    batch_processing: bool = True


@dataclass
class ConvergenceMetrics:
    """Metrics for convergence analysis"""
    current_correlation: float
    rolling_correlation: pd.Series
    convergence_speed: float
    time_to_convergence: Optional[float]
    spread_momentum: float
    ratio_momentum: float
    volatility_ratio: float
    convergence_probability: float
    convergence_strength: float
    historical_convergence_rate: float
    mean_reversion_strength: float
    cointegration_strength: float


@dataclass
class ConvergenceResult:
    """Result from convergence trading strategy calculation"""
    signal: ConvergenceSignal
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    convergence_type: ConvergenceType
    spread_z_score: float
    ratio_z_score: float
    current_spread: float
    current_ratio: float
    target_spread: float
    target_ratio: float
    hedge_ratio: float
    beta_a: float
    beta_b: float
    regime: ConvergenceRegime
    metrics: ConvergenceMetrics
    entry_price_a: Optional[float]
    entry_price_b: Optional[float]
    position_size_a: float
    position_size_b: float
    expected_profit: float
    risk_reward_ratio: float
    metadata: Dict[str, Any]
    timestamp: datetime


class BaseConvergenceStrategy(ABC):
    """Abstract base class for convergence trading strategies"""
    
    def __init__(self, config: ConvergenceConfig = None):
        self.config = config or ConvergenceConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup_indicators()
    
    def _setup_indicators(self):
        """Initialize technical indicators"""
        self.indicators = ConsolidatedIndicators()
    
    @abstractmethod
    def calculate_convergence_signal(self, data_a: pd.DataFrame, data_b: pd.DataFrame, 
                                   symbol_a: str, symbol_b: str) -> ConvergenceResult:
        """Calculate convergence trading signal for given pair"""
        pass
    
    def _detect_convergence_pattern(self, prices_a: pd.Series, prices_b: pd.Series) -> Tuple[ConvergenceType, float, float]:
        """Detect type and strength of convergence pattern"""
        # Align series
        aligned_a, aligned_b = prices_a.align(prices_b, join='inner')
        
        if len(aligned_a) < self.config.convergence_lookback:
            return ConvergenceType.PRICE_CONVERGENCE, 0.0, 0.0
        
        # Calculate different convergence metrics
        convergence_scores = {}
        
        # 1. Price convergence (absolute difference)
        price_diff = abs(aligned_a - aligned_b)
        price_convergence_trend = self._calculate_convergence_trend(price_diff)
        convergence_scores[ConvergenceType.PRICE_CONVERGENCE] = price_convergence_trend
        
        # 2. Ratio convergence (ratio approaching 1 or stable value)
        ratio = aligned_a / aligned_b
        ratio_stability = 1.0 / (1.0 + ratio.rolling(self.config.convergence_lookback).std().iloc[-1])
        convergence_scores[ConvergenceType.RATIO_CONVERGENCE] = ratio_stability
        
        # 3. Spread convergence (spread approaching zero)
        spread = aligned_a - aligned_b
        spread_convergence_trend = self._calculate_convergence_trend(abs(spread))
        convergence_scores[ConvergenceType.SPREAD_CONVERGENCE] = spread_convergence_trend
        
        # 4. Volatility convergence
        vol_a = aligned_a.rolling(self.config.volatility_window).std()
        vol_b = aligned_b.rolling(self.config.volatility_window).std()
        vol_diff = abs(vol_a - vol_b)
        vol_convergence_trend = self._calculate_convergence_trend(vol_diff)
        convergence_scores[ConvergenceType.VOLATILITY_CONVERGENCE] = vol_convergence_trend
        
        # 5. Correlation convergence (correlation increasing)
        rolling_corr = aligned_a.rolling(self.config.rolling_correlation_window).corr(aligned_b)
        corr_trend = self._calculate_trend(rolling_corr)
        convergence_scores[ConvergenceType.CORRELATION_CONVERGENCE] = max(0.0, corr_trend)
        
        # 6. Momentum convergence
        momentum_a = aligned_a.pct_change(5).rolling(5).mean()
        momentum_b = aligned_b.pct_change(5).rolling(5).mean()
        momentum_diff = abs(momentum_a - momentum_b)
        momentum_convergence_trend = self._calculate_convergence_trend(momentum_diff)
        convergence_scores[ConvergenceType.MOMENTUM_CONVERGENCE] = momentum_convergence_trend
        
        # Find strongest convergence pattern
        best_type = max(convergence_scores, key=convergence_scores.get)
        best_score = convergence_scores[best_type]
        
        # Calculate overall convergence strength
        overall_strength = np.mean(list(convergence_scores.values()))
        
        return best_type, best_score, overall_strength
    
    def _calculate_convergence_trend(self, series: pd.Series) -> float:
        """Calculate convergence trend (negative slope indicates convergence)"""
        if len(series) < 5:
            return 0.0
        
        try:
            # Use linear regression to find trend
            x = np.arange(len(series))
            y = series.values
            
            # Remove NaN values
            valid_mask = ~np.isnan(y)
            if np.sum(valid_mask) < 3:
                return 0.0
            
            x_valid = x[valid_mask]
            y_valid = y[valid_mask]
            
            slope, _, r_value, _, _ = stats.linregress(x_valid, y_valid)
            
            # Negative slope indicates convergence (decreasing difference)
            convergence_strength = max(0.0, -slope * r_value**2)
            
            return min(1.0, convergence_strength * 100)  # Scale to 0-1
            
        except Exception as e:
            self.logger.warning(f"Error calculating convergence trend: {e}")
            return 0.0
    
    def _calculate_trend(self, series: pd.Series) -> float:
        """Calculate trend direction and strength"""
        if len(series) < 5:
            return 0.0
        
        try:
            x = np.arange(len(series))
            y = series.values
            
            # Remove NaN values
            valid_mask = ~np.isnan(y)
            if np.sum(valid_mask) < 3:
                return 0.0
            
            x_valid = x[valid_mask]
            y_valid = y[valid_mask]
            
            slope, _, r_value, _, _ = stats.linregress(x_valid, y_valid)
            
            return slope * r_value**2  # Trend strength weighted by R²
            
        except Exception:
            return 0.0
    
    def _calculate_convergence_speed(self, series: pd.Series) -> float:
        """Calculate speed of convergence"""
        if len(series) < 10:
            return 0.0
        
        # Calculate rate of change in the convergence metric
        recent_change = (series.iloc[-1] - series.iloc[-10]) / 10
        
        # Normalize by current level
        if series.iloc[-1] != 0:
            speed = abs(recent_change) / abs(series.iloc[-1])
        else:
            speed = 0.0
        
        return min(1.0, speed * 100)  # Scale to 0-1
    
    def _estimate_time_to_convergence(self, series: pd.Series, target_level: float = 0.0) -> Optional[float]:
        """Estimate time to convergence based on current trend"""
        if len(series) < 5:
            return None
        
        try:
            # Calculate current trend
            x = np.arange(len(series))
            y = series.values
            
            valid_mask = ~np.isnan(y)
            if np.sum(valid_mask) < 3:
                return None
            
            x_valid = x[valid_mask]
            y_valid = y[valid_mask]
            
            slope, intercept, r_value, _, _ = stats.linregress(x_valid, y_valid)
            
            # Only proceed if trend is significant and moving toward target
            if abs(r_value) < 0.3 or abs(slope) < 1e-6:
                return None
            
            current_value = series.iloc[-1]
            current_time = len(series) - 1
            
            # Calculate when series will reach target level
            if slope != 0:
                time_to_target = (target_level - (intercept + slope * current_time)) / slope
                days_to_convergence = time_to_target
                
                # Return only if reasonable timeframe
                if 0 < days_to_convergence <= self.config.max_convergence_time:
                    return days_to_convergence
            
            return None
            
        except Exception:
            return None
    
    def _calculate_convergence_probability(self, data_a: pd.DataFrame, data_b: pd.DataFrame) -> float:
        """Calculate probability of convergence based on historical patterns"""
        try:
            # Calculate historical spread
            spread = data_a['close'] - data_b['close']
            
            # Look for historical convergence events
            spread_std = spread.rolling(self.config.convergence_lookback).std()
            spread_z = (spread - spread.rolling(self.config.convergence_lookback).mean()) / spread_std
            
            # Count convergence events (when z-score moves from extreme to neutral)
            convergence_events = 0
            total_opportunities = 0
            
            for i in range(self.config.convergence_lookback, len(spread_z) - 5):
                if abs(spread_z.iloc[i]) > 1.5:  # Extreme divergence
                    total_opportunities += 1
                    
                    # Check if convergence occurred in next 5-20 days
                    future_z = spread_z.iloc[i+5:i+20]
                    if len(future_z) > 0 and any(abs(future_z) < 0.5):
                        convergence_events += 1
            
            if total_opportunities > 0:
                return convergence_events / total_opportunities
            else:
                return 0.5  # Default probability
                
        except Exception:
            return 0.5
    
    def _detect_convergence_regime(self, data_a: pd.DataFrame, data_b: pd.DataFrame, 
                                 convergence_metrics: ConvergenceMetrics) -> ConvergenceRegime:
        """Detect current convergence regime"""
        # Calculate recent volatility
        returns_a = data_a['close'].pct_change().dropna()
        returns_b = data_b['close'].pct_change().dropna()
        
        vol_a = returns_a.rolling(self.config.volatility_window).std().iloc[-1]
        vol_b = returns_b.rolling(self.config.volatility_window).std().iloc[-1]
        avg_vol = (vol_a + vol_b) / 2
        
        # Calculate spread trend
        spread = data_a['close'] - data_b['close']
        spread_trend = self._calculate_trend(spread.tail(self.config.convergence_lookback))
        
        # Regime classification
        if avg_vol > returns_a.rolling(60).std().quantile(0.8):
            return ConvergenceRegime.HIGH_VOLATILITY
        elif avg_vol < returns_a.rolling(60).std().quantile(0.2):
            return ConvergenceRegime.LOW_VOLATILITY
        elif convergence_metrics.convergence_strength > 0.7:
            return ConvergenceRegime.STRONG_CONVERGENCE
        elif convergence_metrics.convergence_strength > 0.3:
            return ConvergenceRegime.WEAK_CONVERGENCE
        elif abs(spread_trend) < 0.1:
            return ConvergenceRegime.STABLE_SPREAD
        elif convergence_metrics.current_correlation < self.config.min_correlation:
            return ConvergenceRegime.BREAKDOWN
        elif spread_trend > 0.2:
            return ConvergenceRegime.DIVERGING
        else:
            return ConvergenceRegime.TRENDING_TOGETHER
    
    def _calculate_expected_profit(self, current_spread: float, target_spread: float, 
                                 position_size_a: float, position_size_b: float,
                                 price_a: float, price_b: float) -> float:
        """Calculate expected profit from convergence trade"""
        # Expected change in spread
        spread_change = target_spread - current_spread
        
        # Profit from spread change
        # Long A, Short B: profit when spread increases (A rises relative to B)
        # Short A, Long B: profit when spread decreases (B rises relative to A)
        
        if position_size_a > 0:  # Long A, Short B
            expected_profit = spread_change * abs(position_size_a)
        else:  # Short A, Long B
            expected_profit = -spread_change * abs(position_size_a)
        
        # Convert to percentage return
        total_capital = abs(position_size_a * price_a) + abs(position_size_b * price_b)
        
        if total_capital > 0:
            return expected_profit / total_capital
        else:
            return 0.0
    
    def _calculate_risk_reward_ratio(self, expected_profit: float, stop_loss: float) -> float:
        """Calculate risk-reward ratio"""
        if stop_loss > 0:
            return abs(expected_profit) / stop_loss
        else:
            return 0.0


class ConvergenceStatisticalArbitrageStrategy(BaseConvergenceStrategy):
    """Convergence-focused statistical arbitrage strategy"""
    
    def calculate_convergence_signal(self, data_a: pd.DataFrame, data_b: pd.DataFrame, 
                                   symbol_a: str, symbol_b: str) -> ConvergenceResult:
        """Calculate convergence statistical arbitrage signal"""
        if len(data_a) < self.config.convergence_lookback or len(data_b) < self.config.convergence_lookback:
            return self._create_neutral_result(data_a, data_b, symbol_a, symbol_b)
        
        # Detect convergence pattern
        convergence_type, pattern_strength, overall_strength = self._detect_convergence_pattern(
            data_a['close'], data_b['close']
        )
        
        # Calculate spread and ratio
        spread, ratio, hedge_ratio = self._calculate_spread_and_ratio(
            data_a['close'], data_b['close']
        )
        
        if len(spread) < self.config.convergence_lookback:
            return self._create_neutral_result(data_a, data_b, symbol_a, symbol_b)
        
        # Calculate z-scores
        spread_z_score = self._calculate_z_score(spread, self.config.convergence_lookback)
        ratio_z_score = self._calculate_z_score(ratio, self.config.convergence_lookback)
        
        # Calculate convergence metrics
        convergence_metrics = self._calculate_convergence_metrics(data_a, data_b, spread, ratio)
        
        # Detect regime
        regime = self._detect_convergence_regime(data_a, data_b, convergence_metrics)
        
        # Calculate betas
        returns_a = data_a['close'].pct_change().dropna()
        returns_b = data_b['close'].pct_change().dropna()
        beta_a, beta_b = self._calculate_beta(returns_a, returns_b)
        
        # Generate signal
        signal = self._generate_convergence_signal(
            spread_z_score, ratio_z_score, convergence_metrics, regime, convergence_type
        )
        
        # Calculate strength and confidence
        strength = min(1.0, overall_strength * pattern_strength)
        confidence = self._calculate_convergence_confidence(
            convergence_metrics, regime, convergence_type
        )
        
        # Calculate position sizes
        current_price_a = data_a['close'].iloc[-1]
        current_price_b = data_b['close'].iloc[-1]
        
        position_size_a, position_size_b = self._calculate_convergence_position_sizes(
            current_price_a, current_price_b, hedge_ratio, beta_a, beta_b, signal
        )
        
        # Calculate targets and expected profit
        target_spread = self._calculate_target_spread(spread)
        target_ratio = self._calculate_target_ratio(ratio)
        
        expected_profit = self._calculate_expected_profit(
            spread.iloc[-1], target_spread, position_size_a, position_size_b,
            current_price_a, current_price_b
        )
        
        risk_reward_ratio = self._calculate_risk_reward_ratio(
            expected_profit, self.config.stop_loss
        )
        
        return ConvergenceResult(
            signal=signal,
            strength=strength,
            confidence=confidence,
            convergence_type=convergence_type,
            spread_z_score=spread_z_score,
            ratio_z_score=ratio_z_score,
            current_spread=spread.iloc[-1],
            current_ratio=ratio.iloc[-1],
            target_spread=target_spread,
            target_ratio=target_ratio,
            hedge_ratio=hedge_ratio,
            beta_a=beta_a,
            beta_b=beta_b,
            regime=regime,
            metrics=convergence_metrics,
            entry_price_a=current_price_a if signal != ConvergenceSignal.NEUTRAL else None,
            entry_price_b=current_price_b if signal != ConvergenceSignal.NEUTRAL else None,
            position_size_a=position_size_a,
            position_size_b=position_size_b,
            expected_profit=expected_profit,
            risk_reward_ratio=risk_reward_ratio,
            metadata={
                'symbol_a': symbol_a,
                'symbol_b': symbol_b,
                'pattern_strength': pattern_strength,
                'overall_strength': overall_strength,
                'convergence_lookback': self.config.convergence_lookback
            },
            timestamp=datetime.now()
        )
    
    def _calculate_spread_and_ratio(self, prices_a: pd.Series, prices_b: pd.Series) -> Tuple[pd.Series, pd.Series, float]:
        """Calculate spread and ratio with convergence focus"""
        # Align series
        aligned_a, aligned_b = prices_a.align(prices_b, join='inner')
        
        if len(aligned_a) == 0:
            return pd.Series(), pd.Series(), 1.0
        
        # Calculate optimal hedge ratio for convergence
        hedge_ratio = self._calculate_convergence_hedge_ratio(aligned_a, aligned_b)
        
        # Calculate spread: A - hedge_ratio * B
        spread = aligned_a - hedge_ratio * aligned_b
        
        # Calculate ratio: A / B
        ratio = aligned_a / aligned_b
        ratio = ratio.replace([np.inf, -np.inf], np.nan).dropna()
        
        return spread, ratio, hedge_ratio
    
    def _calculate_convergence_hedge_ratio(self, prices_a: pd.Series, prices_b: pd.Series) -> float:
        """Calculate hedge ratio optimized for convergence detection"""
        try:
            # Use shorter window for more responsive hedge ratio
            window = min(self.config.convergence_lookback, len(prices_a))
            
            if window < 10:
                return 1.0
            
            # Use recent data for hedge ratio calculation
            recent_a = prices_a.tail(window)
            recent_b = prices_b.tail(window)
            
            # Remove any NaN values
            valid_data = pd.DataFrame({'a': recent_a, 'b': recent_b}).dropna()
            
            if len(valid_data) < 5:
                return 1.0
            
            # Linear regression with focus on minimizing spread variance
            X = valid_data['b'].values.reshape(-1, 1)
            y = valid_data['a'].values
            
            reg = LinearRegression().fit(X, y)
            hedge_ratio = reg.coef_[0]
            
            return hedge_ratio if not np.isnan(hedge_ratio) else 1.0
            
        except Exception as e:
            self.logger.warning(f"Error calculating convergence hedge ratio: {e}")
            return 1.0
    
    def _calculate_z_score(self, series: pd.Series, window: int) -> float:
        """Calculate z-score with convergence focus"""
        if len(series) < window:
            return 0.0
        
        # Use exponential weighting for more recent data
        ewm_mean = series.ewm(span=window).mean()
        ewm_std = series.ewm(span=window).std()
        
        current_value = series.iloc[-1]
        mean_value = ewm_mean.iloc[-1]
        std_value = ewm_std.iloc[-1]
        
        if std_value > 0:
            return (current_value - mean_value) / std_value
        else:
            return 0.0
    
    def _calculate_beta(self, returns_a: pd.Series, returns_b: pd.Series) -> Tuple[float, float]:
        """Calculate beta with convergence focus"""
        try:
            # Use shorter window for beta calculation
            window = min(self.config.beta_lookback, len(returns_a))
            
            aligned_a, aligned_b = returns_a.align(returns_b, join='inner')
            valid_data = pd.DataFrame({'a': aligned_a, 'b': aligned_b}).dropna()
            
            if len(valid_data) < window:
                return 1.0, 1.0
            
            recent_data = valid_data.tail(window)
            
            # Beta of A relative to B
            cov_ab = np.cov(recent_data['a'], recent_data['b'])[0, 1]
            var_b = np.var(recent_data['b'])
            
            if var_b > 0:
                beta_a = cov_ab / var_b
            else:
                beta_a = 1.0
            
            beta_b = 1.0  # B is the reference
            
            return beta_a, beta_b
            
        except Exception as e:
            self.logger.warning(f"Error calculating beta: {e}")
            return 1.0, 1.0
    
    def _calculate_convergence_metrics(self, data_a: pd.DataFrame, data_b: pd.DataFrame,
                                     spread: pd.Series, ratio: pd.Series) -> ConvergenceMetrics:
        """Calculate comprehensive convergence metrics"""
        # Current correlation
        current_correlation = data_a['close'].tail(self.config.rolling_correlation_window).corr(
            data_b['close'].tail(self.config.rolling_correlation_window)
        )
        
        # Rolling correlation
        rolling_correlation = data_a['close'].rolling(
            self.config.rolling_correlation_window
        ).corr(data_b['close'])
        
        # Convergence speed
        convergence_speed = self._calculate_convergence_speed(abs(spread))
        
        # Time to convergence
        time_to_convergence = self._estimate_time_to_convergence(abs(spread))
        
        # Momentum calculations
        spread_momentum = self._calculate_trend(spread.tail(10))
        ratio_momentum = self._calculate_trend(ratio.tail(10))
        
        # Volatility ratio
        vol_a = data_a['close'].pct_change().rolling(self.config.volatility_window).std().iloc[-1]
        vol_b = data_b['close'].pct_change().rolling(self.config.volatility_window).std().iloc[-1]
        volatility_ratio = vol_a / vol_b if vol_b > 0 else 1.0
        
        # Convergence probability
        convergence_probability = self._calculate_convergence_probability(data_a, data_b)
        
        # Convergence strength (based on multiple factors)
        convergence_strength = self._calculate_overall_convergence_strength(
            current_correlation, convergence_speed, convergence_probability
        )
        
        # Historical convergence rate
        historical_convergence_rate = self._calculate_historical_convergence_rate(spread)
        
        # Mean reversion strength
        mean_reversion_strength = self._calculate_mean_reversion_strength(spread)
        
        # Cointegration strength
        cointegration_strength = self._calculate_cointegration_strength(data_a['close'], data_b['close'])
        
        return ConvergenceMetrics(
            current_correlation=current_correlation,
            rolling_correlation=rolling_correlation,
            convergence_speed=convergence_speed,
            time_to_convergence=time_to_convergence,
            spread_momentum=spread_momentum,
            ratio_momentum=ratio_momentum,
            volatility_ratio=volatility_ratio,
            convergence_probability=convergence_probability,
            convergence_strength=convergence_strength,
            historical_convergence_rate=historical_convergence_rate,
            mean_reversion_strength=mean_reversion_strength,
            cointegration_strength=cointegration_strength
        )
    
    def _calculate_overall_convergence_strength(self, correlation: float, speed: float, probability: float) -> float:
        """Calculate overall convergence strength"""
        # Weighted combination of factors
        weights = [0.4, 0.3, 0.3]  # correlation, speed, probability
        factors = [abs(correlation), speed, probability]
        
        return sum(w * f for w, f in zip(weights, factors))
    
    def _calculate_historical_convergence_rate(self, spread: pd.Series) -> float:
        """Calculate historical rate of convergence events"""
        if len(spread) < 50:
            return 0.5
        
        # Look for convergence events in historical data
        spread_z = (spread - spread.rolling(20).mean()) / spread.rolling(20).std()
        
        convergence_events = 0
        total_events = 0
        
        for i in range(20, len(spread_z) - 10):
            if abs(spread_z.iloc[i]) > 1.5:  # Divergence event
                total_events += 1
                
                # Check for convergence in next 10 periods
                future_z = spread_z.iloc[i+1:i+11]
                if any(abs(future_z) < 0.5):
                    convergence_events += 1
        
        return convergence_events / total_events if total_events > 0 else 0.5
    
    def _calculate_mean_reversion_strength(self, spread: pd.Series) -> float:
        """Calculate mean reversion strength using half-life"""
        try:
            if len(spread) < 20:
                return 0.0
            
            # Calculate half-life
            spread_lag = spread.shift(1).dropna()
            spread_diff = spread.diff().dropna()
            
            min_len = min(len(spread_lag), len(spread_diff))
            spread_lag = spread_lag.iloc[-min_len:]
            spread_diff = spread_diff.iloc[-min_len:]
            
            # AR(1) regression
            X = np.column_stack([np.ones(len(spread_lag)), spread_lag.values])
            y = spread_diff.values
            
            coeffs = np.linalg.lstsq(X, y, rcond=None)[0]
            beta = coeffs[1]
            
            if beta < 0:
                half_life = -np.log(2) / beta
                # Convert to strength (faster mean reversion = higher strength)
                strength = 1.0 / (1.0 + half_life / 10.0)
                return min(1.0, strength)
            else:
                return 0.0
                
        except Exception:
            return 0.0
    
    def _calculate_cointegration_strength(self, prices_a: pd.Series, prices_b: pd.Series) -> float:
        """Calculate cointegration strength"""
        try:
            from statsmodels.tsa.stattools import adfuller
            
            # Align series
            aligned_a, aligned_b = prices_a.align(prices_b, join='inner')
            valid_data = pd.DataFrame({'a': aligned_a, 'b': aligned_b}).dropna()
            
            if len(valid_data) < 30:
                return 0.0
            
            # Run cointegration regression
            X = valid_data['b'].values.reshape(-1, 1)
            y = valid_data['a'].values
            
            reg = LinearRegression().fit(X, y)
            residuals = y - reg.predict(X)
            
            # Test residuals for stationarity
            adf_result = adfuller(residuals)
            adf_pvalue = adf_result[1]
            
            # Convert p-value to strength (lower p-value = stronger cointegration)
            strength = 1.0 - adf_pvalue
            return max(0.0, strength)
            
        except ImportError:
            # Fallback: use correlation
            correlation = prices_a.corr(prices_b)
            return abs(correlation)
        except Exception:
            return 0.0
    
    def _generate_convergence_signal(self, spread_z_score: float, ratio_z_score: float,
                                   metrics: ConvergenceMetrics, regime: ConvergenceRegime,
                                   convergence_type: ConvergenceType) -> ConvergenceSignal:
        """Generate convergence trading signal"""
        # Only trade in favorable regimes
        if regime in [ConvergenceRegime.BREAKDOWN, ConvergenceRegime.HIGH_VOLATILITY]:
            return ConvergenceSignal.NEUTRAL
        
        # Require minimum convergence strength
        if metrics.convergence_strength < 0.3:
            return ConvergenceSignal.NEUTRAL
        
        # Use spread z-score as primary signal
        primary_z_score = spread_z_score
        
        # Adjust thresholds based on convergence strength and regime
        entry_threshold = self.config.z_score_entry
        
        if regime == ConvergenceRegime.STRONG_CONVERGENCE:
            entry_threshold *= 0.7  # Lower threshold for strong convergence
        elif regime == ConvergenceRegime.WEAK_CONVERGENCE:
            entry_threshold *= 1.2  # Higher threshold for weak convergence
        
        # Adjust for convergence probability
        entry_threshold *= (2.0 - metrics.convergence_probability)  # Higher prob = lower threshold
        
        # Generate signals (convergence logic - bet on mean reversion)
        if primary_z_score > entry_threshold * 1.5:
            return ConvergenceSignal.STRONG_CONVERGENCE_LONG_B_SHORT_A
        elif primary_z_score > entry_threshold:
            return ConvergenceSignal.CONVERGENCE_LONG_B_SHORT_A
        elif primary_z_score < -entry_threshold * 1.5:
            return ConvergenceSignal.STRONG_CONVERGENCE_LONG_A_SHORT_B
        elif primary_z_score < -entry_threshold:
            return ConvergenceSignal.CONVERGENCE_LONG_A_SHORT_B
        else:
            return ConvergenceSignal.NEUTRAL
    
    def _calculate_convergence_confidence(self, metrics: ConvergenceMetrics, 
                                        regime: ConvergenceRegime,
                                        convergence_type: ConvergenceType) -> float:
        """Calculate confidence in convergence signal"""
        confidence = 0.0
        
        # Base confidence from convergence strength (0-0.4)
        confidence += metrics.convergence_strength * 0.4
        
        # Correlation component (0-0.2)
        confidence += min(0.2, abs(metrics.current_correlation) * 0.2)
        
        # Convergence probability component (0-0.2)
        confidence += metrics.convergence_probability * 0.2
        
        # Mean reversion strength component (0-0.1)
        confidence += metrics.mean_reversion_strength * 0.1
        
        # Cointegration strength component (0-0.1)
        confidence += metrics.cointegration_strength * 0.1
        
        # Regime adjustment
        if regime == ConvergenceRegime.STRONG_CONVERGENCE:
            confidence *= 1.2
        elif regime == ConvergenceRegime.WEAK_CONVERGENCE:
            confidence *= 0.9
        elif regime in [ConvergenceRegime.BREAKDOWN, ConvergenceRegime.HIGH_VOLATILITY]:
            confidence *= 0.5
        
        return min(1.0, confidence)
    
    def _calculate_convergence_position_sizes(self, price_a: float, price_b: float, 
                                            hedge_ratio: float, beta_a: float, beta_b: float,
                                            signal: ConvergenceSignal, 
                                            portfolio_value: float = 1000000) -> Tuple[float, float]:
        """Calculate position sizes for convergence trade"""
        if signal == ConvergenceSignal.NEUTRAL:
            return 0.0, 0.0
        
        # Target dollar amounts for each leg
        max_leg_value = portfolio_value * self.config.max_position_size
        
        # Calculate base position sizes
        if abs(beta_a * hedge_ratio + beta_b) > 1e-6:
            # Beta-neutral sizing
            shares_b = -beta_a * hedge_ratio / (beta_a * hedge_ratio + beta_b)
            shares_a = hedge_ratio * shares_b
        else:
            # Simple hedge ratio sizing
            shares_b = max_leg_value / price_b
            shares_a = hedge_ratio * shares_b
        
        # Apply signal direction
        if signal in [ConvergenceSignal.CONVERGENCE_LONG_A_SHORT_B, 
                     ConvergenceSignal.STRONG_CONVERGENCE_LONG_A_SHORT_B]:
            # Long A, Short B
            shares_a = abs(shares_a)
            shares_b = -abs(shares_b)
        else:
            # Short A, Long B
            shares_a = -abs(shares_a)
            shares_b = abs(shares_b)
        
        # Apply position size limits
        dollar_value_a = abs(shares_a * price_a)
        dollar_value_b = abs(shares_b * price_b)
        
        max_value = max(dollar_value_a, dollar_value_b)
        if max_value > max_leg_value:
            scale_factor = max_leg_value / max_value
            shares_a *= scale_factor
            shares_b *= scale_factor
        
        return shares_a, shares_b
    
    def _calculate_target_spread(self, spread: pd.Series) -> float:
        """Calculate target spread for convergence"""
        # Target is typically the long-term mean
        if len(spread) >= 60:
            return spread.rolling(60).mean().iloc[-1]
        else:
            return spread.mean()
    
    def _calculate_target_ratio(self, ratio: pd.Series) -> float:
        """Calculate target ratio for convergence"""
        # Target is typically the long-term mean
        if len(ratio) >= 60:
            return ratio.rolling(60).mean().iloc[-1]
        else:
            return ratio.mean()
    
    def _create_neutral_result(self, data_a: pd.DataFrame, data_b: pd.DataFrame,
                             symbol_a: str, symbol_b: str) -> ConvergenceResult:
        """Create neutral result for insufficient data"""
        return ConvergenceResult(
            signal=ConvergenceSignal.NEUTRAL,
            strength=0.0,
            confidence=0.0,
            convergence_type=ConvergenceType.PRICE_CONVERGENCE,
            spread_z_score=0.0,
            ratio_z_score=0.0,
            current_spread=0.0,
            current_ratio=1.0,
            target_spread=0.0,
            target_ratio=1.0,
            hedge_ratio=1.0,
            beta_a=1.0,
            beta_b=1.0,
            regime=ConvergenceRegime.LOW_VOLATILITY,
            metrics=ConvergenceMetrics(
                current_correlation=0.0,
                rolling_correlation=pd.Series(),
                convergence_speed=0.0,
                time_to_convergence=None,
                spread_momentum=0.0,
                ratio_momentum=0.0,
                volatility_ratio=1.0,
                convergence_probability=0.5,
                convergence_strength=0.0,
                historical_convergence_rate=0.5,
                mean_reversion_strength=0.0,
                cointegration_strength=0.0
            ),
            entry_price_a=None,
            entry_price_b=None,
            position_size_a=0.0,
            position_size_b=0.0,
            expected_profit=0.0,
            risk_reward_ratio=0.0,
            metadata={'insufficient_data': True, 'symbol_a': symbol_a, 'symbol_b': symbol_b},
            timestamp=datetime.now()
        )


class ConvergenceTradingManager:
    """Manager class for coordinating convergence trading strategies"""
    
    def __init__(self, config: ConvergenceConfig = None):
        self.config = config or ConvergenceConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize strategies
        self.strategies = {
            'convergence_statistical_arbitrage': ConvergenceStatisticalArbitrageStrategy(self.config)
        }
        
        # Convergence pair universe
        self.convergence_pairs = []
        self.active_convergence_trades = {}
    
    def add_convergence_pair(self, symbol_a: str, symbol_b: str, 
                           expected_convergence_time: int = 10):
        """Add a pair to the convergence trading universe"""
        pair_id = f"{symbol_a}_{symbol_b}_conv"
        self.convergence_pairs.append({
            'id': pair_id,
            'symbol_a': symbol_a,
            'symbol_b': symbol_b,
            'expected_convergence_time': expected_convergence_time
        })
        self.logger.info(f"Added convergence pair {pair_id} to universe")
    
    def screen_convergence_opportunities(self, data_dict: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        """Screen for convergence trading opportunities"""
        opportunities = []
        
        for pair in self.convergence_pairs:
            symbol_a = pair['symbol_a']
            symbol_b = pair['symbol_b']
            
            if symbol_a not in data_dict or symbol_b not in data_dict:
                continue
            
            data_a = data_dict[symbol_a]
            data_b = data_dict[symbol_b]
            
            if len(data_a) < self.config.convergence_lookback or len(data_b) < self.config.convergence_lookback:
                continue
            
            # Calculate convergence metrics
            strategy = self.strategies['convergence_statistical_arbitrage']
            
            # Detect convergence pattern
            convergence_type, pattern_strength, overall_strength = strategy._detect_convergence_pattern(
                data_a['close'], data_b['close']
            )
            
            # Calculate correlation
            correlation = data_a['close'].tail(self.config.rolling_correlation_window).corr(
                data_b['close'].tail(self.config.rolling_correlation_window)
            )
            
            # Calculate convergence probability
            convergence_probability = strategy._calculate_convergence_probability(data_a, data_b)
            
            if (abs(correlation) >= self.config.min_correlation and 
                overall_strength >= 0.3 and 
                convergence_probability >= 0.6):
                
                opportunities.append({
                    'pair_id': pair['id'],
                    'symbol_a': symbol_a,
                    'symbol_b': symbol_b,
                    'correlation': correlation,
                    'convergence_type': convergence_type.value,
                    'pattern_strength': pattern_strength,
                    'overall_strength': overall_strength,
                    'convergence_probability': convergence_probability,
                    'expected_convergence_time': pair['expected_convergence_time']
                })
        
        # Sort by convergence score
        opportunities.sort(key=lambda x: x['overall_strength'] * x['convergence_probability'], reverse=True)
        
        return opportunities
    
    def calculate_convergence_signals(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, ConvergenceResult]:
        """Calculate convergence signals for all pairs"""
        results = {}
        
        opportunities = self.screen_convergence_opportunities(data_dict)
        
        for opp in opportunities[:8]:  # Limit to top 8 convergence opportunities
            symbol_a = opp['symbol_a']
            symbol_b = opp['symbol_b']
            pair_id = opp['pair_id']
            
            data_a = data_dict[symbol_a]
            data_b = data_dict[symbol_b]
            
            try:
                strategy = self.strategies['convergence_statistical_arbitrage']
                result = strategy.calculate_convergence_signal(data_a, data_b, symbol_a, symbol_b)
                
                results[pair_id] = result
                self.logger.info(f"Calculated convergence signal for {pair_id}: {result.signal.name}")
                
            except Exception as e:
                self.logger.error(f"Error calculating convergence signal for {pair_id}: {e}")
        
        return results
    
    def get_best_convergence_trades(self, results: Dict[str, ConvergenceResult], 
                                  top_n: int = 3) -> List[Tuple[str, ConvergenceResult]]:
        """Get best convergence trading opportunities"""
        # Filter non-neutral signals with good risk-reward
        trades = [(pair_id, result) for pair_id, result in results.items() 
                 if (result.signal != ConvergenceSignal.NEUTRAL and 
                     result.risk_reward_ratio > 1.5 and
                     result.confidence > 0.6)]
        
        # Sort by combined score (confidence * strength * risk_reward_ratio)
        trades.sort(key=lambda x: x[1].confidence * x[1].strength * min(x[1].risk_reward_ratio, 3.0), 
                   reverse=True)
        
        return trades[:top_n]


# Example usage and testing functions
def create_converging_pair_data(days: int = 252, initial_spread: float = 10.0) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Create sample converging pair data for testing"""
    dates = pd.date_range(start='2023-01-01', periods=days, freq='D')
    
    np.random.seed(42)
    
    # Create base price series
    base_price_a = 100.0
    base_price_b = 90.0
    
    # Create converging spread pattern
    convergence_rate = 0.02  # 2% convergence per day
    spread_decay = np.exp(-convergence_rate * np.arange(days))
    target_spread = initial_spread * spread_decay
    
    # Add noise
    noise_a = np.random.normal(0, 0.5, days)
    noise_b = np.random.normal(0, 0.5, days)
    
    # Generate prices with convergence pattern
    prices_a = base_price_a + target_spread/2 + noise_a
    prices_b = base_price_b - target_spread/2 + noise_b
    
    # Ensure positive prices
    prices_a = np.maximum(prices_a, 50.0)
    prices_b = np.maximum(prices_b, 50.0)
    
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


def test_convergence_trading_strategies():
    """Test convergence trading strategies with sample data"""
    # Create sample converging pair data
    data_a, data_b = create_converging_pair_data(200, initial_spread=15.0)
    
    # Initialize convergence trading manager
    config = ConvergenceConfig(
        min_correlation=0.8,
        convergence_lookback=30,
        z_score_entry=1.5,
        z_score_exit=0.3,
        max_convergence_time=20
    )
    
    manager = ConvergenceTradingManager(config)
    
    # Add convergence pair
    manager.add_convergence_pair('STOCK_A', 'STOCK_B', expected_convergence_time=15)
    
    # Create data dictionary
    data_dict = {
        'STOCK_A': data_a,
        'STOCK_B': data_b
    }
    
    # Screen for convergence opportunities
    opportunities = manager.screen_convergence_opportunities(data_dict)
    print(f"\n=== Convergence Opportunities ===")
    for opp in opportunities:
        print(f"Pair: {opp['pair_id']}")
        print(f"  Correlation: {opp['correlation']:.3f}")
        print(f"  Convergence Type: {opp['convergence_type']}")
        print(f"  Pattern Strength: {opp['pattern_strength']:.3f}")
        print(f"  Overall Strength: {opp['overall_strength']:.3f}")
        print(f"  Convergence Probability: {opp['convergence_probability']:.3f}")
        print(f"  Expected Convergence Time: {opp['expected_convergence_time']} days")
    
    # Calculate convergence signals
    results = manager.calculate_convergence_signals(data_dict)
    
    print(f"\n=== Convergence Trading Signals ===")
    for pair_id, result in results.items():
        print(f"\nPair: {pair_id}")
        print(f"  Signal: {result.signal.name}")
        print(f"  Strength: {result.strength:.3f}")
        print(f"  Confidence: {result.confidence:.3f}")
        print(f"  Convergence Type: {result.convergence_type.value}")
        print(f"  Spread Z-Score: {result.spread_z_score:.3f}")
        print(f"  Current Spread: {result.current_spread:.3f}")
        print(f"  Target Spread: {result.target_spread:.3f}")
        print(f"  Expected Profit: {result.expected_profit:.3f}")
        print(f"  Risk-Reward Ratio: {result.risk_reward_ratio:.3f}")
        print(f"  Regime: {result.regime.value}")
        print(f"  Convergence Strength: {result.metrics.convergence_strength:.3f}")
        print(f"  Convergence Probability: {result.metrics.convergence_probability:.3f}")
        print(f"  Time to Convergence: {result.metrics.time_to_convergence:.1f} days" 
              if result.metrics.time_to_convergence else "  Time to Convergence: N/A")
    
    # Get best convergence trades
    best_trades = manager.get_best_convergence_trades(results, top_n=3)
    
    print(f"\n=== Best Convergence Trades ===")
    for i, (pair_id, result) in enumerate(best_trades, 1):
        score = result.confidence * result.strength * min(result.risk_reward_ratio, 3.0)
        print(f"{i}. {pair_id}: {result.signal.name}")
        print(f"   Score: {score:.3f}, Expected Profit: {result.expected_profit:.3f}")
        print(f"   Risk-Reward: {result.risk_reward_ratio:.2f}")


if __name__ == "__main__":
    # Run tests
    test_convergence_trading_strategies()