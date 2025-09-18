#!/usr/bin/env python3
"""
VIX Mean Reversion Strategy

Implements a sophisticated volatility mean reversion strategy that trades based on
VIX (Volatility Index) spikes and their statistical tendency to revert to historical
means. This strategy can be applied to VIX-related instruments or used as a signal
for equity market timing.

Key Features:
- Multi-timeframe VIX analysis with percentile-based signals
- Term structure analysis (VIX vs VIX9D, VIX vs VXV)
- Volatility regime detection and adaptation
- Contango/backwardation analysis for VIX futures
- Dynamic position sizing based on volatility levels
- Market stress detection using VIX spikes
- Integration with equity market signals
- Risk management adapted to volatility trading

Author: Algorithmic Trading System
Date: 2024
Version: 1.0
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, timedelta
from scipy import stats

# Import base strategy class and required modules
from ..core.base_strategy import BaseRetailStrategy
from ...core.risk_management import RiskParameters, PositionSizer
from ...core.market_regime import MarketRegimeDetector, MarketRegime
from ...indicators.technical_indicators import TechnicalIndicators
from ...indicators.candlestick_patterns import CandlestickPatterns
from ...core.signal_generator import Signal, SignalType, SignalStrength
from ...core.execution_engine import ExecutionIntent, OrderType
from ...core.performance_tracker import PerformanceMetrics


class VolatilityRegime(Enum):
    """Volatility regime classifications"""
    LOW = "low"           # VIX < 20th percentile
    NORMAL = "normal"     # VIX between 20th-80th percentile
    ELEVATED = "elevated" # VIX between 80th-95th percentile
    EXTREME = "extreme"   # VIX > 95th percentile


class VIXStructure(Enum):
    """VIX term structure states"""
    STEEP_CONTANGO = "steep_contango"       # VXV >> VIX (normal)
    CONTANGO = "contango"                   # VXV > VIX
    FLAT = "flat"                          # VXV ≈ VIX
    BACKWARDATION = "backwardation"        # VIX > VXV (stress)
    STEEP_BACKWARDATION = "steep_backwardation" # VIX >> VXV (crisis)


@dataclass
class VolatilitySignal:
    """Volatility-specific signal information"""
    vix_level: float
    vix_percentile: float
    vix_zscore: float
    term_structure: VIXStructure
    volatility_regime: VolatilityRegime
    mean_reversion_probability: float
    days_since_spike: int
    spike_magnitude: float


class VIXMeanReversionStrategy(BaseRetailStrategy):
    """
    VIX Mean Reversion Strategy Implementation
    
    This strategy implements sophisticated volatility mean reversion trading with:
    - Multi-timeframe VIX analysis and percentile-based signals
    - Term structure analysis for enhanced signal quality
    - Volatility regime detection and adaptive parameters
    - Market stress detection and crisis mode trading
    - Dynamic position sizing based on volatility levels
    """
    
    def __init__(self, 
                 symbol: str,
                 vix_symbol: str = "VIX",
                 vxv_symbol: str = "VXV",
                 vix9d_symbol: str = "VIX9D",
                 lookback_period: int = 252,
                 spike_threshold: float = 2.0,
                 reversion_threshold: float = 1.5,
                 max_days_to_revert: int = 10,
                 use_term_structure: bool = True,
                 trade_vix_directly: bool = False,
                 equity_hedge_mode: bool = True,
                 max_position_size: float = 0.20,
                 volatility_scaling: bool = True,
                 crisis_mode_threshold: float = 30.0,
                 **kwargs):
        """
        Initialize VIX Mean Reversion Strategy
        
        Args:
            symbol: Primary trading symbol (VIX ETF or equity index)
            vix_symbol: VIX symbol for volatility analysis
            vxv_symbol: VXV (3-month volatility) symbol
            vix9d_symbol: VIX9D (9-day volatility) symbol
            lookback_period: Period for percentile calculations
            spike_threshold: Z-score threshold for volatility spikes
            reversion_threshold: Z-score threshold for mean reversion signals
            max_days_to_revert: Maximum days to wait for reversion
            use_term_structure: Use VIX term structure analysis
            trade_vix_directly: Trade VIX ETFs directly vs use as market timing
            equity_hedge_mode: Use VIX signals for equity hedging
            max_position_size: Maximum position size
            volatility_scaling: Scale position size by volatility
            crisis_mode_threshold: VIX level for crisis mode activation
        """
        super().__init__(symbol, **kwargs)
        
        # Strategy parameters
        self.vix_symbol = vix_symbol
        self.vxv_symbol = vxv_symbol
        self.vix9d_symbol = vix9d_symbol
        self.lookback_period = lookback_period
        self.spike_threshold = spike_threshold
        self.reversion_threshold = reversion_threshold
        self.max_days_to_revert = max_days_to_revert
        self.use_term_structure = use_term_structure
        self.trade_vix_directly = trade_vix_directly
        self.equity_hedge_mode = equity_hedge_mode
        self.max_position_size = max_position_size
        self.volatility_scaling = volatility_scaling
        self.crisis_mode_threshold = crisis_mode_threshold
        
        # Initialize components
        self.technical_indicators = TechnicalIndicators()
        self.candlestick_patterns = CandlestickPatterns()
        self.market_regime_detector = MarketRegimeDetector()
        self.position_sizer = PositionSizer()
        
        # Strategy state
        self.current_regime = MarketRegime.NEUTRAL
        self.volatility_regime = VolatilityRegime.NORMAL
        self.vix_structure = VIXStructure.CONTANGO
        self.vix_history: List[float] = []
        self.spike_dates: List[datetime] = []
        self.crisis_mode = False
        
        # Performance tracking
        self.performance_metrics = PerformanceMetrics()
        
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def _generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """
        Pillar 1: Signal Generation & Augmentation
        
        Generate VIX mean reversion signals by analyzing volatility spikes,
        term structure, and statistical reversion probabilities.
        """
        if len(data) < self.lookback_period:
            return [self._create_neutral_signal()]
            
        signals = []
        
        try:
            # Get VIX data (assuming it's included in the data or available separately)
            vix_data = self._get_vix_data(data)
            if vix_data is None or len(vix_data) < 50:
                return [self._create_neutral_signal()]
            
            # Calculate VIX statistics
            vix_signal = self._analyze_vix_levels(vix_data)
            
            # Update volatility regime
            self._update_volatility_regime(vix_signal)
            
            # Calculate additional indicators for primary symbol
            sma_20 = self.technical_indicators.sma(data['close'], period=20)
            ema_50 = self.technical_indicators.ema(data['close'], period=50)
            rsi = self.technical_indicators.rsi(data['close'], period=14)
            atr = self.technical_indicators.atr(data, period=14)
            
            # Get current values
            current_price = data['close'].iloc[-1]
            current_rsi = rsi.iloc[-1]
            current_atr = atr.iloc[-1]
            current_sma_20 = sma_20.iloc[-1]
            current_ema_50 = ema_50.iloc[-1]
            
            # Generate primary signal based on VIX analysis
            primary_signal = self._generate_vix_signal(vix_signal, data, current_price)
            
            # Enhance signal with market context
            if primary_signal:
                # Add technical confirmation
                technical_confirmation = self._get_technical_confirmation(data, primary_signal.signal_type)
                
                # Adjust confidence based on technical alignment
                if technical_confirmation:
                    primary_signal.confidence = min(0.95, primary_signal.confidence * 1.2)
                else:
                    primary_signal.confidence = max(0.3, primary_signal.confidence * 0.8)
                
                # Add comprehensive metadata
                primary_signal.metadata.update({
                    'current_price': current_price,
                    'rsi': current_rsi,
                    'sma_20': current_sma_20,
                    'ema_50': current_ema_50,
                    'atr': current_atr,
                    'vix_level': vix_signal.vix_level,
                    'vix_percentile': vix_signal.vix_percentile,
                    'vix_zscore': vix_signal.vix_zscore,
                    'volatility_regime': vix_signal.volatility_regime.value,
                    'term_structure': vix_signal.term_structure.value,
                    'mean_reversion_probability': vix_signal.mean_reversion_probability,
                    'days_since_spike': vix_signal.days_since_spike,
                    'spike_magnitude': vix_signal.spike_magnitude,
                    'crisis_mode': self.crisis_mode,
                    'technical_confirmation': technical_confirmation,
                    'market_regime': self.current_regime.value
                })
                
                signals.append(primary_signal)
            else:
                signals.append(self._create_neutral_signal())
            
        except Exception as e:
            self.logger.error(f"Error generating signals: {e}")
            signals.append(self._create_neutral_signal())
            
        return signals
    
    def _get_vix_data(self, data: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        Get VIX data - in practice this would come from a separate data feed
        For now, we'll simulate VIX-like behavior or use a VIX column if available
        """
        try:
            # Check if VIX data is included in the main data
            if 'vix' in data.columns:
                vix_data = pd.DataFrame({
                    'vix': data['vix'],
                    'date': data.index
                })
                return vix_data
            
            # If no VIX data, simulate based on price volatility
            # This is a simplified approach - in practice, use real VIX data
            returns = data['close'].pct_change().dropna()
            rolling_vol = returns.rolling(window=20).std() * np.sqrt(252) * 100
            
            # Scale to VIX-like levels (typically 10-80 range)
            vix_proxy = rolling_vol * 1.5 + 10
            vix_proxy = np.clip(vix_proxy, 8, 80)
            
            vix_data = pd.DataFrame({
                'vix': vix_proxy,
                'date': data.index
            })
            
            return vix_data
            
        except Exception as e:
            self.logger.error(f"Error getting VIX data: {e}")
            return None
    
    def _analyze_vix_levels(self, vix_data: pd.DataFrame) -> VolatilitySignal:
        """
        Analyze VIX levels and calculate volatility statistics
        """
        try:
            current_vix = vix_data['vix'].iloc[-1]
            vix_series = vix_data['vix'].dropna()
            
            # Calculate percentile and z-score
            lookback_data = vix_series.iloc[-self.lookback_period:] if len(vix_series) >= self.lookback_period else vix_series
            
            vix_percentile = stats.percentileofscore(lookback_data, current_vix) / 100
            vix_mean = lookback_data.mean()
            vix_std = lookback_data.std()
            vix_zscore = (current_vix - vix_mean) / vix_std if vix_std > 0 else 0
            
            # Determine volatility regime
            if vix_percentile >= 0.95:
                vol_regime = VolatilityRegime.EXTREME
            elif vix_percentile >= 0.80:
                vol_regime = VolatilityRegime.ELEVATED
            elif vix_percentile <= 0.20:
                vol_regime = VolatilityRegime.LOW
            else:
                vol_regime = VolatilityRegime.NORMAL
            
            # Analyze term structure (simplified - would use actual VXV data)
            term_structure = self._analyze_term_structure(vix_data)
            
            # Calculate mean reversion probability
            reversion_prob = self._calculate_reversion_probability(current_vix, vix_percentile, vix_zscore, vol_regime)
            
            # Detect spikes and calculate days since last spike
            days_since_spike, spike_magnitude = self._analyze_volatility_spikes(vix_series)
            
            return VolatilitySignal(
                vix_level=current_vix,
                vix_percentile=vix_percentile,
                vix_zscore=vix_zscore,
                term_structure=term_structure,
                volatility_regime=vol_regime,
                mean_reversion_probability=reversion_prob,
                days_since_spike=days_since_spike,
                spike_magnitude=spike_magnitude
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing VIX levels: {e}")
            return VolatilitySignal(
                vix_level=20.0,
                vix_percentile=0.5,
                vix_zscore=0.0,
                term_structure=VIXStructure.CONTANGO,
                volatility_regime=VolatilityRegime.NORMAL,
                mean_reversion_probability=0.5,
                days_since_spike=10,
                spike_magnitude=0.0
            )
    
    def _analyze_term_structure(self, vix_data: pd.DataFrame) -> VIXStructure:
        """
        Analyze VIX term structure - simplified version
        In practice, this would use VIX, VIX9D, and VXV data
        """
        try:
            # Simplified term structure analysis
            # Calculate short-term vs medium-term volatility proxy
            vix_series = vix_data['vix']
            
            # Short-term volatility (5-day average)
            short_term_vol = vix_series.rolling(5).mean().iloc[-1]
            
            # Medium-term volatility (20-day average)
            medium_term_vol = vix_series.rolling(20).mean().iloc[-1]
            
            # Calculate structure ratio
            if pd.isna(short_term_vol) or pd.isna(medium_term_vol) or medium_term_vol == 0:
                return VIXStructure.CONTANGO
            
            structure_ratio = short_term_vol / medium_term_vol
            
            # Classify structure
            if structure_ratio > 1.15:
                return VIXStructure.STEEP_BACKWARDATION
            elif structure_ratio > 1.05:
                return VIXStructure.BACKWARDATION
            elif structure_ratio > 0.95:
                return VIXStructure.FLAT
            elif structure_ratio > 0.85:
                return VIXStructure.CONTANGO
            else:
                return VIXStructure.STEEP_CONTANGO
            
        except Exception as e:
            self.logger.error(f"Error analyzing term structure: {e}")
            return VIXStructure.CONTANGO
    
    def _calculate_reversion_probability(self, current_vix: float, percentile: float, 
                                       zscore: float, regime: VolatilityRegime) -> float:
        """
        Calculate probability of mean reversion based on VIX characteristics
        """
        try:
            # Base probability based on percentile
            if percentile >= 0.95:  # Extreme levels
                base_prob = 0.85
            elif percentile >= 0.80:  # Elevated levels
                base_prob = 0.70
            elif percentile <= 0.20:  # Low levels
                base_prob = 0.60  # Low VIX can stay low
            else:
                base_prob = 0.45  # Normal levels
            
            # Adjust for z-score magnitude
            zscore_adjustment = min(0.3, abs(zscore) * 0.1)
            if zscore > 0:  # Above mean
                base_prob += zscore_adjustment
            else:  # Below mean
                base_prob -= zscore_adjustment * 0.5  # Less penalty for low VIX
            
            # Regime-based adjustment
            regime_adjustments = {
                VolatilityRegime.EXTREME: 0.15,    # High reversion probability
                VolatilityRegime.ELEVATED: 0.10,   # Good reversion probability
                VolatilityRegime.NORMAL: 0.0,      # Neutral
                VolatilityRegime.LOW: -0.10        # Lower reversion probability
            }
            
            base_prob += regime_adjustments.get(regime, 0.0)
            
            # Term structure adjustment
            if self.vix_structure == VIXStructure.STEEP_BACKWARDATION:
                base_prob += 0.15  # Strong reversion signal
            elif self.vix_structure == VIXStructure.BACKWARDATION:
                base_prob += 0.10
            elif self.vix_structure == VIXStructure.STEEP_CONTANGO:
                base_prob -= 0.05  # Weaker reversion signal
            
            # Crisis mode adjustment
            if current_vix > self.crisis_mode_threshold:
                base_prob += 0.20  # Very high reversion probability in crisis
            
            return min(0.95, max(0.05, base_prob))
            
        except Exception as e:
            self.logger.error(f"Error calculating reversion probability: {e}")
            return 0.5
    
    def _analyze_volatility_spikes(self, vix_series: pd.Series) -> Tuple[int, float]:
        """
        Analyze volatility spikes and calculate time since last spike
        """
        try:
            if len(vix_series) < 20:
                return 10, 0.0
            
            # Calculate rolling statistics for spike detection
            rolling_mean = vix_series.rolling(20).mean()
            rolling_std = vix_series.rolling(20).std()
            
            # Detect spikes (z-score > threshold)
            z_scores = (vix_series - rolling_mean) / rolling_std
            spike_mask = z_scores > self.spike_threshold
            
            # Find most recent spike
            spike_indices = np.where(spike_mask)[0]
            
            if len(spike_indices) == 0:
                return len(vix_series), 0.0
            
            last_spike_idx = spike_indices[-1]
            days_since_spike = len(vix_series) - 1 - last_spike_idx
            spike_magnitude = z_scores.iloc[last_spike_idx]
            
            return days_since_spike, spike_magnitude
            
        except Exception as e:
            self.logger.error(f"Error analyzing volatility spikes: {e}")
            return 10, 0.0
    
    def _update_volatility_regime(self, vix_signal: VolatilitySignal) -> None:
        """
        Update volatility regime and crisis mode status
        """
        try:
            self.volatility_regime = vix_signal.volatility_regime
            self.vix_structure = vix_signal.term_structure
            
            # Update crisis mode
            previous_crisis_mode = self.crisis_mode
            self.crisis_mode = vix_signal.vix_level > self.crisis_mode_threshold
            
            # Log regime changes
            if hasattr(self, '_previous_vol_regime') and self._previous_vol_regime != self.volatility_regime:
                self.logger.info(f"Volatility regime changed from {self._previous_vol_regime.value} to {self.volatility_regime.value}")
            
            if previous_crisis_mode != self.crisis_mode:
                self.logger.info(f"Crisis mode {'activated' if self.crisis_mode else 'deactivated'} at VIX {vix_signal.vix_level:.1f}")
            
            self._previous_vol_regime = self.volatility_regime
            
        except Exception as e:
            self.logger.error(f"Error updating volatility regime: {e}")
    
    def _generate_vix_signal(self, vix_signal: VolatilitySignal, data: pd.DataFrame, current_price: float) -> Optional[Signal]:
        """
        Generate trading signal based on VIX analysis
        """
        try:
            # Determine signal type based on trading mode
            if self.trade_vix_directly:
                # Trading VIX ETFs directly
                signal_type = self._get_vix_etf_signal(vix_signal)
            elif self.equity_hedge_mode:
                # Using VIX for equity hedging signals
                signal_type = self._get_equity_hedge_signal(vix_signal)
            else:
                # Using VIX for market timing
                signal_type = self._get_market_timing_signal(vix_signal)
            
            if signal_type == SignalType.HOLD:
                return None
            
            # Calculate signal strength
            strength_score = 0
            
            # Mean reversion probability
            strength_score += vix_signal.mean_reversion_probability * 40
            
            # Volatility regime factor
            regime_scores = {
                VolatilityRegime.EXTREME: 35,     # Strong signals in extreme conditions
                VolatilityRegime.ELEVATED: 25,   # Good signals in elevated volatility
                VolatilityRegime.NORMAL: 10,     # Weaker signals in normal conditions
                VolatilityRegime.LOW: 5          # Weak signals in low volatility
            }
            strength_score += regime_scores.get(vix_signal.volatility_regime, 10)
            
            # Term structure factor
            structure_scores = {
                VIXStructure.STEEP_BACKWARDATION: 20,
                VIXStructure.BACKWARDATION: 15,
                VIXStructure.FLAT: 5,
                VIXStructure.CONTANGO: 0,
                VIXStructure.STEEP_CONTANGO: -5
            }
            strength_score += structure_scores.get(vix_signal.term_structure, 0)
            
            # Time since spike factor
            if vix_signal.days_since_spike <= 3:
                strength_score += 15  # Fresh spike
            elif vix_signal.days_since_spike <= 7:
                strength_score += 10  # Recent spike
            elif vix_signal.days_since_spike > self.max_days_to_revert:
                strength_score -= 10  # Old spike
            
            # Crisis mode bonus
            if self.crisis_mode:
                strength_score += 20
            
            # Convert to signal strength
            if strength_score >= 80:
                signal_strength = SignalStrength.STRONG
                confidence = min(0.9, strength_score / 100)
            elif strength_score >= 60:
                signal_strength = SignalStrength.MEDIUM
                confidence = min(0.75, strength_score / 100)
            else:
                signal_strength = SignalStrength.WEAK
                confidence = min(0.6, strength_score / 100)
            
            # Don't trade weak signals unless in crisis mode
            if signal_strength == SignalStrength.WEAK and not self.crisis_mode:
                return None
            
            return Signal(
                symbol=self.symbol,
                signal_type=signal_type,
                strength=signal_strength,
                confidence=confidence,
                timestamp=data.index[-1],
                metadata={
                    'signal_source': 'vix_mean_reversion',
                    'strength_score': strength_score,
                    'trading_mode': 'vix_etf' if self.trade_vix_directly else ('hedge' if self.equity_hedge_mode else 'timing')
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error generating VIX signal: {e}")
            return None
    
    def _get_vix_etf_signal(self, vix_signal: VolatilitySignal) -> SignalType:
        """
        Get signal for trading VIX ETFs directly (VXX, UVXY, etc.)
        """
        try:
            # VIX ETFs generally move opposite to VIX mean reversion
            # When VIX is high and likely to revert down, short VIX ETFs
            # When VIX is low and likely to spike up, long VIX ETFs
            
            if (vix_signal.volatility_regime in [VolatilityRegime.EXTREME, VolatilityRegime.ELEVATED] and
                vix_signal.mean_reversion_probability > 0.7):
                return SignalType.SELL  # Short VIX ETFs when VIX likely to fall
            
            elif (vix_signal.volatility_regime == VolatilityRegime.LOW and
                  vix_signal.vix_percentile < 0.3 and
                  vix_signal.term_structure in [VIXStructure.STEEP_CONTANGO, VIXStructure.CONTANGO]):
                return SignalType.BUY   # Long VIX ETFs when VIX likely to spike
            
            return SignalType.HOLD
            
        except Exception as e:
            self.logger.error(f"Error getting VIX ETF signal: {e}")
            return SignalType.HOLD
    
    def _get_equity_hedge_signal(self, vix_signal: VolatilitySignal) -> SignalType:
        """
        Get signal for equity hedging based on VIX
        """
        try:
            # High VIX suggests market stress - hedge equity positions
            # Low VIX suggests complacency - reduce hedges
            
            if (vix_signal.volatility_regime == VolatilityRegime.EXTREME or
                (vix_signal.volatility_regime == VolatilityRegime.ELEVATED and 
                 vix_signal.term_structure == VIXStructure.BACKWARDATION)):
                return SignalType.SELL  # Hedge/reduce equity exposure
            
            elif (vix_signal.volatility_regime == VolatilityRegime.LOW and
                  vix_signal.mean_reversion_probability < 0.4):
                return SignalType.BUY   # Increase equity exposure
            
            return SignalType.HOLD
            
        except Exception as e:
            self.logger.error(f"Error getting equity hedge signal: {e}")
            return SignalType.HOLD
    
    def _get_market_timing_signal(self, vix_signal: VolatilitySignal) -> SignalType:
        """
        Get signal for market timing based on VIX
        """
        try:
            # High VIX often marks market bottoms (contrarian signal)
            # Low VIX can indicate complacency (caution signal)
            
            if (vix_signal.volatility_regime == VolatilityRegime.EXTREME and
                vix_signal.mean_reversion_probability > 0.8):
                return SignalType.BUY   # Contrarian buy at extreme fear
            
            elif (vix_signal.volatility_regime == VolatilityRegime.ELEVATED and
                  vix_signal.days_since_spike <= 2 and
                  vix_signal.term_structure == VIXStructure.BACKWARDATION):
                return SignalType.BUY   # Buy after recent spike
            
            elif (vix_signal.volatility_regime == VolatilityRegime.LOW and
                  vix_signal.vix_percentile < 0.15):
                return SignalType.SELL  # Caution at extreme complacency
            
            return SignalType.HOLD
            
        except Exception as e:
            self.logger.error(f"Error getting market timing signal: {e}")
            return SignalType.HOLD
    
    def _get_technical_confirmation(self, data: pd.DataFrame, signal_type: SignalType) -> bool:
        """
        Get technical confirmation for VIX-based signals
        """
        try:
            # Calculate technical indicators
            rsi = self.technical_indicators.rsi(data['close'], period=14).iloc[-1]
            sma_20 = self.technical_indicators.sma(data['close'], period=20).iloc[-1]
            current_price = data['close'].iloc[-1]
            
            if signal_type == SignalType.BUY:
                # Look for oversold conditions or support
                return (rsi < 40 or current_price < sma_20 * 0.98)
            
            elif signal_type == SignalType.SELL:
                # Look for overbought conditions or resistance
                return (rsi > 60 or current_price > sma_20 * 1.02)
            
            return True  # Neutral for HOLD
            
        except Exception as e:
            self.logger.error(f"Error getting technical confirmation: {e}")
            return False
    
    def _calculate_risk_parameters(self, data: pd.DataFrame, signal: Signal) -> RiskParameters:
        """
        Pillar 2: Dynamic Risk & Money Management
        
        Calculate position size and risk parameters adapted for volatility trading.
        """
        try:
            # Get signal metadata
            metadata = signal.metadata
            current_price = metadata.get('current_price', data['close'].iloc[-1])
            vix_level = metadata.get('vix_level', 20.0)
            volatility_regime = metadata.get('volatility_regime', 'normal')
            crisis_mode = metadata.get('crisis_mode', False)
            
            # Base position size
            base_size = self.max_position_size
            
            # Adjust size based on signal strength
            strength_multiplier = {
                SignalStrength.WEAK: 0.5,
                SignalStrength.MEDIUM: 0.8,
                SignalStrength.STRONG: 1.0
            }.get(signal.strength, 0.5)
            
            # Volatility-based sizing
            if self.volatility_scaling:
                # Reduce size in high volatility, increase in low volatility
                vol_multiplier = {
                    'extreme': 0.6,    # Smaller positions in extreme volatility
                    'elevated': 0.8,   # Reduced positions in elevated volatility
                    'normal': 1.0,     # Normal positions
                    'low': 1.2         # Larger positions in low volatility
                }.get(volatility_regime, 1.0)
            else:
                vol_multiplier = 1.0
            
            # Crisis mode adjustment
            crisis_multiplier = 0.7 if crisis_mode else 1.0
            
            # Trading mode adjustment
            if self.trade_vix_directly:
                # VIX ETFs are more volatile - smaller positions
                mode_multiplier = 0.6
            elif self.equity_hedge_mode:
                # Hedging positions can be larger
                mode_multiplier = 1.3
            else:
                # Market timing positions
                mode_multiplier = 1.0
            
            # Calculate final position size
            position_size = (base_size * strength_multiplier * vol_multiplier * 
                           crisis_multiplier * mode_multiplier)
            position_size = min(position_size, self.max_position_size * 1.5)
            
            # Calculate stop loss and take profit
            atr = self.technical_indicators.atr(data, period=14).iloc[-1]
            
            # Volatility-adjusted stops
            if volatility_regime == 'extreme':
                stop_multiplier = 3.0  # Wider stops in extreme volatility
                profit_multiplier = 2.0
            elif volatility_regime == 'elevated':
                stop_multiplier = 2.5
                profit_multiplier = 2.5
            else:
                stop_multiplier = 2.0
                profit_multiplier = 3.0
            
            if signal.signal_type == SignalType.BUY:
                stop_loss = current_price - (atr * stop_multiplier)
                take_profit = current_price + (atr * profit_multiplier)
            elif signal.signal_type == SignalType.SELL:
                stop_loss = current_price + (atr * stop_multiplier)
                take_profit = current_price - (atr * profit_multiplier)
            else:
                stop_loss = None
                take_profit = None
            
            return RiskParameters(
                position_size=position_size,
                stop_loss=stop_loss,
                take_profit=take_profit,
                max_risk_per_trade=0.03,  # Higher risk for volatility trading
                risk_reward_ratio=profit_multiplier / stop_multiplier,
                volatility_adjustment=vix_level / 20.0  # VIX level as volatility proxy
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating risk parameters: {e}")
            return self._create_default_risk_parameters()
    
    def _check_market_regime(self, data: pd.DataFrame) -> MarketRegime:
        """
        Pillar 3: Market Regime Adaptation
        
        Detect market regime with enhanced volatility context.
        """
        try:
            # Use standard market regime detector
            regime = self.market_regime_detector.detect_regime(data)
            self.current_regime = regime
            
            # Enhance with volatility regime information
            if self.volatility_regime == VolatilityRegime.EXTREME:
                # Override to high volatility regime during VIX spikes
                regime = MarketRegime.HIGH_VOLATILITY
            elif self.crisis_mode:
                # Crisis mode overrides normal regime detection
                regime = MarketRegime.HIGH_VOLATILITY
            
            # Adapt strategy parameters based on combined regime
            if regime == MarketRegime.HIGH_VOLATILITY or self.crisis_mode:
                # More conservative in high volatility
                self.spike_threshold = max(2.5, self.spike_threshold)
                self.reversion_threshold = max(2.0, self.reversion_threshold)
            elif regime == MarketRegime.LOW_VOLATILITY:
                # More aggressive in low volatility
                self.spike_threshold = min(1.5, self.spike_threshold)
                self.reversion_threshold = min(1.0, self.reversion_threshold)
            
            return regime
            
        except Exception as e:
            self.logger.error(f"Error detecting market regime: {e}")
            return MarketRegime.NEUTRAL
    
    def _determine_execution_intent(self, 
                                  signals: List[Signal], 
                                  risk_params: RiskParameters,
                                  current_position: Optional[Dict]) -> ExecutionIntent:
        """
        Pillar 4: Decoupled Execution Logic & Order Management
        
        Determine execution intent with volatility-specific logic.
        """
        if not signals:
            return ExecutionIntent(action="HOLD", quantity=0)
            
        primary_signal = signals[0]
        
        try:
            # Check for position exit conditions
            if current_position and current_position.get('quantity', 0) != 0:
                current_qty = current_position['quantity']
                entry_price = current_position.get('entry_price', 0)
                current_price = primary_signal.metadata.get('current_price', 0)
                
                # VIX-specific exit conditions
                vix_level = primary_signal.metadata.get('vix_level', 20.0)
                entry_vix = current_position.get('entry_vix', 20.0)
                
                # Exit if VIX has reverted significantly
                if self.trade_vix_directly:
                    # For VIX ETF trades, exit when VIX moves as expected
                    if current_qty < 0 and vix_level < entry_vix * 0.8:  # Short VIX ETF, VIX fell
                        return ExecutionIntent(
                            action="BUY",
                            quantity=abs(current_qty),
                            order_type=OrderType.MARKET,
                            reason="VIX reversion completed"
                        )
                    elif current_qty > 0 and vix_level > entry_vix * 1.3:  # Long VIX ETF, VIX spiked
                        return ExecutionIntent(
                            action="SELL",
                            quantity=abs(current_qty),
                            order_type=OrderType.MARKET,
                            reason="VIX spike captured"
                        )
                
                # Standard stop loss / take profit
                if current_qty > 0:
                    if (risk_params.stop_loss and current_price <= risk_params.stop_loss) or \
                       (risk_params.take_profit and current_price >= risk_params.take_profit):
                        pnl_pct = (current_price - entry_price) / entry_price
                        return ExecutionIntent(
                            action="SELL",
                            quantity=abs(current_qty),
                            order_type=OrderType.MARKET,
                            reason=f"Stop/Target hit: {pnl_pct:.2%}"
                        )
                elif current_qty < 0:
                    if (risk_params.stop_loss and current_price >= risk_params.stop_loss) or \
                       (risk_params.take_profit and current_price <= risk_params.take_profit):
                        pnl_pct = (entry_price - current_price) / entry_price
                        return ExecutionIntent(
                            action="BUY",
                            quantity=abs(current_qty),
                            order_type=OrderType.MARKET,
                            reason=f"Stop/Target hit: {pnl_pct:.2%}"
                        )
            
            # Entry logic
            if primary_signal.signal_type == SignalType.BUY and primary_signal.strength != SignalStrength.WEAK:
                return ExecutionIntent(
                    action="BUY",
                    quantity=risk_params.position_size,
                    order_type=OrderType.MARKET,  # Market orders for volatility trading
                    stop_loss=risk_params.stop_loss,
                    take_profit=risk_params.take_profit,
                    reason=f"VIX mean reversion signal: {primary_signal.metadata.get('volatility_regime', 'unknown')}",
                    metadata={
                        'entry_vix': primary_signal.metadata.get('vix_level'),
                        'volatility_regime': primary_signal.metadata.get('volatility_regime'),
                        'signal_source': primary_signal.metadata.get('signal_source')
                    }
                )
                
            elif primary_signal.signal_type == SignalType.SELL and primary_signal.strength != SignalStrength.WEAK:
                return ExecutionIntent(
                    action="SELL",
                    quantity=risk_params.position_size,
                    order_type=OrderType.MARKET,
                    stop_loss=risk_params.stop_loss,
                    take_profit=risk_params.take_profit,
                    reason=f"VIX mean reversion signal: {primary_signal.metadata.get('volatility_regime', 'unknown')}",
                    metadata={
                        'entry_vix': primary_signal.metadata.get('vix_level'),
                        'volatility_regime': primary_signal.metadata.get('volatility_regime'),
                        'signal_source': primary_signal.metadata.get('signal_source')
                    }
                )
            
            return ExecutionIntent(action="HOLD", quantity=0)
            
        except Exception as e:
            self.logger.error(f"Error determining execution intent: {e}")
            return ExecutionIntent(action="HOLD", quantity=0)
    
    def _update_performance_metrics(self, 
                                  execution_result: Dict,
                                  market_data: pd.DataFrame) -> None:
        """
        Pillar 5: Performance Tracking & Configurability
        
        Update performance metrics with VIX-specific statistics.
        """
        try:
            # Update basic performance metrics
            self.performance_metrics.update(
                timestamp=market_data.index[-1],
                price=market_data['close'].iloc[-1],
                position=execution_result.get('position', 0),
                pnl=execution_result.get('pnl', 0),
                execution_result=execution_result
            )
            
            # VIX-specific metrics
            if hasattr(self, '_last_signal') and self._last_signal:
                signal_metadata = self._last_signal.metadata
                
                # Track VIX levels at entry/exit
                self.performance_metrics.add_custom_metric(
                    'vix_level_at_signal',
                    signal_metadata.get('vix_level', 20.0)
                )
                
                self.performance_metrics.add_custom_metric(
                    'volatility_regime_at_signal',
                    signal_metadata.get('volatility_regime', 'normal')
                )
                
                self.performance_metrics.add_custom_metric(
                    'mean_reversion_probability',
                    signal_metadata.get('mean_reversion_probability', 0.5)
                )
                
                self.performance_metrics.add_custom_metric(
                    'days_since_spike',
                    signal_metadata.get('days_since_spike', 0)
                )
            
            # Track regime statistics
            self.performance_metrics.add_custom_metric('current_volatility_regime', self.volatility_regime.value)
            self.performance_metrics.add_custom_metric('crisis_mode_active', self.crisis_mode)
            self.performance_metrics.add_custom_metric('vix_structure', self.vix_structure.value)
            
            # Calculate regime-specific performance
            trades = self.performance_metrics.get_trades()
            if len(trades) >= 10:
                for regime in VolatilityRegime:
                    regime_trades = [trade for trade in trades[-20:] 
                                   if trade.get('volatility_regime_at_signal') == regime.value]
                    if regime_trades:
                        regime_success = sum(1 for trade in regime_trades if trade.get('pnl', 0) > 0)
                        regime_success_rate = regime_success / len(regime_trades)
                        
                        self.performance_metrics.add_custom_metric(
                            f'{regime.value}_regime_success_rate',
                            regime_success_rate
                        )
            
        except Exception as e:
            self.logger.error(f"Error updating performance metrics: {e}")
    
    def _create_neutral_signal(self) -> Signal:
        """Create a neutral signal when no VIX opportunities are present"""
        return Signal(
            symbol=self.symbol,
            signal_type=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            confidence=0.5,
            timestamp=datetime.now(),
            metadata={'reason': 'No VIX mean reversion opportunities'}
        )
    
    def _create_default_risk_parameters(self) -> RiskParameters:
        """Create default risk parameters when calculation fails"""
        return RiskParameters(
            position_size=self.max_position_size * 0.5,
            stop_loss=None,
            take_profit=None,
            max_risk_per_trade=0.03,
            risk_reward_ratio=2.0,
            volatility_adjustment=1.0
        )
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Return strategy information and current parameters"""
        return {
            'name': 'VIX Mean Reversion Strategy',
            'version': '1.0',
            'description': 'Volatility mean reversion strategy based on VIX analysis',
            'parameters': {
                'vix_symbol': self.vix_symbol,
                'lookback_period': self.lookback_period,
                'spike_threshold': self.spike_threshold,
                'reversion_threshold': self.reversion_threshold,
                'max_days_to_revert': self.max_days_to_revert,
                'use_term_structure': self.use_term_structure,
                'trade_vix_directly': self.trade_vix_directly,
                'equity_hedge_mode': self.equity_hedge_mode,
                'max_position_size': self.max_position_size,
                'volatility_scaling': self.volatility_scaling,
                'crisis_mode_threshold': self.crisis_mode_threshold
            },
            'current_state': {
                'volatility_regime': self.volatility_regime.value,
                'vix_structure': self.vix_structure.value,
                'crisis_mode': self.crisis_mode,
                'market_regime': self.current_regime.value
            },
            'asset_classes': ['vix_etfs', 'equities', 'index_futures'],
            'timeframes': ['1d', '4h', '1h'],
            'market_conditions': ['high_volatility', 'market_stress', 'volatility_spikes']
        }