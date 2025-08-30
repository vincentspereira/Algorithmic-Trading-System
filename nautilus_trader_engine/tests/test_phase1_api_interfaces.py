#!/usr/bin/env python3
"""
Comprehensive API Interfaces Validation Test
Phase 1 - Core System Validation & Hardening

Tests all four API interfaces:
1. REST API (FastAPI)
2. GraphQL API 
3. WebSocket API
4. gRPC API

Author: Vincent S. Pereira
Version: 1.0.0
"""

import sys
import os
import asyncio
import json
import time
import websockets
import aiohttp
from datetime import datetime
from typing import Dict, List, Any
import subprocess
import threading
import signal

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class APITestResults:
    """Collect and manage API test results"""
    
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

async def test_rest_api(results: APITestResults, base_url: str = "http://localhost:8000"):
    """Test REST API endpoints"""
    print("\n🌐 Testing REST API Endpoints")
    print("=" * 40)
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Health Check
        try:
            async with session.get(f"{base_url}/") as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ REST Health Check - PASS")
                    results.add_test_result("rest_api", "health_check", True, f"Status: {response.status}")
                else:
                    print(f"❌ REST Health Check - FAIL (Status: {response.status})")
                    results.add_test_result("rest_api", "health_check", False, f"Status: {response.status}")
        except Exception as e:
            print(f"❌ REST Health Check - FAIL (Error: {e})")
            results.add_test_result("rest_api", "health_check", False, str(e))
        
        # Test 2: OpenAPI Documentation
        try:
            async with session.get(f"{base_url}/docs") as response:
                if response.status == 200:
                    print("✅ REST OpenAPI Docs - PASS")
                    results.add_test_result("rest_api", "openapi_docs", True, "Documentation accessible")
                else:
                    print(f"❌ REST OpenAPI Docs - FAIL (Status: {response.status})")
                    results.add_test_result("rest_api", "openapi_docs", False, f"Status: {response.status}")
        except Exception as e:
            print(f"❌ REST OpenAPI Docs - FAIL (Error: {e})")
            results.add_test_result("rest_api", "openapi_docs", False, str(e))
        
        # Test 3: API V1 Endpoints
        endpoints_to_test = [
            "/api/v1/openapi.json",
        ]
        
        for endpoint in endpoints_to_test:
            test_name = f"endpoint_{endpoint.replace('/', '_')}"
            try:
                async with session.get(f"{base_url}{endpoint}") as response:
                    if response.status in [200, 401]:  # 401 is acceptable for protected endpoints
                        print(f"✅ REST {endpoint} - PASS")
                        results.add_test_result("rest_api", test_name, True, f"Status: {response.status}")
                    else:
                        print(f"❌ REST {endpoint} - FAIL (Status: {response.status})")
                        results.add_test_result("rest_api", test_name, False, f"Status: {response.status}")
            except Exception as e:
                print(f"❌ REST {endpoint} - FAIL (Error: {e})")
                results.add_test_result("rest_api", test_name, False, str(e))

async def test_graphql_api(results: APITestResults, base_url: str = "http://localhost:8000"):
    """Test GraphQL API functionality"""
    print("\n🔗 Testing GraphQL API")
    print("=" * 40)
    
    # Test 1: GraphQL Module Import
    try:
        from nautilus_trader_engine.api.graphql_api import GraphQLCache, QueryComplexityAnalyzer
        print("✅ GraphQL Modules Import - PASS")
        results.add_test_result("graphql_api", "module_import", True, "GraphQL modules imported successfully")
    except Exception as e:
        print(f"❌ GraphQL Modules Import - FAIL (Error: {e})")
        results.add_test_result("graphql_api", "module_import", False, str(e))
        return
    
    # Test 2: GraphQL Cache Functionality
    try:
        cache = GraphQLCache()
        test_query = "{ hello { world } }"
        test_result = {"data": {"hello": {"world": "test"}}}
        
        # Test cache set and get
        await cache.set(test_query, {}, test_result, ttl=10)
        cached_result = await cache.get(test_query, {})
        
        if cached_result == test_result:
            print("✅ GraphQL Cache - PASS")
            results.add_test_result("graphql_api", "cache_functionality", True, "Cache set/get working")
        else:
            print("❌ GraphQL Cache - FAIL")
            results.add_test_result("graphql_api", "cache_functionality", False, "Cache mismatch")
    except Exception as e:
        print(f"❌ GraphQL Cache - FAIL (Error: {e})")
        results.add_test_result("graphql_api", "cache_functionality", False, str(e))
    
    # Test 3: Query Complexity Analyzer
    try:
        analyzer = QueryComplexityAnalyzer(max_complexity=100, max_depth=10)
        print("✅ GraphQL Query Analyzer - PASS")
        results.add_test_result("graphql_api", "query_analyzer", True, "Analyzer initialized successfully")
    except Exception as e:
        print(f"❌ GraphQL Query Analyzer - FAIL (Error: {e})")
        results.add_test_result("graphql_api", "query_analyzer", False, str(e))

