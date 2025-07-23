# Service Mounting and Dependency Injection Patterns

## Overview

This document defines comprehensive patterns for service mounting and dependency injection in the SkyFi MCP server, ensuring clean separation of concerns, proper resource management, and flexible service configuration.

## 1. Service Mounting Architecture

### 1.1 Main Server with Service Mounting

```python
# servers/main.py
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import JSONResponse
from starlette.requests import Request

from .context import MainAppContext
from .dependencies import ServiceDependencyManager
from .middleware import UserTokenMiddleware, ServiceContextMiddleware
from ..exceptions import MCPError

logger = logging.getLogger("mcp-skyfi.server.main")

class SkyFiMCPServer(FastMCP[MainAppContext]):
    """
    Main MCP server with multi-service support, tool filtering, and dependency injection.
    
    Features:
    - Dynamic service mounting based on available configurations
    - Multi-level tool filtering (availability, permissions, read-only mode)
    - Request context management with user authentication
    - Service health monitoring and status reporting
    - Graceful degradation when services are unavailable
    """

    def __init__(self, name: str = "SkyFi MCP Server", **kwargs):
        super().__init__(name=name, **kwargs)
        self.dependency_manager = ServiceDependencyManager()
        self.mounted_services: Dict[str, List[str]] = {}  # Track mounted domains per service

    async def _mcp_list_tools(self) -> List[MCPTool]:
        """Override FastMCP's tool discovery with comprehensive filtering logic."""
        req_context = self._mcp_server.request_context
        if req_context is None or req_context.lifespan_context is None:
            logger.warning("Lifespan context not available during tool list")
            return []

        app_context = req_context.lifespan_context.get("app_lifespan_context")
        if not app_context:
            logger.error("Application context not found")
            return []

        # Get all tools from mounted services
        all_tools = await self.get_tools()
        filtered_tools = []

        for tool_name, tool_obj in all_tools.items():
            if self._should_include_tool(tool_name, tool_obj, app_context):
                filtered_tools.append(tool_obj.to_mcp_tool(name=tool_name))

        logger.info(f"Filtered {len(filtered_tools)} tools from {len(all_tools)} total")
        return filtered_tools

    def _should_include_tool(
        self, 
        tool_name: str, 
        tool_obj: Any, 
        context: MainAppContext
    ) -> bool:
        """
        Multi-level tool filtering logic.
        
        Filters applied:
        1. Explicit tool inclusion/exclusion list
        2. Read-only mode filtering for write operations
        3. Service availability and authentication status
        4. User permission levels
        5. Feature flag and A/B testing
        """
        tool_tags = getattr(tool_obj, 'tags', [])
        
        # 1. Explicit tool filtering
        if context.enabled_tools and tool_name not in context.enabled_tools:
            logger.debug(f"Tool {tool_name} not in enabled tools list")
            return False
        
        if context.disabled_tools and tool_name in context.disabled_tools:
            logger.debug(f"Tool {tool_name} explicitly disabled")
            return False

        # 2. Read-only mode filtering
        if context.read_only and "write" in tool_tags:
            logger.debug(f"Tool {tool_name} filtered due to read-only mode")
            return False

        # 3. Service availability filtering
        service_available = True
        for service_name in ["skyfi", "osm", "weather"]:
            if service_name in tool_tags:
                service_config = getattr(context, f"{service_name}_config", None)
                if not service_config:
                    logger.debug(f"Tool {tool_name} filtered - {service_name} not configured")
                    service_available = False
                    break

        if not service_available:
            return False

        # 4. User permission filtering (if user context available)
        user_permissions = context.get_user_permissions()
        required_permissions = self._get_tool_permissions(tool_obj)
        if required_permissions and not user_permissions.has_all(required_permissions):
            logger.debug(f"Tool {tool_name} filtered - insufficient permissions")
            return False

        # 5. Feature flag filtering
        if not context.is_feature_enabled(tool_name):
            logger.debug(f"Tool {tool_name} filtered - feature flag disabled")
            return False

        return True

    def _get_tool_permissions(self, tool_obj: Any) -> List[str]:
        """Extract required permissions from tool metadata."""
        # This would be implemented based on tool metadata or annotations
        return getattr(tool_obj, 'required_permissions', [])

    def mount_service_domains(self, service_name: str, available_domains: Dict[str, FastMCP]) -> None:
        """
        Mount all domains for a service.
        
        Args:
            service_name: Name of the service (skyfi, osm, weather)
            available_domains: Dictionary of domain_name -> FastMCP instances
        """
        if service_name not in self.mounted_services:
            self.mounted_services[service_name] = []

        for domain_name, domain_mcp in available_domains.items():
            mount_path = f"{service_name}.{domain_name}"
            self.mount(mount_path, domain_mcp)
            self.mounted_services[service_name].append(domain_name)
            logger.info(f"Mounted {service_name}.{domain_name} domain")

    def get_service_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all mounted services."""
        return {
            "server": {
                "name": self.name,
                "mounted_services": self.mounted_services,
                "total_services": len(self.mounted_services),
                "total_domains": sum(len(domains) for domains in self.mounted_services.values())
            },
            "services": self.dependency_manager.get_health_status(),
            "middleware": [
                "UserTokenMiddleware",
                "ServiceContextMiddleware"
            ]
        }

    def http_app(
        self,
        path: str | None = None,
        middleware: List[Middleware] | None = None,
        transport: str = "streamable-http",
    ) -> Starlette:
        """Create HTTP app with comprehensive middleware pipeline."""
        
        # Build middleware stack
        middleware_stack = [
            # User authentication extraction (highest priority)
            Middleware(UserTokenMiddleware),
            
            # Service context injection
            Middleware(ServiceContextMiddleware, server_ref=self),
            
            # Add any custom middleware
            *(middleware or [])
        ]

        return super().http_app(
            path=path,
            middleware=middleware_stack,
            transport=transport
        )

@asynccontextmanager
async def main_lifespan(app: SkyFiMCPServer) -> AsyncIterator[Dict[str, Any]]:
    """
    Server lifespan management with comprehensive service initialization.
    
    Handles:
    - Service configuration loading and validation
    - Service client initialization
    - Health checking and monitoring setup
    - Graceful shutdown procedures
    """
    logger.info("SkyFi MCP server lifespan starting...")
    
    try:
        # Initialize dependency manager
        dependency_manager = ServiceDependencyManager()
        await dependency_manager.initialize()
        
        # Load service configurations
        service_configs = await dependency_manager.load_all_configurations()
        
        # Initialize service clients
        service_clients = await dependency_manager.create_service_clients(service_configs)
        
        # Mount available service domains
        await mount_service_domains(app, dependency_manager, service_configs)
        
        # Create application context
        app_context = MainAppContext(
            dependency_manager=dependency_manager,
            service_configs=service_configs,
            service_clients=service_clients,
            read_only=dependency_manager.is_read_only_mode(),
            enabled_tools=dependency_manager.get_enabled_tools(),
            disabled_tools=dependency_manager.get_disabled_tools(),
        )
        
        # Perform health checks
        health_status = await dependency_manager.perform_health_checks()
        logger.info(f"Health check results: {health_status}")
        
        logger.info("SkyFi MCP server fully initialized")
        
        try:
            yield {"app_lifespan_context": app_context}
        finally:
            logger.info("SkyFi MCP server shutting down...")
            await dependency_manager.shutdown()
            
    except Exception as e:
        logger.error(f"Failed to initialize SkyFi MCP server: {e}")
        raise

async def mount_service_domains(
    app: SkyFiMCPServer,
    dependency_manager: ServiceDependencyManager,
    service_configs: Dict[str, Any]
) -> None:
    """Mount domains for all available services."""
    
    # Import service domains
    from ..services import get_available_domains
    
    for service_name, config in service_configs.items():
        available_domains = get_available_domains(service_name)
        if available_domains:
            app.mount_service_domains(service_name, available_domains)
            logger.info(f"Mounted {len(available_domains)} domains for {service_name}")
        else:
            logger.warning(f"No domains available for {service_name}")

# Create main server instance
main_mcp = SkyFiMCPServer(
    name="SkyFi MCP Server",
    lifespan=main_lifespan
)

# Add health check endpoint
@main_mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def health_check(request: Request) -> JSONResponse:
    """Comprehensive health check endpoint."""
    try:
        status = main_mcp.get_service_status()
        return JSONResponse({
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z",  # Would use actual timestamp
            "server": status["server"],
            "services": status["services"]
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse({
            "status": "unhealthy",
            "error": str(e)
        }, status_code=503)

# Add service status endpoint
@main_mcp.custom_route("/status", methods=["GET"], include_in_schema=False)
async def detailed_status(request: Request) -> JSONResponse:
    """Detailed service status for monitoring."""
    return JSONResponse(main_mcp.get_service_status())
```

