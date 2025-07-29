"""
Dynamic Hedging System
Correlation-based hedging, delta-neutral hedging for options, currency hedging,
and hedging effectiveness measurement with real-time risk management
"""

import asyncio
import time
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
from abc import ABC, abstractmethod
import warnings

# Suppress numpy warnings for cleaner output
warnings.filterwarnings('ignore', category=RuntimeWarning)

try:
    from scipy import stats, optimize
    from scipy.linalg import inv
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    stats = None
    optimize = None


class HedgeType(Enum):
    """Types of hedging strategies"""
    CORRELATION_BASED = "correlation_based"
    DELTA_NEUTRAL = "delta_neutral"
    CURRENCY_HEDGE = "currency_hedge"
    BETA_HEDGE = "beta_hedge"
    VOLATILITY_HEDGE = "volatility_hedge"
    SECTOR_HEDGE = "sector_hedge"


class HedgeStatus(Enum):
    """Hedge status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    REBALANCING = "rebalancing"
    EXPIRED = "expired"
    ERROR = "error"


@dataclass
class HedgeInstrument:
    """Hedge instrument definition"""
    symbol: str
    instrument_type: str  # 'stock', 'option', 'future', 'etf', 'currency'
    hedge_ratio: float
    current_position: float
    target_position: float
    
    # Option-specific fields
    option_type: Optional[str] = None  # 'call', 'put'
    strike: Optional[float] = None
    expiry: Optional[datetime] = None
    
    # Greeks for options
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    
    # Currency-specific fields
    base_currency: Optional[str] = None
    quote_currency: Optional[str] = None
    
    # Metadata
    last_updated: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HedgeStrategy:
    """Hedge strategy definition"""
    strategy_id: str
    hedge_type: HedgeType
    target_portfolio: List[str]  # Symbols to hedge
    hedge_instruments: List[HedgeInstrument]
    
    # Strategy parameters
    rebalance_threshold: float = 0.05  # 5% deviation triggers rebalance
    rebalance_frequency_minutes: int = 60  # Hourly rebalancing
    max_hedge_ratio: float = 1.0
    min_hedge_ratio: float = 0.0
    
    # Risk parameters
    max_tracking_error: float = 0.02  # 2% max tracking error
    confidence_level: float = 0.95
    
    # Status and metrics
    status: HedgeStatus = HedgeStatus.INACTIVE
    effectiveness_score: float = 0.0
    last_rebalance: Optional[datetime] = None
    
    # Performance tracking
    hedge_pnl: float = 0.0
    tracking_error: float = 0.0
    hedge_ratio_history: List[Tuple[datetime, float]] = field(default_factory=list)


@dataclass
class HedgeRecommendation:
    """Hedge recommendation"""
    strategy_id: str
    action: str  # 'create', 'adjust', 'close'
    hedge_instruments: List[HedgeInstrument]
    expected_effectiveness: float
    cost_estimate: float
    risk_reduction: float
    rationale: str
    confidence: float
    
    # Implementation details
    execution_priority: str = "medium"  # 'low', 'medium', 'high', 'urgent'
    estimated_execution_time: int = 300  # seconds
    market_impact_estimate: float = 0.0


@dataclass
class HedgePerformanceMetrics:
    """Hedge performance metrics"""
    strategy_id: str
    measurement_period: str
    
    # Effectiveness metrics
    hedge_effectiveness: float  # 0-1 scale
    tracking_error: float
    correlation_with_target: float
    
    # Financial metrics
    hedge_cost: float
    hedge_pnl: float
    net_hedge_benefit: float
    
    # Risk metrics
    risk_reduction_achieved: float
    var_reduction: float
    volatility_reduction: float
    
    # Operational metrics
    rebalance_frequency: int
    execution_slippage: float
    
    # Time series data
    daily_effectiveness: List[Tuple[datetime, float]] = field(default_factory=list)
    hedge_ratio_evolution: List[Tuple[datetime, float]] = field(default_factory=list)


class HedgeCalculator(ABC):
    """Abstract base class for hedge calculators"""
    
    @abstractmethod
    async def calculate_hedge_ratio(self, 
                                  target_positions: List[Any],
                                  hedge_instruments: List[HedgeInstrument],
                                  **kwargs) -> Dict[str, float]:
        """Calculate optimal hedge ratios"""
        pass
    
    @abstractmethod
    def estimate_hedge_effectiveness(self,
                                   hedge_ratio: float,
                                   correlation: float,
                                   **kwargs) -> float:
        """Estimate hedge effectiveness"""
        pass


class CorrelationBasedHedgeCalculator(HedgeCalculator):
    """Correlation-based hedging calculator"""
    
    def __init__(self, lookback_days: int = 252):
        self.lookback_days = lookback_days
        self.logger = logging.getLogger(__name__)
    
    async def calculate_hedge_ratio(self,
                                  target_positions: List[Any],
                                  hedge_instruments: List[HedgeInstrument],
                                  **kwargs) -> Dict[str, float]:
        """Calculate correlation-based hedge ratios"""
        try:
            # Get historical price data
            target_returns = await self._get_returns_data(
                [pos.symbol for pos in target_positions]
            )
            hedge_returns = await self._get_returns_data(
                [inst.symbol for inst in hedge_instruments]
            )
            
            hedge_ratios = {}
            
            for hedge_inst in hedge_instruments:
                # Calculate optimal hedge ratio using regression
                if hedge_inst.symbol in hedge_returns.columns:
                    hedge_ratio = self._calculate_optimal_ratio(
                        target_returns, 
                        hedge_returns[hedge_inst.symbol]
                    )
                    hedge_ratios[hedge_inst.symbol] = hedge_ratio
                else:
                    hedge_ratios[hedge_inst.symbol] = 0.0
            
            return hedge_ratios
            
        except Exception as e:
            self.logger.error(f"Correlation hedge calculation failed: {e}")
            return {inst.symbol: 0.0 for inst in hedge_instruments}
    
    def estimate_hedge_effectiveness(self,
                                   hedge_ratio: float,
                                   correlation: float,
                                   **kwargs) -> float:
        """Estimate hedge effectiveness using correlation"""
        # Hedge effectiveness = R² from regression
        return correlation ** 2 * (hedge_ratio ** 2) / (1 + hedge_ratio ** 2)
    
    def _calculate_optimal_ratio(self, target_returns: pd.DataFrame, 
                               hedge_returns: pd.Series) -> float:
        """Calculate optimal hedge ratio using OLS regression"""
        try:
            # Portfolio returns (weighted average of target positions)
            portfolio_returns = target_returns.mean(axis=1)
            
            # Remove NaN values
            valid_data = pd.concat([portfolio_returns, hedge_returns], axis=1).dropna()
            
            if len(valid_data) < 30:  # Minimum data requirement
                return 0.0
            
            # OLS regression: portfolio_returns = alpha + beta * hedge_returns
            X = valid_data.iloc[:, 1].values.reshape(-1, 1)  # hedge returns
            y = valid_data.iloc[:, 0].values  # portfolio returns
            
            # Calculate beta (hedge ratio)
            covariance = np.cov(y, X.flatten())[0, 1]
            variance = np.var(X.flatten())
            
            if variance > 0:
                hedge_ratio = -covariance / variance  # Negative for hedging
                return np.clip(hedge_ratio, -2.0, 2.0)  # Reasonable bounds
            else:
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Optimal ratio calculation failed: {e}")
            return 0.0
    
    async def _get_returns_data(self, symbols: List[str]) -> pd.DataFrame:
        """Get historical returns data for symbols"""
        # Placeholder - in real implementation, fetch from data provider
        dates = pd.date_range(end=datetime.now(), periods=self.lookback_days, freq='D')
        
        returns_data = {}
        for symbol in symbols:
            # Generate synthetic returns for demonstration
            np.random.seed(hash(symbol) % 2**32)
            returns = np.random.normal(0.0005, 0.02, len(dates))  # Daily returns
            returns_data[symbol] = returns
        
        return pd.DataFrame(returns_data, index=dates)


class DeltaNeutralHedgeCalculator(HedgeCalculator):
    """Delta-neutral hedging calculator for options portfolios"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def calculate_hedge_ratio(self,
                                  target_positions: List[Any],
                                  hedge_instruments: List[HedgeInstrument],
                                  **kwargs) -> Dict[str, float]:
        """Calculate delta-neutral hedge ratios"""
        try:
            # Calculate portfolio delta
            portfolio_delta = self._calculate_portfolio_delta(target_positions)
            
            hedge_ratios = {}
            
            for hedge_inst in hedge_instruments:
                if hedge_inst.delta is not None:
                    # Calculate hedge ratio to neutralize delta
                    if hedge_inst.delta != 0:
                        hedge_ratio = -portfolio_delta / hedge_inst.delta
                        hedge_ratios[hedge_inst.symbol] = hedge_ratio
                    else:
                        hedge_ratios[hedge_inst.symbol] = 0.0
                else:
                    # For non-option instruments, assume delta = 1
                    hedge_ratios[hedge_inst.symbol] = -portfolio_delta
            
            return hedge_ratios
            
        except Exception as e:
            self.logger.error(f"Delta-neutral hedge calculation failed: {e}")
            return {inst.symbol: 0.0 for inst in hedge_instruments}
    
    def estimate_hedge_effectiveness(self,
                                   hedge_ratio: float,
                                   correlation: float,
                                   **kwargs) -> float:
        """Estimate delta-neutral hedge effectiveness"""
        # For delta-neutral hedging, effectiveness depends on gamma risk
        gamma = kwargs.get('gamma', 0.0)
        time_to_expiry = kwargs.get('time_to_expiry', 30) / 365.0  # Convert to years
        
        # Effectiveness decreases with gamma and time
        gamma_risk = abs(gamma) * time_to_expiry
        effectiveness = max(0.0, 1.0 - gamma_risk)
        
        return effectiveness
    
    def _calculate_portfolio_delta(self, positions: List[Any]) -> float:
        """Calculate total portfolio delta"""
        total_delta = 0.0
        
        for position in positions:
            position_delta = getattr(position, 'delta', 1.0)  # Default delta = 1 for stocks
            position_size = getattr(position, 'quantity', 0)
            
            total_delta += position_delta * position_size
        
        return total_delta


