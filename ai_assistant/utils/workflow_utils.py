"""
Workflow utilities for LangGraph workflows

This module provides utilities and common patterns for LangGraph workflow
management, state handling, and workflow orchestration.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Callable, TypedDict
from dataclasses import dataclass, field
from enum import Enum

from shared.utils import get_logger


logger = get_logger(__name__)


class WorkflowStatus(Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeStatus(Enum):
    """Individual node execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowExecution:
    """Workflow execution tracking"""
    workflow_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_name: str = ""
    status: WorkflowStatus = WorkflowStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_time: Optional[float] = None
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    nodes_executed: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NodeExecution:
    """Individual node execution tracking"""
    node_id: str = ""
    node_name: str = ""
    status: NodeStatus = NodeStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_time: Optional[float] = None
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


class WorkflowState(TypedDict, total=False):
    """Base workflow state with common fields"""
    workflow_id: str
    request_id: str
    user_id: str
    status: str
    errors: List[str]
    start_time: str
    current_node: str
    completed_nodes: List[str]
    metadata: Dict[str, Any]


class WorkflowManager:
    """Manager for workflow executions and monitoring"""
    
    def __init__(self):
        """Initialize workflow manager"""
        self._executions = {}
        self._node_executions = {}
        self.logger = get_logger("workflow_manager")
    
    def create_execution(
        self,
        workflow_name: str,
        input_data: Dict[str, Any]
    ) -> WorkflowExecution:
        """
        Create new workflow execution
        
        Args:
            workflow_name: Name of the workflow
            input_data: Input data for the workflow
            
        Returns:
            Workflow execution instance
        """
        execution = WorkflowExecution(
            workflow_name=workflow_name,
            input_data=input_data.copy()
        )
        
        self._executions[execution.workflow_id] = execution
        self.logger.info(f"Created workflow execution: {execution.workflow_id} ({workflow_name})")
        
        return execution
    
    def start_execution(self, workflow_id: str):
        """
        Mark workflow execution as started
        
        Args:
            workflow_id: Workflow execution ID
        """
        if workflow_id in self._executions:
            execution = self._executions[workflow_id]
            execution.status = WorkflowStatus.RUNNING
            execution.start_time = datetime.now(timezone.utc)
            self.logger.info(f"Started workflow execution: {workflow_id}")
    
    def complete_execution(
        self,
        workflow_id: str,
        output_data: Dict[str, Any],
        success: bool = True,
        error: Optional[str] = None
    ):
        """
        Mark workflow execution as completed
        
        Args:
            workflow_id: Workflow execution ID
            output_data: Output data from the workflow
            success: Whether execution was successful
            error: Error message if failed
        """
        if workflow_id in self._executions:
            execution = self._executions[workflow_id]
            execution.status = WorkflowStatus.COMPLETED if success else WorkflowStatus.FAILED
            execution.end_time = datetime.now(timezone.utc)
            execution.output_data = output_data.copy()
            execution.error = error
            
            if execution.start_time:
                execution.execution_time = (execution.end_time - execution.start_time).total_seconds()
            
            self.logger.info(f"Completed workflow execution: {workflow_id} ({'success' if success else 'failed'})")
    
    def track_node_execution(
        self,
        workflow_id: str,
        node_name: str,
        status: NodeStatus,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """
        Track individual node execution
        
        Args:
            workflow_id: Workflow execution ID
            node_name: Name of the node
            status: Node execution status
            input_data: Input data for the node
            output_data: Output data from the node
            error: Error message if failed
        """
        node_id = f"{workflow_id}:{node_name}"
        
        if node_id not in self._node_executions:
            self._node_executions[node_id] = NodeExecution(
                node_id=node_id,
                node_name=node_name
            )
        
        node_execution = self._node_executions[node_id]
        node_execution.status = status
        
        if status == NodeStatus.RUNNING and not node_execution.start_time:
            node_execution.start_time = datetime.now(timezone.utc)
        elif status in [NodeStatus.COMPLETED, NodeStatus.FAILED]:
            node_execution.end_time = datetime.now(timezone.utc)
            if node_execution.start_time:
                node_execution.execution_time = (
                    node_execution.end_time - node_execution.start_time
                ).total_seconds()
        
        if input_data:
            node_execution.input_data = input_data.copy()
        if output_data:
            node_execution.output_data = output_data.copy()
        if error:
            node_execution.error = error
        
        # Update workflow execution
        if workflow_id in self._executions:
            execution = self._executions[workflow_id]
            if node_name not in execution.nodes_executed and status == NodeStatus.COMPLETED:
                execution.nodes_executed.append(node_name)
    
    def get_execution(self, workflow_id: str) -> Optional[WorkflowExecution]:
        """
        Get workflow execution by ID
        
        Args:
            workflow_id: Workflow execution ID
            
        Returns:
            Workflow execution or None
        """
        return self._executions.get(workflow_id)
    
    def get_node_execution(self, workflow_id: str, node_name: str) -> Optional[NodeExecution]:
        """
        Get node execution
        
        Args:
            workflow_id: Workflow execution ID
            node_name: Node name
            
        Returns:
            Node execution or None
        """
        node_id = f"{workflow_id}:{node_name}"
        return self._node_executions.get(node_id)
    
    def get_execution_summary(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get execution summary with metrics
        
        Args:
            workflow_id: Workflow execution ID
            
        Returns:
            Execution summary
        """
        execution = self.get_execution(workflow_id)
        if not execution:
            return {"error": "Workflow execution not found"}
        
        # Get node executions
        node_executions = []
        for node_id, node_exec in self._node_executions.items():
            if node_id.startswith(f"{workflow_id}:"):
                node_executions.append({
                    "node_name": node_exec.node_name,
                    "status": node_exec.status.value,
                    "execution_time": node_exec.execution_time,
                    "error": node_exec.error
                })
        
        return {
            "workflow_id": execution.workflow_id,
            "workflow_name": execution.workflow_name,
            "status": execution.status.value,
            "execution_time": execution.execution_time,
            "start_time": execution.start_time.isoformat() if execution.start_time else None,
            "end_time": execution.end_time.isoformat() if execution.end_time else None,
            "nodes_executed": execution.nodes_executed,
            "node_executions": node_executions,
            "error": execution.error,
            "metrics": execution.metrics
        }


class ConditionalRouter:
    """Router for conditional workflow paths"""
    
    def __init__(self):
        """Initialize conditional router"""
        self.conditions = {}
        self.logger = get_logger("conditional_router")
    
    def add_condition(
        self,
        condition_name: str,
        condition_func: Callable[[Dict[str, Any]], bool]
    ):
        """
        Add condition for routing
        
        Args:
            condition_name: Name of the condition
            condition_func: Function that evaluates the condition
        """
        self.conditions[condition_name] = condition_func
        self.logger.info(f"Added condition: {condition_name}")
    
    def evaluate_route(
        self,
        state: Dict[str, Any],
        route_map: Dict[str, str]
    ) -> str:
        """
        Evaluate routing conditions
        
        Args:
            state: Current workflow state
            route_map: Map of condition names to next nodes
            
        Returns:
            Next node name
        """
        for condition_name, next_node in route_map.items():
            if condition_name in self.conditions:
                condition_func = self.conditions[condition_name]
                try:
                    if condition_func(state):
                        self.logger.info(f"Condition {condition_name} met, routing to {next_node}")
                        return next_node
                except Exception as e:
                    self.logger.error(f"Error evaluating condition {condition_name}: {e}")
        
        # Default route
        default_node = route_map.get("default", "END")
        self.logger.info(f"No conditions met, routing to default: {default_node}")
        return default_node


class WorkflowRetryHandler:
    """Handler for workflow and node retries"""
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0):
        """
        Initialize retry handler
        
        Args:
            max_retries: Maximum number of retries
            backoff_factor: Exponential backoff factor
        """
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.logger = get_logger("workflow_retry")
    
    async def retry_with_backoff(
        self,
        operation: Callable,
        *args,
        max_retries: Optional[int] = None,
        **kwargs
    ) -> Any:
        """
        Retry operation with exponential backoff
        
        Args:
            operation: Operation to retry
            *args: Operation arguments
            max_retries: Override max retries
            **kwargs: Operation keyword arguments
            
        Returns:
            Operation result
        """
        max_attempts = max_retries or self.max_retries
        
        for attempt in range(max_attempts + 1):
            try:
                if asyncio.iscoroutinefunction(operation):
                    result = await operation(*args, **kwargs)
                else:
                    result = operation(*args, **kwargs)
                
                if attempt > 0:
                    self.logger.info(f"Operation succeeded on attempt {attempt + 1}")
                
                return result
            
            except Exception as e:
                if attempt == max_attempts:
                    self.logger.error(f"Operation failed after {max_attempts + 1} attempts: {e}")
                    raise
                
                delay = self.backoff_factor ** attempt
                self.logger.warning(f"Operation failed on attempt {attempt + 1}, retrying in {delay}s: {e}")
                await asyncio.sleep(delay)


class WorkflowMetrics:
    """Metrics collection for workflows"""
    
    def __init__(self):
        """Initialize workflow metrics"""
        self._metrics = {}
        self.logger = get_logger("workflow_metrics")
    
    def record_execution_time(self, workflow_name: str, execution_time: float):
        """
        Record workflow execution time
        
        Args:
            workflow_name: Name of the workflow
            execution_time: Execution time in seconds
        """
        if workflow_name not in self._metrics:
            self._metrics[workflow_name] = {
                "execution_times": [],
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0
            }
        
        self._metrics[workflow_name]["execution_times"].append(execution_time)
        self._metrics[workflow_name]["total_executions"] += 1
    
    def record_execution_result(self, workflow_name: str, success: bool):
        """
        Record workflow execution result
        
        Args:
            workflow_name: Name of the workflow
            success: Whether execution was successful
        """
        if workflow_name in self._metrics:
            if success:
                self._metrics[workflow_name]["successful_executions"] += 1
            else:
                self._metrics[workflow_name]["failed_executions"] += 1
    
    def get_workflow_metrics(self, workflow_name: str) -> Dict[str, Any]:
        """
        Get metrics for a specific workflow
        
        Args:
            workflow_name: Name of the workflow
            
        Returns:
            Workflow metrics
        """
        if workflow_name not in self._metrics:
            return {}
        
        metrics = self._metrics[workflow_name]
        execution_times = metrics["execution_times"]
        
        if not execution_times:
            return metrics
        
        return {
            **metrics,
            "average_execution_time": sum(execution_times) / len(execution_times),
            "min_execution_time": min(execution_times),
            "max_execution_time": max(execution_times),
            "success_rate": (
                metrics["successful_executions"] / metrics["total_executions"]
                if metrics["total_executions"] > 0 else 0
            )
        }
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get metrics for all workflows
        
        Returns:
            All workflow metrics
        """
        return {
            workflow_name: self.get_workflow_metrics(workflow_name)
            for workflow_name in self._metrics.keys()
        }


# Global instances
workflow_manager = WorkflowManager()
conditional_router = ConditionalRouter()
retry_handler = WorkflowRetryHandler()
workflow_metrics = WorkflowMetrics()


def get_workflow_manager() -> WorkflowManager:
    """Get global workflow manager"""
    return workflow_manager


def get_conditional_router() -> ConditionalRouter:
    """Get global conditional router"""
    return conditional_router


def get_retry_handler() -> WorkflowRetryHandler:
    """Get global retry handler"""
    return retry_handler


def get_workflow_metrics() -> WorkflowMetrics:
    """Get global workflow metrics"""
    return workflow_metrics


# Common workflow utility functions
def create_error_state(
    state: WorkflowState,
    error_message: str,
    node_name: str = "unknown"
) -> WorkflowState:
    """
    Create error state for workflow
    
    Args:
        state: Current workflow state
        error_message: Error message
        node_name: Name of the node where error occurred
        
    Returns:
        Updated state with error
    """
    state["status"] = "error"
    state["errors"].append(f"{node_name}: {error_message}")
    return state


def should_continue_workflow(state: WorkflowState) -> str:
    """
    Determine if workflow should continue or stop
    
    Args:
        state: Current workflow state
        
    Returns:
        Next edge to follow
    """
    if state.get("errors"):
        return "error"
    
    if state.get("status") == "cancelled":
        return "cancelled"
    
    return "continue"


async def timeout_wrapper(
    operation: Callable,
    timeout_seconds: float,
    *args,
    **kwargs
) -> Any:
    """
    Wrap operation with timeout
    
    Args:
        operation: Operation to execute
        timeout_seconds: Timeout in seconds
        *args: Operation arguments
        **kwargs: Operation keyword arguments
        
    Returns:
        Operation result
        
    Raises:
        asyncio.TimeoutError: If operation times out
    """
    if asyncio.iscoroutinefunction(operation):
        return await asyncio.wait_for(
            operation(*args, **kwargs),
            timeout=timeout_seconds
        )
    else:
        # Run sync operation in executor with timeout
        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, operation, *args, **kwargs),
            timeout=timeout_seconds
        )