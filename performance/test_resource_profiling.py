#!/usr/bin/env python3
"""
Comprehensive Test Suite for Resource Profiling Tools
Tests all components of the resource profiling system including
ResourceProfiler, MemoryTracker, CPUProfiler, and GCMonitor.
"""

import asyncio
import gc
import json
import os
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Import the modules we're testing
from resource_profiling import (
    ResourceProfiler, ResourceSnapshot, MemoryProfile, CPUProfile,
    MemoryTracker, CPUProfiler, GCMonitor, profile_function
)

class TestResourceSnapshot(unittest.TestCase):
    """Test cases for ResourceSnapshot data structure"""
    
    def test_resource_snapshot_creation(self):
        """Test ResourceSnapshot creation and attributes"""
        timestamp = datetime.now()
        snapshot = ResourceSnapshot(
            timestamp=timestamp,
            cpu_percent=45.5,
            memory_rss=1024000,
            memory_vms=2048000,
            memory_percent=60.2,
            open_files=150,
            threads=8,
            gc_collections={0: 100, 1: 10, 2: 1},
            gc_objects=50000
        )
        
        self.assertEqual(snapshot.timestamp, timestamp)
        self.assertEqual(snapshot.cpu_percent, 45.5)
        self.assertEqual(snapshot.memory_rss, 1024000)
        self.assertEqual(snapshot.memory_vms, 2048000)
        self.assertEqual(snapshot.memory_percent, 60.2)
        self.assertEqual(snapshot.open_files, 150)
        self.assertEqual(snapshot.threads, 8)
        self.assertEqual(snapshot.gc_collections, {0: 100, 1: 10, 2: 1})
        self.assertEqual(snapshot.gc_objects, 50000)

