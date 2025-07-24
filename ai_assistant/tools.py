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
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

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


def simulate_vector_search(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Simulate vector similarity search for documents
    This is a placeholder for future Qdrant integration
    
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
            "tags": ["moving_average", "crossover", "technical_analysis", "strategy"]
        },
        {
            "id": "doc_002", 
            "title": "Risk Management in Algorithmic Trading",
            "content": "Effective risk management is crucial for successful algorithmic trading. Key concepts include position sizing, stop losses, maximum drawdown limits, and portfolio diversification.",
            "category": "risk_management",
            "relevance_score": 0.88,
            "tags": ["risk_management", "position_sizing", "stop_loss", "drawdown"]
        },
        {
            "id": "doc_003",
            "title": "Backtesting Best Practices",
            "content": "Proper backtesting methodology is essential for validating trading strategies. Important considerations include avoiding look-ahead bias, accounting for transaction costs, and using out-of-sample testing.",
            "category": "backtesting",
            "relevance_score": 0.92,
            "tags": ["backtesting", "validation", "bias", "transaction_costs"]
        },
        {
            "id": "doc_004",
            "title": "Market Volatility Analysis",
            "content": "Understanding market volatility is key to successful trading. Volatility affects strategy performance, risk levels, and optimal position sizing. Common volatility measures include standard deviation and VIX.",
            "category": "market_analysis",
            "relevance_score": 0.85,
            "tags": ["volatility", "market_analysis", "VIX", "standard_deviation"]
        },
        {
            "id": "doc_005",
            "title": "Performance Metrics for Trading Strategies",
            "content": "Key performance metrics for evaluating trading strategies include Sharpe ratio, Calmar ratio, maximum drawdown, win rate, and profit factor. Each metric provides different insights into strategy performance.",
            "category": "performance_metrics",
            "relevance_score": 0.90,
            "tags": ["performance", "sharpe_ratio", "calmar_ratio", "metrics"]
        },
        {
            "id": "doc_006",
            "title": "Technical Indicators Overview",
            "content": "Technical indicators are mathematical calculations based on price and volume data. Popular indicators include RSI, MACD, Bollinger Bands, and moving averages. Each serves different analytical purposes.",
            "category": "technical_analysis",
            "relevance_score": 0.87,
            "tags": ["technical_indicators", "RSI", "MACD", "bollinger_bands"]
        },
        {
            "id": "doc_007",
            "title": "Portfolio Optimization Techniques",
            "content": "Portfolio optimization involves selecting the optimal mix of assets to maximize returns while minimizing risk. Modern Portfolio Theory and the Capital Asset Pricing Model are foundational concepts.",
            "category": "portfolio_management",
            "relevance_score": 0.83,
            "tags": ["portfolio_optimization", "modern_portfolio_theory", "CAPM", "diversification"]
        },
        {
            "id": "doc_008",
            "title": "High-Frequency Trading Strategies",
            "content": "High-frequency trading involves executing large numbers of orders at very high speeds. Strategies include market making, statistical arbitrage, and latency arbitrage. Technology and infrastructure are critical.",
            "category": "hft_strategies",
            "relevance_score": 0.78,
            "tags": ["high_frequency", "market_making", "arbitrage", "latency"]
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
    
