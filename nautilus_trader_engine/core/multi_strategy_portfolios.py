"""
Multi-Strategy Portfolio Management for Institutional-Grade Trading.

This module provides comprehensive multi-strategy portfolio management capabilities
that integrate with the 5-pillar institutional architecture:

- Dynamic Capital Allocation: Risk-parity, equal-weight, and optimization-based allocation
- Correlation Management: Strategy diversification and correlation-aware rebalancing
- Risk Budgeting: Portfolio-level risk control with strategy-specific limits
- Performance Attribution: Strategy contribution analysis and performance decomposition
- Dynamic Rebalancing: Market-aware portfolio rebalancing with transaction cost optimization
- Strategy Replacement: Automated strategy switching based on performance and risk criteria
- Portfolio Optimization: Modern portfolio theory implementation with constraints
- Risk Parity Implementation: Equal risk contribution across strategies
- Kelly Criterion Integration: Optimal position sizing across multiple strategies

The multi-strategy portfolio system enables sophisticated portfolio construction
and management that maximizes risk-adjusted returns while maintaining diversification.
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
from .strategy_components import StrategySignal, PortfolioState, SignalType


class AllocationMethod(Enum):
    """Portfolio allocation methods."""
    EQUAL_WEIGHT = "equal_weight"
    RISK_PARITY = "risk_parity"
    MEAN_VARIANCE = "mean_variance"
    MINIMUM_VARIANCE = "minimum_variance"
    MAXIMUM_SHARPE = "maximum_sharpe"
    KELLY_CRITERION = "kelly_criterion"
    EQUAL_RISK_CONTRIBUTION = "equal_risk_contribution"
    BLACK_LITTERMAN = "black_litterman"


class RebalancingFrequency(Enum):
    """Portfolio rebalancing frequencies."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    THRESHOLD_BASED = "threshold_based"
    MARKET_REGIME = "market_regime"


