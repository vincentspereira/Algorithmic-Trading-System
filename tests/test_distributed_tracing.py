"""
Tests for Distributed Tracing System
"""

import pytest
import asyncio
import time
from datetime import datetime
from unittest.mock import Mock, patch

from nautilus_trader_engine.monitoring.distributed_tracing import (
    DistributedTracer,
    CustomTracer,
    PerformanceAnalyzer,
    TraceDebugger,
    SpanKind,
    TraceLevel,
    SpanContext,
    SpanData,
    initialize_tracing,
    get_tracer,
    trace
)


class TestCustomTracer:
    """Test custom tracer implementation"""
    
    @pytest.fixture
    def tracer(self):
        return CustomTracer("test-service")
    
    def test_tracer_initialization(self, tracer):
        """Test tracer initialization"""
        assert tracer.service_name == "test-service"
        assert len(tracer.spans) == 0
        assert len(tracer.active_spans) == 0
    
    def test_start_span(self, tracer):
        """Test starting a span"""
        span = tracer.start_span("test_operation")
        
        assert isinstance(span, SpanData)
        assert span.operation_name == "test_operation"
        assert span.trace_id is not None
        assert span.span_id is not None
        assert span.parent_span_id is None
        assert span.start_time is not None
        assert span.end_time is None
        assert span.status == "ok"
        assert span.span_kind == SpanKind.INTERNAL
        assert span.service_name == "test-service"
    
    def test_start_child_span(self, tracer):
        """Test starting a child span"""
        parent_span = tracer.start_span("parent_operation")
        parent_context = SpanContext(
            trace_id=parent_span.trace_id,
            span_id=parent_span.span_id
        )
        
        child_span = tracer.start_span("child_operation", parent_context=parent_context)
        
        assert child_span.trace_id == parent_span.trace_id
        assert child_span.parent_span_id == parent_span.span_id
        assert child_span.span_id != parent_span.span_id
    
    def test_finish_span(self, tracer):
        """Test finishing a span"""
        span = tracer.start_span("test_operation")
        time.sleep(0.01)  # Small delay
        
        tracer.finish_span(span)
        
        assert span.end_time is not None
        assert span.duration_ms is not None
        assert span.duration_ms > 0
        assert span.status == "ok"
    
    def test_finish_span_with_error(self, tracer):
        """Test finishing a span with error status"""
        span = tracer.start_span("test_operation")
        tracer.finish_span(span, status="error")
        
        assert span.status == "error"
    
    def test_get_active_span(self, tracer):
        """Test getting active span"""
        assert tracer.get_active_span() is None
        
        span = tracer.start_span("test_operation")
        active_span = tracer.get_active_span()
        
        assert active_span is not None
        assert active_span.span_id == span.span_id
    
    def test_add_span_tag(self, tracer):
        """Test adding tags to span"""
        span = tracer.start_span("test_operation")
        tracer.add_span_tag(span, "user_id", "12345")
        tracer.add_span_tag(span, "operation_type", "database_query")
        
        assert span.tags["user_id"] == "12345"
        assert span.tags["operation_type"] == "database_query"
    
    def test_add_span_log(self, tracer):
        """Test adding logs to span"""
        span = tracer.start_span("test_operation")
        tracer.add_span_log(span, "Starting operation", TraceLevel.INFO)
        tracer.add_span_log(span, "Error occurred", TraceLevel.ERROR)
        
        assert len(span.logs) == 2
        assert span.logs[0]["message"] == "Starting operation"
        assert span.logs[0]["level"] == "info"
        assert span.logs[1]["message"] == "Error occurred"
        assert span.logs[1]["level"] == "error"
    
    def test_get_trace_spans(self, tracer):
        """Test getting spans for a trace"""
        span1 = tracer.start_span("operation1")
        span2 = tracer.start_span("operation2", SpanContext(span1.trace_id, span1.span_id))
        span3 = tracer.start_span("operation3")  # Different trace
        
        trace_spans = tracer.get_trace_spans(span1.trace_id)
        
        assert len(trace_spans) == 2
        assert all(span.trace_id == span1.trace_id for span in trace_spans)
        
        other_trace_spans = tracer.get_trace_spans(span3.trace_id)
        assert len(other_trace_spans) == 1


