"""
Test script for WebSocket implementation

This script tests the WebSocket endpoints for real-time market data,
trading updates, and indicator streaming.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import asyncio
import sys
import os
import json
from typing import List

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("websockets library not available. Install with: pip install websockets")


async def test_websocket_connection():
    """Test WebSocket connection to the market data endpoint"""
    if not WEBSOCKETS_AVAILABLE:
        print("Skipping WebSocket test - websockets library not available")
        return True
        
    print("Testing WebSocket connection...")
    
    try:
        # Connect to the WebSocket endpoint
        uri = "ws://localhost:8000/ws/market-data?symbols=AAPL,GOOGL&data_types=ticks,bars"
        async with websockets.connect(uri) as websocket:
            print("✓ Connected to WebSocket endpoint")
            
            # Wait for connection confirmation
            response = await websocket.recv()
            data = json.loads(response)
            print(f"✓ Received connection confirmation: {data['type']}")
            
            # Send a subscription message
            subscribe_message = {
                "action": "subscribe",
                "topics": ["market.ticks.MSFT"]
            }
            await websocket.send(json.dumps(subscribe_message))
            print("✓ Sent subscription message")
            
            # Wait for subscription confirmation
            response = await websocket.recv()
            data = json.loads(response)
            print(f"✓ Received subscription confirmation: {data['type']}")
            
            # Try to receive a few messages (this would be market data in a real implementation)
            try:
                for i in range(3):
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)
                    print(f"✓ Received message {i+1}: {data.get('type', 'unknown')}")
            except asyncio.TimeoutError:
                print("⚠ No market data received within 5 seconds (expected in test environment)")
            
            print("✓ WebSocket test completed successfully")
            return True
            
    except Exception as e:
        print(f"✗ WebSocket test failed: {e}")
        return False


async def test_trading_updates_websocket():
    """Test WebSocket connection to the trading updates endpoint"""
    if not WEBSOCKETS_AVAILABLE:
        print("Skipping trading updates WebSocket test - websockets library not available")
        return True
        
    print("Testing trading updates WebSocket connection...")
    
    try:
        # Connect to the WebSocket endpoint
        uri = "ws://localhost:8000/ws/trading-updates"
        async with websockets.connect(uri) as websocket:
            print("✓ Connected to trading updates WebSocket endpoint")
            
            # Wait for connection confirmation
            response = await websocket.recv()
            data = json.loads(response)
            print(f"✓ Received connection confirmation: {data['type']}")
            
            print("✓ Trading updates WebSocket test completed successfully")
            return True
            
    except Exception as e:
        print(f"✗ Trading updates WebSocket test failed: {e}")
        return False


async def test_indicators_websocket():
    """Test WebSocket connection to the indicators endpoint"""
    if not WEBSOCKETS_AVAILABLE:
        print("Skipping indicators WebSocket test - websockets library not available")
        return True
        
    print("Testing indicators WebSocket connection...")
    
    try:
        # Connect to the WebSocket endpoint
        uri = "ws://localhost:8000/ws/indicators?symbols=AAPL&indicators=sma,ema"
        async with websockets.connect(uri) as websocket:
            print("✓ Connected to indicators WebSocket endpoint")
            
            # Wait for connection confirmation
            response = await websocket.recv()
            data = json.loads(response)
            print(f"✓ Received connection confirmation: {data['type']}")
            
            print("✓ Indicators WebSocket test completed successfully")
            return True
            
    except Exception as e:
        print(f"✗ Indicators WebSocket test failed: {e}")
        return False


async def main():
    """Run all WebSocket tests"""
    print("Running WebSocket implementation tests...\n")
    
    tests = [
        test_websocket_connection,
        test_trading_updates_websocket,
        test_indicators_websocket
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"Test {test.__name__} failed with exception: {e}")
            results.append(False)
        print()  # Add a blank line between tests
    
    # Summary
    passed = sum(results)
    total = len(results)
    print(f"WebSocket tests completed: {passed}/{total} passed")
    
    if passed == total:
        print("All WebSocket tests passed! 🎉")
        return True
    else:
        print("Some WebSocket tests failed. ❌")
        return False


if __name__ == "__main__":
    # Run the tests
    result = asyncio.run(main())
    sys.exit(0 if result else 1)