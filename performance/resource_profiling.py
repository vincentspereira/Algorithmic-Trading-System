#!/usr/bin/env python3
"""
Nautilus Trader - Resource Profiling Tools
This module provides comprehensive resource profiling capabilities including
memory usage analysis, CPU optimization, garbage collection monitoring,
and resource usage optimization strategies.
"""

import asyncio
import gc
import json
import logging
import os
import sys
import threading
import time
import tracemalloc
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
import cProfile
import pstats
import io

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ResourceSnapshot:
    """Single resource usage snapshot"""
    timestamp: datetime
    cpu_percent: float
    memory_rss: int  # Resident Set Size in bytes
    memory_vms: int  # Virtual Memory Size in bytes
    memory_percent: float
    open_files: int
    threads: int
    gc_collections: Dict[int, int]  # Generation -> collection count
    gc_objects: int
    
@dataclass
class MemoryProfile:
    """Memory profiling results"""
    peak_memory: int
    current_memory: int
    memory_blocks: List[Tuple[str, int, int]]  # filename, lineno, size
    top_allocations: List[Tuple[str, int]]  # description, size
    memory_growth_rate: float  # bytes per second
    potential_leaks: List[Dict[str, Any]]

@dataclass
class CPUProfile:
    """CPU profiling results"""
    total_time: float
    function_stats: List[Dict[str, Any]]
    hotspots: List[Dict[str, Any]]
    call_graph: Dict[str, Any]
    optimization_suggestions: List[str]

