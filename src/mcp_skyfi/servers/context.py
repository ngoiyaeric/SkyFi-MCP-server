"""
Main Application Context

Centralized context management for the SkyFi MCP server with dependency
injection, configuration management, and service coordination.

This module implements the context pattern for managing application-wide
state, configuration, and service instances across the request lifecycle.
"""


import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple
from threading import RLock
from copy import deepcopy

from ..skyfi.config import SkyFiConfig
from ..osm.config import OSMConfig  
from ..weather.config import WeatherConfig
from ..exceptions import SkyFiMCPError

logger = logging.getLogger("mcp-skyfi.context")


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
    
    # Thread Safety
    _context_lock: RLock = field(default_factory=RLock, init=False)
    """Lock for thread-safe context operations"""

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

    def get_effective_credentials(self, user_context: Optional[Dict[str, Any]] = None, service: Optional[str] = None) -> Dict[str, Any]:
        """
        Get effective credentials with 4-tier precedence hierarchy.
        
        Precedence Order:
        1. Client credentials (per-request user context)
        2. OAuth credentials (from user context or config)
        3. Server credentials (from service configuration)
        4. Environment credentials (fallback from config)
        
        Args:
            user_context: Per-request user authentication context
            service: Specific service name for service-specific credentials
            
        Returns:
            Dictionary containing effective credentials with metadata
            
        Raises:
            SkyFiMCPError: If no valid credentials are found
        """
        with self._context_lock:
            effective_user_context = user_context or self.user_context
            
            credentials = {
                "token": None,
                "type": None,
                "source": None,
                "service": service,
                "metadata": {},
                "precedence_level": 0
            }
            
            # Level 1: Client credentials (highest priority)
            client_creds = self._get_client_credentials(effective_user_context)
            if client_creds["token"]:
                credentials.update(client_creds)
                credentials["precedence_level"] = 1
                logger.debug(f"Using client credentials for {service or 'default'}")
                return credentials
            
            # Level 2: OAuth credentials
            oauth_creds = self._get_oauth_credentials(effective_user_context, service)
            if oauth_creds["token"]:
                credentials.update(oauth_creds)
                credentials["precedence_level"] = 2
                logger.debug(f"Using OAuth credentials for {service or 'default'}")
                return credentials
            
            # Level 3: Server credentials
            server_creds = self._get_server_credentials(service)
            if server_creds["token"]:
                credentials.update(server_creds)
                credentials["precedence_level"] = 3
                logger.debug(f"Using server credentials for {service or 'default'}")
                return credentials
            
            # Level 4: Environment credentials (fallback)
            env_creds = self._get_environment_credentials(service)
            if env_creds["token"]:
                credentials.update(env_creds)
                credentials["precedence_level"] = 4
                logger.debug(f"Using environment credentials for {service or 'default'}")
                return credentials
            
            # No credentials found
            logger.warning(f"No valid credentials found for service: {service or 'default'}")
            raise SkyFiMCPError(f"No valid credentials available for service: {service or 'default'}")
    
    def _get_client_credentials(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract client-provided credentials from user context."""
        credentials = {
            "token": None,
            "type": None,
            "source": "client",
            "metadata": {}
        }
        
        # Check for per-request authentication token
        auth_token = user_context.get("auth_token")
        auth_type = user_context.get("auth_type", "bearer")
        auth_metadata = user_context.get("auth_metadata", {})
        
        if auth_token:
            credentials["token"] = auth_token
            credentials["type"] = auth_type
            credentials["metadata"] = {
                "client_ip": user_context.get("client_ip"),
                "request_id": user_context.get("request_id"),
                "auth_source": auth_metadata.get("source"),
                "timestamp": user_context.get("timestamp")
            }
        
        return credentials
    
    def _get_oauth_credentials(self, user_context: Dict[str, Any], service: Optional[str]) -> Dict[str, Any]:
        """Extract OAuth credentials from user context or service config."""
        credentials = {
            "token": None,
            "type": "oauth",
            "source": "oauth",
            "metadata": {}
        }
        
        # Check user context for OAuth token first
        if user_context.get("oauth_access_token"):
            credentials["token"] = user_context["oauth_access_token"]
            credentials["metadata"] = {
                "scope": user_context.get("oauth_scope"),
                "expires_at": user_context.get("oauth_expires_at"),
                "user_id": user_context.get("user_id")
            }
            return credentials
        
        # Check service configuration for OAuth
        if service == "skyfi" and self.skyfi_config:
            if (self.skyfi_config.oauth_access_token and 
                self.skyfi_config.oauth_client_id):
                credentials["token"] = self.skyfi_config.oauth_access_token
                credentials["metadata"] = {
                    "client_id": self.skyfi_config.oauth_client_id,
                    "scope": self.skyfi_config.oauth_scope
                }
        
        return credentials
    
    def _get_server_credentials(self, service: Optional[str]) -> Dict[str, Any]:
        """Extract server-configured credentials."""
        credentials = {
            "token": None,
            "type": "server",
            "source": "server_config",
            "metadata": {}
        }
        
        if service == "skyfi" and self.skyfi_config:
            # Try API key first
            if self.skyfi_config.api_key:
                credentials["token"] = self.skyfi_config.api_key
                credentials["type"] = "api_key"
                credentials["metadata"] = {
                    "workspace": self.skyfi_config.default_workspace,
                    "rate_limit": self.skyfi_config.rate_limit
                }
            # Try personal token as fallback
            elif self.skyfi_config.personal_token:
                credentials["token"] = self.skyfi_config.personal_token
                credentials["type"] = "personal_token"
        
        elif service == "weather" and self.weather_config:
            # Weather service API key
            api_key = getattr(self.weather_config, 'api_key', None)
            if api_key:
                credentials["token"] = api_key
                credentials["type"] = "api_key"
        
        return credentials
    
    def _get_environment_credentials(self, service: Optional[str]) -> Dict[str, Any]:
        """Extract environment-based credentials as fallback."""
        import os
        
        credentials = {
            "token": None,
            "type": "environment",
            "source": "environment",
            "metadata": {}
        }
        
        if service == "skyfi":
            # Check environment variables
            env_token = (os.getenv("SKYFI_API_KEY") or 
                        os.getenv("SKYFI_OAUTH_ACCESS_TOKEN") or 
                        os.getenv("SKYFI_PERSONAL_TOKEN"))
            if env_token:
                credentials["token"] = env_token
                # Determine type based on which env var was found
                if os.getenv("SKYFI_API_KEY") == env_token:
                    credentials["type"] = "api_key"
                elif os.getenv("SKYFI_OAUTH_ACCESS_TOKEN") == env_token:
                    credentials["type"] = "oauth"
                else:
                    credentials["type"] = "personal_token"
        
        elif service == "weather":
            env_token = (os.getenv("WEATHER_API_KEY") or 
                        os.getenv("OPENWEATHER_API_KEY"))
            if env_token:
                credentials["token"] = env_token
                credentials["type"] = "api_key"
        
        return credentials
    
    def get_service_credentials(self, service: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get credentials specifically for a service with validation."""
        try:
            credentials = self.get_effective_credentials(user_context, service)
            
            # Validate credentials for service
            if not self._validate_credentials_for_service(credentials, service):
                raise SkyFiMCPError(f"Invalid credentials for service: {service}")
            
            return credentials
            
        except Exception as e:
            logger.error(f"Failed to get credentials for service {service}: {e}")
            raise
    
    def _validate_credentials_for_service(self, credentials: Dict[str, Any], service: str) -> bool:
        """Validate that credentials are appropriate for the service."""
        if not credentials.get("token"):
            return False
        
        credential_type = credentials.get("type")
        
        if service == "skyfi":
            # SkyFi accepts api_key, oauth, or personal_token
            return credential_type in ["api_key", "oauth", "personal_token", "bearer"]
        
        elif service == "weather":
            # Weather services typically use API keys
            return credential_type in ["api_key"]
        
        elif service == "osm":
            # OSM doesn't require authentication for basic operations
            return True
        
        return False
    
    def update_user_context_safe(self, updates: Dict[str, Any]) -> None:
        """Thread-safe update of user context."""
        with self._context_lock:
            # Create a deep copy to avoid mutation issues
            current_context = deepcopy(self.user_context)
            current_context.update(updates)
            self.user_context = current_context
            
            logger.debug(f"Updated user context with keys: {list(updates.keys())}")
    
    def get_credential_summary(self) -> Dict[str, Any]:
        """Get a summary of available credentials (for debugging/monitoring)."""
        summary = {
            "services": {},
            "user_context_available": bool(self.user_context),
            "timestamp": self.user_context.get("timestamp"),
            "client_ip": self.user_context.get("client_ip")
        }
        
        for service in ["skyfi", "weather", "osm"]:
            try:
                creds = self.get_effective_credentials(service=service)
                summary["services"][service] = {
                    "available": True,
                    "type": creds.get("type"),
                    "source": creds.get("source"),
                    "precedence_level": creds.get("precedence_level")
                }
            except Exception:
                summary["services"][service] = {
                    "available": False,
                    "type": None,
                    "source": None,
                    "precedence_level": 0
                }
        
        return summary
    
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