"""
Dependency Injection System

Centralized dependency management for the SkyFi MCP server with configuration
loading, service discovery, and runtime environment detection.

This module provides factory functions and dependency injection utilities
for managing service configurations, authentication, and runtime settings.
"""


import os
from typing import Dict, List, Optional, Type, Any, Union

from ..utils.environment import get_env_bool, get_env_list
from ..skyfi.config import SkyFiConfig
from ..osm.config import OSMConfig
from ..weather.config import WeatherConfig


def get_available_services() -> Dict[str, bool]:
    """
    Discover available services based on environment configuration.
    
    Checks for the presence of service-specific environment variables
    to determine which services should be initialized.
    
    Returns:
        Dictionary mapping service names to availability status
    """
    services = {}
    
    # SkyFi service - requires API URL at minimum
    services["skyfi"] = bool(os.getenv("SKYFI_API_URL") or os.getenv("SKYFI_URL"))
    
    # OSM service - always available (no authentication required)
    services["osm"] = True
    
    # Weather service - check for various weather API configurations
    weather_indicators = [
        "WEATHER_API_URL",
        "OPENWEATHER_API_KEY", 
        "WEATHER_API_KEY",
        "WEATHER_SERVICE_URL"
    ]
    services["weather"] = any(os.getenv(var) for var in weather_indicators)
    
    return services


def get_config_class(service_name: str) -> Type[Union[SkyFiConfig, OSMConfig, WeatherConfig]]:
    """
    Get the configuration class for a specific service.
    
    Args:
        service_name: Name of the service
        
    Returns:
        Configuration class for the service
        
    Raises:
        ValueError: If service name is not recognized
    """
    config_classes = {
        "skyfi": SkyFiConfig,
        "osm": OSMConfig,
        "weather": WeatherConfig
    }
    
    if service_name not in config_classes:
        raise ValueError(
            f"Unknown service '{service_name}'. "
            f"Available services: {list(config_classes.keys())}"
        )
    
    return config_classes[service_name]


def is_read_only_mode() -> bool:
    """
    Check if the server should run in read-only mode.
    
    Read-only mode can be enabled via:
    - READ_ONLY_MODE environment variable
    - MCP_READ_ONLY environment variable  
    - SKYFI_READ_ONLY environment variable
    
    Returns:
        True if read-only mode is enabled, False otherwise
    """
    read_only_vars = ["READ_ONLY_MODE", "MCP_READ_ONLY", "SKYFI_READ_ONLY"]
    return any(get_env_bool(var, False) for var in read_only_vars)


def get_enabled_tools() -> Optional[List[str]]:
    """
    Get the list of enabled tools from environment configuration.
    
    Tools can be specified via:
    - ENABLED_TOOLS environment variable (comma-separated)
    - MCP_ENABLED_TOOLS environment variable
    - SKYFI_ENABLED_TOOLS environment variable
    
    Returns:
        List of enabled tool names, or None if all tools should be enabled
    """
    tool_vars = ["ENABLED_TOOLS", "MCP_ENABLED_TOOLS", "SKYFI_ENABLED_TOOLS"]
    
    for var in tool_vars:
        tools = get_env_list(var)
        if tools:
            return tools
    
    return None


def get_transport_config() -> Dict[str, Any]:
    """
    Get MCP transport configuration from environment.
    
    Returns:
        Dictionary with transport configuration settings
    """
    return {
        "transport": os.getenv("MCP_TRANSPORT", "stdio"),
        "host": os.getenv("MCP_HOST", "localhost"),
        "port": int(os.getenv("MCP_PORT", "8000")),
        "cors_enabled": get_env_bool("MCP_CORS_ENABLED", False),
        "cors_origins": get_env_list("MCP_CORS_ORIGINS") or ["*"]
    }


def get_logging_config() -> Dict[str, Any]:
    """
    Get logging configuration from environment.
    
    Returns:
        Dictionary with logging configuration settings
    """
    return {
        "level": os.getenv("LOG_LEVEL", "INFO"),
        "format": os.getenv("LOG_FORMAT", "structured"),
        "output": os.getenv("LOG_OUTPUT", "stdout"),
        "file_path": os.getenv("LOG_FILE_PATH"),
        "max_file_size": int(os.getenv("LOG_MAX_FILE_SIZE", "10485760")),  # 10MB
        "backup_count": int(os.getenv("LOG_BACKUP_COUNT", "5"))
    }


def get_security_config() -> Dict[str, Any]:
    """
    Get security configuration from environment.
    
    Returns:
        Dictionary with security settings
    """
    return {
        "rate_limit_enabled": get_env_bool("RATE_LIMIT_ENABLED", False),
        "rate_limit_requests": int(os.getenv("RATE_LIMIT_REQUESTS", "100")),
        "rate_limit_window": int(os.getenv("RATE_LIMIT_WINDOW", "60")),
        "require_auth": get_env_bool("REQUIRE_AUTH", False),
        "auth_header_name": os.getenv("AUTH_HEADER_NAME", "Authorization"),
        "api_key_header_name": os.getenv("API_KEY_HEADER_NAME", "X-API-Key")
    }


