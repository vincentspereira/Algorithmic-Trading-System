import asyncio
import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Set
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal
import re

# Configure logging
logger = logging.getLogger(__name__)

class ComplianceLevel(Enum):
    """Compliance check levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class ComplianceCategory(Enum):
    """Compliance categories."""
    PAPER_TRADING = "PAPER_TRADING"
    POSITION_LIMITS = "POSITION_LIMITS"
    RISK_LIMITS = "RISK_LIMITS"
    REGULATORY = "REGULATORY"
    OPERATIONAL = "OPERATIONAL"
    DATA_PRIVACY = "DATA_PRIVACY"
    AUDIT = "AUDIT"
    MARKET_HOURS = "MARKET_HOURS"
    ORDER_VALIDATION = "ORDER_VALIDATION"
    ACCOUNT_RESTRICTIONS = "ACCOUNT_RESTRICTIONS"

class ComplianceAction(Enum):
    """Actions to take on compliance violations."""
    ALLOW = "ALLOW"
    WARN = "WARN"
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"
    LOG_ONLY = "LOG_ONLY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"

@dataclass
class ComplianceRule:
    """Definition of a compliance rule."""
    rule_id: str
    name: str
    description: str
    category: ComplianceCategory
    level: ComplianceLevel
    action: ComplianceAction
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class ComplianceViolation:
    """Record of a compliance violation."""
    violation_id: str
    rule_id: str
    rule_name: str
    category: ComplianceCategory
    level: ComplianceLevel
    action: ComplianceAction
    description: str
    details: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[str] = None
    account_id: Optional[str] = None
    order_id: Optional[str] = None
    resolved: bool = False
    resolution_notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert violation to dictionary."""
        return {
            'violation_id': self.violation_id,
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'category': self.category.value,
            'level': self.level.value,
            'action': self.action.value,
            'description': self.description,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'account_id': self.account_id,
            'order_id': self.order_id,
            'resolved': self.resolved,
            'resolution_notes': self.resolution_notes
        }

@dataclass
class TradingContext:
    """Context information for compliance checks."""
    user_id: str
    account_id: str
    account_type: str  # 'paper' or 'live'
    session_id: Optional[str] = None
    order_id: Optional[str] = None
    symbol: Optional[str] = None
    order_type: Optional[str] = None
    quantity: Optional[Decimal] = None
    price: Optional[Decimal] = None
    side: Optional[str] = None  # 'BUY' or 'SELL'
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    additional_data: Dict[str, Any] = field(default_factory=dict)

