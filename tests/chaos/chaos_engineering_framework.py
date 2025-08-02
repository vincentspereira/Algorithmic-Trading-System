#!/usr/bin/env python3
"""
Chaos Engineering Framework for Nautilus Trader Engine
Implements failure injection testing, resilience validation, and recovery testing.
"""

import asyncio
import random
import time
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
import psutil
import aiohttp
import websockets
from unittest.mock import patch, Mock
import threading
import signal
import subprocess
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FailureType(Enum):
    """Types of failures that can be injected"""
    NETWORK_LATENCY = "network_latency"
    NETWORK_PARTITION = "network_partition"
    SERVICE_CRASH = "service_crash"
    DATABASE_FAILURE = "database_failure"
    MEMORY_PRESSURE = "memory_pressure"
    CPU_SPIKE = "cpu_spike"
    DISK_FULL = "disk_full"
    API_TIMEOUT = "api_timeout"
    MESSAGE_LOSS = "message_loss"
    DEPENDENCY_FAILURE = "dependency_failure"

class ChaosExperimentStatus(Enum):
    """Status of chaos experiments"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"

@dataclass
class ChaosExperiment:
    """Represents a chaos engineering experiment"""
    experiment_id: str
    name: str
    description: str
    failure_type: FailureType
    target_component: str
    duration: int  # seconds
    intensity: float  # 0.0 to 1.0
    parameters: Dict[str, Any]
    hypothesis: str
    success_criteria: List[str]
    rollback_strategy: str
    status: ChaosExperimentStatus = ChaosExperimentStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    results: Optional[Dict[str, Any]] = None

@dataclass
class SystemMetrics:
    """System metrics captured during experiments"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    network_latency: float
    response_time: float
    error_rate: float
    throughput: float
    active_connections: int
    custom_metrics: Dict[str, float]

