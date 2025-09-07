#!/usr/bin/env python3
"""
Demonstration script for DockerOrchestrator

This script demonstrates the key functionality of the DockerOrchestrator class,
showing how it manages Docker containers, performs health checks, and monitors logs.
"""

import sys
import time
from pathlib import Path

# Add the framework directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent))

from docker_orchestrator import DockerOrchestrator, ContainerStatus, HealthStatus


def main():
    """Demonstrate DockerOrchestrator functionality"""
    print("=" * 80)
    print("DOCKER ORCHESTRATOR DEMONSTRATION")
    print("=" * 80)
    
    # Initialize DockerOrchestrator
    print("\n1. Initializing DockerOrchestrator...")
    orchestrator = DockerOrchestrator()
    print(f"   Project Root: {orchestrator.project_root}")
    print(f"   Compose Files: {orchestrator.compose_files}")
    print(f"   Docker Client Available: {orchestrator.docker_client is not None}")
    
    # Validate Docker environment
    print("\n2. Validating Docker environment...")
    success, errors = orchestrator.validate_docker_environment()
    print(f"   Validation Success: {success}")
    if errors:
        print("   Errors found:")
        for error in errors:
            print(f"     - {error}")
    else:
        print("   ✅ Docker environment is ready")
    
    if not success:
        print("\n⚠️ Docker environment validation failed. Some features may not work.")
        print("Please ensure Docker is installed and running.")
    
    # Get services from compose files
    print("\n3. Discovering services from compose files...")
    services = orchestrator._get_all_services_from_compose()
    print(f"   Found {len(services)} services:")
    for service in services[:10]:  # Show first 10
        print(f"     - {service}")
    if len(services) > 10:
        print(f"     ... and {len(services) - 10} more")
    
    # Get current orchestration status
    print("\n4. Getting current orchestration status...")
    status = orchestrator.get_orchestration_status()
    print(f"   Total Containers: {status.get('total_containers', 0)}")
    print(f"   Status Counts: {status.get('status_counts', {})}")
    print(f"   Health Counts: {status.get('health_counts', {})}")
    
    # Demonstrate container rebuild (dry run)
    print("\n5. Container rebuild demonstration...")
    print("   This would rebuild containers with --no-cache:")
    print("   Command: docker-compose -f docker-compose.yml -f docker-compose.databases.yml build --no-cache --pull")
    
    # Ask user if they want to proceed with actual operations
    if orchestrator.docker_client is not None:
        proceed = input("\n   Proceed with actual Docker operations? (y/N): ").lower().strip()
        
        if proceed == 'y':
            # Demonstrate service stack startup
            print("\n6. Starting service stack (limited services for demo)...")
            demo_services = ["postgres", "redis"]  # Start only essential services
            
            print(f"   Starting services: {demo_services}")
            result = orchestrator.start_service_stack(services=demo_services)
            
            print(f"   Startup Success: {result.success}")
            print(f"   Services Started: {result.services_started}")
            print(f"   Services Failed: {result.services_failed}")
            print(f"   Containers Healthy: {result.containers_healthy}")
            print(f"   Containers Unhealthy: {result.containers_unhealthy}")
            print(f"   Total Startup Time: {result.total_startup_time:.2f} seconds")
            
            if result.error_messages:
                print("   Errors:")
                for error in result.error_messages:
                    print(f"     - {error}")
            
            if result.warnings:
                print("   Warnings:")
                for warning in result.warnings:
                    print(f"     - {warning}")
            
            # Demonstrate health checks
            if result.success:
                print("\n7. Performing comprehensive health checks...")
                health_results = orchestrator.validate_container_health(timeout=60)
                
                print(f"   Health check results for {len(health_results)} containers:")
                for container_name, health_result in health_results.items():
                    status_icon = "✅" if health_result.status == HealthStatus.HEALTHY else "❌"
                    print(f"     {status_icon} {container_name}: {health_result.status.value}")
                    if health_result.response_time:
                        print(f"        Response time: {health_result.response_time:.3f}s")
                    if health_result.error_message:
                        print(f"        Error: {health_result.error_message}")
                
                # Demonstrate log monitoring
                print("\n8. Container log monitoring demonstration...")
                running_containers = [
                    name for name, info in orchestrator.containers_info.items()
                    if info.status == ContainerStatus.RUNNING
                ]
                
                if running_containers:
                    print(f"   Starting log monitoring for {len(running_containers)} containers...")
                    orchestrator.monitor_container_logs(containers=running_containers[:3])  # Monitor first 3
                    
                    print("   Log monitoring started (running in background)")
                    print("   Waiting 10 seconds to collect logs...")
                    time.sleep(10)
                    
                    # Get recent logs
                    print("\n   Recent logs from containers:")
                    for container_name in running_containers[:2]:  # Show logs from first 2
                        logs = orchestrator.get_container_logs(container_name, lines=5)
                        if logs:
                            print(f"     📋 {container_name} (last 5 lines):")
                            for log_entry in logs[-5:]:
                                print(f"        [{log_entry.level}] {log_entry.message[:100]}...")
                        else:
                            print(f"     📋 {container_name}: No recent logs")
                
                # Ask about cleanup
                cleanup = input("\n   Stop and cleanup demo services? (Y/n): ").lower().strip()
                if cleanup != 'n':
                    print("\n9. Stopping demo services...")
                    stop_success = orchestrator.stop_service_stack(services=demo_services)
                    print(f"   Stop Success: {stop_success}")
                    
                    if stop_success:
                        print("   ✅ Demo services stopped successfully")
                    else:
                        print("   ❌ Failed to stop some services")
            
        else:
            print("   Skipping actual Docker operations")
    
    else:
        print("\n6. Docker client not available - skipping live demonstrations")
        print("   The following operations would be available with Docker:")
        print("     - Container rebuild with --no-cache")
        print("     - Service stack startup with docker-compose up -d")
        print("     - Container health check validation")
        print("     - Real-time log monitoring")
        print("     - Service stack shutdown")
        print("     - Resource cleanup")
    
    # Show final status
    print("\n" + "=" * 80)
    print("DEMONSTRATION SUMMARY")
    print("=" * 80)
    
    final_status = orchestrator.get_orchestration_status()
    print(f"Docker Environment: {'✅ Ready' if orchestrator.docker_client else '❌ Not Available'}")
    print(f"Compose Files: {len(orchestrator.compose_files)} files")
    print(f"Discovered Services: {len(services)} services")
    print(f"Current Containers: {final_status.get('total_containers', 0)}")
    
    if orchestrator.docker_client:
        running_count = final_status.get('status_counts', {}).get('running', 0)
        healthy_count = final_status.get('health_counts', {}).get('healthy', 0)
        print(f"Running Containers: {running_count}")
        print(f"Healthy Containers: {healthy_count}")
    
    print("\nDockerOrchestrator demonstration completed!")
    print("\nKey Features Demonstrated:")
    print("  ✅ Docker environment validation")
    print("  ✅ Service discovery from compose files")
    print("  ✅ Container status monitoring")
    print("  ✅ Health check validation")
    print("  ✅ Log monitoring capabilities")
    print("  ✅ Service lifecycle management")


if __name__ == "__main__":
    main()