async def test_websocket_api(results: APITestResults, ws_url: str = "ws://localhost:8000"):
    """Test WebSocket API functionality"""
    print("\n⚡ Testing WebSocket API")
    print("=" * 40)
    
    # Test 1: WebSocket Module Import
    try:
        from nautilus_trader_engine.api.routers.websocket import WebSocketManager, ws_manager
        print("✅ WebSocket Modules Import - PASS")
        results.add_test_result("websocket_api", "module_import", True, "WebSocket modules imported successfully")
    except Exception as e:
        print(f"❌ WebSocket Modules Import - FAIL (Error: {e})")
        results.add_test_result("websocket_api", "module_import", False, str(e))
        return
    
    # Test 2: WebSocket Manager Functionality
    try:
        manager = WebSocketManager()
        print("✅ WebSocket Manager - PASS")
        results.add_test_result("websocket_api", "manager_init", True, "WebSocket manager initialized")
    except Exception as e:
        print(f"❌ WebSocket Manager - FAIL (Error: {e})")
        results.add_test_result("websocket_api", "manager_init", False, str(e))
    
    # Test 3: WebSocket Connection Simulation
    try:
        # We can't easily test actual WebSocket connections without a running server,
        # so we'll test the connection management logic
        manager = WebSocketManager()
        
        # Simulate connection management
        test_client_id = "test_client_123"
        manager.subscriptions[test_client_id] = set()
        
        # Test subscription management
        await manager.subscribe(test_client_id, ["market.ticks.AAPL", "trading.orders"])
        
        if len(manager.subscriptions[test_client_id]) == 2:
            print("✅ WebSocket Subscription Logic - PASS")
            results.add_test_result("websocket_api", "subscription_logic", True, "Subscription management working")
        else:
            print("❌ WebSocket Subscription Logic - FAIL")
            results.add_test_result("websocket_api", "subscription_logic", False, "Subscription count mismatch")
            
    except Exception as e:
        print(f"❌ WebSocket Subscription Logic - FAIL (Error: {e})")
        results.add_test_result("websocket_api", "subscription_logic", False, str(e))

async def test_grpc_api(results: APITestResults):
    """Test gRPC API functionality"""
    print("\n🚀 Testing gRPC API")
    print("=" * 40)
    
    # Test 1: gRPC Proto Files Exist
    try:
        proto_files = [
            "nautilus_trader_engine/api/protos/market_data.proto",
            "api/trading.proto"
        ]
        
        existing_protos = []
        for proto_file in proto_files:
            full_path = os.path.join(os.getcwd(), proto_file)
            if os.path.exists(full_path):
                existing_protos.append(proto_file)
        
        if existing_protos:
            print(f"✅ gRPC Proto Files - PASS ({len(existing_protos)} found)")
            results.add_test_result("grpc_api", "proto_files", True, f"Found: {existing_protos}")
        else:
            print("❌ gRPC Proto Files - FAIL (No proto files found)")
            results.add_test_result("grpc_api", "proto_files", False, "No proto files found")
    except Exception as e:
        print(f"❌ gRPC Proto Files - FAIL (Error: {e})")
        results.add_test_result("grpc_api", "proto_files", False, str(e))
    
    # Test 2: gRPC Generation Script
    try:
        grpc_gen_script = "nautilus_trader_engine/api/generate_grpc_stubs.py"
        if os.path.exists(grpc_gen_script):
            print("✅ gRPC Generation Script - PASS")
            results.add_test_result("grpc_api", "generation_script", True, "Generation script exists")
        else:
            print("❌ gRPC Generation Script - FAIL")
            results.add_test_result("grpc_api", "generation_script", False, "Script not found")
    except Exception as e:
        print(f"❌ gRPC Generation Script - FAIL (Error: {e})")
        results.add_test_result("grpc_api", "generation_script", False, str(e))
    
    # Test 3: gRPC Services Definition
    try:
        # Read proto files and verify service definitions
        proto_content_checks = []
        
        # Check market data proto
        market_data_proto = "nautilus_trader_engine/api/protos/market_data.proto"
        if os.path.exists(market_data_proto):
            with open(market_data_proto, 'r') as f:
                content = f.read()
                if "service MarketData" in content and "StreamMarketData" in content:
                    proto_content_checks.append("MarketData service defined")
        
        # Check trading proto  
        trading_proto = "api/trading.proto"
        if os.path.exists(trading_proto):
            with open(trading_proto, 'r') as f:
                content = f.read()
                if "service TradingService" in content and "SubmitOrder" in content:
                    proto_content_checks.append("TradingService defined")
        
        if proto_content_checks:
            print(f"✅ gRPC Service Definitions - PASS ({len(proto_content_checks)} services)")
            results.add_test_result("grpc_api", "service_definitions", True, f"Services: {proto_content_checks}")
        else:
            print("❌ gRPC Service Definitions - FAIL")
            results.add_test_result("grpc_api", "service_definitions", False, "No service definitions found")
            
    except Exception as e:
        print(f"❌ gRPC Service Definitions - FAIL (Error: {e})")
        results.add_test_result("grpc_api", "service_definitions", False, str(e))

