"""Index Arbitrage Strategies

This module implements index arbitrage strategies that exploit price discrepancies
between index ETFs and their underlying baskets of securities.

Key Features:
- ETF vs basket arbitrage detection
- Real-time tracking error monitoring
- Basket construction and replication
- Transaction cost analysis
- Risk-adjusted arbitrage opportunities
- Multi-timeframe arbitrage analysis

Strategies:
- IndexArbitrageStrategy: Base index arbitrage implementation
- ETFArbitrageStrategy: ETF-specific arbitrage strategies
- BasketArbitrageStrategy: Custom basket arbitrage

Architecture:
- Follows 5-Pillar Architecture principles
- Integrates with core trading components
- Event-driven signal generation
- Real-time market data processing
"""

import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Union

# Core imports
from ...core.data_types import MarketData, Signal, Position
from ...core.events import SignalEvent, OrderEvent
from ...core.risk_management import RiskManager
from ...core.portfolio_management import PortfolioManager
from ...core.signal_generator import SignalGenerator
from ..base_strategy import BaseStrategy, StrategyConfig
from ...utils.technical_indicators import (
    calculate_sma, calculate_ema, calculate_atr,
    calculate_bollinger_bands, calculate_correlation
)
from ...utils.market_utils import (
    calculate_returns, calculate_volatility,
    normalize_prices, validate_market_data
)

# Configure logging
logger = logging.getLogger(__name__)

class IndexArbitrageType(Enum):
    """Types of index arbitrage strategies"""
    ETF_BASKET = "etf_basket"              # ETF vs underlying basket
    INDEX_FUTURES = "index_futures"        # Index futures vs spot
    CROSS_LISTING = "cross_listing"        # Same asset different exchanges
    SECTOR_ROTATION = "sector_rotation"    # Sector ETF arbitrage
    CURRENCY_HEDGED = "currency_hedged"    # Currency hedged ETF arbitrage

@dataclass
class BasketComponent:
    """Represents a component of an index basket"""
    symbol: str
    weight: float
    shares: int = 0
    price: float = 0.0
    market_value: float = 0.0
    
    def __post_init__(self):
        """Calculate market value after initialization"""
        self.market_value = self.shares * self.price

@dataclass
class ArbitrageOpportunity:
    """Represents an arbitrage opportunity"""
    timestamp: datetime
    etf_symbol: str
    etf_price: float
    basket_value: float
    spread: float
    spread_pct: float
    tracking_error: float
    confidence: float
    expected_return: float
    risk_score: float
    transaction_costs: float
    net_opportunity: float
    components: List[BasketComponent] = field(default_factory=list)
    
    def __post_init__(self):
        """Calculate derived metrics"""
        self.spread = self.etf_price - self.basket_value
        self.spread_pct = (self.spread / self.basket_value) * 100 if self.basket_value > 0 else 0
        self.net_opportunity = abs(self.spread_pct) - self.transaction_costs

