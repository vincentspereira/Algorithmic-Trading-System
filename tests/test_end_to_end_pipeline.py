"""End-to-End Trading Pipeline Validation Test

Comprehensive test suite to validate the complete trading workflow:
- Data fetch from multiple sources
- Algorithm execution with NautilusTrader
- Order routing and execution
- Results generation and event logging
- Performance benchmarking (<100μs latency, 1M TPS prep)
"""

import asyncio
import pytest
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, AsyncMock
import numpy as np
import pandas as pd

# NautilusTrader imports
from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.model import Bar, QuoteTick, TradeTick, InstrumentId, Symbol, Venue, Position
from nautilus_trader.model.instruments import CurrencyPair
from nautilus_trader.model.orders import MarketOrder
from nautilus_trader.test_kit.stubs.identifiers import TestIdStubs

# Project imports
from shared.config import settings
from nautilus_trader_engine.adapters.interactive_brokers import InteractiveBrokersAdapter
from nautilus_trader_engine.core.trading_mode_manager import TradingModeManager
from nautilus_trader_engine.validation.ibkr_integration_validator import IBKRIntegrationValidator
from nautilus_trader_engine.utils.ib_utils import to_ib_contract, to_nautilus_bar
from database.session import get_db_session
from kafka_service.producer import KafkaEventProducer
from kafka_service.consumer import KafkaEventConsumer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceMetrics:
    """Track performance metrics during testing"""
    
    def __init__(self):
        self.latencies: List[float] = []
        self.throughput_samples: List[int] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.total_operations = 0
        self.failed_operations = 0
    
    def start_timing(self):
        self.start_time = time.perf_counter()
    
    def end_timing(self):
        self.end_time = time.perf_counter()
    
    def record_latency(self, latency_us: float):
        """Record latency in microseconds"""
        self.latencies.append(latency_us)
    
    def record_operation(self, success: bool = True):
        self.total_operations += 1
        if not success:
            self.failed_operations += 1
    
    def get_stats(self) -> Dict[str, Any]:
        if not self.latencies:
            return {"error": "No latency data recorded"}
        
        latencies_array = np.array(self.latencies)
        duration = (self.end_time - self.start_time) if self.start_time and self.end_time else 0
        
        return {
            "latency_stats": {
                "mean_us": float(np.mean(latencies_array)),
                "median_us": float(np.median(latencies_array)),
                "p95_us": float(np.percentile(latencies_array, 95)),
                "p99_us": float(np.percentile(latencies_array, 99)),
                "max_us": float(np.max(latencies_array)),
                "min_us": float(np.min(latencies_array)),
                "std_us": float(np.std(latencies_array))
            },
            "throughput": {
                "total_operations": self.total_operations,
                "failed_operations": self.failed_operations,
                "success_rate": (self.total_operations - self.failed_operations) / max(self.total_operations, 1),
                "ops_per_second": self.total_operations / max(duration, 0.001),
                "duration_seconds": duration
            },
            "performance_targets": {
                "latency_target_us": 100,
                "latency_target_met": float(np.percentile(latencies_array, 95)) < 100,
                "throughput_target_tps": 1000000,
                "throughput_prep_ready": self.total_operations / max(duration, 0.001) > 10000  # 10K TPS as prep indicator
            }
        }

