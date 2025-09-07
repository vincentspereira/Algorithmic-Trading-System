#!/usr/bin/env python3
"""
Demonstration script for DatabaseIntegrationTester

This script demonstrates the key functionality of the DatabaseIntegrationTester class,
showing how it validates database operations, transaction integrity, connection pooling,
and failover scenarios across multiple database types.
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

# Add the framework directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from database_integration_tester import (
    DatabaseIntegrationTester,
    DatabaseType,
    DatabaseOperationType,
    TestDataType,
    DatabaseTestStatus,
    ConnectionPoolConfig,
    TransactionTestConfig
)


async def main():
    """Demonstrate DatabaseIntegrationTester functionality"""
    print("=" * 80)
    print("DATABASE INTEGRATION TESTER DEMONSTRATION")
    print("=" * 80)
    
    # Initialize DatabaseIntegrationTester
    print("\n1. Initializing DatabaseIntegrationTester...")
    config = {
        'postgres_host': 'localhost',
        'postgres_port': 5432,
        'postgres_db': 'trading_test',
        'postgres_user': 'test_user',
        'postgres_password': 'test_password',
        'mongo_host': 'localhost',
        'mongo_port': 27017,
        'mongo_db': 'trading_test',
        'redis_host': 'localhost',
        'redis_port': 6379,
        'redis_db': 0
    }
    
    tester = DatabaseIntegrationTester(config)
    print(f"   Tester initialized with config for {len(tester.database_configs)} database types")
    print(f"   Test data generators: {len(tester.test_data_generators)}")
    print(f"   Schema managers: {len(tester.schema_managers)}")
    
    # Demonstrate test data generation
    print("\n2. Test Data Generation...")
    
    print("   Generating sample test data for different data types:")
    
    market_data = tester._generate_market_data()
    print(f"   Market Data: {market_data['symbol']} @ ${market_data['price']} (Vol: {market_data['volume']})")
    
    trade_data = tester._generate_trade_data()
    print(f"   Trade Data: {trade_data['side']} {trade_data['quantity']} {trade_data['symbol']} @ ${trade_data['price']}")
    
    portfolio_data = tester._generate_portfolio_data()
    print(f"   Portfolio Data: Account {portfolio_data['account_id']}, Value: ${portfolio_data['total_value']:,.2f}")
    
    user_data = tester._generate_user_data()
    print(f"   User Data: {user_data['username']} ({user_data['email']}) - {user_data['account_type']}")
    
    config_data = tester._generate_configuration_data()
    print(f"   Config Data: {config_data['key']} = {config_data['value']} ({config_data['category']})")
    
    audit_data = tester._generate_audit_data()
    print(f"   Audit Data: {audit_data['action']} on {audit_data['resource']} by {audit_data['user_id']}")
    
    # Register CRUD Tests
    print("\n3. Registering CRUD Integration Tests...")
    
    # SQLite CRUD test
    sqlite_crud_id = tester.register_crud_test(
        "SQLite CRUD Operations",
        DatabaseType.SQLITE,
        TestDataType.MARKET_DATA,
        [
            DatabaseOperationType.CREATE,
            DatabaseOperationType.READ,
            DatabaseOperationType.UPDATE,
            DatabaseOperationType.DELETE,
            DatabaseOperationType.BULK_INSERT
        ],
        {
            'required_operations': ['create', 'read', 'update', 'delete', 'bulk_insert'],
            'performance_thresholds': {
                'create': 50,  # ms
                'read': 25,
                'update': 50,
                'delete': 25,
                'bulk_insert': 200
            }
        }
    )
    print(f"   Registered SQLite CRUD test: {sqlite_crud_id}")
    
    # PostgreSQL CRUD test
    postgres_crud_id = tester.register_crud_test(
        "PostgreSQL CRUD Operations",
        DatabaseType.POSTGRESQL,
        TestDataType.TRADE_DATA,
        [
            DatabaseOperationType.CREATE,
            DatabaseOperationType.READ,
            DatabaseOperationType.UPDATE,
            DatabaseOperationType.DELETE,
            DatabaseOperationType.BULK_INSERT
        ],
        {
            'required_operations': ['create', 'read', 'update', 'delete', 'bulk_insert'],
            'performance_thresholds': {
                'create': 100,  # ms
                'read': 50,
                'update': 100,
                'delete': 50,
                'bulk_insert': 300
            }
        }
    )
    print(f"   Registered PostgreSQL CRUD test: {postgres_crud_id}")
    
    # MongoDB CRUD test
    mongodb_crud_id = tester.register_crud_test(
        "MongoDB CRUD Operations",
        DatabaseType.MONGODB,
        TestDataType.PORTFOLIO_DATA,
        [
            DatabaseOperationType.CREATE,
            DatabaseOperationType.READ,
            DatabaseOperationType.UPDATE,
            DatabaseOperationType.DELETE,
            DatabaseOperationType.BULK_INSERT
        ],
        {
            'required_operations': ['create', 'read', 'update', 'delete', 'bulk_insert'],
            'performance_thresholds': {
                'create': 75,  # ms
                'read': 30,
                'update': 75,
                'delete': 30,
                'bulk_insert': 250
            }
        }
    )
    print(f"   Registered MongoDB CRUD test: {mongodb_crud_id}")
    
    # Redis CRUD test
    redis_crud_id = tester.register_crud_test(
        "Redis CRUD Operations",
        DatabaseType.REDIS,
        TestDataType.USER_DATA,
        [
            DatabaseOperationType.CREATE,
            DatabaseOperationType.READ,
            DatabaseOperationType.UPDATE,
            DatabaseOperationType.DELETE,
            DatabaseOperationType.BULK_INSERT
        ],
        {
            'required_operations': ['create', 'read', 'update', 'delete', 'bulk_insert'],
            'performance_thresholds': {
                'create': 20,  # ms
                'read': 10,
                'update': 20,
                'delete': 10,
                'bulk_insert': 100
            }
        }
    )
    print(f"   Registered Redis CRUD test: {redis_crud_id}")
    
    # Register Transaction Integrity Tests
    print("\n4. Registering Transaction Integrity Tests...")
    
    # PostgreSQL transaction test
    postgres_transaction_config = TransactionTestConfig(
        isolation_level='READ_COMMITTED',
        timeout_seconds=30,
        test_rollback=True,
        test_commit=True,
        test_nested_transactions=True,
        test_concurrent_access=True
    )
    
    postgres_transaction_scenarios = [
        {'name': 'simple_rollback', 'type': 'rollback'},
        {'name': 'simple_commit', 'type': 'commit'},
        {'name': 'nested_transactions', 'type': 'nested'},
        {'name': 'concurrent_access', 'type': 'concurrent'},
        {'name': 'deadlock_prevention', 'type': 'concurrent'}
    ]
    
    postgres_trans_id = tester.register_transaction_integrity_test(
        "PostgreSQL Transaction Integrity",
        DatabaseType.POSTGRESQL,
        postgres_transaction_config,
        postgres_transaction_scenarios
    )
    print(f"   Registered PostgreSQL transaction test: {postgres_trans_id}")
    
    # SQLite transaction test (limited transaction support)
    sqlite_transaction_config = TransactionTestConfig(
        isolation_level='SERIALIZABLE',
        timeout_seconds=15,
        test_rollback=True,
        test_commit=True,
        test_nested_transactions=False,  # SQLite has limited nested transaction support
        test_concurrent_access=False     # SQLite is file-based
    )
    
    sqlite_transaction_scenarios = [
        {'name': 'rollback_test', 'type': 'rollback'},
        {'name': 'commit_test', 'type': 'commit'}
    ]
    
    sqlite_trans_id = tester.register_transaction_integrity_test(
        "SQLite Transaction Integrity",
        DatabaseType.SQLITE,
        sqlite_transaction_config,
        sqlite_transaction_scenarios
    )
    print(f"   Registered SQLite transaction test: {sqlite_trans_id}")
    
    # Register Connection Pool Tests
    print("\n5. Registering Connection Pool Tests...")
    
    # PostgreSQL connection pool test
    postgres_pool_config = ConnectionPoolConfig(
        min_connections=2,
        max_connections=10,
        connection_timeout=30,
        idle_timeout=300,
        retry_attempts=3,
        retry_delay=1.0
    )
    
    postgres_load_scenarios = [
        {
            'name': 'low_load',
            'concurrent_connections': 3,
            'operations_per_connection': 10
        },
        {
            'name': 'medium_load',
            'concurrent_connections': 6,
            'operations_per_connection': 20
        },
        {
            'name': 'high_load',
            'concurrent_connections': 9,
            'operations_per_connection': 30
        },
        {
            'name': 'peak_load',
            'concurrent_connections': 12,  # Exceeds max_connections
            'operations_per_connection': 15
        }
    ]
    
    postgres_pool_id = tester.register_connection_pool_test(
        "PostgreSQL Connection Pool",
        DatabaseType.POSTGRESQL,
        postgres_pool_config,
        postgres_load_scenarios
    )
    print(f"   Registered PostgreSQL connection pool test: {postgres_pool_id}")
    
    # MongoDB connection pool test
    mongodb_pool_config = ConnectionPoolConfig(
        min_connections=1,
        max_connections=8,
        connection_timeout=20,
        idle_timeout=200,
        retry_attempts=2,
        retry_delay=0.5
    )
    
    mongodb_load_scenarios = [
        {
            'name': 'steady_load',
            'concurrent_connections': 4,
            'operations_per_connection': 25
        },
        {
            'name': 'burst_load',
            'concurrent_connections': 7,
            'operations_per_connection': 10
        }
    ]
    
    mongodb_pool_id = tester.register_connection_pool_test(
        "MongoDB Connection Pool",
        DatabaseType.MONGODB,
        mongodb_pool_config,
        mongodb_load_scenarios
    )
    print(f"   Registered MongoDB connection pool test: {mongodb_pool_id}")
    
    # Register Failover Tests
    print("\n6. Registering Database Failover Tests...")
    
    # PostgreSQL failover test
    postgres_failover_scenarios = [
        {'name': 'network_disconnection', 'type': 'network'},
        {'name': 'database_service_crash', 'type': 'service'},
        {'name': 'connection_timeout', 'type': 'timeout'},
        {'name': 'disk_full', 'type': 'storage'},
        {'name': 'memory_exhaustion', 'type': 'resource'}
    ]
    
    postgres_recovery_validation = {
        'max_recovery_time': 30,
        'data_integrity_required': True,
        'automatic_recovery': True,
        'backup_required': True,
        'zero_data_loss': True
    }
    
    postgres_failover_id = tester.register_failover_test(
        "PostgreSQL Failover Recovery",
        DatabaseType.POSTGRESQL,
        postgres_failover_scenarios,
        postgres_recovery_validation
    )
    print(f"   Registered PostgreSQL failover test: {postgres_failover_id}")
    
    # MongoDB failover test
    mongodb_failover_scenarios = [
        {'name': 'replica_set_failure', 'type': 'replica'},
        {'name': 'primary_node_failure', 'type': 'primary'},
        {'name': 'network_partition', 'type': 'network'}
    ]
    
    mongodb_recovery_validation = {
        'max_recovery_time': 20,
        'data_integrity_required': True,
        'automatic_failover': True,
        'replica_consistency': True
    }
    
    mongodb_failover_id = tester.register_failover_test(
        "MongoDB Failover Recovery",
        DatabaseType.MONGODB,
        mongodb_failover_scenarios,
        mongodb_recovery_validation
    )
    print(f"   Registered MongoDB failover test: {mongodb_failover_id}")
    
    # Redis failover test
    redis_failover_scenarios = [
        {'name': 'redis_server_crash', 'type': 'service'},
        {'name': 'memory_overflow', 'type': 'memory'},
        {'name': 'persistence_failure', 'type': 'persistence'}
    ]
    
    redis_recovery_validation = {
        'max_recovery_time': 10,
        'data_integrity_required': False,  # Redis is cache, some data loss acceptable
        'automatic_recovery': True,
        'persistence_recovery': True
    }
    
    redis_failover_id = tester.register_failover_test(
        "Redis Failover Recovery",
        DatabaseType.REDIS,
        redis_failover_scenarios,
        redis_recovery_validation
    )
    print(f"   Registered Redis failover test: {redis_failover_id}")
    
    print(f"\n   Total registered test cases: {len(tester.test_cases)}")
    
    # Execute Individual Test Cases
    print("\n7. Executing Individual Database Test Cases...")
    
    print("\n   Executing SQLite CRUD operations test...")
    sqlite_result = await tester.execute_test_case(sqlite_crud_id)
    print(f"   Result: {sqlite_result.status.value}")
    print(f"   Duration: {sqlite_result.duration:.3f}s")
    print(f"   Operations: {sqlite_result.operation_count}")
    print(f"   Rows Affected: {sqlite_result.rows_affected}")
    print(f"   Transaction Integrity: {sqlite_result.transaction_integrity}")
    if sqlite_result.performance_metrics:
        print(f"   Performance Metrics: {len(sqlite_result.performance_metrics)} operations measured")
    
    print("\n   Executing PostgreSQL transaction integrity test...")
    postgres_trans_result = await tester.execute_test_case(postgres_trans_id)
    print(f"   Result: {postgres_trans_result.status.value}")
    print(f"   Duration: {postgres_trans_result.duration:.3f}s")
    print(f"   Operations: {postgres_trans_result.operation_count}")
    print(f"   Transaction Integrity: {postgres_trans_result.transaction_integrity}")
    
    print("\n   Executing PostgreSQL connection pool test...")
    postgres_pool_result = await tester.execute_test_case(postgres_pool_id)
    print(f"   Result: {postgres_pool_result.status.value}")
    print(f"   Duration: {postgres_pool_result.duration:.3f}s")
    print(f"   Operations: {postgres_pool_result.operation_count}")
    if postgres_pool_result.connection_pool_stats:
        print(f"   Pool Statistics Available: Yes")
    
    print("\n   Executing MongoDB failover test...")
    mongodb_failover_result = await tester.execute_test_case(mongodb_failover_id)
    print(f"   Result: {mongodb_failover_result.status.value}")
    print(f"   Duration: {mongodb_failover_result.duration:.3f}s")
    print(f"   Operations: {mongodb_failover_result.operation_count}")
    if mongodb_failover_result.failover_results:
        print(f"   Failover Results Available: Yes")
    
    # Execute Complete Test Suite
    print("\n8. Executing Complete Database Integration Test Suite...")
    
    suite_result = await tester.execute_test_suite(
        "Comprehensive Database Integration Tests",
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
    
    # Display Database Performance Summary
    if suite_result.database_performance_summary:
        print(f"\n   Database Performance Summary:")
        perf = suite_result.database_performance_summary
        print(f"   Average Test Duration: {perf.get('average_test_duration', 0):.3f}s")
        print(f"   Fastest Operation: {perf.get('min_test_duration', 0):.3f}s")
        print(f"   Slowest Operation: {perf.get('max_test_duration', 0):.3f}s")
        print(f"   Total Execution Time: {perf.get('total_execution_time', 0):.3f}s")
        
        # Show operation performance breakdown
        if 'operation_performance' in perf:
            print(f"   Operation Performance Breakdown:")
            for operation, metrics in perf['operation_performance'].items():
                print(f"     {operation}: avg={metrics['average']:.1f}ms, "
                      f"min={metrics['min']:.1f}ms, max={metrics['max']:.1f}ms")
    
    # Display Transaction Integrity Summary
    if suite_result.transaction_integrity_summary:
        print(f"\n   Transaction Integrity Summary:")
        trans = suite_result.transaction_integrity_summary
        print(f"   Total Transaction Tests: {trans.get('total_transaction_tests', 0)}")
        print(f"   Successful Transactions: {trans.get('successful_transactions', 0)}")
        print(f"   Transaction Success Rate: {trans.get('transaction_success_rate', 0):.1f}%")
        print(f"   Integrity Maintained: {trans.get('integrity_maintained', False)}")
    
    # Display Connection Pool Summary
    if suite_result.connection_pool_summary:
        print(f"\n   Connection Pool Summary:")
        pool = suite_result.connection_pool_summary
        print(f"   Total Pool Tests: {pool.get('total_pool_tests', 0)}")
        print(f"   Successful Pool Tests: {pool.get('successful_pool_tests', 0)}")
        print(f"   Pool Success Rate: {pool.get('pool_success_rate', 0):.1f}%")
        print(f"   Average Pool Utilization: {pool.get('average_pool_utilization', 0):.1f}%")
    
    # Display Failed Tests
    failed_tests = [r for r in suite_result.test_results if r.status == DatabaseTestStatus.FAILED]
    if failed_tests:
        print(f"\n   Failed Tests ({len(failed_tests)}):")
        for result in failed_tests:
            print(f"   ❌ {result.test_case.test_name}")
            print(f"      Database: {result.test_case.database_type.value}")
            print(f"      Operation: {result.test_case.operation_type.value}")
            print(f"      Error: {result.error_message}")
    else:
        print(f"\n   ✅ All database tests passed!")
    
    # Display Recommendations
    if suite_result.recommendations:
        print(f"\n   Recommendations:")
        for i, recommendation in enumerate(suite_result.recommendations, 1):
            print(f"   {i}. {recommendation}")
    
    # Generate Comprehensive Report
    print("\n9. Generating Comprehensive Database Test Report...")
    
    comprehensive_report = tester.generate_comprehensive_report(suite_result)
    
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
    
    # Demonstrate Database Type Analysis
    print("\n10. Database Type Performance Analysis...")
    
    # Group results by database type
    db_type_results = {}
    for result in suite_result.test_results:
        db_type = result.test_case.database_type.value
        if db_type not in db_type_results:
            db_type_results[db_type] = {'total': 0, 'passed': 0, 'avg_duration': 0}
        
        db_type_results[db_type]['total'] += 1
        if result.status == DatabaseTestStatus.PASSED:
            db_type_results[db_type]['passed'] += 1
        db_type_results[db_type]['avg_duration'] += result.duration
    
    print(f"   Database Type Performance Comparison:")
    for db_type, stats in db_type_results.items():
        success_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
        avg_duration = stats['avg_duration'] / stats['total'] if stats['total'] > 0 else 0
        print(f"   {db_type.upper()}:")
        print(f"     Tests: {stats['passed']}/{stats['total']} ({success_rate:.1f}% success)")
        print(f"     Avg Duration: {avg_duration:.3f}s")
    
    # Operation Type Analysis
    print(f"\n   Operation Type Performance Analysis:")
    
    operation_results = {}
    for result in suite_result.test_results:
        op_type = result.test_case.operation_type.value
        if op_type not in operation_results:
            operation_results[op_type] = {'total': 0, 'passed': 0, 'avg_duration': 0}
        
        operation_results[op_type]['total'] += 1
        if result.status == DatabaseTestStatus.PASSED:
            operation_results[op_type]['passed'] += 1
        operation_results[op_type]['avg_duration'] += result.duration
    
    for op_type, stats in operation_results.items():
        success_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
        avg_duration = stats['avg_duration'] / stats['total'] if stats['total'] > 0 else 0
        print(f"   {op_type.upper()}: {stats['passed']}/{stats['total']} "
              f"({success_rate:.1f}% success, {avg_duration:.3f}s avg)")
    
    # Final Summary
    print("\n" + "=" * 80)
    print("DATABASE INTEGRATION TESTER DEMONSTRATION SUMMARY")
    print("=" * 80)
    
    print(f"Test Cases Registered: {len(tester.test_cases)}")
    print(f"Database Types Tested: {len(db_type_results)}")
    print(f"Operation Types Tested: {len(operation_results)}")
    print(f"Total Tests Run: {suite_result.total_tests}")
    print(f"Overall Pass Rate: {suite_result.pass_rate:.1f}%")
    print(f"Total Execution Time: {suite_result.total_duration:.2f}s")
    
    if suite_result.pass_rate == 100.0:
        print("\n🎉 All database integration tests passed! Database layer is validated.")
    elif suite_result.pass_rate >= 80.0:
        print(f"\n✅ Most database tests passed ({suite_result.pass_rate:.1f}%). Minor issues to address.")
    else:
        print(f"\n⚠️  Database test pass rate is low ({suite_result.pass_rate:.1f}%). Significant issues need attention.")
    
    print("\nDatabaseIntegrationTester demonstration completed!")
    print("\nKey Features Demonstrated:")
    print("  ✅ CRUD operations testing across multiple database types")
    print("  ✅ Transaction integrity validation with rollback/commit testing")
    print("  ✅ Connection pooling performance and load testing")
    print("  ✅ Database failover and recovery scenario testing")
    print("  ✅ Comprehensive performance metrics and timing analysis")
    print("  ✅ Multi-database type support (SQLite, PostgreSQL, MongoDB, Redis)")
    print("  ✅ Test data generation for various data types")
    print("  ✅ Schema management and database setup/teardown")
    print("  ✅ Detailed reporting and recommendations")
    print("  ✅ Parallel and sequential test execution")


if __name__ == "__main__":
    asyncio.run(main())