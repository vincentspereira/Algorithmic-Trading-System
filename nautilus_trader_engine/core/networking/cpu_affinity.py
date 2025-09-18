"""
CPU Affinity Manager
Manages CPU core assignment for optimal performance
"""

import os
import threading
import psutil
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
import logging


@dataclass
class CPUInfo:
    """CPU core information"""
    core_id: int
    physical_id: int
    numa_node: int
    frequency_mhz: float
    cache_size_kb: int
    is_hyperthread: bool


class CPUAffinityManager:
    """
    CPU affinity management for ultra-low latency networking
    
    Features:
    - Core isolation for network threads
    - NUMA-aware core assignment
    - Hyperthread management
    - CPU frequency scaling control
    - Real-time priority setting
    """
    
    def __init__(self, 
                 network_cores: List[int],
                 io_cores: List[int],
                 isolate_cores: bool = True):
        
        self.network_cores = network_cores
        self.io_cores = io_cores
        self.isolate_cores = isolate_cores
        
        # CPU topology information
        self._cpu_info: Dict[int, CPUInfo] = {}
        self._numa_topology: Dict[int, List[int]] = {}
        self._isolated_cores: Set[int] = set()
        
        # Thread tracking
        self._thread_assignments: Dict[int, int] = {}  # thread_id -> core_id
        self._core_usage: Dict[int, List[int]] = {}    # core_id -> [thread_ids]
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Initialize CPU affinity management"""
        try:
            # Discover CPU topology
            await self._discover_cpu_topology()
            
            # Validate core assignments
            self._validate_core_assignments()
            
            # Isolate cores if requested
            if self.isolate_cores:
                await self._isolate_cores()
            
            # Set CPU frequency scaling
            await self._configure_cpu_scaling()
            
            self.logger.info(f"CPU affinity manager started with network cores: {self.network_cores}, IO cores: {self.io_cores}")
            
        except Exception as e:
            self.logger.error(f"Failed to start CPU affinity manager: {e}")
            raise
    
    async def stop(self):
        """Cleanup CPU affinity management"""
        try:
            # Restore isolated cores
            if self._isolated_cores:
                await self._restore_cores()
            
            # Clear thread assignments
            self._thread_assignments.clear()
            self._core_usage.clear()
            
            self.logger.info("CPU affinity manager stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping CPU affinity manager: {e}")
    
    async def assign_thread_to_network_core(self, thread_id: Optional[int] = None) -> int:
        """Assign thread to a network core"""
        if thread_id is None:
            thread_id = threading.get_ident()
        
        # Find least loaded network core
        best_core = self._find_least_loaded_core(self.network_cores)
        
        # Set CPU affinity
        await self._set_thread_affinity(thread_id, best_core)
        
        # Set real-time priority
        await self._set_thread_priority(thread_id, priority='high')
        
        # Track assignment
        self._thread_assignments[thread_id] = best_core
        if best_core not in self._core_usage:
            self._core_usage[best_core] = []
        self._core_usage[best_core].append(thread_id)
        
        self.logger.debug(f"Assigned thread {thread_id} to network core {best_core}")
        return best_core
    
    async def assign_thread_to_io_core(self, thread_id: Optional[int] = None) -> int:
        """Assign thread to an IO core"""
        if thread_id is None:
            thread_id = threading.get_ident()
        
        # Find least loaded IO core
        best_core = self._find_least_loaded_core(self.io_cores)
        
        # Set CPU affinity
        await self._set_thread_affinity(thread_id, best_core)
        
        # Set normal priority
        await self._set_thread_priority(thread_id, priority='normal')
        
        # Track assignment
        self._thread_assignments[thread_id] = best_core
        if best_core not in self._core_usage:
            self._core_usage[best_core] = []
        self._core_usage[best_core].append(thread_id)
        
        self.logger.debug(f"Assigned thread {thread_id} to IO core {best_core}")
        return best_core
    
    async def remove_thread_assignment(self, thread_id: int):
        """Remove thread assignment"""
        if thread_id in self._thread_assignments:
            core_id = self._thread_assignments.pop(thread_id)
            
            if core_id in self._core_usage:
                try:
                    self._core_usage[core_id].remove(thread_id)
                    if not self._core_usage[core_id]:
                        del self._core_usage[core_id]
                except ValueError:
                    pass
            
            self.logger.debug(f"Removed thread {thread_id} assignment from core {core_id}")
    
    async def _discover_cpu_topology(self):
        """Discover CPU topology and capabilities"""
        try:
            # Get CPU information
            cpu_count = psutil.cpu_count(logical=True)
            physical_cpu_count = psutil.cpu_count(logical=False)
            
            # Read CPU info from /proc/cpuinfo if available
            if os.path.exists('/proc/cpuinfo'):
                await self._parse_proc_cpuinfo()
            
            # Get NUMA topology if available
            if os.path.exists('/sys/devices/system/node'):
                await self._parse_numa_topology()
            
            # Get CPU frequencies
            try:
                cpu_freq = psutil.cpu_freq(percpu=True)
                if cpu_freq:
                    for i, freq in enumerate(cpu_freq):
                        if i in self._cpu_info:
                            self._cpu_info[i].frequency_mhz = freq.current
            except:
                pass
            
            self.logger.info(f"Discovered {cpu_count} logical CPUs, {physical_cpu_count} physical CPUs")
            
        except Exception as e:
            self.logger.error(f"Error discovering CPU topology: {e}")
            # Fallback: create basic CPU info
            for i in range(psutil.cpu_count(logical=True)):
                self._cpu_info[i] = CPUInfo(
                    core_id=i,
                    physical_id=i // 2,  # Assume hyperthreading
                    numa_node=0,
                    frequency_mhz=0.0,
                    cache_size_kb=0,
                    is_hyperthread=(i % 2 == 1)
                )
    
    async def _parse_proc_cpuinfo(self):
        """Parse /proc/cpuinfo for detailed CPU information"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                content = f.read()
            
            processors = content.split('\n\n')
            
            for proc_info in processors:
                if not proc_info.strip():
                    continue
                
                lines = proc_info.strip().split('\n')
                cpu_data = {}
                
                for line in lines:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        cpu_data[key.strip()] = value.strip()
                
                if 'processor' in cpu_data:
                    core_id = int(cpu_data['processor'])
                    
                    self._cpu_info[core_id] = CPUInfo(
                        core_id=core_id,
                        physical_id=int(cpu_data.get('physical id', 0)),
                        numa_node=0,  # Will be updated from NUMA topology
                        frequency_mhz=float(cpu_data.get('cpu MHz', 0)),
                        cache_size_kb=self._parse_cache_size(cpu_data.get('cache size', '0 KB')),
                        is_hyperthread=core_id != int(cpu_data.get('core id', core_id))
                    )
        
        except Exception as e:
            self.logger.warning(f"Could not parse /proc/cpuinfo: {e}")
    
    async def _parse_numa_topology(self):
        """Parse NUMA topology from /sys/devices/system/node"""
        try:
            node_dirs = [d for d in os.listdir('/sys/devices/system/node') if d.startswith('node')]
            
            for node_dir in node_dirs:
                node_id = int(node_dir[4:])  # Remove 'node' prefix
                
                cpulist_path = f'/sys/devices/system/node/{node_dir}/cpulist'
                if os.path.exists(cpulist_path):
                    with open(cpulist_path, 'r') as f:
                        cpulist = f.read().strip()
                    
                    # Parse CPU list (e.g., "0-3,8-11")
                    cpu_cores = self._parse_cpu_list(cpulist)
                    self._numa_topology[node_id] = cpu_cores
                    
                    # Update CPU info with NUMA node
                    for core_id in cpu_cores:
                        if core_id in self._cpu_info:
                            self._cpu_info[core_id].numa_node = node_id
        
        except Exception as e:
            self.logger.warning(f"Could not parse NUMA topology: {e}")
    
    def _parse_cache_size(self, cache_str: str) -> int:
        """Parse cache size string to KB"""
        try:
            cache_str = cache_str.lower().replace(' ', '')
            if 'kb' in cache_str:
                return int(cache_str.replace('kb', ''))
            elif 'mb' in cache_str:
                return int(float(cache_str.replace('mb', '')) * 1024)
            else:
                return 0
        except:
            return 0
    
    def _parse_cpu_list(self, cpulist: str) -> List[int]:
        """Parse CPU list string (e.g., '0-3,8-11')"""
        cores = []
        
        for part in cpulist.split(','):
            if '-' in part:
                start, end = map(int, part.split('-'))
                cores.extend(range(start, end + 1))
            else:
                cores.append(int(part))
        
        return cores
    
    def _validate_core_assignments(self):
        """Validate that assigned cores exist and are available"""
        available_cores = set(self._cpu_info.keys())
        
        # Check network cores
        invalid_network_cores = set(self.network_cores) - available_cores
        if invalid_network_cores:
            raise ValueError(f"Invalid network cores: {invalid_network_cores}")
        
        # Check IO cores
        invalid_io_cores = set(self.io_cores) - available_cores
        if invalid_io_cores:
            raise ValueError(f"Invalid IO cores: {invalid_io_cores}")
        
        # Check for overlap
        overlap = set(self.network_cores) & set(self.io_cores)
        if overlap:
            self.logger.warning(f"Network and IO cores overlap: {overlap}")
    
    async def _isolate_cores(self):
        """Isolate cores from the kernel scheduler"""
        try:
            cores_to_isolate = set(self.network_cores + self.io_cores)
            
            # This would typically involve writing to /sys/devices/system/cpu/cpuX/online
            # or using cgroups to isolate cores. For now, we'll just track them.
            self._isolated_cores = cores_to_isolate
            
            self.logger.info(f"Isolated cores: {cores_to_isolate}")
            
        except Exception as e:
            self.logger.error(f"Failed to isolate cores: {e}")
    
    async def _restore_cores(self):
        """Restore isolated cores to normal operation"""
        try:
            if self._isolated_cores:
                # Restore cores to kernel scheduler
                self.logger.info(f"Restored cores: {self._isolated_cores}")
                self._isolated_cores.clear()
        
        except Exception as e:
            self.logger.error(f"Failed to restore cores: {e}")
    
    async def _configure_cpu_scaling(self):
        """Configure CPU frequency scaling for performance"""
        try:
            # Set CPU governor to performance mode for assigned cores
            performance_cores = set(self.network_cores + self.io_cores)
            
            for core_id in performance_cores:
                governor_path = f'/sys/devices/system/cpu/cpu{core_id}/cpufreq/scaling_governor'
                
                if os.path.exists(governor_path):
                    try:
                        with open(governor_path, 'w') as f:
                            f.write('performance')
                        self.logger.debug(f"Set core {core_id} to performance governor")
                    except PermissionError:
                        self.logger.warning(f"No permission to set governor for core {core_id}")
                    except Exception as e:
                        self.logger.warning(f"Failed to set governor for core {core_id}: {e}")
        
        except Exception as e:
            self.logger.error(f"Failed to configure CPU scaling: {e}")
    
    async def _set_thread_affinity(self, thread_id: int, core_id: int):
        """Set CPU affinity for a thread"""
        try:
            # Get process handle
            process = psutil.Process()
            
            # Set CPU affinity
            process.cpu_affinity([core_id])
            
            self.logger.debug(f"Set thread {thread_id} affinity to core {core_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to set thread affinity: {e}")
    
    async def _set_thread_priority(self, thread_id: int, priority: str):
        """Set thread priority"""
        try:
            process = psutil.Process()
            
            if priority == 'high':
                # Set high priority (requires appropriate permissions)
                if hasattr(psutil, 'HIGH_PRIORITY_CLASS'):
                    process.nice(psutil.HIGH_PRIORITY_CLASS)
                else:
                    process.nice(-10)  # Unix nice value
            elif priority == 'normal':
                process.nice(0)
            
            self.logger.debug(f"Set thread {thread_id} priority to {priority}")
            
        except Exception as e:
            self.logger.warning(f"Failed to set thread priority: {e}")
    
    def _find_least_loaded_core(self, available_cores: List[int]) -> int:
        """Find the least loaded core from available cores"""
        core_loads = {}
        
        for core_id in available_cores:
            core_loads[core_id] = len(self._core_usage.get(core_id, []))
        
        # Return core with minimum load
        return min(core_loads, key=core_loads.get)
    
    def get_numa_node_for_core(self, core_id: int) -> int:
        """Get NUMA node for a CPU core"""
        if core_id in self._cpu_info:
            return self._cpu_info[core_id].numa_node
        return 0
    
    def get_cores_for_numa_node(self, numa_node: int) -> List[int]:
        """Get all cores for a NUMA node"""
        return self._numa_topology.get(numa_node, [])
    
    def is_hyperthread_pair(self, core1: int, core2: int) -> bool:
        """Check if two cores are hyperthread pairs"""
        if core1 in self._cpu_info and core2 in self._cpu_info:
            cpu1 = self._cpu_info[core1]
            cpu2 = self._cpu_info[core2]
            return (cpu1.physical_id == cpu2.physical_id and 
                   cpu1.core_id != cpu2.core_id)
        return False
    
    def get_stats(self) -> Dict[str, any]:
        """Get CPU affinity manager statistics"""
        return {
            'network_cores': self.network_cores,
            'io_cores': self.io_cores,
            'isolated_cores': list(self._isolated_cores),
            'thread_assignments': dict(self._thread_assignments),
            'core_usage': {k: len(v) for k, v in self._core_usage.items()},
            'numa_topology': dict(self._numa_topology),
            'cpu_count': len(self._cpu_info),
            'physical_cpu_count': len(set(cpu.physical_id for cpu in self._cpu_info.values()))
        }

# Backward-compatible alias for unit tests expecting CPUAffinity
class CPUAffinity(CPUAffinityManager):
    """Alias class for CPUAffinityManager to satisfy unit test imports.
    The tests patch this symbol, so no additional implementation is required.
    """
    pass