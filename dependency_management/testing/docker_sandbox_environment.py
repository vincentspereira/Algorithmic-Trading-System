#!/usr/bin/env python3
"""
Docker-based Testing Sandbox Environment
Provides isolated testing environments for dependency updates and system validation
for the Algorithmic Trading System.
"""

import json
import subprocess
import sys
import os
import tempfile
import shutil
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import docker
from dataclasses import dataclass, asdict

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class SandboxConfig:
    """Configuration for a testing sandbox."""
    name: str
    tier: str
    dependencies: List[str]
    services: List[str]
    environment_vars: Dict[str, str]
    volume_mounts: Dict[str, str]
    network_mode: str
    resource_limits: Dict[str, Any]

@dataclass
class TestResult:
    """Result of a test run."""
    test_id: str
    sandbox_name: str
    started_at: str
    completed_at: str
    status: str  # passed, failed, error
    exit_code: int
    output: str
    logs: str
    artifacts: List[str]
    metrics: Dict[str, Any]

class DockerSandboxEnvironment:
    def __init__(self):
        self.client = docker.from_env()
        self.sandboxes_dir = 'dependency_management/testing/sandboxes'
        self.test_results_dir = 'dependency_management/testing/results'
        os.makedirs(self.sandboxes_dir, exist_ok=True)
        os.makedirs(self.test_results_dir, exist_ok=True)
    
    def create_sandbox_config(self, tier: str, dependencies: List[str] = None) -> SandboxConfig:
        """Create sandbox configuration based on tier."""
        if dependencies is None:
            dependencies = []
        
        # Base services for all sandboxes
        base_services = ['postgres', 'redis', 'kafka', 'zookeeper']
        
        # Tier-specific configurations
        if tier == 'tier1':
            services = base_services + ['nautilus_trader_engine', 'schema-registry']
            environment_vars = {
                'TEST_MODE': 'true',
                'LOG_LEVEL': 'DEBUG',
                'DEPENDENCY_TIER': 'tier1'
            }
            resource_limits = {
                'cpus': 2.0,
                'memory': '4g'
            }
        elif tier == 'tier2':
            services = base_services + ['fastapi', 'langchain', 'quantlib']
            environment_vars = {
                'TEST_MODE': 'true',
                'LOG_LEVEL': 'INFO',
                'DEPENDENCY_TIER': 'tier2'
            }
            resource_limits = {
                'cpus': 1.5,
                'memory': '3g'
            }
        elif tier == 'tier3':
            services = base_services + ['nextjs', 'react', 'lobe-chat']
            environment_vars = {
                'TEST_MODE': 'true',
                'LOG_LEVEL': 'INFO',
                'DEPENDENCY_TIER': 'tier3'
            }
            resource_limits = {
                'cpus': 1.0,
                'memory': '2g'
            }
        else:  # tier4
            services = base_services + ['prometheus', 'grafana', 'keycloak']
            environment_vars = {
                'TEST_MODE': 'true',
                'LOG_LEVEL': 'INFO',
                'DEPENDENCY_TIER': 'tier4'
            }
            resource_limits = {
                'cpus': 1.0,
                'memory': '2g'
            }
        
        # Add specified dependencies
        services.extend(dependencies)
        
        return SandboxConfig(
            name=f"test-sandbox-{tier}-{int(datetime.now().timestamp())}",
            tier=tier,
            dependencies=dependencies,
            services=services,
            environment_vars=environment_vars,
            volume_mounts={
                './data/mock_data': '/app/mock_data',
                './logs': '/app/logs'
            },
            network_mode='bridge',
            resource_limits=resource_limits
        )
    
    def generate_docker_compose(self, config: SandboxConfig) -> str:
        """Generate docker-compose.yml for the sandbox."""
        compose_content = {
            'version': '3.8',
            'services': {},
            'networks': {
                'test-network': {
                    'driver': 'bridge'
                }
            },
            'volumes': {}
        }
        
        # Add services
        for service in config.services:
            service_config = self._get_service_config(service, config)
            if service_config:
                compose_content['services'][service] = service_config
        
        # Add networks
        for service in compose_content['services']:
            compose_content['services'][service]['networks'] = ['test-network']
        
        # Add volumes
        for local_path, container_path in config.volume_mounts.items():
            volume_name = local_path.replace('./', '').replace('/', '_').replace('.', '_')
            compose_content['volumes'][volume_name] = None
            # Mount to first service as example
            if compose_content['services']:
                first_service = next(iter(compose_content['services']))
                if 'volumes' not in compose_content['services'][first_service]:
                    compose_content['services'][first_service]['volumes'] = []
                compose_content['services'][first_service]['volumes'].append(f"{volume_name}:{container_path}")
        
        # Convert to YAML-like string
        import yaml
        return yaml.dump(compose_content, default_flow_style=False)
    
    def _get_service_config(self, service_name: str, config: SandboxConfig) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific service."""
        # This would typically load from template files or a service registry
        # For demo purposes, we'll create basic configurations
        
        base_configs = {
            'postgres': {
                'image': 'postgres:15-alpine',
                'environment': {
                    'POSTGRES_DB': 'test_db',
                    'POSTGRES_USER': 'test_user',
                    'POSTGRES_PASSWORD': 'test_password'
                },
                'healthcheck': {
                    'test': ['CMD-SHELL', 'pg_isready -U test_user'],
                    'interval': '10s',
                    'timeout': '5s',
                    'retries': 5
                }
            },
            'redis': {
                'image': 'redis:7-alpine',
                'command': 'redis-server --requirepass test_password',
                'healthcheck': {
                    'test': ['CMD', 'redis-cli', '-a', 'test_password', 'ping'],
                    'interval': '10s',
                    'timeout': '3s',
                    'retries': 3
                }
            },
            'kafka': {
                'image': 'confluentinc/cp-kafka:7.4.0',
                'environment': {
                    'KAFKA_BROKER_ID': '1',
                    'KAFKA_ZOOKEEPER_CONNECT': 'zookeeper:2181',
                    'KAFKA_ADVERTISED_LISTENERS': 'PLAINTEXT://kafka:9092',
                    'KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR': '1'
                },
                'healthcheck': {
                    'test': ['CMD', 'kafka-broker-api-versions', '--bootstrap-server', 'localhost:9092'],
                    'interval': '30s',
                    'timeout': '10s',
                    'retries': 5
                }
            },
            'zookeeper': {
                'image': 'confluentinc/cp-zookeeper:7.4.0',
                'environment': {
                    'ZOOKEEPER_CLIENT_PORT': '2181',
                    'ZOOKEEPER_TICK_TIME': '2000'
                }
            },
            'nautilus_trader_engine': {
                'build': {
                    'context': '.',
                    'dockerfile': 'nautilus_trader_engine/Dockerfile'
                },
                'environment': config.environment_vars,
                'depends_on': ['kafka', 'postgres', 'redis']
            },
            'schema-registry': {
                'image': 'confluentinc/cp-schema-registry:7.4.0',
                'environment': {
                    'SCHEMA_REGISTRY_HOST_NAME': 'schema-registry',
                    'SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS': 'kafka:9092',
                    'SCHEMA_REGISTRY_LISTENERS': 'http://0.0.0.0:8081'
                },
                'depends_on': ['kafka']
            }
        }
        
        # Add resource limits
        service_config = base_configs.get(service_name, {
            'image': f'{service_name}:latest',
            'environment': config.environment_vars
        })
        
        if config.resource_limits:
            service_config['deploy'] = {
                'resources': {
                    'limits': config.resource_limits
                }
            }
        
        return service_config
    
    def create_sandbox(self, config: SandboxConfig) -> str:
        """Create a testing sandbox environment."""
        sandbox_path = os.path.join(self.sandboxes_dir, config.name)
        os.makedirs(sandbox_path, exist_ok=True)
        
        # Generate docker-compose.yml
        compose_content = self.generate_docker_compose(config)
        compose_file = os.path.join(sandbox_path, 'docker-compose.yml')
        
        with open(compose_file, 'w') as f:
            f.write(compose_content)
        
        # Create environment file
        env_file = os.path.join(sandbox_path, '.env')
        with open(env_file, 'w') as f:
            for key, value in config.environment_vars.items():
                f.write(f"{key}={value}\n")
        
        # Create config file
        config_file = os.path.join(sandbox_path, 'sandbox_config.json')
        with open(config_file, 'w') as f:
            json.dump(asdict(config), f, indent=2)
        
        logger.info(f"Sandbox created at {sandbox_path}")
        return sandbox_path
    
    def start_sandbox(self, sandbox_path: str) -> bool:
        """Start the sandbox environment."""
        try:
            # Change to sandbox directory
            original_dir = os.getcwd()
            os.chdir(sandbox_path)
            
            # Start services
            result = subprocess.run(
                ['docker-compose', 'up', '-d'],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            os.chdir(original_dir)
            
            if result.returncode == 0:
                logger.info(f"Sandbox started successfully: {sandbox_path}")
                return True
            else:
                logger.error(f"Failed to start sandbox: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting sandbox: {e}")
            return False
    
    def stop_sandbox(self, sandbox_path: str) -> bool:
        """Stop the sandbox environment."""
        try:
            # Change to sandbox directory
            original_dir = os.getcwd()
            os.chdir(sandbox_path)
            
            # Stop services
            result = subprocess.run(
                ['docker-compose', 'down'],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            os.chdir(original_dir)
            
            if result.returncode == 0:
                logger.info(f"Sandbox stopped successfully: {sandbox_path}")
                return True
            else:
                logger.error(f"Failed to stop sandbox: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error stopping sandbox: {e}")
            return False
    
    def run_tests_in_sandbox(self, sandbox_path: str, test_command: str) -> TestResult:
        """Run tests in the sandbox environment."""
        test_id = f"test_{int(datetime.now().timestamp())}"
        started_at = datetime.now().isoformat()
        
        try:
            # Change to sandbox directory
            original_dir = os.getcwd()
            os.chdir(sandbox_path)
            
            # Run test command
            result = subprocess.run(
                test_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            os.chdir(original_dir)
            
            # Get container logs
            logs = self._get_sandbox_logs(sandbox_path)
            
            # Create test result
            test_result = TestResult(
                test_id=test_id,
                sandbox_name=os.path.basename(sandbox_path),
                started_at=started_at,
                completed_at=datetime.now().isoformat(),
                status='passed' if result.returncode == 0 else 'failed',
                exit_code=result.returncode,
                output=result.stdout,
                logs=logs,
                artifacts=[],
                metrics={
                    'duration_seconds': (datetime.fromisoformat(datetime.now().isoformat()) - 
                                       datetime.fromisoformat(started_at)).total_seconds()
                }
            )
            
            # Save test result
            self._save_test_result(test_result)
            
            return test_result
            
        except subprocess.TimeoutExpired:
            os.chdir(original_dir)
            test_result = TestResult(
                test_id=test_id,
                sandbox_name=os.path.basename(sandbox_path),
                started_at=started_at,
                completed_at=datetime.now().isoformat(),
                status='error',
                exit_code=124,  # Timeout exit code
                output="Test timed out",
                logs="",
                artifacts=[],
                metrics={
                    'duration_seconds': 600
                }
            )
            self._save_test_result(test_result)
            return test_result
            
        except Exception as e:
            os.chdir(original_dir)
            test_result = TestResult(
                test_id=test_id,
                sandbox_name=os.path.basename(sandbox_path),
                started_at=started_at,
                completed_at=datetime.now().isoformat(),
                status='error',
                exit_code=1,
                output=str(e),
                logs="",
                artifacts=[],
                metrics={}
            )
            self._save_test_result(test_result)
            return test_result
    
    def _get_sandbox_logs(self, sandbox_path: str) -> str:
        """Get logs from sandbox containers."""
        try:
            original_dir = os.getcwd()
            os.chdir(sandbox_path)
            
            result = subprocess.run(
                ['docker-compose', 'logs'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            os.chdir(original_dir)
            return result.stdout
        except Exception as e:
            logger.error(f"Error getting sandbox logs: {e}")
            return ""
    
    def _save_test_result(self, test_result: TestResult):
        """Save test result to file."""
        try:
            filename = f"test_result_{test_result.test_id}.json"
            filepath = os.path.join(self.test_results_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(asdict(test_result), f, indent=2)
                
            logger.info(f"Test result saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving test result: {e}")
    
    def create_rollback_script(self, sandbox_path: str, original_state: Dict[str, Any]) -> str:
        """Create rollback script for the sandbox."""
        rollback_script = f"""#!/bin/bash