class CurrencyHedgeCalculator(HedgeCalculator):
    """Currency hedging calculator"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def calculate_hedge_ratio(self,
                                  target_positions: List[Any],
                                  hedge_instruments: List[HedgeInstrument],
                                  **kwargs) -> Dict[str, float]:
        """Calculate currency hedge ratios"""
        try:
            base_currency = kwargs.get('base_currency', 'USD')
            
            # Calculate currency exposure by currency
            currency_exposures = self._calculate_currency_exposure(
                target_positions, base_currency
            )
            
            hedge_ratios = {}
            
            for hedge_inst in hedge_instruments:
                currency_pair = f"{hedge_inst.base_currency}{hedge_inst.quote_currency}"
                
                if hedge_inst.base_currency in currency_exposures:
                    exposure = currency_exposures[hedge_inst.base_currency]
                    # Hedge ratio = exposure amount / hedge instrument notional
                    hedge_ratio = exposure / 100000  # Assuming 100k notional
                    hedge_ratios[hedge_inst.symbol] = hedge_ratio
                else:
                    hedge_ratios[hedge_inst.symbol] = 0.0
            
            return hedge_ratios
            
        except Exception as e:
            self.logger.error(f"Currency hedge calculation failed: {e}")
            return {inst.symbol: 0.0 for inst in hedge_instruments}
    
    def estimate_hedge_effectiveness(self,
                                   hedge_ratio: float,
                                   correlation: float,
                                   **kwargs) -> float:
        """Estimate currency hedge effectiveness"""
        # Currency hedging effectiveness is typically high (90%+) for direct hedges
        fx_volatility = kwargs.get('fx_volatility', 0.10)  # 10% annual vol
        hedge_coverage = min(1.0, abs(hedge_ratio))
        
        # Effectiveness decreases with FX volatility and incomplete coverage
        effectiveness = hedge_coverage * (1.0 - fx_volatility * 0.1)
        
        return max(0.0, min(1.0, effectiveness))
    
    def _calculate_currency_exposure(self, positions: List[Any], 
                                   base_currency: str) -> Dict[str, float]:
        """Calculate currency exposure by currency"""
        exposures = defaultdict(float)
        
        for position in positions:
            currency = getattr(position, 'currency', base_currency)
            market_value = getattr(position, 'market_value', 0.0)
            
            if currency != base_currency:
                exposures[currency] += market_value
        
        return dict(exposures)


class DynamicHedgingSystem:
    """Main dynamic hedging system"""
    
    def __init__(self, enable_real_time: bool = True):
        self.logger = logging.getLogger(__name__)
        self.enable_real_time = enable_real_time
        
        # Hedge calculators
        self.calculators = {
            HedgeType.CORRELATION_BASED: CorrelationBasedHedgeCalculator(),
            HedgeType.DELTA_NEUTRAL: DeltaNeutralHedgeCalculator(),
            HedgeType.CURRENCY_HEDGE: CurrencyHedgeCalculator()
        }
        
        # Active hedge strategies
        self.active_strategies: Dict[str, HedgeStrategy] = {}
        self.hedge_recommendations: Dict[str, List[HedgeRecommendation]] = {}
        
        # Performance tracking
        self.performance_metrics: Dict[str, HedgePerformanceMetrics] = {}
        
        # Real-time monitoring
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.rebalance_queue = asyncio.Queue()
        
        # System metrics
        self.metrics = {
            'active_strategies': 0,
            'total_hedge_pnl': 0.0,
            'avg_hedge_effectiveness': 0.0,
            'rebalances_completed': 0,
            'rebalances_failed': 0
        }
    
    async def start(self):
        """Start the dynamic hedging system"""
        self.logger.info("Starting Dynamic Hedging System...")
        
        if self.enable_real_time:
            await self._start_real_time_monitoring()
        
        self.logger.info("✅ Dynamic Hedging System started successfully")
    
    async def stop(self):
        """Stop the dynamic hedging system"""
        self.logger.info("Stopping Dynamic Hedging System...")
        
        if self.monitoring_active:
            await self._stop_real_time_monitoring()
        
        self.logger.info("✅ Dynamic Hedging System stopped")
    
    async def create_hedge_strategy(self,
                                  strategy_id: str,
                                  hedge_type: HedgeType,
                                  target_portfolio: List[Any],
                                  hedge_instruments: List[HedgeInstrument],
                                  **kwargs) -> HedgeStrategy:
        """Create a new hedge strategy"""
        try:
            # Calculate initial hedge ratios
            calculator = self.calculators[hedge_type]
            hedge_ratios = await calculator.calculate_hedge_ratio(
                target_portfolio, hedge_instruments, **kwargs
            )
            
            # Update hedge instruments with calculated ratios
            for instrument in hedge_instruments:
                if instrument.symbol in hedge_ratios:
                    instrument.hedge_ratio = hedge_ratios[instrument.symbol]
                    instrument.target_position = (
                        instrument.hedge_ratio * 
                        sum(getattr(pos, 'market_value', 0) for pos in target_portfolio)
                    )
            
            # Create hedge strategy
            strategy = HedgeStrategy(
                strategy_id=strategy_id,
                hedge_type=hedge_type,
                target_portfolio=[getattr(pos, 'symbol', str(pos)) for pos in target_portfolio],
                hedge_instruments=hedge_instruments,
                status=HedgeStatus.ACTIVE,
                last_rebalance=datetime.now()
            )
            
            # Calculate initial effectiveness
            strategy.effectiveness_score = await self._calculate_strategy_effectiveness(
                strategy, target_portfolio
            )
            
            # Store strategy
            self.active_strategies[strategy_id] = strategy
            self.metrics['active_strategies'] = len(self.active_strategies)
            
            self.logger.info(f"Created hedge strategy: {strategy_id}")
            return strategy
            
        except Exception as e:
            self.logger.error(f"Failed to create hedge strategy {strategy_id}: {e}")
            raise
    
    async def rebalance_hedge_strategy(self,
                                     strategy_id: str,
                                     current_portfolio: List[Any]) -> bool:
        """Rebalance an existing hedge strategy"""
        try:
            if strategy_id not in self.active_strategies:
                raise ValueError(f"Strategy {strategy_id} not found")
            
            strategy = self.active_strategies[strategy_id]
            strategy.status = HedgeStatus.REBALANCING
            
            # Recalculate hedge ratios
            calculator = self.calculators[strategy.hedge_type]
            new_hedge_ratios = await calculator.calculate_hedge_ratio(
                current_portfolio, strategy.hedge_instruments
            )
            
            # Update hedge instruments
            rebalance_needed = False
            for instrument in strategy.hedge_instruments:
                if instrument.symbol in new_hedge_ratios:
                    new_ratio = new_hedge_ratios[instrument.symbol]
                    
                    # Check if rebalance is needed
                    ratio_change = abs(new_ratio - instrument.hedge_ratio)
                    if ratio_change > strategy.rebalance_threshold:
                        instrument.hedge_ratio = new_ratio
                        instrument.target_position = (
                            new_ratio * 
                            sum(getattr(pos, 'market_value', 0) for pos in current_portfolio)
                        )
                        rebalance_needed = True
            
            if rebalance_needed:
                # Execute rebalance (placeholder - would integrate with order management)
                await self._execute_hedge_rebalance(strategy)
                
                strategy.last_rebalance = datetime.now()
                strategy.hedge_ratio_history.append(
                    (datetime.now(), strategy.hedge_instruments[0].hedge_ratio)
                )
                
                self.metrics['rebalances_completed'] += 1
                self.logger.info(f"Rebalanced hedge strategy: {strategy_id}")
            
            strategy.status = HedgeStatus.ACTIVE
            return rebalance_needed
            
        except Exception as e:
            self.logger.error(f"Failed to rebalance strategy {strategy_id}: {e}")
            if strategy_id in self.active_strategies:
                self.active_strategies[strategy_id].status = HedgeStatus.ERROR
            self.metrics['rebalances_failed'] += 1
            return False
    
    async def generate_hedge_recommendations(self,
                                           portfolio: List[Any],
                                           risk_tolerance: str = "medium") -> List[HedgeRecommendation]:
        """Generate hedge recommendations for a portfolio"""
        try:
            recommendations = []
            
            # Analyze portfolio risks
            portfolio_risks = await self._analyze_portfolio_risks(portfolio)
            
            # Generate recommendations for each risk type
            for risk_type, risk_level in portfolio_risks.items():
                if risk_level > 0.1:  # 10% risk threshold
                    recommendation = await self._generate_risk_specific_recommendation(
                        risk_type, risk_level, portfolio, risk_tolerance
                    )
                    if recommendation:
                        recommendations.append(recommendation)
            
            # Sort by expected effectiveness
            recommendations.sort(key=lambda x: x.expected_effectiveness, reverse=True)
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to generate hedge recommendations: {e}")
            return []
    
    async def measure_hedge_effectiveness(self,
                                        strategy_id: str,
                                        measurement_period_days: int = 30) -> HedgePerformanceMetrics:
        """Measure hedge effectiveness for a strategy"""
        try:
            if strategy_id not in self.active_strategies:
                raise ValueError(f"Strategy {strategy_id} not found")
            
            strategy = self.active_strategies[strategy_id]
            
            # Calculate performance metrics
            metrics = HedgePerformanceMetrics(
                strategy_id=strategy_id,
                measurement_period=f"{measurement_period_days}d"
            )
            
            # Get historical data for analysis
            end_date = datetime.now()
            start_date = end_date - timedelta(days=measurement_period_days)
            
            # Calculate hedge effectiveness
            metrics.hedge_effectiveness = await self._calculate_realized_effectiveness(
                strategy, start_date, end_date
            )
            
            # Calculate tracking error
            metrics.tracking_error = await self._calculate_tracking_error(
                strategy, start_date, end_date
            )
            
            # Calculate financial metrics
            metrics.hedge_pnl = strategy.hedge_pnl
            metrics.hedge_cost = await self._calculate_hedge_cost(strategy, measurement_period_days)
            metrics.net_hedge_benefit = metrics.hedge_pnl - metrics.hedge_cost
            
            # Calculate risk reduction
            metrics.risk_reduction_achieved = await self._calculate_risk_reduction(
                strategy, start_date, end_date
            )
            
            # Store metrics
            self.performance_metrics[strategy_id] = metrics
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to measure hedge effectiveness for {strategy_id}: {e}")
            raise
    
    async def _calculate_strategy_effectiveness(self,
                                              strategy: HedgeStrategy,
                                              target_portfolio: List[Any]) -> float:
        """Calculate initial strategy effectiveness"""
        try:
            calculator = self.calculators[strategy.hedge_type]
            
            # Calculate average correlation between target and hedge instruments
            correlations = []
            for instrument in strategy.hedge_instruments:
                # Placeholder correlation calculation
                correlation = 0.8  # Would calculate from historical data
                effectiveness = calculator.estimate_hedge_effectiveness(
                    instrument.hedge_ratio, correlation
                )
                correlations.append(effectiveness)
            
            return np.mean(correlations) if correlations else 0.0
            
        except Exception as e:
            self.logger.error(f"Failed to calculate strategy effectiveness: {e}")
            return 0.0
    
    async def _analyze_portfolio_risks(self, portfolio: List[Any]) -> Dict[str, float]:
        """Analyze portfolio risks to identify hedging opportunities"""
        risks = {}
        
        # Market risk (beta exposure)
        market_exposure = sum(getattr(pos, 'beta', 1.0) * getattr(pos, 'market_value', 0) 
                            for pos in portfolio)
        total_value = sum(getattr(pos, 'market_value', 0) for pos in portfolio)
        
        if total_value > 0:
            risks['market_risk'] = abs(market_exposure / total_value)
        
        # Currency risk
        base_currency = 'USD'  # Default base currency
        currency_exposure = 0.0
        for pos in portfolio:
            currency = getattr(pos, 'currency', base_currency)
            if currency != base_currency:
                currency_exposure += getattr(pos, 'market_value', 0)
        
        if total_value > 0:
            risks['currency_risk'] = currency_exposure / total_value
        
        # Sector concentration risk
        sector_exposures = defaultdict(float)
        for pos in portfolio:
            sector = getattr(pos, 'sector', 'Unknown')
            sector_exposures[sector] += getattr(pos, 'market_value', 0)
        
        if sector_exposures and total_value > 0:
            max_sector_exposure = max(sector_exposures.values()) / total_value
            risks['concentration_risk'] = max_sector_exposure
        
        return risks
    
    async def _generate_risk_specific_recommendation(self,
                                                   risk_type: str,
                                                   risk_level: float,
                                                   portfolio: List[Any],
                                                   risk_tolerance: str) -> Optional[HedgeRecommendation]:
        """Generate recommendation for specific risk type"""
        try:
            if risk_type == 'market_risk':
                return await self._generate_market_hedge_recommendation(
                    risk_level, portfolio, risk_tolerance
                )
            elif risk_type == 'currency_risk':
                return await self._generate_currency_hedge_recommendation(
                    risk_level, portfolio, risk_tolerance
                )
            elif risk_type == 'concentration_risk':
                return await self._generate_concentration_hedge_recommendation(
                    risk_level, portfolio, risk_tolerance
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to generate {risk_type} recommendation: {e}")
            return None
    
    async def _generate_market_hedge_recommendation(self,
                                                  risk_level: float,
                                                  portfolio: List[Any],
                                                  risk_tolerance: str) -> HedgeRecommendation:
        """Generate market hedge recommendation"""
        # Create hedge instrument (e.g., SPY short position)
        hedge_instrument = HedgeInstrument(
            symbol="SPY",
            instrument_type="etf",
            hedge_ratio=-risk_level * 0.8,  # 80% hedge ratio
            current_position=0.0,
            target_position=0.0
        )
        
        return HedgeRecommendation(
            strategy_id=f"market_hedge_{int(time.time())}",
            action="create",
            hedge_instruments=[hedge_instrument],
            expected_effectiveness=0.75,
            cost_estimate=0.001,  # 10 bps
            risk_reduction=risk_level * 0.6,  # 60% risk reduction
            rationale=f"High market exposure ({risk_level:.1%}) detected. Recommend SPY hedge.",
            confidence=0.8,
            execution_priority="medium"
        )
    
    async def _generate_currency_hedge_recommendation(self,
                                                    risk_level: float,
                                                    portfolio: List[Any],
                                                    risk_tolerance: str) -> HedgeRecommendation:
        """Generate currency hedge recommendation"""
        # Identify major currency exposures
        hedge_instrument = HedgeInstrument(
            symbol="EURUSD",
            instrument_type="currency",
            hedge_ratio=-risk_level,
            current_position=0.0,
            target_position=0.0,
            base_currency="EUR",
            quote_currency="USD"
        )
        
        return HedgeRecommendation(
            strategy_id=f"currency_hedge_{int(time.time())}",
            action="create",
            hedge_instruments=[hedge_instrument],
            expected_effectiveness=0.90,
            cost_estimate=0.0005,  # 5 bps
            risk_reduction=risk_level * 0.85,  # 85% risk reduction
            rationale=f"Significant currency exposure ({risk_level:.1%}) detected.",
            confidence=0.9,
            execution_priority="high"
        )
    
    async def _generate_concentration_hedge_recommendation(self,
                                                         risk_level: float,
                                                         portfolio: List[Any],
                                                         risk_tolerance: str) -> HedgeRecommendation:
        """Generate concentration hedge recommendation"""
        # Create diversification hedge instrument
        hedge_instrument = HedgeInstrument(
            symbol="VTI",  # Total market ETF
            instrument_type="etf",
            hedge_ratio=risk_level * 0.5,  # 50% hedge ratio
            current_position=0.0,
            target_position=0.0
        )
        
        return HedgeRecommendation(
            strategy_id=f"concentration_hedge_{int(time.time())}",
            action="create",
            hedge_instruments=[hedge_instrument],
            expected_effectiveness=0.60,
            cost_estimate=0.0008,  # 8 bps
            risk_reduction=risk_level * 0.4,  # 40% risk reduction
            rationale=f"High concentration risk ({risk_level:.1%}) detected. Recommend diversification.",
            confidence=0.7,
            execution_priority="medium"
        )
    
    async def _execute_hedge_rebalance(self, strategy: HedgeStrategy):
        """Execute hedge rebalance (placeholder for order management integration)"""
        # In real implementation, this would integrate with order management system
        for instrument in strategy.hedge_instruments:
            position_change = instrument.target_position - instrument.current_position
            if abs(position_change) > 0.01:  # Minimum trade size
                self.logger.info(
                    f"Rebalancing {instrument.symbol}: "
                    f"{instrument.current_position} -> {instrument.target_position}"
                )
                # Update current position (simulated execution)
                instrument.current_position = instrument.target_position
    
    async def _calculate_realized_effectiveness(self,
                                              strategy: HedgeStrategy,
                                              start_date: datetime,
                                              end_date: datetime) -> float:
        """Calculate realized hedge effectiveness"""
        # Placeholder calculation - would use actual P&L data
        return min(0.95, strategy.effectiveness_score * 1.1)
    
    async def _calculate_tracking_error(self,
                                      strategy: HedgeStrategy,
                                      start_date: datetime,
                                      end_date: datetime) -> float:
        """Calculate tracking error"""
        # Placeholder calculation
        return 0.02  # 2% tracking error
    
    async def _calculate_hedge_cost(self,
                                  strategy: HedgeStrategy,
                                  days: int) -> float:
        """Calculate hedge cost"""
        # Estimate based on bid-ask spreads, financing costs, etc.
        daily_cost_rate = 0.0001  # 1 bp per day
        total_notional = sum(abs(inst.target_position) for inst in strategy.hedge_instruments)
        return total_notional * daily_cost_rate * days
    
    async def _calculate_risk_reduction(self,
                                      strategy: HedgeStrategy,
                                      start_date: datetime,
                                      end_date: datetime) -> float:
        """Calculate achieved risk reduction"""
        # Placeholder calculation
        return strategy.effectiveness_score * 0.8
    
    async def _start_real_time_monitoring(self):
        """Start real-time hedge monitoring"""
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_worker, daemon=True)
        self.monitoring_thread.start()
        self.logger.info("Real-time hedge monitoring started")
    
    async def _stop_real_time_monitoring(self):
        """Stop real-time hedge monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5.0)
        self.logger.info("Real-time hedge monitoring stopped")
    
    def _monitoring_worker(self):
        """Background worker for hedge monitoring"""
        while self.monitoring_active:
            try:
                # Check all active strategies for rebalancing needs
                for strategy_id, strategy in self.active_strategies.items():
                    if strategy.status == HedgeStatus.ACTIVE:
                        # Check if rebalancing is needed
                        time_since_rebalance = (
                            datetime.now() - (strategy.last_rebalance or datetime.now())
                        ).total_seconds() / 60  # minutes
                        
                        if time_since_rebalance >= strategy.rebalance_frequency_minutes:
                            # Queue for rebalancing
                            asyncio.run(self.rebalance_queue.put(strategy_id))
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Monitoring worker error: {e}")
                time.sleep(60)
    
    def get_active_strategies(self) -> Dict[str, HedgeStrategy]:
        """Get all active hedge strategies"""
        return self.active_strategies.copy()
    
    def get_strategy_performance(self, strategy_id: str) -> Optional[HedgePerformanceMetrics]:
        """Get performance metrics for a strategy"""
        return self.performance_metrics.get(strategy_id)
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-level metrics"""
        # Update metrics
        self.metrics['active_strategies'] = len(self.active_strategies)
        self.metrics['total_hedge_pnl'] = sum(
            strategy.hedge_pnl for strategy in self.active_strategies.values()
        )
        
        if self.active_strategies:
            self.metrics['avg_hedge_effectiveness'] = np.mean([
                strategy.effectiveness_score for strategy in self.active_strategies.values()
            ])
        
        return self.metrics.copy()


# Global dynamic hedging system instance
_dynamic_hedging_system: Optional[DynamicHedgingSystem] = None


def get_dynamic_hedging_system(enable_real_time: bool = True) -> DynamicHedgingSystem:
    """Get or create the global dynamic hedging system instance"""
    global _dynamic_hedging_system
    
    if _dynamic_hedging_system is None:
        _dynamic_hedging_system = DynamicHedgingSystem(enable_real_time=enable_real_time)
    
    return _dynamic_hedging_system


# Convenience functions
async def create_correlation_hedge(strategy_id: str,
                                 target_portfolio: List[Any],
                                 hedge_symbols: List[str]) -> HedgeStrategy:
    """Convenience function to create correlation-based hedge"""
    hedging_system = get_dynamic_hedging_system()
    
    hedge_instruments = [
        HedgeInstrument(symbol=symbol, instrument_type="stock", hedge_ratio=0.0,
                       current_position=0.0, target_position=0.0)
        for symbol in hedge_symbols
    ]
    
    return await hedging_system.create_hedge_strategy(
        strategy_id=strategy_id,
        hedge_type=HedgeType.CORRELATION_BASED,
        target_portfolio=target_portfolio,
        hedge_instruments=hedge_instruments
    )


async def create_delta_neutral_hedge(strategy_id: str,
                                   options_portfolio: List[Any],
                                   underlying_symbol: str) -> HedgeStrategy:
    """Convenience function to create delta-neutral hedge"""
    hedging_system = get_dynamic_hedging_system()
    
    hedge_instrument = HedgeInstrument(
        symbol=underlying_symbol,
        instrument_type="stock",
        hedge_ratio=0.0,
        current_position=0.0,
        target_position=0.0,
        delta=1.0  # Stock has delta = 1
    )
    
    return await hedging_system.create_hedge_strategy(
        strategy_id=strategy_id,
        hedge_type=HedgeType.DELTA_NEUTRAL,
        target_portfolio=options_portfolio,
        hedge_instruments=[hedge_instrument]
    )


async def create_currency_hedge(strategy_id: str,
                              portfolio: List[Any],
                              currency_pairs: List[str]) -> HedgeStrategy:
    """Convenience function to create currency hedge"""
    hedging_system = get_dynamic_hedging_system()
    
    hedge_instruments = []
    for pair in currency_pairs:
        base_currency = pair[:3]
        quote_currency = pair[3:]
        
        hedge_instruments.append(HedgeInstrument(
            symbol=pair,
            instrument_type="currency",
            hedge_ratio=0.0,
            current_position=0.0,
            target_position=0.0,
            base_currency=base_currency,
            quote_currency=quote_currency
        ))
    
    return await hedging_system.create_hedge_strategy(
        strategy_id=strategy_id,
        hedge_type=HedgeType.CURRENCY_HEDGE,
        target_portfolio=portfolio,
        hedge_instruments=hedge_instruments,
        base_currency="USD"
    )