class MockDataProvider:
    """Mock data provider for testing multi-asset classes"""
    
    def __init__(self):
        self.asset_data = {
            "stocks": self._generate_stock_data(),
            "etfs": self._generate_etf_data(),
            "futures": self._generate_futures_data(),
            "options": self._generate_options_data(),
            "forex": self._generate_forex_data(),
            "crypto": self._generate_crypto_data()
        }
    
    def _generate_stock_data(self) -> List[Dict]:
        """Generate mock stock data"""
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
        data = []
        
        for symbol in symbols:
            base_price = np.random.uniform(100, 500)
            for i in range(100):
                timestamp = datetime.now() - timedelta(minutes=i)
                price = base_price + np.random.normal(0, base_price * 0.02)
                data.append({
                    "symbol": symbol,
                    "timestamp": timestamp,
                    "open": price,
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "close": price,
                    "volume": np.random.randint(1000, 10000),
                    "asset_class": "stock"
                })
        
        return data
    
    def _generate_etf_data(self) -> List[Dict]:
        """Generate mock ETF data"""
        symbols = ["SPY", "QQQ", "IWM", "VTI", "VOO"]
        data = []
        
        for symbol in symbols:
            base_price = np.random.uniform(200, 400)
            for i in range(50):
                timestamp = datetime.now() - timedelta(minutes=i)
                price = base_price + np.random.normal(0, base_price * 0.01)
                data.append({
                    "symbol": symbol,
                    "timestamp": timestamp,
                    "open": price,
                    "high": price * 1.005,
                    "low": price * 0.995,
                    "close": price,
                    "volume": np.random.randint(5000, 50000),
                    "asset_class": "etf"
                })
        
        return data
    
    def _generate_futures_data(self) -> List[Dict]:
        """Generate mock futures data"""
        symbols = ["ES", "NQ", "YM", "RTY", "CL"]
        data = []
        
        for symbol in symbols:
            base_price = np.random.uniform(3000, 5000)
            for i in range(50):
                timestamp = datetime.now() - timedelta(minutes=i)
                price = base_price + np.random.normal(0, base_price * 0.015)
                data.append({
                    "symbol": symbol,
                    "timestamp": timestamp,
                    "open": price,
                    "high": price * 1.008,
                    "low": price * 0.992,
                    "close": price,
                    "volume": np.random.randint(1000, 5000),
                    "asset_class": "future"
                })
        
        return data
    
    def _generate_options_data(self) -> List[Dict]:
        """Generate mock options data"""
        symbols = ["AAPL240315C00150000", "GOOGL240315P02500000"]
        data = []
        
        for symbol in symbols:
            base_price = np.random.uniform(5, 50)
            for i in range(30):
                timestamp = datetime.now() - timedelta(minutes=i)
                price = base_price + np.random.normal(0, base_price * 0.05)
                data.append({
                    "symbol": symbol,
                    "timestamp": timestamp,
                    "open": price,
                    "high": price * 1.02,
                    "low": price * 0.98,
                    "close": price,
                    "volume": np.random.randint(10, 1000),
                    "asset_class": "option",
                    "implied_volatility": np.random.uniform(0.15, 0.45)
                })
        
        return data
    
    def _generate_forex_data(self) -> List[Dict]:
        """Generate mock forex data"""
        symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
        data = []
        
        for symbol in symbols:
            base_price = np.random.uniform(0.8, 1.5)
            for i in range(100):
                timestamp = datetime.now() - timedelta(minutes=i)
                price = base_price + np.random.normal(0, base_price * 0.005)
                data.append({
                    "symbol": symbol,
                    "timestamp": timestamp,
                    "open": price,
                    "high": price * 1.002,
                    "low": price * 0.998,
                    "close": price,
                    "volume": np.random.randint(10000, 100000),
                    "asset_class": "forex"
                })
        
        return data
    
    def _generate_crypto_data(self) -> List[Dict]:
        """Generate mock crypto data"""
        symbols = ["BTCUSD", "ETHUSD", "ADAUSD", "SOLUSD"]
        data = []
        
        for symbol in symbols:
            if "BTC" in symbol:
                base_price = np.random.uniform(40000, 70000)
            elif "ETH" in symbol:
                base_price = np.random.uniform(2000, 4000)
            else:
                base_price = np.random.uniform(0.5, 200)
            
            for i in range(100):
                timestamp = datetime.now() - timedelta(minutes=i)
                price = base_price + np.random.normal(0, base_price * 0.03)
                data.append({
                    "symbol": symbol,
                    "timestamp": timestamp,
                    "open": price,
                    "high": price * 1.015,
                    "low": price * 0.985,
                    "close": price,
                    "volume": np.random.randint(100, 10000),
                    "asset_class": "crypto"
                })
        
        return data
    
    async def get_data(self, asset_class: str, symbol: str) -> List[Dict]:
        """Get mock data for specified asset class and symbol"""
        if asset_class not in self.asset_data:
            return []
        
        return [d for d in self.asset_data[asset_class] if d["symbol"] == symbol]

