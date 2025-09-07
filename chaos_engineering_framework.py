#!/usr/bin/env python3
"""
Chaos Engineering Framework
Provides chaos testing capabilities for the algorithmic trading system.
"""

import asyncio
import random
import time
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from unittest.mock import Mock, AsyncMock

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FailureType(Enum):
    """Types of failures that can be injected."""
    NETWORK_LATENCY = "network_latency"
    NETWORK_PARTITION = "network_partition"
    SERVICE_CRASH = "service_crash"
    DATABASE_TIMEOUT = "database_timeout"
    MEMORY_PRESSURE = "memory_pressure"
    CPU_SPIKE = "cpu_spike"
    DISK_FULL = "disk_full"

@dataclass
class ChaosExperiment:
    """Represents a chaos engineering experiment."""
    name: str
    description: str
    failure_type: FailureType
    target_service: str
    duration_seconds: int
    intensity: float  # 0.0 to 1.0
    conditions: Dict[str, Any]
    expected_behavior: str
    
    def __post_init__(self):
        self.id = f"chaos_{self.name}_{int(time.time())}"
        self.status = "pending"
        self.start_time = None
        self.end_time = None
        self.results = {}

class FailureInjector:
    """Injects various types of failures into the system."""
    
    def __init__(self):
        self.active_failures = {}
        self.failure_history = []
        
    async def inject_network_latency(self, target: str, latency_ms: int, duration: int):
        """Inject network latency."""
        logger.info(f"Injecting {latency_ms}ms network latency to {target} for {duration}s")
        
        failure_id = f"latency_{target}_{int(time.time())}"
        self.active_failures[failure_id] = {
            "type": FailureType.NETWORK_LATENCY,
            "target": target,
            "params": {"latency_ms": latency_ms},
            "start_time": datetime.now(),
            "duration": duration
        }
        
        # Simulate latency injection
        await asyncio.sleep(0.1)
        
        # Schedule cleanup
        asyncio.create_task(self._cleanup_failure(failure_id, duration))
        return failure_id
        
    async def inject_service_crash(self, target: str, crash_probability: float):
        """Inject service crash."""
        logger.info(f"Injecting service crash to {target} with probability {crash_probability}")
        
        if random.random() < crash_probability:
            failure_id = f"crash_{target}_{int(time.time())}"
            self.active_failures[failure_id] = {
                "type": FailureType.SERVICE_CRASH,
                "target": target,
                "params": {"crash_probability": crash_probability},
                "start_time": datetime.now()
            }
            return failure_id
        return None
        
    async def inject_database_timeout(self, target: str, timeout_ms: int, duration: int):
        """Inject database timeout."""
        logger.info(f"Injecting {timeout_ms}ms database timeout to {target} for {duration}s")
        
        failure_id = f"db_timeout_{target}_{int(time.time())}"
        self.active_failures[failure_id] = {
            "type": FailureType.DATABASE_TIMEOUT,
            "target": target,
            "params": {"timeout_ms": timeout_ms},
            "start_time": datetime.now(),
            "duration": duration
        }
        
        # Schedule cleanup
        asyncio.create_task(self._cleanup_failure(failure_id, duration))
        return failure_id
        
    async def _cleanup_failure(self, failure_id: str, duration: int):
        """Clean up failure after duration."""
        await asyncio.sleep(duration)
        if failure_id in self.active_failures:
            failure = self.active_failures.pop(failure_id)
            failure["end_time"] = datetime.now()
            self.failure_history.append(failure)
            logger.info(f"Cleaned up failure {failure_id}")
            
    def get_active_failures(self) -> Dict[str, Any]:
        """Get currently active failures."""
        return self.active_failures.copy()
        
    def get_failure_history(self) -> List[Dict[str, Any]]:
        """Get history of all failures."""
        return self.failure_history.copy()

