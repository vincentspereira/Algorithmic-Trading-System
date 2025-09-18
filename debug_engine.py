#!/usr/bin/env python3
"""
Debug script to test engine startup
"""

import asyncio
import logging
from nautilus_trader_engine.main import NautilusTraderEngine

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_engine():
    """Test engine startup"""
    try:
        logger.info("Creating engine...")
        engine = NautilusTraderEngine('paper')
        
        logger.info("Initializing engine...")
        await engine.initialize()
        
        logger.info("Starting engine...")
        await engine.start()
        
        logger.info(f"Engine running: {engine.is_running}")
        
        logger.info("Stopping engine...")
        await engine.stop()
        
        logger.info("Test completed successfully")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_engine())