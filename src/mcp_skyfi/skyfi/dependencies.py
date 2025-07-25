"""
SkyFi Service Dependencies

Dependency injection system for SkyFi service with factory integration,
context management, and client creation based on collective intelligence patterns.
"""


import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

from fastmcp import Context
from typing_extensions import Annotated

from .factory import get_client_factory, create_skyfi_client
from .client import SkyFiClient
from .config import SkyFiConfig
from ..exceptions import SkyFiAPIError, SkyFiAuthenticationError

if TYPE_CHECKING:
    from ..servers.context import MainAppContext

logger = logging.getLogger("mcp-skyfi.skyfi.dependencies")

# Context dependency annotations for type hints
SkyFiContext = Annotated[Dict[str, Any], Context]


async def get_skyfi_client(context: SkyFiContext) -> SkyFiClient:
    """
    Dependency function to create authenticated SkyFi client using factory pattern.
    
    This function integrates with the collective intelligence factory system to:
    1. Extract user context from MCP request context
    2. Get SkyFi configuration from application context
    3. Create authenticated client using factory with caching and pooling
    4. Return ready-to-use SkyFi client instance
    
    Args:
        context: MCP request context containing app and user data
        
    Returns:
        Configured SkyFiClient instance with factory optimizations
        
    Raises:
        SkyFiAPIError: If SkyFi service is not configured or available
        SkyFiAuthenticationError: If authentication credentials are invalid
        
    Usage in tools:
        @skyfi_mcp.tool()
        async def search_archives(context: SkyFiContext):
            client = await get_skyfi_client(context)
            async with client:
                return await client.search_archives(geometry)
    """
    try:
        # Get application context from MCP request context
        app_context = _get_app_context(context)
        if not app_context:
            raise SkyFiAPIError("Application context not available")
        
        # Check if SkyFi service is available
        if not app_context.is_service_available("skyfi"):
            raise SkyFiAPIError(
                "SkyFi service is not available. Please check your SKYFI_API_KEY "
                "and SKYFI_URL environment variables."
            )
        
        # Get SkyFi configuration
        skyfi_config = app_context.get_service_config("skyfi")
        if not skyfi_config:
            raise SkyFiAPIError("SkyFi configuration not available")
        
        # Get user context with authentication information
        user_context = app_context.user_context.copy()
        
        # Add request metadata for factory optimization
        user_context.update({
            "request_id": app_context.request_metadata.get("request_id"),
            "client_ip": app_context.request_metadata.get("client_ip"),
            "service_name": "skyfi"
        })
        
        logger.debug(f"Creating SkyFi client with factory (auth_type: {user_context.get('auth_type', 'config')})")
        
        # Create client using factory pattern
        client = await create_skyfi_client(user_context, skyfi_config)
        
        logger.info("SkyFi client created successfully with factory optimizations")
        return client
        
    except Exception as e:
        logger.error(f"Failed to create SkyFi client: {e}", exc_info=True)
        
        if isinstance(e, (SkyFiAPIError, SkyFiAuthenticationError)):
            raise
        
        raise SkyFiAPIError(f"Client creation failed: {str(e)}")


async def get_skyfi_client_direct(context: SkyFiContext) -> SkyFiClient:
    """
    Alternative dependency function for direct client creation without factory.
    
    This bypasses the factory system and creates clients directly, useful for:
    - Testing scenarios
    - Debugging factory issues
    - Legacy compatibility
    - Simple use cases without caching needs
    
    Args:
        context: MCP request context
        
    Returns:
        Direct SkyFiClient instance
    """
    try:
        app_context = _get_app_context(context)
        if not app_context or not app_context.is_service_available("skyfi"):
            raise SkyFiAPIError("SkyFi service not available")
        
        skyfi_config = app_context.get_service_config("skyfi")
        user_context = app_context.user_context.copy()
        
        logger.debug("Creating SkyFi client directly (bypassing factory)")
        client = SkyFiClient(config=skyfi_config, user_context=user_context)
        
        return client
        
    except Exception as e:
        logger.error(f"Direct client creation failed: {e}")
        if isinstance(e, (SkyFiAPIError, SkyFiAuthenticationError)):
            raise
        raise SkyFiAPIError(f"Direct client creation failed: {str(e)}")