class IBComplianceEngine:
    """
    Comprehensive compliance engine for Interactive Brokers integration.
    
    This engine ensures all trading operations comply with:
    - Paper trading requirements and restrictions
    - Regulatory compliance (SEC, FINRA, etc.)
    - Risk management policies
    - Operational controls
    - Data privacy and audit requirements
    """
    
    def __init__(
        self,
        max_violation_history: int = 50000,
        alert_callback: Optional[Callable] = None,
        audit_callback: Optional[Callable] = None
    ):
        """
        Initialize the compliance engine.
        
        Parameters
        ----------
        max_violation_history : int
            Maximum number of violation records to keep
        alert_callback : Callable, optional
            Callback for compliance alerts
        audit_callback : Callable, optional
            Callback for audit logging
        """
        self._max_violation_history = max_violation_history
        self._alert_callback = alert_callback
        self._audit_callback = audit_callback
        
        # Compliance rules and violations
        self._rules: Dict[str, ComplianceRule] = {}
        self._violations: List[ComplianceViolation] = []
        
        # Account and user tracking
        self._paper_accounts: Set[str] = set()
        self._live_accounts: Set[str] = set()
        self._user_permissions: Dict[str, Dict[str, Any]] = {}
        
        # Initialize default rules
        self._initialize_default_rules()
        
        logger.info("IB Compliance Engine initialized")
    
    def _initialize_default_rules(self) -> None:
        """Initialize default compliance rules."""
        
        # Paper Trading Rules
        self.add_rule(ComplianceRule(
            rule_id="PT001",
            name="Paper Trading Account Validation",
            description="Ensure operations are only performed on paper trading accounts",
            category=ComplianceCategory.PAPER_TRADING,
            level=ComplianceLevel.CRITICAL,
            action=ComplianceAction.BLOCK,
            parameters={
                'allowed_account_types': ['paper'],
                'blocked_operations': ['live_trading', 'real_money_transfer']
            }
        ))
        
        self.add_rule(ComplianceRule(
            rule_id="PT002",
            name="Paper Trading Position Limits",
            description="Enforce position limits for paper trading accounts",
            category=ComplianceCategory.PAPER_TRADING,
            level=ComplianceLevel.WARNING,
            action=ComplianceAction.WARN,
            parameters={
                'max_position_value': 1000000,  # $1M max position
                'max_daily_trades': 1000,
                'max_order_size': 10000  # shares/contracts
            }
        ))
        
        self.add_rule(ComplianceRule(
            rule_id="PT003",
            name="Paper Trading Data Usage",
            description="Ensure only free/delayed data is used for paper trading",
            category=ComplianceCategory.PAPER_TRADING,
            level=ComplianceLevel.ERROR,
            action=ComplianceAction.BLOCK,
            parameters={
                'allowed_data_sources': ['yahoo_finance', 'alpha_vantage', 'delayed_ib'],
                'blocked_data_sources': ['real_time_ib', 'premium_feeds']
            }
        ))
        
        # Risk Management Rules
        self.add_rule(ComplianceRule(
            rule_id="RM001",
            name="Maximum Order Size",
            description="Limit maximum order size to prevent fat finger errors",
            category=ComplianceCategory.RISK_LIMITS,
            level=ComplianceLevel.ERROR,
            action=ComplianceAction.BLOCK,
            parameters={
                'max_order_value': 100000,  # $100K max order
                'max_shares': 10000,
                'max_contracts': 100
            }
        ))
        
        self.add_rule(ComplianceRule(
            rule_id="RM002",
            name="Daily Trading Limits",
            description="Enforce daily trading volume limits",
            category=ComplianceCategory.RISK_LIMITS,
            level=ComplianceLevel.WARNING,
            action=ComplianceAction.WARN,
            parameters={
                'max_daily_volume': 1000000,  # $1M daily volume
                'max_daily_trades': 500
            }
        ))
        
        # Market Hours Rules
        self.add_rule(ComplianceRule(
            rule_id="MH001",
            name="Market Hours Validation",
            description="Ensure trading only occurs during market hours",
            category=ComplianceCategory.MARKET_HOURS,
            level=ComplianceLevel.WARNING,
            action=ComplianceAction.WARN,
            parameters={
                'enforce_market_hours': True,
                'allow_pre_market': False,
                'allow_after_hours': False
            }
        ))
        
        # Order Validation Rules
        self.add_rule(ComplianceRule(
            rule_id="OV001",
            name="Order Price Validation",
            description="Validate order prices are within reasonable ranges",
            category=ComplianceCategory.ORDER_VALIDATION,
            level=ComplianceLevel.ERROR,
            action=ComplianceAction.BLOCK,
            parameters={
                'max_price_deviation': 0.10,  # 10% from last price
                'min_price': 0.01,
                'max_price': 10000
            }
        ))
        
        # Regulatory Rules
        self.add_rule(ComplianceRule(
            rule_id="REG001",
            name="Pattern Day Trading Rule",
            description="Monitor pattern day trading violations",
            category=ComplianceCategory.REGULATORY,
            level=ComplianceLevel.WARNING,
            action=ComplianceAction.WARN,
            parameters={
                'min_account_equity': 25000,  # PDT rule minimum
                'max_day_trades_per_week': 3  # For accounts under $25K
            }
        ))
        
        # Data Privacy Rules
        self.add_rule(ComplianceRule(
            rule_id="DP001",
            name="PII Protection",
            description="Ensure personally identifiable information is protected",
            category=ComplianceCategory.DATA_PRIVACY,
            level=ComplianceLevel.CRITICAL,
            action=ComplianceAction.BLOCK,
            parameters={
                'mask_sensitive_data': True,
                'encrypt_storage': True,
                'audit_access': True
            }
        ))
        
        # Audit Rules
        self.add_rule(ComplianceRule(
            rule_id="AUD001",
            name="Transaction Logging",
            description="Ensure all transactions are properly logged",
            category=ComplianceCategory.AUDIT,
            level=ComplianceLevel.CRITICAL,
            action=ComplianceAction.LOG_ONLY,
            parameters={
                'log_all_orders': True,
                'log_all_fills': True,
                'log_all_cancellations': True,
                'retention_days': 2555  # 7 years
            }
        ))
    
    def add_rule(self, rule: ComplianceRule) -> None:
        """Add a compliance rule."""
        self._rules[rule.rule_id] = rule
        logger.info(f"Added compliance rule: {rule.rule_id} - {rule.name}")
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a compliance rule."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            logger.info(f"Removed compliance rule: {rule_id}")
            return True
        return False
    
    def enable_rule(self, rule_id: str) -> bool:
        """Enable a compliance rule."""
        if rule_id in self._rules:
            self._rules[rule_id].enabled = True
            self._rules[rule_id].updated_at = datetime.now(timezone.utc)
            logger.info(f"Enabled compliance rule: {rule_id}")
            return True
        return False
    
    def disable_rule(self, rule_id: str) -> bool:
        """Disable a compliance rule."""
        if rule_id in self._rules:
            self._rules[rule_id].enabled = False
            self._rules[rule_id].updated_at = datetime.now(timezone.utc)
            logger.info(f"Disabled compliance rule: {rule_id}")
            return True
        return False
    
    def register_paper_account(self, account_id: str) -> None:
        """Register an account as paper trading account."""
        self._paper_accounts.add(account_id)
        if account_id in self._live_accounts:
            self._live_accounts.remove(account_id)
        logger.info(f"Registered paper trading account: {account_id}")
    
    def register_live_account(self, account_id: str) -> None:
        """Register an account as live trading account."""
        self._live_accounts.add(account_id)
        if account_id in self._paper_accounts:
            self._paper_accounts.remove(account_id)
        logger.info(f"Registered live trading account: {account_id}")
    
    def set_user_permissions(self, user_id: str, permissions: Dict[str, Any]) -> None:
        """Set user permissions."""
        self._user_permissions[user_id] = permissions
        logger.info(f"Set permissions for user: {user_id}")
    
    def _generate_violation_id(self) -> str:
        """Generate unique violation ID."""
        import uuid
        return str(uuid.uuid4())
    
    async def check_compliance(
        self,
        context: TradingContext,
        operation: str,
        data: Dict[str, Any] = None
    ) -> List[ComplianceViolation]:
        """
        Perform comprehensive compliance checks.
        
        Parameters
        ----------
        context : TradingContext
            Trading context for compliance checks
        operation : str
            Operation being performed
        data : Dict[str, Any], optional
            Additional data for compliance checks
        
        Returns
        -------
        List[ComplianceViolation]
            List of compliance violations found
        """
        violations = []
        
        try:
            # Check each enabled rule
            for rule in self._rules.values():
                if not rule.enabled:
                    continue
                
                violation = await self._check_rule(rule, context, operation, data or {})
                if violation:
                    violations.append(violation)
                    
                    # Log violation
                    await self._log_violation(violation)
                    
                    # Send alert if necessary
                    await self._send_alert_if_needed(violation)
                    
                    # Take action based on rule
                    if rule.action == ComplianceAction.BLOCK:
                        # For blocking actions, we might want to stop checking further rules
                        # depending on the implementation requirements
                        pass
            
            # Store violations
            self._violations.extend(violations)
            
            # Maintain violation history limit
            if len(self._violations) > self._max_violation_history:
                self._violations = self._violations[-self._max_violation_history:]
            
            return violations
            
        except Exception as e:
            logger.error(f"Error during compliance check: {str(e)}")
            # Create a system violation for the compliance check failure
            system_violation = ComplianceViolation(
                violation_id=self._generate_violation_id(),
                rule_id="SYS001",
                rule_name="Compliance System Error",
                category=ComplianceCategory.OPERATIONAL,
                level=ComplianceLevel.CRITICAL,
                action=ComplianceAction.ESCALATE,
                description=f"Compliance check failed: {str(e)}",
                details={'error': str(e), 'operation': operation},
                timestamp=datetime.now(timezone.utc),
                user_id=context.user_id,
                account_id=context.account_id
            )
            return [system_violation]
    
    async def _check_rule(
        self,
        rule: ComplianceRule,
        context: TradingContext,
        operation: str,
        data: Dict[str, Any]
    ) -> Optional[ComplianceViolation]:
        """Check a specific compliance rule."""
        try:
            # Route to specific rule checker based on category
            if rule.category == ComplianceCategory.PAPER_TRADING:
                return await self._check_paper_trading_rule(rule, context, operation, data)
            elif rule.category == ComplianceCategory.RISK_LIMITS:
                return await self._check_risk_limits_rule(rule, context, operation, data)
            elif rule.category == ComplianceCategory.MARKET_HOURS:
                return await self._check_market_hours_rule(rule, context, operation, data)
            elif rule.category == ComplianceCategory.ORDER_VALIDATION:
                return await self._check_order_validation_rule(rule, context, operation, data)
            elif rule.category == ComplianceCategory.REGULATORY:
                return await self._check_regulatory_rule(rule, context, operation, data)
            elif rule.category == ComplianceCategory.DATA_PRIVACY:
                return await self._check_data_privacy_rule(rule, context, operation, data)
            elif rule.category == ComplianceCategory.AUDIT:
                return await self._check_audit_rule(rule, context, operation, data)
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error checking rule {rule.rule_id}: {str(e)}")
            return None
    
    async def _check_paper_trading_rule(
        self,
        rule: ComplianceRule,
        context: TradingContext,
        operation: str,
        data: Dict[str, Any]
    ) -> Optional[ComplianceViolation]:
        """Check paper trading compliance rules."""
        
        if rule.rule_id == "PT001":  # Paper Trading Account Validation
            if context.account_type != 'paper' and context.account_id not in self._paper_accounts:
                return ComplianceViolation(
                    violation_id=self._generate_violation_id(),
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    category=rule.category,
                    level=rule.level,
                    action=rule.action,
                    description="Operation attempted on non-paper trading account",
                    details={
                        'account_id': context.account_id,
                        'account_type': context.account_type,
                        'operation': operation
                    },
                    timestamp=datetime.now(timezone.utc),
                    user_id=context.user_id,
                    account_id=context.account_id
                )
        
        elif rule.rule_id == "PT002":  # Paper Trading Position Limits
            params = rule.parameters
            
            # Check order size
            if context.quantity and context.quantity > params.get('max_order_size', float('inf')):
                return ComplianceViolation(
                    violation_id=self._generate_violation_id(),
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    category=rule.category,
                    level=rule.level,
                    action=rule.action,
                    description="Order size exceeds paper trading limits",
                    details={
                        'order_size': float(context.quantity),
                        'max_allowed': params.get('max_order_size'),
                        'symbol': context.symbol
                    },
                    timestamp=datetime.now(timezone.utc),
                    user_id=context.user_id,
                    account_id=context.account_id,
                    order_id=context.order_id
                )
        
        elif rule.rule_id == "PT003":  # Paper Trading Data Usage
            data_source = data.get('data_source')
            if data_source:
                blocked_sources = rule.parameters.get('blocked_data_sources', [])
                if data_source in blocked_sources:
                    return ComplianceViolation(
                        violation_id=self._generate_violation_id(),
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        category=rule.category,
                        level=rule.level,
                        action=rule.action,
                        description="Blocked data source used for paper trading",
                        details={
                            'data_source': data_source,
                            'blocked_sources': blocked_sources
                        },
                        timestamp=datetime.now(timezone.utc),
                        user_id=context.user_id,
                        account_id=context.account_id
                    )
        
        return None
    
    async def _check_risk_limits_rule(
        self,
        rule: ComplianceRule,
        context: TradingContext,
        operation: str,
        data: Dict[str, Any]
    ) -> Optional[ComplianceViolation]:
        """Check risk limits compliance rules."""
        
        if rule.rule_id == "RM001":  # Maximum Order Size
            params = rule.parameters
            
            if context.quantity and context.price:
                order_value = float(context.quantity) * float(context.price)
                max_value = params.get('max_order_value', float('inf'))
                
                if order_value > max_value:
                    return ComplianceViolation(
                        violation_id=self._generate_violation_id(),
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        category=rule.category,
                        level=rule.level,
                        action=rule.action,
                        description="Order value exceeds maximum limit",
                        details={
                            'order_value': order_value,
                            'max_allowed': max_value,
                            'quantity': float(context.quantity),
                            'price': float(context.price)
                        },
                        timestamp=datetime.now(timezone.utc),
                        user_id=context.user_id,
                        account_id=context.account_id,
                        order_id=context.order_id
                    )
        
        return None
    
    async def _check_market_hours_rule(
        self,
        rule: ComplianceRule,
        context: TradingContext,
        operation: str,
        data: Dict[str, Any]
    ) -> Optional[ComplianceViolation]:
        """Check market hours compliance rules."""
        
        if rule.rule_id == "MH001":  # Market Hours Validation
            if rule.parameters.get('enforce_market_hours', False):
                # This is a simplified check - in practice, you'd need to check
                # market calendars for different exchanges and instruments
                current_time = datetime.now(timezone.utc)
                
                # Example: US market hours (9:30 AM - 4:00 PM ET)
                # This is simplified and should be replaced with proper market calendar logic
                market_open = current_time.replace(hour=14, minute=30, second=0, microsecond=0)  # 9:30 AM ET in UTC
                market_close = current_time.replace(hour=21, minute=0, second=0, microsecond=0)  # 4:00 PM ET in UTC
                
                if not (market_open <= current_time <= market_close):
                    return ComplianceViolation(
                        violation_id=self._generate_violation_id(),
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        category=rule.category,
                        level=rule.level,
                        action=rule.action,
                        description="Trading attempted outside market hours",
                        details={
                            'current_time': current_time.isoformat(),
                            'market_open': market_open.isoformat(),
                            'market_close': market_close.isoformat()
                        },
                        timestamp=datetime.now(timezone.utc),
                        user_id=context.user_id,
                        account_id=context.account_id
                    )
        
        return None
    
    async def _check_order_validation_rule(
        self,
        rule: ComplianceRule,
        context: TradingContext,
        operation: str,
        data: Dict[str, Any]
    ) -> Optional[ComplianceViolation]:
        """Check order validation compliance rules."""
        
        if rule.rule_id == "OV001":  # Order Price Validation
            if context.price:
                params = rule.parameters
                price = float(context.price)
                
                # Check minimum and maximum price
                min_price = params.get('min_price', 0)
                max_price = params.get('max_price', float('inf'))
                
                if price < min_price or price > max_price:
                    return ComplianceViolation(
                        violation_id=self._generate_violation_id(),
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        category=rule.category,
                        level=rule.level,
                        action=rule.action,
                        description="Order price outside allowed range",
                        details={
                            'order_price': price,
                            'min_price': min_price,
                            'max_price': max_price
                        },
                        timestamp=datetime.now(timezone.utc),
                        user_id=context.user_id,
                        account_id=context.account_id,
                        order_id=context.order_id
                    )
        
        return None
    
    async def _check_regulatory_rule(
        self,
        rule: ComplianceRule,
        context: TradingContext,
        operation: str,
        data: Dict[str, Any]
    ) -> Optional[ComplianceViolation]:
        """Check regulatory compliance rules."""
        
        if rule.rule_id == "REG001":  # Pattern Day Trading Rule
            # This would require tracking day trades over time
            # Implementation would depend on having access to trading history
            pass
        
        return None
    
    async def _check_data_privacy_rule(
        self,
        rule: ComplianceRule,
        context: TradingContext,
        operation: str,
        data: Dict[str, Any]
    ) -> Optional[ComplianceViolation]:
        """Check data privacy compliance rules."""
        
        if rule.rule_id == "DP001":  # PII Protection
            # Check if sensitive data is being logged or transmitted improperly
            sensitive_fields = ['ssn', 'account_number', 'password', 'api_key']
            
            for field in sensitive_fields:
                if field in data and not rule.parameters.get('mask_sensitive_data', False):
                    return ComplianceViolation(
                        violation_id=self._generate_violation_id(),
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        category=rule.category,
                        level=rule.level,
                        action=rule.action,
                        description="Sensitive data not properly protected",
                        details={
                            'sensitive_field': field,
                            'operation': operation
                        },
                        timestamp=datetime.now(timezone.utc),
                        user_id=context.user_id,
                        account_id=context.account_id
                    )
        
        return None
    
    async def _check_audit_rule(
        self,
        rule: ComplianceRule,
        context: TradingContext,
        operation: str,
        data: Dict[str, Any]
    ) -> Optional[ComplianceViolation]:
        """Check audit compliance rules."""
        
        if rule.rule_id == "AUD001":  # Transaction Logging
            # This rule typically doesn't create violations but ensures logging
            if self._audit_callback:
                audit_data = {
                    'operation': operation,
                    'context': context.__dict__,
                    'data': data,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                await self._audit_callback(audit_data)
        
        return None
    
    async def _log_violation(self, violation: ComplianceViolation) -> None:
        """Log compliance violation."""
        log_message = (
            f"Compliance Violation {violation.violation_id}: {violation.description} "
            f"[{violation.category.value}/{violation.level.value}] "
            f"Rule: {violation.rule_name} ({violation.rule_id})"
        )
        
        if violation.level == ComplianceLevel.CRITICAL:
            logger.critical(log_message)
        elif violation.level == ComplianceLevel.ERROR:
            logger.error(log_message)
        elif violation.level == ComplianceLevel.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    async def _send_alert_if_needed(self, violation: ComplianceViolation) -> None:
        """Send alert for compliance violations if needed."""
        try:
            if self._alert_callback and violation.level in [ComplianceLevel.CRITICAL, ComplianceLevel.ERROR]:
                await self._alert_callback(violation)
        except Exception as e:
            logger.error(f"Error sending compliance alert: {str(e)}")
    
    def get_compliance_summary(self) -> Dict[str, Any]:
        """Get compliance summary and statistics."""
        total_violations = len(self._violations)
        
        if total_violations == 0:
            return {
                'total_violations': 0,
                'active_rules': len([r for r in self._rules.values() if r.enabled]),
                'total_rules': len(self._rules)
            }
        
        # Calculate statistics
        level_counts = {level.value: 0 for level in ComplianceLevel}
        category_counts = {category.value: 0 for category in ComplianceCategory}
        recent_violations = 0
        
        recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        
        for violation in self._violations:
            level_counts[violation.level.value] += 1
            category_counts[violation.category.value] += 1
            
            if violation.timestamp > recent_cutoff:
                recent_violations += 1
        
        return {
            'total_violations': total_violations,
            'recent_violations_24h': recent_violations,
            'level_breakdown': level_counts,
            'category_breakdown': category_counts,
            'active_rules': len([r for r in self._rules.values() if r.enabled]),
            'total_rules': len(self._rules),
            'paper_accounts': len(self._paper_accounts),
            'live_accounts': len(self._live_accounts)
        }
    
    def get_recent_violations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent compliance violations."""
        recent_violations = self._violations[-limit:] if limit else self._violations
        return [violation.to_dict() for violation in recent_violations]
    
    def get_rules(self) -> List[Dict[str, Any]]:
        """Get all compliance rules."""
        return [
            {
                'rule_id': rule.rule_id,
                'name': rule.name,
                'description': rule.description,
                'category': rule.category.value,
                'level': rule.level.value,
                'action': rule.action.value,
                'enabled': rule.enabled,
                'parameters': rule.parameters,
                'created_at': rule.created_at.isoformat(),
                'updated_at': rule.updated_at.isoformat()
            }
            for rule in self._rules.values()
        ]
    
    def resolve_violation(self, violation_id: str, resolution_notes: str) -> bool:
        """Mark a violation as resolved."""
        for violation in self._violations:
            if violation.violation_id == violation_id:
                violation.resolved = True
                violation.resolution_notes = resolution_notes
                logger.info(f"Resolved compliance violation: {violation_id}")
                return True
        return False
    
    async def validate_paper_trading_operation(
        self,
        context: TradingContext,
        operation: str,
        data: Dict[str, Any] = None
    ) -> bool:
        """
        Validate that an operation complies with paper trading requirements.
        
        Parameters
        ----------
        context : TradingContext
            Trading context
        operation : str
            Operation to validate
        data : Dict[str, Any], optional
            Additional operation data
        
        Returns
        -------
        bool
            True if operation is compliant, False otherwise
        """
        violations = await self.check_compliance(context, operation, data)
        
        # Check for blocking violations
        blocking_violations = [
            v for v in violations 
            if v.action == ComplianceAction.BLOCK
        ]
        
        return len(blocking_violations) == 0

# Factory function for easy instantiation
def create_compliance_engine(
    max_violation_history: int = 50000,
    alert_callback: Optional[Callable] = None,
    audit_callback: Optional[Callable] = None
) -> IBComplianceEngine:
    """
    Factory function to create a compliance engine.
    
    Parameters
    ----------
    max_violation_history : int
        Maximum number of violation records to keep
    alert_callback : Callable, optional
        Callback for compliance alerts
    audit_callback : Callable, optional
        Callback for audit logging
    
    Returns
    -------
    IBComplianceEngine
        Configured compliance engine
    """
    return IBComplianceEngine(
        max_violation_history=max_violation_history,
        alert_callback=alert_callback,
        audit_callback=audit_callback
    )