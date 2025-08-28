"""
Risk Manager Agent for Risk Assessment and Position Sizing

This agent specializes in risk management, portfolio optimization, and position
sizing calculations to ensure safe trading operations.
"""

import asyncio
import logging
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ..utils.agent_utils import AgentBase, AgentMessage, AgentResponse
from shared.utils import format_percentage, format_currency


logger = logging.getLogger(__name__)


class RiskManagerAgent(AgentBase):
    """
    Risk Manager Agent for comprehensive risk assessment
    
    Capabilities:
    - Portfolio risk analysis
    - Position sizing calculations
    - Stop-loss and take-profit levels
    - Correlation analysis
    - Value-at-Risk (VaR) calculations
    - Stress testing scenarios
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Risk Manager Agent
        
        Args:
            config: Agent configuration
        """
        super().__init__(name="risk_manager", config=config)
        
        # Risk parameters
        self.max_portfolio_risk = config.get("max_portfolio_risk", 0.02)  # 2% per trade
        self.max_correlation_limit = config.get("max_correlation_limit", 0.7)
        self.var_confidence_level = config.get("var_confidence_level", 0.95)
        
        # Risk cache
        self._risk_cache = {}
        
        logger.info("Risk Manager Agent initialized")
    
    async def assess_risk(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive risk assessment
        
        Args:
            request: Risk assessment request parameters
            
        Returns:
            Risk assessment result
        """
        symbol = request.get("symbol")
        analysis_result = request.get("analysis_result", {})
        portfolio_context = request.get("portfolio_context", {})
        risk_tolerance = request.get("risk_tolerance", "medium")
        
        logger.info(f"Starting risk assessment for {symbol}")
        
        try:
            risk_assessment = {
                "symbol": symbol,
                "timestamp": datetime.utcnow().isoformat(),
                "risk_tolerance": risk_tolerance
            }
            
            # Portfolio risk analysis
            portfolio_risk = await self._analyze_portfolio_risk(symbol, portfolio_context)
            risk_assessment["portfolio_risk"] = portfolio_risk
            
            # Position sizing
            position_sizing = await self._calculate_position_sizing(
                symbol, analysis_result, portfolio_context, risk_tolerance
            )
            risk_assessment["position_sizing"] = position_sizing
            
            # Risk/reward analysis
            risk_reward = await self._analyze_risk_reward(symbol, analysis_result)
            risk_assessment["risk_reward"] = risk_reward
            
            # Correlation analysis
            correlation_risk = await self._analyze_correlation_risk(symbol, portfolio_context)
            risk_assessment["correlation_risk"] = correlation_risk
            
            # VaR calculation
            var_analysis = await self._calculate_var(symbol, position_sizing)
            risk_assessment["var_analysis"] = var_analysis
            
            # Final risk decision
            risk_decision = self._make_risk_decision(risk_assessment)
            risk_assessment["approved"] = risk_decision["approved"]
            risk_assessment["risk_score"] = risk_decision["risk_score"]
            risk_assessment["position_size"] = risk_decision["position_size"]
            risk_assessment["stop_loss"] = risk_decision["stop_loss"]
            risk_assessment["take_profit"] = risk_decision["take_profit"]
            risk_assessment["rationale"] = risk_decision["rationale"]
            
            # Cache result
            self._risk_cache[symbol] = risk_assessment
            
            logger.info(f"Risk assessment completed for {symbol}: {'APPROVED' if risk_decision['approved'] else 'REJECTED'}")
            
            return risk_assessment
        
        except Exception as e:
            logger.error(f"Risk assessment failed for {symbol}: {e}")
            raise
    
    async def _analyze_portfolio_risk(
        self,
        symbol: str,
        portfolio_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze current portfolio risk exposure
        
        Args:
            symbol: Trading symbol
            portfolio_context: Current portfolio information
            
        Returns:
            Portfolio risk analysis
        """
        logger.info(f"Analyzing portfolio risk for {symbol}")
        
        try:
            # Get current portfolio metrics
            total_value = portfolio_context.get("total_value", 100000)
            current_positions = portfolio_context.get("positions", [])
            cash_balance = portfolio_context.get("cash_balance", 20000)
            
            # Calculate current exposure
            total_exposure = sum(pos.get("market_value", 0) for pos in current_positions)
            exposure_ratio = total_exposure / total_value if total_value > 0 else 0
            
            # Calculate sector/asset concentration
            sector_exposure = self._calculate_sector_exposure(current_positions)
            
            # Risk metrics
            portfolio_beta = self._calculate_portfolio_beta(current_positions)
            portfolio_volatility = self._calculate_portfolio_volatility(current_positions)
            
            return {
                "total_value": total_value,
                "total_exposure": total_exposure,
                "exposure_ratio": exposure_ratio,
                "cash_balance": cash_balance,
                "cash_ratio": cash_balance / total_value,
                "sector_exposure": sector_exposure,
                "portfolio_beta": portfolio_beta,
                "portfolio_volatility": portfolio_volatility,
                "diversification_score": self._calculate_diversification_score(current_positions)
            }
        
        except Exception as e:
            logger.error(f"Portfolio risk analysis failed for {symbol}: {e}")
            return {"error": str(e)}
    
    async def _calculate_position_sizing(
        self,
        symbol: str,
        analysis_result: Dict[str, Any],
        portfolio_context: Dict[str, Any],
        risk_tolerance: str
    ) -> Dict[str, Any]:
        """
        Calculate optimal position sizing
        
        Args:
            symbol: Trading symbol
            analysis_result: Market analysis result
            portfolio_context: Portfolio context
            risk_tolerance: Risk tolerance level
            
        Returns:
            Position sizing calculation
        """
        logger.info(f"Calculating position sizing for {symbol}")
        
        try:
            # Get key parameters
            total_value = portfolio_context.get("total_value", 100000)
            current_price = 150.0  # Would get from market data
            confidence = analysis_result.get("confidence", 0.5)
            
            # Risk tolerance multipliers
            risk_multipliers = {
                "conservative": 0.5,
                "moderate": 1.0,
                "aggressive": 1.5
            }
            
            base_risk_multiplier = risk_multipliers.get(risk_tolerance, 1.0)
            
            # Calculate position size using Kelly Criterion and fixed percentage
            kelly_fraction = self._calculate_kelly_fraction(analysis_result)
            fixed_percentage = self.max_portfolio_risk * base_risk_multiplier
            
            # Use conservative approach (smaller of Kelly and fixed percentage)
            risk_fraction = min(kelly_fraction, fixed_percentage)
            
            # Adjust for confidence
            adjusted_risk_fraction = risk_fraction * confidence
            
            # Calculate position value and shares
            position_value = total_value * adjusted_risk_fraction
            estimated_shares = position_value / current_price if current_price > 0 else 0
            
            # Calculate stop loss and take profit levels
            stop_loss_percent = self._calculate_stop_loss_percent(analysis_result, risk_tolerance)
            take_profit_percent = self._calculate_take_profit_percent(analysis_result, risk_tolerance)
            
            return {
                "method": "kelly_criterion_adjusted",
                "risk_fraction": risk_fraction,
                "adjusted_risk_fraction": adjusted_risk_fraction,
                "position_value": position_value,
                "estimated_shares": estimated_shares,
                "current_price": current_price,
                "stop_loss_percent": stop_loss_percent,
                "take_profit_percent": take_profit_percent,
                "max_loss": position_value * stop_loss_percent,
                "expected_profit": position_value * take_profit_percent
            }
        
        except Exception as e:
            logger.error(f"Position sizing calculation failed for {symbol}: {e}")
            return {"error": str(e)}
    
    async def _analyze_risk_reward(
        self,
        symbol: str,
        analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze risk/reward ratio
        
        Args:
            symbol: Trading symbol
            analysis_result: Market analysis result
            
        Returns:
            Risk/reward analysis
        """
        logger.info(f"Analyzing risk/reward for {symbol}")
        
        try:
            current_price = 150.0  # Would get from market data
            target_price = analysis_result.get("target_price", current_price * 1.05)
            
            # Calculate potential reward
            potential_reward = (target_price - current_price) / current_price
            
            # Estimate potential risk based on volatility and technical levels
            technical_analysis = analysis_result.get("technical", {})
            support_levels = technical_analysis.get("support_levels", [current_price * 0.95])
            
            nearest_support = max([level for level in support_levels if level < current_price], default=current_price * 0.95)
            potential_risk = (current_price - nearest_support) / current_price
            
            # Calculate risk/reward ratio
            risk_reward_ratio = potential_reward / potential_risk if potential_risk > 0 else 0
            
            return {
                "current_price": current_price,
                "target_price": target_price,
                "nearest_support": nearest_support,
                "potential_reward": potential_reward,
                "potential_risk": potential_risk,
                "risk_reward_ratio": risk_reward_ratio,
                "assessment": "favorable" if risk_reward_ratio >= 2.0 else "unfavorable"
            }
        
        except Exception as e:
            logger.error(f"Risk/reward analysis failed for {symbol}: {e}")
            return {"error": str(e)}
    
    async def _analyze_correlation_risk(
        self,
        symbol: str,
        portfolio_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze correlation risk with existing positions
        
        Args:
            symbol: Trading symbol
            portfolio_context: Portfolio context
            
        Returns:
            Correlation risk analysis
        """
        logger.info(f"Analyzing correlation risk for {symbol}")
        
        try:
            current_positions = portfolio_context.get("positions", [])
            
            if not current_positions:
                return {
                    "correlation_risk": "low",
                    "max_correlation": 0.0,
                    "correlated_positions": [],
                    "diversification_benefit": True
                }
            
            # Calculate correlations with existing positions
            correlations = []
            for position in current_positions:
                position_symbol = position.get("symbol")
                # Mock correlation calculation - would use actual correlation data
                correlation = self._calculate_correlation(symbol, position_symbol)
                correlations.append({
                    "symbol": position_symbol,
                    "correlation": correlation,
                    "weight": position.get("weight", 0)
                })
            
            # Find maximum correlation
            max_correlation = max([c["correlation"] for c in correlations]) if correlations else 0.0
            
            # Assess correlation risk
            if max_correlation > self.max_correlation_limit:
                risk_level = "high"
            elif max_correlation > 0.5:
                risk_level = "medium"
            else:
                risk_level = "low"
            
            return {
                "correlation_risk": risk_level,
                "max_correlation": max_correlation,
                "correlations": correlations,
                "correlated_positions": [c for c in correlations if c["correlation"] > 0.5],
                "diversification_benefit": max_correlation < 0.3
            }
        
        except Exception as e:
            logger.error(f"Correlation risk analysis failed for {symbol}: {e}")
            return {"error": str(e)}
    
    async def _calculate_var(
        self,
        symbol: str,
        position_sizing: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate Value-at-Risk (VaR)
        
        Args:
            symbol: Trading symbol
            position_sizing: Position sizing information
            
        Returns:
            VaR analysis
        """
        logger.info(f"Calculating VaR for {symbol}")
        
        try:
            position_value = position_sizing.get("position_value", 0)
            
            # Mock volatility - would calculate from historical data
            daily_volatility = 0.025  # 2.5% daily volatility
            
            # Calculate VaR for different time horizons
            confidence_level = self.var_confidence_level
            z_score = 1.96 if confidence_level == 0.95 else 2.58  # 95% or 99%
            
            var_1_day = position_value * daily_volatility * z_score
            var_1_week = position_value * daily_volatility * math.sqrt(5) * z_score
            var_1_month = position_value * daily_volatility * math.sqrt(22) * z_score
            
            return {
                "confidence_level": confidence_level,
                "daily_volatility": daily_volatility,
                "position_value": position_value,
                "var_1_day": var_1_day,
                "var_1_week": var_1_week,
                "var_1_month": var_1_month,
                "var_1_day_percent": var_1_day / position_value if position_value > 0 else 0
            }
        
        except Exception as e:
            logger.error(f"VaR calculation failed for {symbol}: {e}")
            return {"error": str(e)}
    
    def _make_risk_decision(self, risk_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make final risk decision based on all assessments
        
        Args:
            risk_assessment: Complete risk assessment
            
        Returns:
            Risk decision
        """
        # Extract key metrics
        portfolio_risk = risk_assessment.get("portfolio_risk", {})
        position_sizing = risk_assessment.get("position_sizing", {})
        risk_reward = risk_assessment.get("risk_reward", {})
        correlation_risk = risk_assessment.get("correlation_risk", {})
        var_analysis = risk_assessment.get("var_analysis", {})
        
        # Risk scoring (0-100)
        risk_scores = []
        
        # Portfolio exposure score
        exposure_ratio = portfolio_risk.get("exposure_ratio", 0)
        exposure_score = 100 - (exposure_ratio * 100)  # Lower exposure = higher score
        risk_scores.append(("exposure", exposure_score, 0.2))
        
        # Risk/reward score
        risk_reward_ratio = risk_reward.get("risk_reward_ratio", 0)
        rr_score = min(risk_reward_ratio * 25, 100)  # 4:1 ratio = 100 score
        risk_scores.append(("risk_reward", rr_score, 0.3))
        
        # Correlation score
        max_correlation = correlation_risk.get("max_correlation", 0)
        correlation_score = 100 - (max_correlation * 100)
        risk_scores.append(("correlation", correlation_score, 0.2))
        
        # VaR score
        var_1_day_percent = var_analysis.get("var_1_day_percent", 0)
        var_score = 100 - (var_1_day_percent * 1000)  # 10% VaR = 0 score
        risk_scores.append(("var", max(var_score, 0), 0.2))
        
        # Diversification score
        diversification_score = portfolio_risk.get("diversification_score", 50)
        risk_scores.append(("diversification", diversification_score, 0.1))
        
        # Calculate weighted risk score
        total_score = sum(score * weight for _, score, weight in risk_scores)
        
        # Decision thresholds
        if total_score >= 70:
            approved = True
            position_multiplier = 1.0
        elif total_score >= 50:
            approved = True
            position_multiplier = 0.7  # Reduce position size
        elif total_score >= 30:
            approved = True
            position_multiplier = 0.5  # Significantly reduce position size
        else:
            approved = False
            position_multiplier = 0.0
        
        # Calculate final position size
        estimated_shares = position_sizing.get("estimated_shares", 0)
        final_position_size = estimated_shares * position_multiplier
        
        # Calculate stop loss and take profit levels
        current_price = position_sizing.get("current_price", 150.0)
        stop_loss_percent = position_sizing.get("stop_loss_percent", 0.05)
        take_profit_percent = position_sizing.get("take_profit_percent", 0.10)
        
        stop_loss_price = current_price * (1 - stop_loss_percent)
        take_profit_price = current_price * (1 + take_profit_percent)
        
        # Generate rationale
        rationale_parts = []
        if total_score >= 70:
            rationale_parts.append("Strong risk profile")
        elif total_score >= 50:
            rationale_parts.append("Acceptable risk with reduced position")
        elif total_score >= 30:
            rationale_parts.append("High risk, minimal position only")
        else:
            rationale_parts.append("Risk too high for trading")
        
        # Add specific risk factors
        if risk_reward_ratio < 2.0:
            rationale_parts.append("unfavorable risk/reward ratio")
        if max_correlation > 0.7:
            rationale_parts.append("high correlation with existing positions")
        if exposure_ratio > 0.9:
            rationale_parts.append("high portfolio exposure")
        
        rationale = "; ".join(rationale_parts)
        
        return {
            "approved": approved,
            "risk_score": total_score,
            "position_size": final_position_size,
            "position_multiplier": position_multiplier,
            "stop_loss": stop_loss_price,
            "take_profit": take_profit_price,
            "rationale": rationale,
            "risk_breakdown": {name: score for name, score, _ in risk_scores}
        }
    
    def _calculate_kelly_fraction(self, analysis_result: Dict[str, Any]) -> float:
        """Calculate Kelly Criterion fraction"""
        confidence = analysis_result.get("confidence", 0.5)
        # Simplified Kelly calculation: f = (bp - q) / b
        # where b = odds, p = probability of win, q = probability of loss
        win_probability = 0.5 + (confidence - 0.5) * 0.5  # Convert confidence to probability
        loss_probability = 1 - win_probability
        odds = 2.0  # Assume 2:1 odds
        
        kelly_fraction = (odds * win_probability - loss_probability) / odds
        return max(0, min(kelly_fraction, 0.25))  # Cap at 25%
    
    def _calculate_stop_loss_percent(self, analysis_result: Dict[str, Any], risk_tolerance: str) -> float:
        """Calculate stop loss percentage"""
        base_stop_loss = {
            "conservative": 0.03,  # 3%
            "moderate": 0.05,      # 5%
            "aggressive": 0.08     # 8%
        }
        
        volatility_adjustment = 1.0  # Would adjust based on volatility
        return base_stop_loss.get(risk_tolerance, 0.05) * volatility_adjustment
    
    def _calculate_take_profit_percent(self, analysis_result: Dict[str, Any], risk_tolerance: str) -> float:
        """Calculate take profit percentage"""
        base_take_profit = {
            "conservative": 0.06,  # 6%
            "moderate": 0.10,      # 10%
            "aggressive": 0.15     # 15%
        }
        
        confidence = analysis_result.get("confidence", 0.5)
        confidence_adjustment = 0.5 + confidence  # 0.5x to 1.5x multiplier
        
        return base_take_profit.get(risk_tolerance, 0.10) * confidence_adjustment
    
    def _calculate_sector_exposure(self, positions: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate sector exposure percentages"""
        sector_values = {}
        total_value = sum(pos.get("market_value", 0) for pos in positions)
        
        for position in positions:
            sector = position.get("sector", "Unknown")
            value = position.get("market_value", 0)
            sector_values[sector] = sector_values.get(sector, 0) + value
        
        return {sector: value / total_value for sector, value in sector_values.items()} if total_value > 0 else {}
    
    def _calculate_portfolio_beta(self, positions: List[Dict[str, Any]]) -> float:
        """Calculate portfolio beta"""
        if not positions:
            return 1.0
        
        # Mock calculation - would use actual beta data
        total_value = sum(pos.get("market_value", 0) for pos in positions)
        weighted_beta = sum(pos.get("beta", 1.0) * pos.get("market_value", 0) for pos in positions)
        
        return weighted_beta / total_value if total_value > 0 else 1.0
    
    def _calculate_portfolio_volatility(self, positions: List[Dict[str, Any]]) -> float:
        """Calculate portfolio volatility"""
        if not positions:
            return 0.0
        
        # Simplified calculation - would use correlation matrix
        return 0.15  # Mock 15% volatility
    
    def _calculate_diversification_score(self, positions: List[Dict[str, Any]]) -> float:
        """Calculate diversification score (0-100)"""
        if not positions:
            return 100.0
        
        # Simple calculation based on number of positions and sector distribution
        num_positions = len(positions)
        sector_exposure = self._calculate_sector_exposure(positions)
        
        # Score based on number of positions
        position_score = min(num_positions * 10, 50)  # Max 50 points for 5+ positions
        
        # Score based on sector diversification
        if sector_exposure:
            max_sector_exposure = max(sector_exposure.values())
            sector_score = max(0, 50 - (max_sector_exposure - 0.2) * 100)  # Penalty for >20% in one sector
        else:
            sector_score = 0
        
        return position_score + sector_score
    
    def _calculate_correlation(self, symbol1: str, symbol2: str) -> float:
        """Calculate correlation between two symbols"""
        # Mock correlation calculation - would use actual market data
        # For now, return random correlation based on symbol similarity
        if symbol1 == symbol2:
            return 1.0
        
        # Mock logic: same sector = higher correlation
        # Would implement actual correlation calculation using historical price data
        return 0.3  # Default moderate correlation