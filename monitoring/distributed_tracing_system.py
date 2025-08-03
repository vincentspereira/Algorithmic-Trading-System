#!/usr/bin/env python3
"""
Distributed Tracing System
OpenTelemetry-based distributed tracing implementation for comprehensive
observability across all trading system services with performance analysis
and bottleneck identification.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import threading
import os
import sys
from pathlib import Path
import random

# OpenTelemetry imports
try:
    from opentelemetry import trace, metrics, baggage
    from opentelemetry.sdk.trace import TracerProvider, Span
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
    from opentelemetry.instrumentation.asyncio import AsyncioInstrumentor
    from opentelemetry.propagate import set_global_textmap
    from opentelemetry.propagators.b3 import B3MultiFormat
    from opentelemetry.trace.status import Status, StatusCode
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    # Fallback implementation when OpenTelemetry is not available
    OPENTELEMETRY_AVAILABLE = False
    print("OpenTelemetry not available, using fallback implementation")

import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

class SpanKind(Enum):
    """Span kinds for different operation types"""
    INTERNAL = "INTERNAL"
    SERVER = "SERVER"
    CLIENT = "CLIENT"
    PRODUCER = "PRODUCER"
    CONSUMER = "CONSUMER"

class TraceStatus(Enum):
    """Trace status codes"""
    OK = "OK"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"

@dataclass
class SpanContext:
    """Span context for trace correlation"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    trace_flags: int = 1
    trace_state: Dict[str, str] = field(default_factory=dict)
    baggage: Dict[str, str] = field(default_factory=dict)

