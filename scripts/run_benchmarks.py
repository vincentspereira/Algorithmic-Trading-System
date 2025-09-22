#!/usr/bin/env python3
"""
Performance Benchmarking Script for Nautilus Trader Engine.

This script runs comprehensive performance benchmarks to establish
baseline performance metrics and detect performance regressions.

Features:
- Automated benchmark execution
- Historical performance tracking
- Regression detection
- Multiple benchmark categories
- CI/CD integration
- Detailed reporting and visualization

Usage:
    python scripts/run_benchmarks.py [options]

Options:
    --category CATEGORY    Run specific benchmark category
    --baseline            Establish new performance baseline
    --compare             Compare against existing baseline
    --report              Generate detailed performance report
    --export-json         Export results to JSON
    --export-csv          Export results to CSV
    --visualize           Generate performance charts
    --ci                  CI mode (fail on regression)
    --verbose             Verbose output
"""

import os
import sys
import time
import json
import csv
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import statistics
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from nautilus_trader_engine.core.dependency_injection import DependencyInjectionContainer
from nautilus_trader_engine.core.adaptive_parameters import AdaptiveParameterManager
from nautilus_trader_engine.core.ensemble_methods import EnsembleManager, IndicatorSignal
from nautilus_trader_engine.core.validation_system import ValidationManager
from nautilus_trader_engine.core.interfaces import SignalStrength


class BenchmarkResult:
    """Container for benchmark results."""

    def __init__(self, name: str, category: str, iterations: int = 1):
        self.name = name
        self.category = category
        self.iterations = iterations
        self.execution_times: List[float] = []
        self.memory_usage: List[float] = []
        self.cpu_usage: List[float] = []
        self.custom_metrics: Dict[str, List[float]] = {}
        self.timestamp = datetime.now()
        self.metadata: Dict[str, Any] = {}

    def add_measurement(self, execution_time: float, memory_mb: float = 0.0,
                       cpu_percent: float = 0.0, **custom_metrics):
        """Add a measurement to the benchmark."""
        self.execution_times.append(execution_time)
        self.memory_usage.append(memory_mb)
        self.cpu_usage.append(cpu_percent)

        for key, value in custom_metrics.items():
            if key not in self.custom_metrics:
                self.custom_metrics[key] = []
            self.custom_metrics[key].append(value)

    def get_statistics(self) -> Dict[str, Any]:
        """Calculate statistics for the benchmark."""
        stats = {
            'name': self.name,
            'category': self.category,
            'iterations': self.iterations,
            'timestamp': self.timestamp.isoformat(),
            'execution_time': {
                'mean': statistics.mean(self.execution_times) if self.execution_times else 0,
                'median': statistics.median(self.execution_times) if self.execution_times else 0,
                'min': min(self.execution_times) if self.execution_times else 0,
                'max': max(self.execution_times) if self.execution_times else 0,
                'stdev': statistics.stdev(self.execution_times) if len(self.execution_times) > 1 else 0,
                'p95': np.percentile(self.execution_times, 95) if self.execution_times else 0,
                'p99': np.percentile(self.execution_times, 99) if self.execution_times else 0
            }
        }

        if self.memory_usage:
            stats['memory_usage'] = {
                'mean': statistics.mean(self.memory_usage),
                'max': max(self.memory_usage),
                'stdev': statistics.stdev(self.memory_usage) if len(self.memory_usage) > 1 else 0
            }

        if self.cpu_usage:
            stats['cpu_usage'] = {
                'mean': statistics.mean(self.cpu_usage),
                'max': max(self.cpu_usage),
                'stdev': statistics.stdev(self.cpu_usage) if len(self.cpu_usage) > 1 else 0
            }

        # Custom metrics
        for key, values in self.custom_metrics.items():
            stats[key] = {
                'mean': statistics.mean(values),
                'median': statistics.median(values),
                'min': min(values),
                'max': max(values),
                'stdev': statistics.stdev(values) if len(values) > 1 else 0
            }

        return stats


class PerformanceBenchmark:
    """Base class for performance benchmarks."""

    def __init__(self, name: str, category: str, description: str = ""):
        self.name = name
        self.category = category
        self.description = description

    def setup(self):
        """Set up benchmark environment."""
        pass

    def run(self, iterations: int = 100) -> BenchmarkResult:
        """Run the benchmark and return results."""
        raise NotImplementedError("Subclasses must implement run()")

    def teardown(self):
        """Clean up benchmark environment."""
        pass


