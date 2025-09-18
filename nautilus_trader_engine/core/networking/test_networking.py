"""
Test Ultra-Low Latency Networking
Basic tests for networking components
"""

import asyncio


from nautilus_trader_engine.core.networking.network_manager import NetworkManager, NetworkConfig, NetworkMode, NetworkProtocol


async def test_network_manager_basic():
    """Test basic network manager functionality"""
    config = NetworkConfig(
        mode=NetworkMode.LOW_LATENCY,
        enable_kernel_bypass=False,  # Disable for testing
        enable_cpu_affinity=False,   # Disable for testing
        enable_numa_awareness=False, # Disable for testing
        pool_size=10
    )
    
    manager = NetworkManager(config)
    
    try:
        # Start the manager
        await manager.start()
        
        # Get stats
        stats = manager.get_stats()
        assert stats['running'] is True
        assert stats['config']['mode'] == 'low_latency'
        
        print("Network manager basic test passed")
        
    finally:
        await manager.stop()


async def test_connection_creation():
    """Test connection creation"""
    config = NetworkConfig(
        mode=NetworkMode.STANDARD,
        enable_kernel_bypass=False,
        enable_cpu_affinity=False,
        enable_numa_awareness=False
    )
    
    manager = NetworkManager(config)
    
    try:
        await manager.start()
        
        # Try to create a connection (this might fail without actual server)
        try:
            connection = await manager.create_connection(
                "127.0.0.1", 
                8080, 
                NetworkProtocol.TCP
            )
            print("Connection created successfully")
        except Exception as e:
            print(f"Connection creation failed (expected): {e}")
        
        print("Connection creation test completed")
        
    finally:
        await manager.stop()


if __name__ == "__main__":
    print("Testing Ultra-Low Latency Networking...")
    
    # Run basic test
    asyncio.run(test_network_manager_basic())
    
    # Run connection test
    asyncio.run(test_connection_creation())
    
    print("All networking tests completed!")