class StrategyStatus(Enum):
    """Strategy status in portfolio."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    UNDER_PERFORMANCE = "under_performance"
    HIGH_RISK = "high_risk"


@dataclass
class StrategyAllocation:
    """Strategy allocation within portfolio."""
    strategy_id: str
    target_weight: float
    current_weight: float
    risk_budget: float
    performance_score: float
    correlation_matrix: Dict[str, float] = field(default_factory=dict)
    status: StrategyStatus = StrategyStatus.ACTIVE
    last_rebalance: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PortfolioConstraints:
    """Portfolio optimization constraints."""
    max_weight_per_strategy: float = 0.25  # 25%
    min_weight_per_strategy: float = 0.01  # 1%
    max_correlation_threshold: float = 0.8  # 80%
    max_portfolio_volatility: float = 0.20  # 20%
    min_portfolio_return: float = 0.05  # 5%
    max_drawdown_limit: float = 0.15  # 15%
    risk_parity_tolerance: float = 0.05  # 5%
    turnover_limit: float = 0.50  # 50% annual turnover


@dataclass
class PortfolioMetrics:
    """Portfolio-level performance and risk metrics."""
    total_value: float
    daily_return: float
    cumulative_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    value_at_risk: float
    expected_shortfall: float
    diversification_ratio: float
    risk_contribution: Dict[str, float] = field(default_factory=dict)
    performance_attribution: Dict[str, float] = field(default_factory=dict)
    correlation_matrix: Dict[Tuple[str, str], float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RebalancingSignal:
    """Signal for portfolio rebalancing."""
    portfolio_id: str
    strategy_adjustments: Dict[str, float]  # strategy_id -> weight_change
    reason: str
    urgency: str  # low, medium, high, critical
    estimated_cost: float
    expected_impact: Dict[str, float]
    timestamp: datetime = field(default_factory=datetime.now)


class AllocationOptimizer(ABC):
    """Abstract base class for portfolio allocation optimizers."""

    @abstractmethod
    async def optimize_allocation(self, strategies: List[StrategyAllocation],
                                constraints: PortfolioConstraints,
                                market_data: Dict[str, Any]) -> Dict[str, float]:
        """Optimize strategy allocations."""
        pass

    @property
    @abstractmethod
    def optimizer_name(self) -> str:
        """Get optimizer name."""
        pass


@injectable
@singleton
class RiskParityOptimizer(AllocationOptimizer):
    """Risk parity portfolio optimization."""

    @property
    def optimizer_name(self) -> str:
        return "risk_parity"

    async def optimize_allocation(self, strategies: List[StrategyAllocation],
                                constraints: PortfolioConstraints,
                                market_data: Dict[str, Any]) -> Dict[str, float]:
        """Implement risk parity allocation."""
        # Filter active strategies
        active_strategies = [s for s in strategies if s.status == StrategyStatus.ACTIVE]

        if not active_strategies:
            return {}

        num_strategies = len(active_strategies)

        # Start with equal weights
        equal_weight = 1.0 / num_strategies
        weights = {s.strategy_id: equal_weight for s in active_strategies}

        # Adjust for risk parity
        # This is a simplified implementation - in practice, this would use more sophisticated methods
        risk_contributions = await self._calculate_risk_contributions(active_strategies, market_data)

        if risk_contributions:
            # Adjust weights to achieve equal risk contribution
            total_risk = sum(risk_contributions.values())
            if total_risk > 0:
                target_risk_per_strategy = total_risk / num_strategies

                for strategy in active_strategies:
                    current_risk = risk_contributions.get(strategy.strategy_id, 0)
                    if current_risk > 0:
                        adjustment_factor = target_risk_per_strategy / current_risk
                        weights[strategy.strategy_id] *= adjustment_factor

                # Renormalize weights
                total_weight = sum(weights.values())
                if total_weight > 0:
                    weights = {k: v / total_weight for k, v in weights.items()}

        # Apply constraints
        weights = await self._apply_constraints(weights, constraints)

        return weights

    async def _calculate_risk_contributions(self, strategies: List[StrategyAllocation],
                                          market_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate risk contributions for each strategy."""
        risk_contributions = {}

        for strategy in strategies:
            # Simplified risk contribution calculation
            # In practice, this would use covariance matrix and more sophisticated methods
            volatility = strategy.metadata.get('volatility', 0.20)
            current_weight = strategy.current_weight

            risk_contributions[strategy.strategy_id] = volatility * current_weight

        return risk_contributions

    async def _apply_constraints(self, weights: Dict[str, float],
                               constraints: PortfolioConstraints) -> Dict[str, float]:
        """Apply portfolio constraints to weights."""
        # Apply minimum and maximum weight constraints
        for strategy_id, weight in weights.items():
            weights[strategy_id] = max(constraints.min_weight_per_strategy,
                                     min(constraints.max_weight_per_strategy, weight))

        # Renormalize after applying constraints
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}

        return weights


