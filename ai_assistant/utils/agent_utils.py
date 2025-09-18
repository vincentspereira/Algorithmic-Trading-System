"""
Agent utilities for the AI Assistant

This module provides base classes and common functionality for all AI agents
in the system, including message handling, state management, and communication.
"""

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypedDict
from dataclasses import dataclass, field
from enum import Enum

from shared.utils import get_logger


logger = get_logger(__name__)


class MessageType(Enum):
    """Types of messages between agents"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


class AgentStatus(Enum):
    """Agent status states"""
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class AgentMessage:
    """Message structure for agent communication"""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    receiver: str = ""
    message_type: MessageType = MessageType.REQUEST
    content: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Response structure for agent operations"""
    success: bool = True
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    execution_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowState(TypedDict, total=False):
    """Base workflow state for LangGraph workflows"""
    request_id: str
    user_id: str
    status: str
    errors: List[str]
    metadata: Dict[str, Any]


class WorkflowNode:
    """Base class for workflow nodes"""
    
    def __init__(self, name: str):
        """
        Initialize workflow node
        
        Args:
            name: Node name
        """
        self.name = name
        self.logger = get_logger(f"workflow.{name}")
    
    async def execute(self, state: WorkflowState) -> WorkflowState:
        """
        Execute workflow node
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        self.logger.info(f"Executing workflow node: {self.name}")
        
        try:
            result = await self._process(state)
            self.logger.info(f"Workflow node {self.name} completed successfully")
            return result
        except Exception as e:
            self.logger.error(f"Workflow node {self.name} failed: {e}")
            state["errors"].append(f"Node {self.name} error: {str(e)}")
            return state
    
    @abstractmethod
    async def _process(self, state: WorkflowState) -> WorkflowState:
        """
        Process workflow node logic
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        pass


