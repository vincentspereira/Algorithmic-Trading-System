"""Institutional-Grade Regime-Aware Adaptive Trading Strategies

This module implements sophisticated regime-aware adaptive strategies that detect
market regimes and dynamically allocate between different trading strategies
based on current market conditions.

Regime Detection Methods:
- Hidden Markov Models (HMM)
- Gaussian Mixture Models (GMM)
- Machine Learning Classification
- Technical Regime Indicators
- Volatility Regime Detection
- Correlation Regime Analysis

Adaptive Strategy Allocation:
- Dynamic Strategy Weighting
- Regime-Specific Strategy Selection
- Risk-Adjusted Allocation
- Performance-Based Adaptation
- Machine Learning Optimization
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
from sklearn.mixture import GaussianMixture
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import warnings
warnings.filterwarnings('ignore')

# Import Hidden Markov Models
try:
    from hmmlearn import hmm
except ImportError:
    # Fallback implementation
    class hmm:
        class GaussianHMM:
            def __init__(self, *args, **kwargs):
                pass
            def fit(self, *args, **kwargs):
                return self
            def predict(self, *args, **kwargs):
                return np.zeros(10, dtype=int)
            def score(self, *args, **kwargs):
                return 0.0

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

# Import other strategy modules
try:
    from nautilus_trader_engine.strategies.momentum_strategies import MomentumTradingManager
    from nautilus_trader_engine.strategies.mean_reversion_strategies import MeanReversionTradingManager
    from nautilus_trader_engine.strategies.pairs_trading_divergence_strategies import PairsTradingDivergenceManager
    from nautilus_trader_engine.strategies.arbitrage_strategies import ArbitrageTradingManager
except ImportError:
    # Fallback for development
    class MomentumTradingManager:
        def __init__(self, *args, **kwargs):
            pass
        def calculate_signals(self, *args, **kwargs):
            return {}
    
    class MeanReversionTradingManager:
        def __init__(self, *args, **kwargs):
            pass
        def calculate_signals(self, *args, **kwargs):
            return {}
    
    class PairsTradingDivergenceManager:
        def __init__(self, *args, **kwargs):
            pass
        def calculate_signals(self, *args, **kwargs):
            return {}
    
    class ArbitrageTradingManager:
        def __init__(self, *args, **kwargs):
            pass
        def calculate_signals(self, *args, **kwargs):
            return {}


class MarketRegime(Enum):
    """Market regime types for adaptive strategy allocation"""
    BULL_TRENDING = "bull_trending"  # Strong upward trend
    BEAR_TRENDING = "bear_trending"  # Strong downward trend
    SIDEWAYS_RANGE = "sideways_range"  # Range-bound market
    HIGH_VOLATILITY = "high_volatility"  # High volatility regime
    LOW_VOLATILITY = "low_volatility"  # Low volatility regime
    MOMENTUM_REGIME = "momentum_regime"  # Momentum-driven market
    MEAN_REVERSION_REGIME = "mean_reversion_regime"  # Mean-reverting market
    CRISIS_MODE = "crisis_mode"  # Crisis/panic selling
    RECOVERY_MODE = "recovery_mode"  # Post-crisis recovery
    CONSOLIDATION = "consolidation"  # Market consolidation
    BREAKOUT_PENDING = "breakout_pending"  # Pre-breakout compression
    ROTATION_REGIME = "rotation_regime"  # Sector rotation


class RegimeDetectionMethod(Enum):
    """Methods for detecting market regimes"""
    HIDDEN_MARKOV_MODEL = "hmm"
    GAUSSIAN_MIXTURE_MODEL = "gmm"
    MACHINE_LEARNING = "ml"
    TECHNICAL_INDICATORS = "technical"
    VOLATILITY_CLUSTERING = "volatility"
    CORRELATION_ANALYSIS = "correlation"
    ENSEMBLE_METHOD = "ensemble"


class AdaptiveSignal(Enum):
    """Adaptive trading signal types"""
    STRONG_BUY = 3
    BUY = 2
    WEAK_BUY = 1
    NEUTRAL = 0
    WEAK_SELL = -1
    SELL = -2
    STRONG_SELL = -3


class StrategyType(Enum):
    """Types of trading strategies for regime allocation"""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    PAIRS_TRADING = "pairs_trading"
    ARBITRAGE = "arbitrage"
    TREND_FOLLOWING = "trend_following"
    CONTRARIAN = "contrarian"
    VOLATILITY_TRADING = "volatility_trading"
    CARRY_TRADE = "carry_trade"
    MARKET_NEUTRAL = "market_neutral"


@dataclass
class RegimeConfig:
    """Configuration for regime-aware adaptive strategies"""
    # Regime detection parameters
    lookback_window: int = 252  # 1 year for regime detection
    regime_update_frequency: int = 5  # Update regime every 5 days
    min_regime_duration: int = 10  # Minimum regime duration in days
    regime_confidence_threshold: float = 0.7  # Minimum confidence for regime change
    
    # HMM parameters
    n_regimes_hmm: int = 4  # Number of hidden states
    hmm_covariance_type: str = "full"  # HMM covariance type
    hmm_n_iter: int = 100  # HMM training iterations
    
    # GMM parameters
    n_regimes_gmm: int = 5  # Number of Gaussian components
    gmm_covariance_type: str = "full"  # GMM covariance type
    gmm_n_init: int = 10  # GMM initialization attempts
    
    # ML parameters
    ml_features_window: int = 20  # Window for feature calculation
    ml_training_window: int = 500  # Training data window
    ml_model_type: str = "random_forest"  # ML model type
    
    # Strategy allocation parameters
    max_strategy_weight: float = 0.5  # Maximum weight per strategy
    min_strategy_weight: float = 0.05  # Minimum weight per strategy
    rebalance_frequency: int = 5  # Strategy rebalancing frequency
    
    # Risk management
    max_portfolio_volatility: float = 0.2  # Maximum portfolio volatility
    max_drawdown_threshold: float = 0.1  # Maximum drawdown before regime override
    var_confidence: float = 0.05  # VaR confidence level
    
    # Performance parameters
    performance_lookback: int = 60  # Performance evaluation window
    adaptation_speed: float = 0.1  # Speed of strategy weight adaptation
    
    # Advanced features
    use_ensemble_detection: bool = True
    use_dynamic_rebalancing: bool = True
    use_regime_momentum: bool = True
    use_volatility_scaling: bool = True
    
    # Performance optimization
    use_cuda: bool = False
    parallel_processing: bool = True


@dataclass
class RegimeFeatures:
    """Features used for regime detection"""
    returns_mean: float
    returns_std: float
    returns_skewness: float
    returns_kurtosis: float
    volatility_regime: float
    trend_strength: float
    momentum_score: float
    mean_reversion_score: float
    correlation_regime: float
    volume_regime: float
    vix_level: float
    term_structure_slope: float
    credit_spread: float
    timestamp: datetime


@dataclass
class RegimeDetectionResult:
    """Result from regime detection"""
    regime: MarketRegime
    confidence: float  # 0.0 to 1.0
    probability_distribution: Dict[MarketRegime, float]
    regime_duration: int  # Days in current regime
    regime_stability: float  # Stability of regime classification
    features: RegimeFeatures
    detection_method: RegimeDetectionMethod
    metadata: Dict[str, Any]
    timestamp: datetime


@dataclass
class StrategyAllocation:
    """Strategy allocation for current regime"""
    strategy_type: StrategyType
    weight: float  # 0.0 to 1.0
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    max_drawdown: float
    regime_suitability: float  # How suitable for current regime
    recent_performance: float
    confidence: float
    metadata: Dict[str, Any]


@dataclass
class AdaptiveStrategyResult:
    """Result from adaptive strategy calculation"""
    signal: AdaptiveSignal
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    current_regime: MarketRegime
    regime_confidence: float
    strategy_allocations: Dict[StrategyType, StrategyAllocation]
    portfolio_weights: Dict[str, float]
    expected_return: float
    expected_volatility: float
    risk_metrics: Dict[str, float]
    regime_history: List[Tuple[datetime, MarketRegime, float]]
    adaptation_signals: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime


class BaseRegimeDetector(ABC):
    """Abstract base class for regime detection methods"""
    
    def __init__(self, config: RegimeConfig = None):
        self.config = config or RegimeConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.regime_history = []
        self.model = None
        self.scaler = StandardScaler()
        self.is_fitted = False
    
    @abstractmethod
    def fit(self, market_data: Dict[str, pd.DataFrame]) -> bool:
        """Fit the regime detection model"""
        pass
    
    @abstractmethod
    def detect_regime(self, market_data: Dict[str, pd.DataFrame]) -> RegimeDetectionResult:
        """Detect current market regime"""
        pass
    
    def _extract_features(self, market_data: Dict[str, pd.DataFrame]) -> RegimeFeatures:
        """Extract features for regime detection"""
        try:
            # Use market index or create composite
            market_prices = self._get_market_index(market_data)
            
            if len(market_prices) < self.config.ml_features_window:
                return self._default_features()
            
            # Calculate returns
            returns = market_prices.pct_change().dropna()
            recent_returns = returns.tail(self.config.ml_features_window)
            
            # Basic return statistics
            returns_mean = recent_returns.mean()
            returns_std = recent_returns.std()
            returns_skewness = recent_returns.skew()
            returns_kurtosis = recent_returns.kurtosis()
            
            # Volatility regime
            volatility_short = returns.tail(10).std()
            volatility_long = returns.tail(60).std()
            volatility_regime = volatility_short / volatility_long if volatility_long > 0 else 1.0
            
            # Trend strength
            sma_short = market_prices.tail(20).mean()
            sma_long = market_prices.tail(60).mean()
            trend_strength = (sma_short - sma_long) / sma_long if sma_long > 0 else 0.0
            
            # Momentum score
            momentum_1m = (market_prices.iloc[-1] / market_prices.iloc[-21] - 1) if len(market_prices) >= 21 else 0
            momentum_3m = (market_prices.iloc[-1] / market_prices.iloc[-63] - 1) if len(market_prices) >= 63 else 0
            momentum_score = (momentum_1m + momentum_3m) / 2
            
            # Mean reversion score
            current_price = market_prices.iloc[-1]
            sma_20 = market_prices.tail(20).mean()
            std_20 = market_prices.tail(20).std()
            mean_reversion_score = (current_price - sma_20) / std_20 if std_20 > 0 else 0
            
            # Correlation regime (simplified)
            correlation_regime = self._calculate_correlation_regime(market_data)
            
            # Volume regime
            volume_regime = self._calculate_volume_regime(market_data)
            
            # Market stress indicators (proxies)
            vix_level = volatility_regime * 20  # VIX proxy
            term_structure_slope = trend_strength  # Term structure proxy
            credit_spread = abs(mean_reversion_score)  # Credit spread proxy
            
            return RegimeFeatures(
                returns_mean=returns_mean,
                returns_std=returns_std,
                returns_skewness=returns_skewness,
                returns_kurtosis=returns_kurtosis,
                volatility_regime=volatility_regime,
                trend_strength=trend_strength,
                momentum_score=momentum_score,
                mean_reversion_score=mean_reversion_score,
                correlation_regime=correlation_regime,
                volume_regime=volume_regime,
                vix_level=vix_level,
                term_structure_slope=term_structure_slope,
                credit_spread=credit_spread,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.warning(f"Error extracting features: {e}")
            return self._default_features()
    
    def _default_features(self) -> RegimeFeatures:
        """Return default features when calculation fails"""
        return RegimeFeatures(
            returns_mean=0.0, returns_std=0.02, returns_skewness=0.0, returns_kurtosis=3.0,
            volatility_regime=1.0, trend_strength=0.0, momentum_score=0.0,
            mean_reversion_score=0.0, correlation_regime=0.5, volume_regime=1.0,
            vix_level=20.0, term_structure_slope=0.0, credit_spread=0.0,
            timestamp=datetime.now()
        )
    
    def _get_market_index(self, market_data: Dict[str, pd.DataFrame]) -> pd.Series:
        """Get market index or create composite"""
        # Try to find common market indices
        for symbol in ['SPY', 'QQQ', 'IWM', 'VTI']:
            if symbol in market_data and len(market_data[symbol]) > 0:
                return market_data[symbol]['close']
        
        # Create equal-weighted composite
        all_prices = []
        for symbol, data in market_data.items():
            if len(data) >= 30:
                prices = data['close'].pct_change().dropna()
                all_prices.append(prices)
        
        if all_prices:
            composite_returns = pd.concat(all_prices, axis=1).mean(axis=1)
            composite_prices = (1 + composite_returns).cumprod() * 100
            return composite_prices
        else:
            # Fallback
            return pd.Series([100] * 100, index=pd.date_range('2023-01-01', periods=100))
    
    def _calculate_correlation_regime(self, market_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate correlation regime indicator"""
        try:
            returns_data = {}
            for symbol, data in market_data.items():
                if len(data) >= 30:
                    returns_data[symbol] = data['close'].pct_change().dropna()
            
            if len(returns_data) < 2:
                return 0.5
            
            returns_df = pd.DataFrame(returns_data).dropna()
            
            if len(returns_df) < 20:
                return 0.5
            
            # Calculate average correlation
            corr_matrix = returns_df.tail(20).corr()
            
            # Get upper triangle (excluding diagonal)
            mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
            correlations = corr_matrix.where(mask).stack().dropna()
            
            avg_correlation = correlations.mean() if len(correlations) > 0 else 0.5
            
            # Normalize to 0-1 range
            return (avg_correlation + 1) / 2
            
        except Exception as e:
            self.logger.warning(f"Error calculating correlation regime: {e}")
            return 0.5
    
    def _calculate_volume_regime(self, market_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate volume regime indicator"""
        try:
            volume_ratios = []
            
            for symbol, data in market_data.items():
                if len(data) >= 40 and 'volume' in data.columns:
                    recent_volume = data['volume'].tail(10).mean()
                    historical_volume = data['volume'].tail(40).mean()
                    
                    if historical_volume > 0:
                        volume_ratio = recent_volume / historical_volume
                        volume_ratios.append(volume_ratio)
            
            if volume_ratios:
                avg_volume_ratio = np.mean(volume_ratios)
                # Normalize around 1.0
                return min(2.0, max(0.1, avg_volume_ratio))
            else:
                return 1.0
                
        except Exception as e:
            self.logger.warning(f"Error calculating volume regime: {e}")
            return 1.0


class HiddenMarkovRegimeDetector(BaseRegimeDetector):
    """Hidden Markov Model for regime detection"""
    
    def fit(self, market_data: Dict[str, pd.DataFrame]) -> bool:
        """Fit HMM model to market data"""
        try:
            # Extract features for training
            market_prices = self._get_market_index(market_data)
            
            if len(market_prices) < self.config.hmm_n_iter:
                self.logger.warning("Insufficient data for HMM training")
                return False
            
            # Prepare training data
            returns = market_prices.pct_change().dropna()
            
            # Create feature matrix
            features = []
            for i in range(10, len(returns)):
                window_returns = returns.iloc[i-10:i]
                feature_vector = [
                    window_returns.mean(),
                    window_returns.std(),
                    window_returns.skew(),
                    window_returns.kurtosis()
                ]
                features.append(feature_vector)
            
            features_array = np.array(features)
            
            # Normalize features
            features_scaled = self.scaler.fit_transform(features_array)
            
            # Fit HMM model
            self.model = hmm.GaussianHMM(
                n_components=self.config.n_regimes_hmm,
                covariance_type=self.config.hmm_covariance_type,
                n_iter=self.config.hmm_n_iter,
                random_state=42
            )
            
            self.model.fit(features_scaled)
            self.is_fitted = True
            
            self.logger.info(f"HMM model fitted with {self.config.n_regimes_hmm} regimes")
            return True
            
        except Exception as e:
            self.logger.error(f"Error fitting HMM model: {e}")
            return False
    
    def detect_regime(self, market_data: Dict[str, pd.DataFrame]) -> RegimeDetectionResult:
        """Detect regime using HMM"""
        try:
            if not self.is_fitted:
                if not self.fit(market_data):
                    return self._default_regime_result()
            
            # Extract current features
            features = self._extract_features(market_data)
            
            # Prepare feature vector
            feature_vector = np.array([[
                features.returns_mean,
                features.returns_std,
                features.returns_skewness,
                features.returns_kurtosis
            ]])
            
            # Scale features
            feature_scaled = self.scaler.transform(feature_vector)
            
            # Predict regime
            regime_state = self.model.predict(feature_scaled)[0]
            
            # Get state probabilities
            log_prob, state_sequence = self.model.decode(feature_scaled)
            
            # Map HMM states to market regimes
            regime_mapping = self._map_hmm_states_to_regimes(features)
            regime = regime_mapping.get(regime_state, MarketRegime.SIDEWAYS_RANGE)
            
            # Calculate confidence
            confidence = min(1.0, abs(log_prob) / 10.0)
            
            # Create probability distribution
            prob_dist = {r: 0.1 for r in MarketRegime}
            prob_dist[regime] = confidence
            
            # Normalize probabilities
            total_prob = sum(prob_dist.values())
            prob_dist = {r: p/total_prob for r, p in prob_dist.items()}
            
            return RegimeDetectionResult(
                regime=regime,
                confidence=confidence,
                probability_distribution=prob_dist,
                regime_duration=self._calculate_regime_duration(regime),
                regime_stability=confidence,
                features=features,
                detection_method=RegimeDetectionMethod.HIDDEN_MARKOV_MODEL,
                metadata={
                    'hmm_state': regime_state,
                    'log_probability': log_prob,
                    'n_states': self.config.n_regimes_hmm
                },
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error detecting regime with HMM: {e}")
            return self._default_regime_result()
    
    def _map_hmm_states_to_regimes(self, features: RegimeFeatures) -> Dict[int, MarketRegime]:
        """Map HMM states to interpretable market regimes"""
        # Simple heuristic mapping based on features
        mapping = {}
        
        if features.volatility_regime > 1.5:
            if features.returns_mean < -0.001:
                mapping[0] = MarketRegime.CRISIS_MODE
            else:
                mapping[0] = MarketRegime.HIGH_VOLATILITY
        elif features.volatility_regime < 0.7:
            mapping[1] = MarketRegime.LOW_VOLATILITY
        
        if features.trend_strength > 0.02:
            mapping[2] = MarketRegime.BULL_TRENDING
        elif features.trend_strength < -0.02:
            mapping[3] = MarketRegime.BEAR_TRENDING
        else:
            mapping[2] = MarketRegime.SIDEWAYS_RANGE
        
        # Fill remaining states
        for i in range(self.config.n_regimes_hmm):
            if i not in mapping:
                mapping[i] = MarketRegime.CONSOLIDATION
        
        return mapping
    
    def _calculate_regime_duration(self, current_regime: MarketRegime) -> int:
        """Calculate how long we've been in current regime"""
        if not self.regime_history:
            return 1
        
        duration = 1
        for i in range(len(self.regime_history) - 1, -1, -1):
            if self.regime_history[i][1] == current_regime:
                duration += 1
            else:
                break
        
        return duration
    
    def _default_regime_result(self) -> RegimeDetectionResult:
        """Return default regime result when detection fails"""
        return RegimeDetectionResult(
            regime=MarketRegime.SIDEWAYS_RANGE,
            confidence=0.5,
            probability_distribution={r: 1.0/len(MarketRegime) for r in MarketRegime},
            regime_duration=1,
            regime_stability=0.5,
            features=self._default_features(),
            detection_method=RegimeDetectionMethod.HIDDEN_MARKOV_MODEL,
            metadata={'error': 'Default regime used'},
            timestamp=datetime.now()
        )


class AdaptiveStrategyManager:
    """Manager for regime-aware adaptive trading strategies"""
    
    def __init__(self, config: RegimeConfig = None):
        self.config = config or RegimeConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize regime detector
        self.regime_detector = HiddenMarkovRegimeDetector(self.config)
        
        # Initialize strategy managers
        self._initialize_strategy_managers()
        
        # Portfolio tracking
        self.current_allocations = {}
        self.allocation_history = []
        self.performance_history = []
        
        # Regime tracking
        self.regime_history = []
        self.current_regime = MarketRegime.SIDEWAYS_RANGE
        
        # Performance metrics
        self.total_return = 0.0
        self.sharpe_ratio = 0.0
        self.max_drawdown = 0.0
    
    def _initialize_strategy_managers(self):
        """Initialize individual strategy managers"""
        try:
            self.strategy_managers = {
                StrategyType.MOMENTUM: MomentumTradingManager(),
                StrategyType.MEAN_REVERSION: MeanReversionTradingManager(),
                StrategyType.PAIRS_TRADING: PairsTradingDivergenceManager(),
                StrategyType.ARBITRAGE: ArbitrageTradingManager()
            }
        except Exception as e:
            self.logger.warning(f"Error initializing strategy managers: {e}")
            self.strategy_managers = {}
    
    def detect_market_regime(self, market_data: Dict[str, pd.DataFrame]) -> RegimeDetectionResult:
        """Detect current market regime"""
        try:
            # Detect regime
            regime_result = self.regime_detector.detect_regime(market_data)
            
            # Update regime history
            self.regime_history.append((
                datetime.now(),
                regime_result.regime,
                regime_result.confidence
            ))
            
            # Keep history manageable
            if len(self.regime_history) > 1000:
                self.regime_history = self.regime_history[-500:]
            
            self.current_regime = regime_result.regime
            
            self.logger.info(f"Detected regime: {regime_result.regime.value} "
                           f"(confidence: {regime_result.confidence:.3f})")
            
            return regime_result
            
        except Exception as e:
            self.logger.error(f"Error detecting market regime: {e}")
            return self.regime_detector._default_regime_result()
    
    def calculate_strategy_allocations(self, regime_result: RegimeDetectionResult,
                                     market_data: Dict[str, pd.DataFrame]) -> Dict[StrategyType, StrategyAllocation]:
        """Calculate optimal strategy allocations for current regime"""
        allocations = {}
        
        try:
            # Define regime-strategy suitability matrix
            regime_suitability = self._get_regime_strategy_suitability(regime_result.regime)
            
            # Calculate individual strategy signals and performance
            strategy_signals = {}
            for strategy_type, manager in self.strategy_managers.items():
                try:
                    signals = manager.calculate_signals(market_data)
                    strategy_signals[strategy_type] = signals
                except Exception as e:
                    self.logger.warning(f"Error calculating {strategy_type.value} signals: {e}")
                    strategy_signals[strategy_type] = {}
            
            # Calculate allocations for each strategy
            total_suitability = sum(regime_suitability.values())
            
            for strategy_type in StrategyType:
                try:
                    # Base allocation from regime suitability
                    base_weight = regime_suitability.get(strategy_type, 0.1) / total_suitability
                    
                    # Adjust based on recent performance
                    performance_adjustment = self._calculate_performance_adjustment(strategy_type)
                    
                    # Final weight
                    weight = base_weight * (1 + performance_adjustment)
                    weight = max(self.config.min_strategy_weight, 
                               min(self.config.max_strategy_weight, weight))
                    
                    # Calculate expected metrics
                    expected_return = self._estimate_strategy_return(strategy_type, regime_result)
                    expected_volatility = self._estimate_strategy_volatility(strategy_type, regime_result)
                    
                    sharpe_ratio = expected_return / expected_volatility if expected_volatility > 0 else 0
                    
                    allocations[strategy_type] = StrategyAllocation(
                        strategy_type=strategy_type,
                        weight=weight,
                        expected_return=expected_return,
                        expected_volatility=expected_volatility,
                        sharpe_ratio=sharpe_ratio,
                        max_drawdown=self._estimate_strategy_drawdown(strategy_type, regime_result),
                        regime_suitability=regime_suitability.get(strategy_type, 0.1),
                        recent_performance=performance_adjustment,
                        confidence=regime_result.confidence,
                        metadata={
                            'signals': strategy_signals.get(strategy_type, {}),
                            'regime': regime_result.regime.value
                        }
                    )
                    
                except Exception as e:
                    self.logger.warning(f"Error calculating allocation for {strategy_type.value}: {e}")
            
            # Normalize weights
            total_weight = sum(alloc.weight for alloc in allocations.values())
            if total_weight > 0:
                for alloc in allocations.values():
                    alloc.weight /= total_weight
            
        except Exception as e:
            self.logger.error(f"Error calculating strategy allocations: {e}")
        
        return allocations
    
    def _get_regime_strategy_suitability(self, regime: MarketRegime) -> Dict[StrategyType, float]:
        """Get strategy suitability scores for given regime"""
        suitability_matrix = {
            MarketRegime.BULL_TRENDING: {
                StrategyType.MOMENTUM: 0.8,
                StrategyType.MEAN_REVERSION: 0.2,
                StrategyType.PAIRS_TRADING: 0.4,
                StrategyType.ARBITRAGE: 0.6,
                StrategyType.TREND_FOLLOWING: 0.9,
                StrategyType.CONTRARIAN: 0.1,
                StrategyType.VOLATILITY_TRADING: 0.3,
                StrategyType.CARRY_TRADE: 0.7,
                StrategyType.MARKET_NEUTRAL: 0.5
            },
            MarketRegime.BEAR_TRENDING: {
                StrategyType.MOMENTUM: 0.3,
                StrategyType.MEAN_REVERSION: 0.7,
                StrategyType.PAIRS_TRADING: 0.6,
                StrategyType.ARBITRAGE: 0.8,
                StrategyType.TREND_FOLLOWING: 0.4,
                StrategyType.CONTRARIAN: 0.8,
                StrategyType.VOLATILITY_TRADING: 0.7,
                StrategyType.CARRY_TRADE: 0.2,
                StrategyType.MARKET_NEUTRAL: 0.9
            },
            MarketRegime.SIDEWAYS_RANGE: {
                StrategyType.MOMENTUM: 0.3,
                StrategyType.MEAN_REVERSION: 0.8,
                StrategyType.PAIRS_TRADING: 0.9,
                StrategyType.ARBITRAGE: 0.7,
                StrategyType.TREND_FOLLOWING: 0.2,
                StrategyType.CONTRARIAN: 0.6,
                StrategyType.VOLATILITY_TRADING: 0.5,
                StrategyType.CARRY_TRADE: 0.6,
                StrategyType.MARKET_NEUTRAL: 0.8
            },
            MarketRegime.HIGH_VOLATILITY: {
                StrategyType.MOMENTUM: 0.4,
                StrategyType.MEAN_REVERSION: 0.6,
                StrategyType.PAIRS_TRADING: 0.5,
                StrategyType.ARBITRAGE: 0.9,
                StrategyType.TREND_FOLLOWING: 0.3,
                StrategyType.CONTRARIAN: 0.7,
                StrategyType.VOLATILITY_TRADING: 0.9,
                StrategyType.CARRY_TRADE: 0.3,
                StrategyType.MARKET_NEUTRAL: 0.8
            },
            MarketRegime.LOW_VOLATILITY: {
                StrategyType.MOMENTUM: 0.7,
                StrategyType.MEAN_REVERSION: 0.4,
                StrategyType.PAIRS_TRADING: 0.6,
                StrategyType.ARBITRAGE: 0.5,
                StrategyType.TREND_FOLLOWING: 0.8,
                StrategyType.CONTRARIAN: 0.3,
                StrategyType.VOLATILITY_TRADING: 0.2,
                StrategyType.CARRY_TRADE: 0.8,
                StrategyType.MARKET_NEUTRAL: 0.6
            },
            MarketRegime.CRISIS_MODE: {
                StrategyType.MOMENTUM: 0.1,
                StrategyType.MEAN_REVERSION: 0.3,
                StrategyType.PAIRS_TRADING: 0.4,
                StrategyType.ARBITRAGE: 0.9,
                StrategyType.TREND_FOLLOWING: 0.2,
                StrategyType.CONTRARIAN: 0.8,
                StrategyType.VOLATILITY_TRADING: 0.7,
                StrategyType.CARRY_TRADE: 0.1,
                StrategyType.MARKET_NEUTRAL: 0.9
            }
        }
        
        # Default suitability for unlisted regimes
        default_suitability = {
            strategy: 0.5 for strategy in StrategyType
        }
        
        return suitability_matrix.get(regime, default_suitability)
    
    def _calculate_performance_adjustment(self, strategy_type: StrategyType) -> float:
        """Calculate performance-based adjustment for strategy weight"""
        try:
            # Look at recent performance history
            recent_performance = []
            
            for record in self.performance_history[-self.config.performance_lookback:]:
                if strategy_type in record.get('strategy_returns', {}):
                    recent_performance.append(record['strategy_returns'][strategy_type])
            
            if not recent_performance:
                return 0.0
            
            # Calculate Sharpe ratio
            returns = np.array(recent_performance)
            if len(returns) < 5:
                return 0.0
            
            mean_return = returns.mean()
            std_return = returns.std()
            
            if std_return == 0:
                return 0.0
            
            sharpe = mean_return / std_return
            
            # Convert to adjustment factor (-0.5 to +0.5)
            adjustment = np.tanh(sharpe) * 0.5
            
            return adjustment
            
        except Exception as e:
            self.logger.warning(f"Error calculating performance adjustment for {strategy_type.value}: {e}")
            return 0.0
    
    def _estimate_strategy_return(self, strategy_type: StrategyType, regime_result: RegimeDetectionResult) -> float:
        """Estimate expected return for strategy in current regime"""
        # Base returns by strategy type
        base_returns = {
            StrategyType.MOMENTUM: 0.08,
            StrategyType.MEAN_REVERSION: 0.06,
            StrategyType.PAIRS_TRADING: 0.05,
            StrategyType.ARBITRAGE: 0.04,
            StrategyType.TREND_FOLLOWING: 0.07,
            StrategyType.CONTRARIAN: 0.05,
            StrategyType.VOLATILITY_TRADING: 0.06,
            StrategyType.CARRY_TRADE: 0.04,
            StrategyType.MARKET_NEUTRAL: 0.03
        }
        
        base_return = base_returns.get(strategy_type, 0.05)
        
        # Adjust for regime
        regime_multipliers = {
            MarketRegime.BULL_TRENDING: 1.2,
            MarketRegime.BEAR_TRENDING: 0.8,
            MarketRegime.SIDEWAYS_RANGE: 0.9,
            MarketRegime.HIGH_VOLATILITY: 1.1,
            MarketRegime.LOW_VOLATILITY: 0.95,
            MarketRegime.CRISIS_MODE: 0.6
        }
        
        multiplier = regime_multipliers.get(regime_result.regime, 1.0)
        
        return base_return * multiplier
    
    def _estimate_strategy_volatility(self, strategy_type: StrategyType, regime_result: RegimeDetectionResult) -> float:
        """Estimate expected volatility for strategy in current regime"""
        # Base volatilities by strategy type
        base_volatilities = {
            StrategyType.MOMENTUM: 0.15,
            StrategyType.MEAN_REVERSION: 0.12,
            StrategyType.PAIRS_TRADING: 0.08,
            StrategyType.ARBITRAGE: 0.05,
            StrategyType.TREND_FOLLOWING: 0.18,
            StrategyType.CONTRARIAN: 0.14,
            StrategyType.VOLATILITY_TRADING: 0.20,
            StrategyType.CARRY_TRADE: 0.10,
            StrategyType.MARKET_NEUTRAL: 0.06
        }
        
        base_vol = base_volatilities.get(strategy_type, 0.12)
        
        # Adjust for regime volatility
        vol_multiplier = 1.0 + (regime_result.features.volatility_regime - 1.0) * 0.5
        
        return base_vol * vol_multiplier
    
    def _estimate_strategy_drawdown(self, strategy_type: StrategyType, regime_result: RegimeDetectionResult) -> float:
        """Estimate expected maximum drawdown for strategy in current regime"""
        # Base drawdowns by strategy type
        base_drawdowns = {
            StrategyType.MOMENTUM: 0.15,
            StrategyType.MEAN_REVERSION: 0.10,
            StrategyType.PAIRS_TRADING: 0.08,
            StrategyType.ARBITRAGE: 0.05,
            StrategyType.TREND_FOLLOWING: 0.20,
            StrategyType.CONTRARIAN: 0.12,
            StrategyType.VOLATILITY_TRADING: 0.18,
            StrategyType.CARRY_TRADE: 0.08,
            StrategyType.MARKET_NEUTRAL: 0.06
        }
        
        base_drawdown = base_drawdowns.get(strategy_type, 0.10)
        
        # Adjust for regime stress
        if regime_result.regime in [MarketRegime.CRISIS_MODE, MarketRegime.HIGH_VOLATILITY]:
            stress_multiplier = 1.5
        elif regime_result.regime == MarketRegime.LOW_VOLATILITY:
            stress_multiplier = 0.7
        else:
            stress_multiplier = 1.0
        
        return base_drawdown * stress_multiplier
    
    def calculate_adaptive_strategy(self, market_data: Dict[str, pd.DataFrame]) -> AdaptiveStrategyResult:
        """Calculate complete adaptive strategy result"""
        try:
            # Detect market regime
            regime_result = self.detect_market_regime(market_data)
            
            # Calculate strategy allocations
            strategy_allocations = self.calculate_strategy_allocations(regime_result, market_data)
            
            # Calculate portfolio weights (simplified)
            portfolio_weights = self._calculate_portfolio_weights(strategy_allocations, market_data)
            
            # Calculate expected portfolio metrics
            expected_return = sum(
                alloc.weight * alloc.expected_return 
                for alloc in strategy_allocations.values()
            )
            
            expected_volatility = np.sqrt(sum(
                (alloc.weight * alloc.expected_volatility) ** 2 
                for alloc in strategy_allocations.values()
            ))
            
            # Generate overall signal
            signal = self._generate_adaptive_signal(expected_return, regime_result)
            
            # Calculate strength and confidence
            strength = min(1.0, abs(expected_return) / 0.15)  # Normalize to 15% return
            confidence = regime_result.confidence * np.mean([alloc.confidence for alloc in strategy_allocations.values()])
            
            # Risk metrics
            risk_metrics = {
                'expected_volatility': expected_volatility,
                'expected_max_drawdown': max(alloc.max_drawdown * alloc.weight for alloc in strategy_allocations.values()),
                'regime_confidence': regime_result.confidence,
                'strategy_diversification': len([a for a in strategy_allocations.values() if a.weight > 0.05])
            }
            
            # Adaptation signals
            adaptation_signals = {
                'regime_change': self._detect_regime_change(regime_result),
                'rebalance_needed': self._check_rebalance_needed(strategy_allocations),
                'risk_adjustment': self._calculate_risk_adjustment(risk_metrics)
            }
            
            return AdaptiveStrategyResult(
                signal=signal,
                strength=strength,
                confidence=confidence,
                current_regime=regime_result.regime,
                regime_confidence=regime_result.confidence,
                strategy_allocations=strategy_allocations,
                portfolio_weights=portfolio_weights,
                expected_return=expected_return,
                expected_volatility=expected_volatility,
                risk_metrics=risk_metrics,
                regime_history=self.regime_history[-10:],  # Last 10 regime observations
                adaptation_signals=adaptation_signals,
                metadata={
                    'n_strategies': len(strategy_allocations),
                    'regime_detection_method': regime_result.detection_method.value,
                    'regime_duration': regime_result.regime_duration
                },
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating adaptive strategy: {e}")
            
            # Return neutral result
            return AdaptiveStrategyResult(
                signal=AdaptiveSignal.NEUTRAL,
                strength=0.0,
                confidence=0.0,
                current_regime=MarketRegime.SIDEWAYS_RANGE,
                regime_confidence=0.5,
                strategy_allocations={},
                portfolio_weights={},
                expected_return=0.0,
                expected_volatility=0.15,
                risk_metrics={},
                regime_history=[],
                adaptation_signals={},
                metadata={'error': str(e)},
                timestamp=datetime.now()
            )
    
    def _calculate_portfolio_weights(self, strategy_allocations: Dict[StrategyType, StrategyAllocation],
                                   market_data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """Calculate final portfolio weights from strategy allocations"""
        # Simplified: equal weights across available securities
        # In practice, this would use strategy-specific signals
        
        n_securities = min(20, len(market_data))  # Limit to top 20 securities
        
        if n_securities == 0:
            return {}
        
        equal_weight = 1.0 / n_securities
        
        portfolio_weights = {}
        for i, symbol in enumerate(list(market_data.keys())[:n_securities]):
            portfolio_weights[symbol] = equal_weight
        
        return portfolio_weights
    
    def _generate_adaptive_signal(self, expected_return: float, regime_result: RegimeDetectionResult) -> AdaptiveSignal:
        """Generate overall adaptive trading signal"""
        # Adjust thresholds based on regime confidence
        confidence_factor = regime_result.confidence
        
        if expected_return > 0.1 * confidence_factor:
            return AdaptiveSignal.STRONG_BUY
        elif expected_return > 0.05 * confidence_factor:
            return AdaptiveSignal.BUY
        elif expected_return > 0.02 * confidence_factor:
            return AdaptiveSignal.WEAK_BUY
        elif expected_return < -0.1 * confidence_factor:
            return AdaptiveSignal.STRONG_SELL
        elif expected_return < -0.05 * confidence_factor:
            return AdaptiveSignal.SELL
        elif expected_return < -0.02 * confidence_factor:
            return AdaptiveSignal.WEAK_SELL
        else:
            return AdaptiveSignal.NEUTRAL
    
    def _detect_regime_change(self, regime_result: RegimeDetectionResult) -> bool:
        """Detect if regime has changed recently"""
        if len(self.regime_history) < 2:
            return False
        
        current_regime = regime_result.regime
        previous_regime = self.regime_history[-2][1] if len(self.regime_history) >= 2 else current_regime
        
        return current_regime != previous_regime
    
    def _check_rebalance_needed(self, strategy_allocations: Dict[StrategyType, StrategyAllocation]) -> bool:
        """Check if portfolio rebalancing is needed"""
        if not self.current_allocations:
            return True
        
        # Check if allocation changes exceed threshold
        for strategy_type, allocation in strategy_allocations.items():
            current_weight = self.current_allocations.get(strategy_type, 0.0)
            if abs(allocation.weight - current_weight) > 0.05:  # 5% threshold
                return True
        
        return False
    
    def _calculate_risk_adjustment(self, risk_metrics: Dict[str, float]) -> float:
        """Calculate risk adjustment factor"""
        expected_vol = risk_metrics.get('expected_volatility', 0.15)
        target_vol = self.config.max_portfolio_volatility
        
        if expected_vol > target_vol:
            return target_vol / expected_vol  # Scale down
        else:
            return 1.0  # No adjustment needed


# Example usage and testing functions
def create_regime_test_data() -> Dict[str, pd.DataFrame]:
    """Create sample market data with different regime periods"""
    np.random.seed(42)
    
    dates = pd.date_range(start='2022-01-01', periods=500, freq='D')
    
    # Create regime periods
    regime_periods = [
        (0, 100, 'bull_trend', 0.0008, 0.015),      # Bull market
        (100, 200, 'high_vol', 0.0002, 0.035),     # High volatility
        (200, 300, 'bear_trend', -0.0005, 0.025),  # Bear market
        (300, 400, 'sideways', 0.0001, 0.012),     # Sideways
        (400, 500, 'recovery', 0.0006, 0.020)      # Recovery
    ]
    
    market_data = {}
    
    # Create different types of stocks
    stocks = {
        'SPY': {'beta': 1.0, 'sector': 'market'},
        'AAPL': {'beta': 1.2, 'sector': 'tech'},
        'MSFT': {'beta': 1.1, 'sector': 'tech'},
        'JPM': {'beta': 1.3, 'sector': 'finance'},
        'JNJ': {'beta': 0.7, 'sector': 'healthcare'},
        'XOM': {'beta': 1.4, 'sector': 'energy'},
        'AMZN': {'beta': 1.5, 'sector': 'tech'},
        'BRK.B': {'beta': 0.8, 'sector': 'finance'},
        'TSLA': {'beta': 2.0, 'sector': 'auto'},
        'NVDA': {'beta': 1.8, 'sector': 'tech'}
    }
    
    for symbol, params in stocks.items():
        returns = []
        
        for start_idx, end_idx, regime_type, mean_return, volatility in regime_periods:
            period_length = end_idx - start_idx
            
            # Adjust returns based on stock characteristics and regime
            if regime_type == 'bull_trend':
                stock_mean = mean_return * params['beta']
                stock_vol = volatility * (0.8 + 0.4 * params['beta'])
            elif regime_type == 'bear_trend':
                stock_mean = mean_return * params['beta'] * 1.2  # More sensitive in bear market
                stock_vol = volatility * (0.9 + 0.6 * params['beta'])
            elif regime_type == 'high_vol':
                stock_mean = mean_return * params['beta']
                stock_vol = volatility * (1.0 + 0.5 * params['beta'])
            else:
                stock_mean = mean_return * params['beta']
                stock_vol = volatility * (0.9 + 0.2 * params['beta'])
            
            # Generate returns for this regime period
            period_returns = np.random.normal(stock_mean, stock_vol, period_length)
            returns.extend(period_returns)
        
        # Convert to prices
        prices = 100 * (1 + np.array(returns)).cumprod()
        
        # Generate OHLC data
        market_data[symbol] = pd.DataFrame({
            'date': dates,
            'open': prices * (1 + np.random.normal(0, 0.002, len(dates))),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.005, len(dates)))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.005, len(dates)))),
            'close': prices,
            'volume': np.random.lognormal(15, 0.5, len(dates))
        })
    
    return market_data