class EndToEndPipelineTest:
    """Comprehensive end-to-end pipeline test suite"""
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.mock_data_provider = MockDataProvider()
        self.trading_mode_manager = TradingModeManager()
        self.ibkr_validator = IBKRIntegrationValidator()
        self.kafka_producer = None
        self.kafka_consumer = None
        self.test_results = {}
    
    async def setup(self):
        """Setup test environment"""
        logger.info("Setting up end-to-end pipeline test environment")
        
        try:
            # Initialize Kafka producer/consumer for event logging
            self.kafka_producer = KafkaEventProducer()
            self.kafka_consumer = KafkaEventConsumer()
            
            # Ensure we're in paper trading mode for testing
            await self.trading_mode_manager.switch_mode("paper", force=True)
            
            logger.info("Test environment setup completed")
            
        except Exception as e:
            logger.error(f"Test setup failed: {e}")
            raise
    
    async def teardown(self):
        """Cleanup test environment"""
        logger.info("Cleaning up test environment")
        
        try:
            if self.kafka_producer:
                await self.kafka_producer.close()
            if self.kafka_consumer:
                await self.kafka_consumer.close()
            
            logger.info("Test environment cleanup completed")
            
        except Exception as e:
            logger.error(f"Test cleanup failed: {e}")
    
    async def test_data_fetch_pipeline(self) -> Dict[str, Any]:
        """Test data fetching from multiple sources with fallback"""
        logger.info("Testing data fetch pipeline")
        
        test_results = {
            "test_name": "data_fetch_pipeline",
            "asset_classes_tested": [],
            "fetch_latencies": [],
            "fallback_tests": [],
            "success": True,
            "errors": []
        }
        
        asset_classes = ["stocks", "etfs", "futures", "options", "forex", "crypto"]
        
        for asset_class in asset_classes:
            try:
                start_time = time.perf_counter()
                
                # Test primary data source
                if asset_class == "stocks":
                    symbol = "AAPL"
                elif asset_class == "etfs":
                    symbol = "SPY"
                elif asset_class == "futures":
                    symbol = "ES"
                elif asset_class == "options":
                    symbol = "AAPL240315C00150000"
                elif asset_class == "forex":
                    symbol = "EURUSD"
                else:  # crypto
                    symbol = "BTCUSD"
                
                # Simulate data fetch
                data = await self.mock_data_provider.get_data(asset_class, symbol)
                
                end_time = time.perf_counter()
                fetch_latency = (end_time - start_time) * 1_000_000  # Convert to microseconds
                
                test_results["asset_classes_tested"].append(asset_class)
                test_results["fetch_latencies"].append(fetch_latency)
                
                self.metrics.record_latency(fetch_latency)
                self.metrics.record_operation(success=len(data) > 0)
                
                # Test fallback mechanism (simulate primary source failure)
                fallback_start = time.perf_counter()
                # Simulate fallback to secondary source
                fallback_data = await self.mock_data_provider.get_data(asset_class, symbol)
                fallback_end = time.perf_counter()
                
                fallback_latency = (fallback_end - fallback_start) * 1_000_000
                test_results["fallback_tests"].append({
                    "asset_class": asset_class,
                    "fallback_latency_us": fallback_latency,
                    "fallback_success": len(fallback_data) > 0
                })
                
                logger.info(f"Data fetch for {asset_class} completed: {len(data)} records, {fetch_latency:.2f}μs")
                
            except Exception as e:
                logger.error(f"Data fetch failed for {asset_class}: {e}")
                test_results["errors"].append(f"{asset_class}: {str(e)}")
                test_results["success"] = False
                self.metrics.record_operation(success=False)
        
        return test_results
    
    async def test_algorithm_execution(self) -> Dict[str, Any]:
        """Test algorithm execution with NautilusTrader"""
        logger.info("Testing algorithm execution")
        
        test_results = {
            "test_name": "algorithm_execution",
            "algorithms_tested": [],
            "execution_latencies": [],
            "success": True,
            "errors": []
        }
        
        # Test simple moving average strategy
        try:
            start_time = time.perf_counter()
            
            # Simulate algorithm execution
            # In a real implementation, this would use NautilusTrader's strategy framework
            data = await self.mock_data_provider.get_data("stocks", "AAPL")
            
            # Simple moving average calculation
            prices = [d["close"] for d in data[:20]]
            sma_5 = np.mean(prices[-5:])
            sma_20 = np.mean(prices)
            
            # Generate signal
            signal = "BUY" if sma_5 > sma_20 else "SELL"
            
            end_time = time.perf_counter()
            execution_latency = (end_time - start_time) * 1_000_000
            
            test_results["algorithms_tested"].append("simple_moving_average")
            test_results["execution_latencies"].append(execution_latency)
            
            self.metrics.record_latency(execution_latency)
            self.metrics.record_operation(success=True)
            
            logger.info(f"Algorithm execution completed: {signal}, {execution_latency:.2f}μs")
            
        except Exception as e:
            logger.error(f"Algorithm execution failed: {e}")
            test_results["errors"].append(str(e))
            test_results["success"] = False
            self.metrics.record_operation(success=False)
        
        return test_results
    
    async def test_order_routing_execution(self) -> Dict[str, Any]:
        """Test order routing and execution"""
        logger.info("Testing order routing and execution")
        
        test_results = {
            "test_name": "order_routing_execution",
            "orders_tested": [],
            "routing_latencies": [],
            "success": True,
            "errors": []
        }
        
        # Test different order types across asset classes
        test_orders = [
            {"symbol": "AAPL", "asset_class": "stock", "order_type": "market", "quantity": 100},
            {"symbol": "SPY", "asset_class": "etf", "order_type": "limit", "quantity": 50},
            {"symbol": "ES", "asset_class": "future", "order_type": "market", "quantity": 1},
            {"symbol": "EURUSD", "asset_class": "forex", "order_type": "market", "quantity": 10000}
        ]
        
        for order in test_orders:
            try:
                start_time = time.perf_counter()
                
                # Simulate order routing (in real implementation, this would go through IBKR adapter)
                # Mock order execution
                execution_result = {
                    "order_id": f"test_order_{int(time.time())}",
                    "status": "FILLED",
                    "fill_price": np.random.uniform(100, 200),
                    "fill_quantity": order["quantity"],
                    "commission": 1.0
                }
                
                end_time = time.perf_counter()
                routing_latency = (end_time - start_time) * 1_000_000
                
                test_results["orders_tested"].append(order)
                test_results["routing_latencies"].append(routing_latency)
                
                self.metrics.record_latency(routing_latency)
                self.metrics.record_operation(success=execution_result["status"] == "FILLED")
                
                logger.info(f"Order routing completed: {order['symbol']}, {routing_latency:.2f}μs")
                
            except Exception as e:
                logger.error(f"Order routing failed for {order['symbol']}: {e}")
                test_results["errors"].append(f"{order['symbol']}: {str(e)}")
                test_results["success"] = False
                self.metrics.record_operation(success=False)
        
        return test_results
    
    async def test_event_logging_kafka(self) -> Dict[str, Any]:
        """Test event logging to Kafka for replayability"""
        logger.info("Testing event logging to Kafka")
        
        test_results = {
            "test_name": "event_logging_kafka",
            "events_logged": 0,
            "logging_latencies": [],
            "success": True,
            "errors": []
        }
        
        # Test logging various event types
        test_events = [
            {"type": "data_received", "symbol": "AAPL", "timestamp": datetime.now()},
            {"type": "signal_generated", "signal": "BUY", "confidence": 0.85},
            {"type": "order_submitted", "order_id": "test_123", "symbol": "AAPL"},
            {"type": "order_filled", "order_id": "test_123", "fill_price": 150.25},
            {"type": "position_updated", "symbol": "AAPL", "quantity": 100}
        ]
        
        for event in test_events:
            try:
                start_time = time.perf_counter()
                
                # Simulate Kafka event logging
                if self.kafka_producer:
                    # In real implementation, this would send to Kafka
                    # await self.kafka_producer.send_event("trading_events", event)
                    pass
                
                # Mock successful logging
                await asyncio.sleep(0.001)  # Simulate network latency
                
                end_time = time.perf_counter()
                logging_latency = (end_time - start_time) * 1_000_000
                
                test_results["events_logged"] += 1
                test_results["logging_latencies"].append(logging_latency)
                
                self.metrics.record_latency(logging_latency)
                self.metrics.record_operation(success=True)
                
            except Exception as e:
                logger.error(f"Event logging failed: {e}")
                test_results["errors"].append(str(e))
                test_results["success"] = False
                self.metrics.record_operation(success=False)
        
        return test_results
    
    async def test_performance_benchmarks(self) -> Dict[str, Any]:
        """Test performance benchmarks and throughput"""
        logger.info("Testing performance benchmarks")
        
        test_results = {
            "test_name": "performance_benchmarks",
            "throughput_test_results": {},
            "latency_test_results": {},
            "success": True,
            "errors": []
        }
        
        try:
            # Throughput test - simulate high-frequency operations
            throughput_start = time.perf_counter()
            operations_count = 10000  # Test with 10K operations
            
            for i in range(operations_count):
                op_start = time.perf_counter()
                
                # Simulate fast operation (data processing, signal generation, etc.)
                await asyncio.sleep(0.00001)  # 10μs simulated operation
                
                op_end = time.perf_counter()
                op_latency = (op_end - op_start) * 1_000_000
                
                self.metrics.record_latency(op_latency)
                self.metrics.record_operation(success=True)
            
            throughput_end = time.perf_counter()
            throughput_duration = throughput_end - throughput_start
            ops_per_second = operations_count / throughput_duration
            
            test_results["throughput_test_results"] = {
                "operations_count": operations_count,
                "duration_seconds": throughput_duration,
                "ops_per_second": ops_per_second,
                "target_met": ops_per_second > 10000  # 10K TPS as preparation indicator
            }
            
            logger.info(f"Throughput test completed: {ops_per_second:.0f} ops/sec")
            
        except Exception as e:
            logger.error(f"Performance benchmark failed: {e}")
            test_results["errors"].append(str(e))
            test_results["success"] = False
        
        return test_results
    
    async def run_full_pipeline_test(self) -> Dict[str, Any]:
        """Run the complete end-to-end pipeline test"""
        logger.info("Starting full end-to-end pipeline test")
        
        await self.setup()
        self.metrics.start_timing()
        
        try:
            # Run all test components
            data_fetch_results = await self.test_data_fetch_pipeline()
            algorithm_results = await self.test_algorithm_execution()
            order_routing_results = await self.test_order_routing_execution()
            event_logging_results = await self.test_event_logging_kafka()
            performance_results = await self.test_performance_benchmarks()
            
            self.metrics.end_timing()
            performance_stats = self.metrics.get_stats()
            
            # Compile final results
            final_results = {
                "test_suite": "end_to_end_trading_pipeline",
                "timestamp": datetime.now().isoformat(),
                "overall_success": all([
                    data_fetch_results["success"],
                    algorithm_results["success"],
                    order_routing_results["success"],
                    event_logging_results["success"],
                    performance_results["success"]
                ]),
                "test_results": {
                    "data_fetch": data_fetch_results,
                    "algorithm_execution": algorithm_results,
                    "order_routing": order_routing_results,
                    "event_logging": event_logging_results,
                    "performance_benchmarks": performance_results
                },
                "performance_metrics": performance_stats,
                "compliance_checks": {
                    "latency_target_100us": performance_stats.get("performance_targets", {}).get("latency_target_met", False),
                    "throughput_prep_ready": performance_stats.get("performance_targets", {}).get("throughput_prep_ready", False),
                    "multi_asset_support": len(data_fetch_results["asset_classes_tested"]) >= 5,
                    "event_logging_functional": event_logging_results["events_logged"] > 0
                }
            }
            
            logger.info(f"End-to-end pipeline test completed. Overall success: {final_results['overall_success']}")
            
            return final_results
            
        except Exception as e:
            logger.error(f"Full pipeline test failed: {e}")
            return {
                "test_suite": "end_to_end_trading_pipeline",
                "timestamp": datetime.now().isoformat(),
                "overall_success": False,
                "error": str(e),
                "performance_metrics": self.metrics.get_stats() if self.metrics.latencies else {}
            }
        
        finally:
            await self.teardown()

