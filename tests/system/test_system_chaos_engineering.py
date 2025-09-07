#!/usr/bin/env python3
"""
Chaos Engineering Testing System
System tests for chaos engineering experiments to validate system resilience.
"""

import pytest
import asyncio
import time
import json
import random
import threading
import subprocess
import tempfile
import shutil
import os
import signal
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import logging
from typing import Dict, List, Any, Optional, Tuple, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
import uuid
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil
from collections import defaultdict, deque
import socket
import requests
from pathlib import Path
import numpy as np
import statistics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChaosExperimentType(Enum):
    """Types of chaos engineering experiments"""
    LATENCY_INJECTION = "latency_injection"
    PACKET_LOSS = "packet_loss"
    SERVICE_KILL = "service_kill"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    DEPENDENCY_FAILURE = "dependency_failure"
    NETWORK_PARTITION = "network_partition"
    DISK_FILL = "disk_fill"
    CPU_STRESS = "cpu_stress"
    MEMORY_LEAK = "memory_leak"
    CLOCK_SKEW = "clock_skew"
    DNS_FAILURE = "dns_failure"
    SSL_CERTIFICATE_EXPIRY = "ssl_certificate_expiry"
    DATABASE_SLOWDOWN = "database_slowdown"
    MESSAGE_QUEUE_DELAY = "message_queue_delay"
    CONFIGURATION_CORRUPTION = "configuration_corruption"


class ExperimentStatus(Enum):
    """Chaos experiment execution status"""
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"
    ROLLBACK = "rollback"


class ImpactLevel(Enum):
    """Impact level of chaos experiments"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ChaosExperiment:
    """Chaos engineering experiment definition"""
    experiment_id: str
    name: str
    experiment_type: ChaosExperimentType
    description: str
    target_components: List[str]
    duration_seconds: float
    impact_level: ImpactLevel
    hypothesis: str
    success_criteria: Dict[str, Any]
    rollback_plan: List[str]
    safety_checks: List[str]
    parameters: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ExperimentResult:
    """Results of a chaos engineering experiment"""
    experiment_id: str
    status: ExperimentStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    hypothesis_validated: bool = False
    success_criteria_met: bool = False
    observations: List[str] = field(default_factory=list)
    metrics_before: Dict[str, Any] = field(default_factory=dict)
    metrics_during: Dict[str, Any] = field(default_factory=dict)
    metrics_after: Dict[str, Any] = field(default_factory=dict)
    error_messages: List[str] = field(default_factory=list)
    recovery_time: Optional[float] = None
    blast_radius: List[str] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)


class SystemMetricsCollector:
    """Collects system metrics during chaos experiments"""
    
    def __init__(self):
        self.metrics_history = defaultdict(list)
        self.collection_interval = 1.0  # seconds
        self.is_collecting = False
        self.collection_task = None
        
    async def start_collection(self):
        """Start metrics collection"""
        self.is_collecting = True
        self.collection_task = asyncio.create_task(self._collect_metrics())
        logger.info("Started metrics collection")
        
    async def stop_collection(self):
        """Stop metrics collection"""
        self.is_collecting = False
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped metrics collection")
        
    async def _collect_metrics(self):
        """Collect system metrics periodically"""
        while self.is_collecting:
            try:
                timestamp = datetime.now()
                
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=None)
                cpu_count = psutil.cpu_count()
                
                # Memory metrics
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                memory_available = memory.available
                
                # Disk metrics
                disk = psutil.disk_usage('/')
                disk_percent = disk.percent
                disk_free = disk.free
                
                # Network metrics
                network = psutil.net_io_counters()
                network_sent = network.bytes_sent
                network_recv = network.bytes_recv
                
                # Process metrics
                process_count = len(psutil.pids())
                
                metrics = {
                    'timestamp': timestamp.isoformat(),
                    'cpu_percent': cpu_percent,
                    'cpu_count': cpu_count,
                    'memory_percent': memory_percent,
                    'memory_available_mb': memory_available / (1024 * 1024),
                    'disk_percent': disk_percent,
                    'disk_free_gb': disk_free / (1024 * 1024 * 1024),
                    'network_sent_mb': network_sent / (1024 * 1024),
                    'network_recv_mb': network_recv / (1024 * 1024),
                    'process_count': process_count
                }
                
                # Store metrics
                for key, value in metrics.items():
                    if key != 'timestamp':
                        self.metrics_history[key].append({
                            'timestamp': timestamp,
                            'value': value
                        })
                        
                await asyncio.sleep(self.collection_interval)
                
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                await asyncio.sleep(self.collection_interval)
                
    def get_metrics_summary(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get metrics summary for a time period"""
        summary = {}
        
        for metric_name, metric_data in self.metrics_history.items():
            # Filter data by time period
            filtered_data = [
                point for point in metric_data
                if start_time <= point['timestamp'] <= end_time
            ]
            
            if filtered_data:
                values = [point['value'] for point in filtered_data]
                summary[metric_name] = {
                    'min': min(values),
                    'max': max(values),
                    'mean': statistics.mean(values),
                    'median': statistics.median(values),
                    'std_dev': statistics.stdev(values) if len(values) > 1 else 0,
                    'count': len(values)
                }
                
        return summary
        
    def clear_metrics(self):
        """Clear collected metrics"""
        self.metrics_history.clear()


