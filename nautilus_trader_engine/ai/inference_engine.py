"""
Real-Time Inference Engine
Sub-millisecond ML model inference for trading systems
"""

import asyncio
import time
import threading
import multiprocessing
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Callable
from enum import Enum
from collections import deque
import logging
import numpy as np
import ctypes
from concurrent.futures import ThreadPoolExecutor
import queue

from .model_manager import ModelManager, ModelInterface
from ..core.caching.cache_manager import CacheManager
from ..core.messaging.message_bus import MessageBus

class InferencePriority(Enum):
    """Priority levels for inference requests"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
    ULTRA_HIGH = 5  # For sub-millisecond requirements


class InferenceMode(Enum):
    """Inference execution modes"""
    SYNC = "sync"           # Synchronous execution
    ASYNC = "async"         # Asynchronous execution
    BATCH = "batch"         # Batch processing
    STREAMING = "streaming" # Streaming inference
    ZERO_COPY = "zero_copy" # Zero-copy inference


class ModelOptimization(Enum):
    """Model optimization techniques"""
    NONE = "none"
    QUANTIZATION = "quantization"
    PRUNING = "pruning"
    DISTILLATION = "distillation"
    TENSORRT = "tensorrt"
    ONNX = "onnx"


class InferenceStatus(Enum):
    """Status of inference requests"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class InferenceRequest:
    """Request for model inference"""
    request_id: str
    model_id: str
    input_data: Any
    priority: InferencePriority = InferencePriority.NORMAL
    timeout_ms: float = 1000.0
    callback: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Enhanced inference options
    mode: InferenceMode = InferenceMode.SYNC
    optimization: ModelOptimization = ModelOptimization.NONE
    use_cache: bool = True
    batch_compatible: bool = True
    max_latency_ms: float = 100.0  # SLA requirement
    
    # Memory management
    input_buffer: Optional[Any] = None  # Pre-allocated buffer
    output_buffer: Optional[Any] = None  # Pre-allocated buffer
    zero_copy: bool = False
    
    # Timing information
    created_at: float = field(default_factory=time.time_ns)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    # Performance tracking
    queue_entry_time: Optional[float] = None
    processing_start_time: Optional[float] = None
    
    def get_age_ns(self) -> float:
        """Get age of request in nanoseconds"""
        return time.time_ns() - self.created_at
    
    def get_age_ms(self) -> float:
        """Get age of request in milliseconds"""
        return self.get_age_ns() / 1_000_000
    
    def is_expired(self) -> bool:
        """Check if request has expired"""
        return self.get_age_ms() > self.timeout_ms
    
    def is_ultra_low_latency(self) -> bool:
        """Check if this is an ultra-low latency request"""
        return (self.priority == InferencePriority.ULTRA_HIGH or 
                self.max_latency_ms <= 1.0)


