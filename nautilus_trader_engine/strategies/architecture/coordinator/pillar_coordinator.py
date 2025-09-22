"""Pillar Coordinator - 5-Pillar Strategy Architecture

This module coordinates all 5 pillars of the strategy architecture:
1. Signal Generation
2. Market Regime Detection
3. Risk Management
4. Execution Intent
5. Performance Analytics

Author: Vincent S. Pereira
Version: 1.0.0
"""

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
from dataclasses import dataclass, field
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import all pillar components
from ..pillars.signal_generation import (
    SignalGenerator, TradingSignal, SignalStrength, SignalType,
    create_signal_generator
)
from ..pillars.market_regime_detection import (
    MarketRegimeDetector, MarketRegime, RegimeStrength,
    create_market_regime_detector
)
from ..pillars.risk_management import (
    RiskManager, RiskLevel, PositionSizeResult,
    create_risk_manager
)
from ..pillars.execution_intent import (
    ExecutionIntentManager, ExecutionIntent, OrderType, ExecutionAlgorithm,
    create_execution_intent_manager
)
from ..pillars.performance_analytics import (
    PerformanceAnalyticsManager, PerformanceReport, ReportingPeriod,
    create_performance_analytics_manager
)
from ....indicators.consolidated_indicators import ConsolidatedIndicators

logger = logging.getLogger(__name__)

# ===========================================
# ENUMS AND TYPES
# ===========================================

class StrategyState(Enum):
    """Strategy execution states"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"

class CoordinationMode(Enum):
    """Coordination modes for pillar interaction"""
    SEQUENTIAL = "sequential"  # Execute pillars in sequence
    PARALLEL = "parallel"     # Execute pillars in parallel where possible
    ADAPTIVE = "adaptive"     # Dynamically choose based on conditions

class DecisionConfidence(Enum):
    """Confidence levels for trading decisions"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

# ===========================================
# DATA CLASSES
# ===========================================

@dataclass
class StrategyDecision:
    """Comprehensive strategy decision from all pillars"""
    # Signal Information
    primary_signal: TradingSignal
    supporting_signals: List[TradingSignal]
    signal_consensus: float  # -1 to 1
    
    # Market Context
    market_regime: MarketRegime
    regime_strength: RegimeStrength
    regime_confidence: float
    
    # Risk Assessment
    risk_level: RiskLevel
    position_size: PositionSizeResult
    risk_adjusted_size: float
    
    # Execution Plan
    execution_intent: Optional[ExecutionIntent]
    execution_urgency: str
    
    # Decision Metadata
    overall_confidence: DecisionConfidence
    decision_timestamp: datetime
    contributing_factors: Dict[str, Any]
    warnings: List[str]
    
@dataclass
class PillarStatus:
    """Status of individual pillars"""
    pillar_name: str
    is_active: bool
    last_update: datetime
    processing_time_ms: float
    error_count: int
    last_error: Optional[str]
    performance_metrics: Dict[str, float]

@dataclass
class CoordinatorConfig:
    """Configuration for the pillar coordinator"""
    coordination_mode: CoordinationMode = CoordinationMode.ADAPTIVE
    max_parallel_workers: int = 4
    decision_timeout_seconds: float = 5.0
    min_signal_confidence: float = 0.3
    min_regime_confidence: float = 0.5
    enable_risk_override: bool = True
    performance_tracking: bool = True
    
@dataclass
class StrategyMetrics:
    """Real-time strategy metrics"""
    total_decisions: int
    successful_decisions: int
    average_decision_time_ms: float
    signal_accuracy: float
    regime_accuracy: float
    risk_adjusted_returns: float
    current_drawdown: float
    active_positions: int
    
# ===========================================
# PILLAR COORDINATOR
# ===========================================

