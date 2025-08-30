"""
Technical Indicator Manager
Comprehensive system to manage and execute 30+ custom technical indicators

Features:
- Volume-weighted calculations
- Signal aggregation and consensus
- Performance optimization
- Real-time indicator updates
- Custom indicator compositions

Author: Vincent S. Pereira
Phase: Phase 1 - Core System Validation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
import json

from .technical_indicators import TechnicalIndicators, IndicatorResult, IndicatorType
from .advanced_indicators import AdvancedIndicators

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MarketData:
    """Market data container"""
    symbol: str
    timestamp: datetime
    open: pd.Series
    high: pd.Series
    low: pd.Series
    close: pd.Series
    volume: pd.Series
    
@dataclass
class IndicatorConfig:
    """Configuration for individual indicators"""
    name: str
    enabled: bool = True
    weight: float = 1.0
    params: Dict[str, Any] = None
    
@dataclass
class SignalResult:
    """Aggregated signal result"""
    signal: str  # BUY, SELL, NEUTRAL
    confidence: float  # 0.0 to 1.0
    strength: float   # 0.0 to 1.0
    contributing_indicators: List[str]
    timestamp: datetime
    metadata: Dict[str, Any]

class IndicatorManager:
    """Comprehensive technical indicator management system"""
    
    def __init__(self):
        self.indicators = {}
        self.results_cache = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.initialize_indicators()
        
    def initialize_indicators(self):
        """Initialize all 34 technical indicators"""
        
        # Trend Indicators (12) - Enhanced with volume weighting
        trend_indicators = [
            IndicatorConfig("sma", True, 1.0, {"period": 20}),
            IndicatorConfig("ema", True, 1.2, {"period": 20}),
            IndicatorConfig("vwma", True, 1.8, {"period": 20}),  # Higher weight - volume weighted
            IndicatorConfig("vw_ema", True, 1.6, {"period": 20}),  # Volume weighted EMA
            IndicatorConfig("hull_ma", True, 1.1, {"period": 16}),
            IndicatorConfig("kaufman_ama", True, 1.3, {"period": 14}),
            IndicatorConfig("dema", True, 1.0, {"period": 20}),
            IndicatorConfig("tema", True, 1.0, {"period": 20}),
            IndicatorConfig("wma", True, 1.0, {"period": 20}),
            IndicatorConfig("mama", True, 0.9, {"fastlimit": 0.5, "slowlimit": 0.05}),
            IndicatorConfig("t3", True, 1.0, {"period": 14, "vfactor": 0.7}),
            IndicatorConfig("vw_keltner_ema", True, 1.4, {"period": 20, "atr_period": 14})  # VW Keltner EMA
        ]
        
        # Momentum Indicators (12) - Enhanced with volume weighting
        momentum_indicators = [
            IndicatorConfig("rsi", True, 1.2, {"period": 14}),
            IndicatorConfig("vw_rsi", True, 1.6, {"period": 14}),  # Volume weighted RSI
            IndicatorConfig("macd", True, 1.3, {"fast": 12, "slow": 26, "signal": 9}),
            IndicatorConfig("vw_macd", True, 1.8, {"fast": 12, "slow": 26, "signal": 9}),  # Volume weighted MACD
            IndicatorConfig("stochastic", True, 1.2, {"k_period": 14, "d_period": 3}),
            IndicatorConfig("williams_r", True, 1.0, {"period": 14}),
            IndicatorConfig("cci", True, 1.1, {"period": 20}),
            IndicatorConfig("roc", True, 1.0, {"period": 12}),
            IndicatorConfig("momentum", True, 0.9, {"period": 10}),
            IndicatorConfig("ppo", True, 1.0, {"fast": 12, "slow": 26}),
            IndicatorConfig("trix", True, 0.8, {"period": 14}),
            IndicatorConfig("ultimate_oscillator", True, 1.2, {"period1": 7, "period2": 14, "period3": 28})
        ]
        
        # Volatility Indicators (8) - Enhanced with volume weighting
        volatility_indicators = [
            IndicatorConfig("bollinger_bands", True, 1.3, {"period": 20, "std_dev": 2.0}),
            IndicatorConfig("atr", True, 1.1, {"period": 14}),
            IndicatorConfig("vw_atr", True, 1.5, {"period": 14}),  # Volume weighted ATR
            IndicatorConfig("vw_atrp", True, 1.4, {"period": 14}),  # Volume weighted ATRP
            IndicatorConfig("keltner_channels", True, 1.1, {"period": 20, "multiplier": 2.0}),
            IndicatorConfig("donchian_channels", True, 1.0, {"period": 20}),
            IndicatorConfig("standard_deviation", True, 0.9, {"period": 20}),
            IndicatorConfig("average_deviation", True, 0.8, {"period": 20})
        ]
        
        # Volume Indicators (8) - Enhanced with volume weighting
        volume_indicators = [
            IndicatorConfig("vwap", True, 1.8, {}),  # High weight for volume-based
            IndicatorConfig("obv", True, 1.6, {}),
            IndicatorConfig("ad_line", True, 1.5, {}),
            IndicatorConfig("mfi", True, 1.4, {"period": 14}),
            IndicatorConfig("chaikin_oscillator", True, 1.3, {"fast": 3, "slow": 10}),
            IndicatorConfig("volume_rate_of_change", True, 1.2, {"period": 14}),
            IndicatorConfig("ease_of_movement", True, 1.1, {"period": 14}),
            IndicatorConfig("negative_volume_index", True, 1.0, {})
        ]
        
        # Candlestick Pattern Indicators (2) - Visual pattern recognition
        pattern_indicators = [
            IndicatorConfig("candlestick_patterns", True, 1.6, {}),  # High weight for pattern signals
            IndicatorConfig("pattern_strength_analysis", True, 1.4, {})  # Volume-confirmed patterns
        ]
        
        # Combine all indicators (Total: 40+ indicators including patterns)
        all_indicators = (trend_indicators + momentum_indicators + 
                         volatility_indicators + volume_indicators + pattern_indicators)
        
        for indicator in all_indicators:
            self.indicators[indicator.name] = indicator
            
        logger.info(f"Initialized {len(all_indicators)} technical indicators (including volume-weighted variants + candlestick patterns)")
        
    async def calculate_indicators(self, market_data: MarketData) -> Dict[str, IndicatorResult]:
        """Calculate all enabled indicators for given market data"""
        
        results = {}
        tasks = []
        
        for name, config in self.indicators.items():
            if not config.enabled:
                continue
                
            # Create calculation task
            task = asyncio.create_task(
                self._calculate_single_indicator(name, config, market_data)
            )
            tasks.append((name, task))
        
        # Execute all calculations concurrently
        for name, task in tasks:
            try:
                result = await task
                if result:
                    results[name] = result
            except Exception as e:
                logger.error(f"Error calculating {name}: {e}")
                
        logger.info(f"Calculated {len(results)} indicators for {market_data.symbol}")
        return results
    
    async def _calculate_single_indicator(self, name: str, config: IndicatorConfig, 
                                        market_data: MarketData) -> Optional[IndicatorResult]:
        """Calculate a single indicator"""
        
        try:
            params = config.params or {}
            
            # Trend Indicators
            if name == "sma":
                return TechnicalIndicators.sma(market_data.close, **params)
            elif name == "ema":
                return TechnicalIndicators.ema(market_data.close, **params)
            elif name == "vwma":
                return TechnicalIndicators.vwma(market_data.close, market_data.volume, **params)
            elif name == "vw_ema":
                return TechnicalIndicators.vw_ema(market_data.close, market_data.volume, **params)
            elif name == "hull_ma":
                return AdvancedIndicators.hull_ma(market_data.close, **params)
            elif name == "kaufman_ama":
                return AdvancedIndicators.kaufman_ama(market_data.close, **params)
                
            # Momentum Indicators
            elif name == "rsi":
                return TechnicalIndicators.rsi(market_data.close, **params)
            elif name == "vw_rsi":
                return TechnicalIndicators.vw_rsi(market_data.close, market_data.volume, **params)
            elif name == "macd":
                return TechnicalIndicators.macd(market_data.close, **params)
            elif name == "vw_macd":
                return TechnicalIndicators.vw_macd(market_data.close, market_data.volume, **params)
            elif name == "stochastic":
                return AdvancedIndicators.stochastic(market_data.high, market_data.low, market_data.close, **params)
            elif name == "williams_r":
                return AdvancedIndicators.williams_r(market_data.high, market_data.low, market_data.close, **params)
            elif name == "cci":
                return AdvancedIndicators.cci(market_data.high, market_data.low, market_data.close, **params)
                
            # Volatility Indicators
            elif name == "bollinger_bands":
                return TechnicalIndicators.bollinger_bands(market_data.close, **params)
            elif name == "atr":
                return TechnicalIndicators.atr(market_data.high, market_data.low, market_data.close, **params)
            elif name == "vw_atr":
                return TechnicalIndicators.vw_atr(market_data.high, market_data.low, market_data.close, market_data.volume, **params)
            elif name == "vw_atrp":
                return TechnicalIndicators.vw_atrp(market_data.high, market_data.low, market_data.close, market_data.volume, **params)
            elif name == "keltner_channels":
                return AdvancedIndicators.keltner_channels(market_data.high, market_data.low, market_data.close, **params)
            elif name == "donchian_channels":
                return AdvancedIndicators.donchian_channels(market_data.high, market_data.low, **params)
                
            # Volume Indicators
            elif name == "vwap":
                return TechnicalIndicators.vwap(market_data.high, market_data.low, market_data.close, market_data.volume)
            elif name == "obv":
                return TechnicalIndicators.obv(market_data.close, market_data.volume)
            elif name == "ad_line":
                return AdvancedIndicators.ad_line(market_data.high, market_data.low, market_data.close, market_data.volume)
            elif name == "mfi":
                return AdvancedIndicators.mfi(market_data.high, market_data.low, market_data.close, market_data.volume, **params)
                
            # Candlestick Pattern Indicators
            elif name == "candlestick_patterns":
                return TechnicalIndicators.candlestick_patterns(
                    market_data.open, market_data.high, market_data.low, market_data.close, market_data.volume
                )
            elif name == "pattern_strength_analysis":
                return TechnicalIndicators.pattern_strength_analysis(
                    market_data.open, market_data.high, market_data.low, market_data.close, market_data.volume
                )
                
            # Add implementations for remaining indicators...
            else:
                logger.warning(f"Indicator {name} not implemented yet")
                return None
                
        except Exception as e:
            logger.error(f"Error in {name}: {e}")
            return None
    
    def aggregate_signals(self, indicator_results: Dict[str, IndicatorResult]) -> SignalResult:
        """Aggregate signals from all indicators with volume weighting"""
        
        buy_weight = 0.0
        sell_weight = 0.0
        total_weight = 0.0
        contributing_indicators = []
        
        for name, result in indicator_results.items():
            config = self.indicators[name]
            weight = config.weight * result.strength
            
            if result.signal == "BUY":
                buy_weight += weight
                contributing_indicators.append(f"{name}(BUY)")
            elif result.signal == "SELL":
                sell_weight += weight
                contributing_indicators.append(f"{name}(SELL)")
                
            total_weight += weight
        
        # Determine final signal
        if total_weight == 0:
            signal = "NEUTRAL"
            confidence = 0.0
            strength = 0.0
        else:
            buy_ratio = buy_weight / total_weight
            sell_ratio = sell_weight / total_weight
            
            if buy_ratio > sell_ratio and buy_ratio > 0.6:
                signal = "BUY"
                confidence = buy_ratio
                strength = buy_ratio - sell_ratio
            elif sell_ratio > buy_ratio and sell_ratio > 0.6:
                signal = "SELL"
                confidence = sell_ratio
                strength = sell_ratio - buy_ratio
            else:
                signal = "NEUTRAL"
                confidence = max(buy_ratio, sell_ratio)
                strength = abs(buy_ratio - sell_ratio)
        
        return SignalResult(
            signal=signal,
            confidence=confidence,
            strength=strength,
            contributing_indicators=contributing_indicators,
            timestamp=datetime.now(),
            metadata={
                "total_indicators": len(indicator_results),
                "buy_weight": buy_weight,
                "sell_weight": sell_weight,
                "total_weight": total_weight
            }
        )
    
    async def get_trading_signal(self, market_data: MarketData) -> SignalResult:
        """Get comprehensive trading signal from all indicators"""
        
        # Calculate all indicators
        indicator_results = await self.calculate_indicators(market_data)
        
        # Aggregate signals
        signal_result = self.aggregate_signals(indicator_results)
        
        # Cache results
        self.results_cache[market_data.symbol] = {
            "timestamp": datetime.now(),
            "indicator_results": indicator_results,
            "signal_result": signal_result
        }
        
        return signal_result
    
    def get_indicator_summary(self) -> Dict[str, Any]:
        """Get summary of all indicators"""
        
        by_type = {"trend": 0, "momentum": 0, "volatility": 0, "volume": 0, "patterns": 0}
        enabled_count = 0
        total_weight = 0.0
        
        for name, config in self.indicators.items():
            if config.enabled:
                enabled_count += 1
                total_weight += config.weight
                
                # Categorize by type (enhanced with patterns)
                if any(x in name.lower() for x in ["sma", "ema", "vwma", "vw_ema", "hull", "kaufman", "dema", "tema", "wma", "mama", "t3", "keltner_ema"]):
                    by_type["trend"] += 1
                elif any(x in name.lower() for x in ["rsi", "vw_rsi", "macd", "vw_macd", "stochastic", "williams", "cci", "roc", "momentum", "ppo", "trix", "ultimate"]):
                    by_type["momentum"] += 1
                elif any(x in name.lower() for x in ["bollinger", "atr", "vw_atr", "vw_atrp", "keltner", "donchian", "deviation"]):
                    by_type["volatility"] += 1
                elif any(x in name.lower() for x in ["vwap", "obv", "volume", "mfi", "chaikin", "ease", "negative", "ad_line"]):
                    by_type["volume"] += 1
                elif any(x in name.lower() for x in ["candlestick", "pattern"]):
                    by_type["patterns"] += 1
        
        return {
            "total_indicators": len(self.indicators),
            "enabled_indicators": enabled_count,
            "total_weight": total_weight,
            "by_type": by_type,
            "volume_weighted": True,
            "concurrent_execution": True
        }


# Test and demonstration functions
async def test_indicator_manager():
    """Test the indicator manager with sample data"""
    
    logger.info("🧪 Testing Technical Indicator Manager (30+ Indicators)")
    logger.info("=" * 60)
    
    # Create sample market data
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    np.random.seed(42)
    
    # Generate realistic price data
    base_price = 100
    price_changes = np.random.normal(0, 0.02, len(dates))
    prices = [base_price]
    
    for change in price_changes[1:]:
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, 0.01))  # Prevent negative prices
    
    # Create OHLCV data
    close_prices = pd.Series(prices, index=dates)
    high_prices = close_prices * (1 + np.random.uniform(0, 0.03, len(dates)))
    low_prices = close_prices * (1 - np.random.uniform(0, 0.03, len(dates)))
    open_prices = close_prices.shift(1).fillna(close_prices[0])
    volumes = pd.Series(np.random.randint(100000, 1000000, len(dates)), index=dates)
    
    market_data = MarketData(
        symbol="TEST",
        timestamp=datetime.now(),
        open=open_prices,
        high=high_prices,
        low=low_prices,
        close=close_prices,
        volume=volumes
    )
    
    # Initialize indicator manager
    manager = IndicatorManager()
    
    # Get indicator summary
    summary = manager.get_indicator_summary()
    logger.info(f"📊 Indicator Summary:")
    logger.info(f"  Total Indicators: {summary['total_indicators']}")
    logger.info(f"  Enabled: {summary['enabled_indicators']}")
    logger.info(f"  Total Weight: {summary['total_weight']:.1f}")
    logger.info(f"  By Type: {summary['by_type']}")
    
    # Calculate trading signal
    logger.info(f"\n🎯 Calculating Trading Signal...")
    signal_result = await manager.get_trading_signal(market_data)
    
    logger.info(f"\n📈 Trading Signal Results:")
    logger.info(f"  Signal: {signal_result.signal}")
    logger.info(f"  Confidence: {signal_result.confidence:.2%}")
    logger.info(f"  Strength: {signal_result.strength:.2%}")
    logger.info(f"  Contributing Indicators: {len(signal_result.contributing_indicators)}")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"indicator_test_results_{timestamp}.json"
    
    results_data = {
        "summary": summary,
        "signal_result": {
            "signal": signal_result.signal,
            "confidence": signal_result.confidence,
            "strength": signal_result.strength,
            "contributing_indicators": signal_result.contributing_indicators,
            "metadata": signal_result.metadata
        },
        "test_timestamp": datetime.now().isoformat()
    }
    
    with open(results_file, 'w') as f:
        json.dump(results_data, f, indent=2, default=str)
    
    logger.info(f"\n💾 Results saved to: {results_file}")
    
    return signal_result

if __name__ == "__main__":
    asyncio.run(test_indicator_manager())