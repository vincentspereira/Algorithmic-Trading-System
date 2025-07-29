"""
High-Performance Message Bus Implementation
Lock-free, zero-copy message bus for ultra-low latency trading system communication
"""

import asyncio
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable, Any, Set
from concurrent.futures import ThreadPoolExecutor
import logging
from enum import Enum

from .ring_buffer import LockFreeRingBuffer
from .serialization import ZeroCopySerializer, MessageType
from .routing import TopicRouter
from .metrics import MessageMetrics


class MessagePriority(Enum):
    """Message priority levels for routing and processing"""
    CRITICAL = 0    # Market data, order execution
    HIGH = 1        # Risk management, compliance
    NORMAL = 2      # Analytics, reporting
    LOW = 3         # Logging, audit


@dataclass
class Message:
    """Zero-copy message structure"""
    message_id: str
    topic: str
    message_type: MessageType
    priority: MessagePriority
    timestamp: int  # nanoseconds since epoch
    payload: bytes  # Pre-serialized payload
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time_ns()


class MessageHandler(ABC):
    """Abstract base class for message handlers"""
    
    @abstractmethod
    async def handle_message(self, message: Message) -> Optional[Message]:
        """Handle incoming message and optionally return response"""
        pass
    
    @abstractmethod
    def get_subscribed_topics(self) -> List[str]:
        """Return list of topics this handler subscribes to"""
        pass


