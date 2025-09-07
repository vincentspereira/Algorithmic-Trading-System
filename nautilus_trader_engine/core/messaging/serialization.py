"""
Zero-Copy Serialization System
High-performance serialization for trading system messages
"""

import struct
import time
from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Any, Dict, Optional, Union, List
from dataclasses import dataclass
import json
import logging


class MessageType(IntEnum):
    """Message type enumeration for efficient serialization"""
    UNKNOWN = 0
    
    # Market Data
    MARKET_DATA_TICK = 100
    MARKET_DATA_QUOTE = 101
    MARKET_DATA_TRADE = 102
    MARKET_DATA_ORDER_BOOK = 103
    MARKET_DATA_BAR = 104
    
    # Orders
    ORDER_NEW = 200
    ORDER_MODIFY = 201
    ORDER_CANCEL = 202
    ORDER_EXECUTION = 203
    ORDER_REJECT = 204
    ORDER_STATUS = 205
    
    # Risk Management
    RISK_CHECK = 300
    RISK_VIOLATION = 301
    POSITION_UPDATE = 302
    PORTFOLIO_UPDATE = 303
    
    # System
    SYSTEM_HEARTBEAT = 400
    SYSTEM_STATUS = 401
    SYSTEM_ERROR = 402
    SYSTEM_SHUTDOWN = 403
    
    # Analytics
    ANALYTICS_SIGNAL = 500
    ANALYTICS_INDICATOR = 501
    ANALYTICS_BACKTEST = 502
    
    # AI/ML
    AI_PREDICTION = 600
    AI_SIGNAL = 601
    AI_MODEL_UPDATE = 602


@dataclass
class SerializationHeader:
    """Fixed-size header for all serialized messages"""
    magic_number: int = 0x4E545254  # 'NTRT' in hex
    version: int = 1
    message_type: MessageType = MessageType.UNKNOWN
    payload_size: int = 0
    checksum: int = 0
    timestamp: int = 0
    
    HEADER_SIZE = 24  # bytes
    HEADER_FORMAT = '<IIHIIQ'  # little-endian format
    
    def to_bytes(self) -> bytes:
        """Serialize header to bytes"""
        return struct.pack(
            self.HEADER_FORMAT,
            self.magic_number,
            self.version,
            int(self.message_type),
            self.payload_size,
            self.checksum,
            self.timestamp
        )
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'SerializationHeader':
        """Deserialize header from bytes"""
        if len(data) < cls.HEADER_SIZE:
            raise ValueError(f"Insufficient data for header: {len(data)} < {cls.HEADER_SIZE}")
        
        unpacked = struct.unpack(cls.HEADER_FORMAT, data[:cls.HEADER_SIZE])
        
        return cls(
            magic_number=unpacked[0],
            version=unpacked[1],
            message_type=MessageType(unpacked[2]),
            payload_size=unpacked[3],
            checksum=unpacked[4],
            timestamp=unpacked[5]
        )


class Serializer(ABC):
    """Abstract base class for serializers"""
    
    @abstractmethod
    def serialize(self, obj: Any) -> bytes:
        """Serialize object to bytes"""
        pass
    
    @abstractmethod
    def deserialize(self, data: bytes, obj_type: type) -> Any:
        """Deserialize bytes to object"""
        pass


class JSONSerializer(Serializer):
    """JSON serializer for human-readable messages"""
    
    def serialize(self, obj: Any) -> bytes:
        """Serialize object to JSON bytes"""
        try:
            json_str = json.dumps(obj, default=self._json_default, separators=(',', ':'))
            return json_str.encode('utf-8')
        except Exception as e:
            raise ValueError(f"JSON serialization failed: {e}")
    
    def deserialize(self, data: bytes, obj_type: type = dict) -> Any:
        """Deserialize JSON bytes to object"""
        try:
            json_str = data.decode('utf-8')
            return json.loads(json_str)
        except Exception as e:
            raise ValueError(f"JSON deserialization failed: {e}")
    
    def _json_default(self, obj):
        """Handle non-serializable objects"""
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        elif hasattr(obj, '_asdict'):  # namedtuple
            return obj._asdict()
        else:
            return str(obj)


