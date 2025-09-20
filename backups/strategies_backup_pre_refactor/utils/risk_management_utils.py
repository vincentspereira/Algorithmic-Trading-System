import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging
from scipy import stats


@dataclass
class PortfolioRiskMetrics:
    """Portfolio-level risk metrics"""
    total_exposure: float
    sector_exposures: Dict[str, float]
    correlation_matrix: pd.DataFrame
    portfolio_volatility: float
    var_95: float  # Value at Risk 95%
    var_99: float  # Value at Risk 99%
    expected_shortfall: float
    beta_to_market: float
    

class RiskManagementUtils:
    """
    Utility class for common risk management functions used across strategies.
    Implements advanced risk management techniques for institutional-grade trading.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    def calculate_position_size_kelly(win_rate: float, avg_win: float, avg_loss: float, 
                                    account_balance: float, max_risk_per_trade: float = 0.02) -> float:
        """
        Calculate position size using Kelly Criterion with safety constraints.
        
        Args:
            win_rate: Historical win rate (0-1)
            avg_win: Average winning trade amount
            avg_loss: Average losing trade amount (positive value)
            account_balance: Current account balance
            max_risk_per_trade: Maximum risk per trade as fraction of account
            
        Returns:
            Position size as fraction of account balance
        """
        if avg_loss <= 0 or win_rate <= 0 or win_rate >= 1:
            return max_risk_per_trade
        
        # Kelly formula: f = (bp - q) / b
        # where b = avg_win/avg_loss, p = win_rate, q = 1 - win_rate
        b = avg_win / avg_loss
        p = win_rate
        q = 1 - win_rate
        
        kelly_fraction = (b * p - q) / b
        
        # Apply safety constraints
        kelly_fraction = max(0, kelly_fraction)  # No negative positions
        kelly_fraction = min(kelly_fraction, max_risk_per_trade)  # Cap at max risk
        kelly_fraction *= 0.25  # Quarter Kelly for safety
        
        return kelly_fraction
    
    @staticmethod
    def calculate_position_size_volatility_adjusted(price: float, atr: float, 
                                                  account_balance: float, 
                                                  risk_per_trade: float = 0.02) -> int:
        """
        Calculate position size based on volatility (ATR) targeting specific dollar risk.
        
        Args:
            price: Current price of the instrument
            atr: Average True Range (volatility measure)
            account_balance: Current account balance
            risk_per_trade: Risk per trade as fraction of account balance
            
        Returns:
            Number of shares/contracts to trade
        """
        if atr <= 0 or price <= 0:
            return 0
        
        dollar_risk = account_balance * risk_per_trade
        position_size = dollar_risk / (2 * atr)  # 2x ATR as stop distance
        
        return max(1, int(position_size / price))
    
    @staticmethod
    def calculate_correlation_adjustment(symbol: str, portfolio_positions: Dict[str, float],
                                      correlation_matrix: pd.DataFrame) -> float:
        """
        Calculate position size adjustment based on portfolio correlations.
        
        Args:
            symbol: Symbol to calculate adjustment for
            portfolio_positions: Current portfolio positions {symbol: weight}
            correlation_matrix: Correlation matrix between instruments
            
        Returns:
            Adjustment factor (0-1) to reduce position size based on correlations
        """
        if symbol not in correlation_matrix.index or not portfolio_positions:
            return 1.0
        
        total_correlation_exposure = 0.0
        
        for pos_symbol, weight in portfolio_positions.items():
            if pos_symbol in correlation_matrix.columns and pos_symbol != symbol:
                correlation = correlation_matrix.loc[symbol, pos_symbol]
                # Only consider positive correlations for adjustment
                if correlation > 0.3:  # Threshold for significant correlation
                    total_correlation_exposure += abs(weight) * correlation
        
        # Reduce position size based on correlation exposure
        adjustment_factor = max(0.1, 1.0 - (total_correlation_exposure * 0.5))
        return adjustment_factor
    
    @staticmethod
    def calculate_stop_loss_atr(price: float, atr: float, direction: str, 
                              multiplier: float = 2.0) -> float:
        """
        Calculate stop-loss price based on Average True Range.
        
        Args:
            price: Current entry price
            atr: Average True Range
            direction: 'long' or 'short'
            multiplier: ATR multiplier for stop distance
            
        Returns:
            Stop-loss price
        """
        stop_distance = atr * multiplier
        
        if direction.lower() == 'long':
            return price - stop_distance
        elif direction.lower() == 'short':
            return price + stop_distance
        else:
            raise ValueError("Direction must be 'long' or 'short'")
    
    @staticmethod
    def calculate_take_profit_rr(entry_price: float, stop_loss: float, 
                               risk_reward_ratio: float = 2.0) -> float:
        """
        Calculate take-profit price based on risk-reward ratio.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop-loss price
            risk_reward_ratio: Target risk-reward ratio
            
        Returns:
            Take-profit price
        """
        risk = abs(entry_price - stop_loss)
        reward = risk * risk_reward_ratio
        
        if entry_price > stop_loss:  # Long position
            return entry_price + reward
        else:  # Short position
            return entry_price - reward
    
    @staticmethod
    def calculate_trailing_stop_chandelier(highs: pd.Series, lows: pd.Series, 
                                         atr: pd.Series, period: int = 22, 
                                         multiplier: float = 3.0) -> pd.Series:
        """
        Calculate Chandelier Exit trailing stop levels.
        
        Args:
            highs: Series of high prices
            lows: Series of low prices
            atr: Series of ATR values
            period: Lookback period for highest/lowest
            multiplier: ATR multiplier
            
        Returns:
            Series of trailing stop levels
        """
        highest_high = highs.rolling(window=period).max()
        lowest_low = lows.rolling(window=period).min()
        
        long_stop = highest_high - (multiplier * atr)
        short_stop = lowest_low + (multiplier * atr)
        
        # Return both long and short stops as a DataFrame
        return pd.DataFrame({
            'long_stop': long_stop,
            'short_stop': short_stop
        })
    
    @staticmethod
    def calculate_portfolio_var(returns: pd.DataFrame, confidence_level: float = 0.95) -> float:
        """
        Calculate portfolio Value at Risk using historical simulation.
        
        Args:
            returns: DataFrame of portfolio returns
            confidence_level: Confidence level for VaR calculation
            
        Returns:
            Value at Risk as a positive number
        """
        if returns.empty:
            return 0.0
        
        portfolio_returns = returns.sum(axis=1) if len(returns.columns) > 1 else returns.iloc[:, 0]
        var_percentile = (1 - confidence_level) * 100
        var = np.percentile(portfolio_returns.dropna(), var_percentile)
        
        return abs(var)
    
    @staticmethod
    def calculate_expected_shortfall(returns: pd.Series, confidence_level: float = 0.95) -> float:
        """
        Calculate Expected Shortfall (Conditional VaR).
        
        Args:
            returns: Series of returns
            confidence_level: Confidence level
            
        Returns:
            Expected Shortfall as a positive number
        """
        if returns.empty:
            return 0.0
        
        var_threshold = np.percentile(returns.dropna(), (1 - confidence_level) * 100)
        tail_losses = returns[returns <= var_threshold]
        
        if len(tail_losses) == 0:
            return 0.0
        
        return abs(tail_losses.mean())
    
    @staticmethod
    def calculate_maximum_drawdown(equity_curve: pd.Series) -> Tuple[float, pd.Timestamp, pd.Timestamp]:
        """
        Calculate maximum drawdown from equity curve.
        
        Args:
            equity_curve: Series of portfolio equity values
            
        Returns:
            Tuple of (max_drawdown, peak_date, trough_date)
        """
        if equity_curve.empty:
            return 0.0, None, None
        
        # Calculate running maximum
        running_max = equity_curve.expanding().max()
        
        # Calculate drawdown
        drawdown = (equity_curve - running_max) / running_max
        
        # Find maximum drawdown
        max_dd = drawdown.min()
        max_dd_date = drawdown.idxmin()
        
        # Find the peak before maximum drawdown
        peak_date = running_max[:max_dd_date].idxmax()
        
        return abs(max_dd), peak_date, max_dd_date
    
    @staticmethod
    def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """
        Calculate Sharpe ratio.
        
        Args:
            returns: Series of returns
            risk_free_rate: Annual risk-free rate
            
        Returns:
            Sharpe ratio
        """
        if returns.empty or returns.std() == 0:
            return 0.0
        
        excess_returns = returns - (risk_free_rate / 252)  # Daily risk-free rate
        return excess_returns.mean() / returns.std() * np.sqrt(252)
    
    @staticmethod
    def calculate_sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """
        Calculate Sortino ratio (uses downside deviation instead of total volatility).
        
        Args:
            returns: Series of returns
            risk_free_rate: Annual risk-free rate
            
        Returns:
            Sortino ratio
        """
        if returns.empty:
            return 0.0
        
        excess_returns = returns - (risk_free_rate / 252)
        downside_returns = excess_returns[excess_returns < 0]
        
        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0.0
        
        downside_deviation = downside_returns.std()
        return excess_returns.mean() / downside_deviation * np.sqrt(252)
    
    @staticmethod
    def calculate_calmar_ratio(returns: pd.Series) -> float:
        """
        Calculate Calmar ratio (annual return / maximum drawdown).
        
        Args:
            returns: Series of returns
            
        Returns:
            Calmar ratio
        """
        if returns.empty:
            return 0.0
        
        annual_return = (1 + returns).prod() ** (252 / len(returns)) - 1
        equity_curve = (1 + returns).cumprod()
        max_dd, _, _ = RiskManagementUtils.calculate_maximum_drawdown(equity_curve)
        
        if max_dd == 0:
            return 0.0
        
        return annual_return / max_dd
    
    @staticmethod
    def calculate_beta(asset_returns: pd.Series, market_returns: pd.Series) -> float:
        """
        Calculate beta coefficient relative to market.
        
        Args:
            asset_returns: Series of asset returns
            market_returns: Series of market returns
            
        Returns:
            Beta coefficient
        """
        if len(asset_returns) != len(market_returns) or len(asset_returns) < 2:
            return 1.0
        
        # Align the series
        aligned_data = pd.DataFrame({
            'asset': asset_returns,
            'market': market_returns
        }).dropna()
        
        if len(aligned_data) < 2:
            return 1.0
        
        covariance = aligned_data['asset'].cov(aligned_data['market'])
        market_variance = aligned_data['market'].var()
        
        if market_variance == 0:
            return 1.0
        
        return covariance / market_variance
    
    @staticmethod
    def check_risk_limits(current_positions: Dict[str, float], 
                         new_position: Dict[str, float],
                         risk_limits: Dict[str, float]) -> Tuple[bool, str]:
        """
        Check if new position violates risk limits.
        
        Args:
            current_positions: Current portfolio positions
            new_position: Proposed new position
            risk_limits: Dictionary of risk limits
            
        Returns:
            Tuple of (is_valid, reason)
        """
        # Calculate total exposure after new position
        total_exposure = sum(abs(pos) for pos in current_positions.values())
        new_exposure = sum(abs(pos) for pos in new_position.values())
        
        # Check maximum exposure limit
        max_exposure = risk_limits.get('max_total_exposure', 1.0)
        if total_exposure + new_exposure > max_exposure:
            return False, f"Total exposure {total_exposure + new_exposure:.2f} exceeds limit {max_exposure:.2f}"
        
        # Check maximum position size
        max_position_size = risk_limits.get('max_position_size', 0.1)
        for symbol, size in new_position.items():
            if abs(size) > max_position_size:
                return False, f"Position size {abs(size):.2f} for {symbol} exceeds limit {max_position_size:.2f}"
        
        # Check sector concentration (if sector mapping provided)
        sector_limits = risk_limits.get('sector_limits', {})
        if sector_limits:
            # This would require sector mapping - simplified for now
            pass
        
        return True, "All risk limits satisfied"
    
    @staticmethod
    def calculate_optimal_leverage(returns: pd.Series, target_volatility: float = 0.15) -> float:
        """
        Calculate optimal leverage to achieve target volatility.
        
        Args:
            returns: Series of strategy returns
            target_volatility: Target annual volatility
            
        Returns:
            Optimal leverage multiplier
        """
        if returns.empty or returns.std() == 0:
            return 1.0
        
        current_volatility = returns.std() * np.sqrt(252)
        
        if current_volatility == 0:
            return 1.0
        
        optimal_leverage = target_volatility / current_volatility
        
        # Cap leverage at reasonable levels
        return min(optimal_leverage, 3.0)