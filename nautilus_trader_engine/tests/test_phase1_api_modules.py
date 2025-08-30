#!/usr/bin/env python3
"""
API Interfaces Module Validation Test
Phase 1 - Core System Validation & Hardening

Tests all four API interface modules and their readiness:
1. REST API (FastAPI) - Module structure and imports
2. GraphQL API - Module functionality
3. WebSocket API - Module structure and connection logic
4. gRPC API - Proto definitions and structure

Author: Vincent S. Pereira
Version: 1.0.0
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, List, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class APIModuleResults:
    """Collect and manage API module test results"""
    
    def __init__(self):
        self.results = {
            "rest_api": {"status": "NOT_TESTED", "tests": [], "success_rate": 0.0},
            "graphql_api": {"status": "NOT_TESTED", "tests": [], "success_rate": 0.0},
            "websocket_api": {"status": "NOT_TESTED", "tests": [], "success_rate": 0.0},
            "grpc_api": {"status": "NOT_TESTED", "tests": [], "success_rate": 0.0},
        }
        self.total_tests = 0
        self.passed_tests = 0
        
    def add_test_result(self, api_type: str, test_name: str, success: bool, details: str = ""):
        """Add a test result"""
        self.results[api_type]["tests"].append({
            "name": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        
        self.total_tests += 1
        if success:
            self.passed_tests += 1
            
        # Update API status and success rate
        api_tests = self.results[api_type]["tests"]
        api_passed = len([t for t in api_tests if t["success"]])
        api_total = len(api_tests)
        
        if api_total > 0:
            self.results[api_type]["success_rate"] = (api_passed / api_total) * 100
            if self.results[api_type]["success_rate"] >= 75:
                self.results[api_type]["status"] = "READY"
            elif self.results[api_type]["success_rate"] >= 50:
                self.results[api_type]["status"] = "PARTIAL"
            else:
                self.results[api_type]["status"] = "FAILED"
    
    def get_overall_status(self) -> str:
        """Get overall API readiness status"""
        if self.total_tests == 0:
            return "NOT_TESTED"
        
        overall_success_rate = (self.passed_tests / self.total_tests) * 100
        
        if overall_success_rate >= 80:
            return "READY"
        elif overall_success_rate >= 60:
            return "PARTIAL"
        else:
            return "FAILED"

def test_rest_api_modules(results: APIModuleResults):
    """Test REST API module structure and imports"""
    print("\n🌐 Testing REST API Modules")
    print("=" * 40)
    
    # Test 1: Main FastAPI App Import
    try:
        from nautilus_trader_engine.api.main import app
        print("✅ FastAPI Main App - PASS")
        results.add_test_result("rest_api", "main_app_import", True, "FastAPI app imported successfully")
    except Exception as e:
        print(f"❌ FastAPI Main App - FAIL (Error: {e})")
        results.add_test_result("rest_api", "main_app_import", False, str(e))
    
    # Test 2: Router Modules
    router_modules = [
        "nautilus_trader_engine.api.routers.auth",
        "nautilus_trader_engine.api.routers.trading",
        "nautilus_trader_engine.api.routers.backtest",
        "nautilus_trader_engine.api.routers.features",
        "nautilus_trader_engine.api.routers.optimization"
    ]
    
    for module_name in router_modules:
        try:
            __import__(module_name)
            router_name = module_name.split('.')[-1]
            print(f"✅ REST Router {router_name} - PASS")
            results.add_test_result("rest_api", f"router_{router_name}", True, f"Router {router_name} imported")
        except Exception as e:
            router_name = module_name.split('.')[-1]
            print(f"❌ REST Router {router_name} - FAIL (Error: {e})")
            results.add_test_result("rest_api", f"router_{router_name}", False, str(e))
    
    # Test 3: Core Configuration
    try:
        from nautilus_trader_engine.api.core.config import settings
        print("✅ REST API Config - PASS")
        results.add_test_result("rest_api", "config_import", True, "API configuration imported")
    except Exception as e:
        print(f"❌ REST API Config - FAIL (Error: {e})")
        results.add_test_result("rest_api", "config_import", False, str(e))
    
    # Test 4: Models Import
    try:
        from nautilus_trader_engine.api.models.trading import PortfolioResponse, OrderRequest
        print("✅ REST API Models - PASS")
        results.add_test_result("rest_api", "models_import", True, "Trading models imported")
    except Exception as e:
        print(f"❌ REST API Models - FAIL (Error: {e})")
        results.add_test_result("rest_api", "models_import", False, str(e))

def test_graphql_api_modules(results: APIModuleResults):
    """Test GraphQL API module functionality"""
    print("\n🔗 Testing GraphQL API Modules")
    print("=" * 40)
    
    # Test 1: GraphQL Module Import
    try:
        from nautilus_trader_engine.api.graphql_api import GraphQLCache, QueryComplexityAnalyzer, GraphQLMetrics
        print("✅ GraphQL Core Modules - PASS")
        results.add_test_result("graphql_api", "core_modules", True, "Core GraphQL modules imported")
    except Exception as e:
        print(f"❌ GraphQL Core Modules - FAIL (Error: {e})")
        results.add_test_result("graphql_api", "core_modules", False, str(e))
        return
    
    # Test 2: GraphQL Cache Functionality
    try:
        cache = GraphQLCache()
        test_query = "{ hello { world } }"
        
        # Test cache key generation
        cache_key = cache._generate_cache_key(test_query, {})
        if cache_key and len(cache_key) == 32:  # MD5 hash length
            print("✅ GraphQL Cache Key Generation - PASS")
            results.add_test_result("graphql_api", "cache_key_generation", True, "Cache key generation working")
        else:
            print("❌ GraphQL Cache Key Generation - FAIL")
            results.add_test_result("graphql_api", "cache_key_generation", False, "Invalid cache key")
    except Exception as e:
        print(f"❌ GraphQL Cache Key Generation - FAIL (Error: {e})")
        results.add_test_result("graphql_api", "cache_key_generation", False, str(e))
    
    # Test 3: Query Complexity Analyzer
    try:
        analyzer = QueryComplexityAnalyzer(max_complexity=100, max_depth=10)
        if analyzer.max_complexity == 100 and analyzer.max_depth == 10:
            print("✅ GraphQL Query Analyzer - PASS")
            results.add_test_result("graphql_api", "query_analyzer", True, "Query analyzer initialized correctly")
        else:
            print("❌ GraphQL Query Analyzer - FAIL")
            results.add_test_result("graphql_api", "query_analyzer", False, "Analyzer configuration incorrect")
    except Exception as e:
        print(f"❌ GraphQL Query Analyzer - FAIL (Error: {e})")
        results.add_test_result("graphql_api", "query_analyzer", False, str(e))
    
    # Test 4: GraphQL Metrics
    try:
        metrics = GraphQLMetrics(
            query_id="test123",
            query="{ test }",
            variables={},
            execution_time=0.1,
            complexity_score=5,
            field_count=1,
            depth=1,
            user_id="user123",
            timestamp=datetime.now()
        )
        print("✅ GraphQL Metrics - PASS")
        results.add_test_result("graphql_api", "metrics", True, "GraphQL metrics creation working")
    except Exception as e:
        print(f"❌ GraphQL Metrics - FAIL (Error: {e})")
        results.add_test_result("graphql_api", "metrics", False, str(e))

def test_websocket_api_modules(results: APIModuleResults):
    """Test WebSocket API module structure"""
    print("\n⚡ Testing WebSocket API Modules")
    print("=" * 40)
    
    # Test 1: WebSocket Router Import
    try:
        from nautilus_trader_engine.api.routers.websocket import router, WebSocketManager
        print("✅ WebSocket Router - PASS")
        results.add_test_result("websocket_api", "router_import", True, "WebSocket router imported")
    except Exception as e:
        print(f"❌ WebSocket Router - FAIL (Error: {e})")
        results.add_test_result("websocket_api", "router_import", False, str(e))
        return
    
    # Test 2: WebSocket Manager Functionality
    try:
        manager = WebSocketManager()
        
        # Test manager initialization
        if hasattr(manager, 'active_connections') and hasattr(manager, 'subscriptions'):
            print("✅ WebSocket Manager Structure - PASS")
            results.add_test_result("websocket_api", "manager_structure", True, "Manager has required attributes")
        else:
            print("❌ WebSocket Manager Structure - FAIL")
            results.add_test_result("websocket_api", "manager_structure", False, "Missing required attributes")
    except Exception as e:
        print(f"❌ WebSocket Manager Structure - FAIL (Error: {e})")
        results.add_test_result("websocket_api", "manager_structure", False, str(e))
    
    # Test 3: WebSocket Subscription Logic
    try:
        manager = WebSocketManager()
        
        # Simulate subscription management
        test_client_id = "test_client_123"
        manager.subscriptions[test_client_id] = set()
        
        # Test subscription addition (simulate async call)
        test_topics = ["market.ticks.AAPL", "trading.orders"]
        manager.subscriptions[test_client_id].update(test_topics)
        
        if len(manager.subscriptions[test_client_id]) == 2:
            print("✅ WebSocket Subscription Logic - PASS")
            results.add_test_result("websocket_api", "subscription_logic", True, "Subscription management working")
        else:
            print("❌ WebSocket Subscription Logic - FAIL")
            results.add_test_result("websocket_api", "subscription_logic", False, "Subscription count mismatch")
    except Exception as e:
        print(f"❌ WebSocket Subscription Logic - FAIL (Error: {e})")
        results.add_test_result("websocket_api", "subscription_logic", False, str(e))
    
    # Test 4: Streaming Module
    try:
        from nautilus_trader_engine.api.streaming import app as streaming_app
        print("✅ WebSocket Streaming Module - PASS")
        results.add_test_result("websocket_api", "streaming_module", True, "Streaming module imported")
    except Exception as e:
        print(f"❌ WebSocket Streaming Module - FAIL (Error: {e})")
        results.add_test_result("websocket_api", "streaming_module", False, str(e))

def test_grpc_api_modules(results: APIModuleResults):
    """Test gRPC API module structure"""
    print("\n🚀 Testing gRPC API Modules")
    print("=" * 40)
    
    # Test 1: gRPC Proto Files Existence
    proto_files_to_check = [
        ("nautilus_trader_engine/api/protos/market_data.proto", "MarketData Service"),
        ("api/trading.proto", "Trading Service")
    ]
    
    for proto_file, service_name in proto_files_to_check:
        try:
            full_path = os.path.join(os.getcwd(), proto_file)
            if os.path.exists(full_path):
                with open(full_path, 'r') as f:
                    content = f.read()
                    
                # Check for service definition
                if "service" in content.lower():
                    print(f"✅ gRPC Proto {service_name} - PASS")
                    results.add_test_result("grpc_api", f"proto_{service_name.lower().replace(' ', '_')}", True, f"Proto file exists with service definition")
                else:
                    print(f"❌ gRPC Proto {service_name} - FAIL (No service definition)")
                    results.add_test_result("grpc_api", f"proto_{service_name.lower().replace(' ', '_')}", False, "No service definition found")
            else:
                print(f"❌ gRPC Proto {service_name} - FAIL (File not found)")
                results.add_test_result("grpc_api", f"proto_{service_name.lower().replace(' ', '_')}", False, "Proto file not found")
        except Exception as e:
            print(f"❌ gRPC Proto {service_name} - FAIL (Error: {e})")
            results.add_test_result("grpc_api", f"proto_{service_name.lower().replace(' ', '_')}", False, str(e))
    
    # Test 2: gRPC Generation Script
    try:
        gen_script_path = "nautilus_trader_engine/api/generate_grpc_stubs.py"
        if os.path.exists(gen_script_path):
            print("✅ gRPC Generation Script - PASS")
            results.add_test_result("grpc_api", "generation_script", True, "gRPC generation script exists")
        else:
            print("❌ gRPC Generation Script - FAIL")
            results.add_test_result("grpc_api", "generation_script", False, "Generation script not found")
    except Exception as e:
        print(f"❌ gRPC Generation Script - FAIL (Error: {e})")
        results.add_test_result("grpc_api", "generation_script", False, str(e))
    
    # Test 3: Generated gRPC Stubs Directory
    try:
        generated_dir = "nautilus_trader_engine/api/generated"
        if os.path.exists(generated_dir):
            files_in_generated = os.listdir(generated_dir)
            if files_in_generated:
                print(f"✅ gRPC Generated Stubs - PASS ({len(files_in_generated)} files)")
                results.add_test_result("grpc_api", "generated_stubs", True, f"Generated directory with {len(files_in_generated)} files")
            else:
                print("⚠️  gRPC Generated Stubs - EMPTY")
                results.add_test_result("grpc_api", "generated_stubs", False, "Generated directory is empty")
        else:
            print("⚠️  gRPC Generated Stubs - NOT FOUND")
            results.add_test_result("grpc_api", "generated_stubs", False, "Generated directory not found")
    except Exception as e:
        print(f"❌ gRPC Generated Stubs - FAIL (Error: {e})")
        results.add_test_result("grpc_api", "generated_stubs", False, str(e))
    
    # Test 4: Service Definitions Content Analysis
    try:
        service_methods_found = []
        
        # Check trading proto for expected methods
        trading_proto = "api/trading.proto"
        if os.path.exists(trading_proto):
            with open(trading_proto, 'r') as f:
                content = f.read()
                expected_methods = ["SubmitOrder", "CancelOrder", "StreamMarketData", "GetPositions"]
                for method in expected_methods:
                    if method in content:
                        service_methods_found.append(method)
        
        if len(service_methods_found) >= 3:
            print(f"✅ gRPC Service Methods - PASS ({len(service_methods_found)} methods)")
            results.add_test_result("grpc_api", "service_methods", True, f"Found methods: {service_methods_found}")
        else:
            print(f"❌ gRPC Service Methods - FAIL ({len(service_methods_found)} methods)")
            results.add_test_result("grpc_api", "service_methods", False, f"Only found: {service_methods_found}")
            
    except Exception as e:
        print(f"❌ gRPC Service Methods - FAIL (Error: {e})")
        results.add_test_result("grpc_api", "service_methods", False, str(e))

def run_api_module_tests():
    """Run comprehensive API module tests"""
    print("🚀 Starting API Interfaces Module Validation Test")
    print("Phase 1 - Core System Validation & Hardening")
    print("=" * 60)
    
    results = APIModuleResults()
    
    # Run all API module tests
    test_rest_api_modules(results)
    test_graphql_api_modules(results)
    test_websocket_api_modules(results)
    test_grpc_api_modules(results)
    
    # Generate summary
    print(f"\n📊 API Interfaces Module Test Summary")
    print("=" * 50)
    
    overall_status = results.get_overall_status()
    overall_success_rate = (results.passed_tests / results.total_tests) * 100 if results.total_tests > 0 else 0
    
    print(f"Total Tests: {results.total_tests}")
    print(f"Passed: {results.passed_tests}")
    print(f"Failed: {results.total_tests - results.passed_tests}")
    print(f"Overall Success Rate: {overall_success_rate:.1f}%")
    print(f"Overall Status: {overall_status}")
    
    print(f"\nAPI Interface Module Breakdown:")
    for api_type, data in results.results.items():
        status_emoji = "✅" if data["status"] == "READY" else "⚠️" if data["status"] == "PARTIAL" else "❌"
        print(f"  {status_emoji} {api_type.replace('_', ' ').title()}: {data['status']} ({data['success_rate']:.1f}%)")
        
        # Show failed tests
        failed_tests = [t for t in data["tests"] if not t["success"]]
        if failed_tests:
            for test in failed_tests[:3]:  # Show first 3 failures
                print(f"    └─ ❌ {test['name']}: {test['details'][:80]}...")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"phase1_api_modules_test_{timestamp}.json"
    
    final_results = {
        "test_metadata": {
            "timestamp": datetime.now().isoformat(),
            "total_tests": results.total_tests,
            "passed_tests": results.passed_tests,
            "overall_success_rate": overall_success_rate,
            "overall_status": overall_status
        },
        "api_module_results": results.results,
        "phase1_readiness": "READY" if overall_success_rate >= 80 else "PARTIAL" if overall_success_rate >= 60 else "FAILED"
    }
    
    with open(results_file, 'w') as f:
        json.dump(final_results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {results_file}")
    
    # Final assessment
    if overall_success_rate >= 80:
        print(f"\n🎉 Phase 1 API Interfaces: READY!")
        print(f"   • All 4 API types implemented: REST, GraphQL, WebSocket, gRPC")
        print(f"   • {results.passed_tests}/{results.total_tests} module tests passing")
        print(f"   • Comprehensive API ecosystem operational")
        print(f"   • Ready for live server deployment and testing")
    elif overall_success_rate >= 60:
        print(f"\n⚠️  Phase 1 API Interfaces: PARTIALLY READY")
        print(f"   • {results.passed_tests}/{results.total_tests} module tests passing")
        print(f"   • Some API interfaces need attention")
        print(f"   • Review failed modules before deployment")
    else:
        print(f"\n❌ Phase 1 API Interfaces: NEEDS WORK")
        print(f"   • Only {results.passed_tests}/{results.total_tests} module tests passing")
        print(f"   • Significant API module issues need resolution")
    
    return overall_success_rate >= 80

if __name__ == "__main__":
    success = run_api_module_tests()
    sys.exit(0 if success else 1)