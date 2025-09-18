"""Scenario Analysis Module

This module provides comprehensive scenario analysis including Monte Carlo simulations,
historical scenario analysis, and custom scenario testing for backtesting results.
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from scipy import stats
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

@dataclass
class ScenarioConfig:
    """Configuration for scenario analysis"""
    n_simulations: int = 10000
    confidence_levels: List[float] = field(default_factory=lambda: [0.95, 0.99])
    time_horizons: List[int] = field(default_factory=lambda: [1, 5, 10, 21, 63, 252])
    
    # Monte Carlo settings
    use_bootstrap: bool = True
    block_size: int = 5
    random_seed: int = 42
    
    # Historical scenario settings
    scenario_window: int = 252
    min_scenario_length: int = 21
    
    # Custom scenario settings
    custom_scenarios: Dict[str, Dict[str, float]] = field(default_factory=dict)

@dataclass
class MonteCarloResults:
    """Monte Carlo simulation results"""
    simulated_returns: np.ndarray = field(default_factory=lambda: np.array([]))
    percentiles: Dict[str, Dict[int, float]] = field(default_factory=dict)
    
    # Summary statistics
    mean_return: float = 0.0
    std_return: float = 0.0
    skewness: float = 0.0
    kurtosis: float = 0.0
    
    # Risk metrics
    var_estimates: Dict[str, float] = field(default_factory=dict)
    cvar_estimates: Dict[str, float] = field(default_factory=dict)
    
    # Tail statistics
    tail_expectations: Dict[str, float] = field(default_factory=dict)
    extreme_scenarios: Dict[str, float] = field(default_factory=dict)

@dataclass
class HistoricalScenario:
    """Historical scenario definition"""
    name: str
    start_date: datetime
    end_date: datetime
    description: str
    market_conditions: Dict[str, Any] = field(default_factory=dict)
    
    # Scenario characteristics
    duration_days: int = 0
    max_drawdown: float = 0.0
    volatility: float = 0.0
    total_return: float = 0.0

@dataclass
class ScenarioAnalysisResults:
    """Comprehensive scenario analysis results"""
    monte_carlo: MonteCarloResults = field(default_factory=MonteCarloResults)
    historical_scenarios: Dict[str, Dict[str, float]] = field(default_factory=dict)
    custom_scenarios: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Scenario comparisons
    scenario_rankings: List[Tuple[str, float]] = field(default_factory=list)
    worst_case_analysis: Dict[str, Any] = field(default_factory=dict)
    best_case_analysis: Dict[str, Any] = field(default_factory=dict)
    
    # Stress test results
    stress_test_results: Dict[str, float] = field(default_factory=dict)
    
    # Scenario correlations
    scenario_correlations: pd.DataFrame = field(default_factory=pd.DataFrame)

class ScenarioAnalyzer:
    """Comprehensive scenario analyzer
    
    Provides Monte Carlo simulations, historical scenario analysis,
    and custom scenario testing for portfolio risk assessment.
    """
    
    def __init__(self, config: Optional[ScenarioConfig] = None):
        """Initialize scenario analyzer
        
        Args:
            config: Scenario analysis configuration
        """
        self.config = config or ScenarioConfig()
        
        # Predefined historical scenarios
        self.historical_scenarios = {
            'black_monday_1987': {
                'start': '1987-10-01',
                'end': '1987-11-30',
                'description': 'Black Monday crash of 1987',
                'equity_shock': -0.22,
                'volatility_spike': 3.0
            },
            'dot_com_crash_2000': {
                'start': '2000-03-01',
                'end': '2002-10-31',
                'description': 'Dot-com bubble burst',
                'equity_shock': -0.49,
                'volatility_spike': 2.5
            },
            'financial_crisis_2008': {
                'start': '2007-10-01',
                'end': '2009-03-31',
                'description': 'Global Financial Crisis',
                'equity_shock': -0.57,
                'volatility_spike': 4.0
            },
            'flash_crash_2010': {
                'start': '2010-05-06',
                'end': '2010-05-07',
                'description': 'Flash Crash',
                'equity_shock': -0.09,
                'volatility_spike': 5.0
            },
            'covid_crash_2020': {
                'start': '2020-02-20',
                'end': '2020-04-30',
                'description': 'COVID-19 pandemic crash',
                'equity_shock': -0.34,
                'volatility_spike': 3.5
            },
            'rate_hike_2022': {
                'start': '2022-01-01',
                'end': '2022-12-31',
                'description': 'Federal Reserve rate hikes',
                'equity_shock': -0.18,
                'volatility_spike': 1.8
            }
        }
        
        # Set random seed for reproducibility
        np.random.seed(self.config.random_seed)
        
        logger.info(f"Initialized scenario analyzer with {self.config.n_simulations} simulations")
    
    def analyze_scenarios(
        self,
        returns: pd.Series,
        positions: Optional[pd.DataFrame] = None,
        market_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> ScenarioAnalysisResults:
        """Comprehensive scenario analysis
        
        Args:
            returns: Portfolio returns time series
            positions: Position weights over time
            market_data: Market data for scenario construction
            
        Returns:
            Comprehensive scenario analysis results
        """
        try:
            results = ScenarioAnalysisResults()
            
            if returns.empty:
                logger.warning("Empty returns series provided")
                return results
            
            # Monte Carlo simulation
            logger.info("Running Monte Carlo simulations...")
            results.monte_carlo = self._run_monte_carlo_simulation(returns)
            
            # Historical scenario analysis
            logger.info("Analyzing historical scenarios...")
            results.historical_scenarios = self._analyze_historical_scenarios(returns, market_data)
            
            # Custom scenario analysis
            if self.config.custom_scenarios:
                logger.info("Analyzing custom scenarios...")
                results.custom_scenarios = self._analyze_custom_scenarios(returns, positions)
            
            # Stress testing
            logger.info("Running stress tests...")
            results.stress_test_results = self._run_stress_tests(returns)
            
            # Scenario comparisons and rankings
            results = self._compare_scenarios(results)
            
            logger.info("Scenario analysis completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"Error in scenario analysis: {e}")
            raise
    
    def _run_monte_carlo_simulation(self, returns: pd.Series) -> MonteCarloResults:
        """Run Monte Carlo simulation"""
        try:
            results = MonteCarloResults()
            
            if len(returns) < 30:
                logger.warning("Insufficient data for Monte Carlo simulation")
                return results
            
            # Fit distribution to returns
            if self.config.use_bootstrap:
                # Bootstrap resampling
                simulated_returns = self._bootstrap_simulation(returns)
            else:
                # Parametric simulation
                simulated_returns = self._parametric_simulation(returns)
            
            results.simulated_returns = simulated_returns
            
            # Calculate summary statistics
            results.mean_return = np.mean(simulated_returns)
            results.std_return = np.std(simulated_returns)
            results.skewness = stats.skew(simulated_returns)
            results.kurtosis = stats.kurtosis(simulated_returns)
            
            # Calculate percentiles for different time horizons
            for horizon in self.config.time_horizons:
                horizon_returns = simulated_returns * np.sqrt(horizon)
                
                results.percentiles[f'{horizon}d'] = {
                    1: np.percentile(horizon_returns, 1),
                    5: np.percentile(horizon_returns, 5),
                    10: np.percentile(horizon_returns, 10),
                    25: np.percentile(horizon_returns, 25),
                    50: np.percentile(horizon_returns, 50),
                    75: np.percentile(horizon_returns, 75),
                    90: np.percentile(horizon_returns, 90),
                    95: np.percentile(horizon_returns, 95),
                    99: np.percentile(horizon_returns, 99)
                }
            
            # Calculate VaR and CVaR estimates
            for confidence in self.config.confidence_levels:
                alpha = 1 - confidence
                var_threshold = np.percentile(simulated_returns, alpha * 100)
                
                results.var_estimates[f'{confidence:.0%}'] = var_threshold
                
                # CVaR (Expected Shortfall)
                tail_returns = simulated_returns[simulated_returns <= var_threshold]
                results.cvar_estimates[f'{confidence:.0%}'] = np.mean(tail_returns) if len(tail_returns) > 0 else var_threshold
            
            # Tail expectations
            results.tail_expectations = {
                'worst_1%': np.mean(simulated_returns[simulated_returns <= np.percentile(simulated_returns, 1)]),
                'worst_5%': np.mean(simulated_returns[simulated_returns <= np.percentile(simulated_returns, 5)]),
                'best_1%': np.mean(simulated_returns[simulated_returns >= np.percentile(simulated_returns, 99)]),
                'best_5%': np.mean(simulated_returns[simulated_returns >= np.percentile(simulated_returns, 95)])
            }
            
            # Extreme scenarios
            results.extreme_scenarios = {
                'worst_case': np.min(simulated_returns),
                'best_case': np.max(simulated_returns),
                'median_case': np.median(simulated_returns)
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error in Monte Carlo simulation: {e}")
            return MonteCarloResults()
    
    def _bootstrap_simulation(self, returns: pd.Series) -> np.ndarray:
        """Bootstrap resampling simulation"""
        try:
            n_obs = len(returns)
            simulated_returns = np.zeros(self.config.n_simulations)
            
            # Block bootstrap to preserve serial correlation
            for i in range(self.config.n_simulations):
                # Generate random starting points for blocks
                n_blocks = n_obs // self.config.block_size
                block_starts = np.random.randint(0, n_obs - self.config.block_size + 1, n_blocks)
                
                # Sample blocks
                sampled_returns = []
                for start in block_starts:
                    block = returns.iloc[start:start + self.config.block_size]
                    sampled_returns.extend(block.values)
                
                # Take first n_obs observations
                sampled_returns = sampled_returns[:n_obs]
                simulated_returns[i] = np.mean(sampled_returns)
            
            return simulated_returns
            
        except Exception as e:
            logger.error(f"Error in bootstrap simulation: {e}")
            return np.array([])
    
    def _parametric_simulation(self, returns: pd.Series) -> np.ndarray:
        """Parametric simulation using fitted distribution"""
        try:
            # Fit normal distribution
            mean_return = returns.mean()
            std_return = returns.std()
            
            # Generate random samples
            simulated_returns = np.random.normal(mean_return, std_return, self.config.n_simulations)
            
            return simulated_returns
            
        except Exception as e:
            logger.error(f"Error in parametric simulation: {e}")
            return np.array([])
    
    def _analyze_historical_scenarios(self, returns: pd.Series, market_data: Optional[Dict[str, pd.DataFrame]] = None) -> Dict[str, Dict[str, float]]:
        """Analyze historical scenarios"""
        try:
            scenario_results = {}
            
            for scenario_name, scenario_info in self.historical_scenarios.items():
                try:
                    # Apply scenario shock to returns
                    equity_shock = scenario_info.get('equity_shock', 0)
                    volatility_spike = scenario_info.get('volatility_spike', 1)
                    
                    # Simple scenario application
                    base_volatility = returns.std()
                    shocked_volatility = base_volatility * volatility_spike
                    
                    # Simulate scenario impact
                    scenario_return = equity_shock
                    scenario_volatility = shocked_volatility * np.sqrt(252)  # Annualized
                    
                    # Calculate risk metrics under scenario
                    scenario_var_95 = scenario_return - 1.645 * shocked_volatility
                    scenario_var_99 = scenario_return - 2.326 * shocked_volatility
                    
                    scenario_results[scenario_name] = {
                        'expected_return': scenario_return,
                        'volatility': scenario_volatility,
                        'var_95': scenario_var_95,
                        'var_99': scenario_var_99,
                        'max_loss': scenario_return - 3 * shocked_volatility,
                        'probability_loss': self._calculate_loss_probability(scenario_return, shocked_volatility)
                    }
                    
                except Exception as e:
                    logger.warning(f"Error analyzing scenario {scenario_name}: {e}")
                    continue
            
            return scenario_results
            
        except Exception as e:
            logger.error(f"Error analyzing historical scenarios: {e}")
            return {}
    
    def _analyze_custom_scenarios(self, returns: pd.Series, positions: Optional[pd.DataFrame] = None) -> Dict[str, Dict[str, float]]:
        """Analyze custom scenarios"""
        try:
            scenario_results = {}
            
            for scenario_name, scenario_shocks in self.config.custom_scenarios.items():
                try:
                    # Apply custom shocks
                    total_shock = 0
                    
                    if positions is not None:
                        # Weight shocks by positions
                        latest_positions = positions.iloc[-1]
                        for asset, shock in scenario_shocks.items():
                            if asset in latest_positions.index:
                                weight = latest_positions[asset]
                                total_shock += weight * shock
                    else:
                        # Simple average of shocks
                        total_shock = np.mean(list(scenario_shocks.values()))
                    
                    # Calculate scenario metrics
                    base_volatility = returns.std()
                    scenario_volatility = base_volatility * 1.5  # Assume higher volatility in stress
                    
                    scenario_results[scenario_name] = {
                        'expected_return': total_shock,
                        'volatility': scenario_volatility * np.sqrt(252),
                        'var_95': total_shock - 1.645 * scenario_volatility,
                        'var_99': total_shock - 2.326 * scenario_volatility,
                        'max_loss': total_shock - 3 * scenario_volatility,
                        'probability_loss': self._calculate_loss_probability(total_shock, scenario_volatility)
                    }
                    
                except Exception as e:
                    logger.warning(f"Error analyzing custom scenario {scenario_name}: {e}")
                    continue
            
            return scenario_results
            
        except Exception as e:
            logger.error(f"Error analyzing custom scenarios: {e}")
            return {}
    
    def _run_stress_tests(self, returns: pd.Series) -> Dict[str, float]:
        """Run comprehensive stress tests"""
        try:
            stress_results = {}
            
            base_return = returns.mean()
            base_volatility = returns.std()
            
            # Volatility stress tests
            for vol_multiplier in [2, 3, 5]:
                stressed_vol = base_volatility * vol_multiplier
                stress_results[f'vol_shock_{vol_multiplier}x'] = base_return - 2.33 * stressed_vol
            
            # Return stress tests
            for return_shock in [-0.1, -0.2, -0.3, -0.5]:
                stress_results[f'return_shock_{abs(return_shock):.0%}'] = return_shock
            
            # Combined stress tests
            stress_results['combined_stress_moderate'] = -0.15 - 2 * base_volatility
            stress_results['combined_stress_severe'] = -0.30 - 3 * base_volatility
            stress_results['combined_stress_extreme'] = -0.50 - 5 * base_volatility
            
            # Tail risk stress tests
            worst_1pct = returns.quantile(0.01)
            worst_5pct = returns.quantile(0.05)
            
            stress_results['historical_worst_1pct'] = worst_1pct
            stress_results['historical_worst_5pct'] = worst_5pct
            stress_results['tail_risk_2x'] = worst_1pct * 2
            stress_results['tail_risk_3x'] = worst_1pct * 3
            
            return stress_results
            
        except Exception as e:
            logger.error(f"Error running stress tests: {e}")
            return {}
    
    def _compare_scenarios(self, results: ScenarioAnalysisResults) -> ScenarioAnalysisResults:
        """Compare and rank scenarios"""
        try:
            all_scenarios = {}
            
            # Collect all scenario results
            for scenario_name, metrics in results.historical_scenarios.items():
                all_scenarios[f'historical_{scenario_name}'] = metrics.get('expected_return', 0)
            
            for scenario_name, metrics in results.custom_scenarios.items():
                all_scenarios[f'custom_{scenario_name}'] = metrics.get('expected_return', 0)
            
            for scenario_name, return_val in results.stress_test_results.items():
                all_scenarios[f'stress_{scenario_name}'] = return_val
            
            # Rank scenarios by expected return (worst first)
            results.scenario_rankings = sorted(all_scenarios.items(), key=lambda x: x[1])
            
            # Worst case analysis
            if results.scenario_rankings:
                worst_scenario = results.scenario_rankings[0]
                results.worst_case_analysis = {
                    'scenario_name': worst_scenario[0],
                    'expected_loss': worst_scenario[1],
                    'probability_estimate': 0.01,  # Assume 1% probability for worst case
                    'impact_description': f"Worst case scenario with {worst_scenario[1]:.2%} expected loss"
                }
                
                # Best case analysis
                best_scenario = results.scenario_rankings[-1]
                results.best_case_analysis = {
                    'scenario_name': best_scenario[0],
                    'expected_gain': best_scenario[1],
                    'probability_estimate': 0.05,  # Assume 5% probability for best case
                    'impact_description': f"Best case scenario with {best_scenario[1]:.2%} expected gain"
                }
            
            return results
            
        except Exception as e:
            logger.error(f"Error comparing scenarios: {e}")
            return results
    
    def _calculate_loss_probability(self, expected_return: float, volatility: float) -> float:
        """Calculate probability of loss given return and volatility"""
        try:
            if volatility <= 0:
                return 1.0 if expected_return < 0 else 0.0
            
            # Assume normal distribution
            z_score = -expected_return / volatility
            return stats.norm.cdf(z_score)
            
        except Exception as e:
            logger.error(f"Error calculating loss probability: {e}")
            return 0.5
    
    def add_custom_scenario(self, name: str, shocks: Dict[str, float], description: str = ""):
        """Add custom scenario
        
        Args:
            name: Scenario name
            shocks: Dictionary of asset/factor shocks
            description: Scenario description
        """
        try:
            self.config.custom_scenarios[name] = shocks
            logger.info(f"Added custom scenario: {name}")
            
        except Exception as e:
            logger.error(f"Error adding custom scenario: {e}")
    
    def generate_scenario_report(self, results: ScenarioAnalysisResults) -> str:
        """Generate comprehensive scenario analysis report"""
        try:
            report = f"""
