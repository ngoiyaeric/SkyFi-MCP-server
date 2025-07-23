"""
Custom Exception Hierarchy

Comprehensive exception system for the SkyFi MCP server with specific
error types for different layers and services.

Exception Hierarchy:
- SkyFiMCPError (base)
  - ConfigurationError
  - AuthenticationError  
  - ServiceError
    - SkyFiAPIError
    - OSMError
    - WeatherAPIError
  - ValidationError
  - NetworkError
  - ProcessingError
"""

from __future__ import annotations

from typing import Dict, Any, Optional


class SkyFiMCPError(Exception):
    """
    Base exception for all SkyFi MCP server errors.
    
    Provides structured error information with error codes,
    user-friendly messages, and debugging details.
    """
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "UNKNOWN_ERROR",
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}
        self.original_error = original_error
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "code": self.error_code,
            "message": str(self),
            "details": self.details
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.error_code}, message={str(self)})"


class ConfigurationError(SkyFiMCPError):
    """Configuration-related errors."""
    
    def __init__(
        self, 
        message: str, 
        config_key: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message, 
            error_code="CONFIGURATION_ERROR",
            details={"config_key": config_key} if config_key else None,
            **kwargs
        )


class AuthenticationError(SkyFiMCPError):
    """Authentication and authorization errors."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        auth_method: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            error_code="AUTHENTICATION_ERROR",
            details={"auth_method": auth_method} if auth_method else None,
            **kwargs
        )


class ValidationError(SkyFiMCPError):
    """Input validation errors."""
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        **kwargs
    ):
        details = {}
        if field_name:
            details["field"] = field_name
        if field_value is not None:
            details["value"] = str(field_value)
            
        super().__init__(
            message,
            error_code="VALIDATION_ERROR", 
            details=details if details else None,
            **kwargs
        )


class NetworkError(SkyFiMCPError):
    """Network and connectivity errors."""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        url: Optional[str] = None,
        **kwargs
    ):
        details = {}
        if status_code:
            details["status_code"] = status_code
        if url:
            details["url"] = url
            
        super().__init__(
            message,
            error_code="NETWORK_ERROR",
            details=details if details else None,
            **kwargs
        )


class ProcessingError(SkyFiMCPError):
    """Data processing and transformation errors."""
    
    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            error_code="PROCESSING_ERROR",
            details={"operation": operation} if operation else None,
            **kwargs
        )


# Service-specific exceptions
class ServiceError(SkyFiMCPError):
    """Base class for service-specific errors."""
    pass


class SkyFiAPIError(ServiceError):
    """SkyFi Platform API errors."""
    
    def __init__(
        self,
        message: str = "SkyFi API error",
        api_error_code: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            error_code="SKYFI_API_ERROR",
            details={"api_error_code": api_error_code} if api_error_code else None,
            **kwargs
        )


class SkyFiAuthenticationError(SkyFiAPIError):
    """SkyFi API authentication errors."""
    
    def __init__(self, message: str = "SkyFi authentication failed", **kwargs):
        super().__init__(
            message, 
            error_code="SKYFI_AUTH_ERROR",
            **kwargs
        )


class SkyFiNotFoundError(SkyFiAPIError):
    """SkyFi resource not found errors."""
    
    def __init__(
        self, 
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs
    ):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
            
        super().__init__(
            message,
            error_code="SKYFI_NOT_FOUND",
            details=details if details else None,
            **kwargs
        )


class SkyFiPermissionError(SkyFiAPIError):
    """SkyFi permission and authorization errors."""
    
    def __init__(
        self,
        message: str = "Insufficient permissions",
        required_permission: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            error_code="SKYFI_PERMISSION_ERROR",
            details={"required_permission": required_permission} if required_permission else None,
            **kwargs
        )


class OSMError(ServiceError):
    """OpenStreetMap service errors."""
    
    def __init__(self, message: str = "OSM service error", **kwargs):
        super().__init__(
            message,
            error_code="OSM_ERROR",
            **kwargs
        )


class WeatherAPIError(ServiceError):
    """Weather API service errors."""
    
    def __init__(self, message: str = "Weather API error", **kwargs):
        super().__init__(
            message,
            error_code="WEATHER_API_ERROR",
            **kwargs
        )


# Tool execution specific errors
class ToolExecutionError(SkyFiMCPError):
    """Tool execution errors."""
    
    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            error_code="TOOL_EXECUTION_ERROR",
            details={"tool_name": tool_name} if tool_name else None,
            **kwargs
        )


class ReadOnlyModeError(SkyFiMCPError):
    """Errors when attempting write operations in read-only mode."""
    
    def __init__(self, message: str = "Operation not allowed in read-only mode", **kwargs):
        super().__init__(
            message,
            error_code="READ_ONLY_MODE_ERROR", 
            **kwargs
        )


class RateLimitError(SkyFiMCPError):
    """Rate limiting errors."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        **kwargs
    ):
        super().__init__(
            message,
            error_code="RATE_LIMIT_ERROR",
            details={"retry_after": retry_after} if retry_after else None,
            **kwargs
        )


class QuotaExceededError(SkyFiMCPError):
    """API quota exceeded errors."""
    
    def __init__(
        self,
        message: str = "API quota exceeded",
        quota_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            error_code="QUOTA_EXCEEDED_ERROR",
            details={"quota_type": quota_type} if quota_type else None,
            **kwargs
        )