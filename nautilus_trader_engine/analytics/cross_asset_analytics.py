"""
Cross-Asset Analytics System
Implements cross-asset correlation analysis, arbitrage detection, spread trading, and risk attribution
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum
import warnings

# Suppress numpy warnings
warnings.filterwarnings('ignore', category=RuntimeWarning)

try:
    from scipy import stats
    from scipy.optimize import minimize
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    stats = None
    minimize = None


class ArbitrageType(Enum):
    """Types of arbitrage opportunities"""
    STATISTICAL = "statistical"
    TRIANGULAR = "triangular"
    CALENDAR = "calendar"
    CROSS_EXCHANGE = "cross_exchange"
    CURRENCY = "currency"


class SpreadType(Enum):
    """Types of spread trading strategies"""
    PAIRS_TRADING = "pairs_trading"
    CALENDAR_SPREAD = "calendar_spread"
    INTER_COMMODITY = "inter_commodity"
    CURRENCY_SPREAD = "currency_spread"
    YIELD_CURVE = "yield_curve"


@dataclass
class CorrelationResult:
    """Correlation analysis result"""
    asset1: str
    asset2: str
    correlation: float
    p_value: float
    confidence_interval: Tuple[float, float]
    rolling_correlation: List[float] = field(default_factory=list)
    correlation_stability: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class ArbitrageOpportunity:
    """Arbitrage opportunity detection result"""
    opportunity_id: str
    arbitrage_type: ArbitrageType
    assets_involved: List[str]
    expected_profit: float
    confidence_score: float
    risk_score: float
    execution_complexity: str
    time_horizon: str
    market_conditions: Dict[str, Any]
    detected_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None


@dataclass
class SpreadOpportunity:
    """Spread trading opportunity"""
    spread_id: str
    spread_type: SpreadType
    long_asset: str
    short_asset: str
    current_spread: float
    historical_mean: float
    z_score: float
    entry_signal: bool
    exit_signal: bool
    target_profit: float
    stop_loss: float
    confidence: float
    detected_at: datetime = field(default_factory=datetime.now)


@dataclass
class RiskAttribution:
    """Cross-asset risk attribution result"""
    portfolio_var: float
    component_vars: Dict[str, float]
    marginal_vars: Dict[str, float]
    component_contributions: Dict[str, float]
    diversification_ratio: float
    concentration_risk: float
    correlation_risk: float
    attribution_date: datetime = field(default_factory=datetime.now)


class CrossAssetCorrelationAnalyzer:
    """Analyzes correlations between different asset classes"""
    
    def __init__(self, lookback_periods: List[int] = None):
        self.logger = logging.getLogger(__name__)
        self.lookback_periods = lookback_periods or [30, 60, 120, 252]
        self.correlation_cache = {}
        
    async def calculate_correlation_matrix(self, 
                                         price_data: Dict[str, np.ndarray],
                                         method: str = "pearson") -> pd.DataFrame:
        """Calculate correlation matrix for multiple assets"""
        try:
            # Convert to DataFrame for easier handling
            df = pd.DataFrame(price_data)
            
            # Calculate returns
            returns_df = df.pct_change().dropna()
            
            if method == "pearson":
                correlation_matrix = returns_df.corr()
            elif method == "spearman":
                correlation_matrix = returns_df.corr(method='spearman')
            elif method == "kendall":
                correlation_matrix = returns_df.corr(method='kendall')
            else:
                raise ValueError(f"Unsupported correlation method: {method}")
            
            return correlation_matrix
            
        except Exception as e:
            self.logger.error(f"Failed to calculate correlation matrix: {e}")
            return pd.DataFrame()
    
    async def analyze_pairwise_correlation(self, 
                                         asset1_prices: np.ndarray,
                                         asset2_prices: np.ndarray,
                                         asset1_name: str,
                                         asset2_name: str) -> CorrelationResult:
        """Analyze correlation between two assets"""
        try:
            # Calculate returns
            returns1 = np.diff(asset1_prices) / asset1_prices[:-1]
            returns2 = np.diff(asset2_prices) / asset2_prices[:-1]
            
            # Remove any NaN or infinite values
            valid_mask = np.isfinite(returns1) & np.isfinite(returns2)
            returns1 = returns1[valid_mask]
            returns2 = returns2[valid_mask]
            
            if len(returns1) < 10:  # Need minimum data points
                raise ValueError("Insufficient data for correlation analysis")
            
            # Calculate correlation and p-value
            correlation, p_value = stats.pearsonr(returns1, returns2) if SCIPY_AVAILABLE else (np.corrcoef(returns1, returns2)[0, 1], 0.0)
            
            # Calculate confidence interval (if scipy available)
            if SCIPY_AVAILABLE:
                n = len(returns1)
                z = np.arctanh(correlation)
                se = 1 / np.sqrt(n - 3)
                ci_lower = np.tanh(z - 1.96 * se)
                ci_upper = np.tanh(z + 1.96 * se)
                confidence_interval = (ci_lower, ci_upper)
            else:
                confidence_interval = (correlation - 0.1, correlation + 0.1)  # Rough estimate
            
            # Calculate rolling correlation for stability analysis
            rolling_correlations = []
            window_size = min(30, len(returns1) // 4)
            
            if window_size >= 10:
                for i in range(window_size, len(returns1)):
                    window_corr = np.corrcoef(
                        returns1[i-window_size:i],
                        returns2[i-window_size:i]
                    )[0, 1]
                    if np.isfinite(window_corr):
                        rolling_correlations.append(window_corr)
            
            # Calculate correlation stability (lower std = more stable)
            correlation_stability = np.std(rolling_correlations) if rolling_correlations else 1.0
            
            return CorrelationResult(
                asset1=asset1_name,
                asset2=asset2_name,
                correlation=correlation,
                p_value=p_value,
                confidence_interval=confidence_interval,
                rolling_correlation=rolling_correlations,
                correlation_stability=correlation_stability
            )
            
        except Exception as e:
            self.logger.error(f"Failed to analyze pairwise correlation: {e}")
            return CorrelationResult(
                asset1=asset1_name,
                asset2=asset2_name,
                correlation=0.0,
                p_value=1.0,
                confidence_interval=(0.0, 0.0)
            )
    
    async def detect_correlation_breakdowns(self,
                                          correlation_history: List[float],
                                          threshold: float = 0.3) -> List[int]:
        """Detect periods where correlation breaks down significantly"""
        try:
            breakdowns = []
            
            if len(correlation_history) < 20:
                return breakdowns
            
            # Calculate rolling mean and std
            window = min(20, len(correlation_history) // 4)
            rolling_mean = pd.Series(correlation_history).rolling(window).mean()
            rolling_std = pd.Series(correlation_history).rolling(window).std()
            
            # Detect breakdowns (correlation deviates significantly from mean)
            for i in range(window, len(correlation_history)):
                current_corr = correlation_history[i]
                expected_corr = rolling_mean.iloc[i]
                volatility = rolling_std.iloc[i]
                
                if abs(current_corr - expected_corr) > threshold + 2 * volatility:
                    breakdowns.append(i)
            
            return breakdowns
            
        except Exception as e:
            self.logger.error(f"Failed to detect correlation breakdowns: {e}")
            return []


class ArbitrageDetector:
    """Detects arbitrage opportunities across different assets and markets"""
    
    def __init__(self, min_profit_threshold: float = 0.001):
        self.logger = logging.getLogger(__name__)
        self.min_profit_threshold = min_profit_threshold
        self.opportunity_history = []
        
    async def detect_statistical_arbitrage(self,
                                         price_data: Dict[str, np.ndarray],
                                         lookback_window: int = 60) -> List[ArbitrageOpportunity]:
        """Detect statistical arbitrage opportunities using mean reversion"""
        opportunities = []
        
        try:
            assets = list(price_data.keys())
            
            # Analyze all pairs
            for i in range(len(assets)):
                for j in range(i + 1, len(assets)):
                    asset1, asset2 = assets[i], assets[j]
                    prices1, prices2 = price_data[asset1], price_data[asset2]
                    
                    # Ensure we have enough data
                    min_length = min(len(prices1), len(prices2))
                    if min_length < lookback_window:
                        continue
                    
                    # Align data
                    prices1 = prices1[-min_length:]
                    prices2 = prices2[-min_length:]
                    
                    # Calculate price ratio
                    ratio = prices1 / prices2
                    
                    # Calculate rolling statistics
                    ratio_mean = np.mean(ratio[-lookback_window:])
                    ratio_std = np.std(ratio[-lookback_window:])
                    
                    if ratio_std == 0:
                        continue
                    
                    # Current z-score
                    current_ratio = ratio[-1]
                    z_score = (current_ratio - ratio_mean) / ratio_std
                    
                    # Check for arbitrage opportunity (z-score > 2 or < -2)
                    if abs(z_score) > 2.0:
                        expected_profit = abs(z_score) * ratio_std / current_ratio
                        
                        if expected_profit > self.min_profit_threshold:
                            opportunity = ArbitrageOpportunity(
                                opportunity_id=f"stat_arb_{asset1}_{asset2}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                arbitrage_type=ArbitrageType.STATISTICAL,
                                assets_involved=[asset1, asset2],
                                expected_profit=expected_profit,
                                confidence_score=min(abs(z_score) / 3.0, 1.0),
                                risk_score=ratio_std / ratio_mean,
                                execution_complexity="Medium",
                                time_horizon="Short-term",
                                market_conditions={
                                    "z_score": z_score,
                                    "ratio_mean": ratio_mean,
                                    "ratio_std": ratio_std,
                                    "current_ratio": current_ratio
                                }
                            )
                            opportunities.append(opportunity)
            
            return opportunities
            
        except Exception as e:
            self.logger.error(f"Failed to detect statistical arbitrage: {e}")
            return []
    
    async def detect_triangular_arbitrage(self,
                                        currency_pairs: Dict[str, float]) -> List[ArbitrageOpportunity]:
        """Detect triangular arbitrage opportunities in currency markets"""
        opportunities = []
        
        try:
            # Extract unique currencies
            currencies = set()
            for pair in currency_pairs.keys():
                if len(pair) == 6:  # Assuming format like EURUSD
                    currencies.add(pair[:3])
                    currencies.add(pair[3:])
            
            currencies = list(currencies)
            
            # Check all possible triangles
            for i in range(len(currencies)):
                for j in range(i + 1, len(currencies)):
                    for k in range(j + 1, len(currencies)):
                        base, quote1, quote2 = currencies[i], currencies[j], currencies[k]
                        
                        # Try to find the three pairs needed for triangular arbitrage
                        pair1 = f"{base}{quote1}"
                        pair2 = f"{quote1}{quote2}"
                        pair3 = f"{base}{quote2}"
                        
                        # Check if all pairs exist (try both directions)
                        rate1 = currency_pairs.get(pair1) or (1 / currency_pairs.get(f"{quote1}{base}", float('inf')))
                        rate2 = currency_pairs.get(pair2) or (1 / currency_pairs.get(f"{quote2}{quote1}", float('inf')))
                        rate3 = currency_pairs.get(pair3) or (1 / currency_pairs.get(f"{quote2}{base}", float('inf')))
                        
                        if any(rate == float('inf') for rate in [rate1, rate2, rate3]):
                            continue
                        
                        # Calculate implied rate and arbitrage profit
                        implied_rate = rate1 * rate2
                        actual_rate = rate3
                        
                        profit_pct = (implied_rate - actual_rate) / actual_rate
                        
                        if abs(profit_pct) > self.min_profit_threshold:
                            opportunity = ArbitrageOpportunity(
                                opportunity_id=f"tri_arb_{base}_{quote1}_{quote2}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                arbitrage_type=ArbitrageType.TRIANGULAR,
                                assets_involved=[pair1, pair2, pair3],
                                expected_profit=abs(profit_pct),
                                confidence_score=0.9,  # High confidence for triangular arbitrage
                                risk_score=0.1,  # Low risk if executed quickly
                                execution_complexity="High",
                                time_horizon="Immediate",
                                market_conditions={
                                    "implied_rate": implied_rate,
                                    "actual_rate": actual_rate,
                                    "profit_percentage": profit_pct,
                                    "rates": {pair1: rate1, pair2: rate2, pair3: rate3}
                                }
                            )
                            opportunities.append(opportunity)
            
            return opportunities
            
        except Exception as e:
            self.logger.error(f"Failed to detect triangular arbitrage: {e}")
            return []
    
    async def detect_calendar_arbitrage(self,
                                      futures_data: Dict[str, Dict[str, float]]) -> List[ArbitrageOpportunity]:
        """Detect calendar arbitrage opportunities in futures markets"""
        opportunities = []
        
        try:
            # Group by underlying asset
            by_underlying = defaultdict(dict)
            for contract, price in futures_data.items():
                # Assuming contract format like "ES_202403" (underlying_expiry)
                if '_' in contract:
                    underlying, expiry = contract.split('_', 1)
                    by_underlying[underlying][expiry] = price
            
            # Analyze each underlying
            for underlying, contracts in by_underlying.items():
                if len(contracts) < 2:
                    continue
                
                # Sort by expiry
                sorted_contracts = sorted(contracts.items())
                
                # Check consecutive contracts for calendar spread opportunities
                for i in range(len(sorted_contracts) - 1):
                    near_expiry, near_price = sorted_contracts[i]
                    far_expiry, far_price = sorted_contracts[i + 1]
                    
                    # Calculate calendar spread (far - near)
                    spread = far_price - near_price
                    
                    # Simple heuristic: if spread is negative (contango broken), potential opportunity
                    if spread < -self.min_profit_threshold * near_price:
                        opportunity = ArbitrageOpportunity(
                            opportunity_id=f"cal_arb_{underlying}_{near_expiry}_{far_expiry}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            arbitrage_type=ArbitrageType.CALENDAR,
                            assets_involved=[f"{underlying}_{near_expiry}", f"{underlying}_{far_expiry}"],
                            expected_profit=abs(spread) / near_price,
                            confidence_score=0.7,
                            risk_score=0.3,
                            execution_complexity="Medium",
                            time_horizon="Medium-term",
                            market_conditions={
                                "near_price": near_price,
                                "far_price": far_price,
                                "spread": spread,
                                "underlying": underlying
                            }
                        )
                        opportunities.append(opportunity)
            
            return opportunities
            
        except Exception as e:
            self.logger.error(f"Failed to detect calendar arbitrage: {e}")
            return []


class SpreadTradingAnalyzer:
    """Analyzes spread trading opportunities across different assets"""
    
    def __init__(self, z_score_threshold: float = 2.0):
        self.logger = logging.getLogger(__name__)
        self.z_score_threshold = z_score_threshold
        self.spread_history = defaultdict(list)
        
    async def analyze_pairs_trading(self,
                                  asset1_prices: np.ndarray,
                                  asset2_prices: np.ndarray,
                                  asset1_name: str,
                                  asset2_name: str,
                                  lookback_window: int = 60) -> Optional[SpreadOpportunity]:
        """Analyze pairs trading opportunity between two assets"""
        try:
            # Ensure we have enough data
            min_length = min(len(asset1_prices), len(asset2_prices))
            if min_length < lookback_window:
                return None
            
            # Align data
            prices1 = asset1_prices[-min_length:]
            prices2 = asset2_prices[-min_length:]
            
            # Calculate price ratio (spread)
            spread = prices1 / prices2
            
            # Calculate rolling statistics
            spread_window = spread[-lookback_window:]
            spread_mean = np.mean(spread_window)
            spread_std = np.std(spread_window)
            
            if spread_std == 0:
                return None
            
            # Current spread and z-score
            current_spread = spread[-1]
            z_score = (current_spread - spread_mean) / spread_std
            
            # Determine entry/exit signals
            entry_signal = abs(z_score) > self.z_score_threshold
            exit_signal = abs(z_score) < 0.5  # Exit when spread normalizes
            
            # Calculate target profit and stop loss
            target_profit = abs(z_score) * spread_std / current_spread
            stop_loss = 2 * spread_std / current_spread  # 2 standard deviations
            
            # Determine long/short assets based on z-score
            if z_score > 0:
                long_asset, short_asset = asset2_name, asset1_name  # Spread too high, short it
            else:
                long_asset, short_asset = asset1_name, asset2_name  # Spread too low, long it
            
            opportunity = SpreadOpportunity(
                spread_id=f"pairs_{asset1_name}_{asset2_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                spread_type=SpreadType.PAIRS_TRADING,
                long_asset=long_asset,
                short_asset=short_asset,
                current_spread=current_spread,
                historical_mean=spread_mean,
                z_score=z_score,
                entry_signal=entry_signal,
                exit_signal=exit_signal,
                target_profit=target_profit,
                stop_loss=stop_loss,
                confidence=min(abs(z_score) / 3.0, 1.0)
            )
            
            return opportunity
            
        except Exception as e:
            self.logger.error(f"Failed to analyze pairs trading: {e}")
            return None
    
    async def analyze_calendar_spread(self,
                                    near_contract_prices: np.ndarray,
                                    far_contract_prices: np.ndarray,
                                    near_contract_name: str,
                                    far_contract_name: str,
                                    lookback_window: int = 30) -> Optional[SpreadOpportunity]:
        """Analyze calendar spread opportunity between near and far contracts"""
        try:
            # Ensure we have enough data
            min_length = min(len(near_contract_prices), len(far_contract_prices))
            if min_length < lookback_window:
                return None
            
            # Align data
            near_prices = near_contract_prices[-min_length:]
            far_prices = far_contract_prices[-min_length:]
            
            # Calculate calendar spread (far - near)
            spread = far_prices - near_prices
            
            # Calculate rolling statistics
            spread_window = spread[-lookback_window:]
            spread_mean = np.mean(spread_window)
            spread_std = np.std(spread_window)
            
            if spread_std == 0:
                return None
            
            # Current spread and z-score
            current_spread = spread[-1]
            z_score = (current_spread - spread_mean) / spread_std
            
            # Determine entry/exit signals
            entry_signal = abs(z_score) > self.z_score_threshold
            exit_signal = abs(z_score) < 0.5
            
            # Calculate target profit and stop loss
            target_profit = abs(z_score) * spread_std / abs(current_spread) if current_spread != 0 else 0
            stop_loss = 2 * spread_std / abs(current_spread) if current_spread != 0 else 0.1
            
            # Determine long/short based on z-score
            if z_score > 0:
                long_asset, short_asset = near_contract_name, far_contract_name  # Spread too wide
            else:
                long_asset, short_asset = far_contract_name, near_contract_name  # Spread too narrow
            
            opportunity = SpreadOpportunity(
                spread_id=f"calendar_{near_contract_name}_{far_contract_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                spread_type=SpreadType.CALENDAR_SPREAD,
                long_asset=long_asset,
                short_asset=short_asset,
                current_spread=current_spread,
                historical_mean=spread_mean,
                z_score=z_score,
                entry_signal=entry_signal,
                exit_signal=exit_signal,
                target_profit=target_profit,
                stop_loss=stop_loss,
                confidence=min(abs(z_score) / 3.0, 1.0)
            )
            
            return opportunity
            
        except Exception as e:
            self.logger.error(f"Failed to analyze calendar spread: {e}")
            return None
    
    async def analyze_yield_curve_spread(self,
                                       short_term_rates: np.ndarray,
                                       long_term_rates: np.ndarray,
                                       short_term_name: str,
                                       long_term_name: str,
                                       lookback_window: int = 60) -> Optional[SpreadOpportunity]:
        """Analyze yield curve spread trading opportunities"""
        try:
            # Ensure we have enough data
            min_length = min(len(short_term_rates), len(long_term_rates))
            if min_length < lookback_window:
                return None
            
            # Align data
            short_rates = short_term_rates[-min_length:]
            long_rates = long_term_rates[-min_length:]
            
            # Calculate yield spread (long - short)
            spread = long_rates - short_rates
            
            # Calculate rolling statistics
            spread_window = spread[-lookback_window:]
            spread_mean = np.mean(spread_window)
            spread_std = np.std(spread_window)
            
            if spread_std == 0:
                return None
            
            # Current spread and z-score
            current_spread = spread[-1]
            z_score = (current_spread - spread_mean) / spread_std
            
            # Determine entry/exit signals
            entry_signal = abs(z_score) > self.z_score_threshold
            exit_signal = abs(z_score) < 0.5
            
            # Calculate target profit and stop loss (in basis points)
            target_profit = abs(z_score) * spread_std * 10000  # Convert to basis points
            stop_loss = 2 * spread_std * 10000
            
            # Determine strategy based on z-score
            if z_score > 0:
                # Spread too wide - expect flattening
                long_asset, short_asset = short_term_name, long_term_name
            else:
                # Spread too narrow - expect steepening
                long_asset, short_asset = long_term_name, short_term_name
            
            opportunity = SpreadOpportunity(
                spread_id=f"yield_curve_{short_term_name}_{long_term_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                spread_type=SpreadType.YIELD_CURVE,
                long_asset=long_asset,
                short_asset=short_asset,
                current_spread=current_spread,
                historical_mean=spread_mean,
                z_score=z_score,
                entry_signal=entry_signal,
                exit_signal=exit_signal,
                target_profit=target_profit,
                stop_loss=stop_loss,
                confidence=min(abs(z_score) / 3.0, 1.0)
            )
            
            return opportunity
            
        except Exception as e:
            self.logger.error(f"Failed to analyze yield curve spread: {e}")
            return None


class CrossAssetRiskAttributor:
    """Performs cross-asset risk attribution analysis"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    async def calculate_portfolio_risk_attribution(self,
                                                 returns_data: Dict[str, np.ndarray],
                                                 weights: Dict[str, float],
                                                 confidence_level: float = 0.05) -> RiskAttribution:
        """Calculate comprehensive risk attribution for a multi-asset portfolio"""
        try:
            # Align all return series
            assets = list(returns_data.keys())
            min_length = min(len(returns_data[asset]) for asset in assets)
            
            # Create returns matrix
            returns_matrix = np.array([returns_data[asset][-min_length:] for asset in assets]).T
            weights_array = np.array([weights.get(asset, 0.0) for asset in assets])
            
            # Calculate portfolio returns
            portfolio_returns = returns_matrix @ weights_array
            
            # Calculate portfolio VaR
            portfolio_var = np.percentile(portfolio_returns, confidence_level * 100)
            
            # Calculate covariance matrix
            cov_matrix = np.cov(returns_matrix.T)
            
            # Calculate component VaRs
            component_vars = {}
            marginal_vars = {}
            component_contributions = {}
            
            for i, asset in enumerate(assets):
                # Component VaR (individual asset VaR)
                asset_returns = returns_matrix[:, i]
                component_vars[asset] = np.percentile(asset_returns, confidence_level * 100)
                
                # Marginal VaR (contribution to portfolio VaR)
                # Approximate using portfolio sensitivity
                portfolio_vol = np.std(portfolio_returns)
                asset_portfolio_cov = np.cov(asset_returns, portfolio_returns)[0, 1]
                marginal_vars[asset] = asset_portfolio_cov / portfolio_vol if portfolio_vol > 0 else 0
                
                # Component contribution to portfolio VaR
                component_contributions[asset] = weights_array[i] * marginal_vars[asset]
            
            # Calculate diversification metrics
            individual_var_sum = sum(abs(weights[asset] * component_vars[asset]) for asset in assets)
            diversification_ratio = abs(portfolio_var) / individual_var_sum if individual_var_sum > 0 else 1.0
            
            # Calculate concentration risk (Herfindahl index of weights)
            concentration_risk = sum(weights[asset] ** 2 for asset in assets)
            
            # Calculate correlation risk (average absolute correlation)
            correlations = []
            for i in range(len(assets)):
                for j in range(i + 1, len(assets)):
                    corr = np.corrcoef(returns_matrix[:, i], returns_matrix[:, j])[0, 1]
                    if np.isfinite(corr):
                        correlations.append(abs(corr))
            
            correlation_risk = np.mean(correlations) if correlations else 0.0
            
            return RiskAttribution(
                portfolio_var=portfolio_var,
                component_vars=component_vars,
                marginal_vars=marginal_vars,
                component_contributions=component_contributions,
                diversification_ratio=diversification_ratio,
                concentration_risk=concentration_risk,
                correlation_risk=correlation_risk
            )
            
        except Exception as e:
            self.logger.error(f"Failed to calculate risk attribution: {e}")
            return RiskAttribution(
                portfolio_var=0.0,
                component_vars={},
                marginal_vars={},
                component_contributions={},
                diversification_ratio=1.0,
                concentration_risk=1.0,
                correlation_risk=0.0
            )
    
    async def analyze_correlation_risk(self,
                                     returns_data: Dict[str, np.ndarray],
                                     stress_scenarios: List[str] = None) -> Dict[str, Any]:
        """Analyze correlation risk under different market conditions"""
        try:
            stress_scenarios = stress_scenarios or ["normal", "crisis", "recovery"]
            
            assets = list(returns_data.keys())
            min_length = min(len(returns_data[asset]) for asset in assets)
            
            # Create returns matrix
            returns_matrix = np.array([returns_data[asset][-min_length:] for asset in assets]).T
            
            correlation_analysis = {}
            
            for scenario in stress_scenarios:
                if scenario == "normal":
                    # Use all data
                    scenario_returns = returns_matrix
                elif scenario == "crisis":
                    # Use periods of high volatility (bottom 10% of returns)
                    portfolio_returns = np.mean(returns_matrix, axis=1)
                    crisis_threshold = np.percentile(portfolio_returns, 10)
                    crisis_mask = portfolio_returns <= crisis_threshold
                    scenario_returns = returns_matrix[crisis_mask]
                elif scenario == "recovery":
                    # Use periods of high positive returns (top 10%)
                    portfolio_returns = np.mean(returns_matrix, axis=1)
                    recovery_threshold = np.percentile(portfolio_returns, 90)
                    recovery_mask = portfolio_returns >= recovery_threshold
                    scenario_returns = returns_matrix[recovery_mask]
                else:
                    continue
                
                if len(scenario_returns) < 10:  # Need minimum observations
                    continue
                
                # Calculate correlation matrix for this scenario
                scenario_corr = np.corrcoef(scenario_returns.T)
                
                # Extract correlation statistics
                correlations = []
                for i in range(len(assets)):
                    for j in range(i + 1, len(assets)):
                        corr = scenario_corr[i, j]
                        if np.isfinite(corr):
                            correlations.append(corr)
                
                correlation_analysis[scenario] = {
                    "mean_correlation": np.mean(correlations) if correlations else 0.0,
                    "max_correlation": np.max(correlations) if correlations else 0.0,
                    "min_correlation": np.min(correlations) if correlations else 0.0,
                    "correlation_std": np.std(correlations) if correlations else 0.0,
                    "correlation_matrix": scenario_corr.tolist(),
                    "asset_names": assets
                }
            
            return correlation_analysis
            
        except Exception as e:
            self.logger.error(f"Failed to analyze correlation risk: {e}")
            return {}


