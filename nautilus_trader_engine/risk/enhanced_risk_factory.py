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
    # Defaults used when callers omit portfolio_value/asset_price
    default_portfolio_value: float = 100000.0
    default_asset_price: float = 100.0


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
        # Cached market context for compatibility with callers expecting this API
        self._last_atr = None
        self._last_volatility = None
        self._last_prices = None
        self._last_volumes = None

    def update_market_data(self, prices, volumes):
        """Compatibility method: cache recent prices/volumes and compute ATR/volatility.
        - ATR approximation aligns with existing fallback: mean(abs(diff(prices))).
        - Volatility approximated as std of log returns.
        """
        try:
            import numpy as np  # local import to avoid hard dependency at module load
            prices_arr = np.asarray(prices, dtype=float)
            volumes_arr = np.asarray(volumes, dtype=float)
            if prices_arr.size >= 2:
                diffs = np.abs(np.diff(prices_arr))
                self._last_atr = float(np.mean(diffs)) if diffs.size > 0 else 0.0
                rets = np.diff(np.log(prices_arr))
                self._last_volatility = float(np.std(rets)) if rets.size > 0 else 0.0
            else:
                self._last_atr = 0.0
                self._last_volatility = 0.0
            self._last_prices = prices_arr
            self._last_volumes = volumes_arr
        except Exception as e:
            self.logger.error(f"update_market_data failed: {e}")
            self._last_atr = self._last_atr if self._last_atr is not None else 0.0
            self._last_volatility = self._last_volatility if self._last_volatility is not None else 0.0

    def calculate_position_size(self, 
                              signal_strength: float,
                              portfolio_value: float = None,
                              asset_price: float = None,
                              volatility: float = None,
                              atr: float = None,
                              confidence: float = None,
                              market_regime: str = None) -> float:
        """
        Calculate position size based on risk management rules.
        
        Parameters
        ----------
        signal_strength : float
            Signal strength from indicator (-1 to 1)
        portfolio_value : float, optional
            Current portfolio value; if omitted, defaults from config
        asset_price : float, optional
            Current asset price; if omitted, defaults from config
        volatility : float, optional
            Asset volatility for volatility-adjusted sizing
        atr : float, optional
            Average True Range for risk-based sizing
        confidence : float, optional
            Confidence (0-1) used to scale position size
        market_regime : str, optional
            Regime label used for regime-based scaling (e.g., 'trending_up', 'sideways', 'high_volatility')
            
        Returns
        -------
        float
            Position size in units
        """
        try:
            # Provide sensible defaults when not supplied
            if portfolio_value is None:
                portfolio_value = getattr(self.config, 'default_portfolio_value', 100000.0)
            if asset_price is None or asset_price <= 0:
                asset_price = getattr(self.config, 'default_asset_price', 100.0)
            
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
                    
            # Apply maximum position size limit (value-based)
            max_position_value = portfolio_value * self.config.max_position_size
            max_position_units = max_position_value / asset_price
            position_size = min(position_size, max_position_units)
            
            # Apply signal strength again (preserve previous behavior)
            position_size = position_size * abs(signal_strength)
            
            # Confidence scaling
            if confidence is not None:
                try:
                    position_size *= float(np.clip(confidence, 0.0, 1.0))
                except Exception:
                    pass
            
            # Regime-based scaling
            if self.config.regime_adjustment and market_regime:
                regime = str(market_regime).lower()
                regime_multiplier = 1.0
                if 'sideways' in regime or 'range' in regime:
                    regime_multiplier = 0.8
                elif 'trend' in regime or 'bull' in regime or 'bear' in regime:
                    regime_multiplier = 1.1
                if 'extreme' in regime or ('high' in regime and 'vol' in regime):
                    regime_multiplier *= 0.8
                position_size *= regime_multiplier
            
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
        """
        try:
            # Normalize direction (support string inputs for backward-compatibility)
            if isinstance(signal_direction, str):
                direction = 1 if signal_direction.lower() in ("long", "buy", "bull") else -1
            else:
                direction = 1 if int(signal_direction) >= 0 else -1

            # Use cached ATR/volatility if not provided
            if atr is None:
                atr = self._last_atr
            if volatility is None:
                volatility = self._last_volatility

            stop_loss = entry_price
            if self.config.stop_loss_method == StopLossMethod.FIXED_PERCENTAGE:
                stop_loss = entry_price * (1 - (self.config.atr_multiplier * 0.01) * direction)
            elif self.config.stop_loss_method == StopLossMethod.ATR_TRAILING and atr:
                stop_loss = entry_price - (atr * self.config.atr_multiplier * direction)
            elif self.config.stop_loss_method == StopLossMethod.VOLATILITY_BASED and volatility:
                stop_loss = entry_price - (volatility * self.config.atr_multiplier * 100 * direction)
            else:
                stop_loss = entry_price * (1 - (0.02 * direction))
            return stop_loss
        except Exception as e:
            self.logger.error(f"Error calculating stop loss: {e}")
            try:
                direction = 1 if (isinstance(signal_direction, str) and signal_direction.lower() in ("long", "buy", "bull")) or int(signal_direction) >= 0 else -1
            except Exception:
                direction = 1
            return entry_price * (1 - (0.02 * direction))

    def calculate_take_profit(self, 
                            entry_price: float,
                            stop_loss: float = None,
                            signal_direction: int = None,
                            risk_reward_ratio: float = 2.0) -> float:
        """
        Calculate take profit level based on risk-reward ratio.
        Backward-compatible: if called with (entry_price, 'long'/'short'), infer stop_loss using cached ATR.
        """
        try:
            # Backward-compat handling: (entry_price, direction)
            if signal_direction is None and isinstance(stop_loss, (str, int)):
                dir_val = stop_loss
                if isinstance(dir_val, str):
                    direction = 1 if dir_val.lower() in ("long", "buy", "bull") else -1
                else:
                    direction = 1 if int(dir_val) >= 0 else -1
                # Infer stop_loss using current settings and cached ATR/volatility
                inferred_sl = self.calculate_stop_loss(entry_price=entry_price, signal_direction=direction)
                stop_loss = inferred_sl
                signal_direction = direction

            # Final safety: default direction if still None
            if signal_direction is None:
                signal_direction = 1 if (stop_loss is not None and stop_loss < entry_price) else -1

            risk_amount = abs(entry_price - (stop_loss if stop_loss is not None else entry_price * 0.98))
            reward_amount = risk_amount * risk_reward_ratio
            take_profit = entry_price + (reward_amount * (1 if signal_direction > 0 else -1))
            return take_profit
        except Exception as e:
            self.logger.error(f"Error calculating take profit: {e}")
            try:
                direction = 1 if (isinstance(signal_direction, str) and signal_direction.lower() in ("long", "buy", "bull")) or int(signal_direction) >= 0 else -1
            except Exception:
                direction = 1
            risk_amount = abs(entry_price - (stop_loss if stop_loss is not None else entry_price * 0.98))
            reward_amount = risk_amount * 2.0
            return entry_price + (reward_amount * (1 if direction > 0 else -1))
            
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