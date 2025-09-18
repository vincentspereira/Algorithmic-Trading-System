"""Risk Management Pillar

Advanced risk management with dynamic position sizing, portfolio-level controls,
VaR calculations, and real-time risk monitoring.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
from scipy import stats
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    """Risk level classifications"""
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"
    EXTREME = "extreme"

class PositionSizeMethod(Enum):
    """Position sizing methods"""
    FIXED_AMOUNT = "fixed_amount"
    FIXED_PERCENTAGE = "fixed_percentage"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    KELLY_CRITERION = "kelly_criterion"
    RISK_PARITY = "risk_parity"
    MAX_DRAWDOWN = "max_drawdown"
    VAR_BASED = "var_based"

@dataclass
class RiskMetrics:
    """Comprehensive risk metrics"""
    var_1d: float = 0.0  # 1-day Value at Risk
    var_5d: float = 0.0  # 5-day Value at Risk
    cvar_1d: float = 0.0  # Conditional VaR (Expected Shortfall)
    max_drawdown: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    beta: float = 1.0
    correlation_with_market: float = 0.0
    skewness: float = 0.0
    kurtosis: float = 0.0
    tail_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    def get_risk_level(self) -> RiskLevel:
        """Determine overall risk level"""
        risk_score = 0
        
        # VaR contribution
        if abs(self.var_1d) > 0.05:
            risk_score += 3
        elif abs(self.var_1d) > 0.03:
            risk_score += 2
        elif abs(self.var_1d) > 0.02:
            risk_score += 1
            
        # Volatility contribution
        if self.volatility > 0.4:
            risk_score += 3
        elif self.volatility > 0.25:
            risk_score += 2
        elif self.volatility > 0.15:
            risk_score += 1
            
        # Drawdown contribution
        if self.max_drawdown > 0.2:
            risk_score += 3
        elif self.max_drawdown > 0.1:
            risk_score += 2
        elif self.max_drawdown > 0.05:
            risk_score += 1
            
        # Map score to risk level
        if risk_score >= 7:
            return RiskLevel.EXTREME
        elif risk_score >= 5:
            return RiskLevel.VERY_HIGH
        elif risk_score >= 3:
            return RiskLevel.HIGH
        elif risk_score >= 1:
            return RiskLevel.MODERATE
        else:
            return RiskLevel.LOW

@dataclass
class PositionSizeResult:
    """Position sizing calculation result"""
    symbol: str
    recommended_size: float
    max_size: float
    risk_amount: float
    method_used: PositionSizeMethod
    confidence: float
    risk_metrics: RiskMetrics
    constraints_applied: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class PortfolioRisk:
    """Portfolio-level risk assessment"""
    total_var: float = 0.0
    diversification_ratio: float = 0.0
    concentration_risk: float = 0.0
    sector_exposure: Dict[str, float] = field(default_factory=dict)
    correlation_risk: float = 0.0
    leverage: float = 1.0
    liquidity_risk: float = 0.0
    tail_risk: float = 0.0
    stress_test_results: Dict[str, float] = field(default_factory=dict)
    risk_budget_utilization: Dict[str, float] = field(default_factory=dict)

class RiskCalculator:
    """Advanced risk calculations"""
    
    @staticmethod
    def calculate_var(returns: pd.Series, confidence_level: float = 0.05, method: str = 'historical') -> float:
        """Calculate Value at Risk"""
        if len(returns) < 30:
            return 0.0
            
        if method == 'historical':
            return np.percentile(returns.dropna(), confidence_level * 100)
        elif method == 'parametric':
            mean = returns.mean()
            std = returns.std()
            return stats.norm.ppf(confidence_level, mean, std)
        elif method == 'monte_carlo':
            # Simple Monte Carlo simulation
            mean = returns.mean()
            std = returns.std()
            simulated = np.random.normal(mean, std, 10000)
            return np.percentile(simulated, confidence_level * 100)
        else:
            return np.percentile(returns.dropna(), confidence_level * 100)
    
    @staticmethod
    def calculate_cvar(returns: pd.Series, confidence_level: float = 0.05) -> float:
        """Calculate Conditional Value at Risk (Expected Shortfall)"""
        if len(returns) < 30:
            return 0.0
            
        var = RiskCalculator.calculate_var(returns, confidence_level)
        return returns[returns <= var].mean()
    
    @staticmethod
    def calculate_max_drawdown(prices: pd.Series) -> float:
        """Calculate maximum drawdown"""
        if len(prices) < 2:
            return 0.0
            
        peak = prices.expanding().max()
        drawdown = (prices - peak) / peak
        return abs(drawdown.min())
    
    @staticmethod
    def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio"""
        if len(returns) < 30 or returns.std() == 0:
            return 0.0
            
        excess_returns = returns.mean() * 252 - risk_free_rate
        volatility = returns.std() * np.sqrt(252)
        
        return excess_returns / volatility
    
    @staticmethod
    def calculate_sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate Sortino ratio"""
        if len(returns) < 30:
            return 0.0
            
        excess_returns = returns.mean() * 252 - risk_free_rate
        downside_returns = returns[returns < 0]
        
        if len(downside_returns) == 0:
            return float('inf')
            
        downside_deviation = downside_returns.std() * np.sqrt(252)
        
        return excess_returns / downside_deviation
    
    @staticmethod
    def calculate_beta(returns: pd.Series, market_returns: pd.Series) -> float:
        """Calculate beta against market"""
        if len(returns) < 30 or len(market_returns) < 30:
            return 1.0
            
        aligned_returns = returns.align(market_returns, join='inner')
        if len(aligned_returns[0]) < 30:
            return 1.0
            
        covariance = np.cov(aligned_returns[0], aligned_returns[1])[0, 1]
        market_variance = np.var(aligned_returns[1])
        
        return covariance / market_variance if market_variance != 0 else 1.0
    
    @staticmethod
    def calculate_tail_ratio(returns: pd.Series) -> float:
        """Calculate tail ratio (95th percentile / 5th percentile)"""
        if len(returns) < 50:
            return 1.0
            
        p95 = np.percentile(returns, 95)
        p5 = np.percentile(returns, 5)
        
        return abs(p95 / p5) if p5 != 0 else 1.0

class PositionSizer:
    """Advanced position sizing algorithms"""
    
    def __init__(self, account_size: float, max_risk_per_trade: float = 0.02):
        self.account_size = account_size
        self.max_risk_per_trade = max_risk_per_trade
        self.risk_calculator = RiskCalculator()
        
    def calculate_position_size(self, symbol: str, price: float, stop_loss: float, 
                              returns: pd.Series, method: PositionSizeMethod = PositionSizeMethod.VOLATILITY_ADJUSTED,
                              market_returns: Optional[pd.Series] = None) -> PositionSizeResult:
        """Calculate optimal position size"""
        try:
            # Calculate risk metrics
            risk_metrics = self._calculate_risk_metrics(returns, market_returns)
            
            # Calculate position size based on method
            if method == PositionSizeMethod.FIXED_AMOUNT:
                size = self._fixed_amount_sizing(price)
            elif method == PositionSizeMethod.FIXED_PERCENTAGE:
                size = self._fixed_percentage_sizing(price)
            elif method == PositionSizeMethod.VOLATILITY_ADJUSTED:
                size = self._volatility_adjusted_sizing(price, returns)
            elif method == PositionSizeMethod.KELLY_CRITERION:
                size = self._kelly_criterion_sizing(price, returns)
            elif method == PositionSizeMethod.RISK_PARITY:
                size = self._risk_parity_sizing(price, returns)
            elif method == PositionSizeMethod.MAX_DRAWDOWN:
                size = self._max_drawdown_sizing(price, returns)
            elif method == PositionSizeMethod.VAR_BASED:
                size = self._var_based_sizing(price, returns)
            else:
                size = self._volatility_adjusted_sizing(price, returns)
            
            # Apply constraints
            max_size = self._calculate_max_position_size(price, stop_loss)
            final_size = min(size, max_size)
            
            # Calculate risk amount
            risk_amount = abs(price - stop_loss) * final_size
            
            # Determine confidence
            confidence = self._calculate_sizing_confidence(returns, risk_metrics)
            
            # Track constraints applied
            constraints = []
            if final_size < size:
                constraints.append("max_position_limit")
            if risk_amount > self.account_size * self.max_risk_per_trade:
                constraints.append("max_risk_per_trade")
                
            return PositionSizeResult(
                symbol=symbol,
                recommended_size=final_size,
                max_size=max_size,
                risk_amount=risk_amount,
                method_used=method,
                confidence=confidence,
                risk_metrics=risk_metrics,
                constraints_applied=constraints
            )
            
        except Exception as e:
            logger.error(f"Error calculating position size for {symbol}: {e}")
            return PositionSizeResult(
                symbol=symbol,
                recommended_size=0.0,
                max_size=0.0,
                risk_amount=0.0,
                method_used=method,
                confidence=0.0,
                risk_metrics=RiskMetrics()
            )
    
    def _calculate_risk_metrics(self, returns: pd.Series, market_returns: Optional[pd.Series] = None) -> RiskMetrics:
        """Calculate comprehensive risk metrics"""
        metrics = RiskMetrics()
        
        if len(returns) < 30:
            return metrics
            
        try:
            metrics.var_1d = self.risk_calculator.calculate_var(returns, 0.05)
            metrics.var_5d = self.risk_calculator.calculate_var(returns, 0.05) * np.sqrt(5)
            metrics.cvar_1d = self.risk_calculator.calculate_cvar(returns, 0.05)
            metrics.volatility = returns.std() * np.sqrt(252)
            metrics.sharpe_ratio = self.risk_calculator.calculate_sharpe_ratio(returns)
            metrics.sortino_ratio = self.risk_calculator.calculate_sortino_ratio(returns)
            metrics.skewness = returns.skew()
            metrics.kurtosis = returns.kurtosis()
            metrics.tail_ratio = self.risk_calculator.calculate_tail_ratio(returns)
            
            if market_returns is not None:
                metrics.beta = self.risk_calculator.calculate_beta(returns, market_returns)
                metrics.correlation_with_market = returns.corr(market_returns)
                
            # Calculate max drawdown from cumulative returns
            cumulative_returns = (1 + returns).cumprod()
            metrics.max_drawdown = self.risk_calculator.calculate_max_drawdown(cumulative_returns)
            
            # Calmar ratio
            if metrics.max_drawdown > 0:
                annual_return = returns.mean() * 252
                metrics.calmar_ratio = annual_return / metrics.max_drawdown
                
        except Exception as e:
            logger.warning(f"Error calculating risk metrics: {e}")
            
        return metrics
    
    def _fixed_amount_sizing(self, price: float) -> float:
        """Fixed dollar amount position sizing"""
        fixed_amount = self.account_size * 0.1  # 10% of account
        return fixed_amount / price
    
    def _fixed_percentage_sizing(self, price: float) -> float:
        """Fixed percentage position sizing"""
        percentage = 0.05  # 5% of account
        return (self.account_size * percentage) / price
    
    def _volatility_adjusted_sizing(self, price: float, returns: pd.Series) -> float:
        """Volatility-adjusted position sizing"""
        if len(returns) < 30:
            return self._fixed_percentage_sizing(price)
            
        target_volatility = 0.15  # 15% target volatility
        actual_volatility = returns.std() * np.sqrt(252)
        
        if actual_volatility == 0:
            return self._fixed_percentage_sizing(price)
            
        volatility_adjustment = target_volatility / actual_volatility
        base_allocation = self.account_size * 0.1
        adjusted_allocation = base_allocation * volatility_adjustment
        
        return adjusted_allocation / price
    
    def _kelly_criterion_sizing(self, price: float, returns: pd.Series) -> float:
        """Kelly Criterion position sizing"""
        if len(returns) < 50:
            return self._volatility_adjusted_sizing(price, returns)
            
        # Estimate win rate and average win/loss
        wins = returns[returns > 0]
        losses = returns[returns < 0]
        
        if len(wins) == 0 or len(losses) == 0:
            return self._volatility_adjusted_sizing(price, returns)
            
        win_rate = len(wins) / len(returns)
        avg_win = wins.mean()
        avg_loss = abs(losses.mean())
        
        if avg_loss == 0:
            return self._volatility_adjusted_sizing(price, returns)
            
        # Kelly formula: f = (bp - q) / b
        # where b = avg_win/avg_loss, p = win_rate, q = 1 - win_rate
        b = avg_win / avg_loss
        kelly_fraction = (b * win_rate - (1 - win_rate)) / b
        
        # Apply Kelly fraction with safety factor
        kelly_fraction = max(0, min(kelly_fraction * 0.25, 0.2))  # Cap at 20% and use quarter Kelly
        
        return (self.account_size * kelly_fraction) / price
    
    def _risk_parity_sizing(self, price: float, returns: pd.Series) -> float:
        """Risk parity position sizing"""
        if len(returns) < 30:
            return self._volatility_adjusted_sizing(price, returns)
            
        volatility = returns.std() * np.sqrt(252)
        if volatility == 0:
            return self._fixed_percentage_sizing(price)
            
        # Allocate based on inverse volatility
        target_risk = self.account_size * self.max_risk_per_trade
        position_value = target_risk / volatility
        
        return position_value / price
    
    def _max_drawdown_sizing(self, price: float, returns: pd.Series) -> float:
        """Maximum drawdown-based position sizing"""
        if len(returns) < 50:
            return self._volatility_adjusted_sizing(price, returns)
            
        cumulative_returns = (1 + returns).cumprod()
        max_dd = self.risk_calculator.calculate_max_drawdown(cumulative_returns)
        
        if max_dd == 0:
            return self._fixed_percentage_sizing(price)
            
        # Size position to limit drawdown impact
        target_dd_impact = 0.02  # 2% max impact from this position
        sizing_factor = target_dd_impact / max_dd
        base_allocation = self.account_size * 0.1
        
        return (base_allocation * sizing_factor) / price
    
    def _var_based_sizing(self, price: float, returns: pd.Series) -> float:
        """VaR-based position sizing"""
        if len(returns) < 30:
            return self._volatility_adjusted_sizing(price, returns)
            
        var_1d = abs(self.risk_calculator.calculate_var(returns, 0.05))
        
        if var_1d == 0:
            return self._fixed_percentage_sizing(price)
            
        # Size position based on VaR limit
        max_var_amount = self.account_size * self.max_risk_per_trade
        position_value = max_var_amount / var_1d
        
        return position_value / price
    
    def _calculate_max_position_size(self, price: float, stop_loss: float) -> float:
        """Calculate maximum allowed position size"""
        # Based on maximum risk per trade
        risk_per_share = abs(price - stop_loss)
        if risk_per_share == 0:
            return (self.account_size * 0.1) / price  # Default to 10% if no stop loss
            
        max_risk_amount = self.account_size * self.max_risk_per_trade
        return max_risk_amount / risk_per_share
    
    def _calculate_sizing_confidence(self, returns: pd.Series, risk_metrics: RiskMetrics) -> float:
        """Calculate confidence in position sizing"""
        confidence = 0.5  # Base confidence
        
        # Data quality factor
        if len(returns) >= 100:
            confidence += 0.2
        elif len(returns) >= 50:
            confidence += 0.1
            
        # Risk metrics quality
        if risk_metrics.sharpe_ratio > 1.0:
            confidence += 0.1
        elif risk_metrics.sharpe_ratio > 0.5:
            confidence += 0.05
            
        # Volatility stability
        if 0.1 <= risk_metrics.volatility <= 0.3:
            confidence += 0.1
            
        # Drawdown control
        if risk_metrics.max_drawdown < 0.1:
            confidence += 0.1
            
        return min(confidence, 1.0)

class PortfolioRiskManager:
    """Portfolio-level risk management"""
    
    def __init__(self, max_portfolio_var: float = 0.05, max_concentration: float = 0.2):
        self.max_portfolio_var = max_portfolio_var
        self.max_concentration = max_concentration
        self.risk_calculator = RiskCalculator()
        
    def assess_portfolio_risk(self, positions: Dict[str, Dict], returns_data: Dict[str, pd.Series]) -> PortfolioRisk:
        """Assess portfolio-level risk"""
        try:
            portfolio_risk = PortfolioRisk()
            
            if not positions or not returns_data:
                return portfolio_risk
                
            # Calculate portfolio VaR
            portfolio_risk.total_var = self._calculate_portfolio_var(positions, returns_data)
            
            # Calculate diversification metrics
            portfolio_risk.diversification_ratio = self._calculate_diversification_ratio(positions, returns_data)
            portfolio_risk.concentration_risk = self._calculate_concentration_risk(positions)
            
            # Calculate correlation risk
            portfolio_risk.correlation_risk = self._calculate_correlation_risk(returns_data)
            
            # Calculate leverage
            portfolio_risk.leverage = self._calculate_leverage(positions)
            
            # Stress testing
            portfolio_risk.stress_test_results = self._run_stress_tests(positions, returns_data)
            
            return portfolio_risk
            
        except Exception as e:
            logger.error(f"Error assessing portfolio risk: {e}")
            return PortfolioRisk()
    
    def _calculate_portfolio_var(self, positions: Dict[str, Dict], returns_data: Dict[str, pd.Series]) -> float:
        """Calculate portfolio Value at Risk"""
        try:
            # Get aligned returns
            aligned_returns = pd.DataFrame(returns_data).dropna()
            if aligned_returns.empty:
                return 0.0
                
            # Calculate position weights
            total_value = sum(pos['value'] for pos in positions.values())
            if total_value == 0:
                return 0.0
                
            weights = np.array([positions.get(symbol, {}).get('value', 0) / total_value 
                              for symbol in aligned_returns.columns])
            
            # Calculate portfolio returns
            portfolio_returns = (aligned_returns * weights).sum(axis=1)
            
            # Calculate VaR
            return abs(self.risk_calculator.calculate_var(portfolio_returns, 0.05))
            
        except Exception as e:
            logger.warning(f"Error calculating portfolio VaR: {e}")
            return 0.0
    
    def _calculate_diversification_ratio(self, positions: Dict[str, Dict], returns_data: Dict[str, pd.Series]) -> float:
        """Calculate diversification ratio"""
        try:
            aligned_returns = pd.DataFrame(returns_data).dropna()
            if len(aligned_returns.columns) < 2:
                return 0.0
                
            # Calculate correlation matrix
            corr_matrix = aligned_returns.corr()
            
            # Average correlation
            n = len(corr_matrix)
            avg_correlation = (corr_matrix.sum().sum() - n) / (n * (n - 1))
            
            # Diversification ratio = 1 - average correlation
            return 1 - avg_correlation
            
        except Exception as e:
            logger.warning(f"Error calculating diversification ratio: {e}")
            return 0.0
    
    def _calculate_concentration_risk(self, positions: Dict[str, Dict]) -> float:
        """Calculate concentration risk (Herfindahl index)"""
        try:
            total_value = sum(pos['value'] for pos in positions.values())
            if total_value == 0:
                return 0.0
                
            weights = [pos['value'] / total_value for pos in positions.values()]
            herfindahl_index = sum(w**2 for w in weights)
            
            return herfindahl_index
            
        except Exception as e:
            logger.warning(f"Error calculating concentration risk: {e}")
            return 0.0
    
    def _calculate_correlation_risk(self, returns_data: Dict[str, pd.Series]) -> float:
        """Calculate correlation risk"""
        try:
            aligned_returns = pd.DataFrame(returns_data).dropna()
            if len(aligned_returns.columns) < 2:
                return 0.0
                
            corr_matrix = aligned_returns.corr()
            
            # Calculate average absolute correlation
            n = len(corr_matrix)
            total_abs_corr = 0
            count = 0
            
            for i in range(n):
                for j in range(i+1, n):
                    total_abs_corr += abs(corr_matrix.iloc[i, j])
                    count += 1
                    
            return total_abs_corr / count if count > 0 else 0.0
            
        except Exception as e:
            logger.warning(f"Error calculating correlation risk: {e}")
            return 0.0
    
    def _calculate_leverage(self, positions: Dict[str, Dict]) -> float:
        """Calculate portfolio leverage"""
        try:
            total_long = sum(pos['value'] for pos in positions.values() if pos.get('value', 0) > 0)
            total_short = abs(sum(pos['value'] for pos in positions.values() if pos.get('value', 0) < 0))
            net_value = total_long - total_short
            
            if net_value == 0:
                return 1.0
                
            return (total_long + total_short) / net_value
            
        except Exception as e:
            logger.warning(f"Error calculating leverage: {e}")
            return 1.0
    
    def _run_stress_tests(self, positions: Dict[str, Dict], returns_data: Dict[str, pd.Series]) -> Dict[str, float]:
        """Run portfolio stress tests"""
        stress_results = {}
        
        try:
            aligned_returns = pd.DataFrame(returns_data).dropna()
            if aligned_returns.empty:
                return stress_results
                
            total_value = sum(pos['value'] for pos in positions.values())
            if total_value == 0:
                return stress_results
                
            weights = np.array([positions.get(symbol, {}).get('value', 0) / total_value 
                              for symbol in aligned_returns.columns])
            
            # Market crash scenario (-20% across all assets)
            crash_impact = -0.2
            stress_results['market_crash'] = crash_impact
            
            # High volatility scenario (2x normal volatility)
            portfolio_returns = (aligned_returns * weights).sum(axis=1)
            normal_vol = portfolio_returns.std()
            stress_results['high_volatility'] = -2 * normal_vol
            
            # Correlation breakdown (all correlations go to 1)
            stress_results['correlation_breakdown'] = -0.15
            
            # Interest rate shock
            stress_results['interest_rate_shock'] = -0.1
            
        except Exception as e:
            logger.warning(f"Error running stress tests: {e}")
            
        return stress_results

class RiskManager:
    """Main risk management system"""
    
    def __init__(self, account_size: float, max_risk_per_trade: float = 0.02, max_portfolio_var: float = 0.05):
        self.account_size = account_size
        self.position_sizer = PositionSizer(account_size, max_risk_per_trade)
        self.portfolio_risk_manager = PortfolioRiskManager(max_portfolio_var)
        self.executor = ThreadPoolExecutor(max_workers=3)
        
    async def evaluate_trade_risk(self, symbol: str, price: float, stop_loss: float, 
                                returns: pd.Series, current_positions: Dict[str, Dict],
                                returns_data: Dict[str, pd.Series]) -> Dict[str, Any]:
        """Comprehensive trade risk evaluation"""
        try:
            # Calculate position size
            position_result = self.position_sizer.calculate_position_size(
                symbol, price, stop_loss, returns
            )
            
            # Assess current portfolio risk
            portfolio_risk = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.portfolio_risk_manager.assess_portfolio_risk,
                current_positions,
                returns_data
            )
            
            # Check risk limits
            risk_checks = self._perform_risk_checks(
                position_result, portfolio_risk, current_positions
            )
            
            return {
                'position_sizing': position_result,
                'portfolio_risk': portfolio_risk,
                'risk_checks': risk_checks,
                'recommendation': self._generate_recommendation(position_result, risk_checks)
            }
            
        except Exception as e:
            logger.error(f"Error evaluating trade risk for {symbol}: {e}")
            return {
                'position_sizing': PositionSizeResult(
                    symbol=symbol, recommended_size=0.0, max_size=0.0,
                    risk_amount=0.0, method_used=PositionSizeMethod.FIXED_PERCENTAGE,
                    confidence=0.0, risk_metrics=RiskMetrics()
                ),
                'portfolio_risk': PortfolioRisk(),
                'risk_checks': {'passed': False, 'reasons': ['calculation_error']},
                'recommendation': 'REJECT'
            }
    
    def _perform_risk_checks(self, position_result: PositionSizeResult, 
                           portfolio_risk: PortfolioRisk, current_positions: Dict[str, Dict]) -> Dict[str, Any]:
        """Perform comprehensive risk checks"""
        checks = {
            'passed': True,
            'warnings': [],
            'violations': [],
            'reasons': []
        }
        
        # Position size checks
        if position_result.recommended_size <= 0:
            checks['passed'] = False
            checks['violations'].append('zero_position_size')
            
        # Risk amount check
        max_risk = self.account_size * self.position_sizer.max_risk_per_trade
        if position_result.risk_amount > max_risk:
            checks['passed'] = False
            checks['violations'].append('excessive_risk_per_trade')
            
        # Portfolio VaR check
        if portfolio_risk.total_var > self.portfolio_risk_manager.max_portfolio_var:
            checks['warnings'].append('high_portfolio_var')
            
        # Concentration check
        if portfolio_risk.concentration_risk > self.portfolio_risk_manager.max_concentration:
            checks['warnings'].append('high_concentration')
            
        # Correlation risk check
        if portfolio_risk.correlation_risk > 0.8:
            checks['warnings'].append('high_correlation_risk')
            
        # Leverage check
        if portfolio_risk.leverage > 2.0:
            checks['warnings'].append('high_leverage')
            
        # Risk level check
        risk_level = position_result.risk_metrics.get_risk_level()
        if risk_level in [RiskLevel.VERY_HIGH, RiskLevel.EXTREME]:
            checks['warnings'].append(f'high_individual_risk_{risk_level.value}')
            
        return checks
    
    def _generate_recommendation(self, position_result: PositionSizeResult, risk_checks: Dict[str, Any]) -> str:
        """Generate trading recommendation based on risk analysis"""
        if not risk_checks['passed']:
            return 'REJECT'
        elif len(risk_checks['warnings']) >= 3:
            return 'CAUTION'
        elif position_result.confidence < 0.3:
            return 'LOW_CONFIDENCE'
        elif position_result.confidence > 0.7 and len(risk_checks['warnings']) == 0:
            return 'APPROVE'
        else:
            return 'REVIEW'
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get risk management summary"""
        return {
            'account_size': self.account_size,
            'max_risk_per_trade': self.position_sizer.max_risk_per_trade,
            'max_portfolio_var': self.portfolio_risk_manager.max_portfolio_var,
            'max_concentration': self.portfolio_risk_manager.max_concentration,
            'available_methods': [method.value for method in PositionSizeMethod],
            'risk_levels': [level.value for level in RiskLevel]
        }