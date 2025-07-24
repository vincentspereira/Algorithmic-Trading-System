"""
AI Assistant Service for Algorithmic Trading System - Phase 3
FastAPI backend service that will integrate with Phase 2 API endpoints
and serve as the backend for the AI assistant functionality.
"""

import os
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv
import requests
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AppConfig:
    """Configuration class for managing application settings"""
    
    def __init__(self):
        # Phase 2 API Configuration
        self.phase2_api_base_url = os.getenv("PHASE2_API_BASE_URL", "http://localhost:8001")
        self.phase2_api_key = os.getenv("PHASE2_API_KEY", "")
        
        # AI Assistant Configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.langchain_api_key = os.getenv("LANGCHAIN_API_KEY", "")
        
        # Service Configuration
        self.service_port = int(os.getenv("AI_ASSISTANT_PORT", "8002"))
        self.service_host = os.getenv("AI_ASSISTANT_HOST", "0.0.0.0")
        self.debug_mode = os.getenv("DEBUG", "false").lower() == "true"
        
        # CORS Configuration
        self.allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")
        
    def get_phase2_headers(self) -> Dict[str, str]:
        """Get headers for Phase 2 API requests"""
        headers = {"Content-Type": "application/json"}
        if self.phase2_api_key:
            headers["Authorization"] = f"Bearer {self.phase2_api_key}"
        return headers


# Initialize configuration
config = AppConfig()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("AI Assistant Service starting up...")
    
    # Startup logic
    try:
        # Test connection to Phase 2 API
        response = requests.get(
            f"{config.phase2_api_base_url}/health",
            headers=config.get_phase2_headers(),
            timeout=5
        )
        if response.status_code == 200:
            logger.info("Successfully connected to Phase 2 API")
        else:
            logger.warning(f"Phase 2 API health check returned status: {response.status_code}")
    except requests.RequestException as e:
        logger.warning(f"Could not connect to Phase 2 API: {e}")
    
    yield
    
    # Shutdown logic
    logger.info("AI Assistant Service shutting down...")


# Initialize FastAPI app
app = FastAPI(
    title="AI Assistant Service",
    description="AI Assistant backend for the Algorithmic Trading System - Phase 3",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Pydantic models
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
    """Chat response model for future AI interactions"""
    response: str = Field(..., description="AI assistant response")
    session_id: str = Field(..., description="Session ID")
    timestamp: str = Field(..., description="Response timestamp")


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint to verify service status and dependencies
    """
    from datetime import datetime
    
    # Check Phase 2 API connection
    phase2_connected = False
    try:
        response = requests.get(
            f"{config.phase2_api_base_url}/health",
            headers=config.get_phase2_headers(),
            timeout=5
        )
        phase2_connected = response.status_code == 200
    except requests.RequestException:
        phase2_connected = False
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0",
        phase2_connection=phase2_connected
    )


# Service information endpoint
@app.get("/api/v1/info", response_model=InfoResponse, tags=["Information"])
async def get_service_info():
    """
    Get service information and capabilities
    """
    return InfoResponse(
        service_name="AI Assistant Service",
        version="1.0.0",
        description="AI Assistant backend for the Algorithmic Trading System - Phase 3",
        phase2_api_url=config.phase2_api_base_url,
        supported_features=[
            "Health monitoring",
            "Phase 2 API integration",
            "LangChain framework support",
            "Local LLM support (Ollama)",
            "Chat interface (coming soon)",
            "Trading strategy assistance (coming soon)",
            "Backtesting analysis (coming soon)"
        ]
    )


# Placeholder chat endpoint for future AI interactions
@app.post("/api/v1/chat", response_model=ChatResponse, tags=["AI Chat"])
async def chat_with_assistant(request: ChatRequest):
    """
    Placeholder endpoint for AI chat functionality
    This will be implemented in future iterations with LangChain integration
    """
    from datetime import datetime
    import uuid
    
    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())
    
    # Placeholder response - will be replaced with actual AI logic
    placeholder_response = (
        f"Thank you for your message: '{request.message}'. "
        "The AI assistant is currently in development. "
        "Future capabilities will include trading strategy advice, "
        "backtesting analysis, and market insights powered by LangChain."
    )
    
    return ChatResponse(
        response=placeholder_response,
        session_id=session_id,
        timestamp=datetime.utcnow().isoformat()
    )


# Phase 2 API proxy endpoints (for future integration)
@app.get("/api/v1/phase2/status", tags=["Phase 2 Integration"])
async def get_phase2_status():
    """
    Get Phase 2 API status
    """
    try:
        response = requests.get(
            f"{config.phase2_api_base_url}/health",
            headers=config.get_phase2_headers(),
            timeout=10
        )
        return {
            "phase2_status": "connected" if response.status_code == 200 else "disconnected",
            "status_code": response.status_code,
            "response_time": response.elapsed.total_seconds()
        }
    except requests.RequestException as e:
        return {
            "phase2_status": "error",
            "error": str(e)
        }


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with service information
    """
    return {
        "message": "AI Assistant Service for Algorithmic Trading System",
        "version": "1.0.0",
        "phase": "Phase 3 - AI Assistant MVP",
        "docs": "/docs",
        "health": "/health",
        "info": "/api/v1/info"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.service_host,
        port=config.service_port,
        reload=config.debug_mode,
        log_level="info"
    )