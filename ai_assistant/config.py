
import os
import json
import logging
from typing import Dict

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
        
        # MCP Configuration
        self.enable_sequential_thinking = False
        self.max_file_size = 1048576 # Default 1MB

        self._load_mcp_config()

    def _load_mcp_config(self):
        mcp_config_name = os.getenv("MCP_CONFIG")
        if mcp_config_name:
            config_path = os.path.join(os.path.dirname(__file__), f"{mcp_config_name}.json")
            if os.path.exists(config_path):
                logger.info(f"Loading MCP configuration from {config_path}")
                with open(config_path, 'r') as f:
                    mcp_config = json.load(f)
                    for key, value in mcp_config.items():
                        if hasattr(self, key):
                            setattr(self, key, value)
                        else:
                            logger.warning(f"Unknown configuration key in {mcp_config_name}.json: {key}")
            else:
                logger.warning(f"MCP configuration file not found: {config_path}")

    def get_phase2_headers(self) -> Dict[str, str]:
        """Get headers for Phase 2 API requests"""
        headers = {"Content-Type": "application/json"}
        if self.phase2_api_key:
            headers["Authorization"] = f"Bearer {self.phase2_api_key}"
        return headers

config = AppConfig()
