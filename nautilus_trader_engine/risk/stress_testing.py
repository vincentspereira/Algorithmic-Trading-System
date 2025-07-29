"""
Comprehensive Stress Testing Framework
Scenario-based stress testing, historical stress tests, Monte Carlo stress testing,
and stress test reporting capabilities
"""

import asyncio
import time
import logging
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from collections import defaultdict
import threading
import warnings

# Suppress numpy warnings for cleaner output
warnings.filterwarnings('ignore', category=RuntimeWarning)


class StressTestType(Enum):
    """Types of stress tests"""
    SCENARIO_BASED = "scenario_based"
    HISTORICAL = "historical"
    MONTE_CARLO = "monte_carlo"


class RiskFactor(Enum):
    """Risk factors for stress testing"""
    EQUITY_MARKET = "equity_market"
    INTEREST_RATES = "interest_rates"
    CREDIT_SPREADS = "credit_spreads"
    CURRENCY = "currency"
    COMMODITY = "commodity"
    VOLATILITY = "volatility"
    LIQUIDITY = "liquidity"
    CORRELATION = "correlation"


@dataclass
class StressShock:
    """Individual stress shock definition"""
    factor: RiskFactor
    shock_type: str  # "absolute", "relative", "percentile"
    magnitude: float
    description: str = ""
    
    # Asset-specific shocks
    affected_assets: Optional[List[str]] = None
    affected_sectors: Optional[List[str]] = None


@dataclass
class StressScenarioDefinition:
    """Complete stress scenario definition"""
    name: str
    description: str
    shocks: List[StressShock]
    
    # Scenario metadata
    historical_date: Optional[datetime] = None
    probability: Optional[float] = None
    severity: str = "medium"  # "low", "medium", "high", "extreme"
    
    # Scenario dynamics
    is_simultaneous: bool = True


@dataclass
class StressTestResult:
    """Stress test result for a single scenario"""
    scenario_name: str
    stress_type: StressTestType
    portfolio_id: str
    
    # Portfolio impact
    base_portfolio_value: float
    stressed_portfolio_value: float
    absolute_loss: float
    relative_loss: float
    
    # Risk metrics under stress
    stressed_var: Optional[float] = None
    stressed_expected_shortfall: Optional[float] = None
    stressed_max_drawdown: Optional[float] = None
    
    # Asset-level impacts
    asset_impacts: Dict[str, float] = field(default_factory=dict)
    sector_impacts: Dict[str, float] = field(default_factory=dict)
    
    # Scenario details
    scenario_definition: Optional[StressScenarioDefinition] = None
    calculation_time: datetime = field(default_factory=datetime.now)
    
    # Additional metrics
    recovery_time_estimate: Optional[int] = None  # Days to recover
    
    # Diagnostics
    diagnostics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StressTestSuite:
    """Collection of stress test results"""
    portfolio_id: str
    test_date: datetime
    base_portfolio_value: float
    
    # Individual test results
    scenario_results: List[StressTestResult] = field(default_factory=list)
    
    # Aggregate metrics
    worst_case_loss: float = 0.0
    worst_case_scenario: Optional[str] = None
    average_loss: float = 0.0
    
    # Risk concentration
    tail_risk_scenarios: List[str] = field(default_factory=list)
    systemic_risk_score: float = 0.0
    
    # Diversification effectiveness
    diversification_ratio: float = 1.0
    correlation_breakdown_impact: float = 0.0
    
    def add_result(self, result: StressTestResult):
        """Add a stress test result to the suite"""
        self.scenario_results.append(result)
        
        # Update aggregate metrics
        if abs(result.relative_loss) > abs(self.worst_case_loss):
            self.worst_case_loss = result.relative_loss
            self.worst_case_scenario = result.scenario_name
        
        # Update average loss
        total_loss = sum(r.relative_loss for r in self.scenario_results)
        self.average_loss = total_loss / len(self.scenario_results)
        
        # Update tail risk scenarios (losses > 10%)
        if abs(result.relative_loss) > 0.10:
            if result.scenario_name not in self.tail_risk_scenarios:
                self.tail_risk_scenarios.append(result.scenario_name)


