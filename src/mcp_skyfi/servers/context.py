"""
Main Application Context

Centralized context management for the SkyFi MCP server with dependency
injection, configuration management, and service coordination.

This module implements the context pattern for managing application-wide
state, configuration, and service instances across the request lifecycle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

from ..skyfi.config import SkyFiConfig
from ..osm.config import OSMConfig  
from ..weather.config import WeatherConfig


@dataclass
class MainAppContext:
    """
    Main application context containing all service configurations and runtime state.
    
    This context is created during server lifespan and passed through the MCP
    request handling pipeline. It provides centralized access to:
    
    - Service configurations and authentication status
    - Runtime settings (read-only mode, enabled tools)
    - Service availability status
    - Shared resources and connection pools
    """
    
    # Runtime Configuration
    read_only: bool = False
    """Enable read-only mode to disable all write operations"""
    
    enabled_tools: Optional[List[str]] = None
    """Whitelist of enabled tool names. If None, all tools are enabled"""
    
    # Service Status Tracking
    service_status: Dict[str, bool] = field(default_factory=dict)
    """Dictionary tracking which services are available and configured"""
    
    # Service Configurations
    skyfi_config: Optional[SkyFiConfig] = None
    """SkyFi Platform API configuration and authentication"""
    
    osm_config: Optional[OSMConfig] = None
    """OpenStreetMap service configuration"""
    
    weather_config: Optional[WeatherConfig] = None
    """Weather service configuration and API keys"""
    
    # Shared Resources
    user_context: Dict[str, Any] = field(default_factory=dict)
    """Per-request user context and authentication data"""
    
    request_metadata: Dict[str, Any] = field(default_factory=dict)
    """Request-specific metadata and tracking information"""

    def is_service_available(self, service_name: str) -> bool:
        """
        Check if a specific service is available and properly configured.
        
        Args:
            service_name: Name of the service ("skyfi", "osm", "weather")
            
        Returns:
            True if service is available, False otherwise
        """
        return self.service_status.get(service_name, False)

    def get_service_config(self, service_name: str) -> Optional[Any]:
        """
        Get configuration for a specific service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service configuration object or None if not available
        """
        config_attr = f"{service_name}_config"
        return getattr(self, config_attr, None)

    def is_tool_enabled(self, tool_name: str) -> bool:
        """
        Check if a specific tool is enabled in the current configuration.
        
        Args:
            tool_name: Name of the tool to check
            
        Returns:
            True if tool is enabled, False otherwise
        """
        if self.enabled_tools is None:
            return True  # All tools enabled by default
        return tool_name in self.enabled_tools

    def can_execute_write_operation(self, tool_name: str = "") -> bool:
        """
        Check if write operations are allowed in the current context.
        
        Args:
            tool_name: Optional tool name for specific checking
            
        Returns:
            True if write operations are allowed, False if read-only mode
        """
        if self.read_only:
            return False
        return True

    def get_available_services(self) -> List[str]:
        """
        Get list of all available and configured services.
        
        Returns:
            List of service names that are properly configured
        """
        return [name for name, available in self.service_status.items() if available]

    def get_service_summary(self) -> Dict[str, Any]:
        """
        Get a summary of service availability and configuration status.
        
        Returns:
            Dictionary with service status and configuration summary
        """
        return {
            "available_services": self.get_available_services(),
            "total_services": len(self.service_status),
            "read_only_mode": self.read_only,
            "enabled_tools_count": len(self.enabled_tools) if self.enabled_tools else "all",
            "configurations": {
                "skyfi": bool(self.skyfi_config),
                "osm": bool(self.osm_config), 
                "weather": bool(self.weather_config)
            }
        }

    def update_user_context(self, **kwargs: Any) -> None:
        """
        Update user context with additional information.
        
        This is typically called by middleware to add authentication
        information, user permissions, or request-specific data.
        """
        self.user_context.update(kwargs)

    def get_user_auth_token(self) -> Optional[str]:
        """
        Get the current user's authentication token.
        
        Returns:
            Authentication token if available, None otherwise
        """
        return self.user_context.get("auth_token")

    def get_user_auth_type(self) -> Optional[str]:
        """
        Get the current user's authentication method.
        
        Returns:
            Authentication type ("bearer", "api_key", etc.) or None
        """
        return self.user_context.get("auth_type")

    def has_user_auth(self) -> bool:
        """
        Check if the current request has user authentication.
        
        Returns:
            True if user authentication is available, False otherwise
        """
        return bool(self.get_user_auth_token())

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"MainAppContext("
            f"services={len(self.get_available_services())}, "
            f"read_only={self.read_only}, "
            f"user_auth={self.has_user_auth()})"
        )


@dataclass
class ServiceContext:
    """
    Base context for individual service modules.
    
    This provides a service-specific view of the main application context
    with additional service-specific state and configuration.
    """
    
    main_context: MainAppContext
    """Reference to the main application context"""
    
    service_name: str
    """Name of the current service"""
    
    def __post_init__(self):
        """Validate service context after initialization."""
        if not self.main_context.is_service_available(self.service_name):
            raise ValueError(f"Service '{self.service_name}' is not available")

    @property
    def config(self) -> Optional[Any]:
        """Get the configuration for this service."""
        return self.main_context.get_service_config(self.service_name)

    @property
    def is_read_only(self) -> bool:
        """Check if the service is in read-only mode."""
        return self.main_context.read_only

    @property  
    def user_context(self) -> Dict[str, Any]:
        """Get user context from the main context."""
        return self.main_context.user_context

    def can_execute_tool(self, tool_name: str, is_write_operation: bool = False) -> bool:
        """
        Check if a tool can be executed in the current context.
        
        Args:
            tool_name: Name of the tool
            is_write_operation: Whether the tool performs write operations
            
        Returns:
            True if tool can be executed, False otherwise
        """
        # Check if tool is enabled
        if not self.main_context.is_tool_enabled(tool_name):
            return False
            
        # Check read-only mode for write operations
        if is_write_operation and not self.main_context.can_execute_write_operation():
            return False
            
        return True


@dataclass
class SkyFiContext(ServiceContext):
    """Context specific to SkyFi service operations."""
    
    service_name: str = field(default="skyfi", init=False)
    
    @property
    def skyfi_config(self) -> Optional[SkyFiConfig]:
        """Get SkyFi-specific configuration."""
        return self.config


@dataclass 
class OSMContext(ServiceContext):
    """Context specific to OpenStreetMap service operations."""
    
    service_name: str = field(default="osm", init=False)
    
    @property
    def osm_config(self) -> Optional[OSMConfig]:
        """Get OSM-specific configuration.""" 
        return self.config


@dataclass
class WeatherContext(ServiceContext):
    """Context specific to Weather service operations."""
    
    service_name: str = field(default="weather", init=False)
    
    @property
    def weather_config(self) -> Optional[WeatherConfig]:
        """Get Weather-specific configuration."""
        return self.config