## 2. Application Context and Dependency Management

### 2.1 Main Application Context

```python
# servers/context.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Set, TYPE_CHECKING
from ..models.permissions import UserPermissions, FeatureFlags

if TYPE_CHECKING:
    from .dependencies import ServiceDependencyManager
    from ..skyfi.config import SkyFiConfig
    from ..osm.config import OSMConfig
    from ..weather.config import WeatherConfig
    from ..skyfi.client import SkyFiClient
    from ..osm.client import OSMClient
    from ..weather.client import WeatherClient

@dataclass
class MainAppContext:
    """
    Main application context with comprehensive service and user management.
    
    This context provides:
    - Service configuration and client management
    - User authentication and permission handling
    - Feature flags and A/B testing support
    - Request-scoped data and caching
    - Cross-service coordination
    """
    
    # Core dependencies
    dependency_manager: ServiceDependencyManager
    
    # Service configurations
    service_configs: Dict[str, Any] = field(default_factory=dict)
    service_clients: Dict[str, Any] = field(default_factory=dict)
    
    # Global settings
    read_only: bool = False
    enabled_tools: Optional[Set[str]] = None
    disabled_tools: Optional[Set[str]] = None
    
    # User context (populated per request)
    user_id: Optional[str] = field(default=None, init=False)
    user_permissions: Optional[UserPermissions] = field(default=None, init=False)
    user_auth_token: Optional[str] = field(default=None, init=False)
    user_auth_type: Optional[str] = field(default=None, init=False)
    
    # Feature flags and experimentation
    feature_flags: FeatureFlags = field(default_factory=FeatureFlags)
    
    # Request-scoped cache
    _request_cache: Dict[str, Any] = field(default_factory=dict, init=False)
    
    def __post_init__(self):
        """Initialize derived properties after context creation."""
        self._initialize_service_shortcuts()
    
    def _initialize_service_shortcuts(self):
        """Create shortcut properties for service configurations and clients."""
        # This would dynamically create properties based on available services
        pass
    
    # Service Configuration Access
    @property
    def skyfi_config(self) -> Optional[SkyFiConfig]:
        """Get SkyFi service configuration."""
        return self.service_configs.get("skyfi")
    
    @property
    def osm_config(self) -> Optional[OSMConfig]:
        """Get OSM service configuration."""
        return self.service_configs.get("osm")
    
    @property
    def weather_config(self) -> Optional[WeatherConfig]:
        """Get Weather service configuration."""
        return self.service_configs.get("weather")
    
    # Service Client Access
    @property
    def skyfi_client(self) -> Optional[SkyFiClient]:
        """Get SkyFi service client with user context."""
        if "skyfi" not in self.service_clients:
            return None
        
        client = self.service_clients["skyfi"]
        # Inject user context if available
        if self.user_auth_token:
            client.user_context = {
                "auth_token": self.user_auth_token,
                "auth_type": self.user_auth_type,
                "user_id": self.user_id
            }
        return client
    
    @property
    def osm_client(self) -> Optional[OSMClient]:
        """Get OSM service client."""
        return self.service_clients.get("osm")
    
    @property
    def weather_client(self) -> Optional[WeatherClient]:
        """Get Weather service client with user context."""
        client = self.service_clients.get("weather")
        if client and self.user_auth_token:
            client.user_context = {
                "auth_token": self.user_auth_token,
                "auth_type": self.user_auth_type
            }
        return client
    
    # User Management
    def set_user_context(
        self,
        user_id: Optional[str] = None,
        auth_token: Optional[str] = None,
        auth_type: Optional[str] = None,
        permissions: Optional[UserPermissions] = None
    ) -> None:
        """Set user context for the current request."""
        self.user_id = user_id
        self.user_auth_token = auth_token
        self.user_auth_type = auth_type
        self.user_permissions = permissions or UserPermissions()
    
    def get_user_permissions(self) -> UserPermissions:
        """Get user permissions with safe defaults."""
        return self.user_permissions or UserPermissions()
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        return self.get_user_permissions().has(permission)
    
    # Feature Management
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if feature is enabled for current user/request."""
        return self.feature_flags.is_enabled(feature_name, self.user_id)
    
    def get_feature_variant(self, feature_name: str) -> str:
        """Get feature variant for A/B testing."""
        return self.feature_flags.get_variant(feature_name, self.user_id)
    
    # Caching
    def cache_get(self, key: str) -> Any:
        """Get value from request-scoped cache."""
        return self._request_cache.get(key)
    
    def cache_set(self, key: str, value: Any) -> None:
        """Set value in request-scoped cache."""
        self._request_cache[key] = value
    
    def cache_clear(self) -> None:
        """Clear request-scoped cache."""
        self._request_cache.clear()
    
    # Service Health
    async def check_service_health(self, service_name: str) -> Dict[str, Any]:
        """Check health of a specific service."""
        client = self.service_clients.get(service_name)
        if not client:
            return {"status": "unavailable", "error": "Service not configured"}
        
        try:
            return await client.health_check()
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    # Resource Management
    async def cleanup(self) -> None:
        """Cleanup resources for the current request."""
        self.cache_clear()
        # Additional cleanup logic would go here
```

