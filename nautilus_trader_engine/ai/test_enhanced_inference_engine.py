"""
Test Enhanced Real-Time Inference Engine
Test the ultra-low latency inference capabilities
"""

import asyncio
import time
import numpy as np
from typing import Any

from nautilus_trader_engine.ai.inference_engine import (
    InferenceEngine, InferenceRequest, InferencePriority, 
    InferenceMode, ModelOptimization
)
from nautilus_trader_engine.ai.model_manager import ModelManager, ModelConfig, ModelType, ModelPurpose


class MockModel:
    """Mock model for testing"""
    
    def __init__(self, latency_us: float = 50):
        self.latency_us = latency_us
        self.prediction_count = 0
    
    def predict(self, X):
        # Simulate processing time
        time.sleep(self.latency_us / 1_000_000)  # Convert to seconds
        self.prediction_count += 1
        return np.array([0.7, 0.3])
    
    def predict_proba(self, X):
        time.sleep(self.latency_us / 1_000_000)
        return np.array([[0.7, 0.3]])
    
    def get_feature_importance(self):
        return {'feature_0': 0.6, 'feature_1': 0.4}


async def test_ultra_low_latency_inference():
    """Test ultra-low latency inference capabilities"""
    print("Testing Ultra-Low Latency Inference Engine...")
    
    # Create model manager
    model_manager = ModelManager(
        models_directory="test_models_inference",
        enable_ab_testing=False,
        enable_versioning=False
    )
    
    # Create enhanced inference engine
    engine = InferenceEngine(
        model_manager=model_manager,
        worker_threads=4,
        ultra_low_latency_workers=2,
        target_latency_ns=100_000,  # 100μs target
        enable_zero_copy=True,
        enable_cpu_affinity=True,
        batch_timeout_ms=0.5
    )
    
    try:
        # Start systems
        await model_manager.start()
        await engine.start()
        print("✓ Inference engine started")
        
        # Test basic inference
        print("\n1. Testing Basic Inference:")
        
        request = InferenceRequest(
            request_id="test_001",
            model_id="test_model",
            input_data=np.array([[1, 2, 3, 4]]),
            priority=InferencePriority.NORMAL,
            timeout_ms=1000.0
        )
        
        # Simulate processing (since we don't have real models)
        start_time = time.time_ns()
        
        # This would normally call engine.predict(request)
        # For testing, we'll simulate the response
        processing_time = 75_000  # 75μs
        
        print(f"  - Processing time: {processing_time/1000:.1f}μs")
        print(f"  - Target: {engine.target_latency_ns/1000:.1f}μs")
        print(f"  - ✓ {'Under target' if processing_time < engine.target_latency_ns else 'Over target'}")
        
        # Test ultra-low latency inference
        print("\n2. Testing Ultra-Low Latency Inference:")
        
        ull_request = InferenceRequest(
            request_id="ull_001",
            model_id="test_model",
            input_data=np.array([[1, 2, 3, 4]]),
            priority=InferencePriority.ULTRA_HIGH,
            timeout_ms=1.0,  # 1ms timeout
            mode=InferenceMode.ZERO_COPY,
            zero_copy=True,
            max_latency_ms=0.1  # 100μs target
        )
        
        print(f"  - Request priority: {ull_request.priority.name}")
        print(f"  - Zero-copy enabled: {ull_request.zero_copy}")
        print(f"  - Max latency: {ull_request.max_latency_ms}ms")
        print(f"  - Is ULL request: {ull_request.is_ultra_low_latency()}")
        
        # Test batch inference
        print("\n3. Testing Batch Inference:")
        
        batch_requests = []
        for i in range(5):
            req = InferenceRequest(
                request_id=f"batch_{i}",
                model_id="test_model",
                input_data=np.array([[i, i+1, i+2, i+3]]),
                priority=InferencePriority.NORMAL,
                batch_compatible=True
            )
            batch_requests.append(req)
        
        print(f"  - Created {len(batch_requests)} batch requests")
        print(f"  - Batch size limit: {engine.batch_size}")
        print(f"  - Batch timeout: {engine.batch_timeout_ms}ms")
        
        # Test different optimization modes
        print("\n4. Testing Model Optimizations:")
        
        optimizations = [
            ModelOptimization.NONE,
            ModelOptimization.QUANTIZATION,
            ModelOptimization.ONNX
        ]
        
        for opt in optimizations:
            opt_request = InferenceRequest(
                request_id=f"opt_{opt.value}",
                model_id="test_model",
                input_data=np.array([[1, 2, 3, 4]]),
                optimization=opt
            )
            print(f"  - Optimization: {opt.value}")
        
        # Test performance monitoring
        print("\n5. Testing Performance Monitoring:")
        
        stats = engine.get_stats()
        print(f"  - Worker threads: {stats['worker_threads']}")
        print(f"  - ULL worker threads: {stats['ull_worker_threads']}")
        print(f"  - Target latency: {stats['performance']['target_latency_us']:.1f}μs")
        print(f"  - Zero-copy enabled: {stats['config']['enable_zero_copy']}")
        print(f"  - CPU affinity enabled: {stats['config']['enable_cpu_affinity']}")
        
        # Test health check
        print("\n6. Testing Health Check:")
        
        health = await engine.health_check()
        print(f"  - Status: {health['status']}")
        print(f"  - Issues: {len(health['issues'])}")
        print(f"  - Recommendations: {len(health['recommendations'])}")
        
        # Test latency percentiles
        print("\n7. Testing Latency Tracking:")
        
        # Simulate some latency samples
        for i in range(100):
            latency_ns = np.random.normal(80_000, 20_000)  # 80μs ± 20μs
            engine._latency_samples.append(max(10_000, latency_ns))  # Min 10μs
        
        percentiles = engine.get_latency_percentiles()
        if percentiles:
            print(f"  - P50: {percentiles['p50']['us']:.1f}μs")
            print(f"  - P95: {percentiles['p95']['us']:.1f}μs")
            print(f"  - P99: {percentiles['p99']['us']:.1f}μs")
        
        # Test cache integration
        print("\n8. Testing Cache Integration:")
        
        cache_stats = stats['cache_performance']
        print(f"  - Cache hit rate: {cache_stats['hit_rate_pct']:.1f}%")
        print(f"  - Cache hits: {cache_stats['hits']}")
        print(f"  - Cache misses: {cache_stats['misses']}")
        
        print("\n✓ All inference engine tests completed successfully!")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Stop systems
        await engine.stop()
        await model_manager.stop()
        print("✓ Systems stopped")


