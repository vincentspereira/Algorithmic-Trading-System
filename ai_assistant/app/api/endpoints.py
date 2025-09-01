
import uuid
from datetime import datetime
import logging

from fastapi import APIRouter, HTTPException
import requests

from app.schemas.models import HealthResponse, InfoResponse, ChatRequest, ChatResponse
from ai_assistant.config import config
from app.agents.main_agent import initialize_agent, get_or_create_memory, agent_executor

logger = logging.getLogger(__name__)

router = APIRouter()

# Health check endpoint
@router.get("/health", response_model=HealthResponse, tags=["Health"])
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
@router.get("/v1/info", response_model=InfoResponse, tags=["Information"])
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
@router.post("/v1/chat", response_model=ChatResponse, tags=["AI Chat"])
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
    session_id = request.session_id or str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()

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
        memory = get_or_create_memory(session_id)
        agent_input = {
            "input": request.message,
            "chat_history": memory.chat_memory.messages if memory.chat_memory.messages else []
        }

        if request.context:
            context_str = f"Additional context: {request.context}"
            agent_input["input"] = f"{context_str}\n\nUser message: {request.message}"

        logger.info(f"Processing chat request for session {session_id}: {request.message}")
        result = agent_executor.invoke(agent_input)
        response_text = result.get("output", "I apologize, but I couldn't generate a proper response.")
        intermediate_steps = result.get("intermediate_steps", [])

        reasoning = []
        tools_used = []

        for step in intermediate_steps:
            if len(step) >= 2:
                action, observation = step[0], step[1]
                tool_name = getattr(action, 'tool', 'unknown')
                if tool_name not in tools_used:
                    tools_used.append(tool_name)

                reasoning_step = {
                    "thought": getattr(action, 'log', ''),
                    "action": tool_name,
                    "action_input": getattr(action, 'tool_input', ''),
                    "observation": str(observation)[:500] + "..." if len(str(observation)) > 500 else str(observation)
                }
                reasoning.append(reasoning_step)

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
@router.get("/v1/phase2/status", tags=["Phase 2 Integration"])
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
