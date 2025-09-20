"""Volatility Arbitrage Strategies

This module implements volatility arbitrage strategies that exploit discrepancies
between implied and realized volatility, and volatility surface inefficiencies.

Key Features:
- Implied vs realized volatility arbitrage
- Volatility surface analysis and arbitrage
- Options pricing model integration
- Delta-neutral hedging strategies
- Volatility forecasting and prediction
- Multi-expiration volatility analysis

Strategies:
- VolatilityArbitrageStrategy: Base volatility arbitrage implementation
- ImpliedRealizedArbitrageStrategy: IV vs RV arbitrage
- VolatilitySurfaceArbitrageStrategy: Surface arbitrage opportunities

Architecture:
- Follows 5-Pillar Architecture principles
- Integrates with options pricing models
- Real-time volatility monitoring
- Risk-neutral hedging implementation
"""

import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Union
from scipy import stats
from scipy.optimize import minimize_scalar

# Core imports
from ...core.data_types import MarketData, Signal, Position
from ...core.events import SignalEvent, OrderEvent
from ...core.risk_management import RiskManager
from ...core.portfolio_management import PortfolioManager
from ...core.signal_generator import SignalGenerator
from ..base_strategy import BaseStrategy, StrategyConfig
from ...utils.technical_indicators import (
    calculate_sma, calculate_ema, calculate_atr,
    calculate_bollinger_bands, calculate_rsi
)
from ...utils.market_utils import (
    calculate_returns, calculate_volatility,
    normalize_prices, validate_market_data
)

# Configure logging
logger = logging.getLogger(__name__)

class VolatilityArbitrageType(Enum):
    """Types of volatility arbitrage strategies"""
    IMPLIED_REALIZED = "implied_realized"      # IV vs RV arbitrage
    VOLATILITY_SURFACE = "volatility_surface"  # Surface arbitrage
    TERM_STRUCTURE = "term_structure"          # Term structure arbitrage
    SKEW_ARBITRAGE = "skew_arbitrage"          # Volatility skew arbitrage
    CALENDAR_SPREAD = "calendar_spread"        # Calendar spread arbitrage

@dataclass
class VolatilitySurface:
    """Represents a volatility surface point"""
    underlying_symbol: str
    strike: float
    expiration: datetime
    option_type: str  # 'call' or 'put'
    implied_vol: float
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    price: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    volume: int = 0
    open_interest: int = 0
    
    @property
    def moneyness(self) -> float:
        """Calculate moneyness (strike/spot)"""
        return self.strike / 100.0  # Placeholder, needs spot price
    
    @property
    def time_to_expiry(self) -> float:
        """Calculate time to expiry in years"""
        now = datetime.now()
        if self.expiration > now:
            days = (self.expiration - now).days
            return days / 365.0
        return 0.0

@dataclass
class VolatilityOpportunity:
    """Represents a volatility arbitrage opportunity"""
    timestamp: datetime
    underlying_symbol: str
    strategy_type: VolatilityArbitrageType
    implied_vol: float
    realized_vol: float
    forecast_vol: float
    vol_spread: float
    vol_spread_pct: float
    confidence: float
    expected_return: float
    risk_score: float
    hedge_ratio: float
    position_delta: float
    vega_exposure: float
    theta_decay: float
    surface_points: List[VolatilitySurface] = field(default_factory=list)
    
    def __post_init__(self):
        """Calculate derived metrics"""
        self.vol_spread = self.implied_vol - self.realized_vol
        if self.realized_vol > 0:
            self.vol_spread_pct = (self.vol_spread / self.realized_vol) * 100
        else:
            self.vol_spread_pct = 0.0