class FailureInjector:
    """Injects various types of failures into the system"""
    
    def __init__(self):
        self.active_failures = {}
        self.original_functions = {}
        
    async def inject_network_latency(self, target: str, latency_ms: int, duration: int):
        """Inject network latency"""
        logger.info(f"Injecting {latency_ms}ms network latency to {target} for {duration}s")
        
        # Store original aiohttp connector
        original_connector = aiohttp.TCPConnector
        
        class LatencyConnector(aiohttp.TCPConnector):
            async def _create_connection(self, req, traces, timeout):
                await asyncio.sleep(latency_ms / 1000.0)  # Convert to seconds
                return await super()._create_connection(req, traces, timeout)
        
        # Patch aiohttp connector
        aiohttp.TCPConnector = LatencyConnector
        self.active_failures[f"network_latency_{target}"] = {
            'type': 'network_latency',
            'original': original_connector,
            'start_time': datetime.now()
        }
        
        # Schedule restoration
        await asyncio.sleep(duration)
        await self.restore_network_latency(target)
    
    async def restore_network_latency(self, target: str):
        """Restore normal network latency"""
        failure_key = f"network_latency_{target}"
        if failure_key in self.active_failures:
            original_connector = self.active_failures[failure_key]['original']
            aiohttp.TCPConnector = original_connector
            del self.active_failures[failure_key]
            logger.info(f"Restored normal network latency for {target}")
    
    async def inject_network_partition(self, target: str, duration: int):
        """Simulate network partition"""
        logger.info(f"Injecting network partition to {target} for {duration}s")
        
        # Mock network calls to fail
        original_session_request = aiohttp.ClientSession.request
        
        async def failing_request(self, method, url, **kwargs):
            if target in str(url):
                raise aiohttp.ClientConnectorError(
                    connection_key=None,
                    os_error=OSError("Network partition simulated")
                )
            return await original_session_request(self, method, url, **kwargs)
        
        aiohttp.ClientSession.request = failing_request
        self.active_failures[f"network_partition_{target}"] = {
            'type': 'network_partition',
            'original': original_session_request,
            'start_time': datetime.now()
        }
        
        await asyncio.sleep(duration)
        await self.restore_network_partition(target)
    
    async def restore_network_partition(self, target: str):
        """Restore network connectivity"""
        failure_key = f"network_partition_{target}"
        if failure_key in self.active_failures:
            original_request = self.active_failures[failure_key]['original']
            aiohttp.ClientSession.request = original_request
            del self.active_failures[failure_key]
            logger.info(f"Restored network connectivity to {target}")
    
    async def inject_service_crash(self, service_name: str, duration: int):
        """Simulate service crash"""
        logger.info(f"Simulating crash of {service_name} for {duration}s")
        
        # This would integrate with actual service management
        # For now, we'll simulate by making service calls fail
        crash_key = f"service_crash_{service_name}"
        self.active_failures[crash_key] = {
            'type': 'service_crash',
            'start_time': datetime.now(),
            'service': service_name
        }
        
        await asyncio.sleep(duration)
        await self.restore_service(service_name)
    
    async def restore_service(self, service_name: str):
        """Restore crashed service"""
        crash_key = f"service_crash_{service_name}"
        if crash_key in self.active_failures:
            del self.active_failures[crash_key]
            logger.info(f"Restored service {service_name}")
    
    async def inject_memory_pressure(self, target_usage: float, duration: int):
        """Inject memory pressure"""
        logger.info(f"Injecting memory pressure to {target_usage*100}% for {duration}s")
        
        # Allocate memory to create pressure
        memory_hog = []
        target_bytes = int(psutil.virtual_memory().total * target_usage)
        chunk_size = 1024 * 1024  # 1MB chunks
        
        try:
            while len(memory_hog) * chunk_size < target_bytes:
                memory_hog.append(b'0' * chunk_size)
                await asyncio.sleep(0.01)  # Yield control
            
            self.active_failures['memory_pressure'] = {
                'type': 'memory_pressure',
                'memory_hog': memory_hog,
                'start_time': datetime.now()
            }
            
            await asyncio.sleep(duration)
            
        finally:
            # Clean up memory
            if 'memory_pressure' in self.active_failures:
                del self.active_failures['memory_pressure']['memory_hog']
                del self.active_failures['memory_pressure']
                logger.info("Released memory pressure")
    
    async def inject_cpu_spike(self, target_usage: float, duration: int):
        """Inject CPU spike"""
        logger.info(f"Injecting CPU spike to {target_usage*100}% for {duration}s")
        
        def cpu_burner():
            end_time = time.time() + duration
            while time.time() < end_time:
                # Busy wait to consume CPU
                for _ in range(1000000):
                    pass
                time.sleep(0.01 * (1 - target_usage))  # Control intensity
        
        # Start CPU burning threads
        num_threads = int(psutil.cpu_count() * target_usage)
        threads = []
        
        for _ in range(num_threads):
            thread = threading.Thread(target=cpu_burner)
            thread.start()
            threads.append(thread)
        
        self.active_failures['cpu_spike'] = {
            'type': 'cpu_spike',
            'threads': threads,
            'start_time': datetime.now()
        }
        
        # Wait for threads to complete
        for thread in threads:
            thread.join()
        
        if 'cpu_spike' in self.active_failures:
            del self.active_failures['cpu_spike']
            logger.info("CPU spike completed")
    
    async def inject_api_timeout(self, api_endpoint: str, timeout_ms: int, duration: int):
        """Inject API timeouts"""
        logger.info(f"Injecting {timeout_ms}ms timeout to {api_endpoint} for {duration}s")
        
        # Mock API calls to timeout
        original_timeout = aiohttp.ClientTimeout.total
        
        class TimeoutClientTimeout(aiohttp.ClientTimeout):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                if api_endpoint in str(kwargs.get('url', '')):
                    self.total = timeout_ms / 1000.0
        
        aiohttp.ClientTimeout = TimeoutClientTimeout
        self.active_failures[f"api_timeout_{api_endpoint}"] = {
            'type': 'api_timeout',
            'original': original_timeout,
            'start_time': datetime.now()
        }
        
        await asyncio.sleep(duration)
        await self.restore_api_timeout(api_endpoint)
    
    async def restore_api_timeout(self, api_endpoint: str):
        """Restore normal API timeouts"""
        failure_key = f"api_timeout_{api_endpoint}"
        if failure_key in self.active_failures:
            # Restore original timeout behavior
            del self.active_failures[failure_key]
            logger.info(f"Restored normal API timeout for {api_endpoint}")
    
    async def cleanup_all_failures(self):
        """Clean up all active failures"""
        logger.info("Cleaning up all active failures")
        
        for failure_key, failure_info in list(self.active_failures.items()):
            failure_type = failure_info['type']
            
            if failure_type == 'network_latency':
                target = failure_key.split('_')[-1]
                await self.restore_network_latency(target)
            elif failure_type == 'network_partition':
                target = failure_key.split('_')[-1]
                await self.restore_network_partition(target)
            elif failure_type == 'service_crash':
                service = failure_info['service']
                await self.restore_service(service)
            # Add other cleanup methods as needed
        
        self.active_failures.clear()

