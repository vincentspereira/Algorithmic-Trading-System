#!/usr/bin/env python3
"""
Simple test script to verify ReAct agent implementation
"""

import sys
import os
import logging
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all required imports work"""
    try:
        logger.info("Testing imports...")
        
        # Test LangChain imports
        from langchain.agents import create_react_agent, AgentExecutor
        from langchain.memory import ConversationBufferWindowMemory
        from langchain.prompts import PromptTemplate
        logger.info("✅ LangChain imports successful")
        
        # Test tools import
        from tools import run_backtest_tool, query_documents_tool, get_trading_system_status
        logger.info("✅ Tools import successful")
        
        # Test main app components
        from main import AppConfig, get_llm, create_react_prompt, initialize_agent
        logger.info("✅ Main app components import successful")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error during imports: {e}")
        return False

def test_config():
    """Test configuration initialization"""
    try:
        logger.info("Testing configuration...")
        
        from main import AppConfig
        config = AppConfig()
        
        # Check required attributes
        required_attrs = [
            'llm_provider', 'openai_model', 'ollama_model',
            'max_tokens', 'temperature', 'memory_window_size',
            'max_iterations', 'max_execution_time'
        ]
        
        for attr in required_attrs:
            if not hasattr(config, attr):
                logger.error(f"❌ Missing config attribute: {attr}")
                return False
        
        logger.info(f"✅ Configuration initialized successfully")
        logger.info(f"   LLM Provider: {config.llm_provider}")
        logger.info(f"   OpenAI Model: {config.openai_model}")
        logger.info(f"   Ollama Model: {config.ollama_model}")
        logger.info(f"   Max Tokens: {config.max_tokens}")
        logger.info(f"   Temperature: {config.temperature}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Configuration test failed: {e}")
        return False

def test_prompt_creation():
    """Test ReAct prompt creation"""
    try:
        logger.info("Testing prompt creation...")
        
        from main import create_react_prompt
        prompt = create_react_prompt()
        
        if not hasattr(prompt, 'template'):
            logger.error("❌ Prompt missing template attribute")
            return False
        
        # Check if template contains required placeholders
        required_placeholders = ['{tools}', '{tool_names}', '{input}', '{chat_history}', '{agent_scratchpad}']
        for placeholder in required_placeholders:
            if placeholder not in prompt.template:
                logger.error(f"❌ Prompt missing placeholder: {placeholder}")
                return False
        
        logger.info("✅ ReAct prompt created successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Prompt creation test failed: {e}")
        return False

def test_tools():
    """Test that tools are properly defined"""
    try:
        logger.info("Testing tools...")
        
        from tools import run_backtest_tool, query_documents_tool, get_trading_system_status
        
        tools = [run_backtest_tool, query_documents_tool, get_trading_system_status]
        
        for tool in tools:
            if not hasattr(tool, 'name'):
                logger.error(f"❌ Tool missing name attribute: {tool}")
                return False
            if not hasattr(tool, 'description'):
                logger.error(f"❌ Tool missing description attribute: {tool}")
                return False
            logger.info(f"   ✅ Tool '{tool.name}' is properly defined")
        
        logger.info("✅ All tools are properly defined")
        return True
        
    except Exception as e:
        logger.error(f"❌ Tools test failed: {e}")
        return False

def test_memory():
    """Test memory system"""
    try:
        logger.info("Testing memory system...")
        
        from main import get_or_create_memory
        
        # Test memory creation
        session_id = "test_session_123"
        memory = get_or_create_memory(session_id)
        
        if not hasattr(memory, 'chat_memory'):
            logger.error("❌ Memory missing chat_memory attribute")
            return False
        
        # Test memory persistence
        memory2 = get_or_create_memory(session_id)
        if memory is not memory2:
            logger.error("❌ Memory not persisting for same session")
            return False
        
        logger.info("✅ Memory system working correctly")
        return True
        
    except Exception as e:
        logger.error(f"❌ Memory test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("=" * 50)
    logger.info("ReAct Agent Implementation Test Suite")
    logger.info("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Prompt Creation", test_prompt_creation),
        ("Tools", test_tools),
        ("Memory System", test_memory)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n🧪 Running {test_name} test...")
        try:
            if test_func():
                passed += 1
                logger.info(f"✅ {test_name} test PASSED")
            else:
                logger.error(f"❌ {test_name} test FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} test FAILED with exception: {e}")
    
    logger.info("\n" + "=" * 50)
    logger.info(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests PASSED! ReAct agent implementation is ready.")
        return True
    else:
        logger.error(f"❌ {total - passed} tests FAILED. Please review the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)