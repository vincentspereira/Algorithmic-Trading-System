"""
AI Assistant Service for Algorithmic Trading System - Phase 3
FastAPI backend service that will integrate with Phase 2 API endpoints
and serve as the backend for the AI assistant functionality.
"""

import os
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv
import requests
import logging

# LangChain imports for ReAct agent
from langchain.agents import create_react_agent, AgentExecutor
from langchain.memory import ConversationBufferWindowMemory
from langchain_openai import ChatOpenAI
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.schema import BaseMessage, HumanMessage, AIMessage

# Import tools from tools.py
from tools import run_backtest_tool, query_documents_tool, get_trading_system_status, code_development_tool

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
        
        # LLM Configuration
        self.llm_provider = os.getenv("LLM_PROVIDER", "openai").lower()  # "openai" or "ollama"
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama2")
        self.max_tokens = int(os.getenv("MAX_TOKENS", "2000"))
        self.temperature = float(os.getenv("TEMPERATURE", "0.7"))
        
        # Memory Configuration
        self.memory_window_size = int(os.getenv("MEMORY_WINDOW_SIZE", "10"))
        self.max_iterations = int(os.getenv("MAX_ITERATIONS", "15"))
        self.max_execution_time = int(os.getenv("MAX_EXECUTION_TIME", "60"))
        
        # Service Configuration
        self.service_port = int(os.getenv("AI_ASSISTANT_PORT", "8002"))
        self.service_host = os.getenv("AI_ASSISTANT_HOST", "0.0.0.0")
        self.debug_mode = os.getenv("DEBUG", "false").lower() == "true"
        
        # CORS Configuration
        self.allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080,http://localhost:3210").split(",")
        
    def get_phase2_headers(self) -> Dict[str, str]:
        """Get headers for Phase 2 API requests"""
        headers = {"Content-Type": "application/json"}
        if self.phase2_api_key:
            headers["Authorization"] = f"Bearer {self.phase2_api_key}"
        return headers


# Initialize configuration
config = AppConfig()


# Global variables for agent and memory
agent_executor = None
session_memories = {}


def get_llm():
    """Initialize and return the appropriate LLM based on configuration"""
    try:
        if config.llm_provider == "openai":
            if not config.openai_api_key:
                raise ValueError("OpenAI API key not provided")
            return ChatOpenAI(
                model=config.openai_model,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                openai_api_key=config.openai_api_key
            )
        elif config.llm_provider == "ollama":
            return Ollama(
                base_url=config.ollama_base_url,
                model=config.ollama_model,
                temperature=config.temperature
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {config.llm_provider}")
    except Exception as e:
        logger.error(f"Error initializing LLM: {e}")
        raise


def create_react_prompt():
    """Create the ReAct prompt template for the trading assistant"""
    template = """You are an AI assistant specialized in algorithmic trading and financial analysis. You have access to tools that can help you run backtests, query trading documents, and check system status.

Your role is to:
1. Help users understand trading strategies and concepts
2. Run backtests using the available trading system
3. Provide insights on trading performance and risk management
4. Answer questions about algorithmic trading using relevant documents
5. Assist with trading system operations
6. Develop and modify code using OpenHands-powered development capabilities

You should always think step by step and use the available tools when appropriate. Be precise, informative, and focus on providing actionable trading insights.

TOOLS:
{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Previous conversation:
{chat_history}

Question: {input}
{agent_scratchpad}"""

    return PromptTemplate(
        template=template,
        input_variables=["input", "chat_history", "agent_scratchpad", "tools", "tool_names"]
    )


def initialize_agent():
    """Initialize the ReAct agent with tools and memory"""
    global agent_executor
    
    try:
        # Get LLM
        llm = get_llm()
        
        # Define tools
        tools = [run_backtest_tool, query_documents_tool, get_trading_system_status, code_development_tool]
        
        # Create prompt
        prompt = create_react_prompt()
        
        # Create ReAct agent
        agent = create_react_agent(llm, tools, prompt)
        
        # Create agent executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=config.debug_mode,
            max_iterations=config.max_iterations,
            max_execution_time=config.max_execution_time,
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )
        
        logger.info(f"ReAct agent initialized successfully with {config.llm_provider} LLM")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize ReAct agent: {e}")
        return False