# Rollback script for {os.path.basename(sandbox_path)}
# Generated at {datetime.now().isoformat()}

echo "Rolling back sandbox environment..."

# Stop current sandbox
docker-compose -f {sandbox_path}/docker-compose.yml down

# Restore original state
# This is a placeholder - in a real implementation, you would restore
# the original dependency versions, configurations, etc.

echo "Rollback completed."
"""
        
        script_path = os.path.join(sandbox_path, 'rollback.sh')
        with open(script_path, 'w') as f:
            f.write(rollback_script)
        
        # Make executable
        os.chmod(script_path, 0o755)
        
        return script_path
    
    def cleanup_sandbox(self, sandbox_path: str) -> bool:
        """Clean up sandbox environment."""
        try:
            # Stop sandbox if running
            self.stop_sandbox(sandbox_path)
            
            # Remove sandbox directory
            shutil.rmtree(sandbox_path, ignore_errors=True)
            
            logger.info(f"Sandbox cleaned up: {sandbox_path}")
            return True
        except Exception as e:
            logger.error(f"Error cleaning up sandbox: {e}")
            return False

def main():
    """Main function to demonstrate sandbox environment."""
    print("Starting Docker-based Testing Sandbox Environment...")
    
    sandbox_env = DockerSandboxEnvironment()
    
    # Create sandbox configurations for different tiers
    print("\n=== CREATING SANDBOX CONFIGURATIONS ===")
    
    # Tier 1 sandbox (critical dependencies)
    tier1_config = sandbox_env.create_sandbox_config('tier1', ['nautilus_trader'])
    print(f"Created Tier 1 config: {tier1_config.name}")
    
    # Tier 2 sandbox (important dependencies)
    tier2_config = sandbox_env.create_sandbox_config('tier2', ['langchain', 'fastapi'])
    print(f"Created Tier 2 config: {tier2_config.name}")
    
    # Create actual sandboxes
    print("\n=== CREATING SANDBOXES ===")
    
    # Create Tier 1 sandbox
    tier1_sandbox_path = sandbox_env.create_sandbox(tier1_config)
    print(f"Created Tier 1 sandbox at: {tier1_sandbox_path}")
    
    # Create Tier 2 sandbox
    tier2_sandbox_path = sandbox_env.create_sandbox(tier2_config)
    print(f"Created Tier 2 sandbox at: {tier2_sandbox_path}")
    
    # Show sandbox structure
    print("\n=== SANDBOX STRUCTURE ===")
    for sandbox_path in [tier1_sandbox_path, tier2_sandbox_path]:
        print(f"\nSandbox: {os.path.basename(sandbox_path)}")
        try:
            files = os.listdir(sandbox_path)
            for file in files:
                print(f"  - {file}")
        except Exception as e:
            print(f"  Error listing files: {e}")
    
    # Demonstrate rollback script creation
    print("\n=== CREATING ROLLBACK SCRIPTS ===")
    rollback_script1 = sandbox_env.create_rollback_script(tier1_sandbox_path, {})
    print(f"Created rollback script: {rollback_script1}")
    
    rollback_script2 = sandbox_env.create_rollback_script(tier2_sandbox_path, {})
    print(f"Created rollback script: {rollback_script2}")
    
    print("\nDocker-based Testing Sandbox Environment demonstration completed.")
    print("Note: Actual sandbox startup and testing requires Docker to be running.")
    return 0

if __name__ == "__main__":
    sys.exit(main())