@dataclass
class SpanData:
    """Comprehensive span data structure"""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    operation_name: str
    service_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    status: TraceStatus = TraceStatus.OK
    kind: SpanKind = SpanKind.INTERNAL
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    links: List[Dict[str, Any]] = field(default_factory=list)
    resource: Dict[str, str] = field(default_factory=dict)
    
    def finish(self, status: Optional[TraceStatus] = None):
        """Finish the span"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        if status:
            self.status = status

@dataclass
class TraceData:
    """Complete trace data with all spans"""
    trace_id: str
    spans: List[SpanData]
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    service_count: int = 0
    error_count: int = 0
    root_span: Optional[SpanData] = None
    
    def __post_init__(self):
        """Calculate trace metrics"""
        if self.spans:
            self.start_time = min(span.start_time for span in self.spans)
            if all(span.end_time for span in self.spans):
                self.end_time = max(span.end_time for span in self.spans if span.end_time)
                self.duration = self.end_time - self.start_time
            
            self.service_count = len(set(span.service_name for span in self.spans))
            self.error_count = sum(1 for span in self.spans if span.status == TraceStatus.ERROR)
            
            # Find root span (span without parent)
            root_spans = [span for span in self.spans if not span.parent_span_id]
            self.root_span = root_spans[0] if root_spans else None

class PerformanceAnalyzer:
    """Performance analysis and bottleneck identification"""
    
    def __init__(self):
        self.trace_data: Dict[str, TraceData] = {}
        self.service_metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'total_requests': 0,
            'total_duration': 0.0,
            'error_count': 0,
            'avg_duration': 0.0,
            'p95_duration': 0.0,
            'p99_duration': 0.0,
            'durations': deque(maxlen=1000)
        })
        self.operation_metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'total_requests': 0,
            'total_duration': 0.0,
            'error_count': 0,
            'avg_duration': 0.0,
            'durations': deque(maxlen=1000)
        })
        
        logger.info("Performance analyzer initialized")
    
    def analyze_trace(self, trace: TraceData) -> Dict[str, Any]:
        """Analyze a complete trace for performance insights"""
        analysis = {
            'trace_id': trace.trace_id,
            'total_duration': trace.duration,
            'service_count': trace.service_count,
            'span_count': len(trace.spans),
            'error_count': trace.error_count,
            'bottlenecks': [],
            'critical_path': [],
            'service_breakdown': {},
            'recommendations': []
        }
        
        # Analyze service breakdown
        service_durations = defaultdict(float)
        for span in trace.spans:
            if span.duration:
                service_durations[span.service_name] += span.duration
        
        total_service_time = sum(service_durations.values())
        for service, duration in service_durations.items():
            percentage = (duration / total_service_time * 100) if total_service_time > 0 else 0
            analysis['service_breakdown'][service] = {
                'duration': duration,
                'percentage': percentage
            }
        
        # Identify bottlenecks (spans taking >20% of total trace time)
        if trace.duration:
            bottleneck_threshold = trace.duration * 0.2
            for span in trace.spans:
                if span.duration and span.duration > bottleneck_threshold:
                    analysis['bottlenecks'].append({
                        'span_id': span.span_id,
                        'operation': span.operation_name,
                        'service': span.service_name,
                        'duration': span.duration,
                        'percentage': (span.duration / trace.duration) * 100
                    })
        
        # Calculate critical path (longest sequential path)
        analysis['critical_path'] = self._calculate_critical_path(trace)
        
        # Generate recommendations
        analysis['recommendations'] = self._generate_recommendations(trace, analysis)
        
        return analysis
    
    def _calculate_critical_path(self, trace: TraceData) -> List[Dict[str, Any]]:
        """Calculate the critical path through the trace"""
        # Build span hierarchy
        span_children = defaultdict(list)
        span_map = {span.span_id: span for span in trace.spans}
        
        for span in trace.spans:
            if span.parent_span_id:
                span_children[span.parent_span_id].append(span)
        
        def find_longest_path(span: SpanData) -> Tuple[float, List[SpanData]]:
            """Recursively find the longest path from this span"""
            children = span_children.get(span.span_id, [])
            if not children:
                return span.duration or 0, [span]
            
            max_child_duration = 0
            max_child_path = []
            
            for child in children:
                child_duration, child_path = find_longest_path(child)
                if child_duration > max_child_duration:
                    max_child_duration = child_duration
                    max_child_path = child_path
            
            total_duration = (span.duration or 0) + max_child_duration
            return total_duration, [span] + max_child_path
        
        if trace.root_span:
            _, critical_path_spans = find_longest_path(trace.root_span)
            return [
                {
                    'span_id': span.span_id,
                    'operation': span.operation_name,
                    'service': span.service_name,
                    'duration': span.duration,
                    'start_time': span.start_time
                }
                for span in critical_path_spans
            ]
        
        return []
    
    def _generate_recommendations(self, trace: TraceData, analysis: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations based on analysis"""
        recommendations = []
        
        # Check for slow operations
        if trace.duration and trace.duration > 1.0:  # > 1 second
            recommendations.append("Consider optimizing slow operations in the critical path")
        
        # Check for too many services
        if trace.service_count > 5:
            recommendations.append("High service count may indicate over-decomposition")
        
        # Check for errors
        if trace.error_count > 0:
            recommendations.append(f"Address {trace.error_count} errors in the trace")
        
        # Check for bottlenecks
        if analysis['bottlenecks']:
            recommendations.append("Focus optimization on identified bottleneck operations")
        
        # Check service distribution
        service_breakdown = analysis['service_breakdown']
        if service_breakdown:
            max_service = max(service_breakdown.items(), key=lambda x: x[1]['percentage'])
            if max_service[1]['percentage'] > 70:
                recommendations.append(f"Service '{max_service[0]}' dominates execution time")
        
        return recommendations
    
    def update_metrics(self, span: SpanData):
        """Update performance metrics with new span data"""
        if not span.duration:
            return
        
        # Update service metrics
        service_metrics = self.service_metrics[span.service_name]
        service_metrics['total_requests'] += 1
        service_metrics['total_duration'] += span.duration
        service_metrics['durations'].append(span.duration)
        
        if span.status == TraceStatus.ERROR:
            service_metrics['error_count'] += 1
        
        # Calculate percentiles
        durations = sorted(service_metrics['durations'])
        if durations:
            service_metrics['avg_duration'] = service_metrics['total_duration'] / service_metrics['total_requests']
            service_metrics['p95_duration'] = durations[int(len(durations) * 0.95)]
            service_metrics['p99_duration'] = durations[int(len(durations) * 0.99)]
        
        # Update operation metrics
        operation_key = f"{span.service_name}:{span.operation_name}"
        operation_metrics = self.operation_metrics[operation_key]
        operation_metrics['total_requests'] += 1
        operation_metrics['total_duration'] += span.duration
        operation_metrics['durations'].append(span.duration)
        
        if span.status == TraceStatus.ERROR:
            operation_metrics['error_count'] += 1
        
        if operation_metrics['total_requests'] > 0:
            operation_metrics['avg_duration'] = operation_metrics['total_duration'] / operation_metrics['total_requests']
    
    def get_service_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary by service"""
        return dict(self.service_metrics)
    
    def get_operation_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary by operation"""
        return dict(self.operation_metrics)

