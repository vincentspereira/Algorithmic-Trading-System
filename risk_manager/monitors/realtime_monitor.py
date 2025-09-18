"""Real-Time Risk Monitor

Continuously monitors portfolio risk metrics, detects violations,
and triggers alerts in real-time using async processing.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Callable, Any, Set
import logging
from collections import defaultdict, deque

import numpy as np
import pandas as pd
from dataclasses import asdict

from ..models.risk_models import (
    RiskLimits, RiskMetric, RiskViolation, RiskLevel, RiskMetricType,
    RiskViolationType, PortfolioRiskSummary, RiskCheckResult
)
from ..calculators.var_calculator import VaRCalculator
from ..calculators.position_sizer import PositionSizer

# Configure logging
logger = logging.getLogger(__name__)

class RealTimeRiskMonitor:
    """Real-time risk monitoring system"""
    
    def __init__(self, 
                 risk_limits: Optional[RiskLimits] = None,
                 update_interval: float = 1.0,
                 alert_callbacks: Optional[List[Callable]] = None):
        """
        Initialize real-time risk monitor
        
        Args:
            risk_limits: Risk limits configuration
            update_interval: Update interval in seconds
            alert_callbacks: List of callback functions for alerts
        """
        self.risk_limits = risk_limits or RiskLimits()
        self.update_interval = update_interval
        self.alert_callbacks = alert_callbacks or []
        
        # Risk monitoring state
        self.is_monitoring = False
        self.monitored_accounts: Set[str] = set()
        self.current_metrics: Dict[str, List[RiskMetric]] = defaultdict(list)
        self.active_violations: Dict[str, List[RiskViolation]] = defaultdict(list)
        self.risk_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Performance tracking
        self.last_update_time: Optional[datetime] = None
        self.update_count = 0
        self.processing_times: deque = deque(maxlen=100)
        
        # Calculators
        self.var_calculator = VaRCalculator()
        self.position_sizer = PositionSizer(self.risk_limits)
        
        # Event loop and tasks
        self._monitor_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def start_monitoring(self, account_ids: List[str]) -> None:
        """Start real-time risk monitoring for specified accounts"""
        
        if self.is_monitoring:
            logger.warning("Risk monitoring already active")
            return
        
        self.monitored_accounts.update(account_ids)
        self.is_monitoring = True
        
        # Start monitoring tasks
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info(f"Started risk monitoring for accounts: {account_ids}")
    
    async def stop_monitoring(self) -> None:
        """Stop real-time risk monitoring"""
        
        self.is_monitoring = False
        
        # Cancel tasks
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped risk monitoring")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        
        while self.is_monitoring:
            try:
                start_time = datetime.now(timezone.utc)
                
                # Update risk metrics for all monitored accounts
                for account_id in self.monitored_accounts:
                    await self._update_account_risk_metrics(account_id)
                
                # Record processing time
                processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                self.processing_times.append(processing_time)
                
                self.last_update_time = datetime.now(timezone.utc)
                self.update_count += 1
                
                # Log performance periodically
                if self.update_count % 100 == 0:
                    avg_processing_time = np.mean(self.processing_times)
                    logger.info(f"Risk monitoring: {self.update_count} updates, "
                              f"avg processing time: {avg_processing_time:.3f}s")
                
                # Wait for next update
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(self.update_interval)
    
    async def _cleanup_loop(self) -> None:
        """Cleanup loop for resolved violations and old data"""
        
        while self.is_monitoring:
            try:
                # Clean up resolved violations (older than 1 hour)
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
                
                for account_id in list(self.active_violations.keys()):
                    self.active_violations[account_id] = [
                        v for v in self.active_violations[account_id]
                        if not v.resolved or v.resolution_timestamp > cutoff_time
                    ]
                    
                    # Remove empty lists
                    if not self.active_violations[account_id]:
                        del self.active_violations[account_id]
                
                # Sleep for 5 minutes before next cleanup
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {str(e)}")
                await asyncio.sleep(300)
    
    async def _update_account_risk_metrics(self, account_id: str) -> None:
        """Update risk metrics for a specific account"""
        
        try:
            # Get current portfolio data (this would come from portfolio service)
            portfolio_data = await self._get_portfolio_data(account_id)
            
            if not portfolio_data:
                return
            
            # Calculate risk metrics
            metrics = await self._calculate_risk_metrics(account_id, portfolio_data)
            
            # Update current metrics
            self.current_metrics[account_id] = metrics
            
            # Add to history
            self.risk_history[account_id].append({
                'timestamp': datetime.now(timezone.utc),
                'metrics': [asdict(m) for m in metrics]
            })
            
            # Check for violations
            violations = self._check_risk_violations(account_id, metrics)
            
            # Update active violations
            if violations:
                self.active_violations[account_id].extend(violations)
                
                # Trigger alerts
                for violation in violations:
                    await self._trigger_alert(account_id, violation)
            
        except Exception as e:
            logger.error(f"Error updating risk metrics for {account_id}: {str(e)}")
    
    async def _get_portfolio_data(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get current portfolio data (mock implementation)"""
        
        # This would integrate with the actual portfolio service
        # For now, return mock data
        return {
            'account_id': account_id,
            'total_value': 100000.0,
            'cash': 20000.0,
            'positions': {
                'AAPL': {'quantity': 100, 'market_value': 15000, 'unrealized_pnl': 500},
                'GOOGL': {'quantity': 50, 'market_value': 12000, 'unrealized_pnl': -200},
                'TSLA': {'quantity': 75, 'market_value': 18000, 'unrealized_pnl': 1000}
            },
            'daily_pnl': 300,
            'total_pnl': 2500
        }
    
    async def _calculate_risk_metrics(
        self, 
        account_id: str, 
        portfolio_data: Dict[str, Any]
    ) -> List[RiskMetric]:
        """Calculate comprehensive risk metrics"""
        
        metrics = []
        timestamp = datetime.now(timezone.utc)
        
        try:
            total_value = portfolio_data['total_value']
            positions = portfolio_data['positions']
            
            # Portfolio exposure metrics
            total_exposure = sum(pos['market_value'] for pos in positions.values())
            exposure_metric = RiskMetric(
                metric_type=RiskMetricType.PORTFOLIO_EXPOSURE,
                current_value=total_exposure,
                limit_value=self.risk_limits.max_portfolio_exposure,
                utilization_percent=0,  # Will be calculated in __post_init__
                risk_level=RiskLevel.LOW,  # Will be determined in __post_init__
                timestamp=timestamp,
                account_id=account_id
            )
            metrics.append(exposure_metric)
            
            # Position concentration metrics
            if total_exposure > 0:
                max_position_value = max(pos['market_value'] for pos in positions.values())
                concentration_percent = (max_position_value / total_value) * 100
                
                concentration_metric = RiskMetric(
                    metric_type=RiskMetricType.CONCENTRATION,
                    current_value=concentration_percent,
                    limit_value=self.risk_limits.max_concentration_percent,
                    utilization_percent=0,
                    risk_level=RiskLevel.LOW,
                    timestamp=timestamp,
                    account_id=account_id
                )
                metrics.append(concentration_metric)
            
            # Leverage metric
            cash = portfolio_data.get('cash', 0)
            if cash > 0:
                leverage = total_exposure / (total_value - cash + total_exposure)
                leverage_metric = RiskMetric(
                    metric_type=RiskMetricType.LEVERAGE,
                    current_value=leverage,
                    limit_value=self.risk_limits.max_leverage,
                    utilization_percent=0,
                    risk_level=RiskLevel.LOW,
                    timestamp=timestamp,
                    account_id=account_id
                )
                metrics.append(leverage_metric)
            
            # Daily P&L metric
            daily_pnl = portfolio_data.get('daily_pnl', 0)
            daily_loss_limit = self.risk_limits.max_daily_loss
            
            if daily_pnl < 0:  # Only track losses
                pnl_metric = RiskMetric(
                    metric_type=RiskMetricType.DRAWDOWN,
                    current_value=abs(daily_pnl),
                    limit_value=daily_loss_limit,
                    utilization_percent=0,
                    risk_level=RiskLevel.LOW,
                    timestamp=timestamp,
                    account_id=account_id
                )
                metrics.append(pnl_metric)
            
            # Calculate VaR if we have sufficient data
            var_result = await self._calculate_portfolio_var(account_id, positions)
            if var_result:
                var_limit = total_value * (self.risk_limits.max_var_percentage / 100)
                var_metric = RiskMetric(
                    metric_type=RiskMetricType.VAR,
                    current_value=var_result.var_amount * total_value,
                    limit_value=var_limit,
                    utilization_percent=0,
                    risk_level=RiskLevel.LOW,
                    timestamp=timestamp,
                    account_id=account_id,
                    metadata={'var_method': var_result.method, 'confidence_level': var_result.confidence_level}
                )
                metrics.append(var_metric)
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {str(e)}")
        
        return metrics
    
    async def _calculate_portfolio_var(
        self, 
        account_id: str, 
        positions: Dict[str, Dict]
    ) -> Optional[Any]:
        """Calculate portfolio VaR (simplified implementation)"""
        
        try:
            # This would use historical price data to calculate VaR
            # For now, return a mock result
            from ..models.risk_models import VaRResult, VaRMethod
            
            return VaRResult(
                method=VaRMethod.PARAMETRIC,
                confidence_level=0.95,
                time_horizon=1,
                var_amount=0.02,  # 2% of portfolio
                var_percentage=2.0
            )
            
        except Exception as e:
            logger.error(f"Error calculating portfolio VaR: {str(e)}")
            return None
    
    def _check_risk_violations(
        self, 
        account_id: str, 
        metrics: List[RiskMetric]
    ) -> List[RiskViolation]:
        """Check for risk limit violations"""
        
        violations = []
        
        for metric in metrics:
            if metric.utilization_percent > 100:  # Violation threshold
                
                # Determine violation type
                violation_type_map = {
                    RiskMetricType.PORTFOLIO_EXPOSURE: RiskViolationType.EXPOSURE_LIMIT,
                    RiskMetricType.CONCENTRATION: RiskViolationType.CONCENTRATION_LIMIT,
                    RiskMetricType.LEVERAGE: RiskViolationType.LEVERAGE_LIMIT,
                    RiskMetricType.DRAWDOWN: RiskViolationType.LOSS_LIMIT,
                    RiskMetricType.VAR: RiskViolationType.VAR_LIMIT
                }
                
                violation_type = violation_type_map.get(
                    metric.metric_type, 
                    RiskViolationType.PORTFOLIO_LIMIT
                )
                
                violation = RiskViolation(
                    violation_type=violation_type,
                    severity=metric.risk_level,
                    current_value=metric.current_value,
                    limit_value=metric.limit_value,
                    excess_amount=0,  # Will be calculated in __post_init__
                    account_id=account_id,
                    metadata=metric.metadata
                )
                
                violations.append(violation)
        
        return violations
    
    async def _trigger_alert(
        self, 
        account_id: str, 
        violation: RiskViolation
    ) -> None:
        """Trigger alert for risk violation"""
        
        alert_data = {
            'account_id': account_id,
            'violation_type': violation.violation_type,
            'severity': violation.severity,
            'message': violation.message,
            'timestamp': violation.timestamp.isoformat(),
            'current_value': violation.current_value,
            'limit_value': violation.limit_value,
            'excess_amount': violation.excess_amount
        }
        
        # Call all registered alert callbacks
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert_data)
                else:
                    callback(alert_data)
            except Exception as e:
                logger.error(f"Error in alert callback: {str(e)}")
        
        # Log the alert
        logger.warning(f"Risk violation alert: {violation.message}")
    
    def add_alert_callback(self, callback: Callable) -> None:
        """Add alert callback function"""
        self.alert_callbacks.append(callback)
    
    def remove_alert_callback(self, callback: Callable) -> None:
        """Remove alert callback function"""
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)
    
    async def get_risk_summary(self, account_id: str) -> Optional[PortfolioRiskSummary]:
        """Get current risk summary for account"""
        
        if account_id not in self.monitored_accounts:
            return None
        
        try:
            # Get current portfolio data
            portfolio_data = await self._get_portfolio_data(account_id)
            if not portfolio_data:
                return None
            
            # Get current metrics
            metrics = self.current_metrics.get(account_id, [])
            violations = self.active_violations.get(account_id, [])
            
            # Calculate overall risk level
            if violations:
                max_severity = max(v.severity for v in violations)
                overall_risk_level = max_severity
            else:
                risk_levels = [m.risk_level for m in metrics]
                overall_risk_level = max(risk_levels) if risk_levels else RiskLevel.LOW
            
            # Calculate risk score
            from ..models.risk_models import calculate_risk_score
            risk_score = calculate_risk_score(metrics)
            
            # Extract values from portfolio data
            total_value = portfolio_data['total_value']
            positions = portfolio_data['positions']
            total_exposure = sum(pos['market_value'] for pos in positions.values())
            
            return PortfolioRiskSummary(
                account_id=account_id,
                total_exposure=total_exposure,
                gross_exposure=total_exposure,
                net_exposure=total_exposure,  # Simplified
                long_exposure=total_exposure,
                short_exposure=0.0,
                available_buying_power=portfolio_data.get('cash', 0),
                current_leverage=total_exposure / total_value if total_value > 0 else 0,
                max_position_concentration=max(
                    (pos['market_value'] / total_value) * 100 
                    for pos in positions.values()
                ) if positions else 0,
                daily_pnl=portfolio_data.get('daily_pnl', 0),
                total_pnl=portfolio_data.get('total_pnl', 0),
                unrealized_pnl=sum(pos.get('unrealized_pnl', 0) for pos in positions.values()),
                realized_pnl=0.0,  # Would need to be calculated
                current_drawdown=0.0,  # Would need historical data
                max_drawdown=0.0,  # Would need historical data
                portfolio_volatility=0.0,  # Would need historical data
                portfolio_beta=1.0,  # Would need market data
                overall_risk_level=overall_risk_level,
                risk_score=risk_score,
                active_violations=[asdict(v) for v in violations],
                risk_metrics=[asdict(m) for m in metrics]
            )
            
        except Exception as e:
            logger.error(f"Error generating risk summary for {account_id}: {str(e)}")
            return None
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status"""
        
        avg_processing_time = (
            np.mean(self.processing_times) if self.processing_times else 0
        )
        
        return {
            'is_monitoring': self.is_monitoring,
            'monitored_accounts': list(self.monitored_accounts),
            'update_interval': self.update_interval,
            'last_update_time': self.last_update_time.isoformat() if self.last_update_time else None,
            'update_count': self.update_count,
            'avg_processing_time': avg_processing_time,
            'active_violations_count': sum(len(v) for v in self.active_violations.values()),
            'total_metrics_tracked': sum(len(m) for m in self.current_metrics.values())
        }
    
    async def force_risk_check(self, account_id: str) -> Dict[str, Any]:
        """Force immediate risk check for account"""
        
        if account_id not in self.monitored_accounts:
            self.monitored_accounts.add(account_id)
        
        await self._update_account_risk_metrics(account_id)
        
        return {
            'account_id': account_id,
            'check_time': datetime.now(timezone.utc).isoformat(),
            'metrics_count': len(self.current_metrics.get(account_id, [])),
            'violations_count': len(self.active_violations.get(account_id, [])),
            'risk_summary': await self.get_risk_summary(account_id)
        }