class ScenarioBasedStressTester:
    """Scenario-based stress testing implementation"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def run_stress_test(self,
                            portfolio_positions: List[Any],
                            scenario: StressScenarioDefinition,
                            **kwargs) -> StressTestResult:
        """Run scenario-based stress test"""
        try:
            # Calculate base portfolio value
            base_value = sum(pos.market_value for pos in portfolio_positions)
            
            # Apply stress shocks
            stressed_positions = await self._apply_stress_shocks(
                portfolio_positions, scenario.shocks
            )
            
            # Calculate stressed portfolio value
            stressed_value = sum(pos.market_value for pos in stressed_positions)
            
            # Calculate impacts
            absolute_loss = stressed_value - base_value
            relative_loss = absolute_loss / base_value if base_value > 0 else 0
            
            # Calculate asset-level impacts
            asset_impacts = {}
            for base_pos, stressed_pos in zip(portfolio_positions, stressed_positions):
                impact = (stressed_pos.market_value - base_pos.market_value) / base_pos.market_value
                asset_impacts[base_pos.symbol] = impact
            
            # Calculate sector impacts
            sector_impacts = self._calculate_sector_impacts(portfolio_positions, stressed_positions)
            
            # Estimate recovery time
            recovery_time = self._estimate_recovery_time(scenario, relative_loss)
            
            return StressTestResult(
                scenario_name=scenario.name,
                stress_type=StressTestType.SCENARIO_BASED,
                portfolio_id=kwargs.get('portfolio_id', 'unknown'),
                base_portfolio_value=base_value,
                stressed_portfolio_value=stressed_value,
                absolute_loss=absolute_loss,
                relative_loss=relative_loss,
                asset_impacts=asset_impacts,
                sector_impacts=sector_impacts,
                scenario_definition=scenario,
                recovery_time_estimate=recovery_time,
                diagnostics={
                    'shocks_applied': len(scenario.shocks),
                    'simultaneous_shocks': scenario.is_simultaneous
                }
            )
            
        except Exception as e:
            self.logger.error(f"Scenario-based stress test failed: {e}")
            raise
    
    async def _apply_stress_shocks(self, positions: List[Any], shocks: List[StressShock]) -> List[Any]:
        """Apply stress shocks to portfolio positions"""
        stressed_positions = [self._copy_position(pos) for pos in positions]
        
        for shock in shocks:
            if shock.factor == RiskFactor.EQUITY_MARKET:
                stressed_positions = self._apply_equity_shock(stressed_positions, shock)
            elif shock.factor == RiskFactor.VOLATILITY:
                stressed_positions = self._apply_volatility_shock(stressed_positions, shock)
            elif shock.factor == RiskFactor.LIQUIDITY:
                stressed_positions = self._apply_liquidity_shock(stressed_positions, shock)
        
        return stressed_positions
    
    def _copy_position(self, position):
        """Create a copy of position for stress testing"""
        class StressedPosition:
            def __init__(self, original):
                self.symbol = original.symbol
                self.quantity = getattr(original, 'quantity', 100)
                self.current_price = getattr(original, 'current_price', 100.0)
                self.market_value = getattr(original, 'market_value', self.quantity * self.current_price)
                self.sector = getattr(original, 'sector', 'Unknown')
        
        return StressedPosition(position)
    
    def _apply_equity_shock(self, positions, shock):
        """Apply equity market shock"""
        for pos in positions:
            if shock.affected_assets is None or pos.symbol in shock.affected_assets:
                if shock.shock_type == "relative":
                    pos.current_price *= (1 + shock.magnitude)
                elif shock.shock_type == "absolute":
                    pos.current_price += shock.magnitude
                pos.market_value = pos.quantity * pos.current_price
        return positions
    
    def _apply_volatility_shock(self, positions, shock):
        """Apply volatility shock"""
        for pos in positions:
            if 'option' in pos.symbol.lower():
                pos.current_price *= (1 + shock.magnitude * 0.5)
                pos.market_value = pos.quantity * pos.current_price
        return positions
    
    def _apply_liquidity_shock(self, positions, shock):
        """Apply liquidity shock"""
        for pos in positions:
            liquidity_discount = abs(shock.magnitude) * 0.1
            pos.market_value *= (1 - liquidity_discount)
        return positions
    
    def _calculate_sector_impacts(self, base_positions, stressed_positions):
        """Calculate sector-level impacts"""
        sector_base = defaultdict(float)
        sector_stressed = defaultdict(float)
        
        for base_pos, stressed_pos in zip(base_positions, stressed_positions):
            sector = getattr(base_pos, 'sector', 'Unknown')
            sector_base[sector] += base_pos.market_value
            sector_stressed[sector] += stressed_pos.market_value
        
        sector_impacts = {}
        for sector in sector_base:
            if sector_base[sector] > 0:
                impact = (sector_stressed[sector] - sector_base[sector]) / sector_base[sector]
                sector_impacts[sector] = impact
        
        return sector_impacts
    
    def _estimate_recovery_time(self, scenario, relative_loss):
        """Estimate recovery time based on scenario and loss magnitude"""
        base_recovery = {
            "low": 30,
            "medium": 90,
            "high": 180,
            "extreme": 365
        }
        
        severity_multiplier = max(1.0, abs(relative_loss) * 10)
        return int(base_recovery.get(scenario.severity, 90) * severity_multiplier)


class HistoricalStressTester:
    """Historical stress testing implementation"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.historical_scenarios = self._load_historical_scenarios()
    
    async def run_stress_test(self,
                            portfolio_positions: List[Any],
                            scenario: StressScenarioDefinition,
                            **kwargs) -> StressTestResult:
        """Run historical stress test"""
        try:
            historical_data = kwargs.get('historical_data', {})
            
            if not historical_data:
                historical_data = self._get_predefined_historical_data(scenario.name)
            
            base_value = sum(pos.market_value for pos in portfolio_positions)
            
            stressed_positions = await self._apply_historical_returns(
                portfolio_positions, historical_data
            )
            
            stressed_value = sum(pos.market_value for pos in stressed_positions)
            
            absolute_loss = stressed_value - base_value
            relative_loss = absolute_loss / base_value if base_value > 0 else 0
            
            stressed_var = self._calculate_historical_var(historical_data)
            max_drawdown = self._calculate_max_drawdown(historical_data)
            
            return StressTestResult(
                scenario_name=scenario.name,
                stress_type=StressTestType.HISTORICAL,
                portfolio_id=kwargs.get('portfolio_id', 'unknown'),
                base_portfolio_value=base_value,
                stressed_portfolio_value=stressed_value,
                absolute_loss=absolute_loss,
                relative_loss=relative_loss,
                stressed_var=stressed_var,
                stressed_max_drawdown=max_drawdown,
                scenario_definition=scenario,
                diagnostics={
                    'historical_period': scenario.historical_date,
                    'data_points': len(historical_data)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Historical stress test failed: {e}")
            raise
    
    def _load_historical_scenarios(self):
        """Load predefined historical scenarios"""
        return {
            "Financial Crisis 2008": {
                'start_date': datetime(2008, 9, 15),
                'end_date': datetime(2009, 3, 9),
                'equity_return': -0.57,
                'credit_spread_change': 0.06,
                'volatility_increase': 2.5
            },
            "COVID-19 Pandemic": {
                'start_date': datetime(2020, 2, 19),
                'end_date': datetime(2020, 3, 23),
                'equity_return': -0.34,
                'credit_spread_change': 0.04,
                'volatility_increase': 3.0
            }
        }
    
    def _get_predefined_historical_data(self, scenario_name):
        """Get predefined historical data for scenario"""
        return self.historical_scenarios.get(scenario_name, {})
    
    async def _apply_historical_returns(self, positions, historical_data):
        """Apply historical returns to positions"""
        stressed_positions = []
        
        for pos in positions:
            stressed_pos = self._copy_position(pos)
            
            if 'equity_return' in historical_data:
                stressed_pos.current_price *= (1 + historical_data['equity_return'])
                stressed_pos.market_value = stressed_pos.quantity * stressed_pos.current_price
            
            stressed_positions.append(stressed_pos)
        
        return stressed_positions
    
    def _copy_position(self, position):
        """Create a copy of position for stress testing"""
        class StressedPosition:
            def __init__(self, original):
                self.symbol = original.symbol
                self.quantity = getattr(original, 'quantity', 100)
                self.current_price = getattr(original, 'current_price', 100.0)
                self.market_value = getattr(original, 'market_value', self.quantity * self.current_price)
                self.sector = getattr(original, 'sector', 'Unknown')
        
        return StressedPosition(position)
    
    def _calculate_historical_var(self, historical_data):
        """Calculate VaR based on historical data"""
        if 'equity_return' in historical_data:
            return abs(historical_data['equity_return']) * 0.95
        return None
    
    def _calculate_max_drawdown(self, historical_data):
        """Calculate maximum drawdown from historical data"""
        if 'equity_return' in historical_data:
            return abs(historical_data['equity_return'])
        return None


class MonteCarloStressTester:
    """Monte Carlo stress testing implementation"""
    
    def __init__(self, num_simulations: int = 10000):
        self.logger = logging.getLogger(__name__)
        self.num_simulations = num_simulations
        self.random_state = np.random.RandomState(42)
    
    async def run_stress_test(self,
                            portfolio_positions: List[Any],
                            scenario: StressScenarioDefinition,
                            **kwargs) -> StressTestResult:
        """Run Monte Carlo stress test"""
        try:
            base_value = sum(pos.market_value for pos in portfolio_positions)
            
            simulation_results = await self._run_monte_carlo_simulations(
                portfolio_positions, scenario, **kwargs
            )
            
            portfolio_values = [result['portfolio_value'] for result in simulation_results]
            losses = [(base_value - pv) / base_value for pv in portfolio_values]
            
            var_95 = np.percentile(losses, 95)
            var_99 = np.percentile(losses, 99)
            expected_shortfall = np.mean([loss for loss in losses if loss >= var_95])
            
            avg_stressed_value = np.mean(portfolio_values)
            absolute_loss = avg_stressed_value - base_value
            relative_loss = absolute_loss / base_value if base_value > 0 else 0
            
            return StressTestResult(
                scenario_name=scenario.name,
                stress_type=StressTestType.MONTE_CARLO,
                portfolio_id=kwargs.get('portfolio_id', 'unknown'),
                base_portfolio_value=base_value,
                stressed_portfolio_value=avg_stressed_value,
                absolute_loss=absolute_loss,
                relative_loss=relative_loss,
                stressed_var=var_95,
                stressed_expected_shortfall=expected_shortfall,
                scenario_definition=scenario,
                diagnostics={
                    'num_simulations': self.num_simulations,
                    'var_99': var_99,
                    'min_loss': min(losses),
                    'max_loss': max(losses),
                    'std_loss': np.std(losses)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Monte Carlo stress test failed: {e}")
            raise
    
    async def _run_monte_carlo_simulations(self, positions, scenario, **kwargs):
        """Run Monte Carlo simulations"""
        results = []
        
        volatilities = self._extract_volatilities(positions)
        correlation_matrix = kwargs.get('correlation_matrix', np.eye(len(positions)))
        
        for i in range(self.num_simulations):
            random_shocks = self._generate_correlated_shocks(volatilities, correlation_matrix)
            stressed_positions = self._apply_monte_carlo_shocks(positions, random_shocks)
            portfolio_value = sum(pos.market_value for pos in stressed_positions)
            
            results.append({
                'simulation': i,
                'portfolio_value': portfolio_value,
                'shocks': random_shocks
            })
        
        return results
    
    def _extract_volatilities(self, positions):
        """Extract volatilities from positions"""
        volatilities = []
        for pos in positions:
            vol = getattr(pos, 'volatility', 0.20)
            volatilities.append(vol)
        return np.array(volatilities)
    
    def _generate_correlated_shocks(self, volatilities, correlation_matrix):
        """Generate correlated random shocks"""
        independent_shocks = self.random_state.normal(0, 1, len(volatilities))
        
        try:
            chol = np.linalg.cholesky(correlation_matrix)
            correlated_shocks = chol @ independent_shocks
        except np.linalg.LinAlgError:
            correlated_shocks = independent_shocks
        
        return correlated_shocks * volatilities
    
    def _apply_monte_carlo_shocks(self, positions, shocks):
        """Apply Monte Carlo shocks to positions"""
        stressed_positions = []
        
        for i, pos in enumerate(positions):
            stressed_pos = self._copy_position(pos)
            
            shock = shocks[i] if i < len(shocks) else 0
            stressed_pos.current_price *= (1 + shock)
            stressed_pos.market_value = stressed_pos.quantity * stressed_pos.current_price
            
            stressed_positions.append(stressed_pos)
        
        return stressed_positions
    
    def _copy_position(self, position):
        """Create a copy of position for stress testing"""
        class StressedPosition:
            def __init__(self, original):
                self.symbol = original.symbol
                self.quantity = getattr(original, 'quantity', 100)
                self.current_price = getattr(original, 'current_price', 100.0)
                self.market_value = getattr(original, 'market_value', self.quantity * self.current_price)
                self.sector = getattr(original, 'sector', 'Unknown')
                self.volatility = getattr(original, 'volatility', 0.20)
        
        return StressedPosition(position)


class StressTestingFramework:
    """Main stress testing framework"""
    
    def __init__(self, enable_real_time: bool = False):
        self.logger = logging.getLogger(__name__)
        self.enable_real_time = enable_real_time
        
        # Initialize stress testers
        self.scenario_tester = ScenarioBasedStressTester()
        self.historical_tester = HistoricalStressTester()
        self.monte_carlo_tester = MonteCarloStressTester()
        
        # Stress test results storage
        self.test_results: Dict[str, StressTestSuite] = {}
        self.active_portfolios: Dict[str, List[Any]] = {}
        
        # Real-time monitoring
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.monitoring_interval = 300  # 5 minutes
        
        # Performance metrics
        self.metrics = {
            'tests_completed': 0,
            'tests_failed': 0,
            'avg_test_time_ms': 0.0,
            'active_portfolios': 0
        }
        
        # Predefined scenarios
        self.predefined_scenarios = self._create_predefined_scenarios()
    
    async def start(self):
        """Start the stress testing framework"""
        self.logger.info("Starting Stress Testing Framework...")
        
        if self.enable_real_time:
            await self._start_real_time_monitoring()
        
        self.logger.info("✅ Stress Testing Framework started successfully")
    
    async def stop(self):
        """Stop the stress testing framework"""
        self.logger.info("Stopping Stress Testing Framework...")
        
        if self.monitoring_active:
            await self._stop_real_time_monitoring()
        
        self.logger.info("✅ Stress Testing Framework stopped")
    
    async def run_stress_test_suite(self,
                                  portfolio_id: str,
                                  portfolio_positions: List[Any],
                                  scenarios: Optional[List[StressScenarioDefinition]] = None,
                                  test_types: Optional[List[StressTestType]] = None) -> StressTestSuite:
        """Run comprehensive stress test suite"""
        start_time = time.time()
        
        try:
            if scenarios is None:
                scenarios = list(self.predefined_scenarios.values())
            
            if test_types is None:
                test_types = [StressTestType.SCENARIO_BASED, StressTestType.HISTORICAL, StressTestType.MONTE_CARLO]
            
            base_value = sum(pos.market_value for pos in portfolio_positions)
            test_suite = StressTestSuite(
                portfolio_id=portfolio_id,
                test_date=datetime.now(),
                base_portfolio_value=base_value
            )
            
            for scenario in scenarios:
                for test_type in test_types:
                    try:
                        result = await self._run_single_stress_test(
                            portfolio_positions, scenario, test_type, portfolio_id
                        )
                        test_suite.add_result(result)
                        
                    except Exception as e:
                        self.logger.error(f"Stress test failed for {scenario.name} ({test_type}): {e}")
                        self.metrics['tests_failed'] += 1
            
            self._calculate_suite_metrics(test_suite)
            
            self.test_results[portfolio_id] = test_suite
            self.active_portfolios[portfolio_id] = portfolio_positions
            
            self.metrics['tests_completed'] += len(test_suite.scenario_results)
            self.metrics['active_portfolios'] = len(self.active_portfolios)
            
            execution_time = (time.time() - start_time) * 1000
            self.metrics['avg_test_time_ms'] = (
                (self.metrics['avg_test_time_ms'] * (self.metrics['tests_completed'] - len(test_suite.scenario_results)) + 
                 execution_time) / self.metrics['tests_completed']
            )
            
            self.logger.info(f"✅ Stress test suite completed for {portfolio_id}")
            return test_suite
            
        except Exception as e:
            self.logger.error(f"Stress test suite failed: {e}")
            raise
    
    async def _run_single_stress_test(self,
                                    portfolio_positions: List[Any],
                                    scenario: StressScenarioDefinition,
                                    test_type: StressTestType,
                                    portfolio_id: str) -> StressTestResult:
        """Run a single stress test"""
        if test_type == StressTestType.SCENARIO_BASED:
            return await self.scenario_tester.run_stress_test(
                portfolio_positions, scenario, portfolio_id=portfolio_id
            )
        elif test_type == StressTestType.HISTORICAL:
            return await self.historical_tester.run_stress_test(
                portfolio_positions, scenario, portfolio_id=portfolio_id
            )
        elif test_type == StressTestType.MONTE_CARLO:
            return await self.monte_carlo_tester.run_stress_test(
                portfolio_positions, scenario, portfolio_id=portfolio_id
            )
        else:
            raise ValueError(f"Unsupported stress test type: {test_type}")
    
    def _calculate_suite_metrics(self, test_suite: StressTestSuite):
        """Calculate additional metrics for the test suite"""
        if not test_suite.scenario_results:
            return
        
        extreme_losses = [r for r in test_suite.scenario_results if abs(r.relative_loss) > 0.20]
        test_suite.systemic_risk_score = len(extreme_losses) / len(test_suite.scenario_results)
        
        individual_risks = [abs(r.relative_loss) for r in test_suite.scenario_results]
        portfolio_risk = np.std(individual_risks)
        avg_individual_risk = np.mean(individual_risks)
        test_suite.diversification_ratio = avg_individual_risk / portfolio_risk if portfolio_risk > 0 else 1.0
        
        correlation_results = [r for r in test_suite.scenario_results 
                             if any(shock.factor == RiskFactor.CORRELATION 
                                   for shock in (r.scenario_definition.shocks if r.scenario_definition else []))]
        if correlation_results:
            test_suite.correlation_breakdown_impact = np.mean([abs(r.relative_loss) for r in correlation_results])
    
    def _create_predefined_scenarios(self) -> Dict[str, StressScenarioDefinition]:
        """Create predefined stress scenarios"""
        scenarios = {}
        
        # Financial Crisis 2008
        scenarios['financial_crisis_2008'] = StressScenarioDefinition(
            name="Financial Crisis 2008",
            description="Severe market stress similar to 2008 financial crisis",
            shocks=[
                StressShock(RiskFactor.EQUITY_MARKET, "relative", -0.40, "Equity market crash"),
                StressShock(RiskFactor.VOLATILITY, "relative", 2.5, "Volatility spike"),
                StressShock(RiskFactor.LIQUIDITY, "relative", 0.30, "Liquidity crisis")
            ],
            historical_date=datetime(2008, 9, 15),
            severity="extreme"
        )
        
        # COVID-19 Pandemic
        scenarios['covid_19_pandemic'] = StressScenarioDefinition(
            name="COVID-19 Pandemic",
            description="Market stress from pandemic-induced economic shutdown",
            shocks=[
                StressShock(RiskFactor.EQUITY_MARKET, "relative", -0.30, "Market selloff"),
                StressShock(RiskFactor.VOLATILITY, "relative", 3.0, "Extreme volatility"),
                StressShock(RiskFactor.CORRELATION, "relative", 0.50, "Correlation breakdown")
            ],
            historical_date=datetime(2020, 2, 19),
            severity="high"
        )
        
        # Interest Rate Shock
        scenarios['interest_rate_shock'] = StressScenarioDefinition(
            name="Interest Rate Shock",
            description="Sudden 200bp increase in interest rates",
            shocks=[
                StressShock(RiskFactor.INTEREST_RATES, "absolute", 0.02, "Rate increase"),
                StressShock(RiskFactor.EQUITY_MARKET, "relative", -0.15, "Equity impact")
            ],
            severity="medium"
        )
        
        return scenarios
    
    async def _start_real_time_monitoring(self):
        """Start real-time stress test monitoring"""
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_worker, daemon=True)
        self.monitoring_thread.start()
        self.logger.info("Real-time stress test monitoring started")
    
    async def _stop_real_time_monitoring(self):
        """Stop real-time stress test monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5.0)
        self.logger.info("Real-time stress test monitoring stopped")
    
    def _monitoring_worker(self):
        """Background worker for real-time monitoring"""
        while self.monitoring_active:
            try:
                for portfolio_id, positions in self.active_portfolios.items():
                    asyncio.run(self._run_monitoring_stress_test(portfolio_id, positions))
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Monitoring worker error: {e}")
                time.sleep(60)
    
    async def _run_monitoring_stress_test(self, portfolio_id: str, positions: List[Any]):
        """Run stress test for monitoring"""
        try:
            key_scenarios = [
                self.predefined_scenarios['financial_crisis_2008'],
                self.predefined_scenarios['covid_19_pandemic']
            ]
            
            for scenario in key_scenarios:
                result = await self.scenario_tester.run_stress_test(
                    positions, scenario, portfolio_id=portfolio_id
                )
                
                if abs(result.relative_loss) > 0.15:
                    self.logger.warning(
                        f"🚨 STRESS TEST ALERT: {portfolio_id} - {scenario.name} "
                        f"shows {result.relative_loss:.2%} loss"
                    )
        
        except Exception as e:
            self.logger.error(f"Monitoring stress test failed for {portfolio_id}: {e}")
    
    def get_stress_test_results(self, portfolio_id: str) -> Optional[StressTestSuite]:
        """Get stress test results for a portfolio"""
        return self.test_results.get(portfolio_id)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get stress testing framework metrics"""
        return self.metrics.copy()
    
    def create_custom_scenario(self,
                             name: str,
                             description: str,
                             shocks: List[StressShock],
                             severity: str = "medium") -> StressScenarioDefinition:
        """Create a custom stress scenario"""
        return StressScenarioDefinition(
            name=name,
            description=description,
            shocks=shocks,
            severity=severity
        )
    
    def generate_stress_test_report(self, portfolio_id: str) -> Dict[str, Any]:
        """Generate comprehensive stress test report"""
        test_suite = self.test_results.get(portfolio_id)
        if not test_suite:
            return {"error": f"No stress test results found for {portfolio_id}"}
        
        report = {
            "portfolio_id": portfolio_id,
            "test_date": test_suite.test_date.isoformat(),
            "base_portfolio_value": test_suite.base_portfolio_value,
            "summary": {
                "worst_case_loss": test_suite.worst_case_loss,
                "worst_case_scenario": test_suite.worst_case_scenario,
                "average_loss": test_suite.average_loss,
                "systemic_risk_score": test_suite.systemic_risk_score,
                "diversification_ratio": test_suite.diversification_ratio,
                "tail_risk_scenarios": test_suite.tail_risk_scenarios
            },
            "scenario_results": []
        }
        
        for result in test_suite.scenario_results:
            scenario_report = {
                "scenario_name": result.scenario_name,
                "stress_type": result.stress_type.value,
                "relative_loss": result.relative_loss,
                "absolute_loss": result.absolute_loss,
                "stressed_var": result.stressed_var,
                "recovery_time_estimate": result.recovery_time_estimate,
                "sector_impacts": result.sector_impacts
            }
            report["scenario_results"].append(scenario_report)
        
        return report


# Global stress testing framework instance
_stress_testing_framework: Optional[StressTestingFramework] = None


def get_stress_testing_framework(enable_real_time: bool = False) -> StressTestingFramework:
    """Get or create the global stress testing framework instance"""
    global _stress_testing_framework
    
    if _stress_testing_framework is None:
        _stress_testing_framework = StressTestingFramework(enable_real_time=enable_real_time)
    
    return _stress_testing_framework


# Convenience functions
async def run_stress_test(portfolio_id: str,
                         portfolio_positions: List[Any],
                         scenarios: Optional[List[StressScenarioDefinition]] = None) -> StressTestSuite:
    """Convenience function to run stress tests"""
    framework = get_stress_testing_framework()
    await framework.start()
    
    try:
        return await framework.run_stress_test_suite(portfolio_id, portfolio_positions, scenarios)
    finally:
        await framework.stop()


def create_stress_shock(factor: RiskFactor,
                       shock_type: str,
                       magnitude: float,
                       description: str = "") -> StressShock:
    """Convenience function to create stress shocks"""
    return StressShock(
        factor=factor,
        shock_type=shock_type,
        magnitude=magnitude,
        description=description
    )


def create_stress_scenario(name: str,
                          description: str,
                          shocks: List[StressShock],
                          severity: str = "medium") -> StressScenarioDefinition:
    """Convenience function to create stress scenarios"""
    return StressScenarioDefinition(
        name=name,
        description=description,
        shocks=shocks,
        severity=severity
    )