#!/usr/bin/env python3
"""
Test Suite for Distributed Tracing System
Tests the OpenTelemetry-based distributed tracing implementation.
"""

import asyncio
import json
import time
import unittest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import tempfile
import os
import sys
from pathlib import Path

# Add the parent directory to the path to import monitoring modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from monitoring.distributed_tracing_system import (
    DistributedTracer,
    PerformanceAnalyzer,
    TraceSampler,
    TracingContext,
    SpanData,
    TraceData,
    SpanContext,
    SpanKind,
    TraceStatus,
    initialize_tracing,
    get_tracer,
    trace_operation
)

import structlog

logger = structlog.get_logger(__name__)

class TestSpanData(unittest.TestCase):
    """Test SpanData functionality"""
    
    def test_span_creation(self):
        """Test span data creation"""
        span = SpanData(
            span_id="test_span_123",
            trace_id="test_trace_456",
            parent_span_id="parent_span_789",
            operation_name="test_operation",
            service_name="test_service",
            start_time=time.time(),
            kind=SpanKind.SERVER,
            tags={"user_id": "123", "endpoint": "/api/test"}
        )
        
        self.assertEqual(span.span_id, "test_span_123")
        self.assertEqual(span.trace_id, "test_trace_456")
        self.assertEqual(span.parent_span_id, "parent_span_789")
        self.assertEqual(span.operation_name, "test_operation")
        self.assertEqual(span.service_name, "test_service")
        self.assertEqual(span.kind, SpanKind.SERVER)
        self.assertEqual(span.status, TraceStatus.OK)
        self.assertEqual(span.tags["user_id"], "123")
        self.assertIsNone(span.end_time)
        self.assertIsNone(span.duration)
    
    def test_span_finish(self):
        """Test span finishing"""
        start_time = time.time()
        span = SpanData(
            span_id="test_span",
            trace_id="test_trace",
            parent_span_id=None,
            operation_name="test_op",
            service_name="test_service",
            start_time=start_time
        )
        
        # Finish the span
        time.sleep(0.01)  # Small delay
        span.finish(TraceStatus.OK)
        
        self.assertIsNotNone(span.end_time)
        self.assertIsNotNone(span.duration)
        self.assertGreater(span.duration, 0)
        self.assertEqual(span.status, TraceStatus.OK)
        self.assertAlmostEqual(span.duration, span.end_time - span.start_time, places=6)

class TestTraceData(unittest.TestCase):
    """Test TraceData functionality"""
    
    def test_trace_creation(self):
        """Test trace data creation and metrics calculation"""
        start_time = time.time()
        
        # Create test spans
        spans = [
            SpanData(
                span_id="span_1",
                trace_id="trace_123",
                parent_span_id=None,
                operation_name="root_operation",
                service_name="service_a",
                start_time=start_time,
                end_time=start_time + 0.1,
                duration=0.1,
                status=TraceStatus.OK
            ),
            SpanData(
                span_id="span_2",
                trace_id="trace_123",
                parent_span_id="span_1",
                operation_name="child_operation",
                service_name="service_b",
                start_time=start_time + 0.02,
                end_time=start_time + 0.08,
                duration=0.06,
                status=TraceStatus.ERROR
            ),
            SpanData(
                span_id="span_3",
                trace_id="trace_123",
                parent_span_id="span_1",
                operation_name="another_child",
                service_name="service_a",
                start_time=start_time + 0.05,
                end_time=start_time + 0.09,
                duration=0.04,
                status=TraceStatus.OK
            )
        ]
        
        trace = TraceData(trace_id="trace_123", spans=spans, start_time=start_time)
        
        self.assertEqual(trace.trace_id, "trace_123")
        self.assertEqual(len(trace.spans), 3)
        self.assertEqual(trace.service_count, 2)  # service_a and service_b
        self.assertEqual(trace.error_count, 1)  # One error span
        self.assertIsNotNone(trace.root_span)
        self.assertEqual(trace.root_span.span_id, "span_1")
        self.assertAlmostEqual(trace.duration, 0.1, places=6)

