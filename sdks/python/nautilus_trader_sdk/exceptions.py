"""
Nautilus Trader SDK Exceptions

Custom exceptions for the Nautilus Trader Python SDK.
"""

from typing import Optional, Dict, Any

class NautilusTraderError(Exception):
    """Base exception for Nautilus Trader SDK"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message

class APIError(NautilusTraderError):
    """API-related errors"""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}
    
    def __str__(self) -> str:
        if self.status_code:
            return f"API Error [{self.status_code}]: {self.message}"
        return f"API Error: {self.message}"

class AuthenticationError(NautilusTraderError):
    """Authentication-related errors"""
    pass

class AuthorizationError(NautilusTraderError):
    """Authorization-related errors"""
    pass

class ValidationError(NautilusTraderError):
    """Input validation errors"""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        super().__init__(message)
        self.field = field
        self.value = value
    
    def __str__(self) -> str:
        if self.field:
            return f"Validation Error [{self.field}]: {self.message}"
        return f"Validation Error: {self.message}"

class NetworkError(NautilusTraderError):
    """Network-related errors"""
    pass

class TimeoutError(NautilusTraderError):
    """Request timeout errors"""
    pass

class RateLimitError(NautilusTraderError):
    """Rate limiting errors"""
    
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after
    
    def __str__(self) -> str:
        if self.retry_after:
            return f"Rate Limit Error: {self.message} (retry after {self.retry_after}s)"
        return f"Rate Limit Error: {self.message}"

class OrderError(NautilusTraderError):
    """Order-related errors"""
    
    def __init__(self, message: str, order_id: Optional[str] = None):
        super().__init__(message)
        self.order_id = order_id
    
    def __str__(self) -> str:
        if self.order_id:
            return f"Order Error [{self.order_id}]: {self.message}"
        return f"Order Error: {self.message}"

class PositionError(NautilusTraderError):
    """Position-related errors"""
    
    def __init__(self, message: str, symbol: Optional[str] = None):
        super().__init__(message)
        self.symbol = symbol
    
    def __str__(self) -> str:
        if self.symbol:
            return f"Position Error [{self.symbol}]: {self.message}"
        return f"Position Error: {self.message}"

class StrategyError(NautilusTraderError):
    """Strategy-related errors"""
    
    def __init__(self, message: str, strategy_id: Optional[str] = None):
        super().__init__(message)
        self.strategy_id = strategy_id
    
    def __str__(self) -> str:
        if self.strategy_id:
            return f"Strategy Error [{self.strategy_id}]: {self.message}"
        return f"Strategy Error: {self.message}"

class BacktestError(NautilusTraderError):
    """Backtest-related errors"""
    
    def __init__(self, message: str, backtest_id: Optional[str] = None):
        super().__init__(message)
        self.backtest_id = backtest_id
    
    def __str__(self) -> str:
        if self.backtest_id:
            return f"Backtest Error [{self.backtest_id}]: {self.message}"
        return f"Backtest Error: {self.message}"

class WebSocketError(NautilusTraderError):
    """WebSocket-related errors"""
    pass

class GraphQLError(NautilusTraderError):
    """GraphQL-related errors"""
    
    def __init__(self, message: str, errors: Optional[list] = None):
        super().__init__(message)
        self.errors = errors or []
    
    def __str__(self) -> str:
        if self.errors:
            error_messages = [str(error) for error in self.errors]
            return f"GraphQL Error: {self.message} - {'; '.join(error_messages)}"
        return f"GraphQL Error: {self.message}"

class WebhookError(NautilusTraderError):
    """Webhook-related errors"""
    
    def __init__(self, message: str, webhook_id: Optional[str] = None):
        super().__init__(message)
        self.webhook_id = webhook_id
    
    def __str__(self) -> str:
        if self.webhook_id:
            return f"Webhook Error [{self.webhook_id}]: {self.message}"
        return f"Webhook Error: {self.message}"

class ConfigurationError(NautilusTraderError):
    """Configuration-related errors"""
    pass

class DataError(NautilusTraderError):
    """Data-related errors"""
    pass

# Exception mapping for HTTP status codes
STATUS_CODE_EXCEPTIONS = {
    400: ValidationError,
    401: AuthenticationError,
    403: AuthorizationError,
    404: APIError,
    429: RateLimitError,
    500: APIError,
    502: NetworkError,
    503: NetworkError,
    504: TimeoutError
}

def create_exception_from_response(status_code: int, message: str, response_data: Optional[Dict] = None) -> NautilusTraderError:
    """Create appropriate exception based on HTTP status code"""
    exception_class = STATUS_CODE_EXCEPTIONS.get(status_code, APIError)
    
    if exception_class == RateLimitError:
        retry_after = None
        if response_data and 'retry_after' in response_data:
            retry_after = response_data['retry_after']
        return exception_class(message, retry_after=retry_after)
    elif exception_class == APIError:
        return exception_class(message, status_code=status_code, response_data=response_data)
    else:
        return exception_class(message)