def get_performance_config() -> Dict[str, Any]:
    """
    Get performance and resource configuration from environment.
    
    Returns:
        Dictionary with performance settings
    """
    return {
        "max_concurrent_requests": int(os.getenv("MAX_CONCURRENT_REQUESTS", "10")),
        "request_timeout": int(os.getenv("REQUEST_TIMEOUT", "30")),
        "connection_pool_size": int(os.getenv("CONNECTION_POOL_SIZE", "10")),
        "cache_enabled": get_env_bool("CACHE_ENABLED", True),
        "cache_ttl": int(os.getenv("CACHE_TTL", "300")),  # 5 minutes
        "metrics_enabled": get_env_bool("METRICS_ENABLED", False)
    }


def validate_environment() -> Dict[str, Any]:
    """
    Validate the current environment configuration.
    
    Performs comprehensive validation of:
    - Required environment variables
    - Service configurations  
    - Authentication settings
    - Network and security settings
    
    Returns:
        Dictionary with validation results and any issues found
    """
    validation_result = {
        "valid": True,
        "warnings": [],
        "errors": [],
        "services": {},
        "configuration": {}
    }
    
    # Validate service configurations
    available_services = get_available_services()
    
    for service_name, is_available in available_services.items():
        service_validation = {"available": is_available, "configured": False, "issues": []}
        
        if is_available:
            try:
                config_class = get_config_class(service_name)
                config = config_class.from_env()
                
                # Check if service is properly configured
                if hasattr(config, 'is_auth_configured'):
                    service_validation["configured"] = config.is_auth_configured()
                    
                    if not service_validation["configured"] and service_name != "osm":
                        service_validation["issues"].append("Authentication not configured")
                        validation_result["warnings"].append(
                            f"{service_name.title()} service available but not authenticated"
                        )
                else:
                    service_validation["configured"] = True
                    
            except Exception as e:
                service_validation["issues"].append(str(e))
                validation_result["errors"].append(f"Failed to load {service_name} config: {e}")
                validation_result["valid"] = False
        
        validation_result["services"][service_name] = service_validation
    
    # Validate transport configuration
    transport_config = get_transport_config()
    if transport_config["transport"] not in ["stdio", "streamable-http", "sse"]:
        validation_result["errors"].append(f"Invalid transport: {transport_config['transport']}")
        validation_result["valid"] = False
    
    # Check for common configuration issues
    if is_read_only_mode() and not any(available_services.values()):
        validation_result["warnings"].append(
            "Read-only mode enabled but no services available"
        )
    
    enabled_tools = get_enabled_tools()
    if enabled_tools and not enabled_tools:
        validation_result["warnings"].append("Enabled tools list is empty")
    
    # Validate security configuration
    security_config = get_security_config()
    if security_config["require_auth"] and not any(
        s["configured"] for s in validation_result["services"].values()
    ):
        validation_result["errors"].append(
            "Authentication required but no services are authenticated"
        )
        validation_result["valid"] = False
    
    validation_result["configuration"] = {
        "transport": transport_config,
        "security": security_config,
        "performance": get_performance_config(),
        "logging": get_logging_config()
    }
    
    return validation_result


def create_service_context_factory():
    """
    Create a factory function for service contexts.
    
    This provides a centralized way to create service-specific contexts
    with proper dependency injection and configuration.
    
    Returns:
        Factory function for creating service contexts
    """
    def factory(service_name: str, main_context):
        """Create a service context for the specified service."""
        from .context import SkyFiContext, OSMContext, WeatherContext
        
        context_classes = {
            "skyfi": SkyFiContext,
            "osm": OSMContext,
            "weather": WeatherContext
        }
        
        if service_name not in context_classes:
            raise ValueError(f"Unknown service: {service_name}")
        
        context_class = context_classes[service_name]
        return context_class(main_context=main_context)
    
    return factory


# Create the service context factory instance
create_service_context = create_service_context_factory()


def get_environment_summary() -> Dict[str, Any]:
    """
    Get a comprehensive summary of the current environment configuration.
    
    Useful for debugging, monitoring, and configuration validation.
    
    Returns:
        Dictionary with environment summary
    """
    return {
        "services": get_available_services(),
        "read_only_mode": is_read_only_mode(),
        "enabled_tools": get_enabled_tools(),
        "transport": get_transport_config(),
        "security": get_security_config(),
        "performance": get_performance_config(),
        "logging": get_logging_config(),
        "validation": validate_environment()
    }