class VolatilityAnalyzer:
    """Analyzes volatility arbitrage opportunities"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.min_vol_spread = config.get('min_vol_spread', 0.05)
        self.lookback_period = config.get('lookback_period', 30)
        self.hedge_ratio = config.get('hedge_ratio', 0.8)
        self.risk_free_rate = config.get('risk_free_rate', 0.02)
        
        # Historical data storage
        self.price_history: Dict[str, pd.Series] = {}
        self.vol_history: Dict[str, pd.Series] = {}
        self.implied_vol_history: Dict[str, pd.Series] = {}
        self.realized_vol_history: Dict[str, pd.Series] = {}
        
        logger.info("VolatilityAnalyzer initialized")
    
    def calculate_realized_volatility(
        self,
        prices: pd.Series,
        window: int = 30,
        annualize: bool = True
    ) -> float:
        """Calculate realized volatility
        
        Args:
            prices: Price series
            window: Lookback window
            annualize: Whether to annualize the volatility
            
        Returns:
            Realized volatility
        """
        try:
            if len(prices) < window + 1:
                return 0.0
            
            # Calculate log returns
            log_returns = np.log(prices / prices.shift(1)).dropna()
            
            if len(log_returns) < window:
                return 0.0
            
            # Calculate rolling volatility
            recent_returns = log_returns.tail(window)
            vol = recent_returns.std()
            
            if annualize:
                vol *= np.sqrt(252)  # Annualize assuming 252 trading days
            
            return vol
            
        except Exception as e:
            logger.error(f"Error calculating realized volatility: {e}")
            return 0.0
    
    def calculate_garch_volatility(
        self,
        returns: pd.Series,
        forecast_horizon: int = 1
    ) -> float:
        """Calculate GARCH-based volatility forecast
        
        Args:
            returns: Return series
            forecast_horizon: Forecast horizon in days
            
        Returns:
            Forecasted volatility
        """
        try:
            if len(returns) < 50:  # Need sufficient data for GARCH
                return self.calculate_realized_volatility(returns)
            
            # Simple GARCH(1,1) approximation
            # In practice, would use arch library
            
            # Calculate squared returns
            squared_returns = returns ** 2
            
            # Simple exponential smoothing as GARCH proxy
            alpha = 0.1  # GARCH alpha parameter
            beta = 0.85  # GARCH beta parameter
            
            # Initialize with sample variance
            long_run_var = squared_returns.mean()
            
            # Calculate conditional variance
            conditional_vars = []
            current_var = long_run_var
            
            for ret in squared_returns:
                current_var = (1 - alpha - beta) * long_run_var + alpha * ret + beta * current_var
                conditional_vars.append(current_var)
            
            # Forecast volatility
            if conditional_vars:
                forecast_var = conditional_vars[-1]
                forecast_vol = np.sqrt(forecast_var * 252)  # Annualize
            else:
                forecast_vol = np.sqrt(long_run_var * 252)
            
            return forecast_vol
            
        except Exception as e:
            logger.error(f"Error calculating GARCH volatility: {e}")
            return self.calculate_realized_volatility(returns)
    
    def black_scholes_implied_vol(
        self,
        option_price: float,
        spot_price: float,
        strike: float,
        time_to_expiry: float,
        risk_free_rate: float,
        option_type: str = 'call'
    ) -> float:
        """Calculate Black-Scholes implied volatility
        
        Args:
            option_price: Market price of option
            spot_price: Current spot price
            strike: Strike price
            time_to_expiry: Time to expiry in years
            risk_free_rate: Risk-free rate
            option_type: 'call' or 'put'
            
        Returns:
            Implied volatility
        """
        try:
            if time_to_expiry <= 0 or option_price <= 0:
                return 0.0
            
            def black_scholes_price(vol):
                """Black-Scholes option pricing formula"""
                if vol <= 0:
                    return 0.0
                
                d1 = (np.log(spot_price / strike) + (risk_free_rate + 0.5 * vol**2) * time_to_expiry) / (vol * np.sqrt(time_to_expiry))
                d2 = d1 - vol * np.sqrt(time_to_expiry)
                
                if option_type.lower() == 'call':
                    price = spot_price * stats.norm.cdf(d1) - strike * np.exp(-risk_free_rate * time_to_expiry) * stats.norm.cdf(d2)
                else:  # put
                    price = strike * np.exp(-risk_free_rate * time_to_expiry) * stats.norm.cdf(-d2) - spot_price * stats.norm.cdf(-d1)
                
                return price
            
            def objective(vol):
                """Objective function for implied volatility"""
                return abs(black_scholes_price(vol) - option_price)
            
            # Use numerical optimization to find implied volatility
            result = minimize_scalar(objective, bounds=(0.01, 5.0), method='bounded')
            
            if result.success:
                return result.x
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Error calculating implied volatility: {e}")
            return 0.0
    
    def detect_volatility_opportunity(
        self,
        underlying_data: MarketData,
        surface_data: List[VolatilitySurface],
        strategy_type: VolatilityArbitrageType = VolatilityArbitrageType.IMPLIED_REALIZED
    ) -> Optional[VolatilityOpportunity]:
        """Detect volatility arbitrage opportunities
        
        Args:
            underlying_data: Underlying asset market data
            surface_data: Volatility surface data
            strategy_type: Type of volatility arbitrage
            
        Returns:
            VolatilityOpportunity if found, None otherwise
        """
        try:
            symbol = underlying_data.symbol
            
            # Get price history for realized volatility calculation
            if symbol not in self.price_history:
                return None
            
            prices = self.price_history[symbol]
            if len(prices) < self.lookback_period:
                return None
            
            # Calculate realized volatility
            realized_vol = self.calculate_realized_volatility(prices, self.lookback_period)
            
            if realized_vol <= 0:
                return None
            
            # Calculate forecast volatility
            returns = prices.pct_change().dropna()
            forecast_vol = self.calculate_garch_volatility(returns)
            
            # Get implied volatility from surface data
            if not surface_data:
                return None
            
            # Use ATM options for main comparison
            atm_options = self._get_atm_options(surface_data, underlying_data.close)
            
            if not atm_options:
                return None
            
            # Calculate average implied volatility
            implied_vols = [opt.implied_vol for opt in atm_options if opt.implied_vol > 0]
            
            if not implied_vols:
                return None
            
            implied_vol = np.mean(implied_vols)
            
            # Check if opportunity meets threshold
            vol_spread = implied_vol - realized_vol
            
            if abs(vol_spread) < self.min_vol_spread:
                return None
            
            # Calculate opportunity metrics
            confidence = self._calculate_vol_confidence(implied_vol, realized_vol, forecast_vol)
            risk_score = self._calculate_vol_risk_score(underlying_data, surface_data)
            expected_return = self._calculate_expected_return(vol_spread, implied_vol)
            
            # Calculate Greeks for hedging
            hedge_ratio = self._calculate_hedge_ratio(atm_options)
            position_delta = sum(opt.delta for opt in atm_options) / len(atm_options)
            vega_exposure = sum(opt.vega for opt in atm_options)
            theta_decay = sum(opt.theta for opt in atm_options)
            
            opportunity = VolatilityOpportunity(
                timestamp=underlying_data.timestamp,
                underlying_symbol=symbol,
                strategy_type=strategy_type,
                implied_vol=implied_vol,
                realized_vol=realized_vol,
                forecast_vol=forecast_vol,
                vol_spread=vol_spread,
                vol_spread_pct=(vol_spread / realized_vol) * 100,
                confidence=confidence,
                expected_return=expected_return,
                risk_score=risk_score,
                hedge_ratio=hedge_ratio,
                position_delta=position_delta,
                vega_exposure=vega_exposure,
                theta_decay=theta_decay,
                surface_points=surface_data
            )
            
            logger.info(f"Volatility opportunity detected: {symbol} IV={implied_vol:.3f} RV={realized_vol:.3f}")
            return opportunity
            
        except Exception as e:
            logger.error(f"Error detecting volatility opportunity: {e}")
            return None
    
    def _get_atm_options(self, surface_data: List[VolatilitySurface], spot_price: float) -> List[VolatilitySurface]:
        """Get at-the-money options from surface data
        
        Args:
            surface_data: Volatility surface data
            spot_price: Current spot price
            
        Returns:
            List of ATM options
        """
        try:
            # Find options closest to ATM
            atm_options = []
            
            for option in surface_data:
                # Consider ATM if strike is within 5% of spot
                moneyness = option.strike / spot_price
                if 0.95 <= moneyness <= 1.05:
                    atm_options.append(option)
            
            # If no ATM options, get closest ones
            if not atm_options:
                surface_data.sort(key=lambda x: abs(x.strike - spot_price))
                atm_options = surface_data[:2]  # Take 2 closest
            
            return atm_options
            
        except Exception as e:
            logger.error(f"Error getting ATM options: {e}")
            return []
    
    def _calculate_vol_confidence(self, implied_vol: float, realized_vol: float, forecast_vol: float) -> float:
        """Calculate confidence in volatility opportunity
        
        Args:
            implied_vol: Implied volatility
            realized_vol: Realized volatility
            forecast_vol: Forecast volatility
            
        Returns:
            Confidence score (0-1)
        """
        try:
            # Base confidence on spread size
            spread_magnitude = abs(implied_vol - realized_vol) / realized_vol
            base_confidence = min(spread_magnitude / 0.2, 1.0)  # Normalize to 20% spread
            
            # Adjust based on forecast alignment
            if forecast_vol > 0:
                forecast_alignment = 1 - abs(forecast_vol - realized_vol) / max(forecast_vol, realized_vol)
                confidence = base_confidence * max(forecast_alignment, 0.5)
            else:
                confidence = base_confidence * 0.7  # Reduce confidence without forecast
            
            return max(min(confidence, 1.0), 0.0)
            
        except Exception as e:
            logger.error(f"Error calculating volatility confidence: {e}")
            return 0.5
    
    def _calculate_vol_risk_score(self, underlying_data: MarketData, surface_data: List[VolatilitySurface]) -> float:
        """Calculate risk score for volatility opportunity
        
        Args:
            underlying_data: Underlying market data
            surface_data: Volatility surface data
            
        Returns:
            Risk score (0-1, higher is riskier)
        """
        try:
            risk_factors = []
            
            # Liquidity risk (based on options volume)
            total_volume = sum(opt.volume for opt in surface_data)
            avg_volume = total_volume / len(surface_data) if surface_data else 0
            volume_risk = max(0, 1 - (avg_volume / 1000))  # Normalize to 1000 contracts
            risk_factors.append(volume_risk)
            
            # Bid-ask spread risk
            spreads = [(opt.ask - opt.bid) / opt.price for opt in surface_data 
                      if opt.price > 0 and opt.ask > opt.bid]
            if spreads:
                avg_spread = np.mean(spreads)
                spread_risk = min(avg_spread / 0.1, 1.0)  # Normalize to 10% spread
                risk_factors.append(spread_risk)
            
            # Time decay risk (higher for shorter expiries)
            times_to_expiry = [opt.time_to_expiry for opt in surface_data if opt.time_to_expiry > 0]
            if times_to_expiry:
                avg_time = np.mean(times_to_expiry)
                time_risk = max(0, 1 - (avg_time / 0.25))  # Normalize to 3 months
                risk_factors.append(time_risk)
            
            # Calculate overall risk score
            if risk_factors:
                risk_score = np.mean(risk_factors)
            else:
                risk_score = 0.5  # Default moderate risk
            
            return max(min(risk_score, 1.0), 0.0)
            
        except Exception as e:
            logger.error(f"Error calculating volatility risk score: {e}")
            return 0.5
    
    def _calculate_expected_return(self, vol_spread: float, implied_vol: float) -> float:
        """Calculate expected return from volatility arbitrage
        
        Args:
            vol_spread: Volatility spread (IV - RV)
            implied_vol: Implied volatility
            
        Returns:
            Expected return percentage
        """
        try:
            # Simple approximation: return proportional to vol spread
            if implied_vol > 0:
                return (vol_spread / implied_vol) * 100 * 0.5  # 50% capture rate
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating expected return: {e}")
            return 0.0
    
    def _calculate_hedge_ratio(self, options: List[VolatilitySurface]) -> float:
        """Calculate optimal hedge ratio
        
        Args:
            options: List of options for hedging
            
        Returns:
            Hedge ratio
        """
        try:
            if not options:
                return self.hedge_ratio
            
            # Use average delta for hedge ratio calculation
            deltas = [abs(opt.delta) for opt in options if opt.delta != 0]
            
            if deltas:
                avg_delta = np.mean(deltas)
                # Adjust hedge ratio based on delta
                hedge_ratio = min(avg_delta * self.hedge_ratio, 1.0)
            else:
                hedge_ratio = self.hedge_ratio
            
            return hedge_ratio
            
        except Exception as e:
            logger.error(f"Error calculating hedge ratio: {e}")
            return self.hedge_ratio

class VolatilityArbitrageStrategy(BaseStrategy):
    """Base volatility arbitrage strategy"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # Strategy-specific parameters
        params = config.parameters
        self.arbitrage_type = VolatilityArbitrageType(params.get('arbitrage_type', 'implied_realized'))
        self.min_vol_spread = params.get('min_vol_spread', 0.05)
        self.max_position_size = params.get('max_position_size', 0.05)
        self.hedge_ratio = params.get('hedge_ratio', 0.8)
        
        # Initialize analyzer
        analyzer_config = {
            'min_vol_spread': self.min_vol_spread,
            'lookback_period': params.get('lookback_period', 30),
            'hedge_ratio': self.hedge_ratio,
            'risk_free_rate': params.get('risk_free_rate', 0.02)
        }
        self.analyzer = VolatilityAnalyzer(analyzer_config)
        
        # Current opportunities
        self.current_opportunities: Dict[str, VolatilityOpportunity] = {}
        
        # Options surface data (to be updated externally)
        self.surface_data: Dict[str, List[VolatilitySurface]] = {}
        
        logger.info(f"VolatilityArbitrageStrategy initialized: {self.arbitrage_type.value}")
    
    def update_surface_data(self, symbol: str, surface: List[VolatilitySurface]) -> None:
        """Update volatility surface data
        
        Args:
            symbol: Underlying symbol
            surface: Volatility surface data
        """
        self.surface_data[symbol] = surface
        logger.debug(f"Updated surface data for {symbol}: {len(surface)} points")
    
    def generate_signals(self, market_data: Dict[str, MarketData]) -> List[Signal]:
        """Generate volatility arbitrage signals
        
        Args:
            market_data: Dictionary of market data by symbol
            
        Returns:
            List of generated signals
        """
        signals = []
        
        try:
            # Process each symbol with surface data
            for symbol in self.config.symbols:
                if symbol not in market_data or symbol not in self.surface_data:
                    continue
                
                underlying_data = market_data[symbol]
                surface = self.surface_data[symbol]
                
                # Detect volatility opportunity
                opportunity = self.analyzer.detect_volatility_opportunity(
                    underlying_data, surface, self.arbitrage_type
                )
                
                if opportunity and abs(opportunity.vol_spread) >= self.min_vol_spread:
                    # Store opportunity
                    self.current_opportunities[symbol] = opportunity
                    
                    # Generate signal
                    signal = self._create_volatility_signal(opportunity)
                    if signal:
                        signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating volatility signals: {e}")
            return []
    
    def _create_volatility_signal(self, opportunity: VolatilityOpportunity) -> Optional[Signal]:
        """Create signal from volatility opportunity
        
        Args:
            opportunity: Detected volatility opportunity
            
        Returns:
            Generated signal or None
        """
        try:
            # Determine signal direction based on vol spread
            if opportunity.vol_spread > 0:  # IV > RV, sell volatility
                signal_type = 'SELL_VOLATILITY'
            else:  # IV < RV, buy volatility
                signal_type = 'BUY_VOLATILITY'
            
            # Calculate position size
            base_size = min(abs(opportunity.vol_spread_pct) / 100, self.max_position_size)
            risk_adjusted_size = base_size * (1 - opportunity.risk_score)
            confidence_adjusted_size = risk_adjusted_size * opportunity.confidence
            
            position_size = max(confidence_adjusted_size, 0.01)  # Minimum 1%
            
            signal = Signal(
                timestamp=opportunity.timestamp,
                symbol=opportunity.underlying_symbol,
                signal_type=signal_type,
                strength=opportunity.confidence,
                confidence=opportunity.confidence,
                expected_return=opportunity.expected_return / 100,
                risk_score=opportunity.risk_score,
                position_size=position_size,
                metadata={
                    'strategy': 'volatility_arbitrage',
                    'arbitrage_type': self.arbitrage_type.value,
                    'implied_vol': opportunity.implied_vol,
                    'realized_vol': opportunity.realized_vol,
                    'forecast_vol': opportunity.forecast_vol,
                    'vol_spread': opportunity.vol_spread,
                    'vol_spread_pct': opportunity.vol_spread_pct,
                    'hedge_ratio': opportunity.hedge_ratio,
                    'position_delta': opportunity.position_delta,
                    'vega_exposure': opportunity.vega_exposure,
                    'theta_decay': opportunity.theta_decay
                }
            )
            
            logger.info(f"Generated volatility signal: {signal_type} {opportunity.underlying_symbol} "
                       f"size={position_size:.3f} spread={opportunity.vol_spread:.3f}")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error creating volatility signal: {e}")
            return None
    
    def update_market_data(self, market_data: MarketData) -> None:
        """Update strategy with new market data
        
        Args:
            market_data: New market data
        """
        try:
            # Store price history for volatility calculation
            if market_data.symbol not in self.analyzer.price_history:
                self.analyzer.price_history[market_data.symbol] = pd.Series(dtype=float)
            
            self.analyzer.price_history[market_data.symbol][market_data.timestamp] = market_data.close
            
            # Keep only recent history
            max_history = 252  # 1 year of daily data
            if len(self.analyzer.price_history[market_data.symbol]) > max_history:
                self.analyzer.price_history[market_data.symbol] = \
                    self.analyzer.price_history[market_data.symbol].tail(max_history)
            
        except Exception as e:
            logger.error(f"Error updating market data: {e}")

