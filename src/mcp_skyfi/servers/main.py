"""
Main SkyFi MCP Server Class

This module implements the primary FastMCP server with hierarchical architecture,
multi-service support, tool filtering, and enterprise-grade features.

Architecture:
1. MCP Transport Layer - Protocol handling (STDIO, SSE, Streamable HTTP)
2. FastMCP Server Layer - Framework integration and tool filtering  
3. Service Layer - Business logic for SkyFi, OSM, Weather services
4. Data Processing Layer - Model transformation and validation
5. Authentication Layer - Multi-method security handling
6. Network Layer - HTTP clients and external API management
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Literal, Optional

from fastmcp import FastMCP
from fastmcp.server import MCPTool
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .context import MainAppContext
from .dependencies import (
    get_available_services, 
    get_enabled_tools,
    get_config_class, 
    is_read_only_mode
)
from ..middleware.auth import UserTokenMiddleware
from ..skyfi import skyfi_mcp
from ..osm import osm_mcp  
from ..weather import weather_mcp
from ..exceptions import SkyFiMCPError

logger = logging.getLogger("mcp-skyfi.server.main")


class SkyFiMCP(FastMCP[MainAppContext]):
    """
    Custom FastMCP server class with multi-service support and advanced tool filtering.
    
    Features:
    - Dynamic tool discovery and filtering based on configuration
    - Multi-service mounting with independent authentication
    - Read-only mode support for secure deployments
    - Enterprise authentication middleware integration
    - Comprehensive health monitoring and metrics
    """

    async def _mcp_list_tools(self) -> list[MCPTool]:
        """
        Override FastMCP's tool discovery with custom filtering logic.
        
        Applies multi-level filtering:
        1. Enabled tools filter (whitelist)
        2. Read-only mode filter (excludes write operations)
        3. Service availability filter (requires valid authentication)
        4. User context filter (per-request permissions)
        """
        # Get application context
        req_context = self._mcp_server.request_context
        if req_context is None or req_context.lifespan_context is None:
            logger.warning("Lifespan context not available during tool list")
            return []

        app_context = req_context.lifespan_context.get("app_lifespan_context")
        if not app_context:
            logger.error("Application context not available")
            return []

        # Get all available tools from mounted services
        all_tools = await self.get_tools()
        filtered_tools = []
        
        tool_count = {"total": len(all_tools), "enabled": 0, "filtered": 0}

        for tool_name, tool_obj in all_tools.items():
            if self._should_include_tool(tool_name, tool_obj, app_context):
                filtered_tools.append(tool_obj.to_mcp_tool(name=tool_name))
                tool_count["enabled"] += 1
            else:
                tool_count["filtered"] += 1

        logger.info(
            f"Tool discovery complete: {tool_count['total']} total, "
            f"{tool_count['enabled']} enabled, {tool_count['filtered']} filtered"
        )

        return filtered_tools

    def _should_include_tool(
        self, 
        tool_name: str, 
        tool_obj: Any, 
        context: MainAppContext
    ) -> bool:
        """
        Multi-level tool filtering logic with comprehensive access control.
        
        Filter Hierarchy:
        1. Enabled tools whitelist (server configuration)
        2. Read-only mode enforcement (security)
        3. Service availability (authentication status)
        4. User permissions (per-request authorization)
        """
        try:
            # 1. Enabled tools filter - whitelist approach
            if context.enabled_tools and tool_name not in context.enabled_tools:
                logger.debug(f"Tool {tool_name} filtered: not in enabled tools list")
                return False

            # 2. Read-only mode filter - security enforcement
            if hasattr(tool_obj, 'tags') and context.read_only:
                tool_tags = getattr(tool_obj, 'tags', [])
                if "write" in tool_tags or "admin" in tool_tags:
                    logger.debug(f"Tool {tool_name} filtered: read-only mode active")
                    return False

            # 3. Service availability filter - authentication validation
            if hasattr(tool_obj, 'tags'):
                tool_tags = getattr(tool_obj, 'tags', [])
                
                # Check SkyFi service availability
                if "skyfi" in tool_tags:
                    if not getattr(context, 'skyfi_config', None):
                        logger.debug(f"Tool {tool_name} filtered: SkyFi not configured")
                        return False
                
                # Check OSM service availability (always available)
                if "osm" in tool_tags:
                    # OSM tools are always available as they don't require authentication
                    pass
                
                # Check Weather service availability
                if "weather" in tool_tags:
                    if not getattr(context, 'weather_config', None):
                        logger.debug(f"Tool {tool_name} filtered: Weather service not configured")
                        return False

            # 4. User context filter (future: per-request permissions)
            # This would check user-specific permissions from request context
            # For now, all authenticated tools are available

            return True

        except Exception as e:
            logger.error(f"Error filtering tool {tool_name}: {e}", exc_info=True)
            return False

    def http_app(
        self,
        path: str | None = None,
        middleware: list[Middleware] | None = None,
        transport: Literal["streamable-http", "sse"] = "streamable-http",
    ) -> Starlette:
        """
        Create HTTP application with custom middleware pipeline.
        
        Middleware Stack:
        1. User Authentication Middleware (token extraction)
        2. Rate Limiting Middleware (future)
        3. Request Logging Middleware (future)
        4. CORS Middleware (if enabled)
        """
        # Build middleware pipeline
        auth_middleware = Middleware(UserTokenMiddleware, mcp_server_ref=self)
        final_middleware = [auth_middleware]
        
        if middleware:
            final_middleware.extend(middleware)

        # Create HTTP app with enhanced configuration
        app = super().http_app(
            path=path,
            middleware=final_middleware,
            transport=transport
        )

        return app


@asynccontextmanager
async def main_lifespan(app: FastMCP[MainAppContext]) -> AsyncIterator[dict]:
    """
    Server lifespan management with comprehensive service configuration loading.
    
    Lifecycle:
    1. Load and validate all service configurations
    2. Initialize HTTP clients and connection pools
    3. Set up monitoring and health checks
    4. Create application context with all configurations
    5. Graceful shutdown and resource cleanup
    """
    logger.info("🚀 SkyFi MCP server lifespan starting...")
    
    # Load and validate service configurations
    services = get_available_services()
    service_configs = {}
    service_status = {"skyfi": False, "osm": True, "weather": False}  # OSM always available
    
    # Initialize SkyFi service
    if services.get("skyfi"):
        try:
            from ..skyfi.config import SkyFiConfig
            skyfi_config = SkyFiConfig.from_env()
            
            if skyfi_config.is_auth_configured():
                service_configs["skyfi_config"] = skyfi_config
                service_status["skyfi"] = True
                logger.info("✅ SkyFi service configuration loaded successfully")
            else:
                logger.warning("⚠️ SkyFi API URL found but authentication incomplete")
                
        except Exception as e:
            logger.error(f"❌ Failed to load SkyFi configuration: {e}")
    
    # Initialize OSM service (no authentication required)
    if services.get("osm"):
        try:
            from ..osm.config import OSMConfig
            osm_config = OSMConfig.from_env()
            service_configs["osm_config"] = osm_config
            service_status["osm"] = True
            logger.info("✅ OSM service configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to load OSM configuration: {e}")
            service_status["osm"] = False
    
    # Initialize Weather service
    if services.get("weather"):
        try:
            from ..weather.config import WeatherConfig
            weather_config = WeatherConfig.from_env()
            
            if weather_config.is_auth_configured():
                service_configs["weather_config"] = weather_config
                service_status["weather"] = True
                logger.info("✅ Weather service configuration loaded successfully")
            else:
                logger.warning("⚠️ Weather service URL found but authentication incomplete")
                
        except Exception as e:
            logger.error(f"❌ Failed to load Weather configuration: {e}")

    # Create comprehensive application context
    app_context = MainAppContext(
        read_only=is_read_only_mode(),
        enabled_tools=get_enabled_tools(),
        service_status=service_status,
        **service_configs
    )

    # Log service availability summary
    enabled_services = [name for name, status in service_status.items() if status]
    logger.info(f"🔧 Enabled services: {', '.join(enabled_services) or 'None'}")
    
    if app_context.read_only:
        logger.info("🔒 Read-only mode active - write operations disabled")

    try:
        yield {"app_lifespan_context": app_context}
    finally:
        logger.info("🛑 SkyFi MCP server lifespan shutting down...")
        
        # Cleanup resources
        for config_name, config in service_configs.items():
            if hasattr(config, 'cleanup'):
                try:
                    await config.cleanup()
                    logger.debug(f"✅ Cleaned up {config_name}")
                except Exception as e:
                    logger.warning(f"⚠️ Error cleaning up {config_name}: {e}")


# Initialize main server with service mounting
main_mcp = SkyFiMCP(
    name="SkyFi MCP Server", 
    version="1.0.0",
    lifespan=main_lifespan
)

# Mount service modules with clear namespace separation
main_mcp.mount("skyfi", skyfi_mcp)
main_mcp.mount("osm", osm_mcp)
main_mcp.mount("weather", weather_mcp)


# Add health check endpoint for monitoring
@main_mcp.custom_route("/healthz", methods=["GET"], include_in_schema=False)
async def health_check(request: Request) -> JSONResponse:
    """
    Comprehensive health check endpoint for monitoring and load balancers.
    
    Returns service status, uptime, and basic system metrics.
    """
    try:
        # Get application context if available
        context_data = getattr(request.app.state, 'lifespan_context', {})
        app_context = context_data.get('app_lifespan_context')
        
        health_status = {
            "status": "healthy",
            "version": "1.0.0",
            "services": {
                "skyfi": bool(app_context and getattr(app_context, 'skyfi_config', None)),
                "osm": True,  # OSM is always available
                "weather": bool(app_context and getattr(app_context, 'weather_config', None))
            } if app_context else {"skyfi": False, "osm": False, "weather": False},
            "read_only": bool(app_context and app_context.read_only) if app_context else False
        }
        
        # Determine overall health status
        active_services = sum(health_status["services"].values())
        if active_services == 0:
            health_status["status"] = "unhealthy"
        elif active_services < len(health_status["services"]):
            health_status["status"] = "degraded"
            
        status_code = 200 if health_status["status"] == "healthy" else 503
        
        return JSONResponse(health_status, status_code=status_code)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return JSONResponse(
            {
                "status": "unhealthy", 
                "error": str(e),
                "version": "1.0.0"
            }, 
            status_code=503
        )


# Add metrics endpoint for monitoring (optional)
@main_mcp.custom_route("/metrics", methods=["GET"], include_in_schema=False)
async def metrics_endpoint(request: Request) -> JSONResponse:
    """
    Basic metrics endpoint for monitoring tool usage and performance.
    """
    try:
        # This would integrate with a metrics collection system
        # For now, return basic placeholder metrics
        metrics = {
            "tools": {
                "total_available": 0,
                "enabled": 0,
                "executed_today": 0
            },
            "services": {
                "skyfi_requests": 0,
                "osm_requests": 0,  
                "weather_requests": 0
            },
            "performance": {
                "avg_response_time_ms": 0,
                "error_rate_percent": 0
            }
        }
        
        return JSONResponse(metrics)
        
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}", exc_info=True)
        return JSONResponse({"error": "Metrics unavailable"}, status_code=500)