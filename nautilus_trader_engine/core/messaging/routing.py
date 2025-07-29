"""
Message Routing System
High-performance topic-based message routing for trading system
"""

import re
import threading
from abc import ABC, abstractmethod
from typing import Dict, List, Set, Optional, Callable, Pattern, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

from .serialization import MessageType


class RoutingStrategy(Enum):
    """Message routing strategies"""
    EXACT_MATCH = "exact"           # Exact topic match
    PREFIX_MATCH = "prefix"         # Topic prefix matching
    WILDCARD_MATCH = "wildcard"     # Wildcard pattern matching
    REGEX_MATCH = "regex"           # Regular expression matching


@dataclass
class RoutingRule:
    """Message routing rule definition"""
    pattern: str
    strategy: RoutingStrategy
    priority: int = 0
    enabled: bool = True
    compiled_pattern: Optional[Pattern] = field(default=None, init=False)
    
    def __post_init__(self):
        """Compile patterns for performance"""
        if self.strategy == RoutingStrategy.REGEX_MATCH:
            self.compiled_pattern = re.compile(self.pattern)
        elif self.strategy == RoutingStrategy.WILDCARD_MATCH:
            # Convert wildcard to regex
            regex_pattern = self.pattern.replace('*', '.*').replace('?', '.')
            self.compiled_pattern = re.compile(f"^{regex_pattern}$")


class MessageRouter(ABC):
    """Abstract base class for message routers"""
    
    @abstractmethod
    def add_route(self, pattern: str, handler_id: str, strategy: RoutingStrategy = RoutingStrategy.EXACT_MATCH):
        """Add a routing rule"""
        pass
    
    @abstractmethod
    def remove_route(self, pattern: str, handler_id: str):
        """Remove a routing rule"""
        pass
    
    @abstractmethod
    def route_message(self, topic: str) -> List[str]:
        """Route message to appropriate handlers"""
        pass


