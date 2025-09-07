"""
Comprehensive Technical Indicators Library
Complete Suite of 80+ Technical Indicators + 25+ Candlestick Patterns

This unified library combines:
- Traditional Indicators (40+): Classic technical analysis indicators
- Volume-Weighted Indicators (30+): Enhanced with sophisticated volume weighting
- Advanced Oscillators (10+): Complex momentum and volatility indicators
- Candlestick Patterns (25+): Complete pattern recognition system

Categories:
1. Trend Indicators (25): Moving Averages, Ichimoku, PSAR, Linear Regression, etc.
2. Momentum Oscillators (20): RSI, Stochastic, MACD, CCI, Fisher Transform, etc.
3. Volatility Indicators (15): Bollinger Bands, ATR, Keltner, ADX, Historical Vol, etc.
4. Volume Indicators (20): VWAP, OBV, MFI, CMF, A/D Line, etc.
5. Candlestick Patterns (25+): Complete pattern recognition suite

Author: Vincent S. Pereira
Version: 3.0.0
Total Indicators: 80+
Total Patterns: 25+
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, List, Union, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import warnings
from datetime import datetime

# Import our enhanced components
from .base import (
    VolumeWeightedIndicator, IndicatorConfig, IndicatorResult, 
    IndicatorType, SignalType
)
from .unified_enhanced_indicators import (
    UnifiedEnhancedIndicators, EnhancedIndicatorResult, VolumeWeightingConfig,
    IndicatorCategory as EnhancedCategory, SignalType as EnhancedSignalType
)
from .institutional_volume_profile import (
    InstitutionalVolumeProfile, InstitutionalVolumeProfileResult, VolumeProfileType,
    ValueArea, LiquidityPool, OrderFlowImbalance, VolumeNode
)
from .candlestick_patterns import (
    EnhancedVolumeWeightedPatternDetector,
    VolumeWeightedPatternResult,
    create_enhanced_vw_pattern_detector
)
# Alias for backward compatibility
EnhancedPatternResult = VolumeWeightedPatternResult
AdvancedIndicatorResult = EnhancedIndicatorResult

warnings.filterwarnings('ignore')

class IndicatorCategory(Enum):
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    PATTERNS = "patterns"
    SUPPORT_RESISTANCE = "support_resistance"

@dataclass
class ComprehensiveIndicatorResult:
    """Enhanced result structure for comprehensive indicators"""
    indicator_name: str
    category: IndicatorCategory
    value: Union[float, pd.Series, np.ndarray, dict]
    signal: str  # BUY, SELL, NEUTRAL, STRONG_BUY, STRONG_SELL
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    volume_weighted: bool
    metadata: dict

class ComprehensiveIndicators:
    """Unified comprehensive indicators library with 100+ indicators"""
    
    def __init__(self, volume_weighting_config: Optional[VolumeWeightingConfig] = None):
        # Core unified enhanced systems
        self.unified_indicators = UnifiedEnhancedIndicators(volume_weighting_config)
        
        # Enhanced pattern detection
        self.pattern_detector = create_enhanced_vw_pattern_detector()
        
        # Institutional volume profile
        self.volume_profile = InstitutionalVolumeProfile(
            tick_size=0.01,
            value_area_percent=0.70,
            institutional_threshold=10000.0
        )
        
        # Configuration
        self.volume_weighting_config = volume_weighting_config or VolumeWeightingConfig()
    
    # ===========================================
    # VOLUME-WEIGHTED IMPLEMENTATIONS
    # ===========================================
    
    @staticmethod
    def vw_sma(price: pd.Series, volume: pd.Series, period: int = 20) -> IndicatorResult:
        """Volume Weighted Simple Moving Average"""
        price_volume = price * volume
        pv_sum = price_volume.rolling(window=period).sum()
        vol_sum = volume.rolling(window=period).sum()
        vw_sma = pv_sum / vol_sum
        
        signal = "BUY" if price.iloc[-1] > vw_sma.iloc[-1] else "SELL"
        strength = abs(price.iloc[-1] - vw_sma.iloc[-1]) / vw_sma.iloc[-1]
        
        return IndicatorResult(vw_sma, signal, min(strength, 1.0), 0.8, 
                             {"period": period, "volume_weighted": True})
    
    @staticmethod
    def vw_stochastic(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series,
                     k_period: int = 14, d_period: int = 3) -> IndicatorResult:
        """Volume Weighted Stochastic Oscillator"""
        # Calculate volume-weighted price levels
        vw_high = (high * volume).rolling(k_period).sum() / volume.rolling(k_period).sum()
        vw_low = (low * volume).rolling(k_period).sum() / volume.rolling(k_period).sum()
        vw_close = (close * volume).rolling(k_period).sum() / volume.rolling(k_period).sum()
        
        # Calculate volume-weighted stochastic
        lowest_low = vw_low.rolling(k_period).min()
        highest_high = vw_high.rolling(k_period).max()
        
        vw_k = 100 * (vw_close - lowest_low) / (highest_high - lowest_low)
        vw_d = vw_k.rolling(d_period).mean()
        
        if vw_k.iloc[-1] < 20:
            signal, strength = "STRONG_BUY", 0.9
        elif vw_k.iloc[-1] < 30:
            signal, strength = "BUY", 0.7
        elif vw_k.iloc[-1] > 80:
            signal, strength = "STRONG_SELL", 0.9
        elif vw_k.iloc[-1] > 70:
            signal, strength = "SELL", 0.7
        else:
            signal, strength = "NEUTRAL", 0.0
        
        return IndicatorResult(
            {"vw_k": vw_k, "vw_d": vw_d}, signal, strength, 0.85,
            {"k_period": k_period, "d_period": d_period, "volume_weighted": True}
        )
    
    # ===========================================
    # ENHANCED UNIFIED METHODS
    # ===========================================
    
    def calculate_enhanced_indicator(self, indicator_name: str, data: Dict[str, pd.Series]) -> EnhancedIndicatorResult:
        """Calculate enhanced indicator with institutional features"""
        return self.unified_indicators.calculate_indicator(indicator_name, data)
    
    def calculate_all_enhanced_indicators(self, data: Dict[str, pd.Series]) -> Dict[str, EnhancedIndicatorResult]:
        """Calculate all enhanced indicators"""
        return self.unified_indicators.calculate_all(data)
    
    def detect_enhanced_pattern(self, pattern_name: str, data: Dict[str, pd.Series], index: int = -1) -> EnhancedPatternResult:
        """Detect enhanced candlestick pattern with volume weighting"""
        return self.enhanced_patterns.detect_pattern(pattern_name, data, index)
    
    def detect_all_enhanced_patterns(self, data: Dict[str, pd.Series], index: int = -1) -> Dict[str, EnhancedPatternResult]:
        """Detect all enhanced patterns"""
        return self.enhanced_patterns.detect_all_patterns(data, index)
    
    def get_market_regime_analysis(self, data: Dict[str, pd.Series]) -> Dict[str, Any]:
        """Get comprehensive market regime analysis"""
        # Get market regime from unified indicators
        market_regime = self.unified_indicators.get_market_regime(data)
        
        # Get institutional signals from patterns
        institutional_signals = self.enhanced_patterns.get_institutional_signals(data)
        
        # Get strongest pattern
        strongest_pattern = self.enhanced_patterns.get_strongest_pattern(data)
        
        # Combine analysis
        return {
            "market_regime": market_regime.value,
            "institutional_signals": institutional_signals,
            "strongest_pattern": strongest_pattern.pattern_name if strongest_pattern else None,
            "pattern_confidence": strongest_pattern.confidence if strongest_pattern else 0.0,
            "smart_money_activity": institutional_signals.get("smart_money_score", 0.0)
        }
    
    def get_trading_signals(self, data: Dict[str, pd.Series]) -> Dict[str, Any]:
        """Get comprehensive trading signals"""
        # Calculate enhanced indicators
        enhanced_results = self.calculate_all_enhanced_indicators(data)
        
        # Detect patterns
        pattern_results = self.detect_all_enhanced_patterns(data)
        
        # Aggregate signals
        indicator_signals = [r.signal for r in enhanced_results.values()]
        pattern_signals = [r.pattern_type for r in pattern_results.values() if r.detected]
        
        # Count signal types
        buy_signals = sum(1 for s in indicator_signals if s in [EnhancedSignalType.BUY, EnhancedSignalType.STRONG_BUY])
        sell_signals = sum(1 for s in indicator_signals if s in [EnhancedSignalType.SELL, EnhancedSignalType.STRONG_SELL])
        
        # Calculate overall confidence
        confidences = [r.confidence for r in enhanced_results.values()]
        avg_confidence = np.mean(confidences) if confidences else 0.0
        
        # Determine overall signal
        if buy_signals > sell_signals * 1.5:
            overall_signal = "STRONG_BUY"
        elif buy_signals > sell_signals:
            overall_signal = "BUY"
        elif sell_signals > buy_signals * 1.5:
            overall_signal = "STRONG_SELL"
        elif sell_signals > buy_signals:
            overall_signal = "SELL"
        else:
            overall_signal = "NEUTRAL"
        
        return {
            "overall_signal": overall_signal,
            "confidence": avg_confidence,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "total_indicators": len(enhanced_results),
            "detected_patterns": len([r for r in pattern_results.values() if r.detected]),
            "market_analysis": self.get_market_regime_analysis(data)
        }
    
    def get_risk_metrics(self, data: Dict[str, pd.Series]) -> Dict[str, float]:
        """Calculate risk metrics for position sizing"""
        price = data['close']
        volume = data['volume']
        
        # Volatility metrics
        returns = price.pct_change().dropna()
        volatility = returns.std() * np.sqrt(252)  # Annualized
        
        # Volume-based risk
        volume_volatility = (volume / volume.rolling(20).mean()).std()
        
        # Smart money risk (high smart money activity = lower risk)
        enhanced_results = self.calculate_all_enhanced_indicators(data)
        smart_money_scores = [r.smart_money_flow for r in enhanced_results.values() if r.smart_money_flow]
        avg_smart_money = np.mean(smart_money_scores) if smart_money_scores else 0.0
        
        # Risk-adjusted metrics
        risk_score = (volatility * 0.6) + (volume_volatility * 0.3) - (avg_smart_money * 0.1)
        
        return {
            "price_volatility": volatility,
            "volume_volatility": volume_volatility,
            "smart_money_score": avg_smart_money,
            "overall_risk_score": max(0.0, min(1.0, risk_score)),
            "recommended_position_size": max(0.1, 1.0 - risk_score)  # Inverse relationship
        }
    
    def get_available_enhanced_indicators(self) -> List[str]:
        """Get list of available enhanced indicators"""
        return self.unified_indicators.get_available_indicators()
    
    def get_available_enhanced_patterns(self) -> List[str]:
        """Get list of available enhanced patterns"""
        return self.enhanced_patterns.get_available_patterns()
    
    def calculate_advanced_indicators(self, high: float, low: float, close: float, 
                                    volume: float, timestamp: datetime) -> Dict[str, AdvancedIndicatorResult]:
        """Calculate all advanced volume-weighted indicators"""
        return self.advanced_indicators.calculate_all(high, low, close, volume, timestamp)
    
    def calculate_support_resistance(self, high: float, low: float, close: float, 
                                   volume: float, timestamp: datetime) -> AdvancedIndicatorResult:
        """Calculate volume-weighted support and resistance levels"""
        return self.advanced_indicators.support_resistance.calculate(high, low, close, volume, timestamp)
    
    def calculate_vw_roc(self, price: float, volume: float, timestamp: datetime) -> AdvancedIndicatorResult:
        """Calculate Volume-Weighted Rate of Change"""
        return self.advanced_indicators.vw_roc.calculate(price, volume, timestamp)
    
    def calculate_vw_macd(self, price: float, volume: float, timestamp: datetime) -> AdvancedIndicatorResult:
        """Calculate Volume-Weighted MACD"""
        return self.advanced_indicators.vw_macd.calculate(price, volume, timestamp)
    
    def detect_smart_money_flow(self, high: float, low: float, close: float, 
                               volume: float, timestamp: datetime) -> AdvancedIndicatorResult:
        """Detect smart money flow patterns"""
        return self.advanced_indicators.smart_money.calculate(high, low, close, volume, timestamp)
    
    def analyze_volume_profile(self, high: float, low: float, close: float, volume: float,
                              buy_volume: float = None, sell_volume: float = None,
                              timestamp: datetime = None) -> InstitutionalVolumeProfileResult:
        """Analyze institutional volume profile"""
        return self.volume_profile.update(high, low, close, volume, buy_volume, sell_volume, timestamp=timestamp)
    
    def get_market_regime_analysis(self, high: float, low: float, close: float, 
                                  volume: float, timestamp: datetime) -> Dict[str, Any]:
        """Get comprehensive market regime analysis"""
        # Calculate advanced indicators
        advanced_results = self.calculate_advanced_indicators(high, low, close, volume, timestamp)
        
        # Get market regime from advanced indicators
        market_regime = self.advanced_indicators.get_market_regime(advanced_results)
        
        # Get trading recommendation
        trading_recommendation = self.advanced_indicators.get_trading_recommendation(advanced_results)
        
        # Analyze volume profile
        volume_profile_result = self.analyze_volume_profile(high, low, close, volume, timestamp=timestamp)
        
        return {
            "market_regime": market_regime.value,
            "trading_recommendation": trading_recommendation,
            "advanced_indicators": {
                name: {
                    "signal": result.signal,
                    "confidence": result.confidence,
                    "strength": result.strength,
                    "value": result.value
                } for name, result in advanced_results.items()
            },
            "volume_profile": {
                "poc": volume_profile_result.value_area.point_of_control,
                "value_area_high": volume_profile_result.value_area.value_area_high,
                "value_area_low": volume_profile_result.value_area.value_area_low,
                "vwap": volume_profile_result.vwap,
                "twap": volume_profile_result.twap,
                "market_efficiency": volume_profile_result.market_efficiency,
                "institutional_activity": volume_profile_result.institutional_activity_score,
                "smart_money_flow": volume_profile_result.smart_money_flow,
                "liquidity_pools_count": len(volume_profile_result.liquidity_pools)
            },
            "timestamp": timestamp
        }
    
    def get_liquidity_analysis(self, price: float) -> Dict[str, Any]:
        """Get liquidity analysis at specific price level"""
        liquidity_at_price = self.volume_profile.get_liquidity_at_price(price)
        support_resistance = self.volume_profile.get_support_resistance_levels()
        
        return {
            "liquidity_at_price": liquidity_at_price,
            "support_levels": support_resistance.get('support', []),
            "resistance_levels": support_resistance.get('resistance', []),
            "nearest_support": max([s for s in support_resistance.get('support', []) if s < price], default=None),
            "nearest_resistance": min([r for r in support_resistance.get('resistance', []) if r > price], default=None)
        }
    
    def get_comprehensive_analysis(self, high: float, low: float, close: float, 
                                  volume: float, timestamp: datetime = None) -> Dict[str, Any]:
        """Get comprehensive analysis combining all indicator types"""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Traditional indicators
        traditional_results = {}
        try:
            traditional_results['sma_20'] = self.sma(close, 20)
            traditional_results['ema_20'] = self.ema(close, 20)
            traditional_results['rsi_14'] = self.rsi(close, 14)
            traditional_results['macd'] = self.macd(close)
        except Exception as e:
            traditional_results['error'] = str(e)
        
        # Enhanced indicators
        enhanced_results = {}
        try:
            enhanced_results = self.calculate_all_enhanced_indicators(high, low, close, volume, timestamp)
        except Exception as e:
            enhanced_results['error'] = str(e)
        
        # Advanced indicators
        advanced_results = {}
        try:
            advanced_results = self.calculate_advanced_indicators(high, low, close, volume, timestamp)
        except Exception as e:
            advanced_results['error'] = str(e)
        
        # Volume profile
        volume_profile_result = None
        try:
            volume_profile_result = self.analyze_volume_profile(high, low, close, volume, timestamp=timestamp)
        except Exception as e:
            volume_profile_result = {'error': str(e)}
        
        # Market regime analysis
        market_analysis = {}
        try:
            market_analysis = self.get_market_regime_analysis(high, low, close, volume, timestamp)
        except Exception as e:
            market_analysis['error'] = str(e)
        
        # Liquidity analysis
        liquidity_analysis = {}
        try:
            liquidity_analysis = self.get_liquidity_analysis(close)
        except Exception as e:
            liquidity_analysis['error'] = str(e)
        
        return {
            "timestamp": timestamp,
            "price_data": {
                "high": high,
                "low": low,
                "close": close,
                "volume": volume
            },
            "traditional_indicators": traditional_results,
            "enhanced_indicators": enhanced_results,
            "advanced_indicators": advanced_results,
            "volume_profile": volume_profile_result,
            "market_analysis": market_analysis,
            "liquidity_analysis": liquidity_analysis
        }
    
    def get_available_advanced_indicators(self) -> List[str]:
        """Get list of available advanced indicators"""
        return self.advanced_indicators.get_available_indicators()
    
    def analyze_liquidity_pools(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze liquidity pools and order flow"""
        try:
            # Get institutional volume profile
            volume_profile = self.volume_profile.analyze_market_data(
                data['high'].values, data['low'].values, 
                data['close'].values, data['volume'].values
            )
            
            # Extract liquidity information
            liquidity_analysis = {
                'total_liquidity_pools': len(volume_profile.liquidity_pools),
                'major_liquidity_levels': [
                    {
                        'price': pool.price_level,
                        'volume': pool.total_volume,
                        'strength': pool.strength,
                        'type': pool.pool_type
                    }
                    for pool in volume_profile.liquidity_pools[:5]  # Top 5
                ],
                'order_flow_imbalances': [
                    {
                        'price': imbalance.price_level,
                        'ratio': imbalance.buy_sell_ratio,
                        'volume': imbalance.total_volume,
                        'direction': imbalance.direction
                    }
                    for imbalance in volume_profile.order_flow_imbalances[:3]  # Top 3
                ],
                'smart_money_activity': {
                    'footprint_score': volume_profile.smart_money_footprint.overall_score,
                    'institutional_bias': volume_profile.smart_money_footprint.institutional_bias,
                    'accumulation_zones': volume_profile.smart_money_footprint.accumulation_zones,
                    'distribution_zones': volume_profile.smart_money_footprint.distribution_zones
                }
            }
            
            return liquidity_analysis
            
        except Exception as e:
            return {
                'error': f'Liquidity analysis failed: {str(e)}',
                'total_liquidity_pools': 0,
                'major_liquidity_levels': [],
                'order_flow_imbalances': [],
                'smart_money_activity': {}
            }
    
    def detect_enhanced_candlestick_patterns(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Detect enhanced volume-weighted candlestick patterns"""
        try:
            # Detect all patterns
            patterns = self.vw_pattern_detector.detect_all_patterns(data)
            
            # Generate comprehensive summary
            summary = self.vw_pattern_detector.get_pattern_summary(patterns)
            
            # Extract recent patterns (last 10 periods)
            recent_patterns = []
            recent_indices = sorted(patterns.keys())[-10:] if patterns else []
            
            for idx in recent_indices:
                for pattern in patterns[idx]:
                    recent_patterns.append({
                        'index': idx,
                        'timestamp': data.index[idx] if hasattr(data.index, '__getitem__') else idx,
                        'pattern_name': pattern.pattern_name,
                        'pattern_type': pattern.pattern_type.value,
                        'confidence': pattern.confidence,
                        'strength': pattern.strength.value,
                        'volume_profile': pattern.volume_profile.value,
                        'smart_money_involvement': pattern.smart_money_involvement,
                        'institutional_bias': pattern.institutional_bias,
                        'risk_reward_ratio': pattern.risk_reward_ratio,
                        'target_price': pattern.target_price,
                        'stop_loss': pattern.stop_loss
                    })
            
            return {
                'total_patterns': summary['total_patterns'],
                'unique_patterns': summary['unique_patterns'],
                'institutional_grade_patterns': summary['institutional_grade_patterns'],
                'high_confidence_patterns': summary['high_confidence_patterns'],
                'average_confidence': summary['average_confidence'],
                'average_risk_reward': summary['average_risk_reward'],
                'recent_patterns': recent_patterns,
                'strongest_signals': [
                    {
                        'pattern_name': signal.pattern_name,
                        'confidence': signal.confidence,
                        'smart_money_score': signal.smart_money_involvement,
                        'institutional_bias': signal.institutional_bias,
                        'risk_reward': signal.risk_reward_ratio
                    }
                    for signal in summary['strongest_signals']
                ],
                'volume_profile_distribution': summary['volume_profile_distribution']
            }
            
        except Exception as e:
            return {
                'error': f'Pattern detection failed: {str(e)}',
                'total_patterns': 0,
                'recent_patterns': [],
                'strongest_signals': []
            }
    
    def get_pattern_based_signals(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Get trading signals based on enhanced candlestick patterns"""
        try:
            # Detect patterns
            patterns = self.vw_pattern_detector.detect_all_patterns(data)
            
            if not patterns:
                return {
                    'signal': 'NEUTRAL',
                    'confidence': 0.0,
                    'reasoning': 'No significant patterns detected',
                    'risk_metrics': {}
                }
            
            # Get most recent patterns
            latest_index = max(patterns.keys())
            latest_patterns = patterns[latest_index]
            
            # Find highest confidence pattern
            best_pattern = max(latest_patterns, key=lambda p: p.confidence * (1 + p.smart_money_involvement))
            
            # Determine overall signal
            if best_pattern.pattern_type.value in ['reversal_bullish', 'continuation_bullish', 'smart_money_entry']:
                signal = 'BUY'
            elif best_pattern.pattern_type.value in ['reversal_bearish', 'continuation_bearish', 'smart_money_exit']:
                signal = 'SELL'
            else:
                signal = 'NEUTRAL'
            
            # Adjust signal strength based on institutional involvement
            if best_pattern.institutional_bias == 'strong_bullish' and signal == 'BUY':
                signal = 'STRONG_BUY'
            elif best_pattern.institutional_bias == 'strong_bearish' and signal == 'SELL':
                signal = 'STRONG_SELL'
            
            return {
                'signal': signal,
                'confidence': best_pattern.confidence,
                'pattern_name': best_pattern.pattern_name,
                'smart_money_involvement': best_pattern.smart_money_involvement,
                'institutional_bias': best_pattern.institutional_bias,
                'volume_profile': best_pattern.volume_profile.value,
                'risk_reward_ratio': best_pattern.risk_reward_ratio,
                'target_price': best_pattern.target_price,
                'stop_loss': best_pattern.stop_loss,
                'reasoning': f'{best_pattern.pattern_name} detected with {best_pattern.confidence:.1%} confidence and {best_pattern.smart_money_involvement:.1%} smart money involvement',
                'risk_metrics': {
                    'pattern_reliability': best_pattern.pattern_reliability,
                    'risk_reward_ratio': best_pattern.risk_reward_ratio,
                    'stop_loss_distance': abs(data['close'].iloc[-1] - best_pattern.stop_loss) / data['close'].iloc[-1] if best_pattern.stop_loss else None,
                    'target_distance': abs(best_pattern.target_price - data['close'].iloc[-1]) / data['close'].iloc[-1] if best_pattern.target_price else None
                }
            }
            
        except Exception as e:
            return {
                'signal': 'NEUTRAL',
                'confidence': 0.0,
                'error': f'Pattern signal generation failed: {str(e)}',
                'risk_metrics': {}
            }
    
    @staticmethod
    def vw_bollinger_bands(price: pd.Series, volume: pd.Series, period: int = 20, std_dev: float = 2.0) -> IndicatorResult:
        """Volume Weighted Bollinger Bands"""
        # Calculate volume weighted moving average
        price_volume = price * volume
        pv_sum = price_volume.rolling(window=period).sum()
        vol_sum = volume.rolling(window=period).sum()
        vw_ma = pv_sum / vol_sum
        
        # Calculate volume weighted standard deviation
        vw_variance = ((price - vw_ma) ** 2 * volume).rolling(period).sum() / volume.rolling(period).sum()
        vw_std = np.sqrt(vw_variance)
        
        upper = vw_ma + (vw_std * std_dev)
        lower = vw_ma - (vw_std * std_dev)
        
        # %B calculation
        bb_percent = (price - lower) / (upper - lower)
        bandwidth = (upper - lower) / vw_ma
        
        if bb_percent.iloc[-1] > 1.0:
            signal, strength = "SELL", min((bb_percent.iloc[-1] - 1.0) * 2, 1.0)
        elif bb_percent.iloc[-1] < 0.0:
            signal, strength = "BUY", min(abs(bb_percent.iloc[-1]) * 2, 1.0)
        else:
            signal, strength = "NEUTRAL", 0.0
        
        return IndicatorResult(
            {"upper": upper, "middle": vw_ma, "lower": lower, "percent_b": bb_percent, "bandwidth": bandwidth},
            signal, strength, 0.85,
            {"period": period, "std_dev": std_dev, "volume_weighted": True}
        )
    
    @staticmethod
    def vw_williams_r(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 14) -> IndicatorResult:
        """Volume Weighted Williams %R"""
        # Calculate volume weighted high and low
        vw_high = (high * volume).rolling(period).sum() / volume.rolling(period).sum()
        vw_low = (low * volume).rolling(period).sum() / volume.rolling(period).sum()
        vw_close = (close * volume).rolling(period).sum() / volume.rolling(period).sum()
        
        highest_high = vw_high.rolling(period).max()
        lowest_low = vw_low.rolling(period).min()
        
        vw_williams_r = -100 * (highest_high - vw_close) / (highest_high - lowest_low)
        
        if vw_williams_r.iloc[-1] < -80:
            signal, strength = "STRONG_BUY", 0.9
        elif vw_williams_r.iloc[-1] < -50:
            signal, strength = "BUY", 0.6
        elif vw_williams_r.iloc[-1] > -20:
            signal, strength = "STRONG_SELL", 0.9
        else:
            signal, strength = "NEUTRAL", 0.0
        
        return IndicatorResult(vw_williams_r, signal, strength, 0.8, 
                             {"period": period, "volume_weighted": True})
    
    @staticmethod
    def vw_cci(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 20) -> IndicatorResult:
        """Volume Weighted Commodity Channel Index"""
        # Volume weighted typical price
        typical_price = (high + low + close) / 3
        vw_tp = (typical_price * volume).rolling(period).sum() / volume.rolling(period).sum()
        vw_tp_sma = vw_tp.rolling(period).mean()
        
        # Volume weighted mean deviation
        vw_mean_dev = (abs(vw_tp - vw_tp_sma) * volume).rolling(period).sum() / volume.rolling(period).sum()
        
        vw_cci = (vw_tp - vw_tp_sma) / (0.015 * vw_mean_dev)
        
        if vw_cci.iloc[-1] > 200:
            signal, strength = "STRONG_SELL", 0.9
        elif vw_cci.iloc[-1] > 100:
            signal, strength = "SELL", 0.7
        elif vw_cci.iloc[-1] < -200:
            signal, strength = "STRONG_BUY", 0.9
        elif vw_cci.iloc[-1] < -100:
            signal, strength = "BUY", 0.7
        else:
            signal, strength = "NEUTRAL", 0.0
        
        return IndicatorResult(vw_cci, signal, strength, 0.8, 
                             {"period": period, "volume_weighted": True})
    
    # ===========================================
    # MASTER INDICATOR CALCULATION METHOD
    # ===========================================
    
    def calculate_all_indicators(self, data: Dict[str, pd.Series], 
                               include_patterns: bool = True,
                               include_volume_weighted: bool = True) -> Dict[str, ComprehensiveIndicatorResult]:
        """
        Calculate all available indicators
        
        Args:
            data: Dictionary containing 'open', 'high', 'low', 'close', 'volume' Series
            include_patterns: Whether to include candlestick patterns
            include_volume_weighted: Whether to include volume-weighted variants
        
        Returns:
            Dictionary of all calculated indicators
        """
        results = {}
        
        # Extract data series
        open_data = data['open']
        high_data = data['high'] 
        low_data = data['low']
        close_data = data['close']
        volume_data = data['volume']
        
        # ===========================================
        # TREND INDICATORS
        # ===========================================
        
        # Traditional Moving Averages
        sma_result = self.traditional_indicators.sma(close_data, 20)
        results['sma_20'] = ComprehensiveIndicatorResult(
            "Simple Moving Average (20)", IndicatorCategory.TREND, sma_result.value,
            sma_result.signal, sma_result.strength, 0.7, False, sma_result.metadata
        )
        
        ema_result = self.traditional_indicators.ema(close_data, 20)
        results['ema_20'] = ComprehensiveIndicatorResult(
            "Exponential Moving Average (20)", IndicatorCategory.TREND, ema_result.value,
            ema_result.signal, ema_result.strength, 0.75, False, ema_result.metadata
        )
        
        # Enhanced Moving Averages
        kama_result = self.enhanced_indicators.adaptive_moving_average(close_data, 20)
        results['kama_20'] = ComprehensiveIndicatorResult(
            "Kaufman Adaptive MA (20)", IndicatorCategory.TREND, kama_result.value,
            kama_result.signal, kama_result.strength, kama_result.confidence, False, kama_result.metadata
        )
        
        dema_result = self.enhanced_indicators.double_exponential_ma(close_data, 21)
        results['dema_21'] = ComprehensiveIndicatorResult(
            "Double Exponential MA (21)", IndicatorCategory.TREND, dema_result.value,
            dema_result.signal, dema_result.strength, dema_result.confidence, False, dema_result.metadata
        )
        
        hull_result = self.enhanced_indicators.hull_moving_average(close_data, 21)
        results['hull_21'] = ComprehensiveIndicatorResult(
            "Hull Moving Average (21)", IndicatorCategory.TREND, hull_result.value,
            hull_result.signal, hull_result.strength, hull_result.confidence, False, hull_result.metadata
        )
        
        # Volume-Weighted Trend Indicators
        if include_volume_weighted:
            vwma_result = self.traditional_indicators.vwma(close_data, volume_data, 20)
            results['vwma_20'] = ComprehensiveIndicatorResult(
                "Volume Weighted MA (20)", IndicatorCategory.TREND, vwma_result.value,
                vwma_result.signal, vwma_result.strength, 0.8, True, vwma_result.metadata
            )
            
            vw_ema_result = self.traditional_indicators.vw_ema(close_data, volume_data, 20)
            results['vw_ema_20'] = ComprehensiveIndicatorResult(
                "Volume Weighted EMA (20)", IndicatorCategory.TREND, vw_ema_result.value,
                vw_ema_result.signal, vw_ema_result.strength, 0.85, True, vw_ema_result.metadata
            )
            
            vw_sma_result = self.vw_sma(close_data, volume_data, 20)
            results['vw_sma_20'] = ComprehensiveIndicatorResult(
                "Volume Weighted SMA (20)", IndicatorCategory.TREND, vw_sma_result.value,
                vw_sma_result.signal, vw_sma_result.strength, vw_sma_result.confidence, True, vw_sma_result.metadata
            )
        
        # ===========================================
        # MOMENTUM INDICATORS
        # ===========================================
        
        # Traditional Momentum
        rsi_result = self.traditional_indicators.rsi(close_data, 14)
        results['rsi_14'] = ComprehensiveIndicatorResult(
            "Relative Strength Index (14)", IndicatorCategory.MOMENTUM, rsi_result.value,
            rsi_result.signal, rsi_result.strength, 0.8, False, rsi_result.metadata
        )
        
        macd_result = self.traditional_indicators.macd(close_data, 12, 26, 9)
        results['macd'] = ComprehensiveIndicatorResult(
            "MACD (12,26,9)", IndicatorCategory.MOMENTUM, macd_result.value,
            macd_result.signal, macd_result.strength, 0.85, False, macd_result.metadata
        )
        
        # Enhanced Momentum
        stoch_result = self.enhanced_indicators.stochastic_oscillator(high_data, low_data, close_data, 14, 3, 3)
        results['stochastic'] = ComprehensiveIndicatorResult(
            "Stochastic Oscillator (14,3,3)", IndicatorCategory.MOMENTUM, stoch_result.value,
            stoch_result.signal, stoch_result.strength, stoch_result.confidence, False, stoch_result.metadata
        )
        
        williams_result = self.enhanced_indicators.williams_percent_r(high_data, low_data, close_data, 14)
        results['williams_r'] = ComprehensiveIndicatorResult(
            "Williams %R (14)", IndicatorCategory.MOMENTUM, williams_result.value,
            williams_result.signal, williams_result.strength, williams_result.confidence, False, williams_result.metadata
        )
        
        cci_result = self.enhanced_indicators.commodity_channel_index(high_data, low_data, close_data, 20)
        results['cci'] = ComprehensiveIndicatorResult(
            "Commodity Channel Index (20)", IndicatorCategory.MOMENTUM, cci_result.value,
            cci_result.signal, cci_result.strength, cci_result.confidence, False, cci_result.metadata
        )
        
        # Volume-Weighted Momentum
        if include_volume_weighted:
            vw_rsi_result = self.traditional_indicators.vw_rsi(close_data, volume_data, 14)
            results['vw_rsi_14'] = ComprehensiveIndicatorResult(
                "Volume Weighted RSI (14)", IndicatorCategory.MOMENTUM, vw_rsi_result.value,
                vw_rsi_result.signal, vw_rsi_result.strength, 0.85, True, vw_rsi_result.metadata
            )
            
            vw_macd_result = self.traditional_indicators.vw_macd(close_data, volume_data, 12, 26, 9)
            results['vw_macd'] = ComprehensiveIndicatorResult(
                "Volume Weighted MACD (12,26,9)", IndicatorCategory.MOMENTUM, vw_macd_result.value,
                vw_macd_result.signal, vw_macd_result.strength, 0.9, True, vw_macd_result.metadata
            )
            
            vw_stoch_result = self.vw_stochastic(high_data, low_data, close_data, volume_data, 14, 3)
            results['vw_stochastic'] = ComprehensiveIndicatorResult(
                "Volume Weighted Stochastic (14,3)", IndicatorCategory.MOMENTUM, vw_stoch_result.value,
                vw_stoch_result.signal, vw_stoch_result.strength, vw_stoch_result.confidence, True, vw_stoch_result.metadata
            )
        
        # ===========================================
        # VOLATILITY INDICATORS
        # ===========================================
        
        # Traditional Volatility
        bb_result = self.traditional_indicators.bollinger_bands(close_data, 20, 2.0)
        results['bollinger_bands'] = ComprehensiveIndicatorResult(
            "Bollinger Bands (20,2)", IndicatorCategory.VOLATILITY, bb_result.value,
            bb_result.signal, bb_result.strength, 0.8, False, bb_result.metadata
        )
        
        atr_result = self.traditional_indicators.atr(high_data, low_data, close_data, 14)
        results['atr_14'] = ComprehensiveIndicatorResult(
            "Average True Range (14)", IndicatorCategory.VOLATILITY, atr_result.value,
            atr_result.signal, atr_result.strength, 0.7, False, atr_result.metadata
        )
        
        # Enhanced Volatility
        keltner_result = self.volatility_volume_indicators.keltner_channels(high_data, low_data, close_data, 20, 2.0)
        results['keltner_channels'] = ComprehensiveIndicatorResult(
            "Keltner Channels (20,2)", IndicatorCategory.VOLATILITY, keltner_result.value,
            keltner_result.signal, keltner_result.strength, keltner_result.confidence, False, keltner_result.metadata
        )
        
        donchian_result = self.volatility_volume_indicators.donchian_channels(high_data, low_data, close_data, 20)
        results['donchian_channels'] = ComprehensiveIndicatorResult(
            "Donchian Channels (20)", IndicatorCategory.VOLATILITY, donchian_result.value,
            donchian_result.signal, donchian_result.strength, donchian_result.confidence, False, donchian_result.metadata
        )
        
        # Volume-Weighted Volatility
        if include_volume_weighted:
            vw_atr_result = self.traditional_indicators.vw_atr(high_data, low_data, close_data, volume_data, 14)
            results['vw_atr_14'] = ComprehensiveIndicatorResult(
                "Volume Weighted ATR (14)", IndicatorCategory.VOLATILITY, vw_atr_result.value,
                vw_atr_result.signal, vw_atr_result.strength, 0.85, True, vw_atr_result.metadata
            )
            
            vw_bb_result = self.vw_bollinger_bands(close_data, volume_data, 20, 2.0)
            results['vw_bollinger_bands'] = ComprehensiveIndicatorResult(
                "Volume Weighted Bollinger Bands (20,2)", IndicatorCategory.VOLATILITY, vw_bb_result.value,
                vw_bb_result.signal, vw_bb_result.strength, vw_bb_result.confidence, True, vw_bb_result.metadata
            )
        
        # ===========================================
        # VOLUME INDICATORS
        # ===========================================
        
        vwap_result = self.traditional_indicators.vwap(high_data, low_data, close_data, volume_data)
        results['vwap'] = ComprehensiveIndicatorResult(
            "Volume Weighted Average Price", IndicatorCategory.VOLUME, vwap_result.value,
            vwap_result.signal, vwap_result.strength, 0.9, True, vwap_result.metadata
        )
        
        obv_result = self.traditional_indicators.obv(close_data, volume_data)
        results['obv'] = ComprehensiveIndicatorResult(
            "On Balance Volume", IndicatorCategory.VOLUME, obv_result.value,
            obv_result.signal, obv_result.strength, 0.7, True, obv_result.metadata
        )
        
        # Enhanced Volume
        enhanced_vwap_result = self.volatility_volume_indicators.volume_weighted_average_price(high_data, low_data, close_data, volume_data)
        results['enhanced_vwap'] = ComprehensiveIndicatorResult(
            "Enhanced VWAP with Bands", IndicatorCategory.VOLUME, enhanced_vwap_result.value,
            enhanced_vwap_result.signal, enhanced_vwap_result.strength, enhanced_vwap_result.confidence, True, enhanced_vwap_result.metadata
        )
        
        mfi_result = self.volatility_volume_indicators.money_flow_index(high_data, low_data, close_data, volume_data, 14)
        results['mfi_14'] = ComprehensiveIndicatorResult(
            "Money Flow Index (14)", IndicatorCategory.VOLUME, mfi_result.value,
            mfi_result.signal, mfi_result.strength, mfi_result.confidence, True, mfi_result.metadata
        )
        
        # ===========================================
        # CANDLESTICK PATTERNS
        # ===========================================
        
        if include_patterns:
            try:
                # Create DataFrame for pattern analysis
                pattern_df = pd.DataFrame({
                    'open': open_data,
                    'high': high_data,
                    'low': low_data,
                    'close': close_data,
                    'volume': volume_data
                })
                
                # Detect all patterns
                patterns_dict = self.pattern_detector.detect_all_patterns(pattern_df)
                pattern_summary = self.pattern_detector.get_pattern_summary(patterns_dict)
                
                results['candlestick_patterns'] = ComprehensiveIndicatorResult(
                    "Candlestick Patterns Analysis", IndicatorCategory.PATTERNS, patterns_dict,
                    "NEUTRAL", 0.0, 0.8, False, pattern_summary
                )
                
                # Add individual strong patterns
                if pattern_summary.get('strongest_signals'):
                    for i, signal in enumerate(pattern_summary['strongest_signals'][:3]):  # Top 3
                        results[f'pattern_{i+1}'] = ComprehensiveIndicatorResult(
                            signal['pattern'], IndicatorCategory.PATTERNS, signal,
                            "BUY" if "bullish" in signal['type'] else "SELL" if "bearish" in signal['type'] else "NEUTRAL",
                            signal['strength'], signal['confidence'], False, 
                            {"pattern_type": signal['type'], "reliability": signal['reliability']}
                        )
                
            except Exception as e:
                print(f"Pattern analysis failed: {e}")
        
        return results
    
    def get_indicator_summary(self, results: Dict[str, ComprehensiveIndicatorResult]) -> Dict:
        """Generate comprehensive summary of all indicators"""
        
        summary = {
            "total_indicators": len(results),
            "by_category": {},
            "strong_signals": [],
            "volume_weighted_count": 0,
            "overall_sentiment": {"bullish": 0, "bearish": 0, "neutral": 0}
        }
        
        # Categorize and analyze
        for name, result in results.items():
            category = result.category.value
            if category not in summary["by_category"]:
                summary["by_category"][category] = 0
            summary["by_category"][category] += 1
            
            if result.volume_weighted:
                summary["volume_weighted_count"] += 1
            
            # Analyze signals
            if "BUY" in result.signal:
                summary["overall_sentiment"]["bullish"] += 1
            elif "SELL" in result.signal:
                summary["overall_sentiment"]["bearish"] += 1
            else:
                summary["overall_sentiment"]["neutral"] += 1
            
            # Collect strong signals
            if result.strength * result.confidence > 0.7:
                summary["strong_signals"].append({
                    "indicator": result.indicator_name,
                    "signal": result.signal,
                    "strength": result.strength,
                    "confidence": result.confidence,
                    "category": category,
                    "volume_weighted": result.volume_weighted
                })
        
        # Sort strong signals by strength
        summary["strong_signals"] = sorted(summary["strong_signals"], 
                                         key=lambda x: x["strength"] * x["confidence"], reverse=True)[:10]
        
        # Calculate overall sentiment
        total_signals = sum(summary["overall_sentiment"].values())
        if total_signals > 0:
            summary["sentiment_percentages"] = {
                "bullish": summary["overall_sentiment"]["bullish"] / total_signals * 100,
                "bearish": summary["overall_sentiment"]["bearish"] / total_signals * 100,
                "neutral": summary["overall_sentiment"]["neutral"] / total_signals * 100
            }
        
        return summary