"""
Phase 1 End-to-End Pipeline Testing

Pipeline test: Data → Algorithm → Results → Kafka Logging

Author: Vincent S. Pereira
Version: 1.0.0
Phase: Phase 1 - Core System Validation & Hardening
"""

import asyncio
import logging
import time
import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any
import sys
import os

# Add project paths
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Add IB API path
ibapi_path = r"C:\TWS API\source\pythonclient"
if os.path.exists(ibapi_path):
    sys.path.insert(0, ibapi_path)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import components
try:
    from ib_insync import IB, Stock, MarketOrder
    IB_INSYNC_AVAILABLE = True
except ImportError:
    IB_INSYNC_AVAILABLE = False

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


class Phase1PipelineTest:
    """Phase 1 pipeline testing"""
    
    def __init__(self):
        self.ib = None
        self.test_results = {}
        self.start_time = None
        self.events_logged = []
        
    async def run_pipeline_test(self) -> Dict[str, Any]:
        """Run pipeline test"""
        logger.info("🚀 Phase 1 End-to-End Pipeline Test")
        logger.info("=" * 50)
        
        self.start_time = time.time()
        
        # Step 1: Data Ingestion
        await self._test_data_ingestion()
        
        # Step 2: Algorithm Execution
        await self._test_algorithm_execution()
        
        # Step 3: Order Routing
        await self._test_order_routing()
        
        # Step 4: Event Logging
        await self._test_event_logging()
        
        # Generate summary
        self._generate_summary()
        
        return self.test_results
    
    async def _test_data_ingestion(self):
        """Test data ingestion from multiple sources"""
        logger.info("\n📊 Step 1: Data Ingestion")
        logger.info("-" * 30)
        
        results = {}
        
        # IBKR real-time data
        if IB_INSYNC_AVAILABLE:
            try:
                self.ib = IB()
                await self.ib.connectAsync('127.0.0.1', 7497, clientId=0)
                
                contract = Stock('AAPL', 'SMART', 'USD')
                ticker = self.ib.reqMktData(contract, '', False, False)
                await asyncio.sleep(2)
                
                results["ibkr_data"] = {
                    "status": "PASSED",
                    "symbol": "AAPL",
                    "price": getattr(ticker, 'last', 0) or getattr(ticker, 'bid', 0)
                }
                logger.info("✓ IBKR real-time data retrieved")
                
                self.ib.cancelMktData(contract)
                
            except Exception as e:
                results["ibkr_data"] = {"status": "FAILED", "error": str(e)}
                logger.error(f"✗ IBKR data failed: {e}")
        
        # Yahoo Finance historical data
        if YFINANCE_AVAILABLE:
            try:
                ticker = yf.Ticker("AAPL")
                data = ticker.history(period="5d")
                
                results["yahoo_data"] = {
                    "status": "PASSED" if not data.empty else "FAILED",
                    "rows": len(data),
                    "latest_price": float(data['Close'].iloc[-1]) if not data.empty else None
                }
                logger.info(f"✓ Yahoo Finance data: {len(data)} rows")
                
            except Exception as e:
                results["yahoo_data"] = {"status": "FAILED", "error": str(e)}
                logger.error(f"✗ Yahoo Finance failed: {e}")
        
        self.test_results["data_ingestion"] = results
    
    async def _test_algorithm_execution(self):
        """Test algorithm execution with technical analysis"""
        logger.info("\n🧮 Step 2: Algorithm Execution")
        logger.info("-" * 30)
        
        try:
            # Generate test data
            np.random.seed(42)
            n = 100
            prices = 150 * np.exp(np.cumsum(np.random.normal(0.0001, 0.02, n)))
            
            data = pd.DataFrame({
                'close': prices,
                'volume': np.random.lognormal(12, 0.5, n)
            })
            
            # Calculate indicators
            data['sma_20'] = data['close'].rolling(20).mean()
            data['sma_50'] = data['close'].rolling(50).mean()
            data['rsi'] = self._calculate_rsi(data['close'])
            
            # Generate signals
            signals = []
            for i in range(50, len(data)):
                row = data.iloc[i]
                if row['sma_20'] > row['sma_50'] and row['rsi'] < 70:
                    signals.append({
                        'signal': 'BUY',
                        'price': row['close'],
                        'timestamp': datetime.now().isoformat()
                    })
                elif row['sma_20'] < row['sma_50'] and row['rsi'] > 30:
                    signals.append({
                        'signal': 'SELL',
                        'price': row['close'],
                        'timestamp': datetime.now().isoformat()
                    })
            
            self.trading_signals = signals[:3]  # Limit for testing
            
            self.test_results["algorithm_execution"] = {
                "status": "PASSED",
                "data_points": len(data),
                "signals_generated": len(signals),
                "test_signals": len(self.trading_signals)
            }
            logger.info(f"✓ Algorithm generated {len(signals)} signals")
            
        except Exception as e:
            self.test_results["algorithm_execution"] = {
                "status": "FAILED",
                "error": str(e)
            }
            logger.error(f"✗ Algorithm execution failed: {e}")
    
    async def _test_order_routing(self):
        """Test order routing through IBKR"""
        logger.info("\n📈 Step 3: Order Routing")
        logger.info("-" * 30)
        
        if self.ib and self.ib.isConnected():
            try:
                executed_orders = []
                
                for signal in getattr(self, 'trading_signals', []):
                    contract = Stock('AAPL', 'SMART', 'USD')
                    action = signal['signal']
                    quantity = 100  # Test quantity
                    
                    order = MarketOrder(action, quantity)
                    trade = self.ib.placeOrder(contract, order)
                    
                    await asyncio.sleep(1)
                    
                    executed_orders.append({
                        'action': action,
                        'quantity': quantity,
                        'order_id': trade.order.orderId,
                        'status': trade.orderStatus.status
                    })
                    
                    # Log event
                    self.events_logged.append({
                        'event_type': 'order_placed',
                        'timestamp': datetime.now().isoformat(),
                        'action': action,
                        'quantity': quantity,
                        'order_id': trade.order.orderId
                    })
                
                self.test_results["order_routing"] = {
                    "status": "PASSED",
                    "orders_executed": len(executed_orders),
                    "details": executed_orders
                }
                logger.info(f"✓ Executed {len(executed_orders)} orders")
                
            except Exception as e:
                self.test_results["order_routing"] = {
                    "status": "FAILED",
                    "error": str(e)
                }
                logger.error(f"✗ Order routing failed: {e}")
        else:
            self.test_results["order_routing"] = {
                "status": "SKIPPED",
                "message": "No IBKR connection"
            }
    
    async def _test_event_logging(self):
        """Test event logging (simulated Kafka)"""
        logger.info("\n📝 Step 4: Event Logging")
        logger.info("-" * 30)
        
        try:
            # Add pipeline events
            self.events_logged.extend([
                {
                    'event_type': 'pipeline_start',
                    'timestamp': datetime.now().isoformat(),
                    'test_id': 'phase1_pipeline'
                },
                {
                    'event_type': 'data_ingestion_complete',
                    'timestamp': datetime.now().isoformat(),
                    'sources': ['ibkr', 'yahoo']
                },
                {
                    'event_type': 'algorithm_complete',
                    'timestamp': datetime.now().isoformat(),
                    'signals': len(getattr(self, 'trading_signals', []))
                }
            ])
            
            # Save events to file (Kafka simulation)
            log_file = f"pipeline_events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(log_file, 'w') as f:
                json.dump(self.events_logged, f, indent=2)
            
            self.test_results["event_logging"] = {
                "status": "PASSED",
                "events_logged": len(self.events_logged),
                "log_file": log_file
            }
            logger.info(f"✓ Logged {len(self.events_logged)} events to {log_file}")
            
        except Exception as e:
            self.test_results["event_logging"] = {
                "status": "FAILED",
                "error": str(e)
            }
            logger.error(f"✗ Event logging failed: {e}")
    
    def _generate_summary(self):
        """Generate test summary"""
        logger.info("\n📊 Pipeline Test Summary")
        logger.info("=" * 50)
        
        total_time = time.time() - self.start_time
        
        # Count results
        all_statuses = []
        for category, tests in self.test_results.items():
            if isinstance(tests, dict):
                if "status" in tests:
                    all_statuses.append(tests["status"])
                else:
                    for test_name, result in tests.items():
                        if isinstance(result, dict) and "status" in result:
                            all_statuses.append(result["status"])
        
        passed = all_statuses.count("PASSED")
        failed = all_statuses.count("FAILED")
        skipped = all_statuses.count("SKIPPED")
        
        summary = {
            "total_execution_time": round(total_time, 2),
            "total_tests": len(all_statuses),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "success_rate": round((passed / len(all_statuses) * 100) if all_statuses else 0, 1),
            "pipeline_ready": failed == 0,
            "events_logged": len(self.events_logged),
            "timestamp": datetime.now().isoformat()
        }
        
        self.test_results["summary"] = summary
        
        # Print results
        logger.info(f"Total Tests: {len(all_statuses)}")
        logger.info(f"✓ Passed: {passed}")
        logger.info(f"✗ Failed: {failed}")
        logger.info(f"⏭ Skipped: {skipped}")
        logger.info(f"Success Rate: {summary['success_rate']}%")
        logger.info(f"Pipeline Ready: {'✓ YES' if summary['pipeline_ready'] else '✗ NO'}")
        logger.info(f"Events Logged: {summary['events_logged']}")
        logger.info(f"Execution Time: {summary['total_execution_time']}s")
    
    def _calculate_rsi(self, prices, period=14):
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    async def cleanup(self):
        """Clean up connections"""
        try:
            if self.ib and self.ib.isConnected():
                self.ib.disconnect()
                logger.info("✓ IB connection closed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


async def main():
    """Main function"""
    tester = Phase1PipelineTest()
    
    try:
        results = await asyncio.wait_for(
            tester.run_pipeline_test(),
            timeout=120  # 2 minute timeout
        )
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"phase1_pipeline_test_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"\n💾 Results saved to: {results_file}")
        
        return results
        
    except asyncio.TimeoutError:
        logger.error("\n⏰ Pipeline test timed out")
        raise
    except Exception as e:
        logger.error(f"Pipeline test failed: {e}")
        raise
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())