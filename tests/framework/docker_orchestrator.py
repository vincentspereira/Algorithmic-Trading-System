"""
Docker Orchestrator for Testing Framework

This module provides comprehensive Docker container management for the
Phase 1 testing framework, including container rebuild, service stack startup,
health checks, and log monitoring.
"""

import os
import sys
import subprocess
import time
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum
import logging
import threading
import queue
from datetime import datetime, timedelta
import requests
import docker
from docker.errors import DockerException, APIError, NotFound

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContainerStatus(Enum):
    """Container status enumeration"""
    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    STOPPING = "stopping"
    RESTARTING = "restarting"
    PAUSED = "paused"
    EXITED = "exited"
    DEAD = "dead"
    CREATED = "created"
    REMOVING = "removing"
    UNKNOWN = "unknown"


class HealthStatus(Enum):
    """Health check status enumeration"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    NONE = "none"
    UNKNOWN = "unknown"


class ServiceStatus(Enum):
    """Service status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    STARTING = "starting"
    STOPPING = "stopping"
    UNKNOWN = "unknown"


@dataclass
class ContainerInfo:
    """Information about a Docker container"""
    name: str
    id: str
    image: str
    status: ContainerStatus
    health_status: HealthStatus
    ports: Dict[str, str]
    created: datetime
    started: Optional[datetime] = None
    finished: Optional[datetime] = None
    exit_code: Optional[int] = None
    error_message: Optional[str] = None


@dataclass
class ServiceInfo:
    """Information about a Docker Compose service"""
    name: str
    containers: List[ContainerInfo]
    status: ServiceStatus
    health_status: HealthStatus
    dependencies: List[str]
    ports: Dict[str, str]
    environment: Dict[str, str]
    volumes: List[str]


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    service_name: str
    container_name: str
    status: HealthStatus
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    timestamp: datetime = None
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.details is None:
            self.details = {}


@dataclass
class LogEntry:
    """Docker container log entry"""
    container_name: str
    timestamp: datetime
    level: str
    message: str
    source: str = "container"


@dataclass
class OrchestrationResult:
    """Result of orchestration operations"""
    success: bool
    services_started: List[str]
    services_failed: List[str]
    containers_healthy: List[str]
    containers_unhealthy: List[str]
    total_startup_time: float
    error_messages: List[str]
    warnings: List[str]
    details: Dict[str, Any]