class TopicRouter(MessageRouter):
    """
    High-performance topic-based message router
    
    Features:
    - Multiple routing strategies (exact, prefix, wildcard, regex)
    - Priority-based routing
    - Thread-safe operations
    - Performance optimized lookups
    """
    
    def __init__(self):
        self._exact_routes: Dict[str, Set[str]] = {}
        self._prefix_routes: List[tuple[str, Set[str]]] = []
        self._wildcard_routes: List[tuple[RoutingRule, Set[str]]] = []
        self._regex_routes: List[tuple[RoutingRule, Set[str]]] = []
        
        # Thread safety
        self._lock = threading.RWLock() if hasattr(threading, 'RWLock') else threading.Lock()
        
        # Performance caching
        self._route_cache: Dict[str, List[str]] = {}
        self._cache_size_limit = 10000
        
        self.logger = logging.getLogger(__name__)
    
    def add_route(self, 
                  pattern: str, 
                  handler_id: str, 
                  strategy: RoutingStrategy = RoutingStrategy.EXACT_MATCH,
                  priority: int = 0):
        """
        Add a routing rule
        
        Args:
            pattern: Topic pattern to match
            handler_id: Unique identifier for the handler
            strategy: Routing strategy to use
            priority: Priority for rule evaluation (higher = first)
        """
        with self._lock:
            if strategy == RoutingStrategy.EXACT_MATCH:
                if pattern not in self._exact_routes:
                    self._exact_routes[pattern] = set()
                self._exact_routes[pattern].add(handler_id)
            
            elif strategy == RoutingStrategy.PREFIX_MATCH:
                # Insert in priority order
                inserted = False
                for i, (existing_pattern, handlers) in enumerate(self._prefix_routes):
                    if existing_pattern == pattern:
                        handlers.add(handler_id)
                        inserted = True
                        break
                
                if not inserted:
                    self._prefix_routes.append((pattern, {handler_id}))
                    # Sort by pattern length (longer first) for better matching
                    self._prefix_routes.sort(key=lambda x: len(x[0]), reverse=True)
            
            elif strategy in [RoutingStrategy.WILDCARD_MATCH, RoutingStrategy.REGEX_MATCH]:
                rule = RoutingRule(pattern, strategy, priority)
                
                # Find existing rule or create new one
                routes_list = self._wildcard_routes if strategy == RoutingStrategy.WILDCARD_MATCH else self._regex_routes
                
                inserted = False
                for i, (existing_rule, handlers) in enumerate(routes_list):
                    if existing_rule.pattern == pattern:
                        handlers.add(handler_id)
                        inserted = True
                        break
                
                if not inserted:
                    routes_list.append((rule, {handler_id}))
                    # Sort by priority (higher first)
                    routes_list.sort(key=lambda x: x[0].priority, reverse=True)
            
            # Clear cache when routes change
            self._route_cache.clear()
            
            self.logger.debug(f"Added route: {pattern} -> {handler_id} ({strategy.value})")
    
    def remove_route(self, pattern: str, handler_id: str):
        """Remove a routing rule"""
        with self._lock:
            removed = False
            
            # Check exact routes
            if pattern in self._exact_routes:
                self._exact_routes[pattern].discard(handler_id)
                if not self._exact_routes[pattern]:
                    del self._exact_routes[pattern]
                removed = True
            
            # Check prefix routes
            for i, (existing_pattern, handlers) in enumerate(self._prefix_routes):
                if existing_pattern == pattern:
                    handlers.discard(handler_id)
                    if not handlers:
                        del self._prefix_routes[i]
                    removed = True
                    break
            
            # Check wildcard and regex routes
            for routes_list in [self._wildcard_routes, self._regex_routes]:
                for i, (rule, handlers) in enumerate(routes_list):
                    if rule.pattern == pattern:
                        handlers.discard(handler_id)
                        if not handlers:
                            del routes_list[i]
                        removed = True
                        break
            
            if removed:
                self._route_cache.clear()
                self.logger.debug(f"Removed route: {pattern} -> {handler_id}")
    
    def route_message(self, topic: str) -> List[str]:
        """
        Route message to appropriate handlers
        
        Args:
            topic: Message topic to route
            
        Returns:
            List[str]: List of handler IDs that should receive the message
        """
        # Check cache first
        if topic in self._route_cache:
            return self._route_cache[topic]
        
        handlers = set()
        
        # Use read lock for better concurrency
        with self._lock:
            # 1. Exact match (fastest)
            if topic in self._exact_routes:
                handlers.update(self._exact_routes[topic])
            
            # 2. Prefix match
            for pattern, route_handlers in self._prefix_routes:
                if topic.startswith(pattern):
                    handlers.update(route_handlers)
            
            # 3. Wildcard match
            for rule, route_handlers in self._wildcard_routes:
                if rule.enabled and rule.compiled_pattern and rule.compiled_pattern.match(topic):
                    handlers.update(route_handlers)
            
            # 4. Regex match
            for rule, route_handlers in self._regex_routes:
                if rule.enabled and rule.compiled_pattern and rule.compiled_pattern.match(topic):
                    handlers.update(route_handlers)
        
        # Convert to list and cache result
        handler_list = list(handlers)
        
        # Limit cache size to prevent memory issues
        if len(self._route_cache) < self._cache_size_limit:
            self._route_cache[topic] = handler_list
        
        return handler_list
    
    def get_route_stats(self) -> Dict[str, int]:
        """Get routing statistics"""
        with self._lock:
            return {
                'exact_routes': len(self._exact_routes),
                'prefix_routes': len(self._prefix_routes),
                'wildcard_routes': len(self._wildcard_routes),
                'regex_routes': len(self._regex_routes),
                'cached_routes': len(self._route_cache)
            }
    
    def clear_cache(self):
        """Clear the routing cache"""
        with self._lock:
            self._route_cache.clear()
    
    def list_routes(self) -> Dict[str, List[str]]:
        """List all current routes"""
        routes = {}
        
        with self._lock:
            # Exact routes
            for pattern, handlers in self._exact_routes.items():
                routes[f"exact:{pattern}"] = list(handlers)
            
            # Prefix routes
            for pattern, handlers in self._prefix_routes:
                routes[f"prefix:{pattern}"] = list(handlers)
            
            # Wildcard routes
            for rule, handlers in self._wildcard_routes:
                routes[f"wildcard:{rule.pattern}"] = list(handlers)
            
            # Regex routes
            for rule, handlers in self._regex_routes:
                routes[f"regex:{rule.pattern}"] = list(handlers)
        
        return routes