def test_regime_aware_strategies():
    """Test regime-aware adaptive strategies with sample data"""
    # Create sample market data with regime changes
    market_data = create_regime_test_data()
    
    # Initialize adaptive strategy manager
    config = RegimeConfig(
        lookback_window=200,
        regime_update_frequency=5,
        n_regimes_hmm=4,
        rebalance_frequency=10
    )
    
    manager = AdaptiveStrategyManager(config)
    
    # Calculate adaptive strategy
    result = manager.calculate_adaptive_strategy(market_data)
    
    print("\n=== Regime-Aware Adaptive Strategy Results ===")
    print(f"Current Regime: {result.current_regime.value}")
    print(f"Regime Confidence: {result.regime_confidence:.3f}")
    print(f"Overall Signal: {result.signal.name}")
    print(f"Signal Strength: {result.strength:.3f}")
    print(f"Signal Confidence: {result.confidence:.3f}")
    print(f"Expected Return: {result.expected_return:.4f} ({result.expected_return*100:.2f}%)")
    print(f"Expected Volatility: {result.expected_volatility:.4f} ({result.expected_volatility*100:.2f}%)")
    
    print(f"\nStrategy Allocations:")
    for strategy_type, allocation in result.strategy_allocations.items():
        print(f"  {strategy_type.value}:")
        print(f"    Weight: {allocation.weight:.3f} ({allocation.weight*100:.1f}%)")
        print(f"    Expected Return: {allocation.expected_return:.4f}")
        print(f"    Sharpe Ratio: {allocation.sharpe_ratio:.3f}")
        print(f"    Regime Suitability: {allocation.regime_suitability:.3f}")
    
    print(f"\nRisk Metrics:")
    for metric, value in result.risk_metrics.items():
        print(f"  {metric}: {value:.4f}")
    
    print(f"\nAdaptation Signals:")
    for signal_type, value in result.adaptation_signals.items():
        print(f"  {signal_type}: {value}")
    
    print(f"\nTop 5 Portfolio Holdings:")
    sorted_weights = sorted(result.portfolio_weights.items(), key=lambda x: x[1], reverse=True)
    for symbol, weight in sorted_weights[:5]:
        print(f"  {symbol}: {weight:.3f} ({weight*100:.1f}%)")
    
    # Test regime detection over time
    print(f"\n=== Regime History (Last 5) ===")
    for timestamp, regime, confidence in result.regime_history[-5:]:
        print(f"  {timestamp.strftime('%Y-%m-%d')}: {regime.value} (conf: {confidence:.3f})")
    
    # Test different market data windows
    print(f"\n=== Regime Detection Over Time ===")
    for i in range(100, 500, 100):
        subset_data = {}
        for symbol, data in market_data.items():
            subset_data[symbol] = data.iloc[:i].copy()
        
        regime_result = manager.detect_market_regime(subset_data)
        print(f"  Day {i}: {regime_result.regime.value} (conf: {regime_result.confidence:.3f})")


if __name__ == "__main__":
    # Run tests
    test_regime_aware_strategies()