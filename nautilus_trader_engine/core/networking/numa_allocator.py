"""
NUMA Allocator
NUMA-aware memory allocation for optimal performance
"""

import mmap
import os
import ctypes
import ctypes.util
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
import logging


@dataclass
class MemoryRegion:
    """Memory region information"""
    address: int
    size: int
    numa_node: int
    is_huge_page: bool
    page_size: int


class NUMAAllocator:
    """
    NUMA-aware memory allocator
    
    Features:
    - NUMA node-specific allocation
    - Huge page support
    - Memory prefaulting
    - Memory binding policies
    - Zero-copy buffer management
    """
    
    def __init__(self, 
                 numa_node: Optional[int] = None,
                 memory_policy: str = "local",
                 enable_huge_pages: bool = True,
                 huge_page_size: int = 2 * 1024 * 1024):  # 2MB
        
        self.numa_node = numa_node
        self.memory_policy = memory_policy
        self.enable_huge_pages = enable_huge_pages
        self.huge_page_size = huge_page_size
        
        # Memory tracking
        self._allocated_regions: Dict[int, MemoryRegion] = {}
        self._total_allocated = 0
        
        # NUMA library
        self._libnuma = None
        self._numa_available = False
        
        # Huge page support
        self._huge_pages_available = False
        self._huge_page_path = None
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Initialize NUMA allocator"""
        try:
            # Load NUMA library
            await self._load_numa_library()
            
            # Check huge page support
            await self._check_huge_page_support()
            
            # Set memory policy
            if self._numa_available:
                await self._set_memory_policy()
            
            self.logger.info(f"NUMA allocator started (NUMA: {self._numa_available}, Huge pages: {self._huge_pages_available})")
            
        except Exception as e:
            self.logger.error(f"Failed to start NUMA allocator: {e}")
            # Continue without NUMA support
    
    async def stop(self):
        """Cleanup NUMA allocator"""
        try:
            # Free all allocated regions
            for address, region in list(self._allocated_regions.items()):
                await self.free_memory(address)
            
            self.logger.info("NUMA allocator stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping NUMA allocator: {e}")
    
    async def allocate_memory(self, 
                            size: int, 
                            numa_node: Optional[int] = None,
                            use_huge_pages: Optional[bool] = None,
                            prefault: bool = True) -> int:
        """
        Allocate NUMA-aware memory
        
        Args:
            size: Size in bytes
            numa_node: Specific NUMA node (None for default)
            use_huge_pages: Use huge pages if available
            prefault: Prefault pages to avoid page faults
            
        Returns:
            Memory address
        """
        try:
            target_numa_node = numa_node or self.numa_node or 0
            use_huge = use_huge_pages if use_huge_pages is not None else self.enable_huge_pages
            
            # Align size to page boundary
            page_size = self.huge_page_size if (use_huge and self._huge_pages_available) else 4096
            aligned_size = ((size + page_size - 1) // page_size) * page_size
            
            # Allocate memory
            if use_huge and self._huge_pages_available:
                address = await self._allocate_huge_pages(aligned_size, target_numa_node)
            else:
                address = await self._allocate_regular_pages(aligned_size, target_numa_node)
            
            # Prefault pages if requested
            if prefault:
                await self._prefault_pages(address, aligned_size)
            
            # Track allocation
            region = MemoryRegion(
                address=address,
                size=aligned_size,
                numa_node=target_numa_node,
                is_huge_page=(use_huge and self._huge_pages_available),
                page_size=page_size
            )
            
            self._allocated_regions[address] = region
            self._total_allocated += aligned_size
            
            self.logger.debug(f"Allocated {aligned_size} bytes at 0x{address:x} on NUMA node {target_numa_node}")
            
            return address
            
        except Exception as e:
            self.logger.error(f"Failed to allocate memory: {e}")
            raise
    
    async def free_memory(self, address: int):
        """Free allocated memory"""
        try:
            if address not in self._allocated_regions:
                raise ValueError(f"Address 0x{address:x} not found in allocated regions")
            
            region = self._allocated_regions[address]
            
            # Unmap memory
            if region.is_huge_page:
                await self._free_huge_pages(address, region.size)
            else:
                await self._free_regular_pages(address, region.size)
            
            # Update tracking
            del self._allocated_regions[address]
            self._total_allocated -= region.size
            
            self.logger.debug(f"Freed {region.size} bytes at 0x{address:x}")
            
        except Exception as e:
            self.logger.error(f"Failed to free memory at 0x{address:x}: {e}")
            raise
    
    async def bind_memory_to_node(self, address: int, size: int, numa_node: int):
        """Bind memory region to specific NUMA node"""
        try:
            if not self._numa_available:
                self.logger.warning("NUMA not available, cannot bind memory")
                return
            
            # Use mbind system call to bind memory
            if self._libnuma:
                # Create node mask
                nodemask = ctypes.c_ulong(1 << numa_node)
                
                # Call mbind
                result = self._libnuma.mbind(
                    ctypes.c_void_p(address),
                    ctypes.c_size_t(size),
                    ctypes.c_int(1),  # MPOL_BIND
                    ctypes.pointer(nodemask),
                    ctypes.c_ulong(64),  # maxnode
                    ctypes.c_int(0)   # flags
                )
                
                if result != 0:
                    raise OSError(f"mbind failed with result {result}")
                
                self.logger.debug(f"Bound memory 0x{address:x} to NUMA node {numa_node}")
        
        except Exception as e:
            self.logger.error(f"Failed to bind memory to NUMA node: {e}")
    
    async def get_memory_node(self, address: int) -> int:
        """Get NUMA node for memory address"""
        try:
            if not self._numa_available or not self._libnuma:
                return 0
            
            # Use get_mempolicy to get node
            node = ctypes.c_int()
            result = self._libnuma.get_mempolicy(
                ctypes.pointer(node),
                None,
                ctypes.c_ulong(0),
                ctypes.c_void_p(address),
                ctypes.c_ulong(1)  # MPOL_F_ADDR
            )
            
            if result == 0:
                return node.value
            else:
                return 0
        
        except Exception as e:
            self.logger.error(f"Failed to get memory node: {e}")
            return 0
    
    async def _load_numa_library(self):
        """Load NUMA library"""
        try:
            # Try to load libnuma
            libnuma_path = ctypes.util.find_library('numa')
            if libnuma_path:
                self._libnuma = ctypes.CDLL(libnuma_path)
                
                # Check if NUMA is available
                if hasattr(self._libnuma, 'numa_available'):
                    if self._libnuma.numa_available() == 0:
                        self._numa_available = True
                        self.logger.info("NUMA library loaded successfully")
                    else:
                        self.logger.warning("NUMA library loaded but NUMA not available")
                else:
                    self.logger.warning("NUMA library loaded but numa_available not found")
            else:
                self.logger.warning("NUMA library not found")
        
        except Exception as e:
            self.logger.warning(f"Failed to load NUMA library: {e}")
    
    async def _check_huge_page_support(self):
        """Check for huge page support"""
        try:
            # Check /proc/meminfo for huge page info
            if os.path.exists('/proc/meminfo'):
                with open('/proc/meminfo', 'r') as f:
                    content = f.read()
                
                if 'HugePages_Total:' in content:
                    # Parse huge page info
                    for line in content.split('\n'):
                        if line.startswith('HugePages_Total:'):
                            total_pages = int(line.split()[1])
                            if total_pages > 0:
                                self._huge_pages_available = True
                                break
            
            # Check for hugetlbfs mount point
            if os.path.exists('/dev/hugepages'):
                self._huge_page_path = '/dev/hugepages'
            elif os.path.exists('/mnt/huge'):
                self._huge_page_path = '/mnt/huge'
            
            if self._huge_pages_available:
                self.logger.info(f"Huge pages available at {self._huge_page_path}")
            else:
                self.logger.info("Huge pages not available")
        
        except Exception as e:
            self.logger.warning(f"Failed to check huge page support: {e}")
    
    async def _set_memory_policy(self):
        """Set memory allocation policy"""
        try:
            if not self._numa_available or not self._libnuma:
                return
            
            if self.memory_policy == "local":
                # Set policy to allocate on local node
                self._libnuma.numa_set_localalloc()
                self.logger.debug("Set memory policy to local allocation")
            
            elif self.memory_policy == "bind" and self.numa_node is not None:
                # Bind to specific node
                nodemask = ctypes.c_ulong(1 << self.numa_node)
                self._libnuma.numa_set_bind_policy(ctypes.pointer(nodemask))
                self.logger.debug(f"Set memory policy to bind to node {self.numa_node}")
            
            elif self.memory_policy == "interleave":
                # Interleave across all nodes
                self._libnuma.numa_set_interleave_mask(self._libnuma.numa_all_nodes_ptr)
                self.logger.debug("Set memory policy to interleave")
        
        except Exception as e:
            self.logger.error(f"Failed to set memory policy: {e}")
    
    async def _allocate_huge_pages(self, size: int, numa_node: int) -> int:
        """Allocate memory using huge pages"""
        try:
            if not self._huge_page_path:
                raise OSError("Huge page path not available")
            
            # Create temporary file in hugetlbfs
            import tempfile
            fd = None
            
            try:
                # Create temporary file
                fd = tempfile.NamedTemporaryFile(dir=self._huge_page_path, delete=False)
                temp_path = fd.name
                fd.close()
                
                # Open file for mmap
                fd = os.open(temp_path, os.O_RDWR)
                
                # Truncate to required size
                os.ftruncate(fd, size)
                
                # Memory map the file
                mm = mmap.mmap(fd, size, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)
                
                # Get memory address
                address = ctypes.addressof(ctypes.c_char.from_buffer(mm))
                
                # Bind to NUMA node if available
                if self._numa_available:
                    await self.bind_memory_to_node(address, size, numa_node)
                
                # Clean up file descriptor but keep mapping
                os.close(fd)
                os.unlink(temp_path)
                
                return address
            
            finally:
                if fd is not None:
                    try:
                        os.close(fd)
                    except:
                        pass
        
        except Exception as e:
            self.logger.error(f"Failed to allocate huge pages: {e}")
            # Fallback to regular pages
            return await self._allocate_regular_pages(size, numa_node)
    
    async def _allocate_regular_pages(self, size: int, numa_node: int) -> int:
        """Allocate memory using regular pages"""
        try:
            # Use mmap for anonymous mapping
            mm = mmap.mmap(-1, size, mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS, 
                          mmap.PROT_READ | mmap.PROT_WRITE)
            
            # Get memory address
            address = ctypes.addressof(ctypes.c_char.from_buffer(mm))
            
            # Bind to NUMA node if available
            if self._numa_available:
                await self.bind_memory_to_node(address, size, numa_node)
            
            return address
        
        except Exception as e:
            self.logger.error(f"Failed to allocate regular pages: {e}")
            raise
    
    async def _free_huge_pages(self, address: int, size: int):
        """Free huge page memory"""
        try:
            # Unmap memory
            mm = mmap.mmap(-1, 0)  # Create dummy mmap object
            mm.close()  # This will unmap the memory
        
        except Exception as e:
            self.logger.error(f"Failed to free huge pages: {e}")
    
    async def _free_regular_pages(self, address: int, size: int):
        """Free regular page memory"""
        try:
            # Unmap memory
            mm = mmap.mmap(-1, 0)  # Create dummy mmap object
            mm.close()  # This will unmap the memory
        
        except Exception as e:
            self.logger.error(f"Failed to free regular pages: {e}")
    
    async def _prefault_pages(self, address: int, size: int):
        """Prefault pages to avoid page faults during operation"""
        try:
            # Touch every page to force allocation
            page_size = 4096
            
            for offset in range(0, size, page_size):
                # Read and write a byte to force page allocation
                ptr = ctypes.cast(address + offset, ctypes.POINTER(ctypes.c_char))
                original_value = ptr.contents.value
                ptr.contents = ctypes.c_char(b'\\x00')
                ptr.contents = ctypes.c_char(original_value)
            
            self.logger.debug(f"Prefaulted {size // page_size} pages")
        
        except Exception as e:
            self.logger.warning(f"Failed to prefault pages: {e}")
    
    def create_zero_copy_buffer(self, size: int, numa_node: Optional[int] = None) -> 'ZeroCopyBuffer':
        """Create a zero-copy buffer"""
        return ZeroCopyBuffer(self, size, numa_node)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get NUMA allocator statistics"""
        return {
            'numa_available': self._numa_available,
            'huge_pages_available': self._huge_pages_available,
            'numa_node': self.numa_node,
            'memory_policy': self.memory_policy,
            'total_allocated_bytes': self._total_allocated,
            'allocated_regions': len(self._allocated_regions),
            'huge_page_size': self.huge_page_size,
            'huge_page_path': self._huge_page_path
        }