class MessageTypeRouter(MessageRouter):
    """Router that routes based on message type rather than topic"""
    
    def __init__(self):
        self._type_routes: Dict[MessageType, Set[str]] = {}
        self._lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
    
    def add_route(self, message_type: MessageType, handler_id: str, **kwargs):
        """Add route for specific message type"""
        with self._lock:
            if message_type not in self._type_routes:
                self._type_routes[message_type] = set()
            self._type_routes[message_type].add(handler_id)
            
            self.logger.debug(f"Added message type route: {message_type} -> {handler_id}")
    
    def remove_route(self, message_type: MessageType, handler_id: str):
        """Remove route for specific message type"""
        with self._lock:
            if message_type in self._type_routes:
                self._type_routes[message_type].discard(handler_id)
                if not self._type_routes[message_type]:
                    del self._type_routes[message_type]
                
                self.logger.debug(f"Removed message type route: {message_type} -> {handler_id}")
    
    def route_message(self, message_type: MessageType) -> List[str]:
        """Route message based on type"""
        with self._lock:
            return list(self._type_routes.get(message_type, set()))


class CompositeRouter(MessageRouter):
    """
    Composite router that combines multiple routing strategies
    
    Allows routing based on both topic patterns and message types
    """
    
    def __init__(self):
        self.topic_router = TopicRouter()
        self.type_router = MessageTypeRouter()
        self.logger = logging.getLogger(__name__)
    
    def add_topic_route(self, pattern: str, handler_id: str, strategy: RoutingStrategy = RoutingStrategy.EXACT_MATCH):
        """Add topic-based route"""
        self.topic_router.add_route(pattern, handler_id, strategy)
    
    def add_type_route(self, message_type: MessageType, handler_id: str):
        """Add message type-based route"""
        self.type_router.add_route(message_type, handler_id)
    
    def add_route(self, pattern: str, handler_id: str, strategy: RoutingStrategy = RoutingStrategy.EXACT_MATCH):
        """Add route (defaults to topic routing)"""
        self.topic_router.add_route(pattern, handler_id, strategy)
    
    def remove_route(self, pattern: str, handler_id: str):
        """Remove route (defaults to topic routing)"""
        self.topic_router.remove_route(pattern, handler_id)
    
    def route_message(self, topic: str, message_type: Optional[MessageType] = None) -> List[str]:
        """Route message using both topic and type"""
        handlers = set()
        
        # Route by topic
        handlers.update(self.topic_router.route_message(topic))
        
        # Route by message type if provided
        if message_type:
            handlers.update(self.type_router.route_message(message_type))
        
        return list(handlers)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get combined routing statistics"""
        return {
            'topic_router': self.topic_router.get_route_stats(),
            'type_router': len(self.type_router._type_routes)
        }


# Fallback for systems without RWLock
if not hasattr(threading, 'RWLock'):
    class RWLock:
        """Simple read-write lock implementation"""
        def __init__(self):
            self._lock = threading.Lock()
        
        def __enter__(self):
            self._lock.__enter__()
        
        def __exit__(self, *args):
            self._lock.__exit__(*args)
    
    threading.RWLock = RWLock