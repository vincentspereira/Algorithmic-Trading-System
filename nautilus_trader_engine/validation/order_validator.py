"""Order Validator for Asset Class Specific Rules
Validates orders against asset class specific trading rules.
"""

from typing import Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Result of order validation."""
    valid: bool
    violations: List[str] = field(default_factory=list)


class AssetClassOrderValidator:
    """Validates orders against asset class specific rules."""
    
    def __init__(self):
        """Initialize the order validator."""
        self.trading_rules = {
            'forex': {
                'min_quantity': 1000,
                'max_quantity': 10000000,
                'allowed_order_types': ['MARKET', 'LIMIT', 'STOP'],
                'trading_sessions': ['LONDON', 'NEW_YORK', 'TOKYO'],
                'weekend_trading': False
            },
            'stocks': {
                'min_quantity': 1,
                'max_quantity': 1000000,
                'allowed_order_types': ['MARKET', 'LIMIT', 'STOP_LIMIT'],
                'trading_sessions': ['REGULAR', 'PRE_MARKET', 'AFTER_HOURS'],
                'weekend_trading': False
            },
            'crypto': {
                'min_quantity': 0.001,
                'max_quantity': 1000,
                'allowed_order_types': ['MARKET', 'LIMIT', 'STOP'],
                'trading_sessions': ['24_7'],
                'weekend_trading': True
            }
        }
    
    def validate_order(self, order: Dict[str, Any]) -> ValidationResult:
        """Validate order against asset class rules.
        
        Args:
            order: Order details dictionary
            
        Returns:
            ValidationResult with validation details
        """
        asset_class = order['asset_class']
        rules = self.trading_rules.get(asset_class, {})
        
        validation_result = ValidationResult(valid=True, violations=[])
        
        # Check quantity limits
        if order['quantity'] < rules.get('min_quantity', 0):
            validation_result.valid = False
            validation_result.violations.append(f"Quantity below minimum {rules['min_quantity']}")
        
        if order['quantity'] > rules.get('max_quantity', float('inf')):
            validation_result.valid = False
            validation_result.violations.append(f"Quantity above maximum {rules['max_quantity']}")
        
        # Check order type
        allowed_types = rules.get('allowed_order_types', [])
        if order['order_type'] not in allowed_types:
            validation_result.valid = False
            validation_result.violations.append(f"Order type {order['order_type']} not allowed")
        
        return validation_result
    
    def get_trading_rules(self, asset_class: str) -> Dict[str, Any]:
        """Get trading rules for an asset class.
        
        Args:
            asset_class: Asset class name
            
        Returns:
            Dictionary of trading rules
        """
        return self.trading_rules.get(asset_class, {})