class AgentBase(ABC):
    """
    Base class for all AI agents
    
    Provides common functionality for agent initialization, communication,
    state management, and lifecycle operations.
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize agent
        
        Args:
            name: Agent name
            config: Agent configuration
        """
        self.name = name
        self.config = config or {}
        self.agent_id = str(uuid.uuid4())
        self.status = AgentStatus.INITIALIZING
        self.logger = get_logger(f"agent.{name}")
        
        # Message handling
        self._message_queue = asyncio.Queue()
        self._response_handlers = {}
        
        # State management
        self._state = {}
        self._metrics = {
            "messages_processed": 0,
            "errors_encountered": 0,
            "start_time": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc)
        }
        
        # Initialize agent
        self._initialize()
    
    def _initialize(self):
        """Initialize agent-specific configuration"""
        self.status = AgentStatus.READY
        self.logger.info(f"Agent {self.name} initialized with ID: {self.agent_id}")
    
    async def send_message(
        self,
        receiver: str,
        message_type: MessageType,
        content: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> AgentMessage:
        """
        Send message to another agent
        
        Args:
            receiver: Target agent name
            message_type: Type of message
            content: Message content
            correlation_id: Optional correlation ID
            
        Returns:
            Sent message
        """
        message = AgentMessage(
            sender=self.name,
            receiver=receiver,
            message_type=message_type,
            content=content,
            correlation_id=correlation_id
        )
        
        self.logger.info(f"Sending {message_type.value} message to {receiver}")
        
        # In a real implementation, this would use the message bus (Kafka)
        # For now, just log the message
        self._metrics["messages_processed"] += 1
        self._metrics["last_activity"] = datetime.now(timezone.utc)
        
        return message
    
    async def receive_message(self, message: AgentMessage) -> AgentResponse:
        """
        Receive and process message
        
        Args:
            message: Received message
            
        Returns:
            Response to the message
        """
        self.logger.info(f"Received {message.message_type.value} message from {message.sender}")
        
        try:
            self.status = AgentStatus.BUSY
            
            # Process message based on type
            if message.message_type == MessageType.REQUEST:
                response = await self._handle_request(message)
            elif message.message_type == MessageType.NOTIFICATION:
                response = await self._handle_notification(message)
            else:
                response = AgentResponse(
                    success=False,
                    error=f"Unsupported message type: {message.message_type.value}"
                )
            
            self.status = AgentStatus.READY
            self._metrics["messages_processed"] += 1
            self._metrics["last_activity"] = datetime.now(timezone.utc)
            
            return response
        
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            self.status = AgentStatus.ERROR
            self._metrics["errors_encountered"] += 1
            
            return AgentResponse(
                success=False,
                error=str(e),
                message="Failed to process message"
            )
    
    async def _handle_request(self, message: AgentMessage) -> AgentResponse:
        """
        Handle request message
        
        Args:
            message: Request message
            
        Returns:
            Response to the request
        """
        # Default implementation - override in subclasses
        return AgentResponse(
            success=True,
            message=f"Request processed by {self.name}",
            data={"processed": True}
        )
    
    async def _handle_notification(self, message: AgentMessage) -> AgentResponse:
        """
        Handle notification message
        
        Args:
            message: Notification message
            
        Returns:
            Response to the notification
        """
        # Default implementation - override in subclasses
        self.logger.info(f"Notification received: {message.content}")
        return AgentResponse(
            success=True,
            message="Notification acknowledged"
        )
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get agent status information
        
        Returns:
            Agent status dictionary
        """
        uptime = datetime.now(timezone.utc) - self._metrics["start_time"]
        
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": self.status.value,
            "uptime_seconds": int(uptime.total_seconds()),
            "metrics": self._metrics.copy(),
            "state_size": len(self._state),
            "queue_size": self._message_queue.qsize()
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get agent performance metrics
        
        Returns:
            Performance metrics
        """
        uptime = datetime.now(timezone.utc) - self._metrics["start_time"]
        
        return {
            "messages_processed": self._metrics["messages_processed"],
            "errors_encountered": self._metrics["errors_encountered"],
            "error_rate": (
                self._metrics["errors_encountered"] / self._metrics["messages_processed"]
                if self._metrics["messages_processed"] > 0 else 0
            ),
            "uptime_seconds": int(uptime.total_seconds()),
            "last_activity": self._metrics["last_activity"].isoformat(),
            "messages_per_hour": (
                self._metrics["messages_processed"] / (uptime.total_seconds() / 3600)
                if uptime.total_seconds() > 0 else 0
            )
        }
    
    def update_state(self, key: str, value: Any):
        """
        Update agent state
        
        Args:
            key: State key
            value: State value
        """
        self._state[key] = value
        self.logger.debug(f"State updated: {key}")
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """
        Get agent state value
        
        Args:
            key: State key
            default: Default value if key not found
            
        Returns:
            State value
        """
        return self._state.get(key, default)
    
    async def shutdown(self):
        """Shutdown agent gracefully"""
        self.logger.info(f"Shutting down agent {self.name}")
        self.status = AgentStatus.SHUTDOWN
        
        # Clear message queue
        while not self._message_queue.empty():
            try:
                self._message_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        # Perform cleanup
        await self._cleanup()
        
        self.logger.info(f"Agent {self.name} shutdown complete")
    
    async def _cleanup(self):
        """Perform agent-specific cleanup"""
        # Override in subclasses if needed
        pass


class AgentRegistry:
    """Registry for managing agent instances"""
    
    def __init__(self):
        """Initialize agent registry"""
        self._agents = {}
        self.logger = get_logger("agent_registry")
    
    def register_agent(self, agent: AgentBase):
        """
        Register an agent
        
        Args:
            agent: Agent to register
        """
        self._agents[agent.name] = agent
        self.logger.info(f"Agent registered: {agent.name} ({agent.agent_id})")
    
    def unregister_agent(self, agent_name: str):
        """
        Unregister an agent
        
        Args:
            agent_name: Name of agent to unregister
        """
        if agent_name in self._agents:
            del self._agents[agent_name]
            self.logger.info(f"Agent unregistered: {agent_name}")
    
    def get_agent(self, agent_name: str) -> Optional[AgentBase]:
        """
        Get agent by name
        
        Args:
            agent_name: Agent name
            
        Returns:
            Agent instance or None
        """
        return self._agents.get(agent_name)
    
    def list_agents(self) -> List[str]:
        """
        List all registered agent names
        
        Returns:
            List of agent names
        """
        return list(self._agents.keys())
    
    def get_all_agents_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all registered agents
        
        Returns:
            Dictionary of agent statuses
        """
        return {name: agent.get_status() for name, agent in self._agents.items()}
    
    async def shutdown_all_agents(self):
        """Shutdown all registered agents"""
        self.logger.info("Shutting down all agents")
        
        for agent in self._agents.values():
            try:
                await agent.shutdown()
            except Exception as e:
                self.logger.error(f"Error shutting down agent {agent.name}: {e}")
        
        self._agents.clear()
        self.logger.info("All agents shutdown complete")


# Global agent registry instance
agent_registry = AgentRegistry()


def get_agent_registry() -> AgentRegistry:
    """
    Get the global agent registry
    
    Returns:
        Agent registry instance
    """
    return agent_registry