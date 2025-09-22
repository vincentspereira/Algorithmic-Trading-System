"""
Performance Benchmarks for Nautilus Trader Engine
Comprehensive benchmarking suite for measuring system performance.
"""

import time
import psutil
import cProfile
import io
import pstats
import gc
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
import json
import csv
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nautilus_trader_engine.core.base.dependency_injection import DependencyContainer
from nautilus_trader_engine.core.base.event_system import EventSystem, Event
from nautilus_trader_engine.core.caching.cache_layer import MultiLevelCache, CacheLevel
from nautilus_trader_engine.core.streaming.streaming_architecture import (
    StreamManager, StreamPipeline, StreamMessage, StreamType,
    MarketDataProcessor, TechnicalIndicatorProcessor
)
from nautilus_trader_engine.engines.parallel_processing_engine import ParallelProcessor
from nautilus_trader_engine.analysis.indicators.adaptive_parameters import AdaptiveParameterManager
from nautilus_trader_engine.analysis.indicators.ensemble_methods import IndicatorEnsemble


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""
    name: str
    execution_time: float
    throughput: float
    memory_usage: float
    cpu_usage: float
    iterations: int
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkSuite:
    """Collection of benchmark results."""
    name: str
    results: List[BenchmarkResult] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    system_info: Dict[str, Any] = field(default_factory=dict)


class PerformanceBenchmarker:
    """Main performance benchmarking class."""

    def __init__(self):
        self.results = []
        self.system_info = self._collect_system_info()

    def _collect_system_info(self) -> Dict[str, Any]:
        """Collect system information for benchmark context."""
        return {
            'cpu_count': psutil.cpu_count(),
            'cpu_count_logical': psutil.cpu_count(logical=True),
            'memory_total': psutil.virtual_memory().total,
            'memory_available': psutil.virtual_memory().available,
            'python_version': sys.version,
            'platform': sys.platform,
            'hostname': psutil.os.uname().node
        }

    def benchmark_function(self, func: Callable, name: str,
                          iterations: int = 100, warmup_iterations: int = 10,
                          **kwargs) -> BenchmarkResult:
        """Benchmark a function with detailed metrics."""
        # Warmup
        for _ in range(warmup_iterations):
            func(**kwargs)

        # Force garbage collection
        gc.collect()

        # Measure initial memory and CPU
        initial_memory = psutil.Process().memory_info().rss
        initial_cpu = psutil.cpu_percent(interval=None)

        # Execute benchmark
        start_time = time.perf_counter()
        cpu_samples = []

        for i in range(iterations):
            # Sample CPU usage
            if i % 10 == 0:
                cpu_samples.append(psutil.cpu_percent(interval=None))

            func(**kwargs)

        end_time = time.perf_counter()

        # Measure final memory and CPU
        final_memory = psutil.Process().memory_info().rss
        final_cpu = psutil.cpu_percent(interval=None)

        # Calculate metrics
        execution_time = end_time - start_time
        throughput = iterations / execution_time if execution_time > 0 else 0
        memory_usage = final_memory - initial_memory
        avg_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0

        result = BenchmarkResult(
            name=name,
            execution_time=execution_time,
            throughput=throughput,
            memory_usage=memory_usage,
            cpu_usage=avg_cpu,
            iterations=iterations,
            metadata={
                'function': func.__name__,
                'kwargs': kwargs,
                'warmup_iterations': warmup_iterations
            }
        )

        self.results.append(result)
        return result

    def profile_function(self, func: Callable, name: str, **kwargs) -> str:
        """Profile a function using cProfile."""
        profiler = cProfile.Profile()
        profiler.enable()

        try:
            func(**kwargs)
        finally:
            profiler.disable()

        # Get profile stats
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(20)  # Top 20 functions

        return s.getvalue()