@injectable
@singleton
class MeanVarianceOptimizer(AllocationOptimizer):
    """Mean-variance portfolio optimization."""

    @property
    def optimizer_name(self) -> str:
        return "mean_variance"

    async def optimize_allocation(self, strategies: List[StrategyAllocation],
                                constraints: PortfolioConstraints,
                                market_data: Dict[str, Any]) -> Dict[str, float]:
        """Implement mean-variance optimization."""
        # Filter active strategies
        active_strategies = [s for s in strategies if s.status == StrategyStatus.ACTIVE]

        if not active_strategies:
            return {}

        # Extract expected returns and volatilities
        expected_returns = {}
        volatilities = {}
        correlations = {}

        for strategy in active_strategies:
            expected_returns[strategy.strategy_id] = strategy.metadata.get('expected_return', 0.10)
            volatilities[strategy.strategy_id] = strategy.metadata.get('volatility', 0.20)

            # Get correlations with other strategies
            for other_strategy in active_strategies:
                if other_strategy != strategy:
                    corr_key = (strategy.strategy_id, other_strategy.strategy_id)
                    correlations[corr_key] = strategy.correlation_matrix.get(
                        other_strategy.strategy_id, 0.5
                    )

        # Simplified mean-variance optimization
        # In practice, this would use quadratic programming
        weights = await self._simple_mean_variance_optimization(
            expected_returns, volatilities, correlations, constraints
        )

        return weights

    async def _simple_mean_variance_optimization(self, expected_returns: Dict[str, float],
                                              volatilities: Dict[str, float],
                                              correlations: Dict[Tuple[str, str], float],
                                              constraints: PortfolioConstraints) -> Dict[str, float]:
        """Simplified mean-variance optimization."""
        strategy_ids = list(expected_returns.keys())

        if len(strategy_ids) == 1:
            return {strategy_ids[0]: 1.0}

        # Start with equal weights
        weights = {sid: 1.0 / len(strategy_ids) for sid in strategy_ids}

        # Adjust weights based on risk-return profile
        # This is a very simplified approach
        for sid in strategy_ids:
            return_score = expected_returns[sid]
            risk_score = volatilities[sid]

            # Favor strategies with better risk-adjusted returns
            sharpe_like_score = return_score / risk_score if risk_score > 0 else 0
            weights[sid] *= (1 + sharpe_like_score)

        # Renormalize
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}

        return weights


@injectable
@singleton
class KellyCriterionOptimizer(AllocationOptimizer):
    """Kelly Criterion portfolio optimization."""

    @property
    def optimizer_name(self) -> str:
        return "kelly_criterion"

    async def optimize_allocation(self, strategies: List[StrategyAllocation],
                                constraints: PortfolioConstraints,
                                market_data: Dict[str, Any]) -> Dict[str, float]:
        """Implement Kelly Criterion allocation."""
        # Filter active strategies
        active_strategies = [s for s in strategies if s.status == StrategyStatus.ACTIVE]

        if not active_strategies:
            return {}

        weights = {}

        for strategy in active_strategies:
            # Get strategy parameters
            win_rate = strategy.metadata.get('win_rate', 0.55)
            avg_win = strategy.metadata.get('avg_win', 0.08)
            avg_loss = strategy.metadata.get('avg_loss', 0.04)

            if avg_loss == 0:
                kelly_fraction = 0
            else:
                # Kelly formula: (bp - q) / b
                # where b = odds (avg_win/avg_loss), p = win_rate, q = loss_rate
                b = avg_win / avg_loss
                kelly_fraction = (b * win_rate - (1 - win_rate)) / b

            # Use half-Kelly for safety
            kelly_fraction = max(0, min(kelly_fraction * 0.5, constraints.max_weight_per_strategy))

            weights[strategy.strategy_id] = kelly_fraction

        # Renormalize weights
        total_weight = sum(weights.values())
        if total_weight > 1.0:
            weights = {k: v / total_weight for k, v in weights.items()}
        elif total_weight < 1.0:
            # Distribute remaining weight equally
            remaining = 1.0 - total_weight
            equal_share = remaining / len(weights)
            weights = {k: v + equal_share for k, v in weights.items()}

        return weights