### 2.2 Service Dependency Manager

```python
# servers/dependencies.py
from __future__ import annotations

import logging
import os
from typing import Dict, Any, Optional, Set, List, Type
from ..utils.config_manager import ConfigurationManager
from ..utils.environment import get_env_bool, get_env_list

logger = logging.getLogger("mcp-skyfi.dependencies")

class ServiceDependencyManager:
    """
    Comprehensive service dependency management.
    
    Handles:
    - Service discovery and configuration loading
    - Client lifecycle management
    - Health monitoring and circuit breaker patterns
    - Resource cleanup and connection management
    - Configuration validation and error reporting
    """
    
    def __init__(self):
        self.config_manager = ConfigurationManager()
        self.service_configs: Dict[str, Any] = {}
        self.service_clients: Dict[str, Any] = {}
        self.health_status: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the dependency manager."""
        if self._initialized:
            return
        
        logger.info("Initializing Service Dependency Manager")
        self._initialized = True
    
    async def load_all_configurations(self) -> Dict[str, Any]:
        """
        Load and validate configurations for all available services.
        
        Returns:
            Dictionary of service_name -> configuration_object for valid configs
        """
        logger.info("Loading service configurations...")
        
        # Load configurations using the configuration manager
        configs = self.config_manager.load_all_configs()
        
        # Log configuration status
        for service_name, config in configs.items():
            logger.info(f"✓ {service_name.title()} service configured")
            logger.debug(f"{service_name} config: {config.get_display_info()}")
        
        # Log any configuration errors
        validation_errors = self.config_manager.get_validation_errors()
        for service_name, errors in validation_errors.items():
            if service_name not in configs:  # Only log for unconfigured services
                logger.warning(f"✗ {service_name.title()} service not configured: {errors}")
        
        self.service_configs = configs
        return configs
    
    async def create_service_clients(self, configs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create service clients for all configured services.
        
        Args:
            configs: Dictionary of service configurations
            
        Returns:
            Dictionary of service_name -> client_instance
        """
        logger.info("Creating service clients...")
        clients = {}
        
        for service_name, config in configs.items():
            try:
                client_class = self._get_client_class(service_name)
                client = client_class(config)
                clients[service_name] = client
                logger.info(f"✓ Created {service_name} client")
            except Exception as e:
                logger.error(f"✗ Failed to create {service_name} client: {e}")
        
        self.service_clients = clients
        return clients
    
    def _get_client_class(self, service_name: str) -> Type:
        """Get client class for a service."""
        client_classes = {
            "skyfi": "mcp_skyfi.skyfi.client.SkyFiClient",
            "osm": "mcp_skyfi.osm.client.OSMClient",
            "weather": "mcp_skyfi.weather.client.WeatherClient"
        }
        
        class_path = client_classes.get(service_name)
        if not class_path:
            raise ValueError(f"Unknown service: {service_name}")
        
        module_path, class_name = class_path.rsplit(".", 1)
        module = __import__(module_path, fromlist=[class_name])
        return getattr(module, class_name)
    
    async def perform_health_checks(self) -> Dict[str, Dict[str, Any]]:
        """
        Perform health checks on all configured services.
        
        Returns:
            Dictionary of service_name -> health_status
        """
        logger.info("Performing service health checks...")
        health_results = {}
        
        for service_name, client in self.service_clients.items():
            try:
                health_status = await client.health_check()
                health_results[service_name] = health_status
                
                status = health_status.get("status", "unknown")
                logger.info(f"✓ {service_name} health: {status}")
                
            except Exception as e:
                health_results[service_name] = {
                    "status": "error",
                    "error": str(e)
                }
                logger.error(f"✗ {service_name} health check failed: {e}")
        
        self.health_status = health_results
        return health_results
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status for all services."""
        return {
            "overall_status": self._calculate_overall_health(),
            "services": self.health_status,
            "configured_services": list(self.service_configs.keys()),
            "available_services": list(self.service_clients.keys()),
            "configuration_errors": self.config_manager.get_validation_errors(),
        }
    
    def _calculate_overall_health(self) -> str:
        """Calculate overall system health status."""
        if not self.health_status:
            return "unknown"
        
        statuses = [status.get("status", "unknown") for status in self.health_status.values()]
        
        if all(status == "healthy" for status in statuses):
            return "healthy"
        elif any(status == "error" for status in statuses):
            return "degraded"
        else:
            return "unknown"
    
    # Environment-based configuration
    def is_read_only_mode(self) -> bool:
        """Check if server should run in read-only mode."""
        return get_env_bool("READ_ONLY_MODE", False)
    
    def get_enabled_tools(self) -> Optional[Set[str]]:
        """Get set of explicitly enabled tools."""
        tools_list = get_env_list("ENABLED_TOOLS")
        return set(tools_list) if tools_list else None
    
    def get_disabled_tools(self) -> Optional[Set[str]]:
        """Get set of explicitly disabled tools."""
        tools_list = get_env_list("DISABLED_TOOLS")
        return set(tools_list) if tools_list else None
    
    def get_feature_flags(self) -> Dict[str, bool]:
        """Get feature flags configuration."""
        flags = {}
        
        # Parse feature flags from environment
        flags_str = os.getenv("FEATURE_FLAGS", "")
        for flag_def in flags_str.split(","):
            flag_def = flag_def.strip()
            if "=" in flag_def:
                name, value = flag_def.split("=", 1)
                flags[name.strip()] = value.strip().lower() in ("true", "1", "yes")
        
        return flags
    
    # Resource management
    async def shutdown(self) -> None:
        """Shutdown all services and cleanup resources."""
        logger.info("Shutting down Service Dependency Manager...")
        
        # Close all service clients
        for service_name, client in self.service_clients.items():
            try:
                if hasattr(client, 'close'):
                    await client.close()
                logger.info(f"✓ Closed {service_name} client")
            except Exception as e:
                logger.error(f"✗ Error closing {service_name} client: {e}")
        
        self.service_clients.clear()
        self.service_configs.clear()
        self.health_status.clear()
        self._initialized = False
        
        logger.info("Service Dependency Manager shutdown complete")
```