class CoreBenchmarks:
    """Benchmarks for core system components."""

    def __init__(self, benchmarker: PerformanceBenchmarker):
        self.benchmarker = benchmarker

    def benchmark_dependency_injection(self) -> List[BenchmarkResult]:
        """Benchmark dependency injection performance."""
        results = []

        container = DependencyContainer()

        # Register services
        for i in range(100):
            @container.injectable()
            class TestService:
                def __init__(self):
                    self.value = i

            container.register(TestService, name=f"TestService{i}")

        # Benchmark service resolution
        def resolve_service():
            service = container.resolve("TestService50")
            return service.value

        result = self.benchmarker.benchmark_function(
            resolve_service,
            "dependency_injection_resolution",
            iterations=1000
        )
        results.append(result)

        return results

    def benchmark_event_system(self) -> List[BenchmarkResult]:
        """Benchmark event system performance."""
        results = []

        event_system = EventSystem()

        # Register multiple handlers
        events_received = []
        def event_handler(event: Event):
            events_received.append(event)

        for i in range(10):
            event_system.subscribe("benchmark_event", event_handler)

        # Benchmark event publishing
        def publish_event():
            event = Event("benchmark_event", {"data": "test"})
            event_system.publish(event)

        result = self.benchmarker.benchmark_function(
            publish_event,
            "event_system_publishing",
            iterations=1000
        )
        results.append(result)

        return results

    def benchmark_caching(self) -> List[BenchmarkResult]:
        """Benchmark caching system performance."""
        results = []

        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = MultiLevelCache(
                levels=[CacheLevel.L1_MEMORY, CacheLevel.L3_DISK],
                memory_size=10000,
                disk_config={"cache_dir": temp_dir, "max_size_mb": 10}
            )

            test_data = {"key": "value", "numbers": list(range(100))}

            # Benchmark cache set
            def cache_set():
                cache.set(f"key_{np.random.randint(0, 1000)}", test_data)

            set_result = self.benchmarker.benchmark_function(
                cache_set,
                "cache_set_operation",
                iterations=1000
            )
            results.append(set_result)

            # Benchmark cache get
            def cache_get():
                result = cache.get(f"key_{np.random.randint(0, 1000)}")
                return result

            get_result = self.benchmarker.benchmark_function(
                cache_get,
                "cache_get_operation",
                iterations=1000
            )
            results.append(get_result)

        return results


class StreamingBenchmarks:
    """Benchmarks for streaming components."""

    def __init__(self, benchmarker: PerformanceBenchmarker):
        self.benchmarker = benchmarker
        self.stream_manager = StreamManager()

    async def benchmark_stream_processing(self) -> List[BenchmarkResult]:
        """Benchmark streaming pipeline performance."""
        results = []

        # Create pipeline
        pipeline = self.stream_manager.create_pipeline("benchmark_pipeline")
        market_processor = MarketDataProcessor("BENCH")
        indicator_processor = TechnicalIndicatorProcessor(['SMA'])

        pipeline.add_processor(market_processor)
        pipeline.add_processor(indicator_processor)

        output_queue = asyncio.Queue()
        pipeline.add_output_queue("output", output_queue)

        await pipeline.start()

        # Generate test messages
        messages = []
        for i in range(1000):
            message = StreamMessage(
                stream_type=StreamType.MARKET_DATA,
                symbol="BENCH",
                timestamp=datetime.now(),
                data={
                    'open': 100.0 + i * 0.01,
                    'high': 101.0 + i * 0.01,
                    'low': 99.0 + i * 0.01,
                    'close': 100.5 + i * 0.01,
                    'volume': 100000 + i * 10
                },
                sequence_number=i
            )
            messages.append(message)

        # Benchmark message ingestion
        start_time = time.perf_counter()

        for msg in messages:
            await pipeline.ingest_message(msg)

        # Wait for processing
        await asyncio.sleep(2)

        processing_time = time.perf_counter() - start_time

        # Count processed messages
        processed_count = 0
        try:
            while True:
                result = output_queue.get_nowait()
                processed_count += 1
                output_queue.task_done()
        except asyncio.QueueEmpty:
            pass

        await pipeline.stop()

        # Create benchmark result
        result = BenchmarkResult(
            name="stream_processing",
            execution_time=processing_time,
            throughput=len(messages) / processing_time if processing_time > 0 else 0,
            memory_usage=0,  # Would need to measure separately
            cpu_usage=0,     # Would need to measure separately
            iterations=len(messages),
            metadata={
                'messages_sent': len(messages),
                'messages_processed': processed_count,
                'processing_efficiency': processed_count / len(messages)
            }
        )

        results.append(result)
        return results