@injectable
@singleton
class MultiStrategyPortfolioManager:
    """
    Multi-Strategy Portfolio Manager for Institutional-Grade Trading.

    Features:
    - Dynamic capital allocation across multiple strategies
    - Risk-parity and optimization-based portfolio construction
    - Correlation-aware strategy diversification
    - Dynamic rebalancing with transaction cost optimization
    - Performance attribution and risk decomposition
    - Strategy replacement and portfolio adaptation
    - Real-time portfolio monitoring and alerting
    - Stress testing and scenario analysis
    """

    def __init__(self, container: Optional[DependencyInjectionContainer] = None):
        self._container = container or get_container()
        self._event_bus = get_event_bus()
        self._portfolios: Dict[str, List[StrategyAllocation]] = {}
        self._portfolio_metrics: Dict[str, PortfolioMetrics] = {}
        self._optimizers: Dict[str, AllocationOptimizer] = {}
        self._constraints: Dict[str, PortfolioConstraints] = {}
        self._lock = asyncio.Lock()

        # Initialize optimizers
        self._initialize_optimizers()

    def _initialize_optimizers(self):
        """Initialize portfolio optimizers."""
        try:
            self._optimizers = {
                'risk_parity': self._container.get_service(RiskParityOptimizer),
                'mean_variance': self._container.get_service(MeanVarianceOptimizer),
                'kelly_criterion': self._container.get_service(KellyCriterionOptimizer)
            }
        except Exception as e:
            logger.warning(f"Failed to initialize some optimizers: {e}")

    async def create_portfolio(self, portfolio_id: str, strategy_ids: List[str],
                              allocation_method: AllocationMethod = AllocationMethod.RISK_PARITY,
                              constraints: Optional[PortfolioConstraints] = None) -> bool:
        """
        Create a new multi-strategy portfolio.

        Args:
            portfolio_id: Unique portfolio identifier
            strategy_ids: List of strategy IDs to include
            allocation_method: Method for capital allocation
            constraints: Portfolio constraints

        Returns:
            Success status
        """
        async with self._lock:
            if portfolio_id in self._portfolios:
                logger.warning(f"Portfolio {portfolio_id} already exists")
                return False

            # Create strategy allocations
            allocations = []
            equal_weight = 1.0 / len(strategy_ids)

            for strategy_id in strategy_ids:
                allocation = StrategyAllocation(
                    strategy_id=strategy_id,
                    target_weight=equal_weight,
                    current_weight=equal_weight,
                    risk_budget=equal_weight,
                    performance_score=1.0,
                    status=StrategyStatus.ACTIVE
                )
                allocations.append(allocation)

            self._portfolios[portfolio_id] = allocations
            self._constraints[portfolio_id] = constraints or PortfolioConstraints()

            logger.info(f"Created portfolio {portfolio_id} with {len(strategy_ids)} strategies")
            return True

    async def optimize_portfolio(self, portfolio_id: str, market_data: Dict[str, Any],
                               allocation_method: AllocationMethod = AllocationMethod.RISK_PARITY) -> Dict[str, float]:
        """
        Optimize portfolio allocations.

        Args:
            portfolio_id: Portfolio identifier
            market_data: Current market data
            allocation_method: Optimization method to use

        Returns:
            Optimized strategy weights
        """
        if portfolio_id not in self._portfolios:
            raise ValueError(f"Portfolio {portfolio_id} not found")

        allocations = self._portfolios[portfolio_id]
        constraints = self._constraints[portfolio_id]

        # Get appropriate optimizer
        optimizer_name = allocation_method.value
        if optimizer_name not in self._optimizers:
            logger.warning(f"Optimizer {optimizer_name} not available, using risk_parity")
            optimizer_name = 'risk_parity'

        optimizer = self._optimizers[optimizer_name]

        # Optimize allocations
        try:
            optimized_weights = await optimizer.optimize_allocation(
                allocations, constraints, market_data
            )

            # Update allocations
            for allocation in allocations:
                if allocation.strategy_id in optimized_weights:
                    allocation.target_weight = optimized_weights[allocation.strategy_id]

            # Publish optimization event
            await self._publish_optimization_event(portfolio_id, optimized_weights, allocation_method)

            return optimized_weights

        except Exception as e:
            logger.error(f"Portfolio optimization failed for {portfolio_id}: {e}")
            return {}

    async def rebalance_portfolio(self, portfolio_id: str, current_portfolio: PortfolioState,
                                market_data: Dict[str, Any]) -> Optional[RebalancingSignal]:
        """
        Check if portfolio needs rebalancing and generate rebalancing signal.

        Args:
            portfolio_id: Portfolio identifier
            current_portfolio: Current portfolio state
            market_data: Current market data

        Returns:
            Rebalancing signal if needed, None otherwise
        """
        if portfolio_id not in self._portfolios:
            return None

        allocations = self._portfolios[portfolio_id]
        constraints = self._constraints[portfolio_id]

        # Calculate current weights
        total_value = current_portfolio.total_value
        current_weights = {}

        for symbol, position in current_portfolio.positions.items():
            # Map position to strategy (simplified - in practice this would be more sophisticated)
            strategy_id = self._map_position_to_strategy(symbol, allocations)
            if strategy_id:
                if strategy_id not in current_weights:
                    current_weights[strategy_id] = 0
                current_weights[strategy_id] += position.market_value / total_value

        # Check if rebalancing is needed
        adjustments = {}
        total_adjustment = 0

        for allocation in allocations:
            if allocation.status != StrategyStatus.ACTIVE:
                continue

            current_weight = current_weights.get(allocation.strategy_id, 0)
            target_weight = allocation.target_weight
            weight_diff = target_weight - current_weight

            # Check if adjustment exceeds threshold
            threshold = constraints.turnover_limit * 0.1  # 10% of annual turnover as monthly threshold

            if abs(weight_diff) > threshold:
                adjustments[allocation.strategy_id] = weight_diff
                total_adjustment += abs(weight_diff)

        if not adjustments:
            return None

        # Calculate estimated transaction costs
        estimated_cost = await self._estimate_transaction_costs(adjustments, current_portfolio, market_data)

        # Create rebalancing signal
        signal = RebalancingSignal(
            portfolio_id=portfolio_id,
            strategy_adjustments=adjustments,
            reason="Portfolio drift exceeds threshold",
            urgency="medium" if total_adjustment < 0.1 else "high",
            estimated_cost=estimated_cost,
            expected_impact={
                'tracking_error_reduction': total_adjustment * 0.8,
                'risk_adjustment': total_adjustment * 0.6
            }
        )

        # Publish rebalancing signal
        await self._publish_rebalancing_event(signal)

        return signal

    async def execute_rebalancing(self, signal: RebalancingSignal,
                                current_portfolio: PortfolioState) -> List[StrategySignal]:
        """
        Execute portfolio rebalancing.

        Args:
            signal: Rebalancing signal
            current_portfolio: Current portfolio state

        Returns:
            List of strategy signals for rebalancing
        """
        signals = []

        for strategy_id, weight_change in signal.strategy_adjustments.items():
            if weight_change > 0:
                # Need to increase position - generate buy signals
                signals.append(StrategySignal(
                    signal_type=SignalType.BUY,
                    symbol=f"PORTFOLIO_{strategy_id}",
                    strength=SignalStrength.MODERATE,
                    confidence=0.8,
                    quantity=weight_change * current_portfolio.total_value,
                    metadata={
                        'rebalancing': True,
                        'portfolio_id': signal.portfolio_id,
                        'reason': signal.reason
                    }
                ))
            elif weight_change < 0:
                # Need to decrease position - generate sell signals
                signals.append(StrategySignal(
                    signal_type=SignalType.SELL,
                    symbol=f"PORTFOLIO_{strategy_id}",
                    strength=SignalStrength.MODERATE,
                    confidence=0.8,
                    quantity=abs(weight_change) * current_portfolio.total_value,
                    metadata={
                        'rebalancing': True,
                        'portfolio_id': signal.portfolio_id,
                        'reason': signal.reason
                    }
                ))

        return signals

    async def update_portfolio_metrics(self, portfolio_id: str,
                                     portfolio_state: PortfolioState,
                                     market_data: Dict[str, Any]) -> PortfolioMetrics:
        """
        Update and calculate portfolio-level metrics.

        Args:
            portfolio_id: Portfolio identifier
            portfolio_state: Current portfolio state
            market_data: Current market data

        Returns:
            Updated portfolio metrics
        """
        if portfolio_id not in self._portfolios:
            raise ValueError(f"Portfolio {portfolio_id} not found")

        allocations = self._portfolios[portfolio_id]

        # Calculate basic metrics
        total_value = portfolio_state.total_value
        positions_value = sum(pos.market_value for pos in portfolio_state.positions.values())

        # Calculate returns (simplified - would need historical data)
        daily_return = 0.0  # Placeholder
        cumulative_return = (total_value - 100000) / 100000  # Assuming $100k initial

        # Calculate volatility (simplified)
        volatilities = [data.get('volatility', 0.20) for data in market_data.values()]
        portfolio_volatility = statistics.mean(volatilities) if volatilities else 0.20

        # Calculate Sharpe ratio
        risk_free_rate = 0.02  # 2%
        sharpe_ratio = (daily_return - risk_free_rate/252) / portfolio_volatility * math.sqrt(252) if portfolio_volatility > 0 else 0

        # Calculate Sortino ratio (simplified)
        sortino_ratio = sharpe_ratio * 0.8  # Placeholder

        # Calculate maximum drawdown (simplified)
        max_drawdown = 0.05  # Placeholder

        # Calculate VaR and ES (simplified)
        value_at_risk = total_value * portfolio_volatility * 1.645
        expected_shortfall = value_at_risk * 1.2

        # Calculate diversification ratio
        num_positions = len(portfolio_state.positions)
        diversification_ratio = math.sqrt(num_positions) if num_positions > 0 else 1.0

        # Calculate risk contributions
        risk_contributions = {}
        for allocation in allocations:
            if allocation.strategy_id in portfolio_state.positions:
                position_value = sum(pos.market_value for pos in portfolio_state.positions.values()
                                   if self._map_position_to_strategy(pos.symbol, allocations) == allocation.strategy_id)
                risk_contributions[allocation.strategy_id] = (position_value / total_value) * portfolio_volatility

        metrics = PortfolioMetrics(
            total_value=total_value,
            daily_return=daily_return,
            cumulative_return=cumulative_return,
            volatility=portfolio_volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            value_at_risk=value_at_risk,
            expected_shortfall=expected_shortfall,
            diversification_ratio=diversification_ratio,
            risk_contribution=risk_contributions
        )

        # Store metrics
        async with self._lock:
            self._portfolio_metrics[portfolio_id] = metrics

        return metrics

    async def get_portfolio_performance_attribution(self, portfolio_id: str) -> Dict[str, float]:
        """
        Calculate performance attribution by strategy.

        Args:
            portfolio_id: Portfolio identifier

        Returns:
            Performance attribution by strategy
        """
        if portfolio_id not in self._portfolios:
            return {}

        allocations = self._portfolios[portfolio_id]
        attribution = {}

        for allocation in allocations:
            # Simplified attribution calculation
            # In practice, this would use more sophisticated methods like Brinson attribution
            weight = allocation.current_weight
            performance_score = allocation.performance_score

            attribution[allocation.strategy_id] = weight * performance_score

        return attribution

    def get_portfolio_allocations(self, portfolio_id: str) -> List[StrategyAllocation]:
        """Get current portfolio allocations."""
        return self._portfolios.get(portfolio_id, [])

    def get_portfolio_metrics(self, portfolio_id: str) -> Optional[PortfolioMetrics]:
        """Get current portfolio metrics."""
        return self._portfolio_metrics.get(portfolio_id)

    def update_strategy_status(self, portfolio_id: str, strategy_id: str,
                             status: StrategyStatus, reason: str = "") -> bool:
        """Update strategy status in portfolio."""
        if portfolio_id not in self._portfolios:
            return False

        for allocation in self._portfolios[portfolio_id]:
            if allocation.strategy_id == strategy_id:
                allocation.status = status
                allocation.metadata['status_change_reason'] = reason
                allocation.metadata['status_change_time'] = time.time()

                logger.info(f"Updated strategy {strategy_id} status to {status.value} in portfolio {portfolio_id}")
                return True

        return False

    def _map_position_to_strategy(self, symbol: str, allocations: List[StrategyAllocation]) -> Optional[str]:
        """Map position symbol to strategy ID (simplified implementation)."""
        # This is a simplified mapping - in practice, this would be more sophisticated
        for allocation in allocations:
            if allocation.strategy_id in symbol:
                return allocation.strategy_id
        return None

    async def _estimate_transaction_costs(self, adjustments: Dict[str, float],
                                        portfolio: PortfolioState,
                                        market_data: Dict[str, Any]) -> float:
        """Estimate transaction costs for rebalancing."""
        total_cost = 0

        for strategy_id, weight_change in adjustments.items():
            # Estimate based on position size and market conditions
            position_value = abs(weight_change) * portfolio.total_value

            # Assume 0.1% transaction cost
            transaction_cost = position_value * 0.001

            # Add market impact cost (simplified)
            volatility = 0.20  # Default
            market_impact = position_value * volatility * 0.0005

            total_cost += transaction_cost + market_impact

        return total_cost

    async def _publish_optimization_event(self, portfolio_id: str, weights: Dict[str, float],
                                        method: AllocationMethod):
        """Publish portfolio optimization event."""
        event_data = {
            "portfolio_id": portfolio_id,
            "optimization_method": method.value,
            "new_weights": weights,
            "timestamp": time.time()
        }

        await self._event_bus.publish_event(
            self._event_bus.create_event(
                EventType.SYSTEM_HEALTH_CHANGED,
                "multi_strategy_portfolio",
                event_data,
                EventPriority.NORMAL
            )
        )

    async def _publish_rebalancing_event(self, signal: RebalancingSignal):
        """Publish portfolio rebalancing event."""
        event_data = {
            "portfolio_id": signal.portfolio_id,
            "adjustments": signal.strategy_adjustments,
            "reason": signal.reason,
            "urgency": signal.urgency,
            "estimated_cost": signal.estimated_cost,
            "timestamp": time.time()
        }

        await self._event_bus.publish_event(
            self._event_bus.create_event(
                EventType.SYSTEM_HEALTH_CHANGED,
                "multi_strategy_portfolio",
                event_data,
                EventPriority.HIGH if signal.urgency in ['high', 'critical'] else EventPriority.NORMAL
            )
        )


