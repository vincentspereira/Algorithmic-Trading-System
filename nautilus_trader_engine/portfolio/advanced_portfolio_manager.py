"""Advanced Portfolio Management System for Phase 1

Provides sophisticated portfolio management with:
- Multi-asset class support (equities, bonds, options, futures, crypto)
- Dynamic rebalancing with multiple strategies
- Advanced risk management and optimization
- Real-time portfolio monitoring and analytics
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict
import uuid

from ..risk.portfolio_optimizer import (
    PortfolioOptimizationEngine, OptimizationMethod, ObjectiveFunction,
    Asset, OptimizationConstraints, OptimizationResult
)


class AssetClass(Enum):
    """Supported asset classes"""
    EQUITY = "equity"
    BOND = "bond"
    OPTION = "option"
    FUTURE = "future"
    CRYPTO = "crypto"
    COMMODITY = "commodity"
    FOREX = "forex"
    REIT = "reit"


class RebalancingStrategy(Enum):
    """Portfolio rebalancing strategies"""
    PERIODIC = "periodic"  # Time-based rebalancing
    THRESHOLD = "threshold"  # Drift-based rebalancing
    VOLATILITY_TARGET = "volatility_target"  # Risk-based rebalancing
    MOMENTUM = "momentum"  # Trend-following rebalancing
    MEAN_REVERSION = "mean_reversion"  # Contrarian rebalancing
    RISK_PARITY = "risk_parity"  # Equal risk contribution
    BLACK_LITTERMAN = "black_litterman"  # View-based rebalancing


class RebalancingFrequency(Enum):
    """Rebalancing frequency options"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"


@dataclass
class AssetAllocation:
    """Asset allocation specification"""
    symbol: str
    asset_class: AssetClass
    target_weight: float
    min_weight: float = 0.0
    max_weight: float = 1.0
    
    # Risk parameters
    volatility_target: Optional[float] = None
    max_drawdown: Optional[float] = None
    
    # Rebalancing parameters
    rebalancing_threshold: float = 0.05  # 5% drift threshold
    transaction_cost: float = 0.001  # 10 bps
    
    # Asset-specific parameters
    sector: Optional[str] = None
    country: Optional[str] = None
    currency: str = "USD"
    
    # Market data
    current_price: float = 0.0
    market_value: float = 0.0
    quantity: float = 0.0


@dataclass
class PortfolioConstraints:
    """Advanced portfolio constraints"""
    # Weight constraints
    max_single_asset_weight: float = 0.10  # 10% max per asset
    max_sector_weight: float = 0.25  # 25% max per sector
    max_country_weight: float = 0.30  # 30% max per country
    
    # Risk constraints
    max_portfolio_volatility: float = 0.20  # 20% max volatility
    max_portfolio_drawdown: float = 0.15  # 15% max drawdown
    max_var_95: float = 0.05  # 5% max VaR
    
    # Asset class constraints
    asset_class_limits: Dict[AssetClass, Tuple[float, float]] = field(default_factory=dict)
    
    # Liquidity constraints
    min_liquidity_ratio: float = 0.05  # 5% minimum cash
    max_illiquid_assets: float = 0.20  # 20% max illiquid assets
    
    # Leverage constraints
    max_leverage: float = 1.0  # No leverage by default
    
    # Turnover constraints
    max_annual_turnover: float = 2.0  # 200% max annual turnover


@dataclass
class RebalancingConfig:
    """Rebalancing configuration"""
    strategy: RebalancingStrategy
    frequency: RebalancingFrequency
    
    # Threshold-based parameters
    drift_threshold: float = 0.05  # 5% drift threshold
    
    # Volatility targeting parameters
    target_volatility: float = 0.12  # 12% target volatility
    volatility_lookback: int = 252  # 1 year lookback
    
    # Risk parity parameters
    risk_budget_tolerance: float = 0.01  # 1% tolerance
    
    # Transaction cost parameters
    min_trade_size: float = 1000.0  # Minimum $1000 trade
    max_transaction_cost: float = 0.005  # 50 bps max cost
    
    # Timing parameters
    rebalancing_time: str = "09:30"  # Market open
    blackout_periods: List[Tuple[datetime, datetime]] = field(default_factory=list)