### 2.3 Middleware for Context Injection

```python
# servers/middleware.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Dict, Optional
import logging

logger = logging.getLogger("mcp-skyfi.middleware")

class UserTokenMiddleware(BaseHTTPMiddleware):
    """
    Extract user authentication tokens from request headers.
    
    Supports multiple authentication methods:
    - Bearer tokens (OAuth, PAT)
    - Service-specific API keys
    - Custom authentication headers
    """
    
    SUPPORTED_AUTH_HEADERS = {
        "Authorization": "bearer",
        "X-Skyfi-Api-Key": "skyfi_api_key",
        "X-Weather-Api-Key": "weather_api_key",
        "X-API-Key": "api_key"
    }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Extract authentication information from request."""
        
        # Initialize auth context
        request.state.user_auth_token = None
        request.state.user_auth_type = None
        request.state.user_id = None
        
        # Check each supported authentication header
        for header_name, auth_type in self.SUPPORTED_AUTH_HEADERS.items():
            header_value = request.headers.get(header_name)
            if not header_value:
                continue
            
            if auth_type == "bearer" and header_value.startswith("Bearer "):
                # Extract Bearer token
                token = header_value[7:].strip()
                request.state.user_auth_token = token
                request.state.user_auth_type = "bearer"
                
                # Could extract user ID from JWT here if needed
                # request.state.user_id = extract_user_id_from_jwt(token)
                break
                
            elif auth_type != "bearer":
                # Direct API key authentication
                request.state.user_auth_token = header_value
                request.state.user_auth_type = auth_type
                break
        
        # Log authentication method (without exposing tokens)
        if request.state.user_auth_token:
            logger.debug(f"Request authenticated with {request.state.user_auth_type}")
        else:
            logger.debug("Unauthenticated request")
        
        return await call_next(request)

class ServiceContextMiddleware(BaseHTTPMiddleware):
    """
    Inject service context into requests for MCP tool execution.
    
    Creates a request-scoped context with:
    - Service clients configured with user authentication
    - User permissions and feature flags
    - Request-specific caching
    """
    
    def __init__(self, app, server_ref):
        super().__init__(app)
        self.server_ref = server_ref
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Inject service context into request."""
        
        try:
            # Get main application context from lifespan
            lifespan_context = getattr(request.app.state, "lifespan_context", {})
            app_context = lifespan_context.get("app_lifespan_context")
            
            if app_context:
                # Create request-scoped context copy
                request_context = self._create_request_context(request, app_context)
                request.state.service_context = request_context
                
                logger.debug("Service context injected into request")
            else:
                logger.warning("No application context available for request")
                request.state.service_context = None
            
        except Exception as e:
            logger.error(f"Failed to inject service context: {e}")
            request.state.service_context = None
        
        response = await call_next(request)
        
        # Cleanup request context if created
        if hasattr(request.state, "service_context") and request.state.service_context:
            await request.state.service_context.cleanup()
        
        return response
    
    def _create_request_context(self, request: Request, app_context):
        """Create request-scoped context from application context."""
        from .context import MainAppContext
        
        # Create a copy of the application context for this request
        request_context = MainAppContext(
            dependency_manager=app_context.dependency_manager,
            service_configs=app_context.service_configs,
            service_clients=app_context.service_clients,
            read_only=app_context.read_only,
            enabled_tools=app_context.enabled_tools,
            disabled_tools=app_context.disabled_tools,
            feature_flags=app_context.feature_flags,
        )
        
        # Inject user authentication context
        request_context.set_user_context(
            user_id=getattr(request.state, "user_id", None),
            auth_token=getattr(request.state, "user_auth_token", None),
            auth_type=getattr(request.state, "user_auth_type", None),
        )
        
        return request_context
```

