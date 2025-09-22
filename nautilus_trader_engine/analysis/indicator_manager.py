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

# Replace stale imports with consolidated factories and core result types
from .core_indicator_base import IndicatorResult
from .trend_indicators import (
    create_sma, create_ema, create_vwma, create_hma
)
from .momentum_indicators import (
    create_rsi, create_macd, create_stochastic
)
from .volatility_indicators import (
    create_bollinger_bands, create_atr, create_keltner_channels, create_standard_deviation
)
from .volume_indicators import (
    create_vwap, create_obv, create_mfi
)
from .pattern_indicators import create_pattern_detector

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
    """Configuration for individual indicators (manager-level)"""
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
        self.indicators: Dict[str, IndicatorConfig] = {}
        self.indicator_instances: Dict[str, Any] = {}
        self.results_cache = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.initialize_indicators()
        
    def initialize_indicators(self):
        """Initialize supported technical indicators using consolidated factories"""
        
        # Trend Indicators (supported)
        trend_indicators = [
            IndicatorConfig("sma", True, 1.0, {"period": 20}),
            IndicatorConfig("ema", True, 1.2, {"period": 20}),
            IndicatorConfig("vwma", True, 1.8, {"period": 20}),
            IndicatorConfig("vw_ema", True, 1.6, {"period": 20, "volume_weighted": True}),  # map to EMA with volume weighting
            IndicatorConfig("hull_ma", True, 1.1, {"period": 16}),
        ]
        
        # Momentum Indicators (supported)
        momentum_indicators = [
            IndicatorConfig("rsi", True, 1.2, {"period": 14}),
            IndicatorConfig("vw_rsi", True, 1.6, {"period": 14, "enable_volume_weighting": True}),
            IndicatorConfig("macd", True, 1.3, {"fast_period": 12, "slow_period": 26, "signal_period": 9}),
            IndicatorConfig("vw_macd", True, 1.8, {"fast_period": 12, "slow_period": 26, "signal_period": 9, "enable_volume_weighting": True}),
            IndicatorConfig("stochastic", True, 1.2, {"k_period": 14, "d_period": 3, "smooth_k": 3}),
        ]
        
        # Volatility Indicators (supported)
        volatility_indicators = [
            IndicatorConfig("bollinger_bands", True, 1.3, {"period": 20, "std_dev": 2.0}),
            IndicatorConfig("atr", True, 1.1, {"period": 14}),
            IndicatorConfig("vw_atr", True, 1.5, {"period": 14, "volume_weighted": True}),
            IndicatorConfig("keltner_channels", True, 1.1, {"period": 20, "atr_multiplier": 2.0}),
            IndicatorConfig("standard_deviation", True, 0.9, {"period": 20}),
        ]
        
        # Volume Indicators (supported subset)
        volume_indicators = [
            IndicatorConfig("vwap", True, 1.8, {}),
            IndicatorConfig("obv", True, 1.6, {}),
            IndicatorConfig("mfi", True, 1.4, {"period": 14}),
        ]
        
        # Candlestick Pattern Indicators (consolidated)
        pattern_indicators = [
            IndicatorConfig("candlestick_patterns", True, 1.6, {}),
        ]
        
        # Combine supported indicators
        all_indicators = trend_indicators + momentum_indicators + volatility_indicators + volume_indicators + pattern_indicators
        
        # Register configs and create instances
        self.indicators.clear()
        self.indicator_instances.clear()
        for indicator in all_indicators:
            self.indicators[indicator.name] = indicator
            instance = self._create_indicator_instance(indicator.name, indicator.params or {})
            if instance is not None:
                self.indicator_instances[indicator.name] = instance
            else:
                logger.warning(f"Factory not found or unsupported for indicator: {indicator.name}")
            
        logger.info(f"Initialized {len(self.indicator_instances)} indicator instances (from {len(all_indicators)} configured)")
    
    def _create_indicator_instance(self, name: str, params: Dict[str, Any]):
        """Create indicator instance using consolidated factories"""
        try:
            lname = name.lower()
            # Trend
            if lname == "sma":
                return create_sma(period=int(params.get("period", 20)), volume_weighted=bool(params.get("volume_weighted", False)))
            if lname == "ema":
                return create_ema(period=int(params.get("period", 20)), volume_weighted=bool(params.get("volume_weighted", False)))
            if lname == "vwma":
                return create_vwma(period=int(params.get("period", 20)))
            if lname == "vw_ema":
                return create_ema(period=int(params.get("period", 20)), volume_weighted=True)
            if lname == "hull_ma":
                return create_hma(period=int(params.get("period", 16)), volume_weighted=bool(params.get("volume_weighted", False)))
            
            # Momentum
            if lname == "rsi":
                return create_rsi(period=int(params.get("period", 14)), **{k: v for k, v in params.items() if k != "period"})
            if lname == "vw_rsi":
                # Enable volume weighting via config flag
                p = dict(params)
                p.setdefault("enable_volume_weighting", True)
                p.setdefault("period", 14)
                return create_rsi(period=int(p.pop("period")), **p)
            if lname == "macd":
                return create_macd(
                    fast_period=int(params.get("fast_period", 12)),
                    slow_period=int(params.get("slow_period", 26)),
                    signal_period=int(params.get("signal_period", 9)),
                    **{k: v for k, v in params.items() if k not in {"fast_period", "slow_period", "signal_period"}}
                )
            if lname == "vw_macd":
                p = dict(params)
                p.setdefault("enable_volume_weighting", True)
                return create_macd(
                    fast_period=int(p.pop("fast_period", 12)),
                    slow_period=int(p.pop("slow_period", 26)),
                    signal_period=int(p.pop("signal_period", 9)),
                    **p
                )
            if lname == "stochastic":
                return create_stochastic(
                    k_period=int(params.get("k_period", 14)),
                    d_period=int(params.get("d_period", 3)),
                    smooth_k=int(params.get("smooth_k", 3)),
                    **{k: v for k, v in params.items() if k not in {"k_period", "d_period", "smooth_k"}}
                )
            
            # Volatility
            if lname == "bollinger_bands":
                return create_bollinger_bands(
                    period=int(params.get("period", 20)),
                    std_dev=float(params.get("std_dev", 2.0)),
                    volume_weighted=bool(params.get("volume_weighted", False)),
                    **{k: v for k, v in params.items() if k not in {"period", "std_dev", "volume_weighted"}}
                )
            if lname == "atr":
                return create_atr(period=int(params.get("period", 14)), volume_weighted=bool(params.get("volume_weighted", False)))
            if lname == "vw_atr":
                return create_atr(period=int(params.get("period", 14)), volume_weighted=True)
            if lname == "keltner_channels":
                return create_keltner_channels(
                    period=int(params.get("period", 20)),
                    atr_multiplier=float(params.get("atr_multiplier", 2.0)),
                    volume_weighted=bool(params.get("volume_weighted", False)),
                    **{k: v for k, v in params.items() if k not in {"period", "atr_multiplier", "volume_weighted"}}
                )
            if lname == "standard_deviation":
                return create_standard_deviation(period=int(params.get("period", 20)), volume_weighted=bool(params.get("volume_weighted", False)))
            
            # Volume
            if lname == "vwap":
                return create_vwap(**{k: v for k, v in params.items()})
            if lname == "obv":
                return create_obv(**{k: v for k, v in params.items()})
            if lname == "mfi":
                return create_mfi(period=int(params.get("period", 14)), **{k: v for k, v in params.items() if k != "period"})
            
            # Patterns
            if lname in {"candlestick_patterns", "pattern_strength_analysis"}:
                return create_pattern_detector(**{k: v for k, v in params.items()})
            
            return None
        except Exception as e:
            logger.error(f"Failed to create indicator instance for {name}: {e}")
            return None
        
    async def calculate_indicators(self, market_data: MarketData) -> Dict[str, IndicatorResult]:
        """Calculate all enabled indicators for given market data"""
        
        results: Dict[str, IndicatorResult] = {}
        tasks: List[Tuple[str, asyncio.Task]] = []
        
        for name, config in self.indicators.items():
            if not config.enabled:
                continue
            if name not in self.indicator_instances:
                logger.warning(f"No instance available for indicator: {name}")
                continue
            
            task = asyncio.create_task(self._calculate_single_indicator(name, config, market_data))
            tasks.append((name, task))
        
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
        """Calculate a single indicator by sequentially feeding OHLCV data"""
        
        instance = self.indicator_instances.get(name)
        if instance is None:
            return None
        
        loop = asyncio.get_running_loop()
        
        def compute_last_result() -> Optional[IndicatorResult]:
            try:
                # Reset instance state for a fresh run
                if hasattr(instance, 'reset'):
                    instance.reset()
                last_result: Optional[IndicatorResult] = None
                
                # Iterate over time series
                for ts in market_data.close.index:
                    price = float(market_data.close.loc[ts])
                    volume = float(market_data.volume.loc[ts]) if market_data.volume is not None else 1.0
                    
                    # Pattern detector needs full OHLC
                    if name in {"candlestick_patterns", "pattern_strength_analysis"} and hasattr(instance, 'calculate'):
                        ohlc_data = {
                            'open': float(market_data.open.loc[ts]),
                            'high': float(market_data.high.loc[ts]),
                            'low': float(market_data.low.loc[ts]),
                            'close': price,
                        }
                        result = instance.calculate(price=price, volume=volume, timestamp=ts, ohlc_data=ohlc_data)
                    else:
                        # Default streaming update API
                        result = instance.update(price=price, volume=volume, timestamp=ts)
                    
                    if result is not None:
                        last_result = result
                
                return last_result
            except Exception as e:
                logger.error(f"Error in compute_last_result for {name}: {e}")
                return None
        
        # Offload computation to thread pool to avoid blocking event loop
        return await loop.run_in_executor(self.executor, compute_last_result)
    
    def aggregate_signals(self, indicator_results: Dict[str, IndicatorResult]) -> SignalResult:
        """Aggregate signals from all indicators with volume weighting"""
        
        buy_weight = 0.0
        sell_weight = 0.0
        total_weight = 0.0
        contributing_indicators: List[str] = []
        
        for name, result in indicator_results.items():
            config = self.indicators.get(name)
            if config is None:
                continue
            
            # Extract signal direction and strength robustly across implementations
            sig = getattr(result, 'signal', None)
            if sig is None:
                continue
            
            # Determine signal type string
            if hasattr(sig, 'signal_type'):
                stype = getattr(sig, 'signal_type')
                stype_name = getattr(stype, 'name', str(stype))
            else:
                stype_name = getattr(sig, 'name', str(sig))  # enum or string
            
            # Determine strength/confidence
            if hasattr(sig, 'strength') and isinstance(getattr(sig, 'strength'), (int, float)):
                strength_val = float(sig.strength)
            elif hasattr(result, 'strength') and isinstance(getattr(result, 'strength'), (int, float)):
                strength_val = float(result.strength)
            elif hasattr(result, 'confidence') and isinstance(getattr(result, 'confidence'), (int, float)):
                strength_val = float(result.confidence)
            else:
                strength_val = 1.0
            
            weight = (config.weight or 1.0) * max(0.0, min(strength_val, 1.0))
            
            if 'BUY' in stype_name.upper():
                buy_weight += weight
                contributing_indicators.append(f"{name}(BUY)")
            elif 'SELL' in stype_name.upper():
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
            if config.enabled and name in self.indicator_instances:
                enabled_count += 1
                total_weight += config.weight
                
                lname = name.lower()
                if lname in {"sma", "ema", "vwma", "vw_ema", "hull_ma"}:
                    by_type["trend"] += 1
                elif lname in {"rsi", "vw_rsi", "macd", "vw_macd", "stochastic"}:
                    by_type["momentum"] += 1
                elif lname in {"bollinger_bands", "atr", "vw_atr", "keltner_channels", "standard_deviation"}:
                    by_type["volatility"] += 1
                elif lname in {"vwap", "obv", "mfi"}:
                    by_type["volume"] += 1
                elif lname in {"candlestick_patterns", "pattern_strength_analysis"}:
                    by_type["patterns"] += 1
        
        return {
            "total_indicators": len(self.indicator_instances),
            "enabled_indicators": enabled_count,
            "total_weight": total_weight,
            "by_type": by_type,
            "volume_weighted": True,
            "concurrent_execution": True
        }


# Test and demonstration functions
async def test_indicator_manager():
    """Test the indicator manager with sample data"""
    
    logger.info("🧪 Testing Technical Indicator Manager (Consolidated)")
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