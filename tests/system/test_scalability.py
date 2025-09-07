#!/usr/bin/env python3
"""
Scalability Testing System
System tests for validating system scalability under various load conditions.
"""

import sys
import pytest

if sys.platform == "win32":
    pytest.skip("Skipping scalability tests on Windows", allow_module_level=True)

import asyncio
import time
import json
import random
import threading
import subprocess
import tempfile
import shutil
import os
import signal
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import logging
from typing import Dict, List, Any, Optional, Tuple, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
import uuid
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil
from collections import defaultdict, deque
import socket
import requests
from pathlib import Path
import numpy as np
import statistics
import multiprocessing
from queue import Queue, Empty
import gc
import resource

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LoadTestType(Enum):
    """Types of load tests for scalability"""
    THROUGHPUT = "throughput"
    LATENCY = "latency"
    CONCURRENT_USERS = "concurrent_users"
    DATA_VOLUME = "data_volume"
    CONNECTION_POOL = "connection_pool"
    MEMORY_USAGE = "memory_usage"
    CPU_UTILIZATION = "cpu_utilization"
    DISK_IO = "disk_io"
    NETWORK_BANDWIDTH = "network_bandwidth"
    DATABASE_CONNECTIONS = "database_connections"
    MESSAGE_QUEUE = "message_queue"
    CACHE_PERFORMANCE = "cache_performance"
    API_ENDPOINTS = "api_endpoints"
    WEBSOCKET_CONNECTIONS = "websocket_connections"
    BATCH_PROCESSING = "batch_processing"


class ScalabilityMetric(Enum):
    """Scalability metrics to measure"""
    REQUESTS_PER_SECOND = "requests_per_second"
    RESPONSE_TIME_P50 = "response_time_p50"
    RESPONSE_TIME_P95 = "response_time_p95"
    RESPONSE_TIME_P99 = "response_time_p99"
    ERROR_RATE = "error_rate"
    MEMORY_USAGE_MB = "memory_usage_mb"
    CPU_USAGE_PERCENT = "cpu_usage_percent"
    DISK_IO_MBPS = "disk_io_mbps"
    NETWORK_IO_MBPS = "network_io_mbps"
    ACTIVE_CONNECTIONS = "active_connections"
    QUEUE_DEPTH = "queue_depth"
    CACHE_HIT_RATE = "cache_hit_rate"
    DATABASE_POOL_UTILIZATION = "database_pool_utilization"
    GARBAGE_COLLECTION_TIME = "garbage_collection_time"
    THREAD_COUNT = "thread_count"


@dataclass
class LoadTestConfiguration:
    """Configuration for load testing"""
    test_name: str
    test_type: LoadTestType
    duration_seconds: float
    ramp_up_seconds: float
    ramp_down_seconds: float
    target_load: int  # requests/second, users, connections, etc.
    max_load: int
    load_increment: int
    success_criteria: Dict[ScalabilityMetric, float]
    resource_limits: Dict[str, float]
    test_data_size: int = 1000
    warmup_requests: int = 100
    cooldown_seconds: float = 30.0
    tags: List[str] = field(default_factory=list)


@dataclass
class LoadTestResult:
    """Results from a load test"""
    test_name: str
    test_type: LoadTestType
    start_time: datetime
    end_time: datetime
    duration: float
    target_load: int
    actual_load: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    metrics: Dict[ScalabilityMetric, float]
    resource_usage: Dict[str, List[float]]
    error_details: List[str]
    performance_breakdown: Dict[str, float]
    scalability_score: float
    bottlenecks_identified: List[str]
    recommendations: List[str]


class PerformanceMonitor:
    """Monitor system performance during load tests"""
    
    def __init__(self, sampling_interval: float = 1.0):
        self.sampling_interval = sampling_interval
        self.is_monitoring = False
        self.metrics_history = defaultdict(list)
        self.monitor_task = None
        self.start_time = None
        
    async def start_monitoring(self):
        """Start performance monitoring"""
        self.is_monitoring = True
        self.start_time = time.time()
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Started performance monitoring")
        
    async def stop_monitoring(self):
        """Stop performance monitoring"""
        self.is_monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped performance monitoring")
        
    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                timestamp = time.time() - self.start_time
                
                # System metrics
                cpu_percent = psutil.cpu_percent(interval=None)
                memory = psutil.virtual_memory()
                disk_io = psutil.disk_io_counters()
                network_io = psutil.net_io_counters()
                
                # Process metrics
                process = psutil.Process()
                process_memory = process.memory_info().rss / (1024 * 1024)  # MB
                process_cpu = process.cpu_percent()
                thread_count = process.num_threads()
                
                # Store metrics
                metrics = {
                    'timestamp': timestamp,
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_available_mb': memory.available / (1024 * 1024),
                    'process_memory_mb': process_memory,
                    'process_cpu_percent': process_cpu,
                    'thread_count': thread_count,
                    'disk_read_mb': disk_io.read_bytes / (1024 * 1024) if disk_io else 0,
                    'disk_write_mb': disk_io.write_bytes / (1024 * 1024) if disk_io else 0,
                    'network_sent_mb': network_io.bytes_sent / (1024 * 1024) if network_io else 0,
                    'network_recv_mb': network_io.bytes_recv / (1024 * 1024) if network_io else 0
                }
                
                for key, value in metrics.items():
                    if key != 'timestamp':
                        self.metrics_history[key].append((timestamp, value))
                        
                await asyncio.sleep(self.sampling_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.sampling_interval)
                
    def get_metrics_summary(self) -> Dict[str, Dict[str, float]]:
        """Get summary statistics for all metrics"""
        summary = {}
        
        for metric_name, data_points in self.metrics_history.items():
            if data_points:
                values = [point[1] for point in data_points]
                summary[metric_name] = {
                    'min': min(values),
                    'max': max(values),
                    'mean': statistics.mean(values),
                    'median': statistics.median(values),
                    'p95': np.percentile(values, 95),
                    'p99': np.percentile(values, 99),
                    'std_dev': statistics.stdev(values) if len(values) > 1 else 0
                }
                
        return summary
        
    def clear_metrics(self):
        """Clear collected metrics"""
        self.metrics_history.clear()


