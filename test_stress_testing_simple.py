#!/usr/bin/env python3
"""
Simple test for Stress Testing Framework
"""

import asyncio
import numpy as np
import sys
import os
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.abspath('.'))


async def test_stress_testing_framework():
    """Test basic stress testing functionality"""
    print("Testing Stress Testing Framework...")
    
    try:
        # Import the stress testing components
        from nautilus_trader_engine.risk.stress_testing import (
            StressTestingFramework, StressTestType,
            StressShock, StressScenarioDefinition, RiskFactor,
            create_stress_shock, create_stress_scenario
        )
        print("✓ Successfully imported stress testing classes")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return
    
    # Initialize stress testing framework
    try:
        framework = StressTestingFramework(enable_real_time=False)
        await framework.start()
        print("✓ Stress testing framework started successfully")
    except Exception as e:
        print(f"❌ Failed to start stress testing framework: {e}")
        return
    
    try:
        # Create sample portfolio positions
        class MockPosition:
            def __init__(self, symbol, current_price, quantity, sector="Unknown"):
                self.symbol = symbol
                self.current_price = current_price
                self.quantity = quantity
                self.market_value = current_price * quantity
                self.sector = sector
                self.volatility = 0.20  # 20% volatility
                self.returns = np.random.normal(0, 0.02, 252)  # Daily returns
        
        positions = [
            MockPosition("AAPL", 150.0, 100, "Technology"),
            MockPosition("MSFT", 300.0, 50, "Technology"),
            MockPosition("JPM", 140.0, 75, "Financial"),
            MockPosition("JNJ", 160.0, 60, "Healthcare"),
            MockPosition("XOM", 80.0, 125, "Energy")
        ]
        
        portfolio_value = sum(pos.market_value for pos in positions)
        print(f"Created portfolio with {len(positions)} positions, total value: ${portfolio_value:,.2f}")
        
        # Test 1: Scenario-based stress testing
        print("\\n=== Scenario-Based Stress Testing ===")
        
        # Test predefined scenarios
        predefined_scenarios = ["financial_crisis_2008", "covid_19_pandemic", "interest_rate_shock"]
        
        for scenario_name in predefined_scenarios:
            if scenario_name in framework.predefined_scenarios:
                scenario = framework.predefined_scenarios[scenario_name]
                result = await framework._run_single_stress_test(
                    positions, scenario, StressTestType.SCENARIO_BASED, "test_portfolio"
                )
                
                print(f"✓ {scenario_name}:")
                print(f"  Portfolio Loss: {result.relative_loss:.2%}")
                print(f"  Absolute Loss: ${result.absolute_loss:,.2f}")
                print(f"  Recovery Time: {result.recovery_time_estimate} days")
        
        # Test 2: Custom scenario creation
        print("\\n=== Custom Scenario Testing ===")
        
        custom_shocks = [
            create_stress_shock(RiskFactor.EQUITY_MARKET, "relative", -0.25, "25% equity decline"),
            create_stress_shock(RiskFactor.VOLATILITY, "relative", 2.0, "Volatility doubling"),
            create_stress_shock(RiskFactor.LIQUIDITY, "relative", 0.20, "20% liquidity impact")
        ]
        
        custom_scenario = create_stress_scenario(
            "Custom Market Crash",
            "Custom severe market stress scenario",
            custom_shocks,
            "high"
        )
        
        custom_result = await framework._run_single_stress_test(
            positions, custom_scenario, StressTestType.SCENARIO_BASED, "test_portfolio"
        )
        
        print(f"✓ Custom scenario completed:")
        print(f"  Portfolio Loss: {custom_result.relative_loss:.2%}")
        print(f"  Absolute Loss: ${custom_result.absolute_loss:,.2f}")
        print(f"  Asset Impacts: {len(custom_result.asset_impacts)} assets affected")
        
        # Test 3: Historical stress testing
        print("\\n=== Historical Stress Testing ===")
        
        historical_scenario = framework.predefined_scenarios["financial_crisis_2008"]
        historical_result = await framework._run_single_stress_test(
            positions, historical_scenario, StressTestType.HISTORICAL, "test_portfolio"
        )
        
        print(f"✓ Historical stress test completed:")
        print(f"  Portfolio Loss: {historical_result.relative_loss:.2%}")
        print(f"  Stressed VaR: {historical_result.stressed_var:.2%}" if historical_result.stressed_var else "  Stressed VaR: N/A")
        print(f"  Max Drawdown: {historical_result.stressed_max_drawdown:.2%}" if historical_result.stressed_max_drawdown else "  Max Drawdown: N/A")
        
        # Test 4: Monte Carlo stress testing
        print("\\n=== Monte Carlo Stress Testing ===")
        
        # Create correlation matrix for Monte Carlo
        n_assets = len(positions)
        correlation_matrix = np.eye(n_assets)
        # Add some correlation between tech stocks
        correlation_matrix[0, 1] = correlation_matrix[1, 0] = 0.6  # AAPL-MSFT correlation
        
        mc_result = await framework._run_single_stress_test(
            positions, custom_scenario, StressTestType.MONTE_CARLO, "test_portfolio"
        )
        
        print(f"✓ Monte Carlo stress test completed:")
        print(f"  Portfolio Loss: {mc_result.relative_loss:.2%}")
        print(f"  Stressed VaR: {mc_result.stressed_var:.2%}" if mc_result.stressed_var else "  Stressed VaR: N/A")
        print(f"  Expected Shortfall: {mc_result.stressed_expected_shortfall:.2%}" if mc_result.stressed_expected_shortfall else "  Expected Shortfall: N/A")
        
        # Test 5: Comprehensive stress test suite
        print("\\n=== Comprehensive Stress Test Suite ===")
        
        test_suite = await framework.run_stress_test_suite(
            "comprehensive_test_portfolio",
            positions,
            scenarios=list(framework.predefined_scenarios.values())[:3],  # Test first 3 scenarios
            test_types=[StressTestType.SCENARIO_BASED, StressTestType.HISTORICAL]
        )
        
        print(f"✓ Comprehensive stress test suite completed:")
        print(f"  Total scenarios tested: {len(test_suite.scenario_results)}")
        print(f"  Worst case loss: {test_suite.worst_case_loss:.2%}")
        print(f"  Worst case scenario: {test_suite.worst_case_scenario}")
        print(f"  Average loss: {test_suite.average_loss:.2%}")
        print(f"  Systemic risk score: {test_suite.systemic_risk_score:.3f}")
        print(f"  Diversification ratio: {test_suite.diversification_ratio:.3f}")
        print(f"  Tail risk scenarios: {len(test_suite.tail_risk_scenarios)}")
        
        # Test 6: Stress test reporting
        print("\\n=== Stress Test Reporting ===")
        
        report = framework.generate_stress_test_report("comprehensive_test_portfolio")
        
        print(f"✓ Generated comprehensive stress test report:")
        print(f"  Portfolio ID: {report['portfolio_id']}")
        print(f"  Test Date: {report['test_date']}")
        print(f"  Base Portfolio Value: ${report['base_portfolio_value']:,.2f}")
        print(f"  Worst Case Loss: {report['summary']['worst_case_loss']:.2%}")
        print(f"  Worst Case Scenario: {report['summary']['worst_case_scenario']}")
        print(f"  Scenario Results: {len(report['scenario_results'])} scenarios")
        
        # Test 7: Framework metrics
        print("\\n=== Framework Metrics ===")
        
        metrics = framework.get_metrics()
        print(f"✓ Framework metrics:")
        print(f"  Tests completed: {metrics['tests_completed']}")
        print(f"  Tests failed: {metrics['tests_failed']}")
        print(f"  Active portfolios: {metrics['active_portfolios']}")
        print(f"  Average test time: {metrics['avg_test_time_ms']:.2f}ms")
        
        # Test 8: Stress test results retrieval
        print("\\n=== Results Retrieval ===")
        
        stored_results = framework.get_stress_test_results("comprehensive_test_portfolio")
        if stored_results:
            print(f"✓ Retrieved stored results:")
            print(f"  Portfolio ID: {stored_results.portfolio_id}")
            print(f"  Number of scenario results: {len(stored_results.scenario_results)}")
            print(f"  Test date: {stored_results.test_date}")
        else:
            print("❌ No stored results found")
        
        print("\\n✅ Stress Testing Framework test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        try:
            await framework.stop()
            print("✓ Stress testing framework stopped")
        except Exception as e:
            print(f"❌ Failed to stop stress testing framework: {e}")


async def test_convenience_functions():
    """Test convenience functions"""
    print("\\n=== Testing Convenience Functions ===")
    
    try:
        from nautilus_trader_engine.risk.stress_testing import (
            run_stress_test, create_stress_shock, create_stress_scenario,
            RiskFactor, StressTestType
        )
        
        # Create sample position
        class MockPosition:
            def __init__(self, symbol, current_price, quantity):
                self.symbol = symbol
                self.current_price = current_price
                self.quantity = quantity
                self.market_value = current_price * quantity
                self.sector = "Technology"
                self.volatility = 0.20
                self.returns = np.random.normal(0, 0.02, 252)
        
        positions = [MockPosition("AAPL", 150.0, 100)]
        
        # Test convenience function for creating stress shocks
        shock = create_stress_shock(
            RiskFactor.EQUITY_MARKET, 
            "relative", 
            -0.30, 
            "30% equity market decline"
        )
        
        print(f"✓ Created stress shock: {shock.description}")
        print(f"  Factor: {shock.factor.value}")
        print(f"  Magnitude: {shock.magnitude:.1%}")
        
        # Test convenience function for creating scenarios
        scenario = create_stress_scenario(
            "Test Scenario",
            "Simple test scenario",
            [shock],
            "medium"
        )
        
        print(f"✓ Created stress scenario: {scenario.name}")
        print(f"  Description: {scenario.description}")
        print(f"  Number of shocks: {len(scenario.shocks)}")
        print(f"  Severity: {scenario.severity}")
        
        print("✅ Convenience functions test completed successfully!")
        
    except Exception as e:
        print(f"❌ Convenience functions test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the tests
    asyncio.run(test_stress_testing_framework())
    asyncio.run(test_convenience_functions())