class ResourceProfiler:
    """Comprehensive resource profiling system"""
    
    def __init__(self, sampling_interval: float = 1.0):
        self.sampling_interval = sampling_interval
        self.snapshots: List[ResourceSnapshot] = []
        self.profiling_active = False
        self.profiling_thread = None
        
        # Memory tracking
        self.memory_tracker = MemoryTracker()
        
        # CPU profiling
        self.cpu_profiler = CPUProfiler()
        
        # GC monitoring
        self.gc_monitor = GCMonitor()
    
    def start_profiling(self):
        """Start continuous resource profiling"""
        if self.profiling_active:
            logger.warning("Profiling already active")
            return
        
        logger.info("Starting resource profiling")
        self.profiling_active = True
        self.profiling_thread = threading.Thread(target=self._profiling_loop, daemon=True)
        self.profiling_thread.start()
        
        # Start memory tracking
        self.memory_tracker.start_tracking()
        
        # Start GC monitoring
        self.gc_monitor.start_monitoring()
    
    def stop_profiling(self):
        """Stop continuous resource profiling"""
        if not self.profiling_active:
            logger.warning("Profiling not active")
            return
        
        logger.info("Stopping resource profiling")
        self.profiling_active = False
        
        if self.profiling_thread:
            self.profiling_thread.join(timeout=5.0)
        
        # Stop memory tracking
        self.memory_tracker.stop_tracking()
        
        # Stop GC monitoring
        self.gc_monitor.stop_monitoring()
    
    def _profiling_loop(self):
        """Main profiling loop"""
        while self.profiling_active:
            try:
                snapshot = self._take_snapshot()
                self.snapshots.append(snapshot)
                time.sleep(self.sampling_interval)
            except Exception as e:
                logger.error(f"Error in profiling loop: {e}")
    
    def _take_snapshot(self) -> ResourceSnapshot:
        """Take a resource usage snapshot"""
        # Mock implementation - in real scenario would use psutil
        return ResourceSnapshot(
            timestamp=datetime.now(),
            cpu_percent=self._get_cpu_usage(),
            memory_rss=self._get_memory_rss(),
            memory_vms=self._get_memory_vms(),
            memory_percent=self._get_memory_percent(),
            open_files=self._get_open_files(),
            threads=self._get_thread_count(),
            gc_collections=self._get_gc_collections(),
            gc_objects=len(gc.get_objects())
        )
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        # Mock implementation
        import random
        return random.uniform(10.0, 80.0)
    
    def _get_memory_rss(self) -> int:
        """Get Resident Set Size in bytes"""
        # Mock implementation
        import random
        return random.randint(100_000_000, 500_000_000)  # 100MB - 500MB
    
    def _get_memory_vms(self) -> int:
        """Get Virtual Memory Size in bytes"""
        # Mock implementation
        import random
        return random.randint(200_000_000, 1_000_000_000)  # 200MB - 1GB
    
    def _get_memory_percent(self) -> float:
        """Get memory usage percentage"""
        # Mock implementation
        import random
        return random.uniform(20.0, 70.0)
    
    def _get_open_files(self) -> int:
        """Get number of open files"""
        # Mock implementation
        import random
        return random.randint(50, 200)
    
    def _get_thread_count(self) -> int:
        """Get number of threads"""
        return threading.active_count()
    
    def _get_gc_collections(self) -> Dict[int, int]:
        """Get garbage collection statistics"""
        return {i: gc.get_count()[i] for i in range(3)}
    
    def generate_resource_report(self) -> Dict[str, Any]:
        """Generate comprehensive resource usage report"""
        if not self.snapshots:
            return {"error": "No profiling data available"}
        
        report = {
            "profiling_duration": self._calculate_profiling_duration(),
            "resource_summary": self._generate_resource_summary(),
            "memory_analysis": self.memory_tracker.get_analysis(),
            "cpu_analysis": self.cpu_profiler.get_analysis(),
            "gc_analysis": self.gc_monitor.get_analysis(),
            "optimization_recommendations": self._generate_optimization_recommendations(),
            "resource_trends": self._analyze_resource_trends(),
            "potential_issues": self._identify_potential_issues()
        }
        
        return report
    
    def _calculate_profiling_duration(self) -> float:
        """Calculate total profiling duration in seconds"""
        if len(self.snapshots) < 2:
            return 0.0
        
        start_time = self.snapshots[0].timestamp
        end_time = self.snapshots[-1].timestamp
        return (end_time - start_time).total_seconds()
    
    def _generate_resource_summary(self) -> Dict[str, Any]:
        """Generate resource usage summary"""
        if not self.snapshots:
            return {}
        
        cpu_values = [s.cpu_percent for s in self.snapshots]
        memory_values = [s.memory_percent for s in self.snapshots]
        
        return {
            "cpu_usage": {
                "mean": sum(cpu_values) / len(cpu_values),
                "min": min(cpu_values),
                "max": max(cpu_values),
                "current": cpu_values[-1]
            },
            "memory_usage": {
                "mean": sum(memory_values) / len(memory_values),
                "min": min(memory_values),
                "max": max(memory_values),
                "current": memory_values[-1]
            },
            "gc_objects": {
                "current": self.snapshots[-1].gc_objects,
                "peak": max(s.gc_objects for s in self.snapshots)
            }
        }
    
    def _analyze_resource_trends(self) -> Dict[str, Any]:
        """Analyze resource usage trends"""
        if len(self.snapshots) < 10:
            return {"error": "Insufficient data for trend analysis"}
        
        # Calculate trends for last 10 snapshots
        recent_snapshots = self.snapshots[-10:]
        
        cpu_trend = self._calculate_trend([s.cpu_percent for s in recent_snapshots])
        memory_trend = self._calculate_trend([s.memory_percent for s in recent_snapshots])
        
        return {
            "cpu_trend": cpu_trend,
            "memory_trend": memory_trend,
            "trend_analysis": {
                "cpu_increasing": cpu_trend > 0.1,
                "memory_increasing": memory_trend > 0.1,
                "stable_performance": abs(cpu_trend) < 0.1 and abs(memory_trend) < 0.1
            }
        }
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend using simple linear regression"""
        if len(values) < 2:
            return 0.0
        
        n = len(values)
        x_values = list(range(n))
        
        # Calculate slope using least squares
        x_mean = sum(x_values) / n
        y_mean = sum(values) / n
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def _identify_potential_issues(self) -> List[Dict[str, Any]]:
        """Identify potential performance issues"""
        issues = []
        
        if not self.snapshots:
            return issues
        
        # Check for high CPU usage
        recent_cpu = [s.cpu_percent for s in self.snapshots[-5:]]
        if recent_cpu and sum(recent_cpu) / len(recent_cpu) > 80:
            issues.append({
                "type": "high_cpu_usage",
                "severity": "high",
                "description": "CPU usage consistently above 80%",
                "recommendation": "Investigate CPU-intensive operations and consider optimization"
            })
        
        # Check for high memory usage
        recent_memory = [s.memory_percent for s in self.snapshots[-5:]]
        if recent_memory and sum(recent_memory) / len(recent_memory) > 85:
            issues.append({
                "type": "high_memory_usage",
                "severity": "high",
                "description": "Memory usage consistently above 85%",
                "recommendation": "Investigate memory leaks and optimize memory usage"
            })
        
        # Check for increasing object count (potential memory leak)
        if len(self.snapshots) >= 10:
            early_objects = sum(s.gc_objects for s in self.snapshots[:5]) / 5
            recent_objects = sum(s.gc_objects for s in self.snapshots[-5:]) / 5
            
            if recent_objects > early_objects * 1.5:
                issues.append({
                    "type": "potential_memory_leak",
                    "severity": "medium",
                    "description": "Object count increased significantly during profiling",
                    "recommendation": "Investigate potential memory leaks and object retention"
                })
        
        return issues
    
    def _generate_optimization_recommendations(self) -> List[Dict[str, str]]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Add general recommendations
        recommendations.extend([
            {
                "category": "memory",
                "recommendation": "Use object pooling for frequently created/destroyed objects",
                "impact": "medium"
            },
            {
                "category": "cpu",
                "recommendation": "Profile CPU-intensive functions and optimize algorithms",
                "impact": "high"
            },
            {
                "category": "gc",
                "recommendation": "Minimize object allocations in hot code paths",
                "impact": "medium"
            },
            {
                "category": "io",
                "recommendation": "Use async I/O for network and file operations",
                "impact": "high"
            }
        ])
        
        return recommendations

class MemoryTracker:
    """Memory usage tracking and analysis"""
    
    def __init__(self):
        self.tracking_active = False
        self.snapshots = []
        self.tracemalloc_started = False
    
    def start_tracking(self):
        """Start memory tracking"""
        if not self.tracking_active:
            self.tracking_active = True
            if not tracemalloc.is_tracing():
                tracemalloc.start()
                self.tracemalloc_started = True
            logger.info("Memory tracking started")
    
    def stop_tracking(self):
        """Stop memory tracking"""
        if self.tracking_active:
            self.tracking_active = False
            if self.tracemalloc_started and tracemalloc.is_tracing():
                tracemalloc.stop()
                self.tracemalloc_started = False
            logger.info("Memory tracking stopped")
    
    def get_analysis(self) -> Dict[str, Any]:
        """Get memory usage analysis"""
        analysis = {
            "tracking_active": self.tracking_active,
            "current_memory": self._get_current_memory(),
            "top_allocations": self._get_top_allocations(),
            "memory_growth": self._analyze_memory_growth()
        }
        
        return analysis
    
    def _get_current_memory(self) -> Dict[str, Any]:
        """Get current memory usage"""
        if tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            return {
                "current_bytes": current,
                "peak_bytes": peak,
                "current_mb": current / 1024 / 1024,
                "peak_mb": peak / 1024 / 1024
            }
        else:
            return {"error": "Memory tracing not active"}
    
    def _get_top_allocations(self) -> List[Dict[str, Any]]:
        """Get top memory allocations"""
        if not tracemalloc.is_tracing():
            return []
        
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        
        allocations = []
        for stat in top_stats[:10]:  # Top 10 allocations
            allocations.append({
                "filename": stat.traceback.format()[0] if stat.traceback.format() else "unknown",
                "size_bytes": stat.size,
                "size_mb": stat.size / 1024 / 1024,
                "count": stat.count
            })
        
        return allocations
    
    def _analyze_memory_growth(self) -> Dict[str, Any]:
        """Analyze memory growth patterns"""
        # Mock implementation
        return {
            "growth_rate_mb_per_minute": 0.5,
            "is_growing": True,
            "growth_trend": "linear"
        }

class CPUProfiler:
    """CPU profiling and analysis"""
    
    def __init__(self):
        self.profiler = None
        self.profiling_active = False
        self.profile_data = None
    
    def start_profiling(self):
        """Start CPU profiling"""
        if not self.profiling_active:
            self.profiler = cProfile.Profile()
            self.profiler.enable()
            self.profiling_active = True
            logger.info("CPU profiling started")
    
    def stop_profiling(self):
        """Stop CPU profiling"""
        if self.profiling_active and self.profiler:
            self.profiler.disable()
            self.profiling_active = False
            
            # Capture profile data
            s = io.StringIO()
            ps = pstats.Stats(self.profiler, stream=s)
            ps.sort_stats('cumulative')
            ps.print_stats(20)  # Top 20 functions
            self.profile_data = s.getvalue()
            
            logger.info("CPU profiling stopped")
    
    def get_analysis(self) -> Dict[str, Any]:
        """Get CPU profiling analysis"""
        if not self.profile_data:
            return {"error": "No CPU profiling data available"}
        
        return {
            "profiling_active": self.profiling_active,
            "profile_summary": self._parse_profile_data(),
            "hotspots": self._identify_hotspots(),
            "optimization_suggestions": self._generate_cpu_optimizations()
        }
    
    def _parse_profile_data(self) -> Dict[str, Any]:
        """Parse CPU profile data"""
        # Mock implementation
        return {
            "total_calls": 12345,
            "total_time": 1.234,
            "top_functions": [
                {"function": "trading_algorithm", "time": 0.456, "calls": 1000},
                {"function": "market_data_processing", "time": 0.234, "calls": 5000},
                {"function": "risk_calculation", "time": 0.123, "calls": 2000}
            ]
        }
    
    def _identify_hotspots(self) -> List[Dict[str, Any]]:
        """Identify CPU hotspots"""
        return [
            {
                "function": "trading_algorithm",
                "cpu_time_percent": 37.0,
                "recommendation": "Optimize algorithm complexity"
            },
            {
                "function": "market_data_processing",
                "cpu_time_percent": 19.0,
                "recommendation": "Use vectorized operations"
            }
        ]
    
    def _generate_cpu_optimizations(self) -> List[str]:
        """Generate CPU optimization suggestions"""
        return [
            "Use NumPy for numerical computations",
            "Implement caching for expensive calculations",
            "Consider using Cython for performance-critical code",
            "Optimize database queries to reduce CPU load",
            "Use multiprocessing for CPU-intensive tasks"
        ]

class GCMonitor:
    """Garbage collection monitoring"""
    
    def __init__(self):
        self.monitoring_active = False
        self.gc_stats = defaultdict(list)
        self.initial_counts = None
    
    def start_monitoring(self):
        """Start GC monitoring"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.initial_counts = gc.get_count()
            logger.info("GC monitoring started")
    
    def stop_monitoring(self):
        """Stop GC monitoring"""
        if self.monitoring_active:
            self.monitoring_active = False
            logger.info("GC monitoring stopped")
    
    def get_analysis(self) -> Dict[str, Any]:
        """Get GC analysis"""
        current_counts = gc.get_count()
        
        analysis = {
            "monitoring_active": self.monitoring_active,
            "current_objects": {
                "generation_0": current_counts[0],
                "generation_1": current_counts[1],
                "generation_2": current_counts[2]
            },
            "gc_stats": gc.get_stats(),
            "recommendations": self._generate_gc_recommendations()
        }
        
        if self.initial_counts:
            analysis["object_growth"] = {
                "generation_0": current_counts[0] - self.initial_counts[0],
                "generation_1": current_counts[1] - self.initial_counts[1],
                "generation_2": current_counts[2] - self.initial_counts[2]
            }
        
        return analysis
    
    def _generate_gc_recommendations(self) -> List[str]:
        """Generate GC optimization recommendations"""
        return [
            "Minimize object creation in hot code paths",
            "Use object pooling for frequently used objects",
            "Avoid circular references that prevent garbage collection",
            "Consider manual GC tuning for performance-critical applications",
            "Use weak references where appropriate to avoid retention"
        ]