SCENARIO ANALYSIS REPORT
=======================

Monte Carlo Simulation Results:
- Simulations: {self.config.n_simulations:,}
- Mean Return: {results.monte_carlo.mean_return:.2%}
- Volatility: {results.monte_carlo.std_return:.2%}
- Skewness: {results.monte_carlo.skewness:.3f}
- Kurtosis: {results.monte_carlo.kurtosis:.3f}

Value at Risk Estimates:
"""
            
            for confidence, var_value in results.monte_carlo.var_estimates.items():
                cvar_value = results.monte_carlo.cvar_estimates.get(confidence, 0)
                report += f"- VaR ({confidence}): {var_value:.2%}, CVaR: {cvar_value:.2%}\n"
            
            report += "\nTail Expectations:\n"
            for tail_type, expectation in results.monte_carlo.tail_expectations.items():
                report += f"- {tail_type.replace('_', ' ').title()}: {expectation:.2%}\n"
            
            report += "\nExtreme Scenarios:\n"
            for scenario_type, value in results.monte_carlo.extreme_scenarios.items():
                report += f"- {scenario_type.replace('_', ' ').title()}: {value:.2%}\n"
            
            if results.historical_scenarios:
                report += "\nHistorical Scenario Analysis:\n"
                for scenario_name, metrics in results.historical_scenarios.items():
                    report += f"- {scenario_name}: {metrics.get('expected_return', 0):.2%} (VaR 95%: {metrics.get('var_95', 0):.2%})\n"
            
            if results.stress_test_results:
                report += "\nStress Test Results:\n"
                worst_stress = min(results.stress_test_results.items(), key=lambda x: x[1])
                report += f"- Worst Stress Test: {worst_stress[0]} = {worst_stress[1]:.2%}\n"
                
                for stress_name, stress_value in list(results.stress_test_results.items())[:5]:
                    report += f"- {stress_name}: {stress_value:.2%}\n"
            
            if results.scenario_rankings:
                report += "\nScenario Rankings (Worst to Best):\n"
                for i, (scenario_name, return_val) in enumerate(results.scenario_rankings[:10]):
                    report += f"{i+1:2d}. {scenario_name}: {return_val:.2%}\n"
            
            if results.worst_case_analysis:
                report += f"""