def get_skyfi_config(context: SkyFiContext) -> SkyFiConfig:
    """
    Dependency function to get SkyFi configuration.
    
    Args:
        context: MCP request context
        
    Returns:
        SkyFi configuration instance
        
    Raises:
        SkyFiAPIError: If configuration is not available
    """
    try:
        app_context = _get_app_context(context)
        if not app_context:
            raise SkyFiAPIError("Application context not available")
        
        skyfi_config = app_context.get_service_config("skyfi")
        if not skyfi_config:
            raise SkyFiAPIError("SkyFi configuration not available")
        
        return skyfi_config
        
    except Exception as e:
        logger.error(f"Failed to get SkyFi config: {e}")
        if isinstance(e, SkyFiAPIError):
            raise
        raise SkyFiAPIError(f"Configuration access failed: {str(e)}")


def get_user_context(context: SkyFiContext) -> Dict[str, Any]:
    """
    Dependency function to get user context information.
    
    Args:
        context: MCP request context
        
    Returns:
        User context dictionary with authentication and metadata
    """
    try:
        app_context = _get_app_context(context)
        if not app_context:
            return {}
        
        return app_context.user_context.copy()
        
    except Exception as e:
        logger.warning(f"Failed to get user context: {e}")
        return {}


def is_read_only_mode(context: SkyFiContext) -> bool:
    """
    Check if the current request is in read-only mode.
    
    Args:
        context: MCP request context
        
    Returns:
        True if read-only mode is active
    """
    try:
        app_context = _get_app_context(context)
        return app_context.read_only if app_context else False
        
    except Exception:
        return False


def can_execute_write_operation(context: SkyFiContext, tool_name: str = "") -> bool:
    """
    Check if write operations are allowed in the current context.
    
    Args:
        context: MCP request context
        tool_name: Name of the tool requesting write access
        
    Returns:
        True if write operations are allowed
    """
    try:
        app_context = _get_app_context(context)
        if not app_context:
            return False
        
        return app_context.can_execute_write_operation(tool_name)
        
    except Exception:
        return False


async def get_factory_stats(context: SkyFiContext) -> Dict[str, Any]:
    """
    Get SkyFi client factory statistics for monitoring and debugging.
    
    Args:
        context: MCP request context
        
    Returns:
        Factory statistics including cache hits, connection pool status, etc.
    """
    try:
        factory = get_client_factory()
        stats = factory.get_factory_stats()
        
        logger.debug("Retrieved factory statistics")
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get factory stats: {e}")
        return {"error": str(e)}


async def cleanup_factory_resources(context: SkyFiContext) -> Dict[str, Any]:
    """
    Clean up factory resources and return cleanup statistics.
    
    This is useful for maintenance operations and resource management.
    
    Args:
        context: MCP request context
        
    Returns:
        Cleanup statistics
    """
    try:
        factory = get_client_factory()
        cleanup_stats = await factory.cleanup_resources()
        
        logger.info("Factory resources cleaned up successfully")
        return cleanup_stats
        
    except Exception as e:
        logger.error(f"Failed to cleanup factory resources: {e}")
        return {"error": str(e)}


def _get_app_context(context: SkyFiContext) -> Optional['MainAppContext']:
    """
    Extract MainAppContext from MCP request context.
    
    Args:
        context: MCP request context dictionary
        
    Returns:
        MainAppContext instance or None if not available
    """
    try:
        # Navigate the MCP context structure to find app context
        mcp_server = context.get("_mcp_server")
        if not mcp_server:
            logger.debug("MCP server not found in context")
            return None
        
        request_context = getattr(mcp_server, "request_context", None)
        if not request_context:
            logger.debug("Request context not found")
            return None
        
        lifespan_context = getattr(request_context, "lifespan_context", None)
        if not lifespan_context:
            logger.debug("Lifespan context not found")
            return None
        
        app_context = lifespan_context.get("app_lifespan_context")
        if not app_context:
            logger.debug("App lifespan context not found")
            return None
        
        return app_context
        
    except Exception as e:
        logger.warning(f"Failed to extract app context: {e}")
        return None


# Export dependency functions for use in tools
__all__ = [
    "get_skyfi_client",
    "get_skyfi_client_direct", 
    "get_skyfi_config",
    "get_user_context",
    "is_read_only_mode",
    "can_execute_write_operation",
    "get_factory_stats",
    "cleanup_factory_resources",
    "SkyFiContext"
]