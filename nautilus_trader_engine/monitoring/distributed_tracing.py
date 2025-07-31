"""
Distributed Tracing System
OpenTelemetry-based distributed tracing for end-to-end request tracking,
performance bottleneck identification, and trace-based debugging.
"""

import asyncio
import logging
import time
import uuid
import json
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum
from contextlib import asynccontextmanager
import threading
from functools import wraps

# Try to import OpenTelemetry components
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.asyncio import AsyncIOInstrumentor
    from opentelemetry.trace.status import Status, StatusCode
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    trace = None


class SpanKind(Enum):
    """Span kinds for different operation types"""
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class TraceLevel(Enum):
    """Trace levels for filtering"""
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


@dataclass
class SpanContext:
    """Span context information"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    baggage: Dict[str, str] = field(default_factory=dict)


@dataclass
class SpanData:
    """Span data for custom tracing implementation"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: str = "ok"
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    span_kind: SpanKind = SpanKind.INTERNAL
    service_name: str = "nautilus-trader"


class CustomTracer:
    """Custom tracer implementation when OpenTelemetry is not available"""
    
    def __init__(self, service_name: str = "nautilus-trader"):
        self.service_name = service_name
        self.spans: Dict[str, SpanData] = {}
        self.active_spans: Dict[str, str] = {}  # thread_id -> span_id
        self.logger = logging.getLogger(__name__)
        self._lock = threading.Lock()
    
    def start_span(self, 
                   operation_name: str, 
                   parent_context: Optional[SpanContext] = None,
                   span_kind: SpanKind = SpanKind.INTERNAL,
                   tags: Dict[str, Any] = None) -> SpanData:
        """Start a new span"""
        with self._lock:
            trace_id = parent_context.trace_id if parent_context else str(uuid.uuid4())
            span_id = str(uuid.uuid4())
            parent_span_id = parent_context.span_id if parent_context else None
            
            span = SpanData(
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=parent_span_id,
                operation_name=operation_name,
                start_time=datetime.now(),
                span_kind=span_kind,
                service_name=self.service_name,
                tags=tags or {}
            )
            
            self.spans[span_id] = span
            thread_id = threading.get_ident()
            self.active_spans[thread_id] = span_id
            
            return span
    
    def finish_span(self, span: SpanData, status: str = "ok"):
        """Finish a span"""
        with self._lock:
            span.end_time = datetime.now()
            span.duration_ms = (span.end_time - span.start_time).total_seconds() * 1000
            span.status = status
            
            # Remove from active spans
            thread_id = threading.get_ident()
            if thread_id in self.active_spans and self.active_spans[thread_id] == span.span_id:
                del self.active_spans[thread_id]
    
    def get_active_span(self) -> Optional[SpanData]:
        """Get the currently active span"""
        thread_id = threading.get_ident()
        span_id = self.active_spans.get(thread_id)
        return self.spans.get(span_id) if span_id else None
    
    def add_span_tag(self, span: SpanData, key: str, value: Any):
        """Add a tag to a span"""
        span.tags[key] = value
    
    def add_span_log(self, span: SpanData, message: str, level: TraceLevel = TraceLevel.INFO):
        """Add a log entry to a span"""
        span.logs.append({
            "timestamp": datetime.now().isoformat(),
            "level": level.value,
            "message": message
        })
    
    def get_trace_spans(self, trace_id: str) -> List[SpanData]:
        """Get all spans for a trace"""
        return [span for span in self.spans.values() if span.trace_id == trace_id]


