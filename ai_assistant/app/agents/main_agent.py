
from typing import Dict, Any

from langchain.agents import AgentExecutor, create_react_agent
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import PromptTemplate
from langchain_openai import OpenAI
from langchain_community.llms import Ollama

from ai_assistant.config import config

# Global agent executor instance
agent_executor: AgentExecutor = None

# Memory store for conversations
memory_store: Dict[str, ConversationBufferMemory] = {}

def initialize_agent() -> bool:
    """Initializes the ReAct agent with configured LLM and tools."""
    global agent_executor

    # Choose LLM provider
    if config.llm_provider == "openai":
        llm = OpenAI(openai_api_key=config.openai_api_key, temperature=config.temperature)
    elif config.llm_provider == "ollama":
        llm = Ollama(base_url=config.ollama_base_url, model=config.ollama_model, temperature=config.temperature)
    else:
        raise ValueError(f"Unsupported LLM provider: {config.llm_provider}")

    # Define tools (placeholder for actual tools)
    tools = [] # TODO: Add actual tools here

    # Define the prompt template for the ReAct agent
    template = """Answer the following questions as best you can. You have access to the following tools:

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

Begin!

Question: {input}
Thought:{agent_scratchpad}"""
    prompt = PromptTemplate.from_template(template)

    # Create the ReAct agent
    agent = create_react_agent(llm, tools, prompt)

    # Create the agent executor
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    return True

def get_or_create_memory(session_id: str) -> ConversationBufferMemory:
    """Retrieves or creates a conversation memory for a given session ID."""
    if session_id not in memory_store:
        memory_store[session_id] = ConversationBufferMemory(return_messages=True, memory_key="chat_history")
    return memory_store[session_id]