class IndicatorBenchmarks:
    """Benchmarks for technical indicators."""

    def __init__(self, benchmarker: PerformanceBenchmarker):
        self.benchmarker = benchmarker

    def benchmark_indicator_calculation(self) -> List[BenchmarkResult]:
        """Benchmark technical indicator calculations."""
        results = []

        # Create large dataset
        dates = pd.date_range('2023-01-01', periods=10000, freq='5min')
        data = pd.DataFrame({
            'open': np.random.uniform(100, 110, 10000),
            'high': np.random.uniform(105, 115, 10000),
            'low': np.random.uniform(95, 105, 10000),
            'close': np.random.uniform(100, 110, 10000),
            'volume': np.random.uniform(1000000, 5000000, 10000)
        }, index=dates)

        # Benchmark individual indicators
        indicators = [
            ('SMA_20', lambda: data['close'].rolling(20).mean()),
            ('EMA_20', lambda: data['close'].ewm(span=20).mean()),
            ('RSI_14', lambda: self._calculate_rsi(data['close'], 14)),
            ('MACD', lambda: self._calculate_macd(data['close'])),
            ('BollingerBands', lambda: self._calculate_bollinger_bands(data['close'], 20))
        ]

        for name, indicator_func in indicators:
            result = self.benchmarker.benchmark_function(
                indicator_func,
                f"indicator_{name}",
                iterations=10
            )
            results.append(result)

        return results

    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_macd(self, prices: pd.Series) -> pd.DataFrame:
        """Calculate MACD indicator."""
        ema_12 = prices.ewm(span=12).mean()
        ema_26 = prices.ewm(span=26).mean()
        macd_line = ema_12 - ema_26
        signal_line = macd_line.ewm(span=9).mean()
        histogram = macd_line - signal_line

        return pd.DataFrame({
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        })

    def _calculate_bollinger_bands(self, prices: pd.Series, period: int) -> pd.DataFrame:
        """Calculate Bollinger Bands."""
        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        upper_band = sma + (std * 2)
        lower_band = sma - (std * 2)

        return pd.DataFrame({
            'upper': upper_band,
            'middle': sma,
            'lower': lower_band
        })


