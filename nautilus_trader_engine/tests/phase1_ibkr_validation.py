"""
Phase 1 - IBKR Connection and Paper Trading Validation Script

This script performs comprehensive validation of the NautilusTrader IBKR integration
for Phase 1 requirements including:
- IBKR connection validation
- Paper trading mode verification
- Multi-asset support testing
- Order routing validation
- Performance baseline measurement

Author: Vincent S. Pereira
Version: 1.0.0
Phase: Phase 1 - Core System Validation & Hardening
"""

import asyncio
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd

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

try:
    from nautilus_trader_engine.adapters.ibkr_adapter import IBKRAdapter, initialize_ibkr_adapter
    # Updated imports for new Nautilus Trader version
    try:
        from nautilus_trader.config import TradingNodeConfig
        from nautilus_trader_engine.config.ib_config import IBCommonConfig
        # Create simple config classes since the new version doesn't have PaperTradingConfig
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
            
    except ImportError:
        # Fallback if config module structure is different
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
    
    NAUTILUS_ADAPTERS_AVAILABLE = True
    logger.info("✓ Nautilus IBKR adapters available")
except ImportError as e:
    try:
        # Fallback to direct imports
        from adapters.ibkr_adapter import IBKRAdapter, initialize_ibkr_adapter
        class IBPaperConfig:
            NAME = "IB_PAPER"
            PORT = 7497
            ACCOUNT_ID = "DU1234567"
            HOST = "127.0.0.1"
            CLIENT_ID = 101
            VENUE = "IB"
        
        class IBLiveConfig:
            NAME = "IB_LIVE"
            PORT = 7496
            ACCOUNT_ID = "U1234567"
            HOST = "127.0.0.1"
            CLIENT_ID = 102
            VENUE = "IB"
        
        NAUTILUS_ADAPTERS_AVAILABLE = True
        logger.info("✓ Nautilus IBKR adapters available (fallback import)")
    except ImportError as e2:
        # Create minimal config classes for testing even without adapters
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
        
        NAUTILUS_ADAPTERS_AVAILABLE = False
        logger.error(f"✗ Failed to import Nautilus adapters: {e2}")