class DistributedTracer:
    """Main distributed tracing system"""
    
    def __init__(self, 
                 service_name: str = "nautilus-trader",
                 jaeger_endpoint: Optional[str] = None,
                 sampling_rate: float = 1.0):
        self.service_name = service_name
        self.sampling_rate = sampling_rate
        self.logger = logging.getLogger(__name__)
        
        # Initialize tracer
        if OPENTELEMETRY_AVAILABLE:
            self._init_opentelemetry_tracer(jaeger_endpoint)
            self.tracer = trace.get_tracer(__name__)
            self.custom_tracer = None
        else:
            self.logger.warning("OpenTelemetry not available, using custom tracer")
            self.tracer = None
            self.custom_tracer = CustomTracer(service_name)
        
        # Performance tracking
        self.performance_data = defaultdict(list)
        self.bottlenecks = []
        
    def _init_opentelemetry_tracer(self, jaeger_endpoint: Optional[str]):
        """Initialize OpenTelemetry tracer"""
        try:
            # Set up tracer provider
            trace.set_tracer_provider(TracerProvider())
            
            # Set up exporters
            console_exporter = ConsoleSpanExporter()
            span_processor = BatchSpanProcessor(console_exporter)
            
            trace.get_tracer_provider().add_span_processor(span_processor)
            
            # Auto-instrument common libraries
            RequestsInstrumentor().instrument()
            AsyncIOInstrumentor().instrument()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenTelemetry: {e}")
    
    @asynccontextmanager
    async def trace_async(self, 
                         operation_name: str,
                         span_kind: SpanKind = SpanKind.INTERNAL,
                         tags: Dict[str, Any] = None):
        """Async context manager for tracing"""
        if self.tracer:
            # OpenTelemetry implementation
            with self.tracer.start_as_current_span(operation_name) as span:
                if tags:
                    for key, value in tags.items():
                        span.set_attribute(key, str(value))
                
                start_time = time.time()
                try:
                    yield span
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
                finally:
                    duration = (time.time() - start_time) * 1000
                    span.set_attribute("duration_ms", duration)
                    self._record_performance(operation_name, duration)
        else:
            # Custom tracer implementation
            span = self.custom_tracer.start_span(operation_name, span_kind=span_kind, tags=tags)
            start_time = time.time()
            try:
                yield span
            except Exception as e:
                self.custom_tracer.finish_span(span, status="error")
                self.custom_tracer.add_span_log(span, f"Error: {str(e)}", TraceLevel.ERROR)
                raise
            finally:
                duration = (time.time() - start_time) * 1000
                self.custom_tracer.add_span_tag(span, "duration_ms", duration)
                self.custom_tracer.finish_span(span)
                self._record_performance(operation_name, duration)
    
    def _record_performance(self, operation_name: str, duration_ms: float):
        """Record performance data for analysis"""
        self.performance_data[operation_name].append({
            "timestamp": datetime.now(),
            "duration_ms": duration_ms
        })
        
        # Keep only recent data (last 1000 entries per operation)
        if len(self.performance_data[operation_name]) > 1000:
            self.performance_data[operation_name] = self.performance_data[operation_name][-1000:]
    
    def trace_function(self, 
                      operation_name: Optional[str] = None,
                      span_kind: SpanKind = SpanKind.INTERNAL,
                      tags: Dict[str, Any] = None):
        """Decorator for tracing functions"""
        def decorator(func):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            if asyncio.iscoroutinefunction(func):
                @wraps(func)
                async def async_wrapper(*args, **kwargs):
                    async with self.trace_async(op_name, span_kind, tags):
                        return await func(*args, **kwargs)
                return async_wrapper
            else:
                @wraps(func)
                def sync_wrapper(*args, **kwargs):
                    with self.trace_sync(op_name, span_kind, tags):
                        return func(*args, **kwargs)
                return sync_wrapper
        
        return decorator
    
    def trace_sync(self, 
                   operation_name: str,
                   span_kind: SpanKind = SpanKind.INTERNAL,
                   tags: Dict[str, Any] = None):
        """Synchronous context manager for tracing"""
        class SyncTraceContext:
            def __init__(self, tracer_instance):
                self.tracer_instance = tracer_instance
                self.operation_name = operation_name
                self.span_kind = span_kind
                self.tags = tags or {}
                self.span = None
                self.start_time = None
            
            def __enter__(self):
                if self.tracer_instance.tracer:
                    self.span = self.tracer_instance.tracer.start_span(self.operation_name)
                    for key, value in self.tags.items():
                        self.span.set_attribute(key, str(value))
                else:
                    self.span = self.tracer_instance.custom_tracer.start_span(
                        self.operation_name, span_kind=self.span_kind, tags=self.tags
                    )
                
                self.start_time = time.time()
                return self.span
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                duration = (time.time() - self.start_time) * 1000
                
                if self.tracer_instance.tracer:
                    if exc_type:
                        self.span.set_status(Status(StatusCode.ERROR, str(exc_val)))
                    self.span.set_attribute("duration_ms", duration)
                    self.span.end()
                else:
                    if exc_type:
                        self.tracer_instance.custom_tracer.add_span_log(
                            self.span, f"Error: {str(exc_val)}", TraceLevel.ERROR
                        )
                        self.tracer_instance.custom_tracer.finish_span(self.span, status="error")
                    else:
                        self.tracer_instance.custom_tracer.add_span_tag(self.span, "duration_ms", duration)
                        self.tracer_instance.custom_tracer.finish_span(self.span)
                
                self.tracer_instance._record_performance(self.operation_name, duration)
        
        return SyncTraceContext(self)