class CrossAssetAnalyticsEngine:
    """Main engine that orchestrates all cross-asset analytics"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.correlation_analyzer = CrossAssetCorrelationAnalyzer()
        self.arbitrage_detector = ArbitrageDetector()
        self.spread_analyzer = SpreadTradingAnalyzer()
        self.risk_attributor = CrossAssetRiskAttributor()
        
        # Results cache
        self.results_cache = {
            "correlations": {},
            "arbitrage_opportunities": [],
            "spread_opportunities": [],
            "risk_attributions": {}
        }
    
    async def run_comprehensive_analysis(self,
                                       market_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Run comprehensive cross-asset analysis"""
        try:
            results = {
                "analysis_timestamp": datetime.now(),
                "correlations": {},
                "arbitrage_opportunities": [],
                "spread_opportunities": [],
                "risk_attribution": {},
                "summary": {}
            }
            
            # Extract price data
            price_data = {}
            for asset, data in market_data.items():
                if "prices" in data and len(data["prices"]) > 0:
                    price_data[asset] = np.array(data["prices"])
            
            if len(price_data) < 2:
                self.logger.warning("Insufficient price data for cross-asset analysis")
                return results
            
            # 1. Correlation Analysis
            self.logger.info("Running correlation analysis...")
            correlation_matrix = await self.correlation_analyzer.calculate_correlation_matrix(price_data)
            results["correlations"]["matrix"] = correlation_matrix.to_dict() if not correlation_matrix.empty else {}
            
            # Pairwise correlation analysis
            assets = list(price_data.keys())
            pairwise_correlations = []
            
            for i in range(len(assets)):
                for j in range(i + 1, len(assets)):
                    asset1, asset2 = assets[i], assets[j]
                    corr_result = await self.correlation_analyzer.analyze_pairwise_correlation(
                        price_data[asset1], price_data[asset2], asset1, asset2
                    )
                    pairwise_correlations.append({
                        "asset1": corr_result.asset1,
                        "asset2": corr_result.asset2,
                        "correlation": corr_result.correlation,
                        "p_value": corr_result.p_value,
                        "stability": corr_result.correlation_stability
                    })
            
            results["correlations"]["pairwise"] = pairwise_correlations
            
            # 2. Arbitrage Detection
            self.logger.info("Detecting arbitrage opportunities...")
            
            # Statistical arbitrage
            stat_arb_opportunities = await self.arbitrage_detector.detect_statistical_arbitrage(price_data)
            results["arbitrage_opportunities"].extend([
                {
                    "id": opp.opportunity_id,
                    "type": opp.arbitrage_type.value,
                    "assets": opp.assets_involved,
                    "expected_profit": opp.expected_profit,
                    "confidence": opp.confidence_score,
                    "risk": opp.risk_score
                } for opp in stat_arb_opportunities
            ])
            
            # 3. Spread Trading Analysis
            self.logger.info("Analyzing spread trading opportunities...")
            
            # Pairs trading analysis
            for i in range(len(assets)):
                for j in range(i + 1, len(assets)):
                    asset1, asset2 = assets[i], assets[j]
                    spread_opp = await self.spread_analyzer.analyze_pairs_trading(
                        price_data[asset1], price_data[asset2], asset1, asset2
                    )
                    
                    if spread_opp and spread_opp.entry_signal:
                        results["spread_opportunities"].append({
                            "id": spread_opp.spread_id,
                            "type": spread_opp.spread_type.value,
                            "long_asset": spread_opp.long_asset,
                            "short_asset": spread_opp.short_asset,
                            "z_score": spread_opp.z_score,
                            "target_profit": spread_opp.target_profit,
                            "confidence": spread_opp.confidence
                        })
            
            # 4. Risk Attribution (if weights provided)
            if all("weight" in market_data[asset] for asset in assets):
                self.logger.info("Calculating risk attribution...")
                
                # Extract returns data
                returns_data = {}
                weights = {}
                
                for asset in assets:
                    prices = price_data[asset]
                    if len(prices) > 1:
                        returns_data[asset] = np.diff(prices) / prices[:-1]
                        weights[asset] = market_data[asset].get("weight", 1.0 / len(assets))
                
                risk_attr = await self.risk_attributor.calculate_portfolio_risk_attribution(
                    returns_data, weights
                )
                
                results["risk_attribution"] = {
                    "portfolio_var": risk_attr.portfolio_var,
                    "component_contributions": risk_attr.component_contributions,
                    "diversification_ratio": risk_attr.diversification_ratio,
                    "concentration_risk": risk_attr.concentration_risk,
                    "correlation_risk": risk_attr.correlation_risk
                }
            
            # 5. Generate Summary
            results["summary"] = {
                "total_assets_analyzed": len(assets),
                "correlation_pairs": len(pairwise_correlations),
                "arbitrage_opportunities": len(results["arbitrage_opportunities"]),
                "spread_opportunities": len(results["spread_opportunities"]),
                "high_correlation_pairs": len([c for c in pairwise_correlations if abs(c["correlation"]) > 0.7]),
                "analysis_quality": "Good" if len(assets) >= 5 else "Limited"
            }
            
            # Cache results
            self.results_cache.update(results)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to run comprehensive analysis: {e}")
            return {"error": str(e), "analysis_timestamp": datetime.now()}


