"""
Unified Margin System
Comprehensive margin calculation system supporting portfolio margin, SPAN margin for futures,
options margin requirements, and margin optimization strategies across all asset classes.
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
import math

# Suppress numpy warnings
warnings.filterwarnings('ignore', category=RuntimeWarning)

try:
    from scipy import stats, optimize
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    stats = None
    optimize = None


class MarginType(Enum):
    """Types of margin calculations"""
    INITIAL = "initial"
    MAINTENANCE = "maintenance"
    PORTFOLIO = "portfolio"
    SPAN = "span"
    OPTIONS = "options"
    CROSS_MARGIN = "cross_margin"


class AssetClass(Enum):
    """Asset classes for margin calculation"""
    EQUITY = "equity"
    OPTION = "option"
    FUTURE = "future"
    BOND = "bond"
    FOREX = "forex"
    CRYPTOCURRENCY = "cryptocurrency"


class RiskScenario(Enum):
    """Risk scenarios for SPAN margin calculation"""
    PRICE_UP_VOLATILITY_UP = "price_up_vol_up"
    PRICE_UP_VOLATILITY_DOWN = "price_up_vol_down"
    PRICE_DOWN_VOLATILITY_UP = "price_down_vol_up"
    PRICE_DOWN_VOLATILITY_DOWN = "price_down_vol_down"
    PRICE_UNCHANGED_VOLATILITY_UP = "price_unchanged_vol_up"
    PRICE_UNCHANGED_VOLATILITY_DOWN = "price_unchanged_vol_down"


@dataclass
class Position:
    """Position information for margin calculation"""
    symbol: str
    asset_class: AssetClass
    quantity: float
    current_price: float
    market_value: float
    
    # Asset-specific attributes
    underlying_symbol: Optional[str] = None
    strike_price: Optional[float] = None
    expiry_date: Optional[datetime] = None
    option_type: Optional[str] = None  # 'call' or 'put'
    
    # Risk attributes
    volatility: float = 0.0
    beta: float = 1.0
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    
    # Margin attributes
    initial_margin_rate: float = 0.0
    maintenance_margin_rate: float = 0.0
    
    # Metadata
    exchange: str = ""
    currency: str = "USD"
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class MarginRequirement:
    """Margin requirement result"""
    position_id: str
    margin_type: MarginType
    required_margin: float
    excess_margin: float
    margin_utilization: float
    
    # Breakdown
    initial_margin: float = 0.0
    maintenance_margin: float = 0.0
    portfolio_margin: float = 0.0
    
    # Risk metrics
    leverage: float = 1.0
    risk_score: float = 0.0
    
    # Calculation details
    calculation_method: str = ""
    risk_scenarios: Dict[str, float] = field(default_factory=dict)
    offsets: Dict[str, float] = field(default_factory=dict)
    
    calculated_at: datetime = field(default_factory=datetime.now)


@dataclass
class PortfolioMarginResult:
    """Portfolio-level margin calculation result"""
    total_margin_required: float
    total_excess_margin: float
    portfolio_leverage: float
    margin_utilization: float
    
    # By asset class
    margin_by_asset_class: Dict[str, float] = field(default_factory=dict)
    
    # Risk metrics
    portfolio_var: float = 0.0
    diversification_benefit: float = 0.0
    concentration_risk: float = 0.0
    
    # Optimization
    optimization_opportunities: List[str] = field(default_factory=list)
    potential_savings: float = 0.0
    
    calculation_timestamp: datetime = field(default_factory=datetime.now)


class EquityMarginCalculator:
    """Calculates margin requirements for equity positions"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Default margin rates (can be customized per broker/exchange)
        self.default_initial_margin_rate = 0.50  # 50% for long positions
        self.default_maintenance_margin_rate = 0.25  # 25% for long positions
        self.short_margin_rate = 1.50  # 150% for short positions
        
    async def calculate_margin(self, position: Position) -> MarginRequirement:
        """Calculate margin requirement for equity position"""
        try:
            market_value = abs(position.market_value)
            
            # Determine margin rates based on position type
            if position.quantity > 0:  # Long position
                initial_rate = position.initial_margin_rate or self.default_initial_margin_rate
                maintenance_rate = position.maintenance_margin_rate or self.default_maintenance_margin_rate
            else:  # Short position
                initial_rate = self.short_margin_rate
                maintenance_rate = self.short_margin_rate * 0.8  # 80% of initial for maintenance
            
            # Calculate margin requirements
            initial_margin = market_value * initial_rate
            maintenance_margin = market_value * maintenance_rate
            
            # Risk-based adjustments
            volatility_adjustment = 1.0 + (position.volatility * 2.0)  # Higher vol = higher margin
            beta_adjustment = 1.0 + (abs(position.beta - 1.0) * 0.5)  # Higher beta = higher margin
            
            adjusted_initial = initial_margin * volatility_adjustment * beta_adjustment
            adjusted_maintenance = maintenance_margin * volatility_adjustment * beta_adjustment
            
            return MarginRequirement(
                position_id=position.symbol,
                margin_type=MarginType.INITIAL,
                required_margin=adjusted_initial,
                excess_margin=0.0,  # Will be calculated at portfolio level
                margin_utilization=0.0,  # Will be calculated at portfolio level
                initial_margin=adjusted_initial,
                maintenance_margin=adjusted_maintenance,
                leverage=1.0 / initial_rate if initial_rate > 0 else 1.0,
                risk_score=volatility_adjustment * beta_adjustment,
                calculation_method="Equity Standard Margin"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to calculate equity margin for {position.symbol}: {e}")
            return MarginRequirement(
                position_id=position.symbol,
                margin_type=MarginType.INITIAL,
                required_margin=abs(position.market_value) * 0.5,  # Fallback to 50%
                excess_margin=0.0,
                margin_utilization=0.0,
                calculation_method="Equity Fallback Margin"
            )


class OptionsMarginCalculator:
    """Calculates margin requirements for options positions"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    async def calculate_margin(self, position: Position) -> MarginRequirement:
        """Calculate margin requirement for options position"""
        try:
            if position.quantity > 0:
                # Long options - premium paid, no additional margin required
                return MarginRequirement(
                    position_id=position.symbol,
                    margin_type=MarginType.OPTIONS,
                    required_margin=0.0,
                    excess_margin=0.0,
                    margin_utilization=0.0,
                    calculation_method="Long Options - Premium Only"
                )
            else:
                # Short options - calculate margin requirement
                return await self._calculate_short_option_margin(position)
                
        except Exception as e:
            self.logger.error(f"Failed to calculate options margin for {position.symbol}: {e}")
            return MarginRequirement(
                position_id=position.symbol,
                margin_type=MarginType.OPTIONS,
                required_margin=abs(position.market_value) * 2.0,  # Conservative fallback
                excess_margin=0.0,
                margin_utilization=0.0,
                calculation_method="Options Fallback Margin"
            )
    
    async def _calculate_short_option_margin(self, position: Position) -> MarginRequirement:
        """Calculate margin for short options positions"""
        try:
            # Get underlying price (assuming it's available)
            underlying_price = position.current_price / abs(position.delta) if position.delta != 0 else position.current_price
            
            # Standard options margin calculation
            option_premium = abs(position.market_value)
            
            if position.option_type == "call":
                # Short call margin
                out_of_money = max(0, position.strike_price - underlying_price)
                margin_requirement = option_premium + max(
                    0.20 * underlying_price - out_of_money,
                    0.10 * underlying_price
                )
            else:  # put
                # Short put margin
                out_of_money = max(0, underlying_price - position.strike_price)
                margin_requirement = option_premium + max(
                    0.20 * underlying_price - out_of_money,
                    0.10 * position.strike_price
                )
            
            # Risk adjustments
            volatility_adjustment = 1.0 + (position.volatility * 1.5)
            time_decay_adjustment = 1.0 + max(0, -position.theta * 30)  # 30-day theta impact
            
            adjusted_margin = margin_requirement * volatility_adjustment * time_decay_adjustment
            
            return MarginRequirement(
                position_id=position.symbol,
                margin_type=MarginType.OPTIONS,
                required_margin=adjusted_margin,
                excess_margin=0.0,
                margin_utilization=0.0,
                initial_margin=adjusted_margin,
                maintenance_margin=adjusted_margin * 0.8,
                leverage=underlying_price / adjusted_margin if adjusted_margin > 0 else 1.0,
                risk_score=volatility_adjustment * time_decay_adjustment,
                calculation_method="Short Options Standard Margin"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to calculate short option margin: {e}")
            return MarginRequirement(
                position_id=position.symbol,
                margin_type=MarginType.OPTIONS,
                required_margin=abs(position.market_value) * 2.0,
                excess_margin=0.0,
                margin_utilization=0.0,
                calculation_method="Short Options Fallback"
            )


class SPANMarginCalculator:
    """Implements SPAN (Standard Portfolio Analysis of Risk) margin calculation for futures"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # SPAN parameters (these would typically be provided by the exchange)
        self.default_price_scan_range = 0.06  # 6% price scan range
        self.default_volatility_scan_range = 0.35  # 35% volatility scan range
        self.minimum_commodity_charge = 0.0
        
    async def calculate_span_margin(self, positions: List[Position]) -> Dict[str, MarginRequirement]:
        """Calculate SPAN margin for a portfolio of futures/options positions"""
        try:
            margin_requirements = {}
            
            # Group positions by underlying commodity/product
            commodity_groups = defaultdict(list)
            for position in positions:
                underlying = position.underlying_symbol or position.symbol
                commodity_groups[underlying].append(position)
            
            # Calculate SPAN margin for each commodity group
            for commodity, commodity_positions in commodity_groups.items():
                span_margin = await self._calculate_commodity_span_margin(commodity, commodity_positions)
                
                for position in commodity_positions:
                    # Allocate SPAN margin proportionally to positions
                    position_weight = abs(position.market_value) / sum(abs(p.market_value) for p in commodity_positions)
                    allocated_margin = span_margin * position_weight
                    
                    margin_requirements[position.symbol] = MarginRequirement(
                        position_id=position.symbol,
                        margin_type=MarginType.SPAN,
                        required_margin=allocated_margin,
                        excess_margin=0.0,
                        margin_utilization=0.0,
                        initial_margin=allocated_margin,
                        maintenance_margin=allocated_margin * 0.8,
                        calculation_method="SPAN Margin",
                        risk_scenarios={}  # Would include detailed scenario results
                    )
            
            return margin_requirements
            
        except Exception as e:
            self.logger.error(f"Failed to calculate SPAN margin: {e}")
            return {}
    
    async def _calculate_commodity_span_margin(self, commodity: str, positions: List[Position]) -> float:
        """Calculate SPAN margin for a single commodity group"""
        try:
            if not positions:
                return 0.0
            
            # Get representative position for commodity parameters
            representative_position = positions[0]
            underlying_price = representative_position.current_price
            
            # Define risk scenarios
            price_up = underlying_price * (1 + self.default_price_scan_range)
            price_down = underlying_price * (1 - self.default_price_scan_range)
            vol_up_factor = 1 + self.default_volatility_scan_range
            vol_down_factor = max(0.1, 1 - self.default_volatility_scan_range)
            
            scenarios = [
                (price_up, vol_up_factor),
                (price_up, vol_down_factor),
                (price_down, vol_up_factor),
                (price_down, vol_down_factor),
                (underlying_price, vol_up_factor),
                (underlying_price, vol_down_factor)
            ]
            
            # Calculate P&L for each scenario
            scenario_pnls = []
            
            for scenario_price, vol_factor in scenarios:
                scenario_pnl = 0.0
                
                for position in positions:
                    if position.asset_class == AssetClass.FUTURE:
                        # Futures P&L
                        price_change = scenario_price - position.current_price
                        position_pnl = position.quantity * price_change
                    elif position.asset_class == AssetClass.OPTION:
                        # Options P&L (simplified Black-Scholes approximation)
                        position_pnl = self._estimate_option_pnl(
                            position, scenario_price, vol_factor
                        )
                    else:
                        position_pnl = 0.0
                    
                    scenario_pnl += position_pnl
                
                scenario_pnls.append(scenario_pnl)
            
            # SPAN margin is the maximum loss across all scenarios
            max_loss = -min(scenario_pnls)  # Convert to positive loss
            
            # Add minimum commodity charge if applicable
            span_margin = max(max_loss, self.minimum_commodity_charge)
            
            return span_margin
            
        except Exception as e:
            self.logger.error(f"Failed to calculate commodity SPAN margin: {e}")
            return sum(abs(p.market_value) * 0.1 for p in positions)  # 10% fallback
    
    def _estimate_option_pnl(self, position: Position, new_price: float, vol_factor: float) -> float:
        """Estimate option P&L for scenario analysis"""
        try:
            # Simplified option P&L estimation using Greeks
            price_change = new_price - position.current_price
            vol_change = (vol_factor - 1.0) * position.volatility
            
            # Delta P&L
            delta_pnl = position.delta * price_change * position.quantity
            
            # Gamma P&L (second-order price effect)
            gamma_pnl = 0.5 * position.gamma * (price_change ** 2) * position.quantity
            
            # Vega P&L (volatility effect)
            vega_pnl = position.vega * vol_change * position.quantity
            
            total_pnl = delta_pnl + gamma_pnl + vega_pnl
            
            return total_pnl
            
        except Exception as e:
            self.logger.error(f"Failed to estimate option P&L: {e}")
            return 0.0


class PortfolioMarginCalculator:
    """Calculates portfolio-level margin with cross-margining benefits"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    async def calculate_portfolio_margin(self, positions: List[Position]) -> PortfolioMarginResult:
        """Calculate portfolio margin with cross-margining benefits"""
        try:
            if not positions:
                return PortfolioMarginResult(
                    total_margin_required=0.0,
                    total_excess_margin=0.0,
                    portfolio_leverage=1.0,
                    margin_utilization=0.0
                )
            
            # Calculate individual position margins
            individual_margins = {}
            total_individual_margin = 0.0
            total_market_value = 0.0
            
            # Initialize calculators
            equity_calc = EquityMarginCalculator()
            options_calc = OptionsMarginCalculator()
            span_calc = SPANMarginCalculator()
            
            # Group positions by asset class
            equity_positions = [p for p in positions if p.asset_class == AssetClass.EQUITY]
            option_positions = [p for p in positions if p.asset_class == AssetClass.OPTION]
            future_positions = [p for p in positions if p.asset_class == AssetClass.FUTURE]
            
            # Calculate margins by asset class
            margin_by_asset_class = {}
            
            # Equity margins
            if equity_positions:
                equity_margin = 0.0
                for position in equity_positions:
                    margin_req = await equity_calc.calculate_margin(position)
                    individual_margins[position.symbol] = margin_req
                    equity_margin += margin_req.required_margin
                    total_market_value += abs(position.market_value)
                
                margin_by_asset_class["equity"] = equity_margin
                total_individual_margin += equity_margin
            
            # Options margins
            if option_positions:
                options_margin = 0.0
                for position in option_positions:
                    margin_req = await options_calc.calculate_margin(position)
                    individual_margins[position.symbol] = margin_req
                    options_margin += margin_req.required_margin
                    total_market_value += abs(position.market_value)
                
                margin_by_asset_class["options"] = options_margin
                total_individual_margin += options_margin
            
            # SPAN margins for futures
            if future_positions:
                span_margins = await span_calc.calculate_span_margin(future_positions)
                futures_margin = sum(margin.required_margin for margin in span_margins.values())
                
                for symbol, margin_req in span_margins.items():
                    individual_margins[symbol] = margin_req
                
                margin_by_asset_class["futures"] = futures_margin
                total_individual_margin += futures_margin
                
                for position in future_positions:
                    total_market_value += abs(position.market_value)
            
            # Calculate portfolio-level benefits
            diversification_benefit = await self._calculate_diversification_benefit(positions)
            correlation_benefit = await self._calculate_correlation_benefit(positions)
            hedging_benefit = await self._calculate_hedging_benefit(positions)
            
            # Total portfolio margin (with benefits)
            total_benefit = diversification_benefit + correlation_benefit + hedging_benefit
            portfolio_margin = max(total_individual_margin - total_benefit, total_individual_margin * 0.5)
            
            # Calculate portfolio metrics
            portfolio_leverage = total_market_value / portfolio_margin if portfolio_margin > 0 else 1.0
            margin_utilization = portfolio_margin / total_market_value if total_market_value > 0 else 0.0
            
            # Identify optimization opportunities
            optimization_opportunities = await self._identify_optimization_opportunities(positions, individual_margins)
            potential_savings = total_individual_margin - portfolio_margin
            
            return PortfolioMarginResult(
                total_margin_required=portfolio_margin,
                total_excess_margin=max(0, total_individual_margin - portfolio_margin),
                portfolio_leverage=portfolio_leverage,
                margin_utilization=margin_utilization,
                margin_by_asset_class=margin_by_asset_class,
                diversification_benefit=diversification_benefit,
                concentration_risk=await self._calculate_concentration_risk(positions),
                optimization_opportunities=optimization_opportunities,
                potential_savings=potential_savings
            )
            
        except Exception as e:
            self.logger.error(f"Failed to calculate portfolio margin: {e}")
            return PortfolioMarginResult(
                total_margin_required=sum(abs(p.market_value) * 0.3 for p in positions),
                total_excess_margin=0.0,
                portfolio_leverage=1.0,
                margin_utilization=0.3
            )
    
    async def _calculate_diversification_benefit(self, positions: List[Position]) -> float:
        """Calculate diversification benefit for margin reduction"""
        try:
            if len(positions) < 2:
                return 0.0
            
            # Simple diversification benefit based on number of positions and asset classes
            unique_asset_classes = len(set(p.asset_class for p in positions))
            num_positions = len(positions)
            
            # Benefit increases with more positions and asset classes
            diversification_factor = min(0.15, (unique_asset_classes - 1) * 0.05 + (num_positions - 1) * 0.01)
            
            total_margin = sum(abs(p.market_value) * 0.3 for p in positions)  # Rough estimate
            return total_margin * diversification_factor
            
        except Exception as e:
            self.logger.error(f"Failed to calculate diversification benefit: {e}")
            return 0.0
    
    async def _calculate_correlation_benefit(self, positions: List[Position]) -> float:
        """Calculate correlation benefit for negatively correlated positions"""
        try:
            # Simplified correlation benefit calculation
            # In practice, this would use actual correlation matrices
            
            benefit = 0.0
            
            # Look for potential hedging relationships
            equity_positions = [p for p in positions if p.asset_class == AssetClass.EQUITY]
            option_positions = [p for p in positions if p.asset_class == AssetClass.OPTION]
            
            # Options hedging equity positions
            for equity_pos in equity_positions:
                for option_pos in option_positions:
                    if (option_pos.underlying_symbol == equity_pos.symbol and
                        np.sign(equity_pos.quantity) != np.sign(option_pos.quantity)):
                        # Potential hedge - reduce margin requirement
                        hedge_benefit = min(abs(equity_pos.market_value), abs(option_pos.market_value)) * 0.1
                        benefit += hedge_benefit
            
            return benefit
            
        except Exception as e:
            self.logger.error(f"Failed to calculate correlation benefit: {e}")
            return 0.0
    
    async def _calculate_hedging_benefit(self, positions: List[Position]) -> float:
        """Calculate explicit hedging benefit"""
        try:
            # Look for explicit hedging strategies
            benefit = 0.0
            
            # Group by underlying
            by_underlying = defaultdict(list)
            for position in positions:
                underlying = position.underlying_symbol or position.symbol
                by_underlying[underlying].append(position)
            
            # Calculate hedging benefit for each underlying
            for underlying, underlying_positions in by_underlying.items():
                if len(underlying_positions) > 1:
                    # Calculate net exposure
                    net_delta = sum(p.quantity * p.delta for p in underlying_positions)
                    gross_delta = sum(abs(p.quantity * p.delta) for p in underlying_positions)
                    
                    if gross_delta > 0:
                        hedge_ratio = 1 - abs(net_delta) / gross_delta
                        hedge_benefit = sum(abs(p.market_value) for p in underlying_positions) * hedge_ratio * 0.05
                        benefit += hedge_benefit
            
            return benefit
            
        except Exception as e:
            self.logger.error(f"Failed to calculate hedging benefit: {e}")
            return 0.0
    
    async def _calculate_concentration_risk(self, positions: List[Position]) -> float:
        """Calculate concentration risk score"""
        try:
            if not positions:
                return 0.0
            
            total_value = sum(abs(p.market_value) for p in positions)
            if total_value == 0:
                return 0.0
            
            # Calculate Herfindahl index for concentration
            weights = [abs(p.market_value) / total_value for p in positions]
            herfindahl_index = sum(w ** 2 for w in weights)
            
            # Normalize to 0-1 scale (1 = maximum concentration)
            max_herfindahl = 1.0  # Single position
            min_herfindahl = 1.0 / len(positions)  # Equal weights
            
            if max_herfindahl > min_herfindahl:
                concentration_risk = (herfindahl_index - min_herfindahl) / (max_herfindahl - min_herfindahl)
            else:
                concentration_risk = 0.0
            
            return concentration_risk
            
        except Exception as e:
            self.logger.error(f"Failed to calculate concentration risk: {e}")
            return 0.0
    
    async def _identify_optimization_opportunities(self, 
                                                positions: List[Position], 
                                                individual_margins: Dict[str, MarginRequirement]) -> List[str]:
        """Identify margin optimization opportunities"""
        try:
            opportunities = []
            
            # High margin utilization positions
            high_margin_positions = [
                pos for pos in positions 
                if individual_margins.get(pos.symbol, MarginRequirement("", MarginType.INITIAL, 0, 0, 0)).risk_score > 1.5
            ]
            
            if high_margin_positions:
                opportunities.append(f"Consider reducing exposure in {len(high_margin_positions)} high-risk positions")
            
            # Unhedged positions
            equity_symbols = {p.symbol for p in positions if p.asset_class == AssetClass.EQUITY}
            option_underlyings = {p.underlying_symbol for p in positions if p.asset_class == AssetClass.OPTION}
            
            unhedged_equities = equity_symbols - option_underlyings
            if unhedged_equities:
                opportunities.append(f"Consider hedging {len(unhedged_equities)} unhedged equity positions")
            
            # Concentration risk
            concentration_risk = await self._calculate_concentration_risk(positions)
            if concentration_risk > 0.7:
                opportunities.append("High concentration risk - consider diversification")
            
            # Asset class imbalance
            asset_class_values = defaultdict(float)
            for pos in positions:
                asset_class_values[pos.asset_class.value] += abs(pos.market_value)
            
            total_value = sum(asset_class_values.values())
            if total_value > 0:
                max_allocation = max(asset_class_values.values()) / total_value
                if max_allocation > 0.8:
                    opportunities.append("Consider cross-asset diversification for margin benefits")
            
            return opportunities
            
        except Exception as e:
            self.logger.error(f"Failed to identify optimization opportunities: {e}")
            return []


class MarginOptimizer:
    """Optimizes margin usage across the portfolio"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    async def optimize_margin_usage(self, 
                                  positions: List[Position], 
                                  available_capital: float,
                                  target_leverage: float = 2.0) -> Dict[str, Any]:
        """Optimize margin usage to maximize capital efficiency"""
        try:
            portfolio_calc = PortfolioMarginCalculator()
            current_portfolio = await portfolio_calc.calculate_portfolio_margin(positions)
            
            optimization_result = {
                "current_margin_usage": current_portfolio.total_margin_required,
                "available_capital": available_capital,
                "current_leverage": current_portfolio.portfolio_leverage,
                "target_leverage": target_leverage,
                "optimization_suggestions": [],
                "potential_improvements": {}
            }
            
            # Calculate optimal position sizing
            if available_capital > current_portfolio.total_margin_required:
                excess_capital = available_capital - current_portfolio.total_margin_required
                
                # Suggest position size increases
                for position in positions:
                    if position.asset_class == AssetClass.EQUITY:
                        # Conservative scaling for equities
                        max_scale_factor = min(2.0, 1 + (excess_capital / current_portfolio.total_margin_required))
                        suggested_scale = min(max_scale_factor, target_leverage / current_portfolio.portfolio_leverage)
                        
                        if suggested_scale > 1.1:  # Only suggest if meaningful increase
                            optimization_result["optimization_suggestions"].append({
                                "type": "position_scaling",
                                "symbol": position.symbol,
                                "current_quantity": position.quantity,
                                "suggested_quantity": position.quantity * suggested_scale,
                                "additional_margin_required": position.market_value * (suggested_scale - 1) * 0.5
                            })
            
            # Suggest hedging strategies
            hedging_suggestions = await self._suggest_hedging_strategies(positions)
            optimization_result["optimization_suggestions"].extend(hedging_suggestions)
            
            # Suggest cross-margining opportunities
            cross_margin_suggestions = await self._suggest_cross_margining(positions)
            optimization_result["optimization_suggestions"].extend(cross_margin_suggestions)
            
            # Calculate potential improvements
            optimization_result["potential_improvements"] = {
                "margin_reduction": current_portfolio.potential_savings,
                "leverage_increase": target_leverage - current_portfolio.portfolio_leverage,
                "capital_efficiency": (target_leverage / current_portfolio.portfolio_leverage - 1) * 100
            }
            
            return optimization_result
            
        except Exception as e:
            self.logger.error(f"Failed to optimize margin usage: {e}")
            return {"error": str(e)}
    
    async def _suggest_hedging_strategies(self, positions: List[Position]) -> List[Dict[str, Any]]:
        """Suggest hedging strategies to reduce margin requirements"""
        suggestions = []
        
        try:
            # Find unhedged equity positions
            equity_positions = [p for p in positions if p.asset_class == AssetClass.EQUITY and p.quantity > 0]
            existing_hedges = {p.underlying_symbol for p in positions if p.asset_class == AssetClass.OPTION}
            
            for equity_pos in equity_positions:
                if equity_pos.symbol not in existing_hedges:
                    # Suggest protective put
                    suggestions.append({
                        "type": "protective_put",
                        "underlying": equity_pos.symbol,
                        "strategy": "Buy protective put to hedge downside risk",
                        "estimated_margin_reduction": equity_pos.market_value * 0.1,
                        "cost_estimate": equity_pos.market_value * 0.02
                    })
            
            # Suggest collar strategies for large positions
            large_positions = [p for p in equity_positions if abs(p.market_value) > 50000]
            for large_pos in large_positions:
                suggestions.append({
                    "type": "collar_strategy",
                    "underlying": large_pos.symbol,
                    "strategy": "Implement collar (buy put, sell call) to reduce margin",
                    "estimated_margin_reduction": large_pos.market_value * 0.15,
                    "net_cost_estimate": large_pos.market_value * 0.005  # Net cost after premium received
                })
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Failed to suggest hedging strategies: {e}")
            return []
    
    async def _suggest_cross_margining(self, positions: List[Position]) -> List[Dict[str, Any]]:
        """Suggest cross-margining opportunities"""
        suggestions = []
        
        try:
            # Group positions by underlying
            by_underlying = defaultdict(list)
            for position in positions:
                underlying = position.underlying_symbol or position.symbol
                by_underlying[underlying].append(position)
            
            # Look for cross-margining opportunities
            for underlying, underlying_positions in by_underlying.items():
                if len(underlying_positions) > 1:
                    long_positions = [p for p in underlying_positions if p.quantity > 0]
                    short_positions = [p for p in underlying_positions if p.quantity < 0]
                    
                    if long_positions and short_positions:
                        total_long_value = sum(abs(p.market_value) for p in long_positions)
                        total_short_value = sum(abs(p.market_value) for p in short_positions)
                        
                        potential_offset = min(total_long_value, total_short_value)
                        margin_reduction = potential_offset * 0.3  # Estimated 30% reduction
                        
                        suggestions.append({
                            "type": "cross_margining",
                            "underlying": underlying,
                            "strategy": f"Cross-margin long and short positions in {underlying}",
                            "estimated_margin_reduction": margin_reduction,
                            "positions_involved": len(underlying_positions)
                        })
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Failed to suggest cross-margining: {e}")
            return []


