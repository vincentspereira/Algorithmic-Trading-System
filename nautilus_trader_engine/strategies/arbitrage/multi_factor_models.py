"""Multi-Factor Models and Statistical Strategies

This module implements multi-factor models and statistical arbitrage strategies
based on academic factor research and quantitative finance principles.

Key Features:
- Fama-French factor models (3-factor, 5-factor)
- Momentum and reversal factors
- Quality and profitability factors
- Value and growth factors
- Low volatility and size factors
- Custom factor construction
- Factor timing and allocation
- Risk model integration

Strategies:
- MultiFactorStrategy: Base multi-factor implementation
- FamaFrenchStrategy: Fama-French factor models
- MomentumFactorStrategy: Momentum-based factors
- QualityFactorStrategy: Quality and profitability factors

Architecture:
- Follows 5-Pillar Architecture principles
- Statistical factor analysis
- Risk-adjusted factor exposure
- Dynamic factor allocation
"""

import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Union
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# Core imports
from ...core.data_types import MarketData, Signal, Position
from ...core.events import SignalEvent, OrderEvent
from ...core.risk_management import RiskManager
from ...core.portfolio_management import PortfolioManager
from ...core.signal_generator import SignalGenerator
from ..core.base_strategy import BaseStrategy, StrategyConfig
from ...utils.technical_indicators import (
    calculate_sma, calculate_ema, calculate_rsi,
    calculate_bollinger_bands, calculate_correlation
)
from ...utils.market_utils import (
    calculate_returns, calculate_volatility,
    normalize_prices, validate_market_data
)

# Configure logging
logger = logging.getLogger(__name__)

class FactorType(Enum):
    """Types of factors in multi-factor models"""
    VALUE = "value"                    # Value factors (P/E, P/B, etc.)
    MOMENTUM = "momentum"              # Price and earnings momentum
    QUALITY = "quality"                # Quality and profitability
    SIZE = "size"                      # Market capitalization
    VOLATILITY = "volatility"          # Low volatility factor
    GROWTH = "growth"                  # Growth factors
    PROFITABILITY = "profitability"    # Profitability metrics
    INVESTMENT = "investment"          # Investment and asset growth
    MARKET = "market"                  # Market beta factor
    CUSTOM = "custom"                  # Custom factors

@dataclass
class FactorExposure:
    """Represents factor exposure for an asset"""
    symbol: str
    factor_type: FactorType
    exposure: float
    z_score: float
    percentile: float
    factor_return: float = 0.0
    factor_volatility: float = 0.0
    t_stat: float = 0.0
    p_value: float = 1.0
    
    @property
    def is_significant(self) -> bool:
        """Check if factor exposure is statistically significant"""
        return self.p_value < 0.05 and abs(self.t_stat) > 2.0

@dataclass
class FactorModel:
    """Represents a multi-factor model"""
    name: str
    factors: List[FactorType]
    factor_loadings: Dict[str, float] = field(default_factory=dict)
    factor_returns: Dict[str, pd.Series] = field(default_factory=dict)
    r_squared: float = 0.0
    alpha: float = 0.0
    alpha_t_stat: float = 0.0
    residual_volatility: float = 0.0
    information_ratio: float = 0.0
    sharpe_ratio: float = 0.0
    
    def __post_init__(self):
        """Initialize factor model"""
        if not self.factor_loadings:
            self.factor_loadings = {factor.value: 0.0 for factor in self.factors}