class TraceSampler:
    """Intelligent trace sampling for high-throughput environments"""
    
    def __init__(self, default_rate: float = 0.1):
        self.default_rate = default_rate
        self.service_rates: Dict[str, float] = {}
        self.operation_rates: Dict[str, Tuple[str, float]] = {}  # (service, rate)
        self.error_sampling_rate = 1.0  # Always sample errors
        self.slow_request_threshold = 1.0  # Sample all requests > 1s
        self.adaptive_sampling_enabled = True
        
        logger.info("Trace sampler initialized", default_rate=default_rate)
    
    def should_sample(self, service_name: str, operation_name: str, 
                     context: Optional[Dict[str, Any]] = None) -> bool:
        """Determine if a trace should be sampled"""
        # Always sample if there's an error context
        if context and context.get('error'):
            return True
        
        # Always sample slow requests
        if context and context.get('duration', 0) > self.slow_request_threshold:
            return True
        
        # Check operation-specific sampling rate
        operation_key = f"{service_name}:{operation_name}"
        if operation_key in self.operation_rates:
            _, rate = self.operation_rates[operation_key]
            return random.random() < rate
        
        # Check service-specific sampling rate
        if service_name in self.service_rates:
            rate = self.service_rates[service_name]
            return random.random() < rate
        
        # Use default sampling rate
        return random.random() < self.default_rate
    
    def set_service_sampling_rate(self, service_name: str, rate: float):
        """Set sampling rate for a specific service"""
        self.service_rates[service_name] = max(0.0, min(1.0, rate))
        logger.info("Updated service sampling rate", service=service_name, rate=rate)
    
    def set_operation_sampling_rate(self, service_name: str, operation_name: str, rate: float):
        """Set sampling rate for a specific operation"""
        operation_key = f"{service_name}:{operation_name}"
        self.operation_rates[operation_key] = (service_name, max(0.0, min(1.0, rate)))
        logger.info("Updated operation sampling rate", 
                   service=service_name, operation=operation_name, rate=rate)
    
    def adapt_sampling_rates(self, performance_data: Dict[str, Any]):
        """Adapt sampling rates based on performance data"""
        if not self.adaptive_sampling_enabled:
            return
        
        # Increase sampling for slow services
        for service, metrics in performance_data.get('services', {}).items():
            avg_duration = metrics.get('avg_duration', 0)
            error_rate = metrics.get('error_count', 0) / max(metrics.get('total_requests', 1), 1)
            
            # Increase sampling for slow or error-prone services
            if avg_duration > 0.5 or error_rate > 0.05:
                new_rate = min(1.0, self.service_rates.get(service, self.default_rate) * 1.5)
                self.set_service_sampling_rate(service, new_rate)
            # Decrease sampling for fast, reliable services
            elif avg_duration < 0.1 and error_rate < 0.01:
                new_rate = max(0.01, self.service_rates.get(service, self.default_rate) * 0.8)
                self.set_service_sampling_rate(service, new_rate)

