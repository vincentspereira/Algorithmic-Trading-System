from typing import Dict

from shared.config import settings

class AppConfig:
    """Configuration class for managing application settings"""

    def __init__(self):
        # Phase 2 API Configuration
        self.phase2_api_base_url = settings.PHASE2_API_BASE_URL
        self.phase2_api_key = settings.PHASE2_API_KEY

        # AI Assistant Configuration
        self.openai_api_key = settings.OPENAI_API_KEY
        self.ollama_base_url = settings.OLLAMA_BASE_URL
        self.langchain_api_key = settings.LANGCHAIN_API_KEY

        # LLM Configuration
        self.llm_provider = settings.LLM_PROVIDER.lower()
        self.openai_model = settings.OPENAI_MODEL
        self.ollama_model = settings.OLLAMA_MODEL
        self.max_tokens = settings.MAX_TOKENS
        self.temperature = settings.TEMPERATURE

        # Memory Configuration
        self.memory_window_size = settings.MEMORY_WINDOW_SIZE
        self.max_iterations = settings.MAX_ITERATIONS
        self.max_execution_time = settings.MAX_EXECUTION_TIME

        # Service Configuration
        self.service_port = settings.AI_ASSISTANT_PORT
        self.service_host = settings.AI_ASSISTANT_HOST
        self.debug_mode = settings.DEBUG_MODE

        # CORS Configuration
        self.allowed_origins = settings.ALLOWED_ORIGINS.split(",")

    def get_phase2_headers(self) -> Dict[str, str]:
        """Get headers for Phase 2 API requests"""
        headers = {"Content-Type": "application/json"}
        if self.phase2_api_key:
            headers["Authorization"] = f"Bearer {self.phase2_api_key}"
        return headers

config = AppConfig()