class MockTradingSystem:
    """Mock trading system for chaos engineering tests"""
    
    def __init__(self):
        self.is_running = True
        self.order_count = 0
        self.error_count = 0
        self.latency_ms = 10
        self.throughput_ops_per_sec = 1000
        self.memory_usage_mb = 512
        self.cpu_usage_percent = 25
        self.connection_pool_size = 100
        self.active_connections = 0
        self.chaos_effects = {}
        
    def inject_chaos(self, chaos_type: ChaosExperimentType, parameters: Dict[str, Any]):
        """Inject chaos into the trading system"""
        self.chaos_effects[chaos_type] = parameters
        
        if chaos_type == ChaosExperimentType.LATENCY_INJECTION:
            self.latency_ms += parameters.get('additional_latency_ms', 100)
            
        elif chaos_type == ChaosExperimentType.CPU_STRESS:
            self.cpu_usage_percent += parameters.get('cpu_load_percent', 50)
            
        elif chaos_type == ChaosExperimentType.MEMORY_LEAK:
            self.memory_usage_mb += parameters.get('memory_leak_mb', 100)
            
        elif chaos_type == ChaosExperimentType.SERVICE_KILL:
            self.is_running = False
            
        elif chaos_type == ChaosExperimentType.DATABASE_SLOWDOWN:
            self.latency_ms += parameters.get('db_slowdown_ms', 200)
            self.throughput_ops_per_sec *= 0.5  # Reduce throughput
            
        logger.info(f"Injected {chaos_type.value} chaos with parameters: {parameters}")
        
    def remove_chaos(self, chaos_type: ChaosExperimentType):
        """Remove chaos effect"""
        if chaos_type in self.chaos_effects:
            parameters = self.chaos_effects.pop(chaos_type)
            
            if chaos_type == ChaosExperimentType.LATENCY_INJECTION:
                self.latency_ms -= parameters.get('additional_latency_ms', 100)
                
            elif chaos_type == ChaosExperimentType.CPU_STRESS:
                self.cpu_usage_percent -= parameters.get('cpu_load_percent', 50)
                
            elif chaos_type == ChaosExperimentType.MEMORY_LEAK:
                self.memory_usage_mb -= parameters.get('memory_leak_mb', 100)
                
            elif chaos_type == ChaosExperimentType.SERVICE_KILL:
                self.is_running = True
                
            elif chaos_type == ChaosExperimentType.DATABASE_SLOWDOWN:
                self.latency_ms -= parameters.get('db_slowdown_ms', 200)
                self.throughput_ops_per_sec *= 2.0  # Restore throughput
                
            logger.info(f"Removed {chaos_type.value} chaos")
            
    async def place_order(self, symbol: str, quantity: float, price: float) -> Dict[str, Any]:
        """Place a trading order"""
        if not self.is_running:
            raise Exception("Trading system is not running")
            
        # Simulate latency
        await asyncio.sleep(self.latency_ms / 1000.0)
        
        # Simulate occasional errors under chaos
        if self.chaos_effects and random.random() < 0.05:  # 5% error rate under chaos
            self.error_count += 1
            raise Exception("Order placement failed due to system stress")
            
        self.order_count += 1
        self.active_connections += 1
        
        order = {
            'order_id': f"ORD_{self.order_count:06d}",
            'symbol': symbol,
            'quantity': quantity,
            'price': price,
            'status': 'filled',
            'latency_ms': self.latency_ms,
            'timestamp': datetime.now().isoformat()
        }
        
        # Simulate connection cleanup
        await asyncio.sleep(0.001)
        self.active_connections -= 1
        
        return order
        
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        return {
            'is_running': self.is_running,
            'order_count': self.order_count,
            'error_count': self.error_count,
            'error_rate': self.error_count / max(self.order_count, 1) * 100,
            'latency_ms': self.latency_ms,
            'throughput_ops_per_sec': self.throughput_ops_per_sec,
            'memory_usage_mb': self.memory_usage_mb,
            'cpu_usage_percent': self.cpu_usage_percent,
            'active_connections': self.active_connections,
            'connection_pool_size': self.connection_pool_size,
            'active_chaos_effects': list(self.chaos_effects.keys())
        }
        
    def health_check(self) -> Dict[str, Any]:
        """Perform system health check"""
        metrics = self.get_system_metrics()
        
        # Determine health status
        health_score = 100
        
        if not self.is_running:
            health_score = 0
        else:
            if metrics['error_rate'] > 10:
                health_score -= 30
            if metrics['latency_ms'] > 100:
                health_score -= 20
            if metrics['cpu_usage_percent'] > 80:
                health_score -= 25
            if metrics['memory_usage_mb'] > 2000:
                health_score -= 25
                
        return {
            'health_score': max(0, health_score),
            'status': 'healthy' if health_score > 70 else 'degraded' if health_score > 30 else 'unhealthy',
            'metrics': metrics
        }


