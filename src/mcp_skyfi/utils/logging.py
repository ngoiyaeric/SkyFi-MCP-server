"""
Logging Configuration

Structured logging setup for the SkyFi MCP server with support for
different output formats, log levels, and monitoring integration.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, Optional

try:
    import structlog
    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False


def configure_logging(
    level: str = "INFO",
    format_type: str = "structured",
    output: str = "stdout",
    file_path: Optional[str] = None,
    max_file_size: int = 10485760,  # 10MB
    backup_count: int = 5
) -> None:
    """
    Configure logging for the SkyFi MCP server.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        format_type: Format type (structured, json, simple)
        output: Output destination (stdout, stderr, file)
        file_path: Path for file output
        max_file_size: Maximum log file size in bytes
        backup_count: Number of backup files to keep
    """
    
    # Convert string level to logging constant
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure root logger
    logging.root.setLevel(log_level)
    
    # Clear any existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Create formatter based on type
    if format_type == "structured" and HAS_STRUCTLOG:
        configure_structured_logging(level)
    else:
        configure_standard_logging(level, format_type, output, file_path, max_file_size, backup_count)
    
    # Configure specific loggers
    configure_logger_levels()
    
    # Log startup message
    logger = logging.getLogger("mcp-skyfi.logging")
    logger.info(f"Logging configured: level={level}, format={format_type}, output={output}")


def configure_structured_logging(level: str) -> None:
    """Configure structured logging with structlog."""
    
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Add handler to root logger
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    logging.root.addHandler(handler)


def configure_standard_logging(
    level: str,
    format_type: str,
    output: str,
    file_path: Optional[str],
    max_file_size: int,
    backup_count: int
) -> None:
    """Configure standard Python logging."""
    
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Define formatters
    formatters = {
        "simple": logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ),
        "detailed": logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        ),
        "json": JsonFormatter() if format_type == "json" else logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    }
    
    formatter = formatters.get(format_type, formatters["simple"])
    
    # Create handler based on output type
    if output == "file" and file_path:
        handler = RotatingFileHandler(
            file_path, 
            maxBytes=max_file_size,
            backupCount=backup_count
        )
    elif output == "stderr":
        handler = logging.StreamHandler(sys.stderr)
    else:  # stdout (default)
        handler = logging.StreamHandler(sys.stdout)
    
    handler.setLevel(log_level)
    handler.setFormatter(formatter)
    
    logging.root.addHandler(handler)


def configure_logger_levels() -> None:
    """Configure specific logger levels for better control."""
    
    # Reduce noise from external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    # FastMCP and MCP related
    logging.getLogger("fastmcp").setLevel(logging.INFO)
    logging.getLogger("mcp").setLevel(logging.INFO)
    
    # Our application loggers
    logging.getLogger("mcp-skyfi").setLevel(logging.DEBUG)


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging without structlog."""
    
    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime
        
        log_entry = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, '__dict__'):
            extra_fields = {
                k: v for k, v in record.__dict__.items()
                if k not in {
                    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                    'filename', 'module', 'lineno', 'funcName', 'created',
                    'msecs', 'relativeCreated', 'thread', 'threadName',
                    'processName', 'process', 'stack_info', 'exc_info',
                    'exc_text', 'message'
                }
            }
            if extra_fields:
                log_entry["extra"] = extra_fields
        
        return json.dumps(log_entry)


def get_logger(name: str, **kwargs) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name
        **kwargs: Additional context for structured logging
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if HAS_STRUCTLOG and kwargs:
        # Return structured logger with bound context
        return structlog.get_logger(name).bind(**kwargs)
    
    return logger


def log_request(
    logger: logging.Logger,
    method: str,
    url: str,
    status_code: Optional[int] = None,
    duration_ms: Optional[float] = None,
    **kwargs
) -> None:
    """
    Log HTTP request information.
    
    Args:
        logger: Logger instance
        method: HTTP method
        url: Request URL
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        **kwargs: Additional context
    """
    context = {
        "method": method,
        "url": url,
        "status_code": status_code,
        "duration_ms": duration_ms,
        **kwargs
    }
    
    if status_code and status_code >= 400:
        logger.error(f"HTTP {method} {url} failed", extra=context)
    else:
        logger.info(f"HTTP {method} {url}", extra=context)


def log_tool_execution(
    logger: logging.Logger,
    tool_name: str,
    success: bool,
    duration_ms: Optional[float] = None,
    error: Optional[str] = None,
    **kwargs
) -> None:
    """
    Log tool execution information.
    
    Args:
        logger: Logger instance
        tool_name: Name of the executed tool
        success: Whether execution was successful
        duration_ms: Execution duration in milliseconds
        error: Error message if execution failed
        **kwargs: Additional context
    """
    context = {
        "tool_name": tool_name,
        "success": success,
        "duration_ms": duration_ms,
        **kwargs
    }
    
    if success:
        logger.info(f"Tool {tool_name} executed successfully", extra=context)
    else:
        context["error"] = error
        logger.error(f"Tool {tool_name} execution failed", extra=context)


def create_audit_logger(name: str = "mcp-skyfi.audit") -> logging.Logger:
    """
    Create a logger specifically for audit events.
    
    Args:
        name: Logger name
        
    Returns:
        Configured audit logger
    """
    audit_logger = logging.getLogger(name)
    
    # Audit logs should always be at INFO level or higher
    audit_logger.setLevel(logging.INFO)
    
    return audit_logger


def log_security_event(
    event_type: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log security-related events.
    
    Args:
        event_type: Type of security event
        user_id: User identifier
        ip_address: Client IP address
        details: Additional event details
    """
    audit_logger = create_audit_logger("mcp-skyfi.security")
    
    context = {
        "event_type": event_type,
        "user_id": user_id,
        "ip_address": ip_address,
        "details": details or {}
    }
    
    audit_logger.warning(f"Security event: {event_type}", extra=context)