class TestResourceProfiler(unittest.TestCase):
    """Test cases for ResourceProfiler"""
    
    def setUp(self):
        self.profiler = ResourceProfiler(sampling_interval=0.1)
    
    def tearDown(self):
        if self.profiler.profiling_active:
            self.profiler.stop_profiling()
    
    def test_profiler_initialization(self):
        """Test profiler initialization"""
        self.assertEqual(self.profiler.sampling_interval, 0.1)
        self.assertFalse(self.profiler.profiling_active)
        self.assertIsNone(self.profiler.profiling_thread)
        self.assertEqual(len(self.profiler.snapshots), 0)
        self.assertIsInstance(self.profiler.memory_tracker, MemoryTracker)
        self.assertIsInstance(self.profiler.cpu_profiler, CPUProfiler)
        self.assertIsInstance(self.profiler.gc_monitor, GCMonitor)
    
    def test_start_stop_profiling(self):
        """Test starting and stopping profiling"""
        # Test start
        self.profiler.start_profiling()
        self.assertTrue(self.profiler.profiling_active)
        self.assertIsNotNone(self.profiler.profiling_thread)
        self.assertTrue(self.profiler.profiling_thread.is_alive())
        
        # Wait a bit for some snapshots
        time.sleep(0.3)
        
        # Test stop
        self.profiler.stop_profiling()
        self.assertFalse(self.profiler.profiling_active)
        
        # Should have collected some snapshots
        self.assertGreater(len(self.profiler.snapshots), 0)
    
    def test_double_start_profiling(self):
        """Test starting profiling when already active"""
        self.profiler.start_profiling()
        
        # Starting again should not cause issues
        self.profiler.start_profiling()
        self.assertTrue(self.profiler.profiling_active)
        
        self.profiler.stop_profiling()
    
    def test_stop_without_start(self):
        """Test stopping profiling when not active"""
        # Should not cause issues
        self.profiler.stop_profiling()
        self.assertFalse(self.profiler.profiling_active)
    
    def test_take_snapshot(self):
        """Test taking a resource snapshot"""
        snapshot = self.profiler._take_snapshot()
        
        self.assertIsInstance(snapshot, ResourceSnapshot)
        self.assertIsInstance(snapshot.timestamp, datetime)
        self.assertIsInstance(snapshot.cpu_percent, float)
        self.assertIsInstance(snapshot.memory_rss, int)
        self.assertIsInstance(snapshot.memory_vms, int)
        self.assertIsInstance(snapshot.memory_percent, float)
        self.assertIsInstance(snapshot.open_files, int)
        self.assertIsInstance(snapshot.threads, int)
        self.assertIsInstance(snapshot.gc_collections, dict)
        self.assertIsInstance(snapshot.gc_objects, int)
        
        # Validate ranges
        self.assertGreaterEqual(snapshot.cpu_percent, 0.0)
        self.assertLessEqual(snapshot.cpu_percent, 100.0)
        self.assertGreaterEqual(snapshot.memory_percent, 0.0)
        self.assertLessEqual(snapshot.memory_percent, 100.0)
        self.assertGreater(snapshot.memory_rss, 0)
        self.assertGreater(snapshot.memory_vms, 0)
        self.assertGreater(snapshot.threads, 0)
    
    def test_generate_resource_report_no_data(self):
        """Test generating report with no profiling data"""
        report = self.profiler.generate_resource_report()
        
        self.assertIn("error", report)
        self.assertEqual(report["error"], "No profiling data available")
    
    def test_generate_resource_report_with_data(self):
        """Test generating report with profiling data"""
        # Add some mock snapshots
        for i in range(5):
            snapshot = ResourceSnapshot(
                timestamp=datetime.now() - timedelta(seconds=i),
                cpu_percent=50.0 + i,
                memory_rss=1000000 + i * 10000,
                memory_vms=2000000 + i * 20000,
                memory_percent=60.0 + i,
                open_files=100 + i,
                threads=8,
                gc_collections={0: 100 + i, 1: 10, 2: 1},
                gc_objects=50000 + i * 1000
            )
            self.profiler.snapshots.append(snapshot)
        
        report = self.profiler.generate_resource_report()
        
        # Verify report structure
        self.assertIn("profiling_duration", report)
        self.assertIn("resource_summary", report)
        self.assertIn("memory_analysis", report)
        self.assertIn("cpu_analysis", report)
        self.assertIn("gc_analysis", report)
        self.assertIn("optimization_recommendations", report)
        self.assertIn("resource_trends", report)
        self.assertIn("potential_issues", report)
        
        # Verify resource summary
        summary = report["resource_summary"]
        self.assertIn("cpu_usage", summary)
        self.assertIn("memory_usage", summary)
        self.assertIn("gc_objects", summary)
        
        # Verify CPU usage stats
        cpu_stats = summary["cpu_usage"]
        self.assertIn("mean", cpu_stats)
        self.assertIn("min", cpu_stats)
        self.assertIn("max", cpu_stats)
        self.assertIn("current", cpu_stats)
    
    def test_calculate_profiling_duration(self):
        """Test profiling duration calculation"""
        # No snapshots
        duration = self.profiler._calculate_profiling_duration()
        self.assertEqual(duration, 0.0)
        
        # Single snapshot
        self.profiler.snapshots.append(ResourceSnapshot(
            timestamp=datetime.now(),
            cpu_percent=50.0, memory_rss=1000000, memory_vms=2000000,
            memory_percent=60.0, open_files=100, threads=8,
            gc_collections={0: 100, 1: 10, 2: 1}, gc_objects=50000
        ))
        duration = self.profiler._calculate_profiling_duration()
        self.assertEqual(duration, 0.0)
        
        # Multiple snapshots
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=10)
        
        self.profiler.snapshots = [
            ResourceSnapshot(
                timestamp=start_time,
                cpu_percent=50.0, memory_rss=1000000, memory_vms=2000000,
                memory_percent=60.0, open_files=100, threads=8,
                gc_collections={0: 100, 1: 10, 2: 1}, gc_objects=50000
            ),
            ResourceSnapshot(
                timestamp=end_time,
                cpu_percent=55.0, memory_rss=1100000, memory_vms=2100000,
                memory_percent=65.0, open_files=105, threads=8,
                gc_collections={0: 110, 1: 11, 2: 1}, gc_objects=51000
            )
        ]
        
        duration = self.profiler._calculate_profiling_duration()
        self.assertAlmostEqual(duration, 10.0, places=1)
    
    def test_calculate_trend(self):
        """Test trend calculation"""
        # Increasing trend
        increasing_values = [1.0, 2.0, 3.0, 4.0, 5.0]
        trend = self.profiler._calculate_trend(increasing_values)
        self.assertGreater(trend, 0)
        
        # Decreasing trend
        decreasing_values = [5.0, 4.0, 3.0, 2.0, 1.0]
        trend = self.profiler._calculate_trend(decreasing_values)
        self.assertLess(trend, 0)
        
        # Stable trend
        stable_values = [3.0, 3.0, 3.0, 3.0, 3.0]
        trend = self.profiler._calculate_trend(stable_values)
        self.assertAlmostEqual(trend, 0.0, places=2)
        
        # Empty values
        trend = self.profiler._calculate_trend([])
        self.assertEqual(trend, 0.0)
        
        # Single value
        trend = self.profiler._calculate_trend([5.0])
        self.assertEqual(trend, 0.0)

