
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_CONSUMER_GROUP_ID: str = "backtest_service"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_POOL_SIZE: int = 50
    CACHE_EXP_PREDICTIONS: int = 60
    CACHE_EXP_RISK: int = 300
    CACHE_EXP_MARKET_DATA: int = 10

    # ClickHouse
    CLICKHOUSE_HOST: str = "localhost"

    # DuckDB
    DUCKDB_DATABASE_PATH: str = "/app/data/duckdb/trading_research.duckdb"

    # FIX Protocol
    FIX_CONNECTION_TYPE: str = "initiator"
    FIX_RECONNECT_INTERVAL: int = 60
    FIX_FILE_STORE_PATH: str = "/var/lib/quickfixj/client"
    FIX_FILE_LOG_PATH: str = "/var/lib/quickfixj/logs/client"
    FIX_START_TIME: str = "00:00:00"
    FIX_END_TIME: str = "00:00:00"
    FIX_HEART_BT_INT: int = 30
    FIX_CHECK_LATENCY: str = "Y"
    FIX_VALIDATION: str = "Y"
    FIX_BEGIN_STRING: str = "FIX.4.4"
    FIX_DEFAULT_APPL_VER_ID: str = "FIX.4.4"
    FIX_TARGET_COMP_ID: str = "SERVER"
    FIX_SENDER_COMP_ID: str = "CLIENT1"
    FIX_SOCKET_CONNECT_HOST: str = "fix-gateway"
    FIX_SOCKET_CONNECT_PORT: int = 9876

    # Interactive Brokers
    IB_HOST: str = "127.0.0.1"
    IB_PAPER_PORT: int = 4002
    IB_PAPER_CLIENT_ID: int = 1
    IB_PAPER_ACCOUNT: str = "DU1234567"
    IB_LIVE_PORT: int = 4001
    IB_LIVE_CLIENT_ID: int = 1
    IB_LIVE_ACCOUNT: str = "U1234567"

    # AI Assistant
    PHASE2_API_BASE_URL: str = "http://localhost:8001"
    PHASE2_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LANGCHAIN_API_KEY: str = ""
    LLM_PROVIDER: str = "openai"
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    OLLAMA_MODEL: str = "llama2"
    MAX_TOKENS: int = 2000
    TEMPERATURE: float = 0.7
    MEMORY_WINDOW_SIZE: int = 10
    MAX_ITERATIONS: int = 15
    MAX_EXECUTION_TIME: int = 60
    AI_ASSISTANT_PORT: int = 8002
    AI_ASSISTANT_HOST: str = "0.0.0.0"
    DEBUG_MODE: bool = False
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8080,http://localhost:3210"

    # Backtest Service
    BACKTEST_SERVICE_HOST: str = "0.0.0.0"
    BACKTEST_SERVICE_PORT: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