Worst Case Analysis:
- Scenario: {results.worst_case_analysis.get('scenario_name', 'Unknown')}
- Expected Loss: {results.worst_case_analysis.get('expected_loss', 0):.2%}
- Estimated Probability: {results.worst_case_analysis.get('probability_estimate', 0):.1%}
"""
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating scenario report: {e}")
            return "Error generating scenario analysis report"
    
    def export_simulation_data(self, results: MonteCarloResults, filename: str):
        """Export Monte Carlo simulation data
        
        Args:
            results: Monte Carlo results
            filename: Output filename
        """
        try:
            if len(results.simulated_returns) == 0:
                logger.warning("No simulation data to export")
                return
            
            # Create DataFrame with simulation results
            df = pd.DataFrame({
                'simulation_id': range(len(results.simulated_returns)),
                'simulated_return': results.simulated_returns
            })
            
            # Add percentile rankings
            df['percentile_rank'] = df['simulated_return'].rank(pct=True)
            
            # Add scenario classifications
            df['scenario_type'] = 'normal'
            df.loc[df['percentile_rank'] <= 0.01, 'scenario_type'] = 'extreme_loss'
            df.loc[df['percentile_rank'] <= 0.05, 'scenario_type'] = 'severe_loss'
            df.loc[df['percentile_rank'] >= 0.95, 'scenario_type'] = 'strong_gain'
            df.loc[df['percentile_rank'] >= 0.99, 'scenario_type'] = 'extreme_gain'
            
            # Export to CSV
            df.to_csv(filename, index=False)
            logger.info(f"Exported simulation data to {filename}")
            
        except Exception as e:
            logger.error(f"Error exporting simulation data: {e}")