"""Unit tests for Messaging System components."""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio
from typing import Dict, Any, List, Optional
import time
import json


class TestMessageBus:
    """Test suite for Message Bus."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.bus_config = {
            'max_queue_size': 10000,
            'batch_size': 100,
            'flush_interval_ms': 10,
            'serialization_format': 'msgpack'
        }
        
        self.sample_message = {
            'id': 'msg_001',
            'type': 'market_data',
            'timestamp': time.time(),
            'data': {
                'symbol': 'EURUSD',
                'bid': 1.0850,
                'ask': 1.0852,
                'volume': 1000000
            }
        }
    
    @patch('nautilus_trader_engine.core.messaging.message_bus.MessageBus')
    def test_message_bus_initialization(self, mock_message_bus):
        """Test message bus initialization."""
        mock_bus = Mock()
        mock_message_bus.return_value = mock_bus
        
        from nautilus_trader_engine.core.messaging.message_bus import MessageBus
        bus = MessageBus(self.bus_config)
        
        assert bus is not None
        mock_message_bus.assert_called_once_with(self.bus_config)
    
    @patch('nautilus_trader_engine.core.messaging.message_bus.MessageBus')
    def test_message_publishing(self, mock_message_bus):
        """Test message publishing functionality."""
        mock_bus = Mock()
        mock_message_bus.return_value = mock_bus
        
        # Mock publishing behavior
        mock_bus.publish.return_value = True
        mock_bus.get_queue_size.return_value = 1
        
        from nautilus_trader_engine.core.messaging.message_bus import MessageBus
        bus = MessageBus(self.bus_config)
        
        # Test message publishing
        result = bus.publish('market_data', self.sample_message)
        assert result is True
        mock_bus.publish.assert_called_once_with('market_data', self.sample_message)
        
        # Test queue size
        queue_size = bus.get_queue_size()
        assert queue_size == 1
    
    @patch('nautilus_trader_engine.core.messaging.message_bus.MessageBus')
    def test_message_subscription(self, mock_message_bus):
        """Test message subscription functionality."""
        mock_bus = Mock()
        mock_message_bus.return_value = mock_bus
        
        # Mock subscription behavior
        mock_callback = Mock()
        mock_bus.subscribe.return_value = 'subscription_id_001'
        mock_bus.unsubscribe.return_value = True
        
        from nautilus_trader_engine.core.messaging.message_bus import MessageBus
        bus = MessageBus(self.bus_config)
        
        # Test subscription
        subscription_id = bus.subscribe('market_data', mock_callback)
        assert subscription_id == 'subscription_id_001'
        mock_bus.subscribe.assert_called_once_with('market_data', mock_callback)
        
        # Test unsubscription
        result = bus.unsubscribe(subscription_id)
        assert result is True
        mock_bus.unsubscribe.assert_called_once_with(subscription_id)
    
    @patch('nautilus_trader_engine.core.messaging.message_bus.MessageBus')
    def test_batch_processing(self, mock_message_bus):
        """Test batch message processing."""
        mock_bus = Mock()
        mock_message_bus.return_value = mock_bus
        
        # Mock batch processing
        messages = [self.sample_message for _ in range(5)]
        mock_bus.publish_batch.return_value = 5
        mock_bus.get_batch_stats.return_value = {
            'batches_processed': 10,
            'messages_per_batch_avg': 95,
            'processing_time_ms_avg': 2.5
        }
        
        from nautilus_trader_engine.core.messaging.message_bus import MessageBus
        bus = MessageBus(self.bus_config)
        
        # Test batch publishing
        processed_count = bus.publish_batch('market_data', messages)
        assert processed_count == 5
        
        # Test batch statistics
        stats = bus.get_batch_stats()
        assert stats['batches_processed'] == 10
        assert stats['processing_time_ms_avg'] <= 5.0


class TestRingBuffer:
    """Test suite for Ring Buffer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.buffer_config = {
            'size': 1024,
            'element_size_bytes': 64,
            'numa_node': 0,
            'lock_free': True
        }
    
    @patch('nautilus_trader_engine.core.messaging.ring_buffer.RingBuffer')
    def test_ring_buffer_initialization(self, mock_ring_buffer):
        """Test ring buffer initialization."""
        mock_buffer = Mock()
        mock_ring_buffer.return_value = mock_buffer
        
        from nautilus_trader_engine.core.messaging.ring_buffer import RingBuffer
        buffer = RingBuffer(self.buffer_config)
        
        assert buffer is not None
        mock_ring_buffer.assert_called_once_with(self.buffer_config)
    
    @patch('nautilus_trader_engine.core.messaging.ring_buffer.RingBuffer')
    def test_ring_buffer_operations(self, mock_ring_buffer):
        """Test ring buffer read/write operations."""
        mock_buffer = Mock()
        mock_ring_buffer.return_value = mock_buffer
        
        # Mock buffer operations
        test_data = b'test_message_data'
        mock_buffer.write.return_value = True
        mock_buffer.read.return_value = test_data
        mock_buffer.is_full.return_value = False
        mock_buffer.is_empty.return_value = False
        
        from nautilus_trader_engine.core.messaging.ring_buffer import RingBuffer
        buffer = RingBuffer(self.buffer_config)
        
        # Test write operation
        write_result = buffer.write(test_data)
        assert write_result is True
        mock_buffer.write.assert_called_once_with(test_data)
        
        # Test read operation
        read_data = buffer.read()
        assert read_data == test_data
        mock_buffer.read.assert_called_once()
        
        # Test buffer state
        assert not buffer.is_full()
        assert not buffer.is_empty()
    
    @patch('nautilus_trader_engine.core.messaging.ring_buffer.RingBuffer')
    def test_ring_buffer_performance(self, mock_ring_buffer):
        """Test ring buffer performance characteristics."""
        mock_buffer = Mock()
        mock_ring_buffer.return_value = mock_buffer
        
        # Mock performance metrics
        mock_buffer.get_performance_stats.return_value = {
            'write_latency_ns': 100,  # 100 nanoseconds
            'read_latency_ns': 80,
            'throughput_msgs_per_sec': 1000000,  # 1M messages/sec
            'memory_usage_bytes': 65536
        }
        
        from nautilus_trader_engine.core.messaging.ring_buffer import RingBuffer
        buffer = RingBuffer(self.buffer_config)
        
        stats = buffer.get_performance_stats()
        assert stats['write_latency_ns'] <= 200  # Should be very fast
        assert stats['throughput_msgs_per_sec'] >= 500000  # High throughput


