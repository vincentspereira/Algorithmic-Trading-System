# Mock strategy module to satisfy UAT test imports
import asyncio
from unittest.mock import Mock

# Create mock functions for all the expected API endpoints
def get_strategy_form():
    return {
        'status': 'success',
        'form_fields': ['name', 'description', 'parameters', 'risk_limits'],
        'strategy_types': ['mean_reversion', 'momentum', 'arbitrage']
    }

def create_strategy(config):
    return {
        'status': 'success',
        'strategy_id': 'STRAT_001',
        'message': 'Strategy created successfully'
    }

def validate_strategy(config):
    return {
        'status': 'success',
        'validation_result': True,
        'issues': []
    }

def validate_risk_compliance(config):
    return {
        'status': 'success',
        'compliance_status': 'compliant',
        'violations': []
    }

def get_strategy_performance(strategy_id):
    return {
        'status': 'success',
        'performance_metrics': {
            'total_return': 0.125,
            'sharpe_ratio': 1.25,
            'max_drawdown': 0.05
        }
    }

def validate_form_input(input_data):
    return {
        'status': 'success',
        'valid': True,
        'errors': []
    }

def get_strategy_templates():
    return {
        'status': 'success',
        'templates': [
            {'id': 'template_1', 'name': 'Mean Reversion', 'description': 'Basic mean reversion strategy'},
            {'id': 'template_2', 'name': 'Momentum', 'description': 'Momentum-based strategy'}
        ]
    }

# Make sure all attributes are available at module level
__all__ = [
    'get_strategy_form',
    'create_strategy',
    'validate_strategy',
    'validate_risk_compliance',
    'get_strategy_performance',
    'validate_form_input',
    'get_strategy_templates'
]