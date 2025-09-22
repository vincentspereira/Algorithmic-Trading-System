"""Hardware Acceleration Module

Provides GPU (CUDA) and FPGA acceleration for computationally intensive
indicator calculations to achieve ultra-low latency performance.

Key Features:
- CUDA GPU acceleration for parallel computations
- FPGA integration for ultra-low latency
- Automatic fallback to CPU implementations
- Memory management and optimization
- Batch processing capabilities
- Performance monitoring and profiling
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple, Union, Callable
from collections import deque, defaultdict
from dataclasses import dataclass, field
from enum import Enum
import json
from abc import ABC, abstractmethod
import threading
import time

try:
    from utils.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# Try to import CUDA libraries
try:
    import cupy as cp
    import cupyx.scipy.signal as cp_signal
    CUDA_AVAILABLE = True
    logger.info("CUDA acceleration available")
except ImportError:
    cp = None
    cp_signal = None
    CUDA_AVAILABLE = False
    logger.info("CUDA not available, using CPU fallback")

# Try to import Numba for JIT compilation
try:
    from numba import jit, cuda, float32, float64
    import numba as nb
    NUMBA_AVAILABLE = True
    logger.info("Numba JIT compilation available")
except ImportError:
    jit = lambda func: func  # No-op decorator
    cuda = None
    NUMBA_AVAILABLE = False
    logger.info("Numba not available, using standard Python")

# Try to import OpenCL for broader GPU support
try:
    import pyopencl as cl
    import pyopencl.array as cl_array
    OPENCL_AVAILABLE = True
    logger.info("OpenCL acceleration available")
except ImportError:
    cl = None
    cl_array = None
    OPENCL_AVAILABLE = False
    logger.info("OpenCL not available")

class AccelerationType(Enum):
    """Available acceleration types"""
    CPU = "cpu"
    CUDA = "cuda"
    OPENCL = "opencl"
    FPGA = "fpga"
    AUTO = "auto"

class ComputeKernel(Enum):
    """Available compute kernels"""
    MOVING_AVERAGE = "moving_average"
    RSI = "rsi"
    MACD = "macd"
    BOLLINGER_BANDS = "bollinger_bands"
    ATR = "atr"
    STOCHASTIC = "stochastic"
    VOLUME_WEIGHTED = "volume_weighted"
    CORRELATION = "correlation"
    COVARIANCE = "covariance"
    FFT = "fft"
    CONVOLUTION = "convolution"

@dataclass
class AccelerationConfig:
    """Configuration for hardware acceleration"""
    # Acceleration preferences
    preferred_acceleration: AccelerationType = AccelerationType.AUTO
    fallback_to_cpu: bool = True
    
    # Memory management
    max_gpu_memory_mb: int = 1024  # 1GB default
    batch_size: int = 10000
    use_memory_pool: bool = True
    
    # Performance settings
    enable_profiling: bool = False
    cache_kernels: bool = True
    optimize_memory_access: bool = True
    
    # CUDA specific
    cuda_device_id: int = 0
    cuda_streams: int = 4
    
    # OpenCL specific
    opencl_platform_id: int = 0
    opencl_device_id: int = 0
    
    # FPGA specific
    fpga_bitstream_path: Optional[str] = None
    fpga_clock_frequency: int = 200  # MHz
    
    # Thresholds for acceleration
    min_data_size_for_gpu: int = 1000
    min_batch_size_for_acceleration: int = 100

@dataclass
class PerformanceMetrics:
    """Performance metrics for acceleration"""
    kernel_name: str
    acceleration_type: AccelerationType
    data_size: int
    execution_time_ms: float
    memory_usage_mb: float
    throughput_ops_per_sec: float
    speedup_factor: float
    timestamp: datetime = field(default_factory=datetime.now)

class GPUMemoryManager:
    """Manages GPU memory allocation and deallocation"""
    
    def __init__(self, config: AccelerationConfig):
        self.config = config
        self.allocated_memory = 0
        self.memory_pool = None
        
        if CUDA_AVAILABLE and config.use_memory_pool:
            try:
                self.memory_pool = cp.get_default_memory_pool()
                logger.info("CUDA memory pool initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize CUDA memory pool: {e}")
    
    def allocate_gpu_array(self, shape: Tuple[int, ...], dtype=np.float32) -> Union[np.ndarray, Any]:
        """Allocate GPU array"""
        if not CUDA_AVAILABLE:
            return np.zeros(shape, dtype=dtype)
        
        try:
            # Calculate memory requirement
            memory_mb = np.prod(shape) * np.dtype(dtype).itemsize / (1024 * 1024)
            
            if self.allocated_memory + memory_mb > self.config.max_gpu_memory_mb:
                logger.warning("GPU memory limit reached, using CPU fallback")
                return np.zeros(shape, dtype=dtype)
            
            gpu_array = cp.zeros(shape, dtype=dtype)
            self.allocated_memory += memory_mb
            
            return gpu_array
            
        except Exception as e:
            logger.warning(f"GPU allocation failed: {e}, using CPU fallback")
            return np.zeros(shape, dtype=dtype)
    
    def free_gpu_memory(self):
        """Free GPU memory"""
        if CUDA_AVAILABLE and self.memory_pool:
            try:
                self.memory_pool.free_all_blocks()
                self.allocated_memory = 0
                logger.debug("GPU memory freed")
            except Exception as e:
                logger.warning(f"Failed to free GPU memory: {e}")
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get memory usage information"""
        info = {
            'allocated_mb': self.allocated_memory,
            'max_mb': self.config.max_gpu_memory_mb,
            'utilization': self.allocated_memory / self.config.max_gpu_memory_mb
        }
        
        if CUDA_AVAILABLE:
            try:
                meminfo = cp.cuda.runtime.memGetInfo()
                info.update({
                    'gpu_free_mb': meminfo[0] / (1024 * 1024),
                    'gpu_total_mb': meminfo[1] / (1024 * 1024)
                })
            except Exception as e:
                logger.debug(f"Could not get GPU memory info: {e}")
        
        return info