class PerformanceAnalyzer:
    """Analyzes performance data from traces"""
    
    def __init__(self, tracer: DistributedTracer):
        self.tracer = tracer
        self.logger = logging.getLogger(__name__)
    
    def identify_bottlenecks(self, threshold_ms: float = 1000.0) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks"""
        bottlenecks = []
        
        for operation_name, data_points in self.tracer.performance_data.items():
            if not data_points:
                continue
            
            durations = [dp["duration_ms"] for dp in data_points]
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            p95_duration = sorted(durations)[int(len(durations) * 0.95)] if durations else 0
            
            if avg_duration > threshold_ms or p95_duration > threshold_ms * 2:
                bottlenecks.append({
                    "operation": operation_name,
                    "avg_duration_ms": avg_duration,
                    "max_duration_ms": max_duration,
                    "p95_duration_ms": p95_duration,
                    "sample_count": len(durations),
                    "severity": "high" if avg_duration > threshold_ms * 2 else "medium"
                })
        
        return sorted(bottlenecks, key=lambda x: x["avg_duration_ms"], reverse=True)
    
    def get_operation_stats(self, operation_name: str) -> Dict[str, Any]:
        """Get detailed statistics for an operation"""
        data_points = self.tracer.performance_data.get(operation_name, [])
        
        if not data_points:
            return {"error": "No data available for operation"}
        
        durations = [dp["duration_ms"] for dp in data_points]
        durations.sort()
        
        stats = {
            "operation": operation_name,
            "sample_count": len(durations),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
            "avg_duration_ms": sum(durations) / len(durations),
            "median_duration_ms": durations[len(durations) // 2],
            "p95_duration_ms": durations[int(len(durations) * 0.95)],
            "p99_duration_ms": durations[int(len(durations) * 0.99)],
            "recent_trend": self._calculate_trend(data_points[-100:])  # Last 100 samples
        }
        
        return stats
    
    def _calculate_trend(self, recent_data: List[Dict[str, Any]]) -> str:
        """Calculate performance trend"""
        if len(recent_data) < 10:
            return "insufficient_data"
        
        # Simple trend calculation - compare first and last halves
        mid_point = len(recent_data) // 2
        first_half_avg = sum(dp["duration_ms"] for dp in recent_data[:mid_point]) / mid_point
        second_half_avg = sum(dp["duration_ms"] for dp in recent_data[mid_point:]) / (len(recent_data) - mid_point)
        
        if second_half_avg > first_half_avg * 1.1:
            return "degrading"
        elif second_half_avg < first_half_avg * 0.9:
            return "improving"
        else:
            return "stable"


class TraceDebugger:
    """Debug tools for trace analysis"""
    
    def __init__(self, tracer: DistributedTracer):
        self.tracer = tracer
        self.logger = logging.getLogger(__name__)
    
    def find_slow_traces(self, threshold_ms: float = 5000.0) -> List[Dict[str, Any]]:
        """Find traces that exceed duration threshold"""
        slow_traces = []
        
        if self.tracer.custom_tracer:
            # Group spans by trace_id
            traces = defaultdict(list)
            for span in self.tracer.custom_tracer.spans.values():
                if span.duration_ms and span.duration_ms > threshold_ms:
                    traces[span.trace_id].append(span)
            
            for trace_id, spans in traces.items():
                total_duration = sum(span.duration_ms for span in spans if span.duration_ms)
                slow_traces.append({
                    "trace_id": trace_id,
                    "total_duration_ms": total_duration,
                    "span_count": len(spans),
                    "operations": [span.operation_name for span in spans],
                    "slowest_operation": max(spans, key=lambda s: s.duration_ms or 0).operation_name
                })
        
        return sorted(slow_traces, key=lambda x: x["total_duration_ms"], reverse=True)
    
    def analyze_trace_tree(self, trace_id: str) -> Dict[str, Any]:
        """Analyze the structure of a trace"""
        if not self.tracer.custom_tracer:
            return {"error": "Custom tracer not available"}
        
        spans = self.tracer.custom_tracer.get_trace_spans(trace_id)
        if not spans:
            return {"error": "Trace not found"}
        
        # Build trace tree
        root_spans = [s for s in spans if not s.parent_span_id]
        child_spans = defaultdict(list)
        
        for span in spans:
            if span.parent_span_id:
                child_spans[span.parent_span_id].append(span)
        
        def build_tree(span: SpanData) -> Dict[str, Any]:
            children = child_spans.get(span.span_id, [])
            return {
                "span_id": span.span_id,
                "operation": span.operation_name,
                "duration_ms": span.duration_ms,
                "status": span.status,
                "tags": span.tags,
                "children": [build_tree(child) for child in children]
            }
        
        return {
            "trace_id": trace_id,
            "total_spans": len(spans),
            "root_spans": [build_tree(root) for root in root_spans],
            "total_duration_ms": sum(s.duration_ms for s in spans if s.duration_ms)
        }


# Global tracer instance
_global_tracer: Optional[DistributedTracer] = None


def initialize_tracing(service_name: str = "nautilus-trader", 
                      jaeger_endpoint: Optional[str] = None,
                      sampling_rate: float = 1.0) -> DistributedTracer:
    """Initialize global distributed tracing"""
    global _global_tracer
    _global_tracer = DistributedTracer(service_name, jaeger_endpoint, sampling_rate)
    return _global_tracer


def get_tracer() -> Optional[DistributedTracer]:
    """Get the global tracer instance"""
    return _global_tracer


def trace(operation_name: Optional[str] = None,
          span_kind: SpanKind = SpanKind.INTERNAL,
          tags: Dict[str, Any] = None):
    """Decorator for tracing functions"""
    if _global_tracer:
        return _global_tracer.trace_function(operation_name, span_kind, tags)
    else:
        # No-op decorator if tracing not initialized
        def decorator(func):
            return func
        return decorator


# Example usage and testing
async def example_usage():
    """Example usage of the Distributed Tracing System"""
    
    # Initialize tracing
    tracer = initialize_tracing("nautilus-trader-example")
    
    # Example traced function
    @tracer.trace_function("database_query")
    async def fetch_data(query: str):
        """Simulated database query"""
        await asyncio.sleep(0.1)  # Simulate DB latency
        return f"Results for: {query}"
    
    @tracer.trace_function("business_logic")
    async def process_data(data: str):
        """Simulated business logic"""
        await asyncio.sleep(0.05)  # Simulate processing
        return data.upper()
    
    @tracer.trace_function("main_operation", tags={"version": "1.0", "user": "test"})
    async def main_workflow():
        """Main workflow with nested operations"""
        async with tracer.trace_async("data_preparation"):
            data = await fetch_data("SELECT * FROM trades")
        
        async with tracer.trace_async("data_processing"):
            result = await process_data(data)
        
        return result
    
    # Execute traced operations
    print("Executing traced operations...")
    result = await main_workflow()
    print(f"Result: {result}")
    
    # Analyze performance
    analyzer = PerformanceAnalyzer(tracer)
    bottlenecks = analyzer.identify_bottlenecks(threshold_ms=50.0)
    
    print(f"\n=== Performance Analysis ===")
    if bottlenecks:
        print("Identified bottlenecks:")
        for bottleneck in bottlenecks:
            print(f"- {bottleneck['operation']}: {bottleneck['avg_duration_ms']:.2f}ms avg")
    else:
        print("No significant bottlenecks detected")
    
    # Get operation statistics
    for operation in ["database_query", "business_logic", "main_operation"]:
        stats = analyzer.get_operation_stats(operation)
        if "error" not in stats:
            print(f"\n{operation} stats:")
            print(f"  Average: {stats['avg_duration_ms']:.2f}ms")
            print(f"  P95: {stats['p95_duration_ms']:.2f}ms")
            print(f"  Samples: {stats['sample_count']}")
    
    # Debug trace analysis
    debugger = TraceDebugger(tracer)
    slow_traces = debugger.find_slow_traces(threshold_ms=100.0)
    
    if slow_traces:
        print(f"\n=== Slow Traces ===")
        for trace in slow_traces[:3]:  # Show top 3
            print(f"Trace {trace['trace_id'][:8]}: {trace['total_duration_ms']:.2f}ms")
            print(f"  Operations: {', '.join(trace['operations'])}")


if __name__ == "__main__":
    asyncio.run(example_usage())