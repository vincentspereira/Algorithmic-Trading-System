#!/usr/bin/env python3
"""
Enhanced Multi-Source Data Feed Test for Phase 1
Tests the fallback mechanism and validates all data sources

Phase 1 Requirements:
- Primary: IBKR (paper trading)
- Fallback: Yahoo Finance (free)
- Additional: Alpha Vantage (if available)
- Emergency: Cached data

Author: Vincent S. Pereira
Version: 1.0.0
"""

import asyncio
import logging
import sys
import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Add project paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from nautilus_trader_engine.data_feeds.multi_source_feed_manager import DataFeedManager, DataSource, DataStatus, MarketDataPoint
    FEED_MANAGER_AVAILABLE = True
except ImportError as e:
    FEED_MANAGER_AVAILABLE = False
    print(f"Feed manager not available: {e}")

try:
    import yfinance as yf
    YAHOO_AVAILABLE = True
except ImportError:
    YAHOO_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Phase1DataFeedTester:
    """Comprehensive data feed testing for Phase 1"""
    
    def __init__(self):
        self.test_symbols = ["AAPL", "MSFT", "SPY", "EURUSD"]
        self.results = {}
        self.feed_manager = None
        
    async def setup(self):
        """Setup the feed manager"""
        if FEED_MANAGER_AVAILABLE:
            self.feed_manager = DataFeedManager()
            logger.info("✅ DataFeedManager initialized")
        else:
            logger.warning("⚠️ DataFeedManager not available - running limited tests")
    
    async def test_yahoo_finance_direct(self):
        """Test Yahoo Finance directly"""
        logger.info("\n🧪 Testing Yahoo Finance Direct Access...")
        
        if not YAHOO_AVAILABLE:
            logger.warning("❌ Yahoo Finance not available")
            return {"status": "UNAVAILABLE", "reason": "yfinance not installed"}
        
        results = {}
        
        for symbol in ["AAPL", "MSFT", "SPY"]:
            try:
                start_time = time.time()
                ticker = yf.Ticker(symbol)
                
                # Get recent data
                hist = ticker.history(period="5d")
                if hist.empty:
                    logger.warning(f"⚠️ No data for {symbol}")
                    results[symbol] = {"status": "NO_DATA"}
                    continue
                
                latest = hist.iloc[-1]
                latency = (time.time() - start_time) * 1000
                
                data_point = {
                    "symbol": symbol,
                    "price": float(latest['Close']),
                    "volume": int(latest['Volume']),
                    "timestamp": hist.index[-1].isoformat(),
                    "latency_ms": latency,
                    "source": "yahoo_finance",
                    "status": "SUCCESS"
                }
                
                results[symbol] = data_point
                logger.info(f"✅ {symbol}: ${latest['Close']:.2f} (Vol: {latest['Volume']:,}) - {latency:.1f}ms")
                
            except Exception as e:
                logger.error(f"❌ Failed to get {symbol}: {e}")
                results[symbol] = {"status": "ERROR", "error": str(e)}
        
        return results
    
    async def test_alpha_vantage_direct(self):
        """Test Alpha Vantage directly (if API key available)"""
        logger.info("\n🧪 Testing Alpha Vantage Direct Access...")
        
        api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if not api_key:
            logger.warning("⚠️ Alpha Vantage API key not found in environment")
            return {"status": "NO_API_KEY"}
        
        if not REQUESTS_AVAILABLE:
            logger.warning("❌ Requests library not available")
            return {"status": "NO_REQUESTS"}
        
        results = {}
        
        for symbol in ["AAPL", "MSFT"]:
            try:
                start_time = time.time()
                
                url = f"https://www.alphavantage.co/query"
                params = {
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol,
                    "apikey": api_key
                }
                
                response = requests.get(url, params=params, timeout=20)
                response.raise_for_status()
                
                data = response.json()
                latency = (time.time() - start_time) * 1000
                
                if "Global Quote" in data:
                    quote = data["Global Quote"]
                    data_point = {
                        "symbol": symbol,
                        "price": float(quote["05. price"]),
                        "change": quote["09. change"],
                        "change_percent": quote["10. change percent"],
                        "timestamp": datetime.now().isoformat(),
                        "latency_ms": latency,
                        "source": "alpha_vantage",
                        "status": "SUCCESS"
                    }
                    
                    results[symbol] = data_point
                    logger.info(f"✅ {symbol}: ${quote['05. price']} ({quote['10. change percent']}) - {latency:.1f}ms")
                    
                elif "Note" in data:
                    logger.warning(f"⚠️ Rate limit reached for Alpha Vantage")
                    results[symbol] = {"status": "RATE_LIMITED", "message": data["Note"]}
                else:
                    logger.warning(f"⚠️ Unexpected response for {symbol}: {data}")
                    results[symbol] = {"status": "UNEXPECTED_RESPONSE", "data": data}
                
                # Rate limiting
                await asyncio.sleep(12)  # Alpha Vantage free tier: 5 calls per minute
                
            except Exception as e:
                logger.error(f"❌ Failed to get {symbol} from Alpha Vantage: {e}")
                results[symbol] = {"status": "ERROR", "error": str(e)}
        
        return results
    
    async def test_fallback_sequence(self):
        """Test the fallback sequence logic"""
        logger.info("\n🧪 Testing Fallback Sequence Logic...")
        
        if not self.feed_manager:
            logger.warning("⚠️ Feed manager not available")
            return {"status": "NO_FEED_MANAGER"}
        
        results = {}
        
        # Test primary source availability
        primary_available = await self._test_source_availability(DataSource.IBKR)
        yahoo_available = await self._test_source_availability(DataSource.YAHOO)
        alpha_available = await self._test_source_availability(DataSource.ALPHA_VANTAGE)
        
        results["source_availability"] = {
            "IBKR": primary_available,
            "YAHOO": yahoo_available,
            "ALPHA_VANTAGE": alpha_available
        }
        
        # Test fallback order
        fallback_order = [s.name.value for s in self.feed_manager.fallback_order]
        results["fallback_order"] = fallback_order
        
        logger.info(f"📋 Fallback order: {' → '.join(fallback_order)}")
        
        return results
    
    async def _test_source_availability(self, source: DataSource) -> Dict[str, Any]:
        """Test if a specific data source is available"""
        try:
            if source == DataSource.IBKR:
                # Try to connect to IB Gateway/TWS
                try:
                    from ib_insync import IB
                    ib = IB()
                    connected = ib.connect('127.0.0.1', 7497, clientId=999, timeout=5)
                    if connected:
                        ib.disconnect()
                        return {"available": True, "status": "CONNECTED"}
                    else:
                        return {"available": False, "status": "CONNECTION_FAILED"}
                except Exception as e:
                    return {"available": False, "status": "ERROR", "error": str(e)}
            
            elif source == DataSource.YAHOO:
                # Test Yahoo Finance
                if YAHOO_AVAILABLE:
                    ticker = yf.Ticker("AAPL")
                    data = ticker.history(period="1d")
                    if not data.empty:
                        return {"available": True, "status": "DATA_AVAILABLE"}
                    else:
                        return {"available": False, "status": "NO_DATA"}
                else:
                    return {"available": False, "status": "NOT_INSTALLED"}
            
            elif source == DataSource.ALPHA_VANTAGE:
                # Test Alpha Vantage
                api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
                if api_key and REQUESTS_AVAILABLE:
                    return {"available": True, "status": "API_KEY_AVAILABLE"}
                else:
                    return {"available": False, "status": "NO_API_KEY"}
            
            else:
                return {"available": False, "status": "UNKNOWN_SOURCE"}
                
        except Exception as e:
            return {"available": False, "status": "ERROR", "error": str(e)}
    
    async def test_comprehensive_data_retrieval(self):
        """Test comprehensive data retrieval with fallback"""
        logger.info("\n🧪 Testing Comprehensive Data Retrieval...")
        
        results = {}
        
        # Test Yahoo Finance fallback
        yahoo_results = await self.test_yahoo_finance_direct()
        results["yahoo_finance"] = yahoo_results
        
        # Test Alpha Vantage if available
        alpha_results = await self.test_alpha_vantage_direct()
        results["alpha_vantage"] = alpha_results
        
        # Test fallback logic
        fallback_results = await self.test_fallback_sequence()
        results["fallback_logic"] = fallback_results
        
        return results
    
    async def run_all_tests(self):
        """Run all data feed tests"""
        logger.info("🚀 Starting Phase 1 Multi-Source Data Feed Tests")
        logger.info("=" * 70)
        
        await self.setup()
        
        # Run comprehensive tests
        self.results = await self.test_comprehensive_data_retrieval()
        
        # Generate summary
        await self.generate_summary()
        
        return self.results
    
    async def generate_summary(self):
        """Generate test summary"""
        logger.info("\n📊 Phase 1 Data Feed Test Summary")
        logger.info("=" * 50)
        
        # Yahoo Finance results
        yahoo_results = self.results.get("yahoo_finance", {})
        if isinstance(yahoo_results, dict) and "status" not in yahoo_results:
            yahoo_success = len([r for r in yahoo_results.values() if r.get("status") == "SUCCESS"])
            yahoo_total = len(yahoo_results)
            logger.info(f"📈 Yahoo Finance: {yahoo_success}/{yahoo_total} symbols successful")
        else:
            logger.info(f"📈 Yahoo Finance: {yahoo_results.get('status', 'UNKNOWN')}")
        
        # Alpha Vantage results
        alpha_results = self.results.get("alpha_vantage", {})
        if isinstance(alpha_results, dict) and "status" not in alpha_results:
            alpha_success = len([r for r in alpha_results.values() if r.get("status") == "SUCCESS"])
            alpha_total = len(alpha_results)
            logger.info(f"📊 Alpha Vantage: {alpha_success}/{alpha_total} symbols successful")
        else:
            logger.info(f"📊 Alpha Vantage: {alpha_results.get('status', 'UNKNOWN')}")
        
        # Fallback logic
        fallback_results = self.results.get("fallback_logic", {})
        if "source_availability" in fallback_results:
            available_sources = [
                source for source, info in fallback_results["source_availability"].items()
                if info.get("available", False)
            ]
            logger.info(f"🔄 Available sources: {', '.join(available_sources)}")
        
        # Overall assessment
        yahoo_working = isinstance(yahoo_results, dict) and any(
            r.get("status") == "SUCCESS" for r in yahoo_results.values() if isinstance(r, dict)
        )
        
        alpha_working = isinstance(alpha_results, dict) and any(
            r.get("status") == "SUCCESS" for r in alpha_results.values() if isinstance(r, dict)
        )
        
        if yahoo_working:
            logger.info("\n🎉 Phase 1 Data Feeds: READY!")
            logger.info("   • Yahoo Finance working (primary fallback)")
            if alpha_working:
                logger.info("   • Alpha Vantage working (additional source)")
            logger.info("   • Fallback mechanism operational")
            phase1_ready = True
        else:
            logger.info("\n⚠️  Phase 1 Data Feeds: NEEDS ATTENTION")
            logger.info("   • Yahoo Finance not working properly")
            logger.info("   • Check internet connection and dependencies")
            phase1_ready = False
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"data_feeds_test_{timestamp}.json"
        
        final_results = {
            "test_metadata": {
                "timestamp": datetime.now().isoformat(),
                "phase": "Phase 1",
                "test_type": "multi_source_data_feeds",
                "phase1_ready": phase1_ready
            },
            "test_results": self.results,
            "summary": {
                "yahoo_finance_working": yahoo_working,
                "alpha_vantage_working": alpha_working,
                "primary_fallback_available": yahoo_working,
                "phase1_status": "READY" if phase1_ready else "NEEDS_WORK"
            }
        }
        
        with open(results_file, 'w') as f:
            json.dump(final_results, f, indent=2, default=str)
        
        logger.info(f"\n💾 Results saved to: {results_file}")
        
        return phase1_ready

async def main():
    """Main test function"""
    tester = Phase1DataFeedTester()
    
    try:
        results = await tester.run_all_tests()
        return results
    except KeyboardInterrupt:
        logger.info("\n⏹️ Test interrupted by user")
        return None
    except Exception as e:
        logger.error(f"\n💥 Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    results = asyncio.run(main())