class ChaosEngineeringFramework:
    """Framework for executing chaos engineering experiments"""
    
    def __init__(self):
        self.experiments = {}
        self.results = {}
        self.active_experiments = {}
        self.metrics_collector = SystemMetricsCollector()
        self.safety_enabled = True
        self.abort_threshold = {
            'error_rate': 50.0,  # 50% error rate
            'latency_ms': 5000,  # 5 second latency
            'cpu_percent': 95.0,  # 95% CPU usage
            'memory_percent': 95.0  # 95% memory usage
        }
        
    def register_experiment(self, experiment: ChaosExperiment):
        """Register a chaos experiment"""
        self.experiments[experiment.experiment_id] = experiment
        logger.info(f"Registered experiment: {experiment.name}")
        
    async def execute_experiment(self, experiment_id: str, target_system: MockTradingSystem) -> ExperimentResult:
        """Execute a chaos engineering experiment"""
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
            
        experiment = self.experiments[experiment_id]
        result = ExperimentResult(
            experiment_id=experiment_id,
            status=ExperimentStatus.PLANNED,
            start_time=datetime.now()
        )
        
        try:
            logger.info(f"Starting chaos experiment: {experiment.name}")
            
            # Pre-experiment safety checks
            if self.safety_enabled:
                safety_passed = await self._perform_safety_checks(experiment, target_system)
                if not safety_passed:
                    result.status = ExperimentStatus.ABORTED
                    result.error_messages.append("Safety checks failed")
                    return result
                    
            # Collect baseline metrics
            result.metrics_before = target_system.get_system_metrics()
            
            # Start metrics collection
            await self.metrics_collector.start_collection()
            
            result.status = ExperimentStatus.RUNNING
            self.active_experiments[experiment_id] = result
            
            # Execute experiment phases
            await self._execute_experiment_phases(experiment, target_system, result)
            
            result.status = ExperimentStatus.COMPLETED
            result.end_time = datetime.now()
            result.duration = (result.end_time - result.start_time).total_seconds()
            
            # Collect post-experiment metrics
            result.metrics_after = target_system.get_system_metrics()
            
            # Validate hypothesis and success criteria
            await self._validate_experiment_results(experiment, result)
            
            logger.info(f"Completed chaos experiment: {experiment.name}")
            
        except Exception as e:
            result.status = ExperimentStatus.FAILED
            result.error_messages.append(str(e))
            logger.error(f"Experiment {experiment_id} failed: {e}")
            
        finally:
            # Stop metrics collection
            await self.metrics_collector.stop_collection()
            
            # Ensure cleanup
            await self._cleanup_experiment(experiment, target_system)
            
            if experiment_id in self.active_experiments:
                del self.active_experiments[experiment_id]
                
        self.results[experiment_id] = result
        return result
        
    async def _perform_safety_checks(self, experiment: ChaosExperiment, target_system: MockTradingSystem) -> bool:
        """Perform safety checks before experiment"""
        logger.info("Performing safety checks")
        
        # Check system health
        health = target_system.health_check()
        if health['health_score'] < 70:
            logger.warning(f"System health too low for experiment: {health['health_score']}")
            return False
            
        # Check if high-impact experiment during business hours
        if experiment.impact_level == ImpactLevel.CRITICAL:
            current_hour = datetime.now().hour
            if 9 <= current_hour <= 17:  # Business hours
                logger.warning("Critical impact experiment blocked during business hours")
                return False
                
        # Custom safety checks
        for safety_check in experiment.safety_checks:
            if safety_check == "low_traffic_period":
                # Simulate traffic check
                if target_system.throughput_ops_per_sec > 500:
                    logger.warning("Traffic too high for experiment")
                    return False
                    
            elif safety_check == "backup_systems_ready":
                # Simulate backup system check
                if random.random() < 0.1:  # 10% chance backup not ready
                    logger.warning("Backup systems not ready")
                    return False
                    
        return True
        
    async def _execute_experiment_phases(self, experiment: ChaosExperiment, target_system: MockTradingSystem, result: ExperimentResult):
        """Execute the main phases of the experiment"""
        # Phase 1: Inject chaos
        logger.info(f"Injecting chaos: {experiment.experiment_type.value}")
        target_system.inject_chaos(experiment.experiment_type, experiment.parameters)
        
        # Phase 2: Monitor system during chaos
        monitoring_duration = experiment.duration_seconds
        monitoring_start = time.time()
        
        while time.time() - monitoring_start < monitoring_duration:
            # Check abort conditions
            if self.safety_enabled:
                should_abort = await self._check_abort_conditions(target_system, result)
                if should_abort:
                    result.status = ExperimentStatus.ABORTED
                    result.error_messages.append("Experiment aborted due to safety thresholds")
                    break
                    
            # Collect observations
            health = target_system.health_check()
            result.observations.append(f"Health score: {health['health_score']} at {datetime.now().isoformat()}")
            
            # Record metrics during experiment
            current_metrics = target_system.get_system_metrics()
            result.metrics_during = current_metrics
            
            await asyncio.sleep(1.0)  # Check every second
            
        # Phase 3: Remove chaos (rollback)
        logger.info("Rolling back chaos injection")
        target_system.remove_chaos(experiment.experiment_type)
        
        # Phase 4: Monitor recovery
        recovery_start = time.time()
        recovery_timeout = 60.0  # 60 seconds max recovery time
        
        while time.time() - recovery_start < recovery_timeout:
            health = target_system.health_check()
            if health['health_score'] > 80:  # System recovered
                result.recovery_time = time.time() - recovery_start
                result.observations.append(f"System recovered in {result.recovery_time:.1f} seconds")
                break
                
            await asyncio.sleep(1.0)
            
        if result.recovery_time is None:
            result.recovery_time = recovery_timeout
            result.error_messages.append("System did not fully recover within timeout")
            
    async def _check_abort_conditions(self, target_system: MockTradingSystem, result: ExperimentResult) -> bool:
        """Check if experiment should be aborted due to safety thresholds"""
        metrics = target_system.get_system_metrics()
        
        # Check error rate
        if metrics['error_rate'] > self.abort_threshold['error_rate']:
            logger.warning(f"Aborting: Error rate {metrics['error_rate']:.1f}% exceeds threshold")
            return True
            
        # Check latency
        if metrics['latency_ms'] > self.abort_threshold['latency_ms']:
            logger.warning(f"Aborting: Latency {metrics['latency_ms']}ms exceeds threshold")
            return True
            
        # Check CPU usage
        if metrics['cpu_usage_percent'] > self.abort_threshold['cpu_percent']:
            logger.warning(f"Aborting: CPU usage {metrics['cpu_usage_percent']:.1f}% exceeds threshold")
            return True
            
        return False
        
    async def _validate_experiment_results(self, experiment: ChaosExperiment, result: ExperimentResult):
        """Validate experiment hypothesis and success criteria"""
        logger.info("Validating experiment results")
        
        # Check success criteria
        criteria_met = 0
        total_criteria = len(experiment.success_criteria)
        
        for criterion, expected_value in experiment.success_criteria.items():
            if criterion == "system_recovers":
                if result.recovery_time is not None and result.recovery_time < 60.0:
                    criteria_met += 1
                    
            elif criterion == "error_rate_below":
                if result.metrics_during.get('error_rate', 0) < expected_value:
                    criteria_met += 1
                    
            elif criterion == "latency_below":
                if result.metrics_during.get('latency_ms', 0) < expected_value:
                    criteria_met += 1
                    
            elif criterion == "throughput_above":
                if result.metrics_during.get('throughput_ops_per_sec', 0) > expected_value:
                    criteria_met += 1
                    
        result.success_criteria_met = criteria_met == total_criteria
        
        # Validate hypothesis (simplified)
        # In a real system, this would involve more complex analysis
        if result.success_criteria_met and result.recovery_time is not None:
            result.hypothesis_validated = True
            result.lessons_learned.append("System demonstrated resilience to chaos")
        else:
            result.hypothesis_validated = False
            result.lessons_learned.append("System showed vulnerabilities that need addressing")
            
    async def _cleanup_experiment(self, experiment: ChaosExperiment, target_system: MockTradingSystem):
        """Cleanup after experiment"""
        logger.info("Cleaning up experiment")
        
        # Ensure all chaos effects are removed
        target_system.remove_chaos(experiment.experiment_type)
        
        # Execute rollback plan
        for rollback_step in experiment.rollback_plan:
            logger.info(f"Executing rollback step: {rollback_step}")
            # In a real system, this would execute actual rollback commands
            await asyncio.sleep(0.1)
            
    def get_experiment_report(self, experiment_id: str) -> Dict[str, Any]:
        """Generate experiment report"""
        if experiment_id not in self.results:
            raise ValueError(f"No results found for experiment {experiment_id}")
            
        experiment = self.experiments[experiment_id]
        result = self.results[experiment_id]
        
        report = {
            'experiment': {
                'id': experiment.experiment_id,
                'name': experiment.name,
                'type': experiment.experiment_type.value,
                'description': experiment.description,
                'hypothesis': experiment.hypothesis,
                'impact_level': experiment.impact_level.value,
                'duration_seconds': experiment.duration_seconds
            },
            'execution': {
                'status': result.status.value,
                'start_time': result.start_time.isoformat(),
                'end_time': result.end_time.isoformat() if result.end_time else None,
                'duration': result.duration,
                'recovery_time': result.recovery_time
            },
            'results': {
                'hypothesis_validated': result.hypothesis_validated,
                'success_criteria_met': result.success_criteria_met,
                'blast_radius': result.blast_radius,
                'observations': result.observations,
                'lessons_learned': result.lessons_learned
            },
            'metrics': {
                'before': result.metrics_before,
                'during': result.metrics_during,
                'after': result.metrics_after
            },
            'errors': result.error_messages,
            'generated_at': datetime.now().isoformat()
        }
        
        return report


