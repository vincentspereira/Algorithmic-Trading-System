#!/usr/bin/env python3
"""
Docker Management Script for Nautilus Trader Engine.

This script provides comprehensive Docker container management,
including building, deployment, monitoring, and maintenance operations.

Features:
- Automated container lifecycle management
- Multi-environment deployment support
- Health monitoring and auto-healing
- Log aggregation and analysis
- Backup and restore operations
- Security scanning and updates

Usage:
    python scripts/docker_manager.py [command] [options]

Commands:
    build       Build Docker images
    deploy      Deploy containers to environment
    monitor     Monitor container health and performance
    logs        Aggregate and analyze container logs
    backup      Create backups of persistent data
    restore     Restore data from backups
    cleanup     Clean up unused containers and images
    security    Run security scans on containers
"""

import os
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DOCKER_DIR = PROJECT_ROOT / "docker"
COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"
OVERRIDE_FILE = PROJECT_ROOT / "docker-compose.override.yml"


class DockerManager:
    """
    Comprehensive Docker container management for Nautilus Trader Engine.

    Provides high-level operations for container lifecycle, monitoring,
    and maintenance with production-grade reliability features.
    """

    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.docker_dir = DOCKER_DIR
        self.compose_file = COMPOSE_FILE
        self.override_file = OVERRIDE_FILE

    def run_command(self, command: List[str], cwd: Optional[Path] = None,
                   capture_output: bool = False) -> subprocess.CompletedProcess:
        """Run a shell command with proper error handling."""
        try:
            logger.info(f"Running: {' '.join(command)}")
            result = subprocess.run(
                command,
                cwd=cwd or self.project_root,
                capture_output=capture_output,
                text=True,
                check=True
            )
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e}")
            logger.error(f"stdout: {e.stdout}")
            logger.error(f"stderr: {e.stderr}")
            raise

    def build_images(self, services: Optional[List[str]] = None,
                    no_cache: bool = False, parallel: bool = True) -> bool:
        """Build Docker images."""
        logger.info("Building Docker images...")

        cmd = ["docker-compose", "-f", str(self.compose_file)]

        if self.override_file.exists():
            cmd.extend(["-f", str(self.override_file)])

        cmd.append("build")

        if services:
            cmd.extend(services)

        if no_cache:
            cmd.append("--no-cache")

        if parallel:
            cmd.append("--parallel")

        try:
            self.run_command(cmd)
            logger.info("✓ Images built successfully")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to build images: {e}")
            return False

    def deploy_containers(self, environment: str = "production",
                         services: Optional[List[str]] = None,
                         scale: Optional[Dict[str, int]] = None) -> bool:
        """Deploy containers to specified environment."""
        logger.info(f"Deploying to {environment} environment...")

        # Set environment-specific compose files
        compose_files = [str(self.compose_file)]

        if environment == "development":
            if self.override_file.exists():
                compose_files.append(str(self.override_file))
        elif environment == "testing":
            # Could add testing-specific overrides
            pass

        cmd = ["docker-compose"]
        for cf in compose_files:
            cmd.extend(["-f", cf])

        cmd.append("up")
        cmd.append("-d")

        if services:
            cmd.extend(services)

        if scale:
            for service, count in scale.items():
                cmd.extend(["--scale", f"{service}={count}"])

        try:
            self.run_command(cmd)
            logger.info(f"✓ Containers deployed to {environment}")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to deploy containers: {e}")
            return False

    def monitor_containers(self, services: Optional[List[str]] = None,
                          watch: bool = False) -> Dict[str, Any]:
        """Monitor container health and performance."""
        logger.info("Monitoring containers...")

        # Get container stats
        cmd = ["docker", "stats", "--no-stream", "--format", "json"]

        if services:
            # Filter by service names (this is simplified)
            containers = self._get_containers_by_service(services)
            if containers:
                cmd.extend(containers)

        try:
            result = self.run_command(cmd, capture_output=True)
            stats = result.stdout.strip().split('\n')
            stats_data = [json.loads(line) for line in stats if line.strip()]

            # Get container health
            health_data = self._get_container_health(services)

            monitoring_data = {
                "timestamp": datetime.now().isoformat(),
                "stats": stats_data,
                "health": health_data,
                "summary": self._summarize_monitoring(stats_data, health_data)
            }

            if not watch:
                self._display_monitoring(monitoring_data)
            else:
                # In watch mode, continuously monitor
                self._watch_containers(services)

            return monitoring_data

        except Exception as e:
            logger.error(f"✗ Failed to monitor containers: {e}")
            return {}

    def aggregate_logs(self, services: Optional[List[str]] = None,
                      since: Optional[str] = None, follow: bool = False) -> bool:
        """Aggregate and analyze container logs."""
        logger.info("Aggregating container logs...")

        cmd = ["docker-compose", "-f", str(self.compose_file)]

        if self.override_file.exists():
            cmd.extend(["-f", str(self.override_file)])

        cmd.append("logs")

        if follow:
            cmd.append("-f")

        if since:
            cmd.extend(["--since", since])

        if services:
            cmd.extend(services)

        try:
            if follow:
                # For follow mode, don't capture output
                subprocess.run(cmd, cwd=self.project_root)
            else:
                result = self.run_command(cmd, capture_output=True)
                self._analyze_logs(result.stdout)

            return True
        except Exception as e:
            logger.error(f"✗ Failed to aggregate logs: {e}")
            return False

    def backup_data(self, services: Optional[List[str]] = None,
                   destination: Optional[Path] = None) -> bool:
        """Create backups of persistent data."""
        logger.info("Creating data backups...")

        if destination is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            destination = self.project_root / "backups" / f"backup_{timestamp}"

        destination.mkdir(parents=True, exist_ok=True)

        # Services that have persistent data
        data_services = {
            "postgres": self._backup_postgres,
            "redis": self._backup_redis,
            "prometheus": self._backup_prometheus,
            "grafana": self._backup_grafana
        }

        if services:
            data_services = {k: v for k, v in data_services.items() if k in services}

        success = True
        for service_name, backup_func in data_services.items():
            try:
                logger.info(f"Backing up {service_name}...")
                backup_func(destination / service_name)
                logger.info(f"✓ {service_name} backup completed")
            except Exception as e:
                logger.error(f"✗ {service_name} backup failed: {e}")
                success = False

        if success:
            logger.info(f"✓ All backups completed successfully in {destination}")
        else:
            logger.warning("⚠️ Some backups failed")

        return success

    def restore_data(self, backup_path: Path, services: Optional[List[str]] = None) -> bool:
        """Restore data from backups."""
        logger.info(f"Restoring data from {backup_path}...")

        if not backup_path.exists():
            logger.error(f"Backup path does not exist: {backup_path}")
            return False

        # Services that can be restored
        restore_services = {
            "postgres": self._restore_postgres,
            "redis": self._restore_redis,
            "prometheus": self._restore_prometheus,
            "grafana": self._restore_grafana
        }

        if services:
            restore_services = {k: v for k, v in restore_services.items() if k in services}

        success = True
        for service_name, restore_func in restore_services.items():
            service_backup = backup_path / service_name
            if service_backup.exists():
                try:
                    logger.info(f"Restoring {service_name}...")
                    restore_func(service_backup)
                    logger.info(f"✓ {service_name} restore completed")
                except Exception as e:
                    logger.error(f"✗ {service_name} restore failed: {e}")
                    success = False
            else:
                logger.warning(f"No backup found for {service_name}")

        if success:
            logger.info("✓ All restores completed successfully")
        else:
            logger.warning("⚠️ Some restores failed")

        return success

    def cleanup_containers(self, remove_images: bool = False,
                          remove_volumes: bool = False) -> bool:
        """Clean up unused containers and images."""
        logger.info("Cleaning up containers...")

        try:
            # Stop and remove containers
            self.run_command(["docker-compose", "down"])

            # Remove unused containers
            self.run_command(["docker", "container", "prune", "-f"])

            if remove_images:
                # Remove unused images
                self.run_command(["docker", "image", "prune", "-f"])

            if remove_volumes:
                # Remove unused volumes (dangerous!)
                logger.warning("Removing unused volumes...")
                self.run_command(["docker", "volume", "prune", "-f"])

            # Remove networks
            self.run_command(["docker", "network", "prune", "-f"])

            logger.info("✓ Cleanup completed")
            return True

        except Exception as e:
            logger.error(f"✗ Cleanup failed: {e}")
            return False

    def security_scan(self, services: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run security scans on containers."""
        logger.info("Running security scans...")

        results = {}

        # Get running containers
        containers = self._get_running_containers(services)

        for container in containers:
            container_name = container['Names'].lstrip('/')
            logger.info(f"Scanning {container_name}...")

            try:
                # Run Trivy security scan
                cmd = [
                    "docker", "run", "--rm",
                    "-v", "/var/run/docker.sock:/var/run/docker.sock",
                    "aquasec/trivy:latest", "image",
                    "--format", "json",
                    container['Image']
                ]

                result = self.run_command(cmd, capture_output=True)
                scan_results = json.loads(result.stdout)

                results[container_name] = {
                    "image": container['Image'],
                    "scan_time": datetime.now().isoformat(),
                    "vulnerabilities": scan_results.get('Results', []),
                    "summary": self._summarize_security_scan(scan_results)
                }

            except Exception as e:
                logger.error(f"Failed to scan {container_name}: {e}")
                results[container_name] = {"error": str(e)}

        # Display results
        self._display_security_results(results)

        return results

    def _get_containers_by_service(self, services: List[str]) -> List[str]:
        """Get container names by service."""
        try:
            result = self.run_command(
                ["docker-compose", "ps", "--format", "json"],
                capture_output=True
            )

            containers = [json.loads(line) for line in result.stdout.strip().split('\n') if line.strip()]
            service_containers = []

            for container in containers:
                container_name = container.get('Name', '')
                for service in services:
                    if service in container_name:
                        service_containers.append(container_name)
                        break

            return service_containers

        except Exception:
            return []

    def _get_container_health(self, services: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get container health status."""
        try:
            result = self.run_command(
                ["docker", "ps", "--format", "json"],
                capture_output=True
            )

            containers = [json.loads(line) for line in result.stdout.strip().split('\n') if line.strip()]
            health_data = {}

            for container in containers:
                name = container.get('Names', '').lstrip('/')
                if services and not any(s in name for s in services):
                    continue

                # Check health status (simplified)
                health_data[name] = {
                    "status": container.get('Status', ''),
                    "running": 'Up' in container.get('Status', ''),
                    "ports": container.get('Ports', '')
                }

            return health_data

        except Exception as e:
            logger.error(f"Failed to get container health: {e}")
            return {}

    def _display_monitoring(self, data: Dict[str, Any]):
        """Display monitoring data in a readable format."""
        print("\n" + "="*80)
        print("CONTAINER MONITORING REPORT")
        print("="*80)
        print(f"Timestamp: {data['timestamp']}")
        print()

        # Container stats
        print("CONTAINER STATISTICS:")
        print("-" * 50)
        for stat in data['stats']:
            name = stat.get('Name', 'Unknown')
            cpu = stat.get('CPUPerc', '0%')
            mem = stat.get('MemPerc', '0%')
            net = stat.get('NetIO', '0B/0B')
            block = stat.get('BlockIO', '0B/0B')

            print(f"{name}:")
            print(f"  CPU: {cpu}")
            print(f"  Memory: {mem}")
            print(f"  Network: {net}")
            print(f"  Block I/O: {block}")
            print()

        # Health summary
        summary = data['summary']
        print("HEALTH SUMMARY:")
        print("-" * 50)
        print(f"Total Containers: {summary['total_containers']}")
        print(f"Running: {summary['running']}")
        print(f"Healthy: {summary['healthy']}")
        print(f"CPU Usage: {summary['avg_cpu']:.1f}%")
        print(f"Memory Usage: {summary['avg_memory']:.1f}%")

    def _summarize_monitoring(self, stats: List[Dict], health: Dict) -> Dict[str, Any]:
        """Summarize monitoring data."""
        total_containers = len(health)
        running = sum(1 for h in health.values() if h['running'])

        if stats:
            avg_cpu = sum(float(s.get('CPUPerc', '0%').rstrip('%')) for s in stats) / len(stats)
            avg_mem = sum(float(s.get('MemPerc', '0%').rstrip('%')) for s in stats) / len(stats)
        else:
            avg_cpu = avg_mem = 0.0

        return {
            "total_containers": total_containers,
            "running": running,
            "healthy": running,  # Simplified
            "avg_cpu": avg_cpu,
            "avg_memory": avg_mem
        }

    def _get_running_containers(self, services: Optional[List[str]] = None) -> List[Dict]:
        """Get list of running containers."""
        try:
            result = self.run_command(
                ["docker", "ps", "--format", "json"],
                capture_output=True
            )

            containers = [json.loads(line) for line in result.stdout.strip().split('\n') if line.strip()]

            if services:
                # Filter containers by service name
                filtered = []
                for container in containers:
                    name = container.get('Names', '')
                    if any(service in name for service in services):
                        filtered.append(container)
                return filtered

            return containers

        except Exception as e:
            logger.error(f"Failed to get running containers: {e}")
            return []

    def _backup_postgres(self, destination: Path):
        """Backup PostgreSQL data."""
        cmd = [
            "docker-compose", "exec", "-T", "postgres",
            "pg_dump", "-U", "nautilus", "nautilus_trader"
        ]

        with open(destination / "backup.sql", 'w') as f:
            result = self.run_command(cmd, capture_output=True)
            f.write(result.stdout)

    def _backup_redis(self, destination: Path):
        """Backup Redis data."""
        cmd = [
            "docker", "run", "--rm",
            "--volumes-from", "nautilus-redis",
            "-v", f"{destination}:/backup",
            "alpine:latest",
            "cp", "/data/dump.rdb", "/backup/redis_dump.rdb"
        ]

        self.run_command(cmd)

    def _backup_prometheus(self, destination: Path):
        """Backup Prometheus data."""
        cmd = [
            "docker", "run", "--rm",
            "--volumes-from", "nautilus-prometheus",
            "-v", f"{destination}:/backup",
            "alpine:latest",
            "cp", "-r", "/prometheus", "/backup"
        ]

        self.run_command(cmd)

    def _backup_grafana(self, destination: Path):
        """Backup Grafana data."""
        cmd = [
            "docker", "run", "--rm",
            "--volumes-from", "nautilus-grafana",
            "-v", f"{destination}:/backup",
            "alpine:latest",
            "cp", "-r", "/var/lib/grafana", "/backup"
        ]

        self.run_command(cmd)

    def _restore_postgres(self, backup_path: Path):
        """Restore PostgreSQL data."""
        backup_file = backup_path / "backup.sql"
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")

        cmd = [
            "docker-compose", "exec", "-T", "postgres",
            "psql", "-U", "nautilus", "-d", "nautilus_trader"
        ]

        with open(backup_file, 'r') as f:
            result = subprocess.run(cmd, stdin=f, cwd=self.project_root, check=True)

    def _restore_redis(self, backup_path: Path):
        """Restore Redis data."""
        backup_file = backup_path / "redis_dump.rdb"
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")

        cmd = [
            "docker", "run", "--rm",
            "-v", f"{backup_file}:/backup/dump.rdb",
            "--volumes-from", "nautilus-redis",
            "alpine:latest",
            "cp", "/backup/dump.rdb", "/data/dump.rdb"
        ]

        self.run_command(cmd)

    def _restore_prometheus(self, backup_path: Path):
        """Restore Prometheus data."""
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{backup_path}:/backup",
            "--volumes-from", "nautilus-prometheus",
            "alpine:latest",
            "cp", "-r", "/backup/prometheus/*", "/prometheus/"
        ]

        self.run_command(cmd)

    def _restore_grafana(self, backup_path: Path):
        """Restore Grafana data."""
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{backup_path}:/backup",
            "--volumes-from", "nautilus-grafana",
            "alpine:latest",
            "cp", "-r", "/backup/grafana/*", "/var/lib/grafana/"
        ]

        self.run_command(cmd)

    def _analyze_logs(self, logs: str):
        """Analyze container logs for patterns and issues."""
        # Simple log analysis - could be enhanced with ML
        lines = logs.split('\n')
        error_count = sum(1 for line in lines if 'ERROR' in line.upper())
        warning_count = sum(1 for line in lines if 'WARNING' in line.upper())

        print(f"Log Analysis:")
        print(f"  Total lines: {len(lines)}")
        print(f"  Errors: {error_count}")
        print(f"  Warnings: {warning_count}")

    def _display_security_results(self, results: Dict[str, Any]):
        """Display security scan results."""
        print("\n" + "="*80)
        print("SECURITY SCAN REPORT")
        print("="*80)

        total_vulnerabilities = 0
        critical_count = 0
        high_count = 0

        for container_name, result in results.items():
            if 'error' in result:
                print(f"❌ {container_name}: Scan failed - {result['error']}")
                continue

            vulns = result.get('vulnerabilities', [])
            vuln_count = len(vulns)
            total_vulnerabilities += vuln_count

            # Count severity levels
            for vuln in vulns:
                severity = vuln.get('Vulnerability', {}).get('Severity', '').upper()
                if severity == 'CRITICAL':
                    critical_count += 1
                elif severity == 'HIGH':
                    high_count += 1

            status = "✅" if vuln_count == 0 else "⚠️" if vuln_count < 5 else "❌"
            print(f"{status} {container_name}: {vuln_count} vulnerabilities")

        print(f"\nSUMMARY:")
        print(f"  Total Vulnerabilities: {total_vulnerabilities}")
        print(f"  Critical: {critical_count}")
        print(f"  High: {high_count}")

        if total_vulnerabilities == 0:
            print("🎉 No vulnerabilities found!")
        elif critical_count > 0:
            print("🚨 Critical vulnerabilities detected - immediate action required!")
        elif high_count > 0:
            print("⚠️ High-severity vulnerabilities detected - review recommended")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Docker Management for Nautilus Trader Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Build command
    build_parser = subparsers.add_parser('build', help='Build Docker images')
    build_parser.add_argument('--services', nargs='*', help='Specific services to build')
    build_parser.add_argument('--no-cache', action='store_true', help='Build without cache')
    build_parser.add_argument('--no-parallel', action='store_true', help='Disable parallel builds')

    # Deploy command
    deploy_parser = subparsers.add_parser('deploy', help='Deploy containers')
    deploy_parser.add_argument('--environment', default='production',
                              choices=['production', 'development', 'testing'],
                              help='Deployment environment')
    deploy_parser.add_argument('--services', nargs='*', help='Specific services to deploy')
    deploy_parser.add_argument('--scale', action='append',
                              help='Scale services (format: service=count)')

    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Monitor containers')
    monitor_parser.add_argument('--services', nargs='*', help='Specific services to monitor')
    monitor_parser.add_argument('--watch', action='store_true', help='Continuously monitor')

    # Logs command
    logs_parser = subparsers.add_parser('logs', help='Aggregate container logs')
    logs_parser.add_argument('--services', nargs='*', help='Specific services')
    logs_parser.add_argument('--since', help='Show logs since timestamp')
    logs_parser.add_argument('--follow', action='store_true', help='Follow log output')

    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Create data backups')
    backup_parser.add_argument('--services', nargs='*', help='Specific services to backup')
    backup_parser.add_argument('--destination', help='Backup destination directory')

    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Restore data from backups')
    restore_parser.add_argument('backup_path', help='Path to backup directory')
    restore_parser.add_argument('--services', nargs='*', help='Specific services to restore')

    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up containers and images')
    cleanup_parser.add_argument('--remove-images', action='store_true',
                               help='Remove unused images')
    cleanup_parser.add_argument('--remove-volumes', action='store_true',
                               help='Remove unused volumes (dangerous!)')

    # Security command
    security_parser = subparsers.add_parser('security', help='Run security scans')
    security_parser.add_argument('--services', nargs='*', help='Specific services to scan')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    manager = DockerManager()

    try:
        if args.command == 'build':
            scale_dict = {}
            if hasattr(args, 'scale') and args.scale:
                for scale_arg in args.scale:
                    service, count = scale_arg.split('=')
                    scale_dict[service] = int(count)

            success = manager.build_images(
                services=getattr(args, 'services', None),
                no_cache=getattr(args, 'no_cache', False),
                parallel=not getattr(args, 'no_parallel', False)
            )

        elif args.command == 'deploy':
            scale_dict = {}
            if hasattr(args, 'scale') and args.scale:
                for scale_arg in args.scale:
                    service, count = scale_arg.split('=')
                    scale_dict[service] = int(count)

            success = manager.deploy_containers(
                environment=args.environment,
                services=getattr(args, 'services', None),
                scale=scale_dict
            )

        elif args.command == 'monitor':
            data = manager.monitor_containers(
                services=getattr(args, 'services', None),
                watch=getattr(args, 'watch', False)
            )
            success = bool(data)

        elif args.command == 'logs':
            success = manager.aggregate_logs(
                services=getattr(args, 'services', None),
                since=getattr(args, 'since', None),
                follow=getattr(args, 'follow', False)
            )

        elif args.command == 'backup':
            success = manager.backup_data(
                services=getattr(args, 'services', None),
                destination=Path(getattr(args, 'destination', None)) if getattr(args, 'destination', None) else None
            )

        elif args.command == 'restore':
            success = manager.restore_data(
                backup_path=Path(args.backup_path),
                services=getattr(args, 'services', None)
            )

        elif args.command == 'cleanup':
            success = manager.cleanup_containers(
                remove_images=getattr(args, 'remove_images', False),
                remove_volumes=getattr(args, 'remove_volumes', False)
            )

        elif args.command == 'security':
            results = manager.security_scan(
                services=getattr(args, 'services', None)
            )
            success = not any('error' in result for result in results.values())

        if success:
            print("✓ Command completed successfully")
            sys.exit(0)
        else:
            print("✗ Command failed")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()