## 3. Context Usage in Tools

### 3.1 Tool Context Access Pattern

```python
# Example tool using dependency injection
from fastmcp import FastMCP, Context
from typing import Annotated
from ..servers.context import MainAppContext

service_mcp = FastMCP("Service Tools")

@service_mcp.tool(
    name="example_tool",
    description="Example tool demonstrating context usage",
    tags=["example", "read"]
)
async def example_tool(
    parameter: Annotated[str, "Example parameter"],
    context: Annotated[MainAppContext, Context]
) -> str:
    """Example tool showing proper context usage."""
    
    try:
        # 1. Access service configuration
        if not context.skyfi_config:
            raise MCPError("SkyFi service not configured")
        
        # 2. Check user permissions
        if not context.has_permission("skyfi:read"):
            raise MCPError("Insufficient permissions")
        
        # 3. Check feature flags
        if not context.is_feature_enabled("advanced_search"):
            raise MCPError("Feature not available")
        
        # 4. Use request cache
        cache_key = f"example:{parameter}"
        cached_result = context.cache_get(cache_key)
        if cached_result:
            return cached_result
        
        # 5. Execute with service client (includes user auth)
        async with context.skyfi_client as client:
            result = await client.some_operation(parameter)
        
        # 6. Cache result
        context.cache_set(cache_key, result)
        
        return f"Operation completed: {result}"
        
    except Exception as e:
        # Context automatically includes user and request information
        logger.error(f"Tool execution failed: {e}", extra={
            "user_id": context.user_id,
            "auth_type": context.user_auth_type,
            "parameter": parameter
        })
        raise MCPError(f"Operation failed: {str(e)}")
```

