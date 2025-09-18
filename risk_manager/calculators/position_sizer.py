"""Position Sizing Calculator

Implements various position sizing methods including fixed amount/percentage,
Kelly Criterion, volatility-adjusted, risk parity, ATR-based, and VaR-based sizing.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import asyncio
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Union, Any
import logging

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from ..models.risk_models import (
    PositionSizingMethod, PositionSizingResult, RiskLimits
)

# Configure logging
logger = logging.getLogger(__name__)

class PositionSizer:
    """Position sizing calculator with multiple methodologies"""
    
    def __init__(self, risk_limits: Optional[RiskLimits] = None):
        """
        Initialize position sizer
        
        Args:
            risk_limits: Risk limits configuration
        """
        self.risk_limits = risk_limits or RiskLimits()
        
    async def calculate_position_size(
        self,
        method: PositionSizingMethod,
        account_balance: float,
        current_price: float,
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
        volatility: Optional[float] = None,
        expected_return: Optional[float] = None,
        win_rate: Optional[float] = None,
        avg_win: Optional[float] = None,
        avg_loss: Optional[float] = None,
        correlation_matrix: Optional[np.ndarray] = None,
        current_positions: Optional[Dict[str, float]] = None,
        **kwargs
    ) -> PositionSizingResult:
        """
        Calculate position size using specified method
        
        Args:
            method: Position sizing method
            account_balance: Current account balance
            current_price: Current asset price
            stop_loss_price: Stop loss price (if applicable)
            take_profit_price: Take profit price (if applicable)
            volatility: Asset volatility (annualized)
            expected_return: Expected return (annualized)
            win_rate: Historical win rate (0-1)
            avg_win: Average winning trade amount
            avg_loss: Average losing trade amount
            correlation_matrix: Asset correlation matrix
            current_positions: Current portfolio positions
            **kwargs: Additional method-specific parameters
            
        Returns:
            PositionSizingResult with recommended position size
        """
        
        try:
            # Validate inputs
            self._validate_inputs(account_balance, current_price)
            
            # Calculate position size based on method
            if method == PositionSizingMethod.FIXED_AMOUNT:
                result = await self._calculate_fixed_amount(
                    account_balance, current_price, **kwargs
                )
            elif method == PositionSizingMethod.FIXED_PERCENTAGE:
                result = await self._calculate_fixed_percentage(
                    account_balance, current_price, **kwargs
                )
            elif method == PositionSizingMethod.KELLY_CRITERION:
                result = await self._calculate_kelly_criterion(
                    account_balance, current_price, win_rate, avg_win, avg_loss, **kwargs
                )
            elif method == PositionSizingMethod.VOLATILITY_ADJUSTED:
                result = await self._calculate_volatility_adjusted(
                    account_balance, current_price, volatility, **kwargs
                )
            elif method == PositionSizingMethod.RISK_PARITY:
                result = await self._calculate_risk_parity(
                    account_balance, current_price, volatility, correlation_matrix, **kwargs
                )
            elif method == PositionSizingMethod.ATR_BASED:
                result = await self._calculate_atr_based(
                    account_balance, current_price, stop_loss_price, **kwargs
                )
            elif method == PositionSizingMethod.VAR_BASED:
                result = await self._calculate_var_based(
                    account_balance, current_price, volatility, **kwargs
                )
            else:
                raise ValueError(f"Unsupported position sizing method: {method}")
            
            # Apply risk limits
            result = self._apply_risk_limits(result, account_balance, current_price)
            
            # Set additional fields
            result.stop_loss_price = stop_loss_price
            result.take_profit_price = take_profit_price
            
            return result
            
        except Exception as e:
            logger.error(f"Position sizing calculation failed: {str(e)}")
            # Return minimal position on error
            return PositionSizingResult(
                method=method,
                recommended_quantity=0.0,
                recommended_value=0.0,
                risk_amount=0.0,
                risk_percentage=0.0,
                confidence_score=0.0,
                metadata={"error": str(e)}
            )
    
    async def _calculate_fixed_amount(
        self,
        account_balance: float,
        current_price: float,
        fixed_amount: Optional[float] = None,
        **kwargs
    ) -> PositionSizingResult:
        """Calculate fixed amount position sizing"""
        
        fixed_amount = fixed_amount or self.risk_limits.max_position_value
        
        # Calculate quantity based on fixed amount
        quantity = fixed_amount / current_price
        actual_value = quantity * current_price
        
        # Risk is the full position value (worst case)
        risk_amount = actual_value
        risk_percentage = (risk_amount / account_balance) * 100
        
        return PositionSizingResult(
            method=PositionSizingMethod.FIXED_AMOUNT,
            recommended_quantity=quantity,
            recommended_value=actual_value,
            risk_amount=risk_amount,
            risk_percentage=risk_percentage,
            confidence_score=0.8,  # High confidence for simple method
            metadata={
                "fixed_amount": fixed_amount,
                "price_per_share": current_price
            }
        )
    
    async def _calculate_fixed_percentage(
        self,
        account_balance: float,
        current_price: float,
        percentage: Optional[float] = None,
        **kwargs
    ) -> PositionSizingResult:
        """Calculate fixed percentage position sizing"""
        
        percentage = percentage or self.risk_limits.max_position_percentage
        
        # Calculate position value as percentage of account
        position_value = account_balance * (percentage / 100)
        quantity = position_value / current_price
        
        # Risk is the full position value
        risk_amount = position_value
        risk_percentage = percentage
        
        return PositionSizingResult(
            method=PositionSizingMethod.FIXED_PERCENTAGE,
            recommended_quantity=quantity,
            recommended_value=position_value,
            risk_amount=risk_amount,
            risk_percentage=risk_percentage,
            confidence_score=0.8,
            metadata={
                "percentage": percentage,
                "account_balance": account_balance
            }
        )
    
    async def _calculate_kelly_criterion(
        self,
        account_balance: float,
        current_price: float,
        win_rate: Optional[float],
        avg_win: Optional[float],
        avg_loss: Optional[float],
        **kwargs
    ) -> PositionSizingResult:
        """Calculate Kelly Criterion position sizing"""
        
        if not all([win_rate, avg_win, avg_loss]):
            logger.warning("Insufficient data for Kelly Criterion, using conservative sizing")
            # Fall back to conservative fixed percentage
            return await self._calculate_fixed_percentage(
                account_balance, current_price, 2.0  # 2% conservative
            )
        
        # Kelly formula: f = (bp - q) / b
        # where b = avg_win/avg_loss, p = win_rate, q = 1 - win_rate
        b = abs(avg_win / avg_loss) if avg_loss != 0 else 1.0
        p = win_rate
        q = 1 - win_rate
        
        kelly_fraction = (b * p - q) / b
        
        # Apply Kelly fraction limits (typically 0-25%)
        kelly_fraction = max(0, min(kelly_fraction, 0.25))
        
        # Further reduce by safety factor
        safety_factor = kwargs.get('kelly_safety_factor', 0.5)
        adjusted_kelly = kelly_fraction * safety_factor
        
        # Calculate position size
        position_value = account_balance * adjusted_kelly
        quantity = position_value / current_price
        
        # Risk calculation (using average loss)
        risk_amount = position_value * (abs(avg_loss) / current_price)
        risk_percentage = (risk_amount / account_balance) * 100
        
        # Confidence based on sample size and edge
        edge = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
        confidence_score = min(0.9, max(0.1, kelly_fraction * 2))  # Scale to 0.1-0.9
        
        return PositionSizingResult(
            method=PositionSizingMethod.KELLY_CRITERION,
            recommended_quantity=quantity,
            recommended_value=position_value,
            risk_amount=risk_amount,
            risk_percentage=risk_percentage,
            confidence_score=confidence_score,
            metadata={
                "kelly_fraction": kelly_fraction,
                "adjusted_kelly": adjusted_kelly,
                "win_rate": win_rate,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "edge": edge,
                "safety_factor": safety_factor
            }
        )
    
    async def _calculate_volatility_adjusted(
        self,
        account_balance: float,
        current_price: float,
        volatility: Optional[float],
        **kwargs
    ) -> PositionSizingResult:
        """Calculate volatility-adjusted position sizing"""
        
        if volatility is None:
            logger.warning("No volatility data, using fixed percentage")
            return await self._calculate_fixed_percentage(
                account_balance, current_price, 3.0
            )
        
        # Target volatility (default 2% daily)
        target_volatility = kwargs.get('target_volatility', 0.02)
        
        # Convert annual volatility to daily if needed
        if volatility > 1.0:  # Assume it's in percentage
            volatility = volatility / 100
        
        # Assume annual volatility, convert to daily
        daily_volatility = volatility / math.sqrt(252)
        
        # Calculate position size to achieve target volatility
        volatility_scalar = target_volatility / daily_volatility if daily_volatility > 0 else 0.1
        
        # Limit the scalar to reasonable bounds
        volatility_scalar = max(0.01, min(volatility_scalar, 0.2))  # 1% to 20%
        
        # Calculate position
        position_value = account_balance * volatility_scalar
        quantity = position_value / current_price
        
        # Risk is based on daily volatility
        risk_amount = position_value * daily_volatility * 2  # 2 standard deviations
        risk_percentage = (risk_amount / account_balance) * 100
        
        # Confidence based on volatility stability
        confidence_score = max(0.3, min(0.9, 1 - daily_volatility * 10))
        
        return PositionSizingResult(
            method=PositionSizingMethod.VOLATILITY_ADJUSTED,
            recommended_quantity=quantity,
            recommended_value=position_value,
            risk_amount=risk_amount,
            risk_percentage=risk_percentage,
            confidence_score=confidence_score,
            metadata={
                "volatility": volatility,
                "daily_volatility": daily_volatility,
                "target_volatility": target_volatility,
                "volatility_scalar": volatility_scalar
            }
        )
    
    async def _calculate_risk_parity(
        self,
        account_balance: float,
        current_price: float,
        volatility: Optional[float],
        correlation_matrix: Optional[np.ndarray],
        **kwargs
    ) -> PositionSizingResult:
        """Calculate risk parity position sizing"""
        
        if volatility is None:
            logger.warning("No volatility data for risk parity, using equal weight")
            return await self._calculate_fixed_percentage(
                account_balance, current_price, 5.0
            )
        
        # Target risk contribution (default equal risk)
        target_risk_contribution = kwargs.get('target_risk_contribution', 1.0)
        
        # Convert volatility to daily if needed
        if volatility > 1.0:
            volatility = volatility / 100
        daily_volatility = volatility / math.sqrt(252)
        
        # Risk parity weight is inversely proportional to volatility
        risk_parity_weight = target_risk_contribution / daily_volatility
        
        # Normalize to reasonable portfolio percentage (max 10%)
        max_weight = 0.10
        normalized_weight = min(risk_parity_weight * 0.01, max_weight)
        
        # Calculate position
        position_value = account_balance * normalized_weight
        quantity = position_value / current_price
        
        # Risk calculation
        risk_amount = position_value * daily_volatility * 2
        risk_percentage = (risk_amount / account_balance) * 100
        
        confidence_score = 0.7  # Moderate confidence for risk parity
        
        return PositionSizingResult(
            method=PositionSizingMethod.RISK_PARITY,
            recommended_quantity=quantity,
            recommended_value=position_value,
            risk_amount=risk_amount,
            risk_percentage=risk_percentage,
            confidence_score=confidence_score,
            metadata={
                "volatility": volatility,
                "daily_volatility": daily_volatility,
                "risk_parity_weight": risk_parity_weight,
                "normalized_weight": normalized_weight,
                "target_risk_contribution": target_risk_contribution
            }
        )
    
    async def _calculate_atr_based(
        self,
        account_balance: float,
        current_price: float,
        stop_loss_price: Optional[float],
        atr_value: Optional[float] = None,
        atr_multiplier: float = 2.0,
        **kwargs
    ) -> PositionSizingResult:
        """Calculate ATR-based position sizing"""
        
        # Risk per trade (default 1% of account)
        risk_per_trade = kwargs.get('risk_per_trade', 0.01) * account_balance
        
        # Determine stop distance
        if stop_loss_price is not None:
            stop_distance = abs(current_price - stop_loss_price)
        elif atr_value is not None:
            stop_distance = atr_value * atr_multiplier
        else:
            # Default to 2% of current price
            stop_distance = current_price * 0.02
            logger.warning("No ATR or stop loss provided, using 2% default")
        
        # Calculate position size based on risk
        if stop_distance > 0:
            quantity = risk_per_trade / stop_distance
        else:
            quantity = 0
        
        position_value = quantity * current_price
        
        # Risk is the predefined risk per trade
        risk_amount = risk_per_trade
        risk_percentage = (risk_amount / account_balance) * 100
        
        # Confidence based on stop distance reasonableness
        stop_percentage = (stop_distance / current_price) * 100
        confidence_score = max(0.2, min(0.9, 1 - (stop_percentage - 2) / 10))
        
        return PositionSizingResult(
            method=PositionSizingMethod.ATR_BASED,
            recommended_quantity=quantity,
            recommended_value=position_value,
            risk_amount=risk_amount,
            risk_percentage=risk_percentage,
            confidence_score=confidence_score,
            stop_loss_price=current_price - stop_distance,  # Assuming long position
            metadata={
                "atr_value": atr_value,
                "atr_multiplier": atr_multiplier,
                "stop_distance": stop_distance,
                "risk_per_trade": risk_per_trade,
                "stop_percentage": stop_percentage
            }
        )
    
    async def _calculate_var_based(
        self,
        account_balance: float,
        current_price: float,
        volatility: Optional[float],
        confidence_level: float = 0.95,
        **kwargs
    ) -> PositionSizingResult:
        """Calculate VaR-based position sizing"""
        
        if volatility is None:
            logger.warning("No volatility data for VaR sizing, using conservative approach")
            return await self._calculate_fixed_percentage(
                account_balance, current_price, 2.0
            )
        
        # Target VaR as percentage of account (default 1%)
        target_var_percentage = kwargs.get('target_var_percentage', 0.01)
        target_var_amount = account_balance * target_var_percentage
        
        # Convert volatility to daily
        if volatility > 1.0:
            volatility = volatility / 100
        daily_volatility = volatility / math.sqrt(252)
        
        # Calculate VaR multiplier for confidence level
        from scipy import stats
        alpha = 1 - confidence_level
        z_score = abs(stats.norm.ppf(alpha))
        
        # Position size to achieve target VaR
        var_per_dollar = daily_volatility * z_score
        if var_per_dollar > 0:
            position_value = target_var_amount / var_per_dollar
        else:
            position_value = account_balance * 0.01  # 1% fallback
        
        quantity = position_value / current_price
        
        # Risk is the target VaR
        risk_amount = target_var_amount
        risk_percentage = target_var_percentage * 100
        
        confidence_score = 0.8  # High confidence for VaR-based sizing
        
        return PositionSizingResult(
            method=PositionSizingMethod.VAR_BASED,
            recommended_quantity=quantity,
            recommended_value=position_value,
            risk_amount=risk_amount,
            risk_percentage=risk_percentage,
            confidence_score=confidence_score,
            metadata={
                "volatility": volatility,
                "daily_volatility": daily_volatility,
                "confidence_level": confidence_level,
                "z_score": z_score,
                "target_var_percentage": target_var_percentage,
                "var_per_dollar": var_per_dollar
            }
        )
    
    def _apply_risk_limits(
        self,
        result: PositionSizingResult,
        account_balance: float,
        current_price: float
    ) -> PositionSizingResult:
        """Apply risk limits to position sizing result"""
        
        original_quantity = result.recommended_quantity
        
        # Apply maximum position size limit
        max_quantity_by_size = self.risk_limits.max_position_size
        if result.recommended_quantity > max_quantity_by_size:
            result.recommended_quantity = max_quantity_by_size
        
        # Apply maximum position value limit
        max_quantity_by_value = self.risk_limits.max_position_value / current_price
        if result.recommended_quantity > max_quantity_by_value:
            result.recommended_quantity = max_quantity_by_value
        
        # Apply maximum position percentage limit
        max_position_value = account_balance * (self.risk_limits.max_position_percentage / 100)
        max_quantity_by_percentage = max_position_value / current_price
        if result.recommended_quantity > max_quantity_by_percentage:
            result.recommended_quantity = max_quantity_by_percentage
        
        # Recalculate values if quantity was adjusted
        if result.recommended_quantity != original_quantity:
            result.recommended_value = result.recommended_quantity * current_price
            result.risk_percentage = (result.recommended_value / account_balance) * 100
            
            # Reduce confidence score due to limit application
            result.confidence_score *= 0.8
            
            # Add metadata about limits applied
            result.metadata["limits_applied"] = True
            result.metadata["original_quantity"] = original_quantity
            result.metadata["quantity_reduction"] = original_quantity - result.recommended_quantity
        
        return result
    
    def _validate_inputs(
        self,
        account_balance: float,
        current_price: float
    ) -> None:
        """Validate input parameters"""
        
        if account_balance <= 0:
            raise ValueError("Account balance must be positive")
        
        if current_price <= 0:
            raise ValueError("Current price must be positive")
    
    async def calculate_optimal_position_size(
        self,
        account_balance: float,
        current_price: float,
        methods: List[PositionSizingMethod],
        **kwargs
    ) -> PositionSizingResult:
        """Calculate position size using multiple methods and return optimal result"""
        
        results = []
        
        # Calculate using all specified methods
        for method in methods:
            try:
                result = await self.calculate_position_size(
                    method, account_balance, current_price, **kwargs
                )
                results.append(result)
            except Exception as e:
                logger.warning(f"Failed to calculate {method}: {str(e)}")
        
        if not results:
            # Return conservative fallback
            return await self.calculate_position_size(
                PositionSizingMethod.FIXED_PERCENTAGE,
                account_balance, current_price, percentage=1.0
            )
        
        # Weight results by confidence score
        total_weighted_quantity = 0
        total_weight = 0
        
        for result in results:
            weight = result.confidence_score
            total_weighted_quantity += result.recommended_quantity * weight
            total_weight += weight
        
        if total_weight > 0:
            optimal_quantity = total_weighted_quantity / total_weight
        else:
            optimal_quantity = np.mean([r.recommended_quantity for r in results])
        
        # Create combined result
        optimal_value = optimal_quantity * current_price
        avg_risk_percentage = np.mean([r.risk_percentage for r in results])
        avg_confidence = np.mean([r.confidence_score for r in results])
        
        return PositionSizingResult(
            method=PositionSizingMethod.FIXED_PERCENTAGE,  # Placeholder
            recommended_quantity=optimal_quantity,
            recommended_value=optimal_value,
            risk_amount=optimal_value * (avg_risk_percentage / 100),
            risk_percentage=avg_risk_percentage,
            confidence_score=avg_confidence,
            metadata={
                "methods_used": [r.method for r in results],
                "individual_results": [{
                    "method": r.method,
                    "quantity": r.recommended_quantity,
                    "confidence": r.confidence_score
                } for r in results],
                "combination_method": "weighted_average"
            }
        )