"""
Quick IBKR Connection Validation - Phase 1

This script performs essential IBKR validation tests without performance testing
to avoid hanging issues. Perfect for quick validation of core functionality.

Author: Vincent S. Pereira
Version: 1.0.0
Phase: Phase 1 - Core System Validation & Hardening
"""

import asyncio
import logging
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import required modules
try:
    from ib_insync import IB, Stock, Contract, MarketOrder, LimitOrder
    IB_INSYNC_AVAILABLE = True
    logger.info("✓ ib_insync library available - real IBKR testing enabled")
except ImportError:
    IB_INSYNC_AVAILABLE = False
    logger.warning("⚠ ib_insync not available - simulation mode only")

# Import our adapters with proper path setup
import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Add IB API path for better compatibility
ibapi_path = r"C:\TWS API\source\pythonclient"
if os.path.exists(ibapi_path):
    sys.path.insert(0, ibapi_path)
    logger.info(f"✓ Added IB API path: {ibapi_path}")
else:
    logger.warning(f"⚠ IB API path not found: {ibapi_path}")

# Simple config classes for testing
class IBPaperConfig:
    NAME = "IB_PAPER"
    PORT = 7497
    ACCOUNT_ID = "DUK221396"
    HOST = "127.0.0.1"
    CLIENT_ID = 0
    VENUE = "IB"

class IBLiveConfig:
    NAME = "IB_LIVE"
    PORT = 7496
    ACCOUNT_ID = "U1234567"
    HOST = "127.0.0.1"
    CLIENT_ID = 102
    VENUE = "IB"


