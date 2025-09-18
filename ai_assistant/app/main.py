
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import requests

from ai_assistant.config import config
from app.api.endpoints import router
from app.agents.main_agent import initialize_agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

    # Initialize ReAct agent
    try:
        if initialize_agent():
            logger.info("ReAct agent initialized successfully")
        else:
            logger.error("Failed to initialize ReAct agent - chat functionality will be limited")
    except Exception as e:
        logger.error(f"Error during agent initialization: {e}")

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

# Include API router
app.include_router(router)

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now(timezone.utc).isoformat()
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
            "timestamp": datetime.now(timezone.utc).isoformat()
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