class DockerOrchestrator:
    """
    Manages Docker container orchestration for testing framework.
    
    This class handles Docker container rebuild, service stack startup,
    health checks, and log monitoring for the testing environment.
    """
    
    def __init__(self, project_root: Optional[Path] = None, compose_files: Optional[List[str]] = None):
        """
        Initialize the DockerOrchestrator.
        
        Args:
            project_root: Path to the project root directory. If None, uses current directory.
            compose_files: List of docker-compose file paths. If None, uses default files.
        """
        self.project_root = project_root or Path.cwd()
        self.compose_files = compose_files or [
            "docker-compose.yml",
            "docker-compose.databases.yml"
        ]
        
        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {str(e)}")
            self.docker_client = None
        
        # Configuration
        self.health_check_timeout = 300  # 5 minutes
        self.health_check_interval = 10  # 10 seconds
        self.startup_timeout = 600  # 10 minutes
        self.log_buffer_size = 1000
        
        # State tracking
        self.services_info: Dict[str, ServiceInfo] = {}
        self.containers_info: Dict[str, ContainerInfo] = {}
        self.log_buffer: queue.Queue = queue.Queue(maxsize=self.log_buffer_size)
        self.monitoring_threads: List[threading.Thread] = []
        self.stop_monitoring = threading.Event()
    
    def validate_docker_environment(self) -> Tuple[bool, List[str]]:
        """
        Validate Docker environment and prerequisites.
        
        Returns:
            Tuple[bool, List[str]]: Success status and list of error messages
        """
        errors = []
        
        try:
            # Check if Docker is installed and running
            if self.docker_client is None:
                errors.append("Docker client not available")
                return False, errors
            
            # Check Docker version
            version_info = self.docker_client.version()
            logger.info(f"Docker version: {version_info.get('Version', 'Unknown')}")
            
            # Check if docker-compose is available
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                errors.append("docker-compose not available")
            else:
                logger.info(f"Docker Compose version: {result.stdout.strip()}")
            
            # Check compose files exist
            for compose_file in self.compose_files:
                compose_path = self.project_root / compose_file
                if not compose_path.exists():
                    errors.append(f"Compose file not found: {compose_file}")
            
            # Check Docker daemon is responsive
            try:
                containers = self.docker_client.containers.list()
                logger.info(f"Docker daemon responsive, found {len(containers)} containers")
            except Exception as e:
                errors.append(f"Docker daemon not responsive: {str(e)}")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(f"Docker environment validation failed: {str(e)}")
            return False, errors
    
    def rebuild_containers_with_no_cache(self, services: Optional[List[str]] = None) -> bool:
        """
        Rebuild Docker containers with --no-cache option.
        
        Args:
            services: List of specific services to rebuild. If None, rebuilds all services.
            
        Returns:
            bool: True if rebuild is successful
        """
        try:
            logger.info("Starting container rebuild with --no-cache...")
            
            # Build docker-compose command
            cmd = ["docker-compose"]
            
            # Add compose files
            for compose_file in self.compose_files:
                cmd.extend(["-f", str(self.project_root / compose_file)])
            
            # Add build command with --no-cache
            cmd.extend(["build", "--no-cache", "--pull"])
            
            # Add specific services if provided
            if services:
                cmd.extend(services)
                logger.info(f"Rebuilding specific services: {', '.join(services)}")
            else:
                logger.info("Rebuilding all services")
            
            # Execute rebuild
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes timeout for rebuild
            )
            
            if result.returncode == 0:
                logger.info("Container rebuild completed successfully")
                return True
            else:
                logger.error(f"Container rebuild failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Container rebuild timed out after 30 minutes")
            return False
        except Exception as e:
            logger.error(f"Container rebuild error: {str(e)}")
            return False
    
    def start_service_stack(self, services: Optional[List[str]] = None, detached: bool = True) -> OrchestrationResult:
        """
        Start Docker Compose service stack with docker-compose up -d.
        
        Args:
            services: List of specific services to start. If None, starts all services.
            detached: Whether to run in detached mode (-d flag)
            
        Returns:
            OrchestrationResult: Detailed results of the startup operation
        """
        start_time = time.time()
        services_started = []
        services_failed = []
        error_messages = []
        warnings = []
        
        try:
            logger.info("Starting Docker Compose service stack...")
            
            # Build docker-compose command
            cmd = ["docker-compose"]
            
            # Add compose files
            for compose_file in self.compose_files:
                cmd.extend(["-f", str(self.project_root / compose_file)])
            
            # Add up command
            cmd.append("up")
            
            if detached:
                cmd.append("-d")
            
            # Add specific services if provided
            if services:
                cmd.extend(services)
                logger.info(f"Starting specific services: {', '.join(services)}")
            else:
                logger.info("Starting all services")
            
            # Execute startup
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=self.startup_timeout
            )
            
            if result.returncode == 0:
                logger.info("Service stack startup completed")
                
                # Parse output to determine which services started
                if services:
                    services_started = services.copy()
                else:
                    services_started = self._get_all_services_from_compose()
                
            else:
                logger.error(f"Service stack startup failed: {result.stderr}")
                error_messages.append(f"Docker Compose startup failed: {result.stderr}")
                services_failed = services or self._get_all_services_from_compose()
            
            # Wait for services to be ready and perform health checks
            if services_started:
                logger.info("Waiting for services to be ready...")
                time.sleep(10)  # Initial wait for containers to start
                
                # Update container information
                self._update_containers_info()
                
                # Perform health checks
                containers_healthy, containers_unhealthy = self._perform_health_checks()
                
                # Check for any services that failed to start properly
                for service in services_started.copy():
                    if not self._is_service_running(service):
                        services_started.remove(service)
                        services_failed.append(service)
                        warnings.append(f"Service {service} failed to start properly")
            else:
                containers_healthy = []
                containers_unhealthy = []
            
            total_startup_time = time.time() - start_time
            success = len(services_failed) == 0 and len(error_messages) == 0
            
            return OrchestrationResult(
                success=success,
                services_started=services_started,
                services_failed=services_failed,
                containers_healthy=containers_healthy,
                containers_unhealthy=containers_unhealthy,
                total_startup_time=total_startup_time,
                error_messages=error_messages,
                warnings=warnings,
                details={
                    'compose_files': self.compose_files,
                    'detached': detached,
                    'startup_timeout': self.startup_timeout
                }
            )
            
        except subprocess.TimeoutExpired:
            error_msg = f"Service stack startup timed out after {self.startup_timeout} seconds"
            logger.error(error_msg)
            error_messages.append(error_msg)
            
            return OrchestrationResult(
                success=False,
                services_started=services_started,
                services_failed=services or self._get_all_services_from_compose(),
                containers_healthy=[],
                containers_unhealthy=[],
                total_startup_time=time.time() - start_time,
                error_messages=error_messages,
                warnings=warnings,
                details={'timeout': True}
            )
            
        except Exception as e:
            error_msg = f"Service stack startup error: {str(e)}"
            logger.error(error_msg)
            error_messages.append(error_msg)
            
            return OrchestrationResult(
                success=False,
                services_started=services_started,
                services_failed=services or self._get_all_services_from_compose(),
                containers_healthy=[],
                containers_unhealthy=[],
                total_startup_time=time.time() - start_time,
                error_messages=error_messages,
                warnings=warnings,
                details={'exception': str(e)}
            )
    
    def validate_container_health(self, timeout: Optional[int] = None) -> Dict[str, HealthCheckResult]:
        """
        Validate container health with comprehensive health checks.
        
        Args:
            timeout: Timeout in seconds for health checks. If None, uses default.
            
        Returns:
            Dict[str, HealthCheckResult]: Health check results for each container
        """
        timeout = timeout or self.health_check_timeout
        health_results = {}
        
        logger.info("Starting comprehensive container health validation...")
        
        try:
            # Update container information
            self._update_containers_info()
            
            # Perform health checks for each container
            for container_name, container_info in self.containers_info.items():
                logger.info(f"Checking health for container: {container_name}")
                
                health_result = self._check_container_health(container_info, timeout)
                health_results[container_name] = health_result
                
                logger.info(f"Health check result for {container_name}: {health_result.status.value}")
            
            # Perform service-level health checks
            service_health_results = self._perform_service_health_checks(timeout)
            health_results.update(service_health_results)
            
            return health_results
            
        except Exception as e:
            logger.error(f"Container health validation error: {str(e)}")
            return health_results
    
    def monitor_container_logs(self, containers: Optional[List[str]] = None, 
                             follow: bool = True, tail: int = 100) -> None:
        """
        Monitor container logs with real-time streaming.
        
        Args:
            containers: List of container names to monitor. If None, monitors all containers.
            follow: Whether to follow logs in real-time
            tail: Number of lines to tail from the end of logs
        """
        try:
            logger.info("Starting container log monitoring...")
            
            if containers is None:
                containers = list(self.containers_info.keys())
            
            # Start monitoring threads for each container
            for container_name in containers:
                if container_name in self.containers_info:
                    thread = threading.Thread(
                        target=self._monitor_single_container_logs,
                        args=(container_name, follow, tail),
                        daemon=True
                    )
                    thread.start()
                    self.monitoring_threads.append(thread)
                    logger.info(f"Started log monitoring for container: {container_name}")
            
        except Exception as e:
            logger.error(f"Log monitoring setup error: {str(e)}")
    
    def stop_service_stack(self, services: Optional[List[str]] = None, 
                          remove_volumes: bool = False) -> bool:
        """
        Stop Docker Compose service stack.
        
        Args:
            services: List of specific services to stop. If None, stops all services.
            remove_volumes: Whether to remove volumes when stopping
            
        Returns:
            bool: True if stop is successful
        """
        try:
            logger.info("Stopping Docker Compose service stack...")
            
            # Stop monitoring
            self.stop_monitoring.set()
            
            # Build docker-compose command
            cmd = ["docker-compose"]
            
            # Add compose files
            for compose_file in self.compose_files:
                cmd.extend(["-f", str(self.project_root / compose_file)])
            
            # Add down command
            cmd.append("down")
            
            if remove_volumes:
                cmd.append("--volumes")
            
            # Add specific services if provided
            if services:
                cmd.extend(services)
                logger.info(f"Stopping specific services: {', '.join(services)}")
            else:
                logger.info("Stopping all services")
            
            # Execute stop
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout for stop
            )
            
            if result.returncode == 0:
                logger.info("Service stack stopped successfully")
                return True
            else:
                logger.error(f"Service stack stop failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Service stack stop timed out after 5 minutes")
            return False
        except Exception as e:
            logger.error(f"Service stack stop error: {str(e)}")
            return False
    
    def get_service_status(self, service_name: str) -> Optional[ServiceInfo]:
        """
        Get detailed status information for a specific service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Optional[ServiceInfo]: Service information or None if not found
        """
        try:
            self._update_containers_info()
            return self.services_info.get(service_name)
        except Exception as e:
            logger.error(f"Error getting service status for {service_name}: {str(e)}")
            return None
    
    def get_container_logs(self, container_name: str, lines: int = 100) -> List[LogEntry]:
        """
        Get recent logs from a specific container.
        
        Args:
            container_name: Name of the container
            lines: Number of recent lines to retrieve
            
        Returns:
            List[LogEntry]: List of log entries
        """
        logs = []
        
        try:
            if self.docker_client is None:
                return logs
            
            container = self.docker_client.containers.get(container_name)
            log_lines = container.logs(tail=lines, timestamps=True).decode('utf-8').split('\n')
            
            for line in log_lines:
                if line.strip():
                    # Parse timestamp and message
                    parts = line.split(' ', 1)
                    if len(parts) >= 2:
                        timestamp_str = parts[0]
                        message = parts[1]
                        
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        except:
                            timestamp = datetime.now()
                        
                        # Determine log level
                        level = "INFO"
                        message_upper = message.upper()
                        if "ERROR" in message_upper or "FATAL" in message_upper:
                            level = "ERROR"
                        elif "WARN" in message_upper:
                            level = "WARNING"
                        elif "DEBUG" in message_upper:
                            level = "DEBUG"
                        
                        logs.append(LogEntry(
                            container_name=container_name,
                            timestamp=timestamp,
                            level=level,
                            message=message,
                            source="container"
                        ))
            
        except Exception as e:
            logger.error(f"Error getting logs for container {container_name}: {str(e)}")
        
        return logs
    
    def cleanup_resources(self, remove_images: bool = False, 
                         remove_volumes: bool = False) -> bool:
        """
        Clean up Docker resources (containers, networks, volumes, images).
        
        Args:
            remove_images: Whether to remove images
            remove_volumes: Whether to remove volumes
            
        Returns:
            bool: True if cleanup is successful
        """
        try:
            logger.info("Starting Docker resource cleanup...")
            
            # Stop all services first
            self.stop_service_stack()
            
            # Build cleanup command
            cmd = ["docker", "system", "prune", "-f"]
            
            if remove_volumes:
                cmd.append("--volumes")
            
            # Execute cleanup
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                logger.info("Docker resource cleanup completed")
                
                # Additional cleanup for images if requested
                if remove_images:
                    image_cleanup_cmd = ["docker", "image", "prune", "-a", "-f"]
                    image_result = subprocess.run(
                        image_cleanup_cmd,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    
                    if image_result.returncode == 0:
                        logger.info("Docker image cleanup completed")
                    else:
                        logger.warning(f"Docker image cleanup had issues: {image_result.stderr}")
                
                return True
            else:
                logger.error(f"Docker resource cleanup failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Docker resource cleanup error: {str(e)}")
            return False
    
    def _get_all_services_from_compose(self) -> List[str]:
        """Get list of all services from docker-compose files."""
        services = []
        
        try:
            for compose_file in self.compose_files:
                compose_path = self.project_root / compose_file
                if compose_path.exists():
                    with open(compose_path, 'r') as f:
                        compose_data = yaml.safe_load(f)
                        if 'services' in compose_data:
                            services.extend(compose_data['services'].keys())
        except Exception as e:
            logger.error(f"Error parsing compose files: {str(e)}")
        
        return list(set(services))  # Remove duplicates
    
    def _update_containers_info(self) -> None:
        """Update container information from Docker API."""
        try:
            if self.docker_client is None:
                return
            
            containers = self.docker_client.containers.list(all=True)
            
            for container in containers:
                container_info = self._parse_container_info(container)
                self.containers_info[container_info.name] = container_info
                
        except Exception as e:
            logger.error(f"Error updating container info: {str(e)}")
    
    def _parse_container_info(self, container) -> ContainerInfo:
        """Parse Docker container object into ContainerInfo."""
        try:
            # Get container attributes
            attrs = container.attrs
            
            # Parse status
            status_str = container.status.lower()
            status = ContainerStatus.UNKNOWN
            for container_status in ContainerStatus:
                if container_status.value in status_str:
                    status = container_status
                    break
            
            # Parse health status
            health_status = HealthStatus.NONE
            if 'State' in attrs and 'Health' in attrs['State']:
                health_data = attrs['State']['Health']
                health_status_str = health_data.get('Status', '').lower()
                for health_stat in HealthStatus:
                    if health_stat.value in health_status_str:
                        health_status = health_stat
                        break
            
            # Parse ports
            ports = {}
            if 'NetworkSettings' in attrs and 'Ports' in attrs['NetworkSettings']:
                port_data = attrs['NetworkSettings']['Ports']
                for container_port, host_bindings in port_data.items():
                    if host_bindings:
                        host_port = host_bindings[0]['HostPort']
                        ports[container_port] = host_port
            
            # Parse timestamps
            created = datetime.fromisoformat(attrs['Created'].replace('Z', '+00:00'))
            
            started = None
            if 'State' in attrs and 'StartedAt' in attrs['State']:
                started_str = attrs['State']['StartedAt']
                if started_str != '0001-01-01T00:00:00Z':
                    started = datetime.fromisoformat(started_str.replace('Z', '+00:00'))
            
            finished = None
            if 'State' in attrs and 'FinishedAt' in attrs['State']:
                finished_str = attrs['State']['FinishedAt']
                if finished_str != '0001-01-01T00:00:00Z':
                    finished = datetime.fromisoformat(finished_str.replace('Z', '+00:00'))
            
            # Parse exit code
            exit_code = None
            if 'State' in attrs and 'ExitCode' in attrs['State']:
                exit_code = attrs['State']['ExitCode']
            
            return ContainerInfo(
                name=container.name,
                id=container.id,
                image=attrs.get('Config', {}).get('Image', ''),
                status=status,
                health_status=health_status,
                ports=ports,
                created=created,
                started=started,
                finished=finished,
                exit_code=exit_code
            )
            
        except Exception as e:
            logger.error(f"Error parsing container info: {str(e)}")
            return ContainerInfo(
                name=container.name,
                id=container.id,
                image="unknown",
                status=ContainerStatus.UNKNOWN,
                health_status=HealthStatus.UNKNOWN,
                ports={},
                created=datetime.now(),
                error_message=str(e)
            )
    
    def _perform_health_checks(self) -> Tuple[List[str], List[str]]:
        """Perform health checks on all containers."""
        healthy_containers = []
        unhealthy_containers = []
        
        for container_name, container_info in self.containers_info.items():
            if container_info.status == ContainerStatus.RUNNING:
                health_result = self._check_container_health(container_info)
                
                if health_result.status == HealthStatus.HEALTHY:
                    healthy_containers.append(container_name)
                else:
                    unhealthy_containers.append(container_name)
            else:
                unhealthy_containers.append(container_name)
        
        return healthy_containers, unhealthy_containers
    
    def _check_container_health(self, container_info: ContainerInfo, 
                               timeout: int = None) -> HealthCheckResult:
        """Check health of a specific container."""
        timeout = timeout or self.health_check_timeout
        start_time = time.time()
        
        try:
            # If container has built-in health check, use that
            if container_info.health_status != HealthStatus.NONE:
                return HealthCheckResult(
                    service_name="",
                    container_name=container_info.name,
                    status=container_info.health_status,
                    response_time=time.time() - start_time
                )
            
            # Custom health checks based on container name/service
            if "postgres" in container_info.name.lower():
                return self._check_postgres_health(container_info, timeout)
            elif "redis" in container_info.name.lower():
                return self._check_redis_health(container_info, timeout)
            elif "clickhouse" in container_info.name.lower():
                return self._check_clickhouse_health(container_info, timeout)
            elif "kafka" in container_info.name.lower():
                return self._check_kafka_health(container_info, timeout)
            elif "minio" in container_info.name.lower():
                return self._check_minio_health(container_info, timeout)
            else:
                # Generic health check - just check if container is running
                status = HealthStatus.HEALTHY if container_info.status == ContainerStatus.RUNNING else HealthStatus.UNHEALTHY
                return HealthCheckResult(
                    service_name="",
                    container_name=container_info.name,
                    status=status,
                    response_time=time.time() - start_time
                )
                
        except Exception as e:
            return HealthCheckResult(
                service_name="",
                container_name=container_info.name,
                status=HealthStatus.UNHEALTHY,
                error_message=str(e),
                response_time=time.time() - start_time
            )
    
    def _check_postgres_health(self, container_info: ContainerInfo, timeout: int) -> HealthCheckResult:
        """Check PostgreSQL container health."""
        try:
            # Use pg_isready command
            result = subprocess.run(
                ["docker", "exec", container_info.name, "pg_isready", "-U", "postgres"],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            status = HealthStatus.HEALTHY if result.returncode == 0 else HealthStatus.UNHEALTHY
            error_message = result.stderr if result.returncode != 0 else None
            
            return HealthCheckResult(
                service_name="postgres",
                container_name=container_info.name,
                status=status,
                error_message=error_message
            )
            
        except Exception as e:
            return HealthCheckResult(
                service_name="postgres",
                container_name=container_info.name,
                status=HealthStatus.UNHEALTHY,
                error_message=str(e)
            )
    
    def _check_redis_health(self, container_info: ContainerInfo, timeout: int) -> HealthCheckResult:
        """Check Redis container health."""
        try:
            # Use redis-cli ping command
            result = subprocess.run(
                ["docker", "exec", container_info.name, "redis-cli", "ping"],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            status = HealthStatus.HEALTHY if result.returncode == 0 and "PONG" in result.stdout else HealthStatus.UNHEALTHY
            error_message = result.stderr if result.returncode != 0 else None
            
            return HealthCheckResult(
                service_name="redis",
                container_name=container_info.name,
                status=status,
                error_message=error_message
            )
            
        except Exception as e:
            return HealthCheckResult(
                service_name="redis",
                container_name=container_info.name,
                status=HealthStatus.UNHEALTHY,
                error_message=str(e)
            )
    
    def _check_clickhouse_health(self, container_info: ContainerInfo, timeout: int) -> HealthCheckResult:
        """Check ClickHouse container health."""
        try:
            # Try HTTP health check first
            for port_mapping in container_info.ports.values():
                if "8123" in port_mapping:
                    try:
                        response = requests.get(f"http://localhost:{port_mapping}/ping", timeout=10)
                        if response.status_code == 200:
                            return HealthCheckResult(
                                service_name="clickhouse",
                                container_name=container_info.name,
                                status=HealthStatus.HEALTHY,
                                response_time=response.elapsed.total_seconds()
                            )
                    except:
                        pass
            
            # Fallback to clickhouse-client
            result = subprocess.run(
                ["docker", "exec", container_info.name, "clickhouse-client", "--query", "SELECT 1"],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            status = HealthStatus.HEALTHY if result.returncode == 0 else HealthStatus.UNHEALTHY
            error_message = result.stderr if result.returncode != 0 else None
            
            return HealthCheckResult(
                service_name="clickhouse",
                container_name=container_info.name,
                status=status,
                error_message=error_message
            )
            
        except Exception as e:
            return HealthCheckResult(
                service_name="clickhouse",
                container_name=container_info.name,
                status=HealthStatus.UNHEALTHY,
                error_message=str(e)
            )
    
    def _check_kafka_health(self, container_info: ContainerInfo, timeout: int) -> HealthCheckResult:
        """Check Kafka container health."""
        try:
            # Use kafka-broker-api-versions command
            result = subprocess.run(
                ["docker", "exec", container_info.name, "kafka-broker-api-versions", 
                 "--bootstrap-server", "localhost:9092"],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            status = HealthStatus.HEALTHY if result.returncode == 0 else HealthStatus.UNHEALTHY
            error_message = result.stderr if result.returncode != 0 else None
            
            return HealthCheckResult(
                service_name="kafka",
                container_name=container_info.name,
                status=status,
                error_message=error_message
            )
            
        except Exception as e:
            return HealthCheckResult(
                service_name="kafka",
                container_name=container_info.name,
                status=HealthStatus.UNHEALTHY,
                error_message=str(e)
            )
    
    def _check_minio_health(self, container_info: ContainerInfo, timeout: int) -> HealthCheckResult:
        """Check MinIO container health."""
        try:
            # Try HTTP health check
            for port_mapping in container_info.ports.values():
                if "9000" in port_mapping:
                    try:
                        response = requests.get(f"http://localhost:{port_mapping}/minio/health/live", timeout=10)
                        status = HealthStatus.HEALTHY if response.status_code == 200 else HealthStatus.UNHEALTHY
                        
                        return HealthCheckResult(
                            service_name="minio",
                            container_name=container_info.name,
                            status=status,
                            response_time=response.elapsed.total_seconds()
                        )
                    except Exception as e:
                        return HealthCheckResult(
                            service_name="minio",
                            container_name=container_info.name,
                            status=HealthStatus.UNHEALTHY,
                            error_message=str(e)
                        )
            
            # If no port mapping found, assume unhealthy
            return HealthCheckResult(
                service_name="minio",
                container_name=container_info.name,
                status=HealthStatus.UNHEALTHY,
                error_message="No accessible port found"
            )
            
        except Exception as e:
            return HealthCheckResult(
                service_name="minio",
                container_name=container_info.name,
                status=HealthStatus.UNHEALTHY,
                error_message=str(e)
            )
    
    def _perform_service_health_checks(self, timeout: int) -> Dict[str, HealthCheckResult]:
        """Perform service-level health checks."""
        service_health_results = {}
        
        # This would be extended with specific service health checks
        # For now, we'll use container-level health as a proxy
        
        return service_health_results
    
    def _is_service_running(self, service_name: str) -> bool:
        """Check if a service is running."""
        try:
            # Get containers for this service
            service_containers = [
                container for container in self.containers_info.values()
                if service_name in container.name.lower()
            ]
            
            # Service is running if at least one container is running
            return any(
                container.status == ContainerStatus.RUNNING 
                for container in service_containers
            )
            
        except Exception as e:
            logger.error(f"Error checking service status for {service_name}: {str(e)}")
            return False
    
    def _monitor_single_container_logs(self, container_name: str, follow: bool, tail: int) -> None:
        """Monitor logs for a single container."""
        try:
            if self.docker_client is None:
                return
            
            container = self.docker_client.containers.get(container_name)
            
            # Get log stream
            log_stream = container.logs(stream=follow, tail=tail, timestamps=True)
            
            for log_line in log_stream:
                if self.stop_monitoring.is_set():
                    break
                
                try:
                    line = log_line.decode('utf-8').strip()
                    if line:
                        # Parse and add to log buffer
                        parts = line.split(' ', 1)
                        if len(parts) >= 2:
                            timestamp_str = parts[0]
                            message = parts[1]
                            
                            try:
                                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            except:
                                timestamp = datetime.now()
                            
                            log_entry = LogEntry(
                                container_name=container_name,
                                timestamp=timestamp,
                                level="INFO",
                                message=message
                            )
                            
                            # Add to buffer (non-blocking)
                            try:
                                self.log_buffer.put_nowait(log_entry)
                            except queue.Full:
                                # Remove oldest entry and add new one
                                try:
                                    self.log_buffer.get_nowait()
                                    self.log_buffer.put_nowait(log_entry)
                                except queue.Empty:
                                    pass
                                
                except Exception as e:
                    logger.error(f"Error processing log line from {container_name}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error monitoring logs for {container_name}: {str(e)}")
    
    def get_orchestration_status(self) -> Dict[str, Any]:
        """
        Get comprehensive orchestration status.
        
        Returns:
            Dict[str, Any]: Complete status information
        """
        try:
            self._update_containers_info()
            
            # Count containers by status
            status_counts = {}
            for status in ContainerStatus:
                status_counts[status.value] = 0
            
            for container in self.containers_info.values():
                status_counts[container.status.value] += 1
            
            # Count containers by health
            health_counts = {}
            for health in HealthStatus:
                health_counts[health.value] = 0
            
            for container in self.containers_info.values():
                health_counts[container.health_status.value] += 1
            
            return {
                'total_containers': len(self.containers_info),
                'status_counts': status_counts,
                'health_counts': health_counts,
                'services': list(self.services_info.keys()),
                'compose_files': self.compose_files,
                'monitoring_active': not self.stop_monitoring.is_set(),
                'log_buffer_size': self.log_buffer.qsize()
            }
            
        except Exception as e:
            logger.error(f"Error getting orchestration status: {str(e)}")
            return {'error': str(e)}
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        try:
            self.stop_monitoring.set()
            if self.docker_client:
                self.docker_client.close()
        except:
            pass