class TestMemoryTracker(unittest.TestCase):
    """Test cases for MemoryTracker"""
    
    def setUp(self):
        self.tracker = MemoryTracker()
    
    def tearDown(self):
        if self.tracker.tracking_active:
            self.tracker.stop_tracking()
    
    def test_memory_tracker_initialization(self):
        """Test memory tracker initialization"""
        self.assertFalse(self.tracker.tracking_active)
        self.assertEqual(len(self.tracker.snapshots), 0)
        self.assertFalse(self.tracker.tracemalloc_started)
    
    def test_start_stop_tracking(self):
        """Test starting and stopping memory tracking"""
        # Test start
        self.tracker.start_tracking()
        self.assertTrue(self.tracker.tracking_active)
        
        # Test stop
        self.tracker.stop_tracking()
        self.assertFalse(self.tracker.tracking_active)
    
    def test_get_analysis(self):
        """Test getting memory analysis"""
        analysis = self.tracker.get_analysis()
        
        self.assertIsInstance(analysis, dict)
        self.assertIn("tracking_active", analysis)
        self.assertIn("current_memory", analysis)
        self.assertIn("top_allocations", analysis)
        self.assertIn("memory_growth", analysis)
        
        self.assertEqual(analysis["tracking_active"], self.tracker.tracking_active)

class TestCPUProfiler(unittest.TestCase):
    """Test cases for CPUProfiler"""
    
    def setUp(self):
        self.profiler = CPUProfiler()
    
    def tearDown(self):
        if self.profiler.profiling_active:
            self.profiler.stop_profiling()
    
    def test_cpu_profiler_initialization(self):
        """Test CPU profiler initialization"""
        self.assertIsNone(self.profiler.profiler)
        self.assertFalse(self.profiler.profiling_active)
        self.assertIsNone(self.profiler.profile_data)
    
    def test_start_stop_profiling(self):
        """Test starting and stopping CPU profiling"""
        # Test start
        self.profiler.start_profiling()
        self.assertTrue(self.profiler.profiling_active)
        self.assertIsNotNone(self.profiler.profiler)
        
        # Do some work
        result = sum(range(1000))
        
        # Test stop
        self.profiler.stop_profiling()
        self.assertFalse(self.profiler.profiling_active)
        self.assertIsNotNone(self.profiler.profile_data)
    
    def test_get_analysis_no_data(self):
        """Test getting analysis with no profiling data"""
        analysis = self.profiler.get_analysis()
        
        self.assertIn("error", analysis)
        self.assertEqual(analysis["error"], "No CPU profiling data available")
    
    def test_get_analysis_with_data(self):
        """Test getting analysis with profiling data"""
        # Start and stop profiling to generate data
        self.profiler.start_profiling()
        
        # Do some work to generate profile data
        for i in range(100):
            result = sum(range(100))
        
        self.profiler.stop_profiling()
        
        analysis = self.profiler.get_analysis()
        
        self.assertIn("profiling_active", analysis)
        self.assertIn("profile_summary", analysis)
        self.assertIn("hotspots", analysis)
        self.assertIn("optimization_suggestions", analysis)
        
        self.assertFalse(analysis["profiling_active"])
        self.assertIsInstance(analysis["optimization_suggestions"], list)

class TestGCMonitor(unittest.TestCase):
    """Test cases for GCMonitor"""
    
    def setUp(self):
        self.monitor = GCMonitor()
    
    def tearDown(self):
        if self.monitor.monitoring_active:
            self.monitor.stop_monitoring()
    
    def test_gc_monitor_initialization(self):
        """Test GC monitor initialization"""
        self.assertFalse(self.monitor.monitoring_active)
        self.assertIsNone(self.monitor.initial_counts)
    
    def test_start_stop_monitoring(self):
        """Test starting and stopping GC monitoring"""
        # Test start
        self.monitor.start_monitoring()
        self.assertTrue(self.monitor.monitoring_active)
        self.assertIsNotNone(self.monitor.initial_counts)
        
        # Test stop
        self.monitor.stop_monitoring()
        self.assertFalse(self.monitor.monitoring_active)
    
    def test_get_analysis(self):
        """Test getting GC analysis"""
        analysis = self.monitor.get_analysis()
        
        self.assertIsInstance(analysis, dict)
        self.assertIn("monitoring_active", analysis)
        self.assertIn("current_objects", analysis)
        self.assertIn("gc_stats", analysis)
        self.assertIn("recommendations", analysis)
        
        # Check current objects structure
        current_objects = analysis["current_objects"]
        self.assertIn("generation_0", current_objects)
        self.assertIn("generation_1", current_objects)
        self.assertIn("generation_2", current_objects)
        
        # Check recommendations
        recommendations = analysis["recommendations"]
        self.assertIsInstance(recommendations, list)
        self.assertGreater(len(recommendations), 0)
    
    def test_get_analysis_with_growth(self):
        """Test getting analysis with object growth tracking"""
        # Start monitoring to set initial counts
        self.monitor.start_monitoring()
        
        # Create some objects to change GC counts
        temp_objects = [[] for _ in range(1000)]
        
        analysis = self.monitor.get_analysis()
        
        # Should have object growth data
        self.assertIn("object_growth", analysis)
        
        object_growth = analysis["object_growth"]
        self.assertIn("generation_0", object_growth)
        self.assertIn("generation_1", object_growth)
        self.assertIn("generation_2", object_growth)

