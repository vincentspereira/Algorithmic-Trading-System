"""Institutional-Grade Performance Benchmarking Framework

Comprehensive performance testing suite for consolidated indicators measuring:
- Execution times across varying dataset sizes
- Memory usage and resource utilization
- Engine performance comparison (Pandas, Numba, CUDA)
- Baseline metrics establishment for optimization

Compliance: Institutional-Grade Technical Indicator Standards
Author: Vincent S. Pereira
Version: 1.0.0
"""

import time
import psutil
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import json
import logging
from datetime import datetime
import tracemalloc
import gc
from contextlib import contextmanager

try:
    from nautilus_trader_engine.indicators.consolidated_indicators import (
        ConsolidatedIndicators, ComputeEngine, IndicatorResult
    )
    CONSOLIDATED_AVAILABLE = True
except ImportError:
    CONSOLIDATED_AVAILABLE = False
    print("Warning: Consolidated indicators not available for benchmarking")
    
    # Create mock classes for type hints when not available
    class ComputeEngine:
        PANDAS = "pandas"
        AUTO = "auto"
    
    class IndicatorResult:
        pass


@dataclass
class BenchmarkResult:
    """Container for benchmark results with institutional-grade metrics."""
    indicator_name: str
    engine: str
    dataset_size: int
    execution_time: float  # seconds
    memory_peak: float     # MB
    memory_current: float  # MB
    cpu_percent: float
    success: bool
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'indicator_name': self.indicator_name,
            'engine': self.engine,
            'dataset_size': self.dataset_size,
            'execution_time': self.execution_time,
            'memory_peak': self.memory_peak,
            'memory_current': self.memory_current,
            'cpu_percent': self.cpu_percent,
            'success': self.success,
            'error_message': self.error_message,
            'timestamp': self.timestamp.isoformat()
        }