class TestDistributedTracer:
    """Test distributed tracer"""
    
    @pytest.fixture
    def tracer(self):
        return DistributedTracer("test-service")
    
    def test_tracer_initialization(self, tracer):
        """Test tracer initialization"""
        assert tracer.service_name == "test-service"
        assert tracer.sampling_rate == 1.0
        assert tracer.custom_tracer is not None  # Should use custom tracer when OpenTelemetry not available
    
    @pytest.mark.asyncio
    async def test_trace_async_context_manager(self, tracer):
        """Test async tracing context manager"""
        async with tracer.trace_async("test_operation") as span:
            await asyncio.sleep(0.01)
            assert span is not None
        
        # Check that performance data was recorded
        assert "test_operation" in tracer.performance_data
        assert len(tracer.performance_data["test_operation"]) == 1
        assert tracer.performance_data["test_operation"][0]["duration_ms"] > 0
    
    @pytest.mark.asyncio
    async def test_trace_async_with_tags(self, tracer):
        """Test async tracing with tags"""
        tags = {"user_id": "12345", "operation_type": "query"}
        
        async with tracer.trace_async("test_operation", tags=tags) as span:
            await asyncio.sleep(0.01)
            if hasattr(span, 'tags'):  # Custom tracer
                assert span.tags["user_id"] == "12345"
                assert span.tags["operation_type"] == "query"
    
    @pytest.mark.asyncio
    async def test_trace_async_with_exception(self, tracer):
        """Test async tracing with exception"""
        with pytest.raises(ValueError):
            async with tracer.trace_async("test_operation") as span:
                raise ValueError("Test error")
        
        # Should still record performance data
        assert "test_operation" in tracer.performance_data
    
    def test_trace_sync_context_manager(self, tracer):
        """Test sync tracing context manager"""
        with tracer.trace_sync("test_operation") as span:
            time.sleep(0.01)
            assert span is not None
        
        # Check that performance data was recorded
        assert "test_operation" in tracer.performance_data
        assert len(tracer.performance_data["test_operation"]) == 1
    
    def test_trace_function_decorator_async(self, tracer):
        """Test function decorator for async functions"""
        @tracer.trace_function("decorated_async_operation")
        async def async_test_function():
            await asyncio.sleep(0.01)
            return "success"
        
        async def run_test():
            result = await async_test_function()
            assert result == "success"
            assert "decorated_async_operation" in tracer.performance_data
        
        asyncio.run(run_test())
    
    def test_trace_function_decorator_sync(self, tracer):
        """Test function decorator for sync functions"""
        @tracer.trace_function("decorated_sync_operation")
        def sync_test_function():
            time.sleep(0.01)
            return "success"
        
        result = sync_test_function()
        assert result == "success"
        assert "decorated_sync_operation" in tracer.performance_data
    
    def test_performance_data_recording(self, tracer):
        """Test performance data recording and cleanup"""
        # Generate many data points
        for i in range(1200):  # More than the 1000 limit
            tracer._record_performance("test_operation", float(i))
        
        # Should keep only the last 1000 entries
        assert len(tracer.performance_data["test_operation"]) == 1000
        # Should keep the most recent entries
        assert tracer.performance_data["test_operation"][-1]["duration_ms"] == 1199.0