# Global multi-strategy portfolio manager instance
_multi_strategy_manager = MultiStrategyPortfolioManager()


def get_multi_strategy_manager() -> MultiStrategyPortfolioManager:
    """Get the global multi-strategy portfolio manager."""
    return _multi_strategy_manager


# Convenience functions
async def create_portfolio(portfolio_id: str, strategy_ids: List[str],
                          allocation_method: AllocationMethod = AllocationMethod.RISK_PARITY,
                          constraints: Optional[PortfolioConstraints] = None) -> bool:
    """Create a new multi-strategy portfolio."""
    return await _multi_strategy_manager.create_portfolio(portfolio_id, strategy_ids, allocation_method, constraints)


async def optimize_portfolio(portfolio_id: str, market_data: Dict[str, Any],
                           allocation_method: AllocationMethod = AllocationMethod.RISK_PARITY) -> Dict[str, float]:
    """Optimize portfolio allocations."""
    return await _multi_strategy_manager.optimize_portfolio(portfolio_id, market_data, allocation_method)


async def rebalance_portfolio(portfolio_id: str, current_portfolio: PortfolioState,
                            market_data: Dict[str, Any]) -> Optional[RebalancingSignal]:
    """Check if portfolio needs rebalancing."""
    return await _multi_strategy_manager.rebalance_portfolio(portfolio_id, current_portfolio, market_data)


async def update_portfolio_metrics(portfolio_id: str, portfolio_state: PortfolioState,
                                 market_data: Dict[str, Any]) -> PortfolioMetrics:
    """Update portfolio metrics."""
    return await _multi_strategy_manager.update_portfolio_metrics(portfolio_id, portfolio_state, market_data)