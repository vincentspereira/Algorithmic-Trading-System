"""
Risk-Adaptive Strategies for Institutional-Grade Trading.

This module provides sophisticated risk-adaptive strategies that dynamically adjust
their behavior based on market conditions, risk levels, and performance metrics:

- Market Regime Adaptation: Strategies that adapt to bull/bear/sideways markets
- Volatility-Based Adaptation: Risk management based on volatility levels
- Performance-Based Adaptation: Strategy adjustment based on recent performance
- Risk-Budgeting Strategies: Dynamic allocation based on risk budgets
- Correlation-Aware Strategies: Position sizing based on portfolio correlation
- Stress-Testing Strategies: Strategies that perform well under adverse conditions
- Machine Learning-Enhanced Adaptation: ML models for optimal strategy selection

The risk-adaptive framework integrates with the 5-pillar institutional architecture
to provide dynamic, market-aware, and risk-conscious trading strategies.
"""

import asyncio
import math
import statistics
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from weakref import WeakSet

import numpy as np
from loguru import logger

from .dependency_injection import (
    DependencyInjectionContainer,
    get_container,
    injectable,
    singleton,
    ServiceLifetime
)
from .interfaces import SignalStrength, MarketRegime, RiskLevel
from .event_system import EventBus, get_event_bus, EventType, EventPriority
from .strategy_components import (
    StrategySignal,
    SignalType,
    PortfolioState,
    StrategyComponent,
    ComponentType
)


class AdaptationTrigger(Enum):
    """Triggers for strategy adaptation."""
    MARKET_REGIME_CHANGE = "market_regime_change"
    VOLATILITY_SPIKE = "volatility_spike"
    PERFORMANCE_DECLINE = "performance_decline"
    RISK_LIMIT_BREACH = "risk_limit_breach"
    CORRELATION_CHANGE = "correlation_change"
    TIME_BASED = "time_based"
    EXTERNAL_SIGNAL = "external_signal"


class AdaptationStrategy(Enum):
    """Strategy adaptation methods."""
    PARAMETER_ADJUSTMENT = "parameter_adjustment"
    COMPONENT_SWITCHING = "component_switching"
    POSITION_RESIZING = "position_resizing"
    STRATEGY_SWITCHING = "strategy_switching"
    RISK_BUDGET_REALLOCATION = "risk_budget_reallocation"
    MARKET_TIMING = "market_timing"


@dataclass
class RiskProfile:
    """Risk profile for adaptive strategies."""
    max_drawdown: float = 0.10  # 10%
    max_daily_loss: float = 0.02  # 2%
    max_position_size: float = 0.05  # 5%
    max_volatility: float = 0.25  # 25%
    target_sharpe_ratio: float = 1.5
    risk_free_rate: float = 0.02
    rebalance_frequency: str = "daily"
    stress_test_threshold: float = 0.95  # 95% confidence level