class SystemMonitor:
    """Monitors system metrics during chaos experiments"""
    
    def __init__(self):
        self.metrics_history = []
        self.monitoring_active = False
        self.custom_metric_collectors = {}
    
    def add_custom_metric_collector(self, name: str, collector: Callable[[], float]):
        """Add custom metric collector"""
        self.custom_metric_collectors[name] = collector
    
    async def start_monitoring(self, interval: float = 1.0):
        """Start monitoring system metrics"""
        self.monitoring_active = True
        logger.info("Started system monitoring")
        
        while self.monitoring_active:
            metrics = await self.collect_metrics()
            self.metrics_history.append(metrics)
            await asyncio.sleep(interval)
    
    def stop_monitoring(self):
        """Stop monitoring system metrics"""
        self.monitoring_active = False
        logger.info("Stopped system monitoring")
    
    async def collect_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        # System metrics
        cpu_usage = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        memory_usage = memory.percent
        
        # Network metrics (simplified)
        network_latency = await self.measure_network_latency()
        
        # Application metrics (would integrate with actual monitoring)
        response_time = await self.measure_response_time()
        error_rate = await self.measure_error_rate()
        throughput = await self.measure_throughput()
        active_connections = await self.count_active_connections()
        
        # Custom metrics
        custom_metrics = {}
        for name, collector in self.custom_metric_collectors.items():
            try:
                custom_metrics[name] = collector()
            except Exception as e:
                logger.warning(f"Failed to collect custom metric {name}: {e}")
                custom_metrics[name] = 0.0
        
        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            network_latency=network_latency,
            response_time=response_time,
            error_rate=error_rate,
            throughput=throughput,
            active_connections=active_connections,
            custom_metrics=custom_metrics
        )
    
    async def measure_network_latency(self) -> float:
        """Measure network latency to a test endpoint"""
        try:
            start_time = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.get('http://httpbin.org/get', timeout=aiohttp.ClientTimeout(total=5)) as response:
                    await response.text()
            end_time = time.time()
            return (end_time - start_time) * 1000  # Convert to milliseconds
        except Exception:
            return 999.0  # High latency indicates failure
    
    async def measure_response_time(self) -> float:
        """Measure application response time"""
        # This would integrate with actual application endpoints
        # For now, return a simulated value
        return random.uniform(10, 100)  # milliseconds
    
    async def measure_error_rate(self) -> float:
        """Measure application error rate"""
        # This would integrate with actual error tracking
        # For now, return a simulated value
        return random.uniform(0, 5)  # percentage
    
    async def measure_throughput(self) -> float:
        """Measure application throughput"""
        # This would integrate with actual throughput metrics
        # For now, return a simulated value
        return random.uniform(100, 1000)  # requests per second
    
    async def count_active_connections(self) -> int:
        """Count active network connections"""
        try:
            connections = psutil.net_connections()
            return len([conn for conn in connections if conn.status == 'ESTABLISHED'])
        except Exception:
            return 0
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of collected metrics"""
        if not self.metrics_history:
            return {}
        
        # Calculate averages, mins, maxes
        cpu_values = [m.cpu_usage for m in self.metrics_history]
        memory_values = [m.memory_usage for m in self.metrics_history]
        latency_values = [m.network_latency for m in self.metrics_history]
        response_values = [m.response_time for m in self.metrics_history]
        error_values = [m.error_rate for m in self.metrics_history]
        
        return {
            'duration': len(self.metrics_history),
            'cpu_usage': {
                'avg': sum(cpu_values) / len(cpu_values),
                'min': min(cpu_values),
                'max': max(cpu_values)
            },
            'memory_usage': {
                'avg': sum(memory_values) / len(memory_values),
                'min': min(memory_values),
                'max': max(memory_values)
            },
            'network_latency': {
                'avg': sum(latency_values) / len(latency_values),
                'min': min(latency_values),
                'max': max(latency_values)
            },
            'response_time': {
                'avg': sum(response_values) / len(response_values),
                'min': min(response_values),
                'max': max(response_values)
            },
            'error_rate': {
                'avg': sum(error_values) / len(error_values),
                'min': min(error_values),
                'max': max(error_values)
            }
        }

class ResilienceValidator:
    """Validates system resilience during chaos experiments"""
    
    def __init__(self):
        self.validation_rules = []
        self.validation_results = []
    
    def add_validation_rule(self, name: str, condition: Callable[[SystemMetrics], bool], 
                          description: str):
        """Add a validation rule"""
        self.validation_rules.append({
            'name': name,
            'condition': condition,
            'description': description
        })
    
    async def validate_resilience(self, metrics_history: List[SystemMetrics]) -> Dict[str, Any]:
        """Validate system resilience based on metrics"""
        results = {
            'overall_resilience': True,
            'rule_results': [],
            'summary': {}
        }
        
        for rule in self.validation_rules:
            rule_passed = True
            failed_metrics = []
            
            for metrics in metrics_history:
                if not rule['condition'](metrics):
                    rule_passed = False
                    failed_metrics.append(metrics.timestamp)
            
            rule_result = {
                'name': rule['name'],
                'description': rule['description'],
                'passed': rule_passed,
                'failed_count': len(failed_metrics),
                'failed_timestamps': failed_metrics
            }
            
            results['rule_results'].append(rule_result)
            
            if not rule_passed:
                results['overall_resilience'] = False
        
        # Calculate summary statistics
        if metrics_history:
            results['summary'] = {
                'total_metrics_collected': len(metrics_history),
                'experiment_duration': (metrics_history[-1].timestamp - metrics_history[0].timestamp).total_seconds(),
                'rules_passed': sum(1 for r in results['rule_results'] if r['passed']),
                'rules_failed': sum(1 for r in results['rule_results'] if not r['passed']),
                'total_rules': len(results['rule_results'])
            }
        
        return results

class ChaosExperimentRunner:
    """Runs chaos engineering experiments"""
    
    def __init__(self):
        self.failure_injector = FailureInjector()
        self.system_monitor = SystemMonitor()
        self.resilience_validator = ResilienceValidator()
        self.experiment_history = []
        
        # Setup default resilience validation rules
        self.setup_default_validation_rules()
    
    def setup_default_validation_rules(self):
        """Setup default resilience validation rules"""
        # CPU usage should not exceed 95%
        self.resilience_validator.add_validation_rule(
            "cpu_usage_limit",
            lambda m: m.cpu_usage < 95.0,
            "CPU usage should remain below 95%"
        )
        
        # Memory usage should not exceed 90%
        self.resilience_validator.add_validation_rule(
            "memory_usage_limit",
            lambda m: m.memory_usage < 90.0,
            "Memory usage should remain below 90%"
        )
        
        # Response time should not exceed 5 seconds
        self.resilience_validator.add_validation_rule(
            "response_time_limit",
            lambda m: m.response_time < 5000.0,
            "Response time should remain below 5 seconds"
        )
        
        # Error rate should not exceed 10%
        self.resilience_validator.add_validation_rule(
            "error_rate_limit",
            lambda m: m.error_rate < 10.0,
            "Error rate should remain below 10%"
        )
    
    async def run_experiment(self, experiment: ChaosExperiment) -> Dict[str, Any]:
        """Run a chaos engineering experiment"""
        logger.info(f"Starting chaos experiment: {experiment.name}")
        
        experiment.status = ChaosExperimentStatus.RUNNING
        experiment.start_time = datetime.now()
        
        try:
            # Start monitoring
            monitor_task = asyncio.create_task(self.system_monitor.start_monitoring())
            
            # Wait a bit to collect baseline metrics
            await asyncio.sleep(5)
            
            # Inject failure based on type
            await self.inject_failure(experiment)
            
            # Wait for experiment duration
            await asyncio.sleep(experiment.duration)
            
            # Stop monitoring
            self.system_monitor.stop_monitoring()
            await monitor_task
            
            # Validate resilience
            resilience_results = await self.resilience_validator.validate_resilience(
                self.system_monitor.metrics_history
            )
            
            # Compile results
            experiment.end_time = datetime.now()
            experiment.status = ChaosExperimentStatus.COMPLETED
            experiment.results = {
                'metrics_summary': self.system_monitor.get_metrics_summary(),
                'resilience_validation': resilience_results,
                'experiment_duration': (experiment.end_time - experiment.start_time).total_seconds(),
                'hypothesis_validated': resilience_results['overall_resilience']
            }
            
            logger.info(f"Completed chaos experiment: {experiment.name}")
            
        except Exception as e:
            logger.error(f"Chaos experiment failed: {e}")
            experiment.status = ChaosExperimentStatus.FAILED
            experiment.end_time = datetime.now()
            experiment.results = {
                'error': str(e),
                'experiment_duration': (experiment.end_time - experiment.start_time).total_seconds() if experiment.start_time else 0
            }
        
        finally:
            # Always cleanup failures
            await self.failure_injector.cleanup_all_failures()
            self.system_monitor.stop_monitoring()
            
            # Clear metrics history for next experiment
            self.system_monitor.metrics_history.clear()
        
        # Store experiment in history
        self.experiment_history.append(experiment)
        
        return experiment.results
    
    async def inject_failure(self, experiment: ChaosExperiment):
        """Inject failure based on experiment configuration"""
        failure_type = experiment.failure_type
        target = experiment.target_component
        duration = experiment.duration
        intensity = experiment.intensity
        params = experiment.parameters
        
        if failure_type == FailureType.NETWORK_LATENCY:
            latency_ms = int(params.get('latency_ms', 1000 * intensity))
            await self.failure_injector.inject_network_latency(target, latency_ms, duration)
        
        elif failure_type == FailureType.NETWORK_PARTITION:
            await self.failure_injector.inject_network_partition(target, duration)
        
        elif failure_type == FailureType.SERVICE_CRASH:
            await self.failure_injector.inject_service_crash(target, duration)
        
        elif failure_type == FailureType.MEMORY_PRESSURE:
            target_usage = params.get('target_usage', intensity)
            await self.failure_injector.inject_memory_pressure(target_usage, duration)
        
        elif failure_type == FailureType.CPU_SPIKE:
            target_usage = params.get('target_usage', intensity)
            await self.failure_injector.inject_cpu_spike(target_usage, duration)
        
        elif failure_type == FailureType.API_TIMEOUT:
            timeout_ms = int(params.get('timeout_ms', 5000 * intensity))
            await self.failure_injector.inject_api_timeout(target, timeout_ms, duration)
        
        else:
            logger.warning(f"Unsupported failure type: {failure_type}")
    
    def generate_experiment_report(self, experiment: ChaosExperiment) -> str:
        """Generate a detailed experiment report"""
        if not experiment.results:
            return f"Experiment {experiment.name} has no results"
        
        report = f"""