class UnifiedMarginSystem:
    """Main unified margin system that orchestrates all margin calculations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize calculators
        self.equity_calculator = EquityMarginCalculator()
        self.options_calculator = OptionsMarginCalculator()
        self.span_calculator = SPANMarginCalculator()
        self.portfolio_calculator = PortfolioMarginCalculator()
        self.optimizer = MarginOptimizer()
        
        # System configuration
        self.margin_buffer = 0.05  # 5% buffer above required margin
        self.max_leverage = 4.0  # Maximum allowed leverage
        
    async def calculate_comprehensive_margin(self, 
                                           positions: List[Position],
                                           available_capital: float = None) -> Dict[str, Any]:
        """Calculate comprehensive margin requirements and optimization suggestions"""
        try:
            if not positions:
                return {
                    "portfolio_margin": PortfolioMarginResult(0, 0, 1, 0),
                    "individual_margins": {},
                    "optimization": {},
                    "compliance": {"status": "compliant", "issues": []},
                    "summary": {"total_positions": 0, "total_margin": 0}
                }
            
            # Calculate portfolio margin
            portfolio_result = await self.portfolio_calculator.calculate_portfolio_margin(positions)
            
            # Calculate individual margins for detailed breakdown
            individual_margins = {}
            
            for position in positions:
                if position.asset_class == AssetClass.EQUITY:
                    margin_req = await self.equity_calculator.calculate_margin(position)
                elif position.asset_class == AssetClass.OPTION:
                    margin_req = await self.options_calculator.calculate_margin(position)
                else:
                    # Default margin calculation
                    margin_req = MarginRequirement(
                        position_id=position.symbol,
                        margin_type=MarginType.INITIAL,
                        required_margin=abs(position.market_value) * 0.2,
                        excess_margin=0.0,
                        margin_utilization=0.0,
                        calculation_method="Default Margin"
                    )
                
                individual_margins[position.symbol] = margin_req
            
            # Optimization analysis
            optimization_result = {}
            if available_capital:
                optimization_result = await self.optimizer.optimize_margin_usage(
                    positions, available_capital
                )
            
            # Compliance check
            compliance_result = await self._check_margin_compliance(
                portfolio_result, available_capital
            )
            
            # Summary
            summary = {
                "total_positions": len(positions),
                "total_margin": portfolio_result.total_margin_required,
                "total_market_value": sum(abs(p.market_value) for p in positions),
                "portfolio_leverage": portfolio_result.portfolio_leverage,
                "margin_utilization": portfolio_result.margin_utilization,
                "diversification_benefit": portfolio_result.diversification_benefit,
                "asset_class_breakdown": portfolio_result.margin_by_asset_class
            }
            
            return {
                "portfolio_margin": portfolio_result,
                "individual_margins": individual_margins,
                "optimization": optimization_result,
                "compliance": compliance_result,
                "summary": summary,
                "calculation_timestamp": datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate comprehensive margin: {e}")
            return {"error": str(e), "calculation_timestamp": datetime.now()}
    
    async def _check_margin_compliance(self, 
                                     portfolio_result: PortfolioMarginResult,
                                     available_capital: float = None) -> Dict[str, Any]:
        """Check margin compliance and identify issues"""
        try:
            compliance_result = {
                "status": "compliant",
                "issues": [],
                "warnings": [],
                "recommendations": []
            }
            
            # Check leverage limits
            if portfolio_result.portfolio_leverage > self.max_leverage:
                compliance_result["status"] = "non_compliant"
                compliance_result["issues"].append(
                    f"Portfolio leverage ({portfolio_result.portfolio_leverage:.2f}) exceeds maximum allowed ({self.max_leverage})"
                )
            
            # Check margin buffer
            if available_capital:
                required_with_buffer = portfolio_result.total_margin_required * (1 + self.margin_buffer)
                if available_capital < required_with_buffer:
                    compliance_result["warnings"].append(
                        f"Available capital below recommended buffer. Need ${required_with_buffer:,.2f}, have ${available_capital:,.2f}"
                    )
            
            # Check concentration risk
            if portfolio_result.concentration_risk > 0.8:
                compliance_result["warnings"].append(
                    "High concentration risk detected - consider diversification"
                )
            
            # Recommendations based on analysis
            if portfolio_result.optimization_opportunities:
                compliance_result["recommendations"].extend(portfolio_result.optimization_opportunities)
            
            return compliance_result
            
        except Exception as e:
            self.logger.error(f"Failed to check margin compliance: {e}")
            return {"status": "error", "error": str(e)}
    
    async def simulate_margin_impact(self, 
                                   current_positions: List[Position],
                                   proposed_trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Simulate the margin impact of proposed trades"""
        try:
            # Calculate current margin
            current_margin = await self.portfolio_calculator.calculate_portfolio_margin(current_positions)
            
            # Create simulated positions after trades
            simulated_positions = current_positions.copy()
            
            for trade in proposed_trades:
                symbol = trade["symbol"]
                quantity_change = trade["quantity"]
                price = trade.get("price", 0)
                
                # Find existing position or create new one
                existing_pos = next((p for p in simulated_positions if p.symbol == symbol), None)
                
                if existing_pos:
                    # Modify existing position
                    existing_pos.quantity += quantity_change
                    existing_pos.market_value = existing_pos.quantity * existing_pos.current_price
                else:
                    # Create new position
                    new_position = Position(
                        symbol=symbol,
                        asset_class=trade.get("asset_class", AssetClass.EQUITY),
                        quantity=quantity_change,
                        current_price=price,
                        market_value=quantity_change * price
                    )
                    simulated_positions.append(new_position)
            
            # Remove positions with zero quantity
            simulated_positions = [p for p in simulated_positions if p.quantity != 0]
            
            # Calculate new margin
            new_margin = await self.portfolio_calculator.calculate_portfolio_margin(simulated_positions)
            
            # Calculate impact
            margin_impact = {
                "current_margin": current_margin.total_margin_required,
                "new_margin": new_margin.total_margin_required,
                "margin_change": new_margin.total_margin_required - current_margin.total_margin_required,
                "leverage_change": new_margin.portfolio_leverage - current_margin.portfolio_leverage,
                "trades_analyzed": len(proposed_trades),
                "recommendation": "approve" if new_margin.portfolio_leverage <= self.max_leverage else "reject"
            }
            
            return margin_impact
            
        except Exception as e:
            self.logger.error(f"Failed to simulate margin impact: {e}")
            return {"error": str(e)}