## 4. Testing Patterns for Dependency Injection

### 4.1 Test Context Creation

```python
# tests/conftest.py
import pytest
from unittest.mock import Mock, AsyncMock
from ..servers.context import MainAppContext
from ..servers.dependencies import ServiceDependencyManager

@pytest.fixture
async def mock_dependency_manager():
    """Create mock dependency manager for testing."""
    manager = Mock(spec=ServiceDependencyManager)
    manager.is_read_only_mode.return_value = False
    manager.get_enabled_tools.return_value = None
    manager.get_disabled_tools.return_value = None
    manager.get_health_status.return_value = {"overall_status": "healthy"}
    return manager

@pytest.fixture
async def test_app_context(mock_dependency_manager):
    """Create test application context with mocked services."""
    
    # Mock service configurations
    mock_skyfi_config = Mock()
    mock_skyfi_config.is_auth_configured.return_value = True
    mock_skyfi_config.get_display_info.return_value = {"service": "skyfi"}
    
    # Mock service clients
    mock_skyfi_client = AsyncMock()
    mock_skyfi_client.health_check.return_value = {"status": "healthy"}
    
    context = MainAppContext(
        dependency_manager=mock_dependency_manager,
        service_configs={"skyfi": mock_skyfi_config},
        service_clients={"skyfi": mock_skyfi_client}
    )
    
    return context

@pytest.fixture
def test_user_context(test_app_context):
    """Create test context with user authentication."""
    test_app_context.set_user_context(
        user_id="test-user-123",
        auth_token="test-token",
        auth_type="bearer"
    )
    return test_app_context
```