class TestProfileFunctionDecorator(unittest.TestCase):
    """Test cases for profile_function decorator"""
    
    def test_profile_function_decorator(self):
        """Test the profile_function decorator"""
        
        @profile_function
        def test_function(n):
            """Test function to profile"""
            return sum(range(n))
        
        # Run the decorated function
        result = test_function(1000)
        
        # Verify the function still works
        self.assertEqual(result, sum(range(1000)))
        
        # Check that a profile report was generated
        # (In a real test, we'd check for the file, but here we just verify no exceptions)
        self.assertTrue(True)  # If we get here, no exceptions were raised

class TestIntegration(unittest.TestCase):
    """Integration tests for resource profiling system"""
    
    def test_full_profiling_workflow(self):
        """Test complete profiling workflow"""
        profiler = ResourceProfiler(sampling_interval=0.1)
        
        try:
            # Start profiling
            profiler.start_profiling()
            
            # Simulate some work
            time.sleep(0.3)
            
            # Create some objects
            temp_data = []
            for i in range(1000):
                temp_data.append(f"data_{i}")
            
            # Do some CPU work
            result = sum(range(10000))
            
            # Stop profiling
            profiler.stop_profiling()
            
            # Generate report
            report = profiler.generate_resource_report()
            
            # Verify report structure
            self.assertIsInstance(report, dict)
            self.assertNotIn("error", report)
            self.assertIn("resource_summary", report)
            self.assertIn("optimization_recommendations", report)
            
            # Verify we collected some snapshots
            self.assertGreater(len(profiler.snapshots), 0)
            
        finally:
            if profiler.profiling_active:
                profiler.stop_profiling()
    
    def test_concurrent_profiling(self):
        """Test profiling with concurrent operations"""
        profiler = ResourceProfiler(sampling_interval=0.05)
        
        async def async_work():
            """Async work simulation"""
            await asyncio.sleep(0.1)
            return sum(range(1000))
        
        def sync_work():
            """Sync work simulation"""
            return [i**2 for i in range(1000)]
        
        try:
            profiler.start_profiling()
            
            # Run concurrent operations
            async def run_concurrent():
                tasks = [async_work() for _ in range(5)]
                results = await asyncio.gather(*tasks)
                return results
            
            # Run async work
            async_results = asyncio.run(run_concurrent())
            
            # Run sync work
            sync_results = [sync_work() for _ in range(3)]
            
            profiler.stop_profiling()
            
            # Verify results
            self.assertEqual(len(async_results), 5)
            self.assertEqual(len(sync_results), 3)
            
            # Verify profiling data was collected
            self.assertGreater(len(profiler.snapshots), 0)
            
        finally:
            if profiler.profiling_active:
                profiler.stop_profiling()

def run_resource_profiling_tests():
    """Run all resource profiling tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestResourceSnapshot,
        TestResourceProfiler,
        TestMemoryTracker,
        TestCPUProfiler,
        TestGCMonitor,
        TestProfileFunctionDecorator,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    print("Running comprehensive tests for Resource Profiling Tools...")
    print("=" * 70)
    
    success = run_resource_profiling_tests()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ All Resource Profiling tests PASSED!")
        print("\nResource Profiling Tools verified:")
        print("  - ResourceProfiler: Continuous profiling and reporting")
        print("  - MemoryTracker: Memory usage tracking and analysis")
        print("  - CPUProfiler: CPU profiling and hotspot detection")
        print("  - GCMonitor: Garbage collection monitoring")
        print("  - Integration: End-to-end workflow validation")
    else:
        print("❌ Some Resource Profiling tests FAILED!")
        print("Please check the test output above for details.")
    
    print("=" * 70)
    exit(0 if success else 1)