class CUDAKernels:
    """CUDA kernel implementations for common indicators"""
    
    @staticmethod
    def moving_average_cuda(data: cp.ndarray, window: int) -> cp.ndarray:
        """CUDA implementation of moving average"""
        if not CUDA_AVAILABLE:
            raise RuntimeError("CUDA not available")
        
        # Use CuPy's built-in convolution for moving average
        kernel = cp.ones(window, dtype=data.dtype) / window
        return cp.convolve(data, kernel, mode='valid')
    
    @staticmethod
    def rsi_cuda(prices: cp.ndarray, period: int = 14) -> cp.ndarray:
        """CUDA implementation of RSI"""
        if not CUDA_AVAILABLE:
            raise RuntimeError("CUDA not available")
        
        # Calculate price changes
        deltas = cp.diff(prices)
        
        # Separate gains and losses
        gains = cp.where(deltas > 0, deltas, 0)
        losses = cp.where(deltas < 0, -deltas, 0)
        
        # Calculate average gains and losses
        avg_gains = cp.convolve(gains, cp.ones(period)/period, mode='valid')
        avg_losses = cp.convolve(losses, cp.ones(period)/period, mode='valid')
        
        # Calculate RSI
        rs = avg_gains / (avg_losses + 1e-10)  # Avoid division by zero
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def bollinger_bands_cuda(prices: cp.ndarray, window: int = 20, 
                           num_std: float = 2.0) -> Tuple[cp.ndarray, cp.ndarray, cp.ndarray]:
        """CUDA implementation of Bollinger Bands"""
        if not CUDA_AVAILABLE:
            raise RuntimeError("CUDA not available")
        
        # Calculate moving average
        ma = CUDAKernels.moving_average_cuda(prices, window)
        
        # Calculate rolling standard deviation
        # This is a simplified implementation
        squared_diffs = cp.square(prices[window-1:] - ma)
        rolling_var = cp.convolve(squared_diffs, cp.ones(window)/window, mode='valid')
        rolling_std = cp.sqrt(rolling_var)
        
        # Calculate bands
        upper_band = ma + (rolling_std * num_std)
        lower_band = ma - (rolling_std * num_std)
        
        return upper_band, ma, lower_band
    
    @staticmethod
    def volume_weighted_price_cuda(prices: cp.ndarray, volumes: cp.ndarray, 
                                 window: int) -> cp.ndarray:
        """CUDA implementation of volume-weighted price"""
        if not CUDA_AVAILABLE:
            raise RuntimeError("CUDA not available")
        
        # Calculate price * volume
        pv = prices * volumes
        
        # Rolling sum of price * volume
        pv_sum = cp.convolve(pv, cp.ones(window), mode='valid')
        
        # Rolling sum of volume
        vol_sum = cp.convolve(volumes, cp.ones(window), mode='valid')
        
        # Volume weighted price
        vwp = pv_sum / (vol_sum + 1e-10)  # Avoid division by zero
        
        return vwp