class ImpliedRealizedArbitrageStrategy(VolatilityArbitrageStrategy):
    """Implied vs Realized volatility arbitrage strategy"""
    
    def __init__(self, config: StrategyConfig):
        # Set specific arbitrage type
        config.parameters['arbitrage_type'] = 'implied_realized'
        super().__init__(config)
        
        # IV-RV specific parameters
        params = config.parameters
        self.vol_forecast_weight = params.get('vol_forecast_weight', 0.3)
        self.mean_reversion_factor = params.get('mean_reversion_factor', 0.1)
        
        logger.info("ImpliedRealizedArbitrageStrategy initialized")

class VolatilitySurfaceArbitrageStrategy(VolatilityArbitrageStrategy):
    """Volatility surface arbitrage strategy"""
    
    def __init__(self, config: StrategyConfig):
        # Set specific arbitrage type
        config.parameters['arbitrage_type'] = 'volatility_surface'
        super().__init__(config)
        
        # Surface-specific parameters
        params = config.parameters
        self.skew_threshold = params.get('skew_threshold', 0.1)
        self.term_structure_threshold = params.get('term_structure_threshold', 0.05)
        
        logger.info("VolatilitySurfaceArbitrageStrategy initialized")

# Utility functions
def calculate_implied_volatility(
    option_price: float,
    spot_price: float,
    strike: float,
    time_to_expiry: float,
    risk_free_rate: float = 0.02,
    option_type: str = 'call'
) -> float:
    """Calculate Black-Scholes implied volatility
    
    Args:
        option_price: Market price of option
        spot_price: Current spot price
        strike: Strike price
        time_to_expiry: Time to expiry in years
        risk_free_rate: Risk-free rate
        option_type: 'call' or 'put'
        
    Returns:
        Implied volatility
    """
    analyzer = VolatilityAnalyzer({})
    return analyzer.black_scholes_implied_vol(
        option_price, spot_price, strike, time_to_expiry, risk_free_rate, option_type
    )

def calculate_realized_volatility(prices: pd.Series, window: int = 30) -> float:
    """Calculate realized volatility from price series
    
    Args:
        prices: Price series
        window: Lookback window
        
    Returns:
        Annualized realized volatility
    """
    analyzer = VolatilityAnalyzer({})
    return analyzer.calculate_realized_volatility(prices, window)

def detect_volatility_mispricing(
    implied_vol: float,
    realized_vol: float,
    threshold: float = 0.05
) -> Optional[float]:
    """Detect volatility mispricing
    
    Args:
        implied_vol: Implied volatility
        realized_vol: Realized volatility
        threshold: Minimum threshold for mispricing
        
    Returns:
        Volatility spread if mispricing detected, None otherwise
    """
    try:
        if realized_vol <= 0:
            return None
        
        vol_spread = implied_vol - realized_vol
        
        if abs(vol_spread) >= threshold:
            return vol_spread
        
        return None
        
    except Exception as e:
        logger.error(f"Error detecting volatility mispricing: {e}")
        return None