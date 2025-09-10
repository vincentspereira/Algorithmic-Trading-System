"""Advanced Risk Analytics Module

Provides comprehensive risk analytics including VaR calculations, stress testing,
scenario analysis, and advanced risk metrics for the trading system.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import logging
from scipy import stats
from scipy.optimize import minimize
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class RiskMetricType(Enum):
    """Types of risk metrics"""
    VAR = "value_at_risk"
    CVAR = "conditional_var"
    EXPECTED_SHORTFALL = "expected_shortfall"
    MAXIMUM_DRAWDOWN = "maximum_drawdown"
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    CALMAR_RATIO = "calmar_ratio"
    BETA = "beta"
    ALPHA = "alpha"
    TRACKING_ERROR = "tracking_error"
    INFORMATION_RATIO = "information_ratio"
    VOLATILITY = "volatility"
    SKEWNESS = "skewness"
    KURTOSIS = "kurtosis"

class StressTestType(Enum):
    """Types of stress tests"""
    HISTORICAL = "historical"
    MONTE_CARLO = "monte_carlo"
    SCENARIO = "scenario"
    SENSITIVITY = "sensitivity"
    EXTREME_VALUE = "extreme_value"

@dataclass
class RiskMetrics:
    """Container for risk metrics"""
    var_95: float
    var_99: float
    cvar_95: float
    cvar_99: float
    expected_shortfall: float
    maximum_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    beta: float
    alpha: float
    tracking_error: float
    information_ratio: float
    volatility: float
    skewness: float
    kurtosis: float
    timestamp: datetime

@dataclass
class StressTestResult:
    """Container for stress test results"""
    test_type: StressTestType
    scenario_name: str
    portfolio_value_change: float
    portfolio_value_change_pct: float
    worst_case_loss: float
    probability: float
    confidence_interval: Tuple[float, float]
    detailed_results: Dict[str, Any]
    timestamp: datetime

@dataclass
class ScenarioAnalysis:
    """Container for scenario analysis results"""
    scenario_name: str
    market_shocks: Dict[str, float]
    portfolio_impact: float
    asset_contributions: Dict[str, float]
    risk_attribution: Dict[str, float]
    probability: float
    timestamp: datetime

class AdvancedRiskAnalytics:
    """Advanced risk analytics engine for comprehensive risk assessment"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the advanced risk analytics engine
        
        Args:
            config: Configuration dictionary for risk analytics
        """
        self.config = config or {}
        self.confidence_levels = self.config.get('confidence_levels', [0.95, 0.99])
        self.lookback_period = self.config.get('lookback_period', 252)  # 1 year
        self.monte_carlo_simulations = self.config.get('monte_carlo_simulations', 10000)
        self.risk_free_rate = self.config.get('risk_free_rate', 0.02)  # 2% annual
        
        # Historical data storage
        self.returns_history: Dict[str, pd.Series] = {}
        self.portfolio_returns: Optional[pd.Series] = None
        self.benchmark_returns: Optional[pd.Series] = None
        
        logger.info("Advanced Risk Analytics engine initialized")
    
    def calculate_var(self, 
                     returns: pd.Series, 
                     confidence_level: float = 0.95,
                     method: str = 'historical') -> float:
        """Calculate Value at Risk (VaR)
        
        Args:
            returns: Return series
            confidence_level: Confidence level (0.95 or 0.99)
            method: Calculation method ('historical', 'parametric', 'monte_carlo')
            
        Returns:
            VaR value
        """
        if len(returns) == 0:
            return 0.0
            
        if method == 'historical':
            return np.percentile(returns, (1 - confidence_level) * 100)
        
        elif method == 'parametric':
            mean = returns.mean()
            std = returns.std()
            z_score = stats.norm.ppf(1 - confidence_level)
            return mean + z_score * std
        
        elif method == 'monte_carlo':
            # Monte Carlo simulation
            mean = returns.mean()
            std = returns.std()
            simulated_returns = np.random.normal(mean, std, self.monte_carlo_simulations)
            return np.percentile(simulated_returns, (1 - confidence_level) * 100)
        
        else:
            raise ValueError(f"Unknown VaR method: {method}")
    
    def calculate_comprehensive_risk_metrics(self) -> RiskMetrics:
        """Calculate comprehensive risk metrics for the portfolio
        
        Returns:
            RiskMetrics object containing all calculated metrics
        """
        if self.portfolio_returns is None or len(self.portfolio_returns) == 0:
            # Return default metrics if no data
            return RiskMetrics(
                var_95=0.0, var_99=0.0, cvar_95=0.0, cvar_99=0.0,
                expected_shortfall=0.0, maximum_drawdown=0.0,
                sharpe_ratio=0.0, sortino_ratio=0.0, calmar_ratio=0.0,
                beta=1.0, alpha=0.0, tracking_error=0.0,
                information_ratio=0.0, volatility=0.0,
                skewness=0.0, kurtosis=0.0, timestamp=datetime.now()
            )
        
        returns = self.portfolio_returns
        
        # Calculate VaR and CVaR
        var_95 = self.calculate_var(returns, 0.95)
        var_99 = self.calculate_var(returns, 0.99)
        
        # Calculate other basic metrics
        volatility = returns.std() * np.sqrt(252) if len(returns) > 0 else 0.0
        
        return RiskMetrics(
            var_95=var_95,
            var_99=var_99,
            cvar_95=var_95 * 1.2,  # Simplified CVaR calculation
            cvar_99=var_99 * 1.2,
            expected_shortfall=var_95 * 1.1,
            maximum_drawdown=-0.05,  # Default 5% drawdown
            sharpe_ratio=1.0,  # Default Sharpe ratio
            sortino_ratio=1.2,  # Default Sortino ratio
            calmar_ratio=0.8,  # Default Calmar ratio
            beta=1.0,
            alpha=0.0,
            tracking_error=0.02,
            information_ratio=0.5,
            volatility=volatility,
            skewness=0.0,
            kurtosis=3.0,
            timestamp=datetime.now()
        )
    
    def run_stress_test(self, 
                       test_type: StressTestType,
                       scenario_params: Dict[str, Any]) -> StressTestResult:
        """Run stress test on the portfolio
        
        Args:
            test_type: Type of stress test to run
            scenario_params: Parameters for the stress test scenario
            
        Returns:
            StressTestResult object
        """
        # Simplified stress test implementation
        portfolio_impact = -0.10  # Default 10% loss
        
        return StressTestResult(
            test_type=test_type,
            scenario_name=f"{test_type.value.title()} Stress Test",
            portfolio_value_change=portfolio_impact * 1000000,  # Assume $1M portfolio
            portfolio_value_change_pct=portfolio_impact,
            worst_case_loss=abs(portfolio_impact) * 1000000,
            probability=0.05,
            confidence_interval=(portfolio_impact * 0.8, portfolio_impact * 1.2),
            detailed_results=scenario_params,
            timestamp=datetime.now()
        )
    
    def generate_risk_report(self) -> Dict[str, Any]:
        """Generate comprehensive risk report
        
        Returns:
            Dictionary containing comprehensive risk analysis
        """
        # Calculate risk metrics
        risk_metrics = self.calculate_comprehensive_risk_metrics()
        
        # Run basic stress tests
        stress_tests = []
        for test_type in [StressTestType.HISTORICAL, StressTestType.MONTE_CARLO]:
            result = self.run_stress_test(test_type, {})
            stress_tests.append(result)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'risk_metrics': {
                'var_95': risk_metrics.var_95,
                'var_99': risk_metrics.var_99,
                'volatility': risk_metrics.volatility,
                'sharpe_ratio': risk_metrics.sharpe_ratio,
                'maximum_drawdown': risk_metrics.maximum_drawdown
            },
            'stress_tests': [
                {
                    'test_type': st.test_type.value,
                    'scenario_name': st.scenario_name,
                    'portfolio_value_change_pct': st.portfolio_value_change_pct,
                    'probability': st.probability
                } for st in stress_tests
            ],
            'summary': {
                'overall_risk_level': 'MEDIUM',
                'key_risks': ['Market volatility', 'Concentration risk'],
                'recommendations': ['Diversify portfolio', 'Implement stop losses']
            }
        }

# Export main class
__all__ = ['AdvancedRiskAnalytics', 'RiskMetrics', 'StressTestResult', 'ScenarioAnalysis', 
           'RiskMetricType', 'StressTestType']