class TestTraceSampler(unittest.TestCase):
    """Test TraceSampler functionality"""
    
    def test_initialization(self):
        """Test sampler initialization"""
        sampler = TraceSampler(default_rate=0.5)
        
        self.assertEqual(sampler.default_rate, 0.5)
        self.assertEqual(sampler.error_sampling_rate, 1.0)
        self.assertEqual(sampler.slow_request_threshold, 1.0)
        self.assertTrue(sampler.adaptive_sampling_enabled)
    
    def test_default_sampling(self):
        """Test default sampling behavior"""
        sampler = TraceSampler(default_rate=0.0)  # Never sample
        
        # Should not sample normal requests
        should_sample = sampler.should_sample("test_service", "test_operation")
        self.assertFalse(should_sample)
        
        # Should always sample errors
        should_sample = sampler.should_sample("test_service", "test_operation", {"error": True})
        self.assertTrue(should_sample)
        
        # Should always sample slow requests
        should_sample = sampler.should_sample("test_service", "test_operation", {"duration": 2.0})
        self.assertTrue(should_sample)
    
    def test_service_specific_sampling(self):
        """Test service-specific sampling rates"""
        sampler = TraceSampler(default_rate=0.0)
        
        # Set service-specific rate
        sampler.set_service_sampling_rate("important_service", 1.0)
        
        # Should sample for important service
        should_sample = sampler.should_sample("important_service", "test_operation")
        self.assertTrue(should_sample)
        
        # Should not sample for other services
        should_sample = sampler.should_sample("other_service", "test_operation")
        self.assertFalse(should_sample)
    
    def test_operation_specific_sampling(self):
        """Test operation-specific sampling rates"""
        sampler = TraceSampler(default_rate=0.0)
        
        # Set operation-specific rate
        sampler.set_operation_sampling_rate("test_service", "critical_operation", 1.0)
        
        # Should sample for critical operation
        should_sample = sampler.should_sample("test_service", "critical_operation")
        self.assertTrue(should_sample)
        
        # Should not sample for other operations
        should_sample = sampler.should_sample("test_service", "normal_operation")
        self.assertFalse(should_sample)

