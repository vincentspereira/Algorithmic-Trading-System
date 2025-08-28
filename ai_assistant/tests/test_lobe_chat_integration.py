#!/usr/bin/env python3
"""
Test script for Lobe Chat integration with AI Assistant
This script tests the complete integration flow from Lobe Chat to AI Assistant
"""

import asyncio
import json
import sys
from typing import Dict, Any
import httpx
import time

# Test configuration
AI_ASSISTANT_URL = "http://localhost:8002"
LOBE_ADAPTER_URL = "http://localhost:8003"
LOBE_CHAT_URL = "http://localhost:3210"

class LobeChatIntegrationTester:
    """Test suite for Lobe Chat integration"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_results = []
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def log_test(self, test_name: str, success: bool, message: str = "", details: Dict[str, Any] = None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if message:
            print(f"    {message}")
        if details:
            print(f"    Details: {json.dumps(details, indent=2)}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "details": details
        })
    
    async def test_ai_assistant_health(self):
        """Test AI Assistant health endpoint"""
        try:
            response = await self.client.get(f"{AI_ASSISTANT_URL}/health")
            success = response.status_code == 200
            data = response.json() if success else None
            
            self.log_test(
                "AI Assistant Health Check",
                success,
                f"Status: {response.status_code}",
                data
            )
            return success
        except Exception as e:
            self.log_test("AI Assistant Health Check", False, f"Error: {str(e)}")
            return False
    
    async def test_lobe_adapter_health(self):
        """Test Lobe Chat Adapter health endpoint"""
        try:
            response = await self.client.get(f"{LOBE_ADAPTER_URL}/health")
            success = response.status_code == 200
            data = response.json() if success else None
            
            self.log_test(
                "Lobe Chat Adapter Health Check",
                success,
                f"Status: {response.status_code}",
                data
            )
            return success
        except Exception as e:
            self.log_test("Lobe Chat Adapter Health Check", False, f"Error: {str(e)}")
            return False
    
    async def test_lobe_chat_frontend(self):
        """Test Lobe Chat frontend accessibility"""
        try:
            response = await self.client.get(LOBE_CHAT_URL)
            success = response.status_code == 200
            
            self.log_test(
                "Lobe Chat Frontend Access",
                success,
                f"Status: {response.status_code}"
            )
            return success
        except Exception as e:
            self.log_test("Lobe Chat Frontend Access", False, f"Error: {str(e)}")
            return False
    
    async def test_models_endpoint(self):
        """Test OpenAI-compatible models endpoint"""
        try:
            response = await self.client.get(f"{LOBE_ADAPTER_URL}/v1/models")
            success = response.status_code == 200
            data = response.json() if success else None
            
            # Check if trading-assistant model is available
            has_trading_model = False
            if data and "data" in data:
                has_trading_model = any(
                    model.get("id") == "trading-assistant" 
                    for model in data["data"]
                )
            
            self.log_test(
                "Models Endpoint",
                success and has_trading_model,
                f"Status: {response.status_code}, Trading model available: {has_trading_model}",
                data
            )
            return success and has_trading_model
        except Exception as e:
            self.log_test("Models Endpoint", False, f"Error: {str(e)}")
            return False
    
    async def test_direct_ai_assistant_chat(self):
        """Test direct chat with AI Assistant"""
        try:
            test_message = "Hello, can you help me with algorithmic trading?"
            payload = {
                "message": test_message,
                "session_id": "test-session-direct"
            }
            
            response = await self.client.post(
                f"{AI_ASSISTANT_URL}/api/v1/chat",
                json=payload
            )
            
            success = response.status_code == 200
            data = response.json() if success else None
            
            # Check response structure
            has_response = data and "response" in data and data["response"]
            has_session_id = data and "session_id" in data
            
            self.log_test(
                "Direct AI Assistant Chat",
                success and has_response and has_session_id,
                f"Status: {response.status_code}, Has response: {has_response}",
                {"response_length": len(data.get("response", "")) if data else 0}
            )
            return success and has_response
        except Exception as e:
            self.log_test("Direct AI Assistant Chat", False, f"Error: {str(e)}")
            return False
    
    async def test_adapter_chat_completion(self):
        """Test chat completion through adapter"""
        try:
            test_payload = {
                "model": "trading-assistant",
                "messages": [
                    {"role": "user", "content": "What is algorithmic trading?"}
                ],
                "temperature": 0.7,
                "max_tokens": 1000,
                "stream": False
            }
            
            response = await self.client.post(
                f"{LOBE_ADAPTER_URL}/v1/chat/completions",
                json=test_payload
            )
            
            success = response.status_code == 200
            data = response.json() if success else None
            
            # Check OpenAI-compatible response structure
            has_choices = data and "choices" in data and len(data["choices"]) > 0
            has_message = has_choices and "message" in data["choices"][0]
            has_content = has_message and "content" in data["choices"][0]["message"]
            
            self.log_test(
                "Adapter Chat Completion",
                success and has_choices and has_message and has_content,
                f"Status: {response.status_code}, Valid structure: {has_choices and has_message and has_content}",
                {
                    "response_length": len(data["choices"][0]["message"]["content"]) if has_content else 0,
                    "model": data.get("model") if data else None
                }
            )
            return success and has_content
        except Exception as e:
            self.log_test("Adapter Chat Completion", False, f"Error: {str(e)}")
            return False
    
    async def test_streaming_response(self):
        """Test streaming chat completion"""
        try:
            test_payload = {
                "model": "trading-assistant",
                "messages": [
                    {"role": "user", "content": "Explain backtesting briefly"}
                ],
                "stream": True
            }
            
            response = await self.client.post(
                f"{LOBE_ADAPTER_URL}/v1/chat/completions",
                json=test_payload
            )
            
            success = response.status_code == 200
            is_streaming = "text/plain" in response.headers.get("content-type", "")
            
            # Read first few chunks to verify streaming
            chunks_received = 0
            if success:
                async for chunk in response.aiter_text():
                    if chunk.strip():
                        chunks_received += 1
                    if chunks_received >= 3:  # Test first few chunks
                        break
            
            self.log_test(
                "Streaming Response",
                success and is_streaming and chunks_received > 0,
                f"Status: {response.status_code}, Streaming: {is_streaming}, Chunks: {chunks_received}"
            )
            return success and chunks_received > 0
        except Exception as e:
            self.log_test("Streaming Response", False, f"Error: {str(e)}")
            return False
    
    async def test_reasoning_traces(self):
        """Test that reasoning traces are included in responses"""
        try:
            test_message = "Run a simple backtest for testing purposes"
            payload = {
                "message": test_message,
                "session_id": "test-session-reasoning"
            }
            
            response = await self.client.post(
                f"{AI_ASSISTANT_URL}/api/v1/chat",
                json=payload
            )
            
            success = response.status_code == 200
            data = response.json() if success else None
            
            # Check for reasoning traces
            has_reasoning = data and "reasoning" in data and data["reasoning"]
            has_tools_used = data and "tools_used" in data and data["tools_used"]
            
            self.log_test(
                "Reasoning Traces",
                success and (has_reasoning or has_tools_used),
                f"Status: {response.status_code}, Has reasoning: {has_reasoning}, Has tools: {has_tools_used}",
                {
                    "reasoning_steps": len(data.get("reasoning", [])) if data else 0,
                    "tools_count": len(data.get("tools_used", [])) if data else 0
                }
            )
            return success
        except Exception as e:
            self.log_test("Reasoning Traces", False, f"Error: {str(e)}")
            return False
    
    async def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 Starting Lobe Chat Integration Tests")
        print("=" * 50)
        
        # Basic health checks
        await self.test_ai_assistant_health()
        await self.test_lobe_adapter_health()
        await self.test_lobe_chat_frontend()
        
        # API functionality tests
        await self.test_models_endpoint()
        await self.test_direct_ai_assistant_chat()
        await self.test_adapter_chat_completion()
        await self.test_streaming_response()
        await self.test_reasoning_traces()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Summary")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['message']}")
        
        return failed_tests == 0


async def main():
    """Main test runner"""
    print("Lobe Chat Integration Test Suite")
    print("Waiting 5 seconds for services to be ready...")
    await asyncio.sleep(5)
    
    async with LobeChatIntegrationTester() as tester:
        success = await tester.run_all_tests()
        
        if success:
            print("\n🎉 All tests passed! Lobe Chat integration is working correctly.")
            sys.exit(0)
        else:
            print("\n💥 Some tests failed. Please check the logs and fix the issues.")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
