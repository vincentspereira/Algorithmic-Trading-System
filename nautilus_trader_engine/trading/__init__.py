"""
Advanced Trading System Components
Comprehensive order management, execution algorithms, and compliance systems
"""

# Import order management components directly
from .order_management import (
    OrderLifecycleManager, Order, OrderFill, OrderModification,
    OrderType, OrderStatus, OrderSide, TimeInForce, OrderPriority,
    OrderExecutionQuality, initialize_order_manager, start_order_manager,
    get_order_manager, stop_order_manager
)

__all__ = [
    'OrderLifecycleManager',
    'Order',
    'OrderFill',
    'OrderModification',
    'OrderType',
    'OrderStatus',
    'OrderSide',
    'TimeInForce',
    'OrderPriority',
    'OrderExecutionQuality',
    'initialize_order_manager',
    'start_order_manager',
    'get_order_manager',
    'stop_order_manager'
]

# Try to import other components, but don't fail if they have issues
try:
    from .smart_order_router import SmartOrderRouter, RoutingStrategy, VenueInfo
    __all__.extend(['SmartOrderRouter', 'RoutingStrategy', 'VenueInfo'])
except ImportError as e:
    print(f"Warning: Could not import smart_order_router: {e}")

try:
    from .execution_algorithms import ExecutionEngine, ExecutionAlgorithm, ExecutionState
    __all__.extend(['ExecutionEngine', 'ExecutionAlgorithm', 'ExecutionState'])
except ImportError as e:
    print(f"Warning: Could not import execution_algorithms: {e}")

try:
    from .compliance_engine import ComplianceEngine, ComplianceRule, ComplianceAction
    __all__.extend(['ComplianceEngine', 'ComplianceRule', 'ComplianceAction'])
except ImportError as e:
    print(f"Warning: Could not import compliance_engine: {e}")