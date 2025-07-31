#!/usr/bin/env python3
"""
Comprehensive test for GraphQL API functionality with detailed progress tracking
"""
import sys
import time
from datetime import datetime

def print_status(message, status="INFO"):
    """Print status with timestamp and formatting"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    status_icons = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "ERROR": "❌",
        "WARNING": "⚠️",
        "PROGRESS": "🔄"
    }
    icon = status_icons.get(status, "📋")
    print(f"[{timestamp}] {icon} {message}")
    sys.stdout.flush()

def progress_bar(current, total, width=30):
    """Create a simple progress bar"""
    filled = int(width * current / total)
    bar = "█" * filled + "░" * (width - filled)
    percent = int(100 * current / total)
    return f"[{bar}] {percent}%"

def test_graphql_imports():
    """Test GraphQL imports with detailed progress"""
    print_status("Starting GraphQL imports test...", "PROGRESS")
    
    try:
        print_status("Importing GraphQL API module...", "PROGRESS")
        from nautilus_trader_engine.api.graphql_api import create_graphql_api, GRAPHQL_AVAILABLE
        print_status(f"GraphQL Available: {GRAPHQL_AVAILABLE}", "INFO")
        
        if not GRAPHQL_AVAILABLE:
            print_status("GraphQL dependencies not available!", "ERROR")
            return False
        
        print_status("GraphQL imports successful!", "SUCCESS")
        return True
        
    except Exception as e:
        print_status(f"Import error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False

def test_graphql_api_creation():
    """Test GraphQL API creation with progress tracking"""
    print_status("Testing GraphQL API creation...", "PROGRESS")
    
    try:
        print_status("Step 1/3: Importing API creator...", "PROGRESS")
        from nautilus_trader_engine.api.graphql_api import create_graphql_api
        
        print_status("Step 2/3: Creating API instance...", "PROGRESS")
        api = create_graphql_api()
        
        print_status("Step 3/3: Verifying schema...", "PROGRESS")
        schema = api.schema
        
        if schema is None:
            print_status("Schema is None!", "ERROR")
            return False
        
        print_status("GraphQL API creation successful!", "SUCCESS")
        return True, api
        
    except Exception as e:
        print_status(f"API creation error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False, None

def test_graphql_queries():
    """Test GraphQL queries with detailed progress"""
    print_status("Testing GraphQL queries...", "PROGRESS")
    
    try:
        success, api = test_graphql_api_creation()
        if not success:
            return False
        
        schema = api.schema
        queries_to_test = [
            ("Schema Introspection", "{ __schema { types { name } } }"),
            ("Orders Query", """
                query {
                    orders(limit: 3) {
                        id
                        symbol
                        side
                        quantity
                        status
                    }
                }
            """),
            ("Portfolio Query", """
                query {
                    portfolio {
                        totalValue
                        cashBalance
                        totalPnl
                    }
                }
            """),
            ("Market Data Query", """
                query {
                    marketData(symbol: "AAPL") {
                        symbol
                        lastPrice
                        change
                        changePercent
                    }
                }
            """)
        ]
        
        total_queries = len(queries_to_test)
        successful_queries = 0
        
        for i, (query_name, query) in enumerate(queries_to_test, 1):
            print_status(f"Testing {query_name} ({i}/{total_queries})...", "PROGRESS")
            print(f"    {progress_bar(i-1, total_queries)}")
            
            try:
                result = schema.execute(query)
                
                if result.errors:
                    print_status(f"{query_name} has errors: {result.errors}", "ERROR")
                    continue
                
                if result.data is None:
                    print_status(f"{query_name} returned no data", "WARNING")
                    continue
                
                print_status(f"{query_name} successful!", "SUCCESS")
                
                # Print some details about the result
                if query_name == "Schema Introspection":
                    type_count = len(result.data['__schema']['types'])
                    print_status(f"  Found {type_count} types in schema", "INFO")
                elif query_name == "Orders Query":
                    order_count = len(result.data['orders'])
                    print_status(f"  Retrieved {order_count} orders", "INFO")
                elif query_name == "Portfolio Query":
                    total_value = result.data['portfolio']['totalValue']
                    print_status(f"  Portfolio total value: ${total_value}", "INFO")
                elif query_name == "Market Data Query":
                    price = result.data['marketData']['lastPrice']
                    symbol = result.data['marketData']['symbol']
                    print_status(f"  {symbol} price: ${price}", "INFO")
                
                successful_queries += 1
                
            except Exception as e:
                print_status(f"{query_name} execution error: {e}", "ERROR")
        
        print(f"    {progress_bar(total_queries, total_queries)}")
        print_status(f"Query tests completed: {successful_queries}/{total_queries} successful", "INFO")
        
        return successful_queries == total_queries
        
    except Exception as e:
        print_status(f"Query test error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False

def test_graphql_mutations():
    """Test GraphQL mutations with progress tracking"""
    print_status("Testing GraphQL mutations...", "PROGRESS")
    
    try:
        success, api = test_graphql_api_creation()
        if not success:
            return False
        
        schema = api.schema
        mutations_to_test = [
            ("Create Order", """
                mutation {
                    createOrder(
                        symbol: "AAPL"
                        side: "buy"
                        quantity: 100
                        orderType: "limit"
                        price: 150.25
                    ) {
                        success
                        message
                        order {
                            id
                            symbol
                            side
                            quantity
                            price
                            status
                        }
                    }
                }
            """),
            ("Cancel Order", """
                mutation {
                    cancelOrder(orderId: "test-order-123") {
                        success
                        message
                    }
                }
            """)
        ]
        
        total_mutations = len(mutations_to_test)
        successful_mutations = 0
        
        for i, (mutation_name, mutation) in enumerate(mutations_to_test, 1):
            print_status(f"Testing {mutation_name} ({i}/{total_mutations})...", "PROGRESS")
            print(f"    {progress_bar(i-1, total_mutations)}")
            
            try:
                result = schema.execute(mutation)
                
                if result.errors:
                    print_status(f"{mutation_name} has errors: {result.errors}", "ERROR")
                    continue
                
                if result.data is None:
                    print_status(f"{mutation_name} returned no data", "WARNING")
                    continue
                
                print_status(f"{mutation_name} successful!", "SUCCESS")
                
                # Print mutation result details
                if mutation_name == "Create Order":
                    success_flag = result.data['createOrder']['success']
                    message = result.data['createOrder']['message']
                    print_status(f"  Success: {success_flag}, Message: {message}", "INFO")
                elif mutation_name == "Cancel Order":
                    success_flag = result.data['cancelOrder']['success']
                    message = result.data['cancelOrder']['message']
                    print_status(f"  Success: {success_flag}, Message: {message}", "INFO")
                
                successful_mutations += 1
                
            except Exception as e:
                print_status(f"{mutation_name} execution error: {e}", "ERROR")
        
        print(f"    {progress_bar(total_mutations, total_mutations)}")
        print_status(f"Mutation tests completed: {successful_mutations}/{total_mutations} successful", "INFO")
        
        return successful_mutations == total_mutations
        
    except Exception as e:
        print_status(f"Mutation test error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False

def test_graphql_complexity():
    """Test GraphQL query complexity analysis with progress"""
    print_status("Testing GraphQL complexity analysis...", "PROGRESS")
    
    try:
        print_status("Step 1/3: Importing complexity analyzer...", "PROGRESS")
        from nautilus_trader_engine.api.graphql_api import QueryComplexityAnalyzer
        from graphql import parse
        
        print_status("Step 2/3: Creating analyzer instance...", "PROGRESS")
        analyzer = QueryComplexityAnalyzer()
        
        print_status("Step 3/3: Testing query analysis...", "PROGRESS")
        
        test_queries = [
            ("Simple Query", """
                query {
                    orders {
                        id
                        symbol
                    }
                }
            """),
            ("Complex Query", """
                query {
                    portfolio {
                        totalValue
                        positions {
                            symbol
                            quantity
                            marketValue
                        }
                    }
                    orders {
                        id
                        symbol
                        side
                        quantity
                    }
                }
            """)
        ]
        
        for query_name, query in test_queries:
            print_status(f"Analyzing {query_name}...", "PROGRESS")
            
            try:
                query_ast = parse(query)
                analysis = analyzer.analyze_query(query_ast)
                
                print_status(f"{query_name} analysis complete!", "SUCCESS")
                print_status(f"  Complexity: {analysis['complexity']}", "INFO")
                print_status(f"  Depth: {analysis['depth']}", "INFO")
                print_status(f"  Field count: {analysis['field_count']}", "INFO")
                print_status(f"  Valid: {analysis['is_valid']}", "INFO")
                
            except Exception as e:
                print_status(f"{query_name} analysis error: {e}", "ERROR")
                return False
        
        print_status("Complexity analysis tests successful!", "SUCCESS")
        return True
        
    except Exception as e:
        print_status(f"Complexity test error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test runner with comprehensive progress tracking"""
    print("=" * 60)
    print("🧪 COMPREHENSIVE GRAPHQL API TEST SUITE")
    print("=" * 60)
    print()
    
    start_time = time.time()
    
    test_suite = [
        ("GraphQL Imports", test_graphql_imports),
        ("GraphQL Queries", test_graphql_queries),
        ("GraphQL Mutations", test_graphql_mutations),
        ("GraphQL Complexity", test_graphql_complexity),
    ]
    
    total_tests = len(test_suite)
    passed_tests = 0
    
    print_status(f"Starting test suite with {total_tests} test categories...", "INFO")
    print()
    
    for i, (test_name, test_func) in enumerate(test_suite, 1):
        print("=" * 40)
        print_status(f"TEST {i}/{total_tests}: {test_name}", "INFO")
        print("=" * 40)
        
        test_start = time.time()
        
        try:
            if test_func():
                test_duration = time.time() - test_start
                print_status(f"{test_name} PASSED in {test_duration:.2f}s", "SUCCESS")
                passed_tests += 1
            else:
                test_duration = time.time() - test_start
                print_status(f"{test_name} FAILED in {test_duration:.2f}s", "ERROR")
        except Exception as e:
            test_duration = time.time() - test_start
            print_status(f"{test_name} CRASHED in {test_duration:.2f}s: {e}", "ERROR")
        
        print()
    
    # Final results
    total_duration = time.time() - start_time
    print("=" * 60)
    print_status("TEST SUITE COMPLETED", "INFO")
    print("=" * 60)
    print_status(f"Total time: {total_duration:.2f} seconds", "INFO")
    print_status(f"Tests passed: {passed_tests}/{total_tests}", "INFO")
    print(f"Success rate: {progress_bar(passed_tests, total_tests)}")
    
    if passed_tests == total_tests:
        print_status("🎉 ALL TESTS PASSED! GraphQL API is fully functional!", "SUCCESS")
        return True
    else:
        print_status(f"⚠️  {total_tests - passed_tests} test(s) failed. GraphQL API needs attention.", "WARNING")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)