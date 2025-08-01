#!/usr/bin/env python3
"""
Nautilus Trader - Latency Benchmarking Framework

This module provides microsecond-precision latency measurement and analysis
for critical trading operations with detailed percentile reporting and
optimization recommendations.
"""

import time
import asyncio
import statistics
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from concurrent.futures import ThreadPoolExecutor, as_completed
import aiohttp
import websockets
import psutil
import threading
from contextlib import contextmanager
import sys
import os

# High-precision timing imports
if sys.platform == "win32":
    # Windows high-precision timing
    import ctypes
    from ctypes import wintypes
    
    kernel32 = ctypes.windll.kernel32
    kernel32.QueryPerformanceCounter.restype = wintypes.LARGE_INTEGER
    kernel32.QueryPerformanceFrequency.restype = wintypes.LARGE_INTEGER
    
    def get_high_precision_time():
        """Get high-precision time on Windows"""
        counter = wintypes.LARGE_INTEGER()
        frequency = wintypes.LARGE_INTEGER()
        kernel32.QueryPerformanceCounter(ctypes.byref(counter))
        kernel32.QueryPerformanceFrequency(ctypes.byref(frequency))
        return counter.value / frequency.value
else:
    # Unix high-precision timing
    def get_high_precision_time():
        """Get high-precision time on Unix systems"""
        return time.perf_counter()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class LatencyMeasurement:
    """Single latency measurement"""
    operation: str
    start_time: float
    end_time: float
    latency_us: float  # Microseconds
    success: bool
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class LatencyStats:
    """Latency statistics"""
    operation: str
    count: int
    min_latency: float
    max_latency: float
    mean_latency: float
    median_latency: float
    std_latency: float
    p50: float
    p90: float
    p95: float
    p99: float
    p99_9: float
    p99_99: float
    success_rate: float
    