class IndexArbitrageAnalyzer:
    """Analyzes index arbitrage opportunities"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.min_arbitrage_threshold = config.get('min_arbitrage_threshold', 0.005)
        self.max_tracking_error = config.get('max_tracking_error', 0.02)
        self.transaction_costs = config.get('transaction_costs', 0.001)
        self.lookback_period = config.get('lookback_period', 20)
        
        # Historical data storage
        self.price_history: Dict[str, pd.Series] = {}
        self.spread_history: pd.Series = pd.Series(dtype=float)
        self.tracking_errors: pd.Series = pd.Series(dtype=float)
        
        logger.info("IndexArbitrageAnalyzer initialized")
    
    def update_basket_weights(self, symbol: str, weights: Dict[str, float]) -> None:
        """Update basket composition weights
        
        Args:
            symbol: ETF symbol
            weights: Dictionary of component weights
        """
        try:
            self.basket_weights = weights
            logger.debug(f"Updated basket weights for {symbol}: {len(weights)} components")
        except Exception as e:
            logger.error(f"Error updating basket weights: {e}")
    
    def calculate_basket_nav(self, prices: Dict[str, float], weights: Dict[str, float]) -> float:
        """Calculate net asset value of basket
        
        Args:
            prices: Current prices of basket components
            weights: Weights of basket components
            
        Returns:
            Calculated NAV
        """
        try:
            nav = 0.0
            total_weight = 0.0
            
            for symbol, weight in weights.items():
                if symbol in prices:
                    nav += prices[symbol] * weight
                    total_weight += weight
            
            # Normalize if weights don't sum to 1
            if total_weight > 0 and abs(total_weight - 1.0) > 0.01:
                nav = nav / total_weight
            
            return nav
            
        except Exception as e:
            logger.error(f"Error calculating basket NAV: {e}")
            return 0.0
    
    def detect_arbitrage_opportunity(
        self,
        etf_data: MarketData,
        basket_prices: Dict[str, float],
        basket_weights: Dict[str, float]
    ) -> Optional[ArbitrageOpportunity]:
        """Detect arbitrage opportunities
        
        Args:
            etf_data: ETF market data
            basket_prices: Prices of basket components
            basket_weights: Weights of basket components
            
        Returns:
            ArbitrageOpportunity if found, None otherwise
        """
        try:
            # Calculate basket NAV
            basket_nav = self.calculate_basket_nav(basket_prices, basket_weights)
            
            if basket_nav <= 0:
                return None
            
            # Calculate spread
            etf_price = etf_data.close
            spread = etf_price - basket_nav
            spread_pct = (spread / basket_nav) * 100
            
            # Check if opportunity meets threshold
            if abs(spread_pct) < self.min_arbitrage_threshold * 100:
                return None
            
            # Calculate tracking error
            tracking_error = self.calculate_tracking_error(etf_data.symbol, basket_nav)
            
            # Skip if tracking error too high
            if tracking_error > self.max_tracking_error:
                return None
            
            # Calculate confidence and risk metrics
            confidence = self.calculate_confidence(spread_pct, tracking_error)
            risk_score = self.calculate_risk_score(etf_data, basket_prices)
            expected_return = abs(spread_pct) - self.transaction_costs * 100
            
            # Create basket components
            components = [
                BasketComponent(
                    symbol=symbol,
                    weight=weight,
                    price=basket_prices.get(symbol, 0.0)
                )
                for symbol, weight in basket_weights.items()
                if symbol in basket_prices
            ]
            
            opportunity = ArbitrageOpportunity(
                timestamp=etf_data.timestamp,
                etf_symbol=etf_data.symbol,
                etf_price=etf_price,
                basket_value=basket_nav,
                spread=spread,
                spread_pct=spread_pct,
                tracking_error=tracking_error,
                confidence=confidence,
                expected_return=expected_return,
                risk_score=risk_score,
                transaction_costs=self.transaction_costs * 100,
                net_opportunity=expected_return,
                components=components
            )
            
            # Store historical data
            self.spread_history[etf_data.timestamp] = spread_pct
            self.tracking_errors[etf_data.timestamp] = tracking_error
            
            logger.info(f"Arbitrage opportunity detected: {etf_data.symbol} spread {spread_pct:.3f}%")
            return opportunity
            
        except Exception as e:
            logger.error(f"Error detecting arbitrage opportunity: {e}")
            return None
    
    def calculate_tracking_error(self, etf_symbol: str, basket_nav: float) -> float:
        """Calculate tracking error between ETF and basket
        
        Args:
            etf_symbol: ETF symbol
            basket_nav: Current basket NAV
            
        Returns:
            Tracking error (standard deviation of return differences)
        """
        try:
            if etf_symbol not in self.price_history:
                return 0.0
            
            etf_prices = self.price_history[etf_symbol]
            
            if len(etf_prices) < 2:
                return 0.0
            
            # Calculate returns
            etf_returns = etf_prices.pct_change().dropna()
            
            # For simplicity, use recent volatility as proxy for tracking error
            if len(etf_returns) >= self.lookback_period:
                recent_returns = etf_returns.tail(self.lookback_period)
                tracking_error = recent_returns.std() * np.sqrt(252)  # Annualized
            else:
                tracking_error = etf_returns.std() * np.sqrt(252) if len(etf_returns) > 1 else 0.0
            
            return tracking_error
            
        except Exception as e:
            logger.error(f"Error calculating tracking error: {e}")
            return 0.0
    
    def calculate_confidence(self, spread_pct: float, tracking_error: float) -> float:
        """Calculate confidence in arbitrage opportunity
        
        Args:
            spread_pct: Spread percentage
            tracking_error: Tracking error
            
        Returns:
            Confidence score (0-1)
        """
        try:
            # Base confidence on spread size relative to tracking error
            if tracking_error > 0:
                confidence = min(abs(spread_pct) / (tracking_error * 100), 1.0)
            else:
                confidence = min(abs(spread_pct) / 0.5, 1.0)  # Default threshold
            
            # Adjust for historical spread persistence
            if len(self.spread_history) > 5:
                recent_spreads = self.spread_history.tail(5)
                spread_consistency = 1.0 - (recent_spreads.std() / (abs(recent_spreads.mean()) + 0.01))
                confidence *= max(spread_consistency, 0.1)
            
            return max(min(confidence, 1.0), 0.0)
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.5
    
    def calculate_risk_score(self, etf_data: MarketData, basket_prices: Dict[str, float]) -> float:
        """Calculate risk score for arbitrage opportunity
        
        Args:
            etf_data: ETF market data
            basket_prices: Basket component prices
            
        Returns:
            Risk score (0-1, higher is riskier)
        """
        try:
            risk_factors = []
            
            # Volume risk (low volume = higher risk)
            if hasattr(etf_data, 'volume') and etf_data.volume > 0:
                # Normalize volume (assuming average volume of 1M shares)
                volume_risk = max(0, 1 - (etf_data.volume / 1000000))
                risk_factors.append(volume_risk)
            
            # Volatility risk
            if etf_data.symbol in self.price_history:
                prices = self.price_history[etf_data.symbol]
                if len(prices) >= 10:
                    returns = prices.pct_change().dropna()
                    volatility = returns.std() * np.sqrt(252)
                    vol_risk = min(volatility / 0.3, 1.0)  # Normalize to 30% annual vol
                    risk_factors.append(vol_risk)
            
            # Basket completeness risk
            available_components = len([p for p in basket_prices.values() if p > 0])
            total_components = len(basket_prices)
            completeness_risk = 1 - (available_components / total_components) if total_components > 0 else 1.0
            risk_factors.append(completeness_risk)
            
            # Calculate overall risk score
            if risk_factors:
                risk_score = np.mean(risk_factors)
            else:
                risk_score = 0.5  # Default moderate risk
            
            return max(min(risk_score, 1.0), 0.0)
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {e}")
            return 0.5

class IndexArbitrageStrategy(BaseStrategy):
    """Base index arbitrage strategy"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # Strategy-specific parameters
        params = config.parameters
        self.arbitrage_type = IndexArbitrageType(params.get('arbitrage_type', 'etf_basket'))
        self.min_arbitrage_threshold = params.get('min_arbitrage_threshold', 0.005)
        self.max_position_size = params.get('max_position_size', 0.1)
        self.rebalance_frequency = params.get('rebalance_frequency', '1H')
        
        # Initialize analyzer
        analyzer_config = {
            'min_arbitrage_threshold': self.min_arbitrage_threshold,
            'max_tracking_error': params.get('max_tracking_error', 0.02),
            'transaction_costs': params.get('transaction_costs', 0.001),
            'lookback_period': params.get('lookback_period', 20)
        }
        self.analyzer = IndexArbitrageAnalyzer(analyzer_config)
        
        # Basket weights (to be set externally)
        self.basket_weights: Dict[str, Dict[str, float]] = {}
        
        # Current opportunities
        self.current_opportunities: Dict[str, ArbitrageOpportunity] = {}
        
        logger.info(f"IndexArbitrageStrategy initialized: {self.arbitrage_type.value}")
    
    def set_basket_weights(self, etf_symbol: str, weights: Dict[str, float]) -> None:
        """Set basket weights for an ETF
        
        Args:
            etf_symbol: ETF symbol
            weights: Component weights
        """
        self.basket_weights[etf_symbol] = weights
        self.analyzer.update_basket_weights(etf_symbol, weights)
        logger.info(f"Set basket weights for {etf_symbol}: {len(weights)} components")
    
    def generate_signals(self, market_data: Dict[str, MarketData]) -> List[Signal]:
        """Generate arbitrage signals
        
        Args:
            market_data: Dictionary of market data by symbol
            
        Returns:
            List of generated signals
        """
        signals = []
        
        try:
            # Process each ETF with defined basket weights
            for etf_symbol, weights in self.basket_weights.items():
                if etf_symbol not in market_data:
                    continue
                
                etf_data = market_data[etf_symbol]
                
                # Get basket component prices
                basket_prices = {}
                for component in weights.keys():
                    if component in market_data:
                        basket_prices[component] = market_data[component].close
                
                # Skip if insufficient basket data
                if len(basket_prices) < len(weights) * 0.8:  # Need at least 80% of components
                    continue
                
                # Detect arbitrage opportunity
                opportunity = self.analyzer.detect_arbitrage_opportunity(
                    etf_data, basket_prices, weights
                )
                
                if opportunity and opportunity.net_opportunity > 0:
                    # Store opportunity
                    self.current_opportunities[etf_symbol] = opportunity
                    
                    # Generate signal
                    signal = self._create_arbitrage_signal(opportunity)
                    if signal:
                        signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating arbitrage signals: {e}")
            return []
    
    def _create_arbitrage_signal(self, opportunity: ArbitrageOpportunity) -> Optional[Signal]:
        """Create signal from arbitrage opportunity
        
        Args:
            opportunity: Detected arbitrage opportunity
            
        Returns:
            Generated signal or None
        """
        try:
            # Determine signal direction
            if opportunity.spread > 0:  # ETF overpriced
                signal_type = 'SELL'  # Sell ETF, buy basket
            else:  # ETF underpriced
                signal_type = 'BUY'   # Buy ETF, sell basket
            
            # Calculate position size based on opportunity size and risk
            base_size = min(opportunity.net_opportunity / 100, self.max_position_size)
            risk_adjusted_size = base_size * (1 - opportunity.risk_score)
            confidence_adjusted_size = risk_adjusted_size * opportunity.confidence
            
            position_size = max(confidence_adjusted_size, 0.01)  # Minimum 1%
            
            signal = Signal(
                timestamp=opportunity.timestamp,
                symbol=opportunity.etf_symbol,
                signal_type=signal_type,
                strength=opportunity.confidence,
                confidence=opportunity.confidence,
                expected_return=opportunity.expected_return / 100,
                risk_score=opportunity.risk_score,
                position_size=position_size,
                metadata={
                    'strategy': 'index_arbitrage',
                    'arbitrage_type': self.arbitrage_type.value,
                    'spread_pct': opportunity.spread_pct,
                    'tracking_error': opportunity.tracking_error,
                    'basket_value': opportunity.basket_value,
                    'transaction_costs': opportunity.transaction_costs,
                    'net_opportunity': opportunity.net_opportunity,
                    'components': len(opportunity.components)
                }
            )
            
            logger.info(f"Generated arbitrage signal: {signal_type} {opportunity.etf_symbol} "
                       f"size={position_size:.3f} spread={opportunity.spread_pct:.3f}%")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error creating arbitrage signal: {e}")
            return None
    
    def update_market_data(self, market_data: MarketData) -> None:
        """Update strategy with new market data
        
        Args:
            market_data: New market data
        """
        try:
            # Store price history for tracking error calculation
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