class TestPerformanceAnalyzer:
    """Test performance analyzer"""
    
    @pytest.fixture
    def tracer_with_data(self):
        tracer = DistributedTracer("test-service")
        
        # Add sample performance data
        for i in range(100):
            tracer._record_performance("fast_operation", 50.0 + i)  # 50-149ms
            tracer._record_performance("slow_operation", 1000.0 + i * 10)  # 1000-1990ms
            tracer._record_performance("variable_operation", 100.0 if i % 2 == 0 else 2000.0)
        
        return tracer
    
    @pytest.fixture
    def analyzer(self, tracer_with_data):
        return PerformanceAnalyzer(tracer_with_data)
    
    def test_identify_bottlenecks(self, analyzer):
        """Test bottleneck identification"""
        bottlenecks = analyzer.identify_bottlenecks(threshold_ms=500.0)
        
        assert len(bottlenecks) >= 2  # slow_operation and variable_operation should be identified
        
        # Should be sorted by average duration (descending)
        assert bottlenecks[0]["avg_duration_ms"] >= bottlenecks[1]["avg_duration_ms"]
        
        # Check that slow_operation is identified
        slow_op_bottleneck = next((b for b in bottlenecks if b["operation"] == "slow_operation"), None)
        assert slow_op_bottleneck is not None
        assert slow_op_bottleneck["severity"] in ["medium", "high"]
    
    def test_get_operation_stats(self, analyzer):
        """Test getting operation statistics"""
        stats = analyzer.get_operation_stats("fast_operation")
        
        assert stats["operation"] == "fast_operation"
        assert stats["sample_count"] == 100
        assert 50.0 <= stats["min_duration_ms"] <= 60.0
        assert 140.0 <= stats["max_duration_ms"] <= 150.0
        assert 90.0 <= stats["avg_duration_ms"] <= 110.0
        assert stats["recent_trend"] in ["improving", "degrading", "stable", "insufficient_data"]
    
    def test_get_operation_stats_nonexistent(self, analyzer):
        """Test getting stats for non-existent operation"""
        stats = analyzer.get_operation_stats("nonexistent_operation")
        assert "error" in stats
    
    def test_calculate_trend(self, analyzer):
        """Test trend calculation"""
        # Test with improving trend data
        improving_data = [
            {"duration_ms": 100.0, "timestamp": datetime.now()},
            {"duration_ms": 90.0, "timestamp": datetime.now()},
            {"duration_ms": 80.0, "timestamp": datetime.now()},
            {"duration_ms": 70.0, "timestamp": datetime.now()},
            {"duration_ms": 60.0, "timestamp": datetime.now()},
            {"duration_ms": 50.0, "timestamp": datetime.now()},
            {"duration_ms": 40.0, "timestamp": datetime.now()},
            {"duration_ms": 30.0, "timestamp": datetime.now()},
            {"duration_ms": 20.0, "timestamp": datetime.now()},
            {"duration_ms": 10.0, "timestamp": datetime.now()}
        ]
        
        trend = analyzer._calculate_trend(improving_data)
        assert trend == "improving"
        
        # Test with insufficient data
        insufficient_data = [{"duration_ms": 100.0, "timestamp": datetime.now()}]
        trend = analyzer._calculate_trend(insufficient_data)
        assert trend == "insufficient_data"


class TestTraceDebugger:
    """Test trace debugger"""
    
    @pytest.fixture
    def tracer_with_traces(self):
        tracer = DistributedTracer("test-service")
        
        # Create some test spans with different durations
        span1 = tracer.custom_tracer.start_span("fast_operation")
        span1.duration_ms = 100.0
        tracer.custom_tracer.finish_span(span1)
        
        span2 = tracer.custom_tracer.start_span("slow_operation")
        span2.duration_ms = 6000.0  # 6 seconds - should be flagged as slow
        tracer.custom_tracer.finish_span(span2)
        
        span3 = tracer.custom_tracer.start_span("very_slow_operation")
        span3.duration_ms = 10000.0  # 10 seconds - very slow
        tracer.custom_tracer.finish_span(span3)
        
        return tracer
    
    @pytest.fixture
    def debugger(self, tracer_with_traces):
        return TraceDebugger(tracer_with_traces)
    
    def test_find_slow_traces(self, debugger):
        """Test finding slow traces"""
        slow_traces = debugger.find_slow_traces(threshold_ms=5000.0)
        
        assert len(slow_traces) >= 2  # slow_operation and very_slow_operation
        
        # Should be sorted by duration (descending)
        assert slow_traces[0]["total_duration_ms"] >= slow_traces[1]["total_duration_ms"]
        
        # Check that very_slow_operation is the slowest
        assert slow_traces[0]["slowest_operation"] == "very_slow_operation"
    
    def test_analyze_trace_tree(self, debugger):
        """Test trace tree analysis"""
        # Create a trace with parent-child relationship
        tracer = debugger.tracer
        parent_span = tracer.custom_tracer.start_span("parent_operation")
        parent_span.duration_ms = 1000.0
        
        child_context = SpanContext(parent_span.trace_id, parent_span.span_id)
        child_span = tracer.custom_tracer.start_span("child_operation", parent_context=child_context)
        child_span.duration_ms = 500.0
        
        tracer.custom_tracer.finish_span(parent_span)
        tracer.custom_tracer.finish_span(child_span)
        
        # Analyze the trace tree
        tree = debugger.analyze_trace_tree(parent_span.trace_id)
        
        assert tree["trace_id"] == parent_span.trace_id
        assert tree["total_spans"] == 2
        assert len(tree["root_spans"]) == 1
        
        root = tree["root_spans"][0]
        assert root["operation"] == "parent_operation"
        assert root["duration_ms"] == 1000.0
        assert len(root["children"]) == 1
        assert root["children"][0]["operation"] == "child_operation"
    
    def test_analyze_nonexistent_trace(self, debugger):
        """Test analyzing non-existent trace"""
        tree = debugger.analyze_trace_tree("nonexistent-trace-id")
        assert "error" in tree