# Example usage and testing
async def example_usage():
    """Example usage of the Unified Margin System"""
    
    # Initialize the margin system
    margin_system = UnifiedMarginSystem()
    
    # Create sample positions
    positions = [
        Position(
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            quantity=100,
            current_price=150.0,
            market_value=15000.0,
            volatility=0.25,
            beta=1.2
        ),
        Position(
            symbol="AAPL240315C00160000",
            asset_class=AssetClass.OPTION,
            quantity=-2,  # Short 2 call options
            current_price=5.0,
            market_value=-1000.0,
            underlying_symbol="AAPL",
            strike_price=160.0,
            option_type="call",
            delta=0.6,
            gamma=0.05,
            theta=-0.02,
            vega=0.15,
            volatility=0.25
        ),
        Position(
            symbol="ES_202406",
            asset_class=AssetClass.FUTURE,
            quantity=1,
            current_price=4500.0,
            market_value=225000.0,  # 1 contract * $50 multiplier * 4500
            volatility=0.20
        )
    ]
    
    # Calculate comprehensive margin
    available_capital = 100000.0
    
    print("Calculating comprehensive margin requirements...")
    result = await margin_system.calculate_comprehensive_margin(positions, available_capital)
    
    # Display results
    print(f"\n=== Unified Margin System Results ===")
    print(f"Calculation Time: {result['calculation_timestamp']}")
    
    # Portfolio summary
    summary = result["summary"]
    print(f"\n=== Portfolio Summary ===")
    print(f"Total Positions: {summary['total_positions']}")
    print(f"Total Market Value: ${summary['total_market_value']:,.2f}")
    print(f"Total Margin Required: ${summary['total_margin']:,.2f}")
    print(f"Portfolio Leverage: {summary['portfolio_leverage']:.2f}x")
    print(f"Margin Utilization: {summary['margin_utilization']:.1%}")
    
    # Asset class breakdown
    if summary.get("asset_class_breakdown"):
        print(f"\n=== Margin by Asset Class ===")
        for asset_class, margin in summary["asset_class_breakdown"].items():
            print(f"{asset_class.title()}: ${margin:,.2f}")
    
    # Individual margins
    print(f"\n=== Individual Position Margins ===")
    for symbol, margin_req in result["individual_margins"].items():
        print(f"{symbol}: ${margin_req.required_margin:,.2f} ({margin_req.calculation_method})")
    
    # Optimization suggestions
    if result["optimization"] and result["optimization"].get("optimization_suggestions"):
        print(f"\n=== Optimization Suggestions ===")
        for suggestion in result["optimization"]["optimization_suggestions"][:3]:
            print(f"- {suggestion.get('strategy', suggestion.get('type', 'Unknown'))}")
    
    # Compliance status
    compliance = result["compliance"]
    print(f"\n=== Compliance Status ===")
    print(f"Status: {compliance['status'].upper()}")
    
    if compliance.get("issues"):
        print("Issues:")
        for issue in compliance["issues"]:
            print(f"  - {issue}")
    
    if compliance.get("warnings"):
        print("Warnings:")
        for warning in compliance["warnings"]:
            print(f"  - {warning}")
    
    # Simulate a trade
    print(f"\n=== Trade Impact Simulation ===")
    proposed_trades = [
        {"symbol": "AAPL", "quantity": 50, "price": 150.0, "asset_class": AssetClass.EQUITY}
    ]
    
    impact = await margin_system.simulate_margin_impact(positions, proposed_trades)
    print(f"Current Margin: ${impact['current_margin']:,.2f}")
    print(f"New Margin: ${impact['new_margin']:,.2f}")
    print(f"Margin Change: ${impact['margin_change']:,.2f}")
    print(f"Recommendation: {impact['recommendation'].upper()}")


if __name__ == "__main__":
    asyncio.run(example_usage())