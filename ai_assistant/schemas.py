
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Current timestamp")
    version: str = Field(..., description="Service version")
    phase2_connection: bool = Field(..., description="Phase 2 API connection status")


class InfoResponse(BaseModel):
    """Service information response model"""
    service_name: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    description: str = Field(..., description="Service description")
    phase2_api_url: str = Field(..., description="Phase 2 API base URL")
    supported_features: list = Field(..., description="List of supported features")


class ChatRequest(BaseModel):
    """Chat request model for future AI interactions"""
    message: str = Field(..., description="User message", min_length=1, max_length=1000)
    session_id: Optional[str] = Field(None, description="Optional session ID for conversation tracking")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context data")


class ChatResponse(BaseModel):
    """Chat response model for AI interactions"""
    response: str = Field(..., description="AI assistant response")
    session_id: str = Field(..., description="Session ID")
    timestamp: str = Field(..., description="Response timestamp")
    reasoning: Optional[List[Dict[str, Any]]] = Field(None, description="Agent's reasoning process (intermediate steps)")
    tools_used: Optional[List[str]] = Field(None, description="List of tools that were invoked")