# Chaos Engineering Experiment Report

## Experiment Details
- **Name:** {experiment.name}
- **Description:** {experiment.description}
- **Failure Type:** {experiment.failure_type.value}
- **Target Component:** {experiment.target_component}
- **Duration:** {experiment.duration} seconds
- **Intensity:** {experiment.intensity}
- **Status:** {experiment.status.value}

## Hypothesis
{experiment.hypothesis}

## Results Summary
- **Experiment Duration:** {experiment.results.get('experiment_duration', 0):.2f} seconds
- **Hypothesis Validated:** {experiment.results.get('hypothesis_validated', False)}
- **Overall Resilience:** {experiment.results.get('resilience_validation', {}).get('overall_resilience', False)}

## Metrics Summary
"""
        
        metrics_summary = experiment.results.get('metrics_summary', {})
        for metric_name, metric_data in metrics_summary.items():
            if isinstance(metric_data, dict) and 'avg' in metric_data:
                report += f"- **{metric_name.replace('_', ' ').title()}:** Avg: {metric_data['avg']:.2f}, Min: {metric_data['min']:.2f}, Max: {metric_data['max']:.2f}\n"
        
        report += "\n## Resilience Validation\n"
        
        resilience_results = experiment.results.get('resilience_validation', {})
        rule_results = resilience_results.get('rule_results', [])
        
        for rule in rule_results:
            status = "✅ PASSED" if rule['passed'] else "❌ FAILED"
            report += f"- **{rule['name']}:** {status}\n"
            report += f"  - {rule['description']}\n"
            if not rule['passed']:
                report += f"  - Failed {rule['failed_count']} times\n"
        
        report += f"\n## Success Criteria\n"
        for criteria in experiment.success_criteria:
            report += f"- {criteria}\n"
        
        report += f"\n## Rollback Strategy\n{experiment.rollback_strategy}\n"
        
        return report

# Predefined chaos experiments
class ChaosExperimentLibrary:
    """Library of predefined chaos experiments"""
    
    @staticmethod
    def network_latency_experiment() -> ChaosExperiment:
        """Network latency chaos experiment"""
        return ChaosExperiment(
            experiment_id="net_latency_001",
            name="Network Latency Resilience Test",
            description="Test system resilience under high network latency conditions",
            failure_type=FailureType.NETWORK_LATENCY,
            target_component="market_data_feed",
            duration=60,
            intensity=0.8,
            parameters={'latency_ms': 500},
            hypothesis="System should maintain functionality with increased latency up to 500ms",
            success_criteria=[
                "Response time increases but remains under 5 seconds",
                "Error rate stays below 5%",
                "No data loss occurs",
                "System recovers within 30 seconds after latency is removed"
            ],
            rollback_strategy="Restore normal network conditions immediately if error rate exceeds 10%"
        )
    
    @staticmethod
    def service_crash_experiment() -> ChaosExperiment:
        """Service crash chaos experiment"""
        return ChaosExperiment(
            experiment_id="svc_crash_001",
            name="Order Management Service Crash Test",
            description="Test system behavior when order management service crashes",
            failure_type=FailureType.SERVICE_CRASH,
            target_component="order_management_service",
            duration=30,
            intensity=1.0,
            parameters={},
            hypothesis="System should gracefully handle order service crashes with automatic recovery",
            success_criteria=[
                "Orders are queued during service downtime",
                "Service automatically restarts within 30 seconds",
                "Queued orders are processed after recovery",
                "No orders are lost"
            ],
            rollback_strategy="Manually restart service if automatic recovery fails"
        )
    
    @staticmethod
    def memory_pressure_experiment() -> ChaosExperiment:
        """Memory pressure chaos experiment"""
        return ChaosExperiment(
            experiment_id="mem_pressure_001",
            name="High Memory Usage Resilience Test",
            description="Test system behavior under high memory pressure",
            failure_type=FailureType.MEMORY_PRESSURE,
            target_component="trading_engine",
            duration=45,
            intensity=0.85,
            parameters={'target_usage': 0.85},
            hypothesis="System should handle high memory usage without crashing",
            success_criteria=[
                "System remains responsive under memory pressure",
                "Garbage collection doesn't cause significant latency spikes",
                "No out-of-memory errors occur",
                "Performance degrades gracefully"
            ],
            rollback_strategy="Release memory pressure immediately if system becomes unresponsive"
        )
    
    @staticmethod
    def network_partition_experiment() -> ChaosExperiment:
        """Network partition chaos experiment"""
        return ChaosExperiment(
            experiment_id="net_partition_001",
            name="Database Network Partition Test",
            description="Test system resilience when database connectivity is lost",
            failure_type=FailureType.NETWORK_PARTITION,
            target_component="database",
            duration=20,
            intensity=1.0,
            parameters={},
            hypothesis="System should handle database connectivity loss with graceful degradation",
            success_criteria=[
                "System switches to read-only mode",
                "Critical operations are cached locally",
                "Users receive appropriate error messages",
                "System recovers automatically when connectivity is restored"
            ],
            rollback_strategy="Restore database connectivity immediately if critical operations fail"
        )

if __name__ == "__main__":
    async def main():
        """Main chaos engineering execution"""
        print("🔥 Chaos Engineering Framework")
        print("=" * 50)
        
        runner = ChaosExperimentRunner()
        
        # Run a sample experiment
        experiment = ChaosExperimentLibrary.network_latency_experiment()
        
        print(f"Running experiment: {experiment.name}")
        results = await runner.run_experiment(experiment)
        
        print("\nExperiment Results:")
        print(f"Status: {experiment.status.value}")
        print(f"Hypothesis Validated: {results.get('hypothesis_validated', False)}")
        
        # Generate report
        report = runner.generate_experiment_report(experiment)
        
        # Save report
        report_path = Path(f"chaos_experiment_report_{experiment.experiment_id}.md")
        with open(report_path, 'w') as f:
            f.write(report)
        
        print(f"\nDetailed report saved to: {report_path}")
        
        return results.get('hypothesis_validated', False)
    
    success = asyncio.run(main())
    sys.exit(0 if success else 1)