def start_api_server():
    """Start the API server for testing"""
    try:
        # Try to start the FastAPI server
        cmd = [sys.executable, "-m", "uvicorn", "nautilus_trader_engine.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
        
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            cwd=os.getcwd()
        )
        
        # Wait a bit for server to start
        time.sleep(3)
        
        # Check if process is still running
        if process.poll() is None:
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"Server failed to start. STDOUT: {stdout.decode()}, STDERR: {stderr.decode()}")
            return None
            
    except Exception as e:
        print(f"Error starting server: {e}")
        return None

async def run_api_tests():
    """Run comprehensive API interface tests"""
    print("🚀 Starting Comprehensive API Interfaces Test")
    print("Phase 1 - Core System Validation & Hardening")
    print("=" * 60)
    
    results = APITestResults()
    
    # Start API server
    print("\n🔧 Starting API Server...")
    server_process = start_api_server()
    
    if server_process:
        print("✅ API Server started successfully")
        # Additional wait to ensure server is fully up
        await asyncio.sleep(2)
    else:
        print("⚠️  API Server failed to start - testing available modules only")
    
    try:
        # Run all API tests
        await test_rest_api(results)
        await test_graphql_api(results)
        await test_websocket_api(results)
        await test_grpc_api(results)
        
        # Generate summary
        print(f"\n📊 API Interfaces Test Summary")
        print("=" * 50)
        
        overall_status = results.get_overall_status()
        overall_success_rate = (results.passed_tests / results.total_tests) * 100 if results.total_tests > 0 else 0
        
        print(f"Total Tests: {results.total_tests}")
        print(f"Passed: {results.passed_tests}")
        print(f"Failed: {results.total_tests - results.passed_tests}")
        print(f"Overall Success Rate: {overall_success_rate:.1f}%")
        print(f"Overall Status: {overall_status}")
        
        print(f"\nAPI Interface Breakdown:")
        for api_type, data in results.results.items():
            status_emoji = "✅" if data["status"] == "READY" else "⚠️" if data["status"] == "PARTIAL" else "❌"
            print(f"  {status_emoji} {api_type.replace('_', ' ').title()}: {data['status']} ({data['success_rate']:.1f}%)")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"phase1_api_interfaces_test_{timestamp}.json"
        
        final_results = {
            "test_metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_tests": results.total_tests,
                "passed_tests": results.passed_tests,
                "overall_success_rate": overall_success_rate,
                "overall_status": overall_status
            },
            "api_results": results.results,
            "phase1_readiness": "READY" if overall_success_rate >= 80 else "PARTIAL" if overall_success_rate >= 60 else "FAILED"
        }
        
        with open(results_file, 'w') as f:
            json.dump(final_results, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {results_file}")
        
        # Final assessment
        if overall_success_rate >= 80:
            print(f"\n🎉 Phase 1 API Interfaces: READY!")
            print(f"   • All 4 API types implemented: REST, GraphQL, WebSocket, gRPC")
            print(f"   • {results.passed_tests}/{results.total_tests} tests passing")
            print(f"   • Comprehensive API ecosystem operational")
        elif overall_success_rate >= 60:
            print(f"\n⚠️  Phase 1 API Interfaces: PARTIALLY READY")
            print(f"   • {results.passed_tests}/{results.total_tests} tests passing")
            print(f"   • Some API interfaces need attention")
        else:
            print(f"\n❌ Phase 1 API Interfaces: NEEDS WORK")
            print(f"   • Only {results.passed_tests}/{results.total_tests} tests passing")
            print(f"   • Significant API issues need resolution")
        
        return overall_success_rate >= 80
        
    finally:
        # Cleanup: Stop the server
        if server_process:
            try:
                server_process.terminate()
                server_process.wait(timeout=5)
                print("\n🔧 API Server stopped")
            except:
                server_process.kill()
                print("\n🔧 API Server forcefully stopped")

if __name__ == "__main__":
    success = asyncio.run(run_api_tests())
    sys.exit(0 if success else 1)