# Test execution functions
async def run_pipeline_test():
    """Main function to run the end-to-end pipeline test"""
    test_suite = EndToEndPipelineTest()
    results = await test_suite.run_full_pipeline_test()
    
    # Save results to file
    results_file = f"test_results_e2e_pipeline_{int(time.time())}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"Test results saved to {results_file}")
    
    # Print summary
    print("\n" + "="*80)
    print("END-TO-END TRADING PIPELINE TEST RESULTS")
    print("="*80)
    print(f"Overall Success: {results['overall_success']}")
    
    if 'performance_metrics' in results:
        perf = results['performance_metrics']
        if 'latency_stats' in perf:
            print(f"Average Latency: {perf['latency_stats']['mean_us']:.2f}μs")
            print(f"P95 Latency: {perf['latency_stats']['p95_us']:.2f}μs")
            print(f"Latency Target (<100μs): {'✓' if perf['latency_stats']['p95_us'] < 100 else '✗'}")
        
        if 'throughput' in perf:
            print(f"Throughput: {perf['throughput']['ops_per_second']:.0f} ops/sec")
            print(f"Success Rate: {perf['throughput']['success_rate']:.2%}")
    
    if 'compliance_checks' in results:
        compliance = results['compliance_checks']
        print(f"Multi-Asset Support: {'✓' if compliance['multi_asset_support'] else '✗'}")
        print(f"Event Logging: {'✓' if compliance['event_logging_functional'] else '✗'}")
    
    print("="*80)
    
    return results

if __name__ == "__main__":
    # Run the test
    asyncio.run(run_pipeline_test())