class TestPerformanceAnalyzer(unittest.TestCase):
    """Test PerformanceAnalyzer functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = PerformanceAnalyzer()
    
    def test_initialization(self):
        """Test analyzer initialization"""
        self.assertIsInstance(self.analyzer.trace_data, dict)
        self.assertIsInstance(self.analyzer.service_metrics, dict)
        self.assertIsInstance(self.analyzer.operation_metrics, dict)
    
    def test_update_metrics(self):
        """Test metrics updating"""
        span = SpanData(
            span_id="test_span",
            trace_id="test_trace",
            parent_span_id=None,
            operation_name="test_operation",
            service_name="test_service",
            start_time=time.time(),
            duration=0.1,
            status=TraceStatus.OK
        )
        
        self.analyzer.update_metrics(span)
        
        # Check service metrics
        service_metrics = self.analyzer.service_metrics["test_service"]
        self.assertEqual(service_metrics['total_requests'], 1)
        self.assertEqual(service_metrics['total_duration'], 0.1)
        self.assertEqual(service_metrics['error_count'], 0)
        self.assertEqual(service_metrics['avg_duration'], 0.1)
        
        # Check operation metrics
        operation_key = "test_service:test_operation"
        operation_metrics = self.analyzer.operation_metrics[operation_key]
        self.assertEqual(operation_metrics['total_requests'], 1)
        self.assertEqual(operation_metrics['total_duration'], 0.1)
        self.assertEqual(operation_metrics['error_count'], 0)
    
    def test_analyze_trace(self):
        """Test trace analysis"""
        # Create a test trace with multiple spans
        spans = [
            SpanData(
                span_id="span_1",
                trace_id="trace_123",
                parent_span_id=None,
                operation_name="root_operation",
                service_name="service_a",
                start_time=time.time(),
                duration=1.0,
                status=TraceStatus.OK
            ),
            SpanData(
                span_id="span_2",
                trace_id="trace_123",
                parent_span_id="span_1",
                operation_name="slow_operation",
                service_name="service_b",
                start_time=time.time(),
                duration=0.8,  # 80% of total time - should be a bottleneck
                status=TraceStatus.OK
            )
        ]
        
        trace = TraceData(trace_id="trace_123", spans=spans, start_time=time.time())
        # Manually set trace duration since __post_init__ calculates it
        trace.duration = 1.0
        trace.end_time = trace.start_time + 1.0
        
        analysis = self.analyzer.analyze_trace(trace)
        
        self.assertEqual(analysis['trace_id'], "trace_123")
        self.assertEqual(analysis['service_count'], 2)
        self.assertEqual(analysis['span_count'], 2)
        self.assertEqual(analysis['error_count'], 0)
        self.assertGreater(len(analysis['bottlenecks']), 0)  # Should identify bottleneck
        self.assertIn('service_a', analysis['service_breakdown'])
        self.assertIn('service_b', analysis['service_breakdown'])

class TestDistributedTracer(unittest.TestCase):
    """Test DistributedTracer functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tracer = DistributedTracer("test_service", {"default_sampling_rate": 1.0})
    
    def test_initialization(self):
        """Test tracer initialization"""
        self.assertEqual(self.tracer.service_name, "test_service")
        self.assertIsNotNone(self.tracer.performance_analyzer)
        self.assertIsNotNone(self.tracer.trace_sampler)
        self.assertIsInstance(self.tracer.active_spans, dict)
        self.assertIsInstance(self.tracer.completed_traces, dict)
    
    def test_span_lifecycle(self):
        """Test complete span lifecycle"""
        # Start a span
        span_id = self.tracer.start_span("test_operation", tags={"user_id": "123"})
        
        if span_id:  # Only test if sampling allowed the span
            self.assertIn(span_id, self.tracer.active_spans)
            
            # Add events and logs
            self.tracer.add_span_event(span_id, "processing_started", {"step": 1})
            self.tracer.add_span_log(span_id, "Processing user request", "INFO")
            self.tracer.set_span_tag(span_id, "processed", True)
            
            # Check span data
            span_data = self.tracer.active_spans[span_id]
            self.assertEqual(span_data.operation_name, "test_operation")
            self.assertEqual(span_data.service_name, "test_service")
            self.assertEqual(span_data.tags["user_id"], "123")
            self.assertEqual(span_data.tags["processed"], True)
            self.assertEqual(len(span_data.events), 1)
            self.assertEqual(len(span_data.logs), 1)
            
            # Finish the span
            self.tracer.finish_span(span_id, TraceStatus.OK)
            
            self.assertNotIn(span_id, self.tracer.active_spans)
    
    def test_nested_spans(self):
        """Test nested span creation"""
        # Start parent span
        parent_span_id = self.tracer.start_span("parent_operation")
        
        if parent_span_id:
            parent_context = SpanContext(
                trace_id=self.tracer.active_spans[parent_span_id].trace_id,
                span_id=parent_span_id
            )
            
            # Start child span
            child_span_id = self.tracer.start_span("child_operation", parent_context)
            
            if child_span_id:
                # Verify parent-child relationship
                child_span = self.tracer.active_spans[child_span_id]
                parent_span = self.tracer.active_spans[parent_span_id]
                
                self.assertEqual(child_span.trace_id, parent_span.trace_id)
                self.assertEqual(child_span.parent_span_id, parent_span_id)
                
                # Finish spans
                self.tracer.finish_span(child_span_id)
                self.tracer.finish_span(parent_span_id)
    
    def test_performance_summary(self):
        """Test performance summary generation"""
        # Create and finish some spans
        for i in range(3):
            span_id = self.tracer.start_span(f"operation_{i}")
            if span_id:
                time.sleep(0.01)  # Small delay
                self.tracer.finish_span(span_id)
        
        summary = self.tracer.get_performance_summary()
        
        self.assertIn('services', summary)
        self.assertIn('operations', summary)
        self.assertIn('sampling_rates', summary)
        self.assertIn('trace_counts', summary)

class TestTracingContext(unittest.TestCase):
    """Test TracingContext context manager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tracer = DistributedTracer("test_service", {"default_sampling_rate": 1.0})
    
    def test_context_manager_success(self):
        """Test context manager for successful operations"""
        with TracingContext(self.tracer, "test_context_operation") as ctx:
            self.assertIsNotNone(ctx.span_id)
            if ctx.span_id:
                self.assertIn(ctx.span_id, self.tracer.active_spans)
                
                # Add some context
                ctx.add_event("processing", {"step": "validation"})
                ctx.add_log("Validating input", "INFO")
                ctx.set_tag("validated", True)
        
        # Span should be finished after context exit
        if ctx.span_id:
            self.assertNotIn(ctx.span_id, self.tracer.active_spans)
    
    def test_context_manager_exception(self):
        """Test context manager with exceptions"""
        try:
            with TracingContext(self.tracer, "failing_operation") as ctx:
                if ctx.span_id:
                    self.assertIn(ctx.span_id, self.tracer.active_spans)
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected exception
        
        # Span should still be finished after exception
        if ctx.span_id:
            self.assertNotIn(ctx.span_id, self.tracer.active_spans)

class TestTraceDecorator(unittest.TestCase):
    """Test trace_operation decorator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tracer = DistributedTracer("test_service", {"default_sampling_rate": 1.0})
        # Set global tracer for decorator
        import monitoring.distributed_tracing_system
        monitoring.distributed_tracing_system._global_tracer = self.tracer
    
    def test_sync_function_decorator(self):
        """Test decorator on synchronous functions"""
        @trace_operation("sync_test_operation", tags={"type": "sync"})
        def sync_test_function(value):
            return value * 2
        
        result = sync_test_function(5)
        self.assertEqual(result, 10)
    
    def test_async_function_decorator(self):
        """Test decorator on asynchronous functions"""
        @trace_operation("async_test_operation", tags={"type": "async"})
        async def async_test_function(value):
            await asyncio.sleep(0.01)
            return value * 3
        
        async def run_test():
            result = await async_test_function(4)
            self.assertEqual(result, 12)
        
        asyncio.run(run_test())
    
    def test_decorator_with_exception(self):
        """Test decorator behavior with exceptions"""
        @trace_operation("failing_operation")
        def failing_function():
            raise RuntimeError("Test error")
        
        with self.assertRaises(RuntimeError):
            failing_function()

