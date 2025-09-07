"""Resource Monitor for system resource usage tracking."""

import random
from typing import Dict, Any
from datetime import datetime


class ResourceMonitor:
    """Monitors system resources including memory, CPU, and connections."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the resource monitor."""
        self.config = config or {}
        self.resource_snapshots = []
    
    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        # Simulate increasing memory usage
        base_memory = 100  # 100MB base
        growth = len(self.resource_snapshots) * 2  # 2MB per snapshot
        return base_memory + growth
    
    def get_cpu_usage_percent(self) -> float:
        """Get current CPU usage percentage."""
        # Simulate CPU usage fluctuation
        return random.uniform(20, 80)  # 20-80% CPU usage
    
    def get_active_connections(self) -> int:
        """Get current active connection count."""
        # Simulate active connections
        return min(1000, len(self.resource_snapshots) * 10)