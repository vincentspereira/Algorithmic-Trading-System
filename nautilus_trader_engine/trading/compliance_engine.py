"""
Real-Time Compliance Engine
Pre-trade compliance checking, position limit monitoring, and regulatory rule engine
"""

import asyncio
import time
import logging
import json
from typing import Dict, List, Optional, Tuple, Any, Callable, Union, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import threading
from concurrent.futures import ThreadPoolExecutor
import uuid

# Import core components
from ..core.messaging.message_bus import MessageBus
from ..core.caching.cache_manager import CacheManager


class ComplianceResult(Enum):
    """Compliance check results"""
    APPROVED = "approved"
    REJECTED = "rejected"
    WARNING = "warning"
    PENDING = "pending"


class RuleType(Enum):
    """Types of compliance rules"""
    POSITION_LIMIT = "position_limit"
    CONCENTRATION_LIMIT = "concentration_limit"
    RISK_LIMIT = "risk_limit"
    TRADING_LIMIT = "trading_limit"
    REGULATORY = "regulatory"
    CUSTOM = "custom"


class RuleSeverity(Enum):
    """Rule violation severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ComplianceAction(Enum):
    """Actions to take on compliance violations"""
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    REDUCE_SIZE = "reduce_size"
    ESCALATE = "escalate"


@dataclass
class ComplianceRule:
    """Compliance rule definition"""
    rule_id: str
    rule_name: str
    rule_type: RuleType
    severity: RuleSeverity
    action: ComplianceAction
    
    # Rule parameters
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Scope
    applies_to_accounts: Set[str] = field(default_factory=set)
    applies_to_symbols: Set[str] = field(default_factory=set)
    applies_to_strategies: Set[str] = field(default_factory=set)
    
    # Status
    is_active: bool = True
    created_time: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
    
    # Rule logic (callable or expression)
    rule_logic: Optional[Callable] = None
    rule_expression: Optional[str] = None
    
    # Metadata
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceCheck:
    """Individual compliance check"""
    check_id: str
    order_id: str
    rule_id: str
    result: ComplianceResult
    
    # Check details
    symbol: str
    side: str
    quantity: float
    price: Optional[float] = None
    account_id: str = ""
    strategy_id: str = ""
    
    # Results
    violation_message: str = ""
    suggested_action: Optional[ComplianceAction] = None
    max_allowed_quantity: Optional[float] = None
    
    # Timing
    check_time: datetime = field(default_factory=datetime.now)
    processing_time_ms: float = 0.0
    
    # Context
    rule_parameters: Dict[str, Any] = field(default_factory=dict)
    market_data: Dict[str, Any] = field(default_factory=dict)
    position_data: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Position:
    """Position information for compliance checking"""
    account_id: str
    symbol: str
    quantity: float
    avg_price: float
    market_value: float
    unrealized_pnl: float
    
    # Risk metrics
    var_1d: float = 0.0
    var_10d: float = 0.0
    beta: float = 0.0
    
    # Timestamps
    last_updated: datetime = field(default_factory=datetime.now)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceViolation:
    """Compliance violation record"""
    violation_id: str
    rule_id: str
    order_id: str
    
    # Violation details
    violation_type: RuleType
    severity: RuleSeverity
    message: str
    
    # Context
    account_id: str
    symbol: str
    quantity: float
    
    # Resolution
    action_taken: ComplianceAction
    resolved: bool = False
    resolution_notes: str = ""
    
    # Timing
    violation_time: datetime = field(default_factory=datetime.now)
    resolution_time: Optional[datetime] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


class ComplianceEngine:
    """
    Real-Time Compliance Engine
    
    Features:
    - Pre-trade compliance checking
    - Real-time position limit monitoring
    - Configurable regulatory rule engine
    - Risk limit enforcement
    - Compliance reporting and audit trails
    - Real-time violation alerts
    - Automated remediation actions
    """
    
    def __init__(self,
                 message_bus: Optional[MessageBus] = None,
                 cache_manager: Optional[CacheManager] = None,
                 max_concurrent_checks: int = 100,
                 enable_real_time_monitoring: bool = True):
        
        self.message_bus = message_bus
        self.cache_manager = cache_manager
        self.max_concurrent_checks = max_concurrent_checks
        self.enable_real_time_monitoring = enable_real_time_monitoring
        
        # Rule management
        self._rules: Dict[str, ComplianceRule] = {}
        self._rule_cache: Dict[str, Any] = {}
        
        # Position tracking
        self._positions: Dict[Tuple[str, str], Position] = {}  # (account_id, symbol) -> Position
        self._position_limits: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        # Compliance checking
        self._check_queue = asyncio.Queue(maxsize=1000)
        self._check_tasks: List[asyncio.Task] = []
        self._running = False
        
        # Thread pool for intensive compliance calculations
        self._thread_pool = ThreadPoolExecutor(
            max_workers=max_concurrent_checks,
            thread_name_prefix="compliance-check"
        )
        
        # Violation tracking
        self._violations: Dict[str, ComplianceViolation] = {}
        self._violation_history: List[ComplianceViolation] = []
        
        # Performance metrics
        self._metrics = {
            'total_checks': 0,
            'approved_checks': 0,
            'rejected_checks': 0,
            'warning_checks': 0,
            'avg_check_time_ms': 0.0,
            'violations_detected': 0,
            'violations_resolved': 0,
            'rules_active': 0
        }
        
        # Built-in rule implementations
        self._rule_implementations = {
            RuleType.POSITION_LIMIT: self._check_position_limit,
            RuleType.CONCENTRATION_LIMIT: self._check_concentration_limit,
            RuleType.RISK_LIMIT: self._check_risk_limit,
            RuleType.TRADING_LIMIT: self._check_trading_limit,
            RuleType.REGULATORY: self._check_regulatory,
            RuleType.CUSTOM: self._check_custom_rule
        }
        
        # Market data cache
        self._market_data: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # Audit trail
        self._audit_trail: deque = deque(maxlen=10000)
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start the compliance engine"""
        if self._running:
            return
        
        self._running = True
        
        # Start compliance check workers
        for i in range(min(10, self.max_concurrent_checks)):
            task = asyncio.create_task(self._compliance_worker(f"compliance-{i}"))
            self._check_tasks.append(task)
        
        # Start real-time monitoring
        if self.enable_real_time_monitoring:
            asyncio.create_task(self._position_monitor())
            asyncio.create_task(self._violation_monitor())
        
        # Start metrics tracking
        asyncio.create_task(self._metrics_tracker())
        
        # Load default rules
        await self._load_default_rules()
        
        self.logger.info("Compliance Engine started")
    
    async def stop(self):
        """Stop the compliance engine"""
        self._running = False
        
        # Cancel check tasks
        for task in self._check_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._check_tasks:
            await asyncio.gather(*self._check_tasks, return_exceptions=True)
        
        # Shutdown thread pool
        self._thread_pool.shutdown(wait=True)
        
        self.logger.info("Compliance Engine stopped")
    
    async def check_pre_trade_compliance(self,
                                       order_id: str,
                                       symbol: str,
                                       side: str,
                                       quantity: float,
                                       price: Optional[float] = None,
                                       account_id: str = "",
                                       strategy_id: str = "") -> List[ComplianceCheck]:
        """Perform pre-trade compliance check"""
        try:
            start_time = time.time_ns()
            
            # Create compliance check request
            check_request = {
                'order_id': order_id,
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': price,
                'account_id': account_id,
                'strategy_id': strategy_id,
                'timestamp': start_time
            }
            
            # Add to check queue
            future = asyncio.Future()
            check_request['future'] = future
            
            await self._check_queue.put(check_request)
            
            # Wait for results
            compliance_checks = await future
            
            # Update metrics
            processing_time = (time.time_ns() - start_time) / 1_000_000
            self._metrics['total_checks'] += 1
            
            # Update average processing time
            current_avg = self._metrics['avg_check_time_ms']
            total_checks = self._metrics['total_checks']
            self._metrics['avg_check_time_ms'] = (
                (current_avg * (total_checks - 1) + processing_time) / total_checks
            )
            
            # Count results
            for check in compliance_checks:
                if check.result == ComplianceResult.APPROVED:
                    self._metrics['approved_checks'] += 1
                elif check.result == ComplianceResult.REJECTED:
                    self._metrics['rejected_checks'] += 1
                elif check.result == ComplianceResult.WARNING:
                    self._metrics['warning_checks'] += 1
            
            return compliance_checks
            
        except Exception as e:
            self.logger.error(f"Pre-trade compliance check failed: {e}")
            # Return rejection on error
            return [ComplianceCheck(
                check_id=str(uuid.uuid4()),
                order_id=order_id,
                rule_id="system_error",
                result=ComplianceResult.REJECTED,
                symbol=symbol,
                side=side,
                quantity=quantity,
                violation_message=f"Compliance check failed: {e}"
            )]
    
    async def _compliance_worker(self, worker_name: str):
        """Background worker for compliance checks"""
        self.logger.debug(f"Compliance worker {worker_name} started")
        
        while self._running:
            try:
                # Get check request from queue
                try:
                    request = await asyncio.wait_for(
                        self._check_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process compliance check
                checks = await self._process_compliance_check(request, worker_name)
                
                # Set result
                request['future'].set_result(checks)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Compliance worker {worker_name} error: {e}")
                if 'future' in locals() and not request['future'].done():
                    request['future'].set_exception(e)
                await asyncio.sleep(1)
        
        self.logger.debug(f"Compliance worker {worker_name} stopped")
    
    async def _process_compliance_check(self, request: Dict[str, Any], worker_name: str) -> List[ComplianceCheck]:
        """Process a compliance check request"""
        order_id = request['order_id']
        symbol = request['symbol']
        side = request['side']
        quantity = request['quantity']
        price = request.get('price')
        account_id = request.get('account_id', '')
        strategy_id = request.get('strategy_id', '')
        
        compliance_checks = []
        
        try:
            # Get applicable rules
            applicable_rules = self._get_applicable_rules(
                account_id, symbol, strategy_id
            )
            
            # Get current position and market data
            position = self._get_position(account_id, symbol)
            market_data = await self._get_market_data(symbol)
            
            # Run compliance checks for each applicable rule
            for rule in applicable_rules:
                check_start_time = time.time_ns()
                
                try:
                    # Get rule implementation
                    rule_impl = self._rule_implementations.get(rule.rule_type)
                    if not rule_impl:
                        continue
                    
                    # Execute rule check
                    check_result = await rule_impl(
                        rule, order_id, symbol, side, quantity, price,
                        account_id, strategy_id, position, market_data
                    )
                    
                    # Set processing time
                    check_result.processing_time_ms = (time.time_ns() - check_start_time) / 1_000_000
                    
                    compliance_checks.append(check_result)
                    
                    # Handle violations
                    if check_result.result == ComplianceResult.REJECTED:
                        await self._handle_violation(check_result, rule)
                    
                except Exception as e:
                    self.logger.error(f"Rule {rule.rule_id} check failed: {e}")
                    # Create error check result
                    error_check = ComplianceCheck(
                        check_id=str(uuid.uuid4()),
                        order_id=order_id,
                        rule_id=rule.rule_id,
                        result=ComplianceResult.REJECTED,
                        symbol=symbol,
                        side=side,
                        quantity=quantity,
                        account_id=account_id,
                        strategy_id=strategy_id,
                        violation_message=f"Rule check error: {e}",
                        processing_time_ms=(time.time_ns() - check_start_time) / 1_000_000
                    )
                    compliance_checks.append(error_check)
            
            # Add to audit trail
            self._add_to_audit_trail({
                'type': 'compliance_check',
                'order_id': order_id,
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'account_id': account_id,
                'checks_performed': len(compliance_checks),
                'results': [c.result.value for c in compliance_checks],
                'timestamp': datetime.now()
            })
            
            return compliance_checks
            
        except Exception as e:
            self.logger.error(f"Compliance check processing failed: {e}")
            return [ComplianceCheck(
                check_id=str(uuid.uuid4()),
                order_id=order_id,
                rule_id="processing_error",
                result=ComplianceResult.REJECTED,
                symbol=symbol,
                side=side,
                quantity=quantity,
                violation_message=f"Processing error: {e}"
            )]
    
    def _get_applicable_rules(self, 
                            account_id: str, 
                            symbol: str, 
                            strategy_id: str) -> List[ComplianceRule]:
        """Get rules applicable to the order"""
        applicable_rules = []
        
        for rule in self._rules.values():
            if not rule.is_active:
                continue
            
            # Check account scope
            if rule.applies_to_accounts and account_id not in rule.applies_to_accounts:
                continue
            
            # Check symbol scope
            if rule.applies_to_symbols and symbol not in rule.applies_to_symbols:
                continue
            
            # Check strategy scope
            if rule.applies_to_strategies and strategy_id not in rule.applies_to_strategies:
                continue
            
            applicable_rules.append(rule)
        
        return applicable_rules
    
    def _get_position(self, account_id: str, symbol: str) -> Optional[Position]:
        """Get current position for account and symbol"""
        return self._positions.get((account_id, symbol))
    
    async def _get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get current market data"""
        try:
            # Check cache first
            if self.cache_manager:
                cached_data = await self.cache_manager.get(f"market_data:{symbol}")
                if cached_data:
                    return cached_data
            
            # Get from internal store
            market_data = self._market_data.get(symbol, {
                'price': 100.0,
                'bid': 99.95,
                'ask': 100.05,
                'volume': 50000.0,
                'volatility': 0.02,
                'beta': 1.0
            })
            
            # Cache the data
            if self.cache_manager:
                await self.cache_manager.set(f"market_data:{symbol}", market_data, ttl=1)
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"Failed to get market data for {symbol}: {e}")
            return {}
    
    # Rule Implementation Methods
    
    async def _check_position_limit(self,
                                  rule: ComplianceRule,
                                  order_id: str,
                                  symbol: str,
                                  side: str,
                                  quantity: float,
                                  price: Optional[float],
                                  account_id: str,
                                  strategy_id: str,
                                  position: Optional[Position],
                                  market_data: Dict[str, Any]) -> ComplianceCheck:
        """Check position limit compliance"""
        try:
            # Get rule parameters
            max_position = rule.parameters.get('max_position', float('inf'))
            max_long_position = rule.parameters.get('max_long_position', max_position)
            max_short_position = rule.parameters.get('max_short_position', max_position)
            
            # Calculate new position after order
            current_position = position.quantity if position else 0.0
            
            if side.lower() == 'buy':
                new_position = current_position + quantity
                limit = max_long_position
            else:
                new_position = current_position - quantity
                limit = -max_short_position
            
            # Check limit
            if side.lower() == 'buy' and new_position > limit:
                max_allowed = max(0, limit - current_position)
                return ComplianceCheck(
                    check_id=str(uuid.uuid4()),
                    order_id=order_id,
                    rule_id=rule.rule_id,
                    result=ComplianceResult.REJECTED if max_allowed <= 0 else ComplianceResult.WARNING,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    account_id=account_id,
                    strategy_id=strategy_id,
                    violation_message=f"Position limit exceeded. Current: {current_position}, Limit: {limit}, Requested: {quantity}",
                    suggested_action=ComplianceAction.REDUCE_SIZE if max_allowed > 0 else ComplianceAction.BLOCK,
                    max_allowed_quantity=max_allowed if max_allowed > 0 else None,
                    rule_parameters=rule.parameters,
                    position_data={'current_position': current_position, 'new_position': new_position}
                )
            elif side.lower() == 'sell' and new_position < limit:
                max_allowed = max(0, current_position - abs(limit))
                return ComplianceCheck(
                    check_id=str(uuid.uuid4()),
                    order_id=order_id,
                    rule_id=rule.rule_id,
                    result=ComplianceResult.REJECTED if max_allowed <= 0 else ComplianceResult.WARNING,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    account_id=account_id,
                    strategy_id=strategy_id,
                    violation_message=f"Short position limit exceeded. Current: {current_position}, Limit: {limit}, Requested: {quantity}",
                    suggested_action=ComplianceAction.REDUCE_SIZE if max_allowed > 0 else ComplianceAction.BLOCK,
                    max_allowed_quantity=max_allowed if max_allowed > 0 else None,
                    rule_parameters=rule.parameters,
                    position_data={'current_position': current_position, 'new_position': new_position}
                )
            
            # Position limit OK
            return ComplianceCheck(
                check_id=str(uuid.uuid4()),
                order_id=order_id,
                rule_id=rule.rule_id,
                result=ComplianceResult.APPROVED,
                symbol=symbol,
                side=side,
                quantity=quantity,
                account_id=account_id,
                strategy_id=strategy_id,
                rule_parameters=rule.parameters,
                position_data={'current_position': current_position, 'new_position': new_position}
            )
            
        except Exception as e:
            self.logger.error(f"Position limit check failed: {e}")
            return ComplianceCheck(
                check_id=str(uuid.uuid4()),
                order_id=order_id,
                rule_id=rule.rule_id,
                result=ComplianceResult.REJECTED,
                symbol=symbol,
                side=side,
                quantity=quantity,
                account_id=account_id,
                strategy_id=strategy_id,
                violation_message=f"Position limit check error: {e}"
            )
    
    async def _check_concentration_limit(self,
                                       rule: ComplianceRule,
                                       order_id: str,
                                       symbol: str,
                                       side: str,
                                       quantity: float,
                                       price: Optional[float],
                                       account_id: str,
                                       strategy_id: str,
                                       position: Optional[Position],
                                       market_data: Dict[str, Any]) -> ComplianceCheck:
        """Check concentration limit compliance"""
        try:
            # Get rule parameters
            max_concentration_pct = rule.parameters.get('max_concentration_percent', 10.0)  # 10% default
            portfolio_value = rule.parameters.get('portfolio_value', 1000000.0)  # $1M default
            
            # Calculate current position value
            current_price = market_data.get('price', price or 100.0)
            current_position_value = (position.quantity * current_price) if position else 0.0
            
            # Calculate new position value after order
            if side.lower() == 'buy':
                new_position_value = current_position_value + (quantity * current_price)
            else:
                new_position_value = current_position_value - (quantity * current_price)
            
            # Calculate concentration percentage
            concentration_pct = abs(new_position_value) / portfolio_value * 100
            
            if concentration_pct > max_concentration_pct:
                # Calculate max allowed quantity
                max_allowed_value = portfolio_value * (max_concentration_pct / 100)
                max_allowed_quantity = max(0, (max_allowed_value - abs(current_position_value)) / current_price)
                
                return ComplianceCheck(
                    check_id=str(uuid.uuid4()),
                    order_id=order_id,
                    rule_id=rule.rule_id,
                    result=ComplianceResult.REJECTED if max_allowed_quantity <= 0 else ComplianceResult.WARNING,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    account_id=account_id,
                    strategy_id=strategy_id,
                    violation_message=f"Concentration limit exceeded. Current: {concentration_pct:.2f}%, Limit: {max_concentration_pct}%",
                    suggested_action=ComplianceAction.REDUCE_SIZE if max_allowed_quantity > 0 else ComplianceAction.BLOCK,
                    max_allowed_quantity=max_allowed_quantity if max_allowed_quantity > 0 else None,
                    rule_parameters=rule.parameters,
                    position_data={
                        'current_concentration_pct': concentration_pct,
                        'max_concentration_pct': max_concentration_pct,
                        'portfolio_value': portfolio_value
                    }
                )
            
            # Concentration limit OK
            return ComplianceCheck(
                check_id=str(uuid.uuid4()),
                order_id=order_id,
                rule_id=rule.rule_id,
                result=ComplianceResult.APPROVED,
                symbol=symbol,
                side=side,
                quantity=quantity,
                account_id=account_id,
                strategy_id=strategy_id,
                rule_parameters=rule.parameters,
                position_data={'concentration_pct': concentration_pct}
            )
            
        except Exception as e:
            self.logger.error(f"Concentration limit check failed: {e}")
            return ComplianceCheck(
                check_id=str(uuid.uuid4()),
                order_id=order_id,
                rule_id=rule.rule_id,
                result=ComplianceResult.REJECTED,
                symbol=symbol,
                side=side,
                quantity=quantity,
                account_id=account_id,
                strategy_id=strategy_id,
                violation_message=f"Concentration limit check error: {e}"
            )
    
    async def _check_risk_limit(self,
                              rule: ComplianceRule,
                              order_id: str,
                              symbol: str,
                              side: str,
                              quantity: float,
                              price: Optional[float],
                              account_id: str,
                              strategy_id: str,
                              position: Optional[Position],
                              market_data: Dict[str, Any]) -> ComplianceCheck:
        """Check risk limit compliance"""
        try:
            # Get rule parameters
            max_var_1d = rule.parameters.get('max_var_1d', 50000.0)  # $50k default
            max_var_10d = rule.parameters.get('max_var_10d', 100000.0)  # $100k default
            max_beta_exposure = rule.parameters.get('max_beta_exposure', 1000000.0)  # $1M default
            
            # Calculate current risk metrics
            current_price = market_data.get('price', price or 100.0)
            volatility = market_data.get('volatility', 0.02)
            beta = market_data.get('beta', 1.0)
            
            # Calculate new position after order
            current_position = position.quantity if position else 0.0
            if side.lower() == 'buy':
                new_position = current_position + quantity
            else:
                new_position = current_position - quantity
            
            # Calculate new position value and risk
            new_position_value = abs(new_position * current_price)
            
            # Simplified VaR calculation (1.65 * volatility * position_value for 95% confidence)
            new_var_1d = 1.65 * volatility * new_position_value
            new_var_10d = new_var_1d * np.sqrt(10)  # Scale to 10 days
            
            # Beta exposure
            new_beta_exposure = abs(new_position_value * beta)
            
            # Check limits
            violations = []
            
            if new_var_1d > max_var_1d:
                violations.append(f"1-day VaR limit exceeded: ${new_var_1d:,.0f} > ${max_var_1d:,.0f}")
            
            if new_var_10d > max_var_10d:
                violations.append(f"10-day VaR limit exceeded: ${new_var_10d:,.0f} > ${max_var_10d:,.0f}")
            
            if new_beta_exposure > max_beta_exposure:
                violations.append(f"Beta exposure limit exceeded: ${new_beta_exposure:,.0f} > ${max_beta_exposure:,.0f}")
            
            if violations:
                # Calculate max allowed quantity based on most restrictive limit
                max_allowed_by_var_1d = (max_var_1d / (1.65 * volatility)) / current_price if volatility > 0 else float('inf')
                max_allowed_by_beta = (max_beta_exposure / beta) / current_price if beta > 0 else float('inf')
                
                max_allowed_quantity = min(max_allowed_by_var_1d, max_allowed_by_beta)
                max_allowed_quantity = max(0, max_allowed_quantity - abs(current_position))
                
                return ComplianceCheck(
                    check_id=str(uuid.uuid4()),
                    order_id=order_id,
                    rule_id=rule.rule_id,
                    result=ComplianceResult.REJECTED if max_allowed_quantity <= 0 else ComplianceResult.WARNING,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    account_id=account_id,
                    strategy_id=strategy_id,
                    violation_message="; ".join(violations),
                    suggested_action=ComplianceAction.REDUCE_SIZE if max_allowed_quantity > 0 else ComplianceAction.BLOCK,
                    max_allowed_quantity=max_allowed_quantity if max_allowed_quantity > 0 else None,
                    rule_parameters=rule.parameters,
                    position_data={
                        'new_var_1d': new_var_1d,
                        'new_var_10d': new_var_10d,
                        'new_beta_exposure': new_beta_exposure
                    }
                )
            
            # Risk limits OK
            return ComplianceCheck(
                check_id=str(uuid.uuid4()),
                order_id=order_id,
                rule_id=rule.rule_id,
                result=ComplianceResult.APPROVED,
                symbol=symbol,
                side=side,
                quantity=quantity,
                account_id=account_id,
                strategy_id=strategy_id,
                rule_parameters=rule.parameters,
                position_data={
                    'var_1d': new_var_1d,
                    'var_10d': new_var_10d,
                    'beta_exposure': new_beta_exposure
                }
            )
            
        except Exception as e:
            self.logger.error(f"Risk limit check failed: {e}")
            return ComplianceCheck(
                check_id=str(uuid.uuid4()),
                order_id=order_id,
                rule_id=rule.rule_id,
                result=ComplianceResult.REJECTED,
                symbol=symbol,
                side=side,
                quantity=quantity,
                account_id=account_id,
                strategy_id=strategy_id,
                violation_message=f"Risk limit check error: {e}"
            )
    
    async def _check_trading_limit(self,
                                 rule: ComplianceRule,
                                 order_id: str,
                                 symbol: str,
                                 side: str,
                                 quantity: float,
                                 price: Optional[float],
                                 account_id: str,
                                 strategy_id: str,
                                 position: Optional[Position],
                                 market_data: Dict[str, Any]) -> ComplianceCheck:
        """Check trading limit compliance"""
        try:
            # Get rule parameters
            max_order_size = rule.parameters.get('max_order_size', float('inf'))
            max_daily_volume = rule.parameters.get('max_daily_volume', float('inf'))
            max_daily_trades = rule.parameters.get('max_daily_trades', float('inf'))
            
            # Check order size limit
            if quantity > max_order_size:
                return ComplianceCheck(
                    check_id=str(uuid.uuid4()),
                    order_id=order_id,
                    rule_id=rule.rule_id,
                    result=ComplianceResult.REJECTED,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    account_id=account_id,
                    strategy_id=strategy_id,
                    violation_message=f"Order size limit exceeded: {quantity} > {max_order_size}",
                    suggested_action=ComplianceAction.REDUCE_SIZE,
                    max_allowed_quantity=max_order_size,
                    rule_parameters=rule.parameters
                )
            
            # Check daily volume limit (simplified - would need to track daily volume)
            # For now, assume we have access to daily volume data
            daily_volume = rule.parameters.get('current_daily_volume', 0.0)
            if daily_volume + quantity > max_daily_volume:
                max_allowed = max(0, max_daily_volume - daily_volume)
                return ComplianceCheck(
                    check_id=str(uuid.uuid4()),
                    order_id=order_id,
                    rule_id=rule.rule_id,
                    result=ComplianceResult.REJECTED if max_allowed <= 0 else ComplianceResult.WARNING,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    account_id=account_id,
                    strategy_id=strategy_id,
                    violation_message=f"Daily volume limit exceeded: {daily_volume + quantity} > {max_daily_volume}",
                    suggested_action=ComplianceAction.REDUCE_SIZE if max_allowed > 0 else ComplianceAction.BLOCK,
                    max_allowed_quantity=max_allowed if max_allowed > 0 else None,
                    rule_parameters=rule.parameters
                )
            
            # Check daily trades limit (simplified)
            daily_trades = rule.parameters.get('current_daily_trades', 0)
            if daily_trades >= max_daily_trades:
                return ComplianceCheck(
                    check_id=str(uuid.uuid4()),
                    order_id=order_id,
                    rule_id=rule.rule_id,
                    result=ComplianceResult.REJECTED,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    account_id=account_id,
                    strategy_id=strategy_id,
                    violation_message=f"Daily trades limit exceeded: {daily_trades} >= {max_daily_trades}",
                    suggested_action=ComplianceAction.BLOCK,
                    rule_parameters=rule.parameters
                )
            
            # Trading limits OK
            return ComplianceCheck(
                check_id=str(uuid.uuid4()),
                order_id=order_id,
                rule_id=rule.rule_id,
                result=ComplianceResult.APPROVED,
                symbol=symbol,
                side=side,
                quantity=quantity,
                account_id=account_id,
                strategy_id=strategy_id,
                rule_parameters=rule.parameters
            )
            
        except Exception as e:
            self.logger.error(f"Trading limit check failed: {e}")
            return ComplianceCheck(
                check_id=str(uuid.uuid4()),
                order_id=order_id,
                rule_id=rule.rule_id,
                result=ComplianceResult.REJECTED,
                symbol=symbol,
                side=side,
                quantity=quantity,
                account_id=account_id,
                strategy_id=strategy_id,
                violation_message=f"Trading limit check error: {e}"
            )
    
    async def _check_regulatory(self,
                              rule: ComplianceRule,
                              order_id: str,
                              symbol: str,
                              side: str,
                              quantity: float,
                              price: Optional[float],
                              account_id: str,
                              strategy_id: str,
                              position: Optional[Position],
                              market_data: Dict[str, Any]) -> ComplianceCheck:
        """Check regulatory compliance"""
        try:
            # Get rule parameters
            regulation_type = rule.parameters.get('regulation_type', 'general')
            
            # Example regulatory checks
            if regulation_type == 'short_sale_rule':
                # Simplified short sale rule check
                if side.lower() == 'sell' and (not position or position.quantity < quantity):
                    # This would be a short sale
                    uptick_required = rule.parameters.get('uptick_required', True)
                    if uptick_required:
                        # Check if last price movement was up (simplified)
                        last_price_change = market_data.get('last_price_change', 0.0)
                        if last_price_change <= 0:
                            return ComplianceCheck(
                                check_id=str(uuid.uuid4()),
                                order_id=order_id,
                                rule_id=rule.rule_id,
                                result=ComplianceResult.REJECTED,
                                symbol=symbol,
                                side=side,
                                quantity=quantity,
                                account_id=account_id,
                                strategy_id=strategy_id,
                                violation_message="Short sale rule violation: uptick required",
                                suggested_action=ComplianceAction.BLOCK,
                                rule_parameters=rule.parameters
                            )
            
            elif regulation_type == 'pattern_day_trader':
                # Pattern Day Trader rule check
                account_equity = rule.parameters.get('account_equity', 25000.0)
                day_trades_count = rule.parameters.get('day_trades_count', 0)
                
                if account_equity < 25000 and day_trades_count >= 3:
                    return ComplianceCheck(
                        check_id=str(uuid.uuid4()),
                        order_id=order_id,
                        rule_id=rule.rule_id,
                        result=ComplianceResult.REJECTED,
                        symbol=symbol,
                        side=side,
                        quantity=quantity,
                        account_id=account_id,
                        strategy_id=strategy_id,
                        violation_message=f"Pattern Day Trader rule violation: Account equity ${account_equity} < $25,000 with {day_trades_count} day trades",
                        suggested_action=ComplianceAction.BLOCK,
                        rule_parameters=rule.parameters
                    )
            
            # Regulatory compliance OK
            return ComplianceCheck(
                check_id=str(uuid.uuid4()),
                order_id=order_id,
                rule_id=rule.rule_id,
                result=ComplianceResult.APPROVED,
                symbol=symbol,
                side=side,
                quantity=quantity,
                account_id=account_id,
                strategy_id=strategy_id,
                rule_parameters=rule.parameters
            )
            
        except Exception as e:
            self.logger.error(f"Regulatory check failed: {e}")
            return ComplianceCheck(
                check_id=str(uuid.uuid4()),
                order_id=order_id,
                rule_id=rule.rule_id,
                result=ComplianceResult.REJECTED,
                symbol=symbol,
                side=side,
                quantity=quantity,
                account_id=account_id,
                strategy_id=strategy_id,
                violation_message=f"Regulatory check error: {e}"
            )
    
    async def _check_custom_rule(self,
                               rule: ComplianceRule,
                               order_id: str,
                               symbol: str,
                               side: str,
                               quantity: float,
                               price: Optional[float],
                               account_id: str,
                               strategy_id: str,
                               position: Optional[Position],
                               market_data: Dict[str, Any]) -> ComplianceCheck:
        """Check custom rule compliance"""
        try:
            # Execute custom rule logic
            if rule.rule_logic:
                # Call custom function
                result = await rule.rule_logic(
                    order_id, symbol, side, quantity, price,
                    account_id, strategy_id, position, market_data, rule.parameters
                )
                
                if isinstance(result, ComplianceCheck):
                    return result
                elif isinstance(result, bool):
                    return ComplianceCheck(
                        check_id=str(uuid.uuid4()),
                        order_id=order_id,
                        rule_id=rule.rule_id,
                        result=ComplianceResult.APPROVED if result else ComplianceResult.REJECTED,
                        symbol=symbol,
                        side=side,
                        quantity=quantity,
                        account_id=account_id,
                        strategy_id=strategy_id,
                        violation_message="" if result else "Custom rule violation",
                        rule_parameters=rule.parameters
                    )
            
            elif rule.rule_expression:
                # Evaluate expression (simplified - would use safe expression evaluator)
                # For now, just return approved
                pass
            
            # Default to approved for custom rules
            return ComplianceCheck(
                check_id=str(uuid.uuid4()),
                order_id=order_id,
                rule_id=rule.rule_id,
                result=ComplianceResult.APPROVED,
                symbol=symbol,
                side=side,
                quantity=quantity,
                account_id=account_id,
                strategy_id=strategy_id,
                rule_parameters=rule.parameters
            )
            
        except Exception as e:
            self.logger.error(f"Custom rule check failed: {e}")
            return ComplianceCheck(
                check_id=str(uuid.uuid4()),
                order_id=order_id,
                rule_id=rule.rule_id,
                result=ComplianceResult.REJECTED,
                symbol=symbol,
                side=side,
                quantity=quantity,
                account_id=account_id,
                strategy_id=strategy_id,
                violation_message=f"Custom rule check error: {e}"
            )
    
    async def _handle_violation(self, check: ComplianceCheck, rule: ComplianceRule):
        """Handle compliance violation"""
        try:
            # Create violation record
            violation = ComplianceViolation(
                violation_id=str(uuid.uuid4()),
                rule_id=rule.rule_id,
                order_id=check.order_id,
                violation_type=rule.rule_type,
                severity=rule.severity,
                message=check.violation_message,
                account_id=check.account_id,
                symbol=check.symbol,
                quantity=check.quantity,
                action_taken=check.suggested_action or ComplianceAction.BLOCK
            )
            
            # Store violation
            self._violations[violation.violation_id] = violation
            self._violation_history.append(violation)
            
            # Update metrics
            self._metrics['violations_detected'] += 1
            
            # Publish violation alert
            if self.message_bus:
                await self.message_bus.publish(
                    topic=f"compliance.violations.{check.account_id}",
                    message={
                        'violation_id': violation.violation_id,
                        'rule_id': rule.rule_id,
                        'order_id': check.order_id,
                        'severity': rule.severity.value,
                        'message': check.violation_message,
                        'symbol': check.symbol,
                        'account_id': check.account_id,
                        'timestamp': violation.violation_time.isoformat()
                    }
                )
            
            # Add to audit trail
            self._add_to_audit_trail({
                'type': 'violation',
                'violation_id': violation.violation_id,
                'rule_id': rule.rule_id,
                'order_id': check.order_id,
                'severity': rule.severity.value,
                'message': check.violation_message,
                'timestamp': datetime.now()
            })
            
        except Exception as e:
            self.logger.error(f"Failed to handle violation: {e}")
    
    async def _position_monitor(self):
        """Real-time position monitoring"""
        while self._running:
            try:
                # Monitor position limits
                for (account_id, symbol), position in self._positions.items():
                    # Check if position exceeds any limits
                    applicable_rules = self._get_applicable_rules(account_id, symbol, "")
                    
                    for rule in applicable_rules:
                        if rule.rule_type == RuleType.POSITION_LIMIT:
                            max_position = rule.parameters.get('max_position', float('inf'))
                            if abs(position.quantity) > max_position:
                                # Create violation
                                violation = ComplianceViolation(
                                    violation_id=str(uuid.uuid4()),
                                    rule_id=rule.rule_id,
                                    order_id="position_monitor",
                                    violation_type=rule.rule_type,
                                    severity=rule.severity,
                                    message=f"Position limit exceeded: {position.quantity} > {max_position}",
                                    account_id=account_id,
                                    symbol=symbol,
                                    quantity=position.quantity,
                                    action_taken=ComplianceAction.ESCALATE
                                )
                                
                                # Handle violation
                                await self._handle_position_violation(violation)
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                self.logger.error(f"Position monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def _violation_monitor(self):
        """Monitor and manage violations"""
        while self._running:
            try:
                # Check for unresolved violations
                unresolved_violations = [
                    v for v in self._violations.values() 
                    if not v.resolved and 
                    (datetime.now() - v.violation_time).total_seconds() > 300  # 5 minutes old
                ]
                
                for violation in unresolved_violations:
                    # Escalate old violations
                    await self._escalate_violation(violation)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Violation monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _metrics_tracker(self):
        """Track and publish compliance metrics"""
        while self._running:
            try:
                # Update rule count
                self._metrics['rules_active'] = len([r for r in self._rules.values() if r.is_active])
                
                # Publish metrics
                if self.message_bus:
                    await self.message_bus.publish(
                        topic="compliance.metrics",
                        message=self._metrics.copy()
                    )
                
                await asyncio.sleep(60)  # Update every minute
                
            except Exception as e:
                self.logger.error(f"Metrics tracking error: {e}")
                await asyncio.sleep(60)
    
    async def _handle_position_violation(self, violation: ComplianceViolation):
        """Handle position-based violations"""
        try:
            # Store violation
            self._violations[violation.violation_id] = violation
            self._violation_history.append(violation)
            
            # Update metrics
            self._metrics['violations_detected'] += 1
            
            # Publish alert
            if self.message_bus:
                await self.message_bus.publish(
                    topic=f"compliance.position_violations.{violation.account_id}",
                    message={
                        'violation_id': violation.violation_id,
                        'account_id': violation.account_id,
                        'symbol': violation.symbol,
                        'message': violation.message,
                        'severity': violation.severity.value,
                        'timestamp': violation.violation_time.isoformat()
                    }
                )
            
        except Exception as e:
            self.logger.error(f"Failed to handle position violation: {e}")
    
    async def _escalate_violation(self, violation: ComplianceViolation):
        """Escalate unresolved violations"""
        try:
            # Mark as escalated
            violation.metadata['escalated'] = True
            violation.metadata['escalation_time'] = datetime.now().isoformat()
            
            # Publish escalation alert
            if self.message_bus:
                await self.message_bus.publish(
                    topic="compliance.escalations",
                    message={
                        'violation_id': violation.violation_id,
                        'rule_id': violation.rule_id,
                        'account_id': violation.account_id,
                        'symbol': violation.symbol,
                        'message': f"ESCALATED: {violation.message}",
                        'severity': 'CRITICAL',
                        'original_time': violation.violation_time.isoformat(),
                        'escalation_time': violation.metadata['escalation_time']
                    }
                )
            
            self.logger.warning(f"Escalated violation {violation.violation_id}: {violation.message}")
            
        except Exception as e:
            self.logger.error(f"Failed to escalate violation: {e}")
    
    async def _load_default_rules(self):
        """Load default compliance rules"""
        try:
            # Position limit rule
            position_rule = ComplianceRule(
                rule_id="default_position_limit",
                rule_name="Default Position Limit",
                rule_type=RuleType.POSITION_LIMIT,
                severity=RuleSeverity.ERROR,
                action=ComplianceAction.BLOCK,
                parameters={
                    'max_position': 10000.0,
                    'max_long_position': 10000.0,
                    'max_short_position': 10000.0
                },
                description="Default position size limits"
            )
            
            # Concentration limit rule
            concentration_rule = ComplianceRule(
                rule_id="default_concentration_limit",
                rule_name="Default Concentration Limit",
                rule_type=RuleType.CONCENTRATION_LIMIT,
                severity=RuleSeverity.WARNING,
                action=ComplianceAction.WARN,
                parameters={
                    'max_concentration_percent': 10.0,
                    'portfolio_value': 1000000.0
                },
                description="Default portfolio concentration limits"
            )
            
            # Risk limit rule
            risk_rule = ComplianceRule(
                rule_id="default_risk_limit",
                rule_name="Default Risk Limit",
                rule_type=RuleType.RISK_LIMIT,
                severity=RuleSeverity.ERROR,
                action=ComplianceAction.BLOCK,
                parameters={
                    'max_var_1d': 50000.0,
                    'max_var_10d': 100000.0,
                    'max_beta_exposure': 1000000.0
                },
                description="Default risk exposure limits"
            )
            
            # Trading limit rule
            trading_rule = ComplianceRule(
                rule_id="default_trading_limit",
                rule_name="Default Trading Limit",
                rule_type=RuleType.TRADING_LIMIT,
                severity=RuleSeverity.WARNING,
                action=ComplianceAction.WARN,
                parameters={
                    'max_order_size': 5000.0,
                    'max_daily_volume': 100000.0,
                    'max_daily_trades': 100
                },
                description="Default trading activity limits"
            )
            
            # Add rules
            await self.add_rule(position_rule)
            await self.add_rule(concentration_rule)
            await self.add_rule(risk_rule)
            await self.add_rule(trading_rule)
            
            self.logger.info("Default compliance rules loaded")
            
        except Exception as e:
            self.logger.error(f"Failed to load default rules: {e}")
    
    def _add_to_audit_trail(self, entry: Dict[str, Any]):
        """Add entry to audit trail"""
        try:
            entry['id'] = str(uuid.uuid4())
            entry['timestamp'] = entry.get('timestamp', datetime.now())
            self._audit_trail.append(entry)
        except Exception as e:
            self.logger.error(f"Failed to add audit trail entry: {e}")
    
    # Public API Methods
    
    async def add_rule(self, rule: ComplianceRule):
        """Add a compliance rule"""
        try:
            self._rules[rule.rule_id] = rule
            
            # Clear rule cache
            self._rule_cache.clear()
            
            # Add to audit trail
            self._add_to_audit_trail({
                'type': 'rule_added',
                'rule_id': rule.rule_id,
                'rule_name': rule.rule_name,
                'rule_type': rule.rule_type.value,
                'severity': rule.severity.value
            })
            
            self.logger.info(f"Added compliance rule: {rule.rule_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to add rule {rule.rule_id}: {e}")
            raise
    
    async def remove_rule(self, rule_id: str):
        """Remove a compliance rule"""
        try:
            if rule_id in self._rules:
                rule = self._rules.pop(rule_id)
                
                # Clear rule cache
                self._rule_cache.clear()
                
                # Add to audit trail
                self._add_to_audit_trail({
                    'type': 'rule_removed',
                    'rule_id': rule_id,
                    'rule_name': rule.rule_name
                })
                
                self.logger.info(f"Removed compliance rule: {rule_id}")
            else:
                raise ValueError(f"Rule {rule_id} not found")
                
        except Exception as e:
            self.logger.error(f"Failed to remove rule {rule_id}: {e}")
            raise
    
    async def update_rule(self, rule_id: str, updates: Dict[str, Any]):
        """Update a compliance rule"""
        try:
            if rule_id not in self._rules:
                raise ValueError(f"Rule {rule_id} not found")
            
            rule = self._rules[rule_id]
            
            # Update rule properties
            for key, value in updates.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)
                elif key == 'parameters':
                    rule.parameters.update(value)
            
            rule.last_modified = datetime.now()
            
            # Clear rule cache
            self._rule_cache.clear()
            
            # Add to audit trail
            self._add_to_audit_trail({
                'type': 'rule_updated',
                'rule_id': rule_id,
                'updates': updates
            })
            
            self.logger.info(f"Updated compliance rule: {rule_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to update rule {rule_id}: {e}")
            raise
    
    async def update_position(self, account_id: str, symbol: str, position: Position):
        """Update position information"""
        try:
            self._positions[(account_id, symbol)] = position
            
            # Cache position data
            if self.cache_manager:
                await self.cache_manager.set(
                    f"position:{account_id}:{symbol}",
                    position,
                    ttl=60
                )
            
        except Exception as e:
            self.logger.error(f"Failed to update position {account_id}:{symbol}: {e}")
    
    async def update_market_data(self, symbol: str, market_data: Dict[str, Any]):
        """Update market data"""
        try:
            self._market_data[symbol] = market_data
            
            # Cache market data
            if self.cache_manager:
                await self.cache_manager.set(
                    f"market_data:{symbol}",
                    market_data,
                    ttl=1
                )
            
        except Exception as e:
            self.logger.error(f"Failed to update market data for {symbol}: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get compliance engine metrics"""
        return self._metrics.copy()
    
    def get_violations(self, resolved: Optional[bool] = None) -> List[ComplianceViolation]:
        """Get compliance violations"""
        violations = list(self._violations.values())
        
        if resolved is not None:
            violations = [v for v in violations if v.resolved == resolved]
        
        return violations
    
    def get_audit_trail(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit trail entries"""
        return list(self._audit_trail)[-limit:]
    
    async def resolve_violation(self, violation_id: str, resolution_notes: str = ""):
        """Resolve a compliance violation"""
        try:
            if violation_id not in self._violations:
                raise ValueError(f"Violation {violation_id} not found")
            
            violation = self._violations[violation_id]
            violation.resolved = True
            violation.resolution_time = datetime.now()
            violation.resolution_notes = resolution_notes
            
            # Update metrics
            self._metrics['violations_resolved'] += 1
            
            # Add to audit trail
            self._add_to_audit_trail({
                'type': 'violation_resolved',
                'violation_id': violation_id,
                'resolution_notes': resolution_notes
            })
            
            self.logger.info(f"Resolved violation {violation_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to resolve violation {violation_id}: {e}")
            raiseol,
                quantity=check.quantity,
                action_taken=rule.action
            )
            
            # Store violation
            self._violations[violation.violation_id] = violation
            self._violation_history.append(violation)
            
            # Update metrics
            self._metrics['violations_detected'] += 1
            
            # Send alert if message bus available
            if self.message_bus:
                await self.message_bus.publish(
                    topic=f"compliance.violations.{rule.severity.value}",
                    message={
                        'violation_id': violation.violation_id,
                        'rule_id': rule.rule_id,
                        'order_id': check.order_id,
                        'symbol': check.symbol,
                        'account_id': check.account_id,
                        'message': check.violation_message,
                        'severity': rule.severity.value,
                        'timestamp': violation.violation_time.isoformat()
                    }
                )
            
            # Add to audit trail
            self._add_to_audit_trail({
                'type': 'violation',
                'violation_id': violation.violation_id,
                'rule_id': rule.rule_id,
                'order_id': check.order_id,
                'severity': rule.severity.value,
                'message': check.violation_message,
                'timestamp': datetime.now()
            })
            
        except Exception as e:
            self.logger.error(f"Violation handling failed: {e}")
    
    def _add_to_audit_trail(self, entry: Dict[str, Any]):
        """Add entry to audit trail"""
        try:
            entry['audit_id'] = str(uuid.uuid4())
            entry['timestamp'] = entry.get('timestamp', datetime.now())
            self._audit_trail.append(entry)
        except Exception as e:
            self.logger.error(f"Audit trail entry failed: {e}")
    
    # Rule Management Methods
    
    async def add_rule(self, rule: ComplianceRule) -> bool:
        """Add compliance rule"""
        try:
            self._rules[rule.rule_id] = rule
            self._metrics['rules_active'] = len([r for r in self._rules.values() if r.is_active])
            
            self.logger.info(f"Added compliance rule: {rule.rule_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add rule {rule.rule_id}: {e}")
            return False
    
    async def remove_rule(self, rule_id: str) -> bool:
        """Remove compliance rule"""
        try:
            if rule_id in self._rules:
                del self._rules[rule_id]
                self._metrics['rules_active'] = len([r for r in self._rules.values() if r.is_active])
                self.logger.info(f"Removed compliance rule: {rule_id}")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to remove rule {rule_id}: {e}")
            return False
    
    async def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """Update compliance rule"""
        try:
            if rule_id not in self._rules:
                return False
            
            rule = self._rules[rule_id]
            
            # Update rule properties
            for key, value in updates.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)
            
            rule.last_modified = datetime.now()
            
            self.logger.info(f"Updated compliance rule: {rule_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update rule {rule_id}: {e}")
            return False
    
    async def activate_rule(self, rule_id: str) -> bool:
        """Activate compliance rule"""
        return await self.update_rule(rule_id, {'is_active': True})
    
    async def deactivate_rule(self, rule_id: str) -> bool:
        """Deactivate compliance rule"""
        return await self.update_rule(rule_id, {'is_active': False})
    
    # Position Management Methods
    
    async def update_position(self, position: Position):
        """Update position information"""
        try:
            key = (position.account_id, position.symbol)
            self._positions[key] = position
            
            # Cache position data
            if self.cache_manager:
                await self.cache_manager.set(
                    f"position:{position.account_id}:{position.symbol}",
                    position,
                    ttl=60
                )
            
        except Exception as e:
            self.logger.error(f"Failed to update position: {e}")
    
    async def update_market_data(self, symbol: str, market_data: Dict[str, Any]):
        """Update market data"""
        try:
            self._market_data[symbol].update(market_data)
            
            # Cache market data
            if self.cache_manager:
                await self.cache_manager.set(f"market_data:{symbol}", market_data, ttl=1)
                
        except Exception as e:
            self.logger.error(f"Failed to update market data: {e}")
    
    # Monitoring Methods
    
    async def _position_monitor(self):
        """Monitor positions for limit breaches"""
        while self._running:
            try:
                # Check all positions against limits
                for (account_id, symbol), position in self._positions.items():
                    # Get applicable position limit rules
                    applicable_rules = [
                        rule for rule in self._rules.values()
                        if (rule.rule_type == RuleType.POSITION_LIMIT and
                            rule.is_active and
                            (not rule.applies_to_accounts or account_id in rule.applies_to_accounts) and
                            (not rule.applies_to_symbols or symbol in rule.applies_to_symbols))
                    ]
                    
                    for rule in applicable_rules:
                        # Check if position exceeds limits
                        max_position = rule.parameters.get('max_position', float('inf'))
                        max_long = rule.parameters.get('max_long_position', max_position)
                        max_short = rule.parameters.get('max_short_position', max_position)
                        
                        if position.quantity > max_long or position.quantity < -max_short:
                            # Create violation
                            violation = ComplianceViolation(
                                violation_id=str(uuid.uuid4()),
                                rule_id=rule.rule_id,
                                order_id="position_monitor",
                                violation_type=RuleType.POSITION_LIMIT,
                                severity=rule.severity,
                                message=f"Position limit breach detected: {position.quantity} exceeds limits",
                                account_id=account_id,
                                symbol=symbol,
                                quantity=position.quantity,
                                action_taken=ComplianceAction.ESCALATE
                            )
                            
                            await self._handle_violation_alert(violation)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Position monitoring error: {e}")
                await asyncio.sleep(30)
    
    async def _violation_monitor(self):
        """Monitor for unresolved violations"""
        while self._running:
            try:
                # Check for unresolved violations older than threshold
                threshold_time = datetime.now() - timedelta(minutes=30)
                
                for violation in self._violations.values():
                    if (not violation.resolved and 
                        violation.violation_time < threshold_time and
                        violation.severity in [RuleSeverity.ERROR, RuleSeverity.CRITICAL]):
                        
                        # Escalate unresolved critical violations
                        await self._escalate_violation(violation)
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Violation monitoring error: {e}")
                await asyncio.sleep(300)
    
    async def _handle_violation_alert(self, violation: ComplianceViolation):
        """Handle violation alert"""
        try:
            # Send immediate alert for critical violations
            if violation.severity == RuleSeverity.CRITICAL:
                if self.message_bus:
                    await self.message_bus.publish(
                        topic="compliance.alerts.critical",
                        message={
                            'violation_id': violation.violation_id,
                            'message': violation.message,
                            'account_id': violation.account_id,
                            'symbol': violation.symbol,
                            'timestamp': violation.violation_time.isoformat()
                        }
                    )
            
            # Store violation
            self._violations[violation.violation_id] = violation
            self._violation_history.append(violation)
            
        except Exception as e:
            self.logger.error(f"Violation alert handling failed: {e}")
    
    async def _escalate_violation(self, violation: ComplianceViolation):
        """Escalate unresolved violation"""
        try:
            if self.message_bus:
                await self.message_bus.publish(
                    topic="compliance.escalation",
                    message={
                        'violation_id': violation.violation_id,
                        'rule_id': violation.rule_id,
                        'message': f"ESCALATION: Unresolved violation - {violation.message}",
                        'account_id': violation.account_id,
                        'symbol': violation.symbol,
                        'age_minutes': (datetime.now() - violation.violation_time).total_seconds() / 60,
                        'timestamp': datetime.now().isoformat()
                    }
                )
            
            self.logger.warning(f"Escalated violation {violation.violation_id}: {violation.message}")
            
        except Exception as e:
            self.logger.error(f"Violation escalation failed: {e}")
    
    async def _metrics_tracker(self):
        """Track compliance metrics"""
        while self._running:
            try:
                # Update active rules count
                self._metrics['rules_active'] = len([r for r in self._rules.values() if r.is_active])
                
                # Update violation resolution rate
                total_violations = len(self._violation_history)
                resolved_violations = len([v for v in self._violation_history if v.resolved])
                
                if total_violations > 0:
                    self._metrics['violation_resolution_rate'] = resolved_violations / total_violations
                
                await asyncio.sleep(60)  # Update every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Metrics tracking error: {e}")
                await asyncio.sleep(60)
    
    async def _load_default_rules(self):
        """Load default compliance rules"""
        try:
            # Default position limit rule
            position_limit_rule = ComplianceRule(
                rule_id="default_position_limit",
                rule_name="Default Position Limit",
                rule_type=RuleType.POSITION_LIMIT,
                severity=RuleSeverity.ERROR,
                action=ComplianceAction.BLOCK,
                parameters={
                    'max_position': 10000.0,
                    'max_long_position': 10000.0,
                    'max_short_position': 10000.0
                },
                description="Default position limit of 10,000 shares per symbol"
            )
            await self.add_rule(position_limit_rule)
            
            # Default concentration limit rule
            concentration_rule = ComplianceRule(
                rule_id="default_concentration_limit",
                rule_name="Default Concentration Limit",
                rule_type=RuleType.CONCENTRATION_LIMIT,
                severity=RuleSeverity.WARNING,
                action=ComplianceAction.WARN,
                parameters={
                    'max_concentration_percent': 15.0,
                    'portfolio_value': 1000000.0
                },
                description="Default concentration limit of 15% per position"
            )
            await self.add_rule(concentration_rule)
            
            # Default order size limit
            order_size_rule = ComplianceRule(
                rule_id="default_order_size_limit",
                rule_name="Default Order Size Limit",
                rule_type=RuleType.TRADING_LIMIT,
                severity=RuleSeverity.ERROR,
                action=ComplianceAction.BLOCK,
                parameters={
                    'max_order_size': 5000.0
                },
                description="Default maximum order size of 5,000 shares"
            )
            await self.add_rule(order_size_rule)
            
            self.logger.info("Loaded default compliance rules")
            
        except Exception as e:
            self.logger.error(f"Failed to load default rules: {e}")
    
    # Public API Methods
    
    def get_rule(self, rule_id: str) -> Optional[ComplianceRule]:
        """Get compliance rule by ID"""
        return self._rules.get(rule_id)
    
    def get_all_rules(self) -> List[ComplianceRule]:
        """Get all compliance rules"""
        return list(self._rules.values())
    
    def get_active_rules(self) -> List[ComplianceRule]:
        """Get active compliance rules"""
        return [rule for rule in self._rules.values() if rule.is_active]
    
    def get_violation(self, violation_id: str) -> Optional[ComplianceViolation]:
        """Get violation by ID"""
        return self._violations.get(violation_id)
    
    def get_violations_by_account(self, account_id: str) -> List[ComplianceViolation]:
        """Get violations for account"""
        return [v for v in self._violation_history if v.account_id == account_id]
    
    def get_violations_by_rule(self, rule_id: str) -> List[ComplianceViolation]:
        """Get violations for rule"""
        return [v for v in self._violation_history if v.rule_id == rule_id]
    
    def get_unresolved_violations(self) -> List[ComplianceViolation]:
        """Get unresolved violations"""
        return [v for v in self._violations.values() if not v.resolved]
    
    def get_compliance_metrics(self) -> Dict[str, Any]:
        """Get compliance metrics"""
        return self._metrics.copy()
    
    def get_audit_trail(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit trail entries"""
        return list(self._audit_trail)[-limit:]
    
    async def resolve_violation(self, violation_id: str, resolution_notes: str = "") -> bool:
        """Resolve a compliance violation"""
        try:
            if violation_id in self._violations:
                violation = self._violations[violation_id]
                violation.resolved = True
                violation.resolution_time = datetime.now()
                violation.resolution_notes = resolution_notes
                
                # Remove from active violations
                del self._violations[violation_id]
                
                # Update metrics
                self._metrics['violations_resolved'] += 1
                
                # Add to audit trail
                self._add_to_audit_trail({
                    'type': 'violation_resolved',
                    'violation_id': violation_id,
                    'resolution_notes': resolution_notes,
                    'timestamp': datetime.now()
                })
                
                self.logger.info(f"Resolved violation {violation_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to resolve violation {violation_id}: {e}")
            return False
    
    async def get_compliance_summary(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        """Get compliance summary"""
        try:
            summary = {
                'total_rules': len(self._rules),
                'active_rules': len([r for r in self._rules.values() if r.is_active]),
                'total_violations': len(self._violation_history),
                'unresolved_violations': len(self._violations),
                'metrics': self._metrics.copy()
            }
            
            if account_id:
                account_violations = self.get_violations_by_account(account_id)
                summary['account_violations'] = len(account_violations)
                summary['account_unresolved'] = len([v for v in account_violations if not v.resolved])
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get compliance summary: {e}")
            return {}
    
    def is_compliant(self, compliance_checks: List[ComplianceCheck]) -> bool:
        """Check if all compliance checks passed"""
        return all(check.result == ComplianceResult.APPROVED for check in compliance_checks)
    
    def has_blocking_violations(self, compliance_checks: List[ComplianceCheck]) -> bool:
        """Check if any compliance checks are blocking"""
        return any(check.result == ComplianceResult.REJECTED for check in compliance_checks)