class ParallelBenchmarks:
    """Benchmarks for parallel processing."""

    def __init__(self, benchmarker: PerformanceBenchmarker):
        self.benchmarker = benchmarker

    def benchmark_parallel_processing(self) -> List[BenchmarkResult]:
        """Benchmark parallel processing performance."""
        results = []

        processor = ParallelProcessor()

        # Create test data
        dates = pd.date_range('2023-01-01', periods=5000, freq='5min')
        data = pd.DataFrame({
            'open': np.random.uniform(100, 110, 5000),
            'high': np.random.uniform(105, 115, 5000),
            'low': np.random.uniform(95, 105, 5000),
            'close': np.random.uniform(100, 110, 5000),
            'volume': np.random.uniform(1000000, 5000000, 5000)
        }, index=dates)

        indicators = [
            {'name': 'SMA', 'parameters': {'period': 20}},
            {'name': 'EMA', 'parameters': {'period': 20}},
            {'name': 'RSI', 'parameters': {'period': 14}}
        ]

        # Benchmark parallel calculation
        async def run_parallel_benchmark():
            start_time = time.perf_counter()
            parallel_results = await processor.calculate_indicators_parallel(data, indicators)
            parallel_time = time.perf_counter() - start_time
            return parallel_time, parallel_results

        # Benchmark sequential calculation
        def run_sequential_benchmark():
            start_time = time.perf_counter()
            sequential_results = {}
            for indicator in indicators:
                # Simplified sequential calculation
                if indicator['name'] == 'SMA':
                    sequential_results[f"SMA_{indicator['parameters']['period']}"] = data['close'].rolling(20).mean()
                elif indicator['name'] == 'EMA':
                    sequential_results[f"EMA_{indicator['parameters']['period']}"] = data['close'].ewm(span=20).mean()
                elif indicator['name'] == 'RSI':
                    sequential_results[f"RSI_{indicator['parameters']['period']}"] = self._calculate_rsi_simple(data['close'], 14)
            sequential_time = time.perf_counter() - start_time
            return sequential_time, sequential_results

        # Run benchmarks
        parallel_time, _ = asyncio.run(run_parallel_benchmark())
        sequential_time, _ = run_sequential_benchmark()

        # Create benchmark results
        parallel_result = BenchmarkResult(
            name="parallel_indicator_calculation",
            execution_time=parallel_time,
            throughput=len(indicators) / parallel_time if parallel_time > 0 else 0,
            memory_usage=0,
            cpu_usage=0,
            iterations=1,
            metadata={'type': 'parallel', 'indicators': len(indicators)}
        )

        sequential_result = BenchmarkResult(
            name="sequential_indicator_calculation",
            execution_time=sequential_time,
            throughput=len(indicators) / sequential_time if sequential_time > 0 else 0,
            memory_usage=0,
            cpu_usage=0,
            iterations=1,
            metadata={'type': 'sequential', 'indicators': len(indicators)}
        )

        results.extend([parallel_result, sequential_result])
        return results

    def _calculate_rsi_simple(self, prices: pd.Series, period: int) -> pd.Series:
        """Simple RSI calculation for benchmarking."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))


class BenchmarkReportGenerator:
    """Generate comprehensive benchmark reports."""

    def __init__(self, benchmarker: PerformanceBenchmarker):
        self.benchmarker = benchmarker

    def generate_report(self, output_dir: str = "docs/benchmarks") -> str:
        """Generate comprehensive benchmark report."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Create benchmark suite
        suite = BenchmarkSuite(
            name="Nautilus Trader Engine Performance Benchmarks",
            results=self.benchmarker.results,
            end_time=datetime.now(),
            system_info=self.benchmarker.system_info
        )

        # Generate different report formats
        self._generate_json_report(suite, output_path)
        self._generate_csv_report(suite, output_path)
        self._generate_markdown_report(suite, output_path)

        return self._generate_summary_report(suite)

    def _generate_json_report(self, suite: BenchmarkSuite, output_path: Path):
        """Generate JSON benchmark report."""
        def serialize_result(result: BenchmarkResult) -> Dict[str, Any]:
            return {
                'name': result.name,
                'execution_time': result.execution_time,
                'throughput': result.throughput,
                'memory_usage': result.memory_usage,
                'cpu_usage': result.cpu_usage,
                'iterations': result.iterations,
                'timestamp': result.timestamp.isoformat(),
                'metadata': result.metadata
            }

        data = {
            'suite_name': suite.name,
            'start_time': suite.start_time.isoformat(),
            'end_time': suite.end_time.isoformat() if suite.end_time else None,
            'system_info': suite.system_info,
            'results': [serialize_result(r) for r in suite.results]
        }

        with open(output_path / "benchmark_results.json", 'w') as f:
            json.dump(data, f, indent=2)

    def _generate_csv_report(self, suite: BenchmarkSuite, output_path: Path):
        """Generate CSV benchmark report."""
        with open(output_path / "benchmark_results.csv", 'w', newline='') as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow([
                'Benchmark Name', 'Execution Time', 'Throughput',
                'Memory Usage', 'CPU Usage', 'Iterations', 'Timestamp'
            ])

            # Write results
            for result in suite.results:
                writer.writerow([
                    result.name,
                    result.execution_time,
                    result.throughput,
                    result.memory_usage,
                    result.cpu_usage,
                    result.iterations,
                    result.timestamp.isoformat()
                ])

    def _generate_markdown_report(self, suite: BenchmarkSuite, output_path: Path):
        """Generate Markdown benchmark report."""
        lines = []

        lines.append("# Nautilus Trader Engine Performance Benchmarks")
        lines.append("")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # System information
        lines.append("## System Information")
        lines.append("")
        for key, value in suite.system_info.items():
            lines.append(f"- **{key}:** {value}")
        lines.append("")

        # Benchmark results
        lines.append("## Benchmark Results")
        lines.append("")

        lines.append("| Benchmark | Execution Time | Throughput | Memory Usage | CPU Usage | Iterations |")
        lines.append("|-----------|----------------|------------|--------------|-----------|------------|")

        for result in suite.results:
            lines.append(".4f")

        lines.append("")
        lines.append("## Performance Analysis")
        lines.append("")

        # Calculate summary statistics
        if suite.results:
            avg_execution_time = sum(r.execution_time for r in suite.results) / len(suite.results)
            avg_throughput = sum(r.throughput for r in suite.results) / len(suite.results)
            total_memory = sum(r.memory_usage for r in suite.results)

            lines.append(".4f")
            lines.append(".2f")
            lines.append(f"- **Total Memory Usage:** {total_memory} bytes")
            lines.append(f"- **Total Benchmarks:** {len(suite.results)}")

        with open(output_path / "benchmark_report.md", 'w') as f:
            f.write('\n'.join(lines))

    def _generate_summary_report(self, suite: BenchmarkSuite) -> str:
        """Generate summary report for console output."""
        lines = []

        lines.append("Nautilus Trader Engine Performance Benchmarks")
        lines.append("=" * 50)
        lines.append("")

        lines.append(f"System: {suite.system_info.get('hostname', 'Unknown')}")
        lines.append(f"CPU Cores: {suite.system_info.get('cpu_count', 'Unknown')}")
        lines.append(f"Memory: {suite.system_info.get('memory_total', 0) // (1024**3)} GB")
        lines.append("")

        lines.append("Benchmark Results:")
        lines.append("-" * 30)

        for result in suite.results:
            lines.append(f"{result.name}:")
            lines.append(".4f")
            lines.append(".2f")
            lines.append(f"  Memory: {result.memory_usage} bytes")
            lines.append(f"  CPU: {result.cpu_usage:.1f}%")
            lines.append("")

        return '\n'.join(lines)