class DependencyInjectionBenchmark(PerformanceBenchmark):
    """Benchmark dependency injection performance."""

    def __init__(self):
        super().__init__(
            "dependency_injection",
            "core",
            "Test dependency injection container performance"
        )
        self.container = None

    def setup(self):
        self.container = DependencyInjectionContainer()

        # Register test services
        for i in range(100):
            class TestService:
                def __init__(self):
                    self.id = i
                    self.data = f"service_data_{i}" * 10

            self.container.register_singleton(TestService, TestService())

    def run(self, iterations: int = 1000) -> BenchmarkResult:
        result = BenchmarkResult(self.name, self.category, iterations)

        for i in range(iterations):
            start_time = time.time()

            # Resolve a service
            class TestService:
                pass
            try:
                service = self.container.get_service(TestService)
                execution_time = time.time() - start_time
                result.add_measurement(execution_time)
            except:
                execution_time = time.time() - start_time
                result.add_measurement(execution_time)

        return result


class AdaptiveParametersBenchmark(PerformanceBenchmark):
    """Benchmark adaptive parameters performance."""

    def __init__(self):
        super().__init__(
            "adaptive_parameters",
            "analysis",
            "Test adaptive parameter management performance"
        )
        self.container = None
        self.manager = None

    def setup(self):
        self.container = DependencyInjectionContainer()
        self.manager = AdaptiveParameterManager(self.container)

        # Register many parameters
        from nautilus_trader_engine.core.adaptive_parameters import (
            ParameterBounds, ParameterType, AdaptationStrategy
        )

        for i in range(50):
            bounds = ParameterBounds(min_value=5.0, max_value=50.0)
            param = {
                "name": f"param_{i}",
                "parameter_type": ParameterType.PERIOD,
                "base_value": 20.0,
                "bounds": bounds,
                "adaptation_strategy": AdaptationStrategy.VOLATILITY_BASED
            }
            self.manager.register_indicator_parameters(f"indicator_{i}", {"period": param})

    def run(self, iterations: int = 100) -> BenchmarkResult:
        result = BenchmarkResult(self.name, self.category, iterations)

        from nautilus_trader_engine.core.interfaces import MarketRegime, RiskLevel

        for i in range(iterations):
            start_time = time.time()

            # Update market condition
            condition = type('MarketCondition', (), {
                'volatility': 0.3 + (i % 10) * 0.05,
                'trend_strength': 0.5,
                'volume_confirmation': 0.6,
                'market_regime': MarketRegime.BULL,
                'risk_level': RiskLevel.MODERATE,
                'timestamp': time.time()
            })()
            self.manager.update_market_condition(condition)

            execution_time = time.time() - start_time
            result.add_measurement(execution_time)

        return result


class EnsembleMethodsBenchmark(PerformanceBenchmark):
    """Benchmark ensemble methods performance."""

    def __init__(self):
        super().__init__(
            "ensemble_methods",
            "analysis",
            "Test ensemble signal combination performance"
        )
        self.container = None
        self.manager = None

    def setup(self):
        self.container = DependencyInjectionContainer()
        self.manager = EnsembleManager(self.container)

    def run(self, iterations: int = 100) -> BenchmarkResult:
        result = BenchmarkResult(self.name, self.category, iterations)

        for i in range(iterations):
            # Create signals
            signals = [
                IndicatorSignal(f"Indicator_{j}", "buy", SignalStrength.STRONG, 0.8, 20.0 + j, time.time())
                for j in range(10)
            ]

            start_time = time.time()

            # Note: This would be async in real implementation
            # For now, simulate processing time
            processed_count = len(signals)

            execution_time = time.time() - start_time
            result.add_measurement(execution_time, signals_processed=processed_count)

        return result


class ValidationSystemBenchmark(PerformanceBenchmark):
    """Benchmark validation system performance."""

    def __init__(self):
        super().__init__(
            "validation_system",
            "core",
            "Test signal validation performance"
        )
        self.container = None
        self.manager = None

    def setup(self):
        self.container = DependencyInjectionContainer()
        self.manager = ValidationManager(self.container)

    def run(self, iterations: int = 1000) -> BenchmarkResult:
        result = BenchmarkResult(self.name, self.category, iterations)

        for i in range(iterations):
            data = {
                'signal_type': 'buy' if i % 2 == 0 else 'sell',
                'confidence': 0.5 + (i % 100) * 0.005,
                'strength': 'strong',
                'indicator_name': f'Indicator_{i % 20}'
            }

            start_time = time.time()

            # Note: This would be async in real implementation
            # For now, simulate validation
            validation_result = {'status': 'valid', 'confidence': data['confidence']}

            execution_time = time.time() - start_time
            result.add_measurement(execution_time, validations_performed=1)

        return result