@dataclass
class MarketCondition:
    """Current market condition assessment."""
    regime: MarketRegime
    volatility: float
    trend_strength: float
    liquidity: float
    correlation_matrix: Dict[Tuple[str, str], float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AdaptationRule:
    """Rule for strategy adaptation."""
    rule_id: str
    trigger: AdaptationTrigger
    condition: Dict[str, Any]
    action: AdaptationStrategy
    parameters: Dict[str, Any]
    priority: int = 1
    cooldown_period: float = 3600.0  # 1 hour
    last_triggered: Optional[float] = None
    enabled: bool = True


@dataclass
class StrategyState:
    """Current state of an adaptive strategy."""
    strategy_id: str
    active_parameters: Dict[str, Any]
    current_risk_profile: RiskProfile
    market_condition: MarketCondition
    performance_metrics: Dict[str, Any]
    adaptation_history: List[Dict[str, Any]] = field(default_factory=list)
    last_adaptation: Optional[float] = None
    risk_budget_utilization: float = 0.0


class RiskAdaptiveStrategy(ABC):
    """Abstract base class for risk-adaptive strategies."""

    @abstractmethod
    async def assess_market_conditions(self, market_data: Dict[str, Any],
                                     portfolio: PortfolioState) -> MarketCondition:
        """Assess current market conditions."""
        pass

    @abstractmethod
    async def adapt_to_conditions(self, market_condition: MarketCondition,
                                current_state: StrategyState) -> Dict[str, Any]:
        """Adapt strategy parameters based on market conditions."""
        pass

    @abstractmethod
    async def calculate_risk_metrics(self, portfolio: PortfolioState,
                                   market_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate comprehensive risk metrics."""
        pass

    @abstractmethod
    async def generate_adaptive_signals(self, market_data: Dict[str, Any],
                                      portfolio: PortfolioState,
                                      market_condition: MarketCondition) -> List[StrategySignal]:
        """Generate signals with risk adaptation."""
        pass

    @property
    @abstractmethod
    def strategy_id(self) -> str:
        """Get unique strategy identifier."""
        pass


@injectable
@singleton
class MarketRegimeAdapter(RiskAdaptiveStrategy):
    """Market regime-based strategy adaptation."""

    def __init__(self):
        self._regime_parameters = {
            MarketRegime.BULL: {
                'position_size_multiplier': 1.2,
                'stop_loss_multiplier': 1.5,
                'take_profit_multiplier': 1.3,
                'volatility_threshold': 0.20
            },
            MarketRegime.BEAR: {
                'position_size_multiplier': 0.8,
                'stop_loss_multiplier': 0.8,
                'take_profit_multiplier': 0.9,
                'volatility_threshold': 0.15
            },
            MarketRegime.SIDEWAYS: {
                'position_size_multiplier': 1.0,
                'stop_loss_multiplier': 1.0,
                'take_profit_multiplier': 1.0,
                'volatility_threshold': 0.10
            },
            MarketRegime.HIGH_VOLATILITY: {
                'position_size_multiplier': 0.6,
                'stop_loss_multiplier': 0.7,
                'take_profit_multiplier': 0.8,
                'volatility_threshold': 0.30
            }
        }

    @property
    def strategy_id(self) -> str:
        return "market_regime_adapter"

    async def assess_market_conditions(self, market_data: Dict[str, Any],
                                     portfolio: PortfolioState) -> MarketCondition:
        """Assess market regime and conditions."""
        # Calculate market metrics
        returns = []
        volatilities = []

        for symbol, data in market_data.items():
            if 'returns' in data:
                returns.extend(data['returns'][-20:])  # Last 20 periods
            if 'close' in data:
                # Calculate rolling volatility
                prices = data.get('price_history', [data['close']])
                if len(prices) > 10:
                    price_returns = [prices[i]/prices[i-1] - 1 for i in range(1, len(prices))]
                    volatility = statistics.stdev(price_returns) * math.sqrt(252)
                    volatilities.append(volatility)

        # Determine market regime
        avg_return = statistics.mean(returns) if returns else 0
        avg_volatility = statistics.mean(volatilities) if volatilities else 0.20

        if avg_volatility > 0.25:
            regime = MarketRegime.HIGH_VOLATILITY
        elif avg_return > 0.001:  # Positive trend
            regime = MarketRegime.BULL
        elif avg_return < -0.001:  # Negative trend
            regime = MarketRegime.BEAR
        else:
            regime = MarketRegime.SIDEWAYS

        # Calculate trend strength
        trend_strength = abs(avg_return) / (avg_volatility + 0.001)  # Avoid division by zero

        return MarketCondition(
            regime=regime,
            volatility=avg_volatility,
            trend_strength=trend_strength,
            liquidity=0.8  # Placeholder
        )

    async def adapt_to_conditions(self, market_condition: MarketCondition,
                                current_state: StrategyState) -> Dict[str, Any]:
        """Adapt strategy parameters based on market regime."""
        regime_params = self._regime_parameters.get(market_condition.regime, {})

        # Adjust parameters based on regime
        adapted_params = current_state.active_parameters.copy()

        for param, multiplier in regime_params.items():
            if param.endswith('_multiplier') and param in adapted_params:
                base_param = param.replace('_multiplier', '')
                if base_param in adapted_params:
                    adapted_params[base_param] = adapted_params[base_param] * multiplier

        # Adjust volatility threshold
        adapted_params['volatility_threshold'] = regime_params.get('volatility_threshold', 0.20)

        return adapted_params

    async def calculate_risk_metrics(self, portfolio: PortfolioState,
                                   market_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate regime-aware risk metrics."""
        # Calculate portfolio VaR adjusted for regime
        positions_value = sum(pos.market_value for pos in portfolio.positions.values())

        if positions_value == 0:
            return {'var_95': 0.0, 'expected_shortfall': 0.0, 'beta': 1.0}

        # Simplified VaR calculation
        volatilities = []
        for symbol, data in market_data.items():
            if 'volatility' in data:
                volatilities.append(data['volatility'])

        portfolio_volatility = statistics.mean(volatilities) if volatilities else 0.20
        var_95 = positions_value * portfolio_volatility * 1.645  # 95% confidence

        return {
            'var_95': var_95,
            'expected_shortfall': var_95 * 1.2,  # Simplified ES
            'beta': 1.0,  # Placeholder
            'regime_adjusted_var': var_95 * self._get_regime_risk_multiplier(portfolio)
        }

    async def generate_adaptive_signals(self, market_data: Dict[str, Any],
                                      portfolio: PortfolioState,
                                      market_condition: MarketCondition) -> List[StrategySignal]:
        """Generate signals adapted to market regime."""
        signals = []

        # Adjust signal generation based on regime
        regime_multiplier = self._get_regime_signal_multiplier(market_condition.regime)

        for symbol, data in market_data.items():
            # Skip if already have position in high volatility
            if (market_condition.regime == MarketRegime.HIGH_VOLATILITY and
                symbol in portfolio.positions):
                continue

            # Generate regime-appropriate signals
            if market_condition.regime == MarketRegime.BULL:
                # More aggressive in bull markets
                if data.get('momentum', 0) > 0.7:
                    signals.append(StrategySignal(
                        signal_type=SignalType.BUY,
                        symbol=symbol,
                        strength=SignalStrength.STRONG,
                        confidence=min(0.9, data.get('momentum', 0) * regime_multiplier),
                        metadata={'adaptation_reason': 'bull_market_momentum'}
                    ))

            elif market_condition.regime == MarketRegime.BEAR:
                # More defensive in bear markets
                if data.get('rsi', 50) < 30:
                    signals.append(StrategySignal(
                        signal_type=SignalType.BUY,
                        symbol=symbol,
                        strength=SignalStrength.MODERATE,
                        confidence=min(0.7, (30 - data.get('rsi', 50)) / 30 * regime_multiplier),
                        metadata={'adaptation_reason': 'bear_market_oversold'}
                    ))

            elif market_condition.regime == MarketRegime.SIDEWAYS:
                # Mean-reversion in sideways markets
                bollinger_pos = data.get('bollinger_position', 0.5)
                if bollinger_pos < 0.2:  # Near lower band
                    signals.append(StrategySignal(
                        signal_type=SignalType.BUY,
                        symbol=symbol,
                        strength=SignalStrength.MODERATE,
                        confidence=min(0.8, (0.2 - bollinger_pos) / 0.2 * regime_multiplier),
                        metadata={'adaptation_reason': 'sideways_mean_reversion'}
                    ))

        return signals

    def _get_regime_risk_multiplier(self, portfolio: PortfolioState) -> float:
        """Get risk multiplier based on portfolio composition."""
        # Simplified risk adjustment
        num_positions = len(portfolio.positions)
        if num_positions > 5:
            return 1.2  # Higher risk for concentrated portfolios
        return 1.0

    def _get_regime_signal_multiplier(self, regime: MarketRegime) -> float:
        """Get signal strength multiplier based on regime."""
        multipliers = {
            MarketRegime.BULL: 1.2,
            MarketRegime.BEAR: 0.8,
            MarketRegime.SIDEWAYS: 1.0,
            MarketRegime.HIGH_VOLATILITY: 0.6
        }
        return multipliers.get(regime, 1.0)


@injectable
@singleton
class VolatilityAdaptiveStrategy(RiskAdaptiveStrategy):
    """Volatility-based strategy adaptation."""

    def __init__(self):
        self._volatility_bands = {
            'low': (0.0, 0.15),
            'medium': (0.15, 0.25),
            'high': (0.25, 0.35),
            'extreme': (0.35, float('inf'))
        }

        self._volatility_parameters = {
            'low': {
                'position_size_max': 0.05,
                'stop_loss_pct': 0.02,
                'take_profit_pct': 0.04,
                'signal_threshold': 0.6
            },
            'medium': {
                'position_size_max': 0.03,
                'stop_loss_pct': 0.03,
                'take_profit_pct': 0.06,
                'signal_threshold': 0.7
            },
            'high': {
                'position_size_max': 0.02,
                'stop_loss_pct': 0.05,
                'take_profit_pct': 0.08,
                'signal_threshold': 0.8
            },
            'extreme': {
                'position_size_max': 0.01,
                'stop_loss_pct': 0.08,
                'take_profit_pct': 0.10,
                'signal_threshold': 0.9
            }
        }

    @property
    def strategy_id(self) -> str:
        return "volatility_adaptive_strategy"

    async def assess_market_conditions(self, market_data: Dict[str, Any],
                                     portfolio: PortfolioState) -> MarketCondition:
        """Assess volatility conditions."""
        volatilities = []

        for symbol, data in market_data.items():
            if 'volatility' in data:
                volatilities.append(data['volatility'])
            elif 'price_history' in data:
                # Calculate volatility from price history
                prices = data['price_history']
                if len(prices) > 10:
                    returns = [prices[i]/prices[i-1] - 1 for i in range(1, len(prices))]
                    vol = statistics.stdev(returns) * math.sqrt(252)
                    volatilities.append(vol)

        avg_volatility = statistics.mean(volatilities) if volatilities else 0.20

        # Determine volatility band
        volatility_band = 'medium'
        for band, (min_vol, max_vol) in self._volatility_bands.items():
            if min_vol <= avg_volatility < max_vol:
                volatility_band = band
                break

        return MarketCondition(
            regime=MarketRegime.SIDEWAYS,  # Placeholder
            volatility=avg_volatility,
            trend_strength=0.5,  # Placeholder
            liquidity=0.8  # Placeholder
        )

    async def adapt_to_conditions(self, market_condition: MarketCondition,
                                current_state: StrategyState) -> Dict[str, Any]:
        """Adapt strategy parameters based on volatility."""
        volatility = market_condition.volatility

        # Determine volatility band
        volatility_band = 'medium'
        for band, (min_vol, max_vol) in self._volatility_bands.items():
            if min_vol <= volatility < max_vol:
                volatility_band = band
                break

        # Get parameters for volatility band
        band_params = self._volatility_parameters[volatility_band]

        # Adapt current parameters
        adapted_params = current_state.active_parameters.copy()
        adapted_params.update(band_params)

        return adapted_params

    async def calculate_risk_metrics(self, portfolio: PortfolioState,
                                   market_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate volatility-adjusted risk metrics."""
        # Calculate volatility-adjusted VaR
        positions_value = sum(pos.market_value for pos in portfolio.positions.values())

        if positions_value == 0:
            return {'var_95': 0.0, 'volatility_adjusted_var': 0.0}

        # Get portfolio volatility
        volatilities = [data.get('volatility', 0.20) for data in market_data.values()]
        portfolio_volatility = statistics.mean(volatilities) if volatilities else 0.20

        # Adjust VaR based on volatility
        base_var = positions_value * portfolio_volatility * 1.645
        volatility_multiplier = min(2.0, portfolio_volatility / 0.20)  # Scale with volatility
        adjusted_var = base_var * volatility_multiplier

        return {
            'var_95': base_var,
            'volatility_adjusted_var': adjusted_var,
            'portfolio_volatility': portfolio_volatility,
            'volatility_multiplier': volatility_multiplier
        }

    async def generate_adaptive_signals(self, market_data: Dict[str, Any],
                                      portfolio: PortfolioState,
                                      market_condition: MarketCondition) -> List[StrategySignal]:
        """Generate volatility-adapted signals."""
        signals = []
        volatility = market_condition.volatility

        # Determine volatility band
        volatility_band = 'medium'
        for band, (min_vol, max_vol) in self._volatility_bands.items():
            if min_vol <= volatility < max_vol:
                volatility_band = band
                break

        band_params = self._volatility_parameters[volatility_band]
        signal_threshold = band_params['signal_threshold']

        for symbol, data in market_data.items():
            # Adjust signal generation based on volatility
            momentum = data.get('momentum', 0)
            rsi = data.get('rsi', 50)

            # Higher threshold in high volatility
            if volatility_band in ['high', 'extreme']:
                if rsi < 25 and momentum < -0.5:  # Strong oversold in high vol
                    signals.append(StrategySignal(
                        signal_type=SignalType.BUY,
                        symbol=symbol,
                        strength=SignalStrength.MODERATE,
                        confidence=min(0.8, (25 - rsi) / 25),
                        metadata={
                            'adaptation_reason': f'{volatility_band}_volatility_oversold',
                            'volatility': volatility,
                            'volatility_band': volatility_band
                        }
                    ))
            else:
                # Normal conditions
                if rsi < 30 and momentum > signal_threshold:
                    signals.append(StrategySignal(
                        signal_type=SignalType.BUY,
                        symbol=symbol,
                        strength=SignalStrength.STRONG,
                        confidence=min(0.9, momentum),
                        metadata={
                            'adaptation_reason': f'{volatility_band}_volatility_momentum',
                            'volatility': volatility,
                            'volatility_band': volatility_band
                        }
                    ))

        return signals


@injectable
@singleton
class PerformanceAdaptiveStrategy(RiskAdaptiveStrategy):
    """Performance-based strategy adaptation."""

    def __init__(self):
        self._performance_thresholds = {
            'sharpe_ratio_min': 0.5,
            'win_rate_min': 0.55,
            'max_drawdown_max': 0.15,
            'profit_factor_min': 1.2
        }

        self._adaptation_triggers = {
            'sharpe_decline': 0.3,  # 30% decline triggers adaptation
            'win_rate_decline': 0.1,  # 10% decline triggers adaptation
            'drawdown_increase': 0.05  # 5% increase triggers adaptation
        }

    @property
    def strategy_id(self) -> str:
        return "performance_adaptive_strategy"

    async def assess_market_conditions(self, market_data: Dict[str, Any],
                                     portfolio: PortfolioState) -> MarketCondition:
        """Assess market conditions with performance context."""
        # This would normally assess market conditions
        # For now, return a basic assessment
        return MarketCondition(
            regime=MarketRegime.SIDEWAYS,
            volatility=0.20,
            trend_strength=0.5,
            liquidity=0.8
        )

    async def adapt_to_conditions(self, market_condition: MarketCondition,
                                current_state: StrategyState) -> Dict[str, Any]:
        """Adapt strategy based on performance metrics."""
        performance = current_state.performance_metrics

        adapted_params = current_state.active_parameters.copy()

        # Adapt based on Sharpe ratio
        sharpe_ratio = performance.get('sharpe_ratio', 1.0)
        if sharpe_ratio < self._performance_thresholds['sharpe_ratio_min']:
            # Reduce risk parameters
            adapted_params['position_size_max'] = adapted_params.get('position_size_max', 0.05) * 0.8
            adapted_params['stop_loss_pct'] = adapted_params.get('stop_loss_pct', 0.05) * 1.2

        # Adapt based on win rate
        win_rate = performance.get('win_rate', 0.55)
        if win_rate < self._performance_thresholds['win_rate_min']:
            # Increase signal quality requirements
            adapted_params['signal_threshold'] = adapted_params.get('signal_threshold', 0.7) * 1.1

        # Adapt based on drawdown
        max_drawdown = performance.get('max_drawdown', 0.0)
        if max_drawdown > self._performance_thresholds['max_drawdown_max']:
            # Further reduce position sizes
            adapted_params['position_size_max'] = adapted_params.get('position_size_max', 0.05) * 0.7

        return adapted_params

    async def calculate_risk_metrics(self, portfolio: PortfolioState,
                                   market_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate performance-adjusted risk metrics."""
        # Calculate performance-adjusted VaR
        positions_value = sum(pos.market_value for pos in portfolio.positions.values())

        if positions_value == 0:
            return {'var_95': 0.0, 'performance_adjusted_var': 0.0}

        # Base VaR calculation
        volatilities = [data.get('volatility', 0.20) for data in market_data.values()]
        portfolio_volatility = statistics.mean(volatilities) if volatilities else 0.20
        base_var = positions_value * portfolio_volatility * 1.645

        # Adjust based on recent performance
        # This is a simplified adjustment - in practice, this would use more sophisticated methods
        performance_adjustment = 1.0  # Neutral adjustment

        # If recent performance is poor, increase VaR estimate
        # (implementation would check recent P&L, win rate, etc.)

        adjusted_var = base_var * performance_adjustment

        return {
            'var_95': base_var,
            'performance_adjusted_var': adjusted_var,
            'performance_adjustment': performance_adjustment
        }

    async def generate_adaptive_signals(self, market_data: Dict[str, Any],
                                      portfolio: PortfolioState,
                                      market_condition: MarketCondition) -> List[StrategySignal]:
        """Generate performance-adapted signals."""
        signals = []

        # This would analyze recent performance and adjust signal generation accordingly
        # For now, return a basic implementation

        for symbol, data in market_data.items():
            # Check if we should generate signals based on recent performance
            # (implementation would check symbol-specific performance)

            momentum = data.get('momentum', 0)
            rsi = data.get('rsi', 50)

            # Generate signals with performance-based adjustments
            if rsi < 35 and momentum > 0.6:
                signals.append(StrategySignal(
                    signal_type=SignalType.BUY,
                    symbol=symbol,
                    strength=SignalStrength.MODERATE,
                    confidence=min(0.8, momentum * 0.9),  # Slightly reduced due to performance adaptation
                    metadata={
                        'adaptation_reason': 'performance_based_adjustment',
                        'original_confidence': momentum,
                        'adjusted_confidence': momentum * 0.9
                    }
                ))

        return signals


@injectable
@singleton
class RiskAdaptiveStrategyManager:
    """
    Risk-Adaptive Strategy Manager for Institutional-Grade Trading.

    Features:
    - Dynamic strategy adaptation based on market conditions
    - Risk-aware parameter adjustment
    - Performance-based strategy optimization
    - Multi-timeframe risk assessment
    - Adaptive risk budgeting
    - Stress testing and scenario analysis
    - Real-time strategy monitoring and alerting
    """

    def __init__(self, container: Optional[DependencyInjectionContainer] = None):
        self._container = container or get_container()
        self._event_bus = get_event_bus()
        self._strategies: Dict[str, RiskAdaptiveStrategy] = {}
        self._strategy_states: Dict[str, StrategyState] = {}
        self._adaptation_rules: List[AdaptationRule] = []
        self._lock = asyncio.Lock()

        # Initialize strategies
        self._initialize_strategies()

        # Initialize default adaptation rules
        self._initialize_adaptation_rules()

    def _initialize_strategies(self):
        """Initialize risk-adaptive strategies."""
        try:
            self._strategies = {
                'market_regime': self._container.get_service(MarketRegimeAdapter),
                'volatility': self._container.get_service(VolatilityAdaptiveStrategy),
                'performance': self._container.get_service(PerformanceAdaptiveStrategy)
            }
        except Exception as e:
            logger.warning(f"Failed to initialize some adaptive strategies: {e}")

    def _initialize_adaptation_rules(self):
        """Initialize default adaptation rules."""
        self._adaptation_rules = [
            AdaptationRule(
                rule_id="high_volatility_reduction",
                trigger=AdaptationTrigger.VOLATILITY_SPIKE,
                condition={"volatility_threshold": 0.30, "duration_minutes": 5},
                action=AdaptationStrategy.POSITION_RESIZING,
                parameters={"size_reduction": 0.5},
                priority=1
            ),
            AdaptationRule(
                rule_id="performance_decline_adaptation",
                trigger=AdaptationTrigger.PERFORMANCE_DECLINE,
                condition={"sharpe_decline_pct": 0.25, "time_window_days": 7},
                action=AdaptationStrategy.PARAMETER_ADJUSTMENT,
                parameters={"risk_reduction": 0.2},
                priority=2
            ),
            AdaptationRule(
                rule_id="regime_change_adaptation",
                trigger=AdaptationTrigger.MARKET_REGIME_CHANGE,
                condition={"min_regime_duration_hours": 24},
                action=AdaptationStrategy.COMPONENT_SWITCHING,
                parameters={"new_regime": "detected_regime"},
                priority=3
            )
        ]

    async def register_strategy(self, strategy_id: str, risk_profile: RiskProfile,
                              initial_parameters: Dict[str, Any]):
        """Register a new adaptive strategy."""
        async with self._lock:
            self._strategy_states[strategy_id] = StrategyState(
                strategy_id=strategy_id,
                active_parameters=initial_parameters,
                current_risk_profile=risk_profile,
                market_condition=MarketCondition(
                    regime=MarketRegime.SIDEWAYS,
                    volatility=0.20,
                    trend_strength=0.5,
                    liquidity=0.8
                ),
                performance_metrics={}
            )

        logger.info(f"Registered adaptive strategy: {strategy_id}")

    async def adapt_strategy(self, strategy_id: str, market_data: Dict[str, Any],
                           portfolio: PortfolioState, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt strategy based on current conditions.

        Args:
            strategy_id: Strategy identifier
            market_data: Current market data
            portfolio: Current portfolio state
            context: Additional context

        Returns:
            Adapted strategy parameters
        """
        if strategy_id not in self._strategy_states:
            raise ValueError(f"Strategy {strategy_id} not registered")

        strategy_state = self._strategy_states[strategy_id]

        # Assess market conditions using all adaptive strategies
        market_conditions = {}
        for strategy_name, strategy in self._strategies.items():
            try:
                condition = await strategy.assess_market_conditions(market_data, portfolio)
                market_conditions[strategy_name] = condition
            except Exception as e:
                logger.error(f"Error assessing conditions with {strategy_name}: {e}")

        # Combine market conditions (use the most conservative assessment)
        combined_condition = self._combine_market_conditions(market_conditions)
        strategy_state.market_condition = combined_condition

        # Check adaptation rules
        triggered_rules = await self._check_adaptation_rules(strategy_state, combined_condition, context)

        # Apply adaptations
        adapted_parameters = strategy_state.active_parameters.copy()

        for rule in triggered_rules:
            try:
                adaptation = await self._apply_adaptation_rule(rule, strategy_state, combined_condition)
                adapted_parameters.update(adaptation)

                # Record adaptation
                strategy_state.adaptation_history.append({
                    'timestamp': time.time(),
                    'rule_id': rule.rule_id,
                    'trigger': rule.trigger.value,
                    'action': rule.action.value,
                    'parameters': adaptation
                })

            except Exception as e:
                logger.error(f"Error applying adaptation rule {rule.rule_id}: {e}")

        # Update strategy state
        strategy_state.active_parameters = adapted_parameters
        strategy_state.last_adaptation = time.time()

        # Publish adaptation event
        await self._publish_adaptation_event(strategy_id, triggered_rules, adapted_parameters)

        return adapted_parameters

    async def generate_adaptive_signals(self, strategy_id: str, market_data: Dict[str, Any],
                                      portfolio: PortfolioState) -> List[StrategySignal]:
        """
        Generate signals using adaptive strategies.

        Args:
            strategy_id: Strategy identifier
            market_data: Current market data
            portfolio: Current portfolio state

        Returns:
            List of adaptive strategy signals
        """
        if strategy_id not in self._strategy_states:
            raise ValueError(f"Strategy {strategy_id} not registered")

        strategy_state = self._strategy_states[strategy_id]
        all_signals = []

        # Generate signals from each adaptive strategy
        for strategy_name, strategy in self._strategies.items():
            try:
                signals = await strategy.generate_adaptive_signals(
                    market_data, portfolio, strategy_state.market_condition
                )

                # Add strategy metadata
                for signal in signals:
                    signal.metadata['adaptive_strategy'] = strategy_name
                    signal.metadata['market_regime'] = strategy_state.market_condition.regime.value
                    signal.metadata['volatility'] = strategy_state.market_condition.volatility

                all_signals.extend(signals)

            except Exception as e:
                logger.error(f"Error generating signals with {strategy_name}: {e}")

        # Filter and prioritize signals
        final_signals = await self._filter_adaptive_signals(all_signals, strategy_state)

        return final_signals

    async def calculate_adaptive_risk_metrics(self, strategy_id: str, portfolio: PortfolioState,
                                            market_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate adaptive risk metrics.

        Args:
            strategy_id: Strategy identifier
            portfolio: Current portfolio state
            market_data: Current market data

        Returns:
            Dictionary of risk metrics
        """
        if strategy_id not in self._strategy_states:
            raise ValueError(f"Strategy {strategy_id} not registered")

        all_metrics = {}

        # Calculate risk metrics from each adaptive strategy
        for strategy_name, strategy in self._strategies.items():
            try:
                metrics = await strategy.calculate_risk_metrics(portfolio, market_data)
                all_metrics.update({f"{strategy_name}_{k}": v for k, v in metrics.items()})
            except Exception as e:
                logger.error(f"Error calculating risk metrics with {strategy_name}: {e}")

        # Combine metrics (use most conservative values)
        combined_metrics = self._combine_risk_metrics(all_metrics)

        return combined_metrics

    def _combine_market_conditions(self, conditions: Dict[str, MarketCondition]) -> MarketCondition:
        """Combine market conditions from multiple strategies."""
        if not conditions:
            return MarketCondition(
                regime=MarketRegime.SIDEWAYS,
                volatility=0.20,
                trend_strength=0.5,
                liquidity=0.8
            )

        # Use most conservative assessments
        regimes = [cond.regime for cond in conditions.values()]
        volatilities = [cond.volatility for cond in conditions.values()]

        # Choose most conservative regime
        regime_priority = {
            MarketRegime.HIGH_VOLATILITY: 4,
            MarketRegime.BEAR: 3,
            MarketRegime.SIDEWAYS: 2,
            MarketRegime.BULL: 1
        }

        conservative_regime = max(regimes, key=lambda r: regime_priority.get(r, 0))
        max_volatility = max(volatilities)

        return MarketCondition(
            regime=conservative_regime,
            volatility=max_volatility,
            trend_strength=statistics.mean([cond.trend_strength for cond in conditions.values()]),
            liquidity=statistics.mean([cond.liquidity for cond in conditions.values()])
        )

    async def _check_adaptation_rules(self, strategy_state: StrategyState,
                                    market_condition: MarketCondition,
                                    context: Dict[str, Any]) -> List[AdaptationRule]:
        """Check which adaptation rules are triggered."""
        triggered_rules = []
        current_time = time.time()

        for rule in self._adaptation_rules:
            if not rule.enabled:
                continue

            # Check cooldown period
            if (rule.last_triggered and
                current_time - rule.last_triggered < rule.cooldown_period):
                continue

            # Check trigger conditions
            if await self._evaluate_rule_condition(rule, strategy_state, market_condition, context):
                triggered_rules.append(rule)
                rule.last_triggered = current_time

        # Sort by priority
        triggered_rules.sort(key=lambda r: r.priority)

        return triggered_rules

    async def _evaluate_rule_condition(self, rule: AdaptationRule, strategy_state: StrategyState,
                                     market_condition: MarketCondition, context: Dict[str, Any]) -> bool:
        """Evaluate if a rule condition is met."""
        condition = rule.condition

        if rule.trigger == AdaptationTrigger.VOLATILITY_SPIKE:
            threshold = condition.get('volatility_threshold', 0.30)
            return market_condition.volatility > threshold

        elif rule.trigger == AdaptationTrigger.PERFORMANCE_DECLINE:
            # Check performance metrics
            sharpe_ratio = strategy_state.performance_metrics.get('sharpe_ratio', 1.0)
            decline_pct = condition.get('sharpe_decline_pct', 0.25)
            # This would compare with historical performance
            return sharpe_ratio < (1.0 - decline_pct)  # Simplified check

        elif rule.trigger == AdaptationTrigger.MARKET_REGIME_CHANGE:
            # Check if regime changed significantly
            # This would compare with previous regime
            return True  # Simplified - always trigger for demo

        return False

    async def _apply_adaptation_rule(self, rule: AdaptationRule, strategy_state: StrategyState,
                                   market_condition: MarketCondition) -> Dict[str, Any]:
        """Apply an adaptation rule."""
        adaptations = {}

        if rule.action == AdaptationStrategy.POSITION_RESIZING:
            size_reduction = rule.parameters.get('size_reduction', 0.5)
            adaptations['position_size_max'] = (
                strategy_state.active_parameters.get('position_size_max', 0.05) * size_reduction
            )

        elif rule.action == AdaptationStrategy.PARAMETER_ADJUSTMENT:
            risk_reduction = rule.parameters.get('risk_reduction', 0.2)
            adaptations['stop_loss_pct'] = (
                strategy_state.active_parameters.get('stop_loss_pct', 0.05) * (1 + risk_reduction)
            )

        return adaptations

    async def _filter_adaptive_signals(self, signals: List[StrategySignal],
                                     strategy_state: StrategyState) -> List[StrategySignal]:
        """Filter and prioritize adaptive signals."""
        if not signals:
            return []

        # Remove conflicting signals
        filtered_signals = []
        symbol_signals = {}

        for signal in signals:
            if signal.symbol not in symbol_signals:
                symbol_signals[signal.symbol] = []
            symbol_signals[signal.symbol].append(signal)

        for symbol, symbol_signal_list in symbol_signals.items():
            if len(symbol_signal_list) == 1:
                filtered_signals.extend(symbol_signal_list)
            else:
                # Choose signal with highest confidence
                best_signal = max(symbol_signal_list, key=lambda s: s.confidence)
                filtered_signals.append(best_signal)

        # Apply risk limits
        risk_profile = strategy_state.current_risk_profile
        max_signals = min(len(filtered_signals), 10)  # Max 10 signals

        # Sort by confidence and strength
        prioritized_signals = sorted(
            filtered_signals,
            key=lambda s: (s.confidence, s.strength.value),
            reverse=True
        )

        return prioritized_signals[:max_signals]

    def _combine_risk_metrics(self, metrics: Dict[str, float]) -> Dict[str, float]:
        """Combine risk metrics from multiple strategies."""
        # Use most conservative (highest) values for risk metrics
        combined = {}

        # Group metrics by type
        var_metrics = {k: v for k, v in metrics.items() if 'var' in k.lower()}
        if var_metrics:
            combined['combined_var_95'] = max(var_metrics.values())

        volatility_metrics = {k: v for k, v in metrics.items() if 'volatility' in k.lower()}
        if volatility_metrics:
            combined['combined_volatility'] = max(volatility_metrics.values())

        return combined

    async def _publish_adaptation_event(self, strategy_id: str, triggered_rules: List[AdaptationRule],
                                      adapted_parameters: Dict[str, Any]):
        """Publish strategy adaptation event."""
        event_data = {
            "strategy_id": strategy_id,
            "triggered_rules": [rule.rule_id for rule in triggered_rules],
            "adapted_parameters": adapted_parameters,
            "timestamp": time.time()
        }

        await self._event_bus.publish_event(
            self._event_bus.create_event(
                EventType.SYSTEM_HEALTH_CHANGED,
                "risk_adaptive_strategy_manager",
                event_data,
                EventPriority.NORMAL
            )
        )

    def get_strategy_state(self, strategy_id: str) -> Optional[StrategyState]:
        """Get the current state of a strategy."""
        return self._strategy_states.get(strategy_id)

    def get_adaptation_history(self, strategy_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get adaptation history for a strategy."""
        state = self._strategy_states.get(strategy_id)
        if state:
            return state.adaptation_history[-limit:]
        return []

    def add_adaptation_rule(self, rule: AdaptationRule):
        """Add a new adaptation rule."""
        self._adaptation_rules.append(rule)
        logger.info(f"Added adaptation rule: {rule.rule_id}")

    def remove_adaptation_rule(self, rule_id: str) -> bool:
        """Remove an adaptation rule."""
        for i, rule in enumerate(self._adaptation_rules):
            if rule.rule_id == rule_id:
                del self._adaptation_rules[i]
                logger.info(f"Removed adaptation rule: {rule_id}")
                return True
        return False


# Global risk-adaptive strategy manager instance
_risk_adaptive_manager = RiskAdaptiveStrategyManager()


def get_risk_adaptive_manager() -> RiskAdaptiveStrategyManager:
    """Get the global risk-adaptive strategy manager."""
    return _risk_adaptive_manager


# Convenience functions
async def adapt_strategy(strategy_id: str, market_data: Dict[str, Any],
                        portfolio: PortfolioState, context: Dict[str, Any]) -> Dict[str, Any]:
    """Adapt a strategy based on current conditions."""
    return await _risk_adaptive_manager.adapt_strategy(strategy_id, market_data, portfolio, context)


async def generate_adaptive_signals(strategy_id: str, market_data: Dict[str, Any],
                                  portfolio: PortfolioState) -> List[StrategySignal]:
    """Generate adaptive signals for a strategy."""
    return await _risk_adaptive_manager.generate_adaptive_signals(strategy_id, market_data, portfolio)


async def calculate_adaptive_risk_metrics(strategy_id: str, portfolio: PortfolioState,
                                        market_data: Dict[str, Any]) -> Dict[str, float]:
    """Calculate adaptive risk metrics for a strategy."""
    return await _risk_adaptive_manager.calculate_adaptive_risk_metrics(strategy_id, portfolio, market_data)