@dataclass
class PortfolioMetrics:
    """Comprehensive portfolio metrics"""
    # Basic metrics
    total_value: float
    cash_balance: float
    invested_value: float
    
    # Performance metrics
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    
    # Risk metrics
    var_95: float
    var_99: float
    expected_shortfall: float
    beta: float
    
    # Allocation metrics
    asset_class_allocation: Dict[AssetClass, float]
    sector_allocation: Dict[str, float]
    country_allocation: Dict[str, float]
    
    # Efficiency metrics
    diversification_ratio: float
    effective_assets: float
    concentration_index: float
    turnover: float
    
    # Timestamp
    calculation_time: datetime


class AdvancedPortfolioManager:
    """Advanced Portfolio Management System"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the advanced portfolio manager"""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Portfolio storage
        self.portfolios: Dict[str, Dict[str, Any]] = {}
        self.allocations: Dict[str, List[AssetAllocation]] = {}
        self.constraints: Dict[str, PortfolioConstraints] = {}
        self.rebalancing_configs: Dict[str, RebalancingConfig] = {}
        
        # Optimization engine
        self.optimization_engine = PortfolioOptimizationEngine(
            enable_real_time=True,
            optimization_interval_seconds=300
        )
        
        # Performance tracking
        self.performance_history: Dict[str, List[PortfolioMetrics]] = defaultdict(list)
        self.rebalancing_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Market data cache
        self.market_data_cache: Dict[str, Dict[str, Any]] = {}
        
        # Risk monitoring
        self.risk_alerts: List[Dict[str, Any]] = []
        
    async def initialize(self):
        """Initialize the portfolio manager"""
        await self.optimization_engine.start()
        self.logger.info("Advanced Portfolio Manager initialized")
    
    async def shutdown(self):
        """Shutdown the portfolio manager"""
        await self.optimization_engine.stop()
        self.logger.info("Advanced Portfolio Manager shutdown")
    
    def create_portfolio(
        self,
        account_id: str,
        initial_capital: float,
        base_currency: str = "USD",
        constraints: Optional[PortfolioConstraints] = None,
        rebalancing_config: Optional[RebalancingConfig] = None
    ) -> str:
        """Create a new advanced portfolio"""
        
        portfolio_id = f"ADV_PORT_{str(uuid.uuid4())[:8].upper()}"
        
        # Initialize portfolio
        portfolio = {
            'portfolio_id': portfolio_id,
            'account_id': account_id,
            'base_currency': base_currency,
            'initial_capital': initial_capital,
            'current_value': initial_capital,
            'cash_balance': initial_capital,
            'created_at': datetime.now(),
            'last_rebalanced': datetime.now(),
            'status': 'active'
        }
        
        self.portfolios[portfolio_id] = portfolio
        self.allocations[portfolio_id] = []
        
        # Set constraints
        self.constraints[portfolio_id] = constraints or PortfolioConstraints()
        
        # Set rebalancing config
        self.rebalancing_configs[portfolio_id] = rebalancing_config or RebalancingConfig(
            strategy=RebalancingStrategy.THRESHOLD,
            frequency=RebalancingFrequency.MONTHLY
        )
        
        self.logger.info(f"Created advanced portfolio {portfolio_id} for account {account_id}")
        return portfolio_id
    
    def set_target_allocation(
        self,
        portfolio_id: str,
        allocations: List[AssetAllocation]
    ) -> bool:
        """Set target asset allocation for portfolio"""
        
        if portfolio_id not in self.portfolios:
            self.logger.error(f"Portfolio {portfolio_id} not found")
            return False
        
        # Validate allocations
        total_weight = sum(alloc.target_weight for alloc in allocations)
        if abs(total_weight - 1.0) > 0.001:
            self.logger.error(f"Target weights sum to {total_weight}, not 1.0")
            return False
        
        # Validate constraints
        constraints = self.constraints[portfolio_id]
        for alloc in allocations:
            if alloc.target_weight > constraints.max_single_asset_weight:
                self.logger.error(
                    f"Asset {alloc.symbol} weight {alloc.target_weight} exceeds max {constraints.max_single_asset_weight}"
                )
                return False
        
        self.allocations[portfolio_id] = allocations
        self.logger.info(f"Set target allocation for portfolio {portfolio_id}")
        return True
    
    async def calculate_portfolio_metrics(self, portfolio_id: str) -> Optional[PortfolioMetrics]:
        """Calculate comprehensive portfolio metrics"""
        
        if portfolio_id not in self.portfolios:
            return None
        
        portfolio = self.portfolios[portfolio_id]
        allocations = self.allocations[portfolio_id]
        
        # Update market values
        await self._update_market_values(portfolio_id)
        
        # Calculate basic metrics
        total_value = portfolio['current_value']
        cash_balance = portfolio['cash_balance']
        invested_value = total_value - cash_balance
        
        # Calculate performance metrics
        total_return = (total_value - portfolio['initial_capital']) / portfolio['initial_capital']
        
        # Calculate risk metrics (simplified for now)
        volatility = 0.15  # Placeholder
        sharpe_ratio = total_return / volatility if volatility > 0 else 0.0
        
        # Calculate allocation metrics
        asset_class_allocation = self._calculate_asset_class_allocation(allocations)
        sector_allocation = self._calculate_sector_allocation(allocations)
        country_allocation = self._calculate_country_allocation(allocations)
        
        # Calculate efficiency metrics
        diversification_ratio = self._calculate_diversification_ratio(allocations)
        effective_assets = self._calculate_effective_assets(allocations)
        concentration_index = self._calculate_concentration_index(allocations)
        
        metrics = PortfolioMetrics(
            total_value=total_value,
            cash_balance=cash_balance,
            invested_value=invested_value,
            total_return=total_return,
            annualized_return=total_return,  # Simplified
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sharpe_ratio * 1.2,  # Approximation
            max_drawdown=0.05,  # Placeholder
            var_95=0.03,  # Placeholder
            var_99=0.05,  # Placeholder
            expected_shortfall=0.06,  # Placeholder
            beta=1.0,  # Placeholder
            asset_class_allocation=asset_class_allocation,
            sector_allocation=sector_allocation,
            country_allocation=country_allocation,
            diversification_ratio=diversification_ratio,
            effective_assets=effective_assets,
            concentration_index=concentration_index,
            turnover=0.0,  # Placeholder
            calculation_time=datetime.now()
        )
        
        # Store metrics history
        self.performance_history[portfolio_id].append(metrics)
        
        return metrics
    
    async def check_rebalancing_needed(self, portfolio_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Check if portfolio needs rebalancing"""
        
        if portfolio_id not in self.portfolios:
            return False, {'error': 'Portfolio not found'}
        
        config = self.rebalancing_configs[portfolio_id]
        allocations = self.allocations[portfolio_id]
        
        # Update market values
        await self._update_market_values(portfolio_id)
        
        # Calculate current weights
        current_weights = self._calculate_current_weights(portfolio_id)
        
        # Check rebalancing conditions
        rebalancing_needed = False
        reasons = []
        
        if config.strategy == RebalancingStrategy.THRESHOLD:
            # Check drift threshold
            for alloc in allocations:
                current_weight = current_weights.get(alloc.symbol, 0.0)
                drift = abs(current_weight - alloc.target_weight)
                
                if drift > config.drift_threshold:
                    rebalancing_needed = True
                    reasons.append(f"{alloc.symbol}: drift {drift:.3f} > threshold {config.drift_threshold}")
        
        elif config.strategy == RebalancingStrategy.PERIODIC:
            # Check time since last rebalancing
            last_rebalanced = self.portfolios[portfolio_id]['last_rebalanced']
            time_since_rebalance = datetime.now() - last_rebalanced
            
            frequency_days = {
                RebalancingFrequency.DAILY: 1,
                RebalancingFrequency.WEEKLY: 7,
                RebalancingFrequency.MONTHLY: 30,
                RebalancingFrequency.QUARTERLY: 90,
                RebalancingFrequency.SEMI_ANNUAL: 180,
                RebalancingFrequency.ANNUAL: 365
            }
            
            if time_since_rebalance.days >= frequency_days[config.frequency]:
                rebalancing_needed = True
                reasons.append(f"Periodic rebalancing due: {time_since_rebalance.days} days since last rebalance")
        
        return rebalancing_needed, {
            'reasons': reasons,
            'current_weights': current_weights,
            'target_weights': {alloc.symbol: alloc.target_weight for alloc in allocations}
        }
    
    async def execute_rebalancing(self, portfolio_id: str) -> Dict[str, Any]:
        """Execute portfolio rebalancing"""
        
        if portfolio_id not in self.portfolios:
            return {'error': 'Portfolio not found'}
        
        try:
            # Check if rebalancing is needed
            needed, analysis = await self.check_rebalancing_needed(portfolio_id)
            
            if not needed:
                return {
                    'status': 'no_rebalancing_needed',
                    'analysis': analysis
                }
            
            # Prepare assets for optimization
            assets = await self._prepare_assets_for_optimization(portfolio_id)
            
            # Get optimization constraints
            opt_constraints = self._get_optimization_constraints(portfolio_id)
            
            # Run optimization
            config = self.rebalancing_configs[portfolio_id]
            method = self._get_optimization_method(config.strategy)
            
            result = await self.optimization_engine.optimize_portfolio(
                portfolio_id=portfolio_id,
                assets=assets,
                method=method,
                constraints=opt_constraints,
                objective=ObjectiveFunction.MAXIMIZE_SHARPE
            )
            
            if not result.convergence:
                return {
                    'status': 'optimization_failed',
                    'error': 'Portfolio optimization did not converge'
                }
            
            # Generate trading orders
            orders = await self._generate_rebalancing_orders(portfolio_id, result)
            
            # Update portfolio state
            self.portfolios[portfolio_id]['last_rebalanced'] = datetime.now()
            
            # Record rebalancing history
            rebalancing_record = {
                'timestamp': datetime.now(),
                'strategy': config.strategy.value,
                'optimization_result': result,
                'orders': orders,
                'total_turnover': result.turnover,
                'transaction_cost': result.total_transaction_cost
            }
            
            self.rebalancing_history[portfolio_id].append(rebalancing_record)
            
            self.logger.info(f"Executed rebalancing for portfolio {portfolio_id}")
            
            return {
                'status': 'completed',
                'rebalancing_record': rebalancing_record,
                'orders': orders
            }
            
        except Exception as e:
            self.logger.error(f"Error executing rebalancing for {portfolio_id}: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def monitor_risk_limits(self, portfolio_id: str) -> Dict[str, Any]:
        """Monitor portfolio risk limits"""
        
        if portfolio_id not in self.portfolios:
            return {'error': 'Portfolio not found'}
        
        constraints = self.constraints[portfolio_id]
        metrics = await self.calculate_portfolio_metrics(portfolio_id)
        
        if not metrics:
            return {'error': 'Could not calculate metrics'}
        
        violations = []
        warnings = []
        
        # Check volatility limit
        if metrics.volatility > constraints.max_portfolio_volatility:
            violations.append({
                'type': 'volatility_breach',
                'current': metrics.volatility,
                'limit': constraints.max_portfolio_volatility
            })
        
        # Check drawdown limit
        if metrics.max_drawdown > constraints.max_portfolio_drawdown:
            violations.append({
                'type': 'drawdown_breach',
                'current': metrics.max_drawdown,
                'limit': constraints.max_portfolio_drawdown
            })
        
        # Check VaR limit
        if metrics.var_95 > constraints.max_var_95:
            violations.append({
                'type': 'var_breach',
                'current': metrics.var_95,
                'limit': constraints.max_var_95
            })
        
        # Check concentration limits
        for asset_class, allocation in metrics.asset_class_allocation.items():
            if asset_class in constraints.asset_class_limits:
                min_limit, max_limit = constraints.asset_class_limits[asset_class]
                if allocation > max_limit:
                    violations.append({
                        'type': 'asset_class_concentration',
                        'asset_class': asset_class.value,
                        'current': allocation,
                        'limit': max_limit
                    })
        
        # Store risk alerts
        if violations:
            alert = {
                'portfolio_id': portfolio_id,
                'timestamp': datetime.now(),
                'violations': violations,
                'warnings': warnings
            }
            self.risk_alerts.append(alert)
        
        return {
            'violations': violations,
            'warnings': warnings,
            'metrics': metrics
        }
    
    # Helper methods
    
    async def _update_market_values(self, portfolio_id: str):
        """Update market values for all positions"""
        # Placeholder - would integrate with market data service
        pass
    
    def _calculate_current_weights(self, portfolio_id: str) -> Dict[str, float]:
        """Calculate current portfolio weights"""
        allocations = self.allocations[portfolio_id]
        total_value = sum(alloc.market_value for alloc in allocations)
        
        if total_value == 0:
            return {}
        
        return {
            alloc.symbol: alloc.market_value / total_value
            for alloc in allocations
        }
    
    def _calculate_asset_class_allocation(self, allocations: List[AssetAllocation]) -> Dict[AssetClass, float]:
        """Calculate asset class allocation"""
        allocation_by_class = defaultdict(float)
        total_value = sum(alloc.market_value for alloc in allocations)
        
        if total_value == 0:
            return {}
        
        for alloc in allocations:
            allocation_by_class[alloc.asset_class] += alloc.market_value / total_value
        
        return dict(allocation_by_class)
    
    def _calculate_sector_allocation(self, allocations: List[AssetAllocation]) -> Dict[str, float]:
        """Calculate sector allocation"""
        allocation_by_sector = defaultdict(float)
        total_value = sum(alloc.market_value for alloc in allocations)
        
        if total_value == 0:
            return {}
        
        for alloc in allocations:
            if alloc.sector:
                allocation_by_sector[alloc.sector] += alloc.market_value / total_value
        
        return dict(allocation_by_sector)
    
    def _calculate_country_allocation(self, allocations: List[AssetAllocation]) -> Dict[str, float]:
        """Calculate country allocation"""
        allocation_by_country = defaultdict(float)
        total_value = sum(alloc.market_value for alloc in allocations)
        
        if total_value == 0:
            return {}
        
        for alloc in allocations:
            if alloc.country:
                allocation_by_country[alloc.country] += alloc.market_value / total_value
        
        return dict(allocation_by_country)
    
    def _calculate_diversification_ratio(self, allocations: List[AssetAllocation]) -> float:
        """Calculate portfolio diversification ratio"""
        # Simplified calculation - would use actual correlation matrix
        return min(len(allocations) / 10.0, 1.0)
    
    def _calculate_effective_assets(self, allocations: List[AssetAllocation]) -> float:
        """Calculate effective number of assets (inverse Herfindahl index)"""
        weights = [alloc.target_weight for alloc in allocations]
        herfindahl = sum(w**2 for w in weights)
        return 1.0 / herfindahl if herfindahl > 0 else 0.0
    
    def _calculate_concentration_index(self, allocations: List[AssetAllocation]) -> float:
        """Calculate concentration index (Herfindahl index)"""
        weights = [alloc.target_weight for alloc in allocations]
        return sum(w**2 for w in weights)
    
    async def _prepare_assets_for_optimization(self, portfolio_id: str) -> List[Asset]:
        """Prepare assets for portfolio optimization"""
        allocations = self.allocations[portfolio_id]
        assets = []
        
        for alloc in allocations:
            asset = Asset(
                symbol=alloc.symbol,
                name=alloc.symbol,  # Simplified
                expected_return=0.08,  # Placeholder
                volatility=0.15,  # Placeholder
                current_price=alloc.current_price,
                sector=alloc.sector,
                country=alloc.country,
                min_weight=alloc.min_weight,
                max_weight=alloc.max_weight,
                transaction_cost=alloc.transaction_cost
            )
            assets.append(asset)
        
        return assets
    
    def _get_optimization_constraints(self, portfolio_id: str) -> OptimizationConstraints:
        """Get optimization constraints for portfolio"""
        constraints = self.constraints[portfolio_id]
        allocations = self.allocations[portfolio_id]
        
        # Build weight constraints
        min_weights = {alloc.symbol: alloc.min_weight for alloc in allocations}
        max_weights = {alloc.symbol: alloc.max_weight for alloc in allocations}
        
        return OptimizationConstraints(
            min_weights=min_weights,
            max_weights=max_weights,
            max_portfolio_risk=constraints.max_portfolio_volatility,
            long_only=True,
            max_leverage=constraints.max_leverage,
            max_turnover=constraints.max_annual_turnover / 12  # Monthly limit
        )
    
    def _get_optimization_method(self, strategy: RebalancingStrategy) -> OptimizationMethod:
        """Get optimization method for rebalancing strategy"""
        method_mapping = {
            RebalancingStrategy.RISK_PARITY: OptimizationMethod.RISK_PARITY,
            RebalancingStrategy.BLACK_LITTERMAN: OptimizationMethod.BLACK_LITTERMAN,
            RebalancingStrategy.THRESHOLD: OptimizationMethod.MEAN_VARIANCE,
            RebalancingStrategy.PERIODIC: OptimizationMethod.MEAN_VARIANCE,
            RebalancingStrategy.VOLATILITY_TARGET: OptimizationMethod.MINIMUM_VARIANCE,
            RebalancingStrategy.MOMENTUM: OptimizationMethod.MAXIMUM_RETURN,
            RebalancingStrategy.MEAN_REVERSION: OptimizationMethod.MEAN_VARIANCE
        }
        
        return method_mapping.get(strategy, OptimizationMethod.MEAN_VARIANCE)
    
    async def _generate_rebalancing_orders(self, portfolio_id: str, result: OptimizationResult) -> List[Dict[str, Any]]:
        """Generate trading orders for rebalancing"""
        portfolio = self.portfolios[portfolio_id]
        current_weights = self._calculate_current_weights(portfolio_id)
        total_value = portfolio['current_value']
        
        orders = []
        
        for symbol, target_weight in result.weights.items():
            current_weight = current_weights.get(symbol, 0.0)
            weight_diff = target_weight - current_weight
            
            if abs(weight_diff) > 0.001:  # 0.1% threshold
                trade_value = weight_diff * total_value
                
                order = {
                    'symbol': symbol,
                    'side': 'buy' if weight_diff > 0 else 'sell',
                    'value': abs(trade_value),
                    'current_weight': current_weight,
                    'target_weight': target_weight,
                    'weight_change': weight_diff
                }
                
                orders.append(order)
        
        return orders
    
    def get_portfolio_summary(self, portfolio_id: str) -> Dict[str, Any]:
        """Get comprehensive portfolio summary"""
        
        if portfolio_id not in self.portfolios:
            return {'error': 'Portfolio not found'}
        
        portfolio = self.portfolios[portfolio_id]
        allocations = self.allocations[portfolio_id]
        constraints = self.constraints[portfolio_id]
        config = self.rebalancing_configs[portfolio_id]
        
        # Get latest metrics
        latest_metrics = None
        if self.performance_history[portfolio_id]:
            latest_metrics = self.performance_history[portfolio_id][-1]
        
        return {
            'portfolio_info': portfolio,
            'allocations': [{
                'symbol': alloc.symbol,
                'asset_class': alloc.asset_class.value,
                'target_weight': alloc.target_weight,
                'current_weight': alloc.market_value / portfolio['current_value'] if portfolio['current_value'] > 0 else 0,
                'market_value': alloc.market_value,
                'sector': alloc.sector,
                'country': alloc.country
            } for alloc in allocations],
            'constraints': {
                'max_single_asset_weight': constraints.max_single_asset_weight,
                'max_portfolio_volatility': constraints.max_portfolio_volatility,
                'max_leverage': constraints.max_leverage
            },
            'rebalancing_config': {
                'strategy': config.strategy.value,
                'frequency': config.frequency.value,
                'drift_threshold': config.drift_threshold
            },
            'latest_metrics': latest_metrics.__dict__ if latest_metrics else None,
            'rebalancing_history_count': len(self.rebalancing_history[portfolio_id]),
            'risk_alerts_count': len([alert for alert in self.risk_alerts if alert['portfolio_id'] == portfolio_id])
        }


# Global instance
_advanced_portfolio_manager: Optional[AdvancedPortfolioManager] = None


def get_advanced_portfolio_manager() -> AdvancedPortfolioManager:
    """Get the global advanced portfolio manager instance"""
    global _advanced_portfolio_manager
    if _advanced_portfolio_manager is None:
        _advanced_portfolio_manager = AdvancedPortfolioManager()
    return _advanced_portfolio_manager


async def initialize_advanced_portfolio_manager(config: Dict[str, Any] = None) -> AdvancedPortfolioManager:
    """Initialize the global advanced portfolio manager"""
    global _advanced_portfolio_manager
    _advanced_portfolio_manager = AdvancedPortfolioManager(config)
    await _advanced_portfolio_manager.initialize()
    return _advanced_portfolio_manager