class FactorAnalyzer:
    """Analyzes factor exposures and constructs factor models"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.lookback_period = config.get('lookback_period', 252)
        self.rebalance_frequency = config.get('rebalance_frequency', 21)  # Monthly
        self.min_observations = config.get('min_observations', 60)
        self.factor_decay = config.get('factor_decay', 0.94)  # Half-life ~12 periods
        
        # Factor data storage
        self.price_data: Dict[str, pd.Series] = {}
        self.fundamental_data: Dict[str, Dict[str, float]] = {}
        self.factor_scores: Dict[str, Dict[FactorType, float]] = {}
        self.factor_returns: Dict[FactorType, pd.Series] = {}
        
        # Factor construction parameters
        self.factor_params = {
            FactorType.VALUE: {'metrics': ['pe_ratio', 'pb_ratio', 'ev_ebitda'], 'direction': -1},
            FactorType.MOMENTUM: {'lookback': [21, 63, 252], 'skip': 21, 'direction': 1},
            FactorType.QUALITY: {'metrics': ['roe', 'roa', 'debt_to_equity'], 'direction': 1},
            FactorType.SIZE: {'metric': 'market_cap', 'direction': -1},
            FactorType.VOLATILITY: {'lookback': 252, 'direction': -1},
            FactorType.GROWTH: {'metrics': ['revenue_growth', 'earnings_growth'], 'direction': 1},
            FactorType.PROFITABILITY: {'metrics': ['gross_margin', 'operating_margin'], 'direction': 1}
        }
        
        logger.info("FactorAnalyzer initialized")
    
    def update_fundamental_data(self, symbol: str, data: Dict[str, float]) -> None:
        """Update fundamental data for a symbol
        
        Args:
            symbol: Stock symbol
            data: Dictionary of fundamental metrics
        """
        self.fundamental_data[symbol] = data
        logger.debug(f"Updated fundamental data for {symbol}: {len(data)} metrics")
    
    def calculate_factor_score(self, symbol: str, factor_type: FactorType) -> Optional[float]:
        """Calculate factor score for a symbol
        
        Args:
            symbol: Stock symbol
            factor_type: Type of factor to calculate
            
        Returns:
            Factor score or None if insufficient data
        """
        try:
            if factor_type == FactorType.VALUE:
                return self._calculate_value_score(symbol)
            elif factor_type == FactorType.MOMENTUM:
                return self._calculate_momentum_score(symbol)
            elif factor_type == FactorType.QUALITY:
                return self._calculate_quality_score(symbol)
            elif factor_type == FactorType.SIZE:
                return self._calculate_size_score(symbol)
            elif factor_type == FactorType.VOLATILITY:
                return self._calculate_volatility_score(symbol)
            elif factor_type == FactorType.GROWTH:
                return self._calculate_growth_score(symbol)
            elif factor_type == FactorType.PROFITABILITY:
                return self._calculate_profitability_score(symbol)
            else:
                logger.warning(f"Unknown factor type: {factor_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error calculating {factor_type.value} score for {symbol}: {e}")
            return None
    
    def _calculate_value_score(self, symbol: str) -> Optional[float]:
        """Calculate value factor score
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Value score (higher = more value)
        """
        try:
            if symbol not in self.fundamental_data:
                return None
            
            data = self.fundamental_data[symbol]
            scores = []
            
            # P/E ratio (lower is better)
            if 'pe_ratio' in data and data['pe_ratio'] > 0:
                pe_score = 1 / data['pe_ratio']  # Invert so higher is better
                scores.append(pe_score)
            
            # P/B ratio (lower is better)
            if 'pb_ratio' in data and data['pb_ratio'] > 0:
                pb_score = 1 / data['pb_ratio']
                scores.append(pb_score)
            
            # EV/EBITDA (lower is better)
            if 'ev_ebitda' in data and data['ev_ebitda'] > 0:
                ev_ebitda_score = 1 / data['ev_ebitda']
                scores.append(ev_ebitda_score)
            
            # Price/Sales (lower is better)
            if 'ps_ratio' in data and data['ps_ratio'] > 0:
                ps_score = 1 / data['ps_ratio']
                scores.append(ps_score)
            
            if scores:
                return np.mean(scores)
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating value score: {e}")
            return None
    
    def _calculate_momentum_score(self, symbol: str) -> Optional[float]:
        """Calculate momentum factor score
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Momentum score
        """
        try:
            if symbol not in self.price_data:
                return None
            
            prices = self.price_data[symbol]
            if len(prices) < 252:  # Need at least 1 year of data
                return None
            
            # Calculate returns over different periods
            returns = []
            
            # 1-month momentum (skip last month to avoid reversal)
            if len(prices) >= 42:  # 21 + 21
                ret_1m = (prices.iloc[-21] / prices.iloc[-42] - 1)
                returns.append(ret_1m)
            
            # 3-month momentum
            if len(prices) >= 84:  # 63 + 21
                ret_3m = (prices.iloc[-21] / prices.iloc[-84] - 1)
                returns.append(ret_3m)
            
            # 6-month momentum
            if len(prices) >= 147:  # 126 + 21
                ret_6m = (prices.iloc[-21] / prices.iloc[-147] - 1)
                returns.append(ret_6m)
            
            # 12-month momentum
            if len(prices) >= 273:  # 252 + 21
                ret_12m = (prices.iloc[-21] / prices.iloc[-273] - 1)
                returns.append(ret_12m)
            
            if returns:
                # Weight recent returns more heavily
                weights = np.array([0.4, 0.3, 0.2, 0.1])[:len(returns)]
                weights = weights / weights.sum()
                momentum_score = np.average(returns, weights=weights)
                return momentum_score
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating momentum score: {e}")
            return None
    
    def _calculate_quality_score(self, symbol: str) -> Optional[float]:
        """Calculate quality factor score
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Quality score
        """
        try:
            if symbol not in self.fundamental_data:
                return None
            
            data = self.fundamental_data[symbol]
            scores = []
            
            # Return on Equity (higher is better)
            if 'roe' in data:
                scores.append(data['roe'])
            
            # Return on Assets (higher is better)
            if 'roa' in data:
                scores.append(data['roa'])
            
            # Debt to Equity (lower is better)
            if 'debt_to_equity' in data:
                debt_score = -data['debt_to_equity']  # Negative so lower debt = higher score
                scores.append(debt_score)
            
            # Interest Coverage (higher is better)
            if 'interest_coverage' in data and data['interest_coverage'] > 0:
                # Cap at reasonable level to avoid outliers
                coverage_score = min(data['interest_coverage'], 50) / 50
                scores.append(coverage_score)
            
            # Earnings Stability (lower volatility is better)
            if 'earnings_volatility' in data and data['earnings_volatility'] > 0:
                stability_score = 1 / (1 + data['earnings_volatility'])
                scores.append(stability_score)
            
            if scores:
                return np.mean(scores)
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating quality score: {e}")
            return None
    
    def _calculate_size_score(self, symbol: str) -> Optional[float]:
        """Calculate size factor score
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Size score (higher = smaller company)
        """
        try:
            if symbol not in self.fundamental_data:
                return None
            
            data = self.fundamental_data[symbol]
            
            if 'market_cap' in data and data['market_cap'] > 0:
                # Use log of market cap, then invert so smaller = higher score
                log_market_cap = np.log(data['market_cap'])
                # Normalize around typical large cap (~$10B)
                size_score = max(0, 25 - log_market_cap)  # ln(10B) ≈ 23
                return size_score
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating size score: {e}")
            return None
    
    def _calculate_volatility_score(self, symbol: str) -> Optional[float]:
        """Calculate low volatility factor score
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Volatility score (higher = lower volatility)
        """
        try:
            if symbol not in self.price_data:
                return None
            
            prices = self.price_data[symbol]
            if len(prices) < 63:  # Need at least 3 months
                return None
            
            # Calculate returns
            returns = prices.pct_change().dropna()
            
            if len(returns) < 21:
                return None
            
            # Calculate volatility over different periods
            vol_1m = returns.tail(21).std() * np.sqrt(252)
            vol_3m = returns.tail(63).std() * np.sqrt(252) if len(returns) >= 63 else vol_1m
            vol_6m = returns.tail(126).std() * np.sqrt(252) if len(returns) >= 126 else vol_3m
            
            # Average volatility with more weight on recent
            avg_vol = 0.5 * vol_1m + 0.3 * vol_3m + 0.2 * vol_6m
            
            # Convert to score (lower volatility = higher score)
            # Normalize around 20% annual volatility
            vol_score = max(0, 1 - (avg_vol / 0.4))  # Score of 0.5 at 20% vol
            
            return vol_score
            
        except Exception as e:
            logger.error(f"Error calculating volatility score: {e}")
            return None
    
    def _calculate_growth_score(self, symbol: str) -> Optional[float]:
        """Calculate growth factor score
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Growth score
        """
        try:
            if symbol not in self.fundamental_data:
                return None
            
            data = self.fundamental_data[symbol]
            scores = []
            
            # Revenue growth (higher is better)
            if 'revenue_growth' in data:
                scores.append(data['revenue_growth'])
            
            # Earnings growth (higher is better)
            if 'earnings_growth' in data:
                scores.append(data['earnings_growth'])
            
            # Book value growth
            if 'book_value_growth' in data:
                scores.append(data['book_value_growth'])
            
            if scores:
                return np.mean(scores)
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating growth score: {e}")
            return None
    
    def _calculate_profitability_score(self, symbol: str) -> Optional[float]:
        """Calculate profitability factor score
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Profitability score
        """
        try:
            if symbol not in self.fundamental_data:
                return None
            
            data = self.fundamental_data[symbol]
            scores = []
            
            # Gross margin (higher is better)
            if 'gross_margin' in data:
                scores.append(data['gross_margin'])
            
            # Operating margin (higher is better)
            if 'operating_margin' in data:
                scores.append(data['operating_margin'])
            
            # Net margin (higher is better)
            if 'net_margin' in data:
                scores.append(data['net_margin'])
            
            # Return on Invested Capital
            if 'roic' in data:
                scores.append(data['roic'])
            
            if scores:
                return np.mean(scores)
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating profitability score: {e}")
            return None
    
    def construct_factor_portfolio(
        self,
        symbols: List[str],
        factor_type: FactorType,
        long_pct: float = 0.2,
        short_pct: float = 0.2
    ) -> Dict[str, float]:
        """Construct long-short factor portfolio
        
        Args:
            symbols: List of symbols to consider
            factor_type: Factor to construct portfolio for
            long_pct: Percentage of symbols to go long
            short_pct: Percentage of symbols to go short
            
        Returns:
            Dictionary of symbol weights
        """
        try:
            # Calculate factor scores for all symbols
            factor_scores = {}
            for symbol in symbols:
                score = self.calculate_factor_score(symbol, factor_type)
                if score is not None:
                    factor_scores[symbol] = score
            
            if len(factor_scores) < 10:  # Need minimum number of stocks
                return {}
            
            # Sort by factor score
            sorted_symbols = sorted(factor_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Select long and short positions
            n_long = max(1, int(len(sorted_symbols) * long_pct))
            n_short = max(1, int(len(sorted_symbols) * short_pct))
            
            long_symbols = [s[0] for s in sorted_symbols[:n_long]]
            short_symbols = [s[0] for s in sorted_symbols[-n_short:]]
            
            # Create portfolio weights
            portfolio_weights = {}
            
            # Equal weight long positions
            long_weight = 0.5 / len(long_symbols) if long_symbols else 0
            for symbol in long_symbols:
                portfolio_weights[symbol] = long_weight
            
            # Equal weight short positions
            short_weight = -0.5 / len(short_symbols) if short_symbols else 0
            for symbol in short_symbols:
                portfolio_weights[symbol] = short_weight
            
            logger.info(f"Constructed {factor_type.value} portfolio: {len(long_symbols)} long, {len(short_symbols)} short")
            return portfolio_weights
            
        except Exception as e:
            logger.error(f"Error constructing factor portfolio: {e}")
            return {}
    
    def calculate_factor_returns(self, factor_type: FactorType, symbols: List[str]) -> pd.Series:
        """Calculate factor returns over time
        
        Args:
            factor_type: Factor to calculate returns for
            symbols: List of symbols in universe
            
        Returns:
            Time series of factor returns
        """
        try:
            # This is a simplified implementation
            # In practice, would need historical factor scores and returns
            
            factor_returns = pd.Series(dtype=float)
            
            # Get common dates from price data
            if not self.price_data:
                return factor_returns
            
            # Find common date range
            all_dates = set()
            for symbol in symbols:
                if symbol in self.price_data:
                    all_dates.update(self.price_data[symbol].index)
            
            if not all_dates:
                return factor_returns
            
            common_dates = sorted(all_dates)
            
            # Calculate factor returns for each date (simplified)
            for i, date in enumerate(common_dates[self.rebalance_frequency::self.rebalance_frequency]):
                # Construct portfolio at rebalance date
                portfolio_weights = self.construct_factor_portfolio(symbols, factor_type)
                
                if not portfolio_weights:
                    continue
                
                # Calculate return over next period
                next_date_idx = min(i + self.rebalance_frequency, len(common_dates) - 1)
                if next_date_idx < len(common_dates):
                    next_date = common_dates[next_date_idx]
                    
                    period_return = 0.0
                    total_weight = 0.0
                    
                    for symbol, weight in portfolio_weights.items():
                        if symbol in self.price_data:
                            prices = self.price_data[symbol]
                            if date in prices.index and next_date in prices.index:
                                stock_return = (prices[next_date] / prices[date]) - 1
                                period_return += weight * stock_return
                                total_weight += abs(weight)
                    
                    if total_weight > 0:
                        factor_returns[date] = period_return
            
            return factor_returns
            
        except Exception as e:
            logger.error(f"Error calculating factor returns: {e}")
            return pd.Series(dtype=float)

class MultiFactorStrategy(BaseStrategy):
    """Multi-factor strategy implementation"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # Strategy-specific parameters
        params = config.parameters
        self.factors = [FactorType(f) for f in params.get('factors', ['value', 'momentum', 'quality'])]
        self.rebalance_frequency = params.get('rebalance_frequency', 21)  # Monthly
        self.long_pct = params.get('long_pct', 0.2)
        self.short_pct = params.get('short_pct', 0.2)
        self.max_position_size = params.get('max_position_size', 0.05)
        
        # Initialize analyzer
        analyzer_config = {
            'lookback_period': params.get('lookback_period', 252),
            'rebalance_frequency': self.rebalance_frequency,
            'min_observations': params.get('min_observations', 60)
        }
        self.analyzer = FactorAnalyzer(analyzer_config)
        
        # Factor models
        self.factor_models: Dict[FactorType, FactorModel] = {}
        
        # Current factor exposures
        self.current_exposures: Dict[str, Dict[FactorType, FactorExposure]] = {}
        
        # Last rebalance date
        self.last_rebalance: Optional[datetime] = None
        
        logger.info(f"MultiFactorStrategy initialized with factors: {[f.value for f in self.factors]}")
    
    def update_fundamental_data(self, symbol: str, data: Dict[str, float]) -> None:
        """Update fundamental data for factor calculation
        
        Args:
            symbol: Stock symbol
            data: Fundamental data dictionary
        """
        self.analyzer.update_fundamental_data(symbol, data)
    
    def generate_signals(self, market_data: Dict[str, MarketData]) -> List[Signal]:
        """Generate multi-factor signals
        
        Args:
            market_data: Dictionary of market data by symbol
            
        Returns:
            List of generated signals
        """
        signals = []
        
        try:
            # Check if rebalancing is needed
            current_time = datetime.now()
            if (self.last_rebalance is None or 
                (current_time - self.last_rebalance).days >= self.rebalance_frequency):
                
                # Update price data
                for symbol, data in market_data.items():
                    if symbol not in self.analyzer.price_data:
                        self.analyzer.price_data[symbol] = pd.Series(dtype=float)
                    self.analyzer.price_data[symbol][data.timestamp] = data.close
                
                # Generate factor-based signals
                factor_signals = self._generate_factor_signals(list(market_data.keys()))
                signals.extend(factor_signals)
                
                self.last_rebalance = current_time
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating multi-factor signals: {e}")
            return []
    
    def _generate_factor_signals(self, symbols: List[str]) -> List[Signal]:
        """Generate signals based on factor analysis
        
        Args:
            symbols: List of symbols to analyze
            
        Returns:
            List of factor-based signals
        """
        signals = []
        
        try:
            # Calculate factor exposures for each symbol
            for symbol in symbols:
                symbol_exposures = {}
                
                for factor_type in self.factors:
                    score = self.analyzer.calculate_factor_score(symbol, factor_type)
                    if score is not None:
                        # Calculate z-score and percentile (simplified)
                        # In practice, would use cross-sectional rankings
                        exposure = FactorExposure(
                            symbol=symbol,
                            factor_type=factor_type,
                            exposure=score,
                            z_score=score,  # Simplified
                            percentile=0.5  # Simplified
                        )
                        symbol_exposures[factor_type] = exposure
                
                self.current_exposures[symbol] = symbol_exposures
            
            # Generate signals based on factor combinations
            for symbol in symbols:
                if symbol not in self.current_exposures:
                    continue
                
                exposures = self.current_exposures[symbol]
                
                # Calculate composite factor score
                composite_score = self._calculate_composite_score(exposures)
                
                if abs(composite_score) > 0.5:  # Threshold for signal generation
                    signal = self._create_factor_signal(symbol, composite_score, exposures)
                    if signal:
                        signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating factor signals: {e}")
            return []
    
    def _calculate_composite_score(self, exposures: Dict[FactorType, FactorExposure]) -> float:
        """Calculate composite factor score
        
        Args:
            exposures: Dictionary of factor exposures
            
        Returns:
            Composite score
        """
        try:
            if not exposures:
                return 0.0
            
            # Equal weight combination (can be enhanced with factor timing)
            scores = [exp.exposure for exp in exposures.values()]
            
            if scores:
                return np.mean(scores)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating composite score: {e}")
            return 0.0
    
    def _create_factor_signal(self, symbol: str, composite_score: float, exposures: Dict[FactorType, FactorExposure]) -> Optional[Signal]:
        """Create signal from factor analysis
        
        Args:
            symbol: Stock symbol
            composite_score: Composite factor score
            exposures: Factor exposures
            
        Returns:
            Generated signal or None
        """
        try:
            # Determine signal direction
            signal_type = 'BUY' if composite_score > 0 else 'SELL'
            
            # Calculate signal strength and confidence
            strength = min(abs(composite_score), 1.0)
            confidence = strength  # Simplified
            
            # Calculate position size
            position_size = min(strength * self.max_position_size, self.max_position_size)
            
            # Estimate expected return (simplified)
            expected_return = composite_score * 0.1  # 10% per unit of score
            
            signal = Signal(
                timestamp=datetime.now(),
                symbol=symbol,
                signal_type=signal_type,
                strength=strength,
                confidence=confidence,
                expected_return=expected_return,
                risk_score=1 - confidence,
                position_size=position_size,
                metadata={
                    'strategy': 'multi_factor',
                    'composite_score': composite_score,
                    'factors': [f.value for f in self.factors],
                    'factor_exposures': {f.value: exp.exposure for f, exp in exposures.items()}
                }
            )
            
            logger.info(f"Generated factor signal: {signal_type} {symbol} score={composite_score:.3f}")
            return signal
            
        except Exception as e:
            logger.error(f"Error creating factor signal: {e}")
            return None