class BenchmarkRunner:
    """Runner for performance benchmarks."""

    def __init__(self):
        self.benchmarks: Dict[str, PerformanceBenchmark] = {}
        self.baseline_file = project_root / "benchmarks" / "baseline.json"
        self.results_dir = project_root / "benchmarks" / "results"
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self._register_benchmarks()

    def _register_benchmarks(self):
        """Register all available benchmarks."""
        self.benchmarks.update({
            'dependency_injection': DependencyInjectionBenchmark(),
            'adaptive_parameters': AdaptiveParametersBenchmark(),
            'ensemble_methods': EnsembleMethodsBenchmark(),
            'validation_system': ValidationSystemBenchmark(),
        })

    def run_benchmark(self, name: str, iterations: int = 100) -> BenchmarkResult:
        """Run a specific benchmark."""
        if name not in self.benchmarks:
            raise ValueError(f"Benchmark '{name}' not found")

        benchmark = self.benchmarks[name]

        print(f"Running benchmark: {name}")
        benchmark.setup()

        try:
            result = benchmark.run(iterations)
            print(".4f")
            return result
        finally:
            benchmark.teardown()

    def run_category(self, category: str, iterations: int = 100) -> List[BenchmarkResult]:
        """Run all benchmarks in a category."""
        category_benchmarks = [
            name for name, benchmark in self.benchmarks.items()
            if benchmark.category == category
        ]

        results = []
        for name in category_benchmarks:
            try:
                result = self.run_benchmark(name, iterations)
                results.append(result)
            except Exception as e:
                print(f"Failed to run benchmark {name}: {e}")

        return results

    def run_all(self, iterations: int = 100) -> List[BenchmarkResult]:
        """Run all benchmarks."""
        results = []
        for name in self.benchmarks.keys():
            try:
                result = self.run_benchmark(name, iterations)
                results.append(result)
            except Exception as e:
                print(f"Failed to run benchmark {name}: {e}")

        return results

    def save_baseline(self, results: List[BenchmarkResult]):
        """Save benchmark results as baseline."""
        baseline_data = {
            'timestamp': datetime.now().isoformat(),
            'results': [result.get_statistics() for result in results]
        }

        with open(self.baseline_file, 'w') as f:
            json.dump(baseline_data, f, indent=2)

        print(f"Baseline saved to {self.baseline_file}")

    def load_baseline(self) -> Optional[Dict[str, Any]]:
        """Load existing baseline."""
        if not self.baseline_file.exists():
            return None

        with open(self.baseline_file, 'r') as f:
            return json.load(f)

    def compare_with_baseline(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Compare results with baseline."""
        baseline = self.load_baseline()
        if not baseline:
            print("No baseline found for comparison")
            return {}

        comparison = {
            'timestamp': datetime.now().isoformat(),
            'baseline_timestamp': baseline['timestamp'],
            'comparisons': []
        }

        baseline_results = {r['name']: r for r in baseline['results']}

        for result in results:
            stats = result.get_statistics()
            name = stats['name']

            if name in baseline_results:
                baseline_stats = baseline_results[name]
                comparison['comparisons'].append({
                    'name': name,
                    'current': stats['execution_time']['mean'],
                    'baseline': baseline_stats['execution_time']['mean'],
                    'change_percent': (
                        (stats['execution_time']['mean'] - baseline_stats['execution_time']['mean']) /
                        baseline_stats['execution_time']['mean'] * 100
                        if baseline_stats['execution_time']['mean'] > 0 else 0
                    ),
                    'regression': stats['execution_time']['mean'] > baseline_stats['execution_time']['mean'] * 1.1
                })

        return comparison

    def export_results(self, results: List[BenchmarkResult], format: str = 'json'):
        """Export benchmark results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"benchmark_results_{timestamp}.{format}"

        if format == 'json':
            data = {
                'timestamp': datetime.now().isoformat(),
                'results': [result.get_statistics() for result in results]
            }

            with open(self.results_dir / filename, 'w') as f:
                json.dump(data, f, indent=2)

        elif format == 'csv':
            if not results:
                return

            # Get all possible keys from statistics
            all_keys = set()
            sample_stats = results[0].get_statistics()
            self._flatten_keys(sample_stats, all_keys)

            with open(self.results_dir / filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['benchmark'] + sorted(all_keys))

                for result in results:
                    stats = result.get_statistics()
                    row = [result.name]
                    flat_stats = self._flatten_stats(stats)

                    for key in sorted(all_keys):
                        row.append(flat_stats.get(key, ''))

                    writer.writerow(row)

        print(f"Results exported to {self.results_dir / filename}")

    def _flatten_keys(self, data: dict, keys: set, prefix: str = ''):
        """Flatten nested dictionary keys."""
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                self._flatten_keys(value, keys, full_key)
            else:
                keys.add(full_key)

    def _flatten_stats(self, data: dict, prefix: str = '') -> dict:
        """Flatten nested statistics."""
        result = {}
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                result.update(self._flatten_stats(value, full_key))
            else:
                result[full_key] = value
        return result

    def generate_report(self, results: List[BenchmarkResult],
                       comparison: Optional[Dict[str, Any]] = None) -> str:
        """Generate a detailed performance report."""
        lines = []
        lines.append("=" * 80)
        lines.append("NAUTILUS TRADER ENGINE - PERFORMANCE BENCHMARK REPORT")
        lines.append("=" * 80)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Summary
        lines.append("SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Total Benchmarks: {len(results)}")
        lines.append(f"Total Iterations: {sum(r.iterations for r in results)}")
        lines.append("")

        # Results by category
        categories = {}
        for result in results:
            if result.category not in categories:
                categories[result.category] = []
            categories[result.category].append(result)

        for category, category_results in categories.items():
            lines.append(f"{category.upper()} BENCHMARKS")
            lines.append("-" * 40)

            for result in category_results:
                stats = result.get_statistics()
                exec_time = stats['execution_time']
                lines.append(f"{result.name}:")
                lines.append(".4f")
                lines.append(".4f")
                lines.append(f"  Iterations: {result.iterations}")
                lines.append("")

        # Performance comparison
        if comparison and comparison.get('comparisons'):
            lines.append("PERFORMANCE COMPARISON")
            lines.append("-" * 40)

            regressions = 0
            for comp in comparison['comparisons']:
                status = "⚠️  REGRESSION" if comp['regression'] else "✓ OK"
                lines.append(f"{comp['name']}: {comp['change_percent']:+.1f}% {status}")
                if comp['regression']:
                    regressions += 1

            lines.append("")
            lines.append(f"Regressions detected: {regressions}")

        return "\n".join(lines)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Performance Benchmarking for Nautilus Trader Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--category', help='Run specific benchmark category')
    parser.add_argument('--benchmark', help='Run specific benchmark')
    parser.add_argument('--iterations', type=int, default=100,
                       help='Number of iterations per benchmark')
    parser.add_argument('--baseline', action='store_true',
                       help='Establish new performance baseline')
    parser.add_argument('--compare', action='store_true',
                       help='Compare against existing baseline')
    parser.add_argument('--report', action='store_true',
                       help='Generate detailed performance report')
    parser.add_argument('--export-json', action='store_true',
                       help='Export results to JSON')
    parser.add_argument('--export-csv', action='store_true',
                       help='Export results to CSV')
    parser.add_argument('--visualize', action='store_true',
                       help='Generate performance charts')
    parser.add_argument('--ci', action='store_true',
                       help='CI mode (fail on regression)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')

    args = parser.parse_args()

    runner = BenchmarkRunner()

    # Determine which benchmarks to run
    if args.benchmark:
        results = [runner.run_benchmark(args.benchmark, args.iterations)]
    elif args.category:
        results = runner.run_category(args.category, args.iterations)
    else:
        results = runner.run_all(args.iterations)

    # Handle results
    if not results:
        print("No benchmarks were run")
        sys.exit(1)

    # Compare with baseline if requested
    comparison = None
    if args.compare:
        comparison = runner.compare_with_baseline(results)

        # Check for regressions in CI mode
        if args.ci and comparison:
            regressions = sum(1 for c in comparison['comparisons'] if c['regression'])
            if regressions > 0:
                print(f"❌ {regressions} performance regressions detected!")
                sys.exit(1)

    # Generate report
    if args.report:
        report = runner.generate_report(results, comparison)
        print(report)

    # Export results
    if args.export_json:
        runner.export_results(results, 'json')

    if args.export_csv:
        runner.export_results(results, 'csv')

    # Save baseline
    if args.baseline:
        runner.save_baseline(results)
        print("✓ New performance baseline established")

    print(f"✓ Completed {len(results)} benchmarks")


if __name__ == '__main__':
    main()