class QuickIBKRValidator:
    """Quick IBKR validation for essential functionality only"""
    
    def __init__(self):
        self.ib = None
        self.test_results = {
            "connection_test": {},
            "paper_trading_test": {},
            "basic_functionality": {},
            "summary": {}
        }
        self.start_time = None
        
    async def run_quick_validation(self) -> Dict[str, Any]:
        """Run quick IBKR validation tests"""
        logger.info("🚀 Starting Quick IBKR Validation Tests")
        logger.info("=" * 50)
        
        self.start_time = time.time()
        
        # Test 1: Basic Connection
        await self._test_basic_connection()
        
        # Test 2: Paper Trading Verification
        await self._test_paper_trading_config()
        
        # Test 3: Basic Market Data
        await self._test_basic_market_data()
        
        # Generate summary
        self._generate_summary()
        
        return self.test_results
    
    async def _test_basic_connection(self):
        """Test 1: Basic IBKR Connection"""
        logger.info("\n📡 Test 1: Basic IBKR Connection")
        logger.info("-" * 35)
        
        if IB_INSYNC_AVAILABLE:
            try:
                self.ib = IB()
                # Use user-specified client ID
                client_id = 0  # User specified Client ID
                
                # Connect with timeout
                await asyncio.wait_for(
                    self.ib.connectAsync('127.0.0.1', 7497, clientId=client_id),
                    timeout=10
                )
                
                self.test_results["connection_test"] = {
                    "status": "PASSED",
                    "message": "Successfully connected to IB Gateway/TWS",
                    "client_id": client_id,
                    "server_version": getattr(self.ib, 'serverVersion', 'Unknown')
                }
                logger.info("✓ Direct IB connection successful")
                
            except asyncio.TimeoutError:
                self.test_results["connection_test"] = {
                    "status": "FAILED",
                    "message": "Connection timeout - check if IB Gateway/TWS is running"
                }
                logger.error("✗ Connection timeout")
                
            except Exception as e:
                self.test_results["connection_test"] = {
                    "status": "FAILED",
                    "message": f"Connection failed: {str(e)}"
                }
                logger.error(f"✗ Connection failed: {e}")
        else:
            self.test_results["connection_test"] = {
                "status": "SKIPPED",
                "message": "ib_insync not available"
            }
            logger.warning("⚠ Skipping - ib_insync not available")
    
    async def _test_paper_trading_config(self):
        """Test 2: Paper Trading Configuration"""
        logger.info("\n📋 Test 2: Paper Trading Configuration")
        logger.info("-" * 35)
        
        try:
            config = IBPaperConfig()
            env_vars = {
                "IB_PAPER_TRADING": os.getenv("IB_PAPER_TRADING", "true"),
                "IB_GATEWAY_PORT": os.getenv("IB_GATEWAY_PORT", "7497"),
                "ENABLE_LIVE_TRADING": os.getenv("ENABLE_LIVE_TRADING", "false"),
                "ENABLE_PAPER_TRADING": os.getenv("ENABLE_PAPER_TRADING", "true")
            }
            
            paper_mode = env_vars["IB_PAPER_TRADING"].lower() == "true"
            live_disabled = env_vars["ENABLE_LIVE_TRADING"].lower() == "false"
            
            self.test_results["paper_trading_test"] = {
                "status": "PASSED" if paper_mode and live_disabled else "WARNING",
                "config_valid": True,
                "paper_trading_enabled": paper_mode,
                "live_trading_disabled": live_disabled,
                "environment_variables": env_vars
            }
            
            if paper_mode and live_disabled:
                logger.info("✓ Paper trading mode confirmed")
            else:
                logger.warning("⚠ Configuration may allow live trading")
                
        except Exception as e:
            self.test_results["paper_trading_test"] = {
                "status": "FAILED",
                "error": str(e)
            }
            logger.error(f"✗ Configuration test failed: {e}")
    
    async def _test_basic_market_data(self):
        """Test 3: Basic Market Data Access"""
        logger.info("\n📈 Test 3: Basic Market Data Access")
        logger.info("-" * 35)
        
        if self.ib and self.ib.isConnected():
            try:
                # Test simple contract details request
                stock = Stock('AAPL', 'SMART', 'USD')
                
                details = await asyncio.wait_for(
                    self.ib.reqContractDetailsAsync(stock),
                    timeout=10
                )\n                \n                if details:\n                    self.test_results[\"basic_functionality\"] = {\n                        \"status\": \"PASSED\",\n                        \"market_data_access\": True,\n                        \"contract_details_count\": len(details),\n                        \"sample_contract\": str(details[0].contract) if details else None\n                    }\n                    logger.info(f\"✓ Market data access confirmed - {len(details)} contract(s) found\")\n                else:\n                    self.test_results[\"basic_functionality\"] = {\n                        \"status\": \"WARNING\",\n                        \"market_data_access\": False,\n                        \"message\": \"No contract details returned\"\n                    }\n                    logger.warning(\"⚠ No contract details returned\")\n                    \n            except asyncio.TimeoutError:\n                self.test_results[\"basic_functionality\"] = {\n                    \"status\": \"FAILED\",\n                    \"error\": \"Market data request timeout\"\n                }\n                logger.error(\"✗ Market data request timeout\")\n                \n            except Exception as e:\n                self.test_results[\"basic_functionality\"] = {\n                    \"status\": \"FAILED\",\n                    \"error\": str(e)\n                }\n                logger.error(f\"✗ Market data test failed: {e}\")\n        else:\n            self.test_results[\"basic_functionality\"] = {\n                \"status\": \"SKIPPED\",\n                \"message\": \"No active IB connection\"\n            }\n            logger.warning(\"⚠ Skipping - no active IB connection\")\n    \n    def _generate_summary(self):\n        \"\"\"Generate test summary\"\"\"\n        logger.info(\"\\n📊 Quick Validation Summary\")\n        logger.info(\"=\" * 50)\n        \n        total_time = time.time() - self.start_time\n        \n        # Count results\n        tests = [self.test_results[\"connection_test\"], \n                self.test_results[\"paper_trading_test\"], \n                self.test_results[\"basic_functionality\"]]\n        \n        passed = sum(1 for t in tests if t.get(\"status\") == \"PASSED\")\n        failed = sum(1 for t in tests if t.get(\"status\") == \"FAILED\")\n        warnings = sum(1 for t in tests if t.get(\"status\") == \"WARNING\")\n        skipped = sum(1 for t in tests if t.get(\"status\") == \"SKIPPED\")\n        \n        summary = {\n            \"total_execution_time_seconds\": round(total_time, 2),\n            \"total_tests\": len(tests),\n            \"passed\": passed,\n            \"failed\": failed,\n            \"warnings\": warnings,\n            \"skipped\": skipped,\n            \"success_rate\": round((passed / len(tests) * 100), 1),\n            \"ibkr_ready\": failed == 0,\n            \"timestamp\": datetime.now().isoformat()\n        }\n        \n        self.test_results[\"summary\"] = summary\n        \n        # Print results\n        logger.info(f\"Total Tests: {len(tests)}\")\n        logger.info(f\"✓ Passed: {passed}\")\n        logger.info(f\"✗ Failed: {failed}\")\n        logger.info(f\"⚠ Warnings: {warnings}\")\n        logger.info(f\"⏭ Skipped: {skipped}\")\n        logger.info(f\"Success Rate: {summary['success_rate']}%\")\n        logger.info(f\"IBKR Ready: {'✓ YES' if summary['ibkr_ready'] else '✗ NO'}\")\n        logger.info(f\"Execution Time: {summary['total_execution_time_seconds']}s\")\n        \n        # Recommendations\n        if failed > 0:\n            logger.info(\"\\n🔧 Recommendations:\")\n            logger.info(\"  • Check IB Gateway/TWS is running\")\n            logger.info(\"  • Verify paper trading configuration\")\n            logger.info(\"  • Ensure API connections are enabled in IB\")\n    \n    async def cleanup(self):\n        \"\"\"Clean up connections\"\"\"\n        try:\n            if self.ib and self.ib.isConnected():\n                self.ib.disconnect()\n                logger.info(\"✓ IB connection closed\")\n        except Exception as e:\n            logger.error(f\"Cleanup error: {e}\")\n\n\nasync def main():\n    \"\"\"Main function for quick validation\"\"\"\n    validator = QuickIBKRValidator()\n    \n    try:\n        # Run with 2-minute timeout\n        results = await asyncio.wait_for(\n            validator.run_quick_validation(),\n            timeout=120\n        )\n        \n        # Save results\n        timestamp = datetime.now().strftime(\"%Y%m%d_%H%M%S\")\n        results_file = f\"quick_ibkr_validation_{timestamp}.json\"\n        \n        with open(results_file, 'w') as f:\n            json.dump(results, f, indent=2, default=str)\n        \n        logger.info(f\"\\n💾 Results saved to: {results_file}\")\n        \n        return results\n        \n    except asyncio.TimeoutError:\n        logger.error(\"\\n⏰ Quick validation timed out after 2 minutes\")\n        raise\n    except Exception as e:\n        logger.error(f\"Quick validation failed: {e}\")\n        raise\n    finally:\n        await validator.cleanup()\n\n\nif __name__ == \"__main__\":\n    asyncio.run(main())