class ETFArbitrageStrategy(IndexArbitrageStrategy):
    """ETF-specific arbitrage strategy"""
    
    def __init__(self, config: StrategyConfig):
        # Set ETF-specific arbitrage type
        config.parameters['arbitrage_type'] = 'etf_basket'
        super().__init__(config)
        
        # ETF-specific parameters
        params = config.parameters
        self.creation_unit_size = params.get('creation_unit_size', 50000)
        self.authorized_participant = params.get('authorized_participant', False)
        
        logger.info("ETFArbitrageStrategy initialized")

class BasketArbitrageStrategy(IndexArbitrageStrategy):
    """Custom basket arbitrage strategy"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # Basket-specific parameters
        params = config.parameters
        self.custom_baskets = params.get('custom_baskets', {})
        self.rebalance_threshold = params.get('rebalance_threshold', 0.05)
        
        logger.info("BasketArbitrageStrategy initialized")
    
    def add_custom_basket(self, basket_name: str, components: Dict[str, float]) -> None:
        """Add a custom basket definition
        
        Args:
            basket_name: Name of the basket
            components: Dictionary of component symbols and weights
        """
        self.custom_baskets[basket_name] = components
        self.set_basket_weights(basket_name, components)
        logger.info(f"Added custom basket {basket_name} with {len(components)} components")

# Utility functions
def calculate_tracking_error(etf_prices: pd.Series, basket_values: pd.Series) -> float:
    """Calculate tracking error between ETF and basket
    
    Args:
        etf_prices: ETF price series
        basket_values: Basket value series
        
    Returns:
        Annualized tracking error
    """
    try:
        if len(etf_prices) != len(basket_values) or len(etf_prices) < 2:
            return 0.0
        
        etf_returns = etf_prices.pct_change().dropna()
        basket_returns = basket_values.pct_change().dropna()
        
        if len(etf_returns) != len(basket_returns) or len(etf_returns) < 2:
            return 0.0
        
        return_diff = etf_returns - basket_returns
        tracking_error = return_diff.std() * np.sqrt(252)
        
        return tracking_error
        
    except Exception as e:
        logger.error(f"Error calculating tracking error: {e}")
        return 0.0

def detect_arbitrage_opportunity(
    etf_price: float,
    basket_value: float,
    threshold: float = 0.005
) -> Optional[float]:
    """Detect arbitrage opportunity
    
    Args:
        etf_price: Current ETF price
        basket_value: Current basket value
        threshold: Minimum threshold for opportunity
        
    Returns:
        Spread percentage if opportunity exists, None otherwise
    """
    try:
        if basket_value <= 0:
            return None
        
        spread_pct = ((etf_price - basket_value) / basket_value) * 100
        
        if abs(spread_pct) >= threshold * 100:
            return spread_pct
        
        return None
        
    except Exception as e:
        logger.error(f"Error detecting arbitrage opportunity: {e}")
        return None

def calculate_basket_value(prices: Dict[str, float], weights: Dict[str, float]) -> float:
    """Calculate basket value from component prices and weights
    
    Args:
        prices: Component prices
        weights: Component weights
        
    Returns:
        Calculated basket value
    """
    try:
        value = 0.0
        total_weight = 0.0
        
        for symbol, weight in weights.items():
            if symbol in prices and prices[symbol] > 0:
                value += prices[symbol] * weight
                total_weight += weight
        
        # Normalize if weights don't sum to 1
        if total_weight > 0 and abs(total_weight - 1.0) > 0.01:
            value = value / total_weight
        
        return value
        
    except Exception as e:
        logger.error(f"Error calculating basket value: {e}")
        return 0.0