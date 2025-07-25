"""
Lobe Chat Adapter Service
Bridges Lobe Chat's expected OpenAI-compatible API format with our AI Assistant's ReAct agent.
"""

import os
import json
import uuid
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
import httpx
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AdapterConfig:
    """Configuration for the Lobe Chat adapter"""
    
    def __init__(self):
        self.ai_assistant_url = os.getenv("AI_ASSISTANT_URL", "http://localhost:8002")
        self.adapter_port = int(os.getenv("LOBE_ADAPTER_PORT", "8003"))
        self.adapter_host = os.getenv("LOBE_ADAPTER_HOST", "0.0.0.0")
        self.allowed_origins = os.getenv("LOBE_ALLOWED_ORIGINS", "http://localhost:3210,http://localhost:3000").split(",")
        self.debug_mode = os.getenv("DEBUG", "false").lower() == "true"


config = AdapterConfig()


# Pydantic models for OpenAI-compatible API
class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: system, user, or assistant")
    content: str = Field(..., description="Message content")
    name: Optional[str] = Field(None, description="Optional name for the message")


class ChatCompletionRequest(BaseModel):
    model: str = Field(..., description="Model identifier")
    messages: List[ChatMessage] = Field(..., description="List of messages")
    temperature: Optional[float] = Field(0.7, description="Sampling temperature")
    max_tokens: Optional[int] = Field(2000, description="Maximum tokens to generate")
    stream: Optional[bool] = Field(False, description="Whether to stream the response")
    user: Optional[str] = Field(None, description="User identifier")


class ChatCompletionChoice(BaseModel):
    index: int = Field(..., description="Choice index")
    message: ChatMessage = Field(..., description="Generated message")
    finish_reason: str = Field(..., description="Reason for finishing")


class ChatCompletionResponse(BaseModel):
    id: str = Field(..., description="Completion ID")
    object: str = Field("chat.completion", description="Object type")
    created: int = Field(..., description="Creation timestamp")
    model: str = Field(..., description="Model used")
    choices: List[ChatCompletionChoice] = Field(..., description="Generated choices")
    usage: Dict[str, int] = Field(..., description="Token usage information")


class ChatCompletionStreamChoice(BaseModel):
    index: int = Field(..., description="Choice index")
    delta: Dict[str, Any] = Field(..., description="Delta content")
    finish_reason: Optional[str] = Field(None, description="Reason for finishing")


class ChatCompletionStreamResponse(BaseModel):
    id: str = Field(..., description="Completion ID")
    object: str = Field("chat.completion.chunk", description="Object type")
    created: int = Field(..., description="Creation timestamp")
    model: str = Field(..., description="Model used")
    choices: List[ChatCompletionStreamChoice] = Field(..., description="Stream choices")


