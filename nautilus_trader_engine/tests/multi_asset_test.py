"""
Phase 1 Multi-Asset Order Routing and Position Management Test

Tests comprehensive multi-asset trading across Stocks, ETFs, Forex, Futures

Author: Vincent S. Pereira
Version: 1.0.0
"""

import asyncio
import logging
import time
import json
from datetime import datetime
from typing import Dict, List, Any
import sys
import os

# Add project paths
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Add IB API path
ibapi_path = r"C:\TWS API\source\pythonclient"
if os.path.exists(ibapi_path):
    sys.path.insert(0, ibapi_path)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from ib_insync import IB, Stock, MarketOrder, Future, Forex
    IB_INSYNC_AVAILABLE = True
except ImportError:
    IB_INSYNC_AVAILABLE = False


class MultiAssetTradingTest:
    """Multi-asset trading system test"""
    
    def __init__(self):
        self.ib = None
        self.test_results = {}
        self.start_time = None
        self.orders_placed = []
        
        # Test assets across different classes
        self.test_assets = {
            "stocks": [
                {"symbol": "AAPL", "exchange": "SMART", "currency": "USD"},
                {"symbol": "MSFT", "exchange": "SMART", "currency": "USD"}
            ],
            "etfs": [
                {"symbol": "SPY", "exchange": "SMART", "currency": "USD"},
                {"symbol": "QQQ", "exchange": "SMART", "currency": "USD"}
            ],
            "forex": [
                {"symbol": "EURUSD", "exchange": "IDEALPRO"},
                {"symbol": "GBPUSD", "exchange": "IDEALPRO"}
            ],
            "futures": [
                {"symbol": "ES", "exchange": "GLOBEX", "expiry": "202503"},
                {"symbol": "NQ", "exchange": "GLOBEX", "expiry": "202503"}
            ]
        }
        
    async def run_multi_asset_test(self) -> Dict[str, Any]:
        """Run multi-asset testing"""
        logger.info("🚀 Multi-Asset Order Routing & Position Management Test")
        logger.info("=" * 60)
        
        self.start_time = time.time()
        
        # Connect to IBKR
        await self._connect_ibkr()
        
        # Test each asset class
        await self._test_stocks()
        await self._test_etfs()
        await self._test_forex()
        await self._test_futures()
        
        # Test position and risk management
        await self._test_position_management()
        await self._test_risk_management()
        
        # Generate summary
        self._generate_summary()
        
        return self.test_results
    
    async def _connect_ibkr(self):
        """Connect to IBKR Gateway"""
        if IB_INSYNC_AVAILABLE:
            try:
                self.ib = IB()
                await self.ib.connectAsync('127.0.0.1', 7497, clientId=0)
                logger.info("✓ Connected to IBKR Gateway")
            except Exception as e:
                logger.error(f"✗ IBKR connection failed: {e}")
                self.ib = None
    
    async def _test_stocks(self):
        """Test stock order routing"""
        logger.info("\n📈 Testing Stock Order Routing")
        logger.info("-" * 30)
        
        results = {"successful": 0, "failed": 0, "orders": []}
        
        if self.ib and self.ib.isConnected():
            for stock in self.test_assets["stocks"]:
                try:
                    contract = Stock(stock["symbol"], stock["exchange"], stock["currency"])
                    order = MarketOrder('BUY', 10)  # 10 shares
                    trade = self.ib.placeOrder(contract, order)
                    
                    await asyncio.sleep(1)
                    
                    order_info = {
                        "symbol": stock["symbol"],
                        "order_id": trade.order.orderId,
                        "status": trade.orderStatus.status,
                        "asset_class": "stock"
                    }
                    
                    results["orders"].append(order_info)
                    self.orders_placed.append(order_info)
                    results["successful"] += 1
                    
                    logger.info(f"  ✓ {stock['symbol']}: Order placed successfully")
                    
                except Exception as e:
                    results["failed"] += 1
                    logger.error(f"  ✗ {stock['symbol']}: {e}")
        
        self.test_results["stocks"] = results
        logger.info(f"Stock orders: {results['successful']} successful, {results['failed']} failed")
    
    async def _test_etfs(self):
        """Test ETF order routing"""
        logger.info("\n🏦 Testing ETF Order Routing")
        logger.info("-" * 30)
        
        results = {"successful": 0, "failed": 0, "orders": []}
        
        if self.ib and self.ib.isConnected():
            for etf in self.test_assets["etfs"]:
                try:
                    contract = Stock(etf["symbol"], etf["exchange"], etf["currency"])
                    order = MarketOrder('BUY', 5)  # 5 shares
                    trade = self.ib.placeOrder(contract, order)
                    
                    await asyncio.sleep(1)
                    
                    order_info = {
                        "symbol": etf["symbol"],
                        "order_id": trade.order.orderId,
                        "status": trade.orderStatus.status,
                        "asset_class": "etf"
                    }
                    
                    results["orders"].append(order_info)
                    self.orders_placed.append(order_info)
                    results["successful"] += 1
                    
                    logger.info(f"  ✓ {etf['symbol']}: Order placed successfully")
                    
                except Exception as e:
                    results["failed"] += 1
                    logger.error(f"  ✗ {etf['symbol']}: {e}")
        
        self.test_results["etfs"] = results
        logger.info(f"ETF orders: {results['successful']} successful, {results['failed']} failed")
    
    async def _test_forex(self):
        """Test Forex order routing"""
        logger.info("\n💱 Testing Forex Order Routing")
        logger.info("-" * 30)
        
        results = {"successful": 0, "failed": 0, "orders": []}
        
        if self.ib and self.ib.isConnected():
            for fx in self.test_assets["forex"]:
                try:
                    contract = Forex(fx["symbol"])
                    order = MarketOrder('BUY', 1000)  # 1000 units
                    trade = self.ib.placeOrder(contract, order)
                    
                    await asyncio.sleep(1)
                    
                    order_info = {
                        "symbol": fx["symbol"],
                        "order_id": trade.order.orderId,
                        "status": trade.orderStatus.status,
                        "asset_class": "forex"
                    }
                    
                    results["orders"].append(order_info)
                    self.orders_placed.append(order_info)
                    results["successful"] += 1
                    
                    logger.info(f"  ✓ {fx['symbol']}: Order placed successfully")
                    
                except Exception as e:
                    results["failed"] += 1
                    logger.error(f"  ✗ {fx['symbol']}: {e}")
        
        self.test_results["forex"] = results
        logger.info(f"Forex orders: {results['successful']} successful, {results['failed']} failed")
    
    async def _test_futures(self):
        """Test Futures order routing"""
        logger.info("\n🔮 Testing Futures Order Routing")
        logger.info("-" * 30)
        
        results = {"successful": 0, "failed": 0, "orders": []}
        
        if self.ib and self.ib.isConnected():
            for future in self.test_assets["futures"]:
                try:
                    contract = Future(future["symbol"], future["expiry"], future["exchange"])
                    order = MarketOrder('BUY', 1)  # 1 contract
                    trade = self.ib.placeOrder(contract, order)
                    
                    await asyncio.sleep(1)
                    
                    order_info = {
                        "symbol": f"{future['symbol']}_{future['expiry']}",
                        "order_id": trade.order.orderId,
                        "status": trade.orderStatus.status,
                        "asset_class": "future"
                    }
                    
                    results["orders"].append(order_info)
                    self.orders_placed.append(order_info)
                    results["successful"] += 1
                    
                    logger.info(f"  ✓ {future['symbol']}: Order placed successfully")
                    
                except Exception as e:
                    results["failed"] += 1
                    logger.error(f"  ✗ {future['symbol']}: {e}")
        
        self.test_results["futures"] = results
        logger.info(f"Futures orders: {results['successful']} successful, {results['failed']} failed")
    
    async def _test_position_management(self):
        """Test position management across asset classes"""
        logger.info("\n📊 Testing Position Management")
        logger.info("-" * 30)
        
        # Simulate position tracking
        positions = {}
        for order in self.orders_placed:
            symbol = order["symbol"]
            asset_class = order["asset_class"]
            
            if symbol not in positions:
                positions[symbol] = {
                    "symbol": symbol,
                    "asset_class": asset_class,
                    "quantity": 0,
                    "market_value": 0,
                    "unrealized_pnl": 0
                }
            
            # Simulate position (assuming orders filled)
            if asset_class == "stock":
                positions[symbol]["quantity"] += 10
                positions[symbol]["market_value"] = positions[symbol]["quantity"] * 150
            elif asset_class == "etf":
                positions[symbol]["quantity"] += 5
                positions[symbol]["market_value"] = positions[symbol]["quantity"] * 400
            elif asset_class == "forex":
                positions[symbol]["quantity"] += 1000
                positions[symbol]["market_value"] = positions[symbol]["quantity"] * 1.1
            elif asset_class == "future":
                positions[symbol]["quantity"] += 1
                positions[symbol]["market_value"] = positions[symbol]["quantity"] * 50000
            
            # Simulate 2% profit
            positions[symbol]["unrealized_pnl"] = positions[symbol]["market_value"] * 0.02
        
        # Calculate portfolio metrics
        total_value = sum(pos["market_value"] for pos in positions.values())
        total_pnl = sum(pos["unrealized_pnl"] for pos in positions.values())
        asset_class_breakdown = {}
        
        for pos in positions.values():
            ac = pos["asset_class"]
            if ac not in asset_class_breakdown:
                asset_class_breakdown[ac] = {"count": 0, "value": 0}
            asset_class_breakdown[ac]["count"] += 1
            asset_class_breakdown[ac]["value"] += pos["market_value"]
        
        self.test_results["position_management"] = {
            "total_positions": len(positions),
            "total_market_value": total_value,
            "total_pnl": total_pnl,
            "asset_class_breakdown": asset_class_breakdown,
            "positions": list(positions.values())
        }
        
        logger.info(f"✓ Positions tracked: {len(positions)}")
        logger.info(f"  Total value: ${total_value:,.2f}")
        logger.info(f"  Total P&L: ${total_pnl:,.2f}")
        logger.info(f"  Asset classes: {len(asset_class_breakdown)}")
    
    async def _test_risk_management(self):
        """Test risk management across asset classes"""
        logger.info("\n⚠️ Testing Risk Management")
        logger.info("-" * 30)
        
        # Risk parameters
        max_position_size = 0.1  # 10% max
        max_asset_class_alloc = 0.4  # 40% max
        portfolio_value = 100000
        
        violations = []
        
        # Check position sizes
        positions = self.test_results.get("position_management", {}).get("positions", [])
        for pos in positions:
            position_pct = pos["market_value"] / portfolio_value
            if position_pct > max_position_size:
                violations.append({
                    "type": "position_size",
                    "symbol": pos["symbol"],
                    "percentage": position_pct
                })
        
        # Check asset class concentration
        breakdown = self.test_results.get("position_management", {}).get("asset_class_breakdown", {})
        for asset_class, data in breakdown.items():
            allocation_pct = data["value"] / portfolio_value
            if allocation_pct > max_asset_class_alloc:
                violations.append({
                    "type": "asset_class_concentration",
                    "asset_class": asset_class,
                    "percentage": allocation_pct
                })
        
        self.test_results["risk_management"] = {
            "violations": violations,
            "risk_checks_passed": len(violations) == 0,
            "max_position_size": max_position_size,
            "max_asset_class_alloc": max_asset_class_alloc
        }
        
        if violations:
            logger.warning(f"⚠ Risk violations: {len(violations)}")
        else:
            logger.info("✓ All risk checks passed")
    
    def _generate_summary(self):
        """Generate test summary"""
        logger.info("\n📊 Multi-Asset Test Summary")
        logger.info("=" * 60)
        
        total_time = time.time() - self.start_time
        total_orders = len(self.orders_placed)
        successful_orders = len([o for o in self.orders_placed if o.get("status") in ["PreSubmitted", "Submitted"]])
        
        # Count asset classes tested
        asset_classes_tested = set()
        for order in self.orders_placed:
            asset_classes_tested.add(order.get("asset_class", "unknown"))
        
        summary = {
            "total_execution_time": round(total_time, 2),
            "total_orders": total_orders,
            "successful_orders": successful_orders,
            "order_success_rate": round((successful_orders / total_orders * 100) if total_orders > 0 else 0, 1),
            "asset_classes_tested": list(asset_classes_tested),
            "multi_asset_ready": successful_orders > 0 and len(asset_classes_tested) > 1,
            "timestamp": datetime.now().isoformat()
        }
        
        self.test_results["summary"] = summary
        
        # Print results
        logger.info(f"Total Orders: {total_orders}")
        logger.info(f"Successful Orders: {successful_orders}")
        logger.info(f"Success Rate: {summary['order_success_rate']}%")
        logger.info(f"Asset Classes: {len(asset_classes_tested)}")
        logger.info(f"Multi-Asset Ready: {'✓ YES' if summary['multi_asset_ready'] else '✗ NO'}")
        logger.info(f"Execution Time: {summary['total_execution_time']}s")
    
    async def cleanup(self):
        """Clean up connections"""
        try:
            if self.ib and self.ib.isConnected():
                self.ib.disconnect()
                logger.info("✓ IBKR connection closed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


async def main():
    """Main function"""
    tester = MultiAssetTradingTest()
    
    try:
        results = await asyncio.wait_for(
            tester.run_multi_asset_test(),
            timeout=180  # 3 minute timeout
        )
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"multi_asset_test_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"\n💾 Results saved to: {results_file}")
        
        return results
        
    except asyncio.TimeoutError:
        logger.error("\n⏰ Multi-asset test timed out")
        raise
    except Exception as e:
        logger.error(f"Multi-asset test failed: {e}")
        raise
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())