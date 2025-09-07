# nautilus_trader_engine/rl/__init__.py

"""
Reinforcement Learning (RL) Integration for NautilusTrader.

This package provides the necessary components to integrate FinRL with the NautilusTrader
ecosystem, enabling the development, training, and deployment of RL-based trading strategies.
"""

try:
    from . import (
        finrl_config,
        environment,
        agents,
        reward_functions,
        training,
        utils,
        blockly_integration,
    )
    __all__ = [
        "finrl_config",
        "environment",
        "agents",
        "reward_functions",
        "training",
        "utils",
        "blockly_integration",
    ]
except ImportError as e:
    print(f"Warning: RL components not available due to missing dependencies: {e}")
    __all__ = []

try:
    from . import (
        finrl_config,
        environment,
        agents,
        reward_functions,
        training,
        utils,
        blockly_integration,
    )
except ImportError as e:
    print(f"Warning: RL components not available due to missing dependencies: {e}")