# Initialize FastAPI app
app = FastAPI(
    title="Lobe Chat Adapter",
    description="OpenAI-compatible API adapter for Lobe Chat integration with AI Assistant",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


async def call_ai_assistant(message: str, session_id: str) -> Dict[str, Any]:
    """Call the AI Assistant service"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{config.ai_assistant_url}/api/v1/chat",
                json={
                    "message": message,
                    "session_id": session_id
                }
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Error calling AI Assistant: {e}")
        raise HTTPException(status_code=503, detail="AI Assistant service unavailable")
    except httpx.HTTPStatusError as e:
        logger.error(f"AI Assistant returned error: {e.response.status_code}")
        raise HTTPException(status_code=e.response.status_code, detail="AI Assistant error")


def extract_user_message(messages: List[ChatMessage]) -> str:
    """Extract the latest user message from the conversation"""
    for message in reversed(messages):
        if message.role == "user":
            return message.content
    return "Hello"


def format_response_with_reasoning(ai_response: Dict[str, Any]) -> str:
    """Format the AI response to include reasoning traces if available"""
    response_text = ai_response.get("response", "")
    reasoning = ai_response.get("reasoning", [])
    tools_used = ai_response.get("tools_used", [])
    
    if reasoning or tools_used:
        formatted_response = response_text + "\n\n---\n\n"
        
        if tools_used:
            formatted_response += f"🔧 **Tools Used**: {', '.join(tools_used)}\n\n"
        
        if reasoning:
            formatted_response += "🧠 **Reasoning Process**:\n\n"
            for i, step in enumerate(reasoning, 1):
                if step.get("thought"):
                    formatted_response += f"**Step {i} - Thought**: {step['thought']}\n\n"
                if step.get("action"):
                    formatted_response += f"**Action**: {step['action']}\n"
                    if step.get("action_input"):
                        formatted_response += f"**Input**: {step['action_input']}\n"
                if step.get("observation"):
                    formatted_response += f"**Result**: {step['observation']}\n\n"
        
        return formatted_response
    
    return response_text


async def stream_response(ai_response: Dict[str, Any], completion_id: str, model: str) -> AsyncGenerator[str, None]:
    """Stream the response in OpenAI format"""
    response_text = format_response_with_reasoning(ai_response)
    created = int(datetime.utcnow().timestamp())
    
    # Split response into chunks for streaming effect
    words = response_text.split()
    chunk_size = 3  # Words per chunk
    
    for i in range(0, len(words), chunk_size):
        chunk_words = words[i:i + chunk_size]
        chunk_content = " ".join(chunk_words)
        
        if i > 0:  # Add space before chunk (except first)
            chunk_content = " " + chunk_content
        
        stream_chunk = ChatCompletionStreamResponse(
            id=completion_id,
            created=created,
            model=model,
            choices=[
                ChatCompletionStreamChoice(
                    index=0,
                    delta={"content": chunk_content},
                    finish_reason=None
                )
            ]
        )
        
        yield f"data: {stream_chunk.model_dump_json()}\n\n"
        await asyncio.sleep(0.05)  # Small delay for streaming effect
    
    # Send final chunk
    final_chunk = ChatCompletionStreamResponse(
        id=completion_id,
        created=created,
        model=model,
        choices=[
            ChatCompletionStreamChoice(
                index=0,
                delta={},
                finish_reason="stop"
            )
        ]
    )
    
    yield f"data: {final_chunk.model_dump_json()}\n\n"
    yield "data: [DONE]\n\n"


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{config.ai_assistant_url}/health")
            ai_assistant_healthy = response.status_code == 200
    except:
        ai_assistant_healthy = False
    
    return {
        "status": "healthy",
        "ai_assistant_connection": ai_assistant_healthy,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI-compatible)"""
    return {
        "object": "list",
        "data": [
            {
                "id": "trading-assistant",
                "object": "model",
                "created": int(datetime.utcnow().timestamp()),
                "owned_by": "algorithmic-trading-system",
                "permission": [],
                "root": "trading-assistant",
                "parent": None
            }
        ]
    }


@app.post("/v1/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest):
    """Create a chat completion (OpenAI-compatible)"""
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    created = int(datetime.utcnow().timestamp())
    
    # Extract user message
    user_message = extract_user_message(request.messages)
    
    # Generate session ID from user identifier or create new one
    session_id = request.user or str(uuid.uuid4())
    
    logger.info(f"Processing chat completion request: {user_message[:100]}...")
    
    # Call AI Assistant
    ai_response = await call_ai_assistant(user_message, session_id)
    
    if request.stream:
        # Return streaming response
        return StreamingResponse(
            stream_response(ai_response, completion_id, request.model),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/plain; charset=utf-8"
            }
        )
    else:
        # Return complete response
        response_text = format_response_with_reasoning(ai_response)
        
        return ChatCompletionResponse(
            id=completion_id,
            created=created,
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content=response_text
                    ),
                    finish_reason="stop"
                )
            ],
            usage={
                "prompt_tokens": len(user_message.split()),
                "completion_tokens": len(response_text.split()),
                "total_tokens": len(user_message.split()) + len(response_text.split())
            }
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "type": "http_error",
                "code": exc.status_code
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "Internal server error",
                "type": "internal_error",
                "code": 500
            }
        }
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Lobe Chat Adapter for Algorithmic Trading AI Assistant",
        "version": "1.0.0",
        "ai_assistant_url": config.ai_assistant_url,
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    uvicorn.run(
        "lobe_chat_adapter:app",
        host=config.adapter_host,
        port=config.adapter_port,
        reload=config.debug_mode,
        log_level="info"
    )