class MockTradingSystemScalable:
    """Mock trading system with scalability features"""
    
    def __init__(self):
        self.is_running = True
        self.request_count = 0
        self.error_count = 0
        self.active_connections = 0
        self.max_connections = 1000
        self.connection_pool_size = 100
        self.database_connections = 0
        self.max_database_connections = 50
        self.cache_size = 10000
        self.cache_data = {}
        self.message_queue = Queue(maxsize=10000)
        self.processing_latency_ms = 10
        self.memory_usage_mb = 256
        self.cpu_usage_percent = 20
        self.response_times = deque(maxlen=10000)
        self.throughput_history = deque(maxlen=1000)
        self.last_throughput_check = time.time()
        self.requests_in_window = 0
        self.lock = threading.Lock()
        
    async def handle_request(self, request_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a generic request with scalability simulation"""
        start_time = time.time()
        
        with self.lock:
            self.request_count += 1
            self.requests_in_window += 1
            
        try:
            # Check connection limits
            if self.active_connections >= self.max_connections:
                raise Exception("Connection limit exceeded")
                
            self.active_connections += 1
            
            # Simulate processing based on request type
            if request_type == "market_data":
                await self._process_market_data_request(payload)
            elif request_type == "order_placement":
                await self._process_order_request(payload)
            elif request_type == "portfolio_query":
                await self._process_portfolio_request(payload)
            elif request_type == "risk_calculation":
                await self._process_risk_request(payload)
            else:
                await self._process_generic_request(payload)
                
            # Record response time
            response_time = (time.time() - start_time) * 1000  # ms
            self.response_times.append(response_time)
            
            return {
                'status': 'success',
                'request_id': f"REQ_{self.request_count:08d}",
                'response_time_ms': response_time,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            with self.lock:
                self.error_count += 1
            raise e
            
        finally:
            self.active_connections -= 1
            
    async def _process_market_data_request(self, payload: Dict[str, Any]):
        """Process market data request"""
        # Check cache first
        cache_key = f"market_data_{payload.get('symbol', 'DEFAULT')}"
        if cache_key in self.cache_data:
            await asyncio.sleep(0.001)  # Cache hit - very fast
            return self.cache_data[cache_key]
            
        # Cache miss - simulate database query
        await self._simulate_database_query()
        
        # Store in cache
        if len(self.cache_data) < self.cache_size:
            self.cache_data[cache_key] = {'price': random.uniform(100, 200), 'volume': random.randint(1000, 10000)}
            
    async def _process_order_request(self, payload: Dict[str, Any]):
        """Process order placement request"""
        # Simulate order validation
        await asyncio.sleep(self.processing_latency_ms / 1000.0)
        
        # Simulate database write
        await self._simulate_database_write()
        
        # Add to message queue for processing
        try:
            self.message_queue.put_nowait({
                'type': 'order_placed',
                'order_id': f"ORD_{self.request_count:08d}",
                'timestamp': time.time()
            })
        except:
            pass  # Queue full
            
    async def _process_portfolio_request(self, payload: Dict[str, Any]):
        """Process portfolio query request"""
        # Simulate complex calculation
        await asyncio.sleep(self.processing_latency_ms * 2 / 1000.0)
        
        # Multiple database queries
        for _ in range(3):
            await self._simulate_database_query()
            
    async def _process_risk_request(self, payload: Dict[str, Any]):
        """Process risk calculation request"""
        # CPU intensive calculation simulation
        await asyncio.sleep(self.processing_latency_ms * 3 / 1000.0)
        
        # Simulate memory usage increase
        self.memory_usage_mb += 0.1
        
    async def _process_generic_request(self, payload: Dict[str, Any]):
        """Process generic request"""
        await asyncio.sleep(self.processing_latency_ms / 1000.0)
        
    async def _simulate_database_query(self):
        """Simulate database query with connection pooling"""
        if self.database_connections >= self.max_database_connections:
            # Wait for available connection
            await asyncio.sleep(0.01)
            
        self.database_connections += 1
        try:
            # Simulate query time
            await asyncio.sleep(0.005)
        finally:
            self.database_connections -= 1
            
    async def _simulate_database_write(self):
        """Simulate database write operation"""
        if self.database_connections >= self.max_database_connections:
            await asyncio.sleep(0.01)
            
        self.database_connections += 1
        try:
            # Write operations are slower
            await asyncio.sleep(0.01)
        finally:
            self.database_connections -= 1
            
    def get_performance_metrics(self) -> Dict[str, float]:
        """Get current performance metrics"""
        current_time = time.time()
        
        # Calculate throughput
        if current_time - self.last_throughput_check >= 1.0:
            throughput = self.requests_in_window / (current_time - self.last_throughput_check)
            self.throughput_history.append(throughput)
            self.requests_in_window = 0
            self.last_throughput_check = current_time
        else:
            throughput = self.throughput_history[-1] if self.throughput_history else 0
            
        # Calculate response time percentiles
        response_times = list(self.response_times)
        if response_times:
            p50 = np.percentile(response_times, 50)
            p95 = np.percentile(response_times, 95)
            p99 = np.percentile(response_times, 99)
        else:
            p50 = p95 = p99 = 0
            
        # Calculate error rate
        error_rate = (self.error_count / max(self.request_count, 1)) * 100
        
        # Cache hit rate
        cache_hit_rate = len(self.cache_data) / max(self.cache_size, 1) * 100
        
        # Database pool utilization
        db_pool_utilization = (self.database_connections / self.max_database_connections) * 100
        
        return {
            ScalabilityMetric.REQUESTS_PER_SECOND.value: throughput,
            ScalabilityMetric.RESPONSE_TIME_P50.value: p50,
            ScalabilityMetric.RESPONSE_TIME_P95.value: p95,
            ScalabilityMetric.RESPONSE_TIME_P99.value: p99,
            ScalabilityMetric.ERROR_RATE.value: error_rate,
            ScalabilityMetric.MEMORY_USAGE_MB.value: self.memory_usage_mb,
            ScalabilityMetric.CPU_USAGE_PERCENT.value: self.cpu_usage_percent,
            ScalabilityMetric.ACTIVE_CONNECTIONS.value: self.active_connections,
            ScalabilityMetric.QUEUE_DEPTH.value: self.message_queue.qsize(),
            ScalabilityMetric.CACHE_HIT_RATE.value: cache_hit_rate,
            ScalabilityMetric.DATABASE_POOL_UTILIZATION.value: db_pool_utilization,
            'total_requests': self.request_count,
            'total_errors': self.error_count
        }
        
    def simulate_load_increase(self, load_factor: float):
        """Simulate system behavior under increased load"""
        # Increase processing latency under load
        base_latency = 10
        self.processing_latency_ms = base_latency * (1 + load_factor * 0.5)
        
        # Increase memory usage
        base_memory = 256
        self.memory_usage_mb = base_memory * (1 + load_factor * 0.3)
        
        # Increase CPU usage
        base_cpu = 20
        self.cpu_usage_percent = min(95, base_cpu * (1 + load_factor * 2))
        
    def reset_metrics(self):
        """Reset performance metrics"""
        self.request_count = 0
        self.error_count = 0
        self.response_times.clear()
        self.throughput_history.clear()
        self.requests_in_window = 0
        self.last_throughput_check = time.time()
        self.cache_data.clear()
        
        # Clear message queue
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except Empty:
                break


class LoadTestExecutor:
    """Execute load tests with various patterns"""
    
    def __init__(self, target_system: MockTradingSystemScalable):
        self.target_system = target_system
        self.performance_monitor = PerformanceMonitor()
        self.active_workers = []
        self.test_results = []
        
    async def execute_load_test(self, config: LoadTestConfiguration) -> LoadTestResult:
        """Execute a load test based on configuration"""
        logger.info(f"Starting load test: {config.test_name}")
        
        start_time = datetime.now()
        
        # Reset system metrics
        self.target_system.reset_metrics()
        
        # Start performance monitoring
        await self.performance_monitor.start_monitoring()
        
        try:
            # Warmup phase
            if config.warmup_requests > 0:
                await self._warmup_phase(config.warmup_requests)
                
            # Main load test execution
            if config.test_type == LoadTestType.THROUGHPUT:
                result = await self._execute_throughput_test(config)
            elif config.test_type == LoadTestType.CONCURRENT_USERS:
                result = await self._execute_concurrent_users_test(config)
            elif config.test_type == LoadTestType.LATENCY:
                result = await self._execute_latency_test(config)
            elif config.test_type == LoadTestType.DATA_VOLUME:
                result = await self._execute_data_volume_test(config)
            elif config.test_type == LoadTestType.CONNECTION_POOL:
                result = await self._execute_connection_pool_test(config)
            else:
                result = await self._execute_generic_load_test(config)
                
            # Cooldown phase
            if config.cooldown_seconds > 0:
                await asyncio.sleep(config.cooldown_seconds)
                
        finally:
            # Stop performance monitoring
            await self.performance_monitor.stop_monitoring()
            
        end_time = datetime.now()
        
        # Finalize result
        result.start_time = start_time
        result.end_time = end_time
        result.duration = (end_time - start_time).total_seconds()
        
        # Add system metrics
        system_metrics = self.target_system.get_performance_metrics()
        for metric, value in system_metrics.items():
            if isinstance(metric, str) and metric in [m.value for m in ScalabilityMetric]:
                result.metrics[ScalabilityMetric(metric)] = value
                
        # Add resource usage summary
        result.resource_usage = self._get_resource_usage_summary()
        
        # Calculate scalability score
        result.scalability_score = self._calculate_scalability_score(result, config)
        
        # Identify bottlenecks and recommendations
        result.bottlenecks_identified = self._identify_bottlenecks(result)
        result.recommendations = self._generate_recommendations(result)
        
        self.test_results.append(result)
        
        logger.info(f"Completed load test: {config.test_name} (Score: {result.scalability_score:.1f})")
        
        return result
        
    async def _warmup_phase(self, warmup_requests: int):
        """Execute warmup requests"""
        logger.info(f"Warming up with {warmup_requests} requests")
        
        tasks = []
        for i in range(warmup_requests):
            task = asyncio.create_task(
                self.target_system.handle_request("market_data", {"symbol": f"WARM_{i}"})
            )
            tasks.append(task)
            
            # Small delay to avoid overwhelming
            if i % 10 == 0:
                await asyncio.sleep(0.01)
                
        # Wait for all warmup requests
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Reset metrics after warmup
        self.target_system.reset_metrics()
        
    async def _execute_throughput_test(self, config: LoadTestConfiguration) -> LoadTestResult:
        """Execute throughput-focused load test"""
        result = LoadTestResult(
            test_name=config.test_name,
            test_type=config.test_type,
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=0,
            target_load=config.target_load,
            actual_load=0,
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            metrics={},
            resource_usage={},
            error_details=[],
            performance_breakdown={},
            scalability_score=0,
            bottlenecks_identified=[],
            recommendations=[]
        )
        
        # Ramp up load gradually
        current_load = 0
        ramp_increment = config.load_increment
        
        while current_load < config.target_load:
            current_load = min(current_load + ramp_increment, config.target_load)
            
            logger.info(f"Ramping up to {current_load} requests/second")
            
            # Update system load simulation
            load_factor = current_load / config.target_load
            self.target_system.simulate_load_increase(load_factor)
            
            # Execute requests at current load level
            await self._execute_sustained_load(current_load, config.duration_seconds / 10)
            
            # Check if we should continue ramping
            metrics = self.target_system.get_performance_metrics()
            if metrics[ScalabilityMetric.ERROR_RATE.value] > 10.0:  # 10% error rate threshold
                logger.warning(f"High error rate detected at {current_load} RPS, stopping ramp-up")
                break
                
        result.actual_load = current_load
        
        # Sustained load test at maximum achieved load
        await self._execute_sustained_load(current_load, config.duration_seconds)
        
        # Collect final metrics
        final_metrics = self.target_system.get_performance_metrics()
        result.total_requests = final_metrics['total_requests']
        result.failed_requests = final_metrics['total_errors']
        result.successful_requests = result.total_requests - result.failed_requests
        
        return result
        
    async def _execute_concurrent_users_test(self, config: LoadTestConfiguration) -> LoadTestResult:
        """Execute concurrent users load test"""
        result = LoadTestResult(
            test_name=config.test_name,
            test_type=config.test_type,
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=0,
            target_load=config.target_load,
            actual_load=0,
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            metrics={},
            resource_usage={},
            error_details=[],
            performance_breakdown={},
            scalability_score=0,
            bottlenecks_identified=[],
            recommendations=[]
        )
        
        # Create concurrent user sessions
        user_tasks = []
        
        for user_id in range(config.target_load):
            task = asyncio.create_task(
                self._simulate_user_session(user_id, config.duration_seconds)
            )
            user_tasks.append(task)
            
            # Gradual ramp-up of users
            if user_id % 10 == 0 and config.ramp_up_seconds > 0:
                await asyncio.sleep(config.ramp_up_seconds / (config.target_load / 10))
                
        # Wait for all user sessions to complete
        user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
        
        # Process results
        successful_sessions = sum(1 for r in user_results if not isinstance(r, Exception))
        failed_sessions = len(user_results) - successful_sessions
        
        result.actual_load = config.target_load
        result.successful_requests = successful_sessions
        result.failed_requests = failed_sessions
        result.total_requests = len(user_results)
        
        return result
        
    async def _execute_latency_test(self, config: LoadTestConfiguration) -> LoadTestResult:
        """Execute latency-focused load test"""
        result = LoadTestResult(
            test_name=config.test_name,
            test_type=config.test_type,
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=0,
            target_load=config.target_load,
            actual_load=0,
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            metrics={},
            resource_usage={},
            error_details=[],
            performance_breakdown={},
            scalability_score=0,
            bottlenecks_identified=[],
            recommendations=[]
        )
        
        # Execute requests with precise timing
        request_interval = 1.0 / config.target_load  # seconds between requests
        
        start_time = time.time()
        request_tasks = []
        
        while time.time() - start_time < config.duration_seconds:
            # Create request task
            task = asyncio.create_task(
                self.target_system.handle_request("latency_test", {"timestamp": time.time()})
            )
            request_tasks.append(task)
            
            # Wait for next request time
            await asyncio.sleep(request_interval)
            
        # Wait for all requests to complete
        request_results = await asyncio.gather(*request_tasks, return_exceptions=True)
        
        # Process results
        successful_requests = sum(1 for r in request_results if not isinstance(r, Exception))
        failed_requests = len(request_results) - successful_requests
        
        result.actual_load = len(request_results) / config.duration_seconds
        result.total_requests = len(request_results)
        result.successful_requests = successful_requests
        result.failed_requests = failed_requests
        
        return result
        
    async def _execute_data_volume_test(self, config: LoadTestConfiguration) -> LoadTestResult:
        """Execute data volume load test"""
        result = LoadTestResult(
            test_name=config.test_name,
            test_type=config.test_type,
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=0,
            target_load=config.target_load,
            actual_load=0,
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            metrics={},
            resource_usage={},
            error_details=[],
            performance_breakdown={},
            scalability_score=0,
            bottlenecks_identified=[],
            recommendations=[]
        )
        
        # Generate large payloads
        large_payload = {
            'data': 'x' * config.test_data_size,  # Large string data
            'numbers': list(range(config.test_data_size // 10)),
            'timestamp': time.time()
        }
        
        # Execute requests with large payloads
        request_tasks = []
        
        for i in range(config.target_load):
            task = asyncio.create_task(
                self.target_system.handle_request("data_volume", large_payload)
            )
            request_tasks.append(task)
            
            # Control request rate
            if i % 10 == 0:
                await asyncio.sleep(0.1)
                
        # Wait for completion
        request_results = await asyncio.gather(*request_tasks, return_exceptions=True)
        
        # Process results
        successful_requests = sum(1 for r in request_results if not isinstance(r, Exception))
        failed_requests = len(request_results) - successful_requests
        
        result.actual_load = config.target_load
        result.total_requests = len(request_results)
        result.successful_requests = successful_requests
        result.failed_requests = failed_requests
        
        return result
        
    async def _execute_connection_pool_test(self, config: LoadTestConfiguration) -> LoadTestResult:
        """Execute connection pool load test"""
        result = LoadTestResult(
            test_name=config.test_name,
            test_type=config.test_type,
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=0,
            target_load=config.target_load,
            actual_load=0,
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            metrics={},
            resource_usage={},
            error_details=[],
            performance_breakdown={},
            scalability_score=0,
            bottlenecks_identified=[],
            recommendations=[]
        )
        
        # Test connection pool limits
        connection_tasks = []
        
        # Create many concurrent connections
        for i in range(config.target_load):
            task = asyncio.create_task(
                self._simulate_long_running_connection(i, config.duration_seconds)
            )
            connection_tasks.append(task)
            
        # Wait for all connections to complete
        connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # Process results
        successful_connections = sum(1 for r in connection_results if not isinstance(r, Exception))
        failed_connections = len(connection_results) - successful_connections
        
        result.actual_load = config.target_load
        result.total_requests = len(connection_results)
        result.successful_requests = successful_connections
        result.failed_requests = failed_connections
        
        return result
        
    async def _execute_generic_load_test(self, config: LoadTestConfiguration) -> LoadTestResult:
        """Execute generic load test"""
        result = LoadTestResult(
            test_name=config.test_name,
            test_type=config.test_type,
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=0,
            target_load=config.target_load,
            actual_load=0,
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            metrics={},
            resource_usage={},
            error_details=[],
            performance_breakdown={},
            scalability_score=0,
            bottlenecks_identified=[],
            recommendations=[]
        )
        
        # Execute mixed workload
        request_types = ["market_data", "order_placement", "portfolio_query", "risk_calculation"]
        request_tasks = []
        
        for i in range(config.target_load):
            request_type = random.choice(request_types)
            task = asyncio.create_task(
                self.target_system.handle_request(request_type, {"request_id": i})
            )
            request_tasks.append(task)
            
        # Wait for completion
        request_results = await asyncio.gather(*request_tasks, return_exceptions=True)
        
        # Process results
        successful_requests = sum(1 for r in request_results if not isinstance(r, Exception))
        failed_requests = len(request_results) - successful_requests
        
        result.actual_load = config.target_load
        result.total_requests = len(request_results)
        result.successful_requests = successful_requests
        result.failed_requests = failed_requests
        
        return result
        
    async def _execute_sustained_load(self, requests_per_second: int, duration_seconds: float):
        """Execute sustained load at specified rate"""
        request_interval = 1.0 / requests_per_second
        start_time = time.time()
        
        while time.time() - start_time < duration_seconds:
            # Create request
            asyncio.create_task(
                self.target_system.handle_request("sustained_load", {"timestamp": time.time()})
            )
            
            await asyncio.sleep(request_interval)
            
    async def _simulate_user_session(self, user_id: int, duration_seconds: float) -> Dict[str, Any]:
        """Simulate a user session with multiple requests"""
        session_start = time.time()
        requests_made = 0
        errors = 0
        
        while time.time() - session_start < duration_seconds:
            try:
                # Simulate user behavior with different request types
                request_type = random.choice(["market_data", "portfolio_query", "order_placement"])
                
                await self.target_system.handle_request(request_type, {
                    "user_id": user_id,
                    "session_time": time.time() - session_start
                })
                
                requests_made += 1
                
                # User think time
                await asyncio.sleep(random.uniform(0.5, 2.0))
                
            except Exception as e:
                errors += 1
                await asyncio.sleep(1.0)  # Wait before retry
                
        return {
            "user_id": user_id,
            "requests_made": requests_made,
            "errors": errors,
            "duration": time.time() - session_start
        }
        
    async def _simulate_long_running_connection(self, connection_id: int, duration_seconds: float) -> Dict[str, Any]:
        """Simulate a long-running connection"""
        connection_start = time.time()
        
        try:
            # Hold connection for specified duration
            while time.time() - connection_start < duration_seconds:
                # Periodic activity on connection
                await self.target_system.handle_request("connection_keepalive", {
                    "connection_id": connection_id
                })
                
                await asyncio.sleep(1.0)  # Keepalive every second
                
            return {
                "connection_id": connection_id,
                "duration": time.time() - connection_start,
                "status": "completed"
            }
            
        except Exception as e:
            return {
                "connection_id": connection_id,
                "duration": time.time() - connection_start,
                "status": "failed",
                "error": str(e)
            }
            
    def _get_resource_usage_summary(self) -> Dict[str, List[float]]:
        """Get resource usage summary from performance monitor"""
        metrics_summary = self.performance_monitor.get_metrics_summary()
        
        resource_usage = {}
        for metric_name, stats in metrics_summary.items():
            resource_usage[metric_name] = [
                stats['min'], stats['max'], stats['mean'], stats['p95'], stats['p99']
            ]
            
        return resource_usage
        
    def _calculate_scalability_score(self, result: LoadTestResult, config: LoadTestConfiguration) -> float:
        """Calculate overall scalability score"""
        score = 100.0
        
        # Success rate impact
        success_rate = result.successful_requests / max(result.total_requests, 1) * 100
        if success_rate < 95:
            score -= (95 - success_rate) * 2
            
        # Performance criteria impact
        for metric, threshold in config.success_criteria.items():
            if metric in result.metrics:
                actual_value = result.metrics[metric]
                
                if metric in [ScalabilityMetric.RESPONSE_TIME_P95, ScalabilityMetric.RESPONSE_TIME_P99, ScalabilityMetric.ERROR_RATE]:
                    # Lower is better
                    if actual_value > threshold:
                        score -= min(30, (actual_value - threshold) / threshold * 100)
                else:
                    # Higher is better
                    if actual_value < threshold:
                        score -= min(30, (threshold - actual_value) / threshold * 100)
                        
        # Resource utilization impact
        if result.resource_usage:
            cpu_max = result.resource_usage.get('cpu_percent', [0, 0, 0, 0, 0])[1]
            memory_max = result.resource_usage.get('memory_percent', [0, 0, 0, 0, 0])[1]
            
            if cpu_max > 90:
                score -= 10
            if memory_max > 90:
                score -= 10
                
        return max(0, score)
        
    def _identify_bottlenecks(self, result: LoadTestResult) -> List[str]:
        """Identify performance bottlenecks"""
        bottlenecks = []
        
        # High error rate
        error_rate = result.failed_requests / max(result.total_requests, 1) * 100
        if error_rate > 5:
            bottlenecks.append(f"High error rate: {error_rate:.1f}%")
            
        # High response times
        if ScalabilityMetric.RESPONSE_TIME_P95 in result.metrics:
            p95_latency = result.metrics[ScalabilityMetric.RESPONSE_TIME_P95]
            if p95_latency > 1000:  # 1 second
                bottlenecks.append(f"High P95 latency: {p95_latency:.1f}ms")
                
        # Resource constraints
        if result.resource_usage:
            cpu_max = result.resource_usage.get('cpu_percent', [0, 0, 0, 0, 0])[1]
            memory_max = result.resource_usage.get('memory_percent', [0, 0, 0, 0, 0])[1]
            
            if cpu_max > 85:
                bottlenecks.append(f"CPU utilization: {cpu_max:.1f}%")
            if memory_max > 85:
                bottlenecks.append(f"Memory utilization: {memory_max:.1f}%")
                
        # Connection pool exhaustion
        if ScalabilityMetric.DATABASE_POOL_UTILIZATION in result.metrics:
            db_util = result.metrics[ScalabilityMetric.DATABASE_POOL_UTILIZATION]
            if db_util > 90:
                bottlenecks.append(f"Database connection pool utilization: {db_util:.1f}%")
                
        return bottlenecks
        
    def _generate_recommendations(self, result: LoadTestResult) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []
        
        # Based on bottlenecks
        for bottleneck in result.bottlenecks_identified:
            if "error rate" in bottleneck:
                recommendations.append("Implement better error handling and retry mechanisms")
            elif "latency" in bottleneck:
                recommendations.append("Optimize database queries and add caching")
            elif "CPU" in bottleneck:
                recommendations.append("Consider horizontal scaling or CPU optimization")
            elif "Memory" in bottleneck:
                recommendations.append("Optimize memory usage and implement garbage collection tuning")
            elif "connection pool" in bottleneck:
                recommendations.append("Increase database connection pool size")
                
        # General recommendations
        if result.scalability_score < 70:
            recommendations.append("Consider implementing load balancing")
            recommendations.append("Review and optimize critical code paths")
            
        if not recommendations:
            recommendations.append("System performed well under load - consider testing higher loads")
            
        return recommendations


class TestScalability:
    """Test suite for system scalability"""
    
    @pytest.fixture(autouse=True)
    async def setup_method(self):
        """Setup scalability test environment"""
        self.trading_system = MockTradingSystemScalable()
        self.load_executor = LoadTestExecutor(self.trading_system)
        
        logger.info("Scalability test environment setup completed")
        
    async def teardown_method(self):
        """Cleanup test environment"""
        # Reset system state
        self.trading_system.reset_metrics()
        
        # Clear performance monitor
        self.load_executor.performance_monitor.clear_metrics()
        
        logger.info("Scalability test environment cleanup completed")
        
    @pytest.mark.asyncio
    async def test_throughput_scalability(self):
        """Test system throughput scalability"""
        config = LoadTestConfiguration(
            test_name="Throughput Scalability Test",
            test_type=LoadTestType.THROUGHPUT,
            duration_seconds=30.0,
            ramp_up_seconds=10.0,
            ramp_down_seconds=5.0,
            target_load=1000,  # 1000 requests per second
            max_load=2000,
            load_increment=100,
            success_criteria={
                ScalabilityMetric.REQUESTS_PER_SECOND: 800.0,
                ScalabilityMetric.RESPONSE_TIME_P95: 500.0,
                ScalabilityMetric.ERROR_RATE: 5.0
            },
            resource_limits={
                "cpu_percent": 80.0,
                "memory_percent": 80.0
            },
            warmup_requests=50
        )
        
        result = await self.load_executor.execute_load_test(config)
        
        # Validate results
        assert result.scalability_score > 60.0  # Minimum acceptable score
        assert result.total_requests > 0
        assert result.successful_requests > 0
        
        # Check throughput achievement
        if ScalabilityMetric.REQUESTS_PER_SECOND in result.metrics:
            achieved_rps = result.metrics[ScalabilityMetric.REQUESTS_PER_SECOND]
            assert achieved_rps > 500  # Should achieve reasonable throughput
            
        logger.info(f"Throughput test completed - Score: {result.scalability_score:.1f}, RPS: {result.metrics.get(ScalabilityMetric.REQUESTS_PER_SECOND, 0):.1f}")
        
    @pytest.mark.asyncio
    async def test_concurrent_users_scalability(self):
        """Test concurrent users scalability"""
        config = LoadTestConfiguration(
            test_name="Concurrent Users Scalability Test",
            test_type=LoadTestType.CONCURRENT_USERS,
            duration_seconds=20.0,
            ramp_up_seconds=5.0,
            ramp_down_seconds=2.0,
            target_load=100,  # 100 concurrent users
            max_load=200,
            load_increment=25,
            success_criteria={
                ScalabilityMetric.RESPONSE_TIME_P95: 1000.0,
                ScalabilityMetric.ERROR_RATE: 10.0
            },
            resource_limits={
                "cpu_percent": 85.0,
                "memory_percent": 85.0
            },
            warmup_requests=20
        )
        
        result = await self.load_executor.execute_load_test(config)
        
        # Validate results
        assert result.scalability_score > 50.0
        assert result.total_requests == config.target_load
        assert result.successful_requests > result.total_requests * 0.8  # 80% success rate
        
        logger.info(f"Concurrent users test completed - Score: {result.scalability_score:.1f}, Success rate: {result.successful_requests/result.total_requests*100:.1f}%")
        
    @pytest.mark.asyncio
    async def test_latency_under_load(self):
        """Test latency performance under load"""
        config = LoadTestConfiguration(
            test_name="Latency Under Load Test",
            test_type=LoadTestType.LATENCY,
            duration_seconds=15.0,
            ramp_up_seconds=3.0,
            ramp_down_seconds=2.0,
            target_load=500,  # 500 requests per second
            max_load=1000,
            load_increment=100,
            success_criteria={
                ScalabilityMetric.RESPONSE_TIME_P50: 100.0,
                ScalabilityMetric.RESPONSE_TIME_P95: 300.0,
                ScalabilityMetric.RESPONSE_TIME_P99: 500.0,
                ScalabilityMetric.ERROR_RATE: 2.0
            },
            resource_limits={
                "cpu_percent": 75.0
            },
            warmup_requests=30
        )
        
        result = await self.load_executor.execute_load_test(config)
        
        # Validate latency requirements
        assert result.scalability_score > 70.0
        
        if ScalabilityMetric.RESPONSE_TIME_P95 in result.metrics:
            p95_latency = result.metrics[ScalabilityMetric.RESPONSE_TIME_P95]
            assert p95_latency < 1000.0  # Should be under 1 second
            
        logger.info(f"Latency test completed - Score: {result.scalability_score:.1f}")
        
    @pytest.mark.asyncio
    async def test_data_volume_scalability(self):
        """Test scalability with large data volumes"""
        config = LoadTestConfiguration(
            test_name="Data Volume Scalability Test",
            test_type=LoadTestType.DATA_VOLUME,
            duration_seconds=10.0,
            ramp_up_seconds=2.0,
            ramp_down_seconds=1.0,
            target_load=100,  # 100 large requests
            max_load=200,
            load_increment=25,
            success_criteria={
                ScalabilityMetric.RESPONSE_TIME_P95: 2000.0,
                ScalabilityMetric.ERROR_RATE: 5.0
            },
            resource_limits={
                "memory_percent": 90.0
            },
            test_data_size=10000,  # 10KB payloads
            warmup_requests=10
        )
        
        result = await self.load_executor.execute_load_test(config)
        
        # Validate data volume handling
        assert result.scalability_score > 60.0
        assert result.successful_requests > result.total_requests * 0.9  # 90% success rate
        
        logger.info(f"Data volume test completed - Score: {result.scalability_score:.1f}")
        
    @pytest.mark.asyncio
    async def test_connection_pool_scalability(self):
        """Test connection pool scalability"""
        config = LoadTestConfiguration(
            test_name="Connection Pool Scalability Test",
            test_type=LoadTestType.CONNECTION_POOL,
            duration_seconds=8.0,
            ramp_up_seconds=2.0,
            ramp_down_seconds=1.0,
            target_load=150,  # 150 concurrent connections
            max_load=300,
            load_increment=50,
            success_criteria={
                ScalabilityMetric.ERROR_RATE: 15.0,
                ScalabilityMetric.DATABASE_POOL_UTILIZATION: 90.0
            },
            resource_limits={
                "active_connections": 200
            },
            warmup_requests=5
        )
        
        result = await self.load_executor.execute_load_test(config)
        
        # Validate connection handling
        assert result.scalability_score > 50.0
        
        # Check that system handled connection pressure
        if result.bottlenecks_identified:
            logger.info(f"Identified bottlenecks: {result.bottlenecks_identified}")
            
        logger.info(f"Connection pool test completed - Score: {result.scalability_score:.1f}")
        
    @pytest.mark.asyncio
    async def test_memory_usage_scalability(self):
        """Test memory usage under increasing load"""
        # Test with progressively larger loads
        load_levels = [50, 100, 200, 400]
        memory_usage_results = []
        
        for load_level in load_levels:
            config = LoadTestConfiguration(
                test_name=f"Memory Usage Test - {load_level} load",
                test_type=LoadTestType.THROUGHPUT,
                duration_seconds=5.0,
                ramp_up_seconds=1.0,
                ramp_down_seconds=1.0,
                target_load=load_level,
                max_load=load_level,
                load_increment=load_level,
                success_criteria={
                    ScalabilityMetric.MEMORY_USAGE_MB: 1000.0
                },
                resource_limits={
                    "memory_percent": 95.0
                },
                warmup_requests=10
            )
            
            result = await self.load_executor.execute_load_test(config)
            
            memory_usage = result.metrics.get(ScalabilityMetric.MEMORY_USAGE_MB, 0)
            memory_usage_results.append((load_level, memory_usage))
            
            # Reset system between tests
            self.trading_system.reset_metrics()
            await asyncio.sleep(2.0)  # Allow garbage collection
            
        # Analyze memory scaling
        logger.info("Memory usage scaling results:")
        for load, memory in memory_usage_results:
            logger.info(f"  Load {load}: {memory:.1f} MB")
            
        # Memory usage should scale reasonably
        max_memory = max(memory for _, memory in memory_usage_results)
        assert max_memory < 2000.0  # Should not exceed 2GB
        
    @pytest.mark.asyncio
    async def test_cpu_utilization_scalability(self):
        """Test CPU utilization under load"""
        config = LoadTestConfiguration(
            test_name="CPU Utilization Scalability Test",
            test_type=LoadTestType.THROUGHPUT,
            duration_seconds=12.0,
            ramp_up_seconds=3.0,
            ramp_down_seconds=2.0,
            target_load=800,
            max_load=1200,
            load_increment=200,
            success_criteria={
                ScalabilityMetric.CPU_USAGE_PERCENT: 85.0,
                ScalabilityMetric.REQUESTS_PER_SECOND: 600.0
            },
            resource_limits={
                "cpu_percent": 90.0
            },
            warmup_requests=40
        )
        
        result = await self.load_executor.execute_load_test(config)
        
        # Validate CPU efficiency
        assert result.scalability_score > 55.0
        
        cpu_usage = result.metrics.get(ScalabilityMetric.CPU_USAGE_PERCENT, 0)
        requests_per_second = result.metrics.get(ScalabilityMetric.REQUESTS_PER_SECOND, 0)
        
        # Calculate CPU efficiency (requests per CPU percent)
        if cpu_usage > 0:
            cpu_efficiency = requests_per_second / cpu_usage
            logger.info(f"CPU efficiency: {cpu_efficiency:.2f} RPS per CPU%")
            assert cpu_efficiency > 5.0  # Should process at least 5 RPS per CPU%
            
        logger.info(f"CPU utilization test completed - Score: {result.scalability_score:.1f}")
        
    @pytest.mark.asyncio
    async def test_mixed_workload_scalability(self):
        """Test scalability with mixed workload patterns"""
        config = LoadTestConfiguration(
            test_name="Mixed Workload Scalability Test",
            test_type=LoadTestType.THROUGHPUT,
            duration_seconds=25.0,
            ramp_up_seconds=5.0,
            ramp_down_seconds=3.0,
            target_load=600,
            max_load=1000,
            load_increment=100,
            success_criteria={
                ScalabilityMetric.REQUESTS_PER_SECOND: 400.0,
                ScalabilityMetric.RESPONSE_TIME_P95: 800.0,
                ScalabilityMetric.ERROR_RATE: 8.0
            },
            resource_limits={
                "cpu_percent": 85.0,
                "memory_percent": 85.0
            },
            warmup_requests=60
        )
        
        result = await self.load_executor.execute_load_test(config)
        
        # Validate mixed workload performance
        assert result.scalability_score > 65.0
        assert result.successful_requests > result.total_requests * 0.85  # 85% success rate
        
        # Check that all success criteria are reasonably met
        criteria_met = 0
        for metric, threshold in config.success_criteria.items():
            if metric in result.metrics:
                actual = result.metrics[metric]
                if metric == ScalabilityMetric.ERROR_RATE:
                    if actual <= threshold:
                        criteria_met += 1
                else:
                    if actual >= threshold * 0.8:  # 80% of target is acceptable
                        criteria_met += 1
                        
        assert criteria_met >= len(config.success_criteria) * 0.6  # 60% of criteria met
        
        logger.info(f"Mixed workload test completed - Score: {result.scalability_score:.1f}, Criteria met: {criteria_met}/{len(config.success_criteria)}")
        
    @pytest.mark.asyncio
    async def test_scalability_regression_detection(self):
        """Test detection of scalability regressions"""
        # Baseline test
        baseline_config = LoadTestConfiguration(
            test_name="Baseline Performance Test",
            test_type=LoadTestType.THROUGHPUT,
            duration_seconds=8.0,
            ramp_up_seconds=2.0,
            ramp_down_seconds=1.0,
            target_load=300,
            max_load=300,
            load_increment=300,
            success_criteria={
                ScalabilityMetric.REQUESTS_PER_SECOND: 250.0,
                ScalabilityMetric.RESPONSE_TIME_P95: 400.0
            },
            resource_limits={},
            warmup_requests=20
        )
        
        baseline_result = await self.load_executor.execute_load_test(baseline_config)
        
        # Simulate system degradation
        self.trading_system.processing_latency_ms *= 2  # Double the latency
        
        # Regression test
        regression_config = LoadTestConfiguration(
            test_name="Regression Detection Test",
            test_type=LoadTestType.THROUGHPUT,
            duration_seconds=8.0,
            ramp_up_seconds=2.0,
            ramp_down_seconds=1.0,
            target_load=300,
            max_load=300,
            load_increment=300,
            success_criteria={
                ScalabilityMetric.REQUESTS_PER_SECOND: 250.0,
                ScalabilityMetric.RESPONSE_TIME_P95: 400.0
            },
            resource_limits={},
            warmup_requests=20
        )
        
        regression_result = await self.load_executor.execute_load_test(regression_config)
        
        # Compare results to detect regression
        baseline_rps = baseline_result.metrics.get(ScalabilityMetric.REQUESTS_PER_SECOND, 0)
        regression_rps = regression_result.metrics.get(ScalabilityMetric.REQUESTS_PER_SECOND, 0)
        
        baseline_p95 = baseline_result.metrics.get(ScalabilityMetric.RESPONSE_TIME_P95, 0)
        regression_p95 = regression_result.metrics.get(ScalabilityMetric.RESPONSE_TIME_P95, 0)
        
        # Detect significant performance degradation
        rps_degradation = (baseline_rps - regression_rps) / max(baseline_rps, 1) * 100
        latency_increase = (regression_p95 - baseline_p95) / max(baseline_p95, 1) * 100
        
        logger.info(f"Performance comparison:")
        logger.info(f"  RPS: {baseline_rps:.1f} -> {regression_rps:.1f} ({rps_degradation:+.1f}%)")
        logger.info(f"  P95 Latency: {baseline_p95:.1f}ms -> {regression_p95:.1f}ms ({latency_increase:+.1f}%)")
        
        # Should detect regression
        assert rps_degradation > 10.0 or latency_increase > 20.0  # Significant degradation detected
        
        # Restore system state
        self.trading_system.processing_latency_ms /= 2
        
    @pytest.mark.asyncio
    async def test_scalability_limits_identification(self):
        """Test identification of system scalability limits"""
        load_levels = [100, 300, 500, 800, 1200, 1600]
        scalability_results = []
        
        for load_level in load_levels:
            config = LoadTestConfiguration(
                test_name=f"Scalability Limit Test - {load_level} RPS",
                test_type=LoadTestType.THROUGHPUT,
                duration_seconds=6.0,
                ramp_up_seconds=1.5,
                ramp_down_seconds=0.5,
                target_load=load_level,
                max_load=load_level,
                load_increment=load_level,
                success_criteria={
                    ScalabilityMetric.ERROR_RATE: 20.0
                },
                resource_limits={},
                warmup_requests=15
            )
            
            result = await self.load_executor.execute_load_test(config)
            
            error_rate = result.metrics.get(ScalabilityMetric.ERROR_RATE, 0)
            actual_rps = result.metrics.get(ScalabilityMetric.REQUESTS_PER_SECOND, 0)
            
            scalability_results.append({
                'target_load': load_level,
                'actual_rps': actual_rps,
                'error_rate': error_rate,
                'scalability_score': result.scalability_score
            })
            
            # Reset system between tests
            self.trading_system.reset_metrics()
            await asyncio.sleep(1.0)
            
            # Stop if error rate becomes too high
            if error_rate > 50.0:
                logger.info(f"Stopping scalability test at {load_level} RPS due to high error rate")
                break
                
        # Analyze scalability curve
        logger.info("Scalability limits analysis:")
        for result in scalability_results:
            logger.info(f"  Target: {result['target_load']} RPS, Actual: {result['actual_rps']:.1f} RPS, Error Rate: {result['error_rate']:.1f}%, Score: {result['scalability_score']:.1f}")
            
        # Should have tested multiple load levels
        assert len(scalability_results) >= 3
        
        # Should show degradation at higher loads
        first_score = scalability_results[0]['scalability_score']
        last_score = scalability_results[-1]['scalability_score']
        assert first_score > last_score  # Performance should degrade under higher load
        
    @pytest.mark.asyncio
    async def test_resource_exhaustion_recovery(self):
        """Test system recovery from resource exhaustion"""
        # Phase 1: Normal load
        normal_config = LoadTestConfiguration(
            test_name="Normal Load Phase",
            test_type=LoadTestType.THROUGHPUT,
            duration_seconds=5.0,
            ramp_up_seconds=1.0,
            ramp_down_seconds=0.5,
            target_load=200,
            max_load=200,
            load_increment=200,
            success_criteria={},
            resource_limits={},
            warmup_requests=10
        )
        
        normal_result = await self.load_executor.execute_load_test(normal_config)
        normal_score = normal_result.scalability_score
        
        # Phase 2: Overload to exhaust resources
        overload_config = LoadTestConfiguration(
            test_name="Resource Exhaustion Phase",
            test_type=LoadTestType.THROUGHPUT,
            duration_seconds=8.0,
            ramp_up_seconds=1.0,
            ramp_down_seconds=1.0,
            target_load=2000,  # Very high load
            max_load=2000,
            load_increment=2000,
            success_criteria={},
            resource_limits={},
            warmup_requests=5
        )
        
        overload_result = await self.load_executor.execute_load_test(overload_config)
        overload_score = overload_result.scalability_score
        
        # Phase 3: Recovery period
        await asyncio.sleep(5.0)  # Allow system to recover
        
        # Reset system state
        self.trading_system.reset_metrics()
        
        # Phase 4: Return to normal load
        recovery_config = LoadTestConfiguration(
            test_name="Recovery Phase",
            test_type=LoadTestType.THROUGHPUT,
            duration_seconds=5.0,
            ramp_up_seconds=1.0,
            ramp_down_seconds=0.5,
            target_load=200,
            max_load=200,
            load_increment=200,
            success_criteria={},
            resource_limits={},
            warmup_requests=10
        )
        
        recovery_result = await self.load_executor.execute_load_test(recovery_config)
        recovery_score = recovery_result.scalability_score
        
        logger.info(f"Resource exhaustion recovery test:")
        logger.info(f"  Normal: {normal_score:.1f}")
        logger.info(f"  Overload: {overload_score:.1f}")
        logger.info(f"  Recovery: {recovery_score:.1f}")
        
        # System should recover reasonably well
        recovery_ratio = recovery_score / max(normal_score, 1)
        assert recovery_ratio > 0.7  # Should recover to at least 70% of original performance
        
        # Overload should show degradation
        assert overload_score < normal_score


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])