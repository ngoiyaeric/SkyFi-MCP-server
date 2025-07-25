
import logging
import logging.config
import sys
from typing import Any, Dict, Optional

import structlog


def configure_logging(
    level: str = "INFO",
    format_type: str = "json",
    include_timestamp: bool = True,
    include_caller: bool = False,
    service_name: str = "mcp-skyfi"
) -> None:
    """
    Configure structured logging for the MCP server.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Format type (json, console, simple)
        include_timestamp: Whether to include timestamps
        include_caller: Whether to include caller information
        service_name: Service name for log context
    """
    # Convert string level to logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure standard logging
    logging.basicConfig(
        level=numeric_level,
        stream=sys.stdout,
        format="%(message)s"  # structlog will handle formatting
    )
    
    # Build processor chain
    processors = []
    
    # Filter by level
    processors.append(structlog.stdlib.filter_by_level)
    
    # Add logger name
    processors.append(structlog.stdlib.add_logger_name)
    
    # Add log level
    processors.append(structlog.stdlib.add_log_level)
    
    # Handle positional arguments
    processors.append(structlog.stdlib.PositionalArgumentsFormatter())
    
    # Add timestamp if requested
    if include_timestamp:
        processors.append(structlog.processors.TimeStamper(fmt="iso"))
    
    # Add caller info if requested
    if include_caller:
        processors.append(structlog.processors.StackInfoRenderer())
        processors.append(structlog.dev.set_exc_info)
    
    # Handle exceptions
    processors.append(structlog.processors.format_exc_info)
    
    # Unicode handling
    processors.append(structlog.processors.UnicodeDecoder())
    
    # Add log level info
    processors.append(structlog.processors.add_log_level)
    
    # Choose final processor based on format type
    if format_type == "json":
        processors.append(structlog.processors.JSONRenderer())
    elif format_type == "console":
        processors.append(
            structlog.dev.ConsoleRenderer(colors=True)
        )
    else:  # simple
        processors.append(
            structlog.processors.KeyValueRenderer(
                key_order=["timestamp", "level", "logger", "message"]
            )
        )
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Set up service context
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(service=service_name)
    
    # Configure specific loggers
    _configure_third_party_loggers(numeric_level)


def _configure_third_party_loggers(level: int) -> None:
    """Configure third-party library loggers."""
    # Reduce httpx logging verbosity
    logging.getLogger("httpx").setLevel(max(level, logging.WARNING))
    logging.getLogger("httpcore").setLevel(max(level, logging.WARNING))
    
    # Reduce uvicorn logging verbosity in production
    if level >= logging.INFO:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    
    # FastMCP logging
    logging.getLogger("fastmcp").setLevel(level)


def get_logger(name: str, **context: Any) -> structlog.BoundLogger:
    """
    Get a structured logger with optional context.
    
    Args:
        name: Logger name (usually __name__)
        **context: Additional context to bind to logger
        
    Returns:
        Bound structlog logger
    """
    logger = structlog.get_logger(name)
    if context:
        logger = logger.bind(**context)
    return logger


def log_function_call(
    logger: structlog.BoundLogger,
    function_name: str,
    args: Optional[Dict[str, Any]] = None,
    level: str = "DEBUG"
) -> None:
    """
    Log function call with arguments.
    
    Args:
        logger: Logger instance
        function_name: Name of function being called
        args: Function arguments (sensitive values should be pre-masked)
        level: Log level
    """
    log_level = getattr(logging, level.upper(), logging.DEBUG)
    
    if logger.isEnabledFor(log_level):
        log_args = args or {}
        getattr(logger, level.lower())(
            f"Calling {function_name}",
            function=function_name,
            args=log_args
        )


def log_api_request(
    logger: structlog.BoundLogger,
    method: str,
    url: str,
    status_code: Optional[int] = None,
    duration_ms: Optional[float] = None,
    **extra: Any
) -> None:
    """
    Log API request with structured data.
    
    Args:
        logger: Logger instance
        method: HTTP method
        url: Request URL (should be sanitized)
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        **extra: Additional context
    """
    log_data = {
        "event_type": "api_request",
        "method": method,
        "url": url,
        **extra
    }
    
    if status_code is not None:
        log_data["status_code"] = status_code
    if duration_ms is not None:
        log_data["duration_ms"] = round(duration_ms, 2)
    
    # Choose log level based on status code
    if status_code is None:
        level = "info"
    elif status_code < 400:
        level = "info"
    elif status_code < 500:
        level = "warning"
    else:
        level = "error"
    
    getattr(logger, level)("API request", **log_data)