### 4.2 Tool Testing with Context

```python
# tests/test_tools.py
import pytest
from unittest.mock import AsyncMock
from ..skyfi.archives import archive_search_tool
from ..exceptions import MCPError

@pytest.mark.asyncio
async def test_archive_search_tool_success(test_user_context):
    """Test successful archive search with proper context."""
    
    # Mock client response
    mock_response = {"archives": [], "total": 0}
    test_user_context.skyfi_client.search_archives = AsyncMock(return_value=mock_response)
    
    # Execute tool
    result = await archive_search_tool(
        aoi="POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
        context=test_user_context
    )
    
    # Verify client was called with correct parameters
    test_user_context.skyfi_client.search_archives.assert_called_once()
    
    assert "No archives found" in result

@pytest.mark.asyncio
async def test_archive_search_tool_no_config(test_app_context):
    """Test tool behavior when service is not configured."""
    
    # Remove SkyFi configuration
    test_app_context.service_configs.pop("skyfi", None)
    
    with pytest.raises(MCPError, match="SkyFi service not configured"):
        await archive_search_tool(
            aoi="POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
            context=test_app_context
        )

@pytest.mark.asyncio
async def test_archive_search_tool_read_only_mode(test_user_context):
    """Test tool behavior in read-only mode."""
    
    # This would be for a write tool, archives are read-only
    test_user_context.read_only = True
    
    # Archive search should still work (it's read-only)
    mock_response = {"archives": [], "total": 0}
    test_user_context.skyfi_client.search_archives = AsyncMock(return_value=mock_response)
    
    result = await archive_search_tool(
        aoi="POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
        context=test_user_context
    )
    
    assert "No archives found" in result
```

This comprehensive service mounting and dependency injection architecture provides:

1. **Clean Separation of Concerns** - Clear boundaries between service configuration, client management, and tool execution
2. **Flexible Service Discovery** - Dynamic mounting based on available configurations
3. **Request-Scoped Context** - Proper isolation and resource management per request
4. **Multi-Level Filtering** - Comprehensive tool filtering based on configuration, permissions, and feature flags
5. **Comprehensive Testing Support** - Full mocking and testing patterns for all components
6. **Health Monitoring** - Built-in health checking and status reporting
7. **Graceful Degradation** - Proper handling of missing services and configurations
8. **Resource Management** - Proper cleanup and connection pooling

The architecture supports both development and production scenarios with comprehensive monitoring, testing, and error handling capabilities.