def profile_function(func: Callable) -> Callable:
    """Decorator to profile a specific function"""
    def wrapper(*args, **kwargs):
        profiler = ResourceProfiler(sampling_interval=0.1)
        profiler.start_profiling()
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            profiler.stop_profiling()
            
            # Generate and save report
            report = profiler.generate_resource_report()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"profile_{func.__name__}_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"Profile report saved to {filename}")
    
    return wrapper

async def main():
    """Main function to demonstrate resource profiling"""
    logger.info("Starting resource profiling demonstration")
    
    # Create profiler
    profiler = ResourceProfiler(sampling_interval=0.5)
    
    # Start profiling
    profiler.start_profiling()
    
    try:
        # Simulate some work
        logger.info("Simulating workload...")
        
        # CPU-intensive task
        for i in range(1000):
            result = sum(range(1000))
        
        # Memory allocation
        data = []
        for i in range(10000):
            data.append(f"data_item_{i}")
        
        # Async operations
        await asyncio.sleep(2.0)
        
        # More CPU work
        for i in range(500):
            result = [x**2 for x in range(100)]
        
        logger.info("Workload simulation complete")
        
    finally:
        # Stop profiling
        profiler.stop_profiling()
    
    # Generate report
    report = profiler.generate_resource_report()
    
    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"resource_profile_report_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    logger.info(f"Resource profile report saved to {filename}")
    
    # Print summary
    print("\n" + "="*60)
    print("RESOURCE PROFILING SUMMARY")
    print("="*60)
    
    if "resource_summary" in report:
        summary = report["resource_summary"]
        
        if "cpu_usage" in summary:
            cpu = summary["cpu_usage"]
            print(f"CPU Usage: Mean={cpu.get('mean', 0):.1f}%, Max={cpu.get('max', 0):.1f}%")
        
        if "memory_usage" in summary:
            memory = summary["memory_usage"]
            print(f"Memory Usage: Mean={memory.get('mean', 0):.1f}%, Max={memory.get('max', 0):.1f}%")
    
    if "potential_issues" in report:
        issues = report["potential_issues"]
        if issues:
            print(f"\nPotential Issues ({len(issues)}):")
            for issue in issues:
                print(f"  - {issue.get('description', 'Unknown issue')}")
    
    if "optimization_recommendations" in report:
        recommendations = report["optimization_recommendations"]
        print(f"\nOptimization Recommendations ({len(recommendations)}):")
        for rec in recommendations[:3]:  # Show top 3
            print(f"  - {rec.get('recommendation', 'Unknown recommendation')}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    asyncio.run(main())