def log_mcp_tool_execution(
    logger: structlog.BoundLogger,
    tool_name: str,
    params: Dict[str, Any],
    success: bool,
    duration_ms: float,
    error: Optional[str] = None
) -> None:
    """
    Log MCP tool execution with structured data.
    
    Args:
        logger: Logger instance
        tool_name: Name of MCP tool
        params: Tool parameters (sensitive values should be pre-masked)
        success: Whether execution was successful
        duration_ms: Execution duration in milliseconds
        error: Error message if failed
    """
    log_data = {
        "event_type": "mcp_tool_execution",
        "tool_name": tool_name,
        "params": params,
        "success": success,
        "duration_ms": round(duration_ms, 2)
    }
    
    if error:
        log_data["error"] = error
    
    level = "info" if success else "error"
    message = f"MCP tool {'completed' if success else 'failed'}: {tool_name}"
    
    getattr(logger, level)(message, **log_data)


def mask_sensitive_data(data: Dict[str, Any], sensitive_keys: Optional[list[str]] = None) -> Dict[str, Any]:
    """
    Mask sensitive data in dictionary for safe logging.
    
    Args:
        data: Data dictionary
        sensitive_keys: List of keys to mask (case-insensitive)
        
    Returns:
        Dictionary with sensitive values masked
    """
    if sensitive_keys is None:
        sensitive_keys = [
            "password", "passwd", "pwd",
            "secret", "key", "token", "auth",
            "api_key", "access_token", "refresh_token",
            "private_key", "client_secret"
        ]
    
    sensitive_keys_lower = [key.lower() for key in sensitive_keys]
    masked_data = {}
    
    for key, value in data.items():
        if any(sensitive in key.lower() for sensitive in sensitive_keys_lower):
            if isinstance(value, str) and len(value) > 4:
                masked_data[key] = "*" * (len(value) - 4) + value[-4:]
            else:
                masked_data[key] = "***"
        elif isinstance(value, dict):
            masked_data[key] = mask_sensitive_data(value, sensitive_keys)
        else:
            masked_data[key] = value
    
    return masked_data


class RequestLogger:
    """Helper class for request logging with timing."""
    
    def __init__(self, logger: structlog.BoundLogger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time: Optional[float] = None
    
    def __enter__(self):
        import time
        self.start_time = time.perf_counter()
        self.logger.debug(f"Starting {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            import time
            duration_ms = (time.perf_counter() - self.start_time) * 1000
            
            if exc_type is None:
                self.logger.info(
                    f"Completed {self.operation}",
                    duration_ms=round(duration_ms, 2)
                )
            else:
                self.logger.error(
                    f"Failed {self.operation}",
                    duration_ms=round(duration_ms, 2),
                    error=str(exc_val) if exc_val else str(exc_type)
                )


def log_security_event(
    event_type: str,
    ip_address: Optional[str] = None,
    user_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    level: str = "WARNING"
) -> None:
    """
    Log security events with structured data for monitoring and alerting.
    
    Args:
        event_type: Type of security event (auth_failure, rate_limit, etc.)
        ip_address: Client IP address
        user_id: User identifier if available
        details: Additional event details
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    security_logger = structlog.get_logger("mcp-skyfi.security")
    
    log_data = {
        "event_type": "security_event",
        "security_event_type": event_type,
        "timestamp": structlog.processors.TimeStamper(fmt="iso")(),
    }
    
    if ip_address:
        log_data["ip_address"] = ip_address
    if user_id:
        log_data["user_id"] = user_id
    if details:
        # Mask sensitive data in details
        log_data["details"] = mask_sensitive_data(details)
    
    # Log at appropriate level
    log_level = getattr(logging, level.upper(), logging.WARNING)
    getattr(security_logger, level.lower())(
        f"Security event: {event_type}",
        **log_data
    )


class PerformanceLogger:
    """Performance monitoring logger."""
    
    def __init__(self, logger: structlog.BoundLogger):
        self.logger = logger
    
    def log_timing(self, operation: str, duration_ms: float, **context: Any):
        """Log operation timing."""
        self.logger.info(
            f"Performance: {operation}",
            operation=operation,
            duration_ms=round(duration_ms, 2),
            **context
        )
    
    def log_memory_usage(self, operation: str, memory_mb: float, **context: Any):
        """Log memory usage."""
        self.logger.info(
            f"Memory: {operation}",
            operation=operation,
            memory_mb=round(memory_mb, 2),
            **context
        )
    
    def log_rate_limit(self, endpoint: str, limit: int, remaining: int, reset_time: Optional[str] = None):
        """Log rate limit status."""
        self.logger.info(
            f"Rate limit: {endpoint}",
            endpoint=endpoint,
            limit=limit,
            remaining=remaining,
            reset_time=reset_time
        )