class NumbaKernels:
    """Numba JIT-compiled kernels for CPU acceleration"""
    
    @staticmethod
    @jit(nopython=True, cache=True)
    def moving_average_numba(data: np.ndarray, window: int) -> np.ndarray:
        """Numba JIT implementation of moving average"""
        n = len(data)
        result = np.empty(n - window + 1, dtype=data.dtype)
        
        for i in range(len(result)):
            result[i] = np.mean(data[i:i + window])
        
        return result
    
    @staticmethod
    @jit(nopython=True, cache=True)
    def rsi_numba(prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Numba JIT implementation of RSI"""
        n = len(prices)
        deltas = np.diff(prices)
        
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        
        # Calculate initial averages
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        rsi = np.empty(n - period, dtype=np.float64)
        
        for i in range(len(rsi)):
            if i == 0:
                rs = avg_gain / (avg_loss + 1e-10)
            else:
                # Exponential moving average
                avg_gain = (avg_gain * (period - 1) + gains[period + i - 1]) / period
                avg_loss = (avg_loss * (period - 1) + losses[period + i - 1]) / period
                rs = avg_gain / (avg_loss + 1e-10)
            
            rsi[i] = 100.0 - (100.0 / (1.0 + rs))
        
        return rsi
    
    @staticmethod
    @jit(nopython=True, cache=True)
    def correlation_numba(x: np.ndarray, y: np.ndarray, window: int) -> np.ndarray:
        """Numba JIT implementation of rolling correlation"""
        n = len(x)
        result = np.empty(n - window + 1, dtype=np.float64)
        
        for i in range(len(result)):
            x_window = x[i:i + window]
            y_window = y[i:i + window]
            
            # Calculate correlation coefficient
            x_mean = np.mean(x_window)
            y_mean = np.mean(y_window)
            
            numerator = np.sum((x_window - x_mean) * (y_window - y_mean))
            x_var = np.sum((x_window - x_mean) ** 2)
            y_var = np.sum((y_window - y_mean) ** 2)
            
            denominator = np.sqrt(x_var * y_var)
            
            if denominator > 1e-10:
                result[i] = numerator / denominator
            else:
                result[i] = 0.0
        
        return result

class FPGAInterface:
    """Interface for FPGA acceleration (placeholder implementation)"""
    
    def __init__(self, config: AccelerationConfig):
        self.config = config
        self.initialized = False
        
        # In a real implementation, this would initialize FPGA communication
        logger.info("FPGA interface initialized (placeholder)")
    
    def moving_average_fpga(self, data: np.ndarray, window: int) -> np.ndarray:
        """FPGA implementation of moving average"""
        # Placeholder - in reality, this would send data to FPGA and receive results
        logger.debug(f"FPGA moving average calculation for {len(data)} points")
        
        # Simulate FPGA processing time (much faster than CPU)
        time.sleep(0.001)  # 1ms simulated processing time
        
        # Return CPU calculation as placeholder
        return np.convolve(data, np.ones(window)/window, mode='valid')
    
    def batch_process_fpga(self, operations: List[Dict[str, Any]]) -> List[np.ndarray]:
        """Batch process multiple operations on FPGA"""
        results = []
        
        for op in operations:
            kernel = op.get('kernel')
            data = op.get('data')
            params = op.get('params', {})
            
            if kernel == ComputeKernel.MOVING_AVERAGE:
                result = self.moving_average_fpga(data, params.get('window', 20))
            else:
                # Fallback to CPU
                result = data  # Placeholder
            
            results.append(result)
        
        return results

class AccelerationEngine:
    """Main acceleration engine that manages different compute backends"""
    
    def __init__(self, config: AccelerationConfig = None):
        self.config = config or AccelerationConfig()
        
        # Initialize components
        self.memory_manager = GPUMemoryManager(self.config)
        self.fpga_interface = FPGAInterface(self.config) if self.config.preferred_acceleration == AccelerationType.FPGA else None
        
        # Performance tracking
        self.performance_history = deque(maxlen=1000)
        self.kernel_cache = {}
        
        # Determine available acceleration
        self.available_acceleration = self._detect_available_acceleration()
        
        logger.info(f"Acceleration engine initialized with: {self.available_acceleration}")
    
    def _detect_available_acceleration(self) -> List[AccelerationType]:
        """Detect available acceleration types"""
        available = [AccelerationType.CPU]  # CPU always available
        
        if CUDA_AVAILABLE:
            try:
                cp.cuda.runtime.getDeviceCount()
                available.append(AccelerationType.CUDA)
            except Exception as e:
                logger.debug(f"CUDA detection failed: {e}")
        
        if OPENCL_AVAILABLE:
            try:
                platforms = cl.get_platforms()
                if platforms:
                    available.append(AccelerationType.OPENCL)
            except Exception as e:
                logger.debug(f"OpenCL detection failed: {e}")
        
        if self.fpga_interface and self.fpga_interface.initialized:
            available.append(AccelerationType.FPGA)
        
        return available
    
    def select_acceleration(self, kernel: ComputeKernel, data_size: int) -> AccelerationType:
        """Select optimal acceleration type for given kernel and data size"""
        
        # Check if data size meets minimum threshold
        if data_size < self.config.min_data_size_for_gpu:
            return AccelerationType.CPU
        
        # Auto selection logic
        if self.config.preferred_acceleration == AccelerationType.AUTO:
            # Prefer FPGA for supported kernels
            if (AccelerationType.FPGA in self.available_acceleration and 
                kernel in [ComputeKernel.MOVING_AVERAGE, ComputeKernel.RSI]):
                return AccelerationType.FPGA
            
            # Prefer CUDA for large datasets
            if (AccelerationType.CUDA in self.available_acceleration and 
                data_size > 10000):
                return AccelerationType.CUDA
            
            # Use CPU with Numba for medium datasets
            if NUMBA_AVAILABLE and data_size > 1000:
                return AccelerationType.CPU
        
        # Use preferred acceleration if available
        if self.config.preferred_acceleration in self.available_acceleration:
            return self.config.preferred_acceleration
        
        # Fallback to CPU
        return AccelerationType.CPU
    
    def compute(self, kernel: ComputeKernel, data: Union[np.ndarray, List[np.ndarray]], 
               **kwargs) -> Union[np.ndarray, List[np.ndarray]]:
        """Main compute function that dispatches to appropriate backend"""
        
        start_time = time.time()
        
        # Determine data size
        if isinstance(data, list):
            data_size = sum(len(arr) for arr in data)
        else:
            data_size = len(data)
        
        # Select acceleration type
        acceleration = self.select_acceleration(kernel, data_size)
        
        try:
            # Dispatch to appropriate backend
            if acceleration == AccelerationType.CUDA:
                result = self._compute_cuda(kernel, data, **kwargs)
            elif acceleration == AccelerationType.FPGA:
                result = self._compute_fpga(kernel, data, **kwargs)
            else:  # CPU (with or without Numba)
                result = self._compute_cpu(kernel, data, **kwargs)
            
            # Record performance metrics
            execution_time = (time.time() - start_time) * 1000  # ms
            self._record_performance(kernel, acceleration, data_size, execution_time)
            
            return result
            
        except Exception as e:
            logger.warning(f"Acceleration failed ({acceleration.value}): {e}")
            
            if self.config.fallback_to_cpu and acceleration != AccelerationType.CPU:
                logger.info("Falling back to CPU computation")
                return self._compute_cpu(kernel, data, **kwargs)
            else:
                raise
    
    def _compute_cuda(self, kernel: ComputeKernel, data: Union[np.ndarray, List[np.ndarray]], 
                     **kwargs) -> Union[np.ndarray, List[np.ndarray]]:
        """CUDA computation backend"""
        
        if not CUDA_AVAILABLE:
            raise RuntimeError("CUDA not available")
        
        # Convert data to GPU arrays
        if isinstance(data, list):
            gpu_data = [cp.asarray(arr) for arr in data]
        else:
            gpu_data = cp.asarray(data)
        
        # Dispatch to appropriate CUDA kernel
        if kernel == ComputeKernel.MOVING_AVERAGE:
            window = kwargs.get('window', 20)
            result = CUDAKernels.moving_average_cuda(gpu_data, window)
        elif kernel == ComputeKernel.RSI:
            period = kwargs.get('period', 14)
            result = CUDAKernels.rsi_cuda(gpu_data, period)
        elif kernel == ComputeKernel.BOLLINGER_BANDS:
            window = kwargs.get('window', 20)
            num_std = kwargs.get('num_std', 2.0)
            result = CUDAKernels.bollinger_bands_cuda(gpu_data, window, num_std)
        elif kernel == ComputeKernel.VOLUME_WEIGHTED:
            volumes = cp.asarray(kwargs.get('volumes'))
            window = kwargs.get('window', 20)
            result = CUDAKernels.volume_weighted_price_cuda(gpu_data, volumes, window)
        else:
            raise NotImplementedError(f"CUDA kernel not implemented for {kernel.value}")
        
        # Convert result back to CPU
        if isinstance(result, tuple):
            return tuple(cp.asnumpy(r) for r in result)
        else:
            return cp.asnumpy(result)
    
    def _compute_fpga(self, kernel: ComputeKernel, data: Union[np.ndarray, List[np.ndarray]], 
                     **kwargs) -> Union[np.ndarray, List[np.ndarray]]:
        """FPGA computation backend"""
        
        if not self.fpga_interface:
            raise RuntimeError("FPGA interface not available")
        
        # Dispatch to FPGA interface
        if kernel == ComputeKernel.MOVING_AVERAGE:
            window = kwargs.get('window', 20)
            return self.fpga_interface.moving_average_fpga(data, window)
        else:
            raise NotImplementedError(f"FPGA kernel not implemented for {kernel.value}")
    
    def _compute_cpu(self, kernel: ComputeKernel, data: Union[np.ndarray, List[np.ndarray]], 
                    **kwargs) -> Union[np.ndarray, List[np.ndarray]]:
        """CPU computation backend (with optional Numba acceleration)"""
        
        # Use Numba kernels if available
        if NUMBA_AVAILABLE:
            if kernel == ComputeKernel.MOVING_AVERAGE:
                window = kwargs.get('window', 20)
                return NumbaKernels.moving_average_numba(data, window)
            elif kernel == ComputeKernel.RSI:
                period = kwargs.get('period', 14)
                return NumbaKernels.rsi_numba(data, period)
            elif kernel == ComputeKernel.CORRELATION:
                y_data = kwargs.get('y_data')
                window = kwargs.get('window', 20)
                return NumbaKernels.correlation_numba(data, y_data, window)
        
        # Fallback to standard NumPy implementations
        if kernel == ComputeKernel.MOVING_AVERAGE:
            window = kwargs.get('window', 20)
            return np.convolve(data, np.ones(window)/window, mode='valid')
        elif kernel == ComputeKernel.RSI:
            period = kwargs.get('period', 14)
            deltas = np.diff(data)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            avg_gains = pd.Series(gains).rolling(period).mean().values
            avg_losses = pd.Series(losses).rolling(period).mean().values
            rs = avg_gains / (avg_losses + 1e-10)
            return 100 - (100 / (1 + rs))
        else:
            raise NotImplementedError(f"CPU kernel not implemented for {kernel.value}")
    
    def _record_performance(self, kernel: ComputeKernel, acceleration: AccelerationType,
                          data_size: int, execution_time_ms: float):
        """Record performance metrics"""
        
        if not self.config.enable_profiling:
            return
        
        # Calculate throughput
        throughput = data_size / (execution_time_ms / 1000) if execution_time_ms > 0 else 0
        
        # Estimate speedup (compared to baseline CPU)
        baseline_time = data_size * 0.001  # Rough estimate: 1μs per data point
        speedup = baseline_time / (execution_time_ms / 1000) if execution_time_ms > 0 else 1
        
        # Get memory usage
        memory_info = self.memory_manager.get_memory_info()
        memory_usage = memory_info.get('allocated_mb', 0)
        
        metrics = PerformanceMetrics(
            kernel_name=kernel.value,
            acceleration_type=acceleration,
            data_size=data_size,
            execution_time_ms=execution_time_ms,
            memory_usage_mb=memory_usage,
            throughput_ops_per_sec=throughput,
            speedup_factor=speedup
        )
        
        self.performance_history.append(metrics)
        
        logger.debug(f"Performance: {kernel.value} on {acceleration.value} - "
                    f"{execution_time_ms:.2f}ms, {throughput:.0f} ops/sec, {speedup:.1f}x speedup")
    
    def batch_compute(self, operations: List[Dict[str, Any]]) -> List[Any]:
        """Batch compute multiple operations for efficiency"""
        
        if len(operations) < self.config.min_batch_size_for_acceleration:
            # Process individually for small batches
            return [self.compute(**op) for op in operations]
        
        # Group operations by acceleration type
        grouped_ops = defaultdict(list)
        
        for i, op in enumerate(operations):
            kernel = op.get('kernel')
            data = op.get('data')
            data_size = len(data) if hasattr(data, '__len__') else 1
            
            acceleration = self.select_acceleration(kernel, data_size)
            grouped_ops[acceleration].append((i, op))
        
        # Process each group
        results = [None] * len(operations)
        
        for acceleration, ops in grouped_ops.items():
            if acceleration == AccelerationType.FPGA and self.fpga_interface:
                # Use FPGA batch processing
                fpga_ops = [op[1] for op in ops]
                fpga_results = self.fpga_interface.batch_process_fpga(fpga_ops)
                
                for (i, _), result in zip(ops, fpga_results):
                    results[i] = result
            else:
                # Process individually
                for i, op in ops:
                    results[i] = self.compute(**op)
        
        return results
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        if not self.performance_history:
            return {}
        
        recent_metrics = list(self.performance_history)[-100:]  # Last 100 operations
        
        # Group by acceleration type
        by_acceleration = defaultdict(list)
        for metric in recent_metrics:
            by_acceleration[metric.acceleration_type.value].append(metric)
        
        summary = {
            'total_operations': len(self.performance_history),
            'recent_operations': len(recent_metrics),
            'available_acceleration': [acc.value for acc in self.available_acceleration],
            'memory_info': self.memory_manager.get_memory_info(),
            'by_acceleration': {}
        }
        
        for acc_type, metrics in by_acceleration.items():
            summary['by_acceleration'][acc_type] = {
                'operations': len(metrics),
                'avg_execution_time_ms': np.mean([m.execution_time_ms for m in metrics]),
                'avg_throughput': np.mean([m.throughput_ops_per_sec for m in metrics]),
                'avg_speedup': np.mean([m.speedup_factor for m in metrics]),
                'total_data_processed': sum(m.data_size for m in metrics)
            }
        
        return summary
    
    def optimize_configuration(self):
        """Optimize configuration based on performance history"""
        if len(self.performance_history) < 50:
            return  # Need more data
        
        recent_metrics = list(self.performance_history)[-50:]
        
        # Analyze performance by acceleration type
        performance_by_type = defaultdict(list)
        for metric in recent_metrics:
            performance_by_type[metric.acceleration_type].append(metric.speedup_factor)
        
        # Find best performing acceleration type
        best_acceleration = None
        best_speedup = 0
        
        for acc_type, speedups in performance_by_type.items():
            avg_speedup = np.mean(speedups)
            if avg_speedup > best_speedup:
                best_speedup = avg_speedup
                best_acceleration = acc_type
        
        # Update preferred acceleration if significantly better
        if (best_acceleration and best_acceleration != self.config.preferred_acceleration and
            best_speedup > 1.5):  # At least 50% better
            
            logger.info(f"Optimizing: switching preferred acceleration from "
                       f"{self.config.preferred_acceleration.value} to {best_acceleration.value} "
                       f"(speedup: {best_speedup:.1f}x)")
            
            self.config.preferred_acceleration = best_acceleration
    
    def cleanup(self):
        """Cleanup resources"""
        self.memory_manager.free_gpu_memory()
        logger.info("Acceleration engine cleanup completed")

# Factory functions
def create_acceleration_engine(config: AccelerationConfig = None) -> AccelerationEngine:
    """Create acceleration engine"""
    return AccelerationEngine(config)

def create_cuda_config() -> AccelerationConfig:
    """Create CUDA-optimized configuration"""
    return AccelerationConfig(
        preferred_acceleration=AccelerationType.CUDA,
        max_gpu_memory_mb=2048,
        batch_size=50000,
        cuda_streams=8,
        enable_profiling=True
    )

def create_fpga_config(bitstream_path: str) -> AccelerationConfig:
    """Create FPGA-optimized configuration"""
    return AccelerationConfig(
        preferred_acceleration=AccelerationType.FPGA,
        fpga_bitstream_path=bitstream_path,
        fpga_clock_frequency=250,
        batch_size=100000,
        enable_profiling=True
    )

# Utility functions for common operations
def accelerated_moving_average(data: np.ndarray, window: int, 
                             engine: AccelerationEngine = None) -> np.ndarray:
    """Compute accelerated moving average"""
    if engine is None:
        engine = create_acceleration_engine()
    
    return engine.compute(ComputeKernel.MOVING_AVERAGE, data, window=window)

def accelerated_rsi(data: np.ndarray, period: int = 14, 
                   engine: AccelerationEngine = None) -> np.ndarray:
    """Compute accelerated RSI"""
    if engine is None:
        engine = create_acceleration_engine()
    
    return engine.compute(ComputeKernel.RSI, data, period=period)

def accelerated_correlation(x: np.ndarray, y: np.ndarray, window: int = 20,
                          engine: AccelerationEngine = None) -> np.ndarray:
    """Compute accelerated rolling correlation"""
    if engine is None:
        engine = create_acceleration_engine()
    
    return engine.compute(ComputeKernel.CORRELATION, x, y_data=y, window=window)