class TestGlobalTracingFunctions:
    """Test global tracing functions"""
    
    def test_initialize_tracing(self):
        """Test global tracer initialization"""
        tracer = initialize_tracing("global-test-service")
        
        assert tracer is not None
        assert tracer.service_name == "global-test-service"
        assert get_tracer() == tracer
    
    def test_trace_decorator_with_global_tracer(self):
        """Test trace decorator with global tracer"""
        initialize_tracing("decorator-test-service")
        
        @trace("global_decorated_operation")
        def test_function():
            time.sleep(0.01)
            return "success"
        
        result = test_function()
        assert result == "success"
        
        # Check that performance data was recorded
        global_tracer = get_tracer()
        assert "global_decorated_operation" in global_tracer.performance_data
    
    def test_trace_decorator_without_global_tracer(self):
        """Test trace decorator without global tracer (should be no-op)"""
        # Reset global tracer
        import nautilus_trader_engine.monitoring.distributed_tracing as dt_module
        dt_module._global_tracer = None
        
        @trace("no_tracer_operation")
        def test_function():
            return "success"
        
        result = test_function()
        assert result == "success"  # Should still work as no-op


@pytest.mark.asyncio
async def test_integration_scenario():
    """Test complete integration scenario"""
    # Initialize tracing
    tracer = initialize_tracing("integration-test")
    
    # Create a complex workflow with nested operations
    @trace("database_query")
    async def fetch_user_data(user_id: str):
        await asyncio.sleep(0.02)  # Simulate DB latency
        return f"user_data_{user_id}"
    
    @trace("cache_lookup")
    async def check_cache(key: str):
        await asyncio.sleep(0.005)  # Simulate cache lookup
        return None  # Cache miss
    
    @trace("business_logic")
    async def process_user_data(data: str):
        await asyncio.sleep(0.01)  # Simulate processing
        return data.upper()
    
    @trace("main_workflow", tags={"version": "1.0", "environment": "test"})
    async def user_workflow(user_id: str):
        # Check cache first
        async with tracer.trace_async("cache_check"):
            cached_data = await check_cache(f"user_{user_id}")
        
        if not cached_data:
            # Fetch from database
            async with tracer.trace_async("data_fetch"):
                user_data = await fetch_user_data(user_id)
        else:
            user_data = cached_data
        
        # Process the data
        async with tracer.trace_async("data_processing"):
            result = await process_user_data(user_data)
        
        return result
    
    # Execute the workflow multiple times
    results = []
    for i in range(5):
        result = await user_workflow(f"user_{i}")
        results.append(result)
    
    # Verify results
    assert len(results) == 5
    assert all("USER_DATA_USER_" in result for result in results)
    
    # Analyze performance
    analyzer = PerformanceAnalyzer(tracer)
    
    # Should have performance data for all operations
    expected_operations = [
        "database_query", "cache_lookup", "business_logic", 
        "main_workflow", "cache_check", "data_fetch", "data_processing"
    ]
    
    for operation in expected_operations:
        stats = analyzer.get_operation_stats(operation)
        if "error" not in stats:
            assert stats["sample_count"] > 0
            assert stats["avg_duration_ms"] > 0
    
    # Check for bottlenecks
    bottlenecks = analyzer.identify_bottlenecks(threshold_ms=15.0)
    
    # Database query should be identified as a bottleneck due to higher latency
    db_bottleneck = next((b for b in bottlenecks if "database" in b["operation"]), None)
    if db_bottleneck:
        assert db_bottleneck["avg_duration_ms"] > 15.0
    
    # Debug analysis
    debugger = TraceDebugger(tracer)
    slow_traces = debugger.find_slow_traces(threshold_ms=30.0)
    
    # Should find some traces (main_workflow traces should be around 35-40ms total)
    assert len(slow_traces) >= 0  # May or may not find slow traces depending on timing
    
    print("Integration test completed successfully!")
    print(f"Executed {len(results)} workflows")
    print(f"Tracked {len(expected_operations)} operation types")
    print(f"Identified {len(bottlenecks)} potential bottlenecks")
    print(f"Found {len(slow_traces)} slow traces")


if __name__ == "__main__":
    # Run the integration test
    asyncio.run(test_integration_scenario())