class LatencyBenchmark:
    """High-precision latency benchmarking framework"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.measurements: List[LatencyMeasurement] = []
        self.benchmarks: Dict[str, List[LatencyMeasurement]] = {}
        
    @contextmanager
    def measure_latency(self, operation: str, metadata: Dict[str, Any] = None):
        """Context manager for measuring operation latency"""
        start_time = get_high_precision_time()
        success = True
        error = None
        
        try:
            yield
        except Exception as e:
            success = False
            error = str(e)
            raise
        finally:
            end_time = get_high_precision_time()
            latency_us = (end_time - start_time) * 1_000_000  # Convert to microseconds
            
            measurement = LatencyMeasurement(
                operation=operation,
                start_time=start_time,
                end_time=end_time,
                latency_us=latency_us,
                success=success,
                error=error,
                metadata=metadata or {}
            )
            
            self.measurements.append(measurement)
            
            if operation not in self.benchmarks:
                self.benchmarks[operation] = []
            self.benchmarks[operation].append(measurement)
    
    async def benchmark_api_endpoints(self, iterations: int = 1000) -> Dict[str, LatencyStats]:
        """Benchmark API endpoint latencies"""
        logger.info(f"Benchmarking API endpoints with {iterations} iterations")
        
        endpoints = [
            ("/health", "GET"),
            ("/api/v1/status", "GET"),
            ("/api/v1/portfolio", "GET"),
            ("/api/v1/orders", "GET"),
            ("/api/v1/positions", "GET"),
            ("/api/v1/market-data/AAPL", "GET"),
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint, method in endpoints:
                operation_name = f"{method} {endpoint}"
                logger.info(f"Benchmarking {operation_name}")
                
                for i in range(iterations):
                    with self.measure_latency(operation_name):
                        async with session.request(method, f"{self.base_url}{endpoint}") as response:
                            await response.read()
                    
                    # Small delay to avoid overwhelming the server
                    if i % 100 == 0:
                        await asyncio.sleep(0.01)
        
        return self.calculate_stats()
    
    def benchmark_database_operations(self, iterations: int = 1000) -> Dict[str, LatencyStats]:
        """Benchmark database operation latencies"""
        logger.info(f"Benchmarking database operations with {iterations} iterations")
        
        # Simulate database operations
        import sqlite3
        
        # Create in-memory database for testing
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()
        
        # Create test table
        cursor.execute("""
            CREATE TABLE test_orders (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                quantity INTEGER,
                price REAL,
                timestamp REAL
            )
        """)
        
        # Insert test data
        test_data = [
            (i, f"SYMBOL_{i%10}", i*10, i*1.5, time.time())
            for i in range(1000)
        ]
        cursor.executemany(
            "INSERT INTO test_orders (id, symbol, quantity, price, timestamp) VALUES (?, ?, ?, ?, ?)",
            test_data
        )
        conn.commit()
        
        # Benchmark operations
        operations = [
            ("SELECT * FROM test_orders WHERE id = ?", "select_by_id"),
            ("SELECT * FROM test_orders WHERE symbol = ?", "select_by_symbol"),
            ("INSERT INTO test_orders (symbol, quantity, price, timestamp) VALUES (?, ?, ?, ?)", "insert"),
            ("UPDATE test_orders SET price = ? WHERE id = ?", "update"),
            ("DELETE FROM test_orders WHERE id = ?", "delete"),
        ]
        
        for sql, operation_name in operations:
            logger.info(f"Benchmarking {operation_name}")
            
            for i in range(iterations):
                with self.measure_latency(f"db_{operation_name}"):
                    if operation_name == "select_by_id":
                        cursor.execute(sql, (i % 1000 + 1,))
                        cursor.fetchall()
                    elif operation_name == "select_by_symbol":
                        cursor.execute(sql, (f"SYMBOL_{i%10}",))
                        cursor.fetchall()
                    elif operation_name == "insert":
                        cursor.execute(sql, (f"NEW_SYMBOL_{i}", i, i*2.0, time.time()))
                    elif operation_name == "update":
                        cursor.execute(sql, (i*3.0, i % 1000 + 1))
                    elif operation_name == "delete":
                        cursor.execute(sql, (i % 100 + 2000,))
                    
                    conn.commit()
        
        conn.close()
        return self.calculate_stats()
    
    async def benchmark_websocket_latency(self, iterations: int = 100) -> Dict[str, LatencyStats]:
        """Benchmark WebSocket message latency"""
        logger.info(f"Benchmarking WebSocket latency with {iterations} iterations")
        
        websocket_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
        
        try:
            async with websockets.connect(websocket_url) as websocket:
                # Ping-pong latency test
                for i in range(iterations):
                    message = {"type": "ping", "id": i, "timestamp": time.time()}
                    
                    with self.measure_latency("websocket_ping"):
                        await websocket.send(json.dumps(message))
                        response = await websocket.recv()
                        json.loads(response)  # Parse response
                    
                    await asyncio.sleep(0.01)  # Small delay
                
                # Market data subscription latency
                for i in range(iterations // 2):
                    subscribe_msg = {
                        "type": "subscribe",
                        "channel": "market_data",
                        "symbol": f"SYMBOL_{i%10}"
                    }
                    
                    with self.measure_latency("websocket_subscribe"):
                        await websocket.send(json.dumps(subscribe_msg))
                        response = await websocket.recv()
                        json.loads(response)
                    
                    await asyncio.sleep(0.02)
                    
        except Exception as e:
            logger.error(f"WebSocket benchmark failed: {e}")
        
        return self.calculate_stats()
    
    def benchmark_memory_operations(self, iterations: int = 10000) -> Dict[str, LatencyStats]:
        """Benchmark memory allocation and access latencies"""
        logger.info(f"Benchmarking memory operations with {iterations} iterations")
        
        # List operations
        for i in range(iterations):
            with self.measure_latency("list_append"):
                test_list = []
                test_list.append(i)
        
        # Dictionary operations
        for i in range(iterations):
            with self.measure_latency("dict_access"):
                test_dict = {"key": i}
                value = test_dict["key"]
        
        # Object creation
        for i in range(iterations):
            with self.measure_latency("object_creation"):
                obj = {"id": i, "data": f"test_data_{i}", "timestamp": time.time()}
        
        # String operations
        for i in range(iterations):
            with self.measure_latency("string_format"):
                result = f"Order {i} for symbol AAPL with quantity {i*10}"
        
        return self.calculate_stats()
    
    def benchmark_cpu_intensive_operations(self, iterations: int = 1000) -> Dict[str, LatencyStats]:
        """Benchmark CPU-intensive operations"""
        logger.info(f"Benchmarking CPU operations with {iterations} iterations")
        
        # Mathematical calculations
        for i in range(iterations):
            with self.measure_latency("math_calculation"):
                result = sum(j**2 for j in range(100))
        
        # JSON serialization/deserialization
        test_data = {
            "orders": [
                {"id": i, "symbol": f"SYMBOL_{i}", "quantity": i*10, "price": i*1.5}
                for i in range(100)
            ]
        }
        
        for i in range(iterations):
            with self.measure_latency("json_serialize"):
                json_str = json.dumps(test_data)
            
            with self.measure_latency("json_deserialize"):
                data = json.loads(json_str)
        
        # Sorting operations
        for i in range(iterations):
            test_list = list(range(1000, 0, -1))  # Reverse sorted list
            with self.measure_latency("list_sort"):
                test_list.sort()
        
        return self.calculate_stats()
    
    def calculate_stats(self) -> Dict[str, LatencyStats]:
        """Calculate latency statistics for all operations"""
        stats = {}
        
        for operation, measurements in self.benchmarks.items():
            if not measurements:
                continue
            
            latencies = [m.latency_us for m in measurements]
            successful = [m for m in measurements if m.success]
            success_rate = len(successful) / len(measurements) * 100
            
            if latencies:
                stats[operation] = LatencyStats(
                    operation=operation,
                    count=len(measurements),
                    min_latency=min(latencies),
                    max_latency=max(latencies),
                    mean_latency=statistics.mean(latencies),
                    median_latency=statistics.median(latencies),
                    std_latency=statistics.stdev(latencies) if len(latencies) > 1 else 0,
                    p50=np.percentile(latencies, 50),
                    p90=np.percentile(latencies, 90),
                    p95=np.percentile(latencies, 95),
                    p99=np.percentile(latencies, 99),
                    p99_9=np.percentile(latencies, 99.9),
                    p99_99=np.percentile(latencies, 99.99),
                    success_rate=success_rate
                )
        
        return stats
    
    def generate_latency_report(self, stats: Dict[str, LatencyStats], output_file: str = None) -> str:
        """Generate comprehensive latency report"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"performance/latency_report_{timestamp}.html"
        
        # Create visualizations
        self._create_latency_visualizations(stats)
        
        # Generate HTML report
        html_content = self._generate_latency_html_report(stats)
        
        # Save report
        Path(output_file).parent.mkdir(exist_ok=True)
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        logger.info(f"Latency report generated: {output_file}")
        return output_file
    
    def _create_latency_visualizations(self, stats: Dict[str, LatencyStats]):
        """Create latency visualizations"""
        if not stats:
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # Latency comparison chart
        operations = list(stats.keys())
        mean_latencies = [stats[op].mean_latency for op in operations]
        p95_latencies = [stats[op].p95 for op in operations]
        p99_latencies = [stats[op].p99 for op in operations]
        
        x = np.arange(len(operations))
        width = 0.25
        
        axes[0, 0].bar(x - width, mean_latencies, width, label='Mean', alpha=0.8)
        axes[0, 0].bar(x, p95_latencies, width, label='P95', alpha=0.8)
        axes[0, 0].bar(x + width, p99_latencies, width, label='P99', alpha=0.8)
        axes[0, 0].set_xlabel('Operations')
        axes[0, 0].set_ylabel('Latency (μs)')
        axes[0, 0].set_title('Latency Comparison by Operation')
        axes[0, 0].set_xticks(x)
        axes[0, 0].set_xticklabels(operations, rotation=45, ha='right')
        axes[0, 0].legend()
        axes[0, 0].set_yscale('log')
        
        # Percentile distribution
        percentiles = [50, 90, 95, 99, 99.9, 99.99]
        for i, operation in enumerate(list(operations)[:5]):  # Show top 5 operations
            percentile_values = [
                stats[operation].p50,
                stats[operation].p90,
                stats[operation].p95,
                stats[operation].p99,
                stats[operation].p99_9,
                stats[operation].p99_99
            ]
            axes[0, 1].plot(percentiles, percentile_values, marker='o', label=operation)
        
        axes[0, 1].set_xlabel('Percentile')
        axes[0, 1].set_ylabel('Latency (μs)')
        axes[0, 1].set_title('Latency Percentile Distribution')
        axes[0, 1].legend()
        axes[0, 1].set_yscale('log')
        axes[0, 1].grid(True, alpha=0.3)
        
        # Success rate chart
        success_rates = [stats[op].success_rate for op in operations]
        colors = ['green' if rate >= 99 else 'orange' if rate >= 95 else 'red' for rate in success_rates]
        
        axes[1, 0].bar(operations, success_rates, color=colors, alpha=0.7)
        axes[1, 0].set_xlabel('Operations')
        axes[1, 0].set_ylabel('Success Rate (%)')
        axes[1, 0].set_title('Success Rate by Operation')
        axes[1, 0].set_xticklabels(operations, rotation=45, ha='right')
        axes[1, 0].set_ylim(0, 100)
        
        # Latency distribution histogram for top operation
        if operations:
            top_operation = min(operations, key=lambda op: stats[op].mean_latency)
            top_measurements = self.benchmarks[top_operation]
            latencies = [m.latency_us for m in top_measurements if m.success]
            
            if latencies:
                axes[1, 1].hist(latencies, bins=50, alpha=0.7, color='blue', edgecolor='black')
                axes[1, 1].axvline(stats[top_operation].mean_latency, color='red', linestyle='--', label='Mean')
                axes[1, 1].axvline(stats[top_operation].p95, color='orange', linestyle='--', label='P95')
                axes[1, 1].axvline(stats[top_operation].p99, color='purple', linestyle='--', label='P99')
                axes[1, 1].set_xlabel('Latency (μs)')
                axes[1, 1].set_ylabel('Frequency')
                axes[1, 1].set_title(f'Latency Distribution - {top_operation}')
                axes[1, 1].legend()
        
        plt.tight_layout()
        plt.savefig('performance/latency_charts.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _generate_latency_html_report(self, stats: Dict[str, LatencyStats]) -> str:
        """Generate HTML latency report"""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Nautilus Trader Latency Benchmark Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .header { background-color: #f0f0f0; padding: 20px; border-radius: 5px; }
                .stats-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                .stats-table th, .stats-table td { border: 1px solid #ddd; padding: 8px; text-align: right; }
                .stats-table th { background-color: #f2f2f2; }
                .chart { text-align: center; margin: 20px 0; }
                .recommendations { background-color: #e8f4f8; padding: 15px; border-radius: 5px; margin: 20px 0; }
                .excellent { color: green; } .good { color: orange; } .poor { color: red; }
                .metric-highlight { font-weight: bold; font-size: 1.1em; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Nautilus Trader Latency Benchmark Report</h1>
                <p><strong>Generated:</strong> {timestamp}</p>
                <p><strong>Total Operations:</strong> {total_operations}</p>
                <p><strong>Total Measurements:</strong> {total_measurements}</p>
            </div>
            
            <h2>Latency Statistics</h2>
            <table class="stats-table">
                <thead>
                    <tr>
                        <th>Operation</th>
                        <th>Count</th>
                        <th>Success Rate</th>
                        <th>Mean (μs)</th>
                        <th>Median (μs)</th>
                        <th>P95 (μs)</th>
                        <th>P99 (μs)</th>
                        <th>P99.9 (μs)</th>
                        <th>Max (μs)</th>
                        <th>Std Dev</th>
                    </tr>
                </thead>
                <tbody>
                    {stats_rows}
                </tbody>
            </table>
            
            <h2>Latency Visualizations</h2>
            <div class="chart">
                <img src="latency_charts.png" alt="Latency Charts" style="max-width: 100%;">
            </div>
            
            <h2>Performance Assessment</h2>
            <div class="recommendations">
                {performance_assessment}
            </div>
            
            <h2>Optimization Recommendations</h2>
            <div class="recommendations">
                {optimization_recommendations}
            </div>
        </body>
        </html>
        """
        
        # Generate statistics rows
        stats_rows = []
        for operation, stat in stats.items():
            success_class = "excellent" if stat.success_rate >= 99 else "good" if stat.success_rate >= 95 else "poor"
            latency_class = "excellent" if stat.mean_latency < 1000 else "good" if stat.mean_latency < 10000 else "poor"
            
            row = f"""
            <tr>
                <td style="text-align: left;">{operation}</td>
                <td>{stat.count}</td>
                <td class="{success_class}">{stat.success_rate:.2f}%</td>
                <td class="{latency_class}">{stat.mean_latency:.2f}</td>
                <td>{stat.median_latency:.2f}</td>
                <td>{stat.p95:.2f}</td>
                <td>{stat.p99:.2f}</td>
                <td>{stat.p99_9:.2f}</td>
                <td>{stat.max_latency:.2f}</td>
                <td>{stat.std_latency:.2f}</td>
            </tr>
            """
            stats_rows.append(row)
        
        # Generate performance assessment
        assessment = self._generate_performance_assessment(stats)
        
        # Generate optimization recommendations
        recommendations = self._generate_optimization_recommendations(stats)
        
        return html_template.format(
            timestamp=datetime.now().isoformat(),
            total_operations=len(stats),
            total_measurements=sum(stat.count for stat in stats.values()),
            stats_rows="".join(stats_rows),
            performance_assessment=assessment,
            optimization_recommendations=recommendations
        )
    
    def _generate_performance_assessment(self, stats: Dict[str, LatencyStats]) -> str:
        """Generate performance assessment"""
        assessments = []
        
        # Overall latency assessment
        all_mean_latencies = [stat.mean_latency for stat in stats.values()]
        if all_mean_latencies:
            overall_mean = statistics.mean(all_mean_latencies)
            if overall_mean < 1000:  # < 1ms
                assessments.append('<p class="excellent">✓ Excellent overall latency performance (&lt;1ms average)</p>')
            elif overall_mean < 10000:  # < 10ms
                assessments.append('<p class="good">⚠ Good overall latency performance (&lt;10ms average)</p>')
            else:
                assessments.append('<p class="poor">✗ Poor overall latency performance (&gt;10ms average)</p>')
        
        # Success rate assessment
        all_success_rates = [stat.success_rate for stat in stats.values()]
        if all_success_rates:
            overall_success = statistics.mean(all_success_rates)
            if overall_success >= 99:
                assessments.append('<p class="excellent">✓ Excellent success rate (&gt;99%)</p>')
            elif overall_success >= 95:
                assessments.append('<p class="good">⚠ Good success rate (&gt;95%)</p>')
            else:
                assessments.append('<p class="poor">✗ Poor success rate (&lt;95%)</p>')
        
        # P99 latency assessment
        all_p99_latencies = [stat.p99 for stat in stats.values()]
        if all_p99_latencies:
            max_p99 = max(all_p99_latencies)
            if max_p99 < 10000:  # < 10ms
                assessments.append('<p class="excellent">✓ Excellent P99 latency (&lt;10ms)</p>')
            elif max_p99 < 50000:  # < 50ms
                assessments.append('<p class="good">⚠ Acceptable P99 latency (&lt;50ms)</p>')
            else:
                assessments.append('<p class="poor">✗ High P99 latency (&gt;50ms)</p>')
        
        return "\n".join(assessments)
    
    def _generate_optimization_recommendations(self, stats: Dict[str, LatencyStats]) -> str:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Find slowest operations
        sorted_operations = sorted(stats.items(), key=lambda x: x[1].mean_latency, reverse=True)
        
        if sorted_operations:
            slowest_op, slowest_stats = sorted_operations[0]
            if slowest_stats.mean_latency > 10000:  # > 10ms
                recommendations.append(f'<p><strong>High Priority:</strong> Optimize "{slowest_op}" operation (avg: {slowest_stats.mean_latency:.2f}μs)</p>')
        
        # Check for high variability
        for operation, stat in stats.items():
            if stat.std_latency > stat.mean_latency:  # High variability
                recommendations.append(f'<p><strong>Consistency:</strong> Reduce latency variability in "{operation}" operation</p>')
        
        # Check for low success rates
        for operation, stat in stats.items():
            if stat.success_rate < 95:
                recommendations.append(f'<p><strong>Reliability:</strong> Improve success rate for "{operation}" operation ({stat.success_rate:.2f}%)</p>')
        
        # General recommendations
        recommendations.extend([
            '<p><strong>Database:</strong> Consider connection pooling and query optimization for database operations</p>',
            '<p><strong>Caching:</strong> Implement caching for frequently accessed data</p>',
            '<p><strong>Network:</strong> Use connection keep-alive and HTTP/2 for API calls</p>',
            '<p><strong>Memory:</strong> Optimize object creation and garbage collection</p>',
            '<p><strong>Monitoring:</strong> Set up continuous latency monitoring with alerting</p>'
        ])
        
        return "\n".join(recommendations)
    
    def export_results(self, stats: Dict[str, LatencyStats], format: str = "json") -> str:
        """Export benchmark results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "json":
            output_file = f"performance/latency_results_{timestamp}.json"
            data = {
                "timestamp": datetime.now().isoformat(),
                "stats": {op: asdict(stat) for op, stat in stats.items()}
            }
            
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
        
        elif format == "csv":
            import csv
            output_file = f"performance/latency_results_{timestamp}.csv"
            
            with open(output_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Operation', 'Count', 'Success Rate', 'Mean (μs)', 'Median (μs)',
                    'P95 (μs)', 'P99 (μs)', 'P99.9 (μs)', 'Max (μs)', 'Std Dev'
                ])
                
                for operation, stat in stats.items():
                    writer.writerow([
                        operation, stat.count, stat.success_rate, stat.mean_latency,
                        stat.median_latency, stat.p95, stat.p99, stat.p99_9,
                        stat.max_latency, stat.std_latency
                    ])
        
        logger.info(f"Results exported to: {output_file}")
        return output_file

async def main():
    """Main function for running latency benchmarks"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Nautilus Trader Latency Benchmark')
    parser.add_argument('--base-url', default='http://localhost:8000', help='Base URL for API tests')
    parser.add_argument('--iterations', type=int, default=1000, help='Number of iterations per test')
    parser.add_argument('--test-type', choices=['api', 'database', 'websocket', 'memory', 'cpu', 'all'], 
                       default='all', help='Type of benchmark to run')
    parser.add_argument('--output', help='Output file for report')
    parser.add_argument('--export-format', choices=['json', 'csv'], default='json', help='Export format')
    
    args = parser.parse_args()
    
    benchmark = LatencyBenchmark(args.base_url)
    
    logger.info("Starting latency benchmarks...")
    
    if args.test_type in ['api', 'all']:
        await benchmark.benchmark_api_endpoints(args.iterations)
    
    if args.test_type in ['database', 'all']:
        benchmark.benchmark_database_operations(args.iterations)
    
    if args.test_type in ['websocket', 'all']:
        await benchmark.benchmark_websocket_latency(args.iterations // 10)
    
    if args.test_type in ['memory', 'all']:
        benchmark.benchmark_memory_operations(args.iterations * 10)
    
    if args.test_type in ['cpu', 'all']:
        benchmark.benchmark_cpu_intensive_operations(args.iterations)
    
    # Calculate and display results
    stats = benchmark.calculate_stats()
    
    # Generate report
    report_file = benchmark.generate_latency_report(stats, args.output)
    print(f"Latency report generated: {report_file}")
    
    # Export results
    export_file = benchmark.export_results(stats, args.export_format)
    print(f"Results exported: {export_file}")
    
    # Print summary
    print(f"\nLatency Benchmark Summary:")
    print(f"Total Operations: {len(stats)}")
    print(f"Total Measurements: {sum(stat.count for stat in stats.values())}")
    
    if stats:
        fastest_op = min(stats.items(), key=lambda x: x[1].mean_latency)
        slowest_op = max(stats.items(), key=lambda x: x[1].mean_latency)
        
        print(f"Fastest Operation: {fastest_op[0]} ({fastest_op[1].mean_latency:.2f}μs)")
        print(f"Slowest Operation: {slowest_op[0]} ({slowest_op[1].mean_latency:.2f}μs)")

if __name__ == "__main__":
    asyncio.run(main())