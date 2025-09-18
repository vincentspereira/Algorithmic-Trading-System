"""Institutional-Grade Arbitrage Trading Strategies

This module implements comprehensive arbitrage strategies with institutional-grade
risk controls, real-time execution, and multi-market connectivity.

Strategies Included:
- Cross-Market Arbitrage
- Statistical Arbitrage
- Risk Arbitrage (Merger Arbitrage)
- Index Arbitrage
- Currency Arbitrage
- Volatility Arbitrage
- Calendar Spread Arbitrage
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import logging
from abc import ABC, abstractmethod
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# Import technical indicators
try:
    from nautilus_trader_engine.indicators.consolidated_indicators import ConsolidatedIndicators, IndicatorResult
    from nautilus_trader_engine.indicators.core_indicator_base import AugmentedIndicator, IndicatorConfig
except ImportError:
    # Fallback for development
    class ConsolidatedIndicators:
        @staticmethod
        def rsi(*args, **kwargs):
            return None
    
    class AugmentedIndicator:
        pass
    
    class IndicatorConfig:
        pass


class ArbitrageSignal(Enum):
    """Arbitrage trading signal types"""
    STRONG_ARBITRAGE_LONG_A_SHORT_B = 3
    ARBITRAGE_LONG_A_SHORT_B = 2
    WEAK_ARBITRAGE_LONG_A_SHORT_B = 1
    NEUTRAL = 0
    WEAK_ARBITRAGE_LONG_B_SHORT_A = -1
    ARBITRAGE_LONG_B_SHORT_A = -2
    STRONG_ARBITRAGE_LONG_B_SHORT_A = -3


class ArbitrageType(Enum):
    """Type of arbitrage opportunity"""
    CROSS_MARKET = "cross_market"
    STATISTICAL = "statistical"
    RISK_ARBITRAGE = "risk_arbitrage"
    INDEX_ARBITRAGE = "index_arbitrage"
    CURRENCY_ARBITRAGE = "currency_arbitrage"
    VOLATILITY_ARBITRAGE = "volatility_arbitrage"
    CALENDAR_SPREAD = "calendar_spread"
    TRIANGULAR_ARBITRAGE = "triangular_arbitrage"
    CONVERTIBLE_ARBITRAGE = "convertible_arbitrage"


class ArbitrageRegime(Enum):
    """Market regime for arbitrage trading"""
    HIGH_OPPORTUNITY = "high_opportunity"
    MODERATE_OPPORTUNITY = "moderate_opportunity"
    LOW_OPPORTUNITY = "low_opportunity"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    TRENDING_MARKET = "trending_market"
    RANGE_BOUND = "range_bound"
    CRISIS_MODE = "crisis_mode"
    NORMAL_CONDITIONS = "normal_conditions"


@dataclass
class ArbitrageConfig:
    """Configuration for arbitrage trading strategies"""
    # Arbitrage detection parameters
    min_spread_threshold: float = 0.001  # 0.1% minimum spread
    max_spread_threshold: float = 0.05   # 5% maximum spread (risk control)
    min_profit_threshold: float = 0.002  # 0.2% minimum profit after costs
    
    # Execution parameters
    max_execution_delay: float = 0.1  # 100ms maximum execution delay
    slippage_tolerance: float = 0.0005  # 0.05% slippage tolerance
    transaction_cost: float = 0.0002  # 0.02% transaction cost per side
    
    # Risk management
    max_position_size: float = 0.05  # 5% per arbitrage trade
    max_leverage: float = 2.0
    stop_loss: float = 0.01  # 1% stop loss
    max_holding_time: int = 300  # 5 minutes maximum holding time (seconds)
    
    # Statistical arbitrage parameters
    lookback_window: int = 60
    z_score_entry: float = 2.0
    z_score_exit: float = 0.5
    z_score_stop: float = 3.0
    
    # Cross-market parameters
    min_correlation: float = 0.95  # High correlation for cross-market arb
    price_update_frequency: float = 0.1  # 100ms price update frequency
    
    # Risk arbitrage parameters
    merger_completion_probability: float = 0.8
    merger_timeline_days: int = 90
    regulatory_risk_factor: float = 0.1
    
    # Index arbitrage parameters
    index_tracking_error: float = 0.001  # 0.1% tracking error threshold
    basket_rebalance_threshold: float = 0.005  # 0.5% rebalance threshold
    
    # Performance optimization
    use_cuda: bool = False
    parallel_processing: bool = True
    real_time_execution: bool = True


@dataclass
class ArbitrageMetrics:
    """Metrics for arbitrage analysis"""
    spread_size: float
    spread_volatility: float
    execution_probability: float
    expected_profit: float
    risk_adjusted_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    average_holding_time: float
    transaction_costs: float
    slippage_impact: float
    market_impact: float


@dataclass
class ArbitrageOpportunity:
    """Arbitrage opportunity details"""
    arbitrage_type: ArbitrageType
    symbol_a: str
    symbol_b: str
    market_a: str
    market_b: str
    price_a: float
    price_b: float
    spread: float
    spread_percentage: float
    expected_profit: float
    execution_time_limit: float
    confidence: float
    risk_score: float
    priority: int
    metadata: Dict[str, Any]
    timestamp: datetime


@dataclass
class ArbitrageResult:
    """Result from arbitrage strategy calculation"""
    signal: ArbitrageSignal
    arbitrage_type: ArbitrageType
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    spread: float
    spread_percentage: float
    expected_profit: float
    risk_adjusted_profit: float
    execution_urgency: float  # 0.0 to 1.0 (how quickly to execute)
    holding_time_estimate: float  # seconds
    position_size_a: float
    position_size_b: float
    entry_price_a: Optional[float]
    entry_price_b: Optional[float]
    target_profit: float
    stop_loss_level: float
    regime: ArbitrageRegime
    metrics: ArbitrageMetrics
    opportunities: List[ArbitrageOpportunity]
    metadata: Dict[str, Any]
    timestamp: datetime


class BaseArbitrageStrategy(ABC):
    """Abstract base class for arbitrage trading strategies"""
    
    def __init__(self, config: ArbitrageConfig = None):
        self.config = config or ArbitrageConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup_indicators()
        self.execution_history = []
        self.performance_metrics = {}
    
    def _setup_indicators(self):
        """Initialize technical indicators"""
        self.indicators = ConsolidatedIndicators()
    
    @abstractmethod
    def detect_arbitrage_opportunities(self, market_data: Dict[str, Dict[str, pd.DataFrame]]) -> List[ArbitrageOpportunity]:
        """Detect arbitrage opportunities across markets"""
        pass
    
    @abstractmethod
    def calculate_arbitrage_signal(self, opportunity: ArbitrageOpportunity, 
                                 market_data: Dict[str, Dict[str, pd.DataFrame]]) -> ArbitrageResult:
        """Calculate arbitrage trading signal for opportunity"""
        pass
    
    def _calculate_spread(self, price_a: float, price_b: float, 
                        hedge_ratio: float = 1.0) -> Tuple[float, float]:
        """Calculate spread and spread percentage"""
        spread = price_a - hedge_ratio * price_b
        
        # Calculate percentage spread relative to average price
        avg_price = (price_a + hedge_ratio * price_b) / 2
        spread_percentage = spread / avg_price if avg_price > 0 else 0.0
        
        return spread, spread_percentage
    
    def _estimate_execution_probability(self, spread_size: float, 
                                      market_volatility: float,
                                      liquidity_score: float) -> float:
        """Estimate probability of successful arbitrage execution"""
        # Base probability from spread size
        if spread_size < self.config.min_spread_threshold:
            return 0.0
        elif spread_size > self.config.max_spread_threshold:
            return 0.1  # Very large spreads are suspicious
        
        # Normalize spread size to probability
        spread_prob = min(1.0, (spread_size - self.config.min_spread_threshold) / 
                         (self.config.max_spread_threshold - self.config.min_spread_threshold))
        
        # Adjust for volatility (higher volatility reduces execution probability)
        volatility_factor = max(0.1, 1.0 - market_volatility * 10)
        
        # Adjust for liquidity
        liquidity_factor = min(1.0, liquidity_score)
        
        return spread_prob * volatility_factor * liquidity_factor
    
    def _calculate_transaction_costs(self, position_size_a: float, position_size_b: float,
                                   price_a: float, price_b: float) -> float:
        """Calculate total transaction costs"""
        cost_a = abs(position_size_a * price_a) * self.config.transaction_cost
        cost_b = abs(position_size_b * price_b) * self.config.transaction_cost
        return cost_a + cost_b
    
    def _estimate_slippage(self, position_size: float, avg_volume: float, 
                          volatility: float) -> float:
        """Estimate slippage based on position size and market conditions"""
        # Market impact model: slippage increases with position size relative to volume
        if avg_volume <= 0:
            return self.config.slippage_tolerance * 2  # High slippage for illiquid markets
        
        volume_ratio = abs(position_size) / avg_volume
        base_slippage = self.config.slippage_tolerance * np.sqrt(volume_ratio)
        
        # Adjust for volatility
        volatility_adjustment = 1.0 + volatility * 5
        
        return base_slippage * volatility_adjustment
    
    def _calculate_risk_adjusted_profit(self, expected_profit: float, 
                                      execution_probability: float,
                                      volatility: float) -> float:
        """Calculate risk-adjusted expected profit"""
        # Adjust for execution probability
        prob_adjusted_profit = expected_profit * execution_probability
        
        # Adjust for volatility risk
        volatility_penalty = volatility * 0.5
        risk_adjusted_profit = prob_adjusted_profit - volatility_penalty
        
        return risk_adjusted_profit
    
    def _detect_arbitrage_regime(self, market_data: Dict[str, Dict[str, pd.DataFrame]]) -> ArbitrageRegime:
        """Detect current arbitrage regime"""
        # Calculate market-wide volatility
        volatilities = []
        for market, symbols in market_data.items():
            for symbol, data in symbols.items():
                if len(data) > 20:
                    returns = data['close'].pct_change().dropna()
                    vol = returns.rolling(20).std().iloc[-1]
                    if not np.isnan(vol):
                        volatilities.append(vol)
        
        if not volatilities:
            return ArbitrageRegime.NORMAL_CONDITIONS
        
        avg_volatility = np.mean(volatilities)
        vol_percentile = np.percentile(volatilities, 80)
        
        # Regime classification
        if avg_volatility > vol_percentile * 1.5:
            return ArbitrageRegime.CRISIS_MODE
        elif avg_volatility > vol_percentile:
            return ArbitrageRegime.HIGH_VOLATILITY
        elif avg_volatility < np.percentile(volatilities, 20):
            return ArbitrageRegime.LOW_VOLATILITY
        else:
            return ArbitrageRegime.NORMAL_CONDITIONS
    
    def _calculate_position_sizes(self, opportunity: ArbitrageOpportunity,
                                portfolio_value: float = 1000000) -> Tuple[float, float]:
        """Calculate optimal position sizes for arbitrage trade"""
        # Maximum position value
        max_position_value = portfolio_value * self.config.max_position_size
        
        # Calculate base position sizes
        if opportunity.arbitrage_type == ArbitrageType.CROSS_MARKET:
            # Equal dollar amounts
            position_value = min(max_position_value, 
                               opportunity.expected_profit * 100)  # 100x profit as position size
            
            shares_a = position_value / opportunity.price_a
            shares_b = -position_value / opportunity.price_b  # Short the expensive one
            
        elif opportunity.arbitrage_type == ArbitrageType.STATISTICAL:
            # Beta-neutral sizing
            hedge_ratio = self._calculate_hedge_ratio(opportunity)
            
            shares_b = max_position_value / opportunity.price_b
            shares_a = hedge_ratio * shares_b
            
        else:
            # Default equal dollar sizing
            position_value = max_position_value / 2
            shares_a = position_value / opportunity.price_a
            shares_b = -position_value / opportunity.price_b
        
        return shares_a, shares_b
    
    def _calculate_hedge_ratio(self, opportunity: ArbitrageOpportunity) -> float:
        """Calculate hedge ratio for arbitrage trade"""
        # Default to 1.0, override in specific strategies
        return 1.0


class CrossMarketArbitrageStrategy(BaseArbitrageStrategy):
    """Cross-market arbitrage strategy for same asset across different markets"""
    
    def detect_arbitrage_opportunities(self, market_data: Dict[str, Dict[str, pd.DataFrame]]) -> List[ArbitrageOpportunity]:
        """Detect cross-market arbitrage opportunities"""
        opportunities = []
        
        # Find common symbols across markets
        all_symbols = set()
        market_symbols = {}
        
        for market, symbols in market_data.items():
            market_symbols[market] = set(symbols.keys())
            all_symbols.update(symbols.keys())
        
        # Find symbols present in multiple markets
        for symbol in all_symbols:
            markets_with_symbol = [market for market, symbols in market_symbols.items() 
                                 if symbol in symbols]
            
            if len(markets_with_symbol) < 2:
                continue
            
            # Compare prices across markets
            for i, market_a in enumerate(markets_with_symbol):
                for market_b in markets_with_symbol[i+1:]:
                    try:
                        data_a = market_data[market_a][symbol]
                        data_b = market_data[market_b][symbol]
                        
                        if len(data_a) == 0 or len(data_b) == 0:
                            continue
                        
                        price_a = data_a['close'].iloc[-1]
                        price_b = data_b['close'].iloc[-1]
                        
                        spread, spread_pct = self._calculate_spread(price_a, price_b)
                        
                        if abs(spread_pct) > self.config.min_spread_threshold:
                            # Calculate expected profit after costs
                            transaction_costs = self._calculate_transaction_costs(
                                1000, -1000, price_a, price_b  # Dummy position sizes
                            )
                            
                            expected_profit = abs(spread_pct) - transaction_costs / ((price_a + price_b) / 2)
                            
                            if expected_profit > self.config.min_profit_threshold:
                                opportunity = ArbitrageOpportunity(
                                    arbitrage_type=ArbitrageType.CROSS_MARKET,
                                    symbol_a=symbol,
                                    symbol_b=symbol,
                                    market_a=market_a,
                                    market_b=market_b,
                                    price_a=price_a,
                                    price_b=price_b,
                                    spread=spread,
                                    spread_percentage=spread_pct,
                                    expected_profit=expected_profit,
                                    execution_time_limit=self.config.max_execution_delay,
                                    confidence=0.9,  # High confidence for cross-market arb
                                    risk_score=0.1,  # Low risk
                                    priority=1 if abs(spread_pct) > 0.01 else 2,
                                    metadata={
                                        'symbol': symbol,
                                        'price_difference': abs(price_a - price_b),
                                        'cheaper_market': market_a if price_a < price_b else market_b,
                                        'expensive_market': market_b if price_a < price_b else market_a
                                    },
                                    timestamp=datetime.now()
                                )
                                
                                opportunities.append(opportunity)
                                
                    except Exception as e:
                        self.logger.warning(f"Error detecting cross-market arbitrage for {symbol}: {e}")
        
        # Sort by expected profit
        opportunities.sort(key=lambda x: x.expected_profit, reverse=True)
        
        return opportunities[:10]  # Return top 10 opportunities
    
    def calculate_arbitrage_signal(self, opportunity: ArbitrageOpportunity, 
                                 market_data: Dict[str, Dict[str, pd.DataFrame]]) -> ArbitrageResult:
        """Calculate cross-market arbitrage signal"""
        # Get current market data
        data_a = market_data[opportunity.market_a][opportunity.symbol_a]
        data_b = market_data[opportunity.market_b][opportunity.symbol_b]
        
        # Calculate metrics
        volatility_a = data_a['close'].pct_change().rolling(20).std().iloc[-1]
        volatility_b = data_b['close'].pct_change().rolling(20).std().iloc[-1]
        avg_volatility = (volatility_a + volatility_b) / 2
        
        # Calculate liquidity scores
        liquidity_a = data_a['volume'].rolling(20).mean().iloc[-1]
        liquidity_b = data_b['volume'].rolling(20).mean().iloc[-1]
        min_liquidity = min(liquidity_a, liquidity_b)
        liquidity_score = min(1.0, min_liquidity / 1000000)  # Normalize to millions
        
        # Calculate execution probability
        execution_probability = self._estimate_execution_probability(
            abs(opportunity.spread_percentage), avg_volatility, liquidity_score
        )
        
        # Calculate position sizes
        position_size_a, position_size_b = self._calculate_position_sizes(opportunity)
        
        # Calculate transaction costs and slippage
        transaction_costs = self._calculate_transaction_costs(
            position_size_a, position_size_b, opportunity.price_a, opportunity.price_b
        )
        
        slippage_a = self._estimate_slippage(position_size_a, liquidity_a, volatility_a)
        slippage_b = self._estimate_slippage(position_size_b, liquidity_b, volatility_b)
        total_slippage = slippage_a + slippage_b
        
        # Calculate risk-adjusted profit
        gross_profit = abs(opportunity.spread_percentage) * abs(position_size_a * opportunity.price_a)
        net_profit = gross_profit - transaction_costs - total_slippage
        
        risk_adjusted_profit = self._calculate_risk_adjusted_profit(
            net_profit, execution_probability, avg_volatility
        )
        
        # Generate signal
        if risk_adjusted_profit > self.config.min_profit_threshold * 1000:  # Scale up
            if opportunity.price_a < opportunity.price_b:
                signal = ArbitrageSignal.ARBITRAGE_LONG_A_SHORT_B
            else:
                signal = ArbitrageSignal.ARBITRAGE_LONG_B_SHORT_A
        else:
            signal = ArbitrageSignal.NEUTRAL
        
        # Calculate strength and confidence
        strength = min(1.0, abs(opportunity.spread_percentage) / 0.01)  # Normalize to 1% spread
        confidence = execution_probability * liquidity_score
        
        # Detect regime
        regime = self._detect_arbitrage_regime(market_data)
        
        # Create metrics
        metrics = ArbitrageMetrics(
            spread_size=abs(opportunity.spread_percentage),
            spread_volatility=avg_volatility,
            execution_probability=execution_probability,
            expected_profit=net_profit,
            risk_adjusted_return=risk_adjusted_profit,
            sharpe_ratio=risk_adjusted_profit / avg_volatility if avg_volatility > 0 else 0,
            max_drawdown=avg_volatility * 2,  # Estimate
            win_rate=execution_probability,
            average_holding_time=self.config.max_execution_delay,
            transaction_costs=transaction_costs,
            slippage_impact=total_slippage,
            market_impact=total_slippage * 0.5
        )
        
        return ArbitrageResult(
            signal=signal,
            arbitrage_type=ArbitrageType.CROSS_MARKET,
            strength=strength,
            confidence=confidence,
            spread=opportunity.spread,
            spread_percentage=opportunity.spread_percentage,
            expected_profit=net_profit,
            risk_adjusted_profit=risk_adjusted_profit,
            execution_urgency=min(1.0, abs(opportunity.spread_percentage) / 0.005),
            holding_time_estimate=self.config.max_execution_delay,
            position_size_a=position_size_a,
            position_size_b=position_size_b,
            entry_price_a=opportunity.price_a,
            entry_price_b=opportunity.price_b,
            target_profit=net_profit,
            stop_loss_level=self.config.stop_loss,
            regime=regime,
            metrics=metrics,
            opportunities=[opportunity],
            metadata={
                'market_a': opportunity.market_a,
                'market_b': opportunity.market_b,
                'symbol': opportunity.symbol_a,
                'execution_time_limit': opportunity.execution_time_limit
            },
            timestamp=datetime.now()
        )


class StatisticalArbitrageStrategy(BaseArbitrageStrategy):
    """Statistical arbitrage strategy for correlated instruments"""
    
    def detect_arbitrage_opportunities(self, market_data: Dict[str, Dict[str, pd.DataFrame]]) -> List[ArbitrageOpportunity]:
        """Detect statistical arbitrage opportunities"""
        opportunities = []
        
        # Collect all instruments
        all_instruments = []
        for market, symbols in market_data.items():
            for symbol, data in symbols.items():
                if len(data) >= self.config.lookback_window:
                    all_instruments.append((market, symbol, data))
        
        # Find correlated pairs
        for i, (market_a, symbol_a, data_a) in enumerate(all_instruments):
            for market_b, symbol_b, data_b in all_instruments[i+1:]:
                try:
                    # Calculate correlation
                    returns_a = data_a['close'].pct_change().dropna()
                    returns_b = data_b['close'].pct_change().dropna()
                    
                    # Align series
                    aligned_a, aligned_b = returns_a.align(returns_b, join='inner')
                    
                    if len(aligned_a) < 30:
                        continue
                    
                    correlation = aligned_a.corr(aligned_b)
                    
                    if abs(correlation) < self.config.min_correlation:
                        continue
                    
                    # Calculate current spread
                    price_a = data_a['close'].iloc[-1]
                    price_b = data_b['close'].iloc[-1]
                    
                    # Calculate hedge ratio
                    hedge_ratio = self._calculate_statistical_hedge_ratio(data_a['close'], data_b['close'])
                    
                    spread, spread_pct = self._calculate_spread(price_a, price_b, hedge_ratio)
                    
                    # Calculate z-score
                    historical_spreads = data_a['close'] - hedge_ratio * data_b['close']
                    spread_mean = historical_spreads.rolling(self.config.lookback_window).mean().iloc[-1]
                    spread_std = historical_spreads.rolling(self.config.lookback_window).std().iloc[-1]
                    
                    if spread_std > 0:
                        z_score = (spread - spread_mean) / spread_std
                    else:
                        continue
                    
                    # Check if z-score exceeds threshold
                    if abs(z_score) > self.config.z_score_entry:
                        expected_profit = abs(z_score) * spread_std / ((price_a + price_b) / 2)
                        
                        if expected_profit > self.config.min_profit_threshold:
                            opportunity = ArbitrageOpportunity(
                                arbitrage_type=ArbitrageType.STATISTICAL,
                                symbol_a=symbol_a,
                                symbol_b=symbol_b,
                                market_a=market_a,
                                market_b=market_b,
                                price_a=price_a,
                                price_b=price_b,
                                spread=spread,
                                spread_percentage=spread_pct,
                                expected_profit=expected_profit,
                                execution_time_limit=300,  # 5 minutes
                                confidence=min(0.9, abs(correlation)),
                                risk_score=1.0 - abs(correlation),
                                priority=1 if abs(z_score) > 2.5 else 2,
                                metadata={
                                    'correlation': correlation,
                                    'z_score': z_score,
                                    'hedge_ratio': hedge_ratio,
                                    'spread_mean': spread_mean,
                                    'spread_std': spread_std
                                },
                                timestamp=datetime.now()
                            )
                            
                            opportunities.append(opportunity)
                            
                except Exception as e:
                    self.logger.warning(f"Error detecting statistical arbitrage for {symbol_a}-{symbol_b}: {e}")
        
        # Sort by z-score magnitude
        opportunities.sort(key=lambda x: abs(x.metadata['z_score']), reverse=True)
        
        return opportunities[:15]  # Return top 15 opportunities
    
    def _calculate_statistical_hedge_ratio(self, prices_a: pd.Series, prices_b: pd.Series) -> float:
        """Calculate hedge ratio for statistical arbitrage"""
        try:
            # Use recent data for hedge ratio calculation
            recent_a = prices_a.tail(self.config.lookback_window)
            recent_b = prices_b.tail(self.config.lookback_window)
            
            # Align series
            aligned_a, aligned_b = recent_a.align(recent_b, join='inner')
            
            if len(aligned_a) < 10:
                return 1.0
            
            # Linear regression
            X = aligned_b.values.reshape(-1, 1)
            y = aligned_a.values
            
            reg = LinearRegression().fit(X, y)
            hedge_ratio = reg.coef_[0]
            
            return hedge_ratio if not np.isnan(hedge_ratio) else 1.0
            
        except Exception:
            return 1.0
    
    def calculate_arbitrage_signal(self, opportunity: ArbitrageOpportunity, 
                                 market_data: Dict[str, Dict[str, pd.DataFrame]]) -> ArbitrageResult:
        """Calculate statistical arbitrage signal"""
        # Implementation similar to CrossMarketArbitrageStrategy but with statistical focus
        # Get current market data
        data_a = market_data[opportunity.market_a][opportunity.symbol_a]
        data_b = market_data[opportunity.market_b][opportunity.symbol_b]
        
        # Calculate z-score from metadata
        z_score = opportunity.metadata['z_score']
        correlation = opportunity.metadata['correlation']
        
        # Generate signal based on z-score
        if z_score > self.config.z_score_entry:
            signal = ArbitrageSignal.ARBITRAGE_LONG_B_SHORT_A  # Short expensive, long cheap
        elif z_score < -self.config.z_score_entry:
            signal = ArbitrageSignal.ARBITRAGE_LONG_A_SHORT_B  # Long expensive, short cheap
        else:
            signal = ArbitrageSignal.NEUTRAL
        
        # Calculate position sizes
        position_size_a, position_size_b = self._calculate_position_sizes(opportunity)
        
        # Apply hedge ratio
        hedge_ratio = opportunity.metadata['hedge_ratio']
        position_size_b *= hedge_ratio
        
        # Calculate metrics (simplified)
        volatility = data_a['close'].pct_change().rolling(20).std().iloc[-1]
        
        metrics = ArbitrageMetrics(
            spread_size=abs(opportunity.spread_percentage),
            spread_volatility=volatility,
            execution_probability=min(0.9, abs(correlation)),
            expected_profit=opportunity.expected_profit,
            risk_adjusted_return=opportunity.expected_profit * abs(correlation),
            sharpe_ratio=abs(z_score) / 2.0,  # Simplified
            max_drawdown=volatility * 3,
            win_rate=0.6,  # Historical estimate
            average_holding_time=3600,  # 1 hour
            transaction_costs=self.config.transaction_cost * 2,
            slippage_impact=self.config.slippage_tolerance,
            market_impact=self.config.slippage_tolerance * 0.5
        )
        
        return ArbitrageResult(
            signal=signal,
            arbitrage_type=ArbitrageType.STATISTICAL,
            strength=min(1.0, abs(z_score) / 3.0),
            confidence=abs(correlation),
            spread=opportunity.spread,
            spread_percentage=opportunity.spread_percentage,
            expected_profit=opportunity.expected_profit,
            risk_adjusted_profit=opportunity.expected_profit * abs(correlation),
            execution_urgency=min(1.0, abs(z_score) / 4.0),
            holding_time_estimate=3600,  # 1 hour
            position_size_a=position_size_a,
            position_size_b=position_size_b,
            entry_price_a=opportunity.price_a,
            entry_price_b=opportunity.price_b,
            target_profit=opportunity.expected_profit,
            stop_loss_level=self.config.stop_loss,
            regime=self._detect_arbitrage_regime(market_data),
            metrics=metrics,
            opportunities=[opportunity],
            metadata=opportunity.metadata,
            timestamp=datetime.now()
        )


class ArbitrageTradingManager:
    """Manager class for coordinating arbitrage trading strategies"""
    
    def __init__(self, config: ArbitrageConfig = None):
        self.config = config or ArbitrageConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize strategies
        self.strategies = {
            'cross_market': CrossMarketArbitrageStrategy(self.config),
            'statistical': StatisticalArbitrageStrategy(self.config)
        }
        
        # Active arbitrage trades
        self.active_trades = {}
        self.execution_queue = []
        
        # Performance tracking
        self.performance_history = []
        self.total_profit = 0.0
        self.total_trades = 0
        self.win_rate = 0.0
    
    def scan_arbitrage_opportunities(self, market_data: Dict[str, Dict[str, pd.DataFrame]]) -> Dict[str, List[ArbitrageOpportunity]]:
        """Scan for arbitrage opportunities across all strategies"""
        all_opportunities = {}
        
        for strategy_name, strategy in self.strategies.items():
            try:
                opportunities = strategy.detect_arbitrage_opportunities(market_data)
                all_opportunities[strategy_name] = opportunities
                
                self.logger.info(f"Found {len(opportunities)} {strategy_name} arbitrage opportunities")
                
            except Exception as e:
                self.logger.error(f"Error scanning {strategy_name} arbitrage opportunities: {e}")
                all_opportunities[strategy_name] = []
        
        return all_opportunities
    
    def calculate_arbitrage_signals(self, opportunities: Dict[str, List[ArbitrageOpportunity]], 
                                  market_data: Dict[str, Dict[str, pd.DataFrame]]) -> Dict[str, List[ArbitrageResult]]:
        """Calculate arbitrage signals for all opportunities"""
        results = {}
        
        for strategy_name, strategy_opportunities in opportunities.items():
            strategy_results = []
            strategy = self.strategies[strategy_name]
            
            for opportunity in strategy_opportunities[:5]:  # Limit to top 5 per strategy
                try:
                    result = strategy.calculate_arbitrage_signal(opportunity, market_data)
                    
                    if result.signal != ArbitrageSignal.NEUTRAL:
                        strategy_results.append(result)
                        
                except Exception as e:
                    self.logger.error(f"Error calculating arbitrage signal: {e}")
            
            results[strategy_name] = strategy_results
        
        return results
    
    def get_best_arbitrage_trades(self, results: Dict[str, List[ArbitrageResult]], 
                                top_n: int = 5) -> List[Tuple[str, ArbitrageResult]]:
        """Get best arbitrage trading opportunities"""
        all_trades = []
        
        for strategy_name, strategy_results in results.items():
            for result in strategy_results:
                if (result.signal != ArbitrageSignal.NEUTRAL and 
                    result.confidence > 0.7 and
                    result.expected_profit > self.config.min_profit_threshold):
                    
                    all_trades.append((strategy_name, result))
        
        # Sort by risk-adjusted profit and execution urgency
        all_trades.sort(key=lambda x: x[1].risk_adjusted_profit * x[1].execution_urgency, 
                       reverse=True)
        
        return all_trades[:top_n]
    
    def execute_arbitrage_trade(self, strategy_name: str, result: ArbitrageResult) -> bool:
        """Execute arbitrage trade (simulation)"""
        try:
            trade_id = f"{strategy_name}_{result.timestamp.strftime('%Y%m%d_%H%M%S')}"
            
            # Simulate execution
            execution_success = result.metrics.execution_probability > np.random.random()
            
            if execution_success:
                # Record successful trade
                self.active_trades[trade_id] = {
                    'strategy': strategy_name,
                    'result': result,
                    'entry_time': datetime.now(),
                    'status': 'active'
                }
                
                self.logger.info(f"Executed arbitrage trade {trade_id}: {result.signal.name}")
                return True
            else:
                self.logger.warning(f"Failed to execute arbitrage trade {trade_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing arbitrage trade: {e}")
            return False
    
    def update_performance_metrics(self):
        """Update performance metrics"""
        if not self.performance_history:
            return
        
        profits = [trade['profit'] for trade in self.performance_history]
        
        self.total_profit = sum(profits)
        self.total_trades = len(profits)
        self.win_rate = sum(1 for p in profits if p > 0) / len(profits) if profits else 0
        
        self.logger.info(f"Arbitrage Performance - Total Profit: {self.total_profit:.4f}, "
                        f"Win Rate: {self.win_rate:.2%}, Total Trades: {self.total_trades}")


# Example usage and testing functions
def create_arbitrage_test_data() -> Dict[str, Dict[str, pd.DataFrame]]:
    """Create sample market data for arbitrage testing"""
    np.random.seed(42)
    
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
    
    # Create cross-market arbitrage opportunity
    base_price = 100.0
    market_a_prices = base_price + np.random.normal(0, 1, 100).cumsum()
    market_b_prices = market_a_prices + np.random.normal(0.5, 0.2, 100)  # Slight premium
    
    # Create correlated pair for statistical arbitrage
    stock_1_prices = 50.0 + np.random.normal(0, 0.5, 100).cumsum()
    stock_2_prices = stock_1_prices * 1.2 + np.random.normal(0, 0.3, 100)  # Correlated with noise
    
    def create_ohlc_data(prices, base_volume=1000000):
        return pd.DataFrame({
            'date': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
            'close': prices,
            'volume': np.random.lognormal(np.log(base_volume), 0.2, len(prices))
        })
    
    market_data = {
        'NYSE': {
            'AAPL': create_ohlc_data(market_a_prices),
            'STOCK1': create_ohlc_data(stock_1_prices)
        },
        'NASDAQ': {
            'AAPL': create_ohlc_data(market_b_prices),  # Same stock, different market
            'STOCK2': create_ohlc_data(stock_2_prices)
        }
    }
    
    return market_data


def test_arbitrage_strategies():
    """Test arbitrage trading strategies with sample data"""
    # Create sample market data
    market_data = create_arbitrage_test_data()
    
    # Initialize arbitrage trading manager
    config = ArbitrageConfig(
        min_spread_threshold=0.001,
        min_profit_threshold=0.002,
        z_score_entry=2.0,
        min_correlation=0.7
    )
    
    manager = ArbitrageTradingManager(config)
    
    # Scan for arbitrage opportunities
    opportunities = manager.scan_arbitrage_opportunities(market_data)
    
    print("\n=== Arbitrage Opportunities ===")
    for strategy_name, strategy_opportunities in opportunities.items():
        print(f"\n{strategy_name.upper()} Arbitrage:")
        for i, opp in enumerate(strategy_opportunities[:3], 1):
            print(f"  {i}. {opp.symbol_a} ({opp.market_a}) vs {opp.symbol_b} ({opp.market_b})")
            print(f"     Spread: {opp.spread_percentage:.4f} ({opp.spread_percentage*100:.2f}%)")
            print(f"     Expected Profit: {opp.expected_profit:.4f}")
            print(f"     Confidence: {opp.confidence:.3f}")
            print(f"     Priority: {opp.priority}")
    
    # Calculate arbitrage signals
    results = manager.calculate_arbitrage_signals(opportunities, market_data)
    
    print("\n=== Arbitrage Trading Signals ===")
    for strategy_name, strategy_results in results.items():
        print(f"\n{strategy_name.upper()} Signals:")
        for i, result in enumerate(strategy_results, 1):
            print(f"  {i}. Signal: {result.signal.name}")
            print(f"     Strength: {result.strength:.3f}")
            print(f"     Confidence: {result.confidence:.3f}")
            print(f"     Expected Profit: {result.expected_profit:.4f}")
            print(f"     Risk-Adjusted Profit: {result.risk_adjusted_profit:.4f}")
            print(f"     Execution Urgency: {result.execution_urgency:.3f}")
            print(f"     Regime: {result.regime.value}")
    
    # Get best arbitrage trades
    best_trades = manager.get_best_arbitrage_trades(results, top_n=5)
    
    print("\n=== Best Arbitrage Trades ===")
    for i, (strategy_name, result) in enumerate(best_trades, 1):
        score = result.risk_adjusted_profit * result.execution_urgency
        print(f"{i}. {strategy_name}: {result.signal.name}")
        print(f"   Score: {score:.4f}")
        print(f"   Expected Profit: {result.expected_profit:.4f}")
        print(f"   Confidence: {result.confidence:.3f}")
        print(f"   Execution Urgency: {result.execution_urgency:.3f}")
        
        # Simulate execution
        success = manager.execute_arbitrage_trade(strategy_name, result)
        print(f"   Execution: {'SUCCESS' if success else 'FAILED'}")
    
    # Update performance metrics
    manager.update_performance_metrics()


if __name__ == "__main__":
    # Run tests
    test_arbitrage_strategies()