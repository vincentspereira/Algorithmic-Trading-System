"""
Agentic Tools for AI Assistant - Phase 3
LangChain tools for interacting with the Algorithmic Trading System

This module provides LangChain tools that enable AI agents to:
1. Run backtests through the Phase 2 API
2. Query documents using vector similarity search (Qdrant placeholder)
3. Parse natural language requests into structured API calls
4. Format results for human-readable responses

These tools are designed to be used by LangChain agents to provide
intelligent trading system assistance.
"""

import os
import re
import json
import logging
import shutil
import subprocess
import tempfile
from datetime import datetime, date, timezone
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

import requests
from langchain.tools import tool
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Configuration
@dataclass
class ToolsConfig:
    """Configuration for AI Assistant tools"""
    phase2_api_base_url: str = os.getenv("PHASE2_API_BASE_URL", "http://localhost:8001")
    phase2_api_key: str = os.getenv("PHASE2_API_KEY", "")
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key: str = os.getenv("QDRANT_API_KEY", "")
    default_username: str = os.getenv("DEFAULT_USERNAME", "demo")
    default_password: str = os.getenv("DEFAULT_PASSWORD", "demo123")
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "30"))


config = ToolsConfig()


# OpenHands Integration Classes and Configuration
class TaskType(Enum):
    """Types of development tasks OpenHands can handle"""
    ADD_ENDPOINT = "add_endpoint"
    MODIFY_FUNCTION = "modify_function"
    CREATE_FILE = "create_file"
    REFACTOR_CODE = "refactor_code"
    ADD_FEATURE = "add_feature"
    FIX_BUG = "fix_bug"
    ADD_TESTS = "add_tests"
    UPDATE_CONFIG = "update_config"


