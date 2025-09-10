"""
Enhanced Risk Factory
Institutional-grade risk management with advanced position sizing and stop loss calculations.
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


class PositionSizingMethod(Enum):
    """Position sizing methods"""
    FIXED_FRACTIONAL = "fixed_fractional"
    KELLY_CRITERION = "kelly_criterion"
    OPTIMAL_F = "optimal_f"
    VOLATILITY_ADJUSTED = "volatility_adjusted"


class StopLossMethod(Enum):
    """Stop loss calculation methods"""
    FIXED_PERCENTAGE = "fixed_percentage"
    ATR_TRAILING = "atr_trailing"
    VOLATILITY_BASED = "volatility_based"
    SUPPORT_RESISTANCE = "support_resistance"


@dataclass
class EnhancedRiskConfig:
    """Configuration for enhanced risk management"""
    base_risk_per_trade: float = 0.02  # 2% of portfolio per trade
    max_portfolio_risk: float = 0.10   # 10% max portfolio risk
    position_sizing_method: PositionSizingMethod = PositionSizingMethod.KELLY_CRITERION
    stop_loss_method: StopLossMethod = StopLossMethod.ATR_TRAILING
    atr_period: int = 14
    atr_multiplier: float = 2.0
    max_position_size: float = 0.05  # 5% max position size
    correlation_adjustment: bool = True
    regime_adjustment: bool = True
    volatility_scaling: bool = True


@dataclass
class RiskMetrics:
    """Comprehensive risk metrics"""
    position_size: float = 0.0
    stop_loss_level: float = 0.0
    take_profit_level: float = 0.0
    risk_reward_ratio: float = 0.0
    expected_value: float = 0.0
    volatility_adjusted_risk: float = 0.0
    correlation_adjusted_risk: float = 0.0
    regime_risk_multiplier: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RiskAdjustedOutput:
    """Output from risk adjustment calculations"""
    adjusted_signal: float = 0.0
    position_size: float = 0.0
    confidence: float = 1.0
    risk_metrics: RiskMetrics = field(default_factory=RiskMetrics)
    metadata: Dict[str, Any] = field(default_factory=dict)


class EnhancedRiskFactory:
    """Advanced risk management factory with institutional-grade features"""
    
    def __init__(self, config: EnhancedRiskConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._risk_history = []
        self._performance_metrics = {}
        
    def calculate_position_size(self, 
                              signal_strength: float,
                              portfolio_value: float,
                              asset_price: float,
                              volatility: float = None,
                              atr: float = None) -> float:
        """
        Calculate position size based on risk management rules.
        
        Parameters
        ----------
        signal_strength : float
            Signal strength from indicator (-1 to 1)
        portfolio_value : float
            Current portfolio value
        asset_price : float
            Current asset price
        volatility : float, optional
            Asset volatility for volatility-adjusted sizing
        atr : float, optional
            Average True Range for risk-based sizing
            
        Returns
        -------
        float
            Position size in units
        """
        try:
            # Base position size calculation
            base_risk_amount = portfolio_value * self.config.base_risk_per_trade
            position_size = 0.0
            
            if self.config.position_sizing_method == PositionSizingMethod.FIXED_FRACTIONAL:
                position_size = (base_risk_amount / asset_price) * abs(signal_strength)
                
            elif self.config.position_sizing_method == PositionSizingMethod.KELLY_CRITERION:
                # Simplified Kelly criterion
                win_rate = 0.55  # Default assumption
                win_loss_ratio = 2.0  # Default assumption
                kelly_fraction = win_rate - ((1 - win_rate) / win_loss_ratio)
                kelly_fraction = max(0, min(kelly_fraction, 1.0))  # Clamp between 0 and 1
                position_size = (base_risk_amount / asset_price) * kelly_fraction * abs(signal_strength)
                
            elif self.config.position_sizing_method == PositionSizingMethod.VOLATILITY_ADJUSTED:
                if volatility and volatility > 0:
                    # Inverse volatility sizing
                    vol_adjustment = 1.0 / (volatility * 100)  # Normalize
                    position_size = (base_risk_amount / asset_price) * vol_adjustment * abs(signal_strength)
                else:
                    position_size = (base_risk_amount / asset_price) * abs(signal_strength)
                    
            # Apply maximum position size limit
            max_position_value = portfolio_value * self.config.max_position_size
            max_position_units = max_position_value / asset_price
            position_size = min(position_size, max_position_units)
            
            # Apply signal strength
            position_size = position_size * abs(signal_strength)
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0.0
            
    def calculate_stop_loss(self, 
                          entry_price: float,
                          signal_direction: int,
                          atr: float = None,
                          volatility: float = None) -> float:
        """
        Calculate stop loss level.
        
        Parameters
        ----------
        entry_price : float
            Entry price for the position
        signal_direction : int
            Direction of signal (-1 for short, 1 for long)
        atr : float, optional
            Average True Range for ATR-based stops
        volatility : float, optional
            Volatility for volatility-based stops
            
        Returns
        -------
        float
            Stop loss price level
        """
        try:
            stop_loss = entry_price
            
            if self.config.stop_loss_method == StopLossMethod.FIXED_PERCENTAGE:
                stop_loss = entry_price * (1 - (self.config.atr_multiplier * 0.01) * signal_direction)
                
            elif self.config.stop_loss_method == StopLossMethod.ATR_TRAILING and atr:
                stop_loss = entry_price - (atr * self.config.atr_multiplier * signal_direction)
                
            elif self.config.stop_loss_method == StopLossMethod.VOLATILITY_BASED and volatility:
                stop_loss = entry_price - (volatility * self.config.atr_multiplier * 100 * signal_direction)
                
            else:
                # Default fixed percentage
                stop_loss = entry_price * (1 - (0.02 * signal_direction))
                
            return stop_loss
            
        except Exception as e:
            self.logger.error(f"Error calculating stop loss: {e}")
            return entry_price * (1 - (0.02 * signal_direction))
            
    def calculate_take_profit(self, 
                            entry_price: float,
                            stop_loss: float,
                            signal_direction: int,
                            risk_reward_ratio: float = 2.0) -> float:
        """
        Calculate take profit level based on risk-reward ratio.
        
        Parameters
        ----------
        entry_price : float
            Entry price for the position
        stop_loss : float
            Stop loss level
        signal_direction : int
            Direction of signal (-1 for short, 1 for long)
        risk_reward_ratio : float
            Desired risk-reward ratio
            
        Returns
        -------
        float
            Take profit price level
        """
        try:
            risk_amount = abs(entry_price - stop_loss)
            reward_amount = risk_amount * risk_reward_ratio
            take_profit = entry_price + (reward_amount * signal_direction)
            return take_profit
            
        except Exception as e:
            self.logger.error(f"Error calculating take profit: {e}")
            risk_amount = abs(entry_price - stop_loss)
            reward_amount = risk_amount * 2.0
            return entry_price + (reward_amount * signal_direction)
            
    def adjust_for_risk(self, 
                       signal: float,
                       portfolio_value: float,
                       asset_price: float,
                       entry_price: float = None,
                       volatility: float = None,
                       atr: float = None,
                       correlation_factor: float = 1.0,
                       regime_factor: float = 1.0) -> RiskAdjustedOutput:
        """
        Apply comprehensive risk adjustments to a trading signal.
        
        Parameters
        ----------
        signal : float
            Original trading signal (-1 to 1)
        portfolio_value : float
            Current portfolio value
        asset_price : float
            Current asset price
        entry_price : float, optional
            Entry price for position
        volatility : float, optional
            Asset volatility
        atr : float, optional
            Average True Range
        correlation_factor : float
            Correlation adjustment factor
        regime_factor : float
            Market regime adjustment factor
            
        Returns
        -------
        RiskAdjustedOutput
            Risk-adjusted signal and metrics
        """
        try:
            # Calculate position size
            position_size = self.calculate_position_size(
                signal_strength=signal,
                portfolio_value=portfolio_value,
                asset_price=asset_price,
                volatility=volatility,
                atr=atr
            )
            
            # Calculate stop loss if entry price provided
            stop_loss = entry_price
            take_profit = entry_price
            risk_reward_ratio = 2.0
            
            if entry_price:
                stop_loss = self.calculate_stop_loss(
                    entry_price=entry_price,
                    signal_direction=1 if signal > 0 else -1,
                    atr=atr,
                    volatility=volatility
                )
                
                take_profit = self.calculate_take_profit(
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    signal_direction=1 if signal > 0 else -1,
                    risk_reward_ratio=risk_reward_ratio
                )
                
                risk_reward_ratio = abs(take_profit - entry_price) / abs(entry_price - stop_loss)
            
            # Apply risk adjustments
            adjusted_signal = signal
            
            # Correlation adjustment
            if self.config.correlation_adjustment:
                adjusted_signal = adjusted_signal * correlation_factor
                
            # Regime adjustment
            if self.config.regime_adjustment:
                adjusted_signal = adjusted_signal * regime_factor
                
            # Volatility scaling
            if self.config.volatility_scaling and volatility:
                vol_scaling = min(1.0, 1.0 / (volatility * 100))  # Inverse volatility scaling
                adjusted_signal = adjusted_signal * vol_scaling
            
            # Calculate expected value
            win_rate = 0.55  # Default assumption
            avg_win = abs(take_profit - entry_price) if entry_price and take_profit else asset_price * 0.02
            avg_loss = abs(entry_price - stop_loss) if entry_price and stop_loss else asset_price * 0.01
            expected_value = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
            
            # Create risk metrics
            risk_metrics = RiskMetrics(
                position_size=position_size,
                stop_loss_level=stop_loss or 0.0,
                take_profit_level=take_profit or 0.0,
                risk_reward_ratio=risk_reward_ratio,
                expected_value=expected_value,
                volatility_adjusted_risk=volatility or 0.0,
                correlation_adjusted_risk=correlation_factor,
                regime_risk_multiplier=regime_factor
            )
            
            # Create output
            output = RiskAdjustedOutput(
                adjusted_signal=adjusted_signal,
                position_size=position_size,
                confidence=abs(signal),
                risk_metrics=risk_metrics
            )
            
            # Store in history
            self._risk_history.append({
                'timestamp': datetime.now(),
                'signal': signal,
                'adjusted_signal': adjusted_signal,
                'position_size': position_size,
                'risk_metrics': risk_metrics
            })
            
            return output
            
        except Exception as e:
            self.logger.error(f"Error in risk adjustment: {e}")
            return RiskAdjustedOutput(
                adjusted_signal=signal,
                position_size=0.0,
                confidence=abs(signal)
            )


# Example usage
if __name__ == "__main__":
    # Create risk factory
    config = EnhancedRiskConfig(
        base_risk_per_trade=0.02,
        position_sizing_method=PositionSizingMethod.KELLY_CRITERION,
        stop_loss_method=StopLossMethod.ATR_TRAILING
    )
    
    risk_factory = EnhancedRiskFactory(config)
    
    # Example risk adjustment
    output = risk_factory.adjust_for_risk(
        signal=0.75,
        portfolio_value=100000,
        asset_price=150.0,
        entry_price=150.0,
        volatility=0.02,
        atr=1.5,
        correlation_factor=0.8,
        regime_factor=1.2
    )
    
    print(f"Original signal: 0.75")
    print(f"Adjusted signal: {output.adjusted_signal:.3f}")
    print(f"Position size: {output.position_size:.2f} units")
    print(f"Stop loss: ${output.risk_metrics.stop_loss_level:.2f}")
    print(f"Take profit: ${output.risk_metrics.take_profit_level:.2f}")
    print(f"Risk/Reward ratio: {output.risk_metrics.risk_reward_ratio:.2f}")