class PillarCoordinator:
    """Coordinates all 5 pillars of the strategy architecture"""
    
    def __init__(self, config: CoordinatorConfig):
        self.config = config
        self.state = StrategyState.INITIALIZING
        
        # Pillar managers
        self.signal_generator: Optional[SignalGenerator] = None
        self.regime_detector: Optional[MarketRegimeDetector] = None
        self.risk_manager: Optional[RiskManager] = None
        self.execution_manager: Optional[ExecutionIntentManager] = None
        self.performance_manager: Optional[PerformanceAnalyticsManager] = None
        
        # Status tracking
        self.pillar_status: Dict[str, PillarStatus] = {}
        self.decision_history: List[StrategyDecision] = []
        self.strategy_metrics = StrategyMetrics(
            total_decisions=0,
            successful_decisions=0,
            average_decision_time_ms=0.0,
            signal_accuracy=0.0,
            regime_accuracy=0.0,
            risk_adjusted_returns=0.0,
            current_drawdown=0.0,
            active_positions=0
        )
        
        # Thread pool for parallel execution
        self.executor = ThreadPoolExecutor(max_workers=config.max_parallel_workers)
        
        # Performance tracking
        self.decision_times: List[float] = []
        self.last_performance_update = datetime.now()
        
    async def initialize(self) -> bool:
        """Initialize all pillars"""
        try:
            logger.info("Initializing 5-Pillar Strategy Architecture...")
            
            # Initialize all pillars
            self.signal_generator = await create_signal_generator()
            self.regime_detector = await create_market_regime_detector()
            self.risk_manager = await create_risk_manager()
            self.execution_manager = await create_execution_intent_manager()
            self.performance_manager = await create_performance_analytics_manager()
            
            # Initialize pillar status tracking
            pillar_names = [
                "signal_generation", "market_regime_detection", 
                "risk_management", "execution_intent", "performance_analytics"
            ]
            
            for name in pillar_names:
                self.pillar_status[name] = PillarStatus(
                    pillar_name=name,
                    is_active=True,
                    last_update=datetime.now(),
                    processing_time_ms=0.0,
                    error_count=0,
                    last_error=None,
                    performance_metrics={}
                )
            
            self.state = StrategyState.ACTIVE
            logger.info("5-Pillar Strategy Architecture initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize pillars: {e}")
            self.state = StrategyState.ERROR
            return False
    
    async def make_strategy_decision(
        self,
        market_data: Dict[str, Any],
        portfolio_state: Dict[str, Any]
    ) -> StrategyDecision:
        """Make comprehensive strategy decision using all pillars"""
        
        start_time = datetime.now()
        warnings = []
        
        try:
            if self.state != StrategyState.ACTIVE:
                raise ValueError(f"Coordinator not active. Current state: {self.state}")
            
            # Execute pillars based on coordination mode
            if self.config.coordination_mode == CoordinationMode.PARALLEL:
                results = await self._execute_pillars_parallel(market_data, portfolio_state)
            else:
                results = await self._execute_pillars_sequential(market_data, portfolio_state)
            
            # Extract results
            signals = results.get('signals', [])
            regime_info = results.get('regime', {})
            risk_assessment = results.get('risk', {})
            
            # Validate results
            if not signals:
                warnings.append("No signals generated")
                signals = [self._create_neutral_signal()]
            
            # Calculate signal consensus
            signal_consensus = self._calculate_signal_consensus(signals)
            
            # Determine primary signal
            primary_signal = max(signals, key=lambda s: s.confidence) if signals else self._create_neutral_signal()
            supporting_signals = [s for s in signals if s != primary_signal]
            
            # Extract regime information
            market_regime = regime_info.get('regime', MarketRegime.NEUTRAL)
            regime_strength = regime_info.get('strength', RegimeStrength.WEAK)
            regime_confidence = regime_info.get('confidence', 0.5)
            
            # Extract risk assessment
            risk_level = risk_assessment.get('risk_level', RiskLevel.MEDIUM)
            position_size = risk_assessment.get('position_size')
            risk_adjusted_size = risk_assessment.get('adjusted_size', 0.0)
            
            # Create execution intent if signal is strong enough
            execution_intent = None
            execution_urgency = "low"
            
            if (abs(signal_consensus) >= self.config.min_signal_confidence and 
                regime_confidence >= self.config.min_regime_confidence):
                
                execution_intent = await self._create_execution_intent(
                    primary_signal, position_size, market_data
                )
                execution_urgency = self._determine_execution_urgency(
                    primary_signal, market_regime, risk_level
                )
            
            # Determine overall confidence
            overall_confidence = self._calculate_overall_confidence(
                signal_consensus, regime_confidence, risk_level
            )
            
            # Create strategy decision
            decision = StrategyDecision(
                primary_signal=primary_signal,
                supporting_signals=supporting_signals,
                signal_consensus=signal_consensus,
                market_regime=market_regime,
                regime_strength=regime_strength,
                regime_confidence=regime_confidence,
                risk_level=risk_level,
                position_size=position_size,
                risk_adjusted_size=risk_adjusted_size,
                execution_intent=execution_intent,
                execution_urgency=execution_urgency,
                overall_confidence=overall_confidence,
                decision_timestamp=datetime.now(),
                contributing_factors={
                    'signal_count': len(signals),
                    'regime_detected': market_regime.value,
                    'risk_override': self.config.enable_risk_override
                },
                warnings=warnings
            )
            
            # Update metrics
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_metrics(decision, processing_time)
            
            # Store decision
            self.decision_history.append(decision)
            if len(self.decision_history) > 1000:  # Keep last 1000 decisions
                self.decision_history = self.decision_history[-1000:]
            
            logger.info(f"Strategy decision made: {primary_signal.signal_type.value} with {overall_confidence.value} confidence")
            return decision
            
        except Exception as e:
            logger.error(f"Error making strategy decision: {e}")
            self.state = StrategyState.ERROR
            raise
    
    async def _execute_pillars_parallel(self, market_data: Dict[str, Any], portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute pillars in parallel"""
        
        tasks = []
        
        # Signal generation
        if self.signal_generator:
            tasks.append(self._run_signal_generation(market_data))
        
        # Market regime detection
        if self.regime_detector:
            tasks.append(self._run_regime_detection(market_data))
        
        # Risk management
        if self.risk_manager:
            tasks.append(self._run_risk_assessment(market_data, portfolio_state))
        
        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = {}
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Pillar execution failed: {result}")
            else:
                processed_results.update(result)
        
        return processed_results
    
    async def _execute_pillars_sequential(self, market_data: Dict[str, Any], portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute pillars sequentially"""
        
        results = {}
        
        # 1. Market regime detection (informs other pillars)
        if self.regime_detector:
            regime_result = await self._run_regime_detection(market_data)
            results.update(regime_result)
        
        # 2. Signal generation (uses regime information)
        if self.signal_generator:
            signal_result = await self._run_signal_generation(market_data)
            results.update(signal_result)
        
        # 3. Risk management (uses signals and regime)
        if self.risk_manager:
            risk_result = await self._run_risk_assessment(market_data, portfolio_state)
            results.update(risk_result)
        
        return results
    
    async def _run_signal_generation(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run signal generation pillar"""
        start_time = datetime.now()
        
        try:
            # Extract price data
            prices = market_data.get('prices', pd.Series())
            volume = market_data.get('volume', pd.Series())
            
            if len(prices) < 50:  # Need minimum data
                return {'signals': []}
            
            # Generate signals
            signals = await self.signal_generator.generate_signals(prices, volume)
            
            # Update status
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_pillar_status('signal_generation', processing_time)
            
            return {'signals': signals}
            
        except Exception as e:
            self._update_pillar_status('signal_generation', 0, str(e))
            logger.error(f"Signal generation failed: {e}")
            return {'signals': []}
    
    async def _run_regime_detection(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run market regime detection pillar"""
        start_time = datetime.now()
        
        try:
            # Extract market data
            prices = market_data.get('prices', pd.Series())
            volume = market_data.get('volume', pd.Series())
            
            if len(prices) < 100:  # Need more data for regime detection
                return {
                    'regime': MarketRegime.NEUTRAL,
                    'strength': RegimeStrength.WEAK,
                    'confidence': 0.5
                }
            
            # Detect regime
            regime_detection = await self.regime_detector.detect_regime(prices, volume)
            
            # Update status
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_pillar_status('market_regime_detection', processing_time)
            
            return {
                'regime': regime_detection.regime,
                'strength': regime_detection.strength,
                'confidence': regime_detection.confidence
            }
            
        except Exception as e:
            self._update_pillar_status('market_regime_detection', 0, str(e))
            logger.error(f"Regime detection failed: {e}")
            return {
                'regime': MarketRegime.NEUTRAL,
                'strength': RegimeStrength.WEAK,
                'confidence': 0.5
            }
    
    async def _run_risk_assessment(self, market_data: Dict[str, Any], portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
        """Run risk management pillar"""
        start_time = datetime.now()
        
        try:
            # Extract portfolio information
            portfolio_value = portfolio_state.get('total_value', 100000)
            current_positions = portfolio_state.get('positions', {})
            
            # Calculate position size
            position_size = await self.risk_manager.calculate_position_size(
                symbol="SAMPLE",
                entry_price=market_data.get('current_price', 100),
                stop_loss=market_data.get('current_price', 100) * 0.98,
                portfolio_value=portfolio_value
            )
            
            # Assess risk level
            risk_level = RiskLevel.MEDIUM  # Simplified
            
            # Update status
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_pillar_status('risk_management', processing_time)
            
            return {
                'risk_level': risk_level,
                'position_size': position_size,
                'adjusted_size': position_size.recommended_size if position_size else 0.0
            }
            
        except Exception as e:
            self._update_pillar_status('risk_management', 0, str(e))
            logger.error(f"Risk assessment failed: {e}")
            return {
                'risk_level': RiskLevel.HIGH,
                'position_size': None,
                'adjusted_size': 0.0
            }
    
    def _calculate_signal_consensus(self, signals: List[TradingSignal]) -> float:
        """Calculate consensus from multiple signals"""
        if not signals:
            return 0.0
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for signal in signals:
            # Convert signal type to numeric value
            signal_value = 1.0 if signal.signal_type == SignalType.BUY else -1.0 if signal.signal_type == SignalType.SELL else 0.0
            weight = signal.confidence
            
            weighted_sum += signal_value * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _create_neutral_signal(self) -> TradingSignal:
        """Create a neutral signal as fallback"""
        return TradingSignal(
            signal_type=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            confidence=0.1,
            price_target=None,
            stop_loss=None,
            timeframe="1D",
            indicators_used=["fallback"],
            metadata={"reason": "fallback_signal"}
        )
    
    async def _create_execution_intent(self, signal: TradingSignal, position_size: Optional[PositionSizeResult], market_data: Dict[str, Any]) -> Optional[ExecutionIntent]:
        """Create execution intent from signal and position size"""
        if not position_size or position_size.recommended_size == 0:
            return None
        
        side = "buy" if signal.signal_type == SignalType.BUY else "sell" if signal.signal_type == SignalType.SELL else None
        if not side:
            return None
        
        return await self.execution_manager.create_intent(
            symbol=market_data.get('symbol', 'UNKNOWN'),
            side=side,
            quantity=position_size.recommended_size,
            target_price=signal.price_target,
            order_type=OrderType.LIMIT if signal.price_target else OrderType.MARKET,
            execution_algorithm=ExecutionAlgorithm.ADAPTIVE
        )
    
    def _determine_execution_urgency(self, signal: TradingSignal, regime: MarketRegime, risk_level: RiskLevel) -> str:
        """Determine execution urgency based on signal and market conditions"""
        if signal.strength == SignalStrength.VERY_STRONG:
            return "high"
        elif regime == MarketRegime.VOLATILE or risk_level == RiskLevel.HIGH:
            return "medium"
        else:
            return "low"
    
    def _calculate_overall_confidence(self, signal_consensus: float, regime_confidence: float, risk_level: RiskLevel) -> DecisionConfidence:
        """Calculate overall decision confidence"""
        # Combine different confidence factors
        signal_factor = abs(signal_consensus)
        regime_factor = regime_confidence
        risk_factor = 1.0 if risk_level == RiskLevel.LOW else 0.8 if risk_level == RiskLevel.MEDIUM else 0.5
        
        overall = (signal_factor + regime_factor + risk_factor) / 3.0
        
        if overall >= 0.8:
            return DecisionConfidence.VERY_HIGH
        elif overall >= 0.65:
            return DecisionConfidence.HIGH
        elif overall >= 0.5:
            return DecisionConfidence.MEDIUM
        elif overall >= 0.35:
            return DecisionConfidence.LOW
        else:
            return DecisionConfidence.VERY_LOW
    
    def _update_pillar_status(self, pillar_name: str, processing_time: float, error: Optional[str] = None):
        """Update pillar status"""
        if pillar_name in self.pillar_status:
            status = self.pillar_status[pillar_name]
            status.last_update = datetime.now()
            status.processing_time_ms = processing_time
            
            if error:
                status.error_count += 1
                status.last_error = error
                status.is_active = False
            else:
                status.is_active = True
    
    def _update_metrics(self, decision: StrategyDecision, processing_time: float):
        """Update strategy metrics"""
        self.strategy_metrics.total_decisions += 1
        self.decision_times.append(processing_time)
        
        # Keep only last 100 decision times for average calculation
        if len(self.decision_times) > 100:
            self.decision_times = self.decision_times[-100:]
        
        self.strategy_metrics.average_decision_time_ms = sum(self.decision_times) / len(self.decision_times)
        
        # Update success rate (simplified)
        if decision.overall_confidence in [DecisionConfidence.HIGH, DecisionConfidence.VERY_HIGH]:
            self.strategy_metrics.successful_decisions += 1
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive coordinator status"""
        return {
            'state': self.state.value,
            'pillar_status': {name: {
                'active': status.is_active,
                'last_update': status.last_update.isoformat(),
                'processing_time_ms': status.processing_time_ms,
                'error_count': status.error_count,
                'last_error': status.last_error
            } for name, status in self.pillar_status.items()},
            'strategy_metrics': {
                'total_decisions': self.strategy_metrics.total_decisions,
                'successful_decisions': self.strategy_metrics.successful_decisions,
                'success_rate': self.strategy_metrics.successful_decisions / max(1, self.strategy_metrics.total_decisions),
                'average_decision_time_ms': self.strategy_metrics.average_decision_time_ms
            },
            'recent_decisions': len(self.decision_history)
        }
    
    async def shutdown(self):
        """Shutdown coordinator and cleanup resources"""
        logger.info("Shutting down 5-Pillar Strategy Architecture...")
        self.state = StrategyState.STOPPED
        self.executor.shutdown(wait=True)
        logger.info("Coordinator shutdown complete")

# ===========================================
# FACTORY FUNCTIONS
# ===========================================

async def create_pillar_coordinator(config: Optional[CoordinatorConfig] = None) -> PillarCoordinator:
    """Factory function to create and initialize PillarCoordinator"""
    if config is None:
        config = CoordinatorConfig()
    
    coordinator = PillarCoordinator(config)
    
    # Initialize all pillars
    success = await coordinator.initialize()
    if not success:
        raise RuntimeError("Failed to initialize PillarCoordinator")
    
    logger.info("PillarCoordinator created and initialized successfully")
    return coordinator

# Example usage
if __name__ == "__main__":
    async def main():
        # Create coordinator
        config = CoordinatorConfig(
            coordination_mode=CoordinationMode.PARALLEL,
            min_signal_confidence=0.4,
            min_regime_confidence=0.6
        )
        
        coordinator = await create_pillar_coordinator(config)
        
        # Sample market data
        dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
        prices = pd.Series(np.random.randn(len(dates)).cumsum() + 100, index=dates)
        volume = pd.Series(np.random.randint(1000, 10000, len(dates)), index=dates)
        
        market_data = {
            'symbol': 'AAPL',
            'prices': prices,
            'volume': volume,
            'current_price': prices.iloc[-1]
        }
        
        portfolio_state = {
            'total_value': 100000,
            'positions': {}
        }
        
        # Make strategy decision
        decision = await coordinator.make_strategy_decision(market_data, portfolio_state)
        
        print(f"Strategy Decision:")
        print(f"Primary Signal: {decision.primary_signal.signal_type.value}")
        print(f"Signal Consensus: {decision.signal_consensus:.3f}")
        print(f"Market Regime: {decision.market_regime.value}")
        print(f"Risk Level: {decision.risk_level.value}")
        print(f"Overall Confidence: {decision.overall_confidence.value}")
        
        if decision.execution_intent:
            print(f"Execution Intent: {decision.execution_intent.side} {decision.execution_intent.quantity}")
        
        # Get status
        status = coordinator.get_status()
        print(f"\nCoordinator Status: {status['state']}")
        print(f"Total Decisions: {status['strategy_metrics']['total_decisions']}")
        print(f"Success Rate: {status['strategy_metrics']['success_rate']:.2%}")
        
        # Shutdown
        await coordinator.shutdown()
    
    asyncio.run(main())