# Example usage and testing
async def example_usage():
    """Example usage of the Cross-Asset Analytics Engine"""
    
    # Initialize engine
    engine = CrossAssetAnalyticsEngine()
    
    # Generate sample market data
    np.random.seed(42)  # For reproducible results
    
    market_data = {
        "AAPL": {
            "prices": np.cumsum(np.random.normal(0.001, 0.02, 100)) + 150,
            "weight": 0.3
        },
        "GOOGL": {
            "prices": np.cumsum(np.random.normal(0.0008, 0.025, 100)) + 2800,
            "weight": 0.2
        },
        "SPY": {
            "prices": np.cumsum(np.random.normal(0.0005, 0.015, 100)) + 450,
            "weight": 0.3
        },
        "TLT": {
            "prices": np.cumsum(np.random.normal(-0.0002, 0.01, 100)) + 120,
            "weight": 0.2
        }
    }
    
    # Run comprehensive analysis
    print("Running comprehensive cross-asset analysis...")
    results = await engine.run_comprehensive_analysis(market_data)
    
    # Display results
    print(f"\n=== Cross-Asset Analysis Results ===")
    print(f"Analysis completed at: {results['analysis_timestamp']}")
    print(f"Assets analyzed: {results['summary']['total_assets_analyzed']}")
    print(f"Correlation pairs: {results['summary']['correlation_pairs']}")
    print(f"Arbitrage opportunities: {results['summary']['arbitrage_opportunities']}")
    print(f"Spread opportunities: {results['summary']['spread_opportunities']}")
    print(f"High correlation pairs: {results['summary']['high_correlation_pairs']}")
    
    # Show some correlations
    if results["correlations"]["pairwise"]:
        print(f"\n=== Top Correlations ===")
        sorted_corrs = sorted(results["correlations"]["pairwise"], 
                            key=lambda x: abs(x["correlation"]), reverse=True)
        for corr in sorted_corrs[:3]:
            print(f"{corr['asset1']} - {corr['asset2']}: {corr['correlation']:.3f}")
    
    # Show arbitrage opportunities
    if results["arbitrage_opportunities"]:
        print(f"\n=== Arbitrage Opportunities ===")
        for opp in results["arbitrage_opportunities"][:3]:
            print(f"{opp['type']}: {opp['assets']} - Profit: {opp['expected_profit']:.4f}")
    
    # Show spread opportunities
    if results["spread_opportunities"]:
        print(f"\n=== Spread Trading Opportunities ===")
        for opp in results["spread_opportunities"][:3]:
            print(f"{opp['type']}: Long {opp['long_asset']}, Short {opp['short_asset']} - Z-Score: {opp['z_score']:.2f}")
    
    # Show risk attribution
    if results["risk_attribution"]:
        print(f"\n=== Risk Attribution ===")
        print(f"Portfolio VaR: {results['risk_attribution']['portfolio_var']:.4f}")
        print(f"Diversification Ratio: {results['risk_attribution']['diversification_ratio']:.3f}")
        print(f"Concentration Risk: {results['risk_attribution']['concentration_risk']:.3f}")


if __name__ == "__main__":
    asyncio.run(example_usage())