class ZeroCopyBuffer:
    """Zero-copy buffer for high-performance networking"""
    
    def __init__(self, allocator: NUMAAllocator, size: int, numa_node: Optional[int] = None):
        self.allocator = allocator
        self.size = size
        self.numa_node = numa_node
        self.address = None
        self._buffer = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.address = await self.allocator.allocate_memory(
            self.size, 
            self.numa_node, 
            use_huge_pages=True,
            prefault=True
        )
        
        # Create buffer view
        self._buffer = ctypes.cast(
            self.address, 
            ctypes.POINTER(ctypes.c_char * self.size)
        ).contents
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.address:
            await self.allocator.free_memory(self.address)
            self.address = None
            self._buffer = None
    
    def get_buffer(self) -> ctypes.Array:
        """Get the underlying buffer"""
        if self._buffer is None:
            raise RuntimeError("Buffer not allocated")
        return self._buffer
    
    def get_address(self) -> int:
        """Get buffer memory address"""
        return self.address
    
    def write(self, data: bytes, offset: int = 0):
        """Write data to buffer"""
        if self._buffer is None:
            raise RuntimeError("Buffer not allocated")
        
        if offset + len(data) > self.size:
            raise ValueError("Data too large for buffer")
        
        # Copy data to buffer
        ctypes.memmove(
            ctypes.addressof(self._buffer) + offset,
            data,
            len(data)
        )
    
    def read(self, length: int, offset: int = 0) -> bytes:
        """Read data from buffer"""
        if self._buffer is None:
            raise RuntimeError("Buffer not allocated")
        
        if offset + length > self.size:
            raise ValueError("Read beyond buffer size")
        
        # Create bytes from buffer
        return bytes(self._buffer[offset:offset + length])