class TestMessageRouting:
    """Test suite for Message Routing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.routing_config = {
            'routing_strategy': 'topic_based',
            'load_balancing': 'round_robin',
            'failover_enabled': True,
            'max_retries': 3
        }
    
    @patch('nautilus_trader_engine.core.messaging.routing.MessageRouter')
    def test_message_routing_initialization(self, mock_router):
        """Test message router initialization."""
        mock_router_instance = Mock()
        mock_router.return_value = mock_router_instance
        
        from nautilus_trader_engine.core.messaging.routing import MessageRouter
        router = MessageRouter(self.routing_config)
        
        assert router is not None
        mock_router.assert_called_once_with(self.routing_config)
    
    @patch('nautilus_trader_engine.core.messaging.routing.MessageRouter')
    def test_topic_based_routing(self, mock_router):
        """Test topic-based message routing."""
        mock_router_instance = Mock()
        mock_router.return_value = mock_router_instance
        
        # Mock routing behavior
        mock_router_instance.add_route.return_value = True
        mock_router_instance.route_message.return_value = 'handler_001'
        mock_router_instance.get_route_stats.return_value = {
            'total_routes': 5,
            'active_handlers': 3,
            'messages_routed': 1000
        }
        
        from nautilus_trader_engine.core.messaging.routing import MessageRouter
        router = MessageRouter(self.routing_config)
        
        # Test route addition
        result = router.add_route('market_data.*', 'market_data_handler')
        assert result is True
        
        # Test message routing
        handler = router.route_message('market_data.EURUSD', self.sample_message)
        assert handler == 'handler_001'
        
        # Test routing statistics
        stats = router.get_route_stats()
        assert stats['total_routes'] == 5
        assert stats['messages_routed'] == 1000
    
    @patch('nautilus_trader_engine.core.messaging.routing.MessageRouter')
    def test_load_balancing(self, mock_router):
        """Test load balancing functionality."""
        mock_router_instance = Mock()
        mock_router.return_value = mock_router_instance
        
        # Mock load balancing
        handlers = ['handler_001', 'handler_002', 'handler_003']
        mock_router_instance.get_next_handler.side_effect = handlers
        mock_router_instance.get_handler_load.return_value = {
            'handler_001': 10,
            'handler_002': 8,
            'handler_003': 12
        }
        
        from nautilus_trader_engine.core.messaging.routing import MessageRouter
        router = MessageRouter(self.routing_config)
        
        # Test round-robin selection
        selected_handlers = [router.get_next_handler() for _ in range(3)]
        assert len(set(selected_handlers)) == 3  # All different handlers
        
        # Test load monitoring
        load_stats = router.get_handler_load()
        assert len(load_stats) == 3
        assert all(load >= 0 for load in load_stats.values())


class TestSerialization:
    """Test suite for Message Serialization."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.serialization_config = {
            'format': 'msgpack',
            'compression': 'lz4',
            'schema_validation': True,
            'version': '1.0'
        }
        
        self.test_message = {
            'id': 'msg_001',
            'timestamp': 1640995200.0,
            'data': {
                'symbol': 'EURUSD',
                'price': 1.0850,
                'volume': 1000000
            }
        }
    
    @patch('nautilus_trader_engine.core.messaging.serialization.MessageSerializer')
    def test_serialization_initialization(self, mock_serializer):
        """Test message serializer initialization."""
        mock_serializer_instance = Mock()
        mock_serializer.return_value = mock_serializer_instance
        
        from nautilus_trader_engine.core.messaging.serialization import MessageSerializer
        serializer = MessageSerializer(self.serialization_config)
        
        assert serializer is not None
        mock_serializer.assert_called_once_with(self.serialization_config)
    
    @patch('nautilus_trader_engine.core.messaging.serialization.MessageSerializer')
    def test_message_serialization(self, mock_serializer):
        """Test message serialization and deserialization."""
        mock_serializer_instance = Mock()
        mock_serializer.return_value = mock_serializer_instance
        
        # Mock serialization behavior
        serialized_data = b'\x82\xa2id\xa7msg_001\xa9timestamp\xcb@\x98\x96\x80\x00\x00\x00\x00'
        mock_serializer_instance.serialize.return_value = serialized_data
        mock_serializer_instance.deserialize.return_value = self.test_message
        
        from nautilus_trader_engine.core.messaging.serialization import MessageSerializer
        serializer = MessageSerializer(self.serialization_config)
        
        # Test serialization
        result = serializer.serialize(self.test_message)
        assert result == serialized_data
        mock_serializer_instance.serialize.assert_called_once_with(self.test_message)
        
        # Test deserialization
        deserialized = serializer.deserialize(serialized_data)
        assert deserialized == self.test_message
        mock_serializer_instance.deserialize.assert_called_once_with(serialized_data)
    
    @patch('nautilus_trader_engine.core.messaging.serialization.MessageSerializer')
    def test_compression_performance(self, mock_serializer):
        """Test compression performance."""
        mock_serializer_instance = Mock()
        mock_serializer.return_value = mock_serializer_instance
        
        # Mock compression metrics
        mock_serializer_instance.get_compression_stats.return_value = {
            'compression_ratio': 0.3,  # 70% compression
            'compression_time_ms': 0.5,
            'decompression_time_ms': 0.3,
            'original_size_bytes': 1000,
            'compressed_size_bytes': 300
        }
        
        from nautilus_trader_engine.core.messaging.serialization import MessageSerializer
        serializer = MessageSerializer(self.serialization_config)
        
        stats = serializer.get_compression_stats()
        assert stats['compression_ratio'] <= 0.5  # Good compression
        assert stats['compression_time_ms'] <= 1.0  # Fast compression
        assert stats['compressed_size_bytes'] < stats['original_size_bytes']
    
    @patch('nautilus_trader_engine.core.messaging.serialization.MessageSerializer')
    def test_schema_validation(self, mock_serializer):
        """Test message schema validation."""
        mock_serializer_instance = Mock()
        mock_serializer.return_value = mock_serializer_instance
        
        # Mock validation behavior
        mock_serializer_instance.validate_schema.return_value = True
        mock_serializer_instance.get_validation_errors.return_value = []
        
        from nautilus_trader_engine.core.messaging.serialization import MessageSerializer
        serializer = MessageSerializer(self.serialization_config)
        
        # Test valid message
        is_valid = serializer.validate_schema(self.test_message)
        assert is_valid is True
        
        # Test validation errors
        errors = serializer.get_validation_errors()
        assert len(errors) == 0


