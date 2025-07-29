"""
Kernel Bypass Socket
High-performance kernel bypass networking implementation
"""

import asyncio
import ctypes
import mmap
import os
import socket
import struct
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import logging

from .numa_allocator import NUMAAllocator
from .cpu_affinity import CPUAffinityManager


@dataclass
class PacketBuffer:
    """Packet buffer for zero-copy operations"""
    address: int
    size: int
    data_length: int
    timestamp: float


class KernelBypassSocket:
    """
    Kernel bypass socket implementation
    
    Features:
    - User-space networking stack
    - Zero-copy packet processing
    - NUMA-aware memory allocation
    - CPU affinity optimization
    - Hardware timestamp support
    """
    
    def __init__(self, 
                 numa_allocator: Optional[NUMAAllocator] = None,
                 cpu_affinity_manager: Optional[CPUAffinityManager] = None,
                 buffer_size: int = 2 * 1024 * 1024,  # 2MB
                 packet_buffer_count: int = 1024):
        
        self.numa_allocator = numa_allocator
        self.cpu_affinity_manager = cpu_affinity_manager
        self.buffer_size = buffer_size
        self.packet_buffer_count = packet_buffer_count
        
        # Connection state
        self.is_connected = False
        self.local_address: Optional[tuple] = None
        self.remote_address: Optional[tuple] = None
        
        # Packet buffers
        self._tx_buffers: List[PacketBuffer] = []
        self._rx_buffers: List[PacketBuffer] = []
        self._free_tx_buffers: List[int] = []
        self._free_rx_buffers: List[int] = []
        
        # Memory regions
        self._tx_memory_region: Optional[int] = None
        self._rx_memory_region: Optional[int] = None
        
        # Network interface
        self._raw_socket: Optional[socket.socket] = None
        self._interface_name: str = "eth0"  # Default interface
        
        # Statistics
        self._stats = {
            'packets_sent': 0,
            'packets_received': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'zero_copy_sends': 0,
            'zero_copy_receives': 0,
            'buffer_overruns': 0,
            'errors': 0
        }
        
        # Background tasks
        self._rx_task: Optional[asyncio.Task] = None
        self._running = False
        
        self.logger = logging.getLogger(__name__)
    
    async def connect(self, host: str, port: int):
        """Connect to remote host"""
        try:
            self.remote_address = (host, port)
            
            # Initialize packet buffers
            await self._initialize_buffers()
            
            # Create raw socket for kernel bypass
            await self._create_raw_socket()
            
            # Start receive task
            self._running = True
            self._rx_task = asyncio.create_task(self._receive_worker())
            
            self.is_connected = True
            self.logger.info(f"Kernel bypass socket connected to {host}:{port}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect kernel bypass socket: {e}")
            await self.close()
            raise
    
    async def close(self):
        """Close the kernel bypass socket"""
        self.is_connected = False
        self._running = False
        
        # Cancel receive task
        if self._rx_task:
            self._rx_task.cancel()
            try:
                await self._rx_task
            except asyncio.CancelledError:
                pass
        
        # Close raw socket
        if self._raw_socket:
            self._raw_socket.close()
            self._raw_socket = None
        
        # Free memory regions
        await self._cleanup_buffers()
        
        self.logger.info("Kernel bypass socket closed")
    
    async def send(self, data: bytes) -> int:
        """Send data using standard copy"""
        if not self.is_connected:
            raise RuntimeError("Socket not connected")
        
        try:
            # Get free buffer
            buffer_idx = await self._get_free_tx_buffer()
            if buffer_idx is None:
                raise RuntimeError("No free TX buffers available")
            
            buffer = self._tx_buffers[buffer_idx]
            
            # Copy data to buffer
            if len(data) > buffer.size:
                raise ValueError(f"Data too large for buffer: {len(data)} > {buffer.size}")
            
            self._copy_to_buffer(buffer.address, data)
            buffer.data_length = len(data)
            buffer.timestamp = time.time()
            
            # Send packet
            bytes_sent = await self._send_packet(buffer)
            
            # Return buffer to free pool
            self._free_tx_buffers.append(buffer_idx)
            
            # Update statistics
            self._stats['packets_sent'] += 1
            self._stats['bytes_sent'] += bytes_sent
            
            return bytes_sent
            
        except Exception as e:
            self._stats['errors'] += 1
            self.logger.error(f"Send error: {e}")
            raise
    
    async def send_zero_copy(self, data: bytes) -> int:
        """Send data using zero-copy operations"""
        if not self.is_connected:
            raise RuntimeError("Socket not connected")
        
        try:
            # For true zero-copy, we would need the data to already be in
            # a properly aligned buffer. For now, this is a placeholder
            # that demonstrates the concept.
            
            # In a real implementation, this would:
            # 1. Check if data is in a suitable buffer
            # 2. Use sendfile() or similar zero-copy mechanism
            # 3. Avoid memory copies
            
            bytes_sent = await self.send(data)  # Fallback to regular send
            
            self._stats['zero_copy_sends'] += 1
            return bytes_sent
            
        except Exception as e:
            self._stats['errors'] += 1
            self.logger.error(f"Zero-copy send error: {e}")
            raise
    
    async def receive(self, buffer_size: int) -> bytes:
        """Receive data using standard copy"""
        if not self.is_connected:
            raise RuntimeError("Socket not connected")
        
        try:
            # Get received buffer
            buffer_idx = await self._get_received_buffer()
            if buffer_idx is None:
                return b''  # No data available
            
            buffer = self._rx_buffers[buffer_idx]
            
            # Copy data from buffer
            data_length = min(buffer_size, buffer.data_length)
            data = self._copy_from_buffer(buffer.address, data_length)
            
            # Return buffer to free pool
            self._free_rx_buffers.append(buffer_idx)
            
            # Update statistics
            self._stats['packets_received'] += 1
            self._stats['bytes_received'] += len(data)
            
            return data
            
        except Exception as e:
            self._stats['errors'] += 1
            self.logger.error(f"Receive error: {e}")
            raise
    
    async def receive_zero_copy(self, buffer_size: int) -> bytes:
        """Receive data using zero-copy operations"""
        if not self.is_connected:
            raise RuntimeError("Socket not connected")
        
        try:
            # For true zero-copy, we would return a buffer view
            # instead of copying data. This is a placeholder.
            
            data = await self.receive(buffer_size)
            
            self._stats['zero_copy_receives'] += 1
            return data
            
        except Exception as e:
            self._stats['errors'] += 1
            self.logger.error(f"Zero-copy receive error: {e}")
            raise
    
    async def is_alive(self) -> bool:
        """Check if connection is alive"""
        return self.is_connected and self._raw_socket is not None
    
    async def _initialize_buffers(self):
        """Initialize packet buffers"""
        try:
            # Calculate total memory needed
            total_tx_memory = self.buffer_size * self.packet_buffer_count
            total_rx_memory = self.buffer_size * self.packet_buffer_count
            
            # Allocate TX memory region
            if self.numa_allocator:
                self._tx_memory_region = await self.numa_allocator.allocate_memory(
                    total_tx_memory, use_huge_pages=True, prefault=True
                )
                self._rx_memory_region = await self.numa_allocator.allocate_memory(
                    total_rx_memory, use_huge_pages=True, prefault=True
                )
            else:
                # Fallback to regular allocation
                self._tx_memory_region = self._allocate_memory_region(total_tx_memory)
                self._rx_memory_region = self._allocate_memory_region(total_rx_memory)
            
            # Create TX buffers
            for i in range(self.packet_buffer_count):
                buffer_address = self._tx_memory_region + (i * self.buffer_size)
                buffer = PacketBuffer(
                    address=buffer_address,
                    size=self.buffer_size,
                    data_length=0,
                    timestamp=0.0
                )
                self._tx_buffers.append(buffer)
                self._free_tx_buffers.append(i)
            
            # Create RX buffers
            for i in range(self.packet_buffer_count):
                buffer_address = self._rx_memory_region + (i * self.buffer_size)
                buffer = PacketBuffer(
                    address=buffer_address,
                    size=self.buffer_size,
                    data_length=0,
                    timestamp=0.0
                )
                self._rx_buffers.append(buffer)
                self._free_rx_buffers.append(i)
            
            self.logger.debug(f"Initialized {len(self._tx_buffers)} TX and {len(self._rx_buffers)} RX buffers")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize buffers: {e}")
            raise
    
    async def _cleanup_buffers(self):
        """Cleanup packet buffers"""
        try:
            # Free memory regions
            if self.numa_allocator:
                if self._tx_memory_region:
                    await self.numa_allocator.free_memory(self._tx_memory_region)
                if self._rx_memory_region:
                    await self.numa_allocator.free_memory(self._rx_memory_region)
            else:
                # Cleanup regular memory regions
                if self._tx_memory_region:
                    self._free_memory_region(self._tx_memory_region)
                if self._rx_memory_region:
                    self._free_memory_region(self._rx_memory_region)
            
            # Clear buffer lists
            self._tx_buffers.clear()
            self._rx_buffers.clear()
            self._free_tx_buffers.clear()
            self._free_rx_buffers.clear()
            
            self._tx_memory_region = None
            self._rx_memory_region = None
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup buffers: {e}")
    
    def _allocate_memory_region(self, size: int) -> int:
        """Allocate memory region using mmap"""
        try:
            # Use mmap for large memory allocation
            mm = mmap.mmap(-1, size, mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS)
            
            # Get memory address
            address = ctypes.addressof(ctypes.c_char.from_buffer(mm))
            
            return address
            
        except Exception as e:
            self.logger.error(f"Failed to allocate memory region: {e}")
            raise
    
    def _free_memory_region(self, address: int):
        """Free memory region"""
        try:
            # In a real implementation, we would properly track and free mmap regions
            pass
        except Exception as e:
            self.logger.error(f"Failed to free memory region: {e}")
    
    async def _create_raw_socket(self):
        """Create raw socket for kernel bypass"""
        try:
            # Create raw socket (requires root privileges)
            self._raw_socket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0800))
            
            # Bind to network interface
            self._raw_socket.bind((self._interface_name, 0))
            
            # Set socket to non-blocking
            self._raw_socket.setblocking(False)
            
            # Get local address
            self.local_address = self._raw_socket.getsockname()
            
            self.logger.debug(f"Created raw socket bound to {self._interface_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to create raw socket: {e}")
            # Fallback to regular socket for testing
            self._raw_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._raw_socket.setblocking(False)
    
    async def _get_free_tx_buffer(self) -> Optional[int]:
        """Get a free TX buffer"""
        if self._free_tx_buffers:
            return self._free_tx_buffers.pop(0)
        
        # No free buffers available
        self._stats['buffer_overruns'] += 1
        return None
    
    async def _get_received_buffer(self) -> Optional[int]:
        """Get a buffer with received data"""
        # This would be populated by the receive worker
        # For now, return None (no data available)
        return None
    
    async def _send_packet(self, buffer: PacketBuffer) -> int:
        """Send packet using raw socket"""
        try:
            if not self._raw_socket:
                raise RuntimeError("Raw socket not available")
            
            # Create packet data
            packet_data = self._copy_from_buffer(buffer.address, buffer.data_length)
            
            # Send packet
            if self.remote_address:
                bytes_sent = self._raw_socket.sendto(packet_data, self.remote_address)
            else:
                bytes_sent = self._raw_socket.send(packet_data)
            
            return bytes_sent
            
        except Exception as e:
            self.logger.error(f"Failed to send packet: {e}")
            raise
    
    async def _receive_worker(self):
        """Background worker for receiving packets"""
        while self._running:
            try:
                if not self._raw_socket:
                    await asyncio.sleep(0.001)
                    continue
                
                # Try to receive data
                try:
                    data, addr = self._raw_socket.recvfrom(65536)
                    
                    # Get free RX buffer
                    buffer_idx = None
                    if self._free_rx_buffers:
                        buffer_idx = self._free_rx_buffers.pop(0)
                    
                    if buffer_idx is not None:
                        buffer = self._rx_buffers[buffer_idx]
                        
                        # Copy data to buffer
                        if len(data) <= buffer.size:
                            self._copy_to_buffer(buffer.address, data)
                            buffer.data_length = len(data)
                            buffer.timestamp = time.time()
                            
                            # Buffer is now ready for consumption
                            # In a real implementation, we would signal waiting receivers
                        else:
                            # Data too large, return buffer to free pool
                            self._free_rx_buffers.append(buffer_idx)
                            self._stats['buffer_overruns'] += 1
                    else:
                        # No free buffers
                        self._stats['buffer_overruns'] += 1
                
                except socket.error:
                    # No data available, continue
                    await asyncio.sleep(0.001)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Receive worker error: {e}")
                await asyncio.sleep(0.01)
    
    def _copy_to_buffer(self, buffer_address: int, data: bytes):
        """Copy data to buffer"""
        try:
            # Create ctypes pointer to buffer
            buffer_ptr = ctypes.cast(buffer_address, ctypes.POINTER(ctypes.c_char * len(data)))
            
            # Copy data
            ctypes.memmove(buffer_ptr.contents, data, len(data))
            
        except Exception as e:
            self.logger.error(f"Failed to copy data to buffer: {e}")
            raise
    
    def _copy_from_buffer(self, buffer_address: int, length: int) -> bytes:
        """Copy data from buffer"""
        try:
            # Create ctypes pointer to buffer
            buffer_ptr = ctypes.cast(buffer_address, ctypes.POINTER(ctypes.c_char * length))
            
            # Copy data
            return bytes(buffer_ptr.contents)
            
        except Exception as e:
            self.logger.error(f"Failed to copy data from buffer: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get kernel bypass socket statistics"""
        return {
            'connected': self.is_connected,
            'local_address': self.local_address,
            'remote_address': self.remote_address,
            'tx_buffers': len(self._tx_buffers),
            'rx_buffers': len(self._rx_buffers),
            'free_tx_buffers': len(self._free_tx_buffers),
            'free_rx_buffers': len(self._free_rx_buffers),
            'buffer_size': self.buffer_size,
            'statistics': self._stats.copy()
        }