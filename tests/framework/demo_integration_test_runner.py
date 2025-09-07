#!/usr/bin/env python3
"""
Demonstration script for IntegrationTestRunner

This script demonstrates the key functionality of the IntegrationTestRunner class,
showing how it orchestrates integration testing across multiple system components,
validates data flows, module interactions, and system boundaries.
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

# Add the framework directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from integration_test_runner import (
    IntegrationTestRunner,
    IntegrationTestCase,
    IntegrationTestType,
    IntegrationPointType,
    IntegrationTestStatus
)


# Sample modules and functions for demonstration
class DataHandler:
    """Sample data handler module"""
    
    @staticmethod
    async def process_market_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming market data"""
        await asyncio.sleep(0.1)  # Simulate processing time
        
        processed_data = data.copy()
        processed_data['processed'] = True
        processed_data['timestamp'] = time.time()
        processed_data['volume_weighted_price'] = (
            processed_data.get('price', 0) * processed_data.get('volume', 1)
        )
        
        return processed_data
    
    @staticmethod
    async def validate_data_integrity(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data integrity"""
        await asyncio.sleep(0.05)
        
        validated_data = data.copy()
        validated_data['validated'] = True
        validated_data['integrity_score'] = 0.95
        
        # Check for required fields
        required_fields = ['symbol', 'price', 'volume']
        validated_data['missing_fields'] = [
            field for field in required_fields if field not in data
        ]
        
        return validated_data


class TradingStrategy:
    """Sample trading strategy module"""
    
    @staticmethod
    async def analyze_signal(data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze trading signal from market data"""
        await asyncio.sleep(0.2)  # Simulate analysis time
        
        signal_data = {
            'signal_type': 'BUY' if data.get('price', 0) < 100 else 'SELL',
            'confidence': 0.85,
            'recommended_quantity': min(data.get('volume', 0) * 0.1, 1000),
            'analysis_timestamp': time.time(),
            'source_data': data
        }
        
        return signal_data
    
    @staticmethod
    async def calculate_position_size(signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate optimal position size"""
        await asyncio.sleep(0.1)
        
        position_data = signal_data.copy()
        position_data['position_size'] = min(
            signal_data.get('recommended_quantity', 0),
            500  # Max position size
        )
        position_data['risk_adjusted'] = True
        
        return position_data


class RiskManager:
    """Sample risk manager module"""
    
    @staticmethod
    async def assess_risk(position_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess risk for the proposed position"""
        await asyncio.sleep(0.15)
        
        risk_assessment = {
            'risk_score': 0.3,  # Low risk
            'max_loss': position_data.get('position_size', 0) * 0.05,
            'risk_approved': True,
            'assessment_timestamp': time.time(),
            'position_data': position_data
        }
        
        return risk_assessment
    
    @staticmethod
    async def apply_risk_limits(risk_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply risk limits to the position"""
        await asyncio.sleep(0.05)
        
        final_data = risk_data.copy()
        final_data['final_approval'] = risk_data.get('risk_approved', False)
        final_data['stop_loss'] = risk_data.get('max_loss', 0) * 1.5
        final_data['take_profit'] = risk_data.get('max_loss', 0) * 3.0
        
        return final_data


async def main():
    """Demonstrate IntegrationTestRunner functionality"""
    print("=" * 80)
    print("INTEGRATION TEST RUNNER DEMONSTRATION")
    print("=" * 80)
    
    # Initialize IntegrationTestRunner
    print("\n1. Initializing IntegrationTestRunner...")
    config = {
        'test_database_path': ':memory:',
        'test_redis_host': 'localhost',
        'test_redis_port': 6379,
        'default_timeout': 30
    }
    
    runner = IntegrationTestRunner(config)
    print(f"   Runner initialized with config: {config}")
    print(f"   Test cases registered: {len(runner.test_cases)}")
    
    # Register Data Flow Tests
    print("\n2. Registering Data Flow Integration Tests...")
    
    # Data Handler to Strategy flow
    data_handler_to_strategy_id = runner.register_data_flow_test(
        "Data Handler to Strategy Flow",
        "DataHandler",
        "TradingStrategy",
        [
            DataHandler.process_market_data,
            DataHandler.validate_data_integrity,
            TradingStrategy.analyze_signal
        ],
        {
            'required_fields': ['signal_type', 'confidence', 'validated'],
            'expected_types': {
                'signal_type': str,
                'confidence': float,
                'validated': bool
            },
            'value_ranges': {
                'confidence': (0.0, 1.0)
            },
            'sample_data': {
                'symbol': 'AAPL',
                'price': 95.50,
                'volume': 1000
            }
        }
    )
    print(f"   Registered data flow test: {data_handler_to_strategy_id}")
    
    # Strategy to Risk Manager flow
    strategy_to_risk_id = runner.register_data_flow_test(
        "Strategy to Risk Manager Flow",
        "TradingStrategy",
        "RiskManager",
        [
            TradingStrategy.calculate_position_size,
            RiskManager.assess_risk,
            RiskManager.apply_risk_limits
        ],
        {
            'required_fields': ['final_approval', 'risk_score', 'stop_loss'],
            'expected_types': {
                'final_approval': bool,
                'risk_score': float,
                'stop_loss': (int, float)
            },
            'value_ranges': {
                'risk_score': (0.0, 1.0)
            },
            'sample_data': {
                'signal_type': 'BUY',
                'confidence': 0.85,
                'recommended_quantity': 100
            }
        }
    )
    print(f"   Registered data flow test: {strategy_to_risk_id}")
    
    # Register Message Passing Tests
    print("\n3. Registering Message Passing Integration Tests...")
    
    order_message_id = runner.register_message_passing_test(
        "Order Message Passing",
        "TradingStrategy",
        "OrderExecutor",
        "order_request",
        {
            'order_type': 'MARKET',
            'symbol': 'AAPL',
            'quantity': 100,
            'side': 'BUY',
            'timestamp': time.time()
        }
    )
    print(f"   Registered message passing test: {order_message_id}")
    
    risk_alert_id = runner.register_message_passing_test(
        "Risk Alert Message",
        "RiskManager",
        "AlertSystem",
        "risk_alert",
        {
            'alert_type': 'POSITION_LIMIT',
            'severity': 'HIGH',
            'message': 'Position limit exceeded',
            'timestamp': time.time()
        }
    )
    print(f"   Registered message passing test: {risk_alert_id}")
    
    # Register Database Integration Tests
    print("\n4. Registering Database Integration Tests...")
    
    portfolio_db_id = runner.register_database_integration_test(
        "Portfolio Database Integration",
        "PortfolioManager",
        ['create', 'read', 'update', 'delete'],
        {
            'portfolio_id': 'TEST_001',
            'account_id': 'ACC_12345',
            'positions': [
                {'symbol': 'AAPL', 'quantity': 100, 'avg_price': 95.50},
                {'symbol': 'GOOGL', 'quantity': 50, 'avg_price': 2800.00}
            ],
            'cash_balance': 10000.00,
            'total_value': 25000.00
        }
    )
    print(f"   Registered database integration test: {portfolio_db_id}")
    
    trade_history_db_id = runner.register_database_integration_test(
        "Trade History Database Integration",
        "TradeHistoryManager",
        ['create', 'read'],
        {
            'trade_id': 'TRD_001',
            'symbol': 'AAPL',
            'quantity': 100,
            'price': 95.50,
            'side': 'BUY',
            'timestamp': time.time(),
            'status': 'FILLED'
        }
    )
    print(f"   Registered database integration test: {trade_history_db_id}")
    
    # Register API Integration Tests
    print("\n5. Registering API Integration Tests...")
    
    market_data_api_id = runner.register_api_integration_test(
        "Market Data API Integration",
        "MarketDataClient",
        ['/api/v1/quotes', '/api/v1/trades'],
        [
            {
                'method': 'GET',
                'params': {'symbol': 'AAPL', 'limit': 100}
            },
            {
                'method': 'GET',
                'params': {'symbol': 'AAPL', 'date': '2024-01-01'}
            }
        ]
    )
    print(f"   Registered API integration test: {market_data_api_id}")
    
    broker_api_id = runner.register_api_integration_test(
        "Broker API Integration",
        "BrokerClient",
        ['/api/orders', '/api/positions'],
        [
            {
                'method': 'POST',
                'data': {
                    'symbol': 'AAPL',
                    'quantity': 100,
                    'side': 'BUY',
                    'order_type': 'MARKET'
                }
            },
            {
                'method': 'GET',
                'params': {'account_id': 'ACC_12345'}
            }
        ]
    )
    print(f"   Registered API integration test: {broker_api_id}")
    
    # Register Failure Recovery Tests
    print("\n6. Registering Failure Recovery Tests...")
    
    network_failure_id = runner.register_failure_recovery_test(
        "Network Failure Recovery",
        ["MarketDataClient", "BrokerClient", "RiskManager"],
        [
            {
                'name': 'market_data_disconnect',
                'type': 'network',
                'affected_modules': ['MarketDataClient']
            },
            {
                'name': 'broker_api_timeout',
                'type': 'timeout',
                'affected_modules': ['BrokerClient']
            }
        ],
        {
            'max_recovery_time': 30,
            'data_integrity_required': True,
            'failover_required': True
        }
    )
    print(f"   Registered failure recovery test: {network_failure_id}")
    
    database_failure_id = runner.register_failure_recovery_test(
        "Database Failure Recovery",
        ["PortfolioManager", "TradeHistoryManager"],
        [
            {
                'name': 'database_connection_lost',
                'type': 'database',
                'affected_modules': ['PortfolioManager', 'TradeHistoryManager']
            }
        ],
        {
            'max_recovery_time': 15,
            'data_integrity_required': True,
            'backup_required': True
        }
    )
    print(f"   Registered failure recovery test: {database_failure_id}")
    
    print(f"\n   Total registered test cases: {len(runner.test_cases)}")
    
    # Execute Individual Test Cases
    print("\n7. Executing Individual Test Cases...")
    
    print("\n   Executing Data Handler to Strategy Flow test...")
    data_flow_result = await runner.execute_test_case(data_handler_to_strategy_id)
    print(f"   Result: {data_flow_result.status.value}")
    print(f"   Duration: {data_flow_result.duration:.3f}s")
    if data_flow_result.data_flow_validation:
        validation = data_flow_result.data_flow_validation
        print(f"   Validation Passed: {validation.get('validation_passed', False)}")
        print(f"   Transformations: {len(validation.get('data_transformations', []))}")
    
    print("\n   Executing Order Message Passing test...")
    message_result = await runner.execute_test_case(order_message_id)
    print(f"   Result: {message_result.status.value}")
    print(f"   Duration: {message_result.duration:.3f}s")
    if message_result.message_passing_validation:
        validation = message_result.message_passing_validation
        print(f"   Delivery Confirmed: {validation.get('delivery_confirmed', False)}")
        print(f"   Processing Confirmed: {validation.get('processing_confirmed', False)}")
        print(f"   Latency: {validation.get('latency_ms', 0):.1f}ms")
    
    print("\n   Executing Portfolio Database Integration test...")
    db_result = await runner.execute_test_case(portfolio_db_id)
    print(f"   Result: {db_result.status.value}")
    print(f"   Duration: {db_result.duration:.3f}s")
    if db_result.integration_point_results:
        results = db_result.integration_point_results
        successful_ops = sum(1 for r in results.values() if r.get('success', False))
        print(f"   Successful Operations: {successful_ops}/{len(results)}")
    
    # Execute Test Suite
    print("\n8. Executing Complete Integration Test Suite...")
    
    suite_result = await runner.execute_test_suite(
        "Algorithmic Trading System Integration Tests",
        parallel_execution=True
    )
    
    print(f"\n   Suite Execution Summary:")
    print(f"   Suite Name: {suite_result.suite_name}")
    print(f"   Total Duration: {suite_result.total_duration:.2f}s")
    print(f"   Total Tests: {suite_result.total_tests}")
    print(f"   Passed: {suite_result.passed_tests}")
    print(f"   Failed: {suite_result.failed_tests}")
    print(f"   Errors: {suite_result.error_tests}")
    print(f"   Timeouts: {suite_result.timeout_tests}")
    print(f"   Pass Rate: {suite_result.pass_rate:.1f}%")
    
    # Display Data Flow Summary
    if suite_result.data_flow_summary:
        print(f"\n   Data Flow Summary:")
        summary = suite_result.data_flow_summary
        print(f"   Total Data Flows: {summary.get('total_data_flows', 0)}")
        print(f"   Successful Flows: {summary.get('successful_flows', 0)}")
        print(f"   Flow Success Rate: {summary.get('success_rate', 0):.1f}%")
        print(f"   Avg Transformation Time: {summary.get('average_transformation_time', 0):.3f}s")
    
    # Display Integration Point Summary
    if suite_result.integration_point_summary:
        print(f"\n   Integration Point Summary:")
        for point_type, stats in suite_result.integration_point_summary.items():
            success_rate = (stats['passed_tests'] / stats['total_tests'] * 100) if stats['total_tests'] > 0 else 0
            print(f"   {point_type.upper()}: {stats['passed_tests']}/{stats['total_tests']} ({success_rate:.1f}%)")
    
    # Display Performance Summary
    if suite_result.performance_summary:
        print(f"\n   Performance Summary:")
        perf = suite_result.performance_summary
        print(f"   Average Test Duration: {perf.get('average_test_duration', 0):.3f}s")
        print(f"   Fastest Test: {perf.get('min_test_duration', 0):.3f}s")
        print(f"   Slowest Test: {perf.get('max_test_duration', 0):.3f}s")
    
    # Display Failed Tests
    failed_tests = [r for r in suite_result.test_results if r.status == IntegrationTestStatus.FAILED]
    if failed_tests:
        print(f"\n   Failed Tests ({len(failed_tests)}):")
        for result in failed_tests:
            print(f"   ❌ {result.test_case.test_name}")
            print(f"      Error: {result.error_message}")
            print(f"      Modules: {', '.join(result.test_case.modules_under_test)}")
    else:
        print(f"\n   ✅ All tests passed!")
    
    # Display Recommendations
    if suite_result.recommendations:
        print(f"\n   Recommendations:")
        for i, recommendation in enumerate(suite_result.recommendations, 1):
            print(f"   {i}. {recommendation}")
    
    # Generate Comprehensive Report
    print("\n9. Generating Comprehensive Report...")
    
    comprehensive_report = runner.generate_comprehensive_report(suite_result)
    
    print("   Report generated successfully!")
    print(f"   Report length: {len(comprehensive_report)} characters")
    
    # Ask user if they want to see the full report
    show_full = input("\n   Show full comprehensive report? (y/N): ").lower().strip()
    if show_full == 'y':
        print("\n" + "=" * 80)
        print(comprehensive_report)
        print("=" * 80)
    else:
        # Show just the summary section
        report_lines = comprehensive_report.split('\n')
        summary_start = next((i for i, line in enumerate(report_lines) if 'SUMMARY' in line), 0)
        summary_end = next((i for i, line in enumerate(report_lines[summary_start:]) if line.startswith('-') and i > 5), 15) + summary_start
        
        print("\n   Report Summary:")
        for line in report_lines[summary_start:summary_end]:
            print(f"   {line}")
    
    # Demonstrate Test Statistics
    print("\n10. Integration Test Statistics...")
    
    # Calculate overall statistics
    total_execution_time = sum(r.duration for r in suite_result.test_results)
    avg_execution_time = total_execution_time / len(suite_result.test_results) if suite_result.test_results else 0
    
    test_types = {}
    for result in suite_result.test_results:
        test_type = result.test_case.test_type.value
        if test_type not in test_types:
            test_types[test_type] = {'total': 0, 'passed': 0, 'failed': 0}
        
        test_types[test_type]['total'] += 1
        if result.status == IntegrationTestStatus.PASSED:
            test_types[test_type]['passed'] += 1
        else:
            test_types[test_type]['failed'] += 1
    
    print(f"   Overall Statistics:")
    print(f"   Total Execution Time: {total_execution_time:.2f}s")
    print(f"   Average Test Duration: {avg_execution_time:.3f}s")
    print(f"   Test Types Covered: {len(test_types)}")
    
    print(f"\n   Test Type Breakdown:")
    for test_type, stats in test_types.items():
        success_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"   {test_type.upper()}: {stats['passed']}/{stats['total']} ({success_rate:.1f}%)")
    
    # Integration Points Coverage
    integration_points = set()
    for result in suite_result.test_results:
        integration_points.update(point.value for point in result.test_case.integration_points)
    
    print(f"\n   Integration Points Tested: {len(integration_points)}")
    for point in sorted(integration_points):
        print(f"   - {point.upper()}")
    
    # Modules Coverage
    modules_tested = set()
    for result in suite_result.test_results:
        modules_tested.update(result.test_case.modules_under_test)
    
    print(f"\n   Modules Under Test: {len(modules_tested)}")
    for module in sorted(modules_tested):
        print(f"   - {module}")
    
    # Final Summary
    print("\n" + "=" * 80)
    print("INTEGRATION TEST RUNNER DEMONSTRATION SUMMARY")
    print("=" * 80)
    
    print(f"Test Cases Registered: {len(runner.test_cases)}")
    print(f"Test Suite Executed: {suite_result.suite_name}")
    print(f"Total Tests Run: {suite_result.total_tests}")
    print(f"Overall Pass Rate: {suite_result.pass_rate:.1f}%")
    print(f"Total Execution Time: {suite_result.total_duration:.2f}s")
    
    if suite_result.pass_rate == 100.0:
        print("\n🎉 All integration tests passed! System integration is validated.")
    elif suite_result.pass_rate >= 80.0:
        print(f"\n✅ Most integration tests passed ({suite_result.pass_rate:.1f}%). Minor issues to address.")
    else:
        print(f"\n⚠️  Integration test pass rate is low ({suite_result.pass_rate:.1f}%). Significant issues need attention.")
    
    print("\nIntegrationTestRunner demonstration completed!")
    print("\nKey Features Demonstrated:")
    print("  ✅ Data flow integration testing with transformation chains")
    print("  ✅ Message passing validation between modules")
    print("  ✅ Database integration testing with CRUD operations")
    print("  ✅ API integration testing with multiple endpoints")
    print("  ✅ Failure recovery testing with various scenarios")
    print("  ✅ Comprehensive test suite execution (parallel and sequential)")
    print("  ✅ Detailed performance metrics and timing analysis")
    print("  ✅ Integration point coverage analysis")
    print("  ✅ Module boundary validation")
    print("  ✅ Comprehensive reporting and recommendations")


if __name__ == "__main__":
    asyncio.run(main())