@dataclass
class InferenceResponse:
    """Response from model inference"""
    request_id: str
    model_id: str
    status: InferenceStatus
    prediction: Optional[Any] = None
    probabilities: Optional[Any] = None
    confidence: Optional[float] = None
    error_message: Optional[str] = None
    
    # Enhanced timing information (nanosecond precision)
    processing_time_ns: float = 0.0
    queue_time_ns: float = 0.0
    total_time_ns: float = 0.0
    model_load_time_ns: float = 0.0
    serialization_time_ns: float = 0.0
    
    # Backward compatibility (milliseconds)
    processing_time_ms: float = 0.0
    queue_time_ms: float = 0.0
    total_time_ms: float = 0.0
    
    # Model information
    model_version: Optional[str] = None
    feature_importance: Optional[Dict[str, float]] = None
    optimization_used: ModelOptimization = ModelOptimization.NONE
    
    # Performance metrics
    cache_hit: bool = False
    batch_size: int = 1
    worker_id: Optional[str] = None
    cpu_core: Optional[int] = None
    memory_usage_bytes: int = 0
    
    # Quality metrics
    prediction_entropy: Optional[float] = None
    model_uncertainty: Optional[float] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Convert nanoseconds to milliseconds for backward compatibility"""
        if self.processing_time_ns > 0:
            self.processing_time_ms = self.processing_time_ns / 1_000_000
        if self.queue_time_ns > 0:
            self.queue_time_ms = self.queue_time_ns / 1_000_000
        if self.total_time_ns > 0:
            self.total_time_ms = self.total_time_ns / 1_000_000


class UltraLowLatencyModelWrapper:
    """
    Ultra-low latency model wrapper with optimizations
    
    Features:
    - Pre-allocated memory buffers
    - Zero-copy operations
    - CPU affinity optimization
    - Model quantization support
    - Batch processing optimization
    """
    
    def __init__(self, 
                 model: ModelInterface, 
                 model_id: str,
                 optimization: ModelOptimization = ModelOptimization.NONE,
                 cpu_core: Optional[int] = None):
        
        self.model = model
        self.model_id = model_id
        self.optimization = optimization
        self.cpu_core = cpu_core
        
        # Pre-allocated buffers
        self._input_buffer = None
        self._output_buffer = None
        self._batch_buffer = None
        
        # Performance tracking
        self._prediction_count = 0
        self._total_inference_time_ns = 0
        self._last_used = time.time_ns()
        
        # Thread-local storage for zero-copy operations
        self._thread_local = threading.local()
        
        # Initialize optimizations
        self._initialize_optimizations()
    
    def _initialize_optimizations(self):
        """Initialize model optimizations"""
        try:
            if self.optimization == ModelOptimization.QUANTIZATION:
                self._apply_quantization()
            elif self.optimization == ModelOptimization.PRUNING:
                self._apply_pruning()
            elif self.optimization == ModelOptimization.ONNX:
                self._convert_to_onnx()
        except Exception as e:
            logging.warning(f"Failed to apply optimization {self.optimization}: {e}")
    
    def _apply_quantization(self):
        """Apply model quantization for faster inference"""
        # Placeholder for quantization logic
        # In practice, this would use framework-specific quantization
        pass
    
    def _apply_pruning(self):
        """Apply model pruning to reduce size"""
        # Placeholder for pruning logic
        pass
    
    def _convert_to_onnx(self):
        """Convert model to ONNX for optimization"""
        # Placeholder for ONNX conversion
        pass
    
    def predict_ultra_fast(self, input_data: Any, use_zero_copy: bool = False) -> Any:
        """Ultra-fast prediction with sub-millisecond target"""
        start_time = time.time_ns()
        
        try:
            # Set CPU affinity if specified
            if self.cpu_core is not None:
                self._set_cpu_affinity()
            
            # Use pre-allocated buffers if available
            if use_zero_copy and self._input_buffer is not None:
                processed_input = self._copy_to_buffer(input_data)
            else:
                processed_input = input_data
            
            # Make prediction
            prediction = self.model.predict(processed_input)
            
            # Update metrics
            inference_time = time.time_ns() - start_time
            self._prediction_count += 1
            self._total_inference_time_ns += inference_time
            self._last_used = time.time_ns()
            
            return prediction
            
        except Exception as e:
            logging.error(f"Ultra-fast prediction failed: {e}")
            raise
    
    def predict_batch_optimized(self, batch_data: List[Any]) -> List[Any]:
        """Batch prediction with optimization"""
        if not batch_data:
            return []
        
        start_time = time.time_ns()
        
        try:
            # Convert to numpy array for batch processing
            if hasattr(self.model, 'predict_batch'):
                # Use native batch prediction if available
                predictions = self.model.predict_batch(batch_data)
            else:
                # Fallback to individual predictions
                predictions = [self.model.predict(data) for data in batch_data]
            
            # Update metrics
            inference_time = time.time_ns() - start_time
            self._prediction_count += len(batch_data)
            self._total_inference_time_ns += inference_time
            self._last_used = time.time_ns()
            
            return predictions
            
        except Exception as e:
            logging.error(f"Batch prediction failed: {e}")
            raise
    
    def _set_cpu_affinity(self):
        """Set CPU affinity for current thread"""
        try:
            import os
            if hasattr(os, 'sched_setaffinity'):
                os.sched_setaffinity(0, {self.cpu_core})
        except Exception as e:
            logging.warning(f"Failed to set CPU affinity: {e}")
    
    def _copy_to_buffer(self, input_data: Any) -> Any:
        """Copy input data to pre-allocated buffer"""
        # Simplified implementation
        return input_data
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        avg_time_ns = (self._total_inference_time_ns / self._prediction_count 
                      if self._prediction_count > 0 else 0)
        
        return {
            'model_id': self.model_id,
            'prediction_count': self._prediction_count,
            'avg_inference_time_ns': avg_time_ns,
            'avg_inference_time_ms': avg_time_ns / 1_000_000,
            'total_inference_time_ns': self._total_inference_time_ns,
            'last_used': self._last_used,
            'optimization': self.optimization.value,
            'cpu_core': self.cpu_core
        }
    
    def warm_up(self, sample_input: Any, iterations: int = 100):
        """Warm up model with sample predictions"""
        for _ in range(iterations):
            try:
                self.predict_ultra_fast(sample_input)
            except Exception:
                pass  # Ignore warm-up errors


class InferenceEngine:
    """
    Ultra-high-performance real-time inference engine
    
    Features:
    - Sub-millisecond inference latency (target: <100μs)
    - Priority-based request queuing with ultra-high priority
    - Zero-copy operations for minimal memory overhead
    - CPU affinity optimization
    - Model optimization (quantization, pruning, ONNX)
    - Batch processing with intelligent batching
    - Advanced caching with prediction result caching
    - Real-time performance monitoring
    - Load balancing across optimized model instances
    """
    
    def __init__(self, 
                 model_manager: ModelManager,
                 cache_manager: Optional[CacheManager] = None,
                 message_bus: Optional[MessageBus] = None,
                 max_queue_size: int = 10000,
                 batch_size: int = 32,
                 batch_timeout_ms: float = 1.0,  # Reduced for lower latency
                 worker_threads: int = 8,  # Increased for better parallelism
                 ultra_low_latency_workers: int = 2,  # Dedicated ULL workers
                 enable_batching: bool = True,
                 enable_caching: bool = True,
                 enable_zero_copy: bool = True,
                 enable_cpu_affinity: bool = True,
                 target_latency_ns: int = 100_000):  # 100μs target
        
        self.model_manager = model_manager
        self.cache_manager = cache_manager
        self.message_bus = message_bus
        self.max_queue_size = max_queue_size
        self.batch_size = batch_size
        self.batch_timeout_ms = batch_timeout_ms
        self.worker_threads = worker_threads
        self.ultra_low_latency_workers = ultra_low_latency_workers
        self.enable_batching = enable_batching
        self.enable_caching = enable_caching
        self.enable_zero_copy = enable_zero_copy
        self.enable_cpu_affinity = enable_cpu_affinity
        self.target_latency_ns = target_latency_ns
        
        # Request queues by priority (lock-free for ultra-low latency)
        self._request_queues = {
            priority: asyncio.Queue(maxsize=max_queue_size) 
            for priority in InferencePriority
        }
        
        # Ultra-low latency queue (separate for sub-millisecond requests)
        self._ull_queue = queue.Queue(maxsize=1000)  # Thread-safe queue
        
        # Response tracking
        self._pending_responses: Dict[str, asyncio.Future] = {}
        
        # Enhanced model cache with optimization
        self._model_cache: Dict[str, UltraLowLatencyModelWrapper] = {}
        self._model_warm_up: Dict[str, bool] = {}
        self._model_load_times: Dict[str, float] = {}
        
        # CPU affinity management
        self._cpu_cores = list(range(multiprocessing.cpu_count()))
        self._worker_cpu_assignments: Dict[str, int] = {}
        
        # Batch processing
        self._batch_queue: deque = deque()
        self._batch_lock = threading.Lock()
        
        # Enhanced result caching
        self._result_cache: Dict[str, InferenceResponse] = {}
        self._cache_lock = threading.Lock()
        self._cache_stats = {'hits': 0, 'misses': 0, 'evictions': 0}
        
        # Thread pools for different priority levels
        self._ull_executor = ThreadPoolExecutor(
            max_workers=ultra_low_latency_workers,
            thread_name_prefix="ull-inference"
        )
        self._standard_executor = ThreadPoolExecutor(
            max_workers=worker_threads,
            thread_name_prefix="std-inference"
        )
        
        # Background tasks
        self._worker_tasks: List[asyncio.Task] = []
        self._ull_worker_tasks: List[asyncio.Task] = []
        self._batch_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Enhanced performance metrics
        self._metrics = {
            'requests_processed': 0,
            'requests_failed': 0,
            'ull_requests_processed': 0,
            'ull_requests_under_target': 0,
            'total_processing_time_ns': 0,
            'avg_processing_time_ns': 0,
            'avg_processing_time_ms': 0.0,
            'min_processing_time_ns': float('inf'),
            'max_processing_time_ns': 0,
            'p95_processing_time_ns': 0,
            'p99_processing_time_ns': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'batch_count': 0,
            'timeout_count': 0,
            'zero_copy_operations': 0,
            'cpu_affinity_optimizations': 0
        }
        
        # Latency tracking for percentiles
        self._latency_samples = deque(maxlen=10000)
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start the ultra-high-performance inference engine"""
        if self._running:
            return
        
        self._running = True
        
        # Start ultra-low latency workers (dedicated threads)
        for i in range(self.ultra_low_latency_workers):
            cpu_core = self._cpu_cores[i % len(self._cpu_cores)] if self.enable_cpu_affinity else None
            task = asyncio.create_task(self._ull_worker(f"ull-worker-{i}", cpu_core))
            self._ull_worker_tasks.append(task)
        
        # Start standard worker tasks
        for i in range(self.worker_threads):
            cpu_core = (self._cpu_cores[(i + self.ultra_low_latency_workers) % len(self._cpu_cores)] 
                       if self.enable_cpu_affinity else None)
            task = asyncio.create_task(self._worker(f"worker-{i}", cpu_core))
            self._worker_tasks.append(task)
        
        # Start batch processing task
        if self.enable_batching:
            self._batch_task = asyncio.create_task(self._batch_processor())
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_worker())
        
        # Start monitoring task
        self._monitoring_task = asyncio.create_task(self._monitoring_worker())
        
        # Initialize cache integration
        if self.cache_manager:
            await self._initialize_cache_integration()
        
        # Warm up models with optimization
        await self._warm_up_models_optimized()
        
        self.logger.info(f"Ultra-high-performance InferenceEngine started: "
                        f"{self.ultra_low_latency_workers} ULL workers, "
                        f"{self.worker_threads} standard workers, "
                        f"target latency: {self.target_latency_ns/1000:.1f}μs")
    
    async def _ull_worker(self, worker_name: str, cpu_core: Optional[int] = None):
        """Ultra-low latency worker for sub-millisecond inference"""
        self.logger.debug(f"ULL Worker {worker_name} started on CPU core {cpu_core}")
        
        # Set CPU affinity if specified
        if cpu_core is not None and self.enable_cpu_affinity:
            self._worker_cpu_assignments[worker_name] = cpu_core
            try:
                import os
                if hasattr(os, 'sched_setaffinity'):
                    os.sched_setaffinity(0, {cpu_core})
            except Exception as e:
                self.logger.warning(f"Failed to set CPU affinity for {worker_name}: {e}")
        
        while self._running:
            try:
                # Check ultra-high priority queue first
                request = await self._get_ull_request()
                
                if request is None:
                    await asyncio.sleep(0.0001)  # 100μs sleep
                    continue
                
                # Process with ultra-low latency optimizations
                await self._process_ull_request(request, worker_name, cpu_core)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"ULL Worker {worker_name} error: {e}")
                await asyncio.sleep(0.001)
        
        self.logger.debug(f"ULL Worker {worker_name} stopped")
    
    async def _get_ull_request(self) -> Optional[InferenceRequest]:
        """Get ultra-low latency request"""
        # Check ultra-high priority queue
        try:
            queue = self._request_queues[InferencePriority.ULTRA_HIGH]
            return queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
        
        # Check critical priority queue
        try:
            queue = self._request_queues[InferencePriority.CRITICAL]
            request = queue.get_nowait()
            if request.is_ultra_low_latency():
                return request
            else:
                # Put back if not ULL
                await queue.put(request)
        except asyncio.QueueEmpty:
            pass
        
        return None
    
    async def _process_ull_request(self, request: InferenceRequest, worker_name: str, cpu_core: Optional[int]):
        """Process ultra-low latency request with optimizations"""
        start_time = time.time_ns()
        request.started_at = start_time
        request.processing_start_time = start_time
        
        try:
            # Get optimized model instance
            model_wrapper = await self._get_ull_model_instance(request.model_id)
            
            if model_wrapper is None:
                await self._complete_request(request, InferenceResponse(
                    request_id=request.request_id,
                    model_id=request.model_id,
                    status=InferenceStatus.FAILED,
                    error_message=f"ULL Model {request.model_id} not available",
                    queue_time_ns=start_time - request.created_at,
                    worker_id=worker_name
                ))
                return
            
            # Ultra-fast prediction
            prediction_start = time.time_ns()
            
            if request.zero_copy and self.enable_zero_copy:
                prediction = model_wrapper.predict_ultra_fast(request.input_data, use_zero_copy=True)
                self._metrics['zero_copy_operations'] += 1
            else:
                prediction = model_wrapper.predict_ultra_fast(request.input_data)
            
            processing_time_ns = time.time_ns() - prediction_start
            
            # Get probabilities if available (skip for ultra-low latency if too slow)
            probabilities = None
            if processing_time_ns < self.target_latency_ns / 2:  # Only if we have time budget
                try:
                    probabilities = model_wrapper.model.predict_proba(request.input_data)
                except (NotImplementedError, AttributeError):
                    pass
            
            # Calculate confidence quickly
            confidence = None
            if probabilities is not None:
                if hasattr(probabilities, 'max'):
                    confidence = float(probabilities.max())
            
            total_time_ns = time.time_ns() - request.created_at
            
            # Create response
            response = InferenceResponse(
                request_id=request.request_id,
                model_id=request.model_id,
                status=InferenceStatus.COMPLETED,
                prediction=prediction.tolist() if hasattr(prediction, 'tolist') else prediction,
                probabilities=probabilities.tolist() if probabilities is not None and hasattr(probabilities, 'tolist') else probabilities,
                confidence=confidence,
                processing_time_ns=processing_time_ns,
                queue_time_ns=start_time - request.created_at,
                total_time_ns=total_time_ns,
                optimization_used=model_wrapper.optimization,
                worker_id=worker_name,
                cpu_core=cpu_core
            )
            
            await self._complete_request(request, response)
            
            # Update ULL metrics
            self._metrics['ull_requests_processed'] += 1
            if total_time_ns <= self.target_latency_ns:
                self._metrics['ull_requests_under_target'] += 1
            
            # Track latency for percentiles
            self._latency_samples.append(total_time_ns)
            
            # Update general metrics
            self._update_processing_metrics(processing_time_ns)
            
        except Exception as e:
            # Handle processing error
            error_response = InferenceResponse(
                request_id=request.request_id,
                model_id=request.model_id,
                status=InferenceStatus.FAILED,
                error_message=str(e),
                queue_time_ns=start_time - request.created_at,
                total_time_ns=time.time_ns() - request.created_at,
                worker_id=worker_name
            )
            
            await self._complete_request(request, error_response)
            
            self._metrics['requests_failed'] += 1
            self.logger.error(f"ULL Request {request.request_id} failed: {e}")
    
    async def _get_ull_model_instance(self, model_id: str) -> Optional[UltraLowLatencyModelWrapper]:
        """Get ultra-low latency optimized model instance"""
        if model_id in self._model_cache:
            return self._model_cache[model_id]
        
        # Try to create optimized wrapper
        try:
            # Get base model from model manager
            base_model = None  # This would be loaded from model manager
            
            # For now, return None - in practice, this would load and optimize the model
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get ULL model {model_id}: {e}")
            return None
    
    def _update_processing_metrics(self, processing_time_ns: float):
        """Update processing time metrics"""
        self._metrics['requests_processed'] += 1
        self._metrics['total_processing_time_ns'] += processing_time_ns
        self._metrics['avg_processing_time_ns'] = (
            self._metrics['total_processing_time_ns'] / self._metrics['requests_processed']
        )
        self._metrics['avg_processing_time_ms'] = self._metrics['avg_processing_time_ns'] / 1_000_000
        
        # Update min/max
        self._metrics['min_processing_time_ns'] = min(
            self._metrics['min_processing_time_ns'], processing_time_ns
        )
        self._metrics['max_processing_time_ns'] = max(
            self._metrics['max_processing_time_ns'], processing_time_ns
        )
        
        # Update percentiles periodically
        if len(self._latency_samples) >= 100:
            self._update_latency_percentiles()
    
    def _update_latency_percentiles(self):
        """Update latency percentile metrics"""
        if not self._latency_samples:
            return
        
        sorted_samples = sorted(self._latency_samples)
        n = len(sorted_samples)
        
        self._metrics['p95_processing_time_ns'] = sorted_samples[int(0.95 * n)]
        self._metrics['p99_processing_time_ns'] = sorted_samples[int(0.99 * n)]
    
    async def _initialize_cache_integration(self):
        """Initialize integration with cache manager"""
        if not self.cache_manager:
            return
        
        try:
            # Set up cache for prediction results
            await self.cache_manager.start()
            self.logger.info("Cache integration initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize cache integration: {e}")
    
    async def _warm_up_models_optimized(self):
        """Warm up models with optimization"""
        try:
            models = await self.model_manager.list_models()
            
            for model_info in models:
                if model_info['status'] == 'deployed':
                    model_id = model_info['model_id']
                    
                    # Create optimized wrapper
                    # This is simplified - in practice would load actual model
                    self._model_warm_up[model_id] = True
                    self.logger.debug(f"Warmed up optimized model {model_id}")
            
        except Exception as e:
            self.logger.error(f"Optimized model warm-up failed: {e}")
    
    async def _monitoring_worker(self):
        """Background worker for performance monitoring"""
        while self._running:
            try:
                # Update percentiles
                self._update_latency_percentiles()
                
                # Log performance metrics periodically
                if self._metrics['requests_processed'] % 1000 == 0:
                    avg_latency_us = self._metrics['avg_processing_time_ns'] / 1000
                    ull_success_rate = (
                        (self._metrics['ull_requests_under_target'] / 
                         max(1, self._metrics['ull_requests_processed'])) * 100
                    )
                    
                    self.logger.info(f"Performance: {avg_latency_us:.1f}μs avg, "
                                   f"{ull_success_rate:.1f}% ULL success rate")
                
                await asyncio.sleep(10)  # Monitor every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Monitoring worker error: {e}")
                await asyncio.sleep(30)
    
    async def stop(self):
        """Stop the inference engine"""
        self._running = False
        
        # Cancel all tasks
        for task in self._worker_tasks:
            task.cancel()
        
        if self._batch_task:
            self._batch_task.cancel()
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Wait for tasks to complete
        all_tasks = self._worker_tasks + [self._batch_task, self._cleanup_task]
        await asyncio.gather(*[t for t in all_tasks if t], return_exceptions=True)
        
        self.logger.info("InferenceEngine stopped")
    
    async def predict(self, request: InferenceRequest) -> InferenceResponse:
        """Submit inference request and wait for response with ultra-low latency support"""
        if not self._running:
            raise RuntimeError("InferenceEngine not running")
        
        request_start = time.time_ns()
        
        # Enhanced cache check with nanosecond precision
        if self.enable_caching and request.use_cache:
            cached_response = await self._get_cached_response_enhanced(request)
            if cached_response:
                self._metrics['cache_hits'] += 1
                self._cache_stats['hits'] += 1
                
                # Update cache hit with current timing
                cached_response.total_time_ns = time.time_ns() - request_start
                cached_response.cache_hit = True
                return cached_response
            
            self._metrics['cache_misses'] += 1
            self._cache_stats['misses'] += 1
        
        # Create future for response
        response_future = asyncio.Future()
        self._pending_responses[request.request_id] = response_future
        
        try:
            # Route to appropriate queue based on latency requirements
            if request.is_ultra_low_latency():
                # Use ultra-high priority queue for sub-millisecond requests
                request.priority = InferencePriority.ULTRA_HIGH
                await self._request_queues[InferencePriority.ULTRA_HIGH].put(request)
            else:
                # Use specified priority queue
                await self._request_queues[request.priority].put(request)
            
            # Set queue entry time
            request.queue_entry_time = time.time_ns()
            
            # Wait for response with timeout
            timeout_seconds = request.timeout_ms / 1000.0
            response = await asyncio.wait_for(response_future, timeout=timeout_seconds)
            
            # Enhanced caching for successful responses
            if (self.enable_caching and request.use_cache and 
                response.status == InferenceStatus.COMPLETED):
                await self._cache_response_enhanced(request, response)
            
            # Publish metrics if message bus available
            if self.message_bus:
                await self._publish_inference_metrics(request, response)
            
            return response
            
        except asyncio.TimeoutError:
            # Handle timeout with enhanced metrics
            total_time_ns = time.time_ns() - request_start
            response = InferenceResponse(
                request_id=request.request_id,
                model_id=request.model_id,
                status=InferenceStatus.TIMEOUT,
                error_message=f"Request timed out after {request.timeout_ms}ms",
                total_time_ns=total_time_ns,
                queue_time_ns=total_time_ns  # All time was queue time
            )
            
            self._metrics['timeout_count'] += 1
            return response
            
        finally:
            # Cleanup
            self._pending_responses.pop(request.request_id, None)
    
    async def predict_ultra_fast(self, 
                               model_id: str, 
                               input_data: Any,
                               request_id: Optional[str] = None,
                               use_zero_copy: bool = True) -> InferenceResponse:
        """Ultra-fast prediction with minimal overhead (target: <100μs)"""
        if not self._running:
            raise RuntimeError("InferenceEngine not running")
        
        # Create minimal request for ultra-low latency
        request = InferenceRequest(
            request_id=request_id or f"ull_{time.time_ns()}",
            model_id=model_id,
            input_data=input_data,
            priority=InferencePriority.ULTRA_HIGH,
            timeout_ms=1.0,  # 1ms timeout
            mode=InferenceMode.ZERO_COPY if use_zero_copy else InferenceMode.SYNC,
            use_cache=False,  # Skip cache for ultra-low latency
            zero_copy=use_zero_copy,
            max_latency_ms=0.1  # 100μs target
        )
        
        return await self.predict(request)
    
    async def _get_cached_response_enhanced(self, request: InferenceRequest) -> Optional[InferenceResponse]:
        """Enhanced cache lookup with integration to cache manager"""
        if not self.enable_caching:
            return None
        
        # Try cache manager first if available
        if self.cache_manager:
            try:
                cache_key = self._create_cache_key_enhanced(request)
                cached_data = await self.cache_manager.get(cache_key)
                
                if cached_data:
                    # Deserialize cached response
                    return self._deserialize_cached_response(cached_data)
            except Exception as e:
                self.logger.debug(f"Cache manager lookup failed: {e}")
        
        # Fallback to local cache
        return self._get_cached_response(request)
    
    async def _cache_response_enhanced(self, request: InferenceRequest, response: InferenceResponse):
        """Enhanced response caching with cache manager integration"""
        if not self.enable_caching:
            return
        
        # Cache in cache manager if available
        if self.cache_manager:
            try:
                cache_key = self._create_cache_key_enhanced(request)
                cached_data = self._serialize_response_for_cache(response)
                
                # Set TTL based on model and prediction confidence
                ttl = self._calculate_cache_ttl(request, response)
                
                await self.cache_manager.set(
                    cache_key, 
                    cached_data, 
                    ttl=ttl,
                    tags=[f"model:{request.model_id}", "inference_result"]
                )
            except Exception as e:
                self.logger.debug(f"Cache manager storage failed: {e}")
        
        # Also cache locally
        self._cache_response(request, response)
    
    def _create_cache_key_enhanced(self, request: InferenceRequest) -> str:
        """Create enhanced cache key with model version and optimization info"""
        import hashlib
        
        # Include model ID, input data, and optimization settings
        key_components = [
            request.model_id,
            str(request.input_data),
            request.optimization.value,
            str(request.zero_copy)
        ]
        
        key_data = "|".join(key_components)
        return f"inference:{hashlib.sha256(key_data.encode()).hexdigest()[:16]}"
    
    def _calculate_cache_ttl(self, request: InferenceRequest, response: InferenceResponse) -> int:
        """Calculate cache TTL based on prediction confidence and model characteristics"""
        base_ttl = 300  # 5 minutes base
        
        # Adjust based on confidence
        if response.confidence:
            if response.confidence > 0.9:
                return base_ttl * 2  # High confidence, cache longer
            elif response.confidence < 0.5:
                return base_ttl // 2  # Low confidence, cache shorter
        
        return base_ttl
    
    def _serialize_response_for_cache(self, response: InferenceResponse) -> Dict[str, Any]:
        """Serialize response for caching"""
        return {
            'prediction': response.prediction,
            'probabilities': response.probabilities,
            'confidence': response.confidence,
            'model_version': response.model_version,
            'optimization_used': response.optimization_used.value,
            'cached_at': time.time_ns()
        }
    
    def _deserialize_cached_response(self, cached_data: Dict[str, Any]) -> InferenceResponse:
        """Deserialize cached response"""
        return InferenceResponse(
            request_id="cached",
            model_id="cached",
            status=InferenceStatus.COMPLETED,
            prediction=cached_data['prediction'],
            probabilities=cached_data['probabilities'],
            confidence=cached_data['confidence'],
            model_version=cached_data['model_version'],
            optimization_used=ModelOptimization(cached_data['optimization_used']),
            cache_hit=True,
            processing_time_ns=0,  # Cached response
            total_time_ns=time.time_ns() - cached_data['cached_at']
        )
    
    async def _publish_inference_metrics(self, request: InferenceRequest, response: InferenceResponse):
        """Publish inference metrics to message bus"""
        if not self.message_bus:
            return
        
        try:
            metrics_data = {
                'model_id': request.model_id,
                'processing_time_ns': response.processing_time_ns,
                'total_time_ns': response.total_time_ns,
                'queue_time_ns': response.queue_time_ns,
                'priority': request.priority.value,
                'optimization': response.optimization_used.value,
                'cache_hit': response.cache_hit,
                'status': response.status.value,
                'timestamp': time.time_ns()
            }
            
            await self.message_bus.publish(
                topic="inference.metrics",
                message=metrics_data
            )
        except Exception as e:
            self.logger.debug(f"Failed to publish metrics: {e}")
    
    async def predict_async(self, request: InferenceRequest) -> str:
        """Submit inference request asynchronously (returns request ID)"""
        if not self._running:
            raise RuntimeError("InferenceEngine not running")
        
        # Add to appropriate priority queue
        await self._request_queues[request.priority].put(request)
        
        return request.request_id
    
    async def get_result(self, request_id: str) -> Optional[InferenceResponse]:
        """Get result for async request"""
        if request_id in self._pending_responses:
            future = self._pending_responses[request_id]
            if future.done():
                return future.result()
        
        return None
    
    async def _worker(self, worker_name: str, cpu_core: Optional[int] = None):
        """Enhanced worker task for processing inference requests"""
        self.logger.debug(f"Worker {worker_name} started on CPU core {cpu_core}")
        
        # Set CPU affinity if specified
        if cpu_core is not None and self.enable_cpu_affinity:
            self._worker_cpu_assignments[worker_name] = cpu_core
            try:
                import os
                if hasattr(os, 'sched_setaffinity'):
                    os.sched_setaffinity(0, {cpu_core})
                    self._metrics['cpu_affinity_optimizations'] += 1
            except Exception as e:
                self.logger.warning(f"Failed to set CPU affinity for {worker_name}: {e}")
        
        while self._running:
            try:
                # Get request from highest priority queue (excluding ultra-high)
                request = await self._get_next_standard_request()
                
                if request is None:
                    await asyncio.sleep(0.001)  # Small delay to prevent busy waiting
                    continue
                
                # Check if request has expired
                if request.is_expired():
                    await self._complete_request(request, InferenceResponse(
                        request_id=request.request_id,
                        model_id=request.model_id,
                        status=InferenceStatus.TIMEOUT,
                        error_message="Request expired in queue",
                        queue_time_ns=(time.time_ns() - request.created_at),
                        total_time_ns=(time.time_ns() - request.created_at),
                        worker_id=worker_name
                    ))
                    continue
                
                # Process request with enhanced features
                await self._process_request_enhanced(request, worker_name, cpu_core)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Worker {worker_name} error: {e}")
                await asyncio.sleep(0.1)
        
        self.logger.debug(f"Worker {worker_name} stopped")
    
    async def _get_next_standard_request(self) -> Optional[InferenceRequest]:
        """Get next request from standard priority queues (excluding ultra-high)"""
        # Check queues in priority order (skip ultra-high as it's handled by ULL workers)
        for priority in [InferencePriority.CRITICAL, InferencePriority.HIGH, 
                        InferencePriority.NORMAL, InferencePriority.LOW]:
            
            queue = self._request_queues[priority]
            
            try:
                # Non-blocking get
                request = queue.get_nowait()
                # Skip ultra-low latency requests in standard workers
                if not request.is_ultra_low_latency():
                    return request
                else:
                    # Put back for ULL workers
                    await self._request_queues[InferencePriority.ULTRA_HIGH].put(request)
            except asyncio.QueueEmpty:
                continue
        
        return None
    
    async def _process_request_enhanced(self, request: InferenceRequest, worker_name: str, cpu_core: Optional[int]):
        """Enhanced request processing with optimization support"""
        start_time = time.time_ns()
        request.started_at = start_time
        request.processing_start_time = start_time
        
        try:
            # Get model instance (try optimized first, then standard)
            model = await self._get_model_instance_enhanced(request.model_id, request.optimization)
            
            if model is None:
                await self._complete_request(request, InferenceResponse(
                    request_id=request.request_id,
                    model_id=request.model_id,
                    status=InferenceStatus.FAILED,
                    error_message=f"Model {request.model_id} not available",
                    queue_time_ns=start_time - request.created_at,
                    total_time_ns=time.time_ns() - request.created_at,
                    worker_id=worker_name
                ))
                return
            
            # Make prediction with appropriate method
            prediction_start = time.time_ns()
            
            if isinstance(model, UltraLowLatencyModelWrapper):
                if request.mode == InferenceMode.BATCH and hasattr(request, 'batch_data'):
                    prediction = model.predict_batch_optimized(request.batch_data)
                else:
                    prediction = model.predict_ultra_fast(
                        request.input_data, 
                        use_zero_copy=request.zero_copy and self.enable_zero_copy
                    )
            else:
                prediction = model.predict(request.input_data)
            
            processing_time_ns = time.time_ns() - prediction_start
            
            # Get probabilities if available and time permits
            probabilities = None
            if processing_time_ns < request.max_latency_ms * 1_000_000 / 2:  # Half time budget
                try:
                    if isinstance(model, UltraLowLatencyModelWrapper):
                        probabilities = model.model.predict_proba(request.input_data)
                    else:
                        probabilities = model.predict_proba(request.input_data)
                except (NotImplementedError, AttributeError):
                    pass
            
            # Calculate confidence and uncertainty
            confidence = None
            uncertainty = None
            if probabilities is not None:
                if hasattr(probabilities, 'max'):
                    confidence = float(probabilities.max())
                    # Simple uncertainty measure (entropy)
                    if hasattr(probabilities, 'shape') and len(probabilities.shape) > 0:
                        probs = probabilities / probabilities.sum()
                        uncertainty = -np.sum(probs * np.log(probs + 1e-10))
            
            # Get feature importance if available and requested
            feature_importance = None
            if request.metadata.get('include_feature_importance', False):
                try:
                    if isinstance(model, UltraLowLatencyModelWrapper):
                        feature_importance = model.model.get_feature_importance()
                    else:
                        feature_importance = model.get_feature_importance()
                except Exception:
                    pass
            
            total_time_ns = time.time_ns() - request.created_at
            
            # Create enhanced response
            response = InferenceResponse(
                request_id=request.request_id,
                model_id=request.model_id,
                status=InferenceStatus.COMPLETED,
                prediction=prediction.tolist() if hasattr(prediction, 'tolist') else prediction,
                probabilities=probabilities.tolist() if probabilities is not None and hasattr(probabilities, 'tolist') else probabilities,
                confidence=confidence,
                processing_time_ns=processing_time_ns,
                queue_time_ns=start_time - request.created_at,
                total_time_ns=total_time_ns,
                feature_importance=feature_importance,
                optimization_used=request.optimization,
                worker_id=worker_name,
                cpu_core=cpu_core,
                model_uncertainty=uncertainty
            )
            
            await self._complete_request(request, response)
            
            # Update metrics
            self._update_processing_metrics(processing_time_ns)
            
        except Exception as e:
            # Handle processing error
            error_response = InferenceResponse(
                request_id=request.request_id,
                model_id=request.model_id,
                status=InferenceStatus.FAILED,
                error_message=str(e),
                queue_time_ns=start_time - request.created_at,
                total_time_ns=time.time_ns() - request.created_at,
                worker_id=worker_name
            )
            
            await self._complete_request(request, error_response)
            
            self._metrics['requests_failed'] += 1
            self.logger.error(f"Request {request.request_id} failed: {e}")
    
    async def _get_model_instance_enhanced(self, model_id: str, optimization: ModelOptimization) -> Optional[Union[ModelInterface, UltraLowLatencyModelWrapper]]:
        """Get enhanced model instance with optimization support"""
        # Try to get optimized wrapper first
        cache_key = f"{model_id}_{optimization.value}"
        
        if cache_key in self._model_cache:
            return self._model_cache[cache_key]
        
        # Try to get from model manager and create wrapper
        try:
            model_info = await self.model_manager.get_model_info(model_id)
            
            if model_info['metadata']['status'] == 'deployed':
                # This is simplified - in practice would load actual model
                # and create optimized wrapper
                return None  # Placeholder
            
        except Exception as e:
            self.logger.error(f"Failed to get enhanced model {model_id}: {e}")
        
        return None
    
    async def _get_next_request(self) -> Optional[InferenceRequest]:
        """Get next request from priority queues"""
        # Check queues in priority order
        for priority in [InferencePriority.CRITICAL, InferencePriority.HIGH, 
                        InferencePriority.NORMAL, InferencePriority.LOW]:
            
            queue = self._request_queues[priority]
            
            try:
                # Non-blocking get
                return queue.get_nowait()
            except asyncio.QueueEmpty:
                continue
        
        return None
    
    async def _process_request(self, request: InferenceRequest):
        """Process individual inference request"""
        start_time = time.time()
        request.started_at = start_time
        
        try:
            # Get model instance
            model = await self._get_model_instance(request.model_id)
            
            if model is None:
                await self._complete_request(request, InferenceResponse(
                    request_id=request.request_id,
                    model_id=request.model_id,
                    status=InferenceStatus.FAILED,
                    error_message=f"Model {request.model_id} not available",
                    queue_time_ms=(start_time - request.created_at) * 1000
                ))
                return
            
            # Make prediction
            prediction_start = time.time()
            prediction = model.predict(request.input_data)
            processing_time = (time.time() - prediction_start) * 1000
            
            # Get probabilities if available
            probabilities = None
            try:
                probabilities = model.predict_proba(request.input_data)
            except (NotImplementedError, AttributeError):
                pass
            
            # Calculate confidence (simplified)
            confidence = None
            if probabilities is not None:
                if hasattr(probabilities, 'max'):
                    confidence = float(probabilities.max())
                elif isinstance(probabilities, (list, tuple)) and len(probabilities) > 0:
                    confidence = float(max(probabilities))
            
            # Get feature importance
            feature_importance = None
            try:
                feature_importance = model.get_feature_importance()
            except Exception:
                pass
            
            # Create response
            response = InferenceResponse(
                request_id=request.request_id,
                model_id=request.model_id,
                status=InferenceStatus.COMPLETED,
                prediction=prediction.tolist() if hasattr(prediction, 'tolist') else prediction,
                probabilities=probabilities.tolist() if probabilities is not None and hasattr(probabilities, 'tolist') else probabilities,
                confidence=confidence,
                processing_time_ms=processing_time,
                queue_time_ms=(start_time - request.created_at) * 1000,
                total_time_ms=(time.time() - request.created_at) * 1000,
                feature_importance=feature_importance
            )
            
            await self._complete_request(request, response)
            
            # Update metrics
            self._metrics['requests_processed'] += 1
            self._metrics['total_processing_time_ms'] += processing_time
            self._metrics['avg_processing_time_ms'] = (
                self._metrics['total_processing_time_ms'] / self._metrics['requests_processed']
            )
            
        except Exception as e:
            # Handle processing error
            error_response = InferenceResponse(
                request_id=request.request_id,
                model_id=request.model_id,
                status=InferenceStatus.FAILED,
                error_message=str(e),
                queue_time_ms=(start_time - request.created_at) * 1000,
                total_time_ms=(time.time() - request.created_at) * 1000
            )
            
            await self._complete_request(request, error_response)
            
            self._metrics['requests_failed'] += 1
            self.logger.error(f"Request {request.request_id} failed: {e}")
    
    async def _complete_request(self, request: InferenceRequest, response: InferenceResponse):
        """Complete request with response"""
        request.completed_at = time.time()
        
        # Set response future if exists
        if request.request_id in self._pending_responses:
            future = self._pending_responses[request.request_id]
            if not future.done():
                future.set_result(response)
        
        # Call callback if provided
        if request.callback:
            try:
                if asyncio.iscoroutinefunction(request.callback):
                    await request.callback(response)
                else:
                    request.callback(response)
            except Exception as e:
                self.logger.error(f"Callback error for request {request.request_id}: {e}")
    
    async def _get_model_instance(self, model_id: str) -> Optional[ModelInterface]:
        """Get cached model instance"""
        if model_id in self._model_cache:
            return self._model_cache[model_id]
        
        # Try to get from model manager
        try:
            # This is a simplified approach - in practice, you'd have a more
            # sophisticated model loading mechanism
            model_info = await self.model_manager.get_model_info(model_id)
            
            if model_info['metadata']['status'] == 'deployed':
                # Load model (simplified)
                # In practice, this would involve loading the actual model
                return None  # Placeholder
            
        except Exception as e:
            self.logger.error(f"Failed to get model {model_id}: {e}")
        
        return None
    
    async def _warm_up_models(self):
        """Warm up deployed models"""
        try:
            models = await self.model_manager.list_models()
            
            for model_info in models:
                if model_info['status'] == 'deployed':
                    model_id = model_info['model_id']
                    
                    # Warm up model (simplified)
                    self._model_warm_up[model_id] = True
                    self.logger.debug(f"Warmed up model {model_id}")
            
        except Exception as e:
            self.logger.error(f"Model warm-up failed: {e}")
    
    def _get_cached_response(self, request: InferenceRequest) -> Optional[InferenceResponse]:
        """Get cached response for request"""
        if not self.enable_caching:
            return None
        
        # Create cache key based on model and input
        cache_key = self._create_cache_key(request)
        
        with self._cache_lock:
            return self._result_cache.get(cache_key)
    
    def _cache_response(self, request: InferenceRequest, response: InferenceResponse):
        """Cache response for future use"""
        if not self.enable_caching:
            return
        
        cache_key = self._create_cache_key(request)
        
        with self._cache_lock:
            # Simple LRU-like cache management
            if len(self._result_cache) > 1000:  # Max cache size
                # Remove oldest entry
                oldest_key = next(iter(self._result_cache))
                del self._result_cache[oldest_key]
            
            self._result_cache[cache_key] = response
    
    def _create_cache_key(self, request: InferenceRequest) -> str:
        """Create cache key for request"""
        # Simple hash-based key (in practice, would be more sophisticated)
        import hashlib
        
        key_data = f"{request.model_id}_{str(request.input_data)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def _batch_processor(self):
        """Process requests in batches for efficiency"""
        while self._running:
            try:
                # Collect batch
                batch = []
                batch_start = time.time()
                
                # Wait for first request or timeout
                try:
                    first_request = await asyncio.wait_for(
                        self._get_next_request(), 
                        timeout=self.batch_timeout_ms / 1000.0
                    )
                    if first_request:
                        batch.append(first_request)
                except asyncio.TimeoutError:
                    continue
                
                # Collect additional requests up to batch size
                while len(batch) < self.batch_size:
                    try:
                        request = await asyncio.wait_for(
                            self._get_next_request(),
                            timeout=0.001  # Very short timeout
                        )
                        if request:
                            batch.append(request)
                        else:
                            break
                    except asyncio.TimeoutError:
                        break
                
                # Process batch if we have requests
                if batch:
                    await self._process_batch(batch)
                    self._metrics['batch_count'] += 1
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Batch processor error: {e}")
                await asyncio.sleep(0.1)
    
    async def _process_batch(self, batch: List[InferenceRequest]):
        """Process batch of requests"""
        # Group by model
        model_batches = {}
        for request in batch:
            if request.model_id not in model_batches:
                model_batches[request.model_id] = []
            model_batches[request.model_id].append(request)
        
        # Process each model batch
        for model_id, requests in model_batches.items():
            try:
                model = await self._get_model_instance(model_id)
                if model is None:
                    # Handle missing model
                    for request in requests:
                        await self._complete_request(request, InferenceResponse(
                            request_id=request.request_id,
                            model_id=model_id,
                            status=InferenceStatus.FAILED,
                            error_message=f"Model {model_id} not available"
                        ))
                    continue
                
                # Batch predict (simplified - would need actual batch support)
                for request in requests:
                    await self._process_request(request)
                
            except Exception as e:
                self.logger.error(f"Batch processing error for model {model_id}: {e}")
                
                # Fail all requests in batch
                for request in requests:
                    await self._complete_request(request, InferenceResponse(
                        request_id=request.request_id,
                        model_id=model_id,
                        status=InferenceStatus.FAILED,
                        error_message=f"Batch processing failed: {e}"
                    ))
    
    async def _cleanup_worker(self):
        """Background cleanup of expired requests and cache"""
        while self._running:
            try:
                current_time = time.time()
                
                # Clean up expired pending responses
                expired_requests = []
                for request_id, future in self._pending_responses.items():
                    if future.done() or (current_time - future._created_at if hasattr(future, '_created_at') else 0) > 300:  # 5 minutes
                        expired_requests.append(request_id)
                
                for request_id in expired_requests:
                    self._pending_responses.pop(request_id, None)
                
                # Clean up old cache entries
                with self._cache_lock:
                    if len(self._result_cache) > 500:  # Clean when cache gets large
                        # Remove half of the entries (simple cleanup)
                        keys_to_remove = list(self._result_cache.keys())[:len(self._result_cache) // 2]
                        for key in keys_to_remove:
                            del self._result_cache[key]
                
                await asyncio.sleep(60)  # Run every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Cleanup worker error: {e}")
                await asyncio.sleep(60)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive inference engine statistics"""
        queue_sizes = {
            priority.name.lower(): queue.qsize() 
            for priority, queue in self._request_queues.items()
        }
        
        # Calculate performance metrics
        ull_success_rate = 0.0
        if self._metrics['ull_requests_processed'] > 0:
            ull_success_rate = (self._metrics['ull_requests_under_target'] / 
                               self._metrics['ull_requests_processed']) * 100
        
        # Calculate cache hit rate
        total_cache_requests = self._cache_stats['hits'] + self._cache_stats['misses']
        cache_hit_rate = (self._cache_stats['hits'] / max(1, total_cache_requests)) * 100
        
        return {
            'running': self._running,
            'worker_threads': self.worker_threads,
            'ull_worker_threads': self.ultra_low_latency_workers,
            'queue_sizes': queue_sizes,
            'total_queue_size': sum(queue_sizes.values()),
            'pending_responses': len(self._pending_responses),
            'cached_models': len(self._model_cache),
            'cache_size': len(self._result_cache),
            'performance': {
                'avg_processing_time_ns': self._metrics['avg_processing_time_ns'],
                'avg_processing_time_ms': self._metrics['avg_processing_time_ms'],
                'avg_processing_time_us': self._metrics['avg_processing_time_ns'] / 1000,
                'min_processing_time_ns': self._metrics['min_processing_time_ns'],
                'max_processing_time_ns': self._metrics['max_processing_time_ns'],
                'p95_processing_time_ns': self._metrics['p95_processing_time_ns'],
                'p99_processing_time_ns': self._metrics['p99_processing_time_ns'],
                'p95_processing_time_us': self._metrics['p95_processing_time_ns'] / 1000,
                'p99_processing_time_us': self._metrics['p99_processing_time_ns'] / 1000,
                'ull_success_rate_pct': ull_success_rate,
                'target_latency_ns': self.target_latency_ns,
                'target_latency_us': self.target_latency_ns / 1000
            },
            'cache_performance': {
                'hit_rate_pct': cache_hit_rate,
                'hits': self._cache_stats['hits'],
                'misses': self._cache_stats['misses'],
                'evictions': self._cache_stats['evictions']
            },
            'metrics': self._metrics.copy(),
            'optimizations': {
                'zero_copy_operations': self._metrics['zero_copy_operations'],
                'cpu_affinity_optimizations': self._metrics['cpu_affinity_optimizations'],
                'worker_cpu_assignments': self._worker_cpu_assignments
            },
            'config': {
                'max_queue_size': self.max_queue_size,
                'batch_size': self.batch_size,
                'batch_timeout_ms': self.batch_timeout_ms,
                'enable_batching': self.enable_batching,
                'enable_caching': self.enable_caching,
                'enable_zero_copy': self.enable_zero_copy,
                'enable_cpu_affinity': self.enable_cpu_affinity,
                'target_latency_ns': self.target_latency_ns
            }
        }
    
    def get_latency_percentiles(self) -> Dict[str, float]:
        """Get detailed latency percentile statistics"""
        if not self._latency_samples:
            return {}
        
        sorted_samples = sorted(self._latency_samples)
        n = len(sorted_samples)
        
        percentiles = {}
        for p in [50, 75, 90, 95, 99, 99.9]:
            idx = int((p / 100.0) * n)
            if idx >= n:
                idx = n - 1
            percentiles[f'p{p}'] = {
                'ns': sorted_samples[idx],
                'us': sorted_samples[idx] / 1000,
                'ms': sorted_samples[idx] / 1_000_000
            }
        
        return percentiles
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of the inference engine"""
        health = {
            'status': 'healthy',
            'issues': [],
            'recommendations': []
        }
        
        # Check if running
        if not self._running:
            health['status'] = 'unhealthy'
            health['issues'].append('Inference engine not running')
            return health
        
        # Check queue sizes
        total_queue_size = sum(q.qsize() for q in self._request_queues.values())
        if total_queue_size > self.max_queue_size * 0.8:
            health['status'] = 'degraded'
            health['issues'].append(f'High queue utilization: {total_queue_size}/{self.max_queue_size}')
            health['recommendations'].append('Consider increasing worker threads or queue size')
        
        # Check error rate
        total_requests = self._metrics['requests_processed'] + self._metrics['requests_failed']
        if total_requests > 100:  # Only check if we have enough data
            error_rate = (self._metrics['requests_failed'] / total_requests) * 100
            if error_rate > 5:  # 5% error rate threshold
                health['status'] = 'degraded'
                health['issues'].append(f'High error rate: {error_rate:.1f}%')
                health['recommendations'].append('Check model availability and input data quality')
        
        # Check ULL performance
        if self._metrics['ull_requests_processed'] > 10:
            ull_success_rate = (self._metrics['ull_requests_under_target'] / 
                               self._metrics['ull_requests_processed']) * 100
            if ull_success_rate < 90:  # 90% success rate threshold
                health['status'] = 'degraded'
                health['issues'].append(f'Low ULL success rate: {ull_success_rate:.1f}%')
                health['recommendations'].append('Consider model optimization or hardware upgrades')
        
        # Check average latency
        if self._metrics['avg_processing_time_ns'] > self.target_latency_ns * 2:
            health['status'] = 'degraded'
            health['issues'].append(f'High average latency: {self._metrics["avg_processing_time_ns"]/1000:.1f}μs')
            health['recommendations'].append('Consider model optimization or load balancing')
        
        return health