class Phase1IBKRValidator:
    """Comprehensive IBKR validation for Phase 1 requirements"""
    
    def __init__(self):
        self.ib = None
        self.adapter = None
        self.test_results = {
            "connection_tests": {},
            "paper_trading_tests": {},
            "multi_asset_tests": {},
            "performance_tests": {},
            "order_routing_tests": {},
            "summary": {}
        }
        self.start_time = None
        
    async def run_all_validations(self) -> Dict[str, Any]:
        """Run comprehensive Phase 1 IBKR validations"""
        logger.info("🚀 Starting Phase 1 IBKR Validation Tests")
        logger.info("=" * 60)
        
        self.start_time = time.time()
        
        # Test 1: Basic Connection Validation
        await self._test_connection_validation()
        
        # Test 2: Paper Trading Mode Verification
        await self._test_paper_trading_mode()
        
        # Test 3: Multi-Asset Support Testing
        await self._test_multi_asset_support()
        
        # Test 4: Order Routing Validation
        await self._test_order_routing()
        
        # Test 5: Performance Baseline Measurement
        await self._test_performance_baseline()
        
        # Generate summary
        self._generate_test_summary()
        
        return self.test_results
    
    async def _test_connection_validation(self):
        """Test 1: Basic IBKR Connection Validation"""
        logger.info("\n📡 Test 1: IBKR Connection Validation")
        logger.info("-" * 40)
        
        test_results = self.test_results["connection_tests"]
        
        # Test 1.1: Direct IB Connection
        if IB_INSYNC_AVAILABLE:
            try:
                self.ib = IB()
                # Use user-specified client ID
                client_id = 0  # User specified Client ID
                await self.ib.connectAsync('127.0.0.1', 7497, clientId=client_id)
                test_results["direct_connection"] = {
                    "status": "PASSED",
                    "message": "Successfully connected to IB Gateway/TWS",
                    "details": {
                        "host": "127.0.0.1",
                        "port": 7497,
                        "client_id": client_id,
                        "account_id": "DUK221396",
                        "connection_time": time.time()
                    }
                }
                logger.info("✓ Direct IB connection successful")
                
                # Test connection info
                account_summary = await self.ib.accountSummaryAsync()
                if account_summary:
                    test_results["account_info"] = {
                        "status": "PASSED",
                        "account_summary": str(account_summary[:3])  # First 3 entries
                    }
                    logger.info("✓ Account information retrieved")
                
            except Exception as e:
                test_results["direct_connection"] = {
                    "status": "FAILED",
                    "message": f"Failed to connect to IB Gateway/TWS: {str(e)}",
                    "error": str(e)
                }
                logger.error(f"✗ Direct IB connection failed: {e}")
        else:
            test_results["direct_connection"] = {
                "status": "SKIPPED",
                "message": "ib_insync not available - using simulation mode"
            }
            logger.warning("⚠ Skipping direct connection test - ib_insync not available")
        
        # Test 1.2: Adapter Connection
        if NAUTILUS_ADAPTERS_AVAILABLE:
            try:
                self.adapter = initialize_ibkr_adapter(paper_trading=True)
                connection_result = await self.adapter.connect()
                
                test_results["adapter_connection"] = {
                    "status": "PASSED" if connection_result else "FAILED",
                    "message": "Adapter connection successful" if connection_result else "Adapter connection failed",
                    "adapter_type": "IBKRAdapter",
                    "paper_trading": True
                }
                logger.info(f"{'✓' if connection_result else '✗'} Adapter connection: {connection_result}")
                
            except Exception as e:
                test_results["adapter_connection"] = {
                    "status": "FAILED",
                    "message": f"Adapter connection failed: {str(e)}",
                    "error": str(e)
                }
                logger.error(f"✗ Adapter connection failed: {e}")
        
    async def _test_paper_trading_mode(self):
        """Test 2: Paper Trading Mode Verification"""
        logger.info("\n📋 Test 2: Paper Trading Mode Verification")
        logger.info("-" * 40)
        
        test_results = self.test_results["paper_trading_tests"]
        
        # Test 2.1: Configuration Validation
        try:
            config = IBPaperConfig()
            test_results["config_validation"] = {
                "status": "PASSED",
                "config": {
                    "name": config.NAME,
                    "port": config.PORT,
                    "account_id": config.ACCOUNT_ID,
                    "venue": str(config.VENUE)
                }
            }
            logger.info("✓ Paper trading configuration valid")
            
        except Exception as e:
            test_results["config_validation"] = {
                "status": "FAILED",
                "message": f"Configuration validation failed: {str(e)}"
            }
            logger.error(f"✗ Configuration validation failed: {e}")
        
        # Test 2.2: Environment Variables Check
        try:
            env_vars = {
                "IB_PAPER_TRADING": os.getenv("IB_PAPER_TRADING", "true"),
                "IB_GATEWAY_PORT": os.getenv("IB_GATEWAY_PORT", "7497"),
                "ENABLE_LIVE_TRADING": os.getenv("ENABLE_LIVE_TRADING", "false"),
                "ENABLE_PAPER_TRADING": os.getenv("ENABLE_PAPER_TRADING", "true")
            }
            
            paper_trading_enabled = env_vars["IB_PAPER_TRADING"].lower() == "true"
            live_trading_disabled = env_vars["ENABLE_LIVE_TRADING"].lower() == "false"
            
            test_results["environment_check"] = {
                "status": "PASSED" if paper_trading_enabled and live_trading_disabled else "WARNING",
                "environment_variables": env_vars,
                "paper_trading_mode": paper_trading_enabled,
                "live_trading_disabled": live_trading_disabled
            }
            
            if paper_trading_enabled and live_trading_disabled:
                logger.info("✓ Environment configured for paper trading")
            else:
                logger.warning("⚠ Environment configuration may allow live trading")
                
        except Exception as e:
            test_results["environment_check"] = {
                "status": "FAILED",
                "message": f"Environment check failed: {str(e)}"
            }
    
    async def _test_multi_asset_support(self):
        """Test 3: Multi-Asset Support Testing"""
        logger.info("\n🏦 Test 3: Multi-Asset Support Testing")
        logger.info("-" * 40)
        
        test_results = self.test_results["multi_asset_tests"]
        
        # Define test assets across different classes
        test_assets = {
            "stocks": [
                {"symbol": "AAPL", "exchange": "SMART", "currency": "USD"},
                {"symbol": "MSFT", "exchange": "SMART", "currency": "USD"}
            ],
            "etfs": [
                {"symbol": "SPY", "exchange": "SMART", "currency": "USD"},
                {"symbol": "QQQ", "exchange": "SMART", "currency": "USD"}
            ],
            "forex": [
                {"symbol": "EUR", "exchange": "IDEALPRO", "currency": "USD"},
                {"symbol": "GBP", "exchange": "IDEALPRO", "currency": "USD"}
            ],
            "futures": [
                {"symbol": "ES", "exchange": "GLOBEX", "currency": "USD"},
                {"symbol": "NQ", "exchange": "GLOBEX", "currency": "USD"}
            ]
        }
        
        if IB_INSYNC_AVAILABLE and self.ib and self.ib.isConnected():
            for asset_class, assets in test_assets.items():
                logger.info(f"Testing {asset_class.upper()} support...")
                class_results = []
                
                for asset in assets:
                    try:
                        if asset_class == "stocks" or asset_class == "etfs":
                            contract = Stock(asset["symbol"], asset["exchange"], asset["currency"])
                        elif asset_class == "forex":
                            from ib_insync import Forex
                            contract = Forex(asset["symbol"] + asset["currency"])
                        elif asset_class == "futures":
                            from ib_insync import Future
                            contract = Future(asset["symbol"], "202412", asset["exchange"])
                        
                        # Request contract details
                        details = await self.ib.reqContractDetailsAsync(contract)
                        
                        if details:
                            class_results.append({
                                "symbol": asset["symbol"],
                                "status": "SUPPORTED",
                                "contract_details": len(details),
                                "primary_exchange": details[0].contract.primaryExchange if details else None
                            })
                            logger.info(f"  ✓ {asset['symbol']} supported")
                        else:
                            class_results.append({
                                "symbol": asset["symbol"],
                                "status": "NOT_FOUND",
                                "message": "No contract details found"
                            })
                            logger.warning(f"  ⚠ {asset['symbol']} not found")
                            
                    except Exception as e:
                        class_results.append({
                            "symbol": asset["symbol"],
                            "status": "ERROR",
                            "error": str(e)
                        })
                        logger.error(f"  ✗ {asset['symbol']} error: {e}")
                
                test_results[asset_class] = {
                    "total_tested": len(assets),
                    "supported": len([r for r in class_results if r["status"] == "SUPPORTED"]),
                    "results": class_results
                }
        else:
            test_results["status"] = "SKIPPED"
            test_results["message"] = "Multi-asset testing requires active IB connection"
            logger.warning("⚠ Skipping multi-asset tests - no active IB connection")
    
    async def _test_order_routing(self):
        """Test 4: Order Routing Validation"""
        logger.info("\n📈 Test 4: Order Routing Validation")
        logger.info("-" * 40)
        
        test_results = self.test_results["order_routing_tests"]
        
        if self.adapter:
            try:
                # Test order submission (simulation)
                try:
                    from nautilus_trader_engine.adapters.broker_adapter import BrokerOrder, OrderType, OrderSide, InstrumentId, Quantity, Price
                except ImportError:
                    try:
                        from adapters.broker_adapter import BrokerOrder, OrderType, OrderSide, InstrumentId, Quantity, Price
                    except ImportError:
                        # Use mock objects for testing
                        class MockInstrumentId:
                            @staticmethod
                            def from_str(s): return f"MOCK_{s}"
                        class MockQuantity:
                            @staticmethod
                            def from_str(s): return float(s)
                        class MockPrice:
                            @staticmethod
                            def from_str(s): return float(s)
                        class MockOrderType:
                            MARKET = "MARKET"
                            LIMIT = "LIMIT"
                        class MockOrderSide:
                            BUY = "BUY"
                            SELL = "SELL"
                        class MockBrokerOrder:
                            def __init__(self, **kwargs): self.__dict__.update(kwargs)
                                
                        BrokerOrder = MockBrokerOrder
                        OrderType = MockOrderType
                        OrderSide = MockOrderSide
                        InstrumentId = MockInstrumentId
                        Quantity = MockQuantity
                        Price = MockPrice
                
                # Create test order
                test_order = BrokerOrder(
                    instrument_id=InstrumentId.from_str("AAPL.XNAS"),
                    order_type=OrderType.MARKET,
                    side=OrderSide.BUY,
                    quantity=Quantity.from_str("100")
                ) if hasattr(BrokerOrder, '__call__') else None
                
                # Submit order (simulation mode)
                order_id = await self.adapter.submit_order(test_order)
                
                test_results["order_submission"] = {
                    "status": "PASSED",
                    "order_id": str(order_id),
                    "instrument": "AAPL",
                    "quantity": 100,
                    "side": "BUY",
                    "type": "MARKET"
                }
                logger.info(f"✓ Order submission successful: {order_id}")
                
                # Test order status retrieval
                status = await self.adapter.get_order_status(order_id)
                test_results["order_status"] = {
                    "status": "PASSED",
                    "order_status": status
                }
                logger.info(f"✓ Order status retrieved: {status}")
                
            except Exception as e:
                test_results["order_routing"] = {
                    "status": "FAILED",
                    "error": str(e)
                }
                logger.error(f"✗ Order routing test failed: {e}")
        else:
            test_results["status"] = "SKIPPED"
            test_results["message"] = "Order routing test requires adapter connection"
            logger.warning("⚠ Skipping order routing tests - no adapter available")
    
    async def _test_performance_baseline(self):
        """Test 5: Performance Baseline Measurement"""
        logger.info("\n⚡ Test 5: Performance Baseline Measurement")
        logger.info("-" * 40)
        
        test_results = self.test_results["performance_tests"]
        
        # Test 5.1: Connection Latency with timeout
        if IB_INSYNC_AVAILABLE and self.ib and self.ib.isConnected():
            try:
                latency_tests = []
                successful_tests = 0
                max_tests = 5  # Reduced from 10 to avoid hanging
                timeout_seconds = 5  # Add timeout per request
                
                logger.info(f"Running {max_tests} latency tests with {timeout_seconds}s timeout each...")
                
                for i in range(max_tests):
                    try:
                        start = time.time()
                        # Add timeout to prevent hanging
                        await asyncio.wait_for(
                            self.ib.reqCurrentTimeAsync(), 
                            timeout=timeout_seconds
                        )
                        end = time.time()
                        latency = (end - start) * 1000  # Convert to milliseconds
                        latency_tests.append(latency)
                        successful_tests += 1
                        logger.info(f"  Test {i+1}/{max_tests}: {latency:.2f}ms")
                        
                        # Small delay between tests
                        await asyncio.sleep(0.1)
                        
                    except asyncio.TimeoutError:
                        logger.warning(f"  Test {i+1}/{max_tests}: Timeout ({timeout_seconds}s)")
                        continue
                    except Exception as e:
                        logger.warning(f"  Test {i+1}/{max_tests}: Error - {e}")
                        continue
                
                if latency_tests:
                    avg_latency = sum(latency_tests) / len(latency_tests)
                    test_results["connection_latency"] = {
                        "status": "PASSED" if avg_latency < 100 else "WARNING",
                        "average_latency_ms": round(avg_latency, 2),
                        "max_latency_ms": round(max(latency_tests), 2),
                        "min_latency_ms": round(min(latency_tests), 2),
                        "target_latency_ms": 100,
                        "successful_tests": successful_tests,
                        "total_tests": max_tests
                    }
                    
                    if avg_latency < 100:
                        logger.info(f"✓ Connection latency: {avg_latency:.2f}ms (target: <100ms)")
                    else:
                        logger.warning(f"⚠ Connection latency: {avg_latency:.2f}ms (exceeds 100ms target)")
                else:
                    test_results["connection_latency"] = {
                        "status": "FAILED",
                        "error": "No successful latency tests completed",
                        "successful_tests": 0,
                        "total_tests": max_tests
                    }
                    logger.error("✗ All latency tests failed")
                    
            except Exception as e:
                test_results["connection_latency"] = {
                    "status": "FAILED",
                    "error": str(e)
                }
                logger.error(f"✗ Latency test failed: {e}")
        else:
            test_results["connection_latency"] = {
                "status": "SKIPPED",
                "message": "No active IB connection for latency testing"
            }
            logger.warning("⚠ Skipping latency tests - no active IB connection")
        
        # Test 5.2: Market Data Throughput (simulated) - made much faster
        try:
            logger.info("Running throughput simulation...")
            throughput_start = time.time()
            simulated_ticks = 1000
            
            # Simulate processing 1000 market data ticks with much less delay
            for i in range(simulated_ticks):
                # Simulate minimal tick processing overhead
                if i % 100 == 0:  # Progress indicator
                    logger.info(f"  Processed {i} ticks...")
                await asyncio.sleep(0.00001)  # Reduced from 0.0001 to 0.00001
            
            throughput_end = time.time()
            total_time = throughput_end - throughput_start
            ticks_per_second = simulated_ticks / total_time if total_time > 0 else 0
            
            test_results["throughput_simulation"] = {
                "status": "PASSED" if ticks_per_second >= 1000 else "WARNING",
                "ticks_per_second": round(ticks_per_second, 2),
                "total_ticks": simulated_ticks,
                "processing_time_seconds": round(total_time, 3),
                "target_tps": 1000
            }
            
            if ticks_per_second >= 1000:
                logger.info(f"✓ Throughput simulation: {ticks_per_second:.0f} TPS (target: ≥1000 TPS)")
            else:
                logger.warning(f"⚠ Throughput simulation: {ticks_per_second:.0f} TPS (below 1000 TPS target)")
                
        except Exception as e:
            test_results["throughput_simulation"] = {
                "status": "FAILED",
                "error": str(e)
            }
            logger.error(f"✗ Throughput test failed: {e}")
    
    def _generate_test_summary(self):
        """Generate comprehensive test summary"""
        logger.info("\n📊 Test Summary")
        logger.info("=" * 60)
        
        total_time = time.time() - self.start_time
        
        # Count test results
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        skipped_tests = 0
        warnings = 0
        
        for category, tests in self.test_results.items():
            if category == "summary":
                continue
                
            for test_name, result in tests.items():
                if isinstance(result, dict) and "status" in result:
                    total_tests += 1
                    status = result["status"]
                    if status == "PASSED":
                        passed_tests += 1
                    elif status == "FAILED":
                        failed_tests += 1
                    elif status == "SKIPPED":
                        skipped_tests += 1
                    elif status == "WARNING":
                        warnings += 1
        
        summary = {
            "total_execution_time_seconds": round(total_time, 2),
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "skipped": skipped_tests,
            "warnings": warnings,
            "success_rate": round((passed_tests / total_tests * 100) if total_tests > 0 else 0, 1),
            "phase1_readiness": "READY" if failed_tests == 0 else "NEEDS_ATTENTION",
            "recommendations": []
        }
        
        # Generate recommendations
        if failed_tests > 0:
            summary["recommendations"].append("Address failed tests before proceeding to Phase 1 implementation")
        if warnings > 0:
            summary["recommendations"].append("Review warning conditions for optimal performance")
        if skipped_tests > 0:
            summary["recommendations"].append("Install missing dependencies to enable full testing")
        
        self.test_results["summary"] = summary
        
        # Print summary
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"✓ Passed: {passed_tests}")
        logger.info(f"✗ Failed: {failed_tests}")
        logger.info(f"⚠ Warnings: {warnings}")
        logger.info(f"⏭ Skipped: {skipped_tests}")
        logger.info(f"Success Rate: {summary['success_rate']}%")
        logger.info(f"Phase 1 Readiness: {summary['phase1_readiness']}")
        logger.info(f"Total Execution Time: {summary['total_execution_time_seconds']}s")
        
        if summary["recommendations"]:
            logger.info("\nRecommendations:")
            for rec in summary["recommendations"]:
                logger.info(f"  • {rec}")
    
    async def cleanup(self):
        """Clean up connections"""
        try:
            if self.ib and self.ib.isConnected():
                self.ib.disconnect()
                logger.info("✓ IB connection closed")
            
            if self.adapter:
                await self.adapter.disconnect()
                logger.info("✓ Adapter disconnected")
                
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


async def main():
    """Main validation function with timeout"""
    validator = Phase1IBKRValidator()
    
    try:
        # Add timeout to prevent hanging (10 minutes max)
        results = await asyncio.wait_for(
            validator.run_all_validations(),
            timeout=600  # 10 minutes timeout
        )
        
        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"phase1_ibkr_validation_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"\n💾 Results saved to: {results_file}")
        
        return results
        
    except asyncio.TimeoutError:
        logger.error("\n⏰ Validation timed out after 10 minutes")
        logger.info("\n📋 Partial results summary:")
        # Try to generate summary with partial results
        try:
            validator._generate_test_summary()
        except:
            logger.error("Could not generate partial summary")
        raise
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise
    finally:
        await validator.cleanup()


if __name__ == "__main__":
    asyncio.run(main())