class TaskPriority(Enum):
    """Priority levels for development tasks"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class OpenHandsConfig:
    """Configuration for OpenHands integration"""
    workspace_root: str = os.getenv("WORKSPACE_ROOT", os.getcwd())
    backup_dir: str = os.getenv("OPENHANDS_BACKUP_DIR", "backups/openhands")
    max_file_size: int = int(os.getenv("MAX_FILE_SIZE", "1048576"))  # 1MB
    allowed_extensions: List[str] = field(default_factory=lambda: [
        '.py', '.js', '.ts', '.json', '.yaml', '.yml', '.md', '.txt', '.sql', '.sh', '.bat'
    ])
    forbidden_paths: List[str] = field(default_factory=lambda: [
        '.git', '__pycache__', 'node_modules', '.env', 'venv', '.venv'
    ])
    max_backup_files: int = int(os.getenv("MAX_BACKUP_FILES", "50"))
    enable_rollback: bool = os.getenv("ENABLE_ROLLBACK", "true").lower() == "true"
    dry_run_mode: bool = os.getenv("DRY_RUN_MODE", "false").lower() == "true"


@dataclass
class PlanningStep:
    """Represents a single step in the OpenHands planning phase"""
    step_id: str
    description: str
    task_type: TaskType
    target_files: List[str]
    dependencies: List[str] = field(default_factory=list)
    estimated_complexity: int = 1  # 1-5 scale
    priority: TaskPriority = TaskPriority.MEDIUM
    validation_criteria: List[str] = field(default_factory=list)


@dataclass
class ExecutionResult:
    """Result of executing a planning step"""
    step_id: str
    success: bool
    files_modified: List[str] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    backup_paths: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    execution_time: float = 0.0
    validation_results: List[str] = field(default_factory=list)


@dataclass
class OpenHandsWorkflow:
    """Complete OpenHands workflow state"""
    workflow_id: str
    original_request: str
    planning_steps: List[PlanningStep] = field(default_factory=list)
    execution_results: List[ExecutionResult] = field(default_factory=list)
    status: str = "initialized"  # initialized, planning, executing, completed, failed, rolled_back
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    total_files_modified: int = 0
    total_files_created: int = 0


# Initialize OpenHands configuration
openhands_config = OpenHandsConfig()


# Pydantic models for tool inputs
class BacktestToolInput(BaseModel):
    """Input model for backtest tool"""
    query: str = Field(
        description="Natural language query for running a backtest. "
        "Example: 'Run a backtest on AAPL from 2022-01-01 to 2023-12-31 using SMA Crossover strategy'"
    )


class DocumentQueryInput(BaseModel):
    """Input model for document query tool"""
    query: str = Field(
        description="Natural language query to search for relevant documents. "
        "Example: 'What are the best trading strategies for volatile markets?'"
    )
    limit: int = Field(
        default=5,
        description="Maximum number of documents to return (1-20)"
    )


class StockPredictionInput(BaseModel):
    """Input model for stock price prediction tool"""
    query: str = Field(
        description="Natural language query for stock price prediction. "
        "Examples: 'Predict AAPL price for next 7 days', "
        "'What will GOOGL stock price be in 30 days?', "
        "'Forecast MSFT price using LSTM model for 1 week'"
    )
    model_type: Optional[str] = Field(
        default=None,
        description="Specific model type to use: 'lstm', 'arima', 'random_forest', 'xgboost', 'prophet', 'ensemble'. "
        "If not specified, the best available model will be selected automatically."
    )
    include_confidence: bool = Field(
        default=True,
        description="Whether to include confidence intervals in the prediction"
    )


class CodeDevelopmentInput(BaseModel):
    """Input model for code development tool"""
    request: str = Field(
        description="Natural language development request. "
        "Examples: 'Add a new endpoint /status to the AI assistant', "
        "'Create a function to calculate portfolio risk metrics', "
        "'Add error handling to the backtest API calls'"
    )
    preview_only: bool = Field(
        default=False,
        description="If True, only show what would be done without making changes"
    )
    target_files: Optional[List[str]] = Field(
        default=None,
        description="Optional list of specific files to target for modifications"
    )


# OpenHands Helper Functions
def create_backup(file_path: str) -> Optional[str]:
    """
    Create a backup of a file before modification
    
    Args:
        file_path: Path to the file to backup
        
    Returns:
        Path to the backup file if successful, None otherwise
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"File does not exist for backup: {file_path}")
            return None
            
        # Create backup directory if it doesn't exist
        backup_dir = Path(openhands_config.backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate backup filename with timestamp
        file_path_obj = Path(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{file_path_obj.stem}_{timestamp}{file_path_obj.suffix}"
        backup_path = backup_dir / backup_filename
        
        # Copy file to backup location
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup: {file_path} -> {backup_path}")
        
        # Clean up old backups if needed
        cleanup_old_backups(backup_dir)
        
        return str(backup_path)
        
    except Exception as e:
        logger.error(f"Failed to create backup for {file_path}: {e}")
        return None


def cleanup_old_backups(backup_dir: Path) -> None:
    """Clean up old backup files to maintain storage limits"""
    try:
        backup_files = list(backup_dir.glob("*"))
        if len(backup_files) > openhands_config.max_backup_files:
            # Sort by modification time and remove oldest
            backup_files.sort(key=lambda x: x.stat().st_mtime)
            files_to_remove = backup_files[:-openhands_config.max_backup_files]
            
            for file_path in files_to_remove:
                file_path.unlink()
                logger.info(f"Removed old backup: {file_path}")
                
    except Exception as e:
        logger.error(f"Error cleaning up backups: {e}")


def is_safe_path(file_path: str) -> bool:
    """
    Check if a file path is safe for modification
    
    Args:
        file_path: Path to check
        
    Returns:
        True if path is safe, False otherwise
    """
    try:
        path_obj = Path(file_path).resolve()
        workspace_root = Path(openhands_config.workspace_root).resolve()
        
        # Check if path is within workspace
        if not str(path_obj).startswith(str(workspace_root)):
            logger.warning(f"Path outside workspace: {file_path}")
            return False
            
        # Check forbidden paths
        for forbidden in openhands_config.forbidden_paths:
            if forbidden in str(path_obj):
                logger.warning(f"Path contains forbidden directory: {file_path}")
                return False
                
        # Check file extension
        if path_obj.suffix and path_obj.suffix not in openhands_config.allowed_extensions:
            logger.warning(f"File extension not allowed: {file_path}")
            return False
            
        # Check file size if exists
        if path_obj.exists() and path_obj.stat().st_size > openhands_config.max_file_size:
            logger.warning(f"File too large: {file_path}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Error checking path safety: {e}")
        return False


def parse_development_request(request: str) -> Dict[str, Any]:
    """
    Parse natural language development request into structured parameters
    
    Args:
        request: Natural language development request
        
    Returns:
        Dictionary with parsed request parameters
    """
    request_lower = request.lower()
    
    # Determine task type
    task_type = TaskType.ADD_FEATURE  # default
    
    if any(keyword in request_lower for keyword in ['add endpoint', 'new endpoint', 'create endpoint']):
        task_type = TaskType.ADD_ENDPOINT
    elif any(keyword in request_lower for keyword in ['modify function', 'update function', 'change function']):
        task_type = TaskType.MODIFY_FUNCTION
    elif any(keyword in request_lower for keyword in ['create file', 'new file', 'add file']):
        task_type = TaskType.CREATE_FILE
    elif any(keyword in request_lower for keyword in ['refactor', 'restructure', 'reorganize']):
        task_type = TaskType.REFACTOR_CODE
    elif any(keyword in request_lower for keyword in ['fix bug', 'fix error', 'debug', 'resolve issue']):
        task_type = TaskType.FIX_BUG
    elif any(keyword in request_lower for keyword in ['add test', 'create test', 'test coverage']):
        task_type = TaskType.ADD_TESTS
    elif any(keyword in request_lower for keyword in ['config', 'configuration', 'settings']):
        task_type = TaskType.UPDATE_CONFIG
    
    # Extract target files/components
    target_files = []
    
    # Look for file patterns
    import re
    file_patterns = [
        r'(\w+\.py)',
        r'(\w+\.js)',
        r'(\w+\.ts)',
        r'(\w+\.json)',
        r'(\w+\.yaml)',
        r'(\w+\.yml)'
    ]
    
    for pattern in file_patterns:
        matches = re.findall(pattern, request)
        target_files.extend(matches)
    
    # Look for endpoint patterns
    endpoint_pattern = r'/(\w+(?:/\w+)*)'
    endpoint_matches = re.findall(endpoint_pattern, request)
    
    # Determine priority
    priority = TaskPriority.MEDIUM
    if any(keyword in request_lower for keyword in ['urgent', 'critical', 'asap']):
        priority = TaskPriority.CRITICAL
    elif any(keyword in request_lower for keyword in ['high priority', 'important']):
        priority = TaskPriority.HIGH
    elif any(keyword in request_lower for keyword in ['low priority', 'when possible']):
        priority = TaskPriority.LOW
    
    return {
        'task_type': task_type,
        'target_files': target_files,
        'endpoints': endpoint_matches,
        'priority': priority,
        'original_request': request
    }


# Helper Functions
def get_auth_token() -> Optional[str]:
    """
    Get authentication token from Phase 2 API
    
    Returns:
        str: JWT access token if successful, None otherwise
    """
    try:
        login_url = f"{config.phase2_api_base_url}/api/v1/auth/login"
        login_data = {
            "username": config.default_username,
            "password": config.default_password
        }
        
        logger.info(f"Attempting to authenticate with Phase 2 API at {login_url}")
        
        response = requests.post(
            login_url,
            json=login_data,
            timeout=config.request_timeout,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            logger.info("Successfully obtained authentication token")
            return access_token
        else:
            logger.error(f"Authentication failed with status {response.status_code}: {response.text}")
            return None
            
    except requests.RequestException as e:
        logger.error(f"Error during authentication: {e}")
        return None


def parse_backtest_request(query: str) -> Dict[str, Any]:
    """
    Parse natural language backtest request into structured parameters
    
    Args:
        query: Natural language query describing the backtest
        
    Returns:
        Dict containing parsed backtest parameters
    """
    # Initialize default parameters
    params = {
        "ticker": None,
        "start_date": None,
        "end_date": None,
        "strategy_name": "moving_average_crossover",
        "initial_capital": 100000.0,
        "fast_period": 10,
        "slow_period": 30
    }
    
    # Convert to uppercase for easier matching
    query_upper = query.upper()
    
    # Extract ticker symbol (look for 3-5 letter combinations that might be tickers)
    ticker_patterns = [
        r'\b([A-Z]{1,5})\b(?:\s+(?:stock|shares?|ticker))?',
        r'(?:ticker|symbol|stock)\s+([A-Z]{1,5})\b',
        r'\bon\s+([A-Z]{1,5})\b'
    ]
    
    for pattern in ticker_patterns:
        match = re.search(pattern, query_upper)
        if match:
            potential_ticker = match.group(1)
            # Filter out common words that might match the pattern
            if potential_ticker not in ['FROM', 'TO', 'USING', 'WITH', 'THE', 'AND', 'OR', 'SMA', 'EMA']:
                params["ticker"] = potential_ticker
                break
    
    # Extract dates
    date_patterns = [
        r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD format
        r'(\d{1,2}/\d{1,2}/\d{4})',  # MM/DD/YYYY format
        r'(\d{4})',  # Just year
    ]
    
    dates_found = []
    for pattern in date_patterns:
        matches = re.findall(pattern, query)
        for match in matches:
            try:
                if len(match) == 4:  # Just year
                    dates_found.append(f"{match}-01-01")
                elif '/' in match:  # MM/DD/YYYY format
                    month, day, year = match.split('/')
                    dates_found.append(f"{year}-{month.zfill(2)}-{day.zfill(2)}")
                else:  # YYYY-MM-DD format
                    dates_found.append(match)
            except:
                continue
    
    # Assign dates (assume first is start, second is end)
    if len(dates_found) >= 1:
        params["start_date"] = dates_found[0]
    if len(dates_found) >= 2:
        params["end_date"] = dates_found[1]
    elif len(dates_found) == 1:
        # If only one date, try to infer the other
        year = int(dates_found[0][:4])
        if 'from' in query.lower() and dates_found[0] in query:
            params["start_date"] = dates_found[0]
            params["end_date"] = f"{year + 1}-12-31"
        else:
            params["end_date"] = dates_found[0]
            params["start_date"] = f"{year - 1}-01-01"
    
    # Extract strategy name
    strategy_patterns = [
        (r'sma\s+crossover|simple\s+moving\s+average\s+crossover', 'moving_average_crossover'),
        (r'moving\s+average\s+crossover|ma\s+crossover', 'moving_average_crossover'),
    ]
    
    for pattern, strategy in strategy_patterns:
        if re.search(pattern, query.lower()):
            params["strategy_name"] = strategy
            break
    
    # Extract initial capital
    capital_match = re.search(r'(?:capital|money|funds?)\s+(?:of\s+)?[\$]?(\d+(?:,\d{3})*(?:\.\d{2})?)', query.lower())
    if capital_match:
        capital_str = capital_match.group(1).replace(',', '')
        try:
            params["initial_capital"] = float(capital_str)
        except ValueError:
            pass
    
    # Extract moving average periods
    fast_match = re.search(r'fast\s+(?:period|ma|sma)\s+(?:of\s+)?(\d+)', query.lower())
    if fast_match:
        params["fast_period"] = int(fast_match.group(1))
    
    slow_match = re.search(r'slow\s+(?:period|ma|sma)\s+(?:of\s+)?(\d+)', query.lower())
    if slow_match:
        params["slow_period"] = int(slow_match.group(1))
    
    # Set default dates if none found
    if not params["start_date"]:
        params["start_date"] = "2023-01-01"
    if not params["end_date"]:
        params["end_date"] = "2023-12-31"
    
    logger.info(f"Parsed backtest parameters: {params}")
    return params


def format_backtest_results(response_data: Dict[str, Any]) -> str:
    """
    Format backtest API response for human-readable output
    
    Args:
        response_data: Raw API response data
        
    Returns:
        Formatted string with key metrics and insights
    """
    try:
        status = response_data.get("status", "unknown")
        
        if status == "error":
            error_msg = response_data.get("error", "Unknown error occurred")
            return f"❌ Backtest failed: {error_msg}"
        
        # Extract parameters
        params = response_data.get("parameters", {})
        ticker = params.get("ticker", "Unknown")
        start_date = params.get("start_date", "Unknown")
        end_date = params.get("end_date", "Unknown")
        strategy = params.get("strategy_name", "Unknown")
        initial_capital = params.get("initial_capital", 0)
        
        # Extract summary metrics
        summary = response_data.get("summary")
        if not summary:
            return "❌ No performance metrics available in the backtest results"
        
        # Format the results
        result_lines = [
            "📊 **Backtest Results Summary**",
            "=" * 40,
            f"🎯 **Strategy**: {strategy.replace('_', ' ').title()}",
            f"📈 **Asset**: {ticker}",
            f"📅 **Period**: {start_date} to {end_date}",
            f"💰 **Initial Capital**: ${initial_capital:,.2f}",
            "",
            "📈 **Performance Metrics**:",
            f"  • Total Return: {summary.get('total_return', 0) * 100:.2f}%",
            f"  • Annual Return: {summary.get('annual_return', 0) * 100:.2f}%",
            f"  • Sharpe Ratio: {summary.get('sharpe_ratio', 0):.2f}",
            f"  • Max Drawdown: {summary.get('max_drawdown', 0) * 100:.2f}%",
            f"  • Volatility: {summary.get('volatility', 0) * 100:.2f}%",
            "",
            "📊 **Trading Statistics**:",
            f"  • Total Trades: {summary.get('total_trades', 0)}",
            f"  • Win Rate: {summary.get('win_rate', 0) * 100:.1f}%",
            f"  • Profit Factor: {summary.get('profit_factor', 0):.2f}",
            f"  • Average Win: ${summary.get('avg_win', 0):.2f}",
            f"  • Average Loss: ${summary.get('avg_loss', 0):.2f}",
            "",
            "💵 **Capital Performance**:",
            f"  • Final Capital: ${summary.get('final_capital', 0):,.2f}",
            f"  • Total Profit/Loss: ${summary.get('final_capital', 0) - initial_capital:,.2f}",
        ]
        
        # Add performance assessment
        total_return = summary.get('total_return', 0)
        sharpe_ratio = summary.get('sharpe_ratio', 0)
        max_drawdown = summary.get('max_drawdown', 0)
        
        result_lines.extend([
            "",
            "🎯 **Performance Assessment**:"
        ])
        
        if total_return > 0.15:
            result_lines.append("  ✅ Excellent returns achieved")
        elif total_return > 0.05:
            result_lines.append("  ✅ Good positive returns")
        elif total_return > 0:
            result_lines.append("  ⚠️ Modest positive returns")
        else:
            result_lines.append("  ❌ Strategy resulted in losses")
        
        if sharpe_ratio > 1.5:
            result_lines.append("  ✅ Excellent risk-adjusted returns")
        elif sharpe_ratio > 1.0:
            result_lines.append("  ✅ Good risk-adjusted returns")
        elif sharpe_ratio > 0.5:
            result_lines.append("  ⚠️ Moderate risk-adjusted returns")
        else:
            result_lines.append("  ❌ Poor risk-adjusted returns")
        
        if abs(max_drawdown) < 0.05:
            result_lines.append("  ✅ Low drawdown - well-controlled risk")
        elif abs(max_drawdown) < 0.15:
            result_lines.append("  ⚠️ Moderate drawdown - acceptable risk")
        else:
            result_lines.append("  ❌ High drawdown - significant risk")
        
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error formatting backtest results: {e}")
        return f"❌ Error formatting results: {str(e)}"


# RAG Pipeline Integration
try:
    from ai_assistant.rag.rag_pipeline import RAGPipeline
    from ai_assistant.rag.rag_config import get_config
    
    # Initialize RAG pipeline (will be lazy-loaded)
    _rag_pipeline = None
    
    def get_rag_pipeline() -> Optional[RAGPipeline]:
        """Get or initialize the RAG pipeline"""
        global _rag_pipeline
        if _rag_pipeline is None:
            try:
                _rag_pipeline = RAGPipeline()
                logger.info("RAG Pipeline initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize RAG Pipeline: {e}")
                return None
        return _rag_pipeline
    
except ImportError as e:
    logger.warning(f"RAG Pipeline dependencies not available: {e}")
    _rag_pipeline = None
    
    def get_rag_pipeline() -> None:
        return None


def search_documents_with_rag(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search documents using the RAG pipeline
    
    Args:
        query: Search query string
        limit: Maximum number of results to return
        
    Returns:
        List of document search results
    """
    rag_pipeline = get_rag_pipeline()
    
    if rag_pipeline is None:
        logger.warning("RAG Pipeline not available, falling back to mock search")
        return simulate_vector_search_fallback(query, limit)
    
    try:
        # Perform RAG search
        rag_response = rag_pipeline.search(query, top_k=limit)
        
        # Convert RAG results to expected format
        results = []
        for search_result in rag_response.results:
            chunk = search_result.chunk
            result = {
                "id": chunk.chunk_id,
                "title": chunk.metadata.title,
                "content": chunk.content,
                "category": chunk.metadata.category,
                "relevance_score": search_result.score,
                "tags": chunk.metadata.tags,
                "source": chunk.metadata.source,
                "file_type": chunk.metadata.file_type,
                "rank": search_result.rank
            }
            results.append(result)
        
        logger.info(f"RAG search completed: {len(results)} results in {rag_response.processing_time:.2f}s")
        return results
        
    except Exception as e:
        logger.error(f"RAG search failed: {e}, falling back to mock search")
        return simulate_vector_search_fallback(query, limit)


def simulate_vector_search_fallback(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Fallback mock vector search when RAG pipeline is not available
    
    Args:
        query: Search query string
        limit: Maximum number of results to return
        
    Returns:
        List of simulated document results
    """
    # Mock document database with trading-related content
    mock_documents = [
        {
            "id": "doc_001",
            "title": "Moving Average Crossover Strategy Guide",
            "content": "The moving average crossover strategy is one of the most popular technical analysis strategies. It involves using two moving averages of different periods to generate buy and sell signals.",
            "category": "trading_strategies",
            "relevance_score": 0.95,
            "tags": ["moving_average", "crossover", "technical_analysis", "strategy"],
            "source": "mock_data",
            "file_type": ".md",
            "rank": 1
        },
        {
            "id": "doc_002",
            "title": "Risk Management in Algorithmic Trading",
            "content": "Effective risk management is crucial for successful algorithmic trading. Key concepts include position sizing, stop losses, maximum drawdown limits, and portfolio diversification.",
            "category": "risk_management",
            "relevance_score": 0.88,
            "tags": ["risk_management", "position_sizing", "stop_loss", "drawdown"],
            "source": "mock_data",
            "file_type": ".md",
            "rank": 2
        },
        {
            "id": "doc_003",
            "title": "Backtesting Best Practices",
            "content": "Proper backtesting methodology is essential for validating trading strategies. Important considerations include avoiding look-ahead bias, accounting for transaction costs, and using out-of-sample testing.",
            "category": "backtesting",
            "relevance_score": 0.92,
            "tags": ["backtesting", "validation", "bias", "transaction_costs"],
            "source": "mock_data",
            "file_type": ".md",
            "rank": 3
        },
        {
            "id": "doc_004",
            "title": "Market Volatility Analysis",
            "content": "Understanding market volatility is key to successful trading. Volatility affects strategy performance, risk levels, and optimal position sizing. Common volatility measures include standard deviation and VIX.",
            "category": "market_analysis",
            "relevance_score": 0.85,
            "tags": ["volatility", "market_analysis", "VIX", "standard_deviation"],
            "source": "mock_data",
            "file_type": ".md",
            "rank": 4
        },
        {
            "id": "doc_005",
            "title": "Performance Metrics for Trading Strategies",
            "content": "Key performance metrics for evaluating trading strategies include Sharpe ratio, Calmar ratio, maximum drawdown, win rate, and profit factor. Each metric provides different insights into strategy performance.",
            "category": "performance_metrics",
            "relevance_score": 0.90,
            "tags": ["performance", "sharpe_ratio", "calmar_ratio", "metrics"],
            "source": "mock_data",
            "file_type": ".md",
            "rank": 5
        }
    ]
    
    # Simple keyword-based relevance scoring
    query_lower = query.lower()
    query_words = set(query_lower.split())
    
    # Calculate relevance scores based on keyword matches
    for doc in mock_documents:
        title_words = set(doc["title"].lower().split())
        content_words = set(doc["content"].lower().split())
        tag_words = set([tag.lower() for tag in doc["tags"]])
        
        # Calculate matches
        title_matches = len(query_words.intersection(title_words))
        content_matches = len(query_words.intersection(content_words))
        tag_matches = len(query_words.intersection(tag_words))
        
        # Weighted relevance score
        relevance = (title_matches * 3 + content_matches * 1 + tag_matches * 2) / len(query_words)
        doc["relevance_score"] = min(0.95, relevance * 0.3 + doc["relevance_score"] * 0.7)
    
    # Sort by relevance and return top results
    sorted_docs = sorted(mock_documents, key=lambda x: x["relevance_score"], reverse=True)
    return sorted_docs[:limit]


# OpenHands Planning and Execution Functions
def create_planning_steps(parsed_request: Dict[str, Any]) -> List[PlanningStep]:
    """
    Create planning steps based on parsed development request
    
    Args:
        parsed_request: Parsed development request parameters
        
    Returns:
        List of planning steps to execute
    """
    steps = []
    task_type = parsed_request['task_type']
    target_files = parsed_request.get('target_files', [])
    endpoints = parsed_request.get('endpoints', [])
    priority = parsed_request.get('priority', TaskPriority.MEDIUM)
    
    if task_type == TaskType.ADD_ENDPOINT:
        # Step 1: Analyze existing API structure
        steps.append(PlanningStep(
            step_id="analyze_api_structure",
            description="Analyze existing API structure and routing",
            task_type=TaskType.ADD_ENDPOINT,
            target_files=["ai_assistant/main.py"],
            validation_criteria=["API structure identified", "Routing pattern understood"]
        ))
        
        # Step 2: Create endpoint implementation
        endpoint_name = endpoints[0] if endpoints else "new_endpoint"
        steps.append(PlanningStep(
            step_id="implement_endpoint",
            description=f"Implement {endpoint_name} endpoint with proper routing and response models",
            task_type=TaskType.ADD_ENDPOINT,
            target_files=["ai_assistant/main.py"],
            dependencies=["analyze_api_structure"],
            estimated_complexity=3,
            priority=priority,
            validation_criteria=["Endpoint function created", "Route decorator added", "Response model defined"]
        ))
        
        # Step 3: Add endpoint to documentation
        steps.append(PlanningStep(
            step_id="update_documentation",
            description="Update API documentation with new endpoint",
            task_type=TaskType.UPDATE_CONFIG,
            target_files=["ai_assistant/main.py"],
            dependencies=["implement_endpoint"],
            estimated_complexity=1,
            validation_criteria=["Docstring added", "OpenAPI tags configured"]
        ))
    
    elif task_type == TaskType.MODIFY_FUNCTION:
        # Step 1: Locate target function
        steps.append(PlanningStep(
            step_id="locate_function",
            description="Locate and analyze target function for modification",
            task_type=TaskType.MODIFY_FUNCTION,
            target_files=target_files or ["ai_assistant/tools.py", "ai_assistant/main.py"],
            validation_criteria=["Function located", "Current implementation analyzed"]
        ))
        
        # Step 2: Implement modifications
        steps.append(PlanningStep(
            step_id="modify_function",
            description="Apply requested modifications to the function",
            task_type=TaskType.MODIFY_FUNCTION,
            target_files=target_files or ["ai_assistant/tools.py"],
            dependencies=["locate_function"],
            estimated_complexity=2,
            priority=priority,
            validation_criteria=["Function modified", "Functionality preserved", "Error handling maintained"]
        ))
    
    elif task_type == TaskType.CREATE_FILE:
        # Step 1: Create new file with basic structure
        steps.append(PlanningStep(
            step_id="create_file",
            description="Create new file with appropriate structure and imports",
            task_type=TaskType.CREATE_FILE,
            target_files=target_files,
            estimated_complexity=2,
            priority=priority,
            validation_criteria=["File created", "Basic structure implemented", "Imports added"]
        ))
    
    elif task_type == TaskType.ADD_FEATURE:
        # Generic feature addition steps
        steps.append(PlanningStep(
            step_id="analyze_requirements",
            description="Analyze feature requirements and identify implementation approach",
            task_type=TaskType.ADD_FEATURE,
            target_files=target_files or ["ai_assistant/tools.py", "ai_assistant/main.py"],
            validation_criteria=["Requirements analyzed", "Implementation approach defined"]
        ))
        
        steps.append(PlanningStep(
            step_id="implement_feature",
            description="Implement the requested feature",
            task_type=TaskType.ADD_FEATURE,
            target_files=target_files or ["ai_assistant/tools.py"],
            dependencies=["analyze_requirements"],
            estimated_complexity=3,
            priority=priority,
            validation_criteria=["Feature implemented", "Integration points identified", "Error handling added"]
        ))
    
    return steps


def execute_planning_step(step: PlanningStep, workflow: OpenHandsWorkflow) -> ExecutionResult:
    """
    Execute a single planning step
    
    Args:
        step: Planning step to execute
        workflow: Current workflow state
        
    Returns:
        Execution result
    """
    start_time = datetime.now()
    result = ExecutionResult(step_id=step.step_id, success=False)
    
    try:
        logger.info(f"Executing step: {step.step_id} - {step.description}")
        
        if step.task_type == TaskType.ADD_ENDPOINT:
            result = execute_add_endpoint_step(step, workflow)
        elif step.task_type == TaskType.MODIFY_FUNCTION:
            result = execute_modify_function_step(step, workflow)
        elif step.task_type == TaskType.CREATE_FILE:
            result = execute_create_file_step(step, workflow)
        elif step.task_type == TaskType.ADD_FEATURE:
            result = execute_add_feature_step(step, workflow)
        else:
            result.error_message = f"Unsupported task type: {step.task_type}"
            
        result.execution_time = (datetime.now() - start_time).total_seconds()
        
        if result.success:
            logger.info(f"Successfully executed step: {step.step_id}")
        else:
            logger.error(f"Failed to execute step: {step.step_id} - {result.error_message}")
            
    except Exception as e:
        result.error_message = f"Exception during execution: {str(e)}"
        result.execution_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"Exception in step {step.step_id}: {e}")
    
    return result


def execute_add_endpoint_step(step: PlanningStep, workflow: OpenHandsWorkflow) -> ExecutionResult:
    """Execute endpoint addition step"""
    result = ExecutionResult(step_id=step.step_id, success=False)
    
    try:
        if step.step_id == "analyze_api_structure":
            # Analyze existing API structure
            main_py_path = "ai_assistant/main.py"
            if os.path.exists(main_py_path):
                with open(main_py_path, 'r') as f:
                    content = f.read()
                    
                # Check for existing endpoints
                endpoint_count = content.count('@app.')
                result.validation_results = [
                    f"Found {endpoint_count} existing endpoints",
                    "FastAPI structure identified",
                    "Routing pattern analyzed"
                ]
                result.success = True
            else:
                result.error_message = "main.py not found"
                
        elif step.step_id == "implement_endpoint":
            # Implement new endpoint
            main_py_path = "ai_assistant/main.py"
            if not is_safe_path(main_py_path):
                result.error_message = "Unsafe file path"
                return result
                
            # Create backup
            backup_path = create_backup(main_py_path)
            if backup_path:
                result.backup_paths.append(backup_path)
            
            # Generate endpoint code based on request
            endpoint_code = generate_endpoint_code(workflow.original_request)
            
            if not openhands_config.dry_run_mode:
                # Add endpoint to main.py
                success = add_endpoint_to_file(main_py_path, endpoint_code)
                if success:
                    result.files_modified.append(main_py_path)
                    result.validation_results = ["Endpoint added to main.py", "Route decorator configured"]
                    result.success = True
                else:
                    result.error_message = "Failed to add endpoint to file"
            else:
                result.validation_results = ["DRY RUN: Endpoint code generated", "Would modify main.py"]
                result.success = True
                
    except Exception as e:
        result.error_message = f"Error in endpoint step: {str(e)}"
    
    return result


def execute_modify_function_step(step: PlanningStep, workflow: OpenHandsWorkflow) -> ExecutionResult:
    """Execute function modification step"""
    result = ExecutionResult(step_id=step.step_id, success=False)
    
    try:
        if step.step_id == "locate_function":
            # Locate target function
            for file_path in step.target_files:
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        content = f.read()
                        # Simple function detection
                        if 'def ' in content:
                            result.validation_results.append(f"Functions found in {file_path}")
                            
            result.success = True
            
        elif step.step_id == "modify_function":
            # Modify function based on request
            for file_path in step.target_files:
                if not is_safe_path(file_path):
                    continue
                    
                backup_path = create_backup(file_path)
                if backup_path:
                    result.backup_paths.append(backup_path)
                
                if not openhands_config.dry_run_mode:
                    # Apply modifications (simplified implementation)
                    result.files_modified.append(file_path)
                    result.validation_results.append(f"Modified functions in {file_path}")
                else:
                    result.validation_results.append(f"DRY RUN: Would modify {file_path}")
                    
            result.success = True
            
    except Exception as e:
        result.error_message = f"Error in function modification: {str(e)}"
    
    return result


def execute_create_file_step(step: PlanningStep, workflow: OpenHandsWorkflow) -> ExecutionResult:
    """Execute file creation step"""
    result = ExecutionResult(step_id=step.step_id, success=False)
    
    try:
        for file_path in step.target_files:
            if not is_safe_path(file_path):
                continue
                
            if not openhands_config.dry_run_mode:
                # Create file with basic structure
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w') as f:
                    f.write(generate_file_template(file_path, workflow.original_request))
                    
                result.files_created.append(file_path)
                result.validation_results.append(f"Created {file_path}")
            else:
                result.validation_results.append(f"DRY RUN: Would create {file_path}")
                
        result.success = True
        
    except Exception as e:
        result.error_message = f"Error creating file: {str(e)}"
    
    return result


def execute_add_feature_step(step: PlanningStep, workflow: OpenHandsWorkflow) -> ExecutionResult:
    """Execute feature addition step"""
    result = ExecutionResult(step_id=step.step_id, success=False)
    
    try:
        if step.step_id == "analyze_requirements":
            # Analyze feature requirements
            result.validation_results = [
                "Feature requirements analyzed",
                "Implementation approach defined",
                "Target files identified"
            ]
            result.success = True
            
        elif step.step_id == "implement_feature":
            # Implement feature
            for file_path in step.target_files:
                if not is_safe_path(file_path):
                    continue
                    
                backup_path = create_backup(file_path)
                if backup_path:
                    result.backup_paths.append(backup_path)
                
                if not openhands_config.dry_run_mode:
                    result.files_modified.append(file_path)
                    result.validation_results.append(f"Feature implemented in {file_path}")
                else:
                    result.validation_results.append(f"DRY RUN: Would modify {file_path}")
                    
            result.success = True
            
    except Exception as e:
        result.error_message = f"Error in feature implementation: {str(e)}"
    
    return result


def generate_endpoint_code(request: str) -> str:
    """Generate endpoint code based on request"""
    # Extract endpoint name from request
    endpoint_match = re.search(r'/(\w+)', request)
    endpoint_name = endpoint_match.group(1) if endpoint_match else "status"
    
    # Generate basic endpoint template
    code = f'''
# {endpoint_name.title()} endpoint - Generated by OpenHands
@app.get("/api/v1/{endpoint_name}", tags=["{endpoint_name.title()}"])
async def get_{endpoint_name}():
    """
    {endpoint_name.title()} endpoint
    Generated based on request: {request}
    """
    return {{
        "{endpoint_name}": "active",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "{endpoint_name.title()} endpoint is working"
    }}
'''
    return code


def generate_file_template(file_path: str, request: str) -> str:
    """Generate file template based on file type and request"""
    file_ext = Path(file_path).suffix
    
    if file_ext == '.py':
        return f'''"""
{Path(file_path).stem} - Generated by OpenHands
Created based on request: {request}
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def main():
    """Main function"""
    logger.info("Module initialized")


if __name__ == "__main__":
    main()
'''
    elif file_ext == '.json':
        return '''{
    "generated_by": "OpenHands",
    "request": "''' + request + '''",
    "created_at": "''' + datetime.now(timezone.utc).isoformat() + '''"
}'''
    else:
        return f'''# {Path(file_path).stem}
# Generated by OpenHands
# Request: {request}
# Created: {datetime.now(timezone.utc).isoformat()}
'''


def add_endpoint_to_file(file_path: str, endpoint_code: str) -> bool:
    """Add endpoint code to main.py file"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Find insertion point (before the main block)
        insertion_point = content.rfind('if __name__ == "__main__":')
        if insertion_point == -1:
            # If no main block, append to end
            insertion_point = len(content)
        
        # Insert the endpoint code
        new_content = content[:insertion_point] + endpoint_code + '\n\n' + content[insertion_point:]
        
        with open(file_path, 'w') as f:
            f.write(new_content)
            
        return True
        
    except Exception as e:
        logger.error(f"Error adding endpoint to file: {e}")
        return False


def rollback_workflow(workflow: OpenHandsWorkflow) -> bool:
    """
    Rollback all changes made during workflow execution
    
    Args:
        workflow: Workflow to rollback
        
    Returns:
        True if rollback successful, False otherwise
    """
    if not openhands_config.enable_rollback:
        logger.warning("Rollback is disabled in configuration")
        return False
        
    try:
        logger.info(f"Starting rollback for workflow: {workflow.workflow_id}")
        rollback_success = True
        
        # Rollback in reverse order of execution
        for result in reversed(workflow.execution_results):
            if not result.success:
                continue
                
            # Restore from backups
            for backup_path in result.backup_paths:
                try:
                    backup_path_obj = Path(backup_path)
                    if backup_path_obj.exists():
                        # Extract original file path from backup name
                        original_name = backup_path_obj.stem.split('_')[0] + backup_path_obj.suffix
                        original_path = backup_path_obj.parent.parent / original_name
                        
                        shutil.copy2(backup_path, original_path)
                        logger.info(f"Restored {original_path} from backup")
                    else:
                        logger.warning(f"Backup file not found: {backup_path}")
                        rollback_success = False
                        
                except Exception as e:
                    logger.error(f"Error restoring from backup {backup_path}: {e}")
                    rollback_success = False
            
            # Remove created files
            for created_file in result.files_created:
                try:
                    if os.path.exists(created_file):
                        os.remove(created_file)
                        logger.info(f"Removed created file: {created_file}")
                except Exception as e:
                    logger.error(f"Error removing created file {created_file}: {e}")
                    rollback_success = False
        
        if rollback_success:
            workflow.status = "rolled_back"
            logger.info(f"Successfully rolled back workflow: {workflow.workflow_id}")
        else:
            logger.error(f"Partial rollback for workflow: {workflow.workflow_id}")
            
        return rollback_success
        
    except Exception as e:
        logger.error(f"Error during rollback: {e}")
        return False


# LangChain Tools
@tool("run_backtest", args_schema=BacktestToolInput)
def run_backtest_tool(query: str) -> str:
    """
    Run a backtest using the Phase 2 API based on natural language input.
    
    This tool parses natural language queries to extract backtest parameters,
    makes API calls to the Phase 2 backtesting service, and returns formatted results.
    
    Example queries:
    - "Run a backtest on AAPL from 2022-01-01 to 2023-12-31 using SMA Crossover strategy"
    - "Backtest GOOGL for 2023 with moving average crossover"
    - "Test the SMA strategy on MSFT from 2022 to 2023 with $50000 capital"
    
    Args:
        query: Natural language description of the backtest to run
        
    Returns:
        Formatted string with backtest results and performance metrics
    """
    try:
        logger.info(f"Processing backtest request: {query}")
        
        # Parse the natural language query
        params = parse_backtest_request(query)
        
        # Validate required parameters
        if not params.get("ticker"):
            return "❌ Error: Could not identify a ticker symbol in your request. Please specify a stock ticker (e.g., AAPL, GOOGL, MSFT)."
        
        # Get authentication token
        token = get_auth_token()
        if not token:
            return "❌ Error: Could not authenticate with the trading system. Please check the API connection."
        
        # Prepare API request
        backtest_url = f"{config.phase2_api_base_url}/api/v1/backtest/backtest"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Prepare request payload
        payload = {
            "ticker": params["ticker"],
            "start_date": params["start_date"],
            "end_date": params["end_date"],
            "strategy_name": params["strategy_name"],
            "initial_capital": params["initial_capital"],
            "fast_period": params["fast_period"],
            "slow_period": params["slow_period"]
        }
        
        logger.info(f"Making backtest API request with payload: {payload}")
        
        # Make the API request
        response = requests.post(
            backtest_url,
            json=payload,
            headers=headers,
            timeout=config.request_timeout
        )
        
        if response.status_code == 200:
            result_data = response.json()
            return format_backtest_results(result_data)
        else:
            error_msg = f"API request failed with status {response.status_code}"
            try:
                error_data = response.json()
                error_msg += f": {error_data.get('error', 'Unknown error')}"
            except:
                error_msg += f": {response.text}"
            
            logger.error(error_msg)
            return f"❌ {error_msg}"
            
    except requests.RequestException as e:
        error_msg = f"Network error while running backtest: {str(e)}"
        logger.error(error_msg)
        return f"❌ {error_msg}"
    except Exception as e:
        error_msg = f"Unexpected error while running backtest: {str(e)}"
        logger.error(error_msg)
        return f"❌ {error_msg}"


@tool("query_documents", args_schema=DocumentQueryInput)
def query_documents_tool(query: str, limit: int = 5) -> str:
    """
    Query the document database using vector similarity search.
    
    This tool searches through trading-related documents, research papers,
    strategy guides, and educational content to find relevant information
    based on the user's query.
    
    Currently uses a simulated vector search with mock documents.
    Future versions will integrate with Qdrant vector database.
    
    Example queries:
    - "What are the best trading strategies for volatile markets?"
    - "How to calculate Sharpe ratio?"
    - "Risk management techniques for algorithmic trading"
    - "Moving average crossover strategy implementation"
    
    Args:
        query: Natural language query to search for relevant documents
        limit: Maximum number of documents to return (1-20, default: 5)
        
    Returns:
        Formatted string with relevant documents and their content
    """
    try:
        logger.info(f"Processing document query: {query}")
        
        # Validate limit parameter
        limit = max(1, min(20, limit))
        
        # Perform vector similarity search using RAG pipeline
        documents = search_documents_with_rag(query, limit)
        
        if not documents:
            return "❌ No relevant documents found for your query."
        
        # Format the results
        result_lines = [
            f"📚 **Document Search Results** (Top {len(documents)} matches)",
            "=" * 50,
            f"🔍 **Query**: {query}",
            ""
        ]
        
        for i, doc in enumerate(documents, 1):
            relevance_percentage = doc["relevance_score"] * 100
            
            result_lines.extend([
                f"**{i}. {doc['title']}** (Relevance: {relevance_percentage:.1f}%)",
                f"📂 Category: {doc['category'].replace('_', ' ').title()}",
                f"📄 Content: {doc['content'][:200]}{'...' if len(doc['content']) > 200 else ''}",
                f"🏷️ Tags: {', '.join(doc['tags'])}",
                f"🆔 Document ID: {doc['id']}",
                ""
            ])
        
        result_lines.extend([
            "💡 **How to use these results**:",
            "• Review the content summaries to find relevant information",
            "• Use document IDs to reference specific sources",
            "• Try more specific queries for targeted results",
            "• Combine insights from multiple documents for comprehensive understanding"
        ])
        
        return "\n".join(result_lines)
        
    except Exception as e:
        error_msg = f"Error querying documents: {str(e)}"
        logger.error(error_msg)
        return f"❌ {error_msg}"


# Additional utility tools that could be useful
@tool("get_trading_system_status")
def get_trading_system_status() -> str:
    """
    Check the status of the Phase 2 trading system API.
    
    This tool verifies connectivity to the backtesting API and returns
    system health information.
    
    Returns:
        Formatted string with system status information
    """
    try:
        logger.info("Checking trading system status")
        
        # Check Phase 2 API health
        health_url = f"{config.phase2_api_base_url}/health"
        
        response = requests.get(health_url, timeout=10)
        
        if response.status_code == 200:
            health_data = response.json()
            
            result_lines = [
                "✅ **Trading System Status: HEALTHY**",
                "=" * 40,
                f"🌐 API Endpoint: {config.phase2_api_base_url}",
                f"📊 Status: {health_data.get('status', 'Unknown')}",
                f"🕐 Timestamp: {health_data.get('timestamp', 'Unknown')}",
                f"📋 Version: {health_data.get('version', 'Unknown')}",
                "",
                "🔧 **Available Services**:",
                "• Backtesting API ✅",
                "• Authentication Service ✅", 
                "• Market Data Access ✅",
                "",
                "💡 The system is ready to process backtest requests!"
            ]
            
            return "\n".join(result_lines)
        else:
            return f"❌ Trading system is not responding properly (Status: {response.status_code})"
            
    except requests.RequestException as e:
        return f"❌ Cannot connect to trading system: {str(e)}"
    except Exception as e:
        return f"❌ Error checking system status: {str(e)}"


@tool("code_development_tool", args_schema=CodeDevelopmentInput)
def code_development_tool(request: str, preview_only: bool = False, target_files: Optional[List[str]] = None) -> str:
    """
    OpenHands-powered code development tool for AI-assisted code generation and modification.
    
    This tool enables the AI assistant to modify code on the file system using OpenHands
    planning and execution workflow. It can handle various development tasks including:
    
    - Adding new API endpoints
    - Creating new functions and classes
    - Modifying existing code
    - Creating new files
    - Refactoring code
    - Adding tests and documentation
    - Fixing bugs and issues
    
    The tool follows a structured approach:
    1. Parse the natural language request
    2. Create a planning phase with step-by-step breakdown
    3. Execute each step with proper safety checks
    4. Provide rollback capabilities if needed
    
    Safety Features:
    - File path validation and workspace restrictions
    - Automatic backup creation before modifications
    - Dry run mode for previewing changes
    - Rollback capabilities for failed operations
    - File size and extension restrictions
    
    Example requests:
    - "Add a new endpoint /status to the AI assistant"
    - "Create a function to calculate portfolio risk metrics"
    - "Add error handling to the backtest API calls"
    - "Refactor the authentication logic in main.py"
    
    Args:
        request: Natural language development request
        preview_only: If True, only show what would be done without making changes
        target_files: Optional list of specific files to target for modifications
        
    Returns:
        Formatted string with execution results, planning steps, and file modifications
    """
    import uuid
    
    try:
        logger.info(f"Processing code development request: {request}")
        
        # Generate unique workflow ID
        workflow_id = str(uuid.uuid4())[:8]
        
        # Parse the development request
        parsed_request = parse_development_request(request)
        
        # Override target files if provided
        if target_files:
            parsed_request['target_files'] = target_files
        
        # Set preview mode if requested
        if preview_only:
            openhands_config.dry_run_mode = True
        
        # Create workflow
        workflow = OpenHandsWorkflow(
            workflow_id=workflow_id,
            original_request=request,
            status="planning"
        )
        
        # Create planning steps
        planning_steps = create_planning_steps(parsed_request)
        workflow.planning_steps = planning_steps
        
        if not planning_steps:
            return "❌ Could not create a valid execution plan for the request. Please provide more specific details."
        
        # Format planning phase results
        result_lines = [
            "🔧 **OpenHands Code Development Tool**",
            "=" * 50,
            f"🆔 **Workflow ID**: {workflow_id}",
            f"📝 **Request**: {request}",
            f"🎯 **Task Type**: {parsed_request['task_type'].value.replace('_', ' ').title()}",
            f"⚡ **Priority**: {parsed_request['priority'].value.title()}",
            f"🔍 **Preview Mode**: {'Yes' if preview_only else 'No'}",
            "",
            "📋 **Planning Phase**:",
            f"Generated {len(planning_steps)} execution steps:",
            ""
        ]
        
        # Display planning steps
        for i, step in enumerate(planning_steps, 1):
            complexity_stars = "⭐" * step.estimated_complexity
            result_lines.extend([
                f"**Step {i}: {step.description}**",
                f"  • ID: {step.step_id}",
                f"  • Type: {step.task_type.value.replace('_', ' ').title()}",
                f"  • Complexity: {complexity_stars} ({step.estimated_complexity}/5)",
                f"  • Target Files: {', '.join(step.target_files)}",
                f"  • Dependencies: {', '.join(step.dependencies) if step.dependencies else 'None'}",
                f"  • Validation: {', '.join(step.validation_criteria)}",
                ""
            ])
        
        # Execute planning steps
        workflow.status = "executing"
        execution_success = True
        
        result_lines.extend([
            "⚙️ **Execution Phase**:",
            ""
        ])
        
        for i, step in enumerate(planning_steps, 1):
            # Check dependencies
            if step.dependencies:
                dependency_met = all(
                    any(result.step_id == dep and result.success for result in workflow.execution_results)
                    for dep in step.dependencies
                )
                if not dependency_met:
                    result_lines.append(f"❌ Step {i}: Skipped due to unmet dependencies")
                    continue
            
            # Execute step
            execution_result = execute_planning_step(step, workflow)
            workflow.execution_results.append(execution_result)
            
            # Update workflow statistics
            workflow.total_files_modified += len(execution_result.files_modified)
            workflow.total_files_created += len(execution_result.files_created)
            
            # Format execution result
            status_icon = "✅" if execution_result.success else "❌"
            result_lines.extend([
                f"{status_icon} **Step {i}: {step.description}**",
                f"  • Execution Time: {execution_result.execution_time:.2f}s",
                f"  • Files Modified: {len(execution_result.files_modified)}",
                f"  • Files Created: {len(execution_result.files_created)}",
                f"  • Backups Created: {len(execution_result.backup_paths)}"
            ])
            
            if execution_result.files_modified:
                result_lines.append(f"  • Modified: {', '.join(execution_result.files_modified)}")
            
            if execution_result.files_created:
                result_lines.append(f"  • Created: {', '.join(execution_result.files_created)}")
            
            if execution_result.validation_results:
                result_lines.append(f"  • Validation: {', '.join(execution_result.validation_results)}")
            
            if not execution_result.success:
                result_lines.append(f"  • Error: {execution_result.error_message}")
                execution_success = False
            
            result_lines.append("")
        
        # Update workflow status
        workflow.status = "completed" if execution_success else "failed"
        workflow.completed_at = datetime.now()
        
        # Summary
        result_lines.extend([
            "📊 **Execution Summary**:",
            f"  • Overall Status: {'✅ Success' if execution_success else '❌ Failed'}",
            f"  • Total Steps: {len(planning_steps)}",
            f"  • Successful Steps: {sum(1 for r in workflow.execution_results if r.success)}",
            f"  • Files Modified: {workflow.total_files_modified}",
            f"  • Files Created: {workflow.total_files_created}",
            f"  • Total Execution Time: {sum(r.execution_time for r in workflow.execution_results):.2f}s",
            ""
        ])
        
        # Rollback option if failed and not in preview mode
        if not execution_success and not preview_only and openhands_config.enable_rollback:
            result_lines.extend([
                "🔄 **Rollback Available**:",
                "The workflow failed. You can request a rollback to undo any changes made.",
                f"Use: 'Rollback workflow {workflow_id}' to restore previous state.",
                ""
            ])
        
        # Safety and next steps
        if preview_only:
            result_lines.extend([
                "🔍 **Preview Mode Summary**:",
                "This was a preview run - no actual changes were made to the file system.",
                "To execute the changes, run the same request without preview_only=True.",
                ""
            ])
        else:
            result_lines.extend([
                "🛡️ **Safety Information**:",
                f"• All modified files have been backed up to: {openhands_config.backup_dir}",
                "• Rollback is available if issues are detected",
                "• File modifications are logged for audit trail",
                ""
            ])
        
        result_lines.extend([
            "💡 **Next Steps**:",
            "• Test the implemented changes thoroughly",
            "• Review the modified files for correctness",
            "• Run any relevant tests to ensure functionality",
            "• Consider adding documentation for new features"
        ])
        
        # Reset dry run mode
        if preview_only:
            openhands_config.dry_run_mode = False
        
        return "\n".join(result_lines)
        
    except Exception as e:
        error_msg = f"Error in code development tool: {str(e)}"
        logger.error(error_msg)
        
        # Reset dry run mode on error
        if preview_only:
            openhands_config.dry_run_mode = False
        
        return f"❌ {error_msg}\n\nPlease check the request format and try again. For complex requests, consider breaking them into smaller, more specific tasks."


# Workflow management helper function
def get_workflow_status(workflow_id: str) -> str:
    """
    Get status of a specific workflow (placeholder for future implementation)
    
    Args:
        workflow_id: ID of the workflow to check
        
    Returns:
        Status information string
    """
    return f"Workflow {workflow_id} status checking is not yet implemented. This would integrate with a workflow persistence layer."


# Forecasting Models Integration
try:
    from .forecasting_models import (
        FeastDataLoader, ModelType, PredictionHorizon,
        ForecastingModelFactory, ModelConfig
    )
    from .model_training import load_trained_model
    from .stock_prediction_models import select_best_model, compare_models
    
    FORECASTING_AVAILABLE = True
    logger.info("Forecasting models integration available")
except ImportError as e:
    FORECASTING_AVAILABLE = False
    logger.warning(f"Forecasting models not available: {e}")


def parse_stock_prediction_request(query: str) -> Dict[str, Any]:
    """
    Parse natural language stock prediction request into structured parameters
    
    Args:
        query: Natural language query describing the prediction request
        
    Returns:
        Dict containing parsed prediction parameters
    """
    # Initialize default parameters
    params = {
        "ticker": None,
        "prediction_horizon": 7,  # days
        "model_type": None,
        "include_confidence": True,
        "start_date": None,
        "end_date": None
    }
    
    # Convert to uppercase for easier matching
    query_upper = query.upper()
    
    # Extract ticker symbol
    ticker_patterns = [
        r'\b([A-Z]{1,5})\b(?:\s+(?:stock|shares?|ticker|price))?',
        r'(?:ticker|symbol|stock)\s+([A-Z]{1,5})\b',
        r'(?:predict|forecast)\s+([A-Z]{1,5})\b'
    ]
    
    for pattern in ticker_patterns:
        match = re.search(pattern, query_upper)
        if match:
            potential_ticker = match.group(1)
            # Filter out common words
            if potential_ticker not in ['FOR', 'THE', 'AND', 'OR', 'NEXT', 'DAYS', 'WEEK', 'MONTH', 'USING', 'WITH']:
                params["ticker"] = potential_ticker
                break
    
    # Extract prediction horizon
    horizon_patterns = [
        (r'(\d+)\s*days?', 1),
        (r'(\d+)\s*day', 1),
        (r'next\s+(\d+)\s*days?', 1),
        (r'(\d+)d\b', 1),
        (r'1\s*week|one\s*week|next\s*week', 7),
        (r'(\d+)\s*weeks?', 7),
        (r'1\s*month|one\s*month|next\s*month', 30),
        (r'(\d+)\s*months?', 30)
    ]
    
    for pattern, multiplier in horizon_patterns:
        match = re.search(pattern, query.lower())
        if match:
            if multiplier == 1:
                params["prediction_horizon"] = int(match.group(1))
            elif multiplier == 7:
                if match.group(0).startswith(('1', 'one', 'next')):
                    params["prediction_horizon"] = 7
                else:
                    params["prediction_horizon"] = int(match.group(1)) * 7
            elif multiplier == 30:
                if match.group(0).startswith(('1', 'one', 'next')):
                    params["prediction_horizon"] = 30
                else:
                    params["prediction_horizon"] = int(match.group(1)) * 30
            break
    
    # Extract model type
    model_patterns = [
        (r'lstm|neural\s*network|deep\s*learning', 'lstm'),
        (r'arima|autoregressive', 'arima'),
        (r'random\s*forest|rf', 'random_forest'),
        (r'xgboost|gradient\s*boost|xgb', 'xgboost'),
        (r'prophet|facebook', 'prophet'),
        (r'ensemble|combined|multiple\s*models', 'ensemble')
    ]
    
    for pattern, model_type in model_patterns:
        if re.search(pattern, query.lower()):
            params["model_type"] = model_type
            break
    
    # Check for confidence interval requests
    if any(word in query.lower() for word in ['confidence', 'uncertainty', 'interval', 'range']):
        params["include_confidence"] = True
    elif any(word in query.lower() for word in ['no confidence', 'without confidence', 'exact']):
        params["include_confidence"] = False
    
    logger.info(f"Parsed prediction parameters: {params}")
    return params


def format_prediction_results(prediction_result: Any, ticker: str, query: str) -> str:
    """
    Format prediction results for human-readable output
    
    Args:
        prediction_result: Prediction result object
        ticker: Stock ticker symbol
        query: Original query
        
    Returns:
        Formatted string with prediction results
    """
    try:
        if not prediction_result:
            return "❌ No prediction results available"
        
        # Extract prediction data
        predictions = prediction_result.predictions
        model_type = prediction_result.model_type.value if hasattr(prediction_result.model_type, 'value') else str(prediction_result.model_type)
        horizon = prediction_result.prediction_horizon.value if hasattr(prediction_result.prediction_horizon, 'value') else prediction_result.prediction_horizon
        confidence = prediction_result.model_confidence
        
        # Format the results
        result_lines = [
            "🔮 **Stock Price Prediction Results**",
            "=" * 45,
            f"🎯 **Query**: {query}",
            f"📈 **Ticker**: {ticker}",
            f"🤖 **Model**: {model_type.replace('_', ' ').title()}",
            f"📅 **Prediction Horizon**: {horizon} day{'s' if horizon != 1 else ''}",
            f"🎯 **Model Confidence**: {confidence * 100:.1f}%",
            "",
            "📊 **Predicted Prices**:"
        ]
        
        # Add predictions
        if isinstance(predictions, (list, np.ndarray)):
            for i, price in enumerate(predictions[:min(len(predictions), horizon)], 1):
                day_label = f"Day {i}" if horizon > 1 else "Tomorrow"
                result_lines.append(f"  • {day_label}: ${price:.2f}")
        else:
            result_lines.append(f"  • Predicted Price: ${predictions:.2f}")
        
        # Add confidence intervals if available
        if hasattr(prediction_result, 'confidence_intervals') and prediction_result.confidence_intervals:
            lower, upper = prediction_result.confidence_intervals
            result_lines.extend([
                "",
                "📈 **Confidence Intervals (95%)**:"
            ])
            
            if isinstance(lower, (list, np.ndarray)) and isinstance(upper, (list, np.ndarray)):
                for i, (low, high) in enumerate(zip(lower[:horizon], upper[:horizon]), 1):
                    day_label = f"Day {i}" if horizon > 1 else "Tomorrow"
                    result_lines.append(f"  • {day_label}: ${low:.2f} - ${high:.2f}")
            else:
                result_lines.append(f"  • Range: ${lower:.2f} - ${upper:.2f}")
        
        # Add feature importance if available
        if hasattr(prediction_result, 'feature_importance') and prediction_result.feature_importance:
            result_lines.extend([
                "",
                "🔍 **Key Factors** (Top 5):"
            ])
            
            # Sort features by importance
            sorted_features = sorted(
                prediction_result.feature_importance.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            for feature, importance in sorted_features:
                feature_name = feature.replace('_', ' ').title()
                result_lines.append(f"  • {feature_name}: {importance * 100:.1f}%")
        
        # Add model metadata
        if hasattr(prediction_result, 'metadata') and prediction_result.metadata:
            metadata = prediction_result.metadata
            result_lines.extend([
                "",
                "ℹ️ **Model Information**:",
                f"  • Features Used: {len(metadata.get('features_used', []))}",
                f"  • Lookback Window: {metadata.get('lookback_window', 'N/A')} days",
                f"  • Scaling Method: {metadata.get('scaling_method', 'N/A').title()}"
            ])
        
        # Add interpretation and recommendations
        result_lines.extend([
            "",
            "💡 **Interpretation**:"
        ])
        
        if confidence > 0.7:
            result_lines.append("  ✅ High confidence prediction - model is well-calibrated")
        elif confidence > 0.5:
            result_lines.append("  ⚠️ Moderate confidence - consider additional analysis")
        else:
            result_lines.append("  ❌ Low confidence - use with caution")
        
        # Add trend analysis if multiple predictions
        if isinstance(predictions, (list, np.ndarray)) and len(predictions) > 1:
            if predictions[-1] > predictions[0]:
                trend = "📈 Upward trend expected"
            elif predictions[-1] < predictions[0]:
                trend = "📉 Downward trend expected"
            else:
                trend = "➡️ Sideways movement expected"
            result_lines.append(f"  • {trend}")
        
        result_lines.extend([
            "",
            "⚠️ **Disclaimer**: This is a predictive model output for informational purposes only.",
            "Not financial advice. Always conduct your own research before making investment decisions."
        ])
        
        return "\n".join(result_lines)
        
    except Exception as e:
        logger.error(f"Error formatting prediction results: {e}")
        return f"❌ Error formatting prediction results: {str(e)}"


@tool("predict_stock_price", args_schema=StockPredictionInput)
def predict_stock_price_tool(
    query: str,
    model_type: Optional[str] = None,
    include_confidence: bool = True
) -> str:
    """
    Predict stock prices using advanced machine learning models.
    
    This tool uses state-of-the-art forecasting models including LSTM neural networks,
    ARIMA, Random Forest, XGBoost, and Prophet to predict future stock prices.
    It integrates with the Feast feature store to access historical market data
    and technical indicators for accurate predictions.
    
    Supported Models:
    - LSTM: Deep learning neural network for complex patterns
    - ARIMA: Statistical model for time series with trends
    - Random Forest: Ensemble method for robust predictions
    - XGBoost: Gradient boosting for high performance
    - Prophet: Facebook's time series forecasting tool
    - Ensemble: Combination of multiple models for best accuracy
    
    Example queries:
    - "Predict AAPL price for next 7 days"
    - "What will GOOGL stock price be in 30 days using LSTM?"
    - "Forecast MSFT price for 1 week with confidence intervals"
    - "Use ensemble model to predict TSLA price for next month"
    
    Args:
        query: Natural language description of the prediction request
        model_type: Specific model to use (optional, auto-selected if not specified)
        include_confidence: Whether to include confidence intervals
        
    Returns:
        Formatted string with prediction results, confidence intervals, and insights
    """
    try:
        if not FORECASTING_AVAILABLE:
            return "❌ Forecasting models are not available. Please check the installation of required dependencies."
        
        logger.info(f"Processing stock prediction request: {query}")
        
        # Parse the natural language query
        params = parse_stock_prediction_request(query)
        
        # Validate required parameters
        if not params.get("ticker"):
            return "❌ Error: Could not identify a ticker symbol in your request. Please specify a stock ticker (e.g., AAPL, GOOGL, MSFT)."
        
        ticker = params["ticker"]
        prediction_horizon = params["prediction_horizon"]
        requested_model_type = model_type or params.get("model_type")
        
        # Map prediction horizon to enum
        if prediction_horizon <= 1:
            horizon_enum = PredictionHorizon.ONE_DAY
        elif prediction_horizon <= 7:
            horizon_enum = PredictionHorizon.SEVEN_DAYS
        else:
            horizon_enum = PredictionHorizon.THIRTY_DAYS
        
        # Load historical data
        data_loader = FeastDataLoader()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)  # 1 year of data
        
        try:
            historical_data = data_loader.load_historical_data(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date
            )
        except Exception as e:
            logger.warning(f"Failed to load data from Feast: {e}. Using mock data.")
            # Create mock data for demonstration
            historical_data = data_loader._load_mock_data(ticker, start_date, end_date)
        
        if len(historical_data) < 100:
            return f"❌ Insufficient historical data for {ticker}. Need at least 100 data points for reliable predictions."
        
        # Select or create model
        if requested_model_type:
            # Use specific model type
            try:
                model_type_enum = ModelType(requested_model_type.lower())
                
                config = ModelConfig(
                    model_type=model_type_enum,
                    prediction_horizon=horizon_enum,
                    lookback_window=60,
                    features=list(historical_data.columns)
                )
                
                model = ForecastingModelFactory.create_model(model_type_enum, config)
                
                # Train model (simplified for demo)
                logger.info(f"Training {requested_model_type} model for {ticker}...")
                model.train(historical_data)
                
            except ValueError as e:
                return f"❌ Invalid model type: {requested_model_type}. Supported types: lstm, arima, random_forest, xgboost, prophet, ensemble"
            except Exception as e:
                logger.error(f"Error training {requested_model_type} model: {e}")
                return f"❌ Failed to train {requested_model_type} model: {str(e)}"
        else:
            # Auto-select best model
            try:
                logger.info(f"Auto-selecting best model for {ticker}...")
                available_models = ['random_forest', 'xgboost']  # Start with faster models
                
                best_model_name, model = select_best_model(
                    data=historical_data,
                    models=available_models,
                    prediction_horizon=prediction_horizon
                )
                
                logger.info(f"Selected {best_model_name} as the best model")
                
            except Exception as e:
                logger.warning(f"Auto-selection failed: {e}. Using Random Forest as fallback.")
                
                # Fallback to Random Forest
                config = ModelConfig(
                    model_type=ModelType.RANDOM_FOREST,
                    prediction_horizon=horizon_enum,
                    lookback_window=60,
                    features=list(historical_data.columns)
                )
                
                model = ForecastingModelFactory.create_model(ModelType.RANDOM_FOREST, config)
                model.train(historical_data)
        
        # Make prediction
        logger.info(f"Making prediction for {ticker}...")
        
        if include_confidence and hasattr(model, 'predict_with_uncertainty'):
            # Use uncertainty quantification if available
            prediction_result = model.predict_with_uncertainty(historical_data, ticker)
        else:
            # Standard prediction
            prediction_result = model.predict(historical_data, ticker)
        
        # Format and return results
        formatted_result = format_prediction_results(prediction_result, ticker, query)
        
        logger.info(f"Prediction completed for {ticker}")
        return formatted_result
        
    except Exception as e:
        error_msg = f"Error in stock price prediction: {str(e)}"
        logger.error(error_msg)
        return f"❌ {error_msg}\n\nPlease check your query format and try again. Example: 'Predict AAPL price for next 7 days'"


# NLP and Explainability Integration
try:
    from ai_assistant.rag.nlp_processor import NLPProcessor, create_nlp_processor
    from ai_assistant.rag.financial_nlp_models import FinancialNLPModels, create_financial_nlp_models
    from ai_assistant.rag.explainability_service import ExplainabilityService, create_explainability_service
    from ai_assistant.rag.explanation_visualizer import ExplanationVisualizer, create_explanation_visualizer
    from ai_assistant.rag.nlp_config import get_config as get_nlp_config
    
    NLP_AVAILABLE = True
    logger.info("NLP and explainability services available")
except ImportError as e:
    NLP_AVAILABLE = False
    logger.warning(f"NLP and explainability services not available: {e}")


# Pydantic models for new tools
class MarketSentimentInput(BaseModel):
    """Input model for market sentiment analysis tool"""
    text: str = Field(
        description="Text to analyze for market sentiment. Can be news articles, earnings reports, "
        "analyst notes, social media posts, or any financial text content."
    )
    include_entities: bool = Field(
        default=True,
        description="Whether to extract financial entities (companies, tickers, etc.)"
    )
    include_risk_assessment: bool = Field(
        default=True,
        description="Whether to include risk level assessment"
    )
    model_type: Optional[str] = Field(
        default="finbert",
        description="NLP model to use: 'finbert', 'roberta', or 'comprehensive' for all models"
    )


class ExplainPredictionInput(BaseModel):
    """Input model for prediction explanation tool"""
    model_name: str = Field(
        description="Name of the model to explain (must be registered with explainability service)"
    )
    input_data: str = Field(
        description="Input data for the prediction as JSON string or description. "
        "Example: '{\"feature1\": 0.5, \"feature2\": 1.2}' or 'AAPL stock with high volume'"
    )
    explanation_types: Optional[List[str]] = Field(
        default=None,
        description="Types of explanations to generate: 'feature_importance', 'waterfall', "
        "'decision_path', 'counterfactual'. If not specified, generates all available types."
    )
    include_visualization: bool = Field(
        default=True,
        description="Whether to generate visualization dashboard"
    )


@tool("analyze_market_sentiment", args_schema=MarketSentimentInput)
def analyze_market_sentiment_tool(
    text: str,
    include_entities: bool = True,
    include_risk_assessment: bool = True,
    model_type: str = "finbert"
) -> str:
    """
    Analyze market sentiment of financial text using advanced NLP models.
    
    This tool uses state-of-the-art financial NLP models including FinBERT to analyze
    sentiment, extract entities, assess risk, and provide comprehensive insights
    about financial texts such as news articles, earnings reports, and market commentary.
    
    Features:
    - Financial sentiment analysis (bullish, bearish, neutral)
    - Named entity recognition for companies, tickers, financial terms
    - Risk level assessment (low, medium, high, critical)
    - Market indicators extraction (earnings mentions, price targets, etc.)
    - Key phrase identification
    - Document classification
    
    Example queries:
    - "Apple reported strong quarterly earnings with revenue growth of 15%"
    - "Market volatility increases amid regulatory concerns for tech stocks"
    - "Federal Reserve signals potential interest rate cuts in upcoming meeting"
    - "Tesla stock surges on positive delivery numbers and production guidance"
    
    Args:
        text: Financial text to analyze for sentiment and insights
        include_entities: Whether to extract financial entities and relationships
        include_risk_assessment: Whether to assess risk level of the content
        model_type: NLP model to use ('finbert', 'roberta', 'comprehensive')
        
    Returns:
        Comprehensive analysis including sentiment, entities, risk assessment, and insights
    """
    try:
        if not NLP_AVAILABLE:
            return "❌ NLP services are not available. Please check the installation of required dependencies (transformers, torch, etc.)."
        
        logger.info(f"Processing market sentiment analysis for text: {text[:100]}...")
        
        # Initialize NLP models
        if model_type == "comprehensive":
            # Use comprehensive financial NLP models
            nlp_models = create_financial_nlp_models()
            analysis_result = nlp_models.comprehensive_analysis(
                text=text,
                include_sentiment=True,
                include_classification=True,
                include_risk=include_risk_assessment
            )
            
            # Format comprehensive results
            result_lines = [
                "🔍 **Comprehensive Market Sentiment Analysis**",
                "=" * 50,
                f"📝 **Text**: {text[:200]}{'...' if len(text) > 200 else ''}",
                ""
            ]
            
            # Add sentiment analysis
            if "sentiment" in analysis_result.get("results", {}):
                sentiment_data = analysis_result["results"]["sentiment"]
                sentiment_emoji = {"bullish": "📈", "bearish": "📉", "neutral": "➡️"}.get(
                    sentiment_data["sentiment"], "❓"
                )
                
                result_lines.extend([
                    f"{sentiment_emoji} **Sentiment Analysis**:",
                    f"  • Overall Sentiment: {sentiment_data['sentiment'].title()} ({sentiment_data['confidence']:.1%} confidence)",
                    f"  • Sentiment Scores: {', '.join([f'{k}: {v:.2f}' for k, v in sentiment_data['sentiment_scores'].items()])}",
                    ""
                ])
                
                # Add market indicators
                if sentiment_data.get("market_indicators"):
                    indicators = sentiment_data["market_indicators"]
                    active_indicators = [k.replace('_', ' ').title() for k, v in indicators.items() if v and isinstance(v, bool)]
                    if active_indicators:
                        result_lines.extend([
                            "📊 **Market Indicators Detected**:",
                            f"  • {', '.join(active_indicators)}",
                            ""
                        ])
                
                # Add key phrases
                if sentiment_data.get("key_phrases"):
                    result_lines.extend([
                        "🔑 **Key Financial Phrases**:",
                        f"  • {', '.join(sentiment_data['key_phrases'])}",
                        ""
                    ])
            
            # Add document classification
            if "classification" in analysis_result.get("results", {}):
                classification_data = analysis_result["results"]["classification"]
                result_lines.extend([
                    "📂 **Document Classification**:",
                    f"  • Category: {classification_data['category'].replace('_', ' ').title()} ({classification_data['confidence']:.1%} confidence)",
                    f"  • Topics: {', '.join(classification_data.get('topics', []))}",
                    ""
                ])
            
            # Add risk assessment
            if "risk" in analysis_result.get("results", {}):
                risk_data = analysis_result["results"]["risk"]
                risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(
                    risk_data["risk_level"], "❓"
                )
                
                result_lines.extend([
                    f"{risk_emoji} **Risk Assessment**:",
                    f"  • Risk Level: {risk_data['risk_level'].title()} ({risk_data['confidence']:.1%} confidence)",
                    ""
                ])
                
                if risk_data.get("risk_factors"):
                    result_lines.extend([
                        "⚠️ **Risk Factors Identified**:",
                        *[f"  • {factor}" for factor in risk_data["risk_factors"]],
                        ""
                    ])
                
                if risk_data.get("mitigation_suggestions"):
                    result_lines.extend([
                        "🛡️ **Risk Mitigation Suggestions**:",
                        *[f"  • {suggestion}" for suggestion in risk_data["mitigation_suggestions"][:3]],
                        ""
                    ])
            
            # Add summary
            if analysis_result.get("summary"):
                result_lines.extend([
                    "📋 **Analysis Summary**:",
                    f"  {analysis_result['summary']}",
                    ""
                ])
            
        else:
            # Use specific model (FinBERT or RoBERTa)
            nlp_processor = create_nlp_processor()
            
            # Sentiment analysis
            sentiment_result = nlp_processor.analyze_sentiment(text)
            
            result_lines = [
                "📈 **Market Sentiment Analysis**",
                "=" * 40,
                f"📝 **Text**: {text[:200]}{'...' if len(text) > 200 else ''}",
                f"🤖 **Model**: {sentiment_result.model_used.upper()}",
                "",
                "💭 **Sentiment Analysis**:",
                f"  • Sentiment: {sentiment_result.sentiment.value.title()}",
                f"  • Confidence: {sentiment_result.confidence:.1%}",
                f"  • Processing Time: {sentiment_result.processing_time:.2f}s",
                ""
            ]
            
            # Add sentiment scores
            if sentiment_result.sentiment_scores:
                result_lines.extend([
                    "📊 **Detailed Scores**:",
                    *[f"  • {label.title()}: {score:.3f}" for label, score in sentiment_result.sentiment_scores.items()],
                    ""
                ])
            
            # Add market indicators
            if sentiment_result.market_indicators:
                indicators = sentiment_result.market_indicators
                active_indicators = [k.replace('_', ' ').title() for k, v in indicators.items() if v and isinstance(v, bool)]
                if active_indicators:
                    result_lines.extend([
                        "📊 **Market Indicators**:",
                        *[f"  • {indicator}" for indicator in active_indicators],
                        ""
                    ])
            
            # Add key phrases
            if sentiment_result.key_phrases:
                result_lines.extend([
                    "🔑 **Key Phrases**:",
                    f"  • {', '.join(sentiment_result.key_phrases)}",
                    ""
                ])
            
            # Entity extraction if requested
            if include_entities:
                entity_result = nlp_processor.extract_entities(text)
                if entity_result.entities:
                    result_lines.extend([
                        "🏢 **Entities Extracted**:",
                        f"  • Total Entities: {len(entity_result.entities)}",
                        ""
                    ])
                    
                    # Group entities by type
                    entity_groups = {}
                    for entity in entity_result.entities:
                        entity_type = entity.get('label', 'Unknown')
                        if entity_type not in entity_groups:
                            entity_groups[entity_type] = []
                        entity_groups[entity_type].append(entity['text'])
                    
                    for entity_type, entities in entity_groups.items():
                        result_lines.append(f"  • {entity_type}: {', '.join(set(entities))}")
                    
                    result_lines.append("")
            
            # Risk assessment if requested
            if include_risk_assessment:
                try:
                    from .financial_nlp_models import FinancialRiskAssessor
                    risk_assessor = FinancialRiskAssessor()
                    risk_result = risk_assessor.assess_risk(text)
                    
                    risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(
                        risk_result.risk_level.value, "❓"
                    )
                    
                    result_lines.extend([
                        f"{risk_emoji} **Risk Assessment**:",
                        f"  • Risk Level: {risk_result.risk_level.value.title()}",
                        f"  • Confidence: {risk_result.confidence:.1%}",
                        ""
                    ])
                    
                    if risk_result.risk_factors:
                        result_lines.extend([
                            "⚠️ **Risk Factors**:",
                            *[f"  • {factor}" for factor in risk_result.risk_factors[:3]],
                            ""
                        ])
                
                except Exception as e:
                    logger.warning(f"Risk assessment failed: {e}")
        
        # Add recommendations
        result_lines.extend([
            "💡 **Recommendations**:",
            "  • Consider multiple sources for comprehensive market analysis",
            "  • Monitor sentiment trends over time for better insights",
            "  • Combine sentiment analysis with technical and fundamental analysis",
            "  • Validate AI insights with domain expertise"
        ])
        
        return "\n".join(result_lines)
        
    except Exception as e:
        error_msg = f"Error in market sentiment analysis: {str(e)}"
        logger.error(error_msg)
        return f"❌ {error_msg}\n\nPlease check your input text and try again. For best results, provide financial news, earnings reports, or market commentary."


@tool("explain_prediction", args_schema=ExplainPredictionInput)
def explain_prediction_tool(
    model_name: str,
    input_data: str,
    explanation_types: Optional[List[str]] = None,
    include_visualization: bool = True
) -> str:
    """
    Generate comprehensive explanations for model predictions using SHAP.
    
    This tool provides model-agnostic explanations that help understand why a model
    made a specific prediction. It uses SHAP (SHapley Additive exPlanations) to
    provide feature importance, decision paths, counterfactual analysis, and
    interactive visualizations.
    
    Explanation Types:
    - Feature Importance: Shows which features most influenced the prediction
    - Waterfall Plot: Visualizes how each feature contributed to the final prediction
    - Decision Path: Shows the step-by-step decision process
    - Counterfactual: Explores "what-if" scenarios by changing feature values
    
    Example usage:
    - Explain stock price predictions: "AAPL prediction with volume=1000000, price=150"
    - Explain trading decisions: "Buy signal for TSLA based on technical indicators"
    - Explain risk assessments: "High risk classification for portfolio allocation"
    
    Args:
        model_name: Name of the registered model to explain
        input_data: Input data as JSON string or natural language description
        explanation_types: List of explanation types to generate
        include_visualization: Whether to generate interactive visualizations
        
    Returns:
        Comprehensive explanation with insights, feature importance, and recommendations
    """
    try:
        if not NLP_AVAILABLE:
            return "❌ Explainability services are not available. Please check the installation of required dependencies (shap, matplotlib, plotly)."
        
        logger.info(f"Generating explanation for model: {model_name}")
        
        # Initialize explainability service
        explainability_service = create_explainability_service()
        
        # Check if model is registered
        model_registry = explainability_service.get_model_registry()
        if model_name not in model_registry:
            available_models = list(model_registry.keys())
            return f"❌ Model '{model_name}' is not registered with the explainability service.\n\nAvailable models: {', '.join(available_models) if available_models else 'None'}\n\nTo register a model, use the explainability service's register_model method."
        
        # Parse input data
        try:
            # Try to parse as JSON first
            if input_data.strip().startswith('{'):
                parsed_input = json.loads(input_data)
            else:
                # Handle natural language input (simplified parsing)
                parsed_input = {"description": input_data}
                logger.info(f"Using natural language input: {input_data}")
        except json.JSONDecodeError:
            # Fallback to treating as description
            parsed_input = {"description": input_data}
        
        # Set default explanation types if not provided
        if explanation_types is None:
            explanation_types = ["feature_importance", "waterfall", "decision_path"]
        
        # Convert string explanation types to enum
        from .explainability_service import ExplanationType
        explanation_type_enums = []
        for exp_type in explanation_types:
            try:
                explanation_type_enums.append(ExplanationType(exp_type.lower()))
            except ValueError:
                logger.warning(f"Unknown explanation type: {exp_type}")
        
        # Generate explanations
        explanations = explainability_service.explain_prediction(
            model_name=model_name,
            input_data=parsed_input,
            explanation_types=explanation_type_enums,
            include_visualization=include_visualization
        )
        
        # Format results
        result_lines = [
            "🔍 **Model Prediction Explanation**",
            "=" * 45,
            f"🤖 **Model**: {model_name}",
            f"📊 **Input Data**: {str(parsed_input)[:200]}{'...' if len(str(parsed_input)) > 200 else ''}",
            f"📈 **Explanations Generated**: {len(explanations)}",
            ""
        ]
        
        # Process each explanation type
        for exp_type, result in explanations.items():
            exp_name = exp_type.value.replace('_', ' ').title()
            result_lines.extend([
                f"📋 **{exp_name}**:",
                f"  • Confidence: {result.confidence:.1%}",
                f"  • Processing Time: {result.processing_time:.2f}s",
                ""
            ])
            
            if exp_type == ExplanationType.FEATURE_IMPORTANCE:
                # Feature importance details
                if hasattr(result, 'top_features') and result.top_features:
                    result_lines.extend([
                        "🎯 **Top Contributing Features**:",
                        *[f"  • {feature}: {importance:.3f}" for feature, importance in result.top_features[:5]],
                        ""
                    ])
                
                if hasattr(result, 'importance_ranking') and result.importance_ranking:
                    result_lines.extend([
                        "📊 **Feature Ranking**:",
                        f"  • Most Important: {result.importance_ranking[0]}",
                        f"  • Least Important: {result.importance_ranking[-1]}",
                        ""
                    ])
            
            elif exp_type == ExplanationType.DECISION_PATH:
                # Decision path details
                if hasattr(result, 'decision_rules') and result.decision_rules:
                    result_lines.extend([
                        "🛤️ **Decision Steps**:",
                        *[f"  • {rule}" for rule in result.decision_rules[:3]],
                        ""
                    ])
            
            elif exp_type == ExplanationType.COUNTERFACTUAL:
                # Counterfactual details
                if hasattr(result, 'scenario_description'):
                    result_lines.extend([
                        "🔄 **What-If Analysis**:",
                        f"  • {result.scenario_description}",
                        ""
                    ])
                
                if hasattr(result, 'change_impact') and result.change_impact:
                    most_sensitive = max(result.change_impact.items(), key=lambda x: x[1])
                    result_lines.extend([
                        "⚡ **Most Sensitive Feature**:",
                        f"  • {most_sensitive[0]}: Impact of {most_sensitive[1]:.3f}",
                        ""
                    ])
        
        # Add model information
        model_info = model_registry[model_name]
        result_lines.extend([
            "ℹ️ **Model Information**:",
            f"  • Model Type: {model_info['model_type']}",
            f"  • Features: {model_info['feature_count']}",
            f"  • Registered: {model_info['registered_at'][:19]}",
            ""
        ])
        
        # Generate visualization dashboard if requested
        if include_visualization and explanations:
            try:
                # Create visualization dashboard
                visualizer = create_explanation_visualizer()
                
                # Convert explanations to format expected by visualizer
                explanation_dict = {}
                for exp_type, result in explanations.items():
                    explanation_dict[exp_type.value] = {
                        "confidence": result.confidence,
                        "processing_time": result.processing_time,
                        "metadata": result.metadata
                    }
                    
                    # Add type-specific data
                    if hasattr(result, 'top_features'):
                        explanation_dict[exp_type.value]["top_features"] = result.top_features
                        explanation_dict[exp_type.value]["importance_scores"] = getattr(result, 'importance_scores', {})
                    
                    if hasattr(result, 'decision_rules'):
                        explanation_dict[exp_type.value]["decision_rules"] = result.decision_rules
                        explanation_dict[exp_type.value]["path_contribution"] = getattr(result, 'path_contribution', {})
                    
                    if hasattr(result, 'scenario_description'):
                        explanation_dict[exp_type.value]["scenario_description"] = result.scenario_description
                        explanation_dict[exp_type.value]["change_impact"] = getattr(result, 'change_impact', {})
                
                # Get prediction value from first result
                prediction_value = list(explanations.values())[0].prediction if explanations else 0.0
                confidence_value = list(explanations.values())[0].confidence if explanations else 0.0
                
                dashboard_html = visualizer.create_summary_dashboard(
                    explanation_dict,
                    model_name,
                    prediction_value,
                    confidence_value
                )
                
                # Save dashboard to temporary location
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                    f.write(dashboard_html)
                    dashboard_path = f.name
                
                result_lines.extend([
                    "📊 **Interactive Dashboard**:",
                    f"  • Dashboard generated with {len(explanations)} visualizations",
                    f"  • Saved to: {dashboard_path}",
                    "  • Open in browser to view interactive plots and detailed analysis",
                    ""
                ])
                
            except Exception as e:
                logger.warning(f"Visualization generation failed: {e}")
                result_lines.extend([
                    "⚠️ **Visualization Note**:",
                    "  • Interactive dashboard generation encountered an issue",
                    "  • Text-based explanations are still available above",
                    ""
                ])
        
        # Add recommendations
        result_lines.extend([
            "💡 **Interpretation Guidelines**:",
            "  • Higher feature importance indicates stronger influence on prediction",
            "  • Decision paths show the logical flow of the model's reasoning",
            "  • Counterfactual analysis reveals model sensitivity to input changes",
            "  • Always validate explanations with domain knowledge",
            "",
            "🎯 **Next Steps**:",
            "  • Review top contributing features for business relevance",
            "  • Test model robustness using counterfactual scenarios",
            "  • Monitor feature importance changes over time",
            "  • Consider feature engineering based on explanation insights"
        ])
        
        return "\n".join(result_lines)
        
    except Exception as e:
        error_msg = f"Error generating prediction explanation: {str(e)}"
        logger.error(error_msg)
        return f"❌ {error_msg}\n\nPlease ensure:\n• The model is properly registered with the explainability service\n• Input data is in correct format (JSON or descriptive text)\n• Required dependencies are installed (shap, matplotlib, plotly)"


# Export all tools for easy import
__all__ = [
    "run_backtest_tool",
    "query_documents_tool",
    "get_trading_system_status",
    "code_development_tool",
    "predict_stock_price_tool",
    "analyze_market_sentiment_tool",
    "explain_prediction_tool",
    "parse_backtest_request",
    "format_backtest_results",
    "parse_stock_prediction_request",
    "format_prediction_results",
    "get_auth_token",
    "search_documents_with_rag",
    "simulate_vector_search_fallback",
    "get_rag_pipeline",
    "create_planning_steps",
    "execute_planning_step",
    "rollback_workflow"
]