class MessageBus:
    """
    High-performance message bus with zero-copy semantics
    
    Features:
    - Lock-free ring buffers for each priority level
    - Zero-copy message passing
    - Topic-based routing
    - Performance metrics collection
    - Backpressure handling
    """
    
    def __init__(self, 
                 buffer_size: int = 1024 * 1024,  # 1M messages per buffer
                 num_worker_threads: int = 4,
                 enable_metrics: bool = True):
        
        self.buffer_size = buffer_size
        self.num_worker_threads = num_worker_threads
        self.enable_metrics = enable_metrics
        
        # Create ring buffers for each priority level
        self.buffers = {
            priority: LockFreeRingBuffer(buffer_size) 
            for priority in MessagePriority
        }
        
        # Message routing
        self.router = TopicRouter()
        self.handlers: Dict[str, List[MessageHandler]] = {}
        
        # Serialization
        self.serializer = ZeroCopySerializer()
        
        # Metrics
        self.metrics = MessageMetrics() if enable_metrics else None
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=num_worker_threads)
        self.worker_threads: List[threading.Thread] = []
        self.running = False
        
        # Performance optimization
        self._message_pool = []  # Object pool for message reuse
        self._pool_lock = threading.Lock()
        
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        """Start the message bus and worker threads"""
        if self.running:
            return
        
        self.running = True
        
        # Start worker threads for each priority level
        for priority in MessagePriority:
            thread = threading.Thread(
                target=self._worker_loop,
                args=(priority,),
                name=f"MessageBus-{priority.name}",
                daemon=True
            )
            thread.start()
            self.worker_threads.append(thread)
        
        self.logger.info(f"MessageBus started with {len(self.worker_threads)} worker threads")
    
    def stop(self):
        """Stop the message bus and all worker threads"""
        if not self.running:
            return
        
        self.running = False
        
        # Wait for worker threads to finish
        for thread in self.worker_threads:
            thread.join(timeout=1.0)
        
        self.executor.shutdown(wait=True)
        self.logger.info("MessageBus stopped")
    
    def subscribe(self, handler: MessageHandler):
        """Subscribe a handler to topics"""
        topics = handler.get_subscribed_topics()
        
        for topic in topics:
            if topic not in self.handlers:
                self.handlers[topic] = []
            self.handlers[topic].append(handler)
        
        self.logger.debug(f"Handler subscribed to topics: {topics}")
    
    def unsubscribe(self, handler: MessageHandler):
        """Unsubscribe a handler from all topics"""
        topics_to_remove = []
        
        for topic, handlers in self.handlers.items():
            if handler in handlers:
                handlers.remove(handler)
                if not handlers:  # Remove empty topic
                    topics_to_remove.append(topic)
        
        for topic in topics_to_remove:
            del self.handlers[topic]
        
        self.logger.debug(f"Handler unsubscribed from {len(topics_to_remove)} topics")
    
    def publish(self, 
                topic: str,
                message_type: MessageType,
                payload: Any,
                priority: MessagePriority = MessagePriority.NORMAL,
                correlation_id: Optional[str] = None,
                reply_to: Optional[str] = None) -> bool:
        """
        Publish a message to the bus
        
        Returns:
            bool: True if message was successfully queued, False if buffer is full
        """
        if not self.running:
            return False
        
        # Serialize payload
        try:
            serialized_payload = self.serializer.serialize(payload, message_type)
        except Exception as e:
            self.logger.error(f"Failed to serialize message: {e}")
            return False
        
        # Create message
        message = self._get_message_from_pool()
        message.message_id = self._generate_message_id()
        message.topic = topic
        message.message_type = message_type
        message.priority = priority
        message.timestamp = time.time_ns()
        message.payload = serialized_payload
        message.correlation_id = correlation_id
        message.reply_to = reply_to
        
        # Try to enqueue message
        buffer = self.buffers[priority]
        success = buffer.try_enqueue(message)
        
        if success:
            if self.metrics:
                self.metrics.record_message_published(topic, priority)
        else:
            # Buffer full - handle backpressure
            self._handle_backpressure(message)
            if self.metrics:
                self.metrics.record_message_dropped(topic, priority)
        
        return success
    
    async def publish_async(self,
                           topic: str,
                           message_type: MessageType,
                           payload: Any,
                           priority: MessagePriority = MessagePriority.NORMAL,
                           correlation_id: Optional[str] = None,
                           reply_to: Optional[str] = None) -> bool:
        """Async version of publish"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.publish,
            topic, message_type, payload, priority, correlation_id, reply_to
        )
    
    def _worker_loop(self, priority: MessagePriority):
        """Worker thread loop for processing messages of specific priority"""
        buffer = self.buffers[priority]
        
        while self.running:
            try:
                # Try to dequeue message
                message = buffer.try_dequeue()
                
                if message is None:
                    # No message available, brief sleep to avoid busy waiting
                    time.sleep(0.000001)  # 1 microsecond
                    continue
                
                # Process message
                self._process_message(message)
                
                # Return message to pool
                self._return_message_to_pool(message)
                
            except Exception as e:
                self.logger.error(f"Error in worker loop for {priority.name}: {e}")
    
    def _process_message(self, message: Message):
        """Process a single message by routing to appropriate handlers"""
        start_time = time.time_ns()
        
        try:
            # Find handlers for this topic
            handlers = self.handlers.get(message.topic, [])
            
            if not handlers:
                if self.metrics:
                    self.metrics.record_message_unrouted(message.topic)
                return
            
            # Route to all handlers
            for handler in handlers:
                try:
                    # Run handler in executor to avoid blocking
                    future = self.executor.submit(
                        self._run_handler_sync, handler, message
                    )
                    
                    # Don't wait for completion to maintain throughput
                    # Handlers should be fast and non-blocking
                    
                except Exception as e:
                    self.logger.error(f"Error submitting handler task: {e}")
            
            if self.metrics:
                processing_time = time.time_ns() - start_time
                self.metrics.record_message_processed(
                    message.topic, message.priority, processing_time
                )
        
        except Exception as e:
            self.logger.error(f"Error processing message {message.message_id}: {e}")
    
    def _run_handler_sync(self, handler: MessageHandler, message: Message):
        """Run message handler synchronously"""
        try:
            # For now, run sync - in production would use async
            # This is a simplified implementation
            if hasattr(handler, 'handle_message_sync'):
                response = handler.handle_message_sync(message)
            else:
                # Fallback for async handlers - would need proper async handling
                response = None
            
            # Handle response if provided
            if response and message.reply_to:
                self.publish(
                    message.reply_to,
                    response.message_type,
                    response.payload,
                    MessagePriority.HIGH,
                    message.message_id
                )
        
        except Exception as e:
            self.logger.error(f"Handler error: {e}")
    
    def _handle_backpressure(self, message: Message):
        """Handle backpressure when buffers are full"""
        # For critical messages, try to make room
        if message.priority == MessagePriority.CRITICAL:
            # Could implement emergency buffer or drop lower priority messages
            self.logger.warning(f"Critical message dropped due to backpressure: {message.topic}")
        else:
            self.logger.debug(f"Message dropped due to backpressure: {message.topic}")
    
    def _generate_message_id(self) -> str:
        """Generate unique message ID"""
        return f"{time.time_ns()}_{threading.get_ident()}"
    
    def _get_message_from_pool(self) -> Message:
        """Get message object from pool for reuse"""
        with self._pool_lock:
            if self._message_pool:
                message = self._message_pool.pop()
                # Reset message fields
                message.message_id = ""
                message.topic = ""
                message.correlation_id = None
                message.reply_to = None
                return message
        
        # Create new message if pool is empty
        return Message("", "", MessageType.UNKNOWN, MessagePriority.NORMAL, 0, b"")
    
    def _return_message_to_pool(self, message: Message):
        """Return message object to pool for reuse"""
        with self._pool_lock:
            if len(self._message_pool) < 1000:  # Limit pool size
                self._message_pool.append(message)
    
    def get_metrics(self) -> Optional[Dict[str, Any]]:
        """Get current message bus metrics"""
        if not self.metrics:
            return None
        
        return self.metrics.get_metrics()
    
    def get_buffer_stats(self) -> Dict[str, Dict[str, int]]:
        """Get buffer utilization statistics"""
        stats = {}
        
        for priority, buffer in self.buffers.items():
            stats[priority.name] = {
                'size': buffer.size(),
                'capacity': buffer.capacity(),
                'utilization_pct': (buffer.size() / buffer.capacity()) * 100
            }
        
        return stats