def get_or_create_memory(session_id: str) -> ConversationBufferWindowMemory:
    """Get or create memory for a session"""
    if session_id not in session_memories:
        session_memories[session_id] = ConversationBufferWindowMemory(
            k=config.memory_window_size,
            return_messages=True,
            memory_key="chat_history"
        )
    return session_memories[session_id]


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
    # Clear session memories
    global session_memories
    session_memories.clear()


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
    """Chat response model for AI interactions"""
    response: str = Field(..., description="AI assistant response")
    session_id: str = Field(..., description="Session ID")
    timestamp: str = Field(..., description="Response timestamp")
    reasoning: Optional[List[Dict[str, Any]]] = Field(None, description="Agent's reasoning process (intermediate steps)")
    tools_used: Optional[List[str]] = Field(None, description="List of tools that were invoked")


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
            "ReAct (Reasoning and Acting) agent framework",
            "LangChain integration with tool usage",
            "OpenAI GPT and local LLM support (Ollama)",
            "Conversational memory with session management",
            "Natural language backtesting via Phase 2 API",
            "Trading document query and search",
            "System status monitoring and diagnostics",
            "Reasoning trace transparency",
            "Multi-tool orchestration for complex queries",
            "OpenHands-powered code development and modification",
            "AI-assisted endpoint creation and feature implementation",
            "Automated code generation with safety checks and rollback"
        ]
    )


# ReAct Agent Chat endpoint
@app.post("/api/v1/chat", response_model=ChatResponse, tags=["AI Chat"])
async def chat_with_assistant(request: ChatRequest):
    """
    Chat with the AI assistant using ReAct (Reasoning and Acting) framework.
    
    The agent can:
    - Run backtests using natural language queries
    - Query trading documents and research
    - Check trading system status
    - Provide trading insights and analysis
    
    The agent uses reasoning traces to show its thought process and tool usage.
    """
    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    
    # Check if agent is initialized
    if agent_executor is None:
        logger.error("ReAct agent not initialized")
        return ChatResponse(
            response="❌ AI Assistant is currently unavailable. The ReAct agent failed to initialize. Please check the configuration and try again later.",
            session_id=session_id,
            timestamp=timestamp,
            reasoning=None,
            tools_used=None
        )
    
    try:
        # Get or create memory for this session
        memory = get_or_create_memory(session_id)
        
        # Prepare input for the agent
        agent_input = {
            "input": request.message,
            "chat_history": memory.chat_memory.messages if memory.chat_memory.messages else []
        }
        
        # Add context if provided
        if request.context:
            context_str = f"Additional context: {request.context}"
            agent_input["input"] = f"{context_str}\n\nUser message: {request.message}"
        
        logger.info(f"Processing chat request for session {session_id}: {request.message}")
        
        # Execute the agent
        result = agent_executor.invoke(agent_input)
        
        # Extract response and intermediate steps
        response_text = result.get("output", "I apologize, but I couldn't generate a proper response.")
        intermediate_steps = result.get("intermediate_steps", [])
        
        # Process reasoning traces
        reasoning = []
        tools_used = []
        
        for step in intermediate_steps:
            if len(step) >= 2:
                action, observation = step[0], step[1]
                
                # Extract tool name
                tool_name = getattr(action, 'tool', 'unknown')
                if tool_name not in tools_used:
                    tools_used.append(tool_name)
                
                # Format reasoning step
                reasoning_step = {
                    "thought": getattr(action, 'log', ''),
                    "action": tool_name,
                    "action_input": getattr(action, 'tool_input', ''),
                    "observation": str(observation)[:500] + "..." if len(str(observation)) > 500 else str(observation)
                }
                reasoning.append(reasoning_step)
        
        # Update memory with the conversation
        memory.chat_memory.add_user_message(request.message)
        memory.chat_memory.add_ai_message(response_text)
        
        logger.info(f"Successfully processed chat request for session {session_id}")
        
        return ChatResponse(
            response=response_text,
            session_id=session_id,
            timestamp=timestamp,
            reasoning=reasoning if reasoning else None,
            tools_used=tools_used if tools_used else None
        )
        
    except Exception as e:
        error_msg = f"Error processing chat request: {str(e)}"
        logger.error(f"Chat error for session {session_id}: {error_msg}")
        
        # Determine if it's an LLM API error
        if "openai" in str(e).lower() or "api" in str(e).lower():
            response_text = "❌ I'm experiencing issues connecting to the AI service. Please check your API configuration and try again."
        elif "timeout" in str(e).lower():
            response_text = "⏱️ The request timed out. Please try a simpler query or check the system status."
        else:
            response_text = f"❌ I encountered an error while processing your request: {str(e)}"
        
        return ChatResponse(
            response=response_text,
            session_id=session_id,
            timestamp=timestamp,
            reasoning=[{"error": error_msg}],
            tools_used=None
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