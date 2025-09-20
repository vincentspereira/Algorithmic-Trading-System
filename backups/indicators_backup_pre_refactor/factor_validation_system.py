"""Factor-Based Signal Validation System

Implements cross-asset awareness and factor-based signal validation for enhanced
signal quality through correlation analysis and factor cluster monitoring.

Key Features:
- Automatic factor cluster identification
- Cross-asset correlation analysis
- Signal validation against correlated factors
- Dynamic factor weight adjustment
- Multi-timeframe factor analysis
- Sector and market factor integration
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple, Union
from collections import deque, defaultdict
from dataclasses import dataclass, field
from enum import Enum
import json
from abc import ABC, abstractmethod

try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    from sklearn.cluster import KMeans
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: scikit-learn not available. Factor analysis will be limited.")

from .enhanced_base import SignalType

try:
    from utils.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

class FactorType(Enum):
    """Types of factors for validation"""
    MARKET = "market"  # Broad market indices
    SECTOR = "sector"  # Sector-specific ETFs
    PEER = "peer"      # Direct competitors
    COMMODITY = "commodity"  # Related commodities
    CURRENCY = "currency"    # Currency factors
    VOLATILITY = "volatility"  # Volatility indices
    INTEREST_RATE = "interest_rate"  # Interest rate factors
    CUSTOM = "custom"  # User-defined factors

class ValidationResult(Enum):
    """Factor validation results"""
    STRONG_CONFIRMATION = "strong_confirmation"
    WEAK_CONFIRMATION = "weak_confirmation"
    NEUTRAL = "neutral"
    WEAK_CONTRADICTION = "weak_contradiction"
    STRONG_CONTRADICTION = "strong_contradiction"

@dataclass
class FactorConfig:
    """Configuration for factor validation"""
    correlation_threshold: float = 0.6
    confirmation_threshold: float = 0.7
    contradiction_threshold: float = -0.3
    lookback_period: int = 50
    min_factor_count: int = 3
    max_factor_count: int = 10
    update_frequency: int = 20  # Update correlations every N periods
    
    # Weight adjustments
    market_factor_weight: float = 0.4
    sector_factor_weight: float = 0.3
    peer_factor_weight: float = 0.2
    other_factor_weight: float = 0.1
    
    # Dynamic adjustment parameters
    enable_dynamic_weights: bool = True
    correlation_decay_factor: float = 0.95
    min_correlation_for_inclusion: float = 0.3

@dataclass
class FactorData:
    """Factor data container"""
    symbol: str
    factor_type: FactorType
    price_history: deque
    volume_history: deque
    returns_history: deque
    correlation_with_target: float = 0.0
    weight: float = 0.0
    last_signal: Optional[SignalType] = None
    last_signal_timestamp: Optional[datetime] = None
    confidence: float = 0.0
    
    def __post_init__(self):
        if not isinstance(self.price_history, deque):
            self.price_history = deque(self.price_history or [], maxlen=200)
        if not isinstance(self.volume_history, deque):
            self.volume_history = deque(self.volume_history or [], maxlen=200)
        if not isinstance(self.returns_history, deque):
            self.returns_history = deque(self.returns_history or [], maxlen=200)

@dataclass
class FactorValidationResult:
    """Result of factor validation"""
    validation_result: ValidationResult
    confidence_adjustment: float
    supporting_factors: List[str]
    contradicting_factors: List[str]
    factor_scores: Dict[str, float]
    correlation_matrix: Dict[str, Dict[str, float]]
    validation_strength: float
    recommendation: str
    
class FactorClusterManager:
    """Manages factor clusters and correlations"""
    
    def __init__(self, config: FactorConfig):
        self.config = config
        self.factors: Dict[str, FactorData] = {}
        self.correlation_matrix = defaultdict(dict)
        self.last_correlation_update = None
        self.target_symbol = None
        self.target_returns = deque(maxlen=config.lookback_period * 2)
        
        # PCA for factor reduction
        if SKLEARN_AVAILABLE:
            self.pca = PCA(n_components=0.95)  # Keep 95% of variance
            self.scaler = StandardScaler()
            self.kmeans = KMeans(n_clusters=3, random_state=42)
        
    def set_target_symbol(self, symbol: str):
        """Set the target symbol for factor validation"""
        self.target_symbol = symbol
        logger.info(f"Target symbol set to: {symbol}")
    
    def add_factor(self, symbol: str, factor_type: FactorType, 
                  price_data: List[float], volume_data: List[float] = None):
        """Add a factor to the cluster"""
        if volume_data is None:
            volume_data = [1.0] * len(price_data)
        
        # Calculate returns
        returns = []
        if len(price_data) > 1:
            returns = [(price_data[i] - price_data[i-1]) / price_data[i-1] 
                      for i in range(1, len(price_data))]
        
        factor_data = FactorData(
            symbol=symbol,
            factor_type=factor_type,
            price_history=deque(price_data, maxlen=200),
            volume_history=deque(volume_data, maxlen=200),
            returns_history=deque(returns, maxlen=200)
        )
        
        self.factors[symbol] = factor_data
        logger.info(f"Added factor: {symbol} ({factor_type.value})")
        
        # Update correlations if we have enough data
        if len(self.factors) >= self.config.min_factor_count:
            self._update_correlations()
    
    def update_factor_data(self, symbol: str, new_price: float, new_volume: float = 1.0):
        """Update factor data with new price/volume"""
        if symbol not in self.factors:
            logger.warning(f"Factor {symbol} not found")
            return
        
        factor = self.factors[symbol]
        
        # Calculate return
        if len(factor.price_history) > 0:
            last_price = factor.price_history[-1]
            if last_price > 0:
                new_return = (new_price - last_price) / last_price
                factor.returns_history.append(new_return)
        
        # Update price and volume
        factor.price_history.append(new_price)
        factor.volume_history.append(new_volume)
        
        # Update target returns if this is the target symbol
        if symbol == self.target_symbol and len(factor.returns_history) > 0:
            self.target_returns.append(factor.returns_history[-1])
    
    def update_target_data(self, new_price: float, new_volume: float = 1.0):
        """Update target symbol data"""
        if self.target_symbol:
            self.update_factor_data(self.target_symbol, new_price, new_volume)
    
    def _update_correlations(self):
        """Update correlation matrix between factors"""
        if not self.target_symbol or self.target_symbol not in self.factors:
            return
        
        target_returns = list(self.target_returns)
        if len(target_returns) < 10:
            return
        
        # Update correlations with target
        for symbol, factor in self.factors.items():
            if symbol == self.target_symbol:
                continue
            
            factor_returns = list(factor.returns_history)
            if len(factor_returns) < 10:
                continue
            
            # Align returns (use minimum length)
            min_len = min(len(target_returns), len(factor_returns))
            if min_len < 10:
                continue
            
            target_aligned = target_returns[-min_len:]
            factor_aligned = factor_returns[-min_len:]
            
            # Calculate correlation
            correlation = np.corrcoef(target_aligned, factor_aligned)[0, 1]
            if not np.isnan(correlation):
                factor.correlation_with_target = correlation
                self.correlation_matrix[self.target_symbol][symbol] = correlation
                self.correlation_matrix[symbol][self.target_symbol] = correlation
        
        # Update factor weights
        self._update_factor_weights()
        
        self.last_correlation_update = datetime.now()
        logger.debug(f"Updated correlations for {len(self.factors)} factors")
    
    def _update_factor_weights(self):
        """Update factor weights based on correlations and types"""
        if not self.config.enable_dynamic_weights:
            # Use static weights based on factor type
            for factor in self.factors.values():
                if factor.factor_type == FactorType.MARKET:
                    factor.weight = self.config.market_factor_weight
                elif factor.factor_type == FactorType.SECTOR:
                    factor.weight = self.config.sector_factor_weight
                elif factor.factor_type == FactorType.PEER:
                    factor.weight = self.config.peer_factor_weight
                else:
                    factor.weight = self.config.other_factor_weight
            return
        
        # Dynamic weight calculation
        total_abs_correlation = 0
        valid_factors = []
        
        for factor in self.factors.values():
            if (factor.symbol != self.target_symbol and 
                abs(factor.correlation_with_target) >= self.config.min_correlation_for_inclusion):
                valid_factors.append(factor)
                total_abs_correlation += abs(factor.correlation_with_target)
        
        if total_abs_correlation == 0:
            return
        
        # Assign weights based on correlation strength and factor type
        for factor in valid_factors:
            base_weight = abs(factor.correlation_with_target) / total_abs_correlation
            
            # Type-based multiplier
            type_multipliers = {
                FactorType.MARKET: 1.5,
                FactorType.SECTOR: 1.3,
                FactorType.PEER: 1.2,
                FactorType.COMMODITY: 1.0,
                FactorType.CURRENCY: 0.8,
                FactorType.VOLATILITY: 0.9,
                FactorType.INTEREST_RATE: 0.7,
                FactorType.CUSTOM: 1.0
            }
            
            multiplier = type_multipliers.get(factor.factor_type, 1.0)
            factor.weight = base_weight * multiplier
        
        # Normalize weights
        total_weight = sum(f.weight for f in valid_factors)
        if total_weight > 0:
            for factor in valid_factors:
                factor.weight /= total_weight
    
    def get_factor_cluster(self) -> Dict[str, FactorData]:
        """Get current factor cluster"""
        return self.factors.copy()
    
    def get_correlation_matrix(self) -> Dict[str, Dict[str, float]]:
        """Get correlation matrix"""
        return dict(self.correlation_matrix)
    
    def identify_similar_factors(self, threshold: float = 0.8) -> List[List[str]]:
        """Identify groups of highly correlated factors"""
        if not SKLEARN_AVAILABLE:
            return []
        
        # Create correlation matrix for clustering
        symbols = list(self.factors.keys())
        if len(symbols) < 3:
            return []
        
        correlation_data = []
        for i, sym1 in enumerate(symbols):
            row = []
            for j, sym2 in enumerate(symbols):
                if i == j:
                    row.append(1.0)
                else:
                    corr = self.correlation_matrix.get(sym1, {}).get(sym2, 0.0)
                    row.append(abs(corr))
            correlation_data.append(row)
        
        correlation_matrix = np.array(correlation_data)
        
        # Use clustering to identify similar factors
        try:
            n_clusters = min(3, len(symbols) // 2)
            if n_clusters < 2:
                return []
            
            self.kmeans.n_clusters = n_clusters
            clusters = self.kmeans.fit_predict(correlation_matrix)
            
            # Group symbols by cluster
            cluster_groups = defaultdict(list)
            for i, cluster_id in enumerate(clusters):
                cluster_groups[cluster_id].append(symbols[i])
            
            return [group for group in cluster_groups.values() if len(group) > 1]
            
        except Exception as e:
            logger.warning(f"Factor clustering failed: {e}")
            return []

class FactorSignalGenerator:
    """Generates signals from factor data"""
    
    def __init__(self, config: FactorConfig):
        self.config = config
    
    def generate_factor_signals(self, factors: Dict[str, FactorData], 
                              target_symbol: str) -> Dict[str, Tuple[SignalType, float]]:
        """Generate signals from factor analysis"""
        factor_signals = {}
        
        for symbol, factor in factors.items():
            if symbol == target_symbol or len(factor.returns_history) < 5:
                continue
            
            signal, confidence = self._analyze_factor_signal(factor)
            factor_signals[symbol] = (signal, confidence)
            
            # Update factor data
            factor.last_signal = signal
            factor.confidence = confidence
            factor.last_signal_timestamp = datetime.now()
        
        return factor_signals
    
    def _analyze_factor_signal(self, factor: FactorData) -> Tuple[SignalType, float]:
        """Analyze individual factor for signal generation"""
        returns = list(factor.returns_history)
        if len(returns) < 5:
            return SignalType.NEUTRAL, 0.0
        
        # Recent momentum
        recent_returns = returns[-5:]
        momentum = sum(recent_returns)
        
        # Volatility-adjusted momentum
        volatility = np.std(returns[-20:]) if len(returns) >= 20 else np.std(returns)
        if volatility == 0:
            return SignalType.NEUTRAL, 0.0
        
        momentum_score = momentum / volatility
        
        # Volume confirmation (if available)
        volume_confirmation = 1.0
        if len(factor.volume_history) >= 5:
            recent_volume = list(factor.volume_history)[-5:]
            avg_volume = np.mean(list(factor.volume_history)[-20:]) if len(factor.volume_history) >= 20 else np.mean(recent_volume)
            if avg_volume > 0:
                current_volume_ratio = np.mean(recent_volume) / avg_volume
                volume_confirmation = min(2.0, max(0.5, current_volume_ratio))
        
        # Generate signal
        if momentum_score > 0.5:
            signal = SignalType.BUY
            confidence = min(0.9, abs(momentum_score) * volume_confirmation * 0.3)
        elif momentum_score < -0.5:
            signal = SignalType.SELL
            confidence = min(0.9, abs(momentum_score) * volume_confirmation * 0.3)
        else:
            signal = SignalType.NEUTRAL
            confidence = 0.0
        
        return signal, confidence

class FactorValidationEngine:
    """Main factor validation engine"""
    
    def __init__(self, config: FactorConfig = None):
        self.config = config or FactorConfig()
        self.cluster_manager = FactorClusterManager(self.config)
        self.signal_generator = FactorSignalGenerator(self.config)
        self.validation_history = deque(maxlen=100)
        
        logger.info("Factor Validation Engine initialized")
    
    def setup_factor_cluster(self, target_symbol: str, factor_definitions: List[Dict[str, Any]]):
        """Setup factor cluster for a target symbol"""
        self.cluster_manager.set_target_symbol(target_symbol)
        
        for factor_def in factor_definitions:
            symbol = factor_def['symbol']
            factor_type = FactorType(factor_def['type'])
            price_data = factor_def.get('price_data', [])
            volume_data = factor_def.get('volume_data', [])
            
            self.cluster_manager.add_factor(symbol, factor_type, price_data, volume_data)
        
        logger.info(f"Setup factor cluster for {target_symbol} with {len(factor_definitions)} factors")
    
    def update_market_data(self, symbol: str, price: float, volume: float = 1.0):
        """Update market data for a symbol"""
        self.cluster_manager.update_factor_data(symbol, price, volume)
    
    def validate_signal(self, target_signal: SignalType, target_confidence: float, 
                       timestamp: datetime = None) -> FactorValidationResult:
        """Validate a signal against factor cluster"""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Get factor cluster
        factors = self.cluster_manager.get_factor_cluster()
        target_symbol = self.cluster_manager.target_symbol
        
        if not target_symbol or len(factors) < self.config.min_factor_count:
            return self._default_validation_result(target_signal, target_confidence)
        
        # Generate factor signals
        factor_signals = self.signal_generator.generate_factor_signals(factors, target_symbol)
        
        # Analyze factor alignment
        validation_result = self._analyze_factor_alignment(
            target_signal, target_confidence, factor_signals, factors
        )
        
        # Store validation history
        self.validation_history.append({
            'timestamp': timestamp,
            'target_signal': target_signal,
            'target_confidence': target_confidence,
            'validation_result': validation_result,
            'factor_count': len(factor_signals)
        })
        
        return validation_result
    
    def _analyze_factor_alignment(self, target_signal: SignalType, target_confidence: float,
                                factor_signals: Dict[str, Tuple[SignalType, float]],
                                factors: Dict[str, FactorData]) -> FactorValidationResult:
        """Analyze alignment between target signal and factor signals"""
        
        supporting_factors = []
        contradicting_factors = []
        factor_scores = {}
        
        total_supporting_weight = 0.0
        total_contradicting_weight = 0.0
        total_weight = 0.0
        
        # Analyze each factor
        for symbol, (factor_signal, factor_confidence) in factor_signals.items():
            if symbol not in factors:
                continue
            
            factor = factors[symbol]
            weight = factor.weight
            correlation = factor.correlation_with_target
            
            # Calculate factor score
            signal_alignment = self._calculate_signal_alignment(target_signal, factor_signal)
            confidence_weight = factor_confidence * target_confidence
            correlation_weight = abs(correlation)
            
            factor_score = signal_alignment * confidence_weight * correlation_weight * weight
            factor_scores[symbol] = factor_score
            
            # Categorize factors
            if signal_alignment > 0.5:  # Supporting
                supporting_factors.append(symbol)
                total_supporting_weight += weight * correlation_weight
            elif signal_alignment < -0.5:  # Contradicting
                contradicting_factors.append(symbol)
                total_contradicting_weight += weight * correlation_weight
            
            total_weight += weight
        
        # Calculate validation strength
        if total_weight == 0:
            validation_strength = 0.0
        else:
            net_support = (total_supporting_weight - total_contradicting_weight) / total_weight
            validation_strength = net_support
        
        # Determine validation result
        if validation_strength > self.config.confirmation_threshold:
            validation_result = ValidationResult.STRONG_CONFIRMATION
            confidence_adjustment = 1.2
        elif validation_strength > 0.3:
            validation_result = ValidationResult.WEAK_CONFIRMATION
            confidence_adjustment = 1.1
        elif validation_strength < self.config.contradiction_threshold:
            validation_result = ValidationResult.STRONG_CONTRADICTION
            confidence_adjustment = 0.5
        elif validation_strength < -0.1:
            validation_result = ValidationResult.WEAK_CONTRADICTION
            confidence_adjustment = 0.8
        else:
            validation_result = ValidationResult.NEUTRAL
            confidence_adjustment = 1.0
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            validation_result, validation_strength, len(supporting_factors), len(contradicting_factors)
        )
        
        # Get correlation matrix
        correlation_matrix = self.cluster_manager.get_correlation_matrix()
        
        return FactorValidationResult(
            validation_result=validation_result,
            confidence_adjustment=confidence_adjustment,
            supporting_factors=supporting_factors,
            contradicting_factors=contradicting_factors,
            factor_scores=factor_scores,
            correlation_matrix=correlation_matrix,
            validation_strength=validation_strength,
            recommendation=recommendation
        )
    
    def _calculate_signal_alignment(self, target_signal: SignalType, factor_signal: SignalType) -> float:
        """Calculate alignment between target and factor signals"""
        if target_signal == SignalType.NEUTRAL or factor_signal == SignalType.NEUTRAL:
            return 0.0
        
        if target_signal == factor_signal:
            return 1.0  # Perfect alignment
        else:
            return -1.0  # Contradiction
    
    def _generate_recommendation(self, validation_result: ValidationResult, 
                               validation_strength: float, supporting_count: int, 
                               contradicting_count: int) -> str:
        """Generate trading recommendation based on validation"""
        
        if validation_result == ValidationResult.STRONG_CONFIRMATION:
            return f"Strong factor support ({supporting_count} supporting factors). Proceed with confidence."
        elif validation_result == ValidationResult.WEAK_CONFIRMATION:
            return f"Moderate factor support ({supporting_count} supporting, {contradicting_count} contradicting). Proceed with caution."
        elif validation_result == ValidationResult.NEUTRAL:
            return f"Mixed factor signals ({supporting_count} supporting, {contradicting_count} contradicting). Consider additional analysis."
        elif validation_result == ValidationResult.WEAK_CONTRADICTION:
            return f"Weak factor contradiction ({contradicting_count} contradicting factors). Reduce position size or wait."
        else:  # STRONG_CONTRADICTION
            return f"Strong factor contradiction ({contradicting_count} contradicting factors). Avoid trade or consider opposite direction."
    
    def _default_validation_result(self, target_signal: SignalType, 
                                 target_confidence: float) -> FactorValidationResult:
        """Default validation result when insufficient factors"""
        return FactorValidationResult(
            validation_result=ValidationResult.NEUTRAL,
            confidence_adjustment=1.0,
            supporting_factors=[],
            contradicting_factors=[],
            factor_scores={},
            correlation_matrix={},
            validation_strength=0.0,
            recommendation="Insufficient factor data for validation. Proceed based on primary signal only."
        )
    
    def get_factor_summary(self) -> Dict[str, Any]:
        """Get summary of current factor cluster"""
        factors = self.cluster_manager.get_factor_cluster()
        correlation_matrix = self.cluster_manager.get_correlation_matrix()
        
        summary = {
            'target_symbol': self.cluster_manager.target_symbol,
            'factor_count': len(factors),
            'factor_types': {},
            'average_correlation': 0.0,
            'high_correlation_factors': [],
            'low_correlation_factors': [],
            'last_validation_count': len(self.validation_history)
        }
        
        # Factor type distribution
        for factor in factors.values():
            factor_type = factor.factor_type.value
            summary['factor_types'][factor_type] = summary['factor_types'].get(factor_type, 0) + 1
        
        # Correlation analysis
        target_symbol = self.cluster_manager.target_symbol
        if target_symbol and target_symbol in correlation_matrix:
            correlations = [abs(corr) for corr in correlation_matrix[target_symbol].values()]
            if correlations:
                summary['average_correlation'] = np.mean(correlations)
                
                # High/low correlation factors
                for symbol, corr in correlation_matrix[target_symbol].items():
                    if abs(corr) > 0.7:
                        summary['high_correlation_factors'].append((symbol, corr))
                    elif abs(corr) < 0.3:
                        summary['low_correlation_factors'].append((symbol, corr))
        
        return summary
    
    def export_factor_data(self) -> Dict[str, Any]:
        """Export factor data for analysis or storage"""
        factors = self.cluster_manager.get_factor_cluster()
        correlation_matrix = self.cluster_manager.get_correlation_matrix()
        
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'target_symbol': self.cluster_manager.target_symbol,
            'config': {
                'correlation_threshold': self.config.correlation_threshold,
                'confirmation_threshold': self.config.confirmation_threshold,
                'lookback_period': self.config.lookback_period
            },
            'factors': {},
            'correlation_matrix': correlation_matrix,
            'validation_history': []
        }
        
        # Export factor data
        for symbol, factor in factors.items():
            export_data['factors'][symbol] = {
                'symbol': symbol,
                'factor_type': factor.factor_type.value,
                'correlation_with_target': factor.correlation_with_target,
                'weight': factor.weight,
                'last_signal': factor.last_signal.value if factor.last_signal else None,
                'confidence': factor.confidence,
                'price_history_length': len(factor.price_history),
                'returns_history_length': len(factor.returns_history)
            }
        
        # Export recent validation history
        for validation in list(self.validation_history)[-10:]:
            export_data['validation_history'].append({
                'timestamp': validation['timestamp'].isoformat(),
                'target_signal': validation['target_signal'].value,
                'target_confidence': validation['target_confidence'],
                'validation_result': validation['validation_result'].validation_result.value,
                'confidence_adjustment': validation['validation_result'].confidence_adjustment,
                'factor_count': validation['factor_count']
            })
        
        return export_data

# Factory functions
def create_factor_validation_engine(config: FactorConfig = None) -> FactorValidationEngine:
    """Create factor validation engine"""
    return FactorValidationEngine(config)

def create_default_factor_cluster(target_symbol: str, market_symbol: str = "SPY", 
                                 sector_symbol: str = None) -> List[Dict[str, Any]]:
    """Create a default factor cluster for common use cases"""
    factors = [
        {
            'symbol': market_symbol,
            'type': 'market',
            'price_data': [],
            'volume_data': []
        }
    ]
    
    if sector_symbol:
        factors.append({
            'symbol': sector_symbol,
            'type': 'sector',
            'price_data': [],
            'volume_data': []
        })
    
    # Add volatility factor
    factors.append({
        'symbol': 'VIX',
        'type': 'volatility',
        'price_data': [],
        'volume_data': []
    })
    
    return factors