"""
Test suite for DockerOrchestrator class

This module contains comprehensive tests for the DockerOrchestrator class,
validating all functionality including container management, health checks,
and log monitoring.
"""

import os
import sys
import tempfile
import shutil
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import pytest
import subprocess
from datetime import datetime, timedelta

# Add the framework directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from docker_orchestrator import (
    DockerOrchestrator,
    ContainerStatus,
    HealthStatus,
    ServiceStatus,
    ContainerInfo,
    ServiceInfo,
    HealthCheckResult,
    LogEntry,
    OrchestrationResult
)


class TestDockerOrchestrator:
    """Test suite for DockerOrchestrator class"""
    
    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory for testing"""
        temp_dir = Path(tempfile.mkdtemp())
        
        # Create sample docker-compose.yml
        compose_content = """
version: '3.8'
services:
  test_postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: test_db
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_pass
    ports:
      - "5432:5432"
  test_redis:
    image: redis:7
    ports:
      - "6379:6379"
"""
        (temp_dir / "docker-compose.yml").write_text(compose_content.strip())
        
        # Create sample docker-compose.databases.yml
        db_compose_content = """
version: '3.8'
services:
  test_clickhouse:
    image: clickhouse/clickhouse-server:23.8
    ports:
      - "8123:8123"