class InstitutionalBenchmarkFramework:
    """Institutional-grade performance benchmarking framework."""
    
    def __init__(self, output_dir: str = "performance/results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.output_dir / 'benchmark.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Benchmark configuration
        self.dataset_sizes = [100, 500, 1000, 2500, 5000, 10000, 25000, 50000]
        self.engines = [ComputeEngine.PANDAS, ComputeEngine.AUTO] if CONSOLIDATED_AVAILABLE else ["pandas", "auto"]
        self.indicators = ['rsi', 'macd', 'bollinger_bands', 'vw_rsi', 'vw_macd']
        
        # Results storage
        self.results: List[BenchmarkResult] = []
        
        self.logger.info("Institutional Benchmark Framework initialized")
        self.logger.info(f"Output directory: {self.output_dir}")
        self.logger.info(f"Dataset sizes: {self.dataset_sizes}")
        self.logger.info(f"Engines: {[e.value if hasattr(e, 'value') else str(e) for e in self.engines]}")
    
    def generate_test_data(self, size: int, seed: int = 42) -> pd.DataFrame:
        """Generate realistic OHLCV test data."""
        np.random.seed(seed)
        
        # Generate realistic price movements
        base_price = 100.0
        returns = np.random.normal(0, 0.02, size)
        prices = [base_price]
        
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        prices = np.array(prices)
        
        # Create OHLC data with realistic spreads
        high = prices * (1 + np.abs(np.random.normal(0, 0.01, size)))
        low = prices * (1 - np.abs(np.random.normal(0, 0.01, size)))
        close = prices
        open_prices = np.roll(close, 1)
        open_prices[0] = base_price
        
        # Generate volume with realistic patterns
        base_volume = 10000
        volume_multiplier = 1 + np.abs(np.random.normal(0, 0.5, size))
        volume = (base_volume * volume_multiplier).astype(int)
        
        # Create date index
        dates = pd.date_range('2020-01-01', periods=size, freq='D')
        
        return pd.DataFrame({
            'open': open_prices,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        }, index=dates)
    
    @contextmanager
    def performance_monitor(self):
        """Context manager for performance monitoring."""
        # Start memory tracking
        tracemalloc.start()
        gc.collect()  # Clean up before measurement
        
        # Get initial CPU usage
        process = psutil.Process()
        cpu_start = process.cpu_percent()
        
        start_time = time.perf_counter()
        
        try:
            yield
        finally:
            end_time = time.perf_counter()
            
            # Get memory usage
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            # Get final CPU usage
            cpu_end = process.cpu_percent()
            
            # Store results in context
            self._last_performance = {
                'execution_time': end_time - start_time,
                'memory_peak': peak / 1024 / 1024,  # Convert to MB
                'memory_current': current / 1024 / 1024,  # Convert to MB
                'cpu_percent': max(cpu_start, cpu_end)
            }
    
    def benchmark_indicator(self, indicator_name: str, engine, 
                          data: pd.DataFrame) -> BenchmarkResult:
        """Benchmark a single indicator with specific engine."""
        if not CONSOLIDATED_AVAILABLE:
            return BenchmarkResult(
                indicator_name=indicator_name,
                engine=str(engine),
                dataset_size=len(data),
                execution_time=0.0,
                memory_peak=0.0,
                memory_current=0.0,
                cpu_percent=0.0,
                success=False,
                error_message="Consolidated indicators not available"
            )
        
        try:
            with self.performance_monitor():
                if indicator_name == 'rsi':
                    result = ConsolidatedIndicators.rsi(
                        data=data['close'], period=14, engine=engine
                    )
                elif indicator_name == 'macd':
                    result = ConsolidatedIndicators.macd(
                        data=data['close'], fast_period=12, slow_period=26, 
                        signal_period=9, engine=engine
                    )
                elif indicator_name == 'bollinger_bands':
                    result = ConsolidatedIndicators.bollinger_bands(
                        data=data['close'], period=20, std_dev=2.0, engine=engine
                    )
                elif indicator_name == 'vw_rsi':
                    result = ConsolidatedIndicators.vw_rsi(
                        price=data['close'], volume=data['volume'], period=14
                    )
                elif indicator_name == 'vw_macd':
                    result = ConsolidatedIndicators.vw_macd(
                        price=data['close'], volume=data['volume'],
                        fast_period=12, slow_period=26, signal_period=9
                    )
                else:
                    raise ValueError(f"Unknown indicator: {indicator_name}")
            
            # Validate result
            if not isinstance(result, IndicatorResult):
                raise ValueError("Invalid result type")
            
            return BenchmarkResult(
                indicator_name=indicator_name,
                engine=str(engine),
                dataset_size=len(data),
                execution_time=self._last_performance['execution_time'],
                memory_peak=self._last_performance['memory_peak'],
                memory_current=self._last_performance['memory_current'],
                cpu_percent=self._last_performance['cpu_percent'],
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"Benchmark failed for {indicator_name} with {engine}: {str(e)}")
            return BenchmarkResult(
                indicator_name=indicator_name,
                engine=str(engine),
                dataset_size=len(data),
                execution_time=0.0,
                memory_peak=0.0,
                memory_current=0.0,
                cpu_percent=0.0,
                success=False,
                error_message=str(e)
            )
    
    def run_comprehensive_benchmark(self) -> List[BenchmarkResult]:
        """Run comprehensive benchmark across all indicators, engines, and dataset sizes."""
        self.logger.info("Starting comprehensive benchmark suite")
        
        total_tests = len(self.indicators) * len(self.engines) * len(self.dataset_sizes)
        current_test = 0
        
        for indicator in self.indicators:
            for engine in self.engines:
                for size in self.dataset_sizes:
                    current_test += 1
                    self.logger.info(
                        f"Running test {current_test}/{total_tests}: "
                        f"{indicator} with {engine} on {size} data points"
                    )
                    
                    # Generate test data
                    data = self.generate_test_data(size)
                    
                    # Run benchmark
                    result = self.benchmark_indicator(indicator, engine, data)
                    self.results.append(result)
                    
                    # Log result
                    if result.success:
                        self.logger.info(
                            f"Success: {result.execution_time:.4f}s, "
                            f"{result.memory_peak:.2f}MB peak memory"
                        )
                    else:
                        self.logger.warning(f"Failed: {result.error_message}")
        
        self.logger.info(f"Benchmark completed. Total results: {len(self.results)}")
        return self.results
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance analysis report."""
        if not self.results:
            return {"error": "No benchmark results available"}
        
        successful_results = [r for r in self.results if r.success]
        
        if not successful_results:
            return {"error": "No successful benchmark results"}
        
        # Calculate statistics
        report = {
            "summary": {
                "total_tests": len(self.results),
                "successful_tests": len(successful_results),
                "success_rate": len(successful_results) / len(self.results) * 100,
                "generated_at": datetime.now().isoformat()
            },
            "performance_metrics": {},
            "engine_comparison": {},
            "scalability_analysis": {},
            "baseline_metrics": {}
        }
        
        # Performance metrics by indicator
        for indicator in self.indicators:
            indicator_results = [r for r in successful_results if r.indicator_name == indicator]
            if indicator_results:
                execution_times = [r.execution_time for r in indicator_results]
                memory_peaks = [r.memory_peak for r in indicator_results]
                
                report["performance_metrics"][indicator] = {
                    "avg_execution_time": np.mean(execution_times),
                    "min_execution_time": np.min(execution_times),
                    "max_execution_time": np.max(execution_times),
                    "std_execution_time": np.std(execution_times),
                    "avg_memory_peak": np.mean(memory_peaks),
                    "max_memory_peak": np.max(memory_peaks)
                }
        
        # Engine comparison
        for engine in self.engines:
            engine_str = str(engine)
            engine_results = [r for r in successful_results if r.engine == engine_str]
            if engine_results:
                execution_times = [r.execution_time for r in engine_results]
                report["engine_comparison"][engine_str] = {
                    "avg_execution_time": np.mean(execution_times),
                    "total_tests": len(engine_results),
                    "performance_score": 1.0 / np.mean(execution_times)  # Higher is better
                }
        
        # Scalability analysis
        for size in self.dataset_sizes:
            size_results = [r for r in successful_results if r.dataset_size == size]
            if size_results:
                execution_times = [r.execution_time for r in size_results]
                report["scalability_analysis"][str(size)] = {
                    "avg_execution_time": np.mean(execution_times),
                    "throughput": size / np.mean(execution_times)  # Records per second
                }
        
        # Baseline metrics for optimization
        all_execution_times = [r.execution_time for r in successful_results]
        all_memory_peaks = [r.memory_peak for r in successful_results]
        
        report["baseline_metrics"] = {
            "overall_avg_execution_time": np.mean(all_execution_times),
            "overall_p95_execution_time": np.percentile(all_execution_times, 95),
            "overall_p99_execution_time": np.percentile(all_execution_times, 99),
            "overall_avg_memory_peak": np.mean(all_memory_peaks),
            "overall_max_memory_peak": np.max(all_memory_peaks)
        }
        
        return report
    
    def save_results(self, filename: str = None) -> str:
        """Save benchmark results to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_results_{timestamp}.json"
        
        filepath = self.output_dir / filename
        
        # Convert results to serializable format
        serializable_results = [result.to_dict() for result in self.results]
        
        # Generate report
        report = self.generate_performance_report()
        
        # Combine results and report
        output_data = {
            "benchmark_results": serializable_results,
            "performance_report": report,
            "metadata": {
                "framework_version": "1.0.0",
                "dataset_sizes": self.dataset_sizes,
                "engines_tested": [str(e) for e in self.engines],
                "indicators_tested": self.indicators
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        self.logger.info(f"Results saved to: {filepath}")
        return str(filepath)
    
    def generate_visualizations(self) -> List[str]:
        """Generate performance visualization charts."""
        if not self.results:
            self.logger.warning("No results available for visualization")
            return []
        
        successful_results = [r for r in self.results if r.success]
        if not successful_results:
            self.logger.warning("No successful results for visualization")
            return []
        
        # Convert to DataFrame for easier plotting
        df = pd.DataFrame([r.to_dict() for r in successful_results])
        
        plt.style.use('seaborn-v0_8')
        generated_files = []
        
        # 1. Execution time by dataset size
        plt.figure(figsize=(12, 8))
        for indicator in self.indicators:
            indicator_data = df[df['indicator_name'] == indicator]
            if not indicator_data.empty:
                plt.plot(indicator_data['dataset_size'], indicator_data['execution_time'], 
                        marker='o', label=indicator, linewidth=2)
        
        plt.xlabel('Dataset Size')
        plt.ylabel('Execution Time (seconds)')
        plt.title('Execution Time vs Dataset Size by Indicator')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xscale('log')
        plt.yscale('log')
        
        filename1 = self.output_dir / 'execution_time_by_size.png'
        plt.savefig(filename1, dpi=300, bbox_inches='tight')
        plt.close()
        generated_files.append(str(filename1))
        
        # 2. Memory usage by dataset size
        plt.figure(figsize=(12, 8))
        for indicator in self.indicators:
            indicator_data = df[df['indicator_name'] == indicator]
            if not indicator_data.empty:
                plt.plot(indicator_data['dataset_size'], indicator_data['memory_peak'], 
                        marker='s', label=indicator, linewidth=2)
        
        plt.xlabel('Dataset Size')
        plt.ylabel('Peak Memory Usage (MB)')
        plt.title('Memory Usage vs Dataset Size by Indicator')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xscale('log')
        
        filename2 = self.output_dir / 'memory_usage_by_size.png'
        plt.savefig(filename2, dpi=300, bbox_inches='tight')
        plt.close()
        generated_files.append(str(filename2))
        
        # 3. Engine performance comparison
        if len(self.engines) > 1:
            plt.figure(figsize=(10, 6))
            engine_performance = df.groupby('engine')['execution_time'].mean()
            bars = plt.bar(engine_performance.index, engine_performance.values)
            plt.xlabel('Compute Engine')
            plt.ylabel('Average Execution Time (seconds)')
            plt.title('Average Performance by Compute Engine')
            plt.yscale('log')
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.4f}s', ha='center', va='bottom')
            
            filename3 = self.output_dir / 'engine_performance_comparison.png'
            plt.savefig(filename3, dpi=300, bbox_inches='tight')
            plt.close()
            generated_files.append(str(filename3))
        
        self.logger.info(f"Generated {len(generated_files)} visualization files")
        return generated_files


def main():
    """Main execution function for benchmark framework."""
    print("Institutional-Grade Performance Benchmarking Framework")
    print("=" * 55)
    
    # Initialize framework
    framework = InstitutionalBenchmarkFramework()
    
    if not CONSOLIDATED_AVAILABLE:
        print("Error: Consolidated indicators not available for benchmarking")
        return
    
    try:
        # Run comprehensive benchmark
        print("\nRunning comprehensive benchmark suite...")
        results = framework.run_comprehensive_benchmark()
        
        # Save results
        print("\nSaving results...")
        results_file = framework.save_results()
        print(f"Results saved to: {results_file}")
        
        # Generate visualizations
        print("\nGenerating visualizations...")
        viz_files = framework.generate_visualizations()
        for viz_file in viz_files:
            print(f"Visualization saved to: {viz_file}")
        
        # Print summary
        report = framework.generate_performance_report()
        if "summary" in report:
            summary = report["summary"]
            print(f"\nBenchmark Summary:")
            print(f"- Total tests: {summary['total_tests']}")
            print(f"- Successful tests: {summary['successful_tests']}")
            print(f"- Success rate: {summary['success_rate']:.1f}%")
            
            if "baseline_metrics" in report:
                baseline = report["baseline_metrics"]
                print(f"\nBaseline Metrics:")
                print(f"- Average execution time: {baseline['overall_avg_execution_time']:.4f}s")
                print(f"- P95 execution time: {baseline['overall_p95_execution_time']:.4f}s")
                print(f"- Average memory peak: {baseline['overall_avg_memory_peak']:.2f}MB")
        
        print("\nBenchmarking completed successfully!")
        
    except Exception as e:
        print(f"Error during benchmarking: {str(e)}")
        framework.logger.error(f"Benchmark failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()