class FamaFrenchStrategy(MultiFactorStrategy):
    """Fama-French factor strategy"""
    
    def __init__(self, config: StrategyConfig):
        # Set Fama-French factors
        config.parameters['factors'] = ['market', 'size', 'value']
        super().__init__(config)
        
        # Fama-French specific parameters
        params = config.parameters
        self.model_type = params.get('model_type', '3_factor')  # 3_factor or 5_factor
        
        if self.model_type == '5_factor':
            self.factors.extend([FactorType.PROFITABILITY, FactorType.INVESTMENT])
        
        logger.info(f"FamaFrenchStrategy initialized: {self.model_type}")

class MomentumFactorStrategy(MultiFactorStrategy):
    """Momentum factor strategy"""
    
    def __init__(self, config: StrategyConfig):
        # Set momentum factors
        config.parameters['factors'] = ['momentum']
        super().__init__(config)
        
        # Momentum-specific parameters
        params = config.parameters
        self.momentum_periods = params.get('momentum_periods', [21, 63, 252])
        self.skip_period = params.get('skip_period', 21)  # Skip recent period
        
        logger.info("MomentumFactorStrategy initialized")

class QualityFactorStrategy(MultiFactorStrategy):
    """Quality factor strategy"""
    
    def __init__(self, config: StrategyConfig):
        # Set quality factors
        config.parameters['factors'] = ['quality', 'profitability']
        super().__init__(config)
        
        # Quality-specific parameters
        params = config.parameters
        self.quality_metrics = params.get('quality_metrics', ['roe', 'roa', 'debt_to_equity'])
        
        logger.info("QualityFactorStrategy initialized")