class DistributedTracer:
    """Main distributed tracing system"""
    
    def __init__(self, service_name: str, config: Optional[Dict[str, Any]] = None):
        self.service_name = service_name
        self.config = config or {}
        
        # Core components
        self.performance_analyzer = PerformanceAnalyzer()
        self.trace_sampler = TraceSampler(
            default_rate=self.config.get('default_sampling_rate', 0.1)
        )
        
        # Trace storage
        self.active_spans: Dict[str, SpanData] = {}
        self.completed_traces: Dict[str, TraceData] = {}
        self.trace_buffer: deque = deque(maxlen=10000)
        
        # OpenTelemetry setup
        self.tracer_provider = None
        self.tracer = None
        
        if OPENTELEMETRY_AVAILABLE:
            self._setup_opentelemetry()
        else:
            self._setup_fallback_tracer()
        
        # Background tasks
        self.running = False
        self.background_tasks: List[asyncio.Task] = []
        
        logger.info("Distributed tracer initialized", service_name=service_name)
    
    def _setup_opentelemetry(self):
        """Setup OpenTelemetry tracing"""
        try:
            # Create resource
            resource = Resource.create({
                "service.name": self.service_name,
                "service.version": "1.0.0",
                "deployment.environment": self.config.get('environment', 'development')
            })
            
            # Setup tracer provider
            self.tracer_provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(self.tracer_provider)
            
            # Setup exporters
            exporters = []
            
            # Console exporter for development
            if self.config.get('console_export', True):
                exporters.append(ConsoleSpanExporter())
            
            # Jaeger exporter
            jaeger_endpoint = self.config.get('jaeger_endpoint')
            if jaeger_endpoint:
                jaeger_exporter = JaegerExporter(
                    agent_host_name=jaeger_endpoint.split(':')[0],
                    agent_port=int(jaeger_endpoint.split(':')[1]) if ':' in jaeger_endpoint else 14268,
                )
                exporters.append(jaeger_exporter)
            
            # OTLP exporter
            otlp_endpoint = self.config.get('otlp_endpoint')
            if otlp_endpoint:
                otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
                exporters.append(otlp_exporter)
            
            # Add span processors
            for exporter in exporters:
                span_processor = BatchSpanProcessor(exporter)
                self.tracer_provider.add_span_processor(span_processor)
            
            # Get tracer
            self.tracer = trace.get_tracer(__name__)
            
            # Setup propagation
            set_global_textmap(B3MultiFormat())
            
            # Auto-instrument common libraries
            RequestsInstrumentor().instrument()
            AioHttpClientInstrumentor().instrument()
            AsyncioInstrumentor().instrument()
            
            logger.info("OpenTelemetry tracing setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup OpenTelemetry: {e}")
            self._setup_fallback_tracer()
    
    def _setup_fallback_tracer(self):
        """Setup fallback tracer when OpenTelemetry is not available"""
        logger.info("Using fallback tracer implementation")
        self.tracer = self  # Use self as tracer for fallback methods
    
    def start_span(self, operation_name: str, parent_context: Optional[SpanContext] = None,
                   kind: SpanKind = SpanKind.INTERNAL, tags: Optional[Dict[str, Any]] = None) -> str:
        """Start a new span"""
        # Check sampling decision
        context = {'tags': tags} if tags else {}
        if not self.trace_sampler.should_sample(self.service_name, operation_name, context):
            return ""  # Return empty span ID for non-sampled traces
        
        # Generate IDs
        span_id = f"span_{uuid.uuid4().hex[:16]}"
        trace_id = parent_context.trace_id if parent_context else f"trace_{uuid.uuid4().hex[:32]}"
        parent_span_id = parent_context.span_id if parent_context else None
        
        # Create span data
        span_data = SpanData(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            service_name=self.service_name,
            start_time=time.time(),
            kind=kind,
            tags=tags or {},
            resource={
                'service.name': self.service_name,
                'service.version': '1.0.0'
            }
        )
        
        # Store active span
        self.active_spans[span_id] = span_data
        
        # If using OpenTelemetry, also create OTel span
        if OPENTELEMETRY_AVAILABLE and self.tracer and hasattr(self.tracer, 'start_span'):
            try:
                otel_span = self.tracer.start_span(operation_name)
                if tags:
                    for key, value in tags.items():
                        otel_span.set_attribute(key, str(value))
                span_data.tags['otel_span'] = otel_span
            except Exception as e:
                logger.warning(f"Failed to create OpenTelemetry span: {e}")
        
        logger.debug("Started span", span_id=span_id, trace_id=trace_id, operation=operation_name)
        return span_id
    
    def finish_span(self, span_id: str, status: Optional[TraceStatus] = None, 
                   tags: Optional[Dict[str, Any]] = None):
        """Finish a span"""
        if not span_id or span_id not in self.active_spans:
            return
        
        span_data = self.active_spans.pop(span_id)
        span_data.finish(status)
        
        # Add final tags
        if tags:
            span_data.tags.update(tags)
        
        # Finish OpenTelemetry span if present
        otel_span = span_data.tags.get('otel_span')
        if otel_span:
            try:
                if status == TraceStatus.ERROR:
                    otel_span.set_status(Status(StatusCode.ERROR))
                else:
                    otel_span.set_status(Status(StatusCode.OK))
                otel_span.end()
            except Exception as e:
                logger.warning(f"Failed to finish OpenTelemetry span: {e}")
        
        # Update performance metrics
        self.performance_analyzer.update_metrics(span_data)
        
        # Add to trace buffer
        self.trace_buffer.append(span_data)
        
        # Try to complete trace
        self._try_complete_trace(span_data.trace_id)
        
        logger.debug("Finished span", span_id=span_id, duration=span_data.duration)
    
    def add_span_event(self, span_id: str, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add an event to a span"""
        if span_id in self.active_spans:
            event = {
                'name': name,
                'timestamp': time.time(),
                'attributes': attributes or {}
            }
            self.active_spans[span_id].events.append(event)
    
    def add_span_log(self, span_id: str, message: str, level: str = "INFO", 
                    fields: Optional[Dict[str, Any]] = None):
        """Add a log entry to a span"""
        if span_id in self.active_spans:
            log_entry = {
                'timestamp': time.time(),
                'message': message,
                'level': level,
                'fields': fields or {}
            }
            self.active_spans[span_id].logs.append(log_entry)
    
    def set_span_tag(self, span_id: str, key: str, value: Any):
        """Set a tag on a span"""
        if span_id in self.active_spans:
            self.active_spans[span_id].tags[key] = value
            
            # Also set on OpenTelemetry span if present
            otel_span = self.active_spans[span_id].tags.get('otel_span')
            if otel_span:
                try:
                    otel_span.set_attribute(key, str(value))
                except Exception as e:
                    logger.warning(f"Failed to set OpenTelemetry attribute: {e}")
    
    def _try_complete_trace(self, trace_id: str):
        """Try to complete a trace when all spans are finished"""
        # Collect all spans for this trace from buffer
        trace_spans = [span for span in self.trace_buffer if span.trace_id == trace_id]
        
        # Check if we have any active spans for this trace
        active_spans_for_trace = [span for span in self.active_spans.values() 
                                if span.trace_id == trace_id]
        
        # If no active spans, the trace is complete
        if not active_spans_for_trace and trace_spans:
            start_time = min(span.start_time for span in trace_spans)
            trace_data = TraceData(trace_id=trace_id, spans=trace_spans, start_time=start_time)
            self.completed_traces[trace_id] = trace_data
            
            # Analyze the completed trace
            analysis = self.performance_analyzer.analyze_trace(trace_data)
            
            logger.info("Trace completed", 
                       trace_id=trace_id, 
                       duration=trace_data.duration,
                       span_count=len(trace_spans),
                       service_count=trace_data.service_count,
                       error_count=trace_data.error_count)
            
            # Remove spans from buffer to save memory
            self.trace_buffer = deque([span for span in self.trace_buffer 
                                     if span.trace_id != trace_id], 
                                    maxlen=self.trace_buffer.maxlen)
    
    async def start(self):
        """Start the distributed tracing system"""
        if self.running:
            return
        
        self.running = True
        
        # Start background tasks
        self.background_tasks = [
            asyncio.create_task(self._trace_cleanup_loop()),
            asyncio.create_task(self._adaptive_sampling_loop()),
            asyncio.create_task(self._performance_analysis_loop())
        ]
        
        logger.info("Distributed tracing system started")
    
    async def stop(self):
        """Stop the distributed tracing system"""
        if not self.running:
            return
        
        self.running = False
        
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        # Shutdown OpenTelemetry
        if self.tracer_provider:
            try:
                self.tracer_provider.shutdown()
            except Exception as e:
                logger.warning(f"Error shutting down tracer provider: {e}")
        
        logger.info("Distributed tracing system stopped")
    
    async def _trace_cleanup_loop(self):
        """Background task to cleanup old traces"""
        while self.running:
            try:
                cutoff_time = time.time() - 3600  # Keep traces for 1 hour
                
                # Remove old completed traces
                old_traces = [trace_id for trace_id, trace in self.completed_traces.items()
                            if trace.start_time < cutoff_time]
                
                for trace_id in old_traces:
                    del self.completed_traces[trace_id]
                
                if old_traces:
                    logger.debug(f"Cleaned up {len(old_traces)} old traces")
                
                await asyncio.sleep(300)  # Run every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in trace cleanup loop: {e}")
                await asyncio.sleep(300)
    
    async def _adaptive_sampling_loop(self):
        """Background task for adaptive sampling"""
        while self.running:
            try:
                # Get performance data
                service_data = self.performance_analyzer.get_service_performance_summary()
                
                # Adapt sampling rates
                self.trace_sampler.adapt_sampling_rates({'services': service_data})
                
                await asyncio.sleep(60)  # Run every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in adaptive sampling loop: {e}")
                await asyncio.sleep(60)
    
    async def _performance_analysis_loop(self):
        """Background task for performance analysis"""
        while self.running:
            try:
                # Analyze recent traces
                recent_traces = [trace for trace in self.completed_traces.values()
                               if trace.start_time > time.time() - 300]  # Last 5 minutes
                
                if recent_traces:
                    # Calculate aggregate metrics
                    total_traces = len(recent_traces)
                    avg_duration = sum(trace.duration for trace in recent_traces if trace.duration) / total_traces
                    error_rate = sum(trace.error_count for trace in recent_traces) / total_traces
                    
                    logger.info("Performance analysis",
                              total_traces=total_traces,
                              avg_duration=avg_duration,
                              error_rate=error_rate)
                
                await asyncio.sleep(300)  # Run every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in performance analysis loop: {e}")
                await asyncio.sleep(300)
    
    def get_trace_data(self, trace_id: str) -> Optional[TraceData]:
        """Get complete trace data"""
        return self.completed_traces.get(trace_id)
    
    def get_active_spans(self) -> Dict[str, SpanData]:
        """Get all active spans"""
        return self.active_spans.copy()
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        return {
            'services': self.performance_analyzer.get_service_performance_summary(),
            'operations': self.performance_analyzer.get_operation_performance_summary(),
            'sampling_rates': {
                'default': self.trace_sampler.default_rate,
                'services': self.trace_sampler.service_rates,
                'operations': dict(self.trace_sampler.operation_rates)
            },
            'trace_counts': {
                'active_spans': len(self.active_spans),
                'completed_traces': len(self.completed_traces),
                'buffer_size': len(self.trace_buffer)
            }
        }

# Context manager for easy span management
class TracingContext:
    """Context manager for distributed tracing"""
    
    def __init__(self, tracer: DistributedTracer, operation_name: str,
                 parent_context: Optional[SpanContext] = None,
                 kind: SpanKind = SpanKind.INTERNAL,
                 tags: Optional[Dict[str, Any]] = None):
        self.tracer = tracer
        self.operation_name = operation_name
        self.parent_context = parent_context
        self.kind = kind
        self.tags = tags or {}
        self.span_id: Optional[str] = None
    
    def __enter__(self) -> 'TracingContext':
        self.span_id = self.tracer.start_span(
            self.operation_name,
            self.parent_context,
            self.kind,
            self.tags
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.span_id:
            status = TraceStatus.ERROR if exc_type else TraceStatus.OK
            self.tracer.finish_span(self.span_id, status)
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add an event to the span"""
        if self.span_id:
            self.tracer.add_span_event(self.span_id, name, attributes)
    
    def add_log(self, message: str, level: str = "INFO", fields: Optional[Dict[str, Any]] = None):
        """Add a log to the span"""
        if self.span_id:
            self.tracer.add_span_log(self.span_id, message, level, fields)
    
    def set_tag(self, key: str, value: Any):
        """Set a tag on the span"""
        if self.span_id:
            self.tracer.set_span_tag(self.span_id, key, value)

# Global tracer instance
_global_tracer: Optional[DistributedTracer] = None

def initialize_tracing(service_name: str, config: Optional[Dict[str, Any]] = None) -> DistributedTracer:
    """Initialize global distributed tracing"""
    global _global_tracer
    _global_tracer = DistributedTracer(service_name, config)
    return _global_tracer

def get_tracer() -> Optional[DistributedTracer]:
    """Get global tracer instance"""
    return _global_tracer

def trace_operation(operation_name: str, kind: SpanKind = SpanKind.INTERNAL,
                   tags: Optional[Dict[str, Any]] = None):
    """Decorator for tracing operations"""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                tracer = get_tracer()
                if not tracer:
                    return await func(*args, **kwargs)
                
                with TracingContext(tracer, operation_name, kind=kind, tags=tags) as ctx:
                    try:
                        result = await func(*args, **kwargs)
                        ctx.set_tag("success", True)
                        return result
                    except Exception as e:
                        ctx.set_tag("error", True)
                        ctx.set_tag("error.message", str(e))
                        ctx.add_log(f"Error in {operation_name}: {e}", "ERROR")
                        raise
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                tracer = get_tracer()
                if not tracer:
                    return func(*args, **kwargs)
                
                with TracingContext(tracer, operation_name, kind=kind, tags=tags) as ctx:
                    try:
                        result = func(*args, **kwargs)
                        ctx.set_tag("success", True)
                        return result
                    except Exception as e:
                        ctx.set_tag("error", True)
                        ctx.set_tag("error.message", str(e))
                        ctx.add_log(f"Error in {operation_name}: {e}", "ERROR")
                        raise
            return sync_wrapper
    return decorator

async def main():
    """Main function for testing the distributed tracing system"""
    # Initialize tracing
    config = {
        'default_sampling_rate': 1.0,  # Sample everything for testing
        'console_export': True,
        'environment': 'development'
    }
    
    tracer = initialize_tracing("trading-system-test", config)
    
    try:
        await tracer.start()
        
        # Simulate some traced operations
        @trace_operation("process_order", SpanKind.SERVER, {"component": "order_service"})
        async def process_order(order_id: str):
            await asyncio.sleep(0.1)  # Simulate processing
            
            @trace_operation("validate_order", SpanKind.INTERNAL)
            async def validate_order():
                await asyncio.sleep(0.05)
                return True
            
            @trace_operation("save_order", SpanKind.INTERNAL)
            async def save_order():
                await asyncio.sleep(0.03)
                return "saved"
            
            valid = await validate_order()
            if valid:
                result = await save_order()
                return f"Order {order_id} processed: {result}"
            return f"Order {order_id} invalid"
        
        # Process some test orders
        tasks = []
        for i in range(5):
            task = asyncio.create_task(process_order(f"order_{i}"))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Wait a bit for traces to complete
        await asyncio.sleep(1)
        
        # Print performance summary
        summary = tracer.get_performance_summary()
        print("\\nPerformance Summary:")
        print(json.dumps(summary, indent=2, default=str))
        
        # Print completed traces
        print(f"\\nCompleted traces: {len(tracer.completed_traces)}")
        for trace_id, trace in tracer.completed_traces.items():
            analysis = tracer.performance_analyzer.analyze_trace(trace)
            print(f"Trace {trace_id}: {analysis['total_duration']:.3f}s, {analysis['span_count']} spans")
        
    finally:
        await tracer.stop()

if __name__ == "__main__":
    asyncio.run(main())