class TestAsyncIntegration(unittest.TestCase):
    """Test async integration functionality"""
    
    async def test_tracer_lifecycle(self):
        """Test complete tracer lifecycle"""
        tracer = DistributedTracer("integration_test_service", {"default_sampling_rate": 1.0})
        
        try:
            # Start tracer
            await tracer.start()
            self.assertTrue(tracer.running)
            
            # Create some traced operations
            span_id = tracer.start_span("integration_test")
            if span_id:
                await asyncio.sleep(0.01)
                tracer.finish_span(span_id)
            
            # Wait a bit for background tasks
            await asyncio.sleep(0.1)
            
        finally:
            # Stop tracer
            await tracer.stop()
            self.assertFalse(tracer.running)

def run_async_test(test_func):
    """Helper function to run async tests"""
    return asyncio.run(test_func())

class AsyncTestRunner:
    """Custom test runner for async tests"""
    
    @staticmethod
    def run_test_suite():
        """Run the complete test suite"""
        # Create test suite
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add test classes
        test_classes = [
            TestSpanData,
            TestTraceData,
            TestTraceSampler,
            TestPerformanceAnalyzer,
            TestDistributedTracer,
            TestTracingContext,
            TestTraceDecorator
        ]
        
        for test_class in test_classes:
            tests = loader.loadTestsFromTestCase(test_class)
            suite.addTests(tests)
        
        # Run synchronous tests
        runner = unittest.TextTestRunner(verbosity=2)
        sync_result = runner.run(suite)
        
        # Run async integration tests
        print("\\n" + "="*70)
        print("Running Async Integration Tests")
        print("="*70)
        
        async_tests = [
            TestAsyncIntegration().test_tracer_lifecycle
        ]
        
        async_results = []
        for test in async_tests:
            try:
                print(f"Running {test.__name__}...")
                asyncio.run(test())
                print(f"✓ {test.__name__} passed")
                async_results.append(True)
            except Exception as e:
                print(f"✗ {test.__name__} failed: {e}")
                async_results.append(False)
        
        # Summary
        print("\\n" + "="*70)
        print("Test Results Summary")
        print("="*70)
        print(f"Synchronous tests: {sync_result.testsRun} run, {len(sync_result.failures)} failures, {len(sync_result.errors)} errors")
        print(f"Asynchronous tests: {len(async_tests)} run, {async_results.count(False)} failures")
        
        total_tests = sync_result.testsRun + len(async_tests)
        total_failures = len(sync_result.failures) + len(sync_result.errors) + async_results.count(False)
        
        print(f"\\nOverall: {total_tests} tests, {total_failures} failures")
        
        if total_failures == 0:
            print("\\n🎉 All distributed tracing tests passed!")
            print("\\n✅ Span lifecycle management works correctly")
            print("✅ Trace correlation and analysis functional")
            print("✅ Performance bottleneck identification working")
            print("✅ Sampling strategies implemented correctly")
            print("✅ Context management and decorators functional")
            return True
        else:
            print(f"\\n❌ {total_failures} tests failed")
            return False

def main():
    """Main test execution function"""
    print("="*70)
    print("Distributed Tracing System Test Suite")
    print("="*70)
    
    # Set up test environment
    os.environ['MONITORING_TEST_MODE'] = 'true'
    
    # Run tests
    runner = AsyncTestRunner()
    success = runner.run_test_suite()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()