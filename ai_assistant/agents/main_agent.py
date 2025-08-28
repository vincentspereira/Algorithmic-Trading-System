
import logging
from langchain.agents import create_react_agent, AgentExecutor
from langchain.memory import ConversationBufferWindowMemory
from langchain_openai import ChatOpenAI
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate

from ai_assistant.config import config
from ai_assistant.tools import run_backtest_tool, query_documents_tool, get_trading_system_status, code_development_tool

logger = logging.getLogger(__name__)

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
        llm = get_llm()
        tools = [run_backtest_tool, query_documents_tool, get_trading_system_status, code_development_tool]
        prompt = create_react_prompt()
        agent = create_react_agent(llm, tools, prompt)
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