"""
        (temp_dir / "docker-compose.databases.yml").write_text(db_compose_content.strip())
        
        yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def mock_docker_client(self):
        """Create a mock Docker client"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.version.return_value = {'Version': '24.0.0'}
        mock_client.containers.list.return_value = []
        return mock_client
    
    @pytest.fixture
    def orchestrator(self, temp_project_dir, mock_docker_client):
        """Create a DockerOrchestrator instance for testing"""
        with patch('docker.from_env', return_value=mock_docker_client):
            return DockerOrchestrator(project_root=temp_project_dir)
    
    def test_init(self, temp_project_dir, mock_docker_client):
        """Test DockerOrchestrator initialization"""
        with patch('docker.from_env', return_value=mock_docker_client):
            orchestrator = DockerOrchestrator(project_root=temp_project_dir)
            
            assert orchestrator.project_root == temp_project_dir
            assert orchestrator.compose_files == ["docker-compose.yml", "docker-compose.databases.yml"]
            assert orchestrator.docker_client == mock_docker_client
            assert orchestrator.health_check_timeout == 300
            assert orchestrator.startup_timeout == 600
    
    def test_init_custom_compose_files(self, temp_project_dir, mock_docker_client):
        """Test DockerOrchestrator initialization with custom compose files"""
        custom_files = ["custom-compose.yml"]
        
        with patch('docker.from_env', return_value=mock_docker_client):
            orchestrator = DockerOrchestrator(
                project_root=temp_project_dir,
                compose_files=custom_files
            )
            
            assert orchestrator.compose_files == custom_files
    
    def test_init_docker_client_failure(self, temp_project_dir):
        """Test DockerOrchestrator initialization when Docker client fails"""
        with patch('docker.from_env', side_effect=Exception("Docker not available")):
            orchestrator = DockerOrchestrator(project_root=temp_project_dir)
            
            assert orchestrator.docker_client is None
    
    def test_validate_docker_environment_success(self, orchestrator, mock_docker_client):
        """Test successful Docker environment validation"""
        # Mock subprocess for docker-compose version check
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "docker-compose version 2.20.0"
            mock_run.return_value = mock_result
            
            success, errors = orchestrator.validate_docker_environment()
            
            assert success == True
            assert len(errors) == 0
            mock_docker_client.version.assert_called_once()
            mock_docker_client.containers.list.assert_called_once()
    
    def test_validate_docker_environment_no_client(self, temp_project_dir):
        """Test Docker environment validation when client is not available"""
        orchestrator = DockerOrchestrator(project_root=temp_project_dir)
        orchestrator.docker_client = None
        
        success, errors = orchestrator.validate_docker_environment()
        
        assert success == False
        assert "Docker client not available" in errors
    
    def test_validate_docker_environment_no_compose(self, orchestrator):
        """Test Docker environment validation when docker-compose is not available"""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_run.return_value = mock_result
            
            success, errors = orchestrator.validate_docker_environment()
            
            assert success == False
            assert "docker-compose not available" in errors
    
    def test_validate_docker_environment_missing_compose_file(self, orchestrator):
        """Test Docker environment validation when compose file is missing"""
        # Remove one of the compose files
        (orchestrator.project_root / "docker-compose.databases.yml").unlink()
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "docker-compose version 2.20.0"
            mock_run.return_value = mock_result
            
            success, errors = orchestrator.validate_docker_environment()
            
            assert success == False
            assert any("docker-compose.databases.yml" in error for error in errors)
    
    @patch('subprocess.run')
    def test_rebuild_containers_with_no_cache_success(self, mock_run, orchestrator):
        """Test successful container rebuild with --no-cache"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = orchestrator.rebuild_containers_with_no_cache()
        
        assert result == True
        mock_run.assert_called_once()
        
        # Check that the command includes --no-cache
        call_args = mock_run.call_args[0][0]
        assert "build" in call_args
        assert "--no-cache" in call_args
        assert "--pull" in call_args
    
    @patch('subprocess.run')
    def test_rebuild_containers_with_no_cache_specific_services(self, mock_run, orchestrator):
        """Test container rebuild with specific services"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        services = ["test_postgres", "test_redis"]
        result = orchestrator.rebuild_containers_with_no_cache(services=services)
        
        assert result == True
        
        # Check that specific services are included in the command
        call_args = mock_run.call_args[0][0]
        assert "test_postgres" in call_args
        assert "test_redis" in call_args
    
    @patch('subprocess.run')
    def test_rebuild_containers_with_no_cache_failure(self, mock_run, orchestrator):
        """Test container rebuild failure"""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Build failed"
        mock_run.return_value = mock_result
        
        result = orchestrator.rebuild_containers_with_no_cache()
        
        assert result == False
    
    @patch('subprocess.run')
    def test_rebuild_containers_with_no_cache_timeout(self, mock_run, orchestrator):
        """Test container rebuild timeout"""
        mock_run.side_effect = subprocess.TimeoutExpired("docker-compose", 1800)
        
        result = orchestrator.rebuild_containers_with_no_cache()
        
        assert result == False
    
    @patch('subprocess.run')
    def test_start_service_stack_success(self, mock_run, orchestrator):
        """Test successful service stack startup"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        # Mock the helper methods
        with patch.object(orchestrator, '_get_all_services_from_compose', return_value=['test_postgres', 'test_redis']):
            with patch.object(orchestrator, '_update_containers_info'):
                with patch.object(orchestrator, '_perform_health_checks', return_value=(['test_postgres'], [])):
                    with patch.object(orchestrator, '_is_service_running', return_value=True):
                        result = orchestrator.start_service_stack()
        
        assert result.success == True
        assert len(result.services_started) == 2
        assert len(result.services_failed) == 0
        assert len(result.containers_healthy) == 1
        assert result.total_startup_time > 0
    
    @patch('subprocess.run')
    def test_start_service_stack_specific_services(self, mock_run, orchestrator):
        """Test service stack startup with specific services"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        services = ["test_postgres"]
        
        with patch.object(orchestrator, '_update_containers_info'):
            with patch.object(orchestrator, '_perform_health_checks', return_value=(['test_postgres'], [])):
                with patch.object(orchestrator, '_is_service_running', return_value=True):
                    result = orchestrator.start_service_stack(services=services)
        
        assert result.success == True
        assert result.services_started == services
        
        # Check that specific services are included in the command
        call_args = mock_run.call_args[0][0]
        assert "test_postgres" in call_args
    
    @patch('subprocess.run')
    def test_start_service_stack_failure(self, mock_run, orchestrator):
        """Test service stack startup failure"""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Startup failed"
        mock_run.return_value = mock_result
        
        with patch.object(orchestrator, '_get_all_services_from_compose', return_value=['test_postgres']):
            result = orchestrator.start_service_stack()
        
        assert result.success == False
        assert len(result.services_failed) == 1
        assert "Docker Compose startup failed" in result.error_messages[0]
    
    @patch('subprocess.run')
    def test_start_service_stack_timeout(self, mock_run, orchestrator):
        """Test service stack startup timeout"""
        mock_run.side_effect = subprocess.TimeoutExpired("docker-compose", 600)
        
        with patch.object(orchestrator, '_get_all_services_from_compose', return_value=['test_postgres']):
            result = orchestrator.start_service_stack()
        
        assert result.success == False
        assert "timed out" in result.error_messages[0]
        assert result.details['timeout'] == True
    
    def test_validate_container_health(self, orchestrator):
        """Test container health validation"""
        # Mock container info
        container_info = ContainerInfo(
            name="test_postgres",
            id="container123",
            image="postgres:15",
            status=ContainerStatus.RUNNING,
            health_status=HealthStatus.HEALTHY,
            ports={"5432/tcp": "5432"},
            created=datetime.now()
        )
        
        orchestrator.containers_info = {"test_postgres": container_info}
        
        with patch.object(orchestrator, '_update_containers_info'):
            with patch.object(orchestrator, '_check_container_health') as mock_check:
                mock_health_result = HealthCheckResult(
                    service_name="postgres",
                    container_name="test_postgres",
                    status=HealthStatus.HEALTHY
                )
                mock_check.return_value = mock_health_result
                
                with patch.object(orchestrator, '_perform_service_health_checks', return_value={}):
                    results = orchestrator.validate_container_health()
        
        assert "test_postgres" in results
        assert results["test_postgres"].status == HealthStatus.HEALTHY
    
    def test_check_postgres_health_success(self, orchestrator):
        """Test PostgreSQL health check success"""
        container_info = ContainerInfo(
            name="test_postgres",
            id="container123",
            image="postgres:15",
            status=ContainerStatus.RUNNING,
            health_status=HealthStatus.NONE,
            ports={"5432/tcp": "5432"},
            created=datetime.now()
        )
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            
            result = orchestrator._check_postgres_health(container_info, 30)
            
            assert result.status == HealthStatus.HEALTHY
            assert result.service_name == "postgres"
            assert result.container_name == "test_postgres"
    
    def test_check_postgres_health_failure(self, orchestrator):
        """Test PostgreSQL health check failure"""
        container_info = ContainerInfo(
            name="test_postgres",
            id="container123",
            image="postgres:15",
            status=ContainerStatus.RUNNING,
            health_status=HealthStatus.NONE,
            ports={"5432/tcp": "5432"},
            created=datetime.now()
        )
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = "Connection failed"
            mock_run.return_value = mock_result
            
            result = orchestrator._check_postgres_health(container_info, 30)
            
            assert result.status == HealthStatus.UNHEALTHY
            assert result.error_message == "Connection failed"
    
    def test_check_redis_health_success(self, orchestrator):
        """Test Redis health check success"""
        container_info = ContainerInfo(
            name="test_redis",
            id="container456",
            image="redis:7",
            status=ContainerStatus.RUNNING,
            health_status=HealthStatus.NONE,
            ports={"6379/tcp": "6379"},
            created=datetime.now()
        )
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "PONG"
            mock_run.return_value = mock_result
            
            result = orchestrator._check_redis_health(container_info, 30)
            
            assert result.status == HealthStatus.HEALTHY
            assert result.service_name == "redis"
    
    def test_check_redis_health_failure(self, orchestrator):
        """Test Redis health check failure"""
        container_info = ContainerInfo(
            name="test_redis",
            id="container456",
            image="redis:7",
            status=ContainerStatus.RUNNING,
            health_status=HealthStatus.NONE,
            ports={"6379/tcp": "6379"},
            created=datetime.now()
        )
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = "Connection refused"
            mock_run.return_value = mock_result
            
            result = orchestrator._check_redis_health(container_info, 30)
            
            assert result.status == HealthStatus.UNHEALTHY
            assert result.error_message == "Connection refused"
    
    @patch('requests.get')
    def test_check_clickhouse_health_http_success(self, mock_get, orchestrator):
        """Test ClickHouse health check via HTTP success"""
        container_info = ContainerInfo(
            name="test_clickhouse",
            id="container789",
            image="clickhouse/clickhouse-server:23.8",
            status=ContainerStatus.RUNNING,
            health_status=HealthStatus.NONE,
            ports={"8123/tcp": "8123"},
            created=datetime.now()
        )
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_get.return_value = mock_response
        
        result = orchestrator._check_clickhouse_health(container_info, 30)
        
        assert result.status == HealthStatus.HEALTHY
        assert result.service_name == "clickhouse"
        assert result.response_time == 0.1
    
    @patch('requests.get')
    def test_check_clickhouse_health_http_failure_fallback(self, mock_get, orchestrator):
        """Test ClickHouse health check HTTP failure with fallback"""
        container_info = ContainerInfo(
            name="test_clickhouse",
            id="container789",
            image="clickhouse/clickhouse-server:23.8",
            status=ContainerStatus.RUNNING,
            health_status=HealthStatus.NONE,
            ports={"8123/tcp": "8123"},
            created=datetime.now()
        )
        
        # Mock HTTP request failure
        mock_get.side_effect = Exception("Connection failed")
        
        # Mock subprocess fallback success
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            
            result = orchestrator._check_clickhouse_health(container_info, 30)
            
            assert result.status == HealthStatus.HEALTHY
            assert result.service_name == "clickhouse"
    
    def test_monitor_container_logs(self, orchestrator, mock_docker_client):
        """Test container log monitoring setup"""
        # Mock container info
        container_info = ContainerInfo(
            name="test_postgres",
            id="container123",
            image="postgres:15",
            status=ContainerStatus.RUNNING,
            health_status=HealthStatus.HEALTHY,
            ports={"5432/tcp": "5432"},
            created=datetime.now()
        )
        
        orchestrator.containers_info = {"test_postgres": container_info}
        
        with patch('threading.Thread') as mock_thread:
            orchestrator.monitor_container_logs(containers=["test_postgres"])
            
            # Verify thread was created and started
            mock_thread.assert_called_once()
            mock_thread.return_value.start.assert_called_once()
    
    def test_get_container_logs(self, orchestrator, mock_docker_client):
        """Test getting container logs"""
        # Mock container
        mock_container = Mock()
        mock_container.logs.return_value = b"2023-01-01T10:00:00Z INFO: Test log message\n2023-01-01T10:00:01Z ERROR: Test error message"
        mock_docker_client.containers.get.return_value = mock_container
        
        logs = orchestrator.get_container_logs("test_container", lines=10)
        
        assert len(logs) == 2
        assert logs[0].container_name == "test_container"
        assert logs[0].level == "INFO"
        assert "Test log message" in logs[0].message
        assert logs[1].level == "ERROR"
        assert "Test error message" in logs[1].message
    
    def test_get_container_logs_no_client(self, orchestrator):
        """Test getting container logs when Docker client is not available"""
        orchestrator.docker_client = None
        
        logs = orchestrator.get_container_logs("test_container")
        
        assert logs == []
    
    @patch('subprocess.run')
    def test_stop_service_stack_success(self, mock_run, orchestrator):
        """Test successful service stack stop"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = orchestrator.stop_service_stack()
        
        assert result == True
        mock_run.assert_called_once()
        
        # Check that the command includes down
        call_args = mock_run.call_args[0][0]
        assert "down" in call_args
    
    @patch('subprocess.run')
    def test_stop_service_stack_with_volumes(self, mock_run, orchestrator):
        """Test service stack stop with volume removal"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = orchestrator.stop_service_stack(remove_volumes=True)
        
        assert result == True
        
        # Check that the command includes --volumes
        call_args = mock_run.call_args[0][0]
        assert "--volumes" in call_args
    
    @patch('subprocess.run')
    def test_stop_service_stack_failure(self, mock_run, orchestrator):
        """Test service stack stop failure"""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Stop failed"
        mock_run.return_value = mock_result
        
        result = orchestrator.stop_service_stack()
        
        assert result == False
    
    def test_get_service_status(self, orchestrator):
        """Test getting service status"""
        # Mock service info
        service_info = ServiceInfo(
            name="test_postgres",
            containers=[],
            status=ServiceStatus.ACTIVE,
            health_status=HealthStatus.HEALTHY,
            dependencies=[],
            ports={"5432": "5432"},
            environment={},
            volumes=[]
        )
        
        orchestrator.services_info = {"test_postgres": service_info}
        
        with patch.object(orchestrator, '_update_containers_info'):
            result = orchestrator.get_service_status("test_postgres")
        
        assert result == service_info
        assert result.name == "test_postgres"
        assert result.status == ServiceStatus.ACTIVE
    
    def test_get_service_status_not_found(self, orchestrator):
        """Test getting service status for non-existent service"""
        with patch.object(orchestrator, '_update_containers_info'):
            result = orchestrator.get_service_status("non_existent")
        
        assert result is None
    
    @patch('subprocess.run')
    def test_cleanup_resources_success(self, mock_run, orchestrator):
        """Test successful resource cleanup"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        with patch.object(orchestrator, 'stop_service_stack', return_value=True):
            result = orchestrator.cleanup_resources()
        
        assert result == True
        
        # Check that docker system prune was called
        assert any("system" in str(call) and "prune" in str(call) for call in mock_run.call_args_list)
    
    @patch('subprocess.run')
    def test_cleanup_resources_with_images(self, mock_run, orchestrator):
        """Test resource cleanup with image removal"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        with patch.object(orchestrator, 'stop_service_stack', return_value=True):
            result = orchestrator.cleanup_resources(remove_images=True)
        
        assert result == True
        
        # Check that both system prune and image prune were called
        call_args_list = [str(call) for call in mock_run.call_args_list]
        assert any("system" in call and "prune" in call for call in call_args_list)
        assert any("image" in call and "prune" in call for call in call_args_list)
    
    def test_get_all_services_from_compose(self, orchestrator):
        """Test getting all services from compose files"""
        services = orchestrator._get_all_services_from_compose()
        
        # Should find services from both compose files
        assert "test_postgres" in services
        assert "test_redis" in services
        assert "test_clickhouse" in services
    
    def test_parse_container_info(self, orchestrator):
        """Test parsing container information"""
        # Mock container object
        mock_container = Mock()
        mock_container.name = "test_container"
        mock_container.id = "container123"
        mock_container.status = "running"
        
        # Mock container attributes
        mock_attrs = {
            'Created': '2023-01-01T10:00:00Z',
            'State': {
                'StartedAt': '2023-01-01T10:00:05Z',
                'FinishedAt': '0001-01-01T00:00:00Z',
                'ExitCode': 0,
                'Health': {
                    'Status': 'healthy'
                }
            },
            'Config': {
                'Image': 'postgres:15'
            },
            'NetworkSettings': {
                'Ports': {
                    '5432/tcp': [{'HostPort': '5432'}]
                }
            }
        }
        mock_container.attrs = mock_attrs
        
        container_info = orchestrator._parse_container_info(mock_container)
        
        assert container_info.name == "test_container"
        assert container_info.id == "container123"
        assert container_info.status == ContainerStatus.RUNNING
        assert container_info.health_status == HealthStatus.HEALTHY
        assert container_info.image == "postgres:15"
        assert "5432/tcp" in container_info.ports
        assert container_info.ports["5432/tcp"] == "5432"
    
    def test_is_service_running(self, orchestrator):
        """Test checking if service is running"""
        # Mock container info
        container_info = ContainerInfo(
            name="test_postgres_1",
            id="container123",
            image="postgres:15",
            status=ContainerStatus.RUNNING,
            health_status=HealthStatus.HEALTHY,
            ports={"5432/tcp": "5432"},
            created=datetime.now()
        )
        
        orchestrator.containers_info = {"test_postgres_1": container_info}
        
        result = orchestrator._is_service_running("postgres")
        assert result == True
        
        # Test with stopped container
        container_info.status = ContainerStatus.STOPPED
        result = orchestrator._is_service_running("postgres")
        assert result == False
    
    def test_get_orchestration_status(self, orchestrator):
        """Test getting orchestration status"""
        # Mock container info
        container_info = ContainerInfo(
            name="test_postgres",
            id="container123",
            image="postgres:15",
            status=ContainerStatus.RUNNING,
            health_status=HealthStatus.HEALTHY,
            ports={"5432/tcp": "5432"},
            created=datetime.now()
        )
        
        orchestrator.containers_info = {"test_postgres": container_info}
        
        with patch.object(orchestrator, '_update_containers_info'):
            status = orchestrator.get_orchestration_status()
        
        assert status['total_containers'] == 1
        assert status['status_counts']['running'] == 1
        assert status['health_counts']['healthy'] == 1
        assert status['compose_files'] == orchestrator.compose_files
        assert 'monitoring_active' in status
        assert 'log_buffer_size' in status
    
    def test_orchestration_result_dataclass(self):
        """Test OrchestrationResult dataclass"""
        result = OrchestrationResult(
            success=True,
            services_started=["postgres", "redis"],
            services_failed=[],
            containers_healthy=["postgres_1", "redis_1"],
            containers_unhealthy=[],
            total_startup_time=30.5,
            error_messages=[],
            warnings=["Minor warning"],
            details={"test": "value"}
        )
        
        assert result.success == True
        assert len(result.services_started) == 2
        assert len(result.containers_healthy) == 2
        assert result.total_startup_time == 30.5
        assert len(result.warnings) == 1
        assert result.details["test"] == "value"
    
    def test_health_check_result_dataclass(self):
        """Test HealthCheckResult dataclass"""
        result = HealthCheckResult(
            service_name="postgres",
            container_name="test_postgres",
            status=HealthStatus.HEALTHY,
            response_time=0.5
        )
        
        assert result.service_name == "postgres"
        assert result.container_name == "test_postgres"
        assert result.status == HealthStatus.HEALTHY
        assert result.response_time == 0.5
        assert result.timestamp is not None
        assert result.details == {}
    
    def test_log_entry_dataclass(self):
        """Test LogEntry dataclass"""
        timestamp = datetime.now()
        log_entry = LogEntry(
            container_name="test_container",
            timestamp=timestamp,
            level="INFO",
            message="Test log message"
        )
        
        assert log_entry.container_name == "test_container"
        assert log_entry.timestamp == timestamp
        assert log_entry.level == "INFO"
        assert log_entry.message == "Test log message"
        assert log_entry.source == "container"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])