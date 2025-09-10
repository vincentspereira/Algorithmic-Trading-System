"""Risk management system for candlestick pattern trading.

This module provides sophisticated risk management capabilities including:
- Pattern-specific risk calculations
- Dynamic stop-loss and target calculations
- Market regime-aware adjustments
- Trailing stop mechanisms
- Multiple target levels
"""

from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np
from .pattern_base import (
    PatternType, RiskManagementParameters, MarketRegime,
    VolumeWeightedPatternResult
)

class IntegratedRiskManagementFactory:
    """Institutional-grade risk management factory for candlestick patterns"""
    
    def __init__(self, 
                 base_risk_percent: float = 0.02,
                 min_risk_reward: float = 1.5,
                 max_risk_percent: float = 0.05,
                 volatility_lookback: int = 20,
                 enable_trailing_stops: bool = True,
                 enable_multiple_targets: bool = True,
                 market_regime_sensitivity: float = 0.3):
        self.base_risk_percent = base_risk_percent
        self.min_risk_reward = min_risk_reward
        self.max_risk_percent = max_risk_percent
        self.volatility_lookback = volatility_lookback
        self.enable_trailing_stops = enable_trailing_stops
        self.enable_multiple_targets = enable_multiple_targets
        self.market_regime_sensitivity = market_regime_sensitivity
        
        # Pattern-specific risk multipliers (expanded)
        self.pattern_risk_multipliers = {
            'hammer': 1.0, 'shooting_star': 1.0, 'doji': 0.8,
            'engulfing': 1.2, 'harami': 0.9, 'piercing_line': 1.1,
            'dark_cloud_cover': 1.1, 'morning_star': 1.3, 'evening_star': 1.3,
            'three_white_soldiers': 1.4, 'three_black_crows': 1.4,
            'marubozu': 1.1, 'spinning_top': 0.7, 'inverted_hammer': 0.9,
            'hanging_man': 1.0, 'tweezer': 0.8, 'abandoned_baby': 1.5,
            'belt_hold': 1.2, 'kicking': 1.6, 'mat_hold': 1.3,
            'rising_three_methods': 1.1, 'falling_three_methods': 1.1
        }
        
        # Market regime multipliers
        self.regime_multipliers = {
            'bull_market': 0.8,  # Lower risk in bull markets
            'bear_market': 1.3,  # Higher risk in bear markets
            'sideways': 1.0,     # Normal risk in sideways markets
            'high_volatility': 1.4,
            'low_volatility': 0.9
        }
    
    def calculate_risk_parameters(self, 
                                pattern_result: VolumeWeightedPatternResult,
                                data: pd.DataFrame,
                                index: int,
                                account_balance: float = 100000) -> RiskManagementParameters:
        """Calculate comprehensive risk management parameters for a detected pattern"""
        
        # Get pattern-specific adjustments
        pattern_multiplier = self.pattern_risk_multipliers.get(pattern_result.pattern_name, 1.0)
        
        # Calculate volatility adjustment
        volatility_adj = self._calculate_volatility_adjustment(data, index)
        
        # Calculate volume adjustment
        volume_adj = self._calculate_volume_adjustment(pattern_result.volume_ratio)
        
        # Calculate smart money adjustment
        smart_money_adj = self._calculate_smart_money_adjustment(
            pattern_result.smart_money_detected,
            pattern_result.institutional_activity
        )
        
        # Enhanced stop-loss calculation
        stop_loss = self._calculate_enhanced_stop_loss(
            data, index, pattern_result, volatility_adj
        )
        
        # Multiple target levels
        target_levels = self._calculate_multiple_targets(
            data, index, pattern_result, volatility_adj
        )
        primary_target = target_levels[0] if target_levels else pattern_result.target_price
        
        # Trailing stop parameters
        trailing_params = self._calculate_trailing_stop_parameters(
            pattern_result, volatility_adj
        ) if self.enable_trailing_stops else None
        
        # Calculate final risk metrics
        entry_price = pattern_result.entry_price
        risk_per_share = abs(entry_price - stop_loss)
        risk_reward_ratio = abs(primary_target - entry_price) / risk_per_share if risk_per_share > 0 else 0
        
        # Position sizing
        max_risk_amount = account_balance * self.max_risk_percent
        position_size_multiplier = min(
            max_risk_amount / (risk_per_share * 100),  # Assuming 100 shares base
            pattern_multiplier * pattern_result.confidence
        )
        
        return RiskManagementParameters(
            pattern_name=pattern_result.pattern_name,
            pattern_type=pattern_result.pattern_type,
            confidence=pattern_result.confidence,
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=primary_target,
            risk_reward_ratio=risk_reward_ratio,
            max_risk_percent=self.max_risk_percent,
            position_size_multiplier=position_size_multiplier,
            volatility_adjustment=volatility_adj,
            volume_adjustment=volume_adj,
            smart_money_adjustment=smart_money_adj
        )
    
    def _calculate_enhanced_stop_loss(self, 
                                    data: pd.DataFrame, 
                                    index: int, 
                                    pattern_result: VolumeWeightedPatternResult,
                                    volatility_adj: float) -> float:
        """Calculate enhanced stop-loss using multiple methods"""
        
        # Method 1: ATR-based stop
        atr_stop = self._calculate_atr_based_stop(data, index, pattern_result, volatility_adj)
        
        # Method 2: Support/Resistance based stop
        sr_stop = self._calculate_support_resistance_stop(data, index, pattern_result)
        
        # Method 3: Pattern-specific stop
        pattern_stop = self._calculate_pattern_specific_stop(data, index, pattern_result)
        
        # Method 4: Volatility-adjusted stop
        vol_stop = self._calculate_volatility_adjusted_stop(data, index, pattern_result, volatility_adj)
        
        # Choose the most conservative (closest to entry) stop
        entry_price = pattern_result.entry_price
        is_bullish = pattern_result.pattern_type in [PatternType.REVERSAL] and entry_price > data.iloc[index]['close']
        
        if is_bullish:
            # For bullish patterns, choose the highest stop (closest to entry)
            return max(atr_stop, sr_stop, pattern_stop, vol_stop)
        else:
            # For bearish patterns, choose the lowest stop (closest to entry)
            return min(atr_stop, sr_stop, pattern_stop, vol_stop)
    
    def _calculate_atr_based_stop(self, 
                                data: pd.DataFrame, 
                                index: int, 
                                pattern_result: VolumeWeightedPatternResult,
                                volatility_adj: float) -> float:
        """Calculate ATR-based stop loss"""
        atr = self._calculate_atr(data, index, period=14)
        multiplier = 2.0 + volatility_adj  # Dynamic ATR multiplier
        
        entry_price = pattern_result.entry_price
        is_bullish = entry_price > data.iloc[index]['close']
        
        if is_bullish:
            return entry_price - (atr * multiplier)
        else:
            return entry_price + (atr * multiplier)
    
    def _calculate_support_resistance_stop(self, 
                                         data: pd.DataFrame, 
                                         index: int, 
                                         pattern_result: VolumeWeightedPatternResult) -> float:
        """Calculate stop based on nearby support/resistance levels"""
        lookback = min(50, index)
        if lookback < 10:
            return pattern_result.entry_price * 0.98  # Fallback 2% stop
        
        # Find recent highs and lows
        recent_data = data.iloc[max(0, index-lookback):index+1]
        highs = recent_data['high'].values
        lows = recent_data['low'].values
        
        # Identify support and resistance levels
        resistance_levels = self._find_resistance_levels(highs)
        support_levels = self._find_support_levels(lows)
        
        entry_price = pattern_result.entry_price
        is_bullish = entry_price > data.iloc[index]['close']
        
        if is_bullish:
            # Find nearest support below entry
            valid_supports = [s for s in support_levels if s < entry_price]
            return max(valid_supports) if valid_supports else entry_price * 0.97
        else:
            # Find nearest resistance above entry
            valid_resistances = [r for r in resistance_levels if r > entry_price]
            return min(valid_resistances) if valid_resistances else entry_price * 1.03
    
    def _calculate_pattern_specific_stop(self, 
                                       data: pd.DataFrame, 
                                       index: int, 
                                       pattern_result: VolumeWeightedPatternResult) -> float:
        """Calculate pattern-specific stop loss"""
        entry_price = pattern_result.entry_price
        pattern_name = pattern_result.pattern_name
        
        # Pattern-specific stop calculations
        if 'hammer' in pattern_name or 'shooting_star' in pattern_name:
            # Use the low/high of the hammer/shooting star candle
            candle = data.iloc[index]
            return candle['low'] if 'hammer' in pattern_name else candle['high']
        
        elif 'engulfing' in pattern_name:
            # Use the low/high of the engulfed candle
            if index > 0:
                prev_candle = data.iloc[index-1]
                return prev_candle['low'] if 'bullish' in pattern_name else prev_candle['high']
        
        elif 'doji' in pattern_name:
            # Conservative stop for doji patterns
            return entry_price * 0.985 if entry_price > data.iloc[index]['close'] else entry_price * 1.015
        
        # Default pattern stop
        return entry_price * 0.98 if entry_price > data.iloc[index]['close'] else entry_price * 1.02
    
    def _calculate_volatility_adjusted_stop(self, 
                                          data: pd.DataFrame, 
                                          index: int, 
                                          pattern_result: VolumeWeightedPatternResult,
                                          volatility_adj: float) -> float:
        """Calculate volatility-adjusted stop loss"""
        entry_price = pattern_result.entry_price
        
        # Base stop percentage adjusted by volatility
        base_stop_pct = 0.02  # 2% base stop
        adjusted_stop_pct = base_stop_pct * (1 + volatility_adj)
        
        is_bullish = entry_price > data.iloc[index]['close']
        
        if is_bullish:
            return entry_price * (1 - adjusted_stop_pct)
        else:
            return entry_price * (1 + adjusted_stop_pct)
    
    def _calculate_multiple_targets(self, 
                                  data: pd.DataFrame, 
                                  index: int, 
                                  pattern_result: VolumeWeightedPatternResult,
                                  volatility_adj: float) -> List[float]:
        """Calculate multiple target levels"""
        if not self.enable_multiple_targets:
            return [pattern_result.target_price] if pattern_result.target_price else []
        
        entry_price = pattern_result.entry_price
        atr = self._calculate_atr(data, index, period=14)
        
        # Calculate multiple targets based on ATR and Fibonacci levels
        fib_levels = [1.0, 1.618, 2.618, 4.236]  # Fibonacci extension levels
        targets = []
        
        is_bullish = entry_price > data.iloc[index]['close']
        direction = 1 if is_bullish else -1
        
        for fib in fib_levels:
            target = entry_price + (direction * atr * fib * (1 + volatility_adj))
            targets.append(target)
        
        return targets
    
    def _calculate_trailing_stop_parameters(self, 
                                          pattern_result: VolumeWeightedPatternResult,
                                          volatility_adj: float) -> Dict[str, float]:
        """Calculate trailing stop parameters"""
        
        # Base trailing stop percentage
        base_trailing_pct = 0.03  # 3% base trailing stop
        
        # Adjust based on pattern confidence and volatility
        confidence_adj = pattern_result.confidence * 0.5  # Higher confidence = tighter trailing
        trailing_pct = base_trailing_pct * (1 - confidence_adj + volatility_adj)
        
        return {
            'trailing_stop_pct': trailing_pct,
            'activation_pct': trailing_pct * 2,  # Activate after 2x the trailing distance
            'step_size': trailing_pct * 0.25     # Move in 25% increments
        }
    
    def _detect_market_regime(self, data: pd.DataFrame, index: int) -> MarketRegime:
        """Detect current market regime"""
        if index < 50:
            return MarketRegime.SIDEWAYS
        
        # Calculate trend strength
        lookback = min(50, index)
        recent_data = data.iloc[index-lookback:index+1]
        
        # Simple trend detection using moving averages
        short_ma = recent_data['close'].rolling(10).mean().iloc[-1]
        long_ma = recent_data['close'].rolling(20).mean().iloc[-1]
        
        # Volatility measurement
        volatility = recent_data['close'].pct_change().std() * np.sqrt(252)
        
        # Regime classification
        if volatility > 0.3:  # High volatility threshold
            return MarketRegime.HIGH_VOLATILITY
        elif volatility < 0.15:  # Low volatility threshold
            return MarketRegime.LOW_VOLATILITY
        elif short_ma > long_ma * 1.02:  # Strong uptrend
            return MarketRegime.BULL_MARKET
        elif short_ma < long_ma * 0.98:  # Strong downtrend
            return MarketRegime.BEAR_MARKET
        else:
            return MarketRegime.SIDEWAYS
    
    def _find_support_levels(self, lows: np.ndarray) -> List[float]:
        """Find support levels from price lows"""
        if len(lows) < 5:
            return []
        
        # Simple support detection using local minima
        supports = []
        for i in range(2, len(lows) - 2):
            if (lows[i] <= lows[i-1] and lows[i] <= lows[i-2] and 
                lows[i] <= lows[i+1] and lows[i] <= lows[i+2]):
                supports.append(lows[i])
        
        return sorted(set(supports))  # Remove duplicates and sort
    
    def _find_resistance_levels(self, highs: np.ndarray) -> List[float]:
        """Find resistance levels from price highs"""
        if len(highs) < 5:
            return []
        
        # Simple resistance detection using local maxima
        resistances = []
        for i in range(2, len(highs) - 2):
            if (highs[i] >= highs[i-1] and highs[i] >= highs[i-2] and 
                highs[i] >= highs[i+1] and highs[i] >= highs[i+2]):
                resistances.append(highs[i])
        
        return sorted(set(resistances))  # Remove duplicates and sort
    
    def _calculate_volume_adjustment(self, volume_ratio: float) -> float:
        """Calculate volume-based risk adjustment"""
        if volume_ratio > 3.0:  # High volume
            return -0.2  # Reduce risk
        elif volume_ratio < 0.5:  # Low volume
            return 0.3   # Increase risk
        else:
            return 0.0   # Normal risk
    
    def _calculate_smart_money_adjustment(self, 
                                        smart_money_detected: bool, 
                                        institutional_activity: bool) -> float:
        """Calculate smart money flow adjustment"""
        adjustment = 0.0
        
        if smart_money_detected:
            adjustment -= 0.15  # Reduce risk when smart money is detected
        
        if institutional_activity:
            adjustment -= 0.1   # Further reduce risk for institutional activity
        
        return adjustment
    
    def _is_at_key_level(self, price: float, data: pd.DataFrame, index: int, 
                        tolerance: float = 0.002) -> bool:
        """Check if price is at a key support/resistance level"""
        if index < 20:
            return False
        
        # Look for nearby significant levels
        lookback_data = data.iloc[max(0, index-50):index]
        
        # Check against recent highs and lows
        recent_highs = lookback_data['high'].nlargest(5)
        recent_lows = lookback_data['low'].nsmallest(5)
        
        for level in list(recent_highs) + list(recent_lows):
            if abs(price - level) / level <= tolerance:
                return True
        
        return False
    
    def _calculate_atr(self, data: pd.DataFrame, index: int, period: int = 14) -> float:
        """Calculate Average True Range"""
        if index < period:
            return 0.01  # Default small ATR
        
        start_idx = max(0, index - period + 1)
        atr_data = data.iloc[start_idx:index+1].copy()
        
        # Calculate True Range
        atr_data['prev_close'] = atr_data['close'].shift(1)
        atr_data['tr1'] = atr_data['high'] - atr_data['low']
        atr_data['tr2'] = abs(atr_data['high'] - atr_data['prev_close'])
        atr_data['tr3'] = abs(atr_data['low'] - atr_data['prev_close'])
        atr_data['true_range'] = atr_data[['tr1', 'tr2', 'tr3']].max(axis=1)
        
        # Calculate ATR as simple moving average of True Range
        return atr_data['true_range'].mean()
    
    def _calculate_volatility_adjustment(self, data: pd.DataFrame, index: int) -> float:
        """Calculate volatility-based risk adjustment"""
        if index < self.volatility_lookback:
            return 0.0
        
        # Calculate recent volatility
        lookback_data = data.iloc[max(0, index - self.volatility_lookback):index+1]
        returns = lookback_data['close'].pct_change().dropna()
        
        if len(returns) < 5:
            return 0.0
        
        current_vol = returns.std() * np.sqrt(252)  # Annualized volatility
        
        # Compare to longer-term volatility
        long_lookback = min(100, index)
        if long_lookback > self.volatility_lookback:
            long_data = data.iloc[max(0, index - long_lookback):index+1]
            long_returns = long_data['close'].pct_change().dropna()
            historical_vol = long_returns.std() * np.sqrt(252)
        else:
            historical_vol = current_vol
        
        # Calculate volatility ratio
        vol_ratio = current_vol / historical_vol if historical_vol > 0 else 1.0
        
        # Higher volatility = higher risk adjustment
        return min((vol_ratio - 1.0) * 0.5, 0.3)