class SystemMonitor:
    """Monitors system health during chaos experiments."""
    
    def __init__(self):
        self.metrics = {}
        self.alerts = []
        self.monitoring_active = False
        
    async def start_monitoring(self):
        """Start system monitoring."""
        self.monitoring_active = True
        logger.info("System monitoring started")
        
        # Start monitoring tasks
        asyncio.create_task(self._monitor_cpu())
        asyncio.create_task(self._monitor_memory())
        asyncio.create_task(self._monitor_network())
        
    async def stop_monitoring(self):
        """Stop system monitoring."""
        self.monitoring_active = False
        logger.info("System monitoring stopped")
        
    async def _monitor_cpu(self):
        """Monitor CPU usage."""
        while self.monitoring_active:
            # Simulate CPU monitoring
            cpu_usage = random.uniform(10, 90)
            self.metrics["cpu_usage"] = cpu_usage
            
            if cpu_usage > 80:
                self.alerts.append({
                    "type": "cpu_high",
                    "value": cpu_usage,
                    "timestamp": datetime.now()
                })
                
            await asyncio.sleep(1)
            
    async def _monitor_memory(self):
        """Monitor memory usage."""
        while self.monitoring_active:
            # Simulate memory monitoring
            memory_usage = random.uniform(20, 85)
            self.metrics["memory_usage"] = memory_usage
            
            if memory_usage > 80:
                self.alerts.append({
                    "type": "memory_high",
                    "value": memory_usage,
                    "timestamp": datetime.now()
                })
                
            await asyncio.sleep(1)
            
    async def _monitor_network(self):
        """Monitor network connectivity."""
        while self.monitoring_active:
            # Simulate network monitoring
            network_latency = random.uniform(1, 100)
            self.metrics["network_latency"] = network_latency
            
            if network_latency > 50:
                self.alerts.append({
                    "type": "network_slow",
                    "value": network_latency,
                    "timestamp": datetime.now()
                })
                
            await asyncio.sleep(1)
            
    def get_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        return self.metrics.copy()
        
    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get system alerts."""
        return self.alerts.copy()
        
    def clear_alerts(self):
        """Clear all alerts."""
        self.alerts.clear()

class ChaosExperimentRunner:
    """Runs chaos engineering experiments."""
    
    def __init__(self):
        self.failure_injector = FailureInjector()
        self.system_monitor = SystemMonitor()
        self.experiments = {}
        self.results = {}
        
    async def run_experiment(self, experiment: ChaosExperiment) -> Dict[str, Any]:
        """Run a chaos experiment."""
        logger.info(f"Starting chaos experiment: {experiment.name}")
        
        experiment.status = "running"
        experiment.start_time = datetime.now()
        self.experiments[experiment.id] = experiment
        
        # Start monitoring
        await self.system_monitor.start_monitoring()
        
        try:
            # Inject failure based on type
            failure_id = await self._inject_failure(experiment)
            
            # Wait for experiment duration
            await asyncio.sleep(experiment.duration_seconds)
            
            # Collect results
            results = {
                "experiment_id": experiment.id,
                "status": "completed",
                "start_time": experiment.start_time,
                "end_time": datetime.now(),
                "metrics": self.system_monitor.get_metrics(),
                "alerts": self.system_monitor.get_alerts(),
                "failure_id": failure_id,
                "active_failures": self.failure_injector.get_active_failures()
            }
            
            experiment.status = "completed"
            experiment.end_time = datetime.now()
            experiment.results = results
            
            self.results[experiment.id] = results
            
            logger.info(f"Chaos experiment {experiment.name} completed")
            return results
            
        except Exception as e:
            logger.error(f"Chaos experiment {experiment.name} failed: {str(e)}")
            experiment.status = "failed"
            experiment.end_time = datetime.now()
            raise
            
        finally:
            # Stop monitoring
            await self.system_monitor.stop_monitoring()
            
    async def _inject_failure(self, experiment: ChaosExperiment) -> Optional[str]:
        """Inject failure based on experiment type."""
        if experiment.failure_type == FailureType.NETWORK_LATENCY:
            latency_ms = int(experiment.intensity * 1000)  # Convert to ms
            return await self.failure_injector.inject_network_latency(
                experiment.target_service, latency_ms, experiment.duration_seconds
            )
            
        elif experiment.failure_type == FailureType.SERVICE_CRASH:
            return await self.failure_injector.inject_service_crash(
                experiment.target_service, experiment.intensity
            )
            
        elif experiment.failure_type == FailureType.DATABASE_TIMEOUT:
            timeout_ms = int(experiment.intensity * 5000)  # Convert to ms
            return await self.failure_injector.inject_database_timeout(
                experiment.target_service, timeout_ms, experiment.duration_seconds
            )
            
        else:
            logger.warning(f"Unsupported failure type: {experiment.failure_type}")
            return None
            
    def get_experiment_results(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get results for a specific experiment."""
        return self.results.get(experiment_id)
        
    def get_all_results(self) -> Dict[str, Any]:
        """Get results for all experiments."""
        return self.results.copy()
        
    def get_experiment_status(self, experiment_id: str) -> Optional[str]:
        """Get status of a specific experiment."""
        experiment = self.experiments.get(experiment_id)
        return experiment.status if experiment else None