def run_comprehensive_benchmarks():
    """Run comprehensive benchmark suite."""
    print("Starting Nautilus Trader Engine Performance Benchmarks...")
    print("=" * 60)

    benchmarker = PerformanceBenchmarker()

    # Run core benchmarks
    print("Running core system benchmarks...")
    core_benchmarks = CoreBenchmarks(benchmarker)
    core_benchmarks.benchmark_dependency_injection()
    core_benchmarks.benchmark_event_system()
    core_benchmarks.benchmark_caching()

    # Run streaming benchmarks
    print("Running streaming benchmarks...")
    streaming_benchmarks = StreamingBenchmarks(benchmarker)
    asyncio.run(streaming_benchmarks.benchmark_stream_processing())

    # Run indicator benchmarks
    print("Running indicator benchmarks...")
    indicator_benchmarks = IndicatorBenchmarks(benchmarker)
    indicator_benchmarks.benchmark_indicator_calculation()

    # Run parallel benchmarks
    print("Running parallel processing benchmarks...")
    parallel_benchmarks = ParallelBenchmarks(benchmarker)
    parallel_benchmarks.benchmark_parallel_processing()

    # Generate reports
    print("Generating benchmark reports...")
    report_generator = BenchmarkReportGenerator(benchmarker)
    summary = report_generator.generate_report()

    print("\nBenchmark Summary:")
    print(summary)

    print("Benchmark reports generated in docs/benchmarks/")
    return benchmarker.results


if __name__ == "__main__":
    results = run_comprehensive_benchmarks()
    print(f"\nCompleted {len(results)} benchmarks successfully!")