# Utility functions
def calculate_factor_loadings(returns: pd.Series, factor_returns: Dict[str, pd.Series]) -> Dict[str, float]:
    """Calculate factor loadings using regression
    
    Args:
        returns: Asset return series
        factor_returns: Dictionary of factor return series
        
    Returns:
        Dictionary of factor loadings
    """
    try:
        from sklearn.linear_model import LinearRegression
        
        # Align data
        common_dates = returns.index
        for factor_name, factor_rets in factor_returns.items():
            common_dates = common_dates.intersection(factor_rets.index)
        
        if len(common_dates) < 30:  # Need minimum observations
            return {}
        
        # Prepare data
        y = returns.loc[common_dates].values
        X = np.column_stack([factor_returns[name].loc[common_dates].values 
                           for name in factor_returns.keys()])
        
        # Fit regression
        model = LinearRegression()
        model.fit(X, y)
        
        # Return loadings
        loadings = {}
        for i, factor_name in enumerate(factor_returns.keys()):
            loadings[factor_name] = model.coef_[i]
        
        return loadings
        
    except Exception as e:
        logger.error(f"Error calculating factor loadings: {e}")
        return {}

def construct_factor_portfolio(factor_scores: Dict[str, float], long_pct: float = 0.2, short_pct: float = 0.2) -> Dict[str, float]:
    """Construct long-short factor portfolio
    
    Args:
        factor_scores: Dictionary of symbol factor scores
        long_pct: Percentage to go long
        short_pct: Percentage to go short
        
    Returns:
        Dictionary of portfolio weights
    """
    try:
        if len(factor_scores) < 10:
            return {}
        
        # Sort by factor score
        sorted_symbols = sorted(factor_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Select positions
        n_long = max(1, int(len(sorted_symbols) * long_pct))
        n_short = max(1, int(len(sorted_symbols) * short_pct))
        
        portfolio_weights = {}
        
        # Long positions (top scores)
        for i in range(n_long):
            symbol = sorted_symbols[i][0]
            portfolio_weights[symbol] = 0.5 / n_long
        
        # Short positions (bottom scores)
        for i in range(n_short):
            symbol = sorted_symbols[-(i+1)][0]
            portfolio_weights[symbol] = -0.5 / n_short
        
        return portfolio_weights
        
    except Exception as e:
        logger.error(f"Error constructing factor portfolio: {e}")
        return {}

def calculate_factor_returns(portfolio_weights: Dict[str, float], returns: Dict[str, pd.Series]) -> pd.Series:
    """Calculate factor portfolio returns
    
    Args:
        portfolio_weights: Portfolio weights
        returns: Dictionary of asset returns
        
    Returns:
        Factor return series
    """
    try:
        if not portfolio_weights or not returns:
            return pd.Series(dtype=float)
        
        # Find common dates
        common_dates = None
        for symbol in portfolio_weights.keys():
            if symbol in returns:
                if common_dates is None:
                    common_dates = returns[symbol].index
                else:
                    common_dates = common_dates.intersection(returns[symbol].index)
        
        if common_dates is None or len(common_dates) == 0:
            return pd.Series(dtype=float)
        
        # Calculate portfolio returns
        factor_returns = pd.Series(0.0, index=common_dates)
        
        for symbol, weight in portfolio_weights.items():
            if symbol in returns:
                asset_returns = returns[symbol].loc[common_dates]
                factor_returns += weight * asset_returns
        
        return factor_returns
        
    except Exception as e:
        logger.error(f"Error calculating factor returns: {e}")
        return pd.Series(dtype=float)