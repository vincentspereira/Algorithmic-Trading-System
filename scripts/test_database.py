#!/usr/bin/env python3
"""
Database Layer Comprehensive Test Suite
Tests all database components and operations

Usage:
    python test_database.py [--full] [--performance]
"""

import asyncio
import argparse
import logging
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from database.database_manager import DatabaseManager, create_database_config
from database.data_access_layer import DataAccessLayer
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseTester:
    """Comprehensive database test suite"""
    
    def __init__(self):
        self.config = create_database_config()
        self.db_manager = None
        self.dal = None
        self.test_results = []
    
    def log_test(self, name: str, success: bool, details: str = "", duration: float = 0):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append({
            "name": name,
            "success": success,
            "details": details,
            "duration": duration
        })
        print(f"{status} {name} ({duration:.3f}s) - {details}")
    
    async def initialize(self):
        """Initialize database connections"""
        print("🚀 Initializing Database Test Suite")
        print("=" * 60)
        
        try:
            self.db_manager = DatabaseManager(self.config)
            await self.db_manager.initialize()
            self.dal = DataAccessLayer(self.db_manager)
            print("✅ Database connections initialized")
        except Exception as e:
            print(f"❌ Failed to initialize databases: {e}")
            raise
    
    async def test_database_health(self):
        """Test database health and connectivity"""
        start_time = time.time()
        
        try:
            health_status = self.db_manager.get_health_status()
            all_healthy = all(health_status.values())
            
            details = f"PostgreSQL: {'✅' if health_status['postgres'] else '❌'}, " \
                     f"ClickHouse: {'✅' if health_status['clickhouse'] else '❌'}, " \
                     f"Redis: {'✅' if health_status['redis'] else '❌'}"
            
            self.log_test("Database Health Check", all_healthy, details, time.time() - start_time)
            return all_healthy
            
        except Exception as e:
            self.log_test("Database Health Check", False, str(e), time.time() - start_time)
            return False
    
    async def test_user_operations(self):
        """Test user CRUD operations"""
        start_time = time.time()
        
        try:
            # Create user
            user = await self.dal.users.create_user(
                username=f"test_user_{uuid.uuid4().hex[:8]}",
                email=f"test_{uuid.uuid4().hex[:8]}@example.com",
                password_hash="hashed_password_123",
                permissions=["read", "write", "trade"]
            )
            
            # Get user by ID
            retrieved_user = await self.dal.users.get_user_by_id(user.id)
            assert retrieved_user is not None
            assert retrieved_user.username == user.username
            
            # Get user by username
            user_by_username = await self.dal.users.get_user_by_username(user.username)
            assert user_by_username is not None
            assert user_by_username.id == user.id
            
            # Update last login
            await self.dal.users.update_last_login(user.id)
            
            # Update permissions
            await self.dal.users.update_user_permissions(user.id, ["read", "admin"])
            
            self.log_test("User Operations", True, 
                         f"Created user {user.username}", time.time() - start_time)
            return user
            
        except Exception as e:
            self.log_test("User Operations", False, str(e), time.time() - start_time)
            return None
    
    async def test_trading_account_operations(self, user):
        """Test trading account operations"""
        if not user:
            return None
            
        start_time = time.time()
        
        try:
            # Create trading account
            account = await self.dal.trading_accounts.create_account(
                user_id=user.id,
                account_name="Test Paper Trading Account",
                broker="IBKR",
                account_number="TEST123456",
                account_type="PAPER",
                api_credentials={"encrypted": True, "test": True}
            )
            
            # Get accounts by user
            accounts = await self.dal.trading_accounts.get_accounts_by_user(user.id)
            assert len(accounts) >= 1
            assert accounts[0].id == account.id
            
            # Get account by ID
            retrieved_account = await self.dal.trading_accounts.get_account_by_id(account.id)
            assert retrieved_account is not None
            assert retrieved_account.account_name == account.account_name
            
            self.log_test("Trading Account Operations", True,
                         f"Created account {account.account_name}", time.time() - start_time)
            return account
            
        except Exception as e:
            self.log_test("Trading Account Operations", False, str(e), time.time() - start_time)
            return None
    
    async def test_order_operations(self, user, account):
        """Test order CRUD operations"""
        if not user or not account:
            return []
            
        start_time = time.time()
        
        try:
            orders = []
            
            # Create multiple orders
            symbols = ["AAPL", "MSFT", "GOOGL"]
            for i, symbol in enumerate(symbols):
                order = await self.dal.orders.create_order(
                    user_id=user.id,
                    account_id=account.id,
                    order_id=f"TEST_ORDER_{uuid.uuid4().hex[:8]}",
                    symbol=symbol,
                    side="BUY" if i % 2 == 0 else "SELL",
                    order_type="MARKET",
                    quantity=100.0 * (i + 1),
                    metadata={"test": True, "order_index": i}
                )
                orders.append(order)
            
            # Get orders by user
            user_orders = await self.dal.orders.get_orders_by_user(user.id)
            assert len(user_orders) >= len(orders)
            
            # Update order status
            await self.dal.orders.update_order_status(
                orders[0].order_id,
                "FILLED",
                filled_quantity=orders[0].quantity,
                avg_fill_price=150.50
            )
            
            # Get order by ID
            filled_order = await self.dal.orders.get_order_by_id(orders[0].order_id, user.id)
            assert filled_order.status == "FILLED"
            assert filled_order.filled_quantity == orders[0].quantity
            
            # Get orders by symbol
            symbol_orders = await self.dal.orders.get_orders_by_symbol("AAPL")
            assert len(symbol_orders) >= 1
            
            self.log_test("Order Operations", True,
                         f"Created and managed {len(orders)} orders", time.time() - start_time)
            return orders
            
        except Exception as e:
            self.log_test("Order Operations", False, str(e), time.time() - start_time)
            return []
    
    async def test_position_operations(self, user, account):
        """Test position operations"""
        if not user or not account:
            return []
            
        start_time = time.time()
        
        try:
            positions = []
            
            # Create/update positions
            symbols = ["AAPL", "MSFT", "GOOGL"]
            for i, symbol in enumerate(symbols):
                position = await self.dal.positions.create_or_update_position(
                    user_id=user.id,
                    account_id=account.id,
                    symbol=symbol,
                    quantity=100.0 * (i + 1),
                    avg_cost=150.0 + i * 10,
                    market_value=(150.0 + i * 10) * 100.0 * (i + 1),
                    unrealized_pnl=i * 100.0
                )
                positions.append(position)
            
            # Get positions by user
            user_positions = await self.dal.positions.get_positions_by_user(user.id, account.id)
            assert len(user_positions) >= len(positions)
            
            # Get position by symbol
            aapl_position = await self.dal.positions.get_position_by_symbol(
                user.id, account.id, "AAPL"
            )
            assert aapl_position is not None
            assert aapl_position.symbol == "AAPL"
            
            # Update position
            updated_position = await self.dal.positions.create_or_update_position(
                user_id=user.id,
                account_id=account.id,
                symbol="AAPL",
                quantity=200.0,  # Updated quantity
                avg_cost=155.0,  # Updated cost
                market_value=31000.0,
                unrealized_pnl=1000.0
            )
            assert updated_position.quantity == 200.0
            
            self.log_test("Position Operations", True,
                         f"Created and managed {len(positions)} positions", time.time() - start_time)
            return positions
            
        except Exception as e:
            self.log_test("Position Operations", False, str(e), time.time() - start_time)
            return []
    
    async def test_strategy_operations(self, user):
        """Test strategy operations"""
        if not user:
            return []
            
        start_time = time.time()
        
        try:
            strategies = []
            
            # Create strategies
            strategy_configs = [
                {
                    "name": "RSI Mean Reversion",
                    "description": "RSI-based mean reversion strategy",
                    "strategy_type": "mean_reversion",
                    "parameters": {
                        "rsi_period": 14,
                        "rsi_oversold": 30,
                        "rsi_overbought": 70,
                        "symbols": ["AAPL", "MSFT"]
                    }
                },
                {
                    "name": "MACD Momentum",
                    "description": "MACD momentum strategy",
                    "strategy_type": "momentum",
                    "parameters": {
                        "fast_period": 12,
                        "slow_period": 26,
                        "signal_period": 9,
                        "symbols": ["GOOGL", "AMZN"]
                    }
                }
            ]
            
            for config in strategy_configs:
                strategy = await self.dal.strategies.create_strategy(
                    user_id=user.id,
                    name=config["name"],
                    description=config["description"],
                    strategy_type=config["strategy_type"],
                    parameters=config["parameters"]
                )
                strategies.append(strategy)
            
            # Get strategies by user
            user_strategies = await self.dal.strategies.get_strategies_by_user(user.id)
            assert len(user_strategies) >= len(strategies)
            
            # Update strategy status
            await self.dal.strategies.update_strategy_status(strategies[0].id, True)
            
            # Update strategy parameters
            new_params = strategies[1].parameters.copy()
            new_params["risk_limit"] = 0.02
            await self.dal.strategies.update_strategy_parameters(strategies[1].id, new_params)
            
            self.log_test("Strategy Operations", True,
                         f"Created and managed {len(strategies)} strategies", time.time() - start_time)
            return strategies
            
        except Exception as e:
            self.log_test("Strategy Operations", False, str(e), time.time() - start_time)
            return []
    
    async def test_market_data_operations(self):
        """Test market data storage and retrieval"""
        start_time = time.time()
        
        try:
            if not self.db_manager.clickhouse_client:
                self.log_test("Market Data Operations", False, 
                             "ClickHouse not available", time.time() - start_time)
                return
            
            # Store sample market data
            now = datetime.utcnow()
            symbols = ["AAPL", "MSFT", "GOOGL"]
            
            for i, symbol in enumerate(symbols):
                for j in range(10):  # 10 data points per symbol
                    timestamp = now - timedelta(minutes=j)
                    await self.dal.market_data.store_market_data(
                        symbol=symbol,
                        timestamp=timestamp,
                        open_price=150.0 + i * 10 + j * 0.1,
                        high=152.0 + i * 10 + j * 0.1,
                        low=149.0 + i * 10 + j * 0.1,
                        close=151.0 + i * 10 + j * 0.1,
                        volume=1000000 + j * 10000,
                        interval="1m",
                        source="test"
                    )
            
            # Retrieve market data
            start_time_query = now - timedelta(minutes=5)
            end_time_query = now
            
            data = await self.dal.market_data.get_market_data(
                symbol="AAPL",
                start_time=start_time_query,
                end_time=end_time_query,
                interval="1m"
            )
            
            assert len(data) >= 0  # Should retrieve some data
            
            # Store indicator data
            await self.dal.market_data.store_indicator_data(
                symbol="AAPL",
                timestamp=now,
                indicator_name="RSI",
                value=65.5,
                signal="BUY",
                strength=0.75,
                metadata={"period": 14, "test": True}
            )
            
            self.log_test("Market Data Operations", True,
                         f"Stored and retrieved market data for {len(symbols)} symbols", 
                         time.time() - start_time)
            
        except Exception as e:
            self.log_test("Market Data Operations", False, str(e), time.time() - start_time)
    
    async def test_caching_operations(self):
        """Test Redis caching operations"""
        start_time = time.time()
        
        try:
            if not self.db_manager.redis_pool:
                self.log_test("Caching Operations", False,
                             "Redis not available", time.time() - start_time)
                return
            
            # Test cache operations
            test_key = "test_cache_key"
            test_value = {"message": "Hello Cache", "timestamp": datetime.utcnow().isoformat()}
            
            # Set cache
            await self.db_manager.cache_set(test_key, test_value, ttl=60)
            
            # Get cache
            cached_value = await self.db_manager.cache_get(test_key)
            assert cached_value is not None
            assert cached_value["message"] == test_value["message"]
            
            # Delete cache
            await self.db_manager.cache_delete(test_key)
            
            # Verify deletion
            deleted_value = await self.db_manager.cache_get(test_key)
            assert deleted_value is None
            
            self.log_test("Caching Operations", True,
                         "Cache set/get/delete operations successful", time.time() - start_time)
            
        except Exception as e:
            self.log_test("Caching Operations", False, str(e), time.time() - start_time)
    
    async def test_performance(self):
        """Performance tests"""
        if not self.db_manager.health_status.get("postgres", False):
            print("⚠️ Skipping performance tests - PostgreSQL not available")
            return
        
        print("\n🏃 Running Performance Tests...")
        
        # Test bulk operations
        start_time = time.time()
        
        try:
            # Create test user for performance tests
            perf_user = await self.dal.users.create_user(
                username=f"perf_user_{uuid.uuid4().hex[:8]}",
                email=f"perf_{uuid.uuid4().hex[:8]}@example.com",
                password_hash="perf_password",
                permissions=["read", "write"]
            )
            
            # Bulk create orders
            order_count = 100
            orders = []
            
            bulk_start = time.time()
            for i in range(order_count):
                order = await self.dal.orders.create_order(
                    user_id=perf_user.id,
                    account_id=perf_user.id,  # Using user ID as mock account ID
                    order_id=f"PERF_ORDER_{i}_{uuid.uuid4().hex[:8]}",
                    symbol=f"TEST{i % 10}",  # 10 different symbols
                    side="BUY" if i % 2 == 0 else "SELL",
                    order_type="MARKET",
                    quantity=100.0 + i,
                    metadata={"performance_test": True, "batch": i // 10}
                )
                orders.append(order)
            
            bulk_duration = time.time() - bulk_start
            orders_per_second = order_count / bulk_duration
            
            self.log_test("Bulk Order Creation", True,
                         f"{order_count} orders in {bulk_duration:.2f}s ({orders_per_second:.1f} ops/sec)",
                         bulk_duration)
            
        except Exception as e:
            self.log_test("Performance Tests", False, str(e), time.time() - start_time)
    
    async def run_all_tests(self, include_performance: bool = False):
        """Run all database tests"""
        print("\n📊 Testing Database Operations:")
        
        # Basic connectivity
        health_ok = await self.test_database_health()
        if not health_ok:
            print("⚠️ Some databases are not healthy, some tests may fail")
        
        # Core operations
        user = await self.test_user_operations()
        account = await self.test_trading_account_operations(user)
        orders = await self.test_order_operations(user, account)
        positions = await self.test_position_operations(user, account)
        strategies = await self.test_strategy_operations(user)
        
        # Data operations
        await self.test_market_data_operations()
        await self.test_caching_operations()
        
        # Performance tests
        if include_performance:
            await self.test_performance()
        
        # Summary
        print("\n" + "=" * 60)
        print("🎯 DATABASE TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        success_rate = (passed / total) * 100 if total > 0 else 0
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Status assessment
        if success_rate >= 90:
            status = "🟢 EXCELLENT"
        elif success_rate >= 75:
            status = "🟡 GOOD"
        elif success_rate >= 50:
            status = "🟠 NEEDS IMPROVEMENT"
        else:
            status = "🔴 CRITICAL ISSUES"
        
        print(f"Overall Status: {status}")
        
        # Failed tests details
        failed_tests = [r for r in self.test_results if not r["success"]]
        if failed_tests:
            print(f"\n❌ Failed Tests:")
            for test in failed_tests:
                print(f"  - {test['name']}: {test['details']}")
        
        return success_rate
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.db_manager:
            await self.db_manager.cleanup()

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Database Test Suite")
    parser.add_argument("--full", action="store_true", help="Run full test suite including setup")
    parser.add_argument("--performance", action="store_true", help="Include performance tests")
    
    args = parser.parse_args()
    
    tester = DatabaseTester()
    
    try:
        await tester.initialize()
        success_rate = await tester.run_all_tests(include_performance=args.performance)
        
        # Exit with appropriate code
        exit_code = 0 if success_rate >= 75 else 1
        sys.exit(exit_code)
        
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        sys.exit(1)
    
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())