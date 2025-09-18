"""Risk Management Engine

Core risk management engine that orchestrates all risk components,
provides unified risk assessment, and manages risk workflows.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
import logging
from dataclasses import asdict
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

from ..models.risk_models import (
    RiskLimits, RiskAssessmentRequest, RiskAssessmentResponse,
    RiskCheckResult, RiskLevel, RiskMetric, RiskViolation,
    PortfolioRiskSummary, OrderRiskAssessment, VaRResult
)
from ..calculators.var_calculator import VaRCalculator
from ..calculators.position_sizer import PositionSizer
from ..monitors.realtime_monitor import RealTimeRiskMonitor

# Configure logging
logger = logging.getLogger(__name__)

class RiskEngine:
    """Comprehensive risk management engine"""
    
    def __init__(self, 
                 risk_limits: Optional[RiskLimits] = None,
                 enable_realtime_monitoring: bool = True,
                 monitoring_interval: float = 1.0,
                 max_workers: int = 4):
        """
        Initialize risk engine
        
        Args:
            risk_limits: Risk limits configuration
            enable_realtime_monitoring: Enable real-time monitoring
            monitoring_interval: Real-time monitoring interval in seconds
            max_workers: Maximum worker threads for parallel processing
        """
        self.risk_limits = risk_limits or RiskLimits()
        self.enable_realtime_monitoring = enable_realtime_monitoring
        self.monitoring_interval = monitoring_interval
        
        # Initialize components
        self.var_calculator = VaRCalculator()
        self.position_sizer = PositionSizer(self.risk_limits)
        
        # Real-time monitoring
        self.realtime_monitor: Optional[RealTimeRiskMonitor] = None
        if enable_realtime_monitoring:
            self.realtime_monitor = RealTimeRiskMonitor(
                risk_limits=self.risk_limits,
                update_interval=monitoring_interval
            )
        
        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Risk engine state
        self.is_initialized = False
        self.risk_cache: Dict[str, Any] = {}
        self.cache_ttl = 60  # Cache TTL in seconds
        
        # Performance metrics
        self.assessment_count = 0
        self.total_processing_time = 0.0
        
        # Event callbacks
        self.risk_violation_callbacks: List[Callable] = []
        self.risk_assessment_callbacks: List[Callable] = []
    
    async def initialize(self) -> None:
        """Initialize the risk engine"""
        
        if self.is_initialized:
            logger.warning("Risk engine already initialized")
            return
        
        try:
            # Initialize components
            logger.info("Initializing risk engine components...")
            
            # Setup real-time monitoring if enabled
            if self.realtime_monitor:
                # Add violation callback
                self.realtime_monitor.add_alert_callback(self._handle_risk_violation)
                logger.info("Real-time risk monitoring configured")
            
            self.is_initialized = True
            logger.info("Risk engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize risk engine: {str(e)}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the risk engine"""
        
        logger.info("Shutting down risk engine...")
        
        try:
            # Stop real-time monitoring
            if self.realtime_monitor and self.realtime_monitor.is_monitoring:
                await self.realtime_monitor.stop_monitoring()
            
            # Shutdown thread pool
            self.executor.shutdown(wait=True)
            
            self.is_initialized = False
            logger.info("Risk engine shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during risk engine shutdown: {str(e)}")
    
    async def assess_order_risk(
        self, 
        request: RiskAssessmentRequest
    ) -> RiskAssessmentResponse:
        """Assess risk for a trading order"""
        
        if not self.is_initialized:
            await self.initialize()
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Validate request
            self._validate_risk_request(request)
            
            # Check cache first
            cache_key = self._generate_cache_key(request)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                return cached_result
            
            # Perform risk assessment
            assessment = await self._perform_order_risk_assessment(request)
            
            # Cache result
            self._cache_result(cache_key, assessment)
            
            # Update performance metrics
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.assessment_count += 1
            self.total_processing_time += processing_time
            
            # Trigger callbacks
            await self._trigger_assessment_callbacks(request, assessment)
            
            logger.debug(f"Order risk assessment completed in {processing_time:.3f}s")
            
            return assessment
            
        except Exception as e:
            logger.error(f"Error in order risk assessment: {str(e)}")
            
            # Return rejection response
            return RiskAssessmentResponse(
                request_id=request.request_id,
                account_id=request.account_id,
                result=RiskCheckResult.REJECTED,
                risk_level=RiskLevel.HIGH,
                approved_quantity=0,
                rejection_reason=f"Risk assessment error: {str(e)}",
                risk_metrics=[],
                violations=[]
            )
    
    async def _perform_order_risk_assessment(
        self, 
        request: RiskAssessmentRequest
    ) -> RiskAssessmentResponse:
        """Perform comprehensive order risk assessment"""
        
        risk_metrics = []
        violations = []
        
        # Get current portfolio data
        portfolio_data = await self._get_portfolio_data(request.account_id)
        
        # Position size check
        position_check = await self._check_position_size_risk(
            request, portfolio_data
        )
        risk_metrics.extend(position_check['metrics'])
        violations.extend(position_check['violations'])
        
        # Exposure check
        exposure_check = await self._check_exposure_risk(
            request, portfolio_data
        )
        risk_metrics.extend(exposure_check['metrics'])
        violations.extend(exposure_check['violations'])
        
        # Concentration check
        concentration_check = await self._check_concentration_risk(
            request, portfolio_data
        )
        risk_metrics.extend(concentration_check['metrics'])
        violations.extend(concentration_check['violations'])
        
        # Leverage check
        leverage_check = await self._check_leverage_risk(
            request, portfolio_data
        )
        risk_metrics.extend(leverage_check['metrics'])
        violations.extend(leverage_check['violations'])
        
        # VaR impact check
        var_check = await self._check_var_impact(
            request, portfolio_data
        )
        risk_metrics.extend(var_check['metrics'])
        violations.extend(var_check['violations'])
        
        # Determine overall result
        if violations:
            result = RiskCheckResult.REJECTED
            risk_level = max(v.severity for v in violations)
            approved_quantity = 0
            rejection_reason = f"Risk violations: {', '.join(v.violation_type.value for v in violations)}"
        else:
            # Calculate approved quantity based on risk metrics
            approved_quantity = await self._calculate_approved_quantity(
                request, risk_metrics
            )
            
            if approved_quantity >= request.quantity:
                result = RiskCheckResult.APPROVED
                risk_level = RiskLevel.LOW
                rejection_reason = None
            elif approved_quantity > 0:
                result = RiskCheckResult.PARTIAL
                risk_level = RiskLevel.MEDIUM
                rejection_reason = f"Partial approval: {approved_quantity} of {request.quantity}"
            else:
                result = RiskCheckResult.REJECTED
                risk_level = RiskLevel.HIGH
                rejection_reason = "Insufficient risk capacity"
        
        return RiskAssessmentResponse(
            request_id=request.request_id,
            account_id=request.account_id,
            result=result,
            risk_level=risk_level,
            approved_quantity=approved_quantity,
            rejection_reason=rejection_reason,
            risk_metrics=risk_metrics,
            violations=violations,
            assessment_timestamp=datetime.now(timezone.utc)
        )
    
    async def _check_position_size_risk(
        self, 
        request: RiskAssessmentRequest, 
        portfolio_data: Dict[str, Any]
    ) -> Dict[str, List]:
        """Check position size risk"""
        
        metrics = []
        violations = []
        
        try:
            # Calculate position value
            position_value = request.quantity * request.price
            
            # Check against maximum position size
            max_position_value = self.risk_limits.max_position_size
            
            if position_value > max_position_value:
                from ..models.risk_models import RiskViolationType
                violation = RiskViolation(
                    violation_type=RiskViolationType.POSITION_LIMIT,
                    severity=RiskLevel.HIGH,
                    current_value=position_value,
                    limit_value=max_position_value,
                    excess_amount=0,  # Will be calculated in __post_init__
                    account_id=request.account_id,
                    message=f"Position size ${position_value:,.2f} exceeds limit ${max_position_value:,.2f}"
                )
                violations.append(violation)
            
            # Create position size metric
            from ..models.risk_models import RiskMetricType
            metric = RiskMetric(
                metric_type=RiskMetricType.POSITION_SIZE,
                current_value=position_value,
                limit_value=max_position_value,
                utilization_percent=0,  # Will be calculated in __post_init__
                risk_level=RiskLevel.LOW,  # Will be determined in __post_init__
                timestamp=datetime.now(timezone.utc),
                account_id=request.account_id
            )
            metrics.append(metric)
            
        except Exception as e:
            logger.error(f"Error in position size risk check: {str(e)}")
        
        return {'metrics': metrics, 'violations': violations}
    
    async def _check_exposure_risk(
        self, 
        request: RiskAssessmentRequest, 
        portfolio_data: Dict[str, Any]
    ) -> Dict[str, List]:
        """Check portfolio exposure risk"""
        
        metrics = []
        violations = []
        
        try:
            # Calculate new total exposure
            current_exposure = portfolio_data.get('total_exposure', 0)
            new_position_value = request.quantity * request.price
            new_total_exposure = current_exposure + new_position_value
            
            # Check against maximum exposure
            max_exposure = self.risk_limits.max_portfolio_exposure
            
            if new_total_exposure > max_exposure:
                from ..models.risk_models import RiskViolationType
                violation = RiskViolation(
                    violation_type=RiskViolationType.EXPOSURE_LIMIT,
                    severity=RiskLevel.HIGH,
                    current_value=new_total_exposure,
                    limit_value=max_exposure,
                    excess_amount=0,  # Will be calculated in __post_init__
                    account_id=request.account_id,
                    message=f"Total exposure ${new_total_exposure:,.2f} exceeds limit ${max_exposure:,.2f}"
                )
                violations.append(violation)
            
            # Create exposure metric
            from ..models.risk_models import RiskMetricType
            metric = RiskMetric(
                metric_type=RiskMetricType.PORTFOLIO_EXPOSURE,
                current_value=new_total_exposure,
                limit_value=max_exposure,
                utilization_percent=0,  # Will be calculated in __post_init__
                risk_level=RiskLevel.LOW,  # Will be determined in __post_init__
                timestamp=datetime.now(timezone.utc),
                account_id=request.account_id
            )
            metrics.append(metric)
            
        except Exception as e:
            logger.error(f"Error in exposure risk check: {str(e)}")
        
        return {'metrics': metrics, 'violations': violations}
    
    async def _check_concentration_risk(
        self, 
        request: RiskAssessmentRequest, 
        portfolio_data: Dict[str, Any]
    ) -> Dict[str, List]:
        """Check position concentration risk"""
        
        metrics = []
        violations = []
        
        try:
            total_value = portfolio_data.get('total_value', 0)
            if total_value <= 0:
                return {'metrics': metrics, 'violations': violations}
            
            # Calculate new position concentration
            current_position_value = portfolio_data.get('positions', {}).get(
                request.symbol, {}
            ).get('market_value', 0)
            
            new_position_value = current_position_value + (request.quantity * request.price)
            concentration_percent = (new_position_value / total_value) * 100
            
            # Check against maximum concentration
            max_concentration = self.risk_limits.max_concentration_percent
            
            if concentration_percent > max_concentration:
                from ..models.risk_models import RiskViolationType
                violation = RiskViolation(
                    violation_type=RiskViolationType.CONCENTRATION_LIMIT,
                    severity=RiskLevel.MEDIUM,
                    current_value=concentration_percent,
                    limit_value=max_concentration,
                    excess_amount=0,  # Will be calculated in __post_init__
                    account_id=request.account_id,
                    message=f"Position concentration {concentration_percent:.1f}% exceeds limit {max_concentration:.1f}%"
                )
                violations.append(violation)
            
            # Create concentration metric
            from ..models.risk_models import RiskMetricType
            metric = RiskMetric(
                metric_type=RiskMetricType.CONCENTRATION,
                current_value=concentration_percent,
                limit_value=max_concentration,
                utilization_percent=0,  # Will be calculated in __post_init__
                risk_level=RiskLevel.LOW,  # Will be determined in __post_init__
                timestamp=datetime.now(timezone.utc),
                account_id=request.account_id
            )
            metrics.append(metric)
            
        except Exception as e:
            logger.error(f"Error in concentration risk check: {str(e)}")
        
        return {'metrics': metrics, 'violations': violations}
    
    async def _check_leverage_risk(
        self, 
        request: RiskAssessmentRequest, 
        portfolio_data: Dict[str, Any]
    ) -> Dict[str, List]:
        """Check leverage risk"""
        
        metrics = []
        violations = []
        
        try:
            total_value = portfolio_data.get('total_value', 0)
            cash = portfolio_data.get('cash', 0)
            current_exposure = portfolio_data.get('total_exposure', 0)
            
            if total_value <= 0:
                return {'metrics': metrics, 'violations': violations}
            
            # Calculate new leverage
            new_position_value = request.quantity * request.price
            new_total_exposure = current_exposure + new_position_value
            new_leverage = new_total_exposure / (total_value - cash + new_total_exposure)
            
            # Check against maximum leverage
            max_leverage = self.risk_limits.max_leverage
            
            if new_leverage > max_leverage:
                from ..models.risk_models import RiskViolationType
                violation = RiskViolation(
                    violation_type=RiskViolationType.LEVERAGE_LIMIT,
                    severity=RiskLevel.HIGH,
                    current_value=new_leverage,
                    limit_value=max_leverage,
                    excess_amount=0,  # Will be calculated in __post_init__
                    account_id=request.account_id,
                    message=f"Leverage {new_leverage:.2f}x exceeds limit {max_leverage:.2f}x"
                )
                violations.append(violation)
            
            # Create leverage metric
            from ..models.risk_models import RiskMetricType
            metric = RiskMetric(
                metric_type=RiskMetricType.LEVERAGE,
                current_value=new_leverage,
                limit_value=max_leverage,
                utilization_percent=0,  # Will be calculated in __post_init__
                risk_level=RiskLevel.LOW,  # Will be determined in __post_init__
                timestamp=datetime.now(timezone.utc),
                account_id=request.account_id
            )
            metrics.append(metric)
            
        except Exception as e:
            logger.error(f"Error in leverage risk check: {str(e)}")
        
        return {'metrics': metrics, 'violations': violations}
    
    async def _check_var_impact(
        self, 
        request: RiskAssessmentRequest, 
        portfolio_data: Dict[str, Any]
    ) -> Dict[str, List]:
        """Check VaR impact of new position"""
        
        metrics = []
        violations = []
        
        try:
            # This would require historical price data and correlation analysis
            # For now, implement a simplified version
            
            total_value = portfolio_data.get('total_value', 0)
            if total_value <= 0:
                return {'metrics': metrics, 'violations': violations}
            
            # Estimate VaR impact (simplified)
            position_value = request.quantity * request.price
            estimated_var_impact = position_value * 0.02  # 2% daily VaR assumption
            
            # Check against VaR limit
            var_limit = total_value * (self.risk_limits.max_var_percentage / 100)
            
            if estimated_var_impact > var_limit:
                from ..models.risk_models import RiskViolationType
                violation = RiskViolation(
                    violation_type=RiskViolationType.VAR_LIMIT,
                    severity=RiskLevel.MEDIUM,
                    current_value=estimated_var_impact,
                    limit_value=var_limit,
                    excess_amount=0,  # Will be calculated in __post_init__
                    account_id=request.account_id,
                    message=f"Estimated VaR impact ${estimated_var_impact:,.2f} exceeds limit ${var_limit:,.2f}"
                )
                violations.append(violation)
            
            # Create VaR metric
            from ..models.risk_models import RiskMetricType
            metric = RiskMetric(
                metric_type=RiskMetricType.VAR,
                current_value=estimated_var_impact,
                limit_value=var_limit,
                utilization_percent=0,  # Will be calculated in __post_init__
                risk_level=RiskLevel.LOW,  # Will be determined in __post_init__
                timestamp=datetime.now(timezone.utc),
                account_id=request.account_id
            )
            metrics.append(metric)
            
        except Exception as e:
            logger.error(f"Error in VaR impact check: {str(e)}")
        
        return {'metrics': metrics, 'violations': violations}
    
    async def _calculate_approved_quantity(
        self, 
        request: RiskAssessmentRequest, 
        risk_metrics: List[RiskMetric]
    ) -> int:
        """Calculate approved quantity based on risk metrics"""
        
        try:
            # Use position sizer to determine optimal quantity
            optimal_quantity = await self.position_sizer.calculate_optimal_position_size(
                symbol=request.symbol,
                price=request.price,
                account_value=100000,  # This should come from portfolio data
                volatility=0.02,  # This should be calculated from historical data
                confidence_level=0.95
            )
            
            # Return the minimum of requested and optimal quantity
            return min(request.quantity, optimal_quantity)
            
        except Exception as e:
            logger.error(f"Error calculating approved quantity: {str(e)}")
            return 0
    
    async def _get_portfolio_data(self, account_id: str) -> Dict[str, Any]:
        """Get portfolio data for account (mock implementation)"""
        
        # This would integrate with the actual portfolio service
        return {
            'account_id': account_id,
            'total_value': 100000.0,
            'cash': 20000.0,
            'total_exposure': 80000.0,
            'positions': {
                'AAPL': {'quantity': 100, 'market_value': 15000},
                'GOOGL': {'quantity': 50, 'market_value': 12000},
                'TSLA': {'quantity': 75, 'market_value': 18000}
            }
        }
    
    def _validate_risk_request(self, request: RiskAssessmentRequest) -> None:
        """Validate risk assessment request"""
        
        if not request.account_id:
            raise ValueError("Account ID is required")
        
        if not request.symbol:
            raise ValueError("Symbol is required")
        
        if request.quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        if request.price <= 0:
            raise ValueError("Price must be positive")
    
    def _generate_cache_key(self, request: RiskAssessmentRequest) -> str:
        """Generate cache key for request"""
        
        return f"{request.account_id}:{request.symbol}:{request.quantity}:{request.price}:{request.order_type}"
    
    def _get_cached_result(self, cache_key: str) -> Optional[RiskAssessmentResponse]:
        """Get cached risk assessment result"""
        
        if cache_key in self.risk_cache:
            cached_data = self.risk_cache[cache_key]
            
            # Check if cache is still valid
            if (datetime.now(timezone.utc) - cached_data['timestamp']).total_seconds() < self.cache_ttl:
                return cached_data['result']
            else:
                # Remove expired cache entry
                del self.risk_cache[cache_key]
        
        return None
    
    def _cache_result(self, cache_key: str, result: RiskAssessmentResponse) -> None:
        """Cache risk assessment result"""
        
        self.risk_cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now(timezone.utc)
        }
        
        # Clean up old cache entries periodically
        if len(self.risk_cache) > 1000:
            self._cleanup_cache()
    
    def _cleanup_cache(self) -> None:
        """Clean up expired cache entries"""
        
        current_time = datetime.now(timezone.utc)
        expired_keys = []
        
        for key, data in self.risk_cache.items():
            if (current_time - data['timestamp']).total_seconds() > self.cache_ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.risk_cache[key]
    
    async def _handle_risk_violation(self, alert_data: Dict[str, Any]) -> None:
        """Handle risk violation alert from real-time monitor"""
        
        logger.warning(f"Risk violation detected: {alert_data}")
        
        # Trigger violation callbacks
        for callback in self.risk_violation_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert_data)
                else:
                    callback(alert_data)
            except Exception as e:
                logger.error(f"Error in risk violation callback: {str(e)}")
    
    async def _trigger_assessment_callbacks(
        self, 
        request: RiskAssessmentRequest, 
        response: RiskAssessmentResponse
    ) -> None:
        """Trigger risk assessment callbacks"""
        
        callback_data = {
            'request': asdict(request),
            'response': asdict(response),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        for callback in self.risk_assessment_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(callback_data)
                else:
                    callback(callback_data)
            except Exception as e:
                logger.error(f"Error in risk assessment callback: {str(e)}")
    
    # Public API methods
    
    async def start_realtime_monitoring(self, account_ids: List[str]) -> None:
        """Start real-time risk monitoring"""
        
        if not self.realtime_monitor:
            raise ValueError("Real-time monitoring not enabled")
        
        await self.realtime_monitor.start_monitoring(account_ids)
    
    async def stop_realtime_monitoring(self) -> None:
        """Stop real-time risk monitoring"""
        
        if self.realtime_monitor:
            await self.realtime_monitor.stop_monitoring()
    
    async def get_portfolio_risk_summary(self, account_id: str) -> Optional[PortfolioRiskSummary]:
        """Get portfolio risk summary"""
        
        if self.realtime_monitor:
            return await self.realtime_monitor.get_risk_summary(account_id)
        
        return None
    
    async def force_risk_check(self, account_id: str) -> Dict[str, Any]:
        """Force immediate risk check"""
        
        if self.realtime_monitor:
            return await self.realtime_monitor.force_risk_check(account_id)
        
        return {}
    
    def add_risk_violation_callback(self, callback: Callable) -> None:
        """Add risk violation callback"""
        self.risk_violation_callbacks.append(callback)
    
    def add_risk_assessment_callback(self, callback: Callable) -> None:
        """Add risk assessment callback"""
        self.risk_assessment_callbacks.append(callback)
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Get risk engine status"""
        
        avg_processing_time = (
            self.total_processing_time / self.assessment_count 
            if self.assessment_count > 0 else 0
        )
        
        status = {
            'is_initialized': self.is_initialized,
            'realtime_monitoring_enabled': self.enable_realtime_monitoring,
            'assessment_count': self.assessment_count,
            'avg_processing_time': avg_processing_time,
            'cache_size': len(self.risk_cache),
            'risk_limits': asdict(self.risk_limits)
        }
        
        if self.realtime_monitor:
            status['realtime_monitor_status'] = self.realtime_monitor.get_monitoring_status()
        
        return status