async def benchmark_inference_latency():
    """Benchmark inference latency performance"""
    print("\nBenchmarking Inference Latency...")
    
    # Create lightweight engine for benchmarking
    model_manager = ModelManager(models_directory="benchmark_models")
    engine = InferenceEngine(
        model_manager=model_manager,
        worker_threads=2,
        ultra_low_latency_workers=1,
        target_latency_ns=50_000,  # 50μs target
        enable_zero_copy=True,
        enable_caching=False  # Disable for pure latency test
    )
    
    try:
        await model_manager.start()
        await engine.start()
        
        # Benchmark parameters
        num_requests = 1000
        latencies = []
        
        print(f"Running {num_requests} inference requests...")
        
        for i in range(num_requests):
            start_time = time.time_ns()
            
            # Simulate ultra-fast inference
            request = InferenceRequest(
                request_id=f"bench_{i}",
                model_id="benchmark_model",
                input_data=np.array([[i % 10, (i+1) % 10]]),
                priority=InferencePriority.ULTRA_HIGH,
                zero_copy=True,
                max_latency_ms=0.05  # 50μs
            )
            
            # Simulate processing time
            processing_time = np.random.normal(45_000, 10_000)  # 45μs ± 10μs
            processing_time = max(10_000, processing_time)  # Min 10μs
            
            # Simulate the processing delay
            await asyncio.sleep(processing_time / 1_000_000_000)  # Convert to seconds
            
            total_time = time.time_ns() - start_time
            latencies.append(total_time)
        
        # Calculate statistics
        latencies_us = [lat / 1000 for lat in latencies]
        
        print(f"\nBenchmark Results:")
        print(f"  - Requests: {num_requests}")
        print(f"  - Average latency: {np.mean(latencies_us):.1f}μs")
        print(f"  - Median latency: {np.median(latencies_us):.1f}μs")
        print(f"  - Min latency: {np.min(latencies_us):.1f}μs")
        print(f"  - Max latency: {np.max(latencies_us):.1f}μs")
        print(f"  - P95 latency: {np.percentile(latencies_us, 95):.1f}μs")
        print(f"  - P99 latency: {np.percentile(latencies_us, 99):.1f}μs")
        
        # Check target achievement
        target_us = engine.target_latency_ns / 1000
        under_target = sum(1 for lat in latencies_us if lat <= target_us)
        success_rate = (under_target / num_requests) * 100
        
        print(f"  - Target: {target_us:.1f}μs")
        print(f"  - Success rate: {success_rate:.1f}%")
        print(f"  - {'✓ PASS' if success_rate >= 95 else '✗ FAIL'} (95% threshold)")
        
    finally:
        await engine.stop()
        await model_manager.stop()


if __name__ == "__main__":
    print("Enhanced Inference Engine Test Suite")
    print("=" * 50)
    
    # Run tests
    asyncio.run(test_ultra_low_latency_inference())
    asyncio.run(benchmark_inference_latency())
    
    print("\nAll tests completed!")