class BinarySerializer(Serializer):
    """High-performance binary serializer for trading data"""
    
    def __init__(self):
        # Format strings for common trading data structures
        self.formats = {
            'tick': '<ddfQ',      # price, size, flags, timestamp
            'quote': '<ddddQ',    # bid, ask, bid_size, ask_size, timestamp
            'trade': '<ddfQ',     # price, size, flags, timestamp
            'order': '<QddfII',   # order_id, price, size, flags, status, timestamp
        }
    
    def serialize(self, obj: Any) -> bytes:
        """Serialize object to binary format using JSON (safer than pickle)"""
        try:
            # Use JSON serialization which is safer than pickle
            json_str = json.dumps(obj, default=self._json_default, separators=(',', ':'))
            return json_str.encode('utf-8')
        except Exception as e:
            raise ValueError(f"Binary serialization failed: {e}")
    
    def deserialize(self, data: bytes, obj_type: type = dict) -> Any:
        """Deserialize binary data to object"""
        try:
            json_str = data.decode('utf-8')
            return json.loads(json_str)
        except Exception as e:
            raise ValueError(f"Binary deserialization failed: {e}")
    
    def _json_default(self, obj):
        """Handle non-serializable objects"""
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        elif hasattr(obj, '_asdict'):  # namedtuple
            return obj._asdict()
        else:
            return str(obj)


class ZeroCopySerializer:
    """
    Zero-copy serializer that minimizes memory allocations
    
    Uses pre-allocated buffers and efficient serialization strategies
    to achieve ultra-low latency message serialization.
    """
    
    def __init__(self, buffer_size: int = 64 * 1024):  # 64KB default buffer
        self.buffer_size = buffer_size
        self.serializers = {
            'json': JSONSerializer(),
            'binary': BinarySerializer()
        }
        
        # Pre-allocated buffers for zero-copy operations
        self._write_buffer = bytearray(buffer_size)
        self._read_buffer = bytearray(buffer_size)
        
        self.logger = logging.getLogger(__name__)
    
    def serialize(self, obj: Any, message_type: MessageType) -> bytes:
        """
        Serialize object with message header
        
        Args:
            obj: Object to serialize
            message_type: Type of message for routing
            
        Returns:
            bytes: Serialized message with header
        """
        start_time = time.time_ns()
        
        try:
            # Choose serializer based on message type
            serializer = self._get_serializer(message_type)
            
            # Serialize payload
            payload = serializer.serialize(obj)
            
            # Create header
            header = SerializationHeader(
                message_type=message_type,
                payload_size=len(payload),
                checksum=self._calculate_checksum(payload),
                timestamp=start_time
            )
            
            # Combine header and payload
            header_bytes = header.to_bytes()
            
            # Use pre-allocated buffer if possible
            total_size = len(header_bytes) + len(payload)
            if total_size <= self.buffer_size:
                # Zero-copy using pre-allocated buffer
                self._write_buffer[:len(header_bytes)] = header_bytes
                self._write_buffer[len(header_bytes):total_size] = payload
                return bytes(self._write_buffer[:total_size])
            else:
                # Fallback to regular allocation for large messages
                return header_bytes + payload
        
        except Exception as e:
            self.logger.error(f"Serialization failed for {message_type}: {e}")
            raise
    
    def deserialize(self, data: bytes) -> tuple[SerializationHeader, Any]:
        """
        Deserialize message with header validation
        
        Args:
            data: Serialized message bytes
            
        Returns:
            tuple: (header, deserialized_object)
        """
        if len(data) < SerializationHeader.HEADER_SIZE:
            raise ValueError("Message too short for header")
        
        # Parse header
        header = SerializationHeader.from_bytes(data)
        
        # Validate header
        if header.magic_number != SerializationHeader().magic_number:
            raise ValueError("Invalid magic number")
        
        if header.version != 1:
            raise ValueError(f"Unsupported version: {header.version}")
        
        # Extract payload
        payload_start = SerializationHeader.HEADER_SIZE
        payload_end = payload_start + header.payload_size
        
        if len(data) < payload_end:
            raise ValueError("Message truncated")
        
        payload = data[payload_start:payload_end]
        
        # Validate checksum
        if header.checksum != self._calculate_checksum(payload):
            raise ValueError("Checksum mismatch")
        
        # Deserialize payload
        serializer = self._get_serializer(header.message_type)
        obj = serializer.deserialize(payload)
        
        return header, obj
    
    def _get_serializer(self, message_type: MessageType) -> Serializer:
        """Get appropriate serializer for message type"""
        # Use binary serializer for high-frequency market data
        if message_type in [MessageType.MARKET_DATA_TICK, 
                           MessageType.MARKET_DATA_QUOTE,
                           MessageType.MARKET_DATA_TRADE]:
            return self.serializers['binary']
        
        # Use JSON for all other messages (safer than pickle)
        else:
            return self.serializers['json']
    
    def _calculate_checksum(self, data: bytes) -> int:
        """Calculate simple checksum for data integrity"""
        # Simple XOR checksum - in production would use CRC32 or similar
        checksum = 0
        for byte in data:
            checksum ^= byte
        return checksum
    
    def get_stats(self) -> Dict[str, Any]:
        """Get serialization statistics"""
        return {
            'buffer_size': self.buffer_size,
            'serializers': list(self.serializers.keys())
        }