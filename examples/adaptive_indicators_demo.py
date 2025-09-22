#!/usr/bin/env python3
"""
Adaptive Indicators Demo for Nautilus Trader Engine.

This example demonstrates how to use the adaptive parameter system
to create indicators that automatically adjust to changing market conditions.

Features demonstrated:
- Adaptive parameter registration and management
- Market condition detection and response
- Real-time parameter adaptation
- Performance monitoring and optimization

Usage:
    python examples/adaptive_indicators_demo.py
"""

import asyncio
import sys
from datetime import datetime, timedelta
from typing import Dict, List
import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, '..')

from nautilus_trader_engine.core.adaptive_parameters import (
    get_adaptive_manager, ParameterBounds, ParameterType,
    AdaptationStrategy, create_adaptive_parameter
)
from nautilus_trader_engine.core.interfaces import MarketRegime, RiskLevel
from nautilus_trader_engine.analysis.indicators.technical_indicators import (
    RSI, MACD, BollingerBands, StochasticOscillator
)


class AdaptiveIndicatorDemo:
    """
    Demonstration of adaptive indicators that adjust to market conditions.

    This demo shows how indicators can automatically tune their parameters
    based on volatility, trend strength, and market regime.
    """

    def __init__(self):
        self.adaptive_manager = get_adaptive_manager()
        self.indicators = {}
        self.market_history = []

    async def initialize_adaptive_indicators(self):
        """Initialize indicators with adaptive parameters."""
        print("🔧 Initializing Adaptive Indicators...")
        print("-" * 50)

        # Create adaptive RSI
        rsi_bounds = ParameterBounds(min_value=5, max_value=50)
        rsi_param = create_adaptive_parameter(
            name="rsi_period",
            parameter_type=ParameterType.PERIOD,
            base_value=14,
            bounds=rsi_bounds,
            adaptation_strategy=AdaptationStrategy.VOLATILITY_BASED
        )

        self.adaptive_manager.register_indicator_parameters("rsi", {"period": rsi_param})
        self.indicators["rsi"] = RSI(period=14, enable_volume_weighting=True)

        # Create adaptive MACD
        macd_bounds = ParameterBounds(min_value=5, max_value=50)
        macd_fast = create_adaptive_parameter(
            name="macd_fast",
            parameter_type=ParameterType.PERIOD,
            base_value=12,
            bounds=macd_bounds,
            adaptation_strategy=AdaptationStrategy.VOLATILITY_BASED
        )
        macd_slow = create_adaptive_parameter(
            name="macd_slow",
            parameter_type=ParameterType.PERIOD,
            base_value=26,
            bounds=macd_bounds,
            adaptation_strategy=AdaptationStrategy.VOLATILITY_BASED
        )

        self.adaptive_manager.register_indicator_parameters("macd", {
            "fast_period": macd_fast,
            "slow_period": macd_slow
        })
        self.indicators["macd"] = MACD(fast_period=12, slow_period=26, signal_period=9)

        # Create adaptive Bollinger Bands
        bb_bounds = ParameterBounds(min_value=10, max_value=100)
        bb_period = create_adaptive_parameter(
            name="bb_period",
            parameter_type=ParameterType.PERIOD,
            base_value=20,
            bounds=bb_bounds,
            adaptation_strategy=AdaptationStrategy.VOLATILITY_BASED
        )

        std_bounds = ParameterBounds(min_value=1.0, max_value=3.0)
        bb_std = create_adaptive_parameter(
            name="bb_std_dev",
            parameter_type=ParameterType.MULTIPLIER,
            base_value=2.0,
            bounds=std_bounds,
            adaptation_strategy=AdaptationStrategy.MARKET_REGIME
        )

        self.adaptive_manager.register_indicator_parameters("bollinger_bands", {
            "period": bb_period,
            "std_dev": bb_std
        })
        self.indicators["bollinger"] = BollingerBands(period=20, std_dev=2.0)

        # Create adaptive Stochastic Oscillator
        stoch_bounds = ParameterBounds(min_value=5, max_value=50)
        stoch_k = create_adaptive_parameter(
            name="stoch_k",
            parameter_type=ParameterType.PERIOD,
            base_value=14,
            bounds=stoch_bounds,
            adaptation_strategy=AdaptationStrategy.TREND_STRENGTH
        )

        self.adaptive_manager.register_indicator_parameters("stochastic", {
            "k_period": stoch_k
        })
        self.indicators["stochastic"] = StochasticOscillator(k_period=14, d_period=3)

        print("✓ Adaptive indicators initialized:")
        print("  - RSI with adaptive period")
        print("  - MACD with adaptive fast/slow periods")
        print("  - Bollinger Bands with adaptive period and std dev")
        print("  - Stochastic Oscillator with adaptive K period")
        print()

    async def simulate_market_conditions(self, periods: int = 1000):
        """Simulate changing market conditions."""
        print(f"📊 Simulating {periods} periods of market conditions...")
        print("-" * 50)

        # Generate synthetic market data with changing conditions
        np.random.seed(42)

        conditions = []
        base_volatility = 0.02
        base_trend = 0.0001

        for i in range(periods):
            # Create changing market conditions
            if i < periods // 4:
                # Low volatility, trending market
                volatility = base_volatility * 0.5
                trend_strength = 0.8
                regime = MarketRegime.TRENDING
                risk_level = RiskLevel.LOW
            elif i < periods // 2:
                # High volatility, ranging market
                volatility = base_volatility * 2.0
                trend_strength = 0.2
                regime = MarketRegime.HIGH_VOLATILITY
                risk_level = RiskLevel.HIGH
            elif i < 3 * periods // 4:
                # Moderate volatility, sideways market
                volatility = base_volatility * 1.2
                trend_strength = 0.4
                regime = MarketRegime.SIDEWAYS
                risk_level = RiskLevel.MODERATE
            else:
                # Bear market conditions
                volatility = base_volatility * 1.5
                trend_strength = 0.6
                regime = MarketRegime.BEAR
                risk_level = RiskLevel.HIGH

            condition = type('MarketCondition', (), {
                'volatility': volatility,
                'trend_strength': trend_strength,
                'volume_confirmation': 0.7,
                'market_regime': regime,
                'risk_level': risk_level,
                'timestamp': datetime.now().timestamp() + i
            })()

            conditions.append(condition)

            # Update adaptive manager
            self.adaptive_manager.update_market_condition(condition)

            # Adapt parameters every 10 periods
            if i % 10 == 0:
                await self.adapt_all_indicators()

            # Print progress
            if (i + 1) % 100 == 0:
                print(f"  Processed {i + 1}/{periods} market conditions...")

        print("✓ Market condition simulation completed")
        print()

        return conditions

    async def adapt_all_indicators(self):
        """Adapt parameters for all indicators."""
        for indicator_name in self.indicators.keys():
            try:
                adapted_params = await self.adaptive_manager.adapt_indicator_parameters(
                    indicator_name,
                    strategies=[
                        AdaptationStrategy.VOLATILITY_BASED,
                        AdaptationStrategy.MARKET_REGIME,
                        AdaptationStrategy.TREND_STRENGTH
                    ]
                )

                # Update indicator parameters (in real implementation, this would
                # trigger indicator recalculation with new parameters)
                if adapted_params:
                    self.update_indicator_parameters(indicator_name, adapted_params)

            except Exception as e:
                print(f"Warning: Failed to adapt {indicator_name}: {e}")

    def update_indicator_parameters(self, indicator_name: str, params: Dict[str, float]):
        """Update indicator parameters (simulation only)."""
        # In a real implementation, this would update the actual indicator objects
        # For demo purposes, we just track the parameter changes
        pass

    async def demonstrate_adaptation(self):
        """Demonstrate how parameters adapt to different conditions."""
        print("🎯 Demonstrating Parameter Adaptation")
        print("-" * 50)

        # Test different market conditions
        test_conditions = [
            {
                "name": "Low Volatility Trending",
                "condition": type('MarketCondition', (), {
                    'volatility': 0.01, 'trend_strength': 0.8,
                    'volume_confirmation': 0.8, 'market_regime': MarketRegime.TRENDING,
                    'risk_level': RiskLevel.LOW, 'timestamp': datetime.now().timestamp()
                })()
            },
            {
                "name": "High Volatility Sideways",
                "condition": type('MarketCondition', (), {
                    'volatility': 0.05, 'trend_strength': 0.2,
                    'volume_confirmation': 0.5, 'market_regime': MarketRegime.HIGH_VOLATILITY,
                    'risk_level': RiskLevel.HIGH, 'timestamp': datetime.now().timestamp()
                })()
            },
            {
                "name": "Bear Market",
                "condition": type('MarketCondition', (), {
                    'volatility': 0.04, 'trend_strength': 0.7,
                    'volume_confirmation': 0.6, 'market_regime': MarketRegime.BEAR,
                    'risk_level': RiskLevel.HIGH, 'timestamp': datetime.now().timestamp()
                })()
            }
        ]

        for test_case in test_conditions:
            print(f"\n📈 Testing: {test_case['name']}")

            # Update market condition
            self.adaptive_manager.update_market_condition(test_case['condition'])

            # Show parameter adaptations
            for indicator_name in self.indicators.keys():
                try:
                    adapted_params = await self.adaptive_manager.adapt_indicator_parameters(
                        indicator_name,
                        strategies=[AdaptationStrategy.VOLATILITY_BASED, AdaptationStrategy.MARKET_REGIME]
                    )

                    if adapted_params:
                        print(f"  {indicator_name.upper()}: {adapted_params}")

                        # Show parameter stats
                        stats = self.adaptive_manager.get_parameter_stats(indicator_name)
                        if stats:
                            for param_name, param_stats in stats.items():
                                current = param_stats.get('current_value', 0)
                                base = param_stats.get('base_value', 0)
                                deviation = param_stats.get('deviation', 0)
                                print(".1f")

                except Exception as e:
                    print(f"  {indicator_name.upper()}: Error - {e}")

        print()

    async def show_adaptation_history(self):
        """Show adaptation history for indicators."""
        print("📚 Adaptation History Summary")
        print("-" * 50)

        for indicator_name in self.indicators.keys():
            history = self.adaptive_manager.get_adaptation_history(indicator_name, limit=10)

            if history:
                print(f"\n🔄 {indicator_name.upper()} Adaptations (last 10):")
                for i, record in enumerate(history[-10:], 1):
                    timestamp = datetime.fromtimestamp(record['timestamp'])
                    strategies = record['strategies']
                    adaptations = record['adaptations']
                    print(f"  {i}. {timestamp.strftime('%H:%M:%S')} - {strategies}")
                    print(f"     Parameters: {adaptations}")
            else:
                print(f"\n🔄 {indicator_name.upper()}: No adaptation history")

        print()

    async def run_demo(self):
        """Run the complete adaptive indicators demonstration."""
        print("🚀 Nautilus Trader Engine - Adaptive Indicators Demo")
        print("=" * 60)

        try:
            # Initialize adaptive indicators
            await self.initialize_adaptive_indicators()

            # Simulate market conditions
            await self.simulate_market_conditions(500)  # Shorter simulation for demo

            # Demonstrate adaptation
            await self.demonstrate_adaptation()

            # Show adaptation history
            await self.show_adaptation_history()

            print("✅ Adaptive indicators demo completed successfully!")

        except Exception as e:
            print(f"❌ Error in demo: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Main execution function."""
    demo = AdaptiveIndicatorDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())