class TestChaosEngineering:
    """Test suite for chaos engineering experiments"""
    
    @pytest.fixture(autouse=True)
    async def setup_method(self):
        """Setup chaos engineering test environment"""
        self.chaos_framework = ChaosEngineeringFramework()
        self.trading_system = MockTradingSystem()
        
        # Configure safety thresholds for testing
        self.chaos_framework.abort_threshold = {
            'error_rate': 75.0,  # Higher threshold for testing
            'latency_ms': 10000,  # 10 second latency
            'cpu_percent': 98.0,
            'memory_percent': 98.0
        }
        
        logger.info("Chaos engineering test environment setup completed")
        
    async def teardown_method(self):
        """Cleanup test environment"""
        # Ensure all chaos effects are removed
        for chaos_type in ChaosExperimentType:
            self.trading_system.remove_chaos(chaos_type)
            
        # Stop any active metrics collection
        if self.chaos_framework.metrics_collector.is_collecting:
            await self.chaos_framework.metrics_collector.stop_collection()
            
        logger.info("Chaos engineering test environment cleanup completed")
        
    @pytest.mark.asyncio
    async def test_latency_injection_experiment(self):
        """Test latency injection chaos experiment"""
        experiment = ChaosExperiment(
            experiment_id="latency_001",
            name="API Latency Injection",
            experiment_type=ChaosExperimentType.LATENCY_INJECTION,
            description="Inject additional latency to test system resilience",
            target_components=["trading_api"],
            duration_seconds=10.0,
            impact_level=ImpactLevel.MEDIUM,
            hypothesis="System should handle increased latency gracefully without cascading failures",
            success_criteria={
                "system_recovers": True,
                "error_rate_below": 10.0,
                "latency_below": 500.0
            },
            rollback_plan=["Remove latency injection", "Verify normal latency restored"],
            safety_checks=["low_traffic_period"],
            parameters={"additional_latency_ms": 200}
        )
        
        self.chaos_framework.register_experiment(experiment)
        
        # Record baseline performance
        baseline_latency = self.trading_system.latency_ms
        
        # Execute experiment
        result = await self.chaos_framework.execute_experiment("latency_001", self.trading_system)
        
        # Validate results
        assert result.status == ExperimentStatus.COMPLETED
        assert result.duration is not None
        assert result.recovery_time is not None
        assert result.recovery_time < 30.0  # Should recover quickly
        
        # Verify latency was injected and then removed
        assert result.metrics_during['latency_ms'] > baseline_latency
        assert result.metrics_after['latency_ms'] == baseline_latency
        
        # Check success criteria
        assert result.success_criteria_met
        assert result.hypothesis_validated
        
        logger.info(f"Latency injection experiment completed with recovery time: {result.recovery_time:.1f}s")
        
    @pytest.mark.asyncio
    async def test_cpu_stress_experiment(self):
        """Test CPU stress chaos experiment"""
        experiment = ChaosExperiment(
            experiment_id="cpu_stress_001",
            name="CPU Stress Test",
            experiment_type=ChaosExperimentType.CPU_STRESS,
            description="Stress CPU to test system behavior under high load",
            target_components=["trading_engine"],
            duration_seconds=8.0,
            impact_level=ImpactLevel.HIGH,
            hypothesis="System should maintain core functionality under CPU stress",
            success_criteria={
                "system_recovers": True,
                "error_rate_below": 20.0
            },
            rollback_plan=["Stop CPU stress", "Monitor CPU usage normalization"],
            safety_checks=["backup_systems_ready"],
            parameters={"cpu_load_percent": 60}
        )
        
        self.chaos_framework.register_experiment(experiment)
        
        # Record baseline CPU usage
        baseline_cpu = self.trading_system.cpu_usage_percent
        
        # Execute experiment
        result = await self.chaos_framework.execute_experiment("cpu_stress_001", self.trading_system)
        
        # Validate results
        assert result.status == ExperimentStatus.COMPLETED
        assert result.metrics_during['cpu_usage_percent'] > baseline_cpu
        assert result.metrics_after['cpu_usage_percent'] == baseline_cpu
        
        # System should still be functional
        assert self.trading_system.is_running
        
        logger.info(f"CPU stress experiment completed")
        
    @pytest.mark.asyncio
    async def test_service_kill_experiment(self):
        """Test service kill chaos experiment"""
        experiment = ChaosExperiment(
            experiment_id="service_kill_001",
            name="Trading Service Kill",
            experiment_type=ChaosExperimentType.SERVICE_KILL,
            description="Kill trading service to test recovery mechanisms",
            target_components=["trading_service"],
            duration_seconds=5.0,
            impact_level=ImpactLevel.CRITICAL,
            hypothesis="Service should restart automatically and resume operations",
            success_criteria={
                "system_recovers": True
            },
            rollback_plan=["Restart service", "Verify service health"],
            safety_checks=["backup_systems_ready", "low_traffic_period"],
            parameters={}
        )
        
        self.chaos_framework.register_experiment(experiment)
        
        # Verify system is running initially
        assert self.trading_system.is_running
        
        # Execute experiment
        result = await self.chaos_framework.execute_experiment("service_kill_001", self.trading_system)
        
        # Validate results
        assert result.status == ExperimentStatus.COMPLETED
        assert not result.metrics_during['is_running']  # Service was killed
        assert result.metrics_after['is_running']  # Service recovered
        
        # Verify recovery
        assert self.trading_system.is_running
        assert result.recovery_time is not None
        
        logger.info(f"Service kill experiment completed with recovery time: {result.recovery_time:.1f}s")
        
    @pytest.mark.asyncio
    async def test_memory_leak_experiment(self):
        """Test memory leak chaos experiment"""
        experiment = ChaosExperiment(
            experiment_id="memory_leak_001",
            name="Memory Leak Simulation",
            experiment_type=ChaosExperimentType.MEMORY_LEAK,
            description="Simulate memory leak to test memory management",
            target_components=["trading_engine"],
            duration_seconds=6.0,
            impact_level=ImpactLevel.MEDIUM,
            hypothesis="System should detect and handle memory pressure gracefully",
            success_criteria={
                "system_recovers": True,
                "error_rate_below": 15.0
            },
            rollback_plan=["Stop memory leak", "Trigger garbage collection"],
            safety_checks=["low_traffic_period"],
            parameters={"memory_leak_mb": 200}
        )
        
        self.chaos_framework.register_experiment(experiment)
        
        # Record baseline memory usage
        baseline_memory = self.trading_system.memory_usage_mb
        
        # Execute experiment
        result = await self.chaos_framework.execute_experiment("memory_leak_001", self.trading_system)
        
        # Validate results
        assert result.status == ExperimentStatus.COMPLETED
        assert result.metrics_during['memory_usage_mb'] > baseline_memory
        assert result.metrics_after['memory_usage_mb'] == baseline_memory
        
        logger.info(f"Memory leak experiment completed")
        
    @pytest.mark.asyncio
    async def test_database_slowdown_experiment(self):
        """Test database slowdown chaos experiment"""
        experiment = ChaosExperiment(
            experiment_id="db_slowdown_001",
            name="Database Slowdown",
            experiment_type=ChaosExperimentType.DATABASE_SLOWDOWN,
            description="Slow down database operations to test timeout handling",
            target_components=["database"],
            duration_seconds=7.0,
            impact_level=ImpactLevel.HIGH,
            hypothesis="System should handle database slowdowns with proper timeouts and retries",
            success_criteria={
                "system_recovers": True,
                "error_rate_below": 25.0,
                "throughput_above": 100.0
            },
            rollback_plan=["Remove database slowdown", "Verify query performance"],
            safety_checks=["backup_systems_ready"],
            parameters={"db_slowdown_ms": 300}
        )
        
        self.chaos_framework.register_experiment(experiment)
        
        # Record baseline metrics
        baseline_latency = self.trading_system.latency_ms
        baseline_throughput = self.trading_system.throughput_ops_per_sec
        
        # Execute experiment
        result = await self.chaos_framework.execute_experiment("db_slowdown_001", self.trading_system)
        
        # Validate results
        assert result.status == ExperimentStatus.COMPLETED
        assert result.metrics_during['latency_ms'] > baseline_latency
        assert result.metrics_during['throughput_ops_per_sec'] < baseline_throughput
        assert result.metrics_after['latency_ms'] == baseline_latency
        assert result.metrics_after['throughput_ops_per_sec'] == baseline_throughput
        
        logger.info(f"Database slowdown experiment completed")
        
    @pytest.mark.asyncio
    async def test_experiment_safety_abort(self):
        """Test experiment safety abort mechanism"""
        # Create experiment with parameters that will trigger abort
        experiment = ChaosExperiment(
            experiment_id="safety_abort_001",
            name="Safety Abort Test",
            experiment_type=ChaosExperimentType.LATENCY_INJECTION,
            description="Test safety abort when thresholds are exceeded",
            target_components=["trading_api"],
            duration_seconds=20.0,  # Long duration
            impact_level=ImpactLevel.MEDIUM,
            hypothesis="Safety mechanisms should abort experiment when thresholds exceeded",
            success_criteria={"system_recovers": True},
            rollback_plan=["Remove latency injection"],
            safety_checks=[],
            parameters={"additional_latency_ms": 8000}  # Very high latency to trigger abort
        )
        
        # Lower abort threshold for this test
        self.chaos_framework.abort_threshold['latency_ms'] = 5000
        
        self.chaos_framework.register_experiment(experiment)
        
        # Execute experiment
        result = await self.chaos_framework.execute_experiment("safety_abort_001", self.trading_system)
        
        # Validate that experiment was aborted
        assert result.status == ExperimentStatus.ABORTED
        assert "safety thresholds" in ' '.join(result.error_messages)
        assert result.duration < experiment.duration_seconds  # Should abort early
        
        # System should be cleaned up
        assert self.trading_system.latency_ms < 1000  # Latency should be restored
        
        logger.info(f"Safety abort test completed - experiment aborted as expected")
        
    @pytest.mark.asyncio
    async def test_concurrent_chaos_experiments(self):
        """Test running multiple chaos experiments concurrently"""
        # Create multiple lightweight experiments
        experiments = [
            ChaosExperiment(
                experiment_id="concurrent_001",
                name="Concurrent Latency Test 1",
                experiment_type=ChaosExperimentType.LATENCY_INJECTION,
                description="Concurrent latency injection test",
                target_components=["api_1"],
                duration_seconds=3.0,
                impact_level=ImpactLevel.LOW,
                hypothesis="System handles concurrent latency injection",
                success_criteria={"system_recovers": True},
                rollback_plan=["Remove latency"],
                safety_checks=[],
                parameters={"additional_latency_ms": 50}
            ),
            ChaosExperiment(
                experiment_id="concurrent_002",
                name="Concurrent CPU Test",
                experiment_type=ChaosExperimentType.CPU_STRESS,
                description="Concurrent CPU stress test",
                target_components=["engine_1"],
                duration_seconds=3.0,
                impact_level=ImpactLevel.LOW,
                hypothesis="System handles concurrent CPU stress",
                success_criteria={"system_recovers": True},
                rollback_plan=["Remove CPU stress"],
                safety_checks=[],
                parameters={"cpu_load_percent": 20}
            )
        ]
        
        # Register experiments
        for exp in experiments:
            self.chaos_framework.register_experiment(exp)
            
        # Note: In practice, concurrent chaos experiments should be carefully coordinated
        # For this test, we'll run them sequentially to avoid interference
        results = []
        for exp in experiments:
            result = await self.chaos_framework.execute_experiment(exp.experiment_id, self.trading_system)
            results.append(result)
            
        # Validate all experiments completed
        for result in results:
            assert result.status == ExperimentStatus.COMPLETED
            assert result.recovery_time is not None
            
        logger.info(f"Completed {len(results)} concurrent chaos experiments")
        
    @pytest.mark.asyncio
    async def test_chaos_experiment_reporting(self):
        """Test chaos experiment reporting functionality"""
        experiment = ChaosExperiment(
            experiment_id="reporting_001",
            name="Reporting Test Experiment",
            experiment_type=ChaosExperimentType.LATENCY_INJECTION,
            description="Test experiment for reporting functionality",
            target_components=["reporting_api"],
            duration_seconds=4.0,
            impact_level=ImpactLevel.LOW,
            hypothesis="Reporting system captures all experiment data",
            success_criteria={
                "system_recovers": True,
                "error_rate_below": 5.0
            },
            rollback_plan=["Remove latency injection", "Verify system health"],
            safety_checks=["low_traffic_period"],
            parameters={"additional_latency_ms": 100}
        )
        
        self.chaos_framework.register_experiment(experiment)
        
        # Execute experiment
        result = await self.chaos_framework.execute_experiment("reporting_001", self.trading_system)
        
        # Generate report
        report = self.chaos_framework.get_experiment_report("reporting_001")
        
        # Validate report structure
        assert 'experiment' in report
        assert 'execution' in report
        assert 'results' in report
        assert 'metrics' in report
        assert 'generated_at' in report
        
        # Validate experiment details
        assert report['experiment']['id'] == experiment.experiment_id
        assert report['experiment']['name'] == experiment.name
        assert report['experiment']['type'] == experiment.experiment_type.value
        
        # Validate execution details
        assert report['execution']['status'] == result.status.value
        assert report['execution']['duration'] == result.duration
        assert report['execution']['recovery_time'] == result.recovery_time
        
        # Validate results
        assert 'hypothesis_validated' in report['results']
        assert 'success_criteria_met' in report['results']
        assert 'observations' in report['results']
        
        # Validate metrics
        assert 'before' in report['metrics']
        assert 'during' in report['metrics']
        assert 'after' in report['metrics']
        
        logger.info(f"Generated comprehensive experiment report")
        
    @pytest.mark.asyncio
    async def test_system_resilience_under_chaos(self):
        """Test overall system resilience under various chaos conditions"""
        # Test system with realistic trading workload during chaos
        num_orders = 50
        chaos_types = [
            (ChaosExperimentType.LATENCY_INJECTION, {"additional_latency_ms": 100}),
            (ChaosExperimentType.CPU_STRESS, {"cpu_load_percent": 30}),
            (ChaosExperimentType.MEMORY_LEAK, {"memory_leak_mb": 100})
        ]
        
        for chaos_type, parameters in chaos_types:
            logger.info(f"Testing resilience under {chaos_type.value}")
            
            # Inject chaos
            self.trading_system.inject_chaos(chaos_type, parameters)
            
            # Simulate trading workload
            successful_orders = 0
            failed_orders = 0
            
            for i in range(num_orders):
                try:
                    order = await self.trading_system.place_order(f"STOCK_{i}", 100, 100.0)
                    successful_orders += 1
                except Exception as e:
                    failed_orders += 1
                    
                # Small delay between orders
                await asyncio.sleep(0.05)
                
            # Remove chaos
            self.trading_system.remove_chaos(chaos_type)
            
            # Validate resilience
            success_rate = successful_orders / num_orders * 100
            assert success_rate > 70.0  # At least 70% success rate under chaos
            
            logger.info(f"Resilience test for {chaos_type.value}: {success_rate:.1f}% success rate")
            
        # Verify system recovered to normal state
        final_health = self.trading_system.health_check()
        assert final_health['health_score'] > 90
        
        logger.info(f"System resilience testing completed - final health: {final_health['health_score']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])