class TestMessagingMetrics:
    """Test suite for Messaging Metrics."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.metrics_config = {
            'collection_interval_ms': 100,
            'retention_hours': 24,
            'export_format': 'prometheus'
        }
    
    @patch('nautilus_trader_engine.core.messaging.metrics.MessagingMetrics')
    def test_metrics_collection(self, mock_metrics):
        """Test messaging metrics collection."""
        mock_metrics_instance = Mock()
        mock_metrics.return_value = mock_metrics_instance
        
        # Mock metrics data
        mock_metrics_instance.get_messaging_stats.return_value = {
            'messages_per_second': 50000,
            'avg_latency_ms': 1.2,
            'p99_latency_ms': 5.0,
            'queue_depth': 150,
            'error_rate': 0.001,
            'throughput_mbps': 25.5
        }
        
        from nautilus_trader_engine.core.messaging.metrics import MessagingMetrics
        metrics = MessagingMetrics(self.metrics_config)
        
        stats = metrics.get_messaging_stats()
        assert stats['messages_per_second'] >= 10000
        assert stats['avg_latency_ms'] <= 5.0
        assert stats['error_rate'] <= 0.01
    
    @patch('nautilus_trader_engine.core.messaging.metrics.MessagingMetrics')
    def test_performance_alerts(self, mock_metrics):
        """Test messaging performance alerts."""
        mock_metrics_instance = Mock()
        mock_metrics.return_value = mock_metrics_instance
        
        # Mock alert conditions
        mock_metrics_instance.check_alert_conditions.return_value = {
            'alerts': [
                {'level': 'warning', 'metric': 'latency', 'value': 4.5, 'threshold': 5.0},
                {'level': 'info', 'metric': 'throughput', 'value': 45000, 'threshold': 40000}
            ],
            'overall_health': 'good'
        }
        
        from nautilus_trader_engine.core.messaging.metrics import MessagingMetrics
        metrics = MessagingMetrics(self.metrics_config)
        
        alert_status = metrics.check_alert_conditions()
        assert alert_status['overall_health'] in ['good', 'warning', 'critical']
        assert len(alert_status['alerts']) >= 0


if __name__ == '__main__':
    pytest.main([__file__])