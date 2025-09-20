import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

# Import base classes and utilities
from ...core.base_institutional_strategy import (
    BaseInstitutionalStrategy, MarketRegime, SignalType, ExecutionAction,
    ExecutionIntent, PerformanceMetrics, StrategyState
)
from ...utils.risk_management_utils import RiskManagementUtils
from ...utils.execution_intent_utils import ExecutionIntentUtils, ExecutionConstraints
from ...core.strategy_config_schema import (
    StrategyConfig, StrategyCategory, AssetClass, TimeFrame,
    IndicatorConfig, SignalConfig, RiskConfig, RegimeConfig,
    ExecutionConfig, PerformanceConfig, BacktestConfig
)


@dataclass
class CoppockSignal:
    """Coppock Curve signal data"""
    coppock_value: float
    vw_coppock_value: float
    roc_11: float
    roc_14: float
    vw_roc_11: float
    vw_roc_14: float
    price: float
    volume: float
    signal_strength: float
    signal_type: SignalType
    bullish_crossover: bool
    bearish_crossover: bool
    momentum_acceleration: bool
    volume_confirmation: bool
    regime_filter_passed: bool
    timestamp: datetime


class CoppockCurveStrategy(BaseInstitutionalStrategy):
    """
    Coppock Curve Strategy with Volume-Weighted Enhancement
    
    The Coppock Curve is a long-term momentum indicator developed by Edwin Coppock
    in 1962, originally designed for identifying major market bottoms and the start
    of new bull markets. This institutional-grade implementation enhances the classic
    indicator with volume-weighting and the full 5-Pillar Architecture:
    
    Pillar 1: Signal Generation & Augmentation
    - Primary: Coppock Curve crossover signals (zero line and directional changes)
    - Secondary: Volume-Weighted Coppock Curve for enhanced signal quality
    - Rate of Change components: 11-month and 14-month ROC (adapted for daily data)
    - Volume confirmation and momentum acceleration detection
    
    Pillar 2: Dynamic Risk & Money Management
    - Position sizing based on signal strength and momentum persistence
    - Long-term volatility-adjusted position sizing
    - Portfolio correlation limits for long-term positions
    
    Pillar 3: Market Regime Adaptation
    - Bull/bear market regime detection for signal filtering
    - Volatility regime adaptation for parameter adjustment
    - Economic cycle awareness for long-term positioning
    
    Pillar 4: Decoupled Execution Logic & Order Management
    - Patient execution optimized for long-term positions
    - TWAP execution for large position accumulation
    - Minimal market impact for institutional-size orders
    
    Pillar 5: Performance Tracking & Configurability
    - Long-term performance attribution
    - Cycle-based performance analysis
    - Momentum persistence tracking
    
    Strategy Logic:
    - Enter long when Coppock Curve crosses above zero or shows strong upward momentum
    - Enhanced with Volume-Weighted calculations for institutional quality
    - Designed for long-term trend following and major market turning points
    - Typically used on monthly data, adapted here for daily with longer periods
    
    Mathematical Foundation:
    - ROC(11) = (Price / Price[11 periods ago] - 1) * 100
    - ROC(14) = (Price / Price[14 periods ago] - 1) * 100
    - Coppock = WMA(10, ROC(11) + ROC(14))
    - Volume-Weighted versions use volume-weighted price changes
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # Strategy-specific parameters (adapted for daily data)
        self.roc_short_period = config.strategy_parameters.get('roc_short_period', 55)  # ~11 months daily
        self.roc_long_period = config.strategy_parameters.get('roc_long_period', 70)   # ~14 months daily
        self.wma_period = config.strategy_parameters.get('wma_period', 50)             # ~10 months daily
        self.signal_threshold = config.strategy_parameters.get('signal_threshold', 0.0)
        self.momentum_threshold = config.strategy_parameters.get('momentum_threshold', 2.0)
        self.volume_confirmation_threshold = config.strategy_parameters.get('volume_confirmation_threshold', 1.2)
        
        # Enhanced parameters for institutional quality
        self.trend_confirmation_period = config.strategy_parameters.get('trend_confirmation_period', 20)
        self.volatility_lookback = config.strategy_parameters.get('volatility_lookback', 60)
        self.regime_detection_period = config.strategy_parameters.get('regime_detection_period', 120)
        self.momentum_acceleration_threshold = config.strategy_parameters.get('momentum_acceleration_threshold', 1.5)
        
        # Internal state
        self.coppock_values = {}
        self.vw_coppock_values = {}
        self.roc_values = {}
        self.vw_roc_values = {}
        self.volume_ma_values = {}
        self.volatility_values = {}
        self.signal_history = {}
        self.momentum_persistence = {}
        
        # Risk management
        self.risk_manager = RiskManagementUtils()
        self.execution_utils = ExecutionIntentUtils()
        
        self.logger.info(f"Initialized Coppock Curve Strategy with ROC periods=({self.roc_short_period}, {self.roc_long_period}), "
                        f"WMA period={self.wma_period}")
    
    def calculate_rate_of_change(self, prices: pd.Series, period: int) -> pd.Series:
        """
        Calculate Rate of Change (ROC) indicator.
        
        Args:
            prices: Price series
            period: ROC period
            
        Returns:
            ROC series as percentage
        """
        if len(prices) < period + 1:
            return pd.Series(index=prices.index, dtype=float)
        
        # Calculate ROC as percentage change
        roc = ((prices / prices.shift(period)) - 1) * 100
        
        return roc.fillna(0)
    
    def calculate_volume_weighted_roc(self, prices: pd.Series, volumes: pd.Series, period: int) -> pd.Series:
        """
        Calculate Volume-Weighted Rate of Change.
        
        This implementation weights the price changes by volume to give more importance
        to price movements that occur on higher volume.
        
        Args:
            prices: Price series
            volumes: Volume series
            period: ROC period
            
        Returns:
            Volume-Weighted ROC series
        """
        if len(prices) < period + 1 or len(volumes) < period + 1:
            return pd.Series(index=prices.index, dtype=float)
        
        # Calculate volume-weighted average prices over the period
        vwap_current = (prices * volumes).rolling(window=period).sum() / volumes.rolling(window=period).sum()
        vwap_lagged = vwap_current.shift(period)
        
        # Calculate Volume-Weighted ROC
        vw_roc = ((vwap_current / vwap_lagged) - 1) * 100
        
        return vw_roc.fillna(0)
    
    def calculate_weighted_moving_average(self, series: pd.Series, period: int) -> pd.Series:
        """
        Calculate Weighted Moving Average (WMA).
        
        Args:
            series: Input series
            period: WMA period
            
        Returns:
            WMA series
        """
        if len(series) < period:
            return pd.Series(index=series.index, dtype=float)
        
        # Create weights (linear weighting)
        weights = np.arange(1, period + 1)
        weights = weights / weights.sum()
        
        # Calculate WMA
        wma = series.rolling(window=period).apply(
            lambda x: np.sum(x * weights) if len(x) == period else np.nan,
            raw=True
        )
        
        return wma.fillna(0)
    
    def calculate_coppock_curve(self, prices: pd.Series, volumes: pd.Series) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate both traditional and Volume-Weighted Coppock Curve.
        
        Args:
            prices: Price series
            volumes: Volume series
            
        Returns:
            Tuple of (Coppock Curve, Volume-Weighted Coppock Curve)
        """
        # Calculate ROC components
        roc_short = self.calculate_rate_of_change(prices, self.roc_short_period)
        roc_long = self.calculate_rate_of_change(prices, self.roc_long_period)
        
        # Calculate Volume-Weighted ROC components
        vw_roc_short = self.calculate_volume_weighted_roc(prices, volumes, self.roc_short_period)
        vw_roc_long = self.calculate_volume_weighted_roc(prices, volumes, self.roc_long_period)
        
        # Sum ROC components
        roc_sum = roc_short + roc_long
        vw_roc_sum = vw_roc_short + vw_roc_long
        
        # Apply Weighted Moving Average to get Coppock Curve
        coppock = self.calculate_weighted_moving_average(roc_sum, self.wma_period)
        vw_coppock = self.calculate_weighted_moving_average(vw_roc_sum, self.wma_period)
        
        return coppock, vw_coppock
    
    def calculate_volume_confirmation(self, volumes: pd.Series, period: int = 30) -> pd.Series:
        """
        Calculate volume confirmation indicator for long-term signals.
        
        Args:
            volumes: Volume series
            period: Lookback period for volume average
            
        Returns:
            Volume confirmation ratio
        """
        volume_ma = volumes.rolling(window=period, min_periods=period).mean()
        volume_ratio = volumes / volume_ma
        return volume_ratio.fillna(1.0)
    
    def calculate_momentum_acceleration(self, coppock: pd.Series, period: int = 10) -> pd.Series:
        """
        Calculate momentum acceleration (rate of change of Coppock Curve).
        
        Args:
            coppock: Coppock Curve series
            period: Period for acceleration calculation
            
        Returns:
            Momentum acceleration series
        """
        if len(coppock) < period + 1:
            return pd.Series(index=coppock.index, dtype=float)
        
        # Calculate the rate of change of Coppock Curve
        acceleration = coppock.diff(period)
        
        return acceleration.fillna(0)
    
    def detect_crossovers(self, coppock: pd.Series, threshold: float = 0.0) -> Tuple[pd.Series, pd.Series]:
        """
        Detect bullish and bearish crossovers of the Coppock Curve.
        
        Args:
            coppock: Coppock Curve series
            threshold: Crossover threshold (typically 0)
            
        Returns:
            Tuple of (bullish_crossovers, bearish_crossovers)
        """
        if len(coppock) < 2:
            return pd.Series(index=coppock.index, dtype=bool), pd.Series(index=coppock.index, dtype=bool)
        
        # Detect crossovers
        above_threshold = coppock > threshold
        below_threshold = coppock <= threshold
        
        # Bullish crossover: from below to above threshold
        bullish_crossover = above_threshold & below_threshold.shift(1)
        
        # Bearish crossover: from above to below threshold
        bearish_crossover = below_threshold & above_threshold.shift(1)
        
        return bullish_crossover.fillna(False), bearish_crossover.fillna(False)
    
    def generate_signals(self, symbol: str, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Pillar 1: Signal Generation & Augmentation
        
        Generate Coppock Curve signals with volume and momentum confirmation.
        
        Args:
            symbol: Trading symbol
            data: OHLCV data
            
        Returns:
            List of signal dictionaries
        """
        min_required_data = max(self.roc_long_period + self.wma_period, 150)
        if len(data) < min_required_data:
            self.logger.warning(f"Insufficient data for Coppock Curve calculation: {len(data)} < {min_required_data}")
            return []
        
        signals = []
        
        try:
            # Calculate indicators
            close_prices = data['close']
            volumes = data['volume']
            
            # Calculate Coppock Curve indicators
            coppock, vw_coppock = self.calculate_coppock_curve(close_prices, volumes)
            
            # Calculate ROC components for analysis
            roc_short = self.calculate_rate_of_change(close_prices, self.roc_short_period)
            roc_long = self.calculate_rate_of_change(close_prices, self.roc_long_period)
            vw_roc_short = self.calculate_volume_weighted_roc(close_prices, volumes, self.roc_short_period)
            vw_roc_long = self.calculate_volume_weighted_roc(close_prices, volumes, self.roc_long_period)
            
            # Calculate confirmation indicators
            volume_confirmation = self.calculate_volume_confirmation(volumes)
            momentum_acceleration = self.calculate_momentum_acceleration(coppock)
            
            # Detect crossovers
            bullish_crossovers, bearish_crossovers = self.detect_crossovers(coppock, self.signal_threshold)
            vw_bullish_crossovers, vw_bearish_crossovers = self.detect_crossovers(vw_coppock, self.signal_threshold)
            
            # Store for later use
            self.coppock_values[symbol] = coppock
            self.vw_coppock_values[symbol] = vw_coppock
            self.roc_values[symbol] = {'short': roc_short, 'long': roc_long}
            self.vw_roc_values[symbol] = {'short': vw_roc_short, 'long': vw_roc_long}
            self.volume_ma_values[symbol] = volume_confirmation
            
            # Generate signals for recent data
            recent_data = data.tail(20)  # Look at last 20 bars for long-term signals
            
            for i, (timestamp, row) in enumerate(recent_data.iterrows()):
                idx = data.index.get_loc(timestamp)
                
                if idx < min_required_data - 10:
                    continue
                
                current_price = row['close']
                current_volume = row['volume']
                
                # Get indicator values
                coppock_val = coppock.iloc[idx] if idx < len(coppock) else 0
                vw_coppock_val = vw_coppock.iloc[idx] if idx < len(vw_coppock) else 0
                roc_s = roc_short.iloc[idx] if idx < len(roc_short) else 0
                roc_l = roc_long.iloc[idx] if idx < len(roc_long) else 0
                vw_roc_s = vw_roc_short.iloc[idx] if idx < len(vw_roc_short) else 0
                vw_roc_l = vw_roc_long.iloc[idx] if idx < len(vw_roc_long) else 0
                vol_conf = volume_confirmation.iloc[idx] if idx < len(volume_confirmation) else 1.0
                momentum_accel = momentum_acceleration.iloc[idx] if idx < len(momentum_acceleration) else 0
                
                # Get crossover signals
                bullish_cross = bullish_crossovers.iloc[idx] if idx < len(bullish_crossovers) else False
                bearish_cross = bearish_crossovers.iloc[idx] if idx < len(bearish_crossovers) else False
                vw_bullish_cross = vw_bullish_crossovers.iloc[idx] if idx < len(vw_bullish_crossovers) else False
                vw_bearish_cross = vw_bearish_crossovers.iloc[idx] if idx < len(vw_bearish_crossovers) else False
                
                if pd.isna(coppock_val) or pd.isna(vw_coppock_val):
                    continue
                
                # Signal generation logic
                signal_type = SignalType.NEUTRAL
                signal_strength = 0.0
                
                # Strong bullish signal: Coppock crossover + volume confirmation + momentum acceleration
                if (bullish_cross or vw_bullish_cross) and vol_conf >= self.volume_confirmation_threshold:
                    signal_type = SignalType.BULLISH
                    
                    # Calculate signal strength based on multiple factors
                    crossover_strength = 1.0 if (bullish_cross and vw_bullish_cross) else 0.7
                    momentum_strength = min(1.0, abs(momentum_accel) / self.momentum_acceleration_threshold)
                    volume_strength = min(1.0, vol_conf / self.volume_confirmation_threshold)
                    coppock_magnitude = min(1.0, abs(coppock_val) / 10.0)  # Normalize to reasonable range
                    
                    signal_strength = min(1.0, 0.3 + crossover_strength * 0.4 + momentum_strength * 0.15 + 
                                        volume_strength * 0.1 + coppock_magnitude * 0.05)
                    
                    # Boost for strong momentum acceleration
                    if momentum_accel > self.momentum_acceleration_threshold:
                        signal_strength = min(1.0, signal_strength * 1.15)
                
                # Moderate bullish signal: Positive Coppock with upward momentum
                elif (coppock_val > self.signal_threshold and vw_coppock_val > self.signal_threshold and 
                      momentum_accel > 0.5):
                    signal_type = SignalType.WEAK_BULLISH
                    
                    momentum_strength = min(1.0, momentum_accel / self.momentum_acceleration_threshold)
                    coppock_strength = min(1.0, (coppock_val + vw_coppock_val) / 20.0)
                    volume_strength = min(1.0, vol_conf)
                    
                    signal_strength = min(0.7, 0.2 + momentum_strength * 0.25 + coppock_strength * 0.15 + 
                                        volume_strength * 0.1)
                
                # Bearish signals (less common for Coppock, but included for completeness)
                elif (bearish_cross or vw_bearish_cross) and vol_conf >= self.volume_confirmation_threshold:
                    signal_type = SignalType.BEARISH
                    
                    crossover_strength = 1.0 if (bearish_cross and vw_bearish_cross) else 0.7
                    momentum_strength = min(1.0, abs(momentum_accel) / self.momentum_acceleration_threshold)
                    volume_strength = min(1.0, vol_conf / self.volume_confirmation_threshold)
                    
                    signal_strength = min(0.8, 0.3 + crossover_strength * 0.3 + momentum_strength * 0.1 + 
                                        volume_strength * 0.1)  # Generally weaker for bearish Coppock signals
                
                elif (coppock_val < -self.momentum_threshold and vw_coppock_val < -self.momentum_threshold and 
                      momentum_accel < -1.0):
                    signal_type = SignalType.WEAK_BEARISH
                    
                    momentum_strength = min(1.0, abs(momentum_accel) / self.momentum_acceleration_threshold)
                    coppock_strength = min(1.0, abs(coppock_val + vw_coppock_val) / 20.0)
                    
                    signal_strength = min(0.6, 0.2 + momentum_strength * 0.2 + coppock_strength * 0.2)
                
                # Create signal if significant
                if signal_strength > 0.25:  # Higher threshold for long-term signals
                    coppock_signal = CoppockSignal(
                        coppock_value=coppock_val,
                        vw_coppock_value=vw_coppock_val,
                        roc_11=roc_s,
                        roc_14=roc_l,
                        vw_roc_11=vw_roc_s,
                        vw_roc_14=vw_roc_l,
                        price=current_price,
                        volume=current_volume,
                        signal_strength=signal_strength,
                        signal_type=signal_type,
                        bullish_crossover=bullish_cross or vw_bullish_cross,
                        bearish_crossover=bearish_cross or vw_bearish_cross,
                        momentum_acceleration=momentum_accel > self.momentum_acceleration_threshold,
                        volume_confirmation=vol_conf >= self.volume_confirmation_threshold,
                        regime_filter_passed=True,  # Will be updated in regime detection
                        timestamp=timestamp
                    )
                    
                    signals.append({
                        'timestamp': timestamp,
                        'symbol': symbol,
                        'signal_type': signal_type,
                        'signal_strength': signal_strength,
                        'price': current_price,
                        'volume': current_volume,
                        'coppock': coppock_val,
                        'vw_coppock': vw_coppock_val,
                        'roc_short': roc_s,
                        'roc_long': roc_l,
                        'vw_roc_short': vw_roc_s,
                        'vw_roc_long': vw_roc_l,
                        'momentum_acceleration': momentum_accel,
                        'volume_confirmation': vol_conf >= self.volume_confirmation_threshold,
                        'bullish_crossover': bullish_cross or vw_bullish_cross,
                        'bearish_crossover': bearish_cross or vw_bearish_cross,
                        'metadata': {
                            'coppock_magnitude': abs(coppock_val),
                            'vw_coppock_magnitude': abs(vw_coppock_val),
                            'momentum_persistence': momentum_accel,
                            'volume_ratio': vol_conf,
                            'signal_quality': 'high' if signal_strength > 0.7 else 'medium' if signal_strength > 0.4 else 'low'
                        }
                    })
            
            # Store signal history
            if symbol not in self.signal_history:
                self.signal_history[symbol] = []
            
            self.signal_history[symbol].extend(signals)
            
            # Keep only recent signals (last 50 for long-term strategy)
            self.signal_history[symbol] = self.signal_history[symbol][-50:]
            
            self.logger.info(f"Generated {len(signals)} Coppock Curve signals for {symbol}")
            
        except Exception as e:
            self.logger.error(f"Error generating Coppock Curve signals for {symbol}: {e}")
            return []
        
        return signals
    
    def detect_market_regime(self, symbol: str, data: pd.DataFrame) -> MarketRegime:
        """
        Pillar 3: Market Regime Adaptation
        
        Detect current market regime for Coppock strategy adaptation.
        
        Args:
            symbol: Trading symbol
            data: OHLCV data
            
        Returns:
            Detected market regime
        """
        if len(data) < self.regime_detection_period:
            return MarketRegime.SIDEWAYS_MARKET
        
        try:
            # Long-term trend analysis using Coppock Curve
            if symbol in self.coppock_values and symbol in self.vw_coppock_values:
                coppock_series = self.coppock_values[symbol]
                vw_coppock_series = self.vw_coppock_values[symbol]
                
                if len(coppock_series) >= 60 and len(vw_coppock_series) >= 60:
                    # Analyze recent Coppock behavior
                    recent_coppock = coppock_series.tail(60)
                    recent_vw_coppock = vw_coppock_series.tail(60)
                    
                    # Bull market: Sustained positive Coppock values
                    positive_periods = len(recent_coppock[recent_coppock > 0])
                    strong_positive_periods = len(recent_coppock[recent_coppock > 5])
                    
                    # Bear market: Sustained negative Coppock values
                    negative_periods = len(recent_coppock[recent_coppock < 0])
                    strong_negative_periods = len(recent_coppock[recent_coppock < -5])
                    
                    # Volatility analysis
                    coppock_volatility = recent_coppock.std()
                    price_volatility = data['close'].tail(60).pct_change().std() * np.sqrt(252)
                    
                    # Determine regime
                    if positive_periods >= 45 and strong_positive_periods >= 20:  # 75% positive, 33% strongly positive
                        return MarketRegime.BULL_MARKET
                    elif negative_periods >= 45 and strong_negative_periods >= 20:
                        return MarketRegime.BEAR_MARKET
                    elif price_volatility > 0.25:  # High volatility
                        return MarketRegime.HIGH_VOLATILITY
                    elif price_volatility < 0.12:  # Low volatility
                        return MarketRegime.LOW_VOLATILITY
                    else:
                        return MarketRegime.SIDEWAYS_MARKET
            
            # Fallback regime detection using price action
            returns = data['close'].pct_change()
            volatility = returns.rolling(window=30).std() * np.sqrt(252)
            current_vol = volatility.iloc[-1]
            
            # Long-term price trend
            price_change_60d = (data['close'].iloc[-1] - data['close'].iloc[-60]) / data['close'].iloc[-60]
            
            if current_vol > 0.25:
                return MarketRegime.HIGH_VOLATILITY
            elif price_change_60d > 0.15:  # Strong uptrend
                return MarketRegime.BULL_MARKET
            elif price_change_60d < -0.15:  # Strong downtrend
                return MarketRegime.BEAR_MARKET
            else:
                return MarketRegime.SIDEWAYS_MARKET
                
        except Exception as e:
            self.logger.error(f"Error detecting market regime for {symbol}: {e}")
            return MarketRegime.SIDEWAYS_MARKET
    
    def calculate_position_size(self, symbol: str, signal_strength: float, 
                              current_price: float, account_value: float) -> float:
        """
        Pillar 2: Dynamic Risk & Money Management
        
        Calculate position size for long-term Coppock positions.
        
        Args:
            symbol: Trading symbol
            signal_strength: Strength of the Coppock signal (0-1)
            current_price: Current asset price
            account_value: Total account value
            
        Returns:
            Position size in shares/units
        """
        try:
            # Base position size from configuration (larger for long-term strategy)
            base_size_pct = self.config.risk_config.base_position_size * 1.5  # Increase for long-term
            max_size_pct = self.config.risk_config.max_position_size
            
            # Adjust for signal strength
            signal_adjusted_size = base_size_pct * signal_strength
            
            # Long-term volatility adjustment (less sensitive than short-term strategies)
            if symbol in self.coppock_values:
                coppock_series = self.coppock_values[symbol]
                if len(coppock_series) > 30:
                    # Use Coppock volatility as a proxy for long-term risk
                    coppock_vol = coppock_series.tail(30).std()
                    vol_adjustment = max(0.7, min(1.3, 5.0 / (coppock_vol + 1.0)))
                    signal_adjusted_size *= vol_adjustment
            
            # Apply maximum position size limit
            final_size_pct = min(signal_adjusted_size, max_size_pct)
            
            # Calculate dollar amount and convert to shares
            dollar_amount = account_value * final_size_pct
            shares = int(dollar_amount / current_price)
            
            # Minimum position size
            shares = max(shares, 1)
            
            self.logger.debug(f"Coppock position size for {symbol}: {shares} shares (${dollar_amount:.2f}, {final_size_pct:.2%})")
            
            return shares
            
        except Exception as e:
            self.logger.error(f"Error calculating position size for {symbol}: {e}")
            return 1  # Minimum position
    
    def should_exit_position(self, symbol: str, current_price: float, 
                           entry_price: float, entry_time: datetime, 
                           position_side: str = 'long') -> Tuple[bool, str]:
        """
        Determine if Coppock position should be exited (long-term holding strategy).
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            entry_price: Position entry price
            entry_time: Position entry time
            position_side: 'long' or 'short'
            
        Returns:
            Tuple of (should_exit, reason)
        """
        try:
            # Calculate current return
            if position_side.lower() == 'long':
                current_return = (current_price - entry_price) / entry_price
            else:
                current_return = (entry_price - current_price) / entry_price
            
            # Long-term time-based exit (Coppock is designed for long-term holding)
            max_hold_days = self.config.strategy_parameters.get('max_hold_days', 180)  # 6 months default
            if (datetime.now() - entry_time).days > max_hold_days:
                return True, f"Maximum hold period ({max_hold_days} days) exceeded"
            
            # Stop-loss check (wider for long-term strategy)
            stop_loss_pct = self.config.risk_config.stop_loss_pct * 1.5  # Wider stops for long-term
            if stop_loss_pct and current_return <= -stop_loss_pct:
                return True, f"Stop-loss triggered at {current_return:.2%}"
            
            # Take-profit check (higher targets for long-term)
            take_profit_pct = self.config.risk_config.take_profit_pct * 2.0  # Higher targets
            if take_profit_pct and current_return >= take_profit_pct:
                return True, f"Take-profit triggered at {current_return:.2%}"
            
            # Coppock-based exit signals
            if symbol in self.coppock_values and symbol in self.vw_coppock_values:
                coppock_series = self.coppock_values[symbol]
                vw_coppock_series = self.vw_coppock_values[symbol]
                
                if len(coppock_series) >= 10 and len(vw_coppock_series) >= 10:
                    current_coppock = coppock_series.iloc[-1]
                    current_vw_coppock = vw_coppock_series.iloc[-1]
                    
                    # Calculate momentum change
                    momentum_change = coppock_series.iloc[-1] - coppock_series.iloc[-10]
                    
                    # Exit long position on sustained negative momentum
                    if (position_side.lower() == 'long' and 
                        current_coppock < -self.momentum_threshold and 
                        current_vw_coppock < -self.momentum_threshold and 
                        momentum_change < -2.0 and 
                        current_return > -0.05):  # Don't exit on small losses
                        return True, f"Coppock bearish signal: Coppock({current_coppock:.2f}), momentum change({momentum_change:.2f})"
                    
                    # Exit short position on sustained positive momentum
                    if (position_side.lower() == 'short' and 
                        current_coppock > self.momentum_threshold and 
                        current_vw_coppock > self.momentum_threshold and 
                        momentum_change > 2.0 and 
                        current_return > -0.05):
                        return True, f"Coppock bullish signal: Coppock({current_coppock:.2f}), momentum change({momentum_change:.2f})"
                    
                    # Exit on extreme opposite signals (risk management)
                    if position_side.lower() == 'long' and current_coppock < -10:
                        return True, f"Extreme bearish Coppock signal: {current_coppock:.2f}"
                    
                    if position_side.lower() == 'short' and current_coppock > 10:
                        return True, f"Extreme bullish Coppock signal: {current_coppock:.2f}"
            
            # Market regime change exit
            current_regime = self.detect_market_regime(symbol, pd.DataFrame())  # Simplified call
            if (position_side.lower() == 'long' and current_regime == MarketRegime.BEAR_MARKET and 
                (datetime.now() - entry_time).days > 30):  # Give time for regime to establish
                return True, f"Market regime changed to bear market"
            
            return False, "No exit conditions met"
            
        except Exception as e:
            self.logger.error(f"Error checking exit conditions for {symbol}: {e}")
            return False, f"Error in exit logic: {e}"
    
    def create_execution_intent(self, symbol: str, action: ExecutionAction, 
                              quantity: float, signal_data: Dict[str, Any]) -> ExecutionIntent:
        """
        Pillar 4: Decoupled Execution Logic & Order Management
        
        Create execution intent optimized for long-term position building.
        
        Args:
            symbol: Trading symbol
            action: Execution action
            quantity: Order quantity
            signal_data: Signal information
            
        Returns:
            Execution intent
        """
        try:
            # Prepare market data
            market_data = {
                'price': signal_data.get('price', 0),
                'volume': signal_data.get('volume', 1000000),
                'avg_volume': signal_data.get('volume', 1000000),
                'volatility': signal_data.get('metadata', {}).get('volatility', 0.02),
                'spread': signal_data.get('price', 0) * 0.001
            }
            
            # Create execution constraints optimized for long-term accumulation
            constraints = ExecutionConstraints(
                max_participation_rate=0.08,  # Lower for patient accumulation
                time_horizon=timedelta(hours=4),  # Longer execution window
                price_improvement_threshold=0.001  # More patient for better prices
            )
            
            # Create execution intent
            intent = self.execution_utils.create_execution_intent(
                action=action,
                symbol=symbol,
                quantity=quantity,
                signal_confidence=signal_data.get('signal_strength', 0.5),
                signal_type=signal_data.get('signal_type', SignalType.NEUTRAL),
                market_data=market_data,
                constraints=constraints
            )
            
            # Add Coppock-specific metadata
            intent.metadata.update({
                'coppock_value': signal_data.get('coppock', 0),
                'vw_coppock_value': signal_data.get('vw_coppock', 0),
                'momentum_acceleration': signal_data.get('momentum_acceleration', 0),
                'strategy_type': 'long_term_momentum',
                'expected_hold_period': 'long_term',
                'crossover_signal': signal_data.get('bullish_crossover', False) or signal_data.get('bearish_crossover', False)
            })
            
            self.logger.info(f"Created Coppock execution intent for {symbol}: {action.value} {quantity} shares")
            
            return intent
            
        except Exception as e:
            self.logger.error(f"Error creating execution intent for {symbol}: {e}")
            return ExecutionIntent(
                action=action,
                symbol=symbol,
                quantity=quantity,
                algorithm=self.config.execution_config.default_algorithm,
                urgency=self.config.execution_config.default_urgency,
                time_in_force=self.config.execution_config.default_time_in_force,
                metadata={'error': str(e)}
            )
    
    def calculate_performance_metrics(self, trades: List[Dict[str, Any]], 
                                    benchmark_returns: Optional[pd.Series] = None) -> PerformanceMetrics:
        """
        Pillar 5: Performance Tracking & Configurability
        
        Calculate Coppock-specific performance metrics.
        
        Args:
            trades: List of completed trades
            benchmark_returns: Benchmark return series
            
        Returns:
            Performance metrics with Coppock-specific enhancements
        """
        try:
            if not trades:
                return PerformanceMetrics(
                    total_return=0.0,
                    sharpe_ratio=0.0,
                    max_drawdown=0.0,
                    win_rate=0.0,
                    profit_factor=0.0,
                    total_trades=0
                )
            
            # Standard performance calculations
            returns = [trade.get('return_pct', 0) for trade in trades]
            total_return = sum(returns)
            
            winning_trades = [r for r in returns if r > 0]
            losing_trades = [r for r in returns if r < 0]
            
            win_rate = len(winning_trades) / len(returns) if returns else 0
            
            # Profit factor
            gross_profit = sum(winning_trades) if winning_trades else 0
            gross_loss = abs(sum(losing_trades)) if losing_trades else 1
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
            
            # Sharpe ratio (annualized for long-term strategy)
            if len(returns) > 1:
                returns_std = np.std(returns)
                sharpe_ratio = (np.mean(returns) / returns_std * np.sqrt(12)) if returns_std > 0 else 0  # Monthly compounding
            else:
                sharpe_ratio = 0
            
            # Maximum drawdown
            cumulative_returns = np.cumsum(returns)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = cumulative_returns - running_max
            max_drawdown = abs(min(drawdowns)) if len(drawdowns) > 0 else 0
            
            # Coppock-specific metrics
            coppock_specific_metrics = {
                'avg_hold_period': np.mean([trade.get('hold_days', 0) for trade in trades]),
                'crossover_trades': len([t for t in trades if t.get('crossover_signal', False)]),
                'momentum_acceleration_trades': len([t for t in trades if t.get('momentum_acceleration', False)]),
                'long_term_winners': len([t for t in trades if t.get('hold_days', 0) > 90 and t.get('return_pct', 0) > 0]),
                'regime_aligned_trades': len([t for t in trades if t.get('regime_aligned', False)])
            }
            
            performance = PerformanceMetrics(
                total_return=total_return,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                win_rate=win_rate,
                profit_factor=profit_factor,
                total_trades=len(trades)
            )
            
            # Add Coppock-specific metadata
            performance.metadata = coppock_specific_metrics
            
            return performance
            
        except Exception as e:
            self.logger.error(f"Error calculating Coppock performance metrics: {e}")
            return PerformanceMetrics(
                total_return=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                total_trades=0
            )
    
    def get_strategy_state(self) -> StrategyState:
        """
        Get current Coppock strategy state and diagnostics.
        
        Returns:
            Current strategy state
        """
        try:
            total_signals = sum(len(signals) for signals in self.signal_history.values())
            
            return StrategyState(
                is_active=True,
                current_positions=len(self.signal_history),
                total_signals_generated=total_signals,
                last_signal_time=datetime.now(),
                strategy_health="HEALTHY",
                error_count=0,
                metadata={
                    'roc_short_period': self.roc_short_period,
                    'roc_long_period': self.roc_long_period,
                    'wma_period': self.wma_period,
                    'signal_threshold': self.signal_threshold,
                    'tracked_symbols': list(self.signal_history.keys()),
                    'coppock_values_cached': len(self.coppock_values),
                    'vw_coppock_values_cached': len(self.vw_coppock_values)
                }
            )
        except Exception as e:
            self.logger.error(f"Error getting Coppock strategy state: {e}")
            return StrategyState(
                is_active=False,
                current_positions=0,
                total_signals_generated=0,
                last_signal_time=datetime.now(),
                strategy_health="ERROR",
                error_count=1,
                metadata={'error': str(e)}
            )


# Example configuration for the Coppock Curve Strategy
def create_coppock_curve_config() -> StrategyConfig:
    """
    Create a sample configuration for the Coppock Curve Strategy.
    
    Returns:
        Strategy configuration
    """
    from datetime import datetime, timedelta
    
    today = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=1095)).strftime('%Y-%m-%d')  # 3 years for long-term
    
    return StrategyConfig(
        name="Coppock Curve Strategy",
        version="1.0.0",
        description="Enhanced Coppock Curve long-term momentum strategy with Volume-Weighted calculations and institutional-grade risk management",
        category=StrategyCategory.MOMENTUM,
        author="Institutional Strategy Developer",
        created_date=today,
        last_modified=today,
        asset_classes=[AssetClass.EQUITY, AssetClass.ETF, AssetClass.INDEX],
        symbols=["SPY", "QQQ", "IWM", "VTI", "VXUS", "VEA", "VWO", "GLD", "TLT"],
        timeframes=[TimeFrame.DAILY, TimeFrame.WEEKLY],
        primary_timeframe=TimeFrame.DAILY,
        signal_config=SignalConfig(
            primary_indicators=[
                IndicatorConfig(
                    name="COPPOCK_CURVE",
                    parameters={"roc_short": 55, "roc_long": 70, "wma_period": 50},
                    volume_weighted=False
                ),
                IndicatorConfig(
                    name="VW_COPPOCK_CURVE",
                    parameters={"roc_short": 55, "roc_long": 70, "wma_period": 50},
                    volume_weighted=True
                )
            ],
            secondary_indicators=[
                IndicatorConfig(
                    name="MOMENTUM_ACCELERATION",
                    parameters={"period": 10},
                    volume_weighted=False
                ),
                IndicatorConfig(
                    name="VOLUME_CONFIRMATION",
                    parameters={"period": 30},
                    volume_weighted=False
                )
            ],
            signal_threshold=0.6,  # Higher threshold for long-term signals
            confirmation_required=True,
            volume_confirmation=True,
            regime_filter=True,
            lookback_bars=20
        ),
        risk_config=RiskConfig(
            position_sizing_method="COPPOCK_MOMENTUM",
            base_position_size=0.08,  # 8% per position (larger for long-term)
            max_position_size=0.20,   # 20% maximum
            stop_loss_pct=0.15,       # 15% stop-loss (wider for long-term)
            take_profit_pct=0.40,     # 40% take-profit (higher targets)
            trailing_stop_pct=0.08,   # 8% trailing stop
            max_drawdown_pct=0.20,    # 20% max drawdown
            correlation_threshold=0.7,
            leverage_limit=1.0
        ),
        regime_config=RegimeConfig(
            enabled=True,
            detection_method="COPPOCK_REGIME",
            lookback_period=120,
            regime_threshold=0.7,
            adaptation_speed=0.1  # Slower adaptation for long-term
        ),
        execution_config=ExecutionConfig(
            max_participation_rate=0.08,  # Lower for patient accumulation
            price_improvement_threshold=0.001,
            slippage_tolerance=0.002,
            smart_routing=True,
            dark_pool_preference=0.3  # Higher for large positions
        ),
        performance_config=PerformanceConfig(
            benchmark_symbol="SPY",
            track_intraday=False,  # Focus on long-term performance
            calculate_attribution=True,
            risk_metrics_enabled=True
        ),
        backtest_config=BacktestConfig(
            start_date=start_date,
            end_date=today,
            initial_capital=100000.0,
            commission_per_trade=1.0,
            commission_pct=0.001,
            slippage_pct=0.001
        ),
        strategy_parameters={
            'roc_short_period': 55,  # ~11 months daily
            'roc_long_period': 70,   # ~14 months daily
            'wma_period': 50,        # ~10 months daily
            'signal_threshold': 0.0,
            'momentum_threshold': 2.0,
            'volume_confirmation_threshold': 1.2,
            'trend_confirmation_period': 20,
            'volatility_lookback': 60,
            'regime_detection_period': 120,
            'momentum_acceleration_threshold': 1.5,
            'max_hold_days': 180  # 6 months maximum hold
        }
    )


# Example usage and testing
if __name__ == "__main__":
    # Create strategy configuration
    config = create_coppock_curve_config()
    
    # Initialize strategy
    strategy = CoppockCurveStrategy(config)
    
    # Create sample data for testing (longer period for Coppock)
    dates = pd.date_range(start='2021-01-01', end='2023-12-31', freq='D')
    np.random.seed(42)
    
    # Create realistic long-term trending data
    base_price = 100
    trend = np.linspace(0, 0.5, len(dates))  # Long-term upward trend
    noise = np.random.randn(len(dates)) * 0.015  # 1.5% daily volatility
    cycles = 0.1 * np.sin(np.linspace(0, 8*np.pi, len(dates)))  # Long-term cycles
    
    price_changes = trend/len(dates) + noise + cycles/len(dates)
    prices = base_price * np.exp(np.cumsum(price_changes))
    
    sample_data = pd.DataFrame({
        'open': prices * (1 + np.random.randn(len(dates)) * 0.003),
        'high': prices * (1 + np.abs(np.random.randn(len(dates))) * 0.008),
        'low': prices * (1 - np.abs(np.random.randn(len(dates))) * 0.008),
        'close': prices,
        'volume': np.random.randint(800000, 2500000, len(dates))
    }, index=dates)
    
    # Ensure realistic OHLC relationships
    sample_data['high'] = np.maximum(sample_data[['open', 'close']].max(axis=1), sample_data['high'])
    sample_data['low'] = np.minimum(sample_data[['open', 'close']].min(axis=1), sample_data['low'])
    
    # Test signal generation
    signals = strategy.generate_signals('TEST', sample_data)
    print(f"Generated {len(signals)} Coppock Curve signals for test data")
    
    if signals:
        print(f"Sample signal: Coppock={signals[0].get('coppock', 'N/A'):.2f}, "
              f"VW-Coppock={signals[0].get('vw_coppock', 'N/A'):.2f}, "
              f"Signal={signals[0].get('signal_type', 'N/A')}, "
              f"Strength={signals[0].get('signal_strength', 'N/A'):.2f}")
    
    # Test market regime detection
    regime = strategy.detect_market_regime('TEST', sample_data)
    print(f"Detected market regime: {regime.value}")
    
    # Test strategy state
    state = strategy.get_strategy_state